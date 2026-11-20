"""Part resolution: BOM line (catalogue SKU) -> the orderable maker part(s).

Where the answer comes from, in this order (the first that names a maker part wins; `source` says which):
1. mechloop/data/real_parts.json (the DG-07 record, practice rule DG-07, mechloop/verifiers/purchased.py);
2. mechloop/data/sourcing/mpn_map.json (seeded from docs/PROVENANCE_AUDIT.md "Real-part replacements" and docs/V12_PLAN.md);
3. a catalogue house's own number recorded in the catalogue (McMaster confirmed number, MISUMI / Accu part);
4. the catalogue's maker and maker part number (vendor record or electrical product), tried at the distributors as given;
5. otherwise a placeholder: no maker part number anywhere.

For DG-07: `resolve_sku(sku, component=None)` gives the verdict for one SKU and `is_placeholder(sku, component)` the yes/no;
`dg07_records()` returns {sku: real_part record} in mechloop/data/real_parts.json's schema for every SKU the map pins (sellers
filled from the sourcing cache where a distributor has been seen to list it). The DG-07 check can merge these with its own
records; nothing here reports findings itself.
"""
from __future__ import annotations

import functools
import json
import re

from .config import DATA

KIND_DISTRIBUTOR, KIND_HOUSE, KIND_MAKER, KIND_PLACEHOLDER = "distributor", "catalogue_house", "maker_direct", "placeholder"
HOUSES = {"mcmaster": "McMaster-Carr", "mcmaster-carr": "McMaster-Carr", "misumi": "MISUMI", "accu": "Accu"}
NOT_A_MAKER = ("any", "commodity", "generic", "typical", "not specified", "unknown", "class", "")


@functools.lru_cache(maxsize=1)
def mpn_map() -> dict:
    return json.loads((DATA / "mpn_map.json").read_text(encoding="utf-8"))["parts"]


def _real_parts() -> dict:
    try:
        from ..verifiers.purchased import records

        return records()
    except Exception:
        try:
            return json.loads((DATA.parent / "real_parts.json").read_text(encoding="utf-8")).get("parts") or {}
        except (OSError, ValueError):
            return {}


def _real_maker(m) -> bool:
    s = str(m or "").strip().lower()
    return bool(s) and not s.startswith(NOT_A_MAKER[:-1]) and "commodity" not in s and "generic" not in s


def base_sku(sku: str) -> str:
    """BOM keys carry notes after the SKU ("DRIVER-BTT-TMC2209 (Octopus: ...)", "GT2-20T-B5 [9 mm belt]")."""
    return re.split(r"\s+[\(\[]", str(sku).strip(), maxsplit=1)[0]


def _item(maker, mpn, qty_per=1, unit="each", match="exact", note=""):
    return {"maker": maker, "mpn": mpn, "qty_per": qty_per, "unit": unit, "match": match, "note": note}


