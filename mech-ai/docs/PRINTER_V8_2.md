# printer_v8_2: three direct Z motors, no belt

Everything here is simulated. Nothing has been built.

`designs/printer_v8_2.py` starts from a copy of `designs/printer_v8_1.py` (v8.1 was not edited). The owner: "there are
belts that drive 3 z shafts from one motor... that seems a bit like a nightmare. it seems a lot easier to have 3 separate
steppers that are directly coupled to a z shaft. no belts". Later review items folded in: a flush top front rail, no
ballast plate (captive nuts instead), visible bed-post joints with no tapped holes, and attachment notes on the bed stack.

It passes all 13 verifiers with **0 errors and 72 warnings** (`verify designs/printer_v8_2.py`, report in
`out/printer_v8_2/`), all 22 requirements met. Every warning is listed below.

## What changed against v8.1

### Z drive

| | v8.1 | v8.2 |
|---|---|---|
| Motors | one NEMA 17 40 mm on a laser-cut drive plate | three StepperOnline **17E19S1684AB4-330RA** lead-screw motors, one per screw |
| Screws | three T8 x 2 bars, 300 mm, in two 608s each | the motors' own Tr8x2 shafts, cut to 252 mm above the motor face, free at the top |
| Synchronisation | one closed 1138 mm GT2 belt, four pulleys, tensioner idler | none mechanical: Klipper `[z_tilt]`, `Z_TILT_ADJUST` |
| Screw supports | three towers of seven laser-cut plates, six 608s, shims, inverted top nuts | one 6.35 mm 6061 motor plate per screw on two aluminium spacer posts |
| Nuts | floating brass T8, gravity-seated (ballast: 12.7 mm front plate) | the same floating brass T8 nuts, **captive** under a keeper plate, no ballast |
| Driver | one SKR Mini E3 driver | three Octopus drivers (M3, M5, M6) |

**The motor.** StepperOnline 17E19S1684AB4-330RA (product page fetched 2026-11-16,
https://www.omc-stepperonline.com/anti-backlash-screw-nut-nema-17-external-48mm-stack-1-68a-lead-2mm-0-07874-length-330mm-17e19s1684ab4-330ra):
NEMA 17, 48 mm body, 0.44 N.m, 1.68 A, 1.65 ohm, 2.8 mH, Tr8x2 x 330 mm integral screw (0.01 mm per full step),
anti-backlash nut supplied, 46.30 USD. It is the current part number of the discontinued 17E19S1684AB2-330RA (same
figures, page gives 350 g). Not on the page and therefore marked unverified on the catalogue part
(`leadscrew_motor_17e19_ab4`, `mechloop/parts/vendor/stepperonline_17e19_ab4.json`): rotor inertia (68 g.cm2, taken from
the sister 17E19S1684MB4), mass (350 g, predecessor's page), body details (pilot, hole square, thread depth: sister model),
axial (thrust) rating (none stated), nut drawing. The datasheet PDF's host (files.omc-stepperonline.com) was refused by
this session's network proxy, so none of its drawing was read. The motor is drawn as two catalogue parts, body and
screw, so that the tolerance, bed-support and fit checks see an 8 mm screw rather than one 42 mm solid.

Why Tr8x2 and not the catalogue's Tr8x8 17E19S1684MB4: the lead angle at the pitch diameter is 5.2 deg; the trapezoidal
flank's friction angle at mu 0.10 to 0.15 is 5.9 to 8.8 deg, so the screw does not back-drive under a static load and the
bed stays where it is with the motors off (efficiency 0.36 to 0.46 by the same sums; the catalogue uses 0.35). The Tr8x8
has a 20 deg lead angle and back-drives. Tr8x2 also gives 0.01 mm per full step against 0.04. Derived, not tested.

**No top bearing.** Each screw runs free-ended from the motor's bearings. Reasons: (1) whip: the first critical speed of
a fixed-free 8 mm screw (root 5.5 mm, 252 mm free) is about 3,600 rpm; Z at its 12 mm/s maximum turns the screws at 360
rpm, a tenth of it. (2) A bearing at the top of a screw whose bottom is already held by the motor's two bearings
over-constrains it: run-out of the integral screw and any tilt of the motor plate would bend the screw between three
bearings and side-load the motor. Free-ended, the screw can follow the floating nut. (3) It saves the plates and
bearings the brief asked to remove.

**Motor mounts.** Each motor hangs under a 6.35 mm laser-cut 6061 plate: its 22 mm pilot sits in a 22.3 mm hole (the
plate locates the motor), four M3 x 10 from above thread 3.65 mm into the motor's own M3 holes (4.5 mm deep: 1.2 d,
0.85 mm short of the bottom), thread-locked. Two 10 mm OD aluminium spacers carry the plate; M5 x 70 bolts with washers
clamp plate, spacer (and, at the front, the electronics tray) to T-nuts in the bottom rail (4.65 mm into the T-nut),
thread-locked. The motor faces are at z 78; the screw tops at z 330, as v8.1's. The front plates are notched clear of the
front beam's end. FEA `z_motor_plate_thrust` (three times the whole bed's weight on one plate): factor of safety 56.7,
0.0023 mm.

