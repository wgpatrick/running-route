# instinct_REQ-001b: Misumi CAD from REQ-001 (supplier CAD batch 3), second delivery

Ingested 2026-11-20 from Google Drive `mechloop handoff/results/REQ-001-supplier-cad-batch-3/`
(folder 1ZtlzfkmX-Yz92soEepnPbyNiPK0uQ43v). Collected by Instinct (the owner's browser agent) from the official MISUMI
catalogue on 3Dfindit / CADENAS, using the owner's existing 3Dfindit account. The STEP files are unchanged copies.
Only the file extension changed (.stp to .step). Each one is named by the maker's part number (the STEP PRODUCT name
matches the file name). The drawing PDFs are 3Dfindit "datasheet" exports (5 pages: 3D view, BOM, catalogue drawing,
technical data, plugins). They are copied unchanged to `vendor_docs/Misumi_<MPN>.pdf`.
Instinct's RESULT.md as delivered is `RESULT_instinct_REQ-001_2026-11-20.md`. RESULT.md does not record the 3Dfindit page URLs.

Nothing here has been copied to `vendor_cad/inbox/`. Staged for review only.

Checks: build123d / OCCT (`.venv`), import, solid count, validity, bbox, then point-in-solid ray probing of
sections, compared with the catalogue drawing on page 3 of each PDF.

| Part | Maker | MPN | Source | File | sha256 | Solids | Valid | BBox (mm) | Drawing check | Result | Replaces SKU |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Post-assembly insertion short nut M3, HFS5 (slot 6) | MISUMI | HNTAJ5-3 | 3Dfindit/CADENAS MISUMI catalogue (Drive id 1Wl39ZBGucHvOfke0hSMmvl62QjKjAHND) | HNTAJ5-3.step (AP214) | 3e22bf58f96c16ece3443de77ea009a0e02c2d1950d53ce64f24d29167dd1f5c | 1 | yes | 8.093 x 5.300 x 10.000 (with spring); nut 8.0 x 3.2 x 10.0 | 10 / 8 / 3.2 / 2.4 / 5.8 all match; M3 hole Ø2.459 (ISO M3x0.5 D1) | PASS | TNUT-2020-M3 |
| Post-assembly insertion short nut M5, HFS5 (slot 6) | MISUMI | HNTAJ5-5 | same (Drive id 1T2bUkQ0dVZLbua5ntmUukdzdq8jqrJLx) | HNTAJ5-5.step (AP214) | 8e519753fbaec9cc18476fa9289e8ec05d6cb0bb3df055246fef1bf79b349d76 | 1 | yes | 8.093 x 5.300 x 10.000 (with spring); nut 8.0 x 3.2 x 10.0 | 10 / 8 / 3.2 / 2.4 / 5.8 all match; M5 hole Ø4.134 (ISO M5x0.8 D1) | PASS | TNUT-2020-M5 |
| Tabbed bracket, 1 slot, HFS5, reversal tabbed, depth 20 | MISUMI | HBLFSNF5 | same (Drive id 1jM_P_jXaz5N8D-3LAwvR3FQE3Bs4BbUL) | HBLFSNF5.step (AP214) | 525e97c1376a694679482c0e8c1411ce315ac852aea2e020d455003e29ef9f47 | 1 | yes | 20.0 x 31.0 x 21.0 (30 x 20 legs + 1 mm tabs) | width 20 (10+10), legs 30 / 20, holes 2 x Ø5.2 at 18 / 10, wall 4.5, tabs 1: all match | PASS against its own drawing. NOT a like-for-like replacement for the design's bracket (see below) | BRKT-2020 (candidate only) |

Drawing PDFs (in vendor_docs/):

| File | sha256 | Content |
|---|---|---|
| Misumi_HNTAJ5-3.pdf | 9e128cd93a31cb4e85be7cbed412a7589f93c97f39c3b864548f9d2e8814ca6d | 3Dfindit datasheet. Family drawing HNTAJ5 / PACK-HNTAJ5. Technical data PN HNTAJ5-3, M 3 |
| Misumi_HNTAJ5-5.pdf | d031c1730634f3bd5fad36b912650ae46332438ff8040ef610ed898d57e319fc | as above. PN HNTAJ5-5, M 5 (same family drawing image) |
| Misumi_HBLFSNF5.pdf | facaee5bf33be15e070fc995e2b254d962aefa5a2425cb4a743412c1b00a0c1a | 3Dfindit datasheet. Drawing HBLFSNF5 (Chinese-language catalogue image). Technical data: applicable screw CBM5-10 x 2, applicable T-nut HNTT5-5 x 2, without cover holes (alteration C), without screw/nut set |

