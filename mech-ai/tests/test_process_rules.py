"""Suppliers' published CNC-milling and 3D-printing rules (mechloop/data/supplier_rules_cnc_3dp), the features they are
judged on (verifiers/dfm_features.py), their evaluation (shops/process_rules.py) and the findings
(verifiers/dfm_process_rules.py).

- every rule carries its source (a supplier page, or a repository file for the owner's printer) and the source's words;
- synthetic solids for each extractor: tool access and set-ups, undercuts, vertical corners, pockets, holes and
  threads, wall thickness and height, flat cantilevers and bridges, overhang angles, pins, enclosed voids;
- the evaluator on hand-made feature dicts (formulas, size bands, thread tables, conflicting conventions);
- the reference parts in reference_parts/batch01: RP01 and RP05 raise the findings they were built to raise, RP02 passes.
"""
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pytest
from build123d import Box, Cylinder, Pos, Rot, fillet, import_step, Axis

from mechloop.model import Design
from mechloop.shops import process_rules as PR
from mechloop.verifiers import dfm_features as FE
from mechloop.verifiers import dfm_geom as G
from mechloop.verifiers.manufacture import verify_manufacture

ROOT = Path(__file__).resolve().parents[1]
RP = ROOT / "reference_parts" / "batch01"
HOSTS = {"xometry": {"www.xometry.com"}, "protolabs": {"www.protolabs.com"}, "hubs": {"www.hubs.com"}, "fictiv": {"www.fictiv.com"},
         "jlccnc": {"jlccnc.com"}, "jlc3dp": {"jlc3dp.com"}, "sendcutsend": {"sendcutsend.com", "app.sendcutsend.com"},
         "rapiddirect": {"www.rapiddirect.com"}, "shapeways": {"www.shapeways.com"}, "pcbway": {"www.pcbway.com"}}


def _norm(s):
    return " ".join(str(s).replace(" ", " ").split())


# ------------------------------------------------------------------------------------------- data
def test_every_rule_has_its_source_and_words():
    docs = PR.load()
    assert set(HOSTS) | {"own_printer"} <= set(docs)
    ids = set()
    for sup, doc in docs.items():
        assert doc["schema"] == PR.SCHEMA and doc["retrieved"] == "2026-11-19" and doc["rules"]
        for r in doc["rules"]:
            assert r["id"] not in ids and r["id"].startswith(sup + "."), r["id"]
            ids.add(r["id"])
            assert r["process"] in ("cnc_milling", "fdm", "sls", "mjf", "sla"), r["id"]
            assert isinstance(r["quote"], str) and len(r["quote"].strip()) >= 8, r["id"]
            assert r["retrieved"] == "2026-11-19" and r["severity"] in ("error", "warning", "info"), r["id"]
            assert r["comparison"] in (">=", "<=", "<", "==", "within", "in_list", "info"), r["id"]
            if sup == "own_printer":
                path = ROOT / r["source_url"]
                assert r.get("source_kind") == "repository file" and path.exists(), r["id"]
                # the owner's printer rules quote repository files: the words must still be there
                assert _norm(r["quote"]) in _norm(path.read_text(encoding="utf-8")), r["id"]
            else:
                assert r["source_url"].startswith("https://") and urlparse(r["source_url"]).hostname in HOSTS[sup], r["id"]
            if r["comparison"] != "info" and r.get("evaluate") is not False:
                assert ("value_mm" in r) or ("value" in r) or r.get("formula"), r["id"]
    for r in PR.all_rules():
        for other in r.get("conflicts") or ():
            assert other in ids, (r["id"], other)
        if r.get("duplicate_of"):
            assert r["duplicate_of"] in ids, r["id"]


