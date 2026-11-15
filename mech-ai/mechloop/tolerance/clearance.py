"""Clearance under tolerance: does a gap that is drawn open stay open when the machine is really built?

The interference verifier works on the drawing. A gap of 0.05 mm passes it exactly as a gap of 5 mm does, although the
first is smaller than what the parts on either side of it can be held to. This check takes every pair of parts that
are NOT a designed contact and whose drawn gap is below THRESHOLD_MM (anywhere in the joints' travel for a pair on two
sides of a joint), and puts the pair through the stack-up the tolerance verifier already simulated: across the same
builds, how wide is the gap, and in what share of them has it closed?

  gap_i = drawn gap + n . (where part B's closest point ended up - where part A's did) + the two surfaces' own error

  n          direction of the drawn gap (from A's closest point to B's), at the pose where the gap is smallest
  positions  mechloop.tolerance.stackup.Build.at for the two parts (process classes per part, every joint of the chain
             between them, bend scatter of bent sheet parts); a screw rides on the part it is threaded into
  travel     a pair across a joint is taken at its closest approach in the joint's mechanical travel and at the
             travel's ends; the as-built direction of the joint's rail (not the drawn axis) carries the body there
  surfaces   each part's own feature-position error (PROCESS[...]["pos"]), independent of the rigid stack-up

Small displacements along the drawn gap direction: an edge sliding past a corner sideways is not modelled.

Judgement (limits stated in every finding):
  share of builds in which the gap has closed  > P_CLOSE_ERROR (1 %)   error    `clearance_closes_under_tolerance`
  0 < share <= 1 %, or none seen in the builds but the spread says at least one in the number simulated   warning
The 1 % line is the one the screw-pattern check reports from (a pattern that starts in under 99 % of builds); a gap
that has closed means two parts are pressed into or rubbing on each other, which is at least as bad as a screw that
has to be forced. Every share carries its standard error, sqrt(p (1 - p) / builds), and is flagged when it is within
two standard errors of the limit.

Design rule, separately (warning `clearance_below_minimum`): a designed clearance between two non-mating parts smaller
than the minimum for the processes involved, whatever the simulation says about it. Defaults, MIN_CLEARANCE_MM: the
larger of the two parts' figures, printed 0.5, saw-cut extrusion 0.5, sheet 0.3, machined 0.2, purchased 0.2 mm. Each
is about four standard deviations of that process's own feature position and face flatness in the PROCESS table
(printed: hypot(0.12, 0.10) x 4 = 0.6; sheet: hypot(0.08, 0.10) x 4 = 0.5, taken as 0.3 because a laser-cut edge is the
accurate feature of a sheet part and its 0.10 flatness acts across the gap only for faces; machined 0.18; purchased
0.09, floored at 0.2 for burrs, paint and labels), i.e. the smallest gap the part's own accuracy can guarantee before
any joint error is added. Override: design.manufacturing["min_clearance_mm"] = 0.4 or {"printed": 0.6, ...}; a pair
with its own design.require_clearance(a, b, gap) is judged against that by the interference verifier and not here.

THRESHOLD_MM = 1.5: pairs drawn further apart than this are not examined. 1.5 mm is the 99.7th percentile of the
longest chain in the machines this was written for (frame to gantry to toolhead against frame to Z axis to bed:
printer_v7 1.48 mm); a chain that scatters more than the threshold is reported (`clearance_search_threshold`), so a
pair that was not looked at is never read as a pair that passed. Override: design.manufacturing["clearance_check_mm"].

What is NOT reported, because it is a designed contact or is judged elsewhere:
  parts that touch (drawn gap <= 0.02 mm: a seat) or overlap (the interference verifier's business)
  pairs with a declared join or allowed overlap (press fit, thread, clamp, set screw, axle, bond)
  a screw against the parts it clamps, threads into or passes through, and against its own nut
  a screw whose head is recessed in a counterbore of a part of its stack, against a part seated on that face over it
  a guide block, bearing or nut tagged `guides=` against the rail, rod or screw it runs on
  a shaft in its bore (coaxial cylinders: the fit check judges those)
  a toolhead part against the bed in the nozzle approach: the motion verifier's toolhead margin judges that
  belts and cables (not solid parts)
"""
from __future__ import annotations

import itertools
import math

import numpy as np

from ..geom import forward_kinematics, location_from_matrix, to_trimesh
from ..model import Design
from ..report import VerifierResult
from .process import process_of, tol
from .stackup import Build, _bb, near_limit, std_error

THRESHOLD_MM = 1.5
P_CLOSE_ERROR = 0.01
TOUCH_MM = 0.02
MIN_CLEARANCE_MM = {"printed": 0.5, "extrusion": 0.5, "sheet": 0.3, "machined": 0.2, "purchased": 0.2}
MAX_FINDINGS = 25
GRID = 5            # samples per joint in the search for the closest approach

_FCL: dict = {}


def min_clearance_for(design: Design, a, b) -> tuple[float, str]:
    own = (design.manufacturing or {}).get("min_clearance_mm")
    table = dict(MIN_CLEARANCE_MM)
    basis = "default for the processes"
    if isinstance(own, (int, float)):
        return float(own), "declared: design.manufacturing['min_clearance_mm']"
    if isinstance(own, dict):
        table.update({k: float(v) for k, v in own.items()})
        basis = "design.manufacturing['min_clearance_mm'] / default for the processes"
    pa, pb = process_of(a), process_of(b)
    return max(table[pa], table[pb]), f"{basis}: {pa} {table[pa]:g} mm, {pb} {table[pb]:g} mm, the larger"


