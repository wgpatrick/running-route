"""Walk a build plan step by step and ask, at each step, what a person at the bench would face:
does the part stay where it is put, which way does it go in, can it be fastened, with what tool."""
from __future__ import annotations

import numpy as np
import trimesh
from scipy.spatial import ConvexHull, QhullError

from ..geom import to_trimesh
from ..model import Design
from .planner import Plan, plan

# seconds; rough bench-assembly allowances, for comparing designs rather than predicting a clock time
T_PLACE, T_HOLD, T_BELOW, T_SIDE, T_TWO_STEP, T_SUBASM = 6.0, 10.0, 8.0, 2.0, 4.0, 12.0
T_SCREW, T_TNUT, T_SCREW_BELOW, T_TOOL_CHANGE, T_FLIP = 8.0, 6.0, 4.0, 4.0, 25.0


def _support(design: Design, parts: list[str], onto: list[str], up=np.array([0.0, 0.0, 1.0]),
             bench: float | None = None) -> dict:
    """Static rest test: is the unit's centre of mass over the patch of surface it rests on?
    `bench` is the height (along `up`) of the bench the assembly is lying on; a part whose
    underside is at that height rests on the bench."""
    comps = {c.name: c for c in design.components}
    if not onto and bench is None:
        return {"stable": False, "reason": "nothing to rest on"}
    below = trimesh.util.concatenate([to_trimesh(comps[o].shape) for o in onto]) if onto else None
    pts = []
    com, mass = np.zeros(3), 0.0
    for p in parts:
        m = to_trimesh(comps[p].shape)
        mk = comps[p].mass()
        com += mk * m.bounds.mean(axis=0)
        mass += mk
        down = np.flatnonzero(m.face_normals @ up < -0.5)
        if len(down) > 160:
            down = down[np.linspace(0, len(down) - 1, 160).astype(int)]
        if not len(down):
            continue
        # sample each downward-facing triangle at its centre and near its corners, so a flat
        # underside made of two triangles still gives a support patch with area
        tri = m.triangles[down]
        c0 = m.triangles_center[down]
        cen = np.vstack([c0] + [0.9 * tri[:, k] + 0.1 * c0 for k in range(3)])
        if bench is not None:
            on_bench = np.abs(cen @ up - bench) < 0.5
            if on_bench.any():
                pts.append(cen[on_bench])
        if below is None:
            continue
        hits = trimesh.ray.ray_triangle.RayMeshIntersector(below).intersects_location(
            cen + up * 0.05, np.tile(-up, (len(cen), 1)), multiple_hits=False)
        loc, ray_idx = hits[0], hits[1]
        if len(loc):
            gap = (cen[ray_idx] - loc) @ up
            pts.append(cen[ray_idx][np.abs(gap) < 0.15])
    com /= max(mass, 1e-12)
    pts = np.vstack(pts) if pts else np.zeros((0, 3))
    if len(pts) == 0:
        return {"stable": False, "reason": "no surface underneath it"}
    # project onto the plane perpendicular to "up"
    ref = np.array([1.0, 0, 0]) if abs(up[0]) < 0.9 else np.array([0, 1.0, 0])
    e1 = np.cross(up, ref); e1 /= np.linalg.norm(e1)
    e2 = np.cross(up, e1)
    xy = np.c_[pts @ e1, pts @ e2]
    c2 = np.array([com @ e1, com @ e2])
    try:
        hull = ConvexHull(xy)
        A, b = hull.equations[:, :2], hull.equations[:, 2]
        margin = float(-(A @ c2 + b).max())  # > 0: inside by this much
    except (QhullError, ValueError):
        d = np.linalg.norm(xy - c2, axis=1).min()
        margin = float(-d) if d > 1.0 else 0.0
    if margin < 0:
        return {"stable": False, "reason": f"centre of mass is {-margin:.0f} mm outside what it rests on", "margin_mm": round(margin, 1)}
    return {"stable": True, "margin_mm": round(margin, 1)}


