"""Checks for the support code added with printer_v10_1 ("make sure all fasteners are in place"):

- drawn drop-in T-nuts (`design.tnut_style = "drop_in"`, catalogue `tnut_2020`) and corner-bracket leg screws;
- the T-slot screw checks of the interference verifier (bottoming in the slot, thread in the T-nut, the T-nut's own fit),
  and the end of the blanket overlap excuse between a T-slot screw and its extrusion;
- the hardware completeness rule of the practice verifier (DG-06);
- a drop-in T-nut's assembly direction;
- the display models and the three states of purchased-part geometry;
- printer_v10_1's own declared facts against printer_v10.

Slot and T-nut dimensions are data (mechloop/parts/vendor/tslot_2020_hardware.json, read from Misumi's catalogue drawings):
the tests pin the arithmetic of the checks on those figures.
"""
import importlib.util
import math
from pathlib import Path

import numpy as np
import pytest
from build123d import Box, Cylinder, Location, Pos

from mechloop import parts as P
from mechloop.model import Design
from mechloop.parts import add_corner_bracket, add_screw, extrusion_2020, place, vendor_cad
from mechloop.parts.tslot import assumed_dimensions, slot_2020, slot_frame, tnut_2020
from mechloop.verifiers.interference import SLOT_BOTTOM_MARGIN_MM, verify_interference
from mechloop.verifiers.practice import verify_practice

ROOT = Path(__file__).resolve().parents[1]
W5 = 1.1          # the M5 washer that is bought (McMaster 91166A240, measured in its STEP): the catalogue had 1.0
B_TYPE = "2020 slot 6, B-type (community STEP) + Misumi HNTAJ5 nut"


def bar(style="drop_in", plate_t=3.175):
    """A 2020 bar along X with a plate on its top face (z 10 .. 10 + plate_t), M5 clearance holes at x = -20, 0, 20."""
    d = Design("tslot", base="bar")
    d.tnut_style = style
    place(d, "bar", extrusion_2020(100), Location((0, 0, 0)))
    pl = Pos(0, 0, 10 + plate_t / 2) * Box(60, 20, plate_t)
    for x in (-20, 0, 20):
        pl -= Pos(x, 0, 10 + plate_t / 2) * Cylinder(2.75, plate_t)
    d.add("plate", pl, material="al6061")
    return d


def codes(r, sev=None):
    return [f.code for f in r.findings if sev is None or f.severity == sev]


def finding(r, code):
    return next(f for f in r.findings if f.code == code)


# ---------------------------------------------------------------- the slot and the T-nut (Misumi's catalogue drawings)
def test_slot_section_is_misumis_drawing_beside_the_plain_simulation_slot():
    s = slot_2020()
    assert (s["opening"], s["lip"], s["depth"], s["cavity_width"]) == (6.0, 2.0, 6.0, 12.0)       # 6, 2, 2 + 4, 12 on the drawing
    assert "READ from the maker's catalogue drawing" in s["status"] and "HFS5" in s["profile"]
    (b,) = s["alternatives"]                                  # one other 2020 section on file; McMaster's 5 mm slot is not judged
    assert (b["name"], b["lip"], b["depth"], b["report_as"]) == (B_TYPE, 1.5, 5.3, "warning") and "ASSUMED" in b["status"]
    assert b["tnut"]["M5"] == {"thread_start": 0.7, "thread_length": 3.2}
    assert s["sim_depth"] == 5.0
    st = extrusion_2020(100)
    assert st.interfaces["slot"]["depth"] == 6.0 and st.interfaces["slot_width"] == 6.2
    for f in ("misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf", "misumi_2019_US_2686_HFS5_extrusions_slot_details.pdf"):
        assert (ROOT / "vendor_docs" / f).read_bytes()[:4] == b"%PDF"
    assert "not used" in __import__("json").load(open(ROOT / "mechloop/parts/vendor/tslot_2020_hardware.json"))["decision"]


