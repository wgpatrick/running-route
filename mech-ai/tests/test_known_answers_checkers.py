"""Known-answer tests for six checker problems reported by the printer_v7 design pass (docs/PRINTER_V7.md, "Checker
behaviour I think is wrong or worth a look"). Small purpose-built designs; answers by hand or by construction; each
tested both ways (the bad case fails, the good case passes)."""
import json
import math
import sys
from pathlib import Path

import pytest
from build123d import Box, Cylinder, Location, Pos

from mechloop.electrical import (PROBE_THERMAL, Device, Electrical, Port, klipper_config, probe_geometry,
                                 probe_temperature_estimate)
from mechloop.model import Design, Joint
from mechloop.parts import add_probe_nuts, place, probe_omron_e2e
from mechloop.report import VerifierResult
from mechloop.verifiers import electrical as VE
from mechloop.verifiers.motion import verify_motion
from mechloop.verifiers.subsystems import verify_subsystems

ROOT = Path(__file__).resolve().parents[1]


def codes(r, severity=None):
    return [f.code for f in r.findings if severity is None or f.severity == severity]


# ---------------------------------------------------------------- 1. probe clamp ring; nuts as separate parts
def probe_head(model="E2E-X10ME1", face_above_nozzle=1.2, mount="closed", turn=0.0, nuts="fused", bed="al6061",
               overtravel=(0.0, 0.0), clamp=(22.0, 25.0), x_probe=40.0):
    """Bed top at z = 50, nozzle tip at z = 100 on a plastic head (x, y within +/-10). A plastic bracket 3 mm thick
    runs from the head's side out to the probe, whose axis is `x_probe` to the side and whose sensing face is
    `face_above_nozzle` above the tip. mount: "closed" (a clearance hole), "fork" (a slot the width of the hole, open
    to +Y), "fork+key" (the slot filled by a second part), "none" (no bracket). turn: the round sensor turned about
    its own axis, degrees."""
    d = Design("probe_head", base="head")
    d.add("frame", Pos(0, 0, 200) * Box(300, 300, 10))
    d.add("bed", Pos(0, 0, 47) * Box(200, 200, 6), material=bed, body="zbody")
    d.add("head", Pos(0, 0, 130) * Box(20, 20, 60), material="petg", body="xbody")              # tip face at z = 100
    zf = 100.0 + face_above_nozzle
    st = probe_omron_e2e(model, clamp=clamp, nuts=nuts)
    place(d, "probe", st, Location((x_probe, 0, zf), (0, 0, turn)), body="xbody")
    if nuts == "separate":
        add_probe_nuts(d, "probe")
    hole = st.interfaces["mounting"]["hole_dia"]
    t = clamp[1] - clamp[0]
    zc = zf + clamp[0] + t / 2
    if mount != "none":
        x0, x1 = 10.0, x_probe + 20.0
        br = Pos((x0 + x1) / 2, 0, zc) * Box(x1 - x0, 40, t) - Pos(x_probe, 0, zc) * Cylinder(hole / 2, t)
        slot = Pos(x_probe, 10.0, zc) * Box(hole, 20.0, t)                                      # from the axis out to y = +20
        if mount.startswith("fork"):
            br -= slot
        d.add("bracket", br, material="petg", body="xbody")
        d.join("bracket", "head", "bonded")
        d.join("probe", "bracket", "clamped by its two nuts")
        if mount == "fork+key":
            d.add("key", slot - Pos(x_probe, 0, zc) * Cylinder(hole / 2, t), material="petg", body="xbody")
            d.join("key", "probe", "clamped by its two nuts")
    d.joints += [Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-90, 90), max_effort=10),
                 Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-90, 50), max_effort=10),
                 Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(0, 50), max_effort=10, overtravel=overtravel)]
    d.tool_point = ("xbody", (0.0, 0.0, 100.0))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z"}
    d.endstops += [{"joint": "x", "sensorless": True}, {"joint": "y", "sensorless": True}, {"joint": "z", "probe": "probe", "at": "max"}]
    return d


def homing_z(d):
    r = verify_subsystems(d)
    return {f.code: f for f in r.findings if f.code.startswith("probe")}, r.metrics["homing"]["z"]


