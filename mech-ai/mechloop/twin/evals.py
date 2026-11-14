"""Evaluating a printer design on its digital twin: a benchmark print suite with a
scorecard, the speed/acceleration envelope, coverage of the build volume,
robustness to assumed parameters, machine faults, design variants and a
sensitivity ranking. Everything runs in simulation."""
from __future__ import annotations

import json
import math
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from build123d import Box, Cylinder, Plane, Polygon, Pos, extrude

from . import PrinterMap, run_print

_PRINTER = None
_PATH = None


def _init(path):
    global _PRINTER, _PATH
    from ..runner import load_design

    _PATH = path
    _PRINTER = load_design(path)


# ------------------------------------------------------------------ parts
def quick_cube():
    return Pos(0, 0, 2) * Box(20, 20, 4)


def bench_parts() -> dict:
    """name -> (shape, what it tests). All sit on Z=0."""
    parts = {}
    parts["cube"] = (Pos(0, 0, 5) * Box(20, 20, 10), "basic dimensional accuracy")
    wall = Pos(0, 0, 4) * (Box(30, 30, 8) - Pos(0, 0, 0.4) * Box(28.4, 28.4, 7.2))
    parts["thin_wall"] = (wall, "0.8 mm walls: single/double bead control")
    plate = Pos(0, 0, 1.5) * Box(46, 20, 3)
    for i, d in enumerate((2, 3, 4, 5, 6)):
        plate -= Pos(-18 + i * 8.5, 4, 1.5) * Cylinder(d / 2, 3)
    for i, w in enumerate((0.4, 0.6, 0.8, 1.0, 1.5)):
        plate -= Pos(-18 + i * 8.5, -5, 1.5) * Box(w, 6, 3)
    parts["tolerance"] = (plate, "holes 2-6 mm and slots 0.4-1.5 mm stay open and on size")
    ov = Pos(0, 0, 0.5) * Box(40, 36, 1)
    for i, ang in enumerate((30, 45, 60)):
        t = math.tan(math.radians(ang))
        prof = Plane.XZ * Polygon((-6, 1), (2, 1), (2 + 10 * t, 11), (-6 + 10 * t, 11), align=None)
        ov += Pos(-8, -8 + i * 12, 0) * extrude(prof, 8)
    parts["overhang"] = (ov, "overhangs at 30, 45 and 60 degrees from vertical")
    br = None
    for i, span in enumerate((10, 20, 30)):
        y = -14 + i * 14
        seg = (Pos(-span / 2 - 2.5, y, 4) * Box(5, 8, 8) + Pos(span / 2 + 2.5, y, 4) * Box(5, 8, 8)
               + Pos(0, y, 9) * Box(span + 10, 8, 2))
        br = seg if br is None else br + seg
    parts["bridge"] = (br, "unsupported bridges of 10, 20 and 30 mm")
    parts["tower"] = (Pos(0, 0, 20) * Box(8, 8, 40), "tall thin part: many short moves, Z travel")
    parts["first_layer"] = (Pos(0, 0, 0.2) * Box(70, 70, 0.4), "large first layer: flow and coverage")
    return parts


# ------------------------------------------------------------------ one run, summarised
KEYS = ("outline_iou_min", "outline_offset_mm", "max_bulge_mm", "max_recess_mm", "layer_shift_mm_worst",
        "top_layer_coverage", "holes_open_fraction", "worst_unsupported_span_mm", "filament_mass_g",
        "first_layer_nozzle_height_mm")


