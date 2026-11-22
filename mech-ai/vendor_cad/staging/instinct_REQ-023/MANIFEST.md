# instinct_REQ-023: M5 large-OD flat washer (about 15 mm OD, DIN 9021 / ISO 7093 class, about 1.2 thick), jam nut across a 6.2 mm T-slot

Ingested 2026-11-22 (about 01:15Z). Drive folder `mechloop handoff/results/REQ-023-m5-large-washer` (1e4J3SWlFlCPMxJOH0yp1kAjcfcSDCCWS);
folder listed by `parentId` (5 files, no further page). Request file `REQ-023-m5-large-washer.md` (17v1OGWsWs0OrU2uqhztKtxLt_CKHAwPD, read only).
Each file was downloaded by Drive id into one new empty scratch directory and read with `python -I` from scripts kept elsewhere.
Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed.
Instinct's STATUS: **COMPLETE** (two candidates, sourcing + CAD + drawings; no purchase made).

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (13ixg6tR4ePpky3KPBbzUhYr62h9M0eUY, 1,483 B) | RESULT_instinct_REQ-023_2026-11-22.md | c16147aad453f19cd29e1d1a1bddf27cc23092bfc1dc56db335aea8ac2a8fc58 |
| 91100A140__cad.step (1p6ECduf02bQQXHHz5F1JojruHFbFifFq, 236,990 B) | McMaster_91100A140_Washer_M5_Oversized_5.3x15x1.2_ZincSteel.step | 9ef7536f9b0209b4422b18874c9a7af6364aa736cf55976da2aaf826a69e9540 |
| 91100A140__datasheet.pdf (1CjohsSvZDE-5cpqjsok2h8cLdrxdFgdS, 50,807 B) | vendor_docs/mcmaster_91100A140_datasheet.pdf | 48cfeb636966cbc773178b46502fa929dd2cea55e03b03d047929d9dd175144e |
| 91116A140__cad.step (1TdzfsP0O8J9ZH9nXA6GBayIUOB1RmlGD, 245,975 B) | McMaster_91116A140_Washer_M5_Oversized_5.3x15x1.2_18-8SS.step | 5f1b33c7fc7314bc4da438b3cc4b90b8cd41272a912054eea8736074854726e9 |
| 91116A140__datasheet.pdf (1Phbsz4rBTbrF7kyKatrfG7nkp6ZCBi4A, 49,054 B) | vendor_docs/mcmaster_91116A140_datasheet.pdf | 8b6eeee4ff2cf049aba441f953a015b73d862ba43c8e068aa8a1de1809636d38 |

## Chosen part
**McMaster-Carr 91100A140**, Zinc-Plated Steel Oversized Washer, for M5, 5.3 mm ID, 15 mm OD, 1.0 to 1.4 mm thick.
SKU in the catalogue: `WASHER-M5-LARGE` (mechloop/parts/vendor/mcmaster_fasteners.json). 91116A140 (18-8 stainless) is staged as the alternate.

Why 91100A140:
- Same material as WASHER-M5 = 91166A240 ("Zinc-Plated Steel General Purpose Washer", "Material: Steel" in the header of
  vendor_cad/inbox/WASHER-M5.step, read only) and as the catalogue's generated
  `washer_flat('M5', 'large')` (material "steel"); the request asked for the same family.
- Same McMaster oversized family as REQ-001's 91100A120 (M3, 9 OD) and 91100A130 (M4, 12 OD).
- Both candidates have identical ID / OD / thickness, so nothing is gained geometrically by the stainless one; for spreading a jam nut's load
  across a T-slot, zinc steel and 18-8 have about the same stiffness. 91100A140 is about one third of the price ($5.12 vs $15.47 per 100).
- Its ID 5.3 / OD 15.0 / thickness 1.2 match the catalogue's ISO 7093-1 M5 large entry (`WASHER["large"]["M5"] = (5.3, 15.0, 1.2)` in
  mechloop/parts/hardware.py) exactly, so no catalogue dimension change is needed.

