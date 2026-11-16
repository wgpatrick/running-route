"""Known-answer tests for the practice verifier (mechloop/verifiers/practice.py; docs/PRACTICE_RULES.md sections 5 and 8;
docs/DESIGN_GUIDELINES.md). Small purpose-built designs; answers by construction; each rule tested both ways: the bad case
raises the finding, the good case does not."""
import math

import pytest
from build123d import Box, Cylinder, Location, Pos

from mechloop import Adjustment, Design, Joint
from mechloop.model import Belt
from mechloop.parts import (add_nut, add_screw, bearing, extrusion_2020, gt2_idler, gt2_pulley, leadscrew_t8, mgn12h_carriage,
                            nema17, place)
from mechloop.verifiers.practice import RULES, verify_practice


def run(d):
    return verify_practice(d)


def found(r, code, severity=None):
    return [f for f in r.findings if f.code == code and (severity is None or f.severity == severity)]


def plate_pair(hole=5.5, nscrews=1, material="steel"):
    """Two 3 mm plates, one on the other, M5 clearance holes in the top one at x = 0 (and x = 20), tapped into the bottom."""
    d = Design("pp")
    top = Pos(0, 0, 1.5) * Box(60, 40, 3)
    for i in range(nscrews):
        top -= Pos(20 * i, 0, 1.5) * Cylinder(hole / 2, 3)
    d.add("top", top, material=material, process="sheet")
    d.add("bottom", Pos(0, 0, -5) * Box(60, 40, 10), material="steel", process="machined")
    for i in range(nscrews):
        add_screw(d, f"s{i}", "M5", 10, at=(20 * i, 0, 3), threads_into="bottom", clamps=("top",))
    return d


# ---------------------------------------------------------------------------------------------------- registry policy
def test_no_recalled_or_derived_rule_is_an_error():
    bad = [r.id for r in RULES.values() if r.evidence in ("recalled", "derived") and r.severity == "error"]
    assert bad == [] or all(RULES[b].status != "implemented" for b in bad)
    assert all(r.status in ("implemented", "xref", "deferred") for r in RULES.values())
    assert all(r.checked_by for r in RULES.values() if r.status == "xref")
    assert all(r.note for r in RULES.values() if r.status == "deferred")


def test_registered_in_the_runner_and_runs_alone():
    from mechloop.runner import ORDER, verify

    assert "practice" in ORDER and ORDER.index("practice") == ORDER.index("manufacture") + 1
    rep = verify(plate_pair(nscrews=2), only=["practice"])
    assert [r.verifier for r in rep.results] == ["practice"]
    m = rep.results[0].metrics
    assert m["rules"]["FST-031"]["status"] == "xref" and "ratings" in m["rules"]["FST-031"]["checked_by"]
    assert m["counts"]["implemented"] >= 20


def test_recalled_rule_cannot_be_raised_to_error_and_disable_works():
    d = Design("adj")
    d.add("a", Box(10, 10, 10))
    d.adjustments.append(Adjustment("slot", "belt_tension", 2.0))
    d.practice = {"severity": {"LOC-006": "error"}}
    f = found(run(d), "adjustment_without_lock")
    assert f and f[0].severity == "warning"                       # recalled evidence: clamped to a warning
    d.practice = {"disable": ["LOC-006"]}
    assert not found(run(d), "adjustment_without_lock")
    d.practice = {"disable": ["NOPE-1"]}
    assert found(run(d), "unknown_practice_rule")


# ---------------------------------------------------------------------------------------------------- FST-060
def shank_case(length, nut_under_head):
    d = Design("shank")
    d.add("plate", Pos(0, 0, 1.5) * (Box(30, 30, 3) - Cylinder(2.75, 3)), material="steel", process="sheet")
    add_screw(d, "s", "M5", length, at=(0, 0, 3), clamps=("plate",))
    add_nut(d, "n", "M5", at=(0, 0, 3 - nut_under_head), direction=(0, 0, -1), screw="s")
    return d


def test_fst060_nut_on_the_plain_shank():
    # M5 x 60: b = 22 mm, thread from 38 mm under the head. A nut 10 mm under the head is on the plain shank.
    f = found(run(shank_case(60, 10)), "nut_on_plain_shank", "error")
    assert f and f[0].data["limit"] == pytest.approx(38.0) and f[0].data["rule"] == "FST-060"
    assert not found(run(shank_case(60, 45)), "nut_on_plain_shank")    # past the thread start
    assert not found(run(shank_case(20, 10)), "nut_on_plain_shank")    # M5 x 20 is fully threaded
    d = shank_case(60, 10)
    d.get("s").meta["fully_threaded"] = True
    assert not found(run(d), "nut_on_plain_shank")


