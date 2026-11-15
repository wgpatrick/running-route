"""Known-answer tests for four checker defects that the printer_v5 redesign exposed (docs/PRINTER_V5.md,
"Checker behaviour worth a look", items 1, 2, 5 and 6). Each uses a small purpose-built design whose right
answer is known by hand calculation or by construction."""
import math

import pytest
from build123d import Box, Cylinder, Location, Pos, Rot

from mechloop.model import AssemblyCase, Design
from mechloop.parts import add_corner_bracket, add_nut, add_screw, extrusion_2020, place
from mechloop.report import VerifierResult
from mechloop.tolerance.fits import screw_patterns
from mechloop.verifiers.assemblability import verify_assemblability
from mechloop.verifiers.fea import verify_fea
from mechloop.verifiers.interference import verify_interference
from mechloop.verifiers.manufacture import verify_manufacture


# ---------------------------------------------------------------- 1. tolerance: captive-nut slot
def nut_slot_design(slot: float, lug_hole: float = 4.2):
    """A printed body with a 3.5 mm lug (clearance hole `lug_hole`) and, behind it, a captive-nut slot
    `slot` mm wide along the screw and open to the top face. An M3x16 through a 10 mm cover ends inside
    the slot (the nut is 2.4 mm), so the slot's far wall is `slot` - 2.5 mm beyond the screw's tip."""
    d = Design("nutslot", base="body")
    body = Pos(10, 0, 0) * Box(20, 40, 20)
    cover = Pos(-5, 0, 0) * Box(10, 40, 20)
    for y in (-12, 12):
        body -= Pos(1.75, y, 4) * Rot(0, 90, 0) * Cylinder(lug_hole / 2, 3.5)
        body -= Pos(3.5 + slot / 2, y, 5.325) * Box(slot, 5.8, 9.35)          # from 3.35 below the axis up to the top
        cover -= Pos(-5, y, 4) * Rot(0, 90, 0) * Cylinder(1.7, 10)
    d.add("body", body, material="petg")
    d.add("cover", cover, material="al6061")
    for i, y in enumerate((-12, 12)):
        add_screw(d, f"s{i}", "M3", 16, at=(-10, y, 4), direction=(1, 0, 0), clamps=("cover", "body"))
        add_nut(d, f"n{i}", "M3", at=(3.5, y, 4), direction=(1, 0, 0), screw=f"s{i}")
    return d


@pytest.mark.parametrize("slot", [2.7, 3.7, 5.0])
def test_nut_slot_is_not_the_clearance_hole(slot):
    """The screw's clearance hole in the body is the 4.2 mm hole in the lug, whatever the width of the nut
    slot behind it: radial clearance 4.2/2 - 3.0/2 + 0.05 (thread made under size) = 0.65 mm.
    Before the fix the slot's far wall, beyond the screw's tip, was measured instead: -0.85 mm (0% of
    builds, an error) at 2.7 mm and 0.15 mm (98%, a warning) at 3.7 mm."""
    r = VerifierResult("t")
    out = screw_patterns(nut_slot_design(slot), r)
    for nut in ("n0", "n1"):
        assert out[f"body -> {nut}"]["nominal_radial_clearance_mm"] == pytest.approx(0.65, abs=0.01)
        assert out[f"body -> {nut}"]["p_all_start"] == 1.0
    assert not r.findings


def test_tight_lug_hole_beside_a_nut_slot_is_still_caught():
    """The check is not weakened: a 3.1 mm printed hole in the lug has 0.10 mm radial clearance, less than
    the 0.075 mm a printed hole closes up plus its scatter, and is reported."""
    r = VerifierResult("t")
    out = screw_patterns(nut_slot_design(3.7, lug_hole=3.1), r)
    assert out["body -> n0"]["nominal_radial_clearance_mm"] == pytest.approx(0.10, abs=0.01)
    assert out["body -> n0"]["p_all_start"] < 0.9
    assert "screws_may_not_align" in [f.code for f in r.findings]


# ---------------------------------------------------------------- 2. fea: which joints are screwed
E_STEEL, NU_STEEL = 200000.0, 0.29


def post_beside_screws(screw_x: float):
    """A 6 x 6 x 60 steel post clamped (not screwed) to a fixed base and pushed sideways at its top. Beside
    it a block is held to the base by two M3 screws at x = screw_x; the post's foot ends at x = -9."""
    d = Design("post", base="base")
    d.add("base", Pos(0, 0, -5) * Box(60, 30, 10), material="steel")
    d.add("post", Pos(-12, 0, 30) * Box(6, 6, 60), material="steel")
    d.join("post", "base", "clamp")
    block = Pos(screw_x + 4, 0, 3) * Box(16, 20, 6)
    for y in (-5, 5):
        block -= Pos(screw_x, y, 3) * Cylinder(1.7, 6)
    d.add("block", block, material="steel")
    for i, y in enumerate((-5, 5)):
        add_screw(d, f"s{i}", "M3", 10, at=(screw_x, y, 6), threads_into="base")
    d.assemblycases.append(AssemblyCase(
        "push", ["base", "post", "block"], fixed=[("base", lambda f: abs(f.center().Z + 10) < 1e-6)],
        loaded=("post", lambda f: abs(f.center().Z - 60) < 1e-6), force=(10.0, 0, 0), probe=(-12, 0, 60), mesh_size=3.0))
    return d


