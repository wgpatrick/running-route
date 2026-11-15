# Vendor data behind the parts catalog

Geometry: the catalog parts now also carry vendor / community CAD (STEP) as a `detail` model, and the simulation
solids were checked against it and corrected: see `docs/VENDOR_CAD.md` (NEMA 17 connector, idler flange 18 mm,
T8 nut stub, bracket width 17, SKR component height 14.2, LRS terminal strip 9.5 mm off centre, lever endstop).

Retrieved 2026-11-14. Recorded values live in `mechloop/parts/vendor/*.json` (one file per
part family; every value has a `source_url`, document title and page/table reference).
Small source documents are stored in `vendor_docs/`. `tests/test_vendor.py` checks that the
catalog parts equal the recorded files.

Each catalog `Stock` now has `verified` and `source`. `source["level"]` is one of:

| level | meaning | counts as vendor-backed |
|---|---|---|
| `vendor` | read from the vendor's own datasheet, drawing or product page | yes |
| `standard` | a dimension standard, read from a published table of it | yes |
| `secondary` | third-party transcription of vendor data; vendor document not reached | no |
| `partial` | only some fields confirmed | no |
| `proxy` / empty | nothing fetched; typical class values | no |

`place()` copies this into `meta["vendor_backed"]` and `meta["source"]`, and every part's
ratings carry a `source` string. The ratings verifier's `approximate_ratings` message now names
only the part types that are not vendor-backed, and reports both lists in
`metrics["vendor_backed_parts"]` / `metrics["unverified_parts"]`.

## What is vendor-backed now

| Part | Source | Old → new |
|---|---|---|
| `nema17(34)` = StepperOnline 17HS13-0404S | datasheet drawing `omc-stepperonline.com/download/17HS13-0404S.pdf`; mass from product page; curve from `..._Torque_Curve.pdf` | mass 0.22 → 0.23 kg; holding 260 → 260 N·mm; inertia 38 → 35 g·cm²; shaft above face 24 → 20 mm; max rpm 1800 → 1320 |
| `nema17(40)` = 17HS16-2004S1 | same set of documents for this part | mass 0.28 → 0.31 kg; holding 400 → 450 N·mm; inertia 54 → 54; shaft 24 → 23 mm; max rpm 1800 → 525 |
| `nema17(48)` = 17HS19-2004S1 | same | mass 0.36 → 0.39 kg; holding 520 → 590 N·mm; inertia 68 → 82; shaft 24 → 24 mm; max rpm 1800 → 750 |
| `nema17(60)` = 17HS24-2104S | same | mass 0.50 → 0.50 kg; holding 650 → 650 N·mm; inertia 102 → 148; max rpm 1800 → 525 |
| all four motors | | generic torque-speed fractions → published 24 V pull-out curve; new ratings `rated_current_a`, `phase_resistance_ohm`, `phase_inductance_mh` |
| `psu_24v(150)` = MEAN WELL LRS-150-24 | `meanwell.com/Upload/PDF/LRS-150/LRS-150-SPEC.PDF` p.2, p.4 | size 159×97×30 unchanged; mass 0.48 → 0.42 kg; base holes 2×M4 at (±60, −32.5) → 2×M3 at (−55.5, −16.5), (22.5, −16.5), 3 mm max screw depth; adds 6.5 A, 156 W, 89 %, inrush 60 A |
| `psu_24v(200)` = LRS-200-24 | `.../LRS-200/LRS-200-SPEC.PDF` | 159×97×30 proxy → 215×115×30; 0.48 → 0.66 kg; 4×M4 at (±75, ±25); 8.8 A, 211.2 W, 89.5 % |
| `psu_24v(350)` = LRS-350-24 | `.../LRS-350/LRS-350-SPEC.PDF` | 159×97×30 proxy → 215×115×30; 0.48 → 0.76 kg; 4×M4 at (±75, ±25); 14.6 A, 350.4 W, 88 % |
| `control_board()` = BIGTREETECH SKR Mini E3 V3.0 | BTT GitHub repo: SIZE drawing, PIN drawing, schematic, user manual | 110×85 → 103.75×70.25 mm; 4 holes on a ±51 × ±38.5 rectangle → 5 holes, not a rectangle; stepper drivers 5 → 4 (TMC2209; the Z driver has two connectors); adds sense resistor 0.11 Ω, main fuse 20 A |
| `shaft_coupler(5, 8)` = StepperOnline MH2025-5-8 | product page | OD 19 → 20 mm; mass 16 → 17 g; rated torque 1500 → 2800 N·mm; adds max torque, max rpm, torsional stiffness, inertia |
| `shcs()`, `hex_nut()` | ISO 4762 / ISO 4032 tables in FreeCAD Fasteners Workbench `FsData/*.csv` | head diameter, head height, socket size, across-flats and nut height all already equal to the tables: no change |

