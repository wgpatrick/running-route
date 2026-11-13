"""Z-axis bed lift for a small 3D printer: 220 x 220 mm bed, 150 mm travel.

Layout (X = width, Y = depth with the front at -Y, Z = up):
- Base: U of 2020 extrusion (two side beams along Y, one rear cross beam along X).
- Two vertical 2020 uprights stand on the cross beam and are tied at the top by a 2020
  beam; MGN12 rails on their front faces, two MGN12H carriages per rail.
- One NEMA 17 hangs under an aluminium angle between the uprights and turns a T8 lead
  screw through a catalog flexible coupler; the screw's top end runs in a 608 bearing
  held in a small plate on the top beam.
- Body "bed": four carriages, a one-piece aluminium carrier (back plate, two L-section
  arms, forked nut tab), the T8 nut, four stainless standoffs and the bed plate.

Choices:
- Carrier in 6061 aluminium, not PETG: the arms cantilever ~220 mm and must stay within
  0.3 mm at the bed edge; PETG is ~33x less stiff, creeps under sustained load and sits
  under a heated bed. FEA treats the carrier as one monolithic piece (CNC'd or welded).
- T8 lead 2 mm (not 8): self-locking, so the bed does not drop when the motor is
  unpowered, and the drive force margin is large. 15 mm/s needs 450 rpm.
- Bed mounting: M3 screws down through the bed and 8 mm stainless standoffs (air gap and
  a poorer heat path than aluminium) into M3 threads tapped 5 mm deep in the 6 mm arm
  flanges. The catalog only has cap screws, so the four heads stand 3 mm proud of the
  bed corners; a real build would countersink them and use springs/levelling nuts.
- The 1.5 kg payload is carried as extra mass on the bed plate (mass_kg override).
"""
from build123d import Box, CenterOf, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from mechloop import Design, Joint, LoadCase, Requirement
from mechloop.model import AssemblyCase
from mechloop.parts import (add_corner_bracket, add_screw, bearing, clearance_hole, extrusion_2020,
                            leadscrew_nut_t8, leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place,
                            shaft_coupler, tap_drill)

TRAVEL = 150.0
PAYLOAD_KG = 1.5
BED = 220.0
T_BED = 3.0
UP_X = 90.0           # upright / rail centre, +/- X
UP_Y = 118.0          # upright centre Y (uprights at the back)
Z_TOP = 330.0         # top of the uprights
Y_FACE = UP_Y - 10    # front face of the uprights = rail base
Y_CAR = Y_FACE - 13   # carriage top face = carrier back-plate rear face
T_PLATE = 6.0         # carrier back plate thickness
Y_PF = Y_CAR - T_PLATE  # carrier back-plate front face
RAIL_L, RAIL_ZC = 250.0, 201.0
ZC = (99.0, 153.0)    # carriage centre heights at home (two per rail, 54 mm apart)
ZP0, ZP1 = ZC[0] - 23, ZC[1] + 23   # back plate bottom / top
Z_ARM = 125.0         # top of the arms
T_WEB, T_FL = 5.0, 6.0  # arm web and flange thickness
FL_IN = 72.0          # arm flange inner |x|
H_STANDOFF = 8.0
Z_BED = Z_ARM + H_STANDOFF          # bed underside at home
BED_Y1 = Y_PF - 2.0                 # bed rear edge, 2 mm in front of the back plate
BED_Y0 = BED_Y1 - BED               # bed front edge
BED_POINTS = [(sx * 79.0, y) for sx in (-1, 1) for y in (-118.0, 72.0)]
LS_Y = 141.0          # lead screw / motor axis Y (behind the uprights' centre line)
MOTOR_L = 34
Z_MF = 22.0 + MOTOR_L  # motor mounting face = underside of the motor mount plate
T_MM = 5.0            # motor mount thickness
Z_TAB = 104.0         # underside of the nut tab at home
T_TAB = 6.0
NUT_HOLES = [(8.0, 0.0), (-8.0, 0.0), (0.0, -8.0)]   # the +Y hole is lost to the fork slot
Z_BEAM = 310.0        # top beam centre height
T_BRG = 8.0           # bearing plate thickness