# ---------------------------------------------------------------------------------------------------- FST-070
def locking_case(nut_locking=None, screw_locking=None, plate_material="al6061"):
    d = Design("lock")
    d.add("rail", Box(200, 20, 4), material="steel")
    d.add("plate", Pos(0, 0, 4.5) * (Box(30, 30, 5) - Cylinder(1.7, 5)), material=plate_material, body="car",
          process="printed" if plate_material == "petg" else "machined")
    add_screw(d, "s", "M3", 12, at=(0, 0, 7), body="car", clamps=("plate",), locking=screw_locking)
    add_nut(d, "n", "M3", at=(0, 0, 2), direction=(0, 0, -1), body="car", screw="s", locking=nut_locking)
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50), max_effort=10))
    return d


def test_fst070_locking_on_a_moving_body():
    f = found(run(locking_case()), "no_locking_feature", "warning")
    assert f and f[0].data["parts"] == ["s"] and f[0].data["value"] == 1
    assert not found(run(locking_case(nut_locking="nyloc")), "no_locking_feature")
    assert not found(run(locking_case(screw_locking="adhesive")), "no_locking_feature")
    assert not found(run(locking_case(screw_locking="serrated")), "no_locking_feature")         # metal seat: accepted
    f = found(run(locking_case(screw_locking="serrated", plate_material="petg")), "no_locking_feature")
    assert f and "preload" in f[0].data["screws"][0]["why"]                                     # printed seat: not accepted
    d = locking_case()
    d.joints.clear()
    d.get("s").body = d.get("n").body = d.get("plate").body = "world"
    assert not found(run(d), "no_locking_feature")                                              # still frame, no motor


# ---------------------------------------------------------------------------------------------------- belts
R20 = 20 * 2.0 / math.pi / 2
ZB = 10.5          # gt2_pulley belt centre height


def open_belt(wrap_deg, width=6.0):
    """A belt from an anchor at the left, over the top of a 20-tooth pulley (not a joint's drive pulley) and away at
    `wrap_deg` of wrap, clockwise."""
    d = Design("belt")
    place(d, "p", gt2_pulley(20, belt_width=width), Location((0, 0, 0)))
    leave = math.radians(90 - wrap_deg)
    p_leave = (R20 * math.cos(leave), R20 * math.sin(leave))
    t = (math.sin(leave), -math.cos(leave))
    b = (p_leave[0] + 100 * t[0], p_leave[1] + 100 * t[1], ZB)
    d.belts.append(Belt("belt", [("anchor", "world", (-100, R20, ZB)), ("pulley", "p", "cw"), ("anchor", "world", b)],
                        width=width))
    return d


def test_blt010_blt011_teeth_and_wrap_on_every_loaded_pulley():
    r = run(open_belt(180))
    assert not found(r, "pulley_few_teeth") and not found(r, "pulley_low_wrap")
    f = found(run(open_belt(90)), "pulley_few_teeth", "warning")          # 90 / 360 x 20 = 5 teeth
    assert f and f[0].data["value"] == pytest.approx(5.0, abs=0.05) and f[0].data["limit"] == 6
    r = run(open_belt(30))                                                # 1.7 teeth: not rated -> error; and under 60 deg
    assert found(r, "pulley_few_teeth", "error") and found(r, "pulley_low_wrap", "warning")
    d = open_belt(90)                                                     # a joint's drive pulley is motion's business
    d.add("car", Pos(0, 50, 0) * Box(5, 5, 5), body="c")
    d.joints.append(Joint("x", "slide", "world", "c", (1, 0, 0), range=(0, 1), drive={"kind": "belt", "pulley": "p", "motor": "m"}))
    assert not found(run(d), "pulley_few_teeth")


def test_blt040_pulley_narrower_than_the_belt():
    f = found(run(open_belt(180, width=12.0)), "pulley_narrower_than_belt")     # 20 T OD 11.97 < 12
    assert f and f[0].data["value"] == pytest.approx(11.97, abs=0.01) and f[0].data["limit"] == 12.0
    assert not found(run(open_belt(180, width=6.0)), "pulley_narrower_than_belt")


def closed_loop(idler):
    d = Design("loop")
    place(d, "p", gt2_pulley(20), Location((0, 0, 0)))
    place(d, "q", gt2_pulley(20), Location((100, 0, 0)))
    path = [("pulley", "p", "ccw"), ("pulley", "q", "ccw")]
    if idler == "back":     # outside the loop on the top run, pressing it 2 mm in: the belt's back wraps it
        place(d, "i", gt2_idler(20), Location((50, R20 + (20 * 2 / math.pi - 0.76) / 2 + 0.38 - 2.0, ZB - 4.25)))
        path.append(("pulley", "i", "cw"))
    d.belts.append(Belt("loop", path))
    return d


