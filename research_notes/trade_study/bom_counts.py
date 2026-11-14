"""Count fasteners, printed parts and motion parts from the BOM files published in the reference repos.

Usage: python -I bom_counts.py <scratch tradestudy dir> <out.json>
Sources are CSV / Markdown BOMs in the cloned repos (data only).
"""
import csv, json, re, sys, os, glob

root, out = sys.argv[1], sys.argv[2]
FAST = re.compile(r"screw|nut\b|t-nut|washer|shim|bolt|grub|M\d+n|M\d+x\d+|dowel|spacer", re.I)
res = {}


def ratrig(path, kits):
    """Rat Rig CSVs are a list of kits; expand the named kits (a kit line may reference another kit by SKU)."""
    rows, cur, kit = {}, None, {}
    for r in csv.reader(open(path, encoding="utf-8", errors="replace")):
        if len(r) >= 5 and r[1].startswith("HW") and r[0] == "" and r[4]:
            cur = r[1]
            kit[cur] = r[4]
            rows[cur] = []
        elif cur and len(r) >= 5 and r[0].strip().isdigit():
            rows[cur].append((int(r[0]), r[1], r[2], r[4]))
    items = []

    def expand(sku, mult=1):
        for q, s, length, name in rows.get(sku, []):
            if s in rows and s != sku:
                expand(s, mult * q)
            else:
                items.append((q * mult, name, length))
    for k in kits:
        expand(k)
    fast = [(q, n) for q, n, _ in items if FAST.search(n) and "lead" not in n.lower()]
    return dict(source=os.path.relpath(path, root), kits={k: kit.get(k) for k in kits},
                line_items=len(items), total_items=sum(q for q, _, _ in items),
                fasteners=sum(q for q, _ in fast), fastener_types=len({n for _, n in fast}),
                extrusions=[(q, n.split(" - ")[0], l) for q, n, l in items if "SLOT" in n],
                rails=[(q, n) for q, n, _ in items if "Linear Rail" in n],
                lead_screws=[(q, n) for q, n, _ in items if "Lead Screw -" in n],
                belts=[(q, n, l) for q, n, l in items if "Timing Belt" in n],
                plates=[(q, n) for q, n, _ in items if re.search(r"plate|PLATE", n)],
                method="from BOM")


p = os.path.join(root, "Rat-Rig_V-Core-3/repo/docs/src/bom/vcore31_bom.csv")
res["ratrig_vcore31_200"] = ratrig(p, ["HW3009MK"])
p = os.path.join(root, "Rat-Rig_V-Minion/repo/docs/src/bom/vminion_20042023_1212.csv")
res["ratrig_vminion"] = ratrig(p, ["HW2856GK"])

# Prusa MINI: Markdown tables per axis
mini = {"printed": 0, "fasteners": 0, "fastener_types": set(), "standard": [], "custom": []}
for f in sorted(glob.glob(os.path.join(root, "prusa3d_Original-Prusa-MINI/repo/BOM/*.md"))):
    sec = None
    for line in open(f, encoding="utf-8", errors="replace"):
        m = re.match(r"\*\*(.+?)\*\*", line.strip())
        if m:
            sec = m.group(1)
            continue
        m = re.match(r"\|(.+?)\|\s*(\d+)\s*\|", line)
        if not m or sec is None:
            continue
        name, q = re.sub(r"\[(.+?)\]\(.*?\)", r"\1", m.group(1)).strip(), int(m.group(2))
        if sec.startswith("PRINTED"):
            mini["printed"] += q
        elif sec.startswith("FASTENERS"):
            mini["fasteners"] += q
            mini["fastener_types"].add(name)
        elif sec.startswith("STANDARD"):
            mini["standard"].append((q, name, os.path.basename(f)))
        elif sec.startswith("CUSTOM"):
            mini["custom"].append((q, name, os.path.basename(f)))
mini["fastener_types"] = len(mini["fastener_types"])
mini["source"] = "prusa3d_Original-Prusa-MINI/repo/BOM/*.md"
mini["method"] = "from BOM"
res["prusa_mini"] = mini
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1)[:6000])
