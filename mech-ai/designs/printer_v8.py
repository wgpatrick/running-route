"""printer_v7: printer_v6 corrected against the vendor data sheets that arrived after v6 was designed.

STATED TARGET (unchanged from v6; docs/PRINTER_V7.md says which lines are met):
  A 180 x 180 x 180 mm open-frame demonstration printer whose every purchased part is off the shelf and every
  fabricated part is printed, laser-cut or a single-set-up plate.
    - parts cost + fabrication estimate <= $900
    - <= 320 parts
    - assembly estimate <= 65 min
    - direct-drive toolhead, <= 0.40 kg moving mass in X
    - both Y belts within 1 mm of plane in >= 98 % of builds
    - a bed probe that works across the whole print area
    - no stand-in ("proxy" / uncatalogued) purchased part

Same machine as v6 (cartesian, E3D Roto + Revo on the X guide block, X rail on the beam's rear face, bed on two Z
rails, 2020 frame, 24 V, SKR Mini E3 V3 + Pi Zero 2 W). What changed, each tied to a vendor document:

1. Endstops (OMRON D2F sheet: operating position 6.8 +/-1.5 mm, not 9.0). Both lever switches moved 2.3 mm towards
   their strikers: the nominal operating position is at the end of the working range and X and Y have 1.5 mm of
   declared over-travel at both ends, so the latest unit still switches (0.1 mm in hand) and the lever stops 0.15 mm
   short of the switch case. Switches kept on X and Y (no sensorless homing: see the doc); buy the D2F-01L type.
2. Coupler (MH2025-5-8 vendor CAD: 8 mm bore 8.6 mm deep, 7.5 mm clamped). The lead screw sits 8.0 mm in its bore;
   the coupler sits 3 mm lower on the motor shaft (11.5 mm in the 5 mm bore, 12.05 allowed), so the screw top is
   2.5 mm under the top back rail.
3. Y belts 9 mm (v6: 12 mm) and the Y pulleys turned hub-outboard: 28.4 N on each Y motor shaft 11.75 mm from the
   face against 35.7 N allowed there (v6: 37.4 N at 16.25 mm against 25.8 N). 9 mm is a Gates stock width, 12 mm is not.
4. Z over-travel declared: 1.65 mm past the nominal nozzle plane (probe offset, mesh, a bed built low);
   design.printer["print_area"] = 180 x 180.
5. Bed probe: OMRON E2E-X10ME1 (catalogue part: M18, unshielded, about 3.0 mm on aluminium, NPN three-wire) in a
   printed arm, clamped by its own nuts, its metal-free zone kept. Bed limited to 85 degC (the sensor's rating).
6. Relay: the neutral runs through the relay's N terminal.
7. Part fan: the catalogue's 24 V 30 mm fan on the board's 24 V fan output (the Sunon sheet in hand is the 12 V
   member of the family; the catalogue has no 24 -> 12 V regulator). The part-cooling duct is drawn.
8. Mains inlet: SCHURTER DD11 pattern on the inlet panel.
9. X rail datum (two laser-cut stops under the Y plates), two M5 per side under each Y plate, bed heater 180 W on
   the board's own output (no MOSFET module).

Layout (X = width, Y = depth with the front at -Y, Z = up) is v4's; see designs/printer_v4.py for the history.

Not modelled (flagged): the Roto's solid is E3D's reference CAD envelope in solid aluminium; tapped holes, T-nuts,
the BAT85 diode and the Revo's spring clip are BOM lines or notes, not geometry; payload is extra mass on the bed;
no airflow model for the duct.
"""
import math

from build123d import Box, Cylinder, Location, Plane, Pos, RectangleRounded, RegularPolygon, Rot, extrude

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import MATERIALS, Belt, ThermalCase
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       iec_inlet_c14, inductive_probe_template, mosfet_module, psu_lrs,
                                       raspberry_pi_zero2w, relay_btt_v12, skr_mini_e3_v3, thermal_fuse)
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, bearing, clearance_hole,
                            endstop_switch, extrusion_2020, fan, gt2_idler, gt2_pulley,
                            leadscrew_nut_t8, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place,
                            shaft_coupler)
from mechloop.parts.hardware import bed_column_silicone, spacer_round
from mechloop.parts.probes import probe_omron_e2e
from mechloop.parts.toolhead import extruder_roto, hotend_revo

# ---- brief ------------------------------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 180.0, 180.0, 180.0
PAYLOAD_KG = 1.0
V_XY, A_XY = 250.0, 4000.0
V_Z, A_Z = 12.0, 200.0
MARGIN = 3.0
ENVELOPE = (420.0, 420.0, 480.0)
# stated targets (see the docstring); each is a Requirement at the end of build()
MAX_PARTS, MAX_TOOLHEAD_KG, MAX_COST_USD, MIN_BELT_IN_PLANE = 320, 0.40, 900.0, 0.98

# ---- electrical choices -----------------------------------------------------------
BED_W = 180.0          # v7: 180 W pad (v6: 200 W). 7.5 A, inside the board's own bed output (8 A allowed), so no MOSFET module
BED_MAX_C = 85.0       # v7: highest bed temperature the firmware is given. The probe (OMRON E2E-X10ME1) rides 1.7 mm above the
                       # bed and is rated for 85 degC ambient; v6 allowed 100 degC over a 70 degC stand-in
PSU_MODEL = "LRS-350-24"
BED_AWG, BED_INS = 16, "silicone"
# A rms at the driver. Extruder: E3D allows 0.318 .. 0.424 A rms for the Roto's motor
RUN_CURRENT = {"x": 0.28, "y": 1.20, "z": 1.00, "extruder": 0.40}
FUSE_A = 8.0
T_TRAY = 3.0
TRAY_Y0, TRAY_Y1 = -138.0, 85.0    # v8: 23 mm deeper at the back (the supply now lies along Y)
Z_TRAY = 20.0 + T_TRAY

# ---- materials for printed parts --------------------------------------------------
HOT = "abs"      # on the toolhead, near the bed, on a motor, or under a steady load: ABS (ASA is not in MATERIALS)
COOL = "petg"    # on the cold frame

# ---- frame ------------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 394.0      # v8: 50 mm taller than v7 (344): room under the bed for the 60 mm flexure posts and the Z belt plane
RAIL_X = FX / 2 - 10                  # side extrusions / Y rails
TX, TY = PRINT_X / 2, PRINT_Y / 2     # +/- travel

# ---- Z axis -----------------------------------------------------------------------
BED = 220.0
T_BED = 8.0            # v8: 8 mm cast plate (v7: 6) on four posts
T_MAG = 1.0            # magnetic sheet bonded to the plate (purchased stand-in, see build())
T_SHEET = 0.5          # spring-steel print sheet (purchased stand-in): the print surface and the probe's target
UP_X = 90.0            # Z upright / rail centre, +/- X
UP_Y = FY / 2 - 10     # uprights stand between the bottom and top back rails
Y_FACE = UP_Y - 10     # front face of the uprights = rail base
Y_CAR = Y_FACE - 13    # carriage top face = back plate rear face
T_BP = 5.0             # back plate: 5 mm sheet (M3x8 through it leaves 3 mm in the blocks' 3.5 mm threads)
Y_PF = Y_CAR - T_BP    # back plate front face
LS_Y = UP_Y + 10       # lead screw / motor axis Y
MOTOR_L = 40           # v8: 40 mm motor on Z (v7: 34): three screws and a heavier bed
T_MM = 5.0             # printed drive mount: slab thickness (M3x8 leaves 3 mm in the motor's 4.5 mm threads)
BED_Y1 = Y_PF - 9.0    # v7: the bed ends 9 mm in front of the back plate (v6: 6): the part fan, now a duct depth further back,
                       # stays 2.7 mm clear of the Z uprights at the rear end of the Y over-travel
BED_Y0 = BED_Y1 - BED
BED_CY = (BED_Y0 + BED_Y1) / 2
ARM_X = 65.0           # 2020 arms: inboard of the uprights so their end screws can be driven from behind
ARM_L = 220.0          # arms run from the back plate to the front plate
# v8 bed mount: the plate stands on four M5 x 80 screws used as flexure posts (60 mm free between jam nuts): stiff along
# their axis (the bed's weight), soft sideways (the hot plate grows 0.27 mm away from its tie), and their nuts are the
# levelling adjustment at assembly. A sheet tie at the rear centre locates the plate in X, Y and yaw.
POST_NUT = 4.7         # ISO 4032 M5 nut
POST_FREE = 60.0       # free length of each post between the jam nut under the plate and the jam nut on the arm
H_COL = POST_FREE + 2 * POST_NUT      # bed underside above the arms
BED_MOUNTS = [(-ARM_X, BED_Y1 - 18.0), (ARM_X, BED_Y1 - 18.0), (-ARM_X, BED_Y1 - 187.0), (ARM_X, BED_Y1 - 187.0)]
POST_CB = 6.0          # counterbore for the M5 heads in the 8 mm plate: heads 1 mm under the magnetic sheet, 2 mm of plate under each
TIE_CB = 4.0           # same for the tie's M3 heads
TIE_Y = BED_Y1 - 30.0  # bed-side screws of the tie
TIE_T = 1.0            # tie: 1 mm steel sheet, bent once
T_FP = 3.0             # front plate: 3 mm steel sheet across the arms' front ends; carries the two front nut blocks
FS_X = FX / 2 - 10     # front lead screws stand over the bottom side rails (x = +/-160)
FS_OFF = 20.0          # ... their axis this far in front of the front plate
NUT_PIN = (0.0, 8.0)   # the one flange hole of the T8 nut that carries the anti-rotation pin
NUT_FLOAT = 2.4        # radial room around the nut barrel and along the pin slot (v7: 1.5; the front screws stand on printed pedestals)
Z_DN = 3.0             # mechanical Z travel below the home position (bed at the bottom)
Z_UP = 1.65            # v7: declared over-travel of the Z joint past the nominal nozzle plane (probe offset, mesh, a bed built low)
Z_SPACING = 59.0       # two blocks per rail, centre to centre
Z_RAIL_L = 300.0

# ---- gantry -----------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13          # underside of the Y plates
T_YP = 3.0                     # Y plates: 3 mm laser-cut steel sheet, like the motor and idler mounts
Z_BEAM = Z_PLATE - 10.0        # v6: the beam hangs UNDER the Y plates, between the Y guide blocks. Its centre line = X rail
                               # centre line = X guide block centre (rail on the beam's rear face)
PR = 20 * 2.0 / math.pi / 2    # pitch radius of the 20T pulleys / idlers
BWX, BWY = 9.0, 9.0           # GT2 belt widths: v7 9 mm on all three (Gates stock width; 12 mm is not, and overloads the Y motor shafts)
P_BC = lambda w: 7.0 + (w + 1) / 2      # gt2_pulley belt centre above its hub bottom
I_H = lambda w: w + 2.5                 # gt2_idler height
MT_Y = 3.0                     # motor / idler mounts: 3 mm steel sheet
MT = MT_Y
# toolhead: everything is placed from the guide block. R_* are distances behind the beam centre line (YB0).
R_TPF = 10.0 + 13.0            # tool plate front face = guide block mounting face
T_TP = 8.0                     # tool plate: 8 mm plate, one set-up (counterbores from the rear)
R_TPR = R_TPF + T_TP           # tool plate rear face = the Roto's side face
_ROTO = extruder_roto().interfaces
ROTO_W = _ROTO["mount_width"]                                  # 38.5
ROTO_NX, ROTO_NY, ROTO_NZ = _ROTO["nozzle_tip"][0]             # nozzle tip in the Roto's frame (-9.05, -4.07, -33.55)
ROTO_H2 = _ROTO["mount_holes_m3"][1]                           # second mounting hole (6.8, 0, 30.5)
HOT_OFF = R_TPR + ROTO_W / 2 + ROTO_NY                         # nozzle axis behind the beam centre: 46.18
YB0 = BED_CY - HOT_OFF         # beam centre Y at home (nozzle over the bed centre)
ROTO_O = (-ROTO_NX, YB0 + R_TPR + ROTO_W / 2, Z_BEAM)          # Roto origin (its lower hole): on the block's centre height
Z_NOZZLE = ROTO_O[2] + ROTO_NZ                                 # nozzle tip: 33.55 below the block centre
NOZZLE_GAP = 0.1               # bed surface -> nozzle with the bed at PRINT_Z: must not exceed the first layer height
# X drive: vertical belt loop over the beam, motor and idler on sheet plates on the beam's front face
XM_X, XI_X = -118.0, 118.0     # motor pulley / idler axes (along Y)
BEAM_L = 288.0                 # X beam: it ends 2.5 mm inboard of the Y guide blocks
XD_Z = Z_BEAM + 33.0           # their height: the lower motor screws clear the Y plate's tongue over the beam
X_PG = 2.75                    # gap between the motor plate and the pulley hub
XB_Y = YB0 - 10.0 + X_PG + P_BC(BWX)      # X belt centre line: over the beam, 4.75 mm behind its centre
X_SP = XB_Y - I_H(BWX) / 2 - (YB0 - 10.0)   # X idler spacer length (9: a stock length)
Z_XL = XD_Z - PR               # lower (anchored) run of the X belt, pitch line
BLK_Z0 = Z_BEAM + 14.0         # underside of the belt block (0.5 above the guide block)
BLK_Z1 = Z_BEAM + 32.5         # its top (the belt's upper run passes 6 mm above)
# Y drives: vertical belt planes outboard of both top side rails (v6: both sides alike)
Y_SP = 3.0                     # Y idler spacers (bought, aluminium, the shortest stock length). v7: the Y pulleys are turned hub-outboard,
                               # so the belt plane is 11.75 mm from the motor face (v6: 16.25) and the hub no longer decides this
YB_X = FX / 2 + MT_Y + Y_SP + I_H(BWY) / 2       # Y belt plane (+/-)
YM_Y, YI_Y = FY / 2 + 24.0, -164.5      # Y motor pulley (behind the frame) and Y idler (front, beyond the Y rails' ends)
Z_YA = Z_PLATE + T_YP + 0.7    # upper (anchored) run of each Y belt lies on its Y plate
Z_YC = Z_YA - PR
BELT_ADJ = 3.0                 # +/- travel of each belt tensioner
PH3, PH5 = 4.2, 6.0            # clearance holes in PRINTED parts (they come out about 0.15 mm small): M3, M5
SH3 = 3.6                      # M3 clearance in laser-cut sheet where four screws must start at once (ISO 273 coarse)
YH3 = 3.5                      # ... in the Y plates, whose play on the guide blocks moves the Y belt anchors sideways
NUT_POCKET = 2.6               # depth of a captive M3 nut pocket
NUT_SLOT = 3.7                 # nut slot width along the screw
CB = 3.2                       # counterbore depth for an M3 cap head
PL_Y0, PL_Y1 = -26.0, 15.5     # Y plates, from the beam centre line
BELT_SLOTS = (-15.0, -6.0, 6.0, 15.0)   # Y belt anchor slots in each Y plate, from the anchor centre
SLOT_W = 3.0                   # their width (= the sheet thickness)
YP_IN = RAIL_X - 33.0          # inboard edge of the tongue that the beam hangs from
YP_NOTCH = (RAIL_X - 15.5, -8.0)   # in front of y = -8 the plate starts here: the X motor / idler plates stand in the notch

