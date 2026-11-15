# Reference machine: how often does the harness cry wolf on a printer that works?

Everything here is simulated. Nothing was built or measured by me. The machine exists and works; the model of it
is mine and is simplified (every simplification is listed).

`designs/ref_vminion.py` is a model of the **Rat Rig V-Minion**, a 180 x 180 x 180 mm kit printer sold since 2021,
run through all 12 verifiers and the twin. Two full runs (`verify --no-render`, 2026-11-15 14:10 and 14:18 UTC, same
`mechloop` source hash) gave identical findings: **30 errors, 20 warnings, 21 notes**.

**Headline.** Of the 30 errors raised on this known-good machine:

| Class | Errors | What |
|---|---|---|
| (a) checker's fault, firm | **15** | printed screw patterns "do not start" (9), power-supply screws "too short" (4), free-standing electronics box "floating / unfastened" (2). Three root causes |
| (a) checker's fault, probable | **1** | hotend overshoot from the simulated PID autotune |
| (b) my modelling | 1 | my own overall-size requirement |
| (c) catalogue part or data missing | 10 | MGN15 blocks stood in by MGN12 (8), 5 V probe stood in by a 24 V one (1), bed-screw travel not published (1) |
| (d) real property of the machine | 3 | no independent hotend cut-off, frame not bonded to earth, 5 A fuse at 115 V. Evidence for these is thin (see each) |

A separate test that the model could not make (its printed parts are simplified blocks): the manufacture verifier on
Rat Rig's 31 **real** printed parts gave **15 more errors** (13 "wall too thin to print", 2 crashes) and 8 "needs
support" warnings, on parts that are printed without support by design. Those are all the checker's.

A latent defect that raised no finding only because of how this model is declared: the tolerance verifier assumes the
bed rides the Z joint. On this machine it computes a nominal nozzle gap of 360.1 mm for a gap that is 0.1 mm.

## 1. Which machine, and why

Preferred was the Voron 0.2. It is CoreXY, and mechloop's motion model is a tree of one-motor joints
(`mechloop/geom.py`, `mechloop/twin/machine.py`; the generated config is `kinematics: cartesian`,
`mechloop/electrical.py`). The twin's calibration code treats CoreXY only as a documented special case outside the
design model. So a cartesian machine was needed. No kinematics were added.

The catalogue then decided between cartesian machines: its only linear guide is the MGN12 rail and MGN12H block, its
only extrusion is 2020, its motors are NEMA 17. Prusa MINI and MK3S run on rods and LM8UU bearings, the Ender 3 on
V-wheels (and the Ender 3 is one of the three machines the twin was calibrated on, so it would not be a blind test);
the Voron Switchwire is CoreXZ. The V-Minion is cartesian, has profile rails on all three axes, NEMA 17 motors, one
T8 lead screw, a 2020 X beam and an MGN12 X rail, and its published kit can be fitted with the catalogue's control
board. It is not among the twin's calibration machines (`calibration_machines.json`: Voron 0.2, Voron Trident 250,
Ender 3) and "minion" appears nowhere else in the repository: the twin comparison is blind.

It still needs substitutes: its frame is 3060 extrusion and its Y and Z rails are MGN15. Both are listed below.

## 2. Sources and licences

| Source | Used for | Licence | Retrieved |
|---|---|---|---|
| `https://github.com/Rat-Rig/V-Minion` @ 6811558 (2023-04-20): `docs/src/bom/vminion_20042023_1212.csv`, `docs/src/assets/dimensions_*.jpg`, `feature_linear_rails.png`, `docs/src/*.md`, `cad/printed_parts/machine/step/*.step` | BOM (cut lengths, rails, screws, belts, electronics), overall drawings, which rail is where, printed-part sizes, volumes and hole diameters | CC BY-NC-SA 4.0 (Rat Rig) | cloned to scratch |
| `https://github.com/Rat-OS/RatOS-configuration` @ 3a6a8b0 (2024-12-27): `printers/v-minion/*`, `z-probe/probe.cfg` | travel, endstop ends, speed limits, motor currents, probe offsets, bed-screw positions, mesh limits, Z position_min | no licence file found in the clone (not checked further); only numbers are quoted | cloned to scratch |
| `https://raw.githubusercontent.com/Klipper3d/klipper/master/config/printer-ratrig-v-minion-2021.cfg` | stock PID values of the kit hotend, limits | GPLv3 (Klipper) | fetched to scratch |
| EVA 2.4.2 (the toolhead Rat Rig ships), `https://github.com/EVA-3D/eva-main` | named only; not fetched | not checked | - |

