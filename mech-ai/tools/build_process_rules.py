"""Build mechloop/data/supplier_rules_cnc_3dp/*.json: suppliers' published CNC-milling and 3D-printing rules.

Same schema as the sheet-metal rules ("mechloop.supplier_rules/1"): every rule carries supplier, process, material,
rule kind, value (or a formula), comparison, severity, source_url, a quote and the retrieval date. Quotes are verified
before anything is written:

- "text": the quote occurs verbatim (whitespace-normalised) in the saved page's text;
- "table_row": every cell given occurs in ONE row of a table parsed from the saved page;
- "json_field": the field of SendCutSend's engineering-specs JSON has exactly that value;
- "repo_file": the quote occurs verbatim (whitespace-normalised) in the named repository file (own_printer rules).

The saved pages are untrusted data: this script only parses them. Run with an isolated interpreter:

    python -I tools/build_process_rules.py <sources_dir> <repo_root> <out_dir>

<sources_dir> holds raw/<page>.txt (text extracted from raw/<page>.html), parsed/<page>_tables.json and
app/scs_sendcutsend-specs.json, as saved on 2026-11-19 (fetch log: fetch_log.jsonl).
"""
import json
import sys
from pathlib import Path

SRC = Path(sys.argv[1])
REPO = Path(sys.argv[2])
OUT = Path(sys.argv[3])
DATE = "2026-11-19"
IN = 25.4

URL = {
    # Xometry
    "xo_cnc": "https://www.xometry.com/capabilities/cnc-machining-service/",
    "xo_std": "https://www.xometry.com/manufacturing-standards/",
    "xo_corner": "https://www.xometry.com/resources/machining/cnc-machining-optimizing-internal-corner-radii/",
    "xo_thin": "https://www.xometry.com/resources/machining/cnc-machining-thin-walls/",
    "xo_costred": "https://www.xometry.com/resources/machining/cnc-machining-cost-reduction/",
    "xo_3dp": "https://www.xometry.com/capabilities/3d-printing-service/",
    "xo_fdm": "https://www.xometry.com/capabilities/3d-printing-service/fused-deposition-modeling/",
    "xo_pla_petg": "https://www.xometry.com/capabilities/3d-printing-service/pla-petg/",
    "xo_sls": "https://www.xometry.com/capabilities/3d-printing-service/selective-laser-sintering/",
    "xo_mjf": "https://www.xometry.com/capabilities/3d-printing-service/hp-multi-jet-fusion/",
    "xo_sla": "https://www.xometry.com/capabilities/3d-printing-service/stereolithography-3d-printing/",
    # Protolabs
    "pl_cnc_mill_dg": "https://www.protolabs.com/services/cnc-machining/cnc-milling/design-guidelines/",
    "pl_cnc_threads_std": "https://www.protolabs.com/services/cnc-machining/threaded-holes-guidelines/standard-holes/",
    "pl_cnc_tol": "https://www.protolabs.com/services/cnc-machining/precision-machining-tolerances/",
    "pl_fdm": "https://www.protolabs.com/services/3d-printing/fused-deposition-modeling/",
    "pl_sls": "https://www.protolabs.com/services/3d-printing/selective-laser-sintering/",
    "pl_mjf": "https://www.protolabs.com/services/3d-printing/multi-jet-fusion/",
    "pl_sla": "https://www.protolabs.com/services/3d-printing/stereolithography/",
    "pl_thin": "https://www.protolabs.com/resources/design-tips/how-to-solve-for-size-constraints-small-gaps-and-thin-walls-in-3d-printed-parts/",
    "pl_3dp_tol": "https://www.protolabs.com/resources/design-tips/3d-printing-tolerances/",
    # Hubs (Protolabs Network)
    "hubs_cnc_design": "https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/",
    "hubs_sharp": "https://www.hubs.com/knowledge-base/sharp-corners-in-cnc-machining/",
    "hubs_cnc_tol": "https://www.hubs.com/knowledge-base/cnc-machining-iso-based-tolerances-and-finishes/",
    "hubs_drills": "https://www.hubs.com/knowledge-base/standard-drill-bit-sizes-cnc-machining-conversion-tables/",
    "hubs_cnc_service": "https://www.hubs.com/cnc-machining/",
    "hubs_fdm_design": "https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/",
    "hubs_geom": "https://www.hubs.com/knowledge-base/3d-printing-geometry-restrictions/",
    "hubs_thin": "https://www.hubs.com/knowledge-base/dfm-tips-for-3d-printed-parts-with-thin-walls/",
    "hubs_fdm_service": "https://www.hubs.com/3d-printing/fdm/",
    "hubs_sls_service": "https://www.hubs.com/3d-printing/sls/",
    "hubs_sls_design": "https://www.hubs.com/knowledge-base/how-design-parts-sls-3d-printing/",
    "hubs_mjf_design": "https://www.hubs.com/knowledge-base/how-to-design-parts-for-mjf/",
    "hubs_sla_design": "https://www.hubs.com/knowledge-base/how-design-parts-sla-3d-printing/",
    # Fictiv (the specification page re-fetch returned 403; the copy read earlier the same day by plain fetch is used)
    "fictiv_spec_cnc_earlier": "https://www.fictiv.com/specifications/cnc-machining",
    # JLC
    "jlccnc_dg": "https://jlccnc.com/help/article/cnc-machining-design-guideline",
    "jlccnc_limits": "https://jlccnc.com/blog/cnc-machining-design-limitations",
    "jlc3dp_dg": "https://jlc3dp.com/help/article/3d-printing-design-guideline",
    "jlc3dp_cap_3dp": "https://jlc3dp.com/capabilities/3d-printing-service",
    # SendCutSend
    "scs_cnc_guide": "https://sendcutsend.com/guidelines/cnc-machining/",
    "scs_specs": "https://app.sendcutsend.com/sendcutsend-specs.json",
    # RapidDirect
    "rd_cnc_dg": "https://www.rapiddirect.com/blog/cnc-machining-design-guide/",
    "rd_3dp_dg": "https://www.rapiddirect.com/blog/3d-printing-design/",
    # Shapeways (the URL redirected to /materials/pa12)
    "shapeways_vp": "https://www.shapeways.com/materials/pa12",
    # PCBWay
    "pcbway_3dp": "https://www.pcbway.com/rapid-prototyping/3D-Printing/",
}
REPO_FILES = {"guidelines": "docs/DESIGN_GUIDELINES.md", "printsettings": "mechloop/printsettings.py",
              "dfm_rules": "mechloop/verifiers/dfm_rules.py", "dfm_print": "mechloop/verifiers/dfm_print.py", "agent": "AGENT.md"}

_TEXT, _TABLES = {}, {}
SPECS = json.loads((SRC / "app" / "scs_sendcutsend-specs.json").read_text(encoding="utf-8"))


def norm(s):
    return " ".join(str(s).replace(" ", " ").split())


def text(page):
    if page not in _TEXT:
        _TEXT[page] = norm((SRC / "raw" / f"{page}.txt").read_text(encoding="utf-8"))
    return _TEXT[page]


def repo_text(key):
    k = ("repo", key)
    if k not in _TEXT:
        _TEXT[k] = norm((REPO / REPO_FILES[key]).read_text(encoding="utf-8"))
    return _TEXT[k]


def table_rows(page):
    if page not in _TABLES:
        tabs = json.loads((SRC / "parsed" / f"{page}_tables.json").read_text(encoding="utf-8"))
        _TABLES[page] = [[norm(c) for c in r] for t in tabs for r in t]
    return _TABLES[page]


RULES = {}
FAIL = []
CHECKED = {"text": 0, "table_row": 0, "json_field": 0, "repo_file": 0}


def add(supplier, rid, *, process, rule, page, quote, quote_kind="text", cells=None, material="*", material_as_published=None,
        value_mm=None, value=None, unit="mm", value_as_published=None, formula=None, comparison=">=", severity="warning",
        phrasing="recommendation", measured=None, note=None, evaluate=True, applies=None, **extra):
    if page in REPO_FILES and quote_kind == "text":
        quote_kind = "repo_file"
    if quote_kind == "text":
        if norm(quote) not in text(page):
            FAIL.append((supplier, rid, page, "text", quote[:100]))
    elif quote_kind == "table_row":
        rows = table_rows(page)
        want = [norm(c) for c in cells]
        if not any(all(w in r for w in want) for r in rows):
            FAIL.append((supplier, rid, page, "table", want))
    elif quote_kind == "json_field":
        sku, section, field, val = cells
        m = next(x for x in SPECS["materials"] if x["sku"] == sku)
        assert str(m[section][field]) == val, (rid, sku, section, field, val)
    elif quote_kind == "repo_file":
        if norm(quote) not in repo_text(page):
            FAIL.append((supplier, rid, page, "repo", quote[:100]))
    else:
        raise ValueError(quote_kind)
    CHECKED[quote_kind] += 1
    r = {"id": f"{supplier}.{rid}", "supplier": supplier, "process": process, "rule": rule, "material": material}
    if material_as_published:
        r["material_as_published"] = material_as_published
    r["thickness_mm"] = None
    if value_mm is not None:
        r["value_mm"] = value_mm
    if value is not None:
        r["value"] = value
        r["unit"] = unit
    if formula:
        r["formula"] = formula
    if value_as_published is not None:
        r["value_as_published"] = value_as_published
    if applies:
        r["applies"] = applies
    r.update({"comparison": comparison, "severity": severity, "phrasing": phrasing})
    if measured:
        r["measured"] = measured
    if not evaluate:
        r["evaluate"] = False
    r.update(extra)
    if note:
        r["note"] = note
    if quote_kind == "repo_file":
        r.update({"source_url": REPO_FILES[page], "source_kind": "repository file"})
    else:
        r["source_url"] = URL[page]
    r.update({"quote": quote, "quote_kind": quote_kind, "retrieved": DATE})
    if cells and quote_kind == "table_row":
        r["cells"] = cells
    assert r["id"] not in RULES, r["id"]
    RULES[r["id"]] = r
    return r


def info(supplier, rid, process, page, quote, rule="info", **kw):
    kw.setdefault("comparison", "info")
    kw.setdefault("severity", "info")
    kw.setdefault("phrasing", "statement")
    return add(supplier, rid, process=process, rule=rule, page=page, quote=quote, **kw)


CNC, FDM, SLS, MJF, SLA = "cnc_milling", "fdm", "sls", "mjf", "sla"
NOT_TEXT = "Engraved and embossed text is not extracted from the model (gap)."
NOT_CLEAR = "Clearance between separately printed or assembled parts is a property of the assembly, not of one part (see the interference verifier); not judged here."

# ============================================================================================ Xometry
XO = "xometry"
add(XO, "cnc.corner_ld_ratio", process=CNC, rule="cnc_corner_ld_ratio", page="xo_costred",
    quote="For optimum design, use an inside corner radius that has a L:D ratio (length to diameter) of 3:1 or less.",
    value=3.0, unit="corner depth / (2 x corner radius)", comparison="<=", severity="warning", phrasing="recommendation (cost)",
    measured="depth of each vertical inside corner over the diameter of the cutter that forms it (2 x its radius); a sharp corner counts as infinite")
add(XO, "cnc.wall_min_metal", process=CNC, rule="cnc_wall_min", page="xo_thin", material="metal",
    quote="As a general rule of thumb, CNC machined walls should have a minimum width of 1/32” (0.794mm).",
    value_mm=0.794, severity="warning", phrasing="rule of thumb", measured="thinnest wall (two near-parallel faces, ray across the material)")
