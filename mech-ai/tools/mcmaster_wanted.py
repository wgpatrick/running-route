"""Write vendor_cad/mcmaster_wanted.csv: every fastener and T-nut type of a design, for fetching supplier CAD.

    python tools/mcmaster_wanted.py designs/printer_v10_1.py

Columns: sku, desc, mcmaster, standard, qty, model_now, toolhead.
  sku        the catalogue SKU; a STEP file saved as vendor_cad/inbox/<sku>.step replaces the part's display model
  mcmaster   the McMaster-Carr number on file, always marked "(unverified ...)": McMaster's pages cannot be reached from the
             sessions that wrote this repository, so no number here was checked against the page it names. Empty: none on file
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

HARDWARE = ("SHCS", "FHCS", "NUT-", "WASHER", "TNUT")          # fasteners and T-nuts; lead-screw nuts (NUT-TR8...) are drive parts
SUSPECT = {"91290A400": "does not fit the 91290A series' numbering for M3 x 8", "91290A500": "does not fit the 91290A series' numbering for M3 x 12",
           "91290A600": "does not fit the 91290A series' numbering for M3 x 14"}


def short_desc(sku: str, descs: list[str]) -> str:
    m = re.match(r"SHCS-(M[\d.]+)x([\d.]+)$", sku)
    if m:
        return f"Socket head cap screw {m.group(1)} x {m.group(2)}"
    m = re.match(r"FHCS-(M[\d.]+)x([\d.]+)$", sku)
    if m:
        return f"Countersunk socket screw {m.group(1)} x {m.group(2)} (ISO 10642)"
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
    mc = vendor_data("mcmaster_fasteners")["part_numbers"]
    by = collections.defaultdict(list)
    for c in design.components:
        if (c.sku or "").startswith(HARDWARE) and not (c.sku or "").startswith("NUT-TR8"):
            by[c.sku].append(c)
    rows = []
    for sku, cs in by.items():
        pn = mc.get(sku, "")
        if pn:
            why = SUSPECT.get(pn)
            pn = f"{pn} (unverified: {why}; likely wrong)" if why else f"{pn} (unverified: not checked on McMaster's page)"
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
