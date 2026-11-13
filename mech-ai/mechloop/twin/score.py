"""A scorecard for a printer design: numbers an agent can try to improve, as opposed to
thresholds it only has to clear. Everything comes from the design's own CAD and simulations."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..runner import load_design, verify
from . import printer_map_for
from .evals import _run_all

ACCELS = (1, 1.5, 2, 3, 4, 5, 6, 8, 10)


def score(design_path, out_root="out", speed: float = 2.0) -> dict:
    t0 = time.time()
    design = load_design(design_path)
    if not design.printer:
        return {"error": "design does not declare design.printer"}
    rep = verify(design, only=["geometry", "ratings", "fea"])
    metrics = {r.verifier: r.metrics for r in rep.results}
    pm = printer_map_for(design, metrics)
    pm_kw = {"belt_ea_n": pm.belt_ea_n, "struct_stiffness": pm.struct_stiffness,
             **{k: getattr(pm, k) for k in ("x", "y", "z", "bed")}}
    out = Path(out_root) / design.name / "score"
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
        "moving_mass_kg": moving,
        "total_mass_kg": round(design.total_mass(), 3),
        "bom_cost_usd": metrics.get("ratings", {}).get("bom_cost_usd_estimate"),
        "first_failure": ({"accel_mm_s2": first_fail * a_nom, "errors": sorted(set(res[f"a{first_fail:g}"]["errors"]))}
                          if first_fail else None),
        "static_errors": [f"{f.verifier}:{f.code}" for f in rep.errors()],
        "seconds": round(time.time() - t0, 1),
    }
    hist = Path(out_root) / design.name / "scores.jsonl"
    hist.parent.mkdir(parents=True, exist_ok=True)
    with open(hist, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), **s}, default=float) + "\n")
    return s


def _dyn(run_dir: Path, key: str):
    try:
        return json.loads((run_dir / "print_report.json").read_text())["dynamics"].get(key)
    except Exception:
        return None
