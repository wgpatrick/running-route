# printer_v8: v7 redesigned for function

Everything here is simulated. Nothing has been built.

`designs/printer_v8.py` starts from `designs/printer_v7.py` (v7 was not edited). It passes all 12 verifiers with
**0 errors and 13 warnings** in two full runs with identical findings (`verify designs/printer_v8.py --no-render`,
2026-11-15, 18:18 to 18:35 and 18:35 to 18:53 UTC, report in `out/printer_v8/`). The designer worked from findings,
`AGENT.md`, the documents and the parts catalogue. Verifier, tolerance, twin and assembly sources were not read.
Nothing under `mechloop/` or `tests/` was edited and no catalogue part was added.

Under today's checks v7 fails with 6 errors (five clearances that close under tolerance, the probe's metal-free
zone entered in 44 % of builds) and its bed sags 0.092 mm under a 1 kg print at the worst corner.

The owner's brief for v8: "the most important thing is functionality". Part count, assembly time and cost are
reported, not optimised. They came out well above what the owner said they accept; see "What it cost".

## Result against the eight requirements

| # | Requirement | Result | Met |
|---|---|---|---|
| 1 | all 12 verifiers, 0 errors, two identical full runs, every warning explained | 0 errors, 13 warnings, findings identical in both runs | yes |
| 2 | 180 mm cube; the probe reaches the whole 180 x 180 mm | travel 180 x 214.5 x 183 mm (Y is 34.5 mm longer so the probe can reach); unprobed strip 0 mm on all four sides | yes |
| 3 | no clearance that can close; none below the process minimum; 1 mm or more on the toolhead; no margin thinner than its parts' scatter | 0 `clearance_closes_under_tolerance`, 0 `clearance_below_minimum`; smallest examined gap in the machine 1.0 mm; both switches and the bed are set at assembly with declared range | yes, with two thin margins listed below (Y belt plane, envelope) |
| 4 | bed trade study, pick on function, 1 kg sag at most 0.02 mm on the screw-only bound | four layouts modelled; chosen: three screws, one block per rail; **0.008 mm** screw-only (0.005 bonded); v7 0.092 | yes |
| 5 | M12 probe on a steel sheet, close to the nozzle, sheet modelled | E2E-X5ME1 with separate nuts in a closed hole, 34.5 mm behind the nozzle; sheet and magnet are declared stand-ins; bed limited to 80 degC | yes; the steel-sheet sensing distance is unverified |
| 6 | no bed weight on a flexible coupler; screw not held at the top | no coupler at all: each screw stands in two 608 bearings, pulley hub on the upper one; tops free | yes; bearing data is the catalogue's "typical" |
| 7 | beat v6 on the twin if function allows | X 79.3 Hz (v6 78.2), **Y 58.8 Hz (v6 60.0)**, owner's acceleration 6,000 (v6 6,300), with Klipper 4,800 (v6 5,000), ceiling 10,000 (v6 10,000) | **no**: equal to v6 within the scorecard's ranges, not better; clearly better than v7 |
| 8 | what v7 had right stays right | relay neutral, DD11 inlet, catalogue fan and duct, sub-assemblies, over-travel all kept; the coupler is gone | yes |

## Per-verifier result and every warning

| Verifier | Errors | Warnings | What the warnings are |
|---|---|---|---|
| geometry | 0 | 0 | |
| interference | 0 | 0 | |
| tolerance | 0 | 0 | |
| manufacture | 0 | 7 | (1) `hole_smaller_than_thickness`, back plate: 3.4 mm holes in 5 mm sheet; as v7. (2, 3) `load_across_layers`, `z_drive_mount` and `z_pedestal_fr`: the load is the screw's thrust pressing the part down onto the rail, so the layers are in compression, not pulled apart; factor of safety 77 and 98. See checker note 5. (4, 5) `holes_too_close`, both Y plates: 2.05 mm of steel between a belt slot and a guide-block screw hole (3 mm wanted). New with the 12 mm belt; it carries the belt anchor (about 40 N). (6) `hole_smaller_than_thickness`, tray: the Pi's M2.5 holes; as v7. (7) `holes_too_close`, inlet panel: SCHURTER's own pattern; as v7 |
| ratings | 0 | 3 | (1) `cantilever_on_guide_blocks`: "4.21 kg hangs 132 mm from its 2 guide blocks ... nods at about 62 Hz and sags 0.015 mm per kg". The check does not count the three lead screws, which are what holds this bed's tilt. Checker note 2. (2, 3) `uncatalogued_cots`: the magnetic sheet and the print sheet, declared stand-ins |
| motion | 0 | 0 | |
| subsystems | 0 | 0 | |
| electrical | 0 | 1 | `cutoff_depends_on_mcu`, hotend: as v7 |
| assemblability | 0 | 1 | `unsupported_step`: one part must be held; as v7 |
| fea | 0 | 1 | `bed_level_changes_over_travel`: "rails' running accuracy over a block spacing of 0 mm ... 0.110 mm". The formula takes the bed's tilt from the blocks alone; with one block per rail and three screws the screws set the tilt. Checker note 2 |
| printing | 0 | 0 | |
| requirements | 0 | 0 | |

