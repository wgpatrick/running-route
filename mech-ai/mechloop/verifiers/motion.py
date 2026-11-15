"""Motion checks.

1. Kinematic sweep: move every joint through its travel (singly, and at the
   corners of the joint space) and look for collisions between bodies, using a
   fast mesh broad phase confirmed by exact B-rep overlap volume.
2. Dynamics (MuJoCo inverse dynamics): effort each joint drive needs to hold
   against gravity and to run a trapezoidal move at its stated speed and
   acceleration, compared with the effort available.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import trimesh

from ..geom import (body_tree, forward_kinematics, location_from_matrix, overlap_volume,
                    to_trimesh)
from ..model import Design
from ..report import VerifierResult, timed

VOL_TOL = 0.5


def sample_poses(design: Design, per_joint: int = 9, max_corners: int = 64, n_random: int = 12,
                 seed: int = 0, mechanical: bool = False) -> list[dict[str, float]]:
    """Poses to check: each joint alone over its travel, the corners of the joint space and random combinations.
    mechanical=True covers each joint's mechanical range (working range plus declared Joint.overtravel); the working
    range's own ends are then sampled too. With no over-travel declared the two are the same poses."""
    def rng_of(j):
        return tuple(j.mechanical_range) if mechanical else tuple(j.range)

    joints = [j for j in design.joints if rng_of(j)[0] != rng_of(j)[1]]
    poses: list[dict[str, float]] = [{}]
    for j in joints:
        lo, hi = rng_of(j)
        span = abs(hi - lo)
        n = int(min(41, max(per_joint, span / (10.0 if j.kind == "slide" else 7.5) + 1)))
        qs = [float(q) for q in np.linspace(lo, hi, n)]
        qs += [float(q) for q in j.range if mechanical and min(abs(q - x) for x in qs) > 1e-9]
        for q in qs:
            poses.append({j.name: q})
    corners = list(itertools.product(*[rng_of(j) for j in joints])) if len(joints) > 1 else []
    rng = np.random.default_rng(seed)
    if len(corners) > max_corners:
        corners = [corners[i] for i in rng.choice(len(corners), max_corners, replace=False)]
    for c in corners:
        poses.append({j.name: float(q) for j, q in zip(joints, c)})
    if len(joints) > 1:
        for _ in range(n_random):
            poses.append({j.name: float(rng.uniform(*rng_of(j))) for j in joints})
    return poses


def nozzle_approach(design: Design) -> dict | None:
    """A printer's declared Z over-travel towards the nozzle. It is not a motion in which the bed passes through the
    nozzle: it is allowance for where the nozzle really ends up relative to the bed in a built machine (the z-offset
    stack-up) and for a bed mesh. Returns the Z joint's name, which end of its travel that is, the bed part, the part
    that carries the nozzle tip (the one the tool point lies on), the body the nozzle rides on and the over-travel in
    mm; None when the design declares none.

    How collisions are judged in that over-travel (verify_motion):
      * bed against the part that carries the tip: not a collision, as deep as the bed has gone past the working range;
      * anything across the Z joint from a part ON THE NOZZLE'S BODY (probe, fan duct, the toolhead's screws): the
        whole toolhead rides with the nozzle in that stack-up, so the bed can come no closer to such a part than
        nozzle contact plus the part's own margin (mechloop.tolerance.toolhead.height_margin: the stack-up inside the
        toolhead between part and tip, plus the bed's flatness over the distance between them). The pair is checked
        at that depth, not at the full over-travel. A duct that hangs below the tip, or closer above it than its
        margin, is still a collision;
      * every other pair (bed against gantry or frame): checked over the full over-travel, as before."""
    pr = design.printer or {}
    j = next((x for x in design.joints if x.name == pr.get("z")), None)
    if j is None or design.tool_point is None or not pr.get("bed"):
        return None
    comps = {c.name: c for c in design.components}
    bed = comps.get(pr["bed"])
    if bed is None:
        return None
    tb, tp = design.tool_point
    from build123d import Vertex

    cand = []
    for c in design.components:
        if c.body != tb:
            continue
        try:
            cand.append((c.shape.distance_to(Vertex(*tp)), c.name))
        except Exception:
            pass
    if not cand or min(cand)[0] > 0.5:
        return None
    nozzle = min(cand)[1]
    T0 = forward_kinematics(design, {})
    out = None
    for side, q_end, ot in ((0, j.range[0], j.range[0] - j.mechanical_range[0]), (1, j.range[1], j.mechanical_range[1] - j.range[1])):
        if ot <= 1e-9:
            continue
        # is this the end at which the bed comes up to the nozzle? compare the nozzle-to-bed distance at the two ends
        def gap(q):
            T = forward_kinematics(design, {j.name: float(q)})
            p = (T[tb] @ np.array([*tp, 1.0]))[:3]
            local = (np.linalg.inv(T[bed.body]) @ np.array([*p, 1.0]))[:3]
            return float(bed.shape.distance_to(Vertex(*local)))
        other = j.range[1 - side]
        if gap(q_end) < gap(other) and gap(q_end) < 5.0:
            out = {"joint": j.name, "side": side, "working_end": float(q_end), "overtravel_mm": float(ot), "bed": bed.name,
                   "nozzle_part": nozzle, "gap_at_working_end_mm": round(gap(q_end), 3), "tool_body": tb,
                   "z_child": j.child}
    return out


