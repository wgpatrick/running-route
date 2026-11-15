"""The moving machine as the twin sees it: per-axis mass, drive force, series stiffness (belts in series with the
frame) and damping, from the CAD, the catalog and the FEA. `run_print` simulates it step by step (stepper.py); the
same numbers, linearised, give each axis's resonance, damping ratio and frequency response, which is what a
resonance test on the built machine would measure and what the firmware's input shaper is tuned from."""
from __future__ import annotations

import math

import numpy as np

from ..geom import forward_kinematics

POLE_PAIRS = 50


def axis_joints(design, pm):
    joints = {j.name: j for j in design.joints}
    return [joints[pm.x], joints[pm.y], joints[pm.z]]


def machine_model(design, pm, mass_extra: dict | None = None) -> dict:
    """Mass, gravity bias, travel per rev, series stiffness and rotor mass for X, Y, Z. Raises ValueError if a drive
    is not resolved. Returns also the motor names per axis so the caller can evaluate the torque curve at speed."""
    import mujoco

    from ..verifiers.motion import build_mujoco
    from ..verifiers.ratings import resolve_drives

    resolve_drives(design)
    jl = axis_joints(design, pm)
    model = build_mujoco(design)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    M = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, M)
    dof = [model.joint(j.name).dofadr[0] for j in jl]
    data.qvel[:] = 0
    data.qacc[:] = 0
    mujoco.mj_inverse(model, data)  # force each axis must supply to hold still = gravity load
    comps = {c.name: c for c in design.components}
    mass, bias, tpr, drives = [], [], [], []
    for k, j in enumerate(jl):
        dr = getattr(j, "drive_resolved", None)
        if not dr:
            raise ValueError(f"Joint {j.name} has no resolved drive (motor + transmission).")
        mass.append(M[dof[k], dof[k]] + j.reflected_inertia + (mass_extra or {}).get("xyz"[k], 0.0))
        bias.append(-float(data.qfrc_inverse[dof[k]]))
        tpr.append(dr["travel_per_rev"])
        curve = comps[dr["motors"][0]].ratings.get("torque_curve_rpm_frac") or [(0, 0.7), (1e6, 0.7)]
        drives.append({"curve": curve, "holding_nmm": sum(comps[m].ratings["holding_torque_nmm"] for m in dr["motors"]),
                       "efficiency": dr["efficiency"], "travel_per_rev": dr["travel_per_rev"]})
    sub = M[np.ix_(dof, dof)]
    coupled = bool(np.abs(sub - np.diag(np.diag(sub))).max() > 1e-6)
    # series compliance: belt stretch (from the belt's routed length) in series with frame flex (from FEA)
    series, motor_mass, belts_used = [], [], {}
    for k, (j, ax) in enumerate(zip(jl, "xyz")):
        ks = None
        dr = j.drive_resolved
        if pm.compliant and dr["kind"] == "belt":
            from ..verifiers.belts import route

            # every belt that runs round one of this joint's drive pulleys pulls on the axis, in parallel
            pul = (j.drive or {}).get("pulley")
            pulleys = set([pul] if isinstance(pul, str) else (pul or []))
            is_pulley = {c.name for c in design.components if "pitch_diameter_mm" in c.ratings}
            for pair in design.joins:
                if len(pair) == 2 and (set(pair) & set(dr["motors"])):
                    pulleys |= set(pair) & is_pulley
            T_home = forward_kinematics(design, {})
            kb, used = 0.0, []
            for b in design.belts:
                if any(n[0] == "pulley" and n[1] in pulleys for n in b.path):
                    L = route(design, b, T_home)["length"]
                    ea = pm.belt_ea_n * b.width / 6.0  # stiffness scales with belt width
                    kb += 4.0 * ea / L  # two runs in parallel, carriage at mid-travel
                    used.append({"belt": b.name, "width_mm": b.width, "n_per_mm": round(4.0 * ea / L, 1)})
            if kb > 0:
                ks = kb
                belts_used[ax] = used
        if pm.compliant and ax in pm.struct_stiffness:
            kst = float(pm.struct_stiffness[ax])
            ks = kst if ks is None else 1.0 / (1.0 / ks + 1.0 / kst)
        series.append(ks)
        motor_mass.append(j.reflected_inertia)
    return {"joints": jl, "mass": np.array(mass), "bias": np.array(bias), "tpr": np.array(tpr), "drives": drives,
            "series": series, "motor_mass": np.array(motor_mass), "belts_used": belts_used, "coupled": coupled,
            "fric": [pm.friction_n.get(a, 2.0) for a in "xyz"], "back": [pm.backlash_mm.get(a, 0.0) for a in "xyz"]}


