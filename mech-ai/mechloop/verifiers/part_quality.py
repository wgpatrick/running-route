"""Part quality: is each custom (fabricated) part a clean solid in which every feature has a purpose?

The other verifiers check that a part is valid, makeable, strong and fits. They do not ask whether the solid is CLEAN
(no slivers, steps of a tenth of a millimetre, faces a hair apart, blocks hanging on by a corner: what patching a part
in place over many versions leaves behind) or whether each FEATURE is used (a hole nothing passes through). This
verifier asks those questions, part by part, for every non-COTS part, plus three design-wide audits that the owner's
review asked for (see docs/CAD_QUALITY_PLAN.md):

  class      severity  code                       what it means                                    threshold
  broken     error     not_one_solid              the part is not exactly one solid                n_solids == 1
             error     invalid_brep               the kernel's check fails (BRepCheck_Analyzer)
             error     open_shell                 a shell is not closed / free edges               0 free edges
             error     non_manifold_edge          an edge shared by more than two faces            0
             error     internal_void              a solid with more than one shell (a cavity)      1 shell
             error     tiny_edge                  an edge shorter than TINY_EDGE                   0.05 mm
             error     sliver_face                a face of tiny area or width                     area < 0.01 mm2 or
                                                                                                   2A/P < 0.1 mm
             error     bad_volume                 volume <= 0 or larger than its bounding box
             error     mesh_not_watertight        its triangulation (the STL a shop gets) has holes
             error     self_intersection          the B-rep intersects itself (BRepAlgoAPI_Check)
  weird      warning   sparse_bbox                volume < SPARSE of its bounding box (a stray      1 %
                                                  feature far from the body?)
             warning   thin_wall                  local wall / web thinner than the process        printed 0.8, machined
                                                  minimum (rays cast inwards from the surface)     0.8, sheet min(1.0, t)
             warning   near_coincident_faces      two faces of the part face each other across     0 < gap < 0.2 mm
                                                  an air gap (a slit left by two booleans)
             warning   small_step                 two parallel planar faces offset by a ledge      0.001 < step < 0.5 mm
             warning   near_parallel_faces        two adjacent planar faces at a tiny angle        0.02 deg < a < 2 deg
             warning   weak_attachment            a feature joined to the body through a contact   width < 0.8 mm and
                                                  patch that is thin and a small share of it        < 15 % of its area
             warning   hole_unused                a hole (1.5 - 25 mm) with nothing in it: no
                                                  screw, pin, shaft, spacer or tool axis
             warning   outside_envelope           material outside the part's declared envelope    meta["envelope"]
                                                  or inside a declared keep-out                     meta["keep_out"]
  odd dims   info      odd_dimension              overall size (in the part's own axes) off the    0.1 mm grid
                                                  0.1 mm grid
             info      odd_hole_diameter          a hole diameter off the 0.1 mm grid
             info      nonstandard_hole           a hole diameter that is no standard clearance,
                                                  tap drill, insert, press, bearing or panel size

Design-wide audits (any part, COTS included):
             warning   allowed_overlap_large      a `design.allow_overlap` pair whose real overlap is large and not
                                                  explained by a thread (screw in its threaded hole / nut / T-nut);
                                                  the volume of every pair is in the metrics
             info      slot_nut_overlap           T-nuts / spring nuts overlapping their extrusion (one summary line)
             warning   screw_through_solid        a threaded pair where the screw fills the other part's material
                                                  (no hole drawn: fill > 0.6 of the screw's section)
             warning   attachment_not_drawn       two parts declared joined by hardware the join note names (a nut, a
                                                  clip, a ring nut ...) with no drawn fastener between them
             info      attachment_by_note         a join with no drawn fastener (press fit, bond, snap ...): fine when
                                                  that is how it is held; listed so it can be read
             warning   stock_hole_missing         a purchased part's interfaces list a hole (key with "hole", not "pin")
                                                  that neither its solid nor its detailed CAD has (info when only the
                                                  simulation solid dropped it)
             warning   stock_hole_misaligned      a purchased part screwed to a custom part where NONE of its listed holes
                                                  meets a hole in that part (info: single unused holes, or no drawn screw)

The checks of one part's own shape do not depend on where it is: they are memoised on the part's intrinsic fingerprint
(identical instances are checked once, also across runs in an incremental verify). Hole tracing, overlaps and joins
read the assembly.

NOT in the default verify (it would add new findings to every existing design): run it with
    mechloop verify designs/printer_v12.py --only part_quality
or `python -m mechloop.verifiers.part_quality designs/printer_v12.py --json out.json`.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict

import numpy as np

from ..report import VerifierResult, timed

VERSION = "1"

# ------------------------------------------------------------------------------------------------ thresholds (mm)
TINY_EDGE = 0.05
SLIVER_AREA = 0.01
SLIVER_WIDTH = 0.10           # 2 x area / perimeter: the width of a long thin face
SPARSE = 0.01
MIN_WALL = {"printed": 0.8, "machined": 0.8, "sheet": 1.0, None: 0.8}   # sheet: min(this, the sheet's thickness)
THIN_MIN_AREA = 0.5           # mm2 of surface that must be under the minimum before a thin wall is reported
GAP_MAX = 0.2
STEP_MAX = 0.5
STEP_MIN = 1e-3
PARALLEL_MAX_DEG = 2.0
PARALLEL_MIN_DEG = 0.02
WEAK_WIDTH = 0.8
WEAK_SHARE = 0.15
HOLE_D = (1.5, 25.0)
GRID = 0.1
# stock plate / sheet thicknesses that are not on the metric grid (inch gauges as SendCutSend / MISUMI / McMaster sell them)
STOCK_GAUGES = (0.508, 0.635, 0.8128, 1.016, 1.27, 1.524, 1.88, 2.032, 2.286, 2.54, 3.175, 4.75, 4.7625, 6.35, 9.525, 12.7, 15.875,
                19.05, 25.4)
OVERLAP_WARN_MM3 = 20.0       # an allowed overlap above this that no thread explains
SCREW_FILL = 0.6
MESH_TOL = 0.02
MESH_ANG = 0.25
MAX_RAYS = 4000

_THREADISH = ("thread", "insert", "pem", "self-clinching", "integral screw", "stud")   # a T-nut in its slot is NOT a thread
_HARDWARE_WORDS = ("nut", "screw", "bolt", "clip", "rivet", "pin", "circlip", "ring nut", "stud", "zip tie", "cable tie")
_FIXING_NOTE = ("integral", "press", "bond", "epoxy", "glue", "snap", "magnet", "sliding", "slide", "rests", "sits", "captive", "float",
                "spring", "solder", "on the rod", "axle", "held in", "clamp", "located", "pilot", "set_screw", "set screw")


def _std_holes() -> set:
    s = set()
    iso273 = {"M2": (2.2, 2.4, 2.6), "M2.5": (2.7, 2.9, 3.1), "M3": (3.2, 3.4, 3.6), "M4": (4.3, 4.5, 4.8),
              "M5": (5.3, 5.5, 5.8), "M6": (6.4, 6.6, 7.0), "M8": (8.4, 9.0, 10.0), "M10": (10.5, 11.0, 12.0),
              "M12": (13.0, 13.5, 14.5)}
    for v in iso273.values():
        s.update(v)
        s.update((round(v[1] + 0.2, 2), round(v[1] + 0.3, 2)))            # printed clearance (DG-05)
    s.update((1.6, 2.05, 2.1, 2.5, 2.9, 3.3, 4.2, 5.0, 6.8, 8.5, 10.2))       # tap drills, M2 .. M12
    s.update((2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0))     # nominal: pins, shafts, threads drawn at major
    s.update((3.2, 3.5, 3.6, 4.0, 4.2, 4.4, 4.6, 5.6, 5.7, 6.0, 6.4, 7.0))    # heat-set inserts M2 .. M5
    s.update((5.5, 6.5, 8.0, 9.5, 10.0, 11.0, 14.0))                          # counterbores M3 .. M8
    s.update((7.0, 9.0, 13.0, 14.0, 15.0, 19.0, 22.0, 24.0, 26.0))            # bearing / bushing ODs
    s.update((12.2, 12.5, 16.2, 16.5, 22.2, 22.3, 22.5, 8.2, 8.5, 10.5, 5.2, 3.1))  # panel cut-outs, pilots, shaft clearances
    return {round(x, 2) for x in s}


STD_HOLES = _std_holes()


# ======================================================================================== OCP helpers
def _faces(shape):
    return list(shape.faces())


def _surf(face):
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    return BRepAdaptor_Surface(face.wrapped)


def _face_point_normal(face):
    """A point on the face (not its centroid) and the outward normal there."""
    from OCP.BRepGProp import BRepGProp_Face
    from OCP.BRepTools import BRepTools
    from OCP.gp import gp_Pnt, gp_Vec

    u0, u1, v0, v1 = BRepTools.UVBounds_s(face.wrapped)
    u, v = (u0 + u1) / 2, (v0 + v1) / 2
    # the middle of the UV box can fall outside a trimmed face (an annulus): try a few
    from OCP.BRepClass import BRepClass_FaceClassifier
    from OCP.gp import gp_Pnt2d
    from OCP.TopAbs import TopAbs_IN, TopAbs_ON

    for fu, fv in ((0.5, 0.5), (0.25, 0.5), (0.75, 0.5), (0.5, 0.25), (0.5, 0.75), (0.1, 0.1), (0.9, 0.9), (0.1, 0.9), (0.9, 0.1)):
        uu, vv = u0 + fu * (u1 - u0), v0 + fv * (v1 - v0)
        st = BRepClass_FaceClassifier(face.wrapped, gp_Pnt2d(uu, vv), 1e-6).State()
        if st in (TopAbs_IN, TopAbs_ON):
            u, v = uu, vv
            break
    p, n = gp_Pnt(), gp_Vec()
    BRepGProp_Face(face.wrapped).Normal(u, v, p, n)
    nn = np.array([n.X(), n.Y(), n.Z()])
    L = np.linalg.norm(nn)
    return np.array([p.X(), p.Y(), p.Z()]), (nn / L if L > 0 else nn)


def _plane_faces(shape):
    from OCP.GeomAbs import GeomAbs_Plane

    out = []
    for f in _faces(shape):
        if _surf(f).GetType() == GeomAbs_Plane:
            p, n = _face_point_normal(f)
            out.append((f, p, n))
    return out


def _holes(shape):
    """Concave cylindrical faces grouped by (axis, radius): [{"d", "axis_p", "axis_d", "z0", "z1", "faces", "arc_deg"}]."""
    from OCP.GeomAbs import GeomAbs_Cylinder
    from OCP.BRepTools import BRepTools

    groups = []
    for f in _faces(shape):
        s = _surf(f)
        if s.GetType() != GeomAbs_Cylinder:
            continue
        cyl = s.Cylinder()
        r = cyl.Radius()
        ax = cyl.Axis()
        o = np.array([ax.Location().X(), ax.Location().Y(), ax.Location().Z()])
        dvec = np.array([ax.Direction().X(), ax.Direction().Y(), ax.Direction().Z()])
        p, n = _face_point_normal(f)
        radial = (p - o) - np.dot(p - o, dvec) * dvec
        if np.dot(n, radial) >= 0:          # normal points away from the axis: a boss / round, not a hole
            continue
        u0, u1, v0, v1 = BRepTools.UVBounds_s(f.wrapped)
        arc = math.degrees(abs(u1 - u0))
        vs = np.array([[v.X, v.Y, v.Z] for v in f.vertices()]) if f.vertices() else np.array([p])
        bb = f.bounding_box()
        corners = np.array([[x, y, z] for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y) for z in (bb.min.Z, bb.max.Z)])
        t = np.concatenate([(vs - o) @ dvec, (corners - o) @ dvec])
        z0, z1 = float(np.min((vs - o) @ dvec)) if len(vs) else 0.0, float(np.max((vs - o) @ dvec)) if len(vs) else 0.0
        if z1 - z0 < 1e-6:
            z0, z1 = float(t.min()), float(t.max())
        for g in groups:
            if abs(g["r"] - r) < 1e-4 and abs(abs(np.dot(g["axis_d"], dvec)) - 1) < 1e-6:
                w = o - g["axis_p"]
                if np.linalg.norm(w - np.dot(w, g["axis_d"]) * g["axis_d"]) < 1e-3:
                    sgn = 1.0 if np.dot(g["axis_d"], dvec) > 0 else -1.0
                    off = np.dot(o - g["axis_p"], g["axis_d"])
                    a, b = off + sgn * z0, off + sgn * z1
                    g["z0"], g["z1"] = min(g["z0"], a, b), max(g["z1"], a, b)
                    g["arc_deg"] += arc
                    g["faces"] += 1
                    break
        else:
            groups.append({"r": r, "d": 2 * r, "axis_p": o, "axis_d": dvec, "z0": z0, "z1": z1, "arc_deg": arc, "faces": 1})
    for g in groups:
        g["arc_deg"] = min(360.0, g["arc_deg"])
        g["center"] = g["axis_p"] + g["axis_d"] * (g["z0"] + g["z1"]) / 2
    return groups


def _mesh(shape, tol=MESH_TOL, ang=MESH_ANG):
    """(vertices, triangles, face index per triangle) of a copy of the shape; outward-wound."""
    from OCP.BRep import BRep_Tool
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopLoc import TopLoc_Location
    from OCP.TopoDS import TopoDS

    cp = BRepBuilderAPI_Copy(shape.wrapped).Shape()
    BRepMesh_IncrementalMesh(cp, tol, False, ang, True)
    V, T, F = [], [], []
    base = 0
    ex = TopExp_Explorer(cp, TopAbs_FACE)
    k = 0
    while ex.More():
        f = TopoDS.Face(ex.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(f, loc)
        if tri is not None:
            tr = loc.Transformation()
            for i in range(1, tri.NbNodes() + 1):
                p = tri.Node(i).Transformed(tr)
                V.append((p.X(), p.Y(), p.Z()))
            rev = f.Orientation() == TopAbs_REVERSED
            for i in range(1, tri.NbTriangles() + 1):
                a, b, c = tri.Triangle(i).Get()
                T.append((base + a - 1, base + c - 1, base + b - 1) if rev else (base + a - 1, base + b - 1, base + c - 1))
                F.append(k)
            base += tri.NbNodes()
        k += 1
        ex.Next()
    return np.array(V, float).reshape(-1, 3), np.array(T, int).reshape(-1, 3), np.array(F, int)


def _trimesh(shape):
    try:
        import trimesh
    except Exception:
        return None, None
    V, T, F = _mesh(shape)
    if not len(T):
        return None, None
    m = trimesh.Trimesh(V, T, process=False)
    m.merge_vertices(digits_vertex=5)
    keep = m.nondegenerate_faces(height=1e-9)
    m.update_faces(keep)
    return m, F[keep]


# ======================================================================================== intrinsic checks
def _process(c) -> str | None:
    p = c.process or c.meta.get("process")
    if p:
        return p
    return "printed" if c.material in ("pla", "petg", "abs", "nylon_pa12") else None


def _pt(a):
    return [round(float(x), 3) for x in a]


def intrinsic_checks(shape, process: str | None) -> list[dict]:
    """Findings that depend on the part's shape only, as dicts {severity, code, message, data}."""
    out: list[dict] = []

    def add(sev, code, msg, **data):
        out.append({"severity": sev, "code": code, "message": msg, "data": data})

    solids = shape.solids()
    if len(solids) != 1:
        add("error", "not_one_solid", f"{len(solids)} solids (a part must be exactly one solid)", solids=len(solids))
    if not solids:
        return out
    _brep_checks(shape, add)
    _edge_face_checks(shape, add)
    bb = shape.bounding_box()
    bbv = max(bb.size.X, 1e-9) * max(bb.size.Y, 1e-9) * max(bb.size.Z, 1e-9)
    vol = float(shape.volume)
    if vol <= 1e-6 or vol > bbv * 1.001:
        add("error", "bad_volume", f"volume {vol:.3g} mm3 against a {bbv:.3g} mm3 bounding box (inside-out or broken)",
            volume=vol, bbox_volume=bbv)
    elif vol < SPARSE * bbv:
        add("warning", "sparse_bbox", f"fills only {vol / bbv:.1%} of its bounding box: a stray feature far from the body?",
            fill=round(vol / bbv, 4))
    m, fidx = _trimesh(shape)
    t_sheet = None
    if m is not None:
        if not m.is_watertight:
            add("error", "mesh_not_watertight", "its triangulation (what an STL export gives a shop) is not closed",
                open_edges=int(len(m.edges) - 2 * len(m.edges_unique)) if False else None)
        else:
            t_sheet = _ray_checks(shape, m, fidx, process, add)
    _plane_pair_checks(shape, add)
    if m is not None and m.is_watertight:
        _weak_attachment(shape, m, add)
    _odd_dims(shape, add)
    return out


