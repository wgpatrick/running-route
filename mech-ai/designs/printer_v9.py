"""printer_v9: printer_v8_2 with a new Z stage and bed, from the owner's sketch. docs/PRINTER_V9.md has the numbers, every
judgement call and the open items.

The owner's sketch and notes: three lead-screw steppers as v8.2, the Z stage guided on THREE vertical linear rails (one
near each screw), the bed as large as the cube allows, the carrier a closed square of 2020 extrusion under the bed, six
simple brackets off that square (three to the nuts, three to the rail carriages), a thin (1/8 in) aluminium deck on the
square, and the bed floating a small distance above the deck on four spring-loaded levelling screws with thumb nuts.

What changed from v8.2 (everything else, gantry, toolhead, frame cube and electronics, is v8.2's: designs/printer_v8_2.py):

1. BED: 265 x 265 x 6.35 mm MIC-6 plate (v8.2: 220 x 256.5 x 9.525) under a 257 x 257 mm PEI spring-steel sheet with
   magnetic base (v8.2: 180 x 180): the largest catalogue sheet that fits the cube (clear width 300 between the posts, less
   the two side rails and their blocks: 264.5; the next sheet size up is 300). Heater: a 190 x 180 mm, 180 W pad between
   the levelling screws.
2. PRINT AREA: the gantry is v8.2's, untouched, so the nozzle still reaches 180 mm in X and 214.5 mm in Y (world y -102.75
   to 111.75). v8.2 printed on 180 of that 214.5 (the other 34.5 mm is travel so the probe, 34.5 mm behind the nozzle,
   reaches the front of the sheet). With a sheet under the whole reach the declared print area is 180 x 214.5 mm; the
   bed is centred on that reach (y 4.5), and the front 34.5 mm of it is beyond the probe (the mesh holds its nearest
   value there). XY travel, not the bed, is what limits the useful area: see the doc for what limits X and Y and the
   frame / gantry change that would unlock more (proposed there, NOT made here).
3. Z GUIDES: three MGN12 rails, one ZF block each: on new uprights in the left and right walls (y -32) and one in the
   back wall (x 65). Each block is tied to the square by one flat 1.6 mm 6061 plate whose 30 mm web is a flexure: stiff
   along the wall (the block's tangential direction), soft square to it (251 N/mm). Left and right blocks hold Y and yaw,
   the rear block holds X: three stiff directions for the three in-plane freedoms, so rail error and the carrier's thermal
   growth go into the webs, not into the balls. The tilt is held by the three screws, as v8.2.
4. CARRIER: a closed rectangle of 2020 (two full-length side members, front and rear members between them, four cast
   corner brackets inside), 270.8 x 281.8 mm outside, with a 3.175 mm 6061 deck bolted on top (ten M5 into T-nuts): the
   deck closes the rectangle in shear and is the levelling datum.
5. SIX BRACKETS, TWO SHAPES: three identical carriage plates (item 3) and three identical 4.75 mm 6061 nut plates under the
   square (two M5 from below into T-nuts), each with v8.2's floating, captive T8 nut (keeper, anti-rotation pin). The three
   motor plates are now one shape too: the rear screw moved onto the back rail's centre line (y 170, v8.2 180).
6. BED MOUNT: four M4 x 35 countersunk screws from the plate's top face (heads 0.7 mm under the magnetic base), each locked
   to the plate by a washer and nut underneath (a fixed stud, no tapped aluminium); a Century Spring DJ-8X20YCS die spring
   (7.6 N/mm, compressed 6 mm: 46 N) between that nut and the deck; under the deck a large washer and a DIN 466 M4 knurled
   thumb nut. The springs push the bed up against the thumb nuts, so in service the bed is held by the studs, not by the
   springs, as long as the load on a point stays under its preload. Deck holes: one fitted (4.3), one slot, two oversize
   (5.5), so the heated plate grows freely. Gap bed to deck: 18.8 mm.

Layout (X = width, Y = depth with the front at -Y, Z = up) is v4's; see designs/printer_v4.py for the history.

Not modelled (flagged): as v8.2 (Roto envelope, T-nuts, PEM nuts, BAT85, Revo clip are BOM lines or notes; payload is extra
mass on the bed plate; no airflow model; pulley set screws; belt teeth; screw whip by hand in the doc), and: the springs
are tubes (not coils) and are left out of the FEA (the studs carry the bed while preloaded; the doc works the spring,
preload, resonance and over-constraint sums by hand); friction at the sliding levelling points.
"""
import math

import numpy as np
from build123d import (Box, Cylinder, GeomType, Location, Plane, Polygon, Pos, RectangleRounded, RegularPolygon, Rot,
                       chamfer, extrude, fillet)

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import MATERIALS, Belt, ModalCase, ThermalCase
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, add_washer, clearance_hole,
                            endstop_switch, extrusion_2020, gt2_idler, gt2_pulley, leadscrew_nut_t8,
                            mgn12_rail, mgn12h_carriage, nema17, place, printed_clearance_hole)
from mechloop.parts.batch6 import fan_cg3010u24
from mechloop.parts.batch7 import leadscrew_motor_17e19_ab4, leadscrew_screw_17e19_ab4, octopus_v11
from mechloop.parts.batch8 import add_thumb_nut, die_spring_dj8x20, print_sheet_pei257
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       iec_inlet_c14, psu_lrs, raspberry_pi_zero2w, relay_btt_v12, thermal_fuse)
from mechloop.parts import CSK
from mechloop.parts.hardware import WASHER, spacer_round
from mechloop.parts.probes import add_probe_nuts, probe_omron_e2e
from mechloop.parts.toolhead import extruder_roto, hotend_revo
from mechloop.shops import assign

# ---- brief ------------------------------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 180.0, 214.5, 180.0     # v9: Y is the whole of the gantry's nozzle travel (v8.2 printed on 180 of it)
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
RUN_CURRENT = {"x": 0.28, "y": 1.20, "z": 0.80, "extruder": 0.40}   # z: per motor, three motors (rated 1.68 A)
BOARD_XY = (94.5, 5.0)  # BTT Octopus V1.1, turned so its motor connectors face +X (the right-hand rail)
HOST_XY = (80.0, -105.0)
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
FRONT_EXT = 13.0       # v8.2 (owner review): the frame's front is 13 mm further forward and its top front rail flush with the
                       # other three (v8.1: 30 mm lower, FT_DROP, so the gantry's front parts passed over it). At full -Y
                       # over-travel the gantry's front-most parts below z 407 (the X mounts' M5 bolt heads on the beam's
                       # front face) reach y -169.5; the flush rail's inner face is now at -173.0 (3.5 mm clear). The X idler
                       # mount's and tension anchor's lugs are trimmed to start 4 mm above the rail (z 408). 13 mm keeps the
                       # machine inside its 420 mm envelope (26 mm, lugs untrimmed, made it 431)
FD = FY + FRONT_EXT    # frame depth, outside to outside of the front and back rails
FRONT_Y = -(FY / 2 - 10) - FRONT_EXT   # centre line of the front rails and posts (v8.1 -170)

# ---- Z stage (v9): bed, deck, 2020 square, three rails ------------------------------
SHEET = 257.0          # print sheet (catalogue print_sheet_pei257): the largest catalogue size that fits the cube
BED = 265.0            # MIC-6 plate, square: 4 mm of margin round the sheet
T_BED = G64            # 6.35 mm MIC-6 (v8.2 9.525): stocked, faces as cast; four supports 208 x 196 apart
T_MAG = 1.5            # the sheet's magnetic base: NOT published by the seller; 1.5 mm from two other sellers' kits (stand-in)
T_SHEET = 0.4          # spring steel (catalogue; a third-party figure)
BED_CY = 4.5           # centre of sheet and plate in Y = centre of the gantry's (unchanged) nozzle reach, world y -102.75 .. 111.75
BED_Y0, BED_Y1 = BED_CY - BED / 2, BED_CY + BED / 2
W5 = WASHER["normal"]["M5"][2]
PAD_X, PAD_Y = 190.0, 180.0   # heater pad, between the levelling screws
# guides: one MGN12 rail + one ZF block per wall; a flat plate with a flexure web ties each block to the square
RAIL_FACE = 13.0       # MGN12H: rail base to the block's mounting face
T_CP = G16             # carriage plates: 1.6 mm 6061 (the web is the radial flexure)
CP_W, CP_WEB, L_FLEX = 50.0, 24.0, 30.0      # plate width, web width, web length
CP_BOLT_U = 16.0       # the plate's two M5 into the square, +/- along the wall from the rail (the driver passes the upright)
K_FLEX = MATERIALS[AL].E * CP_WEB * T_CP ** 3 / L_FLEX ** 3        # web as a guided beam: 12 E I / L^3 = 251 N/mm
FLEX_RANGE = 0.35      # mm: web bending stress 3 E t x / L^2 = 129 MPa there (half of 6061-T6's yield)
WEB_TEST_N = 5.0       # FEA beam test of the web (AssemblyCase carriage_plate_web)
WEB_TEST_MM = WEB_TEST_N * (L_FLEX ** 3 / 3 + L_FLEX ** 2 * 23.7 + L_FLEX * 23.7 ** 2) / (MATERIALS[AL].E * CP_WEB * T_CP ** 3 / 12)
WALL_X = FX / 2 - 20   # inner face of the side walls (150)
UP_Y = FY / 2 - 10     # rear upright in the back wall (y 170)
Y_FACE = UP_Y - 10     # inner face of the back wall (160)
UP_R_X = 65.0          # rear upright: beside the rear screw's motor plate
UP_S_Y = -32.0         # side uprights: between the front motor mounts and the mains inlet's hood
SQ_X = WALL_X - RAIL_FACE - T_CP          # the square's outer side faces at +/-135.4
SQ_Y1 = Y_FACE - RAIL_FACE - T_CP         # its rear outer face (145.4)
SQ_Y0 = 2 * BED_CY - SQ_Y1                # its front outer face (-136.4): the rectangle is centred on the bed
T_DECK = G32           # deck: 3.175 mm 6061 (1/8 in)
# bed mount: stud (M4 countersunk) - washer - nut - die spring - seat washer - deck - large washer - thumb nut
W4, W4L, NUT4 = WASHER["normal"]["M4"][2], WASHER["large"]["M4"][2], 3.2
SPRING_H = 14.0        # DJ-8X20YCS installed: 6 mm of its 20 compressed, 45.6 N (range 12..16 mm: 61..30 N)
SPRING_K = 7.6
GAP = W4 + NUT4 + SPRING_H + W4           # plate underside to deck top: 18.8 mm
STUD_L = 35.0
CSK_SINK = (CSK["M4"][0] - CSK["M4"][1]) / 2      # 0.72 mm: how far an M4 countersunk head sits below the surface
LEVEL_RANGE = 2.0      # +/- at each thumb nut
LEV_X, LEV_Y = 104.0, 98.0                # studs at (+/-104, BED_CY +/- 98): thumb nuts clear the square's corner brackets
# deck hole per stud (thermal growth of the plate): 0 fitted, 1 slot towards 0, 2 and 3 oversize
BED_MOUNTS = [(-LEV_X, BED_CY - LEV_Y), (LEV_X, BED_CY - LEV_Y), (-LEV_X, BED_CY + LEV_Y), (LEV_X, BED_CY + LEV_Y)]
DECK_FIT, DECK_FREE = 4.3, 5.5
LS_Y = FY / 2 - 10     # rear lead screw on the bottom back rail's centre line (v8.2: 180, its outer edge)
FS_X = FX / 2 - 10     # front lead screws over the bottom side rails
FS_Y = -101.0
NUT_OUT = FS_X - SQ_X  # every nut axis is 24.6 mm outboard of the square's face: one nut plate shape
NUT_PIN = (0.0, 8.0)
NUT_FLOAT = 2.8
KEEP_GAP, T_KEEP, KEEP_BX = 0.1, 3.175, 17.6   # nut keeper: axial play, thickness (6061), bolts +/- along the member from the nut
Z_DN = 3.0
Z_UP = 1.65
Z_RAIL_L = 250.0

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
LUG_Z0 = FZ + 10.0 + 4.0  # v8.2: the X idler mount's lug and the X tension anchor's fin start 4 mm above the flush top front rail
X_PG = 2.75
XB_Y = YB0 - 10.0 + X_PG + P_BC(BWX)
X_SP = XB_Y - I_H(BWX) / 2 - (YB0 - 10.0)
Z_XL = XD_Z - PR
Y_SP = 2 * W5                      # v8.2: two M5 washers between each Y idler and its mount (BLT-061: 2 mm to the plate; v8.1 one)
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
PL_Y0, PL_Y1 = -23.5, 19.5     # v8.2: front edge 0.5 mm back (BLT-061: 2.05 mm from the Y idler at full travel)
BELT_SLOTS = (-15.3, -5.5, 5.5, 15.3)   # v8.1: slots as wide as the sheet is thick, webs >= 4.75
SLOT_W = 4.8
YP_IN = RAIL_X - 33.0
YP_NOTCH = (RAIL_X - 15.5, -8.0)

