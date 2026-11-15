"""Known-answer tests for the vendor-document findings (reports/"Vendor documents - what they change.md", numbered
proposals) and for the eight checker defects printer_v6's designer listed (docs/PRINTER_V6.md, "Checker behaviour
worth a look"). Each uses a small purpose-built design whose right answer is known by hand calculation or by
construction; each failed before the change it tests."""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from build123d import Box, Cylinder, Location, Pos, Rot

from mechloop import parts
from mechloop.model import Belt, Cable, Design, Joint
from mechloop.parts import (add_screw, endstop_switch, gt2_idler, gt2_pulley, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17,
                            place, shaft_coupler, vendor_data)
from mechloop.verifiers.interference import verify_interference
from mechloop.verifiers.motion import verify_motion
from mechloop.verifiers.ratings import belt_installation_tension, verify_ratings
from mechloop.verifiers.subsystems import verify_subsystems

ROOT = Path(__file__).parent.parent


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


def codes(r):
    return [f.code for f in r.findings]


# ================================================================== Part 1: vendor documents
# ---------------------------------------------------------------- 1. belt stiffness
def test_belt_stiffness_is_19kn_per_6mm_and_linear_in_width():
    """Expected EA 19 kN per 6 mm (between Gates' 16.9 and the 21 the reference machines imply), range 15 to 27 kept.
    Linear in width: a 12 mm belt is 2 x 19 = 38 kN, a 9 mm belt 28.5 kN. Before: 22 kN (44 and 33)."""
    from mechloop.twin import PrinterMap
    from mechloop.twin import fitted as F

    assert F.triple("belt_ea_n_per_6mm") == [15000.0, 19000.0, 27000.0]
    assert PrinterMap().belt_ea_n == 19000.0
    e = F.entry("belt_ea_n_per_6mm")
    assert [s["ea_n_per_6mm"] for s in e["sources"]] == [16900.0, 21000.0] and "tension" in e["rises_with_tension"]
    gates = vendor_data("gates_gt2")["belt"]["converted"]["EA_n_per_mm_width"]
    assert max(gates.values()) / min(gates.values()) < 1.03                 # Gates, 4 / 6 / 9 mm: linear within 3 %
    assert PrinterMap().belt_ea_n * 12.0 / 6.0 == 38000.0


# ---------------------------------------------------------------- 2. belt pull on a motor shaft
def belt_on_motor(length=48, tension=None, width=12.0, outboard=False):
    """A 20-tooth pulley on a motor shaft and an equal idler 200 mm away, closed belt: each wraps half a turn.
    The pulley's hub bottom is 2.5 mm above the motor face, so a 12 mm belt runs 2.5 + 6 + 1 + 6.5 = 16.0 mm from it."""
    d = Design("shaftload")
    place(d, "motor", nema17(length), Location((0, 0, 0)))
    pul = gt2_pulley(20, 5.0, width)
    place(d, "pulley", pul, Location((0, 0, 2.5)))
    idl = gt2_idler(20, 5.0, width)
    place(d, "idler", idl, Location((200, 0, 2.5 + pul.interfaces["belt_center_z"] - idl.interfaces["belt_center_z"])))
    if outboard:
        place(d, "support", parts.bearing("625"), Location((0, 0, 30.0)))
    d.belts.append(Belt("b", [("pulley", "pulley", "ccw"), ("pulley", "idler", "ccw")], width=width, tension=tension,
                        outboard_support=("pulley",) if outboard else ()))
    return d


def test_belt_pull_is_compared_with_the_motors_shaft_load_limit():
    """12 mm belt at Gates' minimum installation tension, 18.7 N per span, half a turn of wrap: 2 x 18.7 = 37.4 N on
    the shaft, 16.0 mm from the face. Limit of the 48 mm motor: 21 N at 20 mm, i.e. 21 x 20 / 16 = 26.25 N there.
    37.4 / 26.25 = 1.42: a warning. Before: nothing compared them (no belt tension in the model)."""
    assert belt_installation_tension(Belt("b", [], width=12.0))[0] == pytest.approx(18.7)
    assert belt_installation_tension(Belt("b", [], width=6.0))[0] == pytest.approx(9.3)
    r = verify_ratings(belt_on_motor())
    f = [x for x in r.findings if x.code == "motor_shaft_radial_load"]
    assert len(f) == 1 and f[0].severity == "warning"
    assert f[0].data["shaft_load_n"] == pytest.approx(37.4, abs=0.05) and f[0].data["arm_mm"] == pytest.approx(16.0)
    assert f[0].data["allowed_n"] == pytest.approx(26.25, abs=0.06) and "read from drawing, meaning inferred" in f[0].message
    assert f[0].data["tension_for_limit_n"] == pytest.approx(13.1, abs=0.05)
    m = r.metrics["belt_shaft_loads"]["b:pulley"]
    assert m["wrap_deg"] == pytest.approx(180.0, abs=0.1) and m["load_over_allowed"] == pytest.approx(1.42, abs=0.01)


def test_shaft_load_follows_the_declared_tension_and_is_not_invented_for_other_motors():
    """Declared 13 N per span: 26.0 N, under the 26.25 N limit, no finding. The 34 mm motor's sheet has no shaft-load
    line: its load is listed (2 x 18.7) but not judged. An outboard bearing takes the overhung load: not judged."""
    r = verify_ratings(belt_on_motor(tension=13.0))
    assert "motor_shaft_radial_load" not in codes(r)
    assert r.metrics["belt_shaft_loads"]["b:pulley"]["shaft_load_n"] == pytest.approx(26.0)
    r = verify_ratings(belt_on_motor(length=34))
    assert "motor_shaft_radial_load" not in codes(r) and "not judged" in r.metrics["belt_shaft_loads"]["b:pulley"]["judged"]
    r = verify_ratings(belt_on_motor(outboard=True))
    assert "motor_shaft_radial_load" not in codes(r) and r.metrics["belt_shaft_loads"]["b:pulley"]["outboard_support"] == "support"