# bed heights follow from the nozzle
Z_SURF = Z_NOZZLE - NOZZLE_GAP - PRINT_Z          # print surface (top of the steel sheet) at home (bed at the bottom)
Z_BED = Z_SURF - T_SHEET - T_MAG - T_BED          # underside of the aluminium plate at home
Z_FL = Z_BED - H_COL                              # top of the arms (the posts stand on them)
Z_ARM = Z_FL - 10.0                               # arm centre line
BP_Z1 = Z_SURF - 8.0                              # back plate top: 8 mm under the print surface (the toolhead passes over it)
ZC2 = BP_Z1 - 26.0                                # upper Z block centre at home
ZC1 = ZC2 - Z_SPACING                             # lower block
Z_RAIL_C = ZC1 - 22.7 - Z_DN - 5.3 + Z_RAIL_L / 2 # rail: 5.3 mm left below the lower block at -Z_DN; ends below the top back rail
BP_Z0 = ZC1 - 23.0                                # back plate covers both blocks, the arm ends and the nut block's flange
BP_W = 214.0                                      # 5 mm of sheet outside the outer screw holes
# ---- v8 Z drive: three lead screws turned by ONE motor through a closed GT2 belt; each screw stands in two 608 bearings
ZB = 77.25                                        # Z belt plane (belt centre): above the supply (53) and every board, below the carrier
Z_BT = ZB - 10.5                                  # top of each screw's upper bearing = underside of its pulley hub
Z_SLAB = Z_BT + 0.25                              # top of the printed drive mount's slab (motor plate and idler tab)
Z_MF = Z_SLAB - 5.0                               # Z motor mounting face (the motor hangs under the slab)
Z_TAB = 100.0                                     # underside of the three nut blocks at home (nuts clear the pulleys at -Z_DN)
BP_CUT = (48.0, 93.0)                             # back plate: cut away below z = 93 for |x| < 48 (the Z belt and its idler pass there)
NB_H = 10.0                                       # nut block height (v6: 10, so the nut's pin is an M3x16)
NB_BOLTS = [(sx * 23.0, Z_TAB + dz) for sx in (-1, 1) for dz in (0.0, 20.0)]
Y_FPR = Y_PF - ARM_L                              # front plate: rear face (the arms' front ends)
FS_Y = Y_FPR - T_FP - FS_OFF                      # front lead screw axis Y
ZM_X = 37.0                                       # Z motor axis X (the rear screw is at x = 0)
ZT_XY = (22.0, 150.0)                             # tensioner idler on the belt's back, between the right front screw and the motor
Z_SCREW_L = 300.0
Z_BELT_L = 1056.0                                 # closed GT2 loop, 520 teeth (stock length to be confirmed)
# Y endstop (lever switch): the trigger is the lever's operating position at its tip, 10.6 from the switch origin
# along the stroke and 9 to one side
ES_TRIG, ES_SIDE = 8.3, 9.0
LAND_X, LAND_Y1 = (-134.0, -115.5), 34.0          # left Y plate: land behind the beam for the X endstop
ES_OT = 1.5                                       # homing over-travel on X and Y, both ends (see the endstop notes in build())
ES_SP = 4.0                                       # bought spacers under the switch boards (their terminals stand 2.6 mm out)
ES_SP_X = 8.0                                     # X switch: 8 mm spacers, so its M3x16 screws and nuts end above the X rail and its stop
RAIL_STOPS = True
X_JACK = True
RAIL_SCREW_STEP = 2                               # every second hole of the X rail, as in v6
BEAM_BOLT_X = (RAIL_X - 33.0, RAIL_X - 21.0)      # v7: two M5 per side hold the beam under each Y plate (v6: one), |x|
STOP_X = (116.5, 126.0, 131.0, 143.0)             # rail stop plate: finger tip, body, notch, outer edge (|x|)
X_ES_Y = 29.6                                     # where the X switch's lever meets the left edge of the tool plate
# bed probe (v7): OMRON E2E-X10ME1, M18 unshielded, 10 mm on iron, about 3.0 mm on aluminium (2.4 .. 3.63 mm over
# +/-10 % unit spread and +/-10 % with temperature). Sensing face PRB_H above the nozzle tip: it switches with the
# nozzle 0.7 .. 1.9 mm above the bed. Unshielded: no metal within 27.5 mm of its axis in the 22 mm above the face, so
# it stands left of the Roto's heat sink and behind the tool plate, in a printed (ABS) arm.
PRB_MODEL = "E2E-X10ME1"
PRB_H = 1.8
PRB_X = -36.5                                     # probe axis: 28.75 mm from the Roto's heat sink, 30.4 from the HeaterCore
PRB_Y = R_TPR + 28.2                              # ... and 28.2 mm behind the tool plate's rear face
Z_PRB = Z_NOZZLE + PRB_H                          # sensing face
PRB_TURN = 22.5         # the (round) sensor turned about its own axis: see docs/PRINTER_V7.md, checker notes
PRB_CLAMP = (16.0, 22.0)                          # the arm's slab, above the sensing face (between the sensor's two nuts)
ARM_Z0, ARM_Z1 = Z_PRB + PRB_CLAMP[0] - Z_BEAM, Z_PRB + PRB_CLAMP[1] - Z_BEAM     # slab, from Z_BEAM: -15.85 .. -9.85
ARM_FL = 8.0                                      # arm flange thickness (M3x16 from the rear into the tab, tapped through)
ARM_SCREWS = [(-34.5, -4.0), (-26.5, -4.0)]       # arm -> left tab (x, z): above the sensor's metal-free zone
# tool plate outline, from the nozzle axis (x) and the beam centre (z)
TPX = 23.0                                        # half width over the guide block
TP_Z0, TP_Z1 = -14.0, 35.0
TAB_L = (-38.0, -23.0, -14.0, 5.5)                # left tab (x0, x1, z0, z1): the probe arm's seat (under the X switch's screws)
TAB_R = (13.0, 36.0, -27.0, -14.0)                # right tab under the Roto's motor: part-cooling duct
# part-cooling duct (printed): flange on the right tab, closed channel under the Roto's motor, plenum behind the Roto
# that the fan bolts to, outlet in the channel's left wall beside the nozzle
FC_X0, FC_X1 = TAB_R[0], TAB_R[1]
FC_FL = 6.0                                       # flange thickness
FC_Z0, FC_ZF = TAB_R[2], -12.3                    # flange underside; top of flange and channel (0.55 under the Roto's body)
DUCT_Z0 = -31.0                                   # channel underside: 2.55 mm above the nozzle plane
DUCT_W = 1.6                                      # duct walls (four 0.4 mm beads); floor 2.0
FC_LUG_Y = R_TPR + ROTO_W + 0.5                   # plenum front face: 0.5 behind the Roto
PLEN = 6.0                                        # plenum depth
PFAN = (19.5, FC_LUG_Y + PLEN + 5.0, -16.0)       # part fan centre (x, y from YB0, z from Z_BEAM): its right edge clears the rear corner bracket
PLEN_X0, PLEN_X1 = PFAN[0] - 16.5, PFAN[0] + 16.5
FAN_LUG = 3.5                                     # printed wall between the fan and its captive nuts (M3x16 = fan 10 + 3.5 + nut 2.4)
FC_SCREWS = [(18.5, -20.5), (30.5, -20.5)]        # duct flange -> tab (x, z)
DUCT_OUT = (40.0, 52.0, -29.0, -23.0)             # outlet window in the left wall (y0, y1 from YB0; z0, z1 from Z_BEAM)
BLK_SCREWS = [(-9.5, 19.0), (9.5, 19.0)]          # tool plate -> belt block (x, z from Z_BEAM)
BLK_Y0 = XB_Y - YB0 - BWX / 2 - 2.25              # belt block front face, from YB0 (the belt slots are open to it)
BLK_NUT_Y = 17.5                                  # the block's captive nuts bear on this face, from YB0


def mount_pcb(d, name, comp, holes_key, size, screw_len, sp_len, group, use=None):
    """A board on bought nylon spacers on the tray: screw from the top through board, spacer and tray into a nut.
    `use`: indices of the board's holes that get a screw (default: all)."""
    names = []
    for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][holes_key]):
        if use is not None and i not in use:
            continue
        place(d, f"{name}_spacer_{i}", spacer_round(size, sp_len), Location((hx, hy, Z_TRAY)))
        pcb_t = 1.5 if size == "M2.5" else 1.6
        add_screw(d, f"{name}_screw_{i}", size, screw_len, at=(hx, hy, Z_TRAY + sp_len + pcb_t),
                  clamps=(name, f"{name}_spacer_{i}", "electronics_tray"))
        add_nut(d, f"{name}_nut_{i}", size, at=(hx, hy, 20.0), direction=(0, 0, -1), screw=f"{name}_screw_{i}")
        names += [f"{name}_spacer_{i}", f"{name}_screw_{i}", f"{name}_nut_{i}"]
    group += [name] + names


def _hex(depth, af=5.9, turn=30.0):
    return extrude(Rot(0, 0, turn) * RegularPolygon(af / 2, 6, major_radius=False), depth)


def hex_pocket_y(x, y_face, z, depth, into=-1, af=5.9):
    """Pocket for an M3 nut cut into a face at y_face, going `into` (-1: towards -Y, +1: towards +Y)."""
    return Pos(x, y_face, z) * Rot(90 if into < 0 else -90, 0, 0) * _hex(depth, af)   # flats along X, like add_nut's


def hex_pocket_x(x_face, y, z, depth, into=-1, af=5.9):
    """Same, cut into a face at x_face going towards -X (into=-1) or +X."""
    return Pos(x_face, y, z) * Rot(0, -90 if into < 0 else 90, 0) * _hex(depth, af, 0.0)


def hex_pocket_z(x, y, z_face, depth, af=5.9):
    """Same, cut upwards into an underside at z_face."""
    return Pos(x, y, z_face) * _hex(depth, af, 0.0)


def fillet_z(x, y, sx, sy, r, z0, z1):
    """Material that rounds a vertical inside corner at (x, y); the open quadrant is towards (sx, sy)."""
    return (Pos(x + sx * r / 2, y + sy * r / 2, (z0 + z1) / 2) * Box(r, r, z1 - z0)
            - Pos(x + sx * r, y + sy * r, (z0 + z1) / 2) * Cylinder(r, z1 - z0))


def fillet_x(y, z, sy, sz, r, x0, x1):
    """Same for an inside corner that runs along X at (y, z)."""
    return (Pos((x0 + x1) / 2, y + sy * r / 2, z + sz * r / 2) * Box(x1 - x0, r, r)
            - Pos((x0 + x1) / 2, y + sy * r, z + sz * r) * Rot(0, 90, 0) * Cylinder(r, x1 - x0))


def fillet_y(x, z, sx, sz, r, y0, y1):
    """Same for an inside corner that runs along Y at (x, z)."""
    return (Pos(x + sx * r / 2, (y0 + y1) / 2, z + sz * r / 2) * Box(r, y1 - y0, r)
            - Pos(x + sx * r, (y0 + y1) / 2, z + sz * r) * Rot(90, 0, 0) * Cylinder(r, y1 - y0))


def slot_z(x, y, angle_deg, half_len, width, z0, z1):
    """Round-ended slot through a horizontal plate, +/- half_len along the direction angle_deg (from +X)."""
    h = z1 - z0
    return Pos(x, y, (z0 + z1) / 2) * Rot(0, 0, angle_deg) * (
        Box(2 * half_len, width, h) + Pos(-half_len, 0, 0) * Cylinder(width / 2, h)
        + Pos(half_len, 0, 0) * Cylinder(width / 2, h))


def bx(x0, x1, y0, y1, z0, z1):
    """Box from corner to corner."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


ycyl = lambda r, h: Rot(90, 0, 0) * Cylinder(r, h)
xcyl = lambda r, h: Rot(0, 90, 0) * Cylinder(r, h)


def back_plate_shape(carriage_holes):
    """Flat 5 mm sheet on the four Z blocks (laser cut, through holes only). The arms butt against its front face.
    v8: cut away at the bottom centre (the Z belt runs to the rear screw there), two holes for the bed tie."""
    yc = (Y_PF + Y_CAR) / 2
    p = Pos(0, yc, (BP_Z0 + BP_Z1) / 2) * Box(BP_W, T_BP, BP_Z1 - BP_Z0)
    cw, cz = BP_CUT
    p -= Pos(0, yc, (BP_Z0 + cz) / 2 - 1.0) * Box(2 * cw, T_BP, cz - BP_Z0 + 2.0)
    for sx in (-1, 1):       # round the cut-out's two upper corners
        p += fillet_y(sx * cw, cz, -sx, -1, 4.0, Y_PF, Y_CAR)
    for hx, hy, hz in carriage_holes:
        p -= Pos(hx, yc, hz) * ycyl(SH3 / 2, T_BP)
    for sx in (-1, 1):
        p -= Pos(sx * ARM_X, yc, Z_ARM) * ycyl(clearance_hole("M5") / 2, T_BP)          # arm end screw (blind joint)
        # corner bracket screw: a vertical slot, because the cast bracket has a 4 x 17 mm locating rib standing 1 mm
        # out of each leg (it normally sits in a T-slot); here it sits in this slot and keys the bracket
        p -= Pos(sx * ARM_X, yc, Z_ARM + 20.5) * (Box(clearance_hole("M5"), T_BP, 13.0)
                                                   + Pos(0, 0, 6.5) * ycyl(clearance_hole("M5") / 2, T_BP)
                                                   + Pos(0, 0, -6.5) * ycyl(clearance_hole("M5") / 2, T_BP))
    for x, z in NB_BOLTS:
        p -= Pos(x, yc, z) * ycyl(clearance_hole("M3") / 2, T_BP)
    for x in TIE_X:
        p -= Pos(x, yc, TIE_Z) * ycyl(clearance_hole("M3") / 2, T_BP)
    return p


TIE_X = (-20.0, 20.0)                 # tie screws (both flanges)
TIE_W = 60.0
TIE_Z = Z_BED - 12.0                  # tie -> back plate screws


def front_plate_shape():
    """v8: flat 3 mm steel sheet across the arms' front ends (laser cut, through holes only), mirror of the back plate:
    M5 into each arm's tapped end plus a cast corner bracket on top of the arm. Its ends reach out over the bottom
    side rails, where the two front nut blocks bolt to its front face."""
    yc = Y_FPR - T_FP / 2
    z0, z1 = Z_ARM - 15.0, Z_BED - 10.0
    p = bx(-(FS_X - 3.0), FS_X - 3.0, Y_FPR - T_FP, Y_FPR, z0, z1)
    # lightening window between the arms
    p -= Pos(0, yc, (z0 + z1) / 2) * Rot(90, 0, 0) * extrude(RectangleRounded(90.0, z1 - z0 - 24.0, 5.0), T_FP / 2, both=True)
    for sx in (-1, 1):
        p -= Pos(sx * ARM_X, yc, Z_ARM) * ycyl(clearance_hole("M5") / 2, T_FP)
        p -= Pos(sx * ARM_X, yc, Z_ARM + 20.5) * (Box(clearance_hole("M5"), T_FP, 13.0)
                                                   + Pos(0, 0, 6.5) * ycyl(clearance_hole("M5") / 2, T_FP)
                                                   + Pos(0, 0, -6.5) * ycyl(clearance_hole("M5") / 2, T_FP))
        for x, z in FNB_BOLTS:
            p -= Pos(sx * x, yc, z) * ycyl(clearance_hole("M3") / 2, T_FP)
    return p


FNB_BOLTS = [(FS_X - 36.0, Z_TAB), (FS_X - 36.0, Z_TAB + 20.0), (FS_X - 21.0, Z_TAB), (FS_X - 8.0, Z_TAB + 20.0)]   # clear of the block


def nut_block_shape(cx=0.0, y_face=None, sgn=1, bolts=None, x0=None, x1=None):
    """Printed block that sits on a floating T8 nut. A 6 mm flange bolts through a carrier plate (four M3 with nuts,
    no thread in plastic); the block has a square hole with NUT_FLOAT of room around the nut barrel and a slot for
    the anti-rotation pin. `sgn`: +1 the block reaches towards +Y from the plate face at y_face (rear nut, behind the
    back plate), -1 towards -Y (front nuts, in front of the front plate). Printed flange-down."""
    y_face = Y_CAR if y_face is None else y_face
    bolts = NB_BOLTS if bolts is None else bolts
    ls_y = LS_Y if sgn > 0 else FS_Y
    x0, x1 = (cx - 30.0, cx + 30.0) if x0 is None else (x0, x1)
    y_out = ls_y + sgn * 15.0
    b = bx(x0, x1, y_face, y_face + sgn * 6.0, Z_TAB - 7.0, Z_TAB + 27.0)      # flange
    b += bx(cx - 15.0, cx + 15.0, y_face + sgn * 6.0, y_out, Z_TAB, Z_TAB + NB_H)
    b -= Pos(cx, ls_y, Z_TAB + NB_H / 2) * Box(2 * (5.1 + NUT_FLOAT) + 0.8, 2 * (5.1 + NUT_FLOAT) + 0.8, NB_H)
    b -= slot_z(cx + NUT_PIN[0], ls_y + sgn * NUT_PIN[1], 90, NUT_FLOAT, clearance_hole("M3"), Z_TAB, Z_TAB + NB_H)
    for x, z in bolts:
        b -= Pos(x, y_face + sgn * 3.0, z) * ycyl(PH3 / 2, 6.0)
    return b


def bed_shape_():
    b = Pos(0, BED_CY, Z_BED + T_BED / 2) * Box(BED, BED, T_BED)
    for x, y in BED_MOUNTS:   # M5 cap heads of the posts sit 0.4 mm below the plate's top face (under the magnetic sheet)
        b -= Pos(x, y, Z_BED + T_BED / 2) * Cylinder(clearance_hole("M5") / 2, T_BED)
        b -= Pos(x, y, Z_BED + T_BED - POST_CB / 2) * Cylinder(4.75, POST_CB)
    for x in TIE_X:           # tie screws: M3, heads counterbored like v7's bed screws
        b -= Pos(x, TIE_Y, Z_BED + T_BED / 2) * Cylinder(clearance_hole("M3") / 2, T_BED)
        b -= Pos(x, TIE_Y, Z_BED + T_BED - TIE_CB / 2) * Cylinder(3.25, TIE_CB)
    return b


def bed_tie_shape():
    """1 mm steel sheet, one 90 degree bend (inside radius 1, outside 2): a flange under the bed's rear edge (two M3
    from the top, nuts below), 26 mm of free sheet, then down the back plate's front face (two M3, nuts behind).
    It holds the plate in X, Y and yaw at the rear centre and is soft vertically (about 0.2 N/um), so the four posts
    alone set the plate's height and the plate grows away from here when it is hot."""
    t, r = TIE_T, 1.0
    z1 = Z_BED                    # top face of the horizontal flange = bed underside
    y_in = Y_PF - t               # front face of the vertical flange (its rear face lies on the back plate)
    w = TIE_W / 2
    h = bx(-w, w, TIE_Y - 8.0, y_in - r, z1 - t, z1)
    v = bx(-w, w, y_in, Y_PF, TIE_Z - 8.0, z1 - t - r)
    yc, zc = y_in - r, z1 - t - r           # bend centre line
    bend = (Pos(0, yc, zc) * Rot(0, 90, 0) * Cylinder(r + t, TIE_W) - Pos(0, yc, zc) * Rot(0, 90, 0) * Cylinder(r, TIE_W))
    bend &= bx(-w, w, yc, yc + r + t, zc, zc + r + t)
    s = h + v + bend
    for x in TIE_X:
        s -= Pos(x, TIE_Y, z1 - t / 2) * Cylinder(clearance_hole("M3") / 2, t)
        s -= Pos(x, y_in + t / 2, TIE_Z) * ycyl(clearance_hole("M3") / 2, t)
    return s


