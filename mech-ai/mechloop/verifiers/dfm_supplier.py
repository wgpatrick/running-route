"""Each sheet or machined part against its supplier's published design rules (mechloop/data/supplier_rules).

Called once per custom part from verifiers/manufacture.py (after the process checks and the shop-profile checks). It

1. measures the features the suppliers' rules speak about (`features_of`): holes and cut-outs with the material to the
   edge and to the next feature, slots and notches, necks, share cut away, flat size, bends (radius, angle, length),
   formed flange lengths along each bend (for the "share of the bend that meets the minimum flange" rule), holes and
   cut-outs to each bend, self-clinching (PEM) hardware positions, tapped holes, countersinks; for machined parts the
   extents, the thinnest wall, the smallest hole and the threads;
2. judges them against the rules of the supplier the part is assigned to (`supplier_rules.shop_for`: the part's shop,
   else the design's, else SendCutSend for sheet and Xometry for machined). A failed rule the supplier states as a
   requirement is an error; one it phrases as a recommendation is a warning (`code="supplier_rule"`). Every finding
   names the rule id, the supplier, the measured value, the limit, the source URL and the supplier's own words;
3. adds one information finding per part (`supplier_rules_summary`) saying which suppliers' published rules the part
   passes, which rule kinds no supplier publishes for that material and thickness, and which rules could not be
   evaluated because mechloop does not extract the feature (bend reliefs, countersink depth, ...).

The rule data and its evaluation are in mechloop/shops/supplier_rules.py; docs/SUPPLIER_RULES.md is the readable table.
"""
from __future__ import annotations

import math

import numpy as np
from build123d import GeomType

from ..shops import supplier_rules as SR
from . import dfm_geom as G
from . import dfm_sheet as DS

N_SAMPLES = 41          # positions along a bend at which the formed flange length is measured


# ------------------------------------------------------------------------------------- hardware
def _pem_components(design) -> list[dict]:
    """Self-clinching hardware in the design: catalogue PEM parts (SKU NUT-PEM-<pem sku>) and screws declared
    insert='pem' (they name the part they thread into)."""
    out = []
    for p in design.components:
        sku = p.sku or ""
        if not (p.cots and sku.startswith("NUT-PEM-")):
            continue
        m = (p.meta or {}).get("placement")
        if not m:
            continue
        m = np.asarray(m, dtype=float)
        thread = ((p.meta.get("interfaces") or {}).get("thread_d"))
        out.append({"name": p.name, "sku": sku[len("NUT-PEM-"):], "thread": f"M{thread:g}" if thread else sku.split("-")[3],
                    "origin": m[:, 3], "axis": m[:, 2]})
    return out


def _pem_screws(design, c) -> set[str]:
    return {s.name for s in design.components if c.name in (s.meta.get("threads_into") or []) and s.meta.get("thread_insert") == "pem"}


# ----------------------------------------------------------------------------------- flat parts
def _rings(P, plate, holes) -> list[dict]:
    from shapely.geometry import Polygon

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
        w = round_ if round_ is not None else DS._width(poly)
        rings.append({"poly": poly, "c": (cx, cy), "d": round(float(w), 3), "round": round_ is not None, "at": DS._to_world(plate, cx, cy),
                      "slot": _is_slot(poly, w, round_)})
    return rings


def _is_slot(poly, width: float, round_) -> bool:
    """A non-round cut-out at least twice as long as it is wide (a hex or square hole is a hole, not a slot)."""
    return round_ is None and width > 0 and DS._long(poly) >= 2.0 * width


def _webs(rings, boundary) -> None:
    """Fill each ring's material to the edge (`edge_web`), to the nearest other cut feature (`web`) and, for round holes,
    to the nearest other round hole (`hole_web`)."""
    for i, x in enumerate(rings):
        x["edge_web"] = round(float(boundary.distance(x["poly"].exterior)), 3) if boundary is not None and not boundary.is_empty else None
        others = [y for j, y in enumerate(rings) if j != i]
        x["web"] = round(min(float(x["poly"].distance(y["poly"])) for y in others), 3) if others else None
        ro = [y for y in others if y["round"]]
        x["hole_web"] = round(min(float(x["poly"].distance(y["poly"])) for y in ro), 3) if (x["round"] and ro) else None