def _brep_checks(shape, add):
    from OCP.BRep import BRep_Tool
    from OCP.BRepCheck import BRepCheck_Analyzer, BRepCheck_NoError
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_SHELL, TopAbs_SOLID, TopAbs_VERTEX
    from OCP.TopExp import TopExp, TopExp_Explorer
    from OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopoDS import TopoDS

    w = shape.wrapped
    an = BRepCheck_Analyzer(w)
    if not an.IsValid():
        bad = Counter()
        for typ, nm in ((TopAbs_VERTEX, "vertex"), (TopAbs_EDGE, "edge"), (TopAbs_FACE, "face"), (TopAbs_SHELL, "shell"),
                        (TopAbs_SOLID, "solid")):
            ex = TopExp_Explorer(w, typ)
            while ex.More():
                res = an.Result(ex.Current())
                if res is not None:
                    try:
                        sts = list(res.Status())
                    except Exception:
                        sts = []
                    if any(s != BRepCheck_NoError for s in sts):
                        bad[nm] += 1
                ex.Next()
        add("error", "invalid_brep", "the kernel's B-rep check fails" + (f" ({dict(bad)} invalid sub-shapes)" if bad else ""),
            invalid=dict(bad))
    # shells: closed, one per solid
    ex = TopExp_Explorer(w, TopAbs_SOLID)
    while ex.More():
        so = ex.Current()
        n_sh = 0
        e2 = TopExp_Explorer(so, TopAbs_SHELL)
        while e2.More():
            n_sh += 1
            if not BRep_Tool.IsClosed_s(e2.Current()):
                add("error", "open_shell", "a shell of the solid is not closed")
            e2.Next()
        if n_sh > 1:
            add("error", "internal_void", f"a solid with {n_sh} shells: an enclosed cavity (internal void) or a "
                                          "disconnected skin", shells=n_sh)
        ex.Next()
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(w, TopAbs_EDGE, TopAbs_FACE, emap)
    free, nonman = [], []
    for i in range(1, emap.Extent() + 1):
        e = TopoDS.Edge(emap.FindKey(i))
        if BRep_Tool.Degenerated_s(e):
            continue
        faces = emap.FindFromIndex(i)
        # a seam edge appears twice in the same face's list
        uniq = {f.__hash__() if hasattr(f, "__hash__") else id(f) for f in faces}
        nf = faces.Size()
        if nf == 1 and not BRep_Tool.IsClosed_s(e, TopoDS.Face(faces.First())):
            free.append(e)
        elif nf > 2 and len(uniq) > 2:
            nonman.append(e)
    if free:
        add("error", "open_shell", f"{len(free)} free edges (a face edge no other face shares): the skin has a gap",
            at=_pt(_edge_mid(free[0])), count=len(free))
    if nonman:
        add("error", "non_manifold_edge", f"{len(nonman)} edges shared by more than two faces (non-manifold: two "
                                          "bodies touching along a line)", at=_pt(_edge_mid(nonman[0])), count=len(nonman))
    # self-intersection (BOPAlgo argument analyser): cheap on these parts
    try:
        from OCP.BRepAlgoAPI import BRepAlgoAPI_Check

        chk = BRepAlgoAPI_Check(w, True, True)
        if not chk.IsValid():
            add("error", "self_intersection", "the boolean checker finds the B-rep intersecting itself or a small edge / "
                                              "face it cannot use")
    except Exception:
        pass


