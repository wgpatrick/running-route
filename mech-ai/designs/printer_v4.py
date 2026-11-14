"""Complete 3-axis motion system for a small 3D printer: 180 x 180 x 150 mm print volume.

One frame of 2020 extrusion (340 x 360 footprint, top ring centred at Z=300).
Layout (X = width, Y = depth with the front at -Y, Z = up):
- XY gantry on top (adapted from examples/gantry.py, mirrored so the hotend hangs BEHIND
  the X beam, towards the Z uprights): world -> ybody (X beam, X motor) -> xbody (toolhead).
- Z bed lift (adapted from designs/z_axis.py): two extra 2020 uprights between the bottom
  and top back rails carry MGN12 rails; a one-piece aluminium carrier cantilevers the bed
  forward; one NEMA 17 + T8x2 lead screw at the back. world -> zbody.
- With the bed at the top of its travel the bed plate sits INSIDE the top frame ring,
  1 mm below the nozzle. Only the hotend dips below the top of the frame, and it always
  stays over the bed, so the gantry cannot reach the Z axis hardware.

- X belt: open GT2 loop in a horizontal plane in FRONT of the X beam; motor pulley on the left Y
  plate, idler on a bossed ear of the right Y plate, both ends clamped to a tab of the tool plate.
- Y belt: open GT2 loop in a vertical plane outboard of the right frame rail; Y motor behind the
  frame, idler at the front, both ends clamped on top of the right Y plate.

v2 changes versus designs/printer.py (each scored separately):
- 12 mm GT2 belts and matching pulleys/idlers on X and Y (was 6 mm). The catalog pulley SKU does not encode
  belt width and the belt price is an estimate.
- second Y drive on the left rail: NEMA17-48 + 20T pulley + idler + open belt, clamped on a tower that is
  part of the left Y plate (loop above the plate so it clears the X motor, X pulley and X belt).
- X motor NEMA17-40 -> NEMA17-34 (60 g less on the Y axis).

v3 "buildable" changes (tolerance / manufacture / subsystems / heat):
- Frame top ring raised 14 mm (FZ 300 -> 314) to make room for the bed levelling stack and Z over-travel.
- Bed: sits on four silicone levelling columns; M3 screws (heads counterbored in the bed) run down through the
  columns and the carrier flanges to nyloc nuts.  Rear-left carrier hole is a close fit (the fixed point), the other
  three are slots pointing at it, so the heated bed grows freely.  A silicone heater pad is bonded under the bed.
- Z offset: M3 jack screw + lock nut in the carrier's nut tab presses a microswitch at the top of travel; rail,
  lead screw and nut have >= 3 mm of travel beyond both ends of the 150 mm print height.
- Lead screw nut floats: it hangs under the tab (bed weight holds it up against the tab), one M3 pin in a radial
  slot stops it turning, 1.3 mm of radial room around the barrel.
- Rails: both rails of the Y and Z pairs screw into T-nuts that slide +/-1.5 mm across the 6.2 mm slot; one rail is
  set to a straight edge, the other is tightened while the axis is run end to end.
- Hotend: no fitted bore any more; it seats on its top face in a square pocket and two set screws push it into
  one corner (two flat walls), so there is no fit to tolerance.
- Toolhead: direct-drive extruder above the hotend, 30 mm heat-sink fan behind it, X endstop on the left Y plate.
- Every custom part is a flat plate of stock thickness (or a two-sided block); bosses became loose spacers on
  through-bolts; inside corners have a 2-3 mm radius.
- Electronics: control board + 24 V supply on a 3 mm tray across the bottom rails; cables to X, Y and Z bodies.

v4: the complete electrical system (see docs/ELECTRICAL.md). Everything electrical is an off-the-shelf board, module
or component; no custom PCB.
- BIGTREETECH SKR Mini E3 V3.0 (4 x TMC2209) on spacers on the tray; the two Y motors share one driver through the
  board's two paralleled "Z" motor connectors, the Z motor uses the "Y" driver (pin mapping is firmware).
- Mean Well LRS-350-24 (sized from the power budget), IEC C14 inlet with switch and T8A fuse on a side panel,
  BIGTREETECH Relay V1.2 ahead of the supply (dropped by the firmware on any shutdown), protective earth to the
  supply and to a stud on the frame.
- 200 W silicone bed pad with embedded NTC, fed through a stock MOSFET module straight from the supply (the board's
  bed terminal is not asked to carry it) and through a 133 degC thermal cut-off taped to the plate.
- E3D-style 30 W heater cartridge and thermistor cartridge in the hot block; heat-sink fan and part-cooling fan.
- Raspberry Pi Zero 2 W as the Klipper host on the board's serial header.
- Looms with waypoints, strain relief at both ends of each flexing span; flexing spans feed the existing cable check.
The collar of the tool plate grew an 8 mm ear on the left for the part-cooling fan.

Proxies / not modelled (flagged): hotend, silicone levelling columns and bed heater are hand-made proxies
(uncatalogued_cots warnings are true); tapped holes are not drawn; payload is carried as extra mass on the bed.
"""
import math

from build123d import Box, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from mechloop import Adjustment, AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.electrical import Bay, Device, Electrical, Port, Waypoint
from mechloop.model import Belt, ThermalCase
from mechloop.parts.electrical import (THERMISTORS, add_electrical_bom, bed_heater_pad, device_from, embedded_device,
                                       heater_cartridge, iec_inlet_c14, mosfet_module, psu_lrs, raspberry_pi_zero2w,
                                       relay_btt_v12, skr_mini_e3_v3, thermal_fuse, thermistor_cartridge)
from mechloop.parts import (Stock, add_corner_bracket, add_nut, add_screw, clearance_hole,
                            endstop_switch, extruder_direct, extrusion_2020, fan, gt2_idler, gt2_pulley,
                            leadscrew_nut_t8, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place,
                            shaft_coupler)

# ---- brief --------------------------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 180.0, 180.0, 150.0
PAYLOAD_KG = 1.0
V_XY, A_XY = 250.0, 4000.0
V_Z, A_Z = 12.0, 200.0
MARGIN = 3.0
ENVELOPE = (420.0, 420.0, 480.0)

# ---- electrical choices ---------------------------------------------------------
# The loop: ATTEMPT 1 carried v3's placeholders over (150 W pad, 200 W supply, thin PVC wire to the bed straight from
# the board, motors at rated current, no cut-offs); ATTEMPT 2 fixed power and wire; the default is the design that
# passes. MECHLOOP_V4_ATTEMPT=1|2 rebuilds the earlier attempts so their findings can be reproduced.
import os

ATTEMPT = int(os.environ.get("MECHLOOP_V4_ATTEMPT", "3"))
BED_W = {1: 150.0}.get(ATTEMPT, 200.0)
PSU_MODEL = {1: "LRS-200-24"}.get(ATTEMPT, "LRS-350-24")
BED_AWG, BED_INS = {1: (22, "pvc")}.get(ATTEMPT, (16, "silicone"))
USE_MOSFET = ATTEMPT >= 3          # external bed MOSFET module
USE_CUTOFFS = ATTEMPT >= 2         # thermal fuse on the bed, relay ahead of the supply
HOTEND_W = 30.0                    # the cartridge E3D ships with the V6 (vendor/e3d_v6.json)
RUN_CURRENT = ({"x": 0.40, "y": 1.60, "z": 0.40, "extruder": 0.70} if ATTEMPT < 3 else
               {"x": 0.28, "y": 1.20, "z": 0.28, "extruder": 0.60})   # A rms at the driver
FUSE_A = {1: 4.0}.get(ATTEMPT, 8.0)
T_TRAY = 3.0
TRAY_Y0, TRAY_Y1 = -138.0, 62.0    # clear of the corner brackets at both ends
Z_TRAY = 20.0 + T_TRAY

# ---- frame ----------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 314.0      # frame outer X, Y and top-ring centre height (v3: +14 for the bed stack)
RAIL_X = FX / 2 - 10                  # side extrusions / Y rails
TX, TY = PRINT_X / 2, PRINT_Y / 2     # +/- travel