BRG_R = 11.15         # printed seat for a 608 (22 OD): drawn 22.3, prints about 22.15: a sliding fit, the load seats it
PED_T = 16.0          # pedestal tower: half width (608 bearing 22 OD + 5 mm wall)
PED_EAR = 23.0        # its two M5 bolts, +/- along the rail from the screw axis


def z_pedestal_shape(sx):
    """v8: printed pedestal for one front lead screw. A 32 x 32 tower standing on the tray over the bottom side rail,
    a 608 bearing in a pocket at its top (it carries the screw's share of the bed's weight through the pulley hub
    resting on its inner ring) and a second 608 in a pocket at its foot (it only keeps the screw upright). Two ears
    with M5 screws through the tray into T-nuts in the rail's top slot. Printed standing."""
    x, y = sx * FS_X, FS_Y
    t = bx(x - PED_T, x + PED_T, y - PED_T, y + PED_T, Z_TRAY, Z_BT)
    t += bx(x - 10.0, x + 10.0, y - PED_EAR - 9.0, y + PED_EAR + 9.0, Z_TRAY, Z_TRAY + 8.0)
    t -= Pos(x, y, (Z_TRAY + Z_BT) / 2) * Cylinder(9.0, Z_BT - Z_TRAY)                    # clear of the screw and the inner rings
    t -= Pos(x, y, Z_BT - 3.5) * Cylinder(BRG_R, 7.0)                                     # upper bearing seat
    t -= Pos(x, y, Z_TRAY + 3.5) * Cylinder(BRG_R, 7.0)                                    # lower bearing seat (open to the tray)
    for dy in (-PED_EAR, PED_EAR):
        t -= Pos(x, y + dy, Z_TRAY + 4.0) * Cylinder(PH5 / 2, 8.0)
    return t


DM_COL = 14.0                   # drive mount: half width of the rear screw's bearing column (3 mm wall)
DM_Y0, DM_Y1 = LS_Y - 14.0, LS_Y + 23.0
DM_FOOT_X = (-33.0, -21.0)      # M5 into the bottom back rail's top slot
DM_REAR_X = (22.0, 52.0)        # M5 into its rear slot
DM_WALL = (DM_Y1, DM_Y1 + 4.0)  # rear wall, behind the motor
ZT_SLOT = 3.0                   # +/- travel of the tensioner idler's bolt in its slot (along X)