_COLLIDERS: dict[int, tuple] = {}


def colliding_pairs(design: Design, q: dict[str, float], skip_same_body: bool = True):
    """Mesh broad phase at pose q. Returns (pairs, body transforms).
    The collision manager is built once per design and only re-posed."""
    T = forward_kinematics(design, q)
    key = id(design)
    sig = tuple((c.name, id(c.shape.wrapped), c.body) for c in design.components)
    if key not in _COLLIDERS or _COLLIDERS[key][1] != sig:
        cm = trimesh.collision.CollisionManager()
        for c in design.components:
            cm.add_object(c.name, to_trimesh(c.shape))
        _COLLIDERS[key] = (cm, sig, {})
    cm, _, last = _COLLIDERS[key]
    body_of = {}
    for c in design.components:
        body_of[c.name] = c.body
        Tb = T[c.body]
        if c.name not in last or last[c.name] is not Tb and not np.array_equal(last[c.name], Tb):
            cm.set_transform(c.name, Tb)
            last[c.name] = Tb
    _, names = cm.in_collision_internal(return_names=True)
    pairs = [tuple(sorted(p)) for p in names
             if not (skip_same_body and body_of[p[0]] == body_of[p[1]])]
    return sorted(set(pairs)), T


def verify_motion(design: Design, per_joint: int = 9) -> VerifierResult:
    r = VerifierResult("motion")
    if not design.joints:
        r.skipped = "design has no joints"
        return r
    with timed(r):
        try:
            body_tree(design)
        except ValueError as e:
            r.add("error", "bad_kinematic_tree", str(e))
            return r
        from .ratings import resolve_drives

        resolve_drives(design)
        for j in design.joints:
            if j.range[0] == j.range[1]:
                r.add("warning", "zero_travel", f"Joint {j.name} has zero travel range.", joint=j.name)
            if j.range[0] > 0 or j.range[1] < 0:
                r.add("warning", "home_outside_range",
                      f"Joint {j.name}: home pose (0) is outside its range {j.range}.", joint=j.name)
        comps = {c.name: c for c in design.components}
        for j in design.joints:
            if any(float(x) < 0 for x in (tuple(j.overtravel) + (0.0, 0.0))[:2]):
                r.add("error", "bad_overtravel", f"Joint {j.name}: overtravel {tuple(j.overtravel)} must be two values >= 0 "
                      f"(past the low end, past the high end of its range).", joint=j.name)
        # collisions are checked over the MECHANICAL range: the working range plus declared over-travel
        poses = sample_poses(design, per_joint, mechanical=True)
        approach = nozzle_approach(design)
        ot_m = {j.name: {"working_range": list(j.range), "mechanical_range": list(j.mechanical_range)}
                for j in design.joints if tuple(j.mechanical_range) != tuple(j.range)}
        if approach:
            ot_m[approach["joint"]]["nozzle_approach"] = (
                f"in the {approach['overtravel_mm']:g} mm past {approach['joint']}={approach['working_end']:g} the bed "
                f"({approach['bed']}) meeting the nozzle tip ({approach['nozzle_part']}) is by declaration not a collision; "
                f"parts on the nozzle's body ('{approach['tool_body']}') ride with the nozzle and are checked with the bed at "
                f"nozzle contact plus each part's toolhead margin; every other pair is checked over the whole over-travel")
        if ot_m:
            r.metrics["overtravel"] = ot_m
        worst: dict[tuple, dict] = {}
        exact_checks = 0
        cache: dict = {}
        exempted = 0.0
        tool_margin: dict = {}      # toolhead part -> its height margin above the nozzle tip (computed when first needed)
        relieved: dict = {}         # toolhead parts that were checked at nozzle contact + margin instead of the full over-travel

        def a_side(n: str) -> bool:      # which side of the Z joint a part is on
            return _under_body(design, comps[n].body, approach["z_child"])

        for q in poses:
            pairs, T = colliding_pairs(design, q)
            past = 0.0
            if approach and approach["joint"] in q:
                dq = q[approach["joint"]] - approach["working_end"]
                past = dq if approach["side"] == 1 else -dq
            for a, b in pairs:
                if past > 1e-9 and {a, b} == {approach["bed"], approach["nozzle_part"]}:
                    # the nozzle/bed approach itself. Only the tip may be met: the overlap must be no deeper, along the
                    # joint axis, than the bed has gone past the working range.
                    rel = np.linalg.inv(T[comps[a].body]) @ T[comps[b].body]
                    try:
                        common = comps[a].shape & comps[b].shape.moved(location_from_matrix(rel))
                        sols = list(common.solids()) if common is not None else []
                    except Exception:
                        sols = None
                    if sols is not None:
                        jz = next(x for x in design.joints if x.name == approach["joint"])
                        ax = np.array(jz.axis, dtype=float) / np.linalg.norm(jz.axis)
                        ax_a = np.linalg.inv(T[comps[a].body])[:3, :3] @ (T[jz.parent][:3, :3] @ ax if jz.parent in T else ax)
                        depth = 0.0
                        for so in sols:
                            bb = so.bounding_box()
                            pr_ = [np.array([x, y, z]) @ ax_a for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
                                   for z in (bb.min.Z, bb.max.Z)]
                            depth = max(depth, float(max(pr_) - min(pr_)))
                        if depth <= past + 0.05:
                            exempted = max(exempted, past)
                            continue
                # A part on the nozzle's body against something across the Z joint, in the over-travel: the toolhead
                # rides with the nozzle, so the pair is judged no deeper than nozzle contact plus the part's margin.
                Tq, qq, extra = T, q, {}
                if past > 1e-9 and a_side(a) != a_side(b) and approach["tool_body"] in (comps[a].body, comps[b].body):
                    tp_name = a if comps[a].body == approach["tool_body"] else b
                    if tp_name not in tool_margin:
                        from ..tolerance.toolhead import height_margin

                        tool_margin[tp_name] = height_margin(design, tp_name)
                    hm = tool_margin[tp_name]
                    lim = approach["gap_at_working_end_mm"] + hm["margin_mm"]
                    if past > lim:
                        sgn = 1.0 if approach["side"] == 1 else -1.0
                        qq = {**q, approach["joint"]: approach["working_end"] + sgn * lim}
                        Tq = forward_kinematics(design, qq)
                        relieved[tp_name] = hm
                    extra = {"toolhead_margin_mm": hm["margin_mm"], "checked_past_working_end_mm": round(min(past, lim), 3),
                             "toolhead_part": tp_name}
                # relative transform fully determines the overlap -> cache on it
                rel = np.linalg.inv(Tq[comps[a].body]) @ Tq[comps[b].body]
                ck = (a, b, tuple(np.round(rel.reshape(-1), 4)))
                if ck not in cache:
                    exact_checks += 1
                    sb = comps[b].shape.moved(location_from_matrix(rel))
                    cache[ck] = overlap_volume(comps[a].shape, sb)
                vol, where = cache[ck]
                allowed = design.allowed_overlaps.get(frozenset((a, b)))
                if vol > VOL_TOL and (allowed is None or vol > allowed):
                    if (a, b) not in worst or vol > worst[(a, b)]["volume_mm3"]:
                        if where is not None:
                            w = Tq[comps[a].body] @ np.array([*where, 1.0])
                            where = tuple(np.round(w[:3], 1).tolist())
                        first = worst.get((a, b), {}).get("first_pose", qq)
                        worst[(a, b)] = {"volume_mm3": round(vol, 2), "pose": qq, "at": where,
                                         "first_pose": first, **extra}
        for (a, b), w in sorted(worst.items(), key=lambda kv: -kv[1]["volume_mm3"]):
            pose = {k: round(v, 3) for k, v in w["pose"].items()} or "home"
            note, hint = "", "Shorten the joint range, move the part out of the swept path, or add clearance."
            if "toolhead_part" in w:
                note = (f" {w['toolhead_part']} rides with the nozzle: the bed was taken {w['checked_past_working_end_mm']:g} mm "
                        f"past the working range, i.e. to nozzle contact plus this part's toolhead margin "
                        f"({w['toolhead_margin_mm']:g} mm: stack-up to the nozzle tip and bed flatness), not through the whole "
                        f"over-travel.")
                hint = (f"Raise {w['toolhead_part']} so that its underside is at least {w['toolhead_margin_mm']:g} mm above the nozzle "
                        f"tip over the bed, or tie it more tightly to the nozzle (fewer, more accurate joints).")
            r.add("error", "motion_collision",
                  f"{a} hits {b} during travel: {w['volume_mm3']} mm^3 overlap at pose {pose}, near {w['at']}." + note,
                  parts=[a, b], **{k: v for k, v in w.items() if k != "first_pose"}, hint=hint)
        if approach and relieved:
            r.metrics["overtravel"][approach["joint"]]["toolhead_parts_checked_at_nozzle_contact_plus_margin"] = {
                k: {"margin_mm": v["margin_mm"], "stackup_mm": v["stackup_mm"], "bed_rise_mm": v["bed_rise_mm"],
                    **({"assumed": True} if v.get("assumed") else {})} for k, v in sorted(relieved.items())}
        if approach and (exempted > 0 or relieved):
            r.add("info", "nozzle_approach_overtravel",
                  f"Joint {approach['joint']} has {approach['overtravel_mm']:g} mm of declared over-travel past the nozzle plane: "
                  f"the bed meeting the nozzle tip there was not counted as a collision (checked to {exempted:g} mm past). "
                  + (f"{len(relieved)} part(s) on the nozzle's body ({', '.join(sorted(relieved)[:6])}) ride with the nozzle and were "
                     f"checked with the bed at nozzle contact plus their toolhead margin; " if relieved else "")
                  + "every other pair was checked over the whole over-travel. The probe's face height and trigger margin are "
                    "judged by the subsystems verifier.", joint=approach["joint"])
        _runoff(design, r)
        from .belts import verify_belts

        try:
            verify_belts(design, r, poses)
        except Exception as e:
            r.add("error", "belt_check_failed", f"Belt checks did not run: {type(e).__name__}: {e}")
        r.metrics.update({"joints": len(design.joints), "poses_checked": len(poses),
                          "exact_overlap_checks": exact_checks})
        try:
            r.metrics["drives"] = _dynamics(design, r)
        except Exception as e:
            r.add("error", "dynamics_failed", f"MuJoCo dynamics check did not run: {type(e).__name__}: {e}")
        if design.program:
            try:
                _program(design, r)
            except Exception as e:
                r.add("error", "simulation_failed", f"Motion program simulation did not run: {type(e).__name__}: {e}")
    return r


