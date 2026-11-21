# instinct_REQ-021: safety chain (e-stop, safety relay), 4x8 dowels, LRS-350-24 alternatives

Ingested 2026-11-21 (batch 21, about 04:15Z). Drive folder `REQ-021-safety-chain-and-dowels` (1X6xRLtdp1Wd1vM7ifQ8xnZ9CeSHqKEnL).
Fetched by Drive id only (no folder listing or search). Each file went into its own empty scratch directory and was read with `python -I`.
Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed. Instinct's STATUS: **PARTIAL** (items 3 dowels and 4 PSU
alternatives complete; items 1 e-stop and 2 safety relay are candidates with datasheets only, no maker STEP: Omron and TraceParts
registration held as owner decisions, Eaton STEP not retrieved). Instinct says nothing was purchased and no accounts were created.

| Delivered as (Drive id, size B) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1OeDe1OT0Z6cqAb6ueMnpRqmsF5eWsVj1, 8,129) | RESULT_instinct_REQ-021_2026-11-21.md | 5207c8aee3e0a1fefa2d4f9322bd37bbf1234205294b86a7c021c6501cbe5340 |
| RSP-320-24__cad.step (1Ce1RhE_tSRipaSt7zOcPvpoNpgiBW_sX, 2,865,925) | MeanWell_RSP-320-24_series-model_RSP-320_215x115x30.step | efaba049991398318b7d6a791711baf6a12e7e5cf3323d694cf54427b8b1802d |
| UHP-350-24__cad.step (1pD8GY9IiAta-IWsjxZh5fhSDphLH5r5J, 3,198,834) | MeanWell_UHP-350-24_series-model_UHP-350_220x62x31.step | 396c44169013ec79860b6707cdf136536b4c9e27d7fa20214d4632aff16e8dcd |
| LBA350PS24__cad.step (1M_5cxp9h6ui9jfVxBbTZ4jKViD55_d-V, 4,558,485) | XPPower_LBA350PS24_series-model_LBA350_215x115x30.step | 47d8821312c501095e5a7c3f29fcf1e13ac482f824bc16095d40cdcc86b87090 |
| 91595A150__cad.step (1S0eoBB4XtDwHjWV2D1inQF6czKrhi5Nb, 19,752) | McMaster_91595A150_dowel_pin_4x8_m6_52100.step | b9c38e7a5c9530d0c989caac8490d250a216c37eb1e80dd36cfa9148694cb243 |
| RSP-320-24__datasheet.pdf (1jw-dwNdQKWAF-0nRs8eDqeXZ7hSZZN_b, 702,316) | vendor_docs/MeanWell_RSP-320-SPEC_2026-09-04.pdf | 1576cdce738f09f076a869bdc7b20e6ea66b16f4c16bdf3cea1105a34f481a0c |
| UHP-350-24__datasheet.pdf (1CJm0uCGUcvpWyr9KesLanG2lPB3BZHwH, 806,601) | vendor_docs/MeanWell_UHP-350-SPEC_2024-11-23.pdf | 57e24e9aff543456bb6c549ff6f7ea3de823cc89bcbdea7924cd3861b81d6893 |
| LBA350PS24__datasheet.pdf (1Z57z1i8uj7cao2dieV5E_76JFDMZkYqY, 940,863) | vendor_docs/XPPower_LBA350_datasheet_2026-03-07.pdf | 9b4d3375c7a3415da7b8f197e1ae71d091705f867f9680f986884a74f8a54512 |
| A22E-M-02__datasheet.pdf (19BXOsjnc0P9ZxhnEAdqkScz_JMJ63JpU, 1,140,216) | vendor_docs/Omron_A22E_e-stop_datasheet_extract_p33-36_p41-42.pdf | 169b4528d6414d8ca5a8d90a61fb9615e7b7cbd9e1be720035874e689b004a3b |
| M22-PVT-K02__datasheet.pdf (1Om5yH-SmsYX65xoZPnFxodgrkzX3oAnl, 52,205) | vendor_docs/Eaton_M22-PVT-K02_e-stop_2NC_spec_sheet.pdf | 28e8581707fa734c208c40c4ab169e6cc4d9205ae919a2f8cfb5eafa91f9fc4d |
| M22-PVT__datasheet.pdf (1Lu-INOUmJd4v3CWoIgmm6gVfrtUhcvSN, 136,972) | vendor_docs/Eaton_M22-PVT_e-stop_operator_datasheet.pdf | 650fea888697c5b663fd35824018eb9194adfdd6517e64c6c10ee3c1b92753a7 |
| G9SE-201__datasheet.pdf (1grd4-uRN3hPGra8bzMB6Xy3yCP-kAnlX, 4,656,765) | vendor_docs/Omron_G9SE_safety_relay_datasheet_J198-E1-04.pdf | f6c7b523577c2c3eb6e6348d49572d0bc41d8ecd6fb088acc9da704cdc12dfda |
| PSR-SCP-24DC-ESP4-2X1-1X2__datasheet.pdf (1-18AlP96SAIQIjRhE5n0CgdfHmgyqnRG, 64,932) | vendor_docs/Phoenix_2981020_PSR-SCP-24DC-ESP4-2X1-1X2_datasheet.pdf | 4169a1aff0d13b3663a29dd328837b393300f84014f7076b42a740bafe273de3 |
| 91595A150__datasheet.pdf (1SbrNEmjjikQhJAVTOoZkxeRCrQTkda0P, 47,006) | vendor_docs/McMaster_91595A150_dowel_pin_drawing.pdf | 6acbb666b21f98509bb48debeafbbbb14cf9376ab4529216573171509c632881 |

