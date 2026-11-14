"""Vendor and community CAD (STEP files) behind the catalog parts.

A catalog `Stock` has two representations:

  shape   the simulation solid: simple, clean, fast (exact booleans, meshing, sweeps, tolerance cylinders).
  detail  the detailed model (a vendor STEP where one could be had), in exactly the same local frame.
          Used for display and export, and as the reference the simulation solid is checked against.

`stock.model` says what the detail is:

  kind    "vendor CAD"            the maker's own STEP file
          "community CAD"         a STEP someone else drew of the part (never presented as the vendor's)
          "generated to standard" built by code from a dimension standard or the vendor's drawing
          "proxy"                 no detailed model: the simulation solid is all there is
  source  where it came from (file in vendor_cad/, see vendor_cad/SOURCES.md)

Files live in `vendor_cad/` at the repository root. A STEP file dropped into `vendor_cad/inbox/` (or
`vendor_cad/`) whose name matches a part's SKU or one of its `inbox` names replaces that part's detail model
with no code change: it is aligned to the part's local frame automatically (or by a `<file>.json` sidecar with
"rot"/"pos") and then has to pass the same proxy-match check as every other model. See vendor_cad/inbox/README.md.

STEP import is slow, so imported and derived shapes are cached as BREP in `vendor_cad/.cache/`, keyed by the
hash of the source files.

Checks (run from the geometry verifier, see `verify_detail`):

  proxy_matches_cad   for every part with a detail model: bounding box, volume, and the positions and diameters
                      of the mounting holes and shafts named in `interfaces`, measured in the detail model
  detail_clash        every bit of a detail model that sticks out of its simulation solid (connector, lever,
                      terminal cover, cable exit) is tested against the neighbouring parts' simulation solids
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("MECHLOOP_VENDOR_CAD", Path(__file__).resolve().parents[2] / "vendor_cad"))
VERSION = "1"          # bump to invalidate every cached derived shape
KINDS = ("vendor CAD", "community CAD", "generated to standard", "proxy")

_MEM: dict = {}        # key -> Shape (per process)
STOCKS: dict = {}      # model key -> the last Stock built with it (what the checks compare)


def root() -> Path:
    return Path(os.environ.get("MECHLOOP_VENDOR_CAD", ROOT))


def cache_dir() -> Path:
    d = root() / ".cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


# ------------------------------------------------------------------ files
def find_file(*names: str, inbox_only: bool = False) -> Path | None:
    """First STEP file in vendor_cad/inbox/ then vendor_cad/ whose stem equals one of `names` (case and the
    extension .step/.stp ignored)."""
    want = [n.lower().rsplit(".", 1)[0] if n.lower().endswith((".step", ".stp")) else n.lower() for n in names if n]
    dirs = [root() / "inbox"] + ([] if inbox_only else [root()])
    for d in dirs:
        if not d.is_dir():
            continue
        files = {p.stem.lower(): p for p in sorted(d.iterdir()) if p.suffix.lower() in (".step", ".stp")}
        for w in want:
            if w in files:
                return files[w]
    return None


def file_hash(path: Path) -> str:
    st = path.stat()
    key = ("hash", str(path), st.st_size, st.st_mtime_ns)
    if key not in _MEM:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
        _MEM[key] = h.hexdigest()[:20]
    return _MEM[key]


def _read_brep(path: Path):
    from build123d import import_brep

    return import_brep(str(path))


def _write_brep(shape, path: Path) -> None:
    from OCP.BRepTools import BRepTools

    tmp = path.with_suffix(f".tmp{os.getpid()}")
    BRepTools.Write_s(shape.wrapped, str(tmp))
    os.replace(tmp, path)


def load_step(path: Path):
    """A STEP file as a build123d shape, in the file's own frame. Cached as BREP by file hash."""
    path = Path(path)
    h = file_hash(path)
    if ("step", h) in _MEM:
        return _MEM[("step", h)]
    cp = cache_dir() / f"step_{h}.brep"
    if cp.exists():
        s = _read_brep(cp)
    else:
        import io
        from contextlib import redirect_stderr, redirect_stdout

        from build123d import import_step

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            s = import_step(str(path))
        _write_brep(s, cp)
    _MEM[("step", h)] = s
    return s


