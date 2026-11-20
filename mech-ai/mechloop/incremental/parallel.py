"""Run verifiers (and FEA cases) in parallel processes, within a CPU and a memory budget.

Each job is a forked copy of the verify process taken after the design is built and fingerprinted (copy-on-write: the
design is not rebuilt), so it sees exactly the design a serial run sees. Jobs:
  - one per verifier, except FEA, which is split into one job per case (load / assembly / thermal / modal / bed support),
  - the order follows deps.py: printing after FEA (it reads FEA's stiffness), assemblability after interference (it is
    not run when parts overlap); if geometry finds a part with no valid solid, every other result is replaced by
    "not run", as in a serial run.
A job starts when a CPU slot is free (--jobs, default the CPU count up to 4), at most MAX_HEAVY heavy solver cases run at
once (a CalculiX assembly / thermal / bed-support solve takes about 6.5 GB), the memory the running jobs are expected to
add stays within the budget, and the machine has that much memory available right now (so a heavy job does not start
beside another program's). Expected memory per job comes from the previous run's measured peaks
(verify_cache/profile.json), else from defaults. Longest jobs start first.

Results are the same as a serial run's: each job runs the same code on the same design; their findings and metrics are
put back in the serial order.
"""
from __future__ import annotations

import json
import os
import pickle
import resource
import sys
import tempfile
import time
import traceback
from pathlib import Path

MAX_HEAVY = 2
RESERVE_MB = 800                     # left free beside the jobs
DEFAULT_BUDGET_MB = 12500            # of the 15 GB container
HEAVY_MB, LIGHT_FEA_MB, VERIFIER_MB = 6500, 2000, 1500
DEFAULT_SECONDS = {"fea:heavy": 400, "fea:light": 40, "geometry": 140, "interference": 20, "tolerance": 200,
                   "manufacture": 40, "practice": 60, "ratings": 10, "motion": 300, "subsystems": 90, "electrical": 10,
                   "assemblability": 250, "printing": 80}


def mem_available_mb() -> int:
    """Memory usable now on this machine, MB: MemAvailable and the container's cgroup limit (mechloop.resources)."""
    from ..resources import mem_available_mb as m

    return m()


def _rss_mb() -> int:
    try:
        with open("/proc/self/statm") as f:
            return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") // (1 << 20)
    except OSError:
        return 0


class Job:
    def __init__(self, name: str, kind: str, heavy: bool = False, unit=None, index: int | None = None):
        self.name, self.kind, self.heavy, self.unit, self.index = name, kind, heavy, unit, index
        self.est_mb = HEAVY_MB if heavy else (LIGHT_FEA_MB if kind == "fea" else VERIFIER_MB)
        self.est_s = DEFAULT_SECONDS.get(name, DEFAULT_SECONDS["fea:heavy" if heavy else "fea:light"] if kind == "fea" else 60)


