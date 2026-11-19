"""Suppliers' published design rules (mechloop/data/supplier_rules) and their evaluation (shops/supplier_rules.py,
verifiers/dfm_supplier.py).

Small synthetic parts that pass or fail named rules of SendCutSend, Protolabs, Hubs, Xometry and Fictiv, and a check
that every rule in the data carries its page, the page's words and the retrieval date."""
from urllib.parse import urlparse

import pytest
from build123d import Box, Cylinder, Pos, Rot

from mechloop.model import Design
from mechloop.shops import supplier_rules as SR
from mechloop.verifiers.manufacture import verify_manufacture

HOSTS = {"sendcutsend": {"sendcutsend.com"}, "oshcut": {"www.oshcut.com"}, "protolabs": {"www.protolabs.com"},
         "xometry": {"www.xometry.com"}, "fictiv": {"www.fictiv.com"}, "hubs": {"www.hubs.com"}}


# ------------------------------------------------------------------------------------------- data
def test_every_rule_has_its_source_url_quote_and_date():
    docs = SR.load()
    assert set(HOSTS) <= set(docs)
    ids = set()
    for sup, doc in docs.items():
        assert doc["schema"] == SR.SCHEMA and doc["retrieved"] == "2026-11-19" and doc["rules"]
        for r in doc["rules"]:
            assert r["id"] not in ids, r["id"]
            ids.add(r["id"])
            assert r["supplier"] == sup and r["id"].startswith(sup + ".")
            assert r["source_url"].startswith("https://") and urlparse(r["source_url"]).hostname in HOSTS[sup], r["id"]
            assert isinstance(r["quote"], str) and len(r["quote"].strip()) >= 8, r["id"]
            assert r["retrieved"] == "2026-11-19", r["id"]
            assert r["severity"] in ("error", "warning", "info") and r["comparison"] in (">=", "<=", "==", "within", "in", "info"), r["id"]
            assert r["process"] and r["rule"] and r["material"], r["id"]
            assert r["thickness_mm"] is None or r["thickness_mm"] > 0, r["id"]
            if r["comparison"] != "info" and r.get("evaluate") is not False:
                assert ("value_mm" in r) or ("value" in r) or r.get("formula"), r["id"]
            if r.get("thickness_mm") is not None and r["quote_kind"] == "table_row":
                assert r.get("thickness_as_published"), r["id"]
    for sup, doc in docs.items():
        for r in doc["rules"]:
            for other in r.get("conflicts") or ():
                assert other in ids or other.endswith(".*"), (r["id"], other)


def test_known_figures_and_a_flagged_disagreement():
    # SendCutSend bending calculator, 5052 .125": radius .125", min formed flange .476", die .630"
    rules = {r["id"]: r for r in SR.all_rules()}
    assert rules["sendcutsend.bend.flange_min_formed.al5052.3.175mm"]["value_mm"] == pytest.approx(12.09, abs=0.01)
    assert rules["sendcutsend.bend.radius.al5052.3.175mm"]["value_mm"] == pytest.approx(3.175, abs=0.01)
    assert rules["sendcutsend.bend.die_width.al5052.3.175mm"]["value_mm"] == pytest.approx(0.630 * 25.4 / 2, abs=0.01)
    # .080" 5052 radius: .038" on the calculator, .045" on the processing min/max page: both kept and cross-referenced
    a, b = rules["sendcutsend.bend.radius.al5052.2.032mm"], rules["sendcutsend.bend.radius_minmax.al5052.2.032mm"]
    assert a["value_mm"] != b["value_mm"] and b["id"] in a["conflicts"] and a["id"] in b["conflicts"]
    # never interpolated: no SendCutSend bend rule at a thickness it does not list
    assert not SR.applicable("sendcutsend", "al5052", 2.9, kinds={"flange_min", "bend_radius"})


# --------------------------------------------------------------------------------- synthetic parts
def bx(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)


def bent_L(t, r, h_a, l_b, w, holes_b=()):
    """A 90-degree bend as made: leg A rises to z = h_a (outside mould line at z = 0), leg B reaches x = l_b."""
    c = t + r
    s = bx(0, t, -w / 2, w / 2, c, h_a) + bx(c, l_b, -w / 2, w / 2, 0, t)
    ring = Pos(c, 0, c) * Rot(90, 0, 0) * (Cylinder(c, w) - Cylinder(r, w))
    s = s + (ring & bx(0, c, -w / 2, w / 2, 0, c))
    for x, y, dia in holes_b:
        s -= Pos(x, y, t / 2) * Cylinder(dia / 2, t)
    return s


def plate(t, w=100.0, h=60.0, holes=()):
    s = Box(w, h, t)
    for x, y, dia in holes:
        s -= Pos(x, y, 0) * Cylinder(dia / 2, t)
    return s


def run(shape, material="al5052", shop=None):
    d = Design("t")
    d.add("p", shape, material=material, process="sheet", meta={"dfm": {"shop": shop}} if shop else {})
    r = verify_manufacture(d)
    rules = {}
    for f in r.findings:
        if f.code == "supplier_rule":
            rules[f.data["rule"]] = f
    summary = next(f for f in r.findings if f.code == "supplier_rules_summary")
    return rules, summary, r.metrics["parts"]["p"]["supplier_rules"]