def test_known_figures_and_disagreements():
    jl = PR.rule("jlccnc.cnc.corner_radius_depth")                 # R = H/10 + 0.5: 30 mm deep -> R 3.5 (the page's own example)
    assert PR._formula_limit(jl, 30.0) == pytest.approx(3.5)
    m4 = PR.rule("protolabs.cnc.thread_m4_modelled_d")
    assert m4["value_mm"] == [3.24, 3.42] and PR.rule("protolabs.cnc.thread_m4_depth_max")["value_mm"] == pytest.approx(10.16)
    assert PR.rule("sendcutsend.cnc.corner_radius_min")["value_mm"] == pytest.approx(1.587)
    # tapped holes: SendCutSend wants the major diameter modelled, Protolabs and JLCCNC the tap drill
    scs = PR.rule("sendcutsend.cnc.tap_hole_major")
    assert "protolabs.cnc.thread_m4_modelled_d" in scs["conflicts"] and "jlccnc.cnc.tap_drill_m3" in scs["conflicts"]
    # blind-tap run-out: Hubs 1.5 d, JLCCNC 0.5 d
    assert PR.rule("hubs.cnc.blind_tap_runout")["formula"]["d"] == 1.5 and PR.rule("jlccnc.cnc.blind_tap_runout")["formula"]["d"] == 0.5
    assert "hubs.cnc.blind_tap_runout" in PR.rule("jlccnc.cnc.blind_tap_runout")["conflicts"]
    srcs = PR.sources()
    assert any(s["host"] == "www.cnckitchen.com" and "robots" in s["why"] for s in srcs["skipped"])


# ------------------------------------------------------------------------------- feature extraction
def _sample(shape):
    sm = G.sample_surface(shape)
    frame = G.part_frame(shape)
    cyls = G.cylinders(shape)
    return sm, frame, cyls, G.holes(shape, sm, cyls)


def _block_with_pocket(r=0.0, depth=10.0, w=20.0, l=30.0):
    blk = Box(60, 40, 20)
    pk = Pos(0, 0, 10 - depth / 2) * Box(l, w, depth)
    if r > 0:
        pk = fillet(pk.edges().filter_by(Axis.Z), radius=r)
    return blk - pk


def test_corners_and_pockets_sharp_and_filleted():
    s = _block_with_pocket(r=0.0)
    sm, frame, cyls, holes = _sample(s)
    cs = FE.vertical_corners(s, sm, frame, cyls, holes)
    assert len(cs) == 4 and all(c["radius"] == 0 and c["depth"] == pytest.approx(10) and "+Z" in c["approach"] for c in cs)
    s = _block_with_pocket(r=2.0)
    sm, frame, cyls, holes = _sample(s)
    cs = FE.vertical_corners(s, sm, frame, cyls, holes)
    assert len(cs) == 4 and all(c["radius"] == pytest.approx(2) and c["depth"] == pytest.approx(10) for c in cs)
    acc = FE.tool_access(s, sm, frame)
    pk = FE.pockets(s, frame, acc, cs, holes)
    assert len(pk) == 1 and pk[0]["depth"] == pytest.approx(10) and pk[0]["width"] == pytest.approx(20, abs=0.05)
    assert pk[0]["tool_d"] == pytest.approx(4) and pk[0]["corner_radii"] == [2.0]


def test_tool_access_setups_and_undercut():
    two = Box(60, 40, 20) - Pos(0, 0, 8) * Box(20, 20, 4) - Pos(0, 0, -8) * Box(20, 20, 4)
    sm, frame, _, _ = _sample(two)
    a = FE.tool_access(two, sm, frame)
    assert a["setups"] == 2 and set(a["setup_dirs"]) == {"+Z", "-Z"} and not a["inaccessible"]
    # a T-slot: a narrow neck from the top opening into a wider channel below it, run out to both ends
    t = Box(60, 40, 20) - Pos(0, 0, 7) * Box(60, 6, 6) - Pos(0, 0, 1) * Box(60, 16, 6)
    sm, frame, _, _ = _sample(t)
    a = FE.tool_access(t, sm, frame)
    assert not a["inaccessible"] and set(a["setup_dirs"]) & {"+X", "-X"}     # the whole slot is cut along it, from one end
    # stop it short of both ends: the underside of the lips is reached from nowhere by a straight cutter
    t2 = Box(60, 40, 20) - Pos(0, 0, 7) * Box(50, 6, 6) - Pos(0, 0, 1) * Box(50, 16, 6)
    sm, frame, _, _ = _sample(t2)
    a = FE.tool_access(t2, sm, frame)
    assert a["inaccessible"] and a["inaccessible_area_mm2"] > 50


