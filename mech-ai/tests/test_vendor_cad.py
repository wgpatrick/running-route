"""Vendor / community CAD behind the catalog parts: every model loads, sits in its part's frame (the proxy-match
check passes), has a SOURCES.md entry; a wrong simulation solid is caught; what the CAD adds is tested against the
neighbours; a hand-downloaded file in vendor_cad/inbox/ replaces a model with no code change."""
import copy
from pathlib import Path

import pytest
from build123d import Box, Cylinder, Location, Pos, Rot

from mechloop import Design
from mechloop.parts import (corner_bracket_2020, control_board, endstop_switch, extrusion_2020, extruder_roto, fan, gt2_idler, hex_nut,
                            hotend_revo, hotend_v6,
                            leadscrew_nut_t8, mgn12_rail, mgn12h_carriage, nema17, place, psu_24v, shaft_coupler, shcs)
from mechloop.parts import vendor_cad as vc
from mechloop.parts.electrical import psu_lrs, skr_mini_e3_v3
from mechloop.verifiers.geometry import verify_geometry

WITH_CAD = [
    lambda: nema17(34), lambda: nema17(40), lambda: nema17(48), lambda: nema17(60),
    lambda: mgn12_rail(215), lambda: mgn12_rail(300), mgn12h_carriage, lambda: extrusion_2020(340), corner_bracket_2020,
    lambda: gt2_idler(20, 5.0, 6.0), leadscrew_nut_t8, endstop_switch, lambda: fan(30), lambda: fan(40),
    control_board, skr_mini_e3_v3, lambda: psu_lrs("LRS-350-24"), lambda: psu_24v(350),
    lambda: shcs("M3", 8), lambda: shcs("M5", 35), lambda: shcs("M2.5", 12), lambda: hex_nut("M3"), lambda: hex_nut("M5"),
    hotend_v6, extruder_roto, hotend_revo, lambda: hotend_revo(40, 12.0), shaft_coupler,
]


@pytest.mark.parametrize("make", WITH_CAD)
def test_detail_model_loads_and_matches_its_proxy(make):
    st = make()
    assert st.detail is not None, f"{st.sku} has no detail model"
    assert st.model["kind"] in ("vendor CAD", "community CAD", "generated to standard")
    assert st.detail.solids() and st.model["source"]
    bad, meas = vc.check_stock(st)
    assert not bad, [b["message"] for b in bad]
    assert meas["volume_cad_mm3"] > 0


def test_every_file_has_a_sources_entry_and_nothing_else_is_in_the_folder():
    rows = vc.sources_table()
    used = set()
    for make in WITH_CAD:
        st = make()
        if "derived_from" in st.model:           # a file cut from a larger download: the unchanged download is kept beside it
            src = Path(st.model["derived_from"]).name
            used.add(src)
            assert src in rows and (vc.root() / src).exists() and "unchanged" in rows[src]["origin"]
        if "fallback" in st.model:               # a file kept for when the supplier file in the inbox is absent (still listed)
            used.add(Path(st.model["fallback"]).name)
        if "file" in st.model:
            name = Path(st.model["file"]).name
            if Path(st.model["file"]).parent.name == "inbox":      # a supplier file promoted to the inbox (checked below)
                assert f"inbox/{name}" in rows, f"inbox/{name} is not in vendor_cad/SOURCES.md"
                continue
            used.add(name)
            assert name in rows, f"{name} is not in vendor_cad/SOURCES.md"
            assert (vc.root() / name).exists()
            made = rows[name]["made by"]
            assert ("vendor" in made) == (st.model["kind"] == "vendor CAD"), f"{name}: {made} vs {st.model['kind']}"
            assert rows[name]["licence"] and rows[name]["origin"]
    on_disk = {p.name for p in vc.root().iterdir() if p.suffix.lower() in (".step", ".stp")}
    root_rows = {k for k in rows if not k.startswith("inbox/")}
    assert on_disk == used == root_rows, (on_disk ^ used, root_rows ^ used)
    assert all((vc.root() / n).stat().st_size < 5.2e6 for n in on_disk)
    # supplier files in the inbox (2026-11-18 batch): every one has a row naming the supplier and its part number
    inbox = {f"inbox/{p.name}" for p in (vc.root() / "inbox").iterdir() if p.suffix.lower() in (".step", ".stp")}
    assert inbox == set(rows) - root_rows, inbox ^ (set(rows) - root_rows)
    for k in inbox:
        assert "vendor" in rows[k]["made by"] and "McMaster-Carr 9" in rows[k]["origin"] and rows[k]["licence"], k
        assert (vc.root() / k).stat().st_size < 5.2e6


