# Twin calibration study: how far can the digital twin's predictions be believed?

2026-11-15. Code: `mech-ai/mechloop/twin/calibration.py`. Data and scripts: `research_notes/calibration/`.

## Answer in brief

- The twin's axis model was given three real printers from design data only and asked for their resonances
  before the measured values were looked up. Over six axes the mean error is 26 %.
- The error splits cleanly in two. Axes that move a gantry or a bed are right to within 15 % (mean 8 %, no bias).
  Axes that move only the toolhead read 18 %, 42 % and 70 % too high.
- The cause is one missing spring: the twin has nothing between the belt and the nozzle (carriage tilt, printed
  mounts, a wheeled carriage) unless the design's own FEA case supplies it, and a bonded FEA case does not.
- The belt stiffness default (22 kN per 6 mm of width) survives the blind test. The three gantry and bed axes imply
  15, 21 and 27 kN. Keep 22, carry a range of 15 to 27.
- The scorecard's `max_clean_accel_mm_s2` is a step-loss ceiling. On the three machines it sits 6 to 8 times above
  the acceleration their owners run. It should not be read as a usable print acceleration.
- For `printer_v5`: X resonance 88.6 Hz becomes 61 to 75 Hz (expected 68). Y stays at 57 to 65 Hz (scored 62.2).
  Max clean acceleration 10,000 becomes 8,000 to 12,000 mm/s², and the acceleration an owner would actually run
  with input shaping is about 4,600 to 9,600 mm/s². The design's own 4,000 mm/s² limit is inside what is believable.
- Nothing in the twin's defaults was changed. The proposals below are for the owner to accept or not.

## Method

1. **Machines.** Voron 0.2r1 (120 mm CoreXY), Voron Trident 250 (CoreXY), Creality Ender 3 (bed slinger on
   V-wheels). These are the three for which the trade study already had masses and belt lengths measured from
   the makers' CAD. Prusa MK3/MK4 and RatRig V-Core 3 have no assembly CAD in that data and were not used.
2. **Inputs (pass 1).** Moving masses and belt lengths from the CAD measurements; pulley size, voltage and run
   current from the stock firmware configs; motor resistance, inductance and torque from the community motor
   database. Each uncertain input carries a low / nominal / high triple. Frozen in
   `mechloop/twin/calibration_machines.json` (a test pins its hash).
3. **Prediction.** The twin's own axis formula: load mass on the motors' magnetic spring in series with the belts
   (4 EA / L per belt), belt EA at the twin's default, no frame term (there is no FEA of these machines).
   Recorded in `research_notes/calibration/blind_predictions.json` at 00:34 UTC with hashes (`FREEZE.md`).
4. **Measurements (pass 2).** Input-shaper frequencies that owners saved in public Klipper configs on GitHub:
   998 search hits, 910 files read as data, classified by kinematics, travel and names, one entry per distinct
   frequency pair. 91 Voron 0, 11 Trident 250 and 42 Ender 3 configs; about half were written by Klipper's
   accelerometer calibration itself. Every entry and URL is in `measured_configs.json`.
5. **Comparison**, then proposals. `python -m mechloop.twin.calibration compare` reproduces the tables.

### How blind was it

- No measured resonance or tuned acceleration of the three machines was searched for, opened or recorded before
  the freeze. The inputs were not touched after it.
- Not fully independent: `reference.py` had been read, and it contains the measured range of a Voron 2.4 350
  (X 54 to 62 Hz, Y 38 to 50 Hz). The twin's belt stiffness was tuned to that machine, and the Trident shares its
  gantry design. So the Trident is out of sample but in the same family. The Voron 0 and the Ender 3 are unrelated
  to the tuning.
- The model doing the work knows roughly what printers ring at from general training. No number was looked up
  and no input was adjusted after seeing an output; each prediction is the frozen inputs put through the formula.
- One code change happened between the first and second prediction run (one minute apart, before any
  measurement): the step-loss search was capped, because it had returned 2,000,000 mm/s² for one axis. The
  resonance predictions did not change.
- The stock `max_accel` values (2000, 3000, 3000) were seen before the freeze. They are firmware defaults.

## Results

### Resonance per axis

| Machine | Axis (what it moves) | Predicted Hz (5-95 % band) | Measured median Hz (middle half), configs | Error |
|---|---|---|---|---|
| Voron 0.2 | X (toolhead) | 112.6 (101-117) | 79.2 (74.0-88.6), 91 | **+42 %** |
| Voron 0.2 | Y (gantry) | 85.2 (77-89) | 73.8 (62.8-92.2), 91 | +15 % |
| Trident 250 | X (toolhead) | 76.2 (71-80) | 64.6 (62.5-74.0), 11 | **+18 %** |
| Trident 250 | Y (gantry) | 44.5 (41-47) | 48.6 (44.2-50.8), 11 | -8 % |
| Ender 3 | X (toolhead) | 85.8 (78-89) | 50.6 (41.0-68.2), 42 | **+70 %** |
| Ender 3 | Y (bed) | 45.6 (39-46) | 45.0 (38.5-54.8), 42 | +1 % |

