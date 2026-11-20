"""The code and data a result actually rests on, recorded while it is computed (narrow invalidation).

A cached result carries a manifest: {relative path: content hash} of
  - every mechloop source file with a function that RAN while the result was computed (recorded with sys.monitoring:
    one PY_START event per code object, then disabled, so the overhead is a few microseconds per function),
  - the modules those files import from, at module level, transitively, and the modules their functions import
    (one level): module-level constants and re-exports (`from .interference import VOL_TOL`) live there,
  - every data file read by those files (an open() hook attributes each read to the mechloop module that made it,
    whenever it happened: at import, on first use, or now), plus the data files in the same folders,
  - the vendor CAD folder (names, sizes, times) when the vendor-CAD checks ran,
  - the versions of the external libraries and the CalculiX binary.
The result is reused only while every file in its manifest is unchanged. An edit elsewhere in mechloop (another
verifier, the sourcing data, a new module) no longer invalidates it. Anything not recorded cannot be in the manifest
only if it did not run, was not imported by what ran and was not read by it.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import io
import os
import sys
import threading
from functools import lru_cache
from pathlib import Path

from .codehash import PKG_ROOT, _module_file, _module_name, externals

REPO_ROOT = PKG_ROOT.parent
_PKG = str(PKG_ROOT) + os.sep
_SKIP_DIRS = ("__pycache__",)
_LOCK = threading.Lock()

# ------------------------------------------------------------------------------------------------ data reads
DATA_READS: dict[str, set[str]] = {}       # mechloop source file (abs) -> data files (abs) it opened
_orig_open = builtins.open
_installed = False


def _attribute(path: str) -> None:
    for rec in list(_ACTIVE):
        rec.data.add(path)
    f = sys._getframe(2)
    while f is not None:
        fn = f.f_code.co_filename
        if fn.startswith(_PKG) and "incremental" not in fn:
            with _LOCK:
                DATA_READS.setdefault(fn, set()).add(path)
            return
        f = f.f_back


def _open_hook(file, mode="r", *a, **kw):
    try:
        if isinstance(file, (str, os.PathLike)) and "r" in str(mode) and "+" not in str(mode):
            p = os.path.abspath(os.fspath(file))
            if p.startswith(str(REPO_ROOT)) and not p.endswith((".py", ".pyc")):
                _attribute(p)
    except Exception:
        pass
    return _orig_open(file, mode, *a, **kw)


def install() -> None:
    """Hook open() (builtins and io: pathlib's read_text goes through io.open)."""
    global _installed
    if _installed:
        return
    builtins.open = _open_hook
    io.open = _open_hook
    _installed = True


# --------------------------------------------------------------------------------------------- code recording
_ACTIVE: list["Recording"] = []
_TOOL = None


def _tool_id():
    global _TOOL
    if _TOOL is None:
        mon = sys.monitoring
        for i in (4, 3, 5, 2, 1, 0):
            if mon.get_tool(i) is None:
                mon.use_tool_id(i, "mechloop-incremental")
                mon.register_callback(i, mon.events.PY_START, _on_start)
                _TOOL = i
                break
        else:
            _TOOL = -1
    return _TOOL


def _on_start(code, offset):
    fn = code.co_filename
    if fn.startswith(_PKG):
        for rec in _ACTIVE:
            rec.files.add(fn)
    return sys.monitoring.DISABLE


class Recording:
    """with Recording() as rec: ...  -> rec.manifest() after the block (or rec.unknown when recording was impossible)."""

    def __init__(self):
        self.files: set[str] = set()
        self.data: set[str] = set()
        self.extra: dict[str, str] = {}      # manifests of reused sub-results
        self.unknown = ""

    def __enter__(self):
        tid = _tool_id()
        if tid < 0:
            self.unknown = "no free sys.monitoring tool id"
            return self
        install()
        _ACTIVE.append(self)
        sys.monitoring.set_events(tid, sys.monitoring.events.PY_START)
        sys.monitoring.restart_events()        # re-arm code objects that already ran (they run again for this result)
        return self

    def __exit__(self, *exc):
        if self in _ACTIVE:
            _ACTIVE.remove(self)
        if not _ACTIVE and _TOOL is not None and _TOOL >= 0:
            sys.monitoring.set_events(_TOOL, 0)
        return False

    def add_manifest(self, m: dict | None) -> None:
        """A sub-result reused from the cache: what it rested on counts for this result too."""
        if not m:
            return
        if m.get("unknown"):
            self.unknown = self.unknown or m["unknown"]
        self.extra.update(m.get("files", {}))

    def manifest(self) -> dict:
        if self.unknown:
            return {"unknown": self.unknown}
        files = code_closure(frozenset(self.files))
        data = set(self.data)
        for f in files:
            data |= DATA_READS.get(str(PKG_ROOT / f), set())
        data_rel = set(_same_dir_data(files))
        for p in data:
            try:
                data_rel.add(os.path.relpath(p, REPO_ROOT))
            except ValueError:
                pass
        out = {}
        for rel in sorted(files):
            out["mechloop/" + rel] = file_hash(str(PKG_ROOT / rel))
        for rel in sorted(data_rel):
            out[rel] = file_hash(str(REPO_ROOT / rel))
        if "parts/vendor_cad.py" in files:
            out["<vendor_cad dir>"] = dir_stat(str(REPO_ROOT / "vendor_cad"))
        out["<externals>"] = hashlib.sha256(externals().encode()).hexdigest()[:16]
        out.update(self.extra)
        return {"files": out}


def push_manifest(m: dict | None) -> None:
    """Add a reused result's manifest to every recording in progress."""
    for rec in _ACTIVE:
        rec.add_manifest(m)


# ---------------------------------------------------------------------------------------- static helpers
def _imports_of(path: Path):
    """(module-level imports, function-level imports) of a mechloop file, as mechloop module names."""
    tree = ast.parse(path.read_text(), str(path))
    me = _module_name(path)
    pkg = me if path.name == "__init__.py" else me.rsplit(".", 1)[0]

    def names(n):
        if isinstance(n, ast.Import):
            return [a.name for a in n.names]
        if n.level:
            base = pkg.split(".")
            base = base[:len(base) - (n.level - 1)] if n.level > 1 else base
            mod = ".".join(base + ([n.module] if n.module else []))
        else:
            mod = n.module or ""
        return [mod] + [f"{mod}.{a.name}" for a in n.names]

    top, inner = set(), set()
    module_level = set()
    for node in tree.body:
        for n in ast.walk(node) if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else [node]:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                module_level.add(id(n))
                top.update(names(n))
        if isinstance(node, ast.ClassDef):           # imports in a class body run at import time
            for n in node.body:
                if isinstance(n, (ast.Import, ast.ImportFrom)):
                    module_level.add(id(n))
                    top.update(names(n))
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)) and id(n) not in module_level:
            inner.update(names(n))

    def full(ms):
        out = set()
        for m in ms:
            b = m.split(".")
            out.update(".".join(b[:i]) for i in range(1, len(b) + 1))
        return frozenset(m for m in out if m == "mechloop" or m.startswith("mechloop."))
    return full(top), full(inner)