Nothing downloaded is in the repository. No Rat Rig CAD file was copied or loaded by the design: the geometry in
`designs/ref_vminion.py` is re-drawn from dimensions (CC BY-NC-SA allows adaptation with attribution for
non-commercial use; this model is such an adaptation and carries the attribution in its docstring). The STEP files
were only measured (bounding boxes, volumes, cylinder radii) in scratch, with `python -I`, scripts kept in another
directory.

Not reachable from this session (blocked by the network policy, not worked around): `docs.ratrig.com` (the build
guide), `www.answeroverflow.com` (the community thread with input-shaper output). The Fusion 360 master CAD
(`a360.co` link in the README) was not tried. What that costs is in section 9.

## 3. What is modelled faithfully, simplified, substituted

**From published data (faithful):** the three frame members' cut lengths (3060 x 270, 115, 345) and arrangement;
2020 X beam 362 mm; one 250 mm rail and one block per axis; which face each rail is on; TR8x4 lead screw 250 mm with a
5-8 jaw coupler; NEMA 17 x 40 mm motors; 6 mm X belt and 9 mm Y belt on 20-tooth pulleys (the model's routed lengths
are 659 and 633 mm; the BOM cuts 650 and 700 mm); bed = 5 mm cast plate on three 12 mm spacers on a 4 mm sub plate, at
the three positions RatOS names; 160 x 160 mm 180 W pad with thermal fuse; steel flex plate; probe offsets
(-27.8, -12); X and Y home at firmware 0, Z homes on the probe; Z allowed 5 mm below zero; 200 mm/s, 3000 mm/s^2,
Z 15 mm/s; 0.8 A motor currents; 60 W hotend cartridge; 5 A mains fuse; no mains relay, no hotend cut-off, one earth
wire (inlet to supply); free-standing electronics box 260 x 162 x 90 mm with one 40 mm fan; M4 x 6 screws holding the
supply through a 4 mm panel; the Z motor's four slotted holes (7.3 mm slots, measured in `z_motor_cage.step`).

**Substituted (catalogue part for a part the catalogue lacks):**

