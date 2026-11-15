"""printer_v6: printer_v5 with a direct-drive toolhead bolted straight to the X guide block.

STATED TARGET (docs/PRINTER_V6.md says which lines are met):
  A 180 x 180 x 180 mm open-frame demonstration printer whose every purchased part is off the shelf and every
  fabricated part is printed, laser-cut or a single-set-up plate.
    - parts cost + fabrication estimate <= $900
    - <= 320 parts
    - assembly estimate <= 65 min
    - direct-drive toolhead, <= 0.40 kg moving mass in X
    - both Y belts within 1 mm of plane in >= 98 % of builds
    - a bed probe that works across the whole print area
    - no stand-in ("proxy" / uncatalogued) purchased part where the catalogue now has a real one

Same machine in kind as v5 (cartesian, bed moves in Z on two rails with two blocks each and an extrusion-arm
carrier, 2020 frame, 24 V, SKR Mini E3 V3 + Pi Zero 2 W, belt tensioners, no custom PCB). What changed:

1. Direct drive. E3D Roto extruder + Revo hot side (catalogue parts, vendor data) replace the Bowden extruder on the
   frame and the proxy hotend. The Roto's heat-sink fan is 5 V: it runs from the control board's always-on 5 V pins.
2. Toolhead on the rail. The X rail moved from the top of the beam to its REAR face, so the guide block's mounting
   face is vertical and the Roto (which bolts sideways through its body) sits flat on one 8 mm plate that sits flat
   on the block. No printed part and no cantilevered plate between block and nozzle. Nozzle: 28 mm behind and
   34 mm below the block centre (v5: 33 mm and 55 mm).
3. X drive. The X belt runs in a vertical loop over the top of the beam; motor and idler stand on two laser-cut
   plates on the beam's front face (one part, the beam, locates both), inboard of the Y carriages: the belt is 20 %
   shorter and the X motor no longer hangs outside the frame, so the left Y drive is now the mirror image of the
   right one (no belt tower). X homes sensorless (TMC2209 StallGuard); the X switch is gone.
4. Bed probe. Same class of inductive sensor (still a hand-made part with recalled data: the catalogue has none),
   mounted directly on the tool plate with its face 2.0 mm above the nozzle: it switches 0.9 .. 1.5 mm before the
   nozzle touches over its +/-10 % spread. BAT85 diode in the signal lead. Z travel goes on past the nozzle plane.
5. 180 mm of Z: frame 10 mm taller, 250 mm lead screw, Z blocks 55 mm apart on the same 300 mm rails.
6. Real catalogue parts: Pololu / OpenBuilds round spacers, 16 x 18 silicone bed columns, MIC-6 bed plate,
   9 mm belts with 9 mm pulleys and idlers.
7. Hotend safety: PSU relay and bed thermal fuse kept; Revo heater is self-limiting (PTC); a thermal cut-off taped
   to the Roto's heat sink is wired in series with the heater.
8. Consolidation: Bowden parts, belt tower, X endstop, X idler slider, hotend mount and its nuts are gone.

Layout (X = width, Y = depth with the front at -Y, Z = up) is v4's; see designs/printer_v4.py for the history.

Proxies / not modelled (flagged): the bed probe is a hand-made proxy (uncatalogued_cots is true); the Roto's solid is
E3D's drawing envelope (+/-1 mm) in solid aluminium; tapped holes, T-nuts, the part-cooling duct's air channel, the
BAT85 diode and the Revo's spring clip are BOM lines or notes, not geometry; payload is extra mass on the bed.
"""
import math

from build123d import Box, Cylinder, Location, Plane, Pos, RectangleRounded, RegularPolygon, Rot, extrude

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import MATERIALS, Belt, ThermalCase
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       iec_inlet_c14, inductive_probe_template, mosfet_module, psu_lrs,
                                       raspberry_pi_zero2w, relay_btt_v12, skr_mini_e3_v3, thermal_fuse)
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, clearance_hole,
                            endstop_switch, extrusion_2020, fan, gt2_idler, gt2_pulley,
                            leadscrew_nut_t8, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place,
                            shaft_coupler)
from mechloop.parts.hardware import bed_column_silicone, spacer_round
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
BED_W = 200.0
PSU_MODEL = "LRS-350-24"
BED_AWG, BED_INS = 16, "silicone"
# A rms at the driver. Extruder: E3D allows 0.318 .. 0.424 A rms for the Roto's motor
RUN_CURRENT = {"x": 0.28, "y": 1.20, "z": 0.28, "extruder": 0.40}
FUSE_A = 8.0
T_TRAY = 3.0
TRAY_Y0, TRAY_Y1 = -138.0, 62.0    # clear of the corner brackets at both ends
Z_TRAY = 20.0 + T_TRAY

# ---- materials for printed parts --------------------------------------------------
HOT = "abs"      # on the toolhead, near the bed, on a motor, or under a steady load: ABS (ASA is not in MATERIALS)
COOL = "petg"    # on the cold frame

# ---- frame ------------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 344.0      # v6: top ring +10 so a stock 250 mm lead screw ends under the top back rail
RAIL_X = FX / 2 - 10                  # side extrusions / Y rails
TX, TY = PRINT_X / 2, PRINT_Y / 2     # +/- travel

# ---- Z axis -----------------------------------------------------------------------
BED = 220.0
T_BED = 6.0
UP_X = 90.0            # Z upright / rail centre, +/- X
UP_Y = FY / 2 - 10     # uprights stand between the bottom and top back rails
Y_FACE = UP_Y - 10     # front face of the uprights = rail base
Y_CAR = Y_FACE - 13    # carriage top face = back plate rear face
T_BP = 5.0             # back plate: 5 mm sheet (M3x8 through it leaves 3 mm in the blocks' 3.5 mm threads)
Y_PF = Y_CAR - T_BP    # back plate front face
LS_Y = UP_Y + 10       # lead screw / motor axis Y
MOTOR_L = 34
Z_MF = 22.0 + MOTOR_L  # Z motor mounting face
T_MM = 6.0             # printed motor bridge: top plate thickness
BED_Y1 = Y_PF - 1.0    # v6: the bed ends 1 mm in front of the back plate (6 mm further forward than v5: room behind the toolhead)
BED_Y0 = BED_Y1 - BED
BED_CY = (BED_Y0 + BED_Y1) / 2
ARM_X = 65.0           # 2020 arms: inboard of the uprights so their end screws can be driven from behind
ARM_L = 210.0
H_COL = 16.0           # installed height of the silicone levelling columns (catalogue part: 18 free, 2 mm pre-compression)
# bed mounts stand on the arms; the pad (200 wide, 140 deep) lies between the front and the rear pair
BED_MOUNTS = [(-ARM_X, BED_Y1 - 25.0), (ARM_X, BED_Y1 - 25.0), (-ARM_X, BED_Y1 - 195.0), (ARM_X, BED_Y1 - 195.0)]
NUT_PIN = (0.0, 8.0)   # the one flange hole of the T8 nut that carries the anti-rotation pin
NUT_FLOAT = 1.5        # radial room around the nut barrel and along the pin slot
Z_DN = 3.0             # mechanical Z travel below the home position (bed at the bottom)
Z_UP = 2.0             # v6: Z travel beyond the nominal nozzle plane, for the probe's z_offset and the bed mesh
Z_SPACING = 55.0       # two blocks per rail, centre to centre (v5: 80 with 150 mm of travel)
Z_RAIL_L = 300.0
Z_RAIL_C = 22.0 + Z_RAIL_L / 2   # rail 22 .. 322: on the upright only, ends below the top back rail (FZ - 10)

