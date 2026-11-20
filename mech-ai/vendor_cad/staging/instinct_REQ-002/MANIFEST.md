# instinct_REQ-002: supplier CAD and datasheets, batch 3 (full list), first delivery

Ingested 2026-11-20 from Google Drive `mechloop handoff/results/REQ-002-supplier-cad-batch-3-full/`
(folder 1RI-CdoBbH9t_4mt2fioLIT-op7WBFLYL), 54 files, plus the RESULT.md revision of 01:51:45Z. Collected by Instinct
(the owner's browser agent). Instinct's STATUS: **partial**. RESULT.md as delivered (latest revision) is
`RESULT_instinct_REQ-002_2026-11-20.md`. Everything was handled as untrusted data.

Staged for review only. Nothing has been copied to `vendor_cad/inbox/`. Nothing committed.

Method: build123d / OCCT (`.venv`, `python -I`, script outside the data dir), one STEP at a time. Checks: import, solid
count, validity, bbox, cylinder diameters, slice profile along the long axis, compared with the maker drawing delivered
with it. PDFs: header / %%EOF, raw and inflated-stream scan, and a pypdf object-graph walk for /JavaScript, /JS, /Launch,
/EmbeddedFile, /RichMedia, /XFA, /SubmitForm, /OpenAction, /AA. **No PDF contains JavaScript, launch actions or embedded
files.** The only actions are `/OpenAction /GoTo /Fit` (open-at-page view) in three Raspberry Pi PDFs. The raw-byte hits
for "/JS" and "/AA" in the Pi 5 drawing, MIC-6, Finder 22 and RAF PDFs are inside base64 / compressed image data, not PDF
keys. `JST_XH_datasheet.pdf` and the TBI catalogue (REQ-004) are owner-password encrypted (permissions only, opens
without a password).

Source URLs: RESULT.md names the URL for the documents it lists. McMaster parts: `https://www.mcmaster.com/<part number>/`
(owner's account). Molex: molex.com part-detail pages. Panduit: panduit.com. Raspberry Pi: raspberrypi.com /
pip.raspberrypi.com. Drive file ids are in `instinct_seen.json`.

## STEP files staged here

| REQ item | Part | Maker | MPN | File | sha256 | Solids | Valid | BBox (mm) | Drawing check (drawing in vendor_docs) | Result | Catalogue SKU it would replace | Price (RESULT.md) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | SHCS M2x20, black-oxide alloy steel | McMaster-Carr | 91290A049 | 91290A049.step | db695e469b24e268113e482f2f33cf282d39fdd257ef2e612ef52736e26062eb | 1 | yes | 3.8 x 3.8 x 22.0 | head Ø3.8, head 2, length 20 (22 overall): match. Fully threaded Ø2.0 | PASS | SHCS-M2x20 | $16.58/pack |
| 5 | SHCS M2.5x20 | McMaster-Carr | 91290A108 | 91290A108.step | 38221203ebd6bc5a6cecc720ea116c1d9bab04eff16a1e706efdb7f2968e14ce | 1 | yes | 4.5 x 4.5 x 22.5 | head Ø4.5, head 2.5, length 20: match. Fully threaded Ø2.5 | PASS | SHCS-M2.5x20 | $10.88/pack |
| 5 | SHCS M3x25 | McMaster-Carr | 91290A125 | 91290A125.step | 428f90bb6da1915d22bf40043f373759b0031709d3f2fd4635e91b5625974a50 | 1 | yes | 5.5 x 5.5 x 28.0 | head Ø5.5, head 3, length 25: match. Thread Ø3.0 over about 17.9 from the tip (drawing: 18 min), then a plain shank Ø3.108 | PASS | SHCS-M3x25 | $17.78/pack |
| 5 | SHCS M5x16 | McMaster-Carr | 91290A232 | 91290A232.step | 69467c4108095827a7f52a5cea84fc8361996c889231f0d1708d246ed8de37b8 | 1 | yes | 8.5 x 8.5 x 21.0 | head Ø8.5, head 5, length 16: match. Fully threaded Ø5.0 | PASS | SHCS-M5x16 | $17.27/pack |
| 5 | SHCS M5x65 | McMaster-Carr | 91290A270 | 91290A270.step | 767dfe764276141288a950438df187af9af4632ac45ba2b821034375e5aeec82 | 1 | yes | 8.5 x 8.5 x 70.0 | head Ø8.5, head 5, length 65: match. Thread about 22 from the tip (drawing: 22 min), plain shank Ø5.173 | PASS | SHCS-M5x65 | $8.73/pack |
| 5 | SHCS M4x6, zinc-plated alloy steel | McMaster-Carr | 90128A208 | 90128A208.step (9.05 MB) | 6f4c94784b949a01b99dc880c9a59d44c020b836ab967eda82f3719b17042f5f | 1 | yes | 7.0 x 7.0 x 10.0 | head Ø7, head 4, length 6: match | PASS | SHCS-M4x6 (mcmaster_fasteners.json already maps it to 90128A208) | $11.33/pack |
| 5 | Thin-profile hex nut M2x0.4, medium-strength steel | McMaster-Carr | 90370A201 | 90370A201.step | d688b6761bf4133778dea260b0eb54a969aa1ab7964b2df684418a5696191a14 | 1 | yes | 4.0 x 4.619 x 1.2 | 4 across flats, 1.2 high: match its drawing | PASS against its drawing. **Not like-for-like:** NUT-M2 is drawn as ISO 4032 (4.0 AF, **1.6** high). This is a thin nut (1.2). Instinct chose it; RESULT.md calls it a design decision | NUT-M2 (decision needed) | $6.51/pack |
| 5 | General-purpose washer M2, zinc-plated steel | McMaster-Carr | 91166A180 | 91166A180.step | 1326e4abc67288f48f4c3f4fbed5398c68495569a08b8e143e8a41f2b3282e50 | 1 | yes | 5.0 x 5.0 x 0.4 | OD 5.0, ID 2.2: match. Drawing gives thickness 0.2 to 0.4; the model is 0.4 (ISO 7089 nominal is 0.3) | PASS | WASHER-M2 | $3.00/pack |
| 11 | Micro-Fit 3.0 receptacle housing, dual row, 2 ckt | Molex | 43025-0200 | 43025-0200.step (from 43025-0200_STEP.zip, unchanged) | f9a12a374778b5a2bcf6ebc2d436bef732abc6640d76b9224b3c5d63f337a2a2 | 1 | yes | 5.28 x 14.00 x 10.83 | dim A 3.86 + 2 x 0.71 ribs = 5.28: match. Length 14.00: match. 7.57 (2-ckt depth) + 3.28 (latch) = 10.85 vs 10.83 | PASS | CONN-MOLEX-MICROFIT (receptacle half) | not given |
| 11 | Micro-Fit 3.0 plug housing, dual row, 2 ckt, **with panel-mount ears** | Molex | 43020-0200 | 43020-0200.step (from 43020-0200_STEP.zip, unchanged) | 913fb288ec0fbb12666085e951bb5a4b4109ca958b408dc4fc16d4f42c5e1dfb | 1 | yes | 11.09 x 16.89 x 8.95 | length 16.89 (drawing .665/16.89 ref): match. 11.09 is across the panel-mount ears; the drawing gives only the panel cut-out (C 4.21, D 7.90 for 2 ckt) | PASS. Note: -0200 is the panel-mount option; -0201 is the same plug without ears | CONN-MOLEX-MICROFIT (plug half) | not given |
| 20 | Cable tie, miniature, 99 mm | Panduit | PLT1M-C | PLT1M-C.step | fad1b3096545baa0861b5193f286a50adb1467abf59b0441d20fbaec177447af | 1 | yes | 97.93 x 8.14 x 29.12 (modelled with the tail curved) | strap width 2.57 (drawing 2.5), head about 5.0 x 4.6 (drawing C 4.3, E 4.6). Strap section 1.47 thick vs drawing A 1.1 (ribbed strap?). Length about 99 along the curve | PASS (visual-grade CAD). Minor thickness difference noted | CABLE-TIE-100MM | not given |
| 17 | Camera Module 3, standard and wide | Raspberry Pi | (Camera Module 3 std / wide) | RaspberryPi_Camera-Module-3_std+wide_STEP.zip (zip unchanged; 60.7 MB of STEP inside, kept zipped here) | zip b2e2026ea5322bddf1ddcbae97c094822ee9e0ca92d7bc5c748f60a8b5ef6683; std .stp ecbc4b091e51f31c6186b81ad68d4205b8dceec0d90c116cd7fd699e1f1c5702; wide .stp b13715ed4fac37ef8357ffddf824cfafe923e55aa849941c5508986cc625c994 | std 590, wide 631 | yes (all) | std 23.862 x 25.0 x 10.245; wide 23.862 x 25.0 x 11.4 | PCB 25 x 23.862: match both. **Overall depth short of the drawing:** std 10.25 vs 11.3, wide 11.4 vs 12.0. The "_simple" models probably leave out part of the rear connector or lens stack | PASS on the outline. The depth difference needs a look before the model is used for clearance | none (no camera SKU in printer_v11) | not given |

The zip also held two `__MACOSX/._*.stp` resource-fork files (410 bytes each). They were not extracted.

Not staged:

- **Finder 22.32 (item 15), `22.32__step.stp`: FAIL, wrong part.** sha256
  f2b075d60c8b977359b26b1e4893e227980b088511a56fb22255610b62c7b969, 4 solids, valid, bbox 14.25 x 84.0 x 60.8. The STEP
  header names it `022_3x`, and its only PRODUCT is "Complessivo 022_35 1NO+1NC". That is the **022.33 / 022.35
  auxiliary-contact block** from the series zip, not the 22.32 contactor. The 22.32 is 17.5 wide x 84 body x 56.5 deep
  (datasheet p.14). RESULT.md says Instinct extracted "0223x.stp" from the official 173 MB zip. It is kept only in the
  scratch batch dir. Ask Instinct for the 22.32 model from the same zip.
- 91290A221 (M5x6, item 5): `91290A221__step.step` and its drawing are byte-identical to `instinct_REQ-001/91290A221.step`
  (682c663a...) and `vendor_docs/McMaster_91290A221_drawing.pdf`, which were already staged. This confirms M5x6 = 91290A221.

## Documents copied to vendor_docs/ (unchanged)

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 5 | McMaster_91290A049_drawing.pdf | 91290A049__drawing.pdf | cdae4930ca3bbf011f9510b89c827ce61b120f1a270b2c1c82d5043be905e2a5 | SolidWorks drawing, 1 p |
| 5 | McMaster_91290A108_drawing.pdf | 91290A108__drawing.pdf | 617b68e909a20d10171ab2d37c84950862997d75388d4de951feaad3e33c9d95 | 1 p |
| 5 | McMaster_91290A125_drawing.pdf | 91290A125__drawing.pdf | 3bd0cdedf4928adf0225b731585281a36babea8143855fb509da6c9b0ad67c09 | 1 p |
| 5 | McMaster_91290A232_drawing.pdf | 91290A232__drawing.pdf | 7ccb8f5bc038c0df5e9ad48b90ff89e1915dbddc7343f5298d7b2a6f767c78f5 | 1 p |
| 5 | McMaster_91290A270_drawing.pdf | 91290A270__drawing.pdf | 7768aeecb33dbf46ef31e95fdb90f3c16b50186b9d248aac3503614d8b42fd3c | 1 p |
| 5 | McMaster_90370A201_drawing.pdf | 90370A201__drawing.pdf | 2f30292a8d8f8920c9c72f05cbd8ad332bc10b6eef84f652a2576fcf125cebdd | 1 p |
| 5 | McMaster_91166A180_drawing.pdf | 91166A180__drawing.pdf | 439f96d43f7d042297302db5e9c74eff3d7c966aadee21172e600e1849b489b9 | 1 p |
| 5 | McMaster_90128A208_drawing.pdf | 90128A208__drawing.pdf | fe404e256c51f23243c77ad6cd09c27fcf5ea8f069c7819ae8f37ff19eed061b | same bytes as staging/supplier_2026-11-18/_DEVIATIONS/SHCS-M4x6.pdf |
| 11 | Molex_43025-0200_drawing.pdf | 43025-0200__drawing.pdf | 3fa78847433b382fa07609fb9f44b5e8b017804b9b491250dc493eef9e029e28 | 430250000-SD rev A, 1 p |
| 11 | Molex_43020-0200_drawing.pdf | 43020-0200__drawing.pdf | 6b1346a84f864d06b428fda01d10b5b26c79bd94f776f66b5a20b4bc88a17ed8 | SDA-43020, 1 p |
| 11 | Molex_43030-0001_drawing.pdf | 43030-0001__drawing.pdf | 72f9e8ec91466ae63c1f41c45c412bbcef57e71d1595e97a91ade77d326817b9 | female crimp terminal 20-24 AWG; no STEP offered |
| 11 | Molex_43031-0001_drawing.pdf | 43031-0001__drawing.pdf | cdb38bdcffb7426f88b7e00a265c7c65f2c1f128eee2efdd030e5ab8f1a619b8 | male crimp terminal, 2 p; no STEP offered |
| 11 | Molex_39-01-2020_drawing.pdf | 39-01-2020__drawing.pdf | 006bb06a775c0100f3184a02d0aa9e6cc09caf77630144b19a7b5f15ae5b2386 | Mini-Fit Jr receptacle family drawing, 2 p; no STEP |
| 13 | Littelfuse_297_MINI32V_datasheet.pdf | 297__datasheet.pdf | a3d9af50efb3d50d9284b67f814317ebe0ade77966bda2861d8d205109d65aee | 3 p |
| 13 | Littelfuse_218_datasheet.pdf | 218__datasheet.pdf | 0c977771b9905f7e1c827e56752b0bfd3823480ebaac6c80f04b448d5c23a43b | 5x20 mm **time-lag**, 4 p (0218008.MXP = T8A) |
| 14 | Vishay_BAT85S_datasheet.pdf | BAT85S__datasheet.pdf | 0152851a68f60cce52ba39846c00860c71ebfdf878b89a893255abc6d55ce050 | 3 p |
| 15 | Finder_22-series_datasheet.pdf | 22.32__datasheet.pdf | 0c5a0b0c98bf3529c0429ceec12f2ca343f46ad02de65062b80033adbfdeb1cc | S22EN, 18 p, VII-2026; outlines p.14 |
| 10 | JST_XH_datasheet.pdf | XH__datasheet.pdf | 9426b136902f11900825077535e5c65032b7fbc31ffb59c5e9e1f463bb20fb90 | eXH, 9 p, permission-encrypted |
| 17 | RaspberryPi_Pi5_mechanical_drawing.pdf | RaspberryPi5__mechanical-drawing.pdf | 5dd680d6c1f5e7aa9c7b020695e315d04aac862df82ff01d4e9041cd0668d7f2 | **85 x 56 board: match**. Holes Ø2.7 at 58 x 49, 3.5 from the edge |
| 17 | RaspberryPi_Active-Cooler_product_brief.pdf | PiActiveCooler__product-brief.pdf | 8cfa494afdfba991a338ae2710a1438405a0752d61c5d0930b02a8f88dd2eed3 | 7 p |
| 17 | RaspberryPi_27W-USB-C-PSU_product_brief.pdf | Pi27W-PSU__product-brief.pdf | d5b4cc0d9724b7e917f29a76155d1f049802ed86e4d806990aee099ab91f66a9 | 11 p |
| 17 | RaspberryPi_HQ-Camera_product_brief.pdf | PiHQCamera__product-brief.pdf | 21365c8121a511ef02cfe699f862737b4d2925a9fab57b17ce0579ea68173383 | 7 p |
| 17 | RaspberryPi_HQ-Camera_product_brief_2025-02.pdf | PiHQCamera-M12__mechanical-drawing.pdf | 1e4a4fa2ab6850c5c424d92da086ccebb41df98cff193b0a0e8e7860c194903f | **Mislabelled:** this is the Feb-2025 HQ Camera product brief (CS + M12), 7 p, not a standalone M12 drawing |
| 17 | RaspberryPi_HQ-Camera_CS_mechanical_drawing.pdf | PiHQCamera-CS__mechanical-drawing.pdf | ddc86db6cf25fdf2fdd15fc14f15b1d59737e07edbcd70317b2fbbfc3d9f5886 | 38 x 38 board |
| 17 | RaspberryPi_HQ-Camera_schematics.pdf | PiHQCamera__schematics.pdf | 05f7967bfe2981181005023557422a6864a127a34df4894e0f1d11caafaea128 | 3 p |
| 17 | RaspberryPi_Camera-Module-3_std_mechanical_drawing.pdf | PiCameraModule3-std__mechanical-drawing.pdf | bde27f5ab38dd46aa05713bbb17c6e8acc4cb1d48ff9109df511256f6fbc66ac | 25 x 23.862, depth 11.3 |
| 17 | RaspberryPi_Camera-Module-3_wide_mechanical_drawing.pdf | PiCameraModule3-wide__mechanical-drawing.pdf | c5f87a9b48d63857fb3d9c0a3deeec797325c56d198c80bcb77a2062e6925b92 | 25 x 23.862, depth 12 |
| 17 | RaspberryPi_Camera-Module-3_product_brief.pdf | PiCameraModule3__product-brief.pdf | 578efcad6337696a29b9c068815a01d63ddcf7beacf584051d61cf1cddeeaf0a | 7 p |
| 17 | RaspberryPi_Camera-Module-3_schematic.pdf | PiCameraModule3__schematic.pdf | a527a9edc4d2b75f938f0b19d5c33ae1f482beb8e964f4f14260c786025a581b | 2 p |
| 17 | RaspberryPi_camera_cable_15-15_200mm_drawing.pdf | PiCameraCable200mm__drawing.pdf | eb57535be81b6d63e3cc5cb77ac26c84727f5b52f147819186e56bee0eab117d | **15-pin to 15-pin**, 1.0 pitch, 16 wide, 200 long. Not the Pi 5 22-to-15 cable that REQ-003 item 7 asks for |
| 18 | Harwin_R30-620XX14_drawing.pdf | R30-6200614__datasheet.pdf | 0581fecbe0462235f1e852da03bdd6b3b1c277a8f815b4968a4a8b46b8a15e5e | M3 clearance spacer, **aluminium**, Ø5.00 x Ø3.20, R30-6200614 = 6.00 long |
| 19 | RAF_catalog_p31M_4.5mm_swage_spacers.pdf | RAF__catalog.pdf | f5900a6e612d540ad55bace7574b80b92b3781dedca26c368d5a444f62b16a25 | **Only catalogue page 31M** (4.5 mm round swage spacers, M2 / M2.5). Not the standoff sizes asked for |
| 20 | igus_CF880_datasheet.pdf | CF880__datasheet.pdf | 190960a2635671ad06147a6f74aadd82903398d0ca97c405c21810f7f03c0af1 | 7 p |
| 20 | Panduit_PLT1M-C_drawing.pdf | PLT1M-C__drawing.pdf | b712aedc2793809c13e91ab34262bbda637efb1bcbf4708a8c799cfb6002eb66 | PLT series customer drawing |
| 20 | Henkel_Loctite-243_TDS.pdf | Loctite243__tds.pdf | aba3c039d404cc9e9803c8840c85ee851b023de11f798ac84be378593afb2f9b | Apr 2025, 5 p (browser print of the Henkel TDS page) |
| 23 | Alcoa_MIC-6_brochure_AMP003.pdf | MIC-6__datasheet.pdf | 59ea5327e19cd7aa725aab58051aa5dc5e506a907729d89802d183f19682711c | same bytes as staging/MIC6_Alcoa_brochure_readable.pdf; distributor-hosted Alcoa brochure (provenance note in RESULT.md) |

Not copied, because the same bytes are already in vendor_docs:

- PowerGripGT2__design-manual.pdf (item 4, ef9f6021...) = vendor_docs/Gates_GT2_design_manual.pdf
- DD11.0114.1111__datasheet.pdf (item 9, 1db97cff...) = vendor_docs/INLET-C14-SW-FUSE-T8A_datasheet.pdf
- 91290A221__drawing.pdf (d9079754...) = vendor_docs/McMaster_91290A221_drawing.pdf

## Still outstanding per RESULT.md (not delivered)

1 StepperOnline 17E19S1684AB4-330RA (blocked, Cloudflare). 2 HIWIN MGNR12R300 / R220 / MGN12H CAD + MG catalogue (not
started). 3 MISUMI HBLFSN5, GT2 pulley / idler (not started). 6 PEM S-M3-1ZI / S-M3-0ZI (awaiting PEM account). 7 Omron
D2F-01L STEP (not started). 9 Schurter DD11 STEP, 4301.1401, 0001.2513 / 0001.2511 (blocked). 10 JST XH STEPs. 11 Molex
0457503111 (not found) and STEPs for 43030 / 43031 / 39-01-2020 (not offered). 12 TMC2209 (blocked, Akamai). 15 Finder
22.32 STEP (delivered file is the wrong part, see above), IB2232EN-1 (blocked). 16 Phoenix 1119897 (blocked). 18 Harwin
CAD + R30-6700594 / 694 / 894. 19 RAF CAD for 5.5 / 6.1 / 9.725 / 13.2 / 40 mm. 21 Century Spring drawing + max temp
(page: $2.20, backordered 4-6 weeks, 0.8 N/mm). 22 Accu HPLW CAD (needs an account; awaiting owner). 24 PEI kits.
25 Keenovo page.

## Decisions for the owner

1. NUT-M2: the delivered McMaster 90370A201 is a **thin** nut (4 AF x 1.2). The design draws ISO 4032 (4 AF x 1.6).
   Either accept the thin nut (and check the thread engagement) or ask for a standard-height M2 nut.
2. SPACER-NYLON-M3-5x3.3x6: mpn_map.json maps it to Harwin **R30-6700694 (nylon)**. Instinct delivered the drawing for
   **R30-6200614**, the **aluminium** spacer (Ø5 x Ø3.2 x 6.0). Do you want the aluminium one, or the nylon one still?
   (The R30-670 drawing and CAD are outstanding.)
3. CONN-MOLEX-MICROFIT plug: 43020-0200 has panel-mount ears. The free-hanging version is 43020-0201. Pick one for the
   wire-to-wire joint.
4. Finder 22.32: the STEP delivered is the 022.3x auxiliary-contact block. No Finder SKU is in printer_v11; confirm
   whether 22.32 is still wanted before asking for the right file.
5. FUSE-5x20-T8A maps to Schurter 0001.2513. The Littelfuse 218 datasheet (0218008.MXP, 5x20 T8A time-lag) is a valid
   alternate, so there is no conflict.

## Second delivery (ingested 2026-11-20, batch 4)

New in the Drive folder since the first delivery: the two Accu STEPs (02:10Z), the Keenovo page PDF (02:06Z), the HIWIN
general catalogue (02:01Z), and a RESULT.md revision of 02:11:31Z. `RESULT_instinct_REQ-002_2026-11-20.md` is now that
revision (sha256 f5425eff6fc3083e4c7f4000eda9168f5687e633bf4847e832caf42582f46e8f). Changes vs 01:51Z: items 22 (Accu)
and 25 (Keenovo) marked DONE; item 2 notes the HIWIN catalogue; item 3 says the 3dfindit route is exhausted. RESULT.md
says the Accu account was created with the owner's approval (relayed via main); not verified here.

### STEP files staged here

| REQ item | Part | Maker | MPN | File | sha256 | Solids | Valid | BBox (mm) | Drawing check | Result | Catalogue SKU | Price |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 22 | Large flat washer M3, ISO 7093-1, A2 | Accu | HPLW-M3-A2 | HPLW-M3-A2.step (delivered as HPLW-M3-A2__step.stp; header name 406212-HPLW-M3-A2.stp, Autodesk export 2023-11-23, PRODUCT "HPW SCRIPT v4") | 7d1aee09df083a1959cbd9610e3cf88d88760cf890aefe059ff99e51e3d328f3 | 1 (4 faces: 2 planes, 2 cylinders) | yes | 9.000 x 9.000 x **0.800** | Drawing (`supplier_2026-11-19/_DEVIATIONS/WASHER-M3-LARGE.pdf`, `accu_iso7093.json`): OD 9 (+0/-0.36), ID 3.2 (+0.18/-0), T 0.9 (+0/-0.2). Model OD 9.000, ID 3.200: match at nominal. **T 0.800 = middle of the tolerance band** (0.7 to 0.9), not nominal 0.9. Volume 44.46 mm3; at 7.93 g/cm3 = 35.3 g/100 vs drawing 35 g/100 (consistent with the mean thickness) | PASS (within tolerance). The mechloop re-make `washer_flat("M3","large")` is 9 x 3.2 x **0.9** (50.02 mm3); differs by 0.1 in thickness only | WASHER-M3-LARGE | not given |
| 22 | Large flat washer M4, ISO 7093-1, A2 | Accu | HPLW-M4-A2 | HPLW-M4-A2.step (header 406216-HPLW-M4-A2.stp) | f354dade12d1e75009719e3328c0ee8c1df3ba94eba0960d56fabe2ecb2311e4 | 1 (4 faces) | yes | 12.000 x 12.000 x **1.000** | Drawing (`WASHER-M4-LARGE.pdf`): OD 12 (+0/-0.43), ID 4.3 (+0.18/-0), T 1.1 (+0/-0.2). OD 12.000, ID 4.300: match. **T 1.000 = mid-tolerance** (0.9 to 1.1). 98.58 mm3 = 78.2 g/100 vs drawing 77 | PASS (within tolerance). mechloop re-make is 12 x 4.3 x **1.1** (108.43 mm3) | WASHER-M4-LARGE | not given |

Both models sit Z = 0 up, centred on the Z axis, units mm. Whether the re-make should keep nominal T (0.9 / 1.1) or
switch to Accu's model thickness (0.8 / 1.0) is an owner decision; both are inside the drawing tolerance.

### Documents

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 25 | Keenovo_silicone-heater_page_2026-11-20.pdf | KeenovoCustomHeater__page.pdf | 58dc5d2c5608abe43dd1f4af7858ba95fc1c95a251ff0dae800aeaabf6b4d042 | 1 p, Chrome print-to-PDF (Skia) of keenovo.com/products/silicone-heater.html, 2026-11-20 02:06Z. Only /URI link annotations (70); no JavaScript, actions or embedded files. A web-page print, not a datasheet |

Not downloaded: **HIWIN_MG__catalog.pdf** (Drive 1H1QRkmweOT_9K32k8YR2vPTLhxjjVgzh, 17,883,962 bytes). It is over the Drive
connector's 10 MB download limit. It has the same size as REQ-004's HIWIN_LinearGuideway__catalog.pdf and is very likely
the same file, but Drive gives no checksum, so the sha256 dedupe could not be done. It is not the same as the HIWIN PDFs
already in vendor_docs (641,029 and 826,601 bytes). Needs a manual download if wanted.

## Third delivery (ingested 2026-11-20, batch 5)

New in the Drive folder since batch 4: Omron_D2F-01L__datasheet.pdf (02:27Z), DJ-8X20YCS__drawing.pdf (02:33Z), the two
Wham Bam pages (02:36Z), and a RESULT.md revision of 02:47:02Z. `RESULT_instinct_REQ-002_2026-11-20.md` is now that revision
(sha256 9532ba197ea779725909aa2d5d71c37daa34df49bb0595dfedb1c2a0ce933de2). Changes vs 02:11Z: status re-stated (11 of 25 met:
4, 5, 8, 13, 14, 17, 20, 21, 22, 23, 25); item 21 Century Spring now DONE (catalogue pages, chrome alloy, max about 440 °F);
item 7 Omron datasheet delivered, STEP still gated (Digi-Key CAD click-through terms left unaccepted, TraceParts key pending);
item 24 PEI kit partial (Wham Bam only). No STEP files in this delivery. No PDF has JavaScript, actions or embedded files
(Wham Bam plate page: the raw-byte "/JS" and "/AA" are inside compressed data; the pypdf walk is clean).

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 21 | CenturySpring_DJ-8X20YCS_catalog_p460_p475.pdf | DJ-8X20YCS__drawing.pdf | a60a0ff87bb233d3a7596f20895a31dcc3ef1f46613d0f9b5ffff858cd05e432 | 2 p from the Century Spring 2021 catalogue. p.460: max service temperature for chrome-alloy about 440 °F (227 °C). p.475 row DJ-8X20Y: free length 20, **rate 0.78 kgf/mm (7.6 N/mm)**, max operating (50 %): load 8.0 kgf at 10.0 mm deflection (RESULT.md reads this as "max deflection 8.0 mm"; the 8.0 is the load column) |
| 24 | WhamBam_PEI-plate-220_page_2026-11-20.pdf | WhamBam_PEI-plate-220__page.pdf | 3fa04bcb2dbd43acec2bed09a9ecc0c34e79c6ed2dc666db4b605a7da1b9ae9c | 6 p page print. RESULT.md: $35, sold out, 0.4 mm spring steel, 0.12 mm ULTEM PEI per side |
| 24 | WhamBam_magnetic-base-220_page_2026-11-20.pdf | WhamBam_magnetic-base-220__page.pdf | b4384432ec436dc87d085213b911645466421d86510cffe16d7a26996715d820 | 6 p. RESULT.md: 1 mm, 3M adhesive, rated 150 °C continual |

Not copied (same bytes already in vendor_docs): Omron_D2F-01L__datasheet.pdf (d3f2ed08...) =
`vendor_docs/ENDSTOP-MICRO_datasheet.pdf` (6 p, permission-encrypted; its only embedded file is an Adobe Distiller
`.joboptions` settings text, 3.9 kB; only action is `/OpenAction /GoTo /Fit`).
