"""XY gantry for a small 3D printer (200 x 200 mm travel), built from catalog parts.

Bodies: world (frame, Y rails, Y motor) -> ybody (X beam and its rail, X motor)
-> xbody (X carriage, tool plate, hotend).
"""
from build123d import Box, Cylinder, Location, Pos, Rot

from mechloop import Design, Joint, LoadCase, Requirement
from mechloop.parts import (Stock, add_corner_bracket, add_screw, clearance_hole, extrusion_2020, gt2_pulley,
                            mgn12_rail, mgn12h_carriage, nema17, place)

FX, FY, FZ = 300.0, 300.0, 200.0     # frame outer X, Y and top-frame centre height
TRAVEL = 100.0                        # +/- travel on X and Y
RAIL_X = FX / 2 - 10                  # Y rails sit on the left/right top extrusions


def hotend() -> Stock:
    body = Pos(0, 0, -20) * Cylinder(11, 40) + Pos(0, 0, -47.5) * Box(20, 16, 15) + Pos(0, 0, -57.5) * Cylinder(2, 5)
    return Stock(body, "HOTEND-V6", "V6-style hotend with heater block", 0.12, material="al6061", cost_usd=25.0)


def build() -> Design:
    d = Design("gantry", envelope=(380, 380, 300), base="frame_bot_left")
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
        x_out = X_MOTOR_X - 24 if sx < 0 else sx * (RAIL_X + 20)
        # front edge trimmed to y=-13.5 so the tool plate and hotend pass in front of it at the ends of X travel
        plate = Pos((x_in + x_out) / 2, 5.75, z_plate + T_PLATE / 2) * Box(abs(x_out - x_in), 38.5, T_PLATE)
        for x in (-10, 10):
            for y in (-10, 10):   # carriage screws, counterbored flush so the beam can sit on top
                plate -= Pos(sx * RAIL_X + x, y, z_plate + T_PLATE / 2) * Cylinder(clearance_hole("M3") / 2, T_PLATE)
                plate -= Pos(sx * RAIL_X + x, y, z_plate + T_PLATE - 1.6) * Cylinder(3.0, 3.2)
        x_bolt = sx * (RAIL_X - 25)
        plate -= Pos(x_bolt, 0, z_plate + T_PLATE / 2) * Cylinder(clearance_hole("M5") / 2, T_PLATE)
        if sx < 0:
            plate -= Pos(X_MOTOR_X, 0, z_plate + T_PLATE / 2) * Cylinder(11.5, T_PLATE)
            for x in (-15.5, 15.5):
                for y in (-15.5, 15.5):
                    plate -= Pos(X_MOTOR_X + x, y, z_plate + T_PLATE / 2) * Cylinder(clearance_hole("M3") / 2, T_PLATE)
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
    top = Pos(0, -3.25, z_top + 2) * Box(46, 33.5, 4)
    front = Pos(0, -18, z_top - 20) * Box(46, 4, 48)
    tool_plate = top + front
    for x in (-10, 10):
        for y in (-10, 10):
            tool_plate -= Pos(x, y, z_top + 2) * Cylinder(clearance_hole("M3") / 2, 4)
    d.add("tool_plate", tool_plate, material="petg", body="xbody")
    for i, (x, y) in enumerate([(-10, -10), (-10, 10), (10, -10), (10, 10)]):
        add_screw(d, f"tool_screw_{i}", "M3", 6, at=(x, y, z_top + 4), body="xbody", threads_into="x_carriage")
    place(d, "hotend", hotend(), Location((0, HOT_Y, z_top - 4)), body="xbody")
    d.join("hotend", "tool_plate", "groove_clamp")   # clamp block not modelled yet
    d.bom_extra("HOTEND-CLAMP", 1, 2.0)
    # ---- motors -----------------------------------------------------------
    place(d, "x_motor", nema17(40), Location((X_MOTOR_X, 0, z_plate)), body="ybody")
    place(d, "x_pulley", gt2_pulley(20), Location((X_MOTOR_X, 0, z_plate + T_PLATE + 0.5)), body="ybody")
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"x_motor_screw_{i}", "M3", 8, at=(X_MOTOR_X + x, y, z_plate + T_PLATE),
                  body="ybody", threads_into="x_motor")
    # Y motor hangs behind the back rail from a plate bolted to the top of the frame
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
    # ---- joints -------------------------------------------------------------
    # Y range is offset so the hotend (31 mm in front of the beam) stays inside the frame opening
    d.joints.append(Joint("y", "slide", "world", "ybody", (0, 1, 0), range=(-86.0, 114.0),
                          max_speed=300, max_accel=3000,
                          drive={"motor": "y_motor", "kind": "belt", "pulley_teeth": 20}))
    d.joints.append(Joint("x", "slide", "ybody", "xbody", (1, 0, 0), range=(-TRAVEL, TRAVEL),
                          max_speed=300, max_accel=5000,
                          drive={"motor": "x_motor", "kind": "belt", "pulley_teeth": 20}))
    # ---- structural check on the printed tool plate ---------------------------
    d.loadcases.append(LoadCase(
        "toolhead_accel", "tool_plate",
        fixed=lambda f: abs(f.center().Z - z_top) < 1e-6 and f.area > 500,
        loaded=lambda f: abs(f.center().Y + 20) < 1e-6,
        force=(0.3 * 5.0 * 3, 0.0, -0.3 * 9.81 * 3),   # 0.3 kg toolhead, 5 m/s^2, x3 dynamic factor
        min_fos=4.0, max_deflection=0.05))
    d.requirements.append(Requirement("X and Y travel >= 200 mm", lambda dd: (
        all(j.range[1] - j.range[0] >= 200 for j in dd.joints), str({j.name: j.range for j in dd.joints}))))
    return d
