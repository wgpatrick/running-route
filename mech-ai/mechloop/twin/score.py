"""A scorecard for a printer design: numbers an agent can try to improve, as opposed to
thresholds it only has to clear. Everything comes from the design's own CAD and simulations."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..runner import load_design, verify
from . import printer_map_for
from .evals import _run_all

ACCELS = (1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6, 7, 8, 10, 12)


FW_ACCELS = (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12)


def firmware_block(design_path, design, pm, pm_kw, out: Path, speed: float = 2.0, accels=FW_ACCELS) -> dict:
    """The firmware-in-the-loop part of the scorecard: real Klipper plans every print from the generated printer.cfg.
    The acceleration sweep is run twice, with the configuration as generated (input shaper and pressure advance on)
    and with both switched off, so the effect of the firmware features is a difference between two Klipper results and
    is never mixed up with the built-in planner's figures."""
    from . import firmware as fw

    try:
        _, _, commit = fw.find_klipper()
    except fw.FirmwareNotAvailable as ex:
        return {"ran": False, "error": str(ex)}
    from . import tuning

    if str(out.parent.parent) not in tuning.TUNING_ROOTS:          # a sweep made with `mechloop tune --out <same root>`
        tuning.TUNING_ROOTS.insert(0, str(out.parent.parent))
    pa = tuning.pressure_advance(design, pm)
    # the workers are separate processes: hand them the K the generated configuration would carry
    on, off = {"pressure_advance": pa["value"], "bed_mesh": False}, {"input_shaper": False, "pressure_advance": False, "bed_mesh": False}
    kw = {"firmware": "klipper"}
    jobs = [("fw_nominal", "quick", dict(pm_kw), {**kw, "firmware_opts": on}, str(out)),
            ("fw_nominal_plain", "quick", dict(pm_kw), {**kw, "firmware_opts": off}, str(out))]
    for a in accels:
        jobs += [(f"fw_a{a:g}", "quick", dict(pm_kw), {**kw, "firmware_opts": on, "speed_scale": speed, "accel_scale": float(a)}, str(out)),
                 (f"fw_plain_a{a:g}", "quick", dict(pm_kw), {**kw, "firmware_opts": off, "speed_scale": speed, "accel_scale": float(a)}, str(out))]
    res = _run_all(design_path, jobs)
    jl = {j.name: j for j in design.joints}
    a_nom = jl[pm.x].max_accel

    def sweep(prefix):
        return sweep_summary({a: res[f"{prefix}{a:g}"] for a in accels}, a_nom)

    def nominal(name):
        r = res[name]
        rep = _rep(out / name)
        return {"ok": r["ok"], "not_run": r.get("not_run"), "errors": r["errors"], "print_time_s": r["print_time_s"], "cross_track_rms_mm": r["cross_track_rms_mm"],
                "cross_track_worst_mm": r["cross_track_worst_mm"], "cross_track_p99_mm": rep.get("dynamics", {}).get("cross_track_p99_mm"),
                "command_smoothing_worst_mm": rep.get("dynamics", {}).get("command_smoothing_worst_mm"),
                "max_bulge_mm": r["max_bulge_mm"], "outline_offset_mm": r["outline_offset_mm"]}

    tun = (_rep(out / "fw_nominal").get("firmware") or {}).get("tuning") or {}
    sh = tun.get("input_shaper") or {}
    from . import fitted as F

    sug = [sh[ax].get("suggested_max_accel") for ax in ("x", "y") if ax in sh and sh[ax].get("suggested_max_accel")]
    u = F.triple("used_accel_over_shaper_rule")
    owners = ({"shaper_rule_accel_mm_s2": min(sug), "accel_owners_would_run_mm_s2": round(min(sug) * u[1], -2),
               "accel_owners_would_run_range_mm_s2": [round(min(sug) * u[0], -2), round(min(sug) * u[1], -2), round(min(sug) * u[2], -2)],
               "basis": "Klipper's own suggested max_accel for the chosen shapers (the lower axis), times the 0.5 (0.4 to 0.65) of it that "
                        "owners of three reference machines run; the resonance it rests on is the twin's prediction at the values in use "
                        "(its range is under 'ranges' at the top level)"} if sug else {})
    blocks = {"as_configured": {"nominal": nominal("fw_nominal"), **sweep("fw_a")},
              "shaper_and_pressure_advance_off": {"nominal": nominal("fw_nominal_plain"), **sweep("fw_plain_a")}}
    not_run = [f"{k}: {b['not_run_warning']}" for k, b in blocks.items() if b.get("not_run_warning")]
    not_run += [f"{k}: the nominal print was NOT RUN ({res[n]['not_run'].get('detail')})"
                for k, n in (("as_configured", "fw_nominal"), ("shaper_and_pressure_advance_off", "fw_nominal_plain")) if res[n].get("not_run")]
    return {"ran": True, "firmware": "Klipper", "commit": commit, "speed_scale_in_sweep": speed, **owners,
            "prints_not_run": not_run,
            "reading": "highest_clean_accel_mm_s2 is the highest acceleration of the sweep that printed cleanly: with shaping on it is a "
                       "ceiling set by the sweep or by step loss, not an acceleration to run. accel_owners_would_run_mm_s2 is the usable figure.",
            "clean_means": "the test cube prints without lost steps and within the print checks, as in the built-in sweep",
            **blocks,
            "input_shaper": {ax: {k: sh[ax].get(k) for k in ("shaper_type", "shaper_freq", "damping_ratio", "predicted_resonance_hz",
                                                               "suggested_max_accel")} for ax in ("x", "y") if ax in sh},
            "pressure_advance": {k: pa.get(k) for k in ("value", "basis", "from_sweep")},
            "assumed": sorted(set((sh.get("assumed") or []) + (pa.get("assumed") or [])))}


