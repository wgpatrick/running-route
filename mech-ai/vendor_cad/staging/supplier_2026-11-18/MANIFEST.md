# Supplier CAD batch 2026-11-18: staging manifest

Copied 2026-11-19 from the owner's Google Drive folder `1YzqW0h4VMvjzZb2Gk-xAsHR37Rsqf4xI` (main folder: exact matches) and its subfolder `_DEVIATIONS-read-me-first` (`1mQzuez8NFRVWdwxjJud4T32HAwoPB58z`), here as `_DEVIATIONS/`. The supplier report is `00-REPORT-supplier-cad-table.md`.

**Staging only.** Nothing here is in `vendor_cad/inbox/`, so design builds do not pick any of it up. Whoever owns the catalogue decides what gets promoted. Files in `_DEVIATIONS/` are NOT what was requested: the T-slot parts belong to McMaster's 5 mm-slot system, not to a true 2020 6 mm slot.

- Downloaded: 67 of 67 files in the main folder (66 content files plus the report) and 16 of 16 in `_DEVIATIONS/`, 83 in all. These match the report's own count. Every file size matches its Drive metadata.
- Largest file: SHCS-M5x70.step at 4.1 MB. None is over 5 MB, so none comes near the 100 MB git limit.
- Checks were cheap and treated the files as data only. Each STEP header was read, and each STEP was loaded with OCP `STEPControl_Reader` (in `mech-ai/.venv`, `python -I`) to get the solid count and bounding box. All 38 STEP files parse and all declare `SI_UNIT(.MILLI.,.METRE.)`. For each PDF only the `%PDF` magic number was checked.
- The bounding boxes are in mm, in each file's own axes.

## Files

