"""Stack-up by simulation: build the machine many times, each part a little off and each joint
seated a little off, and see where the things that matter end up.

Every joint between two parts adds a small random shift and tilt (from the accuracy of the two
parts and the play in their screws), and each part is made slightly over or under size. A part
held by several joints cannot satisfy them all exactly, so its position is the best compromise
between them (least squares, each joint weighted by how tightly it locates). That is what makes a
closed frame squarer than a chain of the same joints.

Small-displacement, rigid-body estimate: parts do not bend to fit, and thermal growth is separate.
"""
from __future__ import annotations

import math

import numpy as np

from ..geom import bboxes_overlap
from ..model import Design
from .process import process_of, tol

N = 3000


def _bb(shape):
    b = shape.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z])


def _skew_rows(c):
    """Rows of the matrix M such that theta x c = M @ theta."""
    return np.array([[0, c[2], -c[1]], [-c[2], 0, c[0]], [c[1], -c[0], 0]])


class Build:
    """n randomly-built copies of the design. `at(part, point)` gives where a point on a part ends up."""

    def __init__(self, design: Design, n: int = N, seed: int = 0, screw_play: dict | None = None):
        self.d, self.n = design, n
        rng = np.random.default_rng(seed)
        comps = {c.name: c for c in design.components}
        self.comps = comps
        fast = {f.name for f in design.fasteners}
        names = sorted(k for k in comps if k not in fast)       # screws clamp; they do not locate
        box = {k: _bb(comps[k].shape) for k in names}
        self.centroid = {k: (box[k][0] + box[k][1]) / 2 for k in names}
        pairs = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                near = False
                if bboxes_overlap(comps[a].shape, comps[b].shape, 0.05):
                    try:
                        near = comps[a].shape.distance_to(comps[b].shape) <= 0.05
                    except Exception:
                        near = True
                if near or frozenset((a, b)) in design.joins:
                    pairs.append((a, b))
        base = design.base if design.base in names else max(names, key=lambda k: comps[k].shape.volume)
        # keep only parts connected to the base
        adj = {k: set() for k in names}
        for a, b in pairs:
            adj[a].add(b); adj[b].add(a)
        seen, stack = set(), [base]
        while stack:
            k = stack.pop()
            if k in seen:
                continue
            seen.add(k)
            stack.extend(adj[k] - seen)
        self.unplaced = sorted(set(names) - seen)
        free = sorted(seen - {base})
        idx = {k: 6 * i for i, k in enumerate(free)}
        play = screw_play or {}
        rows, rhs, self.iface = [], [], []
        for a, b in pairs:
            if a not in seen or b not in seen:
                continue
            lo = np.maximum(box[a][0], box[b][0]) - 0.05
            hi = np.minimum(box[a][1], box[b][1]) + 0.05
            ext = np.maximum(hi - lo, 0.0)
            c = (lo + hi) / 2
            L = max(float(np.sort(ext)[-1]), 8.0)
            normal = int(np.argmin(ext))
            ta, tb = tol(comps[a]), tol(comps[b])
            s_seat = math.hypot(ta["flat"], tb["flat"])
            s_pos = math.hypot(ta["pos"], tb["pos"])
            slop = play.get(frozenset((a, b)), 0.1)
            S = _skew_rows(c)
            et = np.zeros((n, 3))
            for k in range(3):
                sig = s_seat if k == normal else math.sqrt(s_pos ** 2 + slop ** 2 / 3)
                et[:, k] = rng.normal(0, s_seat, n) if k == normal else rng.normal(0, s_pos, n) + rng.uniform(-slop, slop, n)
                row = np.zeros(6 * len(free))
                for part, sgn in ((b, 1.0), (a, -1.0)):
                    if part in idx:
                        row[idx[part] + k] = sgn
                        row[idx[part] + 3:idx[part] + 6] = sgn * S[k]
                rows.append(row / sig)
                rhs.append((et[:, k], sig, a, b, k, c))
            for k in range(3):
                sig = (s_pos + slop / 2) / L if k == normal else s_seat / L
                er = rng.normal(0, sig, n)
                row = np.zeros(6 * len(free))
                for part, sgn in ((b, 1.0), (a, -1.0)):
                    if part in idx:
                        row[idx[part] + 3 + k] = sgn
                rows.append(row / sig)
                rhs.append((er, sig, a, b, None, c))
            self.iface.append((a, b, et))
        self.eps = {k: rng.normal(0, tol(comps[k])["scale"], n) for k in seen}
        # right-hand sides: the random joint error, less what the two parts' size errors already account for
        R = np.zeros((len(rows), n))
        for r_i, (e, sig, a, b, k, c) in enumerate(rhs):
            v = e.copy()
            if k is not None:
                v = v - self.eps[b] * (c[k] - self.centroid[b][k]) + self.eps[a] * (c[k] - self.centroid[a][k])
            R[r_i] = v / sig
        Amat = np.array(rows)
        X = np.linalg.pinv(Amat) @ R if len(free) else np.zeros((0, n))
        self.t = {base: np.zeros((n, 3))}
        self.th = {base: np.zeros((n, 3))}
        for k_, i0 in idx.items():
            self.t[k_] = X[i0:i0 + 3].T
            self.th[k_] = X[i0 + 3:i0 + 6].T
        self.A = self.t   # parts that were placed

    def at(self, part: str, point) -> np.ndarray:
        """(n, 3) positions of a point (given at its drawn position) on `part` across the builds."""
        p = np.array(point, dtype=float)
        return (p[None, :] + self.t[part] + np.cross(self.th[part], p[None, :])
                + self.eps[part][:, None] * (p - self.centroid[part])[None, :])

    def direction(self, part: str, axis) -> np.ndarray:
        """(n, 3) unit direction of an axis fixed in `part` across the builds."""
        a = np.array(axis, dtype=float)
        v = a[None, :] + np.cross(self.th[part], a[None, :])
        return v / np.linalg.norm(v, axis=1, keepdims=True)

    def nearest_part(self, body: str, point) -> str:
        best, bd = None, 1e18
        p = np.array(point, dtype=float)
        for c in self.d.components:
            if c.body != body or c.name not in self.A:
                continue
            lo, hi = _bb(c.shape)
            dd = float(np.linalg.norm(np.maximum(lo - p, 0) + np.maximum(p - hi, 0)))
            if dd < bd:
                best, bd = c.name, dd
        return best

    def blame(self, outcome: np.ndarray, top: int = 5) -> list:
        """The joints whose seating error the outcome follows most closely."""
        rows = []
        for a, b, et in self.iface:
            cc = 0.0
            for k in range(3):
                if et[:, k].std() > 0:
                    cc = max(cc, abs(float(np.corrcoef(et[:, k], outcome)[0, 1])))
            rows.append((round(cc, 2), f"{a} / {b}", process_of(self.comps[a]), process_of(self.comps[b])))
        return [{"joint": j, "processes": [pa, pb], "correlation": c_} for c_, j, pa, pb in sorted(rows, reverse=True)[:top]]