def sweep_summary(by_accel: dict, a_nom: float) -> dict:
    """One acceleration sweep from its prints' summaries ({accel factor: summarise(report)}).
    A print that was NOT RUN (Klipper's output could not be read back: `not_run` in its summary) is neither clean nor
    a failure: it is left out of "highest clean" and of "first failure", listed under `not_run`, and the summary says
    which figures it leaves open."""
    accels = sorted(by_accel)
    nr = [a for a in accels if by_accel[a].get("not_run")]
    ran = [a for a in accels if a not in nr]
    first_fail = next((a for a in ran if not by_accel[a]["ok"]), None)
    passing = [a for a in ran if by_accel[a]["ok"] and (first_fail is None or a < first_fail)]
    rows = [{"accel_mm_s2": a * a_nom, "ok": (None if a in nr else by_accel[a]["ok"]),
             "status": "NOT RUN" if a in nr else ("clean" if by_accel[a]["ok"] else "failed"),
             "errors": sorted(set(by_accel[a]["errors"])),
             "cross_track_rms_mm": by_accel[a].get("cross_track_rms_mm"), "cross_track_worst_mm": by_accel[a].get("cross_track_worst_mm"),
             "max_bulge_mm": by_accel[a].get("max_bulge_mm"), "print_time_s": by_accel[a].get("print_time_s")} for a in accels]
    top = (max(passing) * a_nom) if passing else 0.0
    out = {"highest_clean_accel_mm_s2": top, "max_clean_accel_mm_s2": top,      # the second is the old name of the first
           "accel_margin": max(passing) if passing else 0.0,
           "highest_accel_tried_mm_s2": max(accels) * a_nom,
           "first_failure": ({"accel_mm_s2": first_fail * a_nom, "errors": sorted(set(by_accel[first_fail]["errors"])),
                              "axes_losing_steps": by_accel[first_fail].get("lost_step_axes")} if first_fail else None),
           "table": rows}
    if nr:
        hi = max(passing) if passing else 0.0
        open_ = [a for a in nr if a > hi and (first_fail is None or a < first_fail)]
        out["not_run"] = [{"accel_mm_s2": a * a_nom, "reason": by_accel[a]["not_run"].get("reason"),
                           "detail": by_accel[a]["not_run"].get("detail")} for a in nr]
        out["not_run_warning"] = (
            f"{len(nr)} of {len(accels)} prints of this sweep were NOT RUN (at "
            + ", ".join(f"{a * a_nom:g}" for a in nr) + " mm/s^2): they are not counted as clean and not as failures. "
            + ("The highest clean figure may be higher than stated: " + ", ".join(f"{a * a_nom:g}" for a in open_)
               + " mm/s^2 lies between it and the first failure (or the top of the sweep) and was not run."
               if open_ else "They lie below the highest clean point, so the highest clean figure stands on its neighbours."))
    return out