Notes on the motor data:

- The datasheets are image-only PDFs; table values were read from the rendered page.
- Torque curve points were read by eye from the plotted markers (about ±0.5 N·cm; speeds sit on gridlines).
- Below the first published speed the first point is used. The 2 A half-step curves start low
  (17HS19: 30 N·cm at 60 rpm, 43 at 90 rpm), so low-speed torque is lower than the old model gave.
- `max_rpm` is where the published curve ends, not a stated motor limit. A design that needs more
  will get `motor_overspeed`.
- The 17HS13-0404S curve was measured at 0.35 A RMS on a DM320T at 24 V, 1600 microsteps.
- Product page and datasheet disagree in three places; the datasheet value is used:
  17HS19 resistance (page 1.6 Ω, drawing 1.40 Ω), 17HS24 holding torque (page text 76 N·cm,
  drawing 0.65 N·m), 17HS16 body length (page 40, drawing 39 ± 1).
- Body length in the geometry is the catalog argument (34/40/48/60), which is the drawing's maximum.

Still assumed on vendor-backed parts (listed in each part's `source["unverified_fields"]`):

- Control board: mass 0.11 kg, hole diameter, heater/bed/fan channel current limits. Height is now 15.8 mm from the
  vendor STEP (was an 18 mm allowance); the vendor STEP does not show the SIZE drawing's five mounting holes
  (`docs/VENDOR_CAD.md`).
- PSU: mass is the per-unit weight from the PACKING row. For LRS-150 the drawing does not say which
  long edge the 32 mm hole offset is measured from in the catalog's frame; the edge at the bottom of
  the datasheet top view was taken as −Y.
- Screws: proof loads (class 12.9), clearance holes and tap drills are the previous values.

## Recorded but not vendor-backed

| Part | What was found | Old → new | Status |
|---|---|---|---|
| `mgn12h_carriage()`, `mgn12_rail()` | Two independent third-party transcriptions of the Hiwin MG table that agree (`basecase/src/data/motionTables.ts`; `open-dolly` research notes quoting a distributor) | dynamic load 4700 → 3720 N; static load 5880 → 5880 N; static moment 36.0 → 36.26 N·m (min of MR 38.22, MP 36.26, MY 36.26); all block and rail dimensions, 54 g and 0.65 kg/m unchanged | `secondary`, ratings keep `approximate` |
| `leadscrew_t8(lead=8)` | StepperOnline LSN-S-MB-320 page: stainless, Ø8, lead 8 | no change | `partial`; efficiency 0.5 is typical, unverified |
| `extrusion_2020()` | Community DXF of the HFS5-2020 section, integrated numerically: area 182 mm², Ixx = Iyy = 7419 mm⁴, slot opening 6.0 mm, 0.49 kg/m at an assumed 2700 kg/m³ | not applied: catalog keeps Ixx 6900, slot 6.2, 0.45 kg/m | `proxy` |

The secondary table also gives the carriage's tapped holes as M3 × 3.5 mm deep. It is exposed as
`interfaces["thread_depth_unverified"]` and does not drive the `thread_bottoms_out` check. If
confirmed against the Hiwin catalogue and renamed to `thread_depth`, these screws are 0.5 mm too long:
`z_carriage_left_screw_0..3` and `z_carriage_right_screw_0..3` in `designs/printer_v3.py`, and
`tool_screw_0..3` in `examples/gantry.py` (each goes 4.0 mm into the block).

Recorded for the electrical work only (not used by the catalog functions here):

- `bigtreetech_skr_mini_e3_v3.json`: connector list, pin names, fuses (F1 20 A/32 V, F2 1.1 A/16 V),
  MOSFET part numbers (bed WSK220N04, hotend WSF3085, fans PL4009), sense resistors 0.11 Ω.
- `trinamic_tmc2209.json`: 2 A RMS, 2.8 A peak, 4.75–28 V, from the BIGTREETECH TMC2209 V1.2
  module manual, not the IC datasheet.
- `e3d_v6.json`: 300 °C maximum with the supplied thermistor, 30 W heater cartridge in 12 V or 24 V,
  30×30×10 fan, from the E3D product page.

## Could not be sourced

| Wanted | Why not | Catalog state |
|---|---|---|
| Hiwin catalogue: C/H/P running parallelism vs length, allowable mounting error e1, preload, tolerances | `www.hiwin.tw` no longer serves the catalogue PDF and its product pages have no tables; `www.hiwin.com` answers 403 to automated requests; the Hiwin support site is not reachable | tolerance check keeps its 0.025 mm default; typical, unverified |
| Gates GT2 belt: stiffness, working tension, minimum pulley teeth | `www.gates.com` answers 403 on product pages; no mirror found | pulleys and idlers unchanged; typical, unverified |
| TMC2209 IC datasheet: RDSon, absolute maxima | `www.analog.com` is refused by the proxy; `www.trinamic.com` drops the transfer; GitHub mirrors are Git-LFS pointers | module-manual values only |
| Misumi HFS5-2020 section properties and length tolerance | `us.misumi-ec.com` is refused by the proxy | unchanged; typical, unverified |
| T8 brass nut dimensions, screw efficiency, anything for lead 2 mm | StepperOnline pages give no dimensions; their datasheet host is not reachable | unchanged; typical, unverified |
| E3D V6 dimensions, mass, thermistor type | product page has no dimension table | `extruder_direct()` unchanged |
| SKR Mini E3 V3 heater/bed/fan current limits, mass, height | vendor documents give MOSFET part numbers only | recorded as `null` |
| ISO 898-1 proof loads, ISO 273 clearance holes | no table on a reachable host | previous values kept; typical, unverified |
| LRS-250 | MEAN WELL makes no such model | `psu_24v(250)` (used by printer v3) stays the 159×97×30 proxy |
| Bearings, linear rod, couplers with other bores | not attempted or nothing found | unchanged; typical, unverified |
| Endstop, fans, corner bracket | community CAD only (`docs/VENDOR_CAD.md`); no vendor document | geometry checked against community CAD; ratings typical, unverified |

## Effect on the existing designs

Run: `mechloop verify <design> --no-render --only geometry interference tolerance ratings subsystems`.

`designs/printer_v3.py` — one new error:

- `control_board`, `subsystems` / `not_enough_drivers`: "5 motors (including the extruder) but the
  control board drives 4." The SKR Mini E3 V3.0 has four drivers; the design has X, two Y motors, Z and
  the extruder.

No new geometry, interference or tolerance findings in either design. Drive numbers moved:

| Design, joint | Motor | Torque at speed, old → new (N·mm) | Available force, old → new (N) |
|---|---|---|---|
| printer_v3 x | 34 mm, 375 rpm | 195 → 104 | 29.1 → 15.5 |
| printer_v3 z | 34 mm, 360 rpm | 197.6 → 108 | 217.3 → 118.7 |
| printer_v3 y | 2 × 48 mm, 375 rpm | 780 → 800 | 116.4 → 119.4 |
| gantry x | 40 mm, 450 rpm | 280 → 290 | 41.8 → 43.3 |
| gantry y | 48 mm, 450 rpm | 364 → 390 | 54.3 → 58.2 |

The 34 mm motor is the 0.4 A 17HS13-0404S, whose published torque falls quickly with speed. The motion
verifier was not run here; printer v3's X and Z force margins should be rechecked with it.

`examples/gantry.py` fails before and after with the same five errors (two `screws_may_not_align`,
`rails_not_parallel`, two `no_cable_to_moving_electrics`); nothing new.

---

# Parts added for printer_v6 (retrieved 2026-11-15)

printer_v5 carried 27 `uncatalogued_cots` warnings: 20 bought spacers, 4 silicone bed columns, the hotend, the bed probe
(the fans were already catalogue parts). These are now catalogue parts, except the probe (added separately).
Code: `mechloop/parts/toolhead.py`, `mechloop/parts/hardware.py`. Tests: `tests/test_vendor.py` (from
"parts added for printer_v6").

## Network reach this time

Reachable: `e3d-online.com` (product data, support pages and, through `e3d-online.com/cdn/shop/files/...`, the
drawings on E3D's CDN), `www.pololu.com`, `raw.githubusercontent.com` and git over HTTPS to github.com, plus the hosts
used on 2026-11-14. Refused by the session's network policy (CONNECT 403 / no DNS): `www.orbiterprojects.com`,
`ldomotors.com`, `docs.ldomotors.com`, `www.bondtech.se`, `www.printables.com`, `cdn.shopify.com`, `www.gates.com`
(HTTP 403 from the site), `www.keyelco.com`, `www.essentracomponents.com`, `www.mcmaster.com`,
`openbuildspartstore.com`, `www.fysetc.com`, `www.matweb.com`, `www.alcoa.com`, `www.arconic.com`,
`www.kaiseraluminum.com`, `www.vistametalsinc.com`, `www.upmet.com`, `en.wikipedia.org`, `www.schott.com`,
`www.littelfuse.com`, `www.slice.engineering`, `www.phaetus.com`, `www.sunon.com`, and every distributor tried
(digikey, mouser, rs-online, farnell, tme, lcsc, misumi). Where a maker's site could not be read, web-search result
snippets were used and the entry is `secondary` (not vendor-backed), or the value is recalled and listed as such.

## The extruder: comparison and choice

Wanted: a direct-drive extruder for a toolhead of about 0.40 kg, 24 V, Klipper, TMC2209 on the SKR Mini E3 V3,
1.75 mm filament.

| | E3D Roto (chosen) | LDO Orbiter v2.0 | Annex Sherpa Mini | Bondtech LGX Lite | E3D Hemera XS |
|---|---|---|---|---|---|
| Mass with motor | **140 g, heat sink and fan included; 157 g with hot side and nozzle** | about 140 g, no hotend | 115-136 g by kit, no hotend | 141 g, no hotend | motor alone 160 g |
| Gear ratio | 11.262:1 | 7.5:1 | 50:8 / 50:10 | 44:10 x 37:17 | not on the page |
| Rotation distance | 26.8937 per hobb turn (2.388 per motor turn), 0.9 deg motor | 4.637 (recalled) | 22.68 with gear ratio (recalled) | 55 with gear ratio, or 5.7 | 397 steps/mm at 16x |
| Motor current | 0.318-0.424 A rms (0.45-0.6 A peak) | 1.0 A rated | 1.0 A rated | 0.45-0.60 A recommended | 0.99 A rms |
| Motor R / L / torque | 7.5 ohm / **not published** / 75 mNm, rotor 7 gcm2 | not reached | not reached | not reached | 2.3 ohm / - / 180 mNm |
| Extrusion force | 70 N+ | 9.4 kg (snippet) | - | - | - |
| Mounting | 2 x 3.3 mm holes, dimensioned drawing | not reached | printed housing | not reached | T-slot faces |
| Nozzle position | dimensioned to the mounting holes | - | - | - | drawing on the page |
| Hotend | Revo, built in | separate | separate | separate | Revo, built in |
| Source reached | **E3D data-sheet page and drawing** | reseller snippets only | reseller snippets only | maker's page via snippets only | E3D data-sheet page |
| Real CAD | Printables only (not reachable): wish list | not reached | STEP on GitHub (reachable) | not reached | not looked for |

Chosen: **E3D Roto** (`extruder_roto()`), with the Revo hot side (`hotend_revo()`).

- Lightest complete answer: 157 g for extruder, motor, heat sink, heat-sink fan, heater, sensor and nozzle. Each
  alternative is about 140 g before a hotend (a V6 adds about 65 g and a fan).
- The only candidate whose maker's own data could be read: mass, gearing, steps/mm, current limits, winding
  resistance, holding torque, rotor inertia, service temperatures, a dimensioned drawing with the mounting holes and the
  nozzle tip, and a Klipper block.
- Its low current (0.32-0.42 A rms) is easy for the board's TMC2209 and for a thin toolhead loom.
- Costs to accept: the heat-sink fan is **5 V** (0.14 A): on this 24 V machine it needs E3D's regulator board
  (REVO-MICRO-BOARD-REG) or the board's 5 V rail; the motor is **0.9 degree** (400 steps), so the Klipper block needs
  `full_steps_per_rotation: 400`; winding **inductance is not published** (11 mH is this catalogue's estimate, flagged);
  ambient limit 40 degC with PLA (no heated chamber); nozzles are Revo only.

Key figures of the catalogue entry, all from
`https://e3d-online.com/pages/revo-support-roto-standard-sensored` (copy: `vendor_docs/E3D_revo-support-roto-standard-sensored.txt`)
unless said otherwise:

| Figure | Value | Source / status |
|---|---|---|
| Part number | REVO-ROTO-COLDSIDE-AS | E3D shop data, variant "Standard" |
| Mass | 0.140 kg; 0.157 kg with hot side and nozzle | "Summary" |
| Gear ratio, rotation distance | 11.262:1; 26.8937 mm; 2682 steps/mm at 16x | "Summary" |
| Motor | NEMA 14, 0.9 deg, 50 g, 7.5 ohm +/-10 %, 75 mNm holding, 5 mNm detent, rotor 7 gcm2, 4.5 V rated | "Motor Specification" |
| Current | 0.45 A peak (0.318 rms) minimum recommended, 0.6 A peak (0.424 rms) maximum | "Summary" |
| Inductance | 11 mH | **estimate** (7.5 ohm x 1.5 ms), not published |
| Motor connector | Molex 43025-0400 (Micro-Fit 3.0, 4-way) | wiring image on the page |
| Fan | 35 x 35 x 7, 5 V, 0.14 A, 7 g | "Fan Specification"; size from the spare-part SKU |
| Mounting | 2 x dia 3.3 +/-0.08 holes at (0, 0) and (6.8, 30.5) | drawing `vendor_docs/E3D_Roto_Dim.svg` |
| Nozzle tip | (-9.05 +/-0.26, -33.55 +0.46/-0.36) from the lower hole; 15.18 +/-0.41 from one side face of the 38.5 width | same drawing |
| Envelope | X -25.25..31.85, Z -11.45..44.15, width 38.5 | same drawing (reference dimensions) |
| Body top, motor, fan, lever, ears | boxes | **scaled from the drawing, +/-1 mm** |
| Side of the 4.07 mm lateral nozzle offset | -Y | **assumed** from the view layout |

**E3D's Klipper block is inconsistent with its own summary.** It prints `rotation_distance: 26.8937`,
`full_steps_per_rotation: 400`, `microsteps: 16` and no `gear_ratio`. That is 238 steps/mm; the summary says 2682.
The figures agree only if 26.8937 is per turn of the hobb: 26.8937 / 11.262 = 2.388 mm per motor turn, 6400 / 2.388 =
2680 steps/mm. The catalogue records 26.8937 with `gear_ratio 11.262:1` and 400 steps, and gives
`rotation_distance_200_steps_no_gear_ratio` = 1.194 for a config writer that can emit only `rotation_distance`
(`mechloop/electrical.py` today). Confirm on the machine with a 100 mm extrusion test.

How the catalogue exposes it (same places as the old `extruder_direct()` plus the new data):

- `ratings["electrical"]`: a `stepper` template (`device_from(el, d, "extruder")` uses it directly; nothing in
  `mechloop/parts/electrical.py` had to change). Ratings `rated_current_a` 0.424 (rms, the unit of `run_current`),
  `phase_resistance_ohm`, `phase_inductance_mh` (estimate), `holding_torque_nmm`; params `rotation_distance`,
  `gear_ratio`, `full_steps_per_rotation`, `run_current` 0.45 (E3D's block).
- `ratings["rotation_distance"]`, `["gear_ratio"]`, `["full_steps_per_rotation"]`, `["rotation_distance_per_motor_rev"]`,
  `["rotation_distance_200_steps_no_gear_ratio"]`, `["fan"]`.
- `interfaces`: `mount_holes_m3` (two points on the hole axes at mid-width), `mount_hole_axis` (0, 1, 0),
  `filament_axis` (two points), `filament_entry`, `hotend_seat` (= `filament_exit`), `nozzle_tip`, `lever_top`, `port:coils`.

Hooks needed outside `mechloop/parts/` (not edited here):

1. `mechloop/electrical.py`, `[extruder]` writer: emit `full_steps_per_rotation` and `gear_ratio` when the firmware
   entry (or the motor device's params) has them. Until then use `rotation_distance: 1.194` in the design's firmware
   dict.
2. The same file's heater plant is constant-power. The Revo heater is PTC: use
   `P(T) = V^2 / (r_ohm_23c * (1 + tempco_per_c * (T - 23)))` from the heater device's `params["ptc"]` (or
   `ratings["resistance_ohm_23c"]`, `["resistance_tempco_per_c"]`). With it, the stuck-MOSFET fault settles lower
   than a 40 W constant source would.
3. A 5 V fan: the fan output must switch the 5 V rail (regulator board in the BOM), not 24 V.
4. Tables keyed by material name do not know `al_mic6` / `al_atp5`: `ALPHA` in `verifiers/fea.py` (23.6e-6),
   `MACHINING` in `verifiers/dfm_rules.py` (as al6061), `THREAD_FACTOR` in `verifiers/interference.py` (1.5 or more:
   cast plate is soft, 2.0 is safer), the earth-bond material list in `verifiers/electrical.py`.

## What is vendor-backed now (added)

| Part | Source | Vendor-verified | Recalled / estimated / scaled |
|---|---|---|---|
| `extruder_roto()` = E3D REVO-ROTO-COLDSIDE-AS | E3D Roto data-sheet page and drawing | table above | inductance; outlines scaled from the drawing; side of the lateral offset; hole depth; cost |
| `hotend_revo(40, 24.0, 0.4)` = E3D RC-CORE-24V-AS-SPRING + RC-NOZZLE-0400-AS-SPK | `e3d-online.com/pages/revo-support-40w-104nt-heatercore`, `.../revo-support-brass-nozzle`, nozzle drawing | 40 W; 14.4 ohm at 23 degC; temperature coefficient 0.002078 /degC (27.2 W at 250 degC); max 300 degC; Klipper sensor "ATC Semitec 104NT-4-R025H42G"; Micro-Fit connectors; nozzle 8 g, 41.1 long, 22.8 +/-0.2 seat to tip, 13 mm block | HeaterCore 16.3 dia x 11.9 (scaled from its drawing); HeaterCore mass 9 g (157 - 140 - 8); thermal capacity 6.5 J/K and area (estimates); sensor response 2 s |
| `hotend_v6()` = E3D V6-175-24V | `e3d-online.com/pages/e3d-classics-support-v6-hotend` and its dimension drawing | 62.55 mm tip to heat-sink top, groove mount 16 / 12 / 16 mm (3.0, 6.0, 3.7 high), heat-sink radius 11.15, block bottom 4.8 above the tip; 300 degC rated, 285 with E3D thermistor, 260 with sock; 30 W heater, 24 V 30 W resistance 16.7-22.6 ohm; Semitec 104NT-4-R025H42G | mass 65 g (recalled); heater block 23 x 16 x 11.5 and bore positions (community model) |
| `spacer_round("M3", L)` nylon, 5 OD x 3.3 ID, L in 2, 4, 6, 8, 10, 12, 15, 20, 25 | Pololu items 1980-1988 (`pololu.com/category/93/spacers`, item 1982 page) | OD, ID, length, item number, pack size | mass (from volume), nylon grade |
| `spacer_round("M2.5", L)` nylon, 4 OD x 2.7 ID, L in 2, 4, 6, 8, 10, 12, 15, 20, 22, 25 | Pololu items 1970-1979 | same | same |

## Recorded but not vendor-backed (added)

| Part | What was found | Status |
|---|---|---|
| `spacer_round("M5", L, "aluminium")`, 10 OD x 5.1 ID | OpenBuilds "Aluminum Spacers": M5 ID, 10 mm OD, 10-pack; 3 mm, 6 mm and 13.2 mm seen; 5.1 mm ID from a reseller. Search snippets only | `secondary`; no SKU; other lengths recalled |
| `spacer_round` in any other size / material (`M3` aluminium 6 x 3.2, `M4` 8 x 4.3, `M5` nylon 10 x 5.3) or a non-stock length | nothing | usual sizes, no part number, "typical, unverified" (`partial` for an off-list length of a Pololu size) |
| `bed_column_silicone(18.0 or 16.2, installed=None)` | reseller listings (FYSETC "solid bed mounts" and one more): OD 16, bore 4, 18 high / 16.2 short; "200 degC" seller claim. Snippets only | `secondary`; no stiffness or hardness. printer_v5's proxy was 12 OD x 20: that size was not found anywhere |
| `MATERIALS["al_mic6"]` 2800 kg/m3, 71 GPa, 0.33, yield 105 MPa | distributor data in snippets: yield 15 ksi, tensile 24 ksi, Brinell 65, expansion 13.1 uin/in-degF (23.6e-6 /K) | density and modulus recalled (0.101 lb/in3, 10.3 Msi) |
| `MATERIALS["al_atp5"]` 2660 kg/m3, 70.3 GPa, 0.33, yield 124 MPa | snippets: cast 5083-type, about 5 % lighter than MIC-6 | every number recalled |
| `gt2_pulley(t, bore, 9)`, `gt2_idler(t, bore, 9)` | nothing from Gates. The functions always took a belt width (geometry and `belt_center` follow it; `Belt.width` drives the twin's belt stiffness), but the SKU did not carry it | SKU and rating now carry the width for new widths: `GT2-20T-B5-W9`, `belt_width_mm`. 6 and 12 mm keep their old names so printer_v4 / v5 BOMs do not change. Still "typical, unverified" |

`fan(30)` / `fan(40)` were not proxies in printer_v5 (community CAD, typical ratings): left as they are. E3D lists a
30 x 30 x 10 24 V fan (E-FAN-30-30-10-24V-BK) with no data on its page.

## The hotend's hardware over-temperature cut-off

The electrical verifier's open warning stands: **no off-the-shelf product that closes it was found.**

- No hotend on a reachable site has a built-in one-shot cut-off. E3D's Revo HeaterCore has the nearest real feature: a
  PTC winding ("power reduces as it gets hotter, reducing hazards in the event of a thermal runaway"). From E3D's
  figures: 40 W at 23 degC, 27.2 W at 250 degC, 25.4 W at 300 degC, about 21.2 W at 450 degC (extrapolated past E3D's
  graph, which ends at 300 degC). It limits a stuck-on heater; it does not switch it off. Recorded in
  `hotend_revo().ratings["electrical"]` (`resistance_ohm_23c`, `resistance_tempco_per_c`, `power_w_at_c`).
- Axial thermal cut-offs of the kind already in the catalogue (`thermal_fuse`) stop at about 240 degC functioning
  temperature (recalled; schott.com not reachable), below a hot block's working temperature.
- A ceramic bimetal disc thermostat (KSD301 class, normally closed, 250-300 degC) is the usual hardware part for this
  but is about 16 mm across and has no seat on a Revo or V6 hot side (recalled; no vendor reached). Not added: it
  would be an invented part.
- What a design can really do with stock parts: keep the PSU relay (already catalogued) so the firmware can drop the
  supply, and add a thermal cut-off on the *heat sink* in series with the heater (it trips when the cold side
  overheats, an indirect but independent signal). E3D sells a Roto heat-sink thermistor kit for the firmware side of
  the same idea.

## Still not vendor data (hand downloads that would fix it)

See `vendor_cad/inbox/README.md` ("Documents"): Roto inductance, MIC-6 and ATP-5 data sheets, Gates 2 mm design
manual, OpenBuilds spacer page.

## Effect on existing designs

None. `printer_v5` `--only ratings`: the same 27 `uncatalogued_cots` warnings and the same findings before and after
(the design still uses its own proxies). No existing part's shape, SKU or ratings changed; `tests/test_vendor.py`
checks the 6 and 12 mm pulley and idler names.
