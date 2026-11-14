"""Off-the-shelf parts as typed components.

Each catalog function returns a `Stock` part: simplified proxy geometry built
from published datasheet dimensions (no vendor CAD is redistributed), plus the
engineering data verifiers need: mass, ratings and named interfaces (mounting
hole patterns, shaft axes) in the part's local frame.

Where a vendor document could be fetched, dimensions and ratings come from the
files in `mechloop/parts/vendor/` (one JSON per part family, each value with its
source URL) and the part is marked `verified` with a `source` record. Everything
else is still a typical value for the generic part class: `verified` stays False
and the ratings carry `approximate`. See docs/VENDOR_DATA.md.
"""
from __future__ import annotations

import functools
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from build123d import (Align, Axis, Box, Cylinder, Location, Part, Plane, Pos, Rot, Shape,
                       Vector)

from ..model import Component, Design, Fastener

_REGISTRY: dict[str, Callable] = {}
VENDOR_DIR = Path(__file__).parent / "vendor"


@functools.lru_cache(maxsize=None)
def vendor_data(family: str) -> dict:
    """The recorded vendor values for a part family (mechloop/parts/vendor/<family>.json)."""
    with open(VENDOR_DIR / f"{family}.json", encoding="utf-8") as f:
        return json.load(f)


def _source(family: str, level: str, part: str | None = None, url: str | None = None, unverified=(), note: str = "") -> dict:
    """Provenance record for a Stock. level: 'vendor' (read from the vendor's own document), 'standard'
    (a dimension standard, via a published table), 'secondary' (third-party transcription of vendor data),
    'partial' (only some fields confirmed), 'proxy' (nothing fetched). Only 'vendor' and 'standard' count as verified."""
    v = vendor_data(family)
    return {"level": level, "file": f"mechloop/parts/vendor/{family}.json", "vendor": v.get("vendor"), "part": part,
            "url": url or v["source_url"], "retrieved": v["retrieved"], "unverified_fields": list(unverified),
            **({"note": note} if note else {})}


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
    verified: bool = False  # dimensions and ratings were read from a vendor document or a standard table
    source: dict = field(default_factory=dict)  # provenance: see _source(); empty means proxy / typical class values


def part(fn):
    import functools

    @functools.wraps(fn)
    def wrapped(*a, **k):
        st = fn(*a, **k)
        st.catalog = True
        st.verified = st.source.get("level") in ("vendor", "standard")
        if st.verified:
            st.ratings.pop("approximate", None)
        lvl = st.source.get("level")
        if st.verified:
            st.ratings["source"] = f"{st.source.get('part') or st.sku}: {st.source['url']}"
        elif lvl in ("secondary", "partial"):
            st.ratings["source"] = f"{lvl}, unverified: {st.source['url']}"
        else:
            st.ratings["source"] = "typical, unverified"
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
                         "vendor_backed": stock.verified, "source": dict(stock.source),
                         "interfaces": {k: [tuple(round(x, 4) for x in tuple((loc * Pos(*p)).position))
                                            for p in v] if isinstance(v, list) else v
                                        for k, v in stock.interfaces.items()}, **meta})
    return c


# ----------------------------------------------------------------- motors
_NEMA17_OLD = {  # previous class values, kept for reference: length: (mass kg, holding torque N*mm, rotor inertia g*cm^2)
    34: (0.22, 260.0, 38.0), 40: (0.28, 400.0, 54.0), 48: (0.36, 520.0, 68.0), 60: (0.50, 650.0, 102.0)}
NEMA17_LENGTHS = (34, 40, 48, 60)


