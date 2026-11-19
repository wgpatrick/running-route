"""Features the suppliers' CNC-milling and 3D-printing rules speak about, measured on any solid.

Everything here measures; nothing judges (the rules are applied by mechloop/shops/process_rules.py). A part is read
from its exact B-rep (faces, edges, cylinders: corner radii, holes, pins, flat overhangs and what holds them) and from
the triangle mesh sampled over its surface (rays: tool access, wall thickness, gaps). Design metadata is used where it
exists: thread callouts (screws that thread into the part, `meta["threads"]`), the print orientation and print
settings. The part is measured in its own frame (dfm_geom.part_frame); "the six principal directions" are that frame's
+-X, +-Y, +-Z.

Machined parts (`machined_features`):
- tool access: every B-rep face is sampled on its own triangulation and each sample is tested from each of the six
  directions (a straight cutter along -d reaches it when the face does not face away from d and a ray towards d
  escapes the part). A face no direction reaches over at least 10 % of its area is inaccessible (undercut or
  internal). The fewest directions that reach every reachable sample (exhaustive over the 63 sets) is the set-up
  count; faces lying on the bounding box (stock faces) need no cutter of their own;
- vertical inside corners: concave cylindrical faces that are not holes (fillets), with radius, depth (their length
  along the axis) and the direction a cutter comes from; sharp straight inside edges no square-on cutter can form
  (dfm_geom.sharp_inside_edges with no reach) are corners of radius 0;
- pockets: flat floors facing a principal direction below the top of the part, with depth (height of the walls round
  them), depth below the face they are cut from, width (largest circle that fits the floor), length (longest side),
  the corner radii round them and the largest cutter that fits;
- slots: the narrowest gap between two facing walls a cutter reaches, with its depth towards the opening;
- holes (dfm_geom.holes): diameter, depth, through or blind, axis direction;
- threads: from screws that thread into the part and from `meta["threads"]` callouts, each matched to the modelled
  hole it is called out on (modelled diameter, hole depth, plain depth left below a blind thread);
- walls: the thinnest walls (two near-parallel faces), each with its free height along the cutter direction.

Printed parts (`printed_features`), in the print orientation:
- walls across the layers and skins lying in them, the thinnest walls classed supported (joined to thicker material
  on two or more sides) or unsupported;
- overhang area by angle from vertical (down-facing surface not on the bed; crowns of horizontal holes up to 10 mm
  and flat ceilings bridged between two supports are taken out and reported separately);
- flat overhangs from the B-rep: each down-facing flat face, the edges where material continues downwards (its
  supports), and from them the longest unsupported cantilever or the bridge span;
- pins and bosses (convex cylinders) with diameter and height, holes with diameter, depth and whether horizontal,
  enclosed voids (an inner shell), threads, the part's size in the print orientation;
- optional PrusaSlicer cross-check (`prusaslicer_support`): slice with support enabled and count support material.

Limits (stated in the features as "limits"): text and engraving are not read; helical thread geometry is not
recognised (threads come from metadata); teardrop holes are not recognised; floor fillets are not measured; a pocket
without a floor (a through window) is seen only through its walls (slots); the wall height is measured along the
principal directions only.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from itertools import combinations
from pathlib import Path

import numpy as np
from build123d import GeomType, Vector

from . import dfm_geom as G

AXES_ORDER = ("+Z", "-Z", "+X", "-X", "+Y", "-Y")
REACH_FACE_MIN = 0.9          # a face is cut from a direction that reaches this share of its samples
INACCESSIBLE_MIN = 0.10       # a face no direction reaches over this share of its area is inaccessible
THIN_PROBE_MM = 3.0           # walls thinner than this are listed (every rule in the data is below it)
HOLE_CROWN_MAX_MM = 10.0      # horizontal holes up to this diameter print their crown without support (dfm_rules)
BRIDGE_EXCUSE_MM = 30.0       # flat ceilings bridged up to this span are bridges, not overhangs (dfm_rules fdm.bridge_max_mm)
LIMITS = ["text and engraving not read", "helical thread geometry not recognised (threads from metadata)",
          "teardrop or flat-top holes not recognised", "floor fillets not measured", "through windows seen through their walls only",
          "wall height measured along the principal directions only"]


# ------------------------------------------------------------------------------------------- helpers
def _face_samples(shape, max_per_face: int = 24) -> tuple[list, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """(faces, points, normals, areas, face index) from each face's own triangulation (the one to_trimesh made)."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_REVERSED
    from OCP.TopLoc import TopLoc_Location

    BRepMesh_IncrementalMesh(shape.wrapped, 0.05, False, 0.3, True)
    faces = list(shape.faces())
    P, N, A, F = [], [], [], []
    for i, f in enumerate(faces):
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f.wrapped, loc)
        if tri is None:
            continue
        trsf = loc.Transformation()
        nodes = np.array([[(p := tri.Node(k).Transformed(trsf)).X(), p.Y(), p.Z()] for k in range(1, tri.NbNodes() + 1)])
        ids = np.array([[t.Value(1), t.Value(2), t.Value(3)] for t in tri.Triangles()]) - 1
        if not len(ids):
            continue
        a, b, c = nodes[ids[:, 0]], nodes[ids[:, 1]], nodes[ids[:, 2]]
        cr = np.cross(b - a, c - a)
        area = 0.5 * np.linalg.norm(cr, axis=1)
        n = cr / np.maximum(2 * area[:, None], 1e-12)
        if f.wrapped.Orientation() == TopAbs_REVERSED:
            n = -n
        cen = (a + b + c) / 3.0
        keep = area > 1e-9
        cen, n, area = cen[keep], n[keep], area[keep]
        if len(cen) > max_per_face:
            # the largest triangles carry the area; their weights are scaled so the face's area is kept
            order = np.argsort(-area)[:max_per_face]
            tot = area.sum()
            cen, n, area = cen[order], n[order], area[order] * tot / area[order].sum()
        P.append(cen)
        N.append(n)
        A.append(area)
        F.append(np.full(len(cen), i))
    if not P:
        z = np.zeros((0, 3))
        return faces, z, z, np.zeros(0), np.zeros(0, dtype=int)
    return faces, np.vstack(P), np.vstack(N), np.concatenate(A), np.concatenate(F)


