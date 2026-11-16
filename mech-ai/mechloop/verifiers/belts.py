"""Belt checks: the route must keep a constant length as the machine moves
(otherwise the belt goes slack or binds), must fit the belt you intend to buy,
and its straight runs must not pass through other parts.

Clearance (warnings, BLT-060 / BLT-061): a straight run that comes within RUN_CLEARANCE_MM of a part the belt slides
past, or a pulley or idler within PULLEY_PLATE_CLEARANCE_MM of a made (non-bought) part, rubs as soon as the belt
flutters, the tension changes or a flange wobbles. The overlap test above only catches a run that is already inside a
part (more than 0.5 mm^3). Override the thresholds with design.practice["limits"]["BLT-060.run_clearance_mm"] and
["BLT-061.pulley_plate_clearance_mm"]."""
from __future__ import annotations

import math

import numpy as np
from build123d import Box, Plane, Pos

from ..geom import bboxes_overlap, forward_kinematics, location_from_matrix, overlap_volume
from ..model import Belt, Design
from ..report import VerifierResult

LEN_TOL = 0.3  # mm of length change over travel a tensioned belt can absorb
# Clearance a straight belt run keeps from any part it slides past (the belt flutters a millimetre or two at speed and
# rides up a flange edge when out of tension), and a pulley or idler from a stationary made part next to it (axial play
# of the bearing or set-screw hub, flange run-out). RECALLED shop practice, not a published figure: warnings only.
RUN_CLEARANCE_MM = 3.0
PULLEY_PLATE_CLEARANCE_MM = 2.0


def clearance_limits(design: Design) -> tuple[float, float]:
    """(run clearance, pulley-to-plate clearance) in mm: the module constants unless design.practice["limits"] says."""
    lim = ((getattr(design, "practice", None) or {}).get("limits") or {})
    return (float(lim.get("BLT-060.run_clearance_mm", RUN_CLEARANCE_MM)),
            float(lim.get("BLT-061.pulley_plate_clearance_mm", PULLEY_PLATE_CLEARANCE_MM)))


def _world_bbox(lb, T):
    """Axis-aligned world box of a local bounding box moved by T (8 corners)."""
    cs = np.array([[x, y, z, 1.0] for x in (lb.min.X, lb.max.X) for y in (lb.min.Y, lb.max.Y) for z in (lb.min.Z, lb.max.Z)])
    w = (T @ cs.T).T[:, :3]
    return w.min(axis=0), w.max(axis=0)


def _boxes_near(a, b, gap):
    return bool(np.all(a[0] - gap <= b[1]) and np.all(b[0] - gap <= a[1]))


def _basis(axis):
    a = np.array(axis, dtype=float)
    a /= np.linalg.norm(a)
    ref = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, ref)
    u /= np.linalg.norm(u)
    v = np.cross(a, u)
    return a, u, v


def route(design: Design, belt: Belt, T: dict) -> dict:
    """Belt geometry at a pose: total length and the straight runs (3D)."""
    comps = {c.name: c for c in design.components}
    a, u, v = _basis(belt.axis)
    nodes = []
    for node in belt.path:
        if node[0] == "pulley":
            c = comps[node[1]]
            ctr = c.meta.get("interfaces", {}).get("belt_center")
            if not ctr or "pitch_diameter_mm" not in c.ratings:
                raise ValueError(f"'{node[1]}' is not a catalog pulley/idler (no belt_center / pitch diameter)")
            p = (T[c.body] @ np.array([*ctr[0], 1.0]))[:3]
            nodes.append((p, c.ratings["pitch_diameter_mm"] / 2, 1.0 if node[2] == "ccw" else -1.0, node[1]))
        elif node[0] == "anchor":
            p = (T[node[1]] @ np.array([*node[2], 1.0]))[:3]
            nodes.append((p, 0.0, 1.0, None))
        else:
            raise ValueError(f"unknown belt node kind '{node[0]}'")
    closed = belt.path[0][0] == "pulley" and belt.path[-1][0] == "pulley"
    P2 = [np.array([n[0] @ u, n[0] @ v]) for n in nodes]
    h = [float(n[0] @ a) for n in nodes]
    pairs = [(i, (i + 1) % len(nodes)) for i in range(len(nodes) if closed else len(nodes) - 1)]
    segs, length = [], 0.0
    tan_in, tan_out = {}, {}
    for i, j in pairs:
        d = P2[j] - P2[i]
        D = float(np.linalg.norm(d))
        k = nodes[j][2] * nodes[j][1] - nodes[i][2] * nodes[i][1]
        if D < 1e-9 or abs(k) > D:
            raise ValueError(f"belt '{belt.name}': pulleys {i} and {j} overlap, no tangent run exists")
        th = math.atan2(d[1], d[0]) + math.acos(k / D)
        n = np.array([math.cos(th), math.sin(th)])
        pi = P2[i] - nodes[i][2] * nodes[i][1] * n
        pj = P2[j] - nodes[j][2] * nodes[j][1] * n
        tan_out[i], tan_in[j] = pi, pj
        length += float(np.linalg.norm(pj - pi))
        segs.append((pi[0] * u + pi[1] * v + h[i] * a, pj[0] * u + pj[1] * v + h[j] * a))
    wraps = {}
    for idx, (p, r, s, name) in enumerate(nodes):
        if r > 0 and idx in tan_in and idx in tan_out:
            a_in = math.atan2(*(tan_in[idx] - P2[idx])[::-1])
            a_out = math.atan2(*(tan_out[idx] - P2[idx])[::-1])
            sweep = ((a_out - a_in) * s) % (2 * math.pi)
            length += r * sweep
            wraps[name] = math.degrees(sweep)
    return {"length": length, "segments": segs, "wraps_deg": wraps, "heights": h, "closed": closed}