def _edge_mid(e):
    from OCP.BRepAdaptor import BRepAdaptor_Curve

    c = BRepAdaptor_Curve(e if not hasattr(e, "wrapped") else e.wrapped)
    p = c.Value((c.FirstParameter() + c.LastParameter()) / 2)
    return (p.X(), p.Y(), p.Z())


def _edge_face_checks(shape, add):
    from OCP.BRep import BRep_Tool

    tiny = [e for e in shape.edges() if not BRep_Tool.Degenerated_s(e.wrapped) and e.length < TINY_EDGE]
    if tiny:
        add("error", "tiny_edge", f"{len(tiny)} edges shorter than {TINY_EDGE} mm (shortest {min(e.length for e in tiny):.4f} mm): "
                                  "two booleans that nearly line up", at=_pt(_edge_mid(tiny[0])), count=len(tiny),
            shortest=round(min(e.length for e in tiny), 5))
    slivers = []
    for f in shape.faces():
        a = f.area
        per = sum(e.length for e in f.edges())
        width = 2 * a / per if per > 0 else 0.0
        if a < SLIVER_AREA or width < SLIVER_WIDTH:
            slivers.append((width, a, f))
    if slivers:
        slivers.sort(key=lambda t: t[0])
        w0, a0, f0 = slivers[0]
        add("error", "sliver_face", f"{len(slivers)} sliver faces (narrowest {w0:.3f} mm wide, {a0:.3g} mm2)",
            at=_pt(f0.center()), count=len(slivers), narrowest=round(w0, 4))


