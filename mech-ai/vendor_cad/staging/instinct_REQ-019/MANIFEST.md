# instinct_REQ-019: stock M5 spacer (wanted about 10 OD, 5.1 to 5.3 bore, 10 long, aluminium, unthreaded)

Ingested 2026-11-21 (batch 18, about 01:15Z). Drive folder `REQ-019-m5-spacer` (1SmfNo_qxoAv9bozvZ9X_EJO-rnPIY3kR).
Fetched by Drive id only. Each file went into its own empty scratch directory and was read with `python -I`.
Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed. Instinct's STATUS: **done** (2 candidates, no purchase).

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1f9mY5XHHlE1nnYeuQNNEw5JRUbQCWqhF, 4,035 B) | RESULT_instinct_REQ-019_2026-11-21.md | 9a8002c633ef6c7aae42d324f35d7e589c7e8adff60aed1ad90dc711bcceea09 |
| 94669A079__cad.step (1LQ1C0ngNR8njC0hsdEaOISxO-axMimv_, 264,576 B) | McMaster_94669A079_Al_spacer_M5_10OD_5.3ID_10L.step | c0f7992bf6f31f398c8a885abf17637f8e16a676ed68c17bc1202464c68cf0eb |
| FWSA-D10-V5.5-T10__cad.step (1XZwUqlxEC9QQdqJKak3vEde7FaB6BTFM, 15,931 B) | Misumi_FWSA-D10-V5.5-T10_Al_spacer_10OD_5.5ID_10L.step | ea195decc39c746105944eb2069b50c8b8ca8bd7cc0584828acef542b2eb27a7 |
| 94669A079__datasheet.pdf (1w52ZIUGEAGZo9_xPdupGiptt2MStPjG6, 51,329 B) | vendor_docs/McMaster_94669A079_Al_spacer_M5_10x10_drawing.pdf | e752618932741e84debeaf3d36925e9608faf1e3b935f14081132aceff70a72a |
| FWSA-D10-V5.5-T10__datasheet.pdf (1uJeLIuP4vkSPE50VOgEJxc3x1t-VC9uq, 44,383 B) | vendor_docs/Misumi_FWSA_plain-spacer_series_drawing_capture.pdf | f3fc034d22f2318c935a60c911bb00e269ad82a89e28d5afcf3462454ae267df |

## Stated provenance, price and availability (per Instinct, not verified; as displayed 2026-11-20 about 16:30 to 16:45 PT, USD)
- **McMaster-Carr 94669A079**, aluminium unthreaded spacer, 10 mm OD, 10 mm long, for M5. $2.53 each (1-24), $2.15 (25-99), $1.87 (100+).
  "Delivers Monday by 5 pm"; no numeric stock count shown. Page https://www.mcmaster.com/94669A079/
- **MISUMI FWSA-D10-V5.5-T10**, configurable plain aluminium spacer, standard grade (page says 2000-series Al alloy). $2.03 each (1-9),
  $1.72 (10-19), $1.10 (50+). Ship date Mon Nov 30, 2026: made to order, not stock. ID only in 0.5 mm steps, so 5.3 is not offered.
  Page https://us.misumi-ec.com/vona2/detail/110300231910/?HissuCode=FWSA-D10-V5.5-T10
- **STEP headers.** McMaster: AP214, SolidWorks 2024, dated 2026-11-06, comments "Material: Aluminum", "(c) 2026 McMaster-Carr Supply Company".
  Misumi: AP214, SolidWorks 2016, dated 2026-11-21T00:43:08, author "EC2", organisation "Amazon.com" (looks like MISUMI's cloud CAD generator on AWS, not a
  third-party source; noted as odd), no material or vendor comment in the file.
- **Drawings.** Neither PDF is the vendor's original. Each is a 1-page wrapper around one embedded raster, made by Instinct (/Title `<PN>__datasheet`,
  CreationDate 2026-11-21 00:34Z and 00:45Z). McMaster: 1050x811 image of the McMaster drawing (title block "Aluminum Unthreaded Spacer", "For Screw Size: M5").
  Misumi: 515x665 screenshot of the **series** drawing (not per-configuration) plus the top of the materials table, which is cut off before the aluminium rows.
- **PDF safety** (pypdf full object walk): no JavaScript, JS, OpenAction, AA, Launch, EmbeddedFile(s), RichMedia, XFA, AcroForm, URI, SubmitForm, GoToR or
  ImportData keys. Not encrypted. No text layer.

## Geometry vs drawing (build123d, python -I)

| Item | Wanted | McMaster drawing | McMaster STEP | Misumi drawing (series + config) | Misumi STEP |
|---|---|---|---|---|---|
| Solids | - | - | 1, valid | - | 1, valid |
| OD | about 10 | 10.00 ±0.13 | 10.000 | D10, 0/-0.2 | 10.000 |
| Bore | 5.1 to 5.3 | 5.30 +0.30/0.00 (5.30 to 5.60) | 5.300 | V5.5, +0.3/+0.1 (5.6 to 5.8) | 5.500 |
| Length | 10 | 10.00 ±0.13 | 10.000 | T10, ±0.1 | 10.000 |
| Chamfers | - | shown, not dimensioned | OD 0.235 x 45 deg, bore 0.35 x 45 deg | 2-C, C0.2 or less (D 16 or less) | OD and bore 0.2 x 45 deg |
| Material | aluminium | "Aluminum" (title block) | "Aluminum" (STEP comment) | not visible: the capture's table shows only steel rows (FWS/FWAS) and is cut off | not stated |
| Volume | - | - | 560.91 mm3 (ideal tube 564.8) | - | 545.87 mm3 (ideal tube 547.8) |

Result: both STEPs match their drawings at nominal. McMaster axis is Z, centred on the origin; Misumi axis is X, from x=0 to x=10.

Notes:
- McMaster STEP has 146 faces for a plain tube: 132 of them are degenerate zero-area planar slivers (total area 7.6e-7 mm2, all within 0.15 um of one point
  inside the wall at r 3.07, z 3.93). The solid is still valid and the volume is right; harmless for import, but the faces may trip a strict mesher.
  The drawing's iso view shows a marking on the OD, which may be where they came from.
- Misumi material is taken only from Instinct's text ("2000 series aluminum alloy"). The delivered drawing capture does not show the aluminium row, and the
  visible table labels standard/precision as FWS/FWAS (steel). Confirm on the product page that FWSA is the aluminium family before ordering.
- Fit to REQ-019: **McMaster 94669A079** is the better fit. It matches 10 OD, 10 long and the 5.30 nominal bore, and it ships next business day. Its bore
  tolerance allows up to 5.60, so the 5.1 to 5.3 band is only met at nominal. Misumi's bore is 5.5 nominal (5.6 to 5.8 actual), outside the band, and it is
  made to order (Nov 30). Neither part guarantees an actual bore of 5.3 or less.