def verify_belts(design: Design, r: VerifierResult, poses: list[dict]) -> None:
    belted = {n[1] for b in design.belts for n in b.path if n[0] == "pulley"}
    for j in design.joints:
        if j.drive and j.drive.get("kind") == "belt":
            pul = j.drive.get("pulley")
            if pul is None or pul not in belted:
                r.add("error", "belt_missing",
                      f"Joint {j.name} is belt-driven but no Belt runs around its drive pulley"
                      f"{'' if pul else ' (name it with drive[\'pulley\'])'}; the drive is not connected to the load.",
                      joint=j.name,
                      hint="Add an idler, anchors on the moving body and a Belt in design.belts.")
    if not design.belts:
        return
    comps = {c.name: c for c in design.components}
    out = {}
    for belt in design.belts:
        try:
            for node in belt.path:
                if node[0] == "pulley" and node[1] not in comps:
                    raise ValueError(f"pulley '{node[1]}' is not a part")
            home = route(design, belt, forward_kinematics(design, {}))
            lengths = []
            for q in poses:
                lengths.append((route(design, belt, forward_kinematics(design, q))["length"], q))
        except ValueError as e:
            r.add("error", "belt_invalid", f"Belt {belt.name}: {e}.", belt=belt.name)
            continue
        ls = np.array([x[0] for x in lengths])
        spread = float(ls.max() - ls.min())
        m = {"length_mm": round(home["length"], 2), "length_change_over_travel_mm": round(spread, 3),
             "wrap_deg": {k: round(v, 1) for k, v in home["wraps_deg"].items()}}
        if spread > LEN_TOL:
            worst = lengths[int(np.abs(ls - home["length"]).argmax())]
            r.add("error", "belt_length_changes",
                  f"Belt {belt.name} path length changes by {spread:.2f} mm over the travel "
                  f"({home['length']:.2f} mm at home, {worst[0]:.2f} mm at {({k: round(v, 1) for k, v in worst[1].items()})}); "
                  f"it would go slack or bind.", belt=belt.name, change_mm=round(spread, 3),
                  hint="Belt runs that lengthen with travel must be parallel to the motion; put the anchors on the "
                       "tangent line between the pulleys and keep both pulleys on the same body.")
        # a wrong wrap sense makes the belt cross itself
        P = [(np.array([p0 @ _basis(belt.axis)[1], p0 @ _basis(belt.axis)[2]]),
              np.array([p1 @ _basis(belt.axis)[1], p1 @ _basis(belt.axis)[2]])) for p0, p1 in home["segments"]]

        def _cross(s1, s2):
            (a0, a1), (b0, b1) = s1, s2
            d1, d2 = a1 - a0, b1 - b0
            den = d1[0] * d2[1] - d1[1] * d2[0]
            if abs(den) < 1e-9:
                return False
            t = ((b0[0] - a0[0]) * d2[1] - (b0[1] - a0[1]) * d2[0]) / den
            u_ = ((b0[0] - a0[0]) * d1[1] - (b0[1] - a0[1]) * d1[0]) / den
            return 0.02 < t < 0.98 and 0.02 < u_ < 0.98

        if any(_cross(P[i], P[k]) for i in range(len(P)) for k in range(i + 1, len(P))):
            r.add("error", "belt_crossed",
                  f"Belt {belt.name} crosses itself; a pulley's wrap sense is probably reversed.", belt=belt.name,
                  hint="Wrap sense follows the right-hand rule about `axis`: 'ccw' is counter-clockwise when you "
                       "look from the tip of the axis vector back toward the pulley.")
        # belt ends must be clamped to something real
        for node in belt.path:
            if node[0] != "anchor":
                continue
            from build123d import Vertex

            vtx = Vertex(*node[2])
            near = min((c.shape.distance_to(vtx) for c in design.components if c.body == node[1]), default=1e9)
            if near > 2.0:
                r.add("error", "belt_anchor_in_air",
                      f"Belt {belt.name}: anchor at {tuple(round(x, 1) for x in node[2])} is {near:.1f} mm from the "
                      f"nearest part of body '{node[1]}'; nothing clamps the belt there.", belt=belt.name,
                      hint="Put the anchor on a clamp feature that is part of (and fastened to) that body.")
        hs = home["heights"]
        if max(hs) - min(hs) > 0.5:
            r.add("error", "belt_misaligned",
                  f"Belt {belt.name}: pulleys/anchors are not in one plane (spread {max(hs) - min(hs):.2f} mm along "
                  f"the pulley axis); the belt would track off.", belt=belt.name)
        for name, w in home["wraps_deg"].items():
            teeth = comps[name].ratings.get("teeth")
            if teeth and w * teeth / 360.0 < 6 and any(
                    j.drive and j.drive.get("pulley") == name for j in design.joints):
                r.add("error", "belt_low_wrap",
                      f"Belt {belt.name} engages only {w * teeth / 360.0:.1f} teeth on drive pulley {name} "
                      f"(need >= 6).", belt=belt.name, pulley=name)
        if home["closed"] and belt.stock_length is not None:
            diff = home["length"] - belt.stock_length
            m["stock_length_mm"] = belt.stock_length
            if abs(diff) > belt.adjust:
                r.add("error", "belt_wrong_length",
                      f"Belt {belt.name}: the route needs {home['length']:.1f} mm but the stock belt is "
                      f"{belt.stock_length:.0f} mm ({diff:+.1f} mm, adjustment available {belt.adjust} mm).",
                      belt=belt.name, hint="Change the centre distance, or pick the nearest stock length (multiples of the pitch).")
        # straight runs must not pass through anything, at home and at the travel extremes
        own = {n[1] for n in belt.path if n[0] == "pulley"}
        a, _, _ = _basis(belt.axis)
        hit: dict[str, dict] = {}
        check = [{}] + [q for q in poses if len(q) == 1][::2] + [q for q in poses if len(q) > 1][:40]
        for q in check:
            T = forward_kinematics(design, q)
            rt = route(design, belt, T)
            for p0, p1 in rt["segments"]:
                L = float(np.linalg.norm(p1 - p0))
                if L < 2.0:
                    continue
                t = (p1 - p0) / L
                seg = Plane(origin=tuple((p0 + p1) / 2), x_dir=tuple(t), z_dir=tuple(a)) * Box(L - 1.0, belt.thickness, belt.width)
                for c in design.components:
                    if c.name in own or c.name in hit:
                        continue
                    shp = c.shape.moved(location_from_matrix(T[c.body]))
                    if not bboxes_overlap(seg, shp):
                        continue
                    vol, where = overlap_volume(seg, shp)
                    if vol > 0.5:
                        hit[c.name] = {"volume_mm3": round(vol, 1), "at": where,
                                       "pose": {k: round(v, 1) for k, v in q.items()} or "home"}
        for name, hdat in hit.items():
            r.add("error", "belt_collision",
                  f"Belt {belt.name} passes through {name} near {hdat['at']} (pose {hdat['pose']}).",
                  belt=belt.name, part=name, **hdat,
                  hint="Move the pulleys/anchors so the run clears the part, or cut a slot for the belt.")
        m["clear_of_parts"] = not hit
        m["clearance"] = belt_clearances(design, belt, check, skip=set(hit), r=r)
        out[belt.name] = m
    r.metrics["belts"] = out