def _rep(run_dir: Path) -> dict:
    try:
        return json.loads((run_dir / "print_report.json").read_text())
    except Exception:
        return {}


def score(design_path, out_root="out", speed: float = 2.0, assembly: bool = False, firmware: str | None = None,
          builtin: bool = True, pm_overrides: dict | None = None, uncertainty: bool = True) -> dict:
    """firmware="klipper" adds a "klipper" block (firmware_block) beside the built-in planner's figures; the top-level
    max_clean_accel_mm_s2, cross_track_* and benchmark_time_s are always the built-in planner's (no input shaping, no
    pressure advance). builtin=False skips the built-in sweep and benchmark (their keys are then None, "not run")."""
    t0 = time.time()
    design = load_design(design_path)
    if not design.printer:
        return {"error": "design does not declare design.printer"}
    rep = verify(design, only=["geometry", "ratings", "fea"])
    metrics = {r.verifier: r.metrics for r in rep.results}
    pm = printer_map_for(design, metrics, **(pm_overrides or {}))
    pm_kw = {"belt_ea_n": pm.belt_ea_n, "struct_stiffness": pm.struct_stiffness, **(pm_overrides or {}),
             **{k: getattr(pm, k) for k in ("x", "y", "z", "bed", "perimeter_speed", "infill_speed", "travel_speed")}}
    out = Path(out_root) / design.name / "score"
    fw_block = firmware_block(design_path, design, pm, pm_kw, out, speed) if firmware == "klipper" else None
    if not builtin:
        s = {"design": design.name, "static_checks_ok": rep.ok, "planner": "built-in planner NOT RUN (firmware only)",
             "nominal_print_ok": None, "benchmark_ok": None, "step_loss_ceiling_accel_mm_s2": None, "max_clean_accel_mm_s2": None,
             "accel_margin": None,
             "cross_track_rms_mm": None, "cross_track_worst_mm": None, "benchmark_time_s": None,
             "frame_stiffness_n_per_mm": pm.struct_stiffness, "klipper": fw_block,
             "static_errors": [f"{f.verifier}:{f.code}" for f in rep.errors()], "seconds": round(time.time() - t0, 1)}
        _append(out_root, design.name, s)
        return s
    jobs = [("nominal", "quick", dict(pm_kw), {}, str(out))]
    jobs += [(f"a{a:g}", "quick", dict(pm_kw), {"speed_scale": speed, "accel_scale": float(a)}, str(out)) for a in ACCELS]
    jobs += [(f"bench_{n}", n, dict(pm_kw), {}, str(out)) for n in ("cube", "tolerance", "tower")]
    res = _run_all(design_path, jobs)
    first_fail = next((a for a in ACCELS if not res[f"a{a:g}"]["ok"]), None)
    passing = [a for a in ACCELS if res[f"a{a:g}"]["ok"] and (first_fail is None or a < first_fail)]
    jl = {j.name: j for j in design.joints}
    a_nom = jl[pm.x].max_accel
    nom = res["nominal"]
    bench = {n: res[f"bench_{n}"] for n in ("cube", "tolerance", "tower")}
    moving = {}
    bodies = design.bodies()

    def carried(body):
        m = sum(c.mass() for c in bodies.get(body, []))
        return m + sum(carried(j.child) for j in design.joints if j.parent == body)

    for ax in ("x", "y", "z"):
        moving[ax] = round(carried(jl[getattr(pm, ax)].child), 3)
    ceiling = (max(passing) * a_nom) if passing else 0.0
    flow = _rep(out / "nominal").get("flow") or {}
    s = {
        "design": design.name,
        "static_checks_ok": rep.ok,
        "planner": "built-in planner (no input shaping, no pressure advance) for every top-level figure",
        "nominal_print_ok": nom["ok"],
        "benchmark_ok": all(b["ok"] for b in bench.values()),
        # --- things to push up
        # where the simulated motors lose steps (at 2x speed): a ceiling, 6 to 8 times above what owners of three
        # reference machines run. `max_clean_accel_mm_s2` is the same number under its old name.
        "step_loss_ceiling_accel_mm_s2": ceiling,
        "max_clean_accel_mm_s2": ceiling,
        "accel_margin": max(passing) if passing else 0.0,
        "resonance_hz": {"x": nom["resonance_hz"][0], "y": nom["resonance_hz"][1]},
        "frame_stiffness_n_per_mm": pm.struct_stiffness,
        # --- things to push down
        "cross_track_rms_mm": _dyn(out / "nominal", "cross_track_rms_mm"),
        "cross_track_worst_mm": _dyn(out / "nominal", "cross_track_worst_mm"),
        "benchmark_time_s": round(sum(b["print_time_s"] for b in bench.values()), 1),
        # with the electrical model: each benchmark part starts from a cold machine (heat-up from the heater simulation)
        "benchmark_time_with_heatup_s": (round(sum(b["print_time_s"] + b["heatup_s"] for b in bench.values()), 1)
                                         if all(b.get("heatup_s") is not None for b in bench.values()) else None),
        "moving_mass_kg": moving,
        "total_mass_kg": round(design.total_mass(), 3),
        "bom_cost_usd": metrics.get("ratings", {}).get("bom_cost_usd_estimate"),
        "first_failure": ({"accel_mm_s2": first_fail * a_nom, "errors": sorted(set(res[f"a{first_fail:g}"]["errors"])),
                           "axes_losing_steps": res[f"a{first_fail:g}"].get("lost_step_axes")}
                          if first_fail else None),
        "print_speeds_mm_s": {"perimeter": pm.perimeter_speed, "infill": pm.infill_speed, "travel": pm.travel_speed},
        # melt-rate cap of the hotend against what the design's speeds ask for (flow-limited speeds are slowed, and named here)
        "melt_rate": {"cap_mm3_s": flow.get("cap_mm3_s"), "requested_flow_mm3_s": flow.get("requested_flow_mm3_s"),
                      "speed_at_cap_mm_s": flow.get("speed_at_cap_mm_s"), "flow_limited": flow.get("limited") or {},
                      "flow_limited_in_2x_sweep": (_rep(out / f"a{ACCELS[0]:g}").get("flow") or {}).get("limited") or {},
                      "hotend_class": (flow.get("basis") or {}).get("class"), "cap_range_mm3_s": [(flow.get("basis") or {}).get("low"),
                                                                                                 (flow.get("basis") or {}).get("high")]},
        "extruder": {"lag_s": pm.extruder_lag_s, "basis": pm.extruder_lag_basis},
        "toolhead_compliance": (_rep(out / "nominal").get("dynamics") or {}).get("toolhead_compliance"),
        **({"assembly": _assembly(design)} if assembly else {}),
        **({"klipper": fw_block} if fw_block is not None else {}),
        "static_errors": [f"{f.verifier}:{f.code}" for f in rep.errors()],
        "seconds": round(time.time() - t0, 1),
    }
    s.update(_ranges(design_path, out, s, pm, pm_overrides, speed, uncertainty))
    s["seconds"] = round(time.time() - t0, 1)
    _append(out_root, design.name, s)
    return s


