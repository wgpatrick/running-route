"""Electrical model and verifier: physics against closed forms and published data, then one passing rig and one
injected fault per check. No full printer is verified here (that is designs/printer_v4.py through the CLI)."""
import json
import math
from pathlib import Path

import numpy as np
import pytest
from build123d import Box, Location, Pos

import mechloop.electrical as E
import mechloop.verifiers.electrical as VE
from mechloop.electrical import Bay, Device, Electrical, Port
from mechloop.model import Design, Joint
from mechloop.parts import nema17, place
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       heater_cartridge, iec_inlet_c14, psu_for_load, psu_lrs, raspberry_pi_zero2w,
                                       relay_btt_v12, skr_mini_e3_v3, thermal_fuse, thermistor_cartridge)


# ------------------------------------------------------------------ physics
def test_thermal_model_matches_first_order_rc():
    """One node, fixed conductance to ambient: T(t) = Ta + P/G (1 - exp(-t G/C))."""
    C, G, P, Ta = 12.0, 0.08, 30.0, 25.0
    net = E.ThermalNet([E.ThermalNode("block", C, g_ambient=G)], [], Ta)
    plant = E.HeaterPlant("rc", net, "block", "block", "block", P)
    r = E.simulate_heater(plant, {}, 200.0, 600.0, duty_override=1.0)
    exact = Ta + P / G * (1 - np.exp(-r["t"] * G / C))
    assert np.abs(r["T"] - exact).max() < 0.5          # implicit Euler at 0.1 s on a 150 s time constant
    assert abs(net.steady(np.array([P]))[0] - (Ta + P / G)) < 0.01


def test_two_node_network_conserves_energy():
    net = E.ThermalNet([E.ThermalNode("a", 5.0), E.ThermalNode("b", 20.0)], [("a", "b", 3.0)], 20.0)
    T = net.start()
    for _ in range(2000):
        T = net.step(T, np.array([10.0, 0.0]), 0.1)
    assert abs((5.0 * (T[0] - 20) + 20.0 * (T[1] - 20)) - 10.0 * 200.0) < 1e-6      # no path to ambient: all heat stored
    assert abs((T[0] - T[1]) - 10.0 * 20.0 / 25.0 / 3.0) < 0.01                     # quasi-steady split across the link


def test_hotend_model_against_published_figures():
    """Marlin's MPC example hotend (Configuration.h): 40 W, 16.7 J/K, 0.068 W/K. Closed form to 200 degC from 25:
    86 s, i.e. 'a minute or two', which is what a V6-class hotend takes. The catalog cartridge's own plant must land
    in the same range."""
    net = E.ThermalNet([E.ThermalNode("block", 16.7, g_ambient=0.068)], [], 25.0)
    t = E.heater_characteristics(E.HeaterPlant("mpc", net, "block", "block", "block", 40.0), [200.0], 400.0)["heatup_s"][200.0]
    assert abs(t - (-16.7 / 0.068 * math.log(1 - 175 * 0.068 / 40.0))) < 1.5
    d = rig()
    plant = E.thermal_plants(d)["extruder"]
    t30 = E.heater_characteristics(plant, [200.0], 600.0)["heatup_s"][200.0]
    assert 45.0 < t30 < 180.0


def test_stepper_curve_matches_vendor_pull_out_curve():
    """StepperOnline 17HS13-0404S, published 24 V pull-out curve at 0.35 A rms (vendor/stepperonline_nema17.json)."""
    rec = json.loads((Path(E.__file__).parent / "parts/vendor/stepperonline_nema17.json").read_text())["parts"]["34"]
    v, pts = rec["values"], rec["pull_out_torque_curve"]["points_rpm_nmm"]
    pts = [p for p in pts if 120 <= p[0] <= 900]
    model = E.stepper_torque_curve(v["holding_torque_nm"], v["rated_current_a"], v["phase_resistance_ohm"],
                                   v["phase_inductance_mh"] * 1e-3, 0.35, 24.0, [p[0] for p in pts]) * 1e3
    err = np.abs(model - np.array([p[1] for p in pts])) / np.array([p[1] for p in pts])
    assert err.max() < 0.13, err


def test_wire_and_thermistor():
    assert abs(E.awg_area_mm2(18) - 0.823) < 0.01 and abs(E.wire_resistance(18, 1000.0) - 0.0209) < 0.0005
    amp = E.wire_ampacity(18, 2.1, 30.0, 90.0)           # chassis-wiring tables give 16 A for AWG 18
    assert 12.0 < amp < 20.0
    assert E.wire_ampacity(18, 2.1, 30.0, 90.0, n_loaded=6) < 0.6 * amp
    assert abs(E.wire_temperature(amp, 18, 2.1, 30.0) - 90.0) < 0.5
    th = E.Thermistor(THERMISTORS["ATC Semitec 104NT-4-R025H42G"])
    for t in (25.0, 160.0, 250.0):
        assert abs(th.temp_from_adc(th.adc(t)) - t) < 1e-6
    assert abs(th.resistance(160.0) - 1074.0) < 1.0
    assert th.deg_per_count(250.0) < 0.5 < th.deg_per_count(295.0)
    assert psu_for_load(150.0) == "LRS-200-24" and psu_for_load(250.0) == "LRS-350-24"


