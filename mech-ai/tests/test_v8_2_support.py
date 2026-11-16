"""Small checks for the support code added with printer_v8_2: countersunk screws, Klipper sections for extra steppers and
[z_tilt], and the per-board Klipper dictionary."""
from pathlib import Path

import pytest

from mechloop import parts as P
from mechloop.electrical import check_klipper_config
from mechloop.twin.firmware import FirmwareNotAvailable, mcu_dictionary


def test_countersunk_screw_head_is_flush_at_z0_and_cone_shaped():
    s = P.fhcs("M5", 16)
    bb = s.shape.bounding_box()
    assert s.sku == "FHCS-M5x16" and bb.max.Z == pytest.approx(0.0, abs=1e-6) and bb.min.Z == pytest.approx(-16.0)
    assert bb.max.X - bb.min.X == pytest.approx(P.CSK["M5"][1]) and s.interfaces["head"] == "countersunk"
    assert s.interfaces["head_below_surface"] == pytest.approx((11.2 - 9.43) / 2, abs=0.01)
    with pytest.raises(ValueError):
        P.fhcs("M8", 20)


CFG = """[mcu]
serial: /dev/ttyAMA0
[printer]
kinematics: cartesian
max_velocity: 200
max_accel: 3000
[stepper_z]
step_pin: PF11
dir_pin: PG3
enable_pin: !PG5
microsteps: 16
rotation_distance: 2
endstop_pin: probe:z_virtual_endstop
position_max: 180
[stepper_z1]
step_pin: PG4
dir_pin: PC1
enable_pin: !PA0
microsteps: 16
rotation_distance: 2
[z_tilt]
z_positions:
    90, 282.75
    -70, 1.75
    250, 1.75
points:
    90, 170
    15, 5
    165, 5
"""


def test_extra_stepper_needs_no_endstop_or_position_max_and_z_tilt_is_known():
    probs = check_klipper_config(CFG, {"PF11", "PG3", "PG5", "PG4", "PC1", "PA0"}, set())
    assert not [p for p in probs if "stepper_z1" in p or "z_tilt" in p], probs
    bad = check_klipper_config(CFG.replace("rotation_distance: 2\n[z_tilt]", "[z_tilt]"), {"PF11", "PG3", "PG5", "PG4", "PC1", "PA0"}, set())
    assert any("[stepper_z1]: missing rotation_distance" in p for p in bad)
    assert any("[z_tilt]: missing points" in p for p in check_klipper_config(CFG.split("points:")[0], set(), set()))


def test_klipper_dictionary_follows_the_board_mcu(tmp_path):
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "klipper.dict").write_text("{}")
    assert mcu_dictionary("[mcu]\nserial: x\n", tmp_path) == tmp_path / "out" / "klipper.dict"
    with pytest.raises(FirmwareNotAvailable):
        mcu_dictionary("[mcu]\n# klipper_mcu: stm32f446\n", tmp_path)
    (tmp_path / "out_stm32f446").mkdir()
    (tmp_path / "out_stm32f446" / "klipper.dict").write_text("{}")
    assert mcu_dictionary("[mcu]\n# klipper_mcu: stm32f446\n", tmp_path) == tmp_path / "out_stm32f446" / "klipper.dict"
    assert P.octopus_v11().ratings["electrical"]["ratings"]["klipper_mcu"] == "stm32f446"
