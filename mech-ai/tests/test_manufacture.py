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


# ---------------------------------------------------------------------------------------------------
# One part that breaks each rule and one that does not. Small parts, coarse sampling: the whole file
# runs in a few seconds.
import pytest
from build123d import Align, Axis, Cone

from mechloop.model import LoadCase
from mechloop.parts import add_screw
from mechloop.verifiers import dfm_rules
from mechloop.verifiers.manufacture import export_flat_patterns


def check(shape, material="al6061", man=None, screws=(), loads=(), **kw):
    d = Design("t")
    if man:
        d.manufacturing = man
    d.add("p", shape, material=material, **kw)
    for i, (size, length, at, direction) in enumerate(screws):
        add_screw(d, f"s{i}", size, length, at=at, direction=direction, threads_into="p")
    for name, force in loads:
        d.loadcases.append(LoadCase(name, "p", fixed=lambda f: True, loaded=lambda f: True, force=force))
    r = verify_manufacture(d)
    return r, {f.code: f for f in r.findings}, r.metrics["parts"]["p"]


def sev(found, code):
    return found[code].severity if code in found else None


# ------------------------------------------------------------------------------------ declaring it
def test_process_is_explicit_and_overridable():
    assert check(Box(40, 30, 3), process="sheet")[2]["process"] == "sheet"
    assert check(Box(40, 30, 3), process="laser")[2]["process"] == "sheet"            # aliases
    assert check(Box(40, 30, 3), material="petg")[2]["process"] == "printed"          # from the material
    assert check(Box(40, 30, 3), material="petg", process="cnc")[2]["process"] == "machined"
    assert check(Box(40, 30, 3), meta={"process": "sheet"})[2]["process"] == "sheet"  # the older spelling
    r, found, _ = check(Box(40, 30, 3), process="cast")
    assert "bad_manufacturing_declaration" in found and not r.ok


def test_every_finding_says_where_how_much_and_why():
    r, found, _ = check(Box(100, 60, 3) - Pos(20, 0, 0) * Cylinder(0.6, 3), process="sheet")
    f = found["hole_too_small_to_cut"]
    assert f.data["part"] == "p" and f.data["at"][0] == [20.0, 0.0, 0.0]
    assert f.data["value"] == pytest.approx(1.2) and f.data["limit"] == 0.5 and f.data["rule"] == "sheet.hole_min_t_ratio"
    assert f.data["source"].startswith("https://sendcutsend.com/") and f.data["hint"]


def test_a_design_can_override_a_limit_and_every_rule_has_a_source():
    part = Box(100, 60, 3) - Pos(20, 0, 0) * Cylinder(0.6, 3)
    assert "hole_too_small_to_cut" in check(part, process="sheet")[1]
    r, found, _ = check(part, process="sheet", man={"limits": {"sheet.hole_min_t_ratio": 0.3}})
    assert "hole_too_small_to_cut" not in found and r.metrics["limits_overridden"] == ["sheet.hole_min_t_ratio"]
    assert "bad_manufacturing_declaration" in check(part, process="sheet", man={"limits": {"sheet.no_such_rule": 1}})[1]
    assert "hole_too_small_to_cut" not in check(part, process="sheet", meta={"dfm": {"limits": {"sheet.hole_min_t_ratio": 0.3}}})[1]
    for rule in dfm_rules.RULES.values():
        assert rule.source in dfm_rules.SOURCES and rule.severity in ("error", "warning", "info")


# ------------------------------------------------------------------------------------- 2D cut parts
PLATE = Box(100, 60, 3)


def test_sheet_clean_part_passes_and_reports_its_profile():
    r, found, row = check(PLATE - Pos(20, 0, 0) * Cylinder(3, 3), process="sheet")
    assert not found
    assert row["form"] == "flat" and row["thickness_mm"] == 3 and row["stock_mm"] == 3.0 and row["flat_size_mm"] == [100.0, 60.0]
    assert row["holes"] == 1 and row["smallest_hole_mm"] == 6.0 and row["through_cut_only"] and row["pierces"] == 2