def _child(job: Job, fn, out_path: str, session) -> None:
    """In the forked process: run the job, write {"value", "deps", "manifest", "delta", "peak"} to out_path."""
    from .. import resources

    resources.in_child()          # the parent holds (and releases) the heavy-solver lock
    code = 0
    try:
        if session is not None:      # only this job's own decisions, stats and memo entries go back
            session.decisions, session.stats, session._new, session._used = {}, {}, {}, {}
        t0 = time.time()
        rss0 = _rss_mb()
        value, deps, manifest = fn()
        payload = {"value": value, "deps": deps, "manifest": manifest, "seconds": time.time() - t0,
                   "delta": session.export_delta() if session is not None else None,
                   "peak": {"peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
                            "rss_at_start_mb": rss0,
                            "solver_peak_mb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024}}
        try:
            data = pickle.dumps(payload, protocol=4)
        except Exception as e:      # an unpicklable value: send what can be sent
            payload["value"] = ("unpicklable", f"{type(e).__name__}: {e}")
            data = pickle.dumps(payload, protocol=4)
        with open(out_path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(out_path + ".tmp", out_path)
    except BaseException:
        code = 3
        try:
            with open(out_path + ".err", "w") as f:
                f.write(traceback.format_exc()[-2000:])
        except Exception:
            pass
    finally:
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os._exit(code)


class Scheduler:
    def __init__(self, jobs: int, budget_mb: int, profile: dict | None = None, log=None):
        self.slots = max(1, jobs)
        self.budget = budget_mb
        self.profile = profile or {}
        self.running: dict[int, tuple] = {}     # pid -> (job, out_path, t0, rss_at_fork)
        from ..resources import workdir

        self.tmp = str(workdir("jobs"))
        self.log = log or (lambda msg: None)
        self.waiting_since: float | None = None

    def estimate(self, job: Job) -> None:
        p = self.profile.get(job.name)
        if p:
            job.est_mb = max(300, int(1.15 * p.get("extra_mb", job.est_mb)))
            job.est_s = p.get("seconds", job.est_s)

    def projected_free_mb(self) -> int:
        """Memory free now (whoever uses the rest: other agents' jobs count) less what our running jobs are still
        expected to add (their estimate minus what they hold already)."""
        from ..resources import tree_rss_mb

        free = mem_available_mb()
        for pid, (j, _out, _t0, rss_fork) in self.running.items():
            grown = max(0, tree_rss_mb(pid) - rss_fork)
            free -= max(0, j.est_mb - grown)
        return free

    def can_start(self, job: Job) -> bool:
        if len(self.running) >= self.slots:
            return False
        if job.heavy and sum(1 for j, *_ in self.running.values() if j.heavy) >= MAX_HEAVY:
            return False
        used = sum(j.est_mb for j, *_ in self.running.values())
        if self.running and used + job.est_mb > self.budget:
            return False
        free = self.projected_free_mb()
        if free < job.est_mb + RESERVE_MB:
            self.waiting_since = self.waiting_since or time.time()
            waited = time.time() - self.waiting_since
            told = getattr(self, "_told", {})
            if time.time() - told.get(job.name, -1e9) > 300:      # at most every 5 min per job
                told[job.name] = time.time()
                self._told = told
                self.log(f"waiting to start {job.name}: needs about {job.est_mb + RESERVE_MB} MB, {max(free, 0)} MB free "
                         f"(other processes on the machine count); waited {waited / 60:.0f} min")
            # a large solver case never starts without its memory; a light job may, after 30 min with none of ours running
            if job.heavy or self.running or waited < 1800:
                return False
            self.log(f"starting {job.name} with only {free} MB free (waited 30 min)")
        self.waiting_since = None
        return True

    def stop_all(self) -> None:
        """Ask every running job to stop (they clean up their scratch folders) and wait for them."""
        import signal

        for pid in list(self.running):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
        t_end = time.time() + 30
        while self.running and time.time() < t_end:
            for pid in list(self.running):
                try:
                    done, _ = os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    done = pid
                if done:
                    self.running.pop(pid, None)
            time.sleep(0.2)
        for pid in list(self.running):
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except OSError:
                pass
        self.running.clear()

    def close(self) -> None:
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def start(self, job: Job, fn, session) -> None:
        out = os.path.join(self.tmp, f"{job.name}.{len(os.listdir(self.tmp))}.pkl")
        rss = _rss_mb()
        sys.stdout.flush()
        sys.stderr.flush()
        pid = os.fork()
        if pid == 0:
            _child(job, fn, out, session)
        self.running[pid] = (job, out, time.time(), rss)

    def wait_one(self, timeout: float = 0.5):
        """[(job, payload or None, error text)] for jobs that ended."""
        done = []
        t_end = time.time() + timeout
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                pid, status = 0, 0
            if pid and pid in self.running:
                job, out, t0, rss = self.running.pop(pid)
                payload, err = None, ""
                if os.path.exists(out):
                    with open(out, "rb") as f:
                        payload = pickle.load(f)
                    os.unlink(out)
                    pk = payload["peak"]       # what the job added on top of the forked copy: its own growth and its solver
                    pk["extra_mb"] = max(0, pk["peak_rss_mb"] - pk["rss_at_start_mb"]) + pk["solver_peak_mb"]
                    payload["wall_s"] = time.time() - t0
                else:
                    sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
                    err = f"worker process died ({'signal ' + str(sig) if sig else 'exit ' + str(os.WEXITSTATUS(status))})"
                    if os.path.exists(out + ".err"):
                        err += ": " + open(out + ".err").read()[-600:]
                done.append((job, payload, err))
                continue
            if done or time.time() >= t_end or not self.running:
                return done
            time.sleep(0.05)


def load_profile(cache_root: Path) -> dict:
    try:
        return json.loads((cache_root / "profile.json").read_text())
    except Exception:
        return {}


def save_profile(cache_root: Path, prof: dict) -> None:
    try:
        cache_root.mkdir(parents=True, exist_ok=True)
        old = load_profile(cache_root)
        old.update(prof)
        (cache_root / "profile.json").write_text(json.dumps(old, indent=1, sort_keys=True))
    except Exception:
        pass
