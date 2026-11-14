"""Count part instances in a STEP assembly from its product structure alone (text level, no geometry).

Usage: python -I step_product_tree.py <lines.txt> <out.json>
<lines.txt> holds the PRODUCT, PRODUCT_DEFINITION_FORMATION, PRODUCT_DEFINITION and
NEXT_ASSEMBLY_USAGE_OCCURRENCE lines of the STEP file (grep them out first). Fallback for assemblies that are
too slow to transfer through OpenCASCADE; gives names and counts, not dimensions.
"""
import collections, json, re, sys
prod, pdf, pd, kids = {}, {}, {}, collections.defaultdict(list)
for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
    m = re.match(r"#(\d+) *= *([A-Z_]+) *\((.*)\) *;", line.strip())
    if not m:
        continue
    i, kind, body = int(m.group(1)), m.group(2), m.group(3)
    refs = [int(x) for x in re.findall(r"#(\d+)", body)]
    if kind == "PRODUCT":
        prod[i] = re.match(r" *'((?:[^']|'')*)'", body).group(1)
    elif kind.startswith("PRODUCT_DEFINITION_FORMATION"):
        pdf[i] = refs[0]
    elif kind == "PRODUCT_DEFINITION":
        pd[i] = refs[0]
    elif kind == "NEXT_ASSEMBLY_USAGE_OCCURRENCE":
        kids[refs[0]].append(refs[1])
name = {d: prod.get(pdf.get(f), "?") for d, f in pd.items()}
children = {c for cs in kids.values() for c in cs}
roots = [d for d in pd if d not in children]
count = collections.Counter()
def walk(d, mult):
    if d not in kids:
        count[name[d]] += mult
        return
    for c, n in collections.Counter(kids[d]).items():
        walk(c, mult * n)
for r in roots:
    walk(r, 1)
json.dump(dict(roots=[name[r] for r in roots], leaf_instances=sum(count.values()), unique_leaf_parts=len(count),
               counts=dict(count.most_common())), open(sys.argv[2], "w"), indent=1)
print("roots", [name[r] for r in roots][:5], "leaf instances", sum(count.values()), "unique", len(count))