def test_sheet_must_be_one_thickness_cut_through():
    assert sev(check(PLATE - Pos(0, 0, 1) * Box(20, 20, 1), process="sheet")[1], "not_2d_profile") == "error"     # a pocket
    assert sev(check(Box(30, 30, 30), process="sheet")[1], "not_sheet") == "error"
    assert sev(check(Box(100, 60, 6.5), process="sheet")[1], "non_stock_thickness") == "error"
    assert sev(check(Box(100, 60, 30), process="sheet")[1], "sheet_thickness") == "error"                         # plate, not sheet
    assert "sheet_thickness" not in check(Box(100, 60, 6), process="sheet")[1]


def test_sheet_hole_size_against_thickness_and_cutting_method():
    small = PLATE - Pos(20, 0, 0) * Cylinder(0.6, 3)          # 1.2 mm hole in 3 mm
    medium = PLATE - Pos(20, 0, 0) * Cylinder(1.2, 3)         # 2.4 mm: over half the thickness, under the thickness
    assert sev(check(small, process="sheet")[1], "hole_too_small_to_cut") == "error"
    assert sev(check(medium, process="sheet")[1], "hole_smaller_than_thickness") == "warning"
    assert "hole_too_small_to_cut" not in check(medium, process="sheet")[1]
    assert sev(check(medium, process="sheet", man={"sheet": {"method": "router"}})[1], "hole_too_small_to_cut") == "error"   # 3.175 mm bit


def test_sheet_webs_between_holes_and_to_the_edge():
    assert sev(check(PLATE - Pos(46, 0, 0) * Cylinder(3, 3), process="sheet")[1], "hole_too_close_to_edge") == "warning"   # 1 mm web
    assert sev(check(PLATE - Pos(46.9, 0, 0) * Cylinder(3, 3), process="sheet")[1], "hole_too_close_to_edge") == "error"   # under the kerf
    r, found, _ = check(PLATE - Cylinder(3, 3) - Pos(8, 0, 0) * Cylinder(3, 3), process="sheet")
    assert found["holes_too_close"].data["value"] == pytest.approx(2.0, abs=0.01)
    assert not check(PLATE - Cylinder(3, 3) - Pos(14, 0, 0) * Cylinder(3, 3), process="sheet")[1]


def test_sheet_thin_tabs_and_narrow_slots():
    assert sev(check(PLATE + Pos(60, 0, 0) * Box(20, 1.5, 3), process="sheet")[1], "thin_feature") == "warning"
    assert "thin_feature" not in check(PLATE + Pos(60, 0, 0) * Box(20, 6, 3), process="sheet")[1]
    assert sev(check(PLATE - Pos(40, 0, 0) * Box(20, 1.0, 3), process="sheet")[1], "narrow_slot") == "warning"
    assert sev(check(PLATE - Pos(40, 0, 0) * Box(20, 0.2, 3), process="sheet")[1], "narrow_slot") == "error"      # under the kerf
    assert "narrow_slot" not in check(PLATE - Pos(40, 0, 0) * Box(20, 4, 3), process="sheet")[1]


def test_sheet_inside_corners_depend_on_the_cutter():
    window = PLATE - Box(30, 20, 3)
    assert "sharp_inside_corner" not in check(window, process="sheet")[1]                 # a laser's corner is 0.15 mm
    r, found, row = check(window, process="sheet", man={"sheet": {"method": "router"}})
    assert sev(found, "sharp_inside_corner") == "warning" and len(found["sharp_inside_corner"].data["at"]) == 4
    from build123d import RectangleRounded, extrude
    rounded = PLATE - extrude(RectangleRounded(30, 20, 2.0), 1.5, both=True)
    assert "sharp_inside_corner" not in check(rounded, process="sheet", man={"sheet": {"method": "router"}})[1]