def drive_force(mm: dict, Vc: np.ndarray, torque_scale: float = 1.0) -> np.ndarray:
    """Peak force (N) each axis's motors can give at each sample's commanded speed."""
    fmax = np.zeros((len(Vc), 3))
    for k, d in enumerate(mm["drives"]):
        rpm = np.abs(Vc[:, k]) / d["travel_per_rev"] * 60.0
        xs, ys = zip(*d["curve"])
        fmax[:, k] = 2 * math.pi * d["holding_nmm"] * np.interp(rpm, xs, ys) * d["efficiency"] / d["travel_per_rev"] * torque_scale
    return fmax


def linear_axis(mm: dict, k: int, pm, speed_mm_s: float = 0.0, torque_scale: float = 1.0) -> dict:
    """Axis k linearised about rest: the stepper's torque-angle curve becomes a spring (F = F_max k_e x for small
    error), in series with the belt/frame spring when there is one. Same parameters and damping rule as stepper.py.
    Returns the state matrices' natural frequencies and damping ratios and a function H(f) = load / command."""
    f0 = float(drive_force(mm, np.full((1, 3), speed_mm_s), torque_scale)[0, k])
    k_e = 2 * math.pi * POLE_PAIRS / float(mm["tpr"][k])              # electrical rad per mm
    k_step = f0 * k_e * 1e3                                           # N/m
    ks = mm["series"][k]
    m_tot, m_rot = float(mm["mass"][k]), float(mm["motor_mass"][k])
    two_mass = ks is not None and np.isfinite(ks) and ks > 0 and m_rot > 1e-9
    if two_mass:
        m_m, m_l, k_s = m_rot, max(m_tot - m_rot, 1e-6), ks * 1e3
        c_m = 2 * pm.damping_ratio * math.sqrt(k_step * m_m)
        c_s = 2 * pm.spring_damping_ratio * math.sqrt(k_s * m_m * m_l / (m_m + m_l))
        A = np.array([[0, 1, 0, 0], [-(k_step + k_s) / m_m, -(c_m + c_s) / m_m, k_s / m_m, c_s / m_m],
                      [0, 0, 0, 1], [k_s / m_l, c_s / m_l, -k_s / m_l, -c_s / m_l]])

        def H(f):
            s = 2j * math.pi * np.asarray(f, dtype=float)
            zm = m_m * s * s + (c_m + c_s) * s + k_step + k_s
            zl = m_l * s * s + c_s * s + k_s
            cpl = c_s * s + k_s
            return (c_m * s + k_step) * cpl / (zm * zl - cpl * cpl)
    else:
        m_m = m_tot
        c_m = 2 * pm.damping_ratio * math.sqrt(k_step * m_m)
        A = np.array([[0, 1], [-k_step / m_m, -c_m / m_m]])

        def H(f):
            s = 2j * math.pi * np.asarray(f, dtype=float)
            return (c_m * s + k_step) / (m_m * s * s + c_m * s + k_step)
    lam = np.linalg.eigvals(A)
    lam = lam[lam.imag > 1e-9]
    modes = sorted(({"hz": float(abs(x) / 2 / math.pi), "damping_ratio": float(-x.real / abs(x))} for x in lam),
                   key=lambda d: d["hz"])
    return {"modes": modes, "H": H, "two_mass": two_mass, "k_step_n_per_mm": k_step * 1e-3,
            "series_n_per_mm": ks if two_mass else None, "holding_force_n": f0}