# ---------------------------------------------------------------- 3. MGN12H rigidity and preload class
def blocks_side_by_side(preload=None):
    d = Design("z")
    for i, x in enumerate((-90, 90)):
        place(d, f"rail{i}", mgn12_rail(200), Location((x, 0, 0), (0, -90, 0)))
        blk = mgn12h_carriage(preload) if preload else mgn12h_carriage()
        place(d, f"blk{i}", blk, Location((x, 0, 0), (0, -90, 0)), body="z", guides="z")
    d.add("arm", Pos(0, 150, 0) * Box(200, 280, 6), body="z", mass_kg=2.0)
    d.joints.append(Joint("z", "slide", "world", "z", (0, 0, 1), range=(-50, 50), max_effort=1000))
    return d


@pytest.mark.parametrize("preload, k_n_um, basis", [(None, 63.0, "assumed"), ("Z1", 81.0, "declared"), ("ZF", 40.0, "declared")])
def test_guide_tilt_uses_the_makers_rigidity_for_the_preload_class(preload, k_n_um, basis):
    """Two blocks side by side resist tilting only over their own ball tracks: K = 2 k L1^2 / 12 with L1 = 32.4 mm.
    Z0 (assumed when not declared): 2 x 63e6 x 0.0324^2 / 12 = 11,022 N.m/rad; Z1: 14,172; ZF has no published
    rigidity and falls back to the assumed 40 N/um: 6,998. Before: 40 N/um and 30 mm for every block, 6,000."""
    g = verify_ratings(blocks_side_by_side(preload)).metrics["guide_loads"]["z"]
    assert g["tilt_stiffness_nm_per_rad"] == pytest.approx(2 * k_n_um * 1e6 * 0.0324 ** 2 / 12, abs=1.0)
    assert g["block_stiffness_assumed_n_per_um"] == k_n_um and g["preload_class"] == (preload or "Z0")
    assert basis in g["preload_class_basis"]
    assert ("Table 3.77" in g["block_stiffness_source"]) == (preload != "ZF")
    assert ("assumed" in g["block_stiffness_source"]) == (preload == "ZF")


# ---------------------------------------------------------------- 4. coupler bore depth
def screw_in_coupler(insertion):
    d = Design("cpl", base="motor_shaft")
    d.add("motor_shaft", Pos(0, 0, -5.75) * Cylinder(2.5, 28.5), material="steel")          # 8.5 mm into the 5 mm bore
    place(d, "coupler", shaft_coupler(5.0, 8.0), Location((0, 0, 0)))
    place(d, "leadscrew", leadscrew_t8(100, lead=2.0), Location((0, 0, 25.0 - insertion)))
    d.join("coupler", "motor_shaft", "clamp")
    d.join("leadscrew", "coupler", "clamp")
    return d


def test_shaft_drawn_deeper_than_the_coupler_bore_is_a_clash():
    """The vendor STEP's 8 mm bore is 7.3 mm of cylinder behind a 0.2 mm chamfer and the spider starts 8.6 mm in.
    A T8 screw drawn 12.5 mm in (as printer_v4 / v5 / v6 do) is 3.9 mm too deep and overlaps the corrected solid by
    pi x 4^2 x 3.9 = 196 mm^3. Before: the catalogue bore was 12.5 mm deep and nothing was reported."""
    r = verify_interference(screw_in_coupler(12.5))
    hit = [f for f in r.findings if f.code == "interference"]
    assert len(hit) == 1 and set(hit[0].data["parts"]) == {"coupler", "leadscrew"}
    assert hit[0].data["volume_mm3"] == pytest.approx(math.pi * 16 * 3.9, abs=1.0)
    deep = [f for f in r.findings if f.code == "shaft_too_deep_in_coupler"]
    assert len(deep) == 1 and deep[0].data["insertion_mm"] == pytest.approx(12.5, abs=0.01)
    assert deep[0].data["max_insertion_mm"] == 8.6 and deep[0].data["too_deep_mm"] == pytest.approx(3.9, abs=0.01)
    m = r.metrics["coupler_shaft_insertion"]
    assert m["coupler:a"]["insertion_mm"] == pytest.approx(8.5, abs=0.01) and m["coupler:a"]["max_insertion_mm"] == 12.05


def test_shaft_at_the_coupler_limit_is_clean_and_the_step_is_the_detail_model():
    r = verify_interference(screw_in_coupler(8.6))
    assert not errs(r) and r.metrics["coupler_shaft_insertion"]["coupler:b"]["insertion_mm"] == pytest.approx(8.6, abs=0.01)
    st = shaft_coupler(5.0, 8.0)
    assert st.model["kind"] == "vendor CAD" and st.model["file"] == "vendor_cad/COUPLER-5x8.step"
    assert st.interfaces["bore_depth"] == 7.5 and len(st.detail.solids()) == 5
    # the limits in the vendor file are what the STEP measures: a test shaft first meets the spider there
    from mechloop.parts import vendor_cad as vc

    spider = max(st.detail.solids(), key=lambda s: -abs(s.volume - 1539.1))
    for dia, depth, from_top in ((8.0, 8.6, True), (5.0, 12.05, False)):
        def overlap(ins):
            z = 25.1 - ins / 2 if from_top else ins / 2
            c = spider & (Pos(0, 0, z) * Cylinder(dia / 2, ins))
            return 0.0 if c is None else sum(s.volume for s in c.solids())
        assert overlap(depth - 0.15) < 0.05 and overlap(depth + 0.4) > 0.3


# ---------------------------------------------------------------- 5 / 6. rail parallelism, verified MGN12, thread depth
def test_mgn12_is_vendor_backed_with_the_makers_parallelism_and_thread_depth():
    """Hiwin Table 3.88: two MG_12 rails may be 9 um out of parallel at ZF / Z0 and 5 um at Z1 (default was 25 um).
    Table 3.79: M3 x 3.5 carriage threads, now under the key the thread check reads."""
    car = mgn12h_carriage()
    assert car.verified and mgn12_rail(300).verified and car.source["level"] == "vendor" and "approximate" not in car.ratings
    assert car.ratings["allowable_parallelism_mm"] == 0.009 and mgn12h_carriage("Z1").ratings["allowable_parallelism_mm"] == 0.005
    assert mgn12h_carriage("ZF").ratings["allowable_parallelism_mm"] == 0.009
    assert "radial_stiffness_n_per_m" not in mgn12h_carriage("ZF").ratings
    assert car.interfaces["thread_depth"] == 3.5 and "thread_depth_unverified" not in car.interfaces
    assert car.ratings["ball_track_length_m"] == pytest.approx(0.0324)


