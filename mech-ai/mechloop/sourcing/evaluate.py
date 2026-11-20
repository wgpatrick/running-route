"""Per BOM line and build quantity: best in-stock offer, alternatives, stock coverage, lead time and flags.

Best offer = the lowest total cost (USD; other currencies converted at config `fx_to_usd`, marked) for at least the needed
quantity, respecting MOQ, order multiple and price breaks (buying up to a cheaper break is allowed), among offers that hold
the whole quantity in stock; offers in the home currency first (config `prefer_home_currency`: Farnell only when no USD
distributor holds it). If none does, the cheapest priced offer is shown with the factory lead time and `out_of_stock`.

Flags: out_of_stock, low_stock (best offer's stock < low_stock_factor x needed), single_source (one distributor holds the
needed quantity; Newark + Farnell count as one), long_lead (lead > long_lead_business_days), not_active (NRND / obsolete),
no_distributor (catalogue house or maker-direct: price and lead time from the catalogue / config, not API-verified),
not_found (an MPN no distributor lists), placeholder (no MPN: DG-07), design_change (the orderable part differs from the
drawn one), lead_unknown, price_converted.
"""
from __future__ import annotations

import math

from .config import config, fx
from .offers import Offer, best_order
from .resolve import KIND_DISTRIBUTOR, KIND_HOUSE, KIND_MAKER, resolve_sku

E14 = ("Newark", "Farnell")


def _group(dist: str) -> str:
    return "element14" if dist in E14 else dist


def lead_business_days(o: Offer, in_stock: bool, cfg: dict) -> tuple[int | None, str]:
    if in_stock:
        return int(cfg["in_stock_ship_business_days"]), "in stock: " + cfg.get("in_stock_ship_note", "distributor shipping estimate")
    if o.factory_lead_weeks:
        return int(math.ceil(o.factory_lead_weeks * 5)) + int(cfg["in_stock_ship_business_days"]), \
            f"not in stock: factory lead {o.lead_time_text or str(o.factory_lead_weeks) + ' weeks'} + shipping"
    return None, "not in stock and no factory lead time given"


def _priced(o: Offer, need: int, cfg: dict) -> dict | None:
    bo = best_order(o, need)
    if bo is None:
        return None
    rate = fx(o.currency, cfg)
    if rate is None:
        return None
    return {**bo, "total_usd": round(bo["total"] * rate, 4), "unit_usd": round(bo["unit_price"] * rate, 6), "converted": o.currency != "USD"}


def offer_row(o: Offer, need: int, cfg: dict) -> dict | None:
    p = _priced(o, need, cfg)
    if p is None:
        return None
    ins = o.stock >= need
    lead, why = lead_business_days(o, ins, cfg)
    return {"distributor": o.distributor, "distributor_pn": o.distributor_pn, "mpn": o.mpn, "maker": o.maker, "stock": o.stock,
            "moq": o.moq, "multiple": o.multiple, "packaging": o.packaging, "currency": o.currency, "order_qty": p["order_qty"],
            "unit_price": p["unit_price"], "total": p["total"], "total_usd": p["total_usd"], "unit_usd": p["unit_usd"],
            "price_converted": p["converted"], "in_stock": ins, "lead_business_days": lead, "lead_basis": why,
            "factory_lead_weeks": o.factory_lead_weeks, "lead_time_text": o.lead_time_text, "status": o.status, "status_text": o.status_text,
            "datasheet_url": o.datasheet_url, "media": o.media, "product_url": o.product_url, "retrieved_at": o.retrieved_at,
            "price_breaks": o.price_breaks, "marketplace": o.marketplace}


