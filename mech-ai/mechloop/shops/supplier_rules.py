"""Suppliers' published sheet-metal and CNC design rules, as data, and their evaluation against a part's features.

The rules live in mechloop/data/supplier_rules/<supplier>.json (schema "mechloop.supplier_rules/1"). Each rule names
its supplier, process, material (a mechloop material key, "*" for all, "al*" for every aluminium), thickness (mm and as
published, or a published range), the rule kind it constrains (`rule`), its value in mm (or a `formula` in the
thickness t, bend radius r and feature size d), a comparison, a severity, the page it came from (`source_url`), a short
quote from that page and the retrieval date. docs/SUPPLIER_RULES.md is the readable form.

Nothing is interpolated: a part whose thickness has no row for a rule gets "no published rule" for it.

This module is geometry-free: `evaluate(features, supplier)` takes the dict built by
mechloop/verifiers/dfm_supplier.py (`features_of`) and returns one result per applicable rule. Tests drive it with
hand-made feature dicts as well as with real parts.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "supplier_rules"
SCHEMA = "mechloop.supplier_rules/1"
T_TOL = 0.05            # a part's thickness matches a published thickness within this (mm), as the stock check does
DEFAULT_SHOP = {"sheet": "sendcutsend", "machined": "xometry"}
PROCESS_GROUPS = {"sheet": ("laser_cut", "bend", "hardware", "tap", "countersink"), "machined": ("cnc_milling",)}

# rule kinds the evaluator measures, and the part features they need ("form": flat / bent / any; "needs": feature key)
MEASURED = {
    "hole_min", "slot_min", "notch_min", "web_min", "hole_edge_web", "slot_edge_web", "hole_hole_web", "tab_min", "cut_away_max",
    "part_min_size", "part_max_size", "thickness_min", "thickness_max", "thickness_range",
    "bend_offered", "bend_radius", "bend_radius_min", "bend_radius_range", "flange_min", "flange_support_min", "feature_to_bend",
    "bend_length_max", "bend_angle_max", "bend_part_min_size", "bend_part_max_size", "bend_material_review",
    "pem_sheet_min", "pem_sheet_max", "pem_sheet_range_al", "pem_center_to_edge", "pem_center_to_bend", "pem_center_to_center",
    "tap_offered", "tap_metric_range", "tap_hole_to_edge", "countersink_offered",
    "cnc_min_feature", "cnc_min_wall", "cnc_min_nominal_thickness", "cnc_part_max_size", "cnc_thread_range", "cnc_thread_callout",
}
INFO_KINDS = {"tolerance_cut", "tolerance_bend", "tolerance_bend_angle", "tolerance_cnc", "kerf", "k_factor", "pem_hole_diameter",
              "pem_hole_tolerance", "bend_radius_options", "cnc_thread_standard"}
# which kinds a part should have a rule for, by form; used to report "no published rule"
EXPECTED = {
    "flat": ("hole_min", "web_min", "hole_edge_web", "part_max_size"),
    "bent": ("hole_min", "flange_min", "feature_to_bend", "bend_radius", "bend_length_max"),
    "machined": ("cnc_min_feature", "cnc_part_max_size"),
}


# ------------------------------------------------------------------------------------------- data
@lru_cache(maxsize=None)
def load() -> dict:
    """{supplier: document} for every rule file."""
    out = {}
    for p in sorted(DATA.glob("*.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        if doc.get("schema") != SCHEMA:
            raise ValueError(f"{p.name}: schema {doc.get('schema')!r}, expected {SCHEMA}")
        out[doc["supplier"]] = doc
    return out


def suppliers() -> list[str]:
    return sorted(load())


def all_rules() -> list[dict]:
    return [r for doc in load().values() for r in doc["rules"]]


def name_of(supplier: str) -> str:
    return (load().get(supplier) or {}).get("name", supplier)


def material_matches(rule_mat: str, material: str) -> bool:
    if rule_mat in ("*", material):
        return True
    return rule_mat.endswith("*") and material.startswith(rule_mat[:-1])


def thickness_matches(rule: dict, t: float | None) -> bool:
    if rule.get("thickness_range_mm"):
        if t is None:
            return False
        lo, hi = rule["thickness_range_mm"]
        return lo - 0.02 <= t <= hi + 0.02
    if rule.get("thickness_mm") is None:
        return True
    return t is not None and abs(rule["thickness_mm"] - t) <= T_TOL


def applicable(supplier: str, material: str, t: float | None, kinds=None, processes=None) -> list[dict]:
    doc = load().get(supplier)
    if not doc:
        return []
    out = []
    for r in doc["rules"]:
        if kinds is not None and r["rule"] not in kinds:
            continue
        if processes is not None and r["process"] not in processes:
            continue
        if material_matches(r["material"], material) and thickness_matches(r, t):
            out.append(r)
    return out


def published_thicknesses(supplier: str, material: str, kind: str) -> list[float]:
    """Thicknesses (mm) at which a supplier publishes a rule of this kind for this material (for 'no published rule' hints)."""
    doc = load().get(supplier) or {"rules": []}
    return sorted({r["thickness_mm"] for r in doc["rules"] if r["rule"] == kind and r.get("thickness_mm") is not None
                   and material_matches(r["material"], material)})


def limit(rule: dict, t: float = 0.0, r: float = 0.0, d: float = 0.0):
    """The rule's limit for a part of thickness t, bend radius r and feature size d: mm (or the rule's own unit)."""
    f = rule.get("formula")
    if f:
        v = f.get("t", 0.0) * t + f.get("r", 0.0) * r + f.get("d", 0.0) * d + f.get("const_mm", 0.0)
        if f.get("floor_mm") is not None:
            v = max(v, f["floor_mm"])
        return round(v, 3)
    if "value_mm" in rule:
        return rule["value_mm"]
    return rule.get("value")


def shop_for(c, design=None, process: str | None = None) -> str:
    """The supplier a part is judged against: meta["dfm"]["shop"], else the design's manufacturing["shop"], else the default
    for its process (SendCutSend for sheet, Xometry for machined). A shop with no rule file (e.g. "generic") falls back
    to the default."""
    shop = ((c.meta.get("dfm") or {}).get("shop") or ((design.manufacturing or {}).get("shop") if design is not None else None))
    if shop in load():
        return shop
    return DEFAULT_SHOP.get(process or "", "sendcutsend")


# ------------------------------------------------------------------------------------- evaluation
def _cmp(measured, lim, comparison: str, tol: float = 0.0) -> bool:
    if comparison == ">=":
        return measured >= lim - 1e-6
    if comparison == "<=":
        return measured <= lim + 1e-6
    if comparison == "==":
        return abs(measured - lim) <= tol + 1e-6
    if comparison == "within":
        return lim[0] - 1e-6 <= measured <= lim[1] + 1e-6
    raise ValueError(comparison)


def _size_ok(size, lim, comparison) -> bool:
    """size (short, long) against a published (short, long) minimum or maximum."""
    s, l_ = sorted(size)
    a, b = sorted(lim)
    if comparison == ">=":
        return s >= a - 1e-6 and l_ >= b - 1e-6
    return s <= a + 1e-6 and l_ <= b + 1e-6


def _k_factor(supplier: str, material: str, t: float) -> float | None:
    ks = [r for r in applicable(supplier, material, t, kinds={"k_factor"}) if isinstance(r.get("value"), (int, float))]
    return float(ks[0]["value"]) if ks else None


def _flange_limit(supplier: str, material: str, t: float, r: float) -> tuple[float, dict] | None:
    """The supplier's governing minimum flange length (largest error-level limit) for this stock and radius."""
    best = None
    for rule in applicable(supplier, material, t, kinds={"flange_min"}):
        if rule.get("evaluate") is False or rule["severity"] != "error":
            continue
        v = limit(rule, t, r)
        if best is None or v > best[0]:
            best = (v, rule)
    return best


