"""Can the parts physically come together?

Assembly-by-disassembly with directional blocking: repeatedly look for a part
that can be pulled straight out along a candidate direction without passing
through any part still in place. The reverse of the removal order is a valid
assembly sequence. Parts that can never be removed are reported with the parts
blocking each direction. Also checks driver/hex-key access to every fastener.

This is a sound "found a plan" test and an incomplete "no plan" test: parts
needing a curved or multi-step insertion path are reported as trapped.
"""
from __future__ import annotations

import numpy as np
import trimesh
from build123d import Axis, Cylinder, Location, Plane, Pos, Vector

from ..geom import bboxes_overlap, location_from_matrix, overlap_volume, to_trimesh, translation
from ..model import Design
from ..report import VerifierResult, timed

VOL_TOL = 0.5
DIRS = {"+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0),
        "+Z": (0, 0, 1), "-Z": (0, 0, -1)}


def _steps(clear: float) -> np.ndarray:
    fine = [0.5, 1, 2, 3, 5, 8, 12]
    coarse = np.arange(16.0, clear + 8.0, 8.0)
    s = np.array([x for x in fine if x < clear] + coarse.tolist() + [clear])
    return np.unique(s)


def verify_assemblability(design: Design, base: str | None = None) -> VerifierResult:
    r = VerifierResult("assemblability")
    comps = {c.name: c for c in design.components}
    if len(comps) < 2:
        r.skipped = "fewer than two parts"
        return r
    with timed(r):
        meshes = {n: to_trimesh(c.shape) for n, c in comps.items()}
        bounds = {n: m.bounds for n, m in meshes.items()}
        fast_axis = {f.name: tuple(float(x) for x in f.axis) for f in design.fasteners if f.name in comps}
        tools_names = set(fast_axis)
        base = base or design.base or max(comps, key=lambda n: comps[n].shape.volume if comps[n].body == "world" else -1)
        remaining = set(comps)
        cm = trimesh.collision.CollisionManager()
        for n in comps:
            cm.add_object(n, meshes[n])
        exact_cache: dict = {}
        blocked_by: dict[tuple[str, str], set[str]] = {}

        def exact(a: str, b: str, d: np.ndarray, s: float) -> float:
            k = (a, b, tuple(np.round(d * s, 3)))
            if k not in exact_cache:
                moved = comps[a].shape.moved(Location(tuple(d * s)))
                exact_cache[k] = overlap_volume(moved, comps[b].shape)[0]
            return exact_cache[k]

        def base_overlap(a: str, b: str) -> float:
            k = (a, b, "home")
            if k not in exact_cache:
                exact_cache[k] = overlap_volume(comps[a].shape, comps[b].shape)[0]
            return exact_cache[k]

        # which parts each fastener holds: anything it touches or threads into
        holds: dict[str, set[str]] = {}
        for f in design.fasteners:
            if f.name not in comps:
                continue
            held = set(f.clamps) & set(comps)
            for pair, kind in design.joins.items():
                if f.name in pair and len(pair) == 2:
                    held |= set(pair) - {f.name}
            fb = comps[f.name].shape
            for n, c in comps.items():
                if n == f.name or n in held or n in tools_names:
                    continue
                if bboxes_overlap(fb, c.shape, 0.05):
                    try:
                        if fb.distance_to(c.shape) <= 0.05:
                            held.add(n)
                    except Exception:
                        pass
            holds[f.name] = held

        # contact graph (touching, overlapping-by-intent or joined): used so that every part
        # is installed onto something already there, not left hanging in mid-air
        touch: dict[str, set[str]] = {n: set() for n in comps}
        names_l = list(comps)
        for i, a in enumerate(names_l):
            for b in names_l[i + 1:]:
                if not bboxes_overlap(comps[a].shape, comps[b].shape, 0.05):
                    continue
                try:
                    near = comps[a].shape.distance_to(comps[b].shape) <= 0.05
                except Exception:
                    near = True
                if near:
                    touch[a].add(b); touch[b].add(a)
        for pair in design.joins:
            if len(pair) == 2 and all(n in comps for n in pair):
                a, b = tuple(pair)
                touch[a].add(b); touch[b].add(a)

        def leaves_supported(name: str) -> bool:
            """After removing `name`, is everything left still connected to the base?"""
            rest = remaining - {name}
            seen, stack = set(), [base]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                stack.extend((touch[n] & rest) - seen)
            return seen >= rest

        def held_by(name: str) -> set[str]:
            return {fn for fn, hs in holds.items() if name in hs and fn in remaining}

        def try_remove(name: str, dname: str, d) -> set[str]:
            """Return the set of parts blocking removal of `name` along d (empty = free)."""
            d = np.array(d, dtype=float)
            d /= np.linalg.norm(d)
            others = remaining - {name}
            if not others:
                return set()
            lo = np.min([bounds[o][0] for o in others], axis=0)
            hi = np.max([bounds[o][1] for o in others], axis=0)
            b = bounds[name]
            # distance to carry the part's bbox fully past the others' bbox along d
            clear = max(float(np.max(np.where(d > 1e-9, (hi - b[0]) / np.where(d > 1e-9, d, 1), 0))),
                        float(np.max(np.where(d < -1e-9, (lo - b[1]) / np.where(d < -1e-9, d, 1), 0))), 1.0) + 2.0
            cm.remove_object(name)
            blockers: set[str] = set()
            try:
                for s in _steps(clear):
                    hit, names = cm.in_collision_single(meshes[name], transform=translation(d * s),
                                                        return_names=True)
                    for o in names if hit else ():
                        if o in blockers:
                            continue
                        allowed = design.allowed_overlaps.get(frozenset((name, o)))
                        vol = exact(name, o, d, float(s))
                        # an intended overlap (thread, press fit) may persist while it withdraws
                        if vol > VOL_TOL and not (allowed is not None and vol <= max(allowed, base_overlap(name, o)) + VOL_TOL):
                            blockers.add(o)
                    if blockers:
                        break
            finally:
                cm.add_object(name, meshes[name])
            return blockers

        tools = {f.name: f for f in design.fasteners if f.name in comps}
        tool_block: dict[str, set[str]] = {}
        tool_cache: dict[str, list[str]] = {}

        def tool_blockers(name: str) -> list[str]:
            if name not in tool_cache:
                tool_cache[name] = [b[0] for b in _tool_hits(design, tools[name])]
            return tool_cache[name]

        order: list[dict] = []
        progress = True
        need_support = True
        unsupported: list[str] = []
        while len(remaining) > 1 and (progress or need_support):
            if not progress:
                need_support = False  # stuck: allow a step that leaves something unsupported, and report it
            progress = False
            # fasteners first, then small parts: mirrors how things are actually taken apart
            cands = sorted(remaining - {base}, key=lambda n: (n not in fast_axis, comps[n].shape.volume))
            for name in cands:
                if name not in fast_axis and held_by(name):
                    continue  # still screwed down: its fasteners come out first
                if need_support and not leaves_supported(name):
                    continue
                dirs = dict(DIRS)
                if name in fast_axis:  # a screw only comes out along its axis, with a driver on it
                    dirs = {"axis": fast_axis[name]}
                for dname, d in dirs.items():
                    key = (name, dname)
                    if key in blocked_by and blocked_by[key] & remaining:
                        continue
                    blockers = try_remove(name, dname, d)
                    if not blockers and name in tools and dname == "axis":
                        blockers = {o for o in tool_blockers(name) if o in remaining}
                        tool_block[name] = blockers
                    blocked_by[key] = blockers
                    if not blockers:
                        if not need_support and not leaves_supported(name):
                            unsupported.append(name)
                        need_support = True
                        order.append({"part": name, "direction": dname})
                        remaining.discard(name)
                        cm.remove_object(name)
                        progress = True
                        break
                if progress:
                    break
        trapped = sorted(remaining - {base})
        for name in trapped:
            if name in tools:
                tb = sorted(tool_block.get(name, set()) & remaining)
                ab = sorted(blocked_by.get((name, "axis"), set()) & remaining)
                f = tools[name]
                blk = sorted(set(tb) | set(ab))
                r.add("error", "tool_access_blocked",
                      f"Fastener {name} cannot be driven: the screw and a {f.tool_diameter:.0f} mm x "
                      f"{f.tool_length:.0f} mm driver along its axis are blocked by {blk}, which must "
                      f"already be in place when it is installed.",
                      fastener=name, blockers=blk,
                      hint="Add an access hole in the blocking part, flip the fastener, or move it clear.")
                continue
            still = sorted(held_by(name))
            if still:
                r.add("error", "trapped_part",
                      f"{name} cannot be installed: it is held by fasteners {still} that themselves cannot be driven.",
                      part=name, held_by=still,
                      hint="Fix access to those fasteners first; this part is only stuck because they are.")
                continue
            why = {dn: sorted(blocked_by.get((name, dn), set()) & remaining) for dn in DIRS}
            common = sorted(set.intersection(*[set(v) for v in why.values()])) if why else []
            r.add("error", "trapped_part",
                  f"{name} cannot be installed/removed along any straight path; "
                  f"blocked by {sorted({b for v in why.values() for b in v})}.",
                  part=name, blocked_by_direction=why, always_blocking=common,
                  hint="Split the enclosing part, add an opening or slot along one direction, or reorder so the blocker installs later.")
        if unsupported and not trapped:
            r.add("warning", "unsupported_step",
                  f"The only assembly order found installs something before the part that supports it "
                  f"(around {sorted(set(unsupported))[:6]}); it would need holding in place or a sub-assembly.",
                  parts=sorted(set(unsupported)),
                  touching={n: sorted(touch[n])[:8] for n in sorted(set(unsupported))[:6]},
                  hint="These parts can only come off after the parts that connect their neighbours to the base. "
                       "Usually fine if they form a bench sub-assembly (e.g. motor on its plate); otherwise add "
                       "a locating feature or change which part carries the screws.")
        seq = [o["part"] for o in reversed(order)]
        r.metrics = {"base": base, "assembly_sequence": [base] + seq if len(seq) <= 200 else "omitted",
                     "insert_directions": {o["part"]: _opp(o["direction"]) for o in reversed(order)}
                     if len(order) <= 200 else "omitted",
                     "parts_placed": len(order) + 1, "parts_total": len(comps),
                     "complete": not trapped, "exact_overlap_checks": len(exact_cache)}
        if design.fasteners:
            ok = sum(1 for f in design.fasteners if f.name in comps and f.name not in trapped)
            r.metrics["fasteners_drivable_in_sequence"] = f"{ok}/{len(design.fasteners)}"
        for f in design.fasteners:
            if f.name not in comps:
                r.add("error", "unknown_fastener", f"Fastener '{f.name}' is not a component.", fastener=f.name)
    return r


def _opp(d: str) -> str:
    if d == "axis":
        return "along fastener axis"
    return ("-" if d[0] == "+" else "+") + d[1]


def _tool_hits(design: Design, f) -> list[tuple]:
    """Parts a driver on fastener f would pass through (in the fully assembled state)."""
    comps = {c.name: c for c in design.components}
    a = Vector(*f.axis).normalized()
    start = Vector(*f.head_center) + a * 0.3
    tool = Plane(origin=start, z_dir=a) * Pos(0, 0, f.tool_length / 2) * Cylinder(f.tool_diameter / 2, f.tool_length)
    hits = []
    for n, c in comps.items():
        if n == f.name or not bboxes_overlap(tool, c.shape):
            continue
        vol, where = overlap_volume(tool, c.shape)
        if vol > VOL_TOL:
            hits.append((n, round(vol, 1), where))
    return hits