## The bed-support trade study

Four layouts were built as verifiable models from one file (`Z_LAYOUT` and `Z_BLOCKS` in `designs/printer_v8.py`;
study files in `designs/studies/`). All four have the same bed (8 mm plate on four posts, below), the same frame
and the same gantry, so the differences are the support. Variants (a), (b) and (c) were run through geometry,
interference, ratings, tolerance and fea (all pass, 0 errors); (a) and (b) also through `assemble`. They are not
finished machines: motion, electrical and assembly checks were not run on them, variant (b) has no tie for the
plate and no worked-out belt route.

| | (a) cantilever, stiffened | (b) two screws, a rail each side | (c) three screws, two blocks per rail | **(d) three screws, one block per rail (chosen)** |
|---|---|---|---|---|
| What it is | v7's layout: back plate on four blocks, one rear screw; a 3 mm steel gusset above each arm | 2020 upright, rail and two blocks at each side; side plates, two cross arms; a screw beside each upright | (d) with a second block on each rail | back plate on two blocks, two arms, front plate; screws at rear centre and both front ends |
| 1 kg at the worst print corner, screw-only / bonded | 0.022 / 0.016 mm | 0.005 / 0.004 mm | 0.004 / 0.003 mm | **0.008 / 0.005 mm** |
| 20 N hand load there, screw-only / bonded | 0.045 / 0.034 mm | 0.009 / 0.007 mm | 0.008 / 0.006 mm | 0.016 / 0.011 mm |
| Tilt across the print area under 1 kg, screw-only | 0.019 mm | 0.005 mm | 0.005 mm | 0.021 mm |
| Screw line to mass centre; moment on the guides | 138 mm; 5.9 N.m | 15 mm; shared | 31 mm; shared | 27 mm; shared |
| Screws redundant in tilt (harness count) | 0 | 1 | 2 | 2 (see text) |
| A 0.02 mm height difference between screws becomes | n/a | 0.007 mm tilt, 76 N on a block, 31 N on a nut | 0.012 mm tilt, **87 N on a block, 41 N on a nut** | 0.017 mm tilt, **0 N on a block, 2.8 N on a nut** |
| Level change over travel (harness formula) | 0.061 mm | 0.038 mm | 0.061 mm | 0.110 mm (formula ignores the screws: checker note 2) |
| Two rails parallel as built (99 %) / Hiwin allowable | 0.83 / 0.009 mm, set at assembly | 1.06 / 0.009 mm, set at assembly | 0.78 / 0.009 mm, set at assembly | 0.96 / 0.009 mm, set at assembly |
| Nut off the screw's axis (99 %) / float provided | 1.4 / 2.2 mm | 1.8 / 2.2 mm | 1.8 / 2.2 mm | 1.9 / 2.2 mm |
| Bed level needed (99 %) / provided | 0.96 / 4.0 mm | 1.00 / 4.0 mm | 0.82 / 4.0 mm | 0.79 / 4.0 mm |
| Hot plate (60 K): gap change / bow | -0.04 / 0.06 mm | -0.08 / 0.04 mm | -0.06 / 0.04 mm | -0.07 / 0.03 mm |
| Parts | 355 | 350 | 398 | 386 |
| Bill of materials | $776 | $786 | $810 | $787 |
| Assembly estimate | 77.4 min | 77.1 min | not run | 84.7 min |
| Drivers needed | 4 | 4 | 4 | 4 |

A fourth idea, belt-driven Z, was not modelled: with a 2 mm lead the screws are self-locking and need no brake,
which a belt-hung bed would.

**Decision: (d).** Reasons, in order:

1. Every screw layout meets the 0.02 mm target with room; the stiffened cantilever misses it by a tenth
   (0.022 mm). So stiffness alone does not separate (b), (c) and (d).
2. What separates them is what happens when the screws are not exactly at one height. They never are: a belt
   holds them to the same angle, not the same height, and rolled T8 screws differ in lead (no figure in the
   catalogue; the harness assumes 0.02 mm). In (b) and (c) the rails hold the carrier's tilt rigidly and the
   screws hold it too, so a 0.02 mm difference puts 31 to 41 N on a nut. The nuts in this design are floating
   and held down only by the bed's weight, about 14 N each. So in (b) and (c) a nut lifts off for any
   difference above roughly 0.01 mm, and the bed is then carried as a cantilever on the rails: the low
   deflection in the table is not what the owner would get. In (d) the same difference puts 2.8 N on a nut
   and tilts the bed 0.017 mm: all three nuts stay seated and the screws really set the plane.
3. (d) keeps v7's rear rails and frees the sides (the toolhead loom, the mains inlet and the supply are where
   (b)'s uprights and cross arms go).
4. (a) is the cheapest (31 fewer parts, $11, about 7 minutes) and exactly constrained. It is the fallback if
   the owner prefers fewer parts over a five times stiffer hand-load figure: 0.022 mm against 0.008 mm, 0.045
   against 0.016 mm.

