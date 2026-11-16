"""printer_v8_1: printer_v8 rebuilt to the owner's design guidelines (docs/DESIGN_GUIDELINES.md). docs/PRINTER_V8_1.md has
the numbers, every change and its reason.

TARGET: a 180 x 180 x 180 mm open-frame printer the owner intends to build; functionality first. Part count, assembly
time and cost are reported, not limits.
    - envelope 420 x 420 x 480 mm (unchanged)
    - direct-drive toolhead, <= 0.40 kg moving mass in X (unchanged)
    - both Y belts within 1 mm of plane in >= 98 % of builds (unchanged)
    - a bed probe that reaches the whole print area (unchanged)
    - bed sag under 1 kg at the worst print corner <= 0.02 mm on the screw-only bound, and every lead-screw nut seated at
      the LSC-015 lead budget (two screws at opposite lead limits)

What changed from v8 (part by part in the doc):

1. NO LOAD-BEARING PRINTED PART. The nut blocks, Z drive mount, Z sleeve, Z pedestals, X belt block and the three belt
   tension anchors are now laser-cut aluminium. The only printed parts are the probe holder (clamped through two
   aluminium compression sleeves, so the Roto's screws do not clamp plastic), the part-cooling duct and three covers
   over the mains terminals. Every printed part declares its print settings (meta["print"]).
2. LASER-CUT FIRST. Every metal part is a 2D laser-cut profile at a SendCutSend stocked gauge (6061-T6 1.6 / 2.54 / 3.175
   / 4.75 / 6.35 / 9.525, 5052-H32 2.286 / 3.175 for the bent parts, 304 1.524 for the bed tie, MIC-6 9.525 for the bed)
   or a purchased part. Nothing is CNC machined: the tool plate is two stacked plates (the rear one is the counterbore
   for the guide-block screws), the bed is cast plate laser-cut with its faces as cast. assign(sheet="sendcutsend").
3. NAMED MATERIALS: no generic steel. Moving plates are 6061-T6; bent parts 5052-H32; the bed tie 304 stainless.
4. NO TAPPED ALUMINIUM WE MAKE, no tapped extrusion ends. Through-bolts with nuts and washers; captive nuts in
   laser-cut hex holes; PEM nuts in the 5052 tension anchors; steel thread inserts only in the bed plate, whose top face
   must stay flat for the print sheet. The bed carrier is a 2020 rectangle joined by corner brackets on T-nuts.
   NO THREAD IN A PRINTED PART (owner review): every screw through a printed part is an M3 through-bolt with washers and
   an ISO 10511 nyloc nut, on the side with access, or captured with its washer in a printed pocket where there is none
   (the part duct); printed clearance holes are ISO 273 medium + 0.2 mm (M3 3.6).
5. WASHERS under every head or nut on a slot, an oversize hole, thin aluminium or plastic; thread locking listed on
   the moving assemblies; rounded outside corners on every cut profile.
6. Z: three T8 x 2 screws on one belt, one guide block per rail, as v8, but every nut stays seated at the lead budget:
   the blocks are Hiwin's clearance class ZF (they locate the carrier, they do not hold its tilt against the screws), the
   carrier is heavier (9.5 mm bed, aluminium floor of nut plates) and its mass centre sits over the screws' triangle.
   Each screw stands in a laser-cut plate tower with two 608s clamped between plates: the upper bearing is the axial
   bearing (a brass T8 nut screwed down on its inner ring carries the bed: no set screw in the weight path), the
   pulley under it is set-screwed for torque only and holds the screw down through an 8 x 12 shim.
7. Catalogue parts: TRONXY PEI180 sheet, Coolerguys CG3010U24 part fan. Stand-ins: the PEI180's magnetic base (its
   thickness is not published), the four M5 threaded-rod bed posts and the two M3 thread inserts in the bed plate.

Layout (X = width, Y = depth with the front at -Y, Z = up) is v4's; see designs/printer_v4.py for the history.

Not modelled (flagged): the Roto's solid is E3D's reference CAD envelope in solid aluminium; T-nuts, PEM nuts' clinch
features, the BAT85 diode and the Revo's spring clip are BOM lines or notes; payload is extra mass on the bed plate; no
airflow model for the duct; pulley set screws; belt teeth.
"""
import math

import numpy as np
from build123d import (Box, Cylinder, GeomType, Location, Plane, Polygon, Pos, RectangleRounded, RegularPolygon, Rot,
                       chamfer, extrude, fillet)

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import MATERIALS, Belt, ThermalCase
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, add_washer, bearing, clearance_hole,
                            endstop_switch, extrusion_2020, gt2_idler, gt2_pulley, leadscrew_nut_t8, leadscrew_t8,
                            mgn12_rail, mgn12h_carriage, nema17, place, printed_clearance_hole)
from mechloop.parts.batch6 import fan_cg3010u24, print_sheet_pei180
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       iec_inlet_c14, psu_lrs, raspberry_pi_zero2w, relay_btt_v12, skr_mini_e3_v3,
                                       thermal_fuse)
from mechloop.parts.hardware import WASHER, spacer_round
from mechloop.parts.probes import add_probe_nuts, probe_omron_e2e
from mechloop.parts.toolhead import extruder_roto, hotend_revo
from mechloop.shops import assign

# ---- brief ------------------------------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 180.0, 180.0, 180.0
PAYLOAD_KG = 1.0
V_XY, A_XY = 250.0, 4000.0
V_Z, A_Z = 12.0, 200.0
MARGIN = 3.0
ENVELOPE = (420.0, 420.0, 480.0)
MAX_TOOLHEAD_KG, MIN_BELT_IN_PLANE = 0.40, 0.98

# ---- electrical choices -----------------------------------------------------------
BED_W = 180.0          # 180 W pad on the board's own bed output (7.5 A of 8 A allowed), as v7 / v8
BED_MAX_C = 80.0       # as v8: the magnetic base's real limit is unknown (the seller says 130 degC); the probe's 85 degC rating is the next limit
PSU_MODEL = "LRS-350-24"
BED_AWG, BED_INS = 16, "silicone"
RUN_CURRENT = {"x": 0.28, "y": 1.20, "z": 1.00, "extruder": 0.40}
FUSE_A = 8.0
T_TRAY = 3.175         # v8.1: SendCutSend 6061 .125"
TRAY_Y0, TRAY_Y1 = -138.0, 85.0
Z_TRAY = 20.0 + T_TRAY

# ---- materials and stock (SendCutSend gauges, mm) ----------------------------------
AL, AL_BEND, SS, CAST = "al6061", "al5052", "stainless304", "al_mic6"
G16, G20, G25, G32, G48, G64, G95, G127 = 1.6, 2.032, 2.54, 3.175, 4.75, 6.35, 9.525, 12.7   # 6061-T6 .063 .080 .100 .125 .187 .250 .375 .500
B23, B32 = 2.286, 3.175                                                  # 5052-H32 .090 .125
R_B32, R_B23 = 3.18, 0.81                                                # SendCutSend's only inside bend radius for those gauges
SS15 = 1.524                                                             # 304 .060
R_SS15 = 1.78
HOT = "abs"            # printed parts near the hotend
COOL = "petg"          # printed covers on the cold frame
PRINT_ABS = {"walls": 4, "top_layers": 5, "bottom_layers": 5, "infill": 0.4, "infill_pattern": "gyroid", "layer_height_mm": 0.2,
             "line_width_mm": 0.45}

# ---- frame ------------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 394.0
RAIL_X = FX / 2 - 10
TX, TY = PRINT_X / 2, PRINT_Y / 2
FT_DROP = 30.0

# ---- Z axis -----------------------------------------------------------------------
BED = 220.0
T_BED = G95            # v8.1: 9.525 mm MIC-6 (a stocked thickness, faces as cast; v8: 8 mm, not stocked)
T_MAG = 1.0            # the PEI180's magnetic base: thickness NOT published (stand-in, see build())
T_SHEET = 0.4          # TRONXY PEI180 spring steel (catalogue)
SHEET = 180.0
UP_X = 90.0
UP_Y = FY / 2 - 10
Y_FACE = UP_Y - 10
Y_CAR = Y_FACE - 13
T_BP = G48             # back plate 4.75 mm (v8: 5, not stocked)
Y_PF = Y_CAR - T_BP
LS_Y = UP_Y + 10       # rear lead screw axis Y (over the bottom back rail)
MOTOR_L = 40
BED_Y1 = Y_PF - 10.5
BED_Y0 = BED_Y1 - BED
BED_CY = (BED_Y0 + BED_Y1) / 2
ARM_X = 65.0
# bed posts: M5 threaded rods (DIN 976-1) screwed into steel thread inserts in the bed plate, a jam nut and washer under
# the plate, POST_FREE of free rod (the flexure that lets the hot plate grow), then a laser-cut tab on the arm with a
# washer and nut above and below it (the levelling adjustment)
POST_NUT, W5 = 4.7, WASHER["normal"]["M5"][2]
POST_FREE = 59.0
T_TAB = G48
POST_INSERT = 7.5      # M5 x 1.5 D thread insert from the plate's underside
H_COL = W5 + POST_NUT + POST_FREE + POST_NUT + W5 + T_TAB
POST_X = ARM_X + 21.0
BED_MOUNTS = [(-POST_X, BED_Y1 - 19.5), (POST_X, BED_Y1 - 19.5), (-POST_X, BED_Y1 - 177.0), (POST_X, BED_Y1 - 177.0)]
TAB_DY = (8.0, 30.0)
BED_FX = 36.5          # v8.1: the plate reaches 36.5 mm past the sheet at the front (v8 16.5): weight over the front nuts
TIE_Y = BED_Y1 - 30.0
PAD_CY = BED_Y1 - 106.0
FS_X = FX / 2 - 10     # front lead screws over the bottom side rails
FS_Y = -101.0
NUT_PIN = (0.0, 8.0)
NUT_FLOAT = 2.8
Z_DN = 3.0
Z_UP = 1.65
Z_RAIL_L = 245.0

# ---- gantry -----------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13
T_YP = G48             # Y plates: 4.75 mm 6061 (v8: 3 mm steel)
Z_BEAM = Z_PLATE - 10.0
PR = 20 * 2.0 / math.pi / 2
BWX, BWY = 9.0, 12.0
P_BC = lambda w: 7.0 + (w + 1) / 2
I_H = lambda w: w + 2.5
SS19, R_SS19 = 1.88, 1.9   # 304 .074, SendCutSend's bend radius
MT_Y = SS19            # Y motor mounts: 1.88 mm 304, bent fin (v8: 2 mm steel): the belt stays 10.1 mm from the motor face
MT_YI = SS19           # Y idler mounts: the same gauge, so idler and pulley share the belt plane
MT = G32               # X motor mount (6061) and X idler mount (5052): 3.175 mm
R_TPF = 10.0 + 13.0
T_TPF, T_TPR = G32, G48            # tool plate: front 3.175 (on the guide block), rear 4.75 (counterbore for the block screws)
T_TP = T_TPF + T_TPR
R_TPR = R_TPF + T_TP
_ROTO = extruder_roto().interfaces
ROTO_W = _ROTO["mount_width"]
ROTO_NX, ROTO_NY, ROTO_NZ = _ROTO["nozzle_tip"][0]
ROTO_H2 = _ROTO["mount_holes_m3"][1]
HOT_OFF = R_TPR + ROTO_W / 2 + ROTO_NY
YB0 = BED_CY - HOT_OFF
ROTO_O = (-ROTO_NX, YB0 + R_TPR + ROTO_W / 2, Z_BEAM)
Z_NOZZLE = ROTO_O[2] + ROTO_NZ
NOZZLE_GAP = 0.1
XM_X, XI_X = -118.0, 118.0
BEAM_L = 288.0
XD_Z = Z_BEAM + 33.0
X_PG = 2.75
XB_Y = YB0 - 10.0 + X_PG + P_BC(BWX)
X_SP = XB_Y - I_H(BWX) / 2 - (YB0 - 10.0)
Z_XL = XD_Z - PR
Y_SP = W5                          # a real M5 washer between each Y idler and its mount
YB_X = FX / 2 + MT_Y + Y_SP + I_H(BWY) / 2
YM_Y = FY / 2 + 24.0
Z_YA = Z_PLATE + T_YP + 0.7
Z_YC = Z_YA - PR
BELT_ADJ = 3.0
# clearance holes in PRINTED parts (owner's practice, docs/DESIGN_GUIDELINES.md): ISO 273 medium + 0.2 mm FDM allowance for a
# vertical hole (M3 3.6, M5 5.7); every printed clearance hole in v8.1 is vertical in its print orientation
PH3, PH5 = printed_clearance_hole("M3"), printed_clearance_hole("M5")
# captive nut pocket in a printed part: nyloc M3 (ISO 10511, 5.5 across flats, 4.0 high) with an M3 washer (7.0 x 0.5) in front
# tightening torque for an M3 through-bolt that clamps a printed part (stated, not the 0.5 N.m the checker assumes for
# plastic): about 520 N of preload, 18 MPa under an M3 washer, well under the printed yield (ABS 30.8, PETG 47 MPa)
PRINTED_JOINT_TORQUE = 0.3
POCKET_AF, POCKET_NUT, POCKET_WD, POCKET_W, POCKET_WALL = 5.5 + 0.3, 4.0 + 0.2, 7.0 + 0.4, 0.5 + 0.1, 2.0
SH3 = 3.6
YH3 = 3.5
CB_TS = T_TPR
PL_Y0, PL_Y1 = -24.0, 19.5
BELT_SLOTS = (-15.3, -5.5, 5.5, 15.3)   # v8.1: slots as wide as the sheet is thick, webs >= 4.75
SLOT_W = 4.8
YP_IN = RAIL_X - 33.0
YP_NOTCH = (RAIL_X - 15.5, -8.0)

# bed heights follow from the nozzle
Z_SURF = Z_NOZZLE - NOZZLE_GAP - PRINT_Z
Z_BED = Z_SURF - T_SHEET - T_MAG - T_BED
Z_FL = Z_BED - H_COL                              # top of the carrier rectangle (arms, beams); the nut plates lie on it
Z_ARM = Z_FL - 10.0
Z_TAB = Z_FL                                      # underside of the three nut plates = top of each nut's flange
BP_Z1 = Z_SURF - 8.0
ZC2 = BP_Z1 - 26.0
ZC1 = ZC2
Z_RAIL_C = ZC1 - 22.7 - Z_DN - 5.3 + Z_RAIL_L / 2
BP_Z0 = Z_ARM - 12.0
BP_W = 215.0
# ---- carrier: a 2020 rectangle (rear beam on the back plate, two arms, front beam) with 9.5 mm nut plates on top ----
RB_Y = Y_PF - 10.0                                # rear beam centre (its rear face on the back plate)
RB_X = 95.0                                       # rear beam half length
FB_FACE = FS_Y + 26.0                             # front beam's front face: clear of the front towers below it
FB_Y = FB_FACE + 10.0
FB_X = FX / 2                                     # front beam half length (flush with the frame's sides)
ARM_Y0, ARM_Y1 = FB_Y + 10.0, RB_Y - 10.0         # arms run between the beams
T_NP = G64                                        # front nut plates (6.35 mm 6061)
T_NPR = G95                                       # rear nut plate (9.525 mm 6061): its tongue is a 48 mm cantilever
NP_HOLE = 2 * (5.1 + NUT_FLOAT) + 0.8             # the nut's barrel floats in a round hole
PIN_SP_D = 5.0                                    # anti-rotation pin: an M2.5 screw through a 5 mm aluminium sleeve
FP_X = 128.0                                      # front stiffener plate half width (clear of the towers and nut plates)
T_FP = G127                                       # 12.7 mm: stiff, and its weight seats the front nuts (docs)
FP_Z1 = Z_BED - 6.0
# ---- Z drive: three towers of laser-cut plates, one belt, one motor ----------------------------------------------------
# lower 608: radial only, located by three flats in H1 and seated on R1. Upper 608: the axial bearing, seated on R3,
# located by three flats in H2a/H2b, retained by R4. The pulley hangs under the upper bearing.
BRG_W = 7.0
T_R1F, T_R0R = G64, G32                          # R1 6.35 on the tray (front) or on a 3.175 base plate R0 (rear, on the rail)
Z_R1T = Z_TRAY + T_R1F                           # top of R1 = lower bearing's underside
T_H1 = G48
T_R3, T_H2A, T_H2B, T_R4 = G48, G48, B23, G32
ZB = 61.84                                       # Z belt plane: above the supply (53.2) and its terminal cover, below the carrier
Z_HUB = ZB + 10.5                                # pulley hub (upper end) = shim's underside
T_SHIM = G16
Z_UB = Z_HUB + T_SHIM                            # upper bearing's underside
Z_R3 = Z_UB - T_R3
Z_H2T = Z_UB + T_H2A + T_H2B
Z_R4T = Z_H2T + T_R4
Z_TOPNUT = Z_UB + BRG_W + 13.5                   # origin of the inverted T8 nut (barrel down on the inner ring)
SEAT_HOLE = 19.6                                 # shoulder plates: the outer ring bears from D2 19.2 to its OD
FLAT_R = 11.0                                    # three flats inscribed at the 608's OD (laser-cut, no bore)
TW_R = 17.0                                      # tower plate radius round the screw
POST_R = 25.0
RAIL_BOLT = 26.0                                 # tower-to-rail M5 bolts, +/- along the rail
ZM_XY = (44.0, 128.0)                            # Z motor axis (in front of the bottom back rail, clear of it)
T_DP = G64                                       # drive plate (motor and tensioner) on the rear tower's posts
Z_DPT = ZB - 10.5 - 0.3                          # drive plate top (pulleys' hubs 0.3 above)
Z_DPB = Z_DPT - T_DP                             # = motor mounting face
ZT_XY = (-20.0, 130.0)                           # tensioner idler on the belt's back: the motor gets ~127 degrees of wrap
ZT_SLOT = 3.0
Z_SCREW_L = 300.0
Z_BELT_L = 1138.0
# Y endstop
ES_TRIG, ES_SIDE = 8.3, 9.0
LAND_X, LAND_Y1 = (-134.0, -116.5), 44.0
ES_SLOT = 2.0
ES_OT = 1.5
YIM_BOLTS = (-174.0, -126.0)
YEM_BOLTS = (89.0, 101.0)
Y_RAIL_C = -28.5
ES_SP = 4.0
ES_SP_X = 8.0
RAIL_SCREW_STEP = 2
BEAM_BOLT_X = (RAIL_X - 33.0, RAIL_X - 21.0)
STOP_X = (116.5, 126.0, 131.0, 143.0)
X_ES_Y = 20.3
# bed probe: OMRON E2E-X5ME1 34.5 mm behind the nozzle reading the PEI180's steel
PRB_MODEL = "E2E-X5ME1"
PRB_H = 2.0
PRB_X = 0.0
PRB_DY = 34.5
PRB_Y = HOT_OFF + PRB_DY
TY_F = TY + PRB_DY
YI_Y = YB0 + PL_Y0 - (TY_F + ES_OT) - 10.5
Z_PRB = Z_NOZZLE + PRB_H
PRB_CLAMP = (15.0, 20.0)
PM_T = 4.0                                        # aluminium compression sleeves (4 mm long) through the printed probe holder
PM_TP = PM_T - 0.6                                # the holder plate: 0.6 mm thinner than its sleeves (the printed minimum clearance
                                                  # 0.5, and open in every simulated build), so the screw clamps metal only
