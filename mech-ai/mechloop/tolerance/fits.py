"""Will it go together? Screw patterns against their holes, and shafts against their bores,
built many times with each part made as accurately as its process allows."""
from __future__ import annotations

import math

import numpy as np
from build123d import Edge, GeomType
from OCP.BRepAdaptor import BRepAdaptor_Surface

from ..geom import bboxes_overlap
from ..model import Design
from ..report import VerifierResult
from .process import process_of, tol


def _hole_radius(part, a0, a1) -> float | None:
    """Radius of the hole a screw's shank passes through in `part` (None if the shank is not inside it)."""
    try:
        line = Edge.make_line(tuple(a0), tuple(a1))
        r = part.distance_to(line)
        return float(r)
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
        for name in set(f.clamps) | {c.name for c in design.components
                                     if c.name != f.name and c.name not in targets and not c.meta.get("thread_d")
                                     and bboxes_overlap(sc.shape, c.shape, 0.05)}:
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
        sb = 0.0 if all_tnut else tb["pos"]
        ea = rng.normal(0, ta["pos"], (n, k, 2))
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
        ok = (need <= (hole_r - screw_r)).all(axis=1)
        p_fit = float(ok.mean())
        nominal_clear = float(min(i["hole_r"] - i["d"] / 2 + 0.05 for i in items))
        out[f"{pa} -> {pb}"] = {"screws": k, "p_all_start": round(p_fit, 4), "nominal_radial_clearance_mm": round(nominal_clear, 3),
                                "process": [process_of(comps[pa]), process_of(comps[pb])]}
        if p_fit < 0.99:
            worst.append((p_fit, pa, pb, k, nominal_clear))
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
        out.append({"r": cyl.Radius(), "p": ax0, "d": axd, "shaft": outward, "len": length, "area": f.area})
    return out


def bores_and_shafts(design: Design, r: VerifierResult, n: int = 4000, seed: int = 1) -> dict:
    """A shaft drawn the same size as its bore fits half the time. Find those pairs and say how often
    they would bind (if meant to slide) or be loose (if meant to be pressed)."""
    rng = np.random.default_rng(seed)
    comps = {c.name: c for c in design.components}
    cyl = {}
    fast = {f.name for f in design.fasteners}
    names = [c.name for c in design.components if c.name not in fast]
    out, flagged = {}, []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if not bboxes_overlap(comps[a].shape, comps[b].shape, 0.05):
                continue
            if comps[a].meta.get("catalog") and comps[b].meta.get("catalog"):
                continue  # two catalog parts made to go together (pulley on its shaft) are toleranced by their makers
            for n_ in (a, b):
                if n_ not in cyl:
                    cyl[n_] = _cylinders(comps[n_].shape)
            for sa, sb, na, nb in ((cyl[a], cyl[b], a, b), (cyl[b], cyl[a], b, a)):
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
                        kind = design.joins.get(frozenset((na, nb)), "")
                        intent = "press" if any(w in str(kind) for w in ("press", "interference")) else "slide"
                        ts, tb_ = tol(comps[na]), tol(comps[nb])
                        ds = 2 * S["r"] + rng.normal(0, ts["hole_sd"], n)
                        db = 2 * B["r"] + tb_["hole_bias"] + rng.normal(0, tb_["hole_sd"], n)
                        clr = db - ds
                        nominal = 2 * (B["r"] - S["r"])
                        if intent == "slide":
                            p_bad = float((clr < 0.0).mean())
                            what = "would not go in"
                        else:
                            p_bad = float((clr > -0.005).mean())
                            what = "would be loose instead of pressed"
                        key = f"{na} in {nb} (dia {2 * S['r']:.2f})"
                        if key in out and out[key]["p_bad"] >= p_bad:
                            continue
                        out[key] = {"intent": intent, "nominal_clearance_mm": round(nominal, 3), "p_bad": round(p_bad, 3),
                                    "process": [process_of(comps[na]), process_of(comps[nb])]}
                        if p_bad > 0.02:
                            flagged.append((p_bad, na, nb, 2 * S["r"], nominal, intent, what))
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
