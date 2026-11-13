"""Z-axis bed lift for a small 3D printer: 220 x 220 mm bed, 150 mm travel.

Layout (X = width, Y = depth with the front at -Y, Z = up):
- Base: U of 2020 extrusion (two side beams along Y, one rear cross beam along X).
- Two vertical 2020 uprights stand on the cross beam, MGN12 rails on their front faces.
- One NEMA 17 hangs under an aluminium angle between the uprights and turns a T8 lead
  screw through a (proxy, uncatalogued) 5-to-8 mm coupler.
- Body "bed": two MGN12H carriages, a one-piece aluminium carrier (back plate, two
  L-section arms, nut tab), the T8 nut and the bed plate.

Choices:
- Carrier in 6061 aluminium, not PETG: the arms cantilever ~220 mm and must stay within
  0.3 mm at the bed edge; PETG is ~33x less stiff, creeps under sustained load and sits
  under a heated bed. FEA treats the carrier as one monolithic piece (CNC'd or welded).
- T8 lead 2 mm (not 8): self-locking, so the bed does not drop when the motor is
  unpowered, and the drive force margin is large. 15 mm/s needs 450 rpm.
- The 1.5 kg payload is carried as extra mass on the bed plate (mass_kg override).
"""
import math

from build123d import Box, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from mechloop import Design, Joint, LoadCase, Requirement
from mechloop.parts import (Stock, add_corner_bracket, add_screw, clearance_hole, extrusion_2020, leadscrew_nut_t8,
                            leadscrew_t8, mgn12_rail, mgn12h_carriage, nema17, place)

TRAVEL = 150.0
PAYLOAD_KG = 1.5
BED = 220.0
T_BED = 3.0
UP_X = 90.0           # upright / rail centre, +/- X
UP_Y = 118.0          # upright centre Y (uprights at the back)
Y_FACE = UP_Y - 10    # front face of the uprights = rail base
Y_CAR = Y_FACE - 13   # carriage top face = carrier back-plate rear face
T_PLATE = 6.0         # carrier back plate thickness
Y_PF = Y_CAR - T_PLATE  # carrier back-plate front face
ZC = 110.0            # carriage centre height at home (bed at the bottom)
Z_BED = ZC + 25.0     # bed underside at home
LS_Y = 128.0          # lead screw / motor axis Y
MOTOR_L = 34
Z_MF = 22.0 + MOTOR_L  # motor mounting face = underside of the motor mount plate
T_MM = 5.0            # motor mount thickness
Z_TAB = 104.0         # underside of the nut tab at home
T_TAB = 6.0
PAD = 0.5             # height of the carriage seating pads on the back plate
T_WEB, T_FL = 5.0, 4.0  # arm web and flange thickness
FL_IN = 72.0          # arm flange inner |x|
BED_Y0, BED_Y1 = Y_CAR - BED, Y_CAR   # bed front / rear edge
BED_SCREWS = [(sx * 79.0, y) for sx in (-1, 1) for y in (-110.0, -15.0, 75.0)]
NUT_HOLES = [(8.0, 0.0), (-8.0, 0.0), (0.0, 8.0), (0.0, -8.0)]


def coupler() -> Stock:
    """PROXY (not in the mechloop catalog): generic 5 mm to 8 mm clamp coupler, D19 x L25.
    Local frame: axis Z, bottom at Z=0; 5 mm bore for the lower 13.5 mm, 8 mm bore above."""
    body = Pos(0, 0, 12.5) * Cylinder(9.5, 25) - Pos(0, 0, 6.75) * Cylinder(2.5, 13.5) \
        - Pos(0, 0, 19.25) * Cylinder(4.0, 11.5)
    return Stock(body, "COUPLER-5x8-D19L25-PROXY", "UNVERIFIED proxy: 5-8 mm shaft coupler D19 x L25", 0.02,
                 material="al6061", cost_usd=3.0)


def carrier_shape(carriage_holes):
    zp0, zp1 = ZC - 23, ZC + 23
    # back plate, relieved 0.5 mm at the rear so it seats on two machined pads (one per carriage)
    c = Pos(0, Y_PF + (T_PLATE - PAD) / 2, ZC) * Box(208, T_PLATE - PAD, zp1 - zp0)
    for sx in (-1, 1):
        c += Pos(sx * UP_X, Y_CAR - PAD / 2, ZC) * Box(27, PAD, 45.4)
        # arm web: on-edge plate, full plate depth at the root tapering to 12 mm at the tip
        prof = Plane.YZ * Polygon((Y_CAR - PAD, zp0), (Y_CAR - PAD, Z_BED), (BED_Y0, Z_BED), (BED_Y0, Z_BED - 12), align=None)
        c += Pos(sx * UP_X - T_WEB / 2, 0, 0) * extrude(prof, T_WEB)
        # top flange (inboard) that the bed bolts to
        x0, x1 = sorted((sx * FL_IN, sx * (UP_X + T_WEB / 2)))
        c += Pos((x0 + x1) / 2, (BED_Y0 + Y_PF) / 2, Z_BED - T_FL / 2) * Box(x1 - x0, Y_PF - BED_Y0, T_FL)
    # nut tab reaching back between the uprights
    y1 = LS_Y + 13
    c += Pos(0, (Y_PF + 3 + y1) / 2, Z_TAB + T_TAB / 2) * Box(26, y1 - Y_PF - 3, T_TAB)
    c -= Pos(0, LS_Y, Z_TAB + T_TAB / 2) * Cylinder(5.4, T_TAB)          # nut barrel
    for dx, dy in NUT_HOLES:
        c -= Pos(dx, LS_Y + dy, Z_TAB + T_TAB / 2) * Cylinder(clearance_hole("M3") / 2, T_TAB)
    for hx, hy, hz in carriage_holes:
        c -= Pos(hx, (Y_PF + Y_CAR) / 2, hz) * Rot(90, 0, 0) * Cylinder(clearance_hole("M3") / 2, T_PLATE)
    for x, y in BED_SCREWS:
        c -= Pos(x, y, Z_BED - T_FL / 2) * Cylinder(clearance_hole("M3") / 2, T_FL)
    return c


