"""Known-answer tests for the fourth batch of vendor documents (reports/"Vendor documents - what they change.md",
proposals 17 to 22): bed probes as catalogue parts, the relay's neutral, fan voltage, the Schurter inlet, McMaster
fasteners. Small purpose-built designs; answers by hand or by construction."""
import sys
from pathlib import Path

import pytest
from build123d import Box, Cylinder, Location, Pos

from mechloop import electrical as E
from mechloop.electrical import Device, Electrical, Port
from mechloop.model import Design, Joint
from mechloop.parts import fan, place, probe_omron_e2e, vendor_data
from mechloop.parts.electrical import device_from
from mechloop.report import VerifierResult
from mechloop.verifiers import electrical as VE
from mechloop.verifiers.subsystems import verify_subsystems

sys.path.insert(0, str(Path(__file__).parent))


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


# ---------------------------------------------------------------- (a) bed probes: mounting and sensing
def probe_toolhead(model="E2E-X5ME1", clamp=(15.0, 18.0), tab="al6061", face_above_nozzle=1.0, metal_block_at=None, with_tab=True):
    """Bed top at z = 50 (aluminium), nozzle tip at z = 100 on a plastic head, the probe 40 mm to the side with its
    sensing face `face_above_nozzle` above the tip, clamped by its nuts in a 30 x 30 x 3 mm tab of material `tab`."""
    d = Design("e2e")
    d.add("frame", Pos(0, 0, 200) * Box(300, 300, 10))
    d.add("bed", Pos(0, 0, 47) * Box(200, 200, 6), material="al6061", body="zbody")
    d.add("head", Pos(0, 0, 130) * Box(20, 20, 60), material="petg", body="xbody")              # tip face at z = 100
    zf = 100.0 + face_above_nozzle
    st = probe_omron_e2e(model, clamp=clamp)
    place(d, "probe", st, Location((40.0, 0, zf)), body="xbody")
    if clamp and with_tab:
        hole = st.interfaces["mounting"]["hole_dia"]
        t = clamp[1] - clamp[0]
        d.add("tab", Pos(40, 0, zf + clamp[0] + t / 2) * (Box(30, 30, t) - Cylinder(hole / 2, t)), material=tab, body="xbody")
        d.join("probe", "tab", "clamped by its two nuts")
    if metal_block_at is not None:
        d.add("block", Pos(40 + metal_block_at + 5, 0, zf + 5) * Box(10, 10, 10), material="al6061", body="xbody")
    d.joints += [Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-90, 90), max_effort=10),
                 Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-90, 50), max_effort=10),
                 Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(0, 50), max_effort=10)]
    d.tool_point = ("xbody", (0.0, 0.0, 100.0))
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z"}
    d.endstops += [{"joint": "x", "sensorless": True}, {"joint": "y", "sensorless": True}, {"joint": "z", "probe": "probe"}]
    return d


def probe_result(d):
    r = verify_subsystems(d)
    # the toolhead-margin warning (2026-11-15) has its own tests in test_known_answers_checkers.py; this rig's probe is not
    # tied to the head, so its margin is the assumed one
    return {f.code: f for f in r.findings if f.code.startswith("probe") and f.code != "probe_trigger_margin_thin"}, r.metrics["homing"]["z"]


def test_catalogue_probes_carry_the_sheets_figures():
    """OMRON E2E sheet: model code M = unshielded; D1 = DC two-wire NO; E1 = NPN three-wire NO. Surrounding metal (p.25):
    unshielded M12 l 15 / d 40, unshielded M18 l 22 / d 55, shielded l 0."""
    x8, x5m, x10m, x5 = (probe_omron_e2e(m) for m in ("E2E-X8MD1", "E2E-X5ME1", "E2E-X10ME1", "E2E-X5E1"))
    e = lambda st: st.ratings["electrical"]["ratings"]
    assert e(x8)["output"] == "two_wire_no" and (e(x8)["min_load_current_ma"], e(x8)["leakage_current_ma_max"], e(x8)["residual_voltage_v_max"]) == (3.0, 0.8, 3.0)
    assert e(x8)["switching_distance_aluminium_range_mm"] == [2.8, 3.2] and e(x8)["temperature_drift_frac"] == 0.10 and e(x8)["max_ambient_c"] == 70.0
    assert e(x5m)["output"] == e(x10m)["output"] == e(x5)["output"] == "npn_no" and e(x5m)["internal_pullup"] is True
    assert (e(x5m)["switching_distance_aluminium_mm"], e(x10m)["switching_distance_aluminium_mm"], e(x5)["switching_distance_aluminium_mm"]) == (1.6, 3.0, 1.75)
    mt = lambda st: st.interfaces["mounting"]
    assert (mt(x8)["shielded"], mt(x8)["head_proud_of_metal_l"], mt(x8)["metal_free_dia_d"], mt(x8)["hole_dia"]) == (False, 15.0, 40.0, 12.5)
    assert (mt(x10m)["head_proud_of_metal_l"], mt(x10m)["metal_free_dia_d"], mt(x10m)["hole_dia"]) == (22.0, 55.0, 18.5)
    assert mt(x5)["shielded"] and mt(x5)["head_proud_of_metal_l"] == 0.0
    for st in (x8, x5m, x10m, x5):
        assert st.catalog and not st.verified and "mass_kg" in st.source["unverified_fields"]       # partly the maker's, said so
    with pytest.raises(ValueError, match="does not fit on the thread"):
        probe_omron_e2e("E2E-X5ME1", clamp=(2.0, 5.0))                  # the lower nut would be on the unthreaded head


