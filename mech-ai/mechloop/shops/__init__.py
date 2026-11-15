"""Fabricators' own published limits, kept as data: one JSON file per shop beside this module.

Every number in a profile carries the page it was read on, the date, and the page's own words
(`verbatim`); what a shop does not publish is listed under `not_published`, not filled in.
docs/FABRICATORS.md is the readable form.

Three things use a profile:

1. `register(SHOPS, SOURCES)` (called at the end of verifiers/dfm_rules.py) puts each profile into the
   table the manufacture verifier's `Limits` reads: stocked thicknesses, rule limits the shop states
   itself, the page each came from.
2. `check_shop_part(...)` (called from verifiers/manufacture.py after a part's own process checks) applies
   what only a named shop can say: is the material in its chart, is there enough web between cut
   features, does it tap that thread in that thickness, which finishing services fit the part.
3. `process_tolerance(...)` (called from tolerance/process.py `tol`) gives the tolerance simulation the
   shop's cut or machining tolerance in place of the class value for that process.

Choosing a shop: `d.manufacturing["shop"] = "sendcutsend"` for a whole design (manufacture verifier), or
per part `meta={"dfm": {"shop": "xometry"}}`. `assign(design, sheet="sendcutsend", machined="xometry")`
writes the per-part form for every custom part of a process; the tolerance simulation reads only the
per-part form (it sees parts, not the design).
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).parent
FINISHES = ("powder_coat", "zinc", "nickel", "anodize", "paint", "oil", "chem_film", "bare")
# which service row of a thickness a declared finish needs
_FINISH_ROW = {"powder_coat": "powder_coat", "zinc": "plating", "nickel": "plating", "anodize": "anodize"}


@lru_cache(maxsize=None)
def profiles() -> dict:
    """{shop name: profile} for every JSON file in this folder."""
    out = {}
    for p in sorted(HERE.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        out[d["name"]] = d
    return out


def profile(name: str) -> dict | None:
    return profiles().get(name)


def source_text(prof: dict, key: str | None) -> str:
    s = (prof.get("sources") or {}).get(key or "")
    if not s:
        return key or prof["name"]
    return f"{s['url']} (read {s['accessed']})" if s.get("url") else s["title"]


def provenance(prof: dict, rule_id: str) -> dict:
    """{value, unit, verbatim, url, accessed} of one of the profile's rules."""
    r = prof["rules"][rule_id]
    s = (prof.get("sources") or {}).get(r.get("source") or "", {})
    return {"value": r.get("value"), "unit": r.get("unit"), "verbatim": r.get("verbatim"), "url": s.get("url"), "accessed": s.get("accessed"),
            "note": r.get("note")}


# ------------------------------------------------------------------------------------- registration
def register(shops: dict, sources: dict) -> None:
    """Merge each profile into dfm_rules.SHOPS (the form `Limits` reads). Keys a shop already had in code (its cut-size and
    bend tables) are kept; the profile adds or replaces stock lists, the shop's own rule limits and their sources."""
    for name, prof in profiles().items():
        for key, s in prof.get("sources", {}).items():
            sources.setdefault(key, f"{s['url']} (read {s['accessed']})" if s.get("url") else s["title"])
        entry = dict(shops.get(name) or {})
        entry.setdefault("plate_stock", dict((shops.get("generic") or {}).get("plate_stock") or {}))
        entry.setdefault("sheet_stock", dict((shops.get("generic") or {}).get("sheet_stock") or {}))
        entry["description"] = prof["description"]
        entry["strict"] = bool(prof.get("strict"))
        entry["source"] = prof.get("source", "own")
        if "sheet" in prof.get("processes", ()):
            stock = {m: tuple(row["t_mm"] for row in info.get("thicknesses", ())) for m, info in prof["materials"].items()}
            entry["sheet_stock"] = {m: t for m, t in stock.items() if t}        # no "*": an unlisted material is not stocked
        if prof.get("plate_stock"):
            entry["plate_stock"] = {**entry["plate_stock"], **{m: tuple(v["mm"]) for m, v in prof["plate_stock"].items()}}
        entry["limits"] = {rid: float(v["value"]) for rid, v in (prof.get("limits") or {}).items()}
        entry["limit_sources"] = {rid: source_text(prof, prof["rules"][v["rule"]].get("source")) for rid, v in (prof.get("limits") or {}).items()}
        entry["profile"] = name
        shops[name] = entry


