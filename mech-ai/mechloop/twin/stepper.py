"""Open-loop stepper drive dynamics for a machine of sliding axes.

Each axis is a motor inertia pulled toward its commanded position by the motor's
torque-angle curve, F = F_max(speed) * sin(electrical angle error), driving the
moving mass through a spring (belt stretch in series with frame flex) with
optional backlash. So the model has the behaviours that matter for a printer:
the load lags and rings after hard accelerations, and when the motor's error
passes a quarter electrical cycle it falls out of step and settles on a
different pole, which is a permanent position loss (a layer shift).

An axis with no series stiffness given (lead screws) is treated as one rigid mass.

Not modelled: microstepping current ripple, mid-band resonance, driver current
dynamics, position-dependent belt length.
"""
from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def _run(Qc, Vc, m_m, m_l, fmax, k_e, c_m, k_s, c_s, back, fric, bias, sub, dt_out):
    n, k = Qc.shape
    qm = Qc[0].copy()
    ql = Qc[0].copy()
    vm = np.zeros(k)
    vl = np.zeros(k)
    out = np.empty((n, k))
    outm = np.empty((n, k))
    h = dt_out / sub
    for i in range(n):
        for j in range(k):  # state at the instant of command sample i
            out[i, j] = ql[j]
            outm[i, j] = qm[j]
        for s in range(sub):
            w = s / sub  # command at the start of the sub-step, where the state is
            for j in range(k):
                if i + 1 < n:
                    qc = Qc[i, j] + (Qc[i + 1, j] - Qc[i, j]) * w
                    vc = Vc[i, j] + (Vc[i + 1, j] - Vc[i, j]) * w
                else:
                    qc = Qc[i, j]
                    vc = 0.0
                f_step = fmax[i, j] * np.sin(k_e[j] * (qc - qm[j])) + c_m[j] * (vc - vm[j])
                if k_s[j] > 0.0:  # motor and load joined by a spring
                    d = qm[j] - ql[j]
                    hb = back[j] / 2
                    if d > hb:
                        de = d - hb
                    elif d < -hb:
                        de = d + hb
                    else:
                        de = 0.0
                    f_s = k_s[j] * de
                    if de != 0.0 or hb == 0.0:
                        f_s += c_s[j] * (vm[j] - vl[j])
                    f_l = f_s + bias[j]
                    if vl[j] > 1e-6:
                        f_l -= fric[j]
                    elif vl[j] < -1e-6:
                        f_l += fric[j]
                    elif abs(f_l) <= fric[j]:
                        f_l = 0.0
                    else:
                        f_l -= np.sign(f_l) * fric[j]
                    vm[j] += (f_step - f_s) / m_m[j] * h
                    qm[j] += vm[j] * h
                    vl[j] += f_l / m_l[j] * h
                    ql[j] += vl[j] * h
                else:  # one rigid mass
                    f = f_step + bias[j]
                    if vm[j] > 1e-6:
                        f -= fric[j]
                    elif vm[j] < -1e-6:
                        f += fric[j]
                    elif abs(f) <= fric[j]:
                        f = 0.0
                    else:
                        f -= np.sign(f) * fric[j]
                    vm[j] += f / (m_m[j] + m_l[j]) * h
                    qm[j] += vm[j] * h
                    ql[j] = qm[j]
                    vl[j] = vm[j]
    return out, outm


def simulate(Qc, Vc, mass, fmax, travel_per_rev, bias, friction, dt_out, damping_ratio=0.25, pole_pairs=50,
             motor_mass=None, series_stiffness=None, backlash=None, spring_damping_ratio=0.05):
    """Qc, Vc: commanded position (mm) and speed (mm/s), shape (T, k).
    mass: total moving mass per axis in kg, including the motor's reflected inertia.
    motor_mass: the reflected-rotor part of that (kg); with series_stiffness (N/mm) > 0 the axis
    becomes motor -- spring -- load. fmax (T, k) in N; bias (gravity along the axis) and friction in N.
    Returns load positions (mm), worst lag, and info."""
    k = Qc.shape[1]
    mass = np.asarray(mass, dtype=float)
    k_e = 2 * np.pi * pole_pairs / np.asarray(travel_per_rev, dtype=float)  # electrical rad per mm
    ks = np.zeros(k) if series_stiffness is None else np.array(
        [0.0 if (x is None or not np.isfinite(x)) else float(x) for x in series_stiffness])
    mm = np.zeros(k) if motor_mass is None else np.asarray(motor_mass, dtype=float)
    ks = np.where(mm > 1e-9, ks, 0.0)  # no rotor inertia known: keep it rigid
    m_m = np.where(ks > 0, mm, mass)
    m_l = np.where(ks > 0, np.maximum(mass - mm, 1e-6), 0.0)
    f0 = np.median(fmax, axis=0)
    k_step = f0 * k_e * 1e3  # N/m
    c_m = 2 * damping_ratio * np.sqrt(k_step * m_m) * 1e-3  # N per (mm/s)
    red = np.where(ks > 0, m_m * m_l / np.maximum(m_m + m_l, 1e-12), 1.0)
    c_s = 2 * spring_damping_ratio * np.sqrt(ks * 1e3 * red) * 1e-3
    w_all = [np.sqrt(k_step / m_m)]
    if (ks > 0).any():
        w_all.append(np.sqrt(np.where(ks > 0, ks * 1e3 / red, 0.0)))
    sub = int(max(1, np.ceil(dt_out * max(w.max() for w in w_all) / 0.2)))
    back = np.zeros(k) if backlash is None else np.asarray(backlash, dtype=float)
    out, outm = _run(np.ascontiguousarray(Qc), np.ascontiguousarray(Vc), m_m * 1e-3, np.maximum(m_l, 1e-9) * 1e-3,
                     np.ascontiguousarray(fmax), k_e, c_m, ks, c_s, back, np.asarray(friction, dtype=float),
                     np.asarray(bias, dtype=float), sub, dt_out)
    # the frequency the load actually rings at: motor spring and series spring acting in series on the load
    k_eff = np.where(ks > 0, 1.0 / (1.0 / np.maximum(k_step, 1e-9) + 1.0 / np.maximum(ks * 1e3, 1e-9)), k_step)
    f_load = np.sqrt(k_eff / np.where(ks > 0, m_l, mass)) / 2 / np.pi
    return out, np.abs(out - Qc).max(axis=0), {
        "substeps": sub, "load_resonance_hz": f_load.round(1).tolist(),
        "series_stiffness_n_per_mm": [round(float(x), 1) if x > 0 else None for x in ks],
        "quarter_cycle_mm": (np.asarray(travel_per_rev) / (4 * pole_pairs)).round(4).tolist(),
        "motor_positions": outm}