def cached(key: str, files: list[Path], build):
    """A derived shape (cut to length, re-framed, assembled), cached in memory and as BREP on disk. The disk key is
    `key`, the hashes of the source `files` and VERSION."""
    hk = hashlib.sha256("|".join([VERSION, key] + [file_hash(Path(f)) for f in files]).encode()).hexdigest()[:20]
    if ("derived", hk) in _MEM:
        return _MEM[("derived", hk)]
    cp = cache_dir() / f"d_{hk}.brep"
    if cp.exists():
        s = _read_brep(cp)
    else:
        s = build()
        _write_brep(s, cp)
    _MEM[("derived", hk)] = s
    return s


# ------------------------------------------------------------------ placing a model in a part's frame
def solids_of(shape, keep=None):
    """The solids of an imported file as one compound; `keep(solid, bbox)` filters them (labels, loose screws)."""
    from build123d import Compound

    sol = [s for s in shape.solids() if keep is None or keep(s, s.bounding_box())]
    return sol[0] if len(sol) == 1 else Compound(children=sol)


def frame(shape, rot=(0.0, 0.0, 0.0), pos=(0.0, 0.0, 0.0), pre=(0.0, 0.0, 0.0)):
    """Move a file's geometry into a catalog part's local frame: translate by `pre`, rotate by `rot` (degrees, about
    X then Y then Z of the fixed axes), translate by `pos`. The transform is baked into the geometry."""
    from build123d import Location, Pos, Rot

    loc = Pos(*pos) * Rot(0, 0, rot[2]) * Rot(0, rot[1], 0) * Rot(rot[0], 0, 0) * Pos(*pre)
    return bake(shape.moved(loc))


def bake(shape):
    """Apply a shape's location to its geometry (so its location is the identity)."""
    from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
    from OCP.TopLoc import TopLoc_Location

    trsf = shape.wrapped.Location().Transformation()
    bare = shape.wrapped.Located(TopLoc_Location())
    out = BRepBuilderAPI_Transform(bare, trsf, True).Shape()
    return _cast(out)


def _cast(wrapped):
    from build123d import Shape

    return Shape.cast(wrapped)


def bbox6(shape) -> np.ndarray:
    b = shape.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z])


def _centroid(shape) -> np.ndarray:
    sol = shape.solids()
    if not sol:
        b = bbox6(shape)
        return (b[:3] + b[3:]) / 2
    v = np.array([s.volume for s in sol])
    c = np.array([tuple(s.center()) for s in sol])
    return (c * v[:, None]).sum(0) / max(v.sum(), 1e-9)


_ROT24 = None


def _rotations():
    global _ROT24
    if _ROT24 is None:
        out = []
        for perm in itertools.permutations(range(3)):
            for signs in itertools.product((1, -1), repeat=3):
                M = np.zeros((3, 3))
                for i, (p, s) in enumerate(zip(perm, signs)):
                    M[i, p] = s
                if np.linalg.det(M) > 0:
                    out.append(M)
        _ROT24 = out
    return _ROT24