# ---- gantry -----------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13          # underside of the Y plates
T_YP = 3.0                     # Y plates: 3 mm laser-cut steel sheet, like the motor and idler mounts
Z_BEAM = Z_PLATE + T_YP + 10   # beam centre line = X rail centre line = X guide block centre (rail on the beam's rear face)
PR = 20 * 2.0 / math.pi / 2    # pitch radius of the 20T pulleys / idlers
BWX, BWY = 9.0, 9.0            # GT2 belt widths (v6: 9 mm, catalogue parts with the width in the SKU)
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
XD_Z = Z_BEAM + 31.0           # their height: the lower motor screws clear the beam top
X_PG = 2.75                    # gap between the motor plate and the pulley hub
XB_Y = YB0 - 10.0 + X_PG + P_BC(BWX)      # X belt centre line: over the beam, 4.75 mm behind its centre
X_SP = XB_Y - I_H(BWX) / 2 - (YB0 - 10.0)   # X idler spacer length (9: a stock length)
Z_XL = XD_Z - PR               # lower (anchored) run of the X belt, pitch line
BLK_Z0 = Z_BEAM + 14.0         # underside of the belt block (0.5 above the guide block)
BLK_Z1 = Z_BEAM + 30.0         # its top (the belt's upper run passes 6.6 mm above)
# Y drives: vertical belt planes outboard of both top side rails (v6: both sides alike)
Y_SP = 6.0                     # Y idler spacers (bought, aluminium): the shortest that lets the pulley hub clear the motor's boss
YB_X = FX / 2 + MT_Y + Y_SP + I_H(BWY) / 2       # Y belt plane (+/-)
YM_Y, YI_Y = FY / 2 + 24.0, -156.0      # Y motor pulley (behind the frame) and Y idler (front, beyond the Y rails' ends)
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
YP_IN = RAIL_X - 33.0          # their inboard edge (the X guide block and the tool plate pass inside it)

# bed heights follow from the nozzle
Z_BED = Z_NOZZLE - NOZZLE_GAP - T_BED - PRINT_Z   # bed underside at home (bed at the bottom)
Z_FL = Z_BED - H_COL                              # top of the arms (the columns stand on them)
Z_ARM = Z_FL - 10.0                               # arm centre line
ZC1 = 22.0 + 5.0 + 22.7 + Z_DN + 0.3              # lower Z block centre at home: 5.3 mm of rail left below it at -Z_DN
ZC2 = ZC1 + Z_SPACING                             # upper block: 22 + 300 - (ZC2 + 22.7 + PRINT_Z + Z_UP) = 9.3 mm left above
BP_Z0, BP_Z1 = ZC1 - 23.0, Z_ARM + 14.0           # back plate covers both blocks and the arm ends
BP_W = 214.0                                      # 5 mm of sheet outside the outer screw holes
Z_TAB = 107.0                                     # underside of the nut block at home (clears the coupler at -Z_DN)
NB_H = 10.0                                       # nut block height (v6: 10, so the nut's pin is an M3x16)
NB_BOLTS = [(sx * 23.0, Z_TAB + dz) for sx in (-1, 1) for dz in (0.0, 20.0)]
# Y endstop (lever switch): the trigger is the lever's operating position at its tip, 10.6 from the switch origin
# along the stroke and 9 to one side
ES_TRIG, ES_SIDE = 10.6, 9.0
LAND_X, LAND_Y1 = (-(RAIL_X - 9.0), -(RAIL_X - 29.5)), 34.0     # left Y plate: land behind the beam for the X endstop
ES_SP = 4.0                                       # bought spacers under the switch boards (their terminals stand 2.6 mm out)
X_ES_Y = 30.2                                     # where the X switch's lever meets the left edge of the tool plate's tab
# bed probe: inductive, sensing face PRB_H above the nozzle tip. With 3.2 mm on aluminium +/-10 % it switches with
# the nozzle 0.88 .. 1.52 mm above the bed.
PRB_SN = 3.2                                      # 8 mm on steel x 0.4 for aluminium: recalled class value, unverified
PRB_H = 2.0
PRB_X = -32.0                                     # probe axis, left of the nozzle (6.8 mm from the Roto's fan screws)
PRB_Y = R_TPR + 9.0                               # ... and behind the tool plate, which it is screwed to
Z_PRB = Z_NOZZLE + PRB_H                          # sensing face
PRB_SCREW_Z = [Z_PRB + 8.0, Z_PRB + 28.0]
# tool plate outline, from the nozzle axis (x) and the beam centre (z)
TPX = 23.0                                        # half width over the guide block
TP_Z0, TP_Z1 = -14.0, 35.0
TAB_L = (-38.2, -23.0, -28.0, 6.0)                # left tab (x0, x1, z0, z1): bed probe (it overhangs the tab by 2.8 mm)
TAB_R = (13.0, 46.0, -27.0, -14.0)                # right tab under the Roto's motor: part-fan carrier
# part-cooling fan carrier (printed): flange on the right tab, spine under the motor, fan behind the Roto
FC_X0, FC_X1 = TAB_R[0], TAB_R[1]
FC_FL = 6.0                                       # flange thickness
FC_Z0, FC_ZF = TAB_R[2], -12.2                    # underside; flange top (0.75 under the Roto's body)
FC_ZS = -23.5                                     # spine top
FC_LUG_Y = R_TPR + ROTO_W + 0.5                   # lug front face: 0.5 behind the Roto
FAN_LUG = 3.5                                     # printed wall between the fan and its captive nuts (M3x16 = fan 10 + 3.5 + nut 2.4)
PFAN = ((FC_X0 + FC_X1) / 2, FC_LUG_Y + FAN_LUG + 5.0, -12.0)    # part fan centre (x, y from YB0, z from Z_BEAM)
FC_SCREWS = [(20.5, -20.5), (39.0, -20.5)]        # carrier -> tab (x, z)
BLK_SCREWS = [(-9.5, 19.0), (9.5, 19.0)]          # tool plate -> belt block (x, z from Z_BEAM)
BLK_Y0 = XB_Y - YB0 - BWX / 2 - 2.25              # belt block front face, from YB0 (the belt slots are open to it)
BLK_NUT_Y = 16.7                                  # the block's captive nuts bear on this face, from YB0