def motor_mount_shape():
    y_back = LS_Y + 22
    m = Pos(0, (Y_FACE - 5 + y_back) / 2, Z_MF + T_MM / 2) * Box(160, y_back - (Y_FACE - 5), T_MM)
    m += Pos(0, Y_FACE - 2.5, Z_MF + 12) * Box(200, 5, 24)       # flange up the front of both uprights
    # pilot as a U-slot open to the back so the mount can be drawn forward off the motor
    m -= Pos(0, LS_Y, Z_MF + T_MM / 2) * Cylinder(11.5, T_MM)
    m -= Pos(0, (LS_Y + y_back) / 2, Z_MF + T_MM / 2) * Box(23, y_back - LS_Y, T_MM)
    for x in (-15.5, 15.5):
        for y in (-15.5, 15.5):
            m -= Pos(x, LS_Y + y, Z_MF + T_MM / 2) * Cylinder(clearance_hole("M3") / 2, T_MM)
    for sx in (-1, 1):
        m -= Pos(sx * UP_X, Y_FACE - 2.5, Z_MF + 16) * Rot(90, 0, 0) * Cylinder(clearance_hole("M5") / 2, 5)
    return m


def build() -> Design:
    d = Design("z_axis", envelope=(300, 300, 330), base="base_cross")
    # ---- base and uprights ------------------------------------------------
    place(d, "base_cross", extrusion_2020(200), Location((0, UP_Y, 10)))
    for sx, n in ((-1, "left"), (1, "right")):
        place(d, f"base_{n}", extrusion_2020(280), Location((sx * 110, 10, 10), (0, 0, 90)))
        place(d, f"upright_{n}", extrusion_2020(300), Location((sx * UP_X, UP_Y, 170), (0, 90, 0)))
        add_corner_bracket(d, f"brkt_cross_front_{n}", "base_cross", f"base_{n}",
                           (sx * 100, UP_Y - 10, 10), (-sx, 0, 0), (0, -1, 0))
        add_corner_bracket(d, f"brkt_cross_back_{n}", "base_cross", f"base_{n}",
                           (sx * 100, UP_Y + 10, 10), (-sx, 0, 0), (0, 1, 0))
        add_corner_bracket(d, f"brkt_up_in_{n}", "base_cross", f"upright_{n}",
                           (sx * 80, UP_Y, 20), (-sx, 0, 0), (0, 0, 1))
        add_corner_bracket(d, f"brkt_up_out_{n}", f"base_{n}", f"upright_{n}",
                           (sx * 100, UP_Y, 20), (sx, 0, 0), (0, 0, 1))
    # ---- rails and carriages ------------------------------------------------
    carriage_holes = []
    for sx, n in ((-1, "left"), (1, "right")):
        rail = place(d, f"rail_{n}", mgn12_rail(225),
                     Location(Plane(origin=(sx * UP_X, Y_FACE, 197.5), x_dir=(0, 0, 1), z_dir=(0, -1, 0))))
        for i, (hx, hy, hz) in enumerate(rail.meta["interfaces"]["mount_holes_m3"][::2]):
            add_screw(d, f"rail_{n}_screw_{i}", "M3", 8, at=(hx, hy - 3.5, hz), direction=(0, 1, 0),
                      threads_into=f"upright_{n}", tnut=True)
        car = place(d, f"carriage_{n}", mgn12h_carriage(),
                    Location(Plane(origin=(sx * UP_X, Y_FACE, ZC), x_dir=(0, 0, 1), z_dir=(0, -1, 0))),
                    body="bed", guides="z")
        holes = car.meta["interfaces"]["mount_holes_m3"]
        carriage_holes += holes
        for i, (hx, hy, hz) in enumerate(holes):
            add_screw(d, f"carriage_{n}_screw_{i}", "M3", 10, at=(hx, hy - T_PLATE, hz), direction=(0, 1, 0),
                      body="bed", threads_into=f"carriage_{n}")
    # ---- carrier, nut, bed ----------------------------------------------------
    d.add("carrier", carrier_shape(carriage_holes), material="al6061", body="bed")
    # nut: flange under the tab (load path in compression), barrel up through the tab
    place(d, "z_nut", leadscrew_nut_t8(), Location((0, LS_Y, Z_TAB - 3.5)), body="bed")
    for i, (dx, dy) in enumerate(NUT_HOLES):
        # M3 x 12 down through tab and nut flange holes, M3 hex nut underneath
        add_screw(d, f"nut_screw_{i}", "M3", 12, at=(dx, LS_Y + dy, Z_TAB + T_TAB), body="bed", threads_into="z_nut")
    d.bom_extra("HEXNUT-M3", 4, 0.03)
    bed_shape = Pos(0, (BED_Y0 + BED_Y1) / 2, Z_BED + T_BED / 2) * Box(BED, BED, T_BED)
    bed_own = bed_shape.volume * 2700e-9
    d.add("bed", bed_shape, material="al6061", body="bed", mass_kg=bed_own + PAYLOAD_KG)   # plate + 1.5 kg payload
    for i, (x, y) in enumerate(BED_SCREWS):
        # from below through the arm flange into M3 tapped holes in the bed: flush print surface
        add_screw(d, f"bed_screw_{i}", "M3", 6, at=(x, y, Z_BED - T_FL), direction=(0, 0, 1), body="bed",
                  threads_into="bed")
    # ---- drive ------------------------------------------------------------------
    d.add("motor_mount", motor_mount_shape(), material="al6061")
    place(d, "z_motor", nema17(MOTOR_L), Location((0, LS_Y, Z_MF)))
    for i, (x, y) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"motor_screw_{i}", "M3", 8, at=(x, LS_Y + y, Z_MF + T_MM), threads_into="z_motor")
    for sx, n in ((-1, "left"), (1, "right")):
        add_screw(d, f"mount_bolt_{n}", "M5", 8, at=(sx * UP_X, Y_FACE - 5, Z_MF + 16), direction=(0, 1, 0),
                  threads_into=f"upright_{n}", tnut=True)
    z_cpl = Z_MF + 11                                  # coupler bottom; motor shaft tip is at Z_MF + 24
    place(d, "coupler", coupler(), Location((0, LS_Y, z_cpl)))
    screw = leadscrew_t8(200, lead=2.0)
    place(d, "leadscrew", screw, Location((0, LS_Y, z_cpl + 14)))
    d.join("coupler", "z_motor", "clamp")
    d.join("leadscrew", "coupler", "clamp")
    # ---- motion -------------------------------------------------------------------
    d.joints.append(Joint("z", "slide", "world", "bed", (0, 0, 1), range=(0.0, TRAVEL),
                          max_speed=15.0, max_accel=300.0,
                          drive={"motor": "z_motor", "kind": "leadscrew", "lead": screw.ratings["lead_mm"],
                                 "efficiency": screw.ratings["efficiency"]}))
    d.program = [{"to": {"z": TRAVEL}}, {"to": {"z": 0.0}}]
    d.tool_point = ("bed", (0.0, (BED_Y0 + BED_Y1) / 2, Z_BED + T_BED))
    # ---- structure -------------------------------------------------------------------
    w_bed = (bed_own + PAYLOAD_KG) * (9.81 + 0.3)      # payload + bed plate, gravity + 300 mm/s^2
    # fixed = the two carriage seating pads (planar faces at the rear of the back plate)
    carriage_pads = lambda f: abs(f.center().Y - Y_CAR) < 1e-6 and f.area > 1000 and abs(f.center().X) > 70
    d.loadcases.append(LoadCase(
        "payload_on_bed", "carrier", fixed=carriage_pads,
        loaded=lambda f: abs(f.center().Z - Z_BED) < 1e-6 and f.area > 1000,     # arm tops under the bed
        force=(0.0, 0.0, -w_bed), min_fos=3.0, max_deflection=0.3))
    d.loadcases.append(LoadCase(
        "nut_thrust", "carrier", fixed=carriage_pads,
        loaded=lambda f: abs(f.center().Z - Z_TAB) < 1e-6 and f.area > 300,      # nut flange seat under the tab
        force=(0.0, 0.0, 2.0 * 3.0 * 9.81), min_fos=3.0, max_deflection=0.3))    # 2x the ~3 kg moving weight
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

    def hold_margin(dd):
        from mechloop.verifiers.ratings import resolve_drives
        avail = resolve_drives(dd)["z"]["available_effort"]
        need = sum(c.mass() for c in dd.components if c.body == "bed") * (9.81 + 0.3)
        return avail >= 3.0 * need, f"drive {avail:.0f} N vs {need:.1f} N to lift and accelerate ({avail / need:.1f}x, need >= 3x)"
    d.requirements.append(Requirement("drive force >= 3x moving weight", hold_margin))
    d.requirements.append(Requirement("lead screw self-locking (efficiency < 0.5)", lambda dd: (
        dd.get("leadscrew").ratings["efficiency"] < 0.5, f"efficiency {dd.get('leadscrew').ratings['efficiency']}")))
    return d