**Screw cut to length.** The screw is sold 330 mm long; it must be cut to 252 mm above the face so its top stays under
the top rails and out of the toolhead's way (hacksaw, 0.5 mm chamfer, run the nut over the end; or ask StepperOnline for
a custom length). The catalogue part takes the cut length and says so in its SKU and description.

**Nuts and the lift.** The floating brass T8 nuts, nut plates and anti-rotation pins are v8.1's. New: each nut is
**captive**. A 3.175 mm laser-cut 6061 keeper sits under the flange, 0.1 mm clear of it, on two M3 through-bolts and
3.6 mm spacers with nyloc nuts: the flange is held between plate and keeper, still free to float sideways 2.6 mm, but the
carrier can no longer lift off it. That replaces v8.1's way of keeping the nuts seated (a heavy carrier with its mass
centre over the screws). The front nut plates are 9.525 mm now (6.35 in v8.1) and bolt to the front beam inboard of the
nut, because the front beam is 36 mm shorter (it ends at +/-152, clear of the front mounts' post bolts).

**Synchronisation.** `Z_TILT_ADJUST` (Klipper `[z_tilt]`, generated into printer.cfg):

| | x, y in the firmware's (nozzle) coordinates |
|---|---|
| z_positions (screws) | rear 90, 282.75; front-left -70, 1.75; front-right 250, 1.75 |
| points (nozzle; probe 34.5 mm behind it) | 90, 170; 15, 5; 165, 5 |

speed 100, horizontal_move_z 5, retries 5, retry_tolerance 0.0075 mm. Run it after homing at the start of every print
(it re-levels the screws at the print height, which the belt could not). The motors stay energised while Klipper runs;
at power-off the Tr8x2 screws hold the bed, and a power cycle needs a new `Z_TILT_ADJUST` (two full steps of possible
slip: 0.02 mm, the harness's figure).

### Electronics: BTT Octopus V1.1

Seven drivers are needed (X, two Y, E, three Z). `manta_m5p` has five. Chosen: **BIGTREETECH Octopus V1.1** (eight
sockets; catalogue `octopus_v11`, `mechloop/parts/vendor/bigtreetech_octopus_v11.json`). Reasons over the Manta M8P V2: its
manual, pin drawing and size drawing come from BTT's own repository and were read here (copies in vendor_cad/staging/),
Klipper's `generic-bigtreetech-octopus-v1.1.cfg` is in third_party and agrees with the drawing pin for pin, and it keeps
the existing Pi Zero 2 W host; the M8P V2 needs a CB1 / CM4 and its Klipper config is not in the checkout. Figures from
the manual: 160 x 100 mm, holes 150 x 90, 12 / 24 V (logic > 14.1 V), beds up to 300 W, 5 V rail 8 A; pins from the
drawing (rev 2026-02-01). Heater and fan current limits are not in the manual's text: 5 A and 1 A, marked unverified.

Wiring: X M0, Y M1, Y left M2 (now on its own driver, `[stepper_y1]`: invert its dir_pin or swap a coil pair), Z rear
M3, extruder M4, Z front-left M5, Z front-right M6, M7 spare. X and Y switches and the probe on STOP0 / STOP1 / STOP2
(their DIAG jumpers removed); the probe still through a BAT85 on an ordinary 3.3 V input (the board's optocoupled
SENSOR port needs a firmware polarity the model does not carry). Pi Zero 2 W on the Octopus's Raspberry Pi header (5 V,
UART2, /dev/ttyAMA0). Power budget: worst case 254 W of the 350 W supply (73 %, limit 85 %); board 5 V rail 0.74 A of
6.4 A allowed. Z run current 0.8 A per motor (rated 1.68); Y 1.2 A per motor (in v8.1 the two Y motors shared one
driver's 1.2 A).

Two checker gaps closed on the way: Klipper's `[stepper_z1]`-style sections need no endstop_pin or position_max and
`[z_tilt]` is a known section (the offline config check rejected both); and the firmware-in-the-loop now plans against
the board's own MCU (the Octopus's STM32F446: `tools/setup_klipper.sh` builds `out_stm32f446/`; the generated printer.cfg
names it). The print for the viewer ran on real Klipper with that dictionary.

### Frame: flush top front rail (owner review)

v8.1's top front rail sat 30 mm low so the gantry could pass over it at the front of Y travel (the probe is 34.5 mm
behind the nozzle, so Y travels 124.5 mm forward). Now all four top rails are flush. **The frame grew 13 mm in Y**, all at
the front: side rails 373 mm (v8.1 360), front rails and posts 13 mm further forward. At full -Y over-travel the
gantry's front-most parts below z 407 (the X mounts' M5 bolt heads on the beam's front face) reach y -169.5; the rail's
inner face is at -173.0 (3.5 mm clear). Two lugs were trimmed so they start 4 mm above the rail (X idler mount's lug, X
tension anchor's fin; the jack screw still bears 9 mm above the cut). A first try at 26 mm (lugs untrimmed) made the
machine 431 mm deep, over the brief's 420 mm envelope; 13 mm keeps it at 419 mm. Mass: about +30 g of extrusion. The
twin's resonances do not include the frame (open item 9 of v8.1), so the scorecard does not see the change; motion and
interference are clean at the travel extremes. The gantry's cable loom now drops from under the left Y plate to a clamp
behind the front rail.

### Front plate deleted (owner review)

v8.1's "front stiffener" was 12.7 mm 6061, 871 g (the model's mass), bolted to the front beam's front face: the code
said "stiff, and its weight seats the front nuts". It was mostly ballast. FEA with and without it, on gravity-seated
nuts (the same solver, the carrier and bed unchanged otherwise):

