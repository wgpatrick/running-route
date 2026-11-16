"""Vendor-backed catalog parts must match the recorded vendor files, and every vendor file must say where it came from."""
import json
from pathlib import Path

import pytest

from mechloop import parts
from mechloop.parts import VENDOR_DIR, vendor_data

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted(VENDOR_DIR.glob("*.json"))


def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def _size(st):
    bb = st.shape.bounding_box()
    return bb.size.X, bb.size.Y, bb.size.Z


def test_vendor_files_exist():
    assert len(FILES) >= 8


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.stem)
def test_every_vendor_file_has_a_source(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    assert d["source_url"].startswith("https://"), path.name
    assert d["retrieved"] in ("2026-11-14", "2026-11-15", "2026-11-16")
    assert d.get("family") and d.get("vendor")
    for node in _walk(d):  # every URL recorded anywhere is https, every stored copy is present and small
        if "source_url" in node:
            assert node["source_url"].startswith("https://")
        if node.get("local_copy"):
            f = ROOT / node["local_copy"]
            assert f.is_file(), node["local_copy"]
            assert f.stat().st_size < 2_000_000


@pytest.mark.parametrize("length", parts.NEMA17_LENGTHS)
def test_nema17_matches_stepperonline(length):
    rec = vendor_data("stepperonline_nema17")["parts"][str(length)]
    v = rec["values"]
    st = parts.nema17(length)
    assert st.verified and st.source["level"] == "vendor" and st.source["part"] == rec["part_number"]
    assert "approximate" not in st.ratings
    assert st.ratings["holding_torque_nmm"] == pytest.approx(v["holding_torque_nm"] * 1000)
    assert st.ratings["rotor_inertia_gcm2"] == v["rotor_inertia_gcm2"]
    assert st.ratings["rated_current_a"] == v["rated_current_a"]
    assert st.ratings["phase_resistance_ohm"] == v["phase_resistance_ohm"]
    assert st.ratings["phase_inductance_mh"] == v["phase_inductance_mh"]
    assert st.mass_kg == pytest.approx(v["mass_g"] / 1000)
    x, y, z = _size(st)
    # the connector / lead exit on +X (from the CAD model, see docs/VENDOR_CAD.md) stands 5.7 mm out of the frame
    assert x == pytest.approx(v["frame_mm_max"] + 5.7) and y == pytest.approx(v["frame_mm_max"])
    assert st.shape.bounding_box().min.X == pytest.approx(-v["frame_mm_max"] / 2)
    assert z == pytest.approx(length + v["shaft_length_mm"])  # body below the face, shaft above
    assert st.interfaces["shaft_dia"] == v["shaft_dia_mm"] and st.interfaces["pilot_dia"] == v["pilot_dia_mm"]
    hx = sorted({abs(h[0]) for h in st.interfaces["mount_holes_m3"]})
    assert hx == [pytest.approx(v["hole_square_mm"] / 2)]
    # the torque curve is the published one: same speeds, torque = fraction x holding torque
    pts = rec["pull_out_torque_curve"]["points_rpm_nmm"]
    curve = st.ratings["torque_curve_rpm_frac"]
    assert [c[0] for c in curve] == [p[0] for p in pts]
    for (_, frac), (_, nmm) in zip(curve, pts):
        assert frac * st.ratings["holding_torque_nmm"] == pytest.approx(nmm, abs=0.1)
    assert st.ratings["max_rpm"] == pts[-1][0]
    assert max(f for _, f in curve) < 1.0  # pull-out torque never exceeds holding torque


def test_nema17_curve_units_consistent():
    for rec in vendor_data("stepperonline_nema17")["parts"].values():
        c = rec["pull_out_torque_curve"]
        k = {"N.cm": 10.0, "gf.cm": 0.0980665}[c["unit"]]
        for (r1, t), (r2, nmm) in zip(c["points_rpm_torque"], c["points_rpm_nmm"]):
            assert r1 == r2 and nmm == pytest.approx(t * k, abs=0.06)


@pytest.mark.parametrize("watts", [150, 200, 350])
def test_psu_matches_meanwell(watts):
    rec = vendor_data("meanwell_lrs")["parts"][str(watts)]
    v = rec["values"]
    st = parts.psu_24v(watts)
    assert st.verified and st.source["part"] == rec["model"] == f"LRS-{watts}-24"
    assert _size(st) == pytest.approx((v["length_mm"], v["width_mm"], v["height_mm"]))
    assert st.mass_kg == v["mass_kg"]
    assert st.ratings["rated_current_a"] == v["rated_current_a"]
    assert st.ratings["efficiency"] == v["efficiency_typ"]
    assert st.ratings["watts"] == watts and st.ratings["rated_power_w"] >= watts
    bm = v["bottom_mount"]
    assert st.interfaces["mount_thread"] == bm["thread"]
    holes = st.interfaces["mount_holes_m4"]
    assert len(holes) == bm["count"] == len(bm["holes_xy_mm"])
    for (hx, hy, hz), (x, y) in zip(holes, bm["holes_xy_mm"]):
        assert (hx + v["length_mm"] / 2, hy + v["width_mm"] / 2, hz) == pytest.approx((x, y, 0.0))
        assert abs(hx) < v["length_mm"] / 2 and abs(hy) < v["width_mm"] / 2


def test_unlisted_psu_wattage_stays_proxy():
    st = parts.psu_24v(250)
    assert not st.verified and st.ratings["approximate"] and st.ratings["source"] == "typical, unverified"


def test_control_board_matches_skr_mini_e3_v3():
    v = vendor_data("bigtreetech_skr_mini_e3_v3")["values"]
    st = parts.control_board()
    assert st.verified
    w, d = v["board_size_mm"]
    x, y, _ = _size(st)
    assert (x, y) == pytest.approx((w, d))
    holes = st.interfaces["mount_holes_m3"]
    assert len(holes) == len(v["mount_holes_xy_mm"]) == 5
    for (hx, hy, hz), (bx, by) in zip(holes, v["mount_holes_xy_mm"]):
        assert (hx + w / 2, hy + d / 2) == pytest.approx((bx, by), abs=1e-3)
        assert 0 < bx < w and 0 < by < d
    assert st.ratings["stepper_drivers"] == v["stepper_drivers"] == 4
    assert st.ratings["sense_resistor_ohm"] == v["driver_sense_resistor_ohm"]
    assert "mass_kg" in st.source["unverified_fields"]


def test_coupler_matches_stepperonline():
    v = vendor_data("stepperonline_coupler")["parts"]["MH2025-5-8"]["values"]
    st = parts.shaft_coupler(5.0, 8.0)
    assert st.verified
    assert _size(st) == pytest.approx((v["outside_diameter_mm"], v["outside_diameter_mm"], v["length_mm"]))
    assert st.interfaces["od"] == v["outside_diameter_mm"] and st.interfaces["length"] == v["length_mm"]
    assert st.ratings["rated_torque_nmm"] == pytest.approx(v["rated_torque_nm"] * 1000)
    assert st.mass_kg == pytest.approx(v["mass_g"] / 1000)
    assert not parts.shaft_coupler(5.0, 5.0).verified  # other bores were not sourced


def test_mgn12_matches_recorded_table_and_hiwins_own_catalogue():
    d = vendor_data("hiwin_mgn12")
    b, r = d["parts"]["MGN12H_block"]["values"], d["parts"]["MGNR12_rail"]["values"]
    car, rail = parts.mgn12h_carriage(), parts.mgn12_rail(300)
    # since 2026-11-15 the values are confirmed by Hiwin's own catalogue (block `catalogue`): vendor-backed
    assert car.verified and rail.verified and car.source["level"] == "vendor" and "approximate" not in car.ratings
    cat = d["catalogue"]["block_dimensions"]["MGN12H"]
    assert (cat["H_mm"], cat["H1_mm"], cat["W_mm"], cat["L_mm"], cat["B_mm"], cat["C_mm"], cat["L1_mm"]) == (
        b["assembly_height_H_mm"], b["clearance_H1_mm"], b["width_W_mm"], b["length_L_mm"], b["hole_spacing_B_mm"],
        b["hole_spacing_C_mm"], b["L1_mm"])
    cd, c0 = d["catalogue"]["load_ratings"]["MGN12H"][:2]
    assert (cd, c0) == (b["dynamic_load_C_kN"] * 1000, b["static_load_C0_kN"] * 1000)
    assert _size(car) == pytest.approx((b["length_L_mm"], b["width_W_mm"], b["assembly_height_H_mm"] - b["clearance_H1_mm"]))
    assert car.interfaces["top_z"] == b["assembly_height_H_mm"]
    assert car.shape.bounding_box().min.Z == pytest.approx(b["clearance_H1_mm"])
    assert car.ratings["dynamic_load_n"] == pytest.approx(b["dynamic_load_C_kN"] * 1000)
    assert car.ratings["static_load_n"] == pytest.approx(b["static_load_C0_kN"] * 1000)
    assert car.ratings["static_moment_nm"] == min(b["static_moment_MR_Nm"], b["static_moment_MP_Nm"], b["static_moment_MY_Nm"])
    assert car.mass_kg == b["mass_kg"]
    assert sorted({abs(h[0]) for h in car.interfaces["mount_holes_m3"]}) == [b["hole_spacing_C_mm"] / 2]
    assert sorted({abs(h[1]) for h in car.interfaces["mount_holes_m3"]}) == [b["hole_spacing_B_mm"] / 2]
    assert _size(rail) == pytest.approx((300, r["width_WR_mm"], r["height_HR_mm"]))
    assert rail.interfaces["hole_pitch"] == r["hole_pitch_P_mm"]
    assert rail.interfaces["screw_seat_z"] == r["height_HR_mm"] - r["counterbore_depth_h_mm"]
    assert rail.mass_kg == pytest.approx(r["mass_kg_per_m"] * 0.3)
    xs = [h[0] for h in rail.interfaces["mount_holes_m3"]]
    assert all(b2 - a2 == pytest.approx(r["hole_pitch_P_mm"]) for a2, b2 in zip(xs, xs[1:]))


def test_fasteners_match_iso_tables():
    d = vendor_data("iso_fasteners")
    for size, row in d["iso4762"].items():
        thread_d, head_d, head_h, key, *_ = parts.SCREW[size]
        assert (head_d, head_h, key) == (row["head_d_max"], row["head_h"], row["hex_key"]), size
        assert thread_d == float(size[1:])
        st = parts.shcs(size, 10)
        assert st.verified and st.source["level"] == "standard" and "proof_load_n" in st.source["unverified_fields"]
        assert st.interfaces["head_d"] == row["head_d_max"]
    for size, row in d["iso4032"].items():
        assert parts.NUT[size] == (row["across_flats"], row["height"]), size
        assert parts.hex_nut(size).verified
    # the recorded values are the ones in the stored copies of the tables
    import csv

    def table(path):  # first table in the file only: later sections reuse the size names
        rows = {}
        for r in csv.reader(open(path)):
            if r and r[0].startswith("M") and len(r) > 8:
                rows.setdefault(r[0], r)
        return rows

    rows = table(ROOT / d["sources"][0]["local_copy"])
    for size, row in d["iso4762"].items():
        assert (float(rows[size][3]), float(rows[size][8])) == (row["head_d_max"], row["head_h"])
    rows = table(ROOT / d["sources"][1]["local_copy"])
    for size, row in d["iso4032"].items():
        assert (float(rows[size][8]), float(rows[size][6])) == (row["across_flats"], row["height"])


def test_unsourced_parts_are_not_marked_verified():
    for st in (parts.extrusion_2020(200), parts.leadscrew_t8(200), parts.leadscrew_t8(200, 2.0), parts.leadscrew_nut_t8(),
               parts.gt2_pulley(), parts.gt2_idler(), parts.bearing("608"), parts.endstop_switch(), parts.extruder_direct(),
               parts.fan(40), parts.linear_rod(8, 100), parts.corner_bracket_2020()):
        assert not st.verified, st.sku
        assert "unverified" in st.ratings["source"]


def test_ratings_verifier_lists_only_unverified_parts():
    from build123d import Location

    from mechloop.model import Design
    from mechloop.verifiers.ratings import verify_ratings

    d = Design("vendor_check")
    parts.place(d, "motor", parts.nema17(48), Location((0, 0, 100)))
    parts.place(d, "psu", parts.psu_24v(350), Location((300, 0, 0)))
    r = verify_ratings(d)
    assert not [f for f in r.findings if f.code == "approximate_ratings"]
    assert r.metrics["vendor_backed_parts"] == ["NEMA17-48", "PSU-24V-350"]
    assert d.get("motor").meta["vendor_backed"] and d.get("motor").meta["source"]["url"].startswith("https://")
    parts.place(d, "block", parts.mgn12h_carriage(), Location((0, 200, 0)))
    parts.place(d, "brg", parts.bearing("608"), Location((0, 300, 0)))
    r = verify_ratings(d)
    f = [f for f in r.findings if f.code == "approximate_ratings"]
    assert len(f) == 1 and f[0].severity == "info"
    assert f[0].data["parts"] == ["BRG-608"]                    # the MGN12H is vendor-backed since Hiwin's catalogue was read
    assert "NEMA17-48" not in f[0].message and "MGN12H" not in f[0].message and "MGN12H" in r.metrics["vendor_backed_parts"]


# ----------------------------------------------------------------- parts added for printer_v6 (2026-11-15)
def test_roto_extruder_matches_e3d():
    d = vendor_data("e3d_roto")
    v, dm = d["values"], d["drawing"]["dimensioned"]
    c = d["reference_cad"]["measured_mm"]            # measured in E3D's reference CAD (vendor_cad/e3d_roto_reference_cad.step)
    st = parts.extruder_roto()
    assert st.verified and st.source["level"] == "vendor" and st.source["part"] == d["part_number"] == "REVO-ROTO-COLDSIDE-AS"
    assert st.sku.startswith("EXTRUDER")            # the subsystems and electrical verifiers find the extruder by this
    assert st.mass_kg == pytest.approx(v["mass_g"] / 1000) == 0.140
    bb = st.shape.bounding_box()
    env = c["envelope"]["cold_side_with_motor"]      # the simulation solid has the CAD's envelope (motor leads excluded) ...
    assert (bb.min.X, bb.max.X) == pytest.approx(tuple(env["x"]), abs=1e-3)
    assert (bb.min.Y, bb.max.Y) == pytest.approx(tuple(env["y"]), abs=1e-3)
    assert (bb.min.Z, bb.max.Z) == pytest.approx(tuple(env["z"]), abs=1e-3)
    # ... and the CAD agrees with E3D's dimensioned drawing (the seat boss hangs 0.3 mm below the drawing's body bottom)
    assert (bb.min.X, bb.max.X) == pytest.approx((dm["x_min_fan_screw_heads_mm"], dm["x_max_motor_rear_mm"]), abs=0.02)
    assert (bb.min.Z, bb.max.Z) == pytest.approx((dm["body_bottom_z_mm"] - 0.3, dm["lever_top_z_mm"]), abs=0.02)
    assert c["body"]["z"][0] == dm["body_bottom_z_mm"] and st.interfaces["fan_face_x"] == pytest.approx(dm["x_fan_face_mm"], abs=0.02)
    assert bb.size.Y == pytest.approx(dm["width_mm"]) == c["width"] == st.interfaces["mount_width"]
    lo, up = st.interfaces["mount_holes_m3"]
    assert lo == (0.0, 0.0, 0.0) and up == (dm["upper_hole_xz_mm"][0], 0.0, dm["upper_hole_xz_mm"][1]) == (6.8, 0.0, 30.5)
    assert st.interfaces["mount_hole_axis"] == (0.0, 1.0, 0.0) and st.interfaces["mount_ears_y"] == (12.25, 19.25)
    tip = st.interfaces["nozzle_tip"][0]
    assert tip == tuple(c["nozzle_tip"]) == (-9.058, -4.06, -33.55)
    assert abs(tip[0] - dm["nozzle_tip_xz_mm"][0]) < 0.02 and tip[2] == dm["nozzle_tip_xz_mm"][1]       # drawing: -9.05 +/-0.26, -33.55
    # the drawing's 15.18 mm is from the -Y face: the side the catalogue had assumed, now measured
    assert tip[1] < 0 and c["nozzle_axis_from_side_face"]["minus_y_face"] == pytest.approx(dm["width_mm"] / 2 + tip[1])
    assert abs(tip[1]) == pytest.approx(dm["width_mm"] / 2 - dm["nozzle_axis_from_side_face_mm"], abs=0.02)
    assert st.interfaces["filament_entry"][0] == (tip[0], tip[1], 27.05) and st.interfaces["lever_top"][0][2] == dm["lever_top_z_mm"]
    lead = st.interfaces["port:coils"]
    assert lead[0] == st.interfaces["motor_lead_exit"][0] and lead[0][1] < 0 < lead[0][2]     # the leads leave towards -Y, +Z
    assert not d["drawing"]["assumed"] and not any("side" in f or "scaled" in f for f in st.source["unverified_fields"])
    top, bottom = st.interfaces["filament_axis"]
    assert top[:2] == bottom[:2] == tip[:2] and bottom == tip                    # filament runs straight down to the nozzle
    seat = st.interfaces["hotend_seat"][0]
    assert seat[2] - tip[2] == pytest.approx(vendor_data("e3d_revo")["nozzle"]["drawing"]["dimensioned"]["seat_flange_to_tip_mm"])
    r = st.ratings
    assert r["rotation_distance"] == v["rotation_distance_mm"] == 26.8937 and r["gear_ratio"] == v["gear_ratio"]
    assert r["full_steps_per_rotation"] == 400
    # E3D's own figures agree with each other only when the gear ratio is applied to the rotation distance
    per_rev = v["rotation_distance_mm"] / v["gear_ratio"]
    assert v["full_steps_per_rotation"] * 16 / per_rev == pytest.approx(v["steps_per_mm_16x"], rel=2e-3)
    assert r["rotation_distance_per_motor_rev"] == pytest.approx(per_rev, abs=1e-3)
    assert r["rotation_distance_200_steps_no_gear_ratio"] == pytest.approx(per_rev / 2, abs=1e-3)
    e = r["electrical"]
    assert e["kind"] == "stepper" and e["product"]["off_the_shelf"] and not e["product"]["custom_pcb"]
    m = v["motor"]
    assert e["ratings"]["phase_resistance_ohm"] == m["phase_resistance_ohm"] and e["ratings"]["holding_torque_nmm"] == m["holding_torque_nmm"]
    assert e["ratings"]["rated_current_a"] == v["current_max_a_rms"] == pytest.approx(v["current_max_a_peak"] / 2 ** 0.5, abs=1e-3)
    assert m["rated_voltage_v"] / m["phase_resistance_ohm"] == pytest.approx(v["current_max_a_peak"])
    # the inductance is not published: it must be there for the electrical model, and must be declared an estimate
    assert m["phase_inductance_mh"] is None and e["ratings"]["phase_inductance_mh"] > 0
    assert "ESTIMATED" in e["sources"]["phase_inductance_mh"]
    assert any("phase_inductance_mh" in f for f in st.source["unverified_fields"])


def test_roto_and_revo_work_with_the_electrical_model():
    from build123d import Location

    from mechloop.electrical import Electrical, stepper_torque_curve
    from mechloop.model import Design
    from mechloop.parts.electrical import device_from, embedded_device

    d = Design("toolhead_check")
    ex = parts.extruder_roto()
    parts.place(d, "extruder", ex, Location((0, 0, 100)), body="xbody")
    seat = d.get("extruder").meta["interfaces"]["hotend_seat"][0]
    hot = parts.hotend_revo()
    parts.place(d, "hotend", hot, Location(seat), body="xbody")
    tip = d.get("hotend").meta["interfaces"]["nozzle_tip"][0]
    assert tip == pytest.approx(d.get("extruder").meta["interfaces"]["nozzle_tip"][0])     # both drawings give the same nozzle tip
    el = Electrical(supply_v=24.0)
    mot = device_from(el, d, "extruder")
    assert mot.kind == "stepper" and mot.ports["coils"].conductors == 4
    assert all(k in mot.ratings for k in ("rated_current_a", "phase_resistance_ohm", "phase_inductance_mh", "holding_torque_nmm"))
    assert mot.params["rotation_distance"] == 26.8937 and mot.params["full_steps_per_rotation"] == 400
    heater = device_from(el, d, "hotend")        # embedded_device finds the heater by the component name
    th = embedded_device(el, d, "hotend", "hotend_thermistor", "thermistor", "ntc", "thermistor", **hot.ratings["thermistor"])
    assert heater.kind == "heater" and set(heater.ports) == {"in"} and heater.ratings["watts"] == 40.0 and heater.ratings["volts"] == 24.0
    assert heater.params["model"] == "block"
    assert th.params["sensor_type"] == "ATC Semitec 104NT-4-R025H42G" and th.params["points"][0] == (25.0, 100000.0) and th.params["node"] == "block"
    import numpy as np

    t = stepper_torque_curve(0.075, mot.ratings["rated_current_a"], mot.ratings["phase_resistance_ohm"], mot.ratings["phase_inductance_mh"] * 1e-3,
                             0.318, 24.0, np.array([0.0, 60.0, 300.0]))
    assert t[0] == pytest.approx(0.075 * 0.318 / 0.424, rel=0.05) and t[-1] <= t[0]


def test_revo_hotside_matches_e3d():
    d = vendor_data("e3d_revo")
    hv, nd = d["heatercore"]["values"], d["nozzle"]["drawing"]["dimensioned"]
    st = parts.hotend_revo()
    assert st.verified and st.sku == "HOTEND-REVO-24V-40W"
    assert st.interfaces["nozzle_tip"] == [(0.0, 0.0, -nd["seat_flange_to_tip_mm"])] and st.interfaces["tube_above_seat"] == pytest.approx(18.3)
    c = d["reference_cad"]["measured_mm"]            # HeaterCore and nozzle block as E3D's reference CAD draws them
    assert c["seat_to_tip"] == nd["seat_flange_to_tip_mm"] and c["nozzle_block"]["dia"] == nd["block_dia_mm"] == st.interfaces["nozzle_block_dia"]
    assert st.interfaces["heatercore_dia"] == c["heatercore"]["dia"] == 16.7
    assert st.interfaces["heater_block_box"] == [(-8.35, -8.35, -20.8), (8.35, 8.35, -3.79)]
    assert st.shape.bounding_box().max.X == pytest.approx(8.35 + 22.0)       # the lead sleeve (HeaterCore drawing; not in the CAD)
    assert st.shape.bounding_box().min.Z == pytest.approx(-22.8) and st.shape.bounding_box().max.Z == pytest.approx(0.0)
    assert st.mass_kg == pytest.approx(0.157 - 0.140)                       # E3D: Roto 140 g, 157 g with hot side and nozzle
    e = st.ratings["electrical"]
    assert e["ratings"]["watts"] == hv["watts"] == 40 and e["ratings"]["max_temp_c"] == hv["max_printing_temperature_c"] == 300
    r0, a = hv["resistance_24v_40w_at_23c_ohm"], hv["temp_coefficient_per_c"]
    assert 24.0 ** 2 / r0 == pytest.approx(40.0) and e["ratings"]["resistance_ohm_23c"] == r0
    assert e["ratings"]["power_w_at_c"][250] == pytest.approx(576 / (r0 * (1 + a * 227)), abs=0.06) == pytest.approx(27.2, abs=0.1)
    assert st.ratings["sensor_type"] == hv["klipper_sensor_type"]
    assert st.ratings["hardware_cutoff"].startswith("none")                 # no real product was found: do not pretend
    assert "ESTIMATES" in e["sources"]["thermal"] and any("thermal" in f for f in st.source["unverified_fields"])
    with pytest.raises(ValueError):
        parts.hotend_revo(60)


def test_v6_hotend_matches_e3d_drawing():
    d = vendor_data("e3d_v6")["added_2026-11-15"]
    h = d["drawing"]["heights_above_nozzle_tip_mm"]
    st = parts.hotend_v6()
    assert st.sku == "HOTEND-V6" and st.source["part"] == "V6-175-24V"
    bb = st.shape.bounding_box()
    assert bb.max.Z == pytest.approx(0.0) and bb.min.Z == pytest.approx(-h["heatsink_top"]) == pytest.approx(-62.55)
    assert st.interfaces["nozzle_tip"] == [(0.0, 0.0, -62.55)]
    g = st.interfaces["groove_mount"]
    assert (g["flange_dia"], g["neck_dia"]) == (16.0, 12.0) and g["neck_z"] == pytest.approx((-9.7, -3.7))
    assert st.ratings["heater_w"] == 30.0 and st.ratings["max_temp_c"] == 285.0 and st.ratings["max_temp_with_sock_c"] == 260.0
    lo, hi = st.ratings["heater_resistance_ohm"]
    assert lo < 24.0 ** 2 / 30.0 < hi
    assert st.ratings["sensor_type"] == "ATC Semitec 104NT-4-R025H42G"
    assert any(f.startswith("mass_kg") for f in st.source["unverified_fields"])


def test_spacers_match_pololu_and_say_what_is_not_sourced():
    r = vendor_data("pololu_spacers")["ranges"]
    listing = (ROOT / vendor_data("pololu_spacers")["local_copy"]).read_text()
    for size, rng in r.items():
        assert parts.spacer_lengths(size) == sorted(float(k) for k in rng["items"])
        for L, it in rng["items"].items():
            st = parts.spacer_round(size, float(L))
            assert st.verified and st.source["part"] == f"Pololu {it['pololu_item']}" and str(it["pololu_item"]) in st.source["url"]
            # the recorded item is the one in the stored copy of Pololu's list
            assert f"{it['pololu_item']} | Nylon Spacer: {L}mm Length, {rng['od_mm']:g}mm OD, {rng['id_mm']:g}mm ID ({it['pack']}-Pack)" in listing
            assert _size(st) == pytest.approx((rng["od_mm"], rng["od_mm"], float(L)))
            assert st.interfaces["bore"] == rng["id_mm"] and st.interfaces["bore"] > float(size[1:])      # a clearance hole
    assert len(r["M3"]["items"]) == 9 and len(r["M2.5"]["items"]) == 10
    odd = parts.spacer_round("M3", 7.0)                       # not a stock length
    assert not odd.verified and "length" in odd.source["unverified_fields"]
    al = parts.spacer_round("M5", 6.0, "aluminium")           # seen in search snippets only
    assert not al.verified and al.source["level"] == "secondary" and "part number" in al.source["unverified_fields"]
    assert (al.interfaces["od"], al.interfaces["bore"]) == (10.0, 5.1) and al.material == "al6061"
    gen = parts.spacer_round("M3", 6.0, "aluminium")          # no source at all
    assert not gen.verified and gen.ratings["source"] == "typical, unverified" and "vendor_part" not in gen.ratings
    assert len({parts.spacer_round(s, 6.0, m).sku for s in parts.hardware.SPACER_SIZES for m in parts.hardware.SPACER_MATERIALS}) == 8


def test_bed_column_is_catalogued_but_not_verified():
    v = vendor_data("silicone_bed_column")["values"]
    st = parts.bed_column_silicone(18.0)
    assert st.catalog and not st.verified and st.source["level"] == "secondary"
    assert _size(st) == pytest.approx((v["od_mm"], v["od_mm"], 18.0))
    sq = parts.bed_column_silicone(18.0, installed=16.0)
    assert sq.sku == st.sku and _size(sq)[2] == pytest.approx(16.0) and sq.mass_kg == st.mass_kg
    with pytest.raises(ValueError):
        parts.bed_column_silicone(20.0)


def test_gt2_width_is_in_the_sku_only_for_new_widths():
    # 6 and 12 mm parts keep the names existing designs and BOMs use; 9 mm carries its width
    for w in (6.0, 12.0):
        p, i = parts.gt2_pulley(20, 5.0, w), parts.gt2_idler(20, 5.0, w)
        assert p.sku == "GT2-20T-B5" and i.sku == "GT2-IDLER-20T-B5" and "belt_width_mm" not in p.ratings and "belt_width_mm" not in i.ratings
    p, i = parts.gt2_pulley(20, 5.0, 9.0), parts.gt2_idler(20, 5.0, 9.0)
    assert p.sku == "GT2-20T-B5-W9" and i.sku == "GT2-IDLER-20T-B5-W9"
    assert p.ratings["belt_width_mm"] == i.ratings["belt_width_mm"] == 9.0
    assert i.interfaces["height"] == pytest.approx(9.0 + 2.5) and not p.verified and not i.verified


def test_cast_tooling_plate_materials_match_the_recorded_file():
    from mechloop import MATERIALS

    rec = vendor_data("cast_tooling_plate")
    assert rec["source_level"] == "secondary"
    for name, r in rec["materials"].items():
        m = MATERIALS[name]
        assert (m.density, m.E, m.nu, m.yield_mpa) == (r["density_kg_m3"], r["E_mpa"], r["nu"], r["yield_mpa"])
        assert r["recalled"]                                      # nothing here was read from the maker's sheet
    assert MATERIALS["al_mic6"].yield_mpa < MATERIALS["al6061"].yield_mpa / 2      # cast plate is flat, not strong


def test_new_catalog_parts_place_without_uncatalogued_warning():
    from build123d import Location

    from mechloop.model import Design
    from mechloop.verifiers.ratings import verify_ratings

    d = Design("v6_parts_check")
    for i, st in enumerate((parts.extruder_roto(), parts.hotend_revo(), parts.hotend_v6(), parts.spacer_round("M3", 6.0),
                            parts.spacer_round("M5", 6.0, "aluminium"), parts.bed_column_silicone(18.0, 16.0))):
        parts.place(d, f"p{i}", st, Location((100.0 * i, 0, 0)))
    r = verify_ratings(d)
    assert not [f for f in r.findings if f.code == "uncatalogued_cots"]
    assert {"EXTRUDER-E3D-ROTO", "HOTEND-REVO-24V-40W", "HOTEND-V6", "SPACER-NYLON-M3-5x3.3x6"} <= set(r.metrics["vendor_backed_parts"])
    assert {"SPACER-AL-M5-10x5.1x6", "BED-COLUMN-SIL-16x18"} <= set(r.metrics["unverified_parts"])
