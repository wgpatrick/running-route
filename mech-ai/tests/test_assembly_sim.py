"""Assembly simulation: build order, sub-assemblies, two-move paths, holding and turning."""
from build123d import Box, Cylinder, Pos

from mechloop.assembly.planner import plan
from mechloop.assembly.simulate import analyse, instructions
from mechloop.model import Design
from mechloop.parts import add_screw


def test_part_on_top_rests_part_on_the_side_needs_holding():
    d = Design("rest", base="block")
    d.add("block", Box(60, 60, 40))
    d.add("on_top", Pos(0, 0, 25) * Box(30, 30, 10))
    d.add("on_side", Pos(35, 0, 0) * Box(10, 30, 30))
    res = analyse(d, reorient=False)
    rows = {r["unit"]: r for r in res["rows"]}
    assert rows["on_top"]["rests_stably"] is True and rows["on_top"]["direction"] == "from above"
    assert rows["on_side"]["rests_stably"] is False
    assert res["metrics"]["needs_holding"] == 1


def test_turning_the_assembly_avoids_holding():
    """Six plates on one side face: laying the block on its side makes them rest, which is worth one turn."""
    d = Design("turn", base="block")
    d.add("block", Box(120, 120, 40))
    for i, y in enumerate((-50, -30, -10, 10, 30, 50)):
        d.add(f"side_{i}", Pos(65, y, 0) * Box(10, 15, 30))
    fixed = analyse(d, reorient=False)
    free = analyse(d, reorient=True)
    assert fixed["metrics"]["needs_holding"] == 6 and fixed["metrics"]["times_assembly_is_turned"] == 0
    assert free["metrics"]["needs_holding"] == 0 and free["metrics"]["times_assembly_is_turned"] == 1
    assert "Turn the assembly" in instructions(d, free)


def test_overhanging_part_tips_but_a_pegged_one_does_not():
    d = Design("tip", base="block")
    d.add("block", Box(40, 40, 40) - Pos(0, 0, 15) * Cylinder(5, 10))
    d.add("diving_board", Pos(35, 0, 22.5) * Box(60, 10, 5))        # 10 mm on the block, 50 mm in the air
    d.add("peg", Pos(0, 0, 25) * Cylinder(5, 30))                    # sits in the hole
    rows = {r["unit"]: r for r in analyse(d, reorient=False)["rows"]}
    assert rows["diving_board"]["rests_stably"] is False and "tip" in rows["diving_board"]["hold_reason"]
    assert rows["peg"]["rests_stably"] is True


def test_two_move_path_is_found():
    """A key that must drop into a slot and then slide under a lip: no single straight move works."""
    body = Box(60, 40, 30) - Pos(-10, 0, 5) * Box(20, 20, 20) - Pos(5, 0, 0) * Box(30, 20, 10)
    d = Design("key", base="body")
    d.add("body", body)
    d.add("key", Pos(10, 0, 0) * Box(18, 18, 9))                     # ends up under the lip
    p = plan(d)
    assert p.complete
    key = next(s for s in p.steps if s.unit == "key")
    assert len(key.path) == 2
    assert not plan(d, two_step=False).complete


def test_subassembly_goes_in_as_one_unit_and_screws_follow_their_part():
    d = Design("sub", base="frame")
    d.add("frame", Box(100, 100, 10))
    d.add("bracket", Pos(0, 0, 10) * Box(40, 40, 10), material="steel")
    d.add("sensor", Pos(0, 0, 20) * (Box(20, 20, 10) - Cylinder(1.7, 10)))
    add_screw(d, "sensor_screw", "M3", 14, at=(0, 0, 25), threads_into="bracket", clamps=("sensor",))
    d.subassemblies["sensor_module"] = ["bracket", "sensor", "sensor_screw"]
    res = analyse(d, reorient=False)
    units = [r["unit"] for r in res["rows"]]
    assert units == ["frame", "sensor_module"]
    assert "sensor_module" in res["subassemblies"]
    inner = [r["unit"] for r in res["subassemblies"]["sensor_module"]["rows"]]
    assert inner.index("sensor") < inner.index("sensor_screw")
    assert res["metrics"]["estimated_time_s"] > res["subassemblies"]["sensor_module"]["metrics"]["estimated_time_s"]


def test_sealed_part_is_reported_trapped():
    d = Design("trap", base="shell")
    d.add("shell", Box(40, 40, 40) - Box(30, 30, 30))
    d.add("core", Box(20, 20, 20))
    res = analyse(d, reorient=False)
    assert res["metrics"]["complete"] is False and res["metrics"]["trapped"] == ["core"]
