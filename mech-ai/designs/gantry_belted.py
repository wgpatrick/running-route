"""XY gantry for a small 3D printer (200 x 200 mm travel) with real belt drives on both axes.

X belt: open GT2 loop in a horizontal plane just behind the X beam (pulley axes vertical), X motor pulley at the
left end, idler on the right Y plate, both ends clamped to a tab that hangs from the tool plate behind the carriage.
Y belt: open GT2 loop in a vertical plane outboard of the right frame rail (pulley axes along X), Y motor at the back,
idler at the front, both ends clamped on top of the right Y plate.

Bodies: world (frame, Y rails, Y motor) -> ybody (X beam and its rail, X motor)
-> xbody (X carriage, tool plate, hotend).
"""
import math

from build123d import Box, Cylinder, Location, Plane, Pos, Rot

from mechloop import AssemblyCase, Design, Joint, LoadCase, ModalCase, Requirement
from mechloop.model import Belt
from mechloop.parts import (Stock, add_corner_bracket, add_screw, clearance_hole, extrusion_2020, gt2_idler, gt2_pulley,
                            mgn12_rail, mgn12h_carriage, nema17, place)

FX, FY, FZ = 300.0, 300.0, 200.0     # frame outer X, Y and top-frame centre height
TRAVEL = 100.0                        # +/- travel on X and Y
RAIL_X = FX / 2 - 10                  # Y rails sit on the left/right top extrusions
PR = 20 * 2.0 / math.pi / 2           # pitch radius of the 20T pulleys and idlers
XB_Y = 28.0                           # X belt: pulley/idler centre line, behind the beam (runs at y = 21.6 and 34.4)
X_IDLER_X = 135.0                     # X idler, on the right Y plate
YB_X = 165.0                          # Y belt plane, outboard of the right frame rail (rail face at x = 150)
YM_Y, YI_Y = 176.0, -125.0            # Y motor pulley (back) and Y idler (front)
MT = 4.0                              # thickness of the Y motor / idler mount plates


def xcyl(r, h):
    return Rot(0, 90, 0) * Cylinder(r, h)


def hotend() -> Stock:
    body = Pos(0, 0, -20) * Cylinder(11, 40) + Pos(0, 0, -47.5) * Box(20, 16, 15) + Pos(0, 0, -57.5) * Cylinder(2, 5)
    return Stock(body, "HOTEND-V6", "V6-style hotend with heater block", 0.12, material="al6061", cost_usd=25.0)


