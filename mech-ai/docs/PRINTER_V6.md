# printer_v6: direct drive on the rail, a probe that triggers in time, fewer parts

Everything here is simulated. Nothing has been built.

`designs/printer_v6.py` starts from `designs/printer_v5.py`. It passes all 12 verifiers (0 errors, 8 warnings,
full run of 2026-11-15 03:38 to 03:52 UTC, against the Roto and Revo solids rebuilt from E3D's reference CAD).
The designer worked from findings, hints, documents, the parts catalogue and the public helpers of
`mechloop/electrical.py`. The verifier, tolerance and twin sources were not read.

## The stated target, line by line

A 180 x 180 x 180 mm open-frame demonstration printer whose every purchased part is off the shelf and every
fabricated part is printed, laser-cut or a single-set-up plate.

| Target | Result | Met |
|---|---|---|
| 180 x 180 x 180 mm | travel 180 x 180 x 183 (180 above home, 3 below); nozzle 0.10 mm above the bed at the top | yes |
| every fabricated part printed, laser-cut or a single-set-up plate | 7 printed, 11 laser-cut, 2 plates machined in one set-up each (bed, tool plate) | yes |
| parts cost + fabrication estimate <= $900 | $719 parts + $129 fabrication ($112 machining, $15 cutting, $2 filament) = **$848** | yes |
| <= 320 parts | **317** | yes |
| assembly estimate <= 65 min | **SCORE_ASM min** | SCORE_ASM_MET |
| direct drive, <= 0.40 kg moving in X | E3D Roto + Revo on the X guide block, **0.351 kg** with the block | yes |
| both Y belts within 1 mm of plane in >= 98 % of builds | 98.4 % and 98.7 % in the final run; over 14 runs of the final geometry and its near variants the right belt was 97.9 to 98.7 %, the left 98.7 to 99.1 % | yes at the mean, **no margin**: the right belt's figure is within the simulation's own scatter (about +/-0.3 %) of the limit |
| a bed probe that works across the whole print area | switches 0.88 to 1.52 mm before the nozzle touches for every unit in its +/-10 % spread; reaches 148 x 174 mm of the 180 x 180 mm | **no**: a 32 mm strip at high X and a 6 mm strip at high Y are not probed |
| no stand-in purchased part where the catalogue has a real one | one hand-made purchased part is left, the bed probe; the catalogue has no probe | yes |

Why the probe line is not met. The Roto is 57 mm wide and its fan draws air in on the left face, its motor is on
the right, the tool plate is in front and nothing can be bolted on behind. The nearest place an 18 x 18 x 36 mm
inductive sensor fits without sitting in the fan's intake or beside the 250 degC HeaterCore is 32 mm to the left of
the nozzle. Covering the last 32 mm would take 32 mm more X travel on one side: a 300 mm X rail, a bed 250 mm wide
(or a print area 16 mm off the bed's centre, outside the heater pad). That is bending the machine for a number.
Klipper holds the nearest measured value in the strip, so a bed that is flat there (MIC-6 plate) prints correctly;
a tilted one is 0.05 mm off at the edge per 0.3 mm of tilt across the bed. v5's strip was 33 mm.

## What changed from v5, and why

### 1. Direct drive: E3D Roto and Revo

`extruder_roto()` (140 g with motor, heat sink and fan) and `hotend_revo(40, 24.0, 0.4)` (17 g) replace the
frame-mounted extruder, the PTFE tube, the proxy hotend, the heater and thermistor cartridges and the 30 mm
heat-sink fan. What the vendor notes asked for:

- **5 V fan.** The Roto's fan is an `embedded_device` of the extruder (5 V, 0.14 A, E3D's figures) wired to the
  control board's always-on 5 V pins (`add_board_5v_port`). It runs whenever the machine is on. 0.82 W, inside the
  board's 5 V budget with the Pi. No regulator board (it would be one more part that is not in the catalogue).
- **Gear ratio.** The firmware block gives no `rotation_distance`; the generated `[extruder]` has
  `rotation_distance: 26.8937`, `gear_ratio: 11.262:1`, `full_steps_per_rotation: 400` from the part. Run current
  0.40 A rms (E3D: 0.318 to 0.424).
- **Geometry.** Every toolhead part is placed from the Roto's interfaces (`nozzle_tip`, `mount_holes_m3`,
  `hotend_seat`), so the design followed the catalogue's change from the drawing envelope to the CAD-based solid
  without edits. Clearances kept: 6.8 mm between the probe and the fan's screw heads, 0.75 mm under the body to the
  fan carrier (the carrier is under the motor, not under the 7.4 mm boss on the nozzle axis), nothing in the corner
  where the motor's leads leave.
