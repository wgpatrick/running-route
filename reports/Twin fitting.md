# Twin fitting: what the digital twin now takes from published data, and what it still assumes

2026-11-15. Code: `mech-ai/mechloop/twin/` (`fitted.py`, `fitted_parameters.json`, `machine.py`, `calibration.py`,
`evals.py`, `score.py`), `mech-ai/mechloop/electrical.py`. Fits and their outputs: `mech-ai/research_notes/fitting/`.
This follows `Twin calibration study.md` (the blind three-machine comparison) and `Datasets and models for fitting the
twin.md` (the data survey and fitting plan).

## Answer in brief

- **The largest model gap is closed, by a term fitted after the fact.** The axis that carries the nozzle now has a
  spring between belt clamp and nozzle: the carriage turning on its guide block. With it the three toolhead axes of the
  blind study go from +42, +18 and +70 % to +1, -1 and -1 %. That second comparison is not blind. The honest figure is
  the two rail machines predicted from each other: +2.3 % and -1.3 %.
- **One number, 10 N/µm, explains both rail machines** once each machine's own block length and nozzle offset are put
  in (9.5 and 10.5 N/µm). As flat stiffnesses they were 121 and 230 N/mm. It is not a block stiffness measurement: it
  lumps the block's tilt with those machines' printed mounts.
- **Ringing damping is 0.065 on the toolhead axis and 0.069 on gantry and bed axes**, range 0.04 to 0.12, from a mode
  fit of 35 machine-axes. The first look's 0.08 and 0.12 were inflated by its estimator, as that report suspected.
- **The extruder lag now depends on the drive.** Direct drive 0.03 s, Bowden 0.24 s at a 0.4 mm nozzle. `printer_v5`
  is Bowden and was being simulated with the direct-drive value; it now gets 0.235 s.
- **The hotend fit did not give a usable default by itself.** The logged Ender 3 hotend fits well (held-out run
  within 6 °C over 20 minutes) but is half as heavy as an E3D V6 and cycles in 5 s in a relay test where real
  machines take 24 to 55 s. The default V6 class therefore uses the fitted structure with Prusa's published V6 totals,
  and its sensor lag was raised to 8 s to bring the relay period inside the public range. Said plainly: the lag is
  adjusted, not fitted.
- **The scorecard no longer presents the step-loss ceiling as a usable acceleration.** It reports the acceleration an
  owner would run with input shaping beside it, and a `[low, expected, high]` range beside every headline number.
- **For `printer_v5`**: X resonance 88.5 Hz becomes 71.6 Hz (64 to 79). Y stays at 62 Hz (57 to 64). The step-loss ceiling is
  12,000 mm/s² (8,000 to 14,000) and the acceleration an owner would run is 6,800 mm/s² (4,500 to 9,500). **For
  `printer_v4`**: X 68.4 Hz becomes 55.4 Hz (50 to 61), now just below Y; an owner would run 5,300 mm/s² (3,400 to 7,900).
  No verifier changed between pass and fail on either design.
- Belt stiffness, friction, the step-loss boundary, guide-block stiffness itself, frame joints, the bed's thermal
  constants and anything about heat in the printed part remain unfitted.

## 1. Toolhead compliance between belt and nozzle

### The model

- The force that moves the toolhead enters at the belt clamp, next to the guide block. The nozzle hangs off the rail by
  an arm r. A force along the rail at the nozzle turns the carriage about an axis across the rail.
- A block resists that turn only over its own ball-track length L: K_rot = k L² / 12 per block. Blocks spaced along the
  rail add k a² each (a measured from their centroid). The stiffness left at the nozzle is K_rot / r².
- This is the rule `verifiers/ratings.py` already used for cantilevered loads. It is now one function,
  `ratings.guide_tilt`, used by the twin as well. `ratings.py`'s own check and its assumed 40 N/µm are unchanged.
- The twin applies the term to the axis whose moving body is the tool body (`machine.toolhead_compliance`), in series
  with the belts and with the design's FEA nozzle stiffness.
- Derived from the design: number of blocks with `guides=` on that joint, their spacing, ball-track length (Hiwin L1,
  32.4 mm for the MGN12H from the vendor file), nozzle distance from the rail.
- Fitted: the effective block stiffness k = 10 N/µm (7.5 to 16).

The FEA case was not changed. It still bonds rail and block, so it has the mounts and the beam but not the tilt; making
it include the tilt needs a compliant layer between rail and block in the mesh, which was not attempted. The two are
added in series. Because the fitted k already contains the reference machines' printed mounts, a design's own mount
compliance is counted partly twice. For `printer_v5` the whole FEA term lowers X by 2 %, so the double count is smaller than that.

### Where k comes from

The blind study found that the toolhead axes needed an extra series spring of 121 N/mm (Voron 0.2) and 230 N/mm
(Trident 250). Those two numbers differ by a factor of two. With each machine's geometry they do not:

