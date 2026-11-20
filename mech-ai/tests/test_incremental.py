"""Incremental verification (mechloop.incremental): fingerprints, dependency declarations, the result cache, tiers.

A synthetic design checks that a change to one part re-runs only what reads it (and reuses the rest); a small real
design checks that a run that reuses results gives exactly the findings of a run without the cache."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from build123d import Box, Pos

from mechloop import Design, LoadCase
from mechloop.incremental import Session, codehash
from mechloop.incremental.deps import DEPS
from mechloop.incremental.fingerprint import fingerprint, shape_fp, value_fp
from mechloop.report import without_timings
from mechloop.runner import ORDER, load_design, run, verify

ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------------------------- declarations
def test_every_verifier_declares_dependencies():
    names = [o if isinstance(o, str) else o[0] for o in ORDER] + ["requirements"]
    missing = [n for n in names if n not in DEPS]
    assert not missing, f"verifiers without a dependency declaration (they would always re-run): {missing}"
    import importlib

    for n, d in DEPS.items():
        importlib.import_module(d.module)
        assert d.parts in ("all", "none"), n
        assert d.granularity in ("verifier", "per_case", "pairwise", "always"), n
        assert d.fields == "*" or all(isinstance(f, str) for f in d.fields), n
        assert set(d.upstream) <= set(names), n


def test_unknown_verifier_has_no_key():
    d = _synthetic()
    s = Session(d, Path("/nonexistent"), use_cache=False)
    key, why = s.key("not_a_verifier")
    assert key is None and "always re-run" in why


# --------------------------------------------------------------------------------------------- fingerprints
def _synthetic(c_size: float = 10.0, force_a: float = 50.0) -> Design:
    d = Design("inc_synth")
    d.add("a", Pos(0, 0, 5) * Box(40, 20, 10), material="al6061")
    d.add("b", Pos(0, 0, 15) * Box(20, 20, 10), material="al6061")          # sits on a
    d.add("c", Pos(100, 0, c_size / 2) * Box(10, 10, c_size), material="al6061")   # far away; c_size is its height
    d.add("e", Pos(92, 0, 2.5) * Box(6, 6, 5), material="al6061")                 # against c's -X face
    d.loadcases.append(LoadCase("load_a", "a", fixed=lambda f: f.center().X < -19.9, loaded=lambda f: f.center().X > 19.9,
                                force=(0, 0, -force_a), min_fos=1.5, mesh_size=4.0))
    d.loadcases.append(LoadCase("load_c", "c", fixed=lambda f: f.center().Z < 1e-6, loaded=lambda f: f.center().Z > c_size - 1e-6,
                                force=(10, 0, 0), min_fos=1.5, mesh_size=3.0))
    return d


def test_fingerprints_are_stable_and_tessellation_independent():
    d1, d2 = _synthetic(), _synthetic()
    f1, f2 = fingerprint(d1), fingerprint(d2)
    assert f1.manifest() == f2.manifest()
    d2.get("a").shape.tessellate(0.01, 0.1)          # meshing the part does not change it
    from mechloop.incremental import fingerprint as fpmod

    fpmod._SHAPE_FP.clear()
    assert fingerprint(d2).manifest() == f1.manifest()
    d2.get("a").color = "red"                         # render colour: read by no check
    assert fingerprint(d2).part("a") == f1.part("a")
    d2.get("a").meta["edge_break_mm"] = 0.3           # meta that checks read
    assert fingerprint(d2).part("a") != f1.part("a")
    d3 = _synthetic(c_size=11.0)
    f3 = fingerprint(d3)
    assert f3.part("c") != f1.part("c") and f3.part("a") == f1.part("a")
    assert f3.bodies["world"] != f1.bodies["world"]
    from build123d import Location

    moved = d1.get("b").shape.moved(Location((0.001, 0, 0)))
    assert shape_fp(moved) != shape_fp(d1.get("b").shape)     # placement is part of the geometry


def test_callable_fingerprints_see_code_and_closures():
    def pred(z):
        return lambda f: f.center().Z < z

    assert value_fp(pred(1.0)) == value_fp(pred(1.0))
    assert value_fp(pred(1.0)) != value_fp(pred(2.0))
    assert value_fp(lambda f: f.area > 5) != value_fp(lambda f: f.area > 6)

    import threading

    assert value_fp({"x": threading.Lock()}).startswith("unstable:")     # no stable form: whatever reads it re-runs


def test_code_hash_follows_sources_and_data(monkeypatch):
    base = codehash.code_hash("mechloop.verifiers.fea")
    base_geo = codehash.code_hash("mechloop.verifiers.geometry")
    assert "verifiers/fea.py" in codehash.module_closure("mechloop.verifiers.fea")
    assert any(f.endswith(".json") for f in codehash.data_files())
    orig = codehash._file_hash.__wrapped__

    def fake(rel):
        return "changed" if rel == "verifiers/fea.py" else orig(rel)

    codehash.clear()
    monkeypatch.setattr(codehash, "_file_hash", fake)
    monkeypatch.setattr(codehash, "code_hash", codehash.code_hash.__wrapped__)
    assert codehash.code_hash("mechloop.verifiers.fea") != base
    data = next(f for f in codehash.data_files() if f.endswith(".json"))
    monkeypatch.setattr(codehash, "_file_hash", lambda rel: "changed" if rel == data else orig(rel))
    assert codehash.code_hash("mechloop.verifiers.geometry") != base_geo     # data files count for every verifier


# ------------------------------------------------------------------------------------------ reuse on a change
ONLY = ["geometry", "interference", "fea"]


def _run(d, out, tier):
    s = Session(d, out, tier=tier, use_cache=True, iteration=1)
    rep = verify(d, ONLY, session=s)
    return rep, rep.incremental


def _findings(rep):
    return [(f.verifier, f.severity, f.code, f.message) for r in rep.results for f in r.findings]


@pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")
def test_one_part_change_reruns_only_what_reads_it(tmp_path):
    out = tmp_path / "inc_synth"
    rep0, inc0 = _run(_synthetic(), out, "full")
    assert inc0["tier"] == "full" and not inc0["reused"]
    assert set(inc0["verifiers"]["fea"]["cases_run"]) == {"load_a", "load_c", } and "cases_reused" not in inc0["verifiers"]["fea"]

    # nothing changed: everything reused, findings identical
    rep1, inc1 = _run(_synthetic(), out, "affected")
    assert set(inc1["reused"]) == set(ONLY)
    assert _findings(rep1) == _findings(rep0)
    assert all(r.reused for r in rep1.results if r.verifier in ONLY)

    # part c changes: geometry and interference re-run (only the pairs with c), case load_c re-runs, load_a is reused
    d2 = _synthetic(c_size=12.0)
    rep2, inc2 = _run(d2, out, "affected")
    v = inc2["verifiers"]
    assert inc2["changed_since_cached_run"]["parts_changed"] == ["c"]
    assert v["geometry"]["status"] == "ran" and v["interference"]["status"] == "ran" and v["fea"]["status"] == "ran"
    assert list(v["fea"]["cases_run"]) == ["load_c"] and list(v["fea"]["cases_reused"]) == ["load_a"]
    within = inc2["reused_within"]["interference"]
    assert within.get("pairs_reused", 0) >= 2            # a-b overlap and gap: unchanged pair
    assert within.get("pairs_computed", 0) >= 1          # c-e: changed pair
    # the same as a run without any cache
    fresh = verify(_synthetic(c_size=12.0), ONLY)
    assert _findings(rep2) == _findings(fresh)
    assert [r.metrics for r in rep2.results] == [r.metrics for r in fresh.results]

    # a load case changes (not a part): only that case re-runs; geometry and interference are reused
    d3 = _synthetic(c_size=12.0, force_a=80.0)
    rep3, inc3 = _run(d3, out, "affected")
    v = inc3["verifiers"]
    assert v["geometry"]["status"] == "reused" and v["interference"]["status"] == "reused"
    assert list(v["fea"]["cases_run"]) == ["load_a"] and list(v["fea"]["cases_reused"]) == ["load_c"]
    assert _findings(rep3) == _findings(verify(_synthetic(c_size=12.0, force_a=80.0), ONLY))

    # quick tier on a change: FEA is not a quick check, so it is NOT RUN (stale), never passed on old results
    rep4, inc4 = _run(_synthetic(c_size=13.0, force_a=80.0), out, "quick")
    fea = next(r for r in rep4.results if r.verifier == "fea")
    assert fea.skipped.startswith("not run: stale") and not fea.ok
    assert inc4["verifiers"]["geometry"]["status"] == "ran"

    # full tier: nothing reused
    rep5, inc5 = _run(_synthetic(c_size=12.0, force_a=80.0), out, "full")
    assert not inc5["reused"] and "cases_reused" not in inc5["verifiers"]["fea"]


def test_release_design_always_gets_full_tier(tmp_path):
    d = _synthetic()
    d.release = True
    s = Session(d, tmp_path / "x", tier="quick", use_cache=True)
    assert s.tier == "full" and s.notes and not s.cache.read


def test_no_cache_writes_nothing(tmp_path):
    d = _synthetic()
    s = Session(d, tmp_path / "x", tier="affected", use_cache=False)
    verify(d, ["geometry"], session=s)
    assert not (tmp_path / "x" / "verify_cache").exists()


def test_undeclared_read_is_not_cached(tmp_path, monkeypatch):
    from mechloop.incremental import deps

    monkeypatch.setitem(deps.DEPS, "geometry", deps.Deps("mechloop.verifiers.geometry", fields=("name",)))
    d = _synthetic()
    d.envelope = (500, 500, 500)
    s = Session(d, tmp_path / "x", tier="affected", use_cache=True)
    rep = verify(d, ["geometry"], session=s)
    dec = rep.incremental["verifiers"]["geometry"]
    assert dec["status"] == "ran" and dec["stored"] is False and "envelope" in dec["undeclared_reads"]
    s2 = Session(d, tmp_path / "x", tier="affected", use_cache=True)
    rep2 = verify(d, ["geometry"], session=s2)
    assert rep2.incremental["verifiers"]["geometry"]["status"] == "ran"      # never reused on a wrong declaration


# ------------------------------------------------------------------------------- a real design, via the CLI path
@pytest.mark.skipif(shutil.which("ccx") is None, reason="CalculiX not installed")
def test_reused_results_equal_a_no_cache_run_on_a_real_design(tmp_path):
    src = (ROOT / "examples" / "motor_bracket.py").read_text()
    f1 = tmp_path / "motor_bracket.py"
    f1.write_text(src)
    out = tmp_path / "out"
    run(f1, out, render=False)                               # plain verify: writes the cache
    assert (out / "motor_bracket" / "verify_cache" / "manifest.json").exists()
    rep_same = run(f1, out, render=False, tier="affected")   # nothing changed: all reused
    assert set(rep_same.incremental["reused"]) >= {"geometry", "interference", "fea", "practice", "assemblability"}
    ref = run(f1, tmp_path / "ref", render=False, use_cache=False)
    assert ref.incremental == {}
    assert without_timings(rep_same.to_dict(500))["findings"] == without_timings(ref.to_dict(500))["findings"]
    assert without_timings(rep_same.to_dict(500)) == without_timings(ref.to_dict(500))

    # one part tweaked (the bracket's gussets): the report must equal a no-cache verify of the tweaked design
    assert "T_RIB = 3.0" in src
    f1.write_text(src.replace("T_RIB = 3.0", "T_RIB = 4.0"))
    rep_tw = run(f1, out, render=False, tier="affected")
    inc = rep_tw.incremental
    assert inc["changed_since_cached_run"]["parts_changed"] == ["bracket"]
    assert inc["verifiers"]["fea"]["status"] == "ran"
    ref_tw = run(f1, tmp_path / "ref2", render=False, use_cache=False)
    assert without_timings(rep_tw.to_dict(500)) == without_timings(ref_tw.to_dict(500))
    hist = [json.loads(x) for x in (out / "motor_bracket" / "history.jsonl").read_text().splitlines()]
    assert hist[-1]["tier"] == "affected" and "reused" in hist[-1]
    report = json.loads((out / "motor_bracket" / "report.json").read_text())
    assert report["incremental"]["tier"] == "affected"
