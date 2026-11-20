# instinct_REQ-008: priority queue (Schurter inlet / drawer / fuses, Phoenix PLC-RSC relay)

Checked 2026-11-20 (batch 5, about 03:30Z). Google Drive `mechloop handoff/results/REQ-008-priority-queue/`
(folder 1W3K9YtzrWAnS2H6KbsBgHhr6L_M__EcD) held only RESULT.md (03:29:48Z), copied here as
`RESULT_instinct_REQ-008_2026-11-20.md` (sha256 a307c60b00accf6378239115c7e58e16638eadf3bef472ef54886a4a18542760). Instinct's
STATUS: **partial (INTERIM, work in progress)**. No files delivered yet; every item is "in progress" or "pending", with
pointers to earlier deliveries. Untrusted data; nothing staged beyond the RESULT.md copy; nothing committed.

Note: item 8 repeats "drawing DRG-02007" for the Harwin spacer; the delivered sheet is R30-670XX94 (see ../instinct_REQ-006).
Item 9 calls Century Spring "partial"; REQ-002's 02:47Z RESULT.md marks it done (see ../instinct_REQ-002, batch 5).

## Batch 7 (ingested 2026-11-20, folder state at 05:33Z): Schurter DD11 / 4301.1401 / SPT 5x20, Phoenix 1119897

Nine new files plus a revised RESULT.md in REQ-008. A full recursive listing of `mechloop handoff/results` (3 pages, 169 items
incl. 8 folders, nextPageToken followed to the end) found nothing else new in any other folder. Downloaded one at a time into
scratchpad `instinct_batch7/REQ-008/`; all sizes match Drive. Everything handled as untrusted data. Staged for review only:
nothing copied to `vendor_cad/inbox/`, nothing committed.

RESULT.md (1sj3kBNRTE9p_aGhdKOtaj0Fow2kYnAf-, 05:33:38Z, 3,383 B, sha256
150fc3d22c9839a04dbd959a73aee3292eb658aa52f30480607620c8c0d06838) overwrites the 03:29Z copy (a307c60b...). STATUS: **partial
(interim; items 1, 3, 4, 12 resolved)**. Instinct says (not verified) all Schurter files are schurter.com downloads and the
Phoenix files come from phoenixcontact.com.

PDF checks (header / %%EOF, raw and inflated-stream scan, pypdf object-graph walk): all four PDFs real PDFs, not encrypted,
**no JavaScript, actions, launch, embedded files, forms**. They do carry ordinary web-link annotations, all to the maker's own
domain (schurter.com / phoenixcontact.com). STEP files: plain ISO-10303-21 text, complete (END-ISO-10303-21), no URLs.

