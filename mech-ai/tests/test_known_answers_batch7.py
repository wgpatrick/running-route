"""Known-answer tests for the seventh batch of vendor data: the Tr8x2 lead-screw motor 17E19S1684AB4-330RA (motor body and
integral screw as two parts) and the BIGTREETECH Octopus V1.1 (eight driver sockets)."""
import math
from pathlib import Path

import pytest
from build123d import Box, Location, Pos

from mechloop import parts as P
from mechloop.model import Design, Joint
from mechloop.parts import place
from mechloop.verifiers.ratings import verify_ratings


def errs(r):
    return [f.code for f in r.findings if f.severity == "error"]


def test_ab4_figures_from_the_product_page_and_what_is_assumed():
    """Product page: 0.44 N.m, 1.68 A, 1.65 ohm, 2.8 mH, Tr8x2 x 330, 0.01 mm per full step, 46.30 USD. Not on the page:
    inertia (68 g.cm2, sister model), mass (0.35 kg, predecessor's page), axial rating (none)."""
    m = P.leadscrew_motor_17e19_ab4()
    r = m.ratings
    assert (r["holding_torque_nmm"], r["rated_current_a"], r["phase_resistance_ohm"], r["phase_inductance_mh"]) == (440.0, 1.68, 1.65, 2.8)
    assert r["lead_mm"] == 2.0 and r["lead_mm"] / 200 == 0.01 and r["efficiency"] < 0.5 and r["self_locking"]
    assert m.cost_usd == 46.30 and m.sku.startswith("NEMA17") and r["integral_leadscrew"]
    assert r["rotor_inertia_gcm2"] == 68.0 and "assumed" in r["rotor_inertia_basis"]
    assert r["axial_load_rating_n"] is None and "NOT STATED" in r["axial_load_rating_status"]
    assert not m.verified and {"mass_kg", "rotor_inertia_gcm2", "axial_load_rating_n"} <= set(m.source["unverified_fields"])
    s = P.leadscrew_screw_17e19_ab4()
    assert s.cost_usd == 0.0 and r["mass_kg_total"] == 0.35 and m.mass_kg + s.mass_kg == pytest.approx(0.35, abs=1e-3)
    bb = m.shape.bounding_box()
    assert bb.min.Z == pytest.approx(-48.0) and bb.max.Z == pytest.approx(2.0)          # body and pilot only: no screw
    assert s.shape.bounding_box().max.Z == pytest.approx(328.0) and s.ratings["lead_mm"] == 2.0


def test_ab4_screw_cut_to_length_says_so():
    s = P.leadscrew_screw_17e19_ab4(252)
    assert s.sku.endswith("-CUT252") and s.ratings["cut_to_length"] and "cut" in s.description
    assert s.shape.bounding_box().max.Z == pytest.approx(252.0)
    with pytest.raises(ValueError):
        P.leadscrew_screw_17e19_ab4(400)


def test_lead_angle_makes_tr8x2_self_locking_and_tr8x8_not():
    """Lead angle at the pitch diameter against the flank friction angle at mu 0.10 (the low end)."""
    rho = math.degrees(math.atan(0.10 / math.cos(math.radians(15))))
    assert math.degrees(math.atan(2.0 / (math.pi * 7.0))) < rho < math.degrees(math.atan(8.0 / (math.pi * 7.0)))


def three_ab4(bed_kg=4.5):
    d = Design("z3")
    d.add("base", Pos(0, 0, -53) * Box(300, 300, 10))
    d.add("bed", Pos(0, 0, 105) * Box(250, 250, 6), body="zb", mass_kg=bed_kg)
    ms, ss, ns = [], [], []
    for i, (x, y) in enumerate(((-100, -80), (100, -80), (0, 100))):
        place(d, f"zm{i}", P.leadscrew_motor_17e19_ab4(), Location((x, y, 0)))
        place(d, f"zs{i}", P.leadscrew_screw_17e19_ab4(200), Location((x, y, 0)))
        place(d, f"zn{i}", P.leadscrew_nut_t8(), Location((x, y, 80)), body="zb", guides="z")
        d.join(f"zs{i}", f"zm{i}", "integral screw")
        ms.append(f"zm{i}"); ss.append(f"zs{i}"); ns.append(f"zn{i}")
    d.joints.append(Joint("z", "slide", "world", "zb", (0, 0, 1), range=(0, 100), max_speed=12.0, max_accel=200.0,
                          drive={"motor": ms, "kind": "leadscrew", "screw": ss, "nut": ns, "sync": "independent"}))
    return d