add(XO, "cnc.thread_depth_ratio", process=CNC, rule="cnc_thread_depth_ratio_max", page="xo_costred",
    quote="As a result, you don’t need to thread a hole to more than 3X the hole’s diameter (and keep it shorter, if possible).",
    value=3.0, unit="x thread diameter", comparison="<=", severity="warning", phrasing="recommendation (cost)")
add(XO, "cnc.thread_hand_tap", process=CNC, rule="cnc_thread_min", page="xo_costred",
    quote="Anything smaller than a 2-56″ requires hand tapping, which adds significant time and risk to the process.",
    value_mm=round(0.086 * IN, 3), value_as_published="2-56 (0.086 in major diameter)", severity="warning", phrasing="cost and risk",
    note="2-56 is a UNC size of 0.086 in (2.18 mm) major diameter; metric threads are compared by nominal diameter.")
add(XO, "cnc.corner_radius_margin", process=CNC, rule="cnc_corner_radius_margin", page="xo_corner",
    quote="As a best practice, we recommend modeling your design with at least 0.02″ – 0.05″ added to internal corner radii, or in this example, a dimension of 0.27″ – 0.30″.",
    value_mm=[0.508, 1.27], comparison="info", severity="info", phrasing="best practice", evaluate=False,
    note="Relative to the end mill's radius, which a model does not state; kept for reference.")
add(XO, "cnc.cavity_depth", process=CNC, rule="cnc_cavity_length_depth", page="xo_costred",
    quote="As a best practice, we suggest parts with lengths up to 4X their depth. Anything greater than that becomes exponentially more expensive to manufacture.",
    value=4.0, comparison="info", severity="info", phrasing="best practice (wording ambiguous)", evaluate=False,
    note="Under 'deep internal cavities'; the sentence does not say which length is compared with which depth, so it is not judged.")
add(XO, "cnc.machine_3axis", process=CNC, rule="cnc_part_max_size", page="xo_cnc", quote="‣ 3 Axis Machining up to 60″",
    value_mm=[1524.0], severity="warning", phrasing="general guideline for machine size",
    measured="longest side of the part", note="Published as 'some guidelines for machine size'; a part over it goes to a manual quote review.")
info(XO, "cnc.surface_finish", CNC, "xo_cnc", "The standard finish is as-machined: 125 Ra or better.", rule="surface_finish", value=125, unit="uin Ra")
info(XO, "cnc.edges", CNC, "xo_cnc", "Sharp edges are broken and deburred by default", rule="edge_condition")
info(XO, "cnc.tolerance_plastics", CNC, "xo_cnc", "Plastics and composites will be +/- 0.010”.", rule="tolerance", value_mm=0.254, material="plastic")
# ---- 3D printing
add(XO, "fdm.wall_min_16in", process=FDM, rule="p3d_wall_min", page="xo_fdm", 
    quote="Minimum Wall Thickness | Description 0.047\"(less than 16\"), 0.060\" (greater than 16\")",
    value_mm=round(0.047 * IN, 3), applies={"part_max_mm_le": 406.4}, severity="error", phrasing="published minimum",
    note="Industrial (Stratasys Fortus) FDM. The same page says desktop FFF prints in PLA 'failing at walls thinner than 0.5 mm'.")
add(XO, "fdm.wall_min_over16in", process=FDM, rule="p3d_wall_min", page="xo_fdm", 
    quote="Minimum Wall Thickness | Description 0.047\"(less than 16\"), 0.060\" (greater than 16\")",
    value_mm=round(0.060 * IN, 3), applies={"part_max_mm_gt": 406.4}, severity="error", phrasing="published minimum")
add(XO, "fdm.desktop_observed", process=FDM, rule="p3d_wall_min", page="xo_fdm", material="pla",
    quote="This desktop 3D printed FFF model in blue PLA overall had better feature resolution, failing at walls thinner than 0.5 mm, pegs to 0.75 mm, and text below 5 mm.",
    value_mm=0.5, severity="error", phrasing="observed failure on a test print", measured="thinnest wall")
add(XO, "fdm.feature_min", process=FDM, rule="p3d_feature_min", page="xo_std",
    quote="Positive features, such as raised text below .040\" in size may not fully resolve or become extremely fragile.",
    value_mm=round(0.040 * IN, 3), severity="warning", phrasing="may not resolve", measured="smallest pin or boss diameter")
add(XO, "fdm.hole_oblong", process=FDM, rule="p3d_hole_min", page="xo_std",
    quote="Holes smaller than .040\", horizontal holes, and protrusions will build slightly oblong due to stair-stepping from layers.",
    value_mm=round(0.040 * IN, 3), severity="warning", phrasing="statement (accuracy)")
add(XO, "fdm.build_size", process=FDM, rule="p3d_part_max_size", page="xo_fdm", quote="Build Size | Description Up to 24\" x 36\" x 36\"", value_mm=[609.6, 914.4, 914.4], comparison="<=", severity="error",
    phrasing="capability")
add(XO, "fdm.pla_petg_max", process=FDM, rule="p3d_part_max_size", page="xo_pla_petg", material="pla|petg", quote="Max Part Size 10\"x10\"x10\" (256 x 256 x 256 mm)",
    value_mm=[256.0, 256.0, 256.0], comparison="<=", severity="error", phrasing="capability")
add(XO, "fdm.threads", process=FDM, rule="p3d_thread_in_print", page="xo_std",
    quote="Modeled threads or precision features may have limited functionality as printed. Tapping or the addition of threaded inserts is recommended for best function.",
    value=0, unit="threads in the print", comparison="<=", severity="warning", phrasing="recommendation")
info(XO, "fdm.tolerance", FDM, "xo_std", "+/- a single build layer thickness for the first inch and +/- .002” for every inch thereafter.", rule="tolerance")
info(XO, "fdm.layer_desktop", FDM, "xo_std", ".008\" layer thickness used for Desktop FDM/FFF platforms (e.g., Prusa MK3S/MK4 or Bambu Lab X1C)", rule="layer_height", value_mm=0.203)
add(XO, "sls.feature_min", process=SLS, rule="p3d_feature_min", page="xo_std", quote="Positive features below .030\" in size may not fully resolve or become extremely fragile.",
    value_mm=0.762, severity="warning", phrasing="may not resolve", duplicate_page_note="the same sentence appears under HP MJF")
add(XO, "sls.hole_min", process=SLS, rule="p3d_hole_min", page="xo_std",
    quote="Standard-sized holes will be drilled out if accessible; holes smaller than .040\", irregular, or deep holes may shrink or sinter shut.",
    value_mm=1.016, severity="warning", phrasing="may sinter shut")
add(XO, "sls.build", process=SLS, rule="p3d_part_max_size", page="xo_sls", quote="Build Area | Tolerance Notes Non-formlabs materials: Up to 13\" x 13\" x 20\"", value_mm=[330.2, 330.2, 508.0], comparison="<=", severity="error",
    phrasing="capability")
add(XO, "sls.warp", process=SLS, rule="p3d_warp_size", page="xo_std",
    quote="Parts with thicker geometries, flat or broad parts (>7”), and parts with uneven wall thicknesses will be prone to significant deviations or warp due to variable thermal shrinkage and stress.",
    value_mm=177.8, comparison="<=", severity="warning", phrasing="statement (warp risk)", measured="longest side of the part")
add(XO, "mjf.feature_min", process=MJF, rule="p3d_feature_min", page="xo_mjf", quote="Minimum Feature Size | Tolerance Notes 0.020\" (0.040\" recommended) or greater.", value_mm=0.508, severity="error", phrasing="published minimum")
add(XO, "mjf.feature_rec", process=MJF, rule="p3d_feature_min", page="xo_mjf", quote="Minimum Feature Size | Tolerance Notes 0.020\" (0.040\" recommended) or greater.", value_mm=1.016, severity="warning", phrasing="recommended")
add(XO, "mjf.build", process=MJF, rule="p3d_part_max_size", page="xo_mjf", quote="Build Area | Tolerance Notes Build area up to 15 x 11 x 15\" (14 x 11 x 13\" is the recommended usable area).",
    value_mm=[279.4, 381.0, 381.0], comparison="<=", severity="error", phrasing="capability")
add(XO, "sla.feature_min_std", process=SLA, rule="p3d_feature_min", page="xo_sla", quote="Minimum linear feature size | Standard Resolution Under .030” are at risk, and under .020” will not build.",
    value_mm=0.508, severity="error", phrasing="will not build")
add(XO, "sla.feature_risk_std", process=SLA, rule="p3d_feature_min", page="xo_sla", quote="Minimum linear feature size | Standard Resolution Under .030” are at risk, and under .020” will not build.",
    value_mm=0.762, severity="warning", phrasing="at risk")

# ============================================================================================ Protolabs
PL = "protolabs"
add(PL, "cnc.sharp_inside_corners", process=CNC, rule="cnc_corner_sharp", page="pl_cnc_mill_dg",
    quote="Sharp inside corners on a part will be radiused (rounded) as a natural result of the CNC machining process. Resulting radii will be the minimum allowable tool radius.",
    value=0, unit="sharp vertical inside corners", comparison="<=", severity="warning", phrasing="statement: the corner is made with a radius",
    measured="vertical inside corners modelled with no radius")
add(PL, "cnc.mill_depth_each_side", process=CNC, rule="cnc_mill_depth_max", page="pl_cnc_mill_dg",
    quote="Maximum depth for factory machined parts that can be milled is 2 in. (50.8mm) from either side of the part.",
    value_mm=50.8, comparison="<=", severity="error", phrasing="requirement", measured="deepest milled floor or pocket below the face it is cut from",
    note="Evaluated here; the same rule in mechloop/data/supplier_rules/protolabs.json (protolabs.cnc.mill_depth_max) is kept there as not evaluated.")
add(PL, "cnc.models_no_internal_threads", process=CNC, rule="cnc_threads_modelled", page="pl_cnc_mill_dg", quote="Avoid modeling internal threads on your part design.",
    value=0, unit="modelled helical threads", comparison="<=", severity="warning", phrasing="recommendation", evaluate=False,
    note="Helical thread geometry is not recognised in the B-rep (gap); threads are taken from the design's callouts.")
for size, lo, hi, depth in (("M2 x 0.4", "1.57", "1.68", "5.08"), ("M2.5 x 0.45", "2.01", "2.14", "5.08"), ("M3 x 0.5", "2.46", "2.60", "7.62"),
                            ("M3.5 x 0.6", "2.85", "3.01", "10.16"), ("M4 x 0.7", "3.24", "3.42", "10.16"), ("M5 x 0.8", "4.14", "4.33", "15.24"),
                            ("M6 x 1.0", "4.92", "5.15", "16.51"), ("M8 x 1.25", "6.65", "6.91", "16.51"), ("M10 x 1.5", "8.38", "8.68", "25.40"),
                            ("M12 x 1.75", "10.00", "10.44", "25.40")):
    d = float(size.split()[0][1:])
    key = size.split()[0].lower()
    q = f"Metric threads | {size} | Minimum modeled diameter (mm) {lo} | Maximum modeled diameter (mm) {hi} | Maximum thread depth (mm)* {depth}"
    add(PL, f"cnc.thread_{key}_modelled_d", process=CNC, rule="cnc_thread_modeled_d", page="pl_cnc_threads_std", quote_kind="table_row",
        cells=[size, lo, hi, depth], quote=q, value_mm=[float(lo), float(hi)], comparison="within", applies={"thread_d": d}, severity="error",
        phrasing="automated-factory requirement", measured="diameter of the modelled hole the thread is called out on")
    add(PL, f"cnc.thread_{key}_depth_max", process=CNC, rule="cnc_thread_depth_max", page="pl_cnc_threads_std", quote_kind="table_row",
        cells=[size, lo, hi, depth], quote=q, value_mm=float(depth), comparison="<=", applies={"thread_d": d}, severity="error",
        phrasing="automated-factory requirement", note="*Obstruction by other features of your part, lead-in treatments, or fixturing requirements may reduce the maximum depth of threads.")