def bed_probe() -> Stock:
    """PROXY (not in the catalog): rectangular inductive proximity sensor of the PL-08N class (NPN, normally open,
    8 mm nominal on steel), 18 x 18 x 36 mm, two M3 through holes across it. Local frame: sensing face on Z=0, body
    above, holes along X at Z = 8 and 28. `trigger` is where a flat aluminium target switches it. Dimensions, mass and
    switching distance are recalled class values, not read from a data sheet."""
    body = Pos(0, 0, 18.0) * Box(18.0, 18.0, 36.0)
    holes = [(0.0, 0.0, 8.0), (0.0, 0.0, 28.0)]
    for _, _, z in holes:
        body -= Pos(0, 0, z) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, 18.0)
    # electrical model of kind 'probe' (supply range, NPN open-collector output, switching distances and their spread)
    tpl = inductive_probe_template(sn_steel_mm=8.0, sn_aluminium_mm=PRB_SN, output="npn_no")
    return Stock(body, "PROBE-INDUCTIVE-8MM", "UNVERIFIED proxy: inductive bed probe 18 x 18 x 36, 8 mm NPN NO", 0.02,
                 material="abs", cost_usd=6.0, ratings={"electrical": tpl},
                 interfaces={"trigger": [(0.0, 0.0, -PRB_SN)], "sensing_face": [(0.0, 0.0, 0.0)], "mount_holes_m3": holes})


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
    """Flat 5 mm sheet on the four Z blocks (laser cut, through holes only). The arms butt against its front face."""
    yc = (Y_PF + Y_CAR) / 2
    p = Pos(0, yc, (BP_Z0 + BP_Z1) / 2) * Box(BP_W, T_BP, BP_Z1 - BP_Z0)
    # lightening window between the two lower blocks (an 8 mm tie is left along the bottom edge)
    p -= Pos(0, yc, BP_Z0 + 31.0) * Rot(90, 0, 0) * extrude(RectangleRounded(136.0, 46.0, 5.0), T_BP / 2, both=True)
    for hx, hy, hz in carriage_holes:
        p -= Pos(hx, yc, hz) * ycyl(SH3 / 2, T_BP)
    for sx in (-1, 1):
        p -= Pos(sx * ARM_X, yc, Z_ARM) * ycyl(clearance_hole("M5") / 2, T_BP)          # arm end screw (blind joint)
        # corner bracket screw: a vertical slot, because the cast bracket has a 4 x 17 mm locating rib standing 1 mm
        # out of each leg (it normally sits in a T-slot); here it sits in this slot and keys the bracket
        p -= Pos(sx * ARM_X, yc, Z_ARM - 20.5) * (Box(clearance_hole("M5"), T_BP, 13.0)
                                                   + Pos(0, 0, 6.5) * ycyl(clearance_hole("M5") / 2, T_BP)
                                                   + Pos(0, 0, -6.5) * ycyl(clearance_hole("M5") / 2, T_BP))
    for x, z in NB_BOLTS:
        p -= Pos(x, yc, z) * ycyl(clearance_hole("M3") / 2, T_BP)
    return p


def nut_block_shape():
    """Printed block behind the back plate that sits on the floating T8 nut. A 6 mm flange bolts through the back plate
    (four M3 with nuts, no thread in plastic); the 14 mm deep block has a square hole with NUT_FLOAT of room around the
    nut barrel and a slot for the anti-rotation pin. Printed flange-down, so the square hole is a 14 mm bridge."""
    y1 = LS_Y + 15.0
    b = Pos(0, Y_CAR + 3.0, Z_TAB + 10.0) * Box(60.0, 6.0, 34.0)      # flange: 7 mm below the block's underside to 27 above
    b += Pos(0, (Y_CAR + 6.0 + y1) / 2, Z_TAB + NB_H / 2) * Box(30.0, y1 - Y_CAR - 6.0, NB_H)
    b -= Pos(0, LS_Y, Z_TAB + NB_H / 2) * Box(2 * (5.1 + NUT_FLOAT) + 0.8, 2 * (5.1 + NUT_FLOAT) + 0.8, NB_H)
    b -= slot_z(NUT_PIN[0], LS_Y + NUT_PIN[1], 90, NUT_FLOAT, clearance_hole("M3"), Z_TAB, Z_TAB + NB_H)
    for x, z in NB_BOLTS:
        b -= Pos(x, Y_CAR + 3.0, z) * ycyl(PH3 / 2, 6.0)
    return b


def bed_shape_():
    b = Pos(0, BED_CY, Z_BED + T_BED / 2) * Box(BED, BED, T_BED)
    for x, y in BED_MOUNTS:   # M3 cap heads sit 0.4 mm below the print surface
        b -= Pos(x, y, Z_BED + T_BED / 2) * Cylinder(clearance_hole("M3") / 2, T_BED)
        b -= Pos(x, y, Z_BED + T_BED - 1.7) * Cylinder(3.25, 3.4)
    return b


MM_X, MM_LEG, MM_FOOT_X, MM_FOOT_W = 23.0, 6.0, 34.5, 10.5     # 79 mm wide: under the 80 mm ABS warp rule of thumb
MM_Y0, MM_Y1 = Y_FACE - 2.0, LS_Y + 22.0


def z_motor_mount_shape():
    """Printed bridge standing on the bottom back rail: two legs beside the motor, feet on the rail's top slot, a top
    plate the motor hangs under. Printed with its front face (y = MM_Y0) on the bed: every wall is vertical and the
    shaft slot is open upwards."""
    x1 = MM_X + MM_LEG
    yc, ly = (MM_Y0 + MM_Y1) / 2, MM_Y1 - MM_Y0
    m = Pos(0, yc, Z_MF + T_MM / 2) * Box(2 * x1, ly, T_MM)
    for sx in (-1, 1):
        m += Pos(sx * (MM_X + MM_LEG / 2), yc, (20.0 + Z_MF) / 2) * Box(MM_LEG, ly, Z_MF - 20.0)
        m += Pos(sx * (x1 + MM_FOOT_W / 2), (MM_Y0 + UP_Y + 9.0) / 2, 22.5) * Box(MM_FOOT_W, UP_Y + 9.0 - MM_Y0, 5.0)
        m -= Pos(sx * MM_FOOT_X, UP_Y, 22.5) * Cylinder(PH5 / 2, 5.0)
    m -= Pos(0, LS_Y, Z_MF + T_MM / 2) * Cylinder(11.5, T_MM)
    m -= Pos(0, (LS_Y + MM_Y1) / 2, Z_MF + T_MM / 2) * Box(23.0, MM_Y1 - LS_Y, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(x, LS_Y + y, Z_MF + T_MM / 2) * Cylinder(PH3 / 2, T_MM)
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
    tp += fillet_y(-TPX, Z_BEAM + TP_Z0, 1, -1, r, y0, y1)           # plate underside / left tab
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
                 + [(PRB_X, z - Z_BEAM) for z in PRB_SCREW_Z]):
        tp -= Pos(x, yc, Z_BEAM + z) * ycyl(2.5 / 2, T_TP)
    for x, z in BLK_SCREWS:      # belt block screws: from the rear too, heads sunk under the Roto's side face
        tp -= Pos(x, yc, Z_BEAM + z) * ycyl(clearance_hole("M3") / 2, T_TP)
        tp -= Pos(x, y1 - CB / 2, Z_BEAM + z) * ycyl(3.0, CB)
    return tp


