"""Firmware tuning as a user would do it on the built machine, done on the twin instead.

  input shaper     Klipper's own shaper_calibrate picks type and frequency per axis from a frequency response. On a
                   real machine that response comes from an accelerometer during TEST_RESONANCES; here it is the
                   twin's own linearised axis model driven the same way (klippy_code.choose_shaper).
  pressure advance K starts at the twin's assumed melt-flow lag (for a first-order lag the two are the same thing)
                   and `pressure_advance_sweep` finds it the way a test print does: print, look at the corners.
  probe / bed mesh offsets and mesh bounds from the CAD (electrical.probe_geometry); `measure_mesh` probes the twin's
                   as-built bed surface point by point and returns the profile Klipper would have saved.

Everything here is a prediction resting on assumed values (damping ratios, belt stiffness, extruder lag, probe
repeatability, the bed's shape). Each result carries an `assumed` list saying which.
"""
from __future__ import annotations

import numpy as np

from . import PrinterMap, _axis_info, bed_deviation, printer_map_for
from .machine import linear_axis, machine_model

PA_SMOOTH_TIME = 0.04          # Klipper's default pressure_advance_smooth_time
# lagrange (Klipper's default) reproduces a plane, and with five points a bow, exactly; its bicubic does not (a plane
# comes back up to 0.008 mm out with the default tension, see tests/test_twin.py)
MESH_DEFAULTS = {"probe_count": (5, 5), "algorithm": "lagrange", "mesh_pps": (2, 2), "fade_start": 1.0, "fade_end": 10.0,
                 "split_delta_z": 0.01, "tension": 0.2}


# ------------------------------------------------------------------ input shaper
def resonance_response(mm: dict, k: int, pm, freqs=None):
    """What a resonance test would record on axis k: Klipper's TEST_RESONANCES sweeps a small oscillation whose
    acceleration amplitude grows with frequency (accel_per_hz * f); the accelerometer on the toolhead sees that times
    the axis's response. Returns (frequencies, power spectral density, the linear model)."""
    f = np.arange(5.0, 200.0, 0.5) if freqs is None else np.asarray(freqs, dtype=float)
    lin = linear_axis(mm, k, pm)
    psd = (f * np.abs(lin["H"](f))) ** 2
    return f, psd, lin


def input_shaper(design, pm: PrinterMap, mm: dict | None = None) -> dict:
    """Shaper type, frequency and damping ratio for X and Y. The choice is made by Klipper's shaper_calibrate from the
    twin's predicted frequency response; raises ImportError when Klipper's source is not installed."""
    from . import klippy_code as K

    mm = mm or machine_model(design, pm)
    out = {"basis": "", "assumed": ["stepper damping ratio %g" % pm.damping_ratio, "belt/frame damping ratio %g" % pm.spring_damping_ratio,
                                    "belt stiffness EA %g N per 6 mm" % pm.belt_ea_n],
           "selected_by": K.source() + " (shaper_calibrate.find_best_shaper) on the twin's synthetic frequency response",
           "frame_stiffness_used_n_per_mm": dict(pm.struct_stiffness) or None}
    for k, ax in enumerate("xy"):
        f, psd, lin = resonance_response(mm, k, pm)
        mode = lin["modes"][0]                       # the mode the load rings at
        zeta = float(min(max(mode["damping_ratio"], 0.02), 0.3))
        ch = K.choose_shaper(f, psd, damping_ratio=zeta)
        out[ax] = {"shaper_type": ch["shaper_type"], "shaper_freq": ch["shaper_freq"], "damping_ratio": round(zeta, 3),
                   "predicted_resonance_hz": round(mode["hz"], 1), "predicted_damping_ratio": round(mode["damping_ratio"], 3),
                   "other_modes_hz": [round(m["hz"], 1) for m in lin["modes"][1:]],
                   "remaining_vibrations_frac": ch["remaining_vibrations_frac"], "smoothing": ch["smoothing"],
                   "suggested_max_accel": ch["suggested_max_accel"], "candidates": ch["candidates"]}
    out["basis"] = ("predicted by the twin, not measured: resonance X %.1f Hz, Y %.1f Hz (%s); damping assumed. Run SHAPER_CALIBRATE"
                    % (out["x"]["predicted_resonance_hz"], out["y"]["predicted_resonance_hz"],
                       "belts + FEA frame stiffness" if pm.struct_stiffness else "belt stiffness only, no FEA frame stiffness"))
    return out