@pytest.mark.parametrize("turn", [0.0, 10.0, 22.5, 45.0])
def test_probe_clamp_does_not_depend_on_turning_a_round_sensor(turn):
    """M18 sensor: nut bearing circle at 9 + 0.6 x (12 - 9) = 10.8 mm radius, hole and fork slot 18.5 mm wide. The slot
    removes 2 asin(9.25 / 10.8) = 117.9 degrees of that circle: an open fork carries 67 % of it, under the 75 % asked,
    whichever way the sensor is turned (the 8-point count gave 5 of 8 at 0 degrees and 6 of 8 at 22.5). A key that
    fills the slot completes the ring, again whichever way the sensor is turned. No bracket: nothing."""
    open_frac = 1.0 - 2.0 * math.degrees(math.asin(9.25 / 10.8)) / 360.0
    f, z = homing_z(probe_head(mount="fork", turn=turn))
    assert f["probe_not_clamped"].severity == "error"
    assert z["mounting"]["clamp_ring_covered_frac"] == pytest.approx(open_frac, abs=1.0 / 72)
    assert z["mounting"]["clamp_ring_covered_frac"] == homing_z(probe_head(mount="fork", turn=0.0))[1]["mounting"]["clamp_ring_covered_frac"]
    f, z = homing_z(probe_head(mount="fork+key", turn=turn))
    assert "probe_not_clamped" not in f and z["mounting"]["clamp_ring_covered_frac"] == 1.0
    assert set(z["mounting"]["clamp_ring_parts"]) == {"bracket", "key"} and z["mounting"]["clamped_in"] == "bracket"


def test_probe_clamp_closed_hole_passes_and_no_plate_fails():
    f, z = homing_z(probe_head(mount="closed"))
    assert "probe_not_clamped" not in f and z["mounting"]["clamp_ring_covered_frac"] == 1.0
    f, z = homing_z(probe_head(mount="none"))
    assert f["probe_not_clamped"].severity == "error" and z["mounting"]["clamp_ring_covered_frac"] == 0.0


def clamp_only(mount, nuts):
    """Head, bracket and sensor alone, for the assembly check."""
    d = probe_head(mount=mount, nuts=nuts)
    keep = {"head", "bracket", "probe", "probe_nut_front", "probe_nut_rear"}
    d.components = [c for c in d.components if c.name in keep]
    for c in d.components:
        c.body = "world"
    d.joints, d.printer, d.endstops, d.tool_point = [], None, [], None
    return d


def test_a_sensor_with_fused_nuts_cannot_enter_a_closed_hole_and_one_with_separate_nuts_can():
    """A threaded barrel sensor is fitted by taking one nut off, passing the barrel through the hole and putting the nut
    back. With the two nuts drawn as part of the sensor (one rigid part, a collar each side of the plate) no straight
    move gets it into a closed hole: trapped. With the nuts as their own catalogue parts the same closed hole is
    assembled: barrel along its axis, a nut from each side. The fused sensor does go sideways into an open fork."""
    from mechloop.verifiers.assemblability import verify_assemblability

    r = verify_assemblability(clamp_only("closed", "fused"))
    trapped = [f for f in r.findings if f.code == "trapped_part"]
    assert trapped and "probe" in trapped[0].message and not r.metrics["complete"]
    r = verify_assemblability(clamp_only("closed", "separate"))
    assert not codes(r, "error") and r.metrics["complete"]
    assert r.metrics["parts_placed"] == r.metrics["parts_total"] == 5
    r = verify_assemblability(clamp_only("fork", "fused"))
    assert not codes(r, "error") and r.metrics["complete"]


def test_separate_nuts_are_catalogue_parts_on_the_clamp_faces_and_are_checked():
    """E2E-X10ME1, plate 22 to 25 mm above the face: front nut 18 to 22 (4 mm), rear nut with its washer 25 to 30
    (1 + 4 mm), both 24 mm across, brass, supplied with the sensor (cost 0). The barrel then has no collars: its widest
    point is the 18 mm thread. Leaving the nuts out is an error; the sensor's own nuts are not metal in its clear zone
    (the plate is 22 mm behind the face, l = 22: the front nut is inside the zone and must not count)."""
    d = probe_head(nuts="separate")
    f, z = homing_z(d)
    assert not [c for c in f if c in ("probe_not_clamped", "probe_nuts_missing", "probe_metal_in_clear_zone")]
    assert z["mounting"]["nuts"] == {"front": ["probe_nut_front"], "rear": ["probe_nut_rear"]} and z["mounting"]["metal_in_zone"] == []
    fb, rb = d.get("probe_nut_front").shape.bounding_box(), d.get("probe_nut_rear").shape.bounding_box()
    zf = 100.0 + 1.2
    assert (fb.min.Z, fb.max.Z) == pytest.approx((zf + 18.0, zf + 22.0)) and (rb.min.Z, rb.max.Z) == pytest.approx((zf + 25.0, zf + 30.0))
    assert fb.size.X == pytest.approx(24.0) and d.get("probe_nut_front").cots and d.get("probe_nut_front").meta["cost_usd"] == 0.0
    assert d.get("probe").shape.bounding_box().size.X == pytest.approx(18.0)
    assert probe_omron_e2e("E2E-X10ME1", clamp=(22.0, 25.0)).shape.bounding_box().size.X == pytest.approx(24.0)     # fused: as before
    fused, sep = probe_omron_e2e("E2E-X10ME1", clamp=(22.0, 25.0)), probe_omron_e2e("E2E-X10ME1", clamp=(22.0, 25.0), nuts="separate")
    nuts_kg = d.get("probe_nut_front").mass() + d.get("probe_nut_rear").mass()
    assert sep.mass_kg + nuts_kg == pytest.approx(fused.mass_kg, abs=1e-9)                  # the sensor's mass is not counted twice
    d2 = probe_head(nuts="separate")
    d2.components = [c for c in d2.components if c.name != "probe_nut_rear"]
    f, _ = homing_z(d2)
    assert f["probe_nuts_missing"].severity == "error" and "upper face" in f["probe_nuts_missing"].message
    with pytest.raises(ValueError, match="needs clamp"):
        probe_omron_e2e("E2E-X10ME1", nuts="separate")