@part
def nema17(length: int = 40) -> Stock:
    """NEMA 17 stepper motor (42.3 mm frame). Local frame: mounting face at Z=0, shaft along +Z, body below.
    Each length is one StepperOnline motor (34: 17HS13-0404S, 40: 17HS16-2004S1, 48: 17HS19-2004S1, 60: 17HS24-2104S)."""
    if length not in NEMA17_LENGTHS:
        raise ValueError(f"nema17 length must be one of {sorted(NEMA17_LENGTHS)}")
    rec = vendor_data("stepperonline_nema17")["parts"][str(length)]
    v = rec["values"]
    torque = v["holding_torque_nm"] * 1000.0
    shaft_len = v["shaft_length_mm"]  # from the mounting face, pilot boss included
    body = Pos(0, 0, -length / 2) * Box(v["frame_mm_max"], v["frame_mm_max"], length)  # `length` is the maximum body length
    boss = Pos(0, 0, v["pilot_height_mm"] / 2) * Cylinder(v["pilot_dia_mm"] / 2, v["pilot_height_mm"])
    shaft = Pos(0, 0, shaft_len / 2) * Cylinder(v["shaft_dia_mm"] / 2, shaft_len)
    h = v["hole_square_mm"] / 2
    holes = [(x, y, 0.0) for x in (-h, h) for y in (-h, h)]
    # published 24 V pull-out torque curve, as a fraction of holding torque. Below the first published speed the
    # first point is used, above the last one the last point; max_rpm is where the published curve ends.
    pts = rec["pull_out_torque_curve"]["points_rpm_nmm"]
    curve = [(float(rpm), round(nmm / torque, 4)) for rpm, nmm in pts]
    return Stock(body + boss + shaft, f"NEMA17-{length}",
                 f"NEMA 17 stepper, {length} mm body (StepperOnline {rec['part_number']})", v["mass_g"] / 1000.0,
                 ratings={"holding_torque_nmm": torque, "rotor_inertia_gcm2": v["rotor_inertia_gcm2"],
                          "torque_curve_rpm_frac": curve, "max_rpm": float(pts[-1][0]),
                          "max_rpm_basis": "last speed of the published pull-out torque curve",
                          "torque_curve_conditions": rec["pull_out_torque_curve"]["title"],
                          "rated_current_a": v["rated_current_a"], "phase_resistance_ohm": v["phase_resistance_ohm"],
                          "phase_inductance_mh": v["phase_inductance_mh"], "vendor_part": rec["part_number"]},
                 interfaces={"mount_holes_m3": holes, "shaft_dia": v["shaft_dia_mm"], "pilot_dia": v["pilot_dia_mm"],
                             "hole_square": v["hole_square_mm"], "thread_depth": v["thread_depth_min_mm"],
                             "shaft_length": shaft_len},
                 cost_usd=14.0,
                 source=_source("stepperonline_nema17", "vendor", rec["part_number"], rec["datasheet"]["source_url"],
                                note="torque curve points read by eye from the published graph"))


# ----------------------------------------------------------- linear motion
_MGN12_NOTE = ("third-party transcriptions of the Hiwin MG table; the Hiwin catalogue itself could not be fetched. "
               "Accuracy class, preload and allowable mounting error are not sourced.")


