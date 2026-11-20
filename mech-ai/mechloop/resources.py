"""Machine resources shared by every mechloop process (and every agent) on this machine.

- mem_available_mb(): memory that can really be used now: the smaller of the kernel's MemAvailable and, for each
  memory cgroup this process is in that has a limit, limit - (usage - reclaimable page cache). The container's limit is
  a cgroup limit, and the OOM killer acts on it, not on the machine's free memory.
- workdir(kind): a scratch folder /tmp/mechloop_<kind>_<pid>_XXXX. The pid in the name lets sweep_stale() remove the
  folders of processes that are gone (a killed run leaves its solver files behind: gigabytes for a bed-support case).
  Folders of the old form (no pid) are removed when untouched for STALE_HOURS.
- heavy_lock(): a machine-wide lock (flock on /tmp/mechloop_heavy.lock) held while CalculiX solves run, so that only
  one verify / score / tune runs its large finite-element cases at a time across all agents. A verify holds it for its
  whole FEA phase (its own worker processes share it: at most 2 large cases at once, within the memory budget); any
  other process that starts CalculiX takes it for that solve. Waiting is the default (the holder and the wait are
  reported on stderr); MECHLOOP_NO_WAIT=1 (`mechloop verify --no-wait`) makes a busy lock an error instead. The lock
  goes away by itself when its holder dies.
"""
from __future__ import annotations

import contextlib
import fcntl
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

TMP = Path(tempfile.gettempdir())
STALE_HOURS = 6.0
LOCK_PATH = Path(os.environ.get("MECHLOOP_HEAVY_LOCK", str(TMP / "mechloop_heavy.lock")))
_PID_DIR = re.compile(r"^mechloop_[a-z0-9]+_(\d+)_")


# ------------------------------------------------------------------------------------------------ memory
def _cgroup_dirs() -> list[Path]:
    out = []
    try:
        lines = Path("/proc/self/cgroup").read_text().splitlines()
    except OSError:
        return out
    for line in lines:
        _, ctrl, path = line.split(":", 2)
        if ctrl == "memory":                       # cgroup v1
            base = Path("/sys/fs/cgroup/memory")
        elif ctrl == "" and Path("/sys/fs/cgroup/cgroup.controllers").exists():
            base = Path("/sys/fs/cgroup")          # cgroup v2 (unified)
        else:
            continue
        p = base / path.lstrip("/")
        while True:
            out.append(p)
            if p == base:
                break
            p = p.parent
    return out


def _cgroup_available_mb() -> int | None:
    best = None
    for d in _cgroup_dirs():
        try:
            if (d / "memory.limit_in_bytes").exists():                       # v1
                limit = int((d / "memory.limit_in_bytes").read_text())
                usage = int((d / "memory.usage_in_bytes").read_text())
                key = "total_inactive_file"
            elif (d / "memory.max").exists():                                # v2
                raw = (d / "memory.max").read_text().strip()
                if raw == "max":
                    continue
                limit, usage = int(raw), int((d / "memory.current").read_text())
                key = "inactive_file"
            else:
                continue
            if limit >= 1 << 60:
                continue
            stat = dict(l.split() for l in (d / "memory.stat").read_text().splitlines() if " " in l)
            cache = int(stat.get(key, stat.get("inactive_file", 0)))
            free = (limit - (usage - cache)) // (1 << 20)
            best = free if best is None else min(best, free)
        except (OSError, ValueError):
            continue
    return best


def mem_available_mb() -> int:
    avail = 1 << 30
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    avail = int(line.split()[1]) // 1024
                    break
    except OSError:
        pass
    cg = _cgroup_available_mb()
    return min(avail, cg) if cg is not None else avail


def tree_rss_mb(pid: int) -> int:
    """Resident memory of a process and all its descendants, MB."""
    kids: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    page = os.sysconf("SC_PAGE_SIZE")
    for d in os.listdir("/proc"):
        if not d.isdigit():
            continue
        try:
            st = Path(f"/proc/{d}/stat").read_text()
            ppid = int(st.rsplit(")", 1)[1].split()[1])
            kids.setdefault(ppid, []).append(int(d))
            rss[int(d)] = int(Path(f"/proc/{d}/statm").read_text().split()[1]) * page
        except (OSError, ValueError, IndexError):
            continue
    total, todo = 0, [pid]
    while todo:
        p = todo.pop()
        total += rss.get(p, 0)
        todo.extend(kids.get(p, []))
    return total // (1 << 20)


