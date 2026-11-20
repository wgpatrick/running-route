# instinct_REQ-013: build1 queue refresh (Schurter, Misumi, McMaster, Raspberry Pi, Eddy Duo, Quarton, Cantherm/Semitec/Omron)

Ingested 2026-11-20 (folder state at about 15:15Z). Drive folder `mechloop handoff/results/REQ-013-build1-queue-refresh` (15LKAJDQN7rX38zy_DSCVmA9h3BzBjwIv)
holds 23 files: RESULT.md plus 22 deliverables, created 14:27:51Z to 15:10:43Z. A folder listing found nothing else. Each file was
downloaded into its own empty directory in scratchpad `ingest_req013/<name>/`, and every size matches Drive. Everything is
untrusted data and staged for review only: nothing went to `vendor_cad/inbox/` and nothing is committed. Checks ran with
`.venv/bin/python -I`, using scripts kept in a separate scratchpad directory (`scripts13/stepck.py`, `faces.py`, `bigbbox.py`,
`emb.py`, plus the earlier `scripts/pdfscan_b3.py` and `pdfstruct_b3.py`).

RESULT.md (11zPs7IGKw2-44Di7ERwitIclD__sz6sQ, 15:10:43Z, 7,767 B) is staged as `RESULT_instinct_REQ-013_2026-11-20.md`
(sha256 6918ff088c5d8c4440c5e7a56b9d4cac315fb770b2653abe2d52225e97976ac3). Instinct's STATUS is **partial**: P1 items 1, 2, 4, 6
and 7 delivered, item 3 facts only, item 5 official-store price only, P2 items 8-11 pending. It also covers REQ-013b (the 24T
P-bore check and the 20T two-set-screw pulley search). Instinct reports that nothing was purchased.

## Files staged here (STEP)

All are plain ISO-10303-21 AP214 text, complete (each ends with END-ISO-10303-21), and import cleanly in build123d. None contains a
URL except the McMaster file, which has only mcmaster.com terms and part links.

| Delivered as (Drive id, size) | Staged as | sha256 | Header / content |
|---|---|---|---|
| 4301.1405__cad.step (1FQ_YqahnAFh3Oq_btmcuL4SQxyW-zBwl, 6,006,141 B) | Schurter_4301.1405.step | 7009b4d51d09d4b90366a169da135c378615f9bd2aff29c24980fc37dd8393fb | SolidWorks 2017, 2020-11-16, product `FD2-finger-1pol-WVS-03`; 1 solid |
| HBLFSN5__cad.step (1T5RK9CySVLeHxf6AhvKCfIHvXgl3I3y-, 157,476 B) | Misumi_HBLFSN5.step | a2a85ab81fd7e0fbf560e0fb28f907b94fbafe8009e76c5a33d8147c991ad1b9 | SolidWorks 2016 / SwSTEP 2.0 (Misumi generator, 2026-10-23); 1 solid |
| HBLFSN5-SEP__cad.step (1H-wIxHH6SNPPfpDzHUltDjpLmSVXDW1i, 320,761 B) | Misumi_HBLFSN5-SEP.step | 6b9b21959abe422a9b0e53f6bef281a612adb93afdcc6c5b05491a9bd4f32c11 | bracket + 2 screws + 2 nuts, 5 solids |
| HNTP5-5__cad.step (1tQY3GtZN__kgglSSOpD-1CqBOPsRE_gP, 74,923 B) | Misumi_HNTP5-5.step | d5594372504705dc01447718a846592c47383777a885eae8daefc6c7a9805f4a | 1 solid |
| CBM5-10__cad.step (13L0EZcg9AW1jrlXsnkuH3H2rQrN8nzcN, 38,485 B) | Misumi_CBM5-10.step | 7fac7a86d0c69963c0714d3931148d189f2048393741b20a5735e9395073d681 | 1 solid; **see the flag below** |
| AGTFW30-GT2090-5__cad.step (1rX1XIpSXMvXW1v-tUrMrCgVhcLk8qZ4P, 384,381 B) | Misumi_AGTFW30-GT2090-5.step | a2db60bf957974ad06081717f28a5c2c8015d4304bb6fd0c40536de9c520a6d4 | idler + 2 flanges + 2 bearings, 5 solids |
| GPA32GT2090-A-P5__cad.step (1OLgy6kQkx90m5mh-op_BcQRxAEEpTYfI, 477,652 B) | Misumi_GPA32GT2090-A-P5.step | 5d31ec3068f6fab36059fba4a10ec83d058a8beee33700419ace63b360b4a348 | pulley + 2 flanges + 2 set screws, 5 solids |
| GPA32GT2090-B-P5__cad.step (1ZGQ4wIbYkfRuSom6MIW2oEzLezhvdNAS, 438,746 B) | Misumi_GPA32GT2090-B-P5.step | 4709058efc3a466271085c538c7216364558a7a14b836f88c297dded732a8df6 | pulley + 2 flanges + 2 set screws, 5 solids |
| 3684N13__cad.step (1Kx1PJIGU__xxoKpVY-IOSvP9cm-rl40T, 1,455,421 B) | McMaster_3684N13.step | 223dbc93c13257a97eb6d2f88f15067079e89054f9873bd42edb803cff2596aa | SolidWorks 2024, 2026-11-05, author "McMaster Carr Supply"; pulley + 2 set screws, 3 solids |