def test_verify_heater_port_trips_like_klipper():
    vh = E._VerifyHeater(check_gain_time=20.0)
    assert not any(vh.check(t, 25.0 + 3.0 * t, 250.0) for t in range(60))          # heating normally
    vh = E._VerifyHeater(check_gain_time=20.0)
    trips = [t for t in range(60) if vh.check(float(t), 25.0, 250.0)]              # never warms up
    assert trips and 20 <= trips[0] <= 22


# ------------------------------------------------------------------ a small complete rig
def rig(psu="LRS-350-24", bed_awg=16, thermistor=True, runaway=True, cutoffs=True, loom_y=60.0, loom_z=10.0, run=0.3,
        custom_board=False):
    d = Design("rig")
    d.add("base", Pos(0, 0, -2.5) * Box(420, 320, 5))
    d.add("bed", Pos(0, 0, 103) * Box(220, 220, 6))
    d.add("hotend", Pos(0, 150, 60) * Box(20, 16, 15))
    d.add("car", Pos(0, -100, 30) * Box(20, 20, 20), body="car")
    place(d, "x_motor", nema17(34), Location((150, 120, 40)))
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-100, 100), max_speed=50, max_accel=500,
                          drive={"motor": "x_motor", "kind": "leadscrew", "lead": 8.0}))
    place(d, "board", skr_mini_e3_v3(), Location((100, 0, 0)))
    place(d, "psu", psu_lrs(psu), Location((-80, 0, 0)))
    place(d, "inlet", iec_inlet_c14(8.0), Location((-190, 120, 0)))
    place(d, "host", raspberry_pi_zero2w(), Location((100, 90, 0)))
    place(d, "relay", relay_btt_v12(), Location((-80, 110, 0)))
    place(d, "bed_heater", bed_heater_pad(140, 200, 150.0), Location((0, 0, 100)))
    place(d, "tco", thermal_fuse(133.0, 109.0, 15.0), Location((90, 0, 98)))
    place(d, "hot_heater", heater_cartridge(30.0), Location((0, 153, 58)))
    place(d, "hot_sensor", thermistor_cartridge(), Location((0, 146, 63)))
    place(d, "earth_stud", nema17(34), Location((-190, -120, -60)))      # any part stands in for the stud here
    for a, b in (("board", "base"), ("psu", "base"), ("inlet", "base"), ("host", "base"), ("relay", "base"), ("bed_heater", "bed"),
                 ("tco", "bed"), ("hot_heater", "hotend"), ("hot_sensor", "hotend"), ("x_motor", "base"), ("earth_stud", "base")):
        d.join(a, b, "bond")
    el = d.electrical = Electrical()
    for nm in ("board", "psu", "inlet", "host", "hot_heater", "x_motor"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed")
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", sensor_type="Generic 3950",
                    points=THERMISTORS["Generic 3950"], tau_s=10.0, node="pad")
    device_from(el, d, "hot_sensor")
    el.add(Device("earth", "earth_point", "earth_stud", {"pe": Port("pe", "pe", "ring-M4", multi=True)}, params={"bonds": "base"},
                  product={"product": "ring terminal on a stud", "vendor": "commodity", "part_number": None, "form": "hardware",
                           "off_the_shelf": True, "custom_pcb": False, "builder_work": "crimp"}))
    el.loom("trunk", [("world", (-60.0, loom_y, loom_z)), ("world", (60.0, loom_y, loom_z))])
    mk = dict(conductors=1, insulation="pvc105")
    if cutoffs:
        device_from(el, d, "tco")
        device_from(el, d, "relay")
        el.wire("L1", "inlet.L", "relay.LIN", 18, **mk)
        el.wire("L2", "relay.LOT", "psu.L", 18, **mk)
        el.wire("ps_on", "board.PS-ON", "relay.ctrl", 26, conductors=3)
        el.wire("bed", "board.HB", "tco.a", bed_awg, insulation="silicone", via=["trunk"])
        el.wire("bed tail", "tco.b", "bed_heater.in", bed_awg, insulation="silicone", length=80.0)
    else:
        d.components = [c for c in d.components if c.name not in ("tco", "relay")]
        el.wire("L", "inlet.L", "psu.L", 18, **mk)
        el.wire("bed", "board.HB", "bed_heater.in", bed_awg, insulation="silicone", via=["trunk"])
    el.wire("N", "inlet.N", "psu.N", 18, **mk)
    el.wire("pe psu", "inlet.PE", "psu.FG", 18, **mk)
    el.wire("pe frame", "inlet.PE", "earth.pe", 18, **mk)
    el.wire("24V", "psu.V+1", "board.POWER", 16, insulation="silicone")
    el.wire("hotend", "board.E0", "hot_heater.in", 20, insulation="silicone")
    el.wire("bed ntc", "board.THB", "bed_ntc.out", 26, insulation="silicone")
    if thermistor:
        el.wire("hot ntc", "board.TH0", "hot_sensor.out", 26)
    el.wire("x", "board.XM", "x_motor.coils", 24, conductors=4)
    el.wire("host", "board.TFT", "host.GPIO", 26, conductors=4)
    vh = {} if runaway else None
    el.firmware = {"kind": "klipper", "steppers": {"x": {"run_current": run}},
                   "heaters": {"extruder": {"heater": "hot_heater", "sensor": "hot_sensor", "max_temp": 280, "targets": [250.0],
                                            "verify_heater": vh},
                               "heater_bed": {"heater": "bed_heater", "sensor": "bed_ntc", "max_temp": 120, "targets": [60.0],
                                              "verify_heater": vh}}}
    el.bay = Bay(["psu", "board", "host"], enclosed=False, vent_area_m2=0.02, height_m=0.05)
    d.endstops.append({"joint": "x", "sensorless": True})
    if custom_board:
        el.devices["relay" if cutoffs else "host"].product.update(custom_pcb=True, off_the_shelf=False, product="home-made board")
    add_electrical_bom(el, d)
    return d