def test_sheet_size_grilles_and_secondary_operations():
    assert sev(check(Box(8, 5, 3), process="sheet")[1], "small_part_needs_tabs") == "warning"
    assert sev(check(Box(3200, 100, 3), process="sheet")[1], "too_big_to_cut") == "warning"
    grille = PLATE
    for i in range(-4, 5):
        grille -= Pos(i * 10, 0, 0) * Box(7, 50, 3)
    assert sev(check(grille, process="sheet")[1], "mostly_holes") == "warning"
    csk = PLATE - Cylinder(2, 3) - Pos(0, 0, 0.5) * Cone(2, 4, 2)
    assert sev(check(csk, process="sheet")[1], "secondary_op_countersink") == "warning"
    r, found, row = check(PLATE, process="sheet", screws=[("M3", 6, (0, 0, 1.5 + 2), (0, 0, -1))])   # an M3 threaded into the sheet
    assert sev(found, "secondary_op_tapping") == "warning" and row["tapped_holes"] == 1


def test_a_shop_profile_brings_its_own_stock_and_sizes():
    scs = {"shop": "sendcutsend"}
    assert sev(check(PLATE, process="sheet", man=scs)[1], "non_stock_thickness") == "error"           # 3.00 mm: they stock 3.18
    assert not check(Box(100, 60, 3.18), process="sheet", man=scs)[1]
    assert sev(check(Box(8, 5, 3.18), process="sheet", man=scs)[1], "too_small_to_cut") == "error"
    assert sev(check(Box(1500, 100, 3.18), process="sheet", man=scs)[1], "too_big_to_cut") is None    # 1727 x 1118 at this gauge
    assert sev(check(Box(1800, 100, 3.18), process="sheet", man=scs)[1], "too_big_to_cut") == "error"
    assert "bad_manufacturing_declaration" in check(PLATE, process="sheet", man={"shop": "acme"})[1]


def bracket(t=2.0, r=2.0, leg_b=30.0, hole_x=None):
    """An L bracket as sheet is really bent: inside radius r, outside radius r + t."""
    s = Box(60, 40, t, align=(Align.MIN, Align.CENTER, Align.MIN)) + Box(t, 40, leg_b, align=(Align.MIN, Align.CENTER, Align.MIN))
    along = s.edges().filter_by(Axis.Y)
    inside = [e for e in along if abs(e.center().X - t) < 1e-6 and abs(e.center().Z - t) < 1e-6]
    outside = [e for e in along if abs(e.center().X) < 1e-6 and abs(e.center().Z) < 1e-6]
    s = s.fillet(r, inside).fillet(r + t, outside)
    if hole_x is not None:
        s -= Pos(hole_x, 0, t / 2) * Cylinder(2.5, t)
    return s


def test_bent_sheet_bends_flanges_and_holes_near_bends():
    r, found, row = check(bracket(), material="al5052", process="sheet")
    assert not found and row["form"] == "bent" and row["bends"] == 1 and row["bend_radii_mm"] == [2.0] and row["thickness_mm"] == 2.0
    assert sev(check(bracket(), process="sheet")[1], "alloy_cracks_when_bent") == "warning"            # 6061
    assert sev(check(bracket(leg_b=5.0), material="al5052", process="sheet")[1], "flange_too_short") == "error"
    assert sev(check(bracket(r=0.5), material="al5052", process="sheet")[1], "bend_radius_too_tight") == "warning"
    near = check(bracket(hole_x=8.0), material="al5052", process="sheet")[1]                           # hole edge 1.5 mm from the bend
    assert near["hole_too_close_to_bend"].data["value"] == pytest.approx(1.5, abs=0.05)
    assert not check(bracket(hole_x=30.0), material="al5052", process="sheet")[1]
    sharp = Box(60, 40, 2, align=(Align.MIN, Align.CENTER, Align.MIN)) + Box(2, 40, 30, align=(Align.MIN, Align.CENTER, Align.MIN))
    assert sev(check(sharp, material="al5052", process="sheet")[1], "sharp_bend") == "error"
    scs = {"shop": "sendcutsend"}
    assert not check(bracket(t=2.03, r=1.14), material="al5052", process="sheet", man=scs)[1]          # their tooling radius
    assert "bend_radius_differs" in check(bracket(t=2.03, r=3.0), material="al5052", process="sheet", man=scs)[1]
    assert sev(check(bracket(t=2.03, r=1.14), process="sheet", man=scs)[1], "material_not_bent") == "error"   # 6061 is not bent there


