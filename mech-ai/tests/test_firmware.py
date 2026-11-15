"""Firmware in the loop: decoding Klipper's command stream, and a real offline Klipper run when it is installed."""
import json
from pathlib import Path

import numpy as np
import pytest

from mechloop.twin import firmware as fw

CFG = """
[stepper_x]
step_pin: PB13
rotation_distance: 40
microsteps: 16
[stepper_y]
step_pin: PB10
rotation_distance: 40
microsteps: 16
[stepper_z]
step_pin: PB0
rotation_distance: 2
microsteps: 16
"""
HZ = 64_000_000.0


def _dump(tmp_path, lines):
    head = ["config_stepper oid=0 step_pin=PB13 dir_pin=PB12 invert_step=-1 step_pulse_ticks=0",
            "config_stepper oid=1 step_pin=PB10 dir_pin=PB2 invert_step=-1 step_pulse_ticks=0",
            "config_stepper oid=2 step_pin=PB0 dir_pin=PC5 invert_step=-1 step_pulse_ticks=0"]
    p = tmp_path / "commands.txt"
    p.write_text("\n".join(head + lines) + "\n")
    return p


def test_queue_step_is_decoded_with_interval_count_and_add(tmp_path):
    # 4 steps: intervals 1000, 1100, 1200, 1300 ticks, then direction reversed for 2 steps
    d = fw.decode(_dump(tmp_path, ["queue_step oid=0 interval=1000 count=4 add=100", "set_next_step_dir oid=0 dir=0",
                                   "queue_step oid=0 interval=500 count=2 add=0",
                                   "queue_step oid=1 interval=64000 count=1 add=0", "queue_step oid=2 interval=64000 count=1 add=0"]),
                  CFG, HZ)
    t, n = d["steps"][0]
    assert np.allclose(t * HZ, [1000, 2100, 3300, 4600, 5100, 5600])
    assert n.tolist() == [1, 2, 3, 4, 3, 2]


def test_a_z_step_after_a_pause_longer_than_the_clock_is_placed_by_its_position_in_the_stream(tmp_path):
    wrap = 1 << 32
    # X steps steadily for 100 s except for a 0.2 s gap at 80 s; the Z move really happens in that gap, but its
    # 32-bit interval has wrapped once and reads as 80 s - 67.1 s
    # Klipper writes commands in the order of the clock they are wanted at: the far Z step (wanted at its own time,
    # 80.05 s) comes after the X command that began at 80.0 s and before the one that begins at 80.2 s
    lines = ["queue_step oid=1 interval=64000 count=1 add=0",
             "queue_step oid=0 interval=64000 count=60000 add=0", "queue_step oid=0 interval=64000 count=19999 add=0",
             "queue_step oid=0 interval=12864000 count=1 add=0",
             f"queue_step oid=2 interval={int(80.05 * HZ) - wrap} count=1 add=0", "queue_step oid=2 interval=6400 count=50 add=0",
             "queue_step oid=0 interval=64000 count=19000 add=0"]
    d = fw.decode(_dump(tmp_path, lines), CFG, HZ)
    tz = d["steps"][2][0]
    assert d["clock_wraps_resolved"]["Z"] == 1
    assert abs(tz[0] - 80.05) < 1e-6 and 80.0 < tz[-1] < 80.2


def _klipper():
    try:
        return fw.find_klipper()
    except fw.FirmwareNotAvailable as e:
        pytest.skip(f"Klipper is not installed (tools/setup_klipper.sh): {e}")


def test_real_klipper_prints_a_small_part_on_printer_v4_and_stays_on_the_gcode_path(tmp_path):
    _klipper()
    from build123d import Box, Pos

    from mechloop.runner import load_design
    from mechloop.twin import printer_map_for, run_print

    d = load_design(Path(__file__).parent.parent / "designs" / "printer_v4.py")
    rep = run_print(d, Pos(0, 0, 1) * Box(10, 10, 2), tmp_path, printer_map_for(d), name="chip", render=False,
                    collisions=False, firmware="klipper")
    assert rep["ok"], json.dumps(rep["findings"])[:800]
    f = rep["firmware"]
    assert f["firmware"] == "Klipper" and not f["klipper_messages"]
    assert f["max_distance_from_gcode_path_mm"] < 0.1
    assert f["peak_speed_mm_s"][0] <= 250 * 1.02 and max(f["peak_step_rate_hz"].values()) < f["mcu_step_rate_limit_hz"]
    assert rep["print"]["outline_iou_mean"] > 0.95


