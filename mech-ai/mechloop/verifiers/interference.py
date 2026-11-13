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
                for g in groups[1:]:
                    r.add("error", "floating_parts",
                          f"In body '{body}', {sorted(g)} do not touch the rest of the body "
                          f"(nothing holds them in place).",
                          body=body, parts=sorted(g),
                          hint="Parts in one rigid body must be in contact (bolted, seated or bonded). Close the gap or add the connecting part.")
        _fastening(design, contacts, r)
        r.metrics = {"pairs": n_pairs, "pairs_checked_exactly": n_exact,
                     "worst_overlap_mm3": round(worst, 2),
                     "contact_pairs": sum(len(v) for v in contacts.values()) // 2}
    return r


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
            for g in groups[1:]:
                parts = sorted(g - fasteners)
                touching = sorted({t for n in parts for t in contacts[n] & names} - g)
                r.add("error", "unfastened",
                      f"In body '{body}', {parts} {'is' if len(parts) == 1 else 'are'} not fastened to the rest "
                      f"(only resting against {touching or 'nothing'}).",
                      body=body, parts=parts, touching=touching,
                      hint="Add screws that pass through/into both parts (parts.add_screw), or declare the "
                           "real joint with design.join(a, b, kind) for a press fit, bond, clamp or set screw.")