One motor and a closed belt rather than three motors: the catalogue board has four drivers and Y already takes
two motors on one; a belt cannot lose synchronisation at power-up (independent motors: two full steps, 0.02 mm
on this screw, per motor). What is given up: automatic tramming. Tramming is done once at assembly on the four
bed posts' nuts. `[z_tilt]` is not used and the multi-Z firmware path is not exercised: the generated
`printer.cfg` has one `[stepper_z]`, and real Klipper loads it (below).

### What the harness says about (d) that I believe is wrong

The harness counts (d) as "over-constrained in tilt by 2 screws", the same as (c), yet its own force figure for
(d) is 0 N on a guide block. It also raises two warnings on (d) that it does not raise on (c): the bed "hangs
132 mm from its 2 guide blocks" and the level changes 0.110 mm over travel. Both treat the blocks as the only
thing holding tilt. That is the physically right design drawing two findings; it is reported, not designed
around. See checker note 2.

## The design

### Z stage

- **Three T8 x 2 screws, 300 mm**, at the rear centre (0, 180) and over the two bottom side rails at the front
  (x = +/-160, y = -101). They end 60 mm under the top rails; nothing holds their tops.
- **Bearings, not a coupler.** Each screw stands in two catalogue 608 bearings 37 mm apart. The 20-tooth pulley
  (8 mm bore) is set-screwed to the screw and its hub rests on the upper bearing's inner ring: that is the
  path for the bed's weight. Front: printed PETG pedestals on the tray, two M5 through the tray into the
  rail's T-nuts. Rear: a printed PETG mount on the bottom back rail with a straight bore (lower bearing, a
  printed sleeve, upper bearing, all from the top), which also carries the motor and the tensioner.
- **Drive.** One 40 mm NEMA 17 at 1.0 A (v7: 34 mm at 0.28 A) hangs under the mount's slab beside the rear
  screw, 20-tooth pulley, 1:1. Closed 6 mm GT2 loop, 1,055.4 mm needed against a 1,056 mm (528-tooth) belt,
  +/-3 mm at the tensioner: a toothed idler on the belt's back in a slot. Wrap: motor 139 degrees (7.7 teeth),
  front screws 120 and 121, rear screw 60 (3.3 teeth; it turns one screw, about 1 N of belt force). Drive
  margin 4.7 (required 3.0). Motor case 41 degC, so the mount is PETG.
- **Guides.** v7's two rear uprights, now with one MGN12H block each on 250 mm rails (v7: two each on 300 mm).
- **Carrier.** 5 mm aluminium back plate on the two blocks, two 2020 arms, a 3 mm steel front plate across the
  arms' front ends; each arm end has an M5 into its tapped end and a cast corner bracket. Three printed nut
  blocks with floating nuts (+/-2.2 mm; v7 +/-1.3). The back plate is cut away at the bottom centre where the
  belt runs to the rear screw.

### Bed

- **8 mm cast plate** (v7: 6 mm), 220 x 236.5 mm: 16.5 mm longer at the front than the print sheet, so the hot
  nozzle is over the plate, not over the supply, while the probe measures the front rows.
- **Four posts instead of silicone columns.** Each is an M5 x 90 cap screw: head counterbored in the plate,
  a jam nut under the plate, 59 mm of free screw, then a laser-cut steel tab bolted on an arm with a nut above
  and a nut below. The posts are 4 mm inside the print area's corners in X. Along its axis a post is about
  45 N/um; sideways it bends. The two nuts at each tab are the levelling adjustment: +/-4 mm of thread
  declared, 0.79 mm needed.
- **Thermal growth.** A flat 1.5 mm steel tie on a cast bracket holds the plate at the rear centre in X, Y and
  yaw and is soft vertically. The plate grows away from it: 0.30 mm at 60 K in the model, taken by the posts
  bending. Hand estimate of the stress in a front post at 60 K: about 190 MPa in a class 12.9 screw (not a
  verifier result). FEA with every joint bonded: gap under the nozzle -0.07 mm, bow 0.03 mm (limits 0.1).
  The steel sheet is left out of that case: it is held by the magnet and slides; bonded to the plate in the
  model it bows the stack 0.3 mm as a bimetal, which a magnet-held sheet does not do. Checker note 4.
- **Print sheet and magnet: stand-ins.** The catalogue has neither. `bed` is a 220 x 220 x 0.5 mm spring-steel
  sheet (0.19 kg, PEI not drawn), `bed_magnet` a 1 mm magnetic sheet (0.18 kg). Every figure on them is a
  typical value. The bed is limited to **80 degC** in the firmware block (targets 60 and 80, `max_temp` 90):
  that is the working limit taken for a standard magnetic sheet. With a high-temperature magnet the probe's
  85 degC rating would be the limit, as in v7.

### Probe

- **OMRON E2E-X5ME1** (catalogue part, `nuts="separate"`, `add_probe_nuts`): M12, unshielded, 5 mm on iron.
  It reads the steel sheet. Face 2.0 mm above the nozzle; it switches with the nozzle 2.0 to 4.0 mm above
  the bed over unit spread and temperature (2.5 to 3.5 over unit spread alone). Face-to-nozzle margin from
  the toolhead's stack-up 0.68 mm, so the clean window is 0.7 to 3.3 mm. No `probe_trigger_margin_thin`.
