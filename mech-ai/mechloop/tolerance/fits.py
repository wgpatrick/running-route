"""Will it go together? Screw patterns against their holes, and shafts against their bores,
built many times with each part made as accurately as its process allows."""
from __future__ import annotations

import math

import numpy as np
from build123d import Edge, GeomType, Plane, Solid
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

from ..geom import bboxes_overlap
from ..model import Design
from ..report import VerifierResult
from .process import PLASTIC_HOLE_YIELD_MM, PLASTICS, process_of, tol


def _hole_radius(part, a0, a1) -> float | None:
    """Radius of the hole a screw's shank passes through in `part`: the smallest RADIAL distance from the
    stretch of screw axis a0-a1 to the part (None if it cannot be measured).

    The plain distance from a line segment to a solid is not that: where the screw ends inside a nut slot
    or a blind pocket, the nearest material can be the wall beyond the end of the segment, and the distance
    to it is measured along the screw, not across it. A captive-nut slot 3.7 mm wide along the screw was
    read as a 3.2 mm clearance hole that way. So when the nearest point lies beyond either end of the
    segment, the part is cut to the slab between the two ends first and the distance is taken to that."""
    try:
        a0, a1 = np.asarray(a0, dtype=float), np.asarray(a1, dtype=float)
        line = Edge.make_line(tuple(a0), tuple(a1))
        ex = BRepExtrema_DistShapeShape(part.wrapped, line.wrapped)
        if not ex.IsDone() or ex.NbSolution() < 1:
            return None
        r = float(ex.Value())
        length = float(np.linalg.norm(a1 - a0))
        if length < 1e-9:
            return r
        u = (a1 - a0) / length

        def radial(k):
            p = ex.PointOnShape1(k)
            v = np.array([p.X(), p.Y(), p.Z()]) - a0
            t = float(v @ u)
            return -1e-6 <= t <= length + 1e-6 and abs(float(np.linalg.norm(v - t * u)) - r) < 1e-6

        if r <= 1e-9 or any(radial(k) for k in range(1, ex.NbSolution() + 1)):
            return r
        # end-on: keep only the material alongside the segment and measure again
        bb = part.bounding_box()
        reach = 2.0 * float(np.linalg.norm([bb.size.X, bb.size.Y, bb.size.Z])) + 10.0
        slab = Solid.make_cylinder(reach, length, Plane(origin=tuple(a0), z_dir=tuple(u)))
        cut = part & slab
        if cut is None or not cut.solids():
            return None                      # no material beside this stretch of the screw: it is not in a hole
        return float(cut.distance_to(line))
    except Exception:
        return None