def two_rails():
    d = Design("pair", base="base")
    d.add("base", Pos(0, 0, -5) * Box(240, 160, 10), material="al6061")
    plate = Pos(0, 0, 15.5) * Box(60, 130, 5)
    for i, y in enumerate((-50, 50)):
        place(d, f"rail{i}", mgn12_rail(200), Location((0, y, 0)))
        place(d, f"blk{i}", mgn12h_carriage(), Location((0, y, 0)), body="car", guides="x")
        d.join(f"rail{i}", "base", "screwed")
        d.join(f"blk{i}", "plate", "screwed")
    d.add("plate", plate, material="al6061", body="car")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50), max_effort=50))
    return d


def test_paired_rail_metrics_carry_the_makers_allowable():
    from mechloop.tolerance import verify_tolerance

    pr = verify_tolerance(two_rails(), n=400).metrics["paired_rails"]["x"]
    assert pr["allowable_mm"] == 0.009 and "Table 3.88" in pr["allowable_source"] and pr["preload_class"] == "Z0"
    assert pr["p_within_allowable_standard_error"] == pytest.approx(math.sqrt(pr["p_within_allowable"] * (1 - pr["p_within_allowable"]) / 400),
                                                                    abs=1e-3)


@pytest.mark.parametrize("length, bottoms", [(8, True), (6, False)])
def test_carriage_screws_are_checked_against_the_3p5_mm_thread(length, bottoms):
    """A 3 mm plate on the block: an M3x8 goes 5.0 mm into holes tapped 3.5 mm deep (error); an M3x6 goes 3.0 mm,
    which is one diameter in steel (fine). Before: the depth sat under `thread_depth_unverified` and neither was checked."""
    d = Design("car", base="rail")
    place(d, "rail", mgn12_rail(100), Location((0, 0, 0)))
    place(d, "block", mgn12h_carriage(), Location((0, 0, 0)))
    plate = Pos(0, 0, 14.5) * Box(30, 27, 3)
    for x, y in ((-10, -10), (10, 10)):
        plate -= Pos(x, y, 14.5) * Cylinder(1.7, 3)
    d.add("plate", plate, material="al6061")
    d.join("block", "rail", "guide")
    for i, (x, y) in enumerate(((-10, -10), (10, 10))):
        add_screw(d, f"s{i}", "M3", length, at=(x, y, 16), threads_into="block", clamps=("plate",))
    r = verify_interference(d)
    hit = [f for f in r.findings if f.code == "thread_bottoms_out"]
    assert (len(hit) == 2) == bottoms
    if bottoms:
        assert hit[0].data["engagement_mm"] == pytest.approx(5.0, abs=0.05) and hit[0].data["depth_mm"] == 3.5
    else:
        assert "thread_engagement" not in codes(r)


# ---------------------------------------------------------------- 7. one source for the motor's resistance
def test_motor_winding_data_has_one_source():
    """17HS19-2004S1: 1.60 ohm on the 2025 drawing and the product page (the 2020 drawing said 1.40). The catalogue
    part, the electrical table and the vendor file now all read the vendor file."""
    from mechloop.parts.electrical import MOTOR_ELECTRICAL

    assert nema17(48).ratings["phase_resistance_ohm"] == 1.6 == MOTOR_ELECTRICAL["NEMA17-48"]["phase_resistance_ohm"]
    for length, rec in vendor_data("stepperonline_nema17")["parts"].items():
        st, me = nema17(int(length)), MOTOR_ELECTRICAL[f"NEMA17-{length}"]
        for k in ("rated_current_a", "phase_resistance_ohm", "phase_inductance_mh", "holding_torque_nmm"):
            assert st.ratings[k] == pytest.approx(me[k]), (length, k)
    # copper loss of one Y motor at 0.6 A in each of two phases: 2 x 0.6^2 x 1.6 = 1.15 W cold (was 1.01 W at 1.4 ohm)
    assert 2 * 0.6 ** 2 * nema17(48).ratings["phase_resistance_ohm"] == pytest.approx(1.152)


def test_motors_use_the_vendor_step_and_its_lead_exit():
    """34 and 48 mm motors: StepperOnline's own STEP. It has no connector block: four leads leave one side, 4.5 to
    7.0 mm from the rear face, in a 4.0 x 2.5 mm bundle. The pilot is 2.0 mm high in the STEP (1.5 + 0.5 chamfer), as
    on the drawing. 40 and 60 mm keep the community model with its 17.2 mm wide connector block."""
    from mechloop.parts import vendor_cad as vc

    for length, body in ((34, 33.0), (48, 48.0)):
        st = nema17(length)
        assert st.model["kind"] == "vendor CAD" and st.ratings["source"].startswith("17HS")
        b = vc.bbox6(st.detail)
        assert b[5] == pytest.approx(st.interfaces["shaft_length"], abs=0.05) and b[2] == pytest.approx(-body, abs=0.05)
        assert b[3] == pytest.approx(26.85, abs=0.01)                               # lead stubs cut 5.7 mm from the side face
        lead = st.shape & (Pos(24.5, 0, -length / 2) * Box(4.0, 40, 200))            # the solid's block outside the frame
        lb = vc.bbox6(lead)
        assert lb[4] - lb[1] == pytest.approx(4.0, abs=0.01) and lb[5] - lb[2] == pytest.approx(2.5, abs=0.01)
        assert lb[2] + body == pytest.approx(4.5, abs=0.01)
        top = st.detail & (Pos(0, 0, 1.9) * Box(60, 60, 0.02))
        assert vc.bbox6(top)[3] > 10.5                                               # pilot still there 1.9 mm above the face
    assert nema17(40).model["kind"] == "community CAD"
    assert nema17(48).ratings["max_radial_load_n"] == 21.0 and "max_radial_load_n" not in nema17(34).ratings