for rng, al in (("Over 0.236 in. (6mm) up to 1.18 in. (30mm)", "±0.004 in. (±0.10 mm)"), ("Over 1.18 in. (30mm) up to 4.72 in. (120mm)", "±0.006 in.(±0.15 mm)")):
    add(PL, "cnc.tol_" + rng.split("(")[1].split(")")[0].replace(" ", ""), process=CNC, rule="tolerance", page="pl_cnc_tol", quote_kind="table_row",
        cells=[rng, al], quote=f"Permissible deviations ranges in nominal lengths | {rng} | Aluminum F (fine) {al}", comparison="info", severity="info",
        phrasing="ISO 2768 fine", material="al*")
add(PL, "fdm.walls", process=FDM, rule="p3d_wall_min", page="pl_fdm", quote_kind="table_row", cells=["Unsupported/Supported Walls", "Minimum 0.8mm"],
    quote="Unsupported/Supported Walls | Minimum 0.0315 in. | Minimum 0.8mm", value_mm=0.8, severity="error", phrasing="published minimum")
add(PL, "fdm.walls_unsupported", process=FDM, rule="p3d_wall_min_unsupported", page="pl_fdm", quote_kind="table_row", cells=["Unsupported/Supported Walls", "Minimum 0.8mm"],
    quote="Unsupported/Supported Walls | Minimum 0.0315 in. | Minimum 0.8mm", value_mm=0.8, severity="error", phrasing="published minimum", duplicate_of="protolabs.fdm.walls")
add(PL, "fdm.feature_min", process=FDM, rule="p3d_feature_min", page="pl_fdm", quote_kind="table_row", cells=["Minimum Feature Size", "2.0mm"],
    quote="Minimum Feature Size | 0.0787 in. | 2.0mm", value_mm=2.0, severity="error", phrasing="published minimum", measured="smallest pin or boss diameter")
add(PL, "fdm.hole_min", process=FDM, rule="p3d_hole_min", page="pl_fdm", quote_kind="table_row", cells=["Minimum Hole Diameter", "2.0mm"],
    quote="Minimum Hole Diameter | 0.0787 in. | 2.0mm", value_mm=2.0, severity="error", phrasing="published minimum")
add(PL, "fdm.max_size", process=FDM, rule="p3d_part_max_size", page="pl_fdm", quote_kind="table_row",
    cells=["Max Part Size", "Prototyping FDM", "Up to 500mm x 500mm x 500mm"], quote="Max Part Size | Prototyping FDM | Up to 500mm x 500mm x 500mm",
    value_mm=[500.0, 500.0, 500.0], comparison="<=", severity="error", phrasing="capability")
info(PL, "fdm.accuracy", FDM, "pl_fdm", "", quote_kind="table_row", cells=["Dimensional Accuracy", "Prototyping FDM", "± 0.5% with a lower limit of ±0.020 in."],
     rule="tolerance")
RULES["protolabs.fdm.accuracy"]["quote"] = "Dimensional Accuracy | Prototyping FDM | ± 0.5% with a lower limit of ±0.020 in. | 0.5mm"
info(PL, "fdm.layers", FDM, "pl_fdm", "Layer Height Options | from 100-300 μm", quote_kind="table_row", cells=["Layer Height Options", "from 100-300 μm"], rule="layer_height")
add(PL, "p3d.small_gap", process=FDM, rule="p3d_clearance_assembly", page="pl_thin",
    quote="This indicates that the distance between each of the spur gear’s teeth is less than the recommended 0.03 in. (0.75mm), and that, depending on the 3D printing process, raw material, part geometry and orientation, the customer can expect partial or even complete fusing between some or all of the teeth.",
    value_mm=0.75, severity="warning", phrasing="recommended gap", evaluate=False, note=NOT_CLEAR + " Stated for 3D printing in general.")
add(PL, "sls.wall_min", process=SLS, rule="p3d_wall_min", page="pl_sls", quote_kind="table_row", cells=["Minimum Wall Thickness", "0.762mm"],
    quote="Minimum Wall Thickness | 0.030 in. | 0.762mm", value_mm=0.762, severity="error", phrasing="published minimum")
add(PL, "sls.feature_nylon", process=SLS, rule="p3d_feature_min", page="pl_sls", quote_kind="table_row", cells=["Nylons", "0.762mm"],
    quote="Minimum feature size | Nylons | 0.03 in. | 0.762mm", value_mm=0.762, severity="error", material="nylon*", phrasing="published minimum")
add(PL, "sls.max_size", process=SLS, rule="p3d_part_max_size", page="pl_sls", quote_kind="table_row",
    cells=["Nylon, TPU, and other PA12 Materials", "309.88mm x 261.62mm x 254mm"], quote="Nylon, TPU, and other PA12 Materials | 12.2 in. x 10.3 in. x 10 in. | 309.88mm x 261.62mm x 254mm",
    value_mm=[254.0, 261.62, 309.88], comparison="<=", severity="error", phrasing="capability")
add(PL, "sls.warp", process=SLS, rule="p3d_warp_thickness", page="pl_sls",
    quote="Larger part sizes (>7 in.) and parts with thin features are the most susceptible to warp. We recommend maintaining a uniform thickness of 0.125 in. (3.175mm) to ensure stability.",
    value_mm=3.175, applies={"part_max_mm_gt": 177.8}, severity="warning", phrasing="recommendation", measured="thinnest wall of a part longer than 7 in.")
add(PL, "mjf.wall_min", process=MJF, rule="p3d_wall_min", page="pl_mjf", quote_kind="table_row", cells=["Wall Thickness", "0.5mm"],
    quote="Wall Thickness | 0.020 in. | 0.5mm", value_mm=0.5, severity="error", phrasing="published minimum")
add(PL, "mjf.feature_min", process=MJF, rule="p3d_feature_min", page="pl_mjf", quote_kind="table_row", cells=["Minimum Feature Size", "0.5mm"],
    quote="Minimum Feature Size | 0.020 in. | 0.5mm", value_mm=0.5, severity="error", phrasing="published minimum")
add(PL, "mjf.max_size", process=MJF, rule="p3d_part_max_size", page="pl_mjf", quote_kind="table_row", cells=["Maximum Part Size", "284mm x 380mm x 380mm"],
    quote="Maximum Part Size | 11.1 in. x 14.9 in. x 14.9 in | 284mm x 380mm x 380mm", value_mm=[284.0, 380.0, 380.0], comparison="<=", severity="error", phrasing="capability")
add(PL, "mjf.warp", process=MJF, rule="p3d_warp_thickness", page="pl_mjf",
    quote="Warpage: Larger part sizes (>7 in.) and parts with thin features are the most susceptible to warp. We recommend maintaining a uniform thickness of 0.125 in. (3.175mm) to ensure stability.",
    value_mm=3.175, applies={"part_max_mm_gt": 177.8}, severity="warning", phrasing="recommendation", measured="thinnest wall of a part longer than 7 in.")
add(PL, "sla.wall_normal", process=SLA, rule="p3d_wall_min", page="pl_sla", quote_kind="table_row", cells=["Minimum wall thickness", "0.010 in. (0.254mm)"],
    quote="Minimum wall thickness | Normal Resolution: 0.010 in. (0.254mm)", value_mm=0.254, severity="error", phrasing="published minimum (normal resolution)")
add(PL, "sla.hole_normal", process=SLA, rule="p3d_hole_min", page="pl_sla", quote_kind="table_row", cells=["Minimum hole size", "0.025 in. (0.635mm)"],
    quote="Minimum hole size | Normal Resolution: 0.025 in. (0.635mm)", value_mm=0.635, severity="error", phrasing="published minimum (normal resolution)")
add(PL, "sla.max_normal", process=SLA, rule="p3d_part_max_size", page="pl_sla", quote_kind="table_row", cells=["Maximum part size", "29 × 25 × 21 in.* (736 × 635 × 533mm*)"],
    quote="Maximum part size | Normal Resolution: 29 × 25 × 21 in.* (736 × 635 × 533mm*)", value_mm=[533.0, 635.0, 736.0], comparison="<=", severity="error", phrasing="capability")
info(PL, "sls.tolerance", SLS, "pl_sls", "For well-designed parts, tolerances of ±0.010 in. (0.25mm) plus 0.1% of nominal length can typically be achieved.", rule="tolerance",
     conflicts_note="The 3D-printing tolerances design tip gives SLS as ±0.010 in. (±0.3048mm) plus ±0.0015 in. per additional inch.")
info(PL, "sls.tolerance_tip", SLS, "pl_3dp_tol", "SLS: Tolerances of ±0.010 in. (±0.3048mm) plus ±0.0015 in. (0.0381mm) for each additional inch can typically be achieved (excludes TPU)",
     rule="tolerance", conflicts=["protolabs.sls.tolerance"], note="0.010 in. is 0.254 mm, not 0.3048 mm: the page's own conversion is inconsistent.")

# ============================================================================================ Hubs (Protolabs Network)
HU = "hubs"
add(HU, "cnc.corner_radius_depth", process=CNC, rule="cnc_corner_radius_depth", page="hubs_cnc_design",
    quote="Vertical corner radius Recommended: ⅓ times cavity depth (or larger)", formula={"d": 1 / 3}, severity="warning", phrasing="recommended",
    measured="radius of each vertical inside corner against its depth")
add(HU, "cnc.corner_radius_depth_rule_of_thumb", process=CNC, rule="cnc_corner_radius_depth", page="hubs_sharp",
    quote="As a rule of thumb, specify corner radii at least one third of the cavity depth.", formula={"d": 1 / 3}, severity="warning", phrasing="rule of thumb",
    duplicate_of="hubs.cnc.corner_radius_depth")
add(HU, "cnc.cavity_depth_width", process=CNC, rule="cnc_pocket_depth_width", page="hubs_cnc_design", quote="Recommended cavity depth: 4 times cavity width",
    value=4.0, unit="x cavity width", comparison="<=", severity="warning", phrasing="recommended", measured="pocket or slot depth over its width")
add(HU, "cnc.cavity_depth_tool_sharp_page", process=CNC, rule="cnc_pocket_depth_tool", page="hubs_sharp", quote="Keep cavity depth to two to three times the cutter diameter.",
    value=3.0, unit="x cutter diameter", comparison="<=", severity="warning", phrasing="rule of thumb (upper end of 2-3x used)",
    conflicts=["hubs.cnc.cavity_depth_width", "fictiv.cnc.pocket_depth_tool"], note="Hubs' design guide allows 4 x the cavity width; this page 2-3 x the cutter diameter.")
add(HU, "cnc.deep_cavity_limit", process=CNC, rule="cnc_pocket_depth_tool", page="hubs_cnc_design",
    quote="A tool diameter-to-cavity depth ratio of up to 30:1 is possible using specialized tooling (maximum depth: 35 cm with a 1-inch diameter end mill tool).",
    value=30.0, unit="x cutter diameter", comparison="<=", severity="error", phrasing="limit of specialised tooling")
add(HU, "cnc.wall_rec_metal", process=CNC, rule="cnc_wall_min", page="hubs_cnc_design", material="metal",
    quote="Minimum wall thickness Recommended: 0.8 mm (metals), 1.5 mm (plastics) Feasible: 0.5 mm (metals), 1.0 mm (plastics)", value_mm=0.8, severity="warning", phrasing="recommended")
add(HU, "cnc.wall_feasible_metal", process=CNC, rule="cnc_wall_min", page="hubs_cnc_design", material="metal",
    quote="Minimum wall thickness Recommended: 0.8 mm (metals), 1.5 mm (plastics) Feasible: 0.5 mm (metals), 1.0 mm (plastics)", value_mm=0.5, severity="error", phrasing="feasible limit")
