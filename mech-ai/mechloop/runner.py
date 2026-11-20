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

try:        # attribute every data file a verifier reads, from the start (mechloop.incremental.coderec)
    from .incremental import coderec as _coderec

    _coderec.install()
except Exception:       # pragma: no cover
    pass

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


def prepare_for_workers() -> bool:
    """Make this process safe to fork into worker processes: the CAD kernel's own thread pool must not have started
    threads (a forked child has none of them and would wait for them forever), so it is limited to the calling thread.
    Call before any CAD work. True when forking is safe."""
    try:
        from OCP.OSD import OSD_ThreadPool

        return not OSD_ThreadPool.DefaultPool_s(1).HasThreads()
    except Exception:
        return False


def _fork_safe() -> bool:
    try:
        from OCP.OSD import OSD_ThreadPool

        return not OSD_ThreadPool.DefaultPool_s().HasThreads()
    except Exception:
        return False


GEOMETRY_FATAL = ("no_solid", "invalid_brep", "zero_volume", "empty_design", "unknown_material")


def verify(design: Design, only: list[str] | None = None, stop_on_geometry_error: bool = True, session=None,
           jobs: int = 1, memory_budget_mb: int | None = None) -> Report:
    """Cheap checks first. If geometry itself is broken, later verifiers are
    reported as NOT RUN (never as a pass).

    session: a mechloop.incremental.Session for a tiered run (results reused from verify_cache/ where what a verifier
    read is unchanged); None runs everything, as always. jobs > 1 (with a session): verifiers and FEA cases run in
    parallel processes within a memory budget (mechloop.incremental.parallel); the report is the same."""
    if session is not None:
        from . import incremental

        incremental.CURRENT = session
        try:
            if jobs > 1 and _fork_safe():
                return _verify_parallel(design, only, stop_on_geometry_error, session, jobs, memory_budget_mb)
            rep = _verify(design, only, stop_on_geometry_error, session)
            if jobs > 1:
                rep.profile["parallel"] = {"jobs": 1, "note": "ran serially: the CAD kernel's thread pool had already "
                                           "started threads in this process, so it cannot be forked safely (start the verify "
                                           "from the command line, or call runner.prepare_for_workers() before building)"}
            return rep
        finally:
            incremental.CURRENT = None
    return _verify(design, only, stop_on_geometry_error, None)


def _call(vs, design, name, metrics_so_far):
    try:
        if name == "printing":  # the twin reads this run's FEA stiffness
            return vs[name](design, metrics_so_far)
        return vs[name](design)
    except Exception as e:
        res = VerifierResult(name)
        res.add("error", "verifier_crashed", f"{name} crashed: {type(e).__name__}: {e}",
                trace=traceback.format_exc()[-600:])
        return res