def test_without_klipper_the_print_is_an_error_not_a_pass(tmp_path, monkeypatch):
    monkeypatch.setenv("MECHLOOP_KLIPPER", str(tmp_path / "nowhere"))
    from build123d import Box, Pos

    from mechloop.runner import load_design
    from mechloop.twin import printer_map_for, run_print

    d = load_design(Path(__file__).parent.parent / "designs" / "printer_v4.py")
    rep = run_print(d, Pos(0, 0, 1) * Box(10, 10, 2), tmp_path, printer_map_for(d), name="chip", render=False,
                    collisions=False, firmware="klipper")
    assert not rep["ok"] and rep["findings"][0]["code"] == "firmware_not_run"


# ---------------------------------------------------------------- input shaper, pressure advance, probe and bed mesh
@pytest.fixture(scope="module")
def v5():
    _klipper()
    from mechloop.runner import load_design
    from mechloop.twin import printer_map_for

    d = load_design(Path(__file__).parent.parent / "designs" / "printer_v5.py")
    return d, printer_map_for(d)


def _sections(cfg):
    c = fw._cfg(cfg)
    return c, set(c.sections())


def test_generated_config_has_shaper_pressure_advance_probe_and_mesh_and_klippy_loads_it(v5, tmp_path):
    from mechloop.electrical import klipper_config
    from mechloop.twin.tuning import firmware_tuning

    d, pm = v5
    cfg = klipper_config(d.electrical, d, tuning=firmware_tuning(d, pm))
    c, secs = _sections(cfg)
    assert {"input_shaper", "probe", "safe_z_home", "bed_mesh", "extruder"} <= secs
    assert c.get("stepper_z", "endstop_pin") == "probe:z_virtual_endstop" and not c.has_option("stepper_z", "position_endstop")
    assert c.get("probe", "pin") == "^!PC2"                      # NPN normally open: board pull-up, active low
    assert c.getfloat("probe", "x_offset") == 33.0 and c.getfloat("probe", "y_offset") == 0.0
    assert abs(c.getfloat("probe", "z_offset") - 0.1) < 1e-9     # 3.2 mm switching distance, face 3.1 mm above the nozzle
    assert c.get("bed_mesh", "mesh_min") == "33, 0" and c.get("bed_mesh", "mesh_max") == "182, 180"
    assert 0.0 < c.getfloat("extruder", "pressure_advance") < 0.2 and c.getfloat("extruder", "max_extrude_only_distance") > 0
    for ax, lo, hi in (("x", 60.0, 130.0), ("y", 45.0, 90.0)):   # at or above the axis's own resonance, by shaper type
        assert lo < c.getfloat("input_shaper", f"shaper_freq_{ax}") < hi
        assert c.get("input_shaper", f"shaper_type_{ax}") in ("zv", "mzv", "ei", "2hump_ei", "3hump_ei")
    chk = fw.check_config(cfg, tmp_path / "chk")
    assert chk["ran"] and chk["ok"], chk
    # a configuration klippy must refuse is reported as refused, not as checked
    bad = fw.check_config(cfg.replace("shaper_type_x: ", "shaper_type_x: no_such_"), tmp_path / "bad")
    assert bad["ran"] and not bad["ok"] and bad["error"]


def test_v4_with_its_z_microswitch_still_gets_a_plain_endstop_and_no_probe_sections(tmp_path):
    _klipper()
    from mechloop.electrical import klipper_config, probe_geometry
    from mechloop.runner import load_design

    d = load_design(Path(__file__).parent.parent / "designs" / "printer_v4.py")
    assert probe_geometry(d) is None
    cfg = klipper_config(d.electrical, d)
    c, secs = _sections(cfg)
    assert not ({"probe", "safe_z_home", "bed_mesh"} & secs) and "input_shaper" in secs
    assert c.get("stepper_z", "endstop_pin") == "^PC2" and c.has_option("stepper_z", "position_endstop")
    chk = fw.check_config(cfg, tmp_path / "chk")
    assert chk["ran"] and chk["ok"], chk


def _chip(v5, out, opts, pm=None, **kw):
    from build123d import Box, Pos

    from mechloop.twin import run_print

    d, pm0 = v5
    return run_print(d, Pos(0, 0, 1) * Box(12, 12, 2), out, pm or pm0, name="chip", render=False, collisions=False,
                     firmware="klipper", firmware_opts=opts, **kw)


