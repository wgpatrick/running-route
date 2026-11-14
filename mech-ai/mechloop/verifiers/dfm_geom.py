"""Geometry measurements shared by the manufacturability checks.

Everything here measures; nothing judges. A part is read two ways: its exact B-rep (planes, cylinders,
cones: hole diameters, corner radii, axes) and a triangle mesh sampled evenly over the surface, from
which rays are cast (wall thickness, the gap to the opposite wall, line of sight for a cutter or the
nozzle). Parts are measured in their own frame (the directions their largest flat faces are square to),
so a part that sits at an angle in the assembly is judged the same as one that sits square.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from build123d import GeomType, Vector
from OCP.BRepAdaptor import BRepAdaptor_Surface

from ..geom import to_trimesh

EPS = 1e-6


# ----------------------------------------------------------------------------------------- frame
def part_frame(shape) -> np.ndarray:
    """Rows are the part's own X, Y, Z directions in world coordinates: Z is the normal carrying the most
    flat area, X the normal square to it carrying the most of the rest. World axes win ties, so a part that
    is already square to the world keeps the world's names for its directions."""
    acc: dict[tuple, float] = {}
    for f in shape.faces():
        if f.geom_type == GeomType.PLANE:
            n = f.normal_at(f.center())
            v = np.array([n.X, n.Y, n.Z])
        elif f.geom_type == GeomType.CYLINDER:
            d = BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Direction()
            v = np.array([d.X(), d.Y(), d.Z()])
        else:
            continue
        k = int(np.argmax(np.abs(v)))
        if v[k] < 0:
            v = -v
        key = tuple(np.round(v, 3))
        acc[key] = acc.get(key, 0.0) + f.area
    world = np.eye(3)
    if not acc:
        return world

    def axis_bonus(v):   # prefer world axes when areas are close
        return 1.05 if max(abs(v)) > 0.999 else 1.0

    dirs = sorted(acc, key=lambda k_: -acc[k_] * axis_bonus(np.array(k_)))
    z = np.array(dirs[0], dtype=float)
    z /= np.linalg.norm(z)
    x = None
    for k_ in dirs[1:]:
        v = np.array(k_, dtype=float)
        if abs(v @ z) < 0.02:
            x = v - (v @ z) * z
            x /= np.linalg.norm(x)
            break
    if x is None:
        x = world[int(np.argmin(np.abs(z)))]
        x = x - (x @ z) * z
        x /= np.linalg.norm(x)
    y = np.cross(z, x)
    fr = np.array([x, y, z])
    # name the frame's axes after the world axes they are nearest to, and point them the same way
    order, used = [], set()
    out = np.zeros((3, 3))
    for i in range(3):
        best = max((j for j in range(3) if j not in used), key=lambda j: abs(fr[j][i]))
        used.add(best)
        v = fr[best]
        out[i] = v if v[i] >= 0 else -v
    if np.linalg.det(out) < 0:
        out[2] = -out[2]
    return out


def axis_names(frame: np.ndarray) -> dict[str, np.ndarray]:
    """The six tool / build directions of a part frame. Named +X..-Z when the frame is the world's,
    otherwise by the nearest world axis with a trailing ' (part frame)' left to the caller."""
    return {"+X": frame[0], "-X": -frame[0], "+Y": frame[1], "-Y": -frame[1], "+Z": frame[2], "-Z": -frame[2]}


# ------------------------------------------------------------------------------------------ mesh
@dataclass
class Sampled:
    mesh: object
    tris: np.ndarray            # (T, 3, 3)
    tri_n: np.ndarray           # (T, 3)
    pts: np.ndarray             # (S, 3) points spread evenly over the surface
    nrm: np.ndarray             # (S, 3) outward normals there
    w: np.ndarray               # (S,) area each sample stands for, mm^2
    tri_of: np.ndarray          # (S,) triangle each sample lies on
    _acc: dict = field(default_factory=dict)