def test_holes_threads_and_runout():
    s = Box(40, 40, 20) - Pos(0, 0, 4) * Cylinder(1.65, 12)          # 3.3 mm blind hole 12 mm deep from the top
    d = Design("t")
    c = d.add("p", s, material="al6061", process="machined", meta={"threads": [{"size": "M4x0.7", "depth": 8, "at": [0, 0, 10], "axis": [0, 0, -1]}]})
    sm, frame, cyls, holes = _sample(s)
    th = FE.match_threads(FE._thread_callouts(d, c, sm), holes)
    assert th[0]["d"] == 4.0 and th[0]["pitch"] == 0.7 and th[0]["hole"]["d"] == pytest.approx(3.3) and not th[0]["hole"]["through"]
    assert th[0]["plain_below_mm"] == pytest.approx(4.0)


def test_thin_wall_height_and_support():
    # a 1.0 mm fin, 12 mm tall, standing free on a base: one rooted side (unsupported), height about 12 mm
    s = Box(40, 20, 4) + Pos(0, 0, 8) * Box(1.0, 20, 12)
    sm, frame, _, _ = _sample(s)
    w = FE.thin_walls(sm, frame)
    assert w and w[0]["t"] == pytest.approx(1.0, abs=0.02) and not w[0]["supported"] and w[0]["height_mm"] == pytest.approx(12, abs=1.0)
    # the same fin between two posts: rooted on three sides
    s2 = s + Pos(0, -11, 8) * Box(6, 2, 12) + Pos(0, 11, 8) * Box(6, 2, 12)
    sm, frame, _, _ = _sample(s2)
    w = FE.thin_walls(sm, frame)
    assert w and w[0]["supported"]


def test_flat_overhangs_cantilever_bridge_and_angles():
    up = np.array([0.0, 0, 1])
    shelf = Box(10, 20, 20) + Pos(15, 0, 8.5) * Box(20, 20, 3)         # 20 mm shelf off a post, 7 mm above the bed
    fo = FE.flat_overhangs(shelf, up, -10.0)
    assert [f["kind"] for f in fo] == ["cantilever"] and fo[0]["length_mm"] == pytest.approx(20, abs=0.8)
    bridge = Box(4, 20, 20) + Pos(24, 0, 0) * Box(4, 20, 20) + Pos(12, 0, 8.5) * Box(20, 20, 3)
    fo = FE.flat_overhangs(bridge, up, -10.0)
    assert [f["kind"] for f in fo] == ["bridge"] and fo[0]["span_mm"] == pytest.approx(20, abs=1.0)
    d = Design("t")
    c = d.add("p", shelf, material="petg", process="printed")
    sm, frame, cyls, holes = _sample(shelf)
    f = FE.printed_features(d, c, sm, frame, cyls, holes, up=up)
    assert sum(f["overhang_bins"].values()) == pytest.approx(400, rel=0.05)
    c2 = d.add("q", bridge, material="petg", process="printed")
    sm, frame, cyls, holes = _sample(bridge)
    f2 = FE.printed_features(d, c2, sm, frame, cyls, holes, up=up)
    assert sum(f2["overhang_bins"].values()) < 5                        # a 20 mm bridge is a bridge, not an overhang


def test_pins_and_enclosed_void():
    s = Box(30, 30, 3) + Pos(0, 0, 5.5) * Cylinder(0.75, 8)
    d = Design("t")
    c = d.add("p", s, material="petg", process="printed")
    sm, frame, cyls, holes = _sample(s)
    f = FE.printed_features(d, c, sm, frame, cyls, holes, up=np.array([0.0, 0, 1]))
    assert f["pins"] and f["pins"][0]["d"] == pytest.approx(1.5) and f["pins"][0]["height"] == pytest.approx(8)
    hollow = Box(30, 30, 30) - Box(20, 20, 20)
    assert sum(max(0, len(x.shells()) - 1) for x in hollow.solids()) == 1


# ------------------------------------------------------------------------------------- evaluation
def _cnc(**kw):
    f = {"process": "cnc_milling", "material": "al6061", "extents_mm": [20, 50, 80], "volume_mm3": 50000, "access": {"setups": 1, "inaccessible": []},
         "corners": [], "pockets": [], "slots": [], "holes": [], "threads": [], "min_wall_mm": 5.0, "thin_walls": [], "angled_cylinders": 0}
    f.update(kw)
    return f


def _res(feat, sup):
    return {x["rule"]["id"]: x for x in PR.evaluate(feat, sup)}


