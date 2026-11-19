"""Build mechloop/data/supplier_rules/*.json from the pages saved in dfm_sources/raw (untrusted data; parsed only).

Every rule carries supplier, process, material, thickness (mm and as published), value, comparison, severity,
source_url, a quote and the retrieval date. Prose quotes are checked to occur verbatim (whitespace-normalised) in
the saved page text; table quotes are checked cell by cell against the parsed table.

Run: python -I build_rules.py <scratch> <out_dir>
"""
import json
import re
import sys
from pathlib import Path

SCR = Path(sys.argv[1])
OUT = Path(sys.argv[2])
RAW = SCR / "dfm_sources" / "raw"
PARSED = SCR / "dfm_parsed"
DATE = "2026-11-19"
IN = 25.4

URL = {
    "scs_bendcalc": "https://sendcutsend.com/bending-calculator/",
    "scs_minmax": "https://sendcutsend.com/materials/processing-min-max/",
    "scs_sizes": "https://sendcutsend.com/materials/min-max/",
    "scs_bending": "https://sendcutsend.com/services/cnc-bending/",
    "scs_deform": "https://sendcutsend.com/guidelines/bend-deformation/",
    "scs_relief": "https://sendcutsend.com/blog/guide-to-designing-bend-reliefs/",
    "scs_cut_guide": "https://sendcutsend.com/guidelines/sheet-cutting/",
    "scs_tol": "https://sendcutsend.com/blog/basic-tolerances-and-cut-feature-relationships/",
    "scs_holedist": "https://sendcutsend.com/blog/how-to-apply-hole-distance-specifications/",
    "scs_hwcat": "https://sendcutsend.com/guidelines/hardware/catalog/",
    "scs_tap": "https://sendcutsend.com/services/tapping/",
    "scs_csk": "https://sendcutsend.com/services/countersinking/",
    "scs_5052": "https://sendcutsend.com/materials/5052-aluminum/",
    "scs_6061": "https://sendcutsend.com/materials/6061-aluminum/",
    "osh_capabilities": "https://www.oshcut.com/capabilities",
    "osh_services_bending": "https://www.oshcut.com/services/bending",
    "osh_services_laser_metal_cutting": "https://www.oshcut.com/services/laser-metal-cutting",
    "osh_services_countersinking": "https://www.oshcut.com/services/countersinking",
    "osh_services_metal_tapping": "https://www.oshcut.com/services/metal-tapping",
    "osh_dg_metal_bending_design_rules": "https://www.oshcut.com/design-guide/metal-bending-design-rules",
    "osh_minimum_maximum_material_sizes": "https://www.oshcut.com/minimum-maximum-material-sizes",
    "pl_sm": "https://www.protolabs.com/services/sheet-metal-fabrication/design-guidelines/",
    "pl_toolkit": "https://www.protolabs.com/resources/design-for-sheet-metal-fabrication-toolkit/",
    "pl_sm_laser": "https://www.protolabs.com/services/sheet-metal-fabrication/laser-cutting/",
    "pl_sm_forming": "https://www.protolabs.com/services/sheet-metal-fabrication/forming/",
    "pl_cnc_mill_dg": "https://www.protolabs.com/services/cnc-machining/cnc-milling/design-guidelines/",
    "xo_smfab": "https://www.xometry.com/capabilities/sheet-metal-fabrication/",
    "xo_laser": "https://www.xometry.com/capabilities/sheet-cutting/laser-cutting/",
    "xo_sheetcut": "https://www.xometry.com/capabilities/sheet-cutting/",
    "xo_std": "https://www.xometry.com/manufacturing-standards/",
    "xo_cnc": "https://www.xometry.com/capabilities/cnc-machining-service/",
    "fictiv_spec_sm": "https://www.fictiv.com/specifications/sheet-metal",
    "fictiv_spec_cnc": "https://www.fictiv.com/specifications/cnc-machining",
    "hubs_sm_basic": "https://www.hubs.com/guides/sheet-metal-fabrication/",
    "scs_specs": "https://app.sendcutsend.com/sendcutsend-specs.json",
}
SPECS = json.loads((SCR / "dfm_sources" / "app" / "scs_sendcutsend-specs.json").read_text(encoding="utf-8"))

_TEXT = {}


def norm(s):
    return " ".join(str(s).replace(" ", " ").split())


def text(page):
    if page not in _TEXT:
        _TEXT[page] = norm((RAW / f"{page}.txt").read_text(encoding="utf-8"))
    return _TEXT[page]


def tables(page):
    return json.loads((PARSED / f"{page}_tables.json").read_text(encoding="utf-8"))


def inch(s):
    """'.476″' / '0.250"' / '.630' / '1.575″' -> mm (None for N/A)."""
    s = norm(s).replace("″", "").replace('"', "").replace("”", "").strip()
    if not s or s.upper() == "N/A":
        return None
    m = re.match(r"^(\d*\.?\d+)$", s)
    if not m:
        raise ValueError(f"not an inch figure: {s!r}")
    return round(float(m.group(1)) * IN, 3)


def try_inch(s):
    try:
        return inch(s)
    except ValueError:
        SKIPPED.append(s)
        return None


SKIPPED = []


def inch_pair(s):
    """'.375″ x 1.5″' or '56″ x 44″ —— 1422.4 x 1117.6mm' -> (short, long) mm."""
    s = norm(s).split("—")[0]
    a, b = [inch(x) for x in s.split("x")[:2]]
    return [min(a, b), max(a, b)]


RULES = {}
CHECKED_QUOTES = 0


def add(supplier, rid, *, process, rule, page, quote, quote_kind="text", material="*", material_as_published=None,
        thickness_mm=None, thickness_as_published=None, thickness_range_mm=None, value_mm=None, value=None, unit="mm",
        value_as_published=None, formula=None, comparison=">=", severity="error", phrasing="requirement", measured=None,
        note=None, evaluate=True, cells=None, table=None, **extra):
    global CHECKED_QUOTES
    if quote_kind == "json_field":
        sku, section, field, val = cells
        m = next(x for x in SPECS["materials"] if x["sku"] == sku)
        assert str(m[section][field]) == val, (rid, sku, section, field, val)
    elif quote_kind == "text":
        assert norm(quote) in text(page), (supplier, rid, page, quote[:80])
    else:
        rows = [[norm(c) for c in r] for t in tables(table or page) for r in t]
        for c in cells:
            assert any(norm(c) in r for r in rows), (supplier, rid, c)
    CHECKED_QUOTES += 1
    r = {"id": f"{supplier}.{rid}", "supplier": supplier, "process": process, "rule": rule, "material": material}
    if material_as_published:
        r["material_as_published"] = material_as_published
    r["thickness_mm"] = thickness_mm
    if thickness_as_published:
        r["thickness_as_published"] = thickness_as_published
    if thickness_range_mm:
        r["thickness_range_mm"] = thickness_range_mm
    if value_mm is not None:
        r["value_mm"] = value_mm
    if value is not None:
        r["value"] = value
        r["unit"] = unit
    if formula:
        r["formula"] = formula
    if value_as_published is not None:
        r["value_as_published"] = value_as_published
    r.update({"comparison": comparison, "severity": severity, "phrasing": phrasing})
    if measured:
        r["measured"] = measured
    if not evaluate:
        r["evaluate"] = False
    r.update(extra)
    if note:
        r["note"] = note
    r.update({"source_url": URL[page], "quote": quote, "quote_kind": quote_kind, "retrieved": DATE})
    assert r["id"] not in RULES, r["id"]
    RULES[r["id"]] = r
    return r


def tkey(mm):
    return f"{mm:.3f}mm"


def walk(table):
    """Rows of a SendCutSend material table with the material carried down: yields (material, cells after it)."""
    h = len(table[0])
    cur = None
    for row in table[1:]:
        if len(row) == h:
            cur, cells = row[0], row[1:]
        elif len(row) == h - 1:
            cells = row
        else:
            continue
        yield cur, cells


SCS_MAT = {"5052 Aluminum": "al5052", "6061 Aluminum": "al6061", "Mild Steel": "steel", "304 Stainless Steel": "stainless304",
           "MIC-6 Aluminum": "al_mic6", "MIC-6 Cast Aluminum": "al_mic6"}

# =============================================================================== SendCutSend
SCS = "sendcutsend"
# ---- general cutting rules (all materials, laser)
add(SCS, "cut.hole_min_t_ratio", process="laser_cut", rule="hole_min", page="scs_cut_guide",
    quote="Minimum hole and cutout size The pierce or tool entry needs a certain amount of room. Holes smaller than the minimum will distort, char, or fail to cut. | Method | Minimum hole/cutout | Laser Cutting | At least 50% of material thickness",
    formula={"t": 0.5}, value_as_published="At least 50% of material thickness", severity="error", measured="smallest hole or cut-out (width of the largest inscribed circle for a non-round cut-out)",
    conflicts=["sendcutsend.cut.hole_min_al5052_page", "sendcutsend.cut.hole_min_al6061_page"], yield_to_specific=True,
    note="The guideline page adds: 'the exact minimum changes with the material and thickness. The current values for every stock we carry live on each material's page' (those per-thickness values are loaded from app.sendcutsend.com and were not read).")
add(SCS, "cut.hole_min_al5052_page", process="laser_cut", rule="hole_min", page="scs_5052", material="al5052", material_as_published="5052 H32 Aluminum",
    quote="Minimum hole size: Equal to material thickness (e.g., .125″ hole in .125″ sheet).", formula={"t": 1.0},
    value_as_published="Equal to material thickness", severity="warning", phrasing="statement",
    conflicts=["sendcutsend.cut.hole_min_t_ratio"],
    note="Contradicts the sheet-cutting guideline (50 % of thickness). Kept as a warning: the guideline page and pre-flight checklist accept 50 %.")