# ------------------------------------------------------------------ pressure advance
TUNING_ROOTS = ["out"]          # where `mechloop tune` results are looked for (<root>/<design>/tune/tuning.json)


def stored_sweep(design_name: str, lag_s: float, roots=None) -> dict | None:
    """The last pressure-advance sweep `mechloop tune` ran for this design, if it was made with the same assumed lag."""
    import json
    from pathlib import Path

    for root in (roots or TUNING_ROOTS):
        f = Path(root) / design_name / "tune" / "tuning.json"
        try:
            sw = json.loads(f.read_text())["pressure_advance"]["sweep"]
            if sw.get("best") is not None and abs(sw.get("assumed_extruder_lag_s", -1.0) - lag_s) < 1e-9:
                return {**sw, "file": str(f)}
        except Exception:
            continue
    return None


def pressure_advance(design, pm: PrinterMap, roots=None) -> dict:
    """K for the config, in this order: fixed in the design's firmware block
    (firmware['extruder_tuning']['pressure_advance']); the best K of the last sweep on the twin (`mechloop tune`), as a
    user takes it from a test print; else the twin's assumed melt-flow lag, the value a first-order lag calls for."""
    el = getattr(design, "electrical", None)
    fixed = ((el.firmware.get("extruder_tuning") or {}).get("pressure_advance") if el is not None else None)
    assumed = [f"extruder lag {pm.extruder_lag_s:g} s (first-order, one value for every flow rate)"]
    if fixed is not None:
        return {"value": float(fixed), "smooth_time": PA_SMOOTH_TIME, "basis": "set in the design's firmware block", "assumed": []}
    sw = stored_sweep(design.name, pm.extruder_lag_s, roots)
    if sw is not None:
        return {"value": float(sw["best"]), "smooth_time": PA_SMOOTH_TIME, "assumed": assumed, "from_sweep": sw["file"],
                "basis": f"best of a sweep on the twin (smallest corner bulge + recess), whose melt-flow lag is an ASSUMED "
                         f"{pm.extruder_lag_s * 1e3:.0f} ms; print a pressure-advance test on the machine"}
    return {"value": float(pm.extruder_lag_s), "smooth_time": PA_SMOOTH_TIME,
            "basis": f"equal to the twin's ASSUMED {pm.extruder_lag_s * 1e3:.0f} ms melt-flow lag (not measured, no sweep run); "
                     "print a pressure-advance test on the machine",
            "assumed": assumed}


# ------------------------------------------------------------------ probe and bed mesh
def mesh_points(pg: dict, count=(5, 5)):
    """Probe positions of the mesh in machine coordinates: (xs, ys), ascending, as Klipper lays them out."""
    return (np.linspace(pg["mesh_min"][0], pg["mesh_max"][0], count[0]), np.linspace(pg["mesh_min"][1], pg["mesh_max"][1], count[1]))