def assign(design, **by_process) -> dict:
    """Name a shop for every custom part of a process: assign(d, sheet="sendcutsend", machined="xometry").
    Writes meta["dfm"]["shop"] on each part that does not already name one. Returns {part: shop}."""
    from ..tolerance.process import process_of

    unknown = [s for s in by_process.values() if s not in profiles() and s != "generic"]
    if unknown:
        raise ValueError(f"unknown shop {unknown}; known: {sorted(profiles())}")
    done = {}
    for c in design.components:
        if c.cots:
            continue
        shop = by_process.get(process_of(c))
        if shop and not (c.meta.get("dfm") or {}).get("shop"):
            c.meta.setdefault("dfm", {})["shop"] = shop
            done[c.name] = shop
    return done


# ------------------------------------------------------------------------------- tolerance tables
_SPAN: dict = {}


def _span(c) -> float:
    """Longest side of the part's bounding box, mm (cached per component)."""
    k = id(c)
    hit = _SPAN.get(k)
    if hit is None or hit[0] is not c or hit[1] is not c.shape:      # an id is reused once its object is gone: check identity
        try:
            bb = c.shape.bounding_box()
            v = float(max(bb.size.X, bb.size.Y, bb.size.Z))
        except Exception:
            v = 0.0
        hit = _SPAN[k] = (c, c.shape, v)
    return hit[2]


def tolerance_row(shop: str, process: str, span_mm: float) -> dict | None:
    """The shop's tolerance entry for a process and part length: the fields it publishes, with their basis."""
    prof = profile(shop)
    rows = ((prof or {}).get("tolerance") or {}).get(process)
    if not rows:
        return None
    for row in rows:
        if row.get("up_to_mm") is None or span_mm <= row["up_to_mm"] + 1e-9:
            return row
    return rows[-1]


def process_tolerance(c, process: str, base: dict) -> dict:
    """The tolerance table for one part: the class values of its process, with the fields its shop publishes replaced
    (meta["dfm"]["shop"]), and then any the part states itself (meta["dfm"]["tolerance"] = {"flat": 0.02}, one standard
    deviation, for a face or pattern toleranced on the drawing)."""
    dfm = c.meta.get("dfm") or {}
    out = dict(base)
    row = tolerance_row(dfm.get("shop") or "", process, _span(c)) if dfm.get("shop") else None
    if row:
        out.update({k: float(v) for k, v in row.items() if k in base})
    own = dfm.get("tolerance") or {}
    bad = [k for k in own if k not in base]
    if bad:
        raise ValueError(f"{c.name}: unknown tolerance field(s) {bad}; use {sorted(base)}")
    out.update({k: float(v) for k, v in own.items()})
    return out


# ---------------------------------------------------------------------------- per-part shop checks
def stock_row(prof: dict, material: str, t: float) -> tuple[dict | None, dict | None]:
    """(material entry, the thickness row nearest t) from a profile; (None, None) if the material is not listed."""
    info = (prof.get("materials") or {}).get(material)
    if not info:
        return None, None
    rows = info.get("thicknesses") or []
    return info, (min(rows, key=lambda r: abs(r["t_mm"] - t)) if rows else None)


def _fits(size, svc) -> bool:
    """A flat part (long, short) inside a service's min and max part size [(short, long), (short, long)]."""
    long_, short_ = max(size), min(size)
    mn, mx = svc.get("min_part_mm"), svc.get("max_part_mm")
    return not ((mn and (short_ < mn[0] - 1e-6 or long_ < mn[1] - 1e-6)) or (mx and (short_ > mx[0] + 1e-6 or long_ > mx[1] + 1e-6)))


