"""DG-07, off-the-shelf parts are real parts (owner, 2026-11-20; docs/DESIGN_GUIDELINES.md, key rule; docs/PROVENANCE_AUDIT.md,
"DG-07 check").

Only parts we fabricate (laser-cut and bent sheet, machined, printed: `cots=False` with process sheet / machined / printed) may
have geometry made by our code. Every other part is a purchased part and must be

(a) a real, orderable product: a named maker, the maker's part number and a seller (or a catalogue house's own number, which is
    maker part number and seller at once: McMaster, MISUMI, Accu as the guideline names them);
(b) drawn from the maker: geometry state "supplier CAD" or "faithful re-make" (re-made from a recorded drawing), as
    `vendor_cad.model_state` decides it;
(c) rated from the maker: every rating a check reads has a source (vendor-level catalogue record without that field among its
    unverified fields, a standard, a per-rating datasheet reference, or an electrical source that is not a typical value).

Anything else is a placeholder: allowed while designing, an error in a design presented as buildable. Findings (practice rule
DG-07): `purchased_part_not_real`, `purchased_geometry_not_sourced`, `purchased_rating_not_sourced`, errors (warnings when the
design sets `exploratory = True`). One finding per SKU and code, naming every instance.

Where the facts come from, in this order: the part's `meta["real_part"]` (a design can declare it with place(..., real_part={...})),
the SKU's record in mechloop/data/real_parts.json, then what the catalogue already records (source level, vendor record, electrical
product, `maker_part` / `supplier_part` / `vendor_part` / `mcmaster_pn` ratings) - the same fields the BOM's maker and provenance
columns are computed from (tools/build_package.py `_maker_of` / `_provenance`). A real_part record:

    {"maker": "HIWIN", "mpn": "MGN12H1R300Z0H", "sellers": [{"name": "Digi-Key", "part_number": "...", "url": "...", "checked": "2026-11-20"}],
     "sold_by_maker": false, "stock_size": "300 mm", "datasheet": "vendor_docs/...pdf", "ratings_source": {"dynamic_load_n": "datasheet p.3"},
     "replace_with": "the real part or the search that will replace a placeholder"}

`part_state(c)` gives the exporters (viewer, review page, BOM, build package) the same verdict per part: real_part_state
"real" | "geometry pending" | "placeholder" | None (fabricated), `placeholder` True for the two non-real states.
"""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path

FABRICATED = ("sheet", "machined", "printed")
PURCHASED = ("purchased", "extrusion")
DATA = Path(__file__).resolve().parent.parent / "data" / "real_parts.json"
# catalogue houses whose own part number is the orderable item (maker part number and seller at once); the guideline names them
CATALOGUE_HOUSES = {"mcmaster": "McMaster-Carr", "mcmaster-carr": "McMaster-Carr", "misumi": "MISUMI", "accu": "Accu"}
NOT_A_MAKER = ("any", "commodity", "generic", "typical", "not specified", "unknown", "class")
PLACEHOLDER_COLOUR = "#ff00ff"         # magenta: the viewer and review page draw placeholders in it
PENDING_COLOUR = "#ff66cc"             # geometry pending: a real part whose CAD is not the maker's yet
UNSOURCED_WORDS = ("typical", "unverified", "assumed", "estimate", "recalled", "class value", "not published", "guess", "proxy")
META_KEY = re.compile(r"(_basis|_source|_status|_note|_conditions)$")


@functools.lru_cache(maxsize=1)
def records() -> dict:
    """mechloop/data/real_parts.json: {sku: real_part record}."""
    try:
        return dict(json.loads(DATA.read_text(encoding="utf-8")).get("parts") or {})
    except FileNotFoundError:
        return {}