def test_three_ab4_share_the_load_and_sum_their_torque():
    """4.5 kg + three 12 g nuts at 200 mm/s^2: (4.536 x 9.81 + 4.536 x 0.2) / 3 = 15.1 N per motor, no rating: three
    warnings. Force without an electrical model: 3 x 2 pi x 0.7 x 440 x 0.35 / 2 = 1016 N."""
    r = verify_ratings(three_ab4())
    assert not errs(r), [f.message for f in r.findings if f.severity == "error"]
    al = r.metrics["leadscrew_axial_loads"]
    assert set(al) == {"zm0", "zm1", "zm2"} and al["zm0"]["screws_sharing"] == 3
    assert al["zm0"]["axial_load_n"] == pytest.approx(4.536 * (9.81 + 0.2) / 3, abs=0.05)
    assert len([f for f in r.findings if f.code == "axial_load_rating_unknown"]) == 3
    assert r.metrics["drives"]["z"]["available_effort"] == pytest.approx(3 * 2 * math.pi * 0.7 * 440 * 0.35 / 2, rel=0.01)


def test_octopus_v11_board_ports_limits_and_pins():
    """Manual: 160 x 100, holes 150 x 90, bed 300 W (12.5 A at 24 V), 5 V rail 8 A; eight driver sockets, nine outputs
    (MOTOR2_1 / MOTOR2_2 on one driver). Pins: BTT pin drawing = Klipper's octopus-v1.1 cfg."""
    st = P.octopus_v11()
    e = st.ratings["electrical"]
    assert st.sku == "CTRL-OCTOPUS-V1.1" and st.ratings["stepper_drivers"] == 8 and e["kind"] == "board"
    bb = st.shape.bounding_box()
    assert (bb.max.X - bb.min.X, bb.max.Y - bb.min.Y) == pytest.approx((160.0, 100.0))
    assert sorted(st.interfaces["mount_holes_m3"])[0][:2] == pytest.approx((-75.0, -45.0))
    p = e["ports"]
    steppers = {k: v for k, v in p.items() if v["kind"] == "stepper_out"}
    assert len(steppers) == 9 and len({v["group"] for v in steppers.values()}) == 8 and p["M2B"]["pin"] == p["M2"]["pin"]
    assert p["HB"]["max_a"] == 12.5 and e["ratings"]["rail_5v_max_a"] == 8.0 and e["ratings"]["driver_modules_included"] is False
    assert p["M0"]["pin"] == {"step": "PF13", "dir": "PF12", "enable": "PF14", "uart": "PC4", "diag": "PG6", "diag_jumper": "DIAG0"}
    assert p["M7"]["pin"]["step"] == "PE6" and p["M7"]["pin"]["uart"] == "PD3"
    assert (p["HB"]["pin"], p["HE0"]["pin"], p["THB"]["pin"], p["TH0"]["pin"], p["FAN0"]["pin"], p["PS-ON"]["pin"]) == ("PA1", "PA2", "PF3", "PF4", "PA8", "PE11")
    assert [p[f"STOP{i}"]["pin"] for i in range(8)] == ["PG6", "PG9", "PG10", "PG11", "PG12", "PG13", "PG14", "PG15"]
    assert not st.verified and "heater and fan current limits" in st.source["unverified_fields"]
    with pytest.raises(ValueError, match="needed data"):
        P.octopus_v11("TMC5160")
    cfg = Path(__file__).parent.parent / "third_party" / "klipper" / "config" / "generic-bigtreetech-octopus-v1.1.cfg"
    if cfg.exists():
        t = cfg.read_text()
        for frag in ("step_pin: PF13", "dir_pin: PF12", "enable_pin: !PF14", "#uart_pin: PC4", "heater_pin: PA1", "heater_pin: PA2 # HE0",
                     "#step_pin: PE6", "#uart_pin: PD3", "endstop_pin: PG10", "sensor_pin: PF3 # TB"):
            assert frag in t, frag