| Delivered as (Drive id) | Staged as | sha256 | Content |
|---|---|---|---|
| DD11.0114.1111__cad.step (1BqZSA4BMbvxczYMxDruGG7CZOZOK7Gmh, 2,998,289 B) | **not staged**: byte-identical to `vendor_cad/inbox/INLET-C14-SW-FUSE-T8A.step` | 4f86626e145c33b3359ad398d4d31fb69e74cff102b190e2b352c6d445bd7c84 | Schurter family model, product `0100.2571`, AP214, 1 solid |
| DD11.0114.1111__datasheet.pdf (1gLRypTZVjF-iHDKl0lZx6TkDxfBembon) | **not copied**: same sha256 as `vendor_docs/INLET-C14-SW-FUSE-T8A_datasheet.pdf` | 1db97cff0daf3ff16140aba71b86a4556479dc26ed8a657b23d7a6a0d3ea0fe7 | typ_DD11, 6 p, 01.09.2025 |
| 4301.1401__cad.step (1s6Hn6w97aEDFbsVukw7Q51XDG-9dpFDP, 5,763,499 B) | instinct_REQ-008/Schurter_4301.1401_fusedrawer-2-pole-fingergrip.step | db2bb325d3ce43343c1ba08325f0fed5ad61333e9974e772934142e5901c4f61 | product `FD2-fingergrip-withoutVS_03`, AP214, 1 solid |
| 4301.1401__datasheet.pdf (1zPe-l482dlQwx5qZHihM0Yl5dYompB66) | vendor_docs/Schurter_Fusedrawer-2_4301.1401_datasheet.pdf | b43d13b3e6ee7a18d1094d2499a2856a71a9d2e54dd32de238e92572178bf34c | Fusedrawer 2 accessories, 6 p, 02.09.2025: 4301.1401 = Fingergrip, 2-pole, no voltage selector, PU 50; fits DD11 (note 3: only 1-/2-pole, without voltage selector). **No dimension drawing** |
| 0001.2511__cad.step (1ciJ8JVJ_PxJ0Sk9PxPHXpOncW7DfJhEH, 41,166 B) | instinct_REQ-008/Schurter_0001.2511_SPT-5x20-T5A.step | dd62df37bd55821e408f0b25ec2f6916688604c326fec245d93b7b0160f32413 | Pro/E 2001 AP203 export, product `124`, surface model |
| 0001.2513__cad.step (1jtqd2ApEFRZKuM228T0bTubN2FNO0ste, 41,166 B) | instinct_REQ-008/Schurter_0001.2513_SPT-5x20-T8A.step | 004c07b8facbe60a5df0e75f1457ec964d8755c1d4498c4cfe4066376ac745e3 | same geometry as 0001.2511; only the product name (`128`) and a timestamp differ |
| SPT-5x20__datasheet.pdf (1ekr-UXrA34L5HhRhbUOjLd95xQomoLKe) | vendor_docs/Schurter_SPT-5x20_fuse_datasheet.pdf | 95063c4cf2ec2a40985b5661dbf54893b8e69b491be5417c7448b06219cebc52 | 4 p, 21.07.2026: SPT 5x20 time-lag T, ceramic, 250 VAC; 0001.2511 = **5 A** (1500 A H), 0001.2513 = **8 A** (1000 A @ 250 VAC) |
| 1119897__cad.stp (1HK-rglviy89WDNPHkJyUKsUwZ9kxeiV2, 674,112 B) | instinct_REQ-008/Phoenix_1119897_PLC-RSC-5DC-21.stp | 4364ae6c9067650f5771040aa6ec1fc2b3275bdb5d84ea09c09c6c200da82966 | Creo Elements/Direct export, AP214; products PLC-BSC-6 base + REL-MR relay (28x15x5), 2 solids |
| 1119897__datasheet.pdf (1ls7lm2T5f_kVfSdo4zW4VkAciZGDl5KX) | vendor_docs/Phoenix_1119897_PLC-RSC-5DC-21_datasheet.pdf | 8142415678837fe4b049323527dbd77d18dba5fb31814a3b2a9aecf35476042e | 12 p online-catalogue PDF generated 2026-11-20 05:32Z: PLC-RSC- 5DC/21, 1 CO, 5 V DC coil (38 mA), screw terminals, NS 35/7.5 |

### Geometry checks (build123d, `.venv/bin/python -I` under `ulimit -v`, one file at a time, peak RSS 400-470 MB; scripts scratchpad/scripts/stepcheck_b7.py, section_b7.py)