def _ray_checks(shape, m, fidx, process, add):
    """Wall thickness (rays inwards) and air slits (rays outwards) from triangle centres."""
    try:
        from trimesh.ray.ray_triangle import RayMeshIntersector
    except Exception:
        return None
    tri_area = m.area_faces
    n = m.face_normals
    c = m.triangles_center
    idx = np.arange(len(tri_area))
    if len(idx) > MAX_RAYS:     # area-weighted sample, keeping every small triangle near features likely
        rng = np.random.default_rng(0)
        idx = np.sort(rng.choice(idx, MAX_RAYS, replace=False, p=tri_area / tri_area.sum()))
    rays = RayMeshIntersector(m)
    eps = 1e-4

    def first_hits(origins, dirs):
        loc, ri, ti = rays.intersects_location(origins, dirs, multiple_hits=True)
        best = np.full(len(origins), np.inf)
        bt = np.full(len(origins), -1)
        if len(ri):
            d = np.einsum("ij,ij->i", loc - origins[ri], dirs[ri])
            ok = d > 2 * eps
            for r_, t_, d_ in zip(ri[ok], ti[ok], d[ok]):
                if d_ < best[r_]:
                    best[r_], bt[r_] = d_, t_
        return best, bt

    o = c[idx]
    nn = n[idx]
    thick, tt = first_hits(o - nn * eps, -nn)
    gap, tg = first_hits(o + nn * eps, nn)
    # sheet: its thickness is the commonest wall across the biggest faces
    t_sheet = None
    finite = np.isfinite(thick)
    if finite.any():
        vals = np.round(thick[finite], 2)
        w = tri_area[idx][finite]
        cnt = defaultdict(float)
        for v, a in zip(vals, w):
            cnt[v] += a
        t_sheet = max(cnt, key=cnt.get)
    lim = MIN_WALL.get(process, MIN_WALL[None])
    if process == "sheet" and t_sheet:
        lim = min(lim, 0.95 * t_sheet)
    opp = np.full(len(idx), False)
    ok = tt >= 0
    opp[ok] = np.einsum("ij,ij->i", n[tt[ok]], nn[ok]) < -0.5
    # the triangulation cuts each curved wall by up to MESH_TOL: a wall exactly at the minimum must not trip it
    thin = finite & opp & (thick < lim - 2 * MESH_TOL - 0.01)
    a_thin = float(tri_area[idx][thin].sum())
    if thin.any() and a_thin >= THIN_MIN_AREA:
        k = int(np.argmin(np.where(thin, thick, np.inf)))
        add("warning", "thin_wall", f"wall / web {thick[k]:.2f} mm thick, under the {lim:.2f} mm minimum for "
                                    f"{process or 'this process'} ({a_thin:.1f} mm2 of surface)",
            at=_pt(o[k]), min_mm=round(float(thick[k]), 3), limit_mm=round(lim, 3), area_mm2=round(a_thin, 2))
    oppg = np.full(len(idx), False)
    okg = tg >= 0
    oppg[okg] = np.einsum("ij,ij->i", n[tg[okg]], nn[okg]) < -0.5
    slit = np.isfinite(gap) & oppg & (gap < GAP_MAX)
    if slit.any():
        k = int(np.argmin(np.where(slit, gap, np.inf)))
        add("warning", "near_coincident_faces", f"two faces of the part face each other {gap[k]:.3f} mm apart (an air "
                                                f"slit under {GAP_MAX} mm: two features that nearly meet)",
            at=_pt(o[k]), gap_mm=round(float(gap[k]), 4), area_mm2=round(float(tri_area[idx][slit].sum()), 2))
    return t_sheet


def _plane_pair_checks(shape, add):
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
    from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE
    from OCP.TopExp import TopExp
    from OCP.collections import IndexedDataMap_TopoDS_Shape_List_TopoDS_Shape_TopTools_ShapeMapHasher as TopTools_IndexedDataMapOfShapeListOfShape
    from OCP.TopoDS import TopoDS

    pf = _plane_faces(shape)
    if len(pf) < 2:
        return
    N = np.array([n for _, _, n in pf])
    P = np.array([p for _, p, _ in pf])
    bbs = []
    for f, _, _ in pf:
        b = f.bounding_box()
        bbs.append((b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z))
    bbs = np.array(bbs)
    steps = []
    for i in range(len(pf)):
        dots = N[i + 1:] @ N[i]
        for jj in np.nonzero(dots > math.cos(math.radians(0.5)))[0]:
            j = i + 1 + jj
            off = abs(float(np.dot(P[j] - P[i], N[i])))
            if not (STEP_MIN < off < STEP_MAX):
                continue
            g = STEP_MAX + 0.1
            if np.any(bbs[i, :3] - g > bbs[j, 3:]) or np.any(bbs[j, :3] - g > bbs[i, 3:]):
                continue
            dist = BRepExtrema_DistShapeShape(pf[i][0].wrapped, pf[j][0].wrapped)
            if dist.IsDone() and dist.Value() <= off + 0.05:
                steps.append((off, i, j))
    if steps:
        steps.sort()
        off, i, j = steps[0]
        add("warning", "small_step", f"{len(steps)} ledges under {STEP_MAX} mm between parallel faces (smallest "
                                     f"{off:.3f} mm): two features that should share one face", at=_pt(P[i]),
            count=len(steps), smallest_mm=round(off, 4), other_at=_pt(P[j]))
    # adjacent planar faces at a tiny angle
    emap = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(shape.wrapped, TopAbs_EDGE, TopAbs_FACE, emap)
    key = {}
    for k, (f, _, _) in enumerate(pf):
        key[f.wrapped.__hash__()] = k
    seen, tilted = set(), []
    for e in range(1, emap.Extent() + 1):
        lst = emap.FindFromIndex(e)
        ks = []
        it = lst.cbegin() if hasattr(lst, "cbegin") else None
        for fs in lst:
            k = key.get(TopoDS.Face(fs).__hash__())
            if k is not None:
                ks.append(k)
        for a in range(len(ks)):
            for b in range(a + 1, len(ks)):
                pr = (min(ks[a], ks[b]), max(ks[a], ks[b]))
                if pr in seen or pr[0] == pr[1]:
                    continue
                seen.add(pr)
                ang = math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(N[pr[0]], N[pr[1]]))))))
                if PARALLEL_MIN_DEG < ang < PARALLEL_MAX_DEG:
                    tilted.append((ang, pr))
    if tilted:
        tilted.sort()
        ang, (i, j) = tilted[0]
        add("warning", "near_parallel_faces", f"{len(tilted)} pairs of adjacent planar faces meet at under "
                                              f"{PARALLEL_MAX_DEG} deg ({ang:.2f} deg): a face that should be one plane",
            at=_pt(P[i]), count=len(tilted), angle_deg=round(ang, 3))


def _weak_attachment(shape, m, add):
    """At each plane where the part has planar faces of both senses (a feature standing on another), the feature's
    contact with what is on the other side must not be a thin sliver that is a small share of it."""
    try:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
    except Exception:
        return
    pf = _plane_faces(shape)
    planes = []
    for i, (_, p, n) in enumerate(pf):
        for _, p2, n2 in pf[i + 1:]:
            if np.dot(n, n2) < -0.99999 and abs(np.dot(p2 - p, n)) < 1e-3:
                c = float(np.dot(p, n))
                if not any(abs(np.dot(n, q) - 1) < 1e-6 and abs(c0 - c) < 1e-3 for q, c0 in planes):
                    planes.append((n, c))
    worst = None
    for n, c in planes[:40]:
        polys = {}
        for s in (1, -1):
            sec = m.section(plane_origin=n * (c + s * 0.02), plane_normal=n)
            if sec is None:
                polys[s] = []
                continue
            try:
                p2, T = sec.to_2D() if hasattr(sec, "to_2D") else sec.to_planar()
                polys[s] = [pg for pg in p2.polygons_full if pg.area > 1e-6]
                polys[f"T{s}"] = T
            except Exception:
                polys[s] = []
        if not polys[1] or not polys[-1]:
            continue
        # both sections are in their own 2-D frames; bring the -1 side into the +1 frame
        try:
            import trimesh

            Tp, Tm = polys["T1"], polys["T-1"]
            M = np.linalg.inv(Tp) @ Tm

            def tf(pg):
                xy = np.array(pg.exterior.coords)
                h = np.c_[xy, np.zeros(len(xy)), np.ones(len(xy))] @ M.T
                holes = [np.c_[np.array(r.coords), np.zeros(len(r.coords)), np.ones(len(r.coords))] @ M.T for r in pg.interiors]
                return Polygon(h[:, :2], [hh[:, :2] for hh in holes])

            below = unary_union([tf(pg).buffer(0) for pg in polys[-1]])
            above = unary_union([pg.buffer(0) for pg in polys[1]])
        except Exception:
            continue
        for side, comps, other in ((1, polys[1], below), (-1, [tf(pg) for pg in polys[-1]], above)):
            for pg in comps:
                pg = pg.buffer(0)
                if pg.area < 1.0:
                    continue
                contact = pg.intersection(other)
                ca = contact.area
                if ca < 1e-6 or ca > WEAK_SHARE * pg.area:
                    continue
                if not contact.buffer(-WEAK_WIDTH / 2).is_empty:
                    continue
                share = ca / pg.area
                if worst is None or share < worst[0]:
                    cxy = contact.centroid
                    worst = (share, ca, pg.area, c, n, (cxy.x, cxy.y), polys["T1"])
    if worst:
        share, ca, pa, c, n, cxy, T = worst
        at = (T @ np.array([cxy[0], cxy[1], 0.0, 1.0]))[:3] - n * 0.02
        add("warning", "weak_attachment", f"a feature ({pa:.0f} mm2 in section) joins the rest through a thin contact patch "
                                          f"of {ca:.2f} mm2 ({share:.1%} of it, under {WEAK_WIDTH} mm wide)",
            at=_pt(at), contact_mm2=round(ca, 3), share=round(share, 4))