def opposite_name(d: str) -> str:
    return ("-" if d[0] == "+" else "+") + d[1]


UPS = {"+Z": (0, 0, 1), "-Z": (0, 0, -1), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "+X": (1, 0, 0), "-X": (-1, 0, 0)}
UP_WORDS = {"+Z": "upright (as designed)", "-Z": "upside down", "+Y": "on its front (back face up)",
            "-Y": "on its back (front face up)", "+X": "on its left side (right side up)",
            "-X": "on its right side (left side up)"}


def _dir_class(dn: str, axis=None, up=(0, 0, 1)) -> str:
    """Which way a part or screw travels relative to gravity, for the assembly lying with `up` upward."""
    from .planner import DIRS

    v = np.array(axis, dtype=float) if (dn == "axis" and axis is not None) else np.array(DIRS.get(dn, (0, 0, -1)), dtype=float)
    z = float(v @ np.array(up, dtype=float)) / (np.linalg.norm(v) or 1.0)
    return "from above" if z < -0.5 else ("from below" if z > 0.5 else "from the side")


def analyse(design: Design, p: Plan | None = None, _depth: int = 0, reorient: bool = True) -> dict:
    """Simulate the build. With reorient=True the assembly may be turned onto any of its six sides
    between steps; the orientation schedule is chosen to minimise holding, awkward directions and flips."""
    p = p or plan(design)
    comps = {c.name: c for c in design.components}
    ups = UPS if reorient else {"+Z": UPS["+Z"]}
    names = list(ups)
    steps = p.steps[1:]
    n = len(steps)
    # cost of doing each step in each orientation
    cost = np.zeros((n, len(names)))
    info = [[None] * len(names) for _ in range(n)]
    from ..geom import to_trimesh as _tm

    from build123d import Location

    from ..geom import bboxes_overlap, overlap_volume
    from .planner import DIRS

    corners = {c.name: _tm(c.shape).bounds for c in design.components}
    installed = list(p.steps[0].parts)

    def blocked_dirs(st) -> dict:
        """Which of the six directions the unit cannot move in once placed (nudged 0.6 mm, exact overlap)."""
        out = {}
        pressed = any(frozenset((a, b)) in design.allowed_overlaps or frozenset((a, b)) in design.joins
                      and design.joins[frozenset((a, b))] in ("press", "press_fit", "bond", "glue")
                      for a in st.parts for b in st.onto)
        for dn, dv in DIRS.items():
            hit = pressed
            if not hit:
                for a in st.parts:
                    moved = comps[a].shape.moved(Location(tuple(0.6 * x for x in dv)))
                    for b in st.onto:
                        if bboxes_overlap(moved, comps[b].shape) and overlap_volume(moved, comps[b].shape)[0] > 0.3:
                            hit = True
                            break
                    if hit:
                        break
            out[dn] = hit
        return out
    for i, st in enumerate(steps):
        final = st.path[-1][0] if st.path else "-Z"
        blk = blocked_dirs(st) if st.kind != "fastener" else {}
        for k, un in enumerate(names):
            up = np.array(ups[un], dtype=float)
            how = _dir_class(final, st.axis, up)
            if st.kind == "fastener":
                c = T_SCREW_BELOW if how == "from below" else 0.0
                info[i][k] = (how, None)
            else:
                # the bench is under the lowest point of what is already built, in this orientation
                bench = min(float(min(corners[q][0] @ up, corners[q][1] @ up)) for q in installed)
                sup = _support(design, st.parts, st.onto, up, bench)
                # let go of it: is it blocked from falling, and from tipping?
                down = opposite_name(un)
                on_bench = any(abs(float(min(corners[q][0] @ up, corners[q][1] @ up)) - bench) < 0.5 for q in st.parts)
                cannot_fall = blk.get(down, False) or on_bench
                lateral = [d_ for d_ in DIRS if d_[1] != un[1]]
                captured = any(blk.get(a_, False) and blk.get(opposite_name(a_), False) for a_ in lateral)
                if not cannot_fall:
                    sup = {"stable": False, "reason": "nothing stops it falling"}
                elif sup["stable"] or captured:
                    sup = {"stable": True}
                else:
                    sup = {"stable": False, "reason": "it would tip or slide off (" + sup.get("reason", "") + ")"}
                c = (T_HOLD if not sup["stable"] else 0.0) + (T_BELOW if how == "from below" else T_SIDE if how == "from the side" else 0.0)
                info[i][k] = (how, sup)
            cost[i, k] = c
        installed += st.parts
    # dynamic programme over orientations: turning the assembly over costs T_FLIP
    if n:
        best = np.full((n, len(names)), np.inf)
        back = np.zeros((n, len(names)), dtype=int)
        start_pen = np.array([0.0 if un == "+Z" else T_FLIP for un in names])
        best[0] = cost[0] + start_pen
        for i in range(1, n):
            for k in range(len(names)):
                trans = best[i - 1] + np.where(np.arange(len(names)) == k, 0.0, T_FLIP)
                back[i, k] = int(trans.argmin())
                best[i, k] = trans.min() + cost[i, k]
        seq = [int(best[-1].argmin())]
        for i in range(n - 1, 0, -1):
            seq.append(int(back[i, seq[-1]]))
        seq.reverse()
    else:
        seq = []
    rows = [{"step": 0, "unit": p.steps[0].unit, "kind": p.steps[0].kind, "action": "start with", "onto": []}]
    time_s = 0.0
    counts = {"needs_holding": 0, "from_below": 0, "two_move_paths": 0, "unsupported_steps": 0}
    last_tool, tool_changes, tools, skus = None, 0, set(), set()
    subs, flips, prev_o = {}, 0, "+Z"
    for i, st in enumerate(steps):
        un = names[seq[i]]
        how, sup = info[i][seq[i]]
        row = {"step": i + 1, "unit": st.unit, "kind": st.kind, "parts": st.parts if st.kind == "subassembly" else None,
               "onto": st.onto[:6], "direction": how, "orientation": un,
               "path": [(d, None if not np.isfinite(dist) else round(dist, 1)) for d, dist in st.path]}
        t = 0.0
        if un != prev_o:
            flips += 1
            row["turn_assembly"] = UP_WORDS[un]
            t += T_FLIP
            prev_o = un
        if st.kind == "fastener":
            c = comps[st.unit]
            key = c.meta.get("interfaces", {}).get("hex_key")
            row["tool"] = f"{key:g} mm hex key" if key else "driver"
            t += T_SCREW + (T_TNUT if c.meta.get("tnut") else 0.0) + (T_SCREW_BELOW if how == "from below" else 0.0)
            if last_tool is not None and row["tool"] != last_tool:
                tool_changes += 1
                t += T_TOOL_CHANGE
            last_tool = row["tool"]
            tools.add(row["tool"])
            skus.add(c.sku or st.unit)
        else:
            row["rests_stably"] = sup["stable"]
            if not sup["stable"]:
                row["hold_reason"] = sup["reason"]
                counts["needs_holding"] += 1
            t += T_SUBASM if st.kind == "subassembly" else T_PLACE
            t += min(10.0, 3.0 * sum(comps[q].mass() for q in st.parts))
            t += (T_HOLD if not sup["stable"] else 0.0) + (T_BELOW if how == "from below" else T_SIDE if how == "from the side" else 0.0)
            if len(st.path) > 1:
                counts["two_move_paths"] += 1
                t += T_TWO_STEP
            if st.kind == "subassembly" and _depth < 2:
                inner = analyse(design, plan(design, members=st.parts), _depth + 1, reorient)
                subs[st.unit] = inner
                t += inner["metrics"]["estimated_time_s"]
        if how == "from below":
            counts["from_below"] += 1
        if st.unsupported:
            counts["unsupported_steps"] += 1
            row["unsupported"] = True
        row["seconds"] = round(t, 1)
        time_s += t
        rows.append(row)
    n_fast = sum(1 for s_ in p.steps if s_.kind == "fastener")
    metrics = {"complete": p.complete, "steps": len(p.steps), "parts": sum(len(s_.parts) for s_ in p.steps),
               "fasteners": n_fast, "fastener_types": len(skus), "tools": sorted(tools), "tool_changes": tool_changes,
               **counts, "times_assembly_is_turned": flips,
               "subassemblies": {k: v["metrics"]["estimated_time_s"] for k, v in subs.items()},
               "estimated_time_s": round(time_s, 0), "estimated_time_min": round(time_s / 60.0, 1),
               "trapped": sorted(p.trapped)}
    return {"plan": p, "rows": rows, "metrics": metrics, "subassemblies": subs}


