# instinct_REQ-020: spool holder hardware (608ZZ bearing, M8 axle, nut, washer; centering sleeves pending)

Ingested 2026-11-21 (batch 19, about 02:15Z). Drive folder `REQ-020-spool-hardware` (1Hb0hdn7QnB6Aj_PTwVviq8tBm2b4Kdud).
Fetched by Drive id only. Each file went into its own empty scratch directory and was read with `python -I`.
Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed. Instinct's STATUS: **PARTIAL** (items 1, 2, 4 fulfilled;
item 3, two centering sleeves, unresolved: "search continues next run"). Nothing purchased.

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (11LCfdfQthsy8zRuW0ZokIqrrjROKQ6t4, 4,261 B) | RESULT_instinct_REQ-020_2026-11-21.md | fe8e6b3a67a3e5a34d77fa1e6368e0ca10378555b3bc656898837dd94066d004 |
| B608ZZ__cad.step (1zGzlwQyYmlqjGuVxu4V0XzRNZXt2prtN, 27,505 B) | Misumi_B608ZZ_bearing_8x22x7_ZZ.step | de78759b3dccc9bac3bb4197ed33c72d14eab6dead7d42aec477face030485de |
| SFAL8-90-B15-S15__cad.step (18KoU0RmWsmDxUEqqYr9lrhn1AYEEeFez, 8,774 B) | Misumi_SFAL8-90-B15-S15_shaft_D8_L90_M8-both-ends_120OA.step | 57de8b9f9ee6cf1775e2684f478e0d8f6f8a77a7abd6600ab438f3971cb96675 |
| 90592A022__cad.step (1mkHXZrWDxBAYAI66zcoJOUyjgZ7VYVD2, 496,969 B) | McMaster_90592A022_hex_nut_M8x1.25_13AF_6.5H.step | 4861615036c2fef0ec4bfa92bbe9b9978b43780587ee5aa6be3c16ff54e5a677 |
| WSF20__cad.step (12JsP2HmbWmeVkQG0V-1ihr1rChEctXw8, 12,845 B) | Misumi_WSF20_shaft_end_washer_20OD_8ID_5T.step | 6b57ab2d03dacb7236ff3ca17e4abe381e51a59621461ffed96db83ee7748152 |
| nsk-608zz1mc3-dimension-page.pdf (1udqtJhZUDMps8mvla5-8VNGpUs141pDV, 66,796 B) | vendor_docs/NSK_608ZZ1MC3_dimension_page_capture.pdf | 5252937d87773183b1c3e965cdd59aad14a1f5eca8be3c982e7065390a398322 |
| SFAL8-90-B15-S15__datasheet.pdf (1rMaZBe-_OehKnO4fvwXbyR19kzrxymA_, 345,391 B) | vendor_docs/Misumi_SFAL_both-ends-threaded_shaft_catalog_p228-229.pdf | 447fff1c3b2ea123acc4ae7a9c94bcd467c981cef95ef1c68e22281414f93481 |
| 90592A022__datasheet.pdf (1FAEGwU0QcP8HfeLIiVI_SaZexaRa6Lt-, 58,136 B) | vendor_docs/McMaster_90592A022_M8_hex_nut_drawing.pdf | 2104b6e3ec4967b0639b3a70a0af93d0dd3ffeffcceff4efd738f5e9c14432f1 |
| WSF20__datasheet.pdf (1-widAeU-ijcI893hxAnydqxNUpGsK_d8, 57,981 B) | vendor_docs/Misumi_WSF_linear_shaft_washer_catalog_p289_capture.pdf | e9f6a3f4852acf1283de6bd51ad0192ff60b1e2d740cef2cb1a104fd9e8db691 |

## Stated provenance, price and availability (per Instinct, not verified; as displayed 2026-11-20, USD)
- **Bearing, item 1.** Reference: NSK 608ZZ1MC3 engineering page (d 8 / D 22 / B 7, r min 0.3, Cr 3650 N, C0r 1370 N, 34,000 rpm grease, MC3, ISO normal).
  **CAD is MISUMI's own B608ZZ, not NSK-authored.** Instinct says the NSK-brand 608ZZ listing on Misumi has no CAD and 3dfindit was bot-blocked.
  Buy reference (Misumi, NSK-brand 608ZZ listing): $2.54 each (1-20), $2.16 (21-50), $2.03 (51-560); ships Sat Nov 21, 2026.
- **Axle, item 2.** MISUMI SFAL8-90-B15-S15, both ends threaded linear shaft, 52100 equivalent, g6, D 8, L 90, M8x1.25 both ends, B = S = 15.
  $37.87 each (1-4), $20.83 (5-12), $18.94 (20-49), $18.18 (50-100); ships Wed Nov 25, 2026.
