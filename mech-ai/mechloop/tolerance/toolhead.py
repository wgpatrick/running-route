"""How far a part of the toolhead can really be from where it is drawn, relative to the nozzle tip.

Why this exists. A printer's declared Z over-travel (Joint.overtravel past the nozzle plane) is not a motion in which
the bed passes through the nozzle: it is allowance for where the nozzle really ends up relative to the bed in a built
machine (the z-offset stack-up of frame, gantry, Z axis and bed) and for a bed mesh. Everything that rides on the body
that carries the nozzle goes up and down WITH the nozzle in that stack-up, so the over-travel is common to all of it.
What can bring the bed closer to such a part than to the nozzle tip is only

  1. the stack-up inside the toolhead between that part and the nozzle tip (`stackup_mm`): the tolerance simulation
     (mechloop.tolerance.stackup.Build) run on the nozzle's body alone, with the part that carries the tip as its
     datum; 99.7th percentile of the height error of the part's lowest point relative to the tip; and
  2. the bed surface not being a plane parallel to the travel, seen over the horizontal distance between the nozzle
     and the part (`bed_rise_mm`): the plate's flatness taken as a simple bow (the maker's stock flatness for cast
     tooling plate, mechloop.tolerance.process.STOCK_PLATE_FLATNESS; the same figure, said to be assumed, for any other
     plate) plus the levelling residual the tolerance verifier accepts (half a layer over 80 % of the plate).

`margin_mm` is their sum: with the nozzle touching the bed, a toolhead part whose underside is `margin_mm` or more
above the tip cannot be touching the bed. The motion verifier checks the bed against toolhead parts no deeper than
nozzle contact plus this margin; the subsystems verifier asks the same margin of a bed probe's sensing face.

Not in it: thermal growth of the hotend (it lowers the tip when hot, which adds clearance for everything else), a
sensor whose height is set on the machine by its nuts (the drawn height is taken), the rise of a print's curled edge
(the subsystems verifier's 1 mm warning), deflection."""
from __future__ import annotations

import copy

import numpy as np

from .process import stock_plate_flatness
from .stackup import SEED, Build, _bb

N_TOOLHEAD = 2000
ASSUMED_FLATNESS_MM = 0.381        # used, and said to be assumed, for a bed plate with no maker's figure (the ATP-5 value)
UNPLACED_STACKUP_MM = 0.5          # a part the simulation cannot tie to the nozzle through touching / joined toolhead parts
LEVEL_RESIDUAL_FRAC = 0.5          # of a layer, over 80 % of the plate: the tolerance verifier's own levelling criterion

_CACHE: dict = {}


def _zdir(design) -> np.ndarray:
    pr = design.printer or {}
    j = next((x for x in design.joints if x.name == pr.get("z")), None)
    a = np.array(j.axis if j is not None else (0, 0, 1), dtype=float)
    return a / np.linalg.norm(a)


def nozzle_part(design) -> str | None:
    """The part the tool point lies on (within 0.5 mm), on the tool point's body."""
    if design.tool_point is None:
        return None
    from build123d import Vertex

    tb, tp = design.tool_point
    cand = []
    for c in design.components:
        if c.body != tb:
            continue
        try:
            cand.append((c.shape.distance_to(Vertex(*tp)), c.name))
        except Exception:
            pass
    if not cand or min(cand)[0] > 0.5:
        return None
    return min(cand)[1]


def bed_rise(design, offset_mm: float) -> dict:
    """How much higher the bed surface can be `offset_mm` to the side of the nozzle than under it."""
    pr = design.printer or {}
    comps = {c.name: c for c in design.components}
    bed = comps.get(pr.get("bed"))
    if bed is None:
        return {"bed_rise_mm": 0.0, "basis": "no bed declared"}
    lo, hi = _bb(bed.shape)
    ext = np.sort(hi - lo)
    thick, span = float(ext[0]), float(ext[1])              # plate thickness, shorter side
    spf = stock_plate_flatness(bed.material, thick)
    flat = spf["flatness_mm"] if spf else ASSUMED_FLATNESS_MM
    r = min(max(float(offset_mm), 0.0), span / 2)
    bow = flat * (1.0 - (1.0 - 2.0 * r / span) ** 2)        # a bow of `flat` over the span, seen from its edge
    lh = float(pr.get("layer_height", 0.2))
    tilt = LEVEL_RESIDUAL_FRAC * lh * r / (0.8 * span)
    return {"bed_rise_mm": round(bow + tilt, 3), "bow_mm": round(bow, 3), "level_residual_mm": round(tilt, 3),
            "plate_flatness_mm": flat, "plate_span_mm": round(span, 1), "offset_mm": round(float(offset_mm), 2),
            "flatness_basis": (spf["source"] if spf else f"ASSUMED {ASSUMED_FLATNESS_MM} mm (the cast tooling plate figure): no maker's "
                               f"flatness for '{bed.material}'"),
            "basis": "plate flatness as one bow over the shorter side, seen from the plate edge, plus a levelling residual of "
                     f"{LEVEL_RESIDUAL_FRAC:g} layer over 80 % of the plate"}