def instructions(design: Design, res: dict, title: str | None = None) -> str:
    """Build instructions as markdown, one numbered step per part with its screws."""
    L = [f"# Build instructions: {title or design.name}", "",
         f"{res['metrics']['parts']} parts, {res['metrics']['fasteners']} screws, about "
         f"{res['metrics']['estimated_time_min']:.0f} minutes (rough allowance). Tools: {', '.join(res['metrics']['tools']) or 'none'}.", ""]
    for name, inner in res["subassemblies"].items():
        L += [f"## Sub-assembly: {name}", ""] + _steps_md(inner) + [""]
    L += ["## Main assembly", ""] + _steps_md(res)
    if res["metrics"]["trapped"]:
        L += ["", "**Cannot be installed as designed:** " + ", ".join(res["metrics"]["trapped"])]
    return "\n".join(L)


def _steps_md(res: dict) -> list[str]:
    out, n = [], 0
    rows = res["rows"]
    i = 0
    while i < len(rows):
        r = rows[i]
        if r.get("action") == "start with":
            out.append(f"{n + 1}. Start with **{r['unit']}** on the bench.")
            n += 1
            i += 1
            continue
        if r["kind"] == "fastener":
            if r.get("turn_assembly"):
                out.append(f"{n + 1}. Turn the assembly {r['turn_assembly']}.")
                n += 1
            j = i
            group = []
            while j < len(rows) and rows[j]["kind"] == "fastener" and rows[j].get("tool") == r.get("tool") \
                    and rows[j]["direction"] == r["direction"] and (j == i or not rows[j].get("turn_assembly")):
                group.append(rows[j]["unit"])
                j += 1
            out.append(f"{n + 1}. Drive {len(group)} screw{'s' if len(group) > 1 else ''} {r['direction']} with the {r['tool']}: "
                       + ", ".join(group[:8]) + (" ..." if len(group) > 8 else "") + ".")
            n += 1
            i = j
            continue
        if r.get("turn_assembly"):
            out.append(f"{n + 1}. Turn the assembly {r['turn_assembly']}.")
            n += 1
        what = f"the **{r['unit']}** sub-assembly" if r["kind"] == "subassembly" else f"**{r['unit']}**"
        path = r["path"]
        move = (f"move it {path[0][0]} then {path[1][0]} by {path[1][1]:.0f} mm" if len(path) > 1 and path[1][1]
                else f"bring it in {r['direction']} ({path[-1][0]})")
        line = f"{n + 1}. Fit {what} onto {', '.join(r['onto'][:3]) or 'the assembly'}: {move}."
        if r.get("rests_stably") is False:
            line += f" Hold it until fastened ({r['hold_reason']})."
        if r.get("unsupported"):
            line += " Nothing already in place supports it."
        out.append(line)
        n += 1
        i += 1
    return out
