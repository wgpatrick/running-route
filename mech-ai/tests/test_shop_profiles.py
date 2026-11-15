"""Shop profiles (mechloop/shops/*.json): known answers against the suppliers' own published limits.

Each test names the figure it leans on; the figures and the pages they came from are in the profiles and
in docs/FABRICATORS.md. Small parts, a few seconds for the whole file."""
import pytest
from build123d import Box, Cylinder, Pos

from mechloop import shops
from mechloop.model import Design
from mechloop.parts import add_screw
from mechloop.tolerance.process import PROCESS, tol
from mechloop.verifiers.dfm_rules import SHOPS, Limits
from mechloop.verifiers.manufacture import verify_manufacture

SCS = {"shop": "sendcutsend"}


def check(shape, material="al6061", man=None, screws=(), meta=None, process="sheet"):
    d = Design("t")
    if man:
        d.manufacturing = man
    d.add("p", shape, material=material, process=process, meta=dict(meta or {}))
    for i, (size, length, at, direction) in enumerate(screws):
        add_screw(d, f"s{i}", size, length, at=at, direction=direction, threads_into="p")
    r = verify_manufacture(d)
    # the sharp-edge, corner and lead-in rules have their own tests (tests/test_known_answers_v8.py); the boxes used here are
    # drawn dead sharp on purpose and would draw them every time
    r.findings[:] = [f for f in r.findings if f.code not in ("sharp_profile_corners", "edges_not_broken", "no_lead_in", "printed_edges")]
    return {f.code: f for f in r.findings}, r.metrics["parts"]["p"]


def sev(found, code):
    return found[code].severity if code in found else None


def plate(t, w=100.0, h=60.0, holes=()):
    s = Box(w, h, t)
    for x, y, dia in holes:
        s -= Pos(x, y, 0) * Cylinder(dia / 2, t)
    return s


# ------------------------------------------------------------------------------------------ the data
def test_every_number_has_a_page_a_date_and_the_pages_own_words():
    profs = shops.profiles()
    assert {"sendcutsend", "xometry"} <= set(profs)
    for name, prof in profs.items():
        assert prof["accessed"] == "2026-11-15" and prof["not_published"]
        for rid, rule in prof["rules"].items():
            src = prof["sources"][rule["source"]]
            assert rule["verbatim"], (name, rid)
            assert src["accessed"] and (src["url"].startswith("https://") or rule["source"] in ("recalled",)), (name, rid)
        for rid, lim in prof["limits"].items():
            assert lim["rule"] in prof["rules"], (name, rid)
        for mat, info in prof["materials"].items():
            for row in info.get("thicknesses", ()):
                for key, cell in row.items():
                    if isinstance(cell, dict):
                        assert cell["verbatim"] and cell["source"] in prof["sources"], (name, mat, row["t_mm"], key)
    # a recalled figure says so
    assert shops.profile("xometry")["plate_stock"]["al_mic6"]["source"] == "recalled"


def test_sendcutsend_stock_is_the_inch_gauge_list():
    al = SHOPS["sendcutsend"]["sheet_stock"]["al6061"]
    assert al == (1.016, 1.6, 2.032, 2.54, 3.175, 4.75, 6.35, 7.95, 9.525, 12.7, 15.875, 19.05)
    steel = SHOPS["sendcutsend"]["sheet_stock"]["steel"]
    assert 3.023 in steel and 3.429 in steel and 1.88 in steel and 2.0 not in steel and 5.0 not in steel
    assert SHOPS["sendcutsend"]["sheet_stock"]["al_mic6"] == (6.35, 9.525, 12.7)          # cast plate, laser cut
    assert [r["t_mm"] for r in shops.profile("sendcutsend")["materials"]["delrin"]["thicknesses"]] == [3.175, 4.75, 6.858]


# -------------------------------------------------------------------------------- stock and material
@pytest.mark.parametrize("material,t,ok", [("al6061", 3.0, False), ("al6061", 3.175, True), ("al6061", 5.0, False), ("al6061", 4.75, True),
                                           ("steel", 2.0, False), ("steel", 1.88, True), ("steel", 3.0, True), ("steel", 1.5, True)])
