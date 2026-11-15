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
    lost = getattr(sm.mesh, "metadata", {}).get("faces_not_meshed")
    if lost:      # checked on what could be meshed: say so, a part that is partly unseen has not passed
        row["faces_not_meshed"] = lost
        r.add("warning", "part_partly_checked", f"{c.name}: the CAD kernel could not mesh {lost} of its faces; the checks below ran on "
              f"the rest of the surface and may miss what is on those faces.", part=c.name, faces_not_meshed=lost,
              hint="Usually a degenerate face in an imported STEP file: re-export or heal the part.")
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
    from ..shops import check_shop_part

    check_shop_part(r, design, c, row, lim)      # what the part's named shop publishes (mechloop/shops/*.json); nothing for "generic"
    try:      # sharp edges and corners (dfm_edges.py): B-rep only, cheap
        from . import dfm_edges

        ed = dfm_edges.check_edges(r, design, c, proc, row, _PRINTED_EDGES)
        _EDGE_CLASSES[c.name] = ed.pop("_class")
        row["edges"] = ed
    except Exception as e:
        row["edges"] = {"checked": False, "why": f"{type(e).__name__}: {e}"}
    return row


_PRINTED_EDGES: dict = {}      # filled per run by check_part, reported once by verify_manufacture
_EDGE_CLASSES: dict = {}


def verify_manufacture(design: Design) -> VerifierResult:
    r = VerifierResult("manufacture")
    custom = [c for c in design.components if not c.cots]
    if not custom:
        r.skipped = "no custom parts"
        return r
    with timed(r):
        parts = {}
        _PRINTED_EDGES.clear()
        _EDGE_CLASSES.clear()
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
        _explain_vendor_patterns(design, r)
        lead = None
        try:
            from . import dfm_edges

            if _PRINTED_EDGES:
                pe = dict(sorted(_PRINTED_EDGES.items()))
                r.add("info", "printed_edges",
                      f"{len(pe)} printed part(s) have sharp edges on the face they are printed on ("
                      f"{sum(v['sharp_edges_on_bed_face'] for v in pe.values())} edges: the squashed first layer spreads there, a 0.4 mm "
                      f"chamfer hides it) and hole mouths without a lead-in ({sum(v['hole_mouths_without_lead_in'] for v in pe.values())}: "
                      f"a small chamfer helps a screw, insert or shaft start). Information only; counts per part in the data.",
                      parts=pe)
            lead = dfm_edges.lead_ins(r, design, dict(_EDGE_CLASSES))
        except Exception as e:
            r.add("warning", "lead_ins_not_checked", f"Lead-ins of shafts and bores were not checked: {type(e).__name__}: {e}")
        try:
            printed = print_settings_report(r, design)
        except ValueError as e:
            r.add("error", "bad_manufacturing_declaration", f"print settings: {e}")
            printed = None
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
                     "edges": {"sharp_outside_edges_by_part": {k: v["edges"]["sharp_outside_edges"] for k, v in sorted(parts.items())
                                                               if isinstance(v.get("edges"), dict) and v["edges"].get("sharp_outside_edges")},
                               "sharp_profile_corners_by_part": {k: v["edges"]["sharp_profile_corners"] for k, v in sorted(parts.items())
                                                                 if isinstance(v.get("edges"), dict) and v["edges"].get("sharp_profile_corners")},
                               "edge_break_declared": {k: v["edges"]["edge_break_declared_mm"] for k, v in sorted(parts.items())
                                                       if isinstance(v.get("edges"), dict) and v["edges"].get("edge_break_declared_mm")},
                               "shaft_bore_lead_ins": lead},
                     "print_settings": printed,
                     "parts": parts if len(parts) <= 40 else {k: {kk: vv for kk, vv in v.items() if kk in ("process", "form", "setups_estimate", "up")}
                                                              for k, v in parts.items()}}
    return r