# ------------------------------------------------------------------------------------------- scratch folders
def workdir(kind: str) -> Path:
    """A new scratch folder for one solve, named with this process's pid (see sweep_stale)."""
    return Path(tempfile.mkdtemp(prefix=f"mechloop_{kind}_{os.getpid()}_"))


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:       # a zombie holds nothing
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def sweep_stale(root: Path = TMP) -> dict:
    """Remove scratch folders left by mechloop processes that are gone. {"removed": n, "freed_mb": x}."""
    removed, freed = 0, 0
    now = time.time()
    try:
        entries = list(os.scandir(root))
    except OSError:
        return {"removed": 0, "freed_mb": 0}
    for e in entries:
        if not e.name.startswith("mechloop_") or not e.is_dir(follow_symlinks=False):
            continue
        m = _PID_DIR.match(e.name)
        if m:
            if _alive(int(m.group(1))):
                continue
        else:
            try:
                newest = max([e.stat().st_mtime] + [f.stat().st_mtime for f in os.scandir(e.path)])
            except OSError:
                continue
            if now - newest < STALE_HOURS * 3600:
                continue
        try:
            size = sum(f.stat().st_size for f in Path(e.path).rglob("*") if f.is_file())
        except OSError:
            size = 0
        shutil.rmtree(e.path, ignore_errors=True)
        if not os.path.exists(e.path):
            removed += 1
            freed += size
    return {"removed": removed, "freed_mb": freed // (1 << 20)}


# ---------------------------------------------------------------------------------------------- heavy lock
class HeavyLockBusy(RuntimeError):
    pass


_HELD = False         # this process (or the verify it was forked from) holds the lock
_FD = None


def holder() -> str:
    try:
        return (LOCK_PATH.with_suffix(".info")).read_text().strip()
    except OSError:
        return "unknown"


def no_wait() -> bool:
    return os.environ.get("MECHLOOP_NO_WAIT", "") not in ("", "0")


def acquire(label: str = "", wait: bool | None = None) -> None:
    """Take the machine-wide heavy-solver lock (re-entrant within this process and its forked workers)."""
    global _HELD, _FD
    if _HELD:
        return
    wait = (not no_wait()) if wait is None else wait
    fd = os.open(str(LOCK_PATH), os.O_RDWR | os.O_CREAT, 0o666)
    t0, told = time.time(), 0.0
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            if not wait:
                os.close(fd)
                raise HeavyLockBusy(f"another heavy FEA run holds {LOCK_PATH} ({holder()})")
            if time.time() - told > 300:
                print(f"mechloop: waiting for the heavy-solver lock {LOCK_PATH}, held by {holder()}; waited "
                      f"{(time.time() - t0) / 60:.0f} min so far (MECHLOOP_NO_WAIT=1 / --no-wait to fail instead)",
                      file=sys.stderr, flush=True)
                told = time.time()
            time.sleep(2.0)
    _FD, _HELD = fd, True
    try:
        LOCK_PATH.with_suffix(".info").write_text(
            f"pid {os.getpid()} since {time.strftime('%H:%M:%S')}: {label or ' '.join(sys.argv)[:200]}\n")
    except OSError:
        pass
    if time.time() - t0 > 5:
        print(f"mechloop: heavy-solver lock taken after {(time.time() - t0) / 60:.1f} min", file=sys.stderr, flush=True)


def release() -> None:
    global _HELD, _FD
    if _FD is not None:
        try:
            fcntl.flock(_FD, fcntl.LOCK_UN)       # releases it for the forked workers that share the descriptor too
            os.close(_FD)
        except OSError:
            pass
    _FD, _HELD = None, False


@contextlib.contextmanager
def heavy_lock(label: str = ""):
    """Hold the lock for the block (a no-op when this process already holds it)."""
    if _HELD:
        yield
        return
    acquire(label)
    try:
        yield
    finally:
        release()


def in_child() -> None:
    """In a forked worker: the parent holds the lock (and releases it); never release it from here."""
    global _FD
    _FD = None
