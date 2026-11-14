"""Can each custom part actually be made by the process it is assigned?

Each custom part is checked against its process (`component.process` / `meta["process"]`, else chosen
from the material; see tolerance/process.py):

- "sheet"    cut in 2D from sheet or plate by laser, waterjet or router, optionally bent: dfm_sheet.py
- "printed"  FDM: dfm_print.py
- "machined" 3-axis CNC milling, or a plain lathe part: dfm_cnc.py

Purchased and cut-to-length parts are not checked (they must not be modified). The limits and where each
came from are in dfm_rules.py; docs/DFM.md explains the checks and what is not covered.

Every finding names the part, where on it (`at`, world coordinates), the measured `value`, the `limit`
with its `rule` id and `source`, and a hint. Errors: the process cannot make it as drawn. Warnings: it
can, at a cost or a risk.
"""
from __future__ import annotations

import traceback

from ..model import Design
from ..report import VerifierResult, timed
from ..tolerance.process import process_of
from . import dfm_geom as G
from .dfm_rules import GENERIC_PLATE_MM, LASER_USD_PER_M, Limits

STOCK_MM = GENERIC_PLATE_MM            # kept for callers of the old name
AXES = {"+Z": (0, 0, 1), "-Z": (0, 0, -1), "+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0)}


def check_part(r: VerifierResult, design: Design, c) -> dict:
    """Run the checks for one part's process. Returns its metrics row."""
    from . import dfm_cnc, dfm_print, dfm_sheet

    proc = process_of(c)
    row = {"process": proc, "material": c.material}
    if proc not in ("printed", "machined", "sheet"):
        row["checked"] = False
        return row
    lim = Limits(design, c)
    sm = G.sample_surface(c.shape)
    frame = G.part_frame(c.shape)
    cyls = G.cylinders(c.shape)
    holes = G.holes(c.shape, sm, cyls)
    if proc == "printed":
        row.update(dfm_print.check_printed(r, design, c, sm, frame, cyls, holes, lim))
    elif proc == "machined":
        row.update(dfm_cnc.check_machined(r, design, c, sm, frame, cyls, holes, lim, proc))
    else:
        plate = dfm_sheet.plate_of(c.shape, frame, sm)
        tapped = G.tapped_holes(design, c, sm)
        mt = dfm_sheet.modal_thickness(sm) if plate is not None and plate["steps"] else None
        if mt is not None and mt[0] < 0.6 * plate["thickness"] and not any(cy.concave and cy.angle < 200 for cy in cyls):
            row.update({"form": "bent, corners sharp", "thickness_mm": round(mt[0], 2)})
            r.add("error", "sharp_bend", f"{c.name}: looks like {mt[0]:g} mm sheet folded with dead-sharp corners (no bend radius). Sheet cannot be "
                  f"bent sharp; the bend has an inside radius of about the thickness and an outside radius one thickness larger.",
                  part=c.name, value=0.0, limit=round(mt[0], 2), rule="sheet.bend_radius_t_ratio", source=lim.source("sheet.bend_radius_t_ratio"),
                  hint=f"Fillet the inside edge of each bend to r >= {mt[0]:g} mm and the outside edge to r + {mt[0]:g} mm; "
                       "flange lengths and hole-to-bend distances are checked once the bends are modelled.")
        elif plate is not None:
            row.update(dfm_sheet.check_flat(r, c, plate, sm, holes, lim, tapped, proc))
            P = row.pop("_profile", None)
            if P is not None:
                row["estimate"] = {"cut_usd": round(P.length / 1000 * LASER_USD_PER_M + 0.05 * (1 + len(P.interiors)), 2),
                                   "basis": f"estimate, not a quote: ${LASER_USD_PER_M:g} per metre of cut plus 5 cents a pierce; material and set-up fee not included"}
        else:
            bent = dfm_sheet.bent_sheet(c.shape, sm, cyls)
            if bent is not None:
                row.update(dfm_sheet.check_bent(r, c, c.shape, bent, sm, holes, lim))
            else:
                row["form"] = "not sheet"
                fc = G.face_classes(c.shape, frame)
                why = (f"{fc['angled_planes']} face(s) at an angle and {fc['tori'] + fc['other'] + fc['cones']} curved face(s)"
                       if fc["angled_planes"] or fc["tori"] or fc["other"] else "it is a block, not a plate, and no bends were recognised")
                r.add("error", "not_sheet", f"{c.name}: declared process 'sheet' but the part is not one constant thickness with square-cut edges "
                      f"({why}). A sheet part is a flat profile, or flat flanges joined by bends with an inside and an outside radius.",
                      part=c.name, at=(fc["angled_at"] + fc["curved_at"])[:6] or None,
                      hint="Model it as a constant-thickness profile (fillet both edges of each bend: r inside, r + t outside), "
                           "or set process='machined' or 'printed'.")
    return row


def verify_manufacture(design: Design) -> VerifierResult:
    r = VerifierResult("manufacture")
    custom = [c for c in design.components if not c.cots]
    if not custom:
        r.skipped = "no custom parts"
        return r
    with timed(r):
        parts = {}
        for c in custom:
            try:
                parts[c.name] = check_part(r, design, c)
            except ValueError as e:     # an unknown process, shop, rule id or orientation: the declaration is wrong, not the part
                r.add("error", "bad_manufacturing_declaration", f"{c.name}: {e}", part=c.name)
                parts[c.name] = {"process": "?", "checked": False}
            except Exception as e:      # one unreadable part must not hide the findings on the others; unmeasured is not a pass
                r.add("error", "part_not_checked", f"{c.name}: the manufacturability check failed on this part ({type(e).__name__}: {e}); "
                      f"it has not been judged.", part=c.name, trace=traceback.format_exc()[-500:])
                parts[c.name] = {"process": process_of(c), "checked": False}
        procs = sorted({v["process"] for v in parts.values()})
        setups = sum(v.get("setups_estimate", 0) for v in parts.values())
        cost = sum((v.get("estimate") or {}).get("cost_usd_each_qty1", 0) or 0 for v in parts.values())
        try:
            lim = Limits(design)
            shop, over = lim.shop_name, sorted(lim.over) or None
        except ValueError:
            shop, over = "?", None
        r.metrics = {"custom_parts": len(custom), "by_process": {p: sum(1 for v in parts.values() if v["process"] == p) for p in procs},
                     "shop": shop, "limits_overridden": over,
                     "machining_setups_total": setups or None,
                     "machining_cost_estimate_usd_qty1": round(cost, 0) or None,
                     "parts": parts if len(parts) <= 40 else {k: {kk: vv for kk, vv in v.items() if kk in ("process", "form", "setups_estimate", "up")}
                                                              for k, v in parts.items()}}
    return r


def export_flat_patterns(design: Design, out_dir) -> dict:
    """DXF flat profiles for the parts a laser shop would cut. See dfm_sheet.export_flat_patterns."""
    from .dfm_sheet import export_flat_patterns as _ex

    return _ex(design, out_dir)