def services_for(prof: dict, material: str, t: float, flat_size) -> dict:
    """Which of the shop's services a flat part of this material, thickness and size can have: {service: {...}}."""
    info, row = stock_row(prof, material, t)
    if row is None:
        return {}
    out = {"stock_mm": row["t_mm"], "stock_listed_as": (row.get("cut") or {}).get("thickness_as_listed"),
           "difference_mm": round(t - row["t_mm"], 3), "grade": info.get("grade")}
    for svc in ("deburr", "tumble", "tap", "countersink", "powder_coat", "plating", "anodize", "bend", "hardware"):
        s = row.get(svc)
        if not s:
            out[svc] = {"offered": False, "why": "not listed for this material and thickness"}
            continue
        ok = _fits(flat_size, s) if flat_size else True
        e = {"offered": bool(ok)}
        if not ok:
            e["why"] = f"part {flat_size[0]:g} x {flat_size[1]:g} mm outside {s.get('min_part_mm')} to {s.get('max_part_mm')} mm"
        if svc == "tap":
            e["metric"] = [s.get("metric_min"), s.get("metric_max")]
        if svc == "countersink":
            e["minor_min_mm"], e["major_max_mm"] = s.get("min_minor_mm"), s.get("max_major_mm")
        e["verbatim"] = s.get("verbatim")
        out[svc] = e
    return out


def check_shop_part(r, design, c, row: dict, lim) -> None:
    """What the part's chosen shop says about it beyond the general process checks. Adds findings to r and a
    `shop_services` / `shop_notes` entry to the part's metrics row. Does nothing for the generic shop."""
    prof = profile(getattr(lim, "shop_name", "") or "")
    proc = row.get("process")
    if prof is None or proc not in ("sheet", "machined"):
        return
    name = c.name

    def add(sev, code, msg, rule=None, **data):
        if rule and rule in prof["rules"]:
            p = provenance(prof, rule)
            data.update(rule=f"{prof['name']}.{rule}", source=f"{p['url']} (read {p['accessed']})", verbatim=p["verbatim"])
            data.setdefault("limit", p["value"] if isinstance(p["value"], (int, float)) else None)
        elif rule:
            data["rule"] = rule
        r.add(sev, code, f"{name}: {msg}", part=name, shop=prof["name"], **data)

    if proc not in prof.get("processes", ()):
        add("warning", "shop_process_not_profiled", f"{prof['name']}'s profile covers {', '.join(prof['processes'])} parts, not {proc}; "
            "only the general rules were applied.", hint="Name the shop that makes this part: meta={'dfm': {'shop': ...}}.")
        return
    if proc == "sheet":
        _check_sheet(prof, r, design, c, row, add)
    else:
        _check_machined(prof, r, design, c, row, add)


def _finish(c) -> str | None:
    f = c.meta.get("finish") or (c.meta.get("dfm") or {}).get("finish")
    return str(f).lower() if f else None


