"""FDM printed parts: which way up, what needs support, what is too thin or too small to print.

The six axis-aligned orientations are tried on a sampled mesh (fast: no slicing). For each: the area that
overhangs by more than 45 degrees, less what prints anyway (short bridges between two walls, the crowns
of small horizontal holes), the first-layer contact area, the height, whether it fits the printer. The
best is chosen and reported; `component.meta["print_up"] = "+Z"` pins one. The remaining checks (thin
walls, small holes and pins, bosses around threads, load across layers) are then made in that orientation.
"""
from __future__ import annotations

import math

import numpy as np

from . import dfm_geom as G
from .dfm_rules import DEFAULT_PRINT_VOLUME, FILAMENT_USD_KG, HEAT_SET, PRINT_FLOW_MM3_S, Limits

COS45 = math.cos(math.radians(45.0))


def _hole_masks(sm: G.Sampled, holes: list) -> list[np.ndarray]:
    out = []
    for h in holes:
        rel = sm.pts - h.origin
        ax = rel @ h.axis
        rad = np.linalg.norm(rel - np.outer(ax, h.axis), axis=1)
        out.append((np.abs(rad - h.diameter / 2) < 0.06) & (np.abs(ax) <= h.depth / 2 + 0.05))
    return out


def _bridge_spans(sm: G.Sampled, idx: np.ndarray, up: np.ndarray, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For flat down-facing samples: the shortest span between two walls that could carry a bridge across
    the sample (inf if no direction has a wall on both sides), and the distance to the nearest wall."""
    span = np.full(len(idx), np.inf)
    nearest = np.full(len(idx), np.inf)
    if len(idx) == 0:
        return span, nearest
    side = [a for a in frame if abs(a @ up) < 0.5]
    g1, g2 = side[0], side[1]
    dirs = [g1, g2, (g1 + g2) / math.sqrt(2), (g1 - g2) / math.sqrt(2)]
    org = sm.pts[idx] - up * 0.12                       # just under the ceiling, in the air
    for g in dirs:
        dp, _ = G.ray_hits(sm.tris, org, g)
        dn, _ = G.ray_hits(sm.tris, org, -g)
        span = np.minimum(span, dp + dn)
        nearest = np.minimum(nearest, np.minimum(dp, dn))
    return span, nearest


def evaluate(sm: G.Sampled, name: str, up: np.ndarray, frame: np.ndarray, holes: list, masks: list, lim: Limits, vol) -> dict:
    h = sm.pts @ up
    verts = np.asarray(sm.mesh.vertices) @ up
    zmin, zmax = float(verts.min()), float(verts.max())
    down = sm.nrm @ up
    on_bed = (down < -0.98) & (h - zmin < 0.3)
    over = (down < -(COS45 + 0.01)) & ~on_bed
    flat = (down < -0.98) & ~on_bed
    # crowns of horizontal holes up to the limit print unsupported
    excused = np.zeros(len(h), dtype=bool)
    droop = []
    for hl, m in zip(holes, masks):
        if abs(hl.axis @ up) < 0.3:
            if hl.diameter <= lim("fdm.horizontal_hole_max_mm") + 1e-9:
                excused |= m
            else:
                droop.append(hl)
    # flat ceilings carried as a bridge between two walls
    idx = np.nonzero(flat & ~excused)[0]
    span, nearest = _bridge_spans(sm, idx, up, frame)
    bridged = span <= lim("fdm.bridge_max_mm") + 1e-9
    excused[idx[bridged]] = True
    need = over & ~excused
    support_area = float(sm.w[need].sum())
    footprint = float(sm.w[on_bed].sum())
    shadow = float((sm.w * np.clip(-down, 0, None)).sum())
    height = zmax - zmin
    side = [a for a in frame if abs(a @ up) < 0.5]
    v = np.asarray(sm.mesh.vertices)
    lat = sorted(float(np.ptp(v @ a)) for a in side)
    fits = lat[1] <= max(vol[:2]) + 1e-6 and lat[0] <= min(vol[:2]) + 1e-6 and height <= vol[2] + 1e-6
    fin = np.isfinite(span)
    return {"up": name, "up_vector": [round(float(x), 3) for x in up], "support_area_mm2": round(support_area, 0),
            "footprint_mm2": round(footprint, 0), "height_mm": round(height, 1), "lateral_mm": [round(x, 1) for x in lat],
            "flat_overhang_mm2": round(float(sm.w[flat].sum()), 0), "fits_print_volume": bool(fits),
            "bed_contact_fraction": round(footprint / max(shadow, 1e-9), 2),
            "slenderness": round(height / math.sqrt(max(footprint, 1.0)), 1),
            "bridges": {"max_span_mm": round(float(span[fin].max()), 1) if fin.any() else 0.0,
                        "over_5mm_mm2": round(float(sm.w[idx[fin & (span > lim("fdm.bridge_clean_mm"))]].sum()), 0),
                        "unsupported_ceiling_mm2": round(float(sm.w[idx[~bridged]].sum()), 0)},
            "_need": need, "_idx": idx, "_span": span, "_bridged": bridged, "_droop": droop, "_h": h, "_zmin": zmin, "_on_bed": on_bed}


def check_printed(r, design, c, sm: G.Sampled, frame: np.ndarray, cyls: list, holes: list, lim: Limits) -> dict:
    name = c.name
    man = lim.man.get("printer") or {}
    vol = tuple(lim.part.get("build_volume") or man.get("build_volume") or (design.printer or {}).get("build_volume") or DEFAULT_PRINT_VOLUME)
    nozzle = float(lim.option("printer", "nozzle", 0.4))
    world = bool(np.allclose(frame, np.eye(3), atol=1e-6))
    axes = G.axis_names(frame)
    masks = _hole_masks(sm, holes)

    def add(sev, code, msg, rule=None, value=None, at=None, hint=None, **more):
        data = {"part": name}
        if rule:
            data.update(lim.data(rule, value))
        if at is not None:
            data["at"] = at
        if hint:
            data["hint"] = hint
        data.update(more)
        r.add(sev, code, f"{name}: {msg}", **data)

    # ---- loads on this part, for the layer-direction check
    loads = []
    for lc in getattr(design, "loadcases", []):
        if lc.component == name:
            f = np.array(lc.force, dtype=float)
            if np.linalg.norm(f) > 0:
                loads.append((lc.name, f / np.linalg.norm(f)))

    pinned = lim.part.get("print_up") or c.meta.get("print_up")
    if pinned and pinned not in axes:
        raise ValueError(f"{name}: print_up {pinned!r}; use one of {sorted(axes)}")
    rows = {}
    for nm, up in axes.items():
        row = evaluate(sm, nm, up, frame, holes, masks, lim, vol)
        across = max((abs(f @ up) for _, f in loads), default=0.0)
        row["load_along_build_axis"] = round(float(across), 2)
        row["plain_score"] = (row["support_area_mm2"] - 0.2 * row["footprint_mm2"] + 0.5 * row["height_mm"]
                              + (0.0 if row["fits_print_volume"] else 1e6))
        row["score"] = row["plain_score"] + 400.0 * max(0.0, across - lim("fdm.layer_load_fraction"))
        rows[nm] = row
    best = rows[pinned] if pinned else min(rows.values(), key=lambda q: q["score"])
    easiest = min(rows.values(), key=lambda q: q["plain_score"])
    up = axes[best["up"]]
    out = {k: v for k, v in best.items() if not k.startswith("_") and k not in ("score", "plain_score")}
    out["orientation_pinned"] = bool(pinned)
    if not pinned and easiest is not best:
        out["orientation_note"] = (f"{easiest['up']} up would print with less support, but a load case then pulls the layers apart "
                                   f"({easiest['load_along_build_axis']:.0%} of it along the build direction); {best['up']} up keeps the load in the layers")
    if not world:
        out["orientation_frame"] = "the part's own axes (it sits at an angle in the assembly); see up_vector"
    out["orientations"] = {nm: {"support_area_mm2": q["support_area_mm2"], "footprint_mm2": q["footprint_mm2"],
                                "height_mm": q["height_mm"], "fits": q["fits_print_volume"]} for nm, q in rows.items()}

    # ---- size
    if not best["fits_print_volume"]:
        fit_any = [nm for nm, q in rows.items() if q["fits_print_volume"]]
        add("error", "too_big_to_print",
            f"{best['lateral_mm']} x {best['height_mm']} mm does not fit a {vol[0]:.0f} x {vol[1]:.0f} x {vol[2]:.0f} mm print volume "
            + (f"with {best['up']} up as pinned (it would fit with {fit_any[0]} up)." if fit_any else "in any of the six orientations."),
            value=max(best["lateral_mm"] + [best["height_mm"]]), limit=max(vol), source="design.manufacturing['printer']['build_volume'] or the default desktop printer",
            hint="Split the part, or make it from plate or extrusion.")

    # ---- support
    need = best["_need"]
    if best["support_area_mm2"] > lim("fdm.support_area_mm2"):
        pts = sm.pts[need]
        sel = G.spread(pts, -sm.w[need], k=5, min_sep=8.0) if len(pts) else []
        alt = min(rows.values(), key=lambda q: q["support_area_mm2"])
        add("warning", "needs_support",
            f"{'pinned' if pinned else 'even in its best'} print orientation ({best['up']} up) {best['support_area_mm2']:.0f} mm² overhangs by more "
            f"than 45 degrees with nothing under it and needs support material"
            + (f" (with {alt['up']} up it would be {alt['support_area_mm2']:.0f} mm²)." if pinned and alt["support_area_mm2"] < 0.5 * best["support_area_mm2"] else "."),
            rule="fdm.support_area_mm2", value=best["support_area_mm2"], orientation=best["up"], at=[G.xyz(pts[i]) for i in sel],
            hint="Chamfer the undersides at 45 degrees, use teardrop holes, or split the part along a flat face.")
    span, idx, bridged = best["_span"], best["_idx"], best["_bridged"]
    long_ = np.isfinite(span) & ~bridged
    if long_.any() and float(sm.w[idx[long_]].sum()) > 20.0:
        k = int(np.argmax(np.where(long_, span, -1)))
        add("warning", "long_bridge",
            f"a flat ceiling spans {span[k]:.0f} mm between walls at {G.xyz(sm.pts[idx[k]])} ({best['up']} up); beyond about "
            f"{lim('fdm.bridge_max_mm'):g} mm a bridge sags badly and is printed on support instead.",
            rule="fdm.bridge_max_mm", value=float(span[k]), at=[G.xyz(sm.pts[idx[k]])],
            hint="Arch or chamfer the ceiling, add a rib to halve the span, or turn the part.")
    if best["_droop"]:
        hl = max(best["_droop"], key=lambda q: q.diameter)
        add("warning", "horizontal_hole_droop",
            f"{len(best['_droop'])} horizontal hole(s) over {lim('fdm.horizontal_hole_max_mm'):g} mm (largest {hl.diameter:g} mm at {G.xyz(hl.origin)}, "
            f"{best['up']} up): the crown sags or needs support inside the bore.",
            rule="fdm.horizontal_hole_max_mm", value=hl.diameter, at=[G.xyz(q.origin) for q in best["_droop"][:6]],
            hint="Make the top of the hole a teardrop or a flat roof, turn the part so the hole is vertical, or ream it after printing.")

    # ---- stays on the bed
    if best["slenderness"] > lim("fdm.slenderness_max"):
        add("warning", "tall_thin_print",
            f"{best['height_mm']:.0f} mm tall on a {best['footprint_mm2']:.0f} mm² footprint; it is likely to wobble or come off the bed.",
            rule="fdm.slenderness_max", value=best["slenderness"], hint="Lay it down, widen the base, or add a brim.")
    elif best["bed_contact_fraction"] < lim("fdm.bed_contact_min_fraction") and best["height_mm"] > 5.0:
        add("warning", "small_bed_contact",
            f"only {best['footprint_mm2']:.0f} mm² touches the bed with {best['up']} up, {best['bed_contact_fraction']:.0%} of the part's outline; "
            f"the first layer will not hold it.", rule="fdm.bed_contact_min_fraction", value=best["bed_contact_fraction"],
            hint="Give it a flat face to stand on, or plan for a raft and support.")

    # ---- walls
    wall_lim = max(lim("fdm.wall_min_mm"), lim("fdm.wall_beads") * nozzle) if "fdm.wall_min_mm" not in lim.over else lim("fdm.wall_min_mm")
    wt = G.wall_thickness(sm)
    thin = wt < wall_lim - 1e-6
    out["min_wall_mm"] = round(float(wt[np.isfinite(wt)].min()), 2) if np.isfinite(wt).any() else None
    out["typical_wall_mm"] = round(2 * c.shape.volume / max(float(sm.mesh.area), 1e-9), 2)
    if thin.sum() >= 2:
        pts, vals = sm.pts[thin], wt[thin]
        sel = G.spread(pts, vals, k=6, min_sep=4.0)
        add("error", "wall_too_thin_to_print",
            f"wall as thin as {vals.min():.2f} mm at {G.xyz(pts[sel[0]])} (about {sm.w[thin].sum():.0f} mm² of surface under {wall_lim:g} mm, "
            f"two beads of a {nozzle:g} mm nozzle): the slicer drops it or prints one fragile bead.",
            rule="fdm.wall_min_mm", value=float(vals.min()), limit_mm=wall_lim, at=[G.xyz(pts[i]) for i in sel],
            hint=f"Thicken to at least {wall_lim:g} mm (three beads, {1.5 * wall_lim:g} mm, for anything that carries load).")
    elif out["typical_wall_mm"] < wall_lim:
        add("error", "wall_too_thin_to_print", f"typical wall about {out['typical_wall_mm']:.2f} mm, under {wall_lim:g} mm.",
            rule="fdm.wall_min_mm", value=out["typical_wall_mm"])

    # ---- small holes and pins
    small = [hl for hl in holes if hl.diameter < lim("fdm.hole_min_mm") - 1e-6]
    if small:
        hl = min(small, key=lambda q: q.diameter)
        add("warning", "hole_too_small_to_print",
            f"{len(small)} hole(s) under {lim('fdm.hole_min_mm'):g} mm (smallest {hl.diameter:g} mm at {G.xyz(hl.origin)}): they print undersize or close up.",
            rule="fdm.hole_min_mm", value=hl.diameter, at=[G.xyz(q.origin) for q in small[:6]],
            hint="Print a pilot dimple and drill it, or open it up.")
    pins = [cy for cy in cyls if not cy.concave and cy.angle >= 180 and 2 * cy.radius < lim("fdm.feature_min_mm") - 1e-6
            and (cy.hi - cy.lo) > cy.radius]
    if pins:
        cy = min(pins, key=lambda q: q.radius)
        add("warning", "feature_too_small_to_print",
            f"{len(pins)} pin(s) or boss(es) under {lim('fdm.feature_min_mm'):g} mm across (smallest {2 * cy.radius:g} mm at {G.xyz(cy.mid)}): "
            f"printed from perimeters alone, they snap off.", rule="fdm.feature_min_mm", value=2 * cy.radius,
            at=[G.xyz(q.mid) for q in pins[:6]], hint="Thicken, add a root fillet, or print a hole and press in a metal pin.")
    on_bed_holes = [hl for hl in holes if abs(abs(hl.axis @ up) - 1) < 1e-3
                    and (hl.origin @ up - hl.depth / 2) - best["_zmin"] < 0.3]
    out["holes_opening_on_bed"] = len(on_bed_holes)
    if on_bed_holes:
        add("info", "elephant_foot",
            f"{len(on_bed_holes)} hole(s) open onto the bed face ({best['up']} up): the squashed first layer makes them and the outline "
            f"about 0.1-0.3 mm tight there.", at=[G.xyz(q.origin) for q in on_bed_holes[:6]],
            source=lim.rule("fdm.overhang_angle_deg").source_text,
            hint="Put a 0.4 mm 45-degree chamfer on edges and hole mouths that touch the bed if the fit matters.")

    # ---- threads in plastic
    tapped = G.tapped_holes(design, c, sm)
    if tapped:
        thin_boss = []
        for tp in tapped:
            a = tp["dir"]
            u = np.cross(a, [1.0, 0, 0] if abs(a[0]) < 0.9 else [0, 1.0, 0])
            u /= np.linalg.norm(u)
            v = np.cross(a, u)
            dirs = np.array([math.cos(k * math.pi / 6) * u + math.sin(k * math.pi / 6) * v for k in range(12)])
            dist, _ = G.ray_hits(sm.tris, np.repeat(tp["mid"][None], 12, axis=0), dirs)
            wall = float(dist.min()) - tp["d"] / 2
            tp["wall"] = wall
            if wall < lim("fdm.thread_wall_d_ratio") * tp["d"] - 1e-6:
                thin_boss.append(tp)
        sizes = sorted({tp["d"] for tp in tapped})
        ins = ", ".join(f"M{d:g}: {HEAT_SET[d][0]:g} mm hole x {HEAT_SET[d][1]:g} mm deep" for d in sizes if d in HEAT_SET)
        add("info", "printed_threads",
            f"{len(tapped)} screw(s) thread straight into the print (M{', M'.join(f'{d:g}' for d in sizes)}). Threads cut in printed plastic strip "
            f"after a few assemblies.", at=[tp["at"] for tp in tapped[:6]], source=lim.rule("fdm.thread_wall_d_ratio").source_text,
            hint="For joints that are opened again use heat-set inserts" + (f" (typical pilot holes, check the insert's datasheet: {ins})" if ins else "")
                 + ", or a captive nut; self-tapping screws for plastic are fine for assemble-once joints.")
        out["threads_in_print"] = len(tapped)
        if thin_boss:
            tp = min(thin_boss, key=lambda q: q["wall"] / q["d"])
            add("warning", "thin_wall_around_thread",
                f"{len(thin_boss)} threaded hole(s) with less plastic around them than the screw's diameter (least {tp['wall']:.1f} mm around "
                f"an M{tp['d']:g} at {tp['at']}): the boss bulges or splits when the screw or insert goes in.",
                rule="fdm.thread_wall_d_ratio", value=tp["wall"], limit_mm=tp["d"], at=[q["at"] for q in thin_boss[:6]],
                hint=f"Leave at least {tp['d']:g} mm of wall all round (boss diameter at least three screw diameters).")

    # ---- layers
    worst = max(((abs(f @ up), nm) for nm, f in loads), default=(0.0, None))
    if worst[0] > lim("fdm.layer_load_fraction") + 1e-9:
        better = min(rows.values(), key=lambda q: (q["load_along_build_axis"], q["score"]))
        add("warning", "load_across_layers",
            f"load case '{worst[1]}' acts {worst[0]:.0%} along the build direction ({best['up']} up): it pulls the layers apart, the weakest "
            f"direction of a printed part, and the FEA assumes the material is equally strong every way.",
            rule="fdm.layer_load_fraction", value=worst[0],
            hint=f"Print with {better['up']} up so the load runs along the layers, or add a through bolt that puts the layers in compression."
                 " (Direction only: a bending load across a tall part also loads the layers and is not detected.)")

    # ---- warp (rule of thumb) and a rough cost
    from .warp import warp_risk

    out["warp"] = warp_risk(design, name, max(best["lateral_mm"] or [0.0]), r)
    vol_mm3 = float(c.shape.volume)
    shell = min(vol_mm3, float(sm.mesh.area) * 1.2)
    deposited = shell + 0.2 * (vol_mm3 - shell)
    from ..model import MATERIALS

    rho = MATERIALS[c.material].density if c.material in MATERIALS else 1250.0
    mass_g = deposited * 1e-9 * rho * 1000
    out["estimate"] = {"filament_g": round(mass_g, 1), "print_hours": round(deposited / PRINT_FLOW_MM3_S / 3600 * 1.25 + 0.05, 2),
                       "material_usd": round(mass_g / 1000 * FILAMENT_USD_KG, 2),
                       "basis": "estimate: 1.2 mm walls, 20% infill, 5 mm3/s, no support material counted"}
    return out
