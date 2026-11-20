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

ORDER = ["geometry", "interference", "tolerance", "manufacture", "practice", "ratings", "motion", "subsystems", "electrical", "assemblability", "fea", "printing"]


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

    from .verifiers.printing import verify_printing

    from .tolerance import verify_tolerance
    from .verifiers.manufacture import verify_manufacture
    from .verifiers.practice import verify_practice
    from .verifiers.subsystems import verify_subsystems
    from .verifiers.electrical import verify_electrical

    return {"geometry": verify_geometry, "interference": verify_interference, "tolerance": verify_tolerance,
            "manufacture": verify_manufacture, "practice": verify_practice, "ratings": verify_ratings,
            "motion": verify_motion, "subsystems": verify_subsystems, "electrical": verify_electrical, "assemblability": verify_assemblability, "fea": verify_fea,
            "printing": verify_printing}


def verify(design: Design, only: list[str] | None = None, stop_on_geometry_error: bool = True, session=None) -> Report:
    """Cheap checks first. If geometry itself is broken, later verifiers are
    reported as NOT RUN (never as a pass).

    session: a mechloop.incremental.Session for a tiered run (results reused from verify_cache/ where the inputs a
    verifier reads are unchanged); None runs everything, as always."""
    if session is not None:
        from . import incremental

        incremental.CURRENT = session
        try:
            return _verify(design, only, stop_on_geometry_error, session)
        finally:
            incremental.CURRENT = None
    return _verify(design, only, stop_on_geometry_error, None)


def _verify(design: Design, only, stop_on_geometry_error: bool, session) -> Report:
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

        def call(name=name):
            try:
                if name == "printing":  # the twin reads this run's FEA stiffness
                    return vs[name](design, {r.verifier: r.metrics for r in rep.results})
                return vs[name](design)
            except Exception as e:
                res = VerifierResult(name)
                res.add("error", "verifier_crashed", f"{name} crashed: {type(e).__name__}: {e}",
                        trace=traceback.format_exc()[-600:])
                return res

        res = call() if session is None else _incremental_step(session, design, name, call, rep)
        rep.results.append(res)
        if name == "geometry" and not res.ok and stop_on_geometry_error and any(
                f.code in ("no_solid", "invalid_brep", "zero_volume", "empty_design", "unknown_material")
                for f in res.findings):
            blocked = True
    if not only or "requirements" in only:
        from .verifiers.geometry import verify_requirements

        rep.results.append(verify_requirements(design, {r.verifier: r.metrics for r in rep.results}))
        if session is not None:
            session.decisions["requirements"] = {"status": "ran", "why": "always re-run (reads every verifier's metrics)"}
    if session is not None:
        session.finish()
        rep.incremental = session.section()
    return rep


def _incremental_step(session, design: Design, name: str, call, rep: Report) -> VerifierResult:
    """One verifier under a tier: reuse the stored result when nothing it reads changed, else run it (or, in the quick
    tier, report it NOT RUN when it is not a quick check)."""
    from .incremental import QUICK
    from .incremental.recorder import recording

    upstream = {r.verifier: r.metrics for r in rep.results}
    try:
        key, why = session.key(name, upstream)
    except Exception as e:          # an input that cannot be fingerprinted: run it
        key, why = None, f"no cache key ({type(e).__name__}: {e}): re-run"
    dec = session.decisions.setdefault(name, {})
    if session.tier != "full":
        hit = session.lookup(name, key)
        if hit is not None:
            res = VerifierResult(name, findings=list(hit["findings"]), metrics=hit["metrics"], skipped=hit["skipped"],
                                 seconds=0.0, reused=dict(hit.get("run") or {}), artifacts_sim=hit.get("artifacts_sim"))
            dec.update({"status": "reused", "from_run": hit.get("run"), "original_seconds": round(hit.get("seconds", 0.0), 1)})
            return res
        if session.tier == "quick" and name not in QUICK:
            dec.update({"status": "not run", "why": "inputs changed since the stored result (or none stored); not a quick-tier "
                                                    "check: run --tier affected or full"})
            return VerifierResult(name, skipped="not run: stale (its inputs changed) and not part of --tier quick")
    session.verifier = name
    with recording(design) as reads:
        res = call()
    session.verifier = None
    from .incremental.deps import ALL_FIELDS, DEPS

    d = DEPS.get(name)
    undeclared = sorted(reads - set(d.fields)) if d is not None and d.fields != ALL_FIELDS else []
    stored = session.store(name, key, res, reads_ok=not undeclared)
    dec.update({"status": "ran", "why": ("full tier: nothing reused" if session.tier == "full"
                                        else why or "inputs changed since the stored result (or none stored)"),
                "stored": stored, **({"undeclared_reads": undeclared} if undeclared else {})})
    if session.stats.get(name):
        dec["reused_within"] = session.stats[name]
    return res


