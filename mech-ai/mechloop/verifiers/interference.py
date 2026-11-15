"""Static assembly checks: interference, required clearances, floating parts."""
from __future__ import annotations

from itertools import combinations

from ..geom import bboxes_overlap, overlap_volume
from ..model import Design
from ..report import VerifierResult, timed

VOL_TOL = 0.5  # mm^3: below this an overlap is treated as touching
TOUCH_TOL = 0.02  # mm: parts closer than this are "in contact"


def verify_interference(design: Design) -> VerifierResult:
    r = VerifierResult("interference")
    with timed(r):
        comps = design.components
        contacts: dict[str, set[str]] = {c.name: set() for c in comps}
        n_pairs = n_exact = 0
        worst = 0.0
        for a, b in combinations(comps, 2):
            n_pairs += 1
            key = frozenset((a.name, b.name))
            need_gap = design.min_clearances.get(key)
            margin = max(TOUCH_TOL, need_gap or 0.0)
            if not bboxes_overlap(a.shape, b.shape, margin):
                continue
            n_exact += 1
            vol, where = overlap_volume(a.shape, b.shape)
            allowed = design.allowed_overlaps.get(key)
            if vol > VOL_TOL:
                contacts[a.name].add(b.name)
                contacts[b.name].add(a.name)
                if allowed is None or vol > allowed:
                    worst = max(worst, vol)
                    r.add("error", "interference",
                          f"{a.name} and {b.name} overlap by {vol:.1f} mm^3 near {where}.",
                          parts=[a.name, b.name], volume_mm3=round(vol, 2), at=where,
                          hint="Move/resize one part, add a pocket or hole, or declare allow_overlap for a real thread/press fit.")
                continue
            try:
                gap = a.shape.distance_to(b.shape)
            except Exception:
                gap = None
            if gap is not None and gap <= TOUCH_TOL:
                contacts[a.name].add(b.name)
                contacts[b.name].add(a.name)
            if need_gap is not None and gap is not None and gap < need_gap - 1e-6:
                r.add("error", "clearance",
                      f"{a.name} to {b.name} gap is {gap:.2f} mm, need >= {need_gap:.2f} mm.",
                      parts=[a.name, b.name], gap_mm=round(gap, 3), required_mm=need_gap)
        # Floating parts: within each rigid body every part must touch the rest of that body.
        for body, members in design.bodies().items():
            if len(members) < 2:
                continue
            names = {m.name for m in members}
            seen, stack = set(), [members[0].name]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                stack.extend((contacts[n] & names) - seen)
            # choose the largest connected group as the reference
            groups, left = [seen], names - seen
            while left:
                g, stack = set(), [next(iter(left))]
                while stack:
                    n = stack.pop()
                    if n in g:
                        continue
                    g.add(n)
                    stack.extend((contacts[n] & names) - g)
                groups.append(g)
                left -= g
            if len(groups) > 1:
                groups.sort(key=len, reverse=True)
                groups = groups[:1] + _not_free_standing(design, body, groups, r, "floating_parts")
                for g in groups[1:]:
                    r.add("error", "floating_parts",
                          f"In body '{body}', {sorted(g)} do not touch the rest of the body "
                          f"(nothing holds them in place).",
                          body=body, parts=sorted(g),
                          hint="Parts in one rigid body must be in contact (bolted, seated or bonded). Close the gap or add the connecting part.")
        _fastening(design, contacts, r)
        _threads(design, r)
        cpl = _coupler_insertion(design, r)
        r.metrics = {**({"coupler_shaft_insertion": cpl} if cpl else {}), "pairs": n_pairs, "pairs_checked_exactly": n_exact,
                     "worst_overlap_mm3": round(worst, 2),
                     "contact_pairs": sum(len(v) for v in contacts.values()) // 2}
    return r


def _not_free_standing(design: Design, body: str, groups: list, r, what: str) -> list:
    """Of the connected groups of a body (largest first), those that are still a fault once declared free-standing
    units (design.free_standing) are taken out. A unit is accepted only on the fixed world, only as ONE connected
    group (a unit whose own parts fall apart is still reported), and only if every part of the group other than
    screws and nuts is listed in it. The reference group (groups[0]) may itself be a unit; it is never returned."""
    units = {k: set(v) for k, v in (getattr(design, "free_standing", None) or {}).items()}
    if not units:
        return groups[1:]
    hardware = {f.name for f in design.fasteners} | {c.name for c in design.components if (c.sku or "").startswith(("SHCS", "NUT"))}
    known = {c.name for c in design.components}
    if r is not None:
        for k, v in units.items():
            for n in sorted(v - known):
                r.add("error", "unknown_part_reference", f"Free-standing unit '{k}' lists '{n}', which is not a part.", name=n)
    used = set()

    def unit_of(g):
        core = g - hardware
        return next((k for k, v in units.items() if core and core <= v), None)

    u0 = unit_of(groups[0])
    if u0:
        used.add(u0)
    bad = []
    for g in groups[1:]:
        u = unit_of(g)
        if body == "world" and u is not None and u not in used:
            used.add(u)
            continue
        bad.append(g)
    return bad


def _fastening(design: Design, contacts: dict[str, set[str]], r: VerifierResult) -> None:
    """Touching is not holding. Within each rigid body, every part must be tied to
    the rest by a fastener it touches or by a declared joint (design.join)."""
    fasteners = {f.name for f in design.fasteners}
    if not fasteners and not design.joins:
        r.add("info", "fastening_not_checked",
              "No fasteners or joins declared, so how parts are held together was not checked.")
        return
    known = {c.name for c in design.components}
    for pair in list(design.joins) + list(design.allowed_overlaps) + list(design.min_clearances):
        for n in pair:
            if n not in known:
                r.add("error", "unknown_part_reference", f"A join/overlap/clearance refers to '{n}', which is not a part.",
                      name=n)
    for body, members in design.bodies().items():
        names = {m.name for m in members}
        if len(names - fasteners) < 2:
            continue
        adj: dict[str, set[str]] = {n: set() for n in names}
        for fn in fasteners & names:
            for other in contacts[fn] & names:
                adj[fn].add(other)
                adj[other].add(fn)
        for f in design.fasteners:  # parts a screw is declared to clamp (it may pass through clearance holes)
            if f.name in names:
                for other in set(f.clamps) & names:
                    adj[f.name].add(other)
                    adj[other].add(f.name)
        for pair in design.joins:
            if len(pair) != 2:
                continue
            a, b = tuple(pair)
            if a in names and b in names:
                adj[a].add(b)
                adj[b].add(a)
        groups, left = [], set(names)
        while left:
            g, stack = set(), [next(iter(left))]
            while stack:
                n = stack.pop()
                if n in g:
                    continue
                g.add(n)
                stack.extend(adj[n] - g)
            groups.append(g)
            left -= g
        groups = [g for g in groups if g - fasteners]
        if len(groups) > 1:
            groups.sort(key=lambda g: -sum(design.get(n).mass() for n in g))
            groups = groups[:1] + _not_free_standing(design, body, groups, None, "unfastened")
            for g in groups[1:]:
                parts = sorted(g - fasteners)
                touching = sorted({t for n in parts for t in contacts[n] & names} - g)
                r.add("error", "unfastened",
                      f"In body '{body}', {parts} {'is' if len(parts) == 1 else 'are'} not fastened to the rest "
                      f"(only resting against {touching or 'nothing'}).",
                      body=body, parts=parts, touching=touching,
                      hint="Add screws that pass through/into both parts (parts.add_screw), or declare the "
                           "real joint with design.join(a, b, kind) for a press fit, bond, clamp or set screw.")


STANDARD_LENGTHS_MM = (3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60)      # ISO 4762 preferred lengths

THREAD_FACTOR = {"steel": 1.0, "stainless304": 1.0, "brass": 1.0, "al6061": 1.5,  # x thread diameter; plastics 2.0
                 # cast tooling plate yields at 105 / 124 MPa against 276 for 6061-T6: kept at the soft-material 2.0
                 "al_mic6": 2.0, "al_atp5": 2.0}


def _threads(design: Design, r: VerifierResult) -> None:
    """Each screw must engage enough thread in the part it screws into."""
    import numpy as np

    comps = {c.name: c for c in design.components}
    axis_of = {f.name: np.array(f.axis, dtype=float) for f in design.fasteners}
    short = 0
    for c in design.components:
        d = c.meta.get("thread_d")
        if not d or c.meta.get("tnut") or c.name not in axis_of:
            continue
        a = axis_of[c.name] / np.linalg.norm(axis_of[c.name])
        for tgt in c.meta.get("threads_into", []):
            if tgt not in comps:
                continue
            try:
                common = c.shape.intersect(comps[tgt].shape)
            except Exception:
                common = None
            eng = 0.0
            items = common if isinstance(common, (list, tuple)) else ([common] if common is not None else [])
            for it in items:
                try:
                    bb = it.bounding_box()
                except Exception:
                    continue
                corners = np.array([[x, y, z] for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
                                    for z in (bb.min.Z, bb.max.Z)])
                pr = corners @ a
                eng = max(eng, float(pr.max() - pr.min()))
            need = THREAD_FACTOR.get(comps[tgt].material, 2.0) * d
            tsku = comps[tgt].sku or ""
            if tsku.startswith("NUT-"):  # a standard nut is full strength once the screw passes through it
                need = comps[tgt].meta.get("interfaces", {}).get("height", d * 0.8)
            depth = comps[tgt].meta.get("interfaces", {}).get("thread_depth")
            fits = None
            if depth is not None:  # a catalog part's own tapped hole: using its full depth is what the vendor intends
                need = min(need, depth - 0.3)
                # The vendor's depth is a MAXIMUM penetration, not a requirement. Screws come in standard lengths, so
                # through a given stack only some engagements exist. If no standard length reaches `need` without
                # bottoming out, the longest one that stays inside the hole is what the vendor's own screw does
                # (Mean Well "4-M4 L=3mm" through a 4 mm panel: M4 x 6 gives 2.0 mm, M4 x 8 would give 4.0): accept
                # it, down to half a diameter of thread (2 to 3 turns), below which the stack must change.
                sb_ = c.shape.bounding_box()
                length = float(abs(np.array([sb_.size.X, sb_.size.Y, sb_.size.Z]) @ np.abs(a))) - float(c.meta.get("interfaces", {}).get("head_h", 0.0))
                grip = length - eng                      # what the screw passes through before the thread starts
                fits = [L - grip for L in STANDARD_LENGTHS_MM if 0.0 < L - grip <= depth + 0.05]
                if fits and max(fits) < need - 0.05:
                    need = max(max(fits), 0.5 * d)
            if depth is not None and eng > depth + 0.05:
                r.add("error", "thread_bottoms_out",
                      f"{c.name} goes {eng:.1f} mm into {tgt}, whose tapped holes are only {depth:.1f} mm deep.",
                      screw=c.name, into=tgt, engagement_mm=round(eng, 2), depth_mm=depth,
                      hint="Use a shorter screw or a thicker part under the head.")
            if eng < need - 0.05:
                short += 1
                r.add("error", "thread_engagement",
                      f"{c.name} engages only {eng:.1f} mm of thread in {tgt} ({comps[tgt].material}); "
                      f"an M{d:g} needs >= {need:.1f} mm there.",
                      screw=c.name, into=tgt, engagement_mm=round(eng, 2), required_mm=round(need, 2),
                      hint="Use a longer screw, thicken the tapped part, or use a nut / threaded insert.")


def _coupler_insertion(design: Design, r: VerifierResult) -> dict:
    """How far each shaft goes into a coupler, against how far a shaft of that size can go (`max_insertion_a` /
    `max_insertion_b` of the catalogue coupler: where it would meet the elastomer spider). Measured as the reach, along
    the coupler's axis from that end, of whatever other part lies on the axis inside the bore's diameter. A shaft drawn
    deeper also overlaps the coupler's solid (reported as `interference`); this finding gives the numbers, and holds
    even where an overlap was allowed."""
    import numpy as np
    from build123d import Cylinder, Pos

    from ..geom import location_from_matrix

    out: dict = {}
    for c in design.components:
        itf = c.meta.get("interfaces") or {}
        if "max_insertion_a" not in itf or not c.meta.get("placement"):
            continue
        P = np.vstack([np.array(c.meta["placement"], dtype=float), [0, 0, 0, 1]])
        o, z = P[:3, 3], P[:3, 2]
        L = float(itf["length"])
        loc = location_from_matrix(P)
        ends = (("a", float(itf["bore_a"]), float(itf["max_insertion_a"]), 1.0, 0.0),
                ("b", float(itf["bore_b"]), float(itf["max_insertion_b"]), -1.0, L))
        for end, bore, limit, sgn, z_end in ends:
            probe = (Pos(0, 0, L / 2) * Cylinder(bore / 2 - 0.05, L)).moved(loc)
            best = None
            for other in design.components:
                if other is c or other.body != c.body or (other.sku or "").startswith(("SHCS", "NUT")):
                    continue
                if not bboxes_overlap(other.shape, probe, 0.0):
                    continue
                try:
                    common = other.shape & probe
                except Exception:
                    continue
                sols = common.solids() if common is not None else []
                if not sols or sum(x.volume for x in sols) < VOL_TOL:
                    continue
                zs = []
                for so in sols:
                    bb = so.bounding_box()
                    for x in (bb.min.X, bb.max.X):
                        for y in (bb.min.Y, bb.max.Y):
                            for zz in (bb.min.Z, bb.max.Z):
                                zs.append(float((np.array([x, y, zz]) - o) @ z))
                # the part must enter from this end: it reaches the end face and the larger part of it is outside that end
                ob = other.shape.bounding_box()
                ctr = float((np.array([(ob.min.X + ob.max.X) / 2, (ob.min.Y + ob.max.Y) / 2, (ob.min.Z + ob.max.Z) / 2]) - o) @ z)
                if (sgn > 0 and (min(zs) > 0.3 or ctr > L / 2)) or (sgn < 0 and (max(zs) < L - 0.3 or ctr < L / 2)):
                    continue
                depth = (max(zs) - z_end) if sgn > 0 else (z_end - min(zs))
                if best is None or depth > best[1]:
                    best = (other.name, depth)
            if best is None:
                continue
            name, depth = best
            out[f"{c.name}:{end}"] = {"shaft": name, "bore_mm": bore, "insertion_mm": round(depth, 2), "max_insertion_mm": limit,
                                      **({"clamped_bore_depth_mm": itf["bore_depth"]} if "bore_depth" in itf else {})}
            if depth > limit + 0.05:
                r.add("error", "shaft_too_deep_in_coupler",
                      f"{name} is drawn {depth:.1f} mm into the {bore:g} mm bore of {c.name}, but a shaft of that size can enter "
                      f"only {limit:g} mm before it meets the coupler's elastomer spider: {depth - limit:.1f} mm too deep.",
                      shaft=name, coupler=c.name, insertion_mm=round(depth, 2), max_insertion_mm=limit,
                      too_deep_mm=round(depth - limit, 2),
                      hint=f"Move the shaft {depth - limit:.1f} mm out of the coupler (or the coupler and what drives it the other "
                           f"way). The hub clamps {itf.get('bore_depth', limit):g} mm of shaft.")
    return out