| Machine | Block | Ball track L | Nozzle off the rail (below, sideways) | Arm r | Implied K_rot | Implied k |
|---|---|---|---|---|---|---|
| Voron 0.2 | MGN7H | 21.8 mm (recalled, unverified) | 50.5, 23.9 mm | 55.9 mm | 378 N·m/rad | 9.5 N/µm |
| Trident 250 | MGN12H | 32.4 mm (vendor file) | 51.0, 37.2 mm | 63.1 mm | 916 N·m/rad | 10.5 N/µm |

Nozzle offsets are from the makers' CAD (`research_notes/trade_study/measurements.json`). They are recorded in a new
file, `mechloop/twin/calibration_posthoc.json`. The frozen inputs (`calibration_machines.json`) are untouched and their
hash is still pinned by a test.

The range 7.5 to 16 N/µm is what the quartiles of the owners' measured frequencies imply for the Voron 0. The Trident's
upper quartile implies a much stiffer value (11 configurations); the range does not cover it.

The Ender 3 rides on wheels. It keeps a flat figure of its own, 40 N/mm (30 to 60), from one machine. No catalogue part
uses it.

### The three machines again (not blind)

`python -m mechloop.twin.calibration posthoc`. Output: `research_notes/fitting/posthoc_comparison.json`.

| Machine | Axis (what it moves) | Measured median | Blind prediction | Error | With the term | Error | Leave one machine out | Error |
|---|---|---|---|---|---|---|---|---|
| Voron 0.2 | X (toolhead) | 79.2 Hz | 112.6 | **+42.2 %** | 80.1 | +1.2 % | 81.0 (k from the Trident) | +2.3 % |
| Voron 0.2 | Y (gantry) | 73.8 | 85.2 | +15.4 % | 85.2 | +15.4 % | no term | |
| Trident 250 | X (toolhead) | 64.6 | 76.2 | **+18.0 %** | 64.2 | -0.6 % | 63.7 (k from the Voron 0) | -1.3 % |
| Trident 250 | Y (gantry) | 48.6 | 44.5 | -8.4 % | 44.5 | -8.4 % | no term | |
| Ender 3 | X (toolhead) | 50.6 | 85.8 | **+69.6 %** | 50.1 | -1.0 % | not possible | |
| Ender 3 | Y (bed) | 45.0 | 45.6 | +1.3 % | 45.6 | +1.3 % | no term | |

- All six axes, mean absolute error: 25.8 % blind, 4.7 % with the term.
- Toolhead axes, mean signed error: +43.3 % blind, -0.1 % with the term.
- Gantry and bed axes: unchanged, mean absolute 8.4 %. They now set the error of the model.

How to read it:

- The "with the term" column is a fit to the same data. One parameter was fitted to two rail machines, and the wheeled
  machine has a parameter of its own, so its -1.0 % is zero by construction (the remainder is rounding of 41 to 40).
- The leave-one-out column is the test: +2.3 % and -1.3 %. With the flat figure of the first study the same test gave
  -11 % and +15 %.
- Two machines agreeing is weak evidence. One of the two block lengths is recalled. A third rail machine with a
  different block or nozzle offset would be a real test; the resonance corpus has the spectra but not the geometry.
- The owners of one machine model differ by ±10 to ±25 % among themselves. An agreement of 2 % between medians is
  better than the data can support and should not be read as the model's accuracy.

## 2. Fits from the datasets

Every row is also in `mechloop/twin/fitted_parameters.json`, which the twin and the heater model load. Nothing in the
code carries a second copy. `python -m mechloop.twin.fitted` prints it.