add(HU, "cnc.wall_rec_plastic", process=CNC, rule="cnc_wall_min", page="hubs_cnc_design", material="plastic",
    quote="Minimum wall thickness Recommended: 0.8 mm (metals), 1.5 mm (plastics) Feasible: 0.5 mm (metals), 1.0 mm (plastics)", value_mm=1.5, severity="warning", phrasing="recommended")
add(HU, "cnc.wall_feasible_plastic", process=CNC, rule="cnc_wall_min", page="hubs_cnc_design", material="plastic",
    quote="Minimum wall thickness Recommended: 0.8 mm (metals), 1.5 mm (plastics) Feasible: 0.5 mm (metals), 1.0 mm (plastics)", value_mm=1.0, severity="error", phrasing="feasible limit")
add(HU, "cnc.hole_feasible", process=CNC, rule="cnc_hole_min", page="hubs_cnc_design", quote="Diameter Recommended: standard drill bit Feasible: any diameter larger than 1 mm",
    value_mm=1.0, severity="error", phrasing="feasible limit", conflicts=["hubs.cnc.small_features_feasible"])
add(HU, "cnc.hole_standard_drill", process=CNC, rule="cnc_hole_standard_drill", page="hubs_cnc_design",
    quote="For high-accuracy holes with a diameter smaller than 20 mm, using a standard diameter is recommended.", value_mm=20.0, comparison="in_list",
    severity="warning", phrasing="recommended", standard_list_rule="hubs.cnc.metric_drills", measured="hole diameter against Hubs' metric drill table (0.01 mm)")
DRILLS = [float(r[0].split()[0]) for r in table_rows("hubs_drills") if r and r[0].endswith(" mm") and len(r) == 2]
add(HU, "cnc.metric_drills", process=CNC, rule="standard_drills", page="hubs_drills", quote_kind="table_row", cells=["0.05 mm", "0.0020"],
    quote="Standard drill bit sizes, metric | Drill size | Diameter (in): 0.05 mm ... 38 mm", value_mm=DRILLS, comparison="info", severity="info", phrasing="reference table")
add(HU, "cnc.small_features_rec", process=CNC, rule="cnc_slot_min", page="hubs_cnc_design", quote="Minimum hole diameter Recommended: 2.5 mm (0.1 inches.'') Feasible: 0.05 mm (0.005 inches.'')",
    value_mm=2.5, severity="warning", phrasing="recommended (smallest standard cutter)", measured="narrowest pocket or slot (the largest cutter that fits)")
add(HU, "cnc.small_features_feasible", process=CNC, rule="cnc_hole_min", page="hubs_cnc_design", quote="Minimum hole diameter Recommended: 2.5 mm (0.1 inches.'') Feasible: 0.05 mm (0.005 inches.'')",
    value_mm=0.05, severity="error", phrasing="feasible (micro-machining)", conflicts=["hubs.cnc.hole_feasible"],
    note="The same page gives 'any diameter larger than 1 mm' as feasible for holes.")
add(HU, "cnc.hole_depth_rec", process=CNC, rule="cnc_hole_depth_ratio", page="hubs_cnc_design", quote="Maximum depth Recommended: 4 times nominal diameter Typical: 10 times nominal diameter Feasible: 40 times nominal diameter",
    value=4.0, unit="x diameter", comparison="<=", severity="warning", phrasing="recommended")
add(HU, "cnc.hole_depth_feasible", process=CNC, rule="cnc_hole_depth_ratio", page="hubs_cnc_design", quote="Maximum depth Recommended: 4 times nominal diameter Typical: 10 times nominal diameter Feasible: 40 times nominal diameter",
    value=40.0, unit="x diameter", comparison="<=", severity="error", phrasing="feasible limit")
add(HU, "cnc.thread_size_rec", process=CNC, rule="cnc_thread_min", page="hubs_cnc_design", quote="Thread size Minimum: M1 (and lower, in some cases) Recommended: M6 or larger",
    value_mm=6.0, severity="warning", phrasing="recommended")
add(HU, "cnc.thread_taps_m2", process=CNC, rule="cnc_thread_min", page="hubs_cnc_design", quote="Taps and dies can be used to cut threads down to M2.",
    value_mm=2.0, severity="error", phrasing="capability of taps")
add(HU, "cnc.thread_length_min", process=CNC, rule="cnc_thread_depth_ratio_min", page="hubs_cnc_design",
    quote="Thread length Minimum: 1.5 times nominal diameter Recommended: 3 times nominal diameter", value=1.5, unit="x thread diameter", severity="warning", phrasing="minimum")
add(HU, "cnc.thread_length_max", process=CNC, rule="cnc_thread_depth_ratio_max", page="hubs_cnc_design",
    quote="Threads longer than 3 times the nominal diameter are thus unnecessary.", value=3.0, unit="x thread diameter", comparison="<=", severity="warning", phrasing="unnecessary beyond")
add(HU, "cnc.blind_tap_runout", process=CNC, rule="cnc_blind_tap_runout", page="hubs_cnc_design",
    quote="For threads in blind holes cut with taps (i.e. all threads smaller than M6), add an unthreaded length equal to 1.5 times the nominal diameter at the bottom of the hole.",
    formula={"d": 1.5}, applies={"thread_d_lt": 6.0}, severity="warning", phrasing="recommendation", conflicts=["jlccnc.cnc.blind_tap_runout"],
    measured="plain hole below the thread of a blind tapped hole, against the thread diameter")
add(HU, "cnc.setups", process=CNC, rule="cnc_setups_max", page="hubs_cnc_design",
    quote="This is often acceptable if the part needs to be rotated up to three or four times, but anything above this limit is excessive.",
    value=4, unit="set-ups (principal directions)", comparison="<=", severity="warning", phrasing="excessive beyond")
add(HU, "cnc.align_features", process=CNC, rule="cnc_off_axis_features", page="hubs_cnc_design",
    quote="We recommend aligning all your model’s features (holes, cavities, vertical walls, etc.) to one of the six principal directions.",
    value=0, unit="faces reachable from no principal direction", comparison="<=", severity="warning", phrasing="recommendation")
add(HU, "cnc.part_max_soft", process=CNC, rule="cnc_part_max_size", page="hubs_cnc_service", quote_kind="table_row", material="al*|brass",
    cells=["3-axis CNC milling (soft metals)", "2000 × 1500 × 200 mm"], quote="Process | Maximum size (L × W × H): 3-axis CNC milling (soft metals) | 2000 × 1500 × 200 mm",
    value_mm=[200.0, 1500.0, 2000.0], comparison="<=", severity="error", phrasing="capability")
add(HU, "cnc.text", process=CNC, rule="cnc_text", page="hubs_cnc_design", quote="Recommended: font size 20 (or larger), 5 mm engraved", evaluate=False, note=NOT_TEXT)
add(HU, "cnc.floor_radius", process=CNC, rule="cnc_floor_radius", page="hubs_cnc_design", quote="Floor radius Recommended: 0.5 mm, 1 mm or no radius Feasible: any radius",
    evaluate=False, comparison="info", severity="info", note="Floor fillets are not extracted (gap).")
add(HU, "cnc.undercut_clearance", process=CNC, rule="cnc_undercut_clearance", page="hubs_cnc_design",
    quote="A good rule of thumb is to add space equal to at least four times the depth of the undercut between the machined wall and any other internal wall.",
    value=4.0, evaluate=False, note="Undercut depth is not measured (gap); undercut faces are reported as unreachable.")
info(HU, "cnc.tolerance_metals", CNC, "hubs_cnc_tol", "", quote_kind="table_row", cells=["Standard ISO class", "ISO 2768-f (fine)", "ISO 2768-m (medium)"], rule="tolerance")
RULES["hubs.cnc.tolerance_metals"]["quote"] = "Standard ISO class | Metals: ISO 2768-f (fine) | Plastics: ISO 2768-m (medium)"
# ---- 3D printing
add(HU, "fdm.walls_unsupported", process=FDM, rule="p3d_wall_min_unsupported", page="hubs_fdm_service", quote_kind="table_row", cells=["Unsupported walls", "0.8 mm (0.0315 in)"],
    quote="Feature | Recommended size: Unsupported walls | 0.8 mm (0.0315 in)", value_mm=0.8, severity="warning", phrasing="recommended size")
add(HU, "fdm.walls_supported", process=FDM, rule="p3d_wall_min", page="hubs_fdm_service", quote_kind="table_row", cells=["Supported walls", "0.8 mm (0.0315 in)"],
    quote="Feature | Recommended size: Supported walls | 0.8 mm (0.0315 in)", value_mm=0.8, severity="warning", phrasing="recommended size")
add(HU, "fdm.feature_min", process=FDM, rule="p3d_feature_min", page="hubs_fdm_service", quote_kind="table_row", cells=["Minimum feature size", "2.0 mm (0.0787 in)"],
    quote="Feature | Recommended size: Minimum feature size | 2.0 mm (0.0787 in)", value_mm=2.0, severity="warning", phrasing="recommended size", measured="smallest pin or boss diameter")
add(HU, "fdm.hole_min", process=FDM, rule="p3d_hole_min", page="hubs_fdm_service", quote_kind="table_row", cells=["Minimum hole diameter", "2.0 mm (0.0787 in)"],
    quote="Feature | Recommended size: Minimum hole diameter | 2.0 mm (0.0787 in)", value_mm=2.0, severity="warning", phrasing="recommended size")
add(HU, "fdm.overhang", process=FDM, rule="p3d_overhang_max_deg", page="hubs_fdm_design",
    quote="Depending on the material, an overhang can usually be printed up to 45° without compromising quality.", value=45.0, unit="deg from vertical", comparison="<=",
    severity="warning", phrasing="usually printable up to; support above", measured="area of down-facing surface steeper than the angle (from vertical), not on the bed")
add(HU, "fdm.bridge", process=FDM, rule="p3d_bridge_max", page="hubs_fdm_design",
    quote="Key design consideration: Due to the nature of FDM, sagging or marks from support material are to some extent always present unless the bridge is less than 5mm.",
    value_mm=5.0, comparison="<=", severity="info", phrasing="statement (surface quality)", measured="longest bridge span between two supports")
add(HU, "fdm.pin_small", process=FDM, rule="p3d_pin_min", page="hubs_fdm_design",
    quote="Key design consideration: If your design contains pins smaller than 5mm in diameter, add a small fillet at the base of the pin.",
    value_mm=5.0, severity="info", phrasing="advice (add a root fillet)", measured="smallest pin diameter")
add(HU, "fdm.build_desktop", process=FDM, rule="p3d_part_max_size", page="hubs_geom", quote_kind="table_row",
    cells=["FDM", "200 x 200 x 200 mm for desktop printers; Up to 900 x 600 x 900 mm for industrial printers"],
    quote="Typical build size | FDM | 200 x 200 x 200 mm for desktop printers; Up to 900 x 600 x 900 mm for industrial printers",
    value_mm=[200.0, 200.0, 200.0], comparison="<=", severity="info", phrasing="typical desktop build size")
add(HU, "fdm.build_service", process=FDM, rule="p3d_part_max_size", page="hubs_fdm_service", quote_kind="table_row",
    cells=["Prototyping FDM", "500 x 500 x 500 mm (19.68 in x 19.68 in x 19.68 in)"], quote="Prototyping FDM | Maximum build size 500 x 500 x 500 mm (19.68 in x 19.68 in x 19.68 in)",
    value_mm=[500.0, 500.0, 500.0], comparison="<=", severity="error", phrasing="capability")
