"""Tests for checks added after the first agent trials."""
from build123d import Box, Cylinder, Location, Pos

from mechloop.model import Design, Joint, LoadCase, Requirement
from mechloop.parts import Stock, add_screw, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place
from mechloop.runner import verify
from mechloop.verifiers.assemblability import verify_assemblability
from mechloop.verifiers.fea import verify_fea
from mechloop.verifiers.motion import verify_motion
from mechloop.verifiers.ratings import verify_ratings


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


def rail_axis(travel):
    d = Design("axis")
    place(d, "rail", mgn12_rail(200), Location((0, 0, 0)))
    place(d, "block", mgn12h_carriage(), Location((0, 0, 0)), body="car", guides="x")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-travel, travel), max_effort=50))
    return d


def test_carriage_runoff():
    assert errs(verify_motion(rail_axis(70))) == []          # block half-length 22.7, rail half 100
    r = verify_motion(rail_axis(90))
    assert errs(r) == ["guide_runoff", "guide_runoff"]


def test_fea_on_a_bolt_hole():
    d = Design("lug")
    d.add("lug", Pos(30, 0, 0) * Box(80, 30, 8) - Cylinder(5, 8), material="al6061")
    d.loadcases.append(LoadCase("pull", "lug",
                                fixed=lambda f: abs(f.center().X - 70) < 1e-6,
                                loaded=lambda f: f.geom_type.name == "CYLINDER",
                                force=(-200, 0, 0), min_fos=2.0, mesh_size=2.5))
    r = verify_fea(d)
    assert r.ok and r.metrics["pull"]["reaction_imbalance"] < 1e-3
    assert abs(r.metrics["pull"]["load_area_mm2"] - 2 * 3.14159 * 5 * 8) < 1.0


def test_screw_installs_after_the_part_it_holds():
    d = Design("stack", base="block")
    d.add("block", Box(40, 40, 20))
    d.add("cover", Pos(0, 0, 12.5) * (Box(40, 40, 5) - Cylinder(1.7, 5)))
    add_screw(d, "screw", "M3", 10, at=(0, 0, 15), threads_into="block")
    r = verify_assemblability(d)
    seq = r.metrics["assembly_sequence"]
    assert errs(r) == [] and seq.index("cover") < seq.index("screw")


def test_requirement_can_read_verifier_metrics():
    d = rail_axis(50)
    d.requirements.append(Requirement("x drive margin >= 2", lambda dd, m: (
        m["motion"]["drives"]["x"]["margin"] in ("inf",) or m["motion"]["drives"]["x"]["margin"] >= 2, "ok")))
    d.requirements.append(Requirement("impossible", lambda dd, m: (m["fea"]["nope"] > 1, "")))
    rep = verify(d)
    req = next(r for r in rep.results if r.verifier == "requirements")
    assert [f.code for f in req.findings] == ["requirement_met", "requirement_failed"]


def test_proxy_parts_are_flagged_and_leadscrew_drive_reads_the_screw():
    d = Design("z")
    place(d, "motor", nema17(40), Location((0, 0, 0)))
    place(d, "screw", leadscrew_t8(200, lead=2), Location((0, 0, 30)))
    place(d, "gizmo", Stock(Box(5, 5, 5), "GIZMO", "hand-made proxy", 0.01), Location((50, 0, 0)))
    d.add("nut_block", Pos(0, 0, 100) * (Box(30, 30, 10) - Cylinder(4.2, 10)), body="z")
    d.joints.append(Joint("z", "slide", "world", "z", (0, 0, 1), range=(-50, 50), max_speed=10, max_accel=100,
                          drive={"motor": "motor", "kind": "leadscrew", "screw": "screw"}))
    r = verify_ratings(d)
    assert "uncatalogued_cots" in [f.code for f in r.findings]
    # F = 2 pi T eta / lead with the catalog's efficiency for a 2 mm lead (0.35)
    T = r.metrics["drives"]["z"]["motor_torque_nmm_at_speed"]
    assert abs(r.metrics["drives"]["z"]["available_effort"] - 2 * 3.14159 * T * 0.35 / 2) < 1.0
    d.joints[0].drive = {"motor": "motor", "kind": "leadscrew", "screw": "missing"}
    assert "drive_part_missing" in errs(verify_ratings(d))


