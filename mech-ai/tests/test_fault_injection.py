"""A check is trusted once it has been seen to fail.

Start from the passing gantry, break it in one specific way, and require the
matching verifier to report exactly that kind of problem.
"""
from pathlib import Path

import pytest
from build123d import Box, Location, Pos

from mechloop.runner import load_design
from mechloop.verifiers.assemblability import verify_assemblability
from mechloop.verifiers.fea import verify_fea
from mechloop.verifiers.geometry import verify_geometry
from mechloop.verifiers.interference import verify_interference
from mechloop.verifiers.motion import verify_motion

GANTRY = Path(__file__).parent.parent / "examples" / "gantry.py"


@pytest.fixture()
def gantry():
    return load_design(GANTRY)


def errs(r):
    return {f.code for f in r.findings if f.severity == "error"}


def test_baseline_is_clean(gantry):
    assert errs(verify_geometry(gantry)) == set()
    assert errs(verify_interference(gantry)) == set()
    assert errs(verify_motion(gantry)) == set()


def test_too_much_travel_hits_something(gantry):
    next(j for j in gantry.joints if j.name == "x").range = (-135.0, 135.0)
    r = verify_motion(gantry)
    assert "motion_collision" in errs(r)


def test_hotend_moved_forward_hits_front_frame(gantry):
    h = gantry.get("hotend")
    h.shape = h.shape.moved(Location((0, -40, 0)))
    r = verify_motion(gantry)
    hits = [f.data["parts"] for f in r.findings if f.code == "motion_collision"]
    assert any("hotend" in p and "frame_top_front" in p for p in hits)


def test_shifted_screw_interferes(gantry):
    s = gantry.get("tool_screw_0")
    s.shape = s.shape.moved(Location((1.5, 0, 0)))
    r = verify_interference(gantry)
    assert any(f.code == "interference" and "tool_screw_0" in f.data["parts"] for f in r.findings)


def test_missing_bracket_joint_is_unfastened(gantry):
    for key in [k for k in gantry.joins if "bracket_0" in k or "bracket_1" in k
                or "bracket_2" in k or "bracket_3" in k]:
        del gantry.joins[key]
    r = verify_interference(gantry)
    assert "unfastened" in errs(r)


def test_removed_support_leaves_floating_part(gantry):
    gone = {c.name for c in gantry.components if c.name.startswith("y_motor_") or c.name.startswith("y_mount")}
    gantry.components = [c for c in gantry.components if c.name not in gone]
    gantry.fasteners = [f for f in gantry.fasteners if f.name not in gone]
    gantry.joins = {k: v for k, v in gantry.joins.items() if not (set(k) & gone)}
    gantry.allowed_overlaps = {k: v for k, v in gantry.allowed_overlaps.items() if not (set(k) & gone)}
    r = verify_interference(gantry)
    floating = [p for f in r.findings if f.code == "floating_parts" for p in f.data["parts"]]
    assert "y_motor" in floating


def test_weak_drive_is_undersized(gantry):
    y = next(j for j in gantry.joints if j.name == "y")
    y.max_accel = 200_000.0
    assert "drive_undersized" in errs(verify_motion(gantry))


def test_heavy_toolhead_changes_required_force(gantry):
    base = verify_motion(gantry).metrics["drives"]["x"]["required"]
    gantry.get("hotend").mass_kg = 1.12  # +1 kg
    heavy = verify_motion(gantry).metrics["drives"]["x"]["required"]
    assert heavy - base == pytest.approx(1.0 * 5.0, rel=0.02)  # F = m a at 5 m/s^2


def test_cover_over_screws_blocks_driver(gantry):
    # a lid resting on the tool screws' heads, declared as the thing everything is built onto
    small = load_design(GANTRY)
    keep = {"x_carriage", "tool_plate", "tool_screw_0", "tool_screw_1", "tool_screw_2", "tool_screw_3"}
    small.components = [c for c in small.components if c.name in keep]
    small.fasteners = [f for f in small.fasteners if f.name in keep]
    small.joints = []
    for c in small.components:
        c.body = "world"
    top = max(c.shape.bounding_box().max.Z for c in small.components)
    small.add("lid", Pos(0, 0, top + 12) * Box(60, 60, 4))
    small.base = "lid"
    assert "tool_access_blocked" in errs(verify_assemblability(small))


def test_overload_fails_strength(gantry):
    lc = gantry.loadcases[0]
    lc.force = tuple(300 * x for x in lc.force)
    assert {"fos_low", "deflection_high"} <= errs(verify_fea(gantry))


def test_envelope(gantry):
    gantry.envelope = (300, 300, 300)
    assert "envelope_exceeded" in errs(verify_geometry(gantry))