- **Where.** 34.5 mm straight behind the nozzle, in the closed hole of a printed ABS mount that the Roto's own
  two screws hold (they are M3 x 50 now). That is as close as the sensor's 40 mm metal-free zone and the
  Roto's rear face allow: 26.2 mm from the HeaterCore's surface where 20 is asked, nothing metal within
  1.5 mm of the zone in any of 3,000 builds. The sensor's own nuts are 7 to 11 and 20 to 25 mm behind the
  face, inside the 15 mm the sheet asks to be free of mounting metal; the check does not count them
  (checker note 6).
- **Reaching the whole area.** The Y working range is -124.5 to +90 mm. To make room: the front top rail sits
  30 mm lower and the X beam passes over it; the Y rails are moved 28.5 mm forward; the Y idlers stand 5 mm
  beyond the frame's front end on L-shaped mounts; the X motor overhangs the front by 18 mm when the front
  rows are probed. `mechloop tune`: first-layer gap error over the whole 180 x 180 mm 0.097 mm RMS / 0.305
  worst without the mesh, **0.007 / 0.017 with it** (v7: 0.011 / 0.036 with strips unprobed).
- The Revo is turned so its leads leave to the left.

### Endstops

Both switches are set at assembly, declared as `Adjustment(..., "endstop")`. No `endstop_window_under_tolerance`.

- **X**: the switch hangs under the left Y plate's land on 4 mm spacers; the end face of the X guide block
  presses the lever. Its two screws run in +/-2 mm slots. Stack-up 0.66 mm (99 %).
- **Y**: at the rear, on a sheet mount on the inner face of the right top rail; the right Y plate's rear edge
  presses the lever. The mount slides on two T-nuts, +/-5 mm declared. Stack-up 1.59 mm (99 %). **Y homes to
  its maximum** (`homing_positive_dir: true`).
- The axis must still be stopped by the signal, as in v7.

### Toolhead clearances

| v7 gap | v8 |
|---|---|
| probe arm to key, 0.20 mm | both parts gone |
| X beam to endstop nut, 0.35 mm | switch moved; nearest thing to the rail is now 1.0 mm |
| Roto to belt-block screw heads, 0.20 mm | heads 1.2 mm under the face (counterbore 4.2) |
| guide block to belt block, 0.50 mm | 1.5 mm |
| Roto to duct, 0.50 and 0.55 mm | 1.35 mm; plenum 1.5 mm behind the Roto |
| Roto to guide-block screw heads, 0.20 mm (not flagged) | M3 x 6 in 5 mm counterbores: 2.0 mm |

### Y drive

v7 went to 9 mm belts because 12 mm belts put 37.4 N on the motor shafts 13.25 mm from the face, where 31.7 N
is allowed. v8 uses 12 mm belts at Gates' own installation tension (18.7 N per span) with the belt plane
**10.25 mm** from the face: motor and idler mounts in 2 mm steel sheet (v7: 3 mm), pulleys hub-outboard, a
1 mm washer under each idler. Allowed there 41.0 N: load 0.91 of the limit (v7: 0.79). The limit is still one
drawing line whose meaning is inferred. 12 mm belt and pulleys are generic, not Gates stock in 2 mm pitch.

### Frame and electronics

Frame 50 mm taller (FZ 394, v7 344) for the posts and the Z belt plane; overall 388 x 419.3 x 463 mm in a
420 x 420 x 480 envelope. Front top rail 30 mm lower. Corner brackets of both top cross rails moved under the
rails (the rear ones stood 0.1 mm from the part fan in the corner of the travel). Supply turned to lie along Y
so both tray edges are free for the pedestals; relay moved; left loom along the front bottom rail; toolhead
loom clamped on the rail's upper land behind the Y switch's mount. 180 W bed heater on the board's own output
as in v7: 7.4 A, supply at 68 %.

## v6, v7, v8

v6 and v7 figures are from `docs/PRINTER_V7.md` and the brief; v8 from the full run and `score --assembly` of
2026-11-15 18:35 to 18:53 UTC.