def test_small_hole_is_an_error_at_sendcutsend_and_a_warning_at_protolabs():
    shape = plate(3.175, holes=((-40, 0, 1.0), (20, 0, 6.0)))
    found, summary, row = run(shape)                                     # default shop for sheet: SendCutSend
    f = found["sendcutsend.cut.hole_min_t_ratio"]                         # "At least 50% of material thickness"
    assert f.severity == "error" and f.data["value"] == pytest.approx(1.0) and f.data["limit"] == pytest.approx(1.588, abs=0.01)
    assert f.data["supplier"] == "sendcutsend" and f.data["source"] == "https://sendcutsend.com/guidelines/sheet-cutting/" and f.data["quote"]
    assert row["assigned"] == "sendcutsend" and "fails" in row["verdict"]
    found, _, row = run(shape, shop="protolabs")                         # "Holes and slots should be a minimum of material thickness"
    f = found["protolabs.cut.hole_min"]
    assert f.severity == "warning" and f.data["limit"] == pytest.approx(3.175)
    assert not any(x.severity == "error" for x in found.values()) and row["assigned"] == "protolabs"
    assert "Protolabs" in summary.message and summary.data["by_supplier"]["sendcutsend"]["errors"] >= 1


def test_clean_plate_passes_sendcutsend():
    found, summary, row = run(plate(3.175, holes=((-30, 0, 6.0), (30, 0, 6.0))))
    assert not [f for f in found.values() if f.severity == "error"]
    assert row["verdict"].startswith("passes") and "SendCutSend" in summary.message


def test_flange_between_sendcutsend_and_protolabs_minimums():
    # 5052 .125": SendCutSend min formed flange .476" = 12.09 mm; Protolabs toolkit 2.5 x t + r = 11.11 mm; Hubs 2 x t + r = 9.53 mm
    shape = bent_L(3.175, 3.175, 11.6, 40.0, 50.0)
    found, summary, row = run(shape)
    f = found["sendcutsend.bend.flange_min_formed.al5052.3.175mm"]
    assert f.severity == "error" and f.data["value"] == pytest.approx(11.6, abs=0.05) and f.data["limit"] == pytest.approx(12.09, abs=0.01)
    by = summary.data["by_supplier"]
    assert by["sendcutsend"]["errors"] >= 1 and by["hubs"]["errors"] == 0
    # Protolabs contradicts itself: its guidelines page says "at least 4 times the material thickness" (12.7 mm, fails),
    # its DFM toolkit 2.5 x t + r (11.11 mm, passes). Both are kept and both are judged.
    found, _, _ = run(shape, shop="protolabs")
    assert "protolabs.bend.flange_min_4t" in found and found["protolabs.bend.flange_min_4t"].data["limit"] == pytest.approx(12.7, abs=0.02)
    assert not any(k.startswith("protolabs.bend.flange_min.") for k in found)


def test_hole_near_bend_against_die_width_and_hubs():
    # hole edge 1.95 mm from the tangent line; SendCutSend measures from the bend centre (die .630"/2 = 8.0 mm): warning;
    # Hubs wants 2 x t = 6.35 mm from the start of the bend radius: warning; both name their reference
    shape = bent_L(3.175, 3.175, 20.0, 40.0, 50.0, holes_b=((10.0, 0.0, 3.4),))
    found, summary, _ = run(shape)
    f = found["sendcutsend.bend.die_width.al5052.3.175mm"]
    assert f.severity == "warning" and 5.0 < f.data["value"] < 8.0
    found, _, _ = run(shape, shop="hubs")
    assert found["hubs.bend.hole_to_bend"].data["value"] == pytest.approx(1.95, abs=0.05)


def test_bending_6061_and_thickness_without_rows():
    # SendCutSend lists no bending of 6061 and no row at 2.9 mm: no bend rule is published, so it is not judged ("no published rule")
    feat = {"process": "sheet", "form": "bent", "material": "al5052", "thickness_mm": 2.9,
            "bends": [{"radius": 3.0, "angle": 90.0, "length": 50.0, "flanges": [{"length": 20.0, "profile": [20.0] * 5}]}], "holes": [], "hole_bend": []}
    res = SR.evaluate(feat, "sendcutsend")
    assert not [x for x in res if x["rule"]["rule"] in ("flange_min", "bend_radius")]
    assert {"flange_min", "bend_radius"} <= set(SR.missing_kinds(feat, "sendcutsend", res))


# ------------------------------------------------------------------------------ evaluate() on dicts
def bent_feat(**kw):
    f = {"process": "sheet", "form": "bent", "material": "al5052", "thickness_mm": 3.175, "holes": [], "hole_bend": [], "pems": [], "tapped": [],
         "bends": [{"radius": 3.175, "angle": 90.0, "length": 50.0, "flanges": [{"length": 20.0, "profile": [20.0] * 10}]}]}
    f.update(kw)
    return f