## Documents (PDF / JPG)

PDF checks: none of the 11 PDFs has JavaScript, Launch, RichMedia, XFA or SubmitForm in the object graph or in inflated streams.
The `/JS` hit in SC1432 comes from compressed image data, not an action (same file as already checked in REQ-002). The
OpenActions in SC1153, SC1223 and D2F-01L are plain `/GoTo` page-fit actions. **D2F-01L** is encrypted with an owner password
only (empty user password; restricts editing) and has **one embedded file**: `OMRON_IAB_catalog-High(1).joboptions` (3,940 B),
an Adobe Distiller settings text, which is harmless. That PDF was not copied anyway, because it duplicates a file already in the repo.

| Delivered as (Drive id, size) | Kept as | sha256 | Note |
|---|---|---|---|
| 4301.1405__datasheet.pdf (1Eyvs5p0juAFeVTd-20NBPHlZkl27qLyz, 324,460 B) | not copied: same bytes as `vendor_docs/Schurter_Fusedrawer-2_4301.1401_datasheet.pdf` | b43d13b3e6ee7a18d1094d2499a2856a71a9d2e54dd32de238e92572178bf34c | Fusedrawer 2, 6 p; lists 4301.1405 = Fingergrip, 1-pole, no voltage selector, PU 50. **No dimension drawing in it** |
| AGTFW30-GT2090-5__datasheet.pdf (144wHBEM7fuuqfLrQHgu3P52HkiwQWsDT, 340,142 B) | vendor_docs/Misumi_AGTFW_flanged-idlers-with-teeth_catalog_p1424-1425.pdf | 3532438f018cc324d844cbb7d169a7e48a481d88d6dba30546066201b1ba6562 | Misumi catalogue pp. 1424-1425 |
| 3684N13__drawing.pdf (17HxNwwJ-v31MYUpz0IHO7Ylw5oqqHdc1, 150,030 B) | vendor_docs/McMaster_3684N13_drawing.pdf | 17473ed11824019b18ea5aef71b518d7d55481fa9d92f336c659dd1223110392 | SolidWorks PDF, **1 page** (Instinct says 4 pages) |
| SC1432__drawing.pdf (1cmnh1hiGXldqMv0WGb0hE-ZPmePuvQOw, 174,949 B) | not copied: same as `vendor_docs/RaspberryPi_Pi5_mechanical_drawing.pdf` | 5dd680d6c1f5e7aa9c7b020695e315d04aac862df82ff01d4e9041cd0668d7f2 | Pi 5 drawing (85 x 56, checked in REQ-002) |
| SC1148__drawing.pdf (1Pst3kHg-0knihkucMZwAM3txriiiZIMp, 233,138 B) | vendor_docs/RaspberryPi_Active-Cooler_SC1148_mechanical_drawing.pdf | 3cc3bccc4b58d0690c2b18251cffc3863091305c32fd5d198f152722ba2bd09f | new; the repo had only the Active Cooler product brief |
| SC1153__datasheet.pdf (1eUzIuahNzfEu9I9gj2fuO4pGCsLXs5n8, 1,233,433 B) | not copied: same as `vendor_docs/RaspberryPi_27W-USB-C-PSU_product_brief.pdf` | d5b4cc0d9724b7e917f29a76155d1f049802ed86e4d806990aee099ab91f66a9 | |
| SC1223__datasheet.pdf (1bUOrT19gmH33jhmZMAgRQtH3lTCEZiPu, 1,244,344 B) | not copied: same as `vendor_docs/RaspberryPi_Camera-Module-3_product_brief.pdf` | 578efcad6337696a29b9c068815a01d63ddcf7beacf584051d61cf1cddeeaf0a | the repo already has CM3 std and wide mechanical drawings, which Instinct says do not exist on the portal |
| EDDY-DUO__drawing.jpg (1xSw-uvAkasNQkazVN-CM7CznvMRw0PRB, 58,592 B) | not copied: same as `vendor_docs/BTT_Eddy_dimensions.jpg` | 7a5bcae8e13c4ee4d085ca0d830176c1f64d7f0311f8588e8b02df549e911345 | 18.30 W x 33.79 H x 15.30/18.30 D; 2 x Ø3.15 at 10.50 |
| VLM-520-56-LPO-D30-F10__datasheet.pdf (145BHsPihkMcremUFhk-IuzFxHXTUpJCm, 1,183,645 B) | vendor_docs/Quarton_VLM-520-56-30deg-series_manual.pdf | 1f58e98d032a9c8bd4bbea97de9db55b5d6ff5187eba5659141db9186d8dde09 | 7 p, green 30° line laser series |
| CS712025Y__datasheet.pdf (1fTAdX50EgbC7P9ydgZogiR3sCWkcpB-E, 1,392,761 B) | vendor_docs/Cantherm_R53_CS712025Y_datasheet_rev2017-04.pdf | aa05d0c4e5acc34d8001efc8a3abace705e4b97f9d04402f3e3f34fd262b61fd | R53/R54/R55, 4 p, ModDate 2017-04-13. A **newer revision** of `vendor_docs/Cantherm_CS7_R53_thermostat_datasheet.pdf` (2015-04-06); both kept |
| 104NT-4-R025H42G__datasheet.pdf (1sdqUn-xpdYox-SQWpIRtOi4laBlrIFSb, 96,355 B) | not copied: same as `vendor_docs/Semitec_NT-4_thermistor_datasheet.pdf` | d328aac1548d144f7d4f27931a7aaf73f7c2459d3c5aef3260edf619b100ad0a | |
| D2F-01L__datasheet.pdf (1492bLgym35NMwQ0j7GqsczDz3_2Qz7a9, 850,668 B) | not copied: same as `vendor_docs/ENDSTOP-MICRO_datasheet.pdf` | d3f2ed08101cf7ec6f57577643225f73faa5475026dda0072bcddf2d99fb04db | encrypted (owner password) + joboptions attachment, see above |