add(SCS, "cut.slot_min_al5052_page", process="laser_cut", rule="slot_min", page="scs_5052", material="al5052", material_as_published="5052 H32 Aluminum",
    quote="Minimum slot width: Material thickness or larger for clean results.", formula={"t": 1.0}, severity="warning", phrasing="recommendation",
    measured="narrowest non-round cut-out")
add(SCS, "cut.hole_edge_al5052_page", process="laser_cut", rule="hole_edge_web", page="scs_5052", material="al5052", material_as_published="5052 H32 Aluminum",
    quote="Spacing from edges: Leave at least 2x thickness between a hole and an edge.", formula={"t": 2.0}, severity="warning", phrasing="recommendation",
    measured="material between a hole's edge and the part's outer edge", conflicts=["sendcutsend.cut.web_min_t_ratio", "sendcutsend.cut.hole_edge_d_ratio"])
add(SCS, "cut.hole_min_al6061_page", process="laser_cut", rule="hole_min", page="scs_6061", material="al6061", material_as_published="6061 T6 Aluminum",
    quote="Design holes no smaller than material thickness.", formula={"t": 1.0}, severity="warning", phrasing="recommendation",
    conflicts=["sendcutsend.cut.hole_min_t_ratio"], note="Under 'For best results'. Contradicts the 50 % guideline minimum.")
add(SCS, "cut.hole_edge_al6061_page", process="laser_cut", rule="hole_edge_web", page="scs_6061", material="al6061", material_as_published="6061 T6 Aluminum",
    quote="Keep holes and cutouts 1.5–2× material thickness away from edges to prevent warping or distortion.", formula={"t": 1.5},
    value_as_published="1.5–2× material thickness", severity="warning", phrasing="recommendation",
    note="Range published; the lower end (1.5 x thickness) is used as the limit.")
add(SCS, "cut.web_min_t_ratio", process="laser_cut", rule="web_min", page="scs_tol",
    quote="We recommend that hole diameters and bridging widths be no less than 50% of the material thickness. For example, on a 0.125” thick part, this would mean having 0.0625” between all of your cut features, or cut features and the edge of your part.",
    formula={"t": 0.5}, severity="warning", phrasing="recommendation", measured="least material between two cut features, or between a cut feature and the outer edge",
    yield_to_specific=True,
    note="The sheet-cutting guideline adds 'Minimum bridge width varies by material, check the material specs for your stock' (per-thickness values not readable without app.sendcutsend.com).")
add(SCS, "cut.web_preferred_t_ratio", process="laser_cut", rule="web_min", page="scs_tol",
    quote="For strength and cut quality reasons, we would prefer that wall thickness or bridging be closer to 1X – 1.5X the material thickness.",
    formula={"t": 1.0}, severity="info", phrasing="preference", measured="least material between cut features or to the edge",
    note="A preference, reported as information only (the 50 % figure above is the recommendation).")
add(SCS, "cut.hole_edge_d_ratio", process="laser_cut", rule="hole_edge_web", page="scs_tol",
    quote="we generally recommend keeping your holes at least 1X their diameter from an edge and slots at least 1.5X their width away from edges or other cut features.",
    formula={"d": 1.0}, severity="warning", phrasing="recommendation", measured="material between a round hole's edge and the outer edge, against the hole's diameter")
add(SCS, "cut.slot_edge_w_ratio", process="laser_cut", rule="slot_edge_web", page="scs_tol",
    quote="we generally recommend keeping your holes at least 1X their diameter from an edge and slots at least 1.5X their width away from edges or other cut features.",
    formula={"d": 1.5}, severity="warning", phrasing="recommendation", measured="material between a non-round cut-out and the outer edge or the next cut feature, against the slot's width")
add(SCS, "cut.removed_max_fraction", process="laser_cut", rule="cut_away_max", page="scs_cut_guide",
    quote="Keep material removal under 50%. Designs above that may be rejected.", value=0.5, unit="fraction", comparison="<=",
    severity="warning", phrasing="risk of rejection", measured="share of the outline's area cut away inside it")
add(SCS, "cut.tolerance", process="laser_cut", rule="tolerance_cut", page="scs_5052", material="al5052",
    quote="Laser-cuttable to ±.005” tolerance at SendCutSend in thicknesses from .040″–.500″.", value_mm=0.127, comparison="info", severity="info", phrasing="statement")
add(SCS, "cut.common_line_gap", process="laser_cut", rule="kerf", page="scs_cut_guide",
    quote="The actual gap between common-nested parts runs 0.006″ to 0.012″ depending on material", value_mm=[0.152, 0.305], comparison="info", severity="info", phrasing="statement")

# ---- cut part size per material and thickness (min/max chart)
for t in tables("scs_sizes")[1:2]:
    for mat, cells in walk(t):
        key = SCS_MAT.get(mat)
        if not key:
            continue
        thk_s, mx, cust, mn, proc = cells
        tmm = round(float(norm(thk_s).split("—")[0].replace("″", "").strip()) * IN, 3)
        tp = norm(thk_s).split("—")[0].strip()
        row_q = " | ".join([mat if True else "", thk_s, mx, cust, mn, proc])
        add(SCS, f"cut.part_min.{key}.{tkey(tmm)}", process="laser_cut", rule="part_min_size", page="scs_sizes", quote_kind="table_row",
            cells=[thk_s, mn], quote=f"Min/max part size chart, {mat} {thk_s}: Min Size {mn} (Max Instant Quote Size {mx})",
            material=key, material_as_published=mat, thickness_mm=tmm, thickness_as_published=tp, value_mm=inch_pair(mn),
            value_as_published=norm(mn), comparison=">=", severity="error", measured="flat part (short side, long side)")
        add(SCS, f"cut.part_max.{key}.{tkey(tmm)}", process="laser_cut", rule="part_max_size", page="scs_sizes", quote_kind="table_row",
            cells=[thk_s, mx], quote=f"Min/max part size chart, {mat} {thk_s}: Max Instant Quote Size {mx}; Max Custom Quote Size {cust}",
            material=key, material_as_published=mat, thickness_mm=tmm, thickness_as_published=tp, value_mm=inch_pair(mx),
            value_as_published=norm(mx), comparison="<=", severity="error", measured="flat part (short side, long side)",
            note=f"Instant-quote limit; custom quotes to {norm(cust)}.")

# ---- bending: bend calculator table (K, radius, die width, min formed flange, corner relief, relief depth)
bc = tables("scs_bendcalc")[0]
BENDMAT = {"5052 Aluminum": "al5052", "Mild Steel": "steel", "304 Stainless Steel": "stainless304"}
cur = None
for row in bc[1:]:
    if len(row) == 9:
        cur, cells = row[0], row[1:]
    elif len(row) == 8:
        cells = row
    else:
        continue
    key = BENDMAT.get(cur)
    if not key:
        continue
    thk, kf, bd, rad, die, fl, crd, rdep = cells
    if norm(kf) == "N/A":
        add(SCS, f"bend.not_offered.{key}.{tkey(inch(thk))}", process="bend", rule="bend_offered", page="scs_bendcalc", quote_kind="table_row",
            cells=[thk, "N/A"], quote=f"Bending specifications per material, {cur} {thk}: N/A in every column", material=key, material_as_published=cur,
            thickness_mm=inch(thk), thickness_as_published=norm(thk), value=False, unit="bool", comparison="==", severity="error")
        continue
    tmm = inch(thk)
    base = dict(process="bend", page="scs_bendcalc", quote_kind="table_row", material=key, material_as_published=cur, thickness_mm=tmm,
                thickness_as_published=norm(thk))
    hdr = "Bending specifications per material (bending calculator)"
    add(SCS, f"bend.radius.{key}.{tkey(tmm)}", rule="bend_radius", cells=[thk, rad], quote=f"{hdr}, {cur} {thk}: Effective Bend Radius @ 90° {rad}",
        value_mm=inch(rad), value_as_published=norm(rad), comparison="==", tolerance_mm=0.15, severity="warning", phrasing="the only radius offered",
        measured="modelled inside bend radius", **base,
        note="See this file's notes.bend_radius.")
    add(SCS, f"bend.k_factor.{key}.{tkey(tmm)}", rule="k_factor", cells=[thk, kf], quote=f"{hdr}, {cur} {thk}: K Factor {kf}",
        value=float(kf), unit="ratio", comparison="info", severity="info", **base)
    add(SCS, f"bend.die_width.{key}.{tkey(tmm)}", rule="feature_to_bend", cells=[thk, die],
        quote=f"{hdr}, {cur} {thk}: Die Width {die}. Bend deformation guideline: make sure your cut features are at least half the die’s width away from the bend line.",
        value_mm=round(inch(die) / 2, 3), value_as_published=f"Die Width {norm(die)} / 2", comparison=">=", severity="warning", phrasing="features inside will distort",
        reference="bend_centerline", measured="flat-pattern distance from the bend line (centre of the bend) to the nearest edge of a hole or cut-out", **base,
        die_width_mm=inch(die))
    add(SCS, f"bend.flange_min_formed.{key}.{tkey(tmm)}", rule="flange_min", cells=[thk, fl], quote=f"{hdr}, {cur} {thk}: Min Formed Flange Length @ 90° {fl}",
        value_mm=inch(fl), value_as_published=norm(fl), comparison=">=", severity="error", measured="formed flange length from the apex (outside mould line) of the bend", **base)
    add(SCS, f"bend.corner_relief_distance.{key}.{tkey(tmm)}", rule="corner_relief_distance", cells=[thk, crd],
        quote=f"{hdr}, {cur} {thk}: Min Corner Relief Distance from Bend Line {crd}", value_mm=inch(crd), value_as_published=norm(crd), comparison=">=",
        severity="warning", phrasing="table figure", evaluate=False, note="Relief geometry is not extracted by mechloop (gap).", **base)
    add(SCS, f"bend.relief_depth.{key}.{tkey(tmm)}", rule="relief_depth_min", cells=[thk, rdep], quote=f"{hdr}, {cur} {thk}: Bend Relief Depth {rdep}",
        value_mm=inch(rdep), value_as_published=norm(rdep), comparison=">=", severity="warning", phrasing="suggested", evaluate=False,
        note="Relief geometry is not extracted by mechloop (gap).", **base)

