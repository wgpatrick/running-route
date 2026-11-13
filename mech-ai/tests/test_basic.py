from build123d import Box, Cylinder, Pos

from mechloop.model import Design, Joint
from mechloop.verifiers.geometry import verify_geometry
from mechloop.verifiers.interference import verify_interference
from mechloop.verifiers.motion import verify_motion


def codes(r):
    return [f.code for f in r.findings if f.severity == "error"]


def test_interference_and_floating():
    d = Design("t")
    d.add("base", Box(100, 100, 10))
    d.add("post", Pos(0, 0, 20) * Box(10, 10, 30))  # sits on base: z 5..35
    assert codes(verify_interference(d)) == []
    d.add("clash", Pos(0, 0, 8) * Box(20, 20, 4))  # buried in base and post
    assert "interference" in codes(verify_interference(d))
    d2 = Design("t2")
    d2.add("base", Box(100, 100, 10))
    d2.add("hover", Pos(0, 0, 30) * Box(10, 10, 10))
    assert codes(verify_interference(d2)) == ["floating_parts"]


def test_geometry_envelope_mass():
    d = Design("t", envelope=(50, 50, 50), max_mass_kg=0.01)
    d.add("base", Box(100, 100, 10))
    assert set(codes(verify_geometry(d))) == {"envelope_exceeded", "mass_exceeded"}


def slider(travel, effort):
    d = Design("slider")
    d.add("rail", Box(300, 10, 10))
    d.add("stop", Pos(140, 0, 15) * Box(10, 10, 20))
    d.add("carriage", Pos(0, 0, 15) * Box(30, 30, 20), body="car", material="steel")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-100, travel),
                          max_effort=effort, max_speed=200, max_accel=5000))
    return d


def test_motion_collision_and_drive():
    assert codes(verify_motion(slider(100, 50))) == []
    assert "motion_collision" in codes(verify_motion(slider(125, 50)))
    r = verify_motion(slider(100, 0.1))
    assert codes(r) == ["drive_undersized"]
    # F = m a: 30*30*20 mm steel = 0.1413 kg at 5 m/s^2 = 0.71 N
    assert abs(r.metrics["drives"]["x"]["required"] - 0.1413 * 5) < 0.02


def test_vertical_axis_holding():
    d = Design("z")
    d.add("col", Box(10, 10, 300))
    d.add("car", Pos(20, 0, 0) * Box(30, 30, 30), body="z", mass_kg=2.0)
    d.joints.append(Joint("z", "slide", "world", "z", (0, 0, 1), range=(-100, 100), max_effort=100))
    r = verify_motion(d)
    assert abs(r.metrics["drives"]["z"]["holding"] - 2.0 * 9.81) < 0.05