@pytest.mark.parametrize("screw_x", [-2.0, 1.0])
def test_screwed_joints_follow_the_screws_not_what_is_near_them(screw_x):
    """The block's screws clamp the block to the base and nothing else, so `base / block` is the only
    screwed joint, wherever the screws are; the post's declared clamp stays joined in both solutions, so both
    stiffness bounds are the post's own: cantilever F L^3 / (3 E I) + shear = 0.0333 + 0.0003 mm for 10 N,
    298 N/mm (the base under the foot gives a few per cent more).
    Before the fix, with the screws 7.3 mm from the post's foot (screw_x = -2, inside 1.5 head diameters),
    `base / post` was listed as a screwed joint with 2 screws and released; at 10.2 mm (screw_x = 1) it was not."""
    r = verify_fea(post_beside_screws(screw_x))
    m = r.metrics["push"]
    assert [j["joint"] for j in m["screwed_joints"]] == ["base / block"], m["screwed_joints"]
    assert m["screwed_joints"][0]["screws"] == 2
    L, b, F = 60.0, 6.0, 10.0
    I, G = b ** 4 / 12, E_STEEL / (2 * (1 + NU_STEEL))
    k = F / (F * L ** 3 / (3 * E_STEEL * I) + F * L / (5 / 6 * G * b * b))
    assert k == pytest.approx(297.7, abs=0.5)
    assert 0.88 * k < m["stiffness_n_per_mm"] < 1.02 * k, m
    assert 0.88 * k < m["stiffness_low_n_per_mm"] <= m["stiffness_n_per_mm"] * 1.001, m
    assert m["stiffness_low_n_per_mm"] > 0.98 * m["stiffness_n_per_mm"], m


# ---------------------------------------------------------------- 5. corner bracket on a plate
def bracket_on_plate(hole: bool = True, thick: float = 5.0):
    """A 2020 arm butted against a plate (front face y = 0) and braced underneath by a cast corner bracket.
    The plate has the bracket's M5 clearance hole 11.5 mm below the corner (or not), and a slot beside it
    for the casting's locating nubs."""
    d = Design("brkt", base="plate")
    plate = Pos(0, thick / 2, -10) * Box(60, thick, 80)
    plate -= Pos(0, thick / 2, 0) * Rot(90, 0, 0) * Cylinder(2.75, thick)
    if hole:
        plate -= Pos(0, thick / 2, -21.5) * Rot(90, 0, 0) * Cylinder(2.75, thick)
    d.add("plate", plate, material="al6061", process="sheet")
    place(d, "arm", extrusion_2020(100), Location((0, -50, 0), (0, 0, 90)))
    add_screw(d, "arm_bolt", "M5", 16, at=(0, thick, 0), direction=(0, -1, 0), threads_into="arm", clamps=("plate",))
    add_corner_bracket(d, "brkt", "arm", "plate", (0, 0, -10), (0, -1, 0), (0, 0, -1))
    return d


def test_corner_bracket_on_a_plate_gets_a_real_screw_and_nut():
    """By construction: the leg on the extrusion keeps its BOM screw and T-nut; the leg on the 5 mm plate is
    through-bolted with real parts. Screw length = 3 mm leg + 5 mm plate + 4.7 mm nut = 12.7 -> M5x16.
    With the clearance hole drawn, nothing interferes and the screw can be driven.
    Before the fix there was no screw or nut component, only `m5_tnut` joins and BOM lines."""
    d = bracket_on_plate()
    names = [c.name for c in d.components]
    assert "brkt_screw" in names and "brkt_nut" in names
    assert d.get("brkt_screw").sku == "SHCS-M5x16" and d.get("brkt_nut").sku == "NUT-M5"
    f = next(f for f in d.fasteners if f.name == "brkt_screw")
    assert set(f.clamps) == {"brkt", "plate"}
    assert d.bom_extras["TNUT-2020-M5"]["qty"] == 1 and d.bom_extras["SHCS-M5x8"]["qty"] == 1
    assert d.joins[frozenset(("brkt", "arm"))] == "m5_tnut" and "tnut" not in d.joins[frozenset(("brkt", "plate"))]
    assert not [f for f in verify_interference(d).findings if f.severity == "error"]
    assert not [f for f in verify_assemblability(d).findings if f.severity == "error"]


