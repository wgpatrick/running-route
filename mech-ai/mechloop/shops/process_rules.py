"""Suppliers' published CNC-milling and 3D-printing rules, as data, and their evaluation against a part's features.

The rules live in mechloop/data/supplier_rules_cnc_3dp/<supplier>.json, in the same schema as the sheet-metal rules
("mechloop.supplier_rules/1", see shops/supplier_rules.py): supplier, process ("cnc_milling", "fdm", "sls", "mjf",
"sla"), material ("*", a material key, "al*", "metal", "plastic", or several joined by "|"), rule kind, value_mm /
value / formula, comparison, severity (requirement = error, recommendation = warning, statement = info), source_url,
a quote and the retrieval date. The "own_printer" rule set is the owner's printer (PLA/PETG, 0.4 mm nozzle), sourced
from repository files (docs/DESIGN_GUIDELINES.md, mechloop/printsettings.py, verifiers/dfm_rules.py, dfm_print.py).
tools/build_process_rules.py builds the files and checks every quote against the saved page. docs/SUPPLIER_RULES.md
(section "CNC milling and 3D printing") is the readable form.

Nothing is interpolated: a rule applies only where its own `applies` conditions hold (thread size, hole or pin
diameter band, part size band); otherwise the part gets no result for it.

This module is geometry-free: `evaluate(features, supplier)` takes the dict built by verifiers/dfm_features.py and
returns one result per applicable rule, like shops/supplier_rules.evaluate.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

from . import supplier_rules as SR

DATA = Path(__file__).resolve().parent.parent / "data" / "supplier_rules_cnc_3dp"
SCHEMA = "mechloop.supplier_rules/1"
PRINT_PROCESSES = ("fdm", "sls", "mjf", "sla")
DEFAULT = {"cnc_milling": "xometry", "fdm": "own_printer", "sls": "xometry", "mjf": "xometry", "sla": "xometry"}
AREA_TOL_MM2 = 5.0          # overhang area under this (beyond the rule's angle) is a sliver, not an overhang
CANTILEVER_TOL_MM = 0.5     # a flat lip shorter than about one extrusion line is not a cantilever
PLASTICS = {"pla", "petg", "abs", "asa", "nylon_pa12", "tpu", "pc", "delrin", "pom", "hdpe", "acetal", "nylon", "peek"}

MEASURED = {
    "cnc_corner_sharp", "cnc_corner_radius_min", "cnc_corner_radius_depth", "cnc_corner_ld_ratio", "cnc_pocket_depth_width",
    "cnc_pocket_depth_tool", "cnc_pocket_depth_xy", "cnc_mill_depth_max", "cnc_slot_min", "cnc_wall_min", "cnc_wall_height_ratio",
    "cnc_hole_min", "cnc_hole_depth_ratio", "cnc_hole_standard_drill", "cnc_thread_min", "cnc_thread_range", "cnc_thread_depth_ratio_max",
    "cnc_thread_depth_ratio_min", "cnc_thread_depth_max", "cnc_thread_modeled_d", "cnc_blind_tap_runout", "cnc_part_max_size",
    "cnc_part_min_size", "cnc_part_min_volume", "cnc_undercut", "cnc_off_axis_features", "cnc_setups_max",
    "p3d_wall_min", "p3d_wall_min_unsupported", "p3d_wall_min_size_band", "p3d_feature_min", "p3d_pin_min", "p3d_pin_height_max",
    "p3d_hole_min", "p3d_hole_depth_max", "p3d_hole_depth_ratio", "p3d_overhang_max_deg", "p3d_overhang_length_max", "p3d_bridge_max",
    "p3d_horizontal_hole_max", "p3d_part_max_size", "p3d_part_min_size", "p3d_part_min_sum", "p3d_thread_in_print", "p3d_thread_min",
    "p3d_enclosed_void", "p3d_warp_size", "p3d_warp_thickness",
}
EXPECTED = {
    "cnc_milling": ("cnc_corner_radius_depth", "cnc_pocket_depth_width", "cnc_wall_min", "cnc_hole_depth_ratio", "cnc_part_max_size", "cnc_setups_max"),
    "fdm": ("p3d_wall_min", "p3d_feature_min", "p3d_hole_min", "p3d_overhang_max_deg", "p3d_part_max_size"),
}
KIND_TEXT = {
    "cnc_corner_sharp": "sharp vertical inside corners", "cnc_corner_radius_min": "vertical inside corner radius",
    "cnc_corner_radius_depth": "inside corner radius against its depth", "cnc_corner_ld_ratio": "corner depth over cutter diameter",
    "cnc_pocket_depth_width": "pocket depth over width", "cnc_pocket_depth_tool": "pocket depth over the largest cutter that fits",
    "cnc_pocket_depth_xy": "pocket depth over its length", "cnc_mill_depth_max": "milled depth below the face it is cut from",
    "cnc_slot_min": "narrowest pocket or slot", "cnc_wall_min": "thinnest wall", "cnc_wall_height_ratio": "wall thickness against its height",
    "cnc_hole_min": "smallest hole", "cnc_hole_depth_ratio": "hole depth over diameter", "cnc_hole_standard_drill": "hole at a standard drill size",
    "cnc_thread_min": "thread size", "cnc_thread_range": "thread size", "cnc_thread_depth_ratio_max": "thread depth over diameter",
    "cnc_thread_depth_ratio_min": "thread depth over diameter", "cnc_thread_depth_max": "thread depth", "cnc_thread_modeled_d": "modelled hole for the thread",
    "cnc_blind_tap_runout": "plain hole below a blind thread", "cnc_part_max_size": "part size", "cnc_part_min_size": "part size (minimum)",
    "cnc_part_min_volume": "part volume", "cnc_undercut": "faces no straight cutter reaches", "cnc_off_axis_features": "holes or cylinders off the principal axes",
    "cnc_setups_max": "set-ups (directions cut from)",
    "p3d_wall_min": "thinnest wall", "p3d_wall_min_unsupported": "thinnest unsupported wall", "p3d_wall_min_size_band": "thinnest wall for the part's size",
    "p3d_feature_min": "smallest pin or boss", "p3d_pin_min": "smallest pin", "p3d_pin_height_max": "pin height for its diameter",
    "p3d_hole_min": "smallest hole", "p3d_hole_depth_max": "small-hole depth", "p3d_hole_depth_ratio": "hole depth over diameter",
    "p3d_overhang_max_deg": "overhang beyond the angle", "p3d_overhang_length_max": "unsupported cantilever", "p3d_bridge_max": "bridge span",
    "p3d_horizontal_hole_max": "horizontal hole diameter", "p3d_part_max_size": "part size", "p3d_part_min_size": "part size (minimum)",
    "p3d_part_min_sum": "sum of the bounding box sides", "p3d_thread_in_print": "threads in the print", "p3d_thread_min": "thread size in the print",
    "p3d_enclosed_void": "enclosed voids (need escape holes)", "p3d_warp_size": "part length (warp)", "p3d_warp_thickness": "thinnest wall of a long part (warp)",
}
UNITLESS = {"cnc_corner_sharp", "cnc_corner_ld_ratio", "cnc_pocket_depth_width", "cnc_pocket_depth_tool", "cnc_pocket_depth_xy", "cnc_hole_depth_ratio",
            "cnc_thread_depth_ratio_max", "cnc_thread_depth_ratio_min", "cnc_undercut", "cnc_off_axis_features", "cnc_setups_max", "cnc_thread_range",
            "p3d_hole_depth_ratio", "p3d_thread_in_print", "p3d_enclosed_void", "cnc_part_min_volume"}


# ------------------------------------------------------------------------------------------- data
@lru_cache(maxsize=None)
def load() -> dict:
    out = {}
    for p in sorted(DATA.glob("*.json")):
        if p.name.startswith("_"):
            continue
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("schema") != SCHEMA:
            raise ValueError(f"{p.name}: schema {doc.get('schema')!r}, expected {SCHEMA}")
        out[doc["supplier"]] = doc
    return out


def sources() -> dict:
    p = DATA / "_sources.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def suppliers(process: str | None = None) -> list[str]:
    return sorted(s for s, d in load().items() if process is None or any(_process_ok(r, process) for r in d["rules"]))


def all_rules() -> list[dict]:
    return [r for d in load().values() for r in d["rules"]]


def rule(rid: str) -> dict:
    return next(r for r in all_rules() if r["id"] == rid)


def name_of(supplier: str) -> str:
    return (load().get(supplier) or {}).get("name", supplier)


def material_matches(rule_mat: str, material: str) -> bool:
    for tok in str(rule_mat).split("|"):
        if tok == "metal" and material not in PLASTICS:
            return True
        if tok == "plastic" and material in PLASTICS:
            return True
        if SR.material_matches(tok, material):
            return True
    return False


def _process_ok(r: dict, process: str) -> bool:
    return r["process"] == process or process in (r.get("applies_processes") or ())


def applicable(supplier: str, process: str, material: str) -> list[dict]:
    doc = load().get(supplier)
    return [r for r in (doc or {"rules": []})["rules"] if _process_ok(r, process) and material_matches(r["material"], material)]


def shop_for(c, design, process: str) -> str:
    """The rule set a part is judged against: meta['dfm']['process_shop'] (or 'shop'), else the design's
    manufacturing['process_shop'] / ['shop'], when that supplier publishes rules for the process; else Xometry for CNC
    and the owner's printer for FDM."""
    cands = [((c.meta.get("dfm") or {}).get("process_shop")), ((c.meta.get("dfm") or {}).get("shop"))]
    man = (getattr(design, "manufacturing", None) or {}) if design is not None else {}
    cands += [man.get("process_shop"), man.get("print_shop") if process in PRINT_PROCESSES else None, man.get("shop")]
    for s in cands:
        if s and s in load() and any(_process_ok(r, process) for r in load()[s]["rules"]):
            return s
    return DEFAULT.get(process, "xometry")


