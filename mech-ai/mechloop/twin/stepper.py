"""Open-loop stepper drive dynamics for a machine of sliding axes.

Each axis is a mass pulled toward its commanded position by the motor's
torque-angle curve, F = F_max(speed) * sin(electrical angle error), so the model
has the two behaviours that matter for a printer: the axis lags and rings when
it is accelerated hard, and when the error passes a quarter electrical cycle
the motor falls out of step and the axis settles on a different pole, which
is a permanent position loss (a layer shift).

Not modelled: microstepping current ripple, mid-band resonance, belt stretch,
frame flex, driver current dynamics.
"""
from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def _run(Qc, Vc, m, fmax, k_e, c, fric, bias, sub, dt_out):
    n, k = Qc.shape
    q = Qc[0].copy()
    v = np.zeros(k)
    out = np.empty((n, k))
    worst = np.zeros(k)
    h = dt_out / sub
    for i in range(n):
        for j in range(k):  # state at the instant of command sample i
            out[i, j] = q[j]
        for s in range(sub):
            w = (s + 1.0) / sub
            for j in range(k):
                if i + 1 < n:
                    qc = Qc[i, j] + (Qc[i + 1, j] - Qc[i, j]) * w
                    vc = Vc[i, j] + (Vc[i + 1, j] - Vc[i, j]) * w
                else:
                    qc = Qc[i, j]
                    vc = 0.0
                err = qc - q[j]
                f = fmax[i, j] * np.sin(k_e[j] * err) + c[j] * (vc - v[j]) + bias[j]
                if v[j] > 1e-6:
                    f -= fric[j]
                elif v[j] < -1e-6:
                    f += fric[j]
                elif abs(f) <= fric[j]:
                    f = 0.0
                else:
                    f -= np.sign(f) * fric[j]
                v[j] += f / m[j] * h
                q[j] += v[j] * h
                if abs(err) > worst[j]:
                    worst[j] = abs(err)
    return out, worst


def simulate(Qc, Vc, mass, fmax, travel_per_rev, bias, friction, dt_out, damping_ratio=0.25, pole_pairs=50):
    """Qc, Vc: commanded position (mm) and speed (mm/s), shape (T, k). mass in kg (incl. reflected
    rotor inertia); fmax (T, k) in N; bias in N (gravity along each axis); friction in N.
    Returns simulated positions (mm) and the worst lag per axis (mm)."""
    k_e = 2 * np.pi * pole_pairs / np.asarray(travel_per_rev, dtype=float)  # electrical rad per mm
    f0 = np.median(fmax, axis=0)
    k_lin = f0 * k_e * 1e3  # N/m
    c = 2 * damping_ratio * np.sqrt(k_lin * mass) * 1e-3  # N per (mm/s)
    wn = np.sqrt(k_lin / mass)
    sub = int(max(1, np.ceil(dt_out * wn.max() / 0.2)))
    # work in mm: a = F/m [m/s^2] * 1e3 [mm/s^2]
    out, worst = _run(np.ascontiguousarray(Qc), np.ascontiguousarray(Vc), np.asarray(mass, dtype=float) * 1e-3,
                      np.ascontiguousarray(fmax), k_e, c, np.asarray(friction, dtype=float),
                      np.asarray(bias, dtype=float), sub, dt_out)
    return out, worst, {"substeps": sub, "natural_frequency_hz": (wn / 2 / np.pi).round(1).tolist(),
                        "quarter_cycle_mm": (np.asarray(travel_per_rev) / (4 * pole_pairs)).round(4).tolist()}
