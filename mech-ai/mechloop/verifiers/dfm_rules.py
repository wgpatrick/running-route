"""The numbers the manufacturability checks judge against, each with where it came from.

Three layers, later ones winning:

1. RULES: general practice from fabricators' published design guides. Each rule is one limit with its
   source URL. Where no guide states a number the rule is mechloop's own, and says so.
2. A shop profile (SHOPS), chosen with `design.manufacturing["shop"]`: that shop's stocked thicknesses,
   part sizes and bend tooling replace the general figures.
3. Overrides: `design.manufacturing["limits"] = {"fdm.bridge_max_mm": 60}` for the whole design, or
   `component.meta["dfm"] = {"limits": {...}}` for one part. Use them for your own machine or a quote.

Severity: "error" means the process cannot make the feature as drawn; "warning" means it can, at a cost
(a secondary operation, special tooling, support material, hand work) or a risk.

The approach (one cited rule table per process, a shop's own limits kept apart from general practice,
value / limit / source on every finding) follows text-to-cad (github.com/earthtojake/text-to-cad, MIT);
no code was copied. Pages were read on 2026-11-14.
"""
from __future__ import annotations

from dataclasses import dataclass

ACCESSED = "2026-11-14"

SOURCES = {
    "scs-cutting": "https://sendcutsend.com/guidelines/laser-cutting/",
    "scs-bending": "https://sendcutsend.com/guidelines/bending/",
    "scs-minmax": "https://sendcutsend.com/materials/min-max/",
    "scs-processing": "https://sendcutsend.com/materials/processing-min-max/",
    "scs-tapping": "https://sendcutsend.com/guidelines/tapping/",
    "scs-countersinking": "https://sendcutsend.com/guidelines/countersinking/",
    "scs-5052": "https://sendcutsend.com/materials/5052-aluminum/",
    "hubs-sheet": "https://www.hubs.com/guides/sheet-metal-fabrication/",
    "hubs-cnc": "https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/",
    "hubs-fdm": "https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/",
    "hubs-fdm-service": "https://www.hubs.com/3d-printing/fdm/",
    "hubs-geometry": "https://www.hubs.com/knowledge-base/3d-printing-geometry-restrictions/",
    "hubs-thin-walls": "https://www.hubs.com/knowledge-base/dfm-tips-for-3d-printed-parts-with-thin-walls/",
    "hubs-fasteners": "https://www.hubs.com/knowledge-base/how-assemble-3d-printed-parts-threaded-fasteners/",
    "protolabs-cnc": "https://www.protolabs.com/services/cnc-machining/cnc-milling/design-guidelines/",
    "t2c-sheet": "text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py",
    "t2c-cnc": "text-to-cad: packages/cad/src/cad/_internal/dfm/cnc.py",
    "t2c-printing": "text-to-cad: packages/cad/src/cad/_internal/dfm/printing.py",
    "t2c-holes": "text-to-cad: packages/cad/src/cad/build123d/_dfm_cnc_holes.py",
    "own": "mechloop's own figure: no published guide read here states one",
}


@dataclass(frozen=True)
class Rule:
    id: str
    limit: float
    unit: str
    severity: str        # error | warning | info
    source: str          # key of SOURCES
    what: str            # the measured figure, in words
    note: str = ""       # how the source words it, or what an own figure rests on

    @property
    def source_text(self) -> str:
        return SOURCES[self.source]


def _r(id_, limit, unit, severity, source, what, note=""):
    return Rule(id_, limit, unit, severity, source, what, note)