- All six: mean absolute error 26 %, mean signed error +23 %.
- Gantry and bed axes: mean absolute 8 %, signed +3 %. All three predictions fall inside the middle half of the
  owners' values.
- Toolhead axes: mean +43 %. None falls inside the middle half.
- The accelerometer-only subset gives the same medians within 1.5 Hz on five axes (Ender 3 Y: 50.6 against 45.0).
- The spread between owners of the same machine (the middle half spans roughly ±10 to ±25 %) is as large as the
  twin's error on the good axes. A prediction cannot be tested more finely than that with this kind of data.

Secondary check, not frozen in advance: the Trident 300 and 350, obtained by lengthening the 250's belts by
200 mm per size and adding 0.06 kg to Y. Same pattern.

| Machine | Axis | Predicted Hz | Measured median Hz, configs | Error |
|---|---|---|---|---|
| Trident 300 | X | 72.6 | 58.8, 55 | +24 % |
| Trident 300 | Y | 41.3 | 43.6, 55 | -5 % |
| Trident 350 | X | 69.4 | 60.4, 8 | +15 % |
| Trident 350 | Y | 38.6 | 44.7, 8 | -14 % |

### Acceleration

| Machine | Stock config | Owners run (median, middle half) | Twin: shaper rule at predicted resonance | Twin: step-loss limit | Step-loss / owners |
|---|---|---|---|---|---|
| Voron 0.2 | 2,000 | 10,000 (6,000-15,000) | 26,300 | 84,900 | 8.5x |
| Trident 250 | 3,000 | 5,000 (4,850-7,650) | 6,600 | 32,900 | 6.6x |
| Ender 3 | 3,000 | 3,000 (3,000-4,000) | 7,000 | 18,900 | 6.3x |

- "Owners run" is `max_accel` in configs that have input shaping set up. It is a choice, not a measured limit. The
  Ender 3 figure equals the example config's default and says little.
- "Shaper rule" is the acceleration at which an MZV shaper tuned to the lower resonance rounds corners by 0.12 mm,
  the rule Klipper's calibration prints. Re-implemented from the published formulas; it reads 0 to 8 % above the
  documentation's example.
- The step-loss limit is what the scorecard's `max_clean_accel_mm_s2` runs into on every design scored so far. It
  is 6 to 8 times what people run. No controlled step-loss measurement was found, so the limit itself is untested.
- Owners run 0.44, 0.51 and 0.62 of the shaper rule evaluated at their own measured resonance. That ratio is the
  most transferable acceleration figure this study produced.
- Without input shaping, the only data are the stock firmware values above. The twin has no prediction to
  compare with them.

### Damping

Owners who measured it entered ringing damping ratios of 0.03 to 0.09 (median 0.05 on the Voron 0, 0.06 to 0.07 on
the Trident; 39 values). The twin's two assumed dampers combine to 0.02 to 0.05 on these axes. Same order, the
twin slightly under-damped. Damping does not move the resonance; it sets how long ringing lasts.

## What the twin gets right and wrong, and why

Right:
- Axes where the belts are the soft element. Mass from CAD, belt length from CAD and 22 kN per 6 mm give the
  resonance to about ±15 %, on a 120 mm CoreXY, a 250 mm CoreXY and a bed slinger.
- The trend with machine size (Trident 250 to 350).
- The order of magnitude of damping.

Wrong:
- Toolhead axes. The measured stiffness at the toolhead is 61 N/mm (Voron 0), 65 N/mm (Trident) and 27 N/mm
  (Ender 3); the model has 124, 90 and 77. The same belts and motors give the right answer on the other axis of
  the same machine, so the belts are not the cause. Nor is mass: the toolhead would have to weigh two to three
  times its CAD mass.
- What is missing is a spring of about 120 N/mm (Voron 0), 230 N/mm (Trident) and 40 N/mm (Ender 3) between
  belt and nozzle. That is the size expected from one small guide block tilting under a nozzle that hangs 50 mm
  below it, and from wheels on an extrusion. Supporting evidence: Ender 3 machines with the S1 gantry and a heavier
  direct-drive head ring higher in X (70 Hz), not lower, so structure and not mass sets that frequency.
