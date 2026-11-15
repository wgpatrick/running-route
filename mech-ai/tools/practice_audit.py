"""Read-only "practical engineering" audit of a mechloop design (first use: designs/printer_v8.py).

    .venv/bin/python tools/practice_audit.py designs/printer_v8.py [--out research_notes/practice/v8_audit.json]

It loads the design through mechloop's public API (mechloop.runner.load_design), changes nothing, and measures what
the rules in docs/PRACTICE_RULES.md / research_notes/practice/rules.yaml need:

  fastener schedule  every screw: size, length, what it passes through (part, material, thickness, measured hole,
                     slot or round), what it threads into and how many diameters, whether nuts sit on the threaded
                     part of a partially threaded screw, thread past the nut, head bearing area / pressure estimate,
                     edge distance, fasteners per joint, locking provision, standard length
  standardisation    distinct fastener SKUs, drive sizes, spanners
  belts              teeth in mesh and wrap on every pulley and idler, back-side idlers against Gates' table 9
  bearings           what stands above / below each ring of every ball bearing (axial retention)
  set screws         every declared set_screw join
  edges              per custom metal part: length of sharp (unbroken) convex edges, sharp profile corners
  T-nuts, adjustments

Every geometric figure is measured by point-in-solid probing of the B-rep at the home pose; resolution is stated in
`method`. Thresholds marked "recalled" in rules.yaml are flagged as such in the output; nothing here is a verifier.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.gp import gp_Pnt  # noqa: E402
from OCP.TopAbs import TopAbs_IN  # noqa: E402

from mechloop.geom import forward_kinematics  # noqa: E402
from mechloop.runner import load_design  # noqa: E402
from mechloop.verifiers.belts import route  # noqa: E402

PLASTICS = {"pla", "petg", "abs", "nylon_pa12"}
# ---- rule data (ids refer to research_notes/practice/rules.yaml) -------------------------------------------------
ISO273 = {"M2.5": (2.7, 2.9, 3.1), "M3": (3.2, 3.4, 3.6), "M4": (4.3, 4.5, 4.8), "M5": (5.3, 5.5, 5.8),
          "M6": (6.4, 6.6, 7.0), "M8": (8.4, 9.0, 10.0)}                    # fine, medium, coarse (FST-020, recalled)
ISO4762_B = {"M2.5": 17.0, "M3": 18.0, "M4": 20.0, "M5": 22.0, "M6": 24.0, "M8": 28.0}   # thread length b (FreeCAD FastenersWB iso4762def.csv, in vendor_docs)
ISO4762_FULL = {"M2.5": 20.0, "M3": 20.0, "M4": 25.0, "M5": 25.0, "M6": 30.0, "M8": 35.0}  # threaded to the head up to this length (recalled)
ISO4762_RANGE = {"M3": (5, 30), "M5": (8, 50)}                               # length range rows of the same CSV
PITCH = {"M2.5": 0.45, "M3": 0.5, "M4": 0.7, "M5": 0.8, "M6": 1.0, "M8": 1.25}
STD_LENGTHS = (4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 80, 90, 100)
ISO7089 = {"M2.5": (2.7, 6.0, 0.5), "M3": (3.2, 7.0, 0.5), "M4": (4.3, 9.0, 0.8), "M5": (5.3, 10.0, 1.0),
           "M6": (6.4, 12.0, 1.6), "M8": (8.4, 16.0, 1.6)}                   # d1, d2, h (FastenersWB iso7089def.csv, fetched)
TORQUE_88 = {"M2.5": 0.7, "M3": 1.3, "M4": 2.9, "M5": 5.7, "M6": 9.9, "M8": 24.0}   # N.m, class 8.8, mu about 0.14 (recalled, FST-040)
ENGAGE = {"steel": 1.0, "stainless304": 1.0, "brass": 1.5, "al6061": 1.5, "al5052": 1.5, "al_mic6": 2.0, "al_atp5": 2.0}  # x d; plastics 2.0
YIELD_FALLBACK = 100.0
PLASTIC_SUSTAINED = 0.3      # share of yield a plastic carries under a screw head for years (recalled rule of thumb, PRT-030)
GATES_2MGT = {"teeth_full_rating": 6, "min_wrap_deg": 60.0, "backside_idler_od_mm": 12.7, "inside_idler_grooves": 12,
              "inside_flat_idler_od_mm": 25.4}                               # Gates LP&P manual, "V. Idler Usage", table 9


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
            self.cls[name] = [BRepClass3d_SolidClassifier(s.wrapped) for s in self.comps[name].shape.solids()]
        return self.cls[name]

    def inside(self, name, p) -> bool:
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


def _frame(axis):
    a = np.array(axis, float)
    a /= np.linalg.norm(a)
    h = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, h)
    u /= np.linalg.norm(u)
    return a, u, np.cross(a, u)


def _ring(c, u, v, r, n):
    return [c + r * (math.cos(t) * u + math.sin(t) * v) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


def _size(sku):
    m = re.match(r"(?:SHCS|NUT)-(M[\d.]+)(?:x([\d.]+))?", sku or "")
    return (m.group(1), float(m.group(2)) if m.group(2) else None) if m else (None, None)


def _mat(c):
    return c.material


def _yield(design, c):
    from mechloop.model import MATERIALS
    return MATERIALS[c.material].yield_mpa if c.material in MATERIALS else YIELD_FALLBACK


def fastener_schedule(design, pr: Probe):
    comps = pr.comps
    screws = {f.name: f for f in design.fasteners}
    is_fast = lambda n: (comps[n].sku or "").startswith(("SHCS-",))
    rows = []
    STEP = 0.25
    for name, f in screws.items():
        c = comps[name]
        size, L = _size(c.sku)
        if size is None:
            continue
        itf = c.meta.get("interfaces", {})
        d, hd, hh = itf.get("thread_d", float(size[1:])), itf.get("head_d"), itf.get("head_h")
        a, u, v = _frame(f.axis)                       # a points from the thread towards the head
        under = np.array(f.head_center, float) - a * hh
        tdir = -a
        lo = np.minimum(under, under + tdir * (L + 1)) - hd
        hi = np.maximum(under, under + tdir * (L + 1)) + hd
        cand = [n for n in pr.near(lo, hi, exclude=(name,)) if not is_fast(n)]
        r_ring = 0.5 * hd - 0.3                        # just inside the head's rim: sees what the head and shank pass
        r_core = 0.5 * d - 0.08                        # just inside the major diameter: a tapped part (solid, or drawn with its
                                                       # tap-drill hole) has material there, a clearance hole has none
        stations = np.arange(STEP / 2, L + 1.0, STEP)
        seen_ring, seen_core = collections.defaultdict(list), collections.defaultdict(list)
        for s in stations:
            cen = under + tdir * s
            for n in cand:
                if sum(pr.inside(n, p) for p in _ring(cen, u, v, r_ring, 6)) >= 3:
                    seen_ring[n].append(s)
                if s <= L and sum(pr.inside(n, p) for p in _ring(cen, u, v, r_core, 4)) >= 3:
                    seen_core[n].append(s)
        threads_into = list(c.meta.get("threads_into", []))
        stack = []
        for n, ss in sorted(seen_ring.items(), key=lambda kv: kv[1][0]):
            z0, z1 = ss[0] - STEP / 2, ss[-1] + STEP / 2
            cc = comps[n]
            e = {"part": n, "material": _mat(cc), "sku": cc.sku, "from_mm": round(z0, 2), "to_mm": round(min(z1, L + 1), 2),
                 "thickness_mm": round(len(ss) * STEP, 2),
                 "role": "nut" if (cc.sku or "").startswith("NUT-") else ("threaded" if n in threads_into else "clamped")}
            if e["role"] == "clamped" and z0 < L:      # measure the hole and the edge distance at mid thickness
                e.update(_hole(pr, n, under + tdir * (0.5 * (z0 + min(z1, L))), u, v, d))
            stack.append(e)
        row = {"screw": name, "sku": c.sku, "size": size, "length_mm": L, "body": c.body, "property_class": None,
               "axis_towards_head": [round(float(x), 3) for x in a], "tnut": bool(c.meta.get("tnut")),
               "threads_into": threads_into, "stack": stack, "flags": []}
        # ---- standard length, partial thread --------------------------------------------------------------------
        if L not in STD_LENGTHS:
            row["flags"].append(f"length {L:g} mm is not a preferred length")
        rng = ISO4762_RANGE.get(size)
        if rng and not rng[0] <= L <= rng[1]:
            row["flags"].append(f"FST-061: {size} x {L:g} is outside ISO 4762's length range for {size} ({rng[0]} to {rng[1]} mm): "
                                "a commercial DIN 912 size at best, check stock")
        b = ISO4762_B.get(size)
        thr0 = 0.0 if L <= ISO4762_FULL.get(size, 0) else L - b      # thread starts this far under the head
        row["thread_starts_mm_under_head"] = round(thr0, 1)
        # ---- engagement --------------------------------------------------------------------------------------------
        eng = []
        for n in threads_into:
            cc = comps.get(n)
            if cc is None:
                continue
            ss = seen_core.get(n, [])
            nut = (cc.sku or "").startswith("NUT-")
            length = len([s for s in ss if s <= L]) * STEP
            need = (cc.meta.get("interfaces", {}).get("height", 0.8 * d) / d) if nut else (
                2.0 if cc.material in PLASTICS else ENGAGE.get(cc.material, 1.5))
            depth = cc.meta.get("interfaces", {}).get("thread_depth")
            if depth and not nut:                      # a catalogue part's own tapped hole: its maker's depth is the most there is
                need = min(need, (depth - 0.3) / d)
            e = {"into": n, "material": cc.material, "nut": nut, "engaged_mm": round(length, 2), "engaged_d": round(length / d, 2),
                 "rule_d": round(need, 2), "ok": bool(c.meta.get("tnut")) or length / d >= need - 0.08}
            if c.meta.get("tnut"):
                e["note"] = "T-nut in the slot (not drawn): engagement is the T-nut's thickness, not measured"
            if ss:
                e["from_mm"], e["to_mm"] = round(ss[0] - STEP / 2, 2), round(ss[-1] + STEP / 2, 2)
                if e["from_mm"] < thr0 - 0.3:
                    e["on_unthreaded_shank_mm"] = round(min(thr0, e["to_mm"]) - e["from_mm"], 2)
                    row["flags"].append(f"FST-060: {n} sits {e['from_mm']:.1f} to {e['to_mm']:.1f} mm under the head, but an ISO 4762 "
                                        f"{size} x {L:g} is threaded only over its last {b:g} mm (from {thr0:.0f} mm)")
                if nut:
                    e["thread_past_nut_mm"] = round(L - e["to_mm"], 2)
                    if L - e["to_mm"] < PITCH[size] - 0.15:
                        row["flags"].append(f"FST-062: thread ends {L - e['to_mm']:+.1f} mm past {n} (want at least one pitch, {PITCH[size]} mm)")
                    if L - e["to_mm"] > 3 * d and not any("FST-060" in x for x in row["flags"]):
                        row["flags"].append(f"FST-062: {L - e['to_mm']:.0f} mm of thread stands past {n} (snag / reach hazard, more than 3 d)")
            if not e["ok"]:
                row["flags"].append(f"FST-010: {e['engaged_d']:.2f} d of thread in {n} ({cc.material}), rule {need:g} d")
            eng.append(e)
        row["engagement"] = eng
        # ---- what the head bears on ----------------------------------------------------------------------------
        first = next((e for e in stack if e["from_mm"] < 0.5), None)
        if first:
            cc = comps[first["part"]]
            dh = first.get("hole_mm") or (d + 0.4)
            dw = 0.92 * hd                                             # washer-face diameter of an ISO 4762 head, about
            pts = [p for r in np.linspace(dh / 2 + 0.05, dw / 2, 4) for p in _ring(under + tdir * 0.1, u, v, r, 16)]
            frac = sum(pr.inside(first["part"], p) for p in pts) / len(pts)
            area = math.pi / 4 * (dw ** 2 - dh ** 2) * frac
            preload = TORQUE_88[size] / (0.2 * d) * 1000.0             # N, at the usual class 8.8 torque (recalled)
            plastic = cc.material in PLASTICS
            limit = _yield(design, cc) * (PLASTIC_SUSTAINED if plastic else 1.0)
            w = ISO7089[size]
            area_w = math.pi / 4 * (w[1] ** 2 - max(dh, w[0]) ** 2)
            head = {"on": first["part"], "material": cc.material, "plastic": plastic, "slot": first.get("slot", False),
                    "hole_mm": first.get("hole_mm"), "supported_fraction": round(frac, 2), "bearing_area_mm2": round(area, 1),
                    "preload_at_8.8_torque_n": round(preload), "pressure_mpa": round(preload / max(area, 0.1)),
                    "limit_mpa": round(limit), "limit_basis": "0.3 x yield, sustained (recalled)" if plastic else "yield of the clamped part",
                    "pressure_with_iso7089_washer_mpa": round(preload / area_w),
                    "max_torque_bare_head_nm": round(limit * area * 0.2 * d / 1000.0, 2),
                    "max_torque_with_washer_nm": round(limit * area_w * 0.2 * d / 1000.0, 2)}
            thin = (not plastic) and cc.material.startswith("al") and first["thickness_mm"] < 3.1
            head["thin_aluminium"] = thin
            if cc.sku and (cc.sku.startswith("SPACER") or "WASHER" in cc.sku):
                head["note"] = "bears on a bought spacer / washer"
            elif cc.cots:
                head["note"] = "bears on a catalogue part (its maker's seat)"
            else:
                if plastic:
                    row["flags"].append(f"PRT-030: head bears directly on printed {cc.material} ({first['part']}): {head['pressure_mpa']} MPa "
                                        f"at the usual torque against about {head['limit_mpa']} MPa sustained; no washer")
                if first.get("slot"):
                    row["flags"].append(f"FST-031: head bears on a slot in {first['part']} with no washer (supported {frac:.0%} of the head face)")
                elif head["pressure_mpa"] > head["limit_mpa"] and not plastic:
                    row["flags"].append(f"FST-030: head pressure {head['pressure_mpa']} MPa on {first['part']} ({cc.material}, limit {head['limit_mpa']})")
            row["head"] = head
        # ---- what the nut bears on -------------------------------------------------------------------------------
        for i, e in enumerate(stack):
            if e["role"] == "nut" and i > 0:
                prev = comps[stack[i - 1]["part"]]
                e["bears_on"] = {"part": prev.name, "material": prev.material}
                if prev.material in PLASTICS and not prev.cots:
                    row["flags"].append(f"PRT-030: nut {e['part']} bears directly on printed {prev.material} ({prev.name}); no washer")
        # ---- edge distance (NASA RP-1228: nominal 2 d, minimum 1.5 d from the hole centre) -------------------------
        for e in stack:
            if e["role"] == "clamped" and e.get("edge_mm") is not None and not comps[e["part"]].cots:
                if e["edge_mm"] < 1.5 * d - 0.26:
                    row["flags"].append(f"FST-050: {e['part']}: {e['edge_mm']:.1f} mm from the hole centre to the nearest edge or cut-out "
                                        f"({e['edge_mm'] / d:.2f} d; minimum 1.5 d, nominal 2 d)")
                cls = e.get("iso273")
                if cls == "tighter than fine" and comps[e["part"]].material not in PLASTICS:
                    row["flags"].append(f"FST-020: {e['part']}: hole {e['hole_mm']} mm is under ISO 273 fine for {size}")
        row["joint"] = sorted({e["part"] for e in stack if e["role"] != "nut" and not (comps[e["part"]].sku or "").startswith("SPACER")}
                              | {n for n in threads_into if not (comps[n].sku or "").startswith("NUT-")})
        row["moving"] = c.body != "world"
        rows.append(row)
    return rows


def _hole(pr: Probe, part, cen, u, v, d):
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
    dia = [(r_in[i] + r_in[i + n_ang // 2]) if r_in[i] is not None and r_in[i + n_ang // 2] is not None else None for i in range(n_ang // 2)]
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


def standardisation(design, rows):
    comps = design.components
    skus = collections.Counter(c.sku for c in comps if (c.sku or "").startswith(("SHCS-", "NUT-")))
    for k, v in design.bom_extras.items():
        if k.startswith(("SHCS-", "NUT", "TNUT", "NYLOC", "WASHER")):
            skus[k] += v["qty"]
    keys = sorted({c.meta.get("interfaces", {}).get("hex_key") for c in comps if (c.sku or "").startswith("SHCS-")} - {None})
    spanners = sorted({c.meta.get("interfaces", {}).get("across_flats") for c in comps if (c.sku or "").startswith("NUT-")} - {None})
    sizes = collections.Counter()
    for k, v in skus.items():
        m = re.search(r"M[\d.]+", k)
        sizes[m.group(0) if m else k] += v
    return {"fastener_skus": dict(sorted(skus.items())), "distinct_skus": len(skus), "distinct_screw_skus": len([k for k in skus if k.startswith("SHCS-")]),
            "thread_sizes": dict(sizes), "hex_keys_mm": keys, "spanners_mm": spanners,
            "washers_in_bom": {k: v["qty"] for k, v in design.bom_extras.items() if "WASHER" in k},
            "locking_in_bom": {k: v["qty"] for k, v in design.bom_extras.items() if re.search("NYLOC|LOCTITE|THREADLOCK|SERRAT", k)}}


def belts(design):
    comps = {c.name: c for c in design.components}
    T = forward_kinematics(design, {j.name: 0.0 for j in design.joints})
    drive = {j.drive.get("pulley") for j in design.joints if j.drive and j.drive.get("pulley")}
    out = []
    for b in design.belts:
        r = route(design, b, T)
        senses = [n[2] for n in b.path if n[0] == "pulley"]
        major = collections.Counter(senses).most_common(1)[0][0]
        item = {"belt": b.name, "width_mm": b.width, "length_mm": round(r["length"], 1), "stock_length_mm": b.stock_length,
                "closed": r["closed"], "tension_n_declared": b.tension, "pulleys": []}
        for node in b.path:
            if node[0] != "pulley":
                continue
            c = comps[node[1]]
            teeth, wrap = c.ratings.get("teeth"), r["wraps_deg"].get(node[1])
            idler = "IDLER" in (c.sku or "")
            backside = r["closed"] and node[2] != major
            mesh = wrap * teeth / 360.0 if (wrap is not None and teeth) else None
            od = c.ratings.get("pitch_diameter_mm", 0) - 0.76
            p = {"part": node[1], "sku": c.sku, "teeth": teeth, "wrap_deg": None if wrap is None else round(wrap, 1),
                 "teeth_in_mesh": None if mesh is None else round(mesh, 1), "idler": idler, "backside": backside,
                 "is_joint_drive_pulley": node[1] in drive, "od_mm": round(od, 2), "flags": []}
            loaded = not idler
            if backside:
                p["flags"].append("BLT-030: a TOOTHED idler runs on the belt's smooth back; Gates: back-side idlers should be flat and uncrowned")
                if od < GATES_2MGT["backside_idler_od_mm"]:
                    p["flags"].append(f"BLT-031: back-side idler OD {od:.1f} mm is under Gates' minimum for 2MGT, 12.7 mm (0.50 in)")
            elif idler and teeth and teeth < GATES_2MGT["inside_idler_grooves"]:
                p["flags"].append("BLT-031: inside idler under 12 grooves")
            if loaded and mesh is not None:
                if mesh < GATES_2MGT["teeth_full_rating"]:
                    derate = max(0.0, 1 - 0.2 * (6 - math.floor(mesh + 1e-9)))
                    p["torque_rating_factor"] = round(derate, 2)
                    p["flags"].append(f"BLT-010: {mesh:.1f} teeth in mesh on a load-carrying pulley (Gates: at least 6; rating x {derate:.1f})")
                if wrap < GATES_2MGT["min_wrap_deg"] + 0.5:
                    p["flags"].append(f"BLT-011: wrap {wrap:.0f} deg; Gates asks at least 60 deg on a loaded sprocket: no margin" if wrap >= 60
                                      else f"BLT-011: wrap {wrap:.0f} deg is under Gates' 60 deg minimum")
            item["pulleys"].append(p)
        out.append(item)
    return out


def bearings(design, pr: Probe):
    out = []
    for c in design.components:
        if not (c.sku or "").startswith("BRG-"):
            continue
        itf = c.meta["interfaces"]
        lo, hi = pr.bb[c.name]
        size = hi - lo
        ax = int(np.argmin(np.abs(size - itf["width"])))
        a = np.eye(3)[ax]
        _, u, v = _frame(a)
        cen = (lo + hi) / 2
        cand = pr.near(lo - 3, hi + 3, exclude=(c.name,))
        r_outer, r_inner = (itf["od"] / 2 - 1.2), (itf["bore"] / 2 + 1.0)

        def who(r, off):
            hit = collections.Counter()
            for p in _ring(cen + a * off, u, v, r, 12):
                for n in cand:
                    if pr.inside(n, p):
                        hit[n] += 1
            return [n for n, k in hit.items() if k >= 6]
        half = itf["width"] / 2
        e = {"bearing": c.name, "sku": c.sku, "axis": "xyz"[ax], "centre": [round(float(x), 2) for x in cen],
             "outer_ring": {"above": who(r_outer, half + 0.4), "below": who(r_outer, -half - 0.4), "seat": who(itf["od"] / 2 + 0.6, 0.0)},
             "inner_ring": {"above": who(r_inner, half + 0.4), "below": who(r_inner, -half - 0.4), "shaft": who(itf["bore"] / 2 - 0.5, 0.0)},
             "joins": sorted({k if isinstance(k, str) else str(k) for pair, k in design.joins.items() if c.name in pair}),
             "flags": []}
        for ring in ("outer_ring", "inner_ring"):
            for side in ("above", "below"):
                if not e[ring][side]:
                    e["flags"].append(f"BRG-020: {ring.replace('_', ' ')} has nothing {side} it (no shoulder, circlip or cover)")
        out.append(e)
    return out


def set_screws(design):
    comps = {c.name: c for c in design.components}
    out = []
    for pair, kind in design.joins.items():
        if (kind if isinstance(kind, str) else str(kind)) == "set_screw":
            a, b = sorted(pair)
            hub = a if "PULLEY" in (comps[a].sku or "") or "GT2" in (comps[a].sku or "") else b
            shaft = b if hub == a else a
            s = comps[shaft]
            out.append({"hub": hub, "hub_sku": comps[hub].sku, "shaft": shaft, "shaft_sku": s.sku,
                        "shaft_kind": "lead screw (trapezoidal thread, no flat)" if (s.sku or "").startswith("T8") else
                        "motor shaft (round in the catalogue solid; a flat is not modelled)" if (s.sku or "").startswith("NEMA") else "other",
                        "set_screw_modelled": False})
    return out


def edges(design, pr: Probe):
    out = []
    for c in design.components:
        if c.cots or c.material in PLASTICS or c.material.startswith("rubber"):
            continue
        shape = c.shape
        emap = collections.defaultdict(list)           # edge -> its faces (edges of one solid share their TShape)
        for fc in shape.faces():
            for e_ in fc.edges():
                pm = e_.position_at(0.5)
                emap[(round(pm.X, 3), round(pm.Y, 3), round(pm.Z, 3), round(e_.length, 3))].append((e_, fc))
        lo, hi = pr.bb[c.name]
        thin_axis = int(np.argmin(hi - lo)) if (c.process or c.meta.get("process")) == "sheet" else None
        sharp_len = total_len = 0.0
        n_sharp = corners = 0
        for lst in emap.values():
            try:
                if len(lst) != 2 or lst[0][0].length < 1e-6:
                    continue
                ed, faces = lst[0][0], [lst[0][1], lst[1][1]]
                p = ed.position_at(0.5)
                n1, n2 = faces[0].normal_at(p), faces[1].normal_at(p)
                total_len += ed.length
                cosang = max(-1.0, min(1.0, n1.dot(n2)))
                if math.degrees(math.acos(cosang)) < 60.0:          # tangent (fillet) or a 45 degree chamfer: broken
                    continue
                s = (n1 + n2).normalized()
                pp = np.array([p.X, p.Y, p.Z])
                sv = np.array([s.X, s.Y, s.Z])
                if pr.inside(c.name, pp - 0.05 * sv) and not pr.inside(c.name, pp + 0.05 * sv):   # convex: metal behind, air in front
                    sharp_len += ed.length
                    n_sharp += 1
                    if thin_axis is not None:
                        t = ed.tangent_at(0.5)
                        if abs([t.X, t.Y, t.Z][thin_axis]) > 0.9 and ed.geom_type.name == "LINE":
                            corners += 1
            except Exception:
                continue
        out.append({"part": c.name, "material": c.material, "process": c.process or c.meta.get("process"), "body": c.body,
                    "edge_length_mm": round(total_len), "sharp_convex_edge_mm": round(sharp_len), "sharp_convex_edges": n_sharp,
                    "sharp_profile_corners": corners if thin_axis is not None else None,
                    "share_unbroken": round(sharp_len / total_len, 2) if total_len else None,
                    "edge_note_declared": bool(c.meta.get("edge_break") or c.meta.get("deburr") or design.manufacturing.get("edge_break"))})
    return out


def tnuts(design, rows):
    per_part = collections.Counter()
    for r in rows:
        if r["tnut"]:
            for e in r["stack"]:
                if e["role"] == "clamped" and not (e["sku"] or "").startswith(("SPACER", "EXT2020")):
                    per_part[e["part"]] += 1
                    break
    brk = collections.Counter(str(k) for k in design.joins.values() if "tnut" in str(k))
    return {"bom": {k: v["qty"] for k, v in design.bom_extras.items() if k.startswith("TNUT")}, "joins_by_kind": dict(brk),
            "drawn_tnut_screws": sum(r["tnut"] for r in rows), "parts_by_tnut_screws": dict(sorted(per_part.items())),
            "held_by_one_tnut_screw": sorted(k for k, v in per_part.items() if v == 1),
            "type_declared": None, "note": "the SKU is TNUT-2020-M3 / -M5 only: drop-in (roll-in, spring) or slide-in is not said, and T-nuts are not geometry"}


def joints(rows):
    by = collections.defaultdict(list)
    for r in rows:
        if len(r["joint"]) >= 2:
            by[tuple(r["joint"])].append(r["screw"])
    single = {" + ".join(k): v[0] for k, v in by.items() if len(v) == 1}
    return {"joints": len(by), "screws_per_joint": dict(collections.Counter(len(v) for v in by.values())), "single_screw_joints": single}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("design")
    ap.add_argument("--out", default=str(ROOT / "research_notes/practice/v8_audit.json"))
    a = ap.parse_args(argv)
    t0 = time.time()
    d = load_design(a.design)
    pr = Probe(d)
    rows = fastener_schedule(d, pr)
    rep = {"design": d.name, "file": a.design, "generated": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
           "method": {"probing": "point-in-solid on the B-rep at the home pose; stack stations every 0.25 mm, hole radius in 0.05 mm steps refined by bisection, "
                                 "edge distance in 0.25 mm steps over 16 directions",
                      "preload": "class 8.8 tightening torque (recalled table) / (0.2 d); property class is not declared in the design",
                      "recalled_thresholds": ["ISO 273 classes", "ISO 4762 full-thread lengths", "class 8.8 torques", "plastic sustained bearing limit 0.3 x yield"]},
           "parts": len(d.components), "fasteners": rows, "standardisation": standardisation(d, rows), "joints": joints(rows),
           "belts": belts(d), "bearings": bearings(d, pr), "set_screws": set_screws(d), "edges": edges(d, pr), "tnuts": tnuts(d, rows),
           "adjustments": [{"name": x.name, "kind": x.kind, "range_mm": x.range_mm, "joint": x.joint, "lock_declared": None} for x in d.adjustments]}
    flags = collections.Counter()
    for r in rows:
        for f in r["flags"]:
            flags[f.split(":")[0]] += 1
    moving = [r["screw"] for r in rows if r["moving"]]
    rep["summary"] = {"screws": len(rows), "flag_counts": dict(flags), "screws_on_moving_bodies": len(moving),
                      "screws_with_declared_locking": 0,
                      "heads_on_printed_plastic": sorted({r["head"]["on"] for r in rows if r.get("head", {}).get("plastic") and "note" not in r["head"]}),
                      "heads_on_slots": sorted({r["head"]["on"] for r in rows if r.get("head", {}).get("slot") and "note" not in r["head"]}),
                      "seconds": round(time.time() - t0, 1), "point_tests": pr.calls}
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep["summary"], indent=1))
    print("written:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
