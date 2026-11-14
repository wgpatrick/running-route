# printer_v5: printer_v4 after the trade study

Everything here is simulated. Nothing has been built.

`designs/printer_v5.py` applies the findings of `../reports/Printer trade study.md` to
`designs/printer_v4.py`. It passes all 12 verifiers (0 errors, 40 warnings, 27 of them hand-made
proxy parts), prints the test bracket with real Klipper planning the motion, and was scored against
v4 on the same day with the same twin (2026-11-14, belt stiffness default 22 kN).

The designer worked from the findings, hints and documents only. The source of the verifiers,
tolerance, assembly, twin and electrical modules was not read.

## Summary

| | v4 | v5 |
|---|---|---|
| Custom parts by process | 35 machined, 2 sheet, 0 printed | 4 machined, 8 sheet, 12 printed |
| Fabrication estimate (the manufacture verifier's own) | $2,381 machining + $5 cutting | $360 machining + $13 cutting + $2 filament (90 g, 6.4 h) |
| Guide blocks per Z rail | 1 | 2, 80 mm apart |
| Bed tilt mode on the blocks (ratings estimate) | 76 Hz, warning | 562 Hz, no warning |
| Mass moving in X | 0.60 kg | 0.36 kg |
| Resonance X / Y | 68.5 / 57.2 Hz | 88.6 / 62.2 Hz |
| Highest clean acceleration | 8,000 mm/s² | 10,000 mm/s² |
| Belt tensioners / bed probe | none / none | X and both Y / inductive probe on Z-STOP |

The price: 55 more parts, 26 more fasteners, 11 more minutes of estimated assembly, $52 more
bill of materials, a bed stage 0.2 kg heavier, wider as-built scatter of nozzle gap and bed level,
and a Bowden extruder. Details are in "What got worse".

## The changes, with the evidence behind each

### 1. Stop machining everything

Study: the references print 640 to 1,250 cm³ of parts; v4's 35 machined parts were estimated at
$2,376, four times its bill of materials; 10 manufacture warnings came from machining shapes the
references print.

| v4 part | v5 | Material, and why |
|---|---|---|
| `carrier` (block, 95% chips, 4 set-ups, $561) | `back_plate` + two 2020 arms + two cast brackets + `nut_block` | see change 2 |
| `tool_plate` (block, 4 set-ups, $132) | `tool_plate` flat 8 mm plate, **machined**, one set-up ($56) + `hotend_mount` printed + `x_belt_block` printed | plate: 6061, it sets the nozzle stiffness (below). Mount and belt block: ABS, they sit 35 mm above a 250 °C heater block on a fan-cooled heat sink |
| `z_motor_mount` (block, 77% chips, $108) | printed bridge on the bottom back rail | ABS: the Z motor case runs at 61 °C (electrical verifier), too warm for PETG under a steady load |
| `y_motor_mount`, `y_motor_mount_l`, `y_idler_mount`, `y_idler_mount_l` (4 mm plates, $46 to $63 each) | the same flat shapes, laser-cut | 3 mm steel sheet: about 1.2 times the bending stiffness of 4 mm aluminium, and an M3 hole is no longer narrower than the sheet |
| `x_belt_clamp`, `y_belt_clamp`, `y_belt_clamp_l`, `y_belt_tower_l` ($43 to $63 each) | printed | ABS on the toolhead and beside the X motor, PETG on the right Y plate |
| 20 turned spacers ($41 each at quantity 1) | bought round spacers | nylon under the boards and the Y endstop, aluminium on the Y idler axles. Proxies: the catalog has no spacer or standoff |
| `z_endstop_bracket` | gone, with the Z switch (change 5) | |
| `bed`, `y_plate_left`, `y_plate_right` | still **machined**, one set-up each | bed: flat print surface with counterbored screw heads. Y plates: the carriage screw heads must be counterbored under the beam, and the two plates set the beam square to the rails |

Printed parts were drawn as printed parts:

- No thread is cut in plastic where a load passes. Belt clamp, fan, probe, mount and tower screws run
  into nuts: captive in pockets (belt block, Y tensioners), in slots closed by the tool plate (fans) or
  plain nuts underneath (hotend mount, tower, nut block). Three heat-set inserts remain: the hotend's
  two set screws and the X tensioner's pull screw.
- Each printed part has a pinned orientation with no support: the motor bridge and nut block stand on
  a flat face with every wall vertical; the nut block's square hole for the lead screw is a 14 mm
  bridge instead of a 13 mm horizontal round hole; the hotend mount and belt block print upside down.
- Clearance holes in printed parts are 4.2 mm for M3 and 6.0 mm for M5 (3.8 mm in the belt clamps).
- Strength with the plastic's properties (FEA, load x3 or more): nut block 1.6 MPa, factor of safety
  25, 0.05 mm; motor bridge 2.0 MPa, 21, 0.04 mm; belt block at 60 N of belt pull 1.9 MPa, 21,
  0.025 mm; belt tower at 120 N 2.2 MPa, 18, 0.03 mm. The limits are 3 and 0.3 mm (0.1 mm for the belt parts).

**Why the tool plate is machined again.** The first v5 tool plate was a 5 mm laser-cut sheet. The
nozzle stiffness in Y (screw-only joints, the value the twin uses) came out at 411 N/mm against
v4's 1,260, and the Y resonance at 54.8 Hz, below v4's 57.2 Hz although the toolhead was 0.26 kg
lighter. Four FEA runs separated two causes. One was the plate: 5 mm against v4's 6 mm plate with
an 18 mm deep collar. The other was how the screw-only model treated the hotend's seat (see
"Checker behaviour", item 2). An 8 mm plate gives 1,239 N/mm. It cannot be sheet, because no
standard M3 length leaves 3.0 to 3.5 mm in the guide block's threads through 8 mm without a
counterbore. Cost: one set-up, $56 estimated, 27 g on the toolhead.

