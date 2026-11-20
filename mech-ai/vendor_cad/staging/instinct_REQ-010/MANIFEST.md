# instinct_REQ-010: nozzle camera files

Checked 2026-11-20 (batch 8, about 06:45Z). Drive folder `mechloop handoff/results/REQ-010-nozzle-camera-files/`
(1brBo3_WLt7nddDDs3jj_VGjoD7pfgF-h, created 06:33:15Z) is **empty**: no RESULT.md, no files. A Drive-wide search for B045401 /
B0292 found nothing either. Nothing staged.

Camera results described elsewhere (B045401 fails close focus, B0292 reaches 40 mm but the board is too big, B0454 candidate
unconfirmed) are not in any delivered file, so they are unverified here. The only camera files on hand are the REQ-003 Arducam
B0454 / B0506 datasheets and pages (../instinct_REQ-003/MANIFEST.md, item 6: 38 x 38 boards, close focus at 20-40 mm unverified;
B0506 states 2 m to infinity). Re-check this folder in the next batch.

## Batch 9 (ingested 2026-11-20, folder state at 06:50Z): B0454 STEP + datasheet, B045401 / B0292 datasheets

Five files arrived in REQ-010 between 06:49:59Z and 06:50:00Z. A new sibling folder `NOTE-pcbway-review-status`
(1kT1X5r2vV3Iaawm4a3emZOVvhrecwDR7, 06:47Z) holds one RESULT.md. It is recorded in
`reference_parts/batch01/results/pcbway_status_2026-11-20.md` and not staged here. A search of `mechloop handoff/results`
for anything created or modified after 06:30Z returned only these 6 files and the 2 folders, so nothing else is new. The
REQ-008 RESULT.md at 06:30:10Z was already seen in batch 8. Each file was downloaded on its own into scratchpad
`instinct_batch9/` (the zip was unpacked inside it), and every size matches Drive. All of it is handled as untrusted data
and staged for review only: nothing went to `vendor_cad/inbox/` and nothing is committed.

RESULT.md (1OC2R0nqrUErLsO4LhkA41PXpsfjm9hbN, 06:49:59Z, 6,659 B) is staged as `RESULT_instinct_REQ-010_2026-11-20.md`
(sha256 8c0b5a88ff1fe1dcb456841da508e027fe2bd732672f7a7db28354d3e5d0a6d9). Instinct's STATUS is **partial**. It reports
nothing purchased and prices captured 2026-11-19 (USD). Its verdict: "no board found that satisfies all four REQ criteria
AND has official 20-40mm focus".

PDF checks used pdfscan_b3.py (header and %%EOF, raw and inflated-stream scan) and pdfstruct_b3.py (pypdf object-graph walk).
Both PDFs are real PDF 1.7 files from WPS Writer and are not encrypted. They contain **no JavaScript, Launch, OpenAction/AA,
embedded files, forms or XFA**. The only link annotations point to http://www.arducam.com. The STEP is plain
ISO-10303-21 AP214 text, complete (ends END-ISO-10303-21), with no URLs.

| Delivered as (Drive id, size) | Staged as | sha256 | Content |
|---|---|---|---|
| B0454__cad.zip (1omzNquUKcTaHC-r8nmEZwPfGdu5VCtcg, 1,780,541 B) | zip not kept; its only member is staged | 7dabce091c3621d757695d8ce75129001c225ed8d78161566c126086c465196f | one entry, `B0454.STEP` (9,230,941 B), no paths |
| B0454.STEP (from the zip) | instinct_REQ-010/Arducam_B0454.STEP | 82915bcae06736b6e6cf2300096ba46cca982c61a8a275dd2ec8f8f8a9685ebf | SolidWorks 2021 / SwSTEP 2.0 export of 2023-11-03, AP214. Assembly `B0454` contains a sub-assembly named **`B0447(UC-A52) Include device`** (an Arducam internal name; the board is shared with another SKU). 148 solids, all valid. Instinct says it came from download.arducam.com/3D-Drawing/B0454.STEP (not verified here: that host is refused by the proxy) |
| B0454__datasheet.pdf (1gGhAgqOKjOnatQFADF3XQ0M632TYwNCW, 528,763 B) | **not copied**: same sha256 as `vendor_docs/Arducam_B0454_datasheet.pdf` (REQ-003) | 5c7f92c2c329c8a31a580267d1e45ba385d0830068654d0235001a75ef8f58e2 | "OV5648 USB2.0 Wide Angle Camera Module B0454", 9 p, V1.0 05.18.2023 |
| B045401__datasheet.pdf (18_CVS-0AklmStldFO8qs_TYJD2JLXnIm, 528,763 B) | **not copied**: byte-identical (`cmp`) to B0454__datasheet.pdf | 5c7f92c2c329c8a31a580267d1e45ba385d0830068654d0235001a75ef8f58e2 | **the same B0454 datasheet**. It names only B0454, OV5648 1/4" and a 38 x 38 board. It says nothing about B045401 (1/2.8", 32 x 32, HDR, enclosure) |
| B0292__datasheet.pdf (1sYPC2Chu-ncSuk61Lkr3tw8GHfhcHgh1, 536,536 B) | vendor_docs/Arducam_B0292_datasheet.pdf (new; no sha256 match in the repo) | 09e0214fae7b098d51ce70a5d9ec4fe2d75a0988e5f3a1bef4c5025aa327fc55 | "IMX219 USB2.0 Autofocus Camera Module B0292", 8 p, V1.0 28.12.2020 |
| RESULT.md (1OC2R0nqrUErLsO4LhkA41PXpsfjm9hbN, 6,659 B) | instinct_REQ-010/RESULT_instinct_REQ-010_2026-11-20.md | 8c0b5a88ff1fe1dcb456841da508e027fe2bd732672f7a7db28354d3e5d0a6d9 | see above |