# ------------------------------------------------------------------------------------------ helpers
def _formula_limit(r: dict, d: float = 0.0, feat: dict | None = None) -> float | None:
    f = r.get("formula")
    if not f:
        return r.get("value_mm", r.get("value"))
    st = (feat or {}).get("settings") or {}
    v = f.get("d", 0.0) * d + f.get("const_mm", 0.0) + f.get("nozzle", 0.0) * st.get("nozzle_mm", 0.0) + f.get("line_width", 0.0) * st.get("line_width_mm", 0.0)
    if f.get("floor_mm") is not None:
        v = max(v, f["floor_mm"])
    return round(v, 3)


def _ok(v, lim, comp, tol=0.0) -> bool:
    if comp == "<":
        return v < lim - 1e-9
    return SR._cmp(v, lim, comp, tol)


def _worst(rule: dict, items: list, value_of, lim_of, what: str) -> dict | None:
    comp = rule["comparison"]
    rows = []
    for it in items:
        v, lim = value_of(it), lim_of(it)
        if v is None or lim is None:
            continue
        if comp in (">=",):
            margin = v - lim
        elif comp in ("<=", "<"):
            margin = (lim - v) if math.isfinite(v) else -1e9
        elif comp == "==":
            margin = rule.get("tolerance_mm", 0.0) - abs(v - lim)
        else:
            margin = min(v - lim[0], lim[1] - v)
        rows.append((margin, v, lim, it))
    if not rows:
        return None
    bad = [x for x in rows if not _ok(x[1], x[2], comp, rule.get("tolerance_mm", 0.0))]
    m = min(rows, key=lambda x: x[0])
    val = m[1] if not isinstance(m[1], float) else (round(m[1], 3) if math.isfinite(m[1]) else "sharp (no radius)")
    return {"status": "fail" if bad else "pass", "measured": val,
            "limit": [round(x, 3) for x in m[2]] if isinstance(m[2], (list, tuple)) else round(float(m[2]), 3), "count": len(bad), "of": len(rows),
            "at": [x[3].get("at") for x in sorted(bad, key=lambda x: x[0])[:6] if x[3].get("at")], "what": what}


