"""How accurately each kind of part is made. Values are typical shop figures (one standard
deviation unless noted), deliberately a little pessimistic, and meant to be replaced with the
supplier's or the machine's own numbers."""
from __future__ import annotations

from ..model import Component

PROCESS = {
    #            feature position   size, fraction   hole diameter: bias, sigma   flatness of a mating face
    #            "pos": a feature against the part's own datum faces. "pattern": one feature against a neighbouring
    #            feature made in the same set-up (hole to hole within one screw pattern), see PATTERN_NOTE.
    "purchased": {"pos": 0.02, "pattern": 0.02, "scale": 0.0001, "hole_bias": 0.00, "hole_sd": 0.01, "flat": 0.01},
    "machined":  {"pos": 0.04, "pattern": 0.02, "scale": 0.0002, "hole_bias": 0.00, "hole_sd": 0.02, "flat": 0.02},
    "sheet":     {"pos": 0.08, "pattern": 0.04, "scale": 0.0005, "hole_bias": 0.00, "hole_sd": 0.04, "flat": 0.10},
    "extrusion": {"pos": 0.15, "pattern": 0.10, "scale": 0.0010, "hole_bias": 0.00, "hole_sd": 0.03, "flat": 0.05},  # saw-cut to length
    "printed":   {"pos": 0.12, "pattern": 0.05, "scale": 0.0015, "hole_bias": -0.15, "hole_sd": 0.07, "flat": 0.10},  # holes print small
}
# PATTERN_NOTE (2026-11-15). Until then the screw-pattern check gave every hole of a pattern its own independent "pos"
# error. That is the error of a hole against a far datum face, and most of it is common to the holes of one pattern:
# an edge that came out fat or thin (first-layer squash, over-extrusion, a kerf) moves the datum, not the holes against
# each other, and a size error is carried separately as "scale". Hole to hole within a pattern a process is much
# better: an FDM printer positions on the same belts and steps for every hole of a layer. Evidence that the old figure
# was wrong: Rat Rig's V-Minion motor cages have four 3.3 mm printed holes on the NEMA 17's 31 mm square and are
# assembled by the thousand, where the old model said 9 % would start (docs/REFERENCE_MACHINE.md, A1).
# The "pattern" values are RECALLED CLASS VALUES (no document fetched): FDM hole pitch about +/-0.1 mm (two standard
# deviations 0.05), laser +/-0.08, CNC +/-0.04 in one set-up.
#
# A screw in a clearance hole in PLASTIC does not need geometric clearance to start: it cuts its way. Printed parts are
# routinely made with M3 screws threading themselves into 2.5 to 2.8 mm holes (0.1 to 0.25 mm of interference all round);
# an interference on one side of a clearance hole is far less. PLASTIC_HOLE_YIELD_MM is the radial interference a
# screw is taken to overcome in a plastic through-hole (recalled practice, no document). The share of builds in which
# every screw starts FREELY is still reported (`p_all_start_freely`), and patterns that rely on the plastic yielding
# are counted in an info finding, so the reliance is visible.
PLASTIC_HOLE_YIELD_MM = 0.15
PLASTICS = {"pla", "petg", "abs", "nylon_pa12"}


# other names a designer may reasonably write for the five processes
ALIASES = {"fdm": "printed", "3d_printed": "printed", "print": "printed", "cnc": "machined", "milled": "machined",
           "turned": "machined", "laser": "sheet", "laser_cut": "sheet", "waterjet": "sheet", "cut": "sheet",
           "sheet_metal": "sheet", "bent": "sheet", "cots": "purchased", "bought": "purchased"}


def process_of(c: Component) -> str:
    """The part's process: stated on the part (`process=` or `meta["process"]`), else from what it is."""
    stated = getattr(c, "process", None) or c.meta.get("process")
    if stated:
        stated = ALIASES.get(str(stated).lower(), str(stated).lower())
        if stated not in PROCESS:
            raise ValueError(f"{c.name}: unknown process {stated!r}; use one of {sorted(PROCESS)} (or {sorted(ALIASES)})")
        return stated
    if c.cots:
        return "extrusion" if (c.sku or "").startswith("EXT20") else "purchased"   # T-slot extrusion, not "EXTRUDER"
    return "printed" if c.material in PLASTICS else "machined"


def tol(c: Component) -> dict:
    """The process table for one part. A part that names its shop (meta["dfm"]["shop"], see mechloop/shops) gets the
    figures that shop publishes in place of the class values; meta["dfm"]["tolerance"] = {"flat": 0.02} states one itself."""
    base = PROCESS[process_of(c)]
    dfm = c.meta.get("dfm")
    if dfm and (dfm.get("shop") or dfm.get("tolerance")):
        from ..shops import process_tolerance

        return process_tolerance(c, process_of(c), base)
    return base


# Flatness of cast aluminium tooling plate USED AS SUPPLIED (not re-machined), mm over the plate: the maker's guarantee.
# Vista Metals ATP-5 product sheet (vendor_docs/ATP5_datasheet.pdf; mechloop/parts/vendor/cast_tooling_plate.json,
# datasheets.al_atp5): 0.381 mm for plate 12.7 mm and thinner, 0.127 mm above, thickness +/-0.127 mm, listed from 6.35 mm.
# No MIC-6 figure could be read (that sheet's tables are empty); the ATP-5 one is shown for it as the class value.
# This is a REFERENCE figure reported beside the bed results, not a tolerance the stack-up applies: the stack-up's
# "machined" flatness (0.02 mm) is for a mating face a shop has cut.
STOCK_PLATE_FLATNESS = {"al_atp5": {"thin_mm": 0.381, "thick_mm": 0.127, "thin_up_to_mm": 12.7, "thickness_tol_mm": 0.127,
                                    "listed_from_mm": 6.35, "source": "Vista Metals ATP-5 product sheet (guaranteed)"},
                        "al_mic6": {"thin_mm": 0.381, "thick_mm": 0.127, "thin_up_to_mm": 12.7, "thickness_tol_mm": 0.127,
                                    "listed_from_mm": 6.35,
                                    "source": "ATP-5's figure shown as the class value: the MIC-6 sheet in hand has no numbers"}}


def stock_plate_flatness(material: str, thickness_mm: float) -> dict | None:
    """The maker's flatness guarantee for a cast tooling plate of this thickness used as supplied, or None for other
    materials. {"flatness_mm", "thickness_tol_mm", "stock_thickness_listed", "source"}."""
    e = STOCK_PLATE_FLATNESS.get(material)
    if e is None:
        return None
    return {"flatness_mm": e["thin_mm"] if thickness_mm <= e["thin_up_to_mm"] + 1e-9 else e["thick_mm"],
            "thickness_tol_mm": e["thickness_tol_mm"], "plate_thickness_mm": round(float(thickness_mm), 3),
            "stock_thickness_listed": bool(thickness_mm >= e["listed_from_mm"] - 1e-9),
            "listed_from_mm": e["listed_from_mm"], "source": e["source"]}