def carrier_shape(carriage_holes):
    c = Pos(0, (Y_PF + Y_CAR) / 2, (ZP0 + ZP1) / 2) * Box(208, T_PLATE, ZP1 - ZP0)
    for sx in (-1, 1):
        # arm web: on-edge plate, 49 mm deep at the root tapering to 12 mm at the tip
        prof = Plane.YZ * Polygon((Y_CAR, ZP0), (Y_CAR, Z_ARM), (BED_Y0, Z_ARM), (BED_Y0, Z_ARM - 12), align=None)
        c += Pos(sx * UP_X - T_WEB / 2, 0, 0) * extrude(prof, T_WEB)
        # top flange (inboard) that the bed standoffs sit on
        x0, x1 = sorted((sx * FL_IN, sx * (UP_X + T_WEB / 2)))
        c += Pos((x0 + x1) / 2, (BED_Y0 + Y_PF) / 2, Z_ARM - T_FL / 2) * Box(x1 - x0, Y_PF - BED_Y0, T_FL)
    # nut tab reaching back between the uprights; forked (slot open to the back) so the
    # carrier can be drawn forward off the lead screw and nut
    y1 = LS_Y + 13
    c += Pos(0, (Y_PF + 3 + y1) / 2, Z_TAB + T_TAB / 2) * Box(26, y1 - Y_PF - 3, T_TAB)
    c -= Pos(0, LS_Y, Z_TAB + T_TAB / 2) * Cylinder(5.4, T_TAB)          # nut barrel
    c -= Pos(0, (LS_Y + y1) / 2, Z_TAB + T_TAB / 2) * Box(10.8, y1 - LS_Y, T_TAB)
    for dx, dy in NUT_HOLES:                                             # tapped M3
        c -= Pos(dx, LS_Y + dy, Z_TAB + T_TAB / 2) * Cylinder(tap_drill("M3") / 2, T_TAB)
    for hx, hy, hz in carriage_holes:
        c -= Pos(hx, (Y_PF + Y_CAR) / 2, hz) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, T_PLATE)
    for x, y in BED_POINTS:                                              # tapped M3
        c -= Pos(x, y, Z_ARM - T_FL / 2) * Cylinder(tap_drill("M3") / 2, T_FL)
    return c