def _under_body(design: Design, body: str, ancestor: str) -> bool:
    parent = {j.child: j.parent for j in design.joints}
    seen = set()
    while body not in seen:
        if body == ancestor:
            return True
        seen.add(body)
        if body not in parent:
            return False
        body = parent[body]
    return False


def _runoff(design: Design, r: VerifierResult) -> None:
    """A guide block or nut must stay on its rail/screw over the whole travel.
    Running off the end is not a collision, so it needs its own check."""
    comps = design.components
    for j in design.joints:
        if j.kind != "slide":
            continue
        a = np.array(j.axis, dtype=float)
        a /= np.linalg.norm(a)
        for blk in [c for c in comps if c.meta.get("guides") == j.name]:
            other_body = j.parent if blk.body == j.child else j.child
            # its partner: the part on the other side of the joint that it wraps or touches
            best, best_d = None, 1.0
            for c in comps:
                if c.body != other_body:
                    continue
                try:
                    dist = blk.shape.distance_to(c.shape)
                except Exception:
                    continue
                if dist < best_d:
                    best, best_d = c, dist
            if best is None:
                r.add("error", "guide_no_partner",
                      f"{blk.name} guides joint {j.name} but is not on (within 1 mm of) any rail or screw on "
                      f"body '{other_body}'.", part=blk.name, joint=j.name)
                continue

            def extent(s):
                bb = s.bounding_box()
                corners = np.array([[x, y, z] for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
                                    for z in (bb.min.Z, bb.max.Z)])
                pr = corners @ a
                return float(pr.min()), float(pr.max())

            b_lo, b_hi = extent(blk.shape)
            p_lo, p_hi = extent(best.shape)
            sign = 1.0 if blk.body == j.child else -1.0
            for q in j.mechanical_range:
                lo, hi = b_lo + sign * q, b_hi + sign * q
                over = max(p_lo - lo, hi - p_hi)
                if over > 0.5:
                    r.add("error", "guide_runoff",
                          f"{blk.name} runs {over:.1f} mm off the end of {best.name} at {j.name}={q:g}.",
                          part=blk.name, partner=best.name, joint=j.name, overhang_mm=round(over, 1),
                          hint="Use a longer rail/screw, shift it, or shorten the travel.")


