"""Geometry helpers shared by verifiers: tessellation, transforms, forward kinematics."""
from __future__ import annotations

import math

import numpy as np
import trimesh
from build123d import Compound, Location, Shape
from OCP.gp import gp_Trsf

from .model import Design, Joint

# id(wrapped) -> (wrapped, mesh). Holding the wrapped object keeps its id from being reused.
_MESH_CACHE: dict[int, tuple] = {}


def to_trimesh(shape: Shape, tol: float = 0.05, ang: float = 0.3) -> trimesh.Trimesh:
    key = id(shape.wrapped)
    if key not in _MESH_CACHE:
        verts, tris = shape.tessellate(tol, ang)
        v = np.array([(p.X, p.Y, p.Z) for p in verts], dtype=float)
        _MESH_CACHE[key] = (shape.wrapped, trimesh.Trimesh(v, np.array(tris, dtype=int), process=False))
    return _MESH_CACHE[key][1]


def translation(v) -> np.ndarray:
    T = np.eye(4)
    T[:3, 3] = v
    return T


def rotation(axis, origin, deg: float) -> np.ndarray:
    return trimesh.transformations.rotation_matrix(math.radians(deg), axis, origin)


def joint_matrix(j: Joint, q: float) -> np.ndarray:
    a = np.array(j.axis, dtype=float)
    a /= np.linalg.norm(a)
    if j.kind == "slide":
        return translation(a * q)
    if j.kind == "hinge":
        return rotation(a, j.origin, q)
    raise ValueError(f"unknown joint kind {j.kind}")


def location_from_matrix(T: np.ndarray) -> Location:
    t = gp_Trsf()
    t.SetValues(*[float(x) for x in T[:3, :].reshape(-1)])
    return Location(t)


def body_tree(design: Design) -> dict[str, Joint]:
    """child body -> joint connecting it to its parent. Validates the tree."""
    by_child: dict[str, Joint] = {}
    for j in design.joints:
        if j.child in by_child:
            raise ValueError(f"body {j.child} is the child of two joints (closed loops unsupported)")
        by_child[j.child] = j
    for b in design.bodies():
        seen, cur = set(), b
        while cur != "world":
            if cur in seen:
                raise ValueError(f"joint cycle at body {cur}")
            seen.add(cur)
            if cur not in by_child:
                raise ValueError(f"body {cur} has no joint path to world")
            cur = by_child[cur].parent
    return by_child


def forward_kinematics(design: Design, q: dict[str, float]) -> dict[str, np.ndarray]:
    """World transform of every body for joint values q (missing joints = 0 = home)."""
    by_child = body_tree(design)
    out: dict[str, np.ndarray] = {"world": np.eye(4)}

    def T(body: str) -> np.ndarray:
        if body not in out:
            j = by_child[body]
            out[body] = T(j.parent) @ joint_matrix(j, q.get(j.name, 0.0))
        return out[body]

    for b in design.bodies():
        T(b)
    return out


def bbox_of(shapes) -> tuple[np.ndarray, np.ndarray]:
    lo = np.full(3, np.inf)
    hi = np.full(3, -np.inf)
    for s in shapes:
        bb = s.bounding_box()
        lo = np.minimum(lo, [bb.min.X, bb.min.Y, bb.min.Z])
        hi = np.maximum(hi, [bb.max.X, bb.max.Y, bb.max.Z])
    return lo, hi


def bboxes_overlap(a: Shape, b: Shape, margin: float = 0.0) -> bool:
    A, B = a.bounding_box(), b.bounding_box()
    return not (
        A.max.X + margin < B.min.X or B.max.X + margin < A.min.X
        or A.max.Y + margin < B.min.Y or B.max.Y + margin < A.min.Y
        or A.max.Z + margin < B.min.Z or B.max.Z + margin < A.min.Z
    )


def overlap_volume(a: Shape, b: Shape) -> tuple[float, tuple[float, float, float] | None]:
    """Exact B-rep interference volume between two shapes and where it is."""
    try:
        common = a.intersect(b)
    except Exception:
        common = None
    if common is None:
        return 0.0, None
    items = common if isinstance(common, (list, tuple)) else [common]
    vol, center = 0.0, None
    for it in items:
        try:
            for s in it.solids():
                v = s.volume
                if v > vol * 0 and v > 0:
                    if center is None or v > vol:
                        c = s.center()
                        center = (round(c.X, 2), round(c.Y, 2), round(c.Z, 2))
                    vol += v
        except Exception:
            continue
    return vol, center