| # | Real part | In the model | Effect |
|---|---|---|---|
| S1 | 3060 T-slot extrusion (3 pieces) | hand-made `Stock`: 30 x 60 box tube, 3 mm walls, web and two cores; I about 2.3e5 / 7.5e4 mm^4, 1.95 kg/m (both estimates) | 3 `uncatalogued_cots` warnings; frame stiffness is an estimate |
| S2 | PEI spring-steel flex plate | hand-made `Stock`, 0.8 mm steel; magnet sheet not drawn | 1 `uncatalogued_cots` warning |
| S3 | 8 mm 5 V inductive probe | OMRON E2E-X5ME1 (M12, 10-30 V, unshielded), at the real offsets | `probe_signal_over_voltage`; the toolhead had to make room for an M12 body |
| S4 | cast 3030 corner brackets (5) | catalogue 2020 bracket (17 mm wide) | joint stiffness; none of it enters a check |
| S5 | MGN15 rail + MGN15H block (Y, Z) | MGN12 rail + MGN12H block | bed 3 mm lower; 8 `thread_bottoms_out` (MGN15H threads are M3 x 4, MGN12H M3 x 3.5); block rigidity 63 instead of 87 N/um |
| S6 | M4 x 30 countersunk bed screws | M4 x 25 cap screws in counterbores | none |
| S7 | stainless 12 mm spacers | catalogue aluminium M4 spacer, 12 mm | none |
| S8 | Keenovo pad with cut-outs for the bed screws | plain catalogue pad, overlaps the spacers by declaration | none |
| S9 | TR8x4 anti-backlash nut block | catalogue brass flange nut in an aluminium block under the beam | how the real block meets the arm is not published |
| S10 | F8-16M thrust bearing in a pillow block | 608 bearing in the printed cap | none |
| S11 | MGN12C X block (34.7 mm, 30 g) | MGN12H (45.4 mm, 54 g) | toolhead 24 g heavy, tilt stiffness high |
| S13 | Dragonfly BMO hotend | E3D V6 | thermal class of the hotend (enters `heater_overshoot`) |
| S14 | Bondtech LGX Lite | catalogue generic direct-drive extruder, 0.24 kg | toolhead mass |
| S15 | 5015 blower | 30 mm axial fan | about 19 g light |
| S19 | Weho 350 W supply | Mean Well LRS-350-24 | mounting holes, thread depth |
| S20 | BTT SKRat 1.0 + 4 TMC2209 | BTT SKR Mini E3 V3 (the case also takes it, Rat Rig's docs) | board limits |
| S21 | Raspberry Pi 3/4 | Pi Zero 2 W | none |

**Simplified:**

- S12. The EVA toolhead (eight printed parts, about 97 cm^3 of plastic) is ONE printed part: a slab on the X block,
  a rear wall with the belt clamp, a front web, cheeks, the probe tab and the X switch's ear. Its shape is mine. The
  nozzle stiffness the FEA reports is governed by this part (see section 7).
- Printed motor cages, idler blocks, caps are plates and blocks with the right interfaces, not the real shapes.
  The model is 412 mm wide; the real machine is 372 mm (the X end blocks are 20 mm slabs with proud bolt heads).
- S16, S18. Fans and the case's own screws, locknuts and standoffs are declared joins and BOM lines. The model has
  104 drawn fasteners; the real kit has well over 250.
- S17. Polycarbonate panels are drawn in PETG (no polycarbonate in the materials table).
- Not drawn: feet, spool holder (3030 x 120), belt tensioners (declared as adjustments), end caps, wire guides, the
  magnet sheet, T-nuts.
- Endstops: where the real switches sit is not published. Both are placed by the catalogue switch's own figures, so
  **the endstop checks are not an independent test here**.
- Loom routes and lengths are mine.
- Guessed from the drawings (plus or minus several mm): Y motor height, lead-screw position behind the arm, X belt
  plane behind the beam, nozzle 31.5 mm below and 32 mm in front of the beam centre.
- Z convention. The harness expects the HIGH end of the Z joint's range to be where nozzle and bed meet. On this
  machine the nozzle moves, so the joint runs downward and the home pose is the arm at the TOP of its travel.

## 4. Result by verifier (both full runs identical)

| Verifier | Result | Errors | Warnings |
|---|---|---|---|
| geometry | pass | 0 | 0 |
| interference | FAIL | 14 | 0 |
| tolerance | FAIL | 10 | 1 |
| manufacture | pass | 0 | 9 |
| ratings | pass | 0 | 4 |
| motion | pass | 0 | 0 |
| subsystems | pass | 0 | 1 |
| electrical | FAIL | 5 | 3 |
| assemblability | pass | 0 | 1 |
| fea | pass | 0 | 0 |
| printing | pass | 0 | 1 |
| requirements | FAIL | 1 | 0 |

Reports: `out/ref_vminion/report.json` (second run), copies of both runs in `out/ref_vminion/evidence/`.

## 5. Every error, classified

### (a) Checker's fault

**A1. `screws_may_not_align`, tolerance, 9 errors (and 1 warning).** "The 4 screws through z_motor_cage into
z_motor all start in only 30 % of builds (printed holes with 0.25 mm radial clearance)". Same for the Y and X motor
mounts and the carriage on its guide block (30 to 31 %), and five smaller patterns (44 to 77 %).

- Real practice: Rat Rig's published `x_motor_cage.step`, `y_motor_cage.step` and `z_motor_cage.step` each have four
  holes of radius 1.65 mm (3.3 mm) on the motor's 31.0 mm square; `top_mgn12.step` has 3.3 mm holes for the guide
  block. That is tighter than the model's 3.4 mm. Thousands of these kits were assembled with those parts.
- Reproduction (`out/ref_vminion/evidence/repro_false_alarms.py`, case A1): a 6 mm printed plate with four holes on
  a catalogue NEMA 17. With 3.4 mm holes the verifier says 30 %; with Rat Rig's 3.3 mm it says **9 %**.
- At fault: `mechloop/tolerance/fits.py` (the screw-pattern loop that ends in `screws_may_not_align`) with
  `mechloop/tolerance/process.py`, `PROCESS["printed"]`: position sigma 0.12 mm per hole, holes 0.15 mm small, and a
  rigid pass/fail (a screw "starts" only with geometric clearance). Printed parts yield, screws cut their way in, and
  0.12 mm between holes 31 mm apart is pessimistic for one print. Four of the nine patterns are one-to-one real
  patterns; the other five are patterns I drew, failing by the same mechanism.

**A2. `thread_engagement`, interference, 4 errors.** "psu_screw_0 engages only 2.0 mm of thread in psu (steel); an
M4 needs >= 2.7 mm there."

- Real practice: the BOM's electronics-case bundle has "Cap Head Screw M4 (Length: 6mm) x 4" and 4 mm panels.
  Mean Well's drawing (in `mechloop/parts/vendor/meanwell_lrs.json`) says "4-M4 L=3mm": at most 3 mm of screw inside.
- The check turns that maximum into a requirement: `need = min(need, depth - 0.3)`
  (`mechloop/verifiers/interference.py`, about line 194). The allowed window is then 2.7 to 3.0 mm. Through a 4 mm
  panel no standard screw length lands in it.
- Reproduction (case A2): LRS-350 on a 4 mm panel. M4 x 6 gives `thread_engagement`; M4 x 8 gives
  `thread_bottoms_out`. Nothing between exists.

**A3. `floating_parts` and `unfastened`, interference, 2 errors.** The electronics box "does not touch the rest of
the body". It is a free-standing unit on the same bench, joined to the machine only by cables (Rat Rig's case
drawing). A design cannot say so. Reproduction (case A3): two blocks 200 mm apart.
At fault: the connectivity check in `mechloop/verifiers/interference.py` (one connected set per body). I count this
as the checker's because the real machine is built this way; one may equally call it a missing feature.

