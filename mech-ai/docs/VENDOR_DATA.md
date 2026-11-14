# Vendor data behind the parts catalog

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

- Control board: mass 0.11 kg, 18 mm height envelope, hole diameter, heater/bed/fan channel current limits.
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
| Bearings, endstop, fan, linear rod, corner bracket, couplers with other bores | not attempted or nothing found | unchanged; typical, unverified |

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