def test_parts_without_cad_say_proxy():
    st = shaft_coupler(6.35, 8.0)                               # the 5 x 8 mm coupler has StepperOnline's STEP; other bores have none
    assert st.detail is None and st.model["kind"] == "proxy"
    assert gt2_idler(20, belt_width=12.0).model["kind"] == "proxy"      # only the 6 mm idler has a model


def test_roto_and_revo_are_e3ds_reference_cad_in_the_part_frames():
    """E3D's Roto reference file (hand-downloaded) is split into cold side and hot side; both sit in their part's
    frame, and the hot side placed at the Roto's `hotend_seat` is E3D's own assembly again."""
    import numpy as np

    ex, hot = extruder_roto(), hotend_revo()
    for st in (ex, hot):
        assert st.model["kind"] == "vendor CAD" and st.model["derived_from"] == "vendor_cad/e3d_roto_reference_cad.step"
        assert not vc.excess_hulls(st, st.model["key"])         # nothing of the CAD sticks out of the simulation solid
    assert len(ex.detail.solids()) == 10 and len(hot.detail.solids()) == 1
    whole = vc.load_step(vc.root() / "e3d_roto_reference_cad.step")
    assert len(whole.solids()) == 11
    v_all, v_cold, v_hot = (sum(s.volume for s in x.solids()) for x in (whole, ex.detail, hot.detail))
    assert 55.0 < v_all - v_cold - v_hot < 65.0                  # the four motor lead wires that were cut off (60.5 mm^3)
    seat, tip = ex.interfaces["hotend_seat"][0], ex.interfaces["nozzle_tip"][0]
    hb = vc.bbox6(hot.detail) + np.array(seat + seat)            # hot side at the seat, unrotated
    assert hb[2] == pytest.approx(tip[2], abs=1e-3) and hb[5] == pytest.approx(seat[2], abs=1e-3)
    assert (hb[0] + hb[3]) / 2 == pytest.approx(tip[0], abs=1e-3) and (hb[1] + hb[4]) / 2 == pytest.approx(tip[1], abs=1e-3)
    # the whole file, moved by the Roto's sidecar transform, is the two detail models side by side
    import json

    sc = json.loads((vc.root() / "EXTRUDER-E3D-ROTO.step.json").read_text())
    wb = vc.bbox6(vc.frame(vc.solids_of(whole, keep=lambda s, b: not 15000 < s.volume < 16000), tuple(sc["rot"]), tuple(sc["pos"])))   # all but the motor
    eb = vc.bbox6(ex.detail)
    assert wb[2] == pytest.approx(tip[2], abs=1e-3) and wb[[0, 1, 4, 5]] == pytest.approx(eb[[0, 1, 4, 5]], abs=1e-3)
    # both mounting holes are where the interfaces say, in each of the two ears
    for x, _, z in ex.interfaces["mount_holes_m3"]:
        for y in (15.75, -15.75):
            hit = vc.find_cylinder(ex.detail, (x, y, z), 3.3, (0, 1, 0), (0.99, 1.04))
            assert hit is not None and hit[0] < 1e-3


def test_wrong_proxy_is_caught():
    st = copy.copy(nema17(48))
    st.shape = Pos(0, 0, -20) * Box(42.3, 42.3, 40) + Pos(0, 0, 12) * Cylinder(2.5, 24)      # 8 mm too short
    st.interfaces = {**st.interfaces, "mount_holes_m3": [(x * 1.1, y, z) for x, y, z in st.interfaces["mount_holes_m3"]]}
    bad, _ = vc.check_stock(st)
    what = " | ".join(b["message"] for b in bad)
    assert "zmin" in what and "mount_holes_m3[0]" in what
    hole = next(b for b in bad if b["what"] == "mount_holes_m3[0]")
    assert hole["cad"] is None or hole["cad"]["offset"] > 1.0             # measured values are reported
    st2 = copy.copy(mgn12_rail(215))
    st2.model = {**st2.model, "features": [vc.hole_feature("hole", (10.0, 0, 1.0), 3.5, (0, 0, 1), tol_dia=0.05)], "no_auto_features": True}
    assert vc.check_stock(st2)[0], "a hole 2.5 mm from where the CAD has one must be reported"


