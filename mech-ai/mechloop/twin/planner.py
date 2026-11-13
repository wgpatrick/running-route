"""Firmware-style motion planning: look-ahead with per-axis speed and acceleration
limits and junction deviation, the scheme Marlin and Klipper-like firmwares use."""
from __future__ import annotations

import numpy as np


def plan(points: np.ndarray, feeds: np.ndarray, vmax: np.ndarray, amax: np.ndarray, dt: float,
         junction_deviation: float = 0.02, dwell: np.ndarray | None = None):
    """points: (N+1, k) axis positions; feeds: (N,) requested path speed per segment.
    Returns t-sampled Q (T, k), V (T, k), seg index (T,), fraction along segment (T,), and per-segment times."""
    d = np.diff(points, axis=0)
    L = np.linalg.norm(d, axis=1)
    n = len(L)
    u = np.zeros_like(d)
    nz = L > 1e-9
    u[nz] = d[nz] / L[nz, None]
    with np.errstate(divide="ignore", invalid="ignore"):
        v_lim = np.min(np.where(np.abs(u) > 1e-9, vmax[None, :] / np.abs(u), np.inf), axis=1)
        a_lim = np.min(np.where(np.abs(u) > 1e-9, amax[None, :] / np.abs(u), np.inf), axis=1)
    vc = np.minimum(feeds, v_lim)
    vc[~nz] = 0.0
    a_lim[~nz] = 1.0
    # junction speeds
    vj = np.zeros(n + 1)
    for i in range(1, n):
        if not (nz[i - 1] and nz[i]):
            continue
        cos_t = -float(u[i - 1] @ u[i])
        if cos_t > 0.999999:
            continue  # full reversal: stop
        a = min(a_lim[i - 1], a_lim[i])
        if cos_t < -0.999999:
            v = min(vc[i - 1], vc[i])
        else:
            s = np.sqrt(0.5 * (1.0 - cos_t))
            v = min(np.sqrt(a * junction_deviation * s / (1.0 - s)), vc[i - 1], vc[i])
        vj[i] = v
    # backward then forward pass so every junction speed is reachable within its segments
    for i in range(n - 1, -1, -1):
        if nz[i]:
            vj[i] = min(vj[i], np.sqrt(vj[i + 1] ** 2 + 2 * a_lim[i] * L[i]))
        else:
            vj[i] = 0.0 if i > 0 else vj[i]
            vj[i + 1] = 0.0
    for i in range(n):
        if nz[i]:
            vj[i + 1] = min(vj[i + 1], np.sqrt(vj[i] ** 2 + 2 * a_lim[i] * L[i]))
    Qs, Vs, Ss, Fs = [], [], [], []
    seg_t = np.zeros(n)
    clock, next_t = 0.0, 0.0
    for i in range(n):
        if not nz[i]:
            T = float(dwell[i]) if dwell is not None else 0.0
            ts = np.arange(next_t - clock, T, dt)
            if len(ts):
                Qs.append(np.repeat(points[i][None, :], len(ts), 0)); Vs.append(np.zeros((len(ts), d.shape[1])))
                Ss.append(np.full(len(ts), i)); Fs.append(ts / T)
                next_t = clock + ts[-1] + dt
            seg_t[i] = T
            clock += T
            continue
        a, ve, vx, v = a_lim[i], vj[i], vj[i + 1], vc[i]
        d1, d2 = (v * v - ve * ve) / (2 * a), (v * v - vx * vx) / (2 * a)
        if d1 + d2 > L[i]:
            v = np.sqrt(max((2 * a * L[i] + ve * ve + vx * vx) / 2, 0.0))
            d1, d2 = (v * v - ve * ve) / (2 * a), (v * v - vx * vx) / (2 * a)
        t1, t3 = (v - ve) / a, (v - vx) / a
        dc = max(L[i] - d1 - d2, 0.0)
        t2 = dc / v if v > 1e-12 else 0.0
        T = t1 + t2 + t3
        ts = np.arange(next_t - clock, T, dt)
        if len(ts):
            s = np.where(ts < t1, ve * ts + 0.5 * a * ts ** 2,
                         np.where(ts < t1 + t2, d1 + v * (ts - t1),
                                  d1 + dc + v * (ts - t1 - t2) - 0.5 * a * (ts - t1 - t2) ** 2))
            sd = np.where(ts < t1, ve + a * ts, np.where(ts < t1 + t2, v, v - a * (ts - t1 - t2)))
            s = np.clip(s, 0.0, L[i])
            Qs.append(points[i][None, :] + s[:, None] * u[i][None, :]); Vs.append(sd[:, None] * u[i][None, :])
            Ss.append(np.full(len(ts), i)); Fs.append(s / L[i])
            next_t = clock + ts[-1] + dt
        seg_t[i] = T
        clock += T
    return (np.vstack(Qs), np.vstack(Vs), np.concatenate(Ss).astype(np.int64), np.concatenate(Fs), seg_t)
