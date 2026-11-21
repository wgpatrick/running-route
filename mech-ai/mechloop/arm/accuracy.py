"""Decisive test 2: tool-point error Monte Carlo (analytic, small-displacement).

Error at the TCP = random joint errors through the Jacobian (servo dither of +/- one encoder count, encoder noise,
backlash with a random side where the load sign is uncertain) + deterministic deflection from the CHANGE of load
between the taught state (0.2 kg tool, no contact) and the task (payload, contact force, screw reaction moment):
transmission windup where the loop does not close on the joint output, beam bending / torsion of links, column, mast
and ram, bearing and guide tilt springs, and belt stretch on linear axes.

Metric (ARM_SCOPE decisive test 2): "3 sigma" = 99.73rd percentile of the error magnitude over the samples, lateral
(xy) at assembly poses (insertion is vertical) and 3D at sheet poses; worst over the class's poses and path points.
Not modelled: thermal drift, encoder INL and eccentricity (repeatable, removed by teaching / calibration), dynamics and
settling, creep of printed parts, tool and coupling compliance. Pass needs test 3 to confirm the joint numbers.
"""
from __future__ import annotations

import numpy as np

from . import poses as PZ

LIMITS = {"assembly": 0.2, "sheet": 1.0}
P3S = 99.73


def jacobian(arm, q, tool_len):
    tcp = arm.fk(q, tool_len)
    cols = []
    for kind, axis, pt in arm.joints(q, tool_len):
        cols.append(np.cross(axis, tcp - pt) if kind == "R" else np.asarray(axis, float))
    return tcp, np.array(cols)          # (n_joints, 3): mm per rad / mm per mm


def _element(tcp, p, Cr, Ct, F, M):
    r = tcp - p
    d = np.zeros(3)
    if Cr is not None:
        d += np.cross(Cr @ (np.cross(r, F) + M), r)
    if Ct is not None:
        d += Ct @ F
    return d


def breakdown(arm, q, tool_len, F, M, cls):
    """Deflection per compliance group (mm, lateral for assembly, 3D for sheet), largest first."""
    tcp = arm.fk(q, tool_len)
    acc: dict = {}
    for p, Cr, Ct, label in arm.compliance(q, tool_len):
        acc[label] = acc.get(label, np.zeros(3)) + _element(tcp, p, Cr, Ct, F, M)
    ds, dw = deflection(arm, q, tool_len, F, M)
    acc["windup (uncorrected joints)"] = dw
    sel = slice(0, 2) if cls == "assembly" else slice(0, 3)
    return dict(sorted(((k, float(np.linalg.norm(v[sel]))) for k, v in acc.items()), key=lambda kv: -kv[1]))


def deflection(arm, q, tool_len, F, M):
    """Deterministic TCP displacement (mm) from a wrench change F (N), M (N·mm): structure + uncorrected windup."""
    tcp = arm.fk(q, tool_len)
    d_struct = np.zeros(3)
    for p, Cr, Ct, _ in arm.compliance(q, tool_len):
        d_struct += _element(tcp, p, Cr, Ct, F, M)
    d_wind = np.zeros(3)
    for (kind, axis, pt), spec in zip(arm.joints(q, tool_len), arm.joint_specs):
        if spec.get("k") is None:
            continue
        if kind == "R":
            tau = axis @ (np.cross(tcp - pt, F) + M)
            d_wind += (tau / spec["k"]) * np.cross(axis, tcp - pt)
        else:
            d_wind += (axis @ F / spec["k"]) * np.asarray(axis, float)
    return d_struct, d_wind


def joint_samples(specs, n, rng):
    """(n, n_joints) random joint errors in rad / mm."""
    out = np.zeros((n, len(specs)))
    for j, s in enumerate(specs):
        f = np.radians(1.0) if s["kind"] == "R" else 1.0
        e = rng.uniform(-s["step"], s["step"], n) + rng.normal(0, s["noise"], n) if s["noise"] else \
            rng.uniform(-s["step"], s["step"], n)
        if s["backlash"]:
            e = e + rng.uniform(-s["backlash"] / 2, s["backlash"] / 2, n)
        out[:, j] = e * f
    return out