def motor_mount_shape():
    y_back = LS_Y + 22
    m = Pos(0, (Y_FACE - 5 + y_back) / 2, Z_MF + T_MM / 2) * Box(160, y_back - (Y_FACE - 5), T_MM)
    m += Pos(0, Y_FACE - 2.5, Z_MF + 9) * Box(200, 5, 18)        # flange up the front of both uprights
    # pilot as a U-slot open to the back so the mount can be drawn forward off the motor
    m -= Pos(0, LS_Y, Z_MF + T_MM / 2) * Cylinder(11.5, T_MM)
    m -= Pos(0, (LS_Y + y_back) / 2, Z_MF + T_MM / 2) * Box(23, y_back - LS_Y, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(x, LS_Y + y, Z_MF + T_MM / 2) * Cylinder(clearance_hole("M3") / 2, T_MM)
    for sx in (-1, 1):
        m -= Pos(sx * UP_X, Y_FACE - 2.5, Z_MF + 9) * Rot(90, 0, 0) * Cylinder(clearance_hole("M5") / 2, 5)
    return m


def bearing_plate_shape():
    z0 = Z_BEAM + 10
    y1 = LS_Y + 16
    p = Pos(0, (Y_FACE + y1) / 2, z0 + T_BRG / 2) * Box(40, y1 - Y_FACE, T_BRG)
    p -= Pos(0, LS_Y, z0 + T_BRG / 2) * Cylinder(11.0, T_BRG)            # 608 bearing seat (press fit)
    for x in (-12, 12):                                                  # M5, heads counterbored 5 mm
        p -= Pos(x, UP_Y, z0 + T_BRG / 2) * Cylinder(clearance_hole("M5") / 2, T_BRG)
        p -= Pos(x, UP_Y, z0 + 3 + 2.5) * Cylinder(4.75, 5)
    return p


def build() -> Design:
    d = Design("z_axis_v2", envelope=(300, 300, 330), base="base_cross")
    # ---- base, uprights, top beam -----------------------------------------
    place(d, "base_cross", extrusion_2020(200), Location((0, UP_Y, 10)))
    place(d, "top_beam", extrusion_2020(160), Location((0, UP_Y, Z_BEAM)))
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"base_{n}", extrusion_2020(280), Location((sx * 110, 20, 10), (0, 0, 90)))
        place(d, f"upright_{n}", extrusion_2020(Z_TOP - 20), Location((sx * UP_X, UP_Y, (Z_TOP + 20) / 2), (0, 90, 0)))
        add_corner_bracket(d, f"brkt_cross_front_{n}", "base_cross", f"base_{n}",
                           (sx * 100, UP_Y - 10, 10), (-sx, 0, 0), (0, -1, 0))
        add_corner_bracket(d, f"brkt_cross_back_{n}", "base_cross", f"base_{n}",
                           (sx * 100, UP_Y + 10, 10), (-sx, 0, 0), (0, 1, 0))
        add_corner_bracket(d, f"brkt_up_in_{n}", "base_cross", f"upright_{n}",
                           (sx * 80, UP_Y, 20), (-sx, 0, 0), (0, 0, 1))
        add_corner_bracket(d, f"brkt_up_out_{n}", f"base_{n}", f"upright_{n}",
                           (sx * 100, UP_Y, 20), (sx, 0, 0), (0, 0, 1))
        add_corner_bracket(d, f"brkt_top_{n}", "top_beam", f"upright_{n}",
                           (sx * 80, UP_Y, Z_BEAM - 10), (-sx, 0, 0), (0, 0, -1))
    # ---- rails and carriages ------------------------------------------------
    carriage_holes = []
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"rail_{n}", mgn12_rail(RAIL_L),
                     Location(Plane(origin=(sx * UP_X, Y_FACE, RAIL_ZC), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
        for i, (hx, hy, hz) in enumerate(rail.meta["interfaces"]["mount_holes_m3"]):   # every hole
            add_screw(d, f"rail_{n}_screw_{i}", "M3", 8, at=(hx, hy - 3.5, hz), direction=(0, 1, 0),
                      threads_into=f"upright_{n}", tnut=True)
        for k, zc in enumerate(ZC):
            car = place(d, f"carriage_{n}_{k}", mgn12h_carriage(),
                        Location(Plane(origin=(sx * UP_X, Y_FACE, zc), x_dir=(0, 0, 1), z_dir=(0, -1, 0))),
                        body="bed", guides="z")
            holes = car.meta["interfaces"]["mount_holes_m3"]
            carriage_holes += holes
            for i, (hx, hy, hz) in enumerate(holes):
                add_screw(d, f"carriage_{n}_{k}_screw_{i}", "M3", 10, at=(hx, hy - T_PLATE, hz), direction=(0, 1, 0),
                          body="bed", threads_into=f"carriage_{n}_{k}")
    # ---- carrier, nut, bed ----------------------------------------------------
    d.add("carrier", carrier_shape(carriage_holes), material="al6061", body="bed")
    # nut: flange on top of the tab, barrel hanging down through it; M3 x 10 through the
    # flange holes (not modelled in the catalog nut) into 6 mm of thread in the tab
    z_nut_top = Z_TAB + T_TAB + 3.5
    place(d, "z_nut", leadscrew_nut_t8(), Location((0, LS_Y, z_nut_top), (180, 0, 0)), body="bed", guides="z")
    for i, (dx, dy) in enumerate(NUT_HOLES):
        add_screw(d, f"nut_screw_{i}", "M3", 10, at=(dx, LS_Y + dy, z_nut_top), body="bed", threads_into="carrier",
                  clamps=("z_nut", "carrier"))
        d.allow_overlap(f"nut_screw_{i}", "z_nut", max_volume=30.0)      # passes through the flange hole
        d.join(f"nut_screw_{i}", "z_nut", "through_bolt")
    bed_shape = Pos(0, (BED_Y0 + BED_Y1) / 2, Z_BED + T_BED / 2) * Box(BED, BED, T_BED)
    for x, y in BED_POINTS:
        bed_shape -= Pos(x, y, Z_BED + T_BED / 2) * Cylinder(clearance_hole("M3") / 2, T_BED)
    bed_own = bed_shape.volume * 2700e-9
    d.add("bed", bed_shape, material="al6061", body="bed", mass_kg=bed_own + PAYLOAD_KG)   # plate + 1.5 kg payload
    standoffs = []
    for i, (x, y) in enumerate(BED_POINTS):
        so = Pos(x, y, Z_ARM + H_STANDOFF / 2) * (Cylinder(4.0, H_STANDOFF) - Cylinder(clearance_hole("M3") / 2, H_STANDOFF))
        d.add(f"standoff_{i}", so, material="stainless304", body="bed")
        standoffs.append(f"standoff_{i}")
        # down through bed and standoff, 5 mm of thread in the arm flange
        add_screw(d, f"bed_screw_{i}", "M3", 16, at=(x, y, Z_BED + T_BED), body="bed", threads_into="carrier",
                  clamps=("bed", f"standoff_{i}", "carrier"))
        d.join(f"bed_screw_{i}", f"standoff_{i}", "clamped")
    # ---- drive ------------------------------------------------------------------
    d.add("motor_mount", motor_mount_shape(), material="al6061")
    place(d, "z_motor", nema17(MOTOR_L), Location((0, LS_Y, Z_MF)))
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"motor_screw_{i}", "M3", 8, at=(x, LS_Y + y, Z_MF + T_MM), threads_into="z_motor")
    for sx, n in ((-1, "left"), (1, "right")):
        add_screw(d, f"mount_bolt_{n}", "M5", 8, at=(sx * UP_X, Y_FACE - 5, Z_MF + 9), direction=(0, 1, 0),
                  threads_into=f"upright_{n}", tnut=True)
    z_tip = Z_MF + 24                                  # motor shaft tip
    place(d, "coupler", shaft_coupler(5.0, 8.0), Location((0, LS_Y, z_tip - 12.5)))
    z_brg = Z_BEAM + 10 + T_BRG / 2                    # bearing centre
    z_ls0 = z_tip + 0.5
    place(d, "leadscrew", leadscrew_t8(z_brg + 3.5 - z_ls0, lead=2.0), Location((0, LS_Y, z_ls0)))
    d.join("coupler", "z_motor", "clamp")
    d.join("leadscrew", "coupler", "clamp")
    # top support: 608 bearing in a plate on the top beam
    d.add("bearing_plate", bearing_plate_shape(), material="al6061")
    place(d, "top_bearing", bearing("608"), Location((0, LS_Y, z_brg)))
    d.join("top_bearing", "bearing_plate", "press")
    for i, x in enumerate((-12, 12)):
        add_screw(d, f"bearing_plate_bolt_{i}", "M5", 8, at=(x, UP_Y, Z_BEAM + 13), threads_into="top_beam", tnut=True)
    # ---- motion -------------------------------------------------------------------
    d.joints.append(Joint("z", "slide", "world", "bed", (0, 0, 1), range=(0.0, TRAVEL),
                          max_speed=15.0, max_accel=300.0, min_drive_margin=3.0,
                          drive={"motor": "z_motor", "kind": "leadscrew", "screw": "leadscrew", "nut": "z_nut",
                                 "coupler": "coupler"}))
    d.program = [{"to": {"z": TRAVEL}}, {"to": {"z": 0.0}}]
    d.tool_point = ("bed", (0.0, (BED_Y0 + BED_Y1) / 2, Z_BED + T_BED))
    # ---- structure -------------------------------------------------------------------
    w_bed = (bed_own + PAYLOAD_KG) * (9.81 + 0.3)      # payload + bed plate, gravity + 300 mm/s^2
    # fixed = the 16 carriage bolt holes through the back plate
    bolt_holes = lambda f: f.geom_type.name == "CYLINDER" and abs(f.center(CenterOf.MASS).Y - (Y_PF + Y_CAR) / 2) < 0.1 \
        and abs(f.center(CenterOf.MASS).X) > 70 and f.area < 80
    d.loadcases.append(LoadCase(
        "payload_on_bed", "carrier", fixed=bolt_holes,
        loaded=lambda f: abs(f.center().Z - Z_ARM) < 1e-6 and f.area > 1000,     # arm tops (standoff seats)
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(
        "nut_thrust", "carrier", fixed=bolt_holes,
        loaded=lambda f: abs(f.center().Z - (Z_TAB + T_TAB)) < 1e-6 and f.area > 300,   # nut seat on the tab
        force=(0.0, 0.0, 2.0 * 3.2 * 9.81), min_fos=3.0, max_deflection=0.3))    # 2x the ~3.2 kg moving weight
    # bed-edge deflection through the real load path: bed -> standoffs -> arms -> carriage bolts
    d.assemblycases.append(AssemblyCase(
        "bed_edge", ["carrier", "bed"] + standoffs, fixed=[("carrier", bolt_holes)],
        loaded=("bed", lambda f: abs(f.center().Z - (Z_BED + T_BED)) < 1e-6 and f.area > 10000),
        force=(0.0, 0.0, -w_bed), probe=(0.0, BED_Y0, Z_BED + T_BED), max_deflection=0.3, min_fos=3.0))
    # ---- requirements -------------------------------------------------------------------
    d.requirements.append(Requirement("Z travel >= 150 mm", lambda dd: (
        (j := dd.joints[0]).range[1] - j.range[0] >= 150.0, str(j.range))))

    def bed_size(dd):
        s = dd.get("bed").shape.bounding_box().size
        return (abs(s.X - 220) < 0.01 and abs(s.Y - 220) < 0.01 and abs(s.Z - 3) < 0.01,
                f"{s.X:.1f} x {s.Y:.1f} x {s.Z:.1f} mm")
    d.requirements.append(Requirement("bed plate is 220 x 220 x 3 mm", bed_size))
    d.requirements.append(Requirement("bed carries the 1.5 kg payload as mass", lambda dd: (
        (m := dd.get("bed").mass()) >= dd.get("bed").shape.volume * 2700e-9 + 1.5 - 1e-9, f"bed + payload {m:.3f} kg")))
    d.requirements.append(Requirement("speed 15 mm/s and accel 300 mm/s^2 declared on the Z joint", lambda dd: (
        dd.joints[0].max_speed >= 15 and dd.joints[0].max_accel >= 300,
        f"{dd.joints[0].max_speed} mm/s, {dd.joints[0].max_accel} mm/s^2")))

    def hold_margin(dd, metrics):
        z = metrics["motion"]["drives"]["z"]
        return (z["available"] >= 3.0 * z["holding"] and z["margin"] >= 3.0,
                f"drive {z['available']} N vs {z['holding']} N to hold, {z['required']} N to move (margin {z['margin']}x, need >= 3x)")
    d.requirements.append(Requirement("drive holds and moves the load with >= 3x margin", hold_margin))
    d.requirements.append(Requirement("lead screw self-locking (efficiency < 0.5)", lambda dd: (
        dd.get("leadscrew").ratings["efficiency"] < 0.5, f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    return d