_RULES = [
    # ------------------------------------------------------------------ 2D cut (laser / waterjet / router)
    _r("sheet.hole_min_t_ratio", 0.5, "x thickness", "error", "scs-cutting", "smallest hole or cut-out, laser",
       "Laser cutting: holes and cut-outs at least 50% of material thickness; smaller ones distort, char or fail to cut"),
    _r("sheet.hole_recommended_t_ratio", 1.0, "x thickness", "warning", "hubs-sheet", "hole diameter",
       "Specify hole diameters larger than the sheet thickness; smaller is possible but may deform or be inaccurate"),
    _r("sheet.hole_min_waterjet_mm", 1.78, "mm", "error", "scs-cutting", "smallest hole or cut-out, waterjet",
       "no less than 0.070 in for most waterjet cut parts"),
    _r("sheet.hole_min_router_mm", 3.175, "mm", "error", "scs-cutting", "smallest hole or cut-out, CNC router",
       "0.125 in, the bit diameter"),
    _r("sheet.hole_to_edge_t_ratio", 1.0, "x thickness", "warning", "hubs-sheet", "material between a hole and the edge",
       "Holes should be at least the sheet's thickness from the edge"),
    _r("sheet.hole_spacing_t_ratio", 2.0, "x thickness", "warning", "hubs-sheet", "material between two holes",
       "Space holes at least 2 times the sheet thickness apart"),
    _r("sheet.feature_width_t_ratio", 1.0, "x thickness", "warning", "t2c-sheet", "width of a slot, tab or neck",
       "text-to-cad applies Hubs's hole-to-edge minimum and Protolabs' notch/tab minimum (the thickness) to any web or slot"),
    _r("sheet.kerf_laser_mm", 0.3, "mm", "error", "hubs-sheet", "laser kerf",
       "laser cutting produces the lowest kerf at 0.3 mm on average; a slot narrower than the kerf cannot be cut"),
    _r("sheet.kerf_waterjet_mm", 0.8, "mm", "error", "scs-cutting", "waterjet stream",
       "0.032 in stream diameter (Hubs gives 0.5-1 mm)"),
    _r("sheet.kerf_router_mm", 3.175, "mm", "error", "scs-cutting", "router bit", "0.125 in bit"),
    _r("sheet.inside_radius_laser_mm", 0.15, "mm", "warning", "scs-cutting", "inside corner radius, laser",
       "approximately the kerf width (very small): a drawn-sharp corner comes out practically sharp"),
    _r("sheet.inside_radius_waterjet_mm", 0.81, "mm", "warning", "scs-cutting", "inside corner radius, waterjet", "0.032 in"),
    _r("sheet.inside_radius_router_mm", 1.6, "mm", "warning", "scs-cutting", "inside corner radius, CNC router",
       "0.063 in, the radius of a 0.125 in bit; use dog-bones where a square part must seat"),
    _r("sheet.thickness_min_mm", 0.5, "mm", "warning", "hubs-sheet", "sheet thickness", "recommended range 0.5-10 mm for laser cutting"),
    _r("sheet.thickness_max_laser_mm", 10.0, "mm", "warning", "hubs-sheet", "sheet thickness", "recommended range 0.5-10 mm for laser cutting"),
    _r("sheet.thickness_limit_mm", 25.4, "mm", "error", "t2c-sheet", "sheet thickness",
       "text-to-cad's own floor: sheet lasers stop near an inch of steel; thicker plate is machined"),
    _r("sheet.max_long_mm", 3048.0, "mm", "warning", "t2c-sheet", "flat part's long side",
       "a standard 5 x 10 ft sheet, the largest standard blank (text-to-cad, citing Xometry)"),
    _r("sheet.max_short_mm", 1524.0, "mm", "warning", "t2c-sheet", "flat part's short side", "a standard 5 x 10 ft sheet"),
    _r("sheet.min_long_mm", 9.5, "mm", "warning", "scs-minmax", "flat part's long side",
       "SendCutSend's smallest laser part in thin stock is 0.25 x 0.375 in; smaller parts fall through the bed or need tabs"),
    _r("sheet.min_short_mm", 6.35, "mm", "warning", "scs-minmax", "flat part's short side", "0.25 in"),
    _r("sheet.removed_max_fraction", 0.5, "fraction", "warning", "scs-cutting", "share of the blank cut away inside the outline",
       "keep material removal under 50% (said of routed parts: grilles shift or break while being cut)"),
    _r("sheet.countersink_min_thickness_mm", 3.18, "mm", "warning", "scs-countersinking", "thickness of a countersunk sheet",
       "materials must be at least 0.125 in thick for countersinking"),
    _r("sheet.tap_min_thickness_mm", 1.5, "mm", "warning", "scs-tapping", "thickness of a tapped sheet",
       "tapping offered from 0.059 in thick"),
    # bends
    _r("sheet.bend_radius_t_ratio", 1.0, "x thickness", "warning", "hubs-sheet", "inside bend radius",
       "Keep the interior bend radii at least as large as the material thickness"),
    _r("sheet.bend_thickness_max_mm", 6.0, "mm", "warning", "hubs-sheet", "thickness of a bent sheet", "0.5-6 mm recommended for bending"),
    _r("sheet.flange_min_t_ratio", 2.0, "x thickness (plus the inside radius)", "error", "t2c-sheet",
       "flange height from the outside of the bend",
       "minimum bend height 2 t + r (Hubs's figure as text-to-cad reads it, from the outside mould line)"),
    _r("sheet.hole_to_bend_t_ratio", 2.0, "x thickness", "warning", "hubs-sheet", "hole edge to the start of the bend radius",
       "Ensure holes are at least 2 times the sheet thickness from the start of the bend radius, or they distort"),
    _r("sheet.bend_radius_max_t_ratio", 10.0, "x thickness", "warning", "t2c-sheet", "inside bend radius",
       "text-to-cad's own line: a radius past 10 t is bump-formed or rolled, not one hit of the brake"),
    # ------------------------------------------------------------------------------- FDM
    _r("fdm.overhang_angle_deg", 45.0, "deg from vertical", "warning", "hubs-fdm", "overhang angle",
       "an overhang can usually be printed up to 45 deg; above that support is required"),
    _r("fdm.support_area_mm2", 150.0, "mm2", "warning", "own", "area needing support in the chosen orientation",
       "below this the support is a few minutes of clean-up; above it, it costs material, time and surface finish"),
    _r("fdm.bridge_clean_mm", 5.0, "mm", "info", "hubs-fdm", "bridge span",
       "sagging or marks are always present to some extent unless the bridge is less than 5 mm"),
    _r("fdm.bridge_max_mm", 30.0, "mm", "warning", "own", "bridge span printed without support",
       "a desktop printer with part cooling bridges a few tens of mm with visible sag; set your printer's figure"),
    _r("fdm.horizontal_hole_max_mm", 10.0, "mm", "warning", "t2c-printing", "diameter of a horizontal round hole",
       "text-to-cad's own figure: up to 10 mm a horizontal hole prints unsupported; wider, its crown sags"),
    _r("fdm.wall_min_mm", 0.8, "mm", "error", "hubs-thin-walls", "wall thickness",
       "FDM minimum wall 0.8 mm supported and free (two beads of a 0.4 mm nozzle)"),
    _r("fdm.wall_beads", 2.0, "x nozzle", "error", "t2c-printing", "wall thickness",
       "text-to-cad's scaling of Hubs's 0.8 mm: two beads of the nozzle actually fitted"),
    _r("fdm.feature_min_mm", 2.0, "mm", "warning", "hubs-fdm-service", "pin or boss diameter",
       "minimum feature size 2.0 mm recommended; pins under 5 mm are perimeters only and snap off"),
    _r("fdm.hole_min_mm", 2.0, "mm", "warning", "hubs-fdm-service", "hole diameter",
       "minimum hole diameter 2.0 mm recommended; holes print undersize, drill critical ones after printing"),
    _r("fdm.slenderness_max", 6.0, "height / sqrt(bed contact area)", "warning", "own", "height over footprint",
       "tall parts on a small footprint wobble under the nozzle or come off the bed"),
    _r("fdm.bed_contact_min_fraction", 0.1, "fraction of the part's shadow", "warning", "own", "first-layer contact area",
       "a part that touches the bed on a small share of its outline needs a brim, a raft or support to stay put"),
    _r("fdm.thread_wall_d_ratio", 1.0, "x screw diameter", "warning", "hubs-fasteners", "wall around a threaded hole or insert",
       "the minimum wall thickness around a thread should match the diameter of the fastener (M5: 5 mm)"),
    _r("fdm.layer_load_fraction", 0.5, "share of the load along the build direction", "warning", "hubs-fdm",
       "load pulling layers apart",
       "FDM parts are inherently weaker in one direction due to layer orientation; the share that triggers this is mechloop's own"),
    # ------------------------------------------------------------------------------- CNC milling
    _r("cnc.corner_radius_min_mm", 1.25, "mm", "warning", "hubs-cnc", "inside corner radius",
       "most shops machine with tools down to 2.5 mm diameter; below that is micro-machining"),
    _r("cnc.corner_depth_ratio", 4.0, "depth / tool diameter", "warning", "hubs-cnc", "corner depth over the tool that fits it",
       "end mills have a cutting length of typically 3-4 times their diameter; recommended corner radius is 1/3 of cavity depth"),
    _r("cnc.corner_depth_limit", 30.0, "depth / tool diameter", "error", "hubs-cnc", "corner depth over the tool that fits it",
       "a tool diameter to cavity depth ratio of up to 30:1 is possible using specialised tooling"),
    _r("cnc.pocket_depth_ratio", 4.0, "depth / width", "warning", "hubs-cnc", "pocket or slot depth over its width",
       "recommended cavity depth: 4 times cavity width"),
    _r("cnc.pocket_depth_limit", 30.0, "depth / width", "error", "hubs-cnc", "pocket or slot depth over its width", "30:1 with specialised tooling"),
    _r("cnc.slot_min_mm", 2.5, "mm", "warning", "hubs-cnc", "slot or gap width", "tools down to 2.5 mm are standard"),
    _r("cnc.wall_min_metal_mm", 0.5, "mm", "error", "hubs-cnc", "wall thickness", "feasible: 0.5 mm (metals)"),
    _r("cnc.wall_recommended_metal_mm", 0.8, "mm", "warning", "hubs-cnc", "wall thickness", "recommended: 0.8 mm (metals)"),
    _r("cnc.wall_min_plastic_mm", 1.0, "mm", "error", "hubs-cnc", "wall thickness", "feasible: 1.0 mm (plastics)"),
    _r("cnc.wall_recommended_plastic_mm", 1.5, "mm", "warning", "hubs-cnc", "wall thickness", "recommended: 1.5 mm (plastics)"),
    _r("cnc.hole_depth_ratio", 10.0, "depth / diameter", "warning", "hubs-cnc", "hole depth over diameter",
       "recommended 4, typical 10; deeper needs specialised drills"),
    _r("cnc.hole_depth_limit", 40.0, "depth / diameter", "error", "hubs-cnc", "hole depth over diameter", "feasible: 40 times nominal diameter"),
    _r("cnc.hole_min_mm", 1.0, "mm", "warning", "hubs-cnc", "hole diameter", "feasible: any diameter larger than 1 mm; smaller is micro-drilling"),
    _r("cnc.drill_tolerance_mm", 0.005, "mm", "warning", "t2c-holes", "distance from the nearest standard drill",
       "Hubs: use a standard drill bit size; text-to-cad's tolerance for 'is that drill'"),
    _r("cnc.drill_max_mm", 13.0, "mm", "info", "own", "largest hole judged as drilled",
       "jobber drills in 0.1 mm steps stop near 13 mm; larger holes are milled or bored, any diameter"),
    _r("cnc.thread_depth_ratio", 3.0, "x diameter", "warning", "hubs-cnc", "thread length over diameter",
       "threads longer than 3 times the nominal diameter are unnecessary"),
    _r("cnc.thread_min_mm", 2.0, "mm", "warning", "hubs-cnc", "thread size", "taps cut threads down to M2 (Protolabs supports M2 to M12)"),
    _r("cnc.blind_tap_runout_d_ratio", 1.5, "x diameter", "warning", "hubs-cnc", "unthreaded depth below a tapped blind hole",
       "for threads smaller than M6 add an unthreaded length of 1.5 times the nominal diameter at the bottom of the hole"),
    _r("cnc.setups_max", 3.0, "set-ups", "warning", "own", "set-ups on a 3-axis mill",
       "each side a cutter must face is a re-fixturing; text-to-cad warns past five, Hubs says three to four rotations"),
    _r("cnc.part_max_mm", 2000.0, "mm", "warning", "t2c-cnc", "longest side", "past a general shop's mill (text-to-cad, citing Hubs's CNC service page)"),
    _r("cnc.removed_max_fraction", 0.85, "fraction of the stock", "warning", "own", "share of the stock turned into chips",
       "a cost signal, not a limit: consider a nearer-net stock shape or a built-up part"),
    _r("cnc.unreachable_fraction", 0.02, "fraction of the surface", "error", "t2c-cnc", "surface no straight cutter reaches",
       "Hubs: undercuts cannot be machined with standard tools; the 2% tolerance on the sampled surface is text-to-cad's"),
]
RULES: dict[str, Rule] = {r.id: r for r in _RULES}