def _check_sheet(prof, r, design, c, row, add) -> None:
    from ..verifiers import dfm_geom as G
    from ..verifiers import dfm_sheet

    t = row.get("thickness_mm")
    info, srow = stock_row(prof, c.material, t or 0.0)
    if info is None:
        add("error", "shop_material_not_offered", f"{prof['name']} lists no {c.material} for cutting (it lists "
            f"{', '.join(sorted(prof['materials']))}).", value=None,
            source=source_text(prof, prof.get("source")), hint="Choose a listed material, or another shop.")
        return
    if t is None or srow is None:
        return
    ts = srow["t_mm"]                      # the shop judges against the stock it will cut
    flat = row.get("flat_size_mm")
    sv = services_for(prof, c.material, t, flat)
    sv["finish_declared"] = _finish(c)
    row["shop_services"] = sv
    if row.get("form") != "flat":
        return
    # ---- web between cut features, and to the edge
    rule = prof["rules"].get("web_min_t_ratio")
    try:
        sm = G.sample_surface(c.shape, n=200)
        plate = dfm_sheet.plate_of(c.shape, G.part_frame(c.shape), sm)
        P = dfm_sheet.profile_of(plate) if plate is not None else None
    except Exception:
        plate, P, sm = None, None, None
    if rule and P is not None and not P.is_empty:
        from shapely.geometry import Polygon

        P = max(dfm_sheet._polys(P), key=lambda p: p.area)
        need = float(rule["value"]) * ts
        rings = [Polygon(ring) for ring in P.interiors]
        worst = None
        for i, a in enumerate(rings):
            d = P.exterior.distance(a.exterior)
            if worst is None or d < worst[0]:
                worst = (d, a.centroid, "the edge")
            for b in rings[i + 1:]:
                d = a.distance(b)
                if d < worst[0]:
                    worst = (d, a.centroid, "the next cut-out")
        if worst is not None:
            row["shop_services"]["least_web_mm"] = round(worst[0], 2)
            row["shop_services"]["web_minimum_mm"] = round(need, 2)
            if worst[0] < need - 1e-6:
                add("error", "shop_web_below_minimum",
                    f"{worst[0]:.2f} mm of material between a hole and {worst[2]}; {prof['name']} asks for at least {need:.2f} mm "
                    f"({rule['value']:g} x the {ts:g} mm stock) between cut features and to the edge.", rule="web_min_t_ratio",
                    value=round(worst[0], 3), limit_mm=round(need, 3), at=[dfm_sheet._to_world(plate, worst[1].x, worst[1].y)],
                    hint=f"Leave at least {need:.2f} mm; {ts:g} to {1.5 * ts:g} mm is what the shop prefers.")
    # ---- threads
    tapped = []
    if sm is not None:
        try:
            tapped = G.tapped_holes(design, c, sm)
        except Exception:
            tapped = []
    if tapped:
        sizes = sorted({float(tp["d"]) for tp in tapped})
        tap = srow.get("tap")
        label = ", ".join(f"M{d:g}" for d in sizes)
        if not tap:
            add("error", "shop_tap_not_offered", f"{len(tapped)} tapped hole(s) ({label}): {prof['name']} does not tap {ts:g} mm {c.material} "
                f"(tapping starts at {prof['rules']['tap_min_thickness_mm']['value']:.2f} mm).", rule="tap_min_thickness_mm", value=ts,
                at=[tp["at"] for tp in tapped[:6]], hint="Use thicker stock, a press-in (PEM) nut, a rivet nut, or a through bolt and nut.")
        else:
            out = [d for d in sizes if d < tap["metric_min"] - 1e-9 or d > tap["metric_max"] + 1e-9]
            if out:
                add("error", "shop_tap_not_offered", f"{', '.join(f'M{d:g}' for d in out)} is outside what {prof['name']} taps in {ts:g} mm "
                    f"{c.material} (M{tap['metric_min']:g} to M{tap['metric_max']:g}).", value=out[0], limit=tap["metric_max"],
                    source=source_text(prof, tap.get("source")), verbatim=" | ".join(tap["verbatim"]), at=[tp["at"] for tp in tapped[:6]],
                    hint="Change the thread or the thickness, or use a press-in nut.")
            elif flat and not _fits(flat, tap):
                add("error", "shop_tap_not_offered", f"the part ({flat[0]:g} x {flat[1]:g} mm) is outside the size {prof['name']} taps "
                    f"({tap['min_part_mm']} to {tap['max_part_mm']} mm).", value=min(flat), source=source_text(prof, tap.get("source")),
                    verbatim=" | ".join(tap["verbatim"]), hint="Tap it by hand, or enlarge the part.")
    # ---- countersinks
    n_csk = (plate or {}).get("countersinks") if plate else 0
    if n_csk:
        csk = srow.get("countersink")
        if not csk or (flat and not _fits(flat, csk)):
            add("error", "shop_countersink_not_offered", f"{n_csk} countersink(s): {prof['name']} does not countersink "
                + (f"{ts:g} mm {c.material}." if not csk else f"a part of {flat[0]:g} x {flat[1]:g} mm (its limits: {csk['min_part_mm']} to {csk['max_part_mm']} mm)."),
                rule="countersink_min_thickness_mm", value=ts, hint="Use button-head screws on plain holes, or thicker stock.")
    # ---- material rules: a finish on carbon steel, and a finish the shop can apply
    fin = _finish(c)
    for mr in prof.get("material_rules", ()):
        if c.material not in (mr.get("materials") or ()):
            continue
        if mr["kind"] == "finish_required" and fin is None:
            pc, pl = sv.get("powder_coat", {}).get("offered"), sv.get("plating", {}).get("offered")
            offer = [w for w, ok in (("powder coat", pc), ("zinc or nickel plating", pl)) if ok]
            add(mr["severity"], "bare_steel_no_finish", f"carbon steel with no finish declared: it rusts. At {ts:g} mm and this size "
                f"{prof['name']} offers " + (" and ".join(offer) if offer else "no coating (part too small or too thin)") + ".",
                source=source_text(prof, mr.get("source")), rule=f"{prof['name']}.{mr['id']}",
                hint="Declare meta={'finish': 'powder_coat'} (adds 0.05-0.13 mm per side, insulates: scrape or mask the earth-bond contact), "
                     "'zinc', 'oil', or 'bare' with a reason; or make the part in aluminium or stainless.")
    if fin in _FINISH_ROW and not sv.get(_FINISH_ROW[fin], {}).get("offered"):
        add("error", "shop_finish_not_offered", f"finish '{fin}' is not offered by {prof['name']} for {ts:g} mm {c.material} at this size "
            f"({sv.get(_FINISH_ROW[fin], {}).get('why', 'not listed')}).", source=source_text(prof, "scs-processing"),
            hint="Choose a finish the shop lists for this stock, or finish the part elsewhere.")
    elif fin is not None and fin not in FINISHES:
        add("warning", "unknown_finish", f"finish '{fin}' is not one of {FINISHES}.")