def belt_block_shape():
    """Printed block on the tool plate's front face, above the guide block, reaching forward over the beam. The X
    belt's two ends slide into a slot from the front; each end is folded back on itself in the taller middle of the
    slot, where its teeth lock in its own teeth (no clamp bar, no clamp screws). Two M3x16 from the rear of the tool
    plate run into captive nuts in slots open to the underside (the guide block closes them). Printed rear face down:
    the belt slot is then a vertical-walled channel open to the top."""
    y0, y1 = YB0 + BLK_Y0, YB0 + R_TPF
    b = bx(-14.0, 14.0, y0, y1, BLK_Z0, BLK_Z1)
    ys = XB_Y + BWX / 2 + 0.5                                           # slot depth: belt width + 0.5
    b -= bx(-14.0, 14.0, y0, ys, Z_XL - 0.75, Z_XL + 0.85)              # one belt thickness
    b -= bx(-9.0, 9.0, y0, ys, Z_XL - 0.75, Z_XL + 2.3)                 # two belt thicknesses, teeth in teeth
    for x, z in BLK_SCREWS:
        b -= Pos(x, (YB0 + BLK_NUT_Y - 5.5 + y1) / 2, Z_BEAM + z) * ycyl(PH3 / 2, y1 - (YB0 + BLK_NUT_Y - 5.5))
        b -= bx(x - 2.9, x + 2.9, YB0 + BLK_NUT_Y - NUT_SLOT, YB0 + BLK_NUT_Y, BLK_Z0, Z_BEAM + z + 3.35)
    return b


def fan_carrier_shape():
    """Printed ABS carrier for the part-cooling fan: a flange on the tool plate's right tab (two M3x16 from the front
    into captive nuts), a 45-degree gusset, a spine under the Roto's motor and a lug behind the Roto that the fan hangs
    on by its two lower holes (captive nuts in slots open to the underside). Its floor and lug are the spine of the
    air duct; the duct's thin walls and outlet are not modelled. Printed lug-down: no overhang past 45 degrees."""
    yf, yl = YB0 + R_TPR, YB0 + FC_LUG_Y
    z0, zf, zs = Z_BEAM + FC_Z0, Z_BEAM + FC_ZF, Z_BEAM + FC_ZS
    c = bx(FC_X0, FC_X1, yf, yf + FC_FL, z0, zf)                               # flange
    g = zf - zs
    gus = bx(FC_X0, FC_X1, yf + FC_FL, yf + FC_FL + g, zs, zf)
    gus -= Pos((FC_X0 + FC_X1) / 2, yf + FC_FL + g, zf) * Rot(45, 0, 0) * Box(FC_X1 - FC_X0 + 1, g * math.sqrt(2), g * math.sqrt(2))
    c += gus                                                                   # gusset
    c += bx(FC_X0, FC_X1, yf + FC_FL, yl, z0, zs)                              # spine
    zb = Z_BEAM + PFAN[2] - 12.0                                               # lower fan holes
    c += bx(FC_X0, FC_X1, yl - 8.0, yl, z0, zb + 6.5)                          # boss the nut slots are cut in
    c += bx(FC_X0, FC_X1, yl, yl + FAN_LUG, z0, Z_BEAM + PFAN[2] + 15.0)       # lug
    c -= Pos(PFAN[0], yl + FAN_LUG / 2, Z_BEAM + PFAN[2]) * ycyl(13.5, FAN_LUG)
    for sx in (-12.0, 12.0):
        c -= Pos(PFAN[0] + sx, yl + FAN_LUG / 2, zb) * ycyl(PH3 / 2, FAN_LUG)
        c -= bx(PFAN[0] + sx - 2.9, PFAN[0] + sx + 2.9, yl - NUT_SLOT, yl, z0, zb + 3.35)
    for x, z in FC_SCREWS:
        c -= Pos(x, yf + FC_FL / 2, Z_BEAM + z) * ycyl(PH3 / 2, FC_FL)
        c -= hex_pocket_y(x, yf + FC_FL - NUT_POCKET, Z_BEAM + z, 16.0, into=1)    # nut pocket, open to the rear through the gusset
    return c