def test_a_thickness_the_shop_does_not_stock_is_an_error(material, t, ok):
    found, row = check(plate(t), material=material, man=SCS, meta={"finish": "oil"})
    assert (sev(found, "non_stock_thickness") is None) == ok
    if not ok:
        assert sev(found, "non_stock_thickness") == "error"
    assert row["shop_services"]["difference_mm"] == pytest.approx(t - row["stock_mm"], abs=1e-3)


def test_a_material_the_shop_does_not_cut_is_an_error():
    found, _ = check(plate(3.0), material="al_atp5", man=SCS)
    assert sev(found, "shop_material_not_offered") == "error"
    assert sev(check(plate(6.35), material="al_mic6", man=SCS)[0], "shop_material_not_offered") is None


# ------------------------------------------------------------------------------------ holes and webs
def test_a_hole_under_half_the_thickness_fails_and_at_the_minimum_passes():
    # SendCutSend: laser holes "At least 50% of material thickness": 2.375 mm in .187 in (4.75 mm) stock
    small, _ = check(plate(4.75, holes=[(0, 0, 2.3)]), man=SCS)
    assert sev(small, "hole_too_small_to_cut") == "error"
    assert small["hole_too_small_to_cut"].data["source"].startswith("https://sendcutsend.com/guidelines/sheet-cutting/")
    at_min, _ = check(plate(4.75, holes=[(0, 0, 2.38)]), man=SCS)
    assert sev(at_min, "hole_too_small_to_cut") is None
    assert sev(at_min, "hole_smaller_than_thickness") == "warning"       # general practice still says it will taper


def test_web_between_cut_features_under_half_the_thickness_fails():
    # "hole diameters and bridging widths be no less than 50% of the material thickness": 1.59 mm in 3.175 mm stock
    thin, row = check(plate(3.175, holes=[(-3.6, 0, 6.0), (3.6, 0, 6.0)]), man=SCS)          # 1.2 mm between the holes
    assert sev(thin, "shop_web_below_minimum") == "error"
    f = thin["shop_web_below_minimum"].data
    assert f["value"] == pytest.approx(1.2, abs=0.02) and f["limit_mm"] == pytest.approx(1.588, abs=0.01)
    assert f["verbatim"].startswith("We recommend that hole diameters and bridging widths") and "sendcutsend.com/blog" in f["source"]
    ok, row = check(plate(3.175, holes=[(-3.85, 0, 6.0), (3.85, 0, 6.0)]), man=SCS)          # 1.7 mm
    assert sev(ok, "shop_web_below_minimum") is None and sev(ok, "holes_too_close") == "warning"
    assert row["shop_services"]["least_web_mm"] == pytest.approx(1.7, abs=0.02)
    edge, _ = check(plate(3.175, w=40, h=20, holes=[(0, 6.0, 6.0)]), man=SCS)                 # 1.0 mm to the edge
    assert sev(edge, "shop_web_below_minimum") == "error"
    assert "shop_web_below_minimum" not in check(plate(3.0, holes=[(-3.6, 0, 6.0), (3.6, 0, 6.0)]))[0]   # generic shop: its own rules only


# ------------------------------------------------------------------------------------------- threads
def test_a_thread_the_shop_does_not_tap_in_that_thickness_is_an_error():
    def tapped(t, size, material="steel"):
        return check(plate(t), material=material, man=SCS, meta={"finish": "oil"}, screws=[(size, 8, (0, 0, t / 2), (0, 0, -1))])[0]

    # mild steel table: .048 in no tapping; .059 in M2 to M3; .074 in M2 to M6; .119 in M2 to M8
    assert sev(tapped(1.219, "M3"), "shop_tap_not_offered") == "error"
    assert sev(tapped(1.499, "M3"), "shop_tap_not_offered") is None
    assert sev(tapped(1.499, "M4"), "shop_tap_not_offered") == "error"
    assert sev(tapped(1.88, "M5"), "shop_tap_not_offered") is None
    assert sev(tapped(3.023, "M5"), "shop_tap_not_offered") is None
    # 6061: .187 in starts at M3
    assert sev(tapped(4.75, "M3", "al6061"), "shop_tap_not_offered") is None
    f = tapped(1.499, "M4")["shop_tap_not_offered"].data
    assert "M3 x 0.5" in f["verbatim"] and f["source"].startswith("https://sendcutsend.com/materials/processing-min-max/")
    # too small a part for the tapping service (1 x 1.5 in)
    tiny = check(plate(3.023, w=30, h=20), material="steel", man=SCS, meta={"finish": "oil"}, screws=[("M3", 8, (0, 0, 1.5), (0, 0, -1))])[0]
    assert sev(tiny, "shop_tap_not_offered") == "error"