info(HU, "fdm.accuracy", FDM, "hubs_fdm_service", "", quote_kind="table_row", cells=["Prototyping FDM", "± 0.5% with a lower limit on ± 0.5 mm (0.0196 in)"], rule="tolerance")
RULES["hubs.fdm.accuracy"]["quote"] = "Prototyping FDM | Dimensional accuracy ± 0.5% with a lower limit on ± 0.5 mm (0.0196 in)"
add(HU, "sls.walls_unsupported", process=SLS, rule="p3d_wall_min_unsupported", page="hubs_sls_service", quote_kind="table_row", cells=["Unsupported walls", "1.0 mm (0.040 in)"],
    quote="Feature | Recommended size: Unsupported walls | 1.0 mm (0.040 in)", value_mm=1.0, severity="warning")
add(HU, "sls.walls_supported", process=SLS, rule="p3d_wall_min", page="hubs_sls_service", quote_kind="table_row", cells=["Supported walls", "0.8 mm (0.031 in)"],
    quote="Feature | Recommended size: Supported walls | 0.8 mm (0.031 in)", value_mm=0.8, severity="warning")
add(HU, "sls.detail", process=SLS, rule="p3d_feature_min", page="hubs_sls_service", quote_kind="table_row", cells=["Minimum detail size", "0.8 mm (0.031 in)"],
    quote="Feature | Recommended size: Minimum detail size | 0.8 mm (0.031 in)", value_mm=0.8, severity="warning")
add(HU, "sls.hole_min", process=SLS, rule="p3d_hole_min", page="hubs_sls_service", quote_kind="table_row", cells=["Minimum hole size", "1.0 mm (0.040 in)"],
    quote="Feature | Recommended size: Minimum hole size | 1.0 mm (0.040 in)", value_mm=1.0, severity="warning", conflicts=["hubs.sls.hole_design_guide"])
add(HU, "sls.hole_design_guide", process=SLS, rule="p3d_hole_min", page="hubs_sls_design", quote="All holes should be larger than 1.5mm in diameter.", value_mm=1.5,
    severity="warning", conflicts=["hubs.sls.hole_min"], note="The SLS service page recommends 1.0 mm.")
add(HU, "sls.escape", process=SLS, rule="p3d_enclosed_void", page="hubs_sls_design",
    quote="To remove unsintered powder after production, it is necessary to include escape holes, which must be a minimum of 3.5mm in diameter.", value_mm=3.5,
    comparison="<=", severity="error", phrasing="requirement", measured="enclosed voids with no opening (each needs an escape hole)")
add(HU, "sls.clearance_moving", process=SLS, rule="p3d_clearance_moving", page="hubs_sls_service", quote_kind="table_row", cells=["Moving parts", "0.5 mm (0.020 in)"],
    quote="Feature | Recommended size: Moving parts | 0.5 mm (0.020 in)", value_mm=0.5, evaluate=False, note=NOT_CLEAR)
add(HU, "mjf.walls_range", process=MJF, rule="p3d_wall_min", page="hubs_mjf_design",
    quote="The walls of any part created with MJF should be between 2.5 mm (0.098 in) and 12.7 mm (0.5 in) thick.", value_mm=2.5, severity="warning",
    conflicts=["hubs.mjf.walls_table", "protolabs.mjf.wall_min"], note="Hubs' geometry-restrictions table recommends 0.5 mm for MJF; Protolabs 0.5 mm.")
add(HU, "mjf.walls_table", process=MJF, rule="p3d_wall_min", page="hubs_geom", quote_kind="table_row", cells=["MJF", "0.5 mm"],
    quote="3D printing process | Recommended Minimum Wall Thickness: MJF | 0.5 mm", value_mm=0.5, severity="warning", conflicts=["hubs.mjf.walls_range"])
add(HU, "mjf.clearance", process=MJF, rule="p3d_clearance_assembly", page="hubs_mjf_design",
    quote="If parts need to be assembled after printing, leave a minimum gap of 0.6 mm (0.024 in) between areas that will connect.", value_mm=0.6, evaluate=False, note=NOT_CLEAR)
add(HU, "sla.walls_supported", process=SLA, rule="p3d_wall_min", page="hubs_sla_design", quote_kind="table_row", cells=["Supported walls", "At least 0.4mm thick"],
    quote="Feature | Design specifications: Supported walls | At least 0.4mm thick", value_mm=0.4, severity="error", phrasing="at least")
add(HU, "sla.walls_unsupported", process=SLA, rule="p3d_wall_min_unsupported", page="hubs_sla_design", quote_kind="table_row", cells=["Unsupported walls", "At least 0.6mm thick"],
    quote="Feature | Design specifications: Unsupported walls | At least 0.6mm thick", value_mm=0.6, severity="error", phrasing="must be at least")
add(HU, "sla.overhang", process=SLA, rule="p3d_overhang_length_max", page="hubs_sla_design",
    quote="Printing without supports often leads to warping of the print, but if it is necessary to print without supports, any unsupported overhangs must be kept less than 1.0mm in length and at least 19° from level.",
    value_mm=1.0, comparison="<=", severity="warning", phrasing="only when printing without supports", measured="longest unsupported overhang (cantilever) length")
add(HU, "sla.drain", process=SLA, rule="p3d_enclosed_void", page="hubs_sla_design", quote="Drain holes should be at least 3.5mm in diameter", value_mm=3.5, comparison="<=", severity="error",
    measured="enclosed voids with no opening")
add(HU, "sla.holes", process=SLA, rule="p3d_hole_min", page="hubs_sla_design", quote="If their diameter is less than 0.8mm in the x-, y- and z-axes, holes may close off during printing.",
    value_mm=0.8, severity="warning", conflicts=["hubs.sla.holes_table"], note="The page's own table says 'Minimum diameter of 0.5mm'.")
add(HU, "sla.holes_table", process=SLA, rule="p3d_hole_min", page="hubs_sla_design", quote_kind="table_row", cells=["Holes", "Minimum diameter of 0.5mm"],
    quote="Feature | Design specifications: Holes | Minimum diameter of 0.5mm", value_mm=0.5, severity="error", conflicts=["hubs.sla.holes"])

# ============================================================================================ Fictiv
FI = "fictiv"
add(FI, "cnc.pocket_depth_tool", process=CNC, rule="cnc_pocket_depth_tool", page="fictiv_spec_cnc_earlier", quote="Avoid deep pockets and cavities (max depth = 4x tool diameter)",
    value=4.0, unit="x cutter diameter", comparison="<=", severity="warning", phrasing="avoid (cost)",
    note="Evaluated here: the cutter is taken as the largest that fits the pocket (its width, and twice its corner radius). The same rule in mechloop/data/supplier_rules/fictiv.json is kept as not evaluated.")
add(FI, "cnc.text", process=CNC, rule="cnc_text", page="fictiv_spec_cnc_earlier", quote="Avoid small text and logos (min 0.020″ depth, 0.030″ width)", evaluate=False, note=NOT_TEXT)
add(FI, "cnc.setups", process=CNC, rule="cnc_setups_max", page="fictiv_spec_cnc_earlier",
    quote="Consolidate features to one side when possible – reduces setups from 4-6 down to 2-3, saving 30-90 min per part", value=3, unit="set-ups", comparison="<=",
    severity="warning", phrasing="cost advice")
add(FI, "cnc.undercuts", process=CNC, rule="cnc_undercut", page="fictiv_spec_cnc_earlier",
    quote="Avoid undercuts requiring T-slot cutters or lollipop mills – these add 15-45 min programming + specialized tooling costs", value=0, unit="faces no straight cutter reaches",
    comparison="<=", severity="warning", phrasing="avoid (cost)")
info(FI, "cnc.tolerance", CNC, "fictiv_spec_cnc_earlier", "Standard tolerances (±0.005\" / ±0.127mm) are achievable with normal machining.", rule="tolerance", value_mm=0.127)

# ============================================================================================ JLCCNC / JLC3DP
JC = "jlccnc"
add(JC, "cnc.corner_radius_depth", process=CNC, rule="cnc_corner_radius_depth", page="jlccnc_dg",
    quote="Assuming the diameter of the cutting tool is D and the maximum depth of the internal cavity is H, with the minimum internal radius denoted as R, the formula is given as R=(H/10)+0.5 and D=H/5 (unit is in mm).",
    formula={"d": 0.1, "const_mm": 0.5}, severity="error", phrasing="the minimum internal radius that can be machined",
    note="In the absence of specific instructions, sharp internal corners will be machined according to this.")
add(JC, "cnc.corner_radius_min", process=CNC, rule="cnc_corner_radius_min", page="jlccnc_dg",
    quote="Currently, we can achieve a minimum internal radius of R 0.5 (mm) with a depth of ≤3 (mm).", value_mm=0.5, severity="error", phrasing="capability")
add(JC, "cnc.sharp_corners", process=CNC, rule="cnc_corner_sharp", page="jlccnc_dg",
    quote="In the absence of specific instructions, sharp internal corners will be machined according to the values shown in the below table based on the corner depth.",
    value=0, unit="sharp vertical inside corners", comparison="<=", severity="warning", phrasing="statement: the corner is made with a radius unless a drawing asks for EDM")
add(JC, "cnc.cavity_depth_tool", process=CNC, rule="cnc_pocket_depth_tool", page="jlccnc_dg",
    quote="Cutting deeper cavities (5 times or more the diameter of the tool) can cause problems such as tool deflection, difficulty in chip removal, and tool breakage, and therefore require special tools or multi-axis CNC systems.",
    value=5.0, unit="x cutter diameter", comparison="<", severity="warning", phrasing="needs special tools at or beyond")
add(JC, "cnc.cavity_depth_xy", process=CNC, rule="cnc_pocket_depth_xy", page="jlccnc_dg",
    quote="The cost can be minimized by limiting the depth of all cavities to five times their length (i.e. the maximum size on the XY plane).", value=5.0,
    unit="x largest pocket size in its plane", comparison="<=", severity="warning", phrasing="cost advice")
add(JC, "cnc.wall_rec_metal", process=CNC, rule="cnc_wall_min", page="jlccnc_dg", material="metal",
    quote="The recommended wall thickness of metal parts should be 0.8 mm (absolute minimum 0.5 mm), and 1.5 mm (absolute minimum 1 mm) for plastic parts.", value_mm=0.8, severity="warning")
add(JC, "cnc.wall_abs_metal", process=CNC, rule="cnc_wall_min", page="jlccnc_dg", material="metal",
    quote="The recommended wall thickness of metal parts should be 0.8 mm (absolute minimum 0.5 mm), and 1.5 mm (absolute minimum 1 mm) for plastic parts.", value_mm=0.5, severity="error",
    phrasing="absolute minimum")
add(JC, "cnc.wall_rec_plastic", process=CNC, rule="cnc_wall_min", page="jlccnc_dg", material="plastic",
    quote="The recommended wall thickness of metal parts should be 0.8 mm (absolute minimum 0.5 mm), and 1.5 mm (absolute minimum 1 mm) for plastic parts.", value_mm=1.5, severity="warning")
add(JC, "cnc.wall_abs_plastic", process=CNC, rule="cnc_wall_min", page="jlccnc_dg", material="plastic",
    quote="The recommended wall thickness of metal parts should be 0.8 mm (absolute minimum 0.5 mm), and 1.5 mm (absolute minimum 1 mm) for plastic parts.", value_mm=1.0, severity="error",
    phrasing="absolute minimum")
add(JC, "cnc.thread_length", process=CNC, rule="cnc_thread_depth_ratio_max", page="jlccnc_dg", quote="The thread length is recommended not to exceed three times of the hole diameter.",
    value=3.0, unit="x thread diameter", comparison="<=", severity="warning")