def summarise(rep: dict) -> dict:
    p, d = rep.get("print", {}), rep.get("dynamics", {})
    out = {"ok": rep.get("ok", False),
           "errors": [f["code"] for f in rep.get("findings", []) if f["severity"] == "error"],
           "warnings": [f["code"] for f in rep.get("findings", []) if f["severity"] == "warning"],
           "print_time_s": rep.get("plan", {}).get("print_time_s"),
           "heatup_s": rep.get("plan", {}).get("heatup_s"),
           "slicer_time_s": rep.get("slicer", {}).get("print_time_s"),
           "rms_lag_mm": d.get("rms_lag_mm"), "worst_lag_mm": d.get("worst_lag_mm"),
           "worst_motor_error_mm": d.get("worst_motor_error_mm"),
           "resonance_hz": d.get("load_resonance_hz"), "sim_seconds": rep.get("seconds"),
           "lost_step_axes": sorted({f["data"].get("axis") for f in rep.get("findings", []) if f["code"] == "lost_steps"}),
           "cross_track_rms_mm": d.get("cross_track_rms_mm"), "cross_track_worst_mm": d.get("cross_track_worst_mm"),
           "machine_collisions": rep.get("machine_collisions")}
    for k in KEYS:
        v = p.get(k)
        out[k] = v["worst"] if isinstance(v, dict) and "worst" in v else (v["span_mm"] if isinstance(v, dict) else v)
    return out


def _shape(key: str):
    """Workers build their own part: CAD shapes cannot be sent between processes."""
    if key == "quick":
        return quick_cube()
    if key == "tower140":
        return Pos(0, 0, 70) * Box(8, 8, 140)
    return bench_parts()[key][0]


def _job(args):
    name, key, pm_kw, run_kw, out = args
    shape = _shape(key)
    pm = replace(PrinterMap(), **pm_kw)
    rep = run_print(_PRINTER, shape, Path(out) / name, pm, name=name, render=run_kw.pop("render", False),
                    collisions=run_kw.pop("collisions", False), **run_kw)
    return name, summarise(rep)


def _run_all(printer_path, jobs, workers=4):
    import multiprocessing as mp

    # spawn, not fork: the CAD kernel and numba start threads that do not survive a fork
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("spawn"), initializer=_init,
                             initargs=(str(printer_path),)) as ex:
        return dict(ex.map(_job, jobs))


# ------------------------------------------------------------------ studies
def benchmark_suite(printer_path, out, pm_kw=None, run_kw=None):
    jobs = [(n, n, dict(pm_kw or {}), {"collisions": True, **(run_kw or {})}, str(out)) for n in bench_parts()]
    res = _run_all(printer_path, jobs)
    for n, (_, what) in bench_parts().items():
        res[n]["tests"] = what
    return res


def envelope(printer_path, out, speeds=(1, 2, 3, 4), accels=(1, 2, 3, 4, 5, 7.5, 10)):
    jobs = [(f"v{v:g}_a{a:g}", "quick", {}, {"speed_scale": float(v), "accel_scale": float(a)}, str(out))
            for v in speeds for a in accels]
    res = _run_all(printer_path, jobs)
    grid = {f"{v:g}": {f"{a:g}": res[f"v{v:g}_a{a:g}"] for a in accels} for v in speeds}
    best = None
    for v in speeds:
        for a in accels:
            r = res[f"v{v:g}_a{a:g}"]
            if r["ok"] and (best is None or r["print_time_s"] < best["print_time_s"]):
                best = {"speed_scale": v, "accel_scale": a, "print_time_s": r["print_time_s"]}
    return {"grid": grid, "fastest_passing": best,
            "baseline_time_s": res[f"v{speeds[0]:g}_a{accels[0]:g}"]["print_time_s"]}


def coverage(printer_path, out, reach=70.0):
    jobs = [(f"at_{x:+.0f}_{y:+.0f}", "quick", {}, {"at": (x, y), "collisions": True}, str(out))
            for x, y in ((0, 0), (reach, reach), (reach, -reach), (-reach, reach), (-reach, -reach))]
    jobs.append(("tall_tower", "tower140", {"layer_height": 0.3}, {"collisions": True}, str(out)))
    return _run_all(printer_path, jobs)