## Geometry checks (build123d; all solids valid)

| Part | Reference | STEP result | Verdict |
|---|---|---|---|
| HBLFSN5 | REQ: 30 x 30 legs, 20 wide, 4.5 thick, 3 x Ø5.3 | legs 0-30 on both axes, width 20.0, inner faces at 4.5, **3 x Ø5.3** (2 on one leg at 10.5 / 18.0, 1 on the other at 18.0); two 6 x 1 mm slot tabs on the back faces make the bbox 31 x 31 x 20; vol 6,196 mm³ | **match** |
| HBLFSN5-SEP | same bracket + hardware | bracket solid identical (vol 6,196.45) + 2 screws (15 x 8.5 dia, M5) + 2 nuts (= HNTP5-5 geometry); bbox 36 x 36 x 20 | match (assembly) |
| HNTP5-5 | Misumi catalogue 2019 p. 2716 (`vendor_docs/misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf`): L 17, width 8.3, M5 | 17.0 x 8.3 x 4.7, M5 tapped hole (Ø4.134 minor), vol 350.8 | **match** on L / width / thread. Height not checked: the catalogue text gives 3.2 / 5.8 / 6.5 without labels. Spring not modelled separately |
| CBM5-10 | REQ: M5 x 10 **socket button head** (ISO 7380: head Ø9.5, height 2.75, 3 mm hex) | head **Ø8.5 x 5.0 cylindrical** (0.5 x 45° top chamfer), **4 mm hex** x 2.5 deep, shank Ø5 x 10 (thread not modelled) | **MISMATCH**: the geometry is a standard socket head cap screw (ISO 4762 M5: Ø8.5 x 5, s 4), not a button head. Either CBM is not Misumi's button-head code, or the wrong part was ordered. Check the part number before use |
| AGTFW30-GT2090-5 | Misumi p. 1425: 30T, P.D. 19.10, O.D. 18.59, F 24, E 15, A 10.0, W 13.3, Dh 7, 675ZZ x 2, d 5 | tooth tips Ø18.59 (30), flanges Ø24.0 x 1.62, E Ø15, W 13.30, flange gap 10.06, Ø7, bearings 8 x 2.5 (x2), bore Ø5.0 | **match** |
| GPA32GT2090-A-P5 | Misumi GPA page (`vendor_docs/Misumi_GPA_GT2090_..._p1340.pdf`): 32T 2GT P.D. 20.37, O.D. 19.86, d 5 with M3 set screws (M3 x 3) | O.D. Ø19.86, flanges Ø25 x 1.65, W 13.3 (gap 10.0), bore Ø5.0, **2 x M3 tapped holes** (Ø2.459 minor) 120° apart through the tooth body + 2 M3 x 3 set screws | **match**; set-screw taps present |
| GPA32GT2090-B-P5 | as above, B shape (hub) | as A plus hub Ø13; overall 21.0; 2 x M3 taps 120° apart + 2 set screws | **match**; set-screw taps present |
| 3684N13 | McMaster drawing: 20T GT2, P.D. 12.22, Ø15, 20 overall, 12.2 / 11, 5 bore, 9 mm belt | P.D. Ø12.22 (20 teeth), Ø15 OD, 20.0 overall (hub 7.8 + teeth 11.0 + flange 1.2 = 12.2 to the hub face), bore Ø5.0, **one flange** plus the hub. **2 radial M4 tapped holes 90° apart with 2 set-screw solids** | **match on all dimensions. Set screws: the STEP has TWO** (at +X and +Y, both in the hub). The drawing's iso view also shows two sockets. Instinct's "ONE set screw" is **wrong**. 3684N13 appears to meet the requested two-set-screw spec. Confirm on the McMaster page |
| Schurter 4301.1405 | datasheet: Fusedrawer 2, 5 x 20, Fingergrip, 1-pole, no voltage selector (no dimensioned drawing in it) | product name `FD2-finger-1pol-WVS-03` (Fingergrip, 1-pole, without voltage selector); bbox 24.65 x 22.85 x 12.25; vol 2,986 | **type matches. Dimensions not verified**: there is no drawing to compare against. Instinct's model name "FD2-010-10-00" does not appear in the file |

