"""Known-answer tests for the sixth batch of vendor data (vendor_cad/staging/MANIFEST.md, "Batch 6"): the lead-screw
motor, the MANTA M5P controller, the Coolerguys 24 V fan, MIC-6 from the maker's brochure, MGN15, the relay's contact
marking, the PEI sheet, the corrected M3x6 screw and the coupler's unpublished figures. Small purpose-built designs."""
import math
import sys
from pathlib import Path

import pytest
from build123d import Box, Cylinder, Location, Pos

from mechloop import parts as P
from mechloop.model import Design, Joint
from mechloop.parts import place, vendor_data
from mechloop.verifiers.ratings import verify_ratings

sys.path.insert(0, str(Path(__file__).parent))


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


# ---------------------------------------------------------------- 1. lead-screw motor
def z_on_leadscrew_motors(n=1, bed_kg=1.5, accel=100.0):
    """A bed of `bed_kg` lifted along Z by `n` lead-screw motors, each with its nut on the bed."""
    d = Design("ls")
    d.add("base", Pos(0, 0, -53) * Box(200, 100, 10))
    d.add("bed", Pos(0, 0, 105) * Box(180, 80, 6), body="zb", mass_kg=bed_kg)
    names = []
    for i in range(n):
        x = (i - (n - 1) / 2) * 120.0
        place(d, f"zm{i}", P.leadscrew_motor_17e19(), Location((x, 0, 0)))
        place(d, f"zn{i}", P.leadscrew_nut_17e19(), Location((x, 0, 80)), body="zb", guides="z")
        names.append(f"zm{i}")
    d.joints.append(Joint("z", "slide", "world", "zb", (0, 0, 1), range=(0, 150), max_speed=8.0, max_accel=accel,
                          drive={"motor": names if n > 1 else names[0], "kind": "leadscrew", "screw": names[0], "nut": "zn0"}))
    return d


def test_leadscrew_motor_figures_conflicts_and_gaps():
    """17E19S1684MB4-300RS: 0.44 N.m, 1.68 A, 1.65 ohm, 2.80 mH, 68 g.cm2, Tr8x8 (lead 8 mm: 8 / 200 = 0.04 mm per full
    step), body 42.3 x 48. Mass: drawing 0.35 kg, product page 454 g: both kept, the heavier used. No axial rating."""
    st = P.leadscrew_motor_17e19()
    r = st.ratings
    assert (r["holding_torque_nmm"], r["rated_current_a"], r["phase_resistance_ohm"], r["phase_inductance_mh"], r["rotor_inertia_gcm2"]) == (440.0, 1.68, 1.65, 2.8, 68.0)
    assert r["lead_mm"] == 8.0 and r["lead_mm"] / 200 == 0.04
    assert st.mass_kg == 0.454 and (r["mass_kg_datasheet"], r["mass_kg_product_page"]) == (0.35, 0.454)
    assert r["axial_load_rating_n"] is None and "NOT STATED" in r["axial_load_rating_status"]
    bb = st.shape.bounding_box()
    assert bb.min.Z == pytest.approx(-48.0) and bb.max.Z == pytest.approx(298.0) and bb.max.Y - bb.min.Y == pytest.approx(42.3)
    assert not st.verified and {"mass_kg", "axial_load_rating_n"} <= set(st.source["unverified_fields"])
    # distinct from the catalogue's separate screw as the printers use it (lead 2 mm behind a coupler)
    t8 = P.leadscrew_t8(300, lead=2.0)
    assert t8.sku != st.sku and t8.ratings["lead_mm"] == 2.0 and "LEADSCREW-TR8x8" in st.sku
    nut = P.leadscrew_nut_17e19()
    assert nut.interfaces["flange_dia"] == 25.4 and nut.interfaces["length"] == 19.05 and len(nut.interfaces["mount_holes_m3"]) == 3


