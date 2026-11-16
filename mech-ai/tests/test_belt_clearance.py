"""Belt clearance (BLT-060 / BLT-061, warnings in mechloop/verifiers/belts.py): a straight run near a part it slides past,
a pulley near a made plate. Small purpose-built belt axis (the one test_checks2 uses)."""
import math

from build123d import Box, Location, Pos

from mechloop.model import Belt, Design, Joint
from mechloop.parts import gt2_idler, gt2_pulley, place
from mechloop.verifiers.belts import PULLEY_PLATE_CLEARANCE_MM, RUN_CLEARANCE_MM, clearance_limits
from mechloop.verifiers.motion import verify_motion

R_P = 20 * 2 / math.pi / 2          # 20-tooth GT2 pitch radius, 6.37 mm


def belt_axis():
    """Drive pulley at x = -150, idler at x = +150, both on the world; the belt's two ends on a carriage 'car'. The upper
    (return) run lies along y = +R_P, the lower along y = -R_P, belt 6 mm wide centred on z = 11."""
    d = Design("beltaxis")
    place(d, "drive", gt2_pulley(20), Location((-150, 0, 0)))
    place(d, "idler", gt2_idler(20), Location((150, 0, 6.25)))
    d.add("clamp", Pos(0, -10.1, 11) * Box(20, 6, 10), body="car")
    z = d.get("drive").meta["interfaces"]["belt_center"][0][2]
    d.belts.append(Belt("x_belt", [("anchor", "car", (10, -R_P, z)), ("pulley", "idler", "ccw"),
                                   ("pulley", "drive", "ccw"), ("anchor", "car", (-10, -R_P, z))]))
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-100, 100), max_effort=50))
    return d


def warns(r, code):
    return [f for f in r.findings if f.code == code]


def test_defaults_and_override():
    d = belt_axis()
    assert clearance_limits(d) == (RUN_CLEARANCE_MM, PULLEY_PLATE_CLEARANCE_MM) == (3.0, 2.0)
    d.practice = {"limits": {"BLT-060.run_clearance_mm": 5.0, "BLT-061.pulley_plate_clearance_mm": 1.0}}
    assert clearance_limits(d) == (5.0, 1.0)


def test_clear_axis_has_no_clearance_warning():
    r = verify_motion(belt_axis())
    assert not warns(r, "belt_run_near_part") and not warns(r, "pulley_near_plate")
    c = r.metrics["belts"]["x_belt"]["clearance"]
    assert c["run_clearance_limit_mm"] == 3.0 and c["runs_near"] == {} and c["pulleys_near"] == {}


def test_a_stationary_part_2mm_from_the_return_run_warns_and_4mm_does_not():
    """A fixed block whose lower face is 2 mm above the upper run's outer face (belt 1.4 mm thick, its centre line on the
    run): a warning with the distance, not the collision error. At 4 mm, nothing."""
    for gap, expect in ((2.0, True), (4.0, False)):
        d = belt_axis()
        y0 = R_P + 0.7 + gap          # belt outer face at R_P + thickness / 2 (thickness 1.4 by default)
        d.add("cover", Pos(60, y0 + 4, 11) * Box(20, 8, 20))
        r = verify_motion(d)
        assert not [f for f in r.findings if f.severity == "error"], [f.message for f in r.findings if f.severity == "error"]
        w = warns(r, "belt_run_near_part")
        assert bool(w) == expect, (gap, [f.message for f in w])
        if expect:
            assert w[0].data["part"] == "cover" and abs(w[0].data["value"] - gap) < 0.1 and w[0].data["limit"] == 3.0
            assert w[0].severity == "warning" and "BLT-060" in w[0].message


def test_a_part_riding_with_the_belt_is_not_flagged():
    """The same block 2 mm from the run but on the carriage (the body the belt's ends are clamped to) moves with the
    belt: no rub, no warning."""
    d = belt_axis()
    d.add("cover", Pos(0, R_P + 0.7 + 2.0 + 4, 11) * Box(20, 8, 20), body="car")
    d.join("cover", "clamp", "bond")
    assert not warns(verify_motion(d), "belt_run_near_part")


def test_the_limit_can_be_raised_or_lowered():
    d = belt_axis()
    d.add("cover", Pos(60, R_P + 0.7 + 4.0 + 4, 11) * Box(20, 8, 20))
    assert not warns(verify_motion(d), "belt_run_near_part")
    d.practice = {"limits": {"BLT-060.run_clearance_mm": 5.0}}
    w = warns(verify_motion(d), "belt_run_near_part")
    assert w and w[0].data["limit"] == 5.0


def test_a_plate_1mm_from_an_idler_warns():
    """A made plate under the idler, 1 mm below its bottom flange (idler from z = 6.25): BLT-061 warning; at 3 mm none."""
    for gap, expect in ((1.0, True), (3.0, False)):
        d = belt_axis()
        d.add("idler_plate", Pos(150, 0, 6.25 - gap - 1.5) * Box(30, 30, 3.0), process="sheet", material="al6061")
        w = warns(verify_motion(d), "pulley_near_plate")
        assert bool(w) == expect, (gap, [f.message for f in w])
        if expect:
            assert w[0].data["pulley"] == "idler" and w[0].data["part"] == "idler_plate" and abs(w[0].data["value"] - gap) < 0.05
