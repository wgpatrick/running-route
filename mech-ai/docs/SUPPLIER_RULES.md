# Suppliers' published design rules (sheet metal and CNC)

Every figure here was read from a supplier's own public web pages on **2026-11-19** by plain page fetch (no account,
no upload, no quote) and is kept as data in `mechloop/data/supplier_rules/<supplier>.json`. Each rule carries the
supplier, process, material, thickness (in mm and as published), rule kind, limit (mm, or a formula in the thickness
`t`, the bend radius `r` and the feature size `d`), comparison, severity, the source URL, a short quote from the page
and the retrieval date. Nothing is interpolated or invented: where a supplier publishes no figure for a material or a
thickness, the check says "no published rule" for it.

Suppliers: SendCutSend, OSH Cut, Protolabs, Xometry, Fictiv and Hubs (Protolabs Network). The older shop profiles
(`mechloop/shops/sendcutsend.json`, `xometry.json`, docs/FABRICATORS.md, read 2026-11-15) stay in force for stock,
services and tolerances; this file adds the per-thickness bending, hardware, tapping and countersinking tables and the
other suppliers.

## 1. How the check uses them

`verifiers/manufacture.py` calls `verifiers/dfm_supplier.py` for every sheet and machined part, after the process
checks and the shop-profile checks:

1. **Features** are measured on the part (`dfm_supplier.features_of`): flat parts: every hole and cut-out (size, round
   or not, slot if at least twice as long as wide), material to the outer edge, to the next cut feature and to the next
   round hole, outline notches and material necks, share cut away, flat size, countersinks; bent parts: each bend
   (inside radius, angle, length), each flange's formed length from the apex at 41 points along the bend (so the
   "share of the bend that meets the minimum flange" rule can be judged), every hole and cut-out on the flanges with
   its distance to each bend's tangent line, material to the non-bend edges; the flat blank of a one-bend part;
   self-clinching hardware (catalogue `NUT-PEM-*` parts and screws declared `insert="pem"`): centre to edge and other
   cut features, to the bend, to the next one; tapped holes (from the screws); machined parts: extents, thinnest
   wall, smallest hole, threads.
2. **Assigned supplier**: the part's `meta["dfm"]["shop"]`, else the design's `manufacturing["shop"]`, else
   SendCutSend for sheet and Xometry for machined parts (`supplier_rules.shop_for`). Any supplier in the data can be
   named (`oshcut`, `protolabs`, `fictiv`, `hubs`); one without a stock profile gets generic stock and limits for the
   process checks.
3. **Findings** (`code="supplier_rule"`): a failed rule of the assigned supplier is an **error** when the supplier
   states it as a requirement ("must", "at least", a size or capability limit, "will be unable to form") and a
   **warning** when it phrases it as a recommendation ("we recommend", "should", "for best results", "will
   distort"). Each finding names the rule id, the supplier, the measured value, the limit, the comparison, the
   source URL, the supplier's own words and the retrieval date, and points at the worst places on the part. A piece of
   hardware whose SKU the supplier does not list gives `supplier_hardware_not_listed` (warning) and is judged against
   the same family and thread whose thickness range admits the sheet.
4. **Cross-supplier summary** (`code="supplier_rules_summary"`, info, one per part, and
   `metrics.parts[<part>].supplier_rules`): the verdict under every supplier's published rules (passes / passes with
   N recommendations not met / fails N rules / no published rules), the rule kinds a supplier publishes nothing for at
   that material and thickness, and the rules that could not be evaluated because mechloop does not extract the
   feature. Useful when choosing a shop.

