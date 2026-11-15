"""Homing, cables and printer essentials."""
from build123d import Box, Location, Pos

from mechloop.model import Cable, Design, Joint
from mechloop.parts import endstop_switch, place
from mechloop.verifiers.subsystems import verify_subsystems


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


def axis(flag_x, yz=(0.0, 30.0)):
    """A carriage on a slide. The switch is on the frame; a flag on the carriage should press it at x = -50."""
    d = Design("ax")
    d.add("rail", Box(200, 10, 10))
    d.add("car", Pos(0, 0, 15) * Box(30, 30, 20), body="car")
    d.add("flag", Pos(flag_x, yz[0], yz[1]) * Box(4, 10, 10), body="car")
    # switch on a post at the -X end, lever facing +X: turned so that its -Y push direction points along -X
    # (until 2026-11-15 this rig had the switch the other way round, lever pressed towards +X, and still passed)
    d.add("post", Pos(-80, 0, 20) * Box(10, 20, 50))
    sw = place(d, "sw", endstop_switch(), Location((-70.0, 0, 26), (90, 0, -90)))
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50), max_effort=10))
    d.endstops.append({"joint": "x", "switch": "sw", "at": "min"})
    return d, sw.meta["interfaces"]


def test_endstop_is_pressed_only_when_the_flag_reaches_it():
    d, itf = axis(0)
    trig, latest = itf["trigger"][0], itf["trigger_latest"][0]
    assert latest[0] == trig[0] - 1.5                 # the lever is pressed along -X; a late unit operates 1.5 mm further in
    # put the flag so its -X face is at the switch's LATEST operating position when the carriage is at -50
    # (the trigger is the lever's operating position at its tip, which is off the switch's centre line)
    d, _ = axis(latest[0] + 50 + 2.0, trig[1:])
    assert errs(verify_subsystems(d)) == []
    d, _ = axis(trig[0] + 50 + 2.0, trig[1:])         # flag at the nominal operating position: late units are never pressed
    r = verify_subsystems(d)
    assert errs(r) == ["endstop_not_reached"] and abs(r.metrics["homing"]["x"]["short_of_latest_operating_position_mm"] - 1.5) < 0.01
    d, _ = axis(trig[0] + 50 + 12.0, trig[1:])        # flag 10 mm short: never pressed
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


# ---------------------------------------------------------------- bed probe
def probe_rig(face_above_nozzle=1.5, bed_material="al6061", probe_x=30.0, z_top=0.0, sn_al=3.2):
    """A bed that rises to a fixed nozzle, with an inductive probe beside the nozzle. Nozzle tip at z = 100; with the
    Z joint at its upper end the bed surface is z_top below... above the nozzle plane by -z_top (0 = touching)."""
    from mechloop.parts import Stock
    from mechloop.parts.electrical import inductive_probe_template

    d = Design("probe_rig")
    d.add("frame", Pos(0, 0, 150) * Box(300, 300, 10))
    d.add("bed", Pos(0, 0, 47) * Box(200, 200, 6), material=bed_material, body="zbody")       # top at z = 50
    d.add("head", Pos(0, 0, 120) * Box(30, 30, 30), body="xbody")
    probe = Stock(Pos(0, 0, 18) * Box(18, 18, 36), "PROBE-INDUCTIVE-8MM", "test probe", 0.02, material="abs",
                  ratings={"electrical": inductive_probe_template(sn_aluminium_mm=sn_al)}, interfaces={"sensing_face": [(0.0, 0.0, 0.0)]})
    place(d, "probe", probe, Location((probe_x, 0, 100 + face_above_nozzle)), body="xbody")
    d.joints += [Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-90, 90), max_effort=10),
                 Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-90, 90), max_effort=10),
                 Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(0, 50 - z_top), max_effort=10)]
    d.tool_point = ("xbody", (0.0, 0.0, 100.0))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z"}
    d.endstops += [{"joint": "x", "sensorless": True}, {"joint": "y", "sensorless": True}, {"joint": "z", "probe": "probe"}]
    return d


def probe_findings(d):
    r = verify_subsystems(d)
    return {f.code: f for f in r.findings if f.code.startswith(("probe", "bed_mesh"))}, r.metrics["homing"]["z"]


def test_probe_offsets_and_z_offset_come_from_the_geometry_and_the_sensing_distance():
    f, z = probe_findings(probe_rig(face_above_nozzle=1.5, z_top=-0.5))
    assert not [c for c, x in f.items() if x.severity == "error"], list(f)
    assert z["x_offset"] == 30.0 and z["y_offset"] == 0.0
    assert z["z_offset"] == 1.7                          # switches 3.2 from the bed; face 1.5 above the nozzle
    assert z["z_offset_range_mm"] == [1.38, 2.02]        # +/-10 % of 3.2
    # nozzle travel is 0..180 in machine coordinates, the bed 200 wide and centred on it (-10..190); the probe sits 30
    # to the right and is kept 18 inside the plate edge: X 30..172, Y 8..172 (limited by the plate, then by travel)
    assert z["mesh_min"] == [30.0, 8.0] and z["mesh_max"] == [172.0, 172.0]
    assert z["home_xy"] == [60.0, 90.0] and z["home_probe_xy"] == [90.0, 90.0]
    assert f["bed_mesh_does_not_cover_print_area"].severity == "warning" and z["unprobed_strip_mm"]["x_low"] == 30.0


def test_probe_that_switches_too_close_to_the_bed_is_an_error():
    # face 3.1 above the nozzle: switches with the nozzle 0.1 above the bed; a short-range unit lets the nozzle touch first
    f, z = probe_findings(probe_rig(face_above_nozzle=3.1, z_top=-0.5))
    assert z["z_offset"] == 0.1 and f["probe_trigger_margin"].severity == "error"
    # face above the nozzle by more than the switching distance: the nozzle always touches first
    f, _ = probe_findings(probe_rig(face_above_nozzle=4.0, z_top=-0.5))
    assert f["probe_triggers_after_nozzle_touches"].severity == "error"


def test_probe_must_be_reached_within_z_travel_and_must_sense_the_bed_material():
    # Z travel stops with the nozzle 2 mm above the bed; the probe needs it at 1.38..2.02
    f, _ = probe_findings(probe_rig(face_above_nozzle=1.5, z_top=2.0))
    assert f["probe_not_reached"].severity == "error"
    f, _ = probe_findings(probe_rig(face_above_nozzle=1.5, z_top=-0.5, bed_material="petg"))
    assert f["probe_cannot_sense_bed"].severity == "error"
    # a probe so far to the side that it is never over the plate inside the travel
    f, _ = probe_findings(probe_rig(face_above_nozzle=1.5, z_top=-0.5, probe_x=185.0))
    assert f["probe_cannot_reach_bed"].severity == "error"