PM_Z0, PM_Z1 = Z_PRB + PRB_CLAMP[0] - Z_BEAM, Z_PRB + PRB_CLAMP[1] - Z_BEAM
TPX = 23.0
TP_Z0, TP_Z1 = -18.0, 38.0
TP_NOTCH = (3.0, 11.0)
TAB_R = (13.5, 38.5, -27.0, -14.0)
FC_X0, FC_X1 = TAB_R[0], TAB_R[1]
FC_FL = 8.5                                       # duct flange: holds two M3 heat-set inserts
FC_Z0, FC_ZF = TAB_R[2], -12.8
DUCT_Z0 = -31.0
DUCT_W = 1.6
FC_LUG_Y = R_TPR + ROTO_W + 1.5
PLEN = 7.0
PFAN = (30.3, FC_LUG_Y + PLEN + 5.0, -16.0)
PLEN_X0, PLEN_X1 = PFAN[0] - 16.5, PFAN[0] + 16.5
FC_SCREWS = [(19.0, -20.5), (30.5, -20.5)]
DUCT_OUT = (40.0, 52.0, -29.0, -23.0)
BLK_SCREWS = [(-9.5, 20.5), (9.5, 20.5)]          # belt bracket -> tool plate (x, z from Z_BEAM)
CLAMP_Y = (-1.8, 12.2)                            # belt clamp screws, from YB0: just in front of and behind the 9 mm belt
NUT_AF3, NUT_T3 = 5.5, 2.4


# =================================================================== helpers
def bx(x0, x1, y0, y1, z0, z1):
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


ycyl = lambda r, h: Rot(90, 0, 0) * Cylinder(r, h)
xcyl = lambda r, h: Rot(0, 90, 0) * Cylinder(r, h)


def zc(x, y, z0, z1, r):
    return Pos(x, y, (z0 + z1) / 2) * Cylinder(r, z1 - z0)


def slot_z(x, y, angle_deg, half_len, width, z0, z1):
    h = z1 - z0
    return Pos(x, y, (z0 + z1) / 2) * Rot(0, 0, angle_deg) * (
        Box(2 * half_len, width, h) + Pos(-half_len, 0, 0) * Cylinder(width / 2, h) + Pos(half_len, 0, 0) * Cylinder(width / 2, h))


def hex_z(x, y, z0, z1, af, turn=0.0):
    """Hexagonal through-hole (across flats af) square to Z: a captive-nut pocket in a laser-cut plate."""
    return Pos(x, y, z0) * extrude(Rot(0, 0, turn) * RegularPolygon(af / 2, 6, major_radius=False), z1 - z0)


def hex_y(x, y0, y1, z, af, turn=0.0):
    return Pos(x, y1, z) * Rot(90, 0, 0) * extrude(Rot(0, 0, turn) * RegularPolygon(af / 2, 6, major_radius=False), y1 - y0)


def fillet_z(x, y, sx, sy, r, z0, z1):
    return (Pos(x + sx * r / 2, y + sy * r / 2, (z0 + z1) / 2) * Box(r, r, z1 - z0)
            - Pos(x + sx * r, y + sy * r, (z0 + z1) / 2) * Cylinder(r, z1 - z0))


def fillet_x(y, z, sy, sz, r, x0, x1):
    return (Pos((x0 + x1) / 2, y + sy * r / 2, z + sz * r / 2) * Box(x1 - x0, r, r)
            - Pos((x0 + x1) / 2, y + sy * r, z + sz * r) * Rot(0, 90, 0) * Cylinder(r, x1 - x0))


def fillet_y(x, z, sx, sz, r, y0, y1):
    return (Pos(x + sx * r / 2, (y0 + y1) / 2, z + sz * r / 2) * Box(r, y1 - y0, r)
            - Pos(x + sx * r, (y0 + y1) / 2, z + sz * r) * Rot(90, 0, 0) * Cylinder(r, y1 - y0))


def round_profile(shape, r=1.0, t=None):
    """Round the convex corners of a cut profile: the straight edges through the sheet's thickness t (an edge of length t
    between two planar faces), where the profile turns outward. Laser cutting makes a radius for nothing
    (DESIGN_GUIDELINES: no sharp corners). t defaults to the part's smallest bounding-box size (a flat part)."""
    if t is None:
        bb = shape.bounding_box()
        t = min(bb.size.X, bb.size.Y, bb.size.Z)

    def candidates(sh):
        out = []
        faces = list(sh.faces())
        for e in sh.edges():
            if e.geom_type != GeomType.LINE or abs(float(e.length) - t) > 0.02:
                continue
            fs = [f for f in faces if any(e.is_same(x) for x in f.edges())]
            if len(fs) != 2 or any(f.geom_type != GeomType.PLANE for f in fs):
                continue
            n1, n2 = (np.array(tuple(f.normal_at(f.center()))) for f in fs)
            if abs(n1 @ n2) > 0.99:
                continue
            p = np.array(tuple(e.position_at(0.5)))
            m = (n1 + n2) / np.linalg.norm(n1 + n2)
            if any(so.is_inside(tuple(p + 0.05 * m)) for so in sh.solids()):
                continue
            out.append(e)
        return out
    es = candidates(shape)
    if not es:
        return shape
    for rr in (r, 0.75 * r, 0.5 * r):
        try:
            return fillet(es, rr)
        except Exception:
            pass
    sh = shape
    for _ in range(len(es)):
        done = False
        for e in candidates(sh):
            for rr in (r, 0.5 * r):
                try:
                    sh = fillet([e], rr)
                    done = True
                    break
                except Exception:
                    continue
            if done:
                break
        if not done:
            break
    return sh


def three_flats(x, y, z0, z1, r_flat=FLAT_R, r_relief=12.0):
    """Hole that locates a 608's outer ring on three laser-cut flats inscribed at its OD, with relief arcs between."""
    h = z1 - z0
    hole = Pos(x, y, (z0 + z1) / 2) * Cylinder(r_relief, h)
    for k in range(3):
        a = k * 120.0 + 90.0
        hole -= Pos(x, y, (z0 + z1) / 2) * Rot(0, 0, a) * Pos(r_flat + 5.0, 0, 0) * Box(10.0, 2 * r_relief, h)
    return hole


def bent_L(t, r, h_a, l_b, w, holes_a=(), holes_b=()):
    """A 90-degree sheet bend drawn as made (inside radius r, outside r + t), in a local frame: leg A in the YZ plane at
    x 0..t rising to z = h_a; leg B in the XY plane at z 0..t reaching to x = l_b; width w along Y (centred). Holes:
    (y, z, dia) on leg A, (x, y, dia) on leg B."""
    c = t + r
    leg_a = bx(0, t, -w / 2, w / 2, c, h_a)
    leg_b = bx(c, l_b, -w / 2, w / 2, 0, t)
    ring = Pos(c, 0, c) * Rot(90, 0, 0) * (Cylinder(c, w) - Cylinder(r, w))
    ring &= bx(0, c, -w / 2, w / 2, 0, c)
    s = leg_a + leg_b + ring
    for y, z, dia in holes_a:
        s -= Pos(t / 2, y, z) * xcyl(dia / 2, t)
    for x, y, dia in holes_b:
        s -= Pos(x, y, t / 2) * Cylinder(dia / 2, t)
    return s


def sheet(d, name, shape, material, body="world", finish="bare", r=1.0, **meta):
    """A laser-cut part: outside profile corners rounded, the finish declared, process sheet."""
    return d.add(name, round_profile(shape, r), material=material, body=body, process="sheet",
                 meta={"finish": finish, **meta})


def mount_pcb(d, name, comp, holes_key, size, screw_len, sp_len, group, use=None):
    names = []
    for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][holes_key]):
        if use is not None and i not in use:
            continue
        place(d, f"{name}_spacer_{i}", spacer_round(size, sp_len), Location((hx, hy, Z_TRAY)))
        pcb_t = 1.5 if size == "M2.5" else 1.6
        add_screw(d, f"{name}_screw_{i}", size, screw_len, at=(hx, hy, Z_TRAY + sp_len + pcb_t),
                  clamps=(name, f"{name}_spacer_{i}", "electronics_tray"))
        add_washer(d, f"{name}_washer_{i}", size, (hx, hy, 20.0), (0, 0, -1), screw=f"{name}_screw_{i}")
        add_nut(d, f"{name}_nut_{i}", size, at=(hx, hy, 20.0 - WASHER["normal"][size][2]), direction=(0, 0, -1), screw=f"{name}_screw_{i}")
        d.join(f"{name}_nut_{i}", "electronics_tray", "clamped through its washer")
        names += [f"{name}_spacer_{i}", f"{name}_screw_{i}", f"{name}_washer_{i}", f"{name}_nut_{i}"]
    group += [name] + names


def bolt_nut(d, name, size, length, head_at, direction, body, clamps, nut_at=None, washer_head=True, washer_nut=True,
             large=False, threads_into=None, nyloc=False):
    """Through-bolt: screw (washer under the head), what it clamps, washer and nut on the far side. head_at = face the
    head's washer bears on; nut_at = face the nut's washer bears on (along `direction`)."""
    add_screw(d, name, size, length, at=head_at, direction=direction, body=body, clamps=clamps,
              washer=("large" if large else True) if washer_head else False, threads_into=threads_into)
    if nut_at is not None:
        dvec = np.array(direction, float) / np.linalg.norm(direction)
        at = np.array(nut_at, float)
        if washer_nut:
            add_washer(d, f"{name}_nwasher", size, tuple(at), tuple(dvec), body=body, screw=name,
                       series="large" if large else "normal")
            at = at + dvec * WASHER["large" if large else "normal"][size][2]
        add_nut(d, f"{name}_nut", size, at=tuple(at), direction=tuple(dvec), body=body, screw=name)
        if washer_nut and clamps:
            d.join(f"{name}_nut", clamps[-1], "clamped through its washer")
        if nyloc:
            d.bom_extra(f"NYLOC-{size}-UPGRADE", 1, 0.03)


def captive_nut(d, screw, at, direction, part, body="world"):
    """Washer and ISO 10511 nyloc nut captured in a printed pocket (nut_pocket) of `part`: at = the pocket face the washer
    bears on, direction = along the screw, away from its head."""
    dvec = np.array(direction, float)
    add_washer(d, f"{screw}_nwasher", "M3", tuple(at), tuple(dvec), body=body, screw=screw)
    add_nut(d, f"{screw}_nut", "M3", at=tuple(np.array(at) + dvec * WASHER["normal"]["M3"][2]), direction=tuple(dvec), body=body,
            screw=screw, standard="iso10511")
    d.join(f"{screw}_nut", part, "captive nut in a printed pocket (flats against the slot's walls), slid in on the bench")
    d.join(f"{screw}_nwasher", part, "washer captured in the printed pocket, under the nut")


def through_bolt_nyloc(d, name, length, head_at, direction, clamps, nut_face, body="world"):
    """M3 through-bolt for a printed part: washer under the head, washer and ISO 10511 nyloc nut on `nut_face` (the face
    the nut's washer bears on, on the side with access)."""
    dvec = np.array(direction, float) / np.linalg.norm(direction)
    sc = add_screw(d, name, "M3", length, at=head_at, direction=tuple(dvec), body=body, clamps=clamps, washer=True)
    sc.meta["torque_nm"] = PRINTED_JOINT_TORQUE
    add_washer(d, f"{name}_nwasher", "M3", tuple(nut_face), tuple(dvec), body=body, screw=name)
    add_nut(d, f"{name}_nut", "M3", at=tuple(np.array(nut_face) + dvec * WASHER["normal"]["M3"][2]), direction=tuple(dvec),
            body=body, screw=name, standard="iso10511")
    d.join(f"{name}_nut", clamps[-1], "clamped through its washer")
    return [name, f"{name}_washer", f"{name}_nwasher", f"{name}_nut"]


def bolt_length(grip, nut_h=4.0, washers=2, past=1.0):
    """Shortest standard M3 cap screw that passes a grip, two washers and a nyloc nut by at least `past` mm."""
    need = grip + washers * WASHER["normal"]["M3"][2] + nut_h + past
    return next(L for L in (10, 12, 16, 20, 25, 30, 35, 40, 45, 50) if L >= need - 1e-9)


def convex_hull(pts):
    """Andrew's monotone chain; returns the hull counter-clockwise."""
    P = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and (h[-1][0] - h[-2][0]) * (p[1] - h[-2][1]) - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0]) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(reversed(P))
    return lo[:-1] + up[:-1]


def screw_len(stack, nut_h, past=0.5, choices=(6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80)):
    need = stack + nut_h + past
    return next(L for L in choices if L >= need - 1e-6)


# =================================================================== part shapes
def back_plate_shape(carriage_holes):
    """4.75 mm 6061 on the two Z blocks. The rear beam is bolted to its front face (three M5 into T-nuts), the rear nut
    plate's tongue passes through a slot (1.5 mm clear all round: not a locating fit), the bed tie is bolted to it."""
    yc = (Y_PF + Y_CAR) / 2
    p = Pos(0, yc, (BP_Z0 + BP_Z1) / 2) * Box(BP_W, T_BP, BP_Z1 - BP_Z0)
    for hx, hy, hz in carriage_holes:
        p -= Pos(hx, yc, hz) * ycyl(4.8 / 2, T_BP)
    for x in RB_BOLTS:
        p -= Pos(x, yc, Z_ARM) * ycyl(clearance_hole("M5") / 2, T_BP)
    p -= bx(-RNP_TW / 2 - 1.5, RNP_TW / 2 + 1.5, Y_PF, Y_CAR, Z_FL - 1.5, Z_FL + T_NPR + 1.5)
    for x in TIE_BOLT_X:
        p -= Pos(x, yc, TIE_BOLT_Z) * ycyl(clearance_hole("M5") / 2, T_BP)
    return p


RB_BOLTS = (-55.0, 0.0, 55.0)
RNP_TW = 50.0                         # rear nut plate's tongue width
TIE_SP = 8.0
TIE_ZT = Z_BED - TIE_SP
TIE_X = (-20.0, 20.0)
TIE_W = 54.0
TIE_BOLT_X = (-15.0, 15.0)
TIE_LEG = 20.0                        # vertical leg of the bent tie, down the back plate's face
TIE_BOLT_Z = TIE_ZT - 14.0


def bed_shape_():
    """9.525 mm MIC-6 cast plate, laser cut (faces as cast): only through holes. The posts and the tie screw into steel
    thread inserts (drilled 5.2, STI tapped, insert fitted by the builder): the top face stays flat for the sheet."""
    b = bx(-BED / 2, BED / 2, BED_Y0 - BED_FX, BED_Y1, Z_BED, Z_BED + T_BED)
    for x, y in BED_MOUNTS:
        b -= zc(x, y, Z_BED, Z_BED + T_BED, 2.6)       # 5.2: drilled for an M5 STI tap, insert fitted by the builder
    for x in TIE_X:
        b -= zc(x, TIE_Y, Z_BED, Z_BED + T_BED, 2.6)
    return b


def tower_plate(x0, y0, z0, z1, posts, rails=(), centre=None, post_hole="M5", rail_hole=5.5, extra=(), lobe=7.8, rail_lobe=9.8):
    """One plate of a lead-screw tower: the convex hull of a disc round the screw and discs round its posts and rail
    bolts (a polygon of short straight cuts: no sharp corner, no blend surfaces)."""
    circ = lambda cx, cy, r: [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    pts = circ(x0, y0, TW_R)
    for px, py in posts:
        pts += circ(px, py, lobe)
    for rx, ry in rails:
        pts += circ(rx, ry, rail_lobe)
    s = Pos(0, 0, z0) * extrude(Polygon(*convex_hull(pts), align=None), z1 - z0)
    for e in extra:
        s += e
    if centre == "seat":
        s -= zc(x0, y0, z0, z1, SEAT_HOLE / 2)
    elif centre == "flats":
        s -= three_flats(x0, y0, z0, z1)
    elif centre == "clear":
        s -= zc(x0, y0, z0, z1, 6.0)
    for px, py in posts:
        if post_hole == "tip":     # room for the post bolt's tip
            s -= zc(px, py, z0, z1, 4.0)
        elif post_hole == "hex":     # captive M5 nut: the same frame as add_nut's, so the flats match
            s -= Location(Plane(origin=(px, py, z1), z_dir=(0, 0, -1))) * extrude(RegularPolygon(8.15 / 2, 6, major_radius=False), z1 - z0)
        elif post_hole:
            s -= zc(px, py, z0, z1, clearance_hole("M5") / 2)
    for rx, ry in rails:
        s -= zc(rx, ry, z0, z1, rail_hole / 2)
    return s


def tool_plate_outline(y0, y1):
    box = lambda x0, x1, z0, z1: bx(x0, x1, y0, y1, Z_BEAM + z0, Z_BEAM + z1)
    tp = box(-TPX, TPX, TP_Z0, TP_Z1) + box(*TAB_R)
    r = 3.0
    tp -= box(-TPX - 1.0, -TPX + TP_NOTCH[0], TP_Z0 - 1.0, TP_NOTCH[1])
    tp += fillet_y(-TPX + TP_NOTCH[0], Z_BEAM + TP_NOTCH[1], -1, -1, r, y0, y1)
    tp += fillet_y(TAB_R[0], Z_BEAM + TP_Z0, -1, -1, r, y0, y1)
    tp += fillet_y(TPX, Z_BEAM + TP_Z0, 1, 1, r, y0, y1)
    # lightening window above the belt bracket's bolts
    tp -= Pos(-6.0, (y0 + y1) / 2, Z_BEAM + 29.6) * Rot(90, 0, 0) * extrude(RectangleRounded(22.0, 6.4, 3.0), (y1 - y0) / 2, both=True)
    return tp


ROTO_HOLES = lambda: [(ROTO_O[0], ROTO_O[2]), (ROTO_O[0] + ROTO_H2[0], ROTO_O[2] + ROTO_H2[2])]
BRK_Z = 20.25                          # belt bracket bolts, from Z_BEAM


def tool_plate_front_shape():
    """3.175 mm 6061 on the X guide block (four M3x6, heads from the rear). PEM M3 nuts clinched in it take the Roto's
    screws, so those screws clamp the Roto, the rear plate and this plate together; clearance holes for the belt
    bracket and the duct."""
    y0, y1 = YB0 + R_TPF, YB0 + R_TPF + T_TPF
    tp = tool_plate_outline(y0, y1)
    for x in (-10, 10):
        for z in (-10, 10):
            tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TPF)
    for x, z in ROTO_HOLES():
        tp -= Pos(x, (y0 + y1) / 2, z) * ycyl(4.22 / 2, T_TPF)          # PEM S-M3-1 mounting hole
    for x, z in BLK_SCREWS:
        tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + BRK_Z) * ycyl(clearance_hole("M3") / 2, T_TPF)
    for x, z in FC_SCREWS:
        tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TPF)
    return tp