A preference (SendCutSend's "closer to 1X - 1.5X the material thickness" web) is kept as **info**. Rules kept only
for cross-checking (the same figure on a second page) are marked `duplicate_of` and not judged twice.

Code: data `mechloop/data/supplier_rules/*.json`; loading and evaluation `mechloop/shops/supplier_rules.py`
(geometry-free, testable with feature dicts); features and findings `mechloop/verifiers/dfm_supplier.py`; one call in
`verifiers/manufacture.py`. Tests: `tests/test_supplier_rules.py`.

## 2. Pages read

| Supplier | Pages (all 2026-11-19) |
|---|---|
| SendCutSend | [bending calculator](https://sendcutsend.com/bending-calculator/) (per-thickness K, radius, die width, min formed flange, relief), [processing min/max](https://sendcutsend.com/materials/processing-min-max/) (bending, tapping, countersinking per thickness), [min/max part sizes](https://sendcutsend.com/materials/min-max/), [bending guidelines](https://sendcutsend.com/services/cnc-bending/), [bend deformation](https://sendcutsend.com/guidelines/bend-deformation/), [bend reliefs](https://sendcutsend.com/blog/guide-to-designing-bend-reliefs/), [sheet cutting guidelines](https://sendcutsend.com/guidelines/sheet-cutting/), [tolerances and cut-feature relationships](https://sendcutsend.com/blog/basic-tolerances-and-cut-feature-relationships/), [hole distance specifications](https://sendcutsend.com/blog/how-to-apply-hole-distance-specifications/), [hardware catalog](https://sendcutsend.com/guidelines/hardware/catalog/), [tapping](https://sendcutsend.com/services/tapping/), [countersinking](https://sendcutsend.com/services/countersinking/), material pages [5052](https://sendcutsend.com/materials/5052-aluminum/) and [6061](https://sendcutsend.com/materials/6061-aluminum/) |
| OSH Cut | [capabilities](https://www.oshcut.com/capabilities), [min/max material sizes](https://www.oshcut.com/minimum-maximum-material-sizes), [bending](https://www.oshcut.com/services/bending), [laser cutting](https://www.oshcut.com/services/laser-metal-cutting), [countersinking](https://www.oshcut.com/services/countersinking), [tapping](https://www.oshcut.com/services/metal-tapping), [bending design rules](https://www.oshcut.com/design-guide/metal-bending-design-rules) |
| Protolabs | [sheet metal design guidelines](https://www.protolabs.com/services/sheet-metal-fabrication/design-guidelines/), [sheet metal DFM toolkit](https://www.protolabs.com/resources/design-for-sheet-metal-fabrication-toolkit/), [laser cutting](https://www.protolabs.com/services/sheet-metal-fabrication/laser-cutting/), [forming](https://www.protolabs.com/services/sheet-metal-fabrication/forming/), [CNC milling design guidelines](https://www.protolabs.com/services/cnc-machining/cnc-milling/design-guidelines/) |
| Xometry | [sheet metal fabrication](https://www.xometry.com/capabilities/sheet-metal-fabrication/) (design guideline table), [laser cutting](https://www.xometry.com/capabilities/sheet-cutting/laser-cutting/), [sheet cutting](https://www.xometry.com/capabilities/sheet-cutting/), [manufacturing standards](https://www.xometry.com/manufacturing-standards/), [CNC machining](https://www.xometry.com/capabilities/cnc-machining-service/) |
| Fictiv | [sheet metal specifications](https://www.fictiv.com/specifications/sheet-metal), [CNC specifications](https://www.fictiv.com/specifications/cnc-machining) |
| Hubs | [sheet metal fabrication guide](https://www.hubs.com/guides/sheet-metal-fabrication/) |

**Not read / not published** (also in each file's `not_read`):

- SendCutSend's per-thickness "View specs" sheets (minimum hole, minimum bridge, tapping and countersink edge
  distances per stock) are loaded by the material pages from `app.sendcutsend.com`, which this session may not fetch
  (the request was refused); only one worked figure (0.063 in. tapping min hole-to-edge, 0.125 in. 5052) appears in a
  blog post and is included. The hardware catalog's studs and standoffs were not transcribed (nuts only). Its catalog
  lists no `S-M3-1` (the M3 carbon-steel nut is `S-M3-0`).
- OSH Cut keeps per-thickness bend radius, k-factor and minimum flange in its quoting app's catalogue
  (`app.oshcut.com/catalog`, not on the allowed host list; not fetched) and publishes no hole, web or edge figures on
  www.oshcut.com. `/design-guide` returned 404. Its size table prints a "Min Size" (e.g. 0.1) with no unit: kept as
  published, not evaluated.
- Protolabs `/services/cnc-machining/design-guidelines/` returned 404 (the milling guidelines were read); no corner
  radius against depth, wall against height or hole depth figure is published there. PEM edge distances are deferred
  to PennEngineering (not read).
- Xometry's sheet-metal design guide URL and `/capabilities/sheet-metal-manufacturing/` returned 404; its machining
  resource articles (corner radii, thin walls, cost reduction) returned HTTP 429 (rate limited) on the day. Their
  figures (3:1 corner L:D, 1/32 in. wall, 3 x D thread depth) stay in `mechloop/shops/xometry.json` as read on
  2026-11-15 and are not duplicated here. The CNC design guide is a gated PDF.
- Fictiv's `/articles/sheet-metal-design-guide` redirects to an index and `/tolerances-and-specifications` returned
  404; the specification pages were read. Hubs' knowledge-base design guides returned 404; Hubs is now Protolabs
  Network and its figures are generic best practice.

## 3. Disagreements (kept both, flagged in the data with `conflicts`)

| Topic | One page says | Another says |
|---|---|---|
| SendCutSend minimum hole | sheet-cutting guideline and pre-flight checklist: "At least 50% of material thickness" (error) | 5052 page: "Minimum hole size: Equal to material thickness"; 6061 page: "Design holes no smaller than material thickness" (kept as warnings) |
| SendCutSend hole to edge | tolerances blog: bridging "no less than 50% of the material thickness"; holes "at least 1X their diameter from an edge" | 5052 page: "at least 2x thickness between a hole and an edge"; 6061 page: "1.5–2× material thickness away from edges" |
| SendCutSend flange support | bend deformation: "Approximately 50% of a bend's length must meet the minimum" (error) | bending guidelines: "at least ~50–60% of the bend's length on both sides" (warning at 60 %); 0.187 in. and thicker "may require ... the full bend length" (warning) |
| SendCutSend 5052 .080 in. bend radius | bending calculator: .038 in. | processing min/max: .045 in. (the older shop profile uses .045 in.) |
| SendCutSend hardware F-M2.5-1, F-M3-1, F-M4-1, F-M5-1 | catalogue "Aluminum material ranges" printed as "0.63″-0.090″" (inverted, apparently 0.063 in.) | the same SKU's min/max sheet thickness rows (0.059 to 0.090 in.), which are the ones evaluated |
| Protolabs minimum flange | design guidelines: "at least 4 times the material thickness" (must) | DFM toolkit: 2.5 to 3.0 x t + bend radius for aluminium (3.5 to 4.0 for steels at some thicknesses) |
| Xometry minimum hole | laser cutting: "2X material thickness with a minimum of 0.062"" | sheet cutting: "larger than the material thickness or 0.050”, whichever is greater" |
| Xometry kerf | laser cutting: "Approximately 0.020"" | sheet cutting: "around 0.008” with a +/- 0.004” tolerance" |
| Between suppliers: minimum bend radius | SendCutSend forms 5052 .090 in. at .032 in. (0.81 mm, its only radius) and 5052 .040 in. at .024 in. | Xometry and Hubs: inside radius at least 1 x thickness; Fictiv 5052: 0.5t to 1.0t |
| Between suppliers: hole to bend | SendCutSend: half the die width from the bend centre (5052 .125 in.: 8.0 mm) | Hubs 2 x t from the start of the radius; Fictiv 2.5 x t + r; Protolabs 2.5 to 4 x t + r; Xometry 6 x t |
| Between suppliers: hole to edge | SendCutSend 1 x hole diameter; Hubs 1 x t | Xometry and Fictiv 2 x t; Protolabs 0.125 in. flat above 0.036 in. stock |
| Between suppliers: hole to hole | Hubs 2 x t | Xometry 6 x t |
| Between suppliers: minimum hole | SendCutSend 0.5 x t | Protolabs, Hubs, Fictiv 1 x t; Xometry 1 to 2 x t (pages disagree) |

Where a page does not say what a distance is measured from, the data's `measured` field records the reading used
(for example Protolabs' "+ bend radius" distances are taken from where the bend's radius starts).

## 4. Gaps: rules recorded but not evaluated

Bend relief width and depth and corner relief distance (relief geometry is not extracted), SendCutSend's flat
(before-bend) flange length (the page does not say where it is measured from; the formed length is judged), U- and
C-channel base ratio, OSH Cut's gauging edge, countersink depth, major diameter and distance to other features
(only the count of countersinks is extracted), SendCutSend's general tapped-hole edge formula (needs the per-material
figure that was not readable), Protolabs' 2 in. milling depth and Fictiv's pocket depth against tool diameter (feature
depths are not extracted), Xometry's corner radius against depth (in the older profile). The flat blank of a part
with more than one bend is not unfolded, so blank-size rules are not judged for it; a one-bend blank uses the
supplier's K-factor where published (K = 0.5, marked as an estimate, otherwise).

## 5. printer_v10_1 against the rules (2026-11-19)

32 sheet parts (no machined parts). Assigned supplier SendCutSend for all (the design's `assign(sheet="sendcutsend")`).

- **SendCutSend: no errors.** 49 warnings, all against its recommendations: holes smaller than the thickness and
  holes nearer the edge than 1.5 to 2 x t on 6061 and 5052 parts (the material pages' figures; the 50 % guideline
  minimum is met everywhere), holes nearer the edge than their own diameter (18 parts, mostly large motor and
  bearing bores), two slots in `y_plate_left`/`right` nearer than 1.5 x width to the next feature, and two holes in
  `x_belt_bracket` and `y_endstop_mount` (5052 .090 in.) 5.87 and 5.93 mm from the bend centre against half the
  0.472 in. die (6.0 mm): they will distort slightly. Five self-clinching M3 nuts are drawn as PEM `S-M3-1`, which
  SendCutSend does not list (`supplier_hardware_not_listed`); judged against `S-M3-0` they meet its 0.250 in. edge and
  bend distances.
- **Protolabs:** one part fails: `bed_plate` (12.7 mm MIC-6) is past its 0.250 in. sheet range. Recommendations not
  met: holes under 1 x t, holes nearer than 0.125 in. to the edge, holes nearer the bend than 2.5 x t + r (6 bent parts).
- **Xometry, Fictiv, Hubs:** no errors; many recommendation misses, chiefly their stricter ratios (Xometry hole to
  hole 6 x t and feature 2 x t; Fictiv hole to edge 2 x t; Hubs and Xometry bend radius at least 1 x t, which
  SendCutSend's own 0.81 mm radius in .090 in. 5052 does not meet). Xometry recommends parts of at least 1 in.:
  `x_belt_clamp` and the two `y_tension_anchor`s are smaller.
- **OSH Cut:** passes, but only thickness and maximum size are published, so most rule kinds are "no published rule".
- Not evaluated on v10_1 for want of extracted features: bend reliefs and corner reliefs (8 bent parts), flat flange
  length, U-channel ratio, countersink depth (`bed_plate`).

Real violations of an assigned supplier's requirement: none. Everything reported for SendCutSend is a recommendation;
the gaps above are where a rule exists but was not measured.

## 6. The rules

### Counts

| supplier | rules | by process | materials named | thicknesses with their own rows |
|---|---|---|---|---|
| Fictiv | 19 | bend 11, cnc_milling 2, hardware 1, laser_cut 5 | al*, al5052, al6061, stainless304, steel | none (ratios and ranges only) |
| Hubs (Protolabs Network) | 7 | bend 4, laser_cut 3 | all (*) | none (ratios and ranges only) |
| OSH Cut | 63 | bend 2, countersink 1, laser_cut 59, tap 1 | al*, al5052, al6061, stainless304, steel | 24 (0.508 to 19.05 mm) |
| Protolabs | 70 | bend 50, cnc_milling 7, countersink 1, hardware 2, laser_cut 10 | al*, al5052, al6061, al_mic6, stainless304, steel | none (ratios and ranges only) |
| SendCutSend | 619 | bend 317, countersink 26, hardware 117, laser_cut 109, tap 50 | al*, al5052, al6061, al_mic6, stainless304, steel | 21 (0.762 to 19.05 mm) |
| Xometry | 22 | bend 7, cnc_milling 4, countersink 2, laser_cut 9 | all (*) | none (ratios and ranges only) |

### Rules that apply at every thickness (or a published thickness range)

t = sheet thickness, r = inside bend radius, d = hole or slot size. Per-thickness Protolabs rows are shown for 5052; 6061, MIC-6 (aluminium column), mild steel and 304 have their own rows in the data. OSH Cut part-size rows and SendCutSend per-thickness rows are in the tables below or in the data.

| rule kind | supplier | material | thickness | limit | severity | rule id |
|---|---|---|---|---|---|---|
| hole_min | Fictiv | * | all | >= 1 x t, at least 0.787 mm | warning | `fictiv.cut.hole_min` |
| hole_min | Hubs (Protolabs Network) | * | all | >= 1 x t | warning | `hubs.cut.hole_min` |
| hole_min | Protolabs | * | all | >= 1 x t | warning | `protolabs.cut.hole_min` |
| hole_min | SendCutSend | * | all | >= 0.5 x t | error | `sendcutsend.cut.hole_min_t_ratio` |
| hole_min | SendCutSend | 5052 H32 Aluminum | all | >= 1 x t | warning | `sendcutsend.cut.hole_min_al5052_page` |
| hole_min | SendCutSend | 6061 T6 Aluminum | all | >= 1 x t | warning | `sendcutsend.cut.hole_min_al6061_page` |
| hole_min | Xometry | * | all | >= 2 x t, at least 1.575 mm | warning | `xometry.cut.feature_min_laser` |
| hole_min | Xometry | * | all | >= 1 x t, at least 1.27 mm | warning | `xometry.cut.hole_min_sheetcut` |
| slot_min | Fictiv | * | all | >= 1 x t | warning | `fictiv.cut.slot_min` |
| slot_min | Protolabs | * | all | >= 1 x t | warning | `protolabs.cut.slot_min` |
| slot_min | SendCutSend | 5052 H32 Aluminum | all | >= 1 x t | warning | `sendcutsend.cut.slot_min_al5052_page` |
| notch_min | Protolabs | * | all | >= 1 x t, at least 1.016 mm | error | `protolabs.cut.notch_min` |
| tab_min | Protolabs | * | all | >= 2 x t, at least 3.2 mm | error | `protolabs.cut.tab_min` |
| web_min | SendCutSend | * | all | >= 0.5 x t | warning | `sendcutsend.cut.web_min_t_ratio` |
| web_min | SendCutSend | * | all | >= 1 x t | info | `sendcutsend.cut.web_preferred_t_ratio` |
| hole_edge_web | Fictiv | * | all | >= 2 x t, at least 1.575 mm | warning | `fictiv.cut.hole_edge` |
| hole_edge_web | Hubs (Protolabs Network) | * | all | >= 1 x t | warning | `hubs.cut.hole_edge` |
| hole_edge_web | Protolabs | * | 0.036 in. (0.914mm) or thinner | >= 1.574 mm | warning | `protolabs.cut.hole_edge_thin` |
| hole_edge_web | Protolabs | * | thicker than 0.036 in. (0.914mm) | >= 3.175 mm | warning | `protolabs.cut.hole_edge_thick` |
| hole_edge_web | SendCutSend | 5052 H32 Aluminum | all | >= 2 x t | warning | `sendcutsend.cut.hole_edge_al5052_page` |
| hole_edge_web | SendCutSend | 6061 T6 Aluminum | all | >= 1.5 x t | warning | `sendcutsend.cut.hole_edge_al6061_page` |
| hole_edge_web | SendCutSend | * | all | >= 1 x d | warning | `sendcutsend.cut.hole_edge_d_ratio` |
| hole_edge_web | Xometry | * | all | >= 2 x t | warning | `xometry.cut.hole_edge` |
| slot_edge_web | SendCutSend | * | all | >= 1.5 x d | warning | `sendcutsend.cut.slot_edge_w_ratio` |
| hole_hole_web | Hubs (Protolabs Network) | * | all | >= 2 x t | warning | `hubs.cut.hole_hole` |
| hole_hole_web | Xometry | * | all | >= 6 x t | warning | `xometry.cut.hole_hole` |
| cut_away_max | SendCutSend | * | all | <= 0.5 | warning | `sendcutsend.cut.removed_max_fraction` |
| part_min_size | Protolabs | * | all | >= 6.35 x 6.35 mm | error | `protolabs.cut.part_min_flat` |
| part_min_size | Xometry | * | all | >= 25.4 x 25.4 mm | warning | `xometry.cut.part_min_laser` |
| part_max_size | Protolabs | * | all | <= 990.6 x 1193.8 mm | error | `protolabs.cut.part_max` |
| thickness_min | OSH Cut | * | all | >= 0.508 mm | error | `oshcut.cut.thickness_min` |
| thickness_max | OSH Cut | al* | all | <= 25.4 mm | error | `oshcut.cut.thickness_max_al` |
| thickness_max | OSH Cut | steel | all | <= 25.4 mm | error | `oshcut.cut.thickness_max_steel` |
| thickness_max | OSH Cut | stainless304 | all | <= 15.875 mm | error | `oshcut.cut.thickness_max_stainless` |
| thickness_range | Fictiv | * | all | within 0.381 to 9.525 mm | warning | `fictiv.cut.thickness_range` |
| thickness_range | Protolabs | * | all | within 0.609 to 6.35 mm | error | `protolabs.cut.thickness_range` |
| thickness_range | Xometry | * | all | within 0.61 to 6.35 mm | info | `xometry.cut.thickness_range_fab` |
| flange_min | Fictiv | * | all | >= 4 x t | warning | `fictiv.bend.flange_min_standard` |
| flange_min | Fictiv | * | all | >= 3 x t | error | `fictiv.bend.flange_min_absolute` |
| flange_min | Hubs (Protolabs Network) | * | all | >= 2 x t + r | warning | `hubs.bend.flange_min` |
| flange_min | Protolabs | * | all | >= 4 x t | error | `protolabs.bend.flange_min_4t` |
| flange_min | Protolabs | Aluminum / Copper | .024 -.050 in. | >= 3 x t + r | error | `protolabs.bend.flange_min.al5052..024-.050in.` |
| flange_min | Protolabs | CRS / Galv. / Galvnl. | .024 -.050 in. | >= 3.5 x t + r | error | `protolabs.bend.flange_min.steel..024-.050in.` |
| flange_min | Protolabs | Stainless Steel | .024 -.050 in. | >= 3.5 x t + r | error | `protolabs.bend.flange_min.stainless304..024-.050in.` |
| flange_min | Protolabs | Aluminum / Copper | .060 -.090 in. | >= 2.5 x t + r | error | `protolabs.bend.flange_min.al5052..060-.090in.` |
| flange_min | Protolabs | CRS / Galv. / Galvnl. | .060 -.090 in. | >= 2.75 x t + r | error | `protolabs.bend.flange_min.steel..060-.090in.` |
| flange_min | Protolabs | Stainless Steel | .060 -.090 in. | >= 2.75 x t + r | error | `protolabs.bend.flange_min.stainless304..060-.090in.` |
| flange_min | Protolabs | Aluminum / Copper | .100 -.134 in. | >= 2.5 x t + r | error | `protolabs.bend.flange_min.al5052..100-.134in.` |
| flange_min | Protolabs | CRS / Galv. / Galvnl. | .100 -.134 in. | >= 2.5 x t + r | error | `protolabs.bend.flange_min.steel..100-.134in.` |
| flange_min | Protolabs | Stainless Steel | .100 -.134 in. | >= 2.5 x t + r | error | `protolabs.bend.flange_min.stainless304..100-.134in.` |
| flange_min | Protolabs | Aluminum / Copper | .160+ | >= 3 x t + r | error | `protolabs.bend.flange_min.al5052..160plus` |
| flange_min | Protolabs | CRS / Galv. / Galvnl. | .160+ | >= 3.5 x t + r | error | `protolabs.bend.flange_min.steel..160plus` |
| flange_min | Protolabs | Stainless Steel | .160+ | >= 4 x t + r | error | `protolabs.bend.flange_min.stainless304..160plus` |
| flange_support_min | SendCutSend | * | all | >= 0.5 | error | `sendcutsend.bend.support_fraction` |
| flange_support_min | SendCutSend | * | all | >= 0.6 | warning | `sendcutsend.bend.support_fraction_bending_page` |
| flange_support_min | SendCutSend | * | 0.187” and thicker | >= 1 | warning | `sendcutsend.bend.support_full_thick` |
| feature_to_bend | Fictiv | * | all | >= 2.5 x t + r | warning | `fictiv.bend.hole_to_bend` |
| feature_to_bend | Hubs (Protolabs Network) | * | all | >= 2 x t | warning | `hubs.bend.hole_to_bend` |
| feature_to_bend | Protolabs | * | all | >= 4 x t | info | `protolabs.bend.feature_near_bend_general` |
| feature_to_bend | Protolabs | Aluminum / Copper | .024 -.050 in. | >= 3 x t + r | warning | `protolabs.bend.feature_to_bend.al5052..024-.050in.` |
| feature_to_bend | Protolabs | CRS / Galv. / Galvnl. | .024 -.050 in. | >= 3.5 x t + r | warning | `protolabs.bend.feature_to_bend.steel..024-.050in.` |
| feature_to_bend | Protolabs | Stainless Steel | .024 -.050 in. | >= 3.5 x t + r | warning | `protolabs.bend.feature_to_bend.stainless304..024-.050in.` |
| feature_to_bend | Protolabs | Aluminum / Copper | .060 -.090 in. | >= 2.5 x t + r | warning | `protolabs.bend.feature_to_bend.al5052..060-.090in.` |
| feature_to_bend | Protolabs | CRS / Galv. / Galvnl. | .060 -.090 in. | >= 2.75 x t + r | warning | `protolabs.bend.feature_to_bend.steel..060-.090in.` |
| feature_to_bend | Protolabs | Stainless Steel | .060 -.090 in. | >= 2.75 x t + r | warning | `protolabs.bend.feature_to_bend.stainless304..060-.090in.` |
| feature_to_bend | Protolabs | Aluminum / Copper | .100 -.134 in. | >= 2.5 x t + r | warning | `protolabs.bend.feature_to_bend.al5052..100-.134in.` |
| feature_to_bend | Protolabs | CRS / Galv. / Galvnl. | .100 -.134 in. | >= 2.5 x t + r | warning | `protolabs.bend.feature_to_bend.steel..100-.134in.` |
| feature_to_bend | Protolabs | Stainless Steel | .100 -.134 in. | >= 2.5 x t + r | warning | `protolabs.bend.feature_to_bend.stainless304..100-.134in.` |
| feature_to_bend | Protolabs | Aluminum / Copper | .160+ | >= 3 x t + r | warning | `protolabs.bend.feature_to_bend.al5052..160plus` |
| feature_to_bend | Protolabs | CRS / Galv. / Galvnl. | .160+ | >= 3.5 x t + r | warning | `protolabs.bend.feature_to_bend.steel..160plus` |
| feature_to_bend | Protolabs | Stainless Steel | .160+ | >= 4 x t + r | warning | `protolabs.bend.feature_to_bend.stainless304..160plus` |
| feature_to_bend | Xometry | * | all | >= 6 x t | warning | `xometry.bend.hole_to_bend` |
| bend_radius_min | Fictiv | Aluminum 5052 | all | >= 0.5 x t | warning | `fictiv.bend.radius_min.al5052` |
| bend_radius_min | Fictiv | Cold Rolled Steel | all | >= 0.5 x t | warning | `fictiv.bend.radius_min.steel` |
| bend_radius_min | Fictiv | Stainless 304 | all | >= 1 x t | warning | `fictiv.bend.radius_min.stainless304` |
| bend_radius_min | Fictiv | Aluminum (alloy not named) | all | >= 1 x t | warning | `fictiv.bend.radius_min.al_unspecified` |
| bend_radius_min | Hubs (Protolabs Network) | * | all | >= 1 x t | warning | `hubs.bend.radius_min` |
| bend_radius_min | Xometry | * | all | >= 1 x t | warning | `xometry.bend.radius_min` |
| bend_radius_range | Protolabs | * | all | within 0.254 to 25.4 mm | warning | `protolabs.bend.radii_tooling` |
| bend_radius_options | Protolabs | * | all | in 0.762, 1.524, 2.286, 3.048 mm | info | `protolabs.bend.radii_standard` |
| bend_angle_max | SendCutSend | * | all | <= 130 deg | error | `sendcutsend.bend.angle_max` |
| bend_length_max | Protolabs | * | all | <= 1193.8 mm | error | `protolabs.bend.length_max` |
| bend_part_min_size | Protolabs | * | all | >= 12.7 x 12.7 mm | error | `protolabs.bend.part_min_formed` |
| relief_width_min | Fictiv | * | all | >= 1 x t, at least 0.762 mm | warning | `fictiv.bend.relief_width` |
| relief_width_min | Hubs (Protolabs Network) | * | all | >= 1 x t | warning | `hubs.bend.relief_width` |
| relief_width_min | SendCutSend | * | all | >= 0.5 x t | warning | `sendcutsend.bend.relief_width` |
| relief_width_min | Xometry | * | all | >= 1 x t | warning | `xometry.bend.relief` |
| relief_depth_min | Fictiv | * | all | >= 1.5 x t | warning | `fictiv.bend.relief_depth` |
| relief_depth_min | SendCutSend | * | all | >= 1 x t + r + 0.508 mm | warning | `sendcutsend.bend.relief_depth_formula` |
| pem_center_to_edge | Fictiv | * | all | >= 2.5 x d | warning | `fictiv.pem.edge` |
| pem_center_to_edge | Protolabs | * | all | info - | info | `protolabs.pem.edge_mfr` |
| tap_metric_range | OSH Cut | * | all | within 3 to 36 | error | `oshcut.tap.metric_range` |
| countersink_depth_max | SendCutSend | * | all | <= 0.6 x t | error | `sendcutsend.csk.depth_max` |
| countersink_thickness_min | OSH Cut | * | all | >= 18-gauge | warning | `oshcut.csk.min_gauge` |
| countersink_to_feature | Xometry | * | all | >= 8 x t | warning | `xometry.csk.feature_to_csk` |
| countersink_major_range | Protolabs | * | all | within 2.286 to 12.7 mm | warning | `protolabs.csk.major_range` |
| tolerance_cut | Fictiv | * | all | info 0.127 mm | info | `fictiv.cut.tolerance` |
| tolerance_cut | OSH Cut | * | all | info 0.127 mm | info | `oshcut.cut.tolerance` |
| tolerance_cut | Protolabs | * | all | info 0.127 mm | info | `protolabs.cut.tolerance` |
| tolerance_cut | SendCutSend | al5052 | all | info 0.127 mm | info | `sendcutsend.cut.tolerance` |
| tolerance_cut | Xometry | * | all | info 0.254 mm | info | `xometry.cut.tolerance` |
| tolerance_bend | Protolabs | * | 0-3.3 mm | info 0.25 mm | info | `protolabs.tol.hole_to_formed_thin` |
| tolerance_bend | Protolabs | * | 3.3-6.35 mm | info 0.508 mm | info | `protolabs.tol.hole_to_formed_thick` |
| tolerance_bend | SendCutSend | * | all | info 0.381 mm | info | `sendcutsend.bend.tolerance_edge` |
| tolerance_bend | Xometry | * | all | info ± .015″ Edge to bend | info | `xometry.bend.tolerance_A` |
| tolerance_bend | Xometry | * | all | info ± .015″ Bend to hole or internal cut feature | info | `xometry.bend.tolerance_D` |
| tolerance_bend | Xometry | * | all | info ± 1 Degree Bend angle | info | `xometry.bend.tolerance_F` |
| tolerance_bend_angle | Fictiv | * | all | info 0.5 to 1 | info | `fictiv.bend.tolerance_angle` |
| tolerance_bend_angle | OSH Cut | * | all | info 1 deg | info | `oshcut.bend.tolerance_angle` |
| tolerance_bend_angle | Protolabs | * | all | info 1 deg | info | `protolabs.bend.tolerance_angle` |
| tolerance_bend_angle | SendCutSend | * | all | info 1 deg | info | `sendcutsend.bend.tolerance_angle` |
| kerf | SendCutSend | * | all | info 0.152 to 0.305 mm | info | `sendcutsend.cut.common_line_gap` |
| kerf | Xometry | * | all | info 0.508 mm | info | `xometry.cut.kerf_laser` |
| kerf | Xometry | * | all | info 0.203 mm | info | `xometry.cut.kerf_sheetcut` |
| cnc_min_feature | Xometry | * | all | >= 0.5 mm | error | `xometry.cnc.min_feature` |
| cnc_min_wall | Protolabs | * | all | >= 0.51 mm | warning | `protolabs.cnc.feature_min` |
| cnc_min_nominal_thickness | Protolabs | * | all | >= 1.02 mm | error | `protolabs.cnc.nominal_thickness` |
| cnc_part_max_size | Protolabs | al* | all | <= 95.3 x 356 x 559 mm | error | `protolabs.cnc.part_max_al_3axis` |
| cnc_part_max_size | Protolabs | stainless304 | all | <= 82.55 x 95.25 x 107.95 mm | error | `protolabs.cnc.part_max_ss304_5axis` |
| cnc_part_max_size | Xometry | * | all | <= 610 x 1219 x 2032 mm | error | `xometry.cnc.part_max_milled` |
| cnc_thread_range | Protolabs | * | all | within 2 to 12 | error | `protolabs.cnc.threads` |
| cnc_mill_depth_max | Protolabs | * | all | <= 50.8 mm | error | `protolabs.cnc.mill_depth_max` |
| cnc_pocket_depth_ratio | Fictiv | * | all | <= 4 x tool diameter | warning | `fictiv.cnc.pocket_depth` |

### SendCutSend bending, per material and thickness

Bending calculator (K, radius, die width, minimum formed flange at 90 degrees, relief depth, corner relief distance) and processing min/max (max bend length, minimum flat blank). Features must be at least half the die width from the bend line (centre of the bend, flat pattern). SendCutSend lists no bending of 6061 or MIC-6.

| material | thickness | K | inside radius mm | die width / 2 mm | min formed flange mm | relief depth mm | corner relief mm | max bend length mm | min flat blank mm |
|---|---|---|---|---|---|---|---|---|---|
| al5052 | .040″ | 0.45 | 0.61 | 5.995 | 7.264 | 2.134 | 0.61 | 1117.6 | 9.525 x 38.1 |
| al5052 | .063″ | 0.42 | 0.889 | 5.995 | 7.696 | 2.997 | 0.762 | 1117.6 | 9.525 x 38.1 |
| al5052 | .080″ | 0.48 | 0.965 (min/max page: 1.143) | 5.995 | 7.95 | 3.505 | 0.94 | 1117.6 | 9.525 x 38.1 |
| al5052 | .090″ | 0.37 | 0.813 | 5.995 | 8.28 | 3.607 | 0.864 | 1117.6 | 9.525 x 38.1 |
| al5052 | .100″ | 0.4 | 3.175 | 8.001 | 11.76 | 6.223 | 0.508 | 1117.6 | 9.525 x 38.1 |
| al5052 | .125″ | 0.44 | 3.175 | 8.001 | 12.09 | 6.858 | 0.813 | 1117.6 | 9.525 x 38.1 |
| al5052 | .187″ | 0.43 | 6.35 | 12.497 | 20.269 | 11.608 | 0.61 | 1117.6 | 9.525 x 38.1 |
| al5052 | .250″ | 0.42 | 6.35 | 20.003 | 34.823 | 13.208 | 1.118 | 1117.6 | 9.525 x 63.5 |
| al5052 | .375″ | not bent | | | | | | | |
| al5052 | .500″ | not bent | | | | | | | |
| stainless304 | .030″ | 0.36 | 2.032 | 5.995 | 7.468 | 3.302 | 0.152 | 1117.6 | 9.525 x 38.1 |
| stainless304 | .048″ | 0.36 | 2.032 | 5.995 | 7.798 | 3.759 | 0.279 | 1117.6 | 9.525 x 38.1 |
| stainless304 | .060″ | 0.34 | 1.778 | 5.995 | 7.976 | 3.81 | 0.406 | 1117.6 | 9.525 x 38.1 |
| stainless304 | .074″ | 0.36 | 1.905 | 5.995 | 8.23 | 4.293 | 0.533 | 1117.6 | 9.525 x 38.1 |
| stainless304 | .100″ | 0.36 | 4.75 | 12.497 | 18.593 | 7.798 | 0.102 | 889.0 | 9.525 x 38.1 |
| stainless304 | .125″ | 0.38 | 3.81 | 12.497 | 18.796 | 7.493 | 0.508 | 1016.0 | 9.525 x 38.1 |
| stainless304 | .187″ | 0.35 | 3.302 | 12.497 | 19.914 | 8.56 | 0.965 | 914.4 | 9.525 x 38.1 |
| stainless304 | .250″ | 0.34 | 5.715 | 20.003 | 35.077 | 12.573 | 0.864 | 457.2 | 9.525 x 63.5 |
| stainless304 | .375″ | not bent | | | | | | | |
| stainless304 | .500″ | not bent | | | | | | | |
| steel | .030″ | 0.38 | 1.143 | 5.995 | 7.264 | 2.413 | 0.381 | 1117.6 | 9.525 x 38.1 |
| steel | .048″ | 0.38 | 1.143 | 5.995 | 7.569 | 2.87 | 0.508 | 1117.6 | 9.525 x 38.1 |
| steel | .059″ | 0.4 | 1.6 | 5.995 | 7.849 | 3.607 | 0.508 | 1117.6 | 9.525 x 38.1 |
| steel | .074″ | 0.4 | 1.6 | 5.995 | 8.128 | 3.988 | 0.635 | 1117.6 | 9.525 x 38.1 |
| steel | .104″ | 0.34 | 1.6 | 8.001 | 11.659 | 4.75 | 0.711 | 1117.6 | 9.525 x 38.1 |
| steel | .119″ | 0.38 | 1.6 | 8.001 | 11.836 | 5.131 | 0.914 | 1117.6 | 9.525 x 38.1 |
| steel | .135″ | 0.32 | 2.54 | 12.497 | 18.847 | 6.477 | 0.711 | 1117.6 | 9.525 x 38.1 |
| steel | .187″ | 0.36 | 3.175 | 12.497 | 19.837 | 8.433 | 1.041 | 558.8 | 9.525 x 38.1 |
| steel | .250″ | 0.36 | 3.81 | 20.003 | 34.569 | 10.668 | 1.372 | 508.0 | 9.525 x 63.5 |
| steel | .313″ | not bent | | | | | | | |
| steel | .375″ | not bent | | | | | | | |
| steel | .500″ | not bent | | | | | | | |

### SendCutSend hardware catalog (metric self-clinching nuts)

| SKU | thread | hole in sheet | min sheet | max sheet | aluminium range | C/L to edge or bend | C/L to C/L |
|---|---|---|---|---|---|---|---|
| F-M2.5-1 | M2.5 | 4.369 mm | 1.499 mm | 2.286 mm | "0.63″-0.090″" as published (inverted; not evaluated) | 5.994 mm | 8.179 mm |
| F-M2.5-2 | M2.5 | 4.369 mm | 2.286 mm | - | 2.286 to 12.7 mm | 5.994 mm | 8.179 mm |
| F-M3-1 | M3 | 4.369 mm | 1.499 mm | 2.286 mm | "0.63″-0.090″" as published (inverted; not evaluated) | 5.994 mm | 8.179 mm |
| F-M3-2 | M3 | 4.369 mm | 2.286 mm | - | 2.286 to 12.7 mm | 5.994 mm | 8.179 mm |
| F-M4-1 | M4 | 7.366 mm | 1.499 mm | 2.286 mm | "0.63″-0.090″" as published (inverted; not evaluated) | 7.188 mm | 10.871 mm |
| F-M4-2 | M4 | 7.366 mm | 2.286 mm | - | 2.286 to 12.7 mm | 7.188 mm | 10.871 mm |
| F-M5-1 | M5 | 7.925 mm | 1.499 mm | 2.286 mm | "0.63″-0.090″" as published (inverted; not evaluated) | 8.001 mm | 11.963 mm |
| F-M5-2 | M5 | 7.925 mm | 2.286 mm | - | 2.286 to 12.7 mm | 8.001 mm | 11.963 mm |
| F-M6-3 | M6 | 8.738 mm | 3.023 mm | 3.962 mm | - | 8.382 mm | 12.751 mm |
| F-M6-4 | M6 | 8.738 mm | 3.835 mm | 4.75 mm | - | 8.382 mm | 12.751 mm |
| F-M6-5 | M6 | 8.738 mm | 3.023 mm | - | - | 8.382 mm | 12.751 mm |
| S-M3-0 | M3 | 4.267 mm | 0.787 mm | - | 1.016 to 12.7 mm | 6.35 mm | 8.534 mm |
| S-M4-0 | M4 | 5.385 mm | 0.787 mm | - | 1.016 to 12.7 mm | 6.909 mm | 9.627 mm |
| S-M6-0 | M6 | 8.763 mm | 1.219 mm | - | 1.6 to 12.7 mm | 8.611 mm | 13.03 mm |
| S-M8-1 | M8 | 10.49 mm | 1.397 mm | - | 1.6 to 12.7 mm | 9.703 mm | - |
| SP-M3-0 | M3 | 4.216 mm | 0.787 mm | - | - | 7.95 mm | 12.725 mm |
| SP-M4-0 | M4 | 5.41 mm | 0.787 mm | - | - | 7.95 mm | 14.834 mm |
| SP-M5-0 | M5 | 6.35 mm | 0.787 mm | - | - | 7.95 mm | 15.037 mm |
| SP-M6-1 | M6 | 8.738 mm | 1.524 mm | - | - | 9.525 mm | 18.136 mm |
| SP-M8-1 | M8 | 10.49 mm | 1.397 mm | - | - | 9.703 mm | 19.228 mm |

### SendCutSend tapping and countersinking, per material and thickness

From the processing min/max page. "no row": the material is absent from the countersinking table (not offered).

| material | thickness | metric taps | countersink |
|---|---|---|---|
| al5052 | .040″ | no | no |
| al5052 | .063″ | M2 to M4 | no |
| al5052 | .080″ | M2 to M6 | no |
| al5052 | .090″ | M2 to M6 | no |
| al5052 | .100″ | M2 to M6 | no |
| al5052 | .125″ | M2 to M10 | minor >= 2.515, major <= 10.846 mm |
| al5052 | .187″ | M3 to M10 | minor >= 2.515, major <= 13.487 mm |
| al5052 | .250″ | M3 to M10 | minor >= 2.515, major <= 16.662 mm |
| al5052 | .313″ | M5 to M10 | minor >= 3.302, major <= 16.662 mm |
| al5052 | .375″ | M5 to M10 | minor >= 3.302, major <= 16.662 mm |
| al5052 | .500″ | M5 to M10 | minor >= 4.902, major <= 16.662 mm |
| al6061 | .040″ | no | no |
| al6061 | .063″ | M2 to M6 | no |
| al6061 | .080″ | M2 to M6 | no |
| al6061 | .100″ | M2 to M6 | no row |
| al6061 | .125″ | M2 to M10 | minor >= 2.515, major <= 11.989 mm |
| al6061 | .187″ | M3 to M10 | minor >= 2.515, major <= 13.487 mm |
| al6061 | .250″ | M3 to M10 | minor >= 2.515, major <= 13.487 mm |
| al6061 | .313″ | M3 to M10 | minor >= 2.515, major <= 16.662 mm |
| al6061 | .375″ | M5 to M10 | minor >= 3.302, major <= 16.662 mm |
| al6061 | .500″ | M5 to M10 | minor >= 4.902, major <= 16.662 mm |
| al6061 | .625″ | M8 to M10 | minor >= 4.902, major <= 16.662 mm |
| al6061 | .750″ | M8 to M16 | minor >= 6.477, major <= 16.662 mm |
| stainless304 | .030″ | no | no row |
| stainless304 | .048″ | no | no row |
| stainless304 | .060″ | M2 to M6 | no row |
| stainless304 | .074″ | M2 to M6 | no row |
| stainless304 | .100″ | M2 to M6 | no row |
| stainless304 | .125″ | M2 to M10 | no row |
| stainless304 | .187″ | M3 to M10 | no row |
| stainless304 | .250″ | M4 to M10 | no row |
| stainless304 | .375″ | M6 to M10 | no row |
| stainless304 | .500″ | M6 to M10 | no row |
| steel | .030″ | no | no row |
| steel | .048″ | no | no row |
| steel | .059″ | M2 to M3 | no row |
| steel | .074″ | M2 to M6 | no row |
| steel | .104″ | M2 to M6 | no row |
| steel | .119″ | M2 to M8 | no row |
| steel | .135″ | M2 to M10 | no row |
| steel | .187″ | M2 to M10 | no row |
| steel | .250 | M2 to M10 | no row |
| steel | .313″ | M4 to M10 | no row |
| steel | .375″ | M6 to M10 | no row |
| steel | .500″ | M6 to M10 | no row |
