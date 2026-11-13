"""Run verifiers on a design and write the loop artefacts."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path

from .model import Design
from .report import Report, VerifierResult

ORDER = ["geometry", "interference", "ratings", "motion", "assemblability", "fea"]


def load_design(path: str | Path) -> Design:
    path = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(f"design_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "build"):
        raise AttributeError(f"{path.name} must define build() -> mechloop.Design")
    d = mod.build()
    if not isinstance(d, Design):
        raise TypeError("build() must return a mechloop.Design")
    return d


def _verifiers():
    from .verifiers.assemblability import verify_assemblability
    from .verifiers.fea import verify_fea
    from .verifiers.geometry import verify_geometry
    from .verifiers.interference import verify_interference
    from .verifiers.motion import verify_motion
    from .verifiers.ratings import verify_ratings

    return {"geometry": verify_geometry, "interference": verify_interference, "ratings": verify_ratings,
            "motion": verify_motion, "assemblability": verify_assemblability, "fea": verify_fea}


def verify(design: Design, only: list[str] | None = None, stop_on_geometry_error: bool = True) -> Report:
    """Cheap checks first. If geometry itself is broken, later verifiers are
    reported as NOT RUN (never as a pass)."""
    rep = Report(design.name)
    vs = _verifiers()
    blocked = False
    for name in ORDER:
        if only and name not in only:
            continue
        if blocked:
            rep.results.append(VerifierResult(name, skipped="not run: geometry errors must be fixed first"))
            continue
        if name == "assemblability" and any(
                f.code == "interference" for r0 in rep.results for f in r0.findings):
            rep.results.append(VerifierResult(
                name, skipped="not run: parts that overlap cannot be sequenced; fix interference first"))
            continue
        try:
            res = vs[name](design)
        except Exception as e:
            res = VerifierResult(name)
            res.add("error", "verifier_crashed", f"{name} crashed: {type(e).__name__}: {e}",
                    trace=traceback.format_exc()[-600:])
        rep.results.append(res)
        if name == "geometry" and not res.ok and stop_on_geometry_error and any(
                f.code in ("no_solid", "invalid_brep", "zero_volume", "empty_design", "unknown_material")
                for f in res.findings):
            blocked = True
    if not only or "requirements" in only:
        from .verifiers.geometry import verify_requirements

        rep.results.append(verify_requirements(design, {r.verifier: r.metrics for r in rep.results}))
    return rep


def run(path: str | Path, out_root: str | Path = "out", only=None, render: bool = True) -> Report:
    t0 = time.time()
    try:
        design = load_design(path)
    except Exception as e:
        rep = Report(Path(path).stem)
        res = VerifierResult("build")
        res.add("error", "build_failed", f"Design script failed: {type(e).__name__}: {e}",
                trace=traceback.format_exc()[-900:])
        rep.results.append(res)
        return rep
    rep = verify(design, only)
    t_ver = time.time()
    out = Path(out_root) / design.name
    out.mkdir(parents=True, exist_ok=True)
    if render:
        try:
            from .render import render_motion, render_views

            rep.artifacts["views"] = str(render_views(design, out / "views.png"))
            sim = next((r.artifacts_sim for r in rep.results if r.artifacts_sim is not None), None)
            if sim is None:  # no simulated program: show each joint sweeping its range instead
                gif = render_motion(design, out / "motion.gif")
                if gif:
                    rep.artifacts["motion"] = str(gif)
            if sim is not None:
                from .render import render_simulation

                rep.artifacts["simulation"] = str(render_simulation(design, sim, out / "simulation.gif"))
        except Exception as e:
            rep.artifacts["render_error"] = f"{type(e).__name__}: {e}"
    try:
        from build123d import Compound, export_step

        comp = Compound(children=[_labelled(c) for c in design.components], label=design.name)
        export_step(comp, str(out / f"{design.name}.step"))
        rep.artifacts["step"] = str(out / f"{design.name}.step")
    except Exception as e:
        rep.artifacts["step_error"] = f"{type(e).__name__}: {e}"
    # loop history: one line per run, so progress across iterations is visible
    hist = out / "history.jsonl"
    n = sum(1 for _ in open(hist)) + 1 if hist.exists() else 1
    rep.partial = bool(only)
    entry = {"iteration": n, "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "ok": rep.ok and not only, "partial": bool(only),
             "verifiers": {r.verifier: ("not run" if r.skipped.startswith("not run") else "skipped" if r.skipped
                                        else "pass" if r.ok else "FAIL") for r in rep.results},
             "errors": [f"{f.verifier}:{f.code}" for f in rep.errors()],
             "seconds": round(time.time() - t0, 1)}
    with open(hist, "a") as f:
        f.write(json.dumps(entry) + "\n")
    rep.artifacts["iteration"] = n
    rep.artifacts["seconds"] = {"verify": round(t_ver - t0, 1), "render_and_export": round(time.time() - t_ver, 1)}
    (out / "report.json").write_text(rep.to_json(max_findings=500))
    return rep


def _labelled(c):
    import copy

    s = copy.copy(c.shape)
    s.label = c.name
    return s