| File | Folder | Status (report) | Supplier + PN | Bytes | STEP bbox (mm) | Check |
|---|---|---|---|---|---|---|
| 00-REPORT-supplier-cad-table.md | main | report | - - | 19,468 | - | text |
| BLOWER-4010-24V.pdf | main | PDF ONLY | GDSTIME GDB4010 (A-Type) | 291,258 | - | PDF header OK (not opened further) |
| ENDSTOP-MICRO.pdf | main | PDF ONLY | Omron D2F (D2F-01L) | 850,668 | - | PDF header OK (not opened further) |
| FHCS-M4x40.pdf | main | DELIVERED | McMaster-Carr 91294A204 | 141,139 | - | PDF header OK (not opened further) |
| FHCS-M4x40.step | main | DELIVERED | McMaster-Carr 91294A204 | 1,604,565 | 8 x 8 x 40 | parses (1 solid), mm; OK: 8.0 head dia x 40.0 overall (flat head, length is overall). Catalogue generates ISO 10642 via bd_warehouse; no FHCS dims in the vendor JSONs to compare |
| HOST-RPI-ZERO-2W.pdf | main | PDF ONLY | Raspberry Pi Zero 2 W | 163,618 | - | PDF header OK (not opened further) |
| INLET-C14-SW-FUSE.pdf | main | DELIVERED | Schurter DD11.0121.1110 (CAD 0100.2571) | 450,651 | - | PDF header OK (not opened further) |
| INLET-C14-SW-FUSE.step | main | DELIVERED | Schurter DD11.0121.1110 (CAD 0100.2571) | 2,998,289 | 30.5 x 65 x 38.7 | parses (1 solid), mm; CHECK: bbox 30.5 x 65.0 x 38.7 vs report's '27x46x38 envelope'. Report figure looks like the body only; bbox matches schurter_dd11.json flange A 65 x 30.5 |
| NUT-M2.5.pdf | main | DELIVERED | McMaster-Carr 90591A270 | 99,205 | - | PDF header OK (not opened further) |
| NUT-M2.5.step | main | DELIVERED | McMaster-Carr 90591A270 | 469,202 | 5 x 5.75 x 2 | parses (1 solid), mm; OK: 5.0 AF / 5.75 AC x 2.0 high = catalogue (ISO 4032 and mcmaster_fasteners.json) |
| NUT-M3-NYLOC.pdf | main | DELIVERED | McMaster-Carr 90576A102 | 90,162 | - | PDF header OK (not opened further) |
| NUT-M3-NYLOC.step | main | DELIVERED | McMaster-Carr 90576A102 | 505,883 | 5.5 x 6.351 x 4 | parses (2 solids), mm; OK: 5.5 AF x 4.0 high, 2 solids (nut + nylon insert) = catalogue NUT_ISO10511 M3 4.0 |
| NUT-M3.pdf | main | DELIVERED | McMaster-Carr 90591A250 | 100,541 | - | PDF header OK (not opened further) |
| NUT-M3.step | main | DELIVERED | McMaster-Carr 90591A250 | 507,180 | 5.5 x 6.325 x 2.4 | parses (1 solid), mm; OK: 5.5 AF / 6.33 AC x 2.4 high = catalogue |
| NUT-M4.pdf | main | DELIVERED | McMaster-Carr 90591A255 | 100,444 | - | PDF header OK (not opened further) |
| NUT-M4.step | main | DELIVERED | McMaster-Carr 90591A255 | 520,661 | 7 x 8.05 x 3.2 | parses (1 solid), mm; OK: 7.0 AF / 8.05 AC x 3.2 high = catalogue ISO 4032 M4 (not yet in mcmaster_fasteners.json part_numbers) |
| PROBE-OMRON-E2E-X5ME1.pdf | main | DELIVERED | Omron E2E-X5ME1 | 1,372,031 | - | PDF header OK (not opened further) |
| PROBE-OMRON-E2E-X5ME1.step | main | DELIVERED | Omron E2E-X5ME1 | 134,190 | 21 x 21 x 57 | parses (3 solids), mm; OK: 3 solids (body + 2 nuts, as report says), 21.0 x 21.0 x 57.0 (21 = M12 nut across corners) |
| RELAY-BTT-V1.2.pdf | main | PDF ONLY | BIGTREETECH Relay V1.2 | 1,199,761 | - | PDF header OK (not opened further) |
| SHCS-M2.5x12.pdf | main | DELIVERED | McMaster-Carr 91290A008 | 152,983 | - | PDF header OK (not opened further) |
| SHCS-M2.5x12.step | main | DELIVERED | McMaster-Carr 91290A008 | 899,841 | 4.5 x 4.5 x 14.5 | parses (1 solid), mm; OK: head 4.5 dia, 14.5 overall = 12 + 2.5 head (ISO 4762 / catalogue) |
| SHCS-M2.5x16.pdf | main | DELIVERED | McMaster-Carr 91290A200 | 132,255 | - | PDF header OK (not opened further) |
| SHCS-M2.5x16.step | main | DELIVERED | McMaster-Carr 91290A200 | 1,126,168 | 4.5 x 4.5 x 18.5 | parses (1 solid), mm; OK: head 4.5 dia, 18.5 overall = 16 + 2.5 head (ISO 4762 / catalogue) |
| SHCS-M3x10.pdf | main | DELIVERED | McMaster-Carr 91290A115 | 152,244 | - | PDF header OK (not opened further) |
| SHCS-M3x10.step | main | DELIVERED | McMaster-Carr 91290A115 | 1,737,216 | 5.5 x 5.5 x 13 | parses (1 solid), mm; OK: head 5.5 dia, 13 overall = 10 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x12.pdf | main | DELIVERED | McMaster-Carr 91290A500 | 149,763 | - | PDF header OK (not opened further) |
| SHCS-M3x12.step | main | DELIVERED | McMaster-Carr 91290A500 | 888,948 | 5.5 x 5.5 x 15 | parses (1 solid), mm; OK: head 5.5 dia, 15 overall = 12 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x16.pdf | main | DELIVERED | McMaster-Carr 91290A120 | 168,397 | - | PDF header OK (not opened further) |
| SHCS-M3x16.step | main | DELIVERED | McMaster-Carr 91290A120 | 2,009,735 | 5.5 x 5.5 x 19 | parses (1 solid), mm; OK: head 5.5 dia, 19 overall = 16 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x18.pdf | main | DELIVERED | McMaster-Carr 91290A121 | 163,512 | - | PDF header OK (not opened further) |
| SHCS-M3x18.step | main | DELIVERED | McMaster-Carr 91290A121 | 2,118,063 | 5.5 x 5.5 x 21 | parses (1 solid), mm; OK: head 5.5 dia, 21 overall = 18 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x20.pdf | main | DELIVERED | McMaster-Carr 91290A123 | 183,010 | - | PDF header OK (not opened further) |
| SHCS-M3x20.step | main | DELIVERED | McMaster-Carr 91290A123 | 2,222,559 | 5.5 x 5.5 x 23 | parses (1 solid), mm; OK: head 5.5 dia, 23 overall = 20 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x40.pdf | main | DELIVERED | McMaster-Carr 91290A136 | 147,123 | - | PDF header OK (not opened further) |
| SHCS-M3x40.step | main | DELIVERED | McMaster-Carr 91290A136 | 2,103,201 | 5.5 x 5.5 x 43 | parses (1 solid), mm; OK: head 5.5 dia, 43 overall = 40 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x45.pdf | main | DELIVERED | McMaster-Carr 91290A079 | 128,891 | - | PDF header OK (not opened further) |
| SHCS-M3x45.step | main | DELIVERED | McMaster-Carr 91290A079 | 1,147,591 | 5.5 x 5.5 x 48 | parses (1 solid), mm; OK: head 5.5 dia, 48 overall = 45 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x5.pdf | main | DELIVERED | McMaster-Carr 91290A110 | 139,253 | - | PDF header OK (not opened further) |
| SHCS-M3x5.step | main | DELIVERED | McMaster-Carr 91290A110 | 1,499,911 | 5.5 x 5.5 x 8 | parses (1 solid), mm; OK: head 5.5 dia, 8 overall = 5 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x50.pdf | main | DELIVERED | McMaster-Carr 91290A137 | 156,362 | - | PDF header OK (not opened further) |
| SHCS-M3x50.step | main | DELIVERED | McMaster-Carr 91290A137 | 2,114,229 | 5.5 x 5.5 x 53 | parses (1 solid), mm; OK: head 5.5 dia, 53 overall = 50 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x6.pdf | main | DELIVERED | McMaster-Carr 91290A111 | 142,544 | - | PDF header OK (not opened further) |
| SHCS-M3x6.step | main | DELIVERED | McMaster-Carr 91290A111 | 1,559,832 | 5.5 x 5.5 x 9 | parses (1 solid), mm; OK: head 5.5 dia, 9 overall = 6 + 3 head (ISO 4762 / catalogue) |
| SHCS-M3x8.pdf | main | DELIVERED | McMaster-Carr 91290A400 | 136,088 | - | PDF header OK (not opened further) |
| SHCS-M3x8.step | main | DELIVERED | McMaster-Carr 91290A400 | 669,210 | 5.5 x 5.5 x 11 | parses (1 solid), mm; OK: head 5.5 dia, 11 overall = 8 + 3 head (ISO 4762 / catalogue) |
| SHCS-M5x10.pdf | main | DELIVERED | McMaster-Carr 91290A224 | 147,131 | - | PDF header OK (not opened further) |
| SHCS-M5x10.step | main | DELIVERED | McMaster-Carr 91290A224 | 1,619,567 | 8.5 x 8.5 x 15 | parses (1 solid), mm; OK: head 8.5 dia, 15 overall = 10 + 5 head (ISO 4762 / catalogue) |
| SHCS-M5x12.pdf | main | DELIVERED | McMaster-Carr 91290A228 | 148,493 | - | PDF header OK (not opened further) |
| SHCS-M5x12.step | main | DELIVERED | McMaster-Carr 91290A228 | 1,704,974 | 8.5 x 8.5 x 17 | parses (1 solid), mm; OK: head 8.5 dia, 17 overall = 12 + 5 head (ISO 4762 / catalogue) |
| SHCS-M5x30.pdf | main | DELIVERED | McMaster-Carr 91290A194 | 173,495 | - | PDF header OK (not opened further) |
| SHCS-M5x30.step | main | DELIVERED | McMaster-Carr 91290A194 | 3,618,907 | 8.499 x 8.499 x 35 | parses (1 solid), mm; OK: head 8.499 dia, 35 overall = 30 + 5 head (ISO 4762 / catalogue) |
| SHCS-M5x35.pdf | main | DELIVERED | McMaster-Carr 91290A195 | 176,523 | - | PDF header OK (not opened further) |
| SHCS-M5x35.step | main | DELIVERED | McMaster-Carr 91290A195 | 3,821,749 | 8.499 x 8.499 x 40 | parses (1 solid), mm; OK: head 8.499 dia, 40 overall = 35 + 5 head (ISO 4762 / catalogue) |
| SHCS-M5x70.pdf | main | DELIVERED | McMaster-Carr 91290A201 | 186,354 | - | PDF header OK (not opened further) |
| SHCS-M5x70.step | main | DELIVERED | McMaster-Carr 91290A201 | 4,136,815 | 8.499 x 8.499 x 75.05 | parses (1 solid), mm; OK: head 8.499 dia, 75.05 overall = 70 + 5 head (ISO 4762 / catalogue) |
| SHCS-M5x8.pdf | main | DELIVERED | McMaster-Carr 91290A222 | 138,361 | - | PDF header OK (not opened further) |
| SHCS-M5x8.step | main | DELIVERED | McMaster-Carr 91290A222 | 1,578,761 | 8.5 x 8.5 x 13 | parses (1 solid), mm; OK: head 8.5 dia, 13 overall = 8 + 5 head (ISO 4762 / catalogue) |
| SPRING-DIE-DJ-8X20YCS.pdf | main | DELIVERED | Century Spring DJ-8X20YCS | 535,013 | - | PDF header OK (not opened further) |
| SPRING-DIE-DJ-8X20YCS.step | main | DELIVERED | Century Spring DJ-8X20YCS | 1,703,553 | 20 x 7.36 x 7.36 | parses (1 solid), mm; CHECK: free length 20.0 OK; OD 7.36 in the model vs report's '~8 mm measured OD' (8 mm is the hole designation; model OD is 7.36) |
| WASHER-M2.5.pdf | main | DELIVERED | McMaster-Carr 91166A190 | 108,430 | - | PDF header OK (not opened further) |
| WASHER-M2.5.step | main | DELIVERED | McMaster-Carr 91166A190 | 256,395 | 6 x 6 x 0.6 | parses (1 solid), mm; OK: 6.0 OD; thickness 0.6 vs catalogue 0.5 (hardware.WASHER mid of ISO 7089 0.45-0.55): +0.1, above the ISO band |
| WASHER-M3.pdf | main | DELIVERED | McMaster-Carr 91166A210 | 107,637 | - | PDF header OK (not opened further) |
| WASHER-M3.step | main | DELIVERED | McMaster-Carr 91166A210 | 234,915 | 7 x 7 x 0.6 | parses (1 solid), mm; OK: 7.0 OD; thickness 0.6 vs catalogue 0.5 (ISO 7089 0.45-0.55): +0.1, above the ISO band |
| WASHER-M4.pdf | main | DELIVERED | McMaster-Carr 91166A230 | 110,177 | - | PDF header OK (not opened further) |
| WASHER-M4.step | main | DELIVERED | McMaster-Carr 91166A230 | 246,646 | 9 x 9 x 0.9 | parses (1 solid), mm; OK: 9.0 OD; thickness 0.9 vs catalogue 0.8 (ISO 7089 0.7-0.9): +0.1, at the top of the band |
| WASHER-M5.pdf | main | DELIVERED | McMaster-Carr 91166A240 | 111,655 | - | PDF header OK (not opened further) |
| WASHER-M5.step | main | DELIVERED | McMaster-Carr 91166A240 | 233,932 | 10 x 10 x 1.1 | parses (1 solid), mm; OK: 10.0 OD; thickness 1.1 vs catalogue 1.0 (ISO 7089 0.9-1.1): +0.1, at the top of the band |
| BRKT-2020.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5537T935 | 111,527 | - | PDF header OK (not opened further) |
| BRKT-2020.step | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5537T935 | 1,812,779 | 18 x 25.7 x 25.7 | parses (7 solids), mm; OK (parses): 7 solids (bracket + included fasteners), 18.0 x 25.7 x 25.7; 5 mm-slot system |
| CTRL-OCTOPUS-V1.0.pdf | _DEVIATIONS | PDF ONLY, V1.0 not V1.1 (EXCEPTION) | BIGTREETECH Octopus V1.0 | 1,285,575 | - | PDF header OK (not opened further) |
| EXT2020-PROFILE.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5537T101-5537T044 | 94,271 | - | PDF header OK (not opened further) |
| EXT2020-PROFILE.step | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5537T101-5537T044 | 391,668 | 20 x 20 x 152.4 | parses (1 solid), mm; DISCREPANCY: 20.0 x 20.0 x 152.4 (1/2 ft) OK; slot opening 5.0 (catalogue 6.0), lip ~1.8 (catalogue 2.0), depth 6.1-6.4 (catalogue 6.0), cavity 11.5 (catalogue 12.0), bore 4.3 (catalogue 4.2). See below |
| GT2-20T-B5-W9.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | ServoCity 3422-0005-0020 | 105,719 | - | PDF header OK (not opened further) |
| GT2-20T-B5-W9.step | _DEVIATIONS | DELIVERED AS DEVIATION | ServoCity 3422-0005-0020 | 2,783,429 | 15 x 18 x 15 | parses (4 solids), mm; OK: byte-identical to GT2-20T-B5.step (same part, as report states) |
| GT2-20T-B5.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | ServoCity 3422-0005-0020 | 105,719 | - | PDF header OK (not opened further) |
| GT2-20T-B5.step | _DEVIATIONS | DELIVERED AS DEVIATION | ServoCity 3422-0005-0020 | 2,783,429 | 15 x 18 x 15 | parses (4 solids), mm; OK: 4 solids, 15.0 x 18.0 x 15.0 (6 mm-belt pulley as report states) |
| NUT-M5.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 90591A260 | 102,773 | - | PDF header OK (not opened further) |
| NUT-M5.step | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 90591A260 | 503,468 | 8 x 9.2 x 4 | parses (1 solid), mm; OK vs report: 8.0 AF / 9.2 AC x 4.0 high (DIN 934). Catalogue default ISO 4032 M5 is 4.7; hex_nut(standard='din934') has 4.0 |
| SHCS-M4x6.pdf | _DEVIATIONS | PDF ONLY (EXCEPTION, STEP withheld >5 MB) | McMaster-Carr 90128A208 (zinc) | 220,551 | - | PDF header OK (not opened further) |
| TNUT-2020-M3.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5278N42 | 117,629 | - | PDF header OK (not opened further) |
| TNUT-2020-M3.step | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5278N42 | 625,783 | 12 x 7.7 x 5.6 | parses (2 solids), mm; DISCREPANCY: 2 solids (body + 3 mm spring ball); body 12.0 along x 7.7 across x 4.6 high, ball +1.0 below; thread ~4.5 long (catalogue 3.4). See below |
| TNUT-2020-M5.pdf | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5278N44 | 117,918 | - | PDF header OK (not opened further) |
| TNUT-2020-M5.step | _DEVIATIONS | DELIVERED AS DEVIATION | McMaster-Carr 5278N44 | 703,029 | 12 x 7.7 x 5.6 | parses (2 solids), mm; DISCREPANCY: same body as M3; thread ~3.3 long + 6.0 dia top countersink (catalogue 3.4). See below |