def pose_error(arm, q, tool_len, F, M, cls, n=4000, rng=None):
    rng = rng or np.random.default_rng(0)
    tcp, J = jacobian(arm, q, tool_len)
    ds, dw = deflection(arm, q, tool_len, F, M)
    dq = joint_samples(arm.joint_specs, n, rng)
    rand = dq @ J
    e = rand + ds + dw
    sel = slice(0, 2) if cls == "assembly" else slice(0, 3)
    mag = np.linalg.norm(e[:, sel], axis=1)
    per_joint = {}
    for j, s in enumerate(arm.joint_specs):
        per_joint[s["label"] + f"#{j}"] = float(np.percentile(np.linalg.norm((dq[:, j:j + 1] * J[j])[:, sel], axis=1), P3S))
    return {"p3s": float(np.percentile(mag, P3S)),
            "random_p3s": float(np.percentile(np.linalg.norm(rand[:, sel], axis=1), P3S)),
            "deflection": float(np.linalg.norm((ds + dw)[sel])), "struct": float(np.linalg.norm(ds[sel])),
            "windup": float(np.linalg.norm(dw[sel])), "per_joint": per_joint}


def load_cases(pose, i=0):
    """Wrench changes to evaluate at path point i: assembly poses at 0.2 and 1 kg plus 20 N (and the pose's moment);
    sheet poses as stated (a path may state one force per point)."""
    if pose.get("forces_n"):
        pose = dict(pose, force_n=pose["forces_n"][i])
    F0, M0 = PZ.wrench(pose)
    if pose["accuracy_class"] != "assembly":
        return [("as stated", F0, M0)]
    out = []
    for m in (0.2, 1.0):
        p = dict(pose, payload_kg=m, force_n=[0.0, 0.0, 20.0])
        F, M = PZ.wrench(p)
        out.append((f"{m} kg + 20 N", F, M0))
    return out


def evaluate_arm(arm, poses, reach_results, n=4000, max_pts=12, seed=0):
    """Worst-case error per pose (over load cases and up to max_pts points of a path) for the arm's joint_specs."""
    rng = np.random.default_rng(seed)
    byid = {r.id: r for r in reach_results}
    rows = []
    for pose in poses:
        r = byid.get(pose["id"])
        if r is None or not r.reach or not r.qs:
            continue
        tool_len = PZ.TOOLS[pose["tool"]][0]
        idx = np.unique(np.linspace(0, len(r.qs) - 1, min(max_pts, len(r.qs))).astype(int))
        worst = None
        for i in idx:
            for lc, F, M in load_cases(pose, i):
                e = pose_error(arm, np.asarray(r.qs[i]), tool_len, F, M, pose["accuracy_class"], n, rng)
                e.update(case=lc, point=int(i))
                if worst is None or e["p3s"] > worst["p3s"]:
                    worst = e
                    worst["breakdown"] = breakdown(arm, np.asarray(r.qs[i]), tool_len, F, M, pose["accuracy_class"])
        worst.update(id=pose["id"], cls=pose["accuracy_class"], required=pose["required"],
                     passes=worst["p3s"] <= LIMITS[pose["accuracy_class"]])
        rows.append(worst)
    return rows


def summarise(rows):
    out = {}
    for cls in LIMITS:
        rs = [r for r in rows if r["cls"] == cls and r["required"]]
        if not rs:
            continue
        w = max(rs, key=lambda r: r["p3s"])
        out[cls] = {"worst_p3s": w["p3s"], "worst_pose": w["id"], "worst_case": w["case"], "random_p3s": w["random_p3s"],
                    "deflection": w["deflection"], "limit": LIMITS[cls], "passes": all(r["passes"] for r in rs)}
    return out