def auto_align(shape, reference):
    """Put an unknown file's geometry into the frame of `reference` (the part's existing detail model or simulation
    solid): the axis-aligned orientation whose bounding box and centre of volume agree best, bounding boxes centred
    on one another. Good for a hand-downloaded file of the same part; the proxy-match check then confirms it (or
    says what is off, and a `<file>.json` sidecar {"rot": [rx, ry, rz], "pos": [x, y, z]} overrides this)."""
    from OCP.gp import gp_Trsf

    from ..geom import location_from_matrix

    rb = bbox6(reference)
    rsize, rctr = rb[3:] - rb[:3], (rb[:3] + rb[3:]) / 2
    roff = _centroid(reference) - rctr
    shape = bake(shape)
    sb = bbox6(shape)
    sctr = (sb[:3] + sb[3:]) / 2
    soff = _centroid(shape) - sctr
    ssize = sb[3:] - sb[:3]
    best = None
    for M in _rotations():
        size = np.abs(M) @ ssize
        score = np.abs(size - rsize).sum() + 0.5 * np.abs(M @ soff - roff).sum()
        if best is None or score < best[0] - 1e-9:
            best = (score, M)
    M = best[1]
    T = np.eye(4)
    T[:3, :3] = M
    T[:3, 3] = rctr - M @ sctr
    return bake(shape.moved(location_from_matrix(T)))


def stretch(shape, axis: str, at: float, delta: float):
    """Lengthen (delta > 0) or shorten (delta < 0) a model along a principal axis by cutting it at `at`, moving the
    +axis side by `delta`, and filling the gap with the section at the cut (or removing the slab). Used to bring a
    model of one length of a part family (a 40 mm motor) to another catalogue length; only valid where the section
    is constant around `at`."""
    from build123d import Box, Pos, extrude

    i = "XYZ".index(axis.upper())
    b = bbox6(shape)
    big = 4 * float(max(b[3:] - b[:3])) + 100.0

    def half(lo, hi):
        ctr = [(b[k] + b[k + 3]) / 2 for k in range(3)]
        size = [big, big, big]
        ctr[i], size[i] = (lo + hi) / 2, hi - lo
        return Pos(*ctr) * Box(*size)

    def shift(d):
        v = [0.0, 0.0, 0.0]
        v[i] = d
        return Pos(*v)

    if abs(delta) < 1e-9:
        return shape
    lo_part = shape & half(b[i] - 10, at)
    if delta > 0:
        hi_part = shape & half(at, b[i + 3] + 10)
        thin = shape & half(at - 0.01, at + 0.01)
        # the section at the cut, swept over the gap
        faces = [f for f in thin.faces() if abs(abs(tuple(f.normal_at())[i]) - 1) < 1e-6
                 and abs(tuple(f.center())[i] - (at + 0.01)) < 1e-6]
        v = [0.0, 0.0, 0.0]
        v[i] = 1.0
        fill = None
        for f in faces:
            e = extrude(shift(-0.01) * f, delta, dir=tuple(v))
            fill = e if fill is None else fill + e
        out = lo_part + shift(delta) * hi_part
        return bake(out + fill) if fill is not None else bake(out)
    hi_part = shape & half(at - delta, b[i + 3] + 10)
    return bake(lo_part + shift(delta) * hi_part)


# ------------------------------------------------------------------ inbox override
def inbox_override(names: list[str], reference):
    """A hand-downloaded STEP for this part, if one is in vendor_cad/inbox/ (or vendor_cad/) under one of `names`.
    Returns (shape in the part's frame, model record) or None."""
    p = find_file(*names, inbox_only=True)
    if p is None:
        return None
    side = {}
    sp = p.with_suffix(p.suffix + ".json")
    if not sp.exists():
        sp = p.with_suffix(".json")
    if sp.exists():
        side = json.loads(sp.read_text())

    def build():
        raw = solids_of(load_step(p))
        if "rot" in side or "pos" in side:
            return frame(raw, tuple(side.get("rot", (0, 0, 0))), tuple(side.get("pos", (0, 0, 0))))
        return auto_align(raw, reference)

    rb = bbox6(reference).round(3).tolist()
    shape = cached(f"inbox:{p.name}:{json.dumps(side, sort_keys=True)}:{rb}", [p], build)
    rel = f"vendor_cad/{p.relative_to(root())}"
    return shape, {"kind": side.get("kind", "vendor CAD"), "file": rel,
                   "source": side.get("source", f"hand download: {rel}"),
                   "note": "hand-downloaded file" + ("" if ("rot" in side or "pos" in side) else ", aligned automatically")}