# ---- bending: processing min/max table (part size, radius, max bend length, flat and formed flange)
for mat, cells in walk(tables("scs_minmax")[1]):
    key = BENDMAT.get(mat)
    if not key:
        continue
    thk, mn, mx, rad, maxlen, flat, formed = cells
    if norm(mn) == "N/A":
        continue
    tmm = inch(thk)
    base = dict(process="bend", page="scs_minmax", quote_kind="table_row", material=key, material_as_published=mat, thickness_mm=tmm,
                thickness_as_published=norm(thk))
    hdr = "Min/max part sizes for bending"
    add(SCS, f"bend.part_min.{key}.{tkey(tmm)}", rule="bend_part_min_size", cells=[thk, mn], quote=f"{hdr}, {mat} {thk}: Min Flat Part Size {mn}",
        value_mm=inch_pair(mn), value_as_published=norm(mn), comparison=">=", severity="error", measured="flat blank (short side, long side)", **base)
    add(SCS, f"bend.part_max.{key}.{tkey(tmm)}", rule="bend_part_max_size", cells=[thk, mx], quote=f"{hdr}, {mat} {thk}: Max Flat Part Size {mx}",
        value_mm=inch_pair(mx), value_as_published=norm(mx), comparison="<=", severity="error", measured="flat blank (short side, long side)", **base)
    add(SCS, f"bend.length_max.{key}.{tkey(tmm)}", rule="bend_length_max", cells=[thk, maxlen], quote=f"{hdr}, {mat} {thk}: Max Bend Length {maxlen}",
        value_mm=inch(maxlen), value_as_published=norm(maxlen), comparison="<=", severity="error", measured="length of each bend", **base)
    add(SCS, f"bend.flange_min_flat.{key}.{tkey(tmm)}", rule="flange_min_flat", cells=[thk, flat],
        quote=f"{hdr}, {mat} {thk}: Min Flange Length (Before Bend/Flat Pattern) {flat}", value_mm=inch(flat), value_as_published=norm(flat),
        comparison=">=", severity="error", evaluate=False, note="The page does not say where the flat flange length is measured from; not evaluated (the formed figure is).", **base)
    add(SCS, f"bend.flange_min_formed_minmax.{key}.{tkey(tmm)}", rule="flange_min", cells=[thk, formed],
        quote=f"{hdr}, {mat} {thk}: Min Flange Length (After Bend) 90° or less (obtuse) {formed}", value_mm=inch(formed), value_as_published=norm(formed),
        comparison=">=", severity="error", measured="formed flange length from the apex (outside mould line) of the bend", evaluate=False,
        duplicate_of=f"sendcutsend.bend.flange_min_formed.{key}.{tkey(tmm)}", note="Same quantity as the bending-calculator 'Min Formed Flange Length @ 90°'; kept for cross-checking (the calculator row is evaluated).", **base)
    add(SCS, f"bend.radius_minmax.{key}.{tkey(tmm)}", rule="bend_radius", cells=[thk, rad], quote=f"{hdr}, {mat} {thk}: Effective Bend Radius @ 90° {rad}",
        value_mm=inch(rad), value_as_published=norm(rad), comparison="==", tolerance_mm=0.15, severity="warning", evaluate=False,
        duplicate_of=f"sendcutsend.bend.radius.{key}.{tkey(tmm)}", note="Kept for cross-checking against the bending calculator, which is evaluated.", **base)

# ---- bending: general
add(SCS, "bend.support_fraction", process="bend", rule="flange_support_min", page="scs_deform",
    quote="Approximately 50% of a bend’s length must meet the minimum flat flange length for the material to be formed successfully.",
    value=0.5, unit="fraction", comparison=">=", severity="error", measured="share of the bend's length over which the flange meets the minimum flange length",
    conflicts=["sendcutsend.bend.support_fraction_bending_page"])
add(SCS, "bend.support_fraction_bending_page", process="bend", rule="flange_support_min", page="scs_bending",
    quote="Flanges need to meet the minimum flange length for at least ~50–60% of the bend’s length on both sides to provide enough press brake support. Thicker materials (.187″–.250″) need more contact.",
    value=0.6, unit="fraction", comparison=">=", severity="warning", phrasing="range; upper end used as a warning",
    measured="share of the bend's length over which the flange meets the minimum flange length", conflicts=["sendcutsend.bend.support_fraction"])
add(SCS, "bend.support_full_thick", process="bend", rule="flange_support_min", page="scs_deform", thickness_range_mm=[4.75, 6.35],
    thickness_as_published="0.187” and thicker",
    quote="Due to safety and tolerance considerations, materials 0.187” and thicker may require that the minimum flange length be met on both sides of the bend line for the full bend length.",
    value=1.0, unit="fraction", comparison=">=", severity="warning", phrasing="may require")
add(SCS, "bend.angle_max", process="bend", rule="bend_angle_max", page="scs_bending", quote="Max Bend Angle |  130°", value=130.0, unit="deg",
    comparison="<=", severity="error", measured="bend angle (deflection from flat)")
add(SCS, "bend.u_channel", process="bend", rule="u_channel_base_ratio", page="scs_bending",
    quote="Sheet metal: base must be at least 2x the flange length (2:1 ratio)", value=2.0, unit="x flange", comparison=">=", severity="error",
    evaluate=False, note="U/C-channel recognition is not implemented (gap).")
add(SCS, "bend.relief_width", process="bend", rule="relief_width_min", page="scs_relief",
    quote="Width: The width of your relief should be at least half the thickness of your material.", formula={"t": 0.5}, severity="warning",
    phrasing="recommendation", evaluate=False, note="Relief geometry is not extracted (gap).")
add(SCS, "bend.relief_depth_formula", process="bend", rule="relief_depth_min", page="scs_relief",
    quote="Depth: The depth of your relief should be at least the material thickness + the bend radius + .02” (0.5mm) measured from the bend line.",
    formula={"t": 1.0, "r": 1.0, "const_mm": 0.508}, severity="warning", phrasing="recommendation", evaluate=False, note="Relief geometry is not extracted (gap).")
add(SCS, "bend.tolerance_edge", process="bend", rule="tolerance_bend", page="scs_bending",
    quote="Bend-to-edge tolerance: +/- 0.015″ (each additional bend adds at least 0.015″)", value_mm=0.381, comparison="info", severity="info")
add(SCS, "bend.tolerance_angle", process="bend", rule="tolerance_bend_angle", page="scs_bending", quote="Bends up to 24″: +/- 1°", value=1.0, unit="deg",
    comparison="info", severity="info")
add(SCS, "bend.tapped_csk_to_bend", process="bend", rule="tap_to_bend", page="scs_holedist",
    quote="To avoid distortion, ensure that tapped holes and the major diameter of any countersunk holes are at least half the die width away from the bend line, measured from the flat pattern.",
    formula={"die_half": 1.0}, severity="warning", phrasing="avoid distortion", reference="bend_centerline", evaluate=False,
    duplicate_of="sendcutsend.bend.die_width.<material>.<thickness>",
    note="Covered by the per-thickness die-width rule (feature_to_bend), which is applied to every hole.")

# ---- hardware (PEM) from the catalog
def hwfield(d, prefix):
    for k, v in d.items():
        if k.startswith(prefix):
            return k, v
    return None, None


