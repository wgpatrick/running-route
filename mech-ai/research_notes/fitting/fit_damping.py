"""Ringing damping ratio from the Klipper resonance-test spectra (research_notes/datasets/klipper_resonance_psd_corpus).

A mode fit in place of the first look's half-power width: the stored spectrum of the excited axis is fitted with one
or two damped modes plus a floor, the model smeared by the analysis window Klipper used (0.64 s Kaiser window, about
2.2 Hz at half power), which the half-power width reads as extra damping. One file per machine and axis.

    python -I fit_damping.py <datasets dir> <out.json>
Reads CSV only; nothing from the data directory is executed."""
import csv, json, math, sys, hashlib, collections
import numpy as np
from scipy.optimize import least_squares

D, OUT = sys.argv[1], sys.argv[2]
BAND = (12.0, 135.0)


def mode(f, f0, z):
    r = f / f0
    return r * (1 + (2 * z * r) ** 2) / ((1 - r * r) ** 2 + (2 * z * r) ** 2)       # Klipper divides the PSD by f


def smear(f, p, fwhm):
    if fwhm <= 0:
        return p
    s = fwhm / 2.355
    df = float(np.median(np.diff(f)))
    n = int(max(1, round(3 * s / df)))
    k = np.exp(-0.5 * (np.arange(-n, n + 1) * df / s) ** 2)
    return np.convolve(np.pad(p, n, mode="edge"), k / k.sum(), mode="valid")


def model(x, f, nm, fwhm):
    p = np.full_like(f, abs(x[-1]))
    for i in range(nm):
        a, f0, z = x[3 * i:3 * i + 3]
        p = p + abs(a) * mode(f, f0, z)
    return smear(f, p, fwhm)


def fit(f, p, fwhm_bins=1.43):
    m = (f >= BAND[0]) & (f <= BAND[1])
    f, p = f[m], p[m]
    if len(f) < 20 or p.max() <= 0:
        return None
    p = p / p.max()
    df = float(np.median(np.diff(f)))
    fwhm = fwhm_bins * df
    ipk = int(np.argmax(p))
    best = None
    for nm in (1, 2):
        starts = [[1.0 / mode(np.array([f[ipk]]), f[ipk], 0.08)[0], f[ipk], 0.08]]
        if nm == 2:      # second mode: the largest residual peak away from the first
            res = p - model(np.array(best_x1), f, 1, fwhm)
            res[np.abs(f - best_x1[1]) < 0.12 * best_x1[1]] = 0
            j = int(np.argmax(res))
            starts = [list(best_x1[:3]) + [max(res[j], 0.02) * 0.16, f[j], 0.08]]
        x0 = np.array(starts[0] + [0.01])
        lo = np.array([0, BAND[0], 0.005] * nm + [0.0])
        hi = np.array([np.inf, BAND[1] + 15, 0.5] * nm + [1.0])
        x0 = np.clip(x0, lo + 1e-9, hi - 1e-9)
        w = 1.0 / np.sqrt(np.maximum(p, 0.02))          # between linear and log weighting
        r = least_squares(lambda x: (model(x, f, nm, fwhm) - p) * w, x0, bounds=(lo, hi))
        sse = float((r.fun ** 2).sum())
        bic = len(f) * math.log(max(sse / len(f), 1e-12)) + (3 * nm + 1) * math.log(len(f))
        if nm == 1:
            best_x1 = r.x
        if best is None or bic < best["bic"] - 6:
            best = {"nm": nm, "x": r.x, "bic": bic, "rmse": math.sqrt(sse / len(f))}
    modes = sorted(((abs(best["x"][3 * i]) * mode(np.array([best["x"][3 * i + 1]]), best["x"][3 * i + 1], best["x"][3 * i + 2])[0],
                     best["x"][3 * i + 1], best["x"][3 * i + 2]) for i in range(best["nm"])), reverse=True)
    return {"modes_fitted": best["nm"], "f_hz": round(float(modes[0][1]), 1), "zeta": round(float(modes[0][2]), 4),
            "second_mode_hz": round(float(modes[1][1]), 1) if len(modes) > 1 else None,
            "second_mode_rel_height": round(float(modes[1][0] / modes[0][0]), 3) if len(modes) > 1 else None,
            "rmse_rel": round(best["rmse"], 4), "at_bound": bool(modes[0][2] <= 0.0051 or modes[0][2] >= 0.499)}


def half_power(f, p):
    m = (f >= BAND[0]) & (f <= BAND[1])
    f, p = f[m], p[m]
    i = int(np.argmax(p))
    h = p[i] / 2
    a = i
    while a > 0 and p[a] > h:
        a -= 1
    b = i
    while b < len(p) - 1 and p[b] > h:
        b += 1
    return (f[b] - f[a]) / (2 * f[i])


def load(path):
    rows = list(csv.reader(open(path)))
    hdr = rows[0]
    a = np.array([[float(v) for v in r[:5]] for r in rows[1:] if len(r) >= 5])
    return hdr, a