| Parameter | Old | New | Range | Source | Held-out check |
|---|---|---|---|---|---|
| Toolhead tilt, effective block stiffness | no such term | 10 N/µm | 7.5 to 16 | X axes of the Voron 0.2 and Trident 250, with CAD nozzle offsets and block lengths | each machine from the other: +2.3 %, -1.3 % |
| Toolhead on wheels | no such term | 40 N/mm | 30 to 60 | Ender 3 X axis | none possible (one machine) |
| Ringing damping ratio, toolhead axis | 0.02 to 0.05 (from two assumed dampers) | 0.065 | 0.043 to 0.116 | mode fit of resonance spectra, 17 machines | halves of the machines: 0.104 (5) against 0.059 (12); owner-entered values 0.03 to 0.09 inside |
| Ringing damping ratio, gantry or bed axis | same | 0.069 | 0.035 to 0.118 | same, 18 machines | 0.090 (6) against 0.053 (12) |
| Extruder lag, direct drive, 0.4 mm | 0.03 s assumed | 0.0315 s | 0.020 to 0.058 | 36 factory pressure-advance expressions, PrusaSlicer | nozzle sizes left out: +5 % (0.5 mm), +1 % (0.8 mm); one filament left out: 31 % |
| Extruder lag, Bowden, 0.4 mm | 0.03 s (the same value) | 0.24 s | 0.18 to 0.40 | 17 factory expressions for the Prusa MINI | 0.8 mm left out: +19 %; one filament left out: 25 % |
| Melt-rate cap, V6 class | none | 11 mm³/s | 10 to 15 | E3D 10, Ellis 11, PrusaSlicer MK3 PLA profiles 15 | not a fit; three sources |
| Melt-rate cap, Revo | none | 12 mm³/s | 11 to 13 | E3D 13, Ellis 11 | not a fit |
| Hotend, fitted machine (Ender 3) | — | 7.15 J/K; 0.085 W/K still air, 0.108 W/K full fan at 245 °C | — | eight logged runs, three-node model | print run held out: RMSE 6.1 °C over 1182 s, +3.0 % power; second run held out: 2.8 °C |
| Hotend, V6 class (default) | 13.5 J/K, free convection on 16 cm², sensor lag 4.5 s (all assumed) | 12.1 J/K; 0.049 W/K still, 0.099 W/K full fan; node split from the fit | 6.5 to 16.8 J/K; 0.049 to 0.14 W/K | totals: Prusa's E3D V6 model; structure: the Ender fit; range: Marlin MPC sets | no log of a V6; relay test only |
| Hotend sensor lag, V6 class | 4.5 s assumed | 8.0 s | 2.1 to 10 | set so the relay period enters the public range | adjusted to that check, see 2.3 |
| Hotend, Revo | 6.9 J/K from part masses, lag 2 s, constant 40 W | 8.77 J/K; 0.040 W/K still, 0.065 full fan; lag 0.27 s; PTC power | 6.9 to 9.1 J/K | totals: Prusa's Revo model; structure: the Ender fit; power: E3D | none |
| Bed thermal | assumed | unchanged | — | — | relay period 48 s inside the public 23 to 161 s |
| Acceleration owners run / shaper rule | not reported | 0.5 | 0.4 to 0.65 | three machines (0.44, 0.51, 0.62) | none; the range is their spread |
| Belt EA per 6 mm | 22 kN | unchanged | 15 to 27 kN | blind comparison | blind: +15, -8, +1 % on the axes it governs |
| Stepper damping ratio | 0.25 | unchanged | 0.125 to 0.375 | assumed | no |

### 2.1 Ringing damping

Script: `research_notes/fitting/fit_damping.py`. Output: `damping_fit.json`.

- Data: the 98 resonance-test spectra stored under licence in `klipper_resonance_psd_corpus/` (16 repositories). 62
  are toolhead X or Y tests. One file per machine and axis was kept, the one with the cleanest peak: 17 X and 18 Y from
  15 repositories.
- Method: one or two damped modes plus a floor, fitted to the excited axis's spectrum from 12 to 135 Hz, with the model
  smeared by the analysis window Klipper used. The second mode is kept only if it improves the fit clearly (BIC). The
  damping of the larger mode is reported. 34 of 35 fits kept two modes.
- Estimator check on synthetic spectra of known damping, same bin width and window: the mode fit returns 0.030, 0.051,
  0.080 and 0.120 for 0.03, 0.05, 0.08 and 0.12. The half-power width returns 0.053, 0.068, 0.094 and 0.136. So the
  first look read 0.015 to 0.023 high, as it said it might.

| | Machines | 10th percentile | Median | 90th percentile | Half-power width, same files |
|---|---|---|---|---|---|
| X files (toolhead axis) | 17 | 0.043 | 0.065 | 0.116 | 0.088 |
| Y files (gantry or bed axis) | 18 | 0.035 | 0.069 | 0.118 | 0.129 |
| CoreXY only, X / Y | 9 / 9 | | 0.049 / 0.049 | | |
| Bed slingers only, X / Y | 4 / 4 | | 0.107 / 0.079 | | |

- Held out: the machines were split in two by a hash of the repository name. The halves give 0.104 (5 machines) and
  0.059 (12) on X, 0.090 (6) and 0.053 (12) on Y. The halves differ by more than X differs from Y. The range is the
  result; the second digit is not.
- Independent check: the 39 damping ratios owners entered by hand (calibration study) run from 0.03 to 0.09 with
  medians of 0.05 to 0.07. They sit inside the range and at the fitted medians.
- In the twin: the stepper's damper stays at its assumed 0.25. The belt and frame damper of each axis is set so that the
  mode the load rings in has the fitted ratio (`machine.spring_damping_for`). For `printer_v5` that damper becomes 0.175
  on X and 0.119 on Y, where it was 0.05 on both.
- Limits. 35 machine-axes, mostly Vorons. Machine class is guessed from the repository name. One repository
  (`Jumpybeetroot/shaper-sim`) is a simulator's sample file and may not be a measurement. X and Y in a file name are
  taken as toolhead axis and gantry or bed axis, which is right for CoreXY and bed slingers and unknown for the rest.

### 2.2 Hotend thermal model

