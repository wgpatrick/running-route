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


def process_of(c: Component) -> str:
    if c.meta.get("process"):
        return c.meta["process"]
    if c.cots:
        return "extrusion" if (c.sku or "").startswith("EXT") else "purchased"
    return "printed" if c.material in PLASTICS else "machined"


def tol(c: Component) -> dict:
    return PROCESS[process_of(c)]