def _necks(P, t: float, rings=()):
    """(tabs, tab probe, notches, notch probe): material necks narrower than the probe width, and notches / slots in the
    outline narrower than theirs, each as (width, world point). The probes are wider than any supplier limit in the data
    (Protolabs: tabs 2 x t or 3.2 mm, notches t or 1.016 mm), so 'none found' passes every such rule."""
    from shapely.geometry import Polygon

    out = []
    for probe, mode in ((max(2.0 * t, 3.2) * 1.1, "tab"), (max(1.0 * t, 1.016) * 1.5, "notch")):
        h = probe / 2 * 0.98
        if mode == "tab":
            reg = DS._polys(P.difference(P.buffer(-h, quad_segs=16).buffer(h, quad_segs=16)))
        else:
            solid = Polygon(P.exterior)
            reg = DS._polys(solid.buffer(h, quad_segs=16).buffer(-h, quad_segs=16).difference(solid))
        reg = [p for p in reg if p.area > 0.2 * probe * probe and DS._long(p) > 1.2 * probe]
        if mode == "tab":       # material beside a hole is a web (judged by the web rules), not a tab
            reg = [p for p in reg if not any(x["poly"].distance(p) < 0.05 for x in rings)]
        out.append(([(round(DS._width(p), 3), p.representative_point()) for p in reg], round(probe, 3)))
    return out


def flat_features(design, c, plate: dict, holes: list, tapped: list) -> dict | None:
    from shapely.geometry import Point, Polygon

    prof = DS.profile_of(plate)
    if prof is None or prof.is_empty:
        return None
    P = max(DS._polys(prof), key=lambda p: p.area)
    t = float(plate["thickness"])
    rings = _rings(P, plate, holes)
    _webs(rings, P.exterior)
    (tabs, tab_probe), (notches, notch_probe) = _necks(P, t, rings)
    mrr = P.minimum_rotated_rectangle
    xs, ys = mrr.exterior.coords.xy
    sides = sorted((math.dist((xs[0], ys[0]), (xs[1], ys[1])), math.dist((xs[1], ys[1]), (xs[2], ys[2]))))
    solid = Polygon(P.exterior)
    feat = {"process": "sheet", "form": "flat", "material": c.material, "thickness_mm": round(t, 3),
            "holes": [{k: v for k, v in x.items() if k not in ("poly", "c")} for x in rings],
            "tabs": [(w, DS._to_world(plate, p.x, p.y)) for w, p in tabs], "tab_probe_mm": tab_probe,
            "notches": [(w, DS._to_world(plate, p.x, p.y)) for w, p in notches], "notch_probe_mm": notch_probe,
            "flat_size_mm": [round(sides[0], 2), round(sides[1], 2)], "cut_away_fraction": round(1.0 - P.area / max(solid.area, 1e-9), 3),
            "countersinks": int(plate.get("countersinks") or 0), "bends": []}

    def ring_at(x, y):
        pt = Point(x, y)
        for r in rings:
            if r["poly"].buffer(0.05).contains(pt):
                return r
        return None

    pems, pem_rings = [], []
    lo, hi = plate["bottom"] - 1.0, plate["top"] + 1.0
    for p in _pem_components(design):
        o = p["origin"]
        if not (lo <= o @ plate["axis"] <= hi):
            continue
        r = ring_at(o @ plate["u"], o @ plate["v"])
        if r is None:
            continue
        pem_rings.append(id(r))
        pems.append({"name": p["name"], "sku": p["sku"], "thread": p["thread"], "ring": r})
    pem_screws = _pem_screws(design, c)
    taps = []
    for tp in tapped:
        q = np.asarray(tp["at"], dtype=float)
        r = ring_at(q @ plate["u"], q @ plate["v"])
        if tp["screw"] in pem_screws:
            if r is not None and id(r) not in pem_rings:
                pem_rings.append(id(r))
                pems.append({"name": tp["screw"], "sku": None, "thread": f"M{tp['d']:g}", "ring": r})
            continue
        taps.append({"d": float(tp["d"]), "at": tp["at"], "web": None if r is None else SR._min(r.get("edge_web"), r.get("web"))})
    for p in pems:
        r = p.pop("ring")
        cpt = Point(*r["c"])
        others = [x["poly"].exterior.distance(cpt) for x in rings if x is not r]
        p.update({"at": r["at"], "hole_d": r["d"], "center_edge": round(float(min([P.exterior.distance(cpt)] + others)), 3), "center_bend": None,
                  "_c": r["c"]})
    for p in pems:
        same = [math.dist(p["_c"], q["_c"]) for q in pems if q is not p and q["thread"] == p["thread"]]
        p["pitch"] = round(min(same), 3) if same else None
    for p in pems:
        p.pop("_c")
    feat["pems"], feat["tapped"] = pems, taps
    return feat