**A4 (probable). `heater_overshoot`, electrical, 1 error.** "Heater 'extruder' overshoots 250 degC by 15.1 K
(limit 10) with simulated PID_CALIBRATE."

- The simulated autotune returns Kp 21.7, Ki 1.88, Kd 62.8. Klipper's stock config for this kit's hotend has
  Kp 22.2, Ki 1.08, Kd 114. With those values on the same thermal model the overshoot is 7.3 K and the finding
  goes (`out/ref_vminion/evidence/probe_heater.py`).
- So the error is made by the tune the harness computes, not by the machine. Whether the tune or the plant is off
  I cannot tell: the plant is the catalogue's V6 class with a 60 W cartridge, not the Dragonfly (substitution S13).
  At fault: `E.autotune_pid` in `mechloop/electrical.py`, used at `mechloop/verifiers/electrical.py` about line 826.

### (b) My modelling

**B1. `requirement_failed`, 1 error.** My own check "published overall size 372 x 375.2 x 366.5": the model is
412 x 360 x 383 mm at home. X is 40 mm over because of my slab end blocks; Z is compared at a different pose (the
published drawing has the arm at mid height, the model's home is the top). The requirement was badly posed; left in
so the count is honest.

### (c) Missing catalogue part or missing data

**C1. `thread_bottoms_out`, interference, 8 errors.** M3 x 8 through the 4 mm sub plate and x_plate goes 4.0 mm into
the stand-in MGN12H blocks (3.5 mm threads). The real MGN15H block's threads are "M3 x 4" (Hiwin table 3.79, in
`hiwin_mgn12.json`), and the BOM lists 36 M3 x 8. The check is right about MGN12H; the catalogue has no MGN15.

**C2. `probe_signal_over_voltage`, electrical, 1 error.** The stand-in sensor pulls its output to 24 V. The real
probe is a 5 V part.

**C3. `adjustment_too_small`, tolerance, 1 error.** "The bed is up to 2.72 mm out of level under the nozzle as
built, but the three M4 bed screws only adjust +/-1.0 mm." The 1.0 mm is my guess: RatOS's `screws_tilt_adjust`
shows the three screws are the tramming adjustment, their travel is not published. I cannot say whether 2.7 mm
(1.1 degree between bed and arm, 99th percentile) is realistic for a single-rail cantilever; the process table calls
its own figures "deliberately a little pessimistic". Unresolved, not counted against the checker.