Script: `fit_hotend.py`. Outputs: `hotend_fit.json`, `hotend_fit_holdout_1927.json`, `hotend_fit_free.json`.

Structure, kept in the existing lumped interface (`ThermalNet`, `HeaterPlant`), so the electrical verifier runs as before:

- three nodes: cartridge, block (where the sensor sits), nozzle side;
- loss from the block as a fixed conductance plus a term growing as T⁴, plus a part-fan term
  g_fan × ((fan − f0) / (1 − f0))ⁿ (`ThermalNet.fan`, new); a small loss from the nozzle node;
- a first-order sensor lag;
- heat taken by the filament as physics, not fitted (density × specific heat × section × speed).

Fit to eight runs of one Ender 3 (40 W cartridge, V6-style hotend), 40 W and 25 °C ambient assumed:

| | Value |
|---|---|
| Total capacity | 7.15 J/K (cartridge 1.5, block 2.0, nozzle side 3.65) |
| Loss at 245 °C, still air | 0.085 W/K, of which 0.034 from the T⁴ term |
| Loss at 245 °C, part fan at 25 / 50 / 100 % | 0.100 / 0.104 / 0.108 W/K |
| Sensor lag | 0.64 s |
| Calibration RMSE | 3.8 °C (one mass on the same runs: 9.5 °C) |
| Held-out print run, 1182 s open loop | RMSE 6.1 °C, bias -5.4 °C: the model needs 3.0 % more power than was logged |
| Same without the filament term | bias +20 °C |
| One mass on the held-out run | RMSE 51 °C |
| Second fit, heat / fan / 150 °C hold / cool run also held out | RMSE 2.8 °C on it (calibration 4.0) |

What the fit does and does not establish:

- The slow behaviour is well determined: total capacity and loss are the same to 3 % whichever run is held out.
- The fast path from heater to sensor is not. With wide bounds the cartridge shrinks to 0.2 J/K behind 17 W/K with a
  sensor lag of 6 s, at an RMSE of 3.7 °C, no worse. With the cartridge and its contact held to what the parts are
  (1.5 to 4 J/K, 0.3 to 1.5 W/K) they end on those bounds with a lag of 0.64 s. The logs, sampled 3 to 4 times a second
  under PID control, cannot tell these apart. So "three-node" is a structure the data permits, not one it demands: two
  masses and a delay fit as well.
- The fan law is weakly determined (exponent 0.24, at or near its bound in both fits).
- Against published constants: capacity 7.15 J/K is at the bottom of Marlin's eight MPC sets (6.5 to 16.8) and about
  half Prusa's E3D V6 (12.1). Loss 0.085 W/K is inside Marlin's range (0.052 to 0.14) and above Prusa's (0.049). The
  log itself shows why: this hotend cools 2.6 K/s at 245 °C and holds 245 °C at 47 % duty. It is a light, bare block.

What the catalogue hotends get:

| Class | Used for | Fitted | Taken from a maker's model | Extrapolated |
|---|---|---|---|---|
| `ender3_fitted` | the validation test only | everything above | — | — |
| `v6` | any cartridge in a block (`heater_cartridge`, the V6 proxies of printer_v4 / v5) | nothing on a V6 | total capacity 12.1 J/K, loss 20.5 to 10.1 K/W (Prusa, E3D V6) | node split, T⁴ share and fan-law shape from the Ender fit; sensor lag 8 s from the relay check |
| `revo` | `hotend_revo` (PTC HeaterCore) | nothing on a Revo | total capacity 8.77 J/K, loss 25.3 to 15.4 K/W, lag 0.27 s (Prusa, Revo); 14.4 Ω and 0.002078 /K (E3D) | node split, T⁴ share and fan-law shape from the Ender fit |

The Revo is a different hotend from the one that was logged. Its numbers are a maker's totals on a borrowed structure.
Prusa's own Revo model has a power term falling 0.14 % per kelvin, which agrees with E3D's PTC figures (40 W cold,
27 W at 250 °C).

The part's own estimates can be brought back with `params["thermal_model"] = "catalog"` on the heater device.

### 2.3 Relay test: dead time and sensor lag

Script: `relay_check.py`. Output: `relay_check.json`. Klipper's own `ControlAutoTune` class runs the test on the model.
The public figures are the 81 distinct extruder and 70 distinct bed PID sets in Klipper's example configurations, each
turned back into the ultimate period Tu and gain Ku. Hotends tested at 210 °C, beds at 60 °C.