| Check | Datasheet | STEP | Result |
|---|---|---|---|
| DD11 flange (version A) | 65 x 30.5 x 2.5 | 65.00 x 30.50, Z -2.5..0 (front Ø6.3 counterbores) | match |
| DD11 front body | 46.7 x 27.7 | 46.70 x 27.70 | match |
| DD11 body behind panel | 46.6 x 27.1 | 46.60 x 27.10 (tapers to 46.45 x 26.95 at 20 mm) | match |
| DD11 panel cut-out | 47.1 ±0.10 x 28.1 ±0.10, R1 | body leaves 0.25 / 0.5 mm per side | consistent |
| DD11 screw holes | 56 ±0.15, Ø3.25 in part | Ø3.25 at Y -14.95 / 41.05, 56.00 apart, centred on the body | match |
| DD11 depth behind panel | 30 body, 33.1 overall | 33.1 | match (code `iec_inlet_c14()` models 30; the 3.1 mm terminal tail is already allowed by its `protrusions` note) |
| DD11 front projection | 5 | 5.6 to the top of the rocker | +0.6, rocker only |
| DD11 solid | - | 1 solid, valid, 20,870 mm³ | ok. Same file as the inbox model, so earlier checks still apply |
| 4301.1401 drawer | **no dimensions in the datasheet** | 24.65 x 22.85 x 12.25, 1 valid solid, 3,007 mm³ | not verifiable against the sheet. Plausible for two side-by-side 5x20 fuses (20 mm fuse + contacts). The STEP is a generic "fingergrip without voltage selector" model; its name does not say 1- or 2-pole |
| SPT 5x20 cartridge | Ø5.2 (+0.1/-0.2) x 20 ±0.5, caps 5.1 ±0.6 | caps Ø5.2 x 5.0 at each end, 20.0 between cap faces; tube Ø4.0 | cartridge **matches** |
| SPT STEP extras | - | Ø5.8 x 5.1 sleeves over each cap (overall 21.2) and **Ø0.65 x 40 mm wire leads at both ends (overall 101.2 mm)** | **mismatch: the model is the axial-lead "SPT 5x20 Pigtail" form**, not the plain cartridge that goes in a fuse drawer |
| SPT STEP topology | - | 36 bounded surfaces in a GEOMETRICALLY_BOUNDED_SURFACE model, **no solid, no shells** | surface-only, as RESULT.md says. Cannot give a volume or run interference checks without rebuilding |
| Phoenix width | 6.2 | 6.10 | -0.1 (6.2 is the module pitch; the model housing is 6.1) |
| Phoenix height | 80 | 80.00 | match |
| Phoenix depth | 94 | **92.6** | **-1.4 mm**; not explained by the files |
| Phoenix solids | - | relay 5.0 x 28.0 x 18.5 (valid, 2,039 mm³); base 6.1 x 80 x 92.6 (28,031 mm³) **is_valid = False** | the base solid fails the OCC validity check; bbox and volume are still usable |

### Flags for the owner (not resolved here)

- **DD11 variant vs the drawer and fuse count.** DD11.0114.1111 is listed on DD11 p.5 as a **1-pole fuseholder** (illuminated
  green, with cover, V-Lock, version A). `mechloop/data/sourcing/mpn_map.json` pairs it with 4301.1401, which the drawer sheet
  lists as a **2-pole** drawer, and `v12_electronics.json` budgets 0001.2513 "2 fitted (L and N) + 2 spares". The 2-pole module
  with the same options is **DD11.0124.1111**. Either the module or the drawer/fuse count needs to change. (The existing
  `iec_inlet_c14()` docstring already suggests the 1-pole drawers 4301.1405 / .1407.)
- The DD11 STEP is a Schurter family model (`0100.2571`), not specific to 0114.1111. It is the same file already in the inbox,
  so this delivery confirms the inbox model's source but adds no new geometry.
- SPT STEP is the pigtail form with leads. For a drawer-mounted cartridge, trim the leads and sleeves or model a Ø5.2 x 20
  cylinder from the datasheet.
- Phoenix 1119897: limiting continuous current **6 A**, max 250 V AC/DC (datasheet). Check this against whatever load it
  switches.
- Fuse ratings agree with the repo: 0001.2511 = T5A (`FUSE-5x20-T5A`), 0001.2513 = T8A (`FUSE-5x20-T8A`).

### REQ-008 status per the 05:33Z RESULT.md

- Done: **1** (Schurter DD11 + 4301.1401 + 0001.2511 / .2513, files above); **3** (Phoenix 1119897, files above); **12** (HIWIN
  MGNR12R-300 + MGN12H, delivered via REQ-005, see ../instinct_REQ-005/MANIFEST.md batch 6).
- Blocked: **4** (StepperOnline 17E19S1684AB4-330RA full datasheet: Cloudflare challenge on stepperonline.com /
  files.omc-stepperonline.com, no alternate official source); **11** (PEM S-M3-0ZI: PEM account approval pending; CADENAS routes
  exhausted); **14** CAD part (Misumi registration rejected).
- In progress / pending: 2 (Finder 22.32 STEP re-verify), 5, 6, 7, 8 (spacer research; STEP blocked on TraceParts), 9, 10,
  13, 14 (part numbers), 15, 16, 17, 18, 19 (partial, no official drawing exists), 20.
