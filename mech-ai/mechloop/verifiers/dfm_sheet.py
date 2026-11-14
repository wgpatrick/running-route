"""Parts cut from sheet or plate in 2D (laser, waterjet, router), and bent sheet.

A flat cut part must be one thickness with every edge square to the sheet: the check finds the sheet
plane from the part's own faces, confirms nothing is stepped or pocketed, projects the top face to an
exact 2D profile and judges that profile: holes against thickness, webs, slots and necks, inside corners
against the cutter, overall size against the sheet. The same profile is what the shop needs, so it is
also written out as a DXF (`export_flat_patterns`).

A bent part is recognised by pairs of coaxial cylinders one thickness apart; its bends, flanges and
holes near bends are judged. It is not unfolded: no DXF is written for it.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from build123d import GeomType
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Line
from OCP.TopAbs import TopAbs_REVERSED

from . import dfm_geom as G
from .dfm_rules import SOURCES, Limits

METHODS = ("laser", "waterjet", "router")


# -------------------------------------------------------------------------------------- the plate
def plate_of(shape, frame: np.ndarray, sm: G.Sampled) -> dict | None:
    """If the part is a plate (every face square to one direction or parallel to it), describe it:
    the direction, its thickness, the levels flat faces sit at, countersinks. Of the directions that
    work the thinnest is the plate's. None for a block."""
    faces = list(shape.faces())
    lo, hi = G.extents(sm, frame)
    size = hi - lo
    good = []
    for k in range(3):
        a = frame[k]
        ok, cones = True, 0
        for f in faces:
            if f.geom_type == GeomType.PLANE:
                v = abs(G._vec(f.normal_at(f.center())) @ a)
                if 0.02 < v < 0.9995:
                    ok = False
                    break
            elif f.geom_type == GeomType.CYLINDER:
                d = G._vec(BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Direction())
                if abs(d @ a) < 0.9995:
                    ok = False
                    break
            elif f.geom_type == GeomType.CONE:
                d = G._vec(BRepAdaptor_Surface(f.wrapped).Cone().Axis().Direction())
                if abs(d @ a) < 0.9995:
                    ok = False
                    break
                cones += 1
            else:
                ok = False
                break
        if ok:
            good.append((size[k], k, cones))
    if not good:
        return None
    t, k, cones = min(good)
    others = [size[i] for i in range(3) if i != k]
    if not (t <= 30.0 and t <= 0.5 * max(others)):
        return None
    a = frame[k]
    caps = []
    for f in faces:
        if f.geom_type == GeomType.PLANE:
            n = G._vec(f.normal_at(f.center()))
            if abs(n @ a) > 0.9995:
                caps.append((round(float(G._vec(f.center()) @ a), 3), float(n @ a), f))
    top, bot = hi[k], lo[k]
    steps = [(lvl, s, f) for lvl, s, f in caps if abs(lvl - top) > 0.01 and abs(lvl - bot) > 0.01]
    return {"k": k, "axis": a, "thickness": float(t), "top": float(top), "bottom": float(bot), "size": size,
            "caps": caps, "steps": steps, "countersinks": cones,
            "u": frame[(k + 1) % 3], "v": frame[(k + 2) % 3]}


def _wire_points(wire, face, u, v) -> np.ndarray:
    """A wire as a closed 2D polyline in the (u, v) plane: straight edges exactly, arcs every 3 degrees."""
    pts = []
    ex = BRepTools_WireExplorer(wire.wrapped, face.wrapped)
    while ex.More():
        e = ex.Current()
        c = BRepAdaptor_Curve(e)
        a, b = c.FirstParameter(), c.LastParameter()
        if c.GetType() == GeomAbs_Line:
            n = 2
        elif c.GetType() == GeomAbs_Circle:
            n = max(3, int(math.ceil(abs(b - a) / math.radians(3.0))) + 1)
        else:
            n = 33
        ts = np.linspace(a, b, n)
        if e.Orientation() == TopAbs_REVERSED:
            ts = ts[::-1]
        for t in ts[:-1]:
            p = c.Value(float(t))
            q = np.array([p.X(), p.Y(), p.Z()])
            pts.append((q @ u, q @ v))
        ex.Next()
    return np.array(pts)