- The acceleration headline. The twin answers "when do the motors lose steps"; owners stop far earlier, at the
  point where ringing and shaper smoothing spoil the part.

Sensitivity of the predicted resonance (percent change per percent of input, nominal point):

| Input | Voron 0 | Trident 250 | Ender 3 | Range of the input | Effect on prediction |
|---|---|---|---|---|---|
| Moving mass | -0.50 | -0.50 | -0.50 | -10 % / +25 % (CAD omits wiring, belts; +50 % on the Ender bed) | -11 % / +5 % |
| Belt stiffness per mm of width | +0.35 | +0.42 | +0.36 | ±30 % | ±11 to 12 % |
| Belt length | -0.35 | -0.42 | -0.37 | ±9 % | ±4 % |
| Motor current (magnetic spring) | +0.15 | +0.08 | +0.14 | -28 % / +23 % (up to +50 % on the Trident) | -5 % / +3 % |
| Belt-to-nozzle compliance | absent | absent | absent | 40 to 230 N/mm needed | -15 to -41 % on toolhead axes |
| Damping | 0 | 0 | 0 | 0.03 to 0.09 | none on frequency |

The largest error by far comes from the term the model does not have. Among the terms it has, mass and belt
stiffness matter equally and cannot be told apart by a resonance measurement: a 20 % mass error looks like a
20 % belt error.

## Proposed parameters (not applied)

Recorded as `calibration.PROPOSED`. The twin's defaults are unchanged.

| Parameter | Now | Proposed | Basis |
|---|---|---|---|
| Belt EA per 6 mm of width | 22 kN, "±30 %" assumed | keep 22 kN; range 15 to 27 kN (2.5 to 4.5 kN per mm of width) | implied by the three gantry and bed axes: 15.0, 21.3, 27.2 kN |
| Belt-to-nozzle stiffness, toolhead on one linear-rail block | none | 170 N/mm, range 120 to 230, in series on that axis | Voron 0: 121, Trident 250: 230 |
| Same, toolhead on V-wheels | none | 40 N/mm, range 30 to 60 | Ender 3: 41 (one machine) |
| Ringing damping ratio | about 0.02 to 0.05 (from two assumed dampers) | 0.05, range 0.03 to 0.09 | 39 owner-entered values |
| Usable acceleration with input shaping | not reported | 0.5 (0.4 to 0.65) x the shaper rule at the lower resonance | owners' settings on the three machines |

With the proposed nominal values the six axes fit to a mean of 6 % (worst +14 %). That is a fit to the same data,
not a test. Leaving one machine out and predicting it from the other two gives -16 % to +19 % on gantry axes and
-11 % / +15 % on the two rail toolhead axes. That is the honest size of the uncertainty: about ±15 to 20 % on
resonance, so ±30 to 40 % on anything that goes with its square, such as shaper-limited acceleration.