def _program(design: Design, r: VerifierResult) -> None:
    from ..sim import program_collisions, simulate

    for step in design.program:
        for k, v in step["to"].items():
            j = next((x for x in design.joints if x.name == k), None)
            if j is None:
                r.add("error", "program_unknown_joint", f"Motion program refers to unknown joint '{k}'.")
                return
            if not (j.range[0] - 1e-9 <= v <= j.range[1] + 1e-9):
                r.add("error", "program_out_of_range",
                      f"Motion program sends joint {k} to {v}, outside its range {j.range}.", joint=k, target=v)
                return
    sim = simulate(design, design.program)
    r.artifacts_sim = sim
    tol = design.tracking_tolerance
    m = {"duration_s": round(sim["duration_s"], 2),
         "max_tracking_error": {k: round(v, 4) for k, v in sim["max_error"].items()},
         "final_error": {k: round(v, 4) for k, v in sim["final_error"].items()},
         "peak_effort": {k: round(v, 2) for k, v in sim["peak_effort"].items()},
         "time_at_force_limit": {k: f"{v:.1%}" for k, v in sim["saturated_fraction"].items()}}
    for k, e in sim["max_error"].items():
        if e > tol:
            r.add("error", "tracking_error",
                  f"Simulated joint {k} falls {e:.2f} from its commanded position (tolerance {tol}); "
                  f"the drive is at its force limit {sim['saturated_fraction'][k]:.0%} of the time.",
                  joint=k, max_error=round(e, 3),
                  hint="Lower acceleration/speed in the program or joint limits, reduce moving mass, or use a stronger drive.")
    hits = program_collisions(design, sim)
    for h in hits:
        r.add("error", "program_collision",
              f"{h['parts'][0]} hits {h['parts'][1]} at t={h['time_s']} s of the motion program, pose {h['pose']}.", **h)
    m["collisions"] = len(hits)
    r.metrics["program"] = m