def profile_of(plate: dict):
    """The plate's outline with its holes as a shapely polygon in the plate's own (u, v) coordinates,
    taken from its top face(s)."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    polys = []
    for lvl, s, f in plate["caps"]:
        if abs(lvl - plate["top"]) > 0.01:
            continue
        outer = _wire_points(f.outer_wire(), f, plate["u"], plate["v"])
        inner = [_wire_points(w, f, plate["u"], plate["v"]) for w in f.inner_wires()]
        if len(outer) >= 3:
            p = Polygon(outer, [h for h in inner if len(h) >= 3])
            polys.append(p if p.is_valid else p.buffer(0))
    if not polys:
        return None
    out = unary_union(polys)
    return out


def _to_world(plate: dict, x: float, y: float, level: float | None = None) -> list[float]:
    lvl = 0.5 * (plate["top"] + plate["bottom"]) if level is None else level
    return G.xyz(x * plate["u"] + y * plate["v"] + lvl * plate["axis"])


def _polys(geom) -> list:
    if geom is None or geom.is_empty:
        return []
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


def _width(poly) -> float:
    """Narrowest dimension of a region: the diameter of the largest circle that fits in it."""
    import shapely

    try:
        seg = shapely.maximum_inscribed_circle(poly, tolerance=0.01)
        return 2.0 * float(seg.length)
    except Exception:
        mrr = poly.minimum_rotated_rectangle
        xs, ys = mrr.exterior.coords.xy
        return float(min(math.dist((xs[0], ys[0]), (xs[1], ys[1])), math.dist((xs[1], ys[1]), (xs[2], ys[2]))))


def sharp_inside_corners_2d(profile, radius: float) -> list[tuple[float, float]]:
    """Where a round cutter of this radius cannot follow the profile: inside corners sharper than it.
    Rolling a disc of that radius around the outside of the material leaves the corners it cannot enter."""
    if radius <= 0:
        return []
    closed = profile.buffer(radius, quad_segs=24).buffer(-radius, quad_segs=24)
    left = closed.difference(profile)
    floor = 0.35 * (1 - math.pi / 4) * radius * radius        # a square corner leaves (1 - pi/4) r^2
    return [(p.representative_point().x, p.representative_point().y) for p in _polys(left) if p.area > floor]


def check_flat(r, c, plate: dict, sm, holes: list, lim: Limits, tapped: list, process: str) -> dict:
    """Judge a flat cut part. Adds findings to r, returns the part's metrics row."""
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree

    name, t = c.name, plate["thickness"]
    method = lim.option("sheet", "method", "laser")
    if method not in METHODS:
        raise ValueError(f"{name}: sheet method {method!r}; use one of {METHODS}")
    strict = bool(lim.shop.get("strict"))
    row = {"form": "flat", "thickness_mm": round(t, 3), "sheet_normal": "XYZ"[plate["k"]], "cut_method": method,
           "shop": lim.shop_name}

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

    # ---- one thickness, cut straight through
    if plate["steps"]:
        worst = max(plate["steps"], key=lambda s: s[2].area)
        at = [G.xyz(G._vec(s[2].center())) for s in sorted(plate["steps"], key=lambda s: -s[2].area)[:6]]
        depth = plate["top"] - worst[0] if worst[1] > 0 else worst[0] - plate["bottom"]
        add("error", "not_2d_profile",
            f"{len(plate['steps'])} face(s) part-way through the {t:g} mm sheet (largest {worst[2].area:.0f} mm², {depth:.2f} mm deep, at {at[0]}): "
            f"pockets, counterbores and steps cannot be cut by a {method}, which cuts full depth only.",
            at=at, value=round(depth, 3), limit=0.0, source=SOURCES["scs-cutting"],
            hint="Make the feature a through cut, move it to a second stacked sheet, or make the part process='machined'.")
        row["through_cut_only"] = False
    else:
        row["through_cut_only"] = True
    if plate["countersinks"]:
        rid = "sheet.countersink_min_thickness_mm"
        thin = t < lim(rid) - 1e-6
        add("error" if (thin and strict) else "warning", "secondary_op_countersink",
            f"{plate['countersinks']} countersink(s): a second operation after cutting (model plain through holes in the cut file)"
            + (f"; the sheet is {t:g} mm and countersinking needs at least {lim(rid):g} mm." if thin else "."),
            rule=rid, value=t, hint="Use button- or cap-head screws on a plain hole, or thicker stock.")

    # ---- stock
    stock = lim.stock("sheet_stock", c.material)
    near = min(stock, key=lambda s: abs(s - t)) if stock else None
    row["stock_mm"] = near
    if not stock:
        add("warning", "material_not_stocked", f"{lim.shop_name} lists no sheet stock for {c.material}.",
            hint="Choose a stocked material or another shop.")
    elif abs(near - t) > 0.05:
        add("error" if process == "sheet" else "warning", "non_stock_thickness",
            f"{t:.2f} mm thick; {c.material} sheet at {lim.shop_name} comes in {', '.join(f'{s:g}' for s in stock)} mm "
            f"(nearest {near:g}). A cut part cannot be any other thickness.",
            value=round(t, 3), limit=near, source=SOURCES[lim.shop.get("source", "own")],
            hint=f"Model the part at {near:g} mm, and re-check what it mates with.")
    for rid, bad, word in (("sheet.thickness_min_mm", t < lim("sheet.thickness_min_mm") - 1e-9, "thinner than"),
                           ("sheet.thickness_max_laser_mm", method == "laser" and t > lim("sheet.thickness_max_laser_mm") + 1e-9, "thicker than"),
                           ("sheet.thickness_limit_mm", t > lim("sheet.thickness_limit_mm") + 1e-9, "past")):
        if bad and not (rid == "sheet.thickness_max_laser_mm" and t > lim("sheet.thickness_limit_mm")):
            add(lim.severity(rid), "sheet_thickness", f"{t:g} mm is {word} the {lim(rid):g} mm {lim.rule(rid).note.split(';')[0]}.",
                rule=rid, value=t, hint="Change thickness, or make it a machined plate.")

    profile = profile_of(plate)
    if profile is None or profile.is_empty:
        add("warning", "profile_not_read", "could not read a flat profile from the top face; the 2D checks were not run.")
        return row
    parts = _polys(profile)
    P = max(parts, key=lambda p: p.area)
    if len(parts) > 1:
        add("error", "not_one_piece", f"the top face is {len(parts)} separate regions; a cut part is one piece.")

    # ---- size
    minx, miny, maxx, maxy = P.bounds
    mrr = P.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    sides = sorted((math.dist((xs[0], ys[0]), (xs[1], ys[1])), math.dist((xs[1], ys[1]), (xs[2], ys[2]))), reverse=True)
    long_, short_ = sides
    row.update({"flat_size_mm": [round(long_, 1), round(short_, 1)], "cut_length_mm": round(P.length, 0),
                "pierces": 1 + len(P.interiors)})
    sizes = lim.shop.get("cut_sizes", {}).get(c.material)
    if sizes and near is not None:
        _, mx, mn = min(sizes, key=lambda s_: abs(s_[0] - near))
        if long_ > mx[0] + 1e-6 or short_ > mx[1] + 1e-6:
            add("error", "too_big_to_cut", f"{long_:.0f} x {short_:.0f} mm is larger than {lim.shop_name}'s {mx[0]:.0f} x {mx[1]:.0f} mm "
                f"limit for {near:g} mm {c.material}.", value=round(long_, 1), limit=mx[0], source=lim.rule("sheet.min_long_mm").source_text,
                hint="Split the part and join the pieces, or use another shop.")
        if long_ < mn[0] - 1e-6 or short_ < mn[1] - 1e-6:
            add("error", "too_small_to_cut", f"{long_:.1f} x {short_:.1f} mm is smaller than {lim.shop_name}'s {mn[0]:g} x {mn[1]:g} mm "
                f"minimum for {near:g} mm {c.material}.", value=round(short_, 2), limit=mn[1], source=lim.rule("sheet.min_long_mm").source_text,
                hint="Leave the part attached to a carrier strip with break-off tabs, or make it larger.")
    else:
        if long_ > lim("sheet.max_long_mm") or short_ > lim("sheet.max_short_mm"):
            add("warning", "too_big_to_cut", f"{long_:.0f} x {short_:.0f} mm does not fit a standard "
                f"{lim('sheet.max_long_mm'):.0f} x {lim('sheet.max_short_mm'):.0f} mm sheet.", rule="sheet.max_long_mm", value=long_,
                hint="Split the part, or find a shop with a larger bed.")
        if long_ < lim("sheet.min_long_mm") - 1e-6 or short_ < lim("sheet.min_short_mm") - 1e-6:
            add("warning", "small_part_needs_tabs", f"{long_:.1f} x {short_:.1f} mm is small enough to drop through the cutting bed or "
                f"tip into the path of the head (under {lim('sheet.min_long_mm'):g} x {lim('sheet.min_short_mm'):g} mm).",
                rule="sheet.min_short_mm", value=short_,
                hint="Tab it to a carrier strip or a neighbouring part, or make it at least that size.")

    # ---- holes and cut-outs
    kerf = lim(f"sheet.kerf_{method}_mm")
    if method == "laser":
        hard, hard_rule = lim("sheet.hole_min_t_ratio") * t, "sheet.hole_min_t_ratio"
    elif method == "waterjet":
        hard, hard_rule = lim("sheet.hole_min_waterjet_mm"), "sheet.hole_min_waterjet_mm"
    else:
        hard, hard_rule = lim("sheet.hole_min_router_mm"), "sheet.hole_min_router_mm"
    soft = lim("sheet.hole_recommended_t_ratio") * t
    rings = []
    for ring in P.interiors:
        poly = Polygon(ring)
        cx, cy = poly.centroid.x, poly.centroid.y
        round_ = None
        for h in holes:
            if abs(abs(h.axis @ plate["axis"]) - 1) < 1e-4 and math.hypot(h.origin @ plate["u"] - cx, h.origin @ plate["v"] - cy) < 0.02 \
                    and abs(poly.area - math.pi * h.diameter ** 2 / 4) < 0.02 * poly.area + 0.01:
                round_ = h.diameter
                break
        w = round_ if round_ is not None else _width(poly)
        rings.append({"poly": poly, "c": (cx, cy), "w": w, "round": round_ is not None})
    too_small = [x for x in rings if x["w"] < hard - 1e-6]
    smallish = [x for x in rings if hard - 1e-6 <= x["w"] < soft - 1e-6]
    if too_small:
        x = min(too_small, key=lambda q: q["w"])
        add("error", "hole_too_small_to_cut",
            f"{len(too_small)} hole(s) or cut-out(s) smaller than a {method} can cut in {t:g} mm (smallest {x['w']:.2f} mm at "
            f"{_to_world(plate, *x['c'])}, minimum {hard:.2f} mm).", rule=hard_rule, value=x["w"], limit_mm=round(hard, 3),
            at=[_to_world(plate, *q["c"]) for q in sorted(too_small, key=lambda q: q["w"])[:6]],
            hint=f"Open them to at least {hard:.2f} mm, or leave a centre mark and drill after cutting.")
    if smallish:
        x = min(smallish, key=lambda q: q["w"])
        add("warning", "hole_smaller_than_thickness",
            f"{len(smallish)} hole(s) or cut-out(s) narrower than the {t:g} mm sheet (smallest {x['w']:.2f} mm at {_to_world(plate, *x['c'])}): "
            f"they cut, but taper and lose accuracy.", rule="sheet.hole_recommended_t_ratio", value=x["w"], limit_mm=round(soft, 3),
            at=[_to_world(plate, *q["c"]) for q in sorted(smallish, key=lambda q: q["w"])[:6]],
            hint=f"Make them at least {soft:g} mm, or drill or ream them after cutting if the size matters.")
    row["holes"] = len(rings)
    row["smallest_hole_mm"] = round(min((x["w"] for x in rings), default=0.0), 2) or None

    # ---- webs: hole to edge, hole to hole
    edge_lim = lim("sheet.hole_to_edge_t_ratio") * t
    near_edge = []
    ext = P.exterior
    for x in rings:
        d = ext.distance(x["poly"].exterior)
        x["edge"] = d
        if d < edge_lim - 1e-6:
            near_edge.append(x)
    if near_edge:
        x = min(near_edge, key=lambda q: q["edge"])
        burnt = x["edge"] <= kerf
        add("error" if burnt else "warning", "hole_too_close_to_edge",
            f"{len(near_edge)} hole(s) with less than {edge_lim:g} mm of material to the edge (least {x['edge']:.2f} mm at "
            f"{_to_world(plate, *x['c'])})" + (f": that is no more than the {kerf:g} mm kerf, so nothing is left." if burnt else
                                               ": the web overheats and distorts, and tears if the part is bent or loaded."),
            rule="sheet.hole_to_edge_t_ratio", value=x["edge"], limit_mm=round(edge_lim, 3),
            at=[_to_world(plate, *q["c"]) for q in sorted(near_edge, key=lambda q: q["edge"])[:6]],
            hint=f"Move the hole in, or widen the part there, to leave at least {edge_lim:g} mm.")
    close = []
    if len(rings) > 1:
        geoms = [x["poly"] for x in rings]
        tree = STRtree(geoms)
        reach = lim("sheet.hole_spacing_t_ratio") * t
        for i, x in enumerate(rings):
            for j in tree.query(x["poly"].buffer(reach)):
                j = int(j)
                if j <= i:
                    continue
                y = rings[j]
                need = reach if (x["round"] and y["round"]) else lim("sheet.feature_width_t_ratio") * t
                d = x["poly"].distance(y["poly"])
                if d < need - 1e-6:
                    close.append((d, need, x, y))
    if close:
        d, need, x, y = min(close, key=lambda q: q[0] / q[1])
        mid = ((x["c"][0] + y["c"][0]) / 2, (x["c"][1] + y["c"][1]) / 2)
        add("error" if d <= kerf else "warning", "holes_too_close",
            f"{len(close)} pair(s) of holes or cut-outs with too little material between them (least {d:.2f} mm at {_to_world(plate, *mid)}, "
            f"wanted {need:g} mm = {need / t:g} x thickness).", rule="sheet.hole_spacing_t_ratio", value=d, limit_mm=round(need, 3),
            at=[_to_world(plate, (a["c"][0] + b["c"][0]) / 2, (a["c"][1] + b["c"][1]) / 2) for _, _, a, b in sorted(close, key=lambda q: q[0])[:6]],
            hint="Space them out, or merge them into one cut-out.")

    # ---- necks and tabs (material narrower than the limit), slots and notches (gaps narrower than the limit)
    wmin = lim("sheet.feature_width_t_ratio") * t
    solid = Polygon(P.exterior)
    opened = P.buffer(-wmin / 2 * 0.98, quad_segs=16).buffer(wmin / 2 * 0.98, quad_segs=16)
    thin = [p for p in _polys(P.difference(opened)) if p.area > 0.2 * wmin * wmin and _long(p) > 1.2 * wmin]
    # a hole near an edge already has its own finding: do not say it twice
    thin = [p for p in thin if not any(x["poly"].distance(p) < 0.05 and (x.get("edge", 9e9) < edge_lim or any(x is q[2] or x is q[3] for q in close))
                                       for x in rings)]
    if thin:
        ws = sorted(((_width(p), p) for p in thin), key=lambda q: q[0])
        w0, p0 = ws[0]
        add("warning", "thin_feature",
            f"{len(thin)} tab(s) or neck(s) narrower than {wmin:g} mm, the sheet's thickness (narrowest about {w0:.2f} mm at "
            f"{_to_world(plate, p0.representative_point().x, p0.representative_point().y)}): they warp from the heat of the cut and bend in handling.",
            rule="sheet.feature_width_t_ratio", value=w0, limit_mm=round(wmin, 3),
            at=[_to_world(plate, p.representative_point().x, p.representative_point().y) for _, p in ws[:6]],
            hint=f"Widen to at least {wmin:g} mm.")
    slot_lim = max(wmin, kerf)
    closed = solid.buffer(slot_lim / 2 * 0.98, quad_segs=16).buffer(-slot_lim / 2 * 0.98, quad_segs=16)
    gaps = [p for p in _polys(closed.difference(solid)) if p.area > 0.2 * slot_lim * slot_lim and _long(p) > 1.2 * slot_lim]
    if gaps:
        ws = sorted(((_width(p), p) for p in gaps), key=lambda q: q[0])
        w0, p0 = ws[0]
        under = w0 < kerf
        add("error" if under else "warning", "narrow_slot",
            f"{len(gaps)} slot(s) or notch(es) in the outline narrower than {slot_lim:g} mm (narrowest about {w0:.2f} mm at "
            f"{_to_world(plate, p0.representative_point().x, p0.representative_point().y)})"
            + (f": narrower than the {kerf:g} mm {method} kerf, it cannot be cut." if under else ": the cut is ragged and the slot closes up with heat."),
            rule=f"sheet.kerf_{method}_mm" if under else "sheet.feature_width_t_ratio", value=w0, limit_mm=round(kerf if under else slot_lim, 3),
            at=[_to_world(plate, p.representative_point().x, p.representative_point().y) for _, p in ws[:6]],
            hint=f"Widen to at least {slot_lim:g} mm.")

    # ---- inside corners against the cutter
    rid = f"sheet.inside_radius_{method}_mm"
    rad = lim(rid)
    corners = sharp_inside_corners_2d(P, rad * 0.98) if rad >= 0.3 else []
    row["sharp_inside_corners"] = len(corners) if rad >= 0.3 else len(sharp_inside_corners_2d(P, 0.5))
    row["inside_corner_radius_left_mm"] = rad
    if corners:
        add("warning", "sharp_inside_corner",
            f"{len(corners)} inside corner(s) drawn sharper than the {rad:g} mm radius a {method} leaves (first at {_to_world(plate, *corners[0])}); "
            f"a square mating part will not seat.", rule=rid, value=0.0,
            at=[_to_world(plate, *p) for p in corners[:6]],
            hint=f"Draw a radius of at least {rad:g} mm, add dog-bone reliefs, or radius the mating part.")

    # ---- how much is cut away
    removed = 1.0 - P.area / max(solid.area, 1e-9)
    row["cut_away_fraction"] = round(removed, 2)
    if removed > lim("sheet.removed_max_fraction"):
        add("warning", "mostly_holes", f"{removed:.0%} of the blank is cut away inside the outline; grilles this open shift, warp or break while "
            f"being cut.", rule="sheet.removed_max_fraction", value=removed, hint="Leave more material, or fewer larger openings.")

    # ---- tapped holes: a second operation
    if tapped:
        sizes_ = sorted({tp["d"] for tp in tapped})
        rid = "sheet.tap_min_thickness_mm"
        msg = f"{len(tapped)} tapped hole(s) (M{', M'.join(f'{d:g}' for d in sizes_)}): tapping is a second operation after cutting"
        sev = "warning"
        tr = lim.shop.get("tap_range_al") if c.material.startswith("al") else None
        out_of_range = []
        if tr:
            band = [rng for thk, rng in tr if thk <= t + 0.05]
            if band:
                lo_, hi_ = band[-1]
                out_of_range = [d for d in sizes_ if d < lo_ or d > hi_]
            else:
                out_of_range = sizes_
        if t < lim(rid) - 1e-6:
            msg += f"; {t:g} mm is thinner than the {lim(rid):g} mm at which tapping is offered"
            sev = "error" if strict else "warning"
        if out_of_range:
            msg += f"; M{', M'.join(f'{d:g}' for d in out_of_range)} is outside what {lim.shop_name} taps in {t:g} mm"
            sev = "error"
        thin_thread = [tp for tp in tapped if t < 3 * tp["pitch"]]
        if thin_thread:
            msg += f"; {len(thin_thread)} have fewer than three threads in {t:g} mm of sheet"
        add(sev, "secondary_op_tapping", msg + ".", rule=rid, value=t, at=[tp["at"] for tp in tapped[:6]],
            hint="Cut the tap-drill size hole and order tapping, or use a rivet nut, a press-in nut or a through bolt with a nut.")
        row["tapped_holes"] = len(tapped)
    row["_profile"] = P
    return row


