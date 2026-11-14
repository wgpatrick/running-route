"""Plan views at one scale: the bed plate and the points that guide and lift it (or the gantry).

Positions come from measurements.json (STEP bounding-box centres, relative to the bed centre).
Usage: python draw_plan_views.py measurements.json out.png
"""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon

M = json.load(open(sys.argv[1]))
INK, MUTED, SURF = "#0b0b0b", "#52514e", "#fcfcfb"
BED, GUIDE, DRIVE = "#2a78d6", "#eb6834", "#1baf7a"      # palette slots 1-3 (validated), fixed roles
o = M["ours"]
panels = [("Ours: 220 mm plate\n1 screw + 2 rails, all behind the bed", o["bed_plate_mm"]["value"][:2],
           [[-90, o["bed_centre_to_z_rail_plane_mm"]["value"]], [90, o["bed_centre_to_z_rail_plane_mm"]["value"]]],
           [[0, o["leadscrew_behind_bed_centre_mm"]["value"]]])]
for key, sub in (("voron0", "1 screw + 2 rails behind the bed"), ("k3", "3 belts + 3 rails around the bed"), ("trident", "3 screws + 3 rails around the bed"),
                 ("voron24", "bed fixed; 4 belts + 4 rails lift gantry")):
    m = M[key]
    b = m["bed_plate_mm"]["value"]
    panels.append((f"{m['label']}: {b['a']:.0f} mm plate\n{sub}", [b["a"], b["b"]],
                   m["z_rail_positions_rel_bed_centre_mm"]["value"], m["z_drive_positions_rel_bed_centre_mm"]["value"]))
fig, axes = plt.subplots(1, len(panels), figsize=(2.9 * len(panels), 3.9), dpi=110, facecolor=SURF)
for ax, (title, bed, rails, drives) in zip(axes, panels):
    ax.set_facecolor(SURF)
    flip = -1 if "K3" in title else 1          # the K3 CAD has its depth axis pointing forward
    if len(drives) >= 3:
        pts = sorted([[p[0], p[1] * flip] for p in drives], key=lambda p: __import__("math").atan2(p[1], p[0]))
        ax.add_patch(Polygon(pts, closed=True, fc="none", ec=DRIVE, lw=1.2, ls=(0, (4, 3))))
    ax.add_patch(Rectangle((-bed[0] / 2, -bed[1] / 2), bed[0], bed[1], fc=BED, ec=SURF, alpha=0.9))
    ax.plot([p[0] for p in rails], [p[1] * flip for p in rails], "s", ms=8, mfc=GUIDE, mec=SURF, mew=1.5)
    ax.plot([p[0] for p in drives], [p[1] * flip for p in drives], "o", ms=9, mfc=DRIVE, mec=SURF, mew=1.5)
    ax.plot(0, 0, "+", ms=8, color=SURF, mew=1.5)
    ax.set_xlim(-250, 250); ax.set_ylim(-200, 280); ax.set_aspect("equal")
    ax.set_title(title, fontsize=8.5, color=INK, loc="left")
    ax.tick_params(colors=MUTED, labelsize=7, length=2)
    ax.set_xticks([-200, 0, 200]); ax.set_yticks([-100, 0, 100, 200])
    for s in ax.spines.values():
        s.set_color("#dddcd6")
    ax.grid(color="#ecebe6", lw=0.5); ax.set_axisbelow(True)
axes[0].set_ylabel("mm, rear of machine up", fontsize=7.5, color=MUTED)
h = [Rectangle((0, 0), 1, 1, fc=BED), plt.Line2D([], [], marker="s", ls="", mfc=GUIDE, mec=SURF, ms=8),
     plt.Line2D([], [], marker="o", ls="", mfc=DRIVE, mec=SURF, ms=9)]
fig.legend(h, ["bed plate", "Z guide rail", "Z drive or support point"], loc="lower center", ncol=3, frameon=False, fontsize=8)
fig.suptitle("Plan views at one scale: what holds the bed (or the gantry) and where", fontsize=10, color=INK, x=0.02, ha="left")
fig.tight_layout(rect=(0, 0.06, 1, 0.94))
fig.savefig(sys.argv[2], facecolor=SURF)
