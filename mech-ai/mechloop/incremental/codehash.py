"""Which code and data decide a verifier's result, as one hash: cached results die when any of it changes.

code_hash(module) = SHA-256 over
  - the source of the module and of every mechloop module it imports, transitively (static: every `import` and
    `from ... import` anywhere in the file, including the ones inside functions),
  - every data file in the mechloop package (vendor/catalogue records, fitted parameters, shop profiles, supplier rule
    data: *.json, *.csv, *.yaml, *.txt ...), whichever verifier reads them (conservative),
  - the versions of the external libraries a result rests on (build123d, OCP, gmsh, trimesh, numpy, scipy, mujoco ...)
    and the CalculiX binary's identity (path, size, mtime).
"""
from __future__ import annotations

import ast
import hashlib
from functools import lru_cache
from pathlib import Path

PKG_ROOT = Path(__file__).resolve().parent.parent          # .../mechloop
PKG = "mechloop"
EXTERNAL = ("build123d", "cadquery-ocp", "OCP", "gmsh", "trimesh", "numpy", "scipy", "mujoco", "python-fcl",
            "meshio", "bd_warehouse")
DATA_SUFFIXES_SKIP = (".py", ".pyc", ".pyo")


def _module_file(mod: str) -> Path | None:
    if not (mod == PKG or mod.startswith(PKG + ".")):
        return None
    rel = mod.split(".")[1:]
    p = PKG_ROOT.joinpath(*rel)
    if (p / "__init__.py").exists():
        return p / "__init__.py"
    if p.with_suffix(".py").exists():
        return p.with_suffix(".py")
    return None


def _module_name(path: Path) -> str:
    rel = path.relative_to(PKG_ROOT.parent).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


@lru_cache(maxsize=None)
def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(), str(path))
    me = _module_name(path)
    pkg = me if path.name == "__init__.py" else me.rsplit(".", 1)[0]
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = pkg.split(".")
                base = base[:len(base) - (node.level - 1)] if node.level > 1 else base
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            out.add(mod)
            for a in node.names:          # `from . import electrical` imports a submodule
                out.add(f"{mod}.{a.name}")
    # every parent package's __init__ runs on import too
    full = set()
    for m in out:
        bits = m.split(".")
        for i in range(1, len(bits) + 1):
            full.add(".".join(bits[:i]))
    return tuple(sorted(m for m in full if m == PKG or m.startswith(PKG + ".")))


@lru_cache(maxsize=None)
def module_closure(mod: str) -> tuple[str, ...]:
    """Every mechloop source file `mod` can run, by static import analysis (sorted relative paths)."""
    seen: set[Path] = set()
    todo = [mod, PKG]
    while todo:
        m = todo.pop()
        f = _module_file(m)
        if f is None or f in seen:
            continue
        seen.add(f)
        todo.extend(_imports(f))
    return tuple(sorted(str(p.relative_to(PKG_ROOT)) for p in seen))


@lru_cache(maxsize=None)
def data_files() -> tuple[str, ...]:
    return tuple(sorted(str(f.relative_to(PKG_ROOT)) for f in PKG_ROOT.rglob("*")
                        if f.is_file() and "__pycache__" not in f.parts and f.suffix not in DATA_SUFFIXES_SKIP))


@lru_cache(maxsize=None)
def _file_hash(rel: str) -> str:
    return hashlib.sha256((PKG_ROOT / rel).read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def externals() -> str:
    from importlib import metadata

    vs = []
    for n in EXTERNAL:
        try:
            vs.append(f"{n}={metadata.version(n)}")
        except Exception:
            vs.append(f"{n}=?")
    import shutil

    ccx = shutil.which("ccx")
    if ccx:
        st = Path(ccx).resolve().stat()
        vs.append(f"ccx={Path(ccx).resolve()}:{st.st_size}:{int(st.st_mtime)}")
    return ";".join(vs)


@lru_cache(maxsize=None)
def code_hash(*modules: str) -> str:
    """Hash of the code and data behind the given mechloop modules (e.g. "mechloop.verifiers.fea")."""
    files = sorted({f for m in modules for f in module_closure(m)})
    h = hashlib.sha256()
    for rel in files + list(data_files()):
        h.update(rel.encode())
        h.update(_file_hash(rel).encode())
    h.update(externals().encode())
    return h.hexdigest()[:24]


def clear() -> None:
    """Forget every cached hash (tests that edit source files)."""
    for f in (_imports, module_closure, data_files, _file_hash, externals, code_hash):
        f.cache_clear()