## HNTAJ5-3 / HNTAJ5-5: measured (file frame: thread axis Y, length along Z, width along X)

- Length along the slot: 10.000 (Z 0 to 10). Drawing 10.
- Neck: 5.800 wide (X ±2.900) and 0.800 high (Y -3.2 to -2.4). Drawing 5.8, 3.2 - 2.4.
- Body: 2.400 high (Y -2.4 to 0). Full 8.000 width (X ±4.000) only in a band about 0.4 mm deep just under the neck
  (Y -2.33 to -1.9). The flanks then taper to about 6.0 wide at the top face (Y = 0). The bottom corners have R0.2.
  Drawing: 8 wide, 2.4, chamfers shown without dimensions. Overall nut height is 3.200. Drawing 3.2.
- Thread: plain hole at the thread's minor diameter, Ø2.459 (M3) / Ø4.134 (M5). These are the ISO 965 D1 values for
  M3x0.5 / M5x0.8. There is no helical thread. The hole runs through and is centred (X 0, Z 5). Both ends have 90°
  countersinks out to the nominal diameter: 0.27 deep for M3 (Ø3.0) and 0.43 deep for M5 (Ø5.0). Full minor-diameter
  length is 2.66 (M3) / 2.34 (M5).
- Leaf spring (304 SS wing): two strips at Z 0.05 to 2.05 and 7.95 to 9.95, about 0.17 thick. They spring from the
  body face away from the neck (Y = 0) to Y = +2.1 in the free state. Total height with the spring is 5.3.
- Volume 206.75 mm3 (M3) / 175.04 mm3 (M5). At 7.85 g/cm3 that is 1.62 g / 1.37 g.
- Seating: the neck goes up into the slot opening, the 8 mm body sits under the lips, and the spring presses toward
  the slot floor. This matches our reading in tslot_2020_hardware.json. On HFS5 (lip 2.0, lip-to-floor 4.0, measured on
  inbox/HFS5-2020-500.step) body 2.4 + free spring 2.1 = 4.5, so the spring is preloaded by about 0.5 mm.

### Differences from our re-make (mechloop/parts/tslot.py `tnut_2020`, mechloop/parts/vendor/tslot_2020_hardware.json)

| Item | Re-make | Misumi STEP |
|---|---|---|
| Length / span / height / body / neck / neck width | 10 / 8 / 3.2 / 2.4 / 0.8 / 5.8 | same |
| Body cross-section | 8 x 2.4 rectangle | 8.0 only for about 0.4 mm under the lips, tapering to about 6.0 at the bottom face, R0.2 edges |
| Hole | nominal Ø3 / Ø5 through 3.2 | minor Ø2.459 / Ø4.134 with 90° countersinks at both ends |
| Thread length used by checks | 3.2 (json `thread_length_mm`) | full-diameter hole 2.66 (M3) / 2.34 (M5). 3.2 including the countersinks. For M5, 2.34 mm is 0.47 d. |
| Leaf spring | left out | modelled, rising 2.1 mm (free) from the body face away from the neck, toward the slot floor |
| Volume (detail) | 215.78 (M3) / 175.57 (M5) mm3 | 206.75 / 175.04 mm3. Ratio 0.958 / 0.997, inside the part's 0.8 to 1.6 tolerance |
| Bbox | 10 x 8 x 3.2 | 10 x 8.09 x 5.3 including the spring (8 x 3.2 without it) |

Frame for inbox use: the re-make has Z along the slot normal, X along the slot, and Z = 0 at the face that bears on
the lips. The STEP has Y along the thread (neck at -Y, bearing face at Y = -2.4), Z along the slot, and the origin at
the centre of the spring-side face at one end. Dropping it into the inbox would need a sidecar placement (rotation, plus
a 2.4 mm shift so the bearing face lands on Z = 0). The spring sticks out 2.1 mm past the simulation box on the floor side.