- RESULT.md still says "drawing DRG-02007" for item 8 (see the note above).

## Batch 8 (ingested 2026-11-20, Drive state at about 06:45Z): REQ-008b, Schurter DD11.0124.1111

Two new files plus a revised RESULT.md in REQ-008. Recursive search of `mechloop handoff/results` for anything created or
modified after 05:30Z, plus a full listing of the two new folders, found only these, the new REQ-009 folder (see
../instinct_REQ-009/MANIFEST.md) and an empty REQ-010 folder (see ../instinct_REQ-010/MANIFEST.md). Downloaded one at a time into
scratchpad `instinct_batch8/REQ-008/`; sizes match Drive. Untrusted data. Nothing copied to `vendor_cad/inbox/`, nothing committed.

RESULT.md (1sj3kBNRTE9p_aGhdKOtaj0Fow2kYnAf-, 06:30:10Z, 5,502 B, sha256
8ed3ec952048fd29ceec45820ceb5e080124e2e8a4990b4cd3be2343ec534347) overwrites the 05:33Z copy (150fc3d2...). STATUS is unchanged
(**partial, interim; items 1, 3, 4, 12 resolved**). It adds a "REQ-008b-updates" section.

| Delivered as (Drive id) | Staged as | sha256 | Content |
|---|---|---|---|
| DD11.0124.1111__cad.step (15ovyvGT0a3xsqiBbY87jgLduX0a_KO5u, 2,998,289 B) | **not staged**: byte-identical to `vendor_cad/inbox/INLET-C14-SW-FUSE-T8A.step` and to the batch-7 DD11.0114.1111__cad.step | 4f86626e145c33b3359ad398d4d31fb69e74cff102b190e2b352c6d445bd7c84 | Schurter family model `0100.2571.STEP` (SolidWorks 2006, AP214), 1 MANIFOLD_SOLID_BREP, complete, no URLs |
| DD11.0124.1111__datasheet.pdf (1iyr9HDluKtGykXGcrvnuw8DUalr6WkLV, 450,651 B) | **not copied**: same sha256 as `vendor_docs/INLET-C14-SW-FUSE-T8A_datasheet.pdf` (already scanned: real PDF, no JavaScript) | 1db97cff0daf3ff16140aba71b86a4556479dc26ed8a657b23d7a6a0d3ea0fe7 | typ_DD11 series sheet, 6 p, 01.09.2025 |

### Checks

