"""Shared measurement of what every screw passes through, and of what touches each ball bearing's faces.

Promoted from the read-only audit `tools/practice_audit.py` (docs/PRACTICE_RULES.md section 4.1), which now imports
these functions, so the audit and the `practice` verifier measure the same way. Everything is point-in-solid probing of
the B-rep at the home pose (no meshing):

  fastener_stack(design, probe)  per screw: size, length, the parts along it in order (from / to in mm under the head,
                                 role: clamped / threaded / nut), each clamped part's hole (diameter, slot, nearest edge
                                 beyond it, ISO 273 class), where the thread starts on a partly threaded ISO 4762 screw,
                                 where each threaded part sits on it, what the head bears on, the parts the screw joins
  bearing_contacts(design, probe)  per catalogue ball bearing: the parts above and below each ring face (0.4 mm off it),
                                 in the bore, round the outside

Resolution: stations every 0.25 mm along the screw; hole radius in 0.05 mm steps refined by bisection; edge distance in
0.25 mm steps over 16 directions.
"""
from __future__ import annotations

import collections
import math
import re

import numpy as np

# ISO 273 clearance holes fine / medium / coarse (FST-020: MMCC ISO 273 table, read from the scan)
ISO273 = {"M2.5": (2.7, 2.9, 3.1), "M3": (3.2, 3.4, 3.6), "M4": (4.3, 4.5, 4.8), "M5": (5.3, 5.5, 5.8),
          "M6": (6.4, 6.6, 7.0), "M8": (8.4, 9.0, 10.0)}
# ISO 4762 thread length b (Westfield table; FastenersWB CSV agrees) and the longest fully threaded length (Aramfix DIN 912)
ISO4762_B = {"M2.5": 17.0, "M3": 18.0, "M4": 20.0, "M5": 22.0, "M6": 24.0, "M8": 28.0}
ISO4762_FULL = {"M2.5": 20.0, "M3": 20.0, "M4": 25.0, "M5": 25.0, "M6": 30.0, "M8": 35.0}
PITCH = {"M2.5": 0.45, "M3": 0.5, "M4": 0.7, "M5": 0.8, "M6": 1.0, "M8": 1.25}
STEP = 0.25


class Probe:
    """Point-in-solid tests against the design's parts, one classifier per solid, bounding boxes first."""

    def __init__(self, design):
        self.comps = {c.name: c for c in design.components}
        self.cls, self.bb = {}, {}
        for c in design.components:
            b = c.shape.bounding_box()
            self.bb[c.name] = (np.array([b.min.X, b.min.Y, b.min.Z]), np.array([b.max.X, b.max.Y, b.max.Z]))
        self.calls = 0

    def _classifiers(self, name):
        if name not in self.cls:
            from OCP.BRepClass3d import BRepClass3d_SolidClassifier

            self.cls[name] = [BRepClass3d_SolidClassifier(s.wrapped) for s in self.comps[name].shape.solids()]
        return self.cls[name]

    def inside(self, name, p) -> bool:
        from OCP.gp import gp_Pnt
        from OCP.TopAbs import TopAbs_IN

        lo, hi = self.bb[name]
        if np.any(p < lo - 1e-6) or np.any(p > hi + 1e-6):
            return False
        g = gp_Pnt(float(p[0]), float(p[1]), float(p[2]))
        for k in self._classifiers(name):
            self.calls += 1
            k.Perform(g, 1e-7)
            if k.State() == TopAbs_IN:
                return True
        return False

    def near(self, lo, hi, exclude=()):
        return [n for n, (a, b) in self.bb.items() if n not in exclude and np.all(b >= lo) and np.all(a <= hi)]


def frame(axis):
    a = np.array(axis, float)
    a /= np.linalg.norm(a)
    h = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, h)
    u /= np.linalg.norm(u)
    return a, u, np.cross(a, u)


