"""Decisive test 1: reach and clearance sweep, and the per-candidate layout optimiser.

Pass (ARM_SCOPE section 4): every required pose / path point reachable inside joint limits with >= 5 deg (or 5 mm)
margin, >= 15 mm clearance between the arm and the printer proxy, door, shelf and stations (the tool may touch only
what the task works on, and its last 25 mm are not checked), one IK branch per path (no flip mid-path), straight sheet
pull >= 240 mm.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np

from . import cell as C
from . import poses as PZ
from .candidates import Articulated5, Cartesian, Scara

CLEAR_MIN = 15.0
MARGIN_MIN = 5.0
Z_T_CHOICES = (229.0, 245.0, 260.0, 275.0, 290.0, 305.0)


class ObstacleSet:
    """Obstacles of one cell state as arrays, for fast point distances."""

    def __init__(self, state: C.CellState):
        obs = C.obstacles(state)
        self.boxes = [o for o in obs if isinstance(o, C.Box)]
        self.panels = [o for o in obs if isinstance(o, C.Panel)]
        self.lo = np.array([b.lo for b in self.boxes])
        self.hi = np.array([b.hi for b in self.boxes])
        self.names = [b.name for b in self.boxes] + [p.name for p in self.panels]

    def dist(self, P):
        """(n, n_obstacles) distances from points P (n,3)."""
        d = np.maximum(np.maximum(self.lo[None] - P[:, None], P[:, None] - self.hi[None]), 0.0)
        out = np.linalg.norm(d, axis=-1)
        cols = [out] + [C.dist_points_panel(P, p)[:, None] for p in self.panels]
        return np.concatenate(cols, axis=1)


_OBS_CACHE: dict = {}


def obstacle_set(state: C.CellState) -> ObstacleSet:
    key = (round(state.z_t, 3), round(state.door_deg, 3), round(state.shelf_off, 3), state.layout)
    if key not in _OBS_CACHE:
        if len(_OBS_CACHE) > 4000:
            _OBS_CACHE.clear()
        _OBS_CACHE[key] = ObstacleSet(state)
    return _OBS_CACHE[key]


def clearance(caps, states, exempt=(), step=10.0):
    best, who = np.inf, ""
    for st in states:
        os_ = obstacle_set(st)
        for c in caps:
            n = max(2, int(np.linalg.norm(c.b - c.a) / step) + 2)
            P = c.a + np.linspace(0, 1, n)[:, None] * (c.b - c.a)
            D = os_.dist(P).min(axis=0) - c.r
            if c.tool and exempt:
                for j, nm in enumerate(os_.names):
                    if nm in exempt:
                        D[j] = np.inf
            j = int(np.argmin(D))
            if D[j] < best:
                best, who = float(D[j]), f"{c.name}~{os_.names[j]}"
    return best, who


@dataclass
class PoseResult:
    id: str
    required: bool
    ok: bool
    reach: bool
    clearance: float
    limiter: str
    margin: float
    qs: list
    pts: list
    note: str = ""
    tilt: float = 0.0


def eval_pose(arm, pose, z_t, step=10.0, layout=None) -> PoseResult:
    """Best result over the pose's allowed tool tilts (the main one, then alternatives such as horizontal)."""
    best = None
    for tilt in [pose.get("tool_axis_tilt_deg", 0.0)] + list(pose.get("alt_tilts_deg", [])):
        r = _eval_pose_tilt(arm, pose, z_t, step, tilt, layout or arm.layout)
        r.tilt = tilt
        if best is None or (r.ok, r.reach, min(r.clearance, 60)) > (best.ok, best.reach, min(best.clearance, 60)):
            best = r
    return best