- **2-pole confirmed from the datasheet.** Variants table (p.5): `2-pole | none | illuminated | green | cover | V-Lock | A |
  DD11.0124.1111`. The first column is the fuseholder pole count; the line switch is 2-pole on every DD11 (header "Line Switch
  2-pole, Fuseholder 1- or 2-pole"). DD11.0114.1111 is the same line with a 1-pole fuseholder.
- **Flange / cut-out same as DD11.0114.1111**: both are mounting version A on the one series sheet, so flange 65 x 30.5 x 2.5,
  cut-out 47.1 x 28.1 R1, screws 56 apart apply to both. The STEP is the identical file checked in batch 7 (all dimensions matched;
  see the table above), so build123d was not re-run.
- **Flag: the STEP is not specific to 0124.1111.** RESULT.md says it was "fetched via Schurter's own CAD download flow for the exact
  order number", but its bytes are the generic family model already in the inbox. Externally a 2-pole fuse drawer differs from a 1-pole
  drawer + spare-fuse case only inside the drawer, so the outline is still usable.
- Instinct reports (not verified): Digi-Key 486-1286-ND, $28.36 qty 1 ($24.10 @10, $22.59 @25, $21.51 @50, $20.49 @100), **not
  stocked, 16-week standard lead time**. DD11.0123.1111 (red lamp, 486-1284-ND, $28.04, 108 in stock) noted as a different part.
- Item 4 (plain-cartridge 5x20 STEP) and item 5 (newer Phoenix 1119897 CAD): no action, no new files. Instinct says Schurter offers
  only pigtail STEPs for 0001.2511 / .2513, and Phoenix only the one model (92.6 mm deep vs 94 mm sheet).

### Owner flags

- Switching to DD11.0124.1111 resolves the batch-7 pole mismatch with the 2-pole drawer 4301.1401 and the 2 fitted 0001.2513
  fuses, but `mechloop/data/sourcing/mpn_map.json` and `v12_electronics.json` still list DD11.0114.1111. Not changed here.
- 16-week lead time and no stock at Digi-Key (as reported) for DD11.0124.1111.

## Batch 10 (ingested 2026-11-20 14:20Z, Drive state as of the 07:52Z files): item 14 Misumi GT2 pulley, item 16 TMC2209, RESULT.md revision

Three new files plus a revised RESULT.md in REQ-008 (`1W3K9YtzrWAnS2H6KbsBgHhr6L_M__EcD`). Each downloaded into its own empty
scratchpad directory (`ingest_req008c/<name>/`); sizes match Drive metadata. Untrusted data: provenance below is as Instinct stated
it, not verified. Nothing copied to `vendor_cad/inbox/`, nothing committed.

| Delivered as (Drive id, modifiedTime) | Staged as | Size | sha256 |
|---|---|---|---|
| GPA20GT2090-A-H5__cad.step (1Bv5ga8Kff1OdYiA7WFj4PDWUNfX7fK-f, 07:19:08Z) | `instinct_REQ-008/Misumi_GPA20GT2090-A-H5_2GT-20T-9mm_H5.step` | 242,830 | e779e3619e2b1a370b33722df696d17c5792efa104dbd1476681715cdf7fee10 |
| GPA20GT2090-A-H5__drawing.pdf (1uljkb1-LPG0Vcl1MSgSxiyBE2d9WvqQx, 07:19:08Z) | `vendor_docs/Misumi_GPA_GT2090_2GT_high-torque_pulley_2019US_p1340.pdf` | 491,898 | 3dee5a1eccdf5e3ceeb152b6fcbb01edadfd4a3fea7716f2ff2de43f48a00e76 |
| TMC2209__datasheet.pdf (1lom8oZFer03VEb6A_j-FykioO2TrJcNh, 07:22:22Z) | `vendor_docs/ADI_TMC2209_datasheet_rev1.08_digikey-copy_OLDER.pdf` | 1,629,829 | 24d6fe363ff4e5898c0c3fa2ed06e9d8a04e34481a5ad5cc9e4555e7403fdd44 |
| RESULT.md (1sj3kBNRTE9p_aGhdKOtaj0Fow2kYnAf-, 07:22:27Z) | `instinct_REQ-008/RESULT_instinct_REQ-008_2026-11-20.md` (overwrites the 06:30Z copy, 8ed3ec95...) | 7,516 | 95a01a7e02280f8912563ccbab92d2d982cd72946b9653fa76221d30b0e0729b |

### Provenance as Instinct stated it

- STEP: "official Misumi-generated STEP AP214 for the exact configured part number, from Misumi's login-gated CAD download flow".
  Header: FILE_NAME 'GPA20GT2090-A-H5.step', 2026-11-04T15:22:07, SwSTEP 2.0 / SolidWorks 2016, AP214 (AUTOMOTIVE_DESIGN). PRODUCTs:
  `GPA20GT2090-A-H5` (assembly), `TIMING PULLEY_GPA20GT2090-A-H5`, `FLANGE_GPA20GT2090-A-H5`. No URLs in the file.
- Drawing PDF: Misumi 2019 US catalogue p.1340 (spread p.1340-1341), the GPA 2GT series drawing, provided because the per-part
  configured-spec PDF flow "did not complete in-session". 1 page, InDesign 14 / Adobe PDF Library 15, created 2021-04-06; no
  JavaScript, no /Launch, no /URI, no embedded files.
- Price/lead time (not verified): us.misumi-ec.com 2026-11-19, $21.65 each, ship date Mon Nov 30 2026.

### STEP check (build123d via `.venv/bin/python -I`)

3 solids (1 pulley body + 2 flanges), all valid. Pulley axis = X. Bounding box 13.30 x 17.00 x 17.00 mm (X 0..13.3).
Volume 1,280.35 mm^3 total (body 960.57, each flange 159.89); about 3.5 g in aluminium.

Catalogue values (p.1340, 2GT, 20 teeth, GT2090, Shape A). Note: on this page Shape A has no extended hub; overall length is W.
L = 21.0 applies to Shape B, which is not offered below 21 teeth for 2GT.

| Dimension | Catalogue | STEP | Result |
|---|---|---|---|
| Teeth | 20 | 20 tooth tips (20 cylinders r6.11) + 20 groove arcs (r0.675) | match |
| Pitch dia P.D. | 12.73 | not a modelled surface; O.D. + 2 x 0.254 pitch-line offset = 12.73 | consistent |
| Outside dia O.D. | 12.22 | 12.22 (tip cylinders r6.11) | match |
| Flange dia F | 17 | 17.00 | match |
| Flange thickness t | 1.0 | 1.00 (x 0.65..1.65 and 11.65..12.65) | match |
| E (flange seat / shoulder dia) | 9 | 9.00 (r4.5 shoulder on body and flange bore) | match |
| Tooth face width A | 10.0 | 10.00 (x 1.65..11.65) | match |
| Overall width W (Shape A length) | 13.3 | 13.30 | match |
| 1.65 shoulder each side | 1.65 | 1.65 | match |
| Bore d | 5 H7, H round hole | 5.00 plain cylinder (r2.5); tolerance not modelled | match (nominal) |
| Set screw / tapped hole | none for H ("H (Round Hole) do not have tapped holes"; "No tapped holes and set screws") | no non-axial cylinders: no radial hole | match |
| Belt width | 9 mm (GT2090) | A = 10 face width, suits 9 mm belt | match |
| D | "—" for 20T | n/a | n/a |

### Checks and owner flags

- **No set screw: confirmed.** H = plain round bore, from both the catalogue text and the STEP. **This pulley cannot be
  clamped to a 5 mm motor shaft as delivered.** From the catalogue's bore-selection table (layout read with pdftotext, so treat as
  likely rather than certain), GPA 2GT GT2090 at 15-21 teeth is offered in **H only** (20T: d = 4, 4.5, 5, 6); the P (round hole
  + tap, M3 x 3 set screw for d5) and N options start at 24 teeth (24T: P 5-8). So a set-screw GPA in 20T is not on this page;
  options are a 24T P5 (GPA24GT2090-A-P5, not checked) or another fixing / supplier. Owner decision; not changed here.
