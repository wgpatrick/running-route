# instinct_REQ-005: rails addendum (Helix / CPC MR12, HIWIN MGN12H 245 mm, NSK, igus, Misumi), first (interim) delivery

Ingested 2026-11-20 (batch 5) from Google Drive `mechloop handoff/results/REQ-005-rails-addendum-helix-hiwin/`
(folder 1_-rIetDBexZ6IT3MwJJwYEeNrE4yaU8_), 6 files as of 03:29Z. Collected by Instinct (the owner's browser agent).
Instinct's STATUS: **partial**. `RESULT_instinct_REQ-005_2026-11-20.md` is the 03:29:20Z RESULT.md (Drive id
1xgxLAJCwLrfp6DcnJug0FK5bGGN4xpgD, sha256 b4b0cfd0efdf6c4714ec072475ee81d76acafe2899f7b2490c2221e8e03117db), which has the price
table. It replaced the 03:01:58Z interim RESULT.md (1K8lJfvr6bYH6tYjfS1_xbbXJCoYIsuV3, sha256 3425a6fe..., no longer in the
folder). Everything was handled as untrusted data.

Staged for review only. Nothing has been copied to `vendor_cad/inbox/`. Nothing committed.

**No STEP or other CAD was delivered** (Helix CAD library loads client-side; HIWIN configurator download not reached; Misumi
CAD needs an unapproved account; NSK / igus CAD pending).

Method (PDFs): header / %%EOF, raw and inflated-stream scan, pypdf object-graph walk for /JavaScript, /JS, /Launch,
/EmbeddedFile, /RichMedia, /XFA, /SubmitForm, /OpenAction, /AA. All three PDFs: **no JavaScript, actions, embedded files
or link annotations**; not encrypted. None duplicates a file already in vendor_docs (sha256).

## Documents copied to vendor_docs/ (unchanged)

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 1 | CPC_MR12_spec_AnaheimAutomation.pdf | CPC-MR12__spec.pdf | 52e088be76a263bdf7fb3faca244058b65e06ae258dc24ab2ee8494e78fb4699 | 2 p, Anaheim Automation (US CPC distributor) MR12 dimension / load table for SS and SU seals, MN / ML / WN / WL blocks, rails 100 to 1000 mm |
| 1 | CPC_MR_miniature_guides_catalog_27p.pdf | CPC-MR__catalog.pdf | a29238cee89b08ffdcdee3a1e6cff1494c5710e915aceafdc1da3227749116ea | 27 p CPC MR catalogue (two-page spreads). **Not the same file** as REQ-004's `CPC_miniature_guides_catalog.pdf` (32 p, 028923c0...). Tables are images (accuracy p.5, preload p.6, rail lengths p.10) |
| 1 | Helix_HMR_miniature_linear_guides_catalog.pdf | Helix-Miniature-Linear-Guides__catalog.pdf | 3681dac553ae831d9285449922f5c51c538cbf67779e9a31ffa1d64be9d10173 | 40 p Helix Linear (CPC-made, HMR = CPC MR). Accuracy / preload PDF p.7, rail lengths p.15, HMR-M SS table PDF p.20-21 (printed p.18-19) |

## Size-12 facts extracted (catalogue values, checked against HIWIN `vendor_docs/Hiwin_MG_catalogue.pdf` GW-11-5-EN-2207-K)