- **Wiring.** `device_from(el, d, "hotend")` is the heater, the thermistor is embedded in it. The HeaterCore's own
  115 / 130 mm leads are declared as pigtails. Their insulation is not in E3D's data; taken as glass-fibre sleeved.

### 2. Toolhead on the rail (requirement 6)

v5: rail on top of the beam, an 8 mm plate cantilevered behind it, a printed mount under the plate, the hotend
held by set screws. Nozzle 32.5 mm behind and 55 mm below the guide block's centre (64 mm away).

v6: the Roto bolts sideways through its body, so the X rail moved to the **rear face** of the beam. The guide
block's mounting face is then vertical: the block, one flat 8 mm plate and the Roto's flat side are a stack of
three faces, held by four M3x8 and two M3x45. No printed part and no overhanging plate carries the nozzle.

| | v5 | v6 |
|---|---|---|
| Nozzle behind the block's mounting face / below the block centre | 32.5 (behind the block centre) / 55 mm | 23.2 / 33.6 mm |
| Nozzle to block centre | 64 mm | 44 mm |
| Between block and nozzle | plate, printed ABS mount, two set screws | plate |
| Belt clamped | 21 mm in front of the block centre, on a printed block | 13 mm in front, on a printed block on the same plate |
| Moving in X | 0.360 kg | 0.351 kg |
| Nozzle stiffness X / Y, screw-only joints (FEA, block bonded to rail) | 1,747 / 1,201 N/mm | 1,435 / 2,036 N/mm |
| Twin's series stiffness on X with the block's tilt | (71.6 Hz after the refit) | 154 N/mm, 80.2 Hz |

The plate stayed 8 mm and machined: the block takes 3.0 to 3.5 mm of M3, and the Roto's M3x45 need 6.5 mm of
thread, which no sheet thickness gives without a counterbore. With the lighter Roto a thinner plate would carry
the load, but the plate is now 66 g of a 351 g toolhead and one set-up, so nothing is gained by thinning it.
The mass centre is the Roto's own, 19 mm behind the plate and at the block's height.

The X figure in the FEA is lower than v5's because the beam now hangs on one M5 per side under 3 mm steel plates
(section 5); the Y figure is higher because the nozzle is 21 mm closer to the beam's axis. The FEA models the Roto
as a solid aluminium block, which it is not, and bonds block to rail, so both figures are upper bounds; the twin
adds the block's tilt from the nozzle's distance, which is the term v6 shortened.

### 3. X drive

A rail on the rear face leaves the X belt nowhere to go in v5's place. The belt now runs in a vertical loop over
the beam. Motor and idler stand on two laser-cut 3 mm steel plates on the beam's front face, so one part (the
beam) locates both ends. They sit inboard of the Y guide blocks (pulleys at x = +/-118): the belt is 484 mm
(v5: 654 mm), the X motor no longer hangs outside the frame, and the left Y drive is the mirror image of the
right one. v5's belt tower, its clamp, three M3x40 and three nuts are gone. The belt ends fold back on themselves
in a slot of a printed block on the tool plate (teeth in teeth); no clamp bar, no clamp screws. Tensioner: the
idler plate slides on its two T-nut screws, pushed by an M3 jack screw in a printed anchor, as on the Y mounts.

### 4. Bed probe (requirement 2)