# ------------------------------------------------------------------------------------------ shops
# Stock a plate or sheet part is cut from, mm. Generic: common metric gauges (mechloop's own list).
GENERIC_SHEET_MM = (0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0)
GENERIC_PLATE_MM = (1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0, 25.0, 30.0, 40.0, 50.0)

# SendCutSend, https://sendcutsend.com/materials/min-max/ : thickness, largest instant-quote part (long, short),
# smallest part (long, short), all mm, fibre laser.
_SCS_CUT = {
    "al6061": [(1.02, (1422.4, 1117.6), (9.5, 6.35)), (1.6, (1422.4, 1117.6), (9.5, 6.35)), (2.03, (1422.4, 1117.6), (9.5, 6.35)),
               (2.54, (1422.4, 762.0), (9.5, 6.35)), (3.18, (1727.2, 1117.6), (9.5, 6.35)), (4.75, (1422.4, 1117.6), (12.7, 12.7)),
               (6.35, (1727.2, 1117.6), (19.05, 12.7)), (7.95, (1422.4, 1117.6), (25.4, 19.05)), (9.53, (1422.4, 1117.6), (25.4, 19.05)),
               (12.7, (1422.4, 1117.6), (25.4, 25.4)), (15.88, (1422.4, 1041.4), (76.2, 76.2)), (19.05, (1422.4, 1041.4), (76.2, 76.2))],
    "al5052": [(1.02, (1727.2, 1117.6), (9.5, 6.35)), (1.6, (1727.2, 1117.6), (9.5, 6.35)), (2.03, (1727.2, 1117.6), (9.5, 6.35)),
               (2.29, (1422.4, 1117.6), (9.5, 6.35)), (2.54, (1727.2, 1117.6), (9.5, 6.35)), (3.18, (1727.2, 1117.6), (9.5, 6.35)),
               (4.75, (1727.2, 1117.6), (19.05, 12.7)), (6.35, (1727.2, 1117.6), (19.05, 12.7)), (7.95, (1422.4, 1117.6), (25.4, 19.05)),
               (9.53, (1422.4, 1117.6), (25.4, 19.05)), (12.7, (1422.4, 1117.6), (25.4, 25.4))],
    "steel": [(0.76, (1422.4, 1117.6), (9.5, 6.35)), (1.23, (1727.2, 1117.6), (9.5, 6.35)), (1.5, (1727.2, 1117.6), (9.5, 6.35)),
              (1.88, (1727.2, 1117.6), (9.5, 6.35)), (2.64, (1727.2, 1117.6), (9.5, 6.35)), (3.02, (1727.2, 1117.6), (9.5, 6.35)),
              (3.5, (1727.2, 1117.6), (9.5, 6.35)), (4.75, (1422.4, 1117.6), (19.05, 12.7)), (6.35, (1422.4, 1117.6), (19.05, 12.7)),
              (7.95, (1422.4, 1117.6), (25.4, 25.4)), (9.53, (1422.4, 1117.6), (25.4, 25.4)), (12.7, (1422.4, 1117.6), (25.4, 25.4))],
    "stainless304": [(0.76, (1422.4, 1117.6), (9.5, 6.35)), (1.23, (1727.2, 1117.6), (9.5, 6.35)), (1.52, (1727.2, 1117.6), (9.5, 6.35)),
                     (1.88, (1727.2, 1117.6), (9.5, 6.35)), (2.54, (1422.4, 1117.6), (9.5, 6.35)), (3.18, (1727.2, 1117.6), (9.5, 6.35)),
                     (4.75, (1422.4, 1117.6), (9.5, 6.35)), (6.35, (1422.4, 1117.6), (9.5, 6.35)), (9.53, (1422.4, 1117.6), (12.7, 12.7)),
                     (12.7, (1422.4, 1117.6), (12.7, 12.7))],
    "brass": [(1.02, (1422.4, 863.6), (9.5, 6.35)), (1.6, (1422.4, 863.6), (9.5, 6.35)), (3.18, (1422.4, 863.6), (9.5, 6.35)),
              (4.75, (1422.4, 863.6), (19.05, 6.35)), (6.35, (1422.4, 863.6), (19.05, 6.35))],
}
# SendCutSend, https://sendcutsend.com/materials/processing-min-max/ (bending, 90 deg or less), inches in the source:
# thickness: (effective inside bend radius, max bend length, min flange after bend measured from the outside of the bend), mm.
# 6061-T6 is not offered for bending (it cracks); 5052 is the bendable aluminium.
_IN = 25.4
_SCS_BEND = {
    "al5052": {1.02: (.024, 44, .286), 1.6: (.035, 44, .303), 2.03: (.045, 44, .313), 2.29: (.032, 44, .326), 2.54: (.125, 44, .463),
               3.18: (.125, 44, .476), 4.75: (.250, 44, .798), 6.35: (.250, 44, 1.371)},
    "steel": {0.76: (.045, 44, .286), 1.23: (.045, 44, .298), 1.5: (.063, 44, .309), 1.88: (.063, 44, .320), 2.64: (.063, 44, .459),
              3.02: (.063, 44, .466), 3.5: (.100, 44, .742), 4.75: (.125, 22, .781), 6.35: (.150, 20, 1.361)},
    "stainless304": {0.76: (.080, 44, .294), 1.23: (.080, 44, .307), 1.52: (.070, 44, .314), 1.88: (.075, 44, .324), 2.54: (.187, 35, .732),
                     3.18: (.150, 40, .740), 4.75: (.130, 36, .784), 6.35: (.225, 18, 1.381)},
    "brass": {1.02: (.040, 44, .292), 1.6: (.040, 44, .308), 3.18: (.060, 33, .471), 4.75: (.095, 18, .782), 6.35: (.130, 25, 1.362)},
}
SCS_BEND = {m: {t: tuple(round(v * _IN, 2) for v in row) for t, row in tab.items()} for m, tab in _SCS_BEND.items()}
# SendCutSend tapping, same page: thickness from (mm): (smallest metric tap, largest metric tap), aluminium 6061.
_SCS_TAP_AL = [(1.6, (2.0, 6.0)), (3.18, (2.0, 10.0)), (4.75, (3.0, 10.0)), (9.53, (5.0, 10.0)), (15.88, (8.0, 10.0))]

