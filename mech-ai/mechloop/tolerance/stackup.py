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

from ..geom import bboxes_overlap, overlap_volume
from ..model import Design
from .process import process_of, tol

N = 3000
SEED = 0             # every tolerance simulation uses fixed seeds and a fixed order of draws: identical runs agree exactly
SCREWED_JOINTS = True   # parts clamped to each other by a screw are located by it even when they do not touch (tests switch it off to show the old result)
CLASH_VOL = 0.5      # mm^3: two parts overlapping by more than this (and not a declared thread / press fit) clash


def std_error(p: float, n: int) -> float:
    """Monte Carlo standard error of a share p estimated from n simulated builds."""
    return math.sqrt(max(p * (1.0 - p), 0.0) / max(n, 1))


def near_limit(p: float, n: int, limit: float) -> bool:
    """True when p is within two standard errors of `limit`: the simulation cannot tell which side it is on. For a
    share of exactly 0 or 1 the error is taken from one build in n (the estimate cannot be closer than that)."""
    se = max(std_error(p, n), std_error(1.0 / max(n, 1), n))
    return abs(p - limit) <= 2.0 * se


def _bb(shape):
    b = shape.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z])


def _skew_rows(c):
    """Rows of the matrix M such that theta x c = M @ theta."""
    return np.array([[0, c[2], -c[1]], [-c[2], 0, c[0]], [c[1], -c[0], 0]])


def design_axis(design: Design, fastener_name: str):
    return next(f.axis for f in design.fasteners if f.name == fastener_name)


