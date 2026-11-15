"""Known-answer tests for the "will it fit and work when it is really made" checks added for printer_v8:
A clearance under tolerance and functional windows, B bent sheet parts, C bed support measures, D shaft / bore
discovery; and for the checker false alarms the reference machine (Rat Rig V-Minion) exposed. Each design is small and
its right answer is known by construction or by hand; the bad case must fail and the good case must pass."""
import math

import numpy as np
import pytest
from build123d import Align, Axis, Box, Cylinder, Location, Pos

from mechloop.model import Adjustment, Design, Joint
from mechloop.parts import (add_screw, clearance_hole, endstop_switch, gt2_idler, gt2_pulley, leadscrew_nut_t8, leadscrew_t8,
                            mgn12_rail, mgn12h_carriage, nema17, place)
from mechloop.report import VerifierResult
from mechloop.tolerance import verify_tolerance
from mechloop.tolerance.bends import BEND_TOLERANCE, PartBends, find_bends
from mechloop.tolerance.clearance import MIN_CLEARANCE_MM, P_CLOSE_ERROR, clearance_check, share_closed, severity_of
from mechloop.tolerance.fits import bores_and_shafts, screw_patterns
from mechloop.tolerance.stackup import Build, std_error
from mechloop.verifiers.bed_support import (G, HAND_LOAD_N, NUT_AXIAL_K_ASSUMED, bed_support, layout, respond, support_model)
from mechloop.verifiers.interference import verify_interference
from mechloop.verifiers.subsystems import verify_subsystems


def codes(r, sev=None):
    return [f.code for f in r.findings if sev is None or f.severity == sev]


def find(r, code):
    return [f for f in r.findings if f.code == code]


# ===================================================================== A. clearance under tolerance
def two_posts(gap, join=False, material="petg"):
    """Two printed posts standing on one machined base, `gap` apart. Each is located on the base by its own seat, so the
    gap between them scatters by both seats and both parts' own accuracy: about 0.25 mm (one standard deviation)."""
    d = Design("posts", base="base")
    d.add("base", Box(120, 40, 10), material="al6061")
    d.add("post_a", Pos(-10 - gap / 2, 0, 20) * Box(20, 40, 30), material=material)
    d.add("post_b", Pos(10 + gap / 2, 0, 20) * Box(20, 40, 30), material=material)
    if join:
        d.join("post_a", "post_b", "bond")
    return d


def clearances(d, n=3000):
    r = VerifierResult("tolerance")
    return clearance_check(d, Build(d, n), r), r


def test_a_hair_thin_gap_closes_under_tolerance_and_a_wide_one_does_not():
    """0.1 mm between two printed posts against a relative scatter of about 0.25 mm: the gap closes in roughly a third of
    builds, far above the 1 % limit: error, with the share and its standard error. 1.4 mm (over five standard
    deviations): no finding. Before: the interference verifier passed both alike."""
    m, r = clearances(two_posts(0.1))
    f = find(r, "clearance_closes_under_tolerance")
    assert len(f) == 1 and f[0].severity == "error" and set(f[0].data["parts"]) == {"post_a", "post_b"}
    p = f[0].data["p_closed"]
    assert 0.2 < p < 0.5 and f[0].data["limit"] == P_CLOSE_ERROR == 0.01
    assert f[0].data["p_closed_standard_error"] == pytest.approx(std_error(p, 3000), abs=1e-4)
    assert 0.15 < f[0].data["gap_sd_mm"] < 0.4 and f[0].data["processes"] == ["printed", "printed"]
    m, r = clearances(two_posts(1.4))
    assert codes(r) == [] and m["pairs_examined"] == 1 and m["pairs"][0]["p_closed"] == 0.0


def test_a_gap_that_closes_rarely_is_a_warning_with_its_share():
    """Known distribution: a 0.3 mm gap with a relative error of exactly 0.1 mm (one standard deviation) closes in
    Phi(-3) = 0.13 % of builds: non-zero, under 1 %: a warning. At 0.5 sd it is Phi(-0.6) = 27 %: an error. At 0.03 sd
    (ten standard deviations) nothing."""
    rng = np.random.default_rng(1)
    sh = share_closed(0.3, rng.normal(0, 0.1, 200000))
    assert sh["p_closed"] == pytest.approx(0.00135, abs=0.0004) and severity_of(sh) == "warning"
    assert sh["p_closed_normal_estimate"] == pytest.approx(0.00135, rel=0.1)
    assert severity_of(share_closed(0.3, rng.normal(0, 0.5, 20000))) == "error"
    assert severity_of(share_closed(0.3, rng.normal(0, 0.03, 20000))) is None
    # none seen in few builds, but the spread says more than one in that many: still a warning, said as an estimate
    few = share_closed(0.3, np.linspace(-0.2, 0.2, 400))
    assert few["p_closed"] == 0.0 and severity_of(few) == "warning"