def _ranges(design_path, out: Path, s: dict, pm, pm_overrides, speed: float, rerun: bool) -> dict:
    """[low, expected, high] beside each headline number, from the fitted parameter ranges (fitted_parameters.json).
    Resonance and the shaper-rule accelerations: closed form (calibration.design_ranges). Step-loss ceiling and
    cross-track error: the twin re-run at the soft and stiff ends (evals.score_uncertainty), unless rerun is False."""
    from . import calibration as C
    from . import fitted as F

    try:
        dr = C.design_ranges(design_path, out / "nominal" / "print_report.json", frame_stiffness=pm.struct_stiffness,
                             max_clean_accel=s["step_loss_ceiling_accel_mm_s2"])
    except Exception as ex:
        return {"ranges": None, "ranges_error": f"{type(ex).__name__}: {ex}"}
    u = F.triple("used_accel_over_shaper_rule")
    ranges = {"resonance_hz": dr["resonance_hz"], "shaper_rule_accel_mm_s2": dr["shaper_rule_accel_mm_s2"],
              "accel_owners_would_run_mm_s2": dr["accel_owners_would_run_mm_s2"],
              "step_loss_ceiling_accel_mm_s2": None, "cross_track_rms_mm": None, "cross_track_worst_mm": None}
    extra = {}
    if rerun:
        from .evals import score_uncertainty

        try:
            un = score_uncertainty(design_path, out, s, speed=speed, accels=ACCELS, pm_overrides=pm_overrides)
            rl = un["range_low_expected_high"]
            for k in ("step_loss_ceiling_accel_mm_s2", "cross_track_rms_mm", "cross_track_worst_mm"):
                ranges[k] = rl[k]
            # the re-run sets also move the damping and the lag; keep the wider of the two resonance ranges
            for ax in dr["resonance_hz"]:
                a, b = dr["resonance_hz"][ax], rl["resonance_hz"][ax]
                ranges["resonance_hz"][ax] = [min(a[0], b[0]), a[1], max(a[2], b[2])]
            extra["uncertainty_runs"] = un["runs"]
            extra["ranges_varied"] = un["varied"]
            extra["ranges_not_varied"] = un["not_varied"]
        except Exception as ex:
            extra["ranges_error"] = f"{type(ex).__name__}: {ex}"
    ranges["max_clean_accel_mm_s2"] = ranges["step_loss_ceiling_accel_mm_s2"]          # old name
    owners = dr["accel_owners_would_run_mm_s2"]
    head = {
        "step_loss_ceiling_accel_mm_s2": {"value": s["step_loss_ceiling_accel_mm_s2"], "range": ranges["step_loss_ceiling_accel_mm_s2"],
                                          "meaning": "acceleration (at 2x speed) at which the simulated motors first lose steps: a ceiling, "
                                                     "not an acceleration to run; one sweep step is not a real difference"},
        "accel_owners_would_run_mm_s2": {"value": owners[1], "range": owners,
                                         "meaning": f"acceleration an owner would run with input shaping: {u[1]:g} ({u[0]:g} to {u[2]:g}) x Klipper's "
                                                    "shaper smoothing rule (MZV, 0.12 mm) at the lower resonance; calibrated on three machines"},
        "resonance_hz": {"value": s["resonance_hz"], "range": ranges["resonance_hz"], "meaning": "frequency each axis's load rings at"},
        "cross_track_rms_mm": {"value": s["cross_track_rms_mm"], "range": ranges["cross_track_rms_mm"],
                               "meaning": "sideways error from the planned path at the design's own settings"},
        "cross_track_worst_mm": {"value": s["cross_track_worst_mm"], "range": ranges["cross_track_worst_mm"], "meaning": "its largest value"},
        "benchmark_time_s": {"value": s["benchmark_time_s"], "range": None,
                             "meaning": "three benchmark parts at the design's own speeds, held to the hotend's melt rate; the ranged "
                                        "parameters do not enter (the melt-rate cap would, if a requested speed were flow-limited: see melt_rate)"}}
    return {"accel_owners_would_run_mm_s2": owners[1], "shaper_rule_accel_mm_s2": dr["shaper_rule_accel_mm_s2"][1],
            "ranges": ranges, "headline": head,
            "ranges_basis": "low / expected / high from the ranges in mechloop/twin/fitted_parameters.json; expected is the scored value",
            **extra}


def _append(out_root, name, s):
    hist = Path(out_root) / name / "scores.jsonl"
    hist.parent.mkdir(parents=True, exist_ok=True)
    with open(hist, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **s}, default=float) + "\n")


def _dyn(run_dir: Path, key: str):
    try:
        return json.loads((run_dir / "print_report.json").read_text())["dynamics"].get(key)
    except Exception:
        return None


def _assembly(design) -> dict:
    """How hard it is to build (from the assembly simulation). All of these are better lower."""
    try:
        from ..assembly.simulate import analyse

        m = analyse(design)["metrics"]
        return {k: m[k] for k in ("complete", "estimated_time_min", "needs_holding", "from_below", "times_assembly_is_turned",
                                  "two_move_paths", "fasteners", "fastener_types", "tool_changes", "parts")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