## Stated provenance, price and availability (per Instinct, not verified)
- 91100A140: $5.12 per pack of 100; "Delivers Tuesday by 5 pm" (delivery estimate, no stock count). https://www.mcmaster.com/91100A140/
- 91116A140: $15.47 per pack of 100; same delivery estimate. https://www.mcmaster.com/91116A140/
- **Family:** Instinct says the reference 91166A general purpose family stops at 10.0 mm OD for M5 (no 15 mm OD); the Oversized Washer
  families (91100A zinc steel, 91116A 18-8) are McMaster's 15 mm OD route. Neither is sold as DIN 9021 / ISO 7093; same oversize pattern.
- **STEP headers:** both AP214, SolidWorks 2024 (SwSTEP 2.0), organisation "McMaster Carr Supply", comments "Part Number: 91100A140",
  "Material: Steel" (dated 2026-11-07T19:01:57) and "Part Number: 91116A140", "Material: 18-8 Stainless Steel" (2026-11-07T18:59:36),
  "(c) 2026 McMaster-Carr Supply Company". Consistent with official McMaster CAD files.
- **Drawings:** not McMaster's original PDFs. Each is a 1-page wrapper around one embedded 1050x811 JPEG made by Instinct (/Title
  `<pn>__datasheet`, CreationDate 2026-11-22 00:49Z). Each raster is the McMaster dimensioned drawing with the matching title-block part number
  and description: OD 15mm, ID 5.3mm "For M5 Screw Size", thickness 1mm to 1.4mm.
- **PDF safety** (pypdf full object walk, both files): no JavaScript, JS, OpenAction, AA, Launch, EmbeddedFile(s), RichMedia, XFA, AcroForm,
  URI, SubmitForm, GoToR or ImportData keys. Not encrypted. No text layer.

## Geometry vs drawing (build123d, python -I)

| Item | Wanted (REQ-023) | Drawing (both) | 91100A140 STEP (measured) | 91116A140 STEP (measured) | Result |
|---|---|---|---|---|---|
| Solids | - | - | 1, valid (is_valid and BRepCheck) | 1, valid (is_valid and BRepCheck) | ok |
| Inside diameter | M5 | 5.3 mm | 5.300 (cylinder face) | 5.300 (cylinder face) | match |
| Outside diameter | about 15 | 15 mm | 15.000 (cylinder face; bbox 15.0 x 15.0) | 15.000 (cylinder face; bbox 15.0 x 15.0) | match |
| Thickness | about 1.2 | 1 to 1.4 mm | 1.200 (flat faces at z = -0.6 and +0.6) | 1.200 (flat faces at z = -0.6 and +0.6) | match (mid of band) |
| Edge breaks | - | 91100A140 drawing shows rounded edges on one face | R 0.291 on both edges of the +Z face only; -Z face flat to the OD (flat area 154.65 mm2) | R 0.075 on all four edges, both faces (flat area 149.87 mm2 each) | consistent |
| Centred | - | - | yes (axis Z through origin) | yes (axis Z through origin) | ok |
| Volume | - | - | 184.42 mm3 (plain ring 185.58) | 185.43 mm3 | - |

Result: both STEPs match their drawings and the request on every checked dimension.

Notes:
- Each STEP is a BREP_WITH_VOIDS: one real outer shell plus 20 zero-volume void shells of 6 zero-area planar faces each (120 faces, total
  area 7e-7 mm2), all clustered at one point inside the material (91100A140 at x 0.54, y 4.82, z -0.214; 91116A140 at x -1.61, y -2.68,
  z -0.214). The solids are still valid and the volumes are right; harmless for import, but a strict mesher may trip on them (same pattern as
  the McMaster parts in instinct_REQ-019 and REQ-022).
- 91100A140 has its edge radius (a punched-washer rollover model) on one face only. For the most bearing area on the rail, put the flat
  (-Z in the STEP) face against the extrusion; with OD 15 across the 6.2 mm slot opening each side overlaps the slot lip by about 4.4 mm.
- Fit to REQ-023: **both meet the request** (M5, 15 OD, 1.2 thick, steel). 91100A140 chosen; 91116A140 is an equally valid stainless alternate.
- Not changed here: the catalogue's `WASHER-M3-LARGE` / `WASHER-M4-LARGE` notes in mcmaster_fasteners.json say McMaster sells no 9 / 12 mm
  OD metric washer, while instinct_REQ-001 staged 91100A120 (M3, 9 OD) and 91100A130 (M4, 12 OD) from this same family. Flagged for the owner.