| | CPC MR12ML SS (Anaheim spec) | Helix HMR 12ML SS | HIWIN MGN12H + MGNR12R |
|---|---|---|---|
| Overall height H (rail base to block top) | 13 | 13 | 13 |
| Rail W1 x H1 | 12 x **7.5** | 12 x **7.5** | 12 x **8.0** |
| Rail hole pitch / counterbore D x d x h | 25 / 6 x 3.5 x 4.5 (M3) | 25 / 6 x 3.5 x 4.5 | 25 / 6 x 3.5 x 4.5 |
| Rail end distance L2/L3 (E) min-max | 4 - 20 | 4 - 20 | 5 - 20 |
| Block width W / rail edge to block edge | 27 / 7.5 | 27 / 7.5 | 27 / N 7.5 |
| Block length L / body L1 | **47.8** (SU: 48) / 34 | **47.6** (SU 47.6; EE/SUE 49) / 34 | **45.4** / 32.4 |
| Block mounting holes | 20 x 20, M3 x 3.5 | 20 x 20, M3 x 3.5 | 20 x 20 (B x C), M3 x 3.5 |
| C (dynamic) | 3.24 kN at 100 km (= 4.08 kN at 50 km) | 3,240 N C100 | 3,720 N at 50 km |
| C0 (static) | 5.63 kN | 5,630 N | 5,880 N |
| Static moments roll / pitch / yaw | 34.9 / 30.2 / 30.2 Nm | 30.2 / 30.2 / 34.9 as printed (column order differs from CPC) | M0X 38.2 / M0Y 36.3 / M0Z 36.3 |
| Block / rail weight | 0.11 lb (50 g) / 0.40 lb per 300 mm | 51 g / 602 g/m | 50 g / 650 g/m |
| Accuracy classes | P / H / N: H ±10/±20/±40 µm, ΔH 7/15/25, W2 ±15/±25/±40, ΔW2 10/20/30 | same table; N stocked | C / H / P (LDO drawing: C ±40 µm) |
| Preload (size 12) | V0 clearance +5~0 µm, VS standard +2~0, V1 light 0~-5 | same; V0 stocked | ZF 4-10 µm backlash, Z0 0-3 µm, Z1 0.02 C |
| Stiffness | **not published** (qualitative only) | **not published** | MGN12H radial 63 / 81 N/µm (Z0 / Z1, GW-11-5-EN); 105 / 182 N/µm in the REQ-007 MG excerpt |
| Standard rail lengths | 70, 95, 120, 145, 170, 195, 220, **245**, 270, 320, 370, 470, 570; Lmax 1000 (butt-joint beyond) | same list, printed as 96 / 196 for 95 / 195 (likely typo); Lmax 1000 | same list plus 695; max standard 1995, max 2000 |
| Speed / acceleration | SS/SU: 3 m/s, 250 m/s² (40 m/s² at V0); EE: 5 m/s, 300 m/s² (60 at V0) | same | - |
| Operating temperature | -40 to +80 °C (short term 100 °C) | - | - |

Drop-in assessment: **mechanically interchangeable with MGN12H for the carriage mounting** (same 13 mm height to the block
top, same 27 mm width and 7.5 mm reference offset, same 20 x 20 M3 x 3.5 block holes, same rail width, 25 mm pitch and
M3 counterbore). Differences: the rail is **0.5 mm lower** (7.5 vs 8) so anything that references the rail top (end
stops, wipers, clamps) moves; the long block is **2.2 to 2.4 mm longer** (47.6 / 47.8 vs 45.4), which costs that much
stroke; rails above 1000 mm need a butt joint; the ordered codes are V0 (clearance) and N (normal) grade, not a preload.
Load ratings are about the same once the 100 km vs 50 km rating basis is converted.

Corrections to RESULT.md (not verified beyond the catalogues):
- "SS series ... Qmax 250 m/s² (60 m/s² at V0)" should read 40 m/s² at V0; 60 m/s² is the EE type (both catalogues).
- RESULT.md calls the Helix p.18 table the source; in the PDF it is p.20-21 (printed p.18-19).
- REQ-004 RESULT.md says "V0N = standard preload". Per both catalogues V0 = clearance and N = normal accuracy.

## Prices / MOQ / stock in RESULT.md 03:29Z (as delivered, captured 2026-11-19, US sites, USD; nothing verified here)