def _principal_axes(shape):
    pf = _plane_faces(shape)
    if not pf:
        return np.eye(3)
    pf.sort(key=lambda t: -t[0].area)
    n1 = pf[0][2]
    n2 = None
    for f, _, n in pf[1:]:
        if abs(np.dot(n, n1)) < 1e-6:
            n2 = n
            break
    if n2 is None:
        a = np.eye(3)[int(np.argmin(np.abs(n1)))]
        n2 = a - np.dot(a, n1) * n1
        n2 /= np.linalg.norm(n2)
    return np.array([n1, n2, np.cross(n1, n2)])


def _extents(shape, R):
    """Size of the shape along the three rows of R (exact: an optimal bounding box of the rotated shape)."""
    from OCP.Bnd import Bnd_Box
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepBndLib import BRepBndLib
    from OCP.gp import gp_Trsf

    t = gp_Trsf()
    t.SetValues(*R[0], 0.0, *R[1], 0.0, *R[2], 0.0)
    moved = shape.wrapped.Moved(TopLoc_Location(t)) if np.allclose(R @ R.T, np.eye(3)) and np.linalg.det(R) > 0 else shape.wrapped
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(moved, b, False, False)
    lo, hi = b.CornerMin(), b.CornerMax()
    return [hi.X() - lo.X(), hi.Y() - lo.Y(), hi.Z() - lo.Z()]


def _off_grid(x: float) -> bool:
    return abs(x / GRID - round(x / GRID)) > 0.02


def _odd_dims(shape, add):
    try:
        R = _principal_axes(shape)
        dims = sorted((round(v, 3) for v in _extents(shape, R)), reverse=True)
    except Exception:
        return
    odd = [v for v in dims if _off_grid(v) and not any(abs(v - g) < 2e-3 for g in STOCK_GAUGES)]
    if odd:
        add("info", "odd_dimension", f"overall size {' x '.join(f'{v:g}' for v in dims)} mm: "
                                     f"{', '.join(f'{v:g}' for v in odd)} not on the {GRID} mm grid", dims=dims, odd=odd)
    holes = [h for h in _holes(shape) if HOLE_D[0] <= h["d"] <= HOLE_D[1] and h["arc_deg"] > 179]
    offg = sorted({round(h["d"], 3) for h in holes if _off_grid(h["d"])})
    if offg:
        add("info", "odd_hole_diameter", f"hole diameters off the {GRID} mm grid: {', '.join(f'{d:g}' for d in offg)} mm",
            diameters=offg)
    nonstd = sorted({round(h["d"], 2) for h in holes if not _off_grid(h["d"]) and round(h["d"], 2) not in STD_HOLES
                     and round(round(h["d"], 2) - 0.0, 1) not in STD_HOLES})
    if nonstd:
        add("info", "nonstandard_hole", f"hole diameters that are no standard clearance / tap / insert / press / bearing "
                                        f"size: {', '.join(f'{d:g}' for d in nonstd)} mm", diameters=nonstd)


# ======================================================================================== assembly checks
class _Scene:
    """Bounding boxes of every part and a point classifier per part (built lazily)."""

    def __init__(self, design):
        self.design = design
        self.comps = list(design.components)
        bb = []
        for c in self.comps:
            b = c.shape.bounding_box()
            bb.append((b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z))
        self.bb = np.array(bb)
        self._cls = {}

    def near(self, pts, pad=0.0, exclude=None):
        pts = np.atleast_2d(pts)
        lo, hi = pts.min(0) - pad, pts.max(0) + pad
        ok = np.all(self.bb[:, :3] <= hi, axis=1) & np.all(self.bb[:, 3:] >= lo, axis=1)
        return [self.comps[i] for i in np.nonzero(ok)[0] if self.comps[i].name != exclude]

    def inside_any(self, c, pts) -> bool:
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN, TopAbs_ON

        sols = self._cls.get(c.name)
        if sols is None:
            sols = [s.wrapped for s in c.shape.solids()]
            self._cls[c.name] = sols
        for p in pts:
            for s in sols:
                st = BRepClass3d_SolidClassifier(s, gp_Pnt(*map(float, p)), 1e-4).State()
                if st in (TopAbs_IN, TopAbs_ON):
                    return True
        return False


def _hole_probe_points(h):
    if "slot_to" in h:     # a slot: probe its whole length
        pts = [_hole_probe_points({**{k: v for k, v in h.items() if k != "slot_to"},
                                   "axis_p": h["axis_p"] + (h["slot_to"] - h["center"]) * f}) for f in (0.0, 0.5, 1.0)]
        return np.vstack(pts)
    d = h["axis_d"]
    a = np.cross(d, [1, 0, 0] if abs(d[0]) < 0.9 else [0, 1, 0])
    a /= np.linalg.norm(a)
    b = np.cross(d, a)
    pts = []
    for f in (0.2, 0.5, 0.8):
        z = h["z0"] + f * (h["z1"] - h["z0"])
        c0 = h["axis_p"] + d * z
        pts.append(c0)
        for ang in range(0, 360, 60):
            t = math.radians(ang)
            pts.append(c0 + 0.55 * h["r"] * (math.cos(t) * a + math.sin(t) * b))
    return np.array(pts)


def _hole_features(shape):
    """Holes (concave cylinders of at least half a turn) of hole-like size, with the two half-round ends of a slot
    merged into one feature (probed along its length). A concave quarter-round is an inside corner, not a hole."""
    hs = [h for h in _holes(shape) if HOLE_D[0] <= h["d"] <= HOLE_D[1] and h["arc_deg"] >= 170]
    full = [h for h in hs if h["arc_deg"] > 300]
    half = [h for h in hs if h["arc_deg"] <= 300]
    used = set()
    for i, a in enumerate(half):
        if i in used:
            continue
        best = None
        for j in range(i + 1, len(half)):
            b = half[j]
            if j in used or abs(a["r"] - b["r"]) > 1e-4 or abs(abs(np.dot(a["axis_d"], b["axis_d"])) - 1) > 1e-6:
                continue
            w = b["center"] - a["center"]
            if abs(np.dot(w, a["axis_d"])) > 1e-3:
                continue
            L = float(np.linalg.norm(w))
            if L < 60 and (best is None or L < best[0]):
                best = (L, j)
        if best is not None:
            used.update((i, best[1]))
            b = half[best[1]]
            full.append({**a, "slot_to": b["center"], "arc_deg": 360.0, "slot_len": best[0]})
        else:
            used.add(i)
            full.append(a)
    return full


