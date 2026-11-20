"""Build 1 schedule: order date -> each part's arrival -> each sub-assembly's earliest start -> final assembly and its critical path.

Sub-assembly membership is the design's own (`design.subassemblies`, the units the assembly planner moves as one,
mechloop/assembly/planner.py). A part outside every sub-assembly, and every BOM-only line (T-nuts, wire, connectors, belts:
no geometry), is needed at the final assembly. Bench time per sub-assembly and for the final assembly is config
`assembly_business_days` (0 = the schedule gives earliest starts only). Business days skip Saturday and Sunday; no holidays.
"""
from __future__ import annotations

import datetime as _dt


def add_business_days(d: _dt.date, n: int) -> _dt.date:
    while n > 0:
        d += _dt.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def next_business_day(d: _dt.date) -> _dt.date:
    d += _dt.timedelta(days=1)
    while d.weekday() >= 5:
        d += _dt.timedelta(days=1)
    return d


def schedule(order_date: _dt.date, purchased: list[dict], fabricated: list[dict], subassemblies: dict, cfg: dict | None = None) -> dict:
    """purchased: [{sku, lead_business_days, members: [part names], flags}]; fabricated: [{name, shop, lead_business_days}];
    subassemblies: {name: [part names]}."""
    from .config import config

    cfg = cfg or config()
    asm = cfg.get("assembly_business_days") or {}
    default_unknown = cfg["no_distributor_houses"]["unknown"]["business_days"]
    items = []                               # every orderable thing with its arrival
    part_item = {}                           # part name -> item index
    for L in purchased:
        lead = L.get("lead_business_days")
        unknown = lead is None
        lead = default_unknown if unknown else int(lead)
        items.append({"kind": "purchased", "id": L["sku"], "lead_business_days": lead, "lead_unknown": unknown,
                      "arrival": add_business_days(order_date, lead).isoformat(), "flags": L.get("flags", []), "members": L.get("members", [])})
        for m in L.get("members", []):
            part_item[m] = len(items) - 1
    for P in fabricated:
        lead = P.get("lead_business_days")
        unknown = lead is None
        lead = default_unknown if unknown else int(lead)
        items.append({"kind": "fabricated", "id": P["name"], "shop": P.get("shop"), "lead_business_days": lead, "lead_unknown": unknown,
                      "arrival": add_business_days(order_date, lead).isoformat(), "flags": P.get("flags", []), "members": [P["name"]]})
        part_item[P["name"]] = len(items) - 1
    in_sub = set()
    subs = []
    for name, parts in (subassemblies or {}).items():
        idx = sorted({part_item[p] for p in parts if p in part_item})
        in_sub |= set(parts)
        if idx:
            gate = max(idx, key=lambda i: (items[i]["arrival"], items[i]["lead_business_days"]))
            start = max(items[i]["arrival"] for i in idx)
        else:
            gate, start = None, order_date.isoformat()
        dur = int(asm.get("subassembly") or 0)
        done = add_business_days(_dt.date.fromisoformat(start), dur).isoformat()
        subs.append({"name": name, "parts": len(parts), "orderable_items": len(idx), "earliest_start": start, "ready": done,
                     "gated_by": items[gate]["id"] if gate is not None else None,
                     "gate_kind": items[gate]["kind"] if gate is not None else None,
                     "waits_for": sorted({items[i]["id"] for i in idx if items[i]["arrival"] == start})})
    # final assembly: every sub-assembly ready, every item arrived (parts outside sub-assemblies and BOM-only lines)
    cands = [(s["ready"], "subassembly", s["name"], s["gated_by"]) for s in subs]
    for i, it in enumerate(items):
        outside = not it["members"] or any(m not in in_sub for m in it["members"])
        if outside:
            cands.append((it["arrival"], it["kind"], it["id"], it["id"]))
    final_start = max(c[0] for c in cands) if cands else order_date.isoformat()
    gating = [c for c in cands if c[0] == final_start]
    final_ready = add_business_days(_dt.date.fromisoformat(final_start), int(asm.get("final") or 0)).isoformat()
    critical = []
    for c in gating:
        if c[1] == "subassembly":
            critical.append({"path": [c[3], c[2], "final assembly"], "arrival": c[0]})
        else:
            critical.append({"path": [c[2], "final assembly"], "arrival": c[0]})
    items.sort(key=lambda x: (x["arrival"], x["id"]), reverse=True)
    for it in items:
        it.pop("members", None)
    return {"order_date": order_date.isoformat(), "items": items, "subassemblies": sorted(subs, key=lambda s: s["earliest_start"], reverse=True),
            "final_assembly": {"earliest_start": final_start, "ready": final_ready,
                               "business_days_from_order": _bdays(order_date, _dt.date.fromisoformat(final_start))},
            "critical_path": critical, "assumptions": {"assembly_business_days": asm, "weekends_skipped": True, "holidays": "none modelled",
                                                        "unknown_lead_business_days": default_unknown}}


def _bdays(a: _dt.date, b: _dt.date) -> int:
    n, d = 0, a
    while d < b:
        d += _dt.timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n