| | with (v8.2 first run) | without | without, nuts captive (v8.2 as built) | limit |
|---|---|---|---|---|
| Moving mass on Z | 5.15 kg | 4.28 kg | 4.40 kg (keepers 0.12 kg) | |
| 1 kg at the worst print corner, screw-only bound | 0.0043 mm | 0.0057 mm | 0.0063 mm | 0.02 |
| 20 N hand load, worst corner | 0.0089 mm | 0.0117 mm | 0.0129 mm | |
| Payload x3 on the bed, stiffness bonded / screwed | 36,146 / 18,724 N/mm | 24,850 / 15,841 | 25,165 / 16,051 | |
| Front nut plate under 3 x the bed's weight | 0.0147 mm | 0.0147 mm | 0.0138 mm | 0.05 |
| Bed growth at +60 K | 0.391 mm | 0.392 mm | 0.383 mm | |
| Nuts at two screws at opposite lead limits | all seated, least 2.9 N | front nuts lift (-1.0 N) | front nuts lift into their thread backlash; 1 kg then sags 0.0185 mm on the supports | |
| Carrier bounce, estimate sqrt(k_screwed / m) / 2 pi | 303 Hz | 306 Hz | 304 Hz | |

No modal case exists for the carrier; the last row is a hand estimate from the payload case's screw-only stiffness and
the moving mass, so it says only that removing mass and stiffness together left the bounce frequency where it was. The
plate was worth 0.0014 mm of bed sag (limit 0.02) and was what kept the front nuts seated. With the keepers the nuts
cannot lift off the carrier, so it is deleted: **0.87 kg off the moving mass**; net of the keepers, Z moving mass
5.106 -> 4.401 kg (-0.705 kg). The remaining free play is the brass nut's own thread backlash (0.1 mm assumed), which the
supplied anti-backlash nut would remove (open item 3).

