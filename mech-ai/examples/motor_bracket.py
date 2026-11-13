"""Motor bracket: holds a NEMA 17 on a 2020 extrusion and reacts belt tension.

Requirement: 3D-printed PETG, belt pull of 80 N on the motor shaft side (X),
factor of safety >= 3, deflection at the motor face <= 0.5 mm, mass <= 60 g.
"""
from build123d import Box, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from mechloop import Design, LoadCase, Requirement
from mechloop.parts import add_screw, clearance_hole, extrusion_2020, nema17, place

T_BASE = 5.0   # base flange thickness
T_WALL = 5.0   # motor plate thickness
T_RIB = 3.0    # side gusset thickness
W = 44.0       # bracket width (Y)
H = 46.0       # motor plate height above base
FOOT = 30.0    # base flange length (X)


def bracket():
    base = Pos(FOOT / 2, 0, T_BASE / 2) * Box(FOOT, W, T_BASE)
    wall = Pos(T_WALL / 2, 0, T_BASE + H / 2) * Box(T_WALL, W, H)
    b = base + wall
    # side gussets tie the wall to the base (iteration 2: FoS 1.14 and 6.5 mm deflection without them)
    tri = Plane.XZ * Polygon((T_WALL, T_BASE), (FOOT, T_BASE), (T_WALL, T_BASE + H), align=None)
    for y in (-W / 2 + T_RIB, W / 2):
        b += Pos(0, y, 0) * extrude(tri, T_RIB)
    cz = T_BASE + H / 2  # motor axis height
    # motor pilot and M3 holes through the wall (axis along X)
    b -= Pos(T_WALL / 2, 0, cz) * Rot(0, 90, 0) * Cylinder(11.5, T_WALL)
    for y in (-15.5, 15.5):
        for z in (-15.5, 15.5):
            b -= Pos(T_WALL / 2, y, cz + z) * Rot(0, 90, 0) * Cylinder(clearance_hole("M3") / 2, T_WALL)
    # two M5 holes down into the extrusion slot
    for y in (-12, 12):
        b -= Pos(15, y, T_BASE / 2) * Cylinder(clearance_hole("M5") / 2, T_BASE)
    return b, cz


def build() -> Design:
    d = Design("motor_bracket", max_mass_kg=0.40)
    br, cz = bracket()
    d.add("bracket", br, material="petg")
    place(d, "extrusion", extrusion_2020(120), Location((15, 0, -10), (0, 0, 90)))
    # motor: mounting face against the wall's -X side, shaft pointing +X through the wall
    place(d, "motor", nema17(40), Location((0, 0, cz), (0, 90, 0)))
    for i, (y, z) in enumerate([(-15.5, -15.5), (-15.5, 15.5), (15.5, -15.5), (15.5, 15.5)]):
        add_screw(d, f"motor_screw_{i}", "M3", 6, at=(T_WALL, y, cz + z), direction=(-1, 0, 0),
                  threads_into="motor", clamps=("bracket", "motor"))
    for i, y in enumerate((-12, 12)):
        add_screw(d, f"base_screw_{i}", "M5", 8, at=(15, y, T_BASE), direction=(0, 0, -1),
                  threads_into="extrusion", clamps=("bracket", "extrusion"))
    d.loadcases.append(LoadCase(
        "belt_pull", "bracket",
        fixed=lambda f: abs(f.center().Z) < 1e-6,                       # underside on the extrusion
        loaded=lambda f: abs(f.center().X) < 1e-6 and f.area > 500,    # motor face of the wall
        force=(80.0, 0.0, 0.0), min_fos=3.0, max_deflection=0.5))
    d.requirements.append(Requirement(
        "bracket mass <= 60 g", lambda dd: ((m := dd.get("bracket").mass()) <= 0.060, f"{m * 1000:.1f} g")))
    return d