## Discrepancies against the catalogue (read-only comparison; no code changed)

The catalogue values come from `mechloop/parts/vendor/tslot_2020_hardware.json` (slot `used` = Misumi HFS5-2020 community DXF, `alternative` = B-type slot-6 community STEP; T-nut values all ASSUMED), `mcmaster_fasteners.json`, `iso_fasteners.json`, `mechloop/parts/hardware.py` (`WASHER`) and `mechloop/parts/__init__.py` (`NUT_ISO10511`).

### McMaster 20 mm extrusion 5537T101 (`_DEVIATIONS/EXT2020-PROFILE.step`)

Measurements come from ray casts on the mid-length cross-section, in steps of 0.2 mm, refined to 0.01 to 0.02 mm at the edges. Distances are from the profile centre, and the nominal outer face is at 10.0.

| Quantity | STEP (measured) | Catalogue used (HFS5 DXF) | Alt (B-type) | Sim solid |
|---|---|---|---|---|
| Slot opening | **5.00** (lip edges at +/-2.50) | 6.0 | 6.0 | 6.2 |
| Lip thickness | **~1.8** (underside 8.03-8.09 from centre; lip top 9.78-9.84 near the opening because the face dips slightly near the slot and reaches 10.0 only at >=8 mm off-centre; 1.97 if measured from the nominal face plane) | 2.0 | 1.5 | none |
| Slot depth, face to floor | **6.40** on the centre line (floor at 3.60); 6.26 at +/-2.0; 6.10 at +/-2.4 | 6.0 (centre groove 6.3) | 5.3 (5.7) | 5.0 |
| Cavity width under lips | **11.5** (cavity edge at +/-5.75) | 12.0 | 12.0 | - |
| Cavity walls | 45 deg | 45 deg | - | - |
| Centre bore | 4.30 dia | 4.2 | - | - |
| Length | 152.4 (1/2 ft) | - | - | - |