def test_designed_contacts_are_not_reported():
    """Guard against false alarms: parts that touch (a seat), a declared join, a screw in its clearance hole and in its
    thread, a guide block on its rail. None is a clearance."""
    assert codes(clearances(two_posts(0.0))[1]) == []                       # touching: a seat
    assert codes(clearances(two_posts(0.1, join=True))[1]) == []            # declared contact
    d = Design("screwed", base="block")                                      # screws through 3.4 mm holes: 0.2 mm all round
    d.add("block", Box(80, 80, 20), material="al6061")
    plate = Pos(0, 0, 12.5) * Box(80, 80, 5)
    for x, y in ((-30, -30), (30, 30)):
        plate -= Pos(x, y, 12.5) * Cylinder(1.7, 5)
    d.add("plate", plate, material="al6061")
    for i, (x, y) in enumerate(((-30, -30), (30, 30))):
        add_screw(d, f"s{i}", "M3", 12, at=(x, y, 15), threads_into="block", clamps=("plate",))
    m, r = clearances(d)
    assert codes(r) == [] and m["search"]["designed_contacts_skipped"].get("a screw and a part of its stack", 0) >= 2
    d = Design("guide", base="beam")                                         # block on rail: 0.2 mm beside the rail by catalogue
    d.add("beam", Pos(0, 0, -10) * Box(200, 20, 20), material="al6061")
    place(d, "rail", mgn12_rail(150), Location((0, 0, 0)))
    place(d, "block", mgn12h_carriage(), Location((0, 0, 0)), body="car", guides="x")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-40, 40)))
    m, r = clearances(d)
    assert codes(r) == [] and m["search"]["designed_contacts_skipped"].get("a guide and what it runs on") == 1


def slider(stop_gap, travel=100.0):
    """A carriage sliding on a base towards a printed stop post: at the END of its travel its face is `stop_gap` from
    the post; at home it is `travel` further away."""
    d = Design("slider", base="base")
    d.add("base", Box(300, 40, 10), material="al6061")
    d.add("car", Pos(-100, 0, 15) * Box(40, 40, 20), material="al6061", body="car")
    d.add("stop", Pos(-80 + travel + stop_gap + 10, 0, 20) * Box(20, 40, 30), material="petg")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(0, travel)))
    return d


def test_a_moving_pair_is_judged_at_its_closest_approach_in_the_travel():
    """At home the carriage is 100.2 mm from the stop; at the end of its travel 0.2 mm. The pair must be found, at
    x = 100, and fail. With the stop 5 mm beyond the end of travel there is nothing to report."""
    m, r = clearances(slider(0.2))
    f = find(r, "clearance_closes_under_tolerance")
    assert len(f) == 1 and f[0].severity == "error" and set(f[0].data["parts"]) == {"car", "stop"}
    assert f[0].data["closest_at_pose"] == {"x": pytest.approx(100.0, abs=0.01)} and f[0].data["gap_mm"] == pytest.approx(0.2, abs=1e-3)
    assert f[0].data["across_joints"] == ["x"]
    assert codes(clearances(slider(5.0))[1]) == []


def test_design_rule_minimum_clearance_by_process():
    """A drawn gap below the minimum for the processes is a warning whatever the simulation says: printed 0.5, machined
    0.2. Two machined posts 0.3 mm apart are above their 0.2; two printed ones are below their 0.5. A declared figure
    (design.manufacturing['min_clearance_mm']) replaces the default."""
    assert MIN_CLEARANCE_MM["printed"] == 0.5 and MIN_CLEARANCE_MM["sheet"] == 0.3 and MIN_CLEARANCE_MM["machined"] == 0.2
    f = find(clearances(two_posts(0.3))[1], "clearance_below_minimum")
    assert len(f) == 1 and f[0].severity == "warning" and f[0].data["minimum_mm"] == 0.5 and f[0].data["gap_mm"] == pytest.approx(0.3)
    assert find(clearances(two_posts(0.3, material="al6061"))[1], "clearance_below_minimum") == []
    d = two_posts(0.3, material="al6061")
    d.manufacturing = {"min_clearance_mm": 0.4}
    assert find(clearances(d)[1], "clearance_below_minimum")[0].data["minimum_mm"] == 0.4
    assert find(clearances(two_posts(0.8))[1], "clearance_below_minimum") == []


def test_a_part_outside_the_stackup_is_reported_not_passed():
    """A part that nothing ties to the base cannot be simulated. A gap to it is reported as not evaluated."""
    d = two_posts(0.1)
    d.add("loose", Pos(0, 40.3, 20) * Box(20, 40, 30), material="petg", body="other")     # 0.3 mm beside base and posts, on its own body
    d.joints.append(Joint("j", "slide", "world", "other", (0, 0, 1), range=(0, 0)))
    m, r = clearances(d)
    assert "clearance_not_evaluated" in codes(r, "warning") and len(m["not_evaluated"]) == 3


def lever_axis(face_y, with_adjustment=False):
    """tests/test_known_answers_v6.lever_axis with the carriage riding ON the frame, so that switch and striker are both
    in the stack-up: frame (machined) - switch on one side, frame - carriage - printed striker on the other."""
    d = Design("es", base="frame")
    d.add("frame", Pos(0, -20, -5) * Box(120, 120, 10))
    place(d, "sw", endstop_switch(), Location((0, 0, 0)))
    d.join("sw", "frame", "screwed")
    d.add("car", Pos(40, 40, 5) * Box(10, 10, 10), body="car")
    d.add("arm", Pos(15, 40, 12.5) * Box(60, 10, 5), body="car", material="petg")
    d.add("striker", Pos(-9, face_y + 20 + 5, 6.0) * Box(6, 10, 8), body="car", material="petg")     # low face at face_y when y = -20
    d.join("arm", "car", "bond")
    d.join("striker", "arm", "bond")
    d.joints.append(Joint("y", "slide", "world", "car", (0, 1, 0), range=(-20, 20), max_effort=10))
    d.endstops.append({"joint": "y", "switch": "sw", "at": "min"})
    if with_adjustment:
        d.adjustments.append(Adjustment("switch on a slot, set against the striker", "endstop", range_mm=5.0, joint="y"))
    return d


