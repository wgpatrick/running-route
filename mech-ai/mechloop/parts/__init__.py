"""Off-the-shelf parts as typed components.

Each catalog function returns a `Stock` part: a simple simulation solid (`shape`)
built from published datasheet dimensions, a detailed model (`detail`: vendor or
community STEP from vendor_cad/, or generated to a standard) in the same frame
where there is one, plus the engineering data verifiers need: mass, ratings and
named interfaces (mounting hole patterns, shaft axes) in the part's local frame.
See docs/VENDOR_CAD.md.

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
from . import details

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
    # `shape` is the simulation solid (simple and clean: every verifier works on it). `detail` is the detailed model
    # (vendor STEP where there is one) in the same local frame, for display and export, and the reference `shape` is
    # checked against. `model` says what it is: kind ("vendor CAD" | "community CAD" | "generated to standard" |
    # "proxy"), source, file, and what the proxy-match check should find. See mechloop/parts/vendor_cad.py.
    detail: Shape | None = None
    model: dict = field(default_factory=dict)
    # The real, orderable product (practice DG-07, mechloop/verifiers/purchased.py): maker, mpn, sellers, stock_size, datasheet,
    # ratings_source. Empty: taken from mechloop/data/real_parts.json by SKU, else from `source` and the ratings.
    real_part: dict = field(default_factory=dict)


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
        _attach_model(fn.__name__, a, k, st)
        return st

    _REGISTRY[fn.__name__] = wrapped
    return wrapped


def _attach_model(fn_name: str, a: tuple, k: dict, st: Stock) -> None:
    """Finish a catalog part's CAD record: a hand-downloaded STEP named after the SKU (or one of model["inbox"]) in
    vendor_cad/inbox/ replaces the detail model; a part without one is marked "proxy"."""
    from . import vendor_cad

    args = ", ".join([repr(x) for x in a] + [f"{n}={v!r}" for n, v in sorted(k.items())])
    names = [st.sku] + list(st.model.get("inbox", []))
    ov = vendor_cad.inbox_override(names, st.detail if st.detail is not None else st.shape)
    if ov is not None:
        st.detail = ov[0]
        st.model = {**st.model, **ov[1], "replaced": st.model.get("kind", "proxy")}
    if st.detail is None:
        st.model = {**st.model, "kind": "proxy", "source": st.model.get("source", "simulation solid only (no CAD model)")}
    st.model["key"] = f"{fn_name}({args})"
    vendor_cad.STOCKS[st.model["key"]] = st


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
    trsf = loc.wrapped.Transformation()
    c = design.add(name, stock.shape.moved(loc), material=stock.material, body=body, cots=True,
                   sku=stock.sku, mass_kg=stock.mass_kg, ratings=dict(stock.ratings),
                   detail=stock.detail.moved(loc) if stock.detail is not None else None,
                   meta={"catalog": stock.catalog, "description": stock.description, "cost_usd": stock.cost_usd,
                         "vendor_backed": stock.verified, "source": dict(stock.source),
                         **({"real_part": dict(stock.real_part)} if stock.real_part else {}),
                         # what the displayed / exported geometry is, and where this instance sits (local -> world)
                         "model": {x: stock.model[x] for x in ("kind", "source", "file", "note", "key", "replaced", "state", "remade_from")
                                   if x in stock.model} or {"kind": "proxy", "source": "hand-made simulation solid"},
                         "placement": [[trsf.Value(i, j) for j in range(1, 5)] for i in range(1, 4)],
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
    detail, model = details.nema17(length, v, rec["part_number"])
    vendor_step = model.get("kind") == "vendor CAD"
    # Pilot boss: 2.0 mm on the drawings and in StepperOnline's STEP files (there 1.5 mm straight plus a 0.5 mm chamfer).
    pilot_h = v["pilot_height_mm"]
    boss = Pos(0, 0, pilot_h / 2) * Cylinder(v["pilot_dia_mm"] / 2, pilot_h)
    shaft = Pos(0, 0, shaft_len / 2) * Cylinder(v["shaft_dia_mm"] / 2, shaft_len)
    # What leaves the +X side near the rear, as in the detail model: the vendor STEP (34, 48 mm) has a small lead exit;
    # the community model used for the other lengths has a connector block.
    cn = details.NEMA17_LEAD_EXIT if vendor_step else details.NEMA17_CONNECTOR
    rear = details.NEMA17_VENDOR_STEP[length]["body"] if vendor_step else length      # the STEP's own rear face (34 mm motor: 33.0)
    conn = Pos((cn["x0"] + cn["x1"]) / 2 - 0.5, 0, -rear + sum(cn["z_from_rear"]) / 2) * Box(
        cn["x1"] - cn["x0"] + 1.0, 2 * cn["half_y"], cn["z_from_rear"][1] - cn["z_from_rear"][0])
    shaft_load = ({"max_radial_load_n": v["max_radial_load_n"], "max_radial_load_at_mm": v["max_radial_load_at_mm"],
                   "max_radial_load_basis": v["max_radial_load_basis"]} if "max_radial_load_n" in v else {})
    h = v["hole_square_mm"] / 2
    holes = [(x, y, 0.0) for x in (-h, h) for y in (-h, h)]
    # published 24 V pull-out torque curve, as a fraction of holding torque. Below the first published speed the
    # first point is used, above the last one the last point; max_rpm is where the published curve ends.
    pts = rec["pull_out_torque_curve"]["points_rpm_nmm"]
    curve = [(float(rpm), round(nmm / torque, 4)) for rpm, nmm in pts]
    return Stock(body + boss + shaft + conn, f"NEMA17-{length}",
                 f"NEMA 17 stepper, {length} mm body (StepperOnline {rec['part_number']})", v["mass_g"] / 1000.0,
                 ratings={"holding_torque_nmm": torque, "rotor_inertia_gcm2": v["rotor_inertia_gcm2"],
                          "torque_curve_rpm_frac": curve, "max_rpm": float(pts[-1][0]),
                          **({"shaft_dia_tol_mm": list(v["shaft_dia_tol_mm"])} if v.get("shaft_dia_tol_mm") else {}),
                          "max_rpm_basis": "last speed of the published pull-out torque curve",
                          "torque_curve_conditions": rec["pull_out_torque_curve"]["title"],
                          "rated_current_a": v["rated_current_a"], "phase_resistance_ohm": v["phase_resistance_ohm"],
                          "phase_inductance_mh": v["phase_inductance_mh"], "vendor_part": rec["part_number"], **shaft_load},
                 interfaces={"mount_holes_m3": holes, "shaft_dia": v["shaft_dia_mm"], "pilot_dia": v["pilot_dia_mm"],
                             "hole_square": v["hole_square_mm"], "thread_depth": v["thread_depth_min_mm"],
                             "shaft_length": shaft_len, "connector_side": "+X", "pilot_height": pilot_h,
                             "lead_exit": "lead exit" if vendor_step else "connector block"},
                 cost_usd=14.0, detail=detail, model=model,
                 source=_source("stepperonline_nema17", "vendor", rec["part_number"], rec["datasheet"]["source_url"],
                                note="torque curve points read by eye from the published graph"))


# ----------------------------------------------------------- linear motion
_MGN12_NOTE = ("confirmed by HIWIN's own catalogue (GW-11-5-EN-2207-K, section 3.5 MG series, Tables 3.76 to 3.90; "
               "vendor_docs/Hiwin_MG_catalogue.pdf, block `catalogue` of the vendor file). The values in use are the "
               "earlier transcriptions, equal to the catalogue's except in rounding: block mass 0.054 kg (catalogue prints "
               "0.05), static moments 38.22 / 36.26 / 36.26 N.m (38.2 / 36.3 / 36.3), rail screw M3x8 (M3 x 10).")
_MGN12_URL = "vendor_docs/Hiwin_MG_catalogue.pdf (HIWIN GmbH catalogue GW-11-5-EN-2207-K, printed pages 92-105; hand-collected)"
MGN12_PRELOAD_CLASSES = ("ZF", "Z0", "Z1")


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
    detail, model = details.mgn12_rail(length, v, holes)
    return Stock(rail, f"MGN12-R-{int(length)}", f"MGN12 rail, {length:.0f} mm", v["mass_kg_per_m"] * length / 1000,
                 detail=detail, model=model,
                 interfaces={"mount_holes_m3": holes, "hole_pitch": pitch, "screw_seat_z": hr - cb_depth},
                 cost_usd=6 + 0.04 * length,
                 source=_source("hiwin_mgn12", "vendor", "MGNR12", _MGN12_URL, note=_MGN12_NOTE))


@part
def mgn12h_carriage(preload: str | None = None) -> Stock:
    """MGN12H carriage block (long). Local frame: sits on an MGN12 rail whose base is Z=0; top face at Z=13.
    preload: Hiwin's class, "ZF" (4-10 um clearance), "Z0" (0-3 um, very light preload) or "Z1" (light preload). Left
    out, Z0 is ASSUMED (and the metrics say so): order that class, or pass the one you buy. It sets the block's radial
    rigidity (Z0 63 N/um, Z1 81; the catalogue gives none for ZF, so a ZF block falls back to the verifier's assumed
    figure) and the allowable parallelism error of two rails (ZF / Z0 9 um, Z1 5 um)."""
    d = vendor_data("hiwin_mgn12")
    cat = d["catalogue"]
    d = d["parts"]
    v, rv = d["MGN12H_block"]["values"], d["MGNR12_rail"]["values"]
    cls = preload or "Z0"
    if cls not in MGN12_PRELOAD_CLASSES:
        raise ValueError(f"mgn12h_carriage preload must be one of {MGN12_PRELOAD_CLASSES}")
    H, H1, W, L = v["assembly_height_H_mm"], v["clearance_H1_mm"], v["width_W_mm"], v["length_L_mm"]
    # block body from H1 above the rail base to H; the rail channel clears the rail's sides by 0.2 mm
    block = Pos(0, 0, (H + H1) / 2) * Box(L, W, H - H1) \
        - Pos(0, 0, (rv["height_HR_mm"] + H1) / 2) * Box(L, rv["width_WR_mm"] + 0.4, rv["height_HR_mm"] - H1)
    holes = [(x, y, H) for x in (-v["hole_spacing_C_mm"] / 2, v["hole_spacing_C_mm"] / 2)
             for y in (-v["hole_spacing_B_mm"] / 2, v["hole_spacing_B_mm"] / 2)]
    moments = {k: v[f"static_moment_{k}_Nm"] for k in ("MR", "MP", "MY")}
    rig = cat["radial_rigidity_n_per_um"]
    par = cat["mounting_surface"]["max_parallelism_of_two_rails_um"]
    stiff = {}
    if cls in rig["columns"]:
        stiff = {"radial_stiffness_n_per_m": rig["MGN12H"][rig["columns"].index(cls)] * 1e6,
                 "radial_stiffness_source": f"Hiwin MG catalogue Table 3.77 (p.96): MGN12H, preload {cls}, radial, per block"}
    detail, model = details.mgn12h(v)
    return Stock(block, "MGN12H", "MGN12H carriage block" + (f" (preload {cls})" if preload else ""), v["mass_kg"],
                 detail=detail, model=model,
                 ratings={"dynamic_load_n": v["dynamic_load_C_kN"] * 1000.0, "static_load_n": v["static_load_C0_kN"] * 1000.0,
                          "static_moment_nm": min(moments.values()), "static_moment_mr_nm": moments["MR"],
                          "static_moment_mp_nm": moments["MP"], "static_moment_my_nm": moments["MY"],
                          "preload_class": cls,
                          "preload_class_basis": "declared by the design" if preload else "assumed (catalogue default Z0; not declared)",
                          # Hiwin's L1: the block body without end caps, the length the ball tracks bear on
                          "ball_track_length_m": cat["block_dimensions"]["MGN12H"]["L1_mm"] * 1e-3, **stiff,
                          "allowable_parallelism_mm": round(par["MG_12"][par["columns"].index(cls)] * 1e-3, 6),
                          "allowable_parallelism_source": f"Hiwin MG catalogue Table 3.88 (p.104): MG_12, preload {cls}"},
                 # M3 x 3.5: Hiwin Table 3.79, so the interference verifier's thread_bottoms_out check applies
                 interfaces={"mount_holes_m3": holes, "top_z": H, "thread_depth": v["thread_depth_mm"]},
                 cost_usd=9.0,
                 source=_source("hiwin_mgn12", "vendor", "MGN12H", _MGN12_URL, note=_MGN12_NOTE))


@part
def extrusion_2020(length: float) -> Stock:
    """20x20 T-slot aluminium extrusion (slot 6). Local frame: along X centred at origin, section centred on the axis."""
    bar = Box(length, 20, 20)
    for rot in (0, 90, 180, 270):
        bar -= Rot(rot, 0, 0) * Pos(0, 0, 7.5) * Box(length, 6.2, 5.0)
    bar -= Rot(0, 90, 0) * Cylinder(2.1, length)
    detail, model = details.extrusion_2020(length)
    from .tslot import slot_2020
    return Stock(bar, f"EXT2020-{int(length)}", f"2020 T-slot extrusion, {length:.0f} mm", 0.45 * length / 1000,
                 material="al6061", detail=detail, model=model,
                 ratings={"Ixx_mm4": 6900.0, "E_mpa": 68900.0, "approximate": True},
                 interfaces={"slot_width": 6.2, "end_tap": "M5", "slot": slot_2020()}, cost_usd=2 + 0.012 * length,
                 source=_source("misumi_hfs5_2020", "partial", "Misumi HFS5-2020",
                                unverified=("mass (0.45 kg/m in the simulation; Misumi 0.5 kg/m)", "Ixx (6900 in the simulation; Misumi 7420)"),
                                note="Misumi HFS5-2020, slot 6, sold cut to length by Misumi (the only purchased part bought cut). Section "
                                     "from Misumi's catalogue (p.2686: 183 mm^2, 0.5 kg/m, Ix 7420 mm^4) and Misumi's STEP (182.13 mm^2; "
                                     "the display model). The simulation solid's mass and Ixx are the older typical figures, kept "
                                     "so older designs' results do not move."))


@part
def linear_rod(diameter: float, length: float) -> Stock:
    """Hardened steel linear shaft. Local frame: along X centred at origin."""
    rod = Rot(0, 90, 0) * Cylinder(diameter / 2, length)
    mass = math.pi * (diameter / 2) ** 2 * length * 7.85e-6
    return Stock(rod, f"ROD-{diameter:g}x{int(length)}", f"Linear shaft {diameter:g} mm x {length:.0f} mm", mass,
                 cost_usd=3 + 0.01 * length)


# ----------------------------------------------------------- transmission
# Belt width in the SKU. The 6 and 12 mm parts were catalogued before the width was part of the name and existing designs
# and BOMs use those names, so they keep them; every other width (9 mm) carries it: "GT2-20T-B5-W9", with the rating
# belt_width_mm. The pulley and idler shapes are generic parts, not Gates products: Gates' design manual
# (vendor_docs/Gates_GT2_design_manual.pdf, mechloop/parts/vendor/gates_gt2.json) lists 2 mm pitch belts in 4, 6 and 9 mm
# only (no 12 mm belt or sprocket as stock) and its 20-groove sprocket only with a 3/16 in (4.76 mm) plain bore.
_GT2_LEGACY_WIDTHS = (6.0, 12.0)


def _gt2_width_tag(w: float) -> str:
    return "" if float(w) in _GT2_LEGACY_WIDTHS else f"-W{w:g}"


def _gt2_width_text(w: float) -> str:
    return "" if float(w) in _GT2_LEGACY_WIDTHS else f", {w:g} mm belt"


def _gt2_width_rating(w: float) -> dict:
    return {} if float(w) in _GT2_LEGACY_WIDTHS else {"belt_width_mm": float(w)}


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
    return Stock(shape, f"GT2-{teeth}T-B{bore:g}{_gt2_width_tag(belt_width)}", f"GT2 pulley {teeth} teeth, {bore:g} mm bore{_gt2_width_text(belt_width)}",
                 0.008 + 0.0004 * teeth, material="al6061",
                 ratings={"pitch_diameter_mm": pd, "teeth": teeth, "belt_pitch_mm": 2.0, **_gt2_width_rating(belt_width)},
                 interfaces={"bore": bore, "height": total, "belt_center_z": h_hub + h_fl + (belt_width + 1) / 2,
                             "belt_center": [(0.0, 0.0, h_hub + h_fl + (belt_width + 1) / 2)]},
                 cost_usd=2.5, source=_gt2_source(belt_width, bore, "pulley"))


@part
def gt2_idler(teeth: int = 20, bore: float = 5.0, belt_width: float = 6.0) -> Stock:
    """GT2 toothed idler with bearings. Local frame: axis along Z, bottom flange at Z=0."""
    pd = teeth * 2.0 / math.pi
    od = pd - 0.76
    h = belt_width + 2.5
    fl = od / 2 + 3.0     # flange radius: 18 mm diameter on a 20-tooth idler (was od + 3; corrected to the CAD model)
    shape = (Pos(0, 0, 0.5) * Cylinder(fl, 1) + Pos(0, 0, h / 2) * Cylinder(od / 2, h)
             + Pos(0, 0, h - 0.5) * Cylinder(fl, 1)) - Pos(0, 0, h / 2) * Cylinder(bore / 2, h)
    detail, model = details.gt2_idler(teeth, bore, belt_width)
    return Stock(shape, f"GT2-IDLER-{teeth}T-B{bore:g}{_gt2_width_tag(belt_width)}", f"GT2 idler {teeth} teeth, {bore:g} mm bore{_gt2_width_text(belt_width)}", 0.007,
                 detail=detail, model=model,
                 ratings={"pitch_diameter_mm": pd, "teeth": teeth, "belt_pitch_mm": 2.0, **_gt2_width_rating(belt_width)},
                 interfaces={"bore": bore, "height": h, "belt_center_z": h / 2, "belt_center": [(0.0, 0.0, h / 2)],
                             "flange_dia": 2 * fl},
                 cost_usd=2.0, source=_gt2_source(belt_width, bore, "idler"))


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
    """T8 brass flanged nut. Local frame: axis along Z, flange bottom at Z=0, barrel above to Z=13.5; the barrel also
    stands 1.5 mm proud below the flange (Z=-1.5), so the seat needs a 10.2 mm bore or counterbore."""
    nut = (Pos(0, 0, 1.75) * Cylinder(11, 3.5) + Pos(0, 0, 6.0) * Cylinder(5.1, 15.0)) \
        - Pos(0, 0, 6.0) * Cylinder(4.0, 15)
    detail, model = details.t8_nut()
    holes = [(8 * math.cos(a), 8 * math.sin(a), 0.0) for a in (0, math.pi / 2, math.pi, 3 * math.pi / 2)]
    return Stock(nut, "T8-NUT", "T8 flanged brass nut", 0.012, material="brass", detail=detail, model=model,
                 interfaces={"mount_holes_m3": holes, "barrel_dia": 10.2, "flange_dia": 22.0, "stub_below_flange": 1.5},
                 cost_usd=1.5)


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
    iface = {"bore": d, "od": D, "width": B}
    if designation == "608":
        # SKF 608 product data (vendor_cad/staging/practice_refs/08_SKF_608_product_data.pdf, practice rule BRG-024):
        # abutment da min 10, inner ring shoulder d1 ~12.15, Da max 20 mm; outer ring's inner diameter D2 ~19.2 (the
        # shields lie between d1 and D2). Axial limit (BRG-022, SKF general catalogue: small bearings, bore up to ~12 mm)
        # 0.25 C0 = 342 N.
        iface.update({"da_min": 10.0, "d1": 12.15, "D2": 19.2, "Da_max": 20.0, "axial_limit_n": 0.25 * C0})
    return Stock(ring, f"BRG-{designation}", f"Ball bearing {designation} ({d}x{D}x{B})", m,
                 ratings={"dynamic_load_n": C, "static_load_n": C0}, interfaces=iface,
                 cost_usd=1.0)


@part
def shaft_coupler(bore_a: float = 5.0, bore_b: float = 8.0) -> Stock:
    """Flexible jaw/beam shaft coupler, L25. Local frame: axis Z, bottom (bore_a side) at Z=0.
    5 x 8 mm bores: StepperOnline MH2025-5-8 jaw coupling (D20 x L25). Its bores are short: `max_insertion_a` /
    `max_insertion_b` in the interfaces are how far a shaft of each size can enter before it meets the elastomer spider
    (12.05 mm for the 5 mm shaft, 8.6 mm for the 8 mm one); `bore_depth` (7.5 mm) is the length the hub clamps.
    Other bores: generic D19 x L25 proxy with bores to mid-length."""
    src, od, length, mass, torque, extra = {}, 19.0, 25.0, 0.016, 1500.0, {"approximate": True}
    ins_a = ins_b = length / 2
    iface, detail, model = {}, None, {}
    if (bore_a, bore_b) == (5.0, 8.0):
        d = vendor_data("stepperonline_coupler")
        v = d["parts"]["MH2025-5-8"]["values"]
        st = d["vendor_step"]["measured_mm"]
        od, length, mass, torque = v["outside_diameter_mm"], v["length_mm"], v["mass_g"] / 1000.0, v["rated_torque_nm"] * 1000.0
        extra = {"max_torque_nmm": v["max_torque_nm"] * 1000.0, "max_rpm": v["max_speed_rpm"],
                 "torsional_stiffness_nm_per_rad": v["torsional_stiffness_nm_per_rad"],
                 "inertia_gcm2": v["moment_of_inertia_kgm2"] * 1e7}
        ins_a, ins_b = st["max_insertion_5mm_shaft"], st["max_insertion_8mm_shaft"]
        iface = {"bore_depth": st["bore_depth_with_chamfer"], "max_insertion_source": "vendor STEP (vendor_cad/COUPLER-5x8.step)"}
        src = _source("stepperonline_coupler", "vendor", "MH2025-5-8",
                      note="bore depth and shaft insertion limits are measured in the vendor's STEP file; the drawing does not give them")
        detail, model = details.shaft_coupler(od, length)
    # each bore is open only as far as a shaft of that size can really go; the rest is solid, so a shaft drawn deeper
    # overlaps the coupler and the interference verifier reports it
    body = Pos(0, 0, length / 2) * Cylinder(od / 2, length) - Pos(0, 0, ins_a / 2) * Cylinder(bore_a / 2, ins_a) \
        - Pos(0, 0, length - ins_b / 2) * Cylinder(bore_b / 2, ins_b)
    return Stock(body, f"COUPLER-{bore_a:g}x{bore_b:g}", f"Flexible coupler {bore_a:g} to {bore_b:g} mm", mass,
                 material="al6061", ratings={"rated_torque_nmm": torque, "angular_misalignment_deg": 1.0,   # typical for jaw couplings; not on the vendor page
                          "angular_misalignment_assumed": True,
                          # the maker publishes no angular or parallel misalignment and no axial stiffness for this coupling
                          # (vendor/stepperonline_coupler.json, not_published_by_the_maker): 1.0 deg stays assumed, the others unknown
                          "parallel_misalignment_mm": None, "axial_stiffness_n_per_mm": None,
                          "misalignment_and_axial_stiffness": "not published by the maker", **extra},
                 interfaces={"bore_a": bore_a, "bore_b": bore_b, "length": length, "od": od,
                             "max_insertion_a": ins_a, "max_insertion_b": ins_b, **iface},
                 cost_usd=3.0, source=src, detail=detail, model=model)


def _gt2_source(belt_width: float, bore: float, what: str) -> dict:
    """Provenance of a generic GT2 pulley / idler: what Gates' manual says about this width and bore as stock."""
    g = vendor_data("gates_gt2")
    stock_w = g["belt"]["stock_widths_mm"]["values"]
    notes = [f"generic {what}, not a Gates catalogue item; dimensions are typical values, unverified"]
    if float(belt_width) not in [float(x) for x in stock_w]:
        notes.append(f"a {belt_width:g} mm belt in 2 mm pitch is NOT Gates stock (stock widths: {', '.join(str(x) for x in stock_w)} mm; "
                     f"no {belt_width:g} mm sprocket either): buy generic GT2 belt and pulleys of this width")
    if what == "pulley" and abs(bore - 4.76) > 0.05:
        notes.append(f"Gates' 20-groove sprocket (2MR-20S) has a 3/16 in (4.76 mm) plain bore only: a {bore:g} mm bore is not Gates stock")
    return {**_source("gates_gt2", "proxy", f"GT2 {what}", note="; ".join(notes)),
            "gates_stock_belt_width": float(belt_width) in [float(x) for x in stock_w]}