def ring(c, u, v, r, n):
    return [c + r * (math.cos(t) * u + math.sin(t) * v) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def size_of(sku):
    """("M5", 90.0) from "SHCS-M5x90"; ("M3", None) from "NUT-M3"; (None, None) otherwise."""
    m = re.match(r"(?:SHCS|NUT)-(M[\d.]+)(?:x([\d.]+))?", sku or "")
    return (m.group(1), float(m.group(2)) if m.group(2) else None) if m else (None, None)


def is_nut(c) -> bool:
    return (c.sku or "").startswith("NUT-")


def is_washer(c) -> bool:
    return (c.sku or "").startswith("WASHER-")


def is_spacer(c) -> bool:
    return (c.sku or "").startswith("SPACER")


def thread_start_mm(size: str, length: float) -> float:
    """How far under the head the thread of an ISO 4762 screw starts (0 for a fully threaded length)."""
    if length <= ISO4762_FULL.get(size, 0.0):
        return 0.0
    return max(0.0, length - ISO4762_B.get(size, length))


def counterbored(pr: Probe, part, under, a, u, v, hd) -> bool:
    """True when the part has material beside the head (the head sits in a counterbore of that part)."""
    pts = ring(under + a * 1.0, u, v, 0.5 * hd + 0.6, 12)
    return sum(pr.inside(part, p) for p in pts) >= 9


def hole(pr: Probe, part, cen, u, v, d):
    """Hole diameter (smallest diameter over 8 directions), slot length (largest), nearest edge beyond the hole."""
    n_ang, out = 16, {}
    r_in, r_out = [], []
    for t in np.linspace(0, 2 * math.pi, n_ang, endpoint=False):
        w = math.cos(t) * u + math.sin(t) * v
        r = 0.5 * d - 0.1
        while r < 3.0 * d and not pr.inside(part, cen + r * w):
            r += 0.05
        if 0.5 * d - 0.1 < r < 3.0 * d:                  # refine the wall position by bisection (to about 0.003 mm)
            lo_r, hi_r = r - 0.05, r
            for _ in range(4):
                mid = 0.5 * (lo_r + hi_r)
                lo_r, hi_r = (lo_r, mid) if pr.inside(part, cen + mid * w) else (mid, hi_r)
            r = 0.5 * (lo_r + hi_r)
        r_in.append(r if r < 3.0 * d else None)
        if r >= 3.0 * d:
            r_out.append(None)
            continue
        r2 = r + 0.25
        while r2 < 4.0 * d + 3 and pr.inside(part, cen + r2 * w):
            r2 += 0.25
        r_out.append(r2 if r2 < 4.0 * d + 3 else None)
    dia = [(r_in[i] + r_in[i + n_ang // 2]) if r_in[i] is not None and r_in[i + n_ang // 2] is not None else None
           for i in range(n_ang // 2)]
    known = [x for x in dia if x is not None]
    if not known:
        return {"hole_mm": None, "open": True}
    out["hole_mm"] = round(min(known), 2)
    longest = None if any(x is None for x in dia) else round(max(known), 2)
    out["slot"] = longest is None or longest - min(known) > 0.3
    if out["slot"]:
        out["slot_length_mm"] = longest if longest is not None else "open"
    edges = [x for x in r_out if x is not None]
    out["edge_mm"] = round(min(edges), 2) if edges else None           # None: no edge within 4 d + 3 mm
    f, m, c = ISO273.get(f"M{d:g}", (None,) * 3)
    if f and not out["slot"]:
        h = out["hole_mm"]
        out["iso273"] = ("tighter than fine" if h < f - 0.08 else "fine" if h < (f + m) / 2 else "medium" if h < (m + c) / 2
                         else "coarse" if h <= c + 0.08 else "larger than coarse")
    return out


def fastener_stack(design, pr: Probe) -> list[dict]:
    """One row per cap screw (SKU SHCS-...): what it passes through, in order, and what that means for its thread and
    head. Measured, not read from declarations, except `threads_into` (which parts the screw is meant to thread into)."""
    comps = pr.comps
    rows = []
    for f in design.fasteners:
        c = comps.get(f.name)
        if c is None:
            continue
        size, L = size_of(c.sku)
        if size is None or L is None:
            continue
        itf = c.meta.get("interfaces", {})
        d, hd, hh = itf.get("thread_d", float(size[1:])), itf.get("head_d"), itf.get("head_h")
        if not hd or not hh:
            continue
        a, u, v = frame(f.axis)                        # a points from the thread towards the head
        under = np.array(f.head_center, float) - a * hh
        tdir = -a
        lo = np.minimum(under, under + tdir * (L + 1)) - hd
        hi = np.maximum(under, under + tdir * (L + 1)) + hd
        # a drawn T-nut (meta["tnut_of"]) is the nut of its own screw, in the slot: not a part of the stack or of the joint
        # (interference.tslot_screws judges it); the row names it under "tnut_part"
        cand = [n for n in pr.near(lo, hi, exclude=(f.name,)) if not (comps[n].sku or "").startswith("SHCS-")
                and not comps[n].meta.get("tnut_of")]
        r_ring = 0.5 * hd - 0.3                        # just inside the head's rim: sees what the head and shank pass
        r_core = 0.5 * d - 0.08                        # just inside the major diameter: a tapped part has material there
        stations = np.arange(STEP / 2, L + 1.0, STEP)
        seen_ring, seen_core = collections.defaultdict(list), collections.defaultdict(list)
        for s in stations:
            cen = under + tdir * s
            for n in cand:
                if sum(pr.inside(n, p) for p in ring(cen, u, v, r_ring, 6)) >= 3:
                    seen_ring[n].append(s)
                if s <= L and sum(pr.inside(n, p) for p in ring(cen, u, v, r_core, 4)) >= 3:
                    seen_core[n].append(s)
        threads_into = [t for t in c.meta.get("threads_into", []) if t in comps]
        stack = []
        for n, ss in sorted(seen_ring.items(), key=lambda kv: kv[1][0]):
            z0, z1 = ss[0] - STEP / 2, ss[-1] + STEP / 2
            cc = comps[n]
            e = {"part": n, "material": cc.material, "sku": cc.sku, "from_mm": round(z0, 2), "to_mm": round(min(z1, L + 1), 2),
                 "thickness_mm": round(len(ss) * STEP, 2),
                 "role": "nut" if is_nut(cc) else ("threaded" if n in threads_into else "clamped")}
            if e["role"] == "clamped" and z0 < L:      # measure the hole and the edge distance at mid thickness
                e.update(hole(pr, n, under + tdir * (0.5 * (z0 + min(z1, L))), u, v, d))
            stack.append(e)
        thr0 = thread_start_mm(size, L)
        if itf.get("thread_length") is not None:       # the bought screw's own thread length (supplier data), not ISO's b
            thr0 = max(0.0, L - float(itf["thread_length"]))
        threaded = []
        for n in threads_into:
            ss = seen_core.get(n, [])
            e = {"into": n, "nut": is_nut(comps[n]), "engaged_mm": round(len([s for s in ss if s <= L]) * STEP, 2)}
            if ss:
                e["from_mm"], e["to_mm"] = round(ss[0] - STEP / 2, 2), round(ss[-1] + STEP / 2, 2)
            threaded.append(e)
        # what the screw's tip bears on (a jack screw pushing a plate): material on the axis just past the tip, in a part
        # the screw is not threaded into
        tip = under + tdir * (L + 0.3)
        tip_on = sorted(n for n in cand if n not in threads_into and not is_nut(comps[n]) and pr.inside(n, tip))
        head = None
        first = next((e for e in stack if e["from_mm"] < 0.5), None)
        if first:
            head = {"on": first["part"], "material": first["material"], "thickness_mm": first["thickness_mm"],
                    "hole_mm": first.get("hole_mm"), "slot": first.get("slot", False),
                    "counterbored": bool(first["from_mm"] < 0.1 and counterbored(pr, first["part"], under, a, u, v, hd))}
        # the parts the screw holds: declared clamps, what it threads into, and parts its shank passes through a hole in
        # (a part merely beside the shank, inside the head's radius, is in the stack but not held)
        declared = [n for n in f.clamps if n in comps]
        held = sorted({e["part"] for e in stack if e["role"] == "clamped" and e.get("hole_mm") is not None}
                      | set(declared) | set(threads_into))
        joint = sorted(n for n in held if not is_nut(comps[n]) and not is_spacer(comps[n]) and not is_washer(comps[n]))
        rows.append({"screw": f.name, "sku": c.sku, "size": size, "d": float(d), "length_mm": float(L), "body": c.body,
                     "axis_towards_head": [round(float(x), 3) for x in a], "under_head": [round(float(x), 3) for x in under],
                     "tnut": bool(c.meta.get("tnut")), "tnut_part": c.meta.get("tnut_part"), "threads_into": threads_into, "stack": stack, "threaded": threaded,
                     "thread_starts_mm_under_head": round(thr0, 2), "head": head, "joint": joint, "held": held,
                     "declared_clamps": declared, "tip_on": tip_on,
                     "locking": c.meta.get("locking"), "torque_nm": c.meta.get("torque_nm"),
                     "thread_insert": c.meta.get("thread_insert"), "heatset_insert": bool(c.meta.get("insert")),
                     "fully_threaded": bool(c.meta.get("fully_threaded"))})
    return rows


def bearing_contacts(design, pr: Probe) -> list[dict]:
    """Every catalogue ball bearing (SKU BRG-...): which parts stand against each ring face (probed 0.4 mm off the face
    on a circle inside the ring), which parts are in its bore and round its outside, and how far out each part on the
    inner ring's faces reaches (for the abutment rule)."""
    out = []
    for c in design.components:
        if not (c.sku or "").startswith("BRG-"):
            continue
        itf = c.meta.get("interfaces") or {}
        if not all(k in itf for k in ("width", "od", "bore")):
            continue
        lo, hi = pr.bb[c.name]
        size = hi - lo
        ax = int(np.argmin(np.abs(size - itf["width"])))
        a = np.eye(3)[ax]
        _, u, v = frame(a)
        cen = (lo + hi) / 2
        cand = pr.near(lo - 3, hi + 3, exclude=(c.name,))
        r_outer, r_inner = (itf["od"] / 2 - 1.2), (itf["bore"] / 2 + 1.0)

        def who(r, off):
            hit = collections.Counter()
            for p in ring(cen + a * off, u, v, r, 12):
                for n in cand:
                    if pr.inside(n, p):
                        hit[n] += 1
            return sorted(n for n, k in hit.items() if k >= 6)
        half = itf["width"] / 2
        out.append({"bearing": c.name, "sku": c.sku, "axis": "xyz"[ax], "centre": [round(float(x), 2) for x in cen],
                    "outer_ring": {"above": who(r_outer, half + 0.4), "below": who(r_outer, -half - 0.4),
                                   "seat": who(itf["od"] / 2 + 0.6, 0.0)},
                    "inner_ring": {"above": who(r_inner, half + 0.4), "below": who(r_inner, -half - 0.4),
                                   "shaft": who(itf["bore"] / 2 - 0.5, 0.0)}})
    return out