def evaluate_item(item: dict, need: int, finder, cfg: dict) -> dict:
    """One orderable item (maker + MPN) at `need` units."""
    found = finder.find(item["mpn"], item.get("maker"), item.get("match", "exact"))
    offers = [o for r in found.values() for o in r["offers"]]
    rows = [r for r in (offer_row(o, need, cfg) for o in offers) if r is not None]
    rows = [r for r in rows if not r["marketplace"]] or rows
    home = cfg.get("currency", "USD")
    pref = (lambda r: r["currency"] != home) if cfg.get("prefer_home_currency", True) else (lambda r: False)
    instock = sorted([r for r in rows if r["in_stock"]], key=lambda r: (pref(r), r["total_usd"], -r["stock"]))
    # nothing holds the quantity: the cheapest order (a backorder), preferring one whose factory lead is known
    best = instock[0] if instock else (sorted(rows, key=lambda r: (pref(r), r["total_usd"], r["lead_business_days"] is None))[0] if rows else None)
    flags = []
    status = {d: r["status"] for d, r in found.items()}
    if not offers:
        flags.append("not_found" if any(s in ("not_found",) for s in status.values()) else "not_cached" if all(
            s == "not_cached" for s in status.values()) else "lookup_error")
    elif not instock:
        flags.append("out_of_stock")
    if best:
        if best["in_stock"] and best["stock"] < cfg["low_stock_factor"] * need:
            flags.append("low_stock")
        if best["status"] in ("nrnd", "obsolete"):
            flags.append("not_active")
        if best["lead_business_days"] is None:
            flags.append("lead_unknown")
        elif best["lead_business_days"] > cfg["long_lead_business_days"]:
            flags.append("long_lead")
        if best["price_converted"]:
            flags.append("price_converted")
        if best["order_qty"] > cfg.get("moq_excess_factor", 10) * need and best["order_qty"] - need > 50:
            flags.append("moq_excess")
    groups = {_group(r["distributor"]) for r in instock}
    if len(groups) == 1:
        flags.append("single_source")
    stock_total = sum(max((r["stock"] for r in rows if _group(r["distributor"]) == g), default=0) for g in {_group(r["distributor"]) for r in rows})
    datasheet = next((r["datasheet_url"] for r in ([best] if best else []) + rows if r and r["datasheet_url"]), "")
    cad = []
    for r in rows:
        for m in r["media"] or []:
            if "cad" in m["type"].lower() and m not in cad:
                cad.append(m)
    alts = [r for r in sorted(rows, key=lambda r: (not r["in_stock"], r["total_usd"])) if r is not best][:6]
    return {"maker": item.get("maker"), "mpn": item["mpn"], "qty_per": item.get("qty_per", 1), "unit": item.get("unit", "each"),
            "need": need, "best": best, "alternatives": alts, "n_offers": len(rows),
            "distributors_listing": sorted({r["distributor"] for r in rows}), "distributors_in_stock": sorted({r["distributor"] for r in instock}),
            "lookup": {d: {k: r.get(k) for k in ("status", "retrieved_at", "stale", "cached", "error")} for d, r in found.items()},
            "stock_coverage": round((best["stock"] / need), 2) if best and need else None,
            "stock_coverage_all": round(stock_total / need, 2) if need else None,
            "datasheet_url": datasheet, "cad_links": cad, "flags": flags}


