from build123d import Box, Cylinder, Pos

from mechloop.model import Design, Fastener
from mechloop.verifiers.assemblability import verify_assemblability


def codes(r):
    return [f.code for f in r.findings if f.severity == "error"]


def test_peg_in_blind_hole_and_trapped():
    base = Box(60, 60, 20) - Pos(0, 0, 5) * Cylinder(5, 10)  # blind hole from top
    d = Design("peg")
    d.add("base", base)
    d.add("peg", Pos(0, 0, 10) * Cylinder(5, 20))
    r = verify_assemblability(d)
    assert codes(r) == [] and r.metrics["insert_directions"]["peg"] == "-Z"
    # a ball sealed inside a closed cavity can never be installed
    shell = Box(40, 40, 40) - Box(30, 30, 30)
    d2 = Design("trapped")
    d2.add("shell", shell)
    d2.add("core", Box(20, 20, 20))
    assert codes(verify_assemblability(d2)) == ["trapped_part"]


def test_lid_must_come_off_before_contents():
    d = Design("box")
    d.add("tub", Box(50, 50, 30) - Pos(0, 0, 2.5) * Box(40, 40, 25))
    d.add("contents", Pos(0, 0, 0) * Box(20, 20, 20))
    d.add("lid", Pos(0, 0, 17.5) * Box(50, 50, 5))
    r = verify_assemblability(d)
    seq = r.metrics["assembly_sequence"]
    assert codes(r) == [] and seq.index("contents") < seq.index("lid")


def test_tool_access():
    d = Design("screw")
    d.add("plate", Box(40, 40, 5) - Cylinder(1.7, 5))
    d.add("screw", Pos(0, 0, 0) * Cylinder(1.5, 5) + Pos(0, 0, 4) * Cylinder(2.75, 3))
    d.fasteners.append(Fastener("screw", (0, 0, 1), (0, 0, 5.5), tool_diameter=5, tool_length=50))
    assert codes(verify_assemblability(d)) == []
    d.add("overhang", Pos(0, 20, 25) * Box(40, 80, 5))
    d.add("post", Pos(0, 55, 10) * Box(10, 10, 25))
    assert "tool_access_blocked" in codes(verify_assemblability(d))
