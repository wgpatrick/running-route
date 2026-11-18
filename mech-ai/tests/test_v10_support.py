"""Checks for the support code added with printer_v10: the ninth catalogue batch (235 mm print sheet), the allowable screw
tilt in the bed-support checker (`tilt_allowance`), and printer_v10's own declared facts (frame unchanged from v9, three
levelling points, the X travel its 288 mm beam allows)."""
import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from build123d import Location

from mechloop import parts as P
from mechloop.model import MATERIALS, Design
from mechloop.parts import place, vendor_data
from mechloop.report import VerifierResult
from mechloop.verifiers import bed_support as BS

sys.path.insert(0, str(Path(__file__).parent))
from test_known_answers_fit import bed_machine, support            # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
THREE = ((-90.0, -90.0), (90.0, -90.0), (0.0, 120.0))
WEB = {"length_mm": 30.0, "width_mm": 24.0, "thickness_mm": 1.6, "material": "al6061", "kt_in_plane": 1.7}
ROT = {"about_float_axis": 2.0e6, "about_across": 2.0e4, "about_travel": 3.0e4}


def _size(st):
    bb = st.shape.bounding_box()
    return bb.size.X, bb.size.Y, bb.size.Z


# ---------------------------------------------------------------- batch 9 catalogue part
def test_print_sheet_235_says_what_is_not_published():
    """235 x 235 x 0.4 mm of steel: 0.1734 kg, computed; secondary source; the listings' thickness conflict is recorded."""
    v = vendor_data("creality_pei235")
    st = P.print_sheet_pei235()
    assert _size(st) == pytest.approx((235.0, 235.0, 0.4)) and st.mass_kg == pytest.approx(235 * 235 * 0.4 * 7.85e-6, abs=1e-4)
    assert st.catalog and not st.verified and st.source["level"] == "secondary" and v["source_level"] == "secondary"
    assert st.interfaces["magnetic_base_thickness"] is None and st.sku == "SHEET-PEI-235"
    assert any("thickness" in f for f in st.source["unverified_fields"]) and "1.2" in v["values"]["steel_thickness_mm"]["note"]


def test_print_sheet_235_places_without_uncatalogued_warning_and_is_listed_unverified():
    from mechloop.verifiers.ratings import verify_ratings

    d = Design("b9")
    place(d, "sheet", P.print_sheet_pei235(), Location((0, 0, 0)))
    r = verify_ratings(d)
    assert not [f for f in r.findings if f.code == "uncatalogued_cots"]
    assert "SHEET-PEI-235" in set(r.metrics["unverified_parts"])


# ---------------------------------------------------------------- allowable screw tilt
def machine(rot=ROT, web=WEB, nut_tilt=None, per_rail=1, sync="independent"):
    """The test bed on three screws, one block per rail, each block on a mount that floats along Y (the rails stand on the
    back wall) with the given turning stiffness and web."""
    d = bed_machine(screws=THREE, blocks_per_rail=per_rail, sync=sync)
    for c in d.components:
        if c.meta.get("guides") == "z" and rot is not None:
            c.meta["guide_float"] = {"axis": (0, -1, 0), "stiffness_n_per_mm": 250.0, "range_mm": 0.3, "rotation_n_mm_per_rad": dict(rot)}
            if web:
                c.meta["guide_float"]["web"] = dict(web)
    if nut_tilt is not None:
        d.joints[-1].drive["nut_tilt_allowance_rad"] = nut_tilt
    return d


def allowance(d):
    m, r = support(d)
    return m["tilt_allowance"], m, r


def test_one_screw_high_tilts_the_bed_by_one_over_the_triangles_height():
    """Screws at (-90, -90), (90, -90), (0, 120): the rear one 1 mm high turns the bed 1 / 210 rad about X (4.76 mrad) when
    the guides are soft beside the screws; across the 180 mm print area that is 0.857 mm. A front screw 1 mm high: the
    bed turns about the line through the other two, 1 mm over that line's distance from the screw."""
    ta, _, _ = allowance(machine())
    rear = ta["per_screw"]["nut2"]
    assert rear["tilt_mrad_per_mm"] == pytest.approx(1000.0 / 210.0, rel=0.02)
    assert rear["bed_level_change_across_print_area_mm_per_mm"] == pytest.approx(180.0 / 210.0, rel=0.02)
    # distance of (-90, -90) from the line through (90, -90) and (0, 120)
    a, b, p = np.array([90.0, -90.0]), np.array([0.0, 120.0]), np.array([-90.0, -90.0])
    t = (b - a) / np.linalg.norm(b - a)
    dist = abs(t[0] * (p - a)[1] - t[1] * (p - a)[0])
    assert ta["per_screw"]["nut0"]["tilt_mrad_per_mm"] == pytest.approx(1000.0 / dist, rel=0.02)