def _applies(r: dict, feat: dict, item: dict | None = None) -> bool:
    a = r.get("applies") or {}
    ext = feat.get("extents_mm") or []
    longest = max(ext) if ext else 0.0
    if "part_max_mm_le" in a and not longest <= a["part_max_mm_le"] + 1e-6:
        return False
    if "part_max_mm_gt" in a and not longest > a["part_max_mm_gt"] + 1e-6:
        return False
    if item is not None:
        d = item.get("d")
        if "thread_d" in a and abs((d or 0) - a["thread_d"]) > 1e-6:
            return False
        if "thread_d_lt" in a and not (d or 0) < a["thread_d_lt"] - 1e-9:
            return False
        if "hole_d_le" in a and not (d or 0) <= a["hole_d_le"] + 1e-6:
            return False
        if "hole_d_gt" in a and not (d or 0) > a["hole_d_gt"] + 1e-6:
            return False
        if "d_range" in a and not (a["d_range"][0] - 1e-6 <= (d or 0) < a["d_range"][1] - 1e-9):
            return False
    if "size_band_mm" in a:
        return _size_band(feat, r) == a["size_band_mm"]
    return True


def _size_band(feat: dict, r: dict) -> float | None:
    """The smallest of the supplier's size bands (square b x b) holding the part's two largest sides; the largest band
    for anything bigger (that band's figure is the least the table asks for a part that size)."""
    bands = sorted({x["applies"]["size_band_mm"] for x in applicable(r["supplier"], r["process"], feat["material"])
                    if (x.get("applies") or {}).get("size_band_mm") and x["rule"] == r["rule"]})
    ext = sorted(feat.get("extents_mm") or [0, 0, 0])
    need = ext[-1]
    for b in bands:
        if need <= b + 1e-6:
            return b
    return bands[-1] if bands else None