| Part | Price | MOQ | Stock / lead | Source |
|---|---|---|---|---|
| Helix HMR12MLSS1V0N-245L (rail + 1 long block) | **$100.85** | **10** (Digi-Key marketplace) | 10 available, 21-day supplier lead | Digi-Key HMR12MLSS1V0N-245L-15-15 |
| Helix HMR12MLSS1V0N-270L | $106.71 | 10 | same | Digi-Key |
| Helix HMR12MLSS1V0N-300L | not listed at Digi-Key | - | - | - |
| Helix HMR12MLSS1V0N-320L | $118.44 | 10 | same | Digi-Key |
| CPC MR12MLSSV0N-300-12.5-12.5 (**long block** set) | **$109.00** (1 pc); $104.99 / $102.07 / $100.67 at higher qty | 1 | **not in stock, typ. 60 days** | Anaheim Automation |
| HIWIN MGN12H ZF block (MGN12HZFH) | $59.00 | 1 | cart-enabled | MotionUSA |
| HIWIN MGN12H Z1 / Z0 block | $59.00 each | 1 | 96 / 70 in stock | Digi-Key |
| HIWIN MGNR12R rail 245 mm (MGNR12R0245HM/E10/E10) | $126.00 | 1 | cart-enabled | MotionUSA |
| HIWIN MGNR12R rail 300 mm | $125.00 | 1 | in stock | Digi-Key (no 245 listed) |
| HIWIN ZF block + 245 mm rail | **about $185** (Instinct's sum of the two lines, not a quoted bundle) | 1 | - | calculated |
| Misumi SSEB13-245 set (standard block) | $117.27 (1-3), $111.39, $105.54, $99.66 (11+) | 1 | ships Nov 23 | Misumi US |
| Misumi SSEBL13-250 / -300 (long block) | $158.95 / $168.11; -245 shows no price | 1 | ships Nov 30 | Misumi US |
| igus TS-04-12 / TW-04-12 / TWE-04-12 | $119.84 (length basis unconfirmed) / $27.92 / $46.29 | 1 | - | igus.com |
| NSK PU12UR / P1U12 | not found | - | - | - |
| LDO MGN12H | **US availability not established** (REQ-008 item 13 pending). Only UK: onetwo3D £31.14 / £33.37 / £34.48 ex VAT (300/350/400), in stock (REQ-004) | - | - | - |

RESULT.md flags (not verified): Instinct could not confirm that Helix HMR12 is CPC-made (Helix's page says
"American-manufactured"), so it treats the Anaheim CPC part as an alternate with the same code pattern and dimensions,
not a proven-identical part. The catalogues do match line for line (same tables, same C / C0 / moments, same rail-length
list). RESULT.md still repeats the "60 m/s² at V0" error for SS.

HIWIN STEP: the configurator disclaimer was accepted with the owner's OK (per RESULT.md, not verified), but the download
needs a configure.hiwin.com account; the old support login was rejected. Misumi CAD: registration rejected twice.

### Batch 5 late arrivals in this folder (03:16Z)

- PU12UR__datasheet.pdf (1ywgI4JQIELlVafLIpT4GQ1PUeQOD2-AV): not copied, same sha256 (2d06a276...) as
  `vendor_docs/NSK_PU-PE_miniature_E3327e.pdf`.
- **MGN12H__catalog.pdf (1lhgrPyR9xKfs5m25gbQmfH8GaCU7BdL7, 17,883,962 bytes): NOT downloaded** (over the connector's 10 MB
  limit). Same size as the two HIWIN catalogue uploads that REQ-007 says are byte-identical (sha256 b9445d5a...); the
  MG-series chapter now exists as an excerpt (see ../instinct_REQ-007/MANIFEST.md).

HIWIN MG excerpt (REQ-007) adds: MGNR12 standard lengths 70, 95, 120, 145, 170, 195, 220, 245, 270, 320, 370, 470, 570, 695
(E 10, max standard 1995, max 2000), accuracy C ±40 / H ±20 / P ±10 µm on H, and radial stiffness MGN12H 105 N/µm (Z0) /
182 N/µm (Z1). The older GW-11-5-EN catalogue in vendor_docs gives 63 / 81 N/µm for the same block, so the two HIWIN
editions disagree on stiffness.

Outstanding: every STEP (Helix, HIWIN, NSK, igus, Misumi); Helix 300L and a single-unit Helix source; LDO US sellers;
NSK price; igus configured rail price; Misumi SSEBL13-245 price.

## Batch 6 (ingested 2026-11-20, folder state at 05:06Z): official HIWIN CAD + drawings, RESULT.md revision

Seven new files plus a revised RESULT.md in REQ-005 (folder 1_-rIetDBexZ6IT3MwJJwYEeNrE4yaU8_). A full recursive listing of
`mechloop handoff/results` (2 pages, 154 files, nextPageToken followed to the end) found nothing else new in any other folder.
Downloaded one at a time into scratchpad `instinct_batch6/REQ-005/`; all sizes match Drive. Everything handled as untrusted
data. Staged for review only: nothing copied to `vendor_cad/inbox/`, nothing committed.

Instinct says (not verified here) the files were generated 2026-11-19 from a configure.hiwin.com account it created "with
Will's approval", after accepting the configurator disclaimer with his OK. The STEP headers say SolidWorks 2024 / SwSTEP 2.0,
AP214, generated 2026-11-20T04:26 to 04:51; the drawings carry HIWIN Corporation (Huntley, IL) title blocks, drawn and checked
11-19-2026, dwg nos. 570302 / 570307 / 570310 / 570313.

PDF checks (same method as above: header / %%EOF, raw and inflated-stream scan, pypdf object-graph walk): all four drawings
1 page, not encrypted, **no JavaScript, actions, embedded files or link annotations**. None duplicates a vendor_docs file.
STEP files: plain ISO-10303-21 text, complete (END-ISO-10303-21), no URLs or other non-geometry content.

| Delivered as (Drive id) | Staged as | sha256 | Content |
|---|---|---|---|
| RESULT.md (1xgxLAJCwLrfp6DcnJug0FK5bGGN4xpgD, 05:06:20Z, 11,704 B) | instinct_REQ-005/RESULT_instinct_REQ-005_2026-11-20.md (overwritten; previous 03:29Z copy was b4b0cfd0...) | c728ca127e6d8240de3512ebc0338da6ada6650875df6f75fa47ff4bdaa8327f | STATUS still partial. Price table unchanged apart from the CAD column; item 2 rewritten (HIWIN CAD) |
| MGNR12R-245__cad.step (1uSJ2xRBPbvRWEaqSBnPxhvXQUqA9nIJH) | instinct_REQ-005/HIWIN_MGNR-12-R0245-H-M.step | 96fe1ffb2a154edacf37ddd75e4a98974f08fc14cc215954da4c3d3d583f1b66 | rail only, MGNR-12-R0245-H-M |
| MGNR12R-300__cad.step (1IlQDTMt2T6CooyAnwxVtnJirlm3-tUz3) | instinct_REQ-005/HIWIN_MGNR-12-R0300-H-M.step | e264f5be08aae26ebef2f594717cbe9784e61ee8bdaaf475761790cf0e575f7f | rail only, MGNR-12-R0300-H-M |
| MGN-12-H-1R0300-ZF-H-M__cad-block-rail-assembly.step (1nPALJXCuGGyfbAMiwPmpoSG_VF2DNj1T) | instinct_REQ-005/HIWIN_MGN-12-H-1R0300-ZF-H-M_block-rail-assembly.step | f89e4a0a5f57037a3a3a7a2713d24baf33578864b9f341a81e1c1a2f4328ca63 | MGN12H ZF block on 300 mm rail, H class |
| MGNR12R-245__drawing.pdf (1eKpVi-n7BxlSHnGlrUJOUz_j3ovWt9Ib) | vendor_docs/HIWIN_MGNR-12-R0245-H-M_drawing.pdf | 1160e8d3afb56789251491ebe773fa1a71de57e9ed2e6e3670bdf1b4d3fdf383 | 10 + 9x25 + 10 = 245, 12 x 8, Ø3.5 thru, Ø6 x 4.5 deep, alloy steel |
| MGNR12R-300__drawing.pdf (1Gt4Mw7JKLecF9IMjblrez-535124LkMh) | vendor_docs/HIWIN_MGNR-12-R0300-H-M_drawing.pdf | 4622dc90c30f4ccec155a65b990101103e2772c9634db5eb5dd2a0f48595d4c4 | 12.5 + 11x25 + 12.5 = 300, otherwise as above |
| MGN-12-H-1R0300-ZF-H-M__drawing-block-rail-assembly.pdf (1VFvpP2mbM2wvAuRhEpnUMPwMywUsgSSy) | vendor_docs/HIWIN_MGN-12-H-1R0300-ZF-H-M_drawing.pdf | 64a155da135ef4b8a9345cbb3cabc3af28136e02d3738879b8b006418964e8c9 | L 45.4, L1 32.4, W 27, B x C 20 x 20, 4-M3x3.5, H 13 ±0.02, H1 3, N 7.5 ±0.025; C 3.72 kN, C0 5.88 kN; running parallelism 0.011; ZF clearance 4-10 µm; material "Stainless Steel" |
| MGN-12-C-1R0300-ZF-H-M__drawing-block-rail-assembly.pdf (1Do9Thq3pNOsfJPuV8yU1ER8Ds6GPHR1w) | vendor_docs/HIWIN_MGN-12-C-1R0300-ZF-H-M_drawing.pdf | 2ea2088110efd3c153e04b74019977e845722edee21e51899ce29d337b5c91b5 | MGN12C: L 34.7, L1 21.7, B x C 20 x 15, 4-M3x3.5, H 13, H1 3; C 2.84 kN, C0 3.92 kN. **No STEP** for MGN12C (per RESULT.md HIWIN's generator dropped the block) |

### Geometry checks (build123d, `.venv/bin/python -I`, scripts in scratchpad/scripts/hiwin_check_b6.py, holes_b6.py, section_cmp_b6.py)

Reference values: HIWIN GW-11-5-EN-2207-K (`vendor_docs/Hiwin_MG_catalogue.pdf`) Table 3.79 (block) and 3.81 (rail), and
the HIWIN drawings above. File frame: rail along -Z, width X, height Y (rail base Y = 0).

| Check | Catalogue / drawing | MGNR-12-R0245 STEP | MGNR-12-R0300 STEP | Assembly STEP |
|---|---|---|---|---|
| Solids / valid | - | 1 / valid (209 faces) | 1 / valid (219 faces) | **10 / all valid** |
| Rail section WR x HR | 12 x 8.0 | 12.000 x 8.000 | 12.000 x 8.000 | 12.000 x 8.000 |
| Rail length | 245 / 300 | 245.000 | 300.000 | 300.000 |
| Holes, pitch P | 25 | 10 holes, 25.000 | 12 holes, 25.000 | 12 holes, 25.000 |
| End distance E1 / E2 | catalogue 5 min, 20 max; drawing 10 / 12.5 | 10.000 / 10.000 | 12.500 / 12.500 | 12.500 / 12.500 |
| Through hole d / counterbore D x h | 3.5 / 6 x 4.5 | 3.500 (Y 0-3.5) / 6.000 x 4.500 (Y 3.5-8) | same | same |
| Rail volume, mass at 7.85 g/cm³ | 0.65 kg/m | 20,824 mm³, 163 g (0.667 kg/m) | 25,540 mm³, 200 g (0.667 kg/m) | rail solid identical to the 300 rail-only file (same volume and face count) |
| Ball track | - | 2 gothic-arch tracks per side, R 1.14, centres at Y 4.65 and 6.26 | same | same |
| Block L / L1 | 45.4 / 32.4 | - | - | 45.400 overall (body 32.4 + 2 end caps 5.5 + 2 end seals 1.0) / body 32.400 |
| Block W, H, H1 | 27, 13, 3.0 | - | - | 27.000; top at Y 13.000; underside at Y 3.000 |
| Block mounting B x C, M x l | 20 x 20, M3 x 3.5 | - | - | 20.000 x 20.000 centred on the body; holes drawn as Ø2.5 tap drill, 4.5 deep (threads not modelled) |
| Block body volume | 0.050 kg | - | - | body 6,662 mm³ (52 g steel); end caps 2 x 1,065 mm³, seals 2 x 175 mm³ |

**Assembly structure: block and rail are separate solids.** Products: `MGN-12-H_...` (block) and `MGNR-12-R_..._MGNR12R`
(rail) under `MGN-12-H-1R0300-ZF-H-M 570302`. The block itself is 9 solids: steel body (27 x 10 x 32.4), two end caps
(26.8 x 9.6 x 5.5), two end seals (26.8 x 9.6 x 1.0) and four small parts 4 x 4 x 4.61 mm at X ±7.25, Y 8-12 (two per end,
likely the end-cap screws or plugs; not identified). The rail is solid 9. The block sits centred on the rail (body centre at
Z -150). No balls are modelled. Instinct's "10 solids" and the rail face counts (209 / 219) are confirmed.

### Differences from the community MGN12 models in the repo

Compared: `vendor_cad/mgn12_rail_100mm.step` (FreeCAD LinearSlide-MGN12-Rail, used by `details.mgn12_rail()`, section swept
to length) and `vendor_cad/mgn12h_block.step` (LinearSlide-MGN12H, used by `details.mgn12h()`; `staging/MGN12H.step` is the
same geometry with a step.parts header). Cross-sections compared with 0.01 mm slabs, both aligned on rail base and centreline.

- Rail envelope identical: 12 x 8, same base chamfers, same holes (Ø3.5 thru, Ø6 x 4.5 cbore, 25 pitch). `mgn12_rail()` places
  holes symmetrically, n = floor((L - 2E)/P) + 1 with E = 10, which gives exactly HIWIN's layouts: 245 -> 10 holes, E 10;
  300 -> 12 holes, E 12.5.
- Rail ball track: HIWIN has two gothic-arch tracks per side (R 1.14 at Y 4.65 / 6.26) with a relief between them; the side
  groove is up to 1.73 mm deep per side (section width 8.53 at Y 5.5). The community rail has one shallow groove (width 10.40
  at Y 5.5, about 0.8 mm deep per side). Section area HIWIN 91.52 mm² vs community 94.22 (+2.70 mm², +3 %); the HIWIN section
  lies entirely inside the community one (HIWIN minus community = 0). Rail mass in the code uses 0.65 kg/m (catalogue).
- Block envelope identical: 27 x 10 (Y 3-13) x 45.4, H1 3, top 13, mounting holes 20 x 20 centred. Section through the body:
  areas 208.5 (HIWIN) vs 211.0 mm² (community), XOR 2.7 + 5.2 mm² (small chamfer / slot-shape differences).
- Community block is one solid with no end caps or seals (so no L1 = 32.4 body, as `details.mgn12h()` already notes); it
  is one 45.4 mm long body, volume 9,481 mm³ vs HIWIN total block 9,219 mm³ (body 6,662 + caps + seals + 4 small parts).
- Mounting threads: community draws Ø3.0 x 3.5 deep; HIWIN draws the Ø2.5 tap drill 4.5 deep (drawing: M3 x 3.5 thread).
- Community block has a Ø1.5 feature at the ends (2 faces); HIWIN has a Ø2.0/Ø2.2 bore in the end caps/seals (lube path).

Not checked: block-to-rail fit of the community pair vs HIWIN pair (the community block's ball rows interpenetrate the
community rail by design, per details.py).

### Notes and flags

- The assembly and MGN12C drawings give material "Stainless Steel"; the rail-only drawings say "Alloy Steel". The part
  numbers carry no stainless code. Not resolved here; treat as a drawing-template detail until HIWIN confirms.
- The 300 mm rail is not a catalogue standard length (standard list ends ...270, 320); HIWIN centred the holes (E 12.5).
  245 is standard (E 10).
- MGN12H block-only STEP: not delivered (Instinct reports HIWIN's generator returns an empty 310-byte STEP for block-only
  configurations). The block geometry is only inside the assembly file. MGN12C: drawing only.
- RESULT.md has **no LDO shipping (REQ-009c) or 80/20 (REQ-009b) content**.
- Prices in the revised RESULT.md are the same figures as the 03:29Z table above (captured 2026-11-19); only the CAD column
  changed (245 / 300 rails: "yes, official STEP + drawing"; ZF block: geometry only inside the assembly STEP).
- RESULT.md open items: MGN12C combo and an MGNR12R-245 combo generation still "in progress"; Misumi CAD still blocked on
  registration; igus configured rail price; Helix STEP; NSK US price.