def _peak() -> dict:
    import resource

    return {"process_peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
            "solver_peak_mb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024}


def _verify(design: Design, only, stop_on_geometry_error: bool, session) -> Report:
    rep = Report(design.name)
    vs = _verifiers()
    blocked = False
    prof = rep.profile.setdefault("verifiers", {})
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
            return _call(vs, design, name, {r.verifier: r.metrics for r in rep.results})

        t0 = time.time()
        res = call() if session is None else _incremental_step(session, design, name, call, rep)
        prof[name] = {"seconds": round(time.time() - t0, 2), **_peak(), "worker": "main",
                      **({"reused": True} if res.reused else {})}
        rep.results.append(res)
        if name == "geometry" and not res.ok and stop_on_geometry_error and any(
                f.code in GEOMETRY_FATAL for f in res.findings):
            blocked = True
    _finish(design, only, session, rep)
    return rep


def _finish(design, only, session, rep) -> None:
    if not only or "requirements" in only:
        from .verifiers.geometry import verify_requirements

        rep.results.append(verify_requirements(design, {r.verifier: r.metrics for r in rep.results}))
        if session is not None:
            session.decisions["requirements"] = {"status": "ran", "why": "always re-run (reads every verifier's metrics)"}
    if session is not None:
        session.finish()
        rep.incremental = session.section()
        fea = session.decisions.get("fea", {})
        if fea.get("cases_run") or fea.get("cases_reused"):
            rep.profile["fea_cases"] = {**{k: {"seconds": v} for k, v in (fea.get("cases_run") or {}).items()},
                                        **{k: {"reused_from": v} for k, v in (fea.get("cases_reused") or {}).items()}}


def _reuse_or_stale(session, name: str, upstream: dict):
    """(VerifierResult or None, slot, why): the stored result when nothing it read changed; a NOT RUN result in the
    quick tier for a stale non-quick verifier; else None (it must run)."""
    from .incremental import QUICK

    try:
        slot, why = session.slot(name, upstream)
    except Exception as e:          # an input that cannot be fingerprinted: run it
        slot, why = None, f"no cache key ({type(e).__name__}: {e}): re-run"
    dec = session.decisions.setdefault(name, {})
    if session.tier != "full":
        hit = session.lookup(name, slot)
        if hit is not None:
            dec.update({"status": "reused", "from_run": hit.get("run"), "original_seconds": round(hit.get("seconds", 0.0), 1)})
            return (VerifierResult(name, findings=list(hit["findings"]), metrics=hit["metrics"], skipped=hit["skipped"],
                                   seconds=0.0, reused=dict(hit.get("run") or {}), artifacts_sim=hit.get("artifacts_sim")),
                    slot, why)
        if session.tier == "quick" and name not in QUICK:
            dec.update({"status": "not run", "why": "what it read changed since the stored result (or none stored); not a "
                                                    "quick-tier check: run --tier affected or full"})
            return VerifierResult(name, skipped="not run: stale (its inputs changed) and not part of --tier quick"), slot, why
    return None, slot, why


def _run_tracked(session, design, name, call):
    """Run a verifier recording what it reads and what code runs: (result, deps, manifest)."""
    from .incremental import coderec
    from .incremental.recorder import tracking

    session.verifier = name
    try:
        with tracking(design) as reads, coderec.Recording() as rec:
            res = call()
    finally:
        session.verifier = None
    return res, session.deps_of(reads), rec.manifest()


def _record_ran(session, name, slot, why, res, deps, manifest) -> None:
    stored = session.store(name, slot, res, deps, manifest)
    dec = session.decisions.setdefault(name, {})
    dec.update({"status": "ran", "why": ("full tier: nothing reused" if session.tier == "full"
                                        else dec.get("stored_result_invalid") or why or "nothing stored yet"),
                "stored": stored})
    if session.stats.get(name):
        dec["reused_within"] = session.stats[name]


def _incremental_step(session, design: Design, name: str, call, rep: Report) -> VerifierResult:
    """One verifier under a tier: reuse the stored result when nothing it read changed, else run it (or, in the quick
    tier, report it NOT RUN when it is not a quick check)."""
    upstream = {r.verifier: r.metrics for r in rep.results}
    res, slot, why = _reuse_or_stale(session, name, upstream)
    if res is not None:
        return res
    res, deps, manifest = _run_tracked(session, design, name, call)
    _record_ran(session, name, slot, why, res, deps, manifest)
    return res


def _verify_parallel(design: Design, only, stop_on_geometry_error: bool, session, jobs: int, budget_mb) -> Report:
    """The same verify, with verifiers and FEA cases as parallel processes (mechloop.incremental.parallel)."""
    from .incremental import coderec, parallel
    from .incremental.recorder import tracking
    from .verifiers.fea import fea_units, run_unit

    rep = Report(design.name)
    vs = _verifiers()
    t_start = time.time()
    names = [n for n in ORDER if not only or n in only]
    results: dict[str, VerifierResult] = {}
    prof = rep.profile.setdefault("verifiers", {})
    sched = parallel.Scheduler(jobs, budget_mb or parallel.DEFAULT_BUDGET_MB,
                               parallel.load_profile(session.cache.root),
                               log=lambda m: print(f"mechloop: {m}", file=sys.stderr, flush=True))
    learned: dict = {}
    pending = list(names)
    ready: list = []
    slots: dict = {}
    fea_units_list, fea_parts, fea_t0, fea_ready = None, {}, None, None

    def metrics_now():
        return {n: results[n].metrics for n in ORDER if n in results}

    def deps_done(n):
        if n == "printing":
            return "fea" in results or "fea" not in names
        if n == "assemblability":
            return "interference" in results or "interference" not in names
        return True

    def verifier_fn(n):
        def fn():
            res, deps, manifest = _run_tracked(session, design, n, lambda: _call(vs, design, n, metrics_now()))
            stored = session.store(n, slots[n][0], res, deps, manifest)
            return {"res": res, "stored": stored}, deps, manifest
        return fn

    def unit_fn(u):
        def fn():
            r = VerifierResult("fea")
            session.verifier = "fea"
            with tracking(design) as reads, coderec.Recording() as rec:
                run_unit(design, r, u)
            return {"findings": r.findings, "metrics": r.metrics}, session.deps_of(reads), rec.manifest()
        return fn

    def promote():
        nonlocal fea_units_list, fea_ready
        for n in list(pending):
            if not deps_done(n):
                continue
            pending.remove(n)
            if n == "assemblability" and any(f.code == "interference" for f in results.get("interference", VerifierResult("x")).findings):
                results[n] = VerifierResult(n, skipped="not run: parts that overlap cannot be sequenced; fix interference first")
                continue
            res, slot, why = _reuse_or_stale(session, n, metrics_now())
            slots[n] = (slot, why)
            if res is not None:
                results[n] = res
                prof[n] = {"seconds": 0.0, "worker": "main", **({"reused": True} if res.reused else {})}
                continue
            if n == "fea":
                ready_res, units = fea_units(design)
                if ready_res is not None:
                    results[n] = ready_res
                    continue
                fea_units_list = units
                for k, u in enumerate(units):
                    job = parallel.Job(f"fea:{u.label}", "fea", heavy=u.heavy, unit=u, index=k)
                    sched.estimate(job)
                    ready.append(job)
                continue
            job = parallel.Job(n, "verifier")
            sched.estimate(job)
            ready.append(job)
        ready.sort(key=lambda j: -j.est_s)

    from . import incremental as _inc
    from . import resources

    lock_told = [0.0]
    lock_failed: dict = {}

    def lock_ok(job) -> bool:
        """An FEA case that has to solve needs the machine-wide heavy-solver lock (held until FEA is done)."""
        if job.kind != "fea" or resources._HELD or _inc.fea_case_reusable(job.unit.kind, job.unit.case):
            return True
        try:
            resources.acquire(f"mechloop verify {design.name} (FEA phase)", wait=False)
            return True
        except resources.HeavyLockBusy as e:
            if resources.no_wait():
                lock_failed[job.index] = e
                return True
            if time.time() - lock_told[0] > 300:
                lock_told[0] = time.time()
                print(f"mechloop: FEA waits for the heavy-solver lock, held by {resources.holder()} (the other verifiers go "
                      f"on; --no-wait to fail instead)", file=sys.stderr, flush=True)
            return False

    def fea_done(job, val):
        nonlocal fea_t0
        fea_parts[job.index] = val
        if len(fea_parts) == len(fea_units_list):
            r = VerifierResult("fea")
            for k in range(len(fea_units_list)):
                r.findings.extend(fea_parts[k]["findings"])
                r.metrics.update(fea_parts[k]["metrics"])
            r.seconds = time.time() - (fea_t0 or time.time())
            results["fea"] = r
            prof["fea"] = {"seconds": round(r.seconds, 2), "worker": "processes (one per case)"}
            dec = session.decisions.setdefault("fea", {})
            all_reused = not dec.get("cases_run")
            dec.update({"status": "reused (every case)" if all_reused else "ran",
                        "why": "full tier: nothing reused" if session.tier == "full" else
                               (slots["fea"][1] or "cases run where what they read changed")})
            resources.release()

    import signal

    def on_term(signum, frame):
        raise SystemExit(128 + signum)

    old_term = signal.signal(signal.SIGTERM, on_term) if hasattr(signal, "SIGTERM") else None
    try:
        promote()
        while pending or ready or sched.running:
            started = True
            while started:
                started = False
                for job in list(ready):
                    if sched.can_start(job) and lock_ok(job):
                        ready.remove(job)
                        if job.kind == "fea" and fea_t0 is None:
                            fea_t0 = time.time()
                        if job.kind == "fea" and job.index in lock_failed:
                            r = VerifierResult("fea")
                            job.unit.on_error(r, lock_failed[job.index])
                            fea_done(job, {"findings": r.findings, "metrics": {}})
                        else:
                            sched.start(job, unit_fn(job.unit) if job.kind == "fea" else verifier_fn(job.name), session)
                        started = True
                        break
            _drain(sched, session, learned, rep, prof, results, slots, fea_done)
            promote()
    except BaseException:
        sched.stop_all()
        raise
    finally:
        resources.release()
        sched.close()
        if old_term is not None:
            signal.signal(signal.SIGTERM, old_term)
    parallel.save_profile(session.cache.root, learned)
    geo = results.get("geometry")
    blocked = bool(geo is not None and stop_on_geometry_error and not geo.ok
                   and any(f.code in GEOMETRY_FATAL for f in geo.findings))
    for n in names:
        if blocked and n != "geometry":
            rep.results.append(VerifierResult(n, skipped="not run: geometry errors must be fixed first"))
        else:
            rep.results.append(results[n])
    rep.profile["parallel"] = {"jobs": jobs, "memory_budget_mb": sched.budget, "max_heavy_solver_cases": parallel.MAX_HEAVY,
                               "wall_seconds": round(time.time() - t_start, 1)}
    _finish(design, only, session, rep)
    return rep


def _drain(sched, session, learned, rep, prof, results, slots, fea_done) -> None:
    """Collect the jobs that ended."""
    for job, payload, err in sched.wait_one(0.5):
        if payload is not None and payload.get("delta"):
            session.merge_delta(payload["delta"])
        peak = (payload or {}).get("peak", {})
        info = {"seconds": round((payload or {}).get("wall_s", 0.0), 2), **{k: v for k, v in peak.items()}, "worker": "process"}
        learned[job.name] = {"extra_mb": peak.get("extra_mb", job.est_mb), "seconds": round((payload or {}).get("seconds", 0.0), 1)}
        if job.kind == "fea":
            if payload is None or isinstance(payload["value"], tuple):
                r = VerifierResult("fea")
                job.unit.on_error(r, RuntimeError(err or str(payload["value"])))
                val = {"findings": r.findings, "metrics": {}}
            else:
                val = payload["value"]
            rep.profile.setdefault("fea_case_processes", {})[job.unit.label] = info
            fea_done(job, val)
        else:
            if payload is None or isinstance(payload["value"], tuple):
                res = VerifierResult(job.name)
                res.add("error", "verifier_crashed", f"{job.name} crashed: {err or payload['value'][1]}")
                stored = False
            else:
                res, stored = payload["value"]["res"], payload["value"]["stored"]
            results[job.name] = res
            prof[job.name] = info
            slot, why = slots[job.name]
            dec = session.decisions.setdefault(job.name, {})
            dec.update({"status": "ran", "why": ("full tier: nothing reused" if session.tier == "full"
                                                else dec.get("stored_result_invalid") or why or "nothing stored yet"),
                        "stored": stored})
            if session.stats.get(job.name):
                dec["reused_within"] = session.stats[job.name]


def run(path: str | Path, out_root: str | Path = "out", only=None, render: bool | None = True, tier: str | None = None,
        use_cache: bool = True, jobs: int | None = None, step: bool | None = None, memory_budget_mb: int | None = None) -> Report:
    """Build and verify a design and write the loop artefacts. tier None: a full verify (results are stored for a later
    tiered run unless use_cache is False); "quick" / "affected" / "full": see mechloop.incremental.

    jobs: parallel processes (None: the CPU count up to 4 for a tiered run, 1 for a plain verify; 1 = serial).
    render / step: the renders and the STEP export of the whole machine. None: on for a plain verify, the full tier and
    a design marked release; off for the quick and affected tiers (they are slow and not checks)."""
    t0 = time.time()
    steps: dict = {}
    import signal
    import threading

    from . import resources

    swept = resources.sweep_stale()       # scratch folders of runs that were killed
    if swept["removed"]:
        steps["stale_scratch_removed"] = swept
    if threading.current_thread() is threading.main_thread():
        def _term(signum, frame):         # a stopped verify still cleans up (scratch folders, solver processes, lock)
            raise SystemExit(128 + signum)

        signal.signal(signal.SIGTERM, _term)
    if jobs is None:
        import os

        jobs = min(4, os.cpu_count() or 1) if tier else 1
    if jobs > 1 and use_cache:
        prepare_for_workers()
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
    steps["load_design_seconds"] = round(time.time() - t0, 1)
    if session is not None:
        steps["fingerprint_seconds"] = session.fps.seconds
    release_tier = tier in (None, "full") or bool(getattr(design, "release", False))
    render = release_tier if render is None else render
    step = release_tier if step is None else step
    if session is None:
        jobs = 1
    t1 = time.time()
    rep = verify(design, only, session=session, jobs=jobs, memory_budget_mb=memory_budget_mb)
    steps["verify_seconds"] = round(time.time() - t1, 1)
    if session is not None and not session.explicit:
        rep.incremental = {}        # a plain verify reports exactly as before (the cache was only written)
    from .report import provenance_of

    rep.provenance = provenance_of(path)
    t_ver = time.time()
    out.mkdir(parents=True, exist_ok=True)
    if render:
        t2 = time.time()
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
        steps["render_seconds"] = round(time.time() - t2, 1)
    else:
        steps["render"] = "not run (--render to ask for it)"
    if step:
        t2 = time.time()
        try:
            from build123d import Compound, export_step

            comp = Compound(children=[_labelled(c) for c in design.components], label=design.name)
            export_step(comp, str(out / f"{design.name}.step"))
            rep.artifacts["step"] = str(out / f"{design.name}.step")
        except Exception as e:
            rep.artifacts["step_error"] = f"{type(e).__name__}: {e}"
        steps["step_export_seconds"] = round(time.time() - t2, 1)
    else:
        steps["step_export"] = "not run (--step to ask for it)"
    if not only or "manufacture" in only:  # flat profiles of the cut parts, as a laser shop wants them
        t2 = time.time()
        try:
            from .verifiers.manufacture import export_flat_patterns

            dxf = export_flat_patterns(design, out / "dxf")
            if dxf:
                rep.artifacts["dxf"] = dxf
        except Exception as e:
            rep.artifacts["dxf_error"] = f"{type(e).__name__}: {e}"
        steps["dxf_seconds"] = round(time.time() - t2, 1)
    steps["total_seconds"] = round(time.time() - t0, 1)
    steps["peak_rss_mb_main_process"] = _peak()["process_peak_rss_mb"]
    rep.profile["steps"] = steps
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
