"""Minimal reproductions of the checker findings on the reference machine that I classify as false alarms.
Run: .venv/bin/python <this file>      (reads mechloop, writes nothing)"""
from build123d import Box, Cylinder, Location, Plane, Pos, Rot

from mechloop import Design
from mechloop.parts import add_screw, clearance_hole, nema17, place
from mechloop.parts.electrical import psu_lrs
from mechloop.runner import verify


def show(title, d, only, codes):
    rep = verify(d, only=only)
    print(f"\n=== {title}")
    fs = [f for r in rep.results for f in r.findings]
    for f in fs:
        if f.code in codes:
            print(f"  [{f.severity}] {f.code}: {f.message[:230]}")
    if not any(f.code in codes for f in fs):
        print("  (no such finding)")


# ---- A1: a printed motor mount with four M3 clearance holes on the NEMA 17's 31 mm square --------------------
# Rat Rig's published x_motor_cage / y_motor_cage / z_motor_cage STEP files have exactly this: four 3.3 mm holes.
for dia in (3.4, 3.3):
    d = Design(f"a1_{dia}", base="mount")
    m = place(d, "motor", nema17(40), Location((0, 0, 0)))
    plate = Pos(0, 0, 3) * Box(50, 50, 6) - Pos(0, 0, 3) * Cylinder(11.5, 6)
    for hx, hy, hz in m.meta["interfaces"]["mount_holes_m3"]:
        plate -= Pos(hx, hy, 3) * Cylinder(dia / 2, 6)
    d.add("mount", plate, material="petg", process="printed")
    for i, (hx, hy, hz) in enumerate(m.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"s{i}", "M3", 10, at=(hx, hy, 6), threads_into="motor", clamps=("mount",))
    show(f"A1 printed NEMA 17 mount, four {dia} mm holes (tolerance)", d, ["tolerance"], {"screws_may_not_align"})

# ---- A2: Mean Well LRS-350 on a 4 mm panel by its bottom holes ("4-M4 L=3mm": at most 3 mm of screw inside) -----
for length in (6, 8):
    d = Design(f"a2_{length}", base="panel")
    p = place(d, "psu", psu_lrs("LRS-350-24"), Location((0, 0, 0)))
    panel = Pos(0, 0, -2) * Box(230, 130, 4)
    for hx, hy, hz in p.meta["interfaces"]["mount_holes_m4"]:
        panel -= Pos(hx, hy, -2) * Cylinder(clearance_hole("M4") / 2, 4)
    d.add("panel", panel, material="al6061", process="sheet")
    for i, (hx, hy, hz) in enumerate(p.meta["interfaces"]["mount_holes_m4"]):
        add_screw(d, f"s{i}", "M4", length, at=(hx, hy, -4), direction=(0, 0, 1), threads_into="psu", clamps=("panel",))
    show(f"A2 LRS-350 on a 4 mm panel with M4 x {length} (interference)", d, ["interference"], {"thread_engagement", "thread_bottoms_out"})

# ---- A3: a machine and a free-standing box on the same bench ----------------------------------------------------
d = Design("a3", base="frame")
d.add("frame", Box(100, 100, 20), material="al6061")
d.add("box", Pos(200, 0, 0) * Box(60, 60, 20), material="al6061")
show("A3 two free-standing units in one design (interference)", d, ["interference"], {"floating_parts", "unfastened"})

# ---- A4 (no synthetic reproduction found): the printed-part wall check on Rat Rig's real printed parts.
# Run instead:  cd <scratch>/scripts && python -I -m mechloop verify real_printed_parts.py --only manufacture --no-render --out <scratch>/out_real
# (real_printed_parts.py loads the published STEP files from a clone of github.com/Rat-Rig/V-Minion; a plain 30 degree
# wedge on a block does NOT trigger the finding, so sharp edges alone are not the cause.)
