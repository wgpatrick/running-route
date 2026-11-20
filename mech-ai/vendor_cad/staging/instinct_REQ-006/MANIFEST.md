# instinct_REQ-006: corrections after checking the REQ-002 deliveries, first delivery

Ingested 2026-11-20 (batch 5) from Google Drive `mechloop handoff/results/REQ-006-corrections-from-REQ-002/`
(folder 1V98cQYkRxEybCp9m66I013GLNnZCbgX3), 12 files, last modified 02:56:31Z. Collected by Instinct (the owner's browser
agent). Instinct's STATUS: **partial** (1 of 7 fully met: item 4). RESULT.md as delivered is
`RESULT_instinct_REQ-006_2026-11-20.md` (sha256 6f6e6dbccdf005deaddd185cf8c2dc9501586e70a815c479cb8ae25a5e169934). Everything was
handled as untrusted data.

Staged for review only. Nothing has been copied to `vendor_cad/inbox/`. Nothing committed.

Method: build123d / OCCT (`.venv`, `python -I`, script outside the data dir), one STEP at a time: import, solid count,
validity, bbox, cylinder diameters, slice profile; compared with the maker drawing. Zip listed first, extracted into its own
empty scratch dir. PDFs: header / %%EOF, raw and inflated-stream scan, pypdf object-graph walk. **No PDF in this delivery
contains JavaScript, actions or embedded files**; none is encrypted. The only hits are /URI link annotations in the web-page
prints and 2 in the McMaster drawing.

## STEP files staged here