def fails(feat, sup):
    return {x["rule"]["id"]: x for x in SR.evaluate(feat, sup) if x["status"] == "fail"}


def test_flange_support_fraction():
    # 40 % of the bend meets SendCutSend's 12.09 mm: "Approximately 50% of a bend's length must meet the minimum"
    prof = [20.0] * 4 + [5.0] * 6
    f = fails(bent_feat(bends=[{"radius": 3.175, "angle": 90.0, "length": 50.0, "flanges": [{"length": 20.0, "profile": prof}]}]), "sendcutsend")
    assert f["sendcutsend.bend.support_fraction"]["measured"] == pytest.approx(0.4)
    prof = [20.0] * 7 + [5.0] * 3                 # 70 %: passes both the 50 % rule and the ~50-60 % warning
    f = fails(bent_feat(bends=[{"radius": 3.175, "angle": 90.0, "length": 50.0, "flanges": [{"length": 20.0, "profile": prof}]}]), "sendcutsend")
    assert not [k for k in f if "support" in k]


def test_bend_radius_and_angle():
    # SendCutSend offers one radius per stock (.125" here; warning when modelled otherwise) and bends to 130 degrees (error)
    f = fails(bent_feat(bends=[{"radius": 1.0, "angle": 135.0, "length": 50.0, "flanges": []}]), "sendcutsend")
    assert f["sendcutsend.bend.radius.al5052.3.175mm"]["rule"]["severity"] == "warning"
    assert f["sendcutsend.bend.angle_max"]["rule"]["severity"] == "error"
    # Xometry: minimum bend 1 x MT; Fictiv 5052: 0.5t-1.0t (lower end)
    assert "xometry.bend.radius_min" in fails(bent_feat(bends=[{"radius": 2.0, "angle": 90.0, "length": 50.0, "flanges": []}]), "xometry")
    assert "fictiv.bend.radius_min.al5052" not in fails(bent_feat(bends=[{"radius": 2.0, "angle": 90.0, "length": 50.0, "flanges": []}]), "fictiv")


def test_pem_hardware_edge_distance_and_catalogue_substitution():
    # SendCutSend catalogue S-M3-0: hole C/L to edge or bend .250" (6.35 mm), C/L to C/L .336"; S-M3-1 is not listed
    pem = {"name": "n", "sku": "S-M3-1", "thread": "M3", "at": [0, 0, 0], "hole_d": 4.27, "center_edge": 5.0, "center_bend": None, "pitch": None}
    feat = {"process": "sheet", "form": "flat", "material": "al5052", "thickness_mm": 3.175, "holes": [], "pems": [pem], "tapped": [], "bends": []}
    sku, note = SR.pem_sku_for(pem, "sendcutsend", 3.175, "al5052")
    assert sku == "S-M3-0" and "not in" in note
    f = fails(feat, "sendcutsend")
    assert f["sendcutsend.pem.edge.S-M3-0"]["limit"] == pytest.approx(6.35)
    pem["center_edge"] = 7.0
    assert "sendcutsend.pem.edge.S-M3-0" not in fails(feat, "sendcutsend")
    # Fictiv: "min edge 2.5x hole diameter" (warning)
    assert fails(feat, "fictiv")["fictiv.pem.edge"]["rule"]["severity"] == "warning"


def test_cnc_rules_xometry_and_protolabs():
    feat = {"process": "machined", "form": "block", "material": "al6061", "thickness_mm": None, "extents_mm": [20.0, 40.0, 600.0],
            "min_wall_mm": 0.45, "smallest_hole_mm": 0.4, "tapped": [{"d": 16.0, "at": [0, 0, 0]}]}
    xo = fails(feat, "xometry")
    assert xo["xometry.cnc.min_feature"]["rule"]["severity"] == "error" and xo["xometry.cnc.min_feature"]["measured"] == pytest.approx(0.4)
    assert "xometry.cnc.part_max_milled" not in xo                          # 600 mm is inside 2032 x 1219 x 610
    pl = fails(feat, "protolabs")
    assert "protolabs.cnc.part_max_al_3axis" in pl                          # longer than 559 mm
    assert "protolabs.cnc.threads" in pl                                    # M16 outside M2 to M12
    assert pl["protolabs.cnc.feature_min"]["rule"]["severity"] == "warning"  # 0.45 mm wall under the recommended 0.51 mm


def test_shop_assignment_defaults():
    d = Design("t")
    a = d.add("a", Box(10, 10, 2), material="al5052", process="sheet")
    b = d.add("b", Box(10, 10, 10), material="al6061", process="machined")
    c = d.add("c", Box(10, 10, 2), material="al5052", process="sheet", meta={"dfm": {"shop": "oshcut"}})
    assert SR.shop_for(a, d, "sheet") == "sendcutsend" and SR.shop_for(b, d, "machined") == "xometry" and SR.shop_for(c, d, "sheet") == "oshcut"
    d.manufacturing = {"shop": "generic"}                  # no rule file: the process default stands
    assert SR.shop_for(a, d, "sheet") == "sendcutsend"
