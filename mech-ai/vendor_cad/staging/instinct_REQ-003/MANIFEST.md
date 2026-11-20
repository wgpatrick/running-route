# instinct_REQ-003: Build 1 additions

Checked 2026-11-20 (last at about 01:58Z): the Drive folder `mechloop handoff/results/REQ-003-build1-additions/`
(1s3685ayrJbVVh85GEsWXSuDuLJB_npFE) is **empty**. There is no RESULT.md yet. Nothing has been staged.

Cross-deliveries under REQ-002 that serve REQ-003 items (see ../instinct_REQ-002/MANIFEST.md):
- item 7: Raspberry Pi Camera Module 3 standard + wide drawings and the official STEP zip (outline OK; depth 10.25 / 11.4
  vs drawing 11.3 / 12.0, to look at). The cable drawing delivered is the **15-to-15 pin 200 mm** cable, not the Pi 5
  22-to-15 pin cable asked for. The 300 / 500 mm lengths are not delivered.
- item 3: the Gates PowerGrip GT2 design manual (already in vendor_docs as Gates_GT2_design_manual.pdf). No belt part
  number or price yet.
All other REQ-003 items (heater, PEI kit, Misumi pulley / idler, ADXL345, nozzle camera, COB strip, DIN rail,
PEM S-M3-0) are outstanding.

2026-11-20 batch 4 re-check (about 02:20Z): the REQ-003 results folder is still empty. The requests folder now also has
REQ-005 (rails addendum, HIWIN / Helix) and REQ-006 (corrections from REQ-002), with no results folders for them yet.

## First delivery (ingested 2026-11-20, batch 5)

The folder now holds 20 files (02:37Z to 02:46Z), RESULT.md last modified 02:46:31Z. Instinct's STATUS: **partial** (done 3,
5, 7, 8, 9; partial 1, 2, 6; blocked 4; waiting 10). RESULT.md as delivered is `RESULT_instinct_REQ-003_2026-11-20.md`
(sha256 fe3466d30eaea6e85d3faf5637e08fd9ddf1a106e21df385d3fd3b1210a83fbc). Untrusted data; nothing to `vendor_cad/inbox/`; nothing
committed. Same checks as the other batches (PDF raw / inflated scan + pypdf walk; STEP via build123d, one at a time).

### CAD staged here

| REQ item | Part | Maker | File | sha256 | Checks | Result | Price (RESULT.md) |
|---|---|---|---|---|---|---|---|
| 5 | ADXL345 V2.0 USB accelerometer board | BIGTREETECH | BTT-ADXL345-V2.0__step.zip (unchanged; one 38.7 MB STEP inside, kept zipped) | zip ba054b2624f938e8be8dc77a03fef2f0f9c9a96531cb0802324032ac692acafa; STEP bd7c069e0e9506b13ecbeb22e8e79006ae3a1bc49f61c89460195afad9ffa76b | Open CASCADE 6.8 export (2023-08-04), Altium board assembly, 98 PRODUCTs. 735 solids, all valid. Overall 34.68 x 16.56 x 4.27 (USB-C overhangs the board). PCB solid 33.25 x 15.50 x 0.35; two Ø3.2 holes 15.5 apart at y 2.5. Drawing (not copied, see below): board height **15.50: match**; its 28.25 / 20.50 / 15.50 / 2.50 dimensions are feature positions, not the board length. RESULT.md's "PCB 28.25 x 15.50, 2 x Ø2.50 holes, 20.50 x 15.50 pattern" misreads the drawing | PASS (reference CAD; board length 33.25 not dimensioned on the drawing) | $9.25 InStock (biqu.equipment, V2.0.1) |

### Not copied: BTT-ADXL345-V2.0__drawing.pdf contains JavaScript

sha256 8a4129376ddb017c14b56c1bfd1fed67e4ecfd38ef93e9a7ce66a7a3eff81811, 1 p, Altium Designer / llPDFLib export (2023-08-23).
It has a document-level /Names /JavaScript tree (`_FindWord`, `_HighlightRect`) and about 430 bookmark /Next JavaScript
actions such as `_FindWord(0, "PAC101");`. That is Altium's standard component-search bookmark script (select a word on the
page), with no launch, submit or URL actions, but it fails the no-JavaScript rule, so it stays only in the scratch batch dir.
A JavaScript-free copy (re-print or strip) is needed if the drawing is wanted.

