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

Proxies / not modelled (flagged): hotend is a hand-made proxy; the hotend collar is modelled
as a plain bore (a real one is a split clamp); payload is carried as extra mass on the bed.
"""
import math

from build123d import Box, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from mechloop import AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.model import Belt
from mechloop.parts import (Stock, add_corner_bracket, add_screw, clearance_hole, extrusion_2020, gt2_idler, gt2_pulley,
                            leadscrew_nut_t8, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place,
                            shaft_coupler)

# ---- brief --------------------------------------------------------------------
PRINT_X, PRINT_Y, PRINT_Z = 180.0, 180.0, 150.0
PAYLOAD_KG = 1.0
V_XY, A_XY = 250.0, 4000.0
V_Z, A_Z = 12.0, 200.0
MARGIN = 3.0
ENVELOPE = (420.0, 420.0, 480.0)

# ---- frame ----------------------------------------------------------------------
FX, FY, FZ = 340.0, 360.0, 300.0      # frame outer X, Y and top-ring centre height
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
BED_SCREWS = [(sx * 79.0, y) for sx in (-1, 1) for y in (BED_Y1 - 215.0, BED_Y1 - 120.0, BED_Y1 - 30.0)]
NUT_HOLES = [(8.0, 0.0), (-8.0, 0.0), (0.0, 8.0), (0.0, -8.0)]

# ---- gantry ---------------------------------------------------------------------
Z_RAIL = FZ + 10
Z_PLATE = Z_RAIL + 13          # underside of the Y plates
T_YP = 6.0
Z_BEAM = Z_PLATE + T_YP + 10
Z_TOP = Z_BEAM + 10 + 13       # top of the X carriage
HOT_OFF = 31.0                 # hotend axis behind the beam centre
YB0 = BED_CY - HOT_OFF         # beam centre Y at home (nozzle over the bed centre)
X_MOTOR_X = -(FX / 2 + 27.0)
RIB = 8.0
Z_NOZZLE = Z_TOP - 4 - 60      # nozzle tip (hotend proxy is 60 long, top at Z_TOP - 4)
PR = 20 * 2.0 / math.pi / 2     # pitch radius of the 20T pulleys / idlers
BWX, BWY = 9.0, 9.0             # GT2 belt widths (v2: 9 mm instead of 6 mm; stiffer belts)
P_BC = lambda w: 7.0 + (w + 1) / 2      # gt2_pulley belt centre above its hub bottom
I_H = lambda w: w + 2.5                 # gt2_idler height
MT_Y = 4.0                     # Y motor / idler mount plate thickness
XB = 28.0                      # X belt centre line, in front of the beam centre
X_IDLER_X = RAIL_X - 20.0
Z_XB = Z_PLATE + T_YP + 0.5 + P_BC(BWX)      # X belt centre height
XA_Y = YB0 - XB + PR           # near (anchored) run of the X belt
TAB_Y0 = XA_Y + 0.7 + 0.03     # tab front face = belt tooth side
YB_X = FX / 2 + MT_Y + 0.5 + P_BC(BWY)           # Y belt plane, outboard of the right frame rail
YM_Y, YI_Y = FY / 2 + 24.0, -128.0      # Y motor pulley (behind the frame) and Y idler (front)
MT = MT_Y
Z_YA = Z_PLATE + T_YP + 0.7    # upper (anchored) run of the Y belt lies on the right Y plate
Z_YC = Z_YA - PR
# v2 second (left) Y drive: belt plane outboard of the left rail, loop ABOVE the left Y plate on a
# clamp tower, so it clears the X motor (below the plate) and the X pulley / X belt (below the loop)
TOW_H = 20.0
YBL_X = -(YB_X + 1.5)
TOW_X0, TOW_X1 = YBL_X - 12.0, YBL_X + BWY / 2 + 0.3
TOW_Y0, TOW_Y1 = YB0 - 9.0, YB0 + 13.5
Z_TOW = Z_PLATE + T_YP + TOW_H
Z_YAL = Z_TOW + 0.7            # lower (anchored) run of the left Y belt lies on the tower
Z_YCL = Z_YAL + PR
YI_YL = -156.0                 # left Y idler: in front of the sweep of the X motor pad
Z_XI = Z_XB - I_H(BWX) / 2              # underside of the X idler
NOZZLE_GAP = 0.1               # bed surface -> nozzle with the bed at the top: must not exceed the first layer
                               # height (the digital twin showed a 1.0 mm gap made the first layer unreachable)

# bed heights follow from the nozzle
Z_BED = Z_NOZZLE - NOZZLE_GAP - T_BED - PRINT_Z   # bed underside at home (bed at the bottom)
ZC = Z_BED - 30.9                                 # Z carriage centre at home (0.9 lower after the bed datum moved up)
Z_TAB = ZC - 6.0                                  # underside of the nut tab at home


def hotend() -> Stock:
    """PROXY (not in the catalog): V6-style hotend. Local frame: axis Z, top at Z=0, nozzle tip at Z=-60."""
    body = Pos(0, 0, -20) * Cylinder(11, 40) + Pos(0, 0, -47.5) * Box(20, 16, 15) + Pos(0, 0, -57.5) * Cylinder(2, 5)
    return Stock(body, "HOTEND-V6", "UNVERIFIED proxy: V6-style hotend with heater block", 0.12, material="al6061",
                 cost_usd=25.0)


def carrier_shape(carriage_holes):
    zp0, zp1 = ZC - 23, ZC + 23
    c = Pos(0, Y_PF + (T_BP - PAD) / 2, ZC) * Box(208, T_BP - PAD, zp1 - zp0)
    for sx in (-1, 1):
        c += Pos(sx * UP_X, Y_CAR - PAD / 2, ZC) * Box(27, PAD, 45.4)
        prof = Plane.YZ * Polygon((Y_CAR - PAD, zp0), (Y_CAR - PAD, Z_BED), (BED_Y0, Z_BED), (BED_Y0, Z_BED - 12),
                                  align=None)
        c += Pos(sx * UP_X - T_WEB / 2, 0, 0) * extrude(prof, T_WEB)
        x0, x1 = sorted((sx * FL_IN, sx * (UP_X + T_WEB / 2)))
        c += Pos((x0 + x1) / 2, (BED_Y0 + Y_PF) / 2, Z_BED - T_FL / 2) * Box(x1 - x0, Y_PF - BED_Y0, T_FL)
    y1 = LS_Y + 13
    c += Pos(0, (Y_PF + 3 + y1) / 2, Z_TAB + T_TAB / 2) * Box(26, y1 - Y_PF - 3, T_TAB)
    c -= Pos(0, LS_Y, Z_TAB + T_TAB / 2) * Cylinder(5.4, T_TAB)
    for dx, dy in NUT_HOLES:
        c -= Pos(dx, LS_Y + dy, Z_TAB + T_TAB / 2) * Cylinder(clearance_hole("M3") / 2, T_TAB)
    for hx, hy, hz in carriage_holes:
        c -= Pos(hx, (Y_PF + Y_CAR) / 2, hz) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, T_BP)
    for x, y in BED_SCREWS:
        c -= Pos(x, y, Z_BED - T_FL / 2) * Cylinder(clearance_hole("M3") / 2, T_FL)
    return c


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
XC_Y0 = TAB_Y0 - 4.6             # front face of the X belt clamp bar
X_CLAMP_SCREWS = [(-13.0, Z_XB + 7.5), (13.0, Z_XB + 7.5), (0.0, Z_XB - 5.75)]


def tool_plate_shape():
    top = Pos(0, (TAB_Y0 + YB0 + 20) / 2, Z_TOP + 2) * Box(46, YB0 + 20 - TAB_Y0, 4)
    # belt tab: drops in front of the carriage and beam to the X belt line; clears the Y plates below
    top += Pos(0, (TAB_Y0 + YB0 - 14) / 2, (TAB_Z0 + Z_TOP) / 2) * Box(40, YB0 - 14 - TAB_Y0, Z_TOP - TAB_Z0)
    rear = Pos(0, YB0 + 18, Z_TOP - 20) * Box(46, 4, 48)
    tp = top + rear
    for sx in (-1, 1):
        tp += Pos(sx * 20, YB0 + 5.25, Z_TOP + 4 + RIB / 2) * Box(6, 45.5 - 8 + RIB, RIB)
        tp += Pos(sx * 20, YB0 + 20 + RIB / 2, Z_TOP - 20 + RIB / 2) * Box(6, RIB, 48 + RIB)
    # collar around the top 12 mm of the hotend (modelled as a plain bore; real part is a split clamp)
    tp += Pos(0, YB0 + 20 + 13, Z_TOP - 10) * Box(46, 26, 12)
    tp -= Pos(0, YB0 + HOT_OFF, Z_TOP - 10) * Cylinder(11, 12)
    for x in (-10, 10):
        for y in (-10, 10):
            tp -= Pos(x, YB0 + y, Z_TOP + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    return tp


def build() -> Design:
    d = Design("printer_v2", envelope=ENVELOPE, base="frame_bot_left")
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
    Z_RAIL_C = 184.0     # 210 mm rail, 79..289: below the top back extrusion, >= 5 mm past the carriage both ends
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"z_rail_{n}", mgn12_rail(210),
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
    place(d, "z_nut", leadscrew_nut_t8(), Location((0, LS_Y, Z_TAB - 3.5)), body="zbody")
    for i, (dx, dy) in enumerate(NUT_HOLES):
        add_screw(d, f"nut_screw_{i}", "M3", 12, at=(dx, LS_Y + dy, Z_TAB + T_TAB), body="zbody", threads_into="z_nut")
    d.bom_extra("HEXNUT-M3", 4, 0.03)
    bed_shape = Pos(0, BED_CY, Z_BED + T_BED / 2) * Box(BED, BED, T_BED)
    bed_own = bed_shape.volume * 2700e-9
    d.add("bed", bed_shape, material="al6061", body="zbody", mass_kg=bed_own + PAYLOAD_KG)   # plate + payload
    for i, (x, y) in enumerate(BED_SCREWS):
        add_screw(d, f"bed_screw_{i}", "M3", 10, at=(x, y, Z_BED - T_FL), direction=(0, 0, 1), body="zbody",
                  threads_into="bed")
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
        x_in = sx * (RAIL_X - 35)
        x_out = X_MOTOR_X - 24 if sx < 0 else YB_X + BWY / 2 + 1.5     # right plate reaches out under the Y belt clamp
        # rear edge trimmed to +13.5 so the tool plate passes behind it
        plate = Pos((x_in + x_out) / 2, YB0 - 5.75, Z_PLATE + T_YP / 2) * Box(abs(x_out - x_in), 38.5, T_YP)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP - 1.6) * Cylinder(3.0, 3.2)
        x_bolt = sx * (RAIL_X - 25)
        plate -= Pos(x_bolt, YB0, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M5") / 2, T_YP)
        if sx < 0:
            # motor pad in front of the beam line so the X pulley sits on the belt centre line
            plate += Pos(X_MOTOR_X, YB0 + (13.5 - XB - 24) / 2, Z_PLATE + T_YP / 2) * Box(48, XB + 24 + 13.5, T_YP)
            plate -= Pos(X_MOTOR_X, YB0 - XB, Z_PLATE + T_YP / 2) * Cylinder(11.5, T_YP)
            for x in (-15.5, 15.5):
                for y in (-15.5, 15.5):
                    plate -= Pos(X_MOTOR_X + x, YB0 - XB + y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
            # integral clamp tower for the left Y belt
            plate += Pos((TOW_X0 + TOW_X1) / 2, (TOW_Y0 + TOW_Y1) / 2, Z_PLATE + T_YP + TOW_H / 2) * Box(
                TOW_X1 - TOW_X0, TOW_Y1 - TOW_Y0, TOW_H)
        else:
            # ear + integral boss carrying the X idler axle (tapped M5 through boss and plate: 11.5 mm of thread)
            plate += Pos(X_IDLER_X, YB0 - 31, Z_PLATE + T_YP / 2) * Box(24, 12, T_YP)
            plate += Pos(X_IDLER_X, YB0 - XB, (Z_PLATE + T_YP + Z_XI) / 2) * Cylinder(5.0, Z_XI - Z_PLATE - T_YP)
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
        add_screw(d, f"tool_screw_{i}", "M3", 8, at=(x, YB0 + y, Z_TOP + 4), body="xbody", threads_into="x_carriage")
    place(d, "hotend", hotend(), Location((0, YB0 + HOT_OFF, Z_TOP - 4)), body="xbody")
    d.join("hotend", "tool_plate", "clamp")
    # ================= X drive ===================================================
    xclamp = Pos(0, (XC_Y0 + TAB_Y0) / 2, Z_XB + 1) * Box(40, TAB_Y0 - XC_Y0, 20)
    for sx in (-1, 1):   # pockets grip the last 14 mm of each belt end against the tab
        xclamp -= Pos(sx * 13, TAB_Y0 - 0.75, Z_XB) * Box(14, 1.5, BWX + 1.2)
    for x, z in X_CLAMP_SCREWS:
        xclamp -= Pos(x, (XC_Y0 + TAB_Y0) / 2, z) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, TAB_Y0 - XC_Y0)
    d.add("x_belt_clamp", xclamp, material="al6061", body="xbody")
    for i, (x, z) in enumerate(X_CLAMP_SCREWS):
        add_screw(d, f"x_belt_clamp_screw_{i}", "M3", 10, at=(x, XC_Y0, z), direction=(0, 1, 0), body="xbody",
                  threads_into="tool_plate")
    place(d, "x_motor", nema17(40), Location((X_MOTOR_X, YB0 - XB, Z_PLATE)), body="ybody")
    place(d, "x_pulley", gt2_pulley(20, belt_width=BWX), Location((X_MOTOR_X, YB0 - XB, Z_PLATE + T_YP + 0.5)), body="ybody")
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 10, at=(X_MOTOR_X + x, YB0 - XB + y, Z_PLATE + T_YP),
                  body="ybody", threads_into="x_motor")
    d.join("x_pulley", "x_motor", "set_screw")
    place(d, "x_idler", gt2_idler(20, belt_width=BWX), Location((X_IDLER_X, YB0 - XB, Z_XI)), body="ybody")
    add_screw(d, "x_idler_bolt", "M5", 20, at=(X_IDLER_X, YB0 - XB, Z_XI + I_H(BWX)), body="ybody", threads_into="y_plate_right")
    d.join("x_idler", "x_idler_bolt", "axle")
    # ================= Y drive: vertical belt plane outboard of the right rail =====
    xf = FX / 2
    xcyl = lambda r, h: Rot(0, 90, 0) * Cylinder(r, h)
    # motor mount: strip bolted along the rail's outer slot + a tall ear behind the frame for the motor face
    mm = (Pos(xf + MT / 2, 152.5, FZ) * Box(MT, 55, 20)
          + Pos(xf + MT / 2, (170 + YM_Y + 23) / 2, (FZ - 10 + Z_YC + 23) / 2) * Box(MT, YM_Y + 23 - 170, Z_YC + 23 - FZ + 10))
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
    # idler mount at the front, in front of the Y carriage / Y plate sweep (reaches y = -109.75);
    # integral boss tapped M5 for the idler axle (10.75 mm of thread)
    x_yi = YB_X - I_H(BWY) / 2
    im = Pos(xf + MT / 2, YI_Y - 1.5, (FZ - 10 + Z_YC + 9) / 2) * Box(MT, 31, Z_YC + 9 - FZ + 10)
    im += Pos((xf + MT + x_yi) / 2, YI_Y, Z_YC) * xcyl(5.0, x_yi - xf - MT)
    for y in (YI_Y - 9.0, YI_Y + 6.0):
        im -= Pos(xf + MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_idler_mount", im, material="al6061")
    for i, y in enumerate((YI_Y - 9.0, YI_Y + 6.0)):
        add_screw(d, f"y_idler_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    place(d, "y_idler", gt2_idler(20, belt_width=BWY), Location(Plane(origin=(x_yi, YI_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    add_screw(d, "y_idler_bolt", "M5", 20, at=(x_yi + I_H(BWY), YI_Y, Z_YC), direction=(-1, 0, 0), threads_into="y_idler_mount")
    d.join("y_idler", "y_idler_bolt", "axle")
    # Y belt clamp on top of the right Y plate: grooved bar, belt ends enter from front and back
    PC = YB0 - 5.75
    YA0, YA1 = PC - 14, PC + 14
    zt = Z_PLATE + T_YP
    yclamp = Pos((RAIL_X + 16 + YB_X + BWY / 2 + 1.5) / 2, PC, zt + 2) * Box(YB_X + BWY / 2 + 1.5 - RAIL_X - 16, YA1 - YA0, 4)
    for sy in (-1, 1):
        yclamp -= Pos(YB_X, PC + sy * 9, zt + 0.75) * Box(BWY + 0.4, 10, 1.5)
    Y_CLAMP_SCREWS = [(YB_X, PC), (RAIL_X + 18.5, PC - 9), (RAIL_X + 18.5, PC + 9)]
    for x, y in Y_CLAMP_SCREWS:
        yclamp -= Pos(x, y, zt + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("y_belt_clamp", yclamp, material="al6061", body="ybody")
    for i, (x, y) in enumerate(Y_CLAMP_SCREWS):
        add_screw(d, f"y_belt_clamp_screw_{i}", "M3", 10, at=(x, y, zt + 4), body="ybody", threads_into="y_plate_right")
    # ================= second Y drive (v2): mirrored motor + belt on the left rail =====
    mml = (Pos(-xf - MT / 2, 152.5, FZ) * Box(MT, 55, 20)
           + Pos(-xf - MT / 2, (170 + YM_Y + 23) / 2, (FZ - 10 + Z_YCL + 23) / 2) * Box(MT, YM_Y + 23 - 170, Z_YCL + 23 - FZ + 10))
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
    iml = Pos(-xf - MT / 2, YI_YL - 1.5, (FZ - 10 + Z_YCL + 9) / 2) * Box(MT, 31, Z_YCL + 9 - FZ + 10)
    iml += Pos((-xf - MT + x_yil) / 2, YI_YL, Z_YCL) * xcyl(5.0, -xf - MT - x_yil)
    for y in (YI_YL - 9.0, YI_YL + 6.0):
        iml -= Pos(-xf - MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_idler_mount_l", iml, material="al6061")
    for i, y in enumerate((YI_YL - 9.0, YI_YL + 6.0)):
        add_screw(d, f"y_idler_mount_l_bolt_{i}", "M5", 8, at=(-xf - MT, y, FZ), direction=(1, 0, 0),
                  threads_into="frame_top_left", tnut=True)
    place(d, "y_idler_l", gt2_idler(20, belt_width=BWY),
          Location(Plane(origin=(x_yil, YI_YL, Z_YCL), x_dir=(0, 1, 0), z_dir=(-1, 0, 0))))
    add_screw(d, "y_idler_l_bolt", "M5", 20, at=(x_yil - I_H(BWY), YI_YL, Z_YCL), direction=(1, 0, 0),
              threads_into="y_idler_mount_l")
    d.join("y_idler_l", "y_idler_l_bolt", "axle")
    # clamp bar on top of the tower
    PCL = (TOW_Y0 + TOW_Y1) / 2
    yclamp_l = Pos((TOW_X0 + TOW_X1) / 2, PCL, Z_TOW + 2) * Box(TOW_X1 - TOW_X0, TOW_Y1 - TOW_Y0, 4)
    for sy in (-1, 1):
        yclamp_l -= Pos(YBL_X, PCL + sy * 7.25, Z_TOW + 0.75) * Box(BWY + 0.4, 8, 1.5)
    YL_CLAMP_SCREWS = [(YBL_X, PCL), (TOW_X0 + 3.0, PCL - 7), (TOW_X0 + 3.0, PCL + 7)]
    for x, y in YL_CLAMP_SCREWS:
        yclamp_l -= Pos(x, y, Z_TOW + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("y_belt_clamp_l", yclamp_l, material="al6061", body="ybody")
    for i, (x, y) in enumerate(YL_CLAMP_SCREWS):
        add_screw(d, f"y_belt_clamp_l_screw_{i}", "M3", 10, at=(x, y, Z_TOW + 4), body="ybody", threads_into="y_plate_left")
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
    d.bom_extra("GT2-BELT-9MM-OPEN-1M", 3, 4.5)   # v2: 9 mm belt (price is an estimate; pulley SKUs do not encode width)

    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY, TY),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": ["y_motor", "y_motor_l"], "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TX, TX),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    d.joints.append(Joint("z", "slide", "world", "zbody", (0, 0, 1), range=(0.0, PRINT_Z),
                          max_speed=V_Z, max_accel=A_Z, min_drive_margin=MARGIN,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": "leadscrew"}))
    # raise the bed, trace a 150 mm square with the nozzle, lower the bed
    d.program = [{"to": {"z": PRINT_Z}},
                 {"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": -75, "y": 75}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 0, "y": 0}},
                 {"to": {"z": 0.0}}]
    nozzle = (0.0, YB0 + HOT_OFF, Z_NOZZLE)
    d.tool_point = ("xbody", nozzle)
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
        loaded=lambda f: abs(f.center().Z - Z_BED) < 1e-6 and f.area > 1000,
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(
        "nut_thrust", "carrier", fixed=carriage_pads,
        loaded=lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 300,
        force=(0.0, 0.0, w_bed), min_fos=3.0, max_deflection=0.3))

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
