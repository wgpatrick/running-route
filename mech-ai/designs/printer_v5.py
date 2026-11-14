"""printer_v5: printer_v4 after the trade study against eleven reference machines (reports/Printer trade study.md).

Same machine in kind: 180 x 180 x 150 mm, cartesian (X motor rides the Y beam), bed moves in Z on one lead screw,
24 V bed, 2020 frame (340 x 360 footprint), SKR Mini E3 V3 + Pi Zero 2 W, no custom PCB. What changed, in the
study's order of priority (docs/PRINTER_V5.md has the evidence and the numbers):

1. Stop machining everything. v4: 35 machined parts. v5: 4 machined flat plates, one set-up each (bed, the two Y
   plates, tool plate), the rest printed
   (ABS near heat or under steady load, PETG elsewhere), laser-cut sheet, or bought:
   - bed carrier -> see 2;  tool_plate -> flat 8 mm plate + printed hotend mount + printed belt block;
   - Y motor and idler mounts -> 3 mm laser-cut steel sheet (same flat shapes);
   - z_motor_mount -> printed ABS bridge standing on the bottom back rail (it no longer sits on the uprights, so
     the Z rails can use their whole length);
   - belt clamps, the left Y belt tower, tensioner blocks -> printed;
   - 20 turned spacers -> bought nylon / aluminium round spacers (proxies: the catalog has none).
2. Bed carrier is an assembly: a flat 5 mm sheet back plate on the four Z blocks, two 2020 arms end-tapped M5 into
   it with a cast corner bracket under each, and a printed ABS block for the floating lead-screw nut. The bed's
   levelling columns stand on the arms; the bed screws go into T-nuts in the arms' top slots.
3. Two MGN12H blocks per Z rail, 80 mm apart, on 300 mm rails (the same rail as the two Y rails). That needs
   284 -> 304 mm uprights: the frame's top ring went up 20 mm (FZ 314 -> 334).
4. Belt tensioners. Y (both belts): the motor mount slides along the frame slot on its three T-nut screws and is
   pushed back by an M3 jack screw in a printed anchor block. X: the idler sits on a printed slider on a slot in the
   right Y plate and is pulled outward by an M3 screw through a printed anchor.
5. Bed probe: an inductive probe (proxy, PL-08N class) beside the hotend, on the board's Z-STOP input. It replaces
   the Z-max microswitch, its bracket and the jack screw: Z homes on the bed surface itself, so re-levelling the bed
   no longer moves the nozzle gap. The four levelling screws stay (one Z motor cannot level the bed).
6. Lighter toolhead. The catalog has one extruder (0.24 kg); with it, the hotend (0.12 kg) and the guide block
   (0.054 kg) alone are 0.41 kg. The extruder therefore moved off the toolhead to the top back rail and feeds
   through a PTFE tube (Bowden), as on the Prusa MINI+ and Ender 3. This is the one change of kind; a lighter
   direct-drive extruder would be the better answer if the catalog had one.
7. Bed plate: cast tooling plate is what should be bought, but MATERIALS has no entry for it, so the part still
   says al6061 (reported).
Not done (optional items): 9 mm belts, blind frame joints. Kept: every v4 Requirement, the X and Y endstop geometry.

Layout (X = width, Y = depth with the front at -Y, Z = up) is v4's; see designs/printer_v4.py for the history.

Proxies / not modelled (flagged): hotend, silicone columns, bed probe, bought spacers are hand-made proxies
(uncatalogued_cots warnings are true); tapped holes, heat-set inserts, the hotend's two set screws, the PTFE tube and
its couplers, T-nuts and the corner brackets' screws are BOM lines, not geometry; payload is extra mass on the bed.
"""
import math

from build123d import Box, Cylinder, Location, Plane, Pos, RectangleRounded, RegularPolygon, Rot, extrude

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import Belt, Cable, ThermalCase
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       heater_cartridge, iec_inlet_c14, mosfet_module, psu_lrs, raspberry_pi_zero2w,
                                       relay_btt_v12, skr_mini_e3_v3, thermal_fuse, thermistor_cartridge)
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, clearance_hole,
                            endstop_switch, extruder_direct, extrusion_2020, fan, gt2_idler, gt2_pulley,
                            leadscrew_nut_t8, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place,
                            shaft_coupler)

# ---- brief (unchanged from v4) --------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 180.0, 180.0, 150.0
PAYLOAD_KG = 1.0
V_XY, A_XY = 250.0, 4000.0
V_Z, A_Z = 12.0, 200.0
MARGIN = 3.0
ENVELOPE = (420.0, 420.0, 480.0)

# ---- electrical choices (v4's final ones) ----------------------------------------
BED_W = 200.0
PSU_MODEL = "LRS-350-24"
BED_AWG, BED_INS = 16, "silicone"
HOTEND_W = 30.0                    # the cartridge E3D ships with the V6 (vendor/e3d_v6.json)
RUN_CURRENT = {"x": 0.28, "y": 1.20, "z": 0.28, "extruder": 0.60}   # A rms at the driver
FUSE_A = 8.0
T_TRAY = 3.0
TRAY_Y0, TRAY_Y1 = -138.0, 62.0    # clear of the corner brackets at both ends
Z_TRAY = 20.0 + T_TRAY

# ---- materials for printed parts --------------------------------------------------
HOT = "abs"      # on the toolhead, near the bed, on a motor, or under a steady load: ABS (ASA is not in MATERIALS)
COOL = "petg"    # on the cold frame

# ---- frame ----------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 334.0      # v5: top ring +20 so that 300 mm Z rails with two blocks each fit the uprights
RAIL_X = FX / 2 - 10                  # side extrusions / Y rails
TX, TY = PRINT_X / 2, PRINT_Y / 2     # +/- travel

# ---- Z axis ---------------------------------------------------------------------
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
BED_Y0, BED_Y1 = Y_CAR - BED, Y_CAR
BED_CY = (BED_Y0 + BED_Y1) / 2
ARM_X = 65.0           # 2020 arms: inboard of the uprights so their end screws can be driven from behind
ARM_L = 210.0
H_COL = 18.0           # installed height of the silicone levelling columns (20 free, 2 mm pre-compression)
# bed mounts stand on the arms; the pad (200 wide, 140 deep) lies between the front and the rear pair
BED_MOUNTS = [(-ARM_X, BED_Y1 - 30.0), (ARM_X, BED_Y1 - 30.0), (-ARM_X, BED_Y1 - 200.0), (ARM_X, BED_Y1 - 200.0)]
NUT_PIN = (0.0, 8.0)   # the one flange hole of the T8 nut that carries the anti-rotation pin
NUT_FLOAT = 1.5        # radial room around the nut barrel and along the pin slot
Z_OVER = 3.0           # mechanical Z travel available beyond each end of the print height
Z_SPACING = 80.0       # v5: two blocks per rail, centre to centre
Z_RAIL_L = 300.0
Z_RAIL_C = 22.0 + Z_RAIL_L / 2   # rail 22 .. 322: on the upright only, ends below the top back rail (FZ - 10)

# ---- gantry ---------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13          # underside of the Y plates
T_YP = 6.0
Z_BEAM = Z_PLATE + T_YP + 10
Z_TOP = Z_BEAM + 10 + 13       # top of the X carriage
HOT_OFF = 32.5                 # hotend axis behind the beam centre
YB0 = BED_CY - HOT_OFF         # beam centre Y at home (nozzle over the bed centre)
X_MOTOR_X = -(FX / 2 + 27.0)
T_TP = 8.0                     # tool plate: 8 mm plate, machined flat with counterbores (nozzle stiffness; see below)
T_COL = 12.0                   # printed hotend mount depth below the plate
Z_NOZZLE = Z_TOP - 60          # nozzle tip (hotend proxy is 60 long, its top seats under the tool plate at Z_TOP)
PR = 20 * 2.0 / math.pi / 2     # pitch radius of the 20T pulleys / idlers
BWX, BWY = 12.0, 12.0           # GT2 belt widths
P_BC = lambda w: 7.0 + (w + 1) / 2      # gt2_pulley belt centre above its hub bottom
I_H = lambda w: w + 2.5                 # gt2_idler height
MT_Y = 3.0                     # Y motor / idler mounts: 3 mm steel sheet
XB = 28.0                      # X belt centre line, in front of the beam centre
X_IDLER_X = RAIL_X - 30.0      # v5: 10 mm further in, to make room for the tensioner inside the frame line
X_SP = 8.0                     # height of the X idler slider under the idler; also lifts the belt over the X endstop
Z_XB = Z_PLATE + T_YP + X_SP + I_H(BWX) / 2  # X belt centre height
XA_Y = YB0 - XB + PR           # near (anchored) run of the X belt
TAB_Y0 = XA_Y + 0.7 + 0.03     # belt block front face = belt tooth side
Y_SP, Y_SP_L = 6.0, 8.0        # Y idler spacers, right and left (bought)
YB_X = FX / 2 + MT_Y + Y_SP + I_H(BWY) / 2       # Y belt plane, outboard of the right frame rail
YM_Y, YI_Y = FY / 2 + 24.0, -128.0      # Y motor pulley (behind the frame) and Y idler (front)
MT = MT_Y
Z_YA = Z_PLATE + T_YP + 0.7    # upper (anchored) run of the Y belt lies on the right Y plate
Z_YC = Z_YA - PR
# second (left) Y drive: belt plane outboard of the left rail, loop ABOVE the left Y plate on a clamp tower
TOW_H = 25.0
YBL_X = -(FX / 2 + MT_Y + Y_SP_L + I_H(BWY) / 2)
TOW_X1 = YBL_X + BWY / 2 + 0.3
TOW_X0 = TOW_X1 - 20.0
TOW_Y0, TOW_Y1 = YB0 - 9.0, YB0 + 13.5
# three M3x40 through clamp bar, tower and Y plate to nuts under the plate (behind the X motor body); the third
# passes between the two belt ends
TOW_BOLTS = [(TOW_X0 + 4.5, YB0 + 0.5), (TOW_X0 + 4.5, YB0 + 9.5), (YBL_X, YB0 + 2.25)]
Z_TOW = Z_PLATE + T_YP + TOW_H
Z_YAL = Z_TOW + 0.7            # lower (anchored) run of the left Y belt lies on the tower
Z_YCL = Z_YAL + PR
YI_YL = -156.0                 # left Y idler: in front of the sweep of the X motor pad
Z_XI = Z_XB - I_H(BWX) / 2              # underside of the X idler
NOZZLE_GAP = 0.1               # bed surface -> nozzle with the bed at the top: must not exceed the first layer height
BELT_ADJ = 3.0                 # +/- travel of each belt tensioner
PH3, PH5 = 4.2, 6.0            # clearance holes in PRINTED parts (they come out about 0.15 mm small): M3, M5
PHC = 3.8                      # belt clamps and the belt tower: tighter, because their play moves the belt sideways
SH3 = 3.6                      # M3 clearance in laser-cut sheet where four screws must start at once (ISO 273 coarse)