def _eval_pose_tilt(arm, pose, z_t, step, tilt, layout) -> PoseResult:
    tool = PZ.TOOLS[pose["tool"]]
    pts, states = PZ.resolve(pose, z_t, layout)
    exempt = set(pose["contact"])
    sols = [arm.ik(p, tool[0], tilt) for p in pts]
    if any(len(s) == 0 for s in sols):
        n_bad = sum(len(s) == 0 for s in sols)
        return PoseResult(pose["id"], pose["required"], False, False, -np.inf, "out of reach", -1, [], pts.tolist(),
                          f"{n_bad}/{len(pts)} points out of reach")
    branches = sorted({arm.branch(q) for s in sols for q in s})
    best = None
    for br in branches:
        qs = []
        for s in sols:
            cand = [q for q in s if arm.branch(q) == br]
            if not cand:
                break
            qs.append(cand[0])
        if len(qs) != len(pts):
            continue
        wi = getattr(arm, "WRAP_INDEX", None)     # base joint: a jump means the path crosses the joint's limit gap
        jumps = 0.0 if wi is None else max((abs(a[wi] - b[wi]) for a, b in zip(qs, qs[1:])), default=0.0)
        margin = min(arm.margin_deg(q) for q in qs)
        cl, who = np.inf, ""
        for q, st in zip(qs, states):
            c_, w_ = clearance(arm.capsules(q, tool), st, exempt, step)
            if c_ < cl:
                cl, who = c_, w_
        ok = margin >= MARGIN_MIN and cl >= CLEAR_MIN and jumps < np.radians(30)
        note = "" if jumps < np.radians(30) else "joint wraps mid-path"
        r = PoseResult(pose["id"], pose["required"], ok, True, cl, who, margin, [list(map(float, q)) for q in qs],
                       pts.tolist(), note)
        key = (ok, min(cl, 60) + min(margin, 30))
        if best is None or key > best[0]:
            best = (key, r)
    if best is None:
        return PoseResult(pose["id"], pose["required"], False, False, -np.inf, "no single IK branch", -1, [],
                          pts.tolist(), "no branch reaches every point")
    return best[1]


def max_straight_pull(arm, z_t, limit=420.0, step=10.0) -> float:
    """Longest straight pull (from the tab, at peel height) that stays reachable and clear on one branch."""
    pose = [p for p in PZ.build_poses() if p["id"] == "A4_pull_240"][0]
    best = 0.0
    for L in np.arange(step, limit + step, step):
        p = copy.deepcopy(pose)
        p["points"] = [[C.SHEET_CX, C.GRIP_Y - d, 8.0] for d in np.arange(0, L + 1e-6, step)]
        if eval_pose(arm, p, z_t).ok:
            best = float(L)
        else:
            break
    return best


def evaluate(arm, poses, z_t, early_exit=False, step=10.0):
    res = []
    for p in poses:
        r = eval_pose(arm, p, z_t, step)
        res.append(r)
        if early_exit and p["required"] and not r.ok:
            break
    return res


def score(res, n_required) -> float:
    """Feasibility score for the optimiser: 0 when every required pose passes; positive shortfall otherwise."""
    s = 0.0
    done = 0
    for r in res:
        if not r.required:
            continue
        done += 1
        if not r.reach:
            s += 200.0
        else:
            sh = max(0.0, CLEAR_MIN - r.clearance) + 4 * max(0.0, MARGIN_MIN - r.margin)
            s += sh if (sh > 0 or r.ok) else 50.0      # e.g. a path through the base axis (yaw jump)
    return s + 200.0 * (n_required - done)


# ---------------------------------------------------------------- per-candidate parameterisation
def _set_home(arm, poses, z_t, gap_need_deg):
    """Point the base joint's limit gap at the emptiest direction of the task points."""
    P = arm.params
    pts = np.concatenate([PZ.resolve(p, z_t, arm.layout)[0] for p in poses])
    ang = np.sort(np.degrees(np.arctan2(pts[:, 1] - P["by"], pts[:, 0] - P["bx"])))
    gaps = np.diff(np.concatenate([ang, ang[:1] + 360]))
    i = int(np.argmax(gaps))
    P["home_deg"] = float(ang[i] + gaps[i] / 2 + 180.0)
    return gaps[i] >= gap_need_deg


def make_scara(x, z_t, poses, specs=None):
    bx, by, L1, L2 = x
    zs = [(PZ.resolve(p, z_t, "ring")[0][:, 2], PZ.TOOLS[p["tool"]][0]) for p in poses]
    zcs = [Scara.zc_for(Scara, z.min(), t) for z, t in zs] + [Scara.zc_for(Scara, z.max(), t) for z, t in zs]
    arm = Scara(dict(bx=bx, by=by, L1=L1, L2=L2, zc_min=min(zcs) - 10, zc_max=max(zcs) + 10), specs)
    _set_home(arm, poses, z_t, 30)
    return arm