SEEN_SKU = set()
NUT_FAMILIES = {"S", "SP", "F", "CLS", "CLA", "CLSS", "SMPS"}      # self-clinching nuts (studs and standoffs not transcribed)
for tb in tables("scs_hwcat"):
    d = {r[0]: r[1] for r in tb if len(r) >= 2}
    sku = d.get("SKU", "")
    thr = d.get("Thread Size", "")
    if not thr.startswith("M") or sku.split("-")[0] not in NUT_FAMILIES:
        continue
    size = thr.split()[0]
    sid = sku if sku not in SEEN_SKU else f"{sku}.{re.sub(r'[^A-Za-z0-9]+', '_', d.get('Fastener material') or 'dup')}"
    SEEN_SKU.add(sku)
    hw = {"sku": sku, "thread": size, "fastener_material": d.get("Fastener material")}
    hdr = f"Hardware catalog, SKU {sku} ({thr})"
    base = dict(process="hardware", page="scs_hwcat", quote_kind="table_row", hardware=hw)
    k, v = hwfield(d, "Hole size in sheet")
    if v and try_inch(v):
        add(SCS, f"pem.hole.{sid}", rule="pem_hole_diameter", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=try_inch(v), value_as_published=norm(v),
            comparison="info", severity="info", note="SendCutSend resizes hardware holes to this size.", **base)
    k, v = hwfield(d, "Minimum sheet thickness")
    if v and try_inch(v):
        add(SCS, f"pem.sheet_min.{sid}", rule="pem_sheet_min", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=try_inch(v), value_as_published=norm(v),
            comparison=">=", severity="error", measured="sheet thickness", **base)
    k, v = hwfield(d, "Maximum sheet thickness")
    if v and try_inch(v):
        add(SCS, f"pem.sheet_max.{sid}", rule="pem_sheet_max", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=try_inch(v), value_as_published=norm(v),
            comparison="<=", severity="error", measured="sheet thickness", **base)
    k, v = hwfield(d, "Aluminum material ranges")
    if v and "-" in v and "N/A" not in v:
        lo, hi = [try_inch(x) for x in norm(v).replace("–", "-").split("-")]
        if lo is None or hi is None:
            continue
        inverted = lo > hi
        add(SCS, f"pem.al_range.{sid}", rule="pem_sheet_range_al", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=[lo, hi], value_as_published=norm(v),
            comparison="within", severity="error", measured="aluminium sheet thickness", material="al*", **base,
            evaluate=not inverted,
            note=("Range for 5052, 6061, 7075 sheet." if not inverted else
                  "Published range is inverted (lower end larger than upper end; apparently a typo for 0.063 in.). Kept as published, not evaluated; "
                  "the SKU's minimum and maximum sheet thickness rows are evaluated instead."))
    k, v = hwfield(d, "Minimum distance hole C/L to edge")
    if v and try_inch(v):
        add(SCS, f"pem.edge.{sid}", rule="pem_center_to_edge", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=try_inch(v), value_as_published=norm(v),
            comparison=">=", severity="error", measured="hardware hole centre to the nearest cut edge (outline or another cut-out)", **base)
        if "bend" in k:
            add(SCS, f"pem.bend.{sid}", rule="pem_center_to_bend", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=try_inch(v), value_as_published=norm(v),
                comparison=">=", severity="error", reference="bend_tangent",
                measured="hardware hole centre to the edge of the bend allowance area (where the bend's radius starts)", **base)
    k, v = hwfield(d, "Minimum C/L to C/L")
    if v and try_inch(v):
        add(SCS, f"pem.pitch.{sid}", rule="pem_center_to_center", cells=[sku, v], quote=f"{hdr}: {k} {v}", value_mm=try_inch(v), value_as_published=norm(v),
            comparison=">=", severity="error", measured="centre to centre of two pieces of the same hardware", **base)

# ---- tapping (per material and thickness: smallest / largest metric tap), general rules
TAPMAT = {"5052 Aluminum": "al5052", "6061 Aluminum": "al6061", "Mild Steel": "steel", "304 Stainless Steel": "stainless304", "MIC-6 Aluminum": "al_mic6"}


def metric(s):
    m = re.match(r"M(\d+(?:\.\d+)?)", norm(s).upper())
    return float(m.group(1)) if m else None


for mat, cells in walk(tables("scs_minmax")[8]):
    key = TAPMAT.get(mat)
    if not key:
        continue
    thk, mn, mx, si, sm_, li, lm = cells
    tmm = inch(thk)
    base = dict(process="tap", page="scs_minmax", quote_kind="table_row", material=key, material_as_published=mat, thickness_mm=tmm,
                thickness_as_published=norm(thk))
    if norm(sm_) == "N/A":
        add(SCS, f"tap.not_offered.{key}.{tkey(tmm)}", rule="tap_offered", cells=[thk, "N/A"], quote=f"Min/max part and tap sizes, {mat} {thk}: N/A",
            value=False, unit="bool", comparison="==", severity="error", **base)
        continue
    add(SCS, f"tap.metric_range.{key}.{tkey(tmm)}", rule="tap_metric_range", cells=[thk, sm_, lm],
        quote=f"Min/max part and tap sizes, {mat} {thk}: Smallest Metric Tap {sm_}, Largest Metric Tap {lm}", value=[metric(sm_), metric(lm)],
        unit="metric thread diameter", comparison="within", severity="error", **base)
add(SCS, "tap.center_to_edge", process="tap", rule="tap_center_to_edge", page="scs_tap",
    quote="Keep the center of any tapped hole at least this distance from other cut features: (tap hole size ÷ 2) + minimum tap hole-to-edge distance for the material",
    formula={"tap_hole_half": 1.0, "material_min": 1.0}, severity="error", evaluate=False,
    note="The per-material minimum tap hole-to-edge distance is on the material pages (not readable); only one example was published (next rule).")
add(SCS, "tap.edge_example_al5052_0.125", process="tap", rule="tap_hole_to_edge", page="scs_holedist", material="al5052", thickness_mm=3.175,
    thickness_as_published="0.125”", quote="We’d need to calculate 0.209”/2 + 0.063” to find the minimum distance from the center of the tapped holes to the nearest cut feature.",
    value_mm=1.6, value_as_published="0.063”", comparison=">=", severity="error", yield_to_specific=True, measured="material between a tapped hole (tap-drill size) and the nearest cut feature",
    note="One worked example (1/4-20 in 0.125 in 5052); the figure 0.063 in is the 'Tapping Min Hole to Edge' for that stock.")

# ---- countersinking
for mat, cells in walk(tables("scs_minmax")[2]):
    key = TAPMAT.get(mat)
    if not key:
        continue
    thk, mn, mx, minor, major = cells
    tmm = inch(thk)
    base = dict(process="countersink", page="scs_minmax", quote_kind="table_row", material=key, material_as_published=mat, thickness_mm=tmm,
                thickness_as_published=norm(thk))
    if norm(minor) == "N/A" or norm(mn) == "N/A":
        add(SCS, f"csk.not_offered.{key}.{tkey(tmm)}", rule="countersink_offered", cells=[thk], quote=f"Min/max part and countersink sizes, {mat} {thk}: N/A",
            value=False, unit="bool", comparison="==", severity="error", **base)
        continue
    add(SCS, f"csk.offered.{key}.{tkey(tmm)}", rule="countersink_offered", cells=[thk, minor, major],
        quote=f"Min/max part and countersink sizes, {mat} {thk}: Min Minor {minor}, Max Major {major}", value=True, unit="bool", comparison="==",
        severity="error", minor_min_mm=inch(minor), major_max_mm=inch(major), **base)
add(SCS, "csk.depth_max", process="countersink", rule="countersink_depth_max", page="scs_csk",
    quote="| Max countersink depth | Should not exceed 60% of material thickness", formula={"t": 0.6}, comparison="<=", severity="error", evaluate=False,
    note="Countersink depth is not measured by mechloop (gap).")


# ---- engineering specs JSON (robots.txt allows /sendcutsend-specs.json): per-thickness cutting, tapping, countersinking, bending
SPECMAT = {"5052 H32 Aluminum": "al5052", "6061 T6 Aluminum": "al6061", "MIC6 Cast Aluminum Plate": "al_mic6",
           "A36/1008 Mild Steel": "steel", "Stainless Steel (304 series)": "stainless304"}
GEN = SPECS["_meta"]["generated_at"]
for m in SPECS["materials"]:
    key = SPECMAT.get(m["name"])
    th = (m.get("general_specs") or {}).get("thickness")
    if not key or not th:
        continue
    tmm = round(float(th) * IN, 3)

    def spec(rid, section, field, rule, comparison, severity, conv="in", **kw):
        v = (m.get(section) or {}).get(field)
        if v in (None, "", "N/A"):
            return None
        if conv == "in":
            val = dict(value_mm=round(float(v) * IN, 3))
        elif conv == "pair":
            a, b = [float(x) for x in v.split("x")]
            val = dict(value_mm=sorted([round(a * IN, 3), round(b * IN, 3)]))
        elif conv == "num":
            val = dict(value=float(v), unit=kw.pop("unit", ""))
        else:
            val = {}
        return add(SCS, f"specs.{rid}.{key}.{tkey(tmm)}", process=kw.pop("process"), rule=rule, page="scs_specs", quote_kind="json_field",
                   cells=[m["sku"], section, field, v], quote=f'sendcutsend-specs.json (generated {GEN}), {m["sku"]} {m["name"]} {th}: {section}.{field} = "{v}"',
                   material=key, material_as_published=m["name"], thickness_mm=tmm, thickness_as_published=f'{th}"', value_as_published=v,
                   comparison=comparison, severity=severity, sku=m["sku"], **val, **kw)

    c = "cutting_specs"
    spec("min_hole", c, "min_hole_size", "hole_min", ">=", "error", process="laser_cut", measured="smallest hole or cut-out",
         note="Per-stock figure from SendCutSend's engineering specs; it supersedes the 50 %-of-thickness guideline for this stock (the file says these sources are updated more often than the documentation).")
    spec("min_bridge", c, "min_bridge_size", "web_min", ">=", "error", process="laser_cut", measured="least material between cut features or to the edge")
    spec("min_hole_to_edge", c, "min_hole_to_edge", "hole_edge_web", ">=", "error", process="laser_cut", measured="material between a hole's edge and the outer edge")
    spec("cut_tolerance", c, "cut_tolerance", "tolerance_cut", "info", "info", process="laser_cut")
    spec("min_part", c, "min_part_size", "part_min_size", ">=", "error", conv="pair", process="laser_cut", evaluate=False,
         duplicate_of=f"sendcutsend.cut.part_min.{key}.{tkey(tmm)}", note="Cross-check of the min/max chart.")
    spec("max_part", c, "max_instant_pricing_part_size", "part_max_size", "<=", "error", conv="pair", process="laser_cut", evaluate=False,
         duplicate_of=f"sendcutsend.cut.part_max.{key}.{tkey(tmm)}", note="Cross-check of the min/max chart.")
    spec("tap_min_hole_to_edge", "tapping_specs", "min_hole_to_edge", "tap_hole_to_edge", ">=", "error", process="tap",
         measured="material between a tapped hole (tap-drill size) and the nearest cut feature")
    spec("csk_center_to_edge", "countersinking_specs", "min_hole_center_to_material_edge", "countersink_center_to_edge", ">=", "error",
         process="countersink", evaluate=False, note="Countersink positions are not extracted per hole (gap).")
    b = "bending_specs"
    spec("bend_radius", b, "effective_bend_radius", "bend_radius", "==", "warning", process="bend", tolerance_mm=0.15, evaluate=False,
         duplicate_of=f"sendcutsend.bend.radius.{key}.{tkey(tmm)}", note="Cross-check of the bending calculator figure.")
    spec("flange_after", b, "min_flange_length_after_bend", "flange_min", ">=", "error", process="bend", evaluate=False,
         duplicate_of=f"sendcutsend.bend.flange_min_formed.{key}.{tkey(tmm)}", note="Cross-check of the bending calculator figure.")
    dr = spec("die_half", b, "die_width", "feature_to_bend", ">=", "warning", process="bend", evaluate=False, reference="bend_centerline",
         duplicate_of=f"sendcutsend.bend.die_width.{key}.{tkey(tmm)}", note="Half the published die width; cross-check of the bending calculator.")
    if dr:
        dr["value_mm"] = round(dr["value_mm"] / 2, 3)
    spec("max_bend_length", b, "max_bend_length", "bend_length_max", "<=", "error", process="bend", evaluate=False,
         duplicate_of=f"sendcutsend.bend.length_max.{key}.{tkey(tmm)}", note="Cross-check of the processing min/max figure.")
    spec("center_bend_acute", b, "min_length_center_bend_line_acute", "flange_min_acute", ">=", "error", process="bend", evaluate=False,
         note="Minimum length from the bend centre line for acute bends; acute bends are not separated by mechloop (gap).")
    spec("min_bend_angle", b, "min_bend_angle", "bend_angle_min", ">=", "error", conv="num", unit="deg", process="bend",
         measured="bend angle (deflection from flat)")