def _fcl_objects(design: Design) -> dict:
    import fcl

    sig = tuple((c.name, id(c.shape.wrapped)) for c in design.components)
    hit = _FCL.get(id(design))
    if hit is not None and hit[0] == sig:
        return hit[1]
    objs = {}
    for c in design.components:
        m = to_trimesh(c.shape)
        bvh = fcl.BVHModel()
        bvh.beginModel(len(m.vertices), len(m.faces))
        bvh.addSubModel(np.asarray(m.vertices, dtype=float), np.asarray(m.faces, dtype=np.int32))
        bvh.endModel()
        objs[c.name] = fcl.CollisionObject(bvh, fcl.Transform())
    _FCL.clear()
    _FCL[id(design)] = (sig, objs)
    return objs


def _joint_path(design: Design) -> dict:
    """body -> joints from it up to the world."""
    by_child = {j.child: j for j in design.joints}
    out = {}
    for b in design.bodies():
        path, cur, seen = [], b, set()
        while cur in by_child and cur not in seen:
            seen.add(cur)
            path.append(by_child[cur])
            cur = by_child[cur].parent
        out[b] = path
    return out


def screw_stacks(design: Design) -> dict:
    """fastener name -> the parts it is a designed interface with: what it threads into, clamps or passes through
    (the FEA's rule for a screw's stack), its nut, and what its nut sits in."""
    from ..verifiers.fea import _screw_stacks

    fast = {f.name for f in design.fasteners}
    names = [c.name for c in design.components if c.name not in fast]
    out = {}
    try:
        for _, _, _, sname, held in _screw_stacks(design, names):
            out[sname] = set(held)
    except Exception:
        pass
    for f in design.fasteners:
        out.setdefault(f.name, set()).update(f.clamps)
    for key, kind in design.joins.items():
        if len(key) != 2:
            continue
        a, b = tuple(key)
        for s, o in ((a, b), (b, a)):
            if s in fast:
                out.setdefault(s, set()).add(o)
    return out


def guide_partners(design: Design) -> set:
    """Pairs (frozenset) of a part tagged `guides=` and the rail, rod or screw it runs on."""
    joints = {j.name: j for j in design.joints}
    out = set()
    for blk in design.components:
        j = joints.get(blk.meta.get("guides"))
        if j is None:
            continue
        other = j.parent if blk.body == j.child else j.child
        best, bd = None, 1.0
        for c in design.components:
            if c.body != other:
                continue
            lo_a, hi_a = _bb(blk.shape)
            lo_b, hi_b = _bb(c.shape)
            if np.any(lo_a - hi_b > 1.0) or np.any(lo_b - hi_a > 1.0):
                continue
            try:
                dd = blk.shape.distance_to(c.shape)
            except Exception:
                continue
            if dd < bd:
                best, bd = c, dd
        if best is not None:
            out.add(frozenset((blk.name, best.name)))
    for j in design.joints:
        drv = j.drive or {}
        nuts = drv.get("nut")
        screws = drv.get("screw")
        for nut in ([nuts] if isinstance(nuts, str) else list(nuts or [])):
            for scr in ([screws] if isinstance(screws, str) else list(screws or [])):
                out.add(frozenset((nut, scr)))
    return out


def rails_of_joints(design: Design) -> dict:
    """joint name -> the first rail (partner of a guide part) of that joint, for its as-built direction."""
    out = {}
    comps = {c.name: c for c in design.components}
    for pair in sorted(guide_partners(design), key=sorted):
        a, b = sorted(pair)
        blk, rail = (a, b) if comps[a].meta.get("guides") else (b, a)
        if comps[blk].meta.get("guides") and "static_load_n" in comps[blk].ratings:
            out.setdefault(comps[blk].meta["guides"], rail)
    return out


def _exact(sa, sb):
    """(distance, point on a, point on b) between two shapes, exact."""
    from OCP.BRepExtrema import BRepExtrema_DistShapeShape

    ex = BRepExtrema_DistShapeShape(sa.wrapped, sb.wrapped)
    if not ex.IsDone() or ex.NbSolution() < 1:
        return None
    p, q = ex.PointOnShape1(1), ex.PointOnShape2(1)
    return float(ex.Value()), np.array([p.X(), p.Y(), p.Z()]), np.array([q.X(), q.Y(), q.Z()])