add(JC, "cnc.blind_tap_runout", process=CNC, rule="cnc_blind_tap_runout", page="jlccnc_dg",
    quote="When the threaded hole is a blind hole, it is recommended to leave an unthreaded length of at least half the hole diameter at the end of the hole.",
    formula={"d": 0.5}, severity="warning", conflicts=["hubs.cnc.blind_tap_runout"], note="Hubs asks for 1.5 x the nominal diameter (threads under M6).")
add(JC, "cnc.tap_drill_m3", process=CNC, rule="cnc_thread_modeled_d", page="jlccnc_dg",
    quote="For example, the standard diameter of the base hole for M3×0.5 is ⌀ 2.5 (see figure below). In the programming, we drill directly according to the ⌀ 2.5 base hole diameter, then use an automatic tapping machine to tap the thread. If the base hole is drawn as ⌀ 3, it will be too large for thread tapping (some can be remedied with thread inserts).",
    value_mm=[2.45, 2.55], comparison="within", applies={"thread_d": 3.0}, value_as_published="⌀ 2.5 (accepted within 0.05 mm)", severity="warning", phrasing="draw the base (tap-drill) hole",
    conflicts=["sendcutsend.cnc.tap_hole_major"])
info(JC, "cnc.tolerance", CNC, "jlccnc_dg", "If no tolerance is provided, parts will be made with standard tolerance (±0.1mm or higher).", rule="tolerance", value_mm=0.1)
J3 = "jlc3dp"
for band, val in (("50x50mm", "1.6mm"), ("100x100mm", "2.0mm"), ("200x200mm", "2.5mm")):
    b = float(band.split("x")[0])
    add(J3, f"fdm.wall_size_{int(b)}", process=FDM, rule="p3d_wall_min_size_band", page="jlc3dp_dg", quote_kind="table_row", cells=["Plastic (FDM)", "1.6mm", "2.0mm", "2.5mm"],
        quote=f"Wall thickness by model size | Materials/Range: Plastic (FDM) | {band}: {val}", value_mm=float(val[:-2]), applies={"size_band_mm": b},
        severity="warning", phrasing="recommended minimum for the model size",
        note="Bands are the table's model sizes (5x5 ... 200x200 mm); a part is put in the smallest band whose square holds its two largest sides (interpretation); FDM has no value below 50x50 mm.")
add(J3, "fdm.structural_wall", process=FDM, rule="p3d_wall_min", page="jlc3dp_dg",
    quote="The recommended minimum wall thickness for structures such as protrusion, positioning, snaps and fasteners is more than 1.5mm.", value_mm=1.5,
    severity="warning", phrasing="recommended for protrusions, snaps and fasteners", applies={"feature": "structural"}, evaluate=False,
    note="Which walls are snaps or fasteners is not known from the geometry.")
add(J3, "fdm.emboss", process=FDM, rule="p3d_emboss", page="jlc3dp_dg", quote="FDM (Plastic) : 1.0 mm deep & 1.0 mm wide", evaluate=False, note=NOT_TEXT)
add(J3, "fdm.thread_min", process=FDM, rule="p3d_thread_min", page="jlc3dp_dg", quote="The minimum recommended thread for printing is M6.", value_mm=6.0, severity="warning",
    measured="smallest thread called out in the print")
add(J3, "fdm.clearance_assembly", process=FDM, rule="p3d_clearance_assembly", page="jlc3dp_dg", quote_kind="table_row",
    cells=["Minimum Clearance", "0.2mm", "0.2mm-0.4mm", "0.2mm-0.4mm", "0.5mm", "0.5mm", "0.5mm"], quote="Clearance between parts that will be assembled together | Plastic (FDM) | 0.5mm",
    value_mm=0.5, evaluate=False, note=NOT_CLEAR)
add(J3, "fdm.clearance_moving", process=FDM, rule="p3d_clearance_moving", page="jlc3dp_dg", quote_kind="table_row",
    cells=["Minimum Clearance", "0.5mm", "0.6mm", "0.6mm", "1.0mm", "1.0mm", "0.5mm"], quote="Clearance between moving parts | Plastic (FDM) | 0.5mm",
    value_mm=0.5, evaluate=False, note=NOT_CLEAR)
add(J3, "fdm.hole_min", process=FDM, rule="p3d_hole_min", page="jlc3dp_dg", quote_kind="table_row", cells=["Plastic (FDM)", "/", "h=1.5—4.5mm", "h=2.0—6.0mm"],
    quote="Aperture (Φ) and hole depth (h) | Plastic (FDM): Φ=1.0mm '/', Φ=1.5mm h=1.5—4.5mm, Φ=2.0mm h=2.0—6.0mm", value_mm=1.5, severity="warning",
    phrasing="smallest aperture listed for FDM")
for phi, hmax in ((1.5, 4.5), (2.0, 6.0)):
    add(J3, f"fdm.hole_depth_{phi:g}", process=FDM, rule="p3d_hole_depth_max", page="jlc3dp_dg", quote_kind="table_row", cells=["Plastic (FDM)", "/", "h=1.5—4.5mm", "h=2.0—6.0mm"],
        quote=f"Aperture (Φ) and hole depth (h) | Plastic (FDM): Φ={phi:g}mm h up to {hmax:g}mm", value_mm=hmax, comparison="<=", applies={"d_range": [phi, phi + 0.5]},
        severity="warning", phrasing="micro-hole depth guide", measured="depth of a hole of this listed aperture",
        note="Interpretation: the row is applied to holes from its aperture up to the next 0.5 mm step (the table lists 1.0, 1.5 and 2.0 mm).")
add(J3, "fdm.pin_min", process=FDM, rule="p3d_pin_min", page="jlc3dp_dg", quote_kind="table_row", cells=["Plastic (FDM)", "/", "H=2—4mm", "H=3—6mm"],
    quote="Column diameter (D) and column height (H) | Plastic (FDM): D=1.0mm '/', D=2.0mm H=2—4mm, D=3.0mm H=3—6mm", value_mm=2.0, severity="warning",
    phrasing="smallest column listed for FDM", measured="smallest pin diameter")
for dd, hmax in ((2.0, 4.0), (3.0, 6.0)):
    add(J3, f"fdm.pin_height_{dd:g}", process=FDM, rule="p3d_pin_height_max", page="jlc3dp_dg", quote_kind="table_row", cells=["Plastic (FDM)", "/", "H=2—4mm", "H=3—6mm"],
        quote=f"Column diameter (D) and column height (H) | Plastic (FDM): D={dd:g}mm H up to {hmax:g}mm", value_mm=hmax, comparison="<=", applies={"d_range": [dd, dd + 1.0]},
        severity="warning", phrasing="positioning-column guide",
        note="Interpretation: the row is applied to pins from its diameter up to the next listed diameter (1.0 mm steps).")
add(J3, "fdm.min_size", process=FDM, rule="p3d_part_min_size", page="jlc3dp_dg", quote_kind="table_row", cells=["FDM (Plastic)", "PLA-P (formerly PLA)", "250 × 250 × 300", "30 × 30 × 10"],
    quote="3D Technologies | FDM (Plastic) | PLA-P (formerly PLA) | Max. 250 × 250 × 300 | Min. 30 × 30 × 10", value_mm=[10.0, 30.0, 30.0], comparison=">=", severity="error",
    phrasing="minimum build size")
add(J3, "fdm.max_size_pla", process=FDM, rule="p3d_part_max_size", page="jlc3dp_dg", material="pla", quote_kind="table_row",
    cells=["FDM (Plastic)", "PLA-P (formerly PLA)", "250 × 250 × 300", "30 × 30 × 10"], quote="3D Technologies | FDM (Plastic) | PLA-P (formerly PLA) | Max. 250 × 250 × 300 | Min. 30 × 30 × 10",
    value_mm=[250.0, 250.0, 300.0], comparison="<=", severity="error", phrasing="capability")
add(J3, "p3d.hole_depth_ratio", process=FDM, rule="p3d_hole_depth_ratio", page="jlc3dp_cap_3dp", quote_kind="table_row", cells=["Depth-to–Diameter Ratio of Hole", "3:1"],
    quote="Design Factor | Recommended Value: Depth-to–Diameter Ratio of Hole | 3:1 | Prevent hole clogging and facilitate cleaning", value=3.0, unit="x diameter", comparison="<=",
    severity="warning", phrasing="recommended value (all processes)", applies_processes=[FDM, SLS, MJF, SLA])
info(J3, "fdm.tolerance", FDM, "jlc3dp_dg", "Plastic (FDM) : ±0.3mm (Within 100mm), ±0.4% (Above 100mm)", rule="tolerance")
info(J3, "fdm.hole_tolerance", FDM, "jlc3dp_dg", "Plastic (FDM) : ±0.4mm", rule="tolerance_hole")
add(J3, "sls.escape", process=SLS, rule="p3d_enclosed_void", page="jlc3dp_dg", quote="(1) The minimum escape hole diameter is 2.5mm.", value_mm=2.5, comparison="<=", severity="error",
    measured="enclosed voids with no opening")
add(J3, "sls.wall_size_50", process=SLS, rule="p3d_wall_min_size_band", page="jlc3dp_dg", quote_kind="table_row", cells=["Nylon (SLS)", "1.0mm", "1.2mm", "1.5mm", "2.0mm", "2.0mm"],
    quote="Wall thickness by model size | Nylon (SLS) | 50x50mm: 1.5mm", value_mm=1.5, applies={"size_band_mm": 50.0}, severity="warning")
add(J3, "mjf.wall_size_50", process=MJF, rule="p3d_wall_min_size_band", page="jlc3dp_dg", quote_kind="table_row", cells=["Nylon (MJF)", "1.0mm", "1.2mm", "1.5mm", "2.0mm", "2.0mm"],
    quote="Wall thickness by model size | Nylon (MJF) | 50x50mm: 1.5mm", value_mm=1.5, applies={"size_band_mm": 50.0}, severity="warning")
add(J3, "sla.wall_size_50", process=SLA, rule="p3d_wall_min_size_band", page="jlc3dp_dg", quote_kind="table_row", cells=["Resin (SLA)", "0.5mm", "0.8mm", "1.0mm", "1.5mm", "2.0mm"],
    quote="Wall thickness by model size | Resin (SLA) | 50x50mm: 1.0mm", value_mm=1.0, applies={"size_band_mm": 50.0}, severity="warning")

# ============================================================================================ SendCutSend (CNC billet)
SC = "sendcutsend"
add(SC, "cnc.part_max", process=CNC, rule="cnc_part_max_size", page="scs_cnc_guide", quote="Maximum overall part size: 7” x 7” x 12”", value_mm=[177.8, 177.8, 304.8],
    comparison="<=", severity="error", phrasing="capability")
add(SC, "cnc.part_min", process=CNC, rule="cnc_part_min_size", page="scs_cnc_guide", quote="Minimum overall part size: .5” x .5” x .5”", value_mm=[12.7, 12.7, 12.7],
    comparison=">=", severity="error", phrasing="capability")
add(SC, "cnc.min_volume_6061", process=CNC, rule="cnc_part_min_volume", page="scs_specs", quote_kind="json_field", material="al6061",
    cells=["ALU6061A-CNC", "cutting_specs", "min_part_volume", "0.075"], quote="ALU6061A-CNC cutting_specs.min_part_volume = 0.075 (cubic inches)",
    value=round(0.075 * IN ** 3, 1), unit="mm3", severity="error", phrasing="capability")
add(SC, "cnc.cutout_min", process=CNC, rule="cnc_slot_min", page="scs_cnc_guide", quote="The minimum internal machined cutout size for CNC milled parts is .125” or 3.175mm.",
    value_mm=3.175, severity="error", phrasing="requirement", measured="narrowest pocket or slot")