def test_blt030_blt031_toothed_back_side_idler():
    r = run(closed_loop("back"))
    assert found(r, "toothed_backside_idler") and found(r, "idler_too_small")
    assert found(r, "idler_too_small")[0].data["limit"] == 12.7
    r = run(closed_loop(None))
    assert not found(r, "toothed_backside_idler") and not found(r, "idler_too_small")


# ---------------------------------------------------------------------------------------------------- bearings, shafts
def bearing_case(retained=True, collar_join="clamp collar", shaft="rod", journal=False):
    """A 608 in a 7 mm housing (bore = its OD). retained: a lip under and a cover over the outer ring, a collar under and
    over the inner ring on the shaft."""
    d = Design("brg")
    d.add("housing", Box(50, 50, 7) - Cylinder(11, 7), material="al6061")
    place(d, "b", bearing("608"), Location((0, 0, 0)))
    if shaft == "rod":
        d.add("shaft", Pos(0, 0, 0) * Cylinder(4, 60), material="steel")
    else:
        place(d, "shaft", leadscrew_t8(60, 2), Location((0, 0, -30)))
        if journal:
            d.get("shaft").meta["journal"] = True
    if retained:
        d.add("lip", Pos(0, 0, -4.5) * (Box(50, 50, 2) - Cylinder(9.5, 2)), material="al6061")
        d.add("cover", Pos(0, 0, 4.5) * (Box(50, 50, 2) - Cylinder(9.5, 2)), material="al6061")
        d.add("collar_lo", Pos(0, 0, -5.0) * (Cylinder(9, 3) - Cylinder(4, 3)), material="steel")
        d.add("collar_hi", Pos(0, 0, 5.0) * (Cylinder(9, 3) - Cylinder(4, 3)), material="steel")
        d.join("collar_lo", "shaft", "clamp collar")
        d.join("collar_hi", "shaft", collar_join)
    return d


def test_brg020_axial_retention_both_rings_both_faces():
    f = found(run(bearing_case(retained=False)), "bearing_not_retained")
    assert f and f[0].data["value"] == 4                       # all four faces free
    assert not found(run(bearing_case(retained=True)), "bearing_not_retained")


def test_brg023_axial_path_through_a_set_screw():
    f = found(run(bearing_case(collar_join="set_screw")), "axial_load_through_set_screw")
    assert f and "collar_hi" in f[0].data["parts"]
    assert not found(run(bearing_case()), "axial_load_through_set_screw")


def test_shf011_bearing_on_a_thread():
    f = found(run(bearing_case(shaft="t8")), "seat_on_thread")
    assert f and "shaft" in f[0].data["parts"]
    assert not found(run(bearing_case(shaft="t8", journal=True)), "seat_on_thread")
    assert not found(run(bearing_case(shaft="rod")), "seat_on_thread")


def set_screw_case(kind, on="motor", journal=False):
    d = Design("ss")
    if on == "motor":
        place(d, "shaft", nema17(40), Location((0, 0, 0)))
    else:
        place(d, "shaft", leadscrew_t8(100, 2), Location((0, 0, 0)))
        d.get("shaft").meta["journal"] = journal
    place(d, "pulley", gt2_pulley(20), Location((0, 0, 10)))
    d.join("pulley", "shaft", kind)
    return d


def test_shf010_set_screw_on_a_flat_and_locked():
    f = found(run(set_screw_case("set_screw")), "set_screw_without_flat")
    assert f and "a flat" in f[0].data["value"] and "adhesive" in f[0].data["value"]
    assert not found(run(set_screw_case("set_screw on flat, threadlocked")), "set_screw_without_flat")
    assert found(run(set_screw_case("set_screw on flat")), "set_screw_without_flat")           # not locked
    assert found(run(set_screw_case("set_screw", on="t8")), "seat_on_thread")                    # SHF-011 on a thread
    assert not found(run(set_screw_case("set_screw on flat, threadlocked", on="t8", journal=True)), "seat_on_thread")


# ---------------------------------------------------------------------------------------------------- joints
def test_fst051_single_screw_joint():
    f = found(run(plate_pair(nscrews=1)), "single_screw_joint")
    assert f and f[0].data["joints"][0]["parts"] == ["bottom", "top"]
    assert not found(run(plate_pair(nscrews=2)), "single_screw_joint")
    d = plate_pair(nscrews=1)
    d.join("top", "bottom", "rib in a slot")
    assert not found(run(d), "single_screw_joint")


def tnut_case(n):
    d = Design("tn")
    place(d, "ext", extrusion_2020(200), Location((0, 0, 0)))
    pl = Pos(0, 0, 11.5) * Box(50, 20, 3)
    for i in range(n):
        pl -= Pos(-10 + 20 * i, 0, 11.5) * Cylinder(2.75, 3)
    d.add("stop", pl, material="steel", process="sheet")
    for i in range(n):
        add_screw(d, f"s{i}", "M5", 8, at=(-10 + 20 * i, 0, 13), threads_into="ext", tnut=True, clamps=("stop",))
    return d


