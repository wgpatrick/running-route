"""Incremental verification: fingerprints, recorded dependencies, a result cache, three tiers, parallel runs.

    mechloop verify designs/x.py --tier quick      geometry, interference (changed pairs), manufacture, practice, ratings;
                                                   any other verifier is reused when what it read is unchanged, else
                                                   reported NOT RUN (stale) -- the run is then partial
    mechloop verify designs/x.py --tier affected   every verifier whose inputs changed re-runs (FEA case by case, DFM
                                                   part by part, interference pair by pair); the rest is reused
    mechloop verify designs/x.py --tier full       everything re-runs, nothing is reused (results are still stored);
                                                   required before freezing / release, and the tier any design marked
                                                   `release = True` gets whatever tier is asked
    mechloop verify designs/x.py                   (no tier) a full verify, as before; results are stored so a later
                                                   `--tier affected` can reuse them
    --no-cache                                     nothing read, nothing stored

How reuse is decided. A stored result (a verifier's, one FEA case's, one part's DFM checks) carries
  - deps: the fingerprints, taken at the start of its run, of exactly what it read from the design: the Design fields,
    the list of parts if it iterated it, and each part attribute it touched (shape, meta, body, ratings ...); recorded
    at run time (recorder.py),
  - manifest: the code that ran and the data files it read (coderec.py).
It is reused only when every one of those is unchanged. Results are deterministic functions of what they read, so a
result whose reads are unchanged would be computed again identically. A part a verifier never touched can change
without re-running it.

A reused result is the stored one, unchanged (findings and metrics), and says where it came from: the report's
`incremental` section lists for each verifier "ran" / "reused" (with the iteration and time of the run that produced
it) / "not run", and the summary line of a reused verifier ends in "[reused from run N]".

Session holds one run's state; the module functions below are the hooks the verifiers call (no-ops when no session
is active, so a verifier run on its own behaves exactly as before).
"""
from __future__ import annotations

import time
from pathlib import Path

from . import coderec, recorder
from .cache import ResultCache
from .deps import DEPS, QUICK
from .fingerprint import FP_VERSION, digest, diff, fingerprint as fingerprint_design, is_unstable, shape_fp, value_fp

