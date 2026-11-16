"""What a screw head, nut or washer bears on (ratings verifier: `ratings.head_bearing`).

A cap screw's head bears on a ring between its clearance hole and its bearing diameter (about 0.92 x the head
diameter, ISO 4762's d_w). Two things go wrong there, and a flat washer is the remedy for both:

(a) THE SEAT IS NOT ALL THERE. Over a slot, an oversize or adjustment hole part of the ring has nothing under it. The
    material actually under the ring is measured (points of the ring classified against the seat part's solid) and
    compared with the ring of the same head on its standard close clearance hole, A_ref:
        under SEAT_ERROR_FRACTION (0.6) of A_ref   -> `screw_head_seat_too_small` (error): fit a washer
        under SEAT_WARN_FRACTION (0.85) of A_ref   -> the same code as a warning (marginal)
(b) THE SEAT IS SOFT. Bearing pressure = preload / area under the ring, against an allowable for the seat's material:
        metals: the limiting surface pressure p_G of VDI 2230 (2015 edition), as Bossard tabulates it
            (vendor_cad/staging/practice_refs/04_Bossard_surface_pressure.pdf): S235 490, X4CrNi18-12 (1.4303, for
            304) 630, AW-6082 T6 (the nearest to 6061-T6) 360, AW-5083 325, cast GK-AlSi9Cu3 200 (for cast tooling
            plate: MIC-6 / ATP-5) MPa. 5052-H32 is not tabulated: DERIVED from AW-5083's p_G scaled by tensile strength
            (228 / 260 x 325 = 285 MPa). Brass: not tabulated, its yield (conservative). Over it -> warning: the seat
            embeds and the joint loses preload.
        printed plastic: no published allowable exists (practice_refs MISSING.txt, item 4). PRT-030's DERIVED limit:
            5 MPa sustained up to 40 degC, 2.5 MPa from 40 to 60 degC, nothing above (see PLASTIC_LIMIT_MPA) -> warning;
            above the data sheet's printed tensile yield (PETG 47, ABS 30.8 MPa) the surface crushes on tightening ->
            error. Where the ring is not over the part's perimeters (the solid walls round the hole, from its print
            settings) and the skin under it is thinner than the ring is wide, the outer part of the ring bears on sparse
            infill: that share carries only infill x the allowable (infill^1.5 when the head presses across the layers),
            Gibson-Ashby honeycomb scaling, DERIVED.
    Preload: Bossard's maximum preload for class 8.8 at mu = 0.14 (VDI 2230 2015, 90 % of yield,
    practice_refs/01_Bossard_preload_torque.pdf; FST-040: M3 2436 N at 1.41 N.m, M4 4.3 kN at 3.3, M5 7.0 kN at 6.5,
    M6 9.9 kN at 11.3, M8 18.1 kN at 27.3) for a joint with metal only in its grip; any other torque T gives F = T / X
    with Bossard's conversion factor at mu 0.14 (M3 0.58, M4 0.76, M5 0.93 mm); "soft" for a joint that clamps
    or threads into plastic, where nobody applies the steel torque: ASSUMED (no table exists). State your own:
    design.manufacturing["tightening_torque_nm"] = {"M3": 0.8} or component.meta["torque_nm"] on one screw.

Bought parts (catalogue parts) as the seat are not judged for pressure: their mounting holes are the maker's.
A catalogue flat washer (mechloop.parts.hardware.washer_flat, ISO 7089 / 7093-1; `add_screw(..., washer=True)` or
`add_washer`) between head or nut and the part moves the check to the washer's own ring on the part.
Not judged: countersunk heads, painted or anodised earth-bond seats.
"""
from __future__ import annotations

import math

import numpy as np

from ..model import MATERIALS, Design
from ..report import VerifierResult