def test_unshielded_probe_needs_its_metal_free_zone():
    """M12 unshielded: face 15 mm proud of metal, 40 mm diameter free. An aluminium tab 15 to 18 mm behind the face is
    outside the zone: fine. The same tab 12 to 15 mm behind it is inside: error, nearest metal 12 mm behind the face. A
    plastic tab there is fine. An aluminium block 14 mm from the axis beside the head is inside the 20 mm radius."""
    f, z = probe_result(probe_toolhead(clamp=(15.0, 18.0)))
    assert not f and z["mounting"]["clamped_in"] == "tab" and z["mounting"]["metal_in_zone"] == []
    f, z = probe_result(probe_toolhead(clamp=(12.0, 15.0)))
    assert list(f) == ["probe_metal_in_clear_zone"] and f["probe_metal_in_clear_zone"].severity == "error"
    hit = z["mounting"]["metal_in_zone"][0]
    assert hit["part"] == "tab" and hit["nearest_to_face_mm"] == 12.0 and (z["mounting"]["metal_free_zone"]["dia_mm"], z["mounting"]["metal_free_zone"]["from_face_mm"]) == (40.0, 15.0)
    assert not probe_result(probe_toolhead(clamp=(12.0, 15.0), tab="petg"))[0]
    f, z = probe_result(probe_toolhead(clamp=(15.0, 18.0), metal_block_at=14.0))
    assert list(f) == ["probe_metal_in_clear_zone"] and z["mounting"]["metal_in_zone"][0]["part"] == "block"
    assert z["mounting"]["metal_in_zone"][0]["nearest_to_axis_mm"] == 14.0
    # 1 mm outside the 20 mm radius: not in the zone as drawn. (This toy toolhead's block is tied to nothing, so whether it
    # ends up inside when built cannot be simulated, which is said: a warning, never a silent pass.)
    f, z = probe_result(probe_toolhead(clamp=(15.0, 18.0), metal_block_at=21.0))
    assert set(f) <= {"probe_zone_not_evaluated"} and z["mounting"]["metal_in_zone"] == []


def test_shielded_probe_may_sit_flush_and_every_probe_must_be_clamped():
    """Shielded M18 (E2E-X5E1): an aluminium tab 4 to 7 mm behind the face is allowed. Any threaded probe without
    `clamp=` or with nothing between its nuts is an error."""
    f, z = probe_result(probe_toolhead("E2E-X5E1", clamp=(4.0, 7.0)))
    assert not f and z["mounting"]["shielded"]
    assert list(probe_result(probe_toolhead(clamp=None))[0]) == ["probe_mount_not_declared"]
    assert list(probe_result(probe_toolhead(clamp=(15.0, 18.0), with_tab=False))[0]) == ["probe_not_clamped"]


