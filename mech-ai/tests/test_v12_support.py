"""printer_v12 support: the sheet unfolder, build stages in DG-07, the HNTP5 nut and HIWIN parts."""
import math

import pytest


def _bent_L(t, r, h_a, l_b, w, holes_b=()):
    from build123d import Box, Cylinder, Pos, Rot

    c = t + r
    leg_a = Pos(t / 2, 0, (c + h_a) / 2) * Box(t, w, h_a - c)
    leg_b = Pos((c + l_b) / 2, 0, t / 2) * Box(l_b - c, w, t)
    ring = (Pos(c, 0, c) * Rot(90, 0, 0) * (Cylinder(c, w) - Cylinder(r, w))) & (Pos(c / 2, 0, c / 2) * Box(c, w, c))
    s = leg_a + leg_b + ring
    for x, y, dia in holes_b:
        s -= Pos(x, y, t / 2) * Cylinder(dia / 2, t)
    return s


def test_unfold_one_bend_matches_hand_calc(tmp_path):
    from mechloop.unfold import unfold, unfold_check, write_flat_dxf

    t, r = 2.286, 0.81
    L = _bent_L(t, r, 13.0, 20.0, 30.0, holes_b=[(12, 5, 3.4), (12, -5, 3.4)])
    res = unfold(L, 0.37)
    assert res["bends"] == 1
    ba = math.pi / 2 * (r + 0.37 * t)
    assert res["bend_allowance_mm"] == pytest.approx(ba, abs=1e-3)
    w = write_flat_dxf(res, tmp_path / "L.dxf")
    assert w["faces"] == 1
    assert max(w["extent_mm"]) == pytest.approx(30.0, abs=0.01)
    assert min(w["extent_mm"]) == pytest.approx((13.0 - t - r) + ba + (20.0 - t - r), abs=0.02)
    assert unfold_check(w["area_mm2"], res["thickness"], L.volume)["ok"]


def test_unfold_check_catches_a_top_face_flat():
    from mechloop.unfold import unfold_check

    assert not unfold_check(2.29 * 23.9, 2.286, 2000.0)["ok"]


def test_hntp5_fits_the_hfs5_cavity():
    from mechloop.parts.batch12 import tnut_hntp5

    st = tnut_hntp5()
    assert st.interfaces["span_bottom"] <= 7.48 and st.interfaces["body_height"] == 3.2
    assert tnut_hntp5(True).shape.bounding_box().min.X == pytest.approx(-11.0, abs=0.01)


def test_stage_of_inherits_from_the_screw():
    from mechloop import Design
    from mechloop.verifiers.purchased import stage_of

    d = Design("t")
    d.add("a", __import__("build123d").Box(1, 1, 1), meta={"build_stage": 1})
    c = d.add("b", __import__("build123d").Box(1, 1, 1), meta={"screw": "a"})
    assert stage_of(c, d) == 1


def test_connector_remakes_match_their_drawings():
    from mechloop.parts import batch12 as b, vendor_cad as vc
    for n, length in ((2, 7.3), (3, 9.8), (4, 12.3)):           # JST XH p.4 table, dimension B
        st = b.jst_xhp_housing(n)
        assert abs(st.shape.bounding_box().size.X - length) < 1e-6
        assert vc.model_state(st.model) == "faithful re-make"
    hb = b.jst_xh_header(4).shape.bounding_box()                   # p.5: B 12.4, 7 above the board, posts 3.4 below
    assert abs(hb.size.X - 12.4) < 1e-6 and abs(hb.max.Z - 7.0) < 1e-6 and abs(hb.min.Z + 3.4) < 1e-6
    mb = b.molex_minifit_39_01_2020().shape.bounding_box()         # SD-5557-003 / Molex STEP: 5.40 wide, 19.6 long
    assert (round(mb.size.X, 2), round(mb.size.Y, 2)) == (5.4, 19.6)
    assert vc.model_state(b.din_rail_phoenix(60).model) in ("supplier CAD", "faithful re-make")