def trace_holes(design, c, scene) -> list[dict]:
    """Holes of part c that nothing in the assembly passes through or mates with."""
    out = []
    holes = _hole_features(c.shape)
    tool_axes = [(np.array(f.head_center, float), np.array(f.axis, float) / (np.linalg.norm(f.axis) or 1.0))
                 for f in design.fasteners]
    for h in holes:
        pts = _hole_probe_points(h)
        used_by = None
        for o in scene.near(pts, pad=0.01, exclude=c.name):
            if scene.inside_any(o, pts):
                used_by = o.name
                break
        if used_by is None:     # a tool access hole: a screw axis runs through it
            for hc, ax in tool_axes:
                if abs(abs(np.dot(ax, h["axis_d"])) - 1) < 0.004:
                    w = h["center"] - hc
                    if np.linalg.norm(w - np.dot(w, ax) * ax) < h["r"]:
                        used_by = "tool axis"
                        break
        if used_by is None:
            kind = f"{h['d']:.2f} x {h['slot_len'] + h['d']:.2f} mm slot" if "slot_to" in h else f"{h['d']:.2f} mm hole"
            out.append({"severity": "warning", "code": "hole_unused",
                        "message": f"{kind} with nothing in it (no screw, pin, shaft, spacer, part or tool "
                                   f"axis passes through): a left-over or a missing part?",
                        "data": {"at": _pt(h["center"]), "d_mm": round(h["d"], 3), "axis": _pt(h["axis_d"]),
                                 "arc_deg": round(h["arc_deg"], 1)}})
    return out


def envelope_checks(c) -> list[dict]:
    out = []
    env = c.meta.get("envelope")
    bb = c.shape.bounding_box()
    if env:
        lo, hi = np.array(env[0], float), np.array(env[1], float)
        blo = np.array([bb.min.X, bb.min.Y, bb.min.Z])
        bhi = np.array([bb.max.X, bb.max.Y, bb.max.Z])
        over = np.maximum(lo - blo, 0) + np.maximum(bhi - hi, 0)
        if np.any(over > 1e-3):
            out.append({"severity": "warning", "code": "outside_envelope",
                        "message": f"material outside its declared envelope by up to {over.max():.2f} mm",
                        "data": {"by_mm": _pt(over)}})
    for k, box in enumerate(c.meta.get("keep_out") or []):
        from build123d import Box, Pos

        lo, hi = np.array(box[0], float), np.array(box[1], float)
        ko = Pos(*((lo + hi) / 2)) * Box(*(hi - lo))
        v = (c.shape & ko).volume
        if v > 1e-3:
            out.append({"severity": "warning", "code": "outside_envelope",
                        "message": f"{v:.1f} mm3 of material inside keep-out {k}", "data": {"keep_out": k, "volume_mm3": v}})
    return out


# ---------------------------------------------------------------------------------------- design-wide audits
def _is_hardware(c) -> bool:
    s = (c.sku or "").upper()
    return c.cots and (s.startswith(("SHCS", "BHCS", "FHCS", "SCREW", "NUT", "WASHER", "TNUT", "PEM", "INSERT", "BOLT"))
                       or bool(c.meta.get("threads_into")) or "washer" in c.name or c.name.endswith(("_nut", "_tnut")))


def _is_nut(c) -> bool:
    """A nut, T-nut or insert: whatever a thread runs into (an allowed overlap with it is the thread)."""
    return c.cots and (bool(re.search(r"(nut|insert)$", c.name.rstrip("_0123456789")))
                       or (c.sku or "").upper().startswith(("NUT", "TNUT", "INSERT", "PEM")))


def _is_screwlike(c, fast) -> bool:
    """A screw, stud, threaded rod or axle: what a nut runs on."""
    s = f"{c.name} {c.sku or ''}".lower()
    return c.name in fast or bool(c.meta.get("threads_into")) or any(w in s for w in ("screw", "shcs", "bhcs", "fhcs", "stud", "rod",
                                                                                     "axle", "thread", "bolt"))


def _screw_d(c) -> float | None:
    m = re.search(r"M(\d+(?:\.\d+)?)", c.sku or "")
    return float(m.group(1)) if m else None


def overlap_audit(design, r) -> dict:
    from .. import incremental as _inc

    comps = {c.name: c for c in design.components}
    fast = {f.name: f for f in design.fasteners}
    rows, flagged = [], []
    for pair, maxv in design.allowed_overlaps.items():
        names = sorted(pair)
        if len(names) != 2 or any(n not in comps for n in names):
            continue
        a, b = comps[names[0]], comps[names[1]]
        ba, bb_ = a.shape.bounding_box(), b.shape.bounding_box()
        if (ba.min.X > bb_.max.X or bb_.min.X > ba.max.X or ba.min.Y > bb_.max.Y or bb_.min.Y > ba.max.Y
                or ba.min.Z > bb_.max.Z or bb_.min.Z > ba.max.Z):
            vol, ext = 0.0, None
        else:
            def comp(a=a, b=b):
                cm = a.shape & b.shape
                v = float(cm.volume) if cm is not None else 0.0
                e = None
                if v > 1e-6:
                    bx = cm.bounding_box()
                    e = [bx.min.X, bx.min.Y, bx.min.Z, bx.max.X, bx.max.Y, bx.max.Z]
                return v, e

            vol, ext = _inc.memo("overlap", lambda: ["ov", _inc.shape_key(a.shape), _inc.shape_key(b.shape)], comp,
                                 code=("verifiers/part_quality.py",))
        kind = str(design.joins.get(pair, ""))
        threadish = any(w in kind.lower() for w in _THREADISH)
        screw = next((x for x in (a, b) if x.name in fast), None)
        nutlike = next((x for x in (a, b) if _is_nut(x)), None)
        on_thread = nutlike is not None and _is_screwlike(b if nutlike is a else a, fast)
        other = b if screw is a else a
        fill = None
        if screw is not None and vol > 1e-3 and ext is not None:
            d = _screw_d(screw)
            ax = np.abs(np.array(fast[screw.name].axis, float))
            ax /= np.linalg.norm(ax) or 1.0
            L = float(np.dot(np.array(ext[3:]) - np.array(ext[:3]), ax))
            if d and L > 0.1:
                fill = vol / (math.pi * d * d / 4 * L)
        row = {"a": names[0], "b": names[1], "volume_mm3": round(vol, 3), "declared_max_mm3": None if maxv >= 1e8 else maxv,
               "join": kind, "threaded": threadish or screw is not None or on_thread, "screw_fill": None if fill is None else round(fill, 3),
               "custom": [n for n in names if not comps[n].cots]}
        rows.append(row)
        if fill is not None and fill > SCREW_FILL and not other.cots:
            r.add("warning", "screw_through_solid",
                  f"{screw.name} fills {fill:.0%} of its section inside {other.name} ({vol:.0f} mm3): no hole is drawn "
                  f"where it passes (a threaded hole overlaps ~30 %)", part=other.name, screw=screw.name, volume_mm3=round(vol, 1),
                  fill=round(fill, 3), check_class="weird")
        elif vol > OVERLAP_WARN_MM3 and not row["threaded"]:
            flagged.append((row, ext))
    # the same overlap repeated on many identical pairs (every drop-in T-nut in its slot) is one finding
    groups = defaultdict(list)
    for row, ext in flagged:
        sig = (row["join"], round(row["volume_mm3"]), tuple(sorted(str(comps[n].sku or re.sub(r"\d+", "#", n))
                                                                    for n in (row["a"], row["b"]))))
        groups[sig].append((row, ext))
    slot_nuts = {k: m for k, m in groups.items() if re.search(r"t-?nut|spring nut", k[0].lower())}
    if slot_nuts:     # how the catalogue T-nuts are drawn (COTS against COTS): one summary line, not a warning each
        n = sum(len(m) for m in slot_nuts.values())
        vols = sorted({k[1] for k in slot_nuts})
        r.add("info", "slot_nut_overlap", f"{n} T-nut / spring-nut pairs overlap their extrusion by {', '.join(map(str, vols))} mm3 "
              f"each (allowed): the nut solid cuts into the slot's lips or the section has no slot there; a modelling "
              f"compromise of purchased parts, hidden from the interference check", count=n, volumes_mm3=vols, check_class="purchased")
    for (kind, v, pat), members in groups.items():
        if (kind, v, pat) in slot_nuts:
            continue
        row, ext = members[0]
        names = [row["a"], row["b"]]
        part = next((n for n in names if not comps[n].cots), names[0])
        at = _pt([(ext[0] + ext[3]) / 2, (ext[1] + ext[4]) / 2, (ext[2] + ext[5]) / 2]) if ext else None
        if len(members) >= 3:
            r.add("warning", "allowed_overlap_large",
                  f"{len(members)} pairs like {names[0]} / {names[1]} are allowed to overlap and each does by {v} mm3 (join: "
                  f"{kind or 'none'}): not a thread; the solids clash and allow_overlap hides it from the interference check",
                  part=part, pair=names, count=len(members), volume_mm3=row["volume_mm3"], join=kind, at=at, check_class="weird")
        else:
            for row, ext in members:
                names = [row["a"], row["b"]]
                r.add("warning", "allowed_overlap_large",
                      f"{names[0]} and {names[1]} are allowed to overlap and do by {row['volume_mm3']:.0f} mm3 (join: "
                      f"{row['join'] or 'none'}): only a thread, a press fit or a panel cut-out should overlap; this hides a "
                      f"clash from the interference check", part=next((n for n in names if not comps[n].cots), names[0]),
                      pair=names, volume_mm3=row["volume_mm3"], join=row["join"], check_class="weird",
                      at=_pt([(ext[0] + ext[3]) / 2, (ext[1] + ext[4]) / 2, (ext[2] + ext[5]) / 2]) if ext else None)
    rows.sort(key=lambda x: -x["volume_mm3"])
    return {"pairs": len(rows), "nonzero": sum(x["volume_mm3"] > 1e-3 for x in rows),
            "flagged": sum(1 for x in rows if x["volume_mm3"] > OVERLAP_WARN_MM3 and not x["threaded"]),
            "screws_filling_cots_part": sum(1 for x in rows if (x["screw_fill"] or 0) > SCREW_FILL and not x["custom"]),
            "rows": rows}


