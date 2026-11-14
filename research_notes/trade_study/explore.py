"""Helper: list parts of an extracted assembly JSON. Usage: explore.py <json> [regex] [max]"""
import json, sys, re, collections
import numpy as np
d = json.load(open(sys.argv[1]))
L = d["leaves"]
rx = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
mx = int(sys.argv[3]) if len(sys.argv) > 3 else 60
bb = np.array([l["bbox"] for l in L])
print("leaves", len(L), "overall", bb[:, :3].min(0).round(1), bb[:, 3:].max(0).round(1), "size", (bb[:, 3:].max(0) - bb[:, :3].min(0)).round(1))
groups = collections.defaultdict(list)
for l in L:
    key = "/".join(l["path"][-2:])
    if rx is None or rx.search("/".join(l["path"])):
        groups[key].append(l)
for key, ls in sorted(groups.items(), key=lambda kv: -kv[1][0]["vol"])[:mx]:
    l = ls[0]
    b = l["bbox"]
    print(f"{len(ls):3d} {key[:70]:70s} size {[round(b[i+3]-b[i],1) for i in range(3)]} min {[round(x) for x in b[:3]]} vol {l['vol']/1000:.1f}cm3")