# ---------------------------------------------------------------- dynamics
def body_inertials(design: Design) -> dict[str, dict]:
    """Mass (kg), COM (m) and inertia about COM (kg m^2) of each body in the home pose."""
    out = {}
    for body, members in design.bodies().items():
        m_tot, first, parts = 0.0, np.zeros(3), []
        for c in members:
            tm = to_trimesh(c.shape)
            tm = trimesh.Trimesh(tm.vertices * 1e-3, tm.faces, process=True)
            mp = tm.mass_properties
            vol = abs(float(mp["volume"])) or 1e-12
            m = c.mass()
            com = np.array(mp["center_mass"], dtype=float)
            I = np.array(mp["inertia"], dtype=float) * (m / vol)  # unit density -> scaled
            if not tm.is_watertight or not np.all(np.isfinite(I)) or np.linalg.eigvalsh(I).min() <= 0:
                ext = tm.extents
                com = tm.bounds.mean(axis=0)
                I = np.diag([(ext[1] ** 2 + ext[2] ** 2), (ext[0] ** 2 + ext[2] ** 2),
                             (ext[0] ** 2 + ext[1] ** 2)]) * m / 12.0
            parts.append((m, com, I))
            m_tot += m
            first += m * com
        com_b = first / m_tot
        I_b = np.zeros((3, 3))
        for m, com, I in parts:
            d = com - com_b
            I_b += I + m * (np.dot(d, d) * np.eye(3) - np.outer(d, d))
        out[body] = {"mass": m_tot, "com": com_b, "inertia": I_b}
    return out