@pytest.fixture(autouse=True)
def _out(tmp_path, monkeypatch):
    monkeypatch.setattr(VE, "OUT_ROOT", str(tmp_path))


def errs(d):
    return [f.code for f in VE.verify_electrical(d).findings if f.severity == "error"]


def test_rig_passes_and_writes_artifacts(tmp_path):
    d = rig()
    r = VE.verify_electrical(d)
    assert [(f.code, f.message) for f in r.findings if f.severity == "error"] == []
    m = r.metrics
    assert m["off_the_shelf"]["custom_pcbs_needed"] == 0
    assert 0.3 < m["power_budget"]["psu_load_frac"] < 0.85
    assert m["heaters"]["extruder"]["faults"]["sensor_detached while holding 250 degC"]["detected"]
    cfg = (tmp_path / "rig" / "electrical" / "printer.cfg").read_text()
    assert "heater_pin: PC9" in cfg and "sensor_pin: PC4" in cfg and "[verify_heater heater_bed]" in cfg and "pid_Kp" in cfg
    assert "step_pin: PB13" in cfg and "rotation_distance: 8" in cfg
    assert (tmp_path / "rig" / "electrical" / "wiring.csv").exists()
    assert m["klipper_config_check"]["problems"] == []


def test_undersized_psu():
    assert "psu_undersized" in errs(rig(psu="LRS-200-24"))


def test_thin_wire_on_the_bed():
    e = errs(rig(bed_awg=24))
    assert "wire_overloaded" in e


def test_heater_without_thermistor():
    e = errs(rig(thermistor=False))
    assert "heater_without_thermistor" in e and "device_not_wired" in e


def test_runaway_protection_disabled():
    r = VE.verify_electrical(rig(runaway=False))
    msgs = [f.message for f in r.findings if f.code == "runaway_not_detected"]
    assert any("sensor_detached" in m for m in msgs)


def test_missing_cutoff():
    assert "no_independent_cutoff" in errs(rig(cutoffs=False))


def test_wire_through_moving_parts_path():
    r = VE.verify_electrical(rig(loom_y=-100.0, loom_z=30.0))
    hits = [f for f in r.findings if f.code == "wire_hits_moving_part"]
    assert hits and hits[0].data["part"] == "car"


def test_driver_current_above_motor_rating():
    e = errs(rig(run=0.6))
    assert "motor_current_over_rating" in e and "motor_too_hot" in e


def test_custom_pcb_is_an_error():
    assert "custom_electronics_required" in errs(rig(custom_board=True))


def test_motor_curve_feeds_the_mechanical_checks():
    from mechloop.verifiers.ratings import resolve_drives

    d = rig()
    out = resolve_drives(d)
    c = d.get("x_motor")
    assert "electrical model" in c.ratings["torque_curve_source"] and c.ratings["torque_curve_class"]
    # 50 mm/s on an 8 mm lead = 375 rpm: the 37 mH winding is voltage-limited to about 100 N*mm there
    assert 80.0 < out["x"]["motor_torque_nmm_at_speed"] < 120.0
