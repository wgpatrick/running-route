"""How accurately each kind of part is made. Values are typical shop figures (one standard
deviation unless noted), deliberately a little pessimistic, and meant to be replaced with the
supplier's or the machine's own numbers."""
from __future__ import annotations

from ..model import Component

PROCESS = {
    #            feature position   size, fraction   hole diameter: bias, sigma   flatness of a mating face
    "purchased": {"pos": 0.02, "scale": 0.0001, "hole_bias": 0.00, "hole_sd": 0.01, "flat": 0.01},
    "machined":  {"pos": 0.04, "scale": 0.0002, "hole_bias": 0.00, "hole_sd": 0.02, "flat": 0.02},
    "sheet":     {"pos": 0.08, "scale": 0.0005, "hole_bias": 0.00, "hole_sd": 0.04, "flat": 0.10},
    "extrusion": {"pos": 0.15, "scale": 0.0010, "hole_bias": 0.00, "hole_sd": 0.03, "flat": 0.05},  # saw-cut to length
    "printed":   {"pos": 0.12, "scale": 0.0015, "hole_bias": -0.15, "hole_sd": 0.07, "flat": 0.10},  # holes print small
}
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
    return PROCESS[process_of(c)]