### (d) Real properties of the machine

**D1. `no_independent_cutoff`, electrical.** "With its MOSFET failed shorted ... the hotend settles at 613 degC."
True of the stock kit (BOM: cartridge, thermistor, no fuse or relay; the bed pad does have a fuse) and of nearly
every hobby printer. It is a known class of hazard and an accepted one. The harness is stricter than practice. I
did not fetch a citation.

**D2. `frame_not_earthed`, electrical.** The BOM has one 200 mm earth wire, inlet to supply. The mains parts are in
a separate plastic box and the frame carries only the supply's isolated 24 V, which is why kits get away with it;
other projects (Voron) require the bond. Debatable between (d) and (a): the check has no notion of a separate
insulated enclosure. Whether the build guide adds a frame bond I could not read (host blocked).

**D3. `mains_fuse_too_small`, electrical.** "Mains fuse 5 A; the supply draws 4.93 A at 115 V, so the fuse must be
at least 6.16 A." The 5 A fuse is the BOM's. At 230 V the draw is 2.47 A and the rule is met. At 115 V with bed and
hotend both full on (254 W DC, a supply without power-factor correction) the estimate is plausible and the margin
is thin; the fuse is not "too small" to work, it is below the harness's 125 % rule. I found no report of blown
fuses and did not search hard. Not counted against the checker.

## 6. Every warning, classified

| Verifier | Warning | n | Class | Note |
|---|---|---|---|---|
| tolerance | `screws_may_not_align` (sub plate into belt mount, 92 %) | 1 | (a) | same mechanism as A1 |
| manufacture | `hole_smaller_than_thickness` (3.4 mm holes in 4 mm sheet) | 3 | (a), mild | the real plates are 4 mm with M3 holes; the text ("they cut, but taper") is fair as advice |
| manufacture | `thin_wall_around_thread`, `hole_too_close_to_edge`, `non_stock_thickness`, `needs_support`, `long_bridge` | 6 | (b) | features of my simplified parts |
| ratings | `uncatalogued_cots` | 4 | (c) | S1, S2 |
| subsystems | `bed_mesh_does_not_cover_print_area` | 1 | (d), true | harness: strips of 10 / 27.8 / 10 / 12 mm unprobed. RatOS's own mesh (15,15 to 150,160) leaves 15 / 30 / 15 / 20 mm |
| electrical | `flex_span_crosses_part` | 3 | (b) | my loom routes |
| assemblability | `unsupported_step` | 1 | (b) | the planner's order for my simplified parts |
| printing | `corner_bulge` 0.45 mm | 1 | (d), generic | the test print runs without pressure advance; owners run with it |

## 7. The manufacture verifier on the real printed parts (supplementary)

The model's printed parts are blocks, so the printed-part rules were barely exercised. In scratch, Rat Rig's 31
single-solid printed-part STEP files were given to the manufacture verifier as printed PETG
(`out/ref_vminion/evidence/real_printed_parts.py`; the files are read from the scratch clone and are not in the
repository). Rat Rig's print settings for them: 4 perimeters, 25 % infill, **supports: none**.

| Finding | n | Parts |
|---|---|---|
| error `wall_too_thin_to_print` | 13 | LJ8_probe_mount_8mm (0.12 mm), back_cartesian (0.30 mm over 778 mm^2), bed_wire_guide_end, bed_wire_guide_start, bmo_face, bmo_support, cartesian_cable_fin, top_mgn12, universal_face, x_motor_cage, y_belt_mount, y_belt_tensioner, z_motor_cage_plug |
| error `part_not_checked` | 2 | TriHorn Duct, ratrig_eva_shroud: `AttributeError: 'NoneType' object has no attribute 'NbNodes'` |
| warning `needs_support` | 8 | bmo_face, side_legs, top_mgn12, x_wire_holder, y_idler, y_motor_cage, z_cap, z_motor_cage |

All 15 errors are on parts that print and work, so all are the checker's (`mechloop/verifiers/dfm_print.py`,
the `wall_too_thin_to_print` branch; the crash is somewhere in its meshing). I did not identify which feature each
thin "wall" is. The large one in back_cartesian is consistent with a built-in sacrificial bridge layer, a standard
trick in these parts, but I did not confirm it. A 30 degree wedge on a block does not trigger the finding, so plain
sharp edges are not the cause. I have no smaller reproduction than the real files.