| REQ item | Part | Maker | MPN | File | sha256 | Solids | Valid | BBox (mm) | Drawing check | Result | Catalogue SKU it would replace | Price (RESULT.md) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | Hex nut M2 x 0.4, 18-8 stainless, DIN 934 / ISO 4032 height | McMaster-Carr | 91828A111 | 91828A111.step (SolidWorks 2024 AP214, 2026-11-06) | 96262052b6f3137b504405770a5ae3a496a28606ba9d48fa0c8865212cec00a5 | 1 | yes | 4.0 x 4.6 x **1.6** | Drawing: 4 mm AF, 1.6 mm high, M2 x 0.4. Model: 4.00 across flats (slice profile flat at 4.00), 4.6 across corners (chamfered; sharp hex 4.62), 1.6 high, bore Ø2.0: **match** | PASS. This is the standard-height nut the design draws (NUT-M2, ISO 4032 4.0 AF x 1.6); it resolves the REQ-002 thin-nut issue (90370A201 was 1.2 high) | NUT-M2 | $7.41 / pack of 100, "Delivers November 27" |
| 1 | Modular contactor 22.32, 2 NO, without DIN slide ("senza slitta") | Finder | 22.32.0.120.4320 | Finder_22.32_2NO_2232_xx20.stp (extracted unchanged from Finder_22.32__step.zip) | 4bace5f50678864c4ea911cba1a662e39c3624076913f7f3c6c29fd2353c1141 | 2 (body + 2.1 x 0.9 x 1.35 detail) | body solid **not valid** per OCCT BRepCheck (the small one is); imports fine | 17.5 x 88.85 x 60.8 | Catalogue (`vendor_docs/Finder_22-series_datasheet.pdf`, p.14 outline, 22.32 box clamp): **17.5 wide, 88.8 high: match**. Depth is not given as text on p.14, not checked. PRODUCT name "2232_2NO_senza_slitta" | PASS on outline (visual-grade; invalid B-rep means do not use it for booleans without repair). Right part this time (REQ-002's file was the 022.3x aux block, 14.25 x 84 x 60.8) | none in printer_v11 (22.32 wanted per REQ) | not given |
| 1 | the same series zip as delivered | Finder | 22.32 series | Finder_22.32__step.zip (unchanged) | 6f7d5beb0b97eafdff9910aa7c99b59b61c6b7d6cf3d86855315ed8e5960c2d2 | - | - | - | Holds 2232_xx20.stp (above) and 2232_xx40.stp (b943995b02767dfc9c859e23b943dbaa73d1e879e94a918316440ea1f636dea1, PRODUCT "2232_1NO+1NC", 4 solids, body not valid, 17.5 x 88.85 x 61.3). No other files | INFO | - | - |

Note: the REQ-002 MANIFEST quoted the 22.32 as "17.5 wide x 84 body x 56.5 deep (datasheet p.14)". p.14 dimensions the
22.32 front view at **88.8** high; 84 is the aux block's height. The model matches 88.8.

## Documents copied to vendor_docs/ (unchanged)

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 4 | McMaster_91828A111_drawing.pdf | 91828A111__drawing.pdf | 1ffa313896394dd21e36447a03421840e80808db5dc15f281f567d7bd12f04a8 | 1 p: 4 mm AF, 1.6 mm, M2 x 0.4 |
| 6 | Molex_43020-0201_drawing.pdf | 43020-0201__drawing.pdf | f2c4c9f21009d7fe8069b8e419c83a352f9e8246ba6f3a35edc40fefb9717649 | SDA-43020-****, Micro-Fit 3.0 plug 2-24 ckt with optional panel mounts, 2 p (no text layer). Part table: **43020-0201 = 2 positions, panel mount NO**; 43020-0200 = YES. Confirms the ear-less plug |
| 6 | Molex_45750-3111_drawing.pdf | 45750-3111__drawing.pdf | 11fcd36356bdadfdfd37d1f585caef8099559f778d95287e49a14aa73a7490c2 | SD-45750-001 rev G9, "Mini-Fit Plus HCS / Mini-Fit Jr." female crimp terminal, 1 p; 457503111 = reel (chain), 16 AWG, tin over nickel; 457503112 = bag. For 5557 / 42474 / 44516 / 43760 / 46992 / 30067 housings |
| 5 | Harwin_R30-670XX94_drawing.pdf | Harwin_R30-6700694__drawing.pdf | 350e770da637944c9756811fa8e856dad343bb2020aad5823e299a2ccfab17c1 | Harwin customer information sheet R30-670XX94 (sheet 2 of 2, iss. 5), image only: M3 clearance circular spacer, **nylon 66 white UL94V-2**, Ø5.00 ±0.20 x Ø3.20 ±0.20, **R30-6700694 = L 6.00** ±0.20. RESULT.md calls it DRG-02007; the sheet says R30-670XX94. Note: the SKU is named 5x3.3x6; the bore is 3.2 |
| 5 | Harwin_R30-6700694_page_2026-11-20.pdf | Harwin_R30-6700694__page.pdf | a910015491019a2a4166cde75dd581e18500c923f4c31e565206290399ce906c | harwin.com product page print, 4 p |
| 1 | Finder_22.32.0.120.4320_page_2026-11-20.pdf | Finder_22.32.0.120.4320__page.pdf | c2731b65087befe0a157e262325af4e0ad9c86764551935c5d8f16a744399ea3 | findernet.com product page print, 1 p |
| 2 | RaspberryPi_camera_cable_Pi5_page_2026-11-20.pdf | PiCameraCable-Pi5__page.pdf | 271c16f7c8da5fd4585e8c6d8b09844b0153109892c5e4b821bed934916fac04 | raspberrypi.com Pi 5 camera cable page print, 3 p. 22-to-15 pin, 200 / 300 / 500 mm; no drawing, no SKU on the page |

Not copied, because the same bytes are already in vendor_docs:
- Finder_22-series__catalog.pdf (0c5a0b0c...) = `vendor_docs/Finder_22-series_datasheet.pdf` (S22EN, 18 p).

## Still outstanding per RESULT.md

1 Finder 22.32.0.230.4340 (2 NC): no maker STEP; the 2NO / 1NO+1NC models share the outline, but using one as the 2NC
reference needs the owner's OK. 2 Pi 5 camera cable drawing: none published (reseller SKUs SC1128 / SC1129 / SC1130 from
The Pi Hut, not maker-published). 5 Harwin R30-6700694 STEP and 6 Molex 43020-0201 STEP: both behind TraceParts portal
access (blocked). 3 skipped and 7 no-op per the REQ.