def _develop(feat: dict, supplier: str) -> tuple[list | None, str | None]:
    """Flat blank of a bent part (short, long) from its features, using the supplier's K-factor where published."""
    dv = feat.get("develop")
    if not dv:
        return None, "flat blank of a part with more than one bend is not unfolded (gap)"
    k = _k_factor(supplier, feat["material"], feat["thickness_mm"])
    basis = "supplier K-factor" if k is not None else "K = 0.5 (no K-factor published; estimate)"
    k = 0.5 if k is None else k
    arc = (dv["r"] + k * feat["thickness_mm"]) * math.radians(dv["angle"])
    return sorted([round(dv["tangent_sum"] + arc, 2), round(dv["width"], 2)]), basis


def evaluate(feat: dict, supplier: str) -> list[dict]:
    """Judge one part's features against one supplier's rules.

    Returns [{rule, status, measured, limit, at, count, detail}] where status is "pass", "fail", "not_evaluated" (the rule
    needs a feature mechloop does not extract, or the rule is kept for reference) or "info"."""
    mat, t, form = feat["material"], feat.get("thickness_mm"), feat.get("form")
    procs = PROCESS_GROUPS["machined"] if feat.get("process") == "machined" else PROCESS_GROUPS["sheet"]
    if feat.get("process") == "sheet" and form != "bent":
        procs = tuple(p for p in procs if p != "bend")
    rules = applicable(supplier, mat, t, processes=procs)
    if feat.get("process") == "sheet" and form == "bent":
        rules += [r for r in applicable(supplier, mat, t, processes=("laser_cut",)) if r["rule"] in ("part_min_size", "part_max_size")
                  and r not in rules]
    out = []
    for rule in rules:
        res = _one(rule, feat, supplier)
        if res is not None:
            res["rule"] = rule
            out.append(res)
    return out