@functools.lru_cache(maxsize=1)
def ratings_used() -> frozenset:
    """Names some check may read: every quoted identifier in the mechloop sources outside the catalogue (mechloop/parts/) and this
    file. A rating whose name appears nowhere in the checks does not need a source for DG-07 (ratings are read as
    `ratings.get("x")`, `r["x"]` after an alias, or through a template, so the literal is the reliable trace)."""
    root = Path(__file__).resolve().parent.parent
    pat = re.compile(r"""["']([A-Za-z][A-Za-z0-9_]*)["']""")
    keys = set()
    files = [p for p in root.rglob("*.py") if p.relative_to(root).parts[0] != "parts" and p.resolve() != Path(__file__).resolve()]
    for p in files:
        try:
            keys |= set(pat.findall(p.read_text(encoding="utf-8")))
        except OSError:
            pass
    return frozenset(keys)


def _process(c) -> str | None:
    try:
        from ..tolerance.process import process_of

        return process_of(c)
    except Exception:
        return c.meta.get("process")


def is_purchased(c) -> bool:
    """A part we buy: an off-the-shelf part (cots), or a part whose process is "purchased" / "extrusion"."""
    return bool(c.cots) or _process(c) in PURCHASED


def is_fabricated(c) -> bool:
    """A part we make or have made to our design: not purchased, process sheet / machined / printed."""
    return not is_purchased(c) and _process(c) in FABRICATED


def _record(c) -> dict:
    rp = dict(records().get(c.sku or "", {}))
    rp.update(c.meta.get("real_part") or {})
    return rp


def _real_maker(m) -> bool:
    s = str(m or "").strip().lower()
    return bool(s) and not s.startswith(NOT_A_MAKER) and "commodity" not in s and "generic" not in s


def maker_of(c) -> tuple[str | None, str | None]:
    """(maker, maker part number) as the BOM computes them (tools/build_package._maker_of), with "any (to the standard)" and
    "commodity" taken as no maker."""
    rp = _record(c)
    if rp.get("maker") and rp.get("mpn"):
        return rp["maker"], rp["mpn"]
    src = c.meta.get("source") or {}
    e = c.ratings.get("electrical") if isinstance(c.ratings.get("electrical"), dict) else {}
    prod = (e or {}).get("product") or {}
    maker, pn = prod.get("vendor"), prod.get("part_number")
    if src.get("level") == "vendor":
        maker = maker or src.get("vendor")
        pn = pn or src.get("part")
    for k in ("vendor_part", "maker_part"):
        v = c.ratings.get(k)
        if not pn and isinstance(v, str) and v.strip():
            pn = v
            maker = maker or v.split()[0]
    if src.get("level") == "standard" and not prod.get("part_number"):
        maker, pn = None, None
    maker, pn = rp.get("maker") or maker, rp.get("mpn") or pn
    return (maker if _real_maker(maker) else None), (str(pn) if pn else None)


def sellers_of(c) -> list[dict]:
    """Where the part can be bought: the record's sellers, a confirmed catalogue-house number (McMaster), a catalogue house's own
    number (supplier_part / maker_part from MISUMI or Accu), a recorded distributor, or the maker itself when the record says so."""
    rp = _record(c)
    out = [s if isinstance(s, dict) else {"name": str(s)} for s in (rp.get("sellers") or ([rp["seller"]] if rp.get("seller") else []))]
    mc, st = c.ratings.get("mcmaster_pn"), str(c.ratings.get("mcmaster_pn_status") or "")
    if mc and st.startswith("confirmed"):
        out.append({"name": "McMaster-Carr", "part_number": mc, "status": st, "catalogue": True})
    for k in ("supplier_part", "maker_part"):
        v = c.ratings.get(k)
        if isinstance(v, str) and v.split() and v.split()[0].lower() in CATALOGUE_HOUSES:
            out.append({"name": CATALOGUE_HOUSES[v.split()[0].lower()], "part_number": " ".join(v.split()[1:]), "catalogue": True})
    if c.ratings.get("distributor"):
        out.append({"name": str(c.ratings["distributor"])})
    if rp.get("sold_by_maker"):
        out.append({"name": maker_of(c)[0] or "maker", "maker_direct": True})
    return out


def _unsourced_text(s) -> bool:
    s = str(s or "").lower()
    return not s.strip() or any(w in s for w in UNSOURCED_WORDS)