# ---------------------------------------------------------------- 2. Z over-travel and what rides with the nozzle
def toolhead_over_bed(overtravel=(0.0, 2.0), clip_above=None, rail_above=None):
    """Bed top at z = 50, nozzle tip at z = 100 on body 'xbody': the bed meets the nozzle plane at z = +50.
    clip_above: a 10 x 10 mm part of the TOOLHEAD, bolted to the hotend's carrier, 30 mm to the side, its underside
    that far above the nozzle plane (negative: it hangs below). rail_above: the same size of part on the GANTRY (body
    'ybody', which does not carry the nozzle), 60 mm to the side."""
    d = Design("zot2")
    d.add("frame", Pos(0, 0, 200) * Box(300, 300, 10))
    d.add("carrier", Pos(15, 0, 147.5) * Box(60, 20, 5), body="xbody")                     # z 145..150
    d.add("hotend", Pos(0, 0, 122.5) * Box(20, 20, 45), body="xbody")                      # tip face at z = 100
    d.join("hotend", "carrier", "screwed")
    if clip_above is not None:
        z0 = 100.0 + clip_above
        d.add("clip", Pos(30, 0, (z0 + 145.0) / 2) * Box(10, 10, 145.0 - z0), body="xbody")
        d.join("clip", "carrier", "screwed")
    if rail_above is not None:
        z0 = 100.0 + rail_above
        d.add("rail", Pos(60, 0, (z0 + 160.0) / 2) * Box(10, 10, 160.0 - z0), body="ybody")
    d.add("bed", Pos(0, 0, 47) * Box(200, 200, 6), material="al6061", body="zbody")        # top at z = 50
    d.joints += [Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(0, 0), max_effort=10),
                 Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(0, 0), max_effort=10),
                 Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(0.0, 50.0), max_effort=100, overtravel=overtravel)]
    d.tool_point = ("xbody", (0.0, 0.0, 100.0))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z"}
    return d


def collisions(d):
    return [f for f in verify_motion(d).findings if f.code == "motion_collision"]


def test_bed_rise_between_nozzle_and_a_point_to_its_side_by_hand():
    """Plate 200 mm, no maker's flatness for 6061: 0.381 mm assumed, as one bow seen from the plate edge. 40 mm to the
    side: 0.381 x (1 - (1 - 80 / 200)^2) = 0.2438; levelling residual 0.5 x 0.2 x 40 / (0.8 x 200) = 0.025. Sum 0.269.
    On cast tooling plate (ATP-5, maker's 0.381 for 6 mm) the same, from the maker's figure."""
    from mechloop.tolerance.toolhead import bed_rise

    br = bed_rise(probe_head(), 40.0)
    assert br["bow_mm"] == pytest.approx(0.244, abs=1e-3) and br["level_residual_mm"] == pytest.approx(0.025, abs=1e-3)
    assert br["bed_rise_mm"] == pytest.approx(0.269, abs=1e-3) and "ASSUMED" in br["flatness_basis"]
    br = bed_rise(probe_head(bed="al_atp5"), 40.0)
    assert br["bed_rise_mm"] == pytest.approx(0.269, abs=1e-3) and "Vista" in br["flatness_basis"]
    assert bed_rise(probe_head(), 0.0)["bed_rise_mm"] == 0.0