def measure_mesh(design, pm: PrinterMap, pg: dict | None = None, count=None, samples: int = 3, seed: int = 0) -> dict:
    """Probe the twin's as-built bed (pm.bed_surface) at every mesh point, the way BED_MESH_CALIBRATE does, and return
    the profile Klipper would store. Each sample carries the probe's repeatability as Gaussian scatter (assumed); the
    median of `samples` is kept, as the generated [probe] section asks; heights are relative to the zero reference
    point (the middle of the bed, where Z is homed)."""
    from ..electrical import probe_geometry

    pg = pg or probe_geometry(design)
    if pg is None or "mesh_min" not in pg:
        raise ValueError("the design has no usable bed probe")
    count = tuple(count or MESH_DEFAULTS["probe_count"])
    _, info = _axis_info(design, pm)
    xs, ys = mesh_points(pg, count)
    rng = np.random.default_rng(seed)
    sig = float(pg.get("repeatability_mm") or 0.0)
    cx, cy = pg["bed_centre"]

    def probe_at(x, y):       # bed height the probe reports with its sensing face over machine point (x, y)
        true = float(bed_deviation(pm, info, x - cx, y - cy))
        return float(np.median(true + rng.normal(0.0, sig, samples))) if sig > 0 else true

    z0 = probe_at(*pg["home_probe_xy"])
    pts = [[round(probe_at(x, y) - z0, 6) for x in xs] for y in ys]
    return {"points": pts, "min_x": float(xs[0]), "max_x": float(xs[-1]), "min_y": float(ys[0]), "max_y": float(ys[-1]),
            "mesh_x_pps": MESH_DEFAULTS["mesh_pps"][0], "mesh_y_pps": MESH_DEFAULTS["mesh_pps"][1],
            "algo": MESH_DEFAULTS["algorithm"] if max(count) <= 6 else "bicubic", "tension": MESH_DEFAULTS["tension"],
            "range_mm": round(float(np.ptp(pts)), 4), "probe_samples": samples, "seed": seed,
            "basis": "probed in simulation on the twin's assumed bed surface "
                     f"{ {k: v for k, v in (pm.bed_surface or {}).items()} }, probe repeatability {sig:g} mm (assumed)",
            "assumed": ["bed surface shape", "probe repeatability"]}


def mesh_error_over_bed(design, pm: PrinterMap, profile: dict, pg: dict, n: int = 41) -> dict:
    """How well the stored mesh, as Klipper interpolates it (its own ZMesh code), matches the bed it was probed on,
    over the area the nozzle can print. Independent of any print."""
    from . import klippy_code as K

    _, info = _axis_info(design, pm)
    (x0, x1), (y0, y1) = pg["print_area"]
    X, Y = np.meshgrid(np.linspace(x0, x1, n), np.linspace(y0, y1, n))
    cx, cy = pg["bed_centre"]
    true = bed_deviation(pm, info, X - cx, Y - cy)
    hx, hy = pg["home_probe_xy"]
    true = true - float(bed_deviation(pm, info, hx - cx, hy - cy))
    mz = K.mesh_z(profile, np.column_stack([X.ravel(), Y.ravel()])).reshape(X.shape)
    err = mz - true
    return {"without_mesh_mm": {"rms": round(float(np.sqrt((true ** 2).mean())), 4), "worst": round(float(np.abs(true).max()), 4)},
            "with_mesh_mm": {"rms": round(float(np.sqrt((err ** 2).mean())), 4), "worst": round(float(np.abs(err).max()), 4)},
            "area": pg["print_area"], "grid": n, "interpolation": K.source() + " (bed_mesh.ZMesh)"}