def test_fst101_part_on_a_single_tnut():
    f = found(run(tnut_case(1)), "single_tnut")
    assert f and f[0].data["parts"] == ["stop"]
    assert not found(run(tnut_case(2)), "single_tnut")
    assert not found(run(tnut_case(1)), "single_screw_joint")                  # T-nut joints are FST-101's, not FST-051's


def test_a_part_beside_the_shank_is_not_held_by_the_screw():
    """Found on ref_vminion: a probe barrel standing beside an endstop screw (inside the head's radius, outside the
    shank, no hole) was counted as held by it and reported as a single-screw joint."""
    d = plate_pair(nscrews=2)
    d.add("neighbour", Pos(0, 3.4 + 5, -5) * Box(10, 10, 10), material="steel")     # 3.4 mm from the axis of s0 (M5 shank 2.5, head 4.25)
    d.get("bottom").shape = d.get("bottom").shape - Pos(0, 3.4 + 5, -5) * Box(10, 10, 10)
    r = run(d)
    assert not any("neighbour" in f.data["parts"] for f in found(r, "single_screw_joint"))


def test_fst051_round_standoff_on_its_screw_is_not_a_single_screw_joint():
    """Found on z_axis_v2 and pan_tilt: a round standoff or retainer on one screw was reported; turning it about the screw
    changes nothing. A square spacer block on the same screw is still reported."""
    def case(round_):
        d = plate_pair(nscrews=2)
        so = (Cylinder(4.0, 6) - Cylinder(1.7, 6)) if round_ else (Box(8, 8, 6) - Cylinder(1.7, 6))
        d.add("so", Pos(0, 30, -3) * so, material="steel")
        d.add("arm", Pos(0, 30, -8) * Box(20, 20, 4), material="steel")
        add_screw(d, "so_screw", "M3", 10, at=(0, 30, 0), threads_into="arm", clamps=("so",))
        return d
    pairs = lambda r: [j["parts"] for f in found(r, "single_screw_joint") for j in f.data["joints"]]
    assert ["arm", "so"] not in pairs(run(case(True)))
    assert ["arm", "so"] in pairs(run(case(False)))


def test_fst101_one_tnut_in_each_of_two_extrusions_is_two():
    """Found on z_axis_v2: a motor mount on one T-nut in each of two extrusions was reported twice."""
    d = Design("tn2")
    place(d, "ext_a", extrusion_2020(200), Location((0, 0, 0)))
    place(d, "ext_b", extrusion_2020(200), Location((0, 40, 0)))
    pl = Pos(0, 20, 11.5) * Box(30, 70, 3) - Pos(0, 0, 11.5) * Cylinder(2.75, 3) - Pos(0, 40, 11.5) * Cylinder(2.75, 3)
    d.add("mount", pl, material="steel", process="sheet")
    add_screw(d, "a", "M5", 8, at=(0, 0, 13), threads_into="ext_a", tnut=True, clamps=("mount",))
    add_screw(d, "b", "M5", 8, at=(0, 40, 13), threads_into="ext_b", tnut=True, clamps=("mount",))
    assert not found(run(d), "single_tnut")


def test_fst051_a_tnut_screw_counts_as_the_second_constraint():
    """Found on ref_vminion: a printed block with one screw into the extrusion's end tap and one T-nut screw into its slot
    was reported as a single-screw joint, because the T-nut screw was left out of the count."""
    d = Design("end")
    place(d, "ext", extrusion_2020(100), Location((0, 0, 0)))                  # along X, its end face at x = 50
    blk = Pos(60, 0, 0) * Box(20, 20, 20) + Pos(40, 0, 15) * Box(20, 20, 10)
    blk -= Pos(60, 0, 0) * Box(20, 5.5, 5.5)
    blk -= Pos(40, 0, 15) * Cylinder(2.75, 10)
    d.add("block", blk, material="steel", process="machined")
    add_screw(d, "end_bolt", "M5", 25, at=(70, 0, 0), direction=(-1, 0, 0), threads_into="ext", clamps=("block",))
    add_screw(d, "slot_bolt", "M5", 8, at=(40, 0, 20), threads_into="ext", tnut=True, clamps=("block",))
    r = run(d)
    assert not found(r, "single_screw_joint") and not found(r, "single_tnut")
    d.fasteners = [f for f in d.fasteners if f.name != "slot_bolt"]
    assert found(run(d), "single_screw_joint")


