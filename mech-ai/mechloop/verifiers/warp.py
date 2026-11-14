"""Warp risk for printed parts: a rule of thumb, not a simulation.

A proper prediction needs a layer-by-layer thermal model calibrated against real prints. A
single-step cooling FEA was tried and rejected: its peel stress is a mesh-dependent corner
singularity and it flagged small PLA parts that print without trouble. What is used instead is
the common experience that warping scales with the longest dimension lying on the bed and with
how much the material shrinks, expressed as a per-material length beyond which an open-air print
usually needs help (brim, enclosure, rounded corners).
"""
from __future__ import annotations

from ..model import Design
from ..report import VerifierResult

# longest bed dimension (mm) an open-air print of this material usually tolerates
OPEN_AIR_LIMIT_MM = {"pla": 220.0, "petg": 160.0, "abs": 80.0, "nylon_pa12": 60.0}


def warp_risk(design: Design, part: str, longest_bed_mm: float, r: VerifierResult | None = None) -> dict:
    comp = design.get(part)
    lim = OPEN_AIR_LIMIT_MM.get(comp.material)
    if lim is None:
        return {"skipped": f"no rule for {comp.material}"}
    idx = longest_bed_mm / lim
    out = {"longest_bed_dimension_mm": round(longest_bed_mm, 1), "open_air_limit_mm": lim,
           "index": round(idx, 2), "basis": "rule of thumb, not simulated"}
    if r is not None and idx > 1.0:
        r.add("warning", "print_warp_risk",
              f"{part}: {longest_bed_mm:.0f} mm on the bed in {comp.material}; open-air prints of this material usually start "
              f"to lift beyond about {lim:.0f} mm (rule of thumb, not simulated).", part=part,
              hint="Add a brim, round the footprint corners, print in an enclosure, split the part, or change material.")
    return out