class Build:
    """n randomly-built copies of the design. `at(part, point)` gives where a point on a part ends up."""

    def __init__(self, design: Design, n: int = N, seed: int = SEED, screw_play: dict | None = None):
        self.d, self.n, self.seed = design, n, seed
        rng = np.random.default_rng(seed)
        comps = {c.name: c for c in design.components}
        self.comps = comps
        # bent sheet parts: bend angle and bend-line scatter (mechloop/tolerance/bends.py). Drawn from their own random
        # streams, so a design without bent parts gives exactly the numbers it gave before bends were modelled.
        from .bends import bends_of

        self.bends, self.bends_not_recognised = bends_of(design, n, seed)
        fast = {f.name for f in design.fasteners}
        names = sorted(k for k in comps if k not in fast)       # screws clamp; they do not locate
        box = {k: _bb(comps[k].shape) for k in names}
        self.centroid = {k: (box[k][0] + box[k][1]) / 2 for k in names}
        pairs = []
        # Two parts that touch locate each other: that contact is a joint of the stack-up. Two parts that OVERLAP are
        # not seated on each other, they are drawn through each other: a clash. A clash must never count as a joint
        # (it would tie the two parts together and tighten every chain through them), unless the overlap is a declared
        # thread or press fit (design.allow_overlap) or the pair has a declared join.
        self.clashes: list = []
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                near = False
                key = frozenset((a, b))
                if bboxes_overlap(comps[a].shape, comps[b].shape, 0.05):
                    try:
                        near = comps[a].shape.distance_to(comps[b].shape) <= 0.05
                    except Exception:
                        near = True
                    if near and key not in design.joins:
                        try:
                            vol, _ = overlap_volume(comps[a].shape, comps[b].shape)
                        except Exception:
                            vol = 0.0
                        allowed = design.allowed_overlaps.get(key)
                        if vol > CLASH_VOL and (allowed is None or vol > allowed):
                            near = False
                            self.clashes.append({"parts": [a, b], "overlap_mm3": round(float(vol), 2)})
                if near or key in design.joins:
                    pairs.append((a, b))
        # A screw that clamps two parts locates them on each other whether or not they touch (a plate on standoffs or
        # on a post between jam nuts, a part over a spacer): that screwed joint is a joint of the stack-up, placed at
        # the screw(s), with the screw's axis as its seating direction. Without it the part would be located only
        # through whatever else it happens to touch, or not at all.
        have = {frozenset(p_) for p_ in pairs}
        clash_keys = {frozenset(c_["parts"]) for c_ in self.clashes}
        screwed: dict = {}
        for f in (design.fasteners if SCREWED_JOINTS else ()):
            held = [k for k in dict.fromkeys(list(f.clamps) + list((comps[f.name].meta.get("threads_into") or []) if f.name in comps else []))
                    if k in box]
            if len(held) < 2 or f.name not in comps:
                continue
            ax = np.array(f.axis, dtype=float)
            ax /= max(np.linalg.norm(ax), 1e-12)
            # order the held parts along the screw; each locates the next
            held.sort(key=lambda k: float(np.dot(self.centroid[k], ax)))
            # only consecutive solid parts: a nut or spacer between two plates touches both and carries the chain itself
            for a, b in zip(held[:-1], held[1:]):
                key = frozenset((a, b))
                if key in clash_keys:
                    continue
                screwed.setdefault(tuple(sorted((a, b))), []).append(f.name)
        self.screwed_apart = []
        self._screw_box = {}
        for (a, b), screws in sorted(screwed.items()):
            los, his = zip(*[_bb(comps[s_].shape) for s_ in screws])
            self._screw_box[frozenset((a, b))] = (np.min(los, axis=0), np.max(his, axis=0), np.array(design_axis(design, screws[0])))
            if frozenset((a, b)) not in have:
                pairs.append((a, b))
                self.screwed_apart.append({"parts": [a, b], "screws": screws})
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
        rot_k: dict = {}       # row index -> axis, for the rotation rows
        for a, b in pairs:
            if a not in seen or b not in seen:
                continue
            lo = np.maximum(box[a][0], box[b][0]) - 0.05
            hi = np.minimum(box[a][1], box[b][1]) + 0.05
            ext = np.maximum(hi - lo, 0.0)
            c = (lo + hi) / 2
            L = max(float(np.sort(ext)[-1]), 8.0)
            normal = int(np.argmin(ext))
            sb = self._screw_box.get(frozenset((a, b)))
            if sb is not None and any(p_["parts"] == sorted((a, b)) for p_ in self.screwed_apart):
                # two parts held apart on screws: the joint is where the screws are (across the screws: their own
                # extent; along them: the span between the two parts), seated along the screw
                normal = int(np.argmax(np.abs(sb[2])))
                lo, hi = sb[0].copy(), sb[1].copy()
                lo[normal] = min(box[a][1][normal], box[b][1][normal])
                hi[normal] = max(box[a][0][normal], box[b][0][normal])
                if hi[normal] < lo[normal]:
                    lo[normal], hi[normal] = hi[normal], lo[normal]
                ext = np.maximum(hi - lo, 0.0)
                c = (lo + hi) / 2
                lat = [float(ext[k_]) for k_ in range(3) if k_ != normal]
                L = max(max(lat), 8.0)
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
                rot_k[len(rows) - 1] = k
            self.iface.append((a, b, et))
        self.eps = {k: rng.normal(0, tol(comps[k])["scale"], n) for k in sorted(seen)}     # sorted: a set's order changes run to run
        # right-hand sides: the random joint error, less what the two parts' size errors already account for
        R = np.zeros((len(rows), n))
        for r_i, (e, sig, a, b, k, c) in enumerate(rhs):
            v = e.copy()
            if k is not None:
                v = v - self.eps[b] * (c[k] - self.centroid[b][k]) + self.eps[a] * (c[k] - self.centroid[a][k])
            # a flange of a bent part is not where the drawing has it: what sits on it moves and turns with it
            for part, sgn in ((a, 1.0), (b, -1.0)):
                pb = self.bends.get(part)
                if pb is not None:
                    v = v + sgn * (pb.displacement(c)[:, k] if k is not None else pb.rotation(c)[:, rot_k[r_i]])
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
        out = (p[None, :] + self.t[part] + np.cross(self.th[part], p[None, :])
               + self.eps[part][:, None] * (p - self.centroid[part])[None, :])
        pb = self.bends.get(part)
        if pb is not None:
            out = out + pb.displacement(p)
        return out

    def direction(self, part: str, axis, at=None) -> np.ndarray:
        """(n, 3) unit direction of an axis fixed in `part` across the builds. For a bent part pass `at`, a point on
        the flange the axis belongs to: that flange's bend error is then included."""
        a = np.array(axis, dtype=float)
        th = self.th[part]
        pb = self.bends.get(part)
        if pb is not None and at is not None:
            th = th + pb.rotation(at)
        v = a[None, :] + np.cross(th, a[None, :])
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


# ---------------------------------------------------------------------------------------------------------------------
# One Build per design and run: the tolerance verifier makes it, later checks (clearances under tolerance, the
# endstop and probe windows of the subsystems verifier) reuse it instead of simulating the builds again.
_LAST: dict = {}


def _signature(design: Design) -> tuple:
    return (tuple((c.name, id(c.shape.wrapped), c.body) for c in design.components), len(design.joins),
            len(design.fasteners), len(design.allowed_overlaps))


def remember(design: Design, build: "Build") -> None:
    _LAST.clear()
    _LAST[id(design)] = (_signature(design), build)


def build_for(design: Design, n: int = N) -> "Build":
    """The Build the tolerance verifier made for this design in this process, or a new one made the same way
    (screw play from the screw patterns), so a check run on its own gives the same numbers."""
    hit = _LAST.get(id(design))
    if hit is not None and hit[0] == _signature(design) and hit[1].n == n:
        return hit[1]
    from ..report import VerifierResult
    from .fits import screw_patterns

    play = {}
    for key, v in screw_patterns(design, VerifierResult("tolerance"), n).items():
        a, b = key.split(" -> ")
        play[frozenset((a, b))] = max(v["nominal_radial_clearance_mm"], 0.0)
    B = Build(design, n, screw_play=play)
    remember(design, B)
    return B
