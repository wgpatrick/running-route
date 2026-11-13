"""Forward dynamics: run a motion program in MuJoCo and see whether the
machine follows it with the force its drives actually have.

Each joint is servoed (PD + inertia feed-forward) with its force clipped to the
drive's available effort, so an undersized drive shows up as tracking error.
This is an idealised closed-loop servo: it does not model stepper step loss,
belt stretch or structural flex.
"""
from __future__ import annotations

import math

import numpy as np

from .geom import location_from_matrix, overlap_volume
from .model import Design


def plan(design: Design, program: list[dict], dt: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[str]]:
    """Coordinated trapezoidal moves through the program's waypoints.
    Returns time-sampled q, v, a (columns = joints, user units) and joint names."""
    joints = design.joints
    names = [j.name for j in joints]
    cur = np.zeros(len(joints))
    Q, V, A = [cur.copy()], [np.zeros(len(joints))], [np.zeros(len(joints))]
    for step in program:
        tgt = cur.copy()
        for k, v in step["to"].items():
            tgt[names.index(k)] = v
        delta = tgt - cur
        dist = float(np.linalg.norm(delta))
        if dist < 1e-9:
            n = int(step.get("dwell", 0.1) / dt)
            Q += [cur.copy()] * n; V += [np.zeros(len(joints))] * n; A += [np.zeros(len(joints))] * n
            continue
        u = delta / dist
        vmax = min([(j.max_speed or 1e9) / abs(u[i]) for i, j in enumerate(joints) if abs(u[i]) > 1e-9]
                   + [step.get("speed", 1e9)])
        amax = min((j.max_accel or 1e9) / abs(u[i]) for i, j in enumerate(joints) if abs(u[i]) > 1e-9)
        if not math.isfinite(vmax) or not math.isfinite(amax) or vmax > 1e8 or amax > 1e8:
            raise ValueError("joints in a motion program need max_speed and max_accel")
        ta = vmax / amax
        if amax * ta * ta > dist:
            ta, tc = math.sqrt(dist / amax), 0.0
        else:
            tc = (dist - amax * ta * ta) / vmax
        vp = amax * ta
        T = 2 * ta + tc
        for t in np.arange(dt, T + dt, dt):
            if t < ta:
                s, sd, sdd = 0.5 * amax * t * t, amax * t, amax
            elif t < ta + tc:
                s, sd, sdd = 0.5 * amax * ta * ta + vp * (t - ta), vp, 0.0
            elif t < T:
                td = t - ta - tc
                s, sd, sdd = 0.5 * amax * ta * ta + vp * tc + vp * td - 0.5 * amax * td * td, vp - amax * td, -amax
            else:
                s, sd, sdd = dist, 0.0, 0.0
            Q.append(cur + u * s); V.append(u * sd); A.append(u * sdd)
        cur = tgt
    n = int(0.15 / dt)  # settle
    Q += [cur.copy()] * n; V += [np.zeros(len(joints))] * n; A += [np.zeros(len(joints))] * n
    return np.array(Q), np.array(V), np.array(A), names


def simulate(design: Design, program: list[dict], dt: float = 0.0005, servo_hz: float = 40.0,
             friction: float = 1.0) -> dict:
    import mujoco

    from .verifiers.motion import build_mujoco

    model = build_mujoco(design)
    model.opt.timestep = dt
    data = mujoco.MjData(model)
    joints = design.joints
    Q, V, A, names = plan(design, program, dt)
    scale = np.array([1e-3 if j.kind == "slide" else math.pi / 180 for j in joints])
    eff_k = np.array([1.0 if j.kind == "slide" else 1e-3 for j in joints])  # user effort -> SI
    dof = np.array([model.joint(n).dofadr[0] for n in names])
    qadr = np.array([model.joint(n).qposadr[0] for n in names])
    limit = np.array([(j.max_effort if j.max_effort is not None else np.inf) for j in joints]) * eff_k
    model.dof_frictionloss[dof] = [friction * (1.0 if j.kind == "slide" else 1e-3) for j in joints]
    M = np.zeros((model.nv, model.nv))
    wn = 2 * math.pi * servo_hz
    n = len(Q)
    q_log = np.zeros((n, len(joints)))
    u_log = np.zeros((n, len(joints)))
    for i in range(n):
        mujoco.mj_forward(model, data)
        if i % 20 == 0:
            mujoco.mj_fullM(model, data, M)
            m_eff = np.diag(M)[dof]
        qr, vr, ar = Q[i] * scale, V[i] * scale, A[i] * scale
        q, v = data.qpos[qadr], data.qvel[dof]
        u = m_eff * (ar + wn * wn * (qr - q) + 2 * wn * (vr - v)) + data.qfrc_bias[dof]
        u = np.clip(u, -limit, limit)
        data.qfrc_applied[:] = 0
        data.qfrc_applied[dof] = u
        mujoco.mj_step(model, data)
        q_log[i] = data.qpos[qadr] / scale
        u_log[i] = u / eff_k
    err = np.abs(q_log - Q)
    sat = (np.abs(u_log) >= 0.999 * (limit / eff_k)[None, :]).mean(axis=0)
    return {"t": np.arange(n) * dt, "q": q_log, "q_ref": Q, "effort": u_log, "names": names,
            "max_error": {nm: float(err[:, k].max()) for k, nm in enumerate(names)},
            "final_error": {nm: float(err[-1, k]) for k, nm in enumerate(names)},
            "peak_effort": {nm: float(np.abs(u_log[:, k]).max()) for k, nm in enumerate(names)},
            "saturated_fraction": {nm: float(sat[k]) for k, nm in enumerate(names)},
            "duration_s": float(n * dt)}


def program_collisions(design: Design, sim: dict, every_mm: float = 4.0) -> list[dict]:
    """Exact collision check along the simulated path (not just at sampled poses)."""
    from .geom import forward_kinematics
    from .verifiers.motion import VOL_TOL, colliding_pairs

    comps = {c.name: c for c in design.components}
    q, names = sim["q"], sim["names"]
    keep, last = [0], q[0]
    for i in range(1, len(q)):
        if np.linalg.norm(q[i] - last) >= every_mm:
            keep.append(i); last = q[i]
    hits: dict[tuple, dict] = {}
    cache: dict = {}
    for i in keep:
        pose = {n: float(q[i, k]) for k, n in enumerate(names)}
        pairs, T = colliding_pairs(design, pose)
        for a, b in pairs:
            rel = np.linalg.inv(T[comps[a].body]) @ T[comps[b].body]
            ck = (a, b, tuple(np.round(rel.reshape(-1), 3)))
            if ck not in cache:
                cache[ck] = overlap_volume(comps[a].shape, comps[b].shape.moved(location_from_matrix(rel)))[0]
            vol = cache[ck]
            allowed = design.allowed_overlaps.get(frozenset((a, b)))
            if vol > VOL_TOL and (allowed is None or vol > allowed) and (a, b) not in hits:
                hits[(a, b)] = {"parts": [a, b], "volume_mm3": round(vol, 2), "time_s": round(float(sim["t"][i]), 3),
                                "pose": {k: round(v, 1) for k, v in pose.items()}}
    return list(hits.values())
