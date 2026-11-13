# Printer and digital-twin evaluation

Everything here was computed in simulation. Friction, extruder lag, damping and belt stiffness are assumed values; the sensitivity section shows which of them matter.

## Summary

**The printer (`designs/printer.py`)**
- Passes all seven benchmark prints. Thin 0.8 mm walls print as a single bead, and bridges are reported but not judged (no sag model).
- Prints cleanly up to 5x its nominal 4000 mm/s² acceleration at nominal speed, and up to 4x speed at 2x acceleration. Beyond that the belts ring, outlines distort and the Y motor loses steps.
- Reaches all four bed corners and the full 140 mm height with no collisions.
- Keeps passing with every assumed value made worse at once (friction doubled, torque -30%, +300 g toolhead, belts half as stiff, less damping).
- Fails as it should on gross faults (motor current at 10%, a seized rail, bed datum 0.3 mm off either way) and degrades without failing on moderate ones (slack belt, 0.5 mm lost motion, a stiff rail).
- Most useful design finding: smaller motors leave no acceleration margin at all, and a 350 g direct-drive extruder halves it.

**The twin**
- 13 validation tests pass (`tests/test_twin_validation.py`): agreement with the slicer's own time and filament estimates, an independent MuJoCo integration of the same axis, injected layer shift / under-extrusion / scale error / bed datum error reported at the injected size, results unchanged when the time step and raster are halved, ringing at the predicted frequency.
- The MuJoCo cross-check found a real bug: the stepper integrator read the command one sub-step early, biasing lag figures by up to about 0.025 mm. Fixed; the two now agree to 0.002-0.004 mm.
- Fed only documented Voron 2.4 values, the axis model predicts X resonance 56-76 Hz (measured 54-62) and Y 34-45 Hz (measured 38-50), and no step loss at three configurations real machines run. The X prediction sits high; with belt stiffness known only to about ±30% this cannot be narrowed further in simulation.
- Belt stiffness is the assumed value the results depend on most. No sensitivity run changed a pass into a fail.

**What this does not establish**
- Anything thermal: warping, adhesion, sag, cooling.
- The acceleration at which a real machine first loses steps; no controlled measurement exists to compare with.
- The ranking of design variants near the failure boundary: it is not monotonic (stiffer belts scored lower than baseline), so differences under about 2x there should not be read as real.
- The reality check uses a physics-based motor torque-speed model in `mechloop/twin/reference.py`, not the catalog torque curve the printer design uses.

## Benchmark print suite

| Part | Tests | Result | Print time (s) | Slicer's estimate (s) | Outline match (min) | Avg outline offset (mm) | Worst bulge / recess (mm) | Holes open | Longest unsupported gap (mm) |
|---|---|---|---|---|---|---|---|---|---|
| cube | basic dimensional accuracy | pass (warnings) | 509 | 512 | 0.988 | -0.015 | 0.40 / 0.15 | – | 1.6 |
| thin_wall | 0.8 mm walls: single/double bead control | pass (warnings) | 477 | 470 | 0.922 | -0.017 | 0.45 / 0.45 | 1.00 | 0.0 |
| tolerance | holes 2-6 mm and slots 0.4-1.5 mm stay open and on size | pass (warnings) | 815 | 852 | 0.985 | 0.019 | 0.40 / 0.15 | 0.94 | 2.0 |
| overhang | overhangs at 30, 45 and 60 degrees from vertical | pass (warnings) | 1440 | 1486 | 0.984 | -0.021 | 0.35 / 0.20 | – | 2.0 |
| bridge | unsupported bridges of 10, 20 and 30 mm | pass (warnings) | 1431 | 1509 | 0.975 | 0.065 | 0.40 / 0.20 | – | 29.6 |
| tower | tall thin part: many short moves, Z travel | pass | 1240 | 1291 | 0.982 | -0.022 | 0.10 / 0.20 | – | 0.0 |
| first_layer | large first layer: flow and coverage | pass (warnings) | 1025 | 1014 | 0.998 | -0.022 | 0.35 / 0.15 | – | 0.0 |

