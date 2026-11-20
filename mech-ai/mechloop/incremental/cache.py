"""Result cache for incremental verification: out/<design>/verify_cache/.

Layout:
  verify_cache/manifest.json            fingerprints of the last run that wrote the cache (what changed since)
  verify_cache/results/<verifier>/<key>.pkl
                                        one verifier's findings, metrics and the run it came from
  verify_cache/fea_cases/<key>.pkl      one FEA case (load / modal / assembly / thermal / bed support)
  verify_cache/<verifier>.<table>.pkl   memoised geometric kernels, keyed by the shapes' fingerprints and the kernel's
                                        parameters: interference.pairs (overlap volume and place, gap of each pair),
                                        assemblability.overlap_memo (distances, overlaps along removal paths and of the
                                        driver), motion.overlap (overlap at each relative pose)

Every key is a digest of what decides the result: the verifier's code hash (its module and imports, the package's data
files, library versions), the fingerprints of the parts and design fields it reads, and the metrics of earlier
verifiers it reads. A key that cannot be formed (an input with no stable fingerprint) is None: always re-run.
Entries are written atomically (temp file + rename), so a killed run leaves no half-written entry; an entry that
fails to load is treated as a miss.
"""
from __future__ import annotations

import contextlib
import json
import os
import pickle
import tempfile
import time
from pathlib import Path

from .codehash import code_hash
from .deps import ALL_FIELDS, DEPS
from .fingerprint import FP_VERSION, Fingerprints, design_field_names, digest, is_unstable, value_fp

KEEP_PER_VERIFIER = 4       # newest entries kept per verifier / per case directory


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _load(path: Path):
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


class ResultCache:
    def __init__(self, root: Path, read: bool = True, write: bool = True):
        self.root = Path(root)
        self.read, self.write = read, write

    # ---------------------------------------------------------------- verifier results and FEA cases
    def get(self, kind: str, key: str | None):
        if not self.read or not key:
            return None
        e = _load(self.root / kind / f"{key}.pkl")
        if e is None or e.get("key") != key:
            return None
        return e

    def put(self, kind: str, key: str | None, entry: dict) -> bool:
        if not self.write or not key:
            return False
        entry = {**entry, "key": key, "stored": time.strftime("%Y-%m-%dT%H:%M:%S")}
        try:
            data = pickle.dumps(entry, protocol=4)
        except Exception:
            return False     # something in the result does not pickle: not cached, re-run next time
        _atomic_write(self.root / kind / f"{key}.pkl", data)
        self._prune(self.root / kind)
        return True

    def _prune(self, d: Path) -> None:
        try:
            files = sorted(d.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            return
        limit = KEEP_PER_VERIFIER * (40 if d.name == "fea_cases" else 1)
        for p in files[limit:]:
            with contextlib.suppress(OSError):
                p.unlink()

    # ------------------------------------------------------------------- memo tables (pairs, overlaps)
    def load_table(self, name: str) -> dict:
        if not self.read:
            return {}
        t = _load(self.root / f"{name}.pkl")
        return t if isinstance(t, dict) else {}

    def save_table(self, name: str, table: dict, used: set | None = None) -> None:
        """Keep the entries this run used (and new ones); stale ones go, so the table does not grow without end."""
        if not self.write:
            return
        if used is not None:
            table = {k: v for k, v in table.items() if k in used}
        _atomic_write(self.root / f"{name}.pkl", pickle.dumps(table, protocol=4))

    # ------------------------------------------------------------------------------------- manifest
    def manifest(self) -> dict | None:
        try:
            return json.loads((self.root / "manifest.json").read_text())
        except Exception:
            return None

    def save_manifest(self, m: dict) -> None:
        if self.write:
            _atomic_write(self.root / "manifest.json", json.dumps(m, indent=0, sort_keys=True).encode())


def verifier_key(name: str, fps: Fingerprints, design, upstream_metrics: dict | None = None) -> tuple[str | None, str]:
    """(key, why there is none). The key of one verifier's whole result on this design."""
    d = DEPS.get(name)
    if d is None:
        return None, "no dependency declaration: always re-run"
    if d.granularity == "always":
        return None, "always re-run (cheap; reads the results of the others)"
    parts = fps.parts_digest() if d.parts == "all" else "no-parts"
    fields = design_field_names(design) if d.fields == ALL_FIELDS else list(d.fields)
    fd = fps.fields_digest(fields)
    up = value_fp({u: (upstream_metrics or {}).get(u) for u in d.upstream}) if d.upstream else "no-upstream"
    for what, v in (("parts", parts), ("fields", fd), ("upstream metrics", up)):
        if is_unstable(v):
            return None, f"{what} have no stable fingerprint ({v[9:80]}): re-run"
    code = code_hash(d.module, *d.extra_modules)
    return digest(FP_VERSION, "verifier", name, code, parts, fd, up), ""
