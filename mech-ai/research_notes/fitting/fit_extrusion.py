"""Extruder lag and melt-rate caps from slicer vendor profiles (research_notes/datasets/slicer_profiles, community_tables).

Pressure advance: every `M572 S<k>` in the PrusaSlicer factory profile, with the printer model, nozzle and filament of the
section it sits in (inheritance is not resolved: only sections that state the value themselves are used).
Flow: `filament_max_volumetric_speed` per filament section, and Bambu's maximum volumetric speed per filament type.
    python -I fit_extrusion.py <datasets dir> <out.json>
Reads text only."""
import collections, csv, json, re, sys
import numpy as np

D, OUT = sys.argv[1], sys.argv[2]
txt = open(D + "/slicer_profiles/prusaslicer_profiles/PrusaResearch_2.3.0.ini", errors="replace").read()
secs = re.split(r"^\[", txt, flags=re.M)[1:]
S = {}
for s in secs:
    head, _, body = s.partition("]\n")
    kv = {}
    for line in body.splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            kv[k.strip()] = v.strip()
    S[head] = kv


def stats(v):
    v = np.array(v, dtype=float)
    return {"n": int(len(v)), "min": round(float(v.min()), 4), "p25": round(float(np.percentile(v, 25)), 4), "median": round(float(np.median(v)), 4),
            "p75": round(float(np.percentile(v, 75)), 4), "max": round(float(v.max()), 4)}


def resolved(name, depth=0):
    """A section with what it inherits (later parents override earlier ones; the section itself wins)."""
    kv = S.get(name, {})
    out = {}
    if depth < 12:
        for par in [x.strip() for x in kv.get("inherits", "").split(";") if x.strip()]:
            out.update(resolved("filament:" + par, depth + 1))
    out.update(kv)
    return out


# ---- pressure advance: every distinct M572 S expression, with the printer family named by the condition in front of it
pa = collections.defaultdict(list)
rows, seen = [], set()
for name, kv in S.items():
    if not name.startswith("filament:"):
        continue
    g = kv.get("start_filament_gcode", "")
    for m in re.finditer(r"M572 S(\{if.*?\{endif\})", g):
        pre = g[:m.start()]
        i = pre.rfind("printer_notes")
        cond = pre[i:i + 80] if i >= 0 else ""
        if "=~" in cond[:16] and "MINI" in cond:
            drive = "bowden"            # Prusa MINI with input shaper: Bowden, V6-type hotend
        elif "=~" in cond[:16] and "MK3.5" in cond:
            drive = "direct"            # MK3.5: direct drive, V6
        elif "!~" in cond[:16] or re.search(r"MK4|XL|COREONE|MK3\.9", cond):
            drive = "direct"            # the {else} branch: Nextruder machines (MK4, XL, Core One), direct drive
        else:
            continue
        key = (drive, m.group(1))
        if key in seen:                 # one entry per distinct factory expression, however many profiles repeat it
            continue
        seen.add(key)
        flex = bool(re.search(r"FLEX|TPU|TPE|PEBA", name, re.I))
        for nz, k in re.findall(r"nozzle_diameter\[[^\]]+\]\s*==\s*([0-9.]+)\}([0-9.]+)", m.group(1)):
            if 0 < float(k) < 2 and not flex:
                pa[(drive, float(nz))].append(float(k))
            rows.append({"section": name, "drive": drive, "nozzle": float(nz), "k_s": float(k), "flexible": flex})
res = {"pressure_advance": {f"{d} {n:g}": stats(v) for (d, n), v in sorted(pa.items()) if len(v) >= 3}, "pa_rows": len(rows)}
res["flexible_0.4"] = {d: stats([r["k_s"] for r in rows if r["flexible"] and r["nozzle"] == 0.4 and r["drive"] == d])
                       for d in ("direct", "bowden") if any(r["flexible"] and r["nozzle"] == 0.4 and r["drive"] == d for r in rows)}
# held-out check of the nozzle scaling: fit K ~ K04 * (0.4/d)^p on 0.4 and 0.6, predict 0.8 and 0.25
med = {k: float(np.median(v)) for k, v in pa.items() if len(v) >= 3}
fitres = {}
for drive in ("direct", "bowden"):
    if (drive, 0.4) in med and (drive, 0.6) in med:
        p = float(np.log(med[(drive, 0.4)] / med[(drive, 0.6)]) / np.log(0.6 / 0.4))
        fitres[drive] = {"k_0.4": med[(drive, 0.4)], "exponent_from_0.4_and_0.6": round(p, 2),
                         "held_out": {f"{d:g}": {"predicted": round(med[(drive, 0.4)] * (0.4 / d) ** p, 4), "factory_median": med[(drive, d)],
                                                 "error_pct": round(100 * (med[(drive, 0.4)] * (0.4 / d) ** p / med[(drive, d)] - 1), 1)}
                                      for d in (0.25, 0.3, 0.5, 0.8) if (drive, d) in med}}
        # leave-one-expression-out at 0.4 mm: the median of the others against each factory value
        v = np.array(pa[(drive, 0.4)])
        loo = [abs(np.median(np.delete(v, i)) / v[i] - 1) for i in range(len(v))]
        fitres[drive]["leave_one_out_0.4_median_abs_error_pct"] = round(100 * float(np.median(loo)), 1)
res["nozzle_scaling"] = fitres
# ---- volumetric flow: concrete filament profiles (not the abstract *...* ones), inheritance resolved
flow = collections.defaultdict(list)
for name in S:
    if not name.startswith("filament:") or name.startswith("filament:*"):
        continue
    kv = resolved(name)
    try:
        v = float(kv.get("filament_max_volumetric_speed", "0"))
    except ValueError:
        continue
    t = kv.get("filament_type", "?")
    tag = name.split("@", 1)[1] if "@" in name else ""
    hot = ("high_flow_nozzle" if "HF" in tag else "mini_bowden_v6" if "MINI" in tag else "nextruder_standard" if re.search(r"PG|MK4|XL|COREONE|MK3\.9", tag)
           else "v6_mk3_family" if tag == "" or "MK3" in tag or "MMU" in tag else "other")
    nz = re.search(r"\b(0\.[2-8]5?)\b", tag)
    if v > 0 and (nz is None or nz.group(1) == "0.4"):
        flow[(hot, t)].append(v)
res["prusa_max_volumetric_speed_0.4"] = {f"{h} | {t}": stats(v) for (h, t), v in sorted(flow.items()) if len(v) >= 5 and t in ("PLA", "PETG", "ABS", "ASA")}
bb = list(csv.DictReader(open(D + "/slicer_profiles/bambustudio_filament_derived/bbl_filament_pa_flow.csv")))
cols = bb[0].keys()
tcol = next(c for c in cols if "type" in c.lower())
vcol = next(c for c in cols if "volumetric" in c.lower())
bf = collections.defaultdict(list)
for r in bb:
    try:
        v = float(r[vcol])
    except (ValueError, TypeError):
        continue
    if v > 0:
        bf[r[tcol]].append(v)
res["bambu_max_volumetric_speed"] = {t: stats(v) for t, v in sorted(bf.items()) if len(v) >= 20}
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps(res, indent=1))
