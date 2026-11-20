"""Sourcing report per design (or per orderable list): JSON + markdown, with the Build 1 schedule.

Inputs, any of:
- a design file: its purchased parts grouped by SKU (with the part names, for the schedule), BOM-only lines, fabricated
  parts with process / form / shop and the verify report's estimates, and its sub-assemblies. Loading a design takes about
  a minute, so the extract is cached as out/sourcing/<name>/design_snapshot.json keyed by the design file's md5;
- a build package BOM (docs/build/<name>/bom.csv): purchased lines only (no part names, so no sub-assembly schedule);
- an orderable list (mechloop/data/sourcing/v12_electronics.json).

Outputs: out/sourcing/<name>/sourcing.json, SOURCING.md, schedule.json, SCHEDULE.md (out/ is gitignored).
"""
from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import json
from collections import Counter
from pathlib import Path

from .config import OUT_DIR, ROOT, config
from .evaluate import evaluate_line
from .fab import fabricated_lines
from .schedule import next_business_day, schedule

FLAG_ORDER = ("placeholder", "out_of_stock", "not_found", "not_active", "moq_excess", "long_lead", "single_source", "low_stock", "no_distributor",
              "design_change", "lead_unknown", "price_converted", "lookup_error", "not_cached")


# ------------------------------------------------------------------------------------------------ inputs
def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def snapshot_design(design_path, report_root=None, refresh: bool = False) -> dict:
    design_path = Path(design_path).resolve()
    md5 = _md5(design_path)
    name_guess = design_path.stem
    snap = OUT_DIR / name_guess / "design_snapshot.json"
    if snap.exists() and not refresh:
        s = json.loads(snap.read_text())
        if s.get("design_md5") == md5:
            return s
    from ..runner import load_design
    from ..verifiers import purchased as P

    d = load_design(design_path)
    rep_path = Path(report_root or ROOT / "out") / d.name / "report.json"
    manu = {}
    if rep_path.exists():
        manu = (json.loads(rep_path.read_text()).get("metrics") or {}).get("manufacture", {}).get("parts", {}) or {}
    lines = {}
    fab = []
    for c in d.components:
        if P.is_purchased(c):
            sku = c.sku or c.name
            L = lines.get(sku)
            if L is None:
                maker, pn = P.maker_of(c)
                sellers = P.sellers_of(c)
                house = next((s for s in sellers if s.get("catalogue")), None)
                L = lines[sku] = {"sku": sku, "qty": 0, "members": [], "description": c.meta.get("description", ""),
                                  "unit_cost_usd": c.meta.get("cost_usd"), "maker": maker or "", "maker_part_number": pn or "",
                                  "mcmaster_number": c.ratings.get("mcmaster_pn") or "", "mcmaster_status": str(c.ratings.get("mcmaster_pn_status") or ""),
                                  "category": "", "real_part": c.meta.get("real_part") or None}
                if house and house["name"] != "McMaster-Carr":
                    L["maker"], L["maker_part_number"] = house["name"], f"{house['name']} {house.get('part_number', '')}"
            L["qty"] += 1
            L["members"].append(c.name)
        elif P.is_fabricated(c):
            mp = manu.get(c.name) or {}
            est = mp.get("estimate") or {}
            val = est.get("cost_usd_each_qty1")
            if val is None and (est.get("cut_usd") is not None or est.get("material_usd") is not None):
                val = (est.get("cut_usd") or 0.0) + (est.get("material_usd") or 0.0)
            proc = mp.get("process") or P._process(c)
            fab.append({"name": c.name, "process": proc, "form": mp.get("form") or ("flat" if proc == "sheet" else ""),
                        "shop": mp.get("shop") or (c.meta.get("dfm") or {}).get("shop") or (d.manufacturing.get("shop") if proc in ("sheet",) else None),
                        "estimate_usd": None if val is None else round(float(val), 2), "estimate_basis": est.get("basis", "")})
    for sku, e in (d.bom_extras or {}).items():
        L = lines.setdefault(sku, {"sku": sku, "qty": 0, "members": [], "description": e.get("description", ""), "unit_cost_usd": e.get("unit_cost_usd"),
                                   "maker": e.get("maker", ""), "maker_part_number": e.get("mpn") or e.get("maker_part_number") or "",
                                   "mcmaster_number": e.get("mcmaster_pn") or "", "mcmaster_status": str(e.get("mcmaster_pn_status") or ""),
                                   "category": "BOM only", "real_part": e.get("real_part")})
        L["qty"] += e.get("qty", 0)
    s = {"design": d.name, "design_file": str(design_path.relative_to(ROOT)) if design_path.is_relative_to(ROOT) else str(design_path),
         "design_md5": md5, "report": str(rep_path.relative_to(ROOT)) if rep_path.exists() else None,
         "lines": list(lines.values()), "fabricated": fab, "subassemblies": {k: list(v) for k, v in d.subassemblies.items()},
         "made": _dt.datetime.now().isoformat(timespec="seconds")}
    snap = OUT_DIR / d.name / "design_snapshot.json"
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps(s, indent=1, default=str))
    return s