# bed heights follow from the nozzle
Z_BED = Z_NOZZLE - NOZZLE_GAP - T_BED - PRINT_Z   # bed underside at home (bed at the bottom)
Z_FL = Z_BED - H_COL                              # top of the arms (the columns stand on them)
Z_ARM = Z_FL - 10.0                               # arm centre line
ZC2 = FZ - 190.0                                  # upper Z block centre at home: 5.3 mm of rail left above it at the top
ZC1 = ZC2 - Z_SPACING                             # lower Z block centre at home: 16 mm of rail left below it at -Z_OVER
BP_Z0, BP_Z1 = ZC1 - 23.0, ZC2 + 23.0             # back plate covers both blocks and the arm ends
BP_W = 214.0                                      # 5 mm of sheet outside the outer screw holes
Z_TAB = 107.0                                     # underside of the nut block at home (clears the coupler at -Z_OVER)
NB_H = 14.0                                       # nut block height
NB_BOLTS = [(sx * 23.0, Z_TAB + dz) for sx in (-1, 1) for dz in (0.0, 20.0)]
# Lever switches (X and Y): the trigger is the lever's operating position at its tip, 10.6 from the switch origin along
# the stroke and 9 to one side.
ES_TRIG, ES_SIDE, ES_PIN_D = 10.6, 9.0, 2.5       # ES_PIN_D: clearance drill for the switch terminals under the board
# bed probe: inductive, sensing face up from the nozzle by its switching distance on aluminium less the first-layer
# gap, so it switches as the bed reaches the nozzle
PRB_SN = 3.2                                      # 8 mm on steel x 0.4 for aluminium: typical, unverified
PRB_X = 33.0                                      # probe axis, right of the nozzle (14 mm of air to the heater block)
Z_PRB = Z_NOZZLE + PRB_SN - NOZZLE_GAP            # sensing face


def hotend() -> Stock:
    """PROXY (not in the catalog): V6-style hotend. Local frame: axis Z, top at Z=0, nozzle tip at Z=-60."""
    body = Pos(0, 0, -20) * Cylinder(11, 40) + Pos(0, 0, -47.5) * Box(20, 16, 15) + Pos(0, 0, -57.5) * Cylinder(2, 5)
    return Stock(body, "HOTEND-V6", "UNVERIFIED proxy: V6-style hotend with heater block (Bowden top)", 0.12,
                 material="al6061", cost_usd=25.0)


def silicone_column() -> Stock:
    """PROXY (not in the catalog): silicone bed-levelling column, 12 OD x 4 bore, drawn at its installed height
    H_COL (20 mm free). Local frame: axis Z, bottom at Z=0.  Material is the nearest in the library (belt rubber,
    E = 50 MPa); real silicone is roughly ten times softer, so the thermal restraint on the bed is overstated."""
    body = Pos(0, 0, H_COL / 2) * (Cylinder(6.0, H_COL) - Cylinder(2.0, H_COL))
    return Stock(body, "BED-COLUMN-SIL-20", "UNVERIFIED proxy: silicone bed levelling column 12 x 20", 0.002,
                 material="rubber_gt2", cost_usd=0.5)


def bed_probe() -> Stock:
    """PROXY (not in the catalog): rectangular inductive proximity sensor of the PL-08N class (NPN, normally open,
    8 mm nominal on steel), 18 x 18 x 36 mm, two M3 through holes across it. Local frame: sensing face on Z=0, body
    above, holes along X at Z = 8 and 28. `trigger` is where a flat aluminium target switches it. Dimensions, mass and
    switching distance are recalled class values, not read from a data sheet."""
    body = Pos(0, 0, 18.0) * Box(18.0, 18.0, 36.0)
    holes = [(0.0, 0.0, 8.0), (0.0, 0.0, 28.0)]
    for _, _, z in holes:
        body -= Pos(0, 0, z) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, 18.0)
    tpl = {"kind": "endstop", "ports": {"out": dict(kind="endstop", connector="JST-XH", max_a=1.0, conductors=3)},
           "ratings": {"switching_distance_steel_mm": 8.0, "switching_distance_aluminium_mm": PRB_SN, "max_ambient_c": 70.0},
           "sources": {k: "PL-08N class value, recalled (typical, unverified)" for k in
                       ("switching_distance_steel_mm", "switching_distance_aluminium_mm", "max_ambient_c")},
           "params": {},
           "product": dict(product="Inductive proximity sensor, 8 mm, NPN normally open, 6-36 V (PL-08N class)",
                           vendor="commodity", part_number=None, form="component", off_the_shelf=True, custom_pcb=False,
                           builder_work="crimp a 3-way JST-XH; feed it from 24 V; if the sensor has an internal pull-up to "
                                        "its supply, fit a BAT85 diode in the signal lead (stock practice, no PCB)")}
    return Stock(body, "PROBE-INDUCTIVE-8MM", "UNVERIFIED proxy: inductive bed probe 18 x 18 x 36, 8 mm NPN NO", 0.02,
                 material="abs", cost_usd=6.0, ratings={"electrical": tpl},
                 interfaces={"trigger": [(0.0, 0.0, -PRB_SN)], "mount_holes_m3": holes})


def round_spacer(od: float, bore: float, length: float, material: str = "nylon_pa12") -> Stock:
    """PROXY (not in the catalog): bought unthreaded round spacer. Local frame: axis Z, bottom at Z=0."""
    body = Pos(0, 0, length / 2) * (Cylinder(od / 2, length) - Cylinder(bore / 2, length))
    kind = "NYLON" if material == "nylon_pa12" else "AL"
    dens = 1010e-9 if material == "nylon_pa12" else 2700e-9
    return Stock(body, f"SPACER-{kind}-{od:g}x{bore:g}x{length:g}",
                 f"UNVERIFIED proxy: round spacer {od:g} OD x {bore:g} bore x {length:g} long", body.volume * dens,
                 material=material, cost_usd=0.1)


def spacer(d, name, at, length, bore, body="world"):
    """Bought nylon spacer (6 mm OD), axis Z, bottom at `at`. v4 turned these from bar."""
    place(d, name, round_spacer(6.0, bore, length), Location(tuple(at)), body=body)


def mount_pcb(d, name, comp, holes_key, size, screw_len, sp_len, group):
    """A board on spacers on the tray: screw from the top through board, spacer and tray into a nut underneath."""
    hole_d = clearance_hole(size)
    names = []
    for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][holes_key]):
        spacer(d, f"{name}_spacer_{i}", (hx, hy, Z_TRAY), sp_len, hole_d)
        pcb_t = 1.5 if size == "M2.5" else 1.6
        add_screw(d, f"{name}_screw_{i}", size, screw_len, at=(hx, hy, Z_TRAY + sp_len + pcb_t),
                  clamps=(name, f"{name}_spacer_{i}", "electronics_tray"))
        add_nut(d, f"{name}_nut_{i}", size, at=(hx, hy, 20.0), direction=(0, 0, -1), screw=f"{name}_screw_{i}")
        names += [f"{name}_spacer_{i}", f"{name}_screw_{i}", f"{name}_nut_{i}"]
    group += [name] + names


def hex_pocket_y(x, y_face, z, depth, into=-1, af=5.9):
    """Pocket for an M3 nut cut into a face at y_face, going `into` (-1: towards -Y, +1: towards +Y)."""
    h = extrude(Rot(0, 0, 30) * RegularPolygon(af / 2, 6, major_radius=False), depth)   # flats along X, like add_nut's
    return Pos(x, y_face, z) * Rot(90 if into < 0 else -90, 0, 0) * h


def fillet_z(x, y, sx, sy, r, z0, z1):
    """Material that rounds a vertical inside corner at (x, y); the open quadrant is towards (sx, sy)."""
    return (Pos(x + sx * r / 2, y + sy * r / 2, (z0 + z1) / 2) * Box(r, r, z1 - z0)
            - Pos(x + sx * r, y + sy * r, (z0 + z1) / 2) * Cylinder(r, z1 - z0))


def fillet_x(y, z, sy, sz, r, x0, x1):
    """Same for an inside corner that runs along X at (y, z)."""
    return (Pos((x0 + x1) / 2, y + sy * r / 2, z + sz * r / 2) * Box(x1 - x0, r, r)
            - Pos((x0 + x1) / 2, y + sy * r, z + sz * r) * Rot(0, 90, 0) * Cylinder(r, x1 - x0))


def slot_z(x, y, angle_deg, half_len, width, z0, z1):
    """Round-ended slot through a horizontal plate, +/- half_len along the direction angle_deg (from +X)."""
    h = z1 - z0
    return Pos(x, y, (z0 + z1) / 2) * Rot(0, 0, angle_deg) * (
        Box(2 * half_len, width, h) + Pos(-half_len, 0, 0) * Cylinder(width / 2, h)
        + Pos(half_len, 0, 0) * Cylinder(width / 2, h))