# ---- Z axis ---------------------------------------------------------------------
BED = 220.0
T_BED = 6.0            # 6 mm plate so the bed screws get 5 mm of thread (3 mm plate gave 2 mm)
UP_X = 90.0            # Z upright / rail centre, +/- X
UP_Y = FY / 2 - 10     # uprights stand between the bottom and top back rails
Y_FACE = UP_Y - 10     # front face of the uprights = rail base
Y_CAR = Y_FACE - 13    # carriage top face = carrier back-plate rear face
T_BP = 6.0             # carrier back plate thickness
Y_PF = Y_CAR - T_BP
LS_Y = UP_Y + 10       # lead screw / motor axis Y
MOTOR_L = 34
Z_MF = 22.0 + MOTOR_L  # Z motor mounting face
T_MM = 5.0
T_TAB = 6.0
PAD = 0.5
T_WEB, T_FL = 5.0, 5.0
FL_IN = 72.0
BED_Y0, BED_Y1 = Y_CAR - BED, Y_CAR
BED_CY = (BED_Y0 + BED_Y1) / 2
# bed mounts: [0] rear-left is the fixed point (close-fit hole); [1] and [2] sit in slots that point at it,
# [3] (diagonally opposite) in an oversize hole
H_COL = 16.0           # installed height of the silicone levelling columns (18 free, 2 mm pre-compression)
BED_MOUNTS = [(-79.0, BED_Y1 - 30.0), (79.0, BED_Y1 - 30.0), (-79.0, BED_Y1 - 200.0), (79.0, BED_Y1 - 200.0)]
BED_SLOT = 1.0         # +/- slot length for bed growth (needs 0.33 mm at 60 K over the 232 mm diagonal)
NUT_PIN = (0.0, 8.0)   # the one flange hole of the T8 nut that carries the anti-rotation pin
NUT_FLOAT = 1.5        # radial room around the nut barrel and along the pin slot
Z_OVER = 3.0           # mechanical Z travel available beyond each end of the print height

# ---- gantry ---------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13          # underside of the Y plates
T_YP = 6.0
Z_BEAM = Z_PLATE + T_YP + 10
Z_TOP = Z_BEAM + 10 + 13       # top of the X carriage
HOT_OFF = 32.5                 # hotend axis behind the beam centre (v3: +1.5 so the extruder screws clear the carriage)
YB0 = BED_CY - HOT_OFF         # beam centre Y at home (nozzle over the bed centre)
X_MOTOR_X = -(FX / 2 + 27.0)
RIB = 8.0
T_TP = 6.0                     # tool plate thickness over the carriage
T_COL = 12.0                   # hotend collar depth below the plate
Z_NOZZLE = Z_TOP - 60          # nozzle tip (hotend proxy is 60 long, its top seats under the tool plate at Z_TOP)
PR = 20 * 2.0 / math.pi / 2     # pitch radius of the 20T pulleys / idlers
BWX, BWY = 12.0, 12.0           # GT2 belt widths (v2: 12 mm, was 6 mm)
P_BC = lambda w: 7.0 + (w + 1) / 2      # gt2_pulley belt centre above its hub bottom
I_H = lambda w: w + 2.5                 # gt2_idler height
MT_Y = 4.0                     # Y motor / idler mount plate thickness
XB = 28.0                      # X belt centre line, in front of the beam centre
X_IDLER_X = RAIL_X - 20.0
X_SP = 8.0                     # X idler spacer (stock 8 mm); also lifts the belt over the X endstop
Z_XB = Z_PLATE + T_YP + X_SP + I_H(BWX) / 2  # X belt centre height
XA_Y = YB0 - XB + PR           # near (anchored) run of the X belt
TAB_Y0 = XA_Y + 0.7 + 0.03     # tab front face = belt tooth side
Y_SP, Y_SP_L = 6.0, 8.0        # Y idler spacers, right and left (stock plate thicknesses)
YB_X = FX / 2 + MT_Y + Y_SP + I_H(BWY) / 2       # Y belt plane, outboard of the right frame rail
YM_Y, YI_Y = FY / 2 + 24.0, -128.0      # Y motor pulley (behind the frame) and Y idler (front)
MT = MT_Y
Z_YA = Z_PLATE + T_YP + 0.7    # upper (anchored) run of the Y belt lies on the right Y plate
Z_YC = Z_YA - PR
# v2 second (left) Y drive: belt plane outboard of the left rail, loop ABOVE the left Y plate on a
# clamp tower, so it clears the X motor (below the plate) and the X pulley / X belt (below the loop)
TOW_H = 25.0                   # stock 25 mm; lower run clears the top of the 12 mm X pulley (22.75 above the plate)
YBL_X = -(FX / 2 + MT_Y + Y_SP_L + I_H(BWY) / 2)
TOW_X1 = YBL_X + BWY / 2 + 0.3
TOW_X0 = TOW_X1 - 20.0         # 20 mm wide block
TOW_Y0, TOW_Y1 = YB0 - 9.0, YB0 + 13.5
TOW_SCREWS = [((TOW_X0 + TOW_X1) / 2, YB0 + 1.0), ((TOW_X0 + TOW_X1) / 2, YB0 + 9.0)]   # behind the X motor body
Z_TOW = Z_PLATE + T_YP + TOW_H
Z_YAL = Z_TOW + 0.7            # lower (anchored) run of the left Y belt lies on the tower
Z_YCL = Z_YAL + PR
YI_YL = -156.0                 # left Y idler: in front of the sweep of the X motor pad
Z_XI = Z_XB - I_H(BWX) / 2              # underside of the X idler
NOZZLE_GAP = 0.1               # bed surface -> nozzle with the bed at the top: must not exceed the first layer
                               # height (the digital twin showed a 1.0 mm gap made the first layer unreachable)

# bed heights follow from the nozzle
Z_BED = Z_NOZZLE - NOZZLE_GAP - T_BED - PRINT_Z   # bed underside at home (bed at the bottom)
Z_FL = Z_BED - H_COL                              # top of the carrier flanges (the columns stand on them)
ZC = Z_FL - 30.9                                  # Z carriage centre at home
Z_TAB = ZC - 6.0                                  # underside of the nut tab at home
# Z endstop: switch on a 4 mm bracket hanging from the top back rail; struck from below by the jack screw
ZS_X, ZB_T = 8.0, 4.0
ZS_Y = Y_FACE - ZB_T - 5.0                        # switch trigger point is 5 mm in front of its mount face
JACK_L = 30.0                                     # jack screw M3x30 (was x35): the lever switch triggers 5.1 mm further
#                                                   from its origin, and its screws must stay below the top rail
ZS_TIP = Z_TAB - 4.0 + JACK_L                     # tip of the jack screw at home
# Lever switch (vendor-CAD pass): the trigger is the lever's operating position at its tip, 10.6 from the switch
# origin along the stroke (was 5.5) and 9 to one side (was on the centre line).
ES_TRIG, ES_SIDE, ES_PIN_D = 10.6, 9.0, 2.5       # ES_PIN_D: clearance drill for the switch terminals under the board
ZS_Z0 = ZS_TIP + PRINT_Z + ES_TRIG                # switch origin: trigger point is ES_TRIG below it
ZB_Z0 = ZS_Z0 - 7.5                               # bottom of the bracket


def hotend() -> Stock:
    """PROXY (not in the catalog): V6-style hotend. Local frame: axis Z, top at Z=0, nozzle tip at Z=-60."""
    body = Pos(0, 0, -20) * Cylinder(11, 40) + Pos(0, 0, -47.5) * Box(20, 16, 15) + Pos(0, 0, -57.5) * Cylinder(2, 5)
    return Stock(body, "HOTEND-V6", "UNVERIFIED proxy: V6-style hotend with heater block", 0.12, material="al6061",
                 cost_usd=25.0)


def silicone_column() -> Stock:
    """PROXY (not in the catalog): silicone bed-levelling column, 12 OD x 4 bore, drawn at its installed height
    H_COL (18 mm free). Local frame: axis Z, bottom at Z=0.  Material is the nearest in the library (belt rubber,
    E = 50 MPa); real silicone is roughly ten times softer, so the thermal restraint on the bed is overstated."""
    body = Pos(0, 0, H_COL / 2) * (Cylinder(6.0, H_COL) - Cylinder(2.0, H_COL))
    return Stock(body, "BED-COLUMN-SIL-18", "UNVERIFIED proxy: silicone bed levelling column 12 x 18", 0.002,
                 material="rubber_gt2", cost_usd=0.5)


def spacer(d, name, at, length, bore, body="world"):
    """Loose round spacer (6 mm OD tube cut from stock), axis Z, bottom at `at`."""
    d.add(name, Pos(at[0], at[1], at[2] + length / 2) * (Cylinder(3.0, length) - Cylinder(bore / 2, length)),
          material="al6061", body=body)


def mount_pcb(d, name, comp, holes_key, size, screw_len, sp_len, group):
    """A board on spacers on the tray: screw from the top through board, spacer and tray into a nut underneath."""
    hole_d = clearance_hole(size)
    t_pcb = comp.shape.bounding_box().min.Z      # underside of the PCB = top of the spacers
    names = []
    for i, (hx, hy, hz) in enumerate(comp.meta["interfaces"][holes_key]):
        spacer(d, f"{name}_spacer_{i}", (hx, hy, Z_TRAY), sp_len, hole_d)
        pcb_t = 1.5 if size == "M2.5" else 1.6
        add_screw(d, f"{name}_screw_{i}", size, screw_len, at=(hx, hy, Z_TRAY + sp_len + pcb_t),
                  clamps=(name, f"{name}_spacer_{i}", "electronics_tray"))
        add_nut(d, f"{name}_nut_{i}", size, at=(hx, hy, 20.0), direction=(0, 0, -1), screw=f"{name}_screw_{i}")
        names += [f"{name}_spacer_{i}", f"{name}_screw_{i}", f"{name}_nut_{i}"]
    group += [name] + names


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