def sample_surface(shape, n: int = 2000, seed: int = 7) -> Sampled:
    """Points spread over the surface in proportion to area, at least one per triangle that is large
    enough to matter, each with the area it stands for."""
    mesh = to_trimesh(shape)
    tris = np.asarray(mesh.triangles, dtype=float)
    tn = np.asarray(mesh.face_normals, dtype=float)
    area = np.asarray(mesh.area_faces, dtype=float)
    total = float(area.sum())
    rng = np.random.default_rng(seed)
    if total <= 0 or len(tris) == 0:
        z = np.zeros((0, 3))
        return Sampled(mesh, tris, tn, z, z, np.zeros(0), np.zeros(0, dtype=int))
    per = np.maximum(np.round(area / total * n).astype(int), (area > total / (6.0 * n)).astype(int))
    if per.sum() == 0:
        per[int(np.argmax(area))] = 1
    idx = np.repeat(np.arange(len(tris)), per)
    k = len(idx)
    # stratified barycentric points: reproducible and reasonably even inside each triangle
    r1 = np.sqrt(rng.random(k))
    r2 = rng.random(k)
    a, b, c = tris[idx, 0], tris[idx, 1], tris[idx, 2]
    pts = (1 - r1)[:, None] * a + (r1 * (1 - r2))[:, None] * b + (r1 * r2)[:, None] * c
    w = area[idx] / per[idx]
    return Sampled(mesh, tris, tn, pts, tn[idx], w, idx)