def test_endstop_window_is_judged_with_the_stackup_not_on_the_drawing():
    """Drawn in the middle of the 0.25 mm window between the switch's latest operating position (Y 6.9) and its case
    (6.65), the design passed. Striker and switch sit at the ends of a chain of a machined frame, a carriage and two
    printed parts: their relative error is several times the window, so most builds end outside it: error, with the two
    shares (never switches / lever on the case). A switch set at assembly on a slot (declared) takes the error out."""
    r = verify_subsystems(lever_axis(6.78))
    f = find(r, "endstop_window_under_tolerance")
    assert len(f) == 1 and f[0].severity == "error"
    w = r.metrics["homing"]["y"]["window_under_tolerance"]
    assert w["evaluated"] and w["striker"] == "striker" and w["window_mm"] == [-0.1, 0.23]
    assert w["drawn_position_in_window_mm"] == pytest.approx(0.12, abs=0.01) and w["relative_error_sd_mm"] > 0.15
    assert w["p_outside_window"] > 0.3 and w["p_late_unit_never_switches"] > 0.05 and w["p_lever_on_case"] > 0.05
    assert w["p_outside_window"] == pytest.approx(w["p_late_unit_never_switches"] + w["p_lever_on_case"], abs=1e-3)
    r = verify_subsystems(lever_axis(6.78, with_adjustment=True))
    assert find(r, "endstop_window_under_tolerance") == [] and codes(r, "error") == []
    w = r.metrics["homing"]["y"]["window_under_tolerance"]
    assert w["set_at_assembly"] and w["adjustment_needed_mm_99"] <= w["adjustment_available_mm"] == 5.0


# ===================================================================== B. bent sheet parts
def bracket(t=2.0, r=2.0, leg_b=40.0):
    """An L bracket as sheet is really bent (tests/test_manufacture.bracket): a 60 mm leg lying on Z = 0..t along +X and
    a `leg_b` leg standing up at X = 0..t; inside radius r about the axis (r + t, y, r + t)."""
    s = Box(60, 40, t, align=(Align.MIN, Align.CENTER, Align.MIN)) + Box(t, 40, leg_b, align=(Align.MIN, Align.CENTER, Align.MIN))
    along = s.edges().filter_by(Axis.Y)
    inside = [e for e in along if abs(e.center().X - t) < 1e-6 and abs(e.center().Z - t) < 1e-6]
    outside = [e for e in along if abs(e.center().X) < 1e-6 and abs(e.center().Z) < 1e-6]
    return s.fillet(r, inside).fillet(r + t, outside)


def test_a_bend_is_found_and_a_point_on_the_flange_moves_by_angle_times_distance():
    """One 90 degree bend about the axis x = z = 4. Datum flange: the long leg. A point on the standing flange at height
    z moves in X by (angle error) x (z - 4) and by the bend-line error: standard deviation
    sqrt((0.5 deg in rad x (z - 4))^2 + 0.19^2): 0.30 mm at z = 30, 0.22 at z = 17. A point on the datum flange does not
    move. A flat plate has no bend."""
    f = find_bends(bracket())
    assert len(f["bends"]) == 1 and f["bends"][0]["angle_deg"] == pytest.approx(90.0) and f["thickness"] == pytest.approx(2.0, abs=0.01)
    assert np.allclose(f["bends"][0]["origin"][[0, 2]], [4.0, 4.0]) and len(f["pieces"]) == 2 and not f["not_separated"]
    assert find_bends(Box(60, 40, 2)) is None
    pb = PartBends("bracket", f, 20000, 0, BEND_TOLERANCE)
    ang = math.radians(BEND_TOLERANCE["angle_sd_deg"])
    for z in (30.0, 17.0):
        dx = pb.displacement((1.0, 0.0, z))[:, 0]
        assert dx.std() == pytest.approx(math.hypot(ang * (z - 4.0), BEND_TOLERANCE["line_sd_mm"]), rel=0.04)
    assert pb.displacement((1.0, 0.0, 30.0))[:, 0].std() > 1.3 * pb.displacement((1.0, 0.0, 17.0))[:, 0].std()
    assert np.all(pb.displacement((40.0, 0.0, 1.0)) == 0.0) and np.all(pb.rotation((40.0, 0.0, 1.0)) == 0.0)
    assert pb.rotation((1.0, 0.0, 30.0))[:, 1].std() == pytest.approx(ang, rel=0.04)


def on_bracket(process, bend_tol=None):
    """A sensor block screwed to the top of the standing flange of a bracket whose long leg lies on a machined base."""
    d = Design("bent", base="base")
    d.add("base", Pos(30, 0, -5) * Box(80, 60, 10), material="al6061")
    d.add("bracket", bracket(), material="al5052", process=process)
    d.add("sensor", Pos(-5, 0, 34) * Box(10, 20, 10), material="al6061")          # on the outside of the flange, z 29..39
    if bend_tol:
        d.manufacturing = {"bend_tolerance": bend_tol}
    return d