SHOPS = {
    "generic": {
        "description": "no particular shop: common metric stock, general design-guide limits",
        "sheet_stock": {"*": GENERIC_SHEET_MM},
        "plate_stock": {"*": GENERIC_PLATE_MM},
        "source": "own",
    },
    "sendcutsend": {
        "description": "SendCutSend laser cutting and bending: inch-gauge stock, per-thickness part sizes and bend tooling",
        "sheet_stock": {m: tuple(r[0] for r in rows) for m, rows in _SCS_CUT.items()},
        "plate_stock": {"*": GENERIC_PLATE_MM},
        "cut_sizes": _SCS_CUT,
        "bend": SCS_BEND,
        "tap_range_al": _SCS_TAP_AL,
        "strict": True,              # a shop's own limits are errors: it will not take the order
        "source": "scs-minmax",
    },
}

# ------------------------------------------------------------------------------------- reference data
# Tap drill for ISO metric coarse threads (nominal minus pitch), and the pitch.
TAP_DRILL = {2.0: (1.6, 0.4), 2.5: (2.05, 0.45), 3.0: (2.5, 0.5), 4.0: (3.3, 0.7), 5.0: (4.2, 0.8), 6.0: (5.0, 1.0),
             8.0: (6.8, 1.25), 10.0: (8.5, 1.5), 12.0: (10.2, 1.75)}
