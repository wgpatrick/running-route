"""Three-node hotend model fitted to the Ender 3 logs (research_notes/datasets/ender3_hotend_twin_logs, GPL-3.0 data).

Nodes: cartridge (the 40 W heater), block (where the thermistor sits), nozzle (nozzle and the hot end of the heat break).
  C_h dTh/dt = P pwm - G_hb (Th - Tb)
  C_b dTb/dt = G_hb (Th - Tb) - G_bn (Tb - Tn) - [g_b + g_fan phi(fan)] (Tb - Ta) - c_rad ((Tb+273)^4 - (Ta+273)^4)
  C_n dTn/dt = G_bn (Tb - Tn) - g_n (Tn - Ta) - k_fil v_e (Tn - Ta)
  sensor: first-order lag tau behind Tb.     phi(fan) = (max(0, fan - f0) / (1 - f0))^n
Open loop: driven by the logged heater duty, fan and extruder speed. P = 40 W and Ta = 25 degC are assumed (not logged);
k_fil is not fitted (PLA: density x specific heat x filament section = 0.0054 W/K per mm/s).

    python -I fit_hotend.py <datasets dir> <out.json> [held-out file substring ...]
Reads CSV only."""
import csv, glob, json, math, os, sys
import numpy as np
from numba import njit
from scipy.optimize import least_squares

D, OUT = sys.argv[1], sys.argv[2]
ARGS = sys.argv[3:]
FREE = "--free" in ARGS          # bounds wide open: the cartridge and sensor-side masses then collapse to nothing (see the report)
HOLD = [a for a in ARGS if not a.startswith("--")] or ["2056_klipper_baski245"]
P_MAX, T_AMB, K_FIL, DT = 40.0, 25.0, 0.0054, 0.05
NAMES = ["C_h", "C_b", "C_n", "G_hb", "G_bn", "g_b", "g_n", "g_fan", "fan_exp", "c_rad", "tau_s", "fan_f0"]
X0 = np.array([2.0, 6.0, 1.5, 1.0, 0.6, 0.03, 0.02, 0.05, 0.6, 1.5e-10, 2.0, 0.15])
LO = np.array([0.2, 0.5, 0.1, 0.1, 0.05, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.0])
HI = np.array([8.0, 25.0, 8.0, 20.0, 10.0, 0.3, 0.3, 0.5, 1.5, 1.0e-9, 8.0, 0.29])
if not FREE:
    # The logs (3 to 4 samples a second, duty set by a PID loop) do not pin down the fast path from heater to sensor: left
    # free, the cartridge shrinks to 0.2 J/K behind 17 W/K and a relay test on the result cycles in 4.5 s where real hotends
    # take 24 to 55 s. So the fast path is held to what the parts are: a 6 x 20 mm cartridge is 1.5 to 4 J/K, its contact
    # with the block 0.3 to 1.5 W/K (the logs' author uses 2.0 J/K and 0.55 W/K), the block at least 2 J/K.
    LO[0], HI[0] = 1.5, 4.0
    LO[3], HI[3] = 0.3, 1.5
    LO[1] = 2.0
    X0[3] = 0.6