def test_flat_profiles_are_written_as_dxf(tmp_path):
    import ezdxf

    d = Design("dx")
    d.add("tray", Box(100, 60, 3) - Pos(20, 0, 0) * Cylinder(3, 3) - Pos(-20, 0, 0) * Cylinder(2, 3), process="sheet")
    d.add("plain_plate", Pos(0, 0, 50) * Box(50, 40, 4), material="al6061")        # machined, but a plain profile: also cut-able
    d.add("pocketed", Pos(0, 0, 90) * (Box(50, 40, 6) - Pos(0, 0, 2) * Box(10, 10, 2)), material="al6061")
    d.add("printed", Pos(0, 0, 130) * Box(20, 20, 20), material="pla")
    done = export_flat_patterns(d, tmp_path)
    assert set(done) == {"tray", "plain_plate"}
    doc = ezdxf.readfile(done["tray"])
    kinds = sorted(e.dxftype() for e in doc.modelspace())
    assert kinds == ["CIRCLE", "CIRCLE", "LINE", "LINE", "LINE", "LINE"] and doc.header["$INSUNITS"] == 4      # millimetres
    assert sorted(round(e.dxf.radius, 3) for e in doc.modelspace() if e.dxftype() == "CIRCLE") == [2.0, 3.0]


# -------------------------------------------------------------------------------------- FDM printing
def test_print_orientation_is_chosen_reported_and_can_be_pinned():
    tee = Pos(0, 0, 5) * Box(20, 20, 10) + Pos(0, 0, 13) * Box(80, 20, 6)
    r, found, row = check(tee, material="petg")
    assert row["up"] in ("-Z", "+Y", "-Y") and not row["orientation_pinned"] and set(row["orientations"]) == set("+X -X +Y -Y +Z -Z".split())
    assert "needs_support" not in found
    r, found, row = check(tee, material="petg", meta={"print_up": "+Z"})             # arms in mid-air
    assert row["up"] == "+Z" and row["orientation_pinned"] and sev(found, "needs_support") == "warning"
    assert found["needs_support"].data["value"] > 1000 and found["needs_support"].data["at"]
    assert "bad_manufacturing_declaration" in check(tee, material="petg", meta={"print_up": "sideways"})[1]


def table(span):
    return Pos(0, 0, 21) * Box(span + 10, 20, 2) + Pos(-(span + 5) / 2, 0, 10) * Box(5, 20, 20) + Pos((span + 5) / 2, 0, 10) * Box(5, 20, 20)


def test_print_bridges_short_ones_print_long_ones_need_support():
    r, found, row = check(table(20), material="pla", meta={"print_up": "+Z"})
    assert "long_bridge" not in found and "needs_support" not in found and row["bridges"]["max_span_mm"] == pytest.approx(20, abs=0.5)
    r, found, row = check(table(60), material="pla", meta={"print_up": "+Z"})
    assert found["long_bridge"].data["value"] == pytest.approx(60, abs=0.5) and "needs_support" in found
    assert "long_bridge" not in check(table(60), material="pla", meta={"print_up": "+Z"}, man={"limits": {"fdm.bridge_max_mm": 80}})[1]


def test_print_horizontal_holes_droop_when_large():
    from build123d import Rot
    blk = Pos(0, 0, 15) * Box(40, 20, 30)
    assert sev(check(blk - Pos(0, 0, 15) * Rot(90, 0, 0) * Cylinder(8, 20), material="pla", meta={"print_up": "+Z"})[1],
               "horizontal_hole_droop") == "warning"
    small = check(blk - Pos(0, 0, 15) * Rot(90, 0, 0) * Cylinder(3, 20), material="pla", meta={"print_up": "+Z"})[1]
    assert "horizontal_hole_droop" not in small and "needs_support" not in small