# ---------------------------------------------------------------------------------------------------- holes
def edge_case(edge_mm, hole=5.5):
    d = Design("edge")
    d.add("tab", Pos(0, 0, 1.5) * (Box(40, 30, 3) - Pos(20 - edge_mm, 0, 0) * Cylinder(hole / 2, 3)), material="steel", process="sheet")
    d.add("base", Pos(0, 0, -5) * Box(60, 40, 10), material="steel", process="machined")
    add_screw(d, "s", "M5", 10, at=(20 - edge_mm, 0, 3), threads_into="base", clamps=("tab",))
    add_screw(d, "s2", "M5", 10, at=(0, 0, 3), threads_into="base", clamps=("tab",))
    d.get("tab").shape = d.get("tab").shape - Pos(0, 0, 1.5) * Cylinder(2.75, 3)
    return d


def test_fst050_edge_distance():
    f = found(run(edge_case(6.0)), "hole_near_edge")                        # 6 mm = 1.2 d < 1.5 d = 7.5 mm
    assert f and f[0].data["value"] == pytest.approx(1.2, abs=0.06) and f[0].data["limit"] == 1.5
    assert not found(run(edge_case(8.0)), "hole_near_edge")
    d = edge_case(6.0)
    d.practice = {"limits": {"FST-050.min_edge_d": 1.1}}
    assert not found(run(d), "hole_near_edge")


def test_fst020_hole_class():
    f = found(run(plate_pair(hole=5.1, nscrews=2)), "hole_under_fine")      # under 5.3 (fine) for M5
    assert f and f[0].data["value"] == pytest.approx(5.1, abs=0.05) and f[0].data["limit"] == 5.3
    assert not found(run(plate_pair(hole=5.5, nscrews=2)), "hole_under_fine")
    d = plate_pair(hole=5.1, nscrews=2)
    for i in range(2):
        d.join(f"s{i}", "top", "axle")
    assert not found(run(d), "hole_under_fine")
    assert found(run(plate_pair(hole=7.0, nscrews=2)), "hole_over_coarse", "info")


def counterbore_case(floor):
    d = Design("cb")
    T = floor + 4.0
    blk = Pos(0, 0, T / 2) * Box(40, 40, T) - Pos(0, 0, T / 2) * Cylinder(2.75, T) - Pos(0, 0, T - 2.0) * Cylinder(4.75, 4.0)
    d.add("plate", blk, material="al6061", process="machined")
    d.add("base", Pos(0, 0, -10) * Box(60, 60, 20), material="steel", process="machined")
    add_screw(d, "s", "M5", 12, at=(0, 0, floor), threads_into="base", clamps=("plate",))
    return d


def test_fst034_counterbore_floor():
    f = found(run(counterbore_case(2.0)), "counterbore_floor_thin")
    assert f and f[0].data["value"] == pytest.approx(0.4, abs=0.06) and f[0].data["limit"] == 1.0
    assert not found(run(counterbore_case(6.0)), "counterbore_floor_thin")


def test_fst081_lookalike_lengths_into_blind_catalogue_threads():
    def case(lengths):
        d = Design("mgn")
        place(d, "blk", mgn12h_carriage(), Location((0, 0, 0)))
        holes = d.get("blk").meta["interfaces"]["mount_holes_m3"]
        top = d.get("blk").meta["interfaces"]["top_z"]
        for i, L in enumerate(lengths):
            add_screw(d, f"s{i}", "M3", L, at=(holes[i][0], holes[i][1], top + 3), threads_into="blk")
        return d
    f = found(run(case([6, 6, 8, 8])), "lookalike_screw_lengths")
    assert f and f[0].data["value"] == 2
    assert not found(run(case([6, 6, 6, 6])), "lookalike_screw_lengths")


def test_loc006_adjustment_lock():
    d = Design("adj")
    d.add("a", Box(10, 10, 10))
    d.adjustments += [Adjustment("idler slot", "belt_tension", 2.0), Adjustment("probe offset", "z_offset", 2.0)]
    f = found(run(d), "adjustment_without_lock")
    assert f and f[0].data["parts"] == ["idler slot"]
    d.adjustments[0].lock = "two M3 screws, threadlocked"
    assert not found(run(d), "adjustment_without_lock")


def test_fst040_torque_table():
    r = run(plate_pair(nscrews=2))
    f = found(r, "torque_not_stated", "info")
    assert f and f[0].data["value"] == 2
    row = r.metrics["torque_table"][0]
    assert row["size"] == "M5" and row["torque_nm"] == pytest.approx(6.5) and row["seat"] == "metal only"
    d = plate_pair(nscrews=2)
    d.manufacturing["tightening_torque_nm"] = {"M5": 5.0}
    assert not found(run(d), "torque_not_stated")