def _hardware_nearby(design, comps, a, b) -> bool:
    """A drawn nut / screw / washer tied (joined or allowed to overlap) to one of the two parts and touching the other."""
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape

    rel = defaultdict(set)
    for pr in list(design.joins) + list(design.allowed_overlaps):
        n = sorted(pr)
        if len(n) == 2:
            rel[n[0]].add(n[1])
            rel[n[1]].add(n[0])
    for x, y in ((a, b), (b, a)):
        for h in rel[x.name]:
            hc = comps.get(h)
            if hc is None or not _is_hardware(hc) or h == y.name:
                continue
            if y.name in rel[h]:
                return True
            dd = BRepExtrema_DistShapeShape(hc.shape.wrapped, y.shape.wrapped)
            if dd.IsDone() and dd.Value() < 0.2:
                return True
    return False


def join_audit(design, r) -> dict:
    """Joins between two parts that no drawn fastener holds together."""
    comps = {c.name: c for c in design.components}
    groups = []
    for f in design.fasteners:
        if f.name not in comps:
            continue
        g = {f.name, *f.clamps, *(comps[f.name].meta.get("threads_into") or [])}
        for pr, kind in design.joins.items():
            if f.name in pr:
                g |= set(pr)
        groups.append(g)
    # nuts / T-nuts tie their own groups to what they sit in
    fastened = set()
    for g in groups:
        for x in g:
            for y in g:
                if x < y:
                    fastened.add((x, y))
    rows = []
    for pr, kind in design.joins.items():
        names = sorted(pr)
        if len(names) != 2 or any(n not in comps for n in names):
            continue
        a, b = comps[names[0]], comps[names[1]]
        if _is_hardware(a) or _is_hardware(b) or tuple(names) in fastened:
            continue
        kl = str(kind).lower()
        words = [w for w in _HARDWARE_WORDS if re.search(rf"\b{re.escape(w)}s?\b", kl)
                 and w.replace(" ", "_") not in f"{a.name} {b.name}".lower()]      # "held in the clip's channel" of led_clip_0
        fixing = any(w in kl for w in _FIXING_NOTE)
        rows.append({"a": names[0], "b": names[1], "join": str(kind), "hardware_named": words, "fixing_note": fixing,
                     "custom": [n for n in names if not comps[n].cots]})
        part = next((n for n in names if not comps[n].cots), None)
        if words and "integral" not in kl and not _hardware_nearby(design, comps, a, b):
            r.add("warning", "attachment_not_drawn",
                  f"{names[0]} and {names[1]} are declared joined ('{kind}') but the {', '.join(words)} that would hold them "
                  f"is not drawn and no drawn fastener connects them: nothing shows how it attaches",
                  part=part or names[0], pair=names, join=str(kind), check_class="weird")
        else:
            r.add("info", "attachment_by_note", f"{names[0]} and {names[1]}: held only by a join note ('{kind}'), no drawn fastener",
                  part=part or names[0], pair=names, join=str(kind), check_class="weird")
    return {"unfastened_joins": len(rows), "rows": rows}


def _hole_near_point(shape, p, tol_axis=0.5, reach=3.0, faces_cache=None):
    """(found, best axis offset, d) for a concave cylinder whose axis passes within tol_axis of p near p."""
    hs = faces_cache if faces_cache is not None else _holes(shape)
    best = (math.inf, None)
    for h in hs:
        if h["d"] > 30:
            continue
        w = p - h["axis_p"]
        t = float(np.dot(w, h["axis_d"]))
        off = float(np.linalg.norm(w - t * h["axis_d"]))
        if t < h["z0"] - reach or t > h["z1"] + reach:
            continue
        if off < best[0]:
            best = (off, h["d"])
    return best[0] <= tol_axis, best[0], best[1]


def _fastened_together(design, a: str, b: str) -> bool:
    for f in design.fasteners:
        g = {f.name, *f.clamps}
        try:
            g |= set(design.get(f.name).meta.get("threads_into") or [])
        except KeyError:
            pass
        if a in g and b in g:
            return True
    return False