# Typical brass heat-set insert pilot holes for printed parts, mm (hole, insert length). Typical catalogue values, not from a
# page read here: confirm against the insert you buy (Hubs: "for hole sizes refer to the insert manufacturer").
HEAT_SET = {2.0: (3.2, 3.0), 2.5: (4.0, 4.0), 3.0: (4.0, 5.7), 4.0: (5.6, 8.1), 5.0: (6.4, 9.5), 6.0: (8.0, 12.7)}

PLASTICS = {"pla", "petg", "abs", "nylon_pa12", "asa", "tpu", "pc"}

# Rough machining figures for the estimate (mechloop's own assumptions, small 3-axis VMC, for comparing alternatives only).
# material removal rate cm3/min, stock price USD/kg
MACHINING = {"al6061": (12.0, 8.0), "al5052": (12.0, 8.0), "brass": (10.0, 14.0), "steel": (3.0, 3.0), "stainless304": (1.8, 8.0),
             "*plastic": (15.0, 12.0), "*": (3.0, 6.0)}
SHOP_RATE_USD_H = 75.0
SETUP_MIN = 12.0            # per set-up: fixture, touch off
PROGRAM_MIN = 20.0          # once per part number
FILAMENT_USD_KG = 25.0
PRINT_FLOW_MM3_S = 5.0      # 0.4 mm nozzle, 0.2 mm layers, about 60 mm/s
LASER_USD_PER_M = 1.5       # cut length, thin aluminium / steel; pierces extra
DEFAULT_PRINT_VOLUME = (220.0, 220.0, 250.0)   # a common desktop printer (Hubs: typical desktop FDM 200 x 200 x 200, industrial up to 900 x 600 x 900)


