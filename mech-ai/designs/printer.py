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

Proxies / not modelled (flagged): hotend is a hand-made proxy; belts, idlers and belt
anchors are not modelled (the harness has no belt model); the hotend collar is modelled
as a plain bore (a real one is a split clamp); payload is carried as extra mass on the bed.
"""
from build123d import Box, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from mechloop import AssemblyCase, Design, Joint, LoadCase, Requirement
from mechloop.parts import (Stock, add_corner_bracket, add_screw, clearance_hole, extrusion_2020, gt2_pulley,
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
T_BED = 3.0
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
T_WEB, T_FL = 5.0, 4.0
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
NOZZLE_GAP = 1.0               # design gap bed surface -> nozzle with the bed at the top

# bed heights follow from the nozzle
Z_BED = Z_NOZZLE - NOZZLE_GAP - T_BED - PRINT_Z   # bed underside at home (bed at the bottom)
ZC = Z_BED - 25.0                                 # Z carriage centre at home
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
    m += Pos(0, Y_FACE - 2.5, Z_MF + 12) * Box(200, 5, 24)
    m -= Pos(0, LS_Y, Z_MF + T_MM / 2) * Cylinder(11.5, T_MM)
    m -= Pos(0, (LS_Y + y_back) / 2, Z_MF + T_MM / 2) * Box(23, y_back - LS_Y, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(x, LS_Y + y, Z_MF + T_MM / 2) * Cylinder(clearance_hole("M3") / 2, T_MM)
    for sx in (-1, 1):
        m -= Pos(sx * UP_X, Y_FACE - 2.5, Z_MF + 16) * Rot(90, 0, 0) * Cylinder(clearance_hole("M5") / 2, 5)
    return m


def tool_plate_shape():
    top = Pos(0, YB0 + 3.25, Z_TOP + 2) * Box(46, 33.5, 4)
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
    d = Design("printer", envelope=ENVELOPE, base="frame_bot_left")
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
    Z_RAIL_C = 194.0
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"z_rail_{n}", mgn12_rail(200),
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
        add_screw(d, f"bed_screw_{i}", "M3", 6, at=(x, y, Z_BED - T_FL), direction=(0, 0, 1), body="zbody",
                  threads_into="bed")
    d.add("z_motor_mount", z_motor_mount_shape(), material="al6061")
    place(d, "z_motor", nema17(MOTOR_L), Location((0, LS_Y, Z_MF)))
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"z_motor_screw_{i}", "M3", 8, at=(x, LS_Y + y, Z_MF + T_MM), threads_into="z_motor")
    for sx, n in ((-1, "left"), (1, "right")):
        add_screw(d, f"z_mount_bolt_{n}", "M5", 8, at=(sx * UP_X, Y_FACE - 5, Z_MF + 16), direction=(0, 1, 0),
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
        x_out = X_MOTOR_X - 24 if sx < 0 else sx * (RAIL_X + 20)
        # rear edge trimmed to +13.5 so the tool plate passes behind it
        plate = Pos((x_in + x_out) / 2, YB0 - 5.75, Z_PLATE + T_YP / 2) * Box(abs(x_out - x_in), 38.5, T_YP)
        for x in (-10, 10):
            for y in (-10, 10):
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
                plate -= Pos(sx * RAIL_X + x, YB0 + y, Z_PLATE + T_YP - 1.6) * Cylinder(3.0, 3.2)
        x_bolt = sx * (RAIL_X - 25)
        plate -= Pos(x_bolt, YB0, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M5") / 2, T_YP)
        if sx < 0:
            plate -= Pos(X_MOTOR_X, YB0, Z_PLATE + T_YP / 2) * Cylinder(11.5, T_YP)
            for x in (-15.5, 15.5):
                for y in (-15.5, 15.5):
                    plate -= Pos(X_MOTOR_X + x, YB0 + y, Z_PLATE + T_YP / 2) * Cylinder(clearance_hole("M3") / 2, T_YP)
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
        add_screw(d, f"tool_screw_{i}", "M3", 6, at=(x, YB0 + y, Z_TOP + 4), body="xbody", threads_into="x_carriage")
    place(d, "hotend", hotend(), Location((0, YB0 + HOT_OFF, Z_TOP - 4)), body="xbody")
    d.join("hotend", "tool_plate", "clamp")
    # ================= XY motors =================================================
    place(d, "x_motor", nema17(40), Location((X_MOTOR_X, YB0, Z_PLATE)), body="ybody")
    place(d, "x_pulley", gt2_pulley(20), Location((X_MOTOR_X, YB0, Z_PLATE + T_YP + 0.5)), body="ybody")
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 8, at=(X_MOTOR_X + x, YB0 + y, Z_PLATE + T_YP),
                  body="ybody", threads_into="x_motor")
    YM_X, YM_Y = 60.0, FY / 2 + 22.0
    ym_plate = Pos(YM_X, (FY / 2 - 20 + YM_Y + 24) / 2, FZ + 12) * Box(60, YM_Y + 24 - (FY / 2 - 20), 4)
    ym_plate -= Pos(YM_X, YM_Y, FZ + 12) * Cylinder(11.5, 4)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            ym_plate -= Pos(YM_X + x, YM_Y + y, FZ + 12) * Cylinder(clearance_hole("M3") / 2, 4)
    for x in (-20, 20):
        ym_plate -= Pos(YM_X + x, FY / 2 - 10, FZ + 12) * Cylinder(clearance_hole("M5") / 2, 4)
    d.add("y_motor_plate", ym_plate, material="al6061")
    place(d, "y_motor", nema17(48), Location((YM_X, YM_Y, FZ + 10)))
    place(d, "y_pulley", gt2_pulley(20), Location((YM_X, YM_Y, FZ + 14.5)))
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"y_motor_screw_{i}", "M3", 8, at=(YM_X + x, YM_Y + y, FZ + 14), threads_into="y_motor")
    for i, x in enumerate((-20, 20)):
        add_screw(d, f"y_motor_plate_bolt_{i}", "M5", 8, at=(YM_X + x, FY / 2 - 10, FZ + 14),
                  threads_into="frame_top_back", tnut=True)
    d.join("x_pulley", "x_motor", "set_screw")
    d.join("y_pulley", "y_motor", "set_screw")

    # ================= joints ====================================================
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-TY, TY),
                          max_speed=V_XY, max_accel=A_XY, min_drive_margin=MARGIN,
                          drive={"motor": "y_motor", "kind": "belt", "pulley": "y_pulley"}))
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

    # ================= structure =================================================
    # nozzle-point stiffness of the whole gantry moving structure, toolhead at mid-span (worst case);
    # deflection probed at the nozzle tip
    moving = ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate", "hotend"]
    y_plate_fix = [("y_plate_left", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6),
                   ("y_plate_right", lambda f: abs(f.center().Z - Z_PLATE) < 1e-6)]
    # load on the nozzle tip face. (The heater-block underside would be the natural choice, but it is an
    # annulus whose centre lies in the nozzle hole and the harness reports "loaded=0 mesh surfaces" for it.)
    block_face = ("hotend", lambda f: abs(f.center().Z - Z_NOZZLE) < 1e-6)
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
        return 0.2 <= gap <= 2.0, f"nozzle tip is {gap:.2f} mm above the bed surface with the bed at the top"
    d.requirements.append(Requirement("bed surface 0.2-2 mm below the nozzle at the top of Z travel", bed_gap))
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
    d.requirements.append(Requirement("all three joints driven by catalog NEMA 17 motors", lambda dd: (
        all(dd.get(jr(dd, n).drive["motor"]).sku.startswith("NEMA17") and dd.get(jr(dd, n).drive["motor"]).meta["catalog"]
            for n in "xyz"), str({n: dd.get(jr(dd, n).drive["motor"]).sku for n in "xyz"}))))
    d.requirements.append(Requirement("Z lead screw self-locking (efficiency < 0.5)", lambda dd: (
        dd.get("leadscrew").ratings["efficiency"] < 0.5, f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    return d