def print_settings_report(r: VerifierResult, design: Design) -> dict | None:
    """Print settings of every printed part (mechloop.printsettings): where they come from, the solid fraction the mass
    is computed with, and two local checks: heat-set inserts whose perimeters are thinner than the insert maker's
    minimum wall (`insert_in_sparse_infill`), and the info `print_settings_default` for parts printed to the default."""
    import numpy as np

    from .. import printsettings as PS

    printed = [c for c in design.components if PS.is_printed(c)]
    if not printed:
        return None
    rows, default = {}, []
    for c in printed:
        fr = PS.fractions(c)
        st = fr["settings"]
        rows[c.name] = {"from": fr["settings_from"], "material": c.material, "walls": st["walls"], "line_width_mm": st["line_width_mm"],
                        "layer_height_mm": st["layer_height_mm"], "top_layers": st["top_layers"], "bottom_layers": st["bottom_layers"],
                        "infill": st["infill"], "infill_pattern": st["infill_pattern"], "orientation": st["orientation"],
                        "solid_fraction": fr["solid_fraction"], "mass_kg": round(c.mass(), 4), "solid_mass_kg": round(c.solid_mass(), 4)}
        if fr["settings_from"] == "default":
            default.append(c.name)
    if default:
        r.add("info", "print_settings_default",
              f"{len(default)} printed part(s) declare no print settings and are taken as printed to the default, "
              f"{PS.DEFAULT_NOTE}. Their mass, stiffness and strength follow from it.",
              parts=sorted(default)[:80], count=len(default), default=PS.DEFAULT_PRINT_SETTINGS,
              hint="Declare d.manufacturing['print_settings'] for the design and meta['print'] where a part differs (walls, infill, orientation).")
    comps = {c.name: c for c in design.components}
    thin = []
    for f in design.fasteners:
        sc = comps.get(f.name)
        if sc is None or not sc.meta.get("insert"):
            continue
        d = float(sc.meta.get("thread_d") or 0)
        need = PS.INSERT_WALL_MIN.get(d)
        for t in sc.meta.get("threads_into") or []:
            tc = comps.get(t)
            if tc is None or not PS.is_printed(tc) or need is None:
                continue
            st = PS.fractions(tc)["settings"]
            wall = float(st["walls"]) * float(st["line_width_mm"])
            if wall < need - 1e-9:
                thin.append({"screw": f.name, "part": t, "size": f"M{d:g}", "perimeters_mm": round(wall, 2), "insert_wall_min_mm": need,
                             "walls_needed": int(np.ceil(need / float(st["line_width_mm"]) - 1e-9))})
    if thin:
        w = min(thin, key=lambda x: x["perimeters_mm"] / x["insert_wall_min_mm"])
        r.add("warning", "insert_in_sparse_infill",
              f"{len(thin)} heat-set insert(s) sit in perimeters thinner than the insert maker's minimum wall (least: {w['screw']} in {w['part']}, "
              f"{w['perimeters_mm']:g} mm of perimeters against {w['insert_wall_min_mm']:g} mm for {w['size']}, ruthex RX data sheet): the rest "
              f"of the boss is sparse infill, which the insert's knurl does not grip and which splits when it is pressed in.",
              inserts=thin[:40], parts=sorted({x["part"] for x in thin}),
              hint=f"Print those parts with at least {w['walls_needed']} walls (meta['print']['walls']), or solid round the insert.")
    mass = sum(comps[n].mass() for n in rows)
    solid = sum(comps[n].solid_mass() for n in rows)
    return {"default": PS.DEFAULT_PRINT_SETTINGS, "default_note": PS.DEFAULT_NOTE, "printed_parts": len(rows),
            "on_default_settings": len(default), "printed_mass_kg": round(mass, 3), "printed_mass_if_solid_kg": round(solid, 3),
            "inserts_in_thin_perimeters": thin[:40], "parts": rows,
            "model": "mass = solid x (shell + core x infill); shell = face area x (walls x line width, or top/bottom layers x layer height); "
                     "edges counted twice, capped at the part's volume"}


def _explain_vendor_patterns(design: Design, r: VerifierResult) -> None:
    """A `holes_too_close` warning whose closest pair is a bought part's own cut-out and screw holes (a power entry
    module's mounting pattern) is true and stays; its hint then says whose pattern it is and what would clear it."""
    import numpy as np

    mods = [c for c in design.components if (c.meta.get("interfaces") or {}).get("pattern_note") and c.meta.get("placement")]
    for f in r.findings:
        if f.code != "holes_too_close" or not f.data.get("at"):
            continue
        for c in mods:
            P = np.array(c.meta["placement"], dtype=float)
            itf = c.meta["interfaces"]
            reach = max(itf.get("cutout", (0, 0))) / 2 + 12.0
            near = [a for a in f.data["at"] if np.linalg.norm(np.array(a, dtype=float) - P[:, 3]) <= reach]
            if near:
                f.data["vendor_pattern"] = {"part": c.name, "sku": c.sku, "web_mm": itf.get("cutout_to_screw_hole_web")}
                f.data["hint"] = (f"{f.data.get('hint', '')} At {c.name} this is the bought part's own pattern and cannot be spaced "
                                  f"out: {itf['pattern_note']}. Thin the panel to 2.5 mm there, or accept the warning with this "
                                  "reason; it is not suppressed.").strip()
                break


def export_flat_patterns(design: Design, out_dir) -> dict:
    """DXF flat profiles for the parts a laser shop would cut. See dfm_sheet.export_flat_patterns."""
    from .dfm_sheet import export_flat_patterns as _ex

    return _ex(design, out_dir)
