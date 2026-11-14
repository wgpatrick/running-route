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


def test_a_z_move_after_a_pause_longer_than_the_clock_is_put_in_the_xy_gap(tmp_path):
    wrap = 1 << 32
    # X steps steadily for 100 s except for a 0.2 s gap at 80 s; the Z move really happens in that gap, but its
    # 32-bit interval has wrapped once and reads as 80 s - 67.1 s
    lines = ["queue_step oid=0 interval=64000 count=60000 add=0", "queue_step oid=0 interval=64000 count=19999 add=0",
             "queue_step oid=0 interval=12864000 count=1 add=0", "queue_step oid=0 interval=64000 count=19000 add=0",
             "queue_step oid=1 interval=64000 count=1 add=0",
             f"queue_step oid=2 interval={int(80.05 * HZ) - wrap} count=1 add=0", "queue_step oid=2 interval=6400 count=50 add=0"]
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