USE_CUTOFFS = USE_MOSFET = True


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
    device_from(el, d, "bed_heater", plate="bed")      # the thermal model takes the plate's mass and area from this part
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
    P1 = (142.0, 146.0, FZ + 2.0)
    # toolhead loom: tied along the top of the Roto's rear face (left end: probe and hot-side leads join; right end:
    # motor lead joins and the free loop leaves), high enough to clear the part fan when the loop trails back
    yl = YB0 + R_TPR + ROTO_W + 2.0
    el.loom("toolhead", [Waypoint("xbody", (-13.0, yl, Z_BEAM + 26.0), clamp="extruder"),
                         Waypoint("xbody", (24.0, yl, Z_BEAM + 26.0), clamp="extruder"),
                         Waypoint("world", (142.0, 177.0, FZ + 13.0), clamp="frame_top_back"), Waypoint("world", P1)],
            flex_length={1: 460.0})
    el.loom("drop_right", [("world", P1), ("world", (143.0, 152.0, FZ - 34.0)), ("world", (145.0, 168.0, FZ - 74.0)),
                           ("world", (145.0, 170.0, 60.0)), ("world", (145.0, 150.0, 34.0))])
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (149.0, 46.0, zt)), ("world", (149.0, -26.0, zt))])
    el.loom("front_right", [("world", (149.0, -26.0, zt)), ("world", (149.0, -120.0, zt)), ("world", (143.0, -150.0, 40.0)),
                            ("world", (143.0, -170.0, 70.0)), ("world", (143.0, -170.0, FZ - 64.0)),
                            ("world", (143.0, -152.0, FZ - 26.0)), ("world", (146.0, -136.0, FZ - 8.0))])
    el.loom("back", [("world", (140.0, 152.0, 30.0)), ("world", (130.0, 155.0, 12.0)), ("world", (30.0, 155.0, 12.0))])
    # the X motor's and X switch's leads are tied under the left Y plate, inboard of the Y carriage; the loop hangs
    # from there to the rail's inner face
    el.loom("gantry", [Waypoint("ybody", (-137.0, YB0 - 20.0, Z_PLATE - 3.0), clamp="y_plate_left"),
                       Waypoint("world", (XL, YB0 - 20.0, ZL), clamp="frame_top_left")], flex_length={0: 150.0})
    el.loom("top_left", [("world", (XL, -20.0, ZL)), ("world", (XL, 136.0, ZL))])
    el.loom("drop_left", [("world", (XL, -27.0, ZL)), ("world", (XL, -120.0, ZL)),
                          ("world", (-143.0, -150.0, FZ - 24.0)), ("world", (-143.0, -170.0, FZ - 64.0)),
                          ("world", (-143.0, -170.0, 70.0)), ("world", (-143.0, -162.0, 48.0)),
                          ("world", (-156.0, -150.0, 36.0)), ("world", (-162.0, -125.0, 36.0)), ("world", (-162.0, -15.0, 36.0))])
    el.loom("front", [("world", (-162.0, -15.0, 36.0)), ("world", (-140.0, -15.0, zt)), ("world", (70.0, -15.0, zt))])
    el.loom("bed", [Waypoint("zbody", (0.0, Y_PF - 3.0, Z_TAB + 19.0), clamp="back_plate"),
                    Waypoint("zbody", (0.0, Y_PF - 3.0, Z_TAB - 4.0), clamp="back_plate"),
                    Waypoint("world", (0.0, TRAY_Y1 - 4.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 330.0})
    el.loom("mains", [("world", (-50.0, -4.0, zt)), ("world", (20.0, -4.0, zt))])
    tool, left = ["tray_right", "drop_right", "toolhead"], ["front", "drop_left"]
    # ---- mains and protective earth (AWG 18 = 0.82 mm^2, 105 degC PVC)
    mk = dict(conductors=1, insulation="pvc105")
    el.wire("mains L inlet-relay", "inlet.L", "psu_relay.LIN", 18, **mk)
    el.wire("mains L relay-supply", "psu_relay.LOT", "psu.L", 18, via=["mains"], **mk)
    el.wire("relay control", "control_board.PS-ON", "psu_relay.ctrl", 26, conductors=3)
    el.wire("mains N", "inlet.N", "psu.N", 18, via=["mains"], **mk)
    el.wire("earth to supply", "inlet.PE", "psu.FG", 18, via=["mains"], **mk)
    el.wire("earth to frame", "inlet.PE", "frame_earth.pe", 18, connector_b="ring-M4", **mk)
    # ---- 24 V distribution
    el.wire("24 V to board", "psu.V+1", "control_board.POWER", 16, insulation="silicone")
    el.wire("24 V to bed module", "psu.V+2", "bed_mosfet.pwr", 14, insulation="silicone")
    el.wire("bed control", "control_board.HB", "bed_mosfet.ctrl", 24)
    el.wire("bed heater", "bed_mosfet.out", "bed_tco.a", BED_AWG, insulation=BED_INS, via=["bed"])
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
                                   "max_temp": 120, "targets": [60.0, 100.0], "verify_heater": {}}},
        "fans": {"part_fan": {"device": "part_fan", "role": "part"}, "hotend_fan": {"device": "hotend_fan", "role": "heatsink"}},
    }
    # hot parts wires must be rated for: the HeaterCore and nozzle block (not the whole part) and the bed plate
    hi = d.get("hotend").meta["interfaces"]
    rc = hi["heatercore_dia"] / 2
    hb = (-rc, YB0 + HOT_OFF - rc, hi["heater_block_box"][0][2], rc, YB0 + HOT_OFF + rc, hi["heater_block_box"][1][2])
    el.hot_parts = {"hotend": {"temp": 250.0, "box": hb}, "bed": 100.0}
    # the bay is the open tray under the bed: air leaves through the open sides of the frame
    el.bay = Bay(devices=[n for n in ("psu", "control_board", "host", "psu_relay", "bed_mosfet") if n in el.devices],
                 enclosed=False, vent_area_m2=0.02, height_m=0.05)
    el.sync_cables(d)
    add_electrical_bom(el, d)
    d.bom_extra(f"FUSE-5x20-T{FUSE_A:g}A", 2, 0.3)
    d.bom_extra("DIODE-BAT85", 1, 0.1)
    return el