# ------------------------------------------------------------------ everything the config needs
def firmware_tuning(design, pm: PrinterMap | None = None, opts: dict | None = None, mass_extra: dict | None = None,
                    strict: bool = True) -> dict:
    """{"input_shaper", "pressure_advance", "probe", "bed_mesh"} for electrical.klipper_config.
    opts: {"input_shaper": True|False|dict, "pressure_advance": True|False|K, "bed_mesh": True|False|profile dict}.
    A part that was asked for and cannot be produced raises; a part switched off is None. With strict=False a shaper
    that cannot be chosen because Klipper's source is not installed is left out and named in out["not_generated"]
    (for writing a configuration file; a print must use strict=True)."""
    from ..electrical import probe_geometry

    opts = dict(opts or {})
    pm = pm or printer_map_for(design)
    out: dict = {"input_shaper": None, "pressure_advance": None, "probe": None, "bed_mesh": None}
    sh = opts.get("input_shaper", True)
    if isinstance(sh, dict):
        out["input_shaper"] = {"basis": "given", **sh}
    elif sh:
        try:
            out["input_shaper"] = input_shaper(design, pm, machine_model(design, pm, mass_extra))
        except ImportError as ex:
            if strict:
                raise
            out["not_generated"] = [f"[input_shaper]: {ex}"]
    pa = opts.get("pressure_advance", True)
    if pa is True:
        out["pressure_advance"] = pressure_advance(design, pm)
    elif pa is not False and pa is not None:
        out["pressure_advance"] = {"value": float(pa), "smooth_time": PA_SMOOTH_TIME, "basis": "value under test", "assumed": []}
    pg = probe_geometry(design)
    out["probe"] = pg
    if pg is not None and "mesh_min" in pg:
        bm = {**MESH_DEFAULTS}
        want = opts.get("bed_mesh", bool(pm.bed_surface))
        if isinstance(want, dict):
            bm["profile"] = want
        elif want:
            bm["profile"] = measure_mesh(design, pm, pg, seed=int(opts.get("mesh_seed", 0)))
        out["bed_mesh"] = bm
    elif opts.get("bed_mesh"):
        raise ValueError("a bed mesh was asked for but the design has no usable bed probe")
    return out


# ------------------------------------------------------------------ studies (each is a set of real Klipper prints)
def _run(printer_path, jobs, workers=3):
    from .evals import _run_all

    return _run_all(printer_path, jobs, workers=workers)


def _report(out, name) -> dict:
    import json
    from pathlib import Path

    try:
        return json.loads((Path(out) / name / "print_report.json").read_text())
    except Exception:
        return {}


def _pm_kw(pm: PrinterMap) -> dict:
    return {k: getattr(pm, k) for k in ("x", "y", "z", "bed", "perimeter_speed", "infill_speed", "travel_speed", "belt_ea_n",
                                        "struct_stiffness", "extruder_lag_s", "damping_ratio", "spring_damping_ratio", "bed_surface")}


def pressure_advance_sweep(printer_path, out, pm: PrinterMap, values=(0.0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06), part="quick") -> dict:
    """Print the test part once per K with real Klipper and read the corner bulge off each result, as a user reads a
    pressure-advance test print. Returns the table and the K with the smallest bulge (ties: the smallest K)."""
    jobs = [(f"pa_{k:g}", part, _pm_kw(pm), {"firmware": "klipper", "firmware_opts": {"pressure_advance": float(k), "bed_mesh": False}},
             str(out)) for k in values]
    res = _run(printer_path, jobs)
    rows = []
    for k in values:
        r = res[f"pa_{k:g}"]
        rows.append({"pressure_advance": k, "ok": r["ok"], "errors": r["errors"], "max_bulge_mm": r["max_bulge_mm"],
                     "max_recess_mm": r["max_recess_mm"], "outline_offset_mm": r["outline_offset_mm"]})
    good = [r for r in rows if r["ok"] and r["max_bulge_mm"] is not None]
    if not good:
        return {"table": rows, "best": None, "error": "no run of the sweep printed"}
    best = min(good, key=lambda r: (r["max_bulge_mm"] + (r["max_recess_mm"] or 0.0), r["pressure_advance"]))
    return {"table": rows, "best": best["pressure_advance"], "criterion": "smallest corner bulge + recess on the test part",
            "assumed_extruder_lag_s": pm.extruder_lag_s,
            "note": "the lag is an assumed first-order constant; the sweep shows the method and that K = lag removes the bulge "
                    "in this model, not what K a real extruder needs"}