def lines_from_bom_csv(path) -> dict:
    rows = list(csv.DictReader(open(path, newline="")))
    lines = [{"sku": r["sku"], "qty": float(r["qty"]), "description": r.get("description", ""), "category": r.get("category", ""),
              "unit_cost_usd": float(r["unit_cost_usd"]) if r.get("unit_cost_usd") not in (None, "") else None,
              "maker": r.get("maker", ""), "maker_part_number": r.get("maker_part_number", ""), "mcmaster_number": r.get("mcmaster_number", ""),
              "mcmaster_status": r.get("mcmaster_status", ""), "members": (r.get("used_as") or "").split()} for r in rows]
    return {"design": Path(path).parent.name, "source": str(path), "lines": lines, "fabricated": [], "subassemblies": {}}


def lines_from_list(path) -> dict:
    d = json.loads(Path(path).read_text())
    return {"design": d.get("name") or Path(path).stem, "source": str(path), "lines": d["lines"], "fabricated": [], "subassemblies": {},
            "build_quantity": d.get("build_quantity")}


# ------------------------------------------------------------------------------------------------ run
def run(data: dict, finder, cfg: dict | None = None, builds: int | None = None, order_date: _dt.date | None = None,
        only=None, print_service: str | None = None, print_option: str | None = None, log=None) -> dict:
    """data: from snapshot_design / lines_from_bom_csv / lines_from_list. `only(line) -> bool` limits the purchased lines."""
    cfg = cfg or config()
    builds = builds or data.get("build_quantity") or cfg["build_quantity"]
    order_date = order_date or next_business_day(_dt.date.today())
    log = log or (lambda s: None)
    lines = []
    for L in data["lines"]:
        if only and not only(L):
            continue
        r = evaluate_line(L, finder, cfg, builds)
        lines.append(r)
        log(f"{L['sku']}: {r['cost_usd']} {','.join(r['flags'])}")
    fab = fabricated_lines(data.get("fabricated") or [], print_service=print_service, print_option=print_option)
    sched = schedule(order_date, [{"sku": r["sku"], "lead_business_days": r["lead_business_days"], "members": r["members"], "flags": r["flags"]}
                                  for r in lines],
                     [{"name": p["name"], "shop": p["shop"], "lead_business_days": p["lead_business_days"], "flags": p["flags"]} for p in fab["parts"]],
                     data.get("subassemblies") or {}, cfg)
    flags = Counter(f for r in lines for f in r["flags"])
    cost = round(sum(r["cost_usd"] or 0.0 for r in lines), 2)
    old = round(sum(r["old_estimate_usd"] or 0.0 for r in lines), 2)
    verified = [r for r in lines if r["api_verified"]]
    fab_cost = round(sum(g["order_usd"] for g in fab["by_shop"].values()), 2)
    summary = {
        "design": data["design"], "source": data.get("design_file") or data.get("source"), "build_quantity": builds,
        "order_date": order_date.isoformat(), "lines": len(lines),
        "purchased_cost_usd": cost, "purchased_old_estimate_usd": old,
        "api_verified": {"lines": len(verified), "cost_usd": round(sum(r["cost_usd"] or 0 for r in verified), 2),
                         "old_estimate_usd": round(sum(r["old_estimate_usd"] or 0 for r in verified), 2)},
        "not_api_verified_cost_usd": round(sum(r["cost_usd"] or 0 for r in lines if not r["api_verified"]), 2),
        "fabricated_cost_usd": fab_cost, "total_cost_usd": round(cost + fab_cost, 2),
        "flags": {f: flags[f] for f in FLAG_ORDER if flags.get(f)},
        "longest_leads": [{"id": i["id"], "kind": i["kind"], "lead_business_days": i["lead_business_days"], "arrival": i["arrival"],
                           "basis": "planning default" if (i["lead_unknown"] or "no_distributor" in i["flags"]) else "distributor / shop figure"}
                          for i in sorted(sched["items"], key=lambda i: (-i["lead_business_days"], i["lead_unknown"]))[:12]],
        "lead_unknown_items": sum(1 for i in sched["items"] if i["lead_unknown"]),
        "critical_path": sched["critical_path"], "final_assembly": sched["final_assembly"],
        "lookups": dict(getattr(finder, "stats", {})), "offline": bool(getattr(finder, "offline", False)),
        "generated": _dt.datetime.now().isoformat(timespec="seconds"), "config": {k: cfg[k] for k in (
            "in_stock_ship_business_days", "low_stock_factor", "long_lead_business_days", "cache_ttl_hours", "fx_to_usd", "distributors")},
    }
    return {"summary": summary, "lines": lines, "fabricated": fab, "schedule": sched}