def _one(rule: dict, feat: dict, supplier: str) -> dict | None:
    kind, comp = rule["rule"], rule["comparison"]
    t = feat.get("thickness_mm") or 0.0
    if kind in INFO_KINDS or comp == "info" or rule.get("duplicate_of"):
        return {"status": "info", "limit": limit(rule, t)}
    if not _relevant(kind, feat):
        return None
    if rule.get("evaluate") is False or kind not in MEASURED:
        return {"status": "not_evaluated", "detail": rule.get("note") or "rule kind not measured by mechloop"}
    holes = feat.get("holes") or []
    bends = feat.get("bends") or []

    def worst(items, value_of, lim_of, label):
        """Worst item against a per-item limit; None if no items."""
        rows = []
        for it in items:
            v, lim_ = value_of(it), lim_of(it)
            if v is None or lim_ is None:
                continue
            if comp == ">=":
                margin = v - lim_
            elif comp == "<=":
                margin = lim_ - v
            elif comp == "==":
                margin = rule.get("tolerance_mm", 0.0) - abs(v - lim_)
            else:
                margin = min(v - lim_[0], lim_[1] - v)
            rows.append((margin, v, lim_, it))
        if not rows:
            return None
        bad = [x for x in rows if not _cmp(x[1], x[2], comp, rule.get("tolerance_mm", 0.0))]
        m = min(rows, key=lambda x: x[0])
        return {"status": "fail" if bad else "pass", "measured": round(m[1], 3),
                "limit": [round(x, 3) for x in m[2]] if isinstance(m[2], list) else round(m[2], 3), "count": len(bad),
                "of": len(rows), "at": [x[3].get("at") for x in sorted(bad, key=lambda x: x[0])[:6] if x[3].get("at")], "what": label}

    lim_t = limit(rule, t)
    # ---------------------------------------------------------------- cutting
    if kind == "hole_min":
        return worst(holes, lambda h: h["d"], lambda h: lim_t, "hole or cut-out size")
    if kind in ("slot_min", "notch_min"):
        slots = [h for h in holes if h.get("slot")] if kind == "slot_min" else []
        items = slots + [{"d": w, "at": at} for w, at in feat.get("notches") or []]
        if items:
            return worst(items, lambda h: h["d"], lambda h: lim_t, "slot or notch width")
        if feat.get("notch_probe_mm") is None:
            return None
        return ({"status": "pass", "measured": None, "limit": lim_t, "detail": f"no slot, and no notch narrower than {feat['notch_probe_mm']:g} mm"}
                if lim_t <= feat["notch_probe_mm"] + 1e-6 else {"status": "not_evaluated", "detail": "limit above the notch probe width"})
    if kind == "web_min":
        return worst(holes, lambda h: _min(h.get("edge_web"), h.get("web")), lambda h: lim_t, "material between cut features or to the edge")
    if kind == "hole_edge_web":
        return worst([h for h in holes if h.get("round")], lambda h: h.get("edge_web"), lambda h: limit(rule, t, d=h["d"]), "hole edge to outer edge")
    if kind == "slot_edge_web":
        return worst([h for h in holes if h.get("slot")], lambda h: _min(h.get("edge_web"), h.get("web")),
                     lambda h: limit(rule, t, d=h["d"]), "slot to edge or next cut feature")
    if kind == "hole_hole_web":
        return worst([h for h in holes if h.get("round") and h.get("hole_web") is not None], lambda h: h.get("hole_web"), lambda h: lim_t,
                     "material between two holes")
    if kind == "tab_min":
        if feat.get("tab_probe_mm") is None:
            return {"status": "not_evaluated", "detail": "necks not measured for this form"}
        if not feat.get("tabs"):
            return ({"status": "pass", "measured": None, "limit": lim_t, "detail": f"no tab or neck narrower than {feat['tab_probe_mm']:g} mm"}
                    if lim_t <= feat["tab_probe_mm"] + 1e-6 else {"status": "not_evaluated", "detail": "limit above the probe width"})
        return worst([{"d": w, "at": at} for w, at in feat["tabs"]], lambda h: h["d"], lambda h: lim_t, "tab or neck width")
    if kind == "cut_away_max":
        v = feat.get("cut_away_fraction")
        return None if v is None else {"status": "pass" if _cmp(v, lim_t, comp) else "fail", "measured": v, "limit": lim_t}
    if kind in ("part_min_size", "part_max_size", "bend_part_min_size", "bend_part_max_size"):
        size, basis = (feat.get("flat_size_mm"), None) if feat.get("form") == "flat" else _develop(feat, supplier)
        if not size:
            return {"status": "not_evaluated", "detail": basis or "flat size not known"}
        ok = _size_ok(size, lim_t, comp)
        return {"status": "pass" if ok else "fail", "measured": size, "limit": lim_t, "detail": basis}
    if kind in ("thickness_min", "thickness_max", "thickness_range"):
        return {"status": "pass" if _cmp(t, lim_t, comp) else "fail", "measured": t, "limit": lim_t}
    # ---------------------------------------------------------------- bending
    if kind == "bend_offered":
        return {"status": "fail" if bends else "pass", "measured": len(bends), "limit": "not bent at this thickness"}
    if kind == "bend_material_review":
        return {"status": "fail" if bends else "pass", "measured": len(bends), "limit": "manual review"} if bends else None
    if kind == "bend_radius":
        return worst(bends, lambda b: b["radius"], lambda b: lim_t, "inside bend radius")
    if kind == "bend_radius_min":
        return worst(bends, lambda b: b["radius"], lambda b: lim_t, "inside bend radius")
    if kind == "bend_radius_range":
        return worst(bends, lambda b: b["radius"], lambda b: lim_t, "inside bend radius")
    if kind == "bend_length_max":
        return worst(bends, lambda b: b["length"], lambda b: lim_t, "bend length")
    if kind == "bend_angle_max":
        return worst(bends, lambda b: b["angle"], lambda b: lim_t, "bend angle")
    if kind == "flange_min":
        fl = [dict(f, at=f.get("at"), r=b["radius"]) for b in bends for f in b.get("flanges", ())]
        return worst(fl, lambda f: f["length"], lambda f: limit(rule, t, r=f["r"]), "formed flange length")
    if kind == "flange_support_min":
        rows = []
        for b in bends:
            fl_lim = _flange_limit(supplier, feat["material"], t, b["radius"])
            if fl_lim is None:
                continue
            for f in b.get("flanges", ()):
                prof = f.get("profile") or []
                if prof and f["length"] >= fl_lim[0] - 1e-6:       # a flange short everywhere is the flange_min finding already
                    frac = sum(1 for x in prof if x >= fl_lim[0] - 1e-6) / len(prof)
                    rows.append({"frac": frac, "at": f.get("at")})
        if not rows:
            return {"status": "not_evaluated", "detail": "no flange-length rule for this stock to measure support against"}
        return worst(rows, lambda x: x["frac"], lambda x: lim_t, "share of the bend's length meeting the minimum flange")
    if kind == "feature_to_bend":
        ref = rule.get("reference") or "bend_tangent"
        rows = []
        k = _k_factor(supplier, feat["material"], t)
        for h in feat.get("hole_bend") or []:
            if ref == "bend_centerline":
                kk = k if k is not None else 0.0          # 0: from the inside radius, the shortest the arc can be (conservative)
                v = h["d_tan"] + (h["r"] + kk * t) * math.radians(h["angle"]) / 2
            else:
                v = h["d_tan"]
            rows.append({"v": v, "lim": limit(rule, t, r=h["r"]), "at": h.get("at")})
        if not rows:
            return {"status": "pass", "measured": None, "limit": lim_t, "detail": "no hole in a flange next to a bend"} if bends else None
        return worst(rows, lambda x: x["v"], lambda x: x["lim"], "hole edge to bend")
    # ---------------------------------------------------------------- hardware
    if kind.startswith("pem_"):
        pems = [p for p in feat.get("pems") or [] if _pem_rule_applies(rule, p, supplier, feat)]
        if not pems:
            return None
        if kind == "pem_sheet_min" or kind == "pem_sheet_max":
            return worst(pems, lambda p: t, lambda p: lim_t, f"sheet thickness for {rule['hardware']['sku']}")
        if kind == "pem_sheet_range_al":
            ok = _cmp(t, lim_t, "within")
            return {"status": "pass" if ok else "fail", "measured": t, "limit": lim_t, "at": [p.get("at") for p in pems][:6]}
        if kind == "pem_center_to_edge":
            return worst(pems, lambda p: p.get("center_edge"), lambda p: limit(rule, t, d=p.get("hole_d") or 0.0), "hardware centre to edge")
        if kind == "pem_center_to_bend":
            return worst([p for p in pems if p.get("center_bend") is not None], lambda p: p["center_bend"], lambda p: lim_t, "hardware centre to bend")
        if kind == "pem_center_to_center":
            return worst([p for p in pems if p.get("pitch") is not None], lambda p: p["pitch"], lambda p: lim_t, "hardware centre to centre")
        return None
    # ---------------------------------------------------------------- tapping / countersinking
    if kind in ("tap_offered", "tap_metric_range", "tap_hole_to_edge"):
        taps = feat.get("tapped") or []
        if not taps:
            return None
        if kind == "tap_offered":
            return {"status": "fail", "measured": [f"M{x['d']:g}" for x in taps], "limit": "not tapped at this thickness",
                    "at": [x.get("at") for x in taps][:6]}
        if kind == "tap_metric_range":
            return _within_all(taps, lim_t)
        return worst([x for x in taps if x.get("web") is not None], lambda x: x["web"], lambda x: lim_t, "tapped hole to nearest cut feature")
    if kind == "countersink_offered":
        n = feat.get("countersinks") or 0
        if not n:
            return None
        return {"status": "pass" if rule.get("value") else "fail", "measured": n, "limit": "offered" if rule.get("value") else "not offered at this thickness"}
    # ---------------------------------------------------------------- CNC
    if kind == "cnc_min_feature":
        vals = [v for v in (feat.get("smallest_hole_mm"), feat.get("min_wall_mm")) if v]
        if not vals:
            return {"status": "not_evaluated", "detail": "no hole or wall measured"}
        v = min(vals)
        return {"status": "pass" if _cmp(v, lim_t, comp) else "fail", "measured": v, "limit": lim_t}
    if kind == "cnc_min_wall":
        v = feat.get("min_wall_mm")
        return None if v is None else {"status": "pass" if _cmp(v, lim_t, comp) else "fail", "measured": v, "limit": lim_t}
    if kind == "cnc_min_nominal_thickness":
        ext = feat.get("extents_mm")
        return None if not ext else {"status": "pass" if _cmp(min(ext), lim_t, comp) else "fail", "measured": round(min(ext), 2), "limit": lim_t}
    if kind == "cnc_part_max_size":
        ext = feat.get("extents_mm")
        if not ext:
            return None
        ok = all(a <= b + 1e-6 for a, b in zip(sorted(ext), sorted(lim_t)))
        return {"status": "pass" if ok else "fail", "measured": [round(x, 1) for x in sorted(ext)], "limit": lim_t}
    if kind == "cnc_thread_range":
        taps = feat.get("tapped") or []
        return _within_all(taps, lim_t) if taps else None
    if kind == "cnc_thread_callout":
        taps = feat.get("tapped") or []
        return {"status": "fail", "measured": len(taps), "limit": "threads called out in the quote or on a drawing",
                "at": [x.get("at") for x in taps][:6]} if taps else None
    return {"status": "not_evaluated", "detail": "rule kind not measured"}