def build_mujoco(design: Design, with_meshes: bool = False):
    """MuJoCo model of the design (SI units). Collisions are off: the exact
    kinematic sweep handles those; MuJoCo is used for dynamics."""
    import mujoco

    spec = mujoco.MjSpec()
    spec.option.gravity = np.array(design.gravity) * 1e-3
    spec.compiler.degree = False
    by_child = body_tree(design)
    inert = body_inertials(design)
    handles = {"world": spec.worldbody}
    children: dict[str, list[str]] = {}
    for child, j in by_child.items():
        children.setdefault(j.parent, []).append(child)

    def add(body: str):
        for ch in children.get(body, []):
            j = by_child[ch]
            b = handles[body].add_body(name=ch)
            ine = inert[ch]
            b.explicitinertial = True
            b.mass = float(ine["mass"])
            b.ipos = ine["com"]
            I = ine["inertia"]
            b.fullinertia = [I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2]]
            a = np.array(j.axis, dtype=float)
            a /= np.linalg.norm(a)
            if j.kind == "slide":
                jj = b.add_joint(name=j.name, type=mujoco.mjtJoint.mjJNT_SLIDE, axis=a)
                jj.range = np.array(j.range) * 1e-3
            else:
                jj = b.add_joint(name=j.name, type=mujoco.mjtJoint.mjJNT_HINGE, axis=a,
                                 pos=np.array(j.origin) * 1e-3)
                jj.range = np.radians(j.range)
            handles[ch] = b
            add(ch)

    add("world")
    if with_meshes:
        for c in design.components:
            tm = to_trimesh(c.shape)
            spec.add_mesh(name=c.name, uservert=(tm.vertices * 1e-3).reshape(-1).tolist(),
                          userface=tm.faces.reshape(-1).tolist())
            g = handles[c.body].add_geom(name=c.name, type=mujoco.mjtGeom.mjGEOM_MESH, meshname=c.name)
            g.contype = 0
            g.conaffinity = 0
    return spec.compile()


def _trapezoid(q0: float, q1: float, vmax: float, amax: float, dt: float):
    d = q1 - q0
    s = math.copysign(1.0, d) if d else 1.0
    D = abs(d)
    ta = vmax / amax
    if amax * ta * ta > D:  # triangular
        ta = math.sqrt(D / amax)
        tc = 0.0
    else:
        tc = (D - amax * ta * ta) / vmax
    T = 2 * ta + tc
    ts = np.arange(0.0, T + dt, dt)
    q, v, a = np.zeros_like(ts), np.zeros_like(ts), np.zeros_like(ts)
    vp = amax * ta
    for i, t in enumerate(ts):
        if t < ta:
            a[i], v[i], q[i] = amax, amax * t, 0.5 * amax * t * t
        elif t < ta + tc:
            a[i], v[i], q[i] = 0.0, vp, 0.5 * amax * ta * ta + vp * (t - ta)
        elif t < T:
            td = t - ta - tc
            a[i], v[i] = -amax, vp - amax * td
            q[i] = 0.5 * amax * ta * ta + vp * tc + vp * td - 0.5 * amax * td * td
        else:
            q[i] = D
    return ts, q0 + s * q, s * v, s * a