# ---------------------------------------------------------------- estimator check on synthetic spectra
def synthetic_check():
    rng = np.random.default_rng(1)
    out = []
    f = np.arange(0, 135, 1.5625)
    fine = np.arange(0, 140, 0.05)
    for z_true in (0.03, 0.05, 0.08, 0.12):
        zs, hs = [], []
        for _ in range(40):
            f0 = rng.uniform(35, 90)
            p = mode(np.maximum(fine, 1e-6), f0, z_true)
            if rng.random() < 0.5:          # a smaller second mode nearby, as many Y spectra have
                p = p + rng.uniform(0.1, 0.5) * mode(np.maximum(fine, 1e-6), f0 * rng.uniform(1.25, 1.8), rng.uniform(0.04, 0.1)) * p.max() / 60
            p = smear(fine, p, 2.2)                                        # the analysis window
            pc = np.interp(f, fine, p) * (1 + 0.05 * rng.standard_normal(len(f))) + 0.005 * p.max()
            r = fit(f, pc)
            zs.append(r["zeta"])
            hs.append(half_power(f, pc))
        out.append({"zeta_true": z_true, "mode_fit_median": round(float(np.median(zs)), 4),
                    "mode_fit_p10_p90": [round(float(np.percentile(zs, 10)), 4), round(float(np.percentile(zs, 90)), 4)],
                    "half_power_median": round(float(np.median(hs)), 4)})
    return out


rows = list(csv.DictReader(open(D + "/klipper_resonance_psd_corpus/corpus_index_and_peaks.csv")))
stored = [r for r in rows if r["stored_as"] and r["kind"].startswith("toolhead")]
fits = []
for r in stored:
    hdr, a = load(D + "/" + r["stored_as"])
    ax = r["kind"][-1]
    col = {"x": 1, "y": 2}[ax]
    p = a[:, col] if a[:, col].max() > 0.3 * a[:, 4].max() else a[:, 4]        # the excited axis, unless the sensor was turned
    ft = fit(a[:, 0], p)
    if ft is None:
        continue
    pk = float(r["peak_over_median"] or 0)
    fits.append({"repo": r["repo"], "machine": r["machine_guess"], "axis": ax, "file": r["stored_as"].split("/", 1)[1], "licence": r["licence"],
                 "peak_over_median": pk, "zeta_half_power_first_look": float(r["zeta_half_power"]) if r["zeta_half_power"] else None, **ft})


def cls(m):
    if "slinger" in m or "Switchwire" in m:
        return "bed slinger"
    return "corexy" if "Voron" in m or "CoreXY" in m else "unknown"


# one file per machine and axis: the cleanest (largest peak over the band median)
by = collections.defaultdict(list)
for ft in fits:
    by[(ft["repo"], ft["machine"], ft["axis"])].append(ft)
one, med = [], []
for key, lst in sorted(by.items()):
    ok = [x for x in lst if not x["at_bound"] and x["peak_over_median"] >= 5] or None
    if ok is None:
        continue
    pick = max(ok, key=lambda x: x["peak_over_median"])
    one.append({**pick, "class": cls(key[1]), "files_of_this_machine": len(lst),
                "zeta_median_over_its_files": round(float(np.median([x["zeta"] for x in ok])), 4)})


def stats(v):
    v = np.array(v)
    return {"n": int(len(v)), "p10": round(float(np.percentile(v, 10)), 3), "p25": round(float(np.percentile(v, 25)), 3),
            "median": round(float(np.median(v)), 3), "p75": round(float(np.percentile(v, 75)), 3), "p90": round(float(np.percentile(v, 90)), 3)}


def half(repo):          # a fixed split of the machines into two halves, by a hash of the repository name
    return int(hashlib.sha256(repo.encode()).hexdigest(), 16) % 2


res = {"method": "one or two damped modes + floor, smeared by a 1.43-bin window, fitted to the excited axis's PSD between "
                 f"{BAND[0]:g} and {BAND[1]:g} Hz; second mode kept only if BIC improves by 6; damping of the larger mode",
       "files_fitted": len(fits), "machines_axes": len(one), "repositories": len({o["repo"] for o in one}),
       "synthetic_check": synthetic_check(), "per_axis": {}, "held_out": {}, "by_class": {}, "one_file_per_machine": one}
for ax in "xy":
    sel = [o for o in one if o["axis"] == ax]
    res["per_axis"][ax] = {"zeta_one_file": stats([o["zeta"] for o in sel]), "zeta_median_of_files": stats([o["zeta_median_over_its_files"] for o in sel]),
                           "f_hz": stats([o["f_hz"] for o in sel]),
                           "half_power_same_files": stats([o["zeta_half_power_first_look"] for o in sel if o["zeta_half_power_first_look"]]),
                           "two_mode_fits": int(sum(o["modes_fitted"] == 2 for o in sel))}
    a = [o["zeta"] for o in sel if half(o["repo"]) == 0]
    b = [o["zeta"] for o in sel if half(o["repo"]) == 1]
    res["held_out"][ax] = {"fit_half": stats(a), "held_out_half": stats(b)}
    for c in ("corexy", "bed slinger", "unknown"):
        v = [o["zeta"] for o in sel if o["class"] == c]
        if v:
            res["by_class"][f"{c} {ax}"] = stats(v)
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "one_file_per_machine"}, indent=1))