BEND_ONLY = {"relief_width_min", "relief_depth_min", "corner_relief_distance", "u_channel_base_ratio", "gauging_edge_min", "flange_min_flat",
             "tap_to_bend"}


def _relevant(kind: str, feat: dict) -> bool:
    """Whether the part has the feature a rule kind is about (a countersink rule says nothing about a part without one)."""
    if kind.startswith("countersink"):
        return bool(feat.get("countersinks"))
    if kind.startswith("tap_"):
        return bool(feat.get("tapped"))
    if kind.startswith("pem_"):
        return bool(feat.get("pems"))
    if kind in BEND_ONLY:
        return bool(feat.get("bends"))
    return True


def _within_all(taps, lim_) -> dict:
    bad = [x for x in taps if not (lim_[0] - 1e-6 <= x["d"] <= lim_[1] + 1e-6)]
    m = bad[0] if bad else taps[0]
    return {"status": "fail" if bad else "pass", "measured": f"M{m['d']:g}", "limit": f"M{lim_[0]:g} to M{lim_[1]:g}", "count": len(bad),
            "of": len(taps), "at": [x.get("at") for x in bad][:6]}


def _min(*vals):
    v = [x for x in vals if x is not None]
    return min(v) if v else None


def pem_sku_for(p: dict, supplier: str, t: float, material: str) -> tuple[str | None, str | None]:
    """The catalogue SKU a piece of hardware is judged against: the SKU it names if the supplier lists it, else the same family
    and thread whose thickness range admits the sheet. Returns (sku, note)."""
    doc = load().get(supplier) or {"rules": []}
    skus = {}
    for r in doc["rules"]:
        hw = r.get("hardware")
        if hw:
            skus.setdefault(hw["sku"], {"thread": hw["thread"], "rules": []})["rules"].append(r)
    if not skus:
        return None, None
    want = p.get("sku")
    if want in skus:
        return want, None
    fam = (want or "S-").split("-")[0]
    cands = [s for s, v in skus.items() if v["thread"] == p.get("thread") and s.split("-")[0] == fam]
    if not cands:
        return None, f"{name_of(supplier)} lists no {fam}-family {p.get('thread')} hardware"

    def fits(s):
        for r in skus[s]["rules"]:
            if r.get("evaluate") is False:
                continue
            if r["rule"] == "pem_sheet_min" and t < r["value_mm"] - 1e-6:
                return False
            if r["rule"] == "pem_sheet_max" and t > r["value_mm"] + 1e-6:
                return False
            if r["rule"] == "pem_sheet_range_al" and material.startswith("al") and not (r["value_mm"][0] - 1e-6 <= t <= r["value_mm"][1] + 1e-6):
                return False
        return True

    ok = [s for s in sorted(cands) if fits(s)]
    pick = ok[0] if ok else sorted(cands)[0]
    note = (f"{want} is not in {name_of(supplier)}'s hardware catalogue; judged against {pick}" if want else f"judged against {pick}")
    return pick, note


