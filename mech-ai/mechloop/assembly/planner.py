"""Assembly planning by disassembly, as a simulation of building the thing.

Units (single parts, or declared sub-assemblies moved as one) are removed from the
finished assembly one at a time along collision-free paths; reversing the order gives a
build sequence in which every unit has a way in. A unit may only come off when the
screws holding it are already out and when what remains is still connected to the base.
Paths are a straight pull, or two straight moves when a straight pull is blocked.

Sound when it finds a plan; when it does not, the report says what blocked each unit,
but a cleverer path (rotation, flexing a part) might exist.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import trimesh
from build123d import Cylinder, Location, Plane, Pos, Vector

from ..geom import bboxes_overlap, overlap_volume, to_trimesh, translation
from ..model import Design

VOL_TOL = 0.5
# removal directions, in order of preference: lifting off (so it goes ON from above) first, from below last
DIRS = {"+Z": (0, 0, 1), "+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "-Z": (0, 0, -1)}


def opposite(d: str) -> str:
    return ("-" if d[0] == "+" else "+") + d[1:] if d[0] in "+-" else d


@dataclass
class Step:
    unit: str
    parts: list[str]
    kind: str  # "part" | "fastener" | "subassembly"
    path: list[tuple[str, float]]  # insertion moves in order: (direction name, distance mm; inf = from clear)
    axis: tuple | None = None  # for fasteners: direction it is driven along
    onto: list[str] = field(default_factory=list)  # installed parts it touches when placed
    unsupported: bool = False  # nothing already in place connects it to the base


@dataclass
class Plan:
    base: str
    steps: list[Step]
    trapped: dict  # unit -> why
    unit_of: dict
    complete: bool
    exact_checks: int = 0


class _World:
    def __init__(self, design: Design):
        self.d = design
        self.comps = {c.name: c for c in design.components}
        self.mesh = {n: to_trimesh(c.shape) for n, c in self.comps.items()}
        self.bounds = {n: m.bounds for n, m in self.mesh.items()}
        self.fast = {f.name: f for f in design.fasteners if f.name in self.comps}
        self.exact_cache: dict = {}
        self.touch = {n: set() for n in self.comps}
        names = list(self.comps)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                if not bboxes_overlap(self.comps[a].shape, self.comps[b].shape, 0.05):
                    continue
                try:
                    near = self.comps[a].shape.distance_to(self.comps[b].shape) <= 0.05
                except Exception:
                    near = True
                if near:
                    self.touch[a].add(b); self.touch[b].add(a)
        for pair in design.joins:
            if len(pair) == 2 and all(n in self.comps for n in pair):
                a, b = tuple(pair)
                self.touch[a].add(b); self.touch[b].add(a)
        self.holds: dict[str, set[str]] = {}
        for f in self.fast.values():
            held = set(f.clamps) & set(self.comps)
            for pair in design.joins:
                if f.name in pair and len(pair) == 2:
                    held |= set(pair) - {f.name}
            held |= {n for n in self.touch[f.name] if n not in self.fast}
            self.holds[f.name] = held

    def exact(self, a: str, b: str, offset) -> float:
        k = (a, b, tuple(np.round(offset, 3)))
        if k not in self.exact_cache:
            moved = self.comps[a].shape.moved(Location(tuple(float(x) for x in offset)))
            self.exact_cache[k] = overlap_volume(moved, self.comps[b].shape)[0]
        return self.exact_cache[k]

    def allowed(self, a: str, b: str, vol: float) -> bool:
        lim = self.d.allowed_overlaps.get(frozenset((a, b)))
        if lim is None:
            return False
        return vol <= max(lim, self.exact(a, b, (0, 0, 0))) + VOL_TOL


def _steps(clear: float) -> np.ndarray:
    fine = [0.5, 1, 2, 3, 5, 8, 12]
    coarse = np.arange(16.0, clear + 8.0, 8.0)
    return np.unique(np.array([x for x in fine if x < clear] + coarse.tolist() + [clear]))


def plan(design: Design, base: str | None = None, members: list[str] | None = None,
         two_step: bool = True) -> Plan:
    """Plan the assembly of `members` (default: everything), honouring design.subassemblies."""
    W = _World(design)
    names = list(members) if members is not None else list(W.comps)
    nameset = set(names)
    # units: declared sub-assemblies (fully inside this scope, and not the scope itself) move as one
    unit_of = {n: n for n in names}
    units: dict[str, list[str]] = {n: [n] for n in names}
    for sname, parts in design.subassemblies.items():
        parts = [p for p in parts if p in nameset]
        if len(parts) >= 2 and set(parts) != nameset and all(unit_of[p] == p for p in parts):
            for p in parts:
                del units[p]
                unit_of[p] = sname
            units[sname] = parts
    base_part = base or design.base or max(names, key=lambda n: W.comps[n].shape.volume if W.comps[n].body == "world" else -1)
    if base_part not in nameset:
        base_part = max(names, key=lambda n: W.comps[n].shape.volume)
    base_unit = unit_of[base_part]
    cm = trimesh.collision.CollisionManager()
    for n in names:
        cm.add_object(n, W.mesh[n])
    remaining = set(units)

    def parts_left() -> set[str]:
        return {p for u in remaining for p in units[u]}

    def kind(u: str) -> str:
        return "subassembly" if len(units[u]) > 1 else ("fastener" if u in W.fast else "part")

    def held_by(u: str) -> set[str]:
        mem = set(units[u])
        left = parts_left()
        return {f for f, hs in W.holds.items() if f in left and f not in mem and (hs & mem) and unit_of.get(f) != u}

    def supported_without(u: str) -> bool:
        rest = parts_left() - set(units[u])
        seen, stack = set(), [base_part]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend((W.touch[n] & rest) - seen)
        return seen >= rest

    def sweep(u: str, d, start=np.zeros(3), limit: float | None = None) -> tuple[set[str], float]:
        """Move unit u from `start` offset along d. Returns (blockers, distance travelled when blocked/clear)."""
        d = np.array(d, dtype=float)
        d /= np.linalg.norm(d)
        mem = units[u]
        others = parts_left() - set(mem)
        if not others:
            return set(), 0.0
        lo = np.min([W.bounds[o][0] for o in others], axis=0)
        hi = np.max([W.bounds[o][1] for o in others], axis=0)
        blo = np.min([W.bounds[m][0] for m in mem], axis=0) + start
        bhi = np.max([W.bounds[m][1] for m in mem], axis=0) + start
        clear = max(float(np.max(np.where(d > 1e-9, (hi - blo) / np.where(d > 1e-9, d, 1), 0))),
                    float(np.max(np.where(d < -1e-9, (lo - bhi) / np.where(d < -1e-9, d, 1), 0))), 1.0) + 2.0
        if limit is not None:
            clear = min(clear, limit)
        for m in mem:
            cm.remove_object(m)
        blockers: set[str] = set()
        reached = clear
        last_free = 0.0
        try:
            for s in _steps(clear):
                off = start + d * s
                for m in mem:
                    hit, hits = cm.in_collision_single(W.mesh[m], transform=translation(off), return_names=True)
                    for o in hits if hit else ():
                        if o in blockers or o in mem:
                            continue
                        vol = W.exact(m, o, off)
                        if vol > VOL_TOL and not W.allowed(m, o, vol):
                            blockers.add(o)
                if blockers:
                    # refine how far it really gets before touching, by bisection on exact overlap
                    lo_s, hi_s = last_free, float(s)
                    for _ in range(6):
                        mid = 0.5 * (lo_s + hi_s)
                        offm = start + d * mid
                        hitm = any(W.exact(m, o, offm) > VOL_TOL and not W.allowed(m, o, W.exact(m, o, offm))
                                   for m in mem for o in blockers)
                        if hitm:
                            hi_s = mid
                        else:
                            lo_s = mid
                    reached = lo_s
                    break
                last_free = float(s)
        finally:
            for m in mem:
                cm.add_object(m, W.mesh[m])
        return blockers, reached

    def tool_blockers(f) -> set[str]:
        a = Vector(*f.axis).normalized()
        start = Vector(*f.head_center) + a * 0.3
        tool = Plane(origin=start, z_dir=a) * Pos(0, 0, f.tool_length / 2) * Cylinder(f.tool_diameter / 2, f.tool_length)
        out = set()
        for n in parts_left():
            if n == f.name or not bboxes_overlap(tool, W.comps[n].shape):
                continue
            if overlap_volume(tool, W.comps[n].shape)[0] > VOL_TOL:
                out.add(n)
        return out

    def find_exit(u: str):
        """Return (path as removal moves, None) or (None, blockers by direction)."""
        why = {}
        if kind(u) == "fastener":
            f = W.fast[u]
            b = W.bounds[u]
            dvec = np.array(f.axis, dtype=float) / np.linalg.norm(f.axis)
            length = float(np.dot(b[1] - b[0], np.abs(dvec))) + 2.0
            blk, _ = sweep(u, f.axis, limit=length)
            if not blk:
                blk = tool_blockers(f)
            if not blk:
                return [("axis", float("inf"))], None
            return None, {"axis": sorted(blk)}
        for dn, d in DIRS.items():
            blk, reached = sweep(u, d)
            if not blk:
                return [(dn, float("inf"))], None
            why[dn] = (sorted(blk), reached)
        if two_step:
            # back off along one direction as far as it goes, then leave along another
            for dn, (blk, reached) in sorted(why.items(), key=lambda kv: -kv[1][1]):
                if reached < 2.0:
                    continue
                for back in (reached - 0.2, reached * 0.75, reached / 2):
                    start = np.array(DIRS[dn], dtype=float) * back
                    for dn2, d2 in DIRS.items():
                        if dn2[1] == dn[1]:
                            continue
                        blk2, _ = sweep(u, d2, start=start)
                        if not blk2:
                            return [(dn, float(back)), (dn2, float("inf"))], None
        return None, {k: v[0] for k, v in why.items()}

    removed: list[Step] = []
    blocked_cache: dict[str, dict] = {}
    need_support, progress = True, True
    while len(remaining) > 1 and (progress or need_support):
        if not progress:
            need_support = False
        progress = False
        cands = sorted(remaining - {base_unit},
                       key=lambda u: (kind(u) != "fastener", sum(W.comps[p].shape.volume for p in units[u])))
        for u in cands:
            if kind(u) != "fastener" and held_by(u):
                continue
            if need_support and not supported_without(u):
                continue
            prev = blocked_cache.get(u)
            if prev is not None and all(set(b) & parts_left() for b in prev.values()) and len(prev) > 0:
                continue  # everything that blocked it last time is still there
            path, why = find_exit(u)
            if path is None:
                blocked_cache[u] = why
                continue
            rest = parts_left() - set(units[u])
            onto = sorted({t for p in units[u] for t in W.touch[p] & rest})
            st = Step(u, list(units[u]), kind(u), [(opposite(dn) if dn != "axis" else "axis", dist) for dn, dist in reversed(path)],
                      axis=tuple(-np.array(W.fast[u].axis)) if kind(u) == "fastener" else None, onto=onto,
                      unsupported=not supported_without(u))
            removed.append(st)
            remaining.discard(u)
            for p in units[u]:
                cm.remove_object(p)
            need_support = True
            progress = True
            break
    trapped = {}
    for u in sorted(remaining - {base_unit}):
        hb = sorted(held_by(u))
        if kind(u) != "fastener" and hb:
            trapped[u] = {"reason": "held", "held_by": hb}
        else:
            trapped[u] = {"reason": "blocked", "blocked_by": blocked_cache.get(u, {})}
    steps = [Step(base_unit, list(units[base_unit]), kind(base_unit), [], onto=[])] + list(reversed(removed))
    return Plan(base_part, steps, trapped, unit_of, not trapped, len(W.exact_cache))