### Bed posts and tie (owner review)

v8.1's posts were M5 threaded rods screwed into stainless thread inserts in tapped blind holes in the MIC-6 plate (the
inserts were BOM lines, invisible in the viewer). Now: an **ISO 10642 M5 x 16 countersunk screw** from the bed's top face,
in a 90 deg countersink (11.2 mm; head 0.9 mm below the surface, under the magnetic base), through the plate and a washer
into an **M5 x 15 coupling nut** (DIN 6334 type, A2; a stand-in: not in the catalogue); the threaded rod is screwed 9 mm
into the coupling nut's lower half. The two nuts at the tab still level the bed (4 mm range kept). The rod's free length,
the flexure for the hot plate, is 48.7 mm (v8.1 59): the carrier was not lowered. The tie: two M5 x 30 countersunk
screws through plate, spacers and tie into washers and nyloc nuts. No tapped holes or inserts remain in the bed plate.
Each post, coupling nut and screw carries a one-line description of the joint. The bed is a bench unit in the assembly
plan (screws in before the magnetic base goes on). New in the catalogue: `fhcs()` (ISO 10642, head figures recalled) and
`add_screw(..., head="countersunk")`; the washer / seat check does not judge countersunk heads (it says so).

### Attachments the viewer cannot show

One-line `meta["description"]` on: bed_heater (adhesive-backed silicone pad bonded to the plate's underside), bed_magnet
(adhesive-backed sheet on the plate's top), bed (PEI sheet held by the magnet, removable), bed_tco (bonded), bed_plate,
hotend (held by the Roto's own clamp), each Z motor and integral screw, each nut, nut plate and keeper, each post.

### Belts: a clearance rule, and its warnings fixed

New in `mechloop/verifiers/belts.py`: `belt_run_near_part` (BLT-060, a straight run within 3 mm of a part it slides
past: not the belt's own pulleys, not parts on the body its anchors ride on) and `pulley_near_plate` (BLT-061, a pulley
within 2 mm of a made part); limits `d.practice["limits"]["BLT-060.run_clearance_mm"]` and
`["BLT-061.pulley_plate_clearance_mm"]`; tests in tests/test_belt_clearance.py. On the first v8.2 run it raised ten
warnings on the Y belts: runs 2.25 to 2.70 mm from the Y motor, its mount and the idler mount, the idlers 1.00 mm from
their mounts and 1.55 mm from the Y plates at full travel. Fixed: two M5 washers between each Y idler and its mount (one
in v8.1), which moves the belt plane 1 mm outward (the motor pulley's hub still has 5.4 of its 6 mm on the shaft), and
the Y plates' front edge 0.5 mm back. Motion now reports none.

### Tolerance: the free-ended screw follows the nut

The stack-up gives the front screws up to 3.4 mm of misalignment with their nuts over the travel (screw 1.05 deg out of
parallel with the rails at the 99.7th percentile; v8.1 2.3 mm, 0.7 deg), more than the nut's 2.6 mm float. The check
called that binding. A free-ended integral screw is a cantilever from the motor's bearings: what the float does not take
it takes by bending. `mechloop/tolerance/__init__.py` now works that out for an integral screw with no bearing at its far
end: 0.78 mm beyond the float at 212 mm gives 3.5 N sideways and 0.7 N of drag against 691 N of drive, so no error. Like
the coupler rule beside it, this is a judgement in the checker; it is reported in the metrics
(`tolerance.lead_screws.*.bending_side_force_n_99`).

## Verify, per verifier

| Verifier | Errors | Warnings | What the warnings are |
|---|---|---|---|
| geometry | 0 | 0 | |
| interference | 0 | 0 | |
| tolerance | 0 | 4 | rear screw's nut float 99 % used (`adjustment_margin_thin`, 2.57 of 2.6 mm); extruder screw to probe 1.31 mm (0.73 % of builds), two part-fan screws to the top back rail 1.44 mm: as v8.1 |
| manufacture | 0 | 34 | hole-size, edge and web warnings on the nut plates (M3 keeper holes drawn 4.8 mm, the smallest SendCutSend cuts in 9.525), motor plates (M3 holes in 6.35 mm, 3.25 mm to the notch), Y plates and tool plates (as v8.1); sharp corners on the three keepers (the profile rounding did not take; to fix); six countersinks in the bed plate (second operation); no lead-in on the motors' pilots in their plate holes (laser-cut) |
| practice | 0 | 15 | FST-070 locking on 83 screws (v8.1 93), BLT-040 (12 mm Y belt on 12 mm pulleys), SHF-010 x 3 (pulley set screws), FST-101, FST-050, FST-081, LOC-006. SHF-011 / BRG-020 (608s on thread) and BLT-030 / 031 (Z idler) are gone with the towers and belt |
| ratings | 0 | 15 | `axial_load_rating_unknown` x 3 (14.7 N per motor, no rating), M3 PEM nuts on oversize holes, washers on printed parts (as v8.1), 9 stand-ins (magnetic base, four rods, four coupling nuts) |
| motion | 0 | 0 | (the new belt clearance rule finds nothing) |
| subsystems | 0 | 1 | bed mesh 12 mm edge strips (as v8.1) |
| electrical | 0 | 1 | `cutoff_depends_on_mcu` (as v8.1) |
| assemblability | 0 | 1 | `unsupported_step` (as v8.1) |
| fea | 0 | 1 | `z_nut_unseats`: at two screws at opposite lead limits a front nut unloads into its thread backlash (captive nuts: the bed stays held; 1 kg then sags 0.0185 mm) |
| printing | 0 | 0 | |
| requirements | 0 | 0 | all 22 pass |

## Numbers against v8.1

`score --assembly` on both (v8.1: out/printer_v8_1/scores.jsonl, 2026-11-16).

| | v8.1 | v8.2 | |
|---|---|---|---|
| Errors / warnings | 0 / 70 | 0 / 72 | v8.1's report predates the belt-clearance rule |
| Total mass | 13.74 kg | **12.98 kg** | -0.76 kg: towers, belt, pulleys, 608s and the front plate out; three motors, keepers in |
| Moving mass X / Y / Z | 0.359 / 1.238 / 5.106 kg | 0.359 / 1.236 / **4.401 kg** | Z -0.705 kg |
| BOM cost (estimate) | $823 | **$963** | +$139: three lead-screw motors $139, Octopus $55 and 7 driver modules $42 against the SKR, Z motor, belt, pulleys and bearings |
| Parts / fasteners | 583 / 180 | 584 / 187 | |
| Assembly time (estimate) | 135.9 min | 138.2 min | 241 placements held (242), 9 tool changes (12) |
| Resonance X / Y | 77.6 / 61.0 Hz | 77.4 / **69.0 Hz** | Y: each Y motor on its own driver at 1.2 A (v8.1: one driver for both); ranges 64.1 to 76.1 against 57.5 to 65.7 |
| Acceleration an owner would run | 6,500 (4,600 to 9,900) | **8,400 (5,800 to 13,500)** mm/s^2 | from the Y resonance |
| Step-loss ceiling | 12,000 | 24,000 mm/s^2 | Y motor current |
| Cross-track RMS / worst | 0.0119 / 0.108 mm | 0.0101 / 0.101 mm | |
| Frame stiffness at the nozzle, screwed X / Y | 1,443 / 1,917 N/mm | 1,450 / 1,921 N/mm | |
| Benchmark time | 2,571 s | 2,571 s | melt-rate bound |
| Z drive margin | | 8.2 (691 N available, three motors at 0.8 A) | requirement 3 |
| Z resolution | 0.01 mm per full step | 0.01 mm per full step | |
| Bed sag, 1 kg worst corner | 0.0048 mm | 0.0063 mm | limit 0.02 |
| Bed level change over the travel from lead error | 0.070 mm | 0.071 mm | now re-levelled at each print start by Z_TILT_ADJUST |

The Y figures moved because of the wiring, not the frame: within the twin's ranges a change of that size is real in
kind (more motor current, stiffer holding), but the step-loss ceiling is a ceiling, not an acceleration to run.

## Open items

1. **Thrust rating of the lead-screw motors.** About 15 N per motor, no rating stated; ask StepperOnline, and get the
   datasheet (nut drawing, rotor inertia, mass) before ordering three.
2. **Screw cut to 252 mm** by the builder (or a custom length); the 328 mm as-sold length above the face is assumed from
   the sister model.
3. **Thread backlash at the Z nuts** (0.1 mm assumed): the keepers hold the flanges, not the threads. Fit the supplied
   anti-backlash nuts once their drawing is in hand, or measure the backlash on the machine. The checker has no
   preloaded-nut kind (v8.1 checker note 5).
4. **Rear screw's nut float 99 % used** at the 99.7th percentile; the front screws exceed it and bend 0.7 to 0.8 mm
   (3.5 N). Align each motor plate to its nut at assembly (post bolts snug, run the carrier to the top, then tighten).
5. **Power-off:** the Tr8x2 screws are self-locking by calculation, not by test; `Z_TILT_ADJUST` after every power cycle.
6. **Octopus heater / fan limits** are typical values; the hotend (1.7 A) and part fan (0.07 A) are far below them.
7. **Coupling nuts** are stand-ins (no catalogue entry); countersunk head dimensions are recalled from ISO 10642.
8. **Keeper corners** are not rounded (profile rounding failed on them): round by hand in the next pass.
9. **Bed posts' free length** fell to 48.7 mm; their bending stress as the plate grows is still a hand estimate.
10. As v8.1: magnetic base thickness, ZF block stiffness assumption, print-sheet edge strips, part cooling not modelled,
    frame stiffness not in the twin.

## Files

- `designs/printer_v8_2.py`; `out/printer_v8_2/report.json`, `scores.jsonl`
- catalogue: `mechloop/parts/batch7.py` (motor, screw, Octopus), `fhcs()` in `mechloop/parts/__init__.py`
- checker changes: `mechloop/verifiers/belts.py` (BLT-060 / 061), `mechloop/electrical.py` (extra steppers, `[z_tilt]`,
  `klipper_mcu`), `mechloop/twin/firmware.py` (per-board dictionary), `mechloop/tolerance/__init__.py` (integral screw
  bends), `mechloop/verifiers/bearing.py` (countersunk heads not judged), `tools/export_viewer.py` (NUT-TR8 nuts visible)
- `docs/build/printer_v8_2/`, `viewer/`, `review/data.json` (generated); v8.1's viewer and review data kept in
  `viewer_v8_1/` and `review_v8_1/`