**B0454 vs B045401 datasheet:** the two files are the same bytes (same sha256). Arducam does not publish a separate B045401
datasheet. The PDF filed as "B045401" is the B0454 datasheet, and Instinct says so too: Digi-Key hosts this same file as the
B045401 datasheet. Whether arducam.com itself serves it under a B045401 name cannot be checked from here. Either way, **there
is still no datasheet, dimensioned drawing or STEP for the B045401 itself.** Its only specs are the UCTRONICS page table in
`vendor_docs/Arducam_B0454_page_2026-11-20.pdf`.

### Datasheet extraction (all three, plus the UCTRONICS page for B045401)

| | B0454 (datasheet) | B045401 (UCTRONICS page; its "datasheet" is the B0454 file) | B0292 (datasheet) |
|---|---|---|---|
| Sensor | OV5648, 1/4", 1.4 µm | 1/2.8", 2 µm, 5 MP. Sensor not named on the page; Instinct's "A5648S" is not in any file here. Digi-Key says OV5648 | Sony IMX219, 1/4", 1.12 µm |
| Resolution / fps | 2592x1944; MJPG 15 fps at 5 MP, **30 fps at 1920x1080 and 1280x720**; YUY2 10 fps at 720p | 2592x1944; MJPG 30 fps at all sizes incl. 5 MP and 1280x720; HDR | 8 MP 3264x2448; MJPG 15 fps at 8 MP, **30 fps at 1080p**; YUY2 15 fps at 720p |
| Interface | USB 2.0 UVC, JST B4B-ZR, 5 V, max 300 mA | USB 2.0 UVC, B4B-ZR, 1.043 W typ. | USB 2.0 UVC, JST ZHR-4, 5 V, max 200 mA |
| Lens / mount | **M12 x P0.5**, EFL 2.1 mm, FoV 95° H, 650 nm IR filter; lens diagram: Ø17.4 front, 20.87 ±0.3 lens front to image plane, holder 2-Ø1.50 screw holes, 22.90 long | M12-S, EFL 2.7 mm F2.8, 88° H, distortion < -1 %, metal enclosure | **autofocus module, mount not stated (no M12 in the datasheet)**; FoV 60° H / 72° D / 47° V; IR filter. The drawing shows a VCM-module outline, not an M12 holder |
| Focus range / MOD | **none stated** (UCTRONICS page: "Fixed Focus", default 300 cm-∞) | "Fixed Focus", **default 300 cm-∞** (page) | **"Focusing Range: 40mm to infinity"** |
| Board size | 38 x 38 mm; holes 28 x 28 (R1.40, Ø2.8) and 34 x 34 (R1.20, Ø2.4); lens centred (19, 19) | 32 x 32 x 1.6 mm (page); no drawing | 38 x 38 mm; holes 28 x 28 (R1.40) and 34 x 34 (R1.30); lens centred (19, 19) |
| Operating temp. | -20 to +70 °C (datasheet); 0-70 °C on the page | 0-70 °C | -20 to +70 °C |
| Close focus at 20-40 mm stated? | **No** | **No** (the stated default is 3 m-∞) | **Only at 40 mm** (the end of the range). 20-39 mm is not covered |

### B0454 STEP vs its datasheet drawing (build123d 3D geometry checks run with `.venv/bin/python -I` under `ulimit -v 3 GB`, one file, peak RSS 447 MB; scripts scratchpad/scripts/b0454_check_b9.py, b0454_check2_b9.py)

The board's top face is at Z = 0, and the lens points +Z.

