"""Incremental verification: fingerprints, dependency declarations, a result cache and three tiers.

    mechloop verify designs/x.py --tier quick      geometry, interference (changed pairs), manufacture, practice, ratings;
                                                   any other verifier is reused when its inputs are unchanged, else
                                                   reported NOT RUN (stale) -- the run is then partial
    mechloop verify designs/x.py --tier affected   every verifier whose inputs changed re-runs (FEA case by case,
                                                   interference pair by pair); the rest is reused
    mechloop verify designs/x.py --tier full       everything re-runs, nothing is reused (results are still stored);
                                                   required before freezing / release, and the tier any design marked
                                                   `release = True` gets whatever tier is asked
    mechloop verify designs/x.py                   (no tier) a full verify, exactly as before; results are stored so a
                                                   later `--tier affected` can reuse them
    --no-cache                                     nothing read, nothing stored

A reused result is the stored one, unchanged (findings and metrics), and says where it came from: the report's
`incremental` section lists for each verifier "ran" / "reused" (with the iteration and time of the run that produced
it) / "not run", and the summary line of a reused verifier ends in "[reused from run N]".

Session holds one run's state; the module functions below are the hooks the verifiers call (no-ops when no session
is active, so a verifier run on its own behaves exactly as before).
"""
from __future__ import annotations

import time
from pathlib import Path

from .cache import ResultCache, verifier_key
from .codehash import code_hash
from .deps import DEPS, QUICK
from .fingerprint import FP_VERSION, digest, diff, fingerprint as fingerprint_design, is_unstable, shape_fp, value_fp

TIERS = ("quick", "affected", "full")
CURRENT: "Session | None" = None


class Session:
    def __init__(self, design, out_dir: Path, tier: str = "full", use_cache: bool = True, iteration: int | None = None,
                 explicit_tier: bool = True):
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}; choose from {TIERS}")
        self.requested_tier = tier
        self.release = bool(getattr(design, "release", False))
        self.notes: list[str] = []
        if self.release and tier != "full":
            self.notes.append(f"design is marked release: tier '{tier}' was asked, a full verify was run (no reuse)")
            tier = "full"
        self.tier = tier
        self.explicit = explicit_tier
        self.design = design
        self.cache = ResultCache(Path(out_dir) / "verify_cache", read=use_cache and tier != "full", write=use_cache)
        self.use_cache = use_cache
        self.fps = fingerprint_design(design)
        self.changes = diff(self.cache.manifest() if use_cache else None, self.fps)
        self.run = {"iteration": iteration, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "tier": tier}
        self.decisions: dict[str, dict] = {}
        self.verifier: str | None = None
        self._tables: dict[str, dict] = {}
        self._used: dict[str, set] = {}
        self.stats: dict[str, dict] = {}

    # ----------------------------------------------------------------------------------------- verifier level
    def key(self, name: str, upstream: dict | None = None):
        return verifier_key(name, self.fps, self.design, upstream)

    def lookup(self, name: str, key):
        return self.cache.get(f"results/{name}", key)

    def store(self, name: str, key, res, reads_ok: bool) -> bool:
        if not reads_ok or key is None:
            return False
        if any(f.code in ("verifier_crashed",) for f in res.findings):
            return False       # a crash may be the machine's (memory, a killed solver): never reuse it
        return self.cache.put(f"results/{name}", key, {
            "verifier": name, "findings": list(res.findings), "metrics": res.metrics, "skipped": res.skipped,
            "seconds": res.seconds, "run": dict(self.run)})

    # ------------------------------------------------------------------------------------------ memo tables
    def table(self, name: str) -> dict:
        if name not in self._tables:
            self._tables[name] = self.cache.load_table(name)
            self._used[name] = set()
        return self._tables[name]

    def mark_used(self, name: str, key) -> None:
        self._used.setdefault(name, set()).add(key)

    def stat(self, what: str, n: int = 1) -> None:
        s = self.stats.setdefault(self.verifier or "?", {})
        s[what] = s.get(what, 0) + n

    def finish(self) -> None:
        for name, t in self._tables.items():
            self.cache.save_table(name, t, self._used.get(name))
        if self.use_cache:
            self.cache.save_manifest({**self.fps.manifest(), "run": self.run, "fp_version": FP_VERSION})

    def section(self) -> dict:
        reused = sorted(n for n, d in self.decisions.items() if d["status"] == "reused")
        return {"tier": self.tier, "requested_tier": self.requested_tier, "release": self.release,
                "cache": "off (--no-cache)" if not self.use_cache else
                         ("written, not read (full tier)" if self.tier == "full" else "read and written"),
                "changed_since_cached_run": {k: (v if not isinstance(v, list) or len(v) <= 40 else v[:40] + [f"... {len(v) - 40} more"])
                                             for k, v in self.changes.items()},
                "verifiers": self.decisions, "reused": reused,
                "reused_within": self.stats, "fingerprint_seconds": self.fps.seconds,
                **({"notes": self.notes} if self.notes else {})}


