"""Task poses and trajectories for Arm Build 1 stages A-D (generated from mechloop.arm.cell; saved as JSON).

Every task is top-down (tool axis -z) by design: the sheet, the door and the shelf are worked through vertical pins in
loops or holes, assembly is designed for vertical insertion (01 section 3). One optional pose tilts the tool 45 deg (part
presented to a side camera) to score the 5-axis's extra freedom; it is not a pass/fail pose.

Forces are the force ON THE TOOL from the environment (N), moments in N·mm, payload includes the tool (kg).
Accuracy classes (ARM_SCOPE owner decisions): "assembly" 3 sigma <= 0.2 mm (provisional; test 4 replaces it), lateral
(xy) error since insertion is vertical; "sheet" <= 1 mm, 3D error.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import cell as C

DATA = Path(__file__).resolve().parents[1] / "data" / "arm" / "task_poses.json"
G = 9.81
TOOLS = {   # flange to TCP length (mm), capsule radius (mm), mass kg -- all est.
    "hook_pin": (70.0, 14.0, 0.15),      # pin with a head: tab hole, door loop, shelf loop (vertical, or horizontal
    #                                    with a 15 mm drop pin on arms that can pitch the tool)
    "gripper": (110.0, 30.0, 0.25),      # parallel-jaw servo gripper (04 tool 1)
    "screwdriver": (130.0, 25.0, 0.30),  # compliant driver (04 tool 5)
}
DOWN = [0.0, 0.0, -1.0]
DOOR_CLOSED = {"door_deg": 0.0, "shelf_off": C.SHELF_TRAVEL}
DOOR_OPEN_STOWED = {"door_deg": C.DOOR_OPEN_DEG, "shelf_off": C.SHELF_TRAVEL}
OPEN_DEPLOYED = {"door_deg": C.DOOR_OPEN_DEG, "shelf_off": 0.0}
HZ = (90.0, 30.0)   # sheet poses may also be worked with the tool horizontal or tilted 30 deg (leaning away from the base,
#                       a hook rather than a straight pin) by an arm that can pitch its tool


def _p(pid, stage, task, pts, *, z_ref="bench", tool="hook_pin", payload=0.2, force=(0, 0, 0), moment=(0, 0, 0),
       cls="sheet", approach=DOWN, states=None, contact=(), required=True, path=False, tilt_deg=0.0, alt_tilts=(),
       note=""):
    pts = [list(map(float, p)) for p in pts]
    states = states or [DOOR_CLOSED]
    return {"id": pid, "stage": stage, "task": task, "kind": "path" if path else "pose", "points": pts, "z_ref": z_ref,
            "tool": tool, "tool_axis_tilt_deg": tilt_deg, "alt_tilts_deg": list(alt_tilts), "payload_kg": payload, "force_n": list(map(float, force)),
            "moment_nmm": list(map(float, moment)), "accuracy_class": cls, "approach": list(map(float, approach)),
            "cell_states": states, "contact": list(contact), "required": required, "note": note}


def _line(a, b, step=10.0):
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(2, int(np.ceil(np.linalg.norm(b - a) / step)) + 1)
    return [a + (b - a) * t for t in np.linspace(0, 1, n)]


def build_poses() -> list[dict]:
    P = []
    x, gy = C.SHEET_CX, C.GRIP_Y
    sheet_states = [OPEN_DEPLOYED]
    sh = ("bed", "shelf", "shelf_guides")
    # ---- Stage A: sheet handling (z relative to the bed transfer height z_T)
    P.append(_p("A1_tab_approach", "A", "approach the grip tab from above", [(x, gy, 25)], z_ref="bed",
                states=sheet_states, contact=sh, approach=DOWN, alt_tilts=HZ))
    P.append(_p("A2_tab_engage", "A", "pin into the tab hole", [(x, gy, 0)], z_ref="bed", states=sheet_states, contact=sh,
                alt_tilts=HZ))
    P.append(_p("A3_peel", "A", "peel the front edge 8 mm off the magnet", _line((x, gy, 0), (x, gy, 8), 2), z_ref="bed",
                path=True, payload=1.0, force=(0, 0, -15), states=sheet_states, contact=sh, approach=[0, 0, 1], alt_tilts=HZ,
                note="peel force 5-15 N est. (01 section 3); test 5 measures it"))
    P.append(_p("A4_pull_240", "A", "straight pull 240 mm (decisive-test minimum)",
                _line((x, gy, 8), (x, gy - C.PULL_TEST, 8)), z_ref="bed", path=True, payload=1.0, force=(0, 20, 0),
                states=sheet_states, contact=sh, approach=[0, -1, 0], alt_tilts=HZ, note="pull 5-20 N est. (01)"))
    P.append(_p("A5_pull_full", "A", f"continue to {C.PULL_FULL:.0f} mm: sheet fully on the shelf",
                _line((x, gy - C.PULL_TEST, 8), (x, gy - C.PULL_FULL, 8)), z_ref="bed", path=True, payload=1.0,
                force=(0, 20, 0), states=sheet_states, contact=sh, approach=[0, -1, 0], alt_tilts=HZ))
    tab_out = gy - C.PULL_FULL
    P.append(_p("A6_flex", "A", "lift the tab end 35 mm against the shelf's clamp to flex the sheet",
                _line((x, tab_out, 8), (x, tab_out, 35), 3), z_ref="bed", path=True, payload=1.0, force=(0, 0, -15),
                states=sheet_states, contact=sh, approach=[0, 0, 1], alt_tilts=HZ, note="flex force est.; shelf fixture does the bending"))
    P.append(_p("A7_reseat_push", "A", "push the sheet back onto the bed", _line((x, tab_out, 6), (x, gy, 6)), z_ref="bed",
                path=True, payload=0.4, force=(0, -15, 0), states=sheet_states, contact=sh, approach=[0, 1, 0], alt_tilts=HZ))
    P.append(_p("A8_reseat_nudge", "A", "nudge against the rear and left pins", [(x - 3, gy + 3, 4)], z_ref="bed",
                payload=0.4, force=(7.1, -7.1, 0), states=sheet_states, contact=sh, approach=[-0.7071, 0.7071, 0], alt_tilts=HZ,
                note="final location by the bed pins (+/-0.3 mm target is the pins', not the arm's)"))
    # door: pin in the free-edge loop, arc 0 -> 85 deg
    degs = np.linspace(0, C.DOOR_OPEN_DEG, 18)
    door_pts = [(*C.handle_xy(d), C.HANDLE_Z) for d in degs]
    door_states = [{"door_deg": float(d), "shelf_off": C.SHELF_TRAVEL} for d in degs]
    # force on the tool opposes the handle's motion (tangent of the arc): 20 N latch break-away at 0 deg, 5 N swinging
    door_f = [list(np.array([np.sin(np.radians(d)), np.cos(np.radians(d)), 0.0]) * (20.0 if i == 0 else 5.0))
              for i, d in enumerate(degs)]
    P.append(_p("A0_door_open", "A", "open the V13 door: pin in the free-edge loop, arc 0-85 deg", door_pts, path=True,
                force=door_f[0], states=door_states, contact=("door",), approach=DOWN,
                note="20 N latch break-away est. (magnetic catch); 5 N swinging; close = same path reversed"))
    P[-1]["forces_n"] = [[float(v) for v in f] for f in door_f]
    sl = [(*C.shelf_loop_xy(o), 0.0) for o in np.linspace(C.SHELF_TRAVEL, 0, 21)]
    sl_states = [{"door_deg": C.DOOR_OPEN_DEG, "shelf_off": float(o)} for o in np.linspace(C.SHELF_TRAVEL, 0, 21)]
    P.append(_p("A0_shelf_deploy", "A", "pull the stowable shelf 440 mm into place (stow = reverse)", sl, z_ref="bed",
                path=True, force=(10, 0, 0), states=sl_states, contact=("shelf", "shelf_guides"),
                note="shelf loop at the shelf top height; drawer friction 10 N est."))
    # ---- Stage B: inspection and part handling
    P.append(_p("B1_pick_on_shelf", "B", "pick a released part off the sheet on the shelf", [(x, -125, 12)], z_ref="bed",
                tool="gripper", payload=0.5, force=(0, 0, 5), cls="sheet", states=sheet_states, contact=sh))
    # station poses: points relative to the station's top centre (z above its top), resolved per layout
    for i, d in enumerate([(-70, -30, -25), (70, 20, -25)]):
        P.append(_p(f"B2_release_tray_{i}", "B", "pick from the release tray (camera-located, loose)", [d],
                    z_ref="station:release_tray", tool="gripper", payload=0.5, force=(0, 0, 5), cls="sheet",
                    contact=("release_tray",), states=[DOOR_CLOSED, DOOR_OPEN_STOWED]))
    for i, d in enumerate([(-90, -60, 15), (95, 65, 15)]):
        P.append(_p(f"B3_present_{i}", "B", "place a part on the scanner / camera stage", [d], z_ref="station:inspection",
                    tool="gripper", payload=0.5, force=(0, 0, 5), cls="sheet", contact=("inspection",),
                    note="stage B: +/-1 mm, +/-2 deg"))
    P.append(_p("B4_present_tilted", "B", "present a part tilted 45 deg to a side camera (optional generality pose)",
                [(0, 0, 150)], z_ref="station:inspection", tool="gripper", payload=0.5, cls="sheet",
                contact=("inspection",), required=False, tilt_deg=45.0))
    # ---- Stage C: simple screwed assemblies (2-3 printed parts, screws into captured nuts)
    for i, d in enumerate([(-70, -40, 5), (70, 40, 5)]):
        P.append(_p(f"C1_tray_pick_{i}", "C", "pick a printed part from a kinematic pocket", [d], z_ref="station:parts_tray",
                    tool="gripper", payload=1.0, force=(0, 0, 20), cls="assembly", contact=("parts_tray",)))
    P.append(_p("C2_place_in_nest", "C", "place part in the screw-station nest", [(0, 0, 15)],
                z_ref="station:screw_station", tool="gripper", payload=1.0, force=(0, 0, 20), cls="assembly",
                contact=("screw_station",)))
    P.append(_p("C3_nut_into_pocket", "C", "drop an M3 nut into its printed pocket", [(30, 0, 25)],
                z_ref="station:screw_station", tool="gripper", payload=0.2, force=(0, 0, 20), cls="assembly",
                contact=("screw_station",)))
    P.append(_p("C4_drive_screw", "C", "start and drive an M3 screw (compliant driver)", [(-30, 0, 30)],
                z_ref="station:screw_station", tool="screwdriver", payload=0.3, force=(0, 0, 20), moment=(0, 0, 1200),
                cls="assembly", contact=("screw_station",), note="20 N axial, 0.4-1.2 N·m reaction (ARM_SCOPE 2.3, est.)"))
    # ---- Stage D: tool library on a rack (end slots of 4 at 70 mm pitch)
    for i, dx in enumerate((-105.0, 105.0)):
        P.append(_p(f"D1_tool_slot_{'first' if i == 0 else 'last'}", "D",
                    "pick / place a tool on the kinematic coupling in a rack slot", [(dx, 0, 10)],
                    z_ref="station:tool_rack", tool="gripper", payload=0.5, force=(0, 0, 30), cls="assembly",
                    contact=("tool_rack",), note="coupling capture +/-0.5-1 mm (01); held to the assembly class here"))
    return P


def resolve(pose: dict, z_t: float, layout: str = "ring"):
    """Concrete TCP points (n,3) and the CellStates to check at each point, for a transfer height and layout."""
    pts = np.array(pose["points"], float)
    ref = pose["z_ref"]
    if ref == "bed":
        pts[:, 2] += z_t
    elif ref.startswith("station:"):
        x0, x1, y0, y1, top = C.stations(layout)[ref.split(":", 1)[1]]
        pts += np.array([(x0 + x1) / 2, (y0 + y1) / 2, top])
    st = pose["cell_states"]
    mk = [C.CellState(z_t, s["door_deg"], s["shelf_off"], layout) for s in st]
    if pose["kind"] == "path" and len(st) == len(pts):
        return pts, [[s] for s in mk]
    return pts, [mk] * len(pts)


def wrench(pose: dict, taught_kg: float = 0.2):
    """Change of the tool wrench from the taught state (tool only, no contact): payload change plus contact force."""
    f = np.array(pose["force_n"], float) + np.array([0, 0, -(pose["payload_kg"] - taught_kg) * G])
    return f, np.array(pose["moment_nmm"], float)


def save(path: Path = DATA) -> list[dict]:
    poses = build_poses()
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"frame": "cell: x right, y into the printer, z up; origin on the bench under the frame's front-face centre; mm",
            "z_ref": "'bed': z relative to the bed transfer height z_T (optimised per candidate); 'bench': absolute; "
                     "'station:<name>': x, y, z relative to that station's top centre (layouts in mechloop/arm/cell.py)",
            "layouts": {k: {n: list(v) for n, v in L.items()} for k, L in C.LAYOUTS.items()},
            "station_size_xyz_top": {k: list(v) for k, v in C.STATION_SIZE.items()},
            "force": "force ON THE TOOL from the environment, N; moment N·mm; payload includes the tool, kg",
            "classes": {"assembly": "3 sigma <= 0.2 mm lateral (provisional, test 4)", "sheet": "3 sigma <= 1 mm 3D"},
            "tools": {k: {"length_mm": v[0], "radius_mm": v[1], "mass_kg": v[2], "note": "est."} for k, v in TOOLS.items()},
            "generated_by": "python -m mechloop.arm.spike (mechloop/arm/poses.py)"}
    path.write_text(json.dumps({"meta": meta, "poses": poses}, indent=1) + "\n")
    return poses


def load(path: Path = DATA) -> list[dict]:
    return json.loads(path.read_text())["poses"]