## Large files (step 3 of the ingest)

- **BTT Eddy STEP**: fetched from https://raw.githubusercontent.com/bigtreetech/Eddy/master/3D/EDDY.STEP. It is public, HTTP 200 and
  47,718,616 B; `/main/` returns 404. sha256 466845364ae965fd4718ad77b58edf934351f4ba7c8f53696a13df0ba5710a25 is **byte-identical**
  to the already staged `vendor_cad/staging/BTT_EDDY.STEP.gz` (gunzipped, same sha), so nothing new was added. The scratch copy is
  at scratchpad `ingest_req013/_fetch_eddy/EDDY.STEP`. build123d imports it as **surfaces only (0 solids)**. Its overall bbox is
  18.10 x 33.79 x 18.30, against the drawing's 18.30 x 33.79 x 18.30, so it matches to within 0.2 mm. The single repo file covers
  Eddy / Eddy Duo (same housing drawing).
- **Raspberry Pi 5 STEP**: not fetched. pip.raspberrypi.com is refused by this session's network proxy (CONNECT 403 on /, robots.txt
  and the category page). That counts as blocked, so it was not worked around. Instinct reports 13.3 MB zipped / 77.6 MB raw.

## Instinct-stated provenance and prices (as stated, not verified)

- 4301.1405: schurter.com CAD portal. Misumi STEPs: logged-in MISUMI USA account. AGTFW30-GT2090-5 is $41.41 (1-9), $28.36 (10+),
  ships Nov 30. GPA32GT2090-B-P5 is $33.37 (1-15) and GPA32GT2090-A-P5 $28.25 (1-15), both shipping Nov 30. Misumi has no 20T or
  24T P bore (P starts at 32T).