TIERS = ("quick", "affected", "full")
CURRENT: "Session | None" = None
KEEP = 3        # stored results kept per slot (different inputs of the same verifier / case / part)


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
        self._new: dict[str, dict] = {}       # table entries added in this process (sent back from a worker)
        self.stats: dict[str, dict] = {}

    # ------------------------------------------------------------------------------------------ dependencies
    def deps_of(self, reads) -> dict | None:
        """The fingerprints (from the start of the run) of what `reads` recorded; None if any has no stable form."""
        f = self.fps
        d = {"fields": {n: f.fields.get(n, "absent") for n in sorted(reads.fields)},
             "attrs": {f"{n}\x1f{a}": f.attr(n, a) for n, a in sorted(reads.attrs)}}
        if reads.parts_list:
            d["parts_list"] = f.parts_list()
        if any(is_unstable(v) for v in list(d["fields"].values()) + list(d["attrs"].values())):
            return None
        return d

    def deps_valid(self, d: dict | None) -> tuple[bool, str]:
        if d is None:
            return False, "dependencies not recorded"
        f = self.fps
        if "parts_list" in d and d["parts_list"] != f.parts_list():
            return False, "parts added or removed"
        for n, v in d.get("fields", {}).items():
            if f.fields.get(n, "absent") != v:
                return False, f"design field '{n}' changed"
        for k, v in d.get("attrs", {}).items():
            n, a = k.split("\x1f", 1)
            if f.attr(n, a) != v:
                return False, f"{n}.{a} changed"
        return True, ""

    def valid(self, entry: dict) -> tuple[bool, str]:
        ok, why = self.deps_valid(entry.get("deps"))
        if not ok:
            return ok, why
        return coderec.still_valid(entry.get("manifest"))

    def find(self, kind: str, slot: str | None, entries: list | None = None):
        """(entry, why not) -- the newest stored entry of this slot whose deps and code are unchanged."""
        if slot is None:
            return None, "no stable key"
        if entries is None:
            if not self.cache.read:
                return None, "full tier: nothing reused" if self.tier == "full" else "cache not read"
            entries = self.cache.get(kind, slot) or []
            entries = entries.get("entries", []) if isinstance(entries, dict) else []
        why = "nothing stored yet"
        for e in entries:
            ok, w = self.valid(e)
            if ok:
                return e, ""
            why = w
        return None, why

    def put(self, kind: str, slot: str | None, entry: dict) -> bool:
        if slot is None or not self.cache.write or entry.get("deps") is None:
            return False
        m = entry.get("manifest")
        if not m or m.get("unknown"):
            return False
        old = self.cache.get(kind, slot)      # (None in the full tier: the cache is not read)
        prev = (old or {}).get("entries", []) if isinstance(old, dict) else []
        entry = {**entry, "run": dict(self.run)}
        return self.cache.put(kind, slot, {"entries": ([entry] + prev)[:KEEP]})

    # ----------------------------------------------------------------------------------------- verifier level
    def slot(self, name: str, upstream: dict | None = None) -> tuple[str | None, str]:
        d = DEPS.get(name)
        if d is None:
            return None, "no dependency declaration: always re-run"
        if d.granularity == "always":
            return None, "always re-run (cheap; reads the results of the others)"
        up = value_fp({u: (upstream or {}).get(u) for u in d.upstream}) if d.upstream else "no-upstream"
        if is_unstable(up):
            return None, "upstream metrics have no stable fingerprint: re-run"
        return digest(FP_VERSION, "verifier", name, up), ""

    def lookup(self, name: str, slot):
        hit, why = self.find(f"results/{name}", slot)
        if hit is None and why not in ("nothing stored yet", "full tier: nothing reused", "cache not read", "no stable key"):
            self.decisions.setdefault(name, {})["stored_result_invalid"] = why
        return hit

    def store(self, name: str, slot, res, deps: dict | None, manifest: dict | None) -> bool:
        if any(f.code in ("verifier_crashed",) for f in res.findings):
            return False       # a crash may be the machine's (memory, a killed solver): never reuse it
        return self.put(f"results/{name}", slot, {
            "verifier": name, "findings": list(res.findings), "metrics": res.metrics, "skipped": res.skipped,
            "seconds": res.seconds, "deps": deps, "manifest": manifest,
            "artifacts_sim": res.artifacts_sim})      # the motion program's trace, so a reused result still renders

    # ------------------------------------------------------------------------------------------ memo tables
    def table(self, name: str) -> dict:
        if name not in self._tables:
            self._tables[name] = self.cache.load_table(name)
            self._used[name] = set()
        return self._tables[name]

    def table_put(self, name: str, k, v) -> None:
        self.table(name)[k] = v
        self._new.setdefault(name, {})[k] = v

    def mark_used(self, name: str, key) -> None:
        self._used.setdefault(name, set()).add(key)

    def stat(self, what: str, n: int = 1) -> None:
        s = self.stats.setdefault(self.verifier or "?", {})
        s[what] = s.get(what, 0) + n

    # ------------------------------------------------------------------------- worker processes (parallel run)
    def export_delta(self) -> dict:
        """What a worker process learned, for the parent: new memo entries, keys used, stats, decisions."""
        return {"new": self._new, "used": {k: v for k, v in self._used.items()}, "stats": self.stats,
                "decisions": self.decisions}

    def merge_delta(self, d: dict) -> None:
        for name, entries in d.get("new", {}).items():
            self.table(name).update(entries)
        for name, used in d.get("used", {}).items():
            self.table(name)
            self._used.setdefault(name, set()).update(used)
        for v, st in d.get("stats", {}).items():
            mine = self.stats.setdefault(v, {})
            for k, n in st.items():
                mine[k] = mine.get(k, 0) + n
        for v, dec in d.get("decisions", {}).items():
            mine = self.decisions.setdefault(v, {})
            for k, val in dec.items():
                if isinstance(val, dict) and isinstance(mine.get(k), dict):
                    mine[k].update(val)        # cases_run / cases_reused of several FEA case processes
                else:
                    mine[k] = val

    def finish(self) -> None:
        for name, t in self._tables.items():
            self.cache.save_table(name, t, self._used.get(name))
        if self.use_cache:
            self.cache.save_manifest({**self.fps.manifest(), "run": self.run, "fp_version": FP_VERSION})

    def section(self) -> dict:
        reused = sorted(n for n, d in self.decisions.items() if d.get("status") == "reused")
        return {"tier": self.tier, "requested_tier": self.requested_tier, "release": self.release,
                "cache": "off (--no-cache)" if not self.use_cache else
                         ("written, not read (full tier)" if self.tier == "full" else "read and written"),
                "changed_since_cached_run": {k: (v if not isinstance(v, list) or len(v) <= 40 else v[:40] + [f"... {len(v) - 40} more"])
                                             for k, v in self.changes.items()},
                "verifiers": self.decisions, "reused": reused,
                "reused_within": self.stats, "fingerprint_seconds": self.fps.seconds,
                "instances": {"parts": len(self.fps.parts),
                              "unique": len({p.get("instance") for p in self.fps.parts.values()}),
                              "note": "unique = distinct shape (placement aside), material, catalogue entry and ratings; "
                                      "placement-independent checks (geometry validity, proxy vs vendor CAD) run once per "
                                      "unique part"},
                **({"notes": self.notes} if self.notes else {})}


# ================================================================================================ hooks
def active() -> "Session | None":
    return CURRENT