### McMaster drop-in T-nuts 5278N42 (M3) / 5278N44 (M5) (`_DEVIATIONS/TNUT-2020-*.step`)

Both files contain two solids: the nut body and a 3.0 mm spring ball. The bodies are the same; only the hole differs. In the file's axes, x runs along the slot, y across it, and z along the screw axis.

| Quantity | STEP (measured) | Catalogue (all ASSUMED) |
|---|---|---|
| Overall height, body only | **4.6** (z -2.3 to +2.3); the ball sticks out a further 1.0 below (total 5.6) | 4.4 |
| Neck/tongue that stands in the slot opening | **~0.6 high** (from the shoulder at z +1.7 to the top at +2.3), **~4.9 wide** (y +/-2.45) | 1.0 high, 5.8 wide |
| Body under the lips (shoulder to bottom) | **4.0** | 3.4 |
| Span across the slot | **7.7** (rounded R15 sides so it can rotate in) | 10.3 |
| Width along the slot | **12.0** | 6.0 |
| Thread length, M3 | **~4.45** (threaded r=1.5 faces from z -2.22 to +2.25, the full height including the tongue) | 3.4 |
| Thread length, M5 | **~3.3** (threaded r=2.5 faces from z -1.68 to +1.61), plus a 6.0 dia countersink in the tongue (z +1.83 to +2.18) | 3.4 |
| Hole position | M3 at x = -3.0, M5 at x = -2.0; ball at x = +3.0 | centred |

