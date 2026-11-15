import json, numpy as np, collections
rows = [r for r in json.load(open("gh/parsed.json")) if r["fx"] and r["fy"]]
def cls(r):
    kw, px, kin = set(r["kw"]), r["pos_max_x"] or 0, r["kinematics"]
    other = {"cr-10","cr10","sovol","anycubic","elegoo","artillery","kingroon","biqu","voxelab","aquila","ender 5","ender5","ender-5","ender 6","ender 7","switchwire"}
    if kin == "corexy" and 115 <= px <= 125 and not kw & {"tri-zero","tri zero","salad","micron","trident"} and kw & {"v0","voron0","voron 0","v0.1","v0.2"}:
        return "voron0"
    if kin == "corexy" and "trident" in kw and not kw & {"v2.4","voron2"}:
        for lo, hi, n in ((240, 262, "trident250"), (290, 312, "trident300"), (340, 362, "trident350")):
            if lo <= px <= hi: return n
    if kin == "cartesian" and 218 <= px <= 252 and "ender" in kw and not kw & other:
        if kw & {"ender 3 v3","ender-3 v3","ender3 v3","v3 se","v3 ke","nebula","v3 plus"}: return "ender3_v3_family"
        if kw & {"s1","sprite"}: return "ender3_s1_or_sprite"
        return "ender3"
    return None
out = collections.defaultdict(list)
for r in rows:
    c = cls(r)
    if c: r["class"] = c; out[c].append(r)
res = {}
for c, lst in sorted(out.items()):
    # one entry per repository and per distinct (fx, fy): forks and copies of the same file count once
    uniq = {}
    for r in lst:
        uniq.setdefault((r["fx"], r["fy"]), r)
    byrepo = {}
    for r in uniq.values():
        byrepo.setdefault(r["repo"].split("/")[0] + str(r["fx"]) , r)
    u = list(uniq.values())
    # drop placeholder-looking pairs: both axes identical round numbers (template defaults)
    u2 = [r for r in u if not (r["fx"] == r["fy"] and float(r["fx"]).is_integer())]
    fx, fy = np.array([r["fx"] for r in u2]), np.array([r["fy"] for r in u2])
    sv = [r for r in u2 if r["saved_x"] or r["saved_y"]]
    def q(a): return [round(float(np.percentile(a, p)), 1) for p in (10, 25, 50, 75, 90)] if len(a) else None
    print(f"{c}: files {len(lst)}, distinct pairs {len(u)}, kept {len(u2)}, auto-saved {len(sv)}")
    print("   fx p10/25/50/75/90", q(fx), " fy", q(fy))
    if sv: print("   auto-saved only: fx", q(np.array([r['fx'] for r in sv])), " fy", q(np.array([r['fy'] for r in sv])))
    acc = np.array([r["max_accel"] for r in u2 if r["max_accel"]])
    print("   max_accel p10/25/50/75/90", q(acc), " run_current_x", q(np.array([r['run_current_x'] for r in u2 if r['run_current_x']])))
    print("   types x", dict(collections.Counter(r["tx"] for r in u2)), " y", dict(collections.Counter(r["ty"] for r in u2)))
    res[c] = u2
json.dump(res, open("gh/classified.json", "w"), indent=0)
