# Vendor documents: what they change

2026-11-15. Eight hand-collected PDFs and six STEP files in `mech-ai/vendor_cad/staging/` (listing:
`MANIFEST.md` there). Every file was treated as data: PDFs read as text and as rendered pages, STEP files loaded as
geometry only.

**Nothing that a design depends on was changed.** No part rating, shape, `MATERIALS` value, verifier constant or twin
parameter moved. The numbers were added beside the existing ones:

- `mech-ai/mechloop/parts/vendor/hiwin_mgn12.json`: new block `catalogue`
- `mech-ai/mechloop/parts/vendor/gates_gt2.json`: new file (Gates manual and the Wang 2018 measurements); nothing reads it
- `mech-ai/mechloop/parts/vendor/stepperonline_nema17.json`: new blocks under parts `34` and `48`
- `mech-ai/mechloop/parts/vendor/stepperonline_coupler.json`: new blocks `drawing`, `vendor_step_first_inspection`
- `mech-ai/mechloop/parts/vendor/cast_tooling_plate.json`: new block `datasheets`
- the eight PDFs copied to `mech-ai/vendor_docs/`; listed in `mech-ai/docs/VENDOR_DATA.md` ("Hand-collected documents")

`tests/test_vendor.py` passes (42 tests). Nothing was re-verified or re-scored: every "expected effect" below is worked
out by hand from the stored reports (`out/printer_v4|v5|v6/report.json`) and from `Twin fitting.md`, and says so.

Page numbers are the printed ones. PDF page = printed page - 91 (Hiwin), + 2 (Gates), + 1 (Wang).

## Answer in brief

| Document | Headline | Against what we assume |
|---|---|---|
| Hiwin MG catalogue | **A rigidity table for MGN is in this edition** (Table 3.77, p.96): MGN12H 63 N/µm at preload Z0, 81 at Z1. Everything recorded for MGN12H and its rail is confirmed by the maker | `BLOCK_K` 40 N/µm is 37 % low for a Z0 block. The twin's fitted 10 N/µm is one sixth of the block's own radial rigidity, so it is mostly something else |
| Gates manual | 2 mm GT3 belt needs 3.8 lb for 0.1 % elongation at 6 mm width: **EA 16.9 kN per 6 mm** (Table 6, p.59). Linear in width from 4 to 9 mm | Our 22 kN is 30 % higher; 16.9 is inside our range (15 to 27) near its low end |
| Wang 2018 | EA of the tested belt 24.2 kN (linear fit to 2 % strain); the tangent value rises from about 11 kN at no load to 30 kN at 1.6 % strain. **Width is not stated** | Brackets our 22 kN from above and explains the spread: stiffness depends on tension. At Gates' normal installation tension the two sources give 17 to 18 kN |
| 17HS13-0404S1 | Same motor as the recorded 17HS13-0404S; only the lead (1 m with connector), two tolerances and two blank cells differ | Confirms the catalogue entry |
| 17HS19-2004S1 (2025 drawing) | **Resistance 1.60 Ω** (we use 1.40 from the 2020 drawing). New line: 21 N maximum at 20 mm on the shaft | Small contradiction (resistance). The shaft-load limit is new and is far below any Gates belt tension |
| MH2025-5-8 | A four-dimension outline drawing. **No misalignment, torque or stiffness figure** | Confirms OD 20, length 25, bores. The 1.0° stays assumed |
| ATP-5 | Density, yield and tensile as recorded. E 70,000 MPa, expansion 23.6e-6 /K, 140 W/m·K, flatness 0.381 mm for plate 12.7 mm and thinner | Confirms `al_atp5` within 1 %. The flatness guarantee for thin plate is loose |
| MIC-6 | **The property tables in this PDF are empty** | Nothing confirmed. Needs fetching again |

## Proposed changes, ordered by effect

None is applied. "Effect" is on printer_v4 / v5 / v6.