- 3684N13: McMaster, $5.99, in stock, origin China. HIWIN MGN12H 295 mm set (Motion Constrained): $79.64 (1 block) / $103.31
  (2 blocks), no STEP.
- Eddy Duo: biqu.equipment $26.63 sale ($33.99 regular). VLM-520-56 LPO-D30-F10: Digi-Key $98.40 (1), 0 in stock, 4 wk lead time.
- Omron 3D CAD needs an aratas.com account, which was not created.
- Item 12 (PCBWay RP03 qty-10 price): unavailable.

## Flags

1. CBM5-10 is not a button head (see the table).
2. 3684N13 has two set screws, against Instinct's "one".
3. The Schurter drawer's dimensions cannot be verified from the delivered datasheet.
4. Instinct calls the McMaster drawing 4 pages; it is 1 page.
5. 7 of 13 documents duplicate files already in vendor_docs.
6. D2F-01L PDF: owner-password encryption and a Distiller joboptions attachment (harmless; not copied).
7. Pi 5 STEP blocked by the proxy.

## 2026-11-20 batch 12 (ingested about 16:15Z)

Four new files in the REQ-013 folder (15LKAJDQN7rX38zy_DSCVmA9h3BzBjwIv), fetched by Drive id only (folder not re-listed).
Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed. Same PDF checks (raw and inflated-stream scan plus a pypdf
walk).

| Delivered as (Drive id, modified, size) | Disposition | sha256 |
|---|---|---|
| RESULT.md (1Mz6RgneOs-56AsUrBrxJvua1exKPuwvf, new file id, 2026-11-20T15:50:42.988Z, 11,198 B) | staged as RESULT_instinct_REQ-013_2026-11-20_1550Z.md | 3c717a1cd1bf158e7eb209d0029dfff4512aaadda9b6d9ae2899000b2b74950a |
| 39-01-2020__drawing.pdf (1tUfLo3vKrz2DQeTLmzWDruqadlq7snRY, 15:46:38.132Z, 201,853 B) | **byte-identical** to vendor_docs/Molex_39-01-2020_drawing.pdf; not copied | 006bb06a775c0100f3184a02d0aa9e6cc09caf77630144b19a7b5f15ae5b2386 |
| ADXL345__drawing.pdf (1vQQxaNUP2wW9YaDR-InKrA63_RItCs65, 15:45:01.346Z, 218,804 B) | **not copied**: contains JavaScript (see below) | 8a4129376ddb017c14b56c1bfd1fed67e4ecfd38ef93e9a7ce66a7a3eff81811 |
| LL2MR09__datasheet.pdf (1od93b3guxet2MzgxMI_L32oKsSR6n1B-, 15:44:22.741Z, 184,552 B) | vendor_docs/Gates_LPP-manual_2mm-GT3_long-length_extract_for_LL2MR09.pdf | 694d76e7a020f73bcdbb6401aec6c0bd18b4de9580ce33498bcf892724436423 |

