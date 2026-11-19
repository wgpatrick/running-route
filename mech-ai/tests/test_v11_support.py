"""printer_v11 support: catalogue additions (blower, POM nut, 220 sheet, flanged button head, re-made large washers, M2
hardware), supplier CAD in the inbox, the slot cavity's taper, a declared nut reverse gap, and the design's stock-size rules."""
import importlib
import sys
from pathlib import Path

import pytest

from mechloop import parts
from mechloop.parts import vendor_cad as vc
from mechloop.parts.batch10 import blower_flow_estimate

ROOT = Path(__file__).resolve().parents[1]


def test_blower_matches_data_sheet():
    st = parts.blower_gdb4010()
    bb = st.shape.bounding_box()
    assert (round(bb.size.X, 3), round(bb.size.Y, 3), round(bb.size.Z, 3)) == (40.0, 40.0, 10.0)
    assert st.ratings["rated_current_a"] == 0.08 and st.ratings["rated_voltage_v"] == 24.0
    assert st.ratings["static_pressure_pa"] == pytest.approx(0.52 * 249.089, abs=0.1)
    assert "NOT STATED" in st.ratings["bearing"]
    assert st.ratings["electrical"]["kind"] == "fan"
    assert vc.model_state(st.model) == "stand-in"


def test_flow_estimate_is_on_both_curves():
    e = blower_flow_estimate(30.0, 1.85)
    assert 0.3 < e["flow_cfm"] < 1.2
    v = e["outlet_velocity_m_s"]
    assert e["pressure_pa"] == pytest.approx(1.85 * 0.5 * 1.2 * v * v, rel=0.03)
    assert blower_flow_estimate(60.0, 1.85)["flow_cfm"] > e["flow_cfm"]      # a bigger outlet passes more air


def test_pom_nut_is_a_labelled_standin():
    st = parts.leadscrew_nut_pom_ab4()
    assert st.cost_usd == 0.0 and vc.model_state(st.model) == "stand-in"
    assert st.source["level"] == "proxy"
    bb = st.shape.bounding_box()
    assert bb.max.Z == pytest.approx(0.0, abs=1e-6) and bb.min.Z == pytest.approx(-32.0, abs=1e-6)


def test_sheet_220_and_flanged_button_head():
    sh = parts.print_sheet_pei220()
    assert sh.interfaces["size"] == (220.0, 220.0) and sh.source["level"] == "secondary"
    b = parts.bhcs_flanged("M5", 8)
    assert b.sku == "BHCS-FL-M5x8" and b.interfaces["head_d"] == 11.8 and b.interfaces["head_h"] == 2.75
    assert b.interfaces["head_d"] < 12.0          # fits between the cast corner bracket's webs (12 mm apart)


def test_large_washers_are_faithful_remakes():
    for size, od, t in (("M3", 9.0, 0.9), ("M4", 12.0, 1.1)):
        w = parts.hardware.washer_flat(size, "large")
        assert w.interfaces["od"] == od and w.interfaces["thickness"] == t
        assert vc.model_state(w.model) == "faithful re-make" and w.material == "stainless304"


def test_m2_hardware_exists():
    assert parts.SCREW["M2"][0] == 2.0 and parts.NUT["M2"] == (4.0, 1.6)
    assert parts.clearance_hole("M2") == pytest.approx(2.2) and parts.printed_clearance_hole("M2") == pytest.approx(2.6)
    assert parts.shcs("M2", 20).interfaces["thread_d"] == 2.0


@pytest.mark.parametrize("sku,fn", [("THUMBNUT-DIN466-M4", lambda: parts.thumb_nut_din466("M4")),
                                    ("SPRING-DIE-DJ-8X20YCS", lambda: parts.die_spring_dj8x20(12)),
                                    ("INLET-C14-SW-FUSE-T8A", lambda: __import__("mechloop.parts.electrical", fromlist=["x"]).iec_inlet_c14(8.0)),
                                    ("PROBE-OMRON-E2E-X5ME1", lambda: parts.probe_omron_e2e("E2E-X5ME1", clamp=(15, 17.286), nuts="separate"))])