# ---------------------------------------------------------------- 8, 9, 15, 16. recorded ratings
def test_recorded_vendor_figures():
    """ATP-5: E 70,000 MPa and 23.6e-6 /K (sheet), flatness guarantee 0.381 mm at 12.7 mm and under, 0.127 mm above;
    6.0 mm is below the listed 6.35 mm. LRS-350: leakage 2 mA at 240 VAC, 80 % of rating at 90 VAC. Pi: -20 to 70 degC."""
    from mechloop import MATERIALS
    from mechloop.parts.electrical import psu_lrs, raspberry_pi_zero2w
    from mechloop.tolerance.process import stock_plate_flatness
    from mechloop.verifiers.fea import ALPHA

    assert MATERIALS["al_atp5"].E == 70000 and ALPHA["al_atp5"] == 23.6e-6
    thin, thick = stock_plate_flatness("al_atp5", 6.0), stock_plate_flatness("al_atp5", 20.0)
    assert thin["flatness_mm"] == 0.381 and thick["flatness_mm"] == 0.127 and not thin["stock_thickness_listed"]
    assert stock_plate_flatness("al6061", 6.0) is None
    psu = psu_lrs("LRS-350-24").ratings["electrical"]["ratings"]
    assert psu["leakage_current_ma_max"] == 2.0 and psu["derate_to_frac_at_90vac"] == 0.8 and psu["full_load_min_vac"] == 100.0
    pi = raspberry_pi_zero2w().ratings["electrical"]["ratings"]
    assert (pi["min_ambient_c"], pi["max_ambient_c"]) == (-20.0, 70.0)


def test_generic_belt_parts_say_they_are_not_gates_stock():
    """Gates lists 2 mm pitch belts in 4, 6 and 9 mm and the 20-groove sprocket with a 4.76 mm bore only."""
    wide, six = gt2_pulley(20, 5.0, 12.0), gt2_pulley(20, 5.0, 6.0)
    assert "12 mm belt in 2 mm pitch is NOT Gates stock" in wide.source["note"] and not wide.source["gates_stock_belt_width"]
    assert "NOT Gates stock" not in six.source["note"] and "4.76 mm" in six.source["note"]
    assert "NOT Gates stock" in gt2_idler(20, 5.0, 12.0).source["note"] and not wide.verified


# ---------------------------------------------------------------- 12 - 14. endstop
def lever_axis(face_y):
    """A switch fixed to the frame, lever pressed in -Y. A flat striker on the carriage; the joint moves it along Y and
    at the low end of travel (y = -20) its face is at `face_y` in the switch's frame (hole line at 1.6)."""
    d = Design("es")
    d.add("frame", Pos(0, -20, -5) * Box(60, 80, 10))
    sw = place(d, "sw", endstop_switch(), Location((0, 0, 0)))
    d.join("sw", "frame", "screwed")
    d.add("car", Pos(30, 40, 5) * Box(10, 10, 10), body="car")
    d.add("striker", Pos(-9, face_y + 20 + 5, 4.5) * Box(6, 10, 4), body="car")       # low face at face_y when y = -20
    d.joints.append(Joint("y", "slide", "world", "car", (0, 1, 0), range=(-20, 20), max_effort=10))
    d.endstops.append({"joint": "y", "switch": "sw", "at": "min"})
    return d, sw


def test_endstop_trigger_is_omrons_operating_position_with_its_spread():
    """OMRON D2F hinge lever: operating position 6.8 +/-1.5 mm from the mounting-hole line (Y 8.4 in the part frame;
    the catalogue had 10.6, which was the FREE position less 1). Movement differential 0.5, overtravel 0.55 minimum."""
    sw = endstop_switch()
    assert sw.interfaces["trigger"] == [(-9.0, 8.4, 4.5)] and sw.interfaces["operating_position_tol"] == 1.5
    assert sw.interfaces["trigger_latest"][0][1] == pytest.approx(6.9) and sw.interfaces["trigger_earliest"][0][1] == pytest.approx(9.9)
    assert sw.interfaces["overtravel"] == 0.55 and sw.interfaces["movement_differential"] == 0.5
    assert sw.interfaces["overtravel_to_case"] == 0.25 and sw.ratings["operating_force_n"] == 0.78
    assert "D2F-01L" in sw.description and "gold" in sw.description
    assert "generated, not a known bought module" in sw.source["note"] and sw.interfaces["pin_length_below"] == 2.62
    assert sw.interfaces["pin_row_omron_right_angled"]["row_below_body_bottom_mm"] == 2.6


@pytest.mark.parametrize("face_y, code, short", [
    (10.6, "endstop_not_reached", 3.7),     # where every design's striker stops today: the old trigger point
    (8.4, "endstop_not_reached", 1.5),      # the nominal operating position: late units never switch
    (6.9, None, 0.0),                       # the latest operating position: every unit switches
    (6.6, "endstop_overtravel", 0.0)])      # 0.05 mm past the case line (6.65): the lever is crushed onto the case
def test_striker_must_reach_the_latest_operating_position_and_stop_short_of_the_case(face_y, code, short):
    d, _ = lever_axis(face_y)
    r = verify_subsystems(d)
    assert errs(r) == ([code] if code else [])
    h = r.metrics["homing"]["y"]
    assert h["short_of_latest_operating_position_mm"] == pytest.approx(short, abs=0.01)
    assert h["short_of_nominal_operating_position_mm"] == pytest.approx(max(face_y - 8.4, 0.0), abs=0.01)
    if code == "endstop_not_reached":
        f = next(x for x in r.findings if x.code == code)
        assert f.data["short_of_latest_mm"] == pytest.approx(short, abs=0.01) and f.data["operating_position_tol_mm"] == 1.5


def test_declared_overtravel_lets_a_late_switch_be_reached():
    """Striker at the nominal operating position at the end of the working range, with 1.5 mm of declared mechanical
    over-travel beyond it: at the mechanical end it is at 6.9 and every unit switches."""
    d, _ = lever_axis(8.4)
    d.joints[0].overtravel = (1.5, 0.0)
    r = verify_subsystems(d)
    assert errs(r) == [] and r.metrics["homing"]["y"]["mechanical_end"] == -21.5
    assert r.metrics["homing"]["y"]["short_of_nominal_at_working_end_mm"] == pytest.approx(0.0, abs=0.01)