| v5 finding | v6 |
|---|---|
| `probe_trigger_margin`: switches 0.10 mm before contact; a short-range unit at -0.22 mm | sensing face 2.0 mm above the nozzle (v5: 3.1): 1.20 mm nominal, 0.88 to 1.52 mm over the +/-10 % spread |
| `probe_not_reached` | reached inside the Z travel by every unit in the spread |
| 33 mm strip at low X | 32 mm at high X and 6 mm at high Y: not fixed, see the target table |
| NPN on 24 V, pull-up unknown | a BAT85 diode in the signal lead whether or not the unit has a pull-up (`series_diode=True`, BOM line); the pin then only ever sees its own 3.3 V pull-up |
| rated 70 degC over a 100 degC bed | **open**. No inductive sensor with real data and a higher rating is in the catalogue; a BLTouch or a switch probe is not something the electrical model or the config writer can represent. Mitigation is procedural: probe at 60 degC, park the head off the bed while it heats further |

Same sensor class as v5 (hand-made part, recalled data). It is screwed straight to a tab of the tool plate with
two M3x25, not to a printed wall. **Z travel beyond the nozzle plane:** rail, blocks, screw and nut have 2 mm
beyond the nominal nozzle plane (a Requirement checks it: 9.3 mm of rail and 31 mm of screw left), and the
`z_offset` adjustment of 2.0 mm rests on that (1.63 mm needed at the 99th percentile). The Z joint's declared
range stops at the nominal plane; why is under "Checker behaviour", item 3.

### 5. Belt-plane scatter (requirement 4)

Six tolerance runs separated the causes in v5 (92.8 % / 92.7 %):

| Variant | Right / left belt within 1 mm |
|---|---|
| v6 with v5's printed clamp bars, 3.8 mm holes | 92.6 / 92.1 % |
| clamp holes 3.4 mm | 97.6 / 97.0 %, but the three screws start in 36 % of builds |
| clamp holes 4.2 mm | 83 / 84 % |
| **no clamp part: belt located by the Y plate itself** | 97.9 to 98.7 / 98.7 to 99.1 % |
| ... and machined motor and idler mounts | 98.9 / 99.2 % (not adopted: about $90 of machining) |
| idler spacer 3, 6 or 9 mm | no difference outside the scatter |

So the chain was shortened where it was loose: each Y belt end goes down through one laser-cut slot in its Y
plate, up through the next, folds back and is tied with a cable tie. The slots locate the belt; there is no part
with screw-hole play between belt and plate (2 clamp bars and 6 screws fewer). Three smaller steps: 3.5 mm
instead of 3.6 mm holes where the Y plates sit on their guide blocks (all four screws still start in 99.97 % of
builds), two bolts per motor mount instead of three, and a +/-1.5 mm slot for each beam bolt so the gantry, not
the Y rails, takes up the frame's width error.

The right belt stays about 0.5 % behind the left in every run. Removing the Y switch from the right idler mount
did not change that. The frame is built up from the left bottom rail, so the right side carries more of its
error; that is the likely cause and it was not pursued further.

### 6. Y plates in sheet, beam under the plates

v5 machined the two Y plates because the beam covered the guide blocks' screws (counterbores), and drove the beam
bolts from below through holes in the electronics tray. In v6 the beam is 288 mm long, ends 2.5 mm inboard of the
Y guide blocks and **hangs under** a tongue of each plate on one M5 from above. The plates are flat 3 mm steel,
laser cut; every screw of the gantry is driven from above or from the side; the tray needs no driver holes.
Machining estimate $209 to $112, machined parts 4 to 2. The gantry sits 23 mm lower: the machine is 413 mm tall
with 30 mm more Z than v5 (418 mm).

### 7. 180 mm of Z

Frame +10 mm (top ring at 344), stock 250 mm lead screw ending 4 mm under the top back rail, the same 300 mm
rails with the two blocks 55 mm apart (v5: 80 mm with 153 mm of travel). Bed tilt mode on the blocks
562 to 358 Hz, still far from the X and Y resonances. Z drive margin 3.4 (3 required).

### 8. Real catalogue parts (requirement 3)

| v5 proxy | v6 |
|---|---|
| 6 mm OD nylon spacers, 5 / 6 / 4 / 3 mm long | Pololu 5 x 3.3 nylon M3 spacers, 6 mm under every board, 4 mm under both switches; Pololu 4 x 2.7 M2.5, 4 mm, under the Pi. All M3 board screws became M3x16 |
| 10 x 5.5 aluminium spacers 6 and 8 mm | OpenBuilds-size 10 x 5.1: 6 mm on both Y idlers, 9 mm on the X idler |
| 12 x 20 silicone columns | `bed_column_silicone(18.0, installed=16.0)`: 16 OD, so the mounts moved 5 mm in from the bed's edges |
| bed in `al6061` | `al_mic6` |
| pulleys and idlers without a width in the SKU | X: 9 mm belt, `GT2-20T-B5-W9` and its idler. Y: 12 mm kept |