def test_supplier_files_adopted_and_consistent(sku, fn):
    st = fn()
    assert st.sku == sku
    assert vc.model_state(st.model) == "supplier CAD", st.model
    findings, _ = vc.check_stock(st)
    assert findings == [], findings


def test_extrusion_display_model_is_misumis_section():
    st = parts.extrusion_2020(300)
    assert st.model["kind"] == "vendor CAD" and "HFS5-2020-500" in st.model.get("file", "")
    assert "cut to length" in st.source["note"] and "unreachable" not in st.source["note"]


def test_slot_cavity_taper_recorded():
    sl = parts.slot_2020()
    assert sl["cavity_full_depth"] == pytest.approx(0.939) and sl["floor_width"] == pytest.approx(5.878)
    w_at = sl["cavity_width"] - 2 * (2.4 - sl["cavity_full_depth"])
    assert w_at == pytest.approx(9.078, abs=1e-3) and w_at > 8.0      # the HNTAJ5 body still fits


def test_declared_nut_reverse_gap():
    from mechloop.verifiers.bed_support import nut_seating

    class J:
        name = "z"
        drive = {"nut_seating": "captive", "nut_reverse_gap_mm": 0.1, "nut_reverse_gap_basis": "keeper play"}

    class D:
        adjustments = []

    out = nut_seating(D(), {"joint": J()})
    assert out["kind"] == "captive" and out["reverse_gap_mm"] == 0.1 and out["reverse_gap_note"] == "keeper play"


@pytest.fixture(scope="module")
def v11():
    sys.path.insert(0, str(ROOT / "designs"))
    return importlib.import_module("printer_v11")


def test_v11_constants(v11):
    assert v11.X_RAIL_L == 250.0 and v11.PRINT_X == pytest.approx(2 * (v11.X_CAR_MAX - v11.ES_OT_X))
    assert v11.Z_SCREW_ABOVE == 328.0
    assert v11.SHEET == 220.0 and v11.T_BED == pytest.approx(6.35)
    assert v11.FS_X + 4.0 < v11.FX / 2 - 20.0          # front screws inboard of the side rails' inner faces
    assert v11.LS_Y - 21.15 > v11.FY / 2               # the rear motor clears the back wall's outer face
    assert all(L in parts.hardware.spacer_lengths("M5", "aluminium") for L in v11.POSTS_R + v11.POSTS_F)


def test_v11_builds_with_stock_parts(v11):
    d = v11.build()
    assert not [c.name for c in d.components if c.ratings.get("cut_to_length")]
    assert d.get("x_rail").shape.bounding_box().size.X == pytest.approx(250.0)
    assert sorted(c.name for c in d.components if not c.cots and c.material == "al5052") == ["probe_mount", "x_belt_bracket"]
    assert not any(c.name.startswith("x_tension") for c in d.components)
    bb = [c.shape.bounding_box() for c in d.components]
    size = (max(b.max.X for b in bb) - min(b.min.X for b in bb), max(b.max.Y for b in bb) - min(b.min.Y for b in bb),
            max(b.max.Z for b in bb) - min(b.min.Z for b in bb))
    assert all(s <= e for s, e in zip(size, v11.ENVELOPE))


def test_delta_blower_and_omron_e2b_are_labelled_standins_picked_up_by_the_inbox_names():
    b = parts.blower_bfb0524hh()
    assert b.ratings["rated_current_a"] == 0.11 and b.ratings["static_pressure_pa"] == 216.0 and b.cost_usd == 17.0
    assert b.ratings["electrical"]["ratings"]["current_a"] == 0.11 and "BFB0524HH" in b.model.get("inbox", [])
    assert vc.model_state(b.model) == "stand-in"
    p = parts.probe_omron_e2e("E2B-M12KS04-WP-C1", clamp=(15, 17.286), nuts="separate")
    el = p.ratings["electrical"]["ratings"]
    assert p.cost_usd == pytest.approx(35.22) and el["output"] == "npn_no" and el["max_ambient_c"] == 70.0
    assert el["switching_distance_steel_mm"] == 4.0
    assert p.interfaces["mounting"]["shielded"] and p.interfaces["mounting"]["head_proud_of_metal_l"] == 0.0
    assert "E2B-M12KS04-WP-C1" in p.model.get("inbox", [])