def test_a_toolhead_part_rides_with_the_nozzle_in_z_overtravel_and_a_gantry_part_does_not():
    """2 mm of Z over-travel past the nozzle plane.
    A clip ON THE TOOLHEAD 1 mm above the nozzle plane: the old rule drove the bed 2 mm past the nozzle and reported
    10 x 10 x 1 = 100 mm^3. The nozzle and the clip are on one body: the over-travel is common to both, so the bed is
    taken only to nozzle contact plus the clip's toolhead margin (well under 1 mm here: two machined joints and
    0.24 mm of bed flatness over 35 mm): no collision.
    The same part ON THE GANTRY (not the nozzle's body) 1 mm above the plane: still 100 mm^3 at z = 52, as before.
    A toolhead part hanging 0.5 mm BELOW the nozzle plane: a collision at every depth, 10 x 10 x (0.5 + margin).
    A toolhead part only 0.05 mm above the plane: closer than its margin, a collision of 10 x 10 x (margin - 0.05)."""
    assert collisions(toolhead_over_bed(clip_above=1.0)) == []
    r = verify_motion(toolhead_over_bed(clip_above=1.0))
    assert "nozzle_approach_overtravel" in codes(r)
    hm = r.metrics["overtravel"]["z"]["toolhead_parts_checked_at_nozzle_contact_plus_margin"]["clip"]
    assert 0.24 < hm["margin_mm"] < 0.9 and hm["bed_rise_mm"] == pytest.approx(0.243, abs=0.01) and hm["stackup_mm"] > 0.0
    (hit,) = collisions(toolhead_over_bed(rail_above=1.0))
    assert set(hit.data["parts"]) == {"bed", "rail"} and hit.data["volume_mm3"] == pytest.approx(100.0, abs=1.0)
    assert hit.data["pose"] == {"z": 52.0} and "toolhead_part" not in hit.data
    (hit,) = collisions(toolhead_over_bed(clip_above=-0.5))
    m = hit.data["toolhead_margin_mm"]
    assert set(hit.data["parts"]) == {"bed", "clip"} and hit.data["toolhead_part"] == "clip"
    assert hit.data["volume_mm3"] == pytest.approx(100.0 * (0.5 + m), abs=1.0) and hit.data["checked_past_working_end_mm"] == pytest.approx(m, abs=1e-3)
    (hit,) = collisions(toolhead_over_bed(clip_above=0.05))
    assert set(hit.data["parts"]) == {"bed", "clip"} and hit.data["volume_mm3"] == pytest.approx(100.0 * (hit.data["toolhead_margin_mm"] - 0.05), abs=1.0)
    # with no over-travel declared nothing changes: the part below the plane is hit in the working range, the others are clear
    (hit,) = collisions(toolhead_over_bed(overtravel=(0.0, 0.0), clip_above=-0.5))
    assert hit.data["volume_mm3"] == pytest.approx(50.0, abs=1.0) and "toolhead_part" not in hit.data
    assert collisions(toolhead_over_bed(overtravel=(0.0, 0.0), clip_above=0.05)) == []


def test_z_overtravel_larger_than_the_probe_face_height_is_not_a_collision_with_the_probe():
    """printer_v7 with Z_UP = 2.2 and the face 1.8 mm up gave 'bed hits bed_probe'. Here: face 1.2 mm above the nozzle,
    3 mm of over-travel. The probe rides with the nozzle: no collision, and the probe findings are the same as with no
    over-travel at all. A probe on the gantry instead of the toolhead is still hit."""
    d = probe_head(face_above_nozzle=1.2, overtravel=(0.0, 3.0))
    assert collisions(d) == []
    f3, z3 = homing_z(d)
    f0, z0 = homing_z(probe_head(face_above_nozzle=1.2))
    assert sorted(f3) == sorted(f0) and z3["probe_to_nozzle_margin"] == z0["probe_to_nozzle_margin"]
    d = probe_head(face_above_nozzle=1.2, overtravel=(0.0, 3.0))
    for n in ("probe", "bracket"):
        d.get(n).body = "ybody"
    assert any(set(h.data["parts"]) == {"bed", "probe"} and "toolhead_part" not in h.data for h in collisions(d))