def _pem_rule_applies(rule: dict, p: dict, supplier: str, feat: dict) -> bool:
    hw = rule.get("hardware")
    if not hw:                                   # a general hardware rule (no SKU): applies to every piece
        return True
    sku, _ = pem_sku_for(p, supplier, feat.get("thickness_mm") or 0.0, feat["material"])
    return sku == hw["sku"]


# ------------------------------------------------------------------------------------ summarising
def summarise(results: list[dict]) -> dict:
    """Counts for a list of evaluate() results."""
    fails = [x for x in results if x["status"] == "fail"]
    return {"errors": sum(1 for x in fails if x["rule"]["severity"] == "error"),
            "warnings": sum(1 for x in fails if x["rule"]["severity"] == "warning"),
            "passed": sum(1 for x in results if x["status"] == "pass"),
            "not_evaluated": sum(1 for x in results if x["status"] == "not_evaluated"),
            "rules": len(results)}


def missing_kinds(feat: dict, supplier: str, results: list[dict]) -> list[str]:
    """Rule kinds a part of this form should be judged by but for which the supplier publishes nothing at this material and
    thickness ('no published rule')."""
    form = "machined" if feat.get("process") == "machined" else feat.get("form")
    have = {x["rule"]["rule"] for x in results}
    exp = list(EXPECTED.get(form, ()))
    if feat.get("pems"):
        exp += ["pem_center_to_edge"]
    if feat.get("tapped") and feat.get("process") == "sheet":
        exp += ["tap_metric_range"]
    if feat.get("countersinks"):
        exp += ["countersink_offered"]
    alt = {"bend_radius": {"bend_radius", "bend_radius_min", "bend_radius_range"}}
    return [k for k in exp if not (alt.get(k, {k}) & have)]


def verdict(summary: dict, missing: list[str], n_rules: int) -> str:
    if n_rules == 0:
        return "no published rules for this material and thickness"
    if summary["errors"]:
        return f"fails {summary['errors']} rule(s)"
    if summary["warnings"]:
        return f"passes, {summary['warnings']} recommendation(s) not met"
    return "passes" + (f" (no published rule for: {', '.join(missing)})" if missing else "")
