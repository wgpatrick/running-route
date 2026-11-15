import json, re, os, sys, collections
hits = json.load(open("gh/hits.json"))
rows = []
seen = set()
for m, lst in hits.items():
    for repo, path, sha in lst:
        if sha in seen: continue
        seen.add(sha)
        try: t = open(f"gh/files/{sha}.txt", errors="replace").read()
        except Exception: continue
        def sect(name):
            mm = re.search(r"^\[" + re.escape(name) + r"\]\s*$(.*?)(?=^\[|^#\*# <-|\Z)", t, re.M | re.S)
            return mm.group(1) if mm else ""
        def val(s, key):
            mm = re.search(r"^\s*" + key + r"\s*[:=]\s*([-\d.]+)", s, re.M)
            return float(mm.group(1)) if mm else None
        def sval(s, key):
            mm = re.search(r"^\s*" + key + r"\s*[:=]\s*(\w+)", s, re.M)
            return mm.group(1).lower() if mm else None
        saved = "\n".join(l[3:] for l in t.splitlines() if l.startswith("#*#"))
        def ssect(name):
            mm = re.search(r"^\s*\[" + re.escape(name) + r"\]\s*$(.*?)(?=^\s*\[|\Z)", saved, re.M | re.S)
            return mm.group(1) if mm else ""
        ish, sish = sect("input_shaper"), ssect("input_shaper")
        r = {"machine_query": m, "repo": repo, "path": path, "url": f"https://github.com/{repo}/blob/HEAD/{path}"}
        for ax in "xy":
            sv, cv = val(sish, f"shaper_freq_{ax}"), val(ish, f"shaper_freq_{ax}")
            r[f"f{ax}"] = sv if sv is not None else cv
            r[f"t{ax}"] = (sval(sish, f"shaper_type_{ax}") or sval(sish, "shaper_type")) if sv is not None else (sval(ish, f"shaper_type_{ax}") or sval(ish, "shaper_type"))
            r[f"saved_{ax}"] = sv is not None
            r[f"pos_max_{ax}"] = val(sect(f"stepper_{ax}"), "position_max")
            cur = None
            for drv in ("tmc2209", "tmc2208", "tmc5160", "tmc2130", "tmc2240", "tmc2226", "tmc2225"):
                cur = cur or val(sect(f"{drv} stepper_{ax}"), "run_current")
            r[f"run_current_{ax}"] = cur
        pr = sect("printer")
        r["kinematics"] = sval(pr, "kinematics"); r["max_accel"] = val(pr, "max_accel"); r["max_velocity"] = val(pr, "max_velocity")
        low = (t + " " + repo + " " + path).lower()
        r["kw"] = [k for k in ("trident", "v0.2", "v0.1", "voron 0", "voron0", "v0", "ender", "ender 3 v3", "ender-3 v3", "ender3 v3", "v3 se", "v3 ke", "s1", "neo", "sprite", "direct drive", "tri-zero", "tri zero", "salad", "micron", "v2.4", "voron2", "switchwire", "glass", "linear rail", "mgn", "stealthburner", "dragon burner", "mini stealth", "afterburner", "adxl", "resonance_tester", "awd", "9mm", "tap", "kirigami", "boop", "cr-10", "cr10", "sovol", "anycubic", "elegoo", "artillery", "kingroon", "biqu", "voxelab", "aquila", "max neo", "ender 5", "ender5", "ender 6", "ender-5", "ender 7", "v3 plus", "nebula", "2040") if k in low]
        rows.append(r)
json.dump(rows, open("gh/parsed.json", "w"), indent=0)
ok = [r for r in rows if r["fx"] and r["fy"]]
print(len(rows), len(ok))
c = collections.Counter((r["machine_query"], r["kinematics"], r["pos_max_x"]) for r in ok)
for k, v in sorted(c.items(), key=lambda kv: -kv[1])[:40]: print(k, v)