# bed heights follow from the nozzle
Z_SURF = Z_NOZZLE - NOZZLE_GAP - PRINT_Z
Z_BED = Z_SURF - T_SHEET - T_MAG - T_BED          # underside of the bed plate
Z_DECK1 = Z_BED - GAP                             # top of the deck
Z_SQT = Z_DECK1 - T_DECK                          # top of the 2020 square
Z_SQ = Z_SQT - 10.0
Z_SQB = Z_SQ - 10.0
T_NP = G48                                        # nut plates: 4.75 mm 6061, under the square (the keeper bolts' 4.8 mm holes are not under the thickness)
Z_TAB = Z_SQB - T_NP                              # underside of the nut plates = top of each nut's flange
ZC = Z_SQB - L_FLEX - 1.0 - 22.7                  # centre of the guide blocks (they hang below the square on the plates' webs)
Z_RAIL_C = ZC + (PRINT_Z + Z_UP - Z_DN) / 2       # rails centred on the blocks' travel
NP_HOLE = 2 * (5.1 + NUT_FLOAT) + 0.8             # the nut's barrel floats in a round hole
NP_U, NP_R1 = 32.0, 21.5                          # nut plate: half length along the member, reach beyond the nut
NP_BOLT_U = 20.0                                  # its two M5 into the member's bottom slot
PIN_SP_D = 5.0                                    # anti-rotation pin: an M2.5 screw through a 5 mm aluminium sleeve
# ---- Z drive: three integrated lead-screw motors, one per screw, no belt (v8.2) ---------------------------------------
Z_MF = 78.0                                      # motor mounting face = underside of the motor plate
T_MP = G64                                       # motor plate 6.35 mm 6061
Z_MPT = Z_MF + T_MP
Z_SCREW_ABOVE = 258.0                            # screw above the face after cutting (328 as sold): top at 336 (v8.2 252: the
                                                 # nuts ride 40 mm higher now that the bed sits close above the carrier)
MP_POST_DY = 28.0                                # posts on the rail under the motor, +/- along the rail from the screw
MP_PILOT_HOLE = 22.3                             # the motor's 22 mm pilot locates in it
PSU_COVER_TOP = 56.04                            # mains cover over the supply's terminals (v8.1: 2.8 mm under its belt plane)
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
TY_F = TY                                       # v9: the print area is the whole Y travel; the front PRB_DY of it is beyond the probe
YI_Y = YB0 - 24.0 - (TY_F + ES_OT) - 10.5      # as v8.1 (same place in the frame as v8.2: the home pose moved, the travel did not)
# Klipper [z_tilt]: firmware X = world x + TX (X homes at -TX), firmware Y = world y - (nozzle's home y) + TY_F
_FW = lambda x, y: (round(x + TX, 2), round(y - (YB0 + HOT_OFF) + TY_F, 2))
Z_TILT = {"z_positions": [_FW(0.0, LS_Y), _FW(-FS_X, FS_Y), _FW(FS_X, FS_Y)],       # rear, front-left, front-right screw
          "points": [(90.0, 185.0), (10.0, 5.0), (170.0, 5.0)],                       # nozzle; probe 34.5 mm behind it
          "speed": 100, "horizontal_move_z": 5, "retries": 5, "retry_tolerance": 0.0075}
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
def countersink_z(x, y, z_top, depth_total, d_csk, d_hole):
    """A 90-degree countersink from the top face z_top (mouth d_csk) with a through clearance hole d_hole, as a solid to cut."""
    from build123d import Cone
    h = (d_csk - d_hole) / 2.0
    return Pos(x, y, z_top - h / 2) * Cone(d_hole / 2, d_csk / 2, h) + zc(x, y, z_top - depth_total, z_top, d_hole / 2)


def bed_shape_():
    """6.35 mm MIC-6 cast plate, laser cut (faces as cast), no tapped holes: four M4 countersunk screws from the top, in
    90-degree countersinks (8.96 mm; SendCutSend's countersinking service or the builder's countersink bit), heads 0.7 mm
    below the surface: the magnetic base lies flat over them."""
    b = bx(-BED / 2, BED / 2, BED_Y0, BED_Y1, Z_BED, Z_BED + T_BED)
    for x, y in BED_MOUNTS:
        b -= countersink_z(x, y, Z_BED + T_BED, T_BED, CSK["M4"][0], clearance_hole("M4"))
    return b


def rz(shape, cx, cy, ang):
    """A shape drawn about the origin, turned `ang` degrees about Z and moved to (cx, cy)."""
    return Pos(cx, cy, 0) * Rot(0, 0, ang) * shape


def rxy(u, r_, cx, cy, ang):
    """Local (u along the member, r_ outward from the square) -> world x, y for a bracket turned `ang` about Z."""
    a = math.radians(ang)
    return (cx + u * math.cos(a) - r_ * math.sin(a), cy + u * math.sin(a) + r_ * math.cos(a))


def nut_plate_local(z0, z1):
    """One nut plate, about its nut's axis: local x along the square's member, local y outward. It lies under the member
    (y from -NUT_OUT - 20 to -NUT_OUT), two M5 from below into the member's bottom slot, and reaches out to the nut: the
    barrel in a round hole, the pin's sleeve in a radial slot, two holes for the keeper's through-bolts."""
    h = z1 - z0
    yc, ly = (NP_R1 - NUT_OUT - 20.0) / 2, NP_R1 + NUT_OUT + 20.0
    s = Pos(0, yc, z0) * extrude(RectangleRounded(2 * NP_U, ly, 3.0), h)
    s -= zc(0, 0, z0, z1, NP_HOLE / 2)
    s -= slot_z(0, NUT_PIN[1], 90.0, NUT_FLOAT, PIN_SP_D + 1.2, z0, z1)
    for u in (-NP_BOLT_U, NP_BOLT_U):
        s -= zc(u, -NUT_OUT - 10.0, z0, z1, clearance_hole("M5") / 2)
    for u in (-KEEP_BX, KEEP_BX):
        s -= zc(u, 0, z0, z1, 4.8 / 2)          # keeper bolts (4.8: with a large washer; M3 clearance is under the sheet's thickness)
    return s


def nut_keeper_local(z0, z1):
    """The keeper under a nut's flange (v8.2), drawn about the nut's axis: local x along the member."""
    from build123d import Circle, SlotOverall
    s = Pos(0, 0, z0) * extrude(RectangleRounded(50.0, 36.0, 3.0), z1 - z0)
    # the barrel's hole and the slot the pin's nut moves in, as one opening; its four corners rounded (v8.2's were sharp)
    cut = Circle(NP_HOLE / 2) + Pos(0, NUT_PIN[1]) * Rot(0, 0, 90) * SlotOverall(2 * NUT_FLOAT + 7.0, 7.0)
    try:
        cut = fillet(cut.vertices(), 0.8)
    except Exception:
        pass
    s -= Pos(0, 0, z0) * extrude(cut, z1 - z0)
    for u in (-KEEP_BX, KEEP_BX):
        s -= zc(u, 0, z0, z1, clearance_hole("M3") / 2)
    return s