# ---------------------------------------------------------------------------------------------------- owner's rules
def printed_motor_mount():
    d = Design("pm")
    place(d, "motor", nema17(40), Location((0, 0, 0)))
    holes = d.get("motor").meta["interfaces"].get("mount_holes_m3") or [(15.5, 15.5, 0)]
    blk = Pos(0, 0, 2.5) * Box(42, 42, 5) - Pos(0, 0, 2.5) * Cylinder(12, 5)
    for h in holes:
        blk -= Pos(h[0], h[1], 2.5) * Cylinder(1.7, 5)
    d.add("mount", blk, material="petg", process="printed")
    for i, h in enumerate(holes):
        add_screw(d, f"m{i}", "M3", 8, at=(h[0], h[1], 5), threads_into="motor", clamps=("mount",))
    d.add("duct", Pos(100, 0, 10) * Box(20, 20, 20), material="petg", process="printed")
    return d


def test_dg01_printed_part_in_a_load_path_is_an_error_unless_waived():
    r = run(printed_motor_mount())
    f = found(r, "printed_load_path", "error")
    assert [x.data["part"] for x in f] == ["mount"] and "a motor" in f[0].data["value"]
    assert r.metrics["printed_parts_in_load_path"] == ["mount"]
    d = printed_motor_mount()
    d.waive("DG-01", "mount", reason="test rig only, the motor runs unloaded on the bench")
    r = run(d)
    assert not found(r, "printed_load_path") and not found(r, "waiver_without_reason") and not found(r, "waiver_unused")
    assert r.metrics["waivers"][0]["suppressed"][0]["parts"] == ["mount"]
    d = printed_motor_mount()
    d.waive("practice.printed_load_path", ["mo*"], reason="short")
    r = run(d)
    assert not found(r, "printed_load_path") and found(r, "waiver_without_reason", "error")
    d = printed_motor_mount()
    d.waive("DG-01", "duct", reason="the duct carries nothing at all, this waiver is stale")
    r = run(d)
    assert found(r, "printed_load_path") and found(r, "waiver_unused", "warning")


def test_dg01_bearing_seat_and_belt_clamp():
    d = Design("pb")
    d.add("block", Box(40, 40, 7) - Cylinder(11, 7), material="abs", process="printed")
    place(d, "b", bearing("608"), Location((0, 0, 0)))
    d.join("b", "block", "press")
    d.add("clamp", Pos(0, 60, 0) * Box(20, 10, 10), material="petg", body="car", process="printed")
    d.add("rail", Pos(0, 60, -10) * Box(300, 10, 10), material="steel")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50), max_effort=10))
    place(d, "p", gt2_pulley(20), Location((100, 60 - R20, -10)))
    d.belts.append(Belt("x", [("anchor", "car", (0, 55.0 - 0.0, 0)), ("pulley", "p", "ccw"), ("anchor", "car", (5, 55.0, 0))]))
    f = {x.data["part"]: x for x in found(run(d), "printed_load_path")}
    assert set(f) == {"block", "clamp"} and "a bearing" in f["block"].data["value"]


def tapped_case(material="al6061", process="machined", insert=False, into="block", tnut=False):
    d = Design("tap")
    d.add("lid", Pos(0, 0, 21.5) * (Box(30, 30, 3) - Cylinder(1.7, 3)), material="steel", process="sheet")
    if into == "block":
        d.add("block", Pos(0, 0, 10) * Box(30, 30, 20), material=material, process=process)
    else:
        place(d, "block", extrusion_2020(100), Location((0, 0, 10), (0, 90, 0)))      # along Z: its end face at z = 60
        d.get("lid").shape = Pos(0, 0, 60 - 20 + 1.5) * (Box(30, 30, 3) - Cylinder(2.75, 3))
    if into == "block":
        add_screw(d, "s", "M3", 10, at=(0, 0, 23), threads_into="block", clamps=("lid",), insert=insert)
    else:
        add_screw(d, "s", "M5", 14, at=(0, 0, 63 - 20), threads_into="block", clamps=("lid",), tnut=tnut)
    return d


def test_dg02_tapped_aluminium_and_extrusion_ends():
    f = found(run(tapped_case()), "tapped_aluminium", "warning")
    assert f and f[0].data["part"] == "block" and f[0].data["value"] == 1
    assert found(run(tapped_case(process="sheet")), "tapped_aluminium")
    assert not found(run(tapped_case(insert="steel")), "tapped_aluminium")
    assert not found(run(tapped_case(insert="pem", process="sheet")), "tapped_aluminium")
    assert not found(run(tapped_case(material="steel")), "tapped_aluminium")
    assert found(run(tapped_case(into="extrusion")), "tapped_extrusion_end")
    assert not found(run(tapped_case(into="extrusion", tnut=True)), "tapped_extrusion_end")


