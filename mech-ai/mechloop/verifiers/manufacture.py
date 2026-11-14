"""Can each custom part actually be made by the process it is assigned?

Printed parts: best orientation, how much needs support, bridges, whether it fits a print bed,
whether it is so tall and thin it would topple. Machined parts: whether it is a plate from stock
thickness, sharp inside corners a round cutter cannot make, deep narrow holes, how many set-ups.
Purchased and cut-to-length parts are not checked (they must not be modified).
"""
from __future__ import annotations

import math

import numpy as np
from build123d import GeomType
from OCP.BRepAdaptor import BRepAdaptor_Surface

from ..geom import to_trimesh
from ..model import Design
from ..report import VerifierResult, timed
from ..tolerance.process import process_of

STOCK_MM = (1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25)
AXES = {"+Z": (0, 0, 1), "-Z": (0, 0, -1), "+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0)}
PRINT_VOLUME = (220.0, 220.0, 250.0)   # a common desktop printer; override with design.printer["build_volume"]


def _print_check(c, mesh, vol_limit) -> dict:
    n, a, cen = mesh.face_normals, mesh.area_faces, mesh.triangles_center
    best = None
    for name, up in AXES.items():
        up = np.array(up, dtype=float)
        h = cen @ up
        zmin, zmax = float((mesh.vertices @ up).min()), float((mesh.vertices @ up).max())
        down = n @ up
        on_bed = (down < -0.98) & (h - zmin < 0.3)
        over = (down < -0.707) & ~on_bed                 # steeper than 45 degrees from vertical, not on the bed
        flat_over = (down < -0.98) & ~on_bed             # flat undersides in mid-air: bridges or supports
        support_area = float(a[over].sum())
        footprint = float(a[on_bed].sum())
        height = zmax - zmin
        score = support_area - 0.2 * footprint + 0.5 * height
        ext = np.ptp(mesh.vertices - np.outer(mesh.vertices @ up, up), axis=0)
        lat = sorted(float(x) for x in ext if x > 1e-6)
        row = {"up": name, "support_area_mm2": round(support_area, 0), "footprint_mm2": round(footprint, 0),
               "height_mm": round(height, 1), "flat_overhang_mm2": round(float(a[flat_over].sum()), 0),
               "lateral_mm": [round(x, 1) for x in lat[-2:]], "score": score}
        if best is None or score < best["score"]:
            best = row
    best.pop("score")
    lat = best["lateral_mm"] + [0, 0]
    fits = max(lat[:2]) <= max(vol_limit[:2]) and min(lat[:2]) <= min(vol_limit[:2]) and best["height_mm"] <= vol_limit[2]
    best["fits_print_volume"] = bool(fits)
    best["slenderness"] = round(best["height_mm"] / math.sqrt(max(best["footprint_mm2"], 1.0)), 1)
    return best


def _plate_axis(shape):
    """If every face is square to one axis or parallel to it, the part can be cut from plate along that
    axis. Of the axes that work, the thinnest is the plate thickness. Returns (axis index, thickness) or None."""
    faces = shape.faces()
    bb = shape.bounding_box()
    size = [bb.size.X, bb.size.Y, bb.size.Z]
    good = []
    for k in range(3):
        ok = True
        for f in faces:
            if f.geom_type == GeomType.PLANE:
                nrm = f.normal_at(f.center())
                v = abs([nrm.X, nrm.Y, nrm.Z][k])
                if 0.02 < v < 0.98:
                    ok = False
                    break
            elif f.geom_type == GeomType.CYLINDER:
                d = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Direction()
                if abs([d.X(), d.Y(), d.Z()][k]) < 0.98:
                    ok = False
                    break
            else:
                ok = False
                break
        if ok:
            good.append((size[k], k))
    if not good:
        return None
    t, k = min(good)
    others = [size[i] for i in range(3) if i != k]
    if t <= 30.0 and t <= 0.5 * max(others):
        return k, t
    return None


def _access_directions(shape, mesh) -> list[str]:
    """Fewest directions a 3-axis cutter must come from to reach every inset face and hole.
    A flat face can be cut as a floor (tool along its normal) or as a wall (tool along the face);
    either way the tool needs a clear line of sight from outside."""
    import trimesh

    bb = shape.bounding_box()
    lo, hi = np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z])
    ray = trimesh.ray.ray_triangle.RayMeshIntersector(mesh)
    dirs = {n_: np.array(v, dtype=float) for n_, v in AXES.items()}
    feats, special = [], set()

    def clear(point, d):
        return not ray.intersects_any([point + d * 0.05], [d])[0]

    for f in shape.faces():
        if f.geom_type == GeomType.PLANE:
            c = f.center()
            nrm = f.normal_at(c)
            v = np.array([nrm.X, nrm.Y, nrm.Z])
            k = int(np.argmax(np.abs(v)))
            if abs(v[k]) < 0.98:
                special.add("angled")
                continue
            pos = np.array([c.X, c.Y, c.Z])
            outer = hi[k] if v[k] > 0 else lo[k]
            if abs(pos[k] - outer) <= 0.05:
                continue                       # an outside face of the stock
            p0 = pos + v * 0.05
            ok = {n_ for n_, d in dirs.items() if abs(d @ v) < 0.02 or d @ v > 0.98 if clear(p0, d)}
            if ok:
                feats.append(ok)
            else:
                special.add("unreachable")
        elif f.geom_type == GeomType.CYLINDER:
            cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
            d_ = cyl.Axis().Direction()
            v = np.array([d_.X(), d_.Y(), d_.Z()])
            k = int(np.argmax(np.abs(v)))
            if abs(v[k]) < 0.98:
                special.add("angled")
                continue
            loc = cyl.Axis().Location()
            c = f.center()
            a0 = np.array([loc.X(), loc.Y(), loc.Z()])
            pc = np.array([c.X, c.Y, c.Z])
            on_axis = a0 + ((pc - a0) @ v) * v
            radial = pc - on_axis
            outward = float(np.array([*f.normal_at(c)]) @ radial) > 0 if np.linalg.norm(radial) > 1e-9 else False
            if outward:
                continue                       # an outside round (a boss or the stock itself): turned or profiled
            ok = {n_ for n_, d in dirs.items() if abs(abs(d @ v) - 1) < 0.02 and clear(on_axis, d)}
            if ok:
                feats.append(ok)
            else:
                special.add("unreachable")
        else:
            special.add("curved")
    chosen = []
    left = [set(x) for x in feats]
    while left:
        best = max(dirs, key=lambda n_: (sum(1 for x in left if n_ in x), n_ == "+Z"))
        chosen.append(best)
        left = [x for x in left if best not in x]
    return sorted(chosen) + sorted(special)