class Scatter:
    """Relative as-built displacement of two parts' points, from one Build. Shared by the clearance check and the
    functional windows of the subsystems verifier (endstop window, probe keep-out zone)."""

    def __init__(self, design: Design, B: Build):
        self.d, self.B = design, B
        self.comps = {c.name: c for c in design.components}
        self.fast = {f.name for f in design.fasteners}
        self.paths = _joint_path(design)
        self.rails = rails_of_joints(design)
        self.stacks = None
        self._carrier: dict = {}
        self._dir: dict = {}
        self.rng = np.random.default_rng([B.seed, 7919])

    def carrier(self, name: str) -> str | None:
        """The part whose as-built position a part takes: itself when the stack-up placed it; for a screw the part it
        threads into (else one it clamps); None when nothing ties it to the stack-up."""
        if name in self._carrier:
            return self._carrier[name]
        out = None
        if name in self.B.A:
            out = name
        else:
            c = self.comps.get(name)
            cands = list((c.meta.get("threads_into") or [])) if c is not None else []
            for f in self.d.fasteners:
                if f.name == name:
                    cands += list(f.clamps)
            if self.stacks is None:
                self.stacks = screw_stacks(self.d)
            cands += sorted(self.stacks.get(name, ()))
            # a nut is placed by contact; a screw threaded into a nut takes the nut's position
            out = next((x for x in cands if x in self.B.A and x not in self.fast), None)
        self._carrier[name] = out
        return out

    def joint_dir_error(self, j) -> np.ndarray | None:
        """(n, 3): as-built direction of travel of a slide joint minus its drawn axis; None when it has no rail in the
        stack-up (the drawn axis is then used) or is a hinge."""
        if j.name in self._dir:
            return self._dir[j.name]
        out = None
        rail = self.rails.get(j.name)
        if j.kind == "slide" and rail in self.B.A:
            ax = np.array(j.axis, dtype=float)
            ax /= np.linalg.norm(ax)
            out = self.B.direction(rail, ax) - ax[None, :]
        self._dir[j.name] = out
        return out

    def displacement(self, name: str, point_home, q: dict) -> np.ndarray | None:
        """(n, 3): where a point of a part (given at the HOME pose) ends up at pose q across the builds, minus where
        the drawing puts it there. Slide joints: the stack-up at home plus the travel along the rail's as-built
        direction. None when the part is not tied to the stack-up."""
        car = self.carrier(name)
        if car is None:
            return None
        p = np.asarray(point_home, dtype=float)
        dlt = self.B.at(car, p) - p[None, :]
        body = self.comps[name].body
        for j in self.paths.get(body, []):
            qj = float(q.get(j.name, 0.0))
            if abs(qj) < 1e-12:
                continue
            e = self.joint_dir_error(j)
            if e is not None:
                dlt = dlt + qj * e
        return dlt

    def local_sd(self, a: str, b: str) -> float:
        return math.hypot(tol(self.comps[a])["pos"], tol(self.comps[b])["pos"])

    def relative(self, a: str, pa_home, b: str, pb_home, q: dict, direction) -> np.ndarray | None:
        """(n,): change of (B's point - A's point) along `direction` across the builds, with the two surfaces' own
        feature error added. None when either part is not tied to the stack-up."""
        da, db = self.displacement(a, pa_home, q), self.displacement(b, pb_home, q)
        if da is None or db is None:
            return None
        n = np.asarray(direction, dtype=float)
        n = n / np.linalg.norm(n)
        return (db - da) @ n + self.rng.normal(0.0, self.local_sd(a, b), self.B.n)

    def chain_note(self, a: str, b: str, q: dict) -> dict:
        ca, cb = self.comps[a], self.comps[b]
        js = [j.name for j in self.paths.get(ca.body, []) if j not in self.paths.get(cb.body, [])] + \
             [j.name for j in self.paths.get(cb.body, []) if j not in self.paths.get(ca.body, [])]
        return {"processes": [process_of(ca), process_of(cb)], "joints_between": js,
                **({"carried_by": {x: self.carrier(x) for x in (a, b) if self.carrier(x) != x}}
                   if any(self.carrier(x) != x for x in (a, b)) else {})}


def share_closed(g0: float, delta: np.ndarray, limit: float = P_CLOSE_ERROR) -> dict:
    """Share of builds in which a gap drawn g0 wide has closed, with its standard error, the spread and a normal
    estimate of the tail for when no simulated build closed it."""
    n = len(delta)
    g = g0 + delta
    p = float((g <= 0.0).mean())
    sd = float(delta.std())
    mean = float(g.mean())
    p_est = 0.5 * math.erfc((mean / sd) / math.sqrt(2.0)) if sd > 0 else (1.0 if mean <= 0 else 0.0)
    return {"p_closed": round(p, 4), "p_closed_standard_error": round(std_error(p, n), 4), "limit": limit,
            "within_sampling_error_of_the_limit": near_limit(p, n, limit), "builds": n,
            "gap_sd_mm": round(sd, 3), "gap_mm_0p15_percentile": round(float(np.percentile(g, 0.15)), 3),
            "p_closed_normal_estimate": float(f"{p_est:.2g}")}


def severity_of(sh: dict) -> str | None:
    if sh["p_closed"] > sh["limit"]:
        return "error"
    if sh["p_closed"] > 0.0 or sh["p_closed_normal_estimate"] >= 1.0 / sh["builds"]:
        return "warning"
    return None