def test_leadscrew_motor_drives_a_joint_without_a_coupler_and_its_axial_load_is_reported():
    """One motor lifting 1.5 kg + its 4 g nut at 100 mm/s^2: weight 1.504 x 9.81 = 14.75 N, acceleration 0.15 N, axial load
    14.9 N. The maker gives no axial rating: a warning with that number, not a silent pass. Drive force without an
    electrical model: 2 pi x (0.7 x 440 N.mm) x 0.5 / 8 mm = 121 N. Two motors share the load: 7.5 N each."""
    r = verify_ratings(z_on_leadscrew_motors(1))
    assert not errs(r)
    dv = r.metrics["drives"]["z"]
    assert dv["kind"] == "leadscrew" and dv["available_effort"] == pytest.approx(2 * math.pi * 0.7 * 440 * 0.5 / 8, abs=0.1)
    assert dv["resolution_per_full_step"] == 0.04
    al = r.metrics["leadscrew_axial_loads"]["zm0"]
    assert al["weight_along_axis_n"] == pytest.approx(1.504 * 9.81, abs=0.02) and al["axial_load_n"] == pytest.approx(14.9, abs=0.05)
    assert al["rating_n"] is None
    f = [x for x in r.findings if x.code == "axial_load_rating_unknown"]
    assert len(f) == 1 and f[0].severity == "warning" and "14.9 N" in f[0].message and "NOT checked" in f[0].message
    r2 = verify_ratings(z_on_leadscrew_motors(2))
    loads = r2.metrics["leadscrew_axial_loads"]
    assert set(loads) == {"zm0", "zm1"} and loads["zm0"]["axial_load_n"] == pytest.approx((1.508 * 9.81 + 0.1508) / 2, abs=0.05)
    assert len([x for x in r2.findings if x.code == "axial_load_rating_unknown"]) == 2


def test_a_stated_axial_rating_is_enforced():
    d = z_on_leadscrew_motors(1)
    d.get("zm0").ratings.update(axial_load_rating_n=10.0)
    assert "axial_load_over_rating" in errs(verify_ratings(d))
    d.get("zm0").ratings.update(axial_load_rating_n=50.0)
    r = verify_ratings(d)
    assert not errs(r) and r.metrics["leadscrew_axial_loads"]["zm0"]["margin"] == pytest.approx(50 / 14.9, abs=0.02)


# ---------------------------------------------------------------- 2. MANTA M5P
def test_manta_m5p_board_ports_limits_and_host():
    """Manual: bed 10 A, heaters 5.5 A, fans 1 A; SIZE drawing: 137.39 x 95, holes 128.39 x 86 (4.5 mm from each edge);
    five driver sockets, drivers not included; core-board host (CM4 / CB1). Pins: Klipper's example config."""
    st = P.manta_m5p()
    e = st.ratings["electrical"]
    assert st.sku == "CTRL-MANTA-M5P" and st.ratings["stepper_drivers"] == 5 and e["kind"] == "board"
    bb = st.shape.bounding_box()
    assert (bb.max.X - bb.min.X, bb.max.Y - bb.min.Y) == pytest.approx((137.39, 95.0))
    assert sorted(st.interfaces["mount_holes_m3"])[0][:2] == pytest.approx((-64.195, -43.0))
    assert (137.39 - 128.39) / 2 == pytest.approx(4.5) and (95 - 86) / 2 == 4.5
    p = e["ports"]
    assert (p["HB"]["max_a"], p["HE0"]["max_a"], p["HE1"]["max_a"], p["FAN0"]["max_a"]) == (10.0, 5.5, 5.5, 1.0)
    assert {k for k, v in p.items() if v["kind"] == "stepper_out"} == {"M1", "M2", "M3", "M3B", "M4", "M5"}
    assert len({v["group"] for v in p.values() if v["kind"] == "stepper_out"}) == 5 and p["M3B"]["pin"]["step"] == p["M3"]["pin"]["step"]
    assert p["M1"]["pin"] == {"step": "PC8", "dir": "!PC9", "enable": "PA15", "uart": "PD9", "diag": "PD3", "diag_jumper": "M1 DIAG"}
    assert p["M5"]["pin"]["uart"] == "PA6" and (p["HB"]["pin"], p["HE0"]["pin"], p["THB"]["pin"], p["TH0"]["pin"], p["PROBE"]["pin"]) == ("PA5", "PC5", "PA0", "PA1", "PC15")
    assert e["ratings"]["driver_modules_included"] is False and e["ratings"]["supply_v"] == (12.0, 24.0)
    assert "CM4" in e["ratings"]["host_on_board"] and not st.verified
    with pytest.raises(ValueError, match="needed data"):
        P.manta_m5p("TMC5160")
    # the pins agree with the Klipper file they are said to come from
    cfg = (Path(__file__).parent.parent / "third_party" / "klipper" / "config" / "generic-bigtreetech-manta-m5p.cfg")
    if cfg.exists():
        t = cfg.read_text()
        for frag in ("step_pin: PC8", "dir_pin: !PC9", "#uart_pin: PD9", "heater_pin: PA5", "#uart_pin: PA6", "#step_pin: PB0"):
            assert frag in t