def _sharp_inside_corners(mesh, axis: int) -> list:
    """Inside corners with no radius, seen in a slice across the plate: a round cutter cannot make them."""
    from shapely.geometry import Polygon

    lo, hi = mesh.bounds[0][axis], mesh.bounds[1][axis]
    nrm = np.zeros(3); nrm[axis] = 1.0
    org = np.zeros(3); org[axis] = lo + 0.37 * (hi - lo)
    sec = mesh.section(plane_origin=org, plane_normal=nrm)
    if sec is None:
        return []
    keep = [i for i in range(3) if i != axis]
    loops = [d[:, keep] for d in sec.discrete if len(d) >= 4]
    if not loops:
        return []
    polys = sorted((Polygon(l) for l in loops), key=lambda p: -p.area)
    out = []
    for li, loop in enumerate(loops):
        P = Polygon(loop)
        if P.area < 1e-6:
            continue
        # is this loop the outside of material or a hole in it?
        hole = any(q.area > P.area * 1.0001 and q.contains(P.representative_point()) for q in polys)
        pts = loop[:-1] if np.allclose(loop[0], loop[-1]) else loop
        ccw = Polygon(pts).exterior.is_ccw
        m = len(pts)
        for i in range(m):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % m]
            v1, v2 = b - a, c - b
            l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if l1 < 1.0 or l2 < 1.0:
                continue      # short segments are the facets of an arc: that corner has a radius
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            ang = math.degrees(math.asin(max(-1.0, min(1.0, cross / (l1 * l2)))))
            left_turn = cross > 0
            # on the outside loop an inside corner is a turn away from the loop's own winding; on a hole it is a turn with it
            inside = (left_turn != ccw) if not hole else (left_turn == ccw)
            if inside and abs(ang) > 30:
                p3 = np.zeros(3); p3[keep] = b; p3[axis] = org[axis]
                out.append([round(float(x), 1) for x in p3])
    return out