def near_pairs(design: Design, threshold: float, skip=None) -> tuple[list, dict]:
    """Every pair of parts whose drawn gap is under `threshold` somewhere in the joints' mechanical travel and that is
    not touching or overlapping there. Returns ([{a, b, gap, pa, pb (world, at pose), q, poses: [...]}], counts).
    `skip(a, b)` -> reason or None removes designed contacts before any geometry is measured."""
    import fcl

    comps = design.components
    objs = _fcl_objects(design)
    paths = _joint_path(design)
    box = {c.name: _bb(c.shape) for c in comps}
    counts = {"pairs": 0, "boxes_within_threshold": 0, "designed_contacts_skipped": {}, "touching_or_overlapping": 0,
              "measured_exactly": 0}
    approach = None
    try:
        from ..verifiers.motion import nozzle_approach

        approach = nozzle_approach(design)
    except Exception:
        approach = None
    slide_only = all(j.kind == "slide" for j in design.joints)
    eye = fcl.Transform()
    out = []
    req = fcl.DistanceRequest(enable_nearest_points=False)

    def fdist(a, b, t):
        objs[a].setTransform(eye)
        objs[b].setTransform(fcl.Transform(np.eye(3), np.asarray(t, dtype=float)) if t is not None else eye)
        res = fcl.DistanceResult()
        return float(fcl.distance(objs[a], objs[b], req, res))

    for ca, cb in itertools.combinations(comps, 2):
        counts["pairs"] += 1
        a, b = ca.name, cb.name
        (lo_a, hi_a), (lo_b, hi_b) = box[a], box[b]
        js = []
        if ca.body != cb.body:
            pa_, pb_ = paths.get(ca.body, []), paths.get(cb.body, [])
            js = [(j, -1.0) for j in pa_ if j not in pb_] + [(j, 1.0) for j in pb_ if j not in pa_]
            js = [(j, s) for j, s in js if j.mechanical_range[0] != j.mechanical_range[1]]
        if js and not slide_only:
            js_generic = True
        else:
            js_generic = False
        # travel of B relative to A: an axis-aligned box of translations (slides), used to sweep B's bounding box
        rng_ = []
        for j, s in js:
            lo_q, hi_q = j.mechanical_range
            if approach and j.name == approach["joint"] and approach["tool_body"] in (ca.body, cb.body):
                # across the Z joint from the nozzle's body: the toolhead rides with the nozzle, so the bed comes no
                # closer than nozzle contact (the motion verifier's toolhead margin judges what is left)
                lim = approach["working_end"] + (1.0 if approach["side"] == 1 else -1.0) * max(approach["gap_at_working_end_mm"], 0.0)
                if approach["side"] == 1:
                    hi_q = min(hi_q, lim)
                else:
                    lo_q = max(lo_q, lim)
            rng_.append((lo_q, hi_q))
        if not js_generic:
            sw_lo, sw_hi = lo_b.copy(), hi_b.copy()
            for (j, s), (lo_q, hi_q) in zip(js, rng_):
                ax = np.array(j.axis, dtype=float)
                ax /= np.linalg.norm(ax)
                t0, t1 = s * lo_q * ax, s * hi_q * ax
                sw_lo = sw_lo + np.minimum(np.minimum(t0, t1), 0.0)
                sw_hi = sw_hi + np.maximum(np.maximum(t0, t1), 0.0)
            if np.any(lo_a - sw_hi > threshold) or np.any(sw_lo - hi_a > threshold):
                continue
        counts["boxes_within_threshold"] += 1
        why = skip(a, b) if skip else None
        if why:
            counts["designed_contacts_skipped"][why] = counts["designed_contacts_skipped"].get(why, 0) + 1
            continue
        # ---- closest approach over the travel
        if not js:
            d0 = fdist(a, b, None)
            if d0 > threshold + 0.1:
                continue
            cands = [({}, None)]
        elif js_generic:
            cands = _generic_poses(design, ca, cb, js, rng_, objs, threshold)
            if not cands:
                continue
        else:
            axes = []
            for j, s in js:
                ax = np.array(j.axis, dtype=float)
                axes.append(s * ax / np.linalg.norm(ax))

            def tr(qv):
                return sum(qi * ax for qi, ax in zip(qv, axes))

            grids = [np.unique(np.concatenate([np.linspace(lo_q, hi_q, GRID), [min(max(0.0, lo_q), hi_q)]])) for lo_q, hi_q in rng_]
            # only the part of each joint's travel where the boxes can be within the threshold at all
            best = []
            for qv in itertools.product(*grids):
                t = tr(qv)
                if np.any(lo_a - (hi_b + t) > threshold) or np.any((lo_b + t) - hi_a > threshold):
                    continue
                best.append((fdist(a, b, t), qv))
            if not best:
                # the boxes come within the threshold only between grid points: start from the box-distance minimum
                qv0 = []
                for (j, s), (lo_q, hi_q), ax in zip(js, rng_, axes):
                    k = int(np.argmax(np.abs(ax)))
                    want = ((lo_a[k] + hi_a[k]) / 2 - (lo_b[k] + hi_b[k]) / 2) / ax[k]
                    qv0.append(float(np.clip(want, lo_q, hi_q)))
                best.append((fdist(a, b, tr(qv0)), tuple(qv0)))
            best.sort(key=lambda x: x[0])
            d_best, q_best = best[0]
            # refine by golden-section search along each joint in turn
            q_best = list(q_best)
            for _ in range(2):
                for k, (lo_q, hi_q) in enumerate(rng_):
                    step = (hi_q - lo_q) / (GRID - 1) if hi_q > lo_q else 0.0
                    lo_s, hi_s = max(lo_q, q_best[k] - step), min(hi_q, q_best[k] + step)
                    if hi_s - lo_s < 1e-6:
                        continue
                    gr = (math.sqrt(5) - 1) / 2
                    c_, d_ = hi_s - gr * (hi_s - lo_s), lo_s + gr * (hi_s - lo_s)

                    def f(x):
                        qq = list(q_best)
                        qq[k] = x
                        return fdist(a, b, tr(qq))
                    fc, fd = f(c_), f(d_)
                    for _i in range(18):
                        if fc < fd:
                            hi_s, d_, fd = d_, c_, fc
                            c_ = hi_s - gr * (hi_s - lo_s)
                            fc = f(c_)
                        else:
                            lo_s, c_, fc = c_, d_, fd
                            d_ = lo_s + gr * (hi_s - lo_s)
                            fd = f(d_)
                    x = (lo_s + hi_s) / 2
                    fx = f(x)
                    for xe in (lo_q, hi_q):          # a flat stretch: prefer the travel's end, where it is exact
                        if abs(x - xe) < 0.05 * max(hi_q - lo_q, 1e-9):
                            fe = f(xe)
                            if fe <= fx + 1e-6:
                                x, fx = xe, fe
                    if fx <= d_best + 1e-9:
                        d_best, q_best[k] = fx, x
            if d_best > threshold + 0.1:
                continue
            cands = [({j.name: float(qi) for (j, s), qi in zip(js, q_best)}, tr(q_best))]
            # the ends of the travel where the pair is still close: the as-built travel direction acts there most
            for qv in itertools.product(*[(lo_q, hi_q) for lo_q, hi_q in rng_]):
                if all(abs(x - y) < 1e-6 for x, y in zip(qv, q_best)):
                    continue
                t = tr(qv)
                if np.any(lo_a - (hi_b + t) > threshold) or np.any((lo_b + t) - hi_a > threshold):
                    continue
                if fdist(a, b, t) <= threshold + 0.1:
                    cands.append(({j.name: float(qi) for (j, s), qi in zip(js, qv)}, t))
        # ---- exact gap and closest points at each candidate pose
        rows = []
        for q, t in cands:
            T = None
            sb = cb.shape
            if q:
                T = forward_kinematics(design, q)
                rel = np.linalg.inv(T[ca.body]) @ T[cb.body]
                sb = cb.shape.moved(location_from_matrix(rel))
            counts["measured_exactly"] += 1
            try:
                ex = _exact(ca.shape, sb)
            except Exception:
                ex = None
            if ex is None:
                continue
            g, p_a, p_b = ex
            # points at the HOME pose of each part (A's frame is its home frame; B's point is moved back)
            p_b_home = p_b if T is None else (np.linalg.inv(rel) @ np.array([*p_b, 1.0]))[:3]
            rows.append({"gap": g, "pa": p_a, "pb": p_b, "pb_home": p_b_home, "q": q})
        if not rows:
            continue
        rows.sort(key=lambda r_: r_["gap"])
        if rows[0]["gap"] <= TOUCH_MM:
            counts["touching_or_overlapping"] += 1
            continue
        if rows[0]["gap"] >= threshold:
            continue
        out.append({"a": a, "b": b, "gap": rows[0]["gap"], "poses": [r_ for r_ in rows if r_["gap"] < threshold],
                    "moving": bool(js), "joints": [j.name for j, _ in js]})
    return out, counts


