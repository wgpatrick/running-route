"""Inspection plans (mechloop.inspect.plan) for the reference parts, and the plans embedded in the measurement form."""
import json
import re
from pathlib import Path

import pytest

from mechloop.inspect import plan as P

ROOT = Path(__file__).resolve().parents[1]
BATCH = ROOT / "reference_parts" / "batch01"


@pytest.fixture(scope="module")
def rp03():
    return P.plan_for_step(BATCH / "RP03_sheet_channel.step", "al5052", shop="sendcutsend", part_id="RP03")


@pytest.fixture(scope="module")
def rp04():
    return P.plan_for_step(BATCH / "RP04_laser_plate.step", "al6061", shop="sendcutsend", part_id="RP04",
                           dxf=str(BATCH / "RP04_laser_plate.dxf"))


def _by_kind(plan, kind):
    return [d for d in plan["dimensions"] if d["kind"] == kind]


def test_tolerances_are_the_shops_published_figures():
    t = P.tolerances("sendcutsend", "al5052", 2.286, "sheet")
    assert t["cut"]["pm"] == pytest.approx(0.127) and t["cut"]["published"]
    assert t["bend_edge"]["pm"] == pytest.approx(0.381) and t["bend_angle_deg"]["pm"] == pytest.approx(1.0)
    assert not t["flat"]["published"] and "class value" in t["flat"]["source"]
    pr = P.tolerances("hubs", "petg", None, "printed")
    assert pr["general"]["pm"] == pytest.approx(0.5)
    assert P._tol_for(pr, "general", 200.0)["pm"] == pytest.approx(1.0)        # 0.5 % of 200 mm


def test_bent_channel_plan(rp03):
    plan, svg = rp03
    assert plan["schema"] == P.SCHEMA and plan["form"] == "bent" and plan["shop"] == "sendcutsend"
    ids = [d["id"] for d in plan["dimensions"]]
    assert ids == list(range(1, len(ids) + 1))
    # the hole near the bend comes first, both diameters, with the finding quoted and distortion expected across the bend
    top = plan["dimensions"][:2]
    assert {d["kind"] for d in top} == {"hole_ovality"}
    across = next(d for d in top if d["key"].endswith("across"))
    assert across["predicted"]["expect_out_of_tolerance"]
    assert any(f["code"] == "hole_too_close_to_bend" for f in across["predicted"]["findings"])
    # bend radius: the shop forms 0.813 mm, not the modelled 2.286 mm
    radii = _by_kind(plan, "bend_radius")
    assert len(radii) == 2 and all(r["nominal"] == pytest.approx(2.286) and r["predicted"]["value"] == pytest.approx(0.813) for r in radii)
    assert any("bend_radius_differs" == f["code"] for f in radii[0]["predicted"]["findings"])
    # flanges: the short 6 mm flange is predicted 0.32 mm short (shop radius + K 0.37) and carries the flange finding
    fl = {round(d["nominal"], 2): d for d in _by_kind(plan, "flange_length")}
    assert fl[6.0]["predicted"]["value"] == pytest.approx(5.684, abs=0.01)
    assert fl[6.0]["predicted"]["findings"]
    assert _by_kind(plan, "web_width")[0]["predicted"]["value"] == pytest.approx(59.37, abs=0.02)
    angles = _by_kind(plan, "bend_angle")
    assert len(angles) == 2 and angles[0]["tol"]["pm"] == 1.0 and angles[0]["method"]["instrument"] == "square_feeler"
    assert _by_kind(plan, "hole_to_bend")
    # the drawing has one balloon per dimension
    assert len(re.findall(r'<g class="b">', svg)) == len(plan["dimensions"])
    assert svg.startswith("<svg") and "currentColor" in svg


def test_flat_plate_plan(rp04):
    plan, svg = rp04
    assert plan["form"] == "flat" and plan["scanner"]["suitable"]
    webs = {round(d["nominal"], 2): d for d in _by_kind(plan, "edge_web")}
    assert 0.8 in webs and webs[0.8]["predicted"]["findings"]
    small = [d for d in _by_kind(plan, "hole_diameter") if d["nominal"] == pytest.approx(1.2)]
    assert small and small[0]["method"]["instrument"] == "pin_gauge"
    assert any(d["nominal"] == pytest.approx(1.0) for d in _by_kind(plan, "slot_width"))
    ov = {d["key"]: d["nominal"] for d in _by_kind(plan, "overall")}
    assert ov == {"overall.X": pytest.approx(120.0), "overall.Y": pytest.approx(80.0)}
    assert all(d["method"]["instrument"] == "scanner" for d in _by_kind(plan, "hole_position"))


def test_committed_plans_and_form():
    idx = json.loads((ROOT / "inspect_form" / "plans" / "index.json").read_text())
    ids = [r["part_id"] for r in idx]
    assert ids == ["RP03", "RP04", "printer_v10_1.x_belt_bracket", "printer_v10_1.y_plate_left", "printer_v10_1.z_deck"]
    deck = json.loads((ROOT / "inspect_form" / "plans" / "printer_v10_1.z_deck.json").read_text())
    pitches = _by_kind(deck, "hole_pitch")
    assert pitches and all(d["depends"] for d in pitches) and pitches[0]["id"] == 1
    html = (ROOT / "inspect_form" / "index.html").read_text()
    a, b = html.index("/*PLANS_BEGIN*/") + 15, html.index("/*PLANS_END*/")
    entries = json.loads(html[a:b])
    assert [e["part_id"] for e in entries] == ids
    assert all(e["svg"].startswith("<svg") and e["dimensions"] for e in entries)
    assert 'claude.use("db")' in html and 'collection("measurements")' in html and 'claude.use("user")' in html