| | v6 | v7 | v8 |
|---|---|---|---|
| Passes all 12 against today's checks | no | no (6 errors) | yes |
| Parts | 317 | 309 | **386** |
| Total mass | 10.24 kg | 10.25 kg | 12.44 kg |
| Bill of materials | $719 | $727 | $787 |
| Fabrication: machining / cutting / filament | $112 / $15 / $2 | $112 / $15 / $2 | $119 / $21 / $4 = $144 |
| Parts + fabrication | $848 | $856 | **$931** |
| Custom parts: machined / sheet / printed | 2 / 11 / 7 | 2 / 13 / 9 | 2 / 20 / 13 |
| Printed | 62 g, 4.4 h | 69 g, 4.9 h | 178 g, 11.1 h |
| Moving mass X / Y / Z | 0.351 / 1.319 / 2.677 kg | 0.394 / 1.382 / 2.679 kg | 0.344 / 1.339 / 4.207 kg |
| Nozzle stiffness X / Y, screw-only (bonded) | 1,435 / 2,036 (2,311 / 2,409) | 1,535 / 2,099 (2,342 / 2,466) | 1,542 / 2,075 (2,332 / 2,438) N/mm |
| Resonance X / Y | 78.2 / 60.0 Hz | 74.0 / 54.6 Hz | 79.3 / 58.8 Hz (73.7 to 87.4 / 55.4 to 63.4) |
| Acceleration an owner would run, built-in planner | 6,300 | 5,200 (3,600 to 8,100) | 6,000 mm/s^2 (4,200 to 9,200) |
| Same with Klipper | 5,000 | 4,200 (3,400 to 5,500) | 4,800 (3,800 to 6,200) |
| Step-loss ceiling | 10,000 | 8,000 | 10,000 (8,000 to 12,000); Y loses steps first, at 12,000 |
| Cross-track RMS / worst (test cube) | 0.012 / 0.107 mm | 0.014 / 0.139 mm | 0.0125 / 0.107 mm |
| Benchmark print time | 2,571 s | 2,571 s | 2,571 s |
| Y belt, shaft load / allowed | 37.4 / 25.8 N | 28.4 / 35.7 N | 37.4 / 41.0 N |
| Y belts within 1 mm of plane | 98.4 / 99.0 % | 99.3 / 99.1 % | **98.1 / 98.1 %** (standard error 0.25 %) |
| Drive margin X / Y / Z | 8.5 / 7.7 / 3.4 | 7.8 / 7.4 / 3.4 | 8.7 / 7.6 / 4.7 |
| **Bed: 1 kg at the worst print corner, screw-only (bonded)** | not measured | 0.092 (0.067) mm | **0.008 (0.005) mm** |
| **Bed: 20 N hand load there** | not measured | 0.189 (0.138) mm | 0.016 (0.011) mm |
| Bed: tilt across the print area under 1 kg | | 0.108 mm | 0.021 mm |
| Bed: screw line to mass centre | | 130 mm, 3.4 N.m on the guides | 27 mm |
| **Smallest clearance between non-mating toolhead parts** | | 0.20 mm | **1.0 mm** |
| Clearances that close under tolerance | | 5 errors, 3 warnings | 0 |
| Z offset needed / provided | 1.62 mm | 1.48 / 1.65 mm | 0.99 / 1.65 mm |
| Bed level needed / provided | 1.21 mm | 1.17 / 1.5 mm | 0.79 / 4.0 mm |
| Probe | stand-in | E2E-X10ME1; strips of 36.5 / 13 / 4 / 4 mm unprobed | E2E-X5ME1 on steel; 0 mm unprobed |
| Bed temperature limit | 100 degC | 85 degC | 80 degC (magnet) |
| Bed to 60 degC | | | 262 s (180 W under a 1.16 kg plate) |
| Assembly estimate | 66.0 min | 64.6 min | **84.7 min** |
| Needs holding / fasteners / fastener types | 88 / 152 / 10 | 81 / 151 / 10 | 96 / 172 / 15 |
| From below / turned / tool changes | 14 / 5 / 5 | 17 / 4 / 7 | 53 / 12 / 6 |
| Warnings | 8 | 7 | 13 |

### What it cost

The owner accepted about 20 more parts and 5 more minutes. v8 is **77 more parts, 20 more minutes and $75 more**
than v7, $31 over the $900 guide. Where the parts went (counted from the two files): Z drive, screws, nut
blocks and front plate +53 (two more screws, six bearings, four pulleys, idler, two pedestals, sleeve, front
plate, two more nut blocks, with their screws and nuts); bed posts, tabs and tie +32 (40 parts where four
columns and four screws were 8); endstops +3; print sheet and magnet +2; probe -1; Z guides and carrier -12
(two blocks and their screws fewer).
What it bought: the bed figures above, a probe that covers the print area, and no gap that can close. The
stiffened cantilever (a) would save 31 parts and about 7 minutes and give a quarter of the stiffness.

### What got worse than v7

- Parts, cost, assembly time, mass, printed hours (above). From-below operations 17 to 53, turns 4 to 12.
- Y belts within 1 mm of plane: 98.1 % against 99.2 %. The cause is the 34.5 mm of extra Y travel (the rails'
  direction error acts over a longer stroke); belt width, mount thickness, idler bolt spacing and frame
  height were each tried and change nothing. It meets the 98 % requirement by less than one standard error.
- Bed limited to 80 degC (v7: 85).
- Bed to 60 degC in 262 s: the plate is 8 mm.
- The machine is 50 mm taller, and its Y idlers and, at the front of the probing travel, its X motor stand
  beyond the frame's front.

## Every clearance under 1 mm that remains

None. The tolerance verifier examined 25 pairs drawn under 1.5 mm; none closes and none is below its process
minimum. Fifteen are drawn at 1.00 mm: back plate to tie, the lead screws' lower ends to the tray, the back
rail and the drive mount's floor, magnetic sheet to the recessed heads of the four posts and the two tie
screws, plate to print sheet (the magnet's thickness), Y idlers to their mounts (the 1 mm washer), X guide
block to the tip of the Roto's lower screw. Next is 1.05 mm, X rail to the X switch's nut. Every one closed in
0 of 3,000 builds and, by its spread, in fewer than 1 in ten million (6 standard deviations or more).

Gaps the tolerance check does not look at (over 1.5 mm as drawn) that I would still watch on a real machine:
probe nut to the Roto's rear face 1.4 mm (same sub-assembly, so not listed); toolhead rear (probe nut, fan
screws) to the top back rail 2.5 mm at the rear end of the Y over-travel; Y plate to idler flange 1.5 mm and
to the idler mount 3 mm at the front end; Y guide block to the Y switch mount 3.0 mm; part fan to the right
top rail 3.5 mm at the X end.