def test_block_moment_is_the_series_stiffness_times_the_tilt_and_its_limit_a_third_of_the_static_rating():
    """Rear screw high: the bed turns about X. The rails stand on the back wall (mount-face normal Y, across X), so each
    block is turned about its ACROSS axis: moment = theta / (1 / (k L^2 / 12) + 1 / about_across). Its share of the static
    rating is that over MP (plus nothing else: no force), and the limit is where it reaches 1 / 3."""
    d = machine()
    ta, m, _ = allowance(d)
    blk = next(c for c in d.components if c.name == "blk00")
    g = next(s for s in BS.support_model(d, BS.layout(d))["supports"] if s["name"] == "blk00")
    k, L = g["k_n_per_um"] * 1e3, g["track_mm"]
    kap = 1.0 / (1.0 / (k * L ** 2 / 12.0) + 1.0 / ROT["about_across"])
    row = ta["per_screw"]["nut2"]
    th = row["tilt_mrad_per_mm"] * 1e-3
    b = row["guide_blocks"]["blk00"]
    assert abs(b["per_mm"]["moment_across_nm"]) == pytest.approx(kap * th * 1e-3, rel=0.02)
    assert abs(b["per_mm"]["moment_about_mount_normal_nm"]) < 1e-3
    assert b["static_rating_used_per_mm"] == pytest.approx(kap * th * 1e-3 / blk.ratings["static_moment_mp_nm"], rel=0.05)
    assert b["block_limit_mm"] == pytest.approx(1.0 / (BS.TILT_STATIC_SAFETY * b["static_rating_used_per_mm"]), rel=0.02)
    assert ta["static_safety"] == 3.0


def test_web_stress_follows_the_declared_web_and_limits_at_half_yield():
    """A front screw high turns the bed about a slanted axis, so each block is also turned about its mount's normal: the
    web is bent in its own plane, 6 M / (t w^2) x kt, and out of it, 6 M / (w t^2). The allowed stress is half of 6061-T6's
    yield (138 MPa); the web's limit is that over the stress per mm."""
    ta, _, _ = allowance(machine())
    b = ta["per_screw"]["nut0"]["guide_blocks"]["blk00"]
    mn, mt = abs(b["per_mm"]["moment_about_mount_normal_nm"]) * 1e3, abs(b["per_mm"]["moment_across_nm"]) * 1e3
    parts = b["per_mm"]["web_stress_parts_mpa"]
    assert mn > 100.0
    assert parts["in_plane"] == pytest.approx(6.0 * mn / (1.6 * 24.0 ** 2) * 1.7, rel=0.01)
    assert parts["out_of_plane"] == pytest.approx(6.0 * mt / (24.0 * 1.6 ** 2), rel=0.01)
    allow = 0.5 * MATERIALS["al6061"].yield_mpa
    assert b["web_stress_allowed_mpa"] == pytest.approx(allow, abs=0.1) and ta["web_yield_fraction"] == 0.5
    assert b["web_limit_mm"] == pytest.approx(allow / b["per_mm"]["web_stress_mpa"], rel=0.02)
    # no web declared: the blocks are still judged, the webs are not
    ta2, _, _ = allowance(machine(web=None))
    assert "web_limit_mm" not in ta2["per_screw"]["nut0"]["guide_blocks"]["blk00"]
    assert not any("web stress" in k for k in ta2["per_screw"]["nut0"]["limits_mm"])


def test_stiffer_mounts_allow_less_tilt_and_rigid_blocks_least():
    """Ten times the mount's turning stiffness: the blocks carry more moment per mm, so the height one screw may stand out
    of plane falls; blocks with no floating mount at all (rigid) allow least."""
    soft, _, _ = allowance(machine())
    stiff, _, _ = allowance(machine(rot={k: 10.0 * v for k, v in ROT.items()}))
    rigid, _, _ = allowance(machine(rot=None))
    assert soft["overload_free_mm"] > stiff["overload_free_mm"] > rigid["overload_free_mm"] > 0
    assert "static moment" in rigid["first_limit"]