def test_corner_rules_by_formula():
    f = _cnc(corners=[{"radius": 3.0, "depth": 30.0, "approach": ["+Z"], "at": [0, 0, 0]}])
    jl = _res(f, "jlccnc")["jlccnc.cnc.corner_radius_depth"]          # needs 3.5
    assert jl["status"] == "fail" and jl["limit"] == pytest.approx(3.5)
    sc = _res(f, "sendcutsend")["sendcutsend.cnc.corner_fillet_height"]  # needs max(1.587, 30/5 = 6)
    assert sc["status"] == "fail" and sc["limit"] == pytest.approx(6.0)
    hu = _res(f, "hubs")["hubs.cnc.corner_radius_depth"]
    assert hu["status"] == "fail" and hu["rule"]["severity"] == "warning"
    xo = _res(f, "xometry")["xometry.cnc.corner_ld_ratio"]            # 30 / 6 = 5 > 3
    assert xo["status"] == "fail" and xo["measured"] == pytest.approx(5.0)
    ok = _cnc(corners=[{"radius": 11.0, "depth": 30.0, "approach": ["+Z"], "at": [0, 0, 0]}])
    assert all(x["status"] != "fail" for x in PR.evaluate(ok, "hubs") + PR.evaluate(ok, "jlccnc") + PR.evaluate(ok, "sendcutsend"))


def test_thread_tables_and_conventions():
    th = [{"d": 4.0, "depth": 10.0, "at": [0, 0, 0], "hole": {"d": 3.3, "depth": 15.0, "through": False}, "plain_below_mm": 5.0}]
    f = _cnc(threads=th)
    pl = _res(f, "protolabs")
    assert pl["protolabs.cnc.thread_m4_modelled_d"]["status"] == "pass" and pl["protolabs.cnc.thread_m4_depth_max"]["status"] == "pass"
    assert "protolabs.cnc.thread_m5_modelled_d" not in pl                      # only the M4 row applies
    assert _res(f, "sendcutsend")["sendcutsend.cnc.tap_hole_major"]["status"] == "fail"      # wants 4.0 modelled
    hu = _res(f, "hubs")
    assert hu["hubs.cnc.blind_tap_runout"]["status"] == "fail" and hu["hubs.cnc.blind_tap_runout"]["limit"] == pytest.approx(6.0)
    assert _res(f, "jlccnc")["jlccnc.cnc.blind_tap_runout"]["status"] == "pass"


def test_print_size_band_and_bands_not_interpolated():
    f = {"process": "fdm", "material": "petg", "extents_mm": [15, 20, 60], "min_wall_mm": 1.8, "thin_walls": [], "pins": [], "holes": [],
         "flat_overhangs": [], "overhang_bins": {}, "threads": [], "enclosed_voids": 0, "settings": {"nozzle_mm": 0.4, "line_width_mm": 0.45}}
    jl = _res(f, "jlc3dp")
    assert jl["jlc3dp.fdm.wall_size_100"]["status"] == "fail" and "jlc3dp.fdm.wall_size_50" not in jl   # 60 mm long: the 100 x 100 band
    own = _res(f, "own_printer")
    assert own["own_printer.fdm.wall_one_line"]["limit"] == pytest.approx(0.4) and own["own_printer.fdm.wall_two_lines"]["limit"] == pytest.approx(0.9)
    f["holes"] = [{"d": 1.7, "depth": 5.0, "at": [0, 0, 0]}, {"d": 5.0, "depth": 30.0, "at": [1, 0, 0]}]
    jl = _res(f, "jlc3dp")
    assert jl["jlc3dp.fdm.hole_depth_1.5"]["status"] == "fail" and jl["jlc3dp.fdm.hole_depth_1.5"]["of"] == 1     # the 5 mm hole is not in the table


# ------------------------------------------------------------------------------------ reference parts
def _verify(step, material, process, meta=None, manufacturing=None):
    d = Design("t")
    d.add("p", import_step(str(RP / step)), material=material, process=process, meta=meta or {})
    if manufacturing:
        d.manufacturing = manufacturing
    r = verify_manufacture(d)
    found = {f.data["rule"]: f for f in r.findings if f.code == "supplier_process_rule"}
    summ = next(f for f in r.findings if f.code == "supplier_process_rules_summary")
    return r, found, summ


RP01_THREAD = {"threads": [{"size": "M4x0.7", "depth": 10, "at": [40, 0, 10], "axis": [-1, 0, 0]}]}