def standard_drill(d: float) -> tuple[float, float]:
    """(nearest standard drill, distance to it). Metric jobber series: 0.05 mm steps to 3 mm, 0.1 mm steps to 14 mm,
    0.25 mm steps to 25 mm; and fractional inch by 1/64. (Series as listed by text-to-cad's hole check, after ASME B94.11M.)"""
    cands = []
    step = 0.05 if d < 3.0 else 0.1 if d < 14.0 else 0.25
    cands.append(round(round(d / step) * step, 4))
    inch = round(d / 25.4 * 64) / 64 * 25.4
    cands.append(inch)
    best = min(cands, key=lambda c: abs(c - d))
    return round(best, 3), abs(best - d)


class Limits:
    """The limits in force for one part: general rules, then the shop's, then the design's and the part's overrides."""

    def __init__(self, design=None, component=None):
        man = getattr(design, "manufacturing", None) or {}
        self.shop_name = (component.meta.get("dfm", {}).get("shop") if component is not None else None) or man.get("shop") or "generic"
        if self.shop_name not in SHOPS:
            raise KeyError(f"unknown shop {self.shop_name!r}; known: {sorted(SHOPS)}")
        self.shop = SHOPS[self.shop_name]
        self.over: dict = dict(man.get("limits") or {})
        if component is not None:
            self.over.update(component.meta.get("dfm", {}).get("limits") or {})
        unknown = [k for k in self.over if k not in RULES]
        if unknown:
            raise KeyError(f"unknown DFM rule id(s) in limits override: {unknown}")
        self.man = man
        self.part = (component.meta.get("dfm") or {}) if component is not None else {}

    def __call__(self, rule_id: str) -> float:
        return float(self.over.get(rule_id, RULES[rule_id].limit))

    def rule(self, rule_id: str) -> Rule:
        return RULES[rule_id]

    def source(self, rule_id: str) -> str:
        return "design override" if rule_id in self.over else RULES[rule_id].source_text

    def severity(self, rule_id: str) -> str:
        return RULES[rule_id].severity

    def option(self, group: str, key: str, default=None):
        """A process option: the part's own (meta["dfm"][key]) first, then design.manufacturing[group][key]."""
        if key in self.part:
            return self.part[key]
        return (self.man.get(group) or {}).get(key, default)

    def stock(self, kind: str, material: str) -> tuple:
        tab = self.shop[kind]
        return tuple(tab.get(material) or tab.get("*") or ())

    def data(self, rule_id: str, value, **more) -> dict:
        """The fields every finding carries so nothing has to be read out of its message."""
        r = RULES[rule_id]
        return {"rule": rule_id, "value": round(float(value), 3) if value is not None else None, "limit": round(self(rule_id), 4),
                "unit": r.unit, "source": self.source(rule_id), **more}


def rule_table_markdown() -> str:
    rows = ["| Rule | Limit | Severity | What | Source |", "|---|---|---|---|---|"]
    for r in _RULES:
        rows.append(f"| `{r.id}` | {r.limit:g} {r.unit} | {r.severity} | {r.what}. {r.note} | {r.source_text} |")
    return "\n".join(rows)