BEARING_DIA_OVER_HEAD = 0.92
NUT_BEARING_OVER_FLATS = 0.95
NUT_FACTOR = 0.2           # kept for callers; the preload now uses Bossard's X below
SEAT_ERROR_FRACTION, SEAT_WARN_FRACTION = 0.6, 0.85
PLASTICS = ("pla", "petg", "abs", "nylon_pa12")
# PRT-030 (docs/PRACTICE_RULES.md, rules.json v2): DERIVED sustained bearing limit for printed PETG / ABS: 5 MPa up to
# 40 degC, 2.5 MPa from 40 to 60 degC, no sustained clamp above 60 degC. Basis: PETG's linear viscoelastic range ends at
# 5.3 to 8.0 MPa (DMA, practice_refs/14_PETG_creep_UTS_research.pdf); the ABS creep study held 5 MPa to stay under 2 %
# strain (14_ABS_creep_MDPI_research.pdf); PETG's creep model is valid only to 60 degC. Not a strength: it keeps the plastic
# in its linear range so the clamp load stays predictable. The part's service temperature: meta["service_temp_c"]
# (default: room, under 40 degC).
PLASTIC_LIMIT_MPA = ((40.0, 5.0), (60.0, 2.5))
# Bossard (VDI 2230 2015), coarse thread, mu_K = mu_G = 0.14 (the lowest practical value Bossard tells the user to
# assume for an undeclared finish; FST-040): conversion factor X = M_A / F_M, mm (N.m per kN), and class 8.8 maxima.
TORQUE_TO_PRELOAD_MM = {"M2.5": 0.50, "M3": 0.58, "M4": 0.76, "M5": 0.93, "M6": 1.14, "M8": 1.51}
PRELOAD_88_N = {"M2.5": 1625.0, "M3": 2436.0, "M4": 4300.0, "M5": 7000.0, "M6": 9900.0, "M8": 18100.0}
# N.m. "steel": Bossard's maximum tightening torque, class 8.8, mu 0.14 (practice_refs/01). "soft": ASSUMED.
TORQUE_NM = {"steel": {"M2.5": 0.81, "M3": 1.41, "M4": 3.3, "M5": 6.5, "M6": 11.3, "M8": 27.3},
             "soft": {"M2.5": 0.3, "M3": 0.5, "M4": 1.1, "M5": 2.0, "M6": 3.5, "M8": 8.0}}
# VDI 2230 (2015) limiting surface pressure p_G, MPa, via Bossard (practice_refs/04): (value, basis)
SURFACE_PRESSURE_MPA = {
    "steel": (490.0, "VDI 2230 (2015) p_G of S235, 490 MPa (Bossard table)"),
    "stainless304": (630.0, "VDI 2230 (2015) p_G of X4CrNi18-12 (1.4303), 630 MPa (Bossard table)"),
    "al6061": (360.0, "VDI 2230 (2015) p_G of AW-6082 T6 (AlMgSi1 F31), 360 MPa, the nearest tabulated alloy to 6061-T6"),
    "al5052": (285.0, "DERIVED: VDI 2230 (2015) p_G of AW-5083 (325 MPa at Rm 260) scaled to 5052-H32's Rm 228 MPa"),
    "al_mic6": (200.0, "VDI 2230 (2015) p_G of cast GK-AlSi9Cu3 (Rm 160), 200 MPa, taken for cast tooling plate (Rm 166)"),
    "al_atp5": (200.0, "VDI 2230 (2015) p_G of cast GK-AlSi9Cu3, 200 MPa, taken for cast tooling plate"),
}
N_R, N_A = 6, 16


def _bb(shape):
    b = shape.bounding_box()
    return np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z])


def _inside(shape, pt) -> bool:
    p = tuple(float(x) for x in pt)
    try:
        return any(so.is_inside(p, 1e-6) for so in shape.solids())
    except Exception:
        return False


def _ring(centre, axis, r_in, r_out):
    """Points of equal area on the ring r_in..r_out about `centre`, square to `axis`."""
    a = np.asarray(axis, dtype=float)
    ref = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, ref)
    u /= np.linalg.norm(u)
    v = np.cross(a, u)
    pts = []
    for i in range(N_R):
        r = math.sqrt(r_in ** 2 + (i + 0.5) / N_R * (r_out ** 2 - r_in ** 2))
        for k in range(N_A):
            t = 2 * math.pi * (k + 0.5 * (i % 2)) / N_A
            pts.append(np.asarray(centre) + r * (math.cos(t) * u + math.sin(t) * v))
    return pts