def resolve_sku(sku: str, component=None, line: dict | None = None) -> dict:
    """Resolution of one SKU. `component` (a placed catalogue part) or `line` (a BOM row: maker, maker_part_number,
    mcmaster_number, mcmaster_status) supplies the catalogue's own facts.

    Returns {"sku", "kind", "items": [{maker, mpn, qty_per, unit, match, note}], "seller", "source", "note", "design_change",
    "alternates", "placeholder", "replace_with"}."""
    b = base_sku(sku)
    out = {"sku": sku, "kind": KIND_PLACEHOLDER, "items": [], "seller": "", "source": "", "note": "", "design_change": False,
           "alternates": [], "placeholder": True, "replace_with": ""}
    # 1. DG-07 record
    rp = dict(_real_parts().get(b) or {})
    if component is not None:
        rp.update(component.meta.get("real_part") or {})
    if rp.get("maker") and rp.get("mpn") and _real_maker(rp["maker"]):
        sellers = [s if isinstance(s, dict) else {"name": str(s)} for s in rp.get("sellers") or []]
        names = " ".join(s.get("name", "") for s in sellers).lower()
        house = next((v for k, v in HOUSES.items() if k in names), None)
        kind = KIND_DISTRIBUTOR if any(d in names for d in ("digi", "mouser", "newark", "farnell", "element14")) else \
            KIND_HOUSE if house else KIND_MAKER if rp.get("sold_by_maker") else KIND_DISTRIBUTOR
        out.update(kind=kind, items=[_item(rp["maker"], rp["mpn"])], seller=house or (sellers[0].get("name") if sellers else ""),
                   source="mechloop/data/real_parts.json", placeholder=False)
        return out
    # 2. mapping file
    m = mpn_map().get(b) or mpn_map().get(sku)
    if m and m.get("kind") == KIND_PLACEHOLDER:
        out.update(source="mechloop/data/sourcing/mpn_map.json: " + m.get("source", ""), replace_with=m.get("replace_with", ""))
        return out
    if m:
        items = [_item(i["maker"], i["mpn"], i.get("qty_per", 1), i.get("unit", "each"), i.get("match", "exact"), i.get("note", ""))
                 for i in m["items"]]
        out.update(kind=m.get("kind", KIND_DISTRIBUTOR), items=items, source="mechloop/data/sourcing/mpn_map.json: " + m.get("source", ""),
                   note=m.get("note", ""), design_change=bool(m.get("design_change")), alternates=m.get("alternates", []), placeholder=False)
        return out
    # 3/4. catalogue
    maker, pn, mc, mcs = None, None, None, ""
    if component is not None:
        try:
            from ..verifiers.purchased import maker_of

            maker, pn = maker_of(component)
        except Exception:
            src = component.meta.get("source") or {}
            maker, pn = src.get("vendor"), src.get("part")
        mc, mcs = component.ratings.get("mcmaster_pn"), str(component.ratings.get("mcmaster_pn_status") or "")
        for k in ("supplier_part", "maker_part"):
            v = component.ratings.get(k)
            if isinstance(v, str) and v.split() and v.split()[0].lower() in HOUSES:
                maker, pn = HOUSES[v.split()[0].lower()], v
    elif line:
        maker, pn = line.get("maker"), line.get("maker_part_number") or line.get("maker_pn")
        mc, mcs = line.get("mcmaster_number") or line.get("mcmaster"), str(line.get("mcmaster_status") or "")
    if mc and mcs.startswith("confirmed"):
        out.update(kind=KIND_HOUSE, items=[_item("McMaster-Carr", str(mc))], seller="McMaster-Carr", placeholder=False,
                   source=f"catalogue: McMaster number {mc} ({mcs[:60]})")
        return out
    first = str(pn or "").split()[0].lower() if pn and str(pn).split() else ""
    if first in HOUSES or str(maker or "").strip().lower() in HOUSES:
        house = HOUSES.get(first) or HOUSES[str(maker).strip().lower()]
        num = " ".join(str(pn).split()[1:]) if first in HOUSES else str(pn)
        out.update(kind=KIND_HOUSE, items=[_item(house, num)], seller=house, placeholder=False, source="catalogue: catalogue house's own number")
        return out
    if _real_maker(maker) and pn and str(pn).strip().lower() not in ("not specified",) and not str(pn).startswith(("ISO ", "DIN ")):
        out.update(kind=KIND_DISTRIBUTOR, items=[_item(maker, str(pn))], placeholder=False,
                   source="catalogue: maker and part number of the vendor / electrical record (tried at the distributors as given)")
        return out
    out["source"] = "no maker part number in real_parts.json, mpn_map.json or the catalogue"
    return out


def is_placeholder(sku: str, component=None, line: dict | None = None) -> bool:
    """True when no orderable maker part is known for the SKU (for DG-07)."""
    return resolve_sku(sku, component, line)["placeholder"]


def dg07_records(cache=None) -> dict:
    """{sku: real_part record} for every SKU mpn_map.json pins to one orderable item (real_parts.json schema). Sellers come
    from the sourcing cache: a distributor that listed the MPN with stock or a price. Offline: reads the cache only."""
    from .cache import Cache

    cache = cache or Cache()
    out = {}
    for sku, m in mpn_map().items():
        if len(m["items"]) != 1:
            continue
        it = m["items"][0]
        sellers = []
        for dist in ("Digi-Key", "Mouser", "Newark", "Farnell"):
            rec = cache.get(dist, it["mpn"], it.get("match", "exact"), offline=True)
            for o in (rec or {}).get("offers", [])[:1]:
                sellers.append({"name": dist, "part_number": o.distributor_pn, "url": o.product_url, "checked": (rec["retrieved_at"] or "")[:10]})
        out[sku] = {"maker": it["maker"], "mpn": it["mpn"], "sellers": sellers, "sold_by_maker": m.get("kind") == KIND_MAKER,
                    "source": m.get("source", ""), "design_change": bool(m.get("design_change"))}
    return out
