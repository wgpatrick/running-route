# Supplier CAD batch 2026-11-19: staging manifest

Copied 2026-11-19 from the owner's Google Drive folder `19Ex99q-xg0cKwm2N8pQ_c8WhI_XcIJSA` and its subfolder `deviations`
(`1hvMqb1U0jBZFgijWDRpgY5xUI5izxEzM`), which is `_DEVIATIONS/` here. The supplier's source and price table is
`SOURCES.txt`, copied unchanged.

**Staging only.** Nothing here is in `vendor_cad/inbox/`, so design builds do not pick any of it up, and no design, checker or
catalogue file was changed. Whoever owns the catalogue decides what gets promoted. Files in `_DEVIATIONS/` are not the
item that was asked for: they are A2 stainless washers, not steel ones.

- Downloaded: 11 of 11 files (10 content files plus `SOURCES.txt`): 9 in the main folder, 2 in `_DEVIATIONS/`. Every byte
  count matches its Drive metadata. Largest file: 1.96 MB.
- Checks treated the files as data only. Each STEP was loaded with OCP `STEPControl_Reader` (`mech-ai/.venv`, `python -I`)
  for solid count, units and bounding box, then measured (section at mid-length, ray casts). PDFs were rendered to images
  and read; nothing was executed.
- `TNUT-2020-M3.pdf` and `TNUT-2020-M5.pdf` are the same file, and both are byte-identical to
  `vendor_docs/misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf`, which the repository already holds (sha256 `0db3cbad...`).

## Files

| File | Folder | Supplier | Part number | Bytes | STEP bbox (mm) | Check |
|---|---|---|---|---|---|---|
| SOURCES.txt | main | - | - | 4,567 | - | text: source / price table, gap list (below) |
| EXT2020-PROFILE.step | main | Misumi (via 3dfindit / CADENAS) | HFS5-2020-500 | 83,639 | 20 x 20 x 500 | parses, AP214 (AUTOMOTIVE_DESIGN), 1 solid, SI milli-metre. Length 500 = part number. Section measured: see below. Section area 182.13 mm2 vs 183 in the datasheet |
| EXT2020-PROFILE.pdf | main | Misumi (3dfindit datasheet) | HFS5-2020-500 | 1,621,219 | - | 7 pages. p.3 section drawing: 20, 12, 6 (both axes), 4-R1, 2, 4, 8, dia 4.2. p.4: A6N01SS-T5 or 6005A-T5, clear anodize, 0.5 kg/m, 183 mm2, Ix = Iy = 0.742e4 mm4. The 2 (lip) and 4 (lip to floor) ARE on this drawing, contrary to SOURCES.txt; the cavity's 45 degree taper and the slot-bottom V are not |
| THUMBNUT-DIN466-M4.step | main | KIPP (via 3dfindit / CADENAS) | K0143.04 | 418,771 | 15.99 x 15.99 x 9.5 | parses, AP214, 1 solid, SI milli-metre. Knurl 16 (crests) x 3.5, collar 8, overall 9.5: matches PDF and catalogue. Details below |
| THUMBNUT-DIN466-M4.pdf | main | KIPP | K0143.04 | 1,961,836 | - | 2 pages: D M4, D1 16, D3 8, H 9.5, K 3.5, steel, 6.2 g; sketch with letters only |
| TNUT-2020-M3.pdf | main | Misumi | HNTP5-3 (page also shows HNTAJ5) | 642,197 | - | Misumi 2019 US catalogue pp.2716-2717. Same file as TNUT-2020-M5.pdf and as vendor_docs/misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf. HNTP5 drawing NOT complete enough for a faithful re-make (below) |
| TNUT-2020-M5.pdf | main | Misumi | HNTP5-5 | 642,197 | - | identical to TNUT-2020-M3.pdf |
| BRKT-2020.pdf | main | Misumi | HBLFSN5 | 692,879 | - | Misumi 2019 US catalogue pp.2692-2693. HBLFSN5 drawing NOT complete enough for a faithful re-make (below) |
| BRKT-2020-ALT.pdf | main | Misumi | HBLTS5 | 622,428 | - | Misumi 2019 US catalogue pp.2696-2697. HBLTS5 drawing NOT complete enough for a faithful re-make (below) |
| WASHER-M3-LARGE.pdf | _DEVIATIONS | Accu | HPLW-M3-A2 | 402,597 | - | ISO 7093-1 M3: OD 9 (+0/-0.36), ID 3.2 (+0.18/-0), T 0.9 (+0/-0.2), A2 stainless 200HV, 35 g/100. MATERIAL DEVIATION (A2, not steel) |
| WASHER-M4-LARGE.pdf | _DEVIATIONS | Accu | HPLW-M4-A2 | 402,319 | - | ISO 7093-1 M4: OD 12 (+0/-0.43), ID 4.3 (+0.18/-0), T 1.1 (+0/-0.2), A2 stainless 200HV, 77 g/100. MATERIAL DEVIATION (A2, not steel) |