# ---- countersink / tap absence for materials not in those tables (mild steel and 304: no countersinking rows)
# (absence is recorded by the evaluator as 'no published rule'; nothing invented here)

# =============================================================================== OSH Cut
OSH = "oshcut"
add(OSH, "cut.tolerance", process="laser_cut", rule="tolerance_cut", page="osh_capabilities",
    quote="OSH Cut's standard tolerances are +/- 0.005\" for most materials and thicknesses.", value_mm=0.127, comparison="info", severity="info")
add(OSH, "cut.thickness_min", process="laser_cut", rule="thickness_min", page="osh_capabilities",
    quote="Our minimum material thickness is 0.02\", but varies depending on the material.", value_mm=0.508, comparison=">=", severity="error", measured="sheet thickness")
add(OSH, "cut.thickness_max_al", process="laser_cut", rule="thickness_max", page="osh_capabilities", material="al*",
    quote="OSH Cut offers metal blank cutting in material thicknesses up to 1.0\" in steel and aluminum.", value_mm=25.4, comparison="<=", severity="error")
add(OSH, "cut.thickness_max_steel", process="laser_cut", rule="thickness_max", page="osh_capabilities", material="steel",
    quote="OSH Cut offers metal blank cutting in material thicknesses up to 1.0\" in steel and aluminum.", value_mm=25.4, comparison="<=", severity="error")
add(OSH, "cut.thickness_max_stainless", process="laser_cut", rule="thickness_max", page="osh_capabilities", material="stainless304",
    quote="We currently offer stainless thicknesses up to 5/8\" thick", value_mm=15.875, comparison="<=", severity="error")
add(OSH, "bend.tolerance_angle", process="bend", rule="tolerance_bend_angle", page="osh_services_bending",
    quote="Our standard bend angle tolerances are +/- 1.0 degree.", value=1.0, unit="deg", comparison="info", severity="info")
add(OSH, "bend.gauging_edge", process="bend", rule="gauging_edge_min", page="osh_dg_metal_bending_design_rules",
    quote="A flat part edge parallel to the bend line, at least 0.25\" long for small parts, or", value_mm=6.35, comparison=">=", severity="error",
    evaluate=False, note="Gauging-surface recognition is not implemented (gap).")
add(OSH, "csk.min_gauge", process="countersink", rule="countersink_thickness_min", page="osh_services_countersinking",
    quote="Typically, as long as the metal is 18-gauge or thicker, the integrity of the hole / depth stop should remain intact.", value_as_published="18-gauge",
    comparison=">=", severity="warning", evaluate=False, note="Gauge not converted: the page gives no thickness for '18-gauge' (it differs by material).")
add(OSH, "tap.metric_range", process="tap", rule="tap_metric_range", page="osh_services_metal_tapping",
    quote="OSH Cut offers metal tapping in tap sizes ranging from 6-32 to 1 1/2-6 (standard) and M3 x 0.5 to M36 - 4.0 (Metric).", value=[3.0, 36.0],
    unit="metric thread diameter", comparison="within", severity="error")
# part size per material and thickness (min/max page): only plain sheet rows of the materials of interest
OSHMAT = {"Aluminum 5052 H32": "al5052", "Aluminum 6061 T6": "al6061", "Stainless Steel 304, #2B finish": "stainless304",
          "Steel, A36 / A1011, HR P&O": "steel", "Steel, A1008, CR": "steel"}
seen = set()
for o in json.loads((PARSED / "osh_sizes.json").read_text()):
    key = OSHMAT.get(o["type"])
    th = o["thickness"]
    m = re.match(r'^(\d*\.?\d+)"', th)
    if not key or not m or not o["max_size"].endswith('"') or " x " not in o["max_size"]:
        continue
    tmm = round(float(m.group(1)) * IN, 3)
    k = (o["type"], tmm)
    if k in seen:
        continue
    seen.add(k)
    a, b = [float(x.strip().strip('"')) for x in o["max_size"].split(" x ")]
    assert norm(o["type"]) in text("osh_minimum_maximum_material_sizes")
    add(OSH, f"cut.part_max.{key}.{o['type'].split(',')[-1].strip().replace(' ', '_').replace('/', '')}.{tkey(tmm)}", process="laser_cut",
        rule="part_max_size", page="osh_minimum_maximum_material_sizes", quote_kind="text",
        quote=f"{o['type']} {th} {o['min_size']} {a:g} \" x {b:g} \"", material=key, material_as_published=o["type"], thickness_mm=tmm,
        thickness_as_published=th, value_mm=sorted([round(a * IN, 1), round(b * IN, 1)]), value_as_published=f'{a:g}" x {b:g}"', comparison="<=",
        severity="error", measured="flat part (short side, long side)",
        min_size_as_published=o["min_size"],
        note="The 'Min Size' column (" + o["min_size"] + ") is printed without a unit; it is kept as published and not evaluated.")

# =============================================================================== Protolabs
PL = "protolabs"
add(PL, "cut.tolerance", process="laser_cut", rule="tolerance_cut", page="pl_sm_laser", quote="+/- 0.005 in. for all features (except for hardware holes)",
    value_mm=0.127, comparison="info", severity="info")
add(PL, "cut.thickness_range", process="laser_cut", rule="thickness_range", page="pl_sm",
    quote="Sheet metal thickness ranges from 0.024 in. (0.609mm) to 0.250 in. (6.35mm).", value_mm=[0.609, 6.35], comparison="within", severity="error")
add(PL, "cut.hole_min", process="laser_cut", rule="hole_min", page="pl_sm", quote="Holes and slots should be a minimum of material thickness in diameter.",
    formula={"t": 1.0}, severity="warning", phrasing="should")
add(PL, "cut.slot_min", process="laser_cut", rule="slot_min", page="pl_sm", quote="Holes and slots should be a minimum of material thickness in diameter.",
    formula={"t": 1.0}, severity="warning", phrasing="should")
add(PL, "cut.hole_edge_thin", process="laser_cut", rule="hole_edge_web", page="pl_sm", thickness_range_mm=[0.0, 0.914], thickness_as_published="0.036 in. (0.914mm) or thinner",
    quote="If a material is 0.036 in. (0.914mm) or thinner, the hole should be 0.062 in. (1.574mm) from the material edge;", value_mm=1.574, severity="warning", phrasing="should",
    measured="material between the hole's edge and the outer edge (the page does not say whether from the hole's edge or centre; edge taken)")
add(PL, "cut.hole_edge_thick", process="laser_cut", rule="hole_edge_web", page="pl_sm", thickness_range_mm=[0.915, 6.35], thickness_as_published="thicker than 0.036 in. (0.914mm)",
    quote="if the material is thicker than 0.036 in. (0.914mm), the hole should be at least 0.125 in. (3.175mm) from the material edge to avoid distortion.", value_mm=3.175,
    severity="warning", phrasing="should", measured="material between the hole's edge and the outer edge (edge taken; the page does not say)")
add(PL, "cut.notch_min", process="laser_cut", rule="notch_min", page="pl_sm",
    quote="Notches must be at least the material’s thickness or 0.04 in. (1.016mm), whichever is greater, and can be no longer than 5 times its width.",
    formula={"t": 1.0, "floor_mm": 1.016}, severity="error", phrasing="must", measured="narrowest notch in the outline")
add(PL, "cut.tab_min", process="laser_cut", rule="tab_min", page="pl_sm",
    quote="Tabs must be at least 2 times the material’s thickness or 0.126 in. (3.200mm), whichever is greater, and can be no longer than 5 times its width.",
    formula={"t": 2.0, "floor_mm": 3.2}, severity="error", phrasing="must", measured="narrowest tab or neck of material")