def test_manta_driver_sections_have_one_uart_pin_each_and_no_bus_address():
    """SKR Mini E3 V3: one UART bus, so uart_pin + tx_pin + uart_address. MANTA M5P: a UART pin per socket, nothing else."""
    from mechloop.electrical import _tmc_uart_lines
    from mechloop.parts.electrical import skr_mini_e3_v3

    m = P.manta_m5p().ratings["electrical"]["ports"]["M3"]["pin"]
    assert _tmc_uart_lines(m) == ["uart_pin: PB10"]
    s = skr_mini_e3_v3().ratings["electrical"]["ports"]["ZAM"]["pin"]
    assert _tmc_uart_lines(s) == ["uart_pin: PC11", "tx_pin: PC10", "uart_address: 1"]


# ---------------------------------------------------------------- 3. the 24 V fan with a sheet
def test_cg3010u24_is_a_24v_fan_with_the_makers_figures(tmp_path, monkeypatch):
    """Coolerguys CG3010U24: 24 V, 0.07 A (1.68 W), 5.45 CFM = 0.154 m3/min, 8.01 mmH2O = 78.6 Pa, 8 g. On a 24 V fan
    output: no voltage mismatch, 0.07 A in the budget."""
    import test_electrical as TE
    from mechloop.parts.electrical import device_from
    from mechloop.verifiers import electrical as VE

    st = P.fan_cg3010u24()
    r = st.ratings
    assert (r["rated_voltage_v"], r["rated_current_a"], r["air_flow_cfm"], r["speed_rpm"], st.mass_kg) == (24.0, 0.07, 5.45, 13400, 0.008)
    assert r["air_flow_m3_min"] == pytest.approx(0.1543, abs=1e-4) and r["static_pressure_pa"] == pytest.approx(8.01 * 9.80665, abs=0.1)
    assert st.sku == "FAN-3010-CG3010U24" and "mount hole pattern" in st.source["unverified_fields"]
    monkeypatch.chdir(tmp_path)
    d = TE.rig()
    place(d, "pfan", st, Location((0, 150, 90)))
    d.join("pfan", "hotend", "bond")
    device_from(d.electrical, d, "pfan")
    d.electrical.wire("part fan", "board.FAN0", "pfan.in", 26)
    res = VE.verify_electrical(d)
    row = res.metrics["power_budget"]["fans"]["pfan"]
    assert not errs(res) and (row["rated_v"], row["supplied_v"], row["current_a"]) == (24.0, 24.0, 0.07)


# ---------------------------------------------------------------- 4. MIC-6
def test_mic6_values_are_the_makers_and_the_density_is_marked():
    """Alcoa brochure: tensile 166, yield 105 MPa, E 71 GPa, 142 W/m.K, 23.6e-6 /K; flatness 0.381 mm for 1/4 to 5/8 in
    plate and 0.127 mm from 3/4 in. Density is not in the brochure: 2800 kept, marked."""
    from mechloop import MATERIALS
    from mechloop.tolerance.process import stock_plate_flatness
    from mechloop.verifiers.fea import ALPHA

    m, rec = MATERIALS["al_mic6"], vendor_data("cast_tooling_plate")["materials"]["al_mic6"]
    assert (m.E, m.yield_mpa, m.density) == (71000, 105, 2800) and ALPHA["al_mic6"] == 23.6e-6
    b = rec["confirmed_by_brochure"]["values"]
    assert (b["tensile_mpa_typ"], b["yield_mpa_typ"], b["E_mpa"], b["thermal_conductivity_w_mk"], b["cte_per_k_20_100c"]) == (166, 105, 71000, 142, 2.36e-05)
    assert "NOT in the Alcoa brochure" in rec["density_note"]["status"] and any("density" in x for x in rec["recalled"])
    assert stock_plate_flatness("al_mic6", 6.35)["flatness_mm"] == 0.381 and stock_plate_flatness("al_mic6", 15.875)["flatness_mm"] == 0.381
    assert stock_plate_flatness("al_mic6", 19.05)["flatness_mm"] == 0.127 and "Alcoa" in stock_plate_flatness("al_mic6", 6.35)["source"]
    assert not stock_plate_flatness("al_mic6", 6.0)["stock_thickness_listed"]