def test_seated_range_is_the_seating_studys_unloading_height():
    """`seated_up_to_mm` is the least height error at which a nut's seating load reaches zero: the same figure the nut
    seating study reports per nut."""
    ta, m, _ = allowance(machine())
    nuts = m["nut_seating_and_lead_error"]["nuts"]
    assert ta["seated_up_to_mm"] == pytest.approx(min(v["unloads_at_height_error_mm"] for v in nuts.values()), abs=2e-3)
    assert ta["routine_height_error_mm"] == pytest.approx(m["nut_seating_and_lead_error"]["levels"][2]["height_error_mm"])


def test_nut_seat_limit_is_the_declared_rocking_angle_over_the_tilt_per_mm():
    """drive['nut_tilt_allowance_rad'] = 2 mrad: the rear screw (4.76 mrad per mm) may stand 0.42 mm high. Not declared:
    the nut seats are not judged, and the metrics say so."""
    ta, _, _ = allowance(machine(nut_tilt=0.002))
    row = ta["per_screw"]["nut2"]
    assert row["nut_seat_limit_mm"] == pytest.approx(0.002 / (row["tilt_mrad_per_mm"] * 1e-3), rel=0.01) == pytest.approx(0.42, abs=0.01)
    assert ta["overload_free_mm"] <= row["nut_seat_limit_mm"] + 1e-9 and "nut seats" in ta["first_limit"]
    ta0, _, _ = allowance(machine())
    assert ta0["nut_tilt_allowance_rad"] is None and "not declared" in ta0["nut_tilt_basis"]
    assert "nut_seat_limit_mm" not in ta0["per_screw"]["nut2"]


def test_findings_info_when_inside_warning_when_the_routine_error_already_overloads():
    """The allowance is reported as an info finding; when it is smaller than the routine height error (LSC-015 budget) the
    finding is the warning z_tilt_allowance_exceeded. Belt-tied screws cannot be driven apart: no allowance is worked out."""
    _, m, r = allowance(machine())
    codes = {f.code: f.severity for f in r.findings}
    assert codes.get("z_tilt_allowance") == "info" and "z_tilt_allowance_exceeded" not in codes
    assert m["tilt_allowance"]["overload_free_over_routine"] > 1.0
    ta, m2, r2 = allowance(machine(nut_tilt=1e-5))
    w = [f for f in r2.findings if f.code == "z_tilt_allowance_exceeded"]
    assert w and w[0].severity == "warning" and ta["overload_free_mm"] < ta["routine_height_error_mm"]
    belt, _ = support(machine(sync="belt"))
    assert "tilt_allowance" not in belt


def test_across_print_area_is_the_height_times_the_level_change_per_mm():
    ta, _, _ = allowance(machine(nut_tilt=0.003))
    g = ta["per_screw"][ta["governing_screw"]]
    assert ta["across_print_area_mm"] == pytest.approx(ta["overload_free_mm"] * g["bed_level_change_across_print_area_mm_per_mm"], abs=2e-3)
    assert ta["overload_free_mm"] == min(v["overload_free_up_to_mm"] for v in ta["per_screw"].values())


# ---------------------------------------------------------------- printer_v10 itself (builds two designs: about a minute)
def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "designs" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, mod.build()


@pytest.fixture(scope="module")
def v9_v10():
    return _load("printer_v9"), _load("printer_v10")


def _bb(c):
    b = c.shape.bounding_box()
    return tuple(round(v, 3) for v in (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z))


def test_v10_frame_extrusions_and_envelope_are_v9s(v9_v10):
    """Every frame member, post and Z upright of v9 is in v10 with the same catalogue part in the same place, and the
    brief's envelope is the same."""
    (m9, d9), (m10, d10) = v9_v10
    frame = [c for c in d9.components if c.name.startswith(("frame_", "post_", "upright_"))]
    assert len(frame) == 15
    for c in frame:
        c10 = d10.get(c.name)
        assert c10.sku == c.sku and _bb(c10) == _bb(c), c.name
    assert tuple(d10.envelope) == tuple(d9.envelope) and (m10.FX, m10.FY, m10.FZ, m10.FD) == (m9.FX, m9.FY, m9.FZ, m9.FD)
    # the carrier's square is v9's too (only its height in the machine moved with the thicker plate)
    for n in ("sq_left", "sq_right", "sq_front", "sq_rear"):
        a, b = _bb(d9.get(n)), _bb(d10.get(n))
        assert d10.get(n).sku == d9.get(n).sku and a[:2] == b[:2] and a[3:5] == b[3:5]