def ringing_test(design, pm: PrinterMap, out, opts: dict | None = None, travel_mm: float = 40.0, speed_mm_s: float | None = None,
                 dwell_s: float = 0.25, accel_scale: float = 1.0, dt: float = 0.0005) -> dict:
    """Residual vibration, measured directly: Klipper moves X, then Y, back and forth over seven distances up to
    `travel_mm` at the machine's travel speed and acceleration, stopping after each; the twin's axes follow its steps; what the nozzle still does after the planned motion has
    ended is the ringing. Returns the largest and RMS excursion per axis over the dwells."""
    from pathlib import Path

    from . import firmware as fw
    from . import to_joints
    from .gcode import parse
    from .machine import drive_force
    from .stepper import simulate

    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    joints, info = _axis_info(design, pm)
    v = float(speed_mm_s or pm.travel_speed)
    f, p = v * 60.0, int(dwell_s * 1000)
    # moves of several lengths, so that no one lucky timing of the acceleration and braking pulses decides the result
    lengths = [travel_mm * k for k in (0.12, 0.2, 0.31, 0.45, 0.6, 0.78, 1.0)]
    x0 = y0 = -travel_mm / 2
    lines = ["G90", "G1 Z2 F600", f"G1 X{x0:g} Y{y0:g} F{f:g}", f"G1 X{x0:g} Y{y0 + 1:g} F600", f"G1 X{x0:g} Y{y0:g} F600", f"G4 P{p}"]
    # ... and at several speeds: a constant-acceleration ramp that lasts a whole number of periods leaves no ringing
    # by itself, so one speed can make an axis look quiet by coincidence
    speeds = [v * k for k in (1.0, 0.27, 0.8, 0.4, 0.6, 0.33, 0.5)]
    for ax in "XY":
        for L, vv in zip(lengths, speeds):
            lines += [f"G1 {ax}{x0 + L:g} F{vv * 60:g}", f"G4 P{p}", f"G1 {ax}{x0:g} F{vv * 60 * 0.85:g}", f"G4 P{p}"]
    n_test = 4 * len(lengths)
    gpath = out / "ringing.gcode"
    gpath.write_text("\n".join(lines) + "\n")
    moves, _ = parse(gpath)
    g = np.array([[m.x, m.y, m.z] for m in moves])
    q = np.stack(to_joints(info, g[:, 0], g[:, 1], g[:, 2]), axis=1)
    pts = np.vstack([np.zeros((1, 3)), q])
    res = fw.commanded(design, info, gpath, pts, dt, out / "firmware", pm=pm, opts={"bed_mesh": False, **(opts or {})},
                       accel_scale=accel_scale)
    Qc, Vc, Qn, seg = res["Qc"], res["Vc"], res["Qn"], res["seg"]
    n_settle = int(0.3 / dt)
    Qc = np.vstack([Qc, np.repeat(Qc[-1:], n_settle, 0)])
    Qn = np.vstack([Qn, np.repeat(Qn[-1:], n_settle, 0)])
    Vc = np.vstack([Vc, np.zeros((n_settle, 3))])
    mm = machine_model(design, pm)
    Qa, _, sinfo = simulate(Qc, Vc, mm["mass"], drive_force(mm, Vc), mm["tpr"], mm["bias"], np.array(mm["fric"]), dt,
                            damping_ratio=pm.damping_ratio, motor_mass=mm["motor_mass"], series_stiffness=mm["series"],
                            backlash=mm["back"], spring_damping_ratio=pm.spring_damping_ratio)
    # dwells: the planned trajectory is at rest (after the four test moves; the approach is not counted)
    Vn = np.gradient(Qn, dt, axis=0)
    # at rest = neither the plan nor the (shaped, slightly longer) command is moving; steps are interpolated, so a
    # dwell creeps by one step at most
    still = (np.abs(Vn[:, :2]).max(axis=1) < 0.5) & (np.abs(Vc[:, :2]).max(axis=1) < 0.5)
    still[: int(np.argmax(np.concatenate([seg, [seg[-1]] * n_settle]) >= len(pts) - 1 - n_test))] = False
    err = (Qa - Qn)[:, :2]
    out_d = {"speeds_mm_s": sorted({round(x, 1) for x in speeds} | {round(0.85 * x, 1) for x in speeds}), "accel_mm_s2": float(res["report"]["what_if"]["max_accel"]), "travel_mm": travel_mm,
             "input_shaper": res["report"]["features"]["input_shaper"], "samples_at_rest": int(still.sum())}
    # one window per dwell; within it, ringing is the excursion about where the axis finally comes to rest (rail
    # friction leaves a small standing offset that is not vibration; it is reported separately)
    idx = np.flatnonzero(still)
    wins = [w for w in np.split(idx, np.flatnonzero(np.diff(idx) > 1) + 1) if len(w) > int(0.1 / dt)]
    out_d["dwells"] = len(wins)
    for k, ax in enumerate("xy"):
        osc = np.concatenate([err[w, k] - err[w[-int(0.02 / dt):], k].mean() for w in wins]) if wins else np.zeros(1)
        rest = [float(err[w[-int(0.02 / dt):], k].mean()) for w in wins] or [0.0]
        out_d[ax] = {"residual_peak_mm": round(float(np.abs(osc).max()), 4), "residual_rms_mm": round(float(np.sqrt((osc ** 2).mean())), 4),
                     "standing_offset_worst_mm": round(float(np.abs(rest).max()), 4)}
    return out_d


