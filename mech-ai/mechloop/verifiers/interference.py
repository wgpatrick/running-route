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
        r.metrics = {"pairs": n_pairs, "pairs_checked_exactly": n_exact,
                     "worst_overlap_mm3": round(worst, 2),
                     "contact_pairs": sum(len(v) for v in contacts.values()) // 2}
    return r