| # | Change | Where | Expected effect |
|---|---|---|---|
| 1 | Belt stiffness: move the expected value from 22 to about 19 kN per 6 mm (between the maker's 16.9 and the 21 the three reference machines imply), keep the range 15 to 27, and record that it rises with tension | `fitted_parameters.json` `belt_ea_n_per_6mm`, `PrinterMap.belt_ea_n` | Twin scores only. At 19 kN: v5 X 71.6 → about 70 Hz, Y 62.0 → about 60; v4 X 55.4 → about 54, Y 56.9 → about 55. At Gates' 16.9 kN: v5 X about 69, Y about 58.5; v4 X about 53, Y about 53.5. The acceleration an owner would run falls 4 to 11 %. v6: X belt spring 273 → 236 N/mm (210 at 16.9), each Y belt 239 → 206 (183). All inside the published ranges. No verifier changes between pass and fail |
| 2 | New check: belt pull on a motor shaft against the motor's radial load limit. Needs a belt pretension on `Belt` and a rating `max_radial_load_n` (21 N at 20 mm for the 48 mm motor) | `ratings.py`, `nema17(48)` | **Would raise a new finding on the Y drives of all three designs** unless the pretension is set below any value Gates recommends: a 12 mm belt at Gates' minimum tension pulls 37 N on the shaft, at its general value 214 N; the limit at the v6 belt plane (16 mm from the motor face) is about 26 N. Rests on reading one terse drawing comment (section 4) |
| 3 | Give `mgn12h_carriage()` the maker's rigidity: `radial_stiffness_n_per_m` 63e6 (Z0), `ball_track_length_m` 0.0324, with the preload class stated. The ratings check already reads both keys | `parts/__init__.py` (not `BLOCK_K`, which stays the fallback for unknown blocks) | v4 Z tilt mode 75.6 → about 102 Hz: its `cantilever_on_guide_blocks` warning (limit 100 Hz) disappears, by 2 Hz. v5 562 → about 708 Hz, v6 358 → about 453 Hz. Sag per kg falls by 37 to 46 %. No other finding changes. Do not apply to blocks bought as ZF (clearance): the catalogue gives them no rigidity |
| 4 | Lead screw seat in the coupler: the vendor CAD has 8 mm and 5 mm bores only 7.3 mm deep, and the elastomer web 9.5 mm from each end. All three designs put the lead screw 12.5 mm into the coupler | `shaft_coupler()` shape and a `bore_depth` interface; `designs/printer_v4/v5/v6` (`z_cpl + 12.5`) | The screw can enter 9.5 mm, not 12.5: it sits 3 mm higher than drawn, or the coupler 3 mm lower. In v6 the screw top is drawn 4 mm under the top back rail, so 1 mm would remain. The motor shaft (8.5 mm in) is fine |
| 5 | Allowed parallelism of two rails: 0.025 mm default → 0.009 mm (MG_12 at ZF or Z0), 0.005 mm at Z1 (Table 3.88, p.104), as `allowable_parallelism_mm` on the block | `parts/__init__.py`; `tolerance/__init__.py` reads it | Metrics only: `p_within_allowable` is already 0.3 to 1.1 % on the Y and Z axes of all three designs and all three declare `rail_align` adjustments, which is the branch that decides pass or fail. The catalogue makes the case for those adjustments stronger |
| 6 | Switch the MGN12 entry from `secondary` to `vendor` (read the `catalogue` block), drop `approximate`, rename `thread_depth_unverified` to `thread_depth` (M3 × 3.5 is now the maker's figure) | `parts/__init__.py` | MGN12H and the rail leave the `approximate_ratings` list. `thread_bottoms_out` starts to apply to carriage screws: v5 and v6 were designed to 3.0 mm of engagement and should pass; printer_v3 and `examples/gantry.py` are known to be 0.5 mm too long; v4 not checked here |
| 7 | 17HS19-2004S1 resistance 1.40 → 1.60 Ω in the vendor file. `parts/electrical.py` `MOTOR_ELECTRICAL` already says 1.6, so the two tables would then agree | `stepperonline_nema17.json` `parts.48.values` | Y motors: copper loss 1.17 → 1.34 W each, case rise 5.7 → 6.5 K. Torque at the designs' 0.6 A per motor is unchanged up to 900 rpm (177 N·mm), 0.3 N·mm lower at 900 rpm. Nothing else |
| 8 | A stock-plate flatness figure for cast tooling plate used as supplied: 0.381 mm guaranteed at 12.7 mm and under, 0.127 mm above (ATP-5). The tolerance model's "machined" figure is 0.02 mm | `tolerance/process.py`, or the bed's own tolerance in the design | The beds are 6 mm plate. v6 probes a mesh, which is what this needs; the bed-level check is about tilt, not bow, so no pass or fail change is expected. ATP-5 is listed from 6.35 mm: a 6.0 mm ATP-5 bed is not shown to be a stock size |
| 9 | `al_atp5`: E 70,300 → 70,000 MPa; expansion in `fea.py` `ALPHA` 23.8e-6 → 23.6e-6 | `model.py`, `verifiers/fea.py` | None today: no design uses `al_atp5` (v6's bed is `al_mic6`) |
| 10 | Record that Gates makes no 12 mm belt or sprocket in 2 mm pitch as stock and no 5 mm bore 20-groove sprocket; the designs' pulleys are generic parts | pulley / idler `source` text; BOM notes | None on checks. A buying note: 12 mm Y belts (v4, v5, v6) and all 5 mm bore pulleys are not Gates catalogue items |
| 11 | Twin text only: MGN7H L1 21.8 mm is now the maker's figure (was "recalled, unverified"); the fitted 10 N/µm can cite the catalogue's 63 and 39 N/µm as what it is not | `fitted_parameters.json` `reference_geometry` | None on numbers |

## 1. Hiwin MG catalogue

`vendor_docs/Hiwin_MG_catalogue.pdf`: HIWIN GmbH, catalogue GW-11-5-EN-2207-K, section 3.5 "MG series", printed pages
92 to 105. Recorded in `hiwin_mgn12.json`, block `catalogue` (MGN7, 9, 12, 15, C and H).

**Is the rigidity table there? Yes.** Section 3.5.11 and Table 3.77 "Radial rigidity of MGN series", p.96, unit N/µm,
with the formula deformation = load / k:

| Block | Z0 | Z1 | | Block | Z0 | Z1 |
|---|---|---|---|---|---|---|
| MGN07C | 26 | 33 | | MGN07H | 39 | 51 |
| MGN09C | 37 | 48 | | MGN09H | 56 | 73 |
| MGN12C | 44 | 56 | | **MGN12H** | **63** | **81** |
| MGN15C | 57 | 74 | | MGN15H | 87 | 113 |

Conditions and limits of that table:

- Per block, radial direction (load pressing the block onto the rail).
- Preload Z0 is "reduced play to very light preload: 0 to 3 µm"; Z1 is "light preload: 0 to 0.02 Cdyn"; ZF is "slight
  backlash: 4 to 10 µm" (Table 3.75, p.95). **No rigidity is given for ZF.** A block with clearance has none until the
  clearance is taken up.
- No lateral, reverse-radial or moment (tilt) rigidity is given, and no ball-track length other than L1.

| Quantity | Now, and where | Catalogue (page) | Difference | Proposed | Effect |
|---|---|---|---|---|---|
| Radial rigidity of one MGN12H | `BLOCK_K = 40e6` N/m, `verifiers/ratings.py:13`, "assumed" | 63 N/µm at Z0, 81 at Z1 (Table 3.77, p.96) | ours is 37 % low at Z0, 51 % low at Z1 | change 3 | v4 loses one warning, by 2 Hz; v5 and v6 metrics rise |
| Length the block bears on | 30 mm default in the cantilever check (`ratings.py:242`); 32.4 mm in `guide_tilt` | L1 32.4 mm (Table 3.79, p.97); L1 is drawn as the block body without end caps | default is 7 % short | part of change 3 | tilt stiffness of a lone pair of blocks +17 % |
| Twin: effective block stiffness for toolhead tilt | 10 N/µm (7.5 to 16), `fitted_parameters.json`; "not a measurement of block stiffness" | radial 63 (MGN12H), 39 (MGN7H) at Z0 | the fitted value is 16 % of the MGN12H figure and 26 % of the MGN7H figure | no change to the value; change 11 | see below |
| MGN7H L1 used in the fit | 21.8 mm, "recalled, unverified" | 21.8 mm (Table 3.79, p.97) | none | change 11 | none |
| MGN12H dimensions: H 13, H1 3, N 7.5, W 27, B 20, B1 3.5, C 20, L 45.4 | `hiwin_mgn12.json` `parts` (secondary) | the same (Table 3.79, p.97) | none | change 6 | part becomes vendor-backed |
| Carriage thread | M3 × 3.5, exposed as `thread_depth_unverified` | M3 × 3.5 (Table 3.79) | none | change 6 | `thread_bottoms_out` would apply |
| Cdyn / C0 | 3720 / 5880 N | 3,720 / 5,880 N; Cdyn is for a 50,000 m travel path (Table 3.76, p.95) | none | note the 50 km basis if a life is ever computed | none |
| Static moments MR / MP / MY | 38.22 / 36.26 / 36.26 N·m; the check uses the minimum, 36.26 | M0X 38.2, M0Y 36.3, M0Z 36.3 N·m (Table 3.76) | rounding | none | none |
| Block mass | 0.054 kg | 0.050 kg (two decimals) | −4 g | none | none |
| Rail: 12 × 8, hole 3.5, counterbore 6 × 4.5, pitch 25, 0.65 kg/m | as recorded | the same (Table 3.81, p.99); end distance 5 to 20 mm, tolerance +0.5 / −1 | rail screw is listed as M3 × 10 (recorded M3x8) | none | none |
| Allowed parallelism of two rails | 0.025 mm default, `tolerance/__init__.py:121` | MG_12: 9 µm at ZF and Z0, 5 µm at Z1 (Table 3.88, p.104) | ours is 2.8 to 5 times looser | change 5 | metrics only |
| Height difference between two rails | not modelled | S1 = distance × K; MG_12: K 1.0e-4 at ZF / Z0, 0.24e-4 at Z1 (Table 3.89). At 200 mm spacing: 0.020 mm, 0.005 mm | new | candidate tolerance check | not estimated |
| Mounting-surface flatness | not modelled | MG_12: 0.050 mm per 200 mm, halved for Z1 or two rails on one surface (Table 3.90) | new | none now | — |
| Running parallelism of block to rail | not modelled | class C: 15 µm (125 to 200 mm), 16 (to 250), 17 (to 315); H: 9, 10, 11; P: 4, 5, 5 (Table 3.86, p.102) | new | none now | — |
| Height H and width N tolerance | not modelled | C ±0.04 / ±0.04; H ±0.02 / ±0.025; P ±0.01 / ±0.015; pair variance 0.03 / 0.015 / 0.007 (Table 3.87, p.103) | new | feeds the Z stack if wanted | — |
| Lateral guide stiffness in the rail-drift metric | `K_GUIDE = 15000` N/mm, `tolerance/__init__.py:16`, assumed | no lateral figure; radial 63 N/µm | not comparable | none | — |

What the catalogue supports about the two stiffness numbers we carry:

- `BLOCK_K` (40 N/µm) is too low for a real MGN12H at Z0 or Z1 by a factor of 1.6 to 2. It is too high for any block
  smaller than MGN12C at Z0 (MGN7H is 39, MGN9C 37, MGN7C 26). One constant for "a small block" is the wrong shape:
  the figure belongs on the part.
- The twin's 10 N/µm is not the block. If the tilt formula (k L1² / 12) is right for the block, the block's own share
  of the fitted compliance is 17 % on the MGN12H machine (10.5 of 63) and 24 % on the MGN7H machine (9.5 of 39); the
  remaining spring would be 12.6 N/µm in the same units on both machines. That is consistent with what `Twin fitting.md`
  says the number lumps in (printed mounts and belt clamp), and is no proof of it.
- The catalogue does not support "one k for both blocks": the bare blocks differ by 39 to 63.
- Upper bound for a design whose toolhead mount were rigid (block at 63 N/µm only): v5 X about 85 Hz instead of 71.6,
  v4 X about 66 instead of 55.4 (series-spring arithmetic on the figures in `Twin fitting.md`, not a twin run). The real
  value for v5 and v6, which have machined or sheet carriages, lies between the two; the documents cannot place it.

Not in this edition: rigidity for ZF, moment rigidity, preload in newtons, friction, a ball-track length.

## 2. Wang 2018, measured GT2 belt

`vendor_docs/Wang2018_GT2_belt.pdf`: Robotics 7(4) 75, technical note. Recorded in `gates_gt2.json`, block
`measurement_wang_2018`.

Test (p.3): new GT-2 belts, neoprene with glass fibre; free lengths 400 mm and 760 mm; three pulls each, to rupture; a
hand-cranked screw stand, 1.6 mm per turn, 0.8 mm/s, one reading per turn; load cell ±0.89 N. Belt section in Figure 1
(p.2): pitch 2, total thickness 1.38 mm, backing 0.63 mm.

**Not stated: belt width, maker, how the ends were gripped, temperature, any pretension.** No unloading and no cycling,
so **no hysteresis data**. One width only.

Read from Figure 4 (p.4) at the six rupture points (±10 N, ±0.3 mm):

| Specimen | Force, N | Extension, mm | Strain | Stress, MPa | Force / strain, kN |
|---|---|---|---|---|---|
| 760 mm, 1 | 670 | 20.6 | 0.0271 | 56 | 24.7 |
| 760 mm, 2 | 565 | 19.4 | 0.0255 | 47.5 | 22.2 |
| 760 mm, 3 | 635 | 19.0 | 0.0250 | 53 | 25.4 |
| 400 mm, 1 | 585 | 11.8 | 0.0295 | 49 | 19.8 |
| 400 mm, 2 | 595 | 12.7 | 0.0318 | 49.5 | 18.7 |
| 400 mm, 3 | 625 | 14.2 | 0.0355 | 52.3 | 17.6 |

- Force over stress is 12.0 mm² at every point: that is the section the authors used. They do not say so.
- Regression (Table 1, p.5), stress in MPa against strain: low-strain linear 2013.8 (to 2 % strain, R² 0.957); whole
  set linear 1821.1; whole set cubic −2.00e6 ε³ + 98,091 ε² + 937.22 ε − 0.18 (R² 0.967).
- EA of the tested belt = modulus × 12.0 mm² (the same as force over strain, so it does not depend on the area):
  **24.2 kN** from the low-strain line, 21.9 kN from the whole-set line.
- Nonlinearity, from the cubic: tangent EA 11.2 kN at zero strain, 13.5 at 0.1 %, 16.9 at 0.26 %, 21.2 at 0.5 %, 27.6
  at 1 %, peak 30.5 at 1.6 %, falling to 17 at 3 % before rupture at 2.5 to 3.6 %. Part of the soft start may be grips
  and seating on a manual stand; the paper does not separate it.

Width, by inference: the specimens broke at 565 to 670 N. Gates' minimum breaking strength for 2 mm pitch is 556 N at
6 mm and 845 N at 9 mm (manual p.59). So the belts were most likely 6 mm. A 9 mm belt at the 1.38 mm thickness would
have a 12.4 mm² section, also near 12.0, so the paper alone cannot exclude it.

| EA, kN | 6 mm | 9 mm | 12 mm | Assumption |
|---|---|---|---|---|
| Ours (`PrinterMap.belt_ea_n`, `machine.py:143` scales with width) | 22 (15 to 27) | 33 | 44 | linear in width |
| Wang, low-strain line, specimen 6 mm | 24.2 | 36.2 | 48.3 | linear in width |
| Wang, same, if the specimen was 9 mm | 16.1 | 24.2 | 32.2 | linear in width |
| Wang, tangent at Gates' general installation tension (44.5 N on 6 mm; 0.32 % strain on the paper's curve), specimen 6 mm | 18.0 | 27.0 | 36.0 | cubic fit |
| Gates, 0.1 % elongation (section 3) | 16.9 | 25.4 | 33.8 (extrapolated) | 12 mm not in the table |

Reading: our 22 kN sits between the maker's low-strain figure and the lab's mid-range figure. On the paper's curve it is the tangent
stiffness at 0.55 % strain, about 90 N on a 6 mm belt, which is twice Gates' general installation tension and equal
to what Gates suggests for registration drives (general value × 1.5 to 2.0, p.65). A belt at the general tension is
nearer 17 to 18 kN. The paper confirms that a single EA is an approximation and that the error has a sign: slack belts are
softer.

## 3. Gates design manual

`vendor_docs/Gates_GT2_design_manual.pdf`. Recorded in `gates_gt2.json`.

| Quantity | Now, and where | Manual (printed page) | Difference | Proposed | Effect |
|---|---|---|---|---|---|
| Belt stiffness, 6 mm | 22 kN, `twin/__init__.py:55`; range 15 to 27 | 3.8 lb for 0.1 % elongation = 16.9 N → **EA 16.9 kN** (Table 6, p.59, fiberglass cord). "Tensile modulus and strength are equivalent" for endless and long-length belting | ours +30 % | change 1 | section "Proposed changes" |
| Stiffness against width | linear, `machine.py:143` | 4 / 6 / 9 mm: 2.6 / 3.8 / 5.7 lb = 11.6 / 16.9 / 25.4 kN; 2,890 / 2,820 / 2,820 N per mm | confirms linear, 4 to 9 mm | none | none |
| 12 mm belt | used on Y in v4, v5, v6 and X in v4, v5; EA 44 kN | not a stock width (p.15 lists 4, 6, 9), not in Table 6, no 12 mm sprocket. It appears only in the width multiplier (p.18) and the tension tables (p.65). Extrapolated EA 33.8 kN | not backed | change 10 | buying note |
| Widths offered | pulley and idler functions take any width | stock 4, 6, 9 mm (p.15) | 9 mm (v6 X) is stock | — | — |
| Working tension | not modelled | Ta at 20 grooves: 24 / 39 / 65 lb = 107 / 173 / 289 N for 4 / 6 / 9 mm (Table 6) | new | a `belt_overloaded` check would have these | drive forces are 14.9 N (X) and 52.8 N over two belts (Y): margins above 10 |
| Breaking strength | not modelled | minimum 85 / 125 / 190 lb = 378 / 556 / 845 N | new | none | — |
| Rated torque, 20 grooves, 6 mm | not modelled | 1.51 N·m at 10 rpm, 0.93 at 300, 0.88 at 400, 0.73 at 1000 (p.18); × width 1.64 (9 mm), 2.32 (12 mm); × length 1.25 to 1.35 for 510 to 800 mm belts; service factor 1.5 to 2.0, or 1.0 on a stepper's holding torque (p.63) | new | none | motors deliver 0.10 (X) and 0.18 N·m (each Y) at speed: far inside |
| Installation tension per span | not modelled; `Belt.adjust` gives ±3 mm of travel | minimum 1.4 / 2.1 / 3.2 / 4.2 lb = 6.2 / 9.3 / 14.2 / 18.7 N; general 6 / 10 / 17 / 24 lb = 26.7 / 44.5 / 75.6 / 106.8 N for 4 / 6 / 9 / 12 mm (Tables 7, 8, p.65); registration drives × 1.5 to 2.0; used belt × 0.7 to 0.8 | new | change 2 needs it | ±3 mm of tensioner travel is ample: 107 N on a 737 mm, 12 mm belt stretches it 2.3 mm in total at 33.8 kN |
| Minimum pulley | 20 teeth used | stock sprockets from 12 grooves; inside idler sprocket 12 grooves; flat backside idler 12.7 mm OD; flat inside idler 25.4 mm OD (Table 9, p.68); 6 teeth in mesh and 60° wrap on loaded sprockets | 20 teeth is fine. A smooth 12 mm idler on the tooth side would be under the minimum | keep idlers toothed, as the catalogue SKU says (the community CAD shown for `gt2_idler` is a smooth one) | none |
| Tooth-jump torque | not modelled | **no number**; p.10 says only that GT3 resists it better and allows lower tension | — | — | — |
| Belt mass | not modelled | not printed. Derived from the mass constant M (0.026 / 0.039 / 0.059 / 0.078, p.65) and the centrifugal formula (p.104): 4.0 / 6.1 / 9.2 / 12.1 g/m | new | none | a 737 mm, 12 mm belt weighs 9 g |
| Belt thickness, width tolerance | 6 mm belt drawn in pulleys with +1 mm face | 1.52 mm overall (Table 15, p.72); width +0.4 / −0.8 mm to 11 mm wide, ±0.8 above (Table 13) | — | — | — |
| Temperature | — | 85 °C maximum for stock belts (p.61) | — | relevant only to an enclosure | — |
| 20-groove pulley, 6 mm (`gt2_pulley(20, 5, 6)`, `parts/__init__.py:287`) | tooth OD 11.97, flanges 14.97, hub 15.97 × 6.0, length 15.0, belt centre 10.5, bore 5 | 2MR-20S-06 (p.29): pitch dia 12.73, OD 12.22, flange 17.40, face 7.37, length 15.88, hub 9.25 × 5.99, **plain bore 4.76 only**, 2 × 4-40 set screws, aluminium | OD +0.25, flange +2.4, length +0.9, belt centre about 10.9, slimmer hub, no 5 mm bore | none to the shape: ours is the generic 5 mm bore part with a 16 mm hub, a different product | none |
| Same, 9 mm (`GT2-20T-B5-W9`, v6 X) | length 18.0, belt centre 12.0 | 2MR-20S-09 (p.30): face 10.41, length 19.05, belt centre about 12.5 | length +1.05 | none | none |
| Face width over belt width | +1.0 mm | +1.0 mm flanged, +3.0 unflanged; flange height 1.1 minimum, 1.5 nominal (Tables 22, 23, p.78) | agrees (our flange is 1.5) | none | none |
| Part numbers | `GT2-20T-B5`, `GT2-20T-B5-W9`, `GT2-IDLER-…` | sprocket `2MR-20S-06`, `2MR-20S-09`; long-length belting `LL2MGT06`, `LL2MGT09`; endless: pitch length, `2MGT`, width code 04 / 06 / 09 (p.14, p.15, p.59) | ours are catalogue-internal names | none | — |

Not in the manual: a modulus curve against tension, hysteresis or damping, a tooth-jump torque, belt mass as a printed
figure, anything for 12 mm in 2 mm pitch.

## 4. StepperOnline motor datasheets

Both are one-page drawings with a specification table. **Neither has a torque-speed curve, a detent torque or a
weight.** The curves in use stay the separately published `_Torque_Curve.pdf` files.

### 17HS13-0404S1 (drawing A0581 rev 0, 2.27.2026) against `nema17(34)`

The catalogue records the 34 mm motor as 17HS13-0404S, from the 10.30.2020 drawing. **S and S1 are the same motor.**

| Quantity | Catalogue (17HS13-0404S) | S1 sheet | Difference |
|---|---|---|---|
| Current, resistance, inductance | 0.40 A, 30.0 Ω, 37.0 mH | 0.40 A, 30.00 Ω ±10 % at 25 °C, 37.00 mH ±20 % at 1 kHz | none |
| Holding torque, step | 0.26 N·m, 1.8° | 0.26 N·m, 1.8°, ±5 % | none |
| Rotor inertia | 35 g·cm² (S sheet) | blank | S1 sheet does not give it |
| Mass | 230 g (product page) | blank | — |
| Frame, body | 42.3 max, 34 max | the same | none |
| Mounting | 4 × M3 on 31 ±0.2, 4.5 deep minimum | 31 **±0.1**, 4.5 minimum | tighter tolerance |
| Pilot | Ø22 +0 / −0.05, 2 high | the same | none |
| Shaft | Ø5 +0 / −0.012, 20 ±1, flat 15 long at 4.5 ±0.1 | the same; flat length ±0.2 (S: ±0.25) | tolerance only |
| Leads | 300 ±10 mm bare | **1000 +20 / −10 mm, UL1007 AWG24, connector HX25402-4Y**, three cable ties | the S / S1 difference |
| Temperatures | — | ambient −10 to 50 °C, class B 130 °C, rise 80 K maximum, 100 MΩ, 500 VAC 1 min, MTBF 6000 h at 24 V / 300 rpm | new, not used |

Proposed: none (optionally name the part 17HS13-0404S1 with a 1 m lead in the BOM). Effect: none.

### 17HS19-2004S1 (drawing A0842 rev 0, 8.1.2025) against `nema17(48)`

| Quantity | Catalogue (10.30.2020 drawing) | 2025 drawing | Difference | Effect |
|---|---|---|---|---|
| Resistance | **1.40 Ω** (`stepperonline_nema17.json`); `MOTOR_ELECTRICAL` in `parts/electrical.py:351` has 1.6 | **1.60 Ω ±10 %** | +14 %; agrees with the product page | change 7 |
| Current, inductance, torque, inertia | 2.0 A, 3.0 mH, 0.59 N·m, 82 g·cm² | the same | none | — |
| Dimensions | 42.3, 48 max, 31 ±0.2, Ø22 × 2, Ø5 × 24 ±1, flat 15 ±0.25 at 4.5 | the same | none | — |
| Leads | 1000 ±15, 4-pin 2.54 mm connector | the same ("Harwin connector") | none | — |
| Shaft load | none recorded | "COMMENT: LENGTH 20mm: 21N MAX" | new | change 2 |
| Connection | bipolar | header cell prints "UNIPOLAR"; four leads and a bipolar table | a drawing slip | none |

The shaft-load line is not labelled further. Read here as the maximum radial force, 21 N at 20 mm from the mounting
face. No verifier compares belt pull with it, and belt pretension is not in the model. In v6 the Y belt runs about
16 mm from the motor face on a pulley carried by the motor shaft alone. Twice Gates' minimum tension for a 12 mm belt
is 37 N; twice its general value is 214 N. The 34 mm X motor's sheet has no such line. Typical printers do run NEMA 17
shafts above this figure; the drawing nevertheless states it.

Also seen, outside these documents: `MOTOR_ELECTRICAL["NEMA17-60"]` has a holding torque of 760 N·mm against 650 in the
catalogue (the product page's text figure against its drawing).

## 5. MH2025-5-8 coupler

Drawing A1917, 10.26.2026, one page: an outline with four dimensions.

| Quantity | Now, and where | Drawing | Difference | Effect |
|---|---|---|---|---|
| OD, length, bores | 20, 25, 5 and 8 (`stepperonline_coupler.json`, product page) | 20, 25, Ø5, Ø8 | none | — |
| Angular misalignment | 1.0°, `parts/__init__.py:383`, `angular_misalignment_assumed: True` | **not given** | — | stays assumed. v5 and v6 need 0.85° (99th percentile, `report.json`), v4 0.70°: a 15 % margin on an assumed number |
| Parallel and axial misalignment | not modelled | not given | — | — |
| Torque 2.8 / 5.6 N·m, 55 N·m/rad, 17,000 rpm, 17 g | product page | not given | — | stay product-page values |
| Clamp screw | not recorded | drawn (one tangential cap screw per hub), no size | the STEP file names it M3-10 | — |

The drawing answers none of the questions asked of it. Typical jaw couplings of this size are rated about 1° angular
and 0.1 to 0.2 mm parallel; that is recollection, not this document. The STEP file adds something the drawing does not
(change 4): bore depth.

## 6. MIC-6 and ATP-5

**MIC-6** (`MIC6_datasheet.pdf`, United Performance Metals, 2 pages): page 1 has the description, an empty composition
table and the applications list; page 2 has the headings "Physical Properties" and "Mechanical Properties" with nothing
under them. No image, no hidden text. The page was saved before its tables loaded. `MATERIALS["al_mic6"]` (2800 kg/m³,
71,000 MPa, 0.33, 105 MPa; `model.py:40`) is neither confirmed nor contradicted. v6's bed is this material.

**ATP-5** (`ATP5_datasheet.pdf`, Vista Metals, values on p.2, "typical"):

| Quantity | Now, and where | Sheet | Difference | Proposed | Effect |
|---|---|---|---|---|---|
| Density | 2660 kg/m³, `model.py:41` | 2660 kg/m³ (0.096 lb/in³) | none | — | — |
| Modulus | 70,300 MPa | 70,000 MPa (10.1 Msi) | −0.4 % | change 9 | none (unused) |
| Yield / tensile | 124 MPa / 283 MPa (JSON) | 124 MPa (18 ksi) / 283 MPa (41 ksi) | none | — | — |
| Elongation, hardness | not recorded | 12 to 15 %, 70 HB | new | — | — |
| Expansion | 23.8e-6 /K, `fea.py:26` and JSON | 23.6e-6 /K at 20 to 100 °C; 24.2e-6 at 101 to 200 °C | −0.8 % | change 9 | none (unused) |
| Thermal conductivity | not recorded | 140 W/m·K | new | available to a bed thermal model | — |
| Specific heat, Poisson's ratio | 0.33 | not given | — | — | — |
| Flatness | tolerance model: "machined" 0.02 mm | guaranteed 0.127 mm above 12.7 mm thick, **0.381 mm at 12.7 mm and under** | 6 to 19 times looser for stock as supplied | change 8 | no pass / fail change expected |
| Thickness | beds are 6.0 mm | 6.35 to 101.6 mm, ±0.127 mm; "imperial and metric sizes"; no list of stock thicknesses | 6.0 mm not shown | change 8 | buying note |
| Alloy, finish | — | AA 5083, 20 RMS maximum, machined both sides, film both sides | — | — | — |

## 7. STEP files: first inspection (not integrated)

Loaded with the project's own CAD kernel, read-only. Sizes in mm, volumes in mm³. All six are valid solids.

| File | Solids | Bounding box | Volume | What it contains | Against the catalogue part |
|---|---|---|---|---|---|
| `17HS13-0404S1.step` (SolidWorks 2014, 2018) | 1 | 42.32 × 60.31 × 53.0 (frame 42.32 square; the 60.3 includes lead stubs) | 57,479 | Whole motor as one solid, four lead stubs Ø1.15 × 20 mm leaving a 7 × 4.3 mm grommet 3.6 to 7.9 mm from the rear face. No connector, no cable, no screws | Body 33.0 long (drawing and catalogue: 34 max). Pilot Ø22.0 × **1.5** (drawing 2.0). Shaft Ø5.0, 20.0 above the face, flat 15 long at 2.0 from the axis: agree. Holes Ø2.5 on a 31.0 square, 4.5 deep: agree (tap drill drawn). The catalogue solid carries a 5.7 × 17.2 × 8 connector block from the community model; this motor has a small lead exit instead, on one side at the rear. File frame: rear face at Z 0, shaft +Z (the catalogue has the mounting face at Z 0) |
| `17HS19-2004S1.step` (SolidWorks 2014, 2018) | 1 | 42.32 × 60.31 × 72.0 | 82,848 | The same, 48 mm body | Body 48.0, pilot Ø22 × 1.5, shaft Ø5 × 24.0, flat 15, holes on 31.0, 4.5 deep: agree except the pilot height. File frame: mounting face at Z 0, shaft towards −Z |
| `COUPLER-5x8.step` (header MH2025-5-8.STEP, SolidWorks 2016, 2023) | 5 | 20.0 × 20.0 × 25.1 | 6,416 | Two clamp hubs (MH20-8: 2,426; MH20-5: 2,205), elastomer spider (1,539; OD 18.3, 10 long, 7 mm centre hole), two M3 × 10 cap screws (123 each) | OD 20.0 and length 25.1 agree. Bores Ø8.0 and Ø5.0 are each **7.3 mm deep**; the catalogue solid has 12.5 mm bores (change 4). Mass from volumes about 16 g (page: 17 g). Axis is not at the file origin (−1.38, −0.01; Z 3.16 to 28.26) |
| `E3D_Roto_Sensored_reference.step` (REVO-ROTO-24V-SENSOR-AS-REFERENCE, 2024-01-24) | 12 | 56.23 × 78.33 × 57.11 | 70,492 | The plain Roto reference (same 11 solids, identical positions and volumes: gearbox cover, heat sink, ring gear, fan, idler, motor, hot side, four screws) **plus one solid, ROTO-FILAMENT-SENSOR-REFERENCE** | Same overall box as the plain Roto already in `vendor_cad/`. The sensor is 20.75 × 24.59 × 17.9 (3,858 mm³) on the filament entry: in the file frame Y 52.35 to 76.94, which is 18.8 to 43.4 mm above the lower mounting hole in the catalogue frame. The plain body top is at 27.05, so the sensor stands 16.3 mm above it, inside the height already taken by the idler lever (44.15). `extruder_roto()` would need the extra solid, a higher filament entry and a sensor connector; no change to mounting holes or nozzle position |
| `E3D_Roto_Bowden_reference.step` (REVO-ROTO-COLDSIDE-BOW-AS, 2024-01-24) | 15 | 56.23 × 70.43 × 53.48 | 59,519 | Cold side for Bowden use: gearbox cover, heat sink, ring gear, idler, motor, four screws (the two button-heads 5 mm shorter than on the plain Roto), **no fan and no hot side**; instead three thin washer pieces where the fan sat, and a Bowden adaptor, collet and clip under the heat sink | Against the plain Roto: 3.6 mm thinner on the fan side (screw heads end at 10.8 instead of 16.2), nothing below the heat sink but the adaptor (Ø9 × 11.6, with collet and clip down to 14.9 mm below the hot-side seat; no nozzle). A different product from the one v6 uses; not needed unless a Bowden design returns |
| `E3D_Revo_Voron_reference.step` (Revo Voron Reference CAD, SolidWorks 2021, 2022) | 1 | 33.24 × 48.8 × 27.16 | 6,533 | A complete Revo Voron hotend as one fused solid: finned heat sink (fins Ø14.8 to Ø18, top flange Ø18 with **four Ø2.5 tapped holes on an 8.5 × 10 mm rectangle**, 4.1 mm inlet for PTFE), HeaterCore Ø16.7, nozzle block Ø13, nozzle, and two lead stubs (Ø4.5 sleeve, Ø2.4) running 25 mm out to one side | Origin on the nozzle seat, tip at −22.8: the same 22.8 mm seat-to-tip and Ø16.7 HeaterCore as `hotend_revo()`. Adds the heat sink (26.0 above the seat; 48.8 tip to top) and the lead exit, which the catalogue's hot side takes from a scaled drawing. It is the hotend for a toolhead with a separate extruder, not for the Roto, which has its own heat sink |

Is `COUPLER-5x8.step` (3.9 MB) a sensible single part? It is a small, clean five-solid assembly: 359 faces, about as
many as either motor. The size comes from spline edges stored with very many points (22,383 points in the file, against
3,247 in the 1.2 MB motor), not from threads or a heavy mesh. It does not need defeaturing. It needs fusing into one
solid (or the two hubs and spider kept and the screws dropped) and moving onto the catalogue frame; re-exported that
way it should fall well under 1 MB.

For integration later: the two motor files and the coupler would replace community CAD and a proxy with vendor CAD. The
motor files show that the connector block now in the `nema17` simulation solid is not on these motors.

## What the documents did not contain

- Hiwin: rigidity for the ZF (clearance) class; lateral and moment rigidity; ball-track length; friction.
- Wang 2018: belt width, maker, grips, temperature; hysteresis; any second width; behaviour under a held pretension.
- Gates: stiffness against tension beyond one point; tooth-jump torque; printed belt mass; 12 mm belts or sprockets in
  2 mm pitch; a 5 mm bore 20-groove sprocket.
- Motor sheets: torque-speed curves, detent torque, weight; rotor inertia for the 17HS13-0404S1; a shaft-load figure
  for the 34 mm motor.
- Coupler drawing: angular, parallel and axial misalignment, torque, stiffness, speed, clamp screw size.
- MIC-6: everything (empty tables).
- ATP-5: specific heat, Poisson's ratio, stock thickness list.

---

# Second and third batch (added later on 2026-11-15)

Four more PDFs, one STEP file and three Zenodo folders arrived in `mech-ai/vendor_cad/staging/` (MANIFEST.md, "Batch 2"
and "Batch 3"). Same rules as above: read as data only, nothing a design depends on was changed, numbers added as
labelled blocks. `tests/test_vendor.py` passes (44 tests). Effects are again hand arithmetic from the stored reports.

Added:

- `mechloop/parts/vendor/omron_d2f.json` (new; nothing reads it) and `vendor_docs/ENDSTOP-MICRO_datasheet.pdf`
- `mechloop/parts/vendor/raspberry_pi_zero2w.json` (new; nothing reads it) and `vendor_docs/HOST-RPI-ZERO-2W_datasheet.pdf`
- `meanwell_lrs.json`: block `parts.350.staging_copy_2026_11_15`
- `bigtreetech_skr_mini_e3_v3.json`: block `staging_copy_2026_11_15`
- `hiwin_mgn12.json`: block `community_step_second_copy`
- Zenodo members of type CSV and G-code extracted to
  `/tmp/claude-0/-home-user-running-route/87481e0a-8f62-5246-a6fc-1c1f80e15b45/scratchpad/agentDocs/` (84 files; nothing
  extracted into the repository; no member had an absolute or `..` path)

**Two of the four PDFs are files we already had.** `SKR_Mini_E3_V3_drawing.pdf` is byte-for-byte
`vendor_docs/BTT_SKR_MINI_E3_V3.0_SIZE_20220301.pdf`, and `LRS-350-24_datasheet.pdf` is byte-for-byte
`vendor_docs/LRS-350-SPEC.PDF` (same SHA-256). They were re-read, not copied again. `MGN12H.step` is the same geometry
as the model already in use.

## Answer in brief

| Document | Headline | Against what we assume |
|---|---|---|
| Omron D2F | Hinge-lever models: **operating position 6.8 ±1.5 mm** above the mounting-hole line, free position 10 mm maximum, overtravel 0.55 mm minimum, movement differential 0.5 mm maximum, operating force 0.78 N maximum (0.25 N low-force) | **Contradicts the catalogue.** The recalled "operating position 10 ±1" is really the free position. The catalogue's trigger point is 2.2 mm too far out, and above the highest operating position any D2F-L can have |
| SKR Mini E3 V3 drawing | Same file as before. Outline 103.75 × 70.25, five holes; re-read gives the same five positions | Confirms the catalogue part. Hole diameter and connector positions are not dimensioned |
| LRS-350 | Same file as before. 14.6 A, 88 %, 60 A inrush, 100 % to 50 °C then 60 % at 70 °C, fan on at 50 °C | Confirms every figure the code uses. Not modelled: 2 mA leakage, derating below 100 VAC, the EN 61000-3-2 note |
| Raspberry Pi Zero 2 W | 65 × 30 mm, holes 3.5 mm from each edge (58 × 23), "5V DC 2.5A" input, −20 to 70 °C | Confirms size and hole pattern. **No current-draw figure**: the 0.60 A in the 5 V budget stays unverified |
| `MGN12H.step` | Identical to `vendor_cad/mgn12h_block.step` | Already the detail model; nothing to do |
| Zenodo 5747732, 22770610, 22716165 | Six Ender 3 Pros with per-layer RMS vibration; a shaker test of a loose bed plate; a fault-detection set that was not downloaded | **None is the missing commanded-motion-plus-response data set** |

## Proposed changes from this batch (continuing the numbering; none applied)

| # | Change | Where | Expected effect |
|---|---|---|---|
| 12 | Endstop trigger: 9.0 → 6.8 mm above the switch's mounting-hole line (Y 10.6 → 8.4 in the part frame), with the tolerance ±1.5 recorded; `pretravel` and `overtravel` restated from the sheet; movement differential 0.5 mm added | `parts/details.py` `ENDSTOP["operate_y"]`, hence `endstop_switch().interfaces` | **`endstop_not_reached` on X and Y in printer_v4, v5 and v6, and on Z in v4**: every striker is drawn to stop exactly on the old trigger (gap 0.0 mm), which would be 2.2 mm short of the nominal operating position; the check fails above 1.0 mm. The fix in each design is to move each switch 2.2 mm towards its striker (`ES_TRIG` 10.6 → 8.4). Until then a real machine homes 2.2 mm (0.7 to 3.7) further than drawn, if the axis has that travel. v5 and v6 home Z on the probe and are not affected there |
| 13 | State which D2F: a gold-contact D2F-01L type for a logic-level endstop. The general D2F needs 100 mA at 5 V as a minimum load; D2F-01 needs 1 mA | endstop `source` text and BOM | None on checks. A general-purpose D2F on a 3.3 V input with a pull-up is outside Omron's operating range |
| 14 | If an Omron right-angled switch on a carrier board is really what is bought: terminal row 2.8 mm below the body bottom (catalogue 0.9), 1.5 mm through the board (catalogue 2.62) | `ENDSTOP["pins"]`, `["pins_z"]` | The three 2.5 mm clearance holes under each switch in v4 to v6 would be 1.9 mm off the pins. Only matters once the bought module is known; the board itself is still a generated one |
| 15 | Leakage current 2 mA at 240 VAC and the input-voltage derating (80 % at 90 VAC) as PSU ratings | `parts/electrical.py` `psu_lrs` | None at 115 / 230 V. Lets an earth-leakage or brown-out check exist. Loads are 72 to 75 % of rating, so even the 80 % figure is not reached |
| 16 | Pi: record −20 to 70 °C as the host's ambient limit; keep 0.60 A flagged unverified | `raspberry_pi_zero2w()` | The bay temperature check gains a limit for the host. No number moves |

Change 12 is the only item in either batch that would turn a passing check into a failing one on its own.

## 8. Omron D2F data sheet (`ENDSTOP-MICRO_datasheet.pdf`, 6 pages)

Recorded in `omron_d2f.json`.

Variants covered (p.1, p.2): ratings D2F (3 A 125 VAC, 2 A 30 VDC), D2F-F (low force, 1 A), D2F-01 and D2F-01F (0.1 A
30 VDC, gold contacts), D2F-5 (5 A 250 VAC). Actuators: pin plunger, hinge lever (L), hinge roller lever (L2),
simulated roller lever R1.3 (L3) and R2.5 (L30). Terminals: straight PCB, self-clinching PCB (-T), right-angled PCB
(-A), left-angled PCB (-A1), solder (-D3), compact solder (-D).

Hinge lever, PCB terminals (D2F-L, D2F-FL, D2F-01L, D2F-01FL, D2F-5L), p.3 and p.4:

| Quantity | Sheet | Catalogue (`endstop_switch()`, `details.ENDSTOP`) | Difference |
|---|---|---|---|
| Body | 12.8 ±0.15 long, 6.5 ±0.1 high, 5.8 ±0.15 thick | 12.8 × 6.55 × 5.8 | agrees |
| Switch mounting holes | 2 × Ø2.0 (+0.12 / 0) on 6.5 ±0.15, 3.15 from the body end, centres 1.5 above the body bottom; M2 screws at 0.08 to 0.1 N·m | hole line 1.5 above the body bottom (Y 1.6); the part's own `mount_holes_m3` are two M3 holes at ±7.5 on a generated carrier board | the switch geometry agrees; the carrier board has no maker |
| Lever | stainless, 12.8 long, 0.3 thick, 3 wide; actuation point A 10.8 mm (reference) from the hinge-side hole, i.e. 7.55 mm from the body centre | lever tip 9.0 mm from the body centre (community model) | catalogue lever 1.45 mm longer |
| **Operating position** | **6.8 ±1.5 mm** from the mounting-hole line (5.3 to 8.3) | `trigger` 9.0 mm from the hole line, from a recalled "10 ±1, low limit used" | **catalogue 2.2 mm too far out; 0.7 mm beyond the sheet's upper limit** |
| Free position | 10 mm maximum | `lever_free` 9.99 mm | agrees with the maximum |
| Pretravel | not given for lever models (pin plunger: 0.5 mm max). Free position maximum minus operating position: 3.2 mm nominal, 1.7 to 4.7 | `pretravel` 0.99 mm | catalogue too small by about 2.2 mm |
| Overtravel | 0.55 mm minimum guaranteed | `overtravel` 3.95 mm (to the lever lying on the case) | the catalogue figure is geometric room from the wrong trigger; from the nominal operating position the case is about 1.5 mm away |
| Movement differential | 0.5 mm maximum | not recorded | new: the switch releases up to 0.5 mm above where it operated |
| Operating force | 0.78 N max (D2F-L, -01L, -5L); 0.25 N max (D2F-FL, -01FL); release 0.05 / 0.02 N min | not recorded | new |
| Terminals | 3 on 5.08 pitch, 0.9 × 0.4; straight: 3.5 below the body, PCB holes Ø1.2; right- or left-angled: legs 2.6 ±0.2 below the body bottom, 3.1 ±0.2 beyond the body face | `pin_holes` at X −5.08, 0, 5.08, row 0.9 mm below the body bottom, 2.62 mm below the board | X agrees; row 1.9 mm off and length 1.1 mm long for an Omron angled part |
| Ratings | contact gap 0.25 mm; minimum load 100 mA at 5 VDC (D2F, D2F-5) or 1 mA at 5 VDC (D2F-01); 1,000,000 mechanical operations; electrical 30,000 (D2F), 100,000 (D2F-01); lever speed 5 to 500 mm/s; −40 to 85 °C; IP40; bounce 1 ms max under the stated shock and vibration | endstop template: JST-XH, 1 A, 3 conductors | new; change 13 |

How far off the recalled values were: the body and pin pitch were right; the operating position was wrong by 3.2 mm at
nominal (10 against 6.8) because the free position was remembered in its place, and using its "low limit" reduced the
error in the catalogue to 2.2 mm. Lever models are rated for operating speeds of 5 to 500 mm/s; the designs' homing speeds were
not checked against that here.

## 9. SKR Mini E3 V3.0 SIZE drawing (same file as already stored)

| Quantity | Catalogue (`skr_mini_e3_v3()`, `control_board()`) | Drawing | Difference |
|---|---|---|---|
| Outline | 103.75 × 70.25 | 103.75 × 70.25 | none |
| Holes, from the bottom-left corner | (23.39, 67.03), (85.55, 67.23), (5.53, 32.05), (37.34, 29.41), (101.22, 2.56) | printed as 23.39 / 3.22 from top, 18.20 from right / 3.02 from top, 5.53 / 32.05, 37.34 / 29.41, 2.53 from right / 2.56: the same five points | none |
| Hole diameter | not recorded | not dimensioned; scaled from the drawing about 3 mm in a pad of about 6 mm | — |
| Connector positions | from the pin drawing and vendor STEP | not dimensioned, apart from four figures at the micro-SD / micro-USB edge (2.79, 16.49, 21.88, 30.26) | — |

**Are the holes the designs use in the right place?** printer_v4, v5 and v6 all place `skr_mini_e3_v3()` on the tray
and take the five hole positions from the part, and the part's positions are exactly the drawing's. So yes, against
this drawing. The open question is the one already in `docs/VENDOR_CAD.md`, and this file cannot close it because it is
the same drawing: BIGTREETECH's own STEP model shows no holes at these five points and two 3.1 mm holes elsewhere.
A real board still has to be measured before the tray is drilled.

## 10. LRS-350-24 (same file as already stored)

| Quantity | Code (`parts/electrical.py` `_LRS`, `psu_lrs`; `verifiers/electrical.py`) | Sheet (page) | Difference |
|---|---|---|---|
| Output | 350.4 W, 14.6 A, 24 V | 350.4 W, 14.6 A, 24 V; adjustable 21.6 to 28.8 V; tolerance ±1 %; ripple 150 mV p-p (p.2) | none |
| Efficiency | 0.88 | 88 % typical | none |
| Input current | 6.8 A at 115 V, 3.4 A at 230 V | the same, typical | none |
| Inrush | 60 A | 60 A typical at 115 and 230 V, cold start | none |
| Derating with temperature | 100 % to 50 °C, 60 % at 70 °C | the same, horizontal mounting (p.3) | none |
| Derating with input voltage | not modelled | 100 % from 100 to 132 VAC and 180 to 264 VAC; falls to 80 % at 90 VAC (p.3) | new; change 15 |
| Fan | "built-in fan, on at 50 °C internal" | on at RTH3 ≥ 50 °C, off at ≤ 40 °C | none |
| Protections | not modelled beyond the fuse checks | overload 110 to 140 %, hiccup, auto-recovery; 150 % peak for 1 s; over-voltage 28.8 to 33.6 V; over-temperature hiccup | new, not needed by a check |
| Earth leakage | not modelled | under 2 mA at 240 VAC | new; change 15 |
| Hold-up | recorded, unused | 16 ms at 230 V, 12 ms at 115 V | none |
| Dimensions, mounting | 215 × 115 × 30; 4 × M4 on 150 × 50, 3 mm screw depth; terminals pitch 9.5 | the same (p.4); side holes 4 × M4 each side, 5 mm depth, 12.5 above the base | none |
| Mass | 0.76 kg | 0.76 kg (packing line) | none |
| Mains harmonics | not mentioned | note 10: does not meet EN 61000-3-2; not for EU end devices above 75 W average input on public mains | a compliance note for a machine sold in the EU, not a check |

Loads in the stored reports: 72 % (v4, v5) and 75 % (v6) of rating against the 85 % limit; nothing moves.

## 11. Raspberry Pi Zero 2 W (`HOST-RPI-ZERO-2W_datasheet.pdf`, product brief, April 2024)

| Quantity | Catalogue (`raspberry_pi_zero2w()`, `parts/electrical.py:225`) | Brief (page) | Difference |
|---|---|---|---|
| Board | 65 × 30 | 65 × 30 (p.3, p.4) | none |
| Holes | four on 58 × 23, drilled 2.8 | centres 3.5 from each edge, so 58 × 23 (p.4); diameter not given | pattern confirmed |
| Supply | 3.0 W, i.e. **0.60 A at 5 V**, "about, under load", unverified | "Input power: 5V DC 2.5A" (p.3) | not comparable: 2.5 A is the recommended supply, not the draw |
| Supply tolerance, typical and peak current | — | **not in the document** | — |
| Operating temperature | none | −20 to +70 °C (p.3) | new; change 16 |
| Connectors | header along +Y | header footprint along the top edge (unpopulated); mini HDMI, USB and power centres at 12.4, 41.4 and 54 mm from the left edge | agrees |

The 5 V budget is unchanged: v6 draws 0.74 A (0.60 host, 0.14 fan) against 0.88 A allowed on the board's 1.1 A fused
rail; v4 and v5 draw 0.60 A. The margin for the Pi's own peaks is 0.14 A in v6, and this document does not say whether
that is enough. The Pi's power figures by state are on Raspberry Pi's documentation site, not in this brief.

## 12. `MGN12H.step` (step.parts)

One solid, 28 faces, 9,481.2 mm³, box 27.0 × 10.0 × 45.4 with the body 3.0 to 13.0 above the rail base; four Ø3.0 holes
on 20 × 20, 3.5 deep; two Ø1.5 ball rows at ±6.0. **Every one of these numbers is identical to
`vendor_cad/mgn12h_block.step`**: it is the same FreeCAD-library model with a step.parts header.

- Against Hiwin Table 3.79: W 27, L 45.4, H 13, H1 3, B 20, C 20 and thread depth 3.5 all agree.
- Not drawn: end caps (so L1 32.4 is not in the model), the oil hole, H2, threads.
- Good enough to be the detail model, kind "community CAD"? Yes, and it already is. Alignment is the existing one in
  `details.mgn12h`: length along file Z from 0 to 45.4, so rotate (90, 0, 90) and shift −22.7 along the rail.
- Nothing to integrate. SOURCES.txt says the step.parts page states no licence; the FreeCAD-library copy in use is
  CC-BY 3.0, so keep that one.

## 13. The Zenodo data sets

`Datasets and models for fitting the twin.md` says what is missing: commanded motion together with the measured
response on a machine whose masses and belt lengths are known.

| | 5747732 "Federated learning dataset" | 22770610 "Printer-bed dataset" | 22716165 "Data acquisition and fault detection" |
|---|---|---|---|
| In staging | description PDF, `GCode.zip` (12 files), `RMS Acceleration by Layer.zip` (72 CSV), `Figures.zip` (2 JPG) | `measured_signals.zip` (7 HDF5, 1.6 MB each), `calibration.zip` (51 JPG of a 7 × 5 checkerboard, 20 mm squares) | a README only |
| Left out | `Raw Acceleration Data.zip`, 90.6 MB | two high-speed-camera archives, 9.3 GB and 8.5 GB | 26 parquet files, about 1.05 GB |
| Machine | six Creality Ender 3 Pro, assembled from kits | a printer bed plate hung free ("suspended"), not a machine | per the README title and file names: a printer printing Benchy under eight conditions (healthy, two temperatures, loose head, four nozzle sizes). Nothing else could be read |
| Sensors, rate | two ADXL345, one on the extruder (X), one on the bed (Y), read by a Raspberry Pi at "around 200 Hz" | force and accelerometer channels and a trigger, logged by a data-acquisition task; high-speed camera | not known from what is here |
| Commanded motion | Cura 4.8 G-code: a 20 × 20 × 3 mm square, 15 layers of 0.2 mm, air-printed, a 5 s pause between layers, speed settings 10 to 120 mm/s | none: a shaker test, sweep and random | G-code of a Benchy, not in the folder |
| Is the command paired with the measurement? | The G-code that was run is given. The raw time histories (time, X, Y) are in the archive that was left out. What is here is one RMS value per layer per axis | force in, acceleration out: a paired input and output, but for a plate, not for motion | unknown |
| Masses, belts, firmware limits | **none given.** The G-code sets no acceleration or jerk, so the firmware's values are unknown | not applicable | unknown |

First look at 5747732 (all 72 CSV and two G-code files):

- Each CSV has 15 rows: layer, mean speed, RMS X, RMS Y. The "mean speed" is path length over Cura's own time
  estimate, not a measurement. It saturates: settings 10, 60 and 120 mm/s give 9.7, 39.8 and 40.7 mm/s, because a
  20 mm side is too short to reach speed under whatever acceleration Cura assumed.
- RMS acceleration (unit not stated, presumably m/s²) rises from about 0.5 to 0.6 at the slowest setting to 0.9 to 1.1
  at the fastest on five printers. So the lowest values are close to a noise floor, and the whole usable signal is a
  factor of two.
- Printer 5 reads 1.0 to 1.8 on X throughout, about 1.7 times the others: one unit is clearly different (or its
  sensor is). Y is alike on all six.
- G-code: 2,609 lines at the 120 setting, feed rates up to F7200, no M201 / M204 / M205.

Judgement:

- **5747732 is not the missing data set.** The part in hand (RMS per layer) carries no time or frequency information
  and can fit no twin parameter. Its one honest use is the one the earlier report gave it: unit-to-unit spread at a
  fixed design, here about ±10 to 12 % in RMS among five machines, with one outlier. The 90.6 MB raw archive would add
  time histories, but at about 200 Hz from a Pi: the Ender's toolhead and bed resonances (about 50 and 45 Hz in the
  calibration study) are below the 100 Hz limit, yet the sampling is irregular, the accelerometer clock is not tied to
  the G-code, and the machine's acceleration setting, masses and belt tension are not given. A resonance frequency per
  printer and axis could probably be read from the ringing after each corner; that would add up to twelve
  more Ender 3 frequencies of the kind the calibration study already has from better data. Effort about a day;
  value low. Worth fetching only for the spread between six nominally identical machines.
- **22770610 is a real input-output data set, of the wrong thing.** A free plate on a shaker gives the plate's bending
  modes and their damping. The twin has no parameter for bed-plate modes; its bed is a rigid mass on the Y drive. It
  could check the FEA's material damping or a plate-mode calculation for a bed like v6's, not the motion model. The
  HDF5 files could not be opened here (no HDF5 reader is installed and nothing may be installed); a look at the raw
  bytes shows `sample_rate`, `channel_names`, `force` and `trigger`. With a reader, extracting two or three mode
  frequencies and damping ratios from the 11.5 MB of signals is half a day. The 17.8 GB of camera frames are not
  needed for that.
- **22716165 cannot be judged**: only the README is here. By its description (accelerometer on a printer printing
  Benchy, healthy and faulted) it is again vibration without the commanded trajectory logged alongside, the same
  limit the earlier report found in the other fault-detection sets. The "loose head" runs could give a signature for
  the twin's slack-carriage case. Fetching one healthy and one loose-head file (about 40 to 80 MB each) would settle
  what it contains; all 26 are not needed for a first look.
- The gap stays open. The cheapest way to close it is still the one in the earlier report: Klipper's `motan` logger on
  one machine whose masses and belts are measured.

## What this batch did not contain

- Omron: a pretravel figure for lever models; the carrier board (no maker's drawing exists for the generic module).
- SKR drawing: hole diameter, connector positions, board height, mass. It is the file we already had.
- LRS-350: nothing new beyond the items listed as not modelled. It is the file we already had.
- Raspberry Pi: supply tolerance, typical and peak current, hole diameter, heights, mass.
- Zenodo: machine masses, belt data and firmware acceleration settings in every set; raw time histories (5747732),
  camera data (22770610) and all measurement files (22716165) were not downloaded.
- SOURCES.txt does not yet list the four batch 3 PDFs, so their download addresses are not recorded.