## HFS5-2020 section from the STEP (mid-length, Z = -250)

Exact edges of the section (61 edges: lines, 4 R1 corner arcs, the 4.2 bore). One slot, face at Y = +10, slot centred on X = 0;
all four slots are the same.

| Feature | STEP | In use (2019 catalogue p.2686, `tslot_2020_hardware.json`) | Difference |
|---|---|---|---|
| Slot opening | 6.000 (X -3 to +3) | 6 | none |
| Lip thickness | 2.000 (Y 10 to 8) | 2 | none |
| Lip underside to slot floor | 4.000 (Y 8 to 4) | 4 | none |
| Depth, face to floor, off the centre line | 6.000 (floor flat for 0.52 < abs(X) < 2.939) | 6.0 | none |
| Depth, face to floor, on the centre line | 6.300 (V tip at Y 3.7) | 6.3 | none |
| Cavity width under the lips | 12.000 (X -6 to +6), but only for 0.939 mm below the lips | 12 (the JSON and checks treat it as one width) | shape: not rectangular. From 0.939 below the lip underside the walls run in at 45 degrees (3.061 x 3.061) to the floor, whose width is 5.878. Width at depth d below the lip underside: 12 for d <= 0.939, then 12 - 2(d - 0.939); 9.08 at d = 2.4 (bottom of the HNTAJ5 body), 5.88 at d = 4 |
| Slot-bottom V | 120 degrees included (flanks 0.600 long, 0.52 half-width, 0.30 deep) | 120 degrees, 0.3 deep | none |
| Centre bore | dia 4.200 | 4.2 | none |
| Corner radii | 4 x R1.000 | 4-R1 | none |
| Core between the slot floors | 8.000 square (X, Y = +/-4) | 8 (drawing) | none |
| Cross-section area | 182.13 mm2 (slab and whole-body volume / 500 agree) | 183 mm2 | -0.87 mm2 (-0.5 %) |

The 8 mm wide HNTAJ5 body (2.4 high) seated against the lips still clears the tapered walls: 9.08 mm available at its lower
edge, 0.54 mm a side. The screw-tip floor under an M5 (radius 2.5) is the flat 6.0 floor (flat to abs(X) = 2.939).

## KIPP K0143.04 thumb nut from the STEP and PDF

| Feature | STEP | KIPP PDF | Catalogue THUMBNUT-DIN466-M4 (`parts/batch8.py`, `vendor/halder_din466.json`, Halder EH 24780.0240) |
|---|---|---|---|
| Overall height | 9.50 | H 9.5 | 9.5 |
| Knurl diameter | 16.0 at the crests (bbox 15.99; ray at Y=0 meets a root at r 7.5) | D1 16 | 16 |
| Knurl height | 3.5 (Z 6.0 to 9.5), crests chamfered 0.5 at each end | K 3.5 | 3.5 |
| Collar diameter | 8.00 | D3 8 | 8 |
| Collar height to the head underside | 6.0, of which 5.0 straight and an R1 fillet into the head | not given (H - K = 6) | 6.0 (h - k), plain cylinder, no fillet |
| Thread | plain bore dia 3.242 (M4 minor), through all 9.5, 90 degree countersink to about dia 4.0 at both faces (0.38 deep) | D M4, length not given | through (assumed, listed unverified); catalogue solid has no hole |
| Material, mass | 894.3 mm3, about 7.0 g in steel | steel, 6.2 g | stainless 1.4305, 6.7 g |

Every dimension agrees. Differences: material (KIPP K0143.04 is steel; the catalogue entry is stainless), mass (6.2 g KIPP vs
6.7 g Halder), and the STEP's R1 collar fillet and countersinks, which the catalogue solid leaves out. The STEP confirms the
thread runs through the full 9.5 mm.

## Drawings: what is dimensioned

**Misumi HNTP5 (TNUT-2020-M3/M5.pdf, p.2716), the nut the owner's agent selected.** Given: 17 (length), 8.3 (width), 5.8
(neck width), 3.2 and 3.8 (heights), L1 (hole position: 6 for HNTP5/HNTPV5/HNTPZ5, 6.5 for SHNTP5), M3/M4/M5 thread.
Not dimensioned: the angle or size of the tapered flanks, the spring-ball diameter, its protrusion and pocket (dashed circle),
the countersink round the thread, the neck height (only by difference). **Not complete enough for a faithful re-make.** This is
a different nut from the revision's: 17 x 8.3 x 3.8 with a spring ball, against HNTAJ5's 10 x 8 x 3.2 with a leaf spring.