@njit(cache=True)
def sim(x, tg, pw, fan, ve, T0, dt, pmax, ta, kfil):
    Ch, Cb, Cn, Ghb, Gbn, gb, gn, gfan, nexp, crad, tau, f0 = x
    n = len(tg)
    out = np.empty(n)
    Th = Tb = Tn = s = T0
    if T0 > ta + 5.0:        # a run that starts hot: nodes at their steady offsets for a hold at T0, no fan
        Tn = (Gbn * Tb + gn * ta) / (Gbn + gn)
        q = Gbn * (Tb - Tn) + gb * (Tb - ta) + crad * ((Tb + 273.15) ** 4 - (ta + 273.15) ** 4)
        Th = Tb + q / Ghb
    ta4 = (ta + 273.15) ** 4
    sub = int(max(1, math.ceil((tg[1] - tg[0]) / dt)))
    h = (tg[1] - tg[0]) / sub
    # conduction between the nodes is stiff: implicit Euler for it (as ThermalNet.step does), losses explicit
    A = np.zeros((3, 3))
    A[0, 0] = Ch / h + Ghb
    A[0, 1] = -Ghb
    A[1, 0] = -Ghb
    A[1, 1] = Cb / h + Ghb + Gbn
    A[1, 2] = -Gbn
    A[2, 1] = -Gbn
    A[2, 2] = Cn / h + Gbn
    Ai = np.linalg.inv(A)
    for i in range(n):
        out[i] = s
        f = fan[i]
        phi = ((f - f0) / (1.0 - f0)) ** nexp if f > f0 else 0.0
        for _ in range(sub):
            b0 = Ch / h * Th + pmax * pw[i]
            b1 = Cb / h * Tb - (gb + gfan * phi) * (Tb - ta) - crad * ((Tb + 273.15) ** 4 - ta4)
            b2 = Cn / h * Tn - (gn + kfil * ve[i]) * (Tn - ta)
            Th = Ai[0, 0] * b0 + Ai[0, 1] * b1 + Ai[0, 2] * b2
            Tb_n = Ai[1, 0] * b0 + Ai[1, 1] * b1 + Ai[1, 2] * b2
            Tn = Ai[2, 0] * b0 + Ai[2, 1] * b1 + Ai[2, 2] * b2
            Tb = Tb_n
            if tau > h:
                s += h * (Tb - s) / tau
            else:
                s = Tb
    return out


def load(p):
    r = list(csv.DictReader(open(p)))
    t = np.array([float(x["time"]) for x in r])
    t -= t[0]
    T = np.array([float(x["T1_real"]) for x in r])
    pw = np.array([float(x["pwm"]) for x in r])
    fan = np.array([float(x["fan_state"]) for x in r])
    ve = np.array([abs(float(x["extrude_velocity"] or 0.0)) for x in r])
    tg = np.arange(0.0, t[-1], 0.25)
    hold = lambda v: v[np.clip(np.searchsorted(t, tg, side="right") - 1, 0, len(t) - 1)]     # the logged duty holds until the next sample
    return {"name": os.path.basename(p)[len("benchmark__"):-4], "tg": tg, "T": np.interp(tg, t, T), "pw": hold(pw), "fan": hold(fan),
            "ve": hold(ve), "sample_s": float(np.median(np.diff(t)))}


runs = [load(p) for p in sorted(glob.glob(D + "/ender3_hotend_twin_logs/benchmark__2026*.csv"))]
cal = [r for r in runs if not any(h in r["name"] for h in HOLD)]
held = [r for r in runs if any(h in r["name"] for h in HOLD)]


def run(x, r, kfil=K_FIL):
    return sim(x, r["tg"], r["pw"], r["fan"], r["ve"], float(r["T"][0]), DT, P_MAX, T_AMB, kfil)


def resid(x):
    # every run counts by its duration, slow-sampled ones at half weight (the duty between their samples is not known)
    return np.concatenate([(run(x, r) - r["T"]) * (0.5 if r["sample_s"] > 1.0 else 1.0) for r in cal])


best = None
rng = np.random.default_rng(0)
for k in range(3):
    x0 = X0 if k == 0 else np.clip(X0 * np.exp(0.5 * rng.standard_normal(len(X0))), LO + 1e-12, HI - 1e-12)
    f = least_squares(resid, x0, bounds=(LO, HI), x_scale=np.maximum(X0, 1e-10), max_nfev=250)
    if best is None or f.cost < best.cost:
        best = f
x = best.x


def score(r, x, **kw):
    y = run(x, r, **kw)
    e = y - r["T"]
    hot = r["T"] > 100.0
    # mean power the model needs to hold the logged temperature against the mean power that was applied (hot part only)
    return {"run": r["name"], "duration_s": round(float(r["tg"][-1])), "sample_s": round(r["sample_s"], 2),
            "rmse_c": round(float(np.sqrt((e ** 2).mean())), 2), "bias_c": round(float(e.mean()), 2), "worst_c": round(float(np.abs(e).max()), 2),
            "final_error_c": round(float(e[-1]), 2), "mean_duty_logged": round(float(r["pw"].mean()), 4)}


