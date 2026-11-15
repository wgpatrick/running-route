"""Summarise the classified public configs into the measurement file the twin compares against."""
import json, re, sys, numpy as np
cl = json.load(open("gh/classified.json"))
hits = {(r, p): s for m, l in json.load(open("gh/hits.json")).items() for r, p, s in l}
def q(a, nd=1):
    a = np.asarray([x for x in a if x is not None], dtype=float)
    return None if not len(a) else {"n": int(len(a)), "p10": round(float(np.percentile(a, 10)), nd), "p25": round(float(np.percentile(a, 25)), nd),
                                    "median": round(float(np.median(a)), nd), "p75": round(float(np.percentile(a, 75)), nd), "p90": round(float(np.percentile(a, 90)), nd)}
summary, entries = {}, {}
for c, lst in cl.items():
    damp = {"x": [], "y": []}
    for r in lst:
        t = open(f"gh/files/{hits[(r['repo'], r['path'])]}.txt", errors="replace").read()
        for ax in "xy":
            for mm in re.finditer(r"^(?:#\*#)?\s*damping_ratio_" + ax + r"\s*[:=]\s*([\d.]+)", t, re.M):
                if abs(float(mm.group(1)) - 0.1) > 1e-6: damp[ax].append(float(mm.group(1)))
    sv = [r for r in lst if r["saved_x"] or r["saved_y"]]
    summary[c] = {"configs": len(lst),
                  "x_hz": q([r["fx"] for r in lst]), "y_hz": q([r["fy"] for r in lst]),
                  "x_hz_autosaved": q([r["fx"] for r in sv]), "y_hz_autosaved": q([r["fy"] for r in sv]),
                  "max_accel_mm_s2": q([r["max_accel"] for r in lst]), "run_current_x_a": q([r["run_current_x"] for r in lst], 2),
                  "damping_ratio_x": q(damp["x"], 3), "damping_ratio_y": q(damp["y"], 3),
                  "shaper_types_x": {k: sum(1 for r in lst if r["tx"] == k) for k in sorted({str(r["tx"]) for r in lst})},
                  "shaper_types_y": {k: sum(1 for r in lst if r["ty"] == k) for k in sorted({str(r["ty"]) for r in lst})}}
    entries[c] = [{k: r[k] for k in ("url", "fx", "fy", "tx", "ty", "saved_x", "saved_y", "max_accel", "max_velocity", "run_current_x", "pos_max_x", "pos_max_y", "kw")} for r in lst]
json.dump(summary, open(sys.argv[1], "w"), indent=1)
json.dump(entries, open(sys.argv[2], "w"), indent=0)
print(json.dumps({c: {k: (v["median"] if isinstance(v, dict) and "median" in v else v) for k, v in s.items() if not k.startswith("shaper")} for c, s in summary.items()}, indent=0))