def _build(design):
    """(Build of the nozzle's body alone with the nozzle part as datum, nozzle part name), cached per design."""
    tb, tp = design.tool_point
    members = [c for c in design.components if c.body == tb]
    sig = (tuple((c.name, id(c.shape.wrapped)) for c in members), tuple(tp), len(design.joins), len(design.fasteners))
    hit = _CACHE.get(id(design))
    if hit is not None and hit[0] == sig:
        return hit[1], hit[2]
    noz = nozzle_part(design)
    B = None
    if noz is not None:
        sub = copy.copy(design)
        sub.components = members
        sub.base = noz
        B = Build(sub, N_TOOLHEAD, SEED)
    _CACHE.clear()
    _CACHE[id(design)] = (sig, B, noz)
    return B, noz


def height_margin(design, part: str, point=None) -> dict | None:
    """Margin (mm) by which `part` (on the nozzle's body) must stand above the nozzle tip not to be touching the bed
    when the nozzle is: see the module docstring. `point`: the point of the part that matters (a probe's sensing
    face); default the lowest point of its bounding box, with the horizontal offset taken to the box's far corner.
    None when the design has no tool point or the part is not on the nozzle's body."""
    if design.tool_point is None:
        return None
    tb, tp = design.tool_point
    comps = {c.name: c for c in design.components}
    c = comps.get(part)
    if c is None or c.body != tb:
        return None
    B, noz = _build(design)
    z = _zdir(design)
    tpn = np.array(tp, dtype=float)
    lo, hi = _bb(c.shape)
    if point is None:
        corners = np.array([[x, y, w] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for w in (lo[2], hi[2])])
        rel = corners - tpn
        horiz = rel - np.outer(rel @ z, z)
        offset = float(np.linalg.norm(horiz, axis=1).max())
        mid = (lo + hi) / 2
        p = mid + z * float((corners @ z).min() - mid @ z)
    else:
        p = np.array(point, dtype=float)
        rel = p - tpn
        offset = float(np.linalg.norm(rel - (rel @ z) * z))
    out = {"part": part, "nozzle_part": noz}
    if part == noz:
        s, basis = 0.0, "the part that carries the nozzle tip: rigid with it"
    elif B is not None and part in B.A:
        h = (B.at(part, p) - B.at(noz, tpn)) @ z - float((p - tpn) @ z)
        s = float(np.percentile(np.abs(h), 99.7))
        basis = (f"tolerance simulation of the toolhead alone ({B.n} builds, datum '{noz}'): 99.7th percentile of the height error "
                 "of this point relative to the nozzle tip")
        out["largest_contributors"] = B.blame(h, top=3)
    else:
        placed = [k for k in (B.A if B is not None else {}) if k != noz]
        worst = 0.0
        for k in placed:           # no tighter than the loosest part that could be simulated
            lo_k, hi_k = _bb(comps[k].shape)
            pk = (lo_k + hi_k) / 2
            hk = (B.at(k, pk) - B.at(noz, tpn)) @ z - float((pk - tpn) @ z)
            worst = max(worst, float(np.percentile(np.abs(hk), 99.7)))
        s = max(UNPLACED_STACKUP_MM, worst)
        basis = (f"ASSUMED {s:.2f} mm: this part is a screw or is not tied to the nozzle part "
                 f"('{noz}') through touching or joined parts of body '{tb}', so its chain could not be simulated")
        out["assumed"] = True
    br = bed_rise(design, offset)
    out.update({"stackup_mm": round(s, 3), "stackup_basis": basis, "bed_rise_mm": br["bed_rise_mm"], "bed_rise": br,
                "margin_mm": round(s + br["bed_rise_mm"], 3)})
    return out