add(PL, "cut.part_min_flat", process="laser_cut", rule="part_min_size", page="pl_sm", quote_kind="table_row", cells=["Flat Part", "0.250 in. x 0.250 in. 6.35mm x 6.35mm"],
    quote="Component Sizes for Sheet Metal Parts: Flat Part 0.250 in. x 0.250 in. 6.35mm x 6.35mm", value_mm=[6.35, 6.35], comparison=">=", severity="error")
add(PL, "bend.part_min_formed", process="bend", rule="bend_part_min_size", page="pl_sm", quote_kind="table_row", cells=["Formed Part", "0.500 in. x 0.500 in. 12.7mm x 12.7mm"],
    quote="Component Sizes for Sheet Metal Parts: Formed Part 0.500 in. x 0.500 in. 12.7mm x 12.7mm", value_mm=[12.7, 12.7], comparison=">=", severity="error")
add(PL, "cut.part_max", process="laser_cut", rule="part_max_size", page="pl_sm", quote_kind="table_row", cells=["Size", "39 in. x 47 in. 990.6mm x 1,193.8mm"],
    quote="Size 39 in. x 47 in. 990.6mm x 1,193.8mm", value_mm=[990.6, 1193.8], comparison="<=", severity="error")
add(PL, "bend.length_max", process="bend", rule="bend_length_max", page="pl_sm", quote_kind="table_row", cells=["Bend Length", "47 in. 1,193.8mm"],
    quote="Bend Length 47 in. 1,193.8mm", value_mm=1193.8, comparison="<=", severity="error")
add(PL, "bend.flange_min_4t", process="bend", rule="flange_min", page="pl_sm", quote="Minimum flange length on sheet metal parts must be at least 4 times the material thickness.",
    formula={"t": 4.0}, severity="error", phrasing="must", measured="formed flange length from the apex (outside mould line); the page does not say where from",
    conflicts=["protolabs.bend.flange_min.al.*"], note="Contradicts the DFM toolkit table (2.5 to 3.0 x thickness + bend radius for aluminium).")
add(PL, "bend.radii_standard", process="bend", rule="bend_radius_options", page="pl_sm",
    quote="We offer a wide range of common bend radii, but our standard options are .030 (.762mm), .060 (1.524mm), .090 (2.286mm), .120 (3.048mm).",
    value_mm=[0.762, 1.524, 2.286, 3.048], comparison="in", tolerance_mm=0.15, severity="info", phrasing="standard (3-day) options",
    note="The toolkit lists tooling from 0.01 in. to 1 in. (next rule); these four are the standard ones.")
add(PL, "bend.radii_tooling", process="bend", rule="bend_radius_range", page="pl_toolkit",
    quote="Protolabs provides a range of internal bend radius tooling options between 0.01 in. and 1 in.", value_mm=[0.254, 25.4], comparison="within",
    severity="warning", phrasing="tooling range; over 1 in. is bump formed")
add(PL, "bend.tolerance_angle", process="bend", rule="tolerance_bend_angle", page="pl_sm", quote="We hold a +/- 1 degree tolerance on all bend angles.", value=1.0,
    unit="deg", comparison="info", severity="info")
add(PL, "bend.6061_manual", process="bend", rule="bend_material_review", page="pl_sm_forming", material="al6061",
    quote="*Formed parts made out of Aluminum 6061-T6 require manual review and are not configurable during the quoting process.", value=True, unit="bool",
    comparison="info", severity="warning", phrasing="manual review", evaluate_on="bent")
add(PL, "bend.feature_near_bend_general", process="bend", rule="feature_to_bend", page="pl_sm",
    quote="Any feature that is within proximity of a bend (typically within 4x material thickness of the bend) is at risk for deformation.",
    formula={"t": 4.0}, severity="info", phrasing="typically at risk", reference="bend_tangent", measured="hole edge to where the bend starts",
    note="General statement; the toolkit table (per material and thickness) is the evaluated rule.")
PLT = {"Aluminum / Copper": ["al5052", "al6061", "al_mic6"], "CRS / Galv. / Galvnl.": ["steel"], "Stainless Steel": ["stainless304"]}
RANGES = {".024 -.050 in.": [0.609, 1.27], ".060 -.090 in.": [1.524, 2.286], ".100 -.134 in.": [2.54, 3.404], ".160+": [4.064, 6.35]}
for ti, rule, label in ((0, "flange_min", "Minimum flange length"), (1, "feature_to_bend", "Placing features near bends")):
    t = tables("pl_toolkit")[ti]
    cols = t[1]
    for row in t[2:]:
        rng = row[0]
        for ci, colname in enumerate(cols):
            txt = row[ci + 1]
            m = re.match(r"(\d+(?:\.\d+)?)x material thickness \+ bend radius", txt)
            assert m, txt
            for key in PLT[colname]:
                add(PL, f"bend.{rule}.{key}.{rng.replace(' ', '').replace('.in', 'in').replace('+', 'plus')}", process="bend", rule=rule, page="pl_toolkit",
                    quote_kind="table_row", cells=[rng, txt, colname], quote=f"DFM toolkit, {label}: {colname}, {rng}: {txt}", material=key,
                    material_as_published=colname, thickness_range_mm=RANGES[rng], thickness_as_published=rng,
                    formula={"t": float(m.group(1)), "r": 1.0}, value_as_published=txt, comparison=">=",
                    severity="error" if rule == "flange_min" else "warning",
                    phrasing="tooling requirement" if rule == "flange_min" else "distance guideline",
                    reference=None if rule == "flange_min" else "bend_tangent",
                    measured=("formed flange length from the apex (outside mould line)" if rule == "flange_min" else
                              "hole edge to where the bend's radius starts (the page does not define the reference; '+ bend radius' suggests the inside face of the bend)"),
                    conflicts=["protolabs.bend.flange_min_4t"] if rule == "flange_min" else None,
                    note="Thicknesses between the published ranges have no rule (not interpolated).")
add(PL, "pem.edge_mfr", process="hardware", rule="pem_center_to_edge", page="pl_sm",
    quote="If hardware inserts are required, the spacing should be according to manufacturer’s specifications.", comparison="info", severity="info", evaluate=False,
    note="Protolabs defers to PennEngineering's 'min. distance hole C/L to edge'; no figure on its own pages.")
add(PL, "pem.hole_tol", process="hardware", rule="pem_hole_tolerance", page="pl_sm_laser", quote="+0.003/-0.000 in. on hardware insert holes to ensure correct seating of inserts",
    value_mm=[0.0, 0.076], comparison="info", severity="info")
add(PL, "csk.major_range", process="countersink", rule="countersink_major_range", page="pl_sm",
    quote="We recommend the major diameters of countersinks measure between 0.090 in. (2.286mm) and 0.500 in. (12.7mm) using one of the following standard angles: 82°, 90°, 100°, and 120°.",
    value_mm=[2.286, 12.7], comparison="within", severity="warning", evaluate=False, note="Countersink major diameter is not extracted (gap).")
add(PL, "tol.hole_to_formed_thin", process="bend", rule="tolerance_bend", page="pl_sm", quote_kind="table_row", thickness_range_mm=[0.0, 3.3],
    cells=["Edge or Hole to Formed Feature", "0.010 in. (0.25mm)"], quote="Tolerances on Multiple Surfaces: Edge or Hole to Formed Feature, Material < .13 in.: 0.010 in. (0.25mm)",
    value_mm=0.25, comparison="info", severity="info")
add(PL, "tol.hole_to_formed_thick", process="bend", rule="tolerance_bend", page="pl_sm", quote_kind="table_row", thickness_range_mm=[3.3, 6.35],
    cells=["Edge or Hole to Formed Feature", "0.020 in. (0.508mm)"], quote="Tolerances on Multiple Surfaces: Edge or Hole to Formed Feature, Material > .13 in.: 0.020 in. (0.508mm)",
    value_mm=0.508, comparison="info", severity="info")
# Protolabs CNC
add(PL, "cnc.feature_min", process="cnc_milling", rule="cnc_min_wall", page="pl_cnc_mill_dg",
    quote="Part features are recommended to be thicker than 0.020 in. (0.51mm) throughout the part, and a nominal part thickness above 0.040 in. (1.02mm) is required.",
    value_mm=0.51, severity="warning", phrasing="recommended", measured="thinnest wall")
add(PL, "cnc.nominal_thickness", process="cnc_milling", rule="cnc_min_nominal_thickness", page="pl_cnc_mill_dg",
    quote="Part features are recommended to be thicker than 0.020 in. (0.51mm) throughout the part, and a nominal part thickness above 0.040 in. (1.02mm) is required.",
    value_mm=1.02, severity="error", phrasing="required", measured="smallest overall dimension of the part")
add(PL, "cnc.mill_depth_max", process="cnc_milling", rule="cnc_mill_depth_max", page="pl_cnc_mill_dg",
    quote="Maximum depth for factory machined parts that can be milled is 2 in. (50.8mm) from either side of the part.", value_mm=50.8, comparison="<=",
    severity="error", evaluate=False, note="Feature depth from each side is not extracted (gap).")
add(PL, "cnc.part_max_al_3axis", process="cnc_milling", rule="cnc_part_max_size", page="pl_cnc_mill_dg", material="al*", quote_kind="table_row",
    cells=["3-axis**", "Aluminum", "22 in. x 14 in. x 3.75 in.", "559mm x 356mm x 95.3mm"], quote="3-axis** Aluminum 22 in. x 14 in. x 3.75 in. 559mm x 356mm x 95.3mm",
    value_mm=[95.3, 356.0, 559.0], comparison="<=", severity="error", measured="part extents (sorted)", note="** two-sided machining only.")