def build() -> Design:
    d = Design("gantry_belted", envelope=(380, 380, 300), base="frame_bot_left")
    # ---- frame --------------------------------------------------------
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
    # corner brackets: post ends to the side rails, and front/back rails to the side rails
    k = 0
    for sx in (-1, 1):
        side = "left" if sx < 0 else "right"
        for sy in (-1, 1):
            post = f"post_{'l' if sx < 0 else 'r'}{'f' if sy < 0 else 'b'}"
            cross = "front" if sy < 0 else "back"
            yi = sy * (FY / 2 - 20)            # inner face of the post / cross rail
            for lvl, zc, zdir in (("top", FZ - 10, -1), ("bot", 20, 1)):
                add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{side}", post,
                                   (sx * RAIL_X, yi, zc), (0, -sy, 0), (0, 0, zdir)); k += 1
                add_corner_bracket(d, f"bracket_{k}", f"frame_{lvl}_{cross}", f"frame_{lvl}_{side}",
                                   (sx * (RAIL_X - 10), yi, FZ if lvl == "top" else 10), (-sx, 0, 0), (0, -sy, 0)); k += 1
    # ---- Y axis: rails on the side extrusions --------------------------
    z_rail = FZ + 10
    z_plate = z_rail + 13            # underside of the Y plates = top of the Y carriages
    T_PLATE = 6.0
    X_MOTOR_X = -(FX / 2 + 27.0)     # X motor rides outboard of the left frame rail
    for sx, n in ((-1, "left"), (1, "right")):
        yr = place(d, f"y_rail_{n}", mgn12_rail(300), Location((sx * RAIL_X, 0, z_rail), (0, 0, 90)))
        for i, (hx, hy, hz) in enumerate(yr.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"y_rail_{n}_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5),
                      threads_into=f"frame_top_{n}", tnut=True)
        place(d, f"y_carriage_{n}", mgn12h_carriage(), Location((sx * RAIL_X, 0, z_rail), (0, 0, 90)),
              body="ybody", guides="y")
        # plate: over the carriage, reaching inboard for the beam bolt; the left one also carries the X motor
        x_in = sx * (RAIL_X - 35)
        x_out = X_MOTOR_X - 24 if sx < 0 else YB_X + 4.5     # right plate reaches out under the Y belt clamp
        # front edge trimmed to y=-13.5 so the tool plate and hotend pass in front of it at the ends of X travel
        plate = Pos((x_in + x_out) / 2, 5.75, z_plate + T_PLATE / 2) * Box(abs(x_out - x_in), 38.5, T_PLATE)
        for x in (-10, 10):
            for y in (-10, 10):   # carriage screws, counterbored flush so the beam can sit on top
                plate -= Pos(sx * RAIL_X + x, y, z_plate + T_PLATE / 2) * Cylinder(clearance_hole("M3") / 2, T_PLATE)
                plate -= Pos(sx * RAIL_X + x, y, z_plate + T_PLATE - 1.6) * Cylinder(3.0, 3.2)
        x_bolt = sx * (RAIL_X - 25)
        plate -= Pos(x_bolt, 0, z_plate + T_PLATE / 2) * Cylinder(clearance_hole("M5") / 2, T_PLATE)
        if sx < 0:
            # motor pad behind the beam line so the X pulley sits on the belt centre line y = XB_Y
            plate += Pos(X_MOTOR_X, (-13.5 + XB_Y + 24) / 2, z_plate + T_PLATE / 2) * Box(48, XB_Y + 24 + 13.5, T_PLATE)
            plate -= Pos(X_MOTOR_X, XB_Y, z_plate + T_PLATE / 2) * Cylinder(11.5, T_PLATE)
            for x in (-15.5, 15.5):
                for y in (-15.5, 15.5):
                    plate -= Pos(X_MOTOR_X + x, XB_Y + y, z_plate + T_PLATE / 2) * Cylinder(clearance_hole("M3") / 2, T_PLATE)
        else:
            # ear carrying the X idler axle (tapped M5)
            plate += Pos(X_IDLER_X, 31, z_plate + T_PLATE / 2) * Box(24, 12, T_PLATE)
        d.add(f"y_plate_{n}", plate, material="al6061", body="ybody")
        for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
            add_screw(d, f"y_plate_{n}_screw_{i}", "M3", 6, at=(sx * RAIL_X + x, y, z_plate + T_PLATE - 3.2),
                      body="ybody", threads_into=f"y_carriage_{n}")
        # beam bolt from below into a T-nut in the beam's bottom slot
        add_screw(d, f"beam_bolt_{n}", "M5", 10, at=(x_bolt, 0, z_plate), direction=(0, 0, 1),
                  body="ybody", threads_into="x_beam", tnut=True)
    # ---- X beam with its rail -------------------------------------------
    z_beam = z_plate + T_PLATE + 10
    place(d, "x_beam", extrusion_2020(FX), Location((0, 0, z_beam)), body="ybody")
    xr = place(d, "x_rail", mgn12_rail(250), Location((0, 0, z_beam + 10)), body="ybody")
    for i, (hx, hy, hz) in enumerate(xr.meta["interfaces"]["mount_holes_m3"][::2]):
        add_screw(d, f"x_rail_screw_{i}", "M3", 8, at=(hx, hy, hz + 3.5), body="ybody",
                  threads_into="x_beam", tnut=True)
    place(d, "x_carriage", mgn12h_carriage(), Location((0, 0, z_beam + 10)), body="xbody", guides="x")
    # ---- tool plate and hotend (hung close to the beam to keep it inside the frame) ---
    z_top = z_beam + 10 + 13
    HOT_Y = -31.0
    RIB = 8.0
    Z_XB = z_plate + T_PLATE + 0.5 + 10.5          # X belt centre height (motor pulley belt_center)
    XA_Y = XB_Y - PR                               # near (anchored) run of the X belt
    TAB_Y1 = XA_Y - 0.7 - 0.03                     # tab back face = belt tooth side
    top = Pos(0, (-20 + TAB_Y1) / 2, z_top + 2) * Box(46, TAB_Y1 + 20, 4)
    # belt tab: drops behind the carriage (y > 13.5) and the beam (y > 10) to the belt line; clears the Y plates below
    TAB_Z0 = z_plate + T_PLATE + 1.5
    top += Pos(0, (14 + TAB_Y1) / 2, (TAB_Z0 + z_top) / 2) * Box(40, TAB_Y1 - 14, z_top - TAB_Z0)
    front = Pos(0, -18, z_top - 20) * Box(46, 4, 48)
    tool_plate = top + front
    # L-shaped ribs over the top and down the front (iteration 5: nozzle stiffness was 40 N/mm without them)
    for sx in (-1, 1):
        tool_plate += Pos(sx * 20, -5.25, z_top + 4 + RIB / 2) * Box(6, 45.5 - 8 + RIB, RIB)
        tool_plate += Pos(sx * 20, -20 - RIB / 2, z_top - 20 + RIB / 2) * Box(6, RIB, 48 + RIB)
    for x in (-10, 10):
        for y in (-10, 10):
            tool_plate -= Pos(x, y, z_top + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("tool_plate", tool_plate, material="petg", body="xbody")
    for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
        add_screw(d, f"tool_screw_{i}", "M3", 6, at=(x, y, z_top + 4), body="xbody", threads_into="x_carriage")
    # X belt clamp bar: pockets grip the last 14 mm of each belt end against the tab
    XC_Y1 = TAB_Y1 + 4.6
    xclamp = Pos(0, (TAB_Y1 + XC_Y1) / 2, Z_XB + 1) * Box(40, XC_Y1 - TAB_Y1, 20)
    for sx in (-1, 1):
        xclamp -= Pos(sx * 13, TAB_Y1 + 0.75, Z_XB) * Box(14, 1.5, 7.2)
    X_CLAMP_SCREWS = [(-13, Z_XB + 7.5), (13, Z_XB + 7.5), (0, Z_XB - 5.75)]   # all clear of the far belt run for the key
    for x, z in X_CLAMP_SCREWS:
        xclamp -= Pos(x, (TAB_Y1 + XC_Y1) / 2, z) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, XC_Y1 - TAB_Y1)
    d.add("x_belt_clamp", xclamp, material="al6061", body="xbody")
    for i, (x, z) in enumerate(X_CLAMP_SCREWS):
        add_screw(d, f"x_belt_clamp_screw_{i}", "M3", 10, at=(x, XC_Y1, z), direction=(0, -1, 0), body="xbody",
                  threads_into="tool_plate")
    d.bom_extra("HEATSET-M3", 3, 0.1)
    place(d, "hotend", hotend(), Location((0, HOT_Y, z_top - 4)), body="xbody")
    d.join("hotend", "tool_plate", "groove_clamp")   # clamp block not modelled yet
    d.bom_extra("HOTEND-CLAMP", 1, 2.0)
    # ---- motors -----------------------------------------------------------
    place(d, "x_motor", nema17(40), Location((X_MOTOR_X, XB_Y, z_plate)), body="ybody")
    place(d, "x_pulley", gt2_pulley(20), Location((X_MOTOR_X, XB_Y, z_plate + T_PLATE + 0.5)), body="ybody")
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 8, at=(X_MOTOR_X + x, XB_Y + y, z_plate + T_PLATE),
                  body="ybody", threads_into="x_motor")
    d.join("x_pulley", "x_motor", "set_screw")
    # X idler on the right Y plate: spacer + M5 axle bolt tapped into the plate ear
    z_xi = Z_XB - 4.25
    sp = Pos(X_IDLER_X, XB_Y, (z_plate + T_PLATE + z_xi) / 2) * (
        Cylinder(4.0, z_xi - z_plate - T_PLATE) - Cylinder(2.75, z_xi - z_plate - T_PLATE))
    d.add("x_idler_spacer", sp, material="al6061", body="ybody")
    place(d, "x_idler", gt2_idler(20), Location((X_IDLER_X, XB_Y, z_xi)), body="ybody")
    add_screw(d, "x_idler_bolt", "M5", 20, at=(X_IDLER_X, XB_Y, z_xi + 8.5), body="ybody", threads_into="y_plate_right")
    d.join("x_idler", "x_idler_bolt", "axle")
    d.join("x_idler_spacer", "x_idler_bolt", "axle")
    # ---- Y drive: vertical belt plane outboard of the right rail ---------------
    Z_YA = z_plate + T_PLATE + 0.7          # upper (anchored) run lies on top of the right Y plate
    Z_YC = Z_YA - PR                        # pulley / idler axis height; lower run passes under the plate
    xf = FX / 2                             # outer face of the right frame rail
    # motor mount: strip bolted along the rail's outer slot + a tall ear behind the frame for the motor face
    mm = (Pos(xf + MT / 2, 127.5, FZ) * Box(MT, 45, 20)
          + Pos(xf + MT / 2, (150 + YM_Y + 23) / 2, (FZ - 10 + Z_YC + 23) / 2) * Box(MT, YM_Y + 23 - 150, Z_YC + 23 - FZ + 10))
    mm -= Pos(xf + MT / 2, YM_Y, Z_YC) * xcyl(11.5, MT)
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            mm -= Pos(xf + MT / 2, YM_Y + y, Z_YC + z) * xcyl(clearance_hole("M3") / 2, MT)
    Y_MOUNT_BOLTS = (113.0, 127.0, 141.0)
    for y in Y_MOUNT_BOLTS:
        mm -= Pos(xf + MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_motor_mount", mm, material="al6061")
    place(d, "y_motor", nema17(48), Location(Plane(origin=(xf, YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    place(d, "y_pulley", gt2_pulley(20),
          Location(Plane(origin=(YB_X - 10.5, YM_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    k = 0
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            add_screw(d, f"y_motor_screw_{k}", "M3", 8, at=(xf + MT, YM_Y + y, Z_YC + z), direction=(-1, 0, 0),
                      threads_into="y_motor"); k += 1
    for i, y in enumerate(Y_MOUNT_BOLTS):
        add_screw(d, f"y_motor_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    d.join("y_pulley", "y_motor", "set_screw")
    # idler mount at the front (kept in front of the Y carriage's sweep, which reaches y = -108.7)
    im = Pos(xf + MT / 2, -126.5, (FZ - 10 + Z_YC + 9) / 2) * Box(MT, 31, Z_YC + 9 - FZ + 10)
    for y in (-134.0, -119.0):
        im -= Pos(xf + MT / 2, y, FZ) * xcyl(clearance_hole("M5") / 2, MT)
    d.add("y_idler_mount", im, material="al6061")
    for i, y in enumerate((-134.0, -119.0)):
        add_screw(d, f"y_idler_mount_bolt_{i}", "M5", 8, at=(xf + MT, y, FZ), direction=(-1, 0, 0),
                  threads_into="frame_top_right", tnut=True)
    x_yi = YB_X - 4.25
    d.add("y_idler_spacer", Pos((xf + MT + x_yi) / 2, YI_Y, Z_YC) * (xcyl(4.0, x_yi - xf - MT) - xcyl(2.75, x_yi - xf - MT)),
          material="al6061")
    place(d, "y_idler", gt2_idler(20), Location(Plane(origin=(x_yi, YI_Y, Z_YC), x_dir=(0, 1, 0), z_dir=(1, 0, 0))))
    add_screw(d, "y_idler_bolt", "M5", 20, at=(x_yi + 8.5, YI_Y, Z_YC), direction=(-1, 0, 0), threads_into="y_idler_mount")
    d.join("y_idler", "y_idler_bolt", "axle")
    d.join("y_idler_spacer", "y_idler_bolt", "axle")
    # Y belt clamp on top of the right Y plate: grooved bar, belt ends enter from front and back
    YA0, YA1 = 5.75 - 14, 5.75 + 14
    zt = z_plate + T_PLATE
    yclamp = Pos((156 + YB_X + 4.5) / 2, 5.75, zt + 2) * Box(YB_X + 4.5 - 156, YA1 - YA0, 4)
    for sy in (-1, 1):
        yclamp -= Pos(YB_X, 5.75 + sy * 9, zt + 0.75) * Box(6.4, 10, 1.5)
    Y_CLAMP_SCREWS = [(YB_X, 5.75), (158.5, 5.75 - 9), (158.5, 5.75 + 9)]
    for x, y in Y_CLAMP_SCREWS:
        yclamp -= Pos(x, y, zt + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("y_belt_clamp", yclamp, material="al6061", body="ybody")
    for i, (x, y) in enumerate(Y_CLAMP_SCREWS):
        add_screw(d, f"y_belt_clamp_screw_{i}", "M3", 8, at=(x, y, zt + 4), body="ybody", threads_into="y_plate_right")
    # ---- belts ---------------------------------------------------------------
    d.belts.append(Belt("x_belt", [("anchor", "xbody", (-20.0, XA_Y, Z_XB)), ("pulley", "x_pulley", "cw"),
                                   ("pulley", "x_idler", "cw"), ("anchor", "xbody", (20.0, XA_Y, Z_XB))],
                        axis=(0, 0, 1)))
    d.belts.append(Belt("y_belt", [("anchor", "ybody", (YB_X, YA0, Z_YA)), ("pulley", "y_idler", "ccw"),
                                   ("pulley", "y_pulley", "ccw"), ("anchor", "ybody", (YB_X, YA1, Z_YA))],
                        axis=(1, 0, 0)))
    d.bom_extra("GT2-BELT-6MM-OPEN-1M", 2, 3.0)
    # ---- joints -------------------------------------------------------------
    # Y range is offset so the hotend (31 mm in front of the beam) stays inside the frame opening
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-86.0, 114.0),
                          max_speed=300, max_accel=3000,
                          drive={"motor": "y_motor", "kind": "belt", "pulley": "y_pulley"}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TRAVEL, TRAVEL),
                          max_speed=300, max_accel=5000,
                          drive={"motor": "x_motor", "kind": "belt", "pulley": "x_pulley"}))
    # ---- motion program: outline a 150 mm square, then cross it diagonally (a print perimeter + travel)
    d.program = [{"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": -75, "y": 75}}, {"to": {"x": -75, "y": -75}}, {"to": {"x": 75, "y": 75}},
                 {"to": {"x": 0, "y": 0}}]
    d.tool_point = ("xbody", (0.0, HOT_Y, z_top - 64))   # nozzle tip
    # ---- structural check on the printed tool plate ---------------------------
    d.loadcases.append(LoadCase(
        "toolhead_accel", "tool_plate",
        fixed=lambda f: abs(f.center().Z - z_top) < 1e-6 and f.area > 500,
        loaded=lambda f: abs(f.center().Y + 20) < 1e-6,
        force=(0.3 * 5.0 * 3, 0.0, -0.3 * 9.81 * 3),   # 0.3 kg toolhead, 5 m/s^2, x3 dynamic factor
        min_fos=4.0, max_deflection=0.05))
    # ---- stiffness of the whole moving structure at the tool, toolhead at mid-span (worst case)
    d.assemblycases.append(AssemblyCase(
        "tool_stiffness", ["y_plate_left", "y_plate_right", "x_beam", "x_rail", "x_carriage", "tool_plate"],
        fixed=[("y_plate_left", lambda f: abs(f.center().Z - z_plate) < 1e-6),
               ("y_plate_right", lambda f: abs(f.center().Z - z_plate) < 1e-6)],
        loaded=("tool_plate", lambda f: abs(f.center().Y + 20) < 1e-6),
        force=(0.0, 3.0, -2.0),              # 0.2 kg toolhead at 5 m/s^2 with a 3x dynamic factor, plus its weight
        probe=(0.0, -20.0, z_top - 44.0), max_deflection=0.02, min_fos=5.0))
    # ---- the X beam must not resonate near the motion bandwidth
    d.modalcases.append(ModalCase(
        "x_beam_mode", "x_beam",
        fixed=lambda f: abs(abs(f.center().X) - FX / 2) < 1e-6, min_frequency_hz=150.0))
    d.requirements.append(Requirement("drive margin >= 5x on both axes (friction and belt losses unmodelled)", lambda dd, m: (
        all(v["margin"] >= 5 for v in m["motion"]["drives"].values()),
        str({k: v["margin"] for k, v in m["motion"]["drives"].items()}))))
    d.requirements.append(Requirement("both belts routed: constant length, clear of parts", lambda dd, m: (
        all(b in m["motion"].get("belts", {}) and m["motion"]["belts"][b]["clear_of_parts"]
            and m["motion"]["belts"][b]["length_change_over_travel_mm"] <= 0.3 for b in ("x_belt", "y_belt")),
        str(m["motion"].get("belts")))))
    d.requirements.append(Requirement("X and Y travel >= 200 mm", lambda dd: (
        all(j.range[1] - j.range[0] >= 200 for j in dd.joints), str({j.name: j.range for j in dd.joints}))))
    return d