RESULT.md changes against the 15:10Z version: item 5 is now DONE (adds US resellers: TH3D $34.99, in stock; Fabreeko $26.99,
out of stock). P2 items 9, 10 and 11 are PARTIAL:
- item 9: the Molex drawing. JST XH CAD sits behind a licence and personal-data form, which was not accepted. Century Spring
  DJ-8X20YCS page specs (max about 440 F). Phoenix NS 35/7.5 confirmed, but its STEP and datasheet are behind TraceParts or a
  captcha.
- item 10: the Gates extract, the ADXL345 drawing, and the ADXL345 STEP noted as 38.7 MB. The COB strip is not started.
- item 11: Arducam shipping policy only, no $ cost.
Item 12 (PCBWay qty-10 price) is still unavailable. These are Instinct's statements, as stated.

Checks:
- **ADXL345 drawing**: same sha256 as the BTT-ADXL345-V2.0__drawing.pdf already rejected under instinct_REQ-003. It is an
  Altium / llPDFLib export with a document /Names JavaScript tree (`_FindWord`, `_HighlightRect`) and 432 bookmark
  `_FindWord(n, "REF")` actions. There is no OpenAction, AA, Launch, URI or embedded file. The script is benign but fails the
  no-JavaScript rule, so it stays only in the scratch dir. Rendered for viewing only: 28.25 / 20.50 / 15.50 / 2.50 dimensions,
  board height 15.50.
- **Gates extract**: 4 pages of the Light Power and Precision Drive Design Manual (InDesign 2014, modified 2020). No JavaScript,
  actions or embedded files. The pages cover the 2mm GT3 width table (9 mm multiplier 1.64), long-length belting (LL2MGT09:
  9 mm, 190 lb, 50 ft minimum) and tolerances (long-length width +0.8 / -1.2 mm). It is apparently a page subset of
  vendor_docs/Gates_GT2_design_manual.pdf (same title; 112 p). **The code "LL2MR09" / "2MR" does not appear in the extract**,
  which uses the older 2MGT / GT3 naming. The LL2MR09 page itself is vendor_docs/Gates_LL2MR09_page_2026-11-20.pdf.
- **Molex drawing**: 2 p, pdftk / iText. No JavaScript, actions or embedded files.

### BTT ADXL345 V2.0 STEP, fetched directly

https://raw.githubusercontent.com/bigtreetech/ADXL345/master/3D/BIGTREETECH%20ADXL345%20V2.0.step returned HTTP 200 with
38,703,630 B. `/main/` returned 404. sha256 bd7c069e0e9506b13ecbeb22e8e79006ae3a1bc49f61c89460195afad9ffa76b is
**byte-identical** to the STEP inside the already staged `../instinct_REQ-003/BTT-ADXL345-V2.0__step.zip`, which confirms that
zip's provenance. gzip -9 would be 6,039,257 B (under 15 MB), but it was **not staged** because it duplicates the REQ-003 zip.
The scratch copy is at scratchpad `ingest_b12/_fetch_adxl345/BIGTREETECH_ADXL345_V2.0.step`. build123d: 735 solids, all valid;
bbox 34.68 x 16.56 x 4.27 (USB-C overhang); volume 406.97 mm3. Against the drawing, the board height 15.50 **matches** (PCB
solid 33.25 x 15.50, per REQ-003). The drawing's 28.25 / 20.50 / 2.50 are feature positions; the board length is not
dimensioned. Result: PASS (reference CAD).