# ------------------------------------------------------------------ measuring a model
def cylinders(shape) -> list[dict]:
    """Every cylindrical face: a point on its axis, the axis direction, diameter, and its extent along the axis."""
    from OCP.BRepAdaptor import BRepAdaptor_Surface
    from OCP.GeomAbs import GeomAbs_Cylinder

    key = ("cyl", id(shape.wrapped))
    if key in _MEM:
        return _MEM[key][1]
    out = []
    for f in shape.faces():
        a = BRepAdaptor_Surface(f.wrapped)
        if a.GetType() != GeomAbs_Cylinder:
            continue
        c = a.Cylinder()
        p, d = c.Location(), c.Axis().Direction()
        p, d = np.array([p.X(), p.Y(), p.Z()]), np.array([d.X(), d.Y(), d.Z()])
        bb = f.bounding_box()
        lo, hi = np.array(tuple(bb.min)), np.array(tuple(bb.max))
        ts = [float((np.array(q) - p) @ d) for q in itertools.product(*zip(lo, hi))]
        out.append({"p": p, "d": d, "dia": 2 * c.Radius(), "t0": min(ts), "t1": max(ts),
                    "span": abs(a.LastUParameter() - a.FirstUParameter())})
    _MEM[key] = (shape.wrapped, out)
    return out


def find_cylinder(shape, at, dia: float, axis=None, dia_range=(0.6, 1.45), reach: float = 3.0, min_span: float = 0.0):
    """The cylindrical face nearest to `at` (distance from the point to the face's axis line, the point lying within
    `reach` of the face's extent along it) whose diameter is within `dia_range` x `dia`, optionally parallel to
    `axis`. Returns (distance, diameter, foot point on the axis) or None."""
    at = np.array(at, dtype=float)
    best = None
    for c in cylinders(shape):
        if not (dia_range[0] * dia <= c["dia"] <= dia_range[1] * dia) or c["span"] < min_span:
            continue
        if axis is not None and abs(float(np.array(axis) @ c["d"])) < 0.999 * float(np.linalg.norm(axis)):
            continue
        t = float((at - c["p"]) @ c["d"])
        if t < c["t0"] - reach or t > c["t1"] + reach:
            continue
        foot = c["p"] + t * c["d"]
        dist = float(np.linalg.norm(at - foot))
        # prefer the closest axis, then the diameter nearest the nominal
        score = (round(dist, 2), abs(c["dia"] - dia))
        if best is None or score < best[0]:
            best = (score, dist, c["dia"], foot)
    return None if best is None else best[1:]


def hole_feature(name: str, at, dia: float, axis=None, tol_pos: float = 0.3, dia_range=None, tol_dia=None) -> dict:
    """One feature the proxy-match check must find in the detail model: a hole or shaft whose axis passes through
    `at` (within tol_pos) with diameter `dia` (within tol_dia, or within dia_range x dia for a hole that may be
    tapped or clearance)."""
    return {"name": name, "at": tuple(float(x) for x in at), "dia": float(dia), "axis": axis, "tol_pos": tol_pos,
            "dia_range": dia_range, "tol_dia": tol_dia}


def _auto_features(interfaces: dict) -> list[dict]:
    out = []
    for k, v in interfaces.items():
        if k.startswith("mount_holes_m") and isinstance(v, list):
            try:
                d = float(k[len("mount_holes_m"):])
            except ValueError:
                continue
            for i, p in enumerate(v):
                # tapped (minor diameter about 0.8 d) up to a generous clearance hole (1.35 d)
                out.append(hole_feature(f"{k}[{i}]", p, d, dia_range=(0.75, 1.4)))
    return out