SCENARIOS = {
    "nominal": ({}, {}),
    "rail friction x2": ({"friction_n": {"x": 4.0, "y": 6.0, "z": 10.0}}, {}),
    "motor torque -30%": ({}, {"torque_scale": 0.7}),
    "toolhead +300 g": ({}, {"mass_extra": {"x": 0.3, "y": 0.3}}),
    "extruder lag x2": ({"extruder_lag_s": 0.06}, {}),
    "belts half as stiff": ({"belt_ea_n": 11000.0}, {}),
    "less damping": ({"damping_ratio": 0.1, "spring_damping_ratio": 0.02}, {}),
    "all of the above": ({"friction_n": {"x": 4.0, "y": 6.0, "z": 10.0}, "extruder_lag_s": 0.06, "belt_ea_n": 11000.0,
                          "damping_ratio": 0.1, "spring_damping_ratio": 0.02},
                         {"torque_scale": 0.7, "mass_extra": {"x": 0.3, "y": 0.3}}),
}

FAULTS = {  # name -> (PrinterMap overrides, run overrides, what should happen)
    "none": ({}, {}, "pass"),
    "slack X belt (30% stiffness, 0.3 mm lost motion)": ({"belt_ea_n": 6600.0, "backlash_mm": {"x": 0.3}}, {}, "degrade"),
    "0.5 mm lost motion on Y": ({"backlash_mm": {"y": 0.5}}, {}, "degrade"),
    "motor current 40%": ({}, {"torque_scale": 0.4}, "degrade or pass"),
    "motor current 10%": ({}, {"torque_scale": 0.1}, "fail"),
    "bed 0.3 mm too low": ({}, {"z_datum_error": 0.3}, "fail"),
    "bed 0.3 mm too high": ({}, {"z_datum_error": -0.3}, "fail"),
    "bed 0.05 mm too low": ({}, {"z_datum_error": 0.05}, "pass"),
    "stiff Y rail (40 N friction, motor can push 54 N)": ({"friction_n": {"x": 2.0, "y": 40.0, "z": 5.0}}, {}, "degrade"),
    "seized Y rail (80 N friction)": ({"friction_n": {"x": 2.0, "y": 80.0, "z": 5.0}}, {}, "fail"),
}

VARIANTS = {
    "baseline": ({}, {}),
    "direct-drive extruder (+350 g on the toolhead)": ({}, {"mass_extra": {"x": 0.35, "y": 0.35}}),
    "short motors (65% torque)": ({}, {"torque_scale": 0.65}),
    "9 mm belts (1.5x stiffness)": ({"belt_ea_n": 33000.0}, {}),
    "light toolhead (-100 g)": ({}, {"mass_extra": {"x": -0.1, "y": -0.1}}),
    "stiff + light (9 mm belts, -100 g)": ({"belt_ea_n": 33000.0}, {"mass_extra": {"x": -0.1, "y": -0.1}}),
}


def scenarios(printer_path, out, table, run_extra=None):
    jobs = [(f"s{i}", "quick", dict(v[0]), {**v[1], **(run_extra or {})}, str(out)) for i, v in enumerate(table.values())]
    res = _run_all(printer_path, jobs)
    return {name: res[f"s{i}"] for i, name in enumerate(table)}


def variants(printer_path, out, speed=2.0, accels=(1, 2, 3, 4, 5, 6, 8, 10)):
    """Each variant at nominal settings, then its highest passing acceleration at 2x speed."""
    nominal = scenarios(printer_path, Path(out) / "nominal", VARIANTS)
    jobs, names = [], list(VARIANTS)
    for i, n in enumerate(names):
        pm_kw, run_kw = VARIANTS[n]
        for a in accels:
            jobs.append((f"v{i}_a{a:g}", "quick", dict(pm_kw), {**run_kw, "speed_scale": speed, "accel_scale": float(a)},
                         str(Path(out) / "sweep")))
    res = _run_all(printer_path, jobs)
    out_d = {}
    for i, n in enumerate(names):
        ok = [a for a in accels if res[f"v{i}_a{a:g}"]["ok"]]
        # highest acceleration below the first failure (a pass above a failure is luck, not margin)
        first_fail = next((a for a in accels if not res[f"v{i}_a{a:g}"]["ok"]), None)
        safe = [a for a in ok if first_fail is None or a < first_fail]
        best = max(safe) if safe else None
        out_d[n] = {"nominal": nominal[n], "max_passing_accel_scale": best,
                    "first_failure": ({"accel_scale": first_fail, "errors": sorted(set(res[f"v{i}_a{first_fail:g}"]["errors"]))}
                                      if first_fail is not None else None),
                    "time_at_max_s": res[f"v{i}_a{best:g}"]["print_time_s"] if best else None}
    return out_d