def test_probe_face_and_trigger_keep_the_toolhead_margin():
    """E2E-X10ME1 on aluminium, 28 mm from the nozzle: 3.0 mm, short end 3.0 x 0.8 = 2.4 mm. The margin M is the
    toolhead's own stack-up between face and tip (simulated: a printed bracket on a printed head) plus the bed rise over
    28 mm: 0.381 x (1 - (1 - 56 / 200)^2) = 0.1835, + 0.5 x 0.2 x 28 / 160 = 0.0175: 0.201 mm.
      face 0.15 mm above the tip: below M (the bed rise alone is more): error, the face can meet the bed first;
      face 1.2: clear of M, shortest trigger 2.4 - 1.2 = 1.2 mm, also clear of M: no finding;
      face 2.2: shortest trigger 0.2 mm, positive but inside M: warning;
      face 2.5: shortest trigger -0.1: the existing error."""
    f, z = homing_z(probe_head(face_above_nozzle=1.2, x_probe=28.0))
    pm = z["probe_to_nozzle_margin"]
    M = pm["margin_mm"]
    assert pm["bed_rise_mm"] == pytest.approx(0.201, abs=1e-3) and pm["stackup_mm"] > 0.05 and not pm.get("assumed")
    assert M == pytest.approx(pm["stackup_mm"] + 0.201, abs=2e-3) and 0.3 < M < 1.1
    assert not f and pm["face_clear_by_mm"] == pytest.approx(1.2 - M, abs=1e-3) and pm["trigger_clear_by_mm"] == pytest.approx(1.2 - M, abs=1e-3)
    assert pm["face_window_mm"] == [M, pytest.approx(2.4 - M, abs=1e-3)]
    f, z = homing_z(probe_head(face_above_nozzle=0.15, x_probe=28.0))
    assert f["probe_face_below_nozzle_margin"].severity == "error" and f["probe_face_below_nozzle_margin"].data["needed_mm"] == pytest.approx(M, abs=0.05)
    f, z = homing_z(probe_head(face_above_nozzle=2.2, x_probe=28.0))
    assert list(f) == ["probe_trigger_margin_thin"] and f["probe_trigger_margin_thin"].severity == "warning"
    assert z["z_offset_range_mm"][0] == pytest.approx(0.2)
    f, z = homing_z(probe_head(face_above_nozzle=2.5, x_probe=28.0))
    assert f["probe_trigger_margin"].severity == "error" and "probe_trigger_margin_thin" not in f


def test_what_the_margin_leaves_the_small_sensor_on_aluminium_and_on_steel():
    """E2E-X5ME1 (M12): 1.6 mm on aluminium, short end 1.28 mm; 5 mm on steel, short end 4.0 mm. With margin M the face
    may sit from M to (short end - M) above the tip. On aluminium that window is empty when M > 0.64 mm (here M is
    about 0.9: printed bracket, 28 mm from the nozzle): a face at 1.0 mm clears the face rule but leaves 0.28 mm of
    trigger margin (warning), and 0.8 mm is below the face rule (error). On a steel bed the window is M to 4.0 - M:
    a face at 1.5 mm is clean."""
    kw = dict(model="E2E-X5ME1", clamp=(15.0, 18.0), x_probe=28.0)
    f, z = homing_z(probe_head(face_above_nozzle=1.0, **kw))
    pm = z["probe_to_nozzle_margin"]
    assert z["z_offset_range_mm"][0] == pytest.approx(0.28) and pm["face_window_mm"][1] == pytest.approx(1.28 - pm["margin_mm"], abs=1e-3)
    assert 0.64 < pm["margin_mm"] < 1.0 and list(f) == ["probe_trigger_margin_thin"]
    f, z = homing_z(probe_head(face_above_nozzle=0.8, **kw))
    assert "probe_face_below_nozzle_margin" in f
    f, z = homing_z(probe_head(face_above_nozzle=1.5, bed="steel", **kw))
    pm = z["probe_to_nozzle_margin"]
    assert not f and z["z_offset_range_mm"][0] == pytest.approx(2.5) and pm["face_window_mm"][1] == pytest.approx(4.0 - pm["margin_mm"], abs=1e-3)


# ---------------------------------------------------------------- 3. assembly time estimate
def bench_unit(declare):
    """A base plate with a post. A bracket hangs on the post's side with a cap under it: fitted to the machine the cap
    goes on from below and must be held. Declared as a bench sub-assembly the unit may be started the other way up."""
    d = Design("bench", base="plate")
    d.add("plate", Box(120, 120, 10))
    d.add("post", Pos(0, 0, 45) * Box(20, 20, 80))
    d.add("bracket", Pos(25, 0, 60) * Box(30, 20, 10))
    d.add("cap", Pos(25, 0, 50) * Box(20, 20, 10))                                         # under the bracket
    for a, b in (("post", "plate"), ("bracket", "post"), ("cap", "bracket")):
        d.join(a, b, "bonded")
    if declare:
        d.subassemblies["unit"] = ["bracket", "cap"]
    return d


