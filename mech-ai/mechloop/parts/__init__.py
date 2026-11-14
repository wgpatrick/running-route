"""Off-the-shelf parts as typed components.

Each catalog function returns a `Stock` part: simplified proxy geometry built
from published datasheet dimensions (no vendor CAD is redistributed), plus the
engineering data verifiers need: mass, ratings and named interfaces (mounting
hole patterns, shaft axes) in the part's local frame.

Ratings are typical values for the generic part class and are marked
`approximate`; replace with the chosen vendor's datasheet before purchase.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from build123d import (Align, Axis, Box, Cylinder, Location, Part, Plane, Pos, Rot, Shape,
                       Vector)

from ..model import Component, Design, Fastener

_REGISTRY: dict[str, Callable] = {}


@dataclass
class Stock:
    shape: Shape
    sku: str
    description: str
    mass_kg: float
    material: str = "steel"
    ratings: dict = field(default_factory=dict)
    interfaces: dict = field(default_factory=dict)  # name -> list[(x, y, z)] or dict
    cost_usd: float | None = None
    catalog: bool = False  # set only by catalog functions; hand-made proxies stay False


def part(fn):
    import functools

    @functools.wraps(fn)
    def wrapped(*a, **k):
        st = fn(*a, **k)
        st.catalog = True
        return st

    _REGISTRY[fn.__name__] = wrapped
    return wrapped


def catalog(query: str = "") -> list[dict]:
    out = []
    for name, fn in sorted(_REGISTRY.items()):
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        if query.lower() in name.lower() or query.lower() in doc.lower():
            import inspect

            out.append({"part": name, "signature": str(inspect.signature(fn)), "about": doc})
    return out


def place(design: Design, name: str, stock: Stock, loc: Location = Location(), body: str = "world",
          **meta) -> Component:
    """Add a catalog part to the design at `loc`. Geometry is never modified."""
    c = design.add(name, stock.shape.moved(loc), material=stock.material, body=body, cots=True,
                   sku=stock.sku, mass_kg=stock.mass_kg, ratings=dict(stock.ratings),
                   meta={"catalog": stock.catalog, "description": stock.description, "cost_usd": stock.cost_usd,
                         "interfaces": {k: [tuple(round(x, 4) for x in tuple((loc * Pos(*p)).position))
                                            for p in v] if isinstance(v, list) else v
                                        for k, v in stock.interfaces.items()}, **meta})
    return c


# ----------------------------------------------------------------- motors
_NEMA17 = {  # length: (mass kg, holding torque N*mm, rotor inertia g*cm^2)
    34: (0.22, 260.0, 38.0), 40: (0.28, 400.0, 54.0), 48: (0.36, 520.0, 68.0), 60: (0.50, 650.0, 102.0)}


@part
def nema17(length: int = 40) -> Stock:
    """NEMA 17 stepper motor (42.3 mm frame). Local frame: mounting face at Z=0, shaft along +Z, body below."""
    if length not in _NEMA17:
        raise ValueError(f"nema17 length must be one of {sorted(_NEMA17)}")
    mass, torque, inertia = _NEMA17[length]
    body = Pos(0, 0, -length / 2) * Box(42.3, 42.3, length)
    boss = Pos(0, 0, 1) * Cylinder(11, 2)
    shaft = Pos(0, 0, 12) * Cylinder(2.5, 24)
    holes = [(x, y, 0.0) for x in (-15.5, 15.5) for y in (-15.5, 15.5)]
    # typical 24 V torque-speed curve for this class, as a fraction of holding torque
    curve = [(0, 0.90), (300, 0.80), (600, 0.60), (900, 0.42), (1200, 0.30), (1800, 0.15)]
    return Stock(body + boss + shaft, f"NEMA17-{length}", f"NEMA 17 stepper, {length} mm body", mass,
                 ratings={"holding_torque_nmm": torque, "rotor_inertia_gcm2": inertia,
                          "torque_curve_rpm_frac": curve, "max_rpm": 1800, "approximate": True},
                 interfaces={"mount_holes_m3": holes, "shaft_dia": 5.0, "pilot_dia": 22.0,
                             "hole_square": 31.0, "thread_depth": 4.5},
                 cost_usd=14.0)


# ----------------------------------------------------------- linear motion
@part
def mgn12_rail(length: float) -> Stock:
    """MGN12 miniature linear rail. Local frame: rail along X centred at origin, base at Z=0, top at Z=8."""
    rail = Pos(0, 0, 4) * Box(length, 12, 8)
    n = int((length - 20) // 25) + 1
    x0 = -(n - 1) * 25 / 2
    holes = [(x0 + i * 25, 0.0, 0.0) for i in range(n)]
    for x, _, _ in holes:  # M3 clearance with counterbore; screw head seats at Z=3.5
        rail -= Pos(x, 0, 4) * Cylinder(1.75, 8)
        rail -= Pos(x, 0, 5.75) * Cylinder(3.0, 4.5)
    return Stock(rail, f"MGN12-R-{int(length)}", f"MGN12 rail, {length:.0f} mm", 0.65 * length / 1000,
                 interfaces={"mount_holes_m3": holes, "hole_pitch": 25.0, "screw_seat_z": 3.5},
                 cost_usd=6 + 0.04 * length)


@part
def mgn12h_carriage() -> Stock:
    """MGN12H carriage block (long). Local frame: sits on an MGN12 rail whose base is Z=0; top face at Z=13."""
    # the block rests on the rail's top face (Z=8) and clears its sides by 0.2 mm
    block = Pos(0, 0, 8) * Box(45.4, 27, 10) - Pos(0, 0, 5.5) * Box(45.4, 12.4, 5.0)
    holes = [(x, y, 13.0) for x in (-10, 10) for y in (-10, 10)]
    return Stock(block, "MGN12H", "MGN12H carriage block", 0.054,
                 ratings={"dynamic_load_n": 4700.0, "static_load_n": 5880.0, "static_moment_nm": 36.0,
                          "approximate": True},
                 interfaces={"mount_holes_m3": holes, "top_z": 13.0}, cost_usd=9.0)


@part
def extrusion_2020(length: float) -> Stock:
    """20x20 T-slot aluminium extrusion (slot 6). Local frame: along X centred at origin, section centred on the axis."""
    bar = Box(length, 20, 20)
    for rot in (0, 90, 180, 270):
        bar -= Rot(rot, 0, 0) * Pos(0, 0, 7.5) * Box(length, 6.2, 5.0)
    bar -= Rot(0, 90, 0) * Cylinder(2.1, length)
    return Stock(bar, f"EXT2020-{int(length)}", f"2020 T-slot extrusion, {length:.0f} mm", 0.45 * length / 1000,
                 material="al6061",
                 ratings={"Ixx_mm4": 6900.0, "E_mpa": 68900.0, "approximate": True},
                 interfaces={"slot_width": 6.2, "end_tap": "M5"}, cost_usd=2 + 0.012 * length)


@part
def linear_rod(diameter: float, length: float) -> Stock:
    """Hardened steel linear shaft. Local frame: along X centred at origin."""
    rod = Rot(0, 90, 0) * Cylinder(diameter / 2, length)
    mass = math.pi * (diameter / 2) ** 2 * length * 7.85e-6
    return Stock(rod, f"ROD-{diameter:g}x{int(length)}", f"Linear shaft {diameter:g} mm x {length:.0f} mm", mass,
                 cost_usd=3 + 0.01 * length)


# ----------------------------------------------------------- transmission
@part
def gt2_pulley(teeth: int = 20, bore: float = 5.0, belt_width: float = 6.0) -> Stock:
    """GT2 timing pulley with hub. Local frame: axis along Z, hub bottom at Z=0."""
    pd = teeth * 2.0 / math.pi
    od = pd - 0.76
    h_hub, h_fl = 6.0, 1.0
    shape = (Pos(0, 0, h_hub / 2) * Cylinder(od / 2 + 2, h_hub)
             + Pos(0, 0, h_hub + h_fl / 2) * Cylinder(od / 2 + 1.5, h_fl)
             + Pos(0, 0, h_hub + h_fl + (belt_width + 1) / 2) * Cylinder(od / 2, belt_width + 1)
             + Pos(0, 0, h_hub + 1.5 * h_fl + belt_width + 1) * Cylinder(od / 2 + 1.5, h_fl))
    total = h_hub + 2 * h_fl + belt_width + 1
    shape -= Pos(0, 0, total / 2) * Cylinder(bore / 2, total)
    return Stock(shape, f"GT2-{teeth}T-B{bore:g}", f"GT2 pulley {teeth} teeth, {bore:g} mm bore", 0.008 + 0.0004 * teeth,
                 material="al6061",
                 ratings={"pitch_diameter_mm": pd, "teeth": teeth, "belt_pitch_mm": 2.0},
                 interfaces={"bore": bore, "height": total, "belt_center_z": h_hub + h_fl + (belt_width + 1) / 2,
                             "belt_center": [(0.0, 0.0, h_hub + h_fl + (belt_width + 1) / 2)]},
                 cost_usd=2.5)


@part
def gt2_idler(teeth: int = 20, bore: float = 5.0, belt_width: float = 6.0) -> Stock:
    """GT2 toothed idler with bearings. Local frame: axis along Z, bottom flange at Z=0."""
    pd = teeth * 2.0 / math.pi
    od = pd - 0.76
    h = belt_width + 2.5
    shape = (Pos(0, 0, 0.5) * Cylinder(od / 2 + 1.5, 1) + Pos(0, 0, h / 2) * Cylinder(od / 2, h)
             + Pos(0, 0, h - 0.5) * Cylinder(od / 2 + 1.5, 1)) - Pos(0, 0, h / 2) * Cylinder(bore / 2, h)
    return Stock(shape, f"GT2-IDLER-{teeth}T-B{bore:g}", f"GT2 idler {teeth} teeth, {bore:g} mm bore", 0.007,
                 ratings={"pitch_diameter_mm": pd, "teeth": teeth, "belt_pitch_mm": 2.0},
                 interfaces={"bore": bore, "height": h, "belt_center_z": h / 2, "belt_center": [(0.0, 0.0, h / 2)]},
                 cost_usd=2.0)


@part
def leadscrew_t8(length: float, lead: float = 8.0) -> Stock:
    """T8 trapezoidal lead screw. Local frame: axis along Z, bottom end at Z=0."""
    screw = Pos(0, 0, length / 2) * Cylinder(4.0, length)
    return Stock(screw, f"T8x{lead:g}-{int(length)}", f"T8 lead screw, lead {lead:g} mm, {length:.0f} mm",
                 math.pi * 16 * length * 7.85e-6 * 0.85, material="stainless304",
                 ratings={"lead_mm": lead, "efficiency": 0.35 if lead <= 2 else 0.5, "approximate": True},
                 cost_usd=6 + 0.01 * length)


@part
def leadscrew_nut_t8() -> Stock:
    """T8 brass flanged nut. Local frame: axis along Z, flange bottom at Z=0, barrel above."""
    nut = (Pos(0, 0, 1.75) * Cylinder(11, 3.5) + Pos(0, 0, 3.5 + 5.75) * Cylinder(5.1, 11.5)) \
        - Pos(0, 0, 7.5) * Cylinder(4.0, 15)
    holes = [(8 * math.cos(a), 8 * math.sin(a), 0.0) for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    return Stock(nut, "T8-NUT", "T8 flanged brass nut", 0.012, material="brass",
                 interfaces={"mount_holes_m3": holes, "barrel_dia": 10.2, "flange_dia": 22.0}, cost_usd=1.5)


@part
def bearing(designation: str = "608") -> Stock:
    """Deep-groove ball bearing by designation (608, 625, 623, 6001, MR105). Local frame: axis Z, centred."""
    table = {  # d, D, B, C (N), C0 (N), mass kg
        "608": (8, 22, 7, 3450, 1370, 0.012), "625": (5, 16, 5, 1880, 680, 0.005),
        "623": (3, 10, 4, 640, 220, 0.0016), "6001": (12, 28, 8, 5400, 2350, 0.022),
        "MR105": (5, 10, 4, 430, 170, 0.0012)}
    if designation not in table:
        raise ValueError(f"bearing must be one of {sorted(table)}")
    d, D, B, C, C0, m = table[designation]
    ring = Cylinder(D / 2, B) - Cylinder(d / 2, B)
    return Stock(ring, f"BRG-{designation}", f"Ball bearing {designation} ({d}x{D}x{B})", m,
                 ratings={"dynamic_load_n": C, "static_load_n": C0}, interfaces={"bore": d, "od": D, "width": B},
                 cost_usd=1.0)


@part
def shaft_coupler(bore_a: float = 5.0, bore_b: float = 8.0) -> Stock:
    """Flexible jaw/beam shaft coupler, D19 x L25. Local frame: axis Z, bottom (bore_a side) at Z=0."""
    body = Pos(0, 0, 12.5) * Cylinder(9.5, 25) - Pos(0, 0, 6.25) * Cylinder(bore_a / 2, 12.5) \
        - Pos(0, 0, 18.75) * Cylinder(bore_b / 2, 12.5)
    return Stock(body, f"COUPLER-{bore_a:g}x{bore_b:g}", f"Flexible coupler {bore_a:g} to {bore_b:g} mm", 0.016,
                 material="al6061", ratings={"rated_torque_nmm": 1500.0, "approximate": True},
                 interfaces={"bore_a": bore_a, "bore_b": bore_b, "length": 25.0, "od": 19.0}, cost_usd=3.0)


def belt_length(teeth_a: int, teeth_b: int, center: float, pitch: float = 2.0) -> float:
    """Pitch length of a closed belt around two pulleys at a centre distance (mm)."""
    da, db = teeth_a * pitch / math.pi, teeth_b * pitch / math.pi
    return 2 * center + math.pi * (da + db) / 2 + (da - db) ** 2 / (4 * center)


# ----------------------------------------------------- electrics and printer subsystems
@part
def endstop_switch() -> Stock:
    """Microswitch endstop on a small board. Local frame: board on Z=0 (mount face), 20 x 10, switch body above;
    it is pressed at the point (0, 5.5, 5), pushing in -Y."""
    board = Pos(0, 0, 0.8) * Box(20, 10, 1.6)
    body = Pos(0, 1.5, 4.6) * Box(12.8, 5.8, 6.0)
    return Stock(board + body, "ENDSTOP-MICRO", "Microswitch endstop board", 0.004, material="abs",
                 interfaces={"trigger": [(0.0, 5.5, 5.0)], "mount_holes_m3": [(-7.5, -2.5, 0.0), (7.5, -2.5, 0.0)]},
                 ratings={"electrical": True}, cost_usd=1.5)


@part
def extruder_direct() -> Stock:
    """Direct-drive extruder with its own small motor. Local frame: mounting face on Z=0, 44 x 44 x 36 body above,
    filament path along -Z through the centre."""
    body = Pos(0, 0, 18) * Box(44, 44, 36)
    holes = [(x, y, 0.0) for x in (-15.5, 15.5) for y in (-15.5, 15.5)]
    return Stock(body, "EXTRUDER-DD", "Direct-drive extruder with pancake stepper", 0.24, material="al6061",
                 interfaces={"mount_holes_m3": holes, "filament_exit": [(0.0, 0.0, 0.0)]},
                 ratings={"electrical": True, "approximate": True}, cost_usd=45.0)


@part
def fan(size: int = 40) -> Stock:
    """Axial fan, 30 or 40 mm square, 10 mm thick. Local frame: centred, air along Z."""
    if size not in (30, 40):
        raise ValueError("fan size must be 30 or 40")
    body = Box(size, size, 10) - Cylinder(size / 2 - 1.5, 10)
    pitch = {30: 24.0, 40: 32.0}[size]
    holes = [(x, y, -5.0) for x in (-pitch / 2, pitch / 2) for y in (-pitch / 2, pitch / 2)]
    return Stock(body, f"FAN-{size}10", f"{size} mm axial fan", {30: 0.008, 40: 0.016}[size], material="abs",
                 interfaces={"mount_holes_m3": holes}, ratings={"electrical": True}, cost_usd=3.0)


@part
def control_board() -> Stock:
    """Printer control board (110 x 85 mm). Local frame: underside on Z=0, centred, 4 mounting holes."""
    board = Pos(0, 0, 9) * Box(110, 85, 18)
    holes = [(x, y, 0.0) for x in (-51, 51) for y in (-38.5, 38.5)]
    return Stock(board, "CTRL-BOARD", "32-bit printer control board with stepper drivers", 0.11, material="abs",
                 interfaces={"mount_holes_m3": holes}, ratings={"electrical": True, "stepper_drivers": 5}, cost_usd=45.0)


@part
def psu_24v(watts: int = 150) -> Stock:
    """Enclosed 24 V power supply (159 x 97 x 30 mm). Local frame: underside on Z=0, centred."""
    body = Pos(0, 0, 15) * Box(159, 97, 30)
    return Stock(body, f"PSU-24V-{watts}", f"24 V {watts} W enclosed power supply", 0.48, material="steel",
                 interfaces={"mount_holes_m4": [(-60, -32.5, 0.0), (60, -32.5, 0.0)]},
                 ratings={"electrical": True, "watts": watts}, cost_usd=22.0)


# --------------------------------------------------------------- fasteners
SCREW = {  # size: (thread d, head d, head h, hex key, close clearance hole, tap drill, proof load N class 12.9)
    "M2.5": (2.5, 4.5, 2.5, 2.0, 2.7, 2.05, 3290), "M3": (3.0, 5.5, 3.0, 2.5, 3.4, 2.5, 4880),
    "M4": (4.0, 7.0, 4.0, 3.0, 4.5, 3.3, 8520), "M5": (5.0, 8.5, 5.0, 4.0, 5.5, 4.2, 13800),
    "M6": (6.0, 10.0, 6.0, 5.0, 6.6, 5.0, 19500), "M8": (8.0, 13.0, 8.0, 6.0, 9.0, 6.8, 35500)}


@part
def shcs(size: str = "M3", length: float = 10.0) -> Stock:
    """Socket head cap screw (ISO 4762). Local frame: underside of head at Z=0, thread along -Z, head above."""
    d, hd, hh, key, *_ = SCREW[size]
    shape = Pos(0, 0, -length / 2) * Cylinder(d / 2, length) + Pos(0, 0, hh / 2) * Cylinder(hd / 2, hh)
    mass = (math.pi * (d / 2) ** 2 * length + math.pi * (hd / 2) ** 2 * hh) * 7.85e-6
    return Stock(shape, f"SHCS-{size}x{length:g}", f"Socket head cap screw {size} x {length:g}", mass,
                 ratings={"proof_load_n": SCREW[size][6]},
                 interfaces={"thread_d": d, "head_d": hd, "head_h": hh, "hex_key": key}, cost_usd=0.08)


NUT = {"M2.5": (5.0, 2.0), "M3": (5.5, 2.4), "M4": (7.0, 3.2), "M5": (8.0, 4.7), "M6": (10.0, 5.2), "M8": (13.0, 6.8)}


@part
def hex_nut(size: str = "M3") -> Stock:
    """Hex nut (ISO 4032). Local frame: axis Z, bearing face at Z=0, nut body above."""
    from build123d import RegularPolygon, extrude

    af, h = NUT[size]
    d = SCREW[size][0]
    body = extrude(RegularPolygon(af / 2, 6, major_radius=False), h)  # solid: the thread is the overlap with the screw
    return Stock(body, f"NUT-{size}", f"Hex nut {size}", af * af * 0.866 * h * 7.85e-6 * 0.7,
                 interfaces={"across_flats": af, "height": h, "thread_d": d}, cost_usd=0.03)


def add_nut(design: Design, name: str, size: str, at, direction=(0, 0, 1), body: str = "world",
            screw: str | None = None) -> Component:
    """Place a hex nut with its bearing face at `at`, body extending along `direction`.
    Pass `screw=` to record that this nut is what that screw threads into."""
    dvec = Vector(*direction).normalized()
    c = place(design, name, hex_nut(size), Location(Plane(origin=at, z_dir=dvec)), body=body)
    if screw:
        design.join(screw, name, "thread")
        design.allow_overlap(screw, name)
        sc = design.get(screw)
        sc.meta.setdefault("threads_into", []).append(name)
    return c


def clearance_hole(size: str) -> float:
    return SCREW[size][4]


def tap_drill(size: str) -> float:
    return SCREW[size][5]


def add_screw(design: Design, name: str, size: str, length: float, at, direction=(0, 0, -1),
              body: str = "world", threads_into: str | list[str] | None = None, clamps=(),
              tnut: bool = False) -> Component:
    """Place a cap screw with the underside of its head at `at`, pointing along `direction`.
    Registers it as a Fastener (tool access is checked), allows the thread to overlap the
    part(s) it screws into and records that it holds them. tnut=True means it threads into
    a T-nut in that part's slot (added to the BOM)."""
    st = shcs(size, length)
    dvec = Vector(*direction).normalized()
    loc = Location(Plane(origin=at, z_dir=-dvec))
    c = place(design, name, st, loc, body=body, thread_d=SCREW[size][0],
              threads_into=[threads_into] if isinstance(threads_into, str) else list(threads_into or []),
              tnut=tnut)
    head_top = Vector(*at) - dvec * st.interfaces["head_h"]
    design.fasteners.append(Fastener(name, tuple(-dvec), tuple(head_top),
                                     tool_diameter=st.interfaces["hex_key"] * 1.6, tool_length=50.0,
                                     clamps=tuple(clamps)))
    if threads_into:
        for t in ([threads_into] if isinstance(threads_into, str) else threads_into):
            design.allow_overlap(name, t, max_volume=math.pi * (SCREW[size][0] / 2) ** 2 * length)
            design.join(name, t, "tnut" if tnut else "thread")
    if tnut:
        design.bom_extra(f"TNUT-2020-{size}", 1, 0.15)
    return c


@part
def corner_bracket_2020() -> Stock:
    """Cast corner bracket for 2020 extrusion. Local frame: inside corner at origin, legs along +X and +Y, 18 mm wide centred on Z=0."""
    from build123d import Polygon, extrude

    tri = extrude(Polygon((0, 0), (20, 0), (0, 20), align=None), 9, both=True)
    return Stock(tri, "BRKT-2020", "2020 corner bracket", 0.012, material="al6061", cost_usd=0.6)


def add_corner_bracket(design: Design, name: str, a: str, b: str, corner, u, v, body: str = "world") -> Component:
    """Brace two perpendicular extrusions: bracket's inside corner at `corner`, legs along
    unit directions u (lying on part a) and v (lying on part b). Its two M5 screws and
    T-nuts are added to the BOM and recorded as the joint."""
    c = place(design, name, corner_bracket_2020(), Location(Plane(origin=corner, x_dir=u, z_dir=Vector(*u).cross(Vector(*v)))),
              body=body)
    design.join(name, a, "m5_tnut")
    design.join(name, b, "m5_tnut")
    design.bom_extra("SHCS-M5x8", 2, 0.08)
    design.bom_extra("TNUT-2020-M5", 2, 0.15)
    return c
