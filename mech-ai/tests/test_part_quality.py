"""Part-quality verifier: each check fires on a small part built to have that defect, and a clean part passes."""
from __future__ import annotations

import pytest
from build123d import Box, Cylinder, Pos, Rot

import mechloop  # noqa: F401
from mechloop.model import Design
from mechloop.parts import Stock, place
from mechloop.verifiers import part_quality as pq


def codes(shape, process="machined"):
    return {f["code"] for f in pq.intrinsic_checks(shape, process)}


def plate_with_hole():
    return Box(40, 30, 5) - Cylinder(2.75, 5)       # 40 x 30 x 5, one 5.5 mm hole


def test_clean_part_passes():
    assert codes(plate_with_hole()) == set()


def test_not_one_solid():
    two = Box(10, 10, 10) + Pos(30, 0, 0) * Box(10, 10, 10)
    assert "not_one_solid" in codes(two)


def test_internal_void():
    s = Box(20, 20, 20) - Box(5, 5, 5)          # a cavity fully inside
    assert "internal_void" in codes(s)


def test_tiny_edge_and_sliver():
    s = Box(20, 20, 5) + Pos(19.9, 0.03, 0) * Box(20, 20, 5)    # shifted 0.03 mm: 0.03 mm edges and step faces
    c = codes(s)
    assert "tiny_edge" in c and "sliver_face" in c


def test_small_step():
    s = Box(20, 20, 5) + Pos(15, 0, 0.2) * Box(10, 20, 5)        # top faces 0.2 mm apart
    assert "small_step" in codes(s)


def test_near_coincident_faces():
    # a 0.1 mm slit between two blocks joined at their far end
    s = Pos(0, 0, 0) * Box(10, 20, 10) + Pos(10.1, 0, 0) * Box(10, 20, 10) + Pos(5.05, 15, 0) * Box(20.1, 10, 10)
    assert "near_coincident_faces" in codes(s)


def test_thin_wall():
    s = Box(20, 20, 10) - Pos(0, 0, 0.5) * Box(19.6, 19.6, 10)   # 0.2 mm side walls, printed
    assert "thin_wall" in codes(s, "printed")


def test_near_parallel_faces():
    s = Box(20, 20, 5) + Pos(5, 0, 0) * Rot(0, 0.5, 0) * Box(20, 20, 5)     # top faces cross at 0.5 deg
    assert "near_parallel_faces" in codes(s)


def test_weak_attachment():
    # a 10 x 10 x 10 block on a plate, overlapping its edge by a 0.3 mm strip
    s = Box(30, 30, 3) + Pos(15 + 5 - 0.3, 0, 1.5 + 5) * Box(10, 10, 10)
    assert "weak_attachment" in codes(s)


def test_sparse_bbox():
    s = Box(100, 2, 2) + Pos(0, 49, 49) * Box(2, 100, 2) + Pos(49, 0, 49) * Box(2, 2, 100)
    s = Box(200, 1, 1) + Pos(99.5, 99.5, 0) * Box(1, 200, 1) + Pos(99.5, 199, 99.5) * Box(1, 1, 200)
    assert "sparse_bbox" in codes(s)


def test_odd_dims():
    s = Box(40.37, 30, 5) - Cylinder(2.63, 5)
    c = codes(s)
    assert {"odd_dimension", "odd_hole_diameter"} <= c
    assert "nonstandard_hole" in codes(Box(40, 30, 5) - Cylinder(3.85, 5))


def _design():
    d = Design("t")
    d.add("plate", Pos(0, 0, 2.5) * plate_with_hole(), material="al6061", process="machined")
    return d


def test_hole_unused_and_used():
    d = _design()
    res = pq.verify_part_quality(d)
    assert any(f.code == "hole_unused" for f in res.findings)
    d.add("pin", Pos(0, 0, 2.5) * Cylinder(2.5, 12), material="steel", cots=True)
    res = pq.verify_part_quality(d)
    assert not any(f.code == "hole_unused" for f in res.findings)


def test_allowed_overlap_and_join_note():
    d = _design()
    d.add("block", Pos(0, 0, 4) * Box(10, 10, 10), material="abs", cots=True)
    d.allow_overlap("plate", "block")
    d.join("plate", "block", "held by its own ring nut")
    res = pq.verify_part_quality(d)
    c = {f.code for f in res.findings}
    assert "allowed_overlap_large" in c and "attachment_not_drawn" in c
    row = res.metrics["overlaps"]["rows"][0]
    assert row["volume_mm3"] > 100


def test_stock_hole_missing():
    d = _design()
    st = Stock(Box(10, 10, 10), "X", "a box that says it has holes", 0.01, interfaces={"mount_holes_m3": [(3, 3, 5), (-3, -3, 5)]})
    place(d, "boxpart", st)
    res = pq.verify_part_quality(d)
    assert any(f.code == "stock_hole_missing" and f.data["part"] == "boxpart" for f in res.findings)
    st2 = Stock(Box(10, 10, 10) - Pos(3, 3, 0) * Cylinder(1.25, 10) - Pos(-3, -3, 0) * Cylinder(1.25, 10), "Y", "has them", 0.01,
                interfaces={"mount_holes_m3": [(3, 3, 5), (-3, -3, 5)]})
    place(d, "boxpart2", st2)
    res = pq.verify_part_quality(d)
    assert not any(f.code == "stock_hole_missing" and f.data["part"] == "boxpart2" for f in res.findings)


def test_envelope():
    d = _design()
    d.get("plate").meta["envelope"] = ((-15, -15, 0), (15, 15, 5))
    res = pq.verify_part_quality(d)
    assert any(f.code == "outside_envelope" for f in res.findings)


def test_runner_opt_in():
    from mechloop.runner import ORDER, OPTIONAL, verify

    assert "part_quality" not in ORDER and "part_quality" in OPTIONAL
    rep = verify(_design(), only=["part_quality"])
    assert [r.verifier for r in rep.results if r.verifier != "requirements"] == ["part_quality"]
