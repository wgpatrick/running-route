"""Each machined or printed part against the suppliers' published CNC-milling and 3D-printing rules
(mechloop/data/supplier_rules_cnc_3dp; the sheet-metal counterpart is dfm_supplier.py).

Called once per custom part from verifiers/manufacture.py, after the process checks. It

1. measures the features the rules speak about (verifiers/dfm_features.py): for machined parts tool access from the
   six principal directions (set-ups, inaccessible faces), vertical inside corners (radius, depth), pockets (depth,
   width, the cutter that fits), slots, holes, threads matched to their modelled holes, the thinnest walls and their
   height; for printed parts, in the print orientation, walls (supported or not), overhang area by angle, flat
   cantilevers and bridges, pins, holes, enclosed voids, threads and size;
2. judges them against the rule set the part is assigned to (process_rules.shop_for: the part's or design's
   'process_shop' / 'shop' when that supplier publishes rules for the process, else Xometry for CNC and the owner's
   printer, "own_printer", for FDM). A failed requirement is an error, a failed recommendation a warning
   (code "supplier_process_rule"); each finding names the rule id, the supplier, the measured value, the limit, the
   source URL (or repository file) and the supplier's own words, and points at the worst places;
3. adds one information finding per part ("supplier_process_rules_summary") with the verdict under every supplier's
   rules for the part's process (and, for printed parts, what an SLS, MJF or SLA service would say), the rule kinds no
   one publishes, and the rules not evaluated because the feature is not extracted (text, clearances between parts).

A PrusaSlicer cross-check runs for printed parts when design.manufacturing["prusaslicer_crosscheck"] is true (or
meta["dfm"]["prusaslicer_crosscheck"]): the part is sliced with support enabled in its print orientation, and the
finding says whether the slicer's support agrees with the overhang rules.
"""
from __future__ import annotations

import numpy as np

from ..shops import process_rules as PR
from . import dfm_features as FE


def _fmt(v) -> str:
    if isinstance(v, (list, tuple)):
        return " x ".join(_fmt(x) for x in v)
    if isinstance(v, float):
        return f"{v:.3g}" if abs(v) < 10 else f"{v:.1f}"
    return str(v)


def features(design, c, row: dict, sm, frame, cyls, holes) -> dict | None:
    proc = row.get("process")
    if proc == "machined":
        if row.get("form") == "turned":
            return None                      # lathe parts: the milling rules do not apply (no turning rules read yet)
        return FE.machined_features(design, c, sm, frame, cyls, holes)
    if proc == "printed":
        up = row.get("up_vector")
        f = FE.printed_features(design, c, sm, frame, cyls, holes, up=np.asarray(up, dtype=float) if up else None)
        pp = (c.meta.get("print") or {}).get("process") or (c.meta.get("dfm") or {}).get("print_process") or "fdm"
        if pp not in PR.PRINT_PROCESSES:
            raise ValueError(f"{c.name}: print process {pp!r}; use one of {PR.PRINT_PROCESSES}")
        f["process"] = pp
        return f
    return None


def _crosscheck_wanted(design, c) -> bool:
    return bool(((c.meta.get("dfm") or {}).get("prusaslicer_crosscheck")) or ((getattr(design, "manufacturing", None) or {}).get("prusaslicer_crosscheck")))


def check_part(r, design, c, row: dict, sm, frame, cyls, holes) -> dict | None:
    feat = features(design, c, row, sm, frame, cyls, holes)
    if feat is None:
        return None
    proc = feat["process"]
    shop = PR.shop_for(c, design, proc)
    verdicts = PR.judge(feat)
    mine = verdicts.get(shop) or {"results": [], "summary": PR.summarise([]), "missing": [], "verdict": "no published rules for this process and material"}
    sname = PR.name_of(shop)
    for res in mine["results"]:
        rule = res["rule"]
        if res["status"] != "fail" or rule["severity"] == "info":
            continue
        unit = PR.unit_of(rule["rule"])
        cnt = f" ({res['count']} of {res['of']})" if (res.get("of") or 1) > 1 else ""
        src = rule["source_url"]
        msg = (f"{c.name}: {sname} rule {rule['id']}: {PR.KIND_TEXT.get(rule['rule'], rule['rule'])} {_fmt(res.get('measured'))}{unit}{cnt}, "
               f"limit {rule['comparison']} {_fmt(res.get('limit'))}{unit} ({rule['severity']}: the {'supplier' if shop != 'own_printer' else 'source'}'s "
               f"words: \"{rule['quote'][:160]}\").")
        r.add(rule["severity"], "supplier_process_rule", msg, part=c.name, supplier=shop, process=proc, rule=rule["id"], rule_kind=rule["rule"],
              value=res.get("measured"), limit=res.get("limit"), comparison=rule["comparison"], count=res.get("count"), at=res.get("at") or None,
              source=src, quote=rule["quote"], retrieved=rule["retrieved"], material=feat["material"], detail=res.get("detail"), note=rule.get("note"))
    gaps = sorted({x["rule"]["rule"] for x in mine["results"] if x["status"] == "not_evaluated"})
    other = {}
    if proc in PR.PRINT_PROCESSES:
        for pp in PR.PRINT_PROCESSES:
            if pp == proc:
                continue
            alt = PR.judge(dict(feat, process=pp))
            other[pp] = {s: v["verdict"] for s, v in alt.items()}
    summary = {"assigned": shop, "process": proc, "verdict": mine["verdict"], "summary": mine["summary"], "no_published_rule": mine["missing"],
               "not_evaluated": gaps, "by_supplier": {s: v["verdict"] for s, v in verdicts.items()}}
    if other:
        summary["other_print_processes"] = other
    feat_small = _feature_digest(feat)
    summary["features"] = feat_small
    if proc in PR.PRINT_PROCESSES and _crosscheck_wanted(design, c):
        summary["prusaslicer"] = _crosscheck(r, c, feat, mine)
    row["supplier_process_rules"] = summary
    passing = sorted(PR.name_of(s) for s, v in verdicts.items() if v["summary"]["errors"] == 0 and any(x["status"] in ("pass", "fail") for x in v["results"]))
    r.add("info", "supplier_process_rules_summary",
          f"{c.name} ({feat['material']}, {proc}): assigned {sname}: {mine['verdict']}. Passes the published {proc} rules of: {', '.join(passing) or 'none'}.",
          part=c.name, supplier=shop, process=proc,
          by_supplier={s: {"verdict": v["verdict"], **v["summary"], "no_published_rule": v["missing"],
                           "failed": sorted(x["rule"]["id"] for x in v["results"] if x["status"] == "fail" and x["rule"]["severity"] != "info")}
                       for s, v in verdicts.items()},
          other_print_processes=other or None, not_evaluated=gaps, features=feat_small)
    return summary