def test_print_thin_walls_small_holes_and_pins():
    base = Pos(0, 0, 2) * Box(40, 40, 4)
    assert sev(check(base + Pos(0, 0, 14) * Box(30, 0.5, 20), material="pla")[1], "wall_too_thin_to_print") == "error"
    assert "wall_too_thin_to_print" not in check(base + Pos(0, 0, 14) * Box(30, 1.6, 20), material="pla")[1]
    # a finer nozzle prints a thinner wall
    assert "wall_too_thin_to_print" not in check(base + Pos(0, 0, 14) * Box(30, 0.5, 20), material="pla",
                                                 man={"printer": {"nozzle": 0.25}, "limits": {"fdm.wall_min_mm": 0.5}})[1]
    assert sev(check(base - Pos(10, 10, 2) * Cylinder(0.6, 4), material="pla")[1], "hole_too_small_to_print") == "warning"
    assert "hole_too_small_to_print" not in check(base - Pos(10, 10, 2) * Cylinder(1.7, 4), material="pla")[1]
    assert sev(check(base + Pos(0, 0, 8) * Cylinder(0.7, 8), material="pla")[1], "feature_too_small_to_print") == "warning"
    assert "feature_too_small_to_print" not in check(base + Pos(0, 0, 8) * Cylinder(3, 8), material="pla")[1]


def test_print_stays_on_the_bed_and_fits_the_printer():
    assert sev(check(Pos(0, 0, 60) * Box(6, 6, 120), material="pla", meta={"print_up": "+Z"})[1], "tall_thin_print") == "warning"
    assert "tall_thin_print" not in check(Pos(0, 0, 10) * Box(30, 30, 20), material="pla")[1]
    assert sev(check(Box(300, 30, 10), material="pla")[1], "too_big_to_print") == "error"
    assert "too_big_to_print" not in check(Box(300, 30, 10), material="pla", man={"printer": {"build_volume": (350, 350, 350)}})[1]
    mushroom = Pos(0, 0, 15) * Box(100, 100, 10) + Pos(0, 0, 5) * Box(20, 20, 10)        # stands on 4% of its outline
    assert sev(check(mushroom, material="pla", meta={"print_up": "+Z"})[1], "small_bed_contact") == "warning"
    assert "small_bed_contact" not in check(mushroom, material="pla", meta={"print_up": "-Z"})[1]


def test_print_threads_need_plastic_around_them():
    boss = Pos(0, 0, 5) * Cylinder(3.0, 10)                                            # 6 mm boss for an M3: 1.5 mm of wall
    r, found, row = check(boss, material="petg", screws=[("M3", 8, (0, 0, 12), (0, 0, -1))])
    assert sev(found, "thin_wall_around_thread") == "warning" and found["thin_wall_around_thread"].data["value"] == pytest.approx(1.5, abs=0.05)
    assert sev(found, "printed_threads") == "info" and "heat-set" in found["printed_threads"].data["hint"]
    fat = check(Pos(0, 0, 5) * Cylinder(6.0, 10), material="petg", screws=[("M3", 8, (0, 0, 12), (0, 0, -1))])[1]
    assert "thin_wall_around_thread" not in fat


def test_print_load_across_the_layers_is_flagged_and_avoided():
    post = Pos(0, 0, 20) * Box(20, 20, 40)
    r, found, row = check(post, material="petg", loads=[("pull", (0, 0, 100.0))], meta={"print_up": "+Z"})
    assert sev(found, "load_across_layers") == "warning"
    r, found, row = check(post, material="petg", loads=[("pull", (0, 0, 100.0))])      # left free, it lays the part down
    assert "load_across_layers" not in found and row["up"][1] != "Z"
    assert "load_across_layers" not in check(post, material="petg", loads=[("side", (100.0, 0, 0))], meta={"print_up": "+Z"})[1]