def tool_plate_rear_shape():
    """4.75 mm 6061 behind the front plate: 6.5 mm holes are the counterbores of the block screws' heads; hex pockets hold
    the belt bracket's nuts (they bear on the front plate) and clear the PEM nuts' heads; the Roto's flat side sits on
    its rear face."""
    y0, y1 = YB0 + R_TPF + T_TPF, YB0 + R_TPR
    tp = tool_plate_outline(y0, y1)
    for x in (-10, 10):
        for z in (-10, 10):
            tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(3.25, T_TPR)
    for x, z in ROTO_HOLES():
        tp -= Location(Plane(origin=(x, y0, z), z_dir=(0, 1, 0))) * extrude(RegularPolygon(5.65 / 2, 6, major_radius=False), T_TPR)
    for x, z in BLK_SCREWS:
        tp -= Location(Plane(origin=(x, y0, Z_BEAM + BRK_Z), z_dir=(0, 1, 0))) * extrude(RegularPolygon(5.65 / 2, 6, major_radius=False), T_TPR)
    for x, z in FC_SCREWS:
        tp -= Pos(x, (y0 + y1) / 2, Z_BEAM + z) * ycyl(4.8 / 2, T_TPR)
    return tp


def nut_pocket(at, axis, up, extra_back=0.0):
    """Captive nut pocket for an M3 nyloc with its washer, as a solid to cut: at = the face the washer bears on (towards
    the screw head), axis = unit vector from that face away from the head, up = the direction the pocket opens (a slot the
    nut and washer slide in along), back / front: how far the slot runs beyond the axis on the closed side (none: it
    opens at `up`'s side). The nut sits flats-on against the slot's walls, so it cannot turn."""
    a, u = np.array(axis, float), np.array(up, float)
    w = np.cross(u, a)
    def slab(y0, y1, width, below):
        # from `below` under the axis (towards -u) to far out along +u (the opening), y0..y1 along the axis
        L = 40.0
        c = np.array(at, float) + a * (y0 + y1) / 2 + u * (L / 2 - below)
        return Location(Plane(origin=tuple(c), x_dir=tuple(w), z_dir=tuple(a))) * Box(width, L, y1 - y0)
    return (slab(0.0, POCKET_W, POCKET_WD, POCKET_WD / 2 + 0.2) +
            slab(POCKET_W - 0.01, POCKET_W + POCKET_NUT + extra_back, POCKET_AF, POCKET_AF / math.sqrt(3) + 0.2))


def part_duct_shape():
    """Printed ABS duct (v8's). No thread in the plastic: the two flange screws and the two fan screws are M3 through-bolts
    into nyloc nuts captured, with their washers, in printed pockets (the flange's from below, the fan bosses' from
    above), slid in on the bench before the duct is fitted: behind the flange is the duct's own air passage and behind the
    fan bosses is the Roto, 1.5 mm away, so there is no access for a loose nut. Clearance holes 3.6 (printed, vertical)."""
    yf, yl, yr = YB0 + R_TPR, YB0 + FC_LUG_Y, YB0 + FC_LUG_Y + PLEN
    z0, zf, zd = Z_BEAM + FC_Z0, Z_BEAM + FC_ZF, Z_BEAM + DUCT_Z0
    zt = Z_BEAM + PFAN[2] + 15.0
    w = DUCT_W
    c = bx(FC_X0, FC_X1, yf, yf + FC_FL, z0, zf)
    c += bx(FC_X0, FC_X1, yf + FC_FL, yl, zd, zf)
    c += bx(PLEN_X0, PLEN_X1, yl, yr, zd, zt)
    c -= bx(FC_X0 + w, FC_X1 - w, yf + FC_FL + w, yr, zd + 2.0, zf - w)
    c -= bx(PLEN_X0 + w, PLEN_X1 - w, yl + w, yr, zd + 2.0, zt - w)
    zb = Z_BEAM + PFAN[2] + 12.0
    for sx in (-12.0, 12.0):
        xb = PFAN[0] + sx
        c += bx(xb - 4.5, xb + 4.5, yl, yr, zb - 5.0, zt)
    for sx in (-12.0, 12.0):
        xb = PFAN[0] + sx
        c -= Pos(xb, yr - PLEN / 2, zb) * ycyl(PH3 / 2, PLEN)
        # pocket open at the top (+Z) and at the back (towards the Roto): the nut and washer drop in from above
        c -= nut_pocket((xb, yr - POCKET_WALL, zb), (0, -1, 0), (0, 0, 1), extra_back=1.0)
    y0, y1, oz0, oz1 = DUCT_OUT
    c -= bx(FC_X0 - 0.1, FC_X0 + w + 0.1, YB0 + y0, YB0 + y1, Z_BEAM + oz0, Z_BEAM + oz1)
    for x, z in FC_SCREWS:
        c -= Pos(x, yf + FC_FL / 2, Z_BEAM + z) * ycyl(PH3 / 2, FC_FL)
        c -= nut_pocket((x, yf + POCKET_WALL, Z_BEAM + z), (0, 1, 0), (0, 0, -1))     # opens at the flange's underside
    return c


PM_X = 12.0


def probe_mount_shape():
    """Printed ABS holder for the M12 probe on the Roto's rear face. The Roto's two screws pass through 6 mm aluminium
    sleeves (compression limiters) in 6.6 mm holes in it; the holder is 0.6 mm thinner than the sleeves, so the washer
    under each screw head bears on the sleeve's end only: the clamp load goes through metal, and the plastic is located on
    the sleeves and held between the Roto's face and the washers (0.6 mm play), carrying only the sensor. Closed 13 mm
    hole, the sensor clamped by its own two nuts."""
    y0 = YB0 + R_TPR + ROTO_W
    y1 = y0 + PM_TP
    ye = YB0 + PRB_Y + 10.5
    z0, z1 = Z_BEAM + PM_Z0, Z_BEAM + PM_Z1
    zt = ROTO_O[2] + ROTO_H2[2] + 5.0
    a = bx(-PM_X, PM_X, y0, y1, z0, Z_BEAM + 4.0)
    a += bx(-PM_X, 25.0, y0, y1, Z_BEAM + 4.0, zt)
    a += bx(-PM_X, PM_X, y1, ye, z0, z1)
    for sx in (-1, 1):
        a += bx(sx * 10.4, sx * PM_X, y1, ye - 6.0, z1, z1 + 9.0)
    a -= bx(-10.2, 10.2, y0, y1, z1, z1 + 6.6)
    a -= Pos(PRB_X, YB0 + PRB_Y, (z0 + z1) / 2) * Cylinder(13.0 / 2, z1 - z0)
    for x, z in ROTO_HOLES():
        a -= Pos(x, (y0 + y1) / 2, z) * ycyl(6.6 / 2, PM_TP)
        a -= Pos(x, y1 + 2.5, z) * ycyl(4.6, 5.0)        # relief round each screw's washer and head (the probe clamp's cheek)
    return a


USE_CUTOFFS = True


