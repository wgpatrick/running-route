"""Per-part validity and whole-design envelope/mass checks."""
from __future__ import annotations

from ..geom import bbox_of
from ..model import MATERIALS, Design
from ..report import VerifierResult, timed


def verify_geometry(design: Design) -> VerifierResult:
    r = VerifierResult("geometry")
    with timed(r):
        if not design.components:
            r.add("error", "empty_design", "Design has no components.")
            return r
        for c in design.components:
            if c.material not in MATERIALS:
                r.add("error", "unknown_material", f"{c.name}: unknown material '{c.material}'.",
                      part=c.name, known=sorted(MATERIALS))
                continue
            s = c.shape
            solids = s.solids()
            if not solids:
                r.add("error", "no_solid", f"{c.name}: shape has no solid volume.", part=c.name)
                continue
            if not s.is_valid:
                r.add("error", "invalid_brep", f"{c.name}: B-rep is invalid (failed kernel check).", part=c.name)
            if s.volume <= 1e-6:
                r.add("error", "zero_volume", f"{c.name}: volume is {s.volume:.3g} mm^3.", part=c.name)
            if len(solids) > 1 and not c.cots:
                r.add("warning", "multiple_solids",
                      f"{c.name}: {len(solids)} disconnected solids in one part (should it be one piece?).",
                      part=c.name, solids=len(solids))
        lo, hi = bbox_of([c.shape for c in design.components])
        size = (hi - lo).round(2).tolist()
        mass = design.total_mass()
        r.metrics = {
            "parts": len(design.components),
            "cots_parts": sum(c.cots for c in design.components),
            "bbox_mm": size,
            "mass_kg": round(mass, 4),
            "mass_by_part_kg": {c.name: round(c.mass(), 4) for c in design.components}
            if len(design.components) <= 30 else "omitted (>30 parts)",
        }
        if any(c.detail is not None for c in design.components):
            # simulation solids against the vendor / community CAD behind them, and what that CAD adds
            from ..parts.vendor_cad import verify_detail

            r.metrics["vendor_cad"] = verify_detail(design, r)
        if design.envelope:
            for ax, got, lim in zip("XYZ", size, design.envelope):
                if got > lim + 1e-6:
                    r.add("error", "envelope_exceeded",
                          f"Overall {ax} size {got:.1f} mm exceeds the {lim:.1f} mm envelope.",
                          axis=ax, size=got, limit=lim)
        if design.max_mass_kg is not None and mass > design.max_mass_kg:
            r.add("error", "mass_exceeded",
                  f"Total mass {mass:.3f} kg exceeds limit {design.max_mass_kg:.3f} kg.",
                  mass=mass, limit=design.max_mass_kg)
    return r


def verify_requirements(design: Design, metrics: dict) -> VerifierResult:
    """The brief's acceptance tests. `check(design)` or `check(design, metrics)` where
    metrics is {verifier: its metrics dict} from this run."""
    import inspect

    r = VerifierResult("requirements")
    if not design.requirements:
        r.skipped = "design declares no requirements"
        return r
    with timed(r):
        for req in design.requirements:
            try:
                n = len(inspect.signature(req.check).parameters)
                ok, detail = req.check(design, metrics) if n >= 2 else req.check(design)
            except Exception as e:  # a requirement that cannot be evaluated is not met
                ok, detail = False, f"could not be evaluated: {type(e).__name__}: {e}"
            r.add("info" if ok else "error", "requirement_met" if ok else "requirement_failed",
                  f"{req.name}: {detail}", requirement=req.name)
        r.metrics = {"met": sum(f.code == "requirement_met" for f in r.findings), "total": len(design.requirements)}
    return r