## Thinnest margins

| Margin | Value | Against |
|---|---|---|
| Envelope in Y | 419.34 mm | 420 (0.66 mm) |
| Y belts within 1 mm of plane | 98.1 % +/-0.25 % | 98 % |
| Y motor shaft load | 0.91 of an inferred limit | 1.0 |
| Z belt against stock length | 1,055.4 mm needed | 1,056 mm belt, +/-3 mm tensioner; the stock length is not confirmed |
| Lead-screw nut float | 1.9 mm needed (99 %) | 2.2 mm |
| Toolhead rear to the top back rail | 2.5 mm at the over-travel end | |
| Toolhead mass | 0.344 kg | 0.40 |
| Rear screw's belt wrap | 60 degrees, 3.3 teeth | no figure; about 1 N of belt force |
| Front post stress at 60 K | about 190 MPa (hand estimate) | 12.9 screw |

## Scores and firmware in the loop

All on the final file (md5 9f4017d8...), 2026-11-15.

`score designs/printer_v8.py --assembly` (18:35 to 18:52 UTC): figures in the comparison table. Toolhead tilt
term on X 466 N/mm (one MGN12H, arm 43 mm); melt rate cap 12 mm^3/s, 4.9 asked.

`score designs/printer_v8.py --firmware klipper --firmware-only` (18:35 to 18:44 UTC, Klipper 29d4ec2). Real
Klipper loaded the generated `printer.cfg` (one `[stepper_z]`, Y homing to maximum, probe offset 0 / 34.5 mm,
mesh 0, 34.5 to 180, 222.5) and planned every print.

| | Shaper and pressure advance off | As configured |
|---|---|---|
| Input shaper | none | X: EI 98.2 Hz; Y: MZV 57.4 Hz |
| Cross-track RMS / worst at 4,000 mm/s^2 | 0.0080 / 0.093 mm | 0.0059 / 0.047 mm |
| Corner bulge | 0.40 mm | 0.15 mm |
| Sweep | clean at 4,000, 6,000, 10,000, 12,000, 16,000; lost steps from 24,000; **8,000 and 20,000 could not be decoded** | clean to 48,000, the highest tried |
| Klipper's shaper rule / what an owner would run | | 9,600 / 4,800 mm/s^2 (3,800 to 6,200) |

The two undecoded points are `firmware_error: Decoded X steps end 8.886 mm from the G-code's last position;
the stream was not decoded correctly`. Klipper raised nothing (its log ends normally). The scorecard therefore
reports "highest clean 6,000" for the shaper-off sweep, which is the decoder's failure, not the machine's.
Checker note 7.

`tune designs/printer_v8.py` (18:35 to 18:37 UTC): shapers as above (predicted resonances 77.7 / 57.1 Hz);
pressure advance 0.042 s; bed mesh 5 x 5 over the whole print area, result under "Probe".

Firmware in the loop, `print designs/printer_v8.py examples/motor_bracket.py:bracket --firmware klipper
--trajectory --out out/printer_v8/fil/bracket` (18:49 to 18:58 UTC): Klipper accepted the generated `printer.cfg`
and planned the whole print with no message. 255 layers, 3,891 s, 15.3 g. Outline match 98.4 % mean, 97.7 %
worst; boundary deviation 0.030 mm mean, 0.044 worst; no layer shift; 0 collisions in 4,075 poses; the lowest
thing after the nozzle is the probe, 2.0 mm above the nozzle plane; peak step rate 19,753 /s of 263,000;
first-layer gap error 0.0017 mm worst. One warning: corner bulge 0.40 mm (v7: 0.35), with pressure advance at
the tuned 0.042 s.

The score, tune and print jobs ran side by side with the second full verify; the design file did not change
after the first full verify.

## Checker behaviour I think is wrong or worth a look

1. **The tolerance stack-up locates the bed through whichever joint chain it finds, not through what carries
   it.** With the plate on four posts and a thin locating tie, the bed's level came out at 5.3 mm (99 %) with
   a bent tie and 8.3 mm with the flat tie on a cast bracket: the stack-up ran through the tie, a part that is
   soft vertically by design. Declaring `d.join("bed_plate", "bed_post_tab_i", ...)` (true: the post and its
   nuts hold the plate on the tab) gives 0.79 mm. Reproduce: in `designs/printer_v8.py` delete the line
   `d.join("bed_plate", f"bed_post_tab_{i}", "post with jam nuts")` and run `--only tolerance`:
   `adjustment_too_small ... bed is up to 8.26 mm out of level`. With the tie also removed the bed is "a part
   that nothing ties to the base" although four screws clamp it. A screw that clamps two parts which do not
   touch is not seen as a joint.