def test_v10_x_travel_is_the_rail_limit_and_y_is_v9s(v9_v10):
    (m9, d9), (m10, d10) = v9_v10
    jx9, jx10 = (next(j for j in d.joints if j.name == "x") for d in (d9, d10))
    jy9, jy10 = (next(j for j in d.joints if j.name == "y") for d in (d9, d10))
    assert jx9.range[1] - jx9.range[0] == pytest.approx(180.0) and jx10.range[1] - jx10.range[0] == pytest.approx(229.6)
    assert jy10.range == jy9.range and jy10.overtravel == jy9.overtravel
    rail, blk = d10.get("x_rail").shape.bounding_box(), d10.get("x_carriage").shape.bounding_box()
    lo, hi = jx10.mechanical_range
    assert rail.size.X == pytest.approx(288.0) == pytest.approx(d10.get("x_beam").shape.bounding_box().size.X)
    assert min(blk.min.X + lo - rail.min.X, rail.max.X - blk.max.X - hi) == pytest.approx(5.0, abs=1e-6)
    # the toolhead is centred on the block: what is below the top rails' tops stays 2 mm or more inside their inner faces
    xs = [c.shape.bounding_box() for c in d10.components if c.body == "xbody" and c.shape.bounding_box().min.Z < m10.FZ + 10.0]
    assert min(b.min.X for b in xs) + lo + 150.0 >= 1.9 and 150.0 - (max(b.max.X for b in xs) + hi) >= 1.9
    assert d10.tool_point[1][0] == pytest.approx(-15.5) and [e["at"] for e in d10.endstops if e["joint"] == "x"] == ["max"]
    assert not [c.name for c in d10.components if c.name.startswith("x_rail_stop")]


def test_v10_bed_is_three_sprung_points_under_a_sheet_the_reach_nearly_fills(v9_v10):
    _, (m10, d10) = v9_v10
    studs = sorted(c.name for c in d10.components if c.name in ("bed_stud_0", "bed_stud_1", "bed_stud_2", "bed_stud_3"))
    assert studs == ["bed_stud_0", "bed_stud_1", "bed_stud_2"]
    assert len([c for c in d10.components if c.sku == "SPRING-DIE-DJ-8X20YCS"]) == 3
    assert len([c for c in d10.components if c.sku == "THUMBNUT-DIN466-M4"]) == 3
    sheet, plate = d10.get("bed").shape.bounding_box(), d10.get("bed_plate").shape.bounding_box()
    assert (sheet.size.X, sheet.size.Y) == pytest.approx((235.0, 235.0)) and plate.size.Z == pytest.approx(12.7)
    px, py = d10.printer["print_area"]
    assert px * py / (235.0 * 235.0) == pytest.approx(0.892, abs=0.002)
    # no thread in the plate: each stud is clamped through it and runs in its thumb nut
    for i in range(3):
        st = d10.get(f"bed_stud_{i}")
        assert "bed_plate" not in (st.meta.get("threads_into") or []) and f"bed_thumb_{i}" in st.meta["threads_into"]
    # spring: 8 mm compressed, 60.8 N, inside the maker's 10 mm at the strong end of the +/-1.5 mm levelling range
    spr = d10.get("bed_spring_0")
    assert spr.ratings["preload_n"] == pytest.approx(60.8) and 20.0 - m10.SPRING_H + m10.LEVEL_RANGE <= 10.0


def test_v10_motor_tilt_allowance_on_the_support_model(v9_v10):
    """Without the FEA (support model only): one Z motor may stand more than a millimetre out of plane before the first
    limit, which is more than three times the routine height error, and the nuts stay seated over the routine error."""
    _, (m10, d10) = v9_v10
    out = BS.bed_support(d10, VerifierResult("fea"), with_fea=False)
    ta = out["tilt_allowance"]
    assert ta["nut_tilt_allowance_rad"] == pytest.approx(0.1 / 22.0)
    assert ta["overload_free_mm"] >= 3.0 * ta["routine_height_error_mm"] and ta["seated_up_to_mm"] >= ta["routine_height_error_mm"]
    assert 1.0 < ta["overload_free_mm"] < 2.0 * m10.LEVEL_RANGE
    lims = ta["per_screw"]["z_nut"]["limits_mm"]
    assert any("web stress" in k for k in lims) and any("static moment" in k for k in lims) and any("nut seats" in k for k in lims)