## HBLFSNF5: measured (file frame: width X 0..20, 30 mm leg along +Y, 20 mm leg along +Z, outside faces Y = 0 and Z = 0)

- Width 20.000, holes centred at X = 10.0. Drawing 20 (10 + 10).
- Legs: 30.0 along Y (the leg lying on Z = 0) and 20.0 along Z (the leg lying on Y = 0). Drawing 30 / 20.
- Wall: 4.5 thick at both holes (outside face to inside face). Drawing 4.5.
- Holes: 2 x Ø5.2. Drafted: Ø5.21 at the inside face, Ø5.66 at the outside (mounting) face. One sits 18.0 from the
  Y = 0 face in the 30 mm leg, the other 10.0 from the Z = 0 face in the 20 mm leg. Drawing 2-Ø5.2, 18 (and 30 - 18 = 12),
  10. The hole in the 30 mm leg has a Ø9 spot face on the inside.
- Locating tabs, 1.0 proud, 6.0 wide (X 7 to 13). On the 30 mm leg: two tabs, Y 4.58 to 12.42 and 24.08 to 25.92, with
  the hole between them. On the 20 mm leg: a 6.0 x 5.64 boss around the hole (Z 7.18 to 12.82), with the hole through it.
  The drawing gives 1 (tab height) and 4.5. HFS5 slot opening measured on inbox/HFS5-2020-500.step is 6.000, so the CAD
  tab is a nominal line-to-line fit.
- Outer profile: closed side webs. The outside is a cylindrical arc (R32) from leg tip to leg tip.
- Volume 5042.8 mm3, about 13.6 g if aluminium at 2.70 g/cm3. Material and mass are not given in the delivered PDF.
- No M5 tapped cover holes. This is the "w/o C" variant, as the technical data says.

### Differences from the design's BRKT-2020 (`corner_bracket_2020`, community casting `vendor_cad/corner_bracket_2020.step`)

| Item | BRKT-2020 (design) | HBLFSNF5 |
|---|---|---|
| Legs | 20 x 20, symmetric | 30 x 20, asymmetric |
| Width | 17 | 20 |
| Leg thickness | 3.0 | 4.5 |
| Screw holes | 6 mm slot per leg (M5 sits 10.0 to 13.1 from the corner). Design puts screws at 11.5 / 13.1 | round Ø5.2, fixed at 18 (30 leg) and 10 (20 leg) |
| Inside | open between webs 12 apart, head pockets | closed webs, solid 4.5 legs, spot face |
| Tabs | 1 mm nubs | 1 mm tabs, 6.0 wide |
| Screws (maker's) | design: SHCS M5x8, no washer, drop-in T-nut | MISUMI lists CBM5-10 x 2 with HNTT5-5 T-nuts |
| Volume | detail 2215.9 mm3 (sim prism 3400) | 5042.8 mm3. Ratio 2.28 to the detail, outside BRKT-2020's volume_ratio 0.6 to 1.9 |

HBLFSNF5 is not the HBLFSN5 that the design notes name (vendor_cad/inbox/README.md, docs/PROVENANCE_AUDIT.md,
supplier_2026-11-19/MANIFEST.md). HBLFSN5 per the 2019 catalogue is 30 x 30 legs, 3 x Ø5.3 holes, 15 g. REQ-001 itself
asked for "HBLFSNF5 or the matching MISUMI corner bracket", and Instinct delivered HBLFSNF5. HBLFSNF5 has round Ø5.2
holes, as the open item in docs/PRINTER_V10_1.md wanted. Its 30 / 20 legs and fixed hole positions mean the frame
layout and the screw positions must be re-checked before it can stand in for BRKT-2020. Whether to adopt it is a
design decision. Staged as a candidate, not a replacement.

## Still missing

- PEM S-M3-0 (self-clinching nut): not delivered. The PEM catalogue needs a new registration, and there is no PEM
  catalogue on 3Dfindit. Instinct found a Bossard-listed "S-M3-0ZI" (BN 20518) on 3Dfindit. It did not download it, and
  that file is not verified as matching. The owner has not yet been asked to decide.
- Misumi page URLs and prices for the three parts are not recorded in RESULT.md.
- No REQ-002 results folder exists under `mechloop handoff/results/` as of this ingest.