def _long(poly) -> float:
    mrr = poly.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    return float(max(math.dist((xs[0], ys[0]), (xs[1], ys[1])), math.dist((xs[1], ys[1]), (xs[2], ys[2]))))


# -------------------------------------------------------------------------------------- bent sheet
def modal_thickness(sm: G.Sampled) -> tuple[float, float] | None:
    """The wall thickness most of the surface has, and the share of the surface that has it."""
    wt = G.wall_thickness(sm)
    ok = np.isfinite(wt)
    if not ok.any():
        return None
    bins = np.round(wt[ok] / 0.02).astype(int)
    vals, inv = np.unique(bins, return_inverse=True)
    weight = np.bincount(inv.reshape(-1), weights=sm.w[ok])
    t = float(vals[int(np.argmax(weight))] * 0.02)
    share = float(weight.max() / sm.w.sum())
    if t <= 0 or share < 0.45:
        return None
    sel = np.abs(wt[ok] - t) < 0.03
    return float(np.average(wt[ok][sel], weights=sm.w[ok][sel])), share


def bent_sheet(shape, sm: G.Sampled, cyls: list) -> dict | None:
    """Recognise a bent sheet part: an inside and an outside cylinder about one axis whose radii differ
    by the thickness the flat faces are apart. Returns thickness and bends, or None."""
    mt = modal_thickness(sm)
    if mt is None:
        return None
    t, share = mt
    bends = []
    for ci in cyls:
        if not ci.concave or ci.angle > 200:
            continue
        for co in cyls:
            if co.concave or abs(co.radius - ci.radius - t) > 0.03 or not G._same_axis(ci.origin, ci.axis, co.origin, co.axis):
                continue
            if abs(co.angle - ci.angle) > 3.0:
                continue
            bends.append({"inside": ci, "outside": co, "radius": ci.radius, "angle": ci.angle,
                          "length": ci.hi - ci.lo, "origin": ci.origin, "axis": ci.axis})
            break
    if not bends:
        return None
    return {"thickness": t, "skin_share": share, "bends": bends}