- **Nut, item 2.** McMaster-Carr 90592A022, steel hex nut, medium strength, class 8, M8 x 1.25. $6.51 per pack of 100; "delivers Monday by 5 pm".
- **Washer, item 2.** MISUMI WSF20, linear shaft end-washer, 1045 equivalent, black oxide, d 8 (+0.3/+0.1), D 20 ±0.2, T 5 ±0.2. Instinct calls it a
  dimensioned candidate, not a verified fit. $3.49 each (1-7, 7 in stock, ships Sat Nov 21); 20-499 $1.44 TBD. Supersedes Instinct's earlier
  McMaster 91116A160 pick (files removed from the Drive folder; never ingested).
- **Item 3, two centering sleeves (ID fits 22 mm bearing OD, OD 50 or less): nothing delivered.** No stock part found and no "fabricate" verdict yet.
- **STEP headers.** B608ZZ: AP214, SolidWorks 2016, 2026-07-01, author "EC2" / org "Amazon.com" (MISUMI cloud CAD generator, as seen in REQ-019).
  SFAL: same generator, dated 2026-11-21T01:48:39 (generated on request). WSF20: SolidWorks 2016, 2025-11-28, author and org blank, no vendor comment.
  90592A022: SolidWorks 2024, 2026-11-08, author/org "McMaster Carr Supply", comment "Finished Material: Steel".
- **PDFs.** NSK page, nut drawing and WSF page are 1-page Instinct-made wrappers around one raster each (/Title `<name>`, CreationDate
  2026-11-21 01:43Z, 01:55Z, 02:01Z), no text layer. SFAL is a genuine MISUMI catalog spread (Adobe InDesign, 2020-09-07), pages 228-229, with text.
- **PDF safety** (pypdf full object walk): no JavaScript, JS, OpenAction, AA, Launch, EmbeddedFile(s), RichMedia, XFA, AcroForm, URI, SubmitForm, GoToR or
  ImportData keys in any of the four. Not encrypted.

## Geometry vs drawing (build123d, python -I)

All four STEPs: 1 solid each, valid. Thread geometry is not modelled on the shaft; the nut bore is modelled at 8.0.

| Part | Drawing / config | STEP | Result |
|---|---|---|---|
| B608ZZ bearing | NSK page: d 8, D 22, B 7, r min 0.3 | bore 8.000, OD 22.000, width 7.000; corner rounds 0.3 (bore/OD cylinders span x 0.3 to 6.7); shield recesses at 12.2 and 19.3 dia, 0.6 deep; axis X; vol 2094.6 mm3 | **Match** |
| SFAL8-90-B15-S15 shaft | Catalog: D 8 g6; L = plain length between threads; B, S thread lengths; overall Y = B + L + S = 15 + 90 + 15 = **120**; M8x1.25 (D 8 row: L 25-1086, B/S 7-40) | plain cylinder dia 8.000, length 120.000, axis X; 3 faces (no threads, no end chamfers modelled) | **Match to config** (simplified: threads and 0.4 chamfers not modelled). Note: the part is **120 mm overall**, not 90. |
| 90592A022 nut | McMaster drawing: 13 across flats, 6.5 thick, M8x1.25 | 13.000 AF, 14.911 across chamfered corners, 6.500 thick, bore 8.000, axis Z; vol 672.6 mm3 | **Match** |
| WSF20 washer | Catalog p289: D 20 ±0.2, d 8 +0.3/+0.1 (8.1 to 8.3), T 5 ±0.2, OD chamfer C0.5 or less (D 20+) | OD 20.000, bore 8.000, thickness 5.000, OD chamfers 0.2 x 45 deg both sides, no bore chamfer, axis X; vol 1317.0 mm3 | **Match at nominal** (bore modelled at 8.0, below the 8.1 to 8.3 tolerance band; harmless for layout) |

Notes:
- **Axle length.** If REQ-020 means about 80 to 90 mm overall, SFAL8-90-B15-S15 is 120 mm overall (90 plain + 2 x 15 thread). For 90 mm overall
  with 15 mm threads, the config would be SFAL8-60-B15-S15. Instinct's RESULT says "L=90 mm" without noting this. Check the intended axle span.
- **Washer against the 608.** NSK abutment limits: shaft abutment db max 10.5, housing abutment Db max 19. A 20 OD washer seated on the 8 mm shaft
  bears across the inner ring, shield (12.2 to 19.3) and outer ring face, so it would drag on the outer ring if clamped. Clamping only the inner
  ring needs about 10 to 10.5 OD contact (or a stepped spacer). This agrees with Instinct's own "not a verified fit" caveat.
- **Bearing CAD source.** B608ZZ is Misumi-made, same 8x22x7 ZZ envelope as NSK 608ZZ; fine for layout, not NSK-authored.
- **Item 3 still open.** Centering sleeves: no stock part and no fabricate verdict yet. Instinct says it will report next run.

---

## Batch 20 (2026-11-21, about 03:15Z): RESULT.md revision + item 3 sleeve candidate (Misumi CLBSS28-10)

