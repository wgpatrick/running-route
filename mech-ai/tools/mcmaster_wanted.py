"""Write vendor_cad/mcmaster_wanted.csv: every fastener and T-nut type of a design, for fetching supplier CAD.

    python tools/mcmaster_wanted.py designs/printer_v11.py

Columns: sku, desc, mcmaster, standard, qty, model_now, toolhead.
  sku        the catalogue SKU; a STEP file saved as vendor_cad/inbox/<sku>.step replaces the part's display model
  mcmaster   the McMaster-Carr number. Plain: read from McMaster's product page for the owner (supplier CAD batch 2026-11-18,
             vendor_cad/staging/supplier_2026-11-18/00-REPORT-supplier-cad-table.md). "(unverified ...)": on file from an
             earlier collector and never checked against the page it names. "not sold by McMaster": checked, no such part.
             Empty: none on file
  standard   the standard or maker's part the catalogue part was drawn from
  model_now  the state of the geometry in the model today: "supplier CAD", "faithful re-make" or "stand-in", with what the
             stand-in is (generated to standard / community CAD / assumed dimensions)
  toolhead   how many of them are on the toolhead (the X carriage's body)
"""
import collections
import csv
import re
import sys
from pathlib import Path

from mechloop.parts import vendor_cad, vendor_data
from mechloop.runner import load_design

HARDWARE = ("SHCS", "FHCS", "BHCS", "NUT-", "WASHER", "TNUT")          # fasteners and T-nuts; lead-screw nuts (NUT-TR8...) are drive parts


def short_desc(sku: str, descs: list[str]) -> str:
    m = re.match(r"SHCS-(M[\d.]+)x([\d.]+)$", sku)
    if m:
        return f"Socket head cap screw {m.group(1)} x {m.group(2)}"
    m = re.match(r"FHCS-(M[\d.]+)x([\d.]+)$", sku)
    if m:
        return f"Countersunk socket screw {m.group(1)} x {m.group(2)} (ISO 10642)"
    m = re.match(r"BHCS-FL-(M[\d.]+)x([\d.]+)$", sku)
    if m:
        return f"Flanged button head screw {m.group(1)} x {m.group(2)} (ISO 7380-2)"
    m = re.match(r"NUT-(M[\d.]+)$", sku)
    if m:
        return f"Hex nut {m.group(1)}"
    return min(descs, key=len) if descs else sku


def state_text(model: dict) -> str:
    st = vendor_cad.model_state(model)
    if st != "stand-in":
        return st
    kind = model.get("kind", "proxy")
    what = {"generated to standard": "generated to standard", "community CAD": "community CAD"}.get(kind, "assumed dimensions / simulation solid")
    return f"stand-in ({what})"


def rows_for(design, toolhead_body: str = "xbody") -> list[dict]:
    mf = vendor_data("mcmaster_fasteners")
    mc, batch = mf["part_numbers"], mf.get("supplier_batch_2026_11_18") or {}
    by = collections.defaultdict(list)
    for c in design.components:
        if (c.sku or "").startswith(HARDWARE) and not (c.sku or "").startswith(("NUT-TR8", "NUT-T8x2-POM")):
            by[c.sku].append(c)
    rows = []
    for sku, cs in by.items():
        pn = mc.get(sku, "")
        note = (batch.get("notes") or {}).get(sku, "")
        if sku == "NUT-M5-DIN934":
            pn = mc.get("NUT-M5", "")
        elif pn and sku == "NUT-M5":
            pn = f"{pn} is the DIN 934 nut (4.0 mm), not this ISO 4032 one: use NUT-M5-DIN934"
        elif pn and sku not in batch.get("confirmed", []):
            pn = f"{pn} (unverified: not checked on McMaster's page)"
        elif not pn and note.startswith("not sold by McMaster"):
            pn = "not sold by McMaster"
        if pn and sku == "SHCS-M4x6":
            pn += " (zinc-plated; no STEP under 5 MB)"
        src = cs[0].meta.get("source") or {}
        rows.append({"sku": sku, "desc": short_desc(sku, [str(c.meta.get("description") or "") for c in cs if c.meta.get("description")]),
                     "mcmaster": pn, "standard": src.get("part") or "not specified", "qty": len(cs),
                     "model_now": state_text(cs[0].meta.get("model") or {}),
                     "toolhead": sum(1 for c in cs if c.body == toolhead_body)})
    rows.sort(key=lambda r: (-r["toolhead"], r["sku"]))
    return rows


def main():
    d = load_design(sys.argv[1])
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("vendor_cad") / "mcmaster_wanted.csv"
    rows = rows_for(d)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "desc", "mcmaster", "standard", "qty", "model_now", "toolhead"])
        w.writeheader()
        w.writerows(rows)
    print(f"{out}: {len(rows)} hardware types, {sum(r['qty'] for r in rows)} parts, {sum(r['toolhead'] for r in rows)} on the toolhead")


if __name__ == "__main__":
    main()
