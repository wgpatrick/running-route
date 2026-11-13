"""Belt checks: the route must keep a constant length as the machine moves
(otherwise the belt goes slack or binds), must fit the belt you intend to buy,
and its straight runs must not pass through other parts."""
from __future__ import annotations

import math

import numpy as np
from build123d import Box, Plane, Pos

from ..geom import bboxes_overlap, forward_kinematics, location_from_matrix, overlap_volume
from ..model import Belt, Design
from ..report import VerifierResult

LEN_TOL = 0.3  # mm of length change over travel a tensioned belt can absorb


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
        out[belt.name] = m
    r.metrics["belts"] = out