def carriage_plate_local(z_blk):
    """One carriage plate in its own frame: x along the wall, y up (0 at the square's centre line), z from the block's
    mounting face (0) towards the square (T_CP). Top 20 mm: on the square's outer face, two M5 into T-nuts. Then the web,
    L_FLEX long and CP_WEB wide: the flexure. Below it the block's face, four M3. z_blk: the block's centre, from the
    square's centre line."""
    y0, y1 = z_blk - 22.7 - 1.0, -10.0 - L_FLEX          # bottom edge; top of the block's zone
    s = Pos(0, 0, 0) * extrude(RectangleRounded(CP_W, 20.0, 2.0), T_CP)                         # on the square
    s += Pos(0, (y0 + y1) / 2, 0) * extrude(RectangleRounded(CP_W, y1 - y0, 2.0), T_CP)          # on the block
    s += bx(-CP_WEB / 2, CP_WEB / 2, y1 - 1.0, -9.0, 0, T_CP)                                    # the web
    for sx in (-1, 1):                               # 3 mm radii where the web meets the two zones
        s += fillet_z(sx * CP_WEB / 2, -10.0, sx, -1, 3.0, 0, T_CP)
        s += fillet_z(sx * CP_WEB / 2, y1, sx, 1, 3.0, 0, T_CP)
    for u in (-CP_BOLT_U, CP_BOLT_U):
        s -= Pos(u, 0, T_CP / 2) * Cylinder(clearance_hole("M5") / 2, T_CP)
    for u in (-10.0, 10.0):
        for v in (-10.0, 10.0):
            s -= Pos(u, z_blk + v, T_CP / 2) * Cylinder(clearance_hole("M3") / 2, T_CP)
    return s


def deck_shape():
    """3.175 mm 6061 deck on the square: flush with its outer faces, ten M5 holes over the members' top slots, and one
    hole per bed stud: stud 0 a fitted 4.3 mm hole (locates the bed), stud 1 a 4.3 mm slot pointing at stud 0, studs 2 and
    3 oversize (5.5 mm), so the heated plate grows without bending its studs."""
    z0, z1 = Z_SQT, Z_DECK1
    s = Pos(0, BED_CY, z0) * extrude(RectangleRounded(2 * SQ_X, SQ_Y1 - SQ_Y0, 4.0), T_DECK)
    for x, y in DECK_BOLTS:
        s -= zc(x, y, z0, z1, clearance_hole("M5") / 2)
    (x0, y0), (x1, y1) = BED_MOUNTS[0], BED_MOUNTS[1]
    s -= zc(x0, y0, z0, z1, DECK_FIT / 2)
    s -= slot_z(x1, y1, 0.0, 1.0, DECK_FIT, z0, z1)
    for x, y in BED_MOUNTS[2:]:
        s -= zc(x, y, z0, z1, DECK_FREE / 2)
    return s


DECK_BOLTS = ([(sx * (SQ_X - 10.0), BED_CY + dy) for sx in (-1, 1) for dy in (-100.0, 0.0, 100.0)]
              + [(sx * 55.0, y) for sx in (-1, 1) for y in (SQ_Y0 + 10.0, SQ_Y1 - 10.0)])
# the three guides: (name, rail-base point on the wall (x, y), inward normal, frame rails the upright stands between)
GUIDES = [("left", (-WALL_X, UP_S_Y), (1.0, 0.0, 0.0), "left"), ("right", (WALL_X, UP_S_Y), (-1.0, 0.0, 0.0), "right"),
          ("rear", (UP_R_X, Y_FACE), (0.0, -1.0, 0.0), "back")]