def test_a_bench_subassembly_is_started_any_way_up_without_a_turn():
    """The unit (bracket + cap) on the bench: the cap sits on the bracket when the pair is built upside down. Laying
    the first part on the bench that way up is not a turn of anything: the sub-assembly's own simulation must show no
    turn and no start penalty (25 s before), the cap resting from above, not held and not from below."""
    from mechloop.assembly.simulate import T_FLIP, T_PLACE, analyse

    res = analyse(bench_unit(True))
    inner = res["subassemblies"]["unit"]
    im = inner["metrics"]
    assert im["times_assembly_is_turned"] == 0 and im["needs_holding"] == 0 and im["from_below"] == 0
    assert inner["rows"][0]["orientation"] == "-Z" and "upside down" in inner["rows"][0]["start_orientation"]
    (row,) = inner["rows"][1:]
    assert row["direction"] == "from above" and row["rests_stably"] and "turn_assembly" not in row
    assert im["estimated_time_s"] < T_FLIP and im["estimated_time_s"] == pytest.approx(T_PLACE + 3.0 * bench_unit(True).get("cap").mass(), abs=0.5)
    # the main assembly keeps its rule: it starts upright, and what is inside a sub-assembly is counted once
    assert res["rows"][0]["unit"] == "plate" and "start_orientation" not in res["rows"][0]
    assert res["metrics"]["estimated_time_s"] >= im["estimated_time_s"]


def test_score_and_assemble_give_the_same_assembly_figures():
    """`mechloop score --assembly` analyses the design after running three verifiers on it; `mechloop assemble`
    analyses it as loaded. Same design, same numbers, on the design object and through both entry points."""
    from mechloop.assembly.simulate import analyse
    from mechloop.runner import verify
    from mechloop.twin.score import _assembly

    fresh = analyse(bench_unit(True))["metrics"]
    d = bench_unit(True)
    verify(d, only=["geometry", "ratings", "fea"])
    after = _assembly(d)
    assert all(after[k] == fresh[k] for k in after), (after, fresh)
    assert after["estimated_time_min"] == fresh["estimated_time_min"] == round(fresh["estimated_time_s"] / 60.0, 1)


# ---------------------------------------------------------------- 4. provenance in the generated printer.cfg
def test_printer_cfg_states_where_the_probe_distance_comes_from():
    """printer_v5's probe is the PL-08N-class stand-in: its distance is a recalled class value and the comment must say
    so. printer_v7's is OMRON's E2E-X10ME1: the comment must name the data sheet and its chart, and must not say
    'recalled class value'."""
    from mechloop.runner import load_design

    for name, want, never in (("printer_v5", "recalled", "OMRON"), ("printer_v7", "OMRON E2E data sheet", "recalled class value")):
        d = load_design(ROOT / "designs" / f"{name}.py")
        pg = probe_geometry(d)
        cfg = klipper_config(d.electrical, d, tuning={"probe": pg})
        lines = cfg.splitlines()
        i = next(k for k, l in enumerate(lines) if l.startswith("# probe:"))
        block = "\n".join(lines[i:i + 2])
        assert lines[i + 2] == "[probe]" and lines[i + 1].startswith("# that distance: ")
        assert want in block and never not in block, block
        assert f"({pg['sensing_distance_mm']} mm)" in lines[i]
        assert pg["sources"][f"switching_distance_{pg['target']}_mm"].split(":")[0][:40] in lines[i + 1]


# ---------------------------------------------------------------- 5. the probe above a heated bed
def test_sensor_temperature_estimate_by_hand():
    """M18 barrel: face pi x 9^2 = 254.5 mm^2, side pi x 18 x 48 = 2714 mm^2. Bed 85, room 25, gap 2 mm.
    Film (85 + 25) / 2 = 55 degC. h_rad = 4 x 5.67e-8 x 0.9 x 328.15^3 = 7.21; conduction 0.0285 / 0.002 = 14.25;
    G_in = 21.46 x 254.5e-6 = 5.462e-3 W/K; G_out = 10 x 2714e-6 = 2.714e-2 W/K; f = 0.1675.
    low = 25 + 0.1675 x 60 = 35.1; high = 55 + 0.1675 x 30 = 60.0. Never above the bed nor below the room."""
    e = probe_temperature_estimate(85.0, 25.0, 2.0, math.pi * 81.0, math.pi * 18.0 * 48.0)
    assert e["fraction_of_the_way_to_the_bed"] == pytest.approx(0.1675, abs=1e-3)
    assert e["low_c"] == pytest.approx(35.1, abs=0.1) and e["high_c"] == pytest.approx(60.0, abs=0.1) and e["validated"] is False
    for bed in (40.0, 85.0, 120.0):
        for gap in (0.1, 2.0, 20.0):
            x = probe_temperature_estimate(bed, 25.0, gap, 254.5, 2714.0)
            assert 25.0 <= x["low_c"] <= x["high_c"] <= bed
    assert probe_temperature_estimate(20.0, 25.0, 2.0, 254.5, 2714.0)["high_c"] == 25.0