def z_drive_mount_shape():
    """v8: printed ABS mount on the bottom back rail for the Z drive: the rear lead screw's two 608 bearings in a
    column standing on the rail, a slab at the top that the Z motor hangs under (to the right of the screw) and that
    carries the belt tensioner idler on a forward tab, a foot block with two M5 into the rail's top slot and a rear
    wall with two M5 into the rail's rear slot. Printed slab down."""
    zs0, zs1 = Z_MF, Z_SLAB
    m = bx(-DM_COL, DM_COL, DM_Y0, DM_Y1, 20.0, zs1)                                       # bearing column
    m += bx(DM_COL, ZM_X + 23.0, LS_Y - 23.0, DM_WALL[1], zs0, zs1)                        # slab over the motor
    m += bx(-DM_COL, ZM_X + 23.0, DM_WALL[0], DM_WALL[1], 24.0, zs1)                       # rear wall, behind the motor
    m += bx(-DM_COL, DM_COL, LS_Y, DM_Y1, 2.0, 20.0)                                       # the column runs on down behind the rail
    m += bx(-DM_COL, ZM_X + 23.0, LS_Y, LS_Y + 4.0, 2.0, 21.0)                             # skirt on the rail's rear face, under the motor
    m += bx(-41.0, -DM_COL, UP_Y - 8.0, UP_Y + 8.0, 20.0, zs1)                             # foot block
    m += bx(ZT_XY[0] - 12.0, ZT_XY[0] + 12.0, ZT_XY[1] - 12.0, LS_Y - 23.0, zs0, zs1)      # idler tab
    m += bx(DM_COL, ZT_XY[0] + 12.0, LS_Y - 23.0, DM_Y0, zs0, zs1)
    # rear screw: bore, two bearing seats
    m -= Pos(0, LS_Y, (20.0 + zs1) / 2) * Cylinder(9.0, zs1 - 20.0)
    m -= Pos(0, LS_Y, zs1 - (zs1 - Z_BT + 7.0) / 2) * Cylinder(BRG_R, zs1 - Z_BT + 7.0)
    m -= Pos(0, LS_Y, 23.5) * Cylinder(BRG_R, 7.0)
    # motor: pilot hole (the pulley hub sinks 0.25 mm into it) and four M3
    m -= Pos(ZM_X, LS_Y, (zs0 + zs1) / 2) * Cylinder(11.5, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(ZM_X + x, LS_Y + y, (zs0 + zs1) / 2) * Cylinder(PH3 / 2, T_MM)
    # foot bolts: M5 x 16 on an 8 mm floor, reached through 10 mm bores from the top
    for x in DM_FOOT_X:
        m -= Pos(x, UP_Y, 24.0) * Cylinder(PH5 / 2, 8.0)
        m -= Pos(x, UP_Y, (28.0 + zs1) / 2) * Cylinder(5.0, zs1 - 28.0)
    for x in DM_REAR_X:
        m -= Pos(x, LS_Y + 2.0, 10.0) * ycyl(PH5 / 2, 4.0)
    # tensioner slot
    m -= slot_z(ZT_XY[0], ZT_XY[1], 0.0, ZT_SLOT, clearance_hole("M5"), zs0, zs1)
    return m


def tool_plate_shape():
    """8 mm plate between the X guide block and the Roto: the one structural part of the toolhead. Its front face
    sits on the block (four M3x8, heads counterbored from the rear), the Roto's flat side sits on its rear face (two
    M3x45 through the Roto into tapped holes). A tab on the left carries the bed probe, a tab under the Roto's motor
    the part-fan carrier, and the belt block bolts to the front face above the guide block. Machined in one set-up
    from the rear: outline, six counterbored holes, two clearance holes, four M3 holes tapped through.
    Why not sheet: the block's threads take 3.0 .. 3.5 mm of screw, which no standard M3 length gives through a plate
    thick enough (6.5 mm) for the Roto's screws without a counterbore."""
    y0, y1 = YB0 + R_TPF, YB0 + R_TPR
    yc = (y0 + y1) / 2
    box = lambda x0, x1, z0, z1: bx(x0, x1, y0, y1, Z_BEAM + z0, Z_BEAM + z1)
    tp = box(-TPX, TPX, TP_Z0, TP_Z1) + box(*TAB_L) + box(*TAB_R)
    r = 3.0     # inside corners: a 6 mm cutter, 8 mm deep
    tp += fillet_y(-TPX, Z_BEAM + TAB_L[3], -1, 1, r, y0, y1)        # left tab top / plate edge
    tp += fillet_y(TAB_R[0], Z_BEAM + TP_Z0, -1, -1, r, y0, y1)      # plate underside / right tab
    tp += fillet_y(TPX, Z_BEAM + TP_Z0, 1, 1, r, y0, y1)             # plate edge / right tab top
    for x in (-10, 10):
        for z in (-10, 10):
            tp -= Pos(x, yc, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TP)
            tp -= Pos(x, y1 - CB / 2, Z_BEAM + z) * ycyl(3.0, CB)
    for x, z in FC_SCREWS:
        tp -= Pos(x, yc, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TP)
    # the four tapped holes (Roto, probe) are drilled and tapped right through: tap-drill holes
    for x, z in ([(h[0], h[2] - Z_BEAM) for h in (ROTO_O, (ROTO_O[0] + ROTO_H2[0], 0.0, ROTO_O[2] + ROTO_H2[2]))]
                 + ARM_SCREWS):
        tp -= Pos(x, yc, Z_BEAM + z) * ycyl(2.5 / 2, T_TP)
    # v7: two lightening windows (same set-up): between the guide block's screws and above the belt block's
    for xc, zc, wx, wz in ((0.0, 0.0, 10.0, 10.0), (-6.0, 28.0, 22.0, 8.0)):
        tp -= Pos(xc, yc, Z_BEAM + zc) * Rot(90, 0, 0) * extrude(RectangleRounded(wx, wz, 3.0), T_TP / 2, both=True)
    for x, z in BLK_SCREWS:      # belt block screws: from the rear too, heads sunk under the Roto's side face
        tp -= Pos(x, yc, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TP)
        tp -= Pos(x, y1 - CB / 2, Z_BEAM + z) * ycyl(3.0, CB)
    return tp


def belt_block_shape():
    """Printed block on the tool plate's front face, above the guide block, reaching forward over the beam. The X
    belt's two ends slide into a slot from the front; each end is folded back on itself in the taller middle of the
    slot, where its teeth lock in its own teeth (no clamp bar, no clamp screws). Two M3x16 from the rear of the tool
    plate run into captive nuts dropped into slots from the top. Printed rear face down:
    the belt slot is then a vertical-walled channel open to the top."""
    y0, y1 = YB0 + BLK_Y0, YB0 + R_TPF
    b = bx(-14.0, 14.0, y0, y1, BLK_Z0, BLK_Z1)
    ys = XB_Y + BWX / 2 + 0.5                                           # slot depth: belt width + 0.5
    b -= bx(-14.0, 14.0, y0, ys, Z_XL - 0.75, Z_XL + 0.85)              # one belt thickness
    b -= bx(-9.0, 9.0, y0, ys, Z_XL - 0.75, Z_XL + 2.3)                 # two belt thicknesses, teeth in teeth
    for x, z in BLK_SCREWS:
        b -= Pos(x, (YB0 + BLK_NUT_Y - 6.5 + y1) / 2, Z_BEAM + z) * ycyl(PH3 / 2, y1 - (YB0 + BLK_NUT_Y - 6.5))
        b -= bx(x - 2.9, x + 2.9, YB0 + BLK_NUT_Y - NUT_SLOT, YB0 + BLK_NUT_Y, Z_BEAM + z - 3.35, BLK_Z1)
    return b


def part_duct_shape():
    """Printed ABS part-cooling duct (v7; v6 had only a carrier and left the duct undrawn). From the rear: a plenum
    the fan bolts to (two M3x16 through the fan's lower holes into captive nuts, slots open to the underside), which
    turns the fan's air down into a closed 20.8 x 15.1 mm channel under the Roto's motor; the channel ends at a
    flange on the tool plate's right tab (two M3x16 from the front into captive nuts) and blows out sideways through
    a 12 x 6 mm window in its left wall, 13 mm from the nozzle axis and 4.5 .. 10.5 mm above the nozzle plane.
    Printed rear face down: every wall is vertical, the plenum's front wall is a 30 mm bridge."""
    yf, yl, yr = YB0 + R_TPR, YB0 + FC_LUG_Y, YB0 + FC_LUG_Y + PLEN
    z0, zf, zd = Z_BEAM + FC_Z0, Z_BEAM + FC_ZF, Z_BEAM + DUCT_Z0
    zt = Z_BEAM + PFAN[2] + 15.0                                               # plenum top = fan top
    w = DUCT_W
    c = bx(FC_X0, FC_X1, yf, yf + FC_FL, z0, zf)                               # flange
    c += bx(FC_X0, FC_X1, yf + FC_FL, yl, zd, zf)                              # channel
    c += bx(PLEN_X0, PLEN_X1, yl, yr, zd, zt)                                  # plenum
    c -= bx(FC_X0 + w, FC_X1 - w, yf + FC_FL + w, yr, zd + 2.0, zf - w)        # channel bore, open to the plenum
    c -= bx(PLEN_X0 + w, PLEN_X1 - w, yl + w, yr, zd + 2.0, zt - w)            # plenum bore, open to the fan
    zb = Z_BEAM + PFAN[2] - 12.0                                               # lower fan holes
    for sx in (-12.0, 12.0):                                                   # bosses in the two lower corners for the fan's nuts
        xb = PFAN[0] + sx
        c += bx(xb - 4.5, xb + 4.5, yl, yr, zd, zb + 5.0)
        c -= Pos(xb, yr - FAN_LUG / 2, zb) * ycyl(PH3 / 2, FAN_LUG)
        c -= bx(xb - 2.9, xb + 2.9, yr - FAN_LUG - NUT_SLOT, yr - FAN_LUG, zd, zb + 3.35)
    # the Roto's lower M3x45 has its head on the Roto's rear face, in the plenum's top left corner: solid corner, pocket for the head
    hx, hz = ROTO_O[0], ROTO_O[2]
    c += bx(PLEN_X0, hx + 4.5, yl, yr, hz - 6.5, zt)
    c -= bx(hx - 3.3, hx + 3.3, yl, yl + 4.0, hz - 3.3, zt)
    y0, y1, oz0, oz1 = DUCT_OUT
    c -= bx(FC_X0 - 0.1, FC_X0 + w + 0.1, YB0 + y0, YB0 + y1, Z_BEAM + oz0, Z_BEAM + oz1)      # outlet towards the nozzle
    for x, z in FC_SCREWS:      # screw hole through the flange and a nut slot open to the underside
        c -= Pos(x, yf + (FC_FL + w) / 2, Z_BEAM + z) * ycyl(PH3 / 2, FC_FL + w)
        c -= bx(x - 2.9, x + 2.9, yf + FC_FL - NUT_SLOT, yf + FC_FL, z0, Z_BEAM + z + 3.35)
    return c


def probe_arm_shape():
    """Printed ABS arm for the M18 bed probe: an 8 mm flange on the rear face of the tool plate's left tab (two
    M3x16 from the rear into the tab's tapped holes) standing on a 6 mm slab that runs back under the Roto's fan to
    the 18.5 mm hole the sensor is clamped in by its own two nuts. Plastic, because the unshielded sensor allows no
    metal within 27.5 mm of its head. Printed slab down."""
    yf = YB0 + R_TPR
    a = bx(TAB_L[0], -23.5, yf, yf + ARM_FL, Z_BEAM + ARM_Z0, Z_BEAM + TAB_L[3])               # flange
    a += bx(PRB_X - 15.0, -21.0, yf, YB0 + PRB_Y + 16.5, Z_BEAM + ARM_Z0, Z_BEAM + ARM_Z1)     # slab
    a -= Pos(PRB_X, YB0 + PRB_Y, Z_BEAM + (ARM_Z0 + ARM_Z1) / 2) * Cylinder(18.5 / 2, ARM_Z1 - ARM_Z0)
    # the hole is open to the rear (a fork): the sensor, with both nuts already on its thread, slides in from behind
    a -= bx(PRB_X - 9.25, PRB_X + 9.25, YB0 + PRB_Y, YB0 + PRB_Y + 17.0, Z_BEAM + ARM_Z0, Z_BEAM + ARM_Z1)
    for x, z in ARM_SCREWS:
        a -= Pos(x, yf + ARM_FL / 2, Z_BEAM + z) * ycyl(PH3 / 2, ARM_FL)
    return a


def probe_key_shape():
    """Printed key that closes the mouth of the arm's fork behind the sensor, so the two nuts clamp on a full ring.
    It slides in from behind after the sensor; the nuts overlap it by 2.7 mm and hold it."""
    k = bx(PRB_X - 9.05, PRB_X + 9.05, YB0 + PRB_Y + 6.5, YB0 + PRB_Y + 16.5, Z_BEAM + ARM_Z0, Z_BEAM + ARM_Z1)
    k -= Pos(PRB_X, YB0 + PRB_Y, Z_BEAM + (ARM_Z0 + ARM_Z1) / 2) * Cylinder(18.5 / 2, ARM_Z1 - ARM_Z0)
    return k


USE_CUTOFFS = True
USE_MOSFET = False     # v7: see BED_W


def build_electrical(d: Design) -> Electrical:
    """Devices, looms, wires and firmware settings. Every device is a stock product (Device.product says which).
    v6: the extruder (E3D Roto) is back on the toolhead; heater and thermistor are the Revo HeaterCore; the Roto's 5 V
    heat-sink fan runs from the board's 5 V pins."""
    from mechloop.electrical import add_board_5v_port

    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend", "part_fan", "x_endstop", "y_endstop", "bed_probe", "x_motor",
               "z_motor", "extruder"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed_plate")      # the thermal model takes the plate's mass and area from this part
    for nm in ("y_motor", "y_motor_l"):       # two motors on one driver, coils in parallel (the board's ZAM/ZBM pair)
        device_from(el, d, nm, connection="parallel")
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", ratings={"max_temp_c": 180.0},
                    sources={"points": "Klipper 'Generic 3950' (Keenovo R-T table)", "tau_s": "assumed 10 s (typical, unverified)"},
                    sensor_type="Generic 3950", points=THERMISTORS["Generic 3950"], tau_s=10.0, node="pad")
    # the Revo HeaterCore carries its own thermistor (same CAD part)
    embedded_device(el, d, "hotend", "hotend_thermistor", "thermistor", "ntc", "thermistor", **d.get("hotend").ratings["thermistor"])
    # the Roto's own heat-sink fan: 5 V, 0.14 A (E3D's figures, in the catalogue part's ratings)
    rf = d.get("extruder").ratings["fan"]
    embedded_device(el, d, "extruder", "hotend_fan", "fan", "fan", "fan",
                    ratings={"current_a": rf["current_a"], "volts": rf["volts"]},
                    sources={"current_a": "E3D Roto data sheet, 'Fan Specification': 5 V, 0.14 A"})
    add_board_5v_port(el, "control_board")
    device_from(el, d, "bed_tco")
    device_from(el, d, "psu_relay")
    if USE_MOSFET:
        device_from(el, d, "bed_mosfet")
    el.add(Device("frame_earth", "earth_point", "earth_stud",
                  {"pe": Port("pe", "pe", "ring-M4", 20.0, at=(-FX / 2 - 6.0, 80.0, 10.0), multi=True, extra={"body": "world"})},
                  params={"bonds": "frame_bot_left"},
                  product={"product": "M5 ring terminals under an M5 screw and star washer in a T-nut", "vendor": "commodity",
                           "part_number": None, "form": "hardware", "off_the_shelf": True, "custom_pcb": False,
                           "builder_work": "crimp ring terminals; scratch through the anodising under the washer"}))
    zt = Z_TRAY + 8.0
    XL, ZL = -147.0, FZ - 6.0      # left looms run along the inner face of the left top rail, on its lower land
    # ---- looms (centre lines; one bundle radius off surfaces). Consecutive waypoints on different bodies flex.
    P1 = (147.0, 134.0, FZ - 6.0)      # on the inner face of the right top rail, clear of the toolhead's sweep
    # toolhead loom: tied along the top of the Roto's rear face (left end: probe and hot-side leads join; right end:
    # motor lead joins and the free loop leaves), high enough to clear the part fan when the loop trails back
    yl = YB0 + R_TPR + ROTO_W + 2.0
    el.loom("toolhead", [Waypoint("xbody", (-13.0, yl, Z_BEAM + 26.0), clamp="extruder"),
                         Waypoint("xbody", (24.0, yl, Z_BEAM + 26.0), clamp="extruder"),
                         Waypoint("world", (147.8, 118.0, FZ - 6.0), clamp="frame_top_right"), Waypoint("world", P1)],
            flex_length={1: 460.0})
    el.loom("drop_right", [("world", P1), ("world", (145.0, 152.0, FZ - 32.0)), ("world", (145.0, 168.0, FZ - 74.0)),
                           ("world", (145.0, 170.0, 60.0)), ("world", (145.0, 150.0, 34.0))])
    # v8: the right loom runs between the board and the right Z pedestal (x = 137)
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (137.0, 46.0, zt)), ("world", (137.0, -26.0, zt))])
    el.loom("front_right", [("world", (137.0, -26.0, zt)), ("world", (137.0, -125.0, zt)), ("world", (143.0, -150.0, 40.0)),
                            ("world", (143.0, -170.0, 70.0)), ("world", (143.0, -170.0, FZ - 64.0)),
                            ("world", (143.0, -152.0, FZ - 26.0)), ("world", (146.0, -136.0, FZ - 8.0))])
    el.loom("back", [("world", (140.0, 152.0, 30.0)), ("world", (130.0, 155.0, 12.0)), ("world", (30.0, 155.0, 12.0))])
    # the X motor's and X switch's leads are tied to the front edge of the left Y plate, inboard of the Y guide block;
    # the loop trails forward from there to the rail's inner face (the frame clamp is level with the plate's front
    # edge at y = -TY, so the loop never has to pass back under the guide block)
    el.loom("gantry", [Waypoint("ybody", (-150.0, YB0 + PL_Y0 - 2.5, Z_PLATE + T_YP / 2), clamp="y_plate_left"),
                       Waypoint("world", (XL - 0.8, -134.4, ZL), clamp="frame_top_left")], flex_length={0: 240.0})
    el.loom("top_left", [("world", (XL, -20.0, ZL)), ("world", (XL, 136.0, ZL))])
    # v8: the left loom comes down the front left post and crosses to the board along the top of the front bottom rail
    # (v7 ran it along the left side, where the left Z pedestal now stands, and across the tray, where the supply now lies)
    el.loom("drop_left", [("world", (XL, -27.0, ZL)), ("world", (XL, -120.0, ZL)),
                          ("world", (-143.0, -150.0, FZ - 24.0)), ("world", (-143.0, -170.0, FZ - 64.0)),
                          ("world", (-143.0, -170.0, 70.0)), ("world", (-140.0, -166.0, 26.0))])
    el.loom("front", [("world", (-140.0, -166.0, 26.0)), ("world", (60.0, -166.0, 26.0)), ("world", (72.0, -142.0, zt))])
    el.loom("bed", [Waypoint("zbody", (0.0, Y_PF - 3.0, Z_TAB + 19.0), clamp="back_plate"),
                    Waypoint("zbody", (0.0, Y_PF - 3.0, Z_TAB - 4.0), clamp="back_plate"),
                    Waypoint("world", (0.0, TRAY_Y1 - 4.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 330.0})
    el.loom("mains", [("world", (-122.0, 6.0, zt)), ("world", (-96.0, 14.0, zt)), ("world", (-96.0, 76.0, zt)), ("world", (-78.0, 82.0, zt))])
    tool, left = ["tray_right", "drop_right", "toolhead"], ["front", "drop_left"]
    # ---- mains and protective earth (AWG 18 = 0.82 mm^2, 105 degC PVC)
    mk = dict(conductors=1, insulation="pvc105")
    el.wire("mains L inlet-relay", "inlet.L", "psu_relay.LIN", 18, **mk)
    el.wire("mains L relay-supply", "psu_relay.LOT", "psu.L", 18, via=["mains"], **mk)
    el.wire("relay control", "control_board.PS-ON", "psu_relay.ctrl", 26, conductors=3)
    # v7: the relay module powers itself from the mains, so the neutral runs through its N terminal (twin ferrule)
    el.wire("mains N inlet-relay", "inlet.N", "psu_relay.N", 18, **mk)
    el.wire("mains N relay-supply", "psu_relay.N", "psu.N", 18, via=["mains"], **mk)
    el.wire("earth to supply", "inlet.PE", "psu.FG", 18, via=["mains"], **mk)
    el.wire("earth to frame", "inlet.PE", "frame_earth.pe", 18, connector_b="ring-M4", **mk)
    # ---- 24 V distribution
    el.wire("24 V to board", "psu.V+1", "control_board.POWER", 16, insulation="silicone")
    if USE_MOSFET:
        el.wire("24 V to bed module", "psu.V+2", "bed_mosfet.pwr", 14, insulation="silicone")
        el.wire("bed control", "control_board.HB", "bed_mosfet.ctrl", 24)
        el.wire("bed heater", "bed_mosfet.out", "bed_tco.a", BED_AWG, insulation=BED_INS, via=["bed"])
    else:   # v7: a 180 W pad for an 85 degC bed is inside the board's own bed output (7.5 A of 8 A allowed)
        el.wire("bed heater", "control_board.HB", "bed_tco.a", BED_AWG, insulation=BED_INS, via=["bed"])
    el.wire("bed heater tail", "bed_tco.b", "bed_heater.in", BED_AWG, insulation=BED_INS, length=90.0)
    el.wire("bed thermistor", "control_board.THB", "bed_ntc.out", 26, insulation="silicone", via=["bed"])
    # ---- toolhead: heater, thermistor, two fans, probe, extruder motor
    # the HeaterCore's own leads are 115 / 130 mm long (E3D drawing). E3D rates the part for 300 degC but does not
    # state the lead insulation: taken as glass-fibre sleeved (unverified)
    el.wire("hotend heater", "control_board.E0", "hotend.in", 20, insulation="silicone", via=tool, pigtail=(115.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, insulation="silicone", via=tool,
            pigtail=(130.0, "fiberglass"))
    el.wire("heat-sink fan 5 V", "control_board.5V", "hotend_fan.out", 26, via=tool,
            note="the Roto's fan is a 5 V part: always on from the board's 5 V pins, never on a 24 V fan output")
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    el.wire("bed probe", "control_board.Z-STOP", "bed_probe.out", 26, conductors=3, insulation="silicone", via=tool,
            note="signal and 0 V on the Z-STOP header; the sensor's + lead goes to 24 V (declared on the device, not "
                 "routed as a wire); BAT85 diode in the signal lead, cathode to the sensor")
    # the probe's supply: its brown lead on the 24 V rail at the board's power terminals. The diode is fitted whether
    # or not this unit has an internal pull-up: the board pin then never sees more than its own 3.3 V pull-up.
    el.devices["bed_probe"].params.update(supply_v=24.0, supply_from="24 V rail at the control board's power terminals",
                                          series_diode=True)
    el.wire("extruder motor", "control_board.EM", "extruder.coils", 24, conductors=4, via=tool)
    # ---- axes. The Y pair is on the board's doubled "Z" connectors (one driver); the Z motor is on the "Y" driver.
    el.wire("X motor", "control_board.XM", "x_motor.coils", 24, conductors=4, via=left + ["gantry"])
    el.wire("X endstop", "control_board.X-STOP", "x_endstop.out", 26, conductors=3, via=left + ["gantry"])
    el.wire("Y endstop", "control_board.Y-STOP", "y_endstop.out", 26, conductors=3, via=["tray_right", "front_right"])
    el.wire("Y motor left", "control_board.ZBM", "y_motor_l.coils", 24, conductors=4, via=left + ["top_left"],
            note="mirror-image motor: swap one coil pair at the connector so both turn the belts the same way")
    el.wire("Y motor right", "control_board.ZAM", "y_motor.coils", 24, conductors=4, via=["tray_right", "drop_right"])
    el.wire("Z motor", "control_board.YM", "z_motor.coils", 24, conductors=4, via=["tray_right", "back"])
    el.wire("host serial + 5 V", "control_board.TFT", "host.GPIO", 26, conductors=4)
    # ---- firmware (Klipper). PID values are left to the simulated PID_CALIBRATE. The extruder's rotation distance,
    # gear ratio and 400 full steps come from the Roto's catalogue entry.
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
    # hot parts wires must be rated for: the HeaterCore and nozzle block (not the whole part) and the bed plate
    hi = d.get("hotend").meta["interfaces"]
    rc = hi["heatercore_dia"] / 2
    hb = (-rc, YB0 + HOT_OFF - rc, hi["heater_block_box"][0][2], rc, YB0 + HOT_OFF + rc, hi["heater_block_box"][1][2])
    el.hot_parts = {"hotend": {"temp": 250.0, "box": hb}, "bed": BED_MAX_C}
    # the bay is the open tray under the bed: air leaves through the open sides of the frame
    el.bay = Bay(devices=[n for n in ("psu", "control_board", "host", "psu_relay", "bed_mosfet") if n in el.devices],
                 enclosed=False, vent_area_m2=0.02, height_m=0.05)
    el.sync_cables(d)
    add_electrical_bom(el, d)
    d.bom_extra(f"FUSE-5x20-T{FUSE_A:g}A", 2, 0.3)
    d.bom_extra("DIODE-BAT85", 1, 0.1)
    return el


def build() -> Design:
    d = Design("printer_v8", envelope=ENVELOPE, base="frame_bot_left")
    # laser-cut sheet; a desktop FDM printer for the plastic parts
    d.manufacturing = {"shop": "generic", "sheet": {"method": "laser"},
                       "printer": {"build_volume": (220.0, 220.0, 220.0), "nozzle": 0.4}}
    # ================= frame =====================================================
    for sx, n in ((-1, "left"), (1, "right")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
            place(d, f"frame_{lvl}_{n}", extrusion_2020(FY), Location((sx * RAIL_X, 0, z), (0, 0, 90)))
    for sy, n in ((-1, "front"), (1, "back")):
        for z, lvl in ((FZ, "top"), (10, "bot")):
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
            for lvl, zc, zdir in (("top", FZ - 10, -1), ("bot", 20, 1)):
                add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{side}", post,
                                   (sx * RAIL_X, yi, zc), (0, -sy, 0), (0, 0, zdir)); k += 1
                add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{cross}", f"frame_{lvl}_{side}",
                                   (sx * (RAIL_X - 10), yi, FZ if lvl == "top" else 10), (-sx, 0, 0), (0, -sy, 0)); k += 1
    # Z uprights between the bottom and top back rails
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"upright_{n}", extrusion_2020(FZ - 30), Location((sx * UP_X, UP_Y, (FZ + 10) / 2), (0, 90, 0)))
        for lvl, zc, zdir in (("bot", 20, 1), ("top", FZ - 10, -1)):
            add_corner_bracket(d, f"brkt_up_{lvl}_in_{n}", f"frame_{lvl}_back", f"upright_{n}",
                               (sx * (UP_X - 10), UP_Y, zc), (-sx, 0, 0), (0, 0, zdir))
            add_corner_bracket(d, f"brkt_up_{lvl}_out_{n}", f"frame_{lvl}_back", f"upright_{n}",
                               (sx * (UP_X + 10), UP_Y, zc), (sx, 0, 0), (0, 0, zdir))

    # ================= Z axis ====================================================
    # two blocks on each 300 mm rail, Z_SPACING apart
    carriage_holes = []
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"z_rail_{n}", mgn12_rail(Z_RAIL_L),
                     Location(Plane(origin=(sx * UP_X, Y_FACE, Z_RAIL_C), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
        for i, (hx, hy, hz) in enumerate(rail.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"z_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy - 3.5, hz), direction=(0, 1, 0),
                      threads_into=f"upright_{n}", tnut=True)
        for lvl, zc in (("lo", ZC1), ("hi", ZC2)):
            car = place(d, f"z_carriage_{n}_{lvl}", mgn12h_carriage(),
                        Location(Plane(origin=(sx * UP_X, Y_FACE, zc), x_dir=(0, 0, 1), z_dir=(0, -1, 0))),
                        body="zbody", guides="z")
            holes = car.meta["interfaces"]["mount_holes_m3"]
            carriage_holes += holes
            for i, (hx, hy, hz) in enumerate(holes):
                add_screw(d, f"z_carriage_{n}_{lvl}_screw_{i}", "M3", 8, at=(hx, hy - T_BP, hz), direction=(0, 1, 0),
                          body="zbody", threads_into=f"z_carriage_{n}_{lvl}")
    # bed carrier (v8): sheet back plate on the four blocks, two 2020 arms, sheet front plate. Each arm end is held by
    # an M5 screw through the plate into its tapped end and a cast corner bracket on top of the arm (T-nut in the
    # arm's top slot; its plate-side M5 screw and nut are modelled by add_corner_bracket).
    d.add("back_plate", back_plate_shape(carriage_holes), material="al6061", body="zbody", process="sheet")
    d.add("front_plate", front_plate_shape(), material="steel", body="zbody", process="sheet")
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"bed_arm_{n}", extrusion_2020(ARM_L), Location((sx * ARM_X, Y_PF - ARM_L / 2, Z_ARM), (0, 0, 90)),
              body="zbody")
        add_screw(d, f"bed_arm_{n}_bolt", "M5", 16, at=(sx * ARM_X, Y_CAR, Z_ARM), direction=(0, -1, 0), body="zbody",
                  threads_into=f"bed_arm_{n}", clamps=("back_plate",))
        add_corner_bracket(d, f"bed_arm_{n}_bracket", f"bed_arm_{n}", "back_plate",
                           (sx * ARM_X, Y_PF, Z_ARM + 10.0), (0, -1, 0), (0, 0, 1), body="zbody")
        add_screw(d, f"bed_arm_{n}_fbolt", "M5", 12, at=(sx * ARM_X, Y_FPR - T_FP, Z_ARM), direction=(0, 1, 0), body="zbody",
                  threads_into=f"bed_arm_{n}", clamps=("front_plate",))
        add_corner_bracket(d, f"bed_arm_{n}_fbracket", f"bed_arm_{n}", "front_plate",
                           (sx * ARM_X, Y_FPR, Z_ARM + 10.0), (0, 1, 0), (0, 0, 1), body="zbody")
    # three floating nuts: each hangs under its printed block (the bed's weight keeps the block sitting on the nut
    # flange); the pin screw gets a nyloc nut under the flange left 0.2 mm slack, so the nut slides +/-NUT_FLOAT and
    # cannot turn. Rear: behind the back plate's centre. Front: on the front plate's ends, over the bottom side rails.
    nut_sets = [("", 0.0, LS_Y, 1, Y_CAR, Y_PF, "back_plate", NB_BOLTS, None, None, "+Y")]
    for sx, tag in ((-1, "_fl"), (1, "_fr")):
        xs = sorted((sx * (FS_X - 42.0), sx * (FS_X + 15.0)))
        nut_sets.append((tag, sx * FS_X, FS_Y, -1, Y_FPR - T_FP, Y_FPR, "front_plate", [(sx * x, z) for x, z in FNB_BOLTS], xs[0], xs[1], "-Y"))
    for tag, cx, ly, sgn, y_face, y_far, plate, bolts, x0, x1, up in nut_sets:
        d.add(f"nut_block{tag}", nut_block_shape(cx, y_face, sgn, bolts, x0, x1), material=HOT, body="zbody", process="printed",
              meta={"print_up": up})
        for i, (x, z) in enumerate(bolts):
            add_screw(d, f"nut_block{tag}_bolt_{i}", "M3", 16, at=(x, y_far, z), direction=(0, sgn, 0), body="zbody",
                      clamps=(plate, f"nut_block{tag}"))
            add_nut(d, f"nut_block{tag}_nut_{i}", "M3", at=(x, y_face + sgn * 6.0, z), direction=(0, sgn, 0), body="zbody",
                    screw=f"nut_block{tag}_bolt_{i}")
        place(d, f"z_nut{tag}", leadscrew_nut_t8(), Location((cx, ly, Z_TAB - 3.5)), body="zbody")
        add_screw(d, f"nut_pin{tag}", "M3", 16, at=(cx + NUT_PIN[0], ly + sgn * NUT_PIN[1], Z_TAB + NB_H), body="zbody",
                  threads_into=f"z_nut{tag}")
    d.bom_extra("NYLOC-M3", 3, 0.05)
    # bed plate: 8 mm cast tooling plate (MIC-6). Machined in one set-up from the top (six counterbored holes); the
    # cast faces are left as bought.
    bed_own = BED * BED * T_BED * MATERIALS["al_mic6"].density * 1e-9
    d.add("bed_plate", bed_shape_(), material="al_mic6", body="zbody", mass_kg=bed_own + PAYLOAD_KG, process="machined")
    # PURCHASED STAND-INS (the catalogue has no print sheet): a magnetic sheet stuck to the plate and a spring-steel
    # print sheet on it. Every figure here is a typical value, NOT from a data sheet (docs/PRINTER_V8.md, "needed
    # vendor data"). The steel sheet is the print surface (design.printer["bed"]) and the probe's target.
    mag = Stock(Pos(0, 0, T_MAG / 2) * Box(BED, BED, T_MAG), "BED-MAGNET-220-STANDIN",
                "Flexible magnetic sheet 220 x 220 x 1.0 mm, adhesive back (purchased stand-in: thickness, density 3.7 g/cm3 "
                "and an 80 degC working limit are typical figures for ferrite-loaded rubber, unverified)",
                BED * BED * T_MAG * 3.7e-6, material="rubber_gt2", cost_usd=12.0,
                ratings={"max_temp_c": 80.0, "max_temp_basis": "typical for standard magnetic sheet, unverified"})
    sheet = Stock(Pos(0, 0, T_SHEET / 2) * Box(BED, BED, T_SHEET), "PRINT-SHEET-STEEL-220-STANDIN",
                  "Spring-steel print sheet 220 x 220, PEI coated (purchased stand-in: 0.5 mm steel assumed, coating not drawn; "
                  "that an inductive sensor reads thin spring steel like OMRON's 1 mm iron target is unverified)",
                  BED * BED * T_SHEET * 7.85e-6, material="steel", cost_usd=18.0)
    place(d, "bed_magnet", mag, Location((0, BED_CY, Z_BED + T_BED)), body="zbody")
    place(d, "bed", sheet, Location((0, BED_CY, Z_BED + T_BED + T_MAG)), body="zbody")
    d.join("bed_magnet", "bed_plate", "bond")
    d.join("bed", "bed_magnet", "magnet")
    # silicone pad, 200 wide x 140 deep so the four posts stand in front of and behind it; leads leave at the back
    place(d, "bed_heater", bed_heater_pad(200.0, 140.0, BED_W), Location((0, BED_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed_plate", "bond")
    place(d, "bed_tco", thermal_fuse(133.0, 109.0, 15.0), Location((-45.0, BED_Y1 - 5.0, Z_BED - 2.0)), body="zbody")
    d.join("bed_tco", "bed_plate", "bond")
    # bed posts (v8): four M5 x 80 from the top (head counterbored in the plate), a jam nut under the plate, POST_FREE of
    # free screw, a jam nut on the arm, the end in a T-nut in the arm's top slot. The two nuts on each post are the
    # levelling adjustment (set once at assembly, +/-2 mm of thread to spare); the free length bends as the hot plate grows.
    for i, (x, y) in enumerate(BED_MOUNTS):
        arm = f"bed_arm_{'left' if x < 0 else 'right'}"
        add_screw(d, f"bed_post_{i}", "M5", 80, at=(x, y, Z_BED + T_BED - POST_CB), body="zbody", clamps=("bed_plate",))
        d.bom_extra("TNUT-2020-M5", 1, 0.15)
        add_nut(d, f"bed_post_{i}_nut_top", "M5", at=(x, y, Z_BED), direction=(0, 0, -1), body="zbody", screw=f"bed_post_{i}")
        add_nut(d, f"bed_post_{i}_nut_arm", "M5", at=(x, y, Z_FL), direction=(0, 0, 1), body="zbody", screw=f"bed_post_{i}")
        d.join(f"bed_post_{i}_nut_arm", arm, "clamp")
        d.join(f"bed_post_{i}_nut_top", "bed_plate", "clamp")
    # bed tie: locates the plate at the rear centre
    d.add("bed_tie", bed_tie_shape(), material="steel", body="zbody", process="sheet")
    for i, x in enumerate(TIE_X):
        add_screw(d, f"bed_tie_screw_{i}", "M3", 10, at=(x, TIE_Y, Z_BED + T_BED - TIE_CB), body="zbody", clamps=("bed_plate", "bed_tie"))
        add_nut(d, f"bed_tie_nut_{i}", "M3", at=(x, TIE_Y, Z_BED - TIE_T), direction=(0, 0, -1), body="zbody", screw=f"bed_tie_screw_{i}")
        add_screw(d, f"bed_tie_bscrew_{i}", "M3", 12, at=(x, Y_PF - TIE_T, TIE_Z), direction=(0, 1, 0), body="zbody",
                  clamps=("bed_tie", "back_plate"))
        add_nut(d, f"bed_tie_bnut_{i}", "M3", at=(x, Y_CAR, TIE_Z), direction=(0, 1, 0), body="zbody", screw=f"bed_tie_bscrew_{i}")
    # ---- Z drive (v8): ONE motor, closed 6 mm GT2 belt, three T8 x 2 screws. Each screw stands in two 608 bearings; the
    # pulley's hub rests on the upper bearing's inner ring and carries the screw's load into it (no coupler in the load path).
    d.add("z_drive_mount", z_drive_mount_shape(), material=HOT, process="printed", meta={"print_up": "-Z"})
    for i, x in enumerate(DM_FOOT_X):
        add_screw(d, f"z_drive_mount_bolt_{i}", "M5", 16, at=(x, UP_Y, 28.0), threads_into="frame_bot_back", tnut=True,
                  clamps=("z_drive_mount",))
    for i, x in enumerate(DM_REAR_X):
        add_screw(d, f"z_drive_mount_rbolt_{i}", "M5", 8, at=(x, LS_Y + 4.0, 10.0), direction=(0, -1, 0), threads_into="frame_bot_back",
                  tnut=True, clamps=("z_drive_mount",))
    place(d, "z_motor", nema17(MOTOR_L), Location((ZM_X, LS_Y, Z_MF), (0, 0, -90)))    # connector to the front, under the idler tab
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"z_motor_screw_{i}", "M3", 8, at=(ZM_X + x, LS_Y + y, Z_SLAB), threads_into="z_motor",
                  clamps=("z_drive_mount",))
    place(d, "z_pulley_m", gt2_pulley(20, bore=5.0, belt_width=6.0), Location((ZM_X, LS_Y, Z_BT)))
    d.join("z_pulley_m", "z_motor", "set_screw")
    screws = [("", 0.0, LS_Y, 20.0, "z_drive_mount")]
    for sx, tag in ((-1, "_fl"), (1, "_fr")):
        d.add(f"z_pedestal{tag}", z_pedestal_shape(sx), material=COOL, process="printed", meta={"print_up": "+Z"})
        for i, dy in enumerate((-PED_EAR, PED_EAR)):
            add_screw(d, f"z_pedestal{tag}_bolt_{i}", "M5", 16, at=(sx * FS_X, FS_Y + dy, Z_TRAY + 8.0),
                      threads_into=f"frame_bot_{'left' if sx < 0 else 'right'}", tnut=True,
                      clamps=(f"z_pedestal{tag}", "electronics_tray"))
        screws.append((tag, sx * FS_X, FS_Y, Z_TRAY, f"z_pedestal{tag}"))
    for tag, x, y, z0, seat in screws:
        place(d, f"leadscrew{tag}", leadscrew_t8(Z_SCREW_L, lead=2.0), Location((x, y, z0 + 1.0)))
        place(d, f"z_bearing{tag}_lo", bearing("608"), Location((x, y, z0 + 3.5)))
        place(d, f"z_bearing{tag}_hi", bearing("608"), Location((x, y, Z_BT - 3.5)))
        place(d, f"z_pulley{tag}", gt2_pulley(20, bore=8.0, belt_width=6.0), Location((x, y, Z_BT)))
        for lv in ("lo", "hi"):
            d.join(f"z_bearing{tag}_{lv}", seat, "seated in its pocket")
            d.join(f"leadscrew{tag}", f"z_bearing{tag}_{lv}", "clamp")
        d.join(f"z_pulley{tag}", f"leadscrew{tag}", "set_screw")
    # tensioner: a toothed idler on the belt's back between the right front screw and the motor, on an M5 bolt in a
    # slot of the mount's tab (6 mm bought spacer under it). It also wraps the belt 140 degrees round the motor pulley.
    tx, ty = ZT_XY
    place(d, "z_idler_spacer", spacer_round("M5", 6.0, "aluminium"), Location((tx, ty, Z_SLAB)))
    place(d, "z_idler", gt2_idler(20, belt_width=6.0), Location((tx, ty, Z_SLAB + 6.0)))
    add_screw(d, "z_idler_bolt", "M5", 25, at=(tx, ty, Z_MF), direction=(0, 0, 1), clamps=("z_drive_mount", "z_idler_spacer"))
    add_nut(d, "z_idler_nut", "M5", at=(tx, ty, Z_SLAB + 6.0 + 8.5), direction=(0, 0, 1), screw="z_idler_bolt", standard="din934")
    d.join("z_idler", "z_idler_bolt", "axle")
    d.join("z_idler_spacer", "z_drive_mount", "clamp")

    # ================= Y axis ====================================================
    zp0, zp1 = Z_PLATE, Z_PLATE + T_YP
    X_ES_X0 = -TPX - TX - ES_TRIG             # X switch origin (its trigger point is ES_TRIG further in +X)
    X_ES_Y0 = YB0 + X_ES_Y - ES_SIDE
    PC = YB0 - 5.25                           # Y belt anchor centre
    YA0, YA1 = PC + BELT_SLOTS[0] - SLOT_W / 2, PC + BELT_SLOTS[-1] + SLOT_W / 2    # where each belt end leaves the plate
    for sx, n in ((-1, "left"), (1, "right")):
        yr = place(d, f"y_rail_{n}", mgn12_rail(300), Location((sx * RAIL_X, 0, Z_RAIL), (0, 0, 90)))
        for i, (hx, hy, hz) in enumerate(yr.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"y_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5),
                      threads_into=f"frame_top_{n}", tnut=True)
        place(d, f"y_carriage_{n}", mgn12h_carriage(), Location((sx * RAIL_X, YB0, Z_RAIL), (0, 0, 90)),
              body="ybody", guides="y")
        # v6: flat 3 mm laser-cut steel plates. The beam ends inboard of the guide blocks and hangs under a tongue of
        # each plate on one M5 screw from above (T-nut in the beam's top slot), so the four block screws are plain cap
        # heads on top (no counterbores under the beam: v5's reason for machining these plates) and nothing is driven
        # from below. The outboard end carries the Y belt.
        x_out = YB_X + BWY / 2 + 0.5 + 3.25
        x_in = YP_IN if sx > 0 else -LAND_X[1]            # the left plate's tongue runs on inboard to carry the X endstop's land
        plate = (bx(sx * x_in, sx * x_out, YB0 + YP_NOTCH[1], YB0 + PL_Y1, zp0, zp1)
                 + bx(sx * YP_NOTCH[0], sx * x_out, YB0 + PL_Y0, YB0 + YP_NOTCH[1], zp0, zp1))
        plate += fillet_z(sx * YP_NOTCH[0], YB0 + YP_NOTCH[1], -sx, -1, 2.0, zp0, zp1)
        # Y belt anchor (v6): no clamp part. Each belt end goes down through one slot, up through the next, is folded
        # back on itself and tied with a cable tie; the laser-cut slots themselves locate the belt sideways.
        for dy in BELT_SLOTS:
            plate -= slot_z(sx * YB_X, PC + dy, 0.0, (BWY + 1.0 - SLOT_W) / 2, SLOT_W, zp0, zp1)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(YH3 / 2, T_YP)
        # the beam bolts (v7: two per side) sit in +/-1.5 mm slots across the machine: the gantry takes up the frame's
        # width error, so each Y rail can be set to its own frame rail (the Y belt hardware is on those rails)
        if len(BEAM_BOLT_X) > 1:      # tongue 3 mm longer over the beam only (the X guide block passes behind it)
            plate += bx(sx * (YP_IN - 7.5), sx * YP_IN, YB0 + YP_NOTCH[1], YB0 + 9.5, zp0, zp1)
        for xb in BEAM_BOLT_X:
            plate -= slot_z(sx * xb, YB0, 0.0, 1.5, clearance_hole("M5"), zp0, zp1)
        if sx < 0:
            # land behind the beam for the X endstop (the switch stands on two bought spacers); the land stops short of the tool plate's tab at x = -TX
            plate += bx(LAND_X[0], LAND_X[1], YB0 + PL_Y1, YB0 + LAND_Y1, zp0, zp1)
            plate += fillet_z(LAND_X[0], YB0 + PL_Y1, -1, 1, 2.0, zp0, zp1)
            for dy in (-7.5, 7.5):       # the X switch's two screws (through holes: nuts underneath)
                plate -= Pos(X_ES_X0 - 4.2, X_ES_Y0 + dy, Z_PLATE + T_YP / 2) * Cylinder(SH3 / 2, T_YP)
        d.add(f"y_plate_{n}", plate, material="steel", body="ybody", process="sheet")
        for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
            add_screw(d, f"y_plate_{n}_screw_{i}", "M3", 6, at=(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP),
                      body="ybody", threads_into=f"y_carriage_{n}")
        for i, xb in enumerate(BEAM_BOLT_X):
            add_screw(d, f"beam_bolt_{n}" + ("" if i == 0 else f"_{i}"), "M5", 8, at=(sx * xb, YB0, zp1), body="ybody",
                      threads_into="x_beam", tnut=True, clamps=(f"y_plate_{n}",))
    # ================= X axis ====================================================
    # v6: the rail is on the REAR face of the beam, so the guide block's mounting face is vertical
    place(d, "x_beam", extrusion_2020(BEAM_L), Location((0, YB0, Z_BEAM)), body="ybody")
    rear = lambda x: Location(Plane(origin=(x, YB0 + 10.0, Z_BEAM), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    xr = place(d, "x_rail", mgn12_rail(250), rear(0.0), body="ybody")
    for i, (hx, hy, hz) in enumerate(xr.meta["interfaces"]["mount_holes_m3"][::RAIL_SCREW_STEP]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy + 3.5, hz), direction=(0, -1, 0), body="ybody",
                  threads_into="x_beam", tnut=True)
    # v7: the rail's datum. Two identical laser-cut 3 mm steel stops on the beam's rear face, one beyond each end of
    # the guide block's travel. Each stop's top edge sits against the underside of the Y plate's tongue (the face the
    # beam top sits against), and a finger reaches under the rail: the rail is laid on the two fingers (gravity holds
    # it there) while its screws are tightened. Rail height = one laser-cut profile below the Y plates, no slot play.
    if RAIL_STOPS:
        f0, b0, n0, b1 = STOP_X
        for sx, n in ((-1, "left"), (1, "right")):
            y0, y1 = YB0 + 10.0, YB0 + 13.0
            st = bx(sx * b0, sx * b1, y0, y1, Z_BEAM - 10.0, Z_PLATE)
            st -= bx(sx * (b0 - 1.0), sx * n0, y0, y1, Z_BEAM + 1.0, Z_PLATE + 1.0)       # clear of the X switch's screw and nut
            st += bx(sx * f0, sx * b0, y0, y1, Z_BEAM - 10.0, Z_BEAM - 6.0)               # finger under the rail
            st -= Pos(sx * (n0 + b1) / 2, (y0 + y1) / 2, Z_BEAM) * ycyl(clearance_hole("M5") / 2, 3.0)
            d.add(f"x_rail_stop_{n}", st, material="steel", body="ybody", process="sheet")
            add_screw(d, f"x_rail_stop_{n}_bolt", "M5", 8, at=(sx * (n0 + b1) / 2, y1, Z_BEAM), direction=(0, -1, 0),
                      body="ybody", threads_into="x_beam", tnut=True, clamps=(f"x_rail_stop_{n}",))
    place(d, "x_carriage", mgn12h_carriage(), rear(0.0), body="xbody", guides="x")
    # ---- toolhead: guide block -> 8 mm plate -> Roto. Belt block, probe and fan carrier hang on the same plate.
    yf, yrr = YB0 + R_TPF, YB0 + R_TPR
    d.add("tool_plate", tool_plate_shape(), material="al6061", body="xbody", process="machined")
    for i, (x, z) in enumerate([(-10, -10), (10, -10), (-10, 10), (10, 10)]):
        add_screw(d, f"tool_screw_{i}", "M3", 8, at=(x, yrr - CB, Z_BEAM + z), direction=(0, -1, 0), body="xbody",
                  threads_into="x_carriage", clamps=("tool_plate",))
    place(d, "extruder", extruder_roto(), Location(ROTO_O), body="xbody",
          process="purchased")   # the automatic rule reads "extruder" as saw-cut extrusion
    for i, (hx, hy, hz) in enumerate(d.get("extruder").meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"extruder_screw_{i}", "M3", 45, at=(hx, yrr + ROTO_W, hz), direction=(0, -1, 0), body="xbody",
                  threads_into="tool_plate", clamps=("extruder",))
    # Revo hot side: screws finger-tight into the Roto (its thread and 0.7 mm of its seat are inside the Roto's solid);
    # turned so the HeaterCore's leads leave to the rear left, away from the probe and the fan carrier
    seat = d.get("extruder").meta["interfaces"]["hotend_seat"][0]
    place(d, "hotend", hotend_revo(40, 24.0, 0.4), Location(tuple(seat), (0, 0, 100)), body="xbody")
    d.allow_overlap("hotend", "extruder")
    d.join("hotend", "extruder", "clamp")
    # bed probe (catalogue part) clamped by its own two nuts in the printed arm on the plate's left tab
    d.add("probe_arm", probe_arm_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "+Z"})
    for i, (x, z) in enumerate(ARM_SCREWS):
        add_screw(d, f"probe_arm_screw_{i}", "M3", 16, at=(x, yrr + ARM_FL, Z_BEAM + z), direction=(0, -1, 0), body="xbody",
                  threads_into="tool_plate", clamps=("probe_arm",))
    place(d, "bed_probe", probe_omron_e2e(PRB_MODEL, clamp=PRB_CLAMP), Location((PRB_X, YB0 + PRB_Y, Z_PRB), (0, 0, PRB_TURN)), body="xbody")
    d.join("bed_probe", "probe_arm", "clamped by its two nuts")
    d.add("probe_key", probe_key_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "+Z"})
    d.join("probe_key", "bed_probe", "clamped by its two nuts")
    # part-cooling fan behind the Roto on the printed duct. 24 V fan on the board's 24 V fan output (see the docstring)
    d.add("part_duct", part_duct_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "-Y"})
    for i, (x, z) in enumerate(FC_SCREWS):
        add_screw(d, f"part_duct_screw_{i}", "M3", 16, at=(x, yf, Z_BEAM + z), direction=(0, 1, 0), body="xbody",
                  clamps=("tool_plate", "part_duct"))
        add_nut(d, f"part_duct_nut_{i}", "M3", at=(x, yrr + FC_FL - NUT_SLOT, Z_BEAM + z), direction=(0, 1, 0),
                body="xbody", screw=f"part_duct_screw_{i}")
    place(d, "part_fan", fan(30), Location(Plane(origin=(PFAN[0], YB0 + PFAN[1], Z_BEAM + PFAN[2]), x_dir=(1, 0, 0), z_dir=(0, 1, 0))),
          body="xbody")
    for i, sx in enumerate((-12.0, 12.0)):
        add_screw(d, f"part_fan_screw_{i}", "M3", 16, at=(PFAN[0] + sx, YB0 + PFAN[1] + 5.0, Z_BEAM + PFAN[2] - 12.0),
                  direction=(0, -1, 0), body="xbody", clamps=("part_fan", "part_duct"))
        add_nut(d, f"part_fan_nut_{i}", "M3", at=(PFAN[0] + sx, YB0 + FC_LUG_Y + PLEN - FAN_LUG, Z_BEAM + PFAN[2] - 12.0), direction=(0, -1, 0),
                body="xbody", screw=f"part_fan_screw_{i}")
    # ================= X drive ===================================================
    d.add("x_belt_block", belt_block_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "-Y"})
    for i, (x, z) in enumerate(BLK_SCREWS):
        add_screw(d, f"x_belt_block_screw_{i}", "M3", 16, at=(x, yrr - CB, Z_BEAM + z), direction=(0, -1, 0), body="xbody",
                  clamps=("tool_plate", "x_belt_block"))
        add_nut(d, f"x_belt_block_nut_{i}", "M3", at=(x, YB0 + BLK_NUT_Y, Z_BEAM + z), direction=(0, -1, 0), body="xbody",
                screw=f"x_belt_block_screw_{i}")
    # motor and idler on 3 mm laser-cut steel plates on the beam's FRONT face (T-nuts in its front slot): the beam
    # locates both ends of the belt path. Motor in front of the plate, shaft to the rear, pulley over the beam top.
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
    d.add("x_motor_mount", mm, material="steel", body="ybody", process="sheet")
    place(d, "x_motor", nema17(34), fwd(XM_X, yb_f, XD_Z), body="ybody")
    place(d, "x_pulley", gt2_pulley(20, belt_width=BWX), fwd(XM_X, yb_r + X_PG, XD_Z), body="ybody")
    k = 0
    for x in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"x_motor_screw_{k}", "M3", 6, at=(XM_X + x, yb_r, XD_Z + z), direction=(0, -1, 0),
                      body="ybody", threads_into="x_motor", clamps=("x_motor_mount",)); k += 1
    for i, x in enumerate(X_MOUNT_BOLTS):
        add_screw(d, f"x_motor_mount_bolt_{i}", "M5", 8, at=(XM_X + x, yb_f, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_motor_mount",))
    d.join("x_pulley", "x_motor", "set_screw")
    # X idler and belt tensioner: the idler runs on an M5 through-bolt with a bought 9 mm spacer on a second plate.
    # With that plate's two T-nut screws slack it slides along the beam; an M3 jack screw in a printed anchor block
    # (bolted to the same slot, hooked over the beam top) pushes it outward, 0.5 mm per turn.
    im = bx(XI_X - 25.0, XI_X + 25.0, yb_f, yb_r, Z_BEAM - 8.0, XD_Z + 12.0)
    im -= Pos(XI_X, (yb_f + yb_r) / 2, XD_Z) * ycyl(clearance_hole("M5") / 2, MT)
    for x in X_MOUNT_BOLTS:
        im -= Pos(XI_X + x, (yb_f + yb_r) / 2, Z_BEAM) * ycyl(clearance_hole("M5") / 2, MT)
    d.add("x_idler_mount", im, material="steel", body="ybody", process="sheet")
    for i, x in enumerate(X_MOUNT_BOLTS):
        add_screw(d, f"x_idler_mount_bolt_{i}", "M5", 8, at=(XI_X + x, yb_f, Z_BEAM), direction=(0, 1, 0), body="ybody",
                  threads_into="x_beam", tnut=True, clamps=("x_idler_mount",))
    place(d, "x_idler_spacer", spacer_round("M5", X_SP, "aluminium"), fwd(XI_X, yb_r, XD_Z), body="ybody")
    place(d, "x_idler", gt2_idler(20, belt_width=BWX), fwd(XI_X, yb_r + X_SP, XD_Z), body="ybody")
    add_screw(d, "x_idler_bolt", "M5", 30, at=(XI_X, yb_f, XD_Z), direction=(0, 1, 0), body="ybody",
              clamps=("x_idler_mount", "x_idler_spacer"))
    add_nut(d, "x_idler_nut", "M5", at=(XI_X, yb_r + X_SP + I_H(BWX), XD_Z), direction=(0, 1, 0), body="ybody", screw="x_idler_bolt")
    d.join("x_idler", "x_idler_bolt", "axle")
    d.join("x_idler_spacer", "x_idler_mount", "clamp")
    if X_JACK:
        XT0, XT1 = XI_X - 25.0 - 19.0, XI_X - 25.0 - 5.0          # anchor block, inboard of the idler plate
        XT_Z = Z_BEAM + 15.0                                       # jack screw height: in the hook, on the plate's mid-plane
        xta = bx(XT0, XT1, yb_r - 12.0, yb_r, Z_BEAM - 10.0, Z_BEAM + 10.0)
        xta += bx(XT0, XT1, yb_r - 12.0, yb_r + 6.0, Z_BEAM + 10.0, Z_BEAM + 20.0)          # hooks 6 mm over the beam top
        xta -= Pos((XT0 + XT1) / 2, yb_r - 6.0, Z_BEAM) * ycyl(PH5 / 2, 12.0)
        xta -= Pos((XT0 + XT1) / 2, yb_r - MT / 2, XT_Z) * xcyl(PH3 / 2, XT1 - XT0)
        xta -= hex_pocket_x(XT1, yb_r - MT / 2, XT_Z, NUT_POCKET)
        d.add("x_tension_anchor", xta, material=COOL, body="ybody", process="printed", meta={"print_up": "+X"})
        add_screw(d, "x_tension_anchor_bolt", "M5", 16, at=((XT0 + XT1) / 2, yb_r - 12.0, Z_BEAM), direction=(0, 1, 0),
                  body="ybody", threads_into="x_beam", tnut=True, clamps=("x_tension_anchor",))
        add_screw(d, "x_tension_screw", "M3", 25, at=(XI_X - 25.0 - 25.0, yb_r - MT / 2, XT_Z), direction=(1, 0, 0), body="ybody",
                  clamps=("x_tension_anchor",))
        add_nut(d, "x_tension_nut", "M3", at=(XT1 - NUT_POCKET, yb_r - MT / 2, XT_Z), direction=(1, 0, 0), body="ybody",
                screw="x_tension_screw")
        d.join("x_tension_nut", "x_tension_anchor", "clamp")      # captive in its pocket
    # X endstop on the left Y plate's land, behind the beam
    xsw = place(d, "x_endstop", endstop_switch(),
                Location(Plane(origin=(X_ES_X0, X_ES_Y0, zp1 + ES_SP_X), x_dir=(0, -1, 0), z_dir=(0, 0, 1))), body="ybody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"x_endstop_spacer_{i}", spacer_round("M3", ES_SP_X), Location((hx, hy, zp1)), body="ybody")
        add_screw(d, f"x_endstop_screw_{i}", "M3", 16, at=(hx, hy, hz + 1.6), body="ybody",
                  clamps=("x_endstop", f"x_endstop_spacer_{i}", "y_plate_left"))
        add_nut(d, f"x_endstop_nut_{i}", "M3", at=(hx, hy, zp0), direction=(0, 0, -1), body="ybody", screw=f"x_endstop_screw_{i}")
    # ================= Y drives: vertical belt planes outboard of both top side rails =====
    # Mounts are 3 mm laser-cut steel sheet. Belt tensioners: each motor mount is held by two M5 screws in T-nuts,
    # so with them slack it slides along the rail; an M3 jack screw in a printed anchor block (bolted to the same
    # slot, hooked under the rail) pushes it backwards on a lug. v6: left and right are mirror images.
    xf = FX / 2
    Y_MOUNT_BOLTS = (135.0, 165.0)       # v6: two per mount (three in v5)
    AN_Y0, AN_Y1, LUG_Y0, TS_Z = 105.0, 119.0, 125.0, FZ - 15.0
    side = lambda x, y, z, sg: Location(Plane(origin=(x, y, z), x_dir=(0, 1, 0), z_dir=(sg, 0, 0)))

    def motor_mount(sg, zc):
        xa, xb = sorted((sg * xf, sg * (xf + MT)))
        xm = (xa + xb) / 2
        m = (Pos(xm, 152.5, FZ) * Box(MT, 55, 20)
             + Pos(xm, (170 + YM_Y + 23) / 2, (FZ - 10 + zc + 23) / 2) * Box(MT, YM_Y + 23 - 170, zc + 23 - FZ + 10)
             + Pos(xm, LUG_Y0 + 6.0, TS_Z) * Box(MT, 12.0, 10.0))          # lug for the tension screw
        m += fillet_x(170.0, FZ + 10, -1, 1, 3.0, xa, xb)
        m += fillet_x(LUG_Y0 + 12.0, FZ - 10, 1, -1, 2.0, xa, xb)
        m -= Pos(xm, YM_Y, zc) * xcyl(11.5, MT)
        for y in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                m -= Pos(xm, YM_Y + y, zc + z) * xcyl(SH3 / 2, MT)
        for y in Y_MOUNT_BOLTS:
            m -= Pos(xm, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
        return m

    def tensioner(sg, tag, rail):
        """Printed anchor block + M3x25 jack screw (captive nut in the block's rear face) for one Y motor mount."""
        xs = sg * (xf + MT / 2)       # jack screw on the mid-plane of the sheet lug
        a = Pos(sg * (xf + 6.0), (AN_Y0 + AN_Y1) / 2, FZ) * Box(12.0, AN_Y1 - AN_Y0, 20.0)
        a += Pos(sg * (xf + 3.0), (AN_Y0 + AN_Y1) / 2, TS_Z) * Box(18.0, AN_Y1 - AN_Y0, 10.0)     # hooks 6 mm under the rail
        a -= Pos(sg * (xf + 6.0), (AN_Y0 + AN_Y1) / 2, FZ) * xcyl(PH5 / 2, 12.0)
        a -= Pos(xs, (AN_Y0 + AN_Y1) / 2, TS_Z) * ycyl(PH3 / 2, AN_Y1 - AN_Y0)
        a -= hex_pocket_y(xs, AN_Y1, TS_Z, NUT_POCKET)
        d.add(f"y_tension_anchor{tag}", a, material=COOL, process="printed", meta={"print_up": "-X" if sg > 0 else "+X"})
        add_screw(d, f"y_tension_anchor{tag}_bolt", "M5", 16, at=(sg * (xf + 12.0), (AN_Y0 + AN_Y1) / 2, FZ),
                  direction=(-sg, 0, 0), threads_into=rail, tnut=True, clamps=(f"y_tension_anchor{tag}",))
        add_screw(d, f"y_tension_screw{tag}", "M3", 25, at=(xs, LUG_Y0 - 25.0, TS_Z), direction=(0, 1, 0),
                  clamps=(f"y_tension_anchor{tag}",))
        add_nut(d, f"y_tension_nut{tag}", "M3", at=(xs, AN_Y1 - NUT_POCKET, TS_Z), direction=(0, 1, 0),
                screw=f"y_tension_screw{tag}")
        d.join(f"y_tension_nut{tag}", f"y_tension_anchor{tag}", "clamp")      # captive in its pocket

    for sg, tag, n in ((1, "", "right"), (-1, "_l", "left")):
        rail = f"frame_top_{n}"
        d.add(f"y_motor_mount{tag}", motor_mount(sg, Z_YC), material="steel", process="sheet")
        place(d, f"y_motor{tag}", nema17(48), side(sg * xf, YM_Y, Z_YC, sg))
        # v7: hub outboard, toothed end towards the motor (belt pull 11.75 mm from the mounting face)
        place(d, f"y_pulley{tag}", gt2_pulley(20, belt_width=BWY),
              Location(Plane(origin=(sg * (YB_X + P_BC(BWY)), YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(-sg, 0, 0))))
        k = 0
        for y in (-15.5, 15.5):
            for z in (-15.5, 15.5):
                add_screw(d, f"y_motor{tag}_screw_{k}", "M3", 6, at=(sg * (xf + MT), YM_Y + y, Z_YC + z), direction=(-sg, 0, 0),
                          threads_into=f"y_motor{tag}"); k += 1
        for i, y in enumerate(Y_MOUNT_BOLTS):
            add_screw(d, f"y_motor_mount{tag}_bolt_{i}", "M5", 8, at=(sg * (xf + MT), y, FZ), direction=(-sg, 0, 0),
                      threads_into=rail, tnut=True)
        d.join(f"y_pulley{tag}", f"y_motor{tag}", "set_screw")
        tensioner(sg, tag, rail)
        # idler mount at the front, in front of the Y plate's sweep: flat plate; the idler runs on an M5 through-bolt
        # with a bought 6 mm aluminium spacer and a nut on the inside face
        xa, xb = sorted((sg * xf, sg * (xf + MT)))
        xm = (xa + xb) / 2
        im = bx(xa, xb, YI_Y - 15.5, YI_Y + 15.0, FZ - 10.0, Z_YC + 9.0)
        im -= Pos(xm, YI_Y, Z_YC) * xcyl(clearance_hole("M5") / 2, MT)
        for y in (YI_Y - 9.0, YI_Y + 6.0):
            im -= Pos(xm, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
        if sg > 0:
            # Y endstop (v6): on the inner face of the right idler mount, which is taller at its rear end for it; the
            # front edge of the right Y plate presses the lever at y = -TY. Lever switch on two bought 4 mm spacers,
            # M3x16 from the outside (their heads stay clear of the belt), nuts on the board.
            ysw = place(d, "y_endstop", endstop_switch(),
                        Location(Plane(origin=(xf - ES_SP, YB0 + PL_Y0 - TY - ES_TRIG, Z_PLATE + T_YP / 2 + ES_SIDE),
                                       x_dir=(0, 0, 1), z_dir=(-1, 0, 0))))
            ys_holes = ysw.meta["interfaces"]["mount_holes_m3"]
            y_r0, z_r1 = ys_holes[0][1] - 5.5, max(h[2] for h in ys_holes) + 5.0
            y_r1 = ys_holes[0][1] + 5.2
            im += bx(xa, xb, y_r0, y_r1, Z_YC + 9.0, z_r1)
            im += bx(xa, xb, YI_Y + 14.0, y_r1, FZ - 10.0, Z_YC + 9.0)     # the lower switch hole keeps 3.4 mm to the rear edge
            im += fillet_x(y_r0, Z_YC + 9.0, -1, 1, 2.0, xa, xb)
            for hx, hy, hz in ys_holes:
                im -= Pos(xm, hy, hz) * xcyl(SH3 / 2, MT)
        d.add(f"y_idler_mount{tag}", im, material="steel", process="sheet")
        for i, y in enumerate((YI_Y - 9.0, YI_Y + 6.0)):
            add_screw(d, f"y_idler_mount{tag}_bolt_{i}", "M5", 8, at=(sg * (xf + MT), y, FZ), direction=(-sg, 0, 0),
                      threads_into=rail, tnut=True)
        place(d, f"y_idler_spacer{tag}", spacer_round("M5", Y_SP, "aluminium"), side(sg * (xf + MT), YI_Y, Z_YC, sg))
        place(d, f"y_idler{tag}", gt2_idler(20, belt_width=BWY), side(sg * (YB_X - I_H(BWY) / 2), YI_Y, Z_YC, sg))
        add_screw(d, f"y_idler{tag}_bolt", "M5", 30, at=(sg * (YB_X + I_H(BWY) / 2), YI_Y, Z_YC), direction=(-sg, 0, 0),
                  clamps=(f"y_idler_spacer{tag}", f"y_idler_mount{tag}"))
        add_nut(d, f"y_idler{tag}_nut", "M5", at=(sg * xf, YI_Y, Z_YC), direction=(-sg, 0, 0), screw=f"y_idler{tag}_bolt")
        d.join(f"y_idler{tag}", f"y_idler{tag}_bolt", "axle")
        d.join(f"y_idler_spacer{tag}", f"y_idler_mount{tag}", "clamp")
    for i, (hx, hy, hz) in enumerate(ys_holes):
        place(d, f"y_endstop_spacer_{i}", spacer_round("M3", ES_SP), Location(Plane(origin=(xf, hy, hz), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
        add_screw(d, f"y_endstop_screw_{i}", "M3", 16, at=(xf + MT, hy, hz), direction=(-1, 0, 0),
                  clamps=("y_idler_mount", f"y_endstop_spacer_{i}", "y_endstop"))
        add_nut(d, f"y_endstop_nut_{i}", "M3", at=(hx - 1.6, hy, hz), direction=(-1, 0, 0), screw=f"y_endstop_screw_{i}")
    # ================= electronics bay: tray across the bottom rails =============
    tray = Pos(0, (TRAY_Y0 + TRAY_Y1) / 2, 20 + T_TRAY / 2) * Box(FX, TRAY_Y1 - TRAY_Y0, T_TRAY)
    grp = ["electronics_tray"]
    # supply at the front left, terminal strip towards the board (+X); the left loom runs behind it
    # v8: the supply lies along Y in the middle (terminals at the rear), so both tray edges are free for the Z pedestals
    psu = place(d, "psu", psu_lrs(PSU_MODEL), Location((-28.0, -30.0, Z_TRAY), (0, 0, -90)))
    # board on 6 mm spacers, long edge along Y: power / heater terminals face the supply, motor connectors face +X
    board = place(d, "control_board", skr_mini_e3_v3(), Location((95.0, -82.0, Z_TRAY + 6.0), (0, 0, -90)))
    host = place(d, "host", raspberry_pi_zero2w(), Location((95.0, 22.0, Z_TRAY + 4.0), (0, 0, 90)))
    # the board is held by four of its five holes (not the one in the middle), the Pi by two opposite corners
    pcbs = [(board, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2, 4)), (host, "mount_holes_m2.5", "M2.5", 12, 4.0, (0, 3))]
    if USE_CUTOFFS:
        relay = place(d, "psu_relay", relay_btt_v12(), Location((-122.0, -36.0, Z_TRAY + 6.0), (0, 0, 90)))
        pcbs.append((relay, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2)))     # v7: three of its four holes
    if USE_MOSFET:
        mos = place(d, "bed_mosfet", mosfet_module(25.0), Location((100.0, 26.0, Z_TRAY + 6.0), (0, 0, 90)))
        pcbs.append((mos, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2)))       # v7: three of its four holes
    tray_bolts = [(sx * RAIL_X, y) for sx in (-1, 1) for y in (-58.0, 72.0)]
    for sx in (-1, 1):       # the Z pedestals' screws pass through the tray into the same slots
        for dy in (-PED_EAR, PED_EAR):
            tray -= Pos(sx * FS_X, FS_Y + dy, 20 + T_TRAY / 2) * Cylinder(clearance_hole("M5") / 2, T_TRAY)
    for x, y in tray_bolts:
        tray -= Pos(x, y, 20 + T_TRAY / 2) * Cylinder(clearance_hole("M5") / 2, T_TRAY)
    for hx, hy, hz in psu.meta["interfaces"]["mount_holes_m4"]:
        tray -= Pos(hx, hy, 20 + T_TRAY / 2) * Cylinder(clearance_hole("M4") / 2, T_TRAY)
    for comp, key, size, _, _, use in pcbs:
        for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][key]):
            if use is not None and i not in use:
                continue
            tray -= Pos(hx, hy, 20 + T_TRAY / 2) * Cylinder(clearance_hole(size) / 2, T_TRAY)
    d.add("electronics_tray", tray, material="al6061", process="sheet")
    for i, (x, y) in enumerate(tray_bolts):
        add_screw(d, f"tray_bolt_{i}", "M5", 8, at=(x, y, Z_TRAY), threads_into=f"frame_bot_{'left' if x < 0 else 'right'}",
                  tnut=True)
    for i, (hx, hy, hz) in enumerate(psu.meta["interfaces"]["mount_holes_m4"]):   # the supply's base holes take 3 mm of screw
        add_screw(d, f"psu_screw_{i}", "M4", 6, at=(hx, hy, 20.0), direction=(0, 0, 1), threads_into="psu")
        grp.append(f"psu_screw_{i}")
    grp.append("psu")
    for comp, key, size, slen, sp, use in pcbs:
        mount_pcb(d, comp.name, comp, key, size, slen, sp, grp, use)
    d.subassemblies["electronics"] = grp
    # mains inlet (switch + fuse) on a 3 mm panel bolted to the outside of the left bottom rail
    IN_Y, IN_Z, XP = 22.0, 60.0, -FX / 2
    panel = Pos(XP - 1.5, IN_Y, 49.0) * Box(3.0, 70.0, 94.0)
    inlet = place(d, "inlet", iec_inlet_c14(FUSE_A),
                  Location(Plane(origin=(XP - 3.0, IN_Y, IN_Z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    # v7: SCHURTER DD11 pattern from the part: 28.1 x 47.1 cut-out, R1 corners, two 3.4 mm holes 56 apart
    cut_x, cut_y = inlet.meta["interfaces"]["cutout"]
    panel -= Pos(XP - 1.5, IN_Y, IN_Z) * Rot(0, 90, 0) * extrude(
        RectangleRounded(cut_y, cut_x, inlet.meta["interfaces"]["cutout_corner_radius"]), 1.5, both=True)
    for hx, hy, hz in inlet.meta["interfaces"]["mount_holes_m3"]:
        panel -= Pos(XP - 1.5, hy, hz) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, 3.0)
    PANEL_BOLTS = (IN_Y - 27.0, IN_Y + 27.0)
    for y in PANEL_BOLTS:
        panel -= Pos(XP - 1.5, y, 10.0) * Rot(0, 90, 0) * Cylinder(clearance_hole("M5") / 2, 3.0)
    d.add("inlet_panel", panel, material="al6061", process="sheet")
    for i, y in enumerate(PANEL_BOLTS):
        add_screw(d, f"inlet_panel_bolt_{i}", "M5", 8, at=(XP - 3.0, y, 10.0), direction=(1, 0, 0),
                  threads_into="frame_bot_left", tnut=True)
    for i, (hx, hy, hz) in enumerate(inlet.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"inlet_screw_{i}", "M3", 16, at=(XP - 5.5, hy, hz), direction=(1, 0, 0), clamps=("inlet", "inlet_panel"))
        add_nut(d, f"inlet_nut_{i}", "M3", at=(XP, hy, hz), direction=(1, 0, 0), screw=f"inlet_screw_{i}")
    # protective-earth stud: M5 screw into a T-nut in the outer slot of the left bottom rail, ring terminals and a star washer under its head
    add_screw(d, "earth_stud", "M5", 8, at=(XP - 2.0, 80.0, 10.0), direction=(1, 0, 0), threads_into="frame_bot_left", tnut=True)
    d.bom_extra("WASHER-M5-STAR", 1, 0.05)
    # bench sub-assemblies: the bed carrier is built on the bench and fitted as a unit
    d.subassemblies["bed_carrier"] = (
        ["back_plate", "front_plate"]
        + [f"nut_block{t}{k}" for t in ("", "_fl", "_fr") for k in [""] + [f"_{kk}_{i}" for kk in ("bolt", "nut") for i in range(4)]]
        + [f"bed_arm_{n}{sfx}" for n in ("left", "right") for sfx in ("", "_bolt", "_bracket", "_bracket_screw", "_bracket_nut",
                                                                      "_fbolt", "_fbracket", "_fbracket_screw", "_fbracket_nut")])
    d.subassemblies["z_drive"] = (["z_drive_mount", "z_motor", "z_pulley_m", "z_idler_spacer", "z_idler", "z_idler_bolt", "z_idler_nut"]
                                  + [f"z_motor_screw_{i}" for i in range(4)])
    # motors on their plates, idlers on theirs and the part fan on its carrier are bench jobs
    d.subassemblies["x_drive"] = ["x_motor_mount", "x_motor", "x_pulley"] + [f"x_motor_screw_{i}" for i in range(4)]
    d.subassemblies["x_idler_unit"] = ["x_idler_mount", "x_idler_spacer", "x_idler", "x_idler_bolt", "x_idler_nut"]
    d.subassemblies["part_cooling"] = (["part_duct", "part_fan"]
                                       + [f"part_fan_{k}_{i}" for k in ("screw", "nut") for i in range(2)])
    for tag in ("", "_l"):
        d.subassemblies[f"y_drive{tag}"] = ([f"y_motor_mount{tag}", f"y_motor{tag}", f"y_pulley{tag}"]
                                            + [f"y_motor{tag}_screw_{i}" for i in range(4)])
    # ================= belts =====================================================
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (-14.0, XB_Y, Z_XL)), ("pulley", "x_pulley", "ccw"),
                                   ("pulley", "x_idler", "ccw"), ("anchor", "xbody", (14.0, XB_Y, Z_XL))],
                        axis=(0, 1, 0), width=BWX, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, YA0, Z_YA)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt_l", [("anchor", "ybody", (-YB_X, YA0, Z_YA)), ("pulley", "y_idler_l", "ccw"),
                                     ("pulley", "y_pulley_l", "ccw"), ("anchor", "ybody", (-YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    # v8 Z belt: closed 6 mm loop round the three screw pulleys and the motor pulley, tensioner idler on its back
    d.belts.append(Belt("z_belt", [("pulley", "z_pulley_fl", "ccw"), ("pulley", "z_pulley_fr", "ccw"), ("pulley", "z_idler", "cw"),
                                   ("pulley", "z_pulley_m", "ccw"), ("pulley", "z_pulley", "ccw")],
                        axis=(0, 0, 1), width=6.0, stock_length=Z_BELT_L, adjust=ZT_SLOT))
    d.bom_extra(f"GT2-BELT-6MM-CLOSED-{Z_BELT_L:g}", 1, 6.0)
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 1, 4.0)    # X belt (prices are estimates)
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 2, 4.0)    # Y belts (v7: 9 mm)

    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY, TY), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX), overtravel=(ES_OT, ES_OT),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_DN, PRINT_Z), overtravel=(0.0, Z_UP),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": ["leadscrew", "leadscrew_fl", "leadscrew_fr"],
                                 "nut": ["z_nut", "z_nut_fl", "z_nut_fr"], "sync": "belt"}))
    # raise the bed, trace a 150 mm square with the nozzle, lower the bed
    d.program = [{"to": {"z": PRINT_Z}},
                 {"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": -75, "y": 75}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 0, "y": 0}},
                 {"to": {"z": 0.0}}]
    nozzle = (0.0, YB0 + HOT_OFF, Z_NOZZLE)
    d.tool_point = ("xbody", nozzle)
    # ================= homing, cables, adjustments ================================
    d.endstops += [{"joint": "x", "switch": "x_endstop", "at": "min"},     # left edge of the tool plate's probe tab
                   {"joint": "y", "switch": "y_endstop", "at": "min"},     # front edge of the right Y plate
                   {"joint": "z", "probe": "bed_probe", "at": "max"}]      # the probe senses the bed plate itself
    build_electrical(d)      # looms; their flexing spans are added to d.cables
    d.adjustments += [
        # Z homes on the probe; the nozzle-to-bed gap is the probe's z_offset in the firmware, set once with a feeler
        # gauge. The Z joint has Z_UP of declared over-travel past the nominal nozzle plane (rail, screw and nut room is
        # a Requirement below), so a bed that was built low can still come up; the probe's face is PRB_H above the
        # nozzle, so even at the end of the over-travel the nominal bed is 0.15 mm short of it.
        Adjustment("probe z_offset in the firmware", "z_offset", range_mm=Z_UP),
        # the four bed screws (heads in the bed's counterbores) compress the silicone columns 0.5 .. 3.5 mm
        Adjustment("bed levelling screws on silicone columns", "bed_level", range_mm=1.5),
        # T-nuts slide across the 6.2 mm slot (+/-1.6 on an M3): left rail set to a straight edge, right rail's
        # screws tightened one by one while the gantry is run along it; the beam's T-nuts absorb the spacing
        Adjustment("y rails on sliding T-nuts", "rail_align", range_mm=1.5, joint="y"),
        Adjustment("z rails on sliding T-nuts", "rail_align", range_mm=1.5, joint="z",
                   note="left rail to a square, right rail tightened while the bed carrier is run up and down on all four blocks"),
        # the nut hangs under the block with NUT_FLOAT radial room; one pin in a radial slot stops it turning
        Adjustment("floating lead screw nut", "float", range_mm=NUT_FLOAT - 0.2, joint="z"),
        Adjustment("x belt: idler plate slides on its T-nuts, M3 jack screw", "belt_tension",
                   range_mm=BELT_ADJ, joint="x"),
        Adjustment("y belts: motor mounts slide on their T-nuts, M3 jack screws", "belt_tension",
                   range_mm=BELT_ADJ, joint="y"),
    ]
    # how to print on this machine: the digital twin runs as a verifier, using the FEA nozzle stiffness below
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"},
                 "print_area": (PRINT_X, PRINT_Y)}
    d.printer["bed_support"] = {"parts": None}      # filled in below, once the part lists exist

    # ================= structure =================================================
    # nozzle-point stiffness of the whole gantry moving structure, toolhead at mid-span (worst case); deflection
    # probed at the nozzle tip. The Roto is in the model as a solid aluminium block (its real housing is not).
    moving = ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate", "extruder", "hotend"]
    y_plate_fix = [("y_plate_left", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6),
                   ("y_plate_right", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6)]
    z_blk = d.get("hotend").meta["interfaces"]["heater_block_box"][0][2]       # underside of the nozzle's block
    block_face = ("hotend", lambda f: abs(f.center().Z - z_blk) < 1e-3)
    for nm, force in (("nozzle_stiffness_y", (0.0, 3.0, -2.0)), ("nozzle_stiffness_x", (3.0, 0.0, -2.0))):
        d.assemblycases.append(AssemblyCase(nm, moving, fixed=y_plate_fix, loaded=block_face, force=force,
                                            probe=nozzle, max_deflection=0.03, min_fos=5.0))
    # bed carrier: payload x3 (plus the bed plate's own weight x3) on the bed, through the columns and arms into the
    # back plate, held where the four blocks sit on their rails
    w_bed = 3.0 * (PAYLOAD_KG + bed_own) * 9.81
    posts = [f"bed_post_{i}{sfx}" for i in range(len(BED_MOUNTS)) for sfx in ("", "_nut_top", "_nut_arm")]
    zcars = [f"z_carriage_{n}_{lvl}" for n in ("left", "right") for lvl in ("lo", "hi")]
    on_rail = lambda f: abs(f.center().Y - (Y_FACE - 8.0)) < 1e-6
    carrier = ["back_plate", "front_plate", "bed_arm_left", "bed_arm_right"] + [f"bed_arm_{n}_{b}" for n in ("left", "right") for b in ("bracket", "fbracket")]
    nblocks = ["nut_block", "nut_block_fl", "nut_block_fr"]
    bed_stack = ["bed_plate", "bed_magnet", "bed"]
    # the parts the bed-support measures mesh: sheet, magnet, plate, posts with their nuts, carrier, blocks, nut blocks
    d.printer["bed_support"] = {"parts": [*bed_stack, *posts, "bed_tie", *carrier, *zcars, *nblocks]}
    on_nut = lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 100
    d.assemblycases.append(AssemblyCase(
        "payload_x3_on_bed", [*bed_stack, *posts, "bed_tie", *carrier, *zcars, *nblocks],
        fixed=[(c, on_rail) for c in zcars] + [(nb, on_nut) for nb in nblocks],
        loaded=("bed", lambda f: abs(f.center().Z - Z_SURF) < 1e-6 and f.area > 1000),
        force=(0.0, 0.0, -w_bed), probe=(PRINT_X / 2, BED_CY - PRINT_Y / 2, Z_SURF), max_deflection=0.3, min_fos=3.0))
    # printed parts under load, with the plastic's properties
    d.loadcases.append(LoadCase(      # lead-screw thrust on the nut block
        "nut_thrust", "nut_block", fixed=lambda f: abs(f.center().Y - Y_CAR) < 1e-6,
        loaded=lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 300,
        force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(      # v8: the same thrust on a front nut block (offset flange)
        "nut_thrust_front", "nut_block_fr", fixed=lambda f: abs(f.center().Y - (Y_FPR - T_FP)) < 1e-6,
        loaded=lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 300,
        force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(      # v8: the whole thrust on ONE front pedestal's upper bearing seat (it carries about a third)
        "z_pedestal_thrust", "z_pedestal_fr", fixed=lambda f: abs(f.center().Z - Z_TRAY) < 1e-6,
        loaded=lambda f: abs(f.center().Z - (Z_BT - 7.0)) < 1e-6,
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.05))
    d.loadcases.append(LoadCase(      # v8: and on the rear screw's seat in the drive mount, held on the rail
        "z_drive_mount_thrust", "z_drive_mount", fixed=lambda f: abs(f.center().Z - 20.0) < 1e-6,
        loaded=lambda f: abs(f.center().Z - (Z_BT - 7.0)) < 1e-6,
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.05))
    d.loadcases.append(LoadCase(      # X belt pull on the printed belt block: 60 N, about twice what the X motor can pull
        "x_belt_pull", "x_belt_block", fixed=lambda f: abs(f.center().Y - (YB0 + R_TPF)) < 1e-6,
        loaded=lambda f: abs(f.center().Z - (Z_XL - 0.75)) < 1e-6 and f.area > 100,     # the belt slot's floor
        force=(60.0, 0.0, 0.0), min_fos=3.0, max_deflection=0.1))

    # ================= heat: bed 60 K above the frame =============================
    # Bed at +60 K, columns half way, carrier and blocks at frame temperature (worst case for differential growth).
    # Blocks held on their rails. The nozzle (cold, on the gantry) does not move, so the change in the gap is the
    # vertical movement of the bed surface under it. Limits: gap within half a 0.2 mm layer (the probe offset is set
    # with the bed hot, so this is margin on top), bow below 0.1 mm.
    d.thermalcases.append(ThermalCase(
        "bed_heated_60K", [*bed_stack, *posts, "bed_tie", *carrier, *zcars],
        fixed=[(c, on_rail) for c in zcars],
        temps={"bed": 60.0, "bed_magnet": 60.0, "bed_plate": 60.0, **{c: 30.0 for c in posts}, "bed_tie": 30.0, "*": 0.0},
        # a probe snaps to the nearest meshed point, and the nozzle is not in this model, so the "nozzle" reference is
        # put on a held rail face: it must report zero movement
        probes={"nozzle": (-UP_X, Y_FACE - 8.0, ZC1), "bed": (0.0, YB0 + HOT_OFF, Z_SURF)},
        gaps={"nozzle gap": ("nozzle", "bed", "z", 0.1)}, flatness=("bed", "z", 0.1)))

    # ================= requirements ==============================================
    def jr(dd, name):
        return next(j for j in dd.joints if j.name == name)

    def motors_of(dd, name):   # a joint may have several motors (dual Y drive); same check on each
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
        bb = dd.get("bed").shape.bounding_box()
        xr_, yr_ = jr(dd, "x").range, jr(dd, "y").range
        m = min(nx + xr_[0] - bb.min.X, bb.max.X - (nx + xr_[1]), ny + yr_[0] - bb.min.Y, bb.max.Y - (ny + yr_[1]))
        return m >= 0, f"smallest nozzle-to-bed-edge margin over the XY travel: {m:.1f} mm"
    d.requirements.append(Requirement("nozzle stays over the bed plate for all XY positions", nozzle_over_bed))

    def bed_gap(dd):
        top = dd.get("bed").shape.bounding_box().max.Z
        gap = nozzle_tip(dd)[2] - (top + PRINT_Z)
        beyond = jr(dd, "z").range[1] - PRINT_Z
        return (-1e-9 <= gap <= 0.2 + 1e-9 and beyond >= 0,
                f"nozzle tip is {gap:.2f} mm above the bed surface with the bed {PRINT_Z:g} mm up")
    # v2's twin showed that any gap above the first layer height makes the first layer unreachable.
    d.requirements.append(Requirement("bed can reach the nozzle: 0-0.2 mm gap at the top of the print height", bed_gap))
    d.requirements.append(Requirement("bed carries the 1.0 kg payload as mass", lambda dd: (
        (m := dd.get("bed_plate").mass()) >= dd.get("bed_plate").shape.volume * MATERIALS["al_mic6"].density * 1e-9 + PAYLOAD_KG - 1e-9,
        f"bed plate + payload {m:.3f} kg")))

    def speeds(dd):
        s = {n: (jr(dd, n).max_speed, jr(dd, n).max_accel) for n in "xyz"}
        ok = all(s[n][0] >= V_XY and s[n][1] >= A_XY for n in "xy") and s["z"][0] >= V_Z and s["z"][1] >= A_Z
        return ok, str(s)
    d.requirements.append(Requirement("X/Y 250 mm/s at 4000 mm/s^2, Z 12 mm/s at 200 mm/s^2", speeds))
    d.requirements.append(Requirement("drive margin >= 3x on every axis", lambda dd, m: (
        set(m["motion"]["drives"]) == {"x", "y", "z"} and all(v["margin"] >= MARGIN for v in m["motion"]["drives"].values()),
        str({k: v["margin"] for k, v in m["motion"]["drives"].items()}))))
    d.requirements.append(Requirement("all three belts routed: constant length, clear of parts", lambda dd, m: (
        all(b in m["motion"].get("belts", {}) and m["motion"]["belts"][b]["clear_of_parts"]
            and m["motion"]["belts"][b]["length_change_over_travel_mm"] <= 0.3 for b in ("x_belt", "y_belt", "y_belt_l")),
        str(m["motion"].get("belts")))))

    def rail_margins(dd):
        out = {}
        rails = {"y_carriage_left": "y_rail_left", "y_carriage_right": "y_rail_right", "x_carriage": "x_rail",
                 **{f"z_carriage_{s_}_{lv}": f"z_rail_{s_}" for s_ in ("left", "right") for lv in ("lo", "hi")}}
        for n, rail in rails.items():
            ax = n[0].upper()
            cb, rb = dd.get(n).shape.bounding_box(), dd.get(rail).shape.bounding_box()
            lo, hi = jr(dd, ax.lower()).mechanical_range
            out[n] = round(min(getattr(cb.min, ax) + lo - getattr(rb.min, ax), getattr(rb.max, ax) - getattr(cb.max, ax) - hi), 2)
        return min(out.values()) >= 5.0, str(out)
    d.requirements.append(Requirement("every carriage stays >= 5 mm inside its rail ends over the mechanical travel (over-travel included)", lambda dd: rail_margins(dd)))

    def z_beyond(dd):
        ok_rail, detail = rail_margins(dd)
        left = {t: dd.get(f"leadscrew{t}").shape.bounding_box().max.Z - (dd.get(f"z_nut{t}").shape.bounding_box().max.Z + PRINT_Z + Z_UP)
                for t in ("", "_fl", "_fr")}
        return ok_rail and min(left.values()) >= 5.0, f"with Z {Z_UP:g} mm past the nozzle plane: {detail}; lead screws {min(left.values()):.1f} mm above their nuts"
    d.requirements.append(Requirement(f"Z rails, blocks, screw and nut allow {Z_UP:g} mm of travel beyond the nominal nozzle plane", z_beyond))
    d.requirements.append(Requirement("Z rails and lead screw end below the top back extrusion (no rubbing)", lambda dd: (
        max(t := [dd.get(n).shape.bounding_box().max.Z for n in ("z_rail_left", "leadscrew", "leadscrew_fl", "leadscrew_fr")]) < FZ - 10,
        f"rail top {t[0]:.1f}, screw tops {t[1]:.1f} / {t[2]:.1f} / {t[3]:.1f} vs extrusion underside {FZ - 10:.1f}")))
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(mn).sku.startswith("NEMA17") and dd.get(mn).meta["catalog"] for n in "xyz" for mn in motors_of(dd, n)),
        str({n: [dd.get(mn).sku for mn in motors_of(dd, n)] for n in "xyz"}))))
    d.requirements.append(Requirement("Z lead screw self-locking (efficiency < 0.5)", lambda dd: (
        all(dd.get(f"leadscrew{t}").ratings["efficiency"] < 0.5 for t in ("", "_fl", "_fr")), f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    # ---- v6 stated targets that can be computed here (cost and assembly time: see docs/PRINTER_V6.md) ----
    d.requirements.append(Requirement(f"target: at most {MAX_PARTS} parts", lambda dd: (
        len(dd.components) <= MAX_PARTS, f"{len(dd.components)} parts")))
    d.requirements.append(Requirement(f"target: direct drive, at most {MAX_TOOLHEAD_KG:g} kg moving in X", lambda dd: (
        dd.get("extruder").body == "xbody" and (m := sum(c.mass() for c in dd.components if c.body == "xbody")) <= MAX_TOOLHEAD_KG,
        f"{m:.3f} kg on the X guide block, block included")))
    d.requirements.append(Requirement(f"target: both Y belts within 1 mm of plane in >= {MIN_BELT_IN_PLANE:.0%} of builds", lambda dd, m: (
        all(m["tolerance"]["belts"][b]["p_within_1mm"] >= MIN_BELT_IN_PLANE for b in ("y_belt", "y_belt_l")),
        str({b: m["tolerance"]["belts"][b]["p_within_1mm"] for b in ("y_belt", "y_belt_l")}))))
    d.requirements.append(Requirement("the bed probe switches before the nozzle touches for every unit, and over-travel ends short of its face", lambda dd, m: (
        (pz := m["subsystems"]["homing"]["z"])["z_offset_range_mm"][0] > 0.3 and Z_UP < PRB_H,
        f"nozzle {pz['z_offset_range_mm'][0]:.2f} .. {pz['z_offset_range_mm'][1]:.2f} mm above the bed when the probe switches; over-travel {Z_UP:g} mm, face {PRB_H:g} mm above the nozzle")))
    d.requirements.append(Requirement("target: no purchased part is a stand-in where the catalogue has a real one", lambda dd: (
        (px := [c.name for c in dd.components if c.cots and not c.meta.get("catalog")]) == [],
        f"hand-made purchased parts: {px}")))
    return d