## 8. Defects seen that raised no finding in the final run

1. **Tolerance verifier assumes the bed rides Z.** `mechloop/tolerance/__init__.py`, printer section:
   `bz = B.at(bed, ...) + z_travel * dz` and `nominal = pn[2] - (top + z_travel * zdir[2])`. On this machine it
   reports `nominal_gap_mm: 360.1`, `p_first_layer_reachable_as_built: 0.0`,
   `p_bed_reaches_nozzle_with_overtravel: 0.0`. No finding only because a `z_offset` adjustment is declared. With
   it removed (`evidence/probe_gap.py`): "The nozzle-to-bed gap is drawn at 360.10 mm ... only 0 % of machines
   could print their first layer." The gap-error and level figures are relative and probably still meaningful.
2. **Z sign convention is not stated for a moving-nozzle Z.** My first model had Z rising from the bed. The
   generated config got `position_min: -184.9, position_max: 0.1` and the only message was
   `klipper_rejects_config`. AGENT.md states the convention for a bed that rises. Consequence of following it here:
   the home pose is the top of travel, and every home-pose check (envelope, FEA stiffness for the twin, assembly)
   is made there.
3. **The electrical verifier's firmware tuning depends on the previous run's `report.json`.** First full run of
   the new design: input shaper X 52.8 Hz / Y 48.6 Hz ("frame stiffness from: none"). Second run: 39.6 / 23.6 Hz
   ("from out/ref_vminion/report.json"). Findings were the same; these metrics were not.
4. **mechloop changed during the work** (another agent). Seen once: the probe's edge margin in
   `bed_mesh_does_not_cover_print_area` went from 17 to 12 mm between two of my partial runs. Both full runs were
   made on one source hash (113e6fde1878, files under `mechloop/`). `mechloop/tolerance/` changed again after them
   (hash b4dc12381d56 at 14:34 UTC); a tolerance-only re-run then gave the same 10 errors and 1 warning. The other
   verifiers were not re-run on the newer source.

Findings the harness raised on earlier versions of the model that were real mistakes of mine, and are fixed (they
show the checks working): Y belt running through the link; sub plate and heater hitting the Y motor at the end of
travel; a bed screw grazing the link; nut-block screws meeting the coupler; plate screw heads under the beam; a
toolhead ear 0.5 mm into the column at over-travel; two cables too short; bed heater leads overloaded when bundled
with every other wire (the real machine sleeves them separately); `leadscrew_binding` until the Z motor's real
slots were declared as the alignment adjustment; 42 assembly errors until bench sub-assemblies were declared.

## 9. Twin against published figures (blind)

The V-Minion is not in the twin's calibration or fitting data. Published measurements of it are scarce; I found one
unconfirmed resonance figure and no masses or print times.

| Quantity | Twin | Published | Difference | Weight of the evidence |
|---|---|---|---|---|
| X resonance | 39.5 Hz (37.4 to 42.4) with my FEA stiffness; 52.5 Hz belts only | one community thread: fitted MZV 36.2 Hz, second run ZV 45.6 Hz | +9 % / +45 % against 36.2; -13 % / +15 % against 45.6 | very thin: seen only as search-result snippets, the page is blocked; the machine is presumed, not confirmed, to be a V-Minion; a fitted shaper frequency is not the resonance peak |
| Y resonance | 23.5 Hz with my FEA stiffness; 48.4 Hz belts only | none found | - | - |
| Acceleration owners run | 800 mm/s^2 (600 to 1000) | RatOS stock limit 3000; "performance" preset 15000 (travel 8000) at 1.19 A | -73 % against 3000 | the published figures are firmware limits everyone runs, not measurements |
| Same, belts only (first-run shaper rule 6900, x 0.5) | about 3450 | 3000 | +15 % | my arithmetic, not a twin output |
| Step-loss ceiling | 10500 mm/s^2 (9000 to 12000) at 0.8 A | performance preset 15000 at 1.19 A; Klipper stock config limit 20000 | not comparable (different current; limits, not tests) | - |
| Moving mass X / Y | 0.516 / 1.021 kg | none found | - | - |
| Total mass | 7.43 kg (no feet, spool holder, wiring) | not fetched | - | - |
| Print time of a standard part | benchmark 2611 s (three parts) | none found | - | - |
| Belt lengths (a model check, not the twin) | X 659 mm, Y 633 mm | BOM 650, 700 mm | +1.4 %, -9.6 % | BOM lengths are cut lengths with allowance |