def _named_unverified(key: str, unverified) -> bool:
    k = re.sub(r"_(c|n|nm|nmm|mm|a|v|w|kg|g|mpa|hz|rpm|m|mm4|ohm|mh|gcm2)$", "", key).replace("_", " ").strip()
    return any(k and (k in str(u).lower() or str(u).lower().strip() == key) for u in unverified or ())


def _is_value(v) -> bool:
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    return isinstance(v, (list, tuple)) and bool(v) and all(isinstance(x, (int, float, list, tuple)) and not isinstance(x, bool) for x in v)


def unsourced_ratings(c) -> list[str]:
    """Ratings of a purchased part that a check reads but that have no maker's (or standard) source."""
    used = ratings_used()
    rp = _record(c)
    per = rp.get("ratings_source") or {}
    src = c.meta.get("source") or {}
    lvl = src.get("level")
    unver = src.get("unverified_fields") or []
    approx = bool(c.ratings.get("approximate"))
    out = []
    for k, v in c.ratings.items():
        if k not in used or META_KEY.search(k) or not _is_value(v):
            continue
        if per.get(k) and not _unsourced_text(per[k]):
            continue
        basis = " ".join(str(c.ratings.get(k + s, "")) for s in ("_basis", "_source", "_status"))
        ok = lvl in ("vendor", "standard") and not approx and not _named_unverified(k, unver) and not (basis.strip() and _unsourced_text(basis))
        if not ok:
            out.append(k)
    el = c.ratings.get("electrical") if isinstance(c.ratings.get("electrical"), dict) else None
    if el:
        srcs = el.get("sources") or {}
        for k, v in (el.get("ratings") or {}).items():
            if not _is_value(v) or (per.get(k) and not _unsourced_text(per[k])):
                continue
            if _unsourced_text(srcs.get(k)):
                out.append(f"electrical.{k}")
    return sorted(set(out))


def geometry_state(c) -> str:
    from ..parts import vendor_cad

    if not c.cots:
        return "stand-in"              # a purchased part drawn by hand in the design file
    return vendor_cad.model_state(c.meta.get("model") or {})


def assess(c) -> dict | None:
    """DG-07 verdict for one part; None for a fabricated part."""
    if not is_purchased(c):
        return None
    maker, pn = maker_of(c)
    sellers = sellers_of(c)
    catalogue = [s for s in sellers if s.get("catalogue")]
    missing = []
    if not catalogue:
        if not maker:
            missing.append("maker")
        if not pn:
            missing.append("maker part number")
        if not sellers:
            missing.append("seller")
    geo = geometry_state(c)
    geo_ok = geo in ("supplier CAD", "faithful re-make")
    rat = unsourced_ratings(c)
    if not missing and geo_ok and not rat:
        state = "real"
    elif not missing and not rat:
        state = "geometry pending"
    else:
        state = "placeholder"
    rp = _record(c)
    return {"part": c.name, "sku": c.sku or c.name, "state": state, "placeholder": state != "real", "maker": maker, "mpn": pn,
            "sellers": sellers, "missing": missing, "geometry": geo, "unsourced_ratings": rat,
            "replace_with": rp.get("replace_with") or rp.get("candidates") or ""}


def part_state(c) -> dict:
    """For the exporters: {"real_part_state", "placeholder", "placeholder_colour"} (state None for a part we make)."""
    a = assess(c)
    if a is None:
        return {"real_part_state": None, "placeholder": False}
    return {"real_part_state": a["state"], "placeholder": a["placeholder"],
            "placeholder_colour": PLACEHOLDER_COLOUR if a["state"] == "placeholder" else PENDING_COLOUR if a["placeholder"] else None,
            "placeholder_why": "; ".join(why(a)) or None}


def why(a: dict) -> list[str]:
    out = []
    if a["missing"]:
        out.append("no " + ", ".join(a["missing"]))
    if a["geometry"] not in ("supplier CAD", "faithful re-make"):
        out.append(f"geometry is a {a['geometry']} (not the maker's CAD or a re-make from its drawing)")
    if a["unsourced_ratings"]:
        out.append("ratings without a maker's source: " + ", ".join(a["unsourced_ratings"][:6]))
    return out