def bed_mesh_study(printer_path, out, pm: PrinterMap, bed: dict, at=(45.0, 45.0), part="first_layer") -> dict:
    """First-layer gap error with and without the bed mesh, on the same assumed bed: two real Klipper prints of a
    70 x 70 mm two-layer patch placed off-centre, and the mesh checked against the bed over the whole print area."""
    from dataclasses import replace

    from ..electrical import probe_geometry
    from ..runner import load_design

    design = load_design(printer_path)
    pg = probe_geometry(design)
    if pg is None or "mesh_min" not in pg:
        return {"ran": False, "error": "the design has no usable bed probe; a bed mesh cannot be measured"}
    pmb = replace(pm, bed_surface={**bed, "ref_xy": (pg["home_probe_xy"][0] - pg["bed_centre"][0], pg["home_probe_xy"][1] - pg["bed_centre"][1])})
    prof = measure_mesh(design, pmb, pg)
    kw = {"firmware": "klipper", "at": tuple(at)}
    jobs = [("mesh_on", part, _pm_kw(pmb), {**kw, "firmware_opts": {"bed_mesh": True}}, str(out)),
            ("mesh_off", part, _pm_kw(pmb), {**kw, "firmware_opts": {"bed_mesh": False}}, str(out))]
    res = _run(printer_path, jobs, workers=2)
    rows = {}
    for n in ("mesh_on", "mesh_off"):
        rep = _report(out, n)
        rows[n] = {"ok": res[n]["ok"], "errors": res[n]["errors"],
                   "first_layer_gap_error_mm": (rep.get("print") or {}).get("first_layer_gap_error_mm"),
                   "first_layer_nozzle_height_mm": res[n]["first_layer_nozzle_height_mm"],
                   "klipper_mesh": ((rep.get("firmware") or {}).get("features") or {}).get("bed_mesh")}
    return {"ran": True, "bed_surface_assumed_mm": bed, "part": f"{part} at {tuple(at)} mm from the bed centre",
            "probe": {k: pg[k] for k in ("x_offset", "y_offset", "z_offset", "mesh_min", "mesh_max", "repeatability_mm", "unprobed_strip_mm")},
            "mesh": {"points": prof["points"], "range_mm": prof["range_mm"], "probe_count": [len(prof["points"][0]), len(prof["points"])],
                     "how": "klippy's batch mode has no micro-controller to answer a probe, so BED_MESH_CALIBRATE cannot run in it; "
                            "the twin probed its own bed and the result was given to Klipper as the stored [bed_mesh default] "
                            "profile a real machine would have saved"},
            "over_print_area": mesh_error_over_bed(design, pmb, prof, pg), "prints": rows,
            "assumed": ["bed tilt and bow", "probe repeatability %g mm" % pg["repeatability_mm"],
                        "the probe's z_offset is taken as calibrated (its unit-to-unit spread is a separate finding)"]}