### Flags
1. Item 013b-2 in RESULT.md still says 3684N13 has ONE set screw. The staged STEP has two (see the batch 11 flag).
2. The Gates extract does not name LL2MR09 / 2MR (see above).
3. The ADXL345 drawing was re-delivered unchanged with JavaScript. A JavaScript-free copy is still needed if the drawing is wanted.

## 2026-11-20 batch 13 (ingested about 17:15Z)

Source: REQ-013 results folder 15LKAJDQN7rX38zy_DSCVmA9h3BzBjwIv. Each file was downloaded into its own scratch dir and read
with `python3 -I`. The PDFs were checked for JavaScript, Launch, OpenAction/AA, AcroForm/XFA and embedded files: **none found in
any of them**. The only actions are /URI links (phoenixcontact.com product page; klusdesign.com and a mailto).

| Drive file (id, modifiedTime, size) | Destination | sha256 |
|---|---|---|
| RESULT.md (1F4XTfDRpBYiwztAlOPoNon5wYjyCR87R, updated 17:10Z, 15,679 B) | RESULT_instinct_REQ-013_2026-11-20_1710Z.md | f8116da4ba29fec1353a8a3134bc03d46829cd3a87c071a1a572c4edecd5bf2d |
| 0801733__datasheet.pdf (1UuRHPUsdOL9JQVgjPWri3sZEN5DByDQL, 50,066 B) | vendor_docs/Phoenix_0801733_NS35-7.5-PERF_datasheet.pdf | bc2ca91f634476971e3bbe30dd9693173cc89931c2605f545644a2e76b04ca97 |
| PDS-4-ALU__datasheet.pdf (1RL1e-jhoWPxMZt98RUXgKA2TFJ8SYROZ, 569,880 B) | vendor_docs/KLUS_PDS-4-ALU_A01718_datasheet.pdf | e5201d8c67b61cc93a4f9c282cac737bbf568fc918d3b8a6789e892e5c4af7cd |
| 24V-COB-4000K__datasheet.pdf (1ZNsCGivzeBH7k41iXCzE-cv6K-MxhGZR, 312,523 B) | **not copied**: byte-identical to vendor_docs/InspiredLED_24V-COB_flex_spec.pdf (third delivery; see REQ-003) | 2b0101b9fa993922d896d5d315f1fd020eddc4f321a8fdb9060f6504111ecef8 |

### Stated provenance (Instinct's statements, not verified)
- 0801733: the official Phoenix Contact catalog-generated datasheet, "mirrored on Octopart". The direct phoenixcontact.com
  download sits behind Friendly Captcha. Instinct says the captcha flow downloaded the file and the STEP (AP203/214/242,
  loginRequired=false) into the remote browser, but the bytes could not be retrieved from there (direct URL 403).
- PDS-4-ALU: the official KLUS product datasheet.
- 24V-COB-4000K: Inspired LED spec 2.0, via DigiKey media.

### Key specs (from the datasheets)
- **Phoenix Contact 0801733, NS 35/7.5 PERF 2000MM**: perforated DIN rail, EN 60715 standard profile. 35 mm wide, 7.5 mm high,
  2000 mm long. Drawing: 1 mm material, 27 mm inner width. Slots are 15.00 x 6.20 mm at a 25.00 mm pitch. Steel, galvanized and
  thickly passivated, silver. Packing unit **5 pc**, GTIN 4017918006686. PDF from Apache FOP, catalog print dated 2019-05-16.
