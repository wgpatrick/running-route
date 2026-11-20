"""Result cache for incremental verification: out/<design>/verify_cache/.

Layout:
  verify_cache/manifest.json            fingerprints of the last run that wrote the cache (what changed since)
  verify_cache/results/<verifier>/<slot>.pkl
                                        one verifier's findings, metrics, dependencies, manifest and source run
  verify_cache/fea_cases/<slot>.pkl     one FEA case (load / modal / assembly / thermal / bed support)
  verify_cache/<verifier>.parts.pkl     per-part results inside a verifier (manufacture: each custom part's DFM)
  verify_cache/<verifier>.<table>.pkl   memoised geometric kernels, keyed by the shapes' fingerprints and the kernel's
                                        parameters: interference.pairs (overlap volume and place, gap of each pair),
                                        assemblability.overlap_memo (distances, overlaps along removal paths and of the
                                        driver), motion.overlap (overlap at each relative pose)

Every stored result is found by its slot (the verifier, FEA case or part it belongs to, plus the earlier metrics it
reads) and holds up to a few entries, each with its recorded dependencies (fingerprints of what it read from the
design) and the manifest of the code and data that produced it; the session uses the newest entry whose dependencies
and manifest are unchanged. Memo tables are keyed on the shapes' fingerprints and the kernel's own code.
"""
from __future__ import annotations

import contextlib
import json
import os
import pickle
import tempfile
import time
from pathlib import Path


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