# the three nuts: (tag, screw x, y, turn of the nut plate about Z (local y = outward), member it bolts under)
NUTS = [("", 0.0, LS_Y, 0.0, "sq_rear"), ("_fl", -FS_X, FS_Y, 90.0, "sq_left"), ("_fr", FS_X, FS_Y, -90.0, "sq_right")]


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
    """As v8.1, with the BTT Octopus V1.1 in place of the SKR Mini E3 V3.0: seven drivers used, one motor each (X M0, Y
    M1, Y left M2, Z rear M3, extruder M4, Z front-left M5, Z front-right M6; M7 spare); X and Y switches and the probe on
    STOP0 / STOP1 / STOP2 (their DIAG jumpers removed), the probe still through a BAT85 on an ordinary 3.3 V input; the
    Pi Zero 2 W on the Octopus's Raspberry Pi header (5 V, GND, UART2); Klipper [z_tilt] with the three screw positions."""
    from mechloop.electrical import add_board_5v_port

    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend", "part_fan", "x_endstop", "y_endstop", "bed_probe", "x_motor",
               "z_motor", "z_motor_fl", "z_motor_fr", "extruder", "y_motor", "y_motor_l"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed_plate")
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
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (147.0, 60.0, zt)), ("world", (147.0, -40.0, zt))])   # v9: inboard of the right upright
    el.loom("back", [("world", (140.0, 152.0, 30.0)), ("world", (130.0, 160.0, 12.0)), ("world", (66.0, 160.0, 12.0)),
                     ("world", (10.0, 140.0, 32.0))])
    el.loom("gantry", [Waypoint("ybody", (-142.0, YB0 + PL_Y0 + 5.0, Z_PLATE - 1.5), clamp="y_plate_left"),
                       Waypoint("world", (XL - 2.0, FRONT_Y + 13.0, FZ - 12.0), clamp="frame_top_left"), ("world", (XL, -124.0, ZL))],
            flex_length={0: 270.0})
    el.loom("top_left", [("world", (XL, -118.0, ZL)), ("world", (XL, 136.0, ZL))])
    el.loom("drop_left", [("world", (XL, -120.0, ZL)),
                          ("world", (-143.0, -140.0, FZ - 24.0)), ("world", (-143.0, -150.0 - FRONT_EXT, FZ - 60.0)),
                          ("world", (-143.0, FRONT_Y, FZ - 90.0)),
                          ("world", (-143.0, FRONT_Y, 70.0)), ("world", (-140.0, FRONT_Y + 4.0, 26.0))])
    el.loom("front", [("world", (-140.0, FRONT_Y + 4.0, 26.0)), ("world", (60.0, FRONT_Y + 4.0, 26.0)), ("world", (72.0, -142.0, zt))])
    el.loom("bed", [Waypoint("zbody", (-40.0, SQ_Y1 - 21.0, Z_SQ + 5.0), clamp="sq_rear"),
                    Waypoint("zbody", (-40.0, SQ_Y1 - 21.0, Z_SQB - 2.0), clamp="sq_rear"),
                    Waypoint("world", (-40.0, TRAY_Y1 - 1.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 365.0})
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
    el.wire("hotend heater", "control_board.HE0", "hotend.in", 20, insulation="silicone", via=tool, pigtail=(115.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, insulation="silicone", via=tool,
            pigtail=(130.0, "fiberglass"))
    el.wire("heat-sink fan 5 V", "control_board.5V", "hotend_fan.out", 26, via=tool,
            note="the Roto's fan is a 5 V part: always on from the board's 5 V pins, never on a 24 V fan output")
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    el.wire("bed probe", "control_board.STOP2", "bed_probe.out", 26, conductors=3, insulation="silicone", via=tool,
            note="signal and 0 V on the STOP2 (DIAG2) header, its DIAG jumper removed; BAT85 diode in the signal lead at the board end, "
                 "cathode to the sensor, heat-shrunk (the Octopus's optocoupled SENSOR port is not used: its firmware polarity is not modelled)")
    # v8.1: the probe's +24 V lead is its own wire, from the supply's second +V terminal
    pr = d.get("bed_probe").meta["interfaces"]
    el.devices["bed_probe"].ports["vcc"] = Port("vcc", "power_in", "JST-XH", 1.0, conductors=1,
                                                at=tuple(pr.get("sensing_face", [(PRB_X, YB0 + PRB_Y, Z_PRB)])[0]),
                                                extra={"body": "xbody", "draw_a": 0.015})
    el.devices["bed_probe"].params.update(supply_v=24.0, supply_from="psu.V+2 (wire 'bed probe 24 V')", series_diode=True)
    el.wire("bed probe 24 V", "psu.V+2", "bed_probe.vcc", 26, conductors=1, insulation="silicone", via=tool,
            note="the sensor's brown lead; runs in the toolhead loom with the probe's signal pair")
    el.wire("extruder motor", "control_board.M4", "extruder.coils", 24, conductors=4, via=tool)
    el.wire("X motor", "control_board.M0", "x_motor.coils", 24, conductors=4, via=left + ["gantry"])
    el.wire("X endstop", "control_board.STOP0", "x_endstop.out", 26, conductors=3, via=left + ["gantry"],
            note="STOP0 (DIAG0) header, its DIAG jumper removed")
    el.wire("Y endstop", "control_board.STOP1", "y_endstop.out", 26, conductors=3, via=["tray_right", "drop_right"],
            note="STOP1 (DIAG1) header, its DIAG jumper removed")
    el.wire("Y motor left", "control_board.M2", "y_motor_l.coils", 24, conductors=4, via=left + ["top_left"],
            note="mirror-image motor on its own driver ([stepper_y1]): invert its dir_pin (or swap one coil pair) so both turn the belts the same way")
    el.wire("Y motor right", "control_board.M1", "y_motor.coils", 24, conductors=4, via=["tray_right", "drop_right"])
    # v8.2: three Z motors, each on its own driver; their 500 mm leads plug straight into the Octopus (front-right: a short
    # stub; front-left: along the front loom; rear: along the back loom)
    el.wire("Z motor rear", "control_board.M3", "z_motor.coils", 24, conductors=4, via=["tray_right", "back"])
    el.wire("Z motor front left", "control_board.M5", "z_motor_fl.coils", 24, conductors=4, via=["front"])
    el.wire("Z motor front right", "control_board.M6", "z_motor_fr.coils", 24, conductors=4)
    el.wire("host serial + 5 V", "control_board.RPI", "host.GPIO", 26, conductors=4,
            note="Octopus 'Raspberry Pi' header (5 V, GND, PD6 RX, PD5 TX: USART2) to the Pi's GPIO 2/6/8/10; Klipper serial /dev/ttyAMA0")
    el.firmware = {
        "kind": "klipper",
        "steppers": {"x": {"run_current": RUN_CURRENT["x"]}, "y": {"run_current": RUN_CURRENT["y"]},
                     "z": {"run_current": RUN_CURRENT["z"]},
                     "extruder": {"motors": ["extruder"], "run_current": RUN_CURRENT["extruder"]}},
        # Z_TILT_ADJUST: the three screws in the firmware's XY (nozzle) coordinates, and three probe points (nozzle
        # positions; the probe is 34.5 mm behind the nozzle) as close to each screw as the probe reaches over the plate
        "z_tilt": Z_TILT,
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


def motor_plate_shape(x0, y0, posts):
    """6.35 mm 6061 plate the motor hangs under: the convex hull of discs round the motor's four screws and the two posts
    (a polygon of short straight cuts), the pilot hole (locates the motor), four M3 and two M5 clearance holes."""
    circ = lambda cx, cy, r: [(cx + r * math.cos(a), cy + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 40, endpoint=False)]
    pts = []
    for ox in (-15.5, 15.5):
        for oy in (-15.5, 15.5):
            pts += circ(x0 + ox, y0 + oy, 6.5)
    for px, py in posts:
        pts += circ(px, py, 8.0)
    s = Pos(0, 0, Z_MF) * extrude(Polygon(*convex_hull(pts), align=None), T_MP)
    s -= zc(x0, y0, Z_MF, Z_MPT, MP_PILOT_HOLE / 2)
    for ox in (-15.5, 15.5):
        for oy in (-15.5, 15.5):
            s -= zc(x0 + ox, y0 + oy, Z_MF, Z_MPT, clearance_hole("M3") / 2)
    for px, py in posts:
        s -= zc(px, py, Z_MF, Z_MPT, clearance_hole("M5") / 2)
    return s


def build_z_mount(d, tag, x0, y0, turn, posts, rail, on_tray):
    """One Z drive: a 17E19S1684AB4-330RA lead-screw motor (body + its integral Tr8x2 screw, cut to Z_SCREW_ABOVE) hanging
    under a laser-cut motor plate on two aluminium spacer posts. Four M3 x 10 from the plate's top thread 3.65 mm into the
    motor's own M3 holes (4.5 deep: 1.2 d, 0.85 mm short of the bottom), thread-locked. Each post: an M5 x 70 with a washer
    under its head through the plate and a 10 mm OD spacer (and the electronics tray at the front) into a T-nut in the
    bottom rail, thread-locked. No top bearing: the screw runs free-ended (docs/PRINTER_V8_2.md: whip, over-constraint).
    Returns its part names."""
    P = lambda n: f"z_mount{tag or '_rear'}_{n}"
    mot, scr, plate = f"z_motor{tag}", f"leadscrew{tag}", f"z_motor_plate{tag}"
    names = [plate, mot, scr]
    sheet(d, plate, motor_plate_shape(x0, y0, posts), AL)
    place(d, mot, leadscrew_motor_17e19_ab4(), Location((x0, y0, Z_MF), (0, 0, turn)))
    place(d, scr, leadscrew_screw_17e19_ab4(Z_SCREW_ABOVE), Location((x0, y0, Z_MF)))
    d.join(scr, mot, "integral screw: the motor's shaft")
    d.get(scr).meta["description"] = (f"Tr8x2 lead screw: the shaft of {mot} itself (StepperOnline 17E19S1684AB4-330RA), cut to "
                                      f"{Z_SCREW_ABOVE:g} mm above the motor face; free at its top end (no bearing). Not a separate part to buy.")
    d.get(mot).meta["description"] = (f"Lead-screw stepper hanging under {plate}: its 22 mm pilot locates in the plate's hole, four M3 x 10 "
                                      f"from above thread into its own housing. Its shaft is the lead screw {scr}.")
    d.allow_overlap(scr, mot)                    # the screw enters the motor through its pilot (the solids meet there)
    d.join(mot, plate, "pilot located in the plate's 22.3 mm hole, face on the plate")
    for i, (ox, oy) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        nm = f"{mot}_screw_{i}"
        add_screw(d, nm, "M3", 10, at=(x0 + ox, y0 + oy, Z_MPT), direction=(0, 0, -1), threads_into=mot, clamps=(plate,),
                  locking="adhesive")
        names.append(nm)
    z_base = (20.0 + T_TRAY) if on_tray else 20.0
    for i, (px, py) in enumerate(posts):
        sp = P(f"spacer_{i}")
        place(d, sp, spacer_round("M5", round(Z_MF - z_base, 3), "aluminium"), Location((px, py, z_base)))
        b = P(f"bolt_{i}")
        add_screw(d, b, "M5", 70, at=(px, py, Z_MPT), direction=(0, 0, -1), clamps=(plate, sp) + (("electronics_tray",) if on_tray else ()),
                  threads_into=rail, tnut=True, washer=True, locking="adhesive")
        names += [sp, b, f"{b}_washer"]
    return names


def build_frame_z():
    d = Design("printer_v9", envelope=ENVELOPE, base="frame_bot_left")
    d.manufacturing = {"shop": "sendcutsend", "sheet": {"method": "laser"},
                       "printer": {"build_volume": (220.0, 220.0, 220.0), "nozzle": 0.4},
                       "print_settings": dict(PRINT_ABS)}
    # ================= frame (v8) ================================================
    # v8.2: the side rails are FRONT_EXT longer, all at the front; the front rails and posts move forward with them and
    # the top front rail is flush with the other three
    yrail = lambda sy: (FY / 2 - 10) if sy > 0 else FRONT_Y
    for sx, n in ((-1, "left"), (1, "right")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FD), Location((sx * RAIL_X, -FRONT_EXT / 2, z), (0, 0, 90)))
    for sy, n in ((-1, "front"), (1, "back")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FX - 40), Location((0, yrail(sy), z)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            place(d, f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}", extrusion_2020(FZ - 30),
                  Location((sx * RAIL_X, yrail(sy), (FZ + 10) / 2), (0, 90, 0)))
    k = 0
    for sx in (-1, 1):
        side = "left" if sx < 0 else "right"
        for sy in (-1, 1):
            post = f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}"
            cross = "front" if sy < 0 else "back"
            yi = yrail(sy) - sy * 10.0
            for lvl, zcen, zdir in (("top", FZ - 10, -1), ("bot", 20, 1)):
                add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{side}", post, (sx * RAIL_X, yi, zcen), (0, -sy, 0), (0, 0, zdir)); k += 1
                if lvl == "top":
                    add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{cross}", post,
                                       (sx * (RAIL_X - 10), yrail(sy), FZ - 10.0),
                                       (-sx, 0, 0), (0, 0, -1)); k += 1
                else:
                    add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{cross}", f"frame_{lvl}_{side}",
                                       (sx * (RAIL_X - 10), yi, 10), (-sx, 0, 0), (0, -sy, 0)); k += 1
    # ================= Z guides (v9): three uprights, three rails, one ZF block each ==========
    # Left and right uprights stand in the side walls between the bottom and top side rails, the rear one in the back
    # wall; each rail is on its upright's inner face. One clearance-class (ZF) block per rail: the three screws hold the
    # carrier's tilt, the blocks only locate it across the axis. Each block's plate has a flexure web, soft square to
    # the wall, so left and right hold Y and yaw and the rear holds X: three stiff directions, none redundant.
    up = np.array([0.0, 0.0, 1.0])
    guide_parts = {}
    for nm, (bx_, by_), nrm, wall in GUIDES:
        nv = np.array(nrm)
        tv = np.cross(up, nv)                            # along the wall
        ux, uy = bx_ - 10.0 * nv[0], by_ - 10.0 * nv[1]
        place(d, f"upright_{nm}", extrusion_2020(FZ - 30), Location((ux, uy, (FZ + 10) / 2), (0, 90, 0)))
        for lvl, zcen, zdir in (("bot", 20, 1), ("top", FZ - 10, -1)):
            for s_, tg in ((-1, "a"), (1, "b")):
                add_corner_bracket(d, f"brkt_up_{lvl}_{tg}_{nm}", f"frame_{lvl}_{wall}", f"upright_{nm}",
                                   (ux + s_ * 10.0 * tv[0], uy + s_ * 10.0 * tv[1], zcen), tuple(s_ * tv), (0, 0, zdir))
        plane = lambda z: Plane(origin=(bx_, by_, z), x_dir=(0, 0, 1), z_dir=tuple(nv))
        rail = place(d, f"z_rail_{nm}", mgn12_rail(Z_RAIL_L), Location(plane(Z_RAIL_C)))
        for i, h in enumerate(rail.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"z_rail_{nm}_screw_{i}", "M3", 8, at=tuple(np.array(h) + 3.5 * nv), direction=tuple(-nv),
                      threads_into=f"upright_{nm}", tnut=True)
        car = place(d, f"z_carriage_{nm}", mgn12h_carriage(preload="ZF"), Location(plane(ZC)), body="zbody", guides="z")
        # the mount floats along the wall's normal on the plate's web (tolerance verifier: mechloop.tolerance._rail_set)
        E_, G_ = MATERIALS[AL].E, MATERIALS[AL].E / (2 * (1 + MATERIALS[AL].nu))
        car.meta["guide_float"] = {"axis": tuple(nv), "stiffness_n_per_mm": round(K_FLEX, 1), "range_mm": FLEX_RANGE,
                                   "by": f"the {L_FLEX:g} x {CP_WEB:g} x {T_CP:g} mm web of carriage_plate_{nm}",
                                   # the web as a beam between block and square, N.mm/rad (E I / L, G J / L): the bed-support
                                   # model puts these in series with the block's own moment stiffness
                                   "rotation_n_mm_per_rad": {"about_float_axis": round(E_ * T_CP * CP_WEB ** 3 / 12 / L_FLEX),
                                                             "about_across": round(E_ * CP_WEB * T_CP ** 3 / 12 / L_FLEX),
                                                             "about_travel": round(G_ * CP_WEB * T_CP ** 3 / 3 / L_FLEX)}}
        face = np.array([bx_, by_, Z_SQ]) + RAIL_FACE * nv          # on the block's mounting plane, at the square's centre line
        cp = Location(Plane(origin=tuple(face), x_dir=tuple(tv), z_dir=tuple(nv))) * carriage_plate_local(ZC - Z_SQ)
        pl = f"carriage_plate_{nm}"
        d.add(pl, cp, material=AL, body="zbody", process="sheet", meta={"finish": "bare", "description": (
            f"Carriage plate ({nm}): one of three identical flat 1.6 mm 6061 plates. Its top 20 mm is bolted to the 2020 square's "
            f"outer face (two M5, T-nuts); its bottom carries the guide block z_carriage_{nm} (four M3 x 5 into the block's own "
            f"threads). The {L_FLEX:g} mm web between them is a flexure: stiff along the wall, soft square to it ({K_FLEX:.0f} N/mm), "
            f"so this block locates the carrier along the wall only and a rail that is not exactly parallel, or a carrier that "
            f"has grown warm, bends the web instead of loading the block.")})
        for i, h in enumerate(car.meta["interfaces"]["mount_holes_m3"]):
            add_screw(d, f"z_carriage_{nm}_screw_{i}", "M3", 5, at=tuple(np.array(h) + T_CP * nv), direction=tuple(-nv), body="zbody",
                      threads_into=f"z_carriage_{nm}", clamps=(pl,), washer=True, locking="adhesive")
        member = "sq_rear" if nm == "rear" else f"sq_{nm}"
        for i, u in enumerate((-CP_BOLT_U, CP_BOLT_U)):
            add_screw(d, f"{pl}_bolt_{i}", "M5", 8, at=tuple(face + u * tv), direction=tuple(nv), body="zbody",
                      threads_into=member, tnut=True, clamps=(pl,), washer=True, locking="adhesive")
        guide_parts[nm] = (nv, np.array([bx_, by_]))

    # ================= carrier (v9): a closed 2020 rectangle, a deck on top =====================
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"sq_{n}", extrusion_2020(SQ_Y1 - SQ_Y0), Location((sx * (SQ_X - 10.0), BED_CY, Z_SQ), (0, 0, 90)), body="zbody")
    for sy, n, yc in ((-1, "front", SQ_Y0 + 10.0), (1, "rear", SQ_Y1 - 10.0)):
        place(d, f"sq_{n}", extrusion_2020(2 * (SQ_X - 20.0)), Location((0, yc, Z_SQ)), body="zbody")
        for sx, sn in ((-1, "left"), (1, "right")):
            # one cast bracket in each inside corner, both legs on T-nuts
            add_corner_bracket(d, f"sq_bracket_{n[0]}{sn[0]}", f"sq_{sn}", f"sq_{n}", (sx * (SQ_X - 20.0), yc - sy * 10.0, Z_SQ),
                               (0, -sy, 0), (-sx, 0, 0), body="zbody")
    d.add("z_deck", deck_shape(), material=AL, body="zbody", process="sheet", meta={"finish": "bare", "description": (
        "Deck: 3.175 mm (1/8 in) 6061 sheet on top of the 2020 square, ten M5 into T-nuts. It closes the rectangle in shear, "
        "shields the carrier from the heater, and is what the bed is levelled against: the four bed studs pass through it "
        "(one fitted hole, one slot, two oversize) and the thumb nuts bear on its underside.")})
    for i, (x, y) in enumerate(DECK_BOLTS):
        member = ("sq_left" if x < 0 else "sq_right") if abs(abs(x) - (SQ_X - 10.0)) < 1e-6 else ("sq_front" if y < BED_CY else "sq_rear")
        add_screw(d, f"z_deck_bolt_{i}", "M5", 10, at=(x, y, Z_DECK1), body="zbody", threads_into=member, tnut=True,
                  clamps=("z_deck",), washer=True, locking="adhesive")

    # ================= nut plates (three identical) and captive floating nuts (v8.2's) ==========
    zn0, zn1 = Z_TAB, Z_SQB
    for tg, cx, cy, ang, member in NUTS:
        W = lambda u, r_: rxy(u, r_, cx, cy, ang)
        d.add(f"nut_plate{tg}", rz(nut_plate_local(zn0, zn1), cx, cy, ang), material=AL, body="zbody", process="sheet", meta={"finish": "bare"})
        for i, u in enumerate((-NP_BOLT_U, NP_BOLT_U)):
            add_screw(d, f"nut_plate{tg}_bolt_{i}", "M5", 10, at=(*W(u, -NUT_OUT - 10.0), zn0), direction=(0, 0, 1), body="zbody",
                      threads_into=member, tnut=True, clamps=(f"nut_plate{tg}",), washer=True, locking="adhesive")
        px, py = W(*NUT_PIN)
        place(d, f"z_nut{tg}", leadscrew_nut_t8(), Location((cx, cy, Z_TAB - 3.5)), body="zbody")
        place(d, f"nut_pin{tg}_sleeve", spacer_round("M2.5", T_NP + 0.2, "aluminium"), Location((px, py, Z_TAB)), body="zbody")
        add_screw(d, f"nut_pin{tg}", "M2.5", 16, at=(px, py, Z_TAB + T_NP + 0.2), body="zbody", clamps=(f"nut_pin{tg}_sleeve", f"z_nut{tg}"))
        add_nut(d, f"nut_pin{tg}_nut", "M2.5", at=(px, py, Z_TAB - 3.5), direction=(0, 0, -1), body="zbody", screw=f"nut_pin{tg}")
        d.allow_overlap(f"nut_pin{tg}", f"z_nut{tg}", max_volume=40.0)     # passes the flange's hole: the catalogue solid does not show the holes
        d.join(f"z_nut{tg}", f"nut_plate{tg}", "floating: the carrier sits on its flange; the pin in the slot stops it turning")
        # captive (v8.2): a 3.175 mm 6061 keeper under the flange, 0.1 mm clear of it, on two M3 through-bolts with 3.6 mm
        # spacers: the flange floats sideways between plate and keeper but the carrier cannot lift off it
        kz1 = Z_TAB - 3.5 - KEEP_GAP
        kz0 = kz1 - T_KEEP
        d.add(f"nut_keeper{tg}", rz(nut_keeper_local(kz0, kz1), cx, cy, ang), material=AL, body="zbody", process="sheet", meta={"finish": "bare"})
        for k_, u in enumerate((-KEEP_BX, KEEP_BX)):
            bx_, by_ = W(u, 0.0)
            spn = f"nut_keeper{tg}_spacer_{k_}"
            place(d, spn, spacer_round("M3", KEEP_GAP + 3.5, "aluminium"), Location((bx_, by_, kz1)), body="zbody")
            bolt_nut(d, f"nut_keeper{tg}_bolt_{k_}", "M3", screw_len(T_NP + KEEP_GAP + 3.5 + T_KEEP + 1.0, 4.0, 1.0, choices=(20, 25, 30)),
                     (bx_, by_, zn1), (0, 0, -1), "zbody", (f"nut_plate{tg}", spn, f"nut_keeper{tg}"), nut_at=(bx_, by_, kz0),
                     large=True, nyloc=True)
            d.get(f"nut_keeper{tg}_bolt_{k_}").meta["locking"] = "nyloc"
        d.join(f"z_nut{tg}", f"nut_keeper{tg}", "captive: the flange sits between plate and keeper, 0.1 mm play, free to float sideways")
        how = (f"How the bed is lifted: the T8 brass nut z_nut{tg} rides lead screw leadscrew{tg}. Its 22 mm flange is under this "
               f"{T_NP:g} mm plate, which is bolted under the 2020 square's member {member} (two M5 from below into T-nuts), and its "
               f"10.2 mm barrel goes up through the plate's {NP_HOLE:.1f} mm hole. The carrier's weight rests on the flange, so when "
               f"the screw turns the nut climbs it and lifts the plate, the square, the deck and the bed. The M2.5 pin screw "
               f"nut_pin{tg} (through a 5 mm aluminium sleeve, fixed in the flange) sits in a radial slot in the plate: it stops the "
               f"nut turning with the screw while letting it float {NUT_FLOAT:g} mm sideways. The nut is captive: the laser-cut keeper "
               f"nut_keeper{tg}, bolted 0.1 mm under the flange on two M3 through-bolts and spacers, stops the plate lifting off it. "
               f"The three nut plates are one shape, as are the three keepers.")
        d.get(f"nut_plate{tg}").meta["description"] = "Laser-cut 6061 nut plate under the carrier's square. " + how
        d.get(f"z_nut{tg}").meta["description"] = f"T8 flanged brass nut, floating and captive under nut_plate{tg}. " + how
        d.get(f"nut_keeper{tg}").meta["description"] = (f"Keeper: holds z_nut{tg}'s flange up against nut_plate{tg} (0.1 mm play, free to float "
                                                       f"sideways) so the carrier cannot lift off the nut. " + how)
    d.bom_extra("NYLOC-M2.5 (nut pins, in place of the hex nuts drawn)", 3, 0.05)

    # ================= bed (v9): MIC-6 plate, 257 mm sheet, four sprung levelling studs ==========
    bed_own = BED * BED * T_BED * MATERIALS[CAST].density * 1e-9
    d.add("bed_plate", round_profile(bed_shape_(), 2.0, T_BED), material=CAST, body="zbody", mass_kg=bed_own + PAYLOAD_KG, process="sheet",
          meta={"finish": "bare", "note": "MIC-6 6.35 mm, laser cut at SendCutSend, faces as cast; four 90-degree countersinks for M4 "
                                          "(8.96 mm) from the top face"})
    mag = Stock(Pos(0, 0, T_MAG / 2) * Box(SHEET, SHEET, T_MAG), "BED-MAGNET-PEI257-BASE-STANDIN",
                "Magnetic base supplied with the 257 x 257 PEI sheet (stand-in: its thickness is not published; 1.5 mm, as two other "
                "sellers' kits state, and 3.7 g/cm3 assumed; adhesive back; the seller's 120 degC is for the plate)",
                SHEET * SHEET * T_MAG * 3.7e-6, material="rubber_gt2", cost_usd=0.0,
                ratings={"max_temp_c": 120.0, "max_temp_basis": "seller's 'maximum print bed temperature' for the sheet, unverified for the base"})
    place(d, "bed_magnet", mag, Location((0, BED_CY, Z_BED + T_BED)), body="zbody")
    place(d, "bed", print_sheet_pei257(), Location((0, BED_CY, Z_BED + T_BED + T_MAG)), body="zbody")
    d.join("bed_magnet", "bed_plate", "bond")
    d.join("bed", "bed_magnet", "magnet")
    place(d, "bed_heater", bed_heater_pad(PAD_X, PAD_Y, BED_W), Location((0, BED_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed_plate", "bond")
    place(d, "bed_tco", thermal_fuse(133.0, 109.0, 15.0), Location((-45.0, BED_CY + PAD_Y / 2 + 12.0, Z_BED - 2.0)), body="zbody")
    d.join("bed_tco", "bed_plate", "bond")
    for nm_, txt in (("bed_heater", "Silicone heater pad 190 x 180 mm, adhesive-backed, bonded to bed_plate's underside between the four studs (no fasteners)."),
                     ("bed_magnet", "Magnetic base sheet of the 257 mm PEI plate, adhesive-backed, bonded to bed_plate's top face over the studs' heads (no fasteners)."),
                     ("bed", "257 x 257 mm PEI spring-steel print sheet, held on bed_magnet by magnetism alone: lift it off to remove prints."),
                     ("bed_tco", "Thermal fuse, bonded to bed_plate's underside with high-temperature adhesive (thermal contact), in series with the heater."),
                     ("bed_plate", "MIC-6 bed plate, 265 x 265 x 6.35 mm: it floats 18.8 mm above the deck on four M4 studs (countersunk screws from "
                                   "its top face, each locked to it by a nut underneath), pushed up by four die springs against four thumb "
                                   "nuts under the deck; the heater pad is bonded under it, the magnetic base on top.")):
        d.get(nm_).meta["description"] = txt
    # each levelling point, top to bottom: M4 x 35 countersunk screw (fully threaded) from the plate's top face; M4 washer
    # and nut under the plate, thread-locked (the screw is now a stud fixed in the plate: it cannot turn with the thumb
    # nut); die spring; M4 washer on the deck (the spring's seat: it slides on the deck as the plate grows); deck; large M4
    # washer; DIN 466 thumb nut. The spring pushes the plate up against the thumb nut: turning the nut sets the height.
    for i, (x, y) in enumerate(BED_MOUNTS):
        p = f"bed_stud_{i}"
        wt, jam, spr, seat, dw, th = f"{p}_washer", f"{p}_nut", f"bed_spring_{i}", f"bed_spring_{i}_seat", f"bed_thumb_{i}_washer", f"bed_thumb_{i}"
        add_washer(d, wt, "M4", (x, y, Z_BED), (0, 0, -1), body="zbody")
        # the head is placed where it seats: CSK_SINK below the surface, its cone on the countersink's cone (the catalogue
        # draws the head at its actual diameter, 7.53, which a countersink cut to the theoretical 8.96 takes that far down)
        sc = add_screw(d, p, "M4", STUD_L, at=(x, y, Z_BED + T_BED - CSK_SINK), direction=(0, 0, -1), body="zbody",
                       clamps=("bed_plate", wt, "z_deck"), head="countersunk", locking="adhesive")
        sc.meta["fully_threaded"] = True          # buy DIN 7991 / ISO 10642 fully threaded: the lock nut sits 6 to 10 mm under the head
        d.join(wt, "bed_plate", "clamped by the stud's lock nut")
        add_nut(d, jam, "M4", at=(x, y, Z_BED - W4), direction=(0, 0, -1), body="zbody", screw=p, locking="adhesive")
        d.join(jam, wt, "clamp")
        place(d, spr, die_spring_dj8x20(SPRING_H), Location((x, y, Z_DECK1 + W4)), body="zbody")
        add_washer(d, seat, "M4", (x, y, Z_DECK1), (0, 0, 1), body="zbody")
        d.join(spr, jam, "spring seat: the spring's top bears on the stud's lock nut")
        d.join(spr, seat, "spring seat")
        d.join(seat, "z_deck", "sliding: the spring's seat washer lies on the deck, held by the spring's preload")
        add_washer(d, dw, "M4", (x, y, Z_SQT), (0, 0, -1), body="zbody", series="large")
        d.join(dw, "z_deck", "clamp: held against the deck's underside by the spring's preload (the located stud)" if i == 0 else
               "sliding free: held against the deck's underside by the spring's preload, slips as the plate grows")
        add_thumb_nut(d, th, "M4", (x, y, Z_SQT - W4L), (0, 0, -1), body="zbody", screw=p)
        d.join(th, dw, "clamp")
        hole = ("a fitted 4.3 mm hole (this stud locates the bed)" if i == 0 else "a 4.3 mm slot pointing at stud 0 (holds the bed from turning)"
                if i == 1 else "a 5.5 mm oversize hole (free)")
        desc = (f"Bed levelling point {i}: an M4 x {STUD_L:g} countersunk screw from the bed's top face (head 0.7 mm below it, under the "
                f"magnetic base) is locked to the plate by a washer and nut underneath, so it is a fixed stud. A die spring "
                f"(DJ-8X20YCS, {SPRING_K} N/mm, compressed {20 - SPRING_H:g} mm: {SPRING_K * (20 - SPRING_H):.0f} N) between that nut and the "
                f"deck pushes the bed up; the stud passes the deck through {hole} and a large washer and knurled thumb nut under "
                f"the deck hold it down. Turn the thumb nut to level: 0.7 mm per turn, +/-{LEVEL_RANGE:g} mm.")
        for nm_ in (p, jam, spr, th):
            d.get(nm_).meta["description"] = desc
    d.join("bed_plate", "z_deck", "four sprung levelling studs")
    # ================= Z drive: three lead-screw motors, each on its own laser-cut plate ======
    mounts = []
    rear_posts = [(-MP_POST_DY, LS_Y), (MP_POST_DY, LS_Y)]                           # top slot of the bottom back rail, under the motor
    # (tag, screw x, y, motor turn so its connector faces inboard, posts, rail part, base: tray (front) or the rail (rear))
    mounts.append(("", 0.0, LS_Y, -90.0, rear_posts, "frame_bot_back", False))
    for sx, tg in ((-1, "_fl"), (1, "_fr")):
        mounts.append((tg, sx * FS_X, FS_Y, 0.0 if sx < 0 else 180.0, [(sx * FS_X, FS_Y - MP_POST_DY), (sx * FS_X, FS_Y + MP_POST_DY)],
                       f"frame_bot_{'left' if sx < 0 else 'right'}", True))
    mount_parts = {}
    for tg, x0, y0, turn, posts, rail, on_tray in mounts:
        mount_parts[tg] = build_z_mount(d, tg, x0, y0, turn, posts, rail, on_tray)
    def on_rail_of(nm):
        nv, base = guide_parts[nm]
        k, want = (0, base[0] + 8.0 * nv[0]) if abs(nv[0]) > 0.5 else (1, base[1] + 8.0 * nv[1])
        return lambda f: abs((f.center().X, f.center().Y)[k] - want) < 1e-6      # the block's face on the rail's top
    names = [g[0] for g in GUIDES]
    zs = {"tags": ("", "_fl", "_fr"), "zcars": [f"z_carriage_{n}" for n in names],
          "rails": {f"z_carriage_{n}": f"z_rail_{n}" for n in names},
          "carrier": ["sq_left", "sq_right", "sq_front", "sq_rear", "z_deck"] + [f"carriage_plate_{n}" for n in names]
                     + [f"sq_bracket_{e}{s}" for e in ("f", "r") for s in ("l", "r")],
          "nut_plates": ["nut_plate", "nut_plate_fl", "nut_plate_fr"],
          "on_rail": {f"z_carriage_{n}": on_rail_of(n) for n in names}}
    return d, zs, bed_own, mounts, mount_parts


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
    d, zs, bed_own, mounts, mount_parts = build_frame_z()
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
    d.get("hotend").meta["description"] = "E3D Revo hotend, held in the Roto's hotend seat by the Roto's own clamp (no separate fasteners)."
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
    im = im_loc * im
    im -= bx(XI_X - 40.0, XI_X - 10.0, yb_f - 40.0, yb_r - MT - R_B32 - 0.5, Z_BEAM - 20.0, LUG_Z0)     # v8.2: lug starts at z 408
    d.add("x_idler_mount", round_profile(im, 1.0, MT), material=AL_BEND, body="ybody", process="sheet", meta={"finish": "bare"})
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
    xa = xa_loc * xa
    xa -= bx(XA_FIN - 10.0, XA_FIN + 10.0, yb_f - 40.0, yb_r - MT - R_B32 - 0.5, Z_BEAM - 20.0, LUG_Z0)  # v8.2: fin starts at z 408
    d.add("x_tension_anchor", round_profile(xa, 1.0, MT), material=AL_BEND, body="ybody", process="sheet", meta={"finish": "bare"})
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
        add_washer(d, f"y_idler{tag}_spacer_b", "M5", (sg * (xf + MT_YI + W5), YI_Y, Z_YC), (sg, 0, 0), screw=f"y_idler{tag}_bolt")
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
    return finish_build(d, zs, bed_own, mounts, mount_parts)


def finish_build(d, zs, bed_own, mounts, mount_parts) -> Design:
    # ================= electronics bay: tray across the bottom rails =============
    tray = Pos(0, (TRAY_Y0 + TRAY_Y1) / 2, 20 + T_TRAY / 2) * Box(FX, TRAY_Y1 - TRAY_Y0, T_TRAY)
    grp = ["electronics_tray"]
    psu = place(d, "psu", psu_lrs(PSU_MODEL), Location((-28.0, -30.0, Z_TRAY), (0, 0, -90)))
    # v8.2: BTT Octopus V1.1 (eight drivers: X, Y, Y1, three Z, E, one spare) beside the supply, its motor connectors along
    # the right-hand edge; the Pi Zero 2 W in front of it, where the SKR Mini sat
    board = place(d, "control_board", octopus_v11(), Location((BOARD_XY[0], BOARD_XY[1], Z_TRAY + 6.0), (0, 0, -90)))
    host = place(d, "host", raspberry_pi_zero2w(), Location((HOST_XY[0], HOST_XY[1], Z_TRAY + 4.0), (0, 0, 0)))
    pcbs = [(board, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2, 3)), (host, "mount_holes_m2.5", "M2.5", 12, 4.0, (0, 3))]
    tray_hole = {"M3": clearance_hole("M3"), "M2.5": 3.2}
    RELAY_XY = (-115.0, -36.0)
    relay = place(d, "psu_relay", relay_btt_v12(), Location((*RELAY_XY, Z_TRAY + 6.0), (0, 0, 90)))
    pcbs.append((relay, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2)))
    # v9: the side uprights and their corner brackets stand on the bottom side rails where the tray lay: two notches; the
    # tray is held by the four front motor posts' bolts and by these two at the back
    tray_bolts = [(sx * RAIL_X, 72.0) for sx in (-1, 1)]
    for sx in (-1, 1):
        tray -= bx(sx * (WALL_X - 2.0), sx * (FX / 2 + 1.0), UP_S_Y - 32.0, UP_S_Y + 32.0, 19.0, Z_TRAY + 1.0)
    for tg, x0, y0, turn, posts, rail, on_tray in mounts:
        if on_tray:
            for x, y in posts:
                tray -= zc(x, y, 20.0, Z_TRAY, clearance_hole("M5") / 2)     # the front motor posts' bolts pass to the rail
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
              ("mains_cover_psu", (-89.5, 33.5, 60.0, 77.0, Z_TRAY, PSU_COVER_TOP), [(-93.5, 64.0), (37.5, 64.0)])]
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
    for tg, x0, y0, turn, posts, rail, on_tray in mounts:
        # motor, its screw and plate go in as one unit onto the two spacers; the post bolts follow
        d.subassemblies[f"z_drive{tg or '_rear'}"] = [n for n in mount_parts[tg] if "_bolt_" not in n and "_spacer_" not in n and n in have]
    # v9: the bed is a bench unit: plate with its four countersunk studs, their washers and lock nuts, heater and cut-off;
    # the springs go over the studs, the unit goes down through the deck's holes, the thumb nuts go on from below, and the
    # magnetic base and sheet go on last
    bed_unit = ["bed_plate", "bed_heater", "bed_tco"]
    for i in range(len(BED_MOUNTS)):
        bed_unit += [f"bed_stud_{i}{x}" for x in ("", "_washer", "_nut")] + [f"bed_spring_{i}", f"bed_spring_{i}_seat"]
    d.subassemblies["bed_unit"] = [n for n in bed_unit if n in have]
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
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 1, 4.0)
    d.bom_extra("GT2-BELT-12MM-OPEN-1M", 2, 5.0)
    d.bom_extra("THREADLOCKER-MEDIUM (Loctite 243 class: Z motor screws and posts, pulley set screws, jack screws, post jam nuts)", 1, 6.0)
    d.bom_extra("DRIVER-BTT-TMC2209 (Octopus: X, Y, Y1, Z, Z1, Z2, E)", 7, 6.0)
    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY_F, TY), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    # v8.2: three motors, each turning its own screw directly (the screw is its shaft); the firmware levels them with
    # Z_TILT_ADJUST ([z_tilt] in build_electrical)
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_DN, PRINT_Z), overtravel=(0.0, Z_UP),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": [f"z_motor{t}" for t in zs["tags"]], "kind": "leadscrew",
                                 "screw": [f"leadscrew{t}" for t in zs["tags"]],
                                 "nut": [f"z_nut{t}" for t in zs["tags"]], "sync": "independent", "nut_seating": "captive"}))
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
        Adjustment("the knurled thumb nut under the deck at each of the four bed studs (0.7 mm per turn)", "bed_level", range_mm=LEVEL_RANGE,
                   mover="DIN 466 M4 thumb nut", lock="the die spring's preload on the nut's thread (30 to 61 N over the range)"),
        Adjustment("x switch: its screws run in slots in the Y plate's land", "endstop", range_mm=ES_SLOT, joint="x"),
        Adjustment("y switch: its mount slides along the rail on two T-nuts", "endstop", range_mm=5.0, joint="y"),
        Adjustment("y rails on sliding T-nuts", "rail_align", range_mm=1.6, joint="y",
                   note="an M3 in the 6.2 mm slot slides +/-1.6 mm: left rail to a straight edge, right rail tightened while the gantry runs"),
        Adjustment("z rails on sliding T-nuts", "rail_align", range_mm=1.6, joint="z",
                   note="rear rail to a square; left and right rails tightened while the carrier is run up and down; what is left "
                        "goes into the carriage plates' webs"),
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
    # the bed's four mounts as the FEA meshes them: stud, washer and lock nut under the plate, large washer and thumb nut
    # under the deck. The springs are left out: while they are preloaded the bed is held by the studs against the thumb
    # nuts (docs/PRINTER_V9.md works the preload margin)
    posts = [f"bed_stud_{i}{sfx}" for i in range(len(BED_MOUNTS)) for sfx in ("", "_washer", "_nut")] \
        + [f"bed_thumb_{i}{sfx}" for i in range(len(BED_MOUNTS)) for sfx in ("", "_washer")]
    zcars, on_rail, carrier, nplates = zs["zcars"], zs["on_rail"], zs["carrier"], zs["nut_plates"]
    bed_stack = ["bed_plate", "bed_magnet", "bed"]
    d.printer["bed_support"] = {"parts": [*bed_stack, *posts, *carrier, *zcars, *nplates]}
    on_nut = lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 100
    d.assemblycases.append(AssemblyCase(
        "payload_x3_on_bed", [*bed_stack, *posts, *carrier, *zcars, *nplates],
        fixed=[(c, on_rail[c]) for c in zcars] + [(nb, on_nut) for nb in nplates],
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
    # one nut plate (the three are one shape) under three times the whole bed's weight, held at its two M5 holes
    tg, ncx, ncy, nang, _ = NUTS[2]
    fb = [rxy(u, -NUT_OUT - 10.0, ncx, ncy, nang) for u in (-NP_BOLT_U, NP_BOLT_U)]
    d.loadcases.append(LoadCase("nut_thrust", f"nut_plate{tg}",
                                fixed=lambda f: any(hole_at(x, y, clearance_hole("M5") / 2)(f) for x, y in fb),
                                loaded=hole_at(ncx, ncy, NP_HOLE / 2), force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.05))
    # one carriage plate between its block and the square (the three are one shape), as a beam test of its web: 5 N on the
    # block square to the wall, the square's member held, the block FREE to turn (the harness cannot hold a face against
    # turning only): a cantilever, whose deflection at the block's centre beam theory gives as
    # F (L^3 / 3 + L^2 a + L a^2) / (E I), a = 23.7 mm from the web's end to the block's centre: 0.418 mm. On its rail the
    # block cannot turn and the same web is 12 E I / L^3 = K_FLEX. A requirement compares the two.
    d.assemblycases.append(AssemblyCase(
        "carriage_plate_web", ["carriage_plate_right", "sq_right", "z_carriage_right"],
        fixed=[("sq_right", lambda f: abs(f.center().X - (SQ_X - 20.0)) < 1e-6)],
        loaded=("z_carriage_right", on_rail["z_carriage_right"]), force=(WEB_TEST_N, 0.0, 0.0),
        probe=(WALL_X - 8.0, UP_S_Y, ZC), max_deflection=1.0, min_fos=3.0))
    d.loadcases.append(LoadCase("x_belt_pull", "x_belt_bracket", fixed=lambda f: abs(f.center().Y - (YB0 + R_TPF)) < 1e-6,
                                loaded=lambda f: abs(f.center().Z - (Z_XL + 0.7)) < 1e-6 and f.area > 100,
                                force=(60.0, 0.0, 0.0), min_fos=3.0, max_deflection=0.1))
    # ================= heat: bed 60 K above the frame =============================
    # how the four studs hold the growing plate. As designed: stud 0 is located in its fitted hole, the other three slip
    # under their thumb-nut washers (declared "sliding free": normal load only). "stuck": the bound where friction never
    # lets go at any of the four (it does: 0.2 to 0.6 x 41 N against several hundred newtons; the doc has the sums);
    # reported, not limited. Carrier and deck 15 K warm under the heater (assumed).
    warm = {c: 15.0 for c in carrier}
    stuck = [(f"bed_thumb_{i}_washer", "z_deck") for i in range(1, len(BED_MOUNTS))]
    for nm, stick, lim in (("bed_heated_60K", (), 0.1), ("bed_heated_60K_studs_stuck", stuck, None)):
        d.thermalcases.append(ThermalCase(
            nm, ["bed_plate", "bed_magnet", "bed", *posts, *carrier, *zcars, *nplates],
            fixed=[(c, on_rail[c]) for c in zcars] + [(nb, on_nut) for nb in nplates],
            temps={**warm, "bed_magnet": 60.0, "bed_plate": 60.0, "bed": 60.0, **{c: 30.0 for c in posts}, "*": 0.0},
            probes={"nozzle": (UP_R_X, Y_FACE - 8.0, ZC), "bed": (0.0, YB0 + HOT_OFF, Z_SURF - T_SHEET)},
            gaps={"nozzle gap": ("nozzle", "bed", "z", lim)}, flatness=("bed_plate", "z", lim), stick=stick))
    # the bed plate alone, held at its four countersinks, its mass the plate's plus the 1 kg payload spread over it (close to
    # plate + magnetic base + sheet + heater + a 0.3 kg print): its first bending mode. Fixed faces are ideally rigid, so
    # the real figure is lower; the brief sets no limit, 100 Hz keeps it above the gantry's resonances (60 to 80 Hz)
    d.modalcases.append(ModalCase("bed_plate_on_four_studs", "bed_plate", fixed=lambda f: f.geom_type.name == "CONE", min_frequency_hz=100.0))
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
    d.requirements.append(Requirement(f"print volume: travel >= {PRINT_X:g} x {PRINT_Y:g} x {PRINT_Z:g} mm (v8.2: 180 x 180 x 180)", travel))

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
    d.requirements.append(Requirement("all three belts (X, Y, Y left) routed: constant length, clear of parts", lambda dd, m: (
        all(b in m["motion"].get("belts", {}) and m["motion"]["belts"][b]["clear_of_parts"]
            and m["motion"]["belts"][b]["length_change_over_travel_mm"] <= 0.3 for b in ("x_belt", "y_belt", "y_belt_l")),
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
        max(t := [dd.get(n).shape.bounding_box().max.Z for n in ["z_rail_left", "z_rail_right", "z_rail_rear"] + [f"leadscrew{t_}" for t_ in zs["tags"]]]) < FZ - 10,
        f"rail tops {t[0]:.1f}, screw tops {' / '.join(f'{v:.1f}' for v in t[3:])} vs extrusion underside {FZ - 10:.1f}")))
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(mn).sku.startswith("NEMA17") and dd.get(mn).meta["catalog"] for n in "xyz" for mn in motors_of(dd, n)),
        str({n: [dd.get(mn).sku for mn in motors_of(dd, n)] for n in "xyz"}))))
    def z_direct(dd):
        drv = jr(dd, "z").drive
        ms = motors_of(dd, "z")
        belts_on_z = [b.name for b in dd.belts if any(n[0] == "pulley" and n[1].startswith("z_") for n in b.path)]
        ok = (drv.get("sync") == "independent" and len(ms) == 3 and ms == [f"z_motor{t}" for t in zs["tags"]] and not belts_on_z
              and all(dd.get(m).ratings.get("integral_leadscrew") for m in ms) and "coupler" not in drv)
        return ok, f"Z motors {ms}, sync {drv.get('sync')}, belts on Z: {belts_on_z or 'none'}, couplers: {drv.get('coupler', 'none')}"
    d.requirements.append(Requirement("Z: three motors, each screw is its own motor's shaft (no belt, no coupler)", z_direct))
    d.requirements.append(Requirement("Z: the firmware levels the three screws (Klipper [z_tilt] with three screw positions and three points)", lambda dd: (
        len((zt := dd.electrical.firmware.get("z_tilt") or {}).get("z_positions", [])) == 3 and len(zt.get("points", [])) == 3,
        f"z_positions {zt.get('z_positions')}, points {zt.get('points')}")))
    d.requirements.append(Requirement("Z lead screws self-locking (efficiency < 0.5)", lambda dd: (
        all(dd.get(f"leadscrew{t}").ratings["efficiency"] < 0.5 for t in zs["tags"]), f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    d.requirements.append(Requirement("reported, not a limit: part count", lambda dd: (True, f"{len(dd.components)} parts")))
    # ---- v9: the owner's sketch, as checks -------------------------------------------------------------------------------
    def three_rails(dd, m):
        pr = m["tolerance"]["paired_rails"]["z"]
        ic, aa = pr["in_plane_constraints"], pr.get("after_alignment", {})
        ok = len(pr["rails"]) == 3 and len(pr["floats"]) == 3 and ic["redundant"] == 0 and aa.get("within_allowed_side_load")
        return ok, (f"{len(pr['rails'])} rails, {len(pr['floats'])} floating mounts at {K_FLEX:.0f} N/mm, stiff directions {ic['stiff_directions_held']} "
                    f"of 3 needed; as built the rails are up to {pr['parallelism_error_over_travel_mm_99']} mm out of parallel over the travel "
                    f"(aligned at assembly); with {aa.get('residual_between_rails_mm')} mm left a block carries {aa.get('side_load_on_blocks_n_99')} N "
                    f"sideways (allowed {pr['side_load_allowed_n']} N), webs bend {max(aa.get('float_used_mm_99', {0: 0}).values())} mm of {FLEX_RANGE}")
    d.requirements.append(Requirement("v9: Z guided on three rails without over-constraint: three stiff directions, the rest on flexures", three_rails))

    def web_stiffness(dd, m):
        ac = m["fea"]["carriage_plate_web"]
        hi, lo = ac["deflection_mm"], ac["deflection_screwed_joints_mm"]
        ok = abs(hi / WEB_TEST_MM - 1.0) <= 0.15 and lo <= 1.6 * WEB_TEST_MM
        return ok, (f"{WEB_TEST_N:g} N on a block free to turn: FEA {hi:.3f} mm bonded, {lo:.3f} mm with joints held round their screws; beam "
                    f"theory {WEB_TEST_MM:.3f} mm. The same web with the block held square by its rail: {K_FLEX:.0f} N/mm (declared), "
                    f"{K_FLEX * WEB_TEST_MM / lo:.0f} N/mm on the screwed bound")
    d.requirements.append(Requirement("v9: the carriage plates' web is the flexure the tolerance model assumes (FEA within 15 % of beam theory)",
                                      web_stiffness))

    def carrier_square(dd):
        vol = lambda n: dd.get(n).shape.volume
        mem = [dd.get(f"sq_{n}") for n in ("left", "right", "front", "rear")]
        cp = [vol(f"carriage_plate_{g[0]}") for g in GUIDES]
        npv = [vol(f"nut_plate{t[0]}") for t in NUTS]
        mpv = [vol(f"z_motor_plate{t[0]}") for t in NUTS]
        kv = [vol(f"nut_keeper{t[0]}") for t in NUTS]
        same = lambda v: max(v) - min(v) < 1e-3 * max(v)
        dk = dd.get("z_deck").shape.bounding_box()
        ok = (all(c.sku.startswith("EXTRUSION-2020") or "2020" in c.sku for c in mem) and all(c.body == "zbody" for c in mem)
              and same(cp) and same(npv) and same(mpv) and same(kv) and abs(dk.size.Z - 3.175) < 1e-6)
        return ok, (f"four 2020 members {2 * SQ_X:.1f} x {SQ_Y1 - SQ_Y0:.1f} mm outside; deck {dk.size.X:.1f} x {dk.size.Y:.1f} x {dk.size.Z:.3f} mm; "
                    f"three carriage plates one shape: {same(cp)}; three nut plates one shape: {same(npv)}; three keepers: {same(kv)}; "
                    f"three motor plates: {same(mpv)}")
    d.requirements.append(Requirement("v9: carrier is a closed 2020 rectangle with a 1/8 in deck; six brackets in two shapes", carrier_square))

    def spring_preload(dd):
        on_bed = ["bed_plate", "bed_magnet", "bed", "bed_heater", "bed_tco"] + [f"bed_stud_{i}{s}" for i in range(4) for s in ("", "_washer", "_nut")]
        m_bed = sum(dd.get(n).mass() for n in on_bed) - PAYLOAD_KG
        az = A_Z / 1000.0
        share = m_bed * (9.81 + az) / 4 + PAYLOAD_KG * (9.81 + az)       # the bed's own weight in quarters, the whole payload on one point
        lo, nom, hi = (SPRING_K * (20.0 - SPRING_H + s * LEVEL_RANGE) for s in (-1, 0, 1))
        f_hz = math.sqrt(4 * SPRING_K * 1000.0 / (m_bed + PAYLOAD_KG)) / (2 * math.pi)
        a_lift = (4 * lo - (m_bed + PAYLOAD_KG) * 9.81) / (m_bed + PAYLOAD_KG)
        return lo >= 2.0 * share, (f"bed without payload {m_bed:.2f} kg; worst point carries {share:.1f} N (a quarter of the bed, all of the {PAYLOAD_KG:g} kg "
                                   f"payload, Z at {A_Z:g} mm/s^2); spring preload {lo:.1f} / {nom:.1f} / {hi:.1f} N over the +/-{LEVEL_RANGE:g} mm levelling "
                                   f"range: factor {lo / share:.2f} at the weak end. The bed leaves its thumb nuts only above {a_lift:.1f} m/s^2 of upward "
                                   f"carrier acceleration (Z runs {az:g}); on the springs alone it would bounce at {f_hz:.1f} Hz")
    d.requirements.append(Requirement("v9: every bed spring's preload is at least twice the load on its point over the levelling range (the bed stays "
                                      "on its thumb nuts)", spring_preload))

    def plate_growth(dd):
        a, dt = 23.6e-6, 60.0
        (x0, y0) = BED_MOUNTS[0]
        need = {i: math.hypot(x - x0, y - y0) * a * dt for i, (x, y) in enumerate(BED_MOUNTS) if i}
        free = (DECK_FREE - 4.0) / 2
        ok = need[1] <= 1.0 - 0.2 and max(need[2], need[3]) <= free - 0.2
        return ok, (f"plate {dt:g} K warmer than the deck: studs move {need[1]:.2f} (slot, +/-1.0), {need[2]:.2f} and {need[3]:.2f} mm (oversize holes, "
                    f"{free:.2f} mm radial) from the fitted stud; 0.2 mm kept for hole position")
    d.requirements.append(Requirement("v9: the heated plate's growth fits the deck's slot and oversize holes (no stud is bent)", plate_growth))
    d.requirements.append(Requirement("reported: bed and print area", lambda dd, m: (
        True, f"sheet {SHEET:g} x {SHEET:g}, plate {BED:g} x {BED:g} x {T_BED:g}; nozzle over the sheet {PRINT_X:g} x {PRINT_Y:g} mm, probed "
              f"{PRINT_X:g} x {PRINT_Y - m['subsystems']['homing']['z'].get('unprobed_strip_mm', {}).get('y_low', float('nan')):g} mm")))
    d.requirements.append(Requirement(f"target: direct drive, at most {MAX_TOOLHEAD_KG:g} kg moving in X", lambda dd: (
        dd.get("extruder").body == "xbody" and (m := sum(c.mass() for c in dd.components if c.body == "xbody")) <= MAX_TOOLHEAD_KG,
        f"{m:.3f} kg on the X guide block, block included")))
    d.requirements.append(Requirement(f"target: both Y belts within 1 mm of plane in >= {MIN_BELT_IN_PLANE:.0%} of builds", lambda dd, m: (
        all(m["tolerance"]["belts"][b]["p_within_1mm"] >= MIN_BELT_IN_PLANE for b in ("y_belt", "y_belt_l")),
        str({b: m["tolerance"]["belts"][b]["p_within_1mm"] for b in ("y_belt", "y_belt_l")}))))
    d.requirements.append(Requirement("the bed probe switches before the nozzle touches for every unit, and over-travel ends short of its face", lambda dd, m: (
        (pz := m["subsystems"]["homing"]["z"])["z_offset_range_mm"][0] > 0.3 and Z_UP < PRB_H,
        f"nozzle {pz['z_offset_range_mm'][0]:.2f} .. {pz['z_offset_range_mm'][1]:.2f} mm above the bed when the probe switches")))
    STANDINS = ["bed_magnet"]
    d.requirements.append(Requirement("target: no purchased part is a stand-in where the catalogue has a real one", lambda dd: (
        sorted(px := [c.name for c in dd.components if c.cots and not c.meta.get("catalog")]) == STANDINS,
        f"hand-made purchased parts: {px} (the print sheet's magnetic base: its thickness is not published)")))
    d.requirements.append(Requirement("no printed part in a load path (owner's guideline): printed parts are only the probe holder, duct and covers", lambda dd: (
        sorted(pp := [c.name for c in dd.components if c.material in ("abs", "petg", "pla") and not c.cots]) ==
        sorted(["probe_mount", "part_duct", "mains_cover_relay", "mains_cover_psu", "mains_cover_inlet"]), f"printed: {pp}")))
    d.requirements.append(Requirement("bed sag under 1 kg at the worst print corner <= 0.02 mm (screw-only bound)", lambda dd, m: (
        (pw := m["fea"]["bed_support"]["print_weight"])["judged_mm"] <= 0.02 + 1e-9, f"{pw['judged_mm']:.4f} mm at {pw.get('worst_point')}")))
    def nuts_held(dd, m):
        bs = m["fea"]["bed_support"]
        lv = bs["nut_seating_and_lead_error"]["levels"][2]
        kind = bs["nut_seating_and_lead_error"]["nut_seating"]["kind"]
        wc = lv["worst_case"]
        ok = (not lv["a_nut_unseats"]) or (kind == "captive" and wc["print_weight_sag_on_supports_mm"] <= 0.02 + 1e-9)
        return ok, (f"nuts {kind}; height error {lv['height_error_mm']} mm; least nut load margin {min(lv['nut_load_margin_n'].values()):.1f} N; "
                    f"worst case: {wc['nuts_not_seated'] or 'all seated'} off their weight-bearing flank, bed level change "
                    f"{wc['bed_level_change_across_print_area_mm']} mm, 1 kg sag on the supports {wc['print_weight_sag_on_supports_mm']} mm")
    d.requirements.append(Requirement("every lead-screw nut stays held with two screws at opposite lead limits (LSC-015): seated, or "
                                      "captive with the bed's 1 kg sag on its supports <= 0.02 mm", nuts_held))