def run(path: str | Path, out_root: str | Path = "out", only=None, render: bool = True, tier: str | None = None,
        use_cache: bool = True) -> Report:
    """Build and verify a design and write the loop artefacts. tier None: a full verify (results are stored for a later
    tiered run unless use_cache is False); "quick" / "affected" / "full": see mechloop.incremental."""
    t0 = time.time()
    try:
        design = load_design(path)
    except Exception as e:
        rep = Report(Path(path).stem)
        res = VerifierResult("build")
        res.add("error", "build_failed", f"Design script failed: {type(e).__name__}: {e}",
                trace=traceback.format_exc()[-900:])
        rep.results.append(res)
        from .report import provenance_of

        rep.provenance = provenance_of(path)
        return rep
    session = None
    out = Path(out_root) / design.name
    if use_cache or tier:
        try:
            from .incremental import Session

            hist0 = out / "history.jsonl"
            n0 = sum(1 for _ in open(hist0)) + 1 if hist0.exists() else 1
            session = Session(design, out, tier=tier or "full", use_cache=use_cache, iteration=n0,
                              explicit_tier=tier is not None)
        except Exception as e:      # the cache must never stop a verify: run without it
            if tier:
                raise
            session = None
            print(f"WARNING: incremental cache disabled for this run: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
    rep = verify(design, only, session=session)
    if session is not None and not session.explicit:
        rep.incremental = {}        # a plain verify reports exactly as before (the cache was only written)
    from .report import provenance_of

    rep.provenance = provenance_of(path)
    t_ver = time.time()
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
    if not only or "manufacture" in only:  # flat profiles of the cut parts, as a laser shop wants them
        try:
            from .verifiers.manufacture import export_flat_patterns

            dxf = export_flat_patterns(design, out / "dxf")
            if dxf:
                rep.artifacts["dxf"] = dxf
        except Exception as e:
            rep.artifacts["dxf_error"] = f"{type(e).__name__}: {e}"
    # loop history: one line per run, so progress across iterations is visible
    hist = out / "history.jsonl"
    n = sum(1 for _ in open(hist)) + 1 if hist.exists() else 1
    stale = [r.verifier for r in rep.results if r.skipped.startswith("not run: stale")]
    partial = bool(only) or bool(stale)
    rep.partial = partial
    entry = {"iteration": n, "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "ok": rep.ok and not partial, "partial": partial,
             **({"tier": rep.incremental.get("tier"), "reused": rep.incremental.get("reused")} if rep.incremental else {}),
             "verifiers": {r.verifier: ("not run" if r.skipped.startswith("not run") else "skipped" if r.skipped
                                        else "pass" if r.ok else "FAIL") for r in rep.results},
             "errors": [f"{f.verifier}:{f.code}" for f in rep.errors()],
             "seconds": round(time.time() - t0, 1)}
    with open(hist, "a") as f:
        f.write(json.dumps(entry) + "\n")
    rep.artifacts["iteration"] = n
    rep.artifacts["seconds"] = {"verify": round(t_ver - t0, 1), "render_and_export": round(time.time() - t_ver, 1)}
    # a partial run must not replace the last full report: the twin and the viewer read their figures from it
    # (a quick tier that left stale verifiers NOT RUN is partial too)
    (out / ("report_partial.json" if partial else "report.json")).write_text(rep.to_json(max_findings=500))
    return rep


def _labelled(c):
    import copy

    s = copy.copy(c.detail if getattr(c, "detail", None) is not None else c.shape)   # the detailed (vendor) CAD where there is one
    s.label = c.name
    return s