def _dynamics(design: Design, r: VerifierResult) -> dict:
    import mujoco

    model = build_mujoco(design)
    data = mujoco.MjData(model)
    joints = design.joints
    idx = {j.name: model.joint(j.name).dofadr[0] for j in joints}
    qadr = {j.name: model.joint(j.name).qposadr[0] for j in joints}
    scale = {j.name: (1e-3 if j.kind == "slide" else math.pi / 180) for j in joints}
    need = {j.name: 0.0 for j in joints}
    hold = {j.name: 0.0 for j in joints}

    def inverse(q: dict, v: dict, a: dict):
        data.qpos[:] = 0
        data.qvel[:] = 0
        data.qacc[:] = 0
        for n in q:
            data.qpos[qadr[n]] = q[n] * scale[n]
        for n in v:
            data.qvel[idx[n]] = v[n] * scale[n]
        for n in a:
            data.qacc[idx[n]] = a[n] * scale[n]
        mujoco.mj_inverse(model, data)
        return {n: float(data.qfrc_inverse[idx[n]]) for n in idx}

    # static holding effort over sampled poses
    for q in sample_poses(design, per_joint=5, n_random=8):
        f = inverse(q, {}, {})
        for n in f:
            hold[n] = max(hold[n], abs(f[n]))
            need[n] = max(need[n], abs(f[n]))
    # moves: each joint lo->hi and hi->lo with the others parked at their extremes
    move_time = {}
    for j in joints:
        if not (j.max_speed and j.max_accel) or j.range[0] == j.range[1]:
            continue
        others = [o for o in joints if o is not j and o.range[0] != o.range[1]]
        parks = [dict(zip([o.name for o in others], c))
                 for c in itertools.islice(itertools.product(*[o.range for o in others]), 8)] or [{}]
        for a0, a1 in (j.range, j.range[::-1]):
            ts, qs, vs, acs = _trapezoid(a0, a1, j.max_speed, j.max_accel, 0.005)
            move_time[j.name] = round(float(ts[-1]), 3)
            for park in parks:
                for qq, vv, aa in zip(qs[::2], vs[::2], acs[::2]):
                    f = inverse({**park, j.name: qq}, {j.name: vv}, {j.name: aa})
                    for n in f:
                        need[n] = max(need[n], abs(f[n]))
    out = {}
    inert = body_inertials(design)
    for j in joints:
        unit = "N" if j.kind == "slide" else "N*mm"
        k = 1.0 if j.kind == "slide" else 1e3  # N*m -> N*mm
        # the motor must also accelerate its own rotor
        refl = j.reflected_inertia * (j.max_accel or 0.0) * (1e-3 if j.kind == "slide" else math.pi / 180 * 1e-6)
        req, hld = (need[j.name] + refl) * k, hold[j.name] * k
        entry = {"required": round(req, 2), "holding": round(hld, 2), "unit": unit,
                 "available": j.max_effort, "moved_mass_kg": round(inert[j.child]["mass"], 3)}
        if j.name in move_time:
            entry["full_travel_s"] = move_time[j.name]
        if j.max_effort is None:
            r.add("warning", "drive_unrated",
                  f"Joint {j.name} needs up to {req:.1f} {unit} but no max_effort is declared.",
                  joint=j.name, required=req)
        else:
            margin = j.max_effort / req if req > 1e-9 else float("inf")
            entry["margin"] = round(margin, 2) if math.isfinite(margin) else "inf"
            if margin < j.min_drive_margin:
                r.add("error", "drive_undersized",
                      f"Joint {j.name} needs {req:.1f} {unit} (holding {hld:.1f}) but the drive gives "
                      f"{j.max_effort:.1f} {unit}: margin {margin:.2f}x < required {j.min_drive_margin}x.",
                      joint=j.name, required=round(req, 2), available=j.max_effort,
                      hint="Lower acceleration, reduce moving mass, change the transmission ratio or pick a stronger motor.")
        out[j.name] = entry
    return out
