import json, subprocess, sys, time, base64, re, os
out = sys.argv[1]
queries = {
 "voron0": ["shaper_freq_x V0.2 corexy", "shaper_freq_x \"Voron 0\" corexy", "shaper_freq_x \"V0\" \"position_max: 120\"", "shaper_freq_x voron0 corexy", "shaper_freq_x \"V0.2\" filename:printer.cfg"],
 "trident": ["shaper_freq_x Trident corexy", "shaper_freq_x \"Voron Trident\"", "shaper_freq_x Trident \"position_max: 250\"", "shaper_freq_x trident filename:printer.cfg"],
 "ender3": ["shaper_freq_x \"Ender 3\" cartesian", "shaper_freq_x ender3 cartesian", "shaper_freq_x \"Ender-3\" \"position_max: 235\"", "shaper_freq_x \"ender 3 pro\"", "shaper_freq_x \"Ender 3 V2\" cartesian"],
}
hits = {}
for mach, qs in queries.items():
    for q in qs:
        for page in (1, 2):
            r = subprocess.run(["gh", "api", "-X", "GET", "search/code", "-f", f"q={q}", "-f", "per_page=50", "-f", f"page={page}"], capture_output=True, text=True)
            if r.returncode != 0:
                print("ERR", q, r.stderr[:200]); time.sleep(20); continue
            items = json.loads(r.stdout).get("items", [])
            for it in items:
                hits.setdefault(mach, {})[(it["repository"]["full_name"], it["path"])] = it["sha"]
            print(mach, q, page, len(items), flush=True)
            time.sleep(7)
            if len(items) < 50: break
json.dump({m: [[a, b, s] for (a, b), s in v.items()] for m, v in hits.items()}, open(out, "w"), indent=1)