RING_T = 0.1


def _seat(design, boxes, skip: set, centre, into, r_in, r_out):
    """The part with the most material under the ring r_in..r_out just beyond `centre` along `into`: (name, fraction
    of the ring's area). Exact: a ring RING_T thick is intersected with each candidate's solid; if the CAD kernel
    fails on a part, points of the ring are classified against it instead."""
    from build123d import Cylinder, Location, Plane, Pos

    from ..geom import overlap_volume

    into = np.asarray(into, dtype=float)
    plane = np.asarray(centre, dtype=float) + 0.02 * into
    ring = Location(Plane(origin=tuple(plane), z_dir=tuple(into))) * (Pos(0, 0, RING_T / 2) * (Cylinder(r_out, RING_T) - Cylinder(r_in, RING_T)))
    full = math.pi * (r_out ** 2 - r_in ** 2) * RING_T
    pts = None
    best = (None, 0.0)
    for c in design.components:
        if c.name in skip:
            continue
        lo, hi = boxes[c.name]
        if np.any(plane < lo - r_out) or np.any(plane > hi + r_out):
            continue
        try:
            frac = min(float(overlap_volume(c.shape, ring)[0]) / full, 1.0)
        except Exception:
            pts = pts or _ring(plane + 0.03 * into, into, r_in, r_out)
            frac = sum(_inside(c.shape, p) for p in pts) / len(pts)
        if frac > best[1]:
            best = (c.name, frac)
    return best


def is_washer(c) -> bool:
    return (c.sku or "").startswith("WASHER-")


def torque_for(design: Design, comp, size: str, soft: bool) -> tuple:
    man = design.manufacturing or {}
    if comp.meta.get("torque_nm") is not None:
        return float(comp.meta["torque_nm"]), "declared on the screw (meta['torque_nm'])"
    said = (man.get("tightening_torque_nm") or {}).get(size)
    if said is not None:
        return float(said), "declared (design.manufacturing['tightening_torque_nm'])"
    kind = "soft" if soft else "steel"
    t = TORQUE_NM[kind].get(size)
    return t, (f"ASSUMED: {t:g} N.m, what is applied to a screw that clamps or threads into plastic (no table exists)" if soft else
               f"{t:g} N.m, Bossard's maximum for class 8.8 at mu 0.14 (VDI 2230 2015; FST-040)")


def preload_n(size: str, torque_nm: float) -> float:
    """Bossard's maximum preload for class 8.8 at mu 0.14 when the torque is its torque; otherwise F = T / X (Bossard,
    mu 0.14); a size outside the table: T / (0.2 d)."""
    if size in PRELOAD_88_N and abs(torque_nm - TORQUE_NM["steel"][size]) < 1e-9:
        return PRELOAD_88_N[size]
    X = TORQUE_TO_PRELOAD_MM.get(size)
    if X is None:
        return torque_nm * 1e3 / (NUT_FACTOR * float(size[1:]))
    return torque_nm * 1e3 / X


def plastic_limit(temp_c: float | None) -> float | None:
    t = 23.0 if temp_c is None else float(temp_c)
    for upto, lim in PLASTIC_LIMIT_MPA:
        if t <= upto:
            return lim
    return 0.0


def allowable(material: str, temp_c: float | None = None) -> tuple:
    """(pressure for a warning, pressure for an error or None, basis)."""
    m = MATERIALS.get(material)
    if m is None:
        return None, None, "material not in the table"
    if material in PLASTICS:
        from ..printsettings import material_figures

        mf = material_figures(material)
        y = mf["tensile_yield_mpa"]
        lim = plastic_limit(temp_c)
        tt = "room temperature (under 40 degC)" if temp_c is None else f"{float(temp_c):g} degC (meta['service_temp_c'])"
        return lim, y, (
            f"PRT-030, DERIVED: {lim:g} MPa sustained at {tt} (5 MPa to 40 degC, 2.5 MPa to 60 degC, none above: keeps printed "
            f"PETG / ABS in its linear viscoelastic range; no published allowable exists); above the printed yield {y:g} MPa "
            f"({mf['source']}) the surface crushes on tightening")
    if material in SURFACE_PRESSURE_MPA:
        v, basis = SURFACE_PRESSURE_MPA[material]
        return v, None, "FST-030: " + basis
    return m.yield_mpa, None, f"yield of {material} ({m.yield_mpa:g} MPa), taken as the limiting surface pressure (not tabulated; conservative)"