def test_what_is_mounted_on_a_bent_flange_moves_with_the_bend():
    """The sensor's position along X: with the bracket toleranced as a flat sheet part (bend scatter declared zero) its
    spread is the seats' only; with the press-brake class values it grows by the bend's 0.5 degree x 30 mm and 0.19 mm,
    about 0.3 mm, added in quadrature. The tolerance verifier reports the bent part and the values' provenance."""
    p = (-5.0, 0.0, 34.0)
    flat = Build(on_bracket("sheet", {"angle_deg": 0.0, "line_mm": 0.0}), 4000).at("sensor", p)[:, 0].std()
    bent = Build(on_bracket("sheet"), 4000).at("sensor", p)[:, 0].std()
    added = math.sqrt(bent ** 2 - flat ** 2)
    assert added == pytest.approx(math.hypot(math.radians(0.5) * 30.0, 0.19), rel=0.15) and bent > 1.3 * flat
    m = verify_tolerance(on_bracket("sheet"), n=500).metrics["bent_sheet_parts"]
    assert m["parts"]["bracket"]["bends"] == 1 and m["tolerance"]["status"] == "recalled" and m["tolerance"]["angle_sd_deg"] == 0.5
    assert "bent_sheet_parts" not in verify_tolerance(on_bracket("machined"), n=500).metrics


def test_a_sheet_part_that_is_not_flat_and_has_no_recognisable_bend_is_said_so():
    """Two plates meeting at a dead-sharp corner, declared sheet: no bend radius to find. Its flanges would be toleranced
    as a flat part's: a warning says so (the manufacture verifier separately calls the sharp bend an error)."""
    d = Design("sharp", base="base")
    d.add("base", Pos(30, 0, -5) * Box(80, 60, 10), material="al6061")
    d.add("bracket", Box(60, 40, 2, align=(Align.MIN, Align.CENTER, Align.MIN)) + Box(2, 40, 40, align=(Align.MIN, Align.CENTER, Align.MIN)),
          material="al5052", process="sheet")
    r = verify_tolerance(d, n=300)
    assert "sheet_bends_not_recognised" in codes(r, "warning")
    assert "sheet_bends_not_recognised" not in codes(verify_tolerance(on_bracket("sheet"), n=300))