def check_bent(r, c, shape, bent: dict, sm, holes: list, lim: Limits) -> dict:
    name, t = c.name, bent["thickness"]
    row = {"form": "bent", "thickness_mm": round(t, 3), "bends": len(bent["bends"]), "shop": lim.shop_name,
           "flat_pattern": "not unfolded: no DXF written for a bent part"}

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

    stock = lim.stock("sheet_stock", c.material)
    near = min(stock, key=lambda s: abs(s - t)) if stock else None
    row["stock_mm"] = near
    if stock and abs(near - t) > 0.05:
        add("error", "non_stock_thickness", f"{t:.2f} mm thick; {c.material} sheet at {lim.shop_name} comes in "
            f"{', '.join(f'{s:g}' for s in stock)} mm (nearest {near:g}).", value=round(t, 3), limit=near,
            hint=f"Model the part at {near:g} mm.")
    if t > lim("sheet.bend_thickness_max_mm") + 1e-6:
        add("warning", "thick_to_bend", f"{t:g} mm is thicker than the {lim('sheet.bend_thickness_max_mm'):g} mm usually bent on a press brake.",
            rule="sheet.bend_thickness_max_mm", value=t, hint="Use thinner sheet with a stiffening flange, or weld or bolt two plates.")
    shop_bend = (lim.shop.get("bend") or {}).get(c.material)
    if lim.shop.get("bend") is not None and shop_bend is None:
        add("error", "material_not_bent", f"{lim.shop_name} does not bend {c.material}"
            + (" (6061-T6 cracks on a tight bend; 5052 is the aluminium that bends)." if c.material == "al6061" else "."),
            hint="Use al5052, steel or stainless304 for bent parts, or bolt flat plates together.")
    elif c.material == "al6061":
        add("warning", "alloy_cracks_when_bent", "6061-T6 cracks when bent to a tight radius; shops bend 5052 instead "
            "(SendCutSend offers no bending in 6061).", hint="Use material='al5052', or a radius of several thicknesses and ask the shop.",
            source="https://sendcutsend.com/materials/processing-min-max/")
    shop_row = None
    if shop_bend and near is not None:
        key = min(shop_bend, key=lambda k_: abs(k_ - near))
        if abs(key - near) < 0.06:
            shop_row = shop_bend[key]
        else:
            add("error", "thickness_not_bent", f"{lim.shop_name} does not bend {near:g} mm {c.material} (it bends up to {max(shop_bend):g} mm).")

    faces = list(shape.faces())
    planes = [(f, G._vec(f.normal_at(f.center()))) for f in faces if f.geom_type == GeomType.PLANE]
    short, tight, wide, differs, long_bend, near_hole = [], [], [], [], [], []
    for b in bent["bends"]:
        a, o, rin = b["axis"], b["origin"], b["radius"]
        mid = o + a * 0.5 * (b["inside"].lo + b["inside"].hi)
        if rin < lim("sheet.bend_radius_t_ratio") * t - 1e-6 and not (shop_row and abs(rin - shop_row[0]) <= 0.15):
            tight.append((rin, G.xyz(b["inside"].mid)))
        if rin > lim("sheet.bend_radius_max_t_ratio") * t:
            wide.append((rin, G.xyz(b["inside"].mid)))
        if shop_row:
            if abs(rin - shop_row[0]) > 0.15:
                differs.append((rin, G.xyz(b["inside"].mid)))
            if b["length"] > shop_row[1] + 1e-6:
                long_bend.append((b["length"], G.xyz(b["inside"].mid)))
        # the flanges: flat faces tangent to the inside cylinder (their plane is one inside radius from the axis)
        for f, n in planes:
            if abs(n @ a) > 0.02:
                continue
            dist = abs((G._vec(f.center()) - o) @ n)
            if abs(dist - rin) > 0.03:
                continue
            vs = np.array([[v.X, v.Y, v.Z] for v in f.vertices()])
            rel = vs - o
            rel = rel - np.outer(rel @ a, a)
            fdir = np.cross(a, n)
            along = rel @ fdir
            if np.min(np.abs(along)) > 0.05:
                continue                                 # this face does not start at the bend's tangent line
            # the face must also overlap the bend along its axis
            h = (vs - o) @ a
            if h.max() < b["inside"].lo + 0.05 or h.min() > b["inside"].hi - 0.05:
                continue
            reach = along[np.argmax(np.abs(along))]
            sgn = 1.0 if reach > 0 else -1.0
            length_tan = float(abs(reach))
            setback = (rin + t) * math.tan(math.radians(min(b["angle"], 179.0)) / 2)
            height = length_tan + setback
            need = lim("sheet.flange_min_t_ratio") * t + rin
            shop_need = shop_row[2] if shop_row else None
            far = o + a * ((vs - o) @ a).mean() + fdir * reach + n * dist * np.sign((G._vec(f.center()) - o) @ n)
            if height < max(need, shop_need or 0.0) - 1e-6:
                short.append((height, max(need, shop_need or 0.0), G.xyz(far), shop_need is not None and height < shop_need - 1e-6))
            for hl in holes:
                if abs(abs(hl.axis @ n) - 1) > 1e-3:
                    continue
                ho = hl.origin - o
                if abs(abs(ho @ n) - (rin + t / 2)) > t:      # the hole is in this flange's sheet
                    continue
                if not (b["inside"].lo - hl.diameter <= ho @ a <= b["inside"].hi + hl.diameter):
                    continue
                d_tan = sgn * ((ho - (ho @ a) * a) @ fdir) - hl.diameter / 2
                if -hl.diameter < d_tan < lim("sheet.hole_to_bend_t_ratio") * t - 1e-6:
                    near_hole.append((float(d_tan), G.xyz(hl.origin), hl.diameter))
        _ = mid
    row["bend_radii_mm"] = sorted({round(b["radius"], 2) for b in bent["bends"]})
    if tight:
        v = min(tight)
        add("warning", "bend_radius_too_tight", f"{len(tight)} bend(s) with an inside radius under the {t:g} mm thickness (tightest {v[0]:.2f} mm at {v[1]}): "
            f"the outside of the bend cracks or thins.", rule="sheet.bend_radius_t_ratio", value=v[0], limit_mm=round(lim('sheet.bend_radius_t_ratio') * t, 3),
            at=[x[1] for x in sorted(tight)[:6]], hint=f"Use an inside radius of at least {t:g} mm (and the shop's tooling radius if known).")
    if wide:
        v = max(wide)
        add("warning", "bend_radius_too_large", f"{len(wide)} bend(s) with an inside radius over {lim('sheet.bend_radius_max_t_ratio'):g} x thickness "
            f"({v[0]:.1f} mm at {v[1]}): that is rolled or bump-formed in many hits, not one bend.", rule="sheet.bend_radius_max_t_ratio",
            value=v[0] / t, at=[x[1] for x in wide[:6]], hint="Use a radius of one to three thicknesses unless the curve is the point.")
    if differs:
        v = differs[0]
        add("warning", "bend_radius_differs", f"{len(differs)} bend(s) modelled at {v[0]:.2f} mm inside radius; {lim.shop_name} forms {near:g} mm "
            f"{c.material} at {shop_row[0]:g} mm and offers no other radius, so flange positions will move.", value=v[0], limit=shop_row[0],
            source="https://sendcutsend.com/materials/processing-min-max/", at=[x[1] for x in differs[:6]],
            hint=f"Model the bends at {shop_row[0]:g} mm.")
    if long_bend:
        v = max(long_bend)
        add("error", "bend_too_long", f"a {v[0]:.0f} mm bend is longer than the {shop_row[1]:.0f} mm {lim.shop_name} can bend in {near:g} mm {c.material}.",
            value=v[0], limit=shop_row[1], source="https://sendcutsend.com/materials/processing-min-max/", at=[v[1]])
    if short:
        v = min(short)
        add("error", "flange_too_short", f"{len(short)} flange(s) too short to bend (shortest {v[0]:.2f} mm from the outside of the bend at {v[2]}, "
            f"needs {v[1]:.2f} mm" + (f", {lim.shop_name}'s minimum for this stock" if v[3] else " = 2 x thickness + inside radius")
            + "): the brake's die has nothing to bear on.", rule="sheet.flange_min_t_ratio", value=v[0], limit_mm=round(v[1], 3),
            at=[x[2] for x in sorted(short)[:6]], hint=f"Lengthen the flange to at least {v[1]:.1f} mm, or cut it over-long and trim after bending.")
    if near_hole:
        v = min(near_hole)
        need = lim("sheet.hole_to_bend_t_ratio") * t
        add("warning", "hole_too_close_to_bend", f"{len(near_hole)} hole(s) closer than {need:g} mm (2 x thickness) to where a bend's radius starts "
            f"(nearest {max(v[0], 0):.2f} mm, a {v[2]:g} mm hole at {v[1]}): the hole stretches into an oval when the bend is formed.",
            rule="sheet.hole_to_bend_t_ratio", value=max(v[0], 0.0), limit_mm=round(need, 3), at=[x[1] for x in sorted(near_hole)[:6]],
            hint=f"Move the hole at least {need:g} mm from the bend, add a relief slot along the bend, or drill it after bending.")
    return row