def screw_patterns(design: Design, r: VerifierResult, n: int = 4000, seed: int = 0) -> dict:
    """Each group of screws joining the same parts: can all of them be started at once?
    Hole positions and diameters vary by process; the parts may shift to find the best fit."""
    rng = np.random.default_rng(seed)
    comps = {c.name: c for c in design.components}
    groups: dict[tuple, list] = {}
    for f in design.fasteners:
        if f.name not in comps:
            continue
        sc = comps[f.name]
        d = sc.meta.get("thread_d")
        if not d:
            continue
        ax = np.array(f.axis, dtype=float)
        ax /= np.linalg.norm(ax)
        bb = sc.shape.bounding_box()
        ctr = np.array([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2])
        half = 0.5 * float(np.dot([bb.size.X, bb.size.Y, bb.size.Z], np.abs(ax)))
        head = np.array(f.head_center, dtype=float)
        tip = head - ax * (2 * half)
        targets = [t for t in sc.meta.get("threads_into", []) if t in comps]
        through = []
        for name in sorted(set(f.clamps) | {c.name for c in design.components
                                            if c.name != f.name and c.name not in targets and not c.meta.get("thread_d")
                                            and bboxes_overlap(sc.shape, c.shape, 0.05)}):     # sorted: same order every run
            if name not in comps or name in targets:
                continue
            p0, p1 = head - ax * (sc.meta.get("interfaces", {}).get("head_h", d) + 0.3), tip + ax * 0.3
            # only the stretch of shank that lies inside this part's extent along the axis
            pb = comps[name].shape.bounding_box()
            lo = np.array([pb.min.X, pb.min.Y, pb.min.Z]) @ np.abs(ax)
            hi = np.array([pb.max.X, pb.max.Y, pb.max.Z]) @ np.abs(ax)
            s0, s1 = sorted((float(p0 @ np.abs(ax)), float(p1 @ np.abs(ax))))
            a, b = max(s0, lo), min(s1, hi)
            if b - a < 0.3:
                continue
            base = p0 if float(p0 @ np.abs(ax)) < float(p1 @ np.abs(ax)) else p1
            dirn = np.abs(ax) if np.all(ax * np.sign(ax) == np.abs(ax)) else np.abs(ax)
            q0 = base + (a - float(base @ np.abs(ax)) + 0.1) * np.abs(ax)
            q1 = base + (b - float(base @ np.abs(ax)) - 0.1) * np.abs(ax)
            rad = _hole_radius(comps[name].shape, q0, q1)
            if rad is not None and 0.0 < rad < 3 * d:
                through.append((name, rad))
        if not through or not targets:
            continue
        for name, rad in through:
            groups.setdefault((name, targets[0]), []).append({"screw": f.name, "d": d, "hole_r": rad, "ax": ax, "pos": ctr,
                                                              "tnut": bool(sc.meta.get("tnut"))})
    out, worst = {}, []
    for (pa, pb), items in sorted(groups.items()):
        ta, tb = tol(comps[pa]), tol(comps[pb])
        k = len(items)
        ax = items[0]["ax"]
        ref = np.array([1.0, 0, 0]) if abs(ax[0]) < 0.9 else np.array([0, 1.0, 0])
        e1 = np.cross(ax, ref); e1 /= np.linalg.norm(e1)
        e2 = np.cross(ax, e1)
        # a T-nut slides along its slot, so the threaded side has no position error along the slot;
        # treat it as free in both lateral directions only when every screw in the group uses one
        all_tnut = all(i["tnut"] for i in items)
        # hole to hole within one pattern: the process's "pattern" figure, not its feature-to-datum "pos" (process.py)
        sb = 0.0 if all_tnut else tb.get("pattern", tb["pos"])
        ea = rng.normal(0, ta.get("pattern", ta["pos"]), (n, k, 2))
        eb = rng.normal(0, sb, (n, k, 2))
        # size error stretches the pattern
        P = np.array([[i["pos"] @ e1, i["pos"] @ e2] for i in items])
        P = P - P.mean(axis=0)
        stretch = (rng.normal(0, ta["scale"], (n, 1, 1)) - rng.normal(0, tb["scale"], (n, 1, 1))) * P[None, :, :]
        mis = ea - eb + stretch
        mis = mis - mis.mean(axis=1, keepdims=True)          # the parts shift to the best average position
        need = np.linalg.norm(mis, axis=2)                    # radial mismatch at each screw
        hole_r = np.array([i["hole_r"] for i in items])[None, :] + 0.5 * (ta["hole_bias"] + rng.normal(0, ta["hole_sd"], (n, k)))
        # a real screw's thread is made slightly under its nominal diameter (about 0.1 mm for M3-M5)
        screw_r = np.array([i["d"] for i in items])[None, :] / 2 - 0.05
        free = (need <= (hole_r - screw_r)).all(axis=1)
        # a screw cuts its way through a plastic clearance hole that is a little tight on one side (process.py)
        give = PLASTIC_HOLE_YIELD_MM if comps[pa].material in PLASTICS else 0.0
        ok = (need <= (hole_r - screw_r) + give).all(axis=1)
        # screws into T-nuts always start: each nut slides along its slot and has play across it
        p_fit = 1.0 if all_tnut else float(ok.mean())
        p_free = 1.0 if all_tnut else float(free.mean())
        nominal_clear = float(min(i["hole_r"] - i["d"] / 2 + 0.05 for i in items))
        out[f"{pa} -> {pb}"] = {"screws": k, "p_all_start": round(p_fit, 4),
                                "p_all_start_standard_error": round(float(np.sqrt(max(p_fit * (1 - p_fit), 0.0) / n)), 4),
                                "p_all_start_freely": round(p_free, 4),
                                **({"plastic_hole_yield_mm": give} if give else {}),
                                "nominal_radial_clearance_mm": round(nominal_clear, 3),
                                "process": [process_of(comps[pa]), process_of(comps[pb])]}
        if p_fit < 0.99:
            worst.append((p_fit, pa, pb, k, nominal_clear))
    forced = sorted(k_ for k_, v in out.items() if v.get("plastic_hole_yield_mm") and v["p_all_start"] >= 0.99 and v["p_all_start_freely"] < 0.9)
    if forced:
        r.add("info", "screws_cut_into_printed_holes",
              f"{len(forced)} screw pattern(s) in printed parts start in at least 99 % of builds only because a screw cuts its "
              f"way through a plastic hole that is up to {PLASTIC_HOLE_YIELD_MM} mm tight on one side (they start freely in under "
              f"90 %): {', '.join(forced[:6])}. Usual for printed parts; open the holes by 0.2 mm if the screws should drop in.",
              patterns=forced)
    for p_fit, pa, pb, k, clr in sorted(worst)[:12]:
        sev = "error" if p_fit < 0.9 else "warning"
        r.add(sev, "screws_may_not_align",
              f"The {k} screw(s) through {pa} into {pb} all start in only {p_fit:.0%} of builds "
              f"({process_of(comps[pa])} holes with {clr:.2f} mm radial clearance against {process_of(comps[pb])} threads).",
              parts=[pa, pb], p_fit=round(p_fit, 3),
              hint="Open the clearance holes (printed holes come out about 0.15 mm small), slot one of the holes, "
                   "use fewer screws in the pattern, or match-drill.")
    return out