# ---------------------------------------------------------------- 5. MGN15
def test_mgn15_parts_carry_hiwins_figures_and_the_limo_cad_is_only_a_cross_check():
    """Hiwin MGN15H: 58.8 x 32, top 16 above the rail base, underside 4, M3 x 4 on 25 x 25, Cdyn 6370 / C0 9110 N,
    rigidity 87 (Z0) / 113 (Z1) N/um, L1 43.4 mm; two rails 10 um (ZF, Z0) or 6 um (Z1). Rail 15 x 10, holes every 40 mm:
    a 150 mm rail has holes at -60, -20, 20, 60 (15 mm from each end), as LiMo's 150 mm model has."""
    car, rail = P.mgn15h_carriage(), P.mgn15_rail(150)
    bb = car.shape.bounding_box()
    assert (bb.max.X - bb.min.X, bb.max.Y - bb.min.Y, bb.min.Z, bb.max.Z) == pytest.approx((58.8, 32.0, 4.0, 16.0))
    assert sorted(car.interfaces["mount_holes_m3"]) == [(-12.5, -12.5, 16.0), (-12.5, 12.5, 16.0), (12.5, -12.5, 16.0), (12.5, 12.5, 16.0)]
    assert car.interfaces["thread_depth"] == 4.0 and (car.ratings["dynamic_load_n"], car.ratings["static_load_n"]) == (6370.0, 9110.0)
    assert car.ratings["radial_stiffness_n_per_m"] == 87e6 and P.mgn15h_carriage("Z1").ratings["radial_stiffness_n_per_m"] == 113e6
    assert "radial_stiffness_n_per_m" not in P.mgn15h_carriage("ZF").ratings and car.ratings["preload_class_basis"].startswith("assumed")
    assert car.ratings["allowable_parallelism_mm"] == 0.010 and P.mgn15h_carriage("Z1").ratings["allowable_parallelism_mm"] == 0.006
    assert car.ratings["ball_track_length_m"] == pytest.approx(0.0434) and car.ratings["static_moment_nm"] == 57.8
    assert [h[0] for h in rail.interfaces["mount_holes_m3"]] == [-60.0, -20.0, 20.0, 60.0] and rail.interfaces["end_distance"] == 15.0
    assert rail.mass_kg == pytest.approx(1.06 * 0.150) and rail.shape.bounding_box().max.Z == pytest.approx(10.0)
    assert car.verified and "VENDOR-EQUIVALENT" in car.source["note"] and car.model["kind"] == "proxy"
    lm = vendor_data("limo_mgn15")["step_measured_mm"]
    assert (lm["block"]["length_with_end_caps_and_seals"], lm["block"]["width"], lm["block"]["top_above_rail_base"], lm["block"]["thread_depth"]) == (58.8, 32.0, 16.0, 4.0)
    assert lm["rail"]["hole_pitch"] == 40.0 and lm["rail"]["end_distance"] == 15.0


def test_mgn15_tilt_stiffness_by_hand():
    """Two MGN15H side by side: K = 2 k L1^2 / 12 = 2 x 87e6 x 0.0434^2 / 12 = 27,312 N.m/rad (MGN12H: 11,022)."""
    d = Design("z")
    for i, x in enumerate((-90, 90)):
        place(d, f"rail{i}", P.mgn15_rail(200), Location((x, 0, 0), (0, -90, 0)))
        place(d, f"blk{i}", P.mgn15h_carriage(), Location((x, 0, 0), (0, -90, 0)), body="z", guides="z")
    d.add("arm", Pos(0, 150, 0) * Box(200, 280, 6), body="z", mass_kg=2.0)
    d.joints.append(Joint("z", "slide", "world", "z", (0, 0, 1), range=(-50, 50), max_effort=1000))
    g = verify_ratings(d).metrics["guide_loads"]["z"]
    assert g["tilt_stiffness_nm_per_rad"] == pytest.approx(2 * 87e6 * 0.0434 ** 2 / 12, abs=1.0) and g["block_stiffness_assumed_n_per_um"] == 87.0