| Heater model | Tu | Ku | Public 10th to 90th percentile (median) | Inside? |
|---|---|---|---|---|
| Hotend, old assumed model, 40 W | 25.8 s | 0.174 | Tu 24 to 55 s (37); Ku 0.10 to 0.20 (0.16) | yes, at the low edge |
| Hotend, fitted Ender 3, 40 W | 5.4 s | 0.173 | same | **no** |
| Hotend, V6 class with Prusa's lag of 2.1 s, 40 W | 12.6 s | 0.187 | same | **no** |
| Hotend, V6 class as adopted (lag 8 s), 40 W | 24.9 s | 0.164 | same | yes, at the low edge |
| Hotend, V6 class as adopted, 30 W (printer_v4 / v5) | 22.8 s | 0.208 | same | **no, just under** |
| Hotend, Revo class, PTC 40 W | 5.1 s | 0.288 | same | **no** |
| Bed, printer_v4 | 48.6 s | 0.415 | Tu 23 to 161 s (89); Ku 0.35 to 1.08 (0.46) | yes |
| Bed, printer_v5 | 48.3 s | 0.415 | same | yes |

- The beds are inside the public range on both counts. Nothing was changed.
- The hotend was not. The lag term of the V6 class was raised from Prusa's 2.1 s to 8 s. That is inside the 2.9 to 10 s
  that Marlin's MPC sensor constants imply. It brings a 40 W hotend to the low edge of the range and leaves the 30 W
  cartridge of printer_v4 and v5 just under it.
- This is an adjustment to pass a check, and it does not reach the median. Lag scan at 40 W: 2.1 s gives 12.6 s,
  4 s gives 17.1, 6 s gives 21.0, 8 s gives 24.9, 10 s gives 27.0. A lag alone cannot produce 37 s. The model still
  cycles faster than a typical real hotend, most likely because typical hotends wear a silicone sock and lose less.
- The fitted Ender hotend's 5.4 s is not a model error. Its measured cooling rate makes a short cycle unavoidable. It
  is the reason its absolute values were not made the default.
- The Revo class cycles in 5 s. No Revo-only PID set was found to say whether that is right.

### 2.4 Extruder lag

Script: `fit_extrusion.py`. Output: `extrusion_fit.json`.

- Data: every distinct `M572 S` expression for rigid filaments in PrusaSlicer's factory profile, classed by the printer
  condition in front of it: 36 for direct-drive machines (Nextruder family, MK3.5), 17 for the Bowden MINI.
- A pressure-advance constant equals a first-order lag only for a linear compliance. It is used as the lag.

| Nozzle | Direct drive, median (smallest to largest) | Bowden, median (smallest to largest) |
|---|---|---|
| 0.25 mm | 0.11 s (0.07 to 0.20) | 0.73 s (0.55 to 1.02) |
| 0.3 mm | 0.072 s (0.045 to 0.10) | — |
| 0.4 mm | 0.0315 s (0.020 to 0.058) | 0.24 s (0.18 to 0.40) |
| 0.5 mm | 0.022 s (0.015 to 0.050) | — |
| 0.6 mm | 0.018 s (0.012 to 0.038) | 0.15 s (0.10 to 0.22) |
| 0.8 mm | 0.012 s (0.009 to 0.025) | 0.09 s (0.07 to 0.15) |

- Held out: a power law fitted on 0.4 and 0.6 mm predicts 0.5 mm to +5 % and 0.8 mm to +1 % (direct), 0.8 mm to +19 %
  (Bowden). Below 0.4 mm it fails (-45 % at 0.25 mm). The twin therefore uses the table, with log interpolation
  between sizes, not the law.
- The spread is between filaments. Leaving one filament's value out and predicting it with the median of the rest
  misses by 31 % (direct) and 25 % (Bowden), median. That is the size of the range.
- Selection: `design.printer["extruder"] == "bowden"` selects the Bowden column, otherwise direct. The nozzle comes
  from `printer["nozzle"]`. A Bowden tube length (a `Cable` named "bowden", or `printer["bowden_length"]`) scales the
  part above the direct-drive value in proportion to length, against the MINI's tube taken as 430 mm.
- Extrapolated, not fitted: the length scaling, and the 430 mm (recalled, unverified). One maker's machines.
- `printer_v5`: Bowden, 0.4 mm, 420 mm tube: **0.235 s** (0.176 to 0.392). It had 0.03 s. `printer_v4`: direct, 0.0315 s.
- The pressure-advance sweep of `mechloop tune` now spans 0 to twice the lag in use, where it stopped at 0.06 s.

### 2.5 Melt-rate cap

- Not a fit. Three kinds of published figure per class, at a 0.4 mm brass nozzle and PLA.
- V6 class: E3D 10 mm³/s (600 mm³/min at 220 °C), Ellis' table 11, PrusaSlicer's MK3-family PLA profiles 15 at most
  (median of 90 profiles), MINI 14. Cap 11, range 10 to 15.
- Revo: E3D 13 (PLA at 220 °C), Ellis 11. Cap 12, range 11 to 13.
- For reference: PrusaSlicer high-flow nozzles 26 (median, PLA); Bambu's own PLA profiles 12.
- In the twin (`run_print`): the slicer is given the cap as its maximum volumetric speed, so the G-code never asks for
  more. The report states the flow each requested speed needs at this bead, which speeds the cap limits and the speed
  at the cap (`flow`; warning `flow_limited`; `melt_rate` in the scorecard). A G-code move more than 10 % over the cap
  is an error (`flow_cap_not_respected`).