def belt_length(teeth_a: int, teeth_b: int, center: float, pitch: float = 2.0) -> float:
    """Pitch length of a closed belt around two pulleys at a centre distance (mm)."""
    da, db = teeth_a * pitch / math.pi, teeth_b * pitch / math.pi
    return 2 * center + math.pi * (da + db) / 2 + (da - db) ** 2 / (4 * center)


# ----------------------------------------------------- electrics and printer subsystems
@part
def endstop_switch() -> Stock:
    """Lever-microswitch endstop on a small board (OMRON D2F-01L-size hinge-lever switch, gold contacts for logic-level
    loads, soldered to a 20 x 12.5 mm board). Local frame: board on Z=0 (mount face), 20 wide, from Y=-7.5 to Y=5,
    switch body above; the lever is pressed in -Y. Two M3 holes at Y=-4.2.
    `trigger` is the lever's NOMINAL operating position at its tip, (-9.0, 8.4, 4.5): 6.8 mm from the switch's
    mounting-hole line (OMRON data sheet). Unit to unit it lies anywhere within +/-`operating_position_tol` (1.5 mm) of
    that along Y, so the striker must push the lever to Y = 6.9 (`trigger_latest`) for every unit to switch, and must
    stop before the lever lies on the case at Y = 6.65 (`overtravel_to_case` below the latest operating position:
    0.25 mm). OMRON guarantees only `overtravel` = 0.55 mm past each unit's own operating position, and the switch lets
    go again up to `movement_differential` = 0.5 mm above where it operated. The lever tip rests at Y=11.6
    (`lever_free`). Three terminals come 2.6 mm out of the underside at `pin_holes` (X = -5.08, 0, 5.08, Y = -0.8): the
    seat needs a clearance hole at each (2.5 mm drill) and must not touch them. The terminal row is that of the
    generated carrier board, not of a bought module."""
    e = details.ENDSTOP
    w, dpt, t = e["pcb"]
    board = Pos(0, (e["pcb_y"][0] + e["pcb_y"][1]) / 2, t / 2) * Box(w, dpt, t)
    bx, by, bz = e["body_x"], e["body_y"], e["body_z"]
    body = Pos(0, (by[0] + by[1]) / 2, (bz[0] + bz[1]) / 2) * Box(bx[1] - bx[0], by[1] - by[0], bz[1] - bz[0])
    holes = [(x, y, 0.0) for x, y in e["holes"]]
    for x, y, _ in holes:   # M3 mounting holes, far enough from the switch body for a cap head to seat on the board
        board -= Pos(x, y, t / 2) * Cylinder(e["hole_d"] / 2, t)
    op, tol = e["operate_y"], e["operate_tol"]
    trig = (-9.0, round(op, 3), 4.5)
    detail, model = details.endstop()
    om = e["omron_angled_terminals"]
    src = _source("omron_d2f", "partial", "D2F-01L (hinge lever, PCB terminals, gold-alloy contacts, 0.1 A 30 VDC)",
                  unverified=("carrier board", "mount_holes_m3", "pin_holes", "pin_length_below", "lever tip X"),
                  note="switch figures (body, operating position 6.8 +/-1.5 mm, overtravel 0.55 mm min, movement differential "
                       "0.5 mm max, operating force 0.78 N max) are OMRON's D2F data sheet. Buy the gold-contact low-current type "
                       "(D2F-01L): a general-purpose D2F needs 100 mA at 5 V as its minimum load, a 3.3 V logic input with a "
                       "pull-up draws far less; D2F-01 needs 1 mA. The 20 x 12.5 mm carrier board is generated, not a known "
                       "bought module: its terminal row (0.9 mm below the body bottom, 2.62 mm through the board) is kept as "
                       f"drawn. OMRON's right-angled terminals (-A) would be {om['row_below_body_bottom_mm']} +/-{om['row_tol_mm']} mm "
                       f"below the body bottom and {om['through_a_1.6mm_board_mm']} mm through a 1.6 mm board: re-check the three "
                       "terminal holes once the bought module is known")
    return Stock(board + body, "ENDSTOP-MICRO",
                 "Microswitch endstop board (lever switch, OMRON D2F-01L type: gold contacts, for logic-level current)", 0.004,
                 material="abs",
                 interfaces={"trigger": [trig], "mount_holes_m3": holes, "lever_free": [e["lever_tip_free"]],
                             "operating_position_tol": tol,
                             "trigger_latest": [(-9.0, round(op - tol, 3), 4.5)], "trigger_earliest": [(-9.0, round(op + tol, 3), 4.5)],
                             "case_limit": [(-9.0, by[1], 4.5)], "press_direction": (0.0, -1.0, 0.0),
                             "overtravel": e["overtravel_min"],                       # OMRON's guaranteed minimum past the operating position
                             "overtravel_to_case": round(op - tol - by[1], 2),        # geometric room below the latest operating position
                             "movement_differential": e["movement_differential"],
                             "pretravel": round(e["lever_tip_free"][1] - op, 2),      # nominal; 1.7 to 4.7 over the spread
                             "pin_holes": [(x, y, 0.0) for x, y in e["pins"]], "pin_length_below": -e["pins_z"],
                             "pin_row_omron_right_angled": dict(om)},
                 ratings={"electrical": True, "operating_force_n": e["operating_force_n"],
                          "operating_position_mm": [round(op - e["hole_line_y"], 3), tol],
                          "min_load": "1 mA at 5 VDC (D2F-01, gold contacts)"},
                 cost_usd=1.5, detail=detail, model=model, source=src)


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
def fan(size: int = 40, volts: float = 24.0) -> Stock:
    """Axial fan, 30 or 40 mm square, 10 mm thick. Local frame: centred, air along Z.
    `volts` is the fan's RATED voltage and is checked against what its port supplies (`fan_voltage_mismatch`).
    fan(30, 12): Sunon MF30101V2-1000U-A99 (12 V, 6 to 13.8 V operating, 32 mA; maker's sheet), SKU FAN-3010-12V. It
    must not go on a 24 V fan output.
    fan(30) / fan(30, 24): a 24 V 30 mm fan, SKU FAN-3010. The Sunon family's 24 V member (MF30102V...) is the part
    meant, but its sheet is NOT in hand: current 0.05 A is a typical figure, unverified. fan(40): 24 V only, typical."""
    if size not in (30, 40):
        raise ValueError("fan size must be 30 or 40")
    volts = float(volts)
    if (size, volts) not in ((30, 24.0), (30, 12.0), (40, 24.0)):
        raise ValueError("catalogue fans: fan(30, 24), fan(30, 12) (Sunon MF30101V2-1000U-A99) and fan(40, 24)")
    body = Box(size, size, 10) - Cylinder(size / 2 - 1.5, 10)
    pitch = {30: 24.0, 40: 32.0}[size]
    holes = [(x, y, -5.0) for x in (-pitch / 2, pitch / 2) for y in (-pitch / 2, pitch / 2)]
    for x, y, _ in holes:
        body -= Pos(x, y, 0) * Cylinder(1.6, 10)
    detail, model = details.fan(size)
    mass, src = {30: 0.008, 40: 0.016}[size], {}
    rt = {"electrical": True, "rated_voltage_v": volts, "rated_current_a": {30: 0.05, 40: 0.07}[size],
          "rated_current_source": f"{volts:g} V axial fan of this size (typical, unverified)",
          "rated_voltage_source": "catalogue part declared as a 24 V fan; no maker's sheet in hand"}
    sku, text = f"FAN-{size}10", f"{size} mm axial fan, {volts:g} V"
    if size == 30:
        sv = vendor_data("sunon_mf30101v2")["values"]
        if volts == 12.0:
            mass, sku = sv["weight_g"] / 1000.0, "FAN-3010-12V"
            text = "30 mm axial fan, 12 V (Sunon MF30101V2-1000U-A99)"
            rt.update({"rated_voltage_v": sv["rated_voltage_v"], "operating_voltage_v": tuple(sv["operating_voltage_v"]),
                       "rated_current_a": sv["rated_current_a"], "rated_power_w": sv["rated_power_w"], "speed_rpm": sv["speed_rpm"],
                       "air_flow_m3_min": sv["air_flow_m3_min"], "static_pressure_pa": sv["static_pressure_pa"],
                       "noise_dba": sv["noise_dba"], "max_ambient_c": float(sv["operating_temp_c"][1]),
                       "vendor_part": "MF30101V2-1000U-A99",
                       "rated_current_source": "Sunon specification D03033610G-01 p.3: 32 mA rated (37 max) at 12 V",
                       "rated_voltage_source": "Sunon specification D03033610G-01 p.2, p.3: 12 VDC rated, 6 to 13.8 V operating"})
            src = _source("sunon_mf30101v2", "partial", "MF30101V2-1000U-A99",
                          unverified=("fourth mounting hole", "detail model"),
                          note="electrical figures, size, hole pitch and mass are the maker's. The sheet has THREE 3.2 mm holes on "
                               "24 mm (the 145 mm lead leaves at the fourth corner); the solid keeps four. Recommended screw M2.5")
        else:
            rt["vendor_part_intended"] = "Sunon MF30102V... (24 V member of the MF3010 family): sheet not in hand"
            src = _source("sunon_mf30101v2", "proxy", "24 V 30 x 30 x 10 fan",
                          note="the only sheet in hand (vendor_docs/FAN-3010_datasheet.pdf) is the 12 V MF30101V2-1000U-A99. The 24 V "
                               "family member (model code voltage digit 2) is what a 24 V output needs; its sheet is NOT in hand, so "
                               "current (0.05 A) and every other electrical figure here are typical values, unverified. Do not buy "
                               "the MF30101V2 for a 24 V output")
    return Stock(body, sku, text, mass, material="abs", detail=detail, model=model,
                 interfaces={"mount_holes_m3": holes}, ratings=rt, cost_usd=3.0, source=src)