# ================================================================== Part 2: checker problems (docs/PRINTER_V6.md)
# ---------------------------------------------------------------- A. thermal cut-off on a hotend
def _hotend_with_cutoff(**params):
    sys.path.insert(0, str(Path(__file__).parent))
    import test_electrical as TE
    from mechloop.parts.electrical import device_from, thermal_fuse

    d = TE.rig()
    el = d.electrical
    place(d, "hs_tco", thermal_fuse(99, 76, 10), Location((0, 150, 70)))
    d.join("hs_tco", "hotend", "bond")
    device_from(el, d, "hs_tco", **params)
    el.wires = [w for w in el.wires if w.name != "hotend"]
    el.wire("hotend", "board.E0", "hs_tco.a", 20, insulation="silicone")
    el.wire("hotend tail", "hs_tco.b", "hot_heater.in", 20, insulation="silicone", length=80.0)
    return d


def test_cutoff_on_a_hotend_heat_sink_is_simulated_fan_on_and_fan_off():
    """Heat sink between the heat break (G W/K from the block) and the air (0.25 W/K fan on, 0.03 W/K still), all
    assumed. Holding 250 degC in 25 degC air it settles at (G x 250 + g x 25) / (G + g): with this cartridge's
    G = 0.025, 45.5 degC with the fan on and 127.3 degC with it stopped. A 99 degC cut-off therefore stays closed when
    the heater sticks on with the fan running, and opens when the fan has stopped. Before: KeyError 'plate'."""
    from mechloop import electrical as E
    from mechloop.verifiers import electrical as VE

    d = _hotend_with_cutoff()
    rep = VE.heater_report(d.electrical, d, E.electrical_loads(d))["extruder"]
    hs = rep["heat_sink_cutoff"]
    G = hs["assumed"]["heatbreak_w_k"]
    for label, g in (("fan_running", 0.25), ("fan_stopped", 0.03)):
        assert hs[label]["sink_c_settled_while_holding_target"] == pytest.approx((G * 250 + g * 25) / (G + g), abs=0.1)
    assert hs["fan_running"]["sink_c_peak_with_heater_stuck_on"] < 99 and not hs["fan_running"]["cutoff_opens"]
    assert hs["fan_stopped"]["cutoff_opens"] and hs["fan_stopped"]["cutoff_opens_after_s"] > 30
    assert rep["plant"].cutoffs[0]["node"] == "heat_sink"
    # the fitted block model is untouched by the side model: same block temperature with and without the cut-off
    import dataclasses

    plant = rep["plant"]
    a = E.simulate_heater(plant, rep["cfg"], 250.0, 120.0)
    b = E.simulate_heater(dataclasses.replace(plant, heat_sink=None, cutoffs=[]), rep["cfg"], 250.0, 120.0)
    assert np.allclose(a["T"], b["T"])


def test_the_verifier_reports_the_heat_sink_cutoff_honestly_and_an_unknown_node_is_a_finding(tmp_path, monkeypatch):
    from mechloop.verifiers.electrical import verify_electrical

    monkeypatch.chdir(tmp_path)
    r = verify_electrical(_hotend_with_cutoff())
    assert "check_crashed" not in codes(r)
    f = next(x for x in r.findings if x.code == "cutoff_on_heat_sink_needs_fan_failure")
    assert f.severity == "warning" and "does NOT open" in f.message and "not an independent cut-off" in f.message
    r = verify_electrical(_hotend_with_cutoff(node="plate"))
    assert "check_crashed" not in codes(r) and "thermal_fuse_node_unknown" in errs(r)


# ---------------------------------------------------------------- B. sensorless homing
def test_sensorless_homing_writes_a_config_klippy_loads(tmp_path):
    """SKR Mini E3 V3.0: each driver's DIAG goes to a jumper header whose other pin is that axis's endstop input
    (schematic), so X sensorless is diag_pin ^PC0 with the X-DIAG jumper fitted. Klipper's rules: homing_retract_dist 0
    and half a motor turn per second (40 mm per turn: 20 mm/s). Before: no diag_pin, and klippy refused the file."""
    from mechloop.electrical import klipper_config
    from mechloop.runner import load_design
    from mechloop.twin import firmware as fw

    d = load_design(ROOT / "designs" / "printer_v4.py")
    el = d.electrical
    d.endstops = [{"joint": "x", "sensorless": True} if e["joint"] == "x" else e for e in d.endstops]
    sw = next(dev for dev in el.devices.values() if dev.kind == "endstop" and dev.component == "x_endstop")
    el.wires = [w for w in el.wires if sw.name not in (w.a.split(".")[0], w.b.split(".")[0])]      # X-STOP is left empty
    cfg = klipper_config(el, d)
    c = fw._cfg(cfg)
    assert c.get("stepper_x", "endstop_pin") == "tmc2209_stepper_x:virtual_endstop"
    assert c.get("tmc2209 stepper_x", "diag_pin") == "^PC0" and 0 < c.getint("tmc2209 stepper_x", "driver_SGTHRS") <= 255
    assert c.getfloat("stepper_x", "homing_retract_dist") == 0.0 and c.getfloat("stepper_x", "homing_speed") == 20.0
    assert "X-DIAG" in cfg and not c.has_option("tmc2209 stepper_y", "diag_pin")
    try:
        fw.find_klipper()
    except fw.FirmwareNotAvailable as e:
        pytest.skip(f"Klipper is not installed: {e}")
    chk = fw.check_config(cfg, tmp_path / "chk")
    assert chk["ran"] and chk["ok"], chk