def make_cart(x, z_t, poses, specs=None):
    (y_m,) = x
    tmp = Cartesian(dict(y_m=y_m, x_min=0, x_max=0, zr_min=0, zr_max=0, e_min=0, e_max=0))
    qs = np.array([tmp.ik(pt, PZ.TOOLS[p["tool"]][0])[0] for p in poses if not p.get("tool_axis_tilt_deg")
                   for pt in PZ.resolve(p, z_t, "row")[0]])
    arm = Cartesian(dict(y_m=y_m, x_min=qs[:, 0].min() - 10, x_max=qs[:, 0].max() + 10, zr_min=qs[:, 1].min() - 10,
                         zr_max=qs[:, 1].max() + 10, e_min=qs[:, 2].min() - 10, e_max=qs[:, 2].max() + 10), specs)
    arm.layout = "row"
    return arm


def make_art(x, z_t, poses, specs=None):
    bx, by, h0, L2, L3 = x
    arm = Articulated5(dict(bx=bx, by=by, h0=h0, L2=L2, L3=L3), specs)
    _set_home(arm, poses, z_t, 20)
    return arm


CANDIDATES = {   # maker, bounds of the free parameters, cost (smaller = smaller / cheaper arm)
    "scara": (make_scara, [(-300, 400), (-750, -280), (150, 450), (150, 450)],
              lambda a: a.params["L1"] + a.params["L2"] + 0.3 * (a.params["zc_max"] - a.params["zc_min"])),
    "cartesian": (make_cart, [(-800, -480)],
                  lambda a: (a.params["x_max"] - a.params["x_min"]) + 2 * (a.params["e_max"] - a.params["e_min"])
                  + 0.5 * (a.params["zr_max"] - a.params["zr_min"])),
    "articulated5": (make_art, [(-300, 400), (-750, -280), (80, 450), (200, 550), (200, 600)],
                     lambda a: a.params["L2"] + a.params["L3"] + 0.3 * a.params["h0"]),
}


def optimise(kind, poses, n_random=250, n_local=250, seed=1, z_choices=Z_T_CHOICES, log=None):
    """Random search then a shrinking local search over (free params, z_T). Returns the best arm, z_T and its results."""
    maker, bounds, cost = CANDIDATES[kind]
    rng = np.random.default_rng(seed)
    req = [p for p in poses if p["required"]]
    lo, hi = np.array([b[0] for b in bounds], float), np.array([b[1] for b in bounds], float)

    def objective(x, z_t):
        arm = maker(x, z_t, poses)
        res = evaluate(arm, req, z_t, early_exit=False, step=10.0)
        s = score(res, len(req))
        return (s if s > 0 else 0.0), (cost(arm) if s == 0 else 1e9), arm

    best = None
    trials = []
    for i in range(n_random):
        x = lo + rng.random(len(lo)) * (hi - lo)
        z_t = float(rng.choice(z_choices))
        s, c, arm = objective(x, z_t)
        trials.append((s, c, x, z_t))
        if best is None or (s, c) < best[:2]:
            best = (s, c, x, z_t)
    span = (hi - lo) * 0.15
    for i in range(n_local):
        x = np.clip(best[2] + rng.normal(0, 1, len(lo)) * span, lo, hi)
        z_t = best[3] if rng.random() < 0.8 else float(rng.choice(z_choices))
        s, c, arm = objective(x, z_t)
        if (s, c) < best[:2]:
            best = (s, c, x, z_t)
        if i % 50 == 49:
            span *= 0.6
        if log and i % 50 == 49:
            log(f"  {kind} local {i + 1}: shortfall {best[0]:.1f} cost {best[1]:.0f} x {np.round(best[2])} zT {best[3]}")
    arm = maker(best[2], best[3], poses)
    return arm, best[3], evaluate(arm, poses, best[3]), best