The FEA-coupled numbers are not a fair test of the twin. Nozzle stiffness (X 72, Y 29 N/mm) is governed by my
one-piece stand-in for the toolhead and the V6's neck, not by the frame: a variant with the arm 20 mm above the bed
instead of 180 mm gave almost the same (74 and 31 N/mm). The 800 mm/s^2 follows from that 23.5 Hz. With belts and
block tilt only, the twin's figures (52.5 / 48.4 Hz, about 3450 mm/s^2) sit near what the machine is known to run.
Neither is a confirmed error figure. A real comparison needs a readable input-shaper log and the real toolhead.

`score --firmware klipper --firmware-only` works on this design: real Klipper (commit 29d4ec2) loads the generated
`printer.cfg` and plans the prints. With input shaper and pressure advance on, the test cube stays clean up to the
highest acceleration tried (36000 mm/s^2; the harness itself calls that a ceiling, not a setting); with both off the
first failure is at 12000 mm/s^2 (lost steps on Y). Corner bulge 0.30 mm with pressure advance, 0.45 mm without.
"Acceleration owners would run" is 800 mm/s^2 there too, from the same 23.5 Hz.

**Assembly.** `score --assembly` and `assemble`: complete, 160 steps, 197 parts, 104 screws, **40.8 minutes**. I
found no published build time for the V-Minion. A reseller's figure for Rat Rig's larger kits, seen in a search-result snippet only, is 25 to 30
hours for an experienced builder. The model has under half the real fasteners and no wiring, belts, T-nut loading, squaring
or firmware, so 41 minutes is not an estimate of the real build; the two cannot be compared in percent.

## 10. Checks this machine could not exercise

Their false-alarm rate is still unknown.

- Paired-rail parallelism (`rails_not_parallel`): one rail per axis.
- Motor shaft radial load: judged only for the 48 mm motor; this machine has 40 mm motors.
- Two motors on one driver, dual lead screws, sensorless homing, Bowden, PTC heater, mains relay, MOSFET module,
  5 V fan regulator.
- Sheet-metal bends and DXF rules; machining rules beyond two trivial parts.
- Printed-part rules on real shapes inside the design (done separately, section 7).
- Modal cases; load cases beyond one trivial block; thermal case limits (reported, none set).
- Endstop placement (not independent: placed by the catalogue's figures). Probe switching distance on aluminium
  (the target here is the steel sheet). Probe metal-free zone was exercised and passed after I turned the heater
  block away from the probe.
- Bed levelling on springs or columns; cast-plate flatness as a finding.
- Driver access to rail screws under a parked block: no finding in the end.
- CoreXY, CoreXZ: not supported.

## 11. Unverified

- Everything read off the dimension drawings by pixel measurement (several mm).
- 3060 section properties and mass; flex plate thickness; cast plate outline (drawn 184 x 184).
- Where the lead-screw nut block, the endstops, the Y belt and the X belt really sit. The build guide was blocked.
- Bed-screw travel (1.0 mm assumed); probe face height (2 mm assumed); belt tensioner range (5 mm assumed).
- That the kit has no frame earth bond (inferred from the BOM alone).
- That the thin walls in the real printed parts are sacrificial layers.
- The community resonance figure and which machine it is from.
- RatOS's licence. EVA's licence (not used).
- Toolhead mass: the model's 0.516 kg is catalogue stand-ins plus my printed part; no published weight found.
- I did not run the test suite and did not edit anything under `mechloop/` or `tests/`.

## Files

- `designs/ref_vminion.py`: the model.
- `out/ref_vminion/`: reports, generated `electrical/printer.cfg`, `scores.jsonl`.
- `out/ref_vminion/evidence/`: both full-run outputs, the real-parts manufacture output, reproductions
  (`repro_false_alarms.py`, `probe_heater.py`, `probe_gap.py`, `real_printed_parts.py`), the low-pose variant.
  `out/` is git-ignored; the scratch clone the real-parts script reads from is not durable.