Passed 7 of 7. The twin has no thermal model, so overhang and bridge parts are scored on geometry only: it reports how far material spans thin air, not how much it sags.

## Speed and acceleration envelope

Short cube printed at multiples of the nominal speeds (45-60 mm/s printing, 150 mm/s travel) and of the nominal 4000 mm/s² acceleration. Each cell: result, print time, worst nozzle lag on Y.

| Speed × | accel ×1 | accel ×2 | accel ×3 | accel ×4 | accel ×5 | accel ×7.5 | accel ×10 |
|---|---|---|---|---|---|---|---|
| ×1 | ok, 289 s, 0.27 mm | ok, 284 s, 0.48 mm | ok, 282 s, 0.67 mm | ok, 281 s, 0.84 mm | ok, 281 s, 0.95 mm | FAIL, 280 s, 1.21 mm | FAIL, 280 s, 1.18 mm |
| ×2 | ok, 220 s, 0.35 mm | ok, 211 s, 0.85 mm | ok, 208 s, 0.87 mm | ok, 206 s, 1.01 mm | FAIL, 206 s, 4.69 mm | FAIL, 204 s, 5.22 mm | FAIL, 204 s, 8.86 mm |
| ×3 | ok, 208 s, 0.36 mm | ok, 197 s, 1.01 mm | ok, 194 s, 0.90 mm | FAIL, 192 s, 2.49 mm | FAIL, 190 s, 2.60 mm | FAIL, 189 s, 5.74 mm | FAIL, 188 s, 14.33 mm |
| ×4 | ok, 205 s, 0.35 mm | ok, 193 s, 1.01 mm | FAIL, 188 s, 2.44 mm | FAIL, 186 s, 4.57 mm | FAIL, 185 s, 4.70 mm | FAIL, 183 s, 12.23 mm | FAIL, 182 s, 14.58 mm |

Fastest passing setting: speed ×4, acceleration ×2 (193 s against 289 s at nominal).

## Build-volume coverage

| Where | Result | Collisions during print | Outline match (min) | Worst lag X / Y / Z (mm) |
|---|---|---|---|---|
| at_+0_+0 | pass (warnings) | 0 | 0.989 | 0.113 / 0.269 / 0.003 |
| at_+70_+70 | pass (warnings) | 0 | 0.988 | 0.110 / 0.268 / 0.002 |
| at_+70_-70 | pass (warnings) | 0 | 0.989 | 0.112 / 0.269 / 0.003 |
| at_-70_+70 | pass (warnings) | 0 | 0.989 | 0.110 / 0.269 / 0.003 |
| at_-70_-70 | pass (warnings) | 0 | 0.988 | 0.110 / 0.269 / 0.003 |
| tall_tower | pass | 0 | 0.979 | 0.105 / 0.286 / 0.003 |

The twin's dynamics do not vary with position (stiffness is taken at mid-travel), so this section checks reachability and collisions across the bed and over the full Z travel, not position-dependent quality.

## Robustness to assumed values

The same short print with the assumptions made worse. A sound design keeps passing.

| Case | Result | RMS lag X / Y (mm) | Worst lag X / Y (mm) | Worst motor error X / Y (mm) | Outline offset (mm) | Bulge (mm) | Outline match |
|---|---|---|---|---|---|---|---|
| nominal | pass (warnings) | 0.028 / 0.061 | 0.113 / 0.269 | 0.021 / 0.042 | -0.015 | 0.35 | 0.989 |
| rail friction x2 | pass (warnings) | 0.052 / 0.087 | 0.141 / 0.300 | 0.027 / 0.044 | 0.021 | 0.40 | 0.988 |
| motor torque -30% | pass (warnings) | 0.030 / 0.064 | 0.121 / 0.297 | 0.031 / 0.059 | -0.019 | 0.35 | 0.989 |
| toolhead +300 g | pass | 0.036 / 0.075 | 0.189 / 0.360 | 0.035 / 0.053 | 0.012 | 0.30 | 0.987 |
| extruder lag x2 | pass (warnings) | 0.028 / 0.061 | 0.113 / 0.269 | 0.021 / 0.042 | -0.015 | 0.40 | 0.988 |
| belts half as stiff | pass (warnings) | 0.051 / 0.108 | 0.201 / 0.526 | 0.021 / 0.041 | 0.033 | 0.40 | 0.983 |
| less damping | pass (warnings) | 0.030 / 0.074 | 0.116 / 0.312 | 0.022 / 0.048 | 0.036 | 0.35 | 0.985 |
| all of the above | pass (warnings) | 0.115 / 0.181 | 0.336 / 0.621 | 0.048 / 0.073 | 0.117 | 0.50 | 0.969 |