# ---------------------------------------------------------------- C. Z over-travel past the nozzle plane
def bed_under_nozzle(z_range=(0.0, 50.0), overtravel=(0.0, 0.0), clip=False, clip_body="world"):
    """Bed top at z = 50, nozzle tip at z = 100: the bed meets the nozzle plane at z = +50. `clip`: something else
    1 mm above the nozzle plane, 30 mm to the side; on the nozzle's own body ("world" here) or, with clip_body, on a
    body that does not carry the nozzle."""
    d = Design("zot")
    d.add("frame", Pos(0, 0, 150) * Box(300, 300, 10))
    d.add("hotend", Pos(0, 0, 122.5) * Box(20, 20, 45))                                    # tip face at z = 100
    if clip:
        d.add("clip", Pos(30, 0, 123) * Box(10, 10, 44), body=clip_body)                   # underside at z = 101
    d.add("bed", Pos(0, 0, 47) * Box(200, 200, 6), material="al6061", body="zbody")        # top at z = 50
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=z_range, max_effort=100, overtravel=overtravel))
    if clip_body != "world":
        d.joints.append(Joint("g", "slide", "world", clip_body, (0, 1, 0), range=(0.0, 0.0), max_effort=100))
    d.tool_point = ("world", (0.0, 0.0, 100.0))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z"}
    return d


def test_overtravel_past_the_nozzle_plane_is_not_a_collision_but_a_real_crash_still_is():
    """Range ending 2 mm past the plane (the only way to say it before): bed hits hotend, 20 x 20 x 2 = 800 mm^3, a
    false collision. Declared as working range 0..50 plus 2 mm of over-travel: no collision. With a clip 1 mm above the
    nozzle plane on a body that does NOT carry the nozzle, the same over-travel crashes the bed into it:
    10 x 10 x 1 = 100 mm^3, reported. (Since 2026-11-15 the same clip on the nozzle's own body rides with the nozzle
    and is checked at nozzle contact plus its toolhead margin, here under 1 mm: no collision. The cases for that rule,
    including a part that hangs below the nozzle, are in test_known_answers_checkers.py.)"""
    old = [f for f in verify_motion(bed_under_nozzle(z_range=(0.0, 52.0))).findings if f.code == "motion_collision"]
    assert len(old) == 1 and old[0].data["volume_mm3"] == pytest.approx(800.0, abs=1.0)
    r = verify_motion(bed_under_nozzle(overtravel=(0.0, 2.0)))
    assert "motion_collision" not in codes(r) and "nozzle_approach_overtravel" in codes(r)
    assert r.metrics["overtravel"]["z"] ["mechanical_range"] == [0.0, 52.0]
    hit = [f for f in verify_motion(bed_under_nozzle(overtravel=(0.0, 2.0), clip=True, clip_body="gantry")).findings if f.code == "motion_collision"]
    assert len(hit) == 1 and set(hit[0].data["parts"]) == {"bed", "clip"}
    assert hit[0].data["volume_mm3"] == pytest.approx(100.0, abs=1.0) and hit[0].data["pose"] == {"z": 52.0}
    assert [f for f in verify_motion(bed_under_nozzle(overtravel=(0.0, 2.0), clip=True)).findings if f.code == "motion_collision"] == []


def test_overtravel_reaches_the_probe_and_the_tolerance_figures_keep_the_working_range():
    """Probe rig: bed meets the nozzle at the end of the working range (0..50) and 2 mm of over-travel is declared.
    The probe sees a mechanical end 2 mm past the plane (firmware position_min = -2), the working end stays at 0."""
    sys.path.insert(0, str(Path(__file__).parent))
    from test_subsystems import probe_findings, probe_rig

    d = probe_rig(face_above_nozzle=1.5, z_top=0.0)
    f, z = probe_findings(d)
    assert z["nozzle_above_bed_at_end_of_z_travel_mm"] == 0.0              # ends at the plane: nothing in hand below it
    d = probe_rig(face_above_nozzle=1.5, z_top=0.0)
    next(j for j in d.joints if j.name == "z").overtravel = (0.0, 2.0)
    f, z = probe_findings(d)
    assert "probe_not_reached" not in f
    assert z["nozzle_above_bed_at_end_of_z_travel_mm"] == -2.0 and z["nozzle_above_bed_at_end_of_working_z_range_mm"] == 0.0
    assert z["z_overtravel_past_working_range_mm"] == 2.0


def test_generated_position_min_goes_negative_by_the_declared_overtravel(tmp_path):
    """printer_v5 homes Z on a probe; its Z range ends on the nozzle plane, so position_min was 0. With 1.9 mm of
    over-travel declared on the joint the bed can rise to 0.1 - 1.9 = 1.8 mm past the plane: position_min = -1.800."""
    from mechloop.electrical import klipper_config
    from mechloop.runner import load_design
    from mechloop.twin import firmware as fw

    d = load_design(ROOT / "designs" / "printer_v5.py")
    jz = next(j for j in d.joints if j.name == d.printer["z"])
    gap = d.tool_point[1][2] - d.get(d.printer["bed"]).shape.bounding_box().max.Z
    base = fw._cfg(klipper_config(d.electrical, d, tuning={})).getfloat("stepper_z", "position_min")
    assert base == pytest.approx(min(0.0, gap - jz.range[1]), abs=1e-3)
    jz.overtravel = (0.0, 1.9)
    cfg = klipper_config(d.electrical, d, tuning={})
    assert gap - jz.range[1] == pytest.approx(0.1, abs=1e-6)               # v5's bed stops 0.1 mm under the nozzle
    assert fw._cfg(cfg).getfloat("stepper_z", "position_min") == pytest.approx(0.1 - 1.9, abs=1e-3)


# ---------------------------------------------------------------- D. a clash must not tighten a tolerance chain
def chain_with_nut(nut_hi):
    """base -> printed tower -> printed arm -> nut (hanging under the arm's end, z 30..60). A machined rail stands on the
    base with its end face at x = 40 (z 0..40). nut_hi is the nut's high-x face: 40.7 puts it 0.7 mm inside the rail
    end (a clash of 0.7 x 8 x 10 = 56 mm^3), 39.5 leaves it 0.5 mm clear."""
    d = Design("chain", base="base")
    d.add("base", Pos(0, 0, -5) * Box(200, 60, 10), material="al6061")
    d.add("tower", Pos(-60, 0, 30) * Box(20, 20, 60), material="petg")
    d.add("arm", Pos(-5, 0, 65) * Box(130, 20, 10), material="petg")
    d.add("rail", Pos(70, 0, 20) * Box(60, 12, 40), material="steel")                      # x 40..100, z 0..40
    d.add("nut", Pos(nut_hi - 4, 0, 45) * Box(8, 8, 30), material="steel")
    for a, b in (("tower", "base"), ("arm", "tower"), ("nut", "arm"), ("rail", "base")):
        d.join(a, b, "screwed")
    return d


