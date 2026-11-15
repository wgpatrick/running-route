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
| Real CAD | E3D "Roto Reference" (Printables 655950), hand-downloaded 2026-11-15: now the detail model | not reached | STEP on GitHub (reachable) | not reached | not looked for |

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
| Mounting | 2 x dia 3.3 +/-0.08 holes at (0, 0) and (6.8, 30.5), along Y, each through two 7 mm ears at abs(Y) 12.25..19.25 | drawing `vendor_docs/E3D_Roto_Dim.svg`; ears and positions measured in E3D's reference CAD (lower hole drawn 3.39) |
| Nozzle tip | drawing: (-9.05 +/-0.26, -33.55 +0.46/-0.36) from the lower hole, 15.18 +/-0.41 from one side face. Catalogue (reference CAD): (-9.058, -4.06, -33.55), 15.19 from the -Y face | drawing and reference CAD agree |
| Envelope | X -25.258..31.85, Y -19.25..19.25, Z -11.75..44.15 (57.11 x 38.5 x 55.9; the drawing's -25.25, -11.45 body bottom, 38.5 agree) | measured in E3D's reference CAD; motor leads (flexible, to Y -37, Z 44.8 as drawn) excluded |
| Body top, motor, fan, lever, ears | body top 27.05; motor dia 36.2, X 16.35..31.85, axis (0, 7.8); fan Z -9.7..25.3; lever X -21.62..6.92, Y 2.94..12.88; ears X 3.25..10.35 to Z 34.05 | measured in E3D's reference CAD (were scaled from the drawing; table in `docs/VENDOR_CAD.md`) |
| Side of the 4.06 mm lateral nozzle offset | -Y | **confirmed** by the reference CAD (was assumed) |

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
| `extruder_roto()` = E3D REVO-ROTO-COLDSIDE-AS | E3D Roto data-sheet page and drawing; geometry from E3D's reference CAD (`vendor_cad/e3d_roto_reference_cad.step`) | table above | inductance; idler lever travel; licence of the reference CAD; cost |
| `hotend_revo(40, 24.0, 0.4)` = E3D RC-CORE-24V-AS-SPRING + RC-NOZZLE-0400-AS-SPK | `e3d-online.com/pages/revo-support-40w-104nt-heatercore`, `.../revo-support-brass-nozzle`, nozzle drawing | 40 W; 14.4 ohm at 23 degC; temperature coefficient 0.002078 /degC (27.2 W at 250 degC); max 300 degC; Klipper sensor "ATC Semitec 104NT-4-R025H42G"; Micro-Fit connectors; nozzle 8 g, 41.1 long, 22.8 +/-0.2 seat to tip, 13 mm block | lead sleeve 22 x 5 x 4.6 (scaled from the HeaterCore drawing; not in the reference CAD; HeaterCore 16.7 dia x 11.88 is now measured in E3D's reference CAD); HeaterCore mass 9 g (157 - 140 - 8); thermal capacity 6.5 J/K and area (estimates); sensor response 2 s |
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

---

# Hand-collected documents (added 2026-11-15)

The owner downloaded eight documents by hand (Drive folder; listing and sizes in `vendor_cad/staging/MANIFEST.md`). They
were read as PDF only. Copies are in `vendor_docs/`. The numbers are recorded as new, labelled blocks in the vendor JSON
files. **No value that the catalogue code, `MATERIALS`, a verifier or the twin reads was changed**: the blocks sit
beside the old values. What each document would change, and the expected effect on printer_v4 / v5 / v6, is in
`/home/user/running-route/reports/Vendor documents - what they change.md`.

The new blocks use the key `document_file` (not `local_copy`), because `tests/test_vendor.py` limits a `local_copy`
to 2 MB and the Gates manual is 4.2 MB.

| File in `vendor_docs/` | What it is | Recorded in | What it now backs | What it does not contain |
|---|---|---|---|---|
| `Hiwin_MG_catalogue.pdf` | HIWIN GmbH catalogue GW-11-5-EN-2207-K, section 3.5 MG series, printed pages 92-105 (14 PDF pages) | `hiwin_mgn12.json`, block `catalogue` | Primary confirmation of every MGN12H / MGNR12 value under `parts` (was two third-party transcriptions): dimensions, L1 32.4, M3 x 3.5 thread, Cdyn 3720 N, C0 5880 N, moments 38.2 / 36.3 / 36.3 N.m, 0.65 kg/m. New: **radial rigidity** (Table 3.77: MGN12H 63 N/um at Z0, 81 at Z1; MGN7H 39 / 51), preload classes ZF / Z0 / Z1, running parallelism by rail length, H and N tolerances, allowed parallelism of two rails (MG_12: 9 um at ZF / Z0, 5 um at Z1), height coefficient, mounting flatness, shoulders, the same for MGN7, 9, 15 | Rigidity for class ZF, lateral or moment rigidity, a ball-track length separate from L1, friction, preload force in newtons |
| `Gates_GT2_design_manual.pdf` | Gates "Light Power and Precision Drive Design Manual", 112 PDF pages (PDF page = printed page + 2) | new file `gates_gt2.json` | 2 mm pitch GT2 / GT3: stock widths 4 / 6 / 9 mm; working tension, minimum breaking strength and **tension for 0.1 % elongation** per width (Table 6, p.59: 6 mm 3.8 lb, i.e. EA 16.9 kN); torque ratings and width multipliers; installation tension per span (Tables 7, 8, p.65); sprocket tables (2MR-20S-06, 2MR-20S-09), minimum idler sizes, flange and face-width rules, belt thickness 1.52 mm, 85 degC limit | A modulus curve against tension, hysteresis, a tooth-jump torque number, printed belt mass (derived here from the mass constant M), any 12 mm stock belt or sprocket in 2 mm pitch, a 5 mm bore 20-groove sprocket |
| `Wang2018_GT2_belt.pdf` | Wang et al., Robotics 2018, 7(4), 75, https://doi.org/10.3390/robotics7040075 (PDF page = printed page + 1) | `gates_gt2.json`, block `measurement_wang_2018` | Tensile tests of GT2 belt to rupture, 400 and 760 mm free length, six curves; regression table; EA of the tested belt 24.2 kN (low-strain linear fit), tangent rising from about 11 to 30 kN with strain | **Belt width is not stated** (inferred 6 mm from the breaking load), maker, grips, temperature, pretension, unloading or cycling (no hysteresis), any second width |
| `17HS13-0404S1_datasheet.pdf` | StepperOnline drawing A0581 rev 0, 2.27.2026 | `stepperonline_nema17.json`, `parts.34.datasheet_17HS13_0404S1` | The S1 variant: electrically and mechanically the 17HS13-0404S already recorded; differs in the lead (1000 mm with HX25402-4Y connector against 300 mm bare), hole-square tolerance +/-0.1 (S: +/-0.2) and the flat-length tolerance | Rotor inertia and weight (blank), detent torque, torque-speed curve, shaft loads |
| `17HS19-2004S1_datasheet.pdf` | StepperOnline drawing A0842 rev 0, 8.1.2025 | `stepperonline_nema17.json`, `parts.48.datasheet_2025_drawing_A0842` | Same part as the 2020 sheet already stored, but **resistance 1.60 ohm** (2020 sheet 1.40) and a new shaft-load comment, "LENGTH 20mm: 21N MAX" | Weight (blank), detent torque, torque-speed curve, axial load |
| `MH2025-5-8_datasheet.pdf` | StepperOnline drawing A1917, 10.26.2026 | `stepperonline_coupler.json`, block `drawing` (and `vendor_step_first_inspection`) | OD 20, length 25, bores 5 and 8: equal to the product-page values in use | **Any misalignment figure**, torque, stiffness, speed, mass, clamp screw size. The 1.0 deg used by the tolerance check stays assumed |
| `ATP5_datasheet.pdf` | Vista Metals ATP-5 product sheet, 2 pages | `cast_tooling_plate.json`, `datasheets.al_atp5` | Density 2660, yield 124, tensile 283 (all as recorded, were recalled); E 70,000 MPa (recorded 70,300); expansion 23.6e-6 /K at 20-100 degC (recorded 23.8e-6); new: 140 W/m.K, 70 HB, flatness 0.127 mm over 12.7 mm thick and 0.381 mm at 12.7 mm and under, thickness +/-0.127 mm, 6.35 to 101.6 mm | Specific heat, Poisson's ratio, a list of stock thicknesses |
| `MIC6_datasheet.pdf` | United Performance Metals "Alloy MIC 6", 2 pages | `cast_tooling_plate.json`, `datasheets.al_mic6` | **Nothing.** The property tables are empty in this file (headings only; the page was saved before its tables loaded) | Every number. `al_mic6` density and modulus stay recalled. Needs downloading again (print the page after it has loaded, or the Arconic / Kaiser sheet) |

This supersedes three rows of "Could not be sourced" above: the Hiwin catalogue and the Gates manual are now in hand,
and the MGN12 entry can move from `secondary` to `vendor` when the catalogue code is switched to the `catalogue` block.
It closes two of the five lines under "Documents" in `vendor_cad/inbox/README.md` (ATP-5, Gates) and leaves MIC-6 open.

Six STEP files came with the documents and are still in `vendor_cad/staging/` (not integrated): the two motors,
the coupler, E3D's Roto Sensored and Roto Bowden reference models and E3D's Revo Voron reference. First inspection
(solids, sizes, what differs from the catalogue parts) is in the report named above.

## Second and third batch (2026-11-15)

Same rules: labelled blocks only, no value in use changed. Details and effects: the same report, section "Second and
third batch".

| File | What it is | Recorded in | What it now backs | What it does not contain |
|---|---|---|---|---|
| `vendor_docs/ENDSTOP-MICRO_datasheet.pdf` | OMRON D2F ultra subminiature basic switch data sheet, 6 pages | new file `omron_d2f.json` | D2F body, mounting holes, terminals, ratings, and the hinge-lever figures: operating position 6.8 +/-1.5 mm from the mounting-hole line, free position 10 mm max, overtravel 0.55 mm min, movement differential 0.5 mm max, operating force 0.78 N max. **The catalogue endstop's trigger (9.0 mm, from a recalled "10 +/-1") is 2.2 mm too far out**; not changed here | Pretravel for lever models; the carrier board |
| `vendor_docs/HOST-RPI-ZERO-2W_datasheet.pdf` | Raspberry Pi Zero 2 W product brief, April 2024, 6 pages | new file `raspberry_pi_zero2w.json` | 65 x 30 board, holes 3.5 mm from each edge (58 x 23), -20 to 70 degC, "5V DC 2.5A" input | Current draw (the 0.60 A in the 5 V budget stays unverified), supply tolerance, hole diameter, mass |
| `vendor_cad/staging/SKR_Mini_E3_V3_drawing.pdf` | byte-identical to `vendor_docs/BTT_SKR_MINI_E3_V3.0_SIZE_20220301.pdf`; not copied again | `bigtreetech_skr_mini_e3_v3.json`, block `staging_copy_2026_11_15` | re-read confirms the outline and the five hole positions already recorded | hole diameter, connector positions |
| `vendor_cad/staging/LRS-350-24_datasheet.pdf` | byte-identical to `vendor_docs/LRS-350-SPEC.PDF`; not copied again | `meanwell_lrs.json`, block `parts.350.staging_copy_2026_11_15` | confirms every LRS-350 figure in `parts/electrical.py`; adds leakage under 2 mA, derating to 80 % at 90 VAC, protections, side-hole positions, the EN 61000-3-2 note | — |
| `vendor_cad/staging/MGN12H.step` | step.parts copy of the FreeCAD-library MGN12H | `hiwin_mgn12.json`, block `community_step_second_copy` | nothing new: identical geometry to `vendor_cad/mgn12h_block.step`, which is already the detail model | end caps, threads |

The three Zenodo folders in staging are data sets, not vendor documents; they are assessed in the report (none is the
commanded-motion-plus-response set that `Datasets and models for fitting the twin.md` asks for).

## Fourth batch (2026-11-15)

Same rules. Everything went into new JSON files that nothing reads (another agent was editing the parts code at the
time). Details and effects: the same report, section "Fourth batch".

| File in `vendor_docs/` | What it is | Recorded in (new file) | What it now backs | What it does not contain |
|---|---|---|---|---|
| `BED-PROBE_datasheet.pdf` (8.9 MB) | OMRON E2E proximity sensor family sheet, 35 pages; the pick is E2E-X8MD1 2M | `omron_e2e.json` | M12 unshielded, 8 mm +/-10 % on iron, about 2.8 to 3.2 mm on aluminium (chart), **DC two-wire** NO, 10-30 V, 3-100 mA load, 3 V residual, 0.8 mA leakage, -25 to 70 degC, dimensions, clearances. **Not the NPN three-wire block that printer_v6's stand-in models** | Repeatability |
| `FAN-3010_datasheet.pdf` (4.4 MB) | Sunon MF30101V2-1000U-A99 specification, 14 pages | `sunon_mf30101v2.json` | 30 x 30 x 10, three 3.2 mm holes on 24 mm, 7.8 g, 8,600 rpm, 4.6 CFM, 35 Pa, 20 dB(A), 70,000 h. **It is a 12 V fan (6-13.8 V), not 24 V** | The 24 V version |
| `INLET-C14-SW-FUSE-T8A_datasheet.pdf` | Schurter DD11 power entry module, 6 pages | `schurter_dd11.json` | 10 A 250 VAC, 2-pole switch, 5 x 20 fuseholder, cut-out 47.1 x 28.1, screws 56 apart (version A), 4.8 mm terminals, -25 to 85 degC. The catalogue inlet's cut-out (43 x 28), hole pitch (50) and terminals (6.3) differ | Which order number; fuse drawer and fuse are separate |
| `RELAY-BTT-V1.2_datasheet.pdf` | BIGTREETECH Relay V1.2 operating instruction, 8 pages | `bigtreetech_relay_v12.json` | Outline and holes as in the catalogue; terminals LIN / N / LOT; switches the live only; powers itself from mains (needs N, which the catalogue part lacks); 3.3-5 V logic | Contact rating, power-up state, height |
| `BED-COLUMN-SIL-16x18_dims.txt` | collector's note from a seller listing | `silicone_bed_column_dims.json` | 16 OD x 18 x 4 bore, as in the catalogue | Hardness, stiffness |
| (staging only) 17 distinct McMaster STEP files | 91290A-series cap screws, 90591A-series nuts | `mcmaster_fasteners.json` | Part numbers; heads, lengths, sockets equal ISO 4762; M5 nut 4.0 mm thick (DIN 934) against the catalogue's 4.7 (ISO 4032). `SHCS-M3x6.step` is the M3x12 file. Recommendation: keep the generated solids (a McMaster M3x30 is 767 faces and 22,144 triangles against 15 and 696) | M3x6, M3x25, M3x45, M5x16 |
| (staging only) `LRS-350-24.step` | byte-identical to `vendor_cad/meanwell_LRS-350.stp` | — | already the detail model | — |


# Applied 2026-11-15: what the hand-collected documents changed in the code

The two sections above recorded the documents beside the values in use. This section says what was then applied.
Numbering is that of `/home/user/running-route/reports/Vendor documents - what they change.md`, where each proposal is
marked applied or not. Known-answer tests: `tests/test_known_answers_v6.py`. Statements earlier in this file that
these supersede: "Recorded but not vendor-backed" (MGN12 is vendor-backed; `thread_depth_unverified` is now
`thread_depth` and drives `thread_bottoms_out`), "Could not be sourced" rows for Hiwin and Gates, and "No value that
the catalogue code ... reads was changed".

| # | What changed | Where | Source |
|---|---|---|---|
| 1 | Belt stiffness 22 -> **19 kN per 6 mm** (range 15 to 27 kept), linear in width, with a note that it rises with tension | `mechloop/twin/fitted_parameters.json` `belt_ea_n_per_6mm` (the one place; `PrinterMap.belt_ea_n` reads it) | Gates manual Table 6 (16.9 kN); three reference machines and Wang 2018 (21 to 24 kN) |
| 2 | New rating on `nema17(48)`: `max_radial_load_n` 21 at `max_radial_load_at_mm` 20, basis "read from drawing, meaning inferred". New ratings check `motor_shaft_radial_load` (warning); `Belt.tension`, default Gates' minimum installation tension for the width | `stepperonline_nema17.json` parts.48.values; `verifiers/ratings.py` `belt_shaft_loads`; `gates_gt2.json` belt.installation_tension | drawing A0842 (one line); Gates manual p.65 |
| 3 | `mgn12h_carriage(preload=...)`: radial rigidity 63 N/um (Z0, the default, reported as assumed) or 81 (Z1); none for ZF, which uses the verifier's assumed 40. Ball-track length L1 32.4 mm. `ratings.BLOCK_K` is now only the fallback | `parts/__init__.py`; `hiwin_mgn12.json` catalogue | Hiwin Tables 3.77, 3.79 |
| 4 | Coupler: bores as in the vendor STEP; `max_insertion_a` 12.05, `max_insertion_b` 8.6, `bore_depth` 7.5; check `shaft_too_deep_in_coupler` | `shaft_coupler()`; `stepperonline_coupler.json` vendor_step; `verifiers/interference.py` | vendor STEP (`docs/VENDOR_CAD.md`) |
| 5 | Allowable parallelism of two rails: 0.009 mm (ZF, Z0), 0.005 mm (Z1), as `allowable_parallelism_mm` on the block; the paired-rail metrics give it with its source and the preload class (default was 0.025) | `parts/__init__.py`; `tolerance/__init__.py` | Hiwin Table 3.88 |
| 6 | MGN12 rail and carriage are vendor-backed (`source.level` "vendor"); `thread_depth` 3.5, so `thread_bottoms_out` applies to carriage screws. Values in use are the earlier transcriptions, equal to the catalogue's except in rounding (mass 0.054 against a printed 0.05; moments 38.22 / 36.26 against 38.2 / 36.3) | `parts/__init__.py` | Hiwin Tables 3.76, 3.79, 3.81 |
| 7 | 17HS19-2004S1 resistance 1.40 -> 1.60 ohm; `MOTOR_ELECTRICAL` is now built from the vendor file, so the two tables cannot disagree (side effect: the fallback holding torque of the 60 mm motor is the drawing's 650 N.mm, not the page's 760; the catalogue part always used 650) | `stepperonline_nema17.json`; `parts/electrical.py` | drawing A0842 |
| 8 | Stock flatness of cast tooling plate as supplied (0.381 mm up to 12.7 mm thick, 0.127 above), reported beside the bed results as a reference; not applied to the stack-up | `tolerance/process.py` `STOCK_PLATE_FLATNESS`; tolerance metrics `printer.bed_plate_stock_flatness` | ATP-5 sheet (shown for MIC-6 too, whose sheet is empty) |
| 9 | `al_atp5`: E 70,300 -> 70,000 MPa; expansion 23.8e-6 -> 23.6e-6 /K | `model.py`, `verifiers/fea.py`, `cast_tooling_plate.json` | ATP-5 sheet |
| 10 | Pulley and idler source text: 12 mm belt in 2 mm pitch and a 5 mm-bore 20-groove sprocket are not Gates stock | `parts/__init__.py` `_gt2_source` | Gates manual p.15, p.29 |
| 11 | Twin text: the fitted 10 N/um is unchanged; its description now says the bare block is 17 % (MGN12H) and 24 % (MGN7H) of that compliance, the rest mounts and clamp; MGN7H L1 is the maker's figure | `fitted_parameters.json` | Hiwin Tables 3.77, 3.79 |
| 12 | Endstop: trigger 9.0 -> **6.8 mm** from the mounting-hole line (Y 10.6 -> 8.4), tolerance +/-1.5, overtravel 0.55 min, movement differential 0.5, operating force 0.78 N; new interfaces `trigger_latest`, `trigger_earliest`, `case_limit`; the endstop check uses the spread | `parts/details.py` `ENDSTOP` (reads `omron_d2f.json`); `verifiers/subsystems.py` | OMRON D2F data sheet p.4 |
| 13 | BOM text names the gold-contact low-current type (D2F-01L) and why | `endstop_switch()` description and source | OMRON D2F data sheet p.2 |
| 14 | OMRON's right-angled terminal figures recorded on the part (`pin_row_omron_right_angled`); the generated carrier board's row is unchanged and the source text says it is not a known bought module | `endstop_switch()` | OMRON D2F data sheet p.3 |
| 15 | LRS-350: `leakage_current_ma_max` 2.0 at 240 VAC, `derate_to_frac_at_90vac` 0.8, `full_load_min_vac` 100; metrics `bay.psu_low_line`; an error only if the design's own mains range goes below 100 VAC with more load than allowed | `psu_lrs()`; `verifiers/electrical.py` | LRS-350-SPEC p.2, p.3 |
| 16 | Pi Zero 2 W: `min_ambient_c` -20, `max_ambient_c` 70; the bay check compares the bay air with each device's own limit (`device_over_ambient_limit`). The 0.60 A draw stays unverified | `raspberry_pi_zero2w()`; `verifiers/electrical.py` | product brief p.3 |
| motors | `17HS13-0404S1.step`, `17HS19-2004S1.step` and `COUPLER-5x8.step` are detail models; the motors' simulation solids have the STEP's small lead exit in place of a connector block | `docs/VENDOR_CAD.md` | vendor STEP files |

Still not vendor data after this: MIC-6 (empty sheet), the coupler's permissible misalignment (1.0 deg assumed), the
Pi's current draw, any lateral or moment rigidity of a guide block, a shaft-load figure for the 34 mm motor, belt
stiffness against tension as a curve, the endstop's carrier board.


# Applied 2026-11-15 (fourth batch: proposals 17 to 22)

Tests: `tests/test_known_answers_batch4.py`. Status per proposal: the report's last table.

| # | What changed | Where | Source |
|---|---|---|---|
| 17 | Bed probes as catalogue parts: `probe_omron_e2e("E2E-X5ME1" / "E2E-X10ME1" / "E2E-X5E1" / "E2E-X8MD1", clamp=)`. Ratings, thread, nuts and surrounding-metal clearances are the maker's; aluminium distance is a chart reading for a small 1 mm plate (1.6 / 3.0 / 1.75 / 2.8 mm), repeatability assumed, mass estimated (parts are `partial`, not verified). Two-wire model in the electrical check; mounting check in subsystems; temperature drift in the trigger-height range | `mechloop/parts/probes.py`; `omron_e2e.json` block `catalogue_models`; `verifiers/electrical.py`, `verifiers/subsystems.py`, `electrical.probe_geometry` | OMRON E2E data sheet p.13, 16, 17, 18, 21, 25, 27, 28 |
| 18 | `fan(size, volts)`; `fan(30, 12)` = Sunon MF30101V2-1000U-A99 (12 V, 32 mA). The 24 V 30 mm fan: sheet not in hand, figures typical | `parts/__init__.py`, `parts/electrical.py` | Sunon specification D03033610G-01 |
| 19 | Relay N terminal; `required_supply_ports`; error `device_supply_not_connected` | `relay_btt_v12()`; `verifiers/electrical.py` | BIGTREETECH Relay V1.2 manual p.3 |
| 20 | Inlet = SCHURTER DD11 version A (geometry, ratings, 4.8 mm terminals); order number not pinned; hint on the panel's `holes_too_close` | `iec_inlet_c14()`; `verifiers/manufacture.py` | SCHURTER DD11 data sheet p.1, p.3 |
| 21, 22 | McMaster part numbers per fastener SKU, with status, in the BOM; DIN 934 M5 nut as an option (`NUT-M5-DIN934`, 4.0 mm) | `parts/__init__.py` `mcmaster_part`, `hex_nut`, `add_nut`; `verifiers/ratings.py` | `mcmaster_fasteners.json` (STEP files inspected) |

Not vendor data after this: a 24 V 30 mm fan's figures, the relay's contact rating, the inlet's order number and
terminal positions, any probe's repeatability and its distance on a large thick aluminium plate. No touch probe exists
in the catalogue (no off-the-shelf module with data).