**Misumi HNTAJ5 (same page, p.2717), the nut the revision uses.** Given: 10, 8, 3.2, 2.4, 5.8, M (thread drawn through).
Exactly the six figures the revision used; nothing new. Not dimensioned: body chamfers, leaf-spring wing, countersink ring.
So the revision's reading stands; the drawing alone is not a complete copy.

The SOURCES.txt STEP fallback for M5 is "HNTA5-5", which is neither HNTP5 nor HNTAJ5 and is not on these pages; no STEP of
any of these nuts was obtained.

**Misumi HBLFSN5 (BRKT-2020.pdf, p.2692).** Given: 20 (width, 10 + 10), 30 (both legs), 18 and 12 and 10 (hole positions),
4.5 (wall), 1 (tab height), 3-dia 5.3 (dia 4.2 for HBLFSN5-4), M5 tap (alteration C). Table: 15 g, CBM5-10 x 2, HNTT5-5 x 2,
1176 N. Not dimensioned: tab width and length, side-web thickness, inner pocket and fillets, counterbores on the base holes.
**Not complete enough for a faithful re-make.**

**Misumi HBLTS5 (BRKT-2020-ALT.pdf, p.2696).** Given: 14 (width, 7 + 7), 35 (both legs), 25 (hole position), 5 (thickness),
12 (inner gusset extent), dia 4.2 (inner corner), 2-dia 5.5 (dia 4.5 for HBLTS5-4). Table: 15 g, CBM5-10 x 2, HNTT5-5 x 2,
833 N. Not dimensioned: the slot tabs, the rib profile of the extrusion, chamfers. **Not complete enough for a faithful re-make.**

## Gaps (from SOURCES.txt): 7 STEPs not obtained

| Wanted file | Part | Why not |
|---|---|---|
| TNUT-2020-M3.step | Misumi HNTP5-3 | 3dfindit "Error during generation" since about 21:26 PST 2026-11-18 |
| TNUT-2020-M5.step | Misumi HNTA5-5 (fallback: no HNTP5-5 variant on 3dfindit) | generation error |
| BRKT-2020.step | Misumi HBLFSN5 | generation error |
| BRKT-2020-ALT.step | Misumi HBLTS5 | generation error |
| SHCS-M4x6.step (+ .pdf) | Misumi SCB4-6 | 3dfindit lists stainless only; McMaster 90128A208 STEP 8.6 MB, over the 5 MB limit |
| WASHER-M3-LARGE.step | ISO 7093-1 M3 | Misumi / Accu CAD need accounts; McMaster bot-blocked; Fabory 38215.030.001 generation error |
| WASHER-M4-LARGE.step | ISO 7093-1 M4 | as M3; Fabory size-4 variant generation failed, material unverified |

## SHA-256

```
268316031077c7439bf5a6910a318f42b23f5306d8869ad4c02eef51679ecb04  BRKT-2020-ALT.pdf
179aa6117fa82a4bc14d798e6145ec4d8fe47ebcbea32e5ca5524482719eb8f1  BRKT-2020.pdf
0b76dc89b5b090f28feace643a1786ca99cb7344f54ef4a90fbde9bb85ec0413  EXT2020-PROFILE.pdf
154dfcb88e03c1536e91659d063a6733731faaca8e831689fa6488e62df6169b  EXT2020-PROFILE.step
a8123ad4a56f1ef1de937d75805ac62aac28e00d71ba2608e3a19c387cba51cc  SOURCES.txt
fcd638422657195e5eb5ee817fbab32ed06317b96ce3d9ded4f374b0cfcb3f42  THUMBNUT-DIN466-M4.pdf
6ee5c27d6f10cec0cbeef203ef332a41166c3e3f5a53e35bb8ed1837e038c1ff  THUMBNUT-DIN466-M4.step
0db3cbadc5fcde47b1ceae9605e4a44780163e957f7ebc93ebd2efc628adcd98  TNUT-2020-M3.pdf
0db3cbadc5fcde47b1ceae9605e4a44780163e957f7ebc93ebd2efc628adcd98  TNUT-2020-M5.pdf
78211df2eb8ba5d8fad4577330ed8b8d0c09bc0e7baf0d61061db7d62af648e4  _DEVIATIONS/WASHER-M3-LARGE.pdf
c1726cdcc87fe8c98e0114b00b3ed903a062cefe59b6580389cb5441ba352dd8  _DEVIATIONS/WASHER-M4-LARGE.pdf
```