def check_stock(stock) -> tuple[list[dict], dict]:
    """Compare a part's simulation solid with its detail model. Returns (mismatches, measurements). Each mismatch
    is {"what", "proxy", "cad", "limit", "message"}."""
    from ..model import MATERIALS

    model = getattr(stock, "model", None) or {}
    if getattr(stock, "detail", None) is None:
        return [], {}
    bad: list[dict] = []
    pb, db = bbox6(stock.shape), bbox6(stock.detail)
    tol = dict(model.get("tolerance") or {})
    stick = dict(model.get("protrusions") or {})     # e.g. {"ymax": (4.1, "lever at its free position")}
    size = db[3:] - db[:3]
    meas = {"bbox_proxy": pb.round(2).tolist(), "bbox_cad": db.round(2).tolist()}
    for i, side in enumerate(("xmin", "ymin", "zmin", "xmax", "ymax", "zmax")):
        lim = tol.get("bbox", max(0.5, 0.015 * float(size[i % 3])))
        extra = stick.get(side, (0.0, ""))[0] * (-1 if i < 3 else 1)
        if abs(db[i] - pb[i] - extra) > lim + 1e-9:
            bad.append({"what": f"bounding box {side}", "proxy": round(float(pb[i]), 2), "cad": round(float(db[i]), 2),
                        "limit": round(lim, 2),
                        "message": f"{side}: simulation solid {pb[i]:.2f}, detail model {db[i]:.2f}"
                                   + (f" (expected to stick out {abs(extra):.2f}: {stick[side][1]})" if side in stick else "")})
    vp, vd = float(stock.shape.volume), float(sum(s.volume for s in stock.detail.solids()))
    lo, hi = tol.get("volume_ratio", (0.6, 1.7))
    meas["volume_proxy_mm3"], meas["volume_cad_mm3"] = round(vp, 1), round(vd, 1)
    if vd > 0 and not (lo <= vp / vd <= hi):
        bad.append({"what": "volume", "proxy": round(vp, 1), "cad": round(vd, 1), "limit": [lo, hi],
                    "message": f"volume: simulation solid {vp:.0f} mm^3 is {vp / vd:.2f} x the detail model's {vd:.0f} mm^3 "
                               f"(allowed {lo} to {hi})"})
    mat = MATERIALS.get(stock.material)
    if mat is not None and stock.mass_kg and not model.get("assembly"):
        meas["mass_catalog_kg"] = round(stock.mass_kg, 4)
        meas["mass_of_cad_as_solid_kg"] = round(vd * 1e-9 * mat.density, 4)   # as if solid `material`: an upper bound
        mlo, mhi = tol.get("mass_ratio", (0.2, 3.0))
        ratio = stock.mass_kg / max(vd * 1e-9 * mat.density, 1e-12)
        if not (mlo <= ratio <= mhi):
            bad.append({"what": "mass", "proxy": round(stock.mass_kg, 4), "cad": meas["mass_of_cad_as_solid_kg"],
                        "limit": [mlo, mhi],
                        "message": f"mass: catalogue {stock.mass_kg:.3f} kg is {ratio:.2f} x the detail model's volume as "
                                   f"solid {stock.material} ({meas['mass_of_cad_as_solid_kg']:.3f} kg)"})
    feats = list(model.get("features") or []) + ([] if model.get("no_auto_features") else _auto_features(stock.interfaces))
    found = {}
    for ft in feats:
        dr = ft.get("dia_range") or ((1 - 1e-9, 1 + 1e-9) if ft.get("tol_dia") is None else None)
        if dr is None or ft.get("tol_dia") is not None:
            td = ft["tol_dia"] if ft.get("tol_dia") is not None else 0.1
            dr = ((ft["dia"] - td) / ft["dia"], (ft["dia"] + td) / ft["dia"])
        hit = find_cylinder(stock.detail, ft["at"], ft["dia"], ft.get("axis"), dr)
        if hit is None or hit[0] > ft["tol_pos"]:
            near = find_cylinder(stock.detail, ft["at"], ft["dia"], None, (0.3, 3.0), reach=1e9)
            got = "no cylindrical face of that size" if hit is None else f"nearest axis is {hit[0]:.2f} mm away (diameter {hit[1]:.2f})"
            if near is not None and (hit is None or hit[0] > ft["tol_pos"]):
                got += f"; nearest cylinder of any size: diameter {near[1]:.2f} at {np.round(near[2], 2).tolist()}, {near[0]:.2f} mm off"
            bad.append({"what": ft["name"], "proxy": {"at": ft["at"], "dia": ft["dia"]},
                        "cad": None if hit is None else {"offset": round(hit[0], 3), "dia": round(hit[1], 3)},
                        "limit": {"position": ft["tol_pos"], "dia": [round(dr[0] * ft["dia"], 2), round(dr[1] * ft["dia"], 2)]},
                        "message": f"{ft['name']}: expected diameter {ft['dia']:g} at {tuple(round(x, 2) for x in ft['at'])}; "
                                   f"in the detail model {got}"})
        else:
            found[ft["name"]] = {"offset_mm": round(hit[0], 3), "dia_mm": round(hit[1], 3)}
    meas["features"] = found
    return bad, meas