## Machine faults

Faults injected into the machine. 'Expected' is what a real printer would do.

| Case | Expected | Result | RMS lag X / Y (mm) | Worst lag X / Y (mm) | Worst motor error X / Y (mm) | Outline offset (mm) | Bulge (mm) | Outline match |
|---|---|---|---|---|---|---|---|---|
| none | pass | pass (warnings) | 0.028 / 0.061 | 0.113 / 0.269 | 0.021 / 0.042 | -0.015 | 0.35 | 0.989 |
| slack X belt (30% stiffness, 0.3 mm lost motion) | degrade | pass (warnings) | 0.214 / 0.156 | 0.454 / 0.717 | 0.020 / 0.034 | 0.033 | 0.45 | 0.977 |
| 0.5 mm lost motion on Y | degrade | pass (warnings) | 0.028 / 0.247 | 0.113 / 0.648 | 0.021 / 0.060 | -0.068 | 0.45 | 0.967 |
| motor current 40% | degrade or pass | pass (warnings) | 0.035 / 0.070 | 0.145 / 0.342 | 0.057 / 0.114 | -0.018 | 0.40 | 0.989 |
| motor current 10% | fail | FAIL: first_layer_height, layer_missing, lost_steps, print_dimension_error, print_layer_shift, print_outline_defect, print_outline_poor | 0.071 / 22.404 | 0.245 / 59.571 | 0.198 / 59.521 | -4.917 | 1.50 | 0.000 |
| bed 0.3 mm too low | fail | FAIL: first_layer_height | 0.028 / 0.061 | 0.113 / 0.269 | 0.021 / 0.042 | -0.015 | 0.35 | 0.989 |
| bed 0.3 mm too high | fail | FAIL: nozzle_in_bed | 0.028 / 0.061 | 0.113 / 0.269 | 0.021 / 0.042 | -0.015 | 0.35 | 0.989 |
| bed 0.05 mm too low | pass | pass (warnings) | 0.028 / 0.061 | 0.113 / 0.269 | 0.021 / 0.042 | -0.015 | 0.35 | 0.989 |
| stiff Y rail (40 N friction, motor can push 54 N) | degrade | pass (warnings) | 0.028 / 0.465 | 0.113 / 0.935 | 0.021 / 0.206 | -0.050 | 0.45 | 0.977 |
| seized Y rail (80 N friction) | fail | FAIL: lost_steps, print_dimension_error, print_layer_shift, print_outline_defect, print_outline_poor | 0.028 / 7.955 | 0.113 / 18.168 | 0.021 / 17.831 | -4.786 | 1.50 | 0.046 |

Rail misalignment and binding are not modelled, so they are not in this table.

## Design variants

Each variant at nominal settings, then the highest acceleration it prints cleanly at with speeds doubled (nominal acceleration is 4000 mm/s²).

| Variant | Resonance X / Y (Hz) | Nominal: RMS lag Y (mm) | Nominal: outline match | Highest clean acceleration (mm/s²) | What fails first above that |
|---|---|---|---|---|---|
| baseline | 78 / 40 | 0.061 | 0.989 | 16000 | lost_steps, print_dimension_error, print_layer_shift, print_outline_defect, print_outline_poor at 20000 |
| direct-drive extruder (+350 g on the toolhead) | 53 / 36 | 0.077 | 0.988 | 8000 | lost_steps, print_layer_shift, print_outline_defect, print_outline_poor at 12000 |
| short motors (65% torque) | 75 / 39 | 0.064 | 0.989 | 4000 | print_layer_shift, print_outline_defect at 8000 |
| 9 mm belts (1.5x stiffness) | 91 / 47 | 0.045 | 0.990 | 12000 | lost_steps, print_layer_shift, print_outline_defect, print_outline_poor at 16000 |
| light toolhead (-100 g) | 96 / 42 | 0.058 | 0.989 | 16000 | lost_steps at 20000 |
| stiff + light (9 mm belts, -100 g) | 111 / 50 | 0.042 | 0.990 | 8000 | lost_steps, print_layer_shift, print_outline_defect, print_outline_poor at 12000 |