def belt_clearances(design: Design, belt: Belt, poses: list[dict], skip=frozenset(), r: VerifierResult | None = None) -> dict:
    """BLT-060 / BLT-061. Runs: every straight run, at each pose, against every part the belt slides past, that is every
    part except the belt's own pulleys and the parts on the body (or bodies) its anchors ride on, which move with the
    belt. A run is trimmed at each pulley end by the pulley's outer radius (its own flanges and axle hardware are there
    by design). Pulleys: each pulley or idler of the belt against every made part (not bought) other than those joined to
    it; parts on another body are taken at every pose. Returns the closest approach per part; warnings when under the
    limits (parts already reported as a collision are skipped)."""
    run_lim, pul_lim = clearance_limits(design)
    comps = {c.name: c for c in design.components}
    own = {n[1] for n in belt.path if n[0] == "pulley"}
    moving_with = {n[1] for n in belt.path if n[0] == "anchor"}
    joined = {}
    for pair in (getattr(design, "joins", None) or {}):
        pr = tuple(pair)
        if len(pr) == 2:
            joined.setdefault(pr[0], set()).add(pr[1])
            joined.setdefault(pr[1], set()).add(pr[0])
    lbb = {c.name: c.shape.bounding_box() for c in design.components}
    rad = {}
    for pn in own:
        b = lbb[pn]
        rad[pn] = max(b.max.X - b.min.X, b.max.Y - b.min.Y) / 2.0
    a, _, _ = _basis(belt.axis)
    runs_close: dict[str, dict] = {}
    pul_close: dict[tuple, dict] = {}
    path_names = [n[1] if n[0] == "pulley" else None for n in belt.path]
    for q in poses:
        T = forward_kinematics(design, q)
        rt = route(design, belt, T)
        wbb = {n: _world_bbox(lbb[n], T[comps[n].body]) for n in comps}
        nseg = len(rt["segments"])
        for k, (p0, p1) in enumerate(rt["segments"]):
            L = float(np.linalg.norm(p1 - p0))
            if L < 2.0:
                continue
            t = (p1 - p0) / L
            i0, i1 = k, (k + 1) % len(path_names)
            c0 = rad.get(path_names[i0], 1.0) if path_names[i0] else 1.0
            c1 = rad.get(path_names[i1], 1.0) if path_names[i1] else 1.0
            if L - c0 - c1 < 1.0:
                continue
            q0, q1 = p0 + t * c0, p1 - t * c1
            seg = Plane(origin=tuple((q0 + q1) / 2), x_dir=tuple(t), z_dir=tuple(a)) * Box(float(np.linalg.norm(q1 - q0)), belt.thickness, belt.width)
            sb = seg.bounding_box()
            sbb = (np.array([sb.min.X, sb.min.Y, sb.min.Z]), np.array([sb.max.X, sb.max.Y, sb.max.Z]))
            for c in design.components:
                if c.name in own or c.name in skip or c.body in moving_with:
                    continue
                if not _boxes_near(sbb, wbb[c.name], run_lim):
                    continue
                try:
                    dist = float(seg.distance_to(c.shape.moved(location_from_matrix(T[c.body]))))
                except Exception:
                    continue
                if dist < run_lim and dist < runs_close.get(c.name, {}).get("distance_mm", 1e9):
                    runs_close[c.name] = {"distance_mm": round(dist, 2), "pose": {kk: round(v, 1) for kk, v in q.items()} or "home",
                                          "run": k}
        for pn in own:
            pc = comps[pn]
            pshape = None
            for c in design.components:
                if c.cots or c.name in own or c.name in skip or c.name in joined.get(pn, ()):
                    continue
                if (pn, c.name) in pul_close and c.body == pc.body:
                    continue
                if not _boxes_near(wbb[pn], wbb[c.name], pul_lim):
                    continue
                if pshape is None:
                    pshape = pc.shape.moved(location_from_matrix(T[pc.body]))
                try:
                    dist = float(pshape.distance_to(c.shape.moved(location_from_matrix(T[c.body]))))
                except Exception:
                    continue
                key = (pn, c.name)
                if dist < pul_lim and dist < pul_close.get(key, {}).get("distance_mm", 1e9):
                    pul_close[key] = {"distance_mm": round(dist, 2), "pose": {kk: round(v, 1) for kk, v in q.items()} or "home"}
    if r is not None:
        for name, h in sorted(runs_close.items()):
            r.add("warning", "belt_run_near_part",
                  f"Belt {belt.name}: a straight run passes {h['distance_mm']:.2f} mm from {name} (pose {h['pose']}), which it slides "
                  f"past; under {run_lim:g} mm it rubs when the belt flutters or slackens (BLT-060).",
                  belt=belt.name, part=name, rule="BLT-060", value=h["distance_mm"], limit=run_lim, pose=h["pose"],
                  hint="Move the part or the pulleys/anchors so the run keeps the clearance, or open the slot the belt passes through. "
                       "Limit: design.practice['limits']['BLT-060.run_clearance_mm'].")
        for (pn, name), h in sorted(pul_close.items()):
            r.add("warning", "pulley_near_plate",
                  f"Belt {belt.name}: pulley {pn} is {h['distance_mm']:.2f} mm from {name} (pose {h['pose']}); under {pul_lim:g} mm a "
                  f"flange rubs the plate with the bearing's axial play or the hub's run-out (BLT-061).",
                  belt=belt.name, part=name, pulley=pn, rule="BLT-061", value=h["distance_mm"], limit=pul_lim, pose=h["pose"],
                  hint="Space the pulley off the plate (a thicker spacer or a second washer, moving the belt plane with it), or relieve "
                       "the plate. Limit: design.practice['limits']['BLT-061.pulley_plate_clearance_mm'].")
    return {"run_clearance_limit_mm": run_lim, "pulley_plate_clearance_limit_mm": pul_lim,
            "runs_near": runs_close, "pulleys_near": {f"{p} / {c}": v for (p, c), v in pul_close.items()}}