### 2. Bed carrier as an assembly

Study: Voron 0.2 bed frame is three extrusions and four printed parts; the Trident uses two 2020 bed
extrusions; estimate 0.013 mm of arm bending per kg.

- `back_plate`: 5 mm 6061 sheet, laser cut, through holes only, 214 x 126 mm with one window, on the
  four Z blocks (M3x8, 3.0 mm in the blocks' 3.5 mm threads).
- `bed_arm_left/right`: 2020 x 210 mm, 65 mm either side of centre. Each is held by an M5x16 through
  the plate into its tapped end, driven from behind between the upright and the lead screw, and by a
  cast corner bracket underneath.
- The bed's silicone columns stand on the arms. The bed screws (M3x25, heads counterbored in the bed)
  go into T-nuts in the arms' top slots, so levelling is done from above with a hex key. The T-nuts
  are held only by the columns' spring force and slide as the hot bed grows.
- The heater pad was turned to 200 x 140 mm so the four mounts stand in front of and behind it.
- `nut_block`: printed ABS, bolted through the back plate, sits on the floating T8 nut (same float and
  anti-rotation pin as v4). It is behind and below the bed, in open air, at 1.6 MPa under three
  times the load.

FEA `payload_x3_on_bed` (bed, columns, arms, brackets, back plate and blocks meshed together, held
at the rails, 52.5 N on the bed): 0.14 mm at the bed's front edge with screw-only joints, 0.10 mm
bonded, limit 0.3 mm. About 0.05 mm of that is the silicone columns compressing. v4's 0.033 mm was
the carrier alone, clamped at the blocks, so the two are not the same measurement.
Bed 60 K hot: surface rises 0.074 mm, bow 0.010 mm (v4: 0.074, 0.007).

### 3. Two guide blocks per Z rail

Study: v4's bed hangs 229 mm in front of one block per rail; estimated nodding at about 60 Hz, on
top of the X and Y resonances; two blocks 50 mm apart raise the tilt stiffness about 16 times. The
ratings verifier now warns `cantilever_on_guide_blocks` on v4 (76 Hz).

v5: blocks 80 mm apart on 300 mm rails. The study proposed 250 mm rails and 50 mm; that leaves no
over-travel and less than the 5 mm of rail the v4 requirement asks for beyond each block. With
153 mm of travel, 45.4 mm blocks and 5 mm at each end, a rail of L mm allows L - 208.4 mm of
spacing: 41.6 mm on 250 (the blocks would overlap), 91.6 mm on 300. To get 300 mm of free upright:

- the Z motor mount left the uprights' front faces for the bottom back rail;
- the uprights and corner posts grew from 284 to 304 mm (top ring 314 to 334 mm).

The Z rails are now the same part as the Y rails (four MGN12 x 300). Ratings verifier: tilt
stiffness 6,000 to 268,000 N·m/rad, tilt mode 76 to 562 Hz, sag at the mass centre 0.018 to
0.0003 mm per kg, warning cleared. These rest on the verifier's assumed block stiffness of 40 N/µm.

### 4. Belt tensioners

Study: every reference assembly has tensioner parts; v4 has none.

- **Y, both belts.** Each motor mount is held by three M5 screws in T-nuts in the frame slot. With
  them slack the mount slides along the rail. A printed PETG anchor block bolted in the same slot
  (and hooked 6 mm under the rail so it cannot turn) carries an M3x25 jack screw in a captive nut;
  the screw pushes on a lug cut into the mount's profile. 0.5 mm per turn.
- **X.** The idler stands on a printed slider. Its M5 axle bolt runs through a ±3 mm slot in the
  right Y plate to a nut underneath. An M3x20 screw through a fixed printed anchor pulls the slider
  outward; then the axle nut is tightened. The idler moved 10 mm inboard so the anchor stays inside
  the frame line (at the front end of the Y travel that part of the plate passes inside the idler mount).

Declared as two `Adjustment(kind="belt_tension", range_mm=3.0)` and `Belt.adjust = 3.0`. Nothing in
the verifiers checks belt tension or that the declared range exists in the geometry.

### 5. Bed probe

Study: all references but two have a probe; v4's hand levelling has to absorb up to 0.58 mm.

- `bed_probe`: an inductive proximity sensor of the PL-08N class (18 x 18 x 36 mm, 8 mm on steel),
  a hand-made proxy, on a wall of the hotend mount 33 mm to the right of the nozzle, 14 mm of air
  from the heater block. Its face is 3.1 mm above the nozzle tip: the assumed switching distance on
  aluminium (3.2 mm) less the 0.1 mm first-layer gap, so it switches as the bed reaches the nozzle.
- Wired to the board's Z-STOP input (PC2) through the toolhead loom, silicone insulated.
- **The Z microswitch, its bracket and the jack screw are gone** (9 parts). Reason: with the switch
  struck by the carrier, every turn of a levelling screw moved the nozzle gap and the jack screw had
  to be reset. The probe senses the bed surface itself. The Z-offset adjustment is now the probe's
  offset in the firmware. The four levelling screws stay: one Z motor cannot level the bed, so the
  probe gives a mesh and tells the builder how far to turn each screw.
- A microswitch probe was rejected: a fixed lever would have to hang below the nozzle.

What the model can and cannot say about it is under "Still unverified".

### 6. Lighter toolhead

Study: 0.60 kg against 0.25 to 0.47 kg on the references; aim at 0.40 kg.

The catalog has one extruder, 0.24 kg. With the hotend proxy (0.12 kg) and the guide block
(0.054 kg) that is 0.41 kg before any mount, fan or screw, so 0.40 kg cannot be reached with a
direct-drive extruder from this catalog. v5 therefore takes the extruder off the toolhead: it hangs
under a 3 mm sheet plate on the top back rail and feeds through a PTFE tube (Bowden), as on the
Prusa MINI+ (same build volume) and the Ender 3. `design.printer["extruder"] = "bowden"`.

| On the toolhead | v4 | v5 |
|---|---|---|
| Extruder | 0.240 | on the frame |
| Hotend proxy, guide block | 0.174 | 0.174 |
| Tool plate / plate + printed mount + belt block | 0.131 | 0.067 + 0.027 + 0.014 |
| Belt clamp | 0.012 | 0.005 |
| Bed probe | none | 0.020 |
| Fans, cartridges, screws, nuts | 0.040 | 0.053 |
| **Total** | **0.597 kg** | **0.360 kg** |

This is the one change of kind in v5, and it has a cost the twin does not model (see "What got
worse"). A lighter direct-drive extruder (about 0.14 kg exists on the market) would be the better
answer; it needs a catalog entry with real data first.

### 7. Bed plate material

Study: six references specify cast tooling plate. `MATERIALS` has no cast plate and `mechloop/`
may not be edited, so the part still says `al6061`. The purchasing note (MIC6 or ATP5, 6 mm) is in
the design file. Nothing in the results depends on it: the thermal case models uniform material.

## What the verifiers found on the way, and the fixes

| Run | Finding | Fix |
|---|---|---|
| partial 1 | geometry `detail_clash` x2: the cast corner bracket's CAD has a 4 x 17 mm locating rib standing 1 mm out of each leg; it ran into the back plate | the bracket's screw hole in the plate became a vertical slot that the rib sits in |
| partial 1 | interference x5: captive nuts overlapped their pockets by 1.3 mm³ | pockets turned 30° to match the nuts |
| partial 1 | tolerance `screws_may_not_align`, 8 errors: screw patterns through 3.4 mm printed holes or into printed threads start in 24% to 78% of builds (tower clamp 24%, motor bridge 33%, Y clamp 47%, tool plate into the printed mount 55%, fans 76%) | printed clearance holes opened to 4.2 mm; printed threads replaced by through-bolts and captive nuts; four-screw patterns in sheet opened to 3.6 mm |
| partial 1 | subsystems `cable_clamp_in_air`: the gantry loom's frame clamp sat under the rail's slot, 3 mm from metal | moved 3 mm sideways under solid rail |
| partial 1 | manufacture warnings: back plate holes 2.3 mm from the edge; motor bridge 100 mm and hotend mount 81 mm wide in ABS (warp rule of thumb 80 mm); a slot for the Y endstop's terminals 0.9 mm from its screw holes in sheet; tapped holes 1 mm short of breaking through; 2.8 mm of plastic round a thread in the tower | plate widened 6 mm; bridge 79 mm, mount 76 mm; the Y endstop stands on two bought 3 mm spacers and needs no terminal holes; screws lengthened to tap through; tower through-bolted |
| partial 2 | interference `thread_engagement` x4: fan screws had 2.0 mm in their nuts, 2.4 needed | printed lug between fan and nut 4.0 to 3.5 mm |
| partial 2 | tolerance x4 errors: fan screws "start in 0% of builds, -0.35 mm radial clearance" | see "Checker behaviour", item 1 |
| partial 2 | manufacture `needs_support`: 181 mm² under a 3 mm ledge of the belt block | ledge chamfered at 45°; it went altogether with the 8 mm plate |
| partial 3, then motion and assemblability | pass; one `unsupported_step` warning | bed carrier and toolhead declared as bench sub-assemblies (the warning stayed) |
| full 1 | fea `fea_unbalanced` on `nut_thrust` (reactions 1.4% off): the loaded underside of the nut block ran straight into the edge of the fixed flange face | flange extended 7 mm below the block |
| full 1 | not an error: nozzle stiffness Y 411 N/mm, Y resonance 54.8 Hz, below v4; printing `corner_bulge` warning | mount bolts moved, tool plate 8 mm (change 1); Y 62.2 Hz, the warning went |
| full 2 | pass | |

The first full verify took 16 minutes; the second passed. Motion and assemblability passed the
first time they were run.

## v4 against v5

Both scored on 2026-11-14 with `mechloop score --assembly`. v4's fabrication and tolerance figures
are from a v4 verify of the same day.

| | v4 | v5 | |
|---|---|---|---|
| Parts | 292 | 347 | worse |
| Total mass | 10.02 kg | 10.52 kg | worse |
| Bill of materials | $598 | $651 | worse |
| Fabrication estimate | $2,386 | $375 | better |
| Custom parts: machined / sheet / printed | 35 / 2 / 0 | 4 / 8 / 12 | |
| Machining set-ups | 43 | 4 | better |
| Resonance X / Y | 68.5 / 57.2 Hz | 88.6 / 62.2 Hz | better |
| Cross-track error, RMS / worst | 0.0149 / 0.144 mm | 0.0114 / 0.113 mm | better |
| Highest clean acceleration (first failure) | 8,000 (10,000) mm/s² | 10,000 (12,000, Y loses steps) mm/s² | better by one step; one step is within the noise |
| Nozzle stiffness X / Y, screw-only joints | 1,905 / 1,260 N/mm | 1,773 / 1,239 N/mm | slightly worse |
| Moving mass X / Y / Z | 0.597 / 1.489 / 2.471 kg | 0.360 / 1.256 / 2.674 kg | X, Y better; Z worse |
| Drive margin X / Y / Z (3 required) | 5.5 / 7.0 / 3.6 | 8.4 / 8.0 / 3.4 | Z worse |
| Bed tilt mode on the guide blocks | 76 Hz | 562 Hz | better |
| Bed sag on the blocks, at the mass centre | 0.018 mm per kg | 0.0003 mm per kg | better |
| Bed with 3x payload, FEA | 0.033 mm (carrier alone) | 0.14 mm (bed, columns, arms, plate, blocks) | not comparable |
| Benchmark print time | 2,564 s | 2,564 s | same |
| Assembly time estimate | 59.0 min | 69.7 min | worse |
| Parts that need holding | 76 | 89 | worse |
| Fasteners / types | 141 / 14 | 167 / 18 | worse |
| Tool changes / times turned | 9 / 4 | 5 / 5 | |
| Warnings | 19 (5 proxy parts) | 40 (27 proxy parts) | |

Adjustment needed (99th percentile of 3,000 simulated builds) against adjustment provided:

| Adjustment | v4 needed | v5 needed | Provided | How in v5 |
|---|---|---|---|---|
| Z offset | 0.67 mm | 1.14 mm | ±3.0 mm | probe offset in the firmware |
| Bed level | 0.60 mm | 1.04 mm | ±1.5 mm | four screws on silicone columns |
| Y rail alignment | 1.04 mm | 1.11 mm | ±1.5 mm | rails on sliding T-nuts |
| Z rail alignment | 0.89 mm | 0.73 mm | ±1.5 mm | same |
| Lead-screw nut float | 1.88 mm | 2.29 mm | ±1.3 mm | floating nut; no finding in either design, see "Checker behaviour", item 3 |
| Belt tension X, Y | not modelled | not modelled | none in v4, ±3.0 mm in v5 | slider and pull screw; sliding motor mounts and jack screws |

Remaining warnings in v5:

- ratings, 27 `uncatalogued_cots`: 21 bought spacers, 4 silicone columns, hotend, bed probe. True.
- tolerance, 4 `screws_may_not_align` at 98 to 99%: the four fan screws (item 1 below).
- tolerance, 2 `belt_out_of_plane`: both Y belts end up more than 1 mm out of plane in 7% of builds
  (up to 1.5 mm; v4: 1.5% and 3.9%, no warning). The printed clamps have 0.25 mm of play in their
  screw holes and the mounts are sheet. On the bench the clamp is set to the belt and the pulley is
  slid along the motor shaft; there is no adjustment kind to declare that.
- manufacture, 4: back plate has 20 holes narrower than its 5 mm thickness (ream after cutting);
  electronics tray (2) and inlet panel (1), unchanged from v4.
- electrical, 2, unchanged from v4: the hotend's cut-off depends on the controller; the toolhead
  loom's straight line crosses the heat-sink fan at one corner of the travel.
- assemblability, 1 `unsupported_step` (v4 has one too, around a different part).

## Firmware in the loop

`mechloop print designs/printer_v5.py examples/motor_bracket.py:bracket --firmware klipper --trajectory`:
Klipper (commit `29d4ec2`, STM32G0B1) accepted the generated `printer.cfg` and planned the whole
print with no rejected move and no message. 255 layers, 3,941 s, 15.3 g.

| | v5 | v4 (earlier run, softer belt default, for scale only) |
|---|---|---|
| Path error, RMS / worst | 0.0088 / 0.098 mm | 0.0152 / 0.147 mm |
| Outline match, mean | 97.5% | 97.5% |
| Worst lag X / Y | 0.083 / 0.135 mm | 0.158 / 0.184 mm |
| Peak step rate | 19,753 /s of 263,000 | same |
| Collisions (4,045 poses) | 0 | 0 |
| Warning | corner bulge 0.40 mm (assumed 30 ms extruder lag) | same |

The lowest thing on the toolhead after the nozzle is the probe, 3.1 mm above the nozzle plane.

## What got worse

- **Bowden extruder.** About 400 mm of PTFE tube between drive and nozzle: longer retraction, more
  ooze and a softer response of flow to speed; flexible filaments become hard. The twin reports the
  same assumed 30 ms extruder lag for both designs, so none of this is in the scores.
- **More parts and fasteners** (292 to 347, 141 to 167, 14 to 18 types) and 11 minutes more assembly.
  The carrier is 16 parts where it was 1, the tensioners add 12, captive and plain nuts replace
  threads in plastic, the probe adds 5, two more guide blocks add 10.
- **Bill of materials +$52**: two more blocks and longer rails ($25), arms and brackets, probe, PTFE
  tube, spacers, more screws.
- **Z stage 0.2 kg heavier**; Z drive margin 3.6 to 3.4 (3 required).
- **As-built scatter is wider** because sheet and printed parts are less accurate than machined ones:
  nozzle gap error 0.67 to 1.14 mm, bed out of level 1.2 to 2.1 mm before adjustment; 20% of builds
  reach the first layer unadjusted (v4: 35%). All within the adjustment provided.
- **Lead-screw nut misalignment** 1.88 to 2.29 mm at the 99th percentile (printed motor bridge and nut
  block). The motor bridge can be slid on its two T-nuts before tightening; that is not declared.
- **Y belts out of plane** more often (above).
- **Nozzle stiffness** 7% lower in X, 2% in Y.
- **20 mm taller**; the longer posts' effect on frame stiffness is not in the twin (its stiffness cases
  cover the gantry only).
- **The probe cannot reach the whole bed**: it sits 33 mm to the right of the nozzle, so the left
  33 mm of the 180 mm print area is not probed.

## What was not done, and why

- **9 mm belts.** Optional. The catalog's pulleys and idlers take any belt width and their SKUs do
  not encode it, so the catalog cannot say whether 12 mm parts can be bought. 9 mm would cost 25% of
  the belt stiffness. Kept 12 mm; whether 12 mm pulleys with a 5 mm bore are stocked is still open.
- **Blind frame joints.** Optional; the brackets stay. (The two bed arms are blind joints.)
- **A lighter direct-drive extruder as a proxy part.** It would have kept direct drive at about
  0.50 kg, but mass, dimensions and winding data would have been recalled, not read.
- **Three-point bed, CoreXY, fixed bed, mains bed.** Excluded by the study and the brief.
- **Fewer screw types.** Possible (M3x30, M3x40, M5x16 serve 2 to 4 screws each); left for a next pass.
- **Tray and inlet-panel hole warnings.** Carried over from v4 unchanged.

## Allowances and overrides

- `allow_overlap("hotend_heater", "hotend")` and `("hotend_thermistor", "hotend")`: carried over from
  v4; the cartridges are clamped in bores the hotend proxy does not draw.
- The automatic thread overlaps made by `add_screw(threads_into=...)` and `add_nut(screw=...)`.
- `process="purchased"` on the extruder, as in v4 (its SKU starts with "EXT").
- `meta={"print_up": ...}` pins the print orientation of each printed part.
- No limit, threshold, requirement or electrical requirement was changed. No DFM limit was overridden.

## Checker behaviour worth a look

1. **A captive-nut slot is read as the screw's clearance hole (tolerance).** In `hotend_mount` each
   fan screw passes a 4.2 mm hole in a 3.5 mm lug and enters an M3 nut that sits in a slot open to
   the top face, 5.8 mm wide across the flats. With the slot 2.7 mm wide along the screw axis the
   verifier reported `screws_may_not_align`, "printed holes with -0.35 mm radial clearance", 0% of
   builds (an error). With the slot 3.7 mm wide it reports +0.15 mm and 98% (a warning). The clearance
   follows (slot width - 3.0)/2 - 0.2, so the slot's width along the screw is being taken as a hole
   diameter. The hexagonal blind pockets used elsewhere do not trigger it. v5 keeps 3.7 mm, which
   also leaves room for the screw tip; the four warnings are this artefact.
2. **Screw-only stiffness flips with 1 mm of bolt position (fea).** The hotend seats on the tool
   plate and is held by set screws in the mount (`join` kinds `clamp` and `set_screw`, as in v4, where
   the seat stayed bonded in both solutions). With the mount's through-bolts 7.4 mm from the heat
   sink's rim, the screw-only solution listed `tool_plate / hotend` as a screwed joint with 2 screws,
   kept 6 nodes and released 91: 411 N/mm in Y. With the bolts 8.4 and 10.5 mm away (moved to give
   10 mm of plate between holes) the joint is not listed and the result is 646 N/mm on the same
   5 mm plate. Reproduce with `MOUNT_SCREWS` y = (24, 44) against (22, 46.5) and `T_TP = 5`.
3. **Lead-screw nut misalignment exceeds the declared float with no finding (tolerance).** v5:
   `lead_screws.z.nut_misalignment_mm_99` = 2.29 mm, v4 = 1.88 mm, declared float ±1.3 mm,
   `nut_floats: true`, no finding. Either the metric is not the quantity compared or the comparison
   is missing.
   **Fixed afterwards.** The drive did not name the nut, so the nut-seat offset was never measured, and the
   declared float was never compared with anything. The check now measures the offset between the nut's seat
   and the screw where the nut is nearest the motor, compares it with the float (`adjustment_too_small`),
   and lets a flexible coupler take the screw-to-rail angle up to its rating (`coupler_angle_exceeded`
   otherwise). v5: offset 0.16 mm against ±1.3 mm of float; angle 0.86° against a coupler rating of 1.0°
   that is a typical figure for jaw couplings, not a vendor value. That margin is thin.
4. **No probe in the model.** There is no probe device kind. The proxy was given the endstop template
   and a `trigger` interface, and subsystems accepted it as the Z-max switch (gap 0.0 mm at the end
   of travel). That check therefore rests on a point the designer wrote. The generated `printer.cfg`
   treats it as a plain endstop (`endstop_pin: ^PC2`); `[probe]`, `[safe_z_home]` and `[bed_mesh]` are
   not generated, and a normally-open NPN sensor may need the pin inverted.
5. **`add_corner_bracket` on a part that is not an extrusion.** It declares an `m5_tnut` joint to the
   sheet back plate without complaint. The plate-side screw and nut exist only as BOM lines, so their
   access is not checked.
6. **The bed's machining estimate.** $177 and 104 minutes for a 220 x 220 x 6 mm plate with four
   counterbored holes. It is now half of v5's whole machining estimate.
7. **Partial runs overwrite `out/<name>/report.json`.** A `--only` run on v4 replaced its full report;
   v4 was verified again in full afterwards. **Fixed afterwards:** a partial run now writes
   `report_partial.json`.

## Still unverified

- The probe: dimensions, mass and switching distance are recalled class values; drift with bed and
  ambient temperature (the sensor is rated to about 70 °C and works 3 mm above a bed at up to
  100 °C); its 24 V feed and the level of its output at the board input.
- The Bowden path: tube friction, the tube's shape over the travel (only its length, 420 mm against
  326 mm needed, and its bend radius are checked), retraction and pressure behaviour.
- Printed parts in service: creep, heat (there is no thermal model of the toolhead or the motor
  bridge), layer adhesion, insert pull-out. FEA uses isotropic properties of solid plastic.
- Belt tension, tooth load and the tensioners' ranges (declared, not checked against geometry).
- Four blocks on two rails: the tolerance check covers the parallelism of the rail pair and the
  drag it adds, not the fit of two blocks on one rail to one flat plate.
- The bed's freedom to grow: the thermal case bonds the columns to the arms.
- The arm joints: bonded and screw-only bounds only, no preload or contact. The corner brackets'
  plate-side screws are not modelled.
- The tilt mode and sag on the blocks assume 40 N/µm per block.
- Cast tooling plate: not in the material table.
- Frame stiffness with posts 20 mm longer.
- Everything listed as not checked in `AGENT.md` and `docs/ELECTRICAL.md`.

## Files

- `designs/printer_v5.py`: the design.
- `out/printer_v5/`: report, views, STEP, DXF profiles of the sheet parts, `electrical/printer.cfg`,
  `wiring.csv`, `scores.jsonl`, `fil/bracket/` (the firmware-in-the-loop print).
- `viewer/`: v5 export. `viewer_v4/`: the v4 export as it was before.