def pm_for(design, out_root="out") -> tuple:
    """PrinterMap with frame stiffness from the last full verify, if its report is there. Returns (pm, where from)."""
    import json
    from pathlib import Path

    for root in (out_root, "out"):
        prev = Path(root) / design.name / "report.json"
        if prev.exists():
            try:
                pm = printer_map_for(design, json.loads(prev.read_text())["metrics"])
            except Exception:
                continue
            if pm.struct_stiffness or not (design.printer or {}).get("stiffness"):      # a partial run has no FEA figures
                return pm, str(prev)
    return printer_map_for(design), None


def tune_report(design_path, out_root="out", only=None, bed=None) -> dict:
    """`mechloop tune`: everything above for one design, written to <out>/<name>/tune/tuning.json."""
    import json
    import time
    from pathlib import Path

    from ..runner import load_design
    from . import firmware as fw

    t0 = time.time()
    design = load_design(design_path)
    only = set(only or ("shaper", "pressure_advance", "bed_mesh"))
    out = Path(out_root) / design.name / "tune"
    out.mkdir(parents=True, exist_ok=True)
    res: dict = {"design": design.name, "ok": True}
    try:
        _, _, commit = fw.find_klipper()
        res["klipper_commit"] = commit
    except fw.FirmwareNotAvailable as ex:
        return {"design": design.name, "ok": False, "error": f"not run: {ex}"}
    pm, src = pm_for(design, out_root)
    if str(out_root) not in TUNING_ROOTS:
        TUNING_ROOTS.insert(0, str(out_root))
    res["frame_stiffness_n_per_mm"] = pm.struct_stiffness or None
    res["frame_stiffness_from"] = src or "none (no verify report found): belt stiffness only"
    try:
        if "shaper" in only:
            sh = input_shaper(design, pm)
            res["input_shaper"] = sh
            res["ringing_test"] = {}
            for a in (1.0, 3.0):      # at the design's own acceleration and at three times it
                res["ringing_test"][f"accel_x{a:g}"] = {
                    "with_shaper": ringing_test(design, pm, out / f"ring_on_{a:g}", {"input_shaper": True, "pressure_advance": False}, accel_scale=a),
                    "without_shaper": ringing_test(design, pm, out / f"ring_off_{a:g}", {"input_shaper": False, "pressure_advance": False}, accel_scale=a)}
        if "pressure_advance" in only:
            res["pressure_advance"] = {"sweep": pressure_advance_sweep(design_path, out / "pa", pm)}
            if res["pressure_advance"]["sweep"].get("best") is None:
                res["ok"] = False
            (out / "tuning.json").write_text(json.dumps(res, indent=1, default=float))      # so the next line can read it
            res["pressure_advance"]["configured"] = pressure_advance(design, pm)
        if "bed_mesh" in only:
            b = dict(zip(("tilt_x_mm", "tilt_y_mm", "bow_mm"), bed or (0.30, 0.20, 0.15)))
            res["bed_mesh"] = bed_mesh_study(design_path, out / "mesh", pm, b)
            if not res["bed_mesh"].get("ran") or not res["bed_mesh"]["prints"]["mesh_on"]["ok"]:
                res["ok"] = False        # a study whose print did not run is not a result
    except (fw.FirmwareError, fw.FirmwareNotAvailable, ImportError, ValueError) as ex:
        res["ok"] = False
        res["error"] = f"{type(ex).__name__}: {ex}"
    res["seconds"] = round(time.time() - t0, 1)
    (out / "tuning.json").write_text(json.dumps(res, indent=1, default=float))
    return res