def one_node(rs):
    def s1(p, r):
        C, g, gf = p
        out = np.empty(len(r["tg"]))
        T = r["T"][0]
        for i in range(len(out)):
            out[i] = T
            T += 0.25 * (P_MAX * r["pw"][i] - (g + gf * r["fan"][i]) * (T - T_AMB)) / C
        return out
    f1 = least_squares(lambda p: np.concatenate([s1(p, r) - r["T"] for r in rs]), [8, 0.08, 0.03], bounds=([1, 0.01, 0], [40, 1, 1]))
    return f1.x, s1


x1, s1 = one_node(cal)
Tb = 245.0
g_rad = float(x[9] * ((Tb + 273.15) ** 4 - (T_AMB + 273.15) ** 4) / (Tb - T_AMB))
g_noz = float(x[4] * x[6] / (x[4] + x[6]))             # nozzle path seen from the block, steady
phi = lambda f: (max(0.0, f - x[11]) / (1 - x[11])) ** x[8]
still = float(x[5] + g_rad + g_noz)
res = {"assumed": {"heater_w": P_MAX, "ambient_c": T_AMB, "k_fil_w_per_k_per_mm_s": K_FIL},
       "parameters": {n: float(f"{v:.5g}") for n, v in zip(NAMES, x)},
       "at_bounds": [n for n, v, lo, hi in zip(NAMES, x, LO, HI) if (v - lo) < 1e-3 * (hi - lo) or (hi - v) < 1e-3 * (hi - lo)],
       "derived": {"total_capacity_j_k": round(float(x[0] + x[1] + x[2]), 2),
                   "loss_still_air_w_k_at_245c": round(still, 4), "of_which_radiation": round(g_rad, 4),
                   "loss_full_fan_w_k_at_245c": round(still + float(x[7]), 4),
                   "loss_w_k_by_fan": {f"{f:g}": round(still + float(x[7]) * phi(f), 4) for f in (0, 0.25, 0.5, 0.75, 1.0)},
                   "resistance_k_w_still_and_full_fan": [round(1 / still, 1), round(1 / (still + float(x[7])), 1)],
                   "sensor_lag_s": round(float(x[10]), 2)},
       "calibration_runs": [score(r, x) for r in cal], "held_out_runs": [score(r, x) for r in held],
       "held_out_without_filament_term": [score(r, x, kfil=0.0) for r in held],
       "calibration_rmse_c": round(float(np.sqrt(np.mean(np.concatenate([run(x, r) - r["T"] for r in cal]) ** 2))), 2),
       "one_node_same_runs": {"C_j_k": round(float(x1[0]), 2), "g_w_k": round(float(x1[1]), 4), "g_fan_w_k": round(float(x1[2]), 4),
                              "rmse_c": round(float(np.sqrt(np.mean(np.concatenate([s1(x1, r) - r["T"] for r in cal]) ** 2))), 2),
                              "held_out_rmse_c": [round(float(np.sqrt(np.mean((s1(x1, r) - r["T"]) ** 2))), 2) for r in held]},
       "held_out": HOLD, "bounds": "free" if FREE else "physical (cartridge 1.5-4 J/K, contact 0.3-1.5 W/K, block >= 2 J/K)"}
# held-out hold: the duty the model says a hold at the logged temperature needs, against the duty that was applied
for r in held:
    hot = (r["T"] > 200.0)
    if hot.mean() > 0.9:
        need = np.mean([(x[5] + g_rad + x[7] * phi(f)) * (Tb - T_AMB) + (Tb - T_AMB) / (1 / x[4] + 1 / (x[6] + K_FIL * v))
                        for f, v in zip(r["fan"][hot], r["ve"][hot])]) / P_MAX
        res.setdefault("held_out_hold_duty", []).append({"run": r["name"], "model_mean_duty": round(float(need), 4),
                                                         "logged_mean_duty": round(float(r["pw"][hot].mean()), 4),
                                                         "error_pct": round(100 * float(need / r["pw"][hot].mean() - 1), 1)})
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
