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
        first_fail = next((a for a in accels if not res[f"{prefix}{a:g}"]["ok"]), None)
        passing = [a for a in accels if res[f"{prefix}{a:g}"]["ok"] and (first_fail is None or a < first_fail)]
        rows = [{"accel_mm_s2": a * a_nom, "ok": res[f"{prefix}{a:g}"]["ok"], "errors": sorted(set(res[f"{prefix}{a:g}"]["errors"])),
                 "cross_track_rms_mm": res[f"{prefix}{a:g}"]["cross_track_rms_mm"], "cross_track_worst_mm": res[f"{prefix}{a:g}"]["cross_track_worst_mm"],
                 "max_bulge_mm": res[f"{prefix}{a:g}"]["max_bulge_mm"], "print_time_s": res[f"{prefix}{a:g}"]["print_time_s"]} for a in accels]
        return {"max_clean_accel_mm_s2": (max(passing) * a_nom) if passing else 0.0, "accel_margin": max(passing) if passing else 0.0,
                "highest_accel_tried_mm_s2": max(accels) * a_nom,
                "first_failure": ({"accel_mm_s2": first_fail * a_nom, "errors": sorted(set(res[f"{prefix}{first_fail:g}"]["errors"])),
                                   "axes_losing_steps": res[f"{prefix}{first_fail:g}"].get("lost_step_axes")} if first_fail else None),
                "table": rows}

    def nominal(name):
        r = res[name]
        rep = _rep(out / name)
        return {"ok": r["ok"], "errors": r["errors"], "print_time_s": r["print_time_s"], "cross_track_rms_mm": r["cross_track_rms_mm"],
                "cross_track_worst_mm": r["cross_track_worst_mm"], "cross_track_p99_mm": rep.get("dynamics", {}).get("cross_track_p99_mm"),
                "command_smoothing_worst_mm": rep.get("dynamics", {}).get("command_smoothing_worst_mm"),
                "max_bulge_mm": r["max_bulge_mm"], "outline_offset_mm": r["outline_offset_mm"]}

    tun = (_rep(out / "fw_nominal").get("firmware") or {}).get("tuning") or {}
    sh = tun.get("input_shaper") or {}
    return {"ran": True, "firmware": "Klipper", "commit": commit, "speed_scale_in_sweep": speed,
            "clean_means": "the test cube prints without lost steps and within the print checks, as in the built-in sweep",
            "as_configured": {"nominal": nominal("fw_nominal"), **sweep("fw_a")},
            "shaper_and_pressure_advance_off": {"nominal": nominal("fw_nominal_plain"), **sweep("fw_plain_a")},
            "input_shaper": {ax: {k: sh[ax].get(k) for k in ("shaper_type", "shaper_freq", "damping_ratio", "predicted_resonance_hz",
                                                               "suggested_max_accel")} for ax in ("x", "y") if ax in sh},
            "pressure_advance": {k: pa.get(k) for k in ("value", "basis", "from_sweep")},
            "assumed": sorted(set((sh.get("assumed") or []) + (pa.get("assumed") or [])))}


def _rep(run_dir: Path) -> dict:
    try:
        return json.loads((run_dir / "print_report.json").read_text())
    except Exception:
        return {}


def score(design_path, out_root="out", speed: float = 2.0, assembly: bool = False, firmware: str | None = None,
          builtin: bool = True) -> dict:
    """firmware="klipper" adds a "klipper" block (firmware_block) beside the built-in planner's figures; the top-level
    max_clean_accel_mm_s2, cross_track_* and benchmark_time_s are always the built-in planner's (no input shaping, no
    pressure advance). builtin=False skips the built-in sweep and benchmark (their keys are then None, "not run")."""
    t0 = time.time()
    design = load_design(design_path)
    if not design.printer:
        return {"error": "design does not declare design.printer"}
    rep = verify(design, only=["geometry", "ratings", "fea"])
    metrics = {r.verifier: r.metrics for r in rep.results}
    pm = printer_map_for(design, metrics)
    pm_kw = {"belt_ea_n": pm.belt_ea_n, "struct_stiffness": pm.struct_stiffness,
             **{k: getattr(pm, k) for k in ("x", "y", "z", "bed", "perimeter_speed", "infill_speed", "travel_speed")}}
    out = Path(out_root) / design.name / "score"
    fw_block = firmware_block(design_path, design, pm, pm_kw, out, speed) if firmware == "klipper" else None
    if not builtin:
        s = {"design": design.name, "static_checks_ok": rep.ok, "planner": "built-in planner NOT RUN (firmware only)",
             "nominal_print_ok": None, "benchmark_ok": None, "max_clean_accel_mm_s2": None, "accel_margin": None,
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
    s = {
        "design": design.name,
        "static_checks_ok": rep.ok,
        "planner": "built-in planner (no input shaping, no pressure advance) for every top-level figure",
        "nominal_print_ok": nom["ok"],
        "benchmark_ok": all(b["ok"] for b in bench.values()),
        # --- things to push up
        "max_clean_accel_mm_s2": (max(passing) * a_nom) if passing else 0.0,
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
        **({"assembly": _assembly(design)} if assembly else {}),
        **({"klipper": fw_block} if fw_block is not None else {}),
        "static_errors": [f"{f.verifier}:{f.code}" for f in rep.errors()],
        "seconds": round(time.time() - t0, 1),
    }
    _append(out_root, design.name, s)
    return s


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
