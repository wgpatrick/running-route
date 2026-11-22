# instinct_REQ-022: M4 x 0.7 x 60 flat-head socket screw (90 deg, ISO 10642 / DIN 7991), for bed-thumb-reach

Ingested 2026-11-22 (about 00:25Z). Drive folder `mechloop handoff/results/REQ-022-m4x60-flat-head-screw` (13RJADVsQ5SmYd0GHSB3UWOl6WI7NBNDv);
folder listed by `parentId` (3 files, no further page). Each file was downloaded by Drive id into one new empty scratch directory and read with
`python -I` from a script kept elsewhere. Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed.
Instinct's STATUS: **COMPLETE** (one candidate, sourcing + CAD + drawing; no purchase made).

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1H5VIF8R_vaCQX_VGFqSLfhKS8BFvv30-, 1,145 B) | RESULT_instinct_REQ-022_2026-11-21.md | 4ba56f90b2e744f148ce09381bcdcffba572e5e9ce92d33b8630d143f6eee284 |
| 92125A221__cad.step (1zr-oM3W_y9N-kMAKdihqwOogfbX0olvv, 2,338,429 B) | McMaster_92125A221_FHCS_M4x0.7x60_18-8SS_ISO10642.step | 09b79f51fb374c7ba1c8ec23823d43aa41ccdf129f1837af0b79516c85bedf9c |
| 92125A221__datasheet.pdf (10R6vl1Q1tk68rAk66OzRTuZqKlE_VA3s, 51,091 B) | vendor_docs/mcmaster_92125A221_datasheet.pdf | 504ce772e2c40f2156dbf5ce55316798ffa3bf99b51ee8aa9dcc3cbe79bfd362 |

## Part
**McMaster-Carr 92125A221**, 18-8 Stainless Steel Hex-Drive Flat Head Screw, M4 x 0.7 mm, 60 mm long, 90 deg countersink, fully threaded.
SKU in the catalogue: `FHCS-M4x60` (mechloop/parts/vendor/mcmaster_fasteners.json).

## Stated provenance, price and availability (per Instinct, not verified)
- $9.71 per pack of 25; "Delivers Tuesday by 5 pm" (delivery estimate, no stock count). Page https://www.mcmaster.com/92125A221/
- Specs met per product page: DIN 7991, ISO 10642. Tensile 70,000 psi (about 483 MPa) per Instinct.
- **Series:** not the requested family. The black-oxide alloy-steel 91294A series (FHCS-M4x40 = 91294A204) stops at M4 x 50 (91294A537)
  per Instinct; 18-8 stainless was allowed by the request. Material and strength differ from the M4 x 40 (see notes).
- **STEP header:** AP214, SolidWorks 2024 (SwSTEP 2.0), dated 2026-11-06T06:24:58, organisation "McMaster Carr Supply", comments
  "Part Number: 92125A221", "Material: 18-8 Stainless Steel", "(c) 2026 McMaster-Carr Supply Company". Consistent with an official McMaster CAD file.
- **Drawing:** not McMaster's original PDF. A 1-page wrapper around one embedded 1050x811 raster, made by Instinct (/Title `92125A221__datasheet`,
  CreationDate 2026-11-21 23:52Z). The raster is the McMaster dimensioned drawing (title block part number 92125A221).
- **PDF safety** (pypdf full object walk): no JavaScript, JS, OpenAction, AA, Launch, EmbeddedFile(s), RichMedia, XFA, AcroForm, URI, SubmitForm,
  GoToR or ImportData keys. Not encrypted. No text layer.

## Geometry vs drawing (build123d 0.13.0, python -I)

| Item | Wanted (REQ-022) | Drawing | STEP (measured) | Result |
|---|---|---|---|---|
| Solids | - | - | 1, valid (BRepCheck valid) | ok |
| Head diameter | about 8 | 8 mm | 8.000 (with a 0.115 mm cylindrical land at the top edge) | match |
| Head height | about 2.2 to 2.5 | 2.3 mm | 2.300 (head top to the cone/shank junction) | match |
| Countersink angle | 90 deg | 90 deg | head cone semi-angle 45.000 deg, so 90.000 included | match |
| Overall length (head top to tip) | 60 | 60 mm | 60.000 (bbox 8 x 8 x 60, axis Z, head top at z=+30, tip at z=-30) | match |
| Thread | M4 x 0.7 | M4 x 0.7 mm, 4 mm | modelled helical thread: major 4.000, minor 3.091, pitch 0.700 (point-in-solid scan along r=1.9); constant section 9.953 mm2 from just under the head (2.35) to the tip, i.e. fully threaded; tip chamfer about 0.5 x 45 deg | match |
| Hex socket | 2.5 | 2.5 mm | 6 flats at 1.250 from the axis, so 2.500 across flats; flat bottom 1.61 deep; 0.19 x 45 deg mouth chamfer | match |
| Volume | - | - | 631.43 mm3 | - |

Result: the STEP matches the drawing and the request on every checked dimension.

Notes:
- The STEP has 348 faces; 156 of them are degenerate zero-area planar slivers (total area 9e-7 mm2, all clustered at one point inside the shank at
  x -0.29, y -0.86, z -6.70, i.e. 36.7 mm below the head top). The solid is still valid and the volume is right; harmless for import, but a strict
  mesher may trip on them (same pattern as the McMaster spacer in instinct_REQ-019).
- Modelled minor diameter 3.091 is slightly below the ISO M4 external basic minor (d3 about 3.14); it is McMaster's cosmetic thread model, not a
  measured part. Use it for visuals and clearances, not thread-strength checks.
- Head: McMaster draws dk = 8.0 mm. The catalogue's recalled ISO 10642 table (`CSK` in mechloop/parts/__init__.py) uses dk actual max 7.53 and
  theoretical 8.96 for M4; the 8.0 is between them. Not changed here.
- Material: 18-8 stainless (Instinct: 70 ksi tensile, roughly class A2-70). `fhcs()` rates proof load as 0.8 x the 12.9 value; that is
  optimistic for this stainless screw. Not changed here (no design or catalogue code edited); flagged for the owner.
- Fit to REQ-022: **meets the request** (M4 x 0.7 x 60, 90 deg flat head, ISO 10642 / DIN 7991, 2.5 hex, 18-8 allowed). Not the same family as
  FHCS-M4x40 (91294A204, black-oxide alloy steel), which has no 60 mm size per Instinct.