add(PL, "cnc.part_max_ss304_5axis", process="cnc_milling", rule="cnc_part_max_size", page="pl_cnc_mill_dg", material="stainless304", quote_kind="table_row",
    cells=["5-axis", "Stainless Steel 304", "4.25 in. x 3.25 in. x 3.75 in.", "107.95mm x 82.55mm x 95.25mm"],
    quote="5-axis Stainless Steel 304 4.25 in. x 3.25 in. x 3.75 in. 107.95mm x 82.55mm x 95.25mm", value_mm=[82.55, 95.25, 107.95], comparison="<=", severity="error")
add(PL, "cnc.threads", process="cnc_milling", rule="cnc_thread_range", page="pl_cnc_mill_dg",
    quote="In the Protolabs automated factory, we currently support UNC and UNF threads from #2 up to 0.5 in., and metric threads from M2 to M12.", value=[2.0, 12.0],
    unit="metric thread diameter", comparison="within", severity="error")
add(PL, "cnc.tolerance", process="cnc_milling", rule="tolerance_cnc", page="pl_cnc_mill_dg",
    quote="Typically, Protolabs can hold a machining tolerance of +/- 0.005 in. (0.13mm) at its fully automated facility", value_mm=0.13, comparison="info", severity="info")

# =============================================================================== Xometry
XO = "xometry"
xs = "Sheet metal fabrication, design guidelines table (MT = Material Thickness)"
for rid, rule, label, val, comp, sev, meas, extra in (
        ("bend.radius_min", "bend_radius_min", "Minimum Bend", "1X MT", ">=", "warning", "inside bend radius", {}),
        ("cut.hole_edge", "hole_edge_web", "Minimum Hole to Edge Distance", "2X MT", ">=", "warning", "material between a hole's edge and the outer edge (reference not stated; edge taken)", {}),
        ("cut.hole_hole", "hole_hole_web", "Minimum Hole to Hole Distance", "6X MT", ">=", "warning", "material between two holes (reference not stated; edge to edge taken)", {}),
        ("bend.hole_to_bend", "feature_to_bend", "Minimum Bend Edge to Hole Distance", "6X MT", ">=", "warning", "hole edge to the bend edge (where the bend's radius starts)", {"reference": "bend_tangent"}),
        ("csk.feature_to_csk", "countersink_to_feature", "Minimum Feature to Countersink Distance", "8X MT", ">=", "warning", "", {"evaluate": False, "note": "Countersink positions are not extracted per hole (gap)."}),
        ("csk.depth_min", "countersink_depth_min", "Minimum Countersink Depth", "0.6X MT", ">=", "warning", "", {"evaluate": False, "note": "Countersink depth is not measured (gap)."}),
        ("bend.relief", "relief_width_min", "Relief Cuts", "1X MT", ">=", "warning", "", {"evaluate": False, "note": "Relief geometry is not extracted (gap)."}),
        ("cut.corner_fillet", "corner_fillet_min", "Corner Fillets", "0.5X MT", ">=", "warning", "", {"evaluate": False, "note": "Outside-corner radii are judged by dfm_edges; not evaluated here."})):
    f = float(val.split("X")[0])
    add(XO, rid, process="bend" if rid.startswith("bend") else ("countersink" if rid.startswith("csk") else "laser_cut"), rule=rule, page="xo_smfab", quote_kind="table_row",
        cells=[f"Feature{label}", f"Description (MT = Material Thickness){val}"], quote=f"{xs}: {label} | {val}", formula={"t": f}, value_as_published=val,
        comparison=comp, severity=sev, phrasing="design guideline table", measured=meas or None, **extra)
add(XO, "cut.feature_min_laser", process="laser_cut", rule="hole_min", page="xo_laser", quote_kind="table_row",
    cells=["DescriptionMinimum Feature Size", 'General Tolerance2X material thickness with a minimum of 0.062"'],
    quote='Laser Cut Metal General Tolerances: Minimum Feature Size | 2X material thickness with a minimum of 0.062"', formula={"t": 2.0, "floor_mm": 1.575},
    severity="warning", phrasing="general tolerance table", conflicts=["xometry.cut.hole_min_sheetcut"])
add(XO, "cut.hole_min_sheetcut", process="laser_cut", rule="hole_min", page="xo_sheetcut",
    quote="Holes and cutouts should be larger than the material thickness or 0.050”, whichever is greater.", formula={"t": 1.0, "floor_mm": 1.27},
    severity="warning", phrasing="should", conflicts=["xometry.cut.feature_min_laser"],
    note="Contradicts the laser-cutting page (2 x thickness, at least 0.062 in.).")
add(XO, "cut.part_min_laser", process="laser_cut", rule="part_min_size", page="xo_laser", quote_kind="table_row",
    cells=["DescriptionMinimum Recommend Part Size", 'General Tolerance1.000"'], quote='Minimum Recommend Part Size | 1.000"', value_mm=[25.4, 25.4],
    comparison=">=", severity="warning", phrasing="recommended")
add(XO, "cut.kerf_laser", process="laser_cut", rule="kerf", page="xo_laser", quote_kind="table_row", cells=["DescriptionKerf (slit size)", 'General ToleranceApproximately 0.020"'],
    quote='Kerf (slit size) | Approximately 0.020"', value_mm=0.508, comparison="info", severity="info", conflicts=["xometry.cut.kerf_sheetcut"])
add(XO, "cut.kerf_sheetcut", process="laser_cut", rule="kerf", page="xo_sheetcut",
    quote="Kerf is the gap thickness created by the laser and is usually around 0.008” with a +/- 0.004” tolerance depending on the process and material thickness.",
    value_mm=0.203, comparison="info", severity="info", conflicts=["xometry.cut.kerf_laser"])
add(XO, "cut.tolerance", process="laser_cut", rule="tolerance_cut", page="xo_std", quote="Edge to edge tolerances is +/- .010” nominal on the top face of the plate/sheet.",
    value_mm=0.254, comparison="info", severity="info")
add(XO, "cut.thickness_range_fab", process="bend", rule="thickness_range", page="xo_smfab", quote_kind="table_row",
    cells=["FeatureSheet Thickness", "Description0.024” - 0.250” typical. We accommodate thicker or thinner gauges upon request."],
    quote="Sheet Thickness | 0.024” - 0.250” typical. We accommodate thicker or thinner gauges upon request.", value_mm=[0.61, 6.35], comparison="within",
    severity="info", phrasing="typical")
for code, val in (("A", "± .015″ Edge to bend"), ("D", "± .015″ Bend to hole or internal cut feature"), ("F", "± 1 Degree Bend angle")):
    add(XO, f"bend.tolerance_{code}", process="bend", rule="tolerance_bend", page="xo_std", quote=f"{code} - {val}", comparison="info", severity="info",
        value_as_published=val)
# Xometry CNC
add(XO, "cnc.min_feature", process="cnc_milling", rule="cnc_min_feature", page="xo_cnc", quote_kind="table_row",
    cells=["FeatureMinimum Feature Size", "Description0.020” (0.50 mm). This may vary depending on part geometry and chosen material."],
    quote="Minimum Feature Size | 0.020” (0.50 mm). This may vary depending on part geometry and chosen material.", value_mm=0.5, severity="error",
    measured="smallest hole diameter and thinnest wall")
add(XO, "cnc.part_max_milled", process="cnc_milling", rule="cnc_part_max_size", page="xo_cnc", quote_kind="table_row",
    cells=["FeatureMaximum Part Size", "DescriptionMilled parts up to 80” x 48” x 24” (2,032 x 1,219 x 610 mm). Lathe parts up to 62” (1,575 mm) length and 32” (813 mm) diameter."],
    quote="Maximum Part Size | Milled parts up to 80” x 48” x 24” (2,032 x 1,219 x 610 mm).", value_mm=[610.0, 1219.0, 2032.0], comparison="<=", severity="error")
add(XO, "cnc.tolerance", process="cnc_milling", rule="tolerance_cnc", page="xo_cnc", quote_kind="table_row",
    cells=["FeatureGeneral Tolerances", "DescriptionTolerances on metals will be held to +/- 0.005\" (+/- 0.127 mm) in accordance with ISO 2768 unless otherwise specified. Plastics and composites will be +/- 0.010”."],
    quote="General Tolerances | Tolerances on metals will be held to +/- 0.005\" (+/- 0.127 mm) in accordance with ISO 2768 unless otherwise specified.", value_mm=0.127,
    comparison="info", severity="info")
add(XO, "cnc.thread_callout", process="cnc_milling", rule="cnc_thread_callout", page="xo_cnc",
    quote="Tapped holes not explicitly called out as Features on the quoted CAD model may be machined to the diameters specified in that model.", comparison="info",
    severity="warning", phrasing="threads must be called out", value=True, unit="bool")