# ---------------------------------------------------------------- 6. relay contact rating
def test_relay_contact_rating_is_the_component_marking_and_is_compared_with_the_mains_current(tmp_path, monkeypatch):
    """SONGLE SRD-05VDC-SL-C: 10 A 250 VAC on the casing. The rig's supply draws 6.8 A at 115 V at full load; the check
    wants contact >= current x the fuse factor. 10 A passes; the same relay marked 5 A would not."""
    import test_electrical as TE
    from mechloop.parts.electrical import relay_btt_v12
    from mechloop.verifiers import electrical as VE

    tpl = relay_btt_v12().ratings["electrical"]
    assert tpl["ratings"]["contact_a"] == 10.0 and "SONGLE SRD-05VDC-SL-C" in tpl["sources"]["contact_a"]
    assert "COMPONENT marking" in tpl["sources"]["contact_a"] and "inrush" in tpl["sources"]["contact_a"]
    assert vendor_data("bigtreetech_relay_v12")["contact_rating"]["marking"]["250_vac_a"] == 10
    monkeypatch.chdir(tmp_path)
    d = TE.rig()
    assert "relay_contact_too_small" not in errs(VE.verify_electrical(d))
    d.electrical.devices["relay"].ratings["contact_a"] = 1.0
    assert "relay_contact_too_small" in errs(VE.verify_electrical(d))


# ---------------------------------------------------------------- 7. print sheet
def test_print_sheet_has_the_sellers_figures_and_says_what_is_unpublished():
    """180 x 180 x 0.4 mm of steel: 180 x 180 x 0.4 x 7.85e-6 = 0.1017 kg (computed; no mass is published). Base to 130 degC
    (claimed). The magnetic base's thickness is unknown and it is not drawn."""
    st = P.print_sheet_pei180()
    bb = st.shape.bounding_box()
    assert (bb.max.X - bb.min.X, bb.max.Y - bb.min.Y, bb.max.Z) == pytest.approx((180.0, 180.0, 0.4))
    assert st.mass_kg == pytest.approx(0.1017, abs=1e-4) and "computed" in st.ratings["mass_basis"]
    assert st.ratings["magnetic_base_max_temp_c"] == 130.0 and "claim" in st.ratings["magnetic_base_max_temp_basis"]
    assert st.interfaces["magnetic_base_thickness"] is None and st.ratings["steel_grade"] is None and not st.verified
    assert {"mass_kg", "steel grade", "magnetic base thickness"} <= set(st.source["unverified_fields"])


# ---------------------------------------------------------------- 8, 9. corrected screw file, coupler gaps
def test_m3x6_part_number_is_confirmed_now():
    """The corrected STEP is McMaster 91290A111: 5.5 mm head, 3 + 6 = 9 mm overall."""
    r = P.shcs("M3", 6).ratings
    assert r["mcmaster_pn"] == "91290A111" and r["mcmaster_pn_status"].startswith("confirmed")
    m = vendor_data("mcmaster_fasteners")
    assert "SHCS-M3x6.step" not in m["wrong_file"] and m["screws"]["SHCS-M3x6"]["bounding_box_mm"] == [5.5, 5.5, 9.0]


def test_coupler_misalignment_stays_assumed_and_the_unpublished_figures_are_none():
    st = P.shaft_coupler(5.0, 8.0)
    assert st.ratings["angular_misalignment_deg"] == 1.0 and st.ratings["angular_misalignment_assumed"] is True
    assert st.ratings["parallel_misalignment_mm"] is None and st.ratings["axial_stiffness_n_per_mm"] is None
    gaps = vendor_data("stepperonline_coupler")["not_published_by_the_maker"]
    assert gaps["angular_misalignment"] == gaps["parallel_misalignment"] == "not published" and "TORSIONAL" in gaps["axial_stiffness"]