- The hotend's class comes from the part on the tool body whose SKU starts with `HOTEND`. No such part: V6 class is
  assumed and the report says so. Other nozzle sizes scale the cap in proportion to diameter, which is assumed.
- `printer_v4` and `printer_v5` at their own speeds ask for 3.7 mm³/s (perimeters, 45 mm/s) and 4.9 mm³/s (infill,
  60 mm/s). At the scorecard's 2x sweep they ask for 9.8 mm³/s. Neither is limited by 11 mm³/s. At this bead the cap is
  reached at 135 mm/s.

## 3. Scorecard

`mechloop score` output, changes:

- `step_loss_ceiling_accel_mm_s2`: the number that was `max_clean_accel_mm_s2`. The old key is still written with the
  same value, so existing files and scripts keep working. In the Klipper block the corresponding key is
  `highest_clean_accel_mm_s2`, with the old key kept as well.
- `accel_owners_would_run_mm_s2`: 0.5 × Klipper's shaper smoothing rule (MZV, 0.12 mm) at the lower resonance, with
  the range 0.4 to 0.65 × the rule at the low and high ends of the resonance range. In the Klipper block the same
  factor is applied to Klipper's own `suggested_max_accel` for the shapers it chose.
- `headline`: each headline number as `{"value", "range": [low, expected, high], "meaning"}`. `ranges` holds the same
  ranges by key.
- `melt_rate`, `extruder`, `toolhead_compliance`: what the design selected.

Where the ranges come from:

| Number | How its range is made |
|---|---|
| Resonance per axis | closed form: belt stiffness and the toolhead term's block stiffness at the low and high ends together (`calibration.design_ranges`) |
| Acceleration an owner would run | 0.4 / 0.5 / 0.65 × the shaper rule at the low / expected / high lower resonance |
| Step-loss ceiling, cross-track RMS and worst | the twin re-run (nominal print and the acceleration sweep) at the soft, lightly damped, long-lag end and at the stiff, well damped, short-lag end (`evals.score_uncertainty`); low and high are the smallest and largest of the three results |
| Benchmark time | none: the ranged parameters do not enter it |

- "Expected" is always the scored value.
- Not varied, because no data gives them a range: friction, the motor torque curve, moving mass, FEA frame stiffness,
  stepper damping.
- The acceleration sweep moves in steps, so a ceiling range is at least one step wide either way.
- The Klipper block's own figures are point values at the expected parameters. The shaper is still tuned on the same
  model it is tested on.
- `--no-ranges` skips the re-runs. Resonance and the owner's acceleration keep their ranges.

`AGENT.md`, `STATUS.md`, `docs/EVALUATION.md` and `docs/FIRMWARE_IN_THE_LOOP.md` use the new names and say what the
ceiling is.

## 4. printer_v4 and printer_v5 re-scored

Both designs were scored twice with `mechloop score <design> --firmware klipper`: once from a copy of the tree taken
before the twin was touched, once with the fitted twin. Same designs, same FEA, same day, same machine. Outputs:
`/tmp/claude-0/-home-user-running-route/87481e0a-8f62-5246-a6fc-1c1f80e15b45/scratchpad/agentF/` (`before/` and
`printer_v4/`, `printer_v5/`; `before_*.json`, `after_*.json`). Nothing was written into `out/printer_v4`, `out/printer_v5`
or `viewer/`.

### Built-in planner (no input shaping, no pressure advance)

| Score | v4 before | v4 after [low, expected, high] | v5 before | v5 after [low, expected, high] |
|---|---|---|---|---|
| X resonance, Hz | 68.4 | 55.4 [49.7, 55.4, 61.2] | 88.5 | 71.6 [64.2, 71.6, 79.1] |
| Y resonance, Hz | 56.9 | 56.9 [52.4, 56.9, 59.1] | 62.0 | 62.0 [57.1, 62.0, 64.3] |
| Step-loss ceiling, mm/s² (was "max clean acceleration") | 8,000 | 8,000 [6,000, 8,000, 12,000] | 10,000 | 12,000 [8,000, 12,000, 14,000] |
| Acceleration an owner would run, mm/s² | not reported | 5,300 [3,400, 5,300, 7,900] | not reported | 6,800 [4,500, 6,800, 9,500] |
| Shaper smoothing rule at the lower resonance, mm/s² | not reported | 10,600 [8,400, 10,600, 12,100] | not reported | 13,500 [11,300, 13,500, 14,600] |
| Cross-track RMS, mm | 0.0150 | 0.0161 [0.0112, 0.0161, 0.0247] | 0.0115 | 0.0129 [0.0092, 0.0129, 0.0187] |
| Cross-track worst, mm | 0.147 | 0.146 [0.108, 0.146, 0.189] | 0.114 | 0.109 [0.084, 0.109, 0.149] |
| Benchmark time, s (with heat-up) | 2,563.5 (3,054.9) | 2,563.5 (3,054.9), no range | 2,563.5 (3,054.9) | 2,563.5 (3,054.9), no range |
| Extruder lag used, s | 0.03 | 0.0315 (direct) | 0.03 | 0.235 (Bowden, 420 mm tube) |
| Toolhead term on X, N/mm | none | 210 (one MGN12H, nozzle 64.5 mm off the rail) | none | 210 (same carriage) |
| Flow-limited speeds | not checked | none (4.9 of 11 mm³/s; 9.8 in the 2x sweep) | not checked | none |

