"""Practice DG-07: off-the-shelf parts are real parts (docs/DESIGN_GUIDELINES.md, key rule; mechloop/verifiers/purchased.py).

Synthetic designs: a purchased part pinned to a real product with the maker's CAD and sourced ratings passes; a generic
purchased part raises all three errors (warnings in an exploratory design); a part we fabricate with generated geometry
passes; a BOM-only line without a maker is not real; the exporters' per-part verdict matches."""
from build123d import Box, Pos

from mechloop.model import Design
from mechloop.verifiers import purchased as P
from mechloop.verifiers.practice import verify_practice

CODES = ("purchased_part_not_real", "purchased_geometry_not_sourced", "purchased_rating_not_sourced")


def real_part(d, name="motor"):
    return d.add(name, Pos(0, 0, 10) * Box(20, 20, 20), material="steel", cots=True, sku="MOTOR-REAL-1",
                 ratings={"max_temp_c": 80.0, "rated_current_a": 1.5},
                 meta={"catalog": True, "description": "a stepper motor", "vendor_backed": True,
                       "source": {"level": "vendor", "vendor": "StepperOnline", "part": "17HS19-2004S1", "unverified_fields": []},
                       "model": {"kind": "vendor CAD", "file": "vendor_cad/17HS19-2004S1.step", "source": "maker's STEP"},
                       "real_part": {"maker": "StepperOnline", "mpn": "17HS19-2004S1", "sold_by_maker": True,
                                     "sellers": [{"name": "StepperOnline", "part_number": "17HS19-2004S1", "checked": "2026-11-20"}],
                                     "ratings_source": {"max_temp_c": "datasheet p.1", "rated_current_a": "datasheet p.1"}}})


def generic_part(d, name="pulley"):
    return d.add(name, Pos(50, 0, 5) * Box(12, 12, 10), material="al6061", cots=True, sku="GT2-20T-GENERIC",
                 ratings={"max_temp_c": 60.0, "approximate": True, "source": "typical, unverified"},
                 meta={"catalog": True, "description": "GT2 pulley, 20 teeth", "source": {"level": "proxy"},
                       "model": {"kind": "generated to standard", "source": "our generator"}})


def plate(d, name="plate"):
    return d.add(name, Pos(0, 60, 1.5) * Box(60, 40, 3), material="al5052", process="sheet")


def dg07(design):
    r = verify_practice(design)
    return [f for f in r.findings if f.code in CODES], r.metrics["purchased_parts"]


def test_real_purchased_part_passes():
    d = Design("real")
    real_part(d)
    found, m = dg07(d)
    assert found == [] and m["buildable"] and m["counts"]["real_skus"] == 1
    st = P.part_state(d.components[0])
    assert st == {"real_part_state": "real", "placeholder": False, "placeholder_colour": None, "placeholder_why": None}


def test_generic_purchased_part_is_three_errors():
    d = Design("generic")
    generic_part(d)
    found, m = dg07(d)
    by = {f.code: f for f in found}
    assert set(by) == set(CODES) and all(f.severity == "error" for f in found)
    assert set(by["purchased_part_not_real"].data["value"]) == {"maker", "maker part number", "seller"}
    assert by["purchased_geometry_not_sourced"].data["value"] == "stand-in"
    assert by["purchased_rating_not_sourced"].data["value"] == ["max_temp_c"]
    assert "must be fixed before buying" in by["purchased_part_not_real"].message
    assert not m["buildable"] and m["placeholders"][0]["sku"] == "GT2-20T-GENERIC"
    st = P.part_state(d.components[0])
    assert st["placeholder"] and st["real_part_state"] == "placeholder" and st["placeholder_colour"] == P.PLACEHOLDER_COLOUR


def test_exploratory_design_makes_them_warnings():
    d = Design("explore")
    d.exploratory = True
    generic_part(d)
    found, m = dg07(d)
    assert len(found) == 3 and all(f.severity == "warning" for f in found) and m["exploratory"]


def test_fabricated_generated_part_passes():
    d = Design("fab")
    plate(d)
    d.add("clip", Pos(0, -60, 5) * Box(10, 10, 10), material="petg", process="printed")
    found, m = dg07(d)
    assert found == [] and m["counts"]["purchased_skus"] == 0
    assert P.part_state(d.components[0]) == {"real_part_state": None, "placeholder": False}


def test_real_part_with_generated_geometry_is_geometry_pending():
    d = Design("pending")
    c = real_part(d)
    c.meta["model"] = {"kind": "generated to standard", "source": "our generator"}
    found, m = dg07(d)
    assert [f.code for f in found] == ["purchased_geometry_not_sourced"]
    assert P.part_state(c)["real_part_state"] == "geometry pending" and P.part_state(c)["placeholder"]


def test_hand_made_purchased_part_and_bom_only_line():
    d = Design("hand")
    d.add("bracket", Box(20, 20, 20), material="al6061", process="purchased")       # a bought part drawn in the design file
    d.bom_extra("CABLE-TIE-100", 10, 0.05)
    d.bom_extra("WASHER-M3", 4, 0.02, real_part={"maker": "Accu", "mpn": "HPW-M3-A2", "sellers": [{"name": "Accu"}]})
    found, m = dg07(d)
    codes = sorted((f.code, f.data["parts"][0]) for f in found)
    assert ("purchased_part_not_real", "bracket") in codes and ("purchased_geometry_not_sourced", "bracket") in codes
    assert ("purchased_part_not_real", "CABLE-TIE-100") in codes and not any(p == "WASHER-M3" for _, p in codes)


def test_confirmed_catalogue_number_is_maker_number_and_seller():
    d = Design("mcmaster")
    c = d.add("screw", Box(3, 3, 10), material="steel", cots=True, sku="SHCS-M3x10",
              ratings={"mcmaster_pn": "91290A113", "mcmaster_pn_status": "confirmed on McMaster's product page (supplier CAD batch 2026-11-18)"},
              meta={"catalog": True, "source": {"level": "standard", "part": "ISO 4762 M3x10"}, "model": {"kind": "vendor CAD", "file": "x.step"}})
    assert P.assess(c)["state"] == "real"
    c.ratings["mcmaster_pn_status"] = "unconfirmed: listed in the collector's sources, no file inspected"
    assert P.assess(c)["missing"] == ["maker", "maker part number", "seller"]