@part
def mgn12_rail(length: float) -> Stock:
    """MGN12 miniature linear rail. Local frame: rail along X centred at origin, base at Z=0, top at Z=8."""
    v = vendor_data("hiwin_mgn12")["parts"]["MGNR12_rail"]["values"]
    wr, hr, pitch = v["width_WR_mm"], v["height_HR_mm"], v["hole_pitch_P_mm"]
    cb_depth = v["counterbore_depth_h_mm"]
    rail = Pos(0, 0, hr / 2) * Box(length, wr, hr)
    n = int((length - 2 * v["end_distance_E_mm"]) // pitch) + 1
    x0 = -(n - 1) * pitch / 2
    holes = [(x0 + i * pitch, 0.0, 0.0) for i in range(n)]
    for x, _, _ in holes:  # M3 clearance with counterbore; screw head seats at Z = HR - h
        rail -= Pos(x, 0, hr / 2) * Cylinder(v["bolt_hole_d_mm"] / 2, hr)
        rail -= Pos(x, 0, hr - cb_depth / 2) * Cylinder(v["counterbore_D_mm"] / 2, cb_depth)
    return Stock(rail, f"MGN12-R-{int(length)}", f"MGN12 rail, {length:.0f} mm", v["mass_kg_per_m"] * length / 1000,
                 interfaces={"mount_holes_m3": holes, "hole_pitch": pitch, "screw_seat_z": hr - cb_depth},
                 cost_usd=6 + 0.04 * length,
                 source=_source("hiwin_mgn12", "secondary", "MGNR12", note=_MGN12_NOTE))


@part
def mgn12h_carriage() -> Stock:
    """MGN12H carriage block (long). Local frame: sits on an MGN12 rail whose base is Z=0; top face at Z=13."""
    d = vendor_data("hiwin_mgn12")["parts"]
    v, rv = d["MGN12H_block"]["values"], d["MGNR12_rail"]["values"]
    H, H1, W, L = v["assembly_height_H_mm"], v["clearance_H1_mm"], v["width_W_mm"], v["length_L_mm"]
    # block body from H1 above the rail base to H; the rail channel clears the rail's sides by 0.2 mm
    block = Pos(0, 0, (H + H1) / 2) * Box(L, W, H - H1) \
        - Pos(0, 0, (rv["height_HR_mm"] + H1) / 2) * Box(L, rv["width_WR_mm"] + 0.4, rv["height_HR_mm"] - H1)
    holes = [(x, y, H) for x in (-v["hole_spacing_C_mm"] / 2, v["hole_spacing_C_mm"] / 2)
             for y in (-v["hole_spacing_B_mm"] / 2, v["hole_spacing_B_mm"] / 2)]
    moments = {k: v[f"static_moment_{k}_Nm"] for k in ("MR", "MP", "MY")}
    return Stock(block, "MGN12H", "MGN12H carriage block", v["mass_kg"],
                 ratings={"dynamic_load_n": v["dynamic_load_C_kN"] * 1000.0, "static_load_n": v["static_load_C0_kN"] * 1000.0,
                          "static_moment_nm": min(moments.values()), "static_moment_mr_nm": moments["MR"],
                          "static_moment_mp_nm": moments["MP"], "static_moment_my_nm": moments["MY"],
                          "approximate": True},
                 # the M3 x 3.5 thread depth is from the secondary table only, so it is exposed under its own key and does not
                 # yet drive the interference verifier's thread_bottoms_out check (which reads "thread_depth")
                 interfaces={"mount_holes_m3": holes, "top_z": H, "thread_depth_unverified": v["thread_depth_mm"]},
                 cost_usd=9.0,
                 source=_source("hiwin_mgn12", "secondary", "MGN12H", note=_MGN12_NOTE))


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
                 interfaces={"slot_width": 6.2, "end_tap": "M5"}, cost_usd=2 + 0.012 * length,
                 source=_source("misumi_hfs5_2020", "proxy", "HFS5-2020",
                                note="typical, unverified: Misumi's catalogue was unreachable. A community DXF of the profile "
                                     "integrates to Ixx 7419 mm^4, 182 mm^2, slot 6.0 (recorded in the file, not applied)."))


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
                 cost_usd=6 + 0.01 * length,
                 source=_source("stepperonline_leadscrew_t8", "partial" if lead == 8.0 else "proxy", "LSN-S-MB-320",
                                unverified=("efficiency", "mass_kg", "root diameter"),
                                note="only diameter 8 mm, lead 8 mm and stainless steel are confirmed (StepperOnline "
                                     "product page); efficiency is typical, unverified"))


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
    """Flexible jaw/beam shaft coupler, L25. Local frame: axis Z, bottom (bore_a side) at Z=0.
    5 x 8 mm bores: StepperOnline MH2025-5-8 jaw coupling (D20 x L25). Other bores: generic D19 x L25 proxy."""
    src, od, length, mass, torque, extra = {}, 19.0, 25.0, 0.016, 1500.0, {"approximate": True}
    if (bore_a, bore_b) == (5.0, 8.0):
        d = vendor_data("stepperonline_coupler")
        v = d["parts"]["MH2025-5-8"]["values"]
        od, length, mass, torque = v["outside_diameter_mm"], v["length_mm"], v["mass_g"] / 1000.0, v["rated_torque_nm"] * 1000.0
        extra = {"max_torque_nmm": v["max_torque_nm"] * 1000.0, "max_rpm": v["max_speed_rpm"],
                 "torsional_stiffness_nm_per_rad": v["torsional_stiffness_nm_per_rad"],
                 "inertia_gcm2": v["moment_of_inertia_kgm2"] * 1e7}
        src = _source("stepperonline_coupler", "vendor", "MH2025-5-8")
    body = Pos(0, 0, length / 2) * Cylinder(od / 2, length) - Pos(0, 0, length / 4) * Cylinder(bore_a / 2, length / 2) \
        - Pos(0, 0, 3 * length / 4) * Cylinder(bore_b / 2, length / 2)
    return Stock(body, f"COUPLER-{bore_a:g}x{bore_b:g}", f"Flexible coupler {bore_a:g} to {bore_b:g} mm", mass,
                 material="al6061", ratings={"rated_torque_nmm": torque, **extra},
                 interfaces={"bore_a": bore_a, "bore_b": bore_b, "length": length, "od": od}, cost_usd=3.0, source=src)