def _feature_digest(feat: dict) -> dict:
    if feat["process"] == "cnc_milling":
        a = feat.get("access") or {}
        vc = [x for x in feat.get("corners") or [] if x.get("approach")]
        return {"extents_mm": feat.get("extents_mm"), "setups": a.get("setups"), "setup_dirs": a.get("setup_dirs"),
                "inaccessible_faces": len(a.get("inaccessible") or []), "sharp_vertical_corners": sum(1 for x in vc if x["radius"] <= 0),
                "smallest_corner_radius_mm": min((x["radius"] for x in vc), default=None),
                "deepest_pocket": max(feat.get("pockets") or [{}], key=lambda p: p.get("depth", 0)) or None,
                "narrowest_slot_mm": min((s["width"] for s in feat.get("slots") or []), default=None), "min_wall_mm": feat.get("min_wall_mm"),
                "holes": len(feat.get("holes") or []), "threads": [{k: t.get(k) for k in ("d", "depth", "hole", "plain_below_mm", "from")} for t in feat.get("threads") or []]}
    bins = feat.get("overhang_bins") or {}
    return {"extents_mm": feat.get("extents_mm"), "up": feat.get("up"), "min_wall_mm": feat.get("min_wall_mm"),
            "unsupported_walls_min_mm": min((w["t"] for w in feat.get("thin_walls") or [] if not w["supported"]), default=None),
            "overhang_over_45_mm2": round(sum(a for b, a in bins.items() if int(b) + 1 > 45), 1),
            "flat_overhangs": [{k: f.get(k) for k in ("kind", "length_mm", "span_mm", "area_mm2", "at")} for f in feat.get("flat_overhangs") or []][:8],
            "pins_mm": sorted(p["d"] for p in feat.get("pins") or [])[:8], "holes_mm": sorted(h["d"] for h in feat.get("holes") or [])[:8],
            "enclosed_voids": feat.get("enclosed_voids"), "threads": len(feat.get("threads") or [])}


def _crosscheck(r, c, feat: dict, mine: dict) -> dict:
    ps = FE.prusaslicer_support(c, feat["up"], nozzle=feat["settings"]["nozzle_mm"], layer=feat["settings"]["layer_height_mm"])
    if ps is None:
        return {"ran": False, "why": "prusa-slicer is not installed"}
    if not ps.get("ok"):
        r.add("warning", "supplier_process_prusaslicer_failed", f"{c.name}: the PrusaSlicer cross-check did not slice: {ps.get('error')}", part=c.name)
        return {"ran": False, "why": ps.get("error")}
    ours = any(x["status"] == "fail" and x["rule"]["rule"] in ("p3d_overhang_max_deg", "p3d_overhang_length_max") for x in mine["results"])
    slicer = ps["support_mm"] > 1.0
    agree = ours == slicer
    r.add("info" if agree else "warning", "supplier_process_prusaslicer_crosscheck",
          f"{c.name}: PrusaSlicer (support auto) lays {ps['support_mm']:.0f} mm of filament as support in the print orientation; the overhang rules "
          f"{'also say' if ours else 'say no'} support is needed: {'they agree' if agree else 'they DISAGREE (look at the part in the slicer)'}.",
          part=c.name, prusaslicer=ps, rules_need_support=ours, slicer_needs_support=slicer, agree=agree)
    return dict(ps, ran=True, rules_need_support=ours, agree=agree)