def stock_hole_audit(design, r, scene) -> dict:
    """Holes a purchased part's interfaces list must exist in its solid, and line up with a hole in the custom part
    they bolt to."""
    rows = []
    hole_cache = {}
    custom = [c for c in design.components if not c.cots]

    def holes_of(c, which="shape"):
        k = (c.name, which)
        if k not in hole_cache:
            s = c.shape if which == "shape" else c.detail
            try:
                hole_cache[k] = _holes(s) if s is not None else []
            except Exception:
                hole_cache[k] = []
        return hole_cache[k]

    for c in design.components:
        if not c.cots:
            continue
        for key, v in (c.meta.get("interfaces") or {}).items():
            # "pin_holes" (a switch's terminals) are where pins come OUT of the part, not holes in it
            if "hole" not in key or "pin" in key or not isinstance(v, list):
                continue
            pts = [np.array(p, float) for p in v if isinstance(p, (tuple, list)) and len(p) == 3]
            if not pts:
                continue
            missing, missing_detail, mis = [], [], []
            matched: dict = {}
            for p in pts:
                ok, off, _ = _hole_near_point(c.shape, p, faces_cache=holes_of(c))
                if not ok:
                    missing.append(p)
                    if c.detail is not None:
                        okd, _, _ = _hole_near_point(c.detail, p, faces_cache=holes_of(c, "detail"))
                        if not okd:
                            missing_detail.append(p)
                # mating custom part(s): within 1 mm of the point
                for m in scene.near(p, pad=1.0, exclude=c.name):
                    if m.cots:
                        continue
                    from OCP.BRepExtrema import BRepExtrema_DistShapeShape
                    from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
                    from OCP.gp import gp_Pnt

                    okm, offm, dm = _hole_near_point(m.shape, p, tol_axis=0.3, reach=6.0, faces_cache=holes_of(m))
                    if okm:     # (the listed point sits on the hole's axis, in its mouth: no material within a radius)
                        matched[m.name] = matched.get(m.name, 0) + 1
                        continue
                    vx = BRepBuilderAPI_MakeVertex(gp_Pnt(*map(float, p))).Vertex()
                    dd = BRepExtrema_DistShapeShape(vx, m.shape.wrapped)
                    if dd.IsDone() and dd.Value() <= 1.0:
                        mis.append({"fastened": _fastened_together(design, c.name, m.name), "mate": m.name, "at": _pt(p),
                                    "nearest_hole_axis_mm": None if offm == math.inf else round(offm, 3), "nearest_d": dm})
            row = {"part": c.name, "sku": c.sku, "key": key, "listed": len(pts), "missing_in_solid": len(missing),
                   "missing_in_detail": len(missing_detail) if c.detail is not None else None, "misaligned": mis}
            rows.append(row)
            if missing:
                sev = "info" if (c.detail is not None and not missing_detail) else "warning"
                det = ("" if c.detail is None else
                       (" nor in its detailed CAD" if missing_detail else " (its detailed CAD has them: the simulation solid "
                                                                           "dropped them)"))
                r.add(sev, "stock_hole_missing",
                      f"{c.name} ({c.sku}): interfaces['{key}'] lists {len(pts)} holes, {len(missing)} not in its solid{det}",
                      part=c.name, key=key, missing=len(missing), at=_pt(missing[0]), check_class="purchased")
            for mm in mis:
                # a warning only when the two are screwed together and NONE of the listed holes meets a hole in the mate (a
                # camera on two of its four holes leaves the other two blind, which is fine)
                broken = mm["fastened"] and not matched.get(mm["mate"])
                why = ("" if broken else "; no drawn screw fastens the two, so the listed holes are unused" if not mm["fastened"]
                       else f"; {matched.get(mm['mate'])} other listed hole(s) do line up: this one is just not used")
                r.add("warning" if broken else "info", "stock_hole_misaligned",
                      f"{c.name}'s listed hole ('{key}') at {mm['at']} has no matching hole in {mm['mate']}"
                      + (f" (nearest hole axis {mm['nearest_hole_axis_mm']} mm away)" if mm["nearest_hole_axis_mm"] is not None else "")
                      + why,
                      part=mm["mate"], stock=c.name, key=key, at=mm["at"], check_class="purchased")
    return {"interfaces_checked": len(rows), "rows": rows}


# ======================================================================================== the verifier
CLASS = {"not_one_solid": "broken", "invalid_brep": "broken", "open_shell": "broken", "non_manifold_edge": "broken",
         "internal_void": "broken", "tiny_edge": "broken", "sliver_face": "broken", "bad_volume": "broken",
         "mesh_not_watertight": "broken", "self_intersection": "broken", "sparse_bbox": "weird", "thin_wall": "weird",
         "near_coincident_faces": "weird", "small_step": "weird", "near_parallel_faces": "weird", "weak_attachment": "weird",
         "hole_unused": "weird", "outside_envelope": "weird", "odd_dimension": "odd", "odd_hole_diameter": "odd",
         "nonstandard_hole": "odd"}


def verify_part_quality(design, parts: list[str] | None = None, audits: bool = True) -> VerifierResult:
    from .. import incremental as _inc

    r = VerifierResult("part_quality")
    with timed(r):
        custom = [c for c in design.components if not c.cots and (parts is None or c.name in parts)]
        scene = _Scene(design)
        per_part = {}
        for c in custom:
            proc = _process(c)
            try:
                found = _inc.memo("intrinsic", lambda c=c, proc=proc: ["pq", VERSION, _inc.intrinsic_key(c.shape), proc],
                                  lambda c=c, proc=proc: intrinsic_checks(c.shape, proc), code=("verifiers/part_quality.py",))
            except Exception as e:
                found = [{"severity": "error", "code": "check_crashed", "message": f"intrinsic checks crashed: {type(e).__name__}: {e}",
                          "data": {}}]
            if found and found[0]["code"] == "not_one_solid" and not c.shape.solids():
                ctx = []
            else:
                try:
                    ctx = trace_holes(design, c, scene) + envelope_checks(c)
                except Exception as e:
                    ctx = [{"severity": "info", "code": "check_crashed", "message": f"hole tracing crashed: {type(e).__name__}: {e}",
                            "data": {}}]
            # placement: intrinsic locations are in the part's own world position already (shapes are placed)
            for f in found + ctx:
                r.add(f["severity"], f["code"], f"{c.name}: {f['message']}", part=c.name,
                      check_class=CLASS.get(f["code"], "other"), **f["data"])
            per_part[c.name] = {"process": proc, "material": c.material,
                                "errors": sum(f["severity"] == "error" for f in found + ctx),
                                "warnings": sum(f["severity"] == "warning" for f in found + ctx),
                                "info": sum(f["severity"] == "info" for f in found + ctx)}
        r.metrics = {"custom_parts": len(custom), "parts": per_part,
                     "by_code": dict(Counter(f.code for f in r.findings)),
                     "thresholds": {"tiny_edge_mm": TINY_EDGE, "sliver_area_mm2": SLIVER_AREA, "sliver_width_mm": SLIVER_WIDTH,
                                    "min_wall_mm": {str(k): v for k, v in MIN_WALL.items()}, "gap_mm": GAP_MAX,
                                    "step_mm": STEP_MAX, "near_parallel_deg": [PARALLEL_MIN_DEG, PARALLEL_MAX_DEG],
                                    "weak_width_mm": WEAK_WIDTH, "weak_share": WEAK_SHARE, "hole_d_mm": HOLE_D, "grid_mm": GRID,
                                    "overlap_warn_mm3": OVERLAP_WARN_MM3, "screw_fill": SCREW_FILL}}
        if audits and parts is None:
            for nm, fn in (("overlaps", lambda: overlap_audit(design, r)), ("joins", lambda: join_audit(design, r)),
                           ("stock_holes", lambda: stock_hole_audit(design, r, scene))):
                try:
                    r.metrics[nm] = fn()
                except Exception as e:
                    r.add("info", "check_crashed", f"{nm} audit crashed: {type(e).__name__}: {e}")
        r.metrics["by_code"] = dict(Counter(f.code for f in r.findings))
    return r


def main(argv=None) -> None:
    import argparse
    import json

    ap = argparse.ArgumentParser(description="part-quality checks on a design's custom parts")
    ap.add_argument("design")
    ap.add_argument("--json", help="write findings + metrics here")
    ap.add_argument("--parts", nargs="*")
    a = ap.parse_args(argv)
    import mechloop  # noqa: F401
    from ..runner import load_design

    d = load_design(a.design)
    res = verify_part_quality(d, a.parts)
    print(f"part_quality: {res.metrics['custom_parts']} custom parts, {len(res.findings)} findings in {res.seconds:.0f} s")
    for f in res.findings:
        if f.severity != "info":
            print(f"  {f.severity:7s} {f.code:24s} {f.message}")
    if a.json:
        from dataclasses import asdict

        with open(a.json, "w") as fh:
            json.dump({"design": d.name, "findings": [asdict(f) for f in res.findings], "metrics": res.metrics,
                       "seconds": round(res.seconds, 1)}, fh, indent=1, default=str)


if __name__ == "__main__":
    main()