def _endstop_on_plate(relief: bool) -> Design:
    d = Design("es", base="plate")
    sw = endstop_switch()
    plate = Pos(0, 0, -2) * Box(40, 30, 4)
    for x, y, _ in sw.interfaces["mount_holes_m3"]:
        plate -= Pos(x, y, -2) * Cylinder(1.7, 4)
    if relief:
        for x, y, _ in sw.interfaces["pin_holes"]:
            plate -= Pos(x, y, -2) * Cylinder(1.25, 4)
    d.add("plate", plate, material="al6061")
    place(d, "switch", sw, Location((0, 0, 0)))
    return d


def test_envelope_check_catches_what_the_proxy_lacks():
    r = verify_geometry(_endstop_on_plate(relief=False))
    clash = [f for f in r.findings if f.code == "detail_clash"]
    assert clash and clash[0].data["other"] == "plate" and clash[0].data["part"] == "switch"   # the switch terminals
    r = verify_geometry(_endstop_on_plate(relief=True))
    assert not [f for f in r.findings if f.severity == "error"], [f.message for f in r.findings]
    assert r.metrics["vendor_cad"]["checked"]["ENDSTOP-MICRO"]["mismatches"] == 0


def test_endstop_trigger_is_the_lever_operating_position():
    sw = endstop_switch()
    trig, free = sw.interfaces["trigger"][0], sw.interfaces["lever_free"][0]
    top = vc.bbox6(sw.detail)[4]
    assert abs(top - free[1]) < 0.05                         # the lever tip in the CAD is the free position
    assert sw.shape.bounding_box().max.Y < trig[1] < free[1]  # operating position: between the case and the free position
    # OMRON: 6.8 mm from the hole line, 0.55 mm of overtravel guaranteed; the lever meets the case 1.75 mm below nominal
    assert trig[1] == 8.4 and sw.interfaces["overtravel"] == 0.55
    assert abs(trig[1] - sw.shape.bounding_box().max.Y - 1.75) < 1e-6


def test_export_and_placement_use_the_detail_model():
    from mechloop.runner import _labelled

    d = Design("m", base="motor")
    c = place(d, "motor", nema17(48), Location((10, 20, 30), (90, 0, 0)))
    assert c.detail is not None and c.meta["model"]["kind"] == "vendor CAD"        # StepperOnline's own STEP since 2026-11-15
    assert abs(_labelled(c).volume - c.detail.volume) < 1e-6 and abs(c.detail.volume - c.shape.volume) > 100
    a, b = vc.bbox6(c.shape), vc.bbox6(c.detail)
    assert abs(a - b).max() < 0.6                           # moved together


def test_inbox_file_overrides_with_no_code_change(tmp_path, monkeypatch):
    from bd_warehouse.fastener import HexNut
    from build123d import export_step

    (tmp_path / "inbox").mkdir()
    # M6: a size with no supplier file in the repository's own inbox (M2.5 to M4 have McMaster's since 2026-11-18)
    odd = Pos(40, -7, 3) * Rot(90, 0, 0) * HexNut(size="M6-1", fastener_type="iso4032", simple=True)   # some other frame
    export_step(odd, str(tmp_path / "inbox" / "NUT-M6.step"))
    monkeypatch.setenv("MECHLOOP_VENDOR_CAD", str(tmp_path))
    st = hex_nut("M6")
    assert st.model["kind"] == "vendor CAD" and st.model["file"] == "vendor_cad/inbox/NUT-M6.step"
    assert st.model["replaced"] == "generated to standard"
    bad, _ = vc.check_stock(st)                              # aligned automatically into the part's frame
    assert not bad, [b["message"] for b in bad]
    monkeypatch.delenv("MECHLOOP_VENDOR_CAD")
    assert hex_nut("M6").model["kind"] == "generated to standard"
    assert hex_nut("M3").model["kind"] == "vendor CAD"           # the repository's own inbox: McMaster 90591A250
