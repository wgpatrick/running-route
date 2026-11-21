"""Arm Build 1 cell: a light printer proxy plus bench stations, as boxes and one door panel (pure numpy).

Cell frame: x to the right, y INTO the printer, z up; origin on the bench top under the centre of the printer frame's
front face. Units mm. Every number is sourced or marked est./assumption in its comment.

Printer numbers come from docs (PRINTER_V12.md, ARM_SCOPE.md section 2, V13_IDEAS.md) and from a few module constants of
designs/printer_v12.py READ as text (never imported): FX, FY, FZ = 340, 360, 394; WALL_X = FX/2 - 20 = 150 (inner face
of the side walls); top front rail top at FZ + 10; nozzle tip 376.5 - 3.05 = 373.45 above the frame bottom; BED_CX =
-C_NOZ = -15.5; BED_CY = 4.5; sheet 220, plate 240.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------- printer proxy (sourced unless marked)
FEET = 35.5                     # PRINTER_V12.md: frame 35.5 mm above the floor on the NFJN5-30 feet
ENV_W, ENV_D, ENV_H = 388.0, 419.5, 475.9   # PRINTER_V12.md machine envelope (2020 frame)
FRAME_HALF_X = 170.0            # printer_v12.py FX/2 (outer faces of the side walls)
OPEN_HALF_X = 150.0             # printer_v12.py WALL_X: inner faces -> 300 mm clear opening (01 estimated 348 from 388 - 40)
FRONT_Y_PRINTER = -180.0        # printer_v12.py FY/2: front outer face in printer coordinates (est. reading: frame symmetric)
OPEN_Z0 = FEET + 20.0           # top of the bottom front rail (rail 0..20 above the frame bottom)
OPEN_Z1 = FEET + 384.0          # underside of the top front rail (top face at FZ + 10 = 404)
NOZZLE_Z = FEET + 373.45        # nozzle tip; the bed top reaches it at print Z = 0
Z_TRAVEL = 180.0                # PRINTER_V12.md: bed moves in Z only, 180 mm
BED_TOP_MIN, BED_TOP_MAX = NOZZLE_Z - Z_TRAVEL, NOZZLE_Z      # 228.95 .. 408.95 above the bench
SHEET = 220.0                   # PEI spring-steel sheet
PLATE = 240.0                   # MIC-6 bed plate
SHEET_T = 0.64                  # PRINTER_V12 (printer_v12.py T_SHEET)
SHEET_CX = -15.5                # BED_CX = -C_NOZ
SHEET_CY = 4.5 - FRONT_Y_PRINTER          # 184.5 inside the front face
SHEET_FRONT = SHEET_CY - SHEET / 2        # 74.5
SHEET_REAR = SHEET_CY + SHEET / 2         # 294.5
PLATE_FRONT = SHEET_CY - PLATE / 2        # 64.5
# Grip tab (owner-adopted printer change, ARM_SCOPE "Owner decisions"): assumption 24.5 mm forward of the sheet edge,
# 30 mm wide, with a 6 mm hole 7 mm from its tip for a pin/hook tool (the pin tip passes 14.5 mm in front of the plate)
TAB_TIP_Y = SHEET_FRONT - 24.5            # 50.0
GRIP_Y = TAB_TIP_Y + 7.0                  # 57.0: TCP at the tab hole
PULL_TEST = 240.0               # ARM_SCOPE decisive test 1: straight sheet pull >= 240 mm
PULL_FULL = SHEET_REAR + 15.5   # 310: sheet rear edge 15 mm clear of the front face (fully on the shelf; est. need)
TOOLHEAD_PARK_Y = 111.75 - FRONT_Y_PRINTER   # rear end of the nozzle's Y reach (PRINTER_V12 / printer_v12.py comment)

# ---------------------------------------------------------------- V13 door (assumptions; V13_IDEAS.md: hinged FRONT door)
DOOR_HINGE = np.array([-194.0, -10.0])     # assumption: hinge on the LEFT post, axis 10 mm in front of the face
DOOR_W = 388.0                  # full envelope width (assumption)
DOOR_T = 3.0                    # V13_IDEAS.md: 3 mm polycarbonate
DOOR_Z = (FEET, FEET + ENV_H)   # full height (assumption)
DOOR_OPEN_DEG = 85.0            # assumption: door stop at 85 deg (wider would meet the v12 e-stop head, see below)
HANDLE_R = DOOR_W + 50.0        # assumption: a loop handle ON THE FREE EDGE (loop axis vertical), on a 50 mm stand-off
HANDLE_Z = 200.0                # assumption: loop height above the bench, chosen for the arm (door is unbuilt)
ESTOP = ((-235.0, -35.0, FEET + 280.0), (-196.0, 112.0, FEET + 320.0))   # PRINTER_V12.md: head left of the post at
#   z 300, 35 mm proud of the front; body along the outside of the left side (x extent est.)

# ---------------------------------------------------------------- stations (all EXPLORATORY placeholders, est.)
# Stowable sheet shelf: the door sweeps everything within ~413 mm of its hinge in front of the printer, which includes the
# only place a sheet shelf can be (directly in front of the opening). The shelf therefore stows 440 mm to the right
# (outside the sweep) and the arm pulls it into place after opening the door (assumption; see the report's open issues).
SHELF_X = (SHEET_CX - 125.0, SHEET_CX + 125.0)     # sheet +/- 110 plus 15 mm side guides
SHELF_Y = (-255.0, -12.0)
SHELF_TRAVEL = 440.0
SHELF_LOOP = np.array([-80.0, -265.0])            # pull loop on the shelf's front edge (deployed position)
# Station boxes are the same in every layout: (width x, depth y, top z). Two layouts, since floor space is not a
# constraint and stations are placeholders: "ring" around a rotary arm's base (SCARA, 5-axis), "row" along the bench
# front under a Cartesian's X axis. Both keep every station outside the door's sweep (>= ~470 mm from the hinge in the
# swept sector) and clear of the deployed and stowed shelf.
STATION_SIZE = {
    "inspection": (260.0, 200.0, 80.0),      # scanner / camera stage
    "tool_rack": (280.0, 80.0, 150.0),       # 4 slots at 70 mm pitch
    "parts_tray": (200.0, 140.0, 40.0),      # kinematic pockets, AprilTags
    "screw_station": (160.0, 160.0, 100.0),  # nest with captured-nut pocket + screw presenter
    "release_tray": (200.0, 100.0, 60.0),    # released prints, in front of the stowed shelf
}
LAYOUTS = {   # station centres (x, y)
    "ring": {"inspection": (-270.0, -580.0), "tool_rack": (-133.0, -773.0), "parts_tray": (333.0, -773.0),
             "screw_station": (430.0, -540.0), "release_tray": (360.0, -330.0)},
    "row": {"inspection": (-430.0, -360.0), "tool_rack": (-720.0, -360.0), "release_tray": (380.0, -350.0),
            "screw_station": (620.0, -380.0), "parts_tray": (860.0, -360.0)},
}


def stations(layout: str) -> dict:
    """{name: (x0, x1, y0, y1, top z)} for a layout."""
    out = {}
    for n, (cx, cy) in LAYOUTS[layout].items():
        w, d, h = STATION_SIZE[n]
        out[n] = (cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2, h)
    return out


@dataclass(frozen=True)
class Box:
    name: str
    lo: tuple
    hi: tuple


@dataclass(frozen=True)
class Panel:
    """A vertical rectangular plate: segment p0-p1 in plan, z range, thickness."""
    name: str
    p0: tuple
    p1: tuple
    z0: float
    z1: float
    t: float


@dataclass(frozen=True)
class CellState:
    z_t: float = 260.0          # bed (sheet top) transfer height above the bench
    door_deg: float = 0.0       # 0 closed .. DOOR_OPEN_DEG
    shelf_off: float = SHELF_TRAVEL   # 0 deployed .. SHELF_TRAVEL stowed (+x)
    layout: str = "ring"


def door_dir(deg: float) -> np.ndarray:
    a = np.radians(deg)
    return np.array([np.cos(a), -np.sin(a)])


def handle_xy(deg: float) -> np.ndarray:
    return DOOR_HINGE + HANDLE_R * door_dir(deg)


def shelf_loop_xy(off: float) -> np.ndarray:
    return SHELF_LOOP + np.array([off, 0.0])


def obstacles(s: CellState) -> list:
    """All fixed and state-dependent obstacles for one cell state."""
    zt = s.z_t
    top = FEET + ENV_H
    o = [
        Box("printer_left", (-ENV_W / 2, 0.0, FEET), (-OPEN_HALF_X, ENV_D, top)),
        Box("printer_right", (OPEN_HALF_X, 0.0, FEET), (ENV_W / 2, ENV_D, top)),
        Box("printer_bottom", (-OPEN_HALF_X, 0.0, FEET), (OPEN_HALF_X, ENV_D, OPEN_Z0)),
        Box("printer_top", (-OPEN_HALF_X, 0.0, OPEN_Z1), (OPEN_HALF_X, ENV_D, top)),
        # bed plate, carrier and deck, conservatively solid from the bottom rail up to the sheet top
        Box("bed", (-OPEN_HALF_X, PLATE_FRONT - 4.5, OPEN_Z0), (OPEN_HALF_X, ENV_D, zt)),
        # toolhead parked rear-top (nozzle tip at NOZZLE_Z), X beam and duct (est. extent)
        Box("toolhead_parked", (-OPEN_HALF_X, TOOLHEAD_PARK_Y - 60.0, NOZZLE_Z - 15.0), (OPEN_HALF_X, ENV_D, OPEN_Z1)),
        Box("estop", ESTOP[0], ESTOP[1]),
    ]
    for n, (x0, x1, y0, y1, zt_) in stations(s.layout).items():
        o.append(Box(n, (x0, y0, 0.0), (x1, y1, zt_)))
    off = s.shelf_off
    o.append(Box("shelf", (SHELF_X[0] + off, SHELF_Y[0], zt - 40.0), (SHELF_X[1] + off, SHELF_Y[1], zt - 1.2)))
    o.append(Box("shelf_guides", (SHELF_X[0] + off, SHELF_Y[0], zt - 1.2), (SHELF_X[1] + off, SHELF_Y[1] - 40.0, zt + 4.0)))
    p1 = DOOR_HINGE + DOOR_W * door_dir(s.door_deg)
    o.append(Panel("door", tuple(DOOR_HINGE), tuple(p1), DOOR_Z[0], DOOR_Z[1], DOOR_T))
    h = handle_xy(s.door_deg)
    o.append(Box("door", (h[0] - 15, h[1] - 15, HANDLE_Z - 12), (h[0] + 15, h[1] + 15, HANDLE_Z + 12)))   # loop
    return o


# ---------------------------------------------------------------- distances (vectorised)
def dist_points_box(P: np.ndarray, b: Box) -> np.ndarray:
    lo, hi = np.asarray(b.lo), np.asarray(b.hi)
    d = np.maximum(np.maximum(lo - P, P - hi), 0.0)
    out = np.linalg.norm(d, axis=-1)
    inside = np.all((P > lo) & (P < hi), axis=-1)
    if inside.any():   # negative penetration depth
        pen = np.min(np.minimum(P - lo, hi - P), axis=-1)
        out = np.where(inside, -pen, out)
    return out


def dist_points_panel(P: np.ndarray, p: Panel) -> np.ndarray:
    a, b = np.asarray(p.p0), np.asarray(p.p1)
    ab = b - a
    t = np.clip(((P[..., :2] - a) @ ab) / (ab @ ab), 0.0, 1.0)
    dxy = np.linalg.norm(P[..., :2] - (a + t[..., None] * ab), axis=-1) - p.t / 2
    dz = np.maximum(np.maximum(p.z0 - P[..., 2], P[..., 2] - p.z1), 0.0)
    return np.where(dxy > 0, np.hypot(np.maximum(dxy, 0), dz), np.where(dz > 0, dz, dxy))


def dist_points(P: np.ndarray, o) -> np.ndarray:
    return dist_points_box(P, o) if isinstance(o, Box) else dist_points_panel(P, o)


@dataclass
class Capsule:
    """A swept sphere: segment a-b, radius r. `tool` capsules may touch the pose's contact obstacles."""
    name: str
    a: np.ndarray
    b: np.ndarray
    r: float
    tool: bool = False


def capsule_clearance(caps: list, obs: list, exempt: set = frozenset(), step: float = 8.0) -> tuple[float, str]:
    """Minimum surface gap between the arm's capsules and the obstacles, and the (capsule, obstacle) pair that sets it.
    Tool capsules ignore obstacles named in `exempt` (the thing the tool works on)."""
    best, who = np.inf, ""
    for c in caps:
        n = max(2, int(np.linalg.norm(c.b - c.a) / step) + 2)
        P = c.a + np.linspace(0, 1, n)[:, None] * (c.b - c.a)
        for o in obs:
            if c.tool and o.name in exempt:
                continue
            g = float(dist_points(P, o).min()) - c.r
            if g < best:
                best, who = g, f"{c.name}~{o.name}"
    return best, who