What this means for a screw-length check (derived here from the two STEP files and not checked by the design code):
- With the nut's shoulder pulled up against the lip underside (8.03 from the centre), the tongue top sits at about 8.63. That is about 1.2 mm below the local lip top, or 1.37 mm below the nominal face.
- For M3, the thread starts at the tongue top and runs about 4.45 mm.
- For M5, the thread starts about 0.1 mm below the shoulder, about 2.06 mm below the nominal face, and runs about 3.3 mm.
- On the slot centre line, the screw tip has about 4.4 mm below the lip underside before it reaches the floor (8.03 - 3.60).
- The ball bears on the floor, under spring load.
- All of this assumes the 5 mm-slot extrusion. These nuts are sized for that rail, not for a 6 mm-slot 2020.

### Fasteners
- **SHCS (all 19 lengths):** head diameter and overall length match ISO 4762 and the `mcmaster_fasteners.json` pattern exactly (M2.5 4.5 x 2.5 head, M3 5.5 x 3.0, M5 8.5 x 5.0). The only difference is the M5x70 overall length, 75.05 instead of 75.0.
- **SHCS-M4x6:** the catalogue's `mcmaster_fasteners.json` lists **91290A139** (black oxide) for M4x6. The report says McMaster has no black-oxide M4x6 and supplies **90128A208** (zinc-plated), PDF only (its STEP is over 5 MB). Treat this as a part-number conflict to resolve.
- **Hex nuts:**
  - M2.5, M3 and M4 match the catalogue (2.0, 2.4 and 3.2 high).
  - NUT-M5 (in `_DEVIATIONS`) is 4.0 high (DIN 934), against the catalogue default of 4.7 (ISO 4032). That is already known: `hex_nut(standard="din934")` uses 4.0.