def extra_missing(sku: str, e: dict) -> list[str]:
    """A BOM-only line (design.bom_extra, no geometry): what of maker / part number / seller it lacks."""
    rp = dict(records().get(sku, {}))
    rp.update(e.get("real_part") or {})
    if e.get("mcmaster_pn") and str(e.get("mcmaster_pn_status", "confirmed")).startswith("confirmed"):
        return []
    miss = []
    if not _real_maker(rp.get("maker") or e.get("maker")):
        miss.append("maker")
    if not (rp.get("mpn") or e.get("mpn") or e.get("maker_part_number")):
        miss.append("maker part number")
    if not (rp.get("sellers") or rp.get("seller") or e.get("seller") or rp.get("sold_by_maker")):
        miss.append("seller")
    return miss


def dg07(design) -> dict:
    """Every purchased part and BOM-only line of a design, grouped by SKU: {"by_sku", "extras", "counts", "placeholders"}."""
    by = {}
    for c in design.components:
        a = assess(c)
        if a is None:
            continue
        g = by.setdefault(a["sku"], {**{k: a[k] for k in ("sku", "state", "maker", "mpn", "missing", "geometry", "unsourced_ratings",
                                                           "replace_with")},
                                     "sellers": [s.get("name") for s in a["sellers"]], "parts": [], "qty": 0,
                                     "description": c.meta.get("description", "")})
        g["parts"].append(c.name)
        g["qty"] += 1
        rank = {"real": 0, "geometry pending": 1, "placeholder": 2}
        if rank[a["state"]] > rank[g["state"]]:              # one SKU, worst instance (sizes and placements may differ)
            g.update({k: a[k] for k in ("state", "missing", "geometry", "unsourced_ratings")})
    extras = {}
    for sku, e in (design.bom_extras or {}).items():
        miss = extra_missing(sku, e)
        extras[sku] = {"sku": sku, "qty": e.get("qty", 0), "missing": miss, "state": "placeholder" if miss else "real"}
    rows = list(by.values())
    counts = {
        "purchased_skus": len(rows), "purchased_parts": sum(r["qty"] for r in rows), "bom_only_lines": len(extras),
        "real_skus": sum(r["state"] == "real" for r in rows), "geometry_pending_skus": sum(r["state"] == "geometry pending" for r in rows),
        "placeholder_skus": sum(r["state"] == "placeholder" for r in rows),
        "placeholder_parts": sum(r["qty"] for r in rows if r["state"] != "real"),
        "not_real": {"skus": sum(bool(r["missing"]) for r in rows) + sum(bool(x["missing"]) for x in extras.values()),
                     "parts": sum(r["qty"] for r in rows if r["missing"]), "bom_only_lines": sum(bool(x["missing"]) for x in extras.values())},
        "geometry_not_sourced": {"skus": sum(r["geometry"] not in ("supplier CAD", "faithful re-make") for r in rows),
                                 "parts": sum(r["qty"] for r in rows if r["geometry"] not in ("supplier CAD", "faithful re-make"))},
        "rating_not_sourced": {"skus": sum(bool(r["unsourced_ratings"]) for r in rows),
                               "parts": sum(r["qty"] for r in rows if r["unsourced_ratings"])},
    }
    placeholders = [{"sku": r["sku"], "qty": r["qty"], "state": r["state"], "why": "; ".join(why(r)), "replace_with": r["replace_with"]}
                    for r in sorted(rows, key=lambda r: (r["state"] == "geometry pending", r["sku"])) if r["state"] != "real"]
    placeholders += [{"sku": x["sku"], "qty": x["qty"], "state": "placeholder", "why": "BOM-only line with no " + ", ".join(x["missing"]),
                      "replace_with": ""} for x in extras.values() if x["missing"]]
    return {"by_sku": by, "extras": extras, "counts": counts, "placeholders": placeholders,
            "buildable": not placeholders,
            "exploratory": bool(getattr(design, "exploratory", False))}