def _check_machined(prof, r, design, c, row, add) -> None:
    from ..verifiers import dfm_geom as G

    if c.material not in prof["materials"]:
        why = (prof.get("materials_not_listed") or {}).get(c.material, "")
        add("warning", "shop_material_not_listed", f"{c.material} is not in {prof['name']}'s published material list"
            + (f": {why}" if why else "") + ".", source=source_text(prof, "xo-cnc"),
            hint="Expect a manual quote review; or choose a listed material.")
    span = _span(c)
    notes = {"material_listed_as": (prof["materials"].get(c.material) or {}).get("listed_as"), "longest_side_mm": round(span, 1)}
    rules = prof["rules"]
    if "general_tolerance_mm" in rules:
        notes["general_tolerance_mm"] = rules["general_tolerance_mm"]["value"]
    if "form_tolerance_mm" in rules:
        notes["flatness_without_drawing_mm"] = next((tol for up, tol in rules["form_tolerance_mm"]["value"] if up is None or span <= up), None)
    if "edge_break" in rules:
        notes["edge_break"] = rules["edge_break"]["verbatim"]
    if "surface_finish" in rules:
        notes["surface_finish_um_ra"] = rules["surface_finish"]["value"]
    row["shop_notes"] = notes
    axes = (rules.get("max_part_by_axes_mm") or {}).get("value") or {}
    if axes and span > float(axes.get("3", math.inf)) + 1e-6:
        add("warning", "shop_part_too_big", f"{span:.0f} mm long: past the {axes['3']:g} mm {prof['name']} gives for 3-axis work; it goes to quote review.",
            rule="max_part_by_axes_mm", value=round(span, 1), limit=float(axes["3"]))
    mf = rules.get("min_feature_mm")
    holes = row.get("smallest_hole_mm")
    if mf and holes and holes < float(mf["value"]) - 1e-9:
        add("error", "shop_feature_below_minimum", f"a {holes:g} mm hole is below {prof['name']}'s {mf['value']:g} mm minimum feature size.",
            rule="min_feature_mm", value=holes)
    try:
        tapped = G.tapped_holes(design, c, G.sample_surface(c.shape, n=200))
    except Exception:
        tapped = []
    if tapped and "thread_callout" in rules:
        sizes = sorted({float(tp["d"]) for tp in tapped})
        notes["threads"] = [f"M{d:g}" for d in sizes]
        add(rules["thread_callout"].get("severity", "warning"), "shop_thread_callout",
            f"{len(tapped)} tapped hole(s) ({', '.join(f'M{d:g}' for d in sizes)}): the model carries plain holes, and {prof['name']} machines "
            "a hole to the modelled diameter unless it is called out as a thread.", rule="thread_callout", value=len(tapped),
            at=[tp["at"] for tp in tapped[:6]], hint="List every thread (size, depth, through or blind) in the quote's thread features or on a drawing.")