def back_plate_shape(carriage_holes):
    """Flat 5 mm sheet on the four Z blocks (laser cut, through holes only). The arms butt against its front face."""
    yc = (Y_PF + Y_CAR) / 2
    ycyl = lambda r: Rot(90, 0, 0) * Cylinder(r, T_BP)
    p = Pos(0, yc, (BP_Z0 + BP_Z1) / 2) * Box(BP_W, T_BP, BP_Z1 - BP_Z0)
    # lightening window between the two lower blocks (an 8 mm tie is left along the bottom edge)
    p -= Pos(0, yc, BP_Z0 + 31.0) * Rot(90, 0, 0) * extrude(RectangleRounded(136.0, 46.0, 5.0), T_BP / 2, both=True)
    for hx, hy, hz in carriage_holes:
        p -= Pos(hx, yc, hz) * ycyl(SH3 / 2)
    for sx in (-1, 1):
        p -= Pos(sx * ARM_X, yc, Z_ARM) * ycyl(clearance_hole("M5") / 2)          # arm end screw (blind joint)
        # corner bracket screw: a vertical slot, because the cast bracket has a 4 x 17 mm locating rib standing 1 mm
        # out of each leg (it normally sits in a T-slot); here it sits in this slot and keys the bracket
        p -= Pos(sx * ARM_X, yc, Z_ARM - 20.5) * (Box(clearance_hole("M5"), T_BP, 13.0)
                                                   + Pos(0, 0, 6.5) * ycyl(clearance_hole("M5") / 2)
                                                   + Pos(0, 0, -6.5) * ycyl(clearance_hole("M5") / 2))
    for x, z in NB_BOLTS:
        p -= Pos(x, yc, z) * ycyl(clearance_hole("M3") / 2)
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
        b -= Pos(x, Y_CAR + 3.0, z) * Rot(90, 0, 0) * Cylinder(PH3 / 2, 6.0)
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
        m += Pos(sx * (x1 + MM_FOOT_W / 2), (MM_Y0 + UP_Y + 9.0) / 2, 23.0) * Box(MM_FOOT_W, UP_Y + 9.0 - MM_Y0, 6.0)
        m -= Pos(sx * MM_FOOT_X, UP_Y, 23.0) * Cylinder(PH5 / 2, 6.0)
    m -= Pos(0, LS_Y, Z_MF + T_MM / 2) * Cylinder(11.5, T_MM)
    m -= Pos(0, (LS_Y + MM_Y1) / 2, Z_MF + T_MM / 2) * Box(23.0, MM_Y1 - LS_Y, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(x, LS_Y + y, Z_MF + T_MM / 2) * Cylinder(PH3 / 2, T_MM)
    return m


TAB_Z0 = Z_PLATE + T_YP + 1.5
# X endstop: flat on the left Y plate, pressed in -X by the left end of the belt clamp bar at x = -TX
X_ES_X0 = -TX - 20.0 - ES_TRIG   # switch origin X (trigger point is ES_TRIG further in +X)
X_ES_Y0 = TAB_Y0 - 1.5 - ES_SIDE # lever tip (ES_SIDE towards +Y) on the clamp bar's end face
PAD_FRONT = YB0 - XB - 24.0      # front edge of the X motor pad: it presses the Y endstop at y = -TY
XC_Y0 = TAB_Y0 - 5.0             # front face of the X belt clamp bar
XC_Z1 = Z_XB + 13.0              # top of the clamp bar; it runs down to TAB_Z0 so its end face strikes the X endstop
X_CLAMP_SCREWS = [(-13.0, Z_XB + 9.7), (13.0, Z_XB + 9.7), (0.0, Z_XB - 9.5)]
NUT_POCKET = 2.6                 # depth of a captive M3 nut pocket
T_FLG = 5.0                      # belt block flange under the two front carriage screws
CB = 3.2                         # counterbore depth for an M3 cap head in the tool plate
PLATE_Y0 = YB0 - 14.0            # front edge of the tool plate
BLK_Y1 = YB0 - 14.0              # rear face of the belt block (0.5 mm in front of the carriage)
TP_REAR = HOT_OFF + 24.5         # rear edge of the tool plate and of the hotend mount, behind the beam centre
COL_Y0 = 15.5                    # front of the hotend mount (the Y plates end at 14.3)
EAR = 6.0                        # hotend mount is this much wider on the left, for the part-cooling fan
MOUNT_SCREWS = [(x, y) for x in (-16.3, 16.3) for y in (22.0, 46.5)]     # tool plate -> hotend mount, y from YB0
PRB_WALL_X0, PRB_WALL_T = PRB_X + 9.0, 5.0
FAN_Z = Z_TOP - 18.0             # both 30 mm fans: centre height (their upper screws are 6 mm below the plate)
FAN_LUG = 3.5                    # printed wall between a fan and its captive nut (M3x16 = fan 10 + 3.5 + nut 2.4)
NUT_SLOT = 3.7                   # nut slot width along the screw
PF_X = -23.0 - EAR - 5.0         # part-cooling fan mid-plane
PRB_SCREW_Z = [Z_PRB + 8.0, Z_PRB + 28.0]


def tool_plate_shape():
    """Flat 8 mm plate over the X carriage; behind the carriage the hotend seats against its underside. Machined from
    plate in one set-up from the top (counterbores for the two rear carriage screws and the four mount bolts).
    Why machined and 8 mm: with a 5 mm laser-cut sheet the nozzle stiffness in Y fell from v4's 1260 N/mm to
    650 N/mm (screw-only joints), which put the Y resonance below v4's despite the lighter toolhead; 8 mm sheet
    cannot be used because no standard M3 length leaves 3 .. 3.5 mm in the carriage's threads without a counterbore."""
    y1 = YB0 + TP_REAR
    zc = Z_TOP + T_TP / 2
    tp = Pos(0, (PLATE_Y0 + y1) / 2, zc) * Box(46.0, y1 - PLATE_Y0, T_TP)
    cbore = lambda x, y: Pos(x, y, Z_TOP + T_TP - CB / 2) * Cylinder(3.0, CB)
    for x in (-10, 10):
        for y in (-10, 10):
            tp -= Pos(x, YB0 + y, zc) * Cylinder(clearance_hole("M3") / 2, T_TP)
            if y > 0:
                tp -= cbore(x, YB0 + y)
    for x, y in MOUNT_SCREWS:
        tp -= Pos(x, YB0 + y, zc) * Cylinder(clearance_hole("M3") / 2, T_TP)
        tp -= cbore(x, YB0 + y)
    tp -= Pos(0, YB0 + HOT_OFF, zc) * Cylinder(4.0, T_TP)
    return tp


def belt_block_shape():
    """Printed block in front of the X carriage that carries the belt ends. It hooks over the front edge of the tool
    plate and is clamped by the two front carriage screws (printed upside down, flange on the bed: no overhang); the belt clamp screws run into captive nuts in pockets on
    its rear face (the carriage closes the pockets)."""
    zt = Z_TOP + T_TP + T_FLG
    b = Pos(0, (TAB_Y0 + BLK_Y1) / 2, (TAB_Z0 + Z_TOP) / 2) * Box(40.0, BLK_Y1 - TAB_Y0, Z_TOP - TAB_Z0)
    b += Pos(0, (TAB_Y0 + PLATE_Y0 - 0.2) / 2, (Z_TOP + zt) / 2) * Box(40.0, PLATE_Y0 - 0.2 - TAB_Y0, zt - Z_TOP)
    b += Pos(0, (TAB_Y0 + YB0 - 4.5) / 2, zt - T_FLG / 2) * Box(40.0, YB0 - 4.5 - TAB_Y0, T_FLG)
    for x in (-10, 10):
        b -= Pos(x, YB0 - 10, zt - T_FLG / 2) * Cylinder(PH3 / 2, T_FLG)
    for x, z in X_CLAMP_SCREWS:
        b -= Pos(x, (TAB_Y0 + BLK_Y1) / 2, z) * Rot(90, 0, 0) * Cylinder(PH3 / 2, BLK_Y1 - TAB_Y0)
        b -= hex_pocket_y(x, BLK_Y1, z, NUT_POCKET)
    return b


def hotend_mount_shape():
    """Printed ABS frame under the tool plate around the top of the hotend's heat sink: a 24 x 24 pocket (the hotend's
    top face seats on the aluminium plate above; two M3 set screws in heat-set inserts push the heat sink into the
    pocket's front-left corner), the two fans on its rear and left faces, and a wall on the right that drops to carry
    the bed probe. Printed upside down (plate face on the bed): no overhangs."""
    x0, x1 = -23.0 - EAR, 23.0
    hy = YB0 + HOT_OFF
    zc = Z_TOP - T_COL / 2
    c = Pos((x0 + x1) / 2, YB0 + (COL_Y0 + TP_REAR) / 2, zc) * Box(x1 - x0, TP_REAR - COL_Y0, T_COL)
    xw1 = PRB_WALL_X0 + PRB_WALL_T
    c += Pos((x1 + xw1) / 2, hy, zc) * Box(xw1 - x1, 18.0, T_COL)
    zw0 = Z_PRB + 2.0
    c += Pos(PRB_WALL_X0 + PRB_WALL_T / 2, hy, (zw0 + Z_TOP - T_COL) / 2) * Box(PRB_WALL_T, 18.0, Z_TOP - T_COL - zw0)
    pk = Box(18, 24, T_COL) + Box(24, 18, T_COL)
    for cx in (-9, 9):
        for cy in (-9, 9):
            pk += Pos(cx, cy, 0) * Cylinder(3.0, T_COL)
    c -= Pos(1.0, hy + 1.0, zc) * pk
    for z in PRB_SCREW_Z:
        c -= Pos(PRB_WALL_X0 + PRB_WALL_T / 2, hy, z) * Rot(0, 90, 0) * Cylinder(PH3 / 2, PRB_WALL_T)
    for x, y in MOUNT_SCREWS:      # through bolts from the plate to nuts under the mount
        c -= Pos(x, YB0 + y, zc) * Cylinder(PH3 / 2, T_COL)
    # fans: each upper fan screw passes a 4 mm lug into a captive M3 nut in a slot that is open to the top face (the
    # tool plate closes it). No thread in the plastic, and the nuts float enough to meet the fan's own hole pitch.
    zs, hs = FAN_Z + 12.0, Z_TOP - (FAN_Z + 12.0) + 3.35           # slot from 3.35 below the screw axis up to the top
    for y in (-12.0, 12.0):       # part-cooling fan, screws along +X
        c -= Pos((x0 + x0 + FAN_LUG) / 2, hy + y, zs) * Rot(0, 90, 0) * Cylinder(PH3 / 2, FAN_LUG)
        c -= Pos(x0 + FAN_LUG + NUT_SLOT / 2, hy + y, Z_TOP - hs / 2) * Box(NUT_SLOT, 5.8, hs)
    yr = YB0 + TP_REAR
    for x in (-12.0, 12.0):       # heat-sink fan, screws along -Y
        c -= Pos(x, yr - FAN_LUG / 2, zs) * Rot(90, 0, 0) * Cylinder(PH3 / 2, FAN_LUG)
        c -= Pos(x, yr - FAN_LUG - NUT_SLOT / 2, Z_TOP - hs / 2) * Box(5.8, NUT_SLOT, hs)
    return c


USE_CUTOFFS = USE_MOSFET = True
EXM_Y = LS_Y + 24.0              # extruder axis: behind the top back rail


def build_electrical(d: Design) -> Electrical:
    """Devices, looms, wires and firmware settings. Every device is a stock product (Device.product says which).
    v5: the Z microswitch is gone and the inductive bed probe takes its Z-STOP input; the extruder is on the frame."""
    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend_heater", "hotend_thermistor", "hotend_fan",
               "part_fan", "x_endstop", "y_endstop", "bed_probe", "x_motor", "z_motor", "extruder"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed")      # the thermal model takes the plate's mass and area from this part
    for nm in ("y_motor", "y_motor_l"):       # two motors on one driver, coils in parallel (the board's ZAM/ZBM pair)
        device_from(el, d, nm, connection="parallel")
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", ratings={"max_temp_c": 180.0},
                    sources={"points": "Klipper 'Generic 3950' (Keenovo R-T table)", "tau_s": "assumed 10 s (typical, unverified)"},
                    sensor_type="Generic 3950", points=THERMISTORS["Generic 3950"], tau_s=10.0, node="pad")
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
    XL = -154.0      # left looms run under the left top rail, clear of the tensioner block that hooks under it
    # ---- looms (centre lines; one bundle radius off surfaces). Consecutive waypoints on different bodies flex.
    P1 = (124.0, 146.0, FZ + 2.0)
    el.loom("toolhead", [Waypoint("xbody", (-15.0, YB0 + 50.0, Z_TOP + T_TP + 3.0), clamp="tool_plate"),
                         Waypoint("world", (124.0, 177.0, FZ + 13.0), clamp="frame_top_back"), Waypoint("world", P1)],
            flex_length={0: 420.0})
    el.loom("top_back", [("world", (114.0, 184.0, FZ)), ("world", (27.0, 190.0, FZ))])       # to the extruder
    el.loom("drop_right", [("world", P1), ("world", (132.0, 150.0, FZ - 34.0)), ("world", (145.0, 168.0, FZ - 74.0)),
                           ("world", (145.0, 170.0, 60.0)), ("world", (145.0, 150.0, 34.0))])
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (149.0, 46.0, zt)), ("world", (149.0, -26.0, zt))])
    el.loom("back", [("world", (130.0, 150.0, 32.0)), ("world", (30.0, 150.0, 28.0))])
    el.loom("gantry", [Waypoint("ybody", (X_MOTOR_X, YB0 - XB, Z_PLATE - 37.0), clamp="x_motor"),
                       Waypoint("world", (XL, YB0 - XB, FZ - 13.0), clamp="frame_top_left")], flex_length={0: 170.0})
    el.loom("top_left", [("world", (XL, -20.0, FZ - 13.0)), ("world", (XL, 136.0, FZ - 13.0))])
    el.loom("drop_left", [("world", (XL, -27.0, FZ - 13.0)), ("world", (XL, -120.0, FZ - 13.0)),
                          ("world", (-143.0, -150.0, FZ - 24.0)), ("world", (-143.0, -170.0, FZ - 64.0)),
                          ("world", (-143.0, -170.0, 60.0)), ("world", (-143.0, -150.0, 35.0)), ("world", (-110.0, -132.0, zt))])
    el.loom("front", [("world", (-110.0, -132.0, zt)), ("world", (70.0, -132.0, zt))])
    el.loom("bed", [Waypoint("zbody", (0.0, Y_PF - 3.0, Z_TAB + 19.0), clamp="back_plate"),
                    Waypoint("zbody", (0.0, Y_PF - 3.0, Z_TAB - 4.0), clamp="back_plate"),
                    Waypoint("world", (0.0, TRAY_Y1 - 4.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 300.0})
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
    # ---- toolhead: heater, thermistor, two fans, probe (the extruder motor is no longer in the flexing loom)
    el.wire("hotend heater", "control_board.E0", "hotend_heater.in", 20, insulation="silicone", via=tool, pigtail=(150.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, via=tool, pigtail=(150.0, "fiberglass"))
    el.wire("heat-sink fan", "control_board.FAN1", "hotend_fan.in", 26, via=tool)
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    el.wire("bed probe", "control_board.Z-STOP", "bed_probe.out", 26, conductors=3, insulation="silicone", via=tool,
            note="signal and 0 V on the Z-STOP header; the sensor's + lead goes to 24 V (not modelled). Homes Z and "
                 "probes the bed mesh: add [probe] pin ^PC2 with z_offset, [safe_z_home] and [bed_mesh] to printer.cfg")
    el.wire("extruder motor", "control_board.EM", "extruder.coils", 24, conductors=4, via=["tray_right", "drop_right", "top_back"])
    # ---- axes. The Y pair is on the board's doubled "Z" connectors (one driver); the Z motor is on the "Y" driver.
    el.wire("X motor", "control_board.XM", "x_motor.coils", 24, conductors=4, via=left + ["gantry"])
    el.wire("X endstop", "control_board.X-STOP", "x_endstop.out", 26, conductors=3, via=left + ["gantry"])
    el.wire("Y endstop", "control_board.Y-STOP", "y_endstop.out", 26, conductors=3, via=left)
    el.wire("Y motor left", "control_board.ZBM", "y_motor_l.coils", 24, conductors=4, via=left + ["top_left"],
            note="mirror-image motor: swap one coil pair at the connector so both turn the belts the same way")
    el.wire("Y motor right", "control_board.ZAM", "y_motor.coils", 24, conductors=4, via=["tray_right", "drop_right"])
    el.wire("Z motor", "control_board.YM", "z_motor.coils", 24, conductors=4, via=["tray_right", "back"])
    el.wire("host serial + 5 V", "control_board.TFT", "host.GPIO", 26, conductors=4)
    # ---- firmware (Klipper). PID values are left to the simulated PID_CALIBRATE.
    el.firmware = {
        "kind": "klipper",
        "steppers": {"x": {"run_current": RUN_CURRENT["x"]}, "y": {"run_current": RUN_CURRENT["y"]},
                     "z": {"run_current": RUN_CURRENT["z"]},
                     "extruder": {"motors": ["extruder"], "run_current": RUN_CURRENT["extruder"], "rotation_distance": 7.71}},
        "heaters": {"extruder": {"heater": "hotend_heater", "sensor": "hotend_thermistor", "control": "pid", "min_temp": 0,
                                 "max_temp": 280, "targets": [250.0], "verify_heater": {}},
                    "heater_bed": {"heater": "bed_heater", "sensor": "bed_ntc", "control": "pid", "min_temp": 0,
                                   "max_temp": 120, "targets": [60.0, 100.0], "verify_heater": {}}},
        "fans": {"part_fan": {"device": "part_fan", "role": "part"}, "hotend_fan": {"device": "hotend_fan", "role": "heatsink"}},
    }
    # hot parts wires must be rated for: the heater block (not the whole hotend proxy) and the bed plate
    hb = (-10.0, YB0 + HOT_OFF - 8.0, Z_TOP - 60.0, 10.0, YB0 + HOT_OFF + 8.0, Z_TOP - 40.0)
    el.hot_parts = {"hotend": {"temp": 250.0, "box": hb}, "bed": 100.0}
    # the bay is the open tray under the bed: air leaves through the open sides of the frame
    el.bay = Bay(devices=[n for n in ("psu", "control_board", "host", "psu_relay", "bed_mosfet") if n in el.devices],
                 enclosed=False, vent_area_m2=0.02, height_m=0.05)
    el.sync_cables(d)
    add_electrical_bom(el, d)
    d.bom_extra(f"FUSE-5x20-T{FUSE_A:g}A", 2, 0.3)
    return el


def build() -> Design:
    d = Design("printer_v5", envelope=ENVELOPE, base="frame_bot_left")
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
    # v5: two blocks on each 300 mm rail, Z_SPACING apart; the rails run the whole upright because the Z motor mount
    # moved from the uprights' front faces to the bottom back rail
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
    # bed carrier (v5): sheet back plate + two 2020 arms. Each arm is held by an M5 screw through the plate into its
    # tapped end (driven from behind, between the upright and the lead screw) and a cast corner bracket underneath
    # (T-nut in the arm's bottom slot, screw and nut through the plate).
    d.add("back_plate", back_plate_shape(carriage_holes), material="al6061", body="zbody", process="sheet")
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"bed_arm_{n}", extrusion_2020(ARM_L), Location((sx * ARM_X, Y_PF - ARM_L / 2, Z_ARM), (0, 0, 90)),
              body="zbody")
        add_screw(d, f"bed_arm_{n}_bolt", "M5", 16, at=(sx * ARM_X, Y_CAR, Z_ARM), direction=(0, -1, 0), body="zbody",
                  threads_into=f"bed_arm_{n}", clamps=("back_plate",))
        add_corner_bracket(d, f"bed_arm_{n}_bracket", f"bed_arm_{n}", "back_plate",
                           (sx * ARM_X, Y_PF, Z_ARM - 10.0), (0, -1, 0), (0, 0, -1), body="zbody")
    d.bom_extra("NUT-M5", 2, 0.05)       # the brackets' plate-side screws take nuts, not T-nuts
    # floating nut: it hangs under the printed block (the bed's weight keeps the block sitting on the nut flange); the
    # pin screw gets a nyloc nut under the flange left 0.2 mm slack, so the nut slides +/-NUT_FLOAT and cannot turn
    d.add("nut_block", nut_block_shape(), material=HOT, body="zbody", process="printed", meta={"print_up": "+Y"})
    for i, (x, z) in enumerate(NB_BOLTS):
        add_screw(d, f"nut_block_bolt_{i}", "M3", 16, at=(x, Y_PF, z), direction=(0, 1, 0), body="zbody",
                  clamps=("back_plate", "nut_block"))
        add_nut(d, f"nut_block_nut_{i}", "M3", at=(x, Y_CAR + 6.0, z), direction=(0, 1, 0), body="zbody",
                screw=f"nut_block_bolt_{i}")
    place(d, "z_nut", leadscrew_nut_t8(), Location((0, LS_Y, Z_TAB - 3.5)), body="zbody")
    add_screw(d, "nut_pin", "M3", 20, at=(NUT_PIN[0], LS_Y + NUT_PIN[1], Z_TAB + NB_H), body="zbody", threads_into="z_nut")
    d.bom_extra("NYLOC-M3", 1, 0.05)
    # bed: buy it as cast tooling plate (MIC6 / ATP5). MATERIALS has no entry for cast plate, so the model says 6061.
    # Machined because the screw heads are counterbored below the print surface and the face must be flat.
    bed_own = BED * BED * T_BED * 2700e-9
    d.add("bed", bed_shape_(), material="al6061", body="zbody", mass_kg=bed_own + PAYLOAD_KG, process="machined")
    # silicone pad, 200 wide x 140 deep so the four mounts stand in front of and behind it; leads leave at the back
    place(d, "bed_heater", bed_heater_pad(200.0, 140.0, BED_W), Location((0, BED_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed", "bond")
    place(d, "bed_tco", thermal_fuse(133.0, 109.0, 15.0), Location((-25.0, BED_Y1 - 5.0, Z_BED - 2.0)), body="zbody")
    d.join("bed_tco", "bed", "bond")
    # bed mounts: M3x25 from the top (head counterbored in the bed) through a silicone column into a T-nut in the
    # arm's top slot; turning the screw moves that corner +/-1.5 mm. The T-nuts are held only by the columns' spring
    # force, so they slide in the slots as the hot bed grows (0.24 mm between front and rear mounts at 60 K).
    for i, (x, y) in enumerate(BED_MOUNTS):
        arm = f"bed_arm_{'left' if x < 0 else 'right'}"
        place(d, f"bed_column_{i}", silicone_column(), Location((x, y, Z_FL)), body="zbody")
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
        add_screw(d, f"z_mount_bolt_{n}", "M5", 10, at=(sx * MM_FOOT_X, UP_Y, 26.0), threads_into="frame_bot_back", tnut=True,
                  clamps=("z_motor_mount",))
    z_cpl = Z_MF + 11.5                 # coupler bottom; motor shaft tip (Z_MF + 24) fills the 5 mm bore
    place(d, "z_coupler", shaft_coupler(5.0, 8.0), Location((0, LS_Y, z_cpl)))
    place(d, "leadscrew", leadscrew_t8(200, lead=2.0), Location((0, LS_Y, z_cpl + 12.5)))
    d.join("z_coupler", "z_motor", "clamp")
    d.join("leadscrew", "z_coupler", "clamp")
    # extruder (v5: Bowden): hangs under a 3 mm sheet plate on top of the top back rail, behind the rail; filament
    # comes up from below and leaves through the plate into the PTFE tube
    em = Pos(0, (UP_Y - 8.0 + EXM_Y + 24.0) / 2, FZ + 11.5) * Box(100.0, EXM_Y + 24.0 - (UP_Y - 8.0), 3.0)
    em -= Pos(0, EXM_Y, FZ + 11.5) * Cylinder(5.0, 3.0)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            em -= Pos(x, EXM_Y + y, FZ + 11.5) * Cylinder(SH3 / 2, 3.0)
    for x in (-40.0, 40.0):
        em -= Pos(x, UP_Y, FZ + 11.5) * Cylinder(clearance_hole("M5") / 2, 3.0)
    d.add("extruder_mount", em, material="al6061", process="sheet")
    place(d, "extruder", extruder_direct(), Location((0, EXM_Y, FZ + 10.0), (180, 0, 0)),
          process="purchased")   # the automatic rule reads "extruder" as saw-cut extrusion
    k = 0
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            add_screw(d, f"extruder_screw_{k}", "M3", 8, at=(x, EXM_Y + y, FZ + 13.0), threads_into="extruder",
                      clamps=("extruder_mount",)); k += 1
    for i, x in enumerate((-40.0, 40.0)):
        add_screw(d, f"extruder_mount_bolt_{i}", "M5", 8, at=(x, UP_Y, FZ + 13.0), threads_into="frame_top_back", tnut=True,
                  clamps=("extruder_mount",))
    d.bom_extra("PTFE-TUBE-4x2-0.5M", 1, 2.0)
    d.bom_extra("PUSHFIT-PC4-M6", 2, 0.8)

    # ================= Y axis ====================================================
    PL_Y0, PL_Y1 = YB0 - 25.0, YB0 + 14.3     # Y plates; the rear edge is 1.2 mm in front of the hotend mount
    XI_Y = YB0 - XB                           # X pulley / idler axis line
    EAR_X1 = X_IDLER_X + 35.0                 # right plate's ear: idler slot and tensioner anchor, inside the frame line
    for sx, n in ((-1, "left"), (1, "right")):
        yr = place(d, f"y_rail_{n}", mgn12_rail(300), Location((sx * RAIL_X, 0, Z_RAIL), (0, 0, 90)))
        for i, (hx, hy, hz) in enumerate(yr.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"y_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5),
                      threads_into=f"frame_top_{n}", tnut=True)
        place(d, f"y_carriage_{n}", mgn12h_carriage(), Location((sx * RAIL_X, YB0, Z_RAIL), (0, 0, 90)),
              body="ybody", guides="y")
        x_in = X_IDLER_X - 12.0 if sx > 0 else X_ES_X0 + 7.5    # left plate reaches inboard to carry the X endstop
        x_out = X_MOTOR_X - 22.5 if sx < 0 else YB_X + BWY / 2 + 1.5     # right plate reaches out under the Y belt clamp
        zp0, zp1 = Z_PLATE, Z_PLATE + T_YP
        # flat 6 mm plates, machined: the carriage screw heads are counterbored under the beam, and these two plates
        # set the beam square to the Y rails
        plate = Pos((x_in + x_out) / 2, (PL_Y0 + PL_Y1) / 2, Z_PLATE + T_YP / 2) * Box(abs(x_out - x_in), PL_Y1 - PL_Y0, T_YP)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP - 1.6) * Cylinder(3.0, 3.2)
        x_bolt = sx * (RAIL_X - 25)
        plate -= Pos(x_bolt, YB0, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M5") / 2, T_YP)
        if sx < 0:
            # motor pad in front of the beam line so the X pulley sits on the belt centre line
            plate += Pos(X_MOTOR_X + 0.75, YB0 + (13.5 - XB - 24) / 2, Z_PLATE + T_YP / 2) * Box(46.5, XB + 24 + 13.5, T_YP)
            plate += fillet_z(X_MOTOR_X + 24.0, YB0 - 25, 1, -1, 3.0, zp0, zp1)
            plate -= Pos(X_MOTOR_X, YB0 - XB, Z_PLATE + T_YP / 2) * Cylinder(11.5, T_YP)
            for x in (-15.5, 15.5):
                for y in (-15.5, 15.5):
                    plate -= Pos(X_MOTOR_X + x, YB0 - XB + y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
            # land for the X endstop in front of the beam (switch screws tap into the plate)
            land_y0 = X_ES_Y0 - 10.5
            plate += Pos(X_ES_X0, (land_y0 + YB0 - 25) / 2, Z_PLATE + T_YP / 2) * Box(15, YB0 - 25 - land_y0, T_YP)
            e = endstop_switch().interfaces
            for px, py, _ in e["pin_holes"]:      # clearance for the switch terminals (part frame x -> -Y, y -> +X)
                plate -= Pos(X_ES_X0 + py, X_ES_Y0 - px, Z_PLATE + T_YP / 2) * Cylinder(ES_PIN_D / 2, T_YP)
            plate += fillet_z(X_ES_X0 - 7.5, YB0 - 25, -1, -1, 2.0, zp0, zp1)
            for x, y in TOW_BOLTS:   # the Y belt tower is a separate printed block, through-bolted
                plate -= Pos(x, y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
        else:
            # ear for the X idler: the M5 axle bolt sits in a slot along X (belt tensioner), and the tensioner's anchor
            # screws tap into the plate further out
            plate += Pos((x_in + EAR_X1) / 2, YB0 - 32.5, Z_PLATE + T_YP / 2) * Box(EAR_X1 - x_in, 15.0, T_YP)
            plate += fillet_z(EAR_X1, YB0 - 25, 1, -1, 2.0, zp0, zp1)
            plate -= slot_z(X_IDLER_X, XI_Y, 0.0, BELT_ADJ, clearance_hole("M5"), zp0, zp1)
        d.add(f"y_plate_{n}", plate, material="al6061", body="ybody", process="machined")
        for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
            add_screw(d, f"y_plate_{n}_screw_{i}", "M3", 6, at=(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP - 3.2),
                      body="ybody", threads_into=f"y_carriage_{n}")
        add_screw(d, f"beam_bolt_{n}", "M5", 10, at=(x_bolt, YB0, Z_PLATE), direction=(0, 0, 1),
                  body="ybody", threads_into="x_beam", tnut=True)
    # ================= X axis ====================================================
    place(d, "x_beam", extrusion_2020(FX), Location((0, YB0, Z_BEAM)), body="ybody")
    xr = place(d, "x_rail", mgn12_rail(250), Location((0, YB0, Z_BEAM + 10)), body="ybody")
    for i, (hx, hy, hz) in enumerate(xr.meta["interfaces"]["mount_holes_m3"][::2]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5), body="ybody",
                  threads_into="x_beam", tnut=True)
    place(d, "x_carriage", mgn12h_carriage(), Location((0, YB0, Z_BEAM + 10)), body="xbody", guides="x")
    # ---- toolhead (v5): 8 mm flat plate on the carriage, printed ABS hotend mount under it, printed belt block in
    # front of it; hotend, two fans and the bed probe. The extruder is on the frame (Bowden).
    d.add("tool_plate", tool_plate_shape(), material="al6061", body="xbody", process="machined")
    d.add("x_belt_block", belt_block_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "-Z"})
    d.add("hotend_mount", hotend_mount_shape(), material=HOT, body="xbody", process="printed", meta={"print_up": "-Z"})
    for i, (x, y) in enumerate([(-10, -10), (10, -10), (-10, 10), (10, 10)]):
        if y < 0:     # the two front screws also clamp the belt block's flange
            add_screw(d, f"tool_screw_{i}", "M3", 16, at=(x, YB0 + y, Z_TOP + T_TP + T_FLG), body="xbody",
                      threads_into="x_carriage", clamps=("x_belt_block", "tool_plate"))
        else:
            add_screw(d, f"tool_screw_{i}", "M3", 8, at=(x, YB0 + y, Z_TOP + T_TP - CB), body="xbody",
                      threads_into="x_carriage", clamps=("tool_plate",))
    for i, (x, y) in enumerate(MOUNT_SCREWS):      # through the plate and the mount to nuts underneath
        add_screw(d, f"hotend_mount_screw_{i}", "M3", 20, at=(x, YB0 + y, Z_TOP + T_TP - CB), body="xbody",
                  clamps=("tool_plate", "hotend_mount"))
        add_nut(d, f"hotend_mount_nut_{i}", "M3", at=(x, YB0 + y, Z_TOP - T_COL), direction=(0, 0, -1), body="xbody",
                screw=f"hotend_mount_screw_{i}")
    d.bom_extra("INSERT-M3-HEATSET", 2 + 1, 0.08)   # the hotend's two set screws, the X tensioner's pull screw
    place(d, "hotend", hotend(), Location((0, YB0 + HOT_OFF, Z_TOP)), body="xbody")
    d.join("hotend", "hotend_mount", "set_screw")   # two M3 set screws through the mount's walls onto the heat-sink neck
    d.join("hotend", "tool_plate", "clamp")         # ... which also hold its top face against the plate
    d.bom_extra("SETSCREW-M3x10", 2, 0.05)
    # heater and thermistor cartridges clamped in the heater block (the proxy block has no bores: declared overlaps)
    HB_Y, HB_Z = YB0 + HOT_OFF, Z_TOP - 47.5
    place(d, "hotend_heater", heater_cartridge(HOTEND_W, 24.0), Location((0, HB_Y + 3.5, HB_Z - 2.5)), body="xbody")
    place(d, "hotend_thermistor", thermistor_cartridge(), Location((2.5, HB_Y - 5.0, HB_Z + 3.5)), body="xbody")
    for nm in ("hotend_heater", "hotend_thermistor"):
        d.allow_overlap(nm, "hotend")
        d.join(nm, "hotend", "clamp")
    # bed probe on the mount's drop wall: two M3x30 from the right through wall and probe into nuts
    place(d, "bed_probe", bed_probe(), Location((PRB_X, HB_Y, Z_PRB)), body="xbody")
    for i, z in enumerate(PRB_SCREW_Z):
        add_screw(d, f"probe_screw_{i}", "M3", 30, at=(PRB_WALL_X0 + PRB_WALL_T, HB_Y, z), direction=(-1, 0, 0),
                  body="xbody", clamps=("hotend_mount", "bed_probe"))
        add_nut(d, f"probe_nut_{i}", "M3", at=(PRB_X - 9.0, HB_Y, z), direction=(-1, 0, 0), body="xbody",
                screw=f"probe_screw_{i}")
    # heat-sink fan on the rear face of the mount, part-cooling fan on its left face (the duct is not modelled);
    # each hangs from its two upper holes on M3x16 into captive nuts
    place(d, "hotend_fan", fan(30), Location(Plane(origin=(0, YB0 + TP_REAR + 5, FAN_Z), x_dir=(1, 0, 0), z_dir=(0, 1, 0))),
          body="xbody")
    for i, x in enumerate((-12.0, 12.0)):
        add_screw(d, f"fan_screw_{i}", "M3", 16, at=(x, YB0 + TP_REAR + 10, FAN_Z + 12), direction=(0, -1, 0), body="xbody",
                  clamps=("hotend_fan", "hotend_mount"))
        add_nut(d, f"fan_nut_{i}", "M3", at=(x, YB0 + TP_REAR - FAN_LUG, FAN_Z + 12), direction=(0, -1, 0), body="xbody",
                screw=f"fan_screw_{i}")
    place(d, "part_fan", fan(30), Location(Plane(origin=(PF_X, HB_Y, FAN_Z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))),
          body="xbody")
    for i, y in enumerate((-12.0, 12.0)):
        add_screw(d, f"part_fan_screw_{i}", "M3", 16, at=(PF_X - 5.0, HB_Y + y, FAN_Z + 12.0), direction=(1, 0, 0),
                  body="xbody", clamps=("part_fan", "hotend_mount"))
        add_nut(d, f"part_fan_nut_{i}", "M3", at=(PF_X + 5.0 + FAN_LUG, HB_Y + y, FAN_Z + 12.0), direction=(1, 0, 0),
                body="xbody", screw=f"part_fan_screw_{i}")
    # ================= X drive ===================================================
    xclamp = Pos(0, (XC_Y0 + TAB_Y0) / 2, (TAB_Z0 + XC_Z1) / 2) * Box(40, TAB_Y0 - XC_Y0, XC_Z1 - TAB_Z0)
    xclamp -= Pos(0, TAB_Y0 - 0.75, Z_XB) * Box(40, 1.5, BWX + 1.2)   # one straight belt groove (no inside corners)
    for x, z in X_CLAMP_SCREWS:
        xclamp -= Pos(x, (XC_Y0 + TAB_Y0) / 2, z) * Rot(90, 0, 0) * Cylinder(PH3 / 2, TAB_Y0 - XC_Y0)
    d.add("x_belt_clamp", xclamp, material=HOT, body="xbody", process="printed", meta={"print_up": "+Y"})
    for i, (x, z) in enumerate(X_CLAMP_SCREWS):
        add_screw(d, f"x_belt_clamp_screw_{i}", "M3", 12, at=(x, XC_Y0, z), direction=(0, 1, 0), body="xbody",
                  clamps=("x_belt_clamp", "x_belt_block"))
        add_nut(d, f"x_belt_clamp_nut_{i}", "M3", at=(x, BLK_Y1 - NUT_POCKET, z), direction=(0, 1, 0), body="xbody",
                screw=f"x_belt_clamp_screw_{i}")
    place(d, "x_motor", nema17(34), Location((X_MOTOR_X, XI_Y, Z_PLATE)), body="ybody")
    place(d, "x_pulley", gt2_pulley(20, belt_width=BWX), Location((X_MOTOR_X, XI_Y, Z_XB - P_BC(BWX))), body="ybody")
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 10, at=(X_MOTOR_X + x, XI_Y + y, Z_PLATE + T_YP),
                  body="ybody", threads_into="x_motor")
    d.join("x_pulley", "x_motor", "set_screw")
    # X idler and belt tensioner (v5): the idler stands on a printed slider; its M5 axle bolt runs through a +/-3 mm
    # slot in the plate to a nut underneath. With that nut slack, the M3 screw through the fixed anchor block pulls the
    # slider outward (0.5 mm per turn); then the axle nut is tightened.
    zt = Z_PLATE + T_YP
    place(d, "x_idler", gt2_idler(20, belt_width=BWX), Location((X_IDLER_X, XI_Y, Z_XI)), body="ybody")
    sl = (Pos(X_IDLER_X + 0.5, XI_Y, zt + X_SP / 2) * Box(21.0, 18.0, X_SP)
          + Pos(X_IDLER_X + 16.0, XI_Y, zt + 6.0) * Box(10.0, 14.0, 12.0))
    sl -= Pos(X_IDLER_X, XI_Y, zt + X_SP / 2) * Cylinder(2.75, X_SP)
    d.add("x_idler_slider", sl, material=COOL, body="ybody", process="printed", meta={"print_up": "+Z"})
    add_screw(d, "x_idler_bolt", "M5", 35, at=(X_IDLER_X, XI_Y, Z_XI + I_H(BWX)), body="ybody",
              clamps=("x_idler_slider", "y_plate_right"))
    add_nut(d, "x_idler_nut", "M5", at=(X_IDLER_X, XI_Y, Z_PLATE), direction=(0, 0, -1), body="ybody", screw="x_idler_bolt")
    d.join("x_idler", "x_idler_bolt", "axle")
    d.join("x_idler_slider", "y_plate_right", "clamp")
    XT_X = X_IDLER_X + 27.0
    xta = Pos(XT_X, XI_Y, zt + 5.0) * Box(8.0, 20.0, 10.0)
    xta -= Pos(XT_X, XI_Y, zt + 6.0) * Rot(0, 90, 0) * Cylinder(PH3 / 2, 8.0)
    for y in (-6.5, 6.5):
        xta -= Pos(XT_X, XI_Y + y, zt + 5.0) * Cylinder(PH3 / 2, 10.0)
    d.add("x_tension_anchor", xta, material=COOL, body="ybody", process="printed", meta={"print_up": "+Z"})
    for i, y in enumerate((-6.5, 6.5)):
        add_screw(d, f"x_tension_anchor_screw_{i}", "M3", 16, at=(XT_X, XI_Y + y, zt + 10.0), body="ybody",
                  threads_into="y_plate_right", clamps=("x_tension_anchor",))
    add_screw(d, "x_tension_screw", "M3", 20, at=(XT_X + 4.0, XI_Y, zt + 6.0), direction=(-1, 0, 0), body="ybody",
              threads_into="x_idler_slider", clamps=("x_tension_anchor",))
    # X endstop on the left Y plate
    xsw = place(d, "x_endstop", endstop_switch(),
                Location(Plane(origin=(X_ES_X0, X_ES_Y0, Z_PLATE + T_YP), x_dir=(0, -1, 0), z_dir=(0, 0, 1))), body="ybody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"x_endstop_screw_{i}", "M3", 8, at=(hx, hy, hz + 1.6), body="ybody", threads_into="y_plate_left",
                  clamps=("x_endstop",))
    # ================= Y drives: vertical belt planes outboard of both top side rails =====
    # v5: mounts are 3 mm laser-cut steel sheet (same flat shapes as v4's 4 mm machined aluminium). Belt tensioners:
    # each motor mount is held by three M5 screws in T-nuts, so with them slack it slides along the rail; an M3 jack
    # screw in a printed anchor block (bolted to the same slot, hooked under the rail) pushes it backwards on a lug.
    xf = FX / 2
    xcyl = lambda r, h: Rot(0, 90, 0) * Cylinder(r, h)
    Y_MOUNT_BOLTS = (133.0, 150.0, 167.0)
    AN_Y0, AN_Y1, LUG_Y0, TS_Z = 105.0, 119.0, 125.0, FZ - 15.0

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
        a -= Pos(xs, (AN_Y0 + AN_Y1) / 2, TS_Z) * Rot(90, 0, 0) * Cylinder(PH3 / 2, AN_Y1 - AN_Y0)
        a -= hex_pocket_y(xs, AN_Y1, TS_Z, NUT_POCKET)
        d.add(f"y_tension_anchor{tag}", a, material=COOL, process="printed", meta={"print_up": "-X" if sg > 0 else "+X"})
        add_screw(d, f"y_tension_anchor{tag}_bolt", "M5", 16, at=(sg * (xf + 12.0), (AN_Y0 + AN_Y1) / 2, FZ),
                  direction=(-sg, 0, 0), threads_into=rail, tnut=True, clamps=(f"y_tension_anchor{tag}",))
        add_screw(d, f"y_tension_screw{tag}", "M3", 25, at=(xs, LUG_Y0 - 25.0, TS_Z), direction=(0, 1, 0),
                  clamps=(f"y_tension_anchor{tag}",))
        add_nut(d, f"y_tension_nut{tag}", "M3", at=(xs, AN_Y1 - NUT_POCKET, TS_Z), direction=(0, 1, 0),
                screw=f"y_tension_screw{tag}")
        d.join(f"y_tension_nut{tag}", f"y_tension_anchor{tag}", "clamp")      # captive in its pocket

    # ---- right
    d.add("y_motor_mount", motor_mount(1, Z_YC), material="steel", process="sheet")
    place(d, "y_motor", nema17(48), Location(Plane(origin=(xf, YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    place(d, "y_pulley", gt2_pulley(20, belt_width=BWY),
          Location(Plane(origin=(YB_X - P_BC(BWY), YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    k = 0
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"y_motor_screw_{k}", "M3", 6, at=(xf + MT, YM_Y + y, Z_YC + z), direction=(-1, 0, 0),
                      threads_into="y_motor"); k += 1
    for i, y in enumerate(Y_MOUNT_BOLTS):
        add_screw(d, f"y_motor_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    d.join("y_pulley", "y_motor", "set_screw")
    tensioner(1, "", "frame_top_right")
    # idler mount at the front, in front of the Y carriage / Y plate sweep: flat plate; the idler runs on an
    # M5 through-bolt with a bought 6 mm spacer and a nut on the inside face
    x_yi = YB_X - I_H(BWY) / 2
    im = Pos(xf + MT / 2, YI_Y - 1.5, (FZ - 10 + Z_YC + 9) / 2) * Box(MT, 31, Z_YC + 9 - FZ + 10)
    im -= Pos(xf + MT / 2, YI_Y, Z_YC) * xcyl(clearance_hole("M5") / 2, MT)
    for y in (YI_Y - 9.0, YI_Y + 6.0):
        im -= Pos(xf + MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_idler_mount", im, material="steel", process="sheet")
    for i, y in enumerate((YI_Y - 9.0, YI_Y + 6.0)):
        add_screw(d, f"y_idler_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    place(d, "y_idler_spacer", round_spacer(10.0, 5.5, Y_SP, "al6061"),
          Location(Plane(origin=(xf + MT, YI_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    place(d, "y_idler", gt2_idler(20, belt_width=BWY), Location(Plane(origin=(x_yi, YI_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    add_screw(d, "y_idler_bolt", "M5", 30, at=(x_yi + I_H(BWY), YI_Y, Z_YC), direction=(-1, 0, 0),
              clamps=("y_idler_spacer", "y_idler_mount"))
    add_nut(d, "y_idler_nut", "M5", at=(xf, YI_Y, Z_YC), direction=(-1, 0, 0), screw="y_idler_bolt")
    d.join("y_idler", "y_idler_bolt", "axle")
    d.join("y_idler_spacer", "y_idler_mount", "clamp")
    # Y belt clamp on top of the right Y plate: printed grooved bar, belt ends enter from front and back; its screws
    # tap into the aluminium plate
    PC = YB0 - 5.75
    YA0, YA1 = PC - 14, PC + 14
    T_YC = 5.0
    YC_X0 = RAIL_X + 12.5
    yclamp = Pos((YC_X0 + YB_X + BWY / 2 + 1.5) / 2, PC, zt + T_YC / 2) * Box(YB_X + BWY / 2 + 1.5 - YC_X0, YA1 - YA0, T_YC)
    yclamp -= Pos(YB_X, PC, zt + 0.75) * Box(BWY + 0.4, YA1 - YA0, 1.5)   # one straight belt groove
    Y_CLAMP_SCREWS = [(YB_X, PC), (RAIL_X + 16.5, PC - 9), (RAIL_X + 16.5, PC + 9)]
    for x, y in Y_CLAMP_SCREWS:
        yclamp -= Pos(x, y, zt + T_YC / 2) * Cylinder(PHC / 2, T_YC)
    d.add("y_belt_clamp", yclamp, material=COOL, body="ybody", process="printed", meta={"print_up": "-Z"})
    for i, (x, y) in enumerate(Y_CLAMP_SCREWS):
        add_screw(d, f"y_belt_clamp_screw_{i}", "M3", 12, at=(x, y, zt + T_YC), body="ybody", threads_into="y_plate_right",
                  clamps=("y_belt_clamp",))
    # ---- left: mirrored motor + belt
    d.add("y_motor_mount_l", motor_mount(-1, Z_YCL), material="steel", process="sheet")
    place(d, "y_motor_l", nema17(48), Location(Plane(origin=(-xf, YM_Y, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    place(d, "y_pulley_l", gt2_pulley(20, belt_width=BWY),
          Location(Plane(origin=(YBL_X + P_BC(BWY), YM_Y, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    k = 0
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"y_motor_l_screw_{k}", "M3", 6, at=(-xf - MT, YM_Y + y, Z_YCL + z), direction=(1, 0, 0),
                      threads_into="y_motor_l"); k += 1
    for i, y in enumerate(Y_MOUNT_BOLTS):
        add_screw(d, f"y_motor_mount_l_bolt_{i}", "M5", 8, at=(-xf - MT, y, FZ), direction=(1, 0, 0),
                  threads_into="frame_top_left", tnut=True)
    d.join("y_pulley_l", "y_motor_l", "set_screw")
    tensioner(-1, "_l", "frame_top_left")
    x_yil = YBL_X + I_H(BWY) / 2
    # flat plate again; it reaches back to just short of the X motor pad's front edge at y = -TY and carries
    # the Y endstop on its outer face (pressed by that edge)
    iml_y0, iml_y1 = YI_YL - 17.0, PAD_FRONT - TY - 1.5
    iml = Pos(-xf - MT / 2, (iml_y0 + iml_y1) / 2, (FZ - 10 + Z_YCL + 9) / 2) * Box(MT, iml_y1 - iml_y0, Z_YCL + 9 - FZ + 10)
    iml -= Pos(-xf - MT / 2, YI_YL, Z_YCL) * xcyl(clearance_hole("M5") / 2, MT)
    for y in (YI_YL - 9.0, YI_YL + 6.0):
        iml -= Pos(-xf - MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    # the switch board stands on two bought 3 mm spacers, so its terminals (2.6 mm out of the board) clear the sheet
    # without pin holes (holes that close to the screw holes are not good laser practice in 3 mm steel)
    ES_SP = 3.0
    ysw = place(d, "y_endstop", endstop_switch(),
                Location(Plane(origin=(-xf - MT - ES_SP, PAD_FRONT - TY - ES_TRIG, Z_PLATE + T_YP / 2 + ES_SIDE),
                               x_dir=(0, 0, 1), z_dir=(-1, 0, 0))))
    for hx, hy, hz in ysw.meta["interfaces"]["mount_holes_m3"]:
        iml -= Pos(-xf - MT / 2, hy, hz) * xcyl(clearance_hole("M3") / 2, MT)
    d.add("y_idler_mount_l", iml, material="steel", process="sheet")
    for i, (hx, hy, hz) in enumerate(ysw.meta["interfaces"]["mount_holes_m3"]):
        place(d, f"y_endstop_spacer_{i}", round_spacer(6.0, 3.4, ES_SP),
              Location(Plane(origin=(-xf - MT, hy, hz), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
        add_screw(d, f"y_endstop_screw_{i}", "M3", 10, at=(hx - 1.6, hy, hz), direction=(1, 0, 0),
                  clamps=("y_endstop", f"y_endstop_spacer_{i}", "y_idler_mount_l"))
        add_nut(d, f"y_endstop_nut_{i}", "M3", at=(-xf, hy, hz), direction=(1, 0, 0), screw=f"y_endstop_screw_{i}")
    for i, y in enumerate((YI_YL - 9.0, YI_YL + 6.0)):
        add_screw(d, f"y_idler_mount_l_bolt_{i}", "M5", 8, at=(-xf - MT, y, FZ), direction=(1, 0, 0),
                  threads_into="frame_top_left", tnut=True)
    place(d, "y_idler_spacer_l", round_spacer(10.0, 5.5, Y_SP_L, "al6061"),
          Location(Plane(origin=(-xf - MT, YI_YL, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    place(d, "y_idler_l", gt2_idler(20, belt_width=BWY),
          Location(Plane(origin=(x_yil, YI_YL, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    add_screw(d, "y_idler_l_bolt", "M5", 35, at=(x_yil - I_H(BWY), YI_YL, Z_YCL), direction=(1, 0, 0),
              clamps=("y_idler_spacer_l", "y_idler_mount_l"))
    add_nut(d, "y_idler_l_nut", "M5", at=(-xf, YI_YL, Z_YCL), direction=(1, 0, 0), screw="y_idler_l_bolt")
    d.join("y_idler_l", "y_idler_l_bolt", "axle")
    d.join("y_idler_spacer_l", "y_idler_mount_l", "clamp")
    # belt tower: printed 20 x 22.5 x 25 ABS block on the left Y plate (beside the X motor). Three M3x40 run from the
    # top through clamp bar, tower and plate to nuts under the plate: no thread in the plastic
    tower = Pos((TOW_X0 + TOW_X1) / 2, (TOW_Y0 + TOW_Y1) / 2, Z_PLATE + T_YP + TOW_H / 2) * Box(
        TOW_X1 - TOW_X0, TOW_Y1 - TOW_Y0, TOW_H)
    for x, y in TOW_BOLTS:
        tower -= Pos(x, y, Z_PLATE + T_YP + TOW_H / 2) * Cylinder(PHC / 2, TOW_H)
    d.add("y_belt_tower_l", tower, material=HOT, body="ybody", process="printed", meta={"print_up": "+Z"})
    PCL = (TOW_Y0 + TOW_Y1) / 2
    yclamp_l = Pos((TOW_X0 + TOW_X1) / 2, PCL, Z_TOW + T_YC / 2) * Box(TOW_X1 - TOW_X0, TOW_Y1 - TOW_Y0, T_YC)
    yclamp_l -= Pos(YBL_X + 1.0, PCL, Z_TOW + 0.75) * Box(BWY + 0.4 + 2.0, TOW_Y1 - TOW_Y0, 1.5)   # runs out through +X
    for x, y in TOW_BOLTS:
        yclamp_l -= Pos(x, y, Z_TOW + T_YC / 2) * Cylinder(PHC / 2, T_YC)
    d.add("y_belt_clamp_l", yclamp_l, material=HOT, body="ybody", process="printed", meta={"print_up": "-Z"})
    for i, (x, y) in enumerate(TOW_BOLTS):
        add_screw(d, f"y_belt_tower_l_bolt_{i}", "M3", 40, at=(x, y, Z_TOW + T_YC), body="ybody",
                  clamps=("y_belt_clamp_l", "y_belt_tower_l", "y_plate_left"))
        add_nut(d, f"y_belt_tower_l_nut_{i}", "M3", at=(x, y, Z_PLATE), direction=(0, 0, -1), body="ybody",
                screw=f"y_belt_tower_l_bolt_{i}")
    # ================= electronics bay: tray across the bottom rails =============
    tray = Pos(0, (TRAY_Y0 + TRAY_Y1) / 2, 20 + T_TRAY / 2) * Box(FX, TRAY_Y1 - TRAY_Y0, T_TRAY)
    grp = ["electronics_tray"]
    # supply at the front left, terminal strip towards the board (+X); a 12 mm corridor is left along the front edge
    psu = place(d, "psu", psu_lrs(PSU_MODEL), Location((-47.0, -68.5, Z_TRAY), (0, 0, 180)))
    # board on 6 mm spacers, long edge along Y: power / heater terminals face the supply, motor connectors face +X
    board = place(d, "control_board", skr_mini_e3_v3(), Location((109.0, -82.0, Z_TRAY + 6.0), (0, 0, -90)))
    host = place(d, "host", raspberry_pi_zero2w(), Location((45.0, 27.0, Z_TRAY + 4.0), (0, 0, 90)))
    pcbs = [(board, "mount_holes_m3", "M3", 14, 6.0), (host, "mount_holes_m2.5", "M2.5", 12, 4.0)]
    if USE_CUTOFFS:
        relay = place(d, "psu_relay", relay_btt_v12(), Location((-88.0, 24.0, Z_TRAY + 5.0)))
        pcbs.append((relay, "mount_holes_m3", "M3", 12, 5.0))
    if USE_MOSFET:
        mos = place(d, "bed_mosfet", mosfet_module(25.0), Location((100.0, 26.0, Z_TRAY + 5.0), (0, 0, 90)))
        pcbs.append((mos, "mount_holes_m3", "M3", 12, 5.0))
    tray_bolts = [(sx * RAIL_X, y) for sx in (-1, 1) for y in (-128.0, 54.0)]
    for x, y in tray_bolts:
        tray -= Pos(x, y, 20 + T_TRAY / 2) * Cylinder(clearance_hole("M5") / 2, T_TRAY)
    for hx, hy, hz in psu.meta["interfaces"]["mount_holes_m4"]:
        tray -= Pos(hx, hy, 20 + T_TRAY / 2) * Cylinder(clearance_hole("M4") / 2, T_TRAY)
    for comp, key, size, _, _ in pcbs:
        for hx, hy, hz in comp.meta["interfaces"][key]:
            tray -= Pos(hx, hy, 20 + T_TRAY / 2) * Cylinder(clearance_hole(size) / 2, T_TRAY)
    # the tray lies under screws that are driven from below (beam bolts): a driver hole under each,
    # and no board under any of them
    for x, y in [(sx * (RAIL_X - 25), YB0) for sx in (-1, 1)]:
        tray -= Pos(x, y, 20 + T_TRAY / 2) * Cylinder(5.0, T_TRAY)
    tray -= Pos(0, YB0 + HOT_OFF, 20 + T_TRAY / 2) * Cylinder(14.0, T_TRAY)      # the hotend goes in from below
    d.add("electronics_tray", tray, material="al6061", process="sheet")
    for i, (x, y) in enumerate(tray_bolts):
        add_screw(d, f"tray_bolt_{i}", "M5", 6, at=(x, y, Z_TRAY), threads_into=f"frame_bot_{'left' if x < 0 else 'right'}",
                  tnut=True)
    for i, (hx, hy, hz) in enumerate(psu.meta["interfaces"]["mount_holes_m4"]):   # the supply's base holes take 3 mm of screw
        add_screw(d, f"psu_screw_{i}", "M4", 6, at=(hx, hy, 20.0), direction=(0, 0, 1), threads_into="psu")
        grp.append(f"psu_screw_{i}")
    grp.append("psu")
    for comp, key, size, slen, sp in pcbs:
        mount_pcb(d, comp.name, comp, key, size, slen, sp, grp)
    d.subassemblies["electronics"] = grp
    # mains inlet (switch + fuse) on a 3 mm panel bolted to the outside of the left bottom rail
    from build123d import RectangleRounded
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
    # bench sub-assemblies (v5): the bed carrier and the toolhead are built on the bench and fitted as units
    d.subassemblies["bed_carrier"] = (
        ["back_plate", "nut_block"] + [f"nut_block_{k}_{i}" for k in ("bolt", "nut") for i in range(len(NB_BOLTS))]
        + [f"bed_arm_{n}{sfx}" for n in ("left", "right") for sfx in ("", "_bolt", "_bracket")])
    d.subassemblies["toolhead"] = (
        ["tool_plate", "hotend_mount", "hotend", "hotend_heater", "hotend_thermistor", "bed_probe", "hotend_fan", "part_fan"]
        + [f"hotend_mount_{k}_{i}" for k in ("screw", "nut") for i in range(len(MOUNT_SCREWS))]
        + [f"{k}_{i}" for k in ("probe_screw", "probe_nut", "fan_screw", "fan_nut", "part_fan_screw", "part_fan_nut")
           for i in range(2)])
    # ================= belts =====================================================
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (-20.0, XA_Y, Z_XB)), ("pulley", "x_pulley", "ccw"),
                                   ("pulley", "x_idler", "ccw"), ("anchor", "xbody", (20.0, XA_Y, Z_XB))],
                        axis=(0, 0, 1), width=BWX, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, YA0, Z_YA)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    d.belts.append(Belt("y_belt_l", [("anchor", "ybody", (YBL_X, TOW_Y0, Z_YAL)), ("pulley", "y_idler_l", "cw"),
                                     ("pulley", "y_pulley_l", "cw"), ("anchor", "ybody", (YBL_X, TOW_Y1, Z_YAL))],
                        axis=(1, 0, 0), width=BWY, adjust=BELT_ADJ))
    d.bom_extra("GT2-BELT-12MM-OPEN-1M", 3, 6.0)   # 12 mm belt (price is an estimate; pulley SKUs do not encode width)

    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY, TY),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_OVER, PRINT_Z),
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
    d.endstops += [{"joint": "x", "switch": "x_endstop", "at": "min"},     # left end of the belt clamp bar
                   {"joint": "y", "switch": "y_endstop", "at": "min"},     # front edge of the X motor pad
                   {"joint": "z", "switch": "bed_probe", "at": "max"}]     # v5: the probe senses the bed plate itself
    build_electrical(d)      # looms; their flexing spans are added to d.cables
    # Bowden tube from the extruder's outlet to the top of the hotend: 276 mm apart at the far front corners,
    # 76 mm at the back of the Y travel, so it stands up in an arc
    d.cables.append(Cable("bowden tube", ("xbody", (4.5, YB0 + HOT_OFF, Z_TOP + T_TP + 0.5)),
                          ("world", (5.5, EXM_Y, FZ + 13.5)), length=420.0, min_bend_radius=30.0))
    d.adjustments += [
        # v5: Z homes on the probe; the nozzle-to-bed gap is the probe's z_offset in the firmware, set once with a
        # feeler gauge. Rail, lead screw and nut have Z_OVER of travel beyond both ends of the print height.
        Adjustment("probe z_offset in the firmware", "z_offset", range_mm=Z_OVER),
        # the four bed screws (heads in the bed's counterbores) compress the silicone columns 0.5 .. 3.5 mm
        Adjustment("bed levelling screws on silicone columns", "bed_level", range_mm=1.5),
        # T-nuts slide across the 6.2 mm slot (+/-1.6 on an M3): left rail set to a straight edge, right rail's
        # screws tightened one by one while the gantry is run along it; the beam's T-nuts absorb the spacing
        Adjustment("y rails on sliding T-nuts", "rail_align", range_mm=1.5, joint="y"),
        Adjustment("z rails on sliding T-nuts", "rail_align", range_mm=1.5, joint="z",
                   note="left rail to a square, right rail tightened while the bed carrier is run up and down on all four blocks"),
        # the nut hangs under the block with NUT_FLOAT radial room; one pin in a radial slot stops it turning
        Adjustment("floating lead screw nut", "float", range_mm=NUT_FLOAT - 0.2, joint="z"),
        # v5 belt tensioners (see the X idler and the Y motor mounts)
        Adjustment("x belt: idler slider on a slot in the right Y plate, M3 pull screw", "belt_tension",
                   range_mm=BELT_ADJ, joint="x"),
        Adjustment("y belts: motor mounts slide on their T-nuts, M3 jack screws", "belt_tension",
                   range_mm=BELT_ADJ, joint="y"),
    ]
    # how to print on this machine: the digital twin runs as a verifier, using the FEA nozzle stiffness below
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z", "extruder": "bowden",
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"}}

    # ================= structure =================================================
    # nozzle-point stiffness of the whole gantry moving structure, toolhead at mid-span (worst case);
    # deflection probed at the nozzle tip. The printed hotend mount is in the model; the hotend seats on the plate.
    moving = ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate", "hotend_mount", "hotend"]
    y_plate_fix = [("y_plate_left", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6),
                   ("y_plate_right", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6)]
    block_face = ("hotend", lambda f: abs(f.center().Z - (Z_NOZZLE + 5)) < 1e-6)   # heater-block underside
    for nm, force in (("nozzle_stiffness_y", (0.0, 3.0, -2.0)), ("nozzle_stiffness_x", (3.0, 0.0, -2.0))):
        d.assemblycases.append(AssemblyCase(nm, moving, fixed=y_plate_fix, loaded=block_face, force=force,
                                            probe=nozzle, max_deflection=0.03, min_fos=5.0))
    # bed carrier: payload x3 (plus the bed plate's own weight x3) on the bed, through the columns and arms into the
    # back plate, held where the four blocks sit on their rails. v4 checked the one-piece carrier alone, clamped at
    # the blocks; this case has the bed, columns, arms, brackets, back plate and blocks.
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
        "x_belt_pull", "x_belt_block", fixed=lambda f: abs(f.center().Z - (Z_TOP + T_TP)) < 1e-6,
        loaded=lambda f: abs(f.center().Y - TAB_Y0) < 1e-6 and f.area > 300,
        force=(60.0, 0.0, 0.0), min_fos=3.0, max_deflection=0.1))
    d.loadcases.append(LoadCase(      # Y belt pull on the printed tower: 120 N along Y at its top
        "y_belt_pull_tower", "y_belt_tower_l", fixed=lambda f: abs(f.center().Z - (Z_PLATE + T_YP)) < 1e-6,
        loaded=lambda f: abs(f.center().Z - Z_TOW) < 1e-6,
        force=(0.0, 120.0, 0.0), min_fos=3.0, max_deflection=0.1))

    # ================= heat: bed 60 K above the frame =============================
    # Bed at +60 K, columns half way, carrier and blocks at frame temperature (worst case for differential growth).
    # Blocks held on their rails. The nozzle (cold, on the gantry) does not move, so the change in the gap is the
    # vertical movement of the bed surface under it. Limits: gap within half a 0.2 mm layer (the probe offset is set
    # with the bed hot, so this is margin on top), bow below 0.1 mm.
    d.thermalcases.append(ThermalCase(
        "bed_heated_60K", ["bed", *cols, *carrier, *zcars],
        fixed=[(c, on_rail) for c in zcars],
        temps={"bed": 60.0, **{c: 30.0 for c in cols}, "*": 0.0},
        # a probe snaps to the nearest meshed point, and the nozzle is not in this model (it is 150 mm above the bed
        # at home), so the "nozzle" reference is put on a held rail face: it must report zero movement
        probes={"nozzle": (-UP_X, Y_FACE - 8.0, ZC1), "bed": (0.0, YB0 + HOT_OFF, Z_BED + T_BED)},
        gaps={"nozzle gap": ("nozzle", "bed", "z", 0.1)}, flatness=("bed", "z", 0.1)))

    # ================= requirements ==============================================
    def jr(dd, name):
        return next(j for j in dd.joints if j.name == name)

    def motors_of(dd, name):   # v2: a joint may have several motors (dual Y drive); same check on each
        mm_ = jr(dd, name).drive["motor"]
        return [mm_] if isinstance(mm_, str) else list(mm_)

    def nozzle_tip(dd):
        bb = dd.get("hotend").shape.bounding_box()
        return (bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, bb.min.Z

    def travel(dd):
        t = {n: jr(dd, n).range[1] - jr(dd, n).range[0] for n in "xyz"}
        return t["x"] >= PRINT_X and t["y"] >= PRINT_Y and t["z"] >= PRINT_Z, str(t)
    d.requirements.append(Requirement("print volume: travel >= 180 x 180 x 150 mm", travel))

    def nozzle_over_bed(dd):
        nx, ny, _ = nozzle_tip(dd)
        bb = dd.get("bed").shape.bounding_box()
        xr_, yr_ = jr(dd, "x").range, jr(dd, "y").range
        m = min(nx + xr_[0] - bb.min.X, bb.max.X - (nx + xr_[1]), ny + yr_[0] - bb.min.Y, bb.max.Y - (ny + yr_[1]))
        return m >= 0, f"smallest nozzle-to-bed-edge margin over the XY travel: {m:.1f} mm"
    d.requirements.append(Requirement("nozzle stays over the bed plate for all XY positions", nozzle_over_bed))

    def bed_gap(dd):
        gap = nozzle_tip(dd)[2] - (dd.get("bed").shape.bounding_box().max.Z + jr(dd, "z").range[1])
        return -1e-9 <= gap <= 0.2 + 1e-9, f"nozzle tip is {gap:.2f} mm above the bed surface with the bed at the top"
    # The original brief said 0.2-2 mm. The digital twin showed that is wrong: any gap above the first
    # layer height makes the first layer unreachable.
    d.requirements.append(Requirement("bed can reach the nozzle: 0-0.2 mm gap at the top of Z travel", bed_gap))
    d.requirements.append(Requirement("bed carries the 1.0 kg payload as mass", lambda dd: (
        (m := dd.get("bed").mass()) >= dd.get("bed").shape.volume * 2700e-9 + PAYLOAD_KG - 1e-9,
        f"bed + payload {m:.3f} kg")))

    def speeds(dd):
        s = {n: (jr(dd, n).max_speed, jr(dd, n).max_accel) for n in "xyz"}
        ok = all(s[n][0] >= V_XY and s[n][1] >= A_XY for n in "xy") and s["z"][0] >= V_Z and s["z"][1] >= A_Z
        return ok, str(s)
    d.requirements.append(Requirement("X/Y 250 mm/s at 4000 mm/s^2, Z 12 mm/s at 200 mm/s^2", speeds))
    d.requirements.append(Requirement("drive margin >= 3x on every axis", lambda dd, m: (
        set(m["motion"]["drives"]) == {"x", "y", "z"} and all(v["margin"] >= MARGIN for v in m["motion"]["drives"].values()),
        str({k: v["margin"] for k, v in m["motion"]["drives"].items()}))))
    d.requirements.append(Requirement("both belts routed: constant length, clear of parts", lambda dd, m: (
        all(b in m["motion"].get("belts", {}) and m["motion"]["belts"][b]["clear_of_parts"]
            and m["motion"]["belts"][b]["length_change_over_travel_mm"] <= 0.3 for b in ("x_belt", "y_belt")),
        str(m["motion"].get("belts")))))

    def rail_margin(dd):
        out = {}
        rails = {"y_carriage_left": "y_rail_left", "y_carriage_right": "y_rail_right", "x_carriage": "x_rail",
                 **{f"z_carriage_{s_}_{lv}": f"z_rail_{s_}" for s_ in ("left", "right") for lv in ("lo", "hi")}}   # v5: four Z blocks
        for n, rail in rails.items():
            ax = n[0].upper()
            cb, rb = dd.get(n).shape.bounding_box(), dd.get(rail).shape.bounding_box()
            lo, hi = jr(dd, ax.lower()).range
            out[n] = round(min(getattr(cb.min, ax) + lo - getattr(rb.min, ax), getattr(rb.max, ax) - getattr(cb.max, ax) - hi), 2)
        return min(out.values()) >= 5.0, str(out)
    d.requirements.append(Requirement("every carriage stays >= 5 mm inside its rail ends over the travel", rail_margin))
    d.requirements.append(Requirement("Z rails end below the top back extrusion (no rubbing)", lambda dd: (
        (t := dd.get("z_rail_left").shape.bounding_box().max.Z) < FZ - 10, f"rail top {t:.1f} vs extrusion underside {FZ - 10:.1f}")))
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(mn).sku.startswith("NEMA17") and dd.get(mn).meta["catalog"] for n in "xyz" for mn in motors_of(dd, n)),
        str({n: [dd.get(mn).sku for mn in motors_of(dd, n)] for n in "xyz"}))))
    d.requirements.append(Requirement("Z lead screw self-locking (efficiency < 0.5)", lambda dd: (
        dd.get("leadscrew").ratings["efficiency"] < 0.5, f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    return d
