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
    assert d["retrieved"] == "2026-11-14"
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


def test_mgn12_matches_recorded_table_but_is_not_called_verified():
    d = vendor_data("hiwin_mgn12")
    assert d["source_level"] == "secondary"
    b, r = d["parts"]["MGN12H_block"]["values"], d["parts"]["MGNR12_rail"]["values"]
    car, rail = parts.mgn12h_carriage(), parts.mgn12_rail(300)
    assert not car.verified and not rail.verified and car.source["level"] == "secondary"
    assert car.ratings["approximate"] is True
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
    assert f[0].data["parts"] == ["BRG-608", "MGN12H"]
    assert "NEMA17-48" not in f[0].message and "MGN12H" in f[0].message