add(SC, "cnc.corner_radius_min", process=CNC, rule="cnc_corner_radius_min", page="scs_cnc_guide",
    quote="This means the minimum internal radius we can produce for machined features is .0625” or 1.587mm.", value_mm=1.587, severity="error", phrasing="capability")
add(SC, "cnc.sharp_internal", process=CNC, rule="cnc_corner_sharp", page="scs_cnc_guide", quote="Sharp internal features will not be producible due to tooling radii",
    value=0, unit="sharp vertical inside corners", comparison="<=", severity="error", phrasing="not producible")
add(SC, "cnc.corner_fillet_height", process=CNC, rule="cnc_corner_radius_depth", page="scs_cnc_guide",
    quote="Internal wall-to-wall corners will require a fillet which is at least the radius of the cutter being used, or at least one fifth the height of the wall – whichever is greater.",
    formula={"d": 0.2, "floor_mm": 1.587}, severity="error", phrasing="requirement",
    note="The cutter radius is taken as SendCutSend's smallest, 1.587 mm (.0625 in).")
add(SC, "cnc.drill_min", process=CNC, rule="cnc_hole_min", page="scs_cnc_guide", quote="Our smallest drill is .0629″, so we can produce circular holes as small as .0629″ (1.597mm).",
    value_mm=1.597, severity="error", phrasing="capability")
add(SC, "cnc.hole_depth_small", process=CNC, rule="cnc_hole_depth_ratio", page="scs_cnc_guide",
    quote="As a rule of thumb, holes that are up to .500” wide can have a depth that is up to 8x the hole’s diameter.", value=8.0, unit="x diameter", comparison="<=",
    applies={"hole_d_le": 12.7}, severity="warning", phrasing="rule of thumb")
add(SC, "cnc.hole_depth_large", process=CNC, rule="cnc_hole_depth_ratio", page="scs_cnc_guide",
    quote="For holes or cutouts over .500”, the maximum allowed depth will typically be up to 4x the hole diameter.", value=4.0, unit="x diameter", comparison="<=",
    applies={"hole_d_gt": 12.7}, severity="error", phrasing="maximum allowed")
add(SC, "cnc.standard_drills", process=CNC, rule="cnc_hole_standard_drill", page="scs_cnc_guide",
    quote="We recommend that circular holes up to .500” in diameter be sized consistently with standard drill indexes.", value_mm=12.7, comparison="in_list",
    standard_list_rule="hubs.cnc.metric_drills", severity="warning", phrasing="recommendation",
    note="SendCutSend publishes no drill list; Hubs' metric drill table is used as the standard index (and fractional inch sizes by 1/64 in).")
add(SC, "cnc.wall_height", process=CNC, rule="cnc_wall_height_ratio", page="scs_cnc_guide", quote="We recommend that wall thicknesses be at least 1/8th of the wall height.",
    formula={"d": 0.125}, severity="warning", phrasing="recommendation", measured="thinnest walls against their free height")
add(SC, "cnc.unreachable", process=CNC, rule="cnc_undercut", page="scs_cnc_guide", quote="Features will not be producible if our tooling cannot reach the area to mill",
    value=0, unit="faces no straight cutter reaches", comparison="<=", severity="error", phrasing="not producible")
add(SC, "cnc.tap_hole_major", process=CNC, rule="cnc_thread_modeled_d", page="scs_cnc_guide",
    quote="For CNC-machined parts, model holes that you want tapped as simple holes with a diameter that matches the major diameter of the thread for the tap size you need.",
    formula={"d": 1.0}, comparison="==", tolerance_mm=0.05, severity="warning", phrasing="model convention (the app shows the preferred size)",
    conflicts=["protolabs.cnc.thread_m4_modelled_d", "jlccnc.cnc.tap_drill_m3"],
    note="Protolabs and JLCCNC want the tap-drill (minor) diameter modelled; SendCutSend wants the major diameter.")
add(SC, "cnc.tap_sizes", process=CNC, rule="cnc_thread_range", page="scs_cnc_guide", quote_kind="table_row", cells=["M2 x 0.40", "2.000mm"],
    quote="Available thread/tap sizes for CNC machined parts | Metric: M2 x 0.40 ... M12 x 1.75", value=[2.0, 12.0], unit="metric thread diameter", comparison="within",
    severity="error", phrasing="available sizes", sizes=[2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0])
add(SC, "cnc.no_modelled_threads", process=CNC, rule="cnc_threads_modelled", page="scs_cnc_guide", quote="Do not model threads.", value=0, comparison="<=", evaluate=False,
    note="Helical thread geometry is not recognised in the B-rep (gap).")
info(SC, "cnc.tolerance", CNC, "scs_cnc_guide", "Milled parts will have an overall cut tolerance of +/- .005”", rule="tolerance", value_mm=0.127)

# ============================================================================================ RapidDirect
RD = "rapiddirect"
add(RD, "cnc.corner_radius_depth", process=CNC, rule="cnc_corner_radius_depth", page="rd_cnc_dg", quote_kind="table_row", cells=["Internal Corner Radius", "⅓ times cavity depth (or larger)"],
    quote="Internal Corner Radius | Recommended: ⅓ times cavity depth (or larger)", formula={"d": 1 / 3}, severity="warning")
add(RD, "cnc.cavity_depth_width", process=CNC, rule="cnc_pocket_depth_width", page="rd_cnc_dg", quote_kind="table_row", cells=["Cavity Depth", "4 times cavity width", "10 times the tool diameter or 25 cm"],
    quote="Cavity Depth | Recommended: 4 times cavity width | Feasible: 10 times the tool diameter or 25 cm", value=4.0, comparison="<=", severity="warning")
add(RD, "cnc.cavity_depth_tool", process=CNC, rule="cnc_pocket_depth_tool", page="rd_cnc_dg", quote_kind="table_row", cells=["Cavity Depth", "4 times cavity width", "10 times the tool diameter or 25 cm"],
    quote="Cavity Depth | Recommended: 4 times cavity width | Feasible: 10 times the tool diameter or 25 cm", value=10.0, unit="x cutter diameter", comparison="<=", severity="error",
    phrasing="feasible limit")
add(RD, "cnc.wall_rec_metal", process=CNC, rule="cnc_wall_min", page="rd_cnc_dg", material="metal", quote_kind="table_row",
    cells=["Wall Thickness", "1.5 mm (plastics), 0.8 mm (metals)", "1.0 mm (plastics), 0.5 mm (metals)"],
    quote="Wall Thickness | Recommended: 1.5 mm (plastics), 0.8 mm (metals) | Feasible: 1.0 mm (plastics), 0.5 mm (metals)", value_mm=0.8, severity="warning")
add(RD, "cnc.wall_feasible_metal", process=CNC, rule="cnc_wall_min", page="rd_cnc_dg", material="metal", quote_kind="table_row",
    cells=["Wall Thickness", "1.5 mm (plastics), 0.8 mm (metals)", "1.0 mm (plastics), 0.5 mm (metals)"],
    quote="Wall Thickness | Recommended: 1.5 mm (plastics), 0.8 mm (metals) | Feasible: 1.0 mm (plastics), 0.5 mm (metals)", value_mm=0.5, severity="error", phrasing="feasible limit",
    conflicts=["rapiddirect.cnc.wall_prose_metal"])
add(RD, "cnc.wall_prose_metal", process=CNC, rule="cnc_wall_min", page="rd_cnc_dg", material="metal",
    quote="To avoid these difficulties, you can design walls with a minimum thickness of 0.25mm for metal components and 0.50mm for plastic parts as they can withstand the rigors of the manufacturing process.",
    value_mm=0.25, comparison="info", severity="info", conflicts=["rapiddirect.cnc.wall_feasible_metal"],
    note="Contradicts the same page's table (0.5 mm feasible, 0.8 mm recommended for metals); kept as information.")
add(RD, "cnc.hole_depth_rec", process=CNC, rule="cnc_hole_depth_ratio", page="rd_cnc_dg", quote_kind="table_row", cells=["Hole Depth", "4 times the nominal diameter", "40 times the nominal diameter"],
    quote="Hole Depth | Recommended: 4 times the nominal diameter | Feasible: 40 times the nominal diameter", value=4.0, comparison="<=", severity="warning")
add(RD, "cnc.hole_depth_feasible", process=CNC, rule="cnc_hole_depth_ratio", page="rd_cnc_dg", quote_kind="table_row", cells=["Hole Depth", "4 times the nominal diameter", "40 times the nominal diameter"],
    quote="Hole Depth | Recommended: 4 times the nominal diameter | Feasible: 40 times the nominal diameter", value=40.0, comparison="<=", severity="error")
add(RD, "cnc.hole_min", process=CNC, rule="cnc_hole_min", page="rd_cnc_dg", quote_kind="table_row", cells=["Drill Size", "Standard drill bit (0,12”)", "Any diameter larger than 1 mm"],
    quote="Drill Size | Recommended: Standard drill bit (0,12”) | Feasible: Any diameter larger than 1 mm", value_mm=1.0, severity="error")
add(RD, "cnc.thread_length", process=CNC, rule="cnc_thread_depth_ratio_max", page="rd_cnc_dg", quote="A tap that exceeds 3 times its diameter is deep and can pose a significant challenge.",
    value=3.0, comparison="<=", severity="warning")
add(RD, "cnc.depth_al_tool", process=CNC, rule="cnc_pocket_depth_tool", page="rd_cnc_dg", material="al*",
    quote="For instance, with plastics, the ratio should not be greater than 15 times the diameter of the end mill, aluminum should be no more than 10 times, and steel’s limit is 5 times.",
    value=10.0, unit="x cutter diameter", comparison="<=", severity="warning", duplicate_of="rapiddirect.cnc.cavity_depth_tool")
add(RD, "cnc.part_max", process=CNC, rule="cnc_part_max_size", page="rd_cnc_dg", quote_kind="table_row", cells=["CNC Milling", "4000×1500×600 mm 157.5×59.1×23.6 in.", "4×4 mm 0.1×0.1 in."],
    quote="CNC Milling | Maximum Dimension 4000×1500×600 mm | Minimum Dimension 4×4 mm", value_mm=[600.0, 1500.0, 4000.0], comparison="<=", severity="error", phrasing="capability")
info(RD, "cnc.undercut_size", CNC, "rd_cnc_dg", "", quote_kind="table_row", cells=["Undercut dimension", "3 mm to 40 mm"], rule="cnc_undercut_width")
RULES["rapiddirect.cnc.undercut_size"]["quote"] = "Undercut dimension | Recommended: 3 mm to 40 mm"
add(RD, "fdm.clearance_sliding", process=FDM, rule="p3d_clearance_moving", page="rd_3dp_dg", quote_kind="table_row",
    cells=["Fused Deposition Modeling (FDM)", "0.25 mm to 0.35 mm", "0.50 mm to 0.60 mm"], quote="Fused Deposition Modeling (FDM) | Press-fit 0.25 mm to 0.35 mm | Sliding 0.50 mm to 0.60 mm",
    value_mm=0.5, evaluate=False, note=NOT_CLEAR)
add(RD, "fdm.overhang", process=FDM, rule="p3d_overhang_max_deg", page="rd_3dp_dg", quote="Ensure that steep features maintain an angle of less than 45 ° relative to the vertical print plane.",
    value=45.0, unit="deg from vertical", comparison="<=", severity="warning", phrasing="design around self-supporting angles")
add(RD, "pbf.escape", process=SLS, rule="p3d_enclosed_void", page="rd_3dp_dg",
    quote="For industrial powder-bed platforms (SLS/MJF), designing a hollow, shelled structure strictly mandates the inclusion of a minimum of two escape holes (drainage vents) that are at least 3.0mm in diameter.",
    value_mm=3.0, comparison="<=", severity="error", applies_processes=[SLS, MJF])