2. **Three screws with one block per rail are judged as a cantilever.** `ratings.cantilever_on_guide_blocks`
   ("hangs 132 mm from its 2 guide blocks ... sags 0.015 mm per kg") and `fea.bed_level_changes_over_travel`
   (0.110 mm, "block spacing of 0 mm") take the tilt from the blocks only. The same run's `bed_support` gives
   0.008 mm per kg with the screws in. Reproduce: the design itself; compare
   `designs/studies/v8_bed_c_three_screws_two_blocks.py` (neither finding, although its rails fight its
   screws: 87 N on a block for 0.02 mm).
   Also `constraint.redundant_screw_supports` is 2 for both, while `force_on_a_guide_block_n` is 87 and 0.
3. **`screw_synchronisation` assumes 0.02 mm between belt-tied screws and that every nut stays seated.** Lead
   differences between rolled screws are not in the catalogue or the model. For (b) and (c) the force that
   follows (31 to 41 N on a nut) exceeds a floating nut's seating load; the deflection figures do not know
   that. This decided the trade study and rests on my reading, not on a finding.
4. **A magnet-held sheet is bonded in `ThermalCase`.** With `bed` (steel, joined "magnet") in the case:
   `thermal_bow 0.315 mm`, `thermal_gap_change +0.155 mm`. Without it: 0.034 and -0.065. I left the sheet out
   and say so; a join kind that slides would be the right fix.
5. **`load_across_layers` says a compressive load "pulls the layers apart".** `z_pedestal_thrust` is 61 N
   pressing the bearing seat down on a part printed standing on its foot.
6. **The sensor's own nuts are not counted as metal in its metal-free zone.** Convenient, and probably what
   OMRON's mounting drawing implies, but the front nut is 7 to 11 mm behind the face where the rule asks for
   15. Worth a sentence in `AGENT.md` either way.
7. **`score --firmware klipper`: two of eleven shaper-off prints "could not be decoded"** (text above), at
   8,000 and 20,000 mm/s^2, with clean results at 10,000 to 16,000 between them. v7 had none. I do not know
   whether Y homing to maximum or the longer Y axis triggers it. Files: `out/printer_v8/score/fw_plain_a2/`,
   `fw_plain_a5/`.
8. **The two full runs give identical findings but not identical metrics**: `geometry`, `electrical` and
   `assemblability` differ (same length or a few bytes). `docs/REFERENCE_MACHINE.md` section 8.3 names the
   electrical one: firmware tuning read from the previous run's report.
9. **Belt-plane scatter grows with travel that is only used for probing.** Not wrong, but the 98 % line is
   now decided by the 34.5 mm the nozzle never prints in.
10. v7's notes 3 (sub-assemblies raise the time estimate) and 5 (`probe_near_hot_bed`) still apply; its notes
    1 and 2 are fixed by `nuts="separate"` and the toolhead margin.

## Decisions the owner should confirm

1. **Three screws on one belt with one guide block per rail**, at 77 more parts than v7. The alternative is
   the stiffened cantilever (a): 31 fewer parts, 0.022 mm per kg.
2. **Tramming once by hand** on the bed posts' nuts; no `[z_tilt]`.
3. **Bed on four M5 flexure posts and a tie**, no springs or silicone. The bed cannot be re-levelled with
   thumb screws; the mesh takes the rest.
4. **Magnetic sheet and 80 degC**. A high-temperature magnet would allow 85.
5. **Y axis 34.5 mm longer, homing to the rear**, the front top rail 30 mm lower, idlers beyond the frame's
   front, envelope used to 0.66 mm.
6. **12 mm generic belts on Y on 2 mm mounts**, shaft load at 0.91 of an inferred limit.
7. **40 mm Z motor at 1.0 A**.
8. **Part count is no longer a requirement in the file.** v7's "at most 320 parts" is replaced by a line that
   prints the count. This is the one requirement loosened, on the owner's stated priority. The stand-in
   requirement now allows exactly the two sheets. All other requirements are v7's or stricter.
9. **The speed target is not met**: v8 equals v6 within the ranges and does not beat it. The Y axis carries
   the same gantry on belts 20 mm longer.

## Needed vendor data