def cnc_case(kind):
    d = Design("cnc")
    p = Pos(0, 0, 3) * Box(80, 50, 6)
    for x in (-30, 30):
        p -= Pos(x, 0, 3) * Cylinder(2.75, 6)
    if kind == "counterbore":
        p -= Pos(30, 0, 5) * Cylinder(4.75, 2)
    if kind == "bore":
        p -= Pos(0, 0, 3) * Cylinder(11, 6)
        place(d, "b", bearing("608"), Location((0, 0, 3)))
    d.add("plate", p, material="al6061", process="machined", meta={"cnc_reason": "flatness-critical face"} if kind == "reason" else {})
    return d


def test_dg03_machined_part_with_only_through_features():
    r = run(cnc_case("through"))
    f = found(r, "cnc_2d_candidate", "info")
    assert f and f[0].data["thickness_mm"] == pytest.approx(6.0)
    assert not found(run(cnc_case("counterbore")), "cnc_2d_candidate")
    assert not found(run(cnc_case("bore")), "cnc_2d_candidate")
    r = run(cnc_case("reason"))
    assert not found(r, "cnc_2d_candidate") and r.metrics["machined_parts"][0]["cnc_reason"] == "flatness-critical face"


def test_waivers_come_across_with_include():
    sub = printed_motor_mount()
    sub.waive("DG-01", "mount", reason="test rig only, the motor runs unloaded on the bench")
    top = Design("top")
    top.include(sub, prefix="a_")
    assert top.waivers[0]["parts"] == ["a_mount"]


# ---------------------------------------------------------------------------------------------------- DG-04: no thread in plastic
def printed_thread_case(how="tapped", reason=None, load=False):
    """A steel lid on a printed block. how: 'tapped' (screw threads into the plastic), 'insert' (heat-set insert),
    'bolt' (clearance hole through the block, nut underneath). load: the lid is declared in a load path."""
    d = Design("pt")
    d.add("lid", Pos(0, 0, 21.5) * (Box(30, 30, 3) - Cylinder(1.7, 3)), material="steel", process="sheet",
          meta={"load_path": True} if load else {})
    blk = Pos(0, 0, 10) * Box(30, 30, 20)
    if how == "bolt":
        blk -= Pos(0, 0, 10) * Cylinder(1.8, 20)
    d.add("block", blk, material="petg", process="printed", meta={"print_up": "+Z"})
    if how == "bolt":
        add_screw(d, "s", "M3", 30, at=(0, 0, 23), clamps=("lid", "block"))
        add_nut(d, "n", "M3", at=(0, 0, 0), direction=(0, 0, -1), screw="s", standard="iso10511")
    else:
        add_screw(d, "s", "M3", 10, at=(0, 0, 23), threads_into="block", clamps=("lid",), insert=(how == "insert"),
                  insert_reason=reason)
    return d


def test_dg04_thread_in_a_printed_part():
    f = found(run(printed_thread_case("tapped")), "thread_in_printed_part", "warning")
    assert f and f[0].data["part"] == "block" and f[0].data["value"] == 1 and "FST-090" in f[0].data["see_also"]
    assert found(run(printed_thread_case("insert")), "thread_in_printed_part", "warning")          # an insert without a reason
    assert found(run(printed_thread_case("insert", reason="short")), "thread_in_printed_part")     # a reason under 20 characters
    r = run(printed_thread_case("insert", reason="blind hood: no access for a nut inside it"))
    assert not found(r, "thread_in_printed_part") and r.metrics["threads_in_printed_parts"]["accepted_inserts"][0]["screw"] == "s"
    assert not found(run(printed_thread_case("bolt")), "thread_in_printed_part")
    assert found(run(printed_thread_case("tapped", load=True)), "thread_in_printed_part", "error")  # in a load path
    d = printed_thread_case("tapped")
    d.waive("DG-04", "block", reason="test fixture, opened once and never loaded")
    assert not found(run(d), "thread_in_printed_part")
    assert RULES["FST-090"].status == "xref" and "DG-04" in RULES["FST-090"].checked_by


# ---------------------------------------------------------------------------------------------------- DG-05: printed holes
def printed_hole_case(hole, axis="z", washer=False):
    """A 4 mm printed plate (printed +Z up) on a 3 mm steel plate, an M3 through-bolt with a nut. axis 'z': the hole is
    vertical in the print; 'x': its axis lies in the build plane."""
    d = Design("ph")
    if axis == "z":
        d.add("pp", Pos(0, 0, 2) * (Box(30, 30, 4) - Cylinder(hole / 2, 4)), material="petg", process="printed",
              meta={"print_up": "+Z"})
        d.add("base", Pos(0, 0, -1.5) * (Box(30, 30, 3) - Cylinder(1.7, 3)), material="steel", process="sheet")
        add_screw(d, "s", "M3", 12, at=(0, 0, 4), clamps=("pp", "base"), washer=washer)
        add_nut(d, "n", "M3", at=(0, 0, -3), direction=(0, 0, -1), screw="s")
    else:
        from build123d import Rot
        d.add("pp", Pos(2, 0, 0) * (Box(4, 30, 30) - Rot(0, 90, 0) * Cylinder(hole / 2, 4)), material="petg", process="printed",
              meta={"print_up": "+Z"})
        d.add("base", Pos(-1.5, 0, 0) * (Box(3, 30, 30) - Rot(0, 90, 0) * Cylinder(1.7, 3)), material="steel", process="sheet")
        add_screw(d, "s", "M3", 12, at=(4, 0, 0), direction=(-1, 0, 0), clamps=("pp", "base"), washer=washer)
        add_nut(d, "n", "M3", at=(-3, 0, 0), direction=(-1, 0, 0), screw="s")
    return d


