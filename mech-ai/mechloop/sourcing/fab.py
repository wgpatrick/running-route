"""Fabricated parts: lead time and price per assigned shop.

Lead time from the shop profile's `lead_time` (mechloop/shops/<shop>.json: SendCutSend, Xometry) or, for services with no
profile, mechloop/data/sourcing/fab_services.json; both are the owner's agent's benchmark quote pages of 2026-11-19. Price
stays the design's own estimate (report.json manufacture.parts[...].estimate) unless a quote exists; the benchmark's observed
quotes are attached as a reference. Printed parts go to a print service (owner decision 2026-11-20: no owner printer for
Build 1; default Craftcloud).
"""
from __future__ import annotations

import functools
import json

from .config import DATA


@functools.lru_cache(maxsize=1)
def services() -> dict:
    return json.loads((DATA / "fab_services.json").read_text(encoding="utf-8"))


def _profile_lead(shop: str) -> dict | None:
    try:
        from ..shops import profile

        p = profile(shop)
    except Exception:
        p = None
    return (p or {}).get("lead_time")


def default_shop(process: str) -> str | None:
    return services()["defaults"].get(process)


def lead_for(shop: str | None, process: str, form: str = "flat", option: str | None = None) -> dict:
    """{shop, business_days, basis, verbatim, source, estimated} for one fabricated part. `form` is flat / bent for sheet."""
    svc = services()["services"]
    shop = shop or default_shop(process)
    key = form if process == "sheet" else process
    prof = _profile_lead(shop) if shop else None
    if prof is not None:
        row = (prof.get("by_form") or {}).get(key)
        if row:
            return {"shop": shop, "business_days": row["business_days"], "delivered": True, "verbatim": row.get("verbatim", ""),
                    "basis": prof.get("basis", ""), "source": f"mechloop/shops/{shop}.json lead_time ({row.get('part', '')})", "estimated": False}
        # the profile has no figure for this process (Xometry): fall back to the named fallback service
        fb = services()["defaults"].get(f"{process}_fallback")
        if fb and fb != shop:
            r = lead_for(fb, process, form)
            r.update({"shop": shop, "estimated": True,
                      "basis": f"{shop}: {prof.get('basis') or 'no lead time recorded'}; planning figure from {fb}: {r['basis']}"})
            return r
    s = svc.get(shop or "")
    if s:
        if option and option in (s.get("lead_options") or {}):
            row = s["lead_options"][option]
        else:
            row = (s.get("lead") or {}).get(key)
        if row:
            days = row["business_days"]
            basis = "delivered" if row.get("delivered") else f"build {days} + shipping {s.get('shipping_business_days', 0)} ({s.get('shipping_basis', '')})"
            if not row.get("delivered"):
                days = days + int(s.get("shipping_business_days") or 0)
            return {"shop": shop, "business_days": days, "delivered": bool(row.get("delivered")), "verbatim": row.get("verbatim", ""),
                    "basis": basis, "source": f"mechloop/data/sourcing/fab_services.json ({row.get('part', '')})",
                    "estimated": not row.get("delivered")}
    return {"shop": shop, "business_days": None, "delivered": False, "verbatim": "", "basis": "no lead time recorded for this shop and process",
            "source": "", "estimated": True}


def order_floor(shop: str | None) -> tuple[float | None, str]:
    s = services()["services"].get(shop or "") or {}
    return s.get("order_floor_usd"), s.get("order_floor_basis", "")


def price_reference(shop: str | None):
    s = services()["services"].get(shop or "")
    if s:
        return s.get("price_reference")
    p = _profile_lead(shop) if shop else None
    return (p or {}).get("price_reference")


def fabricated_lines(parts: list[dict], print_service: str | None = None, print_option: str | None = None) -> dict:
    """parts: [{name, process, form, shop, estimate_usd, estimate_basis, subassembly}] -> {"parts": [...], "by_shop": {...}}."""
    rows, by_shop = [], {}
    for p in parts:
        proc = p.get("process") or "sheet"
        shop = p.get("shop") or (print_service if proc == "printed" and print_service else default_shop(proc))
        if proc == "printed" and print_service:
            shop = print_service
        ld = lead_for(shop, proc, p.get("form") or "flat", option=print_option if proc == "printed" else None)
        est = p.get("estimate_usd")
        row = {"name": p["name"], "process": proc, "form": p.get("form") or "", "shop": ld["shop"], "lead_business_days": ld["business_days"],
               "lead_basis": ld["basis"], "lead_verbatim": ld["verbatim"], "lead_source": ld["source"], "lead_estimated": ld["estimated"],
               "price_usd": est, "price_basis": p.get("estimate_basis") or ("no estimate in the report" if est is None else "design estimate"),
               "quote": None, "flags": []}
        if est is None:
            row["flags"].append("no_price")
        if ld["business_days"] is None:
            row["flags"].append("no_lead_time")
        if ld["estimated"]:
            row["flags"].append("lead_estimated")
        rows.append(row)
        g = by_shop.setdefault(ld["shop"], {"shop": ld["shop"], "parts": 0, "estimate_usd": 0.0, "lead_business_days": None})
        g["parts"] += 1
        g["estimate_usd"] += est or 0.0
        if ld["business_days"] is not None:
            g["lead_business_days"] = max(g["lead_business_days"] or 0, ld["business_days"])
    for shop, g in by_shop.items():
        floor, basis = order_floor(shop)
        g["estimate_usd"] = round(g["estimate_usd"], 2)
        g["order_floor_usd"], g["order_floor_basis"] = floor, basis
        g["order_usd"] = round(max(g["estimate_usd"], floor or 0.0), 2)
        g["price_reference"] = price_reference(shop)
    return {"parts": rows, "by_shop": by_shop}
