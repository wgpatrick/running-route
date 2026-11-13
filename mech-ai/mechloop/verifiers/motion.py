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
                 seed: int = 0) -> list[dict[str, float]]:
    joints = [j for j in design.joints if j.range[0] != j.range[1]]
    poses: list[dict[str, float]] = [{}]
    for j in joints:
        for q in np.linspace(j.range[0], j.range[1], per_joint):
            poses.append({j.name: float(q)})
    corners = list(itertools.product(*[(j.range[0], j.range[1]) for j in joints])) if len(joints) > 1 else []
    rng = np.random.default_rng(seed)
    if len(corners) > max_corners:
        corners = [corners[i] for i in rng.choice(len(corners), max_corners, replace=False)]
    for c in corners:
        poses.append({j.name: float(q) for j, q in zip(joints, c)})
    if len(joints) > 1:
        for _ in range(n_random):
            poses.append({j.name: float(rng.uniform(*j.range)) for j in joints})
    return poses


def colliding_pairs(design: Design, q: dict[str, float], skip_same_body: bool = True):
    """Mesh broad phase at pose q. Returns (pairs, body transforms)."""
    T = forward_kinematics(design, q)
    cm = trimesh.collision.CollisionManager()
    body_of = {}
    for c in design.components:
        cm.add_object(c.name, to_trimesh(c.shape), transform=T[c.body])
        body_of[c.name] = c.body
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
        poses = sample_poses(design, per_joint)
        worst: dict[tuple, dict] = {}
        exact_checks = 0
        cache: dict = {}
        for q in poses:
            pairs, T = colliding_pairs(design, q)
            for a, b in pairs:
                # relative transform fully determines the overlap -> cache on it
                rel = np.linalg.inv(T[comps[a].body]) @ T[comps[b].body]
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
                            w = T[comps[a].body] @ np.array([*where, 1.0])
                            where = tuple(np.round(w[:3], 1).tolist())
                        first = worst.get((a, b), {}).get("first_pose", q)
                        worst[(a, b)] = {"volume_mm3": round(vol, 2), "pose": q, "at": where,
                                         "first_pose": first}
        for (a, b), w in sorted(worst.items(), key=lambda kv: -kv[1]["volume_mm3"]):
            pose = {k: round(v, 2) for k, v in w["pose"].items()} or "home"
            r.add("error", "motion_collision",
                  f"{a} hits {b} during travel: {w['volume_mm3']} mm^3 overlap at pose {pose}, near {w['at']}.",
                  parts=[a, b], **{k: v for k, v in w.items() if k != "first_pose"},
                  hint="Shorten the joint range, move the part out of the swept path, or add clearance.")
        r.metrics = {"joints": len(design.joints), "poses_checked": len(poses),
                     "exact_overlap_checks": exact_checks}
        try:
            r.metrics["drives"] = _dynamics(design, r)
        except Exception as e:  # dynamics is advisory if the model cannot be built
            r.add("warning", "dynamics_failed", f"MuJoCo dynamics check failed: {type(e).__name__}: {e}")
    return r


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
        req, hld = need[j.name] * k, hold[j.name] * k
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
            if margin < 1.0:
                r.add("error", "drive_undersized",
                      f"Joint {j.name} needs {req:.1f} {unit} (holding {hld:.1f}) but the drive gives "
                      f"{j.max_effort:.1f} {unit}.",
                      joint=j.name, required=round(req, 2), available=j.max_effort,
                      hint="Lower acceleration, reduce moving mass, change the transmission ratio or pick a stronger motor.")
            elif margin < 1.5:
                r.add("warning", "drive_low_margin",
                      f"Joint {j.name} drive margin is only {margin:.2f}x (friction is not modelled).",
                      joint=j.name, margin=round(margin, 2))
        out[j.name] = entry
    return out