# ------------------------------------------------------------------------------------------ DXF
def write_dxf(plate: dict, path: Path) -> bool:
    """The flat profile as a DXF in millimetres, true lines, arcs and circles, on a layer named CUT."""
    from build123d import ExportDXF, Plane, Unit, Vector

    origin = plate["axis"] * plate["top"]
    pl = Plane(origin=Vector(*origin), x_dir=Vector(*plate["u"]), z_dir=Vector(*plate["axis"]))
    ex = ExportDXF(unit=Unit.MM)
    ex.add_layer("CUT")
    n = 0
    for lvl, s, f in plate["caps"]:
        if abs(lvl - plate["top"]) > 0.01:
            continue
        ex.add_shape(pl.to_local_coords(f), layer="CUT")
        n += 1
    if not n:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    ex.write(str(path))
    return True


def export_flat_patterns(design, out_dir) -> dict:
    """Write one DXF per distinct flat cut part (process 'sheet', or a machined plate that is a plain
    through-cut profile and so could be laser cut). Returns {part name: path}."""
    from ..tolerance.process import process_of

    out_dir = Path(out_dir)
    done = {}
    for c in design.components:
        if c.cots:
            continue
        try:
            proc = process_of(c)
            if proc not in ("sheet", "machined"):
                continue
            sm = G.sample_surface(c.shape, n=200)
            plate = plate_of(c.shape, G.part_frame(c.shape), sm)
            if plate is None or plate["steps"] or plate["countersinks"]:
                continue
            if proc == "machined" and G.turned_axis(c.shape) is not None:
                continue                                  # a round spacer is a lathe part, not a profile
            p = out_dir / f"{c.name}.dxf"
            if write_dxf(plate, p):
                done[c.name] = str(p)
        except Exception as e:      # an artefact must never fail the run
            done[c.name] = f"not written: {type(e).__name__}: {e}"
    return done