# ===================================================================== C. bed support
def bed_machine(screws=((0.0, 120.0),), rails=((-80.0, 110.0), (80.0, 110.0)), blocks_per_rail=2, spacing=60.0, mu=None,
                sync=None, z_tilt=False, payload_at=None):
    """A 200 x 200 x 6 bed plate (top at Z = 106, centre at the origin) on body "zb", guided by MGN12 rails standing at
    `rails` (x, y) with their blocks `spacing` apart, carried by T8 lead screws at `screws` (x, y), one motor each."""
    from build123d import Plane

    d = Design("bedtest", base="frame")
    d.add("frame", Pos(0, 0, -5) * Box(300, 300, 10), material="al6061")
    d.add("bed", Pos(0, 0, 103) * Box(200, 194, 6), material="al6061", body="zb", mass_kg=2.0)     # rear edge on the blocks' faces
    if payload_at:
        d.add("payload", Pos(payload_at[0], payload_at[1], 111) * Box(10, 10, 10), material="steel", body="zb", mass_kg=3.0)
    for i, (x, y) in enumerate(rails):
        place(d, f"rail{i}", mgn12_rail(250), Location(Plane(origin=(x, y, 125), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
        for k in range(blocks_per_rail):
            zc = 90 + (k - (blocks_per_rail - 1) / 2) * spacing
            c = place(d, f"blk{i}{k}", mgn12h_carriage(), Location(Plane(origin=(x, y, zc), x_dir=(0, 0, 1), z_dir=(0, -1, 0))),
                      body="zb", guides="z")
            if mu is not None:
                c.ratings["friction_coefficient"] = mu
    motors, scr, nuts = [], [], []
    for i, (x, y) in enumerate(screws):
        place(d, f"motor{i}", nema17(40), Location((x, y, 40)))                      # stands on the frame
        place(d, f"screw{i}", leadscrew_t8(190, lead=8.0), Location((x, y, 66)))
        d.join(f"screw{i}", f"motor{i}", "coupled")
        place(d, f"nut{i}", leadscrew_nut_t8(), Location((x, y, 96)), body="zb")
        motors.append(f"motor{i}"); scr.append(f"screw{i}"); nuts.append(f"nut{i}")
    one = len(screws) == 1
    drive = {"motor": motors[0] if one else motors, "kind": "leadscrew", "screw": scr[0] if one else scr, "nut": nuts[0] if one else nuts}
    if sync:
        drive["sync"] = sync
    d.joints.append(Joint("z", "slide", "world", "zb", (0, 0, 1), range=(0, 100), max_speed=10, max_accel=100, drive=drive))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z", "print_area": (180.0, 180.0)}
    if z_tilt:
        d.printer["z_tilt"] = True
    return d


def support(d):
    r = VerifierResult("fea")
    return bed_support(d, r, with_fea=False), r


def test_a_load_on_the_screws_line_of_action_sinks_by_the_nut_stiffness_alone():
    """Load straight above the single screw: the guides carry nothing, the bed sinks by F / k with k the screw column
    (E A / L: 193 GPa, root 0.78 x 8 mm, the nut's distance from the driven end) in series with the assumed nut
    figure: 1 / (1 / 10000 + L / (193000 x 30.6)), a little under 10 N/um; 20 N -> about 0.002 mm, and no tilt."""
    d = bed_machine()
    lay = layout(d)
    model = support_model(d, lay)
    nut = next(s for s in model["supports"] if s["kind"] == "nut")
    area = math.pi * (0.78 * 8.0) ** 2 / 4
    k = 1 / (1 / NUT_AXIAL_K_ASSUMED + nut["free_length_mm"] / (193000.0 * area))
    assert nut["k_axial_n_per_um"] * 1e3 == pytest.approx(k, rel=1e-6) and 8000 < k < 9900
    res = respond(model, (0, 0, -20.0), (0.0, 120.0, 106.0))
    assert -res["at"]((0.0, 120.0, 106.0))[2] == pytest.approx(20.0 / k, rel=1e-3)
    assert np.linalg.norm(res["theta"]) < 1e-9
    assert all(np.linalg.norm(q["force"]) < 1e-6 for q in res["reactions"] if q["kind"] == "guide")


def test_cantilever_two_screw_and_three_point_beds_are_told_apart():
    """The same bed, guides and loads; only the screws differ. One screw behind the bed (cantilever): a hand load on
    the front corner tilts the bed on its guide blocks. Three screws round the bed: the load lands between supports.
    The front-corner deflection must fall from one to the other, the moment the guides carry likewise, and every
    figure must be there for 1, 2 and 3 screws."""
    out = {}
    for name, scr in (("one", ((0.0, 120.0),)), ("two", ((-120.0, 0.0), (120.0, 0.0))), ("three", ((-90.0, -90.0), (90.0, -90.0), (0.0, 120.0)))):
        m, r = support(bed_machine(screws=scr, z_tilt=True))
        assert m["evaluated"] and m["constraint"]["lead_screws"] == len(scr) and m["constraint"]["redundant_screw_supports"] == len(scr) - 1
        assert m["hand_load"]["load_n"] == HAND_LOAD_N and m["print_weight"]["load_n"] == pytest.approx(9.81)
        assert "bed_flexure_not_evaluated" in codes(r, "warning")           # FEA switched off here: said, not passed over
        out[name] = m
    h = {k: v["hand_load"]["judged_mm"] for k, v in out.items()}
    assert h["one"] > 2.0 * h["three"] and h["one"] > h["two"] > 0
    f = {k: max(x["force_n"] for n_, x in v["moving_mass_on_guides"]["reactions"].items() if n_.startswith("blk")) for k, v in out.items()}
    assert f["one"] > 5.0 * f["three"]
    g1 = out["one"]["moving_mass_on_guides"]            # 2 kg of bed 120 mm in front of the screw, blocks and nut near it
    assert 100.0 < g1["screw_line_to_mass_centre_mm"] < 120.0
    assert g1["moment_on_guides_nm"] == pytest.approx(g1["moving_mass_kg"] * G * g1["screw_line_to_mass_centre_mm"] * 1e-3, rel=1e-3)
    assert out["three"]["moving_mass_on_guides"]["screw_line_to_mass_centre_mm"] < 0.35 * g1["screw_line_to_mass_centre_mm"]
    # one screw: the nut carries the whole weight (the guides are free along the rail), whatever the offset
    assert g1["reactions"]["nut0"]["force_n"] == pytest.approx(g1["moving_mass_kg"] * G, rel=1e-3)


def test_plain_bushings_with_a_long_overhang_bind_and_rolling_blocks_do_not():
    """A heavy load 100 mm in front of the bed's edge, the screw behind it, one short block per rail. Rolling blocks
    (friction 0.005): the added friction is a few per cent of the weight. The same geometry on plain bushings with a
    friction coefficient of 0.4: friction as large as the weight, the classic drawer jam: error."""
    kw = dict(blocks_per_rail=1, payload_at=(0.0, -200.0))
    m, r = support(bed_machine(**kw))
    assert m["moving_mass_on_guides"]["friction_over_weight"] < 0.1 and "z_guides_bind" not in codes(r)
    m, r = support(bed_machine(mu=0.4, **kw))
    assert m["moving_mass_on_guides"]["friction_over_weight"] >= 1.0 and "z_guides_bind" in codes(r, "error")


def test_two_screws_out_of_step_tilt_or_load_the_guides_unless_the_firmware_can_relevel():
    """Two screws, one motor each: at power-up they can sit 2 full steps apart, 2 x 8 / 200 = 0.08 mm. Without a
    declared firmware tilt adjustment that is a warning with the tilt and the guide force it causes; with one, an info.
    One motor and a belt cannot be re-levelled by firmware, but its error is small."""
    m, r = support(bed_machine(screws=((-120.0, 0.0), (120.0, 0.0))))
    s = m["screw_synchronisation"]
    assert s["sync"] == "independent" and s["height_error_mm"] == pytest.approx(0.08) and not s["firmware_can_relevel"]
    assert "z_screws_not_levelled" in codes(r, "warning") and s["force_on_a_guide_block_n"] > 10
    m, r = support(bed_machine(screws=((-120.0, 0.0), (120.0, 0.0)), z_tilt=True))
    assert m["screw_synchronisation"]["firmware_can_relevel"] and "z_screws_not_levelled" not in codes(r) and "z_over_constrained" in codes(r, "info")
    m, r = support(bed_machine(screws=((-120.0, 0.0), (120.0, 0.0)), sync="belt"))
    assert m["screw_synchronisation"]["height_error_mm"] == 0.02 and not m["screw_synchronisation"]["firmware_can_relevel"]


def test_a_bed_that_is_not_held_or_not_declared_is_said_so_never_passed():
    """Three screws and no guides: nothing stops the bed sliding sideways or turning: a mechanism, error. A Z drive
    without a named nut: not evaluated, warning. No printer bed: nothing to do (None)."""
    m, r = support(bed_machine(screws=((-90.0, -90.0), (90.0, -90.0), (0.0, 120.0)), rails=()))
    assert not m["evaluated"] and "bed_not_held" in codes(r, "error")
    d = bed_machine()
    del d.joints[0].drive["nut"]
    m, r = support(d)
    assert not m["evaluated"] and "bed_support_not_evaluated" in codes(r, "warning")
    assert bed_support(two_posts(1.0), VerifierResult("fea")) is None


def test_several_lead_screws_are_accepted_by_ratings_and_tolerance():
    """drive={"screw": [..], "nut": [..], "motor": [..]}: the ratings verifier resolves it (two motors' torque), the
    tolerance verifier checks each screw against the rails. Before: both crashed on the list."""
    from mechloop.verifiers.ratings import verify_ratings

    d = bed_machine(screws=((-120.0, 0.0), (120.0, 0.0)))
    r = verify_ratings(d)
    assert "verifier_crashed" not in codes(r) and r.metrics["drives"]["z"]["parts"]["screw"] == ["screw0", "screw1"]
    one = verify_ratings(bed_machine()).metrics["drives"]["z"]["available_effort"]
    assert r.metrics["drives"]["z"]["available_effort"] == pytest.approx(2 * one, rel=1e-6)
    t = verify_tolerance(d, n=300)
    assert set(t.metrics["lead_screws"]) == {"z:screw0", "z:screw1"}


# ===================================================================== D. shaft / bore pairs
def test_catalogue_fits_are_listed_as_trusted_and_made_bores_are_simulated():
    """A pulley on a motor shaft (two purchased parts) was left out without a word. It is now listed as a catalogue
    fit with the tolerance the catalogue records for the shaft (5 +0 / -0.012), not simulated. A printed hub drawn at
    5.00 on the same shaft IS simulated and fails as before. An idler on its M5 bolt is found through the axle join."""
    d = Design("fits", base="motor")
    place(d, "motor", nema17(48), Location((0, 0, 0)))
    place(d, "pulley", gt2_pulley(20, 5.0), Location((0, 0, 3.0)))
    d.join("pulley", "motor", "set_screw")
    r = VerifierResult("t")
    out = bores_and_shafts(d, r)
    e = out["motor in pulley (dia 5.00)"]
    assert e["class"] == "catalogue fit, trusted" and e["p_bad"] is None and e["held_by"] == "set_screw"
    assert e["catalogue_tolerances_mm"] == {"motor": [-0.012, 0.0]}
    assert codes(r) == ["catalogue_fits_trusted"] and find(r, "catalogue_fits_trusted")[0].severity == "info"
    d = Design("fits2", base="motor")
    place(d, "motor", nema17(48), Location((0, 0, 0)))
    d.add("hub", Pos(0, 0, 10) * (Cylinder(10, 10) - Cylinder(2.5, 10)), material="petg")
    r = VerifierResult("t")
    out = bores_and_shafts(d, r)
    assert out["motor in hub (dia 5.00)"]["class"] == "simulated" and out["motor in hub (dia 5.00)"]["p_bad"] > 0.9
    assert "fit_not_toleranced" in codes(r, "error")
    d = Design("fits3", base="plate")
    d.add("plate", Pos(0, 0, -2.5) * (Box(40, 40, 5) - Cylinder(clearance_hole("M5") / 2, 5)), material="al6061")
    place(d, "idler", gt2_idler(20, 5.0), Location((0, 0, 0)))
    add_screw(d, "bolt", "M5", 25, at=(0, 0, 13.5), clamps=("plate",))
    d.join("idler", "bolt", "axle")
    r = VerifierResult("t")
    out = bores_and_shafts(d, r)
    assert out["bolt in idler (dia 5.00)"]["class"] == "catalogue fit, trusted"
    assert not any("plate" in k for k in out)            # the bolt in the plate's clearance hole is a screw pattern, not a fit


def test_two_catalogue_parts_that_do_not_fit_are_an_error():
    """A 5 mm motor shaft drawn in a 4.9 mm pulley bore: not a fit the makers hold, a wrong part."""
    d = Design("misfit", base="motor")
    place(d, "motor", nema17(48), Location((0, 0, 0)))
    place(d, "pulley", gt2_pulley(20, 4.9), Location((0, 0, 3.0)))
    r = VerifierResult("t")
    bores_and_shafts(d, r)
    assert "catalogue_fit_mismatch" in codes(r, "error")


# ===================================================================== reference-machine false alarms
def nema_mount(dia, pattern=31.0):
    d = Design("mount", base="mount")
    m = place(d, "motor", nema17(40), Location((0, 0, 0)))
    plate = Pos(0, 0, 3) * Box(50, 50, 6) - Pos(0, 0, 3) * Cylinder(11.5, 6)
    holes = m.meta["interfaces"]["mount_holes_m3"]
    for hx, hy, hz in holes:
        plate -= Pos(hx, hy, 3) * Cylinder(dia / 2, 6)
    d.add("mount", plate, material="petg", process="printed")
    for i, (hx, hy, hz) in enumerate(holes):
        add_screw(d, f"s{i}", "M3", 10, at=(hx, hy, 6), threads_into="motor", clamps=("mount",))
    return d


def test_printed_motor_mounts_with_real_kit_hole_sizes_start_and_holes_at_screw_size_do_not():
    """Rat Rig's printed motor cages have four 3.3 mm holes on the NEMA 17's 31 mm square and are built by the
    thousand; the model said 9 % would start (30 % at 3.4 mm), because each hole had its own 0.12 mm position error and
    a screw needed geometric clearance. Hole to hole within a pattern is the process's 'pattern' figure (0.05 mm
    printed) and a screw cuts through up to 0.15 mm of plastic: both sizes now start in over 99 %, and the share that
    start FREELY is still reported. Holes drawn at the screw's own 3.0 mm (2.85 printed) still fail."""
    for dia in (3.3, 3.4):
        r = VerifierResult("t")
        v = screw_patterns(nema_mount(dia), r)["mount -> motor"]
        assert v["p_all_start"] >= 0.99 and "screws_may_not_align" not in codes(r)
        assert v["plastic_hole_yield_mm"] == 0.15 and v["p_all_start_freely"] <= v["p_all_start"]
    r = VerifierResult("t")
    assert screw_patterns(nema_mount(3.3), r)["mount -> motor"]["p_all_start_freely"] < 0.9 and "screws_cut_into_printed_holes" in codes(r, "info")
    r = VerifierResult("t")
    assert screw_patterns(nema_mount(3.0), r)["mount -> motor"]["p_all_start"] < 0.9 and "screws_may_not_align" in codes(r, "error")


def psu_on_panel(length):
    from mechloop.parts.electrical import psu_lrs

    d = Design("psu", base="panel")
    p = place(d, "psu", psu_lrs("LRS-350-24"), Location((0, 0, 0)))
    panel = Pos(0, 0, -2) * Box(230, 130, 4)
    for hx, hy, hz in p.meta["interfaces"]["mount_holes_m4"]:
        panel -= Pos(hx, hy, -2) * Cylinder(clearance_hole("M4") / 2, 4)
    d.add("panel", panel, material="al6061", process="sheet")
    for i, (hx, hy, hz) in enumerate(p.meta["interfaces"]["mount_holes_m4"]):
        add_screw(d, f"s{i}", "M4", length, at=(hx, hy, -4), direction=(0, 0, 1), threads_into="psu", clamps=("panel",))
    return d


def test_a_vendors_maximum_screw_depth_can_be_met_by_a_standard_screw():
    """Mean Well: "4-M4 L=3mm", at most 3 mm of screw inside. Through a 4 mm panel M4 x 6 gives 2.0 mm and M4 x 8 would
    give 4.0. The check demanded 2.7 to 3.0 mm, which no standard length meets. Now the longest standard screw that
    stays inside is accepted (2.0 mm, half a diameter or more); M4 x 8 still bottoms out; M4 x 5 (1.0 mm, a shorter
    screw than the one that fits) is still too little thread."""
    assert codes(verify_interference(psu_on_panel(6)), "error") == []
    assert set(codes(verify_interference(psu_on_panel(8)), "error")) == {"thread_bottoms_out"}
    assert set(codes(verify_interference(psu_on_panel(5)), "error")) == {"thread_engagement"}


def test_a_declared_free_standing_unit_may_stand_apart_and_an_undeclared_one_may_not():
    """An electronics box on the bench beside the machine, joined only by cables. Undeclared it is floating, as before.
    Declared (design.free_standing) it is accepted; a declared unit whose own parts are not held together is not."""
    def two_units(declare=None, lid_gap=0.0):
        d = Design("bench", base="frame")
        d.add("frame", Box(100, 100, 20), material="al6061")
        d.add("foot", Pos(0, 0, -15) * Box(100, 100, 10), material="al6061")
        d.join("frame", "foot", "bond")
        d.add("box", Pos(200, 0, 0) * Box(60, 60, 20), material="al6061")
        d.add("lid", Pos(200, 0, 12.5 + lid_gap) * Box(60, 60, 5), material="al6061")
        if not lid_gap:
            d.join("box", "lid", "bond")
        if declare:
            d.free_standing = {"electronics box": declare}
        return d

    assert {"floating_parts", "unfastened"} <= set(codes(verify_interference(two_units()), "error"))
    assert codes(verify_interference(two_units(["box", "lid"])), "error") == []
    r = verify_interference(two_units(["box", "lid"], lid_gap=5.0))          # the lid hovers over the box
    assert "floating_parts" in codes(r, "error")
    assert "unknown_part_reference" in codes(verify_interference(two_units(["box", "lid", "nothing"])), "error")


def column_printer(z_axis=(0, 0, -1), z_range=(0.0, 100.0), nozzle_above=100.1, bed_rides_too=False):
    """A fixed bed and a toolhead that comes down a column: the nozzle rides Z (the V-Minion's arrangement)."""
    d = Design("column", base="base")
    d.add("base", Pos(0, 0, -5) * Box(200, 200, 10), material="al6061")
    d.add("bed", Pos(0, 0, 3) * Box(120, 120, 6), material="al6061", body="zb" if bed_rides_too else "world")
    d.add("post", Pos(0, 90, 100) * Box(20, 20, 200), material="al6061")
    d.add("zcar", Pos(0, 70, 6 + nozzle_above + 20) * Box(40, 20, 40), material="al6061", body="zb")
    d.add("head", Pos(0, 30, 6 + nozzle_above + 10) * Box(20, 60, 20), material="al6061", body="xb")
    d.joints.append(Joint("z", "slide", "world", "zb", z_axis, range=z_range))
    d.joints.append(Joint("x", "slide", "zb", "xb", (1, 0, 0), range=(-40, 40)))
    d.joints.append(Joint("y", "slide", "xb", "yb", (0, 1, 0), range=(-40, 40)))
    d.add("tip", Pos(0, 0, 6 + nozzle_above + 2.5) * Box(6, 6, 5), material="brass", body="yb")
    d.join("tip", "head", "bond")
    d.tool_point = ("yb", (0.0, 0.0, 6 + nozzle_above))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z"}
    return d


def test_the_nozzle_to_bed_gap_is_right_whichever_of_the_two_rides_z():
    """Nozzle drawn 100.1 mm above a fixed bed, Z joint (0, 0, -1) with 100 mm of travel: at the end the gap is 0.1 mm.
    The tolerance verifier assumed the bed rides Z and reported the home-pose distance plus the travel. A joint on which
    both, or neither, ride is refused with a clear error. The firmware's Z sense is worked out the same way."""
    from mechloop.electrical import z_sense

    d = column_printer()
    pm = verify_tolerance(d, n=300).metrics["printer"]
    assert pm["z_arrangement"] == "the nozzle rides Z" and pm["nominal_gap_mm"] == pytest.approx(0.1, abs=1e-6)
    assert pm["nozzle_meets_bed_at"] == {"z": 100.0}
    assert z_sense(d, d.joints[0]) == {"rides": "nozzle", "closes_with_joint": 1, "error": None}
    up = column_printer(z_axis=(0, 0, 1), z_range=(-100.0, 0.0))             # the same machine drawn with Z rising from the bed
    assert z_sense(up, up.joints[0])["closes_with_joint"] == -1
    assert verify_tolerance(up, n=300).metrics["printer"]["nominal_gap_mm"] == pytest.approx(0.1, abs=1e-6)
    both = column_printer(bed_rides_too=True)
    r = verify_tolerance(both, n=300)
    assert "printer_z_arrangement" in codes(r, "error") and "printer" not in r.metrics
    assert "both the bed and the nozzle ride" in z_sense(both, both.joints[0])["error"]


def test_bed_flexure_is_solved_on_the_real_supports_and_adds_to_the_support_compliance():
    """The 200 x 194 x 6 aluminium plate held only along its rear edge by the four guide blocks, 10 N on a front corner
    of the print area (about 185 mm out). A cantilever of the full width would sink F L^3 / (3 E I) = 10 x 185^3 /
    (3 x 68900 x 3600) = 0.085 mm under a central load; held at two places and loaded on a corner it must sink more, but
    not ten times more. No nut seat among the parts: the supports are reported as the ideal ones. The total is the
    flexure plus the support model's figure."""
    d = bed_machine()
    d.printer["bed_support"] = {"parts": ["bed", "blk00", "blk01", "blk10", "blk11"]}
    r = VerifierResult("fea")
    m = bed_support(d, r)
    fx = m["flexure"]
    assert fx["evaluated"] and fx["supports"].startswith("IDEAL") and fx["parts_from"].startswith("design.printer")
    assert 0.0085 < fx["bonded_mm_per_n"] < 0.085
    pw = m["print_weight"]
    assert pw["total_bonded_mm"] == pytest.approx(pw["flexure_bonded_mm"] + pw["support_compliance_mm"], abs=2e-4)
    assert pw["judged_mm"] > 0.02 and "bed_sags_under_print_weight" in codes(r, "warning")
    assert "bed_flexure_not_evaluated" not in codes(r)


def test_a_face_the_cad_kernel_cannot_mesh_does_not_lose_the_part():
    """The face-by-face mesher used when the kernel returns no triangulation for a face: on a sound solid it gives the
    same closed surface (a 10 x 20 x 30 box: 6000 mm^3) and reports no face left out."""
    import trimesh

    from mechloop.geom import _tessellate_face_by_face

    v, f, skipped = _tessellate_face_by_face(Box(10, 20, 30), 0.05, 0.3)
    assert skipped == 0 and abs(trimesh.Trimesh(v, f, process=True).volume) == pytest.approx(6000.0, rel=1e-6)


def test_a_verify_does_not_read_an_earlier_runs_report():
    """The electrical verifier took the frame stiffness for its input-shaper prediction from the previous run's
    report.json, so the same design gave different metrics on a first and a second run. It no longer looks."""
    import inspect

    from mechloop.verifiers import electrical as EV

    src = inspect.getsource(EV)
    assert "pm_for(" not in src and "report.json" not in src.replace("an earlier run's report.json", "")