def _infill_share(sc, axis, r_in, r_out) -> tuple:
    """(capacity factor of the ring on a printed seat, note): the part of the ring over the perimeters round the hole, or
    under a skin at least as thick as the ring is wide, is solid; the rest bears on sparse infill."""
    from .. import printsettings as PS

    if not PS.is_printed(sc):
        return 1.0, None
    fr = PS.fractions(sc)
    if fr["settings"]["infill"] >= 0.999:
        return 1.0, None
    up, frame = PS.build_direction(sc, fr["settings"])
    upv = up if up is not None else frame[2]
    along = abs(float(np.dot(np.asarray(axis, dtype=float), upv))) > 0.7
    skin = max(fr["top_mm"], fr["bottom_mm"]) if along else fr["wall_mm"]
    if skin >= (r_out - r_in):
        return 1.0, None
    r_solid = min(r_in + fr["wall_mm"], r_out)
    a_all = math.pi * (r_out ** 2 - r_in ** 2)
    a_solid = math.pi * (r_solid ** 2 - r_in ** 2)
    k, why = PS.infill_bearing_factor(sc, axis)
    cap = (a_solid + (a_all - a_solid) * k) / a_all
    return cap, (f"{1 - a_solid / a_all:.0%} of the ring is over sparse infill ({fr['settings']['infill']:.0%}; {why}) under a "
                 f"{skin:.1f} mm skin; DERIVED")