# ---------------------------------------------------------------------------- services and finishes
def test_which_services_fit_a_part():
    prof = shops.profile("sendcutsend")
    s = shops.services_for(prof, "steel", 3.0, [170.0, 100.0])
    assert s["stock_mm"] == 3.023 and s["tumble"]["offered"] and s["deburr"]["offered"] and s["powder_coat"]["offered"]
    assert not s["plating"]["offered"]                                    # zinc from .187 in only
    assert s["tap"]["metric"] == [2.0, 8.0]
    assert not shops.services_for(prof, "steel", 3.0, [180.0, 100.0])["tumble"]["offered"]          # 4 x 7 in
    assert not shops.services_for(prof, "steel", 3.0, [70.0, 40.0])["deburr"]["offered"]            # 1 x 3 in minimum
    assert shops.services_for(prof, "steel", 3.0, [70.0, 40.0])["tumble"]["offered"]                # 0.5 x 1.5 in minimum
    assert not shops.services_for(prof, "steel", 2.0, [70.0, 40.0])["tumble"]["offered"]            # from .119 in
    assert shops.services_for(prof, "steel", 4.75, [100.0, 80.0])["plating"]["offered"]
    assert not shops.services_for(prof, "al6061", 3.0, [100.0, 80.0])["bend"]["offered"]            # 6061 is not bent
    assert shops.services_for(prof, "al5052", 3.175, [100.0, 80.0])["bend"]["offered"]
    assert shops.services_for(prof, "al6061", 3.175, [100.0, 80.0])["countersink"]["minor_min_mm"] == pytest.approx(2.51, abs=0.01)
    assert not shops.services_for(prof, "al6061", 2.54, [100.0, 80.0])["countersink"]["offered"]


def test_carbon_steel_needs_a_declared_finish_the_shop_can_apply():
    bare, _ = check(plate(3.0), material="steel", man=SCS)
    assert sev(bare, "bare_steel_no_finish") == "warning" and "powder coat" in bare["bare_steel_no_finish"].message
    assert "bare_steel_no_finish" not in check(plate(3.0), material="steel", man=SCS, meta={"finish": "powder_coat"})[0]
    zinc, _ = check(plate(3.0), material="steel", man=SCS, meta={"finish": "zinc"})
    assert sev(zinc, "shop_finish_not_offered") == "error"                # plating is listed from 4.75 mm
    assert not check(plate(4.75), material="steel", man=SCS, meta={"finish": "zinc"})[0]
    small, _ = check(plate(3.0, w=40, h=30), material="steel", man=SCS, meta={"finish": "powder_coat"})
    assert sev(small, "shop_finish_not_offered") == "error"               # under 1 x 3 in
    assert "bare_steel_no_finish" not in check(plate(3.175), man=SCS)[0]                              # aluminium
    assert "bare_steel_no_finish" not in check(plate(3.0), material="steel")[0]                       # generic shop: not judged


# ------------------------------------------------------------------------------------------- xometry
def test_xometry_limits_come_with_their_page():
    d = Design("t")
    c = d.add("p", Box(60, 40, 10), material="al6061", process="machined", meta={"dfm": {"shop": "xometry"}})
    c = c if c is not None else d.components[-1]
    lim = Limits(d, c)
    assert lim("cnc.wall_recommended_metal_mm") == pytest.approx(0.794)
    assert lim.source("cnc.wall_recommended_metal_mm").startswith("https://www.xometry.com/resources/machining/cnc-machining-thin-walls/")
    assert lim("cnc.hole_depth_ratio") == 10.0 and lim.source("cnc.hole_depth_ratio").startswith("https://www.hubs.com")   # not published: general rule
    assert Limits(d)("cnc.wall_recommended_metal_mm") == 0.8                                           # the design itself is generic


