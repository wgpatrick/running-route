"""Homing, cables and printer essentials."""
from build123d import Box, Location, Pos

from mechloop.model import Cable, Design, Joint
from mechloop.parts import endstop_switch, place
from mechloop.verifiers.subsystems import verify_subsystems


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


def axis(flag_x):
    """A carriage on a slide. The switch is on the frame; a flag on the carriage should press it at x = -50."""
    d = Design("ax")
    d.add("rail", Box(200, 10, 10))
    d.add("car", Pos(0, 0, 15) * Box(30, 30, 20), body="car")
    d.add("flag", Pos(flag_x, 0, 30) * Box(4, 10, 10), body="car")
    # switch on a post at the -X end, trigger facing +X: rotate so its -Y push direction points along -X
    d.add("post", Pos(-80, 0, 20) * Box(10, 20, 50))
    sw = place(d, "sw", endstop_switch(), Location((-70.0, 0, 26), (90, 0, 90)))
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50), max_effort=10))
    d.endstops.append({"joint": "x", "switch": "sw", "at": "min"})
    return d, sw.meta["interfaces"]["trigger"][0]


def test_endstop_is_pressed_only_when_the_flag_reaches_it():
    d, trig = axis(0)
    # put the flag so its -X face is at the trigger point when the carriage is at -50
    d, _ = axis(trig[0] + 50 + 2.0)
    assert errs(verify_subsystems(d)) == []
    d, _ = axis(trig[0] + 50 + 12.0)                 # flag 10 mm short: never pressed
    assert errs(verify_subsystems(d)) == ["endstop_not_reached"]


def test_cable_must_reach_over_the_whole_travel():
    d = Design("cab")
    d.add("rail", Box(300, 10, 10))
    d.add("car", Pos(0, 0, 15) * Box(30, 30, 20), body="car")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-120, 120), max_effort=10))
    d.cables.append(Cable("loom", ("car", (0, 0, 25)), ("world", (0, 0, 5)), length=100.0))
    r = verify_subsystems(d)
    assert errs(r) == ["cable_too_short"]
    d.cables[0].length = 180.0
    assert errs(verify_subsystems(d)) == []
    d.cables[0] = Cable("loom", ("car", (0, 0, 120)), ("world", (0, 0, 5)), length=300.0)     # clamp point in thin air
    assert "cable_clamp_in_air" in errs(verify_subsystems(d))