def head_bearing(design: Design, r: VerifierResult) -> dict:
    from ..parts import NUT, SCREW

    comps = {c.name: c for c in design.components}
    boxes = {c.name: _bb(c.shape) for c in design.components}
    fast = {f.name: f for f in design.fasteners}
    rows, small, press = [], [], []
    seats = []        # (bearing element name, screw size, centre, direction into the seat, r_in, r_out, kind, grip part names, torque owner)
    for f in design.fasteners:
        c = comps.get(f.name)
        if c is None or not c.meta.get("thread_d"):
            continue
        d = float(c.meta["thread_d"])
        size = f"M{d:g}"
        if size not in SCREW:
            continue
        ifc = c.meta.get("interfaces") or {}
        if ifc.get("head") == "countersunk":      # not judged (module docstring): the head bears on the cone of its countersink
            continue
        hd, hh = float(ifc.get("head_d", SCREW[size][1])), float(ifc.get("head_h", SCREW[size][2]))
        ax = np.array(f.axis, dtype=float)
        ax /= np.linalg.norm(ax)
        under = np.array(f.head_center, dtype=float) - ax * hh
        grip = set(f.clamps) | set(c.meta.get("threads_into") or [])
        seats.append((f.name, size, under, -ax, d / 2, BEARING_DIA_OVER_HEAD * hd / 2, "head", grip, c))
    for c in design.components:
        if not (c.sku or "").startswith("NUT-M") or not c.meta.get("placement"):
            continue
        size = (c.sku or "").split("-")[1]
        if size not in NUT:
            continue
        P = np.array(c.meta["placement"], dtype=float)
        screw = next((s for s in fast if c.name in (comps[s].meta.get("threads_into") or [])), None) if True else None
        grip = (set(fast[screw].clamps) | {c.name}) if screw else {c.name}
        seats.append((c.name, size, P[:3, 3], -P[:3, 2], SCREW[size][0] / 2, NUT_BEARING_OVER_FLATS * NUT[size][0] / 2, "nut", grip,
                      comps.get(screw) if screw else c))
    for name, size, centre, into, r_in, r_out, kind, grip, owner in seats:
        d = SCREW[size][0]
        a_ref = math.pi * ((BEARING_DIA_OVER_HEAD * SCREW[size][1] / 2) ** 2 - (SCREW[size][4] / 2) ** 2)
        r_in = SCREW[size][4] / 2 + 0.01        # the ring starts at the standard close clearance hole: a standard seat is all there
        seat, frac = _seat(design, boxes, {name} | set(fast), centre, into, r_in, r_out)
        element, via = name, None
        if seat is not None and is_washer(comps[seat]):
            w = comps[seat]
            wi = w.meta.get("interfaces") or {}
            via = seat
            centre2 = np.asarray(centre) + np.asarray(into) * float(wi.get("thickness", 0.5))
            r_out = float(wi.get("od", 2 * r_out)) / 2
            seat, frac = _seat(design, boxes, {name, via} | set(fast), centre2, into, r_in, r_out)
            element = via
        if seat is None:
            continue                      # nothing under it at the home pose: the interference / assembly checks own that
        sc = comps[seat]
        area = frac * math.pi * (r_out ** 2 - r_in ** 2)
        soft = any(comps[g].material in PLASTICS for g in (set(grip) | {seat}) if g in comps and not comps[g].cots) or sc.material in PLASTICS
        torque, t_basis = torque_for(design, owner, size, soft)
        row = {"fastener": name, "bears_with": kind if via is None else f"{kind} on washer {via}", "on": seat, "size": size,
               "seat_area_mm2": round(area, 2), "seat_area_over_standard": round(area / a_ref, 2)}
        if sc.cots and not is_washer(sc):
            row["pressure"] = "not judged: the seat is a bought part's own mounting face"
            if area / a_ref < SEAT_WARN_FRACTION:
                small.append((row, area / a_ref))
            rows.append(row)
            continue
        if area / a_ref < SEAT_WARN_FRACTION:
            small.append((row, area / a_ref))
        if torque and area > 1e-6:
            preload = preload_n(size, torque)
            p = preload / area
            warn_at, err_at, basis = allowable(sc.material, sc.meta.get("service_temp_c"))
            cap, inote = _infill_share(sc, into, r_in, r_out)
            if cap < 1.0 and warn_at is not None:
                warn_at = round(warn_at * cap, 1)
                err_at = round(err_at * cap, 1) if err_at is not None else None
                basis = f"{basis}; x {cap:.2f}: {inote}"
                row["over_sparse_infill"] = inote
            if warn_at is not None:
                row["allowed_preload_n"] = round(warn_at * area, 1)
                X = TORQUE_TO_PRELOAD_MM.get(size, NUT_FACTOR * d)
                row["allowed_torque_nm"] = round(warn_at * area * X / 1e3, 3)
            row.update({"tightening_torque_nm": torque, "torque_basis": t_basis, "preload_n": round(preload),
                        "bearing_pressure_mpa": round(p, 1), "allowable_mpa": warn_at, "allowable_basis": basis, "seat_material": sc.material})
            if warn_at is not None and p > warn_at and area / a_ref >= SEAT_ERROR_FRACTION:
                press.append((row, "error" if (err_at is not None and p > err_at) else "warning"))
        rows.append(row)
    sgroups: dict = {}
    for row, ratio in small:
        bought = "pressure" in row            # a bought part's own seat: its proxy solid may not show the real seat
        sev = "error" if (ratio < SEAT_ERROR_FRACTION and not bought) else "warning"
        sgroups.setdefault((sev, row["size"], row["bears_with"].split(" ")[0], bought), []).append((row, ratio))
    for (sev, size, kind, bought), g in sorted(sgroups.items(), key=lambda kv: (kv[0][0] != "error", kv[0][1:])):
        row, ratio = min(g, key=lambda x: x[1])
        on = sorted({x[0]["on"] for x in g})
        r.add(sev, "screw_head_seat_too_small",
              f"{len(g)} {size} {kind}(s) sit over a slot or an oversize hole" + (" of a bought part" if bought else "") + f" (on {', '.join(on[:6])}"
              f"{'...' if len(on) > 6 else ''}): least under {row['fastener']}, {row['seat_area_mm2']:.1f} mm^2 of seat, {ratio:.0%} of what the "
              f"same head has on its standard clearance hole"
              + (": it can pull into the hole." if sev == "error" else
                 " (the bought part's simulation solid may not show its real seat: check it)." if bought else " (marginal)."),
              fasteners=sorted(x[0]["fastener"] for x in g)[:60], parts=on, size=size, count=len(g), least_ratio=round(ratio, 2), rule="FST-031",
              hint="FST-031: put a flat washer under it (add_screw(..., washer=True) or add_washer; series='large' over a wide slot), or "
                   "close the hole to the clearance size.")
    # one finding per (size, seat material, bearing element kind, severity): hundreds of screws make a list, not a wall
    groups: dict = {}
    for row, sev in press:
        key = (sev, row["size"], row["seat_material"], "washer" in row["bears_with"])
        groups.setdefault(key, []).append(row)
    for (sev, size, mat, washered), g in sorted(groups.items(), key=lambda kv: (kv[0][0] != "error", kv[0][1:])):
        w = max(g, key=lambda x: x["bearing_pressure_mpa"])
        parts = sorted({x["on"] for x in g})
        r.add(sev, "screw_head_bearing_pressure",
              f"{len(g)} {size} screw head(s) / nut(s) bear " + ("through a washer " if washered else "directly ") + f"on {mat} "
              f"({', '.join(parts[:6])}{'...' if len(parts) > 6 else ''}): up to {w['bearing_pressure_mpa']:.0f} MPa under {w['fastener']} at a "
              f"preload of {w['preload_n']} N ({w['torque_basis']}; Bossard, mu 0.14), against {w['allowable_mpa']:g} MPa allowed "
              f"({w['allowable_basis']}); that seat carries {w['allowed_preload_n']:.0f} N, about {w['allowed_torque_nm']:.2f} N.m."
              + (" The surface crushes as the screw is tightened." if sev == "error" else " The seat creeps or embeds and the joint loses its preload."),
              fasteners=sorted(x["fastener"] for x in g)[:60], parts=parts, size=size, material=mat, count=len(g),
              worst_mpa=w["bearing_pressure_mpa"], allowable_mpa=w["allowable_mpa"], rule="PRT-030" if mat in PLASTICS else "FST-030",
              hint=("PRT-030: on printed plastic a washer and a metal sleeve (compression limiter) through the hole so the clamp load goes "
                    "through metal, and locking that does not need preload (nyloc); or " if mat in PLASTICS else "") +
                   "Put a flat washer under the head or nut (add_screw(..., washer=True), add_washer; series='large' spreads further), "
                   "bear on a metal part instead, or state the torque you will really use "
                   "(design.manufacturing['tightening_torque_nm']).")
    by_part: dict = {}
    for row, sev in press:
        by_part.setdefault(row["on"], {"error": 0, "warning": 0})[sev] += 1
    return {"seats_examined": len(rows), "on_washers": sum("washer" in x["bears_with"] for x in rows),
            "seat_too_small": [dict(x[0], ratio=round(x[1], 2)) for x in small][:40],
            "pressure_findings_by_part": dict(sorted(by_part.items())),
            "worst": sorted([x for x in rows if "bearing_pressure_mpa" in x and x.get("allowable_mpa") is not None],
                            key=lambda x: -x["bearing_pressure_mpa"] / max(x["allowable_mpa"], 1e-9))[:12],
            "torque_tables_nm": TORQUE_NM, "torque_to_preload_mm": TORQUE_TO_PRELOAD_MM,
            "sources": ["preload and class 8.8 torque: Bossard / VDI 2230 2015, mu 0.14 (practice_refs/01; FST-040)",
                        "metal surface pressure: VDI 2230 2015 p_G via Bossard (practice_refs/04)",
                        "washers: ISO 7089 / 7093 (practice_refs/06)"],
            "assumed": ["torque in joints with plastic in them (no table exists)", "friction mu 0.14 (Bossard's lowest practical value)",
                        "printed-plastic allowable DERIVED (PRT-030): 5 MPa to 40 degC, 2.5 MPa to 60 degC",
                        "5052-H32 surface pressure DERIVED from AW-5083 by tensile strength; brass at its yield",
                        "infill under a head: Gibson-Ashby scaling, DERIVED"]}