@lru_cache(maxsize=None)
def _imports_cached(path: str, mtime: int):
    return _imports_of(Path(path))


def _imports(path: Path):
    return _imports_cached(str(path), path.stat().st_mtime_ns)


def code_closure(executed: frozenset) -> list[str]:
    """Executed files + the modules their functions import (one level) + module-level imports, transitively."""
    start: set[Path] = set()
    for f in executed:
        p = Path(f)
        if p.exists():
            start.add(p)
            for m in _imports(p)[1]:
                mf = _module_file(m)
                if mf is not None:
                    start.add(mf)
    seen: set[Path] = set()
    todo = list(start) + [p for p in (_module_file("mechloop"),) if p]
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        for m in _imports(p)[0]:
            mf = _module_file(m)
            if mf is not None and mf not in seen:
                todo.append(mf)
    return sorted(str(p.relative_to(PKG_ROOT)) for p in seen)


def _same_dir_data(files) -> list[str]:
    out = []
    for d in sorted({str(Path(f).parent) for f in files}):
        dd = PKG_ROOT / d
        for p in dd.iterdir() if dd.is_dir() else ():
            if p.is_file() and p.suffix not in (".py", ".pyc", ".pyo"):
                out.append(os.path.relpath(p, REPO_ROOT))
    return out


_FILE_HASH: dict[str, tuple] = {}


def file_hash(path: str) -> str:
    """Content hash (first 16 hex) of a file, cached on (mtime, size); files over 4 MB by (size, mtime); 'missing'."""
    try:
        st = os.stat(path)
    except OSError:
        return "missing"
    key = (st.st_mtime_ns, st.st_size)
    hit = _FILE_HASH.get(path)
    if hit and hit[0] == key:
        return hit[1]
    if st.st_size > 4 * 1024 * 1024:
        h = f"stat:{st.st_size}:{st.st_mtime_ns}"
    else:
        with _orig_open(path, "rb") as f:
            h = hashlib.sha256(f.read()).hexdigest()[:16]
    _FILE_HASH[path] = (key, h)
    return h


DIR_SKIP = (".cache", "staging", "__pycache__")       # derived caches and incoming files nothing reads from yet


def dir_stat(path: str) -> str:
    """Names, sizes and times of the files under a folder (the vendor CAD), leaving out DIR_SKIP folders."""
    h = hashlib.sha256()
    for root, dirs, files in os.walk(path):
        dirs[:] = sorted(d for d in dirs if d not in DIR_SKIP)
        for n in sorted(files):
            try:
                st = os.stat(os.path.join(root, n))
            except OSError:
                continue
            h.update(f"{os.path.relpath(os.path.join(root, n), path)}:{st.st_size}:{st.st_mtime_ns}\n".encode())
    return h.hexdigest()[:16]


def still_valid(manifest: dict | None) -> tuple[bool, str]:
    """(True, "") when every file in the manifest is as it was; else (False, the first that changed)."""
    if not manifest or manifest.get("unknown") or "files" not in manifest:
        return False, f"code not recorded ({(manifest or {}).get('unknown', 'no manifest')})"
    for rel, h in manifest["files"].items():
        if rel == "<externals>":
            cur = hashlib.sha256(externals().encode()).hexdigest()[:16]
        elif rel == "<vendor_cad dir>":
            cur = dir_stat(str(REPO_ROOT / "vendor_cad"))
        else:
            cur = file_hash(str(REPO_ROOT / rel))
        if cur != h:
            return False, f"{rel} changed"
    return True, ""