# ------------------------------------------------------------------ what sticks out of the simulation solid
def excess_hulls(stock, key: str, outside: float = 0.4, min_size: float = 0.8) -> list[np.ndarray]:
    """The parts of the detail model that lie outside the simulation solid by more than `outside` mm, as convex
    hulls (vertex arrays, local frame), one per connected patch of the detail model's surface."""
    mk = ("hulls", key)
    if mk in _MEM:
        return _MEM[mk]
    import trimesh

    from ..geom import to_trimesh

    hk = hashlib.sha256(f"{VERSION}|{key}|{bbox6(stock.shape).round(3).tolist()}|{round(float(stock.shape.volume), 2)}|"
                        f"{bbox6(stock.detail).round(3).tolist()}|{outside}".encode()).hexdigest()[:20]
    cp = cache_dir() / f"hull_{hk}.npz"
    if cp.exists():
        z = np.load(cp)
        hulls = [z[k] for k in sorted(z.files)]
    else:
        dm = to_trimesh(stock.detail, 0.1, 0.4)
        pm = to_trimesh(stock.shape, 0.05, 0.3)
        hulls = []
        pb = bbox6(stock.shape)
        V = np.asarray(dm.vertices)
        # cheap first: vertices inside the solid's bounding box need the exact test, those well outside do not
        out_bb = ((V < pb[:3] - outside) | (V > pb[3:] + outside)).any(1)
        far = out_bb.copy()
        idx = np.where(~out_bb)[0]
        if len(idx):
            from OCP.BRepExtrema import BRepExtrema_DistShapeShape
            from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeVertex
            from OCP.BRepClass3d import BRepClass3d_SolidClassifier
            from OCP.gp import gp_Pnt
            from OCP.TopAbs import TopAbs_OUT

            # distance to the solid's surface mesh (fast), sign from the exact solid classifier only where needed
            _, dist, _ = trimesh.proximity.closest_point(pm, V[idx])
            cand = idx[dist > outside]
            solids = stock.shape.solids()
            for j in cand:
                p = gp_Pnt(*[float(x) for x in V[j]])
                inside = False
                for s in solids:
                    cl = BRepClass3d_SolidClassifier(s.wrapped, p, 1e-6)
                    if cl.State() != TopAbs_OUT:
                        inside = True
                        break
                far[j] = not inside
        F = np.asarray(dm.faces)
        sel = far[F].any(1)
        if sel.any():
            sub = trimesh.Trimesh(V, F[sel], process=False)
            for comp in sub.split(only_watertight=False):
                pts = np.asarray(comp.vertices)
                keep = pts
                ext = keep.max(0) - keep.min(0)
                if ext.max() < min_size:
                    continue
                try:
                    hull = trimesh.convex.convex_hull(keep)
                    hulls.append(np.asarray(hull.vertices, dtype=float))
                except Exception:
                    lo, hi = keep.min(0), keep.max(0)
                    hulls.append(np.array(list(itertools.product(*zip(lo - 0.05, hi + 0.05))), dtype=float))
        np.savez(cp, **{f"h{i:04d}": h for i, h in enumerate(hulls)})
    _MEM[mk] = hulls
    return hulls