def _corners(feat):
    return feat.get("corners") or []


def _vertical_corners(feat):
    return [c for c in _corners(feat) if c.get("approach")]


def _std_drills() -> list[float]:
    try:
        return rule("hubs.cnc.metric_drills")["value_mm"]
    except StopIteration:
        return []


def _is_std(d: float, drills: list[float]) -> bool:
    if any(abs(d - x) <= 0.01 for x in drills):
        return True
    inch = round(d / 25.4 * 64) / 64 * 25.4                  # fractional inch drills by 1/64 in
    return abs(d - inch) <= 0.01


# ------------------------------------------------------------------------------------------ evaluate
def evaluate(feat: dict, supplier: str) -> list[dict]:
    """Judge one part's features against one supplier's CNC or printing rules: [{rule, status, measured, limit, ...}]."""
    out = []
    for r in applicable(supplier, feat["process"], feat["material"]):
        if r.get("duplicate_of"):
            out.append({"rule": r, "status": "info", "detail": f"same rule as {r['duplicate_of']}"})
            continue
        if r["comparison"] == "info" or r["severity"] == "info" and r["rule"] not in MEASURED:
            out.append({"rule": r, "status": "info", "limit": r.get("value_mm", r.get("value"))})
            continue
        if r.get("evaluate") is False or r["rule"] not in MEASURED:
            out.append({"rule": r, "status": "not_evaluated", "detail": r.get("note") or "rule kind not measured by mechloop"})
            continue
        if not _applies(r, feat):
            continue
        res = _one(r, feat)
        if res is not None:
            res["rule"] = r
            out.append(res)
    return out