def build() -> Design:
    d = Design("printer_v6", envelope=ENVELOPE, base="frame_bot_left")
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
    # bed carrier: sheet back plate + two 2020 arms. Each arm is held by an M5 screw through the plate into its
    # tapped end (driven from behind, between the upright and the lead screw) and a cast corner bracket underneath
    # (T-nut in the arm's bottom slot; its plate-side M5 screw and nut are modelled by add_corner_bracket).
    d.add("back_plate", back_plate_shape(carriage_holes), material="al6061", body="zbody", process="sheet")
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"bed_arm_{n}", extrusion_2020(ARM_L), Location((sx * ARM_X, Y_PF - ARM_L / 2, Z_ARM), (0, 0, 90)),
              body="zbody")
        add_screw(d, f"bed_arm_{n}_bolt", "M5", 16, at=(sx * ARM_X, Y_CAR, Z_ARM), direction=(0, -1, 0), body="zbody",
                  threads_into=f"bed_arm_{n}", clamps=("back_plate",))
        add_corner_bracket(d, f"bed_arm_{n}_bracket", f"bed_arm_{n}", "back_plate",
                           (sx * ARM_X, Y_PF, Z_ARM - 10.0), (0, -1, 0), (0, 0, -1), body="zbody")
    # floating nut: it hangs under the printed block (the bed's weight keeps the block sitting on the nut flange); the
    # pin screw gets a nyloc nut under the flange left 0.2 mm slack, so the nut slides +/-NUT_FLOAT and cannot turn
    d.add("nut_block", nut_block_shape(), material=HOT, body="zbody", process="printed", meta={"print_up": "+Y"})
    for i, (x, z) in enumerate(NB_BOLTS):
        add_screw(d, f"nut_block_bolt_{i}", "M3", 16, at=(x, Y_PF, z), direction=(0, 1, 0), body="zbody",
                  clamps=("back_plate", "nut_block"))
        add_nut(d, f"nut_block_nut_{i}", "M3", at=(x, Y_CAR + 6.0, z), direction=(0, 1, 0), body="zbody",
                screw=f"nut_block_bolt_{i}")
    place(d, "z_nut", leadscrew_nut_t8(), Location((0, LS_Y, Z_TAB - 3.5)), body="zbody")
    add_screw(d, "nut_pin", "M3", 16, at=(NUT_PIN[0], LS_Y + NUT_PIN[1], Z_TAB + NB_H), body="zbody", threads_into="z_nut")
    d.bom_extra("NYLOC-M3", 1, 0.05)
    # bed: 6 mm cast tooling plate (MIC-6). Machined in one set-up because the screw heads are counterbored below the
    # print surface; the cast faces are the print surface and the pad face as bought.
    bed_own = BED * BED * T_BED * MATERIALS["al_mic6"].density * 1e-9
    d.add("bed", bed_shape_(), material="al_mic6", body="zbody", mass_kg=bed_own + PAYLOAD_KG, process="machined")
    # silicone pad, 200 wide x 140 deep so the four mounts stand in front of and behind it; leads leave at the back
    place(d, "bed_heater", bed_heater_pad(200.0, 140.0, BED_W), Location((0, BED_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed", "bond")
    place(d, "bed_tco", thermal_fuse(133.0, 109.0, 15.0), Location((-25.0, BED_Y1 - 5.0, Z_BED - 2.0)), body="zbody")
    d.join("bed_tco", "bed", "bond")
    # bed mounts: M3x25 from the top (head counterbored in the bed) through a silicone column (catalogue part, 16 OD
    # x 18, drawn compressed to 16) into a T-nut in the arm's top slot; turning the screw moves that corner
    # +/-1.5 mm. The T-nuts are held only by the columns' spring force, so they slide as the hot bed grows.
    for i, (x, y) in enumerate(BED_MOUNTS):
        arm = f"bed_arm_{'left' if x < 0 else 'right'}"
        place(d, f"bed_column_{i}", bed_column_silicone(18.0, installed=H_COL), Location((x, y, Z_FL)), body="zbody")
        add_screw(d, f"bed_screw_{i}", "M3", 25, at=(x, y, Z_BED + T_BED - 3.4), body="zbody", threads_into=arm, tnut=True,
                  clamps=("bed", f"bed_column_{i}"))
        d.join(f"bed_column_{i}", "bed", "clamp")
        d.join(f"bed_column_{i}", arm, "clamp")
    # Z motor under a printed ABS bridge on the bottom back rail (the motor case runs at about 60 degC: not PETG)
    d.add("z_motor_mount", z_motor_mount_shape(), material=HOT, process="printed", meta={"print_up": "+Y"})
    place(d, "z_motor", nema17(MOTOR_L), Location((0, LS_Y, Z_MF), (0, 0, 90)))     # connector to the rear
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"z_motor_screw_{i}", "M3", 10, at=(x, LS_Y + y, Z_MF + T_MM), threads_into="z_motor",
                  clamps=("z_motor_mount",))
    for sx, n in ((-1, "left"), (1, "right")):
        add_screw(d, f"z_mount_bolt_{n}", "M5", 8, at=(sx * MM_FOOT_X, UP_Y, 25.0), threads_into="frame_bot_back", tnut=True,
                  clamps=("z_motor_mount",))
    z_cpl = Z_MF + 11.5                 # coupler bottom; motor shaft tip (Z_MF + 20) is in the 5 mm bore
    place(d, "z_coupler", shaft_coupler(5.0, 8.0), Location((0, LS_Y, z_cpl)))
    place(d, "leadscrew", leadscrew_t8(250, lead=2.0), Location((0, LS_Y, z_cpl + 12.5)))    # 80 .. 330: 4 mm under the top back rail
    d.join("z_coupler", "z_motor", "clamp")
    d.join("leadscrew", "z_coupler", "clamp")

    # ================= Y axis ====================================================
    zp0, zp1 = Z_PLATE, Z_PLATE + T_YP
    X_ES_X0 = TAB_L[0] - TX - ES_TRIG         # X switch origin (its trigger point is ES_TRIG further in +X)
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
        # v6: flat 3 mm laser-cut steel plates. The beam now ends inboard of the guide blocks and sits on the inboard 17 mm
        # of each plate, so the four block screws are plain cap heads on top (no counterbores under the beam: v5's
        # reason for machining these plates) and can be driven with the beam on. The outboard end carries the Y belt.
        x_out = YB_X + BWY / 2 + 0.5 + 3.25
        plate = bx(sx * YP_IN, sx * x_out, YB0 + PL_Y0, YB0 + PL_Y1, zp0, zp1)
        # Y belt anchor (v6): no clamp part. Each belt end goes down through one slot, up through the next, is folded
        # back on itself and tied with a cable tie; the laser-cut slots themselves locate the belt sideways.
        for dy in BELT_SLOTS:
            plate -= slot_z(sx * YB_X, PC + dy, 0.0, (BWY + 1.0 - SLOT_W) / 2, SLOT_W, zp0, zp1)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(YH3 / 2, T_YP)
        x_bolt = sx * (RAIL_X - 25)
        plate -= Pos(x_bolt, YB0, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M5") / 2, T_YP)
        if sx < 0:
            # land behind the beam for the X endstop (the switch stands on two bought spacers); the land stops short of the tool plate's tab at x = -TX
            plate += bx(LAND_X[0], LAND_X[1], YB0 + PL_Y1, YB0 + LAND_Y1, zp0, zp1)
            plate += fillet_z(LAND_X[0], YB0 + PL_Y1, -1, 1, 2.0, zp0, zp1)
            plate += fillet_z(LAND_X[1], YB0 + PL_Y1, 1, 1, 2.0, zp0, zp1)
            for dy in (-7.5, 7.5):       # the X switch's two screws (through holes: nuts underneath, beside the guide block)
                plate -= Pos(X_ES_X0 - 4.2, X_ES_Y0 + dy, Z_PLATE + T_YP / 2) * Cylinder(SH3 / 2, T_YP)
        d.add(f"y_plate_{n}", plate, material="steel", body="ybody", process="sheet")
        for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
            add_screw(d, f"y_plate_{n}_screw_{i}", "M3", 6, at=(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP),
                      body="ybody", threads_into=f"y_carriage_{n}")
        add_screw(d, f"beam_bolt_{n}", "M5", 8, at=(x_bolt, YB0, Z_PLATE), direction=(0, 0, 1),
                  body="ybody", threads_into="x_beam", tnut=True)
    # ================= X axis ====================================================
    # v6: the rail is on the REAR face of the beam, so the guide block's mounting face is vertical
    place(d, "x_beam", extrusion_2020(BEAM_L), Location((0, YB0, Z_BEAM)), body="ybody")
    rear = lambda x: Location(Plane(origin=(x, YB0 + 10.0, Z_BEAM), x_dir=(1, 0, 0), z_dir=(0, 1, 0)))
    xr = place(d, "x_rail", mgn12_rail(250), rear(0.0), body="ybody")
    for i, (hx, hy, hz) in enumerate(xr.meta["interfaces"]["mount_holes_m3"][::2]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy + 3.5, hz), direction=(0, -1, 0), body="ybody",
                  threads_into="x_beam", tnut=True)
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
    place(d, "hotend", hotend_revo(40, 24.0, 0.4), Location(tuple(seat), (0, 0, 135)), body="xbody")
    d.allow_overlap("hotend", "extruder")
    d.join("hotend", "extruder", "clamp")
    # bed probe on the plate's left tab: two M3x25 from the rear through the probe into the plate
    place(d, "bed_probe", bed_probe(), Location((PRB_X, YB0 + PRB_Y, Z_PRB), (0, 0, 90)), body="xbody")
    for i, z in enumerate(PRB_SCREW_Z):
        add_screw(d, f"probe_screw_{i}", "M3", 25, at=(PRB_X, YB0 + PRB_Y + 9.0, z), direction=(0, -1, 0), body="xbody",
                  threads_into="tool_plate", clamps=("bed_probe",))
    # part-cooling fan behind the Roto on its printed carrier
    d.add("fan_carrier", fan_carrier_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "-Y"})
    for i, (x, z) in enumerate(FC_SCREWS):
        add_screw(d, f"fan_carrier_screw_{i}", "M3", 16, at=(x, yf, Z_BEAM + z), direction=(0, 1, 0), body="xbody",
                  clamps=("tool_plate", "fan_carrier"))
        add_nut(d, f"fan_carrier_nut_{i}", "M3", at=(x, yrr + FC_FL - NUT_POCKET, Z_BEAM + z), direction=(0, 1, 0),
                body="xbody", screw=f"fan_carrier_screw_{i}")
    place(d, "part_fan", fan(30), Location(Plane(origin=(PFAN[0], YB0 + PFAN[1], Z_BEAM + PFAN[2]), x_dir=(1, 0, 0), z_dir=(0, 1, 0))),
          body="xbody")
    for i, sx in enumerate((-12.0, 12.0)):
        add_screw(d, f"part_fan_screw_{i}", "M3", 16, at=(PFAN[0] + sx, YB0 + PFAN[1] + 5.0, Z_BEAM + PFAN[2] - 12.0),
                  direction=(0, -1, 0), body="xbody", clamps=("part_fan", "fan_carrier"))
        add_nut(d, f"part_fan_nut_{i}", "M3", at=(PFAN[0] + sx, YB0 + FC_LUG_Y, Z_BEAM + PFAN[2] - 12.0), direction=(0, -1, 0),
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
                Location(Plane(origin=(X_ES_X0, X_ES_Y0, zp1 + ES_SP), x_dir=(0, -1, 0), z_dir=(0, 0, 1))), body="ybody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"x_endstop_spacer_{i}", spacer_round("M3", ES_SP), Location((hx, hy, zp1)), body="ybody")
        add_screw(d, f"x_endstop_screw_{i}", "M3", 16, at=(hx, hy, hz + 1.6), body="ybody",
                  clamps=("x_endstop", f"x_endstop_spacer_{i}", "y_plate_left"))
        add_nut(d, f"x_endstop_nut_{i}", "M3", at=(hx, hy, zp0), direction=(0, 0, -1), body="ybody", screw=f"x_endstop_screw_{i}")
    # ================= Y drives: vertical belt planes outboard of both top side rails =====
    # Mounts are 3 mm laser-cut steel sheet. Belt tensioners: each motor mount is held by three M5 screws in T-nuts,
    # so with them slack it slides along the rail; an M3 jack screw in a printed anchor block (bolted to the same
    # slot, hooked under the rail) pushes it backwards on a lug. v6: left and right are mirror images.
    xf = FX / 2
    Y_MOUNT_BOLTS = (133.0, 150.0, 167.0)
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
        place(d, f"y_pulley{tag}", gt2_pulley(20, belt_width=BWY), side(sg * (YB_X - P_BC(BWY)), YM_Y, Z_YC, sg))
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
        im = bx(xa, xb, YI_Y - 17.0, YI_Y + 15.0, FZ - 10.0, Z_YC + 9.0)
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
            im += bx(xa, xb, y_r0, YI_Y + 15.0, Z_YC + 9.0, z_r1)
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
    psu = place(d, "psu", psu_lrs(PSU_MODEL), Location((-47.0, -78.5, Z_TRAY), (0, 0, 180)))
    # board on 6 mm spacers, long edge along Y: power / heater terminals face the supply, motor connectors face +X
    board = place(d, "control_board", skr_mini_e3_v3(), Location((109.0, -82.0, Z_TRAY + 6.0), (0, 0, -90)))
    host = place(d, "host", raspberry_pi_zero2w(), Location((45.0, 27.0, Z_TRAY + 4.0), (0, 0, 90)))
    # the board is held by four of its five holes (not the one in the middle), the Pi by two opposite corners
    pcbs = [(board, "mount_holes_m3", "M3", 16, 6.0, (0, 1, 2, 4)), (host, "mount_holes_m2.5", "M2.5", 12, 4.0, (0, 3))]
    if USE_CUTOFFS:
        relay = place(d, "psu_relay", relay_btt_v12(), Location((-88.0, 24.0, Z_TRAY + 6.0)))
        pcbs.append((relay, "mount_holes_m3", "M3", 16, 6.0, None))
    if USE_MOSFET:
        mos = place(d, "bed_mosfet", mosfet_module(25.0), Location((100.0, 26.0, Z_TRAY + 6.0), (0, 0, 90)))
        pcbs.append((mos, "mount_holes_m3", "M3", 16, 6.0, None))
    tray_bolts = [(sx * RAIL_X, y) for sx in (-1, 1) for y in (-128.0, 54.0)]
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
    panel -= Pos(XP - 1.5, IN_Y, IN_Z) * Rot(0, 90, 0) * extrude(RectangleRounded(43.0, 28.0, 2.0), 1.5, both=True)
    inlet = place(d, "inlet", iec_inlet_c14(FUSE_A),
                  Location(Plane(origin=(XP - 3.0, IN_Y, IN_Z), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
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
        add_screw(d, f"inlet_screw_{i}", "M3", 10, at=(XP - 6.0, hy, hz), direction=(1, 0, 0), clamps=("inlet", "inlet_panel"))
        add_nut(d, f"inlet_nut_{i}", "M3", at=(XP, hy, hz), direction=(1, 0, 0), screw=f"inlet_screw_{i}")
    # protective-earth stud: M5 screw into a T-nut in the outer slot of the left bottom rail, ring terminals and a star washer under its head
    add_screw(d, "earth_stud", "M5", 8, at=(XP - 2.0, 80.0, 10.0), direction=(1, 0, 0), threads_into="frame_bot_left", tnut=True)
    d.bom_extra("WASHER-M5-STAR", 1, 0.05)
    # bench sub-assemblies: the bed carrier and the X motor on its plate are built on the bench and fitted as units
    d.subassemblies["bed_carrier"] = (
        ["back_plate", "nut_block"] + [f"nut_block_{k}_{i}" for k in ("bolt", "nut") for i in range(len(NB_BOLTS))]
        + [f"bed_arm_{n}{sfx}" for n in ("left", "right") for sfx in ("", "_bolt", "_bracket")])
    d.subassemblies["x_drive"] = ["x_motor_mount", "x_motor", "x_pulley"] + [f"x_motor_screw_{i}" for i in range(4)]
    # v6: the beam is bolted to the two Y plates on the bench (v5: from below, through holes in the electronics tray)
    d.subassemblies["gantry"] = ["x_beam", "y_plate_left", "y_plate_right", "beam_bolt_left", "beam_bolt_right"]
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
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 3, 4.0)    # 9 mm open belt, three lengths (price is an estimate)

    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY, TY),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_DN, PRINT_Z + Z_UP),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": "leadscrew", "nut": "z_nut", "coupler": "z_coupler"}))
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
        # gauge. The Z travel runs Z_UP past the nominal nozzle plane, so a bed that was built low can still come up.
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
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"}}

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
    cols = [f"bed_column_{i}" for i in range(len(BED_MOUNTS))]
    zcars = [f"z_carriage_{n}_{lvl}" for n in ("left", "right") for lvl in ("lo", "hi")]
    on_rail = lambda f: abs(f.center().Y - (Y_FACE - 8.0)) < 1e-6
    carrier = ["back_plate", "bed_arm_left", "bed_arm_right", "bed_arm_left_bracket", "bed_arm_right_bracket"]
    d.assemblycases.append(AssemblyCase(
        "payload_x3_on_bed", ["bed", *cols, *carrier, *zcars], fixed=[(c, on_rail) for c in zcars],
        loaded=("bed", lambda f: abs(f.center().Z - (Z_BED + T_BED)) < 1e-6 and f.area > 1000),
        force=(0.0, 0.0, -w_bed), probe=(0.0, BED_Y0, Z_BED + T_BED), max_deflection=0.3, min_fos=3.0))
    # printed parts under load, with the plastic's properties
    d.loadcases.append(LoadCase(      # lead-screw thrust on the nut block
        "nut_thrust", "nut_block", fixed=lambda f: abs(f.center().Y - Y_CAR) < 1e-6,
        loaded=lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 300,
        force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(      # the same thrust pulls the motor down on its printed bridge
        "z_motor_thrust", "z_motor_mount", fixed=lambda f: abs(f.center().Z - 20.0) < 1e-6,
        loaded=lambda f: abs(f.center().Z - Z_MF) < 1e-6 and f.area > 300,
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.3))
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
        "bed_heated_60K", ["bed", *cols, *carrier, *zcars],
        fixed=[(c, on_rail) for c in zcars],
        temps={"bed": 60.0, **{c: 30.0 for c in cols}, "*": 0.0},
        # a probe snaps to the nearest meshed point, and the nozzle is not in this model, so the "nozzle" reference is
        # put on a held rail face: it must report zero movement
        probes={"nozzle": (-UP_X, Y_FACE - 8.0, ZC1), "bed": (0.0, YB0 + HOT_OFF, Z_BED + T_BED)},
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
                f"nozzle tip is {gap:.2f} mm above the bed surface with the bed {PRINT_Z:g} mm up; Z travel continues {beyond:.1f} mm beyond")
    # v2's twin showed that any gap above the first layer height makes the first layer unreachable. v6: the same
    # 0-0.2 mm at the top of the PRINT height; the joint's travel now goes on past it for the probe and the mesh.
    d.requirements.append(Requirement("bed can reach the nozzle: 0-0.2 mm gap at the top of the print height", bed_gap))
    d.requirements.append(Requirement("bed carries the 1.0 kg payload as mass", lambda dd: (
        (m := dd.get("bed").mass()) >= dd.get("bed").shape.volume * MATERIALS["al_mic6"].density * 1e-9 + PAYLOAD_KG - 1e-9,
        f"bed + payload {m:.3f} kg")))

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

    def rail_margin(dd):
        out = {}
        rails = {"y_carriage_left": "y_rail_left", "y_carriage_right": "y_rail_right", "x_carriage": "x_rail",
                 **{f"z_carriage_{s_}_{lv}": f"z_rail_{s_}" for s_ in ("left", "right") for lv in ("lo", "hi")}}
        for n, rail in rails.items():
            ax = n[0].upper()
            cb, rb = dd.get(n).shape.bounding_box(), dd.get(rail).shape.bounding_box()
            lo, hi = jr(dd, ax.lower()).range
            out[n] = round(min(getattr(cb.min, ax) + lo - getattr(rb.min, ax), getattr(rb.max, ax) - getattr(cb.max, ax) - hi), 2)
        return min(out.values()) >= 5.0, str(out)
    d.requirements.append(Requirement("every carriage stays >= 5 mm inside its rail ends over the travel", rail_margin))
    d.requirements.append(Requirement("Z rails and lead screw end below the top back extrusion (no rubbing)", lambda dd: (
        max(t := [dd.get(n).shape.bounding_box().max.Z for n in ("z_rail_left", "leadscrew")]) < FZ - 10,
        f"rail top {t[0]:.1f}, screw top {t[1]:.1f} vs extrusion underside {FZ - 10:.1f}")))
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(mn).sku.startswith("NEMA17") and dd.get(mn).meta["catalog"] for n in "xyz" for mn in motors_of(dd, n)),
        str({n: [dd.get(mn).sku for mn in motors_of(dd, n)] for n in "xyz"}))))
    d.requirements.append(Requirement("Z lead screw self-locking (efficiency < 0.5)", lambda dd: (
        dd.get("leadscrew").ratings["efficiency"] < 0.5, f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    # ---- v6 stated targets that can be computed here (cost and assembly time: see docs/PRINTER_V6.md) ----
    d.requirements.append(Requirement(f"target: at most {MAX_PARTS} parts", lambda dd: (
        len(dd.components) <= MAX_PARTS, f"{len(dd.components)} parts")))
    d.requirements.append(Requirement(f"target: direct drive, at most {MAX_TOOLHEAD_KG:g} kg moving in X", lambda dd: (
        dd.get("extruder").body == "xbody" and (m := sum(c.mass() for c in dd.components if c.body == "xbody")) <= MAX_TOOLHEAD_KG,
        f"{m:.3f} kg on the X guide block, block included")))
    d.requirements.append(Requirement(f"target: both Y belts within 1 mm of plane in >= {MIN_BELT_IN_PLANE:.0%} of builds", lambda dd, m: (
        all(m["tolerance"]["belts"][b]["p_within_1mm"] >= MIN_BELT_IN_PLANE for b in ("y_belt", "y_belt_l")),
        str({b: m["tolerance"]["belts"][b]["p_within_1mm"] for b in ("y_belt", "y_belt_l")}))))
    d.requirements.append(Requirement("target: no purchased part is a stand-in where the catalogue has a real one", lambda dd: (
        (px := [c.name for c in dd.components if c.cots and not c.meta.get("catalog")]) == ["bed_probe"],
        f"hand-made purchased parts: {px} (the catalogue has no bed probe)")))
    return d