# ----------------------------------------------------------------------------------- bent parts
def _plane_axes(n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(n, a)
    u /= np.linalg.norm(u)
    return u, np.cross(n, u)


def bent_features(design, c, bent: dict, holes: list, tapped: list) -> dict:
    from shapely.geometry import LineString, Point, Polygon, box
    from shapely.ops import unary_union

    t = float(bent["thickness"])
    shape = c.shape
    planes = [(f, G._vec(f.normal_at(f.center()))) for f in shape.faces() if f.geom_type == GeomType.PLANE]
    faces: list[dict] = []          # unique flange faces with the tangent lines of the bends they meet

    def face_entry(f, n):
        for e in faces:
            if e["face"].wrapped.IsSame(f.wrapped):
                return e
        u, v = _plane_axes(n)
        outer = DS._wire_points(f.outer_wire(), f, u, v)
        inner = [DS._wire_points(w, f, u, v) for w in f.inner_wires()]
        poly = Polygon(outer, [h for h in inner if len(h) >= 3]) if len(outer) >= 3 else None
        if poly is not None and not poly.is_valid:
            poly = poly.buffer(0)
            poly = max(DS._polys(poly), key=lambda p: p.area) if not poly.is_empty else None
        e = {"face": f, "n": n, "u": u, "v": v, "level": float(G._vec(f.center()) @ n), "poly": poly, "tangents": []}
        faces.append(e)
        return e

    bends = []
    for b in bent["bends"]:
        a, o, rin, ang = b["axis"], b["origin"], float(b["radius"]), float(b["angle"])
        lo, hi = float(b["inside"].lo), float(b["inside"].hi)
        rec = {"radius": round(rin, 3), "angle": round(ang, 2), "length": round(hi - lo, 3), "at": G.xyz(b["inside"].mid), "flanges": []}
        setback = (rin + t) * math.tan(math.radians(min(ang, 179.0)) / 2)
        for f, n in planes:
            if abs(n @ a) > 0.02:
                continue
            dist = abs((G._vec(f.center()) - o) @ n)
            if abs(dist - rin) > 0.03:
                continue
            vs = np.array([[q.X, q.Y, q.Z] for q in f.vertices()])
            rel = vs - o
            rel = rel - np.outer(rel @ a, a)
            fdir = np.cross(a, n)
            along = rel @ fdir
            if np.min(np.abs(along)) > 0.05:
                continue
            hh = (vs - o) @ a
            if hh.max() < lo + 0.05 or hh.min() > hi - 0.05:
                continue
            reach = along[np.argmax(np.abs(along))]
            sgn = 1.0 if reach > 0 else -1.0
            e = face_entry(f, n)
            # tangent line of this bend on the face, in the face's (u, v) coordinates
            p0 = o + n * ((G._vec(f.center()) - o) @ n)                       # a point on the tangent line (along = 0)
            e["tangents"].append({"p": np.array([p0 @ e["u"], p0 @ e["v"]]), "d": np.array([a @ e["u"], a @ e["v"]]),
                                  "inward": np.array([sgn * fdir @ e["u"], sgn * fdir @ e["v"]]), "r": rin, "angle": ang})
            # formed flange length along the bend: polygon in (h along the axis, s away from the tangent line)
            prof = []
            if e["poly"] is not None:
                outer = DS._wire_points(f.outer_wire(), f, a, sgn * fdir)
                inner = [DS._wire_points(w, f, a, sgn * fdir) for w in f.inner_wires()]
                off = np.array([o @ a, o @ (sgn * fdir)])
                fp = Polygon(outer - off, [h - off for h in inner if len(h) >= 3])
                fp = fp if fp.is_valid else fp.buffer(0)
                span = abs(float(reach)) + 10.0
                for h in np.linspace(lo + 0.02 * (hi - lo), hi - 0.02 * (hi - lo), N_SAMPLES):
                    cut = fp.intersection(LineString([(h, -1.0), (h, span)]))
                    top = 0.0
                    for seg in DS._polys(cut) if not cut.is_empty else []:
                        ys_ = [q[1] for q in seg.coords] if hasattr(seg, "coords") else []
                        if ys_ and min(ys_) <= 0.1:
                            top = max(top, max(ys_))
                    prof.append(round(top + setback, 3) if top > 0 else 0.0)
            far = o + a * float(hh.mean()) + fdir * float(reach) + n * dist * np.sign((G._vec(f.center()) - o) @ n)
            rec["flanges"].append({"length": round(abs(float(reach)) + setback, 3), "profile": prof, "at": G.xyz(far),
                                   "reach": round(abs(float(reach)), 3)})
        bends.append(rec)

    # holes and cut-outs on the flange faces: size, material to the (non-bend) edge, to the next feature, to each bend
    hole_list, hole_bend, pems, taps = [], [], [], []
    pem_comp = _pem_components(design)
    pem_screws = _pem_screws(design, c)
    tap_pts = [(tp, np.asarray(tp["at"], dtype=float)) for tp in tapped]
    for e in faces:
        P = e["poly"]
        if P is None or P.is_empty:
            continue
        minx, miny, maxx, maxy = P.bounds
        big = max(maxx - minx, maxy - miny) + 10.0
        strips = []
        lines = []
        for tg in e["tangents"]:
            p, d = tg["p"], tg["d"] / (np.linalg.norm(tg["d"]) or 1.0)
            ln = LineString([tuple(p - d * big * 2), tuple(p + d * big * 2)])
            lines.append((ln, tg))
            strips.append(ln.buffer(0.05))
        boundary = P.exterior.difference(unary_union(strips)) if strips else P.exterior
        rings = []
        for ring in P.interiors:
            poly = Polygon(ring)
            cx, cy = poly.centroid.x, poly.centroid.y
            round_ = None
            for hl in holes:
                if abs(abs(hl.axis @ e["n"]) - 1) < 1e-3 and math.hypot(hl.origin @ e["u"] - cx, hl.origin @ e["v"] - cy) < 0.05:
                    round_ = hl.diameter
                    break
            w = round_ if round_ is not None else DS._width(poly)
            at = G.xyz(cx * e["u"] + cy * e["v"] + e["level"] * e["n"])
            rings.append({"poly": poly, "c": (cx, cy), "d": round(float(w), 3), "round": round_ is not None, "at": at, "slot": _is_slot(poly, w, round_)})
        _webs(rings, boundary)
        for x in rings:
            for ln, tg in lines:
                dt = float(x["poly"].distance(ln))
                # only the side of the tangent line the flange lies on
                side = (np.array(x["c"]) - tg["p"]) @ tg["inward"]
                if side > 0:
                    hole_bend.append({"d_tan": round(dt, 3), "r": tg["r"], "angle": tg["angle"], "d": x["d"], "at": x["at"]})
            hole_list.append({k: v for k, v in x.items() if k not in ("poly", "c")})

        def ring_at(q):
            if abs(q @ e["n"] - e["level"]) > t + 1.0:
                return None
            pt = Point(q @ e["u"], q @ e["v"])
            for r in rings:
                if r["poly"].buffer(0.05).contains(pt):
                    return r
            return None

        found = []
        for p in pem_comp:
            r = ring_at(p["origin"])
            if r is not None:
                found.append((p["name"], p["sku"], p["thread"], r))
        for tp, q in tap_pts:
            r = ring_at(q)
            if r is None:
                continue
            if tp["screw"] in pem_screws:
                if not any(r is f_[3] for f_ in found):
                    found.append((tp["screw"], None, f"M{tp['d']:g}", r))
            else:
                taps.append({"d": float(tp["d"]), "at": tp["at"], "web": SR._min(r.get("edge_web"), r.get("web"))})
        for name, sku, thread, r in found:
            cpt = Point(*r["c"])
            others = [x["poly"].exterior.distance(cpt) for x in rings if x is not r]
            ce = min([boundary.distance(cpt)] + others) if not boundary.is_empty else (min(others) if others else None)
            cb = [ln.distance(cpt) for ln, tg in lines if (np.array(r["c"]) - tg["p"]) @ tg["inward"] > 0]
            pems.append({"name": name, "sku": sku, "thread": thread, "at": r["at"], "hole_d": r["d"],
                         "center_edge": None if ce is None else round(float(ce), 3), "center_bend": round(float(min(cb)), 3) if cb else None,
                         "_c": (tuple(r["c"]), id(e))})
    for p in pems:
        same = [math.dist(p["_c"][0], q["_c"][0]) for q in pems if q is not p and q["thread"] == p["thread"] and q["_c"][1] == p["_c"][1]]
        p["pitch"] = round(min(same), 3) if same else None
    for p in pems:
        p.pop("_c")
    feat = {"process": "sheet", "form": "bent", "material": c.material, "thickness_mm": round(t, 3), "bends": bends, "holes": hole_list,
            "hole_bend": hole_bend, "pems": pems, "tapped": taps, "countersinks": 0, "tab_probe_mm": None, "notch_probe_mm": None}
    if len(bends) == 1 and len(bends[0]["flanges"]) == 2:
        b = bends[0]
        width = 0.0
        for e in faces:
            if e["poly"] is not None:
                a_ = bent["bends"][0]["axis"]
                ax2 = np.array([a_ @ e["u"], a_ @ e["v"]])
                pts = np.asarray(e["poly"].exterior.coords)
                width = max(width, float(np.ptp(pts @ ax2)))
        feat["develop"] = {"tangent_sum": b["flanges"][0]["reach"] + b["flanges"][1]["reach"], "r": b["radius"], "angle": b["angle"], "width": width}
    return feat


# ------------------------------------------------------------------------------------- machined
def machined_features(design, c, row: dict, sm, frame, holes: list) -> dict:
    lo, hi = G.extents(sm, frame)
    try:
        tapped = G.tapped_holes(design, c, sm)
    except Exception:
        tapped = []
    return {"process": "machined", "form": row.get("form"), "material": c.material, "thickness_mm": row.get("thickness_mm"),
            "extents_mm": [round(float(x), 2) for x in sorted(hi - lo)], "min_wall_mm": row.get("min_wall_mm"),
            "smallest_hole_mm": round(min(h.diameter for h in holes), 3) if holes else None,
            "tapped": [{"d": float(tp["d"]), "at": tp["at"]} for tp in tapped]}


def features_of(design, c, row: dict, sm, frame, cyls, holes) -> dict | None:
    """The features the suppliers' rules need, for one part whose process checks produced `row`."""
    proc = row.get("process")
    if proc == "machined":
        return machined_features(design, c, row, sm, frame, holes)
    if proc != "sheet":
        return None
    try:
        tapped = G.tapped_holes(design, c, sm)
    except Exception:
        tapped = []
    if row.get("form") == "flat":
        plate = DS.plate_of(c.shape, frame, sm)
        return flat_features(design, c, plate, holes, tapped) if plate is not None else None
    if row.get("form") == "bent":
        bent = DS.bent_sheet(c.shape, sm, cyls)
        return bent_features(design, c, bent, holes, tapped) if bent is not None else None
    return None


# ------------------------------------------------------------------------------------- findings
KIND_TEXT = {
    "hole_min": "smallest hole or cut-out", "slot_min": "narrowest slot or notch", "notch_min": "narrowest notch in the outline", "web_min": "least material between cut features or to the edge",
    "hole_edge_web": "hole edge to part edge", "slot_edge_web": "slot to edge or next feature", "hole_hole_web": "material between holes",
    "tab_min": "narrowest tab or neck", "cut_away_max": "share of the blank cut away", "part_min_size": "flat part size (minimum)",
    "part_max_size": "flat part size (maximum)", "thickness_min": "sheet thickness (minimum)", "thickness_max": "sheet thickness (maximum)",
    "thickness_range": "sheet thickness range", "bend_offered": "bending offered at this thickness", "bend_radius": "inside bend radius (the only one offered)",
    "bend_radius_min": "inside bend radius (minimum)", "bend_radius_range": "inside bend radius (tooling range)", "flange_min": "formed flange length",
    "flange_min_flat": "flat-pattern flange length from the bend line",
    "flange_support_min": "share of the bend meeting the minimum flange", "feature_to_bend": "hole or cut-out to bend",
    "bend_length_max": "bend length", "bend_angle_max": "bend angle", "bend_angle_min": "bend angle (minimum)", "bend_part_min_size": "flat blank size for bending (minimum)",
    "bend_part_max_size": "flat blank size for bending (maximum)", "bend_material_review": "bent 6061-T6",
    "pem_sheet_min": "sheet thickness for the hardware (minimum)", "pem_sheet_max": "sheet thickness for the hardware (maximum)",
    "pem_sheet_range_al": "aluminium sheet thickness for the hardware", "pem_center_to_edge": "hardware centre to edge",
    "pem_center_to_bend": "hardware centre to bend", "pem_center_to_center": "hardware centre to centre", "tap_offered": "tapping offered at this thickness",
    "tap_metric_range": "metric tap size", "tap_hole_to_edge": "tapped hole to nearest cut feature", "countersink_offered": "countersinking offered at this thickness",
    "cnc_min_feature": "smallest feature", "cnc_min_wall": "thinnest wall", "cnc_min_nominal_thickness": "nominal part thickness",
    "cnc_part_max_size": "part size", "cnc_thread_range": "thread size", "cnc_thread_callout": "threads in the model",
}


def _fmt(v) -> str:
    if isinstance(v, (list, tuple)):
        return " x ".join(_fmt(x) for x in v)
    if isinstance(v, float):
        return f"{v:.3g}" if abs(v) < 10 else f"{v:.1f}"
    return str(v)


def judge(feat: dict) -> dict:
    """Every supplier's rules applied to one part's features: {supplier: {"results", "summary", "missing", "verdict"}}."""
    out = {}
    for sup in SR.suppliers():
        res = SR.evaluate(feat, sup)
        summ = SR.summarise(res)
        miss = SR.missing_kinds(feat, sup, res)
        n_eval = sum(1 for x in res if x["status"] in ("pass", "fail"))
        out[sup] = {"results": res, "summary": summ, "missing": miss, "verdict": SR.verdict(summ, miss, n_eval)}
    return out


def check_part(r, design, c, row: dict, sm, frame, cyls, holes) -> None:
    """Findings for one part against its assigned supplier, and the cross-supplier summary."""
    feat = features_of(design, c, row, sm, frame, cyls, holes)
    if feat is None:
        return
    shop = SR.shop_for(c, design, row.get("process"))
    verdicts = judge(feat)
    mine = verdicts[shop]
    sname = SR.name_of(shop)
    pem_notes = set()
    failed = {x["rule"]["id"]: x for x in mine["results"] if x["status"] == "fail"}
    also = {}            # a failed rule that states the same requirement as another failed one is told in that one's finding
    for x in failed.values():
        same = x["rule"].get("same_requirement_as")
        if same in failed:
            also.setdefault(same, []).append(x)
    for res in mine["results"]:
        rule = res["rule"]
        if rule["rule"].startswith("pem_") and rule.get("hardware"):
            for p in feat.get("pems") or []:
                _, note = SR.pem_sku_for(p, shop, feat["thickness_mm"] or 0.0, feat["material"])
                if note and "not in" in note:
                    pem_notes.add(note)
        if res["status"] != "fail" or rule["severity"] == "info":
            continue
        if rule.get("same_requirement_as") in failed:
            continue
        unit = "" if rule["rule"] in ("cut_away_max", "flange_support_min", "bend_offered", "tap_offered", "tap_metric_range", "countersink_offered",
                                      "cnc_thread_range", "cnc_thread_callout", "bend_material_review") else " mm"
        if rule["rule"] in ("bend_angle_max", "bend_angle_min"):
            unit = " deg"
        cnt = f" ({res['count']} of {res['of']})" if res.get("of", 1) > 1 else ""
        tol = f" +/- {rule['tolerance_mm']:g}" if rule["comparison"] == "==" and rule.get("tolerance_mm") else ""
        same = "".join(f" Same requirement in the flat pattern ({o['rule']['id']}): {KIND_TEXT.get(o['rule']['rule'], o['rule']['rule'])} "
                       f"{_fmt(o.get('measured'))}{unit}, limit {o['rule']['comparison']} {_fmt(o.get('limit'))}{unit}." for o in also.get(rule["id"], []))
        outcome = f" {rule['outcome'][0].upper()}{rule['outcome'][1:]}." if rule.get("outcome") else ""
        msg = (f"{c.name}: {sname} rule {rule['id']}: {KIND_TEXT.get(rule['rule'], rule['rule'])} {_fmt(res.get('measured'))}{unit}{cnt}, "
               f"limit {rule['comparison']} {_fmt(res.get('limit'))}{tol}{unit} ({rule['severity']}: the supplier's words: \"{rule['quote'][:160]}\")."
               f"{outcome}{same}")
        r.add(rule["severity"], "supplier_rule", msg, part=c.name, supplier=shop, rule=rule["id"], rule_kind=rule["rule"],
              value=res.get("measured"), limit=res.get("limit"), comparison=rule["comparison"], count=res.get("count"),
              at=res.get("at") or None, source=rule["source_url"], quote=rule["quote"], retrieved=rule["retrieved"],
              material=feat["material"], thickness_mm=feat.get("thickness_mm"), detail=res.get("detail"), note=rule.get("note"))
    for note in sorted(pem_notes):
        r.add("warning", "supplier_hardware_not_listed", f"{c.name}: {note}.", part=c.name, supplier=shop,
              hint="Order a catalogue SKU the supplier installs, or supply the hardware and ask for a quote.")
    gaps = sorted({x["rule"]["rule"] for x in mine["results"] if x["status"] == "not_evaluated"})
    row["supplier_rules"] = {
        "assigned": shop, "verdict": mine["verdict"], "summary": mine["summary"], "no_published_rule": mine["missing"],
        "not_evaluated": gaps, "by_supplier": {s: v["verdict"] for s, v in verdicts.items()}}
    passing = sorted(SR.name_of(s) for s, v in verdicts.items() if v["summary"]["errors"] == 0 and any(x["status"] in ("pass", "fail") for x in v["results"]))
    r.add("info", "supplier_rules_summary",
          f"{c.name} ({feat['material']}, {feat.get('thickness_mm')} mm, {feat.get('form')}): assigned {sname}: {mine['verdict']}. "
          f"Passes the published rules of: {', '.join(passing) or 'none'}.",
          part=c.name, supplier=shop, by_supplier={s: {"verdict": v["verdict"], **v["summary"], "no_published_rule": v["missing"]} for s, v in verdicts.items()},
          not_evaluated=gaps)


# ------------------------------------------------------------------------------------- a part from a file
def check_file(path, material: str, process: str = "sheet", shop: str | None = None, thickness_mm: float | None = None,
               name: str = "part"):
    """Run the manufacture checks (process rules, shop profile, the assigned supplier's published rules) on one part read from a
    STEP file, with its material, process, shop and (for sheet) stock thickness declared as a supplier's quote page would ask for
    them. Used for reference parts (reference_parts/) and parts that are not in a design. Returns the VerifierResult; a declared
    thickness that the geometry does not have is an error (`declared_thickness_differs`)."""
    from build123d import import_step

    from ..model import Design
    from .manufacture import verify_manufacture

    shape = import_step(str(path))
    d = Design(f"file:{getattr(path, 'name', str(path))}")
    d.add(name, shape, material=material, process=process, meta={"dfm": {"shop": shop}} if shop else {})
    r = verify_manufacture(d)
    row = (r.metrics.get("parts") or {}).get(name) or {}
    t = row.get("thickness_mm")
    if thickness_mm is not None and t is not None and abs(float(t) - float(thickness_mm)) > SR.T_TOL:
        r.add("error", "declared_thickness_differs", f"{name}: declared {thickness_mm:g} mm stock, the geometry is {float(t):g} mm thick.",
              part=name, value=float(t), limit=float(thickness_mm))
    return r