# =============================================================================== Fictiv
FI = "fictiv"
for rid, rule, q, formula, extra in (
        ("bend.k_factor_al", "k_factor", "K-FACTOR: Soft (AL) 0.33–0.40, Medium (Steel) 0.40–0.45, Hard (SS) 0.45–0.50", None,
         {"value": [0.33, 0.40], "unit": "ratio", "comparison": "info", "severity": "info", "material": "al*"}),
        ("bend.relief_width", "relief_width_min", "RELIEF WIDTH: Material thickness or 0.030″, whichever greater", {"t": 1.0, "floor_mm": 0.762},
         {"evaluate": False, "note": "Relief geometry is not extracted (gap)."}),
        ("bend.relief_depth", "relief_depth_min", "RELIEF DEPTH: 1.5× material thickness minimum", {"t": 1.5}, {"evaluate": False, "note": "Relief geometry is not extracted (gap)."}),
        ("bend.flange_min_standard", "flange_min", "MIN FLANGE: Standard 4× thickness, Absolute min 3×, Hems 5×", {"t": 4.0},
         {"severity": "warning", "phrasing": "standard", "measured": "formed flange length (reference not stated; from the apex taken)"}),
        ("bend.flange_min_absolute", "flange_min", "MIN FLANGE: Standard 4× thickness, Absolute min 3×, Hems 5×", {"t": 3.0},
         {"severity": "error", "phrasing": "absolute minimum", "measured": "formed flange length (reference not stated; from the apex taken)"}),
        ("cut.hole_min", "hole_min", "Min hole Ø: 1.0× thickness (min 0.031″)", {"t": 1.0, "floor_mm": 0.787}, {}),
        ("cut.hole_edge", "hole_edge_web", "Hole to edge: ≥2× thickness (min 0.062″)", {"t": 2.0, "floor_mm": 1.575}, {"measured": "material between hole edge and outer edge (reference not stated)"}),
        ("bend.hole_to_bend", "feature_to_bend", "Hole to bend: ≥2.5× thickness + bend radius", {"t": 2.5, "r": 1.0}, {"reference": "bend_tangent"}),
        ("cut.slot_min", "slot_min", "Slots: Min width 1.0× thickness, radius ≥0.5× width", {"t": 1.0}, {}),
        ("pem.edge", "pem_center_to_edge", "PEM: Add 0.005–0.010″ clearance, min edge 2.5× hole Ø", {"d": 2.5},
         {"measured": "hardware hole centre to the outer edge against the hardware hole diameter (reference not stated; centre taken)"})):
    kw = dict(process="bend" if rid.startswith("bend") else ("hardware" if rid.startswith("pem") else "laser_cut"), rule=rule, page="fictiv_spec_sm", quote=q,
              formula=formula, severity="warning", phrasing="specification guideline")
    kw.update(extra)
    add(FI, rid, **kw)
for mat_pub, key, lo, pub in (("Aluminum 5052", "al5052", 0.5, "0.5t – 1.0t"), ("Cold Rolled Steel", "steel", 0.5, "0.5t – 1.0t"), ("Stainless 304", "stainless304", 1.0, "1.0t – 2.0t")):
    add(FI, f"bend.radius_min.{key}", process="bend", rule="bend_radius_min", page="fictiv_spec_sm", quote_kind="table_row", cells=[mat_pub, pub],
        quote=f"Bending Guidelines, Material | Min Bend Radius: {mat_pub} | {pub}", material=key, material_as_published=mat_pub,
        formula={"t": lo}, value_as_published=pub, severity="warning", phrasing="range; lower end used",
        note="A range is published as the minimum bend radius; its lower end is used as the limit.")
add(FI, "bend.radius_min.al_unspecified", process="bend", rule="bend_radius_min", page="fictiv_spec_sm", quote_kind="table_row", cells=["Aluminum", "1.0t – 2.0t"],
    quote="Bending Guidelines, Material | Min Bend Radius: Aluminum | 1.0t – 2.0t", material="al6061", material_as_published="Aluminum (alloy not named)",
    formula={"t": 1.0}, value_as_published="1.0t – 2.0t", severity="warning", phrasing="range; lower end used",
    note="The row says only 'Aluminum' beside a separate 'Aluminum 5052' row; applied to 6061 as the non-5052 aluminium. Flagged as an interpretation.")
add(FI, "cut.tolerance", process="laser_cut", rule="tolerance_cut", page="fictiv_spec_sm", quote="+/- 0.005\" Tightest Tolerance", value_mm=0.127, comparison="info", severity="info")
add(FI, "bend.tolerance_angle", process="bend", rule="tolerance_bend_angle", page="fictiv_spec_sm", quote="0.5°–1° Bend Tol", value=[0.5, 1.0], unit="deg", comparison="info", severity="info")
add(FI, "cut.thickness_range", process="laser_cut", rule="thickness_range", page="fictiv_spec_sm", quote="0.015\"-0.375\" Thickness Range", value_mm=[0.381, 9.525],
    comparison="within", severity="warning", phrasing="published range")
add(FI, "cnc.pocket_depth", process="cnc_milling", rule="cnc_pocket_depth_ratio", page="fictiv_spec_cnc", quote="Avoid deep pockets and cavities (max depth = 4x tool diameter)",
    value=4.0, unit="x tool diameter", comparison="<=", severity="warning", evaluate=False, note="Pocket depth against tool diameter is not extracted (gap).")
add(FI, "cnc.threads", process="cnc_milling", rule="cnc_thread_standard", page="fictiv_spec_cnc",
    quote="Use standard thread sizes (UNC/UNF, metric coarse/fine) – special pitches require custom taps ($30-150) and hand-tapping time", comparison="info", severity="info")

# =============================================================================== Hubs (Protolabs Network)
HU = "hubs"
for rid, rule, q, formula, extra in (
        ("cut.hole_min", "hole_min", "Specify hole diameters larger than the sheet thickness", {"t": 1.0}, {}),
        ("cut.hole_hole", "hole_hole_web", "Space holes at least 2 times the sheet thickness apart", {"t": 2.0}, {}),
        ("cut.hole_edge", "hole_edge_web", "Holes should be at least the sheet’s thickness from the edge", {"t": 1.0}, {}),
        ("bend.hole_to_bend", "feature_to_bend", "Ensure holes are at least 2 times the sheet thickness from the start of the bend radius", {"t": 2.0},
         {"reference": "bend_tangent", "measured": "hole edge to where the bend's radius starts"}),
        ("bend.radius_min", "bend_radius_min", "parts should be designed with the interior bend radius to be the same size or greater than the material thickness.", {"t": 1.0}, {}),
        ("bend.flange_min", "flange_min", "Ensure the bend height is at least double the material thickness plus the bend radius", {"t": 2.0, "r": 1.0},
         {"measured": "formed flange height from the outside of the bend"}),
        ("bend.relief_width", "relief_width_min", "To add a relief cut to your design, add an incision either side of the bend that is at least the same width or greater than the material thickness.",
         {"t": 1.0}, {"evaluate": False, "note": "Relief geometry is not extracted (gap)."})):
    kw = dict(process="bend" if rid.startswith("bend") else "laser_cut", rule=rule, page="hubs_sm_basic", quote=q, formula=formula, severity="warning",
              phrasing="design best practice")
    kw.update(extra)
    add(HU, rid, **kw)

# =============================================================================== cross-check duplicates
for r in list(RULES.values()):
    dup = r.get("duplicate_of")
    if not dup or dup not in RULES:
        continue
    prim = RULES[dup]
    pv, rv = prim.get("value_mm"), r.get("value_mm")
    differ = (sorted(pv) != sorted(rv) and any(abs(a - b) > 0.2 for a, b in zip(sorted(pv), sorted(rv)))) if isinstance(pv, list) and isinstance(rv, list) \
        else abs((pv or 0) - (rv or 0)) > 0.01
    if differ:
        msg = f"{prim['source_url']} gives {prim.get('value_as_published')}, {r['source_url']} gives {r.get('value_as_published')}"
        for a, b in ((prim, r), (r, prim)):
            a.setdefault("conflicts", [])
            if b["id"] not in a["conflicts"]:
                a["conflicts"].append(b["id"])
            if msg not in a.setdefault("conflict_notes", []):
                a["conflict_notes"].append(msg)
        print("CONFLICT", prim["id"], msg)

# =============================================================================== write
SUPPLIERS = {
    "sendcutsend": {"name": "SendCutSend", "processes": ["laser_cut", "bend", "hardware", "tap", "countersink"], "home": "https://sendcutsend.com/"},
    "oshcut": {"name": "OSH Cut", "processes": ["laser_cut", "bend", "tap", "countersink"], "home": "https://www.oshcut.com/"},
    "protolabs": {"name": "Protolabs", "processes": ["laser_cut", "bend", "hardware", "countersink", "cnc_milling"], "home": "https://www.protolabs.com/"},
    "xometry": {"name": "Xometry", "processes": ["laser_cut", "bend", "countersink", "cnc_milling"], "home": "https://www.xometry.com/"},
    "fictiv": {"name": "Fictiv", "processes": ["laser_cut", "bend", "hardware", "cnc_milling"], "home": "https://www.fictiv.com/"},
    "hubs": {"name": "Hubs (Protolabs Network)", "processes": ["laser_cut", "bend"], "home": "https://www.hubs.com/"},
}
NOTES = {"sendcutsend": {"bend_radius": "Bending guidelines (https://sendcutsend.com/services/cnc-bending/): 'Bend radius and K factor are set per material thickness. Design your parts using our specs so they form as expected, we don't offer custom bend radii.' A part modelled at another radius is formed at this one, so its flanges move: a warning, not a refusal."}}
NOT_READ = json.loads((SCR / "dfmtools" / "not_read.json").read_text())
OUT.mkdir(parents=True, exist_ok=True)
for sup, meta in SUPPLIERS.items():
    rules = [r for r in RULES.values() if r["supplier"] == sup]
    doc = {"schema": "mechloop.supplier_rules/1", "version": "2026-11-19.1", "supplier": sup, "name": meta["name"], "home": meta["home"],
           "retrieved": DATE, "processes": meta["processes"],
           "how_read": "Plain HTTPS page fetch, no account, no quote; figures copied as published. Prose quotes are verbatim; 'table_row' quotes name the table, row and cells.",
           "not_read": NOT_READ.get(sup, []), "notes": NOTES.get(sup, {}), "rules": rules}
    (OUT / f"{sup}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(sup, len(rules))
print("quotes checked", CHECKED_QUOTES, "unparsed cells skipped", SKIPPED)