### Real Klipper planning the motion

| Score | v4 before | v4 after | v5 before | v5 after |
|---|---|---|---|---|
| Shaper chosen, X | EI 85.8 Hz (predicted resonance 67.2) | MZV 55.2 Hz (54.9) | EI 108.4 Hz (85.9) | MZV 70.8 Hz (70.6) |
| Shaper chosen, Y | EI 70.8 Hz (55.4) | MZV 55.6 Hz (55.3) | MZV 60.4 Hz (60.0) | MZV 60.4 Hz (59.9) |
| Klipper's suggested max_accel, lower axis, mm/s² | 9,100 | 8,900 | 10,700 | 10,700 |
| Acceleration an owner would run, mm/s² [0.4, 0.5, 0.65 of it] | not reported | 4,400 [3,600, 4,400, 5,800] | not reported | 5,400 [4,300, 5,400, 7,000] |
| Pressure advance in the config, s | 0.03 | 0.0315 | 0.03 | 0.2352 |
| As configured, nominal: cross-track RMS / worst, mm | 0.0045 / 0.042 | 0.0087 / 0.064 | 0.0039 / 0.037 | 0.0083 / 0.047 |
| As configured, nominal: corner bulge, mm | 0.15 | 0.20 | 0.20 | 0.20 |
| As configured: highest clean acceleration in the sweep, mm/s² | 32,000 (Klipper error at 40,000) | 48,000, the highest tried | 48,000, the highest tried | 48,000, the highest tried |
| Shaper and pressure advance off, nominal: RMS / worst, mm | 0.0087 / 0.107 | 0.0098 / 0.101 | 0.0066 / 0.081 | 0.0088 / 0.079 |
| Shaper and pressure advance off, nominal: corner bulge, mm | 0.40 | 0.40 | 0.40 | 0.40 |
| Shaper and pressure advance off: step-loss ceiling, mm/s² | 12,000 | 12,000 | 12,000 | 16,000 |

The Klipper figures are point values at the expected parameters; they were not re-run at the ends of the ranges.

### What moved and what it means

- **X resonance fell on both designs**: 68 to 55 Hz on v4 and 88.5 to 72 Hz on v5. Both carry the nozzle 64.5 mm from
  the rail on one MGN12H block, which the term puts at 210 N/mm, softer than the X belts (261 and 269 N/mm).
- **v4's X axis is now its slower axis**, by a hair (55.4 against 56.9 Hz). Before, Y was the slower axis on both
  designs and X looked comfortably stiff.
- **v5 is still better than v4 on X, and that survives the ranges**: 64 to 79 Hz against 50 to 61 Hz. The gain comes
  from the lighter toolhead, which the fit does not touch. On Y the ranges overlap (57 to 64 against 52 to 59).
- **The other v4-to-v5 differences are inside the ranges.** Cross-track RMS 0.0161 against 0.0129 mm with ranges of
  0.011 to 0.025 and 0.009 to 0.019. Acceleration an owner would run 5,300 against 6,800 mm/s² with ranges of 3,400
  to 7,900 and 4,500 to 9,500. `STATUS.md`'s earlier "cross-track RMS 0.015 to 0.011 mm" is not shown to be an
  improvement.
- **The step-loss ceiling moved up one step on v5** (10,000 to 12,000) although the axis got softer. The Y motor is
  what loses steps, and Y now has more damping; that is the likely cause, not a tested one. One step is not a real
  difference; the range is 8,000 to 14,000.
- **Both designs' own limit of 4,000 mm/s² is inside what an owner would run** on every row (lowest low end: 3,400 for
  v4, built-in planner).
- **Shaping gains less than it appeared to.** With the softer X axis the nominal cross-track RMS with shaper on is
  0.0083 to 0.0087 mm where it was 0.0039 to 0.0045. Most of that is the axis relaxing from its friction lag
  (assumed 2 N over a now softer spring), which no shaper removes. Friction is unfitted, so this floor is as uncertain
  as that assumption.