def build_electrical(d: Design) -> Electrical:
    """As v8, with: the earth point is an M5 stud with an M5 ring terminal, the frame's earth wire is 2.5 mm^2 (AWG 13,
    IEC 60204-1 for a protective conductor not sheathed with the line conductors), the probe's +24 V lead is a wire of its
    own from the supply's second output, and the part fan is the Coolerguys CG3010U24 (24 V, maker's sheet)."""
    from mechloop.electrical import add_board_5v_port

    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend", "part_fan", "x_endstop", "y_endstop", "bed_probe", "x_motor",
               "z_motor", "extruder"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed_plate")
    for nm in ("y_motor", "y_motor_l"):
        device_from(el, d, nm, connection="parallel")
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", ratings={"max_temp_c": 180.0},
                    sources={"points": "Klipper 'Generic 3950' (Keenovo R-T table)", "tau_s": "assumed 10 s (typical, unverified)"},
                    sensor_type="Generic 3950", points=THERMISTORS["Generic 3950"], tau_s=10.0, node="pad")
    embedded_device(el, d, "hotend", "hotend_thermistor", "thermistor", "ntc", "thermistor", **d.get("hotend").ratings["thermistor"])
    rf = d.get("extruder").ratings["fan"]
    embedded_device(el, d, "extruder", "hotend_fan", "fan", "fan", "fan",
                    ratings={"current_a": rf["current_a"], "volts": rf["volts"]},
                    sources={"current_a": "E3D Roto data sheet, 'Fan Specification': 5 V, 0.14 A"})
    add_board_5v_port(el, "control_board")
    device_from(el, d, "bed_tco")
    device_from(el, d, "psu_relay")
    el.add(Device("frame_earth", "earth_point", "earth_stud",
                  {"pe": Port("pe", "pe", "ring-M5", 20.0, at=(-FX / 2 - 6.0, 80.0, 10.0), multi=True, extra={"body": "world"})},
                  params={"bonds": "frame_bot_left"},
                  product={"product": "M5 ring terminals under an M5 screw and serrated washer in a T-nut", "vendor": "commodity",
                           "part_number": None, "form": "hardware", "off_the_shelf": True, "custom_pcb": False,
                           "builder_work": "crimp M5 ring terminals; scratch through the anodising under the serrated washer"}))
    zt = Z_TRAY + 8.0
    XL, ZL = -147.0, FZ - 6.0
    P1 = (147.4, 146.0, FZ + 2.0)
    yl = YB0 + R_TPR + ROTO_W + PM_T + 2.0
    el.loom("toolhead", [Waypoint("xbody", (-10.0, yl, Z_BEAM + 32.0), clamp="probe_mount"),
                         Waypoint("xbody", (23.0, yl, Z_BEAM + 32.0), clamp="probe_mount"),
                         Waypoint("world", (147.8, 138.0, FZ + 6.0), clamp="frame_top_right"), Waypoint("world", P1)],
            flex_length={1: 460.0})
    el.loom("drop_right", [("world", P1), ("world", (146.5, 153.0, FZ - 10.0)), ("world", (145.5, 156.0, FZ - 26.0)),
                           ("world", (145.0, 158.0, FZ - 46.0)), ("world", (145.0, 168.0, FZ - 74.0)),
                           ("world", (145.0, 170.0, 60.0)), ("world", (145.0, 150.0, 34.0))])
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (130.0, 46.0, zt)), ("world", (130.0, -26.0, zt))])
    el.loom("back", [("world", (140.0, 152.0, 30.0)), ("world", (130.0, 160.0, 12.0)), ("world", (66.0, 160.0, 12.0))])
    el.loom("gantry", [Waypoint("ybody", (-150.0, YB0 + PL_Y0 - 2.5, Z_PLATE + T_YP / 2), clamp="y_plate_left"),
                       Waypoint("world", (XL - 0.8, -176.0, ZL), clamp="frame_top_left"), ("world", (XL, -124.0, ZL))],
            flex_length={0: 270.0})
    el.loom("top_left", [("world", (XL, -118.0, ZL)), ("world", (XL, 136.0, ZL))])
    el.loom("drop_left", [("world", (XL, -120.0, ZL)),
                          ("world", (-143.0, -140.0, FZ - 24.0)), ("world", (-143.0, -150.0, FZ - FT_DROP - 30.0)),
                          ("world", (-143.0, -170.0, FZ - FT_DROP - 60.0)),
                          ("world", (-143.0, -170.0, 70.0)), ("world", (-140.0, -166.0, 26.0))])
    el.loom("front", [("world", (-140.0, -166.0, 26.0)), ("world", (60.0, -166.0, 26.0)), ("world", (72.0, -142.0, zt))])
    el.loom("bed", [Waypoint("zbody", (-40.0, Y_CAR + 3.0, BP_Z0 + 30.0), clamp="back_plate"),
                    Waypoint("zbody", (-40.0, Y_CAR + 3.0, BP_Z0 + 4.0), clamp="back_plate"),
                    Waypoint("world", (-40.0, TRAY_Y1 - 1.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 330.0})
    el.loom("mains", [("world", (-115.0, 9.0, zt)), ("world", (-108.0, 44.0, zt)), ("world", (-100.0, 84.0, zt))])
    tool, left = ["tray_right", "drop_right", "toolhead"], ["front", "drop_left"]
    mk = dict(conductors=1, insulation="pvc105")
    el.wire("mains L inlet-relay", "inlet.L", "psu_relay.LIN", 18, **mk)
    el.wire("mains L relay-supply", "psu_relay.LOT", "psu.L", 18, via=["mains"], **mk)
    el.wire("relay control", "control_board.PS-ON", "psu_relay.ctrl", 26, conductors=3)
    el.wire("mains N inlet-relay", "inlet.N", "psu_relay.N", 18, **mk)
    el.wire("mains N relay-supply", "psu_relay.N", "psu.N", 18, via=["mains"], **mk)
    el.wire("earth to supply", "inlet.PE", "psu.FG", 18, via=["mains"], **mk)
    # v8.1: 2.5 mm^2 (AWG 13): the frame's protective conductor runs on its own, not sheathed with the line conductors
    el.wire("earth to frame", "inlet.PE", "frame_earth.pe", 13, connector_b="ring-M5", **mk)
    el.wire("24 V to board", "psu.V+1", "control_board.POWER", 16, insulation="silicone")
    el.wire("bed heater", "control_board.HB", "bed_tco.a", BED_AWG, insulation=BED_INS, via=["bed"])
    el.wire("bed heater tail", "bed_tco.b", "bed_heater.in", BED_AWG, insulation=BED_INS, length=90.0)
    el.wire("bed thermistor", "control_board.THB", "bed_ntc.out", 26, insulation="silicone", via=["bed"])
    el.wire("hotend heater", "control_board.E0", "hotend.in", 20, insulation="silicone", via=tool, pigtail=(115.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, insulation="silicone", via=tool,
            pigtail=(130.0, "fiberglass"))
    el.wire("heat-sink fan 5 V", "control_board.5V", "hotend_fan.out", 26, via=tool,
            note="the Roto's fan is a 5 V part: always on from the board's 5 V pins, never on a 24 V fan output")
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    el.wire("bed probe", "control_board.Z-STOP", "bed_probe.out", 26, conductors=3, insulation="silicone", via=tool,
            note="signal and 0 V on the Z-STOP header; BAT85 diode in the signal lead at the board end, cathode to the sensor, heat-shrunk")
    # v8.1: the probe's +24 V lead is its own wire, from the supply's second +V terminal
    pr = d.get("bed_probe").meta["interfaces"]
    el.devices["bed_probe"].ports["vcc"] = Port("vcc", "power_in", "JST-XH", 1.0, conductors=1,
                                                at=tuple(pr.get("sensing_face", [(PRB_X, YB0 + PRB_Y, Z_PRB)])[0]),
                                                extra={"body": "xbody", "draw_a": 0.015})
    el.devices["bed_probe"].params.update(supply_v=24.0, supply_from="psu.V+2 (wire 'bed probe 24 V')", series_diode=True)
    el.wire("bed probe 24 V", "psu.V+2", "bed_probe.vcc", 26, conductors=1, insulation="silicone", via=tool,
            note="the sensor's brown lead; runs in the toolhead loom with the probe's signal pair")
    el.wire("extruder motor", "control_board.EM", "extruder.coils", 24, conductors=4, via=tool)
    el.wire("X motor", "control_board.XM", "x_motor.coils", 24, conductors=4, via=left + ["gantry"])
    el.wire("X endstop", "control_board.X-STOP", "x_endstop.out", 26, conductors=3, via=left + ["gantry"])
    el.wire("Y endstop", "control_board.Y-STOP", "y_endstop.out", 26, conductors=3, via=["tray_right", "drop_right"])
    el.wire("Y motor left", "control_board.ZBM", "y_motor_l.coils", 24, conductors=4, via=left + ["top_left"],
            note="mirror-image motor: swap one coil pair at the connector so both turn the belts the same way")
    el.wire("Y motor right", "control_board.ZAM", "y_motor.coils", 24, conductors=4, via=["tray_right", "drop_right"])
    el.wire("Z motor", "control_board.YM", "z_motor.coils", 24, conductors=4, via=["tray_right", "back"])
    el.wire("host serial + 5 V", "control_board.TFT", "host.GPIO", 26, conductors=4)
    el.firmware = {
        "kind": "klipper",
        "steppers": {"x": {"run_current": RUN_CURRENT["x"]}, "y": {"run_current": RUN_CURRENT["y"]},
                     "z": {"run_current": RUN_CURRENT["z"]},
                     "extruder": {"motors": ["extruder"], "run_current": RUN_CURRENT["extruder"]}},
        "heaters": {"extruder": {"heater": "hotend", "sensor": "hotend_thermistor", "control": "pid", "min_temp": 0,
                                 "max_temp": 280, "targets": [250.0], "verify_heater": {}},
                    "heater_bed": {"heater": "bed_heater", "sensor": "bed_ntc", "control": "pid", "min_temp": 0,
                                   "max_temp": BED_MAX_C + 10.0, "targets": [60.0, BED_MAX_C], "verify_heater": {}}},
        "fans": {"part_fan": {"device": "part_fan", "role": "part"}, "hotend_fan": {"device": "hotend_fan", "role": "heatsink"}},
    }
    hi = d.get("hotend").meta["interfaces"]
    rc = hi["heatercore_dia"] / 2
    hb = (-rc, YB0 + HOT_OFF - rc, hi["heater_block_box"][0][2], rc, YB0 + HOT_OFF + rc, hi["heater_block_box"][1][2])
    el.hot_parts = {"hotend": {"temp": 250.0, "box": hb}, "bed": BED_MAX_C}
    el.bay = Bay(devices=[n for n in ("psu", "control_board", "host", "psu_relay") if n in el.devices],
                 enclosed=False, vent_area_m2=0.02, height_m=0.05)
    el.sync_cables(d)
    add_electrical_bom(el, d)
    d.bom_extra(f"FUSE-5x20-T{FUSE_A:g}A", 2, 0.3)
    d.bom_extra("DIODE-BAT85", 1, 0.1)
    return el


def build_tower(d, tag, x0, y0, rear, post_xy, rail_xy, rail_part):
    """One lead-screw tower of laser-cut 6061 plates (bottom up): R1 (seat of the lower 608, hex pockets for the post
    bolts' nuts), H1 (three flats locate the lower 608), aluminium spacers, R3 (seat of the upper 608), H2a + H2b (three
    flats; 7.04 mm, so the outer ring is not loaded by the bolts), R4 (retains the outer ring, 0.04 mm float). The pulley
    hangs under the upper bearing on an 8 x 12 shim; a brass T8 nut screwed down on the upper inner ring carries the
    bed's share (thread-locked). Two rail bolts clamp H1 and R1 (and the tray) to the bottom rail's T-nuts; two post
    bolts clamp R4 down to H1 through the spacers. Returns the names of its parts."""
    t_r1 = T_R1F
    z_r1b = Z_R1T - t_r1
    names = []
    pre = "z_rear" if rear else f"z{tag}"
    P = lambda n: f"{pre}_{n}"

    def plate(n, z0, z1, centre, mat=AL, post_hole="M5", rails=False, rail_hole=5.5, extra=(), lobe=7.8, rail_lobe=9.8):
        sheet(d, P(n), tower_plate(x0, y0, z0, z1, post_xy, rail_xy if rails else (), centre, post_hole, rail_hole, extra, lobe, rail_lobe), mat)
        names.append(P(n))

    # R1's rail-bolt holes are clearance only (the bolts' heads and washers bear on H1): as wide as R1 is thick
    plate("r1", z_r1b, Z_R1T, "seat", post_hole="hex", rails=True, rail_hole=t_r1 + 0.1, lobe=11.2,
          rail_lobe=(t_r1 + 0.1) / 2 + t_r1 + 0.3)
    if rear:     # base plate standing in for the tray's thickness: clearance holes only
        plate("r0", z_r1b - T_R0R, z_r1b, None, post_hole="tip", rails=True, rail_hole=T_R0R + 3.3, lobe=11.2,
              rail_lobe=(t_r1 + 0.1) / 2 + t_r1 + 0.3)
    plate("h1", Z_R1T, Z_R1T + T_H1, "flats", rails=True, lobe=8.0)
    plate("r3", Z_R3, Z_UB, "seat")
    plate("h2a", Z_UB, Z_UB + T_H2A, "flats")
    plate("h2b", Z_UB + T_H2A, Z_H2T, "flats", mat=AL_BEND)
    plate("r4", Z_H2T, Z_R4T, "seat")
    # shim on the upper inner ring: 8.6 bore (not a fit on the 8 mm screw), 12 OD (inside the ring's shoulder d1 12.15)
    sheet(d, P("shim"), (zc(x0, y0, Z_HUB, Z_UB, 6.05) & bx(x0 - 5.9, x0 + 5.9, y0 - 7.0, y0 + 7.0, Z_HUB, Z_UB))
          - zc(x0, y0, Z_HUB, Z_UB, 4.275), AL, r=0.5)
    d.join(P("shim"), f"leadscrew{tag}", "slides on the screw (8.55 bore)")
    names.append(P("shim"))
    lo, hi = place(d, P("bearing_lo"), bearing("608"), Location((x0, y0, Z_R1T + BRG_W / 2))), \
        place(d, P("bearing_hi"), bearing("608"), Location((x0, y0, Z_UB + BRG_W / 2)))
    scr = place(d, f"leadscrew{tag}", leadscrew_t8(Z_SCREW_L, lead=2.0), Location((x0, y0, Z_R1T)))
    pul = place(d, f"z_pulley{tag}", gt2_pulley(20, bore=8.0, belt_width=6.0), Location((x0, y0, Z_HUB), (180, 0, 0)))
    nut = place(d, P("topnut"), leadscrew_nut_t8(), Location((x0, y0, Z_TOPNUT), (180, 0, 0)))
    names += [lo.name, hi.name, scr.name, pul.name, nut.name]
    d.join(lo.name, P("r1"), "seated on its shoulder plate")
    d.join(lo.name, P("h1"), "located by three laser-cut flats")
    d.join(hi.name, P("r3"), "seated on its shoulder plate")
    d.join(hi.name, P("h2a"), "located by three laser-cut flats")
    d.join(hi.name, P("r4"), "outer ring retained, 0.04 mm axial float")
    d.join(scr.name, lo.name, "radial support (screw slides in the inner ring)")
    d.join(nut.name, scr.name, "thread (thread-locked, screwed down on the inner ring)")
    d.join(nut.name, hi.name, "bears on the inner ring: carries the bed's share")
    d.join(pul.name, scr.name, "set_screw (torque only; holds the screw down through the shim)")
    d.join(P("shim"), pul.name, "clamped between hub and inner ring")
    d.join(P("shim"), hi.name, "clamped between hub and inner ring")
    # spacers between H1 and R3 (the rear tower's are split by the drive plate)
    z_h1t = Z_R1T + T_H1
    segs = [(z_h1t, Z_DPB), (Z_DPT, Z_R3)] if rear else [(z_h1t, Z_R3)]
    for i, (px, py) in enumerate(post_xy):
        sp = []
        for k, (za, zb) in enumerate(segs):
            nm = P(f"spacer_{i}{'' if len(segs) == 1 else 'ab'[k]}")
            place(d, nm, spacer_round("M5", round(zb - za, 3), "aluminium"), Location((px, py, za)))
            sp.append(nm)
        names += sp
        clamps = (P("r4"), P("h2b"), P("h2a"), P("r3"), *sp, *(("z_drive_plate",) if rear else ()), P("h1"))
        L = screw_len(Z_R4T - Z_R1T + W5, POST_NUT, 0.5, choices=(55, 60, 65, 70, 75))
        add_screw(d, P(f"post_{i}"), "M5", L, at=(px, py, Z_R4T), direction=(0, 0, -1), clamps=clamps, washer=True)
        add_nut(d, P(f"post_{i}_nut"), "M5", at=(px, py, Z_R1T), direction=(0, 0, -1), screw=P(f"post_{i}"))
        d.join(P(f"post_{i}_nut"), P("r1"), "captive in a hex pocket")
        names += [P(f"post_{i}"), P(f"post_{i}_washer"), P(f"post_{i}_nut")]
    for i, (rx, ry) in enumerate(rail_xy):
        cl = (P("h1"), P("r1")) + ((P("r0"),) if rear else ("electronics_tray",))
        add_screw(d, P(f"rail_bolt_{i}"), "M5", 20, at=(rx, ry, Z_R1T + T_H1), direction=(0, 0, -1), clamps=cl,
                  threads_into=rail_part, tnut=True, washer=True)
        names += [P(f"rail_bolt_{i}"), P(f"rail_bolt_{i}_washer")]
    return names


def build_frame_z():
    d = Design("printer_v8_1", envelope=ENVELOPE, base="frame_bot_left")
    d.manufacturing = {"shop": "sendcutsend", "sheet": {"method": "laser"},
                       "printer": {"build_volume": (220.0, 220.0, 220.0), "nozzle": 0.4},
                       "print_settings": dict(PRINT_ABS)}
    # ================= frame (v8) ================================================
    for sx, n in ((-1, "left"), (1, "right")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FY), Location((sx * RAIL_X, 0, z), (0, 0, 90)))
    for sy, n in ((-1, "front"), (1, "back")):
        for z, lvl in ((FZ - (FT_DROP if sy < 0 else 0.0), "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FX - 40), Location((0, sy * (FY / 2 - 10), z)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            place(d, f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}", extrusion_2020(FZ - 30),
                  Location((sx * RAIL_X, sy * (FY / 2 - 10), (FZ + 10) / 2), (0, 90, 0)))
    k = 0
    for sx in (-1, 1):
        side = "left" if sx < 0 else "right"
        for sy in (-1, 1):
            post = f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}"
            cross = "front" if sy < 0 else "back"
            yi = sy * (FY / 2 - 20)
            for lvl, zcen, zdir in (("top", FZ - 10, -1), ("bot", 20, 1)):
                add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{side}", post, (sx * RAIL_X, yi, zcen), (0, -sy, 0), (0, 0, zdir)); k += 1
                if lvl == "top":
                    add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{cross}", post,
                                       (sx * (RAIL_X - 10), sy * (FY / 2 - 10), FZ - (FT_DROP if sy < 0 else 0.0) - 10.0),
                                       (-sx, 0, 0), (0, 0, -1)); k += 1
                else:
                    add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{cross}", f"frame_{lvl}_{side}",
                                       (sx * (RAIL_X - 10), yi, 10), (-sx, 0, 0), (0, -sy, 0)); k += 1
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"upright_{n}", extrusion_2020(FZ - 30), Location((sx * UP_X, UP_Y, (FZ + 10) / 2), (0, 90, 0)))
        for lvl, zcen, zdir in (("bot", 20, 1), ("top", FZ - 10, -1)):
            add_corner_bracket(d, f"brkt_up_{lvl}_in_{n}", f"frame_{lvl}_back", f"upright_{n}", (sx * (UP_X - 10), UP_Y, zcen), (-sx, 0, 0), (0, 0, zdir))
            add_corner_bracket(d, f"brkt_up_{lvl}_out_{n}", f"frame_{lvl}_back", f"upright_{n}", (sx * (UP_X + 10), UP_Y, zcen), (sx, 0, 0), (0, 0, zdir))

    # ================= Z guides: one ZF block per rail ===========================
    carriage_holes = []
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"z_rail_{n}", mgn12_rail(Z_RAIL_L), Location(Plane(origin=(sx * UP_X, Y_FACE, Z_RAIL_C), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
        for i, (hx, hy, hz) in enumerate(rail.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"z_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy - 3.5, hz), direction=(0, 1, 0), threads_into=f"upright_{n}", tnut=True)
        # v8.1: clearance class ZF. The three screws hold the carrier's tilt; the blocks only locate it (x, y, yaw), so a
        # block that does not resist tilt keeps every nut seated when the screws differ in height (docs/PRINTER_V8_1.md)
        car = place(d, f"z_carriage_{n}", mgn12h_carriage(preload="ZF"),
                    Location(Plane(origin=(sx * UP_X, Y_FACE, ZC2), x_dir=(0, 0, 1), z_dir=(0, -1, 0))), body="zbody", guides="z")
        holes = car.meta["interfaces"]["mount_holes_m3"]
        carriage_holes += holes
        for i, (hx, hy, hz) in enumerate(holes):
            add_screw(d, f"z_carriage_{n}_screw_{i}", "M3", 8, at=(hx, hy - T_BP, hz), direction=(0, 1, 0), body="zbody",
                      threads_into=f"z_carriage_{n}", clamps=("back_plate",), washer=True)
    sheet(d, "back_plate", back_plate_shape(carriage_holes), AL, body="zbody")

    # ================= bed carrier: 2020 rectangle, nut plates, front stiffener ===
    place(d, "rear_beam", extrusion_2020(2 * RB_X), Location((0, RB_Y, Z_ARM)), body="zbody")
    for i, x in enumerate(RB_BOLTS):
        add_screw(d, f"rear_beam_bolt_{i}", "M5", 10, at=(x, Y_CAR, Z_ARM), direction=(0, -1, 0), body="zbody",
                  threads_into="rear_beam", tnut=True, clamps=("back_plate",), washer=True)
    place(d, "front_beam", extrusion_2020(2 * FB_X), Location((0, FB_Y, Z_ARM)), body="zbody")
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"bed_arm_{n}", extrusion_2020(ARM_Y1 - ARM_Y0), Location((sx * ARM_X, (ARM_Y0 + ARM_Y1) / 2, Z_ARM), (0, 0, 90)), body="zbody")
        # two cast brackets at each arm end, both legs on T-nuts: one in the inboard corner, one under the arm (the
        # outboard side is where the bed posts' lower nuts are)
        xs = sx * (ARM_X - 10.0)
        add_corner_bracket(d, f"bed_arm_{n}_rbracket_i", f"bed_arm_{n}", "rear_beam", (xs, ARM_Y1, Z_ARM), (0, -1, 0), (-sx, 0, 0), body="zbody")
        add_corner_bracket(d, f"bed_arm_{n}_fbracket_i", f"bed_arm_{n}", "front_beam", (xs, ARM_Y0, Z_ARM), (0, 1, 0), (-sx, 0, 0), body="zbody")
        add_corner_bracket(d, f"bed_arm_{n}_rbracket_u", f"bed_arm_{n}", "rear_beam", (sx * ARM_X, ARM_Y1, Z_ARM - 10.0), (0, -1, 0), (0, 0, -1), body="zbody")
        add_corner_bracket(d, f"bed_arm_{n}_fbracket_u", f"bed_arm_{n}", "front_beam", (sx * ARM_X, ARM_Y0, Z_ARM - 10.0), (0, 1, 0), (0, 0, -1), body="zbody")
    # front stiffener: 6.35 mm 6061 on the front beam's front face (a deep beam between the arms and the nut plates)
    fp = bx(-FP_X, FP_X, FB_FACE - T_FP, FB_FACE, Z_ARM - 19.2, FP_Z1)
    FP_BOLTS = (-110.0, -40.0, 40.0, 110.0)
    for x in FP_BOLTS:
        fp -= Pos(x, FB_FACE - T_FP / 2, Z_ARM) * ycyl(12.8 / 2, T_FP)
    sheet(d, "front_plate", fp, AL, body="zbody")
    for i, x in enumerate(FP_BOLTS):
        add_screw(d, f"front_plate_bolt_{i}", "M5", 18, at=(x, FB_FACE - T_FP, Z_ARM), direction=(0, 1, 0), body="zbody",
                  threads_into="front_beam", tnut=True, clamps=("front_plate",), washer="large")
    # nut plates: 6061 on the beams' top faces (9.525 mm rear, 6.35 mm front); each floating T8 nut hangs under one (the carrier sits on its
    # flange), its barrel in a 16 mm hole, turned by a pin: an M3 through a 6 mm aluminium sleeve in a radial slot
    zn0 = Z_FL
    nut_sets = []
    zn1 = Z_FL + T_NPR
    rnp = bx(-39.0, 39.0, RB_Y - 13.0, RB_Y + 10.0, zn0, zn1) + bx(-RNP_TW / 2, RNP_TW / 2, RB_Y, LS_Y + 21.5, zn0, zn1)
    nut_sets.append(("", 0.0, LS_Y, 1, rnp, [(-26.0, RB_Y), (26.0, RB_Y)], "rear_beam", T_NPR))
    for sx, tg in ((-1, "_fl"), (1, "_fr")):
        xa, xb_ = sorted((sx * (FS_X - 25.0), sx * (FS_X + 15.0)))
        npl = bx(xa, xb_, FS_Y - 21.5, ARM_Y0, zn0, Z_FL + T_NP)
        nut_sets.append((tg, sx * FS_X, FS_Y, -1, npl, [(sx * (FS_X - 15.0), FB_Y), (sx * (FS_X + 5.4), FB_Y)], "front_beam", T_NP))
    for tg, cx, ly, sgn, shp, bolts, beam, tnp in nut_sets:
        zn1 = Z_FL + tnp
        py = ly + sgn * NUT_PIN[1]
        shp -= zc(cx, ly, zn0, zn1, NP_HOLE / 2)
        shp -= slot_z(cx, py, 90.0, NUT_FLOAT, PIN_SP_D + 1.2, zn0, zn1)
        for bxy in bolts:
            shp -= zc(*bxy, zn0, zn1, 3.25)
        sheet(d, f"nut_plate{tg}", shp, AL, body="zbody")
        for i, (x, y) in enumerate(bolts):
            add_screw(d, f"nut_plate{tg}_bolt_{i}", "M5", 16, at=(x, y, zn1), body="zbody", threads_into=beam, tnut=True,
                      clamps=(f"nut_plate{tg}",), washer=True)
        place(d, f"z_nut{tg}", leadscrew_nut_t8(), Location((cx, ly, Z_TAB - 3.5)), body="zbody")
        place(d, f"nut_pin{tg}_sleeve", spacer_round("M2.5", tnp + 0.2, "aluminium"), Location((cx, py, Z_TAB)), body="zbody")
        add_screw(d, f"nut_pin{tg}", "M2.5", 16 if tnp < 8 else 18, at=(cx, py, Z_TAB + tnp + 0.2), body="zbody", clamps=(f"nut_pin{tg}_sleeve", f"z_nut{tg}"))
        add_nut(d, f"nut_pin{tg}_nut", "M2.5", at=(cx, py, Z_TAB - 3.5), direction=(0, 0, -1), body="zbody", screw=f"nut_pin{tg}")
        d.allow_overlap(f"nut_pin{tg}", f"z_nut{tg}", max_volume=40.0)     # passes the flange's hole: the catalogue solid does not show the holes
        d.join(f"z_nut{tg}", f"nut_plate{tg}", "floating: the carrier sits on its flange; the pin in the slot stops it turning")
        lift = tnp + 0.2               # the pin's sleeve stands this far above the plate's underside: it stays in the slot up to here
        how = (f"How the bed is lifted: the T8 brass nut z_nut{tg} rides lead screw leadscrew{tg}. Its 22 mm flange is under this "
               f"{tnp:g} mm plate and its 10.2 mm barrel goes up through the plate's {NP_HOLE:.1f} mm hole. The carrier's weight rests on "
               f"the flange, so when the screw turns, the nut climbs it and lifts the plate (and the carrier and bed) with it; turned "
               f"the other way, the nut goes down and the carrier follows it under its own weight. The M2.5 pin screw nut_pin{tg} "
               f"(through a 5 mm aluminium sleeve, fixed in the flange) sits in a radial slot in the plate: it stops the nut turning "
               f"with the screw while letting it float {NUT_FLOAT:g} mm sideways, so a screw that is not exactly where the plate's hole "
               f"is does not push the carrier sideways. Nothing clamps the plate to the flange: gravity alone holds it down, which "
               f"is why the nut-seating study (every nut keeps a positive load with the screws at opposite lead limits) matters. "
               f"Pushed up: in normal running nothing pushes the bed upward (a nozzle crash pushes it down onto the flanges, and "
               f"the inductive probe does not touch it), but a hand lifting the bed, or something trapped under the carrier while Z "
               f"moves down, lifts the plate off the flange with no stop. It re-seats by itself up to about {lift:.1f} mm of lift, "
               f"while the pin's sleeve is still in its slot (the barrel stays in the hole to 10 mm); beyond that the nut can turn "
               f"and must be lined up by hand before the bed is lowered onto it.")
        d.get(f"nut_plate{tg}").meta["description"] = f"Laser-cut 6061 nut plate on the carrier. " + how
        d.get(f"z_nut{tg}").meta["description"] = f"T8 flanged brass nut, floating under nut_plate{tg}. " + how
    d.bom_extra("NYLOC-M2.5 (nut pins, in place of the hex nuts drawn)", 3, 0.05)

    # ================= bed: MIC-6 plate, PEI180 sheet, threaded-rod posts, tie ======
    bed_own = BED * (BED + BED_FX) * T_BED * MATERIALS[CAST].density * 1e-9
    d.add("bed_plate", round_profile(bed_shape_(), 2.0, T_BED), material=CAST, body="zbody", mass_kg=bed_own + PAYLOAD_KG, process="sheet",
          meta={"finish": "bare", "note": "MIC-6 9.525 mm, laser cut at SendCutSend, faces as cast; 6 holes drilled 5.2 / STI-tapped "
                                          "for M5 thread inserts by the builder"})
    mag = Stock(Pos(0, 0, T_MAG / 2) * Box(SHEET, SHEET, T_MAG), "BED-MAGNET-PEI180-BASE-STANDIN",
                "Magnetic base supplied with the TRONXY PEI180 sheet (stand-in: its thickness is not published; 1.0 mm and 3.7 g/cm3 "
                "assumed; adhesive back; the seller's 130 degC is not qualified)",
                SHEET * SHEET * T_MAG * 3.7e-6, material="rubber_gt2", cost_usd=0.0,
                ratings={"max_temp_c": 130.0, "max_temp_basis": "seller's claim for the PEI180's base, unverified"})
    place(d, "bed_magnet", mag, Location((0, BED_CY, Z_BED + T_BED)), body="zbody")
    place(d, "bed", print_sheet_pei180(), Location((0, BED_CY, Z_BED + T_BED + T_MAG)), body="zbody")
    d.join("bed_magnet", "bed_plate", "bond")
    d.join("bed", "bed_magnet", "magnet")
    place(d, "bed_heater", bed_heater_pad(200.0, 130.0, BED_W), Location((0, PAD_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed_plate", "bond")
    place(d, "bed_tco", thermal_fuse(133.0, 109.0, 15.0), Location((-45.0, BED_Y1 - 5.0, Z_BED - 2.0)), body="zbody")
    d.join("bed_tco", "bed_plate", "bond")
    # posts
    z_low = Z_FL - W5 - POST_NUT - 3.0
    rod_l = round(Z_BED + POST_INSERT - z_low, 1)
    for i, (x, y) in enumerate(BED_MOUNTS):
        sx, sy = (1 if x > 0 else -1), (1 if y > BED_CY else -1)
        arm = f"bed_arm_{'left' if x < 0 else 'right'}"
        ys = sorted((y - sy * TAB_DY[0], y - sy * TAB_DY[1]))
        ye = sorted((y + sy * 7.8, y - sy * (TAB_DY[1] + 7.5)))
        tab = bx(sx * (ARM_X - 9.0), sx * (POST_X + 8.0), ye[0], ye[1], Z_FL, Z_FL + T_TAB)
        tab -= zc(x, y, Z_FL, Z_FL + T_TAB, 3.0)
        for yb in ys:
            tab -= zc(sx * ARM_X, yb, Z_FL, Z_FL + T_TAB, clearance_hole("M5") / 2)
        sheet(d, f"bed_post_tab_{i}", tab, AL, body="zbody")
        for j, yb in enumerate(ys):
            add_screw(d, f"bed_post_tab_{i}_bolt_{j}", "M5", 10, at=(sx * ARM_X, yb, Z_FL + T_TAB), body="zbody", threads_into=arm, tnut=True,
                      clamps=(f"bed_post_tab_{i}",), washer=True)
        # drawn at the M5 stress-area diameter (4.48 mm): the stiffness a threaded rod really has, and a gap to the
        # washers' bore the FEA mesher can fill
        rod_shape = Pos(0, 0, rod_l / 2) * Cylinder(2.24, rod_l)
        rod_shape = chamfer(rod_shape.edges().filter_by(GeomType.CIRCLE), 0.5)      # threaded rod is sold with chamfered ends
        rod = Stock(rod_shape, f"ROD-M5-DIN976-A2-{rod_l:g}",
                    f"Threaded rod M5 x {rod_l:g} mm, DIN 976-1, A2-70 stainless (cut from 1 m stock; stand-in: not in the catalogue)",
                    math.pi * 2.5 ** 2 * rod_l * 8.0e-6 * 0.85, material=SS, cost_usd=0.6)
        p = f"bed_post_{i}"
        place(d, p, rod, Location((x, y, z_low)), body="zbody")
        d.join(p, "bed_plate", "screwed into a steel thread insert, jam nut")
        stack = [("top", Z_BED, (0, 0, -1), "bed_plate"), ("arm", Z_FL + T_TAB, (0, 0, 1), f"bed_post_tab_{i}"),
                 ("low", Z_FL, (0, 0, -1), f"bed_post_tab_{i}")]
        for lv, zf, dv, on in stack:
            wn, nn = f"{p}_washer_{lv}", f"{p}_nut_{lv}"
            add_washer(d, wn, "M5", (x, y, zf), dv, body="zbody")
            add_nut(d, nn, "M5", at=(x, y, zf + dv[2] * W5), direction=dv, body="zbody")
            d.join(wn, on, "clamped by the post's nut")
            d.join(nn, wn, "clamp")
            d.join(nn, p, "thread")
            d.allow_overlap(nn, p)
            d.join(wn, p, "on the rod")
        d.join("bed_plate", f"bed_post_tab_{i}", "post with jam nuts")
    d.bom_extra("INSERT-THREAD-M5x1.5D-STAINLESS (posts)", len(BED_MOUNTS), 0.8)
    # tie: bent 304 stainless (stiff in X, Y and yaw, soft vertically), bolted to the back plate, two M5 into inserts in
    # the bed plate through 8 mm spacers
    tl = bent_L(SS15, R_SS15, TIE_LEG, Y_PF - (TIE_Y - 8.0), TIE_W,
                holes_a=[(-x, TIE_ZT - TIE_BOLT_Z, clearance_hole("M5")) for x in TIE_BOLT_X],
                holes_b=[(Y_PF - TIE_Y, -x, clearance_hole("M5")) for x in TIE_X])
    tie_loc = Location(Plane(origin=(0, Y_PF, TIE_ZT), x_dir=(0, -1, 0), z_dir=(0, 0, -1)))
    d.add("bed_tie", round_profile(tie_loc * tl, 1.0, SS15), material=SS, body="zbody", process="sheet", meta={"finish": "bare"})
    for i, x in enumerate(TIE_X):
        ins = Stock(Pos(0, 0, POST_INSERT / 2) * (Cylinder(3.1, POST_INSERT) - Cylinder(2.1, POST_INSERT)),
                    "INSERT-THREAD-M5x1.5D-STAINLESS", "Wire thread insert M5 x 1.5 D, stainless (Helicoil type; stand-in: not in the catalogue)",
                    0.001, material=SS, cost_usd=0.8)
        place(d, f"bed_insert_{i}", ins, Location((x, TIE_Y, Z_BED)), body="zbody")
        d.allow_overlap(f"bed_insert_{i}", "bed_plate")
        d.join(f"bed_insert_{i}", "bed_plate", "thread insert in an STI-tapped hole")
        place(d, f"bed_tie_spacer_{i}", spacer_round("M5", TIE_SP, "aluminium"), Location((x, TIE_Y, TIE_ZT)), body="zbody")
        add_screw(d, f"bed_tie_screw_{i}", "M5", 16, at=(x, TIE_Y, TIE_ZT - SS15), direction=(0, 0, 1), body="zbody",
                  clamps=("bed_tie", f"bed_tie_spacer_{i}", "bed_plate"), threads_into=f"bed_insert_{i}", washer=True)
    for i, x in enumerate(TIE_BOLT_X):
        bolt_nut(d, f"bed_tie_bolt_{i}", "M5", 16, (x, Y_PF - SS15, TIE_BOLT_Z), (0, 1, 0), "zbody", ("bed_tie", "back_plate"),
                 nut_at=(x, Y_CAR, TIE_BOLT_Z))

    # ================= Z drive: three towers, drive plate, motor, belt ==============
    def posts_for(x0, y0, angs, r=POST_R):
        return [(x0 + r * math.cos(math.radians(a)), y0 + r * math.sin(math.radians(a))) for a in angs]
    y_slot = FY / 2 - 10.0                         # the bottom back rail's top slot
    towers = [("", 0.0, LS_Y, True, posts_for(0.0, LS_Y, (250.0, 290.0), 26.0), [(-34.0, y_slot), (34.0, y_slot)], "frame_bot_back")]
    for sx, tg in ((-1, "_fl"), (1, "_fr")):
        angs = (4.0, 40.0) if sx < 0 else (176.0, 140.0)
        towers.append((tg, sx * FS_X, FS_Y, False, posts_for(sx * FS_X, FS_Y, angs), [(sx * FS_X, FS_Y - RAIL_BOLT), (sx * FS_X, FS_Y + RAIL_BOLT)],
                       f"frame_bot_{'left' if sx < 0 else 'right'}"))
    tower_parts = {}
    # drive plate first (the rear tower's post bolts clamp it)
    mx, my = ZM_XY
    rposts = towers[0][4]
    pts = [(px + 10.0 * math.cos(a), py + 10.0 * math.sin(a)) for px, py in rposts for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    pts += [(mx + ox, my + oy) for ox in (-25.5, 25.5) for oy in (-25.5, 25.5)]
    pts += [(ZT_XY[0] + ox + 10.0 * math.cos(a), ZT_XY[1] + 10.0 * math.sin(a)) for ox in (-ZT_SLOT, ZT_SLOT)
            for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)]
    dp = Polygon(*convex_hull(pts), align=None)
    dps = Pos(0, 0, Z_DPB) * extrude(dp, T_DP)
    for px, py in rposts:
        dps -= zc(px, py, Z_DPB, Z_DPT, 3.25)
    dps -= zc(mx, my, Z_DPB, Z_DPT, 11.5)
    for ox in (-15.5, 15.5):
        for oy in (-15.5, 15.5):
            dps -= zc(mx + ox, my + oy, Z_DPB, Z_DPT, 3.3)
    dps -= slot_z(ZT_XY[0], ZT_XY[1], 0.0, ZT_SLOT, 6.5, Z_DPB, Z_DPT)
    sheet(d, "z_drive_plate", dps, AL)
    for tg, x0, y0, rear, pxy, rxy, rpart in towers:
        tower_parts[tg] = build_tower(d, tg, x0, y0, rear, pxy, rxy, rpart)
    place(d, "z_motor", nema17(MOTOR_L), Location((mx, my, Z_DPB), (0, 0, 90)))
    for i, (ox, oy) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"z_motor_screw_{i}", "M3", 10, at=(mx + ox, my + oy, Z_DPT), threads_into="z_motor", clamps=("z_drive_plate",), washer="large")
    place(d, "z_pulley_m", gt2_pulley(20, bore=5.0, belt_width=6.0), Location((mx, my, Z_DPT + 0.3)))
    d.join("z_pulley_m", "z_motor", "set_screw")
    tx, ty = ZT_XY
    sp_l = round(ZB - I_H(6.0) / 2 - Z_DPT, 2)
    place(d, "z_idler_spacer", spacer_round("M5", sp_l, "aluminium"), Location((tx, ty, Z_DPT)))
    place(d, "z_idler", gt2_idler(20, belt_width=6.0), Location((tx, ty, Z_DPT + sp_l)))
    add_screw(d, "z_idler_bolt", "M5", 30, at=(tx, ty, Z_DPB), direction=(0, 0, 1), clamps=("z_drive_plate", "z_idler_spacer"), washer="large")
    add_washer(d, "z_idler_nwasher", "M5", (tx, ty, Z_DPT + sp_l + I_H(6.0)), (0, 0, 1), screw="z_idler_bolt")
    add_nut(d, "z_idler_nut", "M5", at=(tx, ty, Z_DPT + sp_l + I_H(6.0) + W5), direction=(0, 0, 1), screw="z_idler_bolt", standard="din934")
    d.join("z_idler_nut", "z_idler", "clamped through its washer")
    d.join("z_idler", "z_idler_bolt", "axle")
    d.join("z_idler_spacer", "z_drive_plate", "clamp")
    zs = {"tags": ("", "_fl", "_fr"), "zcars": ["z_carriage_left", "z_carriage_right"],
          "rails": {"z_carriage_left": "z_rail_left", "z_carriage_right": "z_rail_right"},
          "carrier": ["back_plate", "rear_beam", "front_beam", "bed_arm_left", "bed_arm_right", "front_plate", "bed_tie",
                      "bed_tie_spacer_0", "bed_tie_spacer_1"]
                     + [f"bed_arm_{n}_{e}bracket_{s}" for n in ("left", "right") for e in ("r", "f") for s in ("i", "u")],
          "nut_plates": ["nut_plate", "nut_plate_fl", "nut_plate_fr"],
          "on_rail": lambda f: abs(f.center().Y - (Y_FACE - 8.0)) < 1e-6}
    return d, zs, bed_own, towers, tower_parts


def cover_hood(x0, x1, y0, y1, z0, z1, t=1.6, bosses=()):
    """Printed hood over live terminals: a top plate and two walls along Y (at x0 and x1), open at the two ends for the
    wires. Full-height square columns outside the walls take M3 through-bolts from below the tray, with a washer and nyloc
    nut on the column's top (outside the hood, where there is access); clearance hole 3.6 the full height (printed,
    vertical). Printed upside down (top plate on the bed): no bridges, no supports."""
    s = bx(x0, x1, y0, y1, z1 - t, z1) + bx(x0, x0 + t, y0, y1, z0, z1) + bx(x1 - t, x1, y0, y1, z0, z1)
    yb = [b[1] for b in bosses]
    if yb and min(yb) > y1:      # bosses beyond the hood's open end: carry the walls out to them
        s += bx(x0, x0 + t, y1, max(yb) + 4.0, z0, z1) + bx(x1 - t, x1, y1, max(yb) + 4.0, z0, z1)
    for bxx, byy in bosses:
        s += bx(bxx - 4.0, bxx + 4.0, byy - 4.0, byy + 4.0, z0, z1)
        s -= zc(bxx, byy, z0, z1, PH3 / 2)
    return s


def build() -> Design:
    d, zs, bed_own, towers, tower_parts = build_frame_z()
    # ================= Y axis ====================================================
    zp0, zp1 = Z_PLATE, Z_PLATE + T_YP
    X_ES_X0 = -22.7 - TX - ES_TRIG
    X_ES_Y0 = YB0 + X_ES_Y + ES_SIDE
    PC = YB0 - 1.55
    YA0, YA1 = PC + BELT_SLOTS[0] - SLOT_W / 2, PC + BELT_SLOTS[-1] + SLOT_W / 2
    for sx, n in ((-1, "left"), (1, "right")):
        yr = place(d, f"y_rail_{n}", mgn12_rail(300), Location((sx * RAIL_X, Y_RAIL_C, Z_RAIL), (0, 0, 90)))
        for i, (hx, hy, hz) in enumerate(yr.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"y_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5), threads_into=f"frame_top_{n}", tnut=True)
        place(d, f"y_carriage_{n}", mgn12h_carriage(), Location((sx * RAIL_X, YB0, Z_RAIL), (0, 0, 90)), body="ybody", guides="y")
        x_out = YB_X + BWY / 2 + 0.5 + 4.8
        x_in = YP_IN if sx > 0 else -LAND_X[1]
        plate = (bx(sx * x_in, sx * x_out, YB0 + YP_NOTCH[1], YB0 + PL_Y1, zp0, zp1)
                 + bx(sx * YP_NOTCH[0], sx * x_out, YB0 + PL_Y0, YB0 + YP_NOTCH[1], zp0, zp1))
        plate += fillet_z(sx * YP_NOTCH[0], YB0 + YP_NOTCH[1], -sx, -1, 2.0, zp0, zp1)
        for dy in BELT_SLOTS:
            plate -= slot_z(sx * YB_X, PC + dy, 0.0, (BWY + 1.0 - SLOT_W) / 2, SLOT_W, zp0, zp1)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(YH3 / 2, T_YP)
        plate += bx(sx * (YP_IN - 9.0), sx * YP_IN, YB0 + YP_NOTCH[1], YB0 + 9.5, zp0, zp1)
        for xb in BEAM_BOLT_X:
            plate -= slot_z(sx * xb, YB0, 0.0, 1.5, clearance_hole("M5"), zp0, zp1)
        if sx < 0:
            plate += bx(LAND_X[0], LAND_X[1], YB0 + PL_Y1, YB0 + LAND_Y1, zp0, zp1)
            plate += fillet_z(LAND_X[0], YB0 + PL_Y1, -1, 1, 2.0, zp0, zp1)
            for dy in (-7.5, 7.5):
                plate -= slot_z(X_ES_X0 - 4.2, X_ES_Y0 + dy, 0.0, ES_SLOT, SH3, zp0, zp1)
        sheet(d, f"y_plate_{n}", plate, AL, body="ybody")
        for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
            add_screw(d, f"y_plate_{n}_screw_{i}", "M3", 8, at=(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP), body="ybody", threads_into=f"y_carriage_{n}")
        for i, xb in enumerate(BEAM_BOLT_X):
            add_screw(d, f"beam_bolt_{n}" + ("" if i == 0 else f"_{i}"), "M5", 10, at=(sx * xb, YB0, zp1), body="ybody",
                      threads_into="x_beam", tnut=True, clamps=(f"y_plate_{n}",), washer=True)
    # ================= X axis ====================================================
    place(d, "x_beam", extrusion_2020(BEAM_L), Location((0, YB0, Z_BEAM)), body="ybody")
    rear = lambda x: Location(Plane(origin=(x, YB0 + 10.0, Z_BEAM), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    xr = place(d, "x_rail", mgn12_rail(250), rear(0.0), body="ybody")
    for i, (hx, hy, hz) in enumerate(xr.meta["interfaces"]["mount_holes_m3"][::RAIL_SCREW_STEP]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy + 3.5, hz), direction=(0, -1, 0), body="ybody", threads_into="x_beam", tnut=True)
    f0, b0, n0, b1 = STOP_X
    for sx, n in ((-1, "left"), (1, "right")):
        y0, y1 = YB0 + 10.0, YB0 + 10.0 + G32
        st = bx(sx * b0, sx * b1, y0, y1, Z_BEAM - 10.0, Z_PLATE)
        st -= bx(sx * (b0 - 1.0), sx * n0, y0, y1, Z_BEAM + 1.0, Z_PLATE + 1.0)
        st += bx(sx * f0, sx * b0, y0, y1, Z_BEAM - 10.0, Z_BEAM - 6.0)
        st -= Pos(sx * (n0 + b1) / 2, (y0 + y1) / 2, Z_BEAM) * ycyl(clearance_hole("M5") / 2, G32)
        sheet(d, f"x_rail_stop_{n}", st, AL, body="ybody", r=0.6)
        add_screw(d, f"x_rail_stop_{n}_bolt", "M5", 10, at=(sx * (n0 + b1) / 2, y1, Z_BEAM), direction=(0, -1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=(f"x_rail_stop_{n}",), washer=True)
    place(d, "x_carriage", mgn12h_carriage(), rear(0.0), body="xbody", guides="x")
    # ---- toolhead: guide block -> front plate + rear plate -> Roto
    yf, yrr = YB0 + R_TPF, YB0 + R_TPR
    ymid = yf + T_TPF                 # interface between the two tool plates
    sheet(d, "tool_plate", tool_plate_front_shape(), AL, body="xbody", r=0.8)
    sheet(d, "tool_plate_rear", tool_plate_rear_shape(), AL, body="xbody", r=0.8)
    for i, (x, z) in enumerate([(-10, -10), (10, -10), (-10, 10), (10, 10)]):
        add_screw(d, f"tool_screw_{i}", "M3", 6, at=(x, ymid, Z_BEAM + z), direction=(0, -1, 0), body="xbody",
                  threads_into="x_carriage", clamps=("tool_plate",))
    place(d, "extruder", extruder_roto(), Location(ROTO_O), body="xbody", process="purchased")
    yb_pm = yrr + ROTO_W
    for i, (hx, hy, hz) in enumerate(d.get("extruder").meta["interfaces"]["mount_holes_m3"]):
        place(d, f"probe_mount_sleeve_{i}", spacer_round("M3", PM_T, "aluminium"), Location(Plane(origin=(hx, yb_pm, hz), z_dir=(0, 1, 0))), body="xbody")
        # the nut is a PEM S-M3-1 clinched in the front plate (SendCutSend hardware service), its head in a hex hole of
        # the rear plate: the screw clamps sleeve, Roto, rear plate and front plate
        # a washer under the head bears on the sleeve's end, 0.6 mm clear of the printed holder (PM_TP)
        add_screw(d, f"extruder_screw_{i}", "M3", 50, at=(hx, yb_pm + PM_T, hz), direction=(0, -1, 0), body="xbody",
                  clamps=(f"probe_mount_sleeve_{i}", "extruder", "tool_plate_rear", "tool_plate"), washer=True)
        add_nut(d, f"extruder_nut_{i}", "M3", at=(hx, ymid, hz), direction=(0, 1, 0), body="xbody", screw=f"extruder_screw_{i}")
        d.join(f"extruder_nut_{i}", "tool_plate", "PEM self-clinching nut (SendCutSend hardware service)")
        d.join(f"probe_mount_sleeve_{i}", "probe_mount", "compression sleeve: the holder is located on it, held between the Roto's face "
               "and the screw's washer with 0.6 mm play, not clamped")
    seat = d.get("extruder").meta["interfaces"]["hotend_seat"][0]
    place(d, "hotend", hotend_revo(40, 24.0, 0.4), Location(tuple(seat), (0, 0, 190)), body="xbody")
    d.allow_overlap("hotend", "extruder")
    d.join("hotend", "extruder", "clamp")
    d.add("probe_mount", probe_mount_shape(), material=HOT, body="xbody", process="printed",
          meta={"print_up": "+Z", "print": {**PRINT_ABS, "orientation": "+Z"}, "service_temp_c": 45.0})
    place(d, "bed_probe", probe_omron_e2e(PRB_MODEL, clamp=PRB_CLAMP, nuts="separate"), Location((PRB_X, YB0 + PRB_Y, Z_PRB)), body="xbody")
    add_probe_nuts(d, "bed_probe")
    d.join("bed_probe", "probe_mount", "clamped by its two nuts")
    d.add("part_duct", part_duct_shape(), material=HOT, body="xbody", process="printed",
          meta={"print_up": "-Y", "print": {**PRINT_ABS, "orientation": "-Y"}, "service_temp_c": 45.0})
    for i, (x, z) in enumerate(FC_SCREWS):
        # through both tool plates and the duct's flange into a nyloc nut and washer captured in the flange
        add_screw(d, f"part_duct_screw_{i}", "M3", 16, at=(x, yf, Z_BEAM + z), direction=(0, 1, 0), body="xbody",
                  clamps=("tool_plate", "tool_plate_rear", "part_duct"), washer=True).meta["torque_nm"] = PRINTED_JOINT_TORQUE
        captive_nut(d, f"part_duct_screw_{i}", (x, YB0 + R_TPR + POCKET_WALL, Z_BEAM + z), (0, 1, 0), "part_duct", "xbody")
    place(d, "part_fan", fan_cg3010u24(), Location(Plane(origin=(PFAN[0], YB0 + PFAN[1], Z_BEAM + PFAN[2]), x_dir=(1, 0, 0), z_dir=(0, 1, 0))),
          body="xbody")
    for i, sxo in enumerate((-12.0, 12.0)):
        # through the fan's frame (washer on the plastic frame) and the duct's boss into a captured nyloc nut and washer
        fs = add_screw(d, f"part_fan_screw_{i}", "M3", 18, at=(PFAN[0] + sxo, YB0 + PFAN[1] + 5.0, Z_BEAM + PFAN[2] + 12.0),
                       direction=(0, -1, 0), body="xbody", clamps=("part_fan", "part_duct"), washer=True)
        # snug only: plastic fan frame on a printed boss, the nyloc holds it; at the 0.5 N.m assumed for plastic joints the
        # captured washer (on a 9 mm boss) would crush the ABS
        fs.meta["torque_nm"] = 0.2
        captive_nut(d, f"part_fan_screw_{i}", (PFAN[0] + sxo, YB0 + FC_LUG_Y + PLEN - POCKET_WALL, Z_BEAM + PFAN[2] + 12.0), (0, -1, 0),
                    "part_duct", "xbody")
    # ================= X drive ===================================================
    # belt bracket: 5052 2.286 mm bent L on the front tool plate (two M3 into captive nuts in the rear plate); the two belt
    # ends are squeezed between its horizontal leg and a 2.54 mm clamp plate by four M3 with nuts
    t_b = B23
    z_leg = Z_XL + 0.7                                  # underside of the bracket's horizontal leg = top of the belt
    l_b = R_TPF + 8.0
    brk = bent_L(t_b, R_B23, 12.6, l_b, 30.0,
                 holes_a=[(-x, (z_leg + t_b) - (Z_BEAM + BRK_Z), clearance_hole("M3")) for x, _ in BLK_SCREWS],
                 holes_b=[(R_TPF - yy, -xx, clearance_hole("M3")) for xx in (-10.0, 10.0) for yy in CLAMP_Y])
    brk_loc = Location(Plane(origin=(0, yf, z_leg + t_b), x_dir=(0, -1, 0), z_dir=(0, 0, -1)))
    d.add("x_belt_bracket", round_profile(brk_loc * brk, 0.8, B23), material=AL_BEND, body="xbody", process="sheet", meta={"finish": "bare"})
    cp = bx(-15.0, 15.0, YB0 - 6.5, YB0 + 16.0, Z_XL - 0.7 - G20, Z_XL - 0.7)
    for xx in (-10.0, 10.0):
        for yy in CLAMP_Y:
            cp -= zc(xx, YB0 + yy, Z_XL - 0.7 - G20, Z_XL - 0.7, clearance_hole("M3") / 2)
    sheet(d, "x_belt_clamp", cp, AL, body="xbody")
    for i, (x, z) in enumerate(BLK_SCREWS):
        add_screw(d, f"x_belt_bracket_screw_{i}", "M3", 10, at=(x, yf - t_b, Z_BEAM + BRK_Z), direction=(0, 1, 0), body="xbody",
                  clamps=("x_belt_bracket", "tool_plate"), washer=True)
        add_nut(d, f"x_belt_bracket_nut_{i}", "M3", at=(x, ymid, Z_BEAM + BRK_Z), direction=(0, 1, 0), body="xbody", screw=f"x_belt_bracket_screw_{i}")
        d.join(f"x_belt_bracket_nut_{i}", "tool_plate_rear", "captive in a hex pocket")
    k = 0
    for xx in (-10.0, 10.0):
        for yy in CLAMP_Y:
            bolt_nut(d, f"x_belt_clamp_screw_{k}", "M3", 10, (xx, YB0 + yy, z_leg + t_b), (0, 0, -1), "xbody", ("x_belt_bracket", "x_belt_clamp"),
                     nut_at=(xx, YB0 + yy, Z_XL - 0.7 - G20)); k += 1
    d.join("x_belt_clamp", "x_belt_bracket", "the belt ends between them")
    # motor on a flat 3.175 mm 6061 plate, idler on a bent 5052 plate with a forward lug; tension: an M3 jack screw in a
    # PEM nut of a bent 5052 anchor pushes the lug (both plates slide on their T-nuts while the bolts are slack)
    yb_f, yb_r = YB0 - 10.0 - MT, YB0 - 10.0
    fwd = lambda x, y, z: Location(Plane(origin=(x, y, z), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    mm = bx(XM_X - 25.0, XM_X + 25.0, yb_f, yb_r, Z_BEAM - 8.0, XD_Z + 23.0)
    mm -= Pos(XM_X, (yb_f + yb_r) / 2, XD_Z) * ycyl(11.5, MT)
    for x in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            mm -= Pos(XM_X + x, (yb_f + yb_r) / 2, XD_Z + z) * ycyl(SH3 / 2, MT)
    X_MOUNT_BOLTS = (-15.0, 15.0)
    for x in X_MOUNT_BOLTS:
        mm -= Pos(XM_X + x, (yb_f + yb_r) / 2, Z_BEAM) * ycyl(clearance_hole("M5") / 2, MT)
    sheet(d, "x_motor_mount", mm, AL, body="ybody")
    place(d, "x_motor", nema17(34), fwd(XM_X, yb_f, XD_Z), body="ybody")
    place(d, "x_pulley", gt2_pulley(20, belt_width=BWX), fwd(XM_X, yb_r + X_PG, XD_Z), body="ybody")
    k = 0
    for x in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"x_motor_screw_{k}", "M3", 8, at=(XM_X + x, yb_r, XD_Z + z), direction=(0, -1, 0), body="ybody",
                      threads_into="x_motor", clamps=("x_motor_mount",), washer=True); k += 1
    for i, x in enumerate(X_MOUNT_BOLTS):
        add_screw(d, f"x_motor_mount_bolt_{i}", "M5", 10, at=(XM_X + x, yb_f, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_motor_mount",), washer=True)
    d.join("x_pulley", "x_motor", "set_screw")
    zc_im = (Z_BEAM - 8.0 + XD_Z + 12.0) / 2
    w_im = XD_Z + 12.0 - (Z_BEAM - 8.0)
    XIM_BOLTS = (XI_X - 8.0, XI_X + 15.0)
    LUG = 22.0
    JACK_Z, JACK_Y = Z_BEAM + 12.0, yb_r - 15.0
    im = bent_L(MT, R_B32, LUG, 50.0, w_im,
                holes_b=[(25.0, XD_Z - zc_im, clearance_hole("M5"))] + [(xb - (XI_X - 25.0), Z_BEAM - zc_im, clearance_hole("M5")) for xb in XIM_BOLTS])
    im_loc = Location(Plane(origin=(XI_X - 25.0, yb_r, zc_im), x_dir=(1, 0, 0), z_dir=(0, -1, 0)))
    d.add("x_idler_mount", round_profile(im_loc * im, 1.0, MT), material=AL_BEND, body="ybody", process="sheet", meta={"finish": "bare"})
    for i, x in enumerate(XIM_BOLTS):
        add_screw(d, f"x_idler_mount_bolt_{i}", "M5", 10, at=(x, yb_f, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_idler_mount",), washer=True)
    place(d, "x_idler_spacer", spacer_round("M5", X_SP, "aluminium"), fwd(XI_X, yb_r, XD_Z), body="ybody")
    place(d, "x_idler", gt2_idler(20, belt_width=BWX), fwd(XI_X, yb_r + X_SP, XD_Z), body="ybody")
    add_screw(d, "x_idler_bolt", "M5", 35, at=(XI_X, yb_f, XD_Z), direction=(0, 1, 0), body="ybody",
              clamps=("x_idler_mount", "x_idler_spacer"), washer=True)
    add_nut(d, "x_idler_nut", "M5", at=(XI_X, yb_r + X_SP + I_H(BWX), XD_Z), direction=(0, 1, 0), body="ybody", screw="x_idler_bolt")
    d.join("x_idler", "x_idler_bolt", "axle")
    d.join("x_idler_spacer", "x_idler_mount", "clamp")
    XA_FIN = XI_X - 25.0 - 8.0                          # anchor fin's outboard face
    zc_xa = Z_BEAM + 6.0
    xa = bent_L(MT, R_B32, LUG, 34.0, 30.0, holes_a=[(zc_xa - JACK_Z, yb_r - JACK_Y, 4.27)],
                holes_b=[(16.0, zc_xa - Z_BEAM, clearance_hole("M5")), (28.0, zc_xa - Z_BEAM, clearance_hole("M5"))])
    xa_loc = Location(Plane(origin=(XA_FIN, yb_r, zc_xa), x_dir=(-1, 0, 0), z_dir=(0, -1, 0)))
    d.add("x_tension_anchor", round_profile(xa_loc * xa, 1.0, MT), material=AL_BEND, body="ybody", process="sheet", meta={"finish": "bare"})
    for i, lx in enumerate((16.0, 28.0)):
        add_screw(d, f"x_tension_anchor_bolt_{i}", "M5", 10, at=(XA_FIN - lx, yb_f, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_tension_anchor",), washer=True)
    add_nut(d, "x_tension_nut", "M3", at=(XA_FIN, JACK_Y, JACK_Z), direction=(1, 0, 0), body="ybody")
    d.join("x_tension_nut", "x_tension_anchor", "PEM self-clinching nut (SendCutSend hardware service)")
    add_screw(d, "x_tension_screw", "M3", 16, at=(XI_X - 25.0 - 16.0, JACK_Y, JACK_Z), direction=(1, 0, 0), body="ybody",
              threads_into="x_tension_nut")
    d.get("x_tension_screw").meta["torque_nm"] = 0.3
    d.join("x_tension_screw", "x_idler_mount", "jack screw bears on the lug")
    d.bom_extra("PEM-S-M3-1 (x and y tension anchors, Roto screws in the front tool plate; installed by SendCutSend)", 5, 0.4)
    # X endstop: hangs under the left Y plate's land (slots + large washers)
    xsw = place(d, "x_endstop", endstop_switch(),
                Location(Plane(origin=(X_ES_X0, X_ES_Y0, zp0 - ES_SP), x_dir=(0, 1, 0), z_dir=(0, 0, -1))), body="ybody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"x_endstop_spacer_{i}", spacer_round("M3", ES_SP), Location((hx, hy, zp0 - ES_SP)), body="ybody")
        add_screw(d, f"x_endstop_screw_{i}", "M3", 16, at=(hx, hy, zp1), body="ybody",
                  clamps=("y_plate_left", f"x_endstop_spacer_{i}", "x_endstop"), washer="large")
        add_nut(d, f"x_endstop_nut_{i}", "M3", at=(hx, hy, zp0 - ES_SP - 1.6), direction=(0, 0, -1), body="ybody", screw=f"x_endstop_screw_{i}")
    # ================= Y drives ===================================================
    xf = FX / 2
    YMB = (142.0, 168.0)
    side = lambda x, y, z, sg: Location(Plane(origin=(x, y, z), x_dir=(0, 1, 0), z_dir=(sg, 0, 0)))
    for sg, tag, n in ((1, "", "right"), (-1, "_l", "left")):
        rail = f"frame_top_{n}"
        # motor mount: 5052 3.175 mm, bent fin at its front edge (pushed by the jack screw)
        mmb = bent_L(MT_Y, R_SS19, LUG, 55.0, 20.0)
        mml = Location(Plane(origin=(sg * xf, 125.0, FZ), x_dir=(0, 1, 0), z_dir=(sg, 0, 0)))
        xa_, xb_ = sorted((sg * xf, sg * (xf + MT_Y)))
        arm = bx(xa_, xb_, 170.0, YM_Y + 21.0, FZ - 10.0, Z_YC + 23.0)
        arm += fillet_x(170.0, FZ + 10, -1, 1, 3.0, xa_, xb_)
        m = mml * mmb + arm
        xm = (xa_ + xb_) / 2
        m -= Pos(xm, YM_Y, Z_YC) * xcyl(11.5, MT_Y)
        for y in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                m -= Pos(xm, YM_Y + y, Z_YC + z) * xcyl(SH3 / 2, MT_Y)
        for y in YMB:
            m -= Pos(xm, y, FZ) * xcyl(clearance_hole("M5") / 2, MT_Y)
        d.add(f"y_motor_mount{tag}", round_profile(m, 1.0, MT_Y), material=SS, process="sheet", meta={"finish": "bare"})
        place(d, f"y_motor{tag}", nema17(48), Location(Plane(origin=(sg * xf, YM_Y, Z_YC), x_dir=(0, 0, -1), z_dir=(sg, 0, 0))))
        place(d, f"y_pulley{tag}", gt2_pulley(20, belt_width=BWY),
              Location(Plane(origin=(sg * (YB_X + P_BC(BWY)), YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(-sg, 0, 0))))
        k = 0
        for y in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                add_screw(d, f"y_motor{tag}_screw_{k}", "M3", 6, at=(sg * (xf + MT_Y), YM_Y + y, Z_YC + z), direction=(-sg, 0, 0),
                          threads_into=f"y_motor{tag}", clamps=(f"y_motor_mount{tag}",), washer=True); k += 1
        for i, y in enumerate(YMB):
            add_screw(d, f"y_motor_mount{tag}_bolt_{i}", "M5", 10, at=(sg * (xf + MT_Y), y, FZ), direction=(-sg, 0, 0),
                      threads_into=rail, tnut=True, clamps=(f"y_motor_mount{tag}",), washer=True)
        d.join(f"y_pulley{tag}", f"y_motor{tag}", "set_screw")
        # tension anchor: 5052 3.175 mm bent L on the rail's outer face (two T-nuts), PEM nut in its fin
        ya = bent_L(B32, R_B32, LUG, 34.0, 20.0, holes_a=[(0.0, 15.0, 4.27)],
                    holes_b=[(16.0, 0.0, clearance_hole("M5")), (28.0, 0.0, clearance_hole("M5"))])
        yal = Location(Plane(origin=(sg * xf, 117.0, FZ), x_dir=(0, -1, 0), z_dir=(sg, 0, 0)))
        d.add(f"y_tension_anchor{tag}", round_profile(yal * ya, 1.0, B32), material=AL_BEND, process="sheet", meta={"finish": "bare"})
        for i, ly in enumerate((16.0, 28.0)):
            add_screw(d, f"y_tension_anchor{tag}_bolt_{i}", "M5", 10, at=(sg * (xf + B32), 117.0 - ly, FZ), direction=(-sg, 0, 0),
                      threads_into=rail, tnut=True, clamps=(f"y_tension_anchor{tag}",), washer=True)
        add_nut(d, f"y_tension_nut{tag}", "M3", at=(sg * (xf + 15.0), 117.0, FZ), direction=(0, 1, 0))
        d.join(f"y_tension_nut{tag}", f"y_tension_anchor{tag}", "PEM self-clinching nut (SendCutSend hardware service)")
        add_screw(d, f"y_tension_screw{tag}", "M3", 16, at=(sg * (xf + 15.0), 109.0, FZ), direction=(0, 1, 0), threads_into=f"y_tension_nut{tag}")
        d.get(f"y_tension_screw{tag}").meta["torque_nm"] = 0.3      # a jack screw is turned by hand, not torqued
        d.join(f"y_tension_screw{tag}", f"y_motor_mount{tag}", "jack screw bears on the fin")
        # idler mount (6061 3.175 L), the idler on an M5 with a real washer between it and the mount
        xa_, xb_ = sorted((sg * xf, sg * (xf + MT_YI)))
        xm = (xa_ + xb_) / 2
        y_l1 = YI_Y + 7.5
        imy = bx(xa_, xb_, YI_Y - 9.0, y_l1, FZ - 10.0, Z_YC + 9.0) + bx(xa_, xb_, y_l1, YIM_BOLTS[1] + 10.0, FZ - 10.0, FZ + 8.0)
        imy += fillet_x(y_l1, FZ + 8.0, 1, 1, 2.0, xa_, xb_)
        imy -= Pos(xm, YI_Y, Z_YC) * xcyl(clearance_hole("M5") / 2, MT_YI)
        for y in YIM_BOLTS:
            imy -= Pos(xm, y, FZ) * xcyl(clearance_hole("M5") / 2, MT_YI)
        sheet(d, f"y_idler_mount{tag}", imy, SS)
        for i, y in enumerate(YIM_BOLTS):
            add_screw(d, f"y_idler_mount{tag}_bolt_{i}", "M5", 10, at=(sg * (xf + MT_YI), y, FZ), direction=(-sg, 0, 0),
                      threads_into=rail, tnut=True, clamps=(f"y_idler_mount{tag}",), washer=True)
        place(d, f"y_idler{tag}", gt2_idler(20, belt_width=BWY), side(sg * (YB_X - I_H(BWY) / 2), YI_Y, Z_YC, sg))
        add_screw(d, f"y_idler{tag}_bolt", "M5", 30, at=(sg * (YB_X + I_H(BWY) / 2), YI_Y, Z_YC), direction=(-sg, 0, 0),
                  clamps=(f"y_idler_mount{tag}",))
        add_washer(d, f"y_idler{tag}_spacer", "M5", (sg * (xf + MT_YI), YI_Y, Z_YC), (sg, 0, 0), screw=f"y_idler{tag}_bolt")
        add_washer(d, f"y_idler{tag}_nwasher", "M5", (sg * xf, YI_Y, Z_YC), (-sg, 0, 0), screw=f"y_idler{tag}_bolt")
        add_nut(d, f"y_idler{tag}_nut", "M5", at=(sg * (xf - W5), YI_Y, Z_YC), direction=(-sg, 0, 0), screw=f"y_idler{tag}_bolt")
        d.join(f"y_idler{tag}_nut", f"y_idler_mount{tag}", "clamped through its washer")
        d.join(f"y_idler{tag}", f"y_idler{tag}_bolt", "axle")
    # Y endstop at the rear on the right rail's inner face, on a sliding sheet mount
    xi_f = xf - 20.0
    y_strike = YB0 + PL_Y1 + TY
    ysw = place(d, "y_endstop", endstop_switch(),
                Location(Plane(origin=(xi_f + ES_SP, y_strike + ES_TRIG, Z_PLATE + 2.0 + ES_SIDE), x_dir=(0, 0, 1), z_dir=(1, 0, 0))))
    ys_holes = ysw.meta["interfaces"]["mount_holes_m3"]
    yh = ys_holes[0][1]
    MTE = G32
    ym = bx(xi_f - MTE, xi_f, YEM_BOLTS[0] - 6.5, max(yh + 6.0, YEM_BOLTS[1] + 6.5), FZ - 8.0, FZ + 8.0)
    ym += bx(xi_f - MTE, xi_f, yh - 5.4, yh + 6.0, FZ + 8.0, max(h[2] for h in ys_holes) + 5.0)
    for y in YEM_BOLTS:
        ym -= Pos(xi_f - MTE / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MTE)
    for hx, hy, hz in ys_holes:
        ym -= Pos(xi_f - MTE / 2, hy, hz) * xcyl(SH3 / 2, MTE)
    sheet(d, "y_endstop_mount", ym, AL)
    for i, y in enumerate(YEM_BOLTS):
        add_screw(d, f"y_endstop_mount_bolt_{i}", "M5", 10, at=(xi_f - MTE, y, FZ), direction=(1, 0, 0), threads_into="frame_top_right", tnut=True,
                  clamps=("y_endstop_mount",), washer=True)
    for i, (hx, hy, hz) in enumerate(ys_holes):
        place(d, f"y_endstop_spacer_{i}", spacer_round("M3", ES_SP), Location(Plane(origin=(xi_f, hy, hz), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
        add_screw(d, f"y_endstop_screw_{i}", "M3", 12, at=(xi_f - MTE, hy, hz), direction=(1, 0, 0),
                  clamps=("y_endstop_mount", f"y_endstop_spacer_{i}", "y_endstop"), washer=True)
        add_nut(d, f"y_endstop_nut_{i}", "M3", at=(hx + 1.6, hy, hz), direction=(1, 0, 0), screw=f"y_endstop_screw_{i}")
    return finish_build(d, zs, bed_own, towers, tower_parts)


def finish_build(d, zs, bed_own, towers, tower_parts) -> Design:
    # ================= electronics bay: tray across the bottom rails =============
    tray = Pos(0, (TRAY_Y0 + TRAY_Y1) / 2, 20 + T_TRAY / 2) * Box(FX, TRAY_Y1 - TRAY_Y0, T_TRAY)
    grp = ["electronics_tray"]
    psu = place(d, "psu", psu_lrs(PSU_MODEL), Location((-28.0, -30.0, Z_TRAY), (0, 0, -90)))
    board = place(d, "control_board", skr_mini_e3_v3(), Location((85.0, -82.0, Z_TRAY + 6.0), (0, 0, -90)))
    host = place(d, "host", raspberry_pi_zero2w(), Location((85.0, 22.0, Z_TRAY + 4.0), (0, 0, 90)))
    pcbs = [(board, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2, 4)), (host, "mount_holes_m2.5", "M2.5", 12, 4.0, (0, 3))]
    tray_hole = {"M3": clearance_hole("M3"), "M2.5": 3.2}
    RELAY_XY = (-115.0, -36.0)
    relay = place(d, "psu_relay", relay_btt_v12(), Location((*RELAY_XY, Z_TRAY + 6.0), (0, 0, 90)))
    pcbs.append((relay, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2)))
    tray_bolts = [(sx * RAIL_X, y) for sx in (-1, 1) for y in (-58.0, 72.0)]
    for tg, x0, y0, rear, pxy, rxy, rpart in towers:
        if rear:
            continue
        for x, y in pxy:
            tray -= zc(x, y, 20.0, Z_TRAY, 4.0)           # room for the post bolts' tips
        for x, y in rxy:
            tray -= zc(x, y, 20.0, Z_TRAY, clearance_hole("M5") / 2)
    for x, y in tray_bolts:
        tray -= zc(x, y, 20.0, Z_TRAY, clearance_hole("M5") / 2)
    for hx, hy, hz in psu.meta["interfaces"]["mount_holes_m4"]:
        tray -= zc(hx, hy, 20.0, Z_TRAY, clearance_hole("M4") / 2)
    for comp, key, size, _, _, use in pcbs:
        for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][key]):
            if use is not None and i not in use:
                continue
            tray -= zc(hx, hy, 20.0, Z_TRAY, tray_hole[size] / 2)
    # mains covers (printed PETG hoods over the live terminals): M3 through-bolts from below the tray, nyloc nut and washer on
    # each column's top
    rx, ry = RELAY_XY
    covers = [("mains_cover_relay", (rx - 21.0, rx + 21.0, ry + 18.0, ry + 43.0, Z_TRAY, Z_TRAY + 6.0 + 19.6 + 3.8),
               [(rx - 17.0, ry + 47.0), (rx + 17.0, ry + 47.0)]),
              ("mains_cover_psu", (-89.5, 33.5, 60.0, 77.0, Z_TRAY, ZB - 3.0 - 2.8), [(-93.5, 64.0), (37.5, 64.0)])]
    for nm, (x0, x1, y0, y1, z0, z1), bosses in covers:
        d.add(nm, cover_hood(x0, x1, y0, y1, z0, z1, bosses=bosses), material=COOL, process="printed",
              meta={"print_up": "-Z", "print": {**PRINT_ABS, "orientation": "-Z", "infill": 0.3}})
        grp.append(nm)
        for i, (bxx, byy) in enumerate(bosses):
            tray -= zc(bxx, byy, 20.0, Z_TRAY, 3.6 / 2)
            grp += through_bolt_nyloc(d, f"{nm}_screw_{i}", bolt_length(z1 - 20.0), (bxx, byy, 20.0), (0, 0, 1),
                                      ("electronics_tray", nm), (bxx, byy, z1))
    sheet(d, "electronics_tray", tray, AL, r=3.0)
    for i, (x, y) in enumerate(tray_bolts):
        add_screw(d, f"tray_bolt_{i}", "M5", 10, at=(x, y, Z_TRAY), threads_into=f"frame_bot_{'left' if x < 0 else 'right'}",
                  tnut=True, washer=True)
    for i, (hx, hy, hz) in enumerate(psu.meta["interfaces"]["mount_holes_m4"]):
        add_screw(d, f"psu_screw_{i}", "M4", 6, at=(hx, hy, 20.0), direction=(0, 0, 1), threads_into="psu")
        grp.append(f"psu_screw_{i}")
    grp.append("psu")
    for comp, key, size, slen, sp, use in pcbs:
        mount_pcb(d, comp.name, comp, key, size, slen, sp, grp, use)
    d.subassemblies["electronics"] = grp
    # mains inlet on a 2.54 mm panel (the DD11's own 2.75 mm web between cut-out and screw holes meets a one-thickness
    # web only at 2.5 mm or thinner), its rear covered by a printed hood screwed through the panel
    T_IP = G25
    IN_Y, IN_Z, XP = 22.0, 60.0, -FX / 2
    panel = Pos(XP - T_IP / 2, IN_Y, 49.0) * Box(T_IP, 80.0, 94.0)
    inlet = place(d, "inlet", iec_inlet_c14(FUSE_A), Location(Plane(origin=(XP - T_IP, IN_Y, IN_Z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    cut_x, cut_y = inlet.meta["interfaces"]["cutout"]
    panel -= Pos(XP - T_IP / 2, IN_Y, IN_Z) * Rot(0, 90, 0) * extrude(
        RectangleRounded(cut_y, cut_x, inlet.meta["interfaces"]["cutout_corner_radius"]), T_IP / 2, both=True)
    for hx, hy, hz in inlet.meta["interfaces"]["mount_holes_m3"]:
        panel -= Pos(XP - T_IP / 2, hy, hz) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, T_IP)
    PANEL_BOLTS = (IN_Y - 30.0, IN_Y + 30.0)
    for y in PANEL_BOLTS:
        panel -= Pos(XP - T_IP / 2, y, 10.0) * Rot(0, 90, 0) * Cylinder(clearance_hole("M5") / 2, T_IP)
    HOOD_SCREWS = [(IN_Y - 23.0, IN_Z + 20.0), (IN_Y + 23.0, IN_Z + 20.0)]
    for y, z in HOOD_SCREWS:
        panel -= Pos(XP - T_IP / 2, y, z) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, T_IP)
    sheet(d, "inlet_panel", panel, AL, r=2.0)
    for i, y in enumerate(PANEL_BOLTS):
        add_screw(d, f"inlet_panel_bolt_{i}", "M5", 10, at=(XP - T_IP, y, 10.0), direction=(1, 0, 0), threads_into="frame_bot_left", tnut=True,
                  clamps=("inlet_panel",), washer=True)
    for i, (hx, hy, hz) in enumerate(inlet.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"inlet_screw_{i}", "M3", 10, at=(XP - T_IP - 2.5, hy, hz), direction=(1, 0, 0), clamps=("inlet", "inlet_panel"))
        add_washer(d, f"inlet_washer_{i}", "M3", (XP, hy, hz), (1, 0, 0), screw=f"inlet_screw_{i}")
        add_nut(d, f"inlet_nut_{i}", "M3", at=(XP + 0.5, hy, hz), direction=(1, 0, 0), screw=f"inlet_screw_{i}")
        d.join(f"inlet_nut_{i}", "inlet_panel", "clamped through its washer")
    # the inlet is 30.5 wide (y) and 65 tall (z) behind the panel; the hood: top, two sides, an inner end wall open below
    hood = bx(XP, XP + 32.0, IN_Y - 19.0, IN_Y + 19.0, IN_Z + 34.0, IN_Z + 36.0)
    for sy_ in (-1, 1):
        hood += bx(XP, XP + 32.0, IN_Y + sy_ * 18.0 - 1.0, IN_Y + sy_ * 18.0 + 1.0, IN_Z - 34.0, IN_Z + 36.0)
    hood += bx(XP + 30.0, XP + 32.0, IN_Y - 19.0, IN_Y + 19.0, IN_Z + 16.0, IN_Z + 36.0)     # inner end: above the terminals' plugs
    for y, z in HOOD_SCREWS:
        yw = IN_Y + (18.0 if y > IN_Y else -18.0)
        hood += bx(XP, XP + 9.0, min(yw, y - 4.0), max(yw, y + 4.0), z - 4.0, z + 4.0)
        hood -= Pos(XP + 4.5, y, z) * xcyl(PH3 / 2, 9.0)              # printed clearance, vertical in the print (-X up)
    d.add("mains_cover_inlet", hood, material=COOL, process="printed",
          meta={"print_up": "-X", "print": {**PRINT_ABS, "orientation": "-X", "infill": 0.3}})
    for i, (y, z) in enumerate(HOOD_SCREWS):
        # owner review: a through-bolt, head and washer outside the panel, washer and nyloc nut on the boss's inner face
        through_bolt_nyloc(d, f"mains_cover_inlet_screw_{i}", bolt_length(T_IP + 9.0), (XP - T_IP, y, z), (1, 0, 0),
                           ("inlet_panel", "mains_cover_inlet"), (XP + 9.0, y, z))
    add_screw(d, "earth_stud", "M5", 10, at=(XP - 2.0, 80.0, 10.0), direction=(1, 0, 0), threads_into="frame_bot_left", tnut=True)
    d.bom_extra("WASHER-M5-SERRATED (earth stud)", 1, 0.05)
    # ================= bench sub-assemblies =======================================
    have = {c.name for c in d.components}
    for tg, x0, y0, rear, pxy, rxy, rpart in towers:
        parts = [n for n in tower_parts[tg] if "rail_bolt" not in n]
        if rear:
            parts += ["z_drive_plate", "z_motor", "z_pulley_m", "z_idler_spacer", "z_idler", "z_idler_bolt", "z_idler_bolt_washer",
                      "z_idler_nwasher", "z_idler_nut"] + [f"z_motor_screw_{i}{s}" for i in range(4) for s in ("", "_washer")]
        d.subassemblies[f"z_tower{tg or '_rear'}"] = [n for n in parts if n in have]
    d.subassemblies["x_drive"] = ["x_motor_mount", "x_motor", "x_pulley"] + [f"x_motor_screw_{i}{s}" for i in range(4) for s in ("", "_washer")]
    d.subassemblies["x_idler_unit"] = ["x_idler_mount", "x_idler_spacer", "x_idler", "x_idler_bolt", "x_idler_bolt_washer", "x_idler_nut"]
    d.subassemblies["part_cooling"] = ["part_duct", "part_fan"] + [f"part_fan_screw_{i}{s}" for i in range(2)
                                                                   for s in ("", "_washer", "_nwasher", "_nut")]
    for tag in ("", "_l"):
        d.subassemblies[f"y_drive{tag}"] = ([f"y_motor_mount{tag}", f"y_motor{tag}", f"y_pulley{tag}"]
                                            + [f"y_motor{tag}_screw_{i}{s}" for i in range(4) for s in ("", "_washer")])
    # ================= belts =====================================================
    PC = YB0 - 1.55
    YA0, YA1 = PC + BELT_SLOTS[0] - SLOT_W / 2, PC + BELT_SLOTS[-1] + SLOT_W / 2
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (-14.0, XB_Y, Z_XL)), ("pulley", "x_pulley", "ccw"),
                                   ("pulley", "x_idler", "ccw"), ("anchor", "xbody", (14.0, XB_Y, Z_XL))],
                        axis=(0, 1, 0), width=BWX, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, YA0, Z_YA)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt_l", [("anchor", "ybody", (-YB_X, YA0, Z_YA)), ("pulley", "y_idler_l", "ccw"),
                                     ("pulley", "y_pulley_l", "ccw"), ("anchor", "ybody", (-YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    zpath = [("pulley", "z_pulley_fl", "ccw"), ("pulley", "z_pulley_fr", "ccw"), ("pulley", "z_idler", "cw"),
             ("pulley", "z_pulley_m", "ccw"), ("pulley", "z_pulley", "ccw")]
    d.belts.append(Belt("z_belt", zpath, axis=(0, 0, 1), width=6.0, stock_length=Z_BELT_L, adjust=ZT_SLOT))
    d.bom_extra(f"GT2-BELT-6MM-CLOSED-{Z_BELT_L:g}", 1, 6.0)
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 1, 4.0)
    d.bom_extra("GT2-BELT-12MM-OPEN-1M", 2, 5.0)
    d.bom_extra("THREADLOCKER-MEDIUM (Loctite 243 class: Z top nuts, pulley set screws, jack screws, post jam nuts)", 1, 6.0)
    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY_F, TY), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_DN, PRINT_Z), overtravel=(0.0, Z_UP),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": [f"leadscrew{t}" for t in zs["tags"]],
                                 "nut": [f"z_nut{t}" for t in zs["tags"]], "sync": "belt", "nut_seating": "gravity"}))
    d.program = [{"to": {"z": PRINT_Z}},
                 {"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": -75, "y": 75}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 0, "y": 0}},
                 {"to": {"z": 0.0}}]
    nozzle = (0.0, YB0 + HOT_OFF, Z_NOZZLE)
    d.tool_point = ("xbody", nozzle)
    d.endstops += [{"joint": "x", "switch": "x_endstop", "at": "min"},
                   {"joint": "y", "switch": "y_endstop", "at": "max"},
                   {"joint": "z", "probe": "bed_probe", "at": "max"}]
    build_electrical(d)
    d.adjustments += [
        Adjustment("probe z_offset in the firmware", "z_offset", range_mm=Z_UP),
        Adjustment("the two nuts at the tab of each of the four bed posts (set once at assembly)", "bed_level", range_mm=4.0),
        Adjustment("x switch: its screws run in slots in the Y plate's land", "endstop", range_mm=ES_SLOT, joint="x"),
        Adjustment("y switch: its mount slides along the rail on two T-nuts", "endstop", range_mm=5.0, joint="y"),
        Adjustment("z belt: tensioner idler bolt in a slot", "belt_tension", range_mm=ZT_SLOT, joint="z"),
        Adjustment("y rails on sliding T-nuts", "rail_align", range_mm=1.6, joint="y",
                   note="an M3 in the 6.2 mm slot slides +/-1.6 mm: left rail to a straight edge, right rail tightened while the gantry runs"),
        Adjustment("z rails on sliding T-nuts", "rail_align", range_mm=1.6, joint="z",
                   note="left rail to a square, right rail tightened while the carrier is run up and down"),
        Adjustment("floating lead screw nut", "float", range_mm=NUT_FLOAT - 0.2, joint="z"),
        Adjustment("x belt: idler plate slides on its T-nuts, pushed by an M3 jack screw in a PEM nut", "belt_tension", range_mm=BELT_ADJ, joint="x"),
        Adjustment("y belts: motor mounts slide on their T-nuts, pushed by M3 jack screws in PEM nuts", "belt_tension", range_mm=BELT_ADJ, joint="y"),
    ]
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"},
                 "print_area": (PRINT_X, PRINT_Y)}
    # ================= structure =================================================
    moving = ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate", "tool_plate_rear", "extruder", "hotend"]
    y_plate_fix = [("y_plate_left", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6),
                   ("y_plate_right", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6)]
    z_blk = d.get("hotend").meta["interfaces"]["heater_block_box"][0][2]
    block_face = ("hotend", lambda f: abs(f.center().Z - z_blk) < 1e-3)
    for nm, force in (("nozzle_stiffness_y", (0.0, 3.0, -2.0)), ("nozzle_stiffness_x", (3.0, 0.0, -2.0))):
        d.assemblycases.append(AssemblyCase(nm, moving, fixed=y_plate_fix, loaded=block_face, force=force,
                                            probe=nozzle, max_deflection=0.03, min_fos=5.0))
    w_bed = 3.0 * (PAYLOAD_KG + bed_own) * 9.81
    posts = [f"bed_post_{i}{sfx}" for i in range(len(BED_MOUNTS))
             for sfx in ("", "_nut_top", "_nut_arm", "_nut_low", "_washer_top", "_washer_arm", "_washer_low")] \
        + [f"bed_post_tab_{i}" for i in range(len(BED_MOUNTS))]
    zcars, on_rail, carrier, nplates = zs["zcars"], zs["on_rail"], zs["carrier"], zs["nut_plates"]
    bed_stack = ["bed_plate", "bed_magnet", "bed"]
    d.printer["bed_support"] = {"parts": [*bed_stack, *posts, *carrier, *zcars, *nplates]}
    on_nut = lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 100
    d.assemblycases.append(AssemblyCase(
        "payload_x3_on_bed", [*bed_stack, *posts, *carrier, *zcars, *nplates],
        fixed=[(c, on_rail) for c in zcars] + [(nb, on_nut) for nb in nplates],
        loaded=("bed", lambda f: abs(f.center().Z - (Z_SURF)) < 0.05 and f.area > 1000),
        force=(0.0, 0.0, -w_bed), probe=(PRINT_X / 2, BED_CY - PRINT_Y / 2, Z_SURF), max_deflection=0.3, min_fos=3.0))
    # metal parts in the Z load path (no printed part carries load any more)
    def hole_at(x, y, r):
        # a cylindrical face (a whole hole wall or a piece of one) whose sampled points all lie r from the axis (x, y)
        def sel(f):
            if f.geom_type.name != "CYLINDER":
                return False
            pts = [f.position_at(u, v) for u in (0.1, 0.5, 0.9) for v in (0.2, 0.8)]
            return all(abs(math.hypot(p.X - x, p.Y - y) - r) < 0.05 for p in pts)
        return sel
    rb = [(-26.0, RB_Y), (26.0, RB_Y)]
    d.loadcases.append(LoadCase("nut_thrust", "nut_plate",
                                fixed=lambda f: any(hole_at(x, y, 3.25)(f) for x, y in rb),
                                loaded=hole_at(0.0, LS_Y, NP_HOLE / 2), force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.05))
    fb = [(FS_X - 15.0, FB_Y), (FS_X + 5.4, FB_Y)]
    d.loadcases.append(LoadCase("nut_thrust_front", "nut_plate_fr",
                                fixed=lambda f: any(hole_at(x, y, 3.25)(f) for x, y in fb),
                                loaded=hole_at(FS_X, FS_Y, NP_HOLE / 2), force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.05))
    ptw = towers[2][4]
    d.loadcases.append(LoadCase("z_tower_thrust", "z_fr_r3",
                                fixed=lambda f: any(hole_at(x, y, clearance_hole("M5") / 2)(f) for x, y in ptw),
                                loaded=lambda f: abs(f.center().Z - Z_UB) < 1e-6, force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.05))
    d.loadcases.append(LoadCase("x_belt_pull", "x_belt_bracket", fixed=lambda f: abs(f.center().Y - (YB0 + R_TPF)) < 1e-6,
                                loaded=lambda f: abs(f.center().Z - (Z_XL + 0.7)) < 1e-6 and f.area > 100,
                                force=(60.0, 0.0, 0.0), min_fos=3.0, max_deflection=0.1))
    # ================= heat: bed 60 K above the frame =============================
    d.thermalcases.append(ThermalCase(
        "bed_heated_60K", ["bed_plate", "bed_magnet", "bed", *posts, *carrier, *zcars, *nplates],
        fixed=[(c, on_rail) for c in zcars] + [(nb, on_nut) for nb in nplates],
        temps={"bed_magnet": 60.0, "bed_plate": 60.0, "bed": 60.0, **{c: 30.0 for c in posts},
               "bed_tie": 30.0, "bed_tie_spacer_0": 45.0, "bed_tie_spacer_1": 45.0, "*": 0.0},
        probes={"nozzle": (-UP_X, Y_FACE - 8.0, ZC1), "bed": (0.0, YB0 + HOT_OFF, Z_SURF - T_SHEET)},
        gaps={"nozzle gap": ("nozzle", "bed", "z", 0.1)}, flatness=("bed_plate", "z", 0.1)))
    add_requirements(d, zs)
    assign(d, sheet="sendcutsend", machined="xometry")
    return d


def add_requirements(d, zs):
    def jr(dd, name):
        return next(j for j in dd.joints if j.name == name)

    def motors_of(dd, name):
        mm_ = jr(dd, name).drive["motor"]
        return [mm_] if isinstance(mm_, str) else list(mm_)

    def nozzle_tip(dd):
        return dd.tool_point[1]

    def travel(dd):
        t = {n: jr(dd, n).range[1] - jr(dd, n).range[0] for n in "xyz"}
        return t["x"] >= PRINT_X and t["y"] >= PRINT_Y and t["z"] >= PRINT_Z, str(t)
    d.requirements.append(Requirement("print volume: travel >= 180 x 180 x 180 mm", travel))

    def nozzle_over_bed(dd):
        nx, ny, _ = nozzle_tip(dd)
        bb = dd.get("bed_plate").shape.bounding_box()
        xr_, yr_ = jr(dd, "x").range, jr(dd, "y").range
        m = min(nx + xr_[0] - bb.min.X, bb.max.X - (nx + xr_[1]), ny + yr_[0] - bb.min.Y, bb.max.Y - (ny + yr_[1]))
        return m >= 0, f"smallest nozzle-to-bed-edge margin over the XY travel: {m:.1f} mm"
    d.requirements.append(Requirement("nozzle stays over the bed plate for all XY positions", nozzle_over_bed))

    def bed_gap(dd):
        top = dd.get("bed").shape.bounding_box().max.Z
        gap = nozzle_tip(dd)[2] - (top + PRINT_Z)
        beyond = jr(dd, "z").range[1] - PRINT_Z
        return (-1e-9 <= gap <= 0.2 + 1e-9 and beyond >= 0, f"nozzle tip is {gap:.2f} mm above the bed surface with the bed {PRINT_Z:g} mm up")
    d.requirements.append(Requirement("bed can reach the nozzle: 0-0.2 mm gap at the top of the print height", bed_gap))
    d.requirements.append(Requirement("bed carries the 1.0 kg payload as mass", lambda dd: (
        (m := dd.get("bed_plate").mass()) >= dd.get("bed_plate").shape.volume * MATERIALS[CAST].density * 1e-9 + PAYLOAD_KG - 1e-9,
        f"bed plate + payload {m:.3f} kg")))

    def speeds(dd):
        s = {n: (jr(dd, n).max_speed, jr(dd, n).max_accel) for n in "xyz"}
        ok = all(s[n][0] >= V_XY and s[n][1] >= A_XY for n in "xy") and s["z"][0] >= V_Z and s["z"][1] >= A_Z
        return ok, str(s)
    d.requirements.append(Requirement("X/Y 250 mm/s at 4000 mm/s^2, Z 12 mm/s at 200 mm/s^2", speeds))
    d.requirements.append(Requirement("drive margin >= 3x on every axis", lambda dd, m: (
        set(m["motion"]["drives"]) == {"x", "y", "z"} and all(v["margin"] >= MARGIN for v in m["motion"]["drives"].values()),
        str({k: v["margin"] for k, v in m["motion"]["drives"].items()}))))
    d.requirements.append(Requirement("all four belts routed: constant length, clear of parts", lambda dd, m: (
        all(b in m["motion"].get("belts", {}) and m["motion"]["belts"][b]["clear_of_parts"]
            and m["motion"]["belts"][b]["length_change_over_travel_mm"] <= 0.3 for b in ("x_belt", "y_belt", "y_belt_l", "z_belt")),
        str({b: (v.get("clear_of_parts"), v.get("length_change_over_travel_mm")) for b, v in m["motion"].get("belts", {}).items()}))))

    def rail_margins(dd):
        out = {}
        rails = {"y_carriage_left": "y_rail_left", "y_carriage_right": "y_rail_right", "x_carriage": "x_rail", **zs["rails"]}
        for n, rail in rails.items():
            ax = n[0].upper()
            cb, rb = dd.get(n).shape.bounding_box(), dd.get(rail).shape.bounding_box()
            lo, hi = jr(dd, ax.lower()).mechanical_range
            out[n] = round(min(getattr(cb.min, ax) + lo - getattr(rb.min, ax), getattr(rb.max, ax) - getattr(cb.max, ax) - hi), 2)
        return min(out.values()) >= 5.0, str(out)
    d.requirements.append(Requirement("every carriage stays >= 5 mm inside its rail ends over the mechanical travel", lambda dd: rail_margins(dd)))

    def z_beyond(dd):
        ok_rail, detail = rail_margins(dd)
        left = {t: dd.get(f"leadscrew{t}").shape.bounding_box().max.Z - (dd.get(f"z_nut{t}").shape.bounding_box().max.Z + PRINT_Z + Z_UP)
                for t in zs["tags"]}
        return ok_rail and min(left.values()) >= 5.0, f"with Z {Z_UP:g} mm past the nozzle plane: {detail}; lead screws {min(left.values()):.1f} mm above their nuts"
    d.requirements.append(Requirement(f"Z rails, blocks, screws and nuts allow {Z_UP:g} mm of travel beyond the nominal nozzle plane", z_beyond))
    d.requirements.append(Requirement("Z rails and lead screws end below the top back extrusion (no rubbing)", lambda dd: (
        max(t := [dd.get(n).shape.bounding_box().max.Z for n in ["z_rail_left"] + [f"leadscrew{t_}" for t_ in zs["tags"]]]) < FZ - 10,
        f"rail top {t[0]:.1f}, screw tops {' / '.join(f'{v:.1f}' for v in t[1:])} vs extrusion underside {FZ - 10:.1f}")))
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(mn).sku.startswith("NEMA17") and dd.get(mn).meta["catalog"] for n in "xyz" for mn in motors_of(dd, n)),
        str({n: [dd.get(mn).sku for mn in motors_of(dd, n)] for n in "xyz"}))))
    d.requirements.append(Requirement("Z lead screws self-locking (efficiency < 0.5)", lambda dd: (
        all(dd.get(f"leadscrew{t}").ratings["efficiency"] < 0.5 for t in zs["tags"]), f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    d.requirements.append(Requirement("reported, not a limit: part count", lambda dd: (True, f"{len(dd.components)} parts")))
    d.requirements.append(Requirement(f"target: direct drive, at most {MAX_TOOLHEAD_KG:g} kg moving in X", lambda dd: (
        dd.get("extruder").body == "xbody" and (m := sum(c.mass() for c in dd.components if c.body == "xbody")) <= MAX_TOOLHEAD_KG,
        f"{m:.3f} kg on the X guide block, block included")))
    d.requirements.append(Requirement(f"target: both Y belts within 1 mm of plane in >= {MIN_BELT_IN_PLANE:.0%} of builds", lambda dd, m: (
        all(m["tolerance"]["belts"][b]["p_within_1mm"] >= MIN_BELT_IN_PLANE for b in ("y_belt", "y_belt_l")),
        str({b: m["tolerance"]["belts"][b]["p_within_1mm"] for b in ("y_belt", "y_belt_l")}))))
    d.requirements.append(Requirement("the bed probe switches before the nozzle touches for every unit, and over-travel ends short of its face", lambda dd, m: (
        (pz := m["subsystems"]["homing"]["z"])["z_offset_range_mm"][0] > 0.3 and Z_UP < PRB_H,
        f"nozzle {pz['z_offset_range_mm'][0]:.2f} .. {pz['z_offset_range_mm'][1]:.2f} mm above the bed when the probe switches")))
    STANDINS = sorted(["bed_magnet"] + [f"bed_post_{i}" for i in range(len(BED_MOUNTS))] + ["bed_insert_0", "bed_insert_1"])
    d.requirements.append(Requirement("target: no purchased part is a stand-in where the catalogue has a real one", lambda dd: (
        sorted(px := [c.name for c in dd.components if c.cots and not c.meta.get("catalog")]) == STANDINS,
        f"hand-made purchased parts: {px} (the PEI180's magnetic base, threaded rod and thread inserts: the catalogue has none)")))
    d.requirements.append(Requirement("no printed part in a load path (owner's guideline): printed parts are only the probe holder, duct and covers", lambda dd: (
        sorted(pp := [c.name for c in dd.components if c.material in ("abs", "petg", "pla") and not c.cots]) ==
        sorted(["probe_mount", "part_duct", "mains_cover_relay", "mains_cover_psu", "mains_cover_inlet"]), f"printed: {pp}")))
    d.requirements.append(Requirement("bed sag under 1 kg at the worst print corner <= 0.02 mm (screw-only bound)", lambda dd, m: (
        (pw := m["fea"]["bed_support"]["print_weight"])["judged_mm"] <= 0.02 + 1e-9, f"{pw['judged_mm']:.4f} mm at {pw.get('worst_point')}")))
    d.requirements.append(Requirement("every lead-screw nut stays seated with two screws at opposite lead limits (LSC-015)", lambda dd, m: (
        not (lv := m["fea"]["bed_support"]["nut_seating_and_lead_error"]["levels"][2])["a_nut_unseats"],
        f"height error {lv['height_error_mm']} mm; least nut load margin {min(lv['nut_load_margin_n'].values()):.1f} N")))