# -------------------------------------------------------------------------------------- CNC milling
BLOCK = Box(60, 40, 30)


def pocket(w, l, depth, r=0.0):
    from build123d import RectangleRounded, Rectangle, extrude
    sk = RectangleRounded(l, w, r) if r else Rectangle(l, w)
    return Pos(0, 0, 15 - depth) * extrude(sk, depth)


def test_cnc_inside_corners_sharp_small_and_deep():
    r, found, row = check(BLOCK - pocket(20, 30, 10))
    assert sev(found, "sharp_inside_corner") == "error" and row["sharp_inside_corners"] == 4
    assert found["sharp_inside_corner"].data["at"][0][2] == pytest.approx(10.0)          # mid-height of the pocket wall
    assert not check(BLOCK - pocket(20, 30, 10, r=4.0))[1]
    assert sev(check(BLOCK - pocket(20, 30, 3, r=0.5))[1], "small_inside_radius") == "warning"
    deep = check(BLOCK - pocket(20, 30, 20, r=1.5))[1]                                    # 20 deep on a 3 mm cutter: 6.7:1
    assert deep["deep_inside_corner"].data["value"] == pytest.approx(20 / 3, abs=0.05)
    step = Box(60, 40, 30) - Pos(15, 0, 10) * Box(30, 40, 10)                             # an open step: a square end mill makes it
    assert "sharp_inside_corner" not in check(step)[1]


def test_cnc_plate_corner_that_needs_a_side_setup():
    ell = Box(80, 60, 6) - Pos(20, 15, 0) * Box(40, 30, 6)                                # L-shaped plate, sharp inside corner
    r, found, row = check(ell)
    assert sev(found, "sharp_corner_side_milled") == "warning" and "sharp_inside_corner" not in found
    assert row["form"] == "plate" and row["setups_estimate"] == 2


def test_cnc_slots_deep_and_narrow():
    r, found, row = check(BLOCK - Pos(0, 0, 5) * Box(60, 3, 20))                          # 3 wide, 20 deep, open both ends
    assert sev(found, "deep_narrow_slot") == "warning" and found["deep_narrow_slot"].data["value"] > 5
    assert "deep_narrow_slot" not in check(BLOCK - Pos(0, 0, 11) * Box(60, 3, 8))[1]
    assert sev(check(BLOCK - Pos(0, 0, 13) * Box(60, 1.5, 4))[1], "narrow_slot") == "warning"
    assert sev(check(Box(60, 80, 80) - Pos(0, 0, 3) * Box(50, 2, 74))[1], "slot_too_deep") == "error"   # closed ends, 37:1


def test_cnc_thin_walls_and_floors():
    assert sev(check(BLOCK - Pos(0, 19.35 - 5, 5) * Box(40, 10, 20))[1], "thin_wall") == "warning"       # 0.65 mm wall left
    assert sev(check(BLOCK - Pos(0, 19.7 - 5, 5) * Box(40, 10, 20))[1], "thin_wall") == "error"          # 0.3 mm
    assert "thin_wall" not in check(BLOCK - Pos(0, 12, 5) * Box(40, 10, 20))[1]
    assert sev(check(BLOCK - Pos(0, 0, 0.2) * Box(30, 20, 29.6), material="abs", process="machined")[1], "thin_wall") == "error"  # plastic floor 0.4... wall rule 1.0