SENS = {  # parameter -> (low, high) as (PrinterMap overrides, run overrides)
    "rail friction": (({"friction_n": {"x": 1.0, "y": 1.5, "z": 2.5}}, {}), ({"friction_n": {"x": 3.0, "y": 4.5, "z": 7.5}}, {})),
    "extruder lag": (({"extruder_lag_s": 0.015}, {}), ({"extruder_lag_s": 0.045}, {})),
    "stepper damping": (({"damping_ratio": 0.125}, {}), ({"damping_ratio": 0.375}, {})),
    "belt/frame damping": (({"spring_damping_ratio": 0.025}, {}), ({"spring_damping_ratio": 0.075}, {})),
    "belt stiffness": (({"belt_ea_n": 11000.0}, {}), ({"belt_ea_n": 33000.0}, {})),
    "motor torque": (({}, {"torque_scale": 0.5}), ({}, {"torque_scale": 1.5})),
    "toolhead mass": (({}, {"mass_extra": {"x": -0.1, "y": -0.1}}), ({}, {"mass_extra": {"x": 0.2, "y": 0.2}})),
}


def sensitivity(printer_path, out):
    """Move each assumed parameter -50% / +50% and see how much each output moves."""
    jobs = [("base", "quick", {}, {}, str(out))]
    for i, (lo, hi) in enumerate(SENS.values()):
        jobs += [(f"p{i}_lo", "quick", dict(lo[0]), dict(lo[1]), str(out)),
                 (f"p{i}_hi", "quick", dict(hi[0]), dict(hi[1]), str(out))]
    res = _run_all(printer_path, jobs)
    base = res["base"]

    def outs(r):
        return {"rms_lag_y_mm": r["rms_lag_mm"][1], "worst_lag_y_mm": r["worst_lag_mm"][1],
                "max_bulge_mm": r["max_bulge_mm"], "outline_offset_mm": r["outline_offset_mm"],
                "outline_iou_min": r["outline_iou_min"]}

    b = outs(base)
    rows = {}
    for i, name in enumerate(SENS):
        lo, hi = outs(res[f"p{i}_lo"]), outs(res[f"p{i}_hi"])
        rows[name] = {k: {"low": lo[k], "high": hi[k], "swing": round(abs(hi[k] - lo[k]), 4)} for k in b}
        rows[name]["verdict_changes"] = (res[f"p{i}_lo"]["ok"] != base["ok"]) or (res[f"p{i}_hi"]["ok"] != base["ok"])
    return {"base": b, "base_ok": base["ok"], "parameters": rows}


def run_everything(printer_path, out) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    res, t0 = {}, time.time()
    for name, fn in (("benchmark", lambda: benchmark_suite(printer_path, out / "bench")),
                     ("envelope", lambda: envelope(printer_path, out / "envelope")),
                     ("coverage", lambda: coverage(printer_path, out / "coverage")),
                     ("robustness", lambda: scenarios(printer_path, out / "robust", SCENARIOS)),
                     ("faults", lambda: scenarios(printer_path, out / "faults", {k: v[:2] for k, v in FAULTS.items()})),
                     ("variants", lambda: variants(printer_path, out / "variants")),
                     ("sensitivity", lambda: sensitivity(printer_path, out / "sens"))):
        t = time.time()
        res[name] = fn()
        res.setdefault("seconds", {})[name] = round(time.time() - t, 1)
        (out / "evaluation.json").write_text(json.dumps(res, indent=1, default=float))
    res["seconds"]["total"] = round(time.time() - t0, 1)
    (out / "evaluation.json").write_text(json.dumps(res, indent=1, default=float))
    return res