def test_xometry_cast_plate_thickness_and_notes():
    xo = {"shop": "xometry"}
    found, row = check(Box(200, 200, 8), material="al_mic6", man=xo, process="machined")
    assert sev(found, "non_stock_thickness") == "warning"                 # 8 mm is not a MIC-6 thickness (recalled list)
    found, row = check(Box(200, 200, 9.525), material="al_mic6", man=xo, process="machined")
    assert "non_stock_thickness" not in found
    assert row["shop_notes"]["flatness_without_drawing_mm"] == 0.127 and row["shop_notes"]["general_tolerance_mm"] == 0.127
    assert row["shop_notes"]["edge_break"].startswith("Sharp edges will be broken and deburred by default")
    found, row = check(Box(400, 200, 12), material="al6061", man=xo, process="machined")
    assert row["shop_notes"]["flatness_without_drawing_mm"] == 0.254      # 12 to 24 in
    assert sev(check(Box(60, 40, 10), material="al_atp5", man=xo, process="machined")[0], "shop_material_not_listed") == "warning"
    threads, row = check(Box(60, 40, 10), man=xo, process="machined", screws=[("M3", 8, (0, 0, 5), (0, 0, -1))])
    assert sev(threads, "shop_thread_callout") == "warning" and row["shop_notes"]["threads"] == ["M3"]
    # a sheet part sent to a shop profiled for machining only is said, not silently passed
    assert "shop_process_not_profiled" in check(plate(3.0), man=xo)[0]


# ----------------------------------------------------------------------------------------- tolerance
def test_the_tolerance_table_follows_the_parts_shop():
    d = Design("t")
    d.add("small", Box(100, 60, 3.175), material="al6061", process="sheet")
    d.add("long", Box(340, 60, 3.175), material="al6061", process="sheet")
    d.add("block", Box(100, 60, 10), material="al6061", process="machined")
    d.add("duct", Box(20, 20, 20), material="petg", process="printed")
    by = {c.name: c for c in d.components}
    assert tol(by["small"]) is PROCESS["sheet"]                           # no shop named: the class values, untouched
    done = shops.assign(d, sheet="sendcutsend", machined="xometry")
    assert done == {"small": "sendcutsend", "long": "sendcutsend", "block": "xometry"}
    # SendCutSend: +/-0.005 in under 12 in, +/-0.010 in over; a published +/- is two standard deviations
    assert tol(by["small"])["pos"] == pytest.approx(0.0635) and tol(by["long"])["pos"] == pytest.approx(0.127)
    assert tol(by["small"])["hole_sd"] == pytest.approx(0.0635)
    assert tol(by["small"])["pattern"] == PROCESS["sheet"]["pattern"] and tol(by["small"])["flat"] == PROCESS["sheet"]["flat"]   # not published
    # Xometry without a drawing: +/-0.005 in size and location, .005 in form up to 12 in
    assert tol(by["block"])["pos"] == pytest.approx(0.0635) and tol(by["block"])["flat"] == pytest.approx(0.0635)
    assert tol(by["duct"]) is PROCESS["printed"]
    assert PROCESS["sheet"]["pos"] == 0.08 and PROCESS["machined"]["flat"] == 0.02       # the class table itself is not changed
    # a face toleranced on the drawing: the part states it
    by["block"].meta["dfm"]["tolerance"] = {"flat": 0.02}
    assert tol(by["block"])["flat"] == 0.02 and tol(by["block"])["pos"] == pytest.approx(0.0635)
    by["block"].meta["dfm"]["tolerance"] = {"flatness": 0.02}
    with pytest.raises(ValueError):
        tol(by["block"])
    with pytest.raises(ValueError):
        shops.assign(d, sheet="acme")


def test_generic_design_is_untouched_by_the_profiles():
    found, row = check(plate(3.0, holes=[(0, 0, 4.0)]))
    assert not found and "shop_services" not in row and row["shop"] == "generic"