def test_tnut_is_misumis_hntaj5_remade_from_its_drawing():
    for size in ("M3", "M5"):
        st = tnut_2020(size)
        bb = st.shape.bounding_box()
        assert st.sku == f"TNUT-2020-{size}" and st.catalog and st.verified and st.source["part"] == f"MISUMI HNTAJ5-{size[1:]}"
        assert (round(bb.size.X, 3), round(bb.size.Y, 3), round(bb.size.Z, 3)) == (10.0, 8.0, 3.2)
        assert bb.max.Z == pytest.approx(0.8) and bb.min.Z == pytest.approx(-2.4)       # neck above the bearing face, body below
        i = st.interfaces
        assert (i["insertion"], i["thread_length"], i["thread_offset"], i["neck_width"], i["body_height"]) == ("drop-in", 3.2, -0.8, 5.8, 2.4)
        assert vendor_cad.model_state(st.model) == "faithful re-make" and "p.2717" in st.model["remade_from"]
        assert len(st.ratings["left_out_of_the_model"]) == 3            # chamfers, leaf spring, countersink ring: no dimension given
        assert st.detail.volume < st.shape.volume                       # the display model has the thread's hole
        assert vendor_cad.check_stock(st)[0] == []
    assert tnut_2020("M5").ratings["reference_tightening_torque_nm"] == 6.8 and "reference_tightening_torque_nm" not in tnut_2020("M3").ratings
    with pytest.raises(ValueError):
        tnut_2020("M4")
    whats = " | ".join(a["what"] for a in assumed_dimensions())
    for word in ("slot depth", "lip thickness", "T-nut overall height", "thread length", "how the T-nut seats", "tolerances", "tip and the slot floor"):
        assert word in whats
    assert sum("READ" in a["status"] for a in assumed_dimensions()) >= 6


def test_slot_frame_gives_depth_below_the_face_and_offset_from_the_centre_line():
    d = bar()
    fr = slot_frame(d.get("bar"), (5.0, 0.4, 13.0), (0, 0, -1))
    assert fr["depth"] == pytest.approx(-3.0) and fr["offset"] == pytest.approx(0.4) and fr["along_mm"] == pytest.approx(5.0)
    assert tuple(np.round(fr["normal"], 6)) == (0.0, 0.0, 1.0) and fr["half_length"] == pytest.approx(50.0)
    assert slot_frame(d.get("bar"), (0, 0, 13), (1, 0, 0)) is None            # along the bar: not into a slot face
    assert slot_frame(d.get("plate"), (0, 0, 13), (0, 0, -1)) is None         # not an extrusion