# ================================================================================================ hooks
def active() -> "Session | None":
    return CURRENT


def _fea_case_key(s: Session, design, kind: str, case, names) -> str | None:
    import numpy as np

    fps = s.fps
    names = [n for n in names if n]
    comps = {c.name: c for c in design.components}
    if kind == "bed_support":
        parts = fps.parts_digest()
        fields = fps.fields_digest(fps.fields)
        extra = "whole-machine"
    else:
        nameset = set(names)
        parts = fps.parts_digest(names)
        # screws that can act on these parts (their shank inside the parts' box, or naming them)
        boxes = []
        for n in names:
            if n in comps:
                bb = comps[n].shape.bounding_box()
                boxes.append((np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z])))
        lo = np.min([b[0] for b in boxes], axis=0) if boxes else np.zeros(3)
        hi = np.max([b[1] for b in boxes], axis=0) if boxes else np.zeros(3)
        screws = []
        for f in design.fasteners:
            c = comps.get(f.name)
            if c is None:
                continue
            near = f.name in nameset or bool(set(f.clamps) & nameset) or bool(set(c.meta.get("threads_into", []) or []) & nameset)
            if not near:
                sb = c.shape.bounding_box()
                head = np.array(f.head_center, dtype=float)
                slo = np.minimum(head, [sb.min.X, sb.min.Y, sb.min.Z])
                shi = np.maximum(head, [sb.max.X, sb.max.Y, sb.max.Z])
                m = max(10.0, 3.0 * float(c.meta.get("thread_d", 3.0) or 3.0))
                near = bool(np.all(slo - m <= hi) and np.all(lo <= shi + m))
            if near:
                screws.append([f.name, fps.fasteners.get(f.name), fps.part(f.name)])
        pairs = []
        for attr in ("joins", "allowed_overlaps", "min_clearances"):
            for k, v in (getattr(design, attr, {}) or {}).items():
                if set(k) & (nameset | {s_[0] for s_ in screws}):
                    pairs.append([attr, sorted(k), value_fp(v)])
        fields = fps.fields_digest(("manufacturing", "gravity", "tnut_style"))
        extra = digest("fea-neighbours", sorted(screws, key=str), sorted(pairs, key=str))
        if any(is_unstable(x[1] or "") or is_unstable(x[2]) for x in screws):
            return None
    cfp = value_fp(case) if case is not None else "none"
    for v in (parts, fields, cfp):
        if is_unstable(v):
            return None
    return digest(FP_VERSION, "fea-case", kind, getattr(case, "name", kind), code_hash(DEPS["fea"].module), parts, fields, extra, cfp)


def fea_case(design, r, kind: str, case, names, compute):
    """Run (or reuse) one FEA case. `compute(result)` adds its findings to `result` and returns its metrics."""
    s = CURRENT
    if s is None:
        return compute(r)
    try:
        key = _fea_case_key(s, design, kind, case, names)
    except Exception:
        key = None
    label = getattr(case, "name", kind)
    hit = s.cache.get("fea_cases", key)
    if hit is not None:
        r.findings.extend(hit["findings"])
        s.stat("fea_cases_reused")
        s.decisions.setdefault("fea", {}).setdefault("cases_reused", {})[label] = hit.get("run")
        return hit["metrics"]
    from ..report import VerifierResult

    sub = VerifierResult(r.verifier)
    t0 = time.time()
    m = compute(sub)
    r.findings.extend(sub.findings)
    s.stat("fea_cases_run")
    s.decisions.setdefault("fea", {}).setdefault("cases_run", {})[label] = round(time.time() - t0, 1)
    if not any(f.code in ("fea_crashed",) for f in sub.findings):
        s.cache.put("fea_cases", key, {"case": label, "kind": kind, "findings": list(sub.findings), "metrics": m,
                                       "run": dict(s.run)})
    return m


def memo(table: str, key_parts, compute):
    """Persistent memo of a pure geometric kernel. key_parts (or a function returning them, called only in an
    incremental run) must be built from shape fingerprints and the kernel's parameters."""
    s = CURRENT
    if s is None:
        return compute()
    t = s.table(table)
    if callable(key_parts):
        key_parts = key_parts()
    k = digest(FP_VERSION, code_hash(DEPS[s.verifier].module) if s.verifier in DEPS else "?", table, key_parts)
    s.mark_used(table, k)
    if k in t:
        s.stat(f"{table}_reused")
        return t[k]
    v = compute()
    t[k] = v
    s.stat(f"{table}_computed")
    return v


def shape_key(shape) -> str:
    return shape_fp(shape)


__all__ = ["Session", "TIERS", "QUICK", "DEPS", "active", "fea_case", "memo", "shape_key"]