def test_corner_bracket_screw_is_checked_against_the_plate():
    """Without the clearance hole the screw's shank runs through 5 mm of plate: overlap = pi * 2.5^2 * 5 =
    98.2 mm^3, and the screw cannot be driven. Before the fix this plate passed: nothing was there to check."""
    d = bracket_on_plate(hole=False)
    hits = [f for f in verify_interference(d).findings if f.code == "interference" and "brkt_screw" in f.message]
    assert len(hits) == 1 and "plate" in hits[0].message
    assert hits[0].data["volume_mm3"] == pytest.approx(math.pi * 2.5 ** 2 * 5, abs=0.5)
    assert "tool_access_blocked" in [f.code for f in verify_assemblability(d).findings]


def test_corner_bracket_refuses_what_it_cannot_bolt():
    with pytest.raises(ValueError, match="too thick to through-bolt"):
        bracket_on_plate(thick=40.0)
    d = Design("off", base="plate")
    d.add("plate", Pos(0, 30, 0) * Box(60, 5, 80), material="al6061")          # 27.5 mm away from the bracket's leg
    place(d, "arm", extrusion_2020(100), Location((0, -50, 0), (0, 0, 90)))
    with pytest.raises(ValueError, match="does not lie on 'plate'"):
        add_corner_bracket(d, "brkt", "arm", "plate", (0, 0, -10), (0, -1, 0), (0, 0, -1))


def test_corner_bracket_between_two_extrusions_is_unchanged():
    d = Design("frame", base="a")
    place(d, "a", extrusion_2020(100), Location((0, 0, 0)))
    place(d, "b", extrusion_2020(100), Location((-40, 0, 60), (0, 90, 0)))
    c = add_corner_bracket(d, "brkt", "a", "b", (-30, 0, 10), (1, 0, 0), (0, 0, 1))
    assert [x.name for x in d.components] == ["a", "b", "brkt"]
    assert c.shape.volume == pytest.approx(3400.0, rel=1e-6)                    # the catalog solid, untouched
    assert d.bom_extras["TNUT-2020-M5"]["qty"] == 2 and d.bom_extras["SHCS-M5x8"]["qty"] == 2


# ---------------------------------------------------------------- 6. machining estimate of a stock plate
def machined_plate(t: float = 6.0):
    d = Design("plate", base="p")
    p = Box(200, 100, t)
    for x, y in ((-80, -30), (80, -30), (-80, 30), (80, 30)):
        p -= Pos(x, y, 0) * Cylinder(2.5, t)
    d.add("p", p, material="al6061", process="machined")
    return d


def test_stock_plate_estimate_does_not_machine_the_stock_faces():
    """200 x 100 x 6 mm aluminium plate, four 5 mm holes, cut from 6 mm stock plate (blank 204 x 104).
    Cut surface = edges 2 * (200 + 100) * 6 = 3600 mm^2 + hole walls 4 * pi * 5 * 6 = 377 mm^2 = 39.8 cm^2.
    Time = chips (204 * 104 * 6 - part volume) = 7.77 cm^3 / 12 cm^3/min = 0.65 min
         + finishing 39.8 cm^2 * 0.1 min/cm^2 = 3.98 min + 4 holes * 0.3 min = 1.2 min  -> 5.8 min.
    Cost at 1 off = (5.8 + 12 set-up + 20 programming) / 60 * $75 + 0.344 kg * $8 = 47.3 + 2.75 = $50.
    Before the fix both 200 x 100 faces were charged a finishing pass as well: 45.7 min and $100."""
    row = verify_manufacture(machined_plate()).metrics["parts"]["p"]
    est = row["estimate"]
    assert est["finished_area_cm2"] == pytest.approx(39.8, abs=0.4)
    assert est["stock_faces_not_machined_cm2"] == pytest.approx(2 * (200 * 100 - 4 * math.pi * 2.5 ** 2) / 100, abs=0.5)
    assert est["machining_min"] == pytest.approx(5.8, abs=0.2)
    assert est["cost_usd_each_qty1"] == pytest.approx(50, abs=1)
    assert "stay as supplied" in est["assumes"] and "6 mm" in est["assumes"]


def test_non_stock_plate_estimate_still_machines_both_faces():
    """7 mm is not a stock thickness: it comes out of 8 mm plate, both faces are cut and the whole surface is
    finished. Chips (204 * 104 * 8 - 139.45 cm^3) / 12 = 2.52 min + (2 * 200 * 100 + 2 * 300 * 7 + holes
    4 * pi * 5 * 7 - 8 hole ends) / 100 * 0.1 = 44.5 min + 1.2 min = 48.2 min."""
    r = verify_manufacture(machined_plate(7.0))
    est = r.metrics["parts"]["p"]["estimate"]
    assert "non_stock_thickness" in [f.code for f in r.findings]
    assert est["stock_faces_not_machined_cm2"] == 0.0
    assert est["machining_min"] == pytest.approx(48.2, abs=0.5)
    assert "both plate faces are machined" in est["assumes"]