def test_cnc_holes_depth_and_drill_sizes():
    tall = Box(20, 20, 60)
    assert sev(check(tall - Cylinder(1.5, 60))[1], "deep_hole") == "warning"              # 3 mm x 60: 20:1
    assert sev(check(tall - Cylinder(0.6, 60))[1], "hole_too_deep") == "error"            # 1.2 mm x 60: 50:1
    assert "deep_hole" not in check(tall - Cylinder(4, 60))[1]
    r, found, row = check(BLOCK - Cylinder(1.665, 30))                                    # 3.33 mm
    assert sev(found, "non_standard_drill") == "warning" and "3.3" in found["non_standard_drill"].message
    assert not check(BLOCK - Cylinder(1.7, 30))[1]                                        # 3.4 mm: M3 clearance, a standard drill
    assert sev(check(BLOCK - Cylinder(0.4, 30))[1], "tiny_hole") == "warning"
    # two ears bored in line are two short holes, not one long one
    ears = Box(80, 20, 6) + Pos(-37, 0, 13) * Box(6, 20, 20) + Pos(37, 0, 13) * Box(6, 20, 20)
    from build123d import Rot
    r, found, row = check(ears - Pos(0, 0, 15) * Rot(0, 90, 0) * Cylinder(2, 80))
    assert row["holes"] == 2 and "deep_hole" not in found


def test_cnc_threads_read_from_the_screws():
    r, found, row = check(BLOCK, screws=[("M3", 16, (0, 0, 15 + 3), (0, 0, -1))])          # 13 mm of M3 thread: over 3 x d
    assert row["tapped_holes"] == 1 and sev(found, "thread_deeper_than_needed") == "warning"
    plate = Pos(0, 0, 0) * Box(60, 40, 8)
    r, found, row = check(plate, screws=[("M3", 8, (0, 0, 4 + 2), (0, 0, -1))])            # tip 2 mm short of the far face
    assert found["blind_tap_runout"].data["at"][0] == [0.0, 0.0, 4.0]
    assert not check(plate, screws=[("M3", 12, (0, 0, 4 + 2), (0, 0, -1))])[1]             # goes right through: a through tap
    # the tapped hole needs a set-up from its own side even though no hole is modelled
    r, found, row = check(Box(40, 40, 40), screws=[("M4", 8, (20 + 2, 0, 0), (-1, 0, 0))])
    assert row["cut_from"] == ["+X"]


def test_cnc_undercut_is_unreachable_and_setups_are_counted():
    tslot = BLOCK - Pos(0, 0, 10) * Box(40, 6, 10) - Pos(0, 0, 2) * Box(40, 20, 6)         # blind T-slot: a chamber under a neck
    r, found, row = check(tslot)
    assert sev(found, "feature_unreachable") == "error" and row["unreachable_fraction"] > 0.02
    r, found, row = check(BLOCK - Pos(0, 0, 10) * Box(60, 6, 10))
    assert "feature_unreachable" not in found and row["unreachable_fraction"] == 0 and row["cut_from"] == ["+Z"]


def test_cnc_stock_material_removed_and_estimate():
    r, found, row = check(Box(70, 50, 40) - Pos(0, 0, 10) * Box(30, 20, 20))
    assert sev(found, "mostly_chips") is None and row["form"] == "block" and row["stock"] == "block 72 x 52 x 42 mm"
    angle = Box(100, 100, 100) - Pos(3, 3, 0) * Box(100, 100, 100)                          # a 3 mm angle bracket hogged from a cube
    r, found, row = check(angle)
    assert sev(found, "mostly_chips") == "warning" and row["material_removed_fraction"] > 0.9
    est = row["estimate"]
    assert est["basis"].startswith("estimate") and est["cost_usd_each_qty1"] > est["cost_usd_each_qty10"] > 0
    assert any("stock removed" in x for x in row["cost_drivers"])


def test_cnc_turned_part_and_part_at_an_angle():
    from build123d import Rot
    shaft = Cylinder(10, 40) + Pos(0, 0, 25) * Cylinder(5, 10) - Cylinder(3, 60)
    r, found, row = check(shaft, material="steel")
    assert row["form"] == "turned" and row["stock"].startswith("round bar 20 mm") and not found
    # the same pocketed block, turned 30 degrees in the assembly, is judged in its own frame
    tilted = Rot(0, 0, 30) * (BLOCK - pocket(20, 30, 10, r=4.0))
    r, found, row = check(tilted)
    assert not found and row["setups_estimate"] == 1 and "frame" in row