def ring_abutment(design: Design, r: VerifierResult) -> dict:
    """BRG-024: what touches a ball bearing's faces must stay inside that ring's abutment diameters. For each catalogue
    bearing with abutment data (608: d1 12.15, D2 19.2, Da max 20 mm, SKF) the parts lying against each face are found
    on rings of radius just outside the face (points classified against the parts' solids). Contact between d1 and D2
    rubs the shield or seal (`bearing_abutment`, warning); one part touching both the inner ring (inside d1) and the
    outer ring (outside D2) clamps both rings, so the turning ring drags (warning)."""
    comps = list(design.components)
    boxes = {c.name: _bb(c.shape) for c in comps}
    rows, bad = [], []
    for b in comps:
        itf = b.meta.get("interfaces") or {}
        if "d1" not in itf or not b.meta.get("placement"):
            continue
        P = np.array(b.meta["placement"], dtype=float)
        o, ax = P[:3, 3], P[:3, 2] / np.linalg.norm(P[:3, 2])
        u = np.cross(ax, [1.0, 0, 0] if abs(ax[0]) < 0.9 else [0, 1.0, 0])
        u /= np.linalg.norm(u)
        v = np.cross(ax, u)
        radii = np.linspace(itf["bore"] / 2 + 0.3, itf["od"] / 2 - 0.2, 27)       # 0.25 mm apart on a 608
        tol = 2 * (radii[1] - radii[0])                                           # one sample step, as a diameter
        for side in (1.0, -1.0):
            face_c = o + side * ax * (itf["width"] / 2 + 0.05)
            hits: dict = {}
            for c in comps:
                if c.name == b.name:
                    continue
                lo, hi = boxes[c.name]
                if np.any(face_c < lo - itf["od"]) or np.any(face_c > hi + itf["od"]):
                    continue
                touched = []
                for rr in radii:
                    pts = [face_c + rr * (math.cos(t) * u + math.sin(t) * v) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
                    if sum(_inside(c.shape, p) for p in pts) >= 3:
                        touched.append(float(rr))
                if touched:
                    hits[c.name] = (min(touched) * 2, max(touched) * 2)
            for part, (dmin, dmax) in hits.items():
                row = {"bearing": b.name, "part": part, "face": "+" if side > 0 else "-", "contact_from_mm": round(dmin, 1),
                       "contact_to_mm": round(dmax, 1)}
                inner = dmin < itf["d1"]
                outer = dmax > itf["D2"]
                shield = any(itf["d1"] + tol < x < itf["D2"] - tol for x in (dmin, dmax))
                if inner and outer:
                    row["problem"] = "touches both rings: the turning ring drags on it"
                elif shield:
                    row["problem"] = (f"contact reaches {dmax:.1f} mm, past the inner ring's shoulder d1 {itf['d1']:g} mm: it rubs the shield"
                                      if inner else f"contact from {dmin:.1f} mm, inside the outer ring's D2 {itf['D2']:g} mm: it rubs the shield")
                rows.append(row)
                if "problem" in row:
                    bad.append(row)
    if bad:
        r.add("warning", "bearing_abutment",
              f"{len(bad)} part(s) bear on a ball bearing outside the ring they should abut (BRG-024, SKF abutment dimensions): "
              + "; ".join(f"{x['part']} on {x['bearing']} ({x['contact_from_mm']:g} to {x['contact_to_mm']:g} mm: {x['problem']})" for x in bad[:6])
              + ("..." if len(bad) > 6 else "") + ".",
              contacts=bad[:40], rule="BRG-024",
              hint="Put a shim washer that matches the ring (8 x 12 mm on a 608's inner ring) between, or a step / relief so only the "
                   "intended ring is touched.")
    return {"contacts": rows[:80], "problems": len(bad)}