def _cylinders(shape):
    out = []
    for f in shape.faces():
        if f.geom_type != GeomType.CYLINDER:
            continue
        cyl = BRepAdaptor_Surface(f.wrapped).Cylinder()
        loc, d = cyl.Axis().Location(), cyl.Axis().Direction()
        p = f.center()
        ax0 = np.array([loc.X(), loc.Y(), loc.Z()])
        axd = np.array([d.X(), d.Y(), d.Z()])
        pc = np.array([p.X, p.Y, p.Z])
        radial = (pc - ax0) - ((pc - ax0) @ axd) * axd
        try:
            nrm = f.normal_at(p)
            outward = float(np.array([nrm.X, nrm.Y, nrm.Z]) @ radial) > 0
        except Exception:
            continue
        bb = f.bounding_box()
        length = float(abs(np.array([bb.size.X, bb.size.Y, bb.size.Z]) @ np.abs(axd)))
        mid = float((pc - ax0) @ axd)
        out.append({"r": cyl.Radius(), "p": ax0, "d": axd, "shaft": outward, "len": length, "area": f.area,
                    "span": (mid - length / 2, mid + length / 2)})
    return out


AXLE_KINDS = ("axle", "shaft", "pivot", "pin")      # join kinds that make a screw's shank a shaft for what turns on it
SHAFT_TOL_KEYS = ("shaft_dia_tol_mm", "bore_dia_tol_mm")