- **Idler: not available** at Misumi in 20T / 9 mm / 5 mm bore (per Instinct): AGTFW/BGTFW (bearings both sides) 2GT only in 30T,
  closest **AGTFW30-GT2090-5** (30T, 9 mm, 5 mm bore); AGTF/BGTF (centre bearing) has 20T but only 8 and 20 mm bores. No
  substitute picked; Instinct asks for owner approval.
- **TMC2209 datasheet: kept, but it is the OLDER revision.** Instinct's copy is Rev. 1.08 / 2022-MAY-25 (86 p, PDFium output dated
  2022-11-21, sha256 24d6fe36...). The owner-supplied `vendor_docs/ADI_TMC2209_datasheet_rev1.09.pdf` is Rev. 1.09 / 2023-FEB-16
  (86 p, Word output dated 2023-03-01, sha256 1d9e8eed...) and is **newer**; use 1.09. The rev 1.08 copy is kept only because it
  differs (named `_OLDER`); it can be deleted. RESULT.md's claim that 1.08 is "the same revision as the current analog.com-hosted
  file" is contradicted by the owner's 1.09 copy. No JavaScript; 3 /URI link annotations.

### RESULT.md 07:22Z revision

STATUS changes from "items 1, 3, 4, 12 resolved" to **partial, interim: items 1, 2, 3, 12, 16 delivered; item 14 pulley
delivered, idler not available; item 4 blocked**. Item 2 (Finder 22.32) is now marked done by reference to REQ-006; item 16 now
says DONE (rev 1.08, see above); item 14 as above. Items 5-11, 13, 15, 17-20 are unchanged (pending / earlier partials). The
REQ-008b section is unchanged from 06:30Z.