Variants are what-if changes to mass, torque and belt stiffness on the same CAD; they were not re-verified as full designs.

## Sensitivity to assumed parameters

Each parameter moved to 50% and 150% of its assumed value (torque and mass over a similar range). Cells show low → high; parameters are ranked by total relative effect.

| Parameter | rms lag y mm | worst lag y mm | max bulge mm | outline offset mm | outline iou min | Changes pass/fail? |
|---|---|---|---|---|---|---|
| (baseline) | 0.061 | 0.269 | 0.350 | -0.015 | 0.989 | |
| belt stiffness | 0.108 → 0.044 | 0.526 → 0.225 | 0.400 → 0.350 | 0.033 → -0.020 | 0.983 → 0.990 | no |
| rail friction | 0.055 → 0.073 | 0.294 → 0.278 | 0.350 → 0.400 | -0.019 → 0.019 | 0.989 → 0.988 | no |
| toolhead mass | 0.058 → 0.068 | 0.252 → 0.343 | 0.350 → 0.350 | -0.018 → 0.018 | 0.989 → 0.987 | no |
| belt/frame damping | 0.068 → 0.057 | 0.303 → 0.260 | 0.350 → 0.350 | 0.019 → -0.018 | 0.987 → 0.990 | no |
| motor torque | 0.066 → 0.060 | 0.329 → 0.275 | 0.400 → 0.350 | -0.017 → -0.017 | 0.988 → 0.988 | no |
| stepper damping | 0.064 → 0.060 | 0.281 → 0.264 | 0.400 → 0.400 | -0.014 → -0.018 | 0.988 → 0.989 | no |
| extruder lag | 0.061 → 0.061 | 0.269 → 0.269 | 0.350 → 0.400 | -0.015 → -0.016 | 0.989 → 0.988 | no |

## Reality check against a documented printer

Voron 2.4 350 (CoreXY), documented values only. Uncertain inputs were sampled over their plausible ranges (400 samples).

| Quantity | Twin predicts | Reported for real machines | Verdict | Note |
|---|---|---|---|---|
| X resonance | 55.5–75.5 Hz (median 65.2) | 54.0–62.0 Hz | consistent |  |
| Y resonance | 34.0–44.8 Hz (median 39.6) | 38.0–50.0 Hz | consistent |  |
| no step loss at stock config (300 mm/s, 3000 mm/s^2, 0.8 A) | no skip | runs without skipping | consistent |  |
| no step loss at tuned config 1 (450 mm/s, 7000 mm/s^2, 0.875 A) | no skip | runs without skipping | consistent |  |
| no step loss at tuned config 2 (650 mm/s, 20000 mm/s^2, 1.4 A) | no skip | runs without skipping | consistent |  |
| acceleration at which steps are first lost, stock current, 300 mm/s | x: 63900.0, y: 33700.0 | no controlled measurement found; anecdotes pass 20,000-23,000 | not testable | prediction only; it would be contradicted by a stock machine skipping below this |
| speed where torque starts to fall, 1.4 A: 1.8 deg vs 0.9 deg motor | 1.8 deg: 511, 0.9 deg: 274, ratio: 1.86 | 1.8 deg top speed: [800.0, 1000.0], 0.9 deg top speed: 450.0, ratio: [1.78, 2.22] | consistent | compares the ratio between motors; absolute top speed depends on the load during the test |
| extruder lag time constant | 0.03 | 0.03–0.06 s | consistent | the twin's assumed 30 ms lag sits inside the documented pressure-advance range for direct drive |

Compute time: 8 minutes on 4 cores.