def test_dg05_printed_clearance_holes():
    from mechloop.parts import printed_clearance_hole

    assert [printed_clearance_hole(s) for s in ("M2.5", "M3", "M4", "M5", "M6")] == [3.1, 3.6, 4.7, 5.7, 6.8]
    assert printed_clearance_hole("M3", in_plane=True) == 3.7
    f = found(run(printed_hole_case(3.4)), "printed_hole_too_small", "warning")         # medium 3.4 + 0.2 = 3.6
    assert f and f[0].data["value"] == pytest.approx(3.4, abs=0.03) and f[0].data["limit"] == pytest.approx(3.6)
    r = run(printed_hole_case(3.6))
    assert not found(r, "printed_hole_too_small") and not found(r, "printed_hole_oversize_no_washer")
    assert r.metrics["printed_clearance_holes"][0]["orientation"] == "vertical"
    f = found(run(printed_hole_case(3.6, axis="x")), "printed_hole_too_small")            # in the build plane: 3.7
    assert f and f[0].data["limit"] == pytest.approx(3.7)
    assert not found(run(printed_hole_case(3.7, axis="x")), "printed_hole_too_small")
    d = printed_hole_case(3.4)
    d.practice = {"limits": {"DG-05.allowance_vertical_mm": 0.0}}                         # the owner's calibrated allowance
    assert not found(run(d), "printed_hole_too_small")
    f = found(run(printed_hole_case(4.4)), "printed_hole_oversize_no_washer", "warning")  # coarse 3.6 + 0.4 = 4.0, bare head
    assert f and f[0].data["limit"] == pytest.approx(4.0)
    assert not found(run(printed_hole_case(4.4, washer=True)), "printed_hole_oversize_no_washer")
    assert not found(run(plate_pair(hole=7.0, nscrews=2)), "printed_hole_oversize_no_washer")    # metal: FST-020's


# ---------------------------------------------------------------------------------------------------- DG-01: metal sleeves
def sleeve_case(plastic_t=3.8, join=True):
    """A printed plate on a loaded aluminium block, located on a 4 mm aluminium sleeve the screw clamps through; a
    washer under the head bears on the sleeve's end."""
    from mechloop.parts.hardware import spacer_round

    d = Design("sl")
    d.add("block", Pos(0, 0, -5) * (Box(40, 40, 10) - Cylinder(1.7, 10)), material="al6061", process="sheet",
          meta={"load_path": True})
    d.add("holder", Pos(0, 0, plastic_t / 2) * (Box(30, 30, plastic_t) - Cylinder(3.3, plastic_t)), material="abs",
          process="printed", meta={"print_up": "+Z"})
    place(d, "sleeve", spacer_round("M3", 4.0, "aluminium"), Location((0, 0, 0)))
    add_screw(d, "s", "M3", 18, at=(0, 0, 4.0), clamps=("sleeve", "block"), washer=True)
    add_nut(d, "n", "M3", at=(0, 0, -10), direction=(0, 0, -1), screw="s", locking="nyloc")
    if join:
        d.join("sleeve", "holder", "located on the compression sleeve")
    return d


def test_dg01_clamp_through_a_declared_metal_sleeve_is_not_a_load_path():
    r = run(sleeve_case())
    assert not found(r, "printed_load_path")
    assert r.metrics["printed_parts_on_metal_sleeves"]["holder"]["block"][0]["sleeve"] == "sleeve"
    assert found(run(sleeve_case(join=False)), "printed_load_path", "error")            # no declared sleeve: contact counts
    assert found(run(sleeve_case(plastic_t=4.0)), "printed_load_path", "error")         # the washer bears on the plastic too


# ---------------------------------------------------------------------------------------------------- FST-072
def test_fst072_nyloc_temperature():
    d = sleeve_case()
    d.get("block").meta["service_temp_c"] = 150.0
    f = found(run(d), "nyloc_too_hot", "warning")
    assert f and f[0].data["value"] == 150.0 and f[0].data["limit"] == 120.0
    d.get("block").meta["service_temp_c"] = 60.0
    assert not found(run(d), "nyloc_too_hot")