def _cached_unit(kind: str, slot, design, r, compute, label: str, stat: str, capture=None, restore=None, table=None):
    """Run or reuse one unit of work (an FEA case, one part's checks) inside a verifier; see fea_case / part_cached."""
    s = CURRENT
    entries = None
    if table is not None and slot is not None:
        t = s.table(table)
        s.mark_used(table, slot)
        entries = (t.get(slot) or {}).get("entries", []) if s.cache.read else []
    hit, _ = s.find(kind, slot, entries) if slot is not None else (None, "")
    if hit is not None:
        r.findings.extend(hit["findings"])
        if restore is not None:
            restore(hit.get("side"))
        coderec.push_manifest(hit.get("manifest"))
        recorder.push(hit.get("deps"))
        s.stat(f"{stat}_reused")
        return hit, True
    from ..report import VerifierResult

    sub = VerifierResult(r.verifier)
    t0 = time.time()
    with recorder.tracking(design) as reads, coderec.Recording() as rec:
        v = compute(sub)
    r.findings.extend(sub.findings)
    side = capture() if capture is not None else None
    s.stat(f"{stat}_run")
    entry = {"label": label, "findings": list(sub.findings), "value": v, "side": side, "deps": s.deps_of(reads),
             "manifest": rec.manifest(), "seconds": round(time.time() - t0, 2)}
    if not any(f.code in ("fea_crashed",) for f in sub.findings) and slot is not None and entry["deps"] is not None \
            and s.cache.write and not (entry["manifest"] or {}).get("unknown"):
        if table is not None:
            old = (s.table(table).get(slot) or {}).get("entries", []) if s.cache.read else []
            s.table_put(table, slot, {"entries": ([{**entry, "run": dict(s.run)}] + old)[:KEEP]})
        else:
            s.put(kind, slot, entry)
    return entry, False


def fea_case(design, r, kind: str, case, names, compute):
    """Run (or reuse) one FEA case. `compute(result)` adds its findings to `result` and returns its metrics.
    Keyed on the case itself; reused while everything it read (its parts, the screws its stacks looked at, joins,
    print settings ...) is unchanged."""
    s = CURRENT
    if s is None:
        return compute(r)
    cfp = value_fp(case) if case is not None else "none"
    label = getattr(case, "name", kind)
    slot = None if is_unstable(cfp) else digest(FP_VERSION, "fea-case", kind, label, cfp)
    entry, reused = _cached_unit("fea_cases", slot, design, r, compute, label, "fea_cases")
    dec = s.decisions.setdefault("fea", {})
    if reused:
        dec.setdefault("cases_reused", {})[label] = entry.get("run")
    else:
        dec.setdefault("cases_run", {})[label] = entry["seconds"]
    return entry["value"]


def part_cached(r, part, design, compute, capture=None, restore=None):
    """One part's checks inside a verifier, reused while everything they read is unchanged (the part, and whatever
    else they looked at: screws threading into it, the design's settings ...).

    compute(result) adds the part's findings to `result` and returns its value (a metrics row); capture() returns the
    side state the part's run left (module-level tables a verifier aggregates afterwards) and restore(state) puts it
    back on reuse. Outside an incremental run it just runs."""
    s = CURRENT
    if s is None or s.verifier is None:
        return compute(r)
    slot = digest(FP_VERSION, "part", s.verifier, part.name)
    entry, _ = _cached_unit(None, slot, design, r, compute, part.name, "parts", capture, restore,
                            table=f"{s.verifier}.parts")
    return entry["value"]


def memo(table: str, key_parts, compute, code: tuple = ()):
    """Persistent memo of a pure geometric kernel. key_parts (or a function returning them, called only in an
    incremental run) must be built from shape fingerprints and the kernel's parameters."""
    s = CURRENT
    if s is None:
        return compute()
    short, table = table, f"{s.verifier or 'none'}.{table}"   # one table per verifier: one reused whole keeps its memo
    t = s.table(table)
    if callable(key_parts):
        key_parts = key_parts()
    k = digest(FP_VERSION, kernel_hash(code), table, key_parts)
    s.mark_used(table, k)
    if k in t:      # (a full-tier run starts from an empty table: then only identical calls within the run are shared)
        s.stat(f"{short}_reused")
        return t[k]
    v = compute()
    s.table_put(table, k, v)
    s.stat(f"{short}_computed")
    return v


def kernel_hash(code: tuple = ()) -> str:
    """The code behind a memoised kernel: geom.py (exact overlap volume), this module, the fingerprint recipe, the
    library versions, and the files named in `code` (paths relative to the package) where the kernel's own code lives."""
    root = coderec.PKG_ROOT
    files = ("geom.py", "incremental/__init__.py", "incremental/fingerprint.py") + tuple(code)
    return digest("kernel", [[f, coderec.file_hash(str(root / f))] for f in files], coderec.externals())


def shape_key(shape) -> str:
    return shape_fp(shape)


def intrinsic_key(shape) -> str:
    from .fingerprint import intrinsic_fp

    return intrinsic_fp(shape)


__all__ = ["Session", "TIERS", "QUICK", "DEPS", "active", "fea_case", "part_cached", "memo", "shape_key", "intrinsic_key"]
