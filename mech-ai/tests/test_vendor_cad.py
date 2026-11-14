"""Vendor / community CAD behind the catalog parts: every model loads, sits in its part's frame (the proxy-match
check passes), has a SOURCES.md entry; a wrong simulation solid is caught; what the CAD adds is tested against the
neighbours; a hand-downloaded file in vendor_cad/inbox/ replaces a model with no code change."""
import copy
from pathlib import Path

import pytest
from build123d import Box, Cylinder, Location, Pos, Rot

from mechloop import Design
from mechloop.parts import (corner_bracket_2020, control_board, endstop_switch, extrusion_2020, fan, gt2_idler, hex_nut,
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
        if "file" in st.model:
            name = Path(st.model["file"]).name
            used.add(name)
            assert name in rows, f"{name} is not in vendor_cad/SOURCES.md"
            assert (vc.root() / name).exists()
            made = rows[name]["made by"]
            assert ("vendor" in made) == (st.model["kind"] == "vendor CAD"), f"{name}: {made} vs {st.model['kind']}"
            assert rows[name]["licence"] and rows[name]["origin"]
    on_disk = {p.name for p in vc.root().iterdir() if p.suffix.lower() in (".step", ".stp")}
    assert on_disk == used == set(rows), (on_disk ^ used, set(rows) ^ used)
    assert all((vc.root() / n).stat().st_size < 5.2e6 for n in on_disk)


def test_parts_without_cad_say_proxy():
    st = shaft_coupler(5.0, 8.0)
    assert st.detail is None and st.model["kind"] == "proxy"
    assert gt2_idler(20, belt_width=12.0).model["kind"] == "proxy"      # only the 6 mm idler has a model


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
    assert sw.interfaces["overtravel"] > 1.0


def test_export_and_placement_use_the_detail_model():
    from mechloop.runner import _labelled

    d = Design("m", base="motor")
    c = place(d, "motor", nema17(48), Location((10, 20, 30), (90, 0, 0)))
    assert c.detail is not None and c.meta["model"]["kind"] == "community CAD"
    assert abs(_labelled(c).volume - c.detail.volume) < 1e-6 and abs(c.detail.volume - c.shape.volume) > 100
    a, b = vc.bbox6(c.shape), vc.bbox6(c.detail)
    assert abs(a - b).max() < 0.6                           # moved together


def test_inbox_file_overrides_with_no_code_change(tmp_path, monkeypatch):
    from bd_warehouse.fastener import HexNut
    from build123d import export_step

    (tmp_path / "inbox").mkdir()
    odd = Pos(40, -7, 3) * Rot(90, 0, 0) * HexNut(size="M3-0.5", fastener_type="iso4032", simple=True)   # some other frame
    export_step(odd, str(tmp_path / "inbox" / "NUT-M3.step"))
    monkeypatch.setenv("MECHLOOP_VENDOR_CAD", str(tmp_path))
    st = hex_nut("M3")
    assert st.model["kind"] == "vendor CAD" and st.model["file"] == "vendor_cad/inbox/NUT-M3.step"
    assert st.model["replaced"] == "generated to standard"
    bad, _ = vc.check_stock(st)                              # aligned automatically into the part's frame
    assert not bad, [b["message"] for b in bad]
    monkeypatch.delenv("MECHLOOP_VENDOR_CAD")
    assert hex_nut("M3").model["kind"] == "generated to standard"