def bores_and_shafts(design: Design, r: VerifierResult, n: int = 4000, seed: int = 1) -> dict:
    """A shaft drawn the same size as its bore fits half the time. Find those pairs and say how often
    they would bind (if meant to slide) or be loose (if meant to be pressed).

    Which pairs (2026-11-15: before, any pair of two catalogue parts and anything on a screw's shank was left out
    without a word, so a machine with a dozen shafts reported two):
      * a made part with a purchased or made part: simulated from the two processes, as before;
      * two purchased catalogue parts (motor shaft in pulley or coupler, lead screw in coupler and nut, idler on its
        spacer): their makers hold the fit, the simulation's generic "purchased" figures would only pretend to know it.
        Each is LISTED as class "catalogue fit, trusted" with its drawn clearance and whatever tolerance the catalogue
        does record (a NEMA 17's shaft is 5 +0 / -0.012 on StepperOnline's drawing), and one info finding counts them.
        A catalogue pair drawn with the shaft larger than the bore is an error all the same (`catalogue_fit_mismatch`);
      * a screw's shank as a shaft, only where it is one by declaration (design.join(part, screw, "axle")) or where a
        purchased part with a bore rides on it (idler, bearing, spacer): a screw in a made part's clearance hole is the
        screw-pattern check's business, not a fit."""
    rng = np.random.default_rng(seed)
    comps = {c.name: c for c in design.components}
    cyl = {}
    fast = {f.name for f in design.fasteners}
    names = [c.name for c in design.components]
    out, flagged, trusted, mismatch = {}, [], [], []

    def axle(screw, other):
        kind = str(design.joins.get(frozenset((screw, other)), ""))
        if any(w in kind for w in AXLE_KINDS):
            return True
        oc = comps[other]
        return bool(oc.cots and not oc.meta.get("thread_d") and "bore" in (oc.meta.get("interfaces") or {})
                    and frozenset((screw, other)) not in design.allowed_overlaps)

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if a in fast and b in fast:
                continue
            if (a in fast and not axle(a, b)) or (b in fast and not axle(b, a)):
                continue
            if not bboxes_overlap(comps[a].shape, comps[b].shape, 0.05):
                continue
            both_bought = all(comps[x].cots and (comps[x].meta.get("catalog") or x in fast) for x in (a, b))
            for n_ in (a, b):
                if n_ not in cyl:
                    cyl[n_] = _cylinders(comps[n_].shape)
            for sa, sb, na, nb in ((cyl[a], cyl[b], a, b), (cyl[b], cyl[a], b, a)):
                if nb in fast:
                    continue            # a screw is never the bore
                for S in sa:
                    if not S["shaft"] or S["len"] < 1.5:
                        continue
                    for B in sb:
                        if B["shaft"] or B["len"] < 1.5 or abs(B["r"] - S["r"]) > 0.26:
                            continue
                        if abs(abs(S["d"] @ B["d"]) - 1) > 1e-3:
                            continue
                        off = (B["p"] - S["p"]) - ((B["p"] - S["p"]) @ S["d"]) * S["d"]
                        if np.linalg.norm(off) > 0.05:
                            continue
                        # the shaft must actually be inside the bore along the axis, not merely in line with it
                        shift = float((B["p"] - S["p"]) @ S["d"]) * (1.0 if S["d"] @ B["d"] > 0 else 1.0)
                        b0, b1 = sorted(((B["span"][0] if S["d"] @ B["d"] > 0 else -B["span"][1]) + shift,
                                         (B["span"][1] if S["d"] @ B["d"] > 0 else -B["span"][0]) + shift))
                        if min(S["span"][1], b1) - max(S["span"][0], b0) < 1.0:
                            continue
                        kind = design.joins.get(frozenset((na, nb)), "")
                        intent = "press" if any(w in str(kind) for w in ("press", "interference")) else "slide"
                        nominal = 2 * (B["r"] - S["r"])
                        key = f"{na} in {nb} (dia {2 * S['r']:.2f})"
                        if both_bought:
                            if key in out:
                                continue
                            rec = {"intent": intent, "nominal_clearance_mm": round(nominal, 3), "p_bad": None,
                                   "class": "catalogue fit, trusted", "process": [process_of(comps[na]), process_of(comps[nb])],
                                   **({"held_by": str(kind)} if kind else {}),
                                   "basis": "two purchased catalogue parts sold to go together: the fit is their makers', not simulated"}
                            tols = {x: comps[x].ratings.get(k_) or (comps[x].meta.get("interfaces") or {}).get(k_)
                                    for x, k_ in ((na, "shaft_dia_tol_mm"), (nb, "bore_dia_tol_mm"))}
                            if any(tols.values()):
                                rec["catalogue_tolerances_mm"] = {x: v for x, v in tols.items() if v}
                            if na in fast:
                                rec["basis"] = ("a purchased part with a bore on a screw's shank (the shank is made 0.03 to 0.2 mm "
                                                "under its nominal diameter): trusted, not simulated")
                            out[key] = rec
                            trusted.append(key)
                            if intent == "slide" and nominal < -0.011:
                                mismatch.append((na, nb, 2 * S["r"], 2 * B["r"]))
                            continue
                        ts, tb_ = tol(comps[na]), tol(comps[nb])
                        ds = 2 * S["r"] + rng.normal(0, ts["hole_sd"], n) - (0.1 if na in fast else 0.0)   # a thread is made under size
                        db = 2 * B["r"] + tb_["hole_bias"] + rng.normal(0, tb_["hole_sd"], n)
                        clr = db - ds
                        if intent == "slide":
                            p_bad = float((clr < 0.0).mean())
                            what = "would not go in"
                        else:
                            p_bad = float((clr > -0.005).mean())
                            what = "would be loose instead of pressed"
                        if key in out and (out[key]["p_bad"] or 0.0) >= p_bad:
                            continue
                        out[key] = {"intent": intent, "nominal_clearance_mm": round(nominal, 3), "p_bad": round(p_bad, 3),
                                    "class": "simulated", "process": [process_of(comps[na]), process_of(comps[nb])]}
                        if p_bad > 0.02:
                            flagged.append((p_bad, na, nb, 2 * S["r"], nominal, intent, what))
    for na, nb, ds_, db_ in mismatch:
        r.add("error", "catalogue_fit_mismatch",
              f"{na} (dia {ds_:.2f}) in {nb} (bore {db_:.2f}): two purchased parts drawn with the shaft larger than the bore. "
              f"They are not made for each other.", parts=[na, nb], shaft_dia=round(ds_, 3), bore_dia=round(db_, 3),
              hint="Choose the bore size that matches the shaft (see the parts' interfaces['bore']).")
    if trusted:
        r.add("info", "catalogue_fits_trusted",
              f"{len(trusted)} shaft-in-bore pair(s) are between two purchased catalogue parts (or a purchased part on a screw's "
              f"shank) and were not simulated: their makers hold those fits. Listed in the metrics "
              f"(tolerance.shaft_bore_pairs.catalogue_fits): {', '.join(trusted[:8])}" + (" ..." if len(trusted) > 8 else "") + ".",
              pairs=trusted)
    seen = set()
    for p_bad, na, nb, dia, nominal, intent, what in sorted(flagged, reverse=True):
        if (na, nb, round(dia, 1)) in seen:
            continue
        seen.add((na, nb, round(dia, 1)))
        r.add("error" if p_bad > 0.25 else "warning", "fit_not_toleranced",
              f"{na} (dia {dia:.2f}) in {nb}: drawn with {nominal:+.2f} mm clearance and meant to {intent}; "
              f"it {what} in {p_bad:.0%} of builds ({process_of(comps[nb])} bore, {process_of(comps[na])} shaft).",
              parts=[na, nb], p_bad=round(p_bad, 3), intent=intent,
              hint=("Give the bore real clearance: about +0.1 mm on diameter for a machined slip fit, +0.3 mm in a printed part."
                    if intent == "slide" else
                    "Give it real interference (about 0.02-0.05 mm in metal), or retain it another way: clamp, set screw, adhesive, circlip."))
        if len(seen) >= 15:
            break
    return out