def test_rp01_raises_the_expected_cnc_findings():
    r, found, summ = _verify("RP01_cnc_bracket_sharp.step", "al6061", "machined", RP01_THREAD)
    # default CNC supplier Xometry: sharp vertical corners fail the 3:1 corner L:D
    f = found["xometry.cnc.corner_ld_ratio"]
    assert f.severity == "warning" and f.data["count"] == 8 and f.data["source"].startswith("https://www.xometry.com/") and f.data["quote"]
    by = summ.data["by_supplier"]
    # sharp internal pocket corners
    assert "sendcutsend.cnc.sharp_internal" in by["sendcutsend"]["failed"] and "protolabs.cnc.sharp_inside_corners" in by["protolabs"]["failed"]
    assert "jlccnc.cnc.corner_radius_depth" in by["jlccnc"]["failed"]
    # 3 mm slot 16 mm deep (5.3 x its width): Hubs 4 x width, Fictiv 4 x cutter, SendCutSend 3.175 mm minimum cutout
    assert {"hubs.cnc.cavity_depth_width", "fictiv.cnc.pocket_depth_tool"} <= set(by["hubs"]["failed"] + by["fictiv"]["failed"])
    assert "sendcutsend.cnc.cutout_min" in by["sendcutsend"]["failed"]
    # blind M4 tap-drill hole: 5 mm plain below a 10 mm thread is under Hubs' 1.5 d; modelled 3.3 mm, not SendCutSend's major diameter
    assert "hubs.cnc.blind_tap_runout" in by["hubs"]["failed"] and "sendcutsend.cnc.tap_hole_major" in by["sendcutsend"]["failed"]
    assert "protolabs.cnc.thread_m4_modelled_d" not in by["protolabs"]["failed"]
    feats = r.metrics["parts"]["p"]["supplier_process_rules"]["features"]
    assert feats["sharp_vertical_corners"] == 8 and feats["setups"] == 2 and feats["threads"][0]["plain_below_mm"] == pytest.approx(5.0)


def test_rp02_control_passes():
    r, found, summ = _verify("RP02_cnc_plate_clean.step", "al6061", "machined")
    assert not found                                                        # nothing under Xometry
    by = summ.data["by_supplier"]
    for sup in ("xometry", "protolabs", "hubs", "fictiv", "jlccnc", "rapiddirect"):
        assert by[sup]["errors"] == 0 and by[sup]["warnings"] == 0, (sup, by[sup])
    assert by["sendcutsend"]["failed"] == ["sendcutsend.cnc.part_min"]       # 10 mm thick: under SendCutSend's 0.5 in. cube


def test_rp05_raises_the_expected_fdm_findings():
    r, found, summ = _verify("RP05_fdm_clip.step", "petg", "printed", {"print_up": "+Z"})
    assert {"own_printer.fdm.wall_two_lines", "own_printer.fdm.overhang", "own_printer.fdm.cantilever", "own_printer.fdm.pin_min"} <= set(found)
    assert found["own_printer.fdm.wall_two_lines"].data["value"] == pytest.approx(0.6, abs=0.02)
    assert found["own_printer.fdm.overhang"].data["value"] == pytest.approx(400, rel=0.05)
    assert found["own_printer.fdm.cantilever"].data["value"] == pytest.approx(20, abs=0.8)
    assert found["own_printer.fdm.pin_min"].data["value"] == pytest.approx(1.5)
    assert found["own_printer.fdm.overhang"].data["source"] == "mechloop/verifiers/dfm_rules.py"
    by = summ.data["by_supplier"]
    assert {"protolabs.fdm.walls", "protolabs.fdm.feature_min"} <= set(by["protolabs"]["failed"]) and by["protolabs"]["errors"] == 2
    assert "hubs.fdm.walls_unsupported" in by["hubs"]["failed"] and "jlc3dp.fdm.pin_min" in by["jlc3dp"]["failed"]
    assert summ.data["other_print_processes"]["sls"]


@pytest.mark.skipif(shutil.which("prusa-slicer") is None, reason="prusa-slicer not installed")
def test_rp05_prusaslicer_agrees_support_is_needed():
    r, found, summ = _verify("RP05_fdm_clip.step", "petg", "printed", {"print_up": "+Z"}, {"prusaslicer_crosscheck": True})
    x = next(f for f in r.findings if f.code == "supplier_process_prusaslicer_crosscheck")
    assert x.data["agree"] and x.data["prusaslicer"]["support_mm"] > 50