def _generic_poses(design, ca, cb, js, rng_, objs, threshold):
    """Hinged chains: sample the joints between the two bodies on a grid and keep the closest pose."""
    import fcl

    req = fcl.DistanceRequest(enable_nearest_points=False)
    best = None
    grids = [np.unique(np.concatenate([np.linspace(lo_q, hi_q, 2 * GRID - 1), [min(max(0.0, lo_q), hi_q)]])) for lo_q, hi_q in rng_]
    for qv in itertools.product(*grids):
        q = {j.name: float(x) for (j, s), x in zip(js, qv)}
        T = forward_kinematics(design, q)
        rel = np.linalg.inv(T[ca.body]) @ T[cb.body]
        objs[ca.name].setTransform(fcl.Transform())
        objs[cb.name].setTransform(fcl.Transform(rel[:3, :3].copy(), rel[:3, 3].copy()))
        d = float(fcl.distance(objs[ca.name], objs[cb.name], req, fcl.DistanceResult()))
        if best is None or d < best[0]:
            best = (d, q)
    if best is None or best[0] > threshold + 0.1:
        return []
    return [(best[1], None)]


def clearance_check(design: Design, B: Build, r: VerifierResult, shaft_pairs=()) -> dict:
    """Run the check, add its findings to r, return its metrics. `shaft_pairs`: pairs the fit check judges."""
    man = design.manufacturing or {}
    threshold = float(man.get("clearance_check_mm", THRESHOLD_MM))
    comps = {c.name: c for c in design.components}
    fast = {f.name for f in design.fasteners}
    stacks = screw_stacks(design)
    guides = guide_partners(design)
    shaft = {frozenset(p) for p in shaft_pairs}
    approach = None
    try:
        from ..verifiers.motion import nozzle_approach

        approach = nozzle_approach(design)
    except Exception:
        pass
    noz = None
    try:
        from .toolhead import nozzle_part

        noz = nozzle_part(design)
    except Exception:
        pass
    by_child = {j.child: j for j in design.joints}

    def under(body, anc):
        seen = set()
        while body not in seen:
            if body == anc:
                return True
            seen.add(body)
            if body not in by_child:
                return False
            body = by_child[body].parent
        return False

    pr = design.printer or {}
    jz = next((j for j in design.joints if j.name == pr.get("z")), None)
    tool_body = design.tool_point[0] if design.tool_point else None

    bed = pr.get("bed")
    toolhead_vs_bed: list = []
    # what is fixed to a guide block or nut is located on the rail or screw by that guide, not by the stack-up
    by_guide = set()
    for gp in guides:
        for g, partner in (tuple(gp), tuple(gp)[::-1]):
            fixed = {x for k in design.joins if g in k for x in k if x != g}
            for sname, held in stacks.items():
                if g in held:
                    fixed |= set(held) | {sname}
            for x in fixed - {g, partner}:
                by_guide.add(frozenset((x, partner)))
    axis_of = {f.name: np.abs(np.array(f.axis, dtype=float) / np.linalg.norm(f.axis)) for f in design.fasteners}

    def _sunk(screw, other):
        (lo_s, hi_s), (lo_o, hi_o) = _bb(comps[screw].shape), _bb(comps[other].shape)
        side = axis_of[screw] < 0.5                    # the directions across the screw
        return bool(np.all(lo_s[side] >= lo_o[side] - 1e-6) and np.all(hi_s[side] <= hi_o[side] + 1e-6)
                    and np.all(hi_s >= lo_o - 1e-6) and np.all(lo_s <= hi_o + 1e-6)
                    and float((np.minimum(hi_s, hi_o) - np.maximum(lo_s, lo_o))[~side].max()) > 0.3)

    sign_of = {f.name: np.array(f.axis, dtype=float) / np.linalg.norm(f.axis) for f in design.fasteners}     # towards the head
    _seat_cache: dict = {}

    def _seated(o, p_):
        key_ = frozenset((o, p_))
        if key_ in design.joins:
            return True
        if key_ not in _seat_cache:
            try:
                _seat_cache[key_] = bool(comps[o].shape.distance_to(comps[p_].shape) <= 0.05)
            except Exception:
                _seat_cache[key_] = False
        return _seat_cache[key_]

    def _under_cover(screw, other):
        """A screw whose head is let into a counterbore of a part P of its own stack, with `other` seated on P over that
        counterbore: the head sits on P's counterbore floor, `other` on P's face, so the gap between head and cover is
        the depth of P's counterbore less the head's height, a feature of P alone, not a clearance between two
        separately located parts. Needs all of: the screw sunk in P (head inside P's outline and in its thickness);
        `other` touching or joined to P; `other` beyond the head end of the screw; the whole screw inside `other`'s
        outline seen along the screw (the cover lies over the head). A screw passing beside a part, or one whose head
        stands proud, is none of this."""
        ax = sign_of[screw]
        k = int(np.argmax(np.abs(ax)))
        if abs(ax[k]) < 0.999:
            return False
        (lo_s, hi_s), (lo_o, hi_o) = _bb(comps[screw].shape), _bb(comps[other].shape)
        side = np.arange(3) != k
        if not (np.all(lo_s[side] >= lo_o[side] - 1e-6) and np.all(hi_s[side] <= hi_o[side] + 1e-6)):
            return False
        head_end = hi_s[k] if ax[k] > 0 else lo_s[k]
        beyond = (lo_o[k] >= head_end - 1e-6) if ax[k] > 0 else (hi_o[k] <= head_end + 1e-6)
        if not beyond:
            return False
        for p_ in stacks.get(screw, ()):
            if p_ == other or p_ in fast or p_ not in comps:
                continue
            lo_p, hi_p = _bb(comps[p_].shape)
            face = hi_p[k] if ax[k] > 0 else lo_p[k]
            recessed = (head_end <= face + 1e-6) if ax[k] > 0 else (head_end >= face - 1e-6)
            if recessed and _sunk(screw, p_) and _seated(other, p_):
                return True
        return False

    # what is let into or stuck onto the bed plate: its screws (heads in counterbores), heater pad, sensors
    bed_stack = set()
    if bed in comps:
        bed_stack = {s for s, held in stacks.items() if bed in held} | {x for k in design.joins if bed in k for x in k if x != bed}
    striker_pairs = set()
    for e in design.endstops:
        sw = comps.get(e.get("switch"))
        if sw is None:
            continue
        j = next((x for x in design.joints if x.name == e.get("joint")), None)
        if j is None:
            continue
        for c in design.components:      # whatever on the other side of that joint comes to the switch
            if under(c.body, j.child) != under(sw.body, j.child):
                striker_pairs.add(frozenset((sw.name, c.name)))

    def skip(a, b):
        key = frozenset((a, b))
        if key in design.joins:
            return "declared join"
        if key in design.allowed_overlaps:
            return "allowed overlap (thread or press fit)"
        for s, o in ((a, b), (b, a)):
            if s in fast and o in stacks.get(s, ()):
                return "a screw and a part of its stack"
        if key in guides:
            return "a guide and what it runs on"
        for s, o in ((a, b), (b, a)):
            # a screw in a guide block or nut is located on the rail or screw by that guide, not by the stack-up
            if s in fast and any(frozenset((t, o)) in guides for t in (comps[s].meta.get("threads_into") or [])):
                return "a screw in a guide, against what the guide runs on"
        if key in by_guide:
            return "a part fixed to a guide or nut, against what that guide runs on"
        for s, o in ((a, b), (b, a)):
            if s in fast and _sunk(s, o):
                return "a screw let into the part (head in its counterbore)"
        for s, o in ((a, b), (b, a)):
            if s in fast and o not in fast and _under_cover(s, o):
                return "a screw head recessed in a counterbore, under a part seated on that face"
        if key in striker_pairs:
            return "an endstop switch and its striker (endstop window, subsystems verifier)"
        if noz in (a, b) and bed_stack and (a in bed_stack or b in bed_stack):
            return "the nozzle over a screw or pad recessed in the bed (the nozzle meets the bed surface first)"
        if key in shaft:
            return "a shaft in its bore (fit check)"
        if tool_body is not None and bed in (a, b) and tool_body in (comps[a].body, comps[b].body) \
                and comps[a].body != comps[b].body:
            # a toolhead part over the bed plate: the nozzle approach. The nozzle part meets the bed by declaration;
            # every other toolhead part is judged by its toolhead margin (motion verifier, with declared over-travel)
            other = a if b == bed else b
            if other != noz:
                toolhead_vs_bed.append(other)
            return "toolhead part over the bed (nozzle approach: toolhead margin)"
        return None

    pairs, counts = near_pairs(design, threshold, skip)
    S = Scatter(design, B)
    S.stacks = stacks
    rows, not_eval, below_min = [], [], []
    # height error between the nozzle tip and the bed under it, per build: what Z homing removes
    rezero, zdir, rezeroed = None, None, False
    if jz is not None and noz is not None and bed in comps and noz in B.A and bed in B.A and \
            (any(e.get("joint") == jz.name for e in design.endstops) or any(x.kind == "z_offset" for x in design.adjustments)):
        zdir = np.array(jz.axis, dtype=float)
        zdir /= np.linalg.norm(zdir)
        tp = np.array(design.tool_point[1], dtype=float)
        lo_b, hi_b = _bb(comps[bed].shape)
        ref = (lo_b + hi_b) / 2 + zdir * float(np.abs(zdir) @ (hi_b - lo_b)) / 2
        rezero = ((B.at(bed, ref) - ref[None, :]) - (B.at(noz, tp) - tp[None, :])) @ zdir
    worst_sd = 0.0
    for pr_ in pairs:
        a, b = pr_["a"], pr_["b"]
        ca, cb = comps[a], comps[b]
        best = None
        for pose in pr_["poses"]:
            nvec = pose["pb"] - pose["pa"]
            g0 = float(np.linalg.norm(nvec))
            if g0 < 1e-9:
                continue
            rel = S.relative(a, pose["pa"], b, pose["pb_home"], pose["q"], nvec)
            if rel is None:
                continue
            if rezero is not None and {comps[a].body, comps[b].body} == {tool_body, comps[bed].body} and tool_body != comps[bed].body:
                # a part on the nozzle's body against a part on the bed's body (whichever of the two rides Z): homing on
                # the bed (probe, z offset) takes out the height error between nozzle and bed, which is common to both
                sgn = 1.0 if comps[b].body == comps[bed].body else -1.0          # the bed-side part is B (+) or A (-)
                rel = rel - sgn * rezero * float(zdir @ (nvec / g0))
                rezeroed = True
            sh = share_closed(g0, rel)
            if best is None or (sh["p_closed"], sh["p_closed_normal_estimate"]) > (best[1]["p_closed"], best[1]["p_closed_normal_estimate"]):
                best = (pose, sh, g0)
        pose0 = pr_["poses"][0]
        base = {"parts": [a, b], "gap_mm": round(pr_["gap"], 3),
                "at": [round(float(x), 1) for x in (pose0["pa"] + pose0["pb"]) / 2],
                **({"closest_at_pose": {k: round(v, 2) for k, v in pose0["q"].items()}, "across_joints": pr_["joints"]}
                   if pr_["moving"] else {})}
        mn, mn_basis = min_clearance_for(design, ca, cb)
        if frozenset((a, b)) in design.min_clearances:
            mn, mn_basis = float(design.min_clearances[frozenset((a, b))]), "declared for this pair: design.require_clearance"
        if pr_["gap"] < mn - 1e-9:
            below_min.append({**base, "minimum_mm": mn, "minimum_basis": mn_basis})
        if best is None:
            not_eval.append({**base, "why": "not tied to the stack-up: " + ", ".join(x for x in (a, b) if S.carrier(x) is None)})
            continue
        pose, sh, g0 = best
        worst_sd = max(worst_sd, sh["gap_sd_mm"])
        row = {**base, **sh, **S.chain_note(a, b, pose["q"]),
               **({"worst_at_pose": {k: round(v, 2) for k, v in pose["q"].items()}, "gap_there_mm": round(g0, 3)}
                  if pose is not pose0 else {})}
        row["severity"] = severity_of(sh)
        rows.append(row)
    rows.sort(key=lambda x: (-x["p_closed"], -x["p_closed_normal_estimate"], x["gap_mm"]))
    flagged = [x for x in rows if x["severity"]]
    for x in flagged[:MAX_FINDINGS]:
        a, b = x["parts"]
        where = (f" (closest with {x['closest_at_pose']})" if x.get("closest_at_pose") else "")
        if x["severity"] == "error":
            share = (f"closes in {x['p_closed']:.1%} of {x['builds']} simulated builds (standard error "
                     f"{x['p_closed_standard_error']:.1%}; limit {x['limit']:.0%})")
        elif x["p_closed"] > 0:
            share = (f"closes in {x['p_closed']:.2%} of {x['builds']} simulated builds (standard error "
                     f"{x['p_closed_standard_error']:.2%}; an error above {x['limit']:.0%})")
        else:
            share = (f"closed in none of {x['builds']} simulated builds, but its spread puts it at about "
                     f"{x['p_closed_normal_estimate']:.1g} of builds (normal estimate; an error above {x['limit']:.0%})")
        r.add(x["severity"], "clearance_closes_under_tolerance",
              f"{a} to {b}: drawn {x['gap_mm']:.2f} mm apart{where}. Built from {x['processes'][0]} and {x['processes'][1]} parts "
              f"through the joints between them the gap is {x['gap_mm']:.2f} +/-{x['gap_sd_mm']:.2f} mm (one standard deviation) "
              f"and {share}.", **{k: v for k, v in x.items() if k != "severity"},
              hint=f"Open the gap to at least {max(3.3 * x['gap_sd_mm'], min_clearance_for(design, comps[a], comps[b])[0]):.1f} mm "
                   f"(3.3 standard deviations), locate both parts from one part, or shorten the chain of joints between them.")
    if len(flagged) > MAX_FINDINGS:
        r.add("warning", "clearance_findings_truncated",
              f"{len(flagged) - MAX_FINDINGS} more pair(s) close under tolerance; they are listed in the metrics "
              f"(tolerance.clearances.pairs).", pairs=[x["parts"] for x in flagged[MAX_FINDINGS:]])
    for x in sorted(below_min, key=lambda y: y["gap_mm"])[:MAX_FINDINGS]:
        a, b = x["parts"]
        r.add("warning", "clearance_below_minimum",
              f"{a} to {b}: designed clearance {x['gap_mm']:.2f} mm between two parts that do not mate, below the "
              f"{x['minimum_mm']:g} mm minimum ({x['minimum_basis']})."
              + (f" Closest with {x['closest_at_pose']}." if x.get("closest_at_pose") else ""), **x,
              hint=f"Draw at least {x['minimum_mm']:g} mm between non-mating parts, make them a declared contact "
                   f"(design.join) if they are meant to touch, or state the gap you accept with design.require_clearance.")
    if len(below_min) > MAX_FINDINGS:
        r.add("warning", "clearance_findings_truncated",
              f"{len(below_min) - MAX_FINDINGS} more pair(s) are drawn below the minimum clearance; see the metrics "
              f"(tolerance.clearances.below_minimum).", pairs=[x["parts"] for x in below_min[MAX_FINDINGS:]])
    if not_eval:
        r.add("warning", "clearance_not_evaluated",
              f"{len(not_eval)} pair(s) of parts are drawn less than {threshold:g} mm apart but could not be put through the "
              f"stack-up (a part that nothing ties to the base): " + "; ".join(f"{x['parts'][0]} / {x['parts'][1]} "
              f"({x['gap_mm']:.2f} mm)" for x in not_eval[:6]) + ". Not evaluated is not a pass.", pairs=not_eval[:40])
    tvb = sorted(set(toolhead_vs_bed))
    if tvb and approach is None:
        r.add("info", "toolhead_over_bed_not_judged_here",
              f"{len(tvb)} toolhead part(s) come within {threshold:g} mm of the bed plate ({', '.join(tvb[:6])}). Their height above "
              f"the nozzle tip is judged by the toolhead margin, which the motion verifier applies only when the Z joint "
              f"declares over-travel past the nozzle plane (Joint.overtravel); this design declares none, so it was NOT judged.",
              parts=tvb)
    if worst_sd * 3.0 > threshold:
        r.add("info", "clearance_search_threshold",
              f"Pairs drawn up to {threshold:g} mm apart were examined, but one of them scatters by {worst_sd:.2f} mm (one "
              f"standard deviation): gaps wider than {threshold:g} mm on a chain like that can also close and were NOT "
              f"examined. Raise design.manufacturing['clearance_check_mm'] to look further.", gap_sd_mm=round(worst_sd, 3))
    return {"threshold_mm": threshold, "p_closed_error_above": P_CLOSE_ERROR,
            "minimum_clearance_mm_by_process": {**MIN_CLEARANCE_MM, **(man.get("min_clearance_mm") if isinstance(man.get("min_clearance_mm"), dict) else {})}
            if not isinstance(man.get("min_clearance_mm"), (int, float)) else float(man["min_clearance_mm"]),
            "search": counts, "pairs_examined": len(pairs), "pairs_closing": {"error": sum(x["severity"] == "error" for x in rows),
                                                                             "warning": sum(x["severity"] == "warning" for x in rows)},
            "pairs": [{k: v for k, v in x.items()} for x in rows[:60]],
            "below_minimum": below_min[:60], "not_evaluated": not_eval[:40],
            **({"toolhead_parts_over_bed": {"parts": tvb, "judged_by": "toolhead margin (motion verifier)" if approach else
                                            "NOT judged: no Z over-travel declared"}} if tvb else {}),
            **({"z_homing_takes_out_nozzle_to_bed_height": True} if rezeroed else {}),
            "largest_gap_sd_mm": round(worst_sd, 3),
            "method": "drawn gap + relative as-built displacement of the two closest points along the gap direction "
                      "(stack-up builds, as-built rail directions over the travel) + both surfaces' own feature error"}