def carrier_shape(carriage_holes):
    zp0, zp1 = ZC - 23, ZC + 23
    c = Pos(0, Y_PF + (T_BP - PAD) / 2, ZC) * Box(208, T_BP - PAD, zp1 - zp0)
    for sx in (-1, 1):
        c += Pos(sx * UP_X, Y_CAR - PAD / 2, ZC) * Box(27, PAD, 45.4)
        prof = Plane.YZ * Polygon((Y_CAR - PAD, zp0), (Y_CAR - PAD, Z_FL), (BED_Y0, Z_FL), (BED_Y0, Z_FL - 12),
                                  align=None)
        c += Pos(sx * UP_X - T_WEB / 2, 0, 0) * extrude(prof, T_WEB)
        x0, x1 = sorted((sx * FL_IN, sx * (UP_X + T_WEB / 2)))
        c += Pos((x0 + x1) / 2, (BED_Y0 + Y_PF) / 2, Z_FL - T_FL / 2) * Box(x1 - x0, Y_PF - BED_Y0, T_FL)
    y1 = LS_Y + 15
    c += Pos(0, (Y_PF + 3 + y1) / 2, Z_TAB + T_TAB / 2) * Box(26, y1 - Y_PF - 3, T_TAB)
    # floating nut: the barrel (10.2) hangs in a hole with NUT_FLOAT of radial room; the anti-rotation pin (one
    # M3 screw in the nut flange) rides in a radial slot, so the nut can move both ways but cannot turn
    c -= Pos(0, LS_Y, Z_TAB + T_TAB / 2) * Cylinder(5.1 + NUT_FLOAT, T_TAB)
    c -= slot_z(NUT_PIN[0], LS_Y + NUT_PIN[1], 90, NUT_FLOAT, clearance_hole("M3"), Z_TAB, Z_TAB + T_TAB)
    for hx, hy, hz in carriage_holes:
        c -= Pos(hx, (Y_PF + Y_CAR) / 2, hz) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, T_BP)
    # bed mounts: one close-fit hole (the fixed point), three slots that point at it
    fx, fy = BED_MOUNTS[0]
    c -= Pos(fx, fy, Z_FL - T_FL / 2) * Cylinder(1.6, T_FL)
    for x, y in BED_MOUNTS[1:3]:
        c -= slot_z(x, y, math.degrees(math.atan2(fy - y, fx - x)), BED_SLOT, clearance_hole("M3"), Z_FL - T_FL, Z_FL)
    x, y = BED_MOUNTS[3]      # diagonal corner: free both ways (5.4 hole, washer under the nut)
    c -= Pos(x, y, Z_FL - T_FL / 2) * Cylinder(1.7 + BED_SLOT, T_FL)
    return c


def bed_shape_():
    b = Pos(0, BED_CY, Z_BED + T_BED / 2) * Box(BED, BED, T_BED)
    for x, y in BED_MOUNTS:   # M3 cap heads sit 0.4 mm below the print surface
        b -= Pos(x, y, Z_BED + T_BED / 2) * Cylinder(clearance_hole("M3") / 2, T_BED)
        b -= Pos(x, y, Z_BED + T_BED - 1.7) * Cylinder(3.25, 3.4)
    return b