- **NUT-M3-NYLOC:** 4.0 high, which matches `NUT_ISO10511["M3"]`.
- **Washers:** outside diameters match `hardware.WASHER`, but every supplier washer is **0.1 mm thicker** than the catalogue value: M2.5 0.6 vs 0.5, M3 0.6 vs 0.5, M4 0.9 vs 0.8, M5 1.1 vs 1.0. For M2.5 and M3 that is above the ISO 7089 tolerance band the catalogue cites (0.45 to 0.55).
- **FHCS-M4x40:** 8.0 head diameter x 40.0 overall. The vendor JSONs have no FHCS row to compare against.

### Other report-vs-file notes
- **INLET-C14-SW-FUSE.step:** the bounding box is 30.5 x 65.0 x 38.7, not the 27 x 46 x 38 "envelope" the report states. It does match `schurter_dd11.json` flange A (65 x 30.5), so the report's figure is probably the body only.
- **SPRING-DIE-DJ-8X20YCS.step:** the free length is 20.0 as stated, but the model's outside diameter is 7.36, while the report says "~8 mm measured OD".
- **GT2-20T-B5.step and GT2-20T-B5-W9.step:** the two files are byte-identical (same SHA-256), and so are the two PDFs. The report says they are the same part.

## Mentioned in the report but not in Drive (none failed to download)

These have no file because of the report's own status:
- WASHER-M3-LARGE and WASHER-M4-LARGE: NOT FOUND.
- THUMBNUT-DIN466-M4 (KIPP K0143.04): CAD needs an account.
- MGN12H, MGN12-R-250, MGN12-R-300: the HIWIN site needs a login.
- NEMA17-LEADSCREW: no STEP exists, and the datasheet download is blocked.
- T8-NUT, GT2-IDLER-20T-B5 and GT2-IDLER-20T-B5-W9: NOT FOUND.
- FAN-3010-CG3010U24: no CAD or PDF exists.
- SHEET-PEI-235: no CAD exists.

These have a PDF but no STEP:
- SHCS-M4x6: STEP withheld, about 9 MB.
- CTRL-OCTOPUS-V1.1: only the V1.0 PDF was delivered; the V1.0 STEP is 24 MB and the wrong revision.
- BLOWER-4010-24V, RELAY-BTT-V1.2, HOST-RPI-ZERO-2W and ENDSTOP-MICRO: PDF only.