# ============================================================================================ Shapeways (SLS PA12)
SW = "shapeways"
add(SW, "sls.walls_supported", process=SLS, rule="p3d_wall_min", page="shapeways_vp", quote="Supported Walls 0.7 mm (Standard)", value_mm=0.7, severity="error",
    phrasing="minimum (may not survive printing and cleaning)")
add(SW, "sls.walls_unsupported", process=SLS, rule="p3d_wall_min_unsupported", page="shapeways_vp", quote="Unsupported Walls 0.7 mm (Standard)", value_mm=0.7, severity="error")
add(SW, "sls.wires_unsupported", process=SLS, rule="p3d_feature_min", page="shapeways_vp", quote="Unsupported Wires 1.0 mm (Standard)", value_mm=1.0, severity="error",
    measured="smallest pin diameter (a pin is an unsupported wire)")
add(SW, "sls.escape_single", process=SLS, rule="p3d_enclosed_void", page="shapeways_vp", quote="Single Escape Hole Diameter 4.0 mm (Standard)", value_mm=4.0, comparison="<=", severity="error")
add(SW, "sls.min_bbox", process=SLS, rule="p3d_part_min_sum", page="shapeways_vp", quote="X + Y + Z ≥ 20 mm (Standard)", value_mm=20.0, severity="error", measured="sum of the bounding box sides")
add(SW, "sls.max_bbox", process=SLS, rule="p3d_part_max_size", page="shapeways_vp", quote="650 × 350 × 550 mm (Standard White)", value_mm=[350.0, 550.0, 650.0], comparison="<=", severity="error")
add(SW, "sls.clearance", process=SLS, rule="p3d_clearance_assembly", page="shapeways_vp", quote="Clearance Minimum 0.5 mm (Standard)", value_mm=0.5, evaluate=False, note=NOT_CLEAR)
add(SW, "sls.emboss", process=SLS, rule="p3d_emboss", page="shapeways_vp", quote="0.5 mm high & wide for text (All)", evaluate=False, note=NOT_TEXT)
info(SW, "sls.accuracy", SLS, "shapeways_vp", "± 0.15 mm, then ± 0.15% of longest axis", rule="tolerance")

# ============================================================================================ PCBWay
PW = "pcbway"
info(PW, "fdm.accuracy", FDM, "pcbway_3dp", "FDM: L<100mm,±0.2mm. L>100mm,±0.2%*L(mm)", rule="tolerance")

# ============================================================================================ owner's printer (repository sources)
OW = "own_printer"
add(OW, "fdm.wall_one_line", process=FDM, rule="p3d_wall_min", page="dfm_print",
    quote="across the layers a feature needs one bead: under the nozzle diameter the slicer drops it (error).", formula={"nozzle": 1.0}, value_mm=0.4,
    severity="error", phrasing="the project's own check", measured="thinnest wall across the layers")
add(OW, "fdm.wall_two_lines", process=FDM, rule="p3d_wall_min", page="printsettings",
    quote="a 0.4 mm nozzle's usual functional profile: 0.45 mm lines, 0.2 mm layers, 3 walls, 5 top / 4 bottom",
    formula={"line_width": 2.0}, value_mm=0.9, severity="warning", phrasing="derived: two perimeter lines of the default profile",
    note="DERIVED, not published: two lines of the declared line width (0.45 mm by default) so the wall prints as two perimeters; between one line and two it prints as a single fragile bead.")
add(OW, "fdm.overhang", process=FDM, rule="p3d_overhang_max_deg", page="dfm_rules",
    quote="an overhang can usually be printed up to 45 deg; above that support is required", value=45.0, unit="deg from vertical", comparison="<=", severity="warning",
    phrasing="the project's own rule (Hubs' figure)")
add(OW, "fdm.bridge", process=FDM, rule="p3d_bridge_max", page="dfm_rules",
    quote="a desktop printer with part cooling bridges a few tens of mm with visible sag; set your printer's figure", value_mm=30.0, comparison="<=", severity="warning",
    phrasing="the project's own figure (fdm.bridge_max_mm)")
add(OW, "fdm.cantilever", process=FDM, rule="p3d_overhang_length_max", page="dfm_rules",
    quote="an overhang can usually be printed up to 45 deg; above that support is required", value_mm=0.0, comparison="<=", severity="warning",
    phrasing="a flat overhang anchored on one side only has nothing to bridge to", measured="longest flat cantilever (overhang anchored on one side)",
    note="A flat down-facing surface held on one side only is a 90-degree overhang: it needs support at any length.")
add(OW, "fdm.pin_min", process=FDM, rule="p3d_feature_min", page="dfm_rules", quote="minimum feature size 2.0 mm recommended; pins under 5 mm are perimeters only and snap off",
    value_mm=2.0, severity="warning", phrasing="the project's own rule (fdm.feature_min_mm)", measured="smallest pin or boss diameter")
add(OW, "fdm.hole_min", process=FDM, rule="p3d_hole_min", page="dfm_rules", quote="minimum hole diameter 2.0 mm recommended; holes print undersize, drill critical ones after printing",
    value_mm=2.0, severity="warning", phrasing="the project's own rule (fdm.hole_min_mm)")
add(OW, "fdm.horizontal_hole", process=FDM, rule="p3d_horizontal_hole_max", page="dfm_rules",
    quote="text-to-cad's own figure: up to 10 mm a horizontal hole prints unsupported; wider, its crown sags", value_mm=10.0, comparison="<=", severity="warning",
    phrasing="the project's own rule (fdm.horizontal_hole_max_mm)")
add(OW, "fdm.horizontal_hole_teardrop", process=FDM, rule="p3d_horizontal_hole_shape", page="guidelines",
    quote="A hole whose axis lies in the build plane gets 0.3 mm (M3 3.7) and a teardrop or flat top, so it prints without support.", evaluate=False,
    note="Teardrop or flat-top hole profiles are not recognised (gap); hole sizes are checked by practice DG-05.")
add(OW, "fdm.no_threads", process=FDM, rule="p3d_thread_in_print", page="guidelines", quote="No thread is tapped, cut or self-tapped into a printed part.", value=0,
    unit="threads in the print", comparison="<=", severity="warning", phrasing="owner's practice (practice DG-04 judges the joint)")
add(OW, "fdm.build_volume", process=FDM, rule="p3d_part_max_size", page="dfm_rules",
    quote="DEFAULT_PRINT_VOLUME = (220.0, 220.0, 250.0) # a common desktop printer", value_mm=[220.0, 220.0, 250.0], comparison="<=", severity="error",
    phrasing="the project's default printer; design.manufacturing['printer']['build_volume'] replaces it", use_design_build_volume=True)
add(OW, "fdm.clearance_holes", process=FDM, rule="p3d_clearance_hole", page="guidelines",
    quote="Printed clearance holes: ISO 273 medium plus an FDM allowance of 0.2 mm on the diameter", evaluate=False,
    note="Judged per screw by practice DG-05 (printed_hole_too_small); not repeated here.")
add(OW, "fdm.light_parts_only", process=FDM, rule="p3d_load_path", page="guidelines", quote="3D printing only for light, non-load-bearing parts", evaluate=False,
    note="Judged by practice DG-01 (printed_load_path).")
info(OW, "fdm.layer_height", FDM, "printsettings", "DEFAULT_PRINT_SETTINGS = {\"line_width_mm\": 0.45, \"layer_height_mm\": 0.2, \"walls\": 3,", quote_kind="repo_file",
     rule="layer_height", value_mm=0.2)
for k in [k for k, r in RULES.items() if r["supplier"] == OW and r["quote_kind"] != "repo_file"]:
    raise AssertionError(k)

# ============================================================================================ write
SUPPLIERS = {
    "xometry": ("Xometry", "https://www.xometry.com/"), "protolabs": ("Protolabs", "https://www.protolabs.com/"),
    "hubs": ("Hubs (Protolabs Network)", "https://www.hubs.com/"), "fictiv": ("Fictiv", "https://www.fictiv.com/"),
    "jlccnc": ("JLCCNC", "https://jlccnc.com/"), "jlc3dp": ("JLC3DP", "https://jlc3dp.com/"), "sendcutsend": ("SendCutSend", "https://sendcutsend.com/"),
    "rapiddirect": ("RapidDirect", "https://www.rapiddirect.com/"), "shapeways": ("Shapeways", "https://www.shapeways.com/"),
    "pcbway": ("PCBWay", "https://www.pcbway.com/"), "own_printer": ("Owner's printer (PLA/PETG, 0.4 mm nozzle)", "docs/DESIGN_GUIDELINES.md"),
}
NOT_READ = {
    "fictiv": ["Re-fetching https://www.fictiv.com/specifications/cnc-machining, /specifications, /specifications/3d-printing, /capabilities/* and the CNC design-guide article "
               "on 2026-11-19 returned HTTP 403 (a Cloudflare challenge; robots.txt allows Claude-User). Not retried or worked around. The CNC specification page as "
               "fetched earlier the same day (plain fetch, for the sheet-metal rules) is the source; no Fictiv 3D-printing figures were read."],
    "xometry": ["The design guides (/resources/design-guides/design-guide-cnc-machining/, ...-fdm-..., ...-sls-..., ...-mjf-..., ...-sla-...) are download-gated "
                "(form for the PDF); only their landing pages were read and they contain no figures."],
    "hubs": ["Hubs is now Protolabs Network; its knowledge-base figures are general guidance rather than ordering limits."],
    "own_printer": ["Sources are repository files (docs/DESIGN_GUIDELINES.md, mechloop/printsettings.py, mechloop/verifiers/dfm_rules.py, "
                    "mechloop/verifiers/dfm_print.py); quotes are verified against them when this file is built."],
}
SKIPPED = [
    {"host": "www.cnckitchen.com", "why": "robots.txt names ClaudeBot, anthropic-ai and Claude-Web with 'Disallow: /' (Content-Signal ai-train=no): not fetched."},
    {"host": "craftcloud3d.com", "why": "robots.txt allows '/', but the home page and sitemap returned HTTP 403 (Cloudflare challenge) on 2026-11-19: no rules read, not worked around."},
    {"host": "www.fictiv.com", "why": "HTTP 403 (Cloudflare challenge) on re-fetch; earlier same-day copy of the CNC specification page used."},
    {"host": "www.pcbway.com", "why": "Read; the 3D-printing page publishes tolerances only (one info rule)."},
]
for f in FAIL:
    print("QUOTE NOT FOUND", f)
assert not FAIL, f"{len(FAIL)} quote(s) not found"
OUT.mkdir(parents=True, exist_ok=True)
for sup, (name, home) in SUPPLIERS.items():
    rules = [r for r in RULES.values() if r["supplier"] == sup]
    procs = sorted({r["process"] for r in rules})
    doc = {"schema": "mechloop.supplier_rules/1", "version": f"{DATE}.cnc3dp.1", "supplier": sup, "name": name, "home": home, "retrieved": DATE,
           "processes": procs, "how_read": "Plain HTTPS page fetch, robots.txt checked first, no account, no upload, no quote; figures copied as published. "
           "Prose quotes are verbatim; 'table_row' quotes name the table, row and cells (verified cell by cell); repository quotes are verbatim.",
           "not_read": NOT_READ.get(sup, []), "rules": rules}
    (OUT / f"{sup}.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(sup, len(rules), procs)
(OUT / "_sources.json").write_text(json.dumps({"retrieved": DATE, "pages": URL, "repository_files": REPO_FILES, "skipped": SKIPPED}, indent=1) + "\n", encoding="utf-8")
print("quotes checked", CHECKED, "rules", len(RULES))