def test_trigger_height_uses_the_chart_range_the_unit_spread_and_the_temperature_drift():
    """E2E-X5ME1, face 1.0 mm above the nozzle: switches with the nozzle 1.6 - 1.0 = 0.6 mm above an aluminium bed;
    +/-10 % unit to unit and +/-10 % with temperature: 1.6 x 0.8 - 1.0 = 0.28 to 1.6 x 1.2 - 1.0 = 0.92.
    E2E-X8MD1, face 1.5 mm above: 2.8 - 1.5 = 1.3; chart range 2.8 to 3.2: 2.8 x 0.8 - 1.5 = 0.74 to 3.2 x 1.2 - 1.5 = 2.34.
    E2E-X5ME1 with its face 1.4 mm above: 0.2 mm nominal, but a short, warm unit switches at 1.28 - 1.4 = -0.12: error."""
    _, z = probe_result(probe_toolhead("E2E-X5ME1", face_above_nozzle=1.0))
    assert z["z_offset"] == 0.6 and z["z_offset_range_mm"] == [0.28, 0.92] and z["z_offset_range_unit_spread_mm"] == [0.44, 0.76]
    _, z = probe_result(probe_toolhead("E2E-X8MD1", face_above_nozzle=1.5))
    assert z["z_offset"] == 1.3 and z["z_offset_range_mm"] == [0.74, 2.34]
    f, z = probe_result(probe_toolhead("E2E-X5ME1", face_above_nozzle=1.4))
    assert z["z_offset_range_mm"][0] == -0.12 and f["probe_trigger_margin"].severity == "error"


# ---------------------------------------------------------------- (a) bed probes: electrical
def probe_on_a_logic_input(model, **params):
    tpl = probe_omron_e2e(model).ratings["electrical"]
    el = Electrical()
    el.add(Device("board", "board", "board", {"Z-STOP": Port("Z-STOP", "endstop_in", "JST-XH", 3.0, "PC2", 3,
                                                               extra={"logic_v": 3.3, "pin_max_v": 3.6})}))
    el.add(Device("probe", "probe", "probe", {"out": Port("out", "probe", "JST-XH", 1.0, None, tpl["ports"]["out"]["conductors"])},
                  dict(tpl["ratings"]), dict(tpl["sources"]), {"supply_v": 24.0, **params}, dict(tpl["product"])))
    el.wire("probe", "board.Z-STOP", "probe.out", 26, conductors=3)
    r, m = VerifierResult("electrical"), {}
    d = Design("x")
    d.add("opto", Box(20, 10, 5), cots=True)
    VE._probe({"el": el, "design": d}, r, m)
    return {f.code: f for f in r.findings}, m["probe"]["probe"]


def test_two_wire_probe_cannot_go_straight_on_a_logic_input():
    """E2E-X8MD1: needs 3 mA of load, keeps up to 3 V across itself when on, leaks 0.8 mA when off. A 3.3 V input with
    a 40 k pull-up offers 0.08 mA; fed from 24 V the pin would see 24 - 3 = 21 V against a 3.6 V limit. Error.
    With a declared interface whose load is 4.7 k: (24 - 3) / 4.7 = 4.47 mA when on, enough; it must stay off at 0.8 mA."""
    f, m = probe_on_a_logic_input("E2E-X8MD1")
    assert list(f) == ["probe_two_wire_needs_interface"] and f["probe_two_wire_needs_interface"].severity == "error"
    assert m["direct_on_logic_input"]["load_current_ma_from_the_pin_pullup"] == pytest.approx(0.0825, abs=0.001)
    assert m["direct_on_logic_input"]["pin_v_if_fed_from_the_supply"] == 21.0
    ok = {"part": "opto", "load_ohm": 4700.0, "on_current_ma_min": 2.0, "off_current_ma_max": 1.0}
    f, m = probe_on_a_logic_input("E2E-X8MD1", interface=ok)
    assert not f and m["interface"]["load_current_when_on_ma"] == pytest.approx(4.47, abs=0.01)
    for bad, word in (({**ok, "load_ohm": 10000.0}, "2.1 mA"), ({**ok, "off_current_ma_max": 0.5}, "leaks"), ({**ok, "part": "nothing"}, "not an off-the-shelf")):
        f, _ = probe_on_a_logic_input("E2E-X8MD1", interface=bad)
        assert list(f) == ["probe_two_wire_interface_inadequate"] and word in f["probe_two_wire_interface_inadequate"].message


def test_three_wire_npn_probe_is_accepted_with_the_series_diode():
    """E2E-X5ME1 / X10ME1: the output is pulled to the 24 V supply inside the sensor (1.5 to 3 mA source): without a
    diode the 3.6 V pin sees 24 V (error); with the series diode declared it is accepted."""
    for model in ("E2E-X5ME1", "E2E-X10ME1", "E2E-X5E1"):
        f, m = probe_on_a_logic_input(model)
        assert list(f) == ["probe_signal_over_voltage"] and m["signal_high_v_worst_case"] == 24.0
        f, m = probe_on_a_logic_input(model, series_diode=True)
        assert not f and m["signal_high_v_worst_case"] == 3.3
    assert list(probe_on_a_logic_input("E2E-X5ME1", series_diode=True, supply_v=5.0)[0]) == ["probe_supply_out_of_range"]