def _one(r: dict, feat: dict) -> dict | None:
    k, comp = r["rule"], r["comparison"]
    val = r.get("value_mm", r.get("value"))
    ext = sorted(feat.get("extents_mm") or [])
    holes = feat.get("holes") or []
    threads = [t for t in (feat.get("threads") or []) if _applies(r, feat, t)]
    # ------------------------------------------------------------------ CNC corners and pockets
    if k == "cnc_corner_sharp":
        sharp = [c for c in _vertical_corners(feat) if c["radius"] <= 0.0]
        if not _vertical_corners(feat):
            return None
        return {"status": "fail" if len(sharp) > val else "pass", "measured": len(sharp), "limit": val, "count": len(sharp),
                "of": len(_vertical_corners(feat)), "at": [c["at"] for c in sharp[:6]]}
    if k == "cnc_corner_radius_min":
        return _worst(r, _vertical_corners(feat), lambda c: c["radius"], lambda c: val, "vertical inside corner radius")
    if k == "cnc_corner_radius_depth":
        return _worst(r, _vertical_corners(feat), lambda c: c["radius"], lambda c: _formula_limit(r, c["depth"]), "inside corner radius against its depth")
    if k == "cnc_corner_ld_ratio":
        return _worst(r, _vertical_corners(feat), lambda c: (c["depth"] / (2 * c["radius"])) if c["radius"] > 0 else math.inf,
                      lambda c: val, "corner depth over cutter diameter")
    pk = feat.get("pockets") or []
    if k == "cnc_pocket_depth_width":
        return _worst(r, [p for p in pk if p.get("width")], lambda p: p["depth"] / p["width"], lambda p: val, "pocket depth over width")
    if k == "cnc_pocket_depth_tool":
        return _worst(r, [p for p in pk if p.get("tool_d")], lambda p: p["depth"] / p["tool_d"], lambda p: val, "pocket depth over the largest cutter that fits")
    if k == "cnc_pocket_depth_xy":
        return _worst(r, [p for p in pk if p.get("length")], lambda p: p["depth"] / p["length"], lambda p: val, "pocket depth over its length")
    if k == "cnc_mill_depth_max":
        return _worst(r, pk, lambda p: p["depth_from_top"], lambda p: val, "milled depth below the face it is cut from")
    if k == "cnc_slot_min":
        items = [{"d": p["width"], "at": p["at"]} for p in pk if p.get("width")] + [{"d": s["width"], "at": s["at"]} for s in feat.get("slots") or []]
        return _worst(r, items, lambda x: x["d"], lambda x: val, "narrowest pocket or slot")
    # ------------------------------------------------------------------ walls
    if k in ("cnc_wall_min", "p3d_wall_min", "p3d_wall_min_size_band", "p3d_warp_thickness"):
        v = feat.get("min_wall_mm")
        if v is None:
            return {"status": "pass", "measured": None, "limit": _formula_limit(r, feat=feat), "detail": "no wall found (no two near-parallel faces)"}
        lim = _formula_limit(r, feat=feat)
        walls = feat.get("thin_walls") or []
        at = [w["at"] for w in walls if w["t"] < lim - 1e-6][:6]
        return {"status": "pass" if _ok(v, lim, comp) else "fail", "measured": v, "limit": lim, "at": at,
                "count": sum(1 for w in walls if w["t"] < lim - 1e-6) or None}
    if k == "p3d_wall_min_unsupported":
        un = [w for w in feat.get("thin_walls") or [] if not w.get("supported")]
        if not un:
            return {"status": "pass", "measured": None, "limit": val, "detail": "no unsupported wall thinner than 3 mm"}
        return _worst(r, un, lambda w: w["t"], lambda w: val, "thinnest unsupported wall")
    if k == "cnc_wall_height_ratio":
        return _worst(r, [w for w in feat.get("thin_walls") or [] if w.get("height_mm")], lambda w: w["t"], lambda w: _formula_limit(r, w["height_mm"]),
                      "wall thickness against its height")
    # ------------------------------------------------------------------ holes
    if k in ("cnc_hole_min", "p3d_hole_min"):
        return _worst(r, holes, lambda h: h["d"], lambda h: val, "smallest hole")
    if k in ("cnc_hole_depth_ratio", "p3d_hole_depth_ratio"):
        return _worst(r, [h for h in holes if _applies(r, feat, h)], lambda h: h["depth"] / h["d"], lambda h: val, "hole depth over diameter")
    if k == "cnc_hole_standard_drill":
        drills = _std_drills()
        items = [h for h in holes if h["d"] <= val + 1e-6]
        if not items:
            return None
        bad = [h for h in items if not _is_std(h["d"], drills)]
        return {"status": "fail" if bad else "pass", "measured": sorted({h["d"] for h in bad}) or sorted({h["d"] for h in items}),
                "limit": "a standard drill diameter", "count": len(bad), "of": len(items), "at": [h["at"] for h in bad[:6]]}
    if k == "p3d_hole_depth_max":
        return _worst(r, [h for h in holes if _applies(r, feat, h)], lambda h: h["depth"], lambda h: val, "small-hole depth")
    if k == "p3d_horizontal_hole_max":
        return _worst(r, [h for h in holes if h.get("horizontal")], lambda h: h["d"], lambda h: val, "horizontal hole diameter")
    # ------------------------------------------------------------------ threads
    if k in ("cnc_thread_min", "p3d_thread_min"):
        return _worst(r, threads, lambda t: t["d"], lambda t: val, "thread size")
    if k == "cnc_thread_range":
        if not threads:
            return None
        sizes = r.get("sizes")
        bad = [t for t in threads if not (val[0] - 1e-6 <= t["d"] <= val[1] + 1e-6) or (sizes and not any(abs(t["d"] - s) < 1e-6 for s in sizes))]
        return {"status": "fail" if bad else "pass", "measured": sorted({f"M{t['d']:g}" for t in (bad or threads)}),
                "limit": f"M{val[0]:g} to M{val[1]:g}" + (f" ({', '.join('M%g' % s for s in sizes)})" if sizes else ""), "count": len(bad), "of": len(threads),
                "at": [t["at"] for t in bad[:6] if t.get("at")]}
    if k == "cnc_thread_depth_ratio_max" or k == "cnc_thread_depth_ratio_min":
        return _worst(r, [t for t in threads if t.get("depth")], lambda t: float(t["depth"]) / t["d"], lambda t: val, "thread depth over diameter")
    if k == "cnc_thread_depth_max":
        return _worst(r, [t for t in threads if t.get("depth")], lambda t: float(t["depth"]), lambda t: val, "thread depth")
    if k == "cnc_thread_modeled_d":
        items = [t for t in threads if t.get("hole")]
        if r.get("formula"):
            return _worst(r, items, lambda t: t["hole"]["d"], lambda t: _formula_limit(r, t["d"]), "modelled hole diameter for the thread")
        return _worst(r, items, lambda t: t["hole"]["d"], lambda t: val, "modelled hole diameter for the thread")
    if k == "cnc_blind_tap_runout":
        return _worst(r, [t for t in threads if t.get("plain_below_mm") is not None], lambda t: t["plain_below_mm"],
                      lambda t: _formula_limit(r, t["d"]), "plain hole below a blind thread")
    if k == "p3d_thread_in_print":
        th = feat.get("threads") or []
        return {"status": "fail" if len(th) > val else "pass", "measured": len(th), "limit": val, "at": [t["at"] for t in th[:6] if t.get("at")]} if th else None
    # ------------------------------------------------------------------ size and access
    if k in ("cnc_part_max_size", "p3d_part_max_size"):
        lim = list(val) if isinstance(val, (list, tuple)) else [val]
        if r.get("use_design_build_volume") and feat.get("build_volume_mm"):
            lim = list(feat["build_volume_mm"])
        if not ext:
            return None
        if len(lim) == 1:
            ok = ext[-1] <= lim[0] + 1e-6
        else:
            ok = all(a <= b + 1e-6 for a, b in zip(ext, sorted(lim)))
        return {"status": "pass" if ok else "fail", "measured": [round(x, 1) for x in ext], "limit": sorted(lim)}
    if k in ("cnc_part_min_size", "p3d_part_min_size"):
        lim = sorted(val)
        ok = all(a >= b - 1e-6 for a, b in zip(ext, lim))
        return {"status": "pass" if ok else "fail", "measured": [round(x, 1) for x in ext], "limit": lim}
    if k == "p3d_part_min_sum":
        s = sum(ext)
        return {"status": "pass" if s >= val - 1e-6 else "fail", "measured": round(s, 1), "limit": val}
    if k == "cnc_part_min_volume":
        v = feat.get("volume_mm3")
        return None if v is None else {"status": "pass" if v >= val - 1e-6 else "fail", "measured": v, "limit": val}
    if k == "cnc_undercut":
        bad = (feat.get("access") or {}).get("inaccessible") or []
        return {"status": "fail" if len(bad) > val else "pass", "measured": len(bad), "limit": val, "count": len(bad), "at": [x["at"] for x in bad[:6]],
                "detail": f"{sum(x['area_mm2'] for x in bad):.0f} mm2" if bad else None}
    if k == "cnc_off_axis_features":
        n = feat.get("angled_cylinders") or 0
        return {"status": "fail" if n > val else "pass", "measured": n, "limit": val, "at": (feat.get("angled_at") or [])[:6] if n else []}
    if k == "cnc_setups_max":
        a = feat.get("access") or {}
        return {"status": "pass" if a.get("setups", 1) <= val else "fail", "measured": a.get("setups"), "limit": val, "detail": ", ".join(a.get("setup_dirs") or [])}
    # ------------------------------------------------------------------ printing
    pins = feat.get("pins") or []
    if k in ("p3d_feature_min", "p3d_pin_min"):
        return _worst(r, pins, lambda p: p["d"], lambda p: val, "smallest pin or boss")
    if k == "p3d_pin_height_max":
        return _worst(r, [p for p in pins if _applies(r, feat, p)], lambda p: p["height"], lambda p: val, "pin height for its diameter")
    if k == "p3d_overhang_max_deg":
        bins = feat.get("overhang_bins") or {}
        area = sum(a for b, a in bins.items() if int(b) + 1 > val + 1e-9)
        worst = max((int(b) + 1 for b, a in bins.items() if a > 0.5), default=0)
        at = (feat.get("overhang_at") or {}).get(str(int(val)), []) or (feat.get("overhang_at") or {}).get("45", [])
        return {"status": "fail" if area > AREA_TOL_MM2 else "pass", "measured": round(area, 1), "limit": 0.0, "at": at[:6] if area > AREA_TOL_MM2 else [],
                "detail": f"{area:.0f} mm2 of down-facing surface steeper than {val:g} deg from vertical (steepest {worst} deg); "
                          f"bridged flat ceilings up to {feat.get('bridges_excused_up_to_mm', 30):g} mm and horizontal-hole crowns up to "
                          f"{feat.get('hole_crowns_excused_up_to_mm', 10):g} mm are judged as bridges and holes"}
    if k == "p3d_overhang_length_max":
        cl = [f for f in feat.get("flat_overhangs") or [] if f["kind"] in ("cantilever", "floating") and f["length_mm"] > CANTILEVER_TOL_MM]
        if not cl:
            return {"status": "pass", "measured": 0.0, "limit": val, "detail": "no flat overhang held on one side only"}
        return _worst(r, [dict(f, at=f.get("far_at") or f["at"]) for f in cl], lambda f: f["length_mm"], lambda f: val, "unsupported cantilever")
    if k == "p3d_bridge_max":
        br = [dict(f, at=f.get("far_at") or f["at"]) for f in feat.get("flat_overhangs") or [] if f["kind"] == "bridge"]
        return _worst(r, br, lambda f: f["span_mm"], lambda f: val, "bridge span") if br else None
    if k == "p3d_enclosed_void":
        n = feat.get("enclosed_voids") or 0
        return {"status": "fail" if n > 0 else "pass", "measured": n, "limit": 0, "detail": f"each needs an escape hole of at least {val:g} mm" if n else None}
    if k == "p3d_warp_size":
        return {"status": "pass" if ext and ext[-1] <= val + 1e-6 else "fail", "measured": ext[-1] if ext else None, "limit": val} if ext else None
    return {"status": "not_evaluated", "detail": "rule kind not measured"}