# ------------------------------------------------------------------------------------------------ outputs
def _m(x) -> str:
    return "-" if x is None else f"${x:,.2f}"


def _t(headers, rows) -> str:
    esc = lambda v: str(v).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def best_text(r: dict) -> dict:
    """One BOM line's sourcing cells (used by SOURCING.md and tools/build_package.py)."""
    bests = [i["best"] for i in r.get("items", []) if isinstance(i, dict) and i.get("best")]
    if r["resolution"]["kind"] in ("catalogue_house", "maker_direct") or not bests:
        seller = ", ".join(sorted({i.get("seller", "") for i in r.get("items", []) if isinstance(i, dict) and i.get("seller")})) or "-"
        return {"price": r["cost_usd"], "distributor": seller + (" (not API-verified)" if "no_distributor" in r["flags"] else ""),
                "distributor_pn": ", ".join(i.get("mpn", "") for i in r.get("items", []) if isinstance(i, dict)) or "-",
                "stock": "-", "lead": r["lead_business_days"], "flags": r["flags"]}
    return {"price": r["cost_usd"], "distributor": " + ".join(sorted({b["distributor"] for b in bests})),
            "distributor_pn": " + ".join(f"{b['distributor_pn']} x{b['order_qty']}" for b in bests),
            "stock": " / ".join(f"{b['stock']:,}" for b in bests), "lead": r["lead_business_days"], "flags": r["flags"]}