None of the 14 files duplicates (by sha256) anything already in vendor_docs/ or vendor_cad/.

## Stated provenance, price and stock (per Instinct, not verified; as displayed 2026-11-20 about 19:40 to 19:55 PST, USD)
- **E-stop A: Omron A22E-M-02** (40 mm mushroom, push-lock turn-reset, 2 NC, IP65). DigiKey 343 in stock, $94.27 (5+ $82.232). PDF = pages
  33-36 + 41-42 of Omron's 52-page A22E datasheet, re-rendered at 150 dpi by Instinct (full file 19 MB, over its 9 MB limit). Maker STEP behind Omron registration (held).
- **E-stop B: Eaton M22-PVT-K02** (twist-release operator + 2 NC blocks, one PN). DigiKey 27 in stock, $100.77 (5+ $87.90). Alt build M22-PVT ($57.40,
  337 stock) + 2x M22-K01 ($17.42, 0 stock) + M22-A ($4.98) = $92.24 (Instinct's sum). Maker STEP not retrieved (Eaton routes failed in its session).
- **Safety relay A: Phoenix PSR-SCP-24DC/ESP4/2X1/1X2, 2981020.** DigiKey 23 in stock, $285.21. Datasheet is the Phoenix-authored sheet, hosted by Distrelec. STEP behind TraceParts (held).
- **Safety relay B: Omron G9SE-201** (24 VDC). DigiKey 279 in stock, $275.29 (10+ $245.102). Datasheet is Omron J198-E1 (assets.omron.eu). STEP behind Omron registration (held).
- **Dowel: McMaster 91595A150**, 52100 steel, 4 x 8, m6 (+0.004/+0.012), HRC 52 min, DIN 6325 / ISO 8734. $12.10 per 50; "Delivers Monday by 5 pm". STEP AP203 as served.
- **PSU 1: Mean Well RSP-320-24.** meanwellsource.com $78.96, "In stock / ships 3-5 business days". DigiKey does not list it. (docs/PRINTER_V12.md has Mouser 709-RSP320-24 at $53.20, 921 in stock, from an earlier check.)
- **PSU 2: Mean Well UHP-350-24.** meanwellsource.com $102.01, in stock; DigiKey says no longer available.
- **PSU 3: XP Power LBA350PS24.** DigiKey 63 in stock, $44.75 (5+ $43.408). DigiKey offers it as the suggested substitute for RSP-320-24.
- PSU STEPs are series-level (same case for every output voltage), as Instinct says.

## Header and PDF checks
- STEP headers. RSP-320: `RSP-320.stp`, Creo Elements/Direct 19.0, AP214, 2019-02-12. UHP-350: `UHP-350(201111).stp`, Creo Elements/Direct, AP214,
  2020-11-12. LBA350: `LBA350.STEP`, SolidWorks 2024, AP214, 2025-11-20. 91595A150: `91595A150_Dowel Pin.STEP`, SolidWorks 2024, AP203
  (CONFIG_CONTROL_DESIGN), 2026-01-07, author/org "McMaster Carr Supply".
- PDFs, from metadata. RSP-320: CorelDRAW X6, 2026-09-04, file "RSP-320-SPEC 2026-09-04". UHP-350: CorelDRAW X6, 2026-03-18, file "UHP-350-SPEC
  2024-11-23". LBA350: InDesign 21, 2026-05-07, footer "07 March 2026". G9SE: Omron CSM_G9SE_J198-E1_4_7, 2017, modified 2024-06-03. Eaton
  K02: iText, 2023-12-08. Eaton M22-PVT: Eaton Data Sheet Engine, 2024-06-25. Phoenix: Apache FOP, 2017-08-10. **A22E extract and dowel drawing
  are Instinct-made raster wrappers** (/Title only, created 2026-11-21 03:45Z and 03:37Z) with no text layer.
- PDF safety (pypdf full object walk). No JavaScript/JS, Launch, EmbeddedFile(s), RichMedia, XFA, SubmitForm, GoToR or ImportData in any file. Notes:
  - **G9SE**: encrypted with an empty user password (owner-permission restrictions only, R4/AES-128). Its /OpenAction is a plain `/GoTo` to page 1
    with `/Fit`, and its /AcroForm has empty `/Fields`. Both are benign.
  - /URI link annotations only. LBA350: 2 (xppower.com certification tab). Eaton K02: 32 (eaton.com documents incl. a `M22-PV_-K_(2).stp` link and
    social links). Phoenix: 2 (phoenixcontact.com product page). RSP/UHP: 8 each (meanwell.cc/.com.cn/.com, one youtu.be). None was followed.

## PSU comparison against the v12 LRS-350-24
Reference: `mechloop/parts/vendor/meanwell_lrs.json` ("350") and `vendor_docs/LRS-350-SPEC.PDF` (2025-09-12). The STEP is `vendor_cad/meanwell_LRS-350.stp`.
v12 (`designs/printer_v12.py`): `psu_lrs("LRS-350-24")` sits on the tray on its base, fixed by **4x M4 x 6 from below** through the 3.175 tray,
so the screw goes **2.8 mm** into the supply. The printed `mains_cover_psu` hood covers the terminal end (x -89.5..33.5, y 60..77, top 56.04).
The side holes are not used.

### Geometry (build123d, python -I; hole centres from cylinder pairs; frame: L from the terminal end, W from the AC/L long edge, H from the base)
| | LRS-350-24 (v12) | XP Power LBA350PS24 | Mean Well RSP-320-24 | Mean Well UHP-350-24 |
|---|---|---|---|---|
| STEP solids / valid | 17 / ok | 22 / all valid | 21 / **1 invalid** (main case shell, OCCT check) | 35 / all valid |
| STEP bbox (mm) | 215.0 x 115.0 x 30.9 (0.9 below base) | **215.0 x 115.0 x 30.0** | 215.0 x 115.0 x 30.9 (same case as LRS) | **220.0 x 62.0 x 31.3** |
| Datasheet size | 215 x 115 x 30 ±1 | 215 ±1 x 115 ±0.5 x 30 ±0.5 | 215 x 115 x 30 ±1 | 220 x 62 x 31 ±1 |
| Base holes | 4x M4 L=3 max, 150 x 50, 32.5 / 32.5 | **4x M4, 150 ±0.4 x 50 ±0.2, 32.5 / 32.5**, L=4 max; STEP 3.3 tap holes at 32.5/182.5 x 32.55/82.55 | 4x M4 L=3, 150 x 50, 32.5/32.5 (STEP 3.1 at 32.5/182.5 x 32.5/82.5) | 4x dia 3.3 through-holes (M3), pattern about 210.7 x 46.4 |
| Side holes | 2x M4 per side, 150 apart, 32.5 from end, 12.5 up, L=5 | **2x M4 per side, 150 ±0.4, 32.5, 12.5 ±0.3 up**, L=4 max (STEP 4.0 dia) | same as LRS (STEP 3.1 at 32.5/182.5, 12.5 up) | none in the LRS pattern |
| Terminal block | 9-pos, pitch 9.5, at L 2.5-17.2, W 4.5-91.5; 1 L, 2 N, 3 FG, 4-6 -V, 7-9 +V; screws from top; ADJ + LED beyond pin 9 | **9-pos, pitch 9.5 (STEP), L 0.8-16.9, W 3.9-91.3; L, N, FG, -V x3, +V x3 in the same order; ADJ + LED beyond +V**; integrated finger cover | same as LRS (STEP block at L 2.5-17.2, W 5-92) | 3-pos AC (TB1) at one end, 2x 2-pos DC (TB2/3) at the other, plus JST DC-OK |
| Cooling | fan 60 mm, top face, 47.45 from far end / 36.7 from ADJ edge; on at 50 degC | fan (60 mm guard on top, measured from drawing about 48 / 38: same place within about 1 mm); fan not modelled in STEP; on/off control not stated | fan 60 mm, same position as LRS (STEP) | **fanless**: must be on a 450 x 450 Al plate (datasheet) |
| Input | 90-132 / 180-264 VAC **by switch**, no PFC | **90-264 VAC universal, active PFC** (PF 0.98/0.95) | 88-264 VAC universal, PFC | 90-264 VAC, PFC |
| Input current | 6.8 A / 3.4 A typ (115/230) | 4.5 A / 2.2 A max | 4 A / 2 A typ | 4 A / 2 A typ |
| Inrush | 60 A typ (115 and 230) | 30 A @115 / 60 A @230 max, cold | 20 A / 40 A typ | 30 A / 60 A typ, cold |
| Output | 24 V 14.6 A 350.4 W; adj 21.6-28.8 | **24 V 14.6 A 350 W**; adj 20.0-26.4 | 24 V **13.4 A 321.6 W**; adj 20-26.4 | 24 V 14.6 A 350.4 W |
| Efficiency | 88 % | 88 % (230 VAC) | 89 % | 94 % |
| Hold-up / leakage | 16/12 ms typ / 2 mA | 8 ms min / 1.0 mA | 8 ms typ / <1 mA | n/a / n/a |
| Derating | 100 % to 50 degC, 60 % at 70 | 100 % to 50 degC, 60 % at 70 | see curve | Tcase based |
| Mass | 0.76 kg | 0.80 kg | 0.9 kg (packed) | 0.68 kg |
| Price / stock (Instinct) | no stock (189-day lead per PRINTER_V12.md) | $44.75, DigiKey 63 | $78.96 meanwellsource | $102.01 meanwellsource |

**Drop-in verdict.**
- **XP Power LBA350PS24 is a drop-in replacement** for the LRS-350-24 in the existing bay with no re-layout. It has the same 215 x 115 x 30 envelope,
  the same 4x M4 base pattern (150 x 50, 32.5 / 32.5, centred, so either end orientation fits), and the same side pattern. The terminal block is in
  the same place, with the same 9 positions in the same order at 9.5 pitch, under the existing hood footprint (y 60.6 to 76.7 against the hood's
  y 60 to 77). The fan is in the same place and the rating is the same (350 W, 14.6 A). The v12 M4 x 6 screw goes 2.8 mm in, which is inside both
  the LBA's 4 mm and the LRS's 3 mm limit.
  Differences to note: there is no 115/230 switch (universal input with PFC, so lower input current on the T8A fuse); hold-up is shorter (8 ms min);
  the trim range tops out at 26.4 V (not 28.8 V); the fan control law is not stated (it may run continuously); and airflow direction is not drawn.
  The STEP is simplified (no fan; internals are one block), which is fine for packaging. Changing `PSU_MODEL` also needs a new parts entry,
  `electrical.py` numbers and BOM; that is not done here.
- **Mean Well RSP-320-24 is also mechanically drop-in** by its current datasheet (2026-09-04: 215 x 115 x 30, LRS-identical holes, terminals and fan;
  its STEP is the LRS case). It is 13.4 A / 321.6 W (about 84 % at the 270 W peak stated in PRINTER_V12.md). **PRINTER_V12.md's "215 x 115 x 50 mm,
  20 mm taller" note is contradicted by this datasheet and STEP.** That note probably describes the older RSP-320 case.
- **UHP-350-24 is not a drop-in**: 220 x 62 x 31, M3 through-holes, split terminals, fanless and needs a 450 x 450 aluminium plate.

## Safety devices (from the datasheets, for a later re-make; no maker STEP)
| Item | Key dimensions | Terminals / ratings | Notes |
|---|---|---|---|
| Omron A22E-M-02 | 40 dia head; **32 in front of panel**; **54.7 behind the panel face** (41.2 switch-block section, 34 block height); bezel step 6.5, 18.5; tolerance ±0.8 | 2 NC switch blocks, screw terminals; 10 A @100 VAC and 10 A @24 VDC resistive (structure page; Instinct quotes DigiKey's 8 A DC) | **Panel cutout and panel-thickness range are not in the extracted pages.** 22.3 mm is only per DigiKey via Instinct. Use the full Omron A22E datasheet (common A22N cutout) before cutting |
| Eaton M22-PVT-K02 | 38 mm mushroom, front 35 mm; **22.5 mm hole**; spec sheet depth "2 in" (product-level, not a drawing) | 2 NC (positively driven); IP67/IP69K | The spec sheet's "Contact configuration" field reads **"1 NO-2 NC"** while the title says 2NC (Eaton data inconsistency). Its links include an Eaton `M22-PV_-K_(2).stp` (not fetched) |
| Omron G9SE-201 | **17.5 W**, body height 124 (144.5 with mounting tabs: 71 + 73.5 from the rail centre), **depth 111.6** (109 body); screw-mount holes 2x 4.2 / M4 at 133 ±0.3; R2.3 | **Push-In Plus front terminals (not screw)**: A1, A2, T11, T12, T21, T22, T31, T32, T33, X1, 13-14, 23-24; AWG24-16, strip 8-10 mm; 2 NO safety 250 VAC/30 VDC 5 A; aux PNP 100 mA; 24 VDC, 3 W; PL e / Cat 4 | Instinct says "screw terminals"; the datasheet says Push-In Plus. 3 A max when units are mounted side by side; needs PFP-M end stops on DIN rail; 50 mm clearance above and below |
| Phoenix PSR-SCP-24DC/ESP4/2X1/1X2 | **22.5 W x 99 H x 114.5 D** | Plug-in M3 screw terminals, 0.2-2.5 mm2, strip 7 mm; 2 enabling paths 6 A, 1 signalling path; 24 VDC 50 mA; auto/manual start; stop cat 0 | The datasheet headline says **"single-channel"** (REQ asked for dual-channel). It is at the 22.5 mm width limit |

## Dowel 91595A150 (build123d)
1 solid, valid. Dia 4.000 (nominal; m6 +0.004/+0.012 is not modelled), length 8.000, axis Z, volume 92.0 mm3. One end is a crowned dome (0.6 high),
the other a 0.78 lead cone plus a 0.52 dome. This matches the McMaster drawing (4.000 +0.012/+0.004 x 8, rounded ends). **Match.** Press-fit hole size in
the aluminium parts is still a build question (Instinct says so too).

## Odd / for the owner
- **RSP-320 height**: PRINTER_V12.md (Questions for the owner, 0) says RSP-320-24 is 50 mm tall and would need a v12.1 re-layout. The new datasheet
  and STEP both say 30 mm with the LRS pattern. Recheck before re-laying out anything.
- G9SE terminals are Push-In, not screw (Instinct misread). Phoenix 2981020 is "single-channel" by its headline. Eaton spec sheet says 1 NO-2 NC.
- A22E cutout is not in the delivered extract.
- REQ-018's RESULT revision in this batch says an **SKF account was created "with owner approval"**. See instinct_REQ-018/MANIFEST.md, batch 21.