def verify_manufacture(design: Design) -> VerifierResult:
    r = VerifierResult("manufacture")
    custom = [c for c in design.components if not c.cots]
    if not custom:
        r.skipped = "no custom parts"
        return r
    with timed(r):
        vol = tuple((design.printer or {}).get("build_volume", PRINT_VOLUME))
        parts = {}
        for c in custom:
            proc = process_of(c)
            mesh = to_trimesh(c.shape)
            row = {"process": proc}
            if proc == "printed":
                pc = _print_check(c, mesh, vol)
                row.update(pc)
                if not pc["fits_print_volume"]:
                    r.add("error", "too_big_to_print",
                          f"{c.name}: {pc['lateral_mm']} x {pc['height_mm']} mm does not fit a {vol[0]:.0f} x {vol[1]:.0f} x {vol[2]:.0f} mm "
                          f"print volume in its best orientation.", part=c.name,
                          hint="Split the part, or make it from plate or extrusion.")
                if pc["support_area_mm2"] > 150:
                    r.add("warning", "needs_support",
                          f"{c.name}: even in its best print orientation ({pc['up']} up) {pc['support_area_mm2']:.0f} mm² overhangs by more "
                          f"than 45 degrees and needs support material.", part=c.name, orientation=pc["up"],
                          hint="Chamfer the undersides at 45 degrees, use teardrop holes, or split the part along a flat face.")
                if pc["slenderness"] > 6:
                    r.add("warning", "tall_thin_print",
                          f"{c.name}: {pc['height_mm']:.0f} mm tall on a {pc['footprint_mm2']:.0f} mm² footprint; it is likely to wobble or "
                          f"come off the bed.", part=c.name)
                from .warp import warp_risk

                row["warp"] = warp_risk(design, c.name, max(pc["lateral_mm"] or [0.0]), r)
                t_eff = 2 * c.shape.volume / max(mesh.area, 1e-9)
                row["typical_wall_mm"] = round(t_eff, 2)
                if t_eff < 0.8:
                    r.add("error", "wall_too_thin_to_print", f"{c.name}: typical wall about {t_eff:.2f} mm, under two 0.4 mm beads.", part=c.name)
            elif proc in ("machined", "sheet"):
                pl = _plate_axis(c.shape)
                if pl:
                    k, t = pl
                    row.update({"form": "plate", "thickness_mm": round(t, 2), "tool_axis": "XYZ"[k]})
                    if min(abs(t - s_) for s_ in STOCK_MM) > 0.05:
                        near = min(STOCK_MM, key=lambda s_: abs(s_ - t))
                        r.add("warning", "non_stock_thickness",
                              f"{c.name}: {t:.2f} mm thick; plate comes in {near:g} mm, so both faces would need machining.",
                              part=c.name, hint=f"Use {near:g} mm if the design allows.")
                    corners = _sharp_inside_corners(mesh, k)
                    row["sharp_inside_corners"] = len(corners)
                    if corners:
                        r.add("error" if proc == "machined" else "warning", "sharp_inside_corner",
                              f"{c.name}: {len(corners)} inside corner(s) with no radius (first at {corners[0]}); a rotating cutter leaves a "
                              f"radius there, so the mating part will not seat.", part=c.name, at=corners[:6],
                              hint="Add an inside radius of at least 1.5 mm (3 mm cutter), relieve the corner with a dog-bone, "
                                   "or chamfer/radius the mating part.")
                else:
                    need = _access_directions(c.shape, mesh)
                    dirs_ = [n_ for n_ in need if n_[0] in "+-"]
                    setups = max(1, len(dirs_))
                    row.update({"form": "block", "cut_from": need, "setups_estimate": setups})
                    if "angled" in need or "curved" in need:
                        r.add("warning", "angled_faces", f"{c.name}: has faces at an angle to all three axes or curved surfaces; "
                              f"needs a tilted set-up, form tooling or a 5-axis machine.", part=c.name)
                    if "unreachable" in need:
                        r.add("warning", "feature_unreachable", f"{c.name}: has an internal face or hole no straight cutter can reach "
                              f"from outside.", part=c.name, hint="Open the feature to one side, or split the part there.")
                    if setups >= 4:
                        r.add("warning", "many_setups", f"{c.name}: must be cut from {setups} directions ({', '.join(dirs_)}); "
                              f"that is {setups} set-ups on a 3-axis mill.",
                              part=c.name, hint="Make it from two or three plates bolted together, or print it if loads allow.")
                deep = []
                for f in c.shape.faces():
                    if f.geom_type != GeomType.CYLINDER:
                        continue
                    cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
                    d = cyl.Axis().Direction()
                    bb = f.bounding_box()
                    depth = abs(float(np.array([bb.size.X, bb.size.Y, bb.size.Z]) @ np.abs([d.X(), d.Y(), d.Z()])))
                    dia = 2 * cyl.Radius()
                    if dia < 12 and depth / dia > 8:
                        deep.append((round(dia, 2), round(depth, 1)))
                if deep:
                    r.add("warning", "deep_hole", f"{c.name}: hole(s) deeper than 8 diameters: {sorted(set(deep))[:4]} (dia, depth).", part=c.name)
            parts[c.name] = row
        r.metrics = {"custom_parts": len(custom), "by_process": {p: sum(1 for v in parts.values() if v["process"] == p)
                                                                   for p in sorted({v["process"] for v in parts.values()})},
                     "parts": parts if len(parts) <= 25 else "omitted"}
    return r