def test_klipper_shapes_the_steps_and_the_twin_follows_them(v5, tmp_path):
    plain = _chip(v5, tmp_path / "plain", {"input_shaper": False, "pressure_advance": False}, accel_scale=3.0, speed_scale=2.0)
    shaped = _chip(v5, tmp_path / "shaped", {"input_shaper": True, "pressure_advance": False}, accel_scale=3.0, speed_scale=2.0)
    assert plain["ok"] and shaped["ok"], json.dumps(plain["findings"] + shaped["findings"])[:800]
    fp, fs = plain["firmware"], shaped["firmware"]
    assert fp["klipper_runs"] == 1 and fp["features"]["input_shaper"] is None
    assert fs["klipper_runs"] == 2 and fs["features"]["input_shaper"]["y"]["shaper_freq"] > 0
    assert fs["what_if"]["max_accel"] == 3.0 * 4000.0
    # shaping moves the commanded position off the planned one by a fraction of a millimetre, and only in X and Y
    gx, gy, gz = fs["features"]["largest_gap_between_commanded_and_planned_mm"]
    assert 0.01 < max(gx, gy) < 0.6 and gz < 0.002          # Z: within the interpolation of one 0.6 um step
    assert fp["features"]["largest_gap_between_commanded_and_planned_mm"] == [0.0, 0.0, 0.0]
    assert abs(fs["print_time_s"] - fp["print_time_s"]) < 0.2            # it does not change the plan's timing
    assert shaped["dynamics"]["cross_track_worst_mm"] < plain["dynamics"]["cross_track_worst_mm"]
    assert shaped["dynamics"]["cross_track_rms_mm"] < plain["dynamics"]["cross_track_rms_mm"]


def test_pressure_advance_reaches_the_extruder_steps_and_shrinks_the_corner_bulge(v5, tmp_path):
    from dataclasses import replace

    d, pm = v5
    pm = replace(pm, raster_px_per_mm=40)
    off = _chip(v5, tmp_path / "off", {"input_shaper": False, "pressure_advance": False}, pm)
    on = _chip(v5, tmp_path / "on", {"input_shaper": False, "pressure_advance": 0.045}, pm)
    assert off["ok"] and on["ok"]
    assert on["firmware"]["features"]["pressure_advance"] == 0.045 and off["firmware"]["features"]["pressure_advance"] is None
    for r in (off, on):                                                  # the filament total is unchanged by it
        assert abs(r["firmware"]["filament_commanded_mm"] - r["firmware"]["filament_in_gcode_mm"]) < 0.05
    assert on["print"]["max_bulge_mm"] <= off["print"]["max_bulge_mm"] - 0.1


def test_a_tilted_bed_is_followed_through_klippers_mesh_and_not_without_it(v5, tmp_path):
    from dataclasses import replace

    from mechloop.electrical import probe_geometry
    from mechloop.twin.tuning import measure_mesh

    d, pm = v5
    pm = replace(pm, bed_surface={"tilt_x_mm": 0.5, "tilt_y_mm": -0.3})          # a plane: no bow
    pg = {**probe_geometry(d), "repeatability_mm": 0.0}                          # an ideal probe, for a known answer
    prof = measure_mesh(d, pm, pg)
    assert abs(prof["range_mm"] - (0.5 * 149 / 220 + 0.3 * 180 / 220)) < 1e-3   # the plane over the probed area
    kw = dict(at=(40.0, -40.0))
    flat = _chip(v5, tmp_path / "off", {"input_shaper": False, "pressure_advance": False, "bed_mesh": False}, pm, **kw)
    mesh = _chip(v5, tmp_path / "on", {"input_shaper": False, "pressure_advance": False, "bed_mesh": prof}, pm, **kw)
    g0, g1 = flat["print"]["first_layer_gap_error_mm"], mesh["print"]["first_layer_gap_error_mm"]
    expect = 0.5 * 40 / 220 + 0.3 * 40 / 220                                     # bed height at the part: 0.145 mm
    assert abs(abs(g0["mean"]) - expect) < 0.02 and flat["print"]["first_layer_nozzle_height_mm"] < 0.08
    assert mesh["ok"], json.dumps(mesh["findings"])[:600]
    assert g1["worst"] < 0.015                                                   # one mesh step (0.01) and a Z step
    assert mesh["firmware"]["features"]["bed_mesh"]["z_adjust_applied_mm"][1] > 0.1
    assert mesh["firmware"]["max_distance_from_gcode_path_mm"] < 0.1