def z_motor_mount_shape():
    y_back = LS_Y + 22
    m = Pos(0, (Y_FACE - 5 + y_back) / 2, Z_MF + T_MM / 2) * Box(160, y_back - (Y_FACE - 5), T_MM)
    m += Pos(0, Y_FACE - 2.5, Z_MF + 10) * Box(200, 5, 20)
    m -= Pos(0, LS_Y, Z_MF + T_MM / 2) * Cylinder(11.5, T_MM)
    m -= Pos(0, (LS_Y + y_back) / 2, Z_MF + T_MM / 2) * Box(23, y_back - LS_Y, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(x, LS_Y + y, Z_MF + T_MM / 2) * Cylinder(clearance_hole("M3") / 2, T_MM)
    for sx in (-1, 1):
        m -= Pos(sx * UP_X, Y_FACE - 2.5, Z_MF + 11) * Rot(90, 0, 0) * Cylinder(clearance_hole("M5") / 2, 5)
    return m


TAB_Z0 = Z_PLATE + T_YP + 1.5
# X endstop: flat on the left Y plate, pressed in -X by the left end of the belt clamp bar at x = -TX
X_ES_X0 = -TX - 20.0 - ES_TRIG   # switch origin X (trigger point is ES_TRIG further in +X)
X_ES_Y0 = TAB_Y0 - 1.5 - ES_SIDE # lever tip (ES_SIDE towards +Y) on the clamp bar's end face
PAD_FRONT = YB0 - XB - 24.0      # front edge of the X motor pad: it presses the Y endstop at y = -TY
XC_Y0 = TAB_Y0 - 5.0             # front face of the X belt clamp bar (5 mm stock)
XC_Z1 = Z_XB + 13.5              # top of the clamp bar; it runs down to TAB_Z0 so its end face strikes the X endstop
X_CLAMP_SCREWS = [(-13.0, Z_XB + 10.0), (13.0, Z_XB + 10.0), (0.0, Z_XB - 5.75)]
TP_REAR = HOT_OFF + 24.5         # rear edge of the tool plate, behind the beam centre
COL_Y0 = 14.5                    # front of the hotend collar (the carriage ends at 13.5)
EXT_SCREWS = [(x, HOT_OFF + y) for x in (-15.5, 15.5) for y in (-15.5, 15.5)]
EAR = 8.0                        # v4: extra collar width on the left for the part-cooling fan


def tool_plate_shape():
    """6 mm plate over the carriage carrying the extruder on top; belt tab in front; behind the carriage it is
    18 mm deep and holds the hotend in a square pocket cut from below: the hotend's top face seats on the plate and
    two M3 set screws push it into one corner.  Machined from the top and from below."""
    tp = Pos(0, (TAB_Y0 + YB0 + TP_REAR) / 2, Z_TOP + T_TP / 2) * Box(46, YB0 + TP_REAR - TAB_Y0, T_TP)
    # belt tab: drops in front of the carriage and beam to the X belt line; clears the Y plates below
    tp += Pos(0, (TAB_Y0 + YB0 - 14) / 2, (TAB_Z0 + Z_TOP) / 2) * Box(40, YB0 - 14 - TAB_Y0, Z_TOP - TAB_Z0)
    # v4: the collar is 8 mm wider on the left (an ear the part-cooling fan screws into, clear of the extruder screws)
    tp += Pos(-EAR / 2, YB0 + (COL_Y0 + TP_REAR) / 2, Z_TOP - T_COL / 2) * Box(46 + EAR, TP_REAR - COL_Y0, T_COL)
    # hotend seat: a 24 x 24 pocket (3 mm corner radii), not a fitted bore. Two M3 set screws (from the right and
    # from the rear) push the 22 mm heat-sink neck into the pocket's front-left corner, where it bears on two flat
    # walls: located the same way in every build, whatever the pocket's size comes out as.
    pk = Box(18, 24, T_COL) + Box(24, 18, T_COL)
    for cx in (-9, 9):
        for cy in (-9, 9):
            pk += Pos(cx, cy, 0) * Cylinder(3.0, T_COL)
    tp -= Pos(1.0, YB0 + HOT_OFF + 1.0, Z_TOP - T_COL / 2) * pk
    tp -= Pos(0, YB0 + HOT_OFF, Z_TOP + T_TP / 2) * Cylinder(2.1, T_TP)          # filament / PTFE liner
    for x in (-10, 10):
        for y in (-10, 10):   # carriage screws, heads counterbored flush so the extruder sits over them
            tp -= Pos(x, YB0 + y, Z_TOP + T_TP / 2) * Cylinder(clearance_hole("M3") / 2, T_TP)
            tp -= Pos(x, YB0 + y, Z_TOP + T_TP - 1.6) * Cylinder(3.0, 3.2)
    for x, y in EXT_SCREWS:   # extruder screws come up from below, heads counterbored 3.2 mm under the top face
        tp -= Pos(x, YB0 + y, Z_TOP + (T_TP - T_COL) / 2) * Cylinder(clearance_hole("M3") / 2, T_TP + T_COL)
        tp -= Pos(x, YB0 + y, Z_TOP + (3.2 - T_COL) / 2) * Cylinder(3.0, T_COL + 3.2)
    return tp


def build_electrical(d: Design) -> Electrical:
    """Devices, looms, wires and firmware settings. Every device is a stock product (Device.product says which)."""
    el = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
    d.electrical = el
    for nm in ("control_board", "psu", "inlet", "host", "hotend_heater", "hotend_thermistor", "hotend_fan",
               "part_fan", "x_endstop", "y_endstop", "z_endstop", "x_motor", "z_motor", "extruder"):
        device_from(el, d, nm)
    device_from(el, d, "bed_heater", plate="bed")      # the thermal model takes the plate's mass and area from this part
    for nm in ("y_motor", "y_motor_l"):       # two motors on one driver, coils in parallel (the board's ZAM/ZBM pair)
        device_from(el, d, nm, connection="parallel")
    embedded_device(el, d, "bed_heater", "bed_ntc", "thermistor", "ntc", "thermistor", ratings={"max_temp_c": 180.0},
                    sources={"points": "Klipper 'Generic 3950' (Keenovo R-T table)", "tau_s": "assumed 10 s (typical, unverified)"},
                    sensor_type="Generic 3950", points=THERMISTORS["Generic 3950"], tau_s=10.0, node="pad")
    if USE_CUTOFFS:
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
    # ---- looms (centre lines; one bundle radius off surfaces). Consecutive waypoints on different bodies flex.
    P1 = (124.0, 146.0, 316.0)
    el.loom("toolhead", [Waypoint("xbody", (0.0, YB0 + HOT_OFF + 18.0, Z_TOP + T_TP + 39.0), clamp="extruder"),
                         Waypoint("world", (124.0, 177.0, FZ + 13.0), clamp="frame_top_back"), Waypoint("world", P1)],
            flex_length={0: 420.0})
    el.loom("z_stop", [("world", (60.0, 155.0, 310.0)), ("world", (112.0, 155.0, 310.0))])
    el.loom("drop_right", [("world", P1), ("world", (132.0, 150.0, 280.0)), ("world", (145.0, 168.0, 240.0)),
                           ("world", (145.0, 170.0, 60.0)), ("world", (145.0, 150.0, 34.0))])
    el.loom("tray_right", [("world", (145.0, 150.0, 34.0)), ("world", (149.0, 46.0, zt)), ("world", (149.0, -26.0, zt))])
    el.loom("back", [("world", (130.0, 150.0, 32.0)), ("world", (30.0, 150.0, 28.0))])
    el.loom("gantry", [Waypoint("ybody", (X_MOTOR_X, YB0 - XB, Z_PLATE - 37.0), clamp="x_motor"),
                       Waypoint("world", (-164.0, YB0 - XB, FZ - 13.0), clamp="frame_top_left")], flex_length={0: 170.0})
    el.loom("top_left", [("world", (-164.0, -20.0, FZ - 13.0)), ("world", (-164.0, 136.0, FZ - 13.0))])
    el.loom("drop_left", [("world", (-164.0, -27.0, FZ - 13.0)), ("world", (-164.0, -120.0, FZ - 13.0)),
                          ("world", (-143.0, -150.0, 290.0)), ("world", (-143.0, -170.0, 250.0)),
                          ("world", (-143.0, -170.0, 60.0)), ("world", (-143.0, -150.0, 35.0)), ("world", (-110.0, -132.0, zt))])
    el.loom("front", [("world", (-110.0, -132.0, zt)), ("world", (70.0, -132.0, zt))])
    el.loom("bed", [Waypoint("zbody", (0.0, Y_PF - 3.0, ZC + 18.0), clamp="carrier"),
                    Waypoint("zbody", (0.0, Y_PF - 3.0, ZC - 18.0), clamp="carrier"),
                    Waypoint("world", (0.0, TRAY_Y1 - 4.0, Z_TRAY + 3.0), clamp="electronics_tray")], flex_length={1: 300.0})
    el.loom("mains", [("world", (-50.0, -4.0, zt)), ("world", (20.0, -4.0, zt))])
    tool, left = ["tray_right", "drop_right", "toolhead"], ["front", "drop_left"]
    # ---- mains and protective earth (AWG 18 = 0.82 mm^2, 105 degC PVC)
    mk = dict(conductors=1, insulation="pvc105")
    if USE_CUTOFFS:
        el.wire("mains L inlet-relay", "inlet.L", "psu_relay.LIN", 18, **mk)
        el.wire("mains L relay-supply", "psu_relay.LOT", "psu.L", 18, via=["mains"], **mk)
        el.wire("relay control", "control_board.PS-ON", "psu_relay.ctrl", 26, conductors=3)
    else:
        el.wire("mains L", "inlet.L", "psu.L", 18, via=["mains"], **mk)
    el.wire("mains N", "inlet.N", "psu.N", 18, via=["mains"], **mk)
    el.wire("earth to supply", "inlet.PE", "psu.FG", 18, via=["mains"], **mk)
    el.wire("earth to frame", "inlet.PE", "frame_earth.pe", 18, connector_b="ring-M4", **mk)
    # ---- 24 V distribution
    el.wire("24 V to board", "psu.V+1", "control_board.POWER", 16, insulation="silicone")
    if USE_MOSFET:
        el.wire("24 V to bed module", "psu.V+2", "bed_mosfet.pwr", 14, insulation="silicone")
        el.wire("bed control", "control_board.HB", "bed_mosfet.ctrl", 24)
        bed_src = "bed_mosfet.out"
    else:
        bed_src = "control_board.HB"
    if USE_CUTOFFS:
        el.wire("bed heater", bed_src, "bed_tco.a", BED_AWG, insulation=BED_INS, via=["bed"])
        el.wire("bed heater tail", "bed_tco.b", "bed_heater.in", BED_AWG, insulation=BED_INS, length=90.0)
    else:
        el.wire("bed heater", bed_src, "bed_heater.in", BED_AWG, insulation=BED_INS, via=["bed"])
    el.wire("bed thermistor", "control_board.THB", "bed_ntc.out", 26, insulation="silicone" if ATTEMPT > 1 else "pvc", via=["bed"])
    # ---- toolhead
    el.wire("hotend heater", "control_board.E0", "hotend_heater.in", 20, insulation="silicone", via=tool, pigtail=(150.0, "fiberglass"))
    el.wire("hotend thermistor", "control_board.TH0", "hotend_thermistor.out", 26, via=tool, pigtail=(150.0, "fiberglass"))
    el.wire("heat-sink fan", "control_board.FAN1", "hotend_fan.in", 26, via=tool)
    el.wire("part fan", "control_board.FAN0", "part_fan.in", 26, via=tool)
    el.wire("extruder motor", "control_board.EM", "extruder.coils", 24, conductors=4, via=tool)
    # ---- axes. The Y pair is on the board's doubled "Z" connectors (one driver); the Z motor is on the "Y" driver.
    el.wire("X motor", "control_board.XM", "x_motor.coils", 24, conductors=4, via=left + ["gantry"])
    el.wire("X endstop", "control_board.X-STOP", "x_endstop.out", 26, conductors=3, via=left + ["gantry"])
    el.wire("Y endstop", "control_board.Y-STOP", "y_endstop.out", 26, conductors=3, via=left)
    el.wire("Y motor left", "control_board.ZBM", "y_motor_l.coils", 24, conductors=4, via=left + ["top_left"],
            note="mirror-image motor: swap one coil pair at the connector so both turn the belts the same way")
    el.wire("Y motor right", "control_board.ZAM", "y_motor.coils", 24, conductors=4, via=["tray_right", "drop_right"])
    el.wire("Z motor", "control_board.YM", "z_motor.coils", 24, conductors=4, via=["tray_right", "back"])
    el.wire("Z endstop", "control_board.Z-STOP", "z_endstop.out", 26, conductors=3, via=["tray_right", "drop_right", "z_stop"])
    el.wire("host serial + 5 V", "control_board.TFT", "host.GPIO", 26, conductors=4)
    # ---- firmware (Klipper). PID values are left to the simulated PID_CALIBRATE.
    vh = None if ATTEMPT == 1 else {}
    el.firmware = {
        "kind": "klipper",
        "steppers": {"x": {"run_current": RUN_CURRENT["x"]}, "y": {"run_current": RUN_CURRENT["y"]},
                     "z": {"run_current": RUN_CURRENT["z"]},
                     "extruder": {"motors": ["extruder"], "run_current": RUN_CURRENT["extruder"], "rotation_distance": 7.71}},
        "heaters": {"extruder": {"heater": "hotend_heater", "sensor": "hotend_thermistor", "control": "pid", "min_temp": 0,
                                 "max_temp": 280, "targets": [250.0], "verify_heater": vh},
                    "heater_bed": {"heater": "bed_heater", "sensor": "bed_ntc", "control": "pid", "min_temp": 0,
                                   "max_temp": 120, "targets": [60.0, 100.0], "verify_heater": vh}},
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
    d = Design("printer_v4" if ATTEMPT >= 3 else f"printer_v4_attempt{ATTEMPT}", envelope=ENVELOPE, base="frame_bot_left")
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
    carriage_holes = []
    Z_RAIL_C = 187.5     # 215 mm rail, 80..295: below the top back extrusion, >= 5 mm past the carriage at both
                         # ends of the print travel plus Z_OVER of over-travel
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"z_rail_{n}", mgn12_rail(215),
                     Location(Plane(origin=(sx * UP_X, Y_FACE, Z_RAIL_C), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
        for i, (hx, hy, hz) in enumerate(rail.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"z_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy - 3.5, hz), direction=(0, 1, 0),
                      threads_into=f"upright_{n}", tnut=True)
        car = place(d, f"z_carriage_{n}", mgn12h_carriage(),
                    Location(Plane(origin=(sx * UP_X, Y_FACE, ZC), x_dir=(0, 0, 1), z_dir=(0, -1, 0))),
                    body="zbody", guides="z")
        holes = car.meta["interfaces"]["mount_holes_m3"]
        carriage_holes += holes
        for i, (hx, hy, hz) in enumerate(holes):
            add_screw(d, f"z_carriage_{n}_screw_{i}", "M3", 10, at=(hx, hy - T_BP, hz), direction=(0, 1, 0),
                      body="zbody", threads_into=f"z_carriage_{n}")
    d.add("carrier", carrier_shape(carriage_holes), material="al6061", body="zbody")
    # floating nut: hangs under the tab, the bed's weight keeps the tab sitting on its flange; the pin screw gets a
    # nyloc nut under the flange left 0.2 mm slack, so the nut can slide +/-NUT_FLOAT sideways and cannot turn
    place(d, "z_nut", leadscrew_nut_t8(), Location((0, LS_Y, Z_TAB - 3.5)), body="zbody")
    add_screw(d, "nut_pin", "M3", 12, at=(NUT_PIN[0], LS_Y + NUT_PIN[1], Z_TAB + T_TAB), body="zbody", threads_into="z_nut")
    d.bom_extra("NYLOC-M3", 1, 0.05)
    bed_shape = bed_shape_()
    bed_own = BED * BED * T_BED * 2700e-9
    d.add("bed", bed_shape, material="al6061", body="zbody", mass_kg=bed_own + PAYLOAD_KG)   # plate + payload
    # silicone pad, leads leaving at the back edge (towards the carrier's back plate)
    place(d, "bed_heater", bed_heater_pad(140.0, 200.0, BED_W), Location((0, BED_CY, Z_BED), (0, 0, 180)), body="zbody")
    d.join("bed_heater", "bed", "bond")
    if USE_CUTOFFS:   # thermal cut-off taped to the plate behind the pad, in series with the heater
        place(d, "bed_tco", thermal_fuse(133.0, 109.0, 15.0), Location((-25.0, BED_Y1 - 5.0, Z_BED - 2.0)), body="zbody")
        d.join("bed_tco", "bed", "bond")
    # bed mounts: M3x30 down through bed, silicone column and carrier flange to a nut; turning the nut moves that
    # corner +/-1.5 mm (column compressed 0.5 .. 3.5 mm)
    for i, (x, y) in enumerate(BED_MOUNTS):
        place(d, f"bed_column_{i}", silicone_column(), Location((x, y, Z_FL)), body="zbody")
        add_screw(d, f"bed_screw_{i}", "M3", 30, at=(x, y, Z_BED + T_BED - 3.4), body="zbody",
                  clamps=("bed", f"bed_column_{i}", "carrier"))
        add_nut(d, f"bed_nut_{i}", "M3", at=(x, y, Z_FL - T_FL), direction=(0, 0, -1), body="zbody", screw=f"bed_screw_{i}")
        d.join(f"bed_column_{i}", "bed", "clamp")
        d.join(f"bed_column_{i}", "carrier", "clamp")
    d.bom_extra("WASHER-M3", 4, 0.02)
    # Z offset: jack screw in the tab (tapped M3, lock nut on top); its tip presses the Z endstop at the top of travel
    add_screw(d, "z_stop_screw", "M3", JACK_L, at=(ZS_X, ZS_Y, Z_TAB - 4.0), direction=(0, 0, 1), body="zbody", threads_into="carrier")
    add_nut(d, "z_stop_locknut", "M3", at=(ZS_X, ZS_Y, Z_TAB + T_TAB), direction=(0, 0, 1), body="zbody", screw="z_stop_screw")
    ZB_BOLTS = (ZS_X + 20, ZS_X + 38)     # to one side, so a driver from the front passes beside the hotend
    # (widened 9 mm to the left: the switch moved over so that its lever tip is on the jack screw)
    zb = Pos(ZS_X + 12.5, Y_FACE - ZB_T / 2, (ZB_Z0 + FZ + 8) / 2) * Box(67, ZB_T, FZ + 8 - ZB_Z0)
    for x in ZB_BOLTS:
        zb -= Pos(x, Y_FACE - ZB_T / 2, FZ) * Rot(90, 0, 0) * Cylinder(clearance_hole("M5") / 2, ZB_T)
    zsw = place(d, "z_endstop", endstop_switch(),
                Location(Plane(origin=(ZS_X - ES_SIDE, Y_FACE - ZB_T, ZS_Z0), x_dir=(-1, 0, 0), z_dir=(0, -1, 0))))
    for hx, hy, hz in zsw.meta["interfaces"]["mount_holes_m3"]:
        zb -= Pos(hx, Y_FACE - ZB_T / 2, hz) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, ZB_T)
    for hx, hy, hz in zsw.meta["interfaces"]["pin_holes"]:      # the switch terminals stand 2.6 mm out of the board
        zb -= Pos(hx, Y_FACE - ZB_T / 2, hz) * Rot(90, 0, 0) * Cylinder(ES_PIN_D / 2, ZB_T)
    d.add("z_endstop_bracket", zb, material="al6061")
    for i, x in enumerate(ZB_BOLTS):
        add_screw(d, f"z_endstop_bracket_bolt_{i}", "M5", 8, at=(x, Y_FACE - ZB_T, FZ), direction=(0, 1, 0),
                  threads_into="frame_top_back", tnut=True)
    for i, (hx, hy, hz) in enumerate(zsw.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"z_endstop_screw_{i}", "M3", 8, at=(hx, hy - 1.6, hz), direction=(0, 1, 0),
                  clamps=("z_endstop", "z_endstop_bracket"))
        add_nut(d, f"z_endstop_nut_{i}", "M3", at=(hx, Y_FACE, hz), direction=(0, 1, 0), screw=f"z_endstop_screw_{i}")
    d.add("z_motor_mount", z_motor_mount_shape(), material="al6061")
    place(d, "z_motor", nema17(MOTOR_L), Location((0, LS_Y, Z_MF)))
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"z_motor_screw_{i}", "M3", 8, at=(x, LS_Y + y, Z_MF + T_MM), threads_into="z_motor")
    for sx, n in ((-1, "left"), (1, "right")):
        add_screw(d, f"z_mount_bolt_{n}", "M5", 8, at=(sx * UP_X, Y_FACE - 5, Z_MF + 11), direction=(0, 1, 0),
                  threads_into=f"upright_{n}", tnut=True)
    z_cpl = Z_MF + 11.5                 # coupler bottom; motor shaft tip (Z_MF + 24) fills the 5 mm bore
    place(d, "z_coupler", shaft_coupler(5.0, 8.0), Location((0, LS_Y, z_cpl)))
    place(d, "leadscrew", leadscrew_t8(200, lead=2.0), Location((0, LS_Y, z_cpl + 12.5)))
    d.join("z_coupler", "z_motor", "clamp")
    d.join("leadscrew", "z_coupler", "clamp")

    # ================= Y axis ====================================================
    for sx, n in ((-1, "left"), (1, "right")):
        yr = place(d, f"y_rail_{n}", mgn12_rail(300), Location((sx * RAIL_X, 0, Z_RAIL), (0, 0, 90)))
        for i, (hx, hy, hz) in enumerate(yr.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"y_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5),
                      threads_into=f"frame_top_{n}", tnut=True)
        place(d, f"y_carriage_{n}", mgn12h_carriage(), Location((sx * RAIL_X, YB0, Z_RAIL), (0, 0, 90)),
              body="ybody", guides="y")
        x_in = sx * (RAIL_X - 35) if sx > 0 else X_ES_X0 + 7.5    # left plate reaches inboard to carry the X endstop
        x_out = X_MOTOR_X - 22.5 if sx < 0 else YB_X + BWY / 2 + 1.5     # right plate reaches out under the Y belt clamp
        zp0, zp1 = Z_PLATE, Z_PLATE + T_YP
        # flat 6 mm plates. Rear edge trimmed to +13.5 so the toolhead passes behind it
        plate = Pos((x_in + x_out) / 2, YB0 - 5.75, Z_PLATE + T_YP / 2) * Box(abs(x_out - x_in), 38.5, T_YP)
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
            # (longer since the vendor-CAD pass: the switch sits ES_SIDE further forward, lever tip on the clamp bar)
            land_y0 = X_ES_Y0 - 10.5
            plate += Pos(X_ES_X0, (land_y0 + YB0 - 25) / 2, Z_PLATE + T_YP / 2) * Box(15, YB0 - 25 - land_y0, T_YP)
            e = endstop_switch().interfaces
            for px, py, _ in e["pin_holes"]:      # clearance for the switch terminals (part frame x -> -Y, y -> +X)
                plate -= Pos(X_ES_X0 + py, X_ES_Y0 - px, Z_PLATE + T_YP / 2) * Cylinder(ES_PIN_D / 2, T_YP)
            plate += fillet_z(X_ES_X0 - 7.5, YB0 - 25, -1, -1, 2.0, zp0, zp1)
            for x, y in TOW_SCREWS:   # the Y belt tower is a separate block screwed on from below
                plate -= Pos(x, y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
        else:
            # ear for the X idler axle: M5 through-bolt, loose spacer under the idler, nut under the plate
            plate += Pos(X_IDLER_X, YB0 - 31, Z_PLATE + T_YP / 2) * Box(24, 12, T_YP)
            plate += fillet_z(X_IDLER_X - 12, YB0 - 25, -1, -1, 2.0, zp0, zp1)
            plate += fillet_z(X_IDLER_X + 12, YB0 - 25, 1, -1, 2.0, zp0, zp1)
            plate -= Pos(X_IDLER_X, YB0 - XB, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M5") / 2, T_YP)
        d.add(f"y_plate_{n}", plate, material="al6061", body="ybody")
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
    d.add("tool_plate", tool_plate_shape(), material="al6061", body="xbody")   # PETG gave 0.052 mm at the nozzle
    for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
        add_screw(d, f"tool_screw_{i}", "M3", 6, at=(x, YB0 + y, Z_TOP + T_TP - 3.2), body="xbody", threads_into="x_carriage")
    place(d, "hotend", hotend(), Location((0, YB0 + HOT_OFF, Z_TOP)), body="xbody")
    d.join("hotend", "tool_plate", "set_screw")     # two M3 set screws through the collar walls onto the heat-sink neck
    d.bom_extra("SETSCREW-M3x10", 2, 0.05)
    # heater and thermistor cartridges clamped in the heater block (the proxy block has no bores: declared overlaps)
    HB_Y, HB_Z = YB0 + HOT_OFF, Z_TOP - 47.5
    place(d, "hotend_heater", heater_cartridge(HOTEND_W, 24.0), Location((0, HB_Y + 3.5, HB_Z - 2.5)), body="xbody")
    place(d, "hotend_thermistor", thermistor_cartridge(), Location((2.5, HB_Y - 5.0, HB_Z + 3.5)), body="xbody")
    for nm in ("hotend_heater", "hotend_thermistor"):
        d.allow_overlap(nm, "hotend")
        d.join(nm, "hotend", "clamp")
    # ================= X drive ===================================================
    xclamp = Pos(0, (XC_Y0 + TAB_Y0) / 2, (TAB_Z0 + XC_Z1) / 2) * Box(40, TAB_Y0 - XC_Y0, XC_Z1 - TAB_Z0)
    xclamp -= Pos(0, TAB_Y0 - 0.75, Z_XB) * Box(40, 1.5, BWX + 1.2)   # one straight belt groove (no inside corners)
    for x, z in X_CLAMP_SCREWS:
        xclamp -= Pos(x, (XC_Y0 + TAB_Y0) / 2, z) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, TAB_Y0 - XC_Y0)
    d.add("x_belt_clamp", xclamp, material="al6061", body="xbody")
    for i, (x, z) in enumerate(X_CLAMP_SCREWS):
        add_screw(d, f"x_belt_clamp_screw_{i}", "M3", 10, at=(x, XC_Y0, z), direction=(0, 1, 0), body="xbody",
                  threads_into="tool_plate")
    place(d, "x_motor", nema17(34), Location((X_MOTOR_X, YB0 - XB, Z_PLATE)), body="ybody")
    place(d, "x_pulley", gt2_pulley(20, belt_width=BWX), Location((X_MOTOR_X, YB0 - XB, Z_XB - P_BC(BWX))), body="ybody")
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 10, at=(X_MOTOR_X + x, YB0 - XB + y, Z_PLATE + T_YP),
                  body="ybody", threads_into="x_motor")
    d.join("x_pulley", "x_motor", "set_screw")
    place(d, "x_idler", gt2_idler(20, belt_width=BWX), Location((X_IDLER_X, YB0 - XB, Z_XI)), body="ybody")
    d.add("x_idler_spacer", Pos(X_IDLER_X, YB0 - XB, Z_PLATE + T_YP + X_SP / 2) * (Cylinder(5.0, X_SP) - Cylinder(2.75, X_SP)),
          material="al6061", body="ybody")
    add_screw(d, "x_idler_bolt", "M5", 35, at=(X_IDLER_X, YB0 - XB, Z_XI + I_H(BWX)), body="ybody",
              clamps=("x_idler_spacer", "y_plate_right"))
    add_nut(d, "x_idler_nut", "M5", at=(X_IDLER_X, YB0 - XB, Z_PLATE), direction=(0, 0, -1), body="ybody", screw="x_idler_bolt")
    d.join("x_idler", "x_idler_bolt", "axle")
    d.join("x_idler_spacer", "y_plate_right", "clamp")
    # X endstop on the left Y plate
    xsw = place(d, "x_endstop", endstop_switch(),
                Location(Plane(origin=(X_ES_X0, X_ES_Y0, Z_PLATE + T_YP), x_dir=(0, -1, 0), z_dir=(0, 0, 1))), body="ybody")
    for i, (hx, hy, hz) in enumerate(xsw.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"x_endstop_screw_{i}", "M3", 8, at=(hx, hy, hz + 1.6), body="ybody", threads_into="y_plate_left",
                  clamps=("x_endstop",))
    # ================= toolhead: extruder, heat-sink fan ==========================
    place(d, "extruder", extruder_direct(), Location((0, YB0 + HOT_OFF, Z_TOP + T_TP)), body="xbody",
          process="purchased")   # the automatic rule read "extruder" as saw-cut extrusion
    for i, (x, y) in enumerate(EXT_SCREWS):
        add_screw(d, f"extruder_screw_{i}", "M3", 8, at=(x, YB0 + y, Z_TOP + 3.2), direction=(0, 0, 1), body="xbody",
                  threads_into="extruder")
    FAN_Z = Z_TOP - 15.0
    fan_ = place(d, "hotend_fan", fan(30), Location(Plane(origin=(0, YB0 + TP_REAR + 5, FAN_Z), x_dir=(1, 0, 0), z_dir=(0, 1, 0))),
                 body="xbody")
    for i, x in enumerate((-12.0, 12.0)):   # the fan hangs from its two upper holes on the rear face of the collar
        add_screw(d, f"fan_screw_{i}", "M3", 16, at=(x, YB0 + TP_REAR + 10, FAN_Z + 12), direction=(0, -1, 0), body="xbody",
                  threads_into="tool_plate", clamps=("hotend_fan",))
    # part-cooling fan on the left ear of the collar (its duct to the nozzle is not modelled)
    PF_Y, PF_Z = YB0 + 34.0, Z_TOP - 6.0 - 12.0
    place(d, "part_fan", fan(30), Location(Plane(origin=(-23.0 - EAR - 5.0, PF_Y, PF_Z), x_dir=(0, 1, 0), z_dir=(1, 0, 0))),
          body="xbody")
    for i, y in enumerate((-12.0, 12.0)):
        add_screw(d, f"part_fan_screw_{i}", "M3", 16, at=(-23.0 - EAR - 10.0, PF_Y + y, PF_Z + 12.0), direction=(1, 0, 0),
                  body="xbody", threads_into="tool_plate", clamps=("part_fan",))
    # ================= Y drive: vertical belt plane outboard of the right rail =====
    xf = FX / 2
    xcyl = lambda r, h: Rot(0, 90, 0) * Cylinder(r, h)
    # motor mount: strip bolted along the rail's outer slot + a tall ear behind the frame for the motor face
    mm = (Pos(xf + MT / 2, 152.5, FZ) * Box(MT, 55, 20)
          + Pos(xf + MT / 2, (170 + YM_Y + 23) / 2, (FZ - 10 + Z_YC + 23) / 2) * Box(MT, YM_Y + 23 - 170, Z_YC + 23 - FZ + 10))
    mm += fillet_x(170.0, FZ + 10, -1, 1, 3.0, xf, xf + MT)
    mm -= Pos(xf + MT / 2, YM_Y, Z_YC) * xcyl(11.5, MT)
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            mm -= Pos(xf + MT / 2, YM_Y + y, Z_YC + z) * xcyl(clearance_hole("M3") / 2, MT)
    Y_MOUNT_BOLTS = (133.0, 150.0, 167.0)
    for y in Y_MOUNT_BOLTS:
        mm -= Pos(xf + MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_motor_mount", mm, material="al6061")
    place(d, "y_motor", nema17(48), Location(Plane(origin=(xf, YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    place(d, "y_pulley", gt2_pulley(20, belt_width=BWY),
          Location(Plane(origin=(YB_X - P_BC(BWY), YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    k = 0
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"y_motor_screw_{k}", "M3", 8, at=(xf + MT, YM_Y + y, Z_YC + z), direction=(-1, 0, 0),
                      threads_into="y_motor"); k += 1
    for i, y in enumerate(Y_MOUNT_BOLTS):
        add_screw(d, f"y_motor_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    d.join("y_pulley", "y_motor", "set_screw")
    # idler mount at the front, in front of the Y carriage / Y plate sweep: flat 4 mm plate; the idler runs on an
    # M5 through-bolt with a loose 6 mm spacer and a nut on the inside face
    x_yi = YB_X - I_H(BWY) / 2
    im = Pos(xf + MT / 2, YI_Y - 1.5, (FZ - 10 + Z_YC + 9) / 2) * Box(MT, 31, Z_YC + 9 - FZ + 10)
    im -= Pos(xf + MT / 2, YI_Y, Z_YC) * xcyl(clearance_hole("M5") / 2, MT)
    for y in (YI_Y - 9.0, YI_Y + 6.0):
        im -= Pos(xf + MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_idler_mount", im, material="al6061")
    for i, y in enumerate((YI_Y - 9.0, YI_Y + 6.0)):
        add_screw(d, f"y_idler_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    d.add("y_idler_spacer", Pos(xf + MT + Y_SP / 2, YI_Y, Z_YC) * (xcyl(5.0, Y_SP) - xcyl(2.75, Y_SP)), material="al6061")
    place(d, "y_idler", gt2_idler(20, belt_width=BWY), Location(Plane(origin=(x_yi, YI_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    add_screw(d, "y_idler_bolt", "M5", 30, at=(x_yi + I_H(BWY), YI_Y, Z_YC), direction=(-1, 0, 0),
              clamps=("y_idler_spacer", "y_idler_mount"))
    add_nut(d, "y_idler_nut", "M5", at=(xf, YI_Y, Z_YC), direction=(-1, 0, 0), screw="y_idler_bolt")
    d.join("y_idler", "y_idler_bolt", "axle")
    d.join("y_idler_spacer", "y_idler_mount", "clamp")
    # Y belt clamp on top of the right Y plate: grooved bar, belt ends enter from front and back
    PC = YB0 - 5.75
    YA0, YA1 = PC - 14, PC + 14
    zt = Z_PLATE + T_YP
    yclamp = Pos((RAIL_X + 16 + YB_X + BWY / 2 + 1.5) / 2, PC, zt + 2) * Box(YB_X + BWY / 2 + 1.5 - RAIL_X - 16, YA1 - YA0, 4)
    yclamp -= Pos(YB_X, PC, zt + 0.75) * Box(BWY + 0.4, YA1 - YA0, 1.5)   # one straight belt groove
    Y_CLAMP_SCREWS = [(YB_X, PC), (RAIL_X + 18.5, PC - 9), (RAIL_X + 18.5, PC + 9)]
    for x, y in Y_CLAMP_SCREWS:
        yclamp -= Pos(x, y, zt + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("y_belt_clamp", yclamp, material="al6061", body="ybody")
    for i, (x, y) in enumerate(Y_CLAMP_SCREWS):
        add_screw(d, f"y_belt_clamp_screw_{i}", "M3", 10, at=(x, y, zt + 4), body="ybody", threads_into="y_plate_right")
    # ================= second Y drive (v2): mirrored motor + belt on the left rail =====
    mml = (Pos(-xf - MT / 2, 152.5, FZ) * Box(MT, 55, 20)
           + Pos(-xf - MT / 2, (170 + YM_Y + 23) / 2, (FZ - 10 + Z_YCL + 23) / 2) * Box(MT, YM_Y + 23 - 170, Z_YCL + 23 - FZ + 10))
    mml += fillet_x(170.0, FZ + 10, -1, 1, 3.0, -xf - MT, -xf)
    mml -= Pos(-xf - MT / 2, YM_Y, Z_YCL) * xcyl(11.5, MT)
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            mml -= Pos(-xf - MT / 2, YM_Y + y, Z_YCL + z) * xcyl(clearance_hole("M3") / 2, MT)
    for y in Y_MOUNT_BOLTS:
        mml -= Pos(-xf - MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_motor_mount_l", mml, material="al6061")
    place(d, "y_motor_l", nema17(48), Location(Plane(origin=(-xf, YM_Y, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    place(d, "y_pulley_l", gt2_pulley(20, belt_width=BWY),
          Location(Plane(origin=(YBL_X + P_BC(BWY), YM_Y, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    k = 0
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"y_motor_l_screw_{k}", "M3", 8, at=(-xf - MT, YM_Y + y, Z_YCL + z), direction=(1, 0, 0),
                      threads_into="y_motor_l"); k += 1
    for i, y in enumerate(Y_MOUNT_BOLTS):
        add_screw(d, f"y_motor_mount_l_bolt_{i}", "M5", 8, at=(-xf - MT, y, FZ), direction=(1, 0, 0),
                  threads_into="frame_top_left", tnut=True)
    d.join("y_pulley_l", "y_motor_l", "set_screw")
    x_yil = YBL_X + I_H(BWY) / 2
    # flat 4 mm plate again; it reaches back to just short of the X motor pad's front edge at y = -TY and carries
    # the Y endstop on its outer face (pressed by that edge)
    iml_y0, iml_y1 = YI_YL - 17.0, PAD_FRONT - TY - 1.5
    iml = Pos(-xf - MT / 2, (iml_y0 + iml_y1) / 2, (FZ - 10 + Z_YCL + 9) / 2) * Box(MT, iml_y1 - iml_y0, Z_YCL + 9 - FZ + 10)
    iml -= Pos(-xf - MT / 2, YI_YL, Z_YCL) * xcyl(clearance_hole("M5") / 2, MT)
    for y in (YI_YL - 9.0, YI_YL + 6.0):
        iml -= Pos(-xf - MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    ysw = place(d, "y_endstop", endstop_switch(),
                Location(Plane(origin=(-xf - MT, PAD_FRONT - TY - ES_TRIG, Z_PLATE + T_YP / 2 + ES_SIDE),
                               x_dir=(0, 0, 1), z_dir=(-1, 0, 0))))
    for hx, hy, hz in ysw.meta["interfaces"]["mount_holes_m3"]:
        iml -= Pos(-xf - MT / 2, hy, hz) * xcyl(clearance_hole("M3") / 2, MT)
    for hx, hy, hz in ysw.meta["interfaces"]["pin_holes"]:
        iml -= Pos(-xf - MT / 2, hy, hz) * xcyl(ES_PIN_D / 2, MT)
    d.add("y_idler_mount_l", iml, material="al6061")
    for i, (hx, hy, hz) in enumerate(ysw.meta["interfaces"]["mount_holes_m3"]):
        add_screw(d, f"y_endstop_screw_{i}", "M3", 8, at=(hx - 1.6, hy, hz), direction=(1, 0, 0),
                  clamps=("y_endstop", "y_idler_mount_l"))
        add_nut(d, f"y_endstop_nut_{i}", "M3", at=(-xf, hy, hz), direction=(1, 0, 0), screw=f"y_endstop_screw_{i}")
    for i, y in enumerate((YI_YL - 9.0, YI_YL + 6.0)):
        add_screw(d, f"y_idler_mount_l_bolt_{i}", "M5", 8, at=(-xf - MT, y, FZ), direction=(1, 0, 0),
                  threads_into="frame_top_left", tnut=True)
    d.add("y_idler_spacer_l", Pos(-xf - MT - Y_SP_L / 2, YI_YL, Z_YCL) * (xcyl(5.0, Y_SP_L) - xcyl(2.75, Y_SP_L)),
          material="al6061")
    place(d, "y_idler_l", gt2_idler(20, belt_width=BWY),
          Location(Plane(origin=(x_yil, YI_YL, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    add_screw(d, "y_idler_l_bolt", "M5", 35, at=(x_yil - I_H(BWY), YI_YL, Z_YCL), direction=(1, 0, 0),
              clamps=("y_idler_spacer_l", "y_idler_mount_l"))
    add_nut(d, "y_idler_l_nut", "M5", at=(-xf, YI_YL, Z_YCL), direction=(1, 0, 0), screw="y_idler_l_bolt")
    d.join("y_idler_l", "y_idler_l_bolt", "axle")
    d.join("y_idler_spacer_l", "y_idler_mount_l", "clamp")
    # belt tower: 20 x 22.5 block of 25 mm plate on the left Y plate, two M3 from below; the clamp bar screws tap into it
    d.add("y_belt_tower_l", Pos((TOW_X0 + TOW_X1) / 2, (TOW_Y0 + TOW_Y1) / 2, Z_PLATE + T_YP + TOW_H / 2) * Box(
        TOW_X1 - TOW_X0, TOW_Y1 - TOW_Y0, TOW_H), material="al6061", body="ybody")
    for i, (x, y) in enumerate(TOW_SCREWS):
        add_screw(d, f"y_belt_tower_l_screw_{i}", "M3", 12, at=(x, y, Z_PLATE), direction=(0, 0, 1), body="ybody",
                  threads_into="y_belt_tower_l")
    # clamp bar on top of the tower
    PCL = (TOW_Y0 + TOW_Y1) / 2
    yclamp_l = Pos((TOW_X0 + TOW_X1) / 2, PCL, Z_TOW + 2) * Box(TOW_X1 - TOW_X0, TOW_Y1 - TOW_Y0, 4)
    # v4: the groove runs out through the +X side (v3 left a 0.1 mm wall there)
    yclamp_l -= Pos(YBL_X + 1.0, PCL, Z_TOW + 0.75) * Box(BWY + 0.4 + 2.0, TOW_Y1 - TOW_Y0, 1.5)
    YL_CLAMP_SCREWS = [(YBL_X, PCL), (TOW_X0 + 3.0, PCL - 7), (TOW_X0 + 3.0, PCL + 7)]
    for x, y in YL_CLAMP_SCREWS:
        yclamp_l -= Pos(x, y, Z_TOW + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("y_belt_clamp_l", yclamp_l, material="al6061", body="ybody")
    for i, (x, y) in enumerate(YL_CLAMP_SCREWS):
        add_screw(d, f"y_belt_clamp_l_screw_{i}", "M3", 10, at=(x, y, Z_TOW + 4), body="ybody", threads_into="y_belt_tower_l")
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
    # the tray lies under screws that are driven from below (beam bolts, extruder screws): a driver hole under each,
    # and no board under any of them
    for x, y in [(sx * (RAIL_X - 25), YB0) for sx in (-1, 1)] + [(x, YB0 + y) for x, y in EXT_SCREWS]:
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
    # ================= belts =====================================================
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (-20.0, XA_Y, Z_XB)), ("pulley", "x_pulley", "ccw"),
                                   ("pulley", "x_idler", "ccw"), ("anchor", "xbody", (20.0, XA_Y, Z_XB))],
                        axis=(0, 0, 1), width=BWX))
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, YA0, Z_YA)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0), width=BWY))
    d.belts.append(Belt("y_belt_l", [("anchor", "ybody", (YBL_X, TOW_Y0, Z_YAL)), ("pulley", "y_idler_l", "cw"),
                                     ("pulley", "y_pulley_l", "cw"), ("anchor", "ybody", (YBL_X, TOW_Y1, Z_YAL))],
                        axis=(1, 0, 0), width=BWY))
    d.bom_extra("GT2-BELT-12MM-OPEN-1M", 3, 6.0)   # v2: 12 mm belt (price is an estimate; pulley SKUs do not encode width)

    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY, TY),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(-Z_OVER, PRINT_Z),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": "leadscrew"}))
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
                   {"joint": "z", "switch": "z_endstop", "at": "max"}]     # jack screw in the nut tab
    build_electrical(d)      # looms replace v3's three Cable entries (their flexing spans are added to d.cables)
    d.adjustments += [
        # set by turning the M3 jack screw in the nut tab (0.5 mm per turn, lock nut); 4 mm up / 10 mm down of screw
        # travel, and rail, lead screw and nut all have Z_OVER of travel beyond both ends of the print height
        Adjustment("z endstop jack screw", "z_offset", range_mm=Z_OVER),
        # nuts under the four bed screws; silicone columns compressed 0.5 .. 3.5 mm
        Adjustment("bed levelling nuts on silicone columns", "bed_level", range_mm=1.5),
        # T-nuts slide across the 6.2 mm slot (+/-1.6 on an M3): left rail set to a straight edge, right rail's
        # screws tightened one by one while the gantry is run along it; the beam's T-nuts absorb the spacing
        Adjustment("y rails on sliding T-nuts", "rail_align", range_mm=1.5, joint="y"),
        Adjustment("z rails on sliding T-nuts", "rail_align", range_mm=1.5, joint="z",
                   note="left rail to a square, right rail tightened while the carrier is run up and down"),
        # the nut hangs under the tab with NUT_FLOAT radial room; one pin in a radial slot stops it turning
        Adjustment("floating lead screw nut", "float", range_mm=NUT_FLOAT - 0.2, joint="z"),
    ]
    # how to print on this machine: the digital twin runs as a verifier, using the FEA nozzle stiffness below
    d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
                 "stiffness": {"x": "nozzle_stiffness_x", "y": "nozzle_stiffness_y"}}

    # ================= structure =================================================
    # nozzle-point stiffness of the whole gantry moving structure, toolhead at mid-span (worst case);
    # deflection probed at the nozzle tip
    moving = ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate", "hotend"]
    y_plate_fix = [("y_plate_left", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6),
                   ("y_plate_right", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6)]
    block_face = ("hotend", lambda f: abs(f.center().Z - (Z_NOZZLE + 5)) < 1e-6)   # heater-block underside
    for nm, force in (("nozzle_stiffness_y", (0.0, 3.0, -2.0)), ("nozzle_stiffness_x", (3.0, 0.0, -2.0))):
        d.assemblycases.append(AssemblyCase(nm, moving, fixed=y_plate_fix, loaded=block_face, force=force,
                                            probe=nozzle, max_deflection=0.03, min_fos=5.0))
    # bed carrier: payload x3 (plus the bed plate's own weight x3)
    w_bed = 3.0 * (PAYLOAD_KG + bed_own) * 9.81
    carriage_pads = lambda f: abs(f.center().Y - Y_CAR) < 1e-6 and f.area > 1000 and abs(f.center().X) > 70
    d.loadcases.append(LoadCase(
        "payload_x3_on_bed", "carrier", fixed=carriage_pads,
        loaded=lambda f: abs(f.center().Z - Z_FL) < 1e-6 and f.area > 1000,
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(
        "nut_thrust", "carrier", fixed=carriage_pads,
        loaded=lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 300,
        force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.3))

    # ================= heat: bed 60 K above the frame =============================
    # Bed at +60 K, columns half way, carrier and carriages at frame temperature (worst case for differential growth).
    # Carriages held on their rails. The nozzle (cold, on the gantry) does not move, so the change in the gap is the
    # vertical movement of the bed surface under it. Limits: gap within half a 0.2 mm layer (the Z offset is set
    # with the bed hot, so this is margin on top), bow below 0.1 mm.
    cols = [f"bed_column_{i}" for i in range(len(BED_MOUNTS))]
    on_rail = lambda f: abs(f.center().Y - (Y_FACE - 8.0)) < 1e-6
    d.thermalcases.append(ThermalCase(
        "bed_heated_60K", ["bed", *cols, "carrier", "z_carriage_left", "z_carriage_right"],
        fixed=[("z_carriage_left", on_rail), ("z_carriage_right", on_rail)],
        temps={"bed": 60.0, **{c: 30.0 for c in cols}, "*": 0.0},
        # a probe snaps to the nearest meshed point, and the nozzle is not in this model (it is 150 mm above the bed
        # at home), so the "nozzle" reference is put on the held rail face: it must report zero movement
        probes={"nozzle": (-UP_X, Y_FACE - 8.0, ZC), "bed": (0.0, YB0 + HOT_OFF, Z_BED + T_BED)},
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
        for n, ax in (("z_carriage_left", "Z"), ("z_carriage_right", "Z"), ("y_carriage_left", "Y"),
                      ("y_carriage_right", "Y"), ("x_carriage", "X")):
            rail = {"z_carriage_left": "z_rail_left", "z_carriage_right": "z_rail_right", "y_carriage_left": "y_rail_left",
                    "y_carriage_right": "y_rail_right", "x_carriage": "x_rail"}[n]
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
