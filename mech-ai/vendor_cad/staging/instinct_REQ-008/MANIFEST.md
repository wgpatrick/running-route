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