def markdown(rep: dict) -> tuple[str, str]:
    s, lines, fab, sch = rep["summary"], rep["lines"], rep["fabricated"], rep["schedule"]
    T = [f"# Sourcing: {s['design']}", "",
         f"Generated {s['generated']} by `python -m mechloop.sourcing` from `{s['source']}`; build quantity {s['build_quantity']}; "
         f"{'OFFLINE (cache only)' if s['offline'] else 'live distributor APIs with a ' + str(s['config']['cache_ttl_hours']) + ' h cache'} "
         f"(lookups: {s['lookups']}). Prices are distributor list prices at the needed quantity (MOQ, multiples and price breaks applied), "
         "shipping and tax excluded.", "",
         "## Summary", "",
         _t(["", "Value"], [
             ["purchased lines", s["lines"]],
             ["purchased cost at build quantity", f"{_m(s['purchased_cost_usd'])} (old estimate {_m(s['purchased_old_estimate_usd'])})"],
             ["of which priced live (API-verified)", f"{s['api_verified']['lines']} lines, {_m(s['api_verified']['cost_usd'])} (old estimate {_m(s['api_verified']['old_estimate_usd'])})"],
             ["of which catalogue price only (not API-verified: McMaster, MISUMI, maker-direct, placeholders)", _m(s["not_api_verified_cost_usd"])],
             ["fabricated parts (design estimates, per-order floors applied)", _m(s["fabricated_cost_usd"])],
             ["total", _m(s["total_cost_usd"])],
             ["flags", ", ".join(f"{k} {v}" for k, v in s["flags"].items()) or "none"],
             ["order date / final assembly can start", f"{s['order_date']} / {s['final_assembly']['earliest_start']} ({s['final_assembly']['business_days_from_order']} business days)"],
             ["critical path", "; ".join(" -> ".join(c["path"]) + f" (arrives {c['arrival']})" for c in s["critical_path"])],
         ]), "",
         "Flags: out_of_stock (no distributor holds the quantity), low_stock (best offer's stock < "
         f"{s['config']['low_stock_factor']} x needed), single_source (one distributor holds it; Newark + Farnell count as one), "
         f"long_lead (> {s['config']['long_lead_business_days']} business days), not_active (NRND / obsolete), no_distributor (price and lead "
         "from the catalogue / planning defaults, not API-verified), not_found (MPN listed nowhere), placeholder (no MPN: DG-07 error), "
         "design_change (the orderable part is not the one drawn), moq_excess (only sold in a quantity over 10 x the need: not counted in the "
         "cost, the catalogue estimate stands).", ""]
    T += ["## Longest leads", "", _t(["Item", "Kind", "Lead (business days)", "Basis", "Arrives"],
                                      [[x["id"], x["kind"], x["lead_business_days"], x["basis"], x["arrival"]] for x in s["longest_leads"]]), "",
          f"{s['lead_unknown_items']} item(s) have no lead time (placeholders): the schedule gives each the planning default.", ""]
    rows = []
    for r in sorted(lines, key=lambda r: (min([FLAG_ORDER.index(f) for f in r["flags"] if f in FLAG_ORDER] or [99]), r["sku"])):
        b = best_text(r)
        mp = "; ".join(f"{i.get('maker', '')} {i.get('mpn', '')}" for i in r["items"] if isinstance(i, dict)) or r["resolution"].get("replace_with") or "-"
        rows.append([f"`{r['sku']}`", f"{r['qty']:g}", mp[:80], b["distributor"], b["distributor_pn"][:60], b["stock"], _m(b["price"]), _m(r["old_estimate_usd"]),
                     "-" if b["lead"] is None else b["lead"], ", ".join(r["flags"]) or "ok"])
    T += ["## Purchased lines", "", _t(["SKU", "Qty", "Maker part", "Best offer", "Distributor PN x order qty", "Stock", "Cost", "Old est.",
                                       "Lead (bd)", "Flags"], rows), ""]
    alt = [[f"`{r['sku']}`", ", ".join(r["flags"]), f"{a['maker']} {a['mpn']}", a.get("distributor") or "-", a.get("distributor_pn") or "-",
            "-" if a.get("stock") is None else f"{a['stock']:,}", _m(a.get("total_usd")), ", ".join(a["flags"]) or "ok", a.get("note", "")]
           for r in lines for a in r.get("alternate_parts") or []]
    if alt:
        T += ["## Alternates for lines that cannot be bought as specified", "",
              _t(["SKU", "Why", "Alternate", "Best offer", "Distributor PN", "Stock", "Cost", "Flags", "Note"], alt), ""]
    det = []
    for r in lines:
        for i in r["items"]:
            if isinstance(i, dict) and i.get("best"):
                b = i["best"]
                alts = "; ".join(f"{a['distributor']} {_m(a['total_usd'])} ({a['stock']:,} in stock)" for a in i["alternatives"][:3])
                det.append([f"`{r['sku']}`", i["mpn"], i["need"], f"{b['distributor']} {b['distributor_pn']} ({b['packaging']})",
                            f"{b['order_qty']} @ {b['unit_price']:.4g} {b['currency']}", f"{i['stock_coverage']}x", b["status_text"] or b["status"],
                            b["lead_time_text"] or "-", "yes" if i["cad_links"] else "no", "yes" if i["datasheet_url"] else "no", alts or "-"])
    if det:
        T += ["## Offer detail", "", _t(["SKU", "MPN", "Need", "Best offer", "Order", "Coverage", "Status", "Factory lead (distributor)",
                                         "CAD link", "Datasheet", "Alternatives"], det), ""]
    if fab["parts"]:
        T += ["## Fabricated parts", "", _t(["Part", "Process", "Form", "Shop", "Lead (bd)", "Lead basis", "Estimate", "Flags"],
                                             [[p["name"], p["process"], p["form"], p["shop"], p["lead_business_days"], (p["lead_verbatim"] or p["lead_basis"])[:90],
                                               _m(p["price_usd"]), ", ".join(p["flags"]) or "ok"] for p in fab["parts"]]), "",
              _t(["Shop", "Parts", "Sum of estimates", "Order floor", "Order", "Longest lead (bd)"],
                 [[g["shop"], g["parts"], _m(g["estimate_usd"]), _m(g["order_floor_usd"]), _m(g["order_usd"]), g["lead_business_days"]]
                  for g in fab["by_shop"].values()]), "",
              "Fabricated prices are the design's own estimates (sheet: cut length and pierces only, no material or set-up; printed: filament "
              "only) unless a quote exists; the benchmark's observed quotes are in mechloop/data/sourcing/fab_services.json and the shop "
              "profiles' lead_time.price_reference (e.g. SendCutSend RP04 $15.01 at qty 1).", ""]
    S = [f"# Build 1 schedule: {s['design']}", "", f"Order date {sch['order_date']} (all parts ordered that day). Business days, weekends skipped, "
         f"no holidays; bench time per sub-assembly / final: {sch['assumptions']['assembly_business_days']}. Lines with no known lead use "
         f"{sch['assumptions']['unknown_lead_business_days']} business days.", "",
         f"**Final assembly can start {sch['final_assembly']['earliest_start']}** ({sch['final_assembly']['business_days_from_order']} business days after ordering). "
         "Critical path: " + "; ".join(" -> ".join(c["path"]) for c in sch["critical_path"]), ""]
    if sch["subassemblies"]:
        S += ["## Sub-assemblies", "", _t(["Sub-assembly", "Parts", "Earliest start", "Gated by", "Waits for"],
                                          [[x["name"], x["parts"], x["earliest_start"], f"{x['gated_by']} ({x['gate_kind']})", ", ".join(x["waits_for"])[:120]]
                                           for x in sch["subassemblies"]]), ""]
    S += ["## Arrivals", "", _t(["Item", "Kind", "Lead (bd)", "Arrives", "Flags"],
                               [[i["id"], i["kind"] + (f" ({i['shop']})" if i.get("shop") else ""), str(i["lead_business_days"]) + (" (unknown: default)" if i["lead_unknown"] else ""),
                                 i["arrival"], ", ".join(i["flags"])] for i in sch["items"]]), ""]
    return "\n".join(T), "\n".join(S)


def write(rep: dict, out_dir=None) -> Path:
    out = Path(out_dir or OUT_DIR / rep["summary"]["design"])
    out.mkdir(parents=True, exist_ok=True)
    md, smd = markdown(rep)
    (out / "sourcing.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "schedule.json").write_text(json.dumps(rep["schedule"], indent=1, default=str))
    (out / "SOURCING.md").write_text(md)
    (out / "SCHEDULE.md").write_text(smd)
    return out


def load_report(design_name: str, root=None) -> dict | None:
    """The last sourcing report written for a design (for tools/build_package.py), or None."""
    p = Path(root or OUT_DIR) / design_name / "sourcing.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except ValueError:
        return None


def bom_columns(design_name: str, root=None) -> dict:
    """{sku: {"price", "distributor", "distributor_pn", "stock", "lead", "flags", "retrieved"}} from the last report (empty if none)."""
    rep = load_report(design_name, root)
    if not rep:
        return {}
    out = {}
    for r in rep["lines"]:
        b = best_text(r)
        b["retrieved"] = rep["summary"].get("generated")
        b["api_verified"] = r.get("api_verified")
        out[r["sku"]] = b
    out["__summary__"] = rep["summary"]
    return out