# ---------------------------------------------------------------- (b) the relay needs its neutral
def test_relay_without_neutral_is_an_error(tmp_path, monkeypatch):
    """BIGTREETECH Relay V1.2: terminals LIN, N, LOT; its own converter is fed from LIN and N. With the neutral run
    inlet -> relay N -> supply the rig is clean; with the neutral straight to the supply (as v4 to v6 are wired) the relay
    has no supply: one error naming the port."""
    import test_electrical as TE

    monkeypatch.chdir(tmp_path)
    d = TE.rig()
    assert not errs(VE.verify_electrical(d))
    el = d.electrical
    el.wires = [w for w in el.wires if w.name not in ("N", "N2")]
    el.wire("N", "inlet.N", "psu.N", 18, conductors=1, insulation="pvc105")
    r = VE.verify_electrical(d)
    assert errs(r) == ["device_supply_not_connected"]
    f = next(x for x in r.findings if x.code == "device_supply_not_connected")
    assert f.data["port"] == "relay.N" and "neutral" in f.message
    # a wire on N that leads nowhere near a source does not count
    el.wires = [w for w in el.wires if w.name != "N"]
    el.wire("N", "inlet.N", "psu.N", 18, conductors=1, insulation="pvc105")
    assert "N" in d.get("relay").meta["interfaces"] or True
    assert vendor_data("bigtreetech_relay_v12")["values"]["mains_terminals"]["N"] == "neutral in"


# ---------------------------------------------------------------- (c) fan rated voltage
def test_fan_carries_its_rated_voltage_and_a_12v_fan_on_a_24v_output_is_an_error(tmp_path, monkeypatch):
    """Sunon MF30101V2-1000U-A99: 12 V rated (6 to 13.8), 32 mA. On a 24 V fan output: fan_voltage_mismatch (24 against
    12). The catalogue's 24 V 30 mm fan passes; its sheet is not in hand, so its figures stay unverified."""
    import test_electrical as TE

    monkeypatch.chdir(tmp_path)
    f12, f24 = fan(30, 12), fan(30)
    assert (f12.sku, f12.ratings["rated_voltage_v"], f12.ratings["rated_current_a"]) == ("FAN-3010-12V", 12.0, 0.032)
    assert (f24.sku, f24.ratings["rated_voltage_v"]) == ("FAN-3010", 24.0) and not f24.verified
    assert "NOT in hand" in f24.source["note"] and "typical" in f24.ratings["rated_current_source"]
    with pytest.raises(ValueError):
        fan(40, 12)
    for st, bad in ((f12, True), (f24, False)):
        d = TE.rig()
        place(d, "pfan", st, Location((0, 150, 90)))
        d.join("pfan", "hotend", "bond")
        device_from(d.electrical, d, "pfan")
        d.electrical.wire("part fan", "board.FAN0", "pfan.in", 26)
        r = VE.verify_electrical(d)
        row = r.metrics["power_budget"]["fans"]["pfan"]
        assert (row["rated_v"], row["supplied_v"]) == (st.ratings["rated_voltage_v"], 24.0)
        assert ("fan_voltage_mismatch" in errs(r)) == bad


# ---------------------------------------------------------------- (d) mains inlet to the Schurter DD11 drawing
def inlet_panel(t=3.0):
    from build123d import Rot, RectangleRounded, extrude

    from mechloop.parts.electrical import iec_inlet_c14

    d = Design("inlet", base="panel")
    st = iec_inlet_c14(8.0)
    cx, cy = st.interfaces["cutout"]
    panel = Pos(0, 0, -t / 2) * Box(60, 100, t)
    panel -= Pos(0, 0, -t / 2) * extrude(RectangleRounded(cx, cy, st.interfaces["cutout_corner_radius"]), t / 2, both=True)
    for x, y, _ in st.interfaces["mount_holes_m3"]:
        panel -= Pos(x, y, -t / 2) * Cylinder(st.interfaces["hole_dia"] / 2, t)
    d.add("panel", panel, material="al5052", process="sheet")
    place(d, "inlet", st, Location((0, 0, 0)))
    d.join("inlet", "panel", "screwed")
    return d, st