def hot_bed_design(model, bed_c):
    d = probe_head(model, face_above_nozzle=1.8, clamp=(22.0, 25.0) if "10" in model else (15.0, 18.0))
    tpl = d.get("probe").ratings["electrical"]
    el = d.electrical = Electrical()
    el.add(Device("board", "board", "board", {"Z-STOP": Port("Z-STOP", "endstop_in", "JST-XH", 3.0, "PC2", 3,
                                                               extra={"logic_v": 3.3, "pin_max_v": 3.6})}))
    el.add(Device("probe", "probe", "probe", {"out": Port("out", "probe", "JST-XH", 1.0, None, tpl["ports"]["out"]["conductors"])},
                  dict(tpl["ratings"]), dict(tpl["sources"]), {"supply_v": 24.0, "series_diode": True,
                                                                "interface": {"part": "x", "load_ohm": 4700.0}}, dict(tpl["product"])))
    el.wire("probe", "board.Z-STOP", "probe.out", 26, conductors=3)
    el.hot_parts = {"bed": bed_c}
    return d


def hot_bed(model, bed_c, with_design=True):
    d = hot_bed_design(model, bed_c)
    r, m = VerifierResult("electrical"), {}
    VE._probe({"el": d.electrical, "design": d if with_design else None}, r, m)
    return [f for f in r.findings if f.code == "probe_near_hot_bed"], m["probe"]["probe"]


def test_probe_near_hot_bed_uses_the_estimate_with_a_margin():
    """OMRON's sheet: DC three-wire types -40 to 85 degC ambient (E2E-X10ME1), the DC two-wire E2E-X8MD1 -25 to 70.
    The check holds the HIGH end of the estimate plus 10 K against the rating (it was: bed above rating, no margin).
      three-wire, rated 85, bed 85: sensor up to 60 degC (by hand above, gap 1.8 + 0.2), margin 25 K: no warning,
        and now for a stated reason. The old rule also passed, at a margin of 0.
      three-wire, bed 120: high (120 + 25) / 2 + 0.17 x 47.5 = 80.5; 80.5 + 10 > 85: warning.
      two-wire, rated 70, bed 100 (printer_v6's case): M12 face 113 mm^2, side pi x 12 x 40: high about 68: warning.
      two-wire, rated 70, bed 70: high about 51: no warning.
    Without geometry the estimate cannot be made: the bed temperature is held against the rating less the margin, so
    85 over 85 warns (it did not before) and 75 over 85 does not."""
    assert PROBE_THERMAL["margin_k"] == 10.0
    w, row = hot_bed("E2E-X10ME1", 85.0)
    assert not w and row["max_ambient_c"] == 85.0 and row["sensor_temperature_estimate"]["high_c"] == pytest.approx(60.0, abs=0.2)
    assert row["thermal_margin_k"] == pytest.approx(25.0, abs=0.2) and row["thermal_margin_required_k"] == 10.0
    w, row = hot_bed("E2E-X10ME1", 120.0)
    assert len(w) == 1 and w[0].severity == "warning" and row["sensor_temperature_estimate"]["high_c"] == pytest.approx(80.5, abs=0.5)
    w, row = hot_bed("E2E-X8MD1", 100.0)
    assert len(w) == 1 and row["max_ambient_c"] == 70.0 and 60.0 < row["sensor_temperature_estimate"]["high_c"] <= 70.0
    w, row = hot_bed("E2E-X8MD1", 70.0)
    assert not w and row["thermal_margin_k"] > 10.0
    w, row = hot_bed("E2E-X10ME1", 85.0, with_design=False)
    assert len(w) == 1 and row["sensor_temperature_estimate"] is None and row["thermal_margin_k"] == 0.0
    w, row = hot_bed("E2E-X10ME1", 75.0, with_design=False)
    assert not w