def ray_hits(tris: np.ndarray, origins: np.ndarray, dirs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Nearest hit of each ray on the triangles: (distance, triangle index); inf and -1 where it escapes.
    Rays that share a direction (every sample on one flat face does) are tested only against the triangles
    whose shadow along that direction covers them; the rest are tested against every triangle."""
    origins = np.asarray(origins, dtype=float)
    R = len(origins)
    dist = np.full(R, np.inf)
    hit = np.full(R, -1, dtype=int)
    if R == 0 or len(tris) == 0:
        return dist, hit
    dirs = np.asarray(dirs, dtype=float)
    if dirs.ndim == 1:
        dist[:], hit[:] = _hits_common(tris, origins, dirs)
        return dist, hit
    key = np.round(dirs, 4)
    uniq, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    inv = inv.reshape(-1)
    loose = np.zeros(R, dtype=bool)
    for g in range(len(uniq)):
        sel = np.nonzero(inv == g)[0]
        if cnt[g] >= 12:
            dist[sel], hit[sel] = _hits_common(tris, origins[sel], dirs[sel[0]])
        else:
            loose[sel] = True
    if loose.any():
        sel = np.nonzero(loose)[0]
        dist[sel], hit[sel] = _hits_brute(tris, origins[sel], dirs[sel])
    return dist, hit


def _hits_common(tris, origins, d):
    d = d / np.linalg.norm(d)
    u = np.cross(d, [1.0, 0.0, 0.0] if abs(d[0]) < 0.9 else [0.0, 1.0, 0.0])
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    tu, tv = tris @ u, tris @ v                       # (T, 3)
    lo_u, hi_u, lo_v, hi_v = tu.min(1), tu.max(1), tv.min(1), tv.max(1)
    pu, pv = origins @ u, origins @ v
    R = len(origins)
    dist = np.full(R, np.inf)
    hit = np.full(R, -1, dtype=int)
    v0 = tris[:, 0]
    e1 = tris[:, 1] - v0
    e2 = tris[:, 2] - v0
    pvec = np.cross(d, e2)                            # same for every ray
    det = np.einsum("tk,tk->t", pvec, e1)
    chunk = max(1, int(4e6 // max(len(tris), 1)))
    eps = 1e-7
    for s in range(0, R, chunk):
        a, b = pu[s:s + chunk, None], pv[s:s + chunk, None]
        m = (a >= lo_u - eps) & (a <= hi_u + eps) & (b >= lo_v - eps) & (b <= hi_v + eps)
        ri, ti = np.nonzero(m)
        if len(ri) == 0:
            continue
        dt = det[ti]
        ok = np.abs(dt) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, dt, 1.0), 0.0)
        tvec = origins[s + ri] - v0[ti]
        uu = np.einsum("ik,ik->i", tvec, pvec[ti]) * inv
        q = np.cross(tvec, e1[ti])
        vv = (q @ d) * inv
        t = np.einsum("ik,ik->i", q, e2[ti]) * inv
        good = ok & (uu >= -1e-9) & (vv >= -1e-9) & (uu + vv <= 1 + 1e-9) & (t > 1e-7)
        ri, ti, t = ri[good], ti[good], t[good]
        if len(ri) == 0:
            continue
        order = np.lexsort((t, ri))
        ri, ti, t = ri[order], ti[order], t[order]
        first = np.concatenate(([True], ri[1:] != ri[:-1]))
        dist[s + ri[first]] = t[first]
        hit[s + ri[first]] = ti[first]
    return dist, hit


def _hits_brute(tris, origins, dirs):
    R = len(origins)
    dist = np.full(R, np.inf)
    hit = np.full(R, -1, dtype=int)
    v0 = tris[:, 0]
    e1 = tris[:, 1] - v0
    e2 = tris[:, 2] - v0
    chunk = max(1, int(1.5e6 // max(len(tris), 1)))
    for s in range(0, R, chunk):
        o = origins[s:s + chunk][:, None, :]
        d = dirs[s:s + chunk][:, None, :]
        p = np.cross(d, e2[None])
        det = np.einsum("rtk,tk->rt", p, e1)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = o - v0[None]
        u = np.einsum("rtk,rtk->rt", tv, p) * inv
        q = np.cross(tv, e1[None])
        v = np.einsum("rtk,rtk->rt", np.broadcast_to(d, q.shape), q) * inv
        t = np.einsum("rtk,tk->rt", q, e2) * inv
        good = ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9) & (t > 1e-7)
        t = np.where(good, t, np.inf)
        j = np.argmin(t, axis=1)
        dd = t[np.arange(len(j)), j]
        dist[s:s + chunk] = dd
        hit[s:s + chunk] = np.where(np.isfinite(dd), j, -1)
    return dist, hit


def wall_thickness(sm: Sampled) -> np.ndarray:
    """Per sample: how far into the material, straight in, until the opposite surface, where that surface
    faces back the other way (a wall or a floor). inf where the far side is not a wall's other face
    (a sharp edge's wedge, a chamfer)."""
    key = "wall"
    if key not in sm._acc:
        d, h = ray_hits(sm.tris, sm.pts - sm.nrm * 1e-4, -sm.nrm)
        ok = h >= 0
        facing = np.zeros(len(d), dtype=bool)
        # the far face must face away from this one (its outward normal along the ray), near enough
        facing[ok] = np.einsum("ij,ij->i", sm.tri_n[h[ok]], -sm.nrm[ok]) > 0.85
        sm._acc[key] = np.where(facing, d + 1e-4, np.inf)
    return sm._acc[key]


def gap_width(sm: Sampled) -> np.ndarray:
    """Per sample: how far out through the air, straight out, to the next surface of the same part where
    that surface faces back (a slot, a pocket's opposite wall). inf where the view is clear."""
    key = "gap"
    if key not in sm._acc:
        d, h = ray_hits(sm.tris, sm.pts + sm.nrm * 1e-4, sm.nrm)
        ok = h >= 0
        facing = np.zeros(len(d), dtype=bool)
        facing[ok] = np.einsum("ij,ij->i", sm.tri_n[h[ok]], sm.nrm[ok]) < -0.85
        sm._acc[key] = np.where(facing, d + 1e-4, np.inf)
    return sm._acc[key]


def clear_along(sm: Sampled, direction: np.ndarray, lift: float = 0.02) -> np.ndarray:
    """Per sample: True where nothing of the part lies beyond it along `direction` (a straight cutter or the
    view from that side reaches it)."""
    key = ("clear", tuple(np.round(direction, 6)), lift)
    if key not in sm._acc:
        d, _ = ray_hits(sm.tris, sm.pts + sm.nrm * lift + direction * 1e-4, np.asarray(direction, dtype=float))
        sm._acc[key] = ~np.isfinite(d)
    return sm._acc[key]


def spread(points: np.ndarray, values: np.ndarray, k: int = 6, min_sep: float = 4.0, worst: str = "min") -> list[int]:
    """Indices of up to k points, worst value first, no two closer than min_sep: one location per place
    a problem occurs rather than a cloud of samples on the same wall."""
    order = np.argsort(values if worst == "min" else -values)
    out: list[int] = []
    for i in order:
        if all(np.linalg.norm(points[i] - points[j]) >= min_sep for j in out):
            out.append(int(i))
            if len(out) >= k:
                break
    return out


def xyz(p) -> list[float]:
    return [round(float(v), 2) for v in p]


# ------------------------------------------------------------------------------------- B-rep faces
@dataclass
class Cyl:
    face: object
    origin: np.ndarray          # a point on the axis
    axis: np.ndarray            # unit direction
    radius: float
    concave: bool               # True: a hole or an inside corner; False: a boss, a pin, an outside round
    angle: float                # degrees swept about the axis
    lo: float                   # extent along the axis, measured from origin
    hi: float
    mid: np.ndarray             # a point on the surface


def _vec(v) -> np.ndarray:
    return np.array([v.X, v.Y, v.Z], dtype=float) if hasattr(v, "X") and not callable(v.X) else np.array([v.X(), v.Y(), v.Z()], dtype=float)


def cylinders(shape) -> list[Cyl]:
    out = []
    for f in shape.faces():
        if f.geom_type != GeomType.CYLINDER:
            continue
        ad = BRepAdaptor_Surface(f.wrapped)
        cyl = ad.Cylinder()
        a = _vec(cyl.Axis().Direction())
        o = _vec(cyl.Axis().Location())
        u0, u1, v0, v1 = ad.FirstUParameter(), ad.LastUParameter(), ad.FirstVParameter(), ad.LastVParameter()
        pm = ad.Value(0.5 * (u0 + u1), 0.5 * (v0 + v1))
        mid = np.array([pm.X(), pm.Y(), pm.Z()])
        radial = mid - (o + ((mid - o) @ a) * a)
        try:
            n = _vec(f.normal_at(Vector(*mid)))
        except Exception:
            continue
        concave = float(n @ radial) < 0
        # V runs along the axis for a cylinder; the face's wires may trim it further, so take the vertices' span
        vs = [np.array([v.X, v.Y, v.Z]) for v in f.vertices()]
        if vs:
            h = [(p - o) @ a for p in vs]
            lo, hi = min(h), max(h)
            if hi - lo < 1e-9:
                lo, hi = sorted(((ad.Value(u0, v0).XYZ().Dot(cyl.Axis().Direction().XYZ()) - o @ a),
                                 (ad.Value(u0, v1).XYZ().Dot(cyl.Axis().Direction().XYZ()) - o @ a)))
        else:
            lo, hi = v0, v1
        r = float(cyl.Radius())
        length = max(hi - lo, 1e-9)
        ang = min(360.0, math.degrees(f.area / (r * length))) if r > 0 else 0.0
        out.append(Cyl(f, o, a, r, concave, ang, float(lo), float(hi), mid))
    return out


@dataclass
class Hole:
    origin: np.ndarray          # point on the axis at the middle of the hole
    axis: np.ndarray
    diameter: float
    depth: float
    lo: float
    hi: float
    through: bool = True
    open_dirs: tuple = ()       # which of +axis / -axis ends are open to the outside
    steps: list = field(default_factory=list)   # coaxial wider bores (counterbores): [(diameter, depth)]
    countersink: bool = False

    @property
    def center(self) -> np.ndarray:
        return self.origin


def _same_axis(o1, a1, o2, a2, tol=0.02) -> bool:
    if abs(abs(a1 @ a2) - 1) > 1e-4:
        return False
    d = o2 - o1
    return np.linalg.norm(d - (d @ a1) * a1) < tol


def holes(shape, sm: Sampled | None = None, cyls: list[Cyl] | None = None) -> list[Hole]:
    """Round holes: concave cylinders on one axis and radius that together go (nearly) all the way round.
    Coaxial wider bores next to a hole are recorded as its steps (counterbores); a concave cone on the
    axis is a countersink. Through or blind is read from the mesh: a ray along the axis from inside."""
    cyls = cylinders(shape) if cyls is None else cyls
    groups: list[list[Cyl]] = []
    for c in cyls:
        if not c.concave:
            continue
        for g in groups:
            if abs(g[0].radius - c.radius) < 1e-3 and _same_axis(g[0].origin, g[0].axis, c.origin, c.axis):
                g.append(c)
                break
        else:
            groups.append([c])
    raw = []
    for g in groups:
        a, o = g[0].axis, g[0].origin
        spans = []
        for c in g:
            s = 1.0 if c.axis @ a > 0 else -1.0
            off = (c.origin - o) @ a
            l, h = sorted((off + s * c.lo, off + s * c.hi))
            spans.append((l, h, c.angle))
        # angle swept at the most-covered station along the axis
        cuts = sorted({v for l, h, _ in spans for v in (l, h)})
        # stretches along the axis where the wall goes (nearly) all the way round: each is its own hole
        # (two ears of a yoke bored in line are two holes, not one long one)
        runs: list[list[float]] = []
        for i in range(len(cuts) - 1):
            if cuts[i + 1] - cuts[i] < 1e-9:
                continue
            m = 0.5 * (cuts[i] + cuts[i + 1])
            ang = sum(an for l, h, an in spans if l - 1e-9 <= m <= h + 1e-9)
            if ang >= 300.0:
                if runs and abs(runs[-1][1] - cuts[i]) < 1e-6:
                    runs[-1][1] = cuts[i + 1]
                else:
                    runs.append([cuts[i], cuts[i + 1]])
        for lo, hi in runs:
            raw.append(Hole(o + a * 0.5 * (lo + hi), a, 2 * g[0].radius, hi - lo, lo, hi))
    # nothing may stand inside: a concave cylinder around a boss is a groove, not a hole
    tris = sm.tris if sm is not None else np.asarray(to_trimesh(shape).triangles, dtype=float)
    out = []
    for h in raw:
        inside = _point_inside(tris, h.origin)
        if inside:
            continue
        opens = []
        for s in (1.0, -1.0):
            d, _ = ray_hits(tris, h.origin[None], (s * h.axis)[None])
            if not np.isfinite(d[0]):
                opens.append(s)
        h.open_dirs = tuple(opens)
        h.through = len(opens) == 2
        out.append(h)
    # counterbores: a wider coaxial hole that ends where a narrower one begins
    out.sort(key=lambda h_: h_.diameter)
    keep = []
    for h in out:
        parent = next((k for k in keep if _same_axis(k.origin, k.axis, h.origin, h.axis) and h.diameter > k.diameter + 1e-3), None)
        if parent is not None:
            parent.steps.append((round(h.diameter, 3), round(h.depth, 3)))
        else:
            keep.append(h)
    for f in shape.faces():
        if f.geom_type != GeomType.CONE:
            continue
        ad = BRepAdaptor_Surface(f.wrapped)
        ax = ad.Cone().Axis()
        o, a = _vec(ax.Location()), _vec(ax.Direction())
        for h in keep:
            if _same_axis(h.origin, h.axis, o, a):
                h.countersink = True
    return keep


def _point_inside(tris: np.ndarray, p: np.ndarray) -> bool:
    """Is p inside the solid: an odd number of crossings along a ray (two skew directions must agree,
    else a third decides)."""
    votes = []
    for d in ((0.3713, 0.5923, 0.7151), (-0.6312, 0.2417, 0.7371), (0.1931, -0.8823, 0.4293)):
        d = np.array(d) / np.linalg.norm(d)
        votes.append(_crossings(tris, p, d) % 2 == 1)
        if len(votes) == 2 and votes[0] == votes[1]:
            return votes[0]
    return sum(votes) >= 2


def _crossings(tris, p, d) -> int:
    v0 = tris[:, 0]
    e1 = tris[:, 1] - v0
    e2 = tris[:, 2] - v0
    pv = np.cross(d, e2)
    det = np.einsum("tk,tk->t", pv, e1)
    ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    tv = p - v0
    u = np.einsum("tk,tk->t", tv, pv) * inv
    q = np.cross(tv, e1)
    v = (q @ d) * inv
    t = np.einsum("tk,tk->t", q, e2) * inv
    return int(np.count_nonzero(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-9)))


def points_inside(tris: np.ndarray, pts: np.ndarray) -> np.ndarray:
    return np.array([_point_inside(tris, p) for p in pts], dtype=bool)


# --------------------------------------------------------------------------------- face classes
def face_classes(shape, frame: np.ndarray) -> dict:
    """What kinds of surface the part has, relative to its frame: flat faces square to an axis, flat faces
    at an angle, cylinders along an axis or not, cones, and anything freeform."""
    out = {"axis_planes": 0, "angled_planes": 0, "axis_cyls": 0, "angled_cyls": 0, "cones": 0, "tori": 0, "other": 0,
           "angled_at": [], "curved_at": []}
    for f in shape.faces():
        if f.geom_type == GeomType.PLANE:
            n = _vec(f.normal_at(f.center()))
            if np.max(np.abs(frame @ n)) > 0.9995:
                out["axis_planes"] += 1
            else:
                out["angled_planes"] += 1
                out["angled_at"].append(xyz(_vec(f.center())))
        elif f.geom_type == GeomType.CYLINDER:
            d = _vec(BRepAdaptor_Surface(f.wrapped).Cylinder().Axis().Direction())
            if np.max(np.abs(frame @ d)) > 0.9995:
                out["axis_cyls"] += 1
            else:
                out["angled_cyls"] += 1
                out["angled_at"].append(xyz(_vec(f.center())))
        elif f.geom_type == GeomType.CONE:
            out["cones"] += 1
        elif f.geom_type == GeomType.TORUS:
            out["tori"] += 1
            out["curved_at"].append(xyz(_vec(f.center())))
        else:
            out["other"] += 1
            out["curved_at"].append(xyz(_vec(f.center())))
    return out


def extents(sm: Sampled, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Lowest and highest coordinate of the part along each frame axis."""
    v = np.asarray(sm.mesh.vertices, dtype=float) @ frame.T
    return v.min(axis=0), v.max(axis=0)


def turned_axis(shape, cyls: list[Cyl] | None = None):
    """If every face is a surface of revolution about one common axis (or a flat face square to it), the
    part is a lathe part. Returns (origin, axis) or None. Cross holes and flats make it a milled part."""
    cyls = cylinders(shape) if cyls is None else cyls
    if not cyls:
        return None
    big = max(cyls, key=lambda c: (not c.concave, c.radius))
    if big.concave:
        return None
    o, a = big.origin, big.axis
    for f in shape.faces():
        if f.geom_type == GeomType.PLANE:
            n = _vec(f.normal_at(f.center()))
            if abs(abs(n @ a) - 1) > 1e-4:
                return None
        elif f.geom_type in (GeomType.CYLINDER, GeomType.CONE, GeomType.TORUS, GeomType.SPHERE):
            ad = BRepAdaptor_Surface(f.wrapped)
            if f.geom_type == GeomType.CYLINDER:
                ax = ad.Cylinder().Axis()
            elif f.geom_type == GeomType.CONE:
                ax = ad.Cone().Axis()
            elif f.geom_type == GeomType.TORUS:
                ax = ad.Torus().Axis()
            else:
                c = ad.Sphere().Location()
                p = np.array([c.X(), c.Y(), c.Z()]) - o
                if np.linalg.norm(p - (p @ a) * a) > 0.02:
                    return None
                continue
            if not _same_axis(o, a, _vec(ax.Location()), _vec(ax.Direction())):
                return None
        else:
            return None
    return o, a


# ------------------------------------------------------------------------------------- edges
def shared_edges(shape) -> tuple[list, list]:
    """(faces, [(edge, i, j)]): every edge that joins exactly two faces, with the indices of those faces."""
    faces = list(shape.faces())
    seen: dict[int, list] = {}
    for i, f in enumerate(faces):
        for e in f.edges():
            seen.setdefault(hash(e.wrapped), [e]).append(i)
    out = [(v[0], v[1], v[2]) for v in seen.values() if len(v) == 3 and v[1] != v[2]]
    return faces, out


def sharp_inside_edges(shape, sm: Sampled, frame: np.ndarray) -> list[dict]:
    """Straight inside corners between two flat faces that meet square with no radius.

    For each: where it is, its length, the direction it runs, the two face normals, and from which of
    those two normals' sides a square end mill could form it (end on one face, flank on the other) with a
    clear line of sight along the whole edge. An edge nothing reaches cannot be cut by a round tool."""
    faces, pairs = shared_edges(shape)
    out = []
    for e, i, j in pairs:
        fi, fj = faces[i], faces[j]
        if fi.geom_type != GeomType.PLANE or fj.geom_type != GeomType.PLANE or e.geom_type != GeomType.LINE:
            continue
        if e.length < 0.3:
            continue
        n1, n2 = _vec(fi.normal_at(fi.center())), _vec(fj.normal_at(fj.center()))
        if abs(n1 @ n2) > 0.05:
            continue                                   # not square: an angled face, reported elsewhere
        a, b = _vec(e.position_at(0.0)), _vec(e.position_at(1.0))
        m = 0.5 * (a + b)
        # just off the edge towards n1 - n2: inside the material at an inside corner, in the air at an outside one
        if not _point_inside(sm.tris, m + 0.01 * (n1 - n2)) or not _point_inside(sm.tris, m + 0.01 * (n2 - n1)):
            continue
        t = (b - a) / np.linalg.norm(b - a)
        reach = []
        for nd in (n1, n2):
            pts = np.array([a + f_ * (b - a) + 0.02 * (n1 + n2) for f_ in (0.1, 0.5, 0.9)])
            d, _ = ray_hits(sm.tris, pts, nd)
            if not np.isfinite(d).any():
                reach.append(nd)
        out.append({"at": xyz(m), "length": float(e.length), "along": t, "normals": (n1, n2), "reach": reach})
    return out


# ------------------------------------------------------------------------------- tapped holes
def tapped_holes(design, c, sm: Sampled) -> list[dict]:
    """Threads this part must carry. Tapped holes are not modelled as geometry in a design: a screw that
    `threads_into` the part simply overlaps it. So they are read from the screws: where each enters the
    part, how deep it engages, and how much material is left beyond its tip."""
    from .dfm_rules import TAP_DRILL

    fast = {f.name: f for f in design.fasteners}
    out = []
    for s in design.components:
        if c.name not in (s.meta.get("threads_into") or []) or s.meta.get("tnut"):
            continue
        f, d = fast.get(s.name), s.meta.get("thread_d")
        if f is None or not d:
            continue
        dvec = -np.array(f.axis, dtype=float)
        dvec /= np.linalg.norm(dvec)
        head = np.array(f.head_center, dtype=float)
        tip_s = float(((np.asarray(to_trimesh(s.shape).vertices) - head) @ dvec).max())
        ss = np.arange(0.0, tip_s + 1e-9, 0.25)
        pts = head + ss[:, None] * dvec
        inside = points_inside(sm.tris, pts)
        if not inside.any():
            continue
        entry = head + dvec * float(ss[inside][0])
        if not inside[0]:                                # the exact face the screw enters through
            d0, _ = ray_hits(sm.tris, head[None], dvec[None])
            if np.isfinite(d0[0]) and d0[0] <= float(ss[inside][0]) + 1e-6:
                entry = head + dvec * float(d0[0])
        tip = head + dvec * tip_s
        if inside[-1]:
            dist, _ = ray_hits(sm.tris, tip[None], dvec[None])
            beyond = float(dist[0]) if np.isfinite(dist[0]) else 0.0
        else:
            beyond = 0.0
        mid = head + dvec * float(ss[inside].mean())
        out.append({"screw": s.name, "d": float(d), "pitch": TAP_DRILL.get(float(d), (0.8 * d, 0.2 * d))[1],
                    "tap_drill": TAP_DRILL.get(float(d), (0.8 * d, 0))[0], "dir": dvec, "at": xyz(entry), "mid": mid,
                    "engagement": float(inside.sum() * 0.25), "beyond_tip": beyond})
    return out