# ------------------------------------------------------------------------------------ summarising
def summarise(results: list[dict]) -> dict:
    return SR.summarise(results)


def missing_kinds(feat: dict, results: list[dict]) -> list[str]:
    have = {x["rule"]["rule"] for x in results if x["status"] in ("pass", "fail")}
    alt = {"p3d_wall_min": {"p3d_wall_min", "p3d_wall_min_size_band", "p3d_wall_min_unsupported"}, "p3d_feature_min": {"p3d_feature_min", "p3d_pin_min"},
           "cnc_corner_radius_depth": {"cnc_corner_radius_depth", "cnc_corner_ld_ratio", "cnc_corner_radius_min"},
           "cnc_pocket_depth_width": {"cnc_pocket_depth_width", "cnc_pocket_depth_tool"}}
    return [k for k in EXPECTED.get(feat["process"], ()) if not (alt.get(k, {k}) & have)]


def verdict(summary: dict, missing: list[str], n_eval: int) -> str:
    return SR.verdict(summary, missing, n_eval).replace("for this material and thickness", "for this process and material")


def judge(feat: dict, process: str | None = None) -> dict:
    out = {}
    for sup in suppliers(process or feat["process"]):
        res = evaluate(feat, sup)
        if not res:
            continue
        summ = summarise(res)
        miss = missing_kinds(feat, res)
        n_eval = sum(1 for x in res if x["status"] in ("pass", "fail"))
        out[sup] = {"results": res, "summary": summ, "missing": miss, "verdict": verdict(summ, miss, n_eval)}
    return out


def unit_of(kind: str) -> str:
    if kind in UNITLESS:
        return ""
    if kind == "p3d_overhang_max_deg":
        return " mm2"
    return " mm"