# ---------------------------------------------------------------- drawn T-nuts
def test_tnut_screw_draws_its_tnut_under_the_lips_on_the_screw_axis():
    d = bar()
    add_screw(d, "s", "M5", 10, at=(20, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    names = [c.name for c in d.components]
    assert names == ["bar", "plate", "s", "s_tnut", "s_washer", "s_washer_2"] and not d.bom_extras
    tn = d.get("s_tnut")
    bb = tn.shape.bounding_box()
    assert tn.sku == "TNUT-2020-M5" and tn.meta["tnut_of"] == "s" and d.get("s").meta["tnut_part"] == "s_tnut"
    assert bb.max.Z == pytest.approx(10.0 - 2.0 + 0.8) and bb.min.Z == pytest.approx(10.0 - 2.0 - 2.4)      # lip 2.0, neck 0.8, body 2.4
    assert (bb.min.X + bb.max.X) / 2 == pytest.approx(20.0) and (bb.size.X, bb.size.Y) == pytest.approx((10.0, 8.0))
    # two washers: the head sits 2 mm above the plate
    assert d.get("s").shape.bounding_box().max.Z == pytest.approx(13.175 + 2 * W5 + 5.0)
    assert d.get("s_washer_2").shape.bounding_box().min.Z == pytest.approx(13.175 + W5)
    # the screw's allowed overlap with the bar is no longer its whole volume: only what the real slot is deeper than the drawn one
    assert d.allowed_overlaps[frozenset(("s", "bar"))] == pytest.approx(math.pi * 2.5 ** 2 * 1.0)


def test_without_tnut_style_the_tnut_stays_a_bom_line_and_the_check_says_it_did_not_run():
    d = bar(style=None)
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True)
    assert [c.name for c in d.components] == ["bar", "plate", "s", "s_washer"] and d.bom_extras["TNUT-2020-M5"]["qty"] == 1
    r = verify_interference(d)
    assert "tslot_screws_not_checked" in codes(r, "info") and not codes(r, "error")
    assert r.metrics["tslot_screws"] == {"checked": False, "screws": 1}


def test_a_tnut_screw_must_follow_its_extrusion():
    d = Design("order")
    d.tnut_style = "drop_in"
    d.add("plate", Pos(0, 0, 11) * Box(20, 20, 2))
    with pytest.raises(ValueError, match="place the extrusion before"):
        add_screw(d, "s", "M5", 8, at=(0, 0, 12), threads_into="bar", tnut=True)


# ---------------------------------------------------------------- the T-slot screw check: known answers
def judged(length, washers, plate_t=3.175, size="M5"):
    d = bar(plate_t=plate_t)
    add_screw(d, "s", size, length, at=(0, 0, 10 + plate_t), threads_into="bar", tnut=True, clamps=("plate",),
              washer=bool(washers), washers=max(1, washers))
    r = verify_interference(d)
    return r, r.metrics["tslot_screws"]["rows"][0]


def test_m5x10_through_an_eighth_inch_plate_and_one_washer_bottoms_in_the_slot():
    """The owner's v9 finding (with the 1.0 mm washer of the time: 5.825 mm into a 6.0 mm slot, 16.2 mm^3 into the 5.0 mm
    deep simulation slot, which the old blanket excuse hid). With the 1.1 mm washer that is bought: 10 - 3.175 - 1.1 =
    5.725 mm, 0.275 mm from the floor."""
    assert P.hardware.WASHER["normal"]["M5"][2] == W5
    r, row = judged(10, 1)
    assert row["depth_in_slot_mm"] == pytest.approx(5.725) and row["tip_to_floor_mm"] == pytest.approx(0.275)
    f = finding(r, "screw_bottoms_in_slot")
    assert f.severity == "error" and f.data["grip_mm"] == pytest.approx(4.275) and "0.5" in f.message
    assert row["standard_lengths_that_fit"] == [8] and "M5 x 8" in f.data["hint"]      # 2.5 mm of thread (0.505 d): just enough
    assert "interference" not in codes(r)                                # 16.2 mm^3 is inside what the real slot allows


def test_m5x12_through_the_same_stack_is_an_interference_too():
    r, row = judged(12, 1)
    f = finding(r, "screw_bottoms_in_slot")
    assert row["tip_to_floor_mm"] == pytest.approx(-1.725) and "before the joint is clamped" in f.message
    i = finding(r, "interference")           # 2.725 mm into the solid under the 5.0 mm simulation slot: 53 mm^3 > 19.6 allowed
    assert set(i.data["parts"]) == {"s", "bar"} and i.data["volume_mm3"] == pytest.approx(math.pi * 2.5 ** 2 * 2.725, rel=0.02)


def test_thread_in_the_nut_is_counted_from_the_top_of_its_neck():
    """The nut's thread runs from 1.2 to 4.4 mm below the face (neck top to body bottom). M5 x 8 through plate and washer
    ends 3.725 mm down: 2.525 mm (0.505 d), a pass with a warning (not the whole nut). With a second washer it ends
    2.625 mm down: 1.425 mm (0.285 d), an error."""
    r, row = judged(8, 1)
    assert row["engagement_mm"] == pytest.approx(2.525) and not codes(r, "error") and row["through_whole_nut"] is False
    w = finding(r, "tnut_thread_engagement_marginal")
    assert w.severity == "warning" and w.data["count"] == 1
    r, row = judged(8, 2)
    assert row["engagement_mm"] == pytest.approx(1.425) and row["engagement_d"] == pytest.approx(0.285)
    f = finding(r, "tnut_thread_engagement")
    assert f.severity == "error" and f.data["required_mm"] == pytest.approx(2.5) and "1.2 mm below" in f.message
    assert "screw_bottoms_in_slot" not in codes(r)


def test_m5x10_with_a_second_washer_passes_through_the_whole_nut():
    r, row = judged(10, 2)
    assert row["depth_in_slot_mm"] == pytest.approx(4.625) and row["engagement_mm"] == pytest.approx(3.2)
    assert row["through_whole_nut"] and not [f for f in r.findings if f.severity != "info"]      # 0.64 d, as its maker rates the nut
    # the same screw on the other 2020 section on file: 0.675 mm off that floor, the whole nut again
    assert row["alternatives"][B_TYPE] == {"engagement_mm": pytest.approx(3.2), "tip_to_floor_mm": pytest.approx(0.675)}
    v = r.metrics["tslot_screws"]["verdicts_by_geometry"]
    assert set(v) == {"used", B_TYPE} and all(x["bottoms"] == 0 and x["short"] == 0 for x in v.values())
    assert v["used"]["full_nut_thread"] == 1


def test_a_screw_that_passes_here_but_not_on_the_other_section_on_file_is_named():
    """A bare M5 x 8 through 2.6 mm ends 5.4 mm down: 0.6 mm off Misumi's floor, on the floor of the B-type section."""
    r, row = judged(8, 0, plate_t=2.6)
    assert not codes(r, "error")
    f = finding(r, "tslot_profile_sensitive")
    assert f.severity == "warning" and f.data["geometry"] == B_TYPE and (f.data["short"], f.data["bottoms"]) == (0, 1)
    assert r.metrics["tslot_screws"]["verdicts_by_geometry"][B_TYPE]["bottoming_screws"] == ["s"]


def test_m3x8_through_a_rail_seat_has_a_full_nuts_thread():
    """An MGN12 rail's screw seat is 3.5 mm above its base: M3 x 8 ends 4.5 mm into the slot, through the nut's whole 3.2 mm
    of thread (1.07 d)."""
    r, row = judged(8, 0, plate_t=3.5, size="M3")
    assert row["engagement_mm"] == pytest.approx(3.2) and row["engagement_d"] == pytest.approx(1.067, abs=1e-3)
    assert not codes(r, "error") and "tnut_thread_engagement_marginal" not in codes(r)
    assert row["tip_to_floor_mm"] == pytest.approx(1.5) and row["alternatives"][B_TYPE]["tip_to_floor_mm"] == pytest.approx(0.8)


def test_margin_is_the_documented_half_millimetre_and_the_hint_names_a_length_that_fits():
    assert SLOT_BOTTOM_MARGIN_MM == 0.5
    r, row = judged(10, 1, plate_t=6.35)              # v10's nut plates: 2.55 mm in, 1.35 mm of thread; M5 x 12 passes the whole nut
    f = finding(r, "tnut_thread_engagement")
    assert row["standard_lengths_that_fit"] == [12] and "M5 x 12" in f.data["hint"]


def test_a_missing_or_moved_tnut_and_an_off_centre_screw_are_errors():
    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    d.components = [c for c in d.components if c.name != "s_tnut"]
    assert "tnut_missing" in codes(verify_interference(d), "error")
    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    tn = d.get("s_tnut")
    tn.shape = tn.shape.moved(Location((0, 0, -0.6)))
    tn.meta["placement"][2][3] -= 0.6
    assert "tnut_misplaced" in codes(verify_interference(d), "error")
    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0.8, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    assert "screw_off_slot_centre" in codes(verify_interference(d), "error")


def test_a_tnut_too_deep_for_the_slot_or_not_drop_in_is_reported():
    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    itf = d.get("s_tnut").meta["interfaces"]
    itf["body_height"] = 4.5                           # 2.0 + 4.5 > 6.0
    r = verify_interference(d)
    assert "deeper than the 6 mm slot" in finding(r, "tnut_does_not_fit").message
    itf["body_height"], itf["neck_width"] = 2.4, 6.4
    assert "does not stand in the 6 mm opening" in finding(verify_interference(d), "tnut_does_not_fit").message
    itf["neck_width"], itf["insertion"] = 5.8, "slide-in"
    r = verify_interference(d)
    assert finding(r, "tnut_needs_end_loading").severity == "warning" and r.metrics["tslot_screws"]["tnut_types"] == ["slide-in"]


def test_two_tnuts_at_one_place_in_adjacent_slots_do_not_collide():
    """The 8 mm wide, 2.4 mm thick body stays inside the slot's 45 degree walls, so nuts in the top and side slots at the same
    station do not overlap."""
    d = Design("corner", base="bar")
    d.tnut_style = "drop_in"
    place(d, "bar", extrusion_2020(100), Location((0, 0, 0)))
    d.add("top", Pos(0, 0, 11.5) * (Box(20, 20, 3) - Cylinder(2.75, 3)), material="al6061")
    d.add("side", Pos(0, 11.5, 0) * (Box(20, 3, 20) - Pos(0, 0, 0) * Cylinder(2.75, 3, rotation=(90, 0, 0))), material="al6061")
    add_screw(d, "a", "M5", 8, at=(0, 0, 13), threads_into="bar", tnut=True, clamps=("top",))
    add_screw(d, "b", "M5", 8, at=(0, 13, 0), direction=(0, -1, 0), threads_into="bar", tnut=True, clamps=("side",))
    r = verify_interference(d)
    assert "interference" not in codes(r) and not codes(r, "error")


# ---------------------------------------------------------------- corner brackets
def corner(style="drop_in", **kw):
    d = Design("brk", base="a")
    d.tnut_style = style
    place(d, "a", extrusion_2020(100), Location((0, 0, 0)))
    place(d, "b", extrusion_2020(80), Location((-40, 0, 50), (0, 90, 0)))
    add_corner_bracket(d, "k", "a", "b", (-30, 0, 10), (1, 0, 0), (0, 0, 1), **kw)
    return d


def test_bracket_legs_on_slots_get_real_screws_and_tnuts():
    d = corner()
    assert [c.name for c in d.components] == ["a", "b", "k", "k_screw_a", "k_screw_a_tnut", "k_screw", "k_screw_tnut"]
    assert {d.get(n).sku for n in ("k_screw_a", "k_screw")} == {"SHCS-M5x8"} and not d.bom_extras
    assert {f.name for f in d.fasteners} == {"k_screw_a", "k_screw"}
    r = verify_interference(d)
    rows = {x["screw"]: x for x in r.metrics["tslot_screws"]["rows"]}
    assert not codes(r, "error")
    for n in ("k_screw_a", "k_screw"):        # 3 mm leg, no washer: 5.0 mm into the slot, through the whole nut (3.2 mm, 0.64 d)
        assert rows[n]["grip_mm"] == pytest.approx(3.0) and rows[n]["engagement_d"] == pytest.approx(0.64) and rows[n]["through_whole_nut"]
    assert finding(r, "tslot_profile_sensitive").data["count"] == 2      # 0.3 mm from the floor of the shallower section on file
    from mechloop.verifiers.assemblability import verify_assemblability

    asm = verify_assemblability(d)
    assert not codes(asm, "error") and asm.metrics["fasteners_drivable_in_sequence"] == "2/2"
    seq = asm.metrics["assembly_sequence"]
    assert seq.index("k") < seq.index("k_screw") and seq.index("k_screw_tnut") < seq.index("k_screw")      # the nut may arrive with the bracket


def test_bracket_legs_stay_bom_lines_without_tnut_style_and_bad_offsets_are_refused():
    d = corner(style=None)
    assert [c.name for c in d.components] == ["a", "b", "k"]
    assert d.bom_extras["SHCS-M5x8"]["qty"] == 2 and d.bom_extras["TNUT-2020-M5"]["qty"] == 2
    with pytest.raises(ValueError, match="outside the casting's slot"):
        corner(slot_leg={"offsets": (11.5, 14.3)})


def test_washers_under_both_bracket_heads_do_not_fit_and_the_default_says_so():
    """Why the default bracket screw has no washer: with one under each head the heads (or, further out, the slot's end)
    collide."""
    assert P.BRACKET_SLOT_LEG == {"size": "M5", "length": 8, "washers": 0, "offsets": (11.5, 13.1)}
    d = corner(slot_leg={"length": 8, "washers": 1, "offsets": (12.0, 13.0)})
    r = verify_interference(d)
    assert any(f.code == "interference" and set(f.data["parts"]) == {"k_screw_a", "k_screw"} for f in r.findings)


# ---------------------------------------------------------------- drop-in direction in the assembly plan
def test_a_drop_in_tnut_leaves_only_through_its_slots_opening():
    from mechloop.assembly.planner import _only_directions, plan

    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    assert _only_directions(d.get("s_tnut")) == {"+Z"} and _only_directions(d.get("plate")) is None
    from mechloop.assembly.planner import tnut_carried_through

    # it may arrive on its screw through the plate and washers that screw goes through (post-assembly insertion)
    assert tnut_carried_through(d, d.get("s_tnut")) == {"s", "plate", "s_washer", "s_washer_2"}
    p = plan(d, two_step=False)
    order = [st.unit for st in p.steps]
    assert p.complete and order.index("s_tnut") < order.index("s")
    step = next(st for st in p.steps if st.unit == "s_tnut")
    assert step.path == [("-Z", float("inf"))]                    # put in from above, through the opening
    # something else over the slot's opening does block it
    d.add("lid", Pos(40, 0, 13.7) * Box(18, 20, 1.0), material="al6061")      # beside the screw, not on its axis
    d.join("lid", "plate", "bond")
    assert "lid" not in tnut_carried_through(d, d.get("s_tnut"))
    d.get("s_tnut").meta["interfaces"]["insertion"] = "slide-in"
    assert _only_directions(d.get("s_tnut")) is None


# ---------------------------------------------------------------- completeness (practice DG-06)
def dg06(d):
    r = verify_practice(d)
    return [f for f in r.findings if f.data.get("rule") == "DG-06"], r.metrics["hardware_completeness"]


def test_bom_only_hardware_is_an_error_each_line_named():
    d = bar(style=None)
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True)
    d.bom_extra("NYLOC-M3-UPGRADE", 6, 0.03)
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 1, 4.0)            # not hardware: not this rule's business
    fs, m = dg06(d)
    assert sorted((f.code, f.severity, f.data["parts"][0]) for f in fs) == [("hardware_bom_only", "error", "NYLOC-M3-UPGRADE"),
                                                                           ("hardware_bom_only", "error", "TNUT-2020-M5")]
    assert m["bom_only_hardware"] == {"TNUT-2020-M5": 1, "NYLOC-M3-UPGRADE": 6} and m["tnut_screws_without_part"] == 1