def nut_scatter(nut_hi, n=3000, allow=False):
    from mechloop.tolerance.stackup import Build

    d = chain_with_nut(nut_hi)
    if allow:
        d.allow_overlap("nut", "rail")
    B = Build(d, n)
    return float(B.at("nut", (nut_hi - 4, 0, 45))[:, 0].std()), B


def test_an_overlap_is_not_a_joint_of_the_stackup():
    """The nut hangs from a chain of two printed parts; the rail stands on the base beside it. Whether the nut is drawn
    0.5 mm clear of the rail or 0.7 mm inside it, its position scatters the same (the chain is the same): the two
    standard deviations agree within 2 %. Before, the overlap was taken as a seat on the rail, tied the nut to the base
    through one machined part, and the clashing model read a fraction of the scatter (it looked better)."""
    clear, B0 = nut_scatter(39.5)
    clash, B = nut_scatter(40.7)
    assert not B0.clashes and clash == pytest.approx(clear, rel=0.02)
    assert [c["parts"] for c in B.clashes] == [["nut", "rail"]] and B.clashes[0]["overlap_mm3"] == pytest.approx(56.0, abs=0.5)
    # a declared press fit (allow_overlap) IS a joint: the nut is then located by the rail as well, and scatters less
    tied, Bt = nut_scatter(40.7, allow=True)
    assert not Bt.clashes and tied < 0.8 * clash


def test_the_tolerance_verifier_names_the_clash():
    """So that a `--only tolerance` run shows it: one warning, with the pair and the 56 mm^3."""
    from mechloop.tolerance import verify_tolerance

    r = verify_tolerance(chain_with_nut(40.7), n=300)
    f = next(x for x in r.findings if x.code == "clash_in_stackup")
    assert f.severity == "warning" and r.metrics["clashes_not_used_as_joints"][0]["overlap_mm3"] == pytest.approx(56.0, abs=0.5)
    assert "clash_in_stackup" not in codes(verify_tolerance(chain_with_nut(39.5), n=300))


# ---------------------------------------------------------------- H. determinism and sampling error
def _stat_for_subprocess():
    s, _ = nut_scatter(39.5, n=500)
    print(repr(s))


def test_identical_runs_give_identical_numbers_whatever_the_hash_seed():
    """The same build in two fresh interpreters with different string-hash seeds (which reorder Python sets): the
    scatter is identical to the last digit. Before, the per-part size errors were drawn in set order."""
    out = []
    for seed in ("1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        p = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); import test_known_answers_v6 as t; "
                            "t._stat_for_subprocess()"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
        assert p.returncode == 0, p.stderr[-2000:]
        out.append(p.stdout.strip().splitlines()[-1])
    assert len(set(out)) == 1, out


def test_sampling_error_is_reported_and_a_result_at_its_limit_is_flagged():
    """Standard error of a share p over n builds: sqrt(p (1 - p) / n). 0.90 over 3000: 0.0055. 95.5 % against a 95 %
    limit is within two standard errors (2 x 0.0038 = 0.0076) and is flagged; 99 % is not."""
    from mechloop.tolerance import verify_tolerance
    from mechloop.tolerance.stackup import near_limit, std_error

    assert std_error(0.90, 3000) == pytest.approx(0.005477, abs=1e-6)
    assert near_limit(0.955, 3000, 0.95) and not near_limit(0.99, 3000, 0.95) and not near_limit(0.90, 3000, 0.95)
    m = verify_tolerance(two_rails(), n=400).metrics
    assert m["seed"] == 0 and m["builds_simulated"] == 400 and "fixed seed" in m["monte_carlo"]
    assert verify_tolerance(two_rails(), n=400).metrics["paired_rails"] == m["paired_rails"]


# ---------------------------------------------------------------- E. the print area is what the design says it is
@pytest.mark.parametrize("area, x_low, code", [
    (None, 18.0, "bed_mesh_does_not_cover_print_area"),     # undeclared: all the travel over the plate counts
    ((180, 180), 8.0, "bed_mesh_does_not_cover_print_area"),  # declared: only what the probe misses of the 180 mm
    ((160, 160), 0.0, None)])
def test_mesh_coverage_is_judged_on_the_declared_print_area(area, x_low, code):
    """Probe 30 mm to the +X side of the nozzle, kept 18 mm inside a 200 mm plate; X travel 210 mm, of which the low
    30 mm were added so the probe can reach. Machine X: plate 20..220, probe reach from 38. Undeclared, the print area
    is the travel over the plate, 20..210, and 18 mm are unprobed. Declared 180 mm, centred on the plate: 30..210,
    8 mm unprobed (the plate's edge margin); declared 160 mm: 40..200, none."""
    sys.path.insert(0, str(Path(__file__).parent))
    from test_subsystems import probe_findings, probe_rig

    d = probe_rig(face_above_nozzle=1.5, z_top=-0.5)
    next(j for j in d.joints if j.name == "x").range = (-120, 90)
    if area:
        d.printer["print_area"] = area
    f, z = probe_findings(d)
    assert z["unprobed_strip_mm"]["x_low"] == x_low
    assert ("bed_mesh_does_not_cover_print_area" in f) == (code is not None)
    assert z["print_area_basis"].startswith("declared") == (area is not None)


def test_a_declared_print_area_the_nozzle_cannot_reach_is_an_error():
    """Travel 0..180 over a plate at -10..190: a declared 200 mm print area is 10 mm out of reach at each end."""
    sys.path.insert(0, str(Path(__file__).parent))
    from test_subsystems import probe_findings, probe_rig

    d = probe_rig(face_above_nozzle=1.5, z_top=-0.5)
    d.printer["print_area"] = (200, 200)
    f, z = probe_findings(d)
    assert z["print_area_outside_nozzle_reach_mm"] == {"x_low": 10.0, "x_high": 10.0, "y_low": 10.0, "y_high": 10.0}
    assert "print_area_not_reachable" in errs(verify_subsystems(d))


# ---------------------------------------------------------------- F. cable clamp distance
def clamp_rig(point, detail_step=0.0):
    d = Design("clamp")
    d.add("rail", Box(300, 10, 10))
    blk = d.add("block", Pos(0, 0, 20) * Box(100, 100, 10), body="car")                    # top face at z = 25
    if detail_step:
        blk.detail = Pos(0, 0, 20 + detail_step / 2) * Box(100, 100, 10 + detail_step)    # the real part is that much taller
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-10, 10), max_effort=10))
    d.cables.append(Cable("loom", ("car", point), ("world", (0, 0, 5)), length=200.0))
    return d