def _clear(sm: G.Sampled, pts: np.ndarray, nrm: np.ndarray, d: np.ndarray) -> np.ndarray:
    if not len(pts):
        return np.zeros(0, dtype=bool)
    dist, _ = G.ray_hits(sm.tris, pts + nrm * 0.02 + d * 1e-4, np.repeat(d[None], len(pts), axis=0))
    return ~np.isfinite(dist)


def _inside_thickness(sm: G.Sampled, q: np.ndarray, n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """For points q and one direction n: (inside, thickness along +-n) from two rays and the facing of what they hit."""
    if not len(q):
        return np.zeros(0, dtype=bool), np.zeros(0)
    nn = np.repeat(n[None], len(q), axis=0)
    d1, h1 = G.ray_hits(sm.tris, q, nn)
    d2, h2 = G.ray_hits(sm.tris, q, -nn)
    ok = (h1 >= 0) & (h2 >= 0)
    inside = np.zeros(len(q), dtype=bool)
    inside[ok] = (np.einsum("ij,ij->i", sm.tri_n[h1[ok]], nn[ok]) > 0.2) & (np.einsum("ij,ij->i", sm.tri_n[h2[ok]], -nn[ok]) > 0.2)
    return inside, np.where(inside, d1 + d2, np.inf)


def _robust_min(vals: np.ndarray, w: np.ndarray, area_mm2: float = 1.0) -> float | None:
    ok = np.isfinite(vals)
    if not ok.any():
        return None
    v, ww = vals[ok], w[ok]
    order = np.argsort(v)
    cum = np.cumsum(ww[order])
    k = int(np.searchsorted(cum, min(area_mm2, cum[-1] * 0.5)))
    return round(float(v[order][min(k, len(v) - 1)]), 3)


def _dir_name(axes: dict, v) -> str | None:
    for nm, a in axes.items():
        if a @ v > 0.999:
            return nm
    return None


def _near_axis(frame: np.ndarray, v: np.ndarray) -> bool:
    return float(np.max(np.abs(frame @ v))) > 0.9995


# ------------------------------------------------------------------------------------- tool access
def tool_access(shape, sm: G.Sampled, frame: np.ndarray) -> dict:
    """Which principal directions a straight cutter reaches each face from, the inaccessible faces and the set-ups."""
    axes = G.axis_names(frame)
    names = [nm for nm in AXES_ORDER if nm in axes]
    faces, P, N, A, F = _face_samples(shape)
    lo, hi = G.extents(sm, frame)
    reach = np.zeros((len(P), len(names)), dtype=bool)
    for j, nm in enumerate(names):
        d = axes[nm]
        facing = N @ d > -0.02
        idx = np.nonzero(facing)[0]
        reach[idx, j] = _clear(sm, P[idx], N[idx], d)
    pf, nf = P @ frame.T, N @ frame.T
    stock = np.zeros(len(P), dtype=bool)
    for k in range(3):
        stock |= (nf[:, k] > 0.999) & (np.abs(pf[:, k] - hi[k]) < 0.05)
        stock |= (nf[:, k] < -0.999) & (np.abs(pf[:, k] - lo[k]) < 0.05)
    per_face, inaccessible = [], []
    for i, f in enumerate(faces):
        m = F == i
        if not m.any():
            continue
        a = A[m]
        tot = float(a.sum())
        frac = {names[j]: float(a[reach[m, j]].sum() / max(tot, 1e-12)) for j in range(len(names))}
        none = float(a[~reach[m].any(axis=1)].sum())
        dirs = sorted(nm for nm, v in frac.items() if v >= REACH_FACE_MIN)
        row = {"face": i, "area_mm2": round(tot, 2), "dirs": dirs, "stock": bool(stock[m].all()), "type": f.geom_type.name}
        per_face.append(row)
        if none > INACCESSIBLE_MIN * tot and none > 0.5:
            c = f.center()
            inaccessible.append({"face": i, "area_mm2": round(none, 2), "at": G.xyz([c.X, c.Y, c.Z]), "type": f.geom_type.name})
    need = ~stock & reach.any(axis=1)
    best = None
    for k in range(1, len(names) + 1):
        for S in combinations(range(len(names)), k):
            cov = reach[:, list(S)].any(axis=1)
            if (cov | ~need).all():
                score = float(A[reach[:, list(S)].any(axis=1)].sum())
                if best is None or score > best[1]:
                    best = (S, score)
        if best is not None:
            break
    setup_dirs = sorted(names[j] for j in best[0]) if best else []
    return {"faces": len(faces), "per_face": per_face, "inaccessible": inaccessible,
            "inaccessible_area_mm2": round(sum(x["area_mm2"] for x in inaccessible), 2),
            "setups": len(setup_dirs), "setup_dirs": setup_dirs, "stock_faces": sum(1 for r in per_face if r["stock"])}


# ------------------------------------------------------------------------------------ inside corners
def vertical_corners(shape, sm: G.Sampled, frame: np.ndarray, cyls: list, holes: list) -> list[dict]:
    """Vertical inside corners: fillets (concave partial cylinders on a principal axis that are not holes) and sharp
    inside edges no square-on cutter can form; each with radius, depth and the direction a cutter comes from."""
    axes = G.axis_names(frame)
    out = []
    for cy in cyls:
        if not cy.concave or cy.angle >= 300 or not _near_axis(frame, cy.axis):
            continue
        if any(abs(h.diameter / 2 - cy.radius) < 1e-3 and np.linalg.norm(np.cross(cy.origin - h.origin, h.axis)) < 0.02
               and abs(abs(h.axis @ cy.axis) - 1) < 1e-4 for h in holes):
            continue
        rel = cy.mid - cy.origin
        foot = cy.origin + cy.axis * (rel @ cy.axis)
        v = foot - cy.mid
        nv = np.linalg.norm(v)
        if nv < 1e-9:
            continue
        p_air = cy.mid + v / nv * min(0.3, 0.5 * cy.radius)
        opens = []
        for s in (1.0, -1.0):
            d, _ = G.ray_hits(sm.tris, p_air[None], (s * cy.axis)[None])
            if not np.isfinite(d[0]):
                opens.append(_dir_name(axes, s * cy.axis))
        if not opens:
            continue
        out.append({"radius": round(cy.radius, 3), "depth": round(cy.hi - cy.lo, 3), "approach": [o for o in opens if o],
                    "at": G.xyz(cy.mid), "kind": "fillet", "axis": _dir_name(axes, cy.axis) or _dir_name(axes, -cy.axis)})
    for e in G.sharp_inside_edges(shape, sm, frame):
        if e["reach"]:
            continue
        t = np.asarray(e["along"], dtype=float)
        if not _near_axis(frame, t):
            continue
        n1, n2 = e["normals"]
        m = np.asarray(e["at"], dtype=float)
        p_air = m + 0.05 * (n1 + n2)
        opens = []
        for s in (1.0, -1.0):
            d, _ = G.ray_hits(sm.tris, p_air[None], (s * t)[None])
            if not np.isfinite(d[0]):
                opens.append(_dir_name(axes, s * t))
        out.append({"radius": 0.0, "depth": round(float(e["length"]), 3), "approach": [o for o in opens if o], "at": e["at"],
                    "kind": "sharp", "axis": _dir_name(axes, t) or _dir_name(axes, -t)})
    return out


# ------------------------------------------------------------------------------------------- pockets
def _faces_floor(floor, wall, edge, d: np.ndarray) -> bool:
    """Does `wall` face the air above `floor` along their shared edge (a pocket or step wall), rather than face away
    from it (the outside of a plate beside a notch's bottom)?"""
    if edge is None:
        return False
    try:
        m = G._vec(edge.position_at(0.5))
        t = G._vec(edge.tangent_at(0.5))
        gn = G._vec(wall.normal_at(Vector(*m)))
    except Exception:
        return False
    w = np.cross(d, t)
    if np.linalg.norm(w) < 1e-9:
        return False
    w /= np.linalg.norm(w)
    for s in (1.0, -1.0):
        try:
            if floor.distance_to(Vector(*(m + s * w * 0.1))) < 0.02:
                return float(gn @ (s * w)) > 0.3
        except Exception:
            return False
    return False


def _is_hole_wall(g, holes: list) -> bool:
    """A cylindrical face that is a hole's or counterbore's bore (a counterbore's floor is not a pocket)."""
    if g.geom_type != GeomType.CYLINDER:
        return False
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    cy = BRepAdaptor_Surface(g.wrapped).Cylinder()
    r = cy.Radius()
    o, a = G._vec(cy.Axis().Location()), G._vec(cy.Axis().Direction())
    for h in holes:
        if abs(abs(a @ h.axis) - 1) > 1e-4 or np.linalg.norm(np.cross(o - h.origin, h.axis)) > 0.02:
            continue
        if any(abs(2 * r - dd) < 2e-3 for dd in [h.diameter] + [s_[0] for s_ in h.steps]):
            return True
    return False


def pockets(shape, frame: np.ndarray, access: dict, corners: list, holes: list = ()) -> list[dict]:
    """Flat floors facing a principal direction below the top of the part, with the walls that rise round them."""
    from shapely.geometry import Point, Polygon

    from . import dfm_sheet as DS

    axes = G.axis_names(frame)
    faces, pairs = G.shared_edges(shape)
    nbr: dict[int, set] = {}
    edge_of: dict[tuple, object] = {}
    for e, i, j in pairs:
        nbr.setdefault(i, set()).add(j)
        nbr.setdefault(j, set()).add(i)
        edge_of[(i, j)] = edge_of[(j, i)] = e
    reach_of = {r["face"]: set(r["dirs"]) for r in access["per_face"]}
    verts = np.array([[v.X, v.Y, v.Z] for v in shape.vertices()]) if shape.vertices() else np.zeros((0, 3))
    out = []
    for i, f in enumerate(faces):
        if f.geom_type != GeomType.PLANE:
            continue
        n = G._vec(f.normal_at(f.center()))
        nm = _dir_name(axes, n)
        if nm is None or nm not in reach_of.get(i, set()):
            continue
        d = axes[nm]
        level = float(G._vec(f.center()) @ d)
        top = float((verts @ d).max()) if len(verts) else level
        if top - level < 0.05:
            continue
        walls = [j for j in nbr.get(i, ()) if faces[j].geom_type in (GeomType.PLANE, GeomType.CYLINDER)]
        rise = 0.0
        wall_ids = []
        for j in walls:
            g = faces[j]
            if g.geom_type == GeomType.PLANE and abs(G._vec(g.normal_at(g.center())) @ d) > 0.02:
                continue
            if _is_hole_wall(g, holes) or not _faces_floor(f, g, edge_of.get((i, j)), d):
                continue                      # the outside of the part beside the floor (an open side), not a pocket wall
            gv = np.array([[v.X, v.Y, v.Z] for v in g.vertices()])
            if not len(gv):
                continue
            h = float((gv @ d).max()) - level
            if h > 0.05:
                rise = max(rise, h)
                wall_ids.append(j)
        if rise <= 0.05:
            continue
        u = np.cross(d, [1.0, 0, 0] if abs(d[0]) < 0.9 else [0, 1.0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(d, u)
        outer = DS._wire_points(f.outer_wire(), f, u, v)
        inner = [DS._wire_points(w, f, u, v) for w in f.inner_wires()]
        try:
            poly = Polygon(outer, [h for h in inner if len(h) >= 3])
            if not poly.is_valid:
                poly = poly.buffer(0)
            width = DS._width(poly) if not poly.is_empty else None
            length = DS._long(poly) if not poly.is_empty else None
        except Exception:
            width = length = None
        # corners round this floor: those at its level band and inside its outline (in plan)
        radii = []
        for c in corners:
            if nm not in c["approach"]:
                continue
            p = np.asarray(c["at"], dtype=float)
            if not (level - 0.05 <= p @ d <= level + rise + 0.05):
                continue
            try:
                if poly.buffer(max(c["radius"], 0.0) + 0.3).contains(Point(p @ u, p @ v)):
                    radii.append(c["radius"])
            except Exception:
                pass
        tool = width
        if radii and min(radii) > 0 and width is not None:
            tool = min(width, 2 * min(radii))
        c = f.center()
        out.append({"dir": nm, "depth": round(rise, 3), "depth_from_top": round(top - level, 3), "width": None if width is None else round(width, 3),
                    "length": None if length is None else round(length, 3), "corner_radii": sorted(set(round(r, 3) for r in radii)),
                    "tool_d": None if tool is None else round(tool, 3), "floor_area_mm2": round(float(f.area), 2), "at": G.xyz([c.X, c.Y, c.Z])})
    return out


def slots(sm: G.Sampled, frame: np.ndarray, holes: list) -> list[dict]:
    """The narrowest gaps between two facing walls that a cutter reaches, with their depth towards the opening
    (dfm_cnc's slot measure, kept per place)."""
    axes = G.axis_names(frame)
    hole_mask = np.zeros(len(sm.pts), dtype=bool)
    for h in holes:
        rel = sm.pts - h.origin
        ax = rel @ h.axis
        rad = np.linalg.norm(rel - np.outer(ax, h.axis), axis=1)
        hole_mask |= (np.abs(rad - h.diameter / 2) < 0.06) & (np.abs(ax) <= h.depth / 2 + 0.05)
        for dd, _ in h.steps:
            hole_mask |= np.abs(rad - dd / 2) < 0.06
    gp = np.where(hole_mask, np.inf, G.gap_width(sm))
    cand = np.nonzero(np.isfinite(gp) & (gp < 60.0))[0]
    best_depth = np.zeros(len(cand))
    for nm, d in axes.items():
        if not len(cand):
            break
        perp = np.abs(sm.nrm[cand] @ d) < 0.02
        ok = perp & G.clear_along(sm, d)[cand]
        if not ok.any():
            continue
        sub = cand[ok]
        depth, _ = G.ray_hits(sm.tris, sm.pts[sub] - sm.nrm[sub] * 0.02, np.repeat(d[None], len(sub), axis=0))
        depth = np.where(np.isfinite(depth), depth, 0.0)
        cur = best_depth[ok]
        best_depth[ok] = np.where(cur == 0, depth, np.minimum(cur, depth))
    good = best_depth > 0
    idx = cand[good]
    if not len(idx):
        return []
    sel = G.spread(sm.pts[idx], gp[idx], k=8, min_sep=4.0)
    out = []
    for s in sel:
        k = idx[s]
        out.append({"width": round(float(gp[k]), 3), "depth": round(float(best_depth[good][s]), 3),
                    "at": G.xyz(sm.pts[k] + sm.nrm[k] * gp[k] / 2)})
    return out


# ------------------------------------------------------------------------------------------- walls
def thin_walls(sm: G.Sampled, frame: np.ndarray, up: np.ndarray | None = None, probe: float = THIN_PROBE_MM, k: int = 6) -> list[dict]:
    """The thinnest walls (two near-parallel faces, thinner than `probe`): thickness, where, the free height of the
    thin part along each principal direction in the wall's plane, and how many of its four in-plane sides run into
    thicker material (2 or more: supported)."""
    wp = G.wall_thickness(sm, parallel=0.97)
    m = np.isfinite(wp) & (wp < probe)
    if up is not None:
        m &= np.abs(sm.nrm @ up) <= 0.7          # walls across the layers; skins in the layers are listed apart
    idx = np.nonzero(m)[0]
    if not len(idx):
        return []
    sel = G.spread(sm.pts[idx], wp[idx], k=k, min_sep=4.0)
    axes = G.axis_names(frame)
    out = []
    step = 0.5
    steps = np.arange(step, 80.0 + 1e-9, step)
    for s in sel:
        i = idx[s]
        t = float(wp[i])
        n = sm.nrm[i]
        mid = sm.pts[i] - n * (t / 2)
        runs = {}
        rooted = 0
        for nm in ("+X", "+Y", "+Z"):
            a = axes[nm]
            if abs(a @ n) > 0.1:
                continue
            ends = []
            for sg in (1.0, -1.0):
                q = mid[None] + np.outer(steps, sg * a)
                inside, th = _inside_thickness(sm, q, n)
                end, length = "free", float(steps[-1])
                for j in range(len(q)):
                    if not inside[j]:
                        end, length = "free", float(steps[j])
                        break
                    if th[j] > max(1.8 * t, t + 0.6):
                        end, length = "root", float(steps[j])
                        break
                ends.append((end, length))
            rooted += sum(1 for e, _ in ends if e == "root")
            runs[nm[1]] = {"thin_length_mm": round(ends[0][1] + ends[1][1], 2), "ends": [e for e, _ in ends]}
        # height: the run from where the wall is rooted to its free edge (a standing wall); else, for a strip free at
        # both ends of every run, the shortest run; else (rooted all round) the longest
        height = None
        standing = [r for r in runs.values() if sorted(r["ends"]) == ["free", "root"]]
        loose = [r for r in runs.values() if r["ends"] == ["free", "free"]]
        if standing:
            height = max(r["thin_length_mm"] for r in standing)
        elif loose:
            height = min(r["thin_length_mm"] for r in loose)
        elif runs:
            height = max(r["thin_length_mm"] for r in runs.values())
        out.append({"t": round(t, 3), "at": G.xyz(sm.pts[i]), "normal": G.xyz(n), "rooted_sides": rooted, "supported": rooted >= 2,
                    "height_mm": None if height is None else round(height, 2), "runs": runs})
    return out


# ------------------------------------------------------------------------------------------- threads
def _thread_callouts(design, c, sm: G.Sampled) -> list[dict]:
    out = []
    try:
        for tp in G.tapped_holes(design, c, sm):
            out.append({"d": float(tp["d"]), "pitch": tp.get("pitch"), "depth": round(float(tp["engagement"]), 3), "at": tp["at"],
                        "axis": G.xyz(-np.asarray(tp["dir"], dtype=float)), "from": f"screw {tp['screw']}",
                        "beyond_tip": round(float(tp["beyond_tip"]), 3)})
    except Exception:
        pass
    for th in (c.meta.get("threads") or []):
        size = str(th.get("size") or "")
        d = th.get("d")
        pitch = th.get("pitch")
        if d is None and size.upper().startswith("M"):
            body = size[1:].lower().replace(" ", "")
            dd, _, pp = body.partition("x")
            d = float(dd)
            pitch = float(pp) if pp else pitch
        if d is None:
            raise ValueError(f"{c.name}: thread callout {th!r} needs 'size' like 'M4x0.7' or 'd'")
        out.append({"d": float(d), "pitch": pitch, "depth": th.get("depth"), "at": G.xyz(th["at"]) if th.get("at") is not None else None,
                    "axis": G.xyz(th["axis"]) if th.get("axis") is not None else None, "from": "meta['threads']", "size": size or f"M{d:g}"})
    return out


def match_threads(threads: list[dict], holes: list) -> list[dict]:
    """Attach to each thread callout the modelled hole it sits in (axis parallel, callout point near the axis)."""
    for th in threads:
        th["hole"] = None
        if th.get("at") is None:
            continue
        p = np.asarray(th["at"], dtype=float)
        best = None
        for h in holes:
            if th.get("axis") is not None and abs(abs(np.asarray(th["axis"], dtype=float) @ h.axis) - 1) > 1e-3:
                continue
            off = np.linalg.norm(np.cross(p - h.origin, h.axis))
            if off > h.diameter / 2 + 0.6:
                continue
            along = abs((p - h.origin) @ h.axis)
            if along > h.depth / 2 + 1.0:
                continue
            if best is None or off < best[0]:
                best = (off, h)
        if best is None:
            continue
        h = best[1]
        th["hole"] = {"d": round(h.diameter, 3), "depth": round(h.depth, 3), "through": bool(h.through), "at": G.xyz(h.origin)}
        if th.get("depth") is not None and not h.through:
            th["plain_below_mm"] = round(h.depth - float(th["depth"]), 3)
        elif th.get("beyond_tip") is not None and not h.through:
            th["plain_below_mm"] = th["beyond_tip"]
    return threads


# ------------------------------------------------------------------------------------------ machined
def machined_features(design, c, sm: G.Sampled, frame: np.ndarray, cyls: list, holes: list) -> dict:
    shape = c.shape
    lo, hi = G.extents(sm, frame)
    axes = G.axis_names(frame)
    access = tool_access(shape, sm, frame)
    corners = vertical_corners(shape, sm, frame, cyls, holes)
    pk = pockets(shape, frame, access, corners, holes)
    sl = slots(sm, frame, holes)
    walls = thin_walls(sm, frame)
    wp = G.wall_thickness(sm, parallel=0.97)
    threads = match_threads(_thread_callouts(design, c, sm), holes)
    fc = G.face_classes(shape, frame)
    hl = [{"d": round(h.diameter, 3), "depth": round(h.depth, 3), "through": bool(h.through), "at": G.xyz(h.origin),
           "axis": _dir_name(axes, h.axis) or _dir_name(axes, -h.axis) or "angled", "counterbores": [list(s) for s in h.steps]} for h in holes]
    return {"process": "cnc_milling", "material": c.material, "extents_mm": [round(float(x), 2) for x in sorted(hi - lo)],
            "volume_mm3": round(float(shape.volume), 1), "access": {k: v for k, v in access.items() if k != "per_face"},
            "corners": corners, "pockets": pk, "slots": sl, "holes": hl, "threads": threads,
            "min_wall_mm": _robust_min(wp, sm.w), "thin_walls": walls, "angled_cylinders": fc["angled_cyls"],
            "angled_at": fc["angled_at"][:6], "limits": LIMITS}


# ------------------------------------------------------------------------------------------- printed
def flat_overhangs(shape, up: np.ndarray, zmin: float) -> list[dict]:
    """Each down-facing flat face above the bed: where material continues downwards from its edges (supports), and
    from them its longest cantilever, or its bridge span when it is held on opposite sides."""
    from shapely.geometry import LineString, MultiPoint, Point, Polygon
    from shapely.ops import unary_union

    from . import dfm_sheet as DS

    faces, pairs = G.shared_edges(shape)
    adj: dict[int, list] = {}
    for e, i, j in pairs:
        adj.setdefault(i, []).append((e, j))
        adj.setdefault(j, []).append((e, i))
    out = []
    for i, f in enumerate(faces):
        if f.geom_type != GeomType.PLANE:
            continue
        n = G._vec(f.normal_at(f.center()))
        if n @ up > -0.98:
            continue
        level = float(G._vec(f.center()) @ up)
        if level - zmin < 0.3:
            continue
        u = np.cross(up, [1.0, 0, 0] if abs(up[0]) < 0.9 else [0, 1.0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(up, u)
        try:
            poly = Polygon(DS._wire_points(f.outer_wire(), f, u, v), [h for h in (DS._wire_points(w, f, u, v) for w in f.inner_wires()) if len(h) >= 3])
            if not poly.is_valid:
                poly = poly.buffer(0)
        except Exception:
            continue
        if poly.is_empty or poly.area < 0.5:
            continue
        sup = []
        for e, j in adj.get(i, []):
            g = faces[j]
            a, b = G._vec(e.position_at(0.0)), G._vec(e.position_at(1.0))
            m = G._vec(e.position_at(0.5))
            t = b - a
            if np.linalg.norm(t) < 1e-9:
                t = G._vec(e.tangent_at(0.5))
            t = t / np.linalg.norm(t)
            try:
                gn = G._vec(g.normal_at(Vector(*m)))
            except Exception:
                continue
            w = np.cross(gn, t)
            if np.linalg.norm(w) < 1e-9:
                continue
            w /= np.linalg.norm(w)
            down = None
            for s in (1.0, -1.0):
                q = m + s * w * 0.2
                try:
                    if g.distance_to(Vector(*q)) < 0.03:
                        down = (s * w) @ up < -0.3
                        break
                except Exception:
                    continue
            if down:
                pts = [(p @ u, p @ v) for p in (G._vec(e.position_at(k / 8)) for k in range(9))]
                sup.append(LineString(pts))
        c = f.center()
        rec = {"face": i, "area_mm2": round(float(f.area), 2), "level": round(level - zmin, 3), "at": G.xyz([c.X, c.Y, c.Z])}
        minx, miny, maxx, maxy = poly.bounds
        step = max(0.5, max(maxx - minx, maxy - miny) / 40.0)
        gx, gy = np.meshgrid(np.arange(minx + step / 2, maxx, step), np.arange(miny + step / 2, maxy, step))
        cand = [Point(x, y) for x, y in zip(gx.ravel(), gy.ravel())]
        pts = [p for p in cand if poly.contains(p)] or [poly.representative_point()]
        if not sup:
            rec.update({"kind": "floating", "supports": 0, "length_mm": round(math.hypot(maxx - minx, maxy - miny), 2)})
            out.append(rec)
            continue
        S = unary_union(sup)
        dists = np.array([S.distance(p) for p in pts])
        k = int(np.argmax(dists))
        D = float(dists[k])
        far = pts[k]
        # bridge if supports lie on opposite sides of the farthest point
        near = [g for g in (S.geoms if hasattr(S, "geoms") else [S])]
        dirs = []
        for g in near:
            if g.distance(far) <= 1.25 * D + 1e-6:
                from shapely.ops import nearest_points
                q = nearest_points(far, g)[1]
                vv = np.array([q.x - far.x, q.y - far.y])
                if np.linalg.norm(vv) > 1e-9:
                    dirs.append(vv / np.linalg.norm(vv))
        opposite = any(float(a @ b) < -0.5 for a in dirs for b in dirs)
        world_far = G.xyz(far.x * u + far.y * v + level * up)
        if opposite:
            rec.update({"kind": "bridge", "supports": len(near), "span_mm": round(2 * D, 2), "far_at": world_far})
        else:
            rec.update({"kind": "cantilever", "supports": len(near), "length_mm": round(D, 2), "far_at": world_far})
        _ = MultiPoint
        out.append(rec)
    return out


def printed_features(design, c, sm: G.Sampled, frame: np.ndarray, cyls: list, holes: list, up=None, settings: dict | None = None) -> dict:
    from .. import printsettings as PS

    shape = c.shape
    settings = dict(settings or PS.settings_for(c)[0])
    if up is None:
        bd, _ = PS.build_direction(c, settings)
        up = bd if bd is not None else frame[2]
    up = np.asarray(up, dtype=float)
    up = up / np.linalg.norm(up)
    h = sm.pts @ up
    zmin = float((np.asarray(sm.mesh.vertices) @ up).min())
    down = sm.nrm @ up
    on_bed = (down < -0.98) & (h - zmin < 0.3)
    # walls across the layers, skins in them
    wp = G.wall_thickness(sm, parallel=0.97)
    flat = np.abs(sm.nrm @ up) > 0.7
    walls = thin_walls(sm, frame, up)
    # crowns of horizontal holes up to 10 mm, and flat ceilings bridged by B-rep analysis, are not overhangs
    excused = np.zeros(len(sm.pts), dtype=bool)
    hl = []
    for hh in holes:
        horiz = abs(hh.axis @ up) < 0.3
        hl.append({"d": round(hh.diameter, 3), "depth": round(hh.depth, 3), "through": bool(hh.through), "horizontal": bool(horiz),
                   "vertical": bool(abs(abs(hh.axis @ up) - 1) < 1e-3), "at": G.xyz(hh.origin)})
        if horiz and hh.diameter <= HOLE_CROWN_MAX_MM + 1e-9:
            rel = sm.pts - hh.origin
            ax = rel @ hh.axis
            rad = np.linalg.norm(rel - np.outer(ax, hh.axis), axis=1)
            excused |= (np.abs(rad - hh.diameter / 2) < 0.06) & (np.abs(ax) <= hh.depth / 2 + 0.05)
    fo = flat_overhangs(shape, up, zmin)
    faces = list(shape.faces())
    bridged_faces = {r["face"] for r in fo if r["kind"] == "bridge" and r["span_mm"] <= BRIDGE_EXCUSE_MM}
    if bridged_faces:
        # samples on those faces: same plane level and inside the face (by distance to the face)
        for fi in bridged_faces:
            f = faces[fi]
            lvl = float(G._vec(f.center()) @ up)
            cand = np.nonzero((down < -0.98) & (np.abs(h - lvl) < 0.02))[0]
            for s in cand:
                try:
                    if f.distance_to(Vector(*sm.pts[s])) < 0.05:
                        excused[s] = True
                except Exception:
                    pass
    downward = (down < -1e-6) & ~on_bed
    alpha = np.degrees(np.arcsin(np.clip(-down, 0.0, 1.0)))          # 0: vertical wall, 90: flat ceiling
    bins = {}
    for a_, w_ in zip(alpha[downward & ~excused], sm.w[downward & ~excused]):
        b = int(min(89, math.floor(a_)))
        bins[b] = bins.get(b, 0.0) + float(w_)
    over_pts = {}
    for lim_deg in (19, 30, 45, 60):
        sel = np.nonzero(downward & ~excused & (alpha > lim_deg))[0]
        over_pts[str(lim_deg)] = [G.xyz(sm.pts[i]) for i in (sel[G.spread(sm.pts[sel], -sm.w[sel], k=5, min_sep=6.0)] if len(sel) else [])]
    pins = []
    for cy in cyls:
        if cy.concave or cy.angle < 180 or (cy.hi - cy.lo) <= cy.radius:
            continue
        pins.append({"d": round(2 * cy.radius, 3), "height": round(cy.hi - cy.lo, 3), "at": G.xyz(cy.mid),
                     "vertical": bool(abs(abs(cy.axis @ up) - 1) < 1e-3)})
    voids = sum(max(0, len(s.shells()) - 1) for s in shape.solids())
    side = [a for a in frame if abs(a @ up) < 0.5]
    v = np.asarray(sm.mesh.vertices)
    lat = sorted(float(np.ptp(v @ a)) for a in side)
    threads = match_threads(_thread_callouts(design, c, sm), holes)
    man = (getattr(design, "manufacturing", None) or {}) if design is not None else {}
    printer = man.get("printer") or {}
    return {"process": "fdm", "material": c.material, "up": G.xyz(up),
            "extents_mm": [round(float(x), 2) for x in sorted(lat + [float(np.ptp(v @ up))])],
            "size_in_orientation_mm": {"lateral": [round(x, 2) for x in lat], "height": round(float(np.ptp(v @ up)), 2)},
            "volume_mm3": round(float(shape.volume), 1),
            "min_wall_mm": _robust_min(np.where(flat, np.inf, wp), sm.w), "min_skin_mm": _robust_min(np.where(flat, wp, np.inf), sm.w),
            "thin_walls": walls, "overhang_bins": {str(k): round(v_, 2) for k, v_ in sorted(bins.items())}, "overhang_at": over_pts,
            "flat_overhangs": fo, "pins": pins, "holes": hl, "enclosed_voids": int(voids), "threads": threads,
            "settings": {"nozzle_mm": float((printer.get("nozzle") or 0.4)), "line_width_mm": float(settings.get("line_width_mm", 0.45)),
                         "layer_height_mm": float(settings.get("layer_height_mm", 0.2))},
            "build_volume_mm": list(printer.get("build_volume")) if printer.get("build_volume") else None,
            "hole_crowns_excused_up_to_mm": HOLE_CROWN_MAX_MM, "bridges_excused_up_to_mm": BRIDGE_EXCUSE_MM, "limits": LIMITS}


# ------------------------------------------------------------------------------------- PrusaSlicer
def prusaslicer_support(c, up, nozzle: float = 0.4, layer: float = 0.2, timeout: int = 300) -> dict | None:
    """Slice the part with PrusaSlicer, build direction `up` turned to +Z, support enabled (auto), and read back the
    extrusion by feature type (filament mm). None when prusa-slicer is not installed."""
    exe = shutil.which("prusa-slicer")
    if not exe:
        return None
    from ..geom import to_trimesh

    m = to_trimesh(c.shape).copy()
    up = np.asarray(up, dtype=float) / np.linalg.norm(up)
    z = np.array([0.0, 0, 1])
    axis = np.cross(up, z)
    s, cth = np.linalg.norm(axis), float(up @ z)
    R = np.eye(3)
    if s > 1e-9:
        k = axis / s
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
        R = np.eye(3) + s * K + (1 - cth) * K @ K
    elif cth < 0:
        R = np.diag([1.0, -1.0, -1.0])
    vv = np.asarray(m.vertices) @ R.T
    vv -= [vv[:, 0].mean(), vv[:, 1].mean(), vv[:, 2].min()]
    m.vertices = vv
    with tempfile.TemporaryDirectory() as td:
        stl, gc = Path(td) / "p.stl", Path(td) / "p.gcode"
        m.export(stl)
        cmd = [exe, "--export-gcode", str(stl), "--output", str(gc), "--layer-height", str(layer), "--first-layer-height", str(layer),
               "--nozzle-diameter", str(nozzle), "--support-material", "--support-material-auto", "--gcode-comments", "--use-relative-e-distances",
               "--bed-shape", "-150x-150,150x-150,150x150,-150x150", "--center", "0,0", "--skirts", "0"]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0 or not gc.exists():
            return {"ok": False, "error": (p.stderr or p.stdout)[-300:]}
        by: dict[str, float] = {}
        cur = None
        for line in gc.read_text(errors="replace").splitlines():
            if line.startswith(";TYPE:"):
                cur = line[6:].strip()
                continue
            if cur and line.startswith(("G1 ", "G0 ")) and " E" in line:
                try:
                    e = float(line.split(" E")[1].split()[0].split(";")[0])
                except ValueError:
                    continue
                if e > 0:
                    by[cur] = by.get(cur, 0.0) + e
    sup = sum(v for k, v in by.items() if k.lower().startswith("support material"))
    return {"ok": True, "support_mm": round(sup, 1), "overhang_perimeter_mm": round(by.get("Overhang perimeter", 0.0), 1),
            "bridge_infill_mm": round(by.get("Bridge infill", 0.0), 1), "by_type_mm": {k: round(v, 1) for k, v in sorted(by.items())},
            "how": "prusa-slicer --support-material --support-material-auto, layer %g mm, nozzle %g mm; build direction turned to +Z" % (layer, nozzle)}