### Documents copied to vendor_docs/ (unchanged; no JavaScript, actions or embedded files; none encrypted)

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 1 | Keenovo_200x200-24V-200W_page_2026-11-20.pdf | Keenovo_200x200-24V-200W__page.pdf | bf7748ad8c3b72174b669d77b79a7e74967d53312bd1ea6d8be15a1e15ba937b | keenovo.store page print, 5 p. RESULT.md: $43.28, available; 3M adhesive, NTC 100K B3950 included |
| 1 | Keenovo_NTC-100K-B3950_R-T_table.pdf | Keenovo_NTC-Thermistor-R-T-Table.pdf | 2d7ae3c0f8e71fb583954b7b5cf949ac462c63ce0667352ddad1eaf43acd22ec | 5 p R-T table |
| 3 | Gates_LL2MR09_page_2026-11-20.pdf | Gates_LL2MR09__page.pdf | 8561f50a4a419bc3c783adb52734c1194a9bd8d50b915b6e40997b98eccc24f3 | VBeltSupply page print, 5 p. RESULT.md: Gates LL2MR09 (9396-0052), $5.98/ft, 50 ft min, $300 Gates minimum |
| 5 | BTT_ADXL345-V2.0_manual.pdf | BTT-ADXL345-V2.0__manual.pdf | 0a9336b0d4905780e3746febcf3428f61a627c630f941901730cfff058810627 | 13 p |
| 5 | AnalogDevices_ADXL345_datasheet_via-Adafruit.pdf | Adafruit_ADXL345-1231__datasheet.pdf | 889e63f7503a0115054f9cbc5bdcdf175e549dabb629fa688167cb4dcbf80c74 | Analog Devices ADXL345 chip data sheet (40 p) hosted by Adafruit; not a board drawing |
| 5 | Adafruit_ADXL345-1231_page_2026-11-20.pdf | Adafruit_ADXL345-1231__page.pdf | 1c055d014123fdfa09cb55002c89f3b66e89e6f05ef82d34436d584d088c4556 | 8 p. RESULT.md: $17.50 in stock; no official STEP |
| 6 | Arducam_B0454_datasheet.pdf | Arducam_B0454__datasheet.pdf | 5c7f92c2c329c8a31a580267d1e45ba385d0830068654d0235001a75ef8f58e2 | 9 p, OV5648, 38 x 38 board |
| 6 | Arducam_B0454_page_2026-11-20.pdf | Arducam_B0454__page.pdf | e1d72fb2b842e14d22c4a5d797944db7bcf8d073c519cf0493877f51f9b6a54a | 6 p. From $38.99 |
| 6 | Arducam_B0506_datasheet.pdf | Arducam_B0506__datasheet.pdf | b1683815b137212d63c20313ed1f205c8ab1bd996b45c8fa45364326b0ced7a4 | 8 p, OV2710 IR-cut, 38 x 38, manual focus, **default focus range 2 m to infinity** |
| 6 | Arducam_B0506_page_2026-11-20.pdf | Arducam_B0506__page.pdf | 96e50c3fe5b738ba42972937216b94ca7e1e0e76f6fbef865cd8953c35f2deb1 | 5 p. $34.99 |
| 8 | InspiredLED_24V-COB_page_2026-11-20.pdf | InspiredLED_24V-COB__page.pdf | 2d6cfc64134ef37fcb57e6e834382c2b14523c63461365ce05df6aee488e18eb | 4 p |
| 8 | InspiredLED_RadiantEdge-short_8492_datasheet.pdf | InspiredLED_RadiantEdge-short__datasheet.pdf | 0a777a3b364586e7646ed7ce16d8ab8dae81f3759efaa7333d58fef2fd00b382 | 2 p, Radiant Edge DIY short (3/8") set, SKU 8492 |
| 8 | InspiredLED_RadiantEdge_page_2026-11-20.pdf | InspiredLED_RadiantEdge__page.pdf | e57510b652ea91c92ec3347e03c6a209914a86db7b658a201c5de97a5e830868 | 4 p. $50.00 in stock |
| 9 | WAGO_210-112_datasheet.pdf | WAGO_210-112__datasheet.pdf | 762f1f3d217dfea3d8e46e2f400e23bd928b6499e8405b0ad27b9f0d01076bad | 3 p: steel rail 35 x 7.5, 1 mm, 2 m, slotted, EN 60715 |
| 9 | WAGO_210-112_page_2026-11-20.pdf | WAGO_210-112__page.pdf | dcd3774a348554229b2597c8b7a336ad685d7e78d4621f71b46d3aa2f1127f40 | 2 p (Digi-Key: backorder per RESULT.md) |
| 9 | WAGO_249-117_datasheet.pdf | WAGO_249-117__datasheet.pdf | 6b23920cb62ce7cc8dab04a25761466c7ddd9ff689557901874fec4563996a33 | 4 p: screwless end stop, 10 wide x 44 high x 35 deep |
| 9 | WAGO_249-117_page_2026-11-20.pdf | WAGO_249-117__page.pdf | 46d3b58d5e541a83927948fc030f1285f78507b6f0cc81488de9507d7bccb0b5 | 2 p |

Not copied, same bytes already in vendor_docs: InspiredLED_24V-COB__datasheet.pdf (2b0101b9...) =
`vendor_docs/InspiredLED_24V-COB_flex_spec.pdf`.

Delivered under REQ-002 for REQ-003 item 2 (see ../instinct_REQ-002/MANIFEST.md, batch 5): the Wham Bam PEI plate and
magnetic base pages.

### Still outstanding per RESULT.md

1 heater: only one stock candidate (Keenovo). 2 PEI kit: one candidate (Wham Bam), plate sold out. 4 Misumi GT2 pulley /
idler CAD: blocked (account). 6 nozzle camera: 20-40 mm close focus unverified for both Arducams (B0506 states 2 m to
infinity); no STEP for either. 9: no WAGO STEP (CADENAS route blocked); drawings only. 10 PEM S-M3-0: waiting on the PEM
account. Digi-Key price / stock for the Inspired LED and WAGO parts not verified (Digi-Key blocks automation).