def evaluate_line(line: dict, finder, cfg: dict | None = None, builds: int | None = None, component=None) -> dict:
    """line: {sku, qty, unit_cost_usd, description, category, maker, maker_part_number, mcmaster_number, mcmaster_status,
    items? (a list line gives its own items), kind?}."""
    cfg = cfg or config()
    builds = builds or cfg["build_quantity"]
    qty = float(line["qty"]) * builds
    if line.get("items"):
        res = {"sku": line["sku"], "kind": line.get("kind", KIND_DISTRIBUTOR), "items": [
            {"maker": i["maker"], "mpn": i["mpn"], "qty_per": i.get("qty_per", 1), "unit": i.get("unit", "each"), "match": i.get("match", "exact"),
             "note": i.get("note", "")} for i in line["items"]], "seller": line.get("seller", ""), "source": line.get("source", ""),
               "note": line.get("note", ""), "design_change": False, "alternates": [], "placeholder": False, "replace_with": ""}
    else:
        res = resolve_sku(line["sku"], component=component, line=line)
    old_unit = line.get("unit_cost_usd")
    old = None if old_unit in (None, "") else round(float(old_unit) * qty, 2)
    out = {"sku": line["sku"], "category": line.get("category", ""), "description": line.get("description", ""), "qty": qty,
           "resolution": {k: res[k] for k in ("kind", "source", "note", "seller", "design_change", "alternates", "replace_with")},
           "items": [], "old_estimate_usd": old, "cost_usd": None, "lead_business_days": None, "lead_basis": "", "flags": [],
           "api_verified": False, "members": line.get("members", [])}
    flags = set()
    if res["placeholder"]:
        flags.add("placeholder")
        hd = cfg["no_distributor_houses"]["unknown"]
        out.update(cost_usd=old, lead_business_days=hd["business_days"], lead_basis=hd["basis"])
        out["flags"] = sorted(flags)
        return out
    if res["design_change"]:
        flags.add("design_change")
    if res["kind"] in (KIND_HOUSE, KIND_MAKER):
        house = res["seller"] if res["kind"] == KIND_HOUSE else "maker-direct"
        hd = cfg["no_distributor_houses"].get(house) or cfg["no_distributor_houses"]["maker-direct"]
        flags.add("no_distributor")
        out["items"] = [{"maker": i["maker"], "mpn": i["mpn"], "seller": res["seller"] or i["maker"], "need": int(math.ceil(qty * i["qty_per"]))}
                        for i in res["items"]]
        out.update(cost_usd=old, lead_business_days=hd["business_days"], lead_basis=hd["basis"])
        out["flags"] = sorted(flags)
        return out
    total, leads, missing, excess = 0.0, [], 0, 0
    for it in res["items"]:
        need = max(1, int(math.ceil(qty * float(it.get("qty_per", 1)) - 1e-9)))
        ev = evaluate_item(it, need, finder, cfg)
        ev["note"] = it.get("note", "")
        out["items"].append(ev)
        flags |= set(ev["flags"])
        if ev["best"] and "moq_excess" not in ev["flags"]:
            total += ev["best"]["total_usd"]
            leads.append((ev["best"]["lead_business_days"], ev["best"]["lead_basis"], it["mpn"]))
        elif ev["best"]:
            excess += 1             # only sold in a quantity far above the need (a reel of an obsolete part): not counted
            leads.append((ev["best"]["lead_business_days"], ev["best"]["lead_basis"], it["mpn"]))
        else:
            missing += 1
    if out["items"] and not missing and not excess:
        out["cost_usd"] = round(total, 2)
        out["api_verified"] = True
    else:
        n_ok = len(out["items"]) - missing - excess
        out["cost_usd"] = round(total, 2) if n_ok and old is None else old
        if missing:
            # some item not found at any distributor: catalogue price stands, the line counts as not API-verified
            flags.add("no_distributor")
            hd = cfg["no_distributor_houses"]["maker-direct"]
            leads.append((hd["business_days"], "not found at any distributor: " + hd["basis"], "-"))
    alts = list(res.get("alternates") or []) + list(line.get("alternates") or [])
    if alts and flags & {"out_of_stock", "not_active", "not_found", "moq_excess", "no_distributor"}:
        out["alternate_parts"] = []
        for a in alts:
            need = max(1, int(math.ceil(qty * float(a.get("qty_per", 1)) - 1e-9)))
            ev = evaluate_item({"maker": a.get("maker"), "mpn": a["mpn"], "match": a.get("match", "exact")}, need, finder, cfg)
            b = ev["best"] or {}
            out["alternate_parts"].append({"maker": a.get("maker"), "mpn": a["mpn"], "note": a.get("note", ""), "distributor": b.get("distributor"),
                                           "distributor_pn": b.get("distributor_pn"), "stock": b.get("stock"), "total_usd": b.get("total_usd"),
                                           "lead_business_days": b.get("lead_business_days"), "flags": ev["flags"]})
    known = [x for x in leads if x[0] is not None]
    if known:
        lb = max(known, key=lambda x: x[0])
        out["lead_business_days"], out["lead_basis"] = lb[0], (f"{lb[2]}: " if len(res["items"]) > 1 else "") + lb[1]
    out["flags"] = sorted(flags)
    return out