9 mm on Y was tried: the Y resonance fell from 62.0 to 58.1 Hz, below v5. The two Y belts are 727 mm long and
carry 1.32 kg; the X belt is 484 mm and carries 0.35 kg on an axis limited by the block's tilt. Whether 12 mm
pulleys with a 5 mm bore can be bought is still not confirmed (as in v5).

### 9. Consolidation (requirement 5)

347 parts (351 once the corner-bracket screws were modelled) to 317; 18 fastener sizes to SCORE_FTYPES.
Gone: extruder mount and its 6 screws, hotend mount with 4 screws and 4 nuts, two cartridges, heat-sink fan with
2 screws and 2 nuts, belt tower and clamp with 3 screws and 3 nuts, X belt clamp with 3 screws and 3 nuts, two Y
clamp bars with 6 screws, X idler slider and anchor screws, 2 Y motor-mount bolts, 3 board screws with spacers
and nuts (the SKR on four of its five holes, the Pi on two opposite corners), the double-counted `NUT-M5` BOM
line. Added: X and Y idler/motor plates for X (2), fan carrier (1 printed, 4 screws, 4 nuts), 2 spacers and
2 nuts under the X switch. Screw sizes dropped: M3x12, M3x14, M3x20, M3x30, M3x40, M5x6, M5x10, M5x35.
Added: M3x45 (the Roto's). The nut block is 10 mm instead of 14 so its pin is an M3x16; the Z motor bridge's top
plate is 5 mm so its screws are M3x8.

### 10. Hotend safety (requirement 7)

Kept: the relay ahead of the supply (firmware drops it on any shutdown) and the 133 degC cut-off on the bed.
New: the Revo's PTC winding. With its MOSFET shorted and nothing switching it off the model settles at 419 degC
(v5's 30 W cartridge: 451 degC); with the relay the peak is 282 degC. **The `cutoff_depends_on_mcu` warning stays
open**: nothing in the catalogue switches a hotend off without the controller. A thermal cut-off on the Roto's
heat sink in series with the heater was drawn and removed: it trips on a hot cold side (a dead fan), not on a
runaway block with the fan running, it adds two crimps to the heater circuit on the moving head, and the heater
model has no heat-sink node for it (item 1 below).

## What the verifiers caught, and the fixes

| Run | Finding | Fix |
|---|---|---|
| fast 1 | interference x3: captive nuts 1.3 mm^3 into their pockets (hexagon turned the wrong way for nuts along X and Z) | pockets turned |
| fast 2 | electrical `check_crashed` (heater check, `KeyError: 'plate'`) with the heat-sink cut-off in the heater circuit | cut-off removed (section 10; checker item 1) |
| fast 2 | electrical `klipper_rejects_config`: X homed sensorless, klippy: "tmc virtual endstop requires diag pin config" | X switch put back (checker item 2) |
| fast 2 | electrical `connector_blocked` x3 (supply 10.5 mm from the board's terminals after it was moved), `wire_hits_moving_part` (rear loom under the lower Z blocks, which sit lower now), `wire_through_part`, later five `bend_too_tight` | supply back; rear loom on the floor in front of the back rail; left loom round the supply with gentler bends |
| fast 2 | subsystems `cable_clamp_in_air` x2 | clamps moved to 2 to 3 mm from an edge of the part they are tied to |
| fast 3 | interference: X switch screw 0.4 mm into the Y guide block | later moot (switch on spacers, nuts) |
| fast 4 | parts 338, cost about $960: both over target | sections 5, 6 and 9 |
| fast 4 | electrical `wire_not_rated_for_heat` x3 (heater, thermistor, probe leads within 12 mm of the HeaterCore) | HeaterCore leads declared as the part's own pigtails; loom tied along the top of the Roto's rear face so the probe lead leaves away from the nozzle |
| fast 5 | tolerance: endstop screws into tapped sheet start in 96 % of builds | clearance holes and nuts |
| tolerance experiments | Y idler nut 0.7 mm into the end of the Y rail (found as a "0 % of builds" screw pattern) | idlers moved in front of the rails' ends |
| full 1 | motion x4: bed into the nozzle at Z +2 (checker item 3); probe into the X switch's land; part-fan screw heads into the top back rail at Y +90 | Z range ends at the nozzle plane; land shortened; bed and gantry 5 mm further forward |
| full 1 | assemblability, 54 errors from four causes: fan-carrier nuts in a blind tunnel; guide block cannot slide onto its rail past the Y plates; beam bolts from below blocked by the tray; nuts fed from below blocked by the tray | nut slots open to the underside or top; beam under the plates, bolts from above (section 6) |
| full 1 | not an error: Y resonance 58.1 Hz with 9 mm Y belts | 12 mm on Y |
| full 2 | requirements: a Requirement of mine took the metrics dict as an argument; Y belt 97.9 % | function fixed; beam-bolt slots, two-bolt mounts |
| full 3 | pass | |

Three full runs (13 to 14 minutes each), about 14 partial runs, 5 rounds of tolerance experiments on scratch
copies.

## v5 against v6

v5 figures: full report of 2026-11-14 for motion, assembly and FEA; fast verifiers re-run on 2026-11-15 01:27 UTC
(after the checker fixes); resonance from `STATUS.md` after the twin was refitted. v6: full run of
2026-11-15 03:52 UTC, score SCORE_TIME. The twin was being refitted during this work; treat the dynamic figures
as provisional until v4, v5 and v6 are scored together.

| | v5 | v6 |
|---|---|---|
| Passes all 12 | no (subsystems: 2 probe errors) | yes |
| Print volume | 180 x 180 x 150 | 180 x 180 x 180 |
| Parts | 351 (347 before bracket screws were modelled) | 317 |
| Total mass | 10.53 kg | 10.24 kg |
| Bill of materials | $651 | $719 (Roto $115, Revo $40) |
| Fabrication: machining / cutting / filament | $209 / $13 / $2 = $224 | $112 / $15 / $2 = $129 |
| Parts + fabrication | $875 | $848 |
| Custom parts: machined / sheet / printed | 4 / 8 / 12 | 2 / 11 / 7 |
| Printed | 90 g, 6.4 h | 62 g, 4.4 h |
| Moving mass X / Y / Z | 0.360 / 1.256 / 2.674 kg | 0.351 / 1.319 / 2.677 kg |
| Nozzle to guide-block centre | 64 mm | 44 mm |
| Nozzle stiffness X / Y, screw-only | 1,747 / 1,201 N/mm | 1,435 / 2,036 N/mm |
| Resonance X / Y (twin) | 71.6 / 62.0 Hz | SCORE_RES |
| Cross-track RMS / worst (verify's test cube) | 0.011 / 0.113 mm (score) | 0.012 / 0.107 mm |
| Y belts within 1 mm of plane | 92.8 / 92.7 % | 98.4 / 98.7 % |
| X belt within 1 mm | 99.5 % | 99.1 % |
| Bed with 3x payload, screw-only | 368 N/mm | 432 N/mm |
| Bed 60 K hot: gap / bow | -0.074 / 0.010 mm | -0.071 / 0.019 mm |
| Bed tilt mode on the blocks | 562 Hz | 358 Hz |
| Drive margin X / Y / Z | 8.4 / 8.0 / 3.4 | 8.5 / 7.7 / 3.4 |
| Assembly time estimate | 69.7 min | SCORE_ASM min |
| Needs holding / fasteners / fastener types | 89 / 167 / 18 | SCORE_HOLD |
| Warnings | 39: 27 proxy parts, 2 belt plane, 4 manufacture, 1 mesh strip, 4 electrical (pull-up, probe temperature, hotend cut-off, loom across a fan), 1 assembly | 8: 1 proxy part, 3 manufacture, 1 mesh strip, 2 electrical, 1 assembly |

Adjustment needed (99th percentile of 3,000 builds) against provided:

| Adjustment | v5 needed | v6 needed | v6 provided |
|---|---|---|---|
| Z offset | 1.12 mm | 1.63 mm | 2.0 mm (probe offset; rail, screw and nut travel) |
| Bed level | 1.03 mm | 1.19 mm | +/-1.5 mm |
| Y rail alignment | 1.05 mm | 1.14 mm | +/-1.5 mm |
| Z rail alignment | 0.72 mm | 0.88 mm | +/-1.5 mm |
| Lead-screw nut offset | 0.15 mm | 0.16 mm | +/-1.3 mm float |
| Screw to rail angle | 0.83 deg | 0.85 deg | coupler 1.0 deg (typical figure, thin) |
| Belt tension X, Y | not modelled | not modelled | +/-3 mm each |

### What got worse

- **Nozzle height scatter 1.12 to 1.63 mm.** The X rail now hangs on a vertical face, so its height is set by its
  T-nut screws in the slot and not by a face it sits on (`x_beam / x_rail` is the largest contributor). On the
  bench the rail is pushed up against a straight edge laid on the beam's top face before its screws are tightened;
  that is not modelled. Inside the 2.0 mm provided, but the margin is 0.4 mm.
- **Nozzle stiffness in X** 1,747 to 1,435 N/mm in the FEA (single-bolt beam joints under 3 mm steel plates).
- **Y moving mass** +63 g (steel Y plates, two steel plates for the X motor and idler).
- **Bill of materials** +$68: the Roto and Revo cost $155 against $84 for v5's extruder, proxy hotend, cartridges and heat-sink fan.
- **Bed tilt mode** 562 to 358 Hz (blocks 55 mm apart).
- **Part cooling is weaker than it should be.** A 30 mm axial fan behind the Roto on a printed carrier whose floor
  runs under the motor; the duct's walls and outlet are not modelled, and about half of the fan's face looks at
  the Roto's rear. A 4010 blower is the right part; the catalogue has none.
- **Y belt anchors are cable-tied loops through slots.** Cheap and located well, but the holding force is not
  modelled, and the slots are 3 mm wide in 3 mm steel with laser-cut edges that need deburring.

## Allowances and overrides

- `allow_overlap("hotend", "extruder")`: the Revo nozzle screws 0.7 mm into the Roto's seat (a real thread).
- The automatic thread overlaps of `add_screw(threads_into=...)` and `add_nut(screw=...)`.
- `process="purchased"` on the extruder (its SKU starts with "EXT"), as in v4 and v5.
- `meta={"print_up": ...}` pins each printed part's orientation.
- No limit, threshold, requirement value or electrical requirement was changed; no DFM limit overridden.
- Two requirements were reworded, not loosened: the bed-gap requirement reads the gap at Z = 180 (it is the joint's
  end again, so the wording is equivalent to v5's); "Z rails end below the top back extrusion" now also covers the
  lead screw.
- No catalogue part was added. `mechloop/` was not edited.

## Checker behaviour worth a look

1. **A thermal cut-off in series with a block-type heater crashes the heater check.** Reproduce: in v6 place
   `thermal_fuse(99, 76, 10)` on the extruder, `device_from(el, d, "hs_tco")`, wire `control_board.E0 -> hs_tco.a`
   and `hs_tco.b -> hotend.in`. Result: `check_crashed: Electrical check 'heaters' could not run: KeyError:
   'plate'`. The cut-off's node defaults to `"plate"`, which a hotend network does not have, and there is no
   heat-sink node to give it instead.
2. **Sensorless homing produces a config Klipper refuses.** `d.endstops += [{"joint": "x", "sensorless": True}]`
   (documented in `AGENT.md`) writes `endstop_pin: tmc2209_stepper_x:virtual_endstop` but no `diag_pin` in the
   driver section: `klipper_rejects_config: tmc virtual endstop requires diag pin config`. v6 would have saved a
   switch, two spacers, four fasteners and a wire.
3. **Z travel beyond the nozzle plane cannot be declared.** With the Z joint's range ending 2 mm past the
   nominal nozzle plane (what a probe with a z_offset needs for a bed built low, and what a bed mesh needs to lift
   a low corner; the generated config then has `position_min: -1.9`), motion reports `motion_collision: bed hits
   hotend ... at pose {'z': 182.0}`, which is true of the nominal model and of every real printer with a probe.
   With the range ending at the plane, `position_min` is 0 and the mesh has nothing in hand. v6 does the second and
   states the mechanical room as a Requirement. Also: with the over-travel declared, tolerance reported
   `p_first_layer_reachable_as_built: 0.0` (it reads the gap at the end of travel).
4. **A clash makes the belt-plane figure better.** With the Y idler's nut 0.7 mm inside the end of the Y rail the
   tolerance run gave 99.7 % / 99.6 % for the Y belts; with the nut clear, 97.9 % / 98.3 %, nothing else
   changed (`YI_Y = -148` against `-156` at that stage). The overlap seems to be taken as a joint that ties the
   idler to the rail. A `--only tolerance` run does not show the interference.
5. **The mesh check's print area is the whole XY travel.** There is no way to say that travel beyond the
   claimed print area is there for the probe, so extra travel on the probe's side leaves the warning's strip
   exactly as wide.
6. **`cable_clamp_in_air` seems to measure to vertices.** A clamp 3 mm off the middle of the Roto's flat rear face
   is reported as "5 mm" / "6 mm from any part"; 2 mm from a corner passes. A clamp exactly 3.0 mm from a rail
   face fails with the message "is 3 mm from any part".
7. **The assemblability verifier does not use `design.subassemblies`.** Declaring the gantry a bench sub-assembly
   left "beam_bolt blocked by electronics_tray" standing (the tray is 340 mm below a 50 mm driver). The fix in v6
   is a real one, but a bench-built unit cannot be expressed.
8. **The Y-belt figure moves by +/-0.3 % between identical runs**, which is the size of the gap to a 98 % target.
   The seed or the number of builds should be reported with it.

## Still unverified

- Roto: winding inductance (catalogue estimate), the insulation of the HeaterCore's leads, the real stiffness
  of its housing (solid aluminium in the FEA), whether two M3x45 through both ears clamp it flat without
  distorting the idler lever's pocket. Extrusion: confirm steps/mm with a 100 mm test (E3D's own Klipper block
  omits the gear ratio).
- The probe: every figure is recalled (dimensions, 3.2 mm on aluminium, +/-10 %, 70 degC); drift with
  temperature; its 24 V feed is declared, not routed. No bed-probe part with vendor data exists in the catalogue.
- The X rail's height on a vertical face (see "What got worse"), and the single MGN12H block's tilt stiffness
  under the toolhead (the twin's fitted 10 N/um).
- The beam hanging on one M5 per side: no preload or contact model; squareness to the Y rails rests on friction
  under two bolts, as in v5.
- Belt tension, tooth load, the folded-belt and cable-tie anchors, the tensioners' ranges.
- Part cooling (no airflow model, duct not drawn). Heat on the tool plate 7 mm from the HeaterCore.
- 12 mm x 5 mm-bore pulleys and idlers as stock items; OpenBuilds spacer lengths; silicone column stiffness.
- Frame stiffness with 314 mm posts (the stiffness cases cover the gantry only).
- Sheet parts: tolerances are typical values for laser cutting; 3 mm slots in 3 mm steel.
- Everything listed as not checked in `AGENT.md` and `docs/ELECTRICAL.md`.

## Scores and firmware in the loop

SCORE_SECTION

## Decisions that should be confirmed

1. X rail on the rear face of the beam, beam under the Y plates. It is what makes the direct-drive head short
   and the Y plates sheet; it costs 0.5 mm of nozzle-height scatter and some X stiffness.
2. 9 mm belt on X, 12 mm on Y.
3. Y belts tied through slots in the Y plates instead of clamped.
4. The Roto's fan on the board's 5 V pins (always on) instead of E3D's regulator board on a switched output.
5. No heat-sink cut-off; the hotend warning stays open.
6. The probe-coverage target is reported as not met rather than bought with a wider machine.
7. The SKR on four screws and the Pi on two.

## Files

- `designs/printer_v6.py`: the design.
- `out/printer_v6/`: `report.json`, `views.png`, `simulation.gif`, STEP, DXF profiles of the 11 sheet parts,
  `electrical/printer.cfg`, `wiring.csv`, `scores.jsonl`, `tune/`, `fil/bracket/`.
