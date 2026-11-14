"""Manufacturability checks."""
from build123d import Box, Cylinder, Pos

from mechloop.model import Design
from mechloop.verifiers.manufacture import verify_manufacture


def codes(r):
    return [f.code for f in r.findings]


def test_plate_with_a_sharp_pocket_corner_and_odd_thickness():
    d = Design("p")
    d.add("plate", Box(80, 60, 6.5) - Pos(10, 0, 0) * Box(30, 20, 6.5), material="al6061")   # square window
    r = verify_manufacture(d)
    assert {"sharp_inside_corner", "non_stock_thickness"} <= set(codes(r))
    assert r.metrics["parts"]["plate"]["sharp_inside_corners"] == 4
    # the same window with a round end mill's radius in the corners, in stock thickness, is fine
    from build123d import RectangleRounded, extrude
    win = extrude(RectangleRounded(30, 20, 2.0), 3, both=True)
    d2 = Design("p2")
    d2.add("plate", Box(80, 60, 6) - Pos(10, 0, 0) * win, material="al6061")
    assert codes(verify_manufacture(d2)) == []


def test_block_needing_many_setups_and_a_simple_one():
    blk = Box(60, 60, 60)
    for dx, dy, dz in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1)):
        blk -= Pos(25 * dx, 25 * dy, 25 * dz) * Box(20, 20, 20)                 # a pocket in five faces
    d = Design("b")
    d.add("block", blk, material="al6061")
    r = verify_manufacture(d)
    assert "many_setups" in codes(r) and r.metrics["parts"]["block"]["setups_estimate"] >= 5
    d2 = Design("b2")
    d2.add("block", Box(60, 60, 60) - Pos(0, 0, 25) * Box(20, 20, 10), material="al6061")
    assert verify_manufacture(d2).metrics["parts"]["block"]["setups_estimate"] == 1


def test_printed_part_orientation_support_and_size():
    d = Design("t")
    tee = Pos(0, 0, 5) * Box(20, 20, 10) + Pos(0, 0, 13) * Box(80, 20, 6)       # a T: flat arm over a narrow stem
    d.add("tee", tee, material="petg")
    r = verify_manufacture(d)
    row = r.metrics["parts"]["tee"]
    assert row["up"] in ("-Z", "+Y", "-Y")           # arm down on the bed, or on its side: no overhang
    assert row["support_area_mm2"] < 50 and "needs_support" not in codes(r)
    d2 = Design("big")
    d2.add("panel", Box(400, 300, 4), material="abs")
    c2 = codes(verify_manufacture(d2))
    assert "too_big_to_print" in c2 and "print_warp_risk" in c2