def belt_length(teeth_a: int, teeth_b: int, center: float, pitch: float = 2.0) -> float:
    """Pitch length of a closed belt around two pulleys at a centre distance (mm)."""
    da, db = teeth_a * pitch / math.pi, teeth_b * pitch / math.pi
    return 2 * center + math.pi * (da + db) / 2 + (da - db) ** 2 / (4 * center)


# ----------------------------------------------------- electrics and printer subsystems
@part
def endstop_switch() -> Stock:
    """Microswitch endstop on a small board. Local frame: board on Z=0 (mount face), 20 wide, from Y=-7.5 to Y=5,
    switch body above; it is pressed at the point (0, 5.5, 5), pushing in -Y. Two M3 holes at Y=-4.2."""
    board = Pos(0, -1.25, 0.8) * Box(20, 12.5, 1.6)
    body = Pos(0, 1.5, 4.6) * Box(12.8, 5.8, 6.0)
    for x in (-7.5, 7.5):   # M3 mounting holes, far enough from the switch body for a cap head to seat on the board
        board -= Pos(x, -4.2, 0.8) * Cylinder(1.6, 1.6)
    return Stock(board + body, "ENDSTOP-MICRO", "Microswitch endstop board", 0.004, material="abs",
                 interfaces={"trigger": [(0.0, 5.5, 5.0)], "mount_holes_m3": [(-7.5, -4.2, 0.0), (7.5, -4.2, 0.0)]},
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
    for x, y, _ in holes:
        body -= Pos(x, y, 0) * Cylinder(1.6, 10)
    return Stock(body, f"FAN-{size}10", f"{size} mm axial fan", {30: 0.008, 40: 0.016}[size], material="abs",
                 interfaces={"mount_holes_m3": holes}, ratings={"electrical": True}, cost_usd=3.0)


@part
def control_board() -> Stock:
    """Printer control board: BIGTREETECH SKR Mini E3 V3.0 (103.75 x 70.25 mm, 4 on-board TMC2209).
    Local frame: underside on Z=0, centred, +X along the long edge with the motor connectors on the +Y edge;
    5 mounting holes (not a rectangle). The 18 mm height is an envelope allowance, not a vendor figure."""
    d = vendor_data("bigtreetech_skr_mini_e3_v3")
    v = d["values"]
    w, dp = v["board_size_mm"]
    board = Pos(0, 0, 9) * Box(w, dp, 18)
    holes = [(round(x - w / 2, 3), round(y - dp / 2, 3), 0.0) for x, y in v["mount_holes_xy_mm"]]
    return Stock(board, "CTRL-BOARD", "32-bit printer control board with stepper drivers (BTT SKR Mini E3 V3.0)", 0.11,
                 material="abs",
                 interfaces={"mount_holes_m3": holes, "size": (w, dp)},
                 ratings={"electrical": True, "stepper_drivers": v["stepper_drivers"],
                          "motor_connectors": len(v["motor_connectors"]), "sense_resistor_ohm": v["driver_sense_resistor_ohm"],
                          "supply_v": tuple(v["power_input_v"]), "main_fuse_a": v["fuses"]["F1"]["rating_a"]},
                 cost_usd=45.0,
                 source=_source("bigtreetech_skr_mini_e3_v3", "vendor", "SKR Mini E3 V3.0",
                                unverified=("mass_kg", "height", "mount hole diameter", "heater/fan channel current limits")))


_LRS = {150: "LRS-150-24", 200: "LRS-200-24", 350: "LRS-350-24"}


@part
def psu_24v(watts: int = 150) -> Stock:
    """Enclosed 24 V power supply. Local frame: underside on Z=0, centred, length along X, terminal block at -X.
    150 / 200 / 350 W are MEAN WELL LRS-150-24 (159 x 97 x 30, two M3 base holes), LRS-200-24 and LRS-350-24
    (215 x 115 x 30, four M4 base holes). Any other wattage is a generic 159 x 97 x 30 proxy with typical values.
    `mount_holes_m4` always lists the base holes (kept for older designs); check `mount_thread` for the real size."""
    if watts not in _LRS:
        body = Pos(0, 0, 15) * Box(159, 97, 30)
        return Stock(body, f"PSU-24V-{watts}", f"24 V {watts} W enclosed power supply", 0.48, material="steel",
                     interfaces={"mount_holes_m4": [(-60, -32.5, 0.0), (60, -32.5, 0.0)], "mount_thread": "M4"},
                     ratings={"electrical": True, "watts": watts, "approximate": True}, cost_usd=22.0)
    v = vendor_data("meanwell_lrs")["parts"][str(watts)]
    rec, v = v, v["values"]
    L, W, H = v["length_mm"], v["width_mm"], v["height_mm"]
    body = Pos(0, 0, H / 2) * Box(L, W, H)
    bm = v["bottom_mount"]
    holes = [(x - L / 2, y - W / 2, 0.0) for x, y in bm["holes_xy_mm"]]
    return Stock(body, f"PSU-24V-{watts}", f"24 V {watts} W enclosed power supply (MEAN WELL {rec['model']})", v["mass_kg"],
                 material="steel",
                 interfaces={"mount_holes_m4": holes, f"mount_holes_{bm['thread'].lower()}": holes, "mount_thread": bm["thread"],
                             "mount_screw_max_depth": bm["max_screw_penetration_mm"], "size": (L, W, H)},
                 ratings={"electrical": True, "watts": watts, "rated_power_w": v["rated_power_w"],
                          "rated_current_a": v["rated_current_a"], "efficiency": v["efficiency_typ"],
                          "ac_current_a": {int(k): a for k, a in v["ac_current_typ_a"].items()},
                          "inrush_current_a": {int(k): a for k, a in v["inrush_current_typ_a"].items()}},
                 cost_usd=22.0,
                 source=_source("meanwell_lrs", "vendor", rec["model"], rec["datasheet"]["source_url"],
                                note="mass is the per-unit packing weight"))


# --------------------------------------------------------------- fasteners
# Head, socket and nut dimensions agree with the ISO 4762 / ISO 4032 tables recorded in vendor/iso_fasteners.json
# (tests/test_vendor.py checks this). Clearance holes, tap drills and proof loads are typical values, unverified.
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
                 interfaces={"thread_d": d, "head_d": hd, "head_h": hh, "hex_key": key}, cost_usd=0.08,
                 source=_source("iso_fasteners", "standard", f"ISO 4762 {size}", unverified=("proof_load_n",)))


NUT = {"M2.5": (5.0, 2.0), "M3": (5.5, 2.4), "M4": (7.0, 3.2), "M5": (8.0, 4.7), "M6": (10.0, 5.2), "M8": (13.0, 6.8)}


@part
def hex_nut(size: str = "M3") -> Stock:
    """Hex nut (ISO 4032). Local frame: axis Z, bearing face at Z=0, nut body above."""
    from build123d import RegularPolygon, extrude

    af, h = NUT[size]
    d = SCREW[size][0]
    body = extrude(RegularPolygon(af / 2, 6, major_radius=False), h)  # solid: the thread is the overlap with the screw
    return Stock(body, f"NUT-{size}", f"Hex nut {size}", af * af * 0.866 * h * 7.85e-6 * 0.7,
                 interfaces={"across_flats": af, "height": h, "thread_d": d}, cost_usd=0.03,
                 source=_source("iso_fasteners", "standard", f"ISO 4032 {size}",
                                vendor_data("iso_fasteners")["sources"][1]["source_url"]))


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