def test_drift_figure_widens_when_the_sensor_may_pass_70_degc():
    """E2E three-wire: +/-10 % of the sensing distance up to 70 degC, +/-15 % over the whole range to 85 (sheet p.16).
    Bed 85: sensor at most 60 degC: 10 %, short end 3.0 x 0.8 - 1.8 = 0.6 mm. Bed 120: sensor up to 80.5 degC: 15 %,
    short end 3.0 x 0.75 - 1.8 = 0.45 mm."""
    assert probe_omron_e2e("E2E-X10ME1").ratings["electrical"]["ratings"]["temperature_drift_full_range_frac"] == 0.15
    assert "temperature_drift_full_range_frac" not in probe_omron_e2e("E2E-X8MD1").ratings["electrical"]["ratings"]
    pg = probe_geometry(hot_bed_design("E2E-X10ME1", 85.0))
    assert pg["temperature_drift_frac"] == 0.10 and pg["z_offset_range_mm"][0] == pytest.approx(0.6)
    pg = probe_geometry(hot_bed_design("E2E-X10ME1", 120.0))
    assert pg["temperature_drift_frac"] == 0.15 and pg["z_offset_range_mm"][0] == pytest.approx(0.45) and "full range" in pg["temperature_drift_basis"]


# ---------------------------------------------------------------- 6. --out is a root; a missing report is said aloud
def stiff_printer():
    d = probe_head()
    d.name = "stiffy"
    d.printer["stiffness"] = {"x": "nozzle_x", "y": "nozzle_y"}
    return d


def test_missing_verify_report_is_named_and_a_nested_out_folder_is_explained(tmp_path):
    """verify --out <root>/stiffy writes <root>/stiffy/stiffy/report.json. Looking under <root> then finds nothing: the
    fall-back must name the file it looked for and point at the nested one. With the report where it belongs there is
    no warning and the stiffness is used."""
    from mechloop.twin.tuning import missing_report_warning, pm_for_detail

    d = stiff_printer()
    root = tmp_path / "out"
    nested = root / "stiffy" / "stiffy"
    nested.mkdir(parents=True)
    rep = {"metrics": {"fea": {"nozzle_x": {"stiffness_low_n_per_mm": 1500.0, "stiffness_n_per_mm": 2000.0},
                               "nozzle_y": {"stiffness_low_n_per_mm": 2000.0, "stiffness_n_per_mm": 2400.0}}}}
    (nested / "report.json").write_text(json.dumps(rep))
    pm, src, tried = pm_for_detail(d, str(root))
    assert src is None and not pm.struct_stiffness
    assert tried[0]["path"] == str(root / "stiffy" / "report.json") and tried[0]["status"] == "not found"
    assert str(nested / "report.json") in tried[0]["hint"]
    msg = missing_report_warning(d, tried)
    assert msg.startswith("WARNING") and str(root / "stiffy" / "report.json") in msg and "belt stiffness only" in msg and "ROOT" in msg
    (root / "stiffy" / "report.json").write_text(json.dumps(rep))
    pm, src, tried = pm_for_detail(d, str(root))
    assert src == str(root / "stiffy" / "report.json") and pm.struct_stiffness and tried == []
    (root / "stiffy" / "report.json").write_text(json.dumps({"metrics": {}}))             # a partial run: no FEA figures
    pm, src, tried = pm_for_detail(d, str(root))
    assert src is None and "no FEA frame stiffness" in tried[0]["status"]


def test_cli_documents_out_and_warns_when_it_ends_in_the_design_name(capsys):
    from mechloop import cli

    for cmd in ("verify", "score", "tune", "assemble"):
        with pytest.raises(SystemExit):
            cli.main([cmd, "--help"])
        h = " ".join(capsys.readouterr().out.split())
        assert "ROOT folder" in h and "<out>/<design name>/" in h, cmd
    cli._warn_nested_out("out/printer_v7", "printer_v7")
    err = capsys.readouterr().err
    assert "WARNING" in err and str(Path("out/printer_v7") / "printer_v7") in err
    cli._warn_nested_out("out", "printer_v7")
    assert capsys.readouterr().err == ""


def test_tune_says_aloud_that_it_fell_back_to_belt_stiffness(tmp_path, monkeypatch, capsys):
    """`mechloop tune` with no verify report under its --out: the result carries the warning and it is printed on
    stderr, naming the report it looked for. (Klipper is stubbed out: only the report lookup is under test.)"""
    from mechloop.twin import firmware as fw
    from mechloop.twin import tuning

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(fw, "find_klipper", lambda: (None, None, "stub"))
    monkeypatch.setattr(tuning, "load_design", lambda p: stiff_printer(), raising=False)
    import mechloop.runner as runner

    monkeypatch.setattr(runner, "load_design", lambda p: stiff_printer())
    res = tuning.tune_report("stiffy.py", str(tmp_path / "o"), only=["none"])
    err = capsys.readouterr().err
    want = str(tmp_path / "o" / "stiffy" / "report.json")
    assert res["warnings"] and want in res["warnings"][0] and want in err and err.startswith("WARNING")
    assert res["verify_reports_looked_for"][0] == {"path": want, "status": "not found"}
    assert "belt stiffness only" in res["frame_stiffness_from"]