Fetched by Drive id only, from the same folder (1Hb0hdn7QnB6Aj_PTwVviq8tBm2b4Kdud). Each file in its own empty scratch directory, read with `python -I`.
Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed. Instinct's STATUS is now **COMPLETE as sourcing**, with
WSF20 and CLBSS28-10 described as candidates, not verified fits. Nothing purchased.

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1YYSNmXk69nqwFNP62z9wc8uxDoLIXNR3, 5,696 B, 02:38Z) | RESULT_instinct_REQ-020_2026-11-21_0238Z.md (supersedes RESULT_instinct_REQ-020_2026-11-21.md, kept for history) | 8238370e50704b0f2e5c36af0e2dfbd3aa266a3481405ece4bfe0f5cc704455d |
| CLBSS28-10__cad.step (1PnKRH4QKa7D7-O5rTo8ImIMdC4v8BMlP, 12,880 B) | Misumi_CLBSS28-10_bearing_outer-ring_spacer_D28_d22_L10_304SS.step | 814fb734ea912c6bb228c11b78ea42d5f0ecf07e5942f3db2788dd839843a781 |
| CLBSS28-10__datasheet.pdf (1DyVSwVmYIAvHxH_uZfIlz2PGk42pKovu, 211,357 B) | vendor_docs/Misumi_CLB_bearing_spacers_inner-outer-ring_catalog_p1064-1065.pdf | 123e4773cc72c2e230cc820621d3b4a4e6913c3c27fb25bfb63ce97e8439dae7 |

**RESULT.md diff vs the 02:15Z copy.** Only two hunks: the STATUS line (PARTIAL -> COMPLETE as sourcing; L = 10 mm was Instinct's own
assumption, re-deliverable at another L) and the item 3 section ("NOT COMPLETE" -> the CLBSS28-10 candidate). Items 1, 2, 4 and Notes unchanged.
Instinct's stated data (not verified): 304 stainless, bore 22 +0.31/+0.11, OD 28 -0.1/-0.2, L 10 (3-100 in 0.1 steps, negative L tolerance);
$31.91 each (1-4), $28.71 (5-9), $22.06 (10-19), $14.77 (20-200); ships Mon Nov 30, 2026. Instinct itself flags the use as an adaptation.

**STEP header.** AP214, SolidWorks 2016 / SwSTEP 2.0, 2026-11-21T02:36:49, author "EC2" / org "Amazon.com" (MISUMI cloud CAD generator, as in
B608ZZ and SFAL). PRODUCT 'CLBSS28-10'. No material in the file.

**PDF.** Genuine MISUMI catalog spread pp. 1064-1065 "Bearing Spacers, Bearing Inner / Outer Rings" (Adobe InDesign 14.0, 2019-06-12), 1 page,
text layer present, 2 images. pypdf full object walk: no JavaScript, JS, OpenAction, AA, Launch, EmbeddedFile(s), RichMedia, XFA, AcroForm, URI,
SubmitForm, GoToR or ImportData. Not encrypted.

### Geometry vs catalog (build123d, python -I)

| Part | Catalog (outer-ring table, row D 28) | STEP | Result |
|---|---|---|---|
| CLBSS28-10 | D 28 -0.1/-0.2 (27.8-27.9), d 22 +0.3/+0.1 (22.1-22.3), Dh 23, L 10 (negative tol 0/-0.1), C0.5, 304 SS, listed for 6001ZZ / 6902ZZ | 1 valid solid; OD 28.000, bore 22.000, L 10.000, bore chamfers C0.5 both ends (23.0 at faces), no OD chamfer; axis X; vol 2338.65 mm3 | **Match at nominal** (bore modelled at 22.0, below the 22.1-22.3 band; material not in STEP, per catalog only) |

Notes:
- **What the part is.** In MISUMI's outer-ring table the part-number D is the *bearing OD / housing bore* the spacer serves. CLBSS28 is the
  outer-race spacer for 28 mm OD bearings (6001ZZ, 6902ZZ). The 608ZZ row is CLBSS22 (OD about 22, ID 17). Instinct uses CLBSS28 as a sleeve that
  slips over the 608's 22 mm OD (0.1 to 0.3 mm clearance per catalog), outside its catalog purpose.
- **Against the v12 design (turned 6061 sleeves: 10 OD at the 608 inner ring, ID 8 on the 8 mm axle, stepping to 15 OD under the front nut,
  centring a ~51-52 mm spool hub on the bearings).** CLBSS28-10 cannot replace these: its 22 bore does not sit on the 8 mm axle, it would contact
  the outer ring rather than only the inner ring, it has no 15 mm step, and its 28 OD does not reach a 51-52 hub (about 11.5-12 mm radial gap).
  It addresses the REQ text's "ID fits 22 mm bearing OD, OD <= 50" concept, not the v12 inner-ring layout.
- **Closest catalog-stock alternative on the same sheet (not delivered, no CAD).** Inner-ring table row for 608ZZ: d 8 / D 11 (Ds 10), L 1-50,
  e.g. CLBUS (304 SS) or CLBU (aluminium). It is a plain tube, so it could cover the inner-ring spacer but not the 10->15 stepped profile; its
  11 OD is above the 10 OD in v12 and above NSK's db max 10.5 noted in batch 19 (it still clears the 12.2 shield recess per the B608ZZ CAD). Not verified.
