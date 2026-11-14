"""Same-scale side views (looking along X) of each machine's bed and Z arrangement.

Every rectangle is the bounding box of a real solid in that machine's CAD (STEP for the references,
mech-ai/viewer/data.json for ours). Usage:
  python draw_side_views.py <dir with extract_step JSON> <mech-ai/viewer/data.json> <out.png>
"""
import json, os, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from asm import load, sel
from measure_assemblies import CFG

src, ours_json, out = sys.argv[1:4]
INK, MUTED, SURF, FRAME = "#0b0b0b", "#52514e", "#fcfcfb", "#b9b8b2"
COL = dict(bed="#2a78d6", guide="#eb6834", drive="#1baf7a", tool="#eda100")     # palette slots 1-4, fixed order
LAB = dict(bed="bed plate", guide="Z guide rails", drive="Z drive or support point", tool="toolhead")

panels = []
for key in ("voron0", "k3", "trident", "voron24", "ender3"):
    c = CFG.get(key)
    if not c or not os.path.exists(os.path.join(src, c["file"])):
        continue
    L = load(os.path.join(src, c["file"]))
    up = c["up"]
    dep = 1 if up == 2 else 2
    def boxes(rx, minvol=500, vertical_only=False, not_rx=None):
        r = []
        for l in sel(L, rx, minvol, not_rx):
            b = l["bbox"]
            s = [b[i + 3] - b[i] for i in range(3)]
            if vertical_only and s.index(max(s)) != up:
                continue
            r.append((b[dep], b[up], b[dep + 3] - b[dep], b[up + 3] - b[up]))
        return r
    panels.append((c["label"] + "\n" + c["arch"], dict(
        frame=boxes(c["frame"], 2000), bed=boxes(c["bed"]), guide=boxes(c["rails"], 1000, True),
        drive=boxes(c["zscrew"], 1000), tool=boxes(c["toolhead"], 1500))))

d = json.load(open(ours_json))
P = {p["name"]: p["bbox"] for p in d["parts"]}
def ob(rx):
    return [(b[1], b[2], b[4] - b[1], b[5] - b[2]) for n, b in P.items() if re.search(rx, n)]
panels.insert(0, ("Ours: printer_v4\ncartesian, bed moves in Z on 1 screw", dict(
    frame=ob(r"^(frame_|post_|upright_|x_beam)"), bed=ob(r"^bed$"), guide=ob(r"^z_rail_(left|right)$"),
    drive=ob(r"^leadscrew$"), tool=ob(r"^(tool_plate|hotend|extruder)$"))))

n = len(panels)
cols = 3
rows = (n + cols - 1) // cols
fig, axes = plt.subplots(rows, cols, figsize=(cols * 3.3, rows * 3.6), dpi=110, facecolor=SURF)
for ax in axes.flat:
    ax.set_visible(False)
for ax, (title, g) in zip(axes.flat, panels):
    ax.set_visible(True)
    ax.set_facecolor(SURF)
    allb = [b for k in g for b in g[k]]
    x0 = min(b[0] for b in g["frame"]); x1 = max(b[0] + b[2] for b in g["frame"])
    y0 = min(b[1] for b in g["frame"])
    for b in g["frame"]:
        ax.add_patch(Rectangle((b[0] - x0, b[1] - y0), b[2], b[3], fc=FRAME, ec=SURF, lw=0.5))
    for k in ("guide", "drive", "bed", "tool"):
        for b in g[k]:
            ax.add_patch(Rectangle((b[0] - x0, b[1] - y0), max(b[2], 3), max(b[3], 3), fc=COL[k], ec=COL[k] if k == "bed" else SURF, lw=0.6,
                                   alpha=0.95))
    ax.set_xlim(-60, 520); ax.set_ylim(-140, 560)
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.tick_params(colors=MUTED, labelsize=7, length=2)
    for s in ax.spines.values():
        s.set_color("#dddcd6")
    ax.set_xticks([0, 200, 400]); ax.set_yticks([0, 200, 400])
    ax.grid(color="#eceBe6".lower(), lw=0.5); ax.set_axisbelow(True)
handles = [Rectangle((0, 0), 1, 1, fc=COL[k]) for k in COL] + [Rectangle((0, 0), 1, 1, fc=FRAME)]
fig.legend(handles, [LAB[k] for k in COL] + ["frame extrusions"], loc="lower center", ncol=5, frameon=False, fontsize=8,
           labelcolor=INK)
fig.suptitle("Side views at one scale (mm): where the bed sits relative to what holds and lifts it", fontsize=10,
             color=INK, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0.04, 1, 0.96))
fig.savefig(out, facecolor=SURF)
print(out, os.path.getsize(out))
