"""Build the showcase page for a printer design: showcase/index.html plus pictures and data beside it.

    .venv/bin/python tools/build_showcase.py designs/printer_v8.py [--only renders fea page] [--refresh]

Stages (all run by default; each writes what the next reads, so one can be re-run alone):
  renders  pictures of the design's own model with callout points      -> showcase/img/*.webp, showcase/data/renders.json
  fea      the bed-support FEA re-run with the displacement field kept  -> showcase/img/fea_*.webp, showcase/data/fea_fields.json
  page     every number is read from report/score/tune/print files      -> showcase/data/facts.json, showcase/index.html

Numbers are never typed here. They come from out/<design>/report.json, scores.jsonl, score/, tune/, fil/, from the
other versions' files under out/, and from small extracts kept in showcase/data/inputs/ (reports of v6, v7 and the
bed-study variants under the current checks, which live in scratch folders that do not last). `--refresh` re-makes
those extracts from the folders named in INPUT_SOURCES when they exist. The few figures that exist only as prose in
docs/*.md are parsed from the documents by pattern and labelled "documented" on the page.

Nothing under mechloop/ is edited. The FEA stage calls mechloop's own bed-support solver and only keeps the field
it would otherwise delete.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
SHOW = ROOT / "showcase"
IMG = SHOW / "img"
DATA = SHOW / "data"

ELEC = ("electronics_tray", "tray_bolt", "inlet", "earth", "psu", "control_board", "host")


# --------------------------------------------------------------------------------------------- renders

def part_groups(sc) -> dict:
    g: dict = {}
    for n, c in sc.comps.items():
        if n.startswith(ELEC):
            k = "electronics"
        elif c.body == "xbody":
            k = "toolhead"
        elif c.body == "ybody":
            k = "gantry"
        elif c.body == "zbody":
            k = "bed"
        elif n.startswith(("z_", "leadscrew", "upright", "brkt_up")):
            k = "zdrive"
        elif n.startswith("y_"):
            k = "ydrive"
        else:
            k = "frame"
        g.setdefault(k, set()).add(n)
    return g


def _bb(c):
    b = c.shape.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z])


def model_facts(design) -> dict:
    """Dimensions read off the model itself (used in callouts and in the probe map)."""
    C = {c.name: c for c in design.components}
    tp = np.array(design.tool_point[1], dtype=float)
    f = {"nozzle": tp.tolist(), "envelope_mm": list(design.envelope) if design.envelope else None}
    if "bed_probe" in C:
        lo, hi = _bb(C["bed_probe"])
        f["probe_centre"] = [float((lo[0] + hi[0]) / 2), float((lo[1] + hi[1]) / 2), float(lo[2])]
        f["probe_offset_mm"] = [round(f["probe_centre"][0] - tp[0], 2), round(f["probe_centre"][1] - tp[1], 2)]
        f["probe_face_above_nozzle_mm"] = round(float(lo[2] - tp[2]), 2)
        f["probe_diameter_mm"] = round(float(hi[0] - lo[0]), 1)
    for n in ("bed", "bed_plate", "bed_magnet"):
        if n in C:
            lo, hi = _bb(C[n])
            f[n + "_box"] = [lo.round(2).tolist(), hi.round(2).tolist()]
    f["joints"] = {j.name: [float(j.range[0]), float(j.range[1])] for j in design.joints}
    f["print_area"] = list((design.printer or {}).get("print_area") or [])
    f["belts"] = {b.name: float(getattr(b, "width", 0) or 0) for b in design.belts}
    lo = np.min([_bb(c)[0] for c in design.components], axis=0)
    hi = np.max([_bb(c)[1] for c in design.components], axis=0)
    f["bbox_mm"] = (hi - lo).round(1).tolist()
    return f


def view_defs(sc, mf: dict) -> dict:
    """Cameras, what is shown and the callouts of every picture. Callout text is plain language; where it carries a
    number the number is taken from the model (mf) at build time."""
    g = part_groups(sc)
    A = set(sc.comps)

    def pre(*p):
        return {n for n in A if n.startswith(p)}

    ext = {n for n in A if sc.cls[n] == "extrusion"}
    ghost_frame = (g["frame"] & ext) | {"electronics_tray"}
    V = {}
    V["hero"] = dict(
        q={"x": 20, "y": -30, "z": 110}, show=A, size=(1500, 1120),
        camera={"pos": (830, -1060, 800), "focal": (0, 0, 222), "angle": 24},
        callouts=[
            ("Toolhead: E3D Roto extruder and Revo hotend, hung behind the X beam", ["extruder"]),
            ("X beam, a 2020 extrusion with one MGN12 rail", ["x_beam"]),
            ("Y motor, one each side, on a sheet-steel mount", ["y_motor"]),
            ("Bed: steel print sheet on a magnet on a cast aluminium plate", ["bed"]),
            ("Lead screw, one of three, top end free", ["leadscrew_fr"]),
            ("Bed carrier: front plate ties the two arms", ["front_plate"]),
            ("Z motor: the only one, beside the rear screw", ["z_motor"]),
            ("Power supply on the electronics tray", ["psu"]),
            ("Frame of 2020 extrusion; the front top rail sits lower so the X beam passes over it", ["frame_top_front"]),
        ])
    zs = g["bed"] | g["zdrive"] | pre("z_pedestal")
    plate_stack = {"bed", "bed_magnet", "bed_plate", "bed_heater", "bed_tco"}
    V["bed_top"] = dict(
        q={"x": 0, "y": 0, "z": 110}, show=zs - plate_stack, ghost=ghost_frame | {"bed_plate"},
        size=(1500, 1120), belt_names={"z_belt"},
        camera={"pos": (-600, -920, 860), "focal": (0, 30, 180), "angle": 25},
        callouts=[
            ("Flexure post: an M5 screw from the plate down to a tab, two nuts at the tab set the level", ["bed_post_2", "bed_post_3", "bed_post_0", "bed_post_1"]),
            ("Laser-cut steel tab bolted on the arm", ["bed_post_tab_2", "bed_post_tab_3", "bed_post_tab_0", "bed_post_tab_1"]),
            ("Rear tie: a flat steel strip that locates the plate in X, Y and yaw and is soft vertically", ["bed_tie"]),
            ("Arm, 2020 extrusion", ["bed_arm_left"]),
            ("Back plate, 5 mm aluminium, on the two guide blocks", ["back_plate"]),
            ("Front plate, 3 mm steel, across the arms' front ends", ["front_plate"]),
            ("Printed nut block with a floating nut, one per screw", ["nut_block_fl"]),
            ("Front lead screws, over the bottom side rails", ["leadscrew_fl"]),
            ("Rear lead screw", ["leadscrew"]),
            ("One guide block per rail", ["z_carriage_left_hi"]),
            ("Z rail on the rear upright", ["z_rail_right"]),
            ("Closed belt round all three screws (black)", ["z_pulley_fr"]),
        ])
    V["bed_low"] = dict(
        q={"x": 0, "y": 0, "z": 110}, show=zs, ghost=ghost_frame, size=(1500, 1000), belt_names={"z_belt"},
        camera={"pos": (-740, -910, 250), "focal": (0, 30, 165), "angle": 24},
        callouts=[
            ("Printed pedestal holding two 608 bearings; the screw stands in them", ["z_pedestal_fl"]),
            ("20-tooth pulley fixed to the screw; its hub rests on the upper bearing and carries the bed's weight", ["z_pulley_fl"]),
            ("Z motor under the rear mount", ["z_motor"]),
            ("Toothed idler in a slot: the belt tensioner", ["z_idler"]),
            ("Rear drive mount, printed: bearings for the rear screw, motor and tensioner", ["z_drive_mount"]),
            ("8 mm cast plate", ["bed_plate"]),
            ("Lead screw: its top ends below the top rails and nothing holds it", ["leadscrew_fr"]),
        ])
    th = g["toolhead"]
    bed3 = {"bed", "bed_magnet", "bed_plate"}
    V["toolhead"] = dict(
        q={"x": 0, "y": 0, "z": 172}, show=th | {"x_rail", "x_beam"} | pre("x_rail_screw") | bed3,
        size=(1500, 1120), belt_names=set(),
        camera={"pos": (-235, 268, 368), "focal": (6, 34, 400), "angle": 19},
        callouts=[
            ("E3D Roto extruder", ["extruder"]),
            ("E3D Revo hotend", ["hotend"]),
            ("M12 inductive probe (OMRON E2E-X5ME1)", ["bed_probe"]),
            ("The probe's own two nuts clamp it in a closed hole", ["bed_probe_nut_front", "bed_probe_nut_rear"]),
            ("Printed probe mount, held by the extruder's own two screws", ["probe_mount"]),
            ("Part-cooling fan", ["part_fan"]),
            ("Printed duct", ["part_duct"]),
            ("Machined tool plate on the X guide block", ["tool_plate"]),
            ("Printed belt block", ["x_belt_block"]),
            ("X rail on the beam", ["x_rail"]),
            ("Steel print sheet: the probe's target", ["bed"]),
        ])
    nz = np.array(mf["nozzle"]) + np.array([0, 0, 172.0 - 172.0])
    V["toolhead_side"] = dict(
        q={"x": 0, "y": 0, "z": 172}, show=th | {"x_rail", "x_beam"} | pre("x_rail_screw") | bed3,
        size=(1300, 900), belt_names=set(),
        camera={"pos": (-600, 32, 398), "focal": (0, 32, 398), "parallel_scale": 52},
        marks={"nozzle": nz, "probe": mf.get("probe_centre", nz),
               "bed_under_nozzle": [nz[0], nz[1], mf["bed_box"][1][2] + 172.0],
               "bed_under_probe": [nz[0], mf.get("probe_centre", nz)[1], mf["bed_box"][1][2] + 172.0]},
        callouts=[])
    gy = g["gantry"] | g["toolhead"] | g["ydrive"] | pre("frame_top")
    V["gantry"] = dict(
        q={"x": 30, "y": -20, "z": 110}, show=gy, ghost=ghost_frame - pre("frame_top"), size=(1500, 1000),
        belt_names={"x_belt", "y_belt", "y_belt_l"},
        camera={"pos": (-600, -860, 1010), "focal": (0, 0, 380), "angle": 21},
        callouts=[
            ("Y plate, laser-cut steel: carries the beam end on a Y guide block", ["y_plate_left"]),
            ("X beam", ["x_beam"]),
            ("X rail and its guide block", ["x_rail"]),
            ("X motor, rides on the left Y plate", ["x_motor"]),
            ("Y motor", ["y_motor_l"]),
            ("Y motor mount, 2 mm steel sheet, slides on T-nuts to tension the belt", ["y_motor_mount_l"]),
            ("Y rail on the top side rail", ["y_rail_left"]),
            ("Y idler on an L-shaped mount beyond the frame's front end", ["y_idler_mount_l"]),
            ("Y endstop on a sliding mount; the right Y plate's rear edge presses it", ["y_endstop_mount"]),
            ("Right Y plate", ["y_plate_right"]),
            ("Printed tension anchor with an M3 jack screw", ["y_tension_anchor_l"]),
        ])
    V["gantry_corner"] = dict(
        q={"x": 30, "y": 20, "z": 110}, show=gy, size=(1300, 900), belt_names={"x_belt", "y_belt", "y_belt_l"},
        camera={"pos": (430, 480, 610), "focal": (150, 150, 432), "angle": 23},
        callouts=[
            ("Y motor", ["y_motor"]),
            ("Pulley with its hub outboard, so the belt runs close to the motor face", ["y_pulley"]),
            ("Mount in 2 mm steel sheet", ["y_motor_mount"]),
            ("Y endstop switch", ["y_endstop"]),
            ("Its mount slides along the rail on two T-nuts", ["y_endstop_mount"]),
            ("Right Y plate: its rear edge is the striker", ["y_plate_right"]),
            ("Y rail", ["y_rail_right"]),
        ])
    el = g["electronics"]
    V["electronics"] = dict(
        q={"x": 0, "y": 0, "z": 110}, show=el | pre("z_pedestal", "frame_bot", "z_bearing_f", "z_pulley_f"),
        ghost=ghost_frame - pre("frame_bot"), size=(1500, 960), belt_names=set(),
        camera={"pos": (380, -760, 660), "focal": (0, -5, 25), "angle": 22},
        callouts=[
            ("24 V power supply, lying along Y", ["psu"]),
            ("Control board (four stepper drivers)", ["control_board"]),
            ("Relay board: switches the supply's mains feed, wired with its neutral", ["psu_relay"]),
            ("Host computer", ["host"]),
            ("Fused, switched mains inlet", ["inlet"]),
            ("Inlet panel, laser-cut", ["inlet_panel"]),
            ("Tray, laser-cut aluminium, bolted to the bottom rails", ["electronics_tray"]),
            ("Front lead-screw pedestals stand on the tray's edges", ["z_pedestal_fr"]),
        ])
    off = {}
    up = (0.0, 0.0, 230.0)
    side = (-470.0, -120.0, 60.0)
    for n in g["gantry"] | g["toolhead"] | g["ydrive"]:
        off[n] = up
    for n in g["bed"] | g["zdrive"] | pre("z_pedestal"):
        off[n] = side
    for n in g["electronics"]:
        off[n] = (0.0, 0.0, -210.0)
    counts = {
        "gantry": len(g["gantry"] | g["toolhead"] | g["ydrive"]),
        "bed": len(g["bed"] | g["zdrive"] | pre("z_pedestal")),
        "electronics": len(g["electronics"]),
    }
    counts["frame"] = len(A) - sum(counts.values())
    V["exploded"] = dict(
        q={"x": 0, "y": 0, "z": 110}, show=A, size=(1500, 1200), offsets=off,
        belt_offsets={"x_belt": up, "y_belt": up, "y_belt_l": up, "z_belt": side},
        camera={"pos": (1150, -1750, 1250), "focal": (-200, -40, 215), "angle": 24},
        callouts=[
            (f"Gantry, toolhead and Y drive: {counts['gantry']} parts", ["x_beam"]),
            (f"Bed, carrier and Z drive: {counts['bed']} parts", ["bed"]),
            (f"Frame: {counts['frame']} parts", ["frame_top_right"]),
            (f"Electronics tray: {counts['electronics']} parts", ["psu"]),
        ])
    return V


def stage_renders(design_path: Path, only_views=None) -> None:
    from mechloop.runner import load_design

    import showcase_render as R

    t0 = time.time()
    design = load_design(str(design_path))
    sc = R.Scene(design)
    mf = model_facts(design)
    V = view_defs(sc, mf)
    out_path = DATA / "renders.json"
    out = json.loads(out_path.read_text()) if out_path.exists() else {}
    out.setdefault("views", {})
    for k, v in V.items():
        if only_views and k not in only_views:
            continue
        v = dict(v)
        co = [(f"c{i + 1}", lab, names) for i, (lab, names) in enumerate(v.pop("callouts"))]
        r = R.render_view(sc, IMG / f"{k}.webp", callouts=co, **v)
        hidden = [c["label"] for c in r["callouts"] if not c["visible"]]
        if hidden:
            print(f"  [{k}] not visible from this camera, no callout drawn: {hidden}")
        r["callouts"] = [c for c in r["callouts"] if c["visible"]]
        out["views"][k] = r
        print(f"  rendered {k} ({time.time() - t0:.0f} s)")
    cls: dict = {}
    for n, c in sc.cls.items():
        cls[c] = cls.get(c, 0) + 1
    out["model"] = mf
    out["class_counts"] = cls
    out["class_color"] = R.CLASS_COLOR
    out["class_label"] = R.CLASS_LABEL
    out["design"] = design.name
    out["parts"] = len(design.components)
    DATA.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=1))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("design", type=Path)
    ap.add_argument("--only", nargs="*", default=None, help="stages: renders fea page")
    ap.add_argument("--views", nargs="*", default=None, help="with the renders stage: only these views")
    ap.add_argument("--refresh", action="store_true", help="re-make showcase/data/inputs from INPUT_SOURCES")
    a = ap.parse_args()
    stages = a.only or ["renders", "fea", "page"]
    IMG.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    if "renders" in stages:
        stage_renders(a.design, a.views)
    if "fea" in stages:
        import showcase_fea
        showcase_fea.run(a.design, IMG, DATA)
    if "page" in stages:
        import showcase_page
        showcase_page.run(a.design, SHOW, refresh=a.refresh)


if __name__ == "__main__":
    main()