| Part | What is missing | Why it matters |
|---|---|---|
| Spring-steel print sheet, 220 mm | thickness, steel grade, mass, a part number | probe distance, bed mass |
| Magnetic sheet | thickness, mass, temperature limit, adhesive | the 80 degC bed limit |
| OMRON E2E-X5ME1 | sensing distance on a thin spring-steel sheet (the 5 mm is for 1 mm iron, 15 x 15 mm), repeatability | the whole probe window |
| GT2 closed belt, 6 mm | stock lengths near 1,056 mm | Z drive |
| GT2 20-tooth pulley, 8 mm bore | a real part with hub diameter (it must clear the 608's outer ring: at most about 18 mm) | the axial load path |
| GT2 12 mm belt and 20-tooth pulleys, 5 mm bore | a maker with data; Gates has no 12 mm in 2 mm pitch | Y drive |
| 608 bearing | maker's axial rating and internal clearance | axial load path (catalogue: "typical, unverified") |
| T8 x 2 screw and nut | lead accuracy, straightness, nut backlash and axial stiffness | synchronisation between screws |
| NEMA 17, 40 mm (17HS16-2004S1) | radial shaft-load limit | Z belt: 17.4 N at 15.2 mm, not judged |
| NEMA 17, 48 mm (17HS19-2004S1) | what "LENGTH 20mm: 21N MAX" means | Y belts |
| Hiwin MGN12 | accuracy class of the rails bought; moment rigidity of a block | level over travel, the single-block guide |
| M5 washer, 1 mm | modelled as a 1 mm spacer of unknown range | Y idler position |
| For the better Z option | integrated lead-screw motor 17E19S1684MB4-300RS: holding torque, current, resistance, inductance, rotor inertia, mass, body and nut dimensions, thrust rating; or a T8 thrust-bearing block | would remove pulleys' set screws from the load path |

## Still unverified

- That thin spring steel on a magnet switches the sensor like OMRON's iron target. If it switches at 3 mm
  instead of 5, the window closes to nothing at a 2 mm face height: check on the bench before anything else.
- Lead differences between the three screws, and so how evenly they carry.
- The flexure posts: fatigue of a threaded M5 bent 0.3 mm at each heat cycle; that the jam nuts stay tight.
- The bed's own vibration on four slender posts and a tie. No modal case was written for it.
- Pulley set screws carrying each screw's axial load (10 to 20 N) on a plain 8 mm screw end.
- The printed pedestals and mount under years of load (PETG creep); bearing seats printed 22.4 mm.
- 2 mm steel Y mounts: stiffness under 37 N of belt pull is not in any FEA case.
- The frame: 50 mm taller, front top rail lowered. Frame stiffness does not enter the twin.
- The Z belt's 1,056 mm stock length; a toothed idler running on the belt's back.
- Air: the duct is v7's, 10 mm further right, with the fan on its upper holes.
- The probe mount's stiffness (not in an FEA case) and heat on it 11 mm behind the Roto.
- Everything v7 listed that v8 did not touch, and everything `AGENT.md` lists as not checked.

## Allowances and overrides

- `allow_overlap("hotend", "extruder")` as v7; the automatic thread overlaps.
- `d.join("bed_plate", "bed_post_tab_i", "post with jam nuts")` and the nut joins: checker note 1.
- `d.join` for bearings in their pockets, the sleeve, the sheet on the magnet ("magnet"), the magnet ("bond").
- `process="purchased"` on the extruder; `print_up` on printed parts.
- No limit, threshold, DFM limit, tolerance or electrical requirement was changed.
- Requirements changed: part count (decision 8); stand-ins (the two sheets); "nozzle stays over the bed plate"
  now reads the aluminium plate; the lead-screw and rail requirements cover all three screws.

## What the verifiers caught, and the fixes

| Finding | Fix |
|---|---|
| `adjustment_too_small`: nut 1.4 to 1.8 mm off the screw's axis, float 1.3 | float 2.2 mm |
| `clearance_closes_under_tolerance`: bed posts in T-nuts scatter 1.8 mm | posts through tabs with two nuts |
| `thermal_bow` 0.315 mm | checker note 4 |
| `adjustment_too_small`: bed 5.3, then 8.3 mm out of level | checker note 1 |
| `envelope_exceeded` 425 mm, then 421.2 | Y motors turned so the lead leaves downwards; motor mount 2 mm shorter |
| `motion_collision`: tool plate into the X switch | tool plate's lower left edge 3 mm back |
| `trapped_part`: lower rear bearing, Z motor | straight bore with a sleeve; skirt under the motor removed |
| `requirement_failed`: nozzle 14.5 mm off the plate when probing | plate 16.5 mm longer at the front |
| `bend_too_tight`, `flex_span_crosses_part` (five) | looms re-routed |
| `connector_blocked`: relay in front of the inlet's earth terminal | relay moved |
| `clearance_closes_under_tolerance`: part fan 0.13 mm from a corner bracket at the travel's corner | brackets under the rails |
| `drive_undersized` on Z: 1.35 | 40 mm motor at 1.0 A |
| `hole_too_close_to_edge` (error), `wall_single_bead`, `needs_support`, `print_warp_risk` | Y switch mount, belt block, drive mount reshaped; PETG |

Two full verifies of the final file, two earlier full verifies of the two-block version, about 40 partial
runs, 9 study runs, 2 `assemble` runs. One mistake of mine cost a rebuild of part of the file from a snapshot.

## Files

- `designs/printer_v8.py`: the design.
- `designs/studies/v8_bed_a_cantilever.py`, `v8_bed_b_two_screws.py`, `v8_bed_c_three_screws_two_blocks.py`:
  the trade-study variants (they load `printer_v8.py` with another layout).
- `out/printer_v8/`: `report.json`, STEP, DXF profiles, `electrical/printer.cfg`, `wiring.csv`, `scores.jsonl`,
  `score/`, `tune/`, `fil/bracket/`. Renders were not made (`--no-render`).
- One row in `README.md`, one paragraph in `STATUS.md`.