def test_clamp_distance_is_to_the_surface_and_3_mm_is_within_3_mm():
    """A clamp over the middle of a 100 x 100 mm face, 50 mm from every edge and vertex. Exactly 3.0 mm off: allowed
    (the limit is 3 mm; before, 3.0000001 > 3.0 failed with the message 'is 3 mm from any part'). 3.5 mm off: an error
    that says 3.5. Inside the part: 0. On a catalogue part the real surface is its CAD model: a clamp 3 mm off a face
    that the CAD has 2 mm proud of the simulation solid is 3 mm from the part, not 5."""
    from mechloop.verifiers.subsystems import clamp_distance

    assert clamp_distance(clamp_rig((0, 0, 28.0)), "car", (0, 0, 28.0))[0] == pytest.approx(3.0, abs=1e-9)
    assert "cable_clamp_in_air" not in errs(verify_subsystems(clamp_rig((0, 0, 28.0))))
    assert "cable_clamp_in_air" not in errs(verify_subsystems(clamp_rig((0, 0, 28.0 + 5e-8))))
    r = verify_subsystems(clamp_rig((0, 0, 28.5)))
    f = next(x for x in r.findings if x.code == "cable_clamp_in_air")
    assert "3.5 mm from the nearest surface (block)" in f.message and f.data["distance_mm"] == 3.5
    assert clamp_distance(clamp_rig((0, 0, 22.0)), "car", (0, 0, 22.0))[0] == 0.0
    d = clamp_rig((0, 0, 30.0), detail_step=2.0)
    assert clamp_distance(d, "car", (0, 0, 30.0))[0] == pytest.approx(3.0, abs=1e-9)
    assert "cable_clamp_in_air" not in errs(verify_subsystems(d))
    assert "cable_clamp_in_air" in errs(verify_subsystems(clamp_rig((0, 0, 30.0))))


# ---------------------------------------------------------------- G. sub-assemblies in the assemblability verifier
def module_behind_a_wall(declare: bool):
    """A bracket with a cover screwed on from the +X side, standing 5 mm from a wall of the frame itself: in place a
    driver cannot reach the cover screw; on the bench it can."""
    d = Design("mod", base="frame")
    d.add("frame", Pos(0, 0, 0) * Box(120, 100, 10) + Pos(47, 0, 35) * Box(10, 100, 60))   # the wall: x 42..52
    d.add("bracket", Pos(25, 0, 15) * Box(20, 20, 20))                                     # x 15..35
    cover = Pos(36, 0, 15) * Box(2, 20, 20)
    cover -= Pos(36, 0, 15) * Rot(0, 90, 0) * Cylinder(1.7, 2)
    d.add("cover", cover)
    add_screw(d, "cover_screw", "M3", 8, at=(37, 0, 15), direction=(-1, 0, 0), threads_into="bracket", clamps=("cover",))
    d.join("bracket", "frame", "bond")
    if declare:
        d.subassemblies["module"] = ["bracket", "cover", "cover_screw"]
    return d


def test_assemblability_honours_declared_subassemblies():
    """Without the declaration the screw's driver is blocked by the frame's wall. Declared as a bench sub-assembly the module
    is built on its own (driver free) and lowered in as one unit: complete, three parts in the module."""
    from mechloop.verifiers.assemblability import verify_assemblability

    r = verify_assemblability(module_behind_a_wall(False))
    f = [x for x in r.findings if x.code == "tool_access_blocked"]
    assert len(f) == 1 and f[0].data["blockers"] == ["frame"] and r.metrics["not_placed"]
    r = verify_assemblability(module_behind_a_wall(True))
    assert not errs(r) and r.metrics["complete"] and r.metrics["not_placed"] == []
    assert r.metrics["subassemblies"]["module"]["parts"] == 3 and "module" in r.metrics["assembly_sequence"]
    assert r.metrics["parts_placed"] == r.metrics["parts_total"] == 4


def test_an_incomplete_assembly_simulation_says_what_was_not_placed_and_why():
    """A cube closed inside a shell, both in one bench sub-assembly. The main assembly is complete (the module goes on
    in one piece); the module is not. Before: complete false, trapped []."""
    from mechloop.assembly.simulate import analyse
    from mechloop.verifiers.assemblability import verify_assemblability

    d = Design("trap", base="frame")
    d.add("frame", Box(100, 100, 10))
    d.add("shell", Pos(0, 0, 20) * (Box(30, 30, 30) - Box(20, 20, 20)))
    d.add("cube", Pos(0, 0, 15) * Box(10, 10, 10))                                         # resting on the cavity floor
    d.subassemblies["module"] = ["shell", "cube"]
    m = analyse(d, reorient=False)["metrics"]
    assert m["complete"] is False and m["trapped"] == ["module/cube"]
    (np_,) = m["not_placed"]
    assert np_["unit"] == "cube" and np_["in"] == "module" and np_["reason"] == "blocked"
    assert set(np_["blocked_by"]) == {"+X", "-X", "+Y", "-Y", "+Z", "-Z"} and all(v == ["shell"] for v in np_["blocked_by"].values())
    r = verify_assemblability(d)
    f = next(x for x in r.findings if x.code == "trapped_part")
    assert f.data["subassembly"] == "module" and "shell" in f.message and not r.metrics["complete"]