Caveats on the proposal:
- All three machines have 6 mm belts. `printer_v5` has 12 mm belts. Stiffness proportional to width is assumed.
- The belt range absorbs the CAD mass bias. Do not add a separate mass correction on top.
- The belt-to-nozzle term is fitted, not derived. The better fix is to compute it per design (see "Changes
  needed elsewhere").

## printer_v5 with the uncertainty

The twin was re-run on the committed `printer_v5` at the low, expected and high ends of the proposed ranges
(`evals.score_uncertainty`, 30 short prints; output in `research_notes/calibration/printer_v5_score_uncertainty.json`).

| Score | Scored (point) | Low | Expected | High |
|---|---|---|---|---|
| X resonance, Hz | 88.6 | 60.8 | 68.4 | 74.7 |
| Y resonance, Hz | 62.2 | 57.2 | 61.6 | 64.5 |
| Max clean acceleration (step-loss ceiling), mm/s² | 10,000 | 8,000 | 10,000 | 12,000 |
| Cross-track RMS, mm | 0.011 | 0.020 | 0.016 | 0.013 |
| Cross-track worst, mm | 0.113 | 0.153 | 0.122 | 0.113 |
| Shaper-rule acceleration, mm/s² | not scored | 11,400 | 13,300 | 14,700 |
| Acceleration an owner would run, mm/s² | not scored | 4,600 | 6,600 | 9,600 |

- X drops because v5's toolhead rides on one MGN12H block and its FEA stiffness case (1,773 N/mm) meshes the rail
  and the block as solids joined to each other, with no rolling-element tilt. If the real figure is near the 120 to 230 N/mm seen on the Vorons, X is no longer the stiff axis the
  scorecard shows; X and Y come out close, as they do on a Voron 0.
- Y barely moves: its belts are wide and the motors' magnetic spring carries much of the compliance.
- The X figures `STATUS.md` reports for v4 and v5 (68.5 and 88.6 Hz) are both optimistic for the same reason. v4 was
  not re-run here; the gain between them should be re-scored once the missing term is in. The cross-track
  improvement (0.015 to 0.011 mm) is smaller than the uncertainty on either figure.
- The acceleration steps are 2,000 mm/s² wide and scores near the step-loss edge are noisy, so the 8,000 to
  12,000 range is a minimum width.

## Scorecard

`mechloop score` itself is in `score.py`, which is not mine to edit. What exists now, inside the files I own:

- `evals.score_uncertainty(printer_path, out, score)` takes the dict `mechloop score` printed and returns each
  dynamic number as `[low, expected, high]` next to the scored value, by re-running the twin (about 80 s on 2 cores).
- `calibration.design_ranges(design, print_report)` gives the resonance and acceleration ranges in closed form
  from an existing `print_report.json`, in under a second (`python -m mechloop.twin.calibration design ...`).

## Changes needed elsewhere (not made)

1. `mechloop/twin/score.py`: after building `s`, add
   `s["uncertainty"] = calibration.design_ranges(design_path, out / "nominal" / "print_report.json", frame_stiffness=pm.struct_stiffness, max_clean_accel=s["max_clean_accel_mm_s2"])`
   (or `evals.score_uncertainty` behind a flag), and report `accel_owners_would_run_mm_s2` beside `max_clean_accel_mm_s2`.
2. `mechloop/twin/__init__.py`: the comment on `PrinterMap.belt_ea_n` can now say the value is supported by three
   machines with a 15 to 27 kN range. A `toolhead_mount_n_per_mm` term, or better:
3. `mechloop/verifiers/fea.py` or the designs' nozzle stiffness cases: include the guide block's tilt compliance
   (the trade study's `estimates.py` already has block moment stiffness values) so that `struct_stiffness` contains
   the belt-to-nozzle spring. This is the single change that would most improve the twin's resonance predictions.
4. `AGENT.md` scorecard table: say that `max_clean_accel_mm_s2` is a step-loss ceiling.

## What remains unvalidated, and the data that would settle it

| Area | Status | Data needed |
|---|---|---|
| Resonance, gantry and bed axes | tested blind, ±15 to 20 % | raw accelerometer spectra (Klipper CSV) from stock machines with weighed moving parts would tighten it |
| Resonance, toolhead axes | fails blind; fixed only by a fitted term | carriage tilt stiffness from the rail maker (Hiwin tables, blocked), or a push test on a real toolhead |
| Belt EA at 9 and 12 mm width | extrapolated | a maker's figure (Gates), or a resonance from a machine with 9 mm belts and known masses |
| Motor magnetic spring | confounded with belts; low sensitivity on the three machines, higher on v5 | a resonance measured at two run currents on one machine |
| Step-loss acceleration and top speed | not tested; only "stock settings do not skip" | a controlled test naming motor, current, voltage and mass |
| Ringing amplitude, cross-track error | not tested | measured ringing on a printed part, or accelerometer time traces |
| Acceleration without input shaping | not tested | ringing-tower results with the frequency and the acceleration at which ringing became visible |
| Extrusion (lag, pressure advance, flow limits) | not tested here; the 30 ms lag sits in the documented pressure-advance range | measured pressure-advance values with hotend, filament and extruder named; max volumetric flow tests |
| Thermal (heat-up, warping, cooling) | not in the twin | heat-up curves with heater power and bed mass; nothing short of prints for warping |
| Dimensional accuracy | not tested; no usable published measurements were found | calibration-cube measurements from stock machines with speeds and accelerations stated |
| Our own machine | nothing measured | one accelerometer run and one weighed toolhead on the built v5 would replace most of this table |

## Limits of this study

- The measurements are shaper frequencies, not resonance peaks, pooled over shaper types, from modified machines
  whose owners publish their configs. They are many and they agree with the few forum reports found, but they
  are not laboratory data.
- Several community sites were blocked (klipper.discourse.group, forum.vorondesign.com, ellis3dp.com,
  forum.prusa3d.com, reddit.com, forum.duet3d.com, wiki.bambulab.com, os.ratrig.com). Ellis' guide, Prusa and
  Bambu data were therefore not used.
- Three machines, two of them from one design family. One wheeled machine. No machine with belts wider than 6 mm.
- The reference machines were run through the axis formula and the stepper simulation, not through a full
  simulated print: there is no `Design` file for them. CoreXY is treated as two motors and two belts acting
  together on each axis, as in `reference.py`.
- Ender 3 motor current is recalled, not sourced.