def test_bom_quantity_must_equal_the_parts_drawn():
    d = bar()
    add_screw(d, "s", "M5", 8, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",))
    d.bom_extra("SHCS-M5x8", 64, 0.08)
    fs, _ = dg06(d)
    f = next(f for f in fs if f.code == "hardware_count_mismatch")
    assert f.severity == "error" and "65" in f.message and "1 are drawn" in f.message


def test_a_join_that_names_a_fastener_needs_a_drawn_one():
    d = bar()
    d.join("plate", "bar", "m5_tnut")
    fs, m = dg06(d)
    assert [f.code for f in fs] == ["joint_without_fasteners"] and m["joins_naming_fasteners_without_one"] == 1
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    fs, m = dg06(d)
    assert not fs and m["tnuts_drawn"] == 1 and m["bom_only_hardware"] == {}


def test_tnut_without_its_screw_and_set_screw_joins_are_reported():
    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    d.get("s").meta.pop("tnut_part")
    d.join("plate", "bar", "set_screw")
    fs, m = dg06(d)
    assert sorted(f.code for f in fs) == ["tnut_not_drawn", "tnut_without_screw"]
    assert m["set_screw_joins_not_drawn"] == [{"parts": ["bar", "plate"], "kind": "set_screw"}]
    d.waive("DG-06", "s*", reason="test: the nut is deliberately left out here")
    fs, _ = dg06(d)
    assert not fs


def test_stack_rows_leave_the_tnut_out_of_the_joint():
    from mechloop.verifiers import fastener_stack as FS

    d = bar()
    add_screw(d, "s", "M5", 10, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",), washer=True, washers=2)
    row = FS.fastener_stack(d, FS.Probe(d))[0]
    assert row["tnut"] and row["tnut_part"] == "s_tnut" and row["joint"] == ["bar", "plate"]
    assert "s_tnut" not in [e["part"] for e in row["stack"]]


# ---------------------------------------------------------------- display models and their states
def test_washers_nylocs_countersunk_screws_and_probe_nuts_have_generated_models():
    from mechloop.parts.hardware import washer_flat, washer_toothed
    from mechloop.parts.probes import e2e_nut

    # parts with no supplier file in vendor_cad/inbox/: generated to their standard, placeholders
    for st in (washer_flat("M6"), washer_flat("M5", "large"), washer_toothed("M5"), P.hex_nut("M4", "iso10511"),
               e2e_nut(), e2e_nut(washer=True), P.shcs("M5", 16)):
        assert st.detail is not None and st.model["kind"] == "generated to standard", st.sku
        assert vendor_cad.model_state(st.model) == "stand-in"          # a placeholder until the supplier's file arrives
        assert vendor_cad.check_stock(st)[0] == [], st.sku
    pem = P.hex_nut("M3", "pem")
    assert pem.sku == "NUT-PEM-S-M3-1" and pem.model["kind"] == "proxy" and vendor_cad.model_state(pem.model) == "stand-in"
    assert washer_toothed("M5").sku == "WASHER-M5-SERRATED" and washer_toothed("M5").interfaces["thickness"] == 0.6


def test_model_state_has_three_values():
    assert vendor_cad.model_state({"kind": "vendor CAD"}) == "supplier CAD"
    assert vendor_cad.model_state({"kind": "generated to standard", "remade_from": "maker's drawing 123, rev B"}) == "faithful re-make"
    assert vendor_cad.model_state({"kind": "generated to standard"}) == "stand-in"
    assert vendor_cad.model_state({"kind": "community CAD"}) == "stand-in" and vendor_cad.model_state(None) == "stand-in"
    assert vendor_cad.model_state({"kind": "proxy", "state": "stand-in", "remade_from": "x"}) == "stand-in"


def test_mcmaster_numbers_say_whether_they_were_read_from_the_page():
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import mcmaster_wanted as MW

    d = bar()
    add_screw(d, "s", "M3", 8, at=(0, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",))
    add_screw(d, "t", "M3", 30, at=(20, 0, 13.175), threads_into="bar", tnut=True, clamps=("plate",))
    P.add_washer(d, "w", "M3", (40, 0, 20), series="large")
    rows = {r["sku"]: r for r in MW.rows_for(d)}
    assert set(rows) == {"SHCS-M3x8", "SHCS-M3x30", "TNUT-2020-M3", "WASHER-M3-LARGE"}
    assert rows["SHCS-M3x8"]["mcmaster"] == "91290A400" and rows["SHCS-M3x8"]["model_now"] == "supplier CAD"
    assert rows["SHCS-M3x30"]["mcmaster"].startswith("91290A171 (unverified")           # not in the supplier batch
    assert rows["SHCS-M3x30"]["model_now"] == "stand-in (generated to standard)"
    assert rows["TNUT-2020-M3"]["mcmaster"] == "" and rows["TNUT-2020-M3"]["model_now"] == "faithful re-make"
    assert rows["WASHER-M3-LARGE"]["mcmaster"] == "not sold by McMaster"
    assert P.shcs("M3", 8).ratings["mcmaster_pn_status"].startswith("confirmed on McMaster's product page")
    assert "geometry only" in P.shcs("M3", 30).ratings["mcmaster_pn_status"]


def test_supplier_cad_is_the_detail_model_and_supplier_figures_are_in_the_catalogue():
    """The 2026-11-18 batch: McMaster's STEP files in vendor_cad/inbox/ under the SKU replace the generated models and pass
    the proxy check; washers carry the bought thickness; the partly threaded M3 screws and the fully threaded M5 ones
    carry their thread length; the M5 nut that is bought is the DIN 934 one."""
    from mechloop.parts.hardware import WASHER, washer_flat
    from mechloop.verifiers import fastener_stack as FS

    assert [WASHER["normal"][s][2] for s in ("M2.5", "M3", "M4", "M5")] == [0.6, 0.6, 0.9, 1.1]
    for st, pn in ((P.shcs("M3", 8), "91290A400"), (P.shcs("M5", 70), "91290A201"), (P.shcs("M3", 40), "91290A136"),
                   (P.fhcs("M4", 40), "91294A204"), (washer_flat("M5"), "91166A240"), (P.hex_nut("M4"), "90591A255"),
                   (P.hex_nut("M3", "iso10511"), "90576A102"), (P.hex_nut("M5", "din934"), "90591A260")):
        assert st.model["kind"] == "vendor CAD" and vendor_cad.model_state(st.model) == "supplier CAD", st.sku
        assert st.ratings["mcmaster_pn"] == pn and vendor_cad.check_stock(st)[0] == [], st.sku
    assert P.shcs("M4", 6).ratings["mcmaster_pn"] == "90128A208" and "zinc" in P.shcs("M4", 6).ratings["mcmaster_pn_status"]
    assert vendor_cad.model_state(P.shcs("M4", 6).model) == "stand-in"                  # no STEP under 5 MB: generated geometry stays
    # not sold by McMaster; since 2026-11-19 (printer_v11) re-made from Accu's drawing (HPLW-M3-A2): a faithful re-make
    assert vendor_cad.model_state(washer_flat("M3", "large").model) == "faithful re-make"
    assert P.shcs("M3", 40).interfaces["thread_length"] == 18.0 and P.shcs("M5", 70).interfaces["thread_length"] == 70.0
    assert "thread_length" not in P.shcs("M3", 8).interfaces
    # the stack row of a partly threaded screw starts its thread 22 mm under the head; a fully threaded M5 x 30 at 0
    d = Design("thr")
    d.add("block", Pos(0, 0, -20) * Box(20, 60, 40), material="steel")
    add_screw(d, "a", "M3", 40, at=(0, -20, 0), threads_into="block")
    add_screw(d, "b", "M5", 30, at=(0, 20, 0), threads_into="block")
    rows = {r["screw"]: r for r in FS.fastener_stack(d, FS.Probe(d))}
    assert rows["a"]["thread_starts_mm_under_head"] == 22.0 and rows["b"]["thread_starts_mm_under_head"] == 0.0
    assert FS.thread_start_mm("M5", 30) == 8.0                                           # what ISO 4762 alone would say


# ---------------------------------------------------------------- printer_v10 and printer_v10_1
def _build(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "designs" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.build()


@pytest.fixture(scope="module")
def v10():
    return _build("printer_v10")


@pytest.fixture(scope="module")
def v101():
    return _build("printer_v10_1")


def test_v10_1_draws_every_tnut_and_bracket_screw(v10, v101):
    tn = [c for c in v101.components if c.meta.get("tnut_of")]
    assert len(tn) == 156 and sorted({c.sku for c in tn}) == ["TNUT-2020-M3", "TNUT-2020-M5"]
    assert sum(c.sku == "TNUT-2020-M3" for c in tn) == 33 and sum(c.sku == "TNUT-2020-M5" for c in tn) == 123
    # v10 had the same numbers as BOM lines, and 64 bracket screws that were not drawn
    assert v10.bom_extras["TNUT-2020-M5"]["qty"] == 123 and v10.bom_extras["TNUT-2020-M3"]["qty"] == 33
    assert v10.bom_extras["SHCS-M5x8"]["qty"] == 64
    legs = [c for c in v101.components if c.meta.get("bracket_leg_of")]
    assert len(legs) == 64 and {c.sku for c in legs} == {"SHCS-M5x8"}
    assert len([c for c in v101.components if c.sku == "BRKT-2020"]) == 32
    assert not [k for k in v101.bom_extras if k.upper().startswith(("SHCS", "NUT", "TNUT", "WASHER", "NYLOC", "PEM"))]
    assert all(c.meta["interfaces"]["insertion"] == "drop-in" for c in tn)


def test_v10_1_frame_and_made_parts_are_v10s(v10, v101):
    """No frame or envelope change, and no made part changed shape: v10.1 changes screws, washers and nuts only."""
    assert v101.envelope == v10.envelope
    old = {c.name: c for c in v10.components}
    for c in v101.components:
        if c.cots or c.name not in old:
            continue
        assert c.shape.volume == pytest.approx(old[c.name].shape.volume, rel=1e-9), c.name
        a, b = c.shape.bounding_box(), old[c.name].shape.bounding_box()
        assert (a.min.X, a.min.Y, a.min.Z, a.max.X, a.max.Y, a.max.Z) == pytest.approx((b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z), abs=1e-6), c.name
    assert {c.name for c in v10.components if not c.cots} == {c.name for c in v101.components if not c.cots}
    for c in v101.components:
        if (c.sku or "").startswith("EXT2020"):
            assert c.sku == old[c.name].sku and c.meta["placement"] == old[c.name].meta["placement"]


def test_v10_1_toolhead_fasteners_have_no_bare_simulation_solids(v10, v101):
    def hw(d):
        return [c for c in d.components if c.body == "xbody" and (c.sku or "").startswith(("SHCS", "FHCS", "NUT", "WASHER"))]

    # v10 as exported on 2026-11-18 had 26 of its 50 toolhead fasteners as bare simulation solids (20 washers, 4 nylocs, 2
    # probe nuts). The fix is in the catalogue, so v10 built today has none either; its clinch nuts are still drawn as ISO nuts
    kinds = lambda d: sorted((c.meta["model"]["kind"]) for c in hw(d))
    assert len(hw(v10)) == 50 and kinds(v10).count("proxy") == 0
    h = hw(v101)
    assert len(h) == 50
    proxies = sorted(c.sku for c in h if c.meta["model"]["kind"] == "proxy")
    assert proxies == ["NUT-PEM-S-M3-1", "NUT-PEM-S-M3-1"]            # clinch nuts: no standard to generate from; stand-ins
    assert all(c.detail is not None for c in h)
    import collections

    st = collections.Counter(vendor_cad.model_state(c.meta["model"]) for c in h)
    assert st == {"supplier CAD": 46, "stand-in": 4}                  # stand-ins: 2 clinch nuts, the probe's 2 nuts


def test_v10_1_tslot_screws_all_pass_and_v10s_wrong_ones_are_the_41_listed(v10, v101):
    from mechloop.verifiers.interference import _tslot_screws
    from mechloop.report import VerifierResult

    r = VerifierResult("interference")
    m = _tslot_screws(v101, r)
    assert m["screws"] == 156 and m["tnuts_drawn"] == 156 and m["errors"] == 0 and m["tnut_types"] == ["drop-in"]
    assert not [f for f in r.findings if f.severity == "error"]
    for row in m["rows"]:
        assert row["tip_to_floor_mm"] >= 0.5 - 1e-6 and row["engagement_d"] >= 0.5 - 1e-6, row["screw"]
    assert m["marginal_engagement"] == 4 and sum(row["through_whole_nut"] for row in m["rows"]) == 152      # the four beam bolts: 0.59 d
    # v10 judged with the same rule (its own screws, the nuts taken as drawn): which were wrong
    slot = slot_2020()
    comps = {c.name: c for c in v10.components}
    fast = {f.name: f for f in v10.fasteners}
    wrong = {}
    for c in v10.components:
        if not c.meta.get("tnut"):
            continue
        f = fast[c.name]
        a = np.array(f.axis, float)
        under = np.array(f.head_center) - a * c.meta["interfaces"]["head_h"]
        fr = slot_frame(comps[c.meta["threads_into"][0]], under, -a)
        p = fr["depth"] + float(c.sku.split("x")[1])
        eng = max(0.0, min(p, slot["lip"] + 2.4) - (slot["lip"] - 0.8))          # Misumi's nut: thread from 1.2 to 4.4 mm
        if slot["depth"] - p < 0.5 - 1e-6:
            wrong[c.name] = "bottoms"
        elif eng < 0.5 * c.meta["thread_d"] - 1e-6:
            wrong[c.name] = "short"
    assert len(wrong) == 41
    assert sum(v == "bottoms" for v in wrong.values()) == 35 and sum(v == "short" for v in wrong.values()) == 6
    assert {n for n in wrong if n.startswith("nut_plate")} == {f"nut_plate{t}_bolt_{i}" for t in ("", "_fl", "_fr") for i in (0, 1)}
    assert "earth_stud" in wrong and not [n for n in wrong if "rail" in n and "screw" in n]       # the M3 x 8 rail screws were right
    assert not [n for n in wrong if n.startswith("beam_bolt")]                                    # 0.59 d: kept as v10 had them