def sources_table() -> dict:
    """vendor_cad/SOURCES.md parsed: file name -> row dict."""
    p = root() / "SOURCES.md"
    rows = {}
    if not p.exists():
        return rows
    head = None
    for line in p.read_text().splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if head is None:
            head = [c.lower() for c in cells]
            continue
        if set(cells[0]) <= set("-: "):
            continue
        rows[cells[0].strip("`")] = dict(zip(head, cells))
    return rows


# ------------------------------------------------------------------ the two checks, on a whole design
def _world(P, pts: np.ndarray) -> np.ndarray:
    P = np.asarray(P, dtype=float)
    return pts @ P[:, :3].T + P[:, 3]


def verify_detail(design, r, envelope: bool = True) -> dict:
    """Run `proxy_matches_cad` and (optionally) `detail_clash` on a design; findings go into VerifierResult `r`.
    Returns the metrics block."""
    import time

    t0 = time.time()
    by_key: dict = {}
    kinds: dict = {}
    for c in design.components:
        m = c.meta.get("model") or {}
        if c.cots:
            kinds[m.get("kind", "proxy")] = kinds.get(m.get("kind", "proxy"), 0) + 1
        if c.detail is not None and m.get("key") in STOCKS:
            by_key.setdefault(m["key"], []).append(c)
    out = {"parts_by_model_kind": kinds, "part_types_with_cad": len(by_key), "checked": {}}
    for key, comps in sorted(by_key.items()):
        st = STOCKS[key]
        bad, meas = check_stock(st)
        out["checked"][st.sku] = {"model": st.model.get("kind"), "source": st.model.get("source"), "instances": len(comps),
                                  "mismatches": len(bad),
                                  **{k: meas[k] for k in ("bbox_proxy", "bbox_cad", "volume_proxy_mm3", "volume_cad_mm3") if k in meas},
                                  **({"notes": st.model["notes"]} if st.model.get("notes") else {})}
        if bad:
            r.add("error", "proxy_mismatch",
                  f"{st.sku} ({len(comps)} placed, e.g. {comps[0].name}): its simulation solid does not match its "
                  f"{st.model.get('kind')}: " + "; ".join(b["message"] for b in bad[:6]) + (" ..." if len(bad) > 6 else ""),
                  part=comps[0].name, sku=st.sku, key=key, mismatches=bad,
                  hint="Correct the catalog part's simulation solid or interfaces (or the vendor JSON), or fix the model's "
                       "alignment; if the CAD and the data sheet disagree, record it in the part's model notes.")
    out["proxy_match_seconds"] = round(time.time() - t0, 2)
    if not envelope or getattr(design, "detail_envelope", True) is False:
        return out
    t1 = time.time()
    import trimesh
    from scipy.spatial import ConvexHull

    from ..geom import to_trimesh

    comps = list(design.components)
    boxes = np.array([bbox6(c.shape) for c in comps])
    managers: dict = {}
    clashes = []
    tested = exact = 0

    def touches(j, w):
        """Cheap test first: does the convex hull (world vertices w) cut or contain neighbour j's simulation solid?"""
        o = comps[j]
        try:
            hull = ConvexHull(w)
        except Exception:
            return True
        A, b = hull.equations[:, :3], hull.equations[:, 3]
        tm = to_trimesh(o.shape)
        V = np.asarray(tm.vertices)
        if ((V @ A.T + b) < -0.05).all(1).any():       # a vertex of the neighbour is inside the hull
            return True
        if j not in managers:
            mg = trimesh.collision.CollisionManager()
            mg.add_object("o", tm)
            managers[j] = mg
        hm = trimesh.Trimesh(w, hull.simplices, process=False)
        if managers[j].in_collision_single(hm):
            return True
        from OCP.BRepClass3d import BRepClass3d_SolidClassifier
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN

        ctr = gp_Pnt(*map(float, w.mean(0)))            # the hull wholly inside the neighbour
        return any(BRepClass3d_SolidClassifier(so.wrapped, ctr, 1e-6).State() == TopAbs_IN for so in o.shape.solids())

    for key, group in by_key.items():
        st = STOCKS[key]
        hulls = excess_hulls(st, key)
        if not hulls:
            continue
        mates = tuple(st.model.get("mates_with", ()))
        for c in group:
            P = c.meta.get("placement")
            if P is None:
                continue
            det_solids = None
            hit: dict = {}
            for h in hulls:
                w = _world(P, h)
                lo, hi = w.min(0), w.max(0)
                near = np.where((boxes[:, :3] < hi).all(1) & (boxes[:, 3:] > lo).all(1))[0]
                for j in near:
                    o = comps[j]
                    if o is c or frozenset((c.name, o.name)) in design.allowed_overlaps or \
                            (mates and (o.sku or "").startswith(mates)):
                        continue
                    tested += 1
                    if not touches(j, w):
                        continue
                    exact += 1
                    if det_solids is None:
                        det_solids = [(s, bbox6(s)) for s in c.detail.solids()]
                    # against the neighbour's own detail model where it has one (a carriage's lips sit in the
                    # rail's grooves, which the rail's plain simulation solid does not have)
                    other = o.detail if o.detail is not None else o.shape
                    vol, how = 0.0, "exact"
                    try:
                        for s, sb in det_solids:
                            if (sb[:3] < hi + 0.5).all() and (sb[3:] > lo - 0.5).all() and \
                                    (sb[:3] < boxes[j, 3:]).all() and (sb[3:] > boxes[j, :3]).all():
                                for os_ in other.solids():
                                    ob = bbox6(os_)
                                    if not ((sb[:3] < ob[3:]).all() and (sb[3:] > ob[:3]).all()):
                                        continue
                                    common = s & os_
                                    if common is None or not common.solids():
                                        continue
                                    extra = common - c.shape
                                    vol += sum(q.volume for q in extra.solids()) if extra is not None else 0.0
                    except Exception:
                        how, vol = "convex hull (the exact boolean failed)", 1.0
                    if vol > 0.5:
                        e = hit.setdefault(o.name, {"volume": 0.0, "lo": lo, "hi": hi, "how": how})
                        e["volume"] = max(e["volume"], vol)
                        e["lo"], e["hi"] = np.minimum(e["lo"], lo), np.maximum(e["hi"], hi)
            for other_name, e in hit.items():
                clashes.append((c.name, other_name))
                ctr = ((e["lo"] + e["hi"]) / 2).round(1).tolist()
                r.add("error", "detail_clash",
                      f"{c.name} ({st.sku}): a feature of its {st.model.get('kind')} model that the simulation solid lacks "
                      f"(around {ctr}, {np.round(e['hi'] - e['lo'], 1).tolist()} mm) runs into {other_name} by "
                      f"{e['volume']:.1f} mm^3.",
                      part=c.name, other=other_name, at=ctr, size=np.round(e["hi"] - e["lo"], 2).tolist(),
                      volume=round(e["volume"], 2), test=e["how"],
                      hint="Look at the detail model there (connector, lever, terminals, pins, cable exit): move or turn the "
                           "part, or cut a relief in the neighbour.")
    out["envelope"] = {"pairs_tested": tested, "exact_booleans": exact, "clashes": len(clashes), "seconds": round(time.time() - t1, 2),
                       "pose": "home pose only"}
    return out