- **The Bowden lag changed v5 less than expected in these scores.** With pressure advance equal to the lag the corner
  bulge is 0.20 mm, as before. Without it, the built-in planner's test print shows 0.35 mm where it showed 0.30 mm,
  and the printing verifier now warns (`corner_bulge`). The first-order lag model and Klipper's 40 ms smoothing are
  the same as before; only the constant changed.
- **Benchmark time did not move.** Neither design asks its hotend for more than 4.9 mm³/s.

### Verifier outcomes for v4 and v5

`mechloop verify --only ratings fea electrical subsystems printing`, before and after, same two trees.

| | v4 before | v4 after | v5 before | v5 after |
|---|---|---|---|---|
| ratings | pass, 6 warnings | same | pass, 27 warnings | same |
| fea | pass | same | pass | same |
| electrical | pass, 2 warnings | same | pass, 4 warnings | same |
| subsystems | pass | same | FAIL, 2 errors (the probe findings already in `docs/FIRMWARE_IN_THE_LOOP.md`) | same |
| printing | pass | pass | pass | pass, 1 new warning: `corner_bulge` 0.35 mm |

- No verifier changed between pass and fail on either design. The set of findings is identical except for that one
  warning on v5.
- Numbers inside the electrical verifier moved with the hotend model (both designs, 30 W cartridge, to 250 °C):

| | Before | After | Limit |
|---|---|---|---|
| Hotend heat-up, s | 132.8 | 108.8 | 240 |
| Steady duty at 250 °C, still air | 0.44 | 0.38 | — |
| Steady duty at 250 °C, part fan full | not computed | 0.76 | — |
| Power spare for melting, W (needs 2.7) | 16.6 | 7.1 to 7.2 (now taken with the fan at full) | must exceed the need |
| Overshoot, K | 1.9 | 5.1 to 5.2 | 10 |
| Shorted MOSFET: peak, °C / detected after, s | 286 / 31.5 | 292 / 26 | 300 / 60 |

- The melt-capacity margin and the shorted-MOSFET peak are both closer to their limits than they were. The peak is
  8 °C under its limit.
- The other verifiers (geometry, interference, tolerance, manufacture, motion, assemblability, requirements) were not
  re-run. The only changes that reach them are four table entries for materials neither design uses.

## 5. What stays unfitted

| Item | State | What would settle it |
|---|---|---|
| Belt stiffness (EA) | 22 kN per 6 mm kept; range 15 to 27 kN from the blind test; width scaling to 9 and 12 mm untested | the GT2 tensile paper (blocked host), or a resonance from a machine with 9 or 12 mm belts and known masses |
| Guide-block stiffness itself | `ratings.BLOCK_K` 40 N/µm, assumed; the toolhead term's 10 N/µm is an effective figure that includes printed mounts | Hiwin's rigidity table, or a push test on a toolhead |
| Toolhead term on other layouts | fitted to two single-block rail machines; two-block and wheeled carriages extrapolated by the formula | a resonance from a machine with two blocks on the toolhead axis and known geometry |
| Friction | 2 / 3 / 5 N assumed | measured rail friction under printer loads |
| Step-loss boundary | from the torque curve and the stepper model; untested | a controlled test naming motor, current, voltage and mass |
| Stepper damping, mid-band resonance | assumed 0.25; not modelled | accelerometer time traces |
| Frame and joint stiffness | the design's FEA, bonded and screw-only bracket | a modal test of a frame |
| Hotend fast dynamics | sensor lag adjusted to a relay period, not fitted; still fast | a log sampled at 10 Hz or faster with a relay test on the same hotend |
| Hotend totals for the V6 and Revo classes | Prusa's constants, not checked against a log of either | one heat-and-cool log of each with duty recorded |
| Bed thermal | plate capacity from the CAD, bond conductance and sensor lag assumed; only the relay period checked | a bed heat-up log with power |
| Extruder lag non-linearity, Bowden length scaling | one constant per drive and nozzle; length scaling assumed | pressure-advance values with tube length stated |
| Melt-rate onset | a hard cap; no under-extrusion below it | flow-test curves per hotend |
| Warp, cooling, sag, adhesion | not in the twin | NIST AM-Bench (blocked host) |
| Evaluation study | `docs/EVALUATION.md` (on `designs/printer.py`) was not re-run with the fitted twin; its tables are the unfitted twin's | a re-run of `evaluate_printer.py` |

## 6. Limits of this work

- The toolhead term was chosen and fitted after seeing the measurements it is compared with. Only the leave-one-out
  figures are a test, and they rest on two machines.
- Every fit rests on other people's machines: Vorons for damping, Prusa machines for extrusion, one Ender 3 for the
  hotend. Nothing was measured on a machine built from these designs.
- The scorecard ranges cover the parameters that have ranges. They are a lower bound on the uncertainty.
- The FEA nozzle-stiffness case still bonds rail and block.
- Third-party data was parsed as CSV and text only; the fitting scripts were run with `python -I`, except
  `relay_check.py`, which imports the package to run Klipper's autotune class.