| Check | Datasheet | STEP | Result |
|---|---|---|---|
| Board outline / thickness | 38.00 x 38.00 (1.6 per page) | 38.00 x 38.00 x 1.60 (X 0-38, Y 0-38, Z -1.6-0) | match |
| 28 x 28 mounting holes | 4 x R1.40 (Ø2.8), 28.00 pitch, centred | 4 x Ø2.80 at (5, 5), (33, 5), (5, 33), (33, 33): 28.00 pitch, centred | match |
| 34 x 34 corner holes | 4 x R1.20 (Ø2.4) at 34.00 pitch | **absent**: no hole near (2, 2) etc. | **mismatch**: the STEP has only the 28 x 28 pattern. Do not design to the 34 x 34 holes from this model |
| Edge slots | rounded slots along each edge | narrow slots about 0.64 wide at about 2.5 mm from each edge (half-cylinder ends) | present (shape not checked in detail) |
| Lens axis position | 19.00 / 19.00 from the edges (centred) | lens / holder axis at (18.97, 19.02) | match (0.03 mm) |
| Lens front diameter | Ø17.4 | Ø17.4 | match |
| Lens holder | 2-Ø1.50 screw holes; flange 22.90 long; body 13.00 | holder + lens are one solid, 22.0 x 17.4 x 21.6; screw holes Ø1.50 at X 9.97 / 27.97 (pitch 18.0); board holes Ø2.2 under them | screw-hole Ø matches. **Flange 22.0 vs 22.90** in the drawing (-0.9). The drawing does not clearly dimension the screw pitch |
| Lens height | 20.87 ±0.3 lens front to image plane | lens front at Z 21.6, a Ø15 ring to Z 21.78; sensor package Z 0-1.45 | consistent (21.6 minus a sensor-surface height of about 0.7-1.45 gives 20.15-20.9) |
| Connector | 7.56 x 3.81 at 8.24 from the left, 3.47 from the bottom | housing 7.5 x 3.5 at X 8.15, Y 3.71; 4 pins at 1.5 pitch | match (within 0.25) |
| Back side | - | parts to Z -6.1 (connector body through the board); overall Z -6.1 to 21.78 | depth about 27.9 incl. lens |
| Solids | - | 148, all `is_valid` | ok |

The model is the stock B0454 with its 2.1 mm lens at its as-modelled position. It says nothing about focus travel.

### Comparison with docs/NOZZLE_CAMERA.md and Instinct's claims

- **"B045401 fails close focus"**: partly supported. The maker page states "Fixed Focus, default 300 cm-∞". **But the same
  page states exactly the same for the B0454-1** (Fixed Focus, 300 cm-∞). The datasheets give no different focus spec, so
  this does not separate B045401 from B0454. Both are M12-S lenses. NOZZLE_CAMERA.md section 2 holds that an M12 lens
  focuses closer when screwed out by f²/(u-f). That is about 0.16 mm for 2.1 mm at 30 mm, and about 0.27 mm for 2.7 mm. The
  "300 cm-∞" figure is therefore the factory setting, not an optical limit. Two things are not known: whether "fixed focus"
  means the lens is glued, and whether the B045401's metal enclosure lets the lens turn. Neither is answered by any file.
- **"B0292 reaches 40 mm but board too big"**: the 40 mm figure is **confirmed** by the datasheet ("Focusing Range: 40mm to
  infinity"). But 40 mm is the edge of the 20-40 mm window, and the doc's design point is a 30 mm lens front. Its board is
  38 x 38, the **same size as the B0454 fallback**, so board size does not separate B0292 from B0454. Correction to the
  RESULT.md: the B0292 datasheet **does not say M12**. It is an autofocus (VCM) module, so the Commonlands 6.2 mm lens in
  NOZZLE_CAMERA.md cannot be fitted to it. With its stock 60° H FoV at 40 mm, the frame is about 46 mm wide
  (2 x 40 x tan 30°).
- **"B0454 unconfirmed"**: agreed. The datasheet states no focus range. The STEP now matches the drawing (except the missing
  34 x 34 holes), so B0454 now meets the owner's rule (maker, MPN, datasheet, CAD).
- NOZZLE_CAMERA.md recommends the B045401 on the condition that its own datasheet, drawing and STEP are obtained. **That
  condition is still not met.** The RESULT.md says the STEP URL returns 404 and no other official file was found.
  NOZZLE_CAMERA.md (sections 3a, 4, 7) already notes that the B0454 PDF is the one Digi-Key links for B045401. This batch
  confirms it is byte-identical.
- RESULT.md items 3-5 (DFRobot FIT0819, Commonlands CIL062 STEP, other boards) came with no files. Their claims are
  unverified here. FIT0819 temperature and focus are still unpublished, and Commonlands publishes no STEP.

### Prices and stock per RESULT.md (not verified)

B045401 Digi-Key 4679-B045401-ND $62.41, 0 in stock, 2-week lead. B0454 UCTRONICS $38.99 (+$1 "Standard Module"), ships
internationally (CFR), US shipping cost not quoted (an account is needed; account creation was not approved). B0292
Digi-Key 4679-B0292-ND $56.35, 0 in stock. Commonlands CIL062-F4.0-M12A650 $19.00 direct, in stock.