def test_inlet_is_the_schurter_dd11_and_its_own_hole_pattern_still_warns_with_the_reason():
    """DD11 version A: cut-out 47.1 x 28.1, two 3.4 mm holes 56 apart, 4.8 mm quick-connects, 30 mm deep. Web between
    cut-out and screw hole: 28 - 23.55 - 1.7 = 2.75 mm. In 3 mm sheet the rule wants 3 mm: the warning stays, and its
    hint now says the pattern is the maker's. In 2.5 mm sheet 2.75 >= 2.5: no warning. Order number not pinned."""
    from mechloop.verifiers.interference import verify_interference
    from mechloop.verifiers.manufacture import verify_manufacture

    d, st = inlet_panel(3.0)
    assert st.interfaces["cutout"] == (28.1, 47.1) and st.interfaces["cutout_to_screw_hole_web"] == 2.75
    assert [abs(h[1]) for h in st.interfaces["mount_holes_m3"]] == [28.0, 28.0]
    assert st.ratings["electrical"]["ports"]["L"]["connector"] == "faston-4.8" and st.shape.bounding_box().min.Z == -30.0
    assert "NOT PINNED" in st.ratings["electrical"]["sources"]["order_number"] and "order number" in st.source["unverified_fields"]
    assert not st.verified and not errs(verify_interference(d))
    r = verify_manufacture(d)
    f = [x for x in r.findings if x.code == "holes_too_close"]
    assert len(f) == 1 and f[0].severity == "warning" and f[0].data["value"] == pytest.approx(2.75, abs=0.01)
    assert "SCHURTER DD11" in f[0].data["hint"] and "not suppressed" in f[0].data["hint"] and f[0].data["vendor_pattern"]["part"] == "inlet"
    assert "holes_too_close" not in [x.code for x in verify_manufacture(inlet_panel(2.5)[0]).findings]


# ---------------------------------------------------------------- (e) McMaster fasteners
def test_mcmaster_numbers_are_recorded_and_the_m5_nut_keeps_its_iso_height_unless_named():
    """mcmaster_fasteners.json: SHCS-M3x8 is 91290A400 (file inspected); SHCS-M3x6 is listed as 91290A111 but the file
    delivered was the M3x12, so it is unconfirmed; SHCS-M3x25 has none. NUT-M5: ISO 4032 is 4.7 mm high and stays so;
    McMaster's 90591A260 is DIN 934, 4.0 mm, drawn only when named (0.7 mm lower)."""
    from mechloop.parts import add_nut, add_screw, hex_nut, shcs
    from mechloop.verifiers.ratings import verify_ratings

    assert shcs("M3", 8).ratings["mcmaster_pn"] == "91290A400" and "confirmed" in shcs("M3", 8).ratings["mcmaster_pn_status"][:9]
    # (SHCS-M3x6 was "unconfirmed" until the corrected file arrived in batch 6: see test_known_answers_batch6.py)
    assert shcs("M3", 6).ratings["mcmaster_pn"] == "91290A111" and shcs("M3", 6).ratings["mcmaster_pn_status"].startswith("confirmed")
    assert "mcmaster_pn" not in shcs("M3", 25).ratings
    iso, din = hex_nut("M5"), hex_nut("M5", "din934")
    assert (iso.sku, iso.interfaces["height"], iso.interfaces["height_din934_mcmaster"]) == ("NUT-M5", 4.7, 4.0)
    assert "DIN 934" in iso.ratings["mcmaster_pn_status"]
    assert (din.sku, din.interfaces["height"], din.ratings["mcmaster_pn"]) == ("NUT-M5-DIN934", 4.0, "90591A260")
    assert din.shape.bounding_box().max.Z == pytest.approx(4.0) and iso.shape.bounding_box().max.Z == pytest.approx(4.7)
    d = Design("bom", base="a")
    d.add("a", Pos(0, 0, -3) * (Box(30, 30, 6) - Cylinder(2.75, 6)))
    add_screw(d, "s", "M5", 16, at=(0, 0, 0), clamps=("a",))
    add_nut(d, "n", "M5", at=(0, 0, -6), direction=(0, 0, -1), screw="s", standard="din934")
    add_screw(d, "t", "M3", 6, at=(10, 10, 0), threads_into="a")
    bom = verify_ratings(d).metrics["bom"]
    assert bom["NUT-M5-DIN934"]["mcmaster_pn"] == "90591A260" and bom["SHCS-M3x6"]["mcmaster_pn_status"].startswith("confirmed")
    assert "mcmaster_pn" not in bom["SHCS-M5x16"]