def test_rotor_inertia_counts_against_the_drive():
    d = rail_axis(50)
    place(d, "motor", nema17(40), Location((0, 60, 0)))
    j = d.joints[0]
    j.max_effort, j.max_speed, j.max_accel = None, 100, 20000
    j.drive = {"motor": "motor", "kind": "belt", "pulley_teeth": 20}
    r = verify_motion(d)
    drv = r.metrics["drives"]["x"]
    # rotor 54 g cm^2 through a 40 mm/rev belt looks like 0.133 kg at the carriage
    assert abs(j.reflected_inertia - 5.4e-6 * (2 * 3.14159 / 0.04) ** 2) < 1e-3
    assert drv["required"] > (drv["moved_mass_kg"] + 0.12) * 20.0


def belt_axis(anchor_y=0.0, idler_x=150.0):
    """Motor pulley and idler fixed to the world, carriage clamped to the lower belt run."""
    import math

    from mechloop.model import Belt
    from mechloop.parts import gt2_idler, gt2_pulley

    d = Design("beltaxis")
    place(d, "drive", gt2_pulley(20), Location((-150, 0, 0)))
    place(d, "idler", gt2_idler(20), Location((idler_x, 0, 6.25)))
    d.add("clamp", Pos(0, -10.1, 11) * Box(20, 6, 10), body="car")
    r_p = 20 * 2 / math.pi / 2
    z = d.get("drive").meta["interfaces"]["belt_center"][0][2]
    y = -r_p + anchor_y
    d.belts.append(Belt("x_belt", [("anchor", "car", (10, y, z)), ("pulley", "idler", "ccw"),
                                   ("pulley", "drive", "ccw"), ("anchor", "car", (-10, y, z))]))
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-100, 100), max_effort=50))
    return d


def test_belt_route_checks():
    import math

    from mechloop.verifiers.belts import route
    from mechloop.geom import forward_kinematics

    d = belt_axis()
    r = verify_motion(d)
    assert errs(r) == [], [f.message for f in r.findings]
    m = r.metrics["belts"]["x_belt"]
    # open loop: two straight runs of 300 minus the 20 mm gap between anchors, plus two half wraps
    expect = 2 * 300 - 20 + math.pi * (20 * 2 / math.pi)
    assert abs(m["length_mm"] - expect) < 0.05 and m["length_change_over_travel_mm"] < 0.01
    # anchors off the tangent line: the path length now changes as the carriage moves
    assert "belt_length_changes" in errs(verify_motion(belt_axis(anchor_y=-8.0)))
    # something in the way of the return run
    d = belt_axis()
    d.add("post", Pos(60, 6.4, 11) * Box(8, 8, 30))
    assert "belt_collision" in errs(verify_motion(d))


def test_thread_engagement_and_missing_belt():
    from mechloop.parts import gt2_pulley
    from mechloop.verifiers.interference import verify_interference

    d = Design("thr")
    d.add("block", Box(40, 40, 20), material="al6061")
    d.add("cover", Pos(0, 0, 12.5) * (Box(40, 40, 5) - Cylinder(1.7, 5)))
    add_screw(d, "short", "M3", 8, at=(0, 0, 15), threads_into="block")     # 3 mm in aluminium: needs 4.5
    r = verify_interference(d)
    assert "thread_engagement" in errs(r)
    d2 = Design("thr2")
    d2.add("block", Box(40, 40, 20), material="al6061")
    d2.add("cover", Pos(0, 0, 12.5) * (Box(40, 40, 5) - Cylinder(1.7, 5)))
    add_screw(d2, "long", "M3", 10, at=(0, 0, 15), threads_into="block")    # 5 mm: fine
    assert "thread_engagement" not in errs(verify_interference(d2))
    # a belt-driven joint with no belt is not connected to its load
    d3 = rail_axis(50)
    place(d3, "motor", nema17(40), Location((0, 60, 0)))
    place(d3, "pul", gt2_pulley(20), Location((0, 60, 2.5)))
    d3.joints[0].drive = {"motor": "motor", "kind": "belt", "pulley": "pul"}
    d3.joints[0].max_speed, d3.joints[0].max_accel = 100, 1000
    assert "belt_missing" in errs(verify_motion(d3))