@part
def control_board() -> Stock:
    """Printer control board: BIGTREETECH SKR Mini E3 V3.0 (103.75 x 70.25 mm, 4 on-board TMC2209).
    Local frame: underside on Z=0, centred, +X along the long edge with the motor connectors on the +Y edge;
    5 mounting holes (not a rectangle). The 18 mm height is an envelope allowance, not a vendor figure."""
    d = vendor_data("bigtreetech_skr_mini_e3_v3")
    v = d["values"]
    w, dp = v["board_size_mm"]
    board = Pos(0, 0, 7.9) * Box(w, dp, 15.8)       # 1.6 mm PCB + 14.2 mm tallest component (vendor STEP); was 18
    detail, model = details.skr_mini_e3_v3()
    holes = [(round(x - w / 2, 3), round(y - dp / 2, 3), 0.0) for x, y in v["mount_holes_xy_mm"]]
    return Stock(board, "CTRL-BOARD", "32-bit printer control board with stepper drivers (BTT SKR Mini E3 V3.0)", 0.11,
                 material="abs", detail=detail, model=model,
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
    detail, model = details.psu_lrs(rec["model"])
    return Stock(body, f"PSU-24V-{watts}", f"24 V {watts} W enclosed power supply (MEAN WELL {rec['model']})", v["mass_kg"],
                 material="steel", detail=detail, model=model,
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
    "M2": (2.0, 3.8, 2.0, 1.5, 2.2, 1.6, 2030),   # v11 (blower screws): ISO 4762 M2, recalled
    "M2.5": (2.5, 4.5, 2.5, 2.0, 2.7, 2.05, 3290), "M3": (3.0, 5.5, 3.0, 2.5, 3.4, 2.5, 4880),
    "M4": (4.0, 7.0, 4.0, 3.0, 4.5, 3.3, 8520), "M5": (5.0, 8.5, 5.0, 4.0, 5.5, 4.2, 13800),
    "M6": (6.0, 10.0, 6.0, 5.0, 6.6, 5.0, 19500), "M8": (8.0, 13.0, 8.0, 6.0, 9.0, 6.8, 35500)}


def mcmaster_part(sku: str) -> dict:
    """McMaster-Carr part number recorded for a fastener SKU (mechloop/parts/vendor/mcmaster_fasteners.json), for the
    BOM: {"mcmaster_pn", "mcmaster_pn_status"} or {} when none is recorded. Status "confirmed by the delivered STEP
    file" means the file of that number was inspected and equals the ISO dimensions; "unconfirmed" means it was not."""
    m = vendor_data("mcmaster_fasteners")
    pn = m["part_numbers"].get(sku)
    if not pn:
        return {}
    if f"{sku}.step" in m.get("wrong_file", {}):
        return {"mcmaster_pn": pn, "mcmaster_pn_status": "unconfirmed: the STEP file delivered under this name was a different part "
                                                         "(" + m["wrong_file"][f"{sku}.step"].split(";")[0] + ")"}
    seen = sku in m.get("screws", {}) or sku in m.get("nuts", {})
    batch = m.get("supplier_batch_2026_11_18") or {}
    b20 = m.get("instinct_2026_11_20") or {}
    if sku in b20.get("confirmed", []):        # McMaster's own STEP and drawing collected for the owner (Instinct REQ-001 / 002 / 006)
        return {"mcmaster_pn": pn, "mcmaster_pn_status": "confirmed: McMaster's drawing and STEP of this number collected for the owner "
                                                         "(Instinct, 2026-11-20; vendor_cad/staging/instinct_REQ-00x/MANIFEST.md)"}
    if sku in batch.get("confirmed", []):      # read from McMaster's product page for the owner (supplier CAD batch 2026-11-18)
        note = (batch.get("notes") or {}).get(sku)
        return {"mcmaster_pn": pn, "mcmaster_pn_status": "confirmed on McMaster's product page (supplier CAD batch 2026-11-18)"
                                                         + (f": {note}" if note else "")}
    # otherwise "confirmed" means only that a STEP file delivered under this number has the ISO dimensions
    return {"mcmaster_pn": pn, "mcmaster_pn_status": "confirmed by the delivered STEP file (geometry only: the part number was not "
                                                     "checked on McMaster's page)" if seen else
            "unconfirmed: listed in the collector's sources, no file inspected"}


@part
def shcs(size: str = "M3", length: float = 10.0) -> Stock:
    """Socket head cap screw (ISO 4762). Local frame: underside of head at Z=0, thread along -Z, head above."""
    d, hd, hh, key, *_ = SCREW[size]
    shape = Pos(0, 0, -length / 2) * Cylinder(d / 2, length) + Pos(0, 0, hh / 2) * Cylinder(hd / 2, hh)
    mass = (math.pi * (d / 2) ** 2 * length + math.pi * (hd / 2) ** 2 * hh) * 7.85e-6
    detail, model = details.shcs(size, length)
    sku_ = f"SHCS-{size}x{length:g}"
    batch = vendor_data("mcmaster_fasteners").get("supplier_batch_2026_11_18") or {}
    thr = {}
    if sku_ in (batch.get("thread_length_mm") or {}):       # the bought screw is partly threaded: thread over this length from the tip
        thr = {"thread_length": float(batch["thread_length_mm"][sku_])}
    elif sku_ in (batch.get("fully_threaded") or []):       # the bought screw is threaded to the head, longer than ISO's b
        thr = {"thread_length": float(length)}
    return Stock(shape, sku_, f"Socket head cap screw {size} x {length:g}", mass,
                 detail=detail, model=model,
                 ratings={"proof_load_n": SCREW[size][6], **mcmaster_part(sku_)},
                 interfaces={"thread_d": d, "head_d": hd, "head_h": hh, "hex_key": key, **thr}, cost_usd=0.08,
                 source=_source("iso_fasteners", "standard", f"ISO 4762 {size}", unverified=("proof_load_n",)))


# ISO 10642 hexagon socket countersunk head screws (90 deg head): size: (dk theoretical max, dk actual max, hex key).
# RECALLED from the standard's table (not fetched): check against the screw you buy.
CSK = {"M3": (6.72, 5.54, 2.0), "M4": (8.96, 7.53, 2.5), "M5": (11.2, 9.43, 3.0), "M6": (13.44, 11.34, 4.0)}


@part
def fhcs(size: str = "M5", length: float = 16.0) -> Stock:
    """Hexagon socket countersunk head screw (ISO 10642, 90 deg). Local frame: the TOP of the head (the face that lies
    flush in its countersink) at Z=0, head cone and thread along -Z; `length` is overall, head included, as the standard
    gives it. Head drawn at its actual maximum diameter dk; a countersink cut to the theoretical dk (interfaces
    "csk_dia") leaves the head (dk_theo - dk) / 2 below the surface. Head dimensions recalled (ISO 10642 table)."""
    if size not in CSK:
        raise ValueError(f"fhcs size must be one of {sorted(CSK)}")
    d = SCREW[size][0]
    dk_t, dk, key = CSK[size]
    hk = (dk - d) / 2.0
    from build123d import Cone

    shape = Pos(0, 0, -hk / 2) * Cone(d / 2, dk / 2, hk) + Pos(0, 0, -(hk + length) / 2) * Cylinder(d / 2, length - hk)
    mass = (math.pi * (d / 2) ** 2 * length + math.pi / 12 * hk * (dk ** 2 + dk * d + d * d) / 1.0 * 0.25) * 7.85e-6
    detail, model = details.fhcs(size, length)
    return Stock(shape, f"FHCS-{size}x{length:g}", f"Countersunk socket screw {size} x {length:g} (ISO 10642)", mass,
                 detail=detail, model=model,
                 ratings={"proof_load_n": SCREW[size][6] * 0.8, "head": "countersunk", **mcmaster_part(f"FHCS-{size}x{length:g}")},
                 interfaces={"thread_d": d, "head_d": dk, "head_h": 0.0, "hex_key": key, "head": "countersunk", "csk_dia": dk_t,
                             "head_below_surface": round((dk_t - dk) / 2.0, 2)},
                 cost_usd=0.12,
                 source=_source("iso_fasteners", "partial", f"ISO 10642 {size}",
                                unverified=("head diameter and height (recalled)", "proof_load_n"),
                                note="countersunk head dimensions recalled from ISO 10642, not fetched"))


NUT = {"M2": (4.0, 1.6), "M2.5": (5.0, 2.0), "M3": (5.5, 2.4), "M4": (7.0, 3.2), "M5": (8.0, 4.7), "M6": (10.0, 5.2), "M8": (13.0, 6.8)}


NUT_DIN934 = {"M5": 4.0}      # where DIN 934 (what McMaster's 90591A series is) differs in height from ISO 4032
# Prevailing-torque hex nuts with a nylon insert, ISO 10511 (the thin type; DIN 985 has the same heights): height m max, mm.
# Across flats as ISO 4032. RECALLED from the standard's table (not fetched): check against the nut you buy.
NUT_ISO10511 = {"M3": 4.0, "M4": 5.0, "M5": 5.0, "M6": 6.0, "M8": 8.0}


@part
def hex_nut(size: str = "M3", standard: str = "iso4032") -> Stock:
    """Hex nut. Local frame: axis Z, bearing face at Z=0, nut body above.
    standard "iso4032" (default): the generated ISO 4032 solid (M5: 8.0 across flats, 4.7 high).
    standard "din934": only where it differs, i.e. M5, 4.0 mm high (McMaster 90591A260, measured in its STEP file);
    SKU NUT-M5-DIN934.
    standard "iso10511": nylon-insert lock nut (nyloc), M3 to M8, ISO 10511 height (M3 4.0 mm; recalled, not fetched),
    SKU NUT-<size>-NYLOC; its nylon element is rated to about 120 degC (practice rule FST-072). Name it when that is the nut you will buy: 0.7 mm more thread then shows past it. The default
    M5 nut records McMaster's height beside its own (interfaces["height_din934_mcmaster"]) but is not changed by it."""
    from build123d import RegularPolygon, extrude

    if standard not in ("iso4032", "din934", "iso10511", "pem", "pem0"):
        raise ValueError("hex_nut standard must be 'iso4032', 'din934', 'iso10511', 'pem' or 'pem0'")
    if standard in ("pem", "pem0"):
        # "pem0" (v11): PEM S-<size>-0, the shank length SendCutSend stocks (its catalogue has no S-M3-1)
        dash = "0" if standard == "pem0" else "1"
        # A self-clinching nut pressed into sheet by the sheet supplier (PEM S-M3-1 class). STAND-IN: no PennEngineering
        # drawing was read, so it is drawn as the ISO 4032 hex nut solid it replaced (the plates' hex holes were drawn
        # for that solid); only the SKU, the BOM line and the state differ. Wanted: the supplier's STEP.
        af, h = NUT[size]
        body = extrude(RegularPolygon(af / 2, 6, major_radius=False), h)
        return Stock(body, f"NUT-PEM-S-{size}-{dash}", f"Self-clinching nut {size} in sheet (PEM S-{size}-{dash} class; installed by the sheet supplier)",
                     af * af * 0.866 * h * 7.85e-6 * 0.7, ratings={"approximate": True, "installed_by": "sheet supplier"},
                     interfaces={"across_flats": af, "height": h, "thread_d": SCREW[size][0]}, cost_usd=0.4,
                     detail=body, model={"kind": "proxy", "state": "stand-in", "inbox": [f"S-{size}-{dash}"],
                                         "source": "STAND-IN: drawn as an ISO 4032 hex nut solid (5.5 across flats, 2.4 high for M3); the "
                                                   "clinch nut's own body diameter, height and shank are not modelled (no drawing read)",
                                         "tolerance": {"volume_ratio": (0.3, 3.0), "mass_ratio": (0.2, 5.0)}},
                     source=_source("iso_fasteners", "proxy", f"PEM S-{size}-{dash} (self-clinching nut)",
                                    unverified=("body diameter", "height", "shank", "minimum sheet thickness", "mass_kg", "cost"),
                                    note="stand-in: PennEngineering's drawing was not fetched"))
    if standard == "iso10511":
        if size not in NUT_ISO10511:
            raise ValueError(f"hex_nut: ISO 10511 nylon-insert nuts here are {sorted(NUT_ISO10511)}, not {size}")
        af, h = NUT[size][0], NUT_ISO10511[size]
        body = extrude(RegularPolygon(af / 2, 6, major_radius=False), h)
        detail, model = details.nyloc_nut(size, af, NUT[size][1], h)
        return Stock(body, f"NUT-{size}-NYLOC", f"Nylon-insert lock nut {size} (ISO 10511, {h:g} mm high)",
                     af * af * 0.866 * h * 7.85e-6 * 0.7, ratings={"locking": "nyloc", "max_temp_c": 120.0, **mcmaster_part(f"NUT-{size}-NYLOC")},
                     interfaces={"across_flats": af, "height": h, "thread_d": SCREW[size][0]}, cost_usd=0.05,
                     detail=detail, model=model,
                     source=_source("iso_fasteners", "standard", f"ISO 10511 {size}", unverified=("height", "max_temp_c"),
                                    note="height m max from the ISO 10511 / DIN 985 table, recalled; nylon element about "
                                         "120 degC (NASA RP-1228)"))
    af, h = NUT[size]
    d = SCREW[size][0]
    mc = mcmaster_part(f"NUT-{size}")
    din = standard == "din934" and size in NUT_DIN934
    extra_i = {}
    if size in NUT_DIN934:
        extra_i["height_din934_mcmaster"] = NUT_DIN934[size]
        if not din and mc:      # the recorded McMaster nut is the DIN 934 one, not this ISO solid
            mc = {"mcmaster_pn": mc["mcmaster_pn"], "mcmaster_pn_status":
                  f"that McMaster number is the DIN 934 nut, {NUT_DIN934[size]:g} mm high, not this ISO 4032 nut ({h:g} mm): buy ISO 4032 "
                  f"nuts, or declare hex_nut('{size}', 'din934') / add_nut(..., standard='din934')"}
    if din:
        h = NUT_DIN934[size]
    body = extrude(RegularPolygon(af / 2, 6, major_radius=False), h)  # solid: the thread is the overlap with the screw
    detail, model = details.hex_nut(size) if not din else (None, {"source": "simulation solid only: DIN 934 height from McMaster's STEP"})
    iso = vendor_data("iso_fasteners")
    return Stock(body, f"NUT-{size}" + ("-DIN934" if din else ""), f"Hex nut {size}" + (" (DIN 934, McMaster 90591A260)" if din else ""),
                 af * af * 0.866 * h * 7.85e-6 * 0.7, detail=detail, model=model, ratings=dict(mc),
                 interfaces={"across_flats": af, "height": h, "thread_d": d, **extra_i}, cost_usd=0.03,
                 source=(_source("mcmaster_fasteners", "vendor", "90591A260 (DIN 934 M5 hex nut)",
                                 note="across flats 8.0 and thickness 4.0 mm measured in McMaster's STEP file") if din else
                         _source("iso_fasteners", "standard", f"ISO 4032 {size}", iso["sources"][1]["source_url"])))


def add_nut(design: Design, name: str, size: str, at, direction=(0, 0, 1), body: str = "world",
            screw: str | None = None, standard: str = "iso4032", locking: str | None = None) -> Component:
    """Place a hex nut with its bearing face at `at`, body extending along `direction`.
    Pass `screw=` to record that this nut is what that screw threads into. standard="pem": a self-clinching nut in
    sheet (stand-in solid, SKU NUT-PEM-S-<size>-1). standard="din934" places the McMaster
    DIN 934 nut where it differs from ISO 4032 (M5: 4.0 mm high instead of 4.7).
    locking="nyloc" (or "all_metal", "adhesive", "serrated", "jam"): the nut's locking provision (practice rule FST-070),
    recorded in meta["locking"]; the BOM line stays the nut's own (say the type in your BOM notes), unless
    standard="iso10511" places the real nylon-insert nut (taller, SKU NUT-<size>-NYLOC; locking is then "nyloc")."""
    if standard == "iso10511" and not locking:
        locking = "nyloc"
    dvec = Vector(*direction).normalized()
    c = place(design, name, hex_nut(size, standard), Location(Plane(origin=at, z_dir=dvec)), body=body)
    if locking:
        c.meta["locking"] = str(locking)
    if screw:
        design.join(screw, name, "thread")
        design.allow_overlap(screw, name)
        sc = design.get(screw)
        sc.meta.setdefault("threads_into", []).append(name)
    return c


def clearance_hole(size: str) -> float:
    """Clearance hole for a made METAL part (ISO 273 medium). For a printed part use printed_clearance_hole."""
    return SCREW[size][4]


# ISO 273 medium clearance (mm) and the FDM allowance on the diameter for printed clearance holes (owner's practice,
# docs/DESIGN_GUIDELINES.md, Fasteners and threads): vertical holes (axis along the print direction) print undersize, so
# they are drawn medium + 0.2; holes whose axis lies in the build plane are drawn medium + 0.3 with a teardrop or flat
# top. Starting values: calibrate on the printer with a coupon (M3 holes 3.4 to 3.8 in 0.1 steps). Practice rule DG-05.
ISO273_MEDIUM = {"M2": 2.4, "M2.5": 2.9, "M3": 3.4, "M4": 4.5, "M5": 5.5, "M6": 6.6, "M8": 9.0}
FDM_HOLE_ALLOWANCE = {"vertical": 0.2, "in_plane": 0.3}


def printed_clearance_hole(size: str, in_plane: bool = False, allowance: float | None = None) -> float:
    """Clearance hole to DRAW in a printed part: ISO 273 medium + the FDM allowance (0.2 mm for a vertical hole, 0.3 mm
    for one whose axis lies in the build plane). M2.5 3.1, M3 3.6, M4 4.7, M5 5.7, M6 6.8 (vertical)."""
    a = FDM_HOLE_ALLOWANCE["in_plane" if in_plane else "vertical"] if allowance is None else float(allowance)
    return round(ISO273_MEDIUM[size] + a, 2)


def tap_drill(size: str) -> float:
    return SCREW[size][5]


def add_washer(design: Design, name: str, size: str, at, direction=(0, 0, 1), body: str = "world",
               screw: str | None = None, series: str = "normal") -> Component:
    """Place a flat washer (mechloop.parts.hardware.washer_flat) with the face that bears on the part at `at`, the
    washer extending along `direction` (towards the head or nut that sits on it). `screw=` records which screw it
    belongs to (a join, and the screw then holds it). series="large" for slots and soft seats."""
    from .hardware import washer_flat

    dvec = Vector(*direction).normalized()
    c = place(design, name, washer_flat(size, series), Location(Plane(origin=at, z_dir=dvec)), body=body)
    if screw:
        design.join(screw, name, "washer")
        for f in design.fasteners:
            if f.name == screw and name not in f.clamps:
                f.clamps = tuple(f.clamps) + (name,)
    return c


def add_screw(design: Design, name: str, size: str, length: float, at, direction=(0, 0, -1),
              body: str = "world", threads_into: str | list[str] | None = None, clamps=(),
              tnut: bool = False, washer: bool | str = False, insert: bool | str = False,
              locking: str | None = None, insert_reason: str | None = None, head: str = "socket",
              washers: int = 1, tnut_stock: "Stock | None" = None) -> Component:
    """Place a cap screw with the underside of its head at `at`, pointing along `direction`.
    Registers it as a Fastener (tool access is checked), allows the thread to overlap the
    part(s) it screws into and records that it holds them. tnut=True means it threads into
    a T-nut in that part's slot. In a design with `design.tnut_style = "drop_in"` the T-nut is a real part,
    `<name>_tnut` (catalogue `tnut_2020`, SKU TNUT-2020-<size>), placed in the slot under the lips on the screw's axis,
    joined to the screw and the extrusion; without it (older designs) the T-nut is only a BOM line.
    washers=2 with washer=True stacks two washers under the head (`<name>_washer`, `<name>_washer_2`): `at` is still the
    face the first one bears on.
    washer=True (or "large"): a catalogue flat washer `<name>_washer` goes under the head. `at` is then the face the
    WASHER bears on; the head sits one washer thickness higher, so the same screw reaches that much less far into its
    thread (the engagement check sees it: choose the length with the washer in).
    insert=True: it threads into a heat-set insert in the (printed) part it threads into; the manufacture verifier checks
    that part's perimeters against the insert maker's minimum wall (mechloop.printsettings.INSERT_WALL_MIN). The owner's
    practice (practice rule DG-04) wants a through-bolt and nut in printed parts; a heat-set insert is accepted only with
    a written reason, insert_reason="no access for a nut inside the hood" (at least 20 characters).
    insert="steel" (wire thread insert / Helicoil / Keensert, `INSERT-STEEL-<size>`) or "pem" (self-clinching nut in sheet,
    `PEM-NUT-<size>`): the thread in an aluminium part we make is not tapped into the aluminium (practice rule DG-02).
    locking="nyloc" | "adhesive" | "all_metal" | "serrated" | "jam": the screw's locking provision (practice rule
    FST-070), recorded in meta["locking"]; "adhesive" adds a THREADLOCKER line to the BOM."""
    # head="countersunk": an ISO 10642 screw; `at` is then the surface its head lies flush in (the countersink's mouth),
    # not the underside of a head. The washer / seat check does not judge countersunk heads (bearing.py).
    if head == "flanged_button":        # v11: ISO 7380-2, the collar bears (covers a slot without a washer)
        from .batch10 import bhcs_flanged

        st = bhcs_flanged(size, length)
    else:
        st = fhcs(size, length) if head == "countersunk" else shcs(size, length)
    dvec = Vector(*direction).normalized()
    washer_at = None
    if washer:
        from .hardware import WASHER

        series = "large" if washer == "large" else "normal"
        washer_at = tuple(at)
        at = tuple(Vector(*at) - dvec * WASHER[series][size][2] * max(1, int(washers)))
    loc = Location(Plane(origin=at, z_dir=-dvec))
    c = place(design, name, st, loc, body=body, thread_d=SCREW[size][0],
              threads_into=[threads_into] if isinstance(threads_into, str) else list(threads_into or []),
              tnut=tnut)
    if insert:
        kind = "heatset" if insert is True else str(insert).lower()
        if kind in ("heatset", "heat_set", "heat-set"):
            c.meta["insert"] = True
            if insert_reason:
                c.meta["insert_reason"] = str(insert_reason)
            design.bom_extra(f"INSERT-HEATSET-{size}", 1, 0.08)
        elif kind in ("steel", "helicoil", "keensert", "wire"):
            c.meta["thread_insert"] = "steel"
            design.bom_extra(f"INSERT-STEEL-{size}", 1, 0.3)
        elif kind in ("pem", "clinch", "self_clinching"):
            c.meta["thread_insert"] = "pem"
            design.bom_extra(f"PEM-NUT-{size}", 1, 0.25)
        else:
            raise ValueError(f"add_screw('{name}'): insert must be True / 'heatset', 'steel' or 'pem', not {insert!r}")
    if locking:
        c.meta["locking"] = str(locking)
        if str(locking).lower() in ("adhesive", "threadlocker", "loctite") and "THREADLOCKER-MEDIUM" not in design.bom_extras:
            design.bom_extra("THREADLOCKER-MEDIUM", 1, 6.0)       # one bottle for the machine
    head_top = Vector(*at) - dvec * st.interfaces["head_h"]
    design.fasteners.append(Fastener(name, tuple(-dvec), tuple(head_top),
                                     tool_diameter=st.interfaces["hex_key"] * 1.6, tool_length=50.0,
                                     clamps=tuple(clamps)))
    if threads_into:
        for t in ([threads_into] if isinstance(threads_into, str) else threads_into):
            design.allow_overlap(name, t, max_volume=math.pi * (SCREW[size][0] / 2) ** 2 * length)
            design.join(name, t, "tnut" if tnut else "thread")
    if tnut:
        if getattr(design, "tnut_style", None):
            _place_tnut(design, c, name, size, length, at, dvec, body,
                        [threads_into] if isinstance(threads_into, str) else list(threads_into or []), stock=tnut_stock)
        else:
            design.bom_extra(f"TNUT-2020-{size}", 1, 0.15)
    if washer_at is not None:
        from .hardware import WASHER

        series = "large" if washer == "large" else "normal"
        for k in range(max(1, int(washers))):
            add_washer(design, f"{name}_washer" + (f"_{k + 1}" if k else ""), size,
                       tuple(Vector(*washer_at) - dvec * WASHER[series][size][2] * k), tuple(-dvec), body=body, screw=name,
                       series=series)
    return c


def _place_tnut(design: Design, screw: Component, name: str, size: str, length: float, at, dvec, body: str, targets: list,
                stock: "Stock | None" = None) -> None:
    """The drawn T-nut of a tnut=True screw: `<name>_tnut` in the slot of the extrusion the screw enters, its bearing
    face against the underside of the slot's lips, centred on the screw's axis. The simulation solid of the extrusion
    has a plain slot with no T cavity, so the nut's wings overlap that solid by design (allowed, and limited to the
    nut's own volume); what the screw may overlap is cut down from "the whole screw" to nothing here (the interference
    verifier works out what the real slot allows)."""
    from .tslot import slot_frame, tnut_2020

    st = stock if stock is not None else tnut_2020(size)      # v12: a bracket set's own nut (MISUMI HNTP5-5) where given
    known = {c.name for c in design.components}
    if any(t not in known for t in targets):
        raise ValueError(f"add_screw('{name}', tnut=True): {[t for t in targets if t not in known]} is not in the design yet. With "
                         f"design.tnut_style set, place the extrusion before the screws that go into its slot.")
    ext = next((design.get(t) for t in targets if "slot" in (design.get(t).meta.get("interfaces") or {})), None)
    if ext is None:
        raise ValueError(f"add_screw('{name}', tnut=True): none of {targets} is a slotted extrusion (threads_into must name it).")
    fr = slot_frame(ext, tuple(at), tuple(dvec))
    if fr is None:
        raise ValueError(f"add_screw('{name}', tnut=True): the screw does not point square into a slot face of '{ext.name}'.")
    slot = ext.meta["interfaces"]["slot"]
    import numpy as np

    n = fr["normal"]
    tip = np.array(tuple(at), dtype=float) + np.array(tuple(dvec), dtype=float) * length
    depth_tip = fr["depth"] + length                      # `at` is the underside of the head: depth there is -(grip)
    on_face = tip + n * depth_tip                         # the screw's axis where it crosses the extrusion's face
    origin = on_face - n * slot["lip"]
    tn = place(design, f"{name}_tnut", st, Location(Plane(origin=tuple(origin), x_dir=tuple(fr["along"]), z_dir=tuple(n))),
               body=body, tnut_of=name, slot_of=ext.name)
    screw.meta["tnut_part"] = tn.name
    design.join(name, tn.name, "thread")
    design.join(tn.name, ext.name, "drop-in T-nut in the slot")
    design.allow_overlap(name, tn.name)
    design.allow_overlap(tn.name, ext.name, max_volume=float(st.shape.volume) + 1.0)
    r_ = SCREW[size][0] / 2
    for t in targets:      # the screw itself: no blanket excuse any more, only what the real slot is deeper than the drawn one
        design.allow_overlap(name, t, max_volume=math.pi * r_ * r_ * max(0.0, slot["depth"] - slot["sim_depth"]))


@part
def corner_bracket_2020() -> Stock:
    """Cast corner bracket for 2020 extrusion. Local frame: inside corner at origin, legs along +X and +Y, 17 mm wide
    centred on Z=0 (was drawn 18 wide; the CAD model and the usual part are 17)."""
    from build123d import Polygon, extrude

    tri = extrude(Polygon((0, 0), (20, 0), (0, 20), align=None), 8.5, both=True)
    detail, model = details.corner_bracket_2020()
    return Stock(tri, "BRKT-2020", "2020 corner bracket", 0.012, material="al6061", cost_usd=0.6, detail=detail, model=model)


# A corner-bracket leg on a T-slot, drawn (design.tnut_style set). The casting's CAD model has a 6 mm wide slot from 7.0 to
# 16.1 mm from the corner in each leg (so an M5 can sit 10.0 to 13.1 mm out) between side webs 12 mm apart. Two cap-screw
# heads in the two legs clear each other only with no washer under them (one at 12.25 mm or more), and their drivers
# only with both at 11.2 mm or more; with one or two washers under each head there is no pair of positions inside the
# slots. So: M5 x 8, no washer, 11.5 and 13.1 mm out (heads 0.85 mm apart; at 12.5 the 0.25 mm gap closes in 1 build in 15). The bare head on the 6 mm slot is a small seat (ratings:
# screw_head_seat_too_small); a flanged button-head screw (ISO 7380-2) is what this casting wants and is not in the catalogue.
BRACKET_SLOT_LEG = {"size": "M5", "length": 8, "washers": 0, "offsets": (11.5, 13.1)}
BRACKET_CAD_SLOT = (10.0, 13.1, 3.0)        # centres of the slot's end radii and that radius, measured on the CAD model


def add_corner_bracket(design: Design, name: str, a: str, b: str, corner, u, v, body: str = "world",
                       screw_offset: float = 11.5, slot_leg: dict | None = None) -> Component:
    """Brace two perpendicular members: bracket's inside corner at `corner`, legs along
    unit directions u (lying on part a) and v (lying on part b).

    On a T-slot extrusion the leg's M5 screw and T-nut are added to the BOM and recorded as the joint
    (they sit in the slot and are not drawn).

    On anything else (a plate, a printed part) there is no slot and no T-nut, so the leg is through-bolted
    and the hardware is real: an M5 cap screw `<name>_screw` (`_screw_a` on the first leg) with its head
    inside the casting, through the casting's slot and the part, and a hex nut `<name>_nut` on the far
    side. They are components, so interference, driver access, thread and assembly order are checked.
    In a design with `design.tnut_style = "drop_in"` a leg on a T-slot extrusion is drawn too: an M5 cap screw
    `<name>_screw_a` / `<name>_screw` with flat washers under its head (the casting's leg is slotted) into a drop-in T-nut
    `<..>_tnut` in the extrusion's slot, checked like every other T-nut screw. Defaults (BRACKET_SLOT_LEG): M5 x 8 with no
    washer, 11.5 mm from the corner on the first leg and 13.1 mm on the second, so the two heads and their drivers clear
    each other inside the casting's slots (10.0 to 13.1 mm); `slot_leg={"length": .., "washers": .., "offsets": (.., ..)}`
    overrides. In such a design the casting's slots are drawn as its CAD model has them.
    The part needs its own M5 clearance hole `screw_offset` mm from the corner along the leg (the
    casting's slot runs from 7 to 16 mm; with cap screws in both legs keep one of them at 12.3 mm or
    more so the heads clear each other). For such a bracket the simulation solid is the casting as it
    is (3 mm legs, 2.5 mm side webs, slotted, open between the webs) instead of the filled prism,
    because the screw head and the driver go where the prism has metal and the casting has none.
    Raises ValueError if the leg does not lie on the part or the part is too thick to through-bolt."""
    import dataclasses

    from build123d import Polygon, extrude

    uv, vv = Vector(*u).normalized(), Vector(*v).normalized()
    origin = Vector(*corner)
    is_slot = {p: "slot_width" in (design.get(p).meta.get("interfaces") or {}) for p in (a, b)}
    stock = corner_bracket_2020()
    LEG_T, WEB_IN, SLOT = 3.0, 6.0, (7.0, 16.0, 3.0)      # from the casting's CAD model (details.corner_bracket_2020)
    drawn = bool(getattr(design, "tnut_style", None))
    sl = {**BRACKET_SLOT_LEG, **(slot_leg or {})}
    if drawn or not all(is_slot.values()):
        if not 7.0 <= screw_offset <= 16.0:
            raise ValueError(f"add_corner_bracket('{name}'): screw_offset {screw_offset} mm is outside the casting's slot (7 to 16 mm).")
        solid = stock.shape - extrude(Polygon((LEG_T, LEG_T), (20 - LEG_T, LEG_T), (LEG_T, 20 - LEG_T), align=None), WEB_IN, both=True)
        s0, s1, sr = BRACKET_CAD_SLOT if drawn else SLOT
        if drawn:
            for off in ([screw_offset] if not all(is_slot.values()) else []) + [sl["offsets"][i] for i, p_ in enumerate((a, b)) if is_slot[p_]]:
                if not s0 - 1e-6 <= off <= s1 + 1e-6:
                    raise ValueError(f"add_corner_bracket('{name}'): a screw {off} mm from the corner is outside the casting's slot "
                                     f"(an M5 sits {s0:g} to {s1:g} mm out).")
        along_x = (Pos((s0 + s1) / 2, 0, 0) * Box(s1 - s0, 2 * LEG_T, 2 * sr) + Pos(s0, 0, 0) * Rot(90, 0, 0) * Cylinder(sr, 2 * LEG_T)
                   + Pos(s1, 0, 0) * Rot(90, 0, 0) * Cylinder(sr, 2 * LEG_T))
        along_y = (Pos(0, (s0 + s1) / 2, 0) * Box(2 * LEG_T, s1 - s0, 2 * sr) + Pos(0, s0, 0) * Rot(0, 90, 0) * Cylinder(sr, 2 * LEG_T)
                   + Pos(0, s1, 0) * Rot(0, 90, 0) * Cylinder(sr, 2 * LEG_T))
        if drawn or not is_slot[a]:
            solid -= along_x
        if drawn or not is_slot[b]:
            solid -= along_y
        stock = dataclasses.replace(stock, shape=solid)
    c = place(design, name, stock, Location(Plane(origin=corner, x_dir=u, z_dir=uv.cross(vv))), body=body)
    # (part, along its leg, out of the part's face, screw suffix, nut suffix)
    for part_name, along, out, s_sfx, n_sfx in ((a, uv, vv, "_screw_a", "_nut_a"), (b, vv, uv, "_screw", "_nut")):
        if is_slot[part_name] and drawn:
            off = sl["offsets"][0 if s_sfx == "_screw_a" else 1]
            foot = origin + along * off
            add_screw(design, name + s_sfx, sl["size"], sl["length"], at=tuple(foot + out * LEG_T), direction=tuple(-out), body=body,
                      threads_into=part_name, tnut=True, clamps=(name,), washer=bool(sl["washers"]), washers=max(1, int(sl["washers"])),
                      locking=sl.get("locking"), head=sl.get("head", "socket"))
            design.get(name + s_sfx).meta["bracket_leg_of"] = name
            design.join(name, part_name, "m5_tnut")
            continue
        if is_slot[part_name]:
            design.join(name, part_name, "m5_tnut")
            design.bom_extra("SHCS-M5x8", 1, 0.08)
            design.bom_extra("TNUT-2020-M5", 1, 0.15)
            continue
        # how thick is the part under the leg, measured around the screw axis from the face the leg lies on
        foot = origin + along * screw_offset
        probe = Plane(origin=tuple(foot), z_dir=tuple(-out)) * Pos(0, 0, 20.0) * Cylinder(6.0, 40.0)
        under = design.get(part_name).shape & probe
        depths = []
        for so in (under.solids() if under is not None else []):
            bb = so.bounding_box()
            ext = [-(Vector(x, y, z) - foot).dot(out) for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
                   for z in (bb.min.Z, bb.max.Z)]
            if min(ext) < 0.05:
                depths.append(max(ext))
        if not depths:
            raise ValueError(f"add_corner_bracket('{name}'): the leg along {tuple(along)} does not lie on '{part_name}' at "
                             f"{tuple(round(x, 2) for x in foot)}; '{part_name}' is not an extrusion, so the leg is bolted "
                             f"through it there and needs material (and an M5 clearance hole) under it.")
        thick = max(depths)
        nut_h = NUT["M5"][1]
        length = next((L for L in (8, 10, 12, 16, 20, 25, 30) if L >= LEG_T + thick + nut_h), None)
        if length is None:
            raise ValueError(f"add_corner_bracket('{name}'): '{part_name}' is {thick:.1f} mm thick under the leg, too thick to "
                             f"through-bolt with a nut. It is not a T-slot extrusion, so there is no T-nut either: tap it and "
                             f"fasten the bracket yourself with add_screw(threads_into='{part_name}'), or use an extrusion.")
        add_screw(design, name + s_sfx, "M5", length, at=tuple(foot + out * LEG_T), direction=tuple(-out), body=body,
                  clamps=(name, part_name))
        add_nut(design, name + n_sfx, "M5", at=tuple(foot - out * thick), direction=tuple(-out), body=body,
                screw=name + s_sfx)
        design.join(name, part_name, "m5_through_bolt")
    return c


# ----------------------------------------------------- more catalog parts (registered on import)
from .hardware import bed_column_silicone, spacer_lengths, spacer_round, washer_toothed  # noqa: E402,F401
from .tslot import slot_2020, tnut_2020  # noqa: E402,F401
from .toolhead import extruder_roto, hotend_revo, hotend_v6  # noqa: E402,F401
from .probes import add_probe_nuts, e2e_nut, probe_omron_e2e  # noqa: E402,F401
from .batch6 import (fan_cg3010u24, leadscrew_motor_17e19, leadscrew_nut_17e19, manta_m5p, mgn15_rail,  # noqa: E402,F401
                     mgn15h_carriage, print_sheet_pei180)
from .batch7 import leadscrew_motor_17e19_ab4, leadscrew_screw_17e19_ab4, octopus_v11  # noqa: E402,F401
from .batch8 import add_thumb_nut, die_spring_dj8x20, print_sheet_pei257, thumb_nut_din466  # noqa: E402,F401
from .batch9 import print_sheet_pei235  # noqa: E402,F401
from .batch10 import bhcs_flanged, blower_bfb0524hh, blower_gdb4010, leadscrew_nut_pom_ab4, print_sheet_pei220  # noqa: E402,F401
from . import batch12  # noqa: E402,F401  (printer_v12 parts: mechloop.parts.batch12)
