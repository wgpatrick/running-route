# Reference parts batch 01: web benchmark results (2026-11-19)

Source: `web_benchmark_2026-11-19.csv` (41 rows), collected by the owner's agent on the suppliers' public quote pages at
customer pace; no orders, no manual reviews. Screenshots are in the owner's Drive folder "mechloop reference parts batch01".
Skipped under their terms of service (automated access forbidden): Xometry, Protolabs, Fictiv, RapidDirect. JLC3DP offers
no PETG for FDM. OSH Cut's RP03 upload failed technically (not a DFM refusal).

## Expected findings against what each shop flagged

| Part | Expected (MANIFEST) | SendCutSend | OSH Cut | Fabworks | Hubs | JLCCNC / PCBWay / Craftcloud |
|---|---|---|---|---|---|---|
| RP03 sheet channel | flange too short | **error**: min flange 0.254 in (6.45 mm); blocks finishing step | upload failed | **error**: min flange 0.367 in (9.32 mm); blocks checkout | - | none shown |
| RP03 | hole 1.5 mm from bend | not flagged | - | **warning**: "major deformation", move the cutout 0.138 in (3.5 mm) further from the bend | - | none shown |
| RP03 | (not expected) | **warning**: drawn bend radius 0.09 in differs from SCS's 0.032 in; changes finished dimensions | - | - | - | - |
| RP04 laser plate | hole 0.8 mm from edge | **review required**: min hole-to-edge 0.97 mm for instant quoting | "small gaps" warning (1 area) | not flagged | - | none shown |
| RP04 | 1.2 mm hole | not flagged | not flagged | not flagged | - | none shown |
| RP04 | 1.0 mm slot | not flagged | "narrow features" warning (1 area; slot or sharp corner, not said which) | not flagged | - | none shown |
| RP04 | sharp inside corner | not flagged | see above | not flagged | - | none shown |
| RP05 FDM clip | 0.6 mm wall | - | - | - | **warning**: "10% of walls are too thin" | Craftcloud: none |
| RP05 | 20 mm flat overhang | - | - | - | not flagged ("no hard to remove support") | - |
| RP05 | 1.5 mm pin | - | - | - | not flagged ("no intricate details") | - |
| RP01 CNC | sharp pocket corners, deep slot, tapped hole | - | - | - | - | no automated DFM; **PCBWay adds a minimum fillet to recessed corners and deburrs edges to C0.2/R0.2 by default**, i.e. it changes the geometry rather than refusing it |
| RP02 CNC control | none | - | - | - | - | none shown |

## Against our SendCutSend rule data (mechloop/data/supplier_rules/sendcutsend.json, specs file of 2026-11-05)

- Hole to edge, 6061 0.125 in: our rule 0.965 mm (`min_hole_to_edge` = 0.038 in); the quote page said **0.97 mm**. Match.
- Minimum hole, 6061 0.125 in: our rule 0.813 mm; the 1.2 mm hole was not flagged. Consistent.
- Bend radius, 5052 0.090 in: our rule 0.813 mm (0.032 in); the quote page said **0.032 in**. Match. Gap in our check: the
  drawn radius is recorded but not compared with the shop's radius, so we would not have raised SCS's bend-radius warning.
- Minimum flange, 5052 0.090 in: the quote page said **0.254 in (6.45 mm)**; our specs-file rule `min_flange_length_after_bend`
  is 0.326 in (8.28 mm), and Fabworks asks 0.367 in. Different definitions (where the flange is measured); to resolve.
- Hole near a bend: SCS did not flag it; Fabworks did (3.5 mm more needed).

## Prices (USD, as shown; shipping excluded unless stated)

| Part | qty | SendCutSend | OSH Cut (standard) | Fabworks | JLCCNC (estimate) | PCBWay (pre-quote) | Craftcloud (incl. ship) | Hubs |
|---|---|---|---|---|---|---|---|---|
| RP03 | 1 / 10 | 21.64 / 68.50 (incl. deburr) | - | 21.42 / 66.20 | 3.73 / 9.20 (5052-O, not H32) | - | - | - |
| RP04 | 1 / 10 | 15.01 / 90.50 | 18.94 / 95.40 | 19.58 / 90.40 | 3.75 / 18.10 (5052, not 6061) | - | - | - |
| RP01 | 1 / 10 | - | - | - | 27.98 / 176.60 (no thread) | 39.84 / 237.86 (no thread) | - | - |
| RP02 | 1 / 10 | - | - | - | 20.40 / 120.60 | 39.22 / 232.13 | - | - |
| RP05 | 1 / 10 | - | - | - | - | - | 24.02 / 25.88 | 90.00 / 90.00 (min order) |

## What this tells us

1. Sheet metal: the three US shops' automated checks are real and partly agree. SendCutSend's figures match its own
   published specs file exactly where we compared; Fabworks is stricter on flanges and checks hole-to-bend deformation.
2. None of the shops flagged the 1.2 mm hole or the sharp inside corner of RP04, and only OSH Cut flagged a narrow feature:
   these are not refusal-level issues for laser cutting in 3.2 mm aluminium.
3. CNC: no automated DFM from the shops we could use; the Chinese shops quote and leave DFM to engineers (email route).
   PCBWay silently adds fillets, so a design must state where sharp corners matter.
4. FDM services check little (Hubs: thin walls only).

## Changes to our checks suggested by these results (not yet made)

- Compare the drawn bend radius with the assigned shop's radius (warning, as SCS does).
- Resolve the minimum-flange definition (0.254 vs 0.326 in for SCS 5052 0.090); add Fabworks' 0.367 in and its hole-to-bend
  deformation rule (3.5 mm more needed here) as a hand-collected rule from the quote page.
- Record SCS's instant-quote hole-to-edge as "review required" (not a refusal) and OSH Cut's narrow-feature/small-gap
  warnings as recommendations.