- **Inspired LED 24V COB Flex, 4000K "Pure White"** (DigiKey 24V-COB-4000K-12M, Inspired LED code 265216 on the sheet): 24 VDC,
  480 LED/m (144/ft), **CRI 91**, 3.15 W/ft (about **10.3 W/m**), 340 lm/ft. **8 mm** wide, cut every **1.97 in (50 mm, 24 LEDs)**,
  12 m reels or pre-cut lengths, 3M adhesive. Maximum run on a 96 W supply is 292 in; feed from the centre beyond about 130 in.
- **KLUS PDS-4-ALU extrusion, ref A01718**: aluminium, white lacquered, rectangular. **0.6 in wide x 0.5 in high** (about
  15 x 13 mm; the sheet gives inch values only). LED gluing (inner) width **0.4 in (about 10 mm)**, 1 strip up to 0.31 in (8 mm)
  wide. Glow width 11.2 mm. Max 7.3 W/ft. Bendable: 150 mm inward, 350 mm outward. Lengths 39.4 in (A01718L10NS_1) and 78.9 in
  (A01718L10NS_2). Covers are sold separately: LIGER-11 (B17037S satin, 59 %), HS-11 (B17208F frosted, 59 %), KA-11 (B17064F
  frosted, 67 %). PDF made with wkhtmltopdf on 2026-04-29. Publisher: KLUS LLC, Vero Beach FL.

### US seller / price / stock (as Instinct states)
- LED strip: DigiKey 24V-COB-4000K-12M. **Price and stock not captured** (DigiKey blocked the sandbox fetch).
- Channel: "US stock via superbrightleds.com (PDS-4 Plus)". **Price and stock not captured.**
- DIN rail: no price. RESULT says "pack of 25".

### RESULT.md, 17:10Z against 15:50Z
- STATUS line rewritten (item 8 candidates; item 9 datasheet delivered, STEPs held; item 10 datasheets delivered; item 11 needs an address).
- **Item 8 (bed heater and PEI kit): "not started" is now DONE (research), but it is partial on the requirements.**
  - Heater: Keenovo 200-24-0-0-3M-200x200 (24 V, 200 W, 200x200, NTC 100K, 3M adhesive, optional 150 C thermostat). Its
    part page is cited on keenovo.ru. **No US stock at 24 V.** US resellers stock only 110/120 V variants (KB-3D $44.39, 4 in
    stock; West3D $44.99 for 120 V 500 W and $39.99 for 110 V 200 W, both in stock), which Instinct labels a voltage mismatch.
  - PEI: HoneyBadger P-Series Gen 2 220x220 textured, from consum3d.com, $24.99, 12 in stock, rated to 120 C. Wham Bam 220
    (base $26, rated 150 C) is sold out, and its plate ($35) is out of stock. Fulament was unreachable.
- Item 9: the Molex STEP is held because TraceParts needs a registration. The Phoenix datasheet was delivered; its STEP is held
  (see provenance). JST XH is still held behind its licence and personal-data form, unchanged.
- Item 10: the COB strip and KLUS channel lines were added (above).
- "Still open" list rewritten. The item 5 reseller text there was already in the 15:50Z body (batch 12). RP04 and belt sellers
  are not mentioned in the diff.

### Flags
1. The channel datasheet is PDS-4-**ALU** (A01718), but the stated US stock is "PDS-4 **Plus**" at superbrightleds.com. That is a
   different extrusion (A01263, listed by the sheet as a "similar extrusion"). Stock for the actual pick is unconfirmed.
2. The DIN rail packing is 25 in RESULT.md but **5 pc** in the datasheet. "Current revision" in RESULT.md, but the catalog print
   is dated 2019.
3. The COB datasheet was delivered for the third time, unchanged. No price yet.
4. Instinct says the Phoenix captcha flow auto-solved and downloaded files into the remote browser. Nothing was registered and
   no terms were accepted, per Instinct.
5. The Keenovo part page is on keenovo.ru, not keenovo.com, and the 24 V part has no US stock.
