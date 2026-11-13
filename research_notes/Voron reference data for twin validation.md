# Voron reference data for twin validation

Compiled 2026-11-13. Target machine: Voron 2.4 (300/350 mm) and Voron Trident, CoreXY, Klipper.

**How to read the source column**

- **Read directly** = I fetched the file itself (raw.githubusercontent.com) and read the value.
- **Search summary** = the host was blocked for direct fetch; the value comes from a web-search result summary and was not checked against the page. Treat as one step weaker.
- **Derived** = my own arithmetic from other rows; not a published number.

Confidence: **High** = official file read directly. **Medium** = datasheet value via a secondary transcription, or a real user's config read directly. **Low** = single forum anecdote, search summary only, or derived.

Hosts that were blocked and would improve this note if allowed: `cdn.shopify.com` (LDO datasheet PDFs), `www.mdpi.com` / `engrxiv.org` (GT2 belt stiffness paper), `reprap.org`, `forum.vorondesign.com`, `docs.vorondesign.com`, `omc-stepperonline.com`.

---

## 1. Kinematics and transmission

| Item | Value | Units | Source | Type | Confidence |
|---|---|---|---|---|---|
| Kinematics | `corexy` | - | [Voron2_Octopus_Config.cfg](https://github.com/VoronDesign/Voron-2/blob/Voron2.4/firmware/klipper_configurations/Octopus/Voron2_Octopus_Config.cfg), [Trident_Octopus_Config.cfg](https://github.com/VoronDesign/Voron-Trident/blob/main/Firmware/Octopus/Trident_Octopus_Config.cfg) | Official config, read directly | High |
| A/B `rotation_distance` | 40 | mm/rev | same files | Official config, read directly | High |
| Implied pulley | 20 tooth x 2 mm pitch | - | Derived from rotation_distance 40; consistent with retailer kit lists "GT2 20T pulley, 5 mm bore, 9 mm wide" | Derived + search summary | High |
| A/B belt | Gates 2GT (GT2), 2 mm pitch, 9 mm wide, open length ("LL-2GT-9") | - | Retailer motion-kit listings (west3d.com) | Search summary | Medium (official BOM file not read; 9 mm for V2.4/Trident A/B is not in doubt in the community) |
| A/B microsteps | 32 | - | official configs | Read directly | High |
| A/B full steps/rev | 200 (comment: "set to 400 for 0.9 degree stepper") | - | official configs | Read directly | High |
| Resolution | 160 microsteps/mm; 0.2 mm per full step | - | Derived | Derived | High |
| A/B `run_current` (stock) | 0.8 | A RMS | official configs (TMC2209, `sense_resistor: 0.110`) | Read directly | High |
| `interpolate` | false | - | official configs | Read directly | High |
| `stealthchop_threshold` | 0 (i.e. spreadCycle) | - | official configs | Read directly | High |
| Z (V2.4) | belt, `rotation_distance: 40`, `gear_ratio: 80:16`, 32 microsteps, 0.8 A | - | V2.4 official config | Read directly | High |
| Z (Trident) | leadscrew, `rotation_distance` 8 (TR8x8) / 4 / 2, 0.6 A | - | Trident official config | Read directly | High |
| Extruder (stock config) | `rotation_distance: 22.6789511`, `gear_ratio: 50:10`, 32 microsteps, 0.5 A | - | official configs | Read directly | High |
| BOM A/B motor | StepperOnline (OMC) **17HS19-2004S1** | - | Voron forum posts quoting the BOM; west3d calls the OMC 17HS19-2004S1-H kit "BOM spec"; Ellis' guide refers to "the OMC motors from the sourcing guide" ([my_setup.md](https://github.com/AndrewEllis93/Print-Tuning-Guide/blob/main/articles/my_setup.md), read directly) | Search summary + read directly | Medium (official BOM file itself not read) |
| LDO kit motors (V2.4 kit Rev C/D) | A/B: LDO-42STH40-2004MAH(VRN), **0.9 deg**; Z: 4x LDO-42STH48-2004AC(VRN), 1.8 deg | - | Retailer listings; LDO kit configs set `full_steps_per_rotation:400` for X/Y ([LDOVoron2 Firmware](https://github.com/MotorDynamicsLab/LDOVoron2/tree/main/Firmware), read directly) | Search summary + read directly | Medium |
| LDO-42STH48-2504AC | Sold "for Voron 2.4" as an upgrade A/B motor; **not** found in the official BOM or the LDO kit lists | - | Retailer listings | Search summary | Medium |

Note on the motor question in the brief: the LDO-42STH48-2004AC is the LDO equivalent of the BOM OMC motor (same 59 N·cm / 2 A class) but in LDO's own kit it is the **Z** motor; LDO ships a 0.9 degree motor for A/B. A "stock" twin should pick one explicitly: BOM self-sourced = OMC 17HS19-2004S1 (1.8 deg); LDO kit = 42STH40-2004MAH (0.9 deg).

## 2. Motor datasheet values

| Motor | Step | Rated I (A/phase) | R (ohm) | L (mH) | Holding torque (N·m) | Rotor inertia (g·cm²) | Source | Type | Confidence |
|---|---|---|---|---|---|---|---|---|---|
| OMC 17HS19-2004S1 (BOM A/B) | 1.8 deg | 2.0 | 1.4 | 3.0 (±20 % at 1 kHz) | 0.59 | not confirmed (see below) | [klipper_tmc_autotune motor_database.cfg](https://github.com/andrewmcgr/klipper_tmc_autotune/blob/main/motor_database.cfg) (read directly); StepperOnline listing | Community transcription of datasheet + search summary | Medium-High |
| LDO-42STH48-2004AC | 1.8 deg | 2.0 | 1.6 | 3.0 | 0.59 | **85** (detent torque 20 mN·m, mass 0.35 kg) | motor_database.cfg (R, L, T; read directly); LDO datasheet Rev A (inertia, detent, mass) | Transcription + search summary of datasheet | Medium-High |
| LDO-42STH48-2504AC | 1.8 deg | 2.5 | 1.2 | 1.5 | 0.55 | not found | motor_database.cfg (read directly); retailers confirm 2.5 A / 55 N·cm | Transcription + search summary | Medium |
| LDO-42STH40-2004MAH (LDO kit A/B) | 0.9 deg | 2.0 | 1.1 | 2.8 | 0.35 | not found | motor_database.cfg (read directly) | Transcription | Medium |
| LDO-42STH48-2004MAH | 0.9 deg | 2.0 | 1.4 | 2.0 | 0.44 | not found | motor_database.cfg (read directly) | Transcription | Medium |

- Rotor inertia for the OMC 17HS19-2004S1: the commonly quoted figure is 82 g·cm², but the search could not confirm it from the datasheet text. Use 82-85 g·cm² (the LDO equivalent's 85 is confirmed) and flag it as assumed.
- **Torque-speed curves: none obtained.** StepperOnline's listing says a curve exists for the 17HS19-2004S1 but no data points could be retrieved; the LDO datasheets seen in search do not include curves. No (rpm, torque) points at 24 V or 48 V are in this note.
- Derived, for orientation only (not published): at stock 0.8 A RMS (1.13 A peak) the low-speed torque is roughly 0.24 N·m (taking torque constant = 0.59 / (√2 x 2 A)), up to 0.33 N·m if you scale holding torque linearly with peak current. With r = 6.37 mm that is about 37-52 N of belt force per motor. Rotor inertia 85 g·cm² reflected at the belt is about 0.21 kg per motor.

## 3. Moving masses

| Item | Value | Units | Source | Type | Confidence |
|---|---|---|---|---|---|
| Stealthburner + Clockwork 2 complete (wires, screws, LEDs) | 433 | g | TeamFDM forum thread "Voron Stealthburner / Clockwork 2 weight" (teamfdm.com/forums/topic/160-...) | One user's scale measurement, search summary | Low-Medium (single report; hotend type not captured) |
| Mini Stealthburner | < 260 | g | TeamFDM file listing | Designer's claim, search summary | Low |
| V2.4 350 gantry, stock | ~1350 (drops to ~950 with a carbon X tube, of which ~150 g is the tube and ~70 g the X drag chain) | g | [woki-leo/carbonfiber-x-axis](https://github.com/woki-leo/carbonfiber-x-axis) README | One mod author's figure, search summary | Low (what "gantry" includes is not defined in the summary) |
| Generic per-length masses | 2020 extrusion ~500 g/m; MGN12 rail ~380 g/m | g/m | forum post | Hearsay, search summary | Low |
| Motor mass (LDO-42STH48-2004AC) | 0.35 | kg | LDO datasheet | Search summary of datasheet | Medium (motors are frame-mounted, not moving, on V2.4/Trident A/B) |

No official Voron mass budget exists that I could find. Afterburner mass, X-carriage-only mass, and a clean "total moved in Y" breakdown were not found. A working assumption consistent with the above: X moving mass 0.45-0.6 kg (toolhead + carriage + belt/chain share); Y moving mass 1.3-1.6 kg for a 350 (X beam + rail + XY joints + toolhead). These brackets are my inference, not a source.

## 4. Stock firmware limits (official Klipper configs)

| Parameter | Value | Units | Source | Type | Confidence |
|---|---|---|---|---|---|
| `max_velocity` | 300 | mm/s | V2.4 Octopus, V2.4 Spider, Trident Octopus configs | Official, read directly | High |
| `max_accel` | 3000 (comment "#Max 4000") | mm/s² | same | Official, read directly | High |
| `square_corner_velocity` | 5.0 | mm/s | same | Official, read directly | High |
| `max_z_velocity` | 15 (comment: max 15 for 12 V TMC, can increase for 24 V) | mm/s | same | Official, read directly | High |
| `max_z_accel` | 350 | mm/s² | same | Official, read directly | High |
| `homing_speed` X/Y | 25 (comment "Max 100") | mm/s | same | Official, read directly | High |
| `pressure_advance` (commented suggestion) | 0.05; smooth time 0.040 "leave stock" | s | same | Official, read directly | High |
| LDO kit Rev C config | identical: 300 / 3000 / 5.0 / 15 / 350, 0.8 A | - | [octopus-printer-rev-c.cfg](https://github.com/MotorDynamicsLab/LDOVoron2/blob/main/Firmware/octopus-printer-rev-c.cfg) | Kit vendor, read directly | High |
| LDO kit Rev D config | `max_accel: 10000`, `max_velocity: 300`, 0.8 A on TMC5160 (sense 0.075), 0.9 deg A/B | - | [leviathan-printer-rev-d.cfg](https://github.com/MotorDynamicsLab/LDOVoron2/blob/main/Firmware/leviathan-printer-rev-d.cfg) | Kit vendor, read directly | High |
| Old Klipper example (V2 250, 16 microsteps) | 350 / 3000 | mm/s, mm/s² | [kit-voron2-250mm.cfg](https://github.com/Klipper3d/klipper/blob/master/config/kit-voron2-250mm.cfg) | Klipper repo, read directly | High |

## 5. Measured resonance frequencies (Klipper input shaper)

| Machine | X | Y | Suggested / used accel | Source | Type | Confidence |
|---|---|---|---|---|---|---|
| V2.4 350 (zellneralex; 0.875 A A/B) | MZV 61.4 Hz | MZV 43.4 Hz | runs `max_accel: 7000`, `max_velocity: 450` | [input_shaper.cfg](https://github.com/zellneralex/klipper_config/blob/master/input_shaper.cfg), printer.cfg, tmc.cfg | Real user config, read directly | Medium |
| V2.4 350 (Ellis; Stealthburner, Orbiter, single MGN9 X rail, no drag chains) | MZV 61.2 Hz (earlier comment 58.6) | EI 49.8 Hz (earlier comment 40.2) | runs `max_accel: 20000`, `max_velocity: 650`, SCV 8 | [printer.cfg](https://github.com/AndrewEllis93/v2.247_backup_klipper_config/blob/master/printer.cfg) | Real user config, read directly; **modded, not stock** | Medium |
| V2.4 R2 350, Stealthburner + CW2 + Tap | ZV 54.0 Hz | EI 38.6 Hz | ringing still visible at 5000 mm/s² | forum.vorondesign.com thread 1293 | Forum report, search summary | Low-Medium |
| V2.4 350 StealthChanger (toolchanger) | MZV 62.2 Hz | MZV 44.0 Hz; "typical" X 55-70, Y 40-55 | - | third-party guide on glama.ai | Unofficial doc, search summary | Low |
| V2.4 "normal" | "early 60 Hz" | "late 40s Hz" | - | Duet3D forum reply | Hearsay, search summary | Low |
| Trident 300, Stealthburner | MZV 56.8 Hz | not captured ("X a bit higher than Y") | - | forum.vorondesign.com thread 1379 | Forum report, search summary | Low |
| V2.4 350 | - | - | shaper-suggested accel "x > 10,000 and y >= 5000" | forum.vorondesign.com thread 772 | Forum report, search summary | Low |
| V2.4 300 | - | - | shaper-suggested accel "nearly 9k on X, 4.5k on Y" | forum.vorondesign.com thread 921 | Forum report, search summary | Low |

Klipper's own documentation gives no Voron figures. Its example output ([Measuring_Resonances.md](https://github.com/Klipper3d/klipper/blob/master/docs/Measuring_Resonances.md), read directly) is `mzv @ 34.6 Hz -> suggested max_accel <= 3500`, `zv 34.4 Hz -> 4500`, `ei 41.4 Hz -> 3200`. Scaling the MZV limit with f² (derived) gives about 11,000 mm/s² at 61 Hz and 5,500 mm/s² at 43 Hz, which matches the two forum reports above. Klipper also states default `accel_per_hz: 75` for the resonance test and warns against raising `square_corner_velocity` above 5.

Related official number: Voron belt tensioning asks for the A/B belts to ring at **~110 Hz on a 150 mm free span**, stated as "roughly 2 lb of belt tension" (about 9 N); Z belts 140 Hz ([secondary_printer_tuning.md](https://github.com/VoronDesign/Voron-Documentation/blob/main/tuning/secondary_printer_tuning.md), read directly, High). Note 110 Hz / 150 mm / 8.9 N implies a belt linear density of about 8 g/m; a tensioning blog quotes 8.3 g/m for *6 mm* GT2, so for a 9 mm belt the true tension at 110 Hz is probably nearer 13 N. Use 9-13 N as the static pretension bracket.

## 6. Demonstrated limits (step loss, speed tests)

| Claim | Value | Source | Type | Confidence |
|---|---|---|---|---|
| Ellis, 2 A 1.8 deg OMC motors, V2.4 350, 24 V | top speed "closer to 800-1000 mm/s" | [determining_max_speeds_accels.md](https://github.com/AndrewEllis93/Print-Tuning-Guide/blob/main/articles/determining_max_speeds_accels.md) | Experienced user's own measurement, read directly | Medium |
| Ellis, 2 A 0.9 deg LDO motors | "top out around 450 mm/s" | same | same | Medium |
| Ellis' saved config (after ~15 % margin) | 650 mm/s, 20,000 mm/s² at `run_current: 1.4` A, 128 microsteps, TMC2209 | printer.cfg linked above | Read directly; which motor set this snapshot belongs to is ambiguous (config says 200 steps, setup page says 0.9 deg LDO) | Medium-Low |
| Ellis' guidance | start at 40-50 % of rated current (0.8-1.0 A for a 2 A motor); never above 70 % (1.4 A); TMC2209 keep <= 1.4 A RMS; back off ~15 % from the TEST_SPEED limit; skip criterion = endstop position changed by more than one full step (32 microsteps) | [determining_motor_currents.md](https://github.com/AndrewEllis93/Print-Tuning-Guide/blob/main/articles/determining_motor_currents.md) and the article above | Read directly | High (as guidance) |
| Ellis' worked example | "300 mm printer, max accel of 3500": 260 mm test span would allow "a bit over 900 mm/s" theoretically | same article | Read directly | High (it is just v = √(a·d)) |
| V2.4 owner, TEST_SPEED | passed at 375 mm/s and 23,000 mm/s² | Voron forum thread | Anecdote, search summary; motors/current unknown | Low |
| V2.4 owner after LDO motor swap | 800 mm/s travel at 10,000 mm/s² | Voron forum | Anecdote, search summary | Low |
| V2.4 owner | step loss above 2,000 mm/s² (an outlier; almost certainly a mechanical or wiring fault) | Voron forum | Anecdote, search summary | Low |
| 1.8 deg motors + TMC2209 + 24 V | "may have issues at speeds closer to 500 mm/s" | Klipper Discourse | Hearsay, search summary | Low |
| zellneralex daily config | 450 mm/s, 7000 mm/s² at 0.875 A | config linked above | Read directly | Medium |

There is no published, controlled "max accel before skipping at stock 0.8 A with the BOM motor" figure. The best-supported statement is: stock limits (300 mm/s, 3000 mm/s²) are far inside the envelope; healthy machines pass TEST_SPEED at 10,000-20,000+ mm/s² with 0.9-1.4 A.

## 7. Belt stiffness (GT2 / 2GT, 2 mm pitch, glass-fibre cord)

**Plain statement: no reliable manufacturer value exists in public for EA of 6 mm or 9 mm 2GT belt.** Gates' public documents do not list tensile modulus for 2MGT and refer the reader to Gates application engineering (search summary). What exists:

| Item | Value | Converted | Source | Type | Confidence |
|---|---|---|---|---|---|
| "Generic Gates-style" fibreglass GT2, 6 mm | 0.0067 %/N | **EA ≈ 15 kN** (1 m of belt ≈ 15 N/mm) | RepRap wiki "Belt Compliance Measurement" (reprap.org/wiki/Belt_Compliance_Measurement) | Hobbyist dial-indicator measurement with ~1 kg load; search summary; the wiki's column header units are inconsistent | Low-Medium |
| Steel-cord 6 mm GT2 (possibly PU) | 0.0024 %/N | EA ≈ 42 kN | same | same | Low |
| 9 mm vs 6 mm GT2 | "+55 % modulus at 9 mm" | **EA(9 mm) ≈ 22-23 kN** (pure width scaling gives 22.4 kN) | ShapeOko wiki "Belts and Pulleys" | Secondary, no stated method; search summary; conversion derived | Low |
| GT-2 rubber-fibreglass tensile tests to rupture, 400 mm and 760 mm samples, 3 repeats | Stiffness is **non-linear (hyperelastic), no constant-stiffness region**; cubic fit R² > 0.999, linear fit R² > 0.94 | numbers not retrieved | Wang, Si, Chadha, Allison, Patterson, *Robotics* 7(4):75 (2018), [doi:10.3390/robotics7040075](https://doi.org/10.3390/robotics7040075); preprint on engrXiv | Peer-reviewed; abstract-level search summary only (host blocked) | High for the qualitative finding; fit coefficients **not obtained** |
| Breaking strength | 86 N per mm width (≈ 516 N for 6 mm) | - | supplier datasheet (ondrivesus.com) | Search summary | Low |
| Belt linear density, 6 mm GT2 | 8.3 g/m | - | tensioning blog | Search summary | Low |

Recommended use: EA = 15 kN (6 mm) and 22 kN (9 mm) as nominal with at least ±30 % uncertainty, and expect stiffening with tension. The single most valuable follow-up is to read Table 1 of the Robotics paper (open access) for the fitted coefficients.

## 8. Print-quality figures

| Item | Value | Source | Type | Confidence |
|---|---|---|---|---|
| Pressure advance, Klipper "typical" | 0.050 - 1.000 s, high end only for bowden | [Pressure_Advance.md](https://github.com/Klipper3d/klipper/blob/master/docs/Pressure_Advance.md) | Official doc, read directly | High |
| PA, Voron stock config suggestion | 0.05 s, smooth time 0.040 s | official configs | Read directly | High |
| PA, Ellis' machine (Orbiter 1.5 + Rapido UHF, direct drive) | 0.048 s, smooth time 0.02 s | his printer.cfg | Read directly | Medium |
| PA, Ellis' guide example pick | ~0.04 s; direct-drive tuning tower step 0.0025/mm vs bowden 0.025/mm (i.e. direct drive lives roughly in 0.02-0.08) | [pattern_method.md](https://github.com/AndrewEllis93/Print-Tuning-Guide/blob/main/articles/pressure_linear_advance/pattern_method.md), tower_method.md | Read directly | Medium |
| PA, Stealthburner + Revo Micro + LGX Lite (Duet firmware) | 0.08-0.09 s | Duet forum | Anecdote, search summary | Low |
| Residual vibration after shaping | Klipper shapers are designed to cut vibration to 5 % (EI family) within their band; example fits report 0-5 % remaining | [Resonance_Compensation.md](https://github.com/Klipper3d/klipper/blob/master/docs/Resonance_Compensation.md), Measuring_Resonances.md | Official doc, read directly; this is a model prediction, not a measured print amplitude | Medium |
| Ringing frequency from a print | f = V·N/D; doc example 100 mm/s, 6 waves in 12.14 mm -> 49.4 Hz | Resonance_Compensation.md | Official doc, read directly | High (method) |
| Dimensional accuracy | No official Voron claim found. One forum user: "Z less than 0.1 mm off" | Voron forum | Anecdote, search summary | Low |

## 9. Secondary machines (only what was read or is clearly official)

| Item | Value | Source | Type | Confidence |
|---|---|---|---|---|
| Prusa MK4 default max feedrate X/Y/Z/E | 400 / 400 / 40 / 50 mm/s (hardware limits, normal mode: 300 / 300 / 40 / 100) | [Configuration_MK4.h](https://github.com/prusa3d/Prusa-Firmware-Buddy/blob/master/include/marlin/Configuration_MK4.h) | Official firmware, read directly | High |
| Prusa MK4 default max accel X/Y/Z/E | 1250 / 1250 / 200 / 1500 mm/s² (hardware limit normal mode 7000 / 7000 / 750 / 6000; stealth 2500) | same | Read directly | High |
| Prusa MK4 default print/travel accel | 1250 / 1250 mm/s²; junction deviation 0.01 mm | same | Read directly | High |
| Prusa MK4 steps/mm, microsteps | X/Y 100 steps/mm; 16 microsteps (200-step) or 8 (400-step), interpolated to 256 | Configuration_MK4.h, Configuration_MK4_adv.h | Read directly | High |
| Bambu Lab X1 | Not researched to a citable standard in this session (official spec page blocked). | - | - | none |

---

## Numbers a simulation should be able to reproduce

1. **Step geometry:** 40 mm per motor rev, 0.2 mm per full step, 160 microsteps/mm; 300 mm/s = 450 rpm = 1500 full steps/s. (Exact.)
2. **No step loss at stock limits:** 300 mm/s and 3000 mm/s² at 0.8 A RMS, 24 V, BOM 1.8 deg 59 N·cm motors, with large margin. If the twin skips anywhere near this, the twin is wrong. (High confidence.)
3. **Step-loss threshold well above stock:** with 0.9-1.4 A the twin should pass a TEST_SPEED-style pattern at 10,000 mm/s² and plausibly up to about 20,000 mm/s²; a threshold below ~7,000 or above ~40,000 mm/s² at 1.0-1.4 A would be outside every report found. At exactly 0.8 A there is no measured figure; treat anything in 8,000-25,000 mm/s² as unfalsified. (Low-Medium.)
4. **Top speed before torque collapse (1.8 deg, 2 A, 24 V, 1.2-1.4 A):** somewhere in 500-1000 mm/s with light acceleration; 0.9 deg motors roughly half that (~450 mm/s). (Medium, single experienced source plus hearsay.)
5. **X resonance (toolhead on belts), 350 mm V2.4 with Stealthburner:** 54-62 Hz, centre ~60 Hz. (Medium: two configs read directly plus three weaker reports.)
6. **Y resonance, 350 mm V2.4:** 38-50 Hz, centre ~43 Hz; Y is always lower than X by roughly 25-35 %. (Medium.) A Trident 300 should come out similar or slightly higher on X (one report: 56.8 Hz).
7. **Shaper-limited acceleration:** MZV at the measured frequencies gives suggested `max_accel` of roughly 9,000-11,000 mm/s² on X and 4,500-5,500 mm/s² on Y (Klipper's smoothing criterion scales as f²; anchor: 34.6 Hz -> 3,500). (Medium.)
8. **Belt span check:** a 150 mm free span of A/B belt at nominal pretension (9-13 N) should have a first transverse mode at ~110 Hz. (High for the 110 Hz target; Medium for the tension.)
9. **Belt-plus-mass consistency:** with EA(9 mm) ≈ 22 kN ±30 % and the mass brackets in section 3, the twin's X and Y modes should land in the bands of items 5-6 without tuning anything else. If they do not, the first suspects are belt EA (weakest input) and frame/gantry compliance, not the masses.
10. **Extruder lag:** an equivalent pressure-advance constant of 0.03-0.06 s for a direct-drive Stealthburner-class toolhead (0.02-0.09 s outer bracket). (Medium.)
11. **Residual ringing with a correctly tuned shaper:** <= 5 % of unshaped amplitude at the shaper frequency (design target, not a print measurement). (Medium.)

## What could not be found

- Any **torque-speed curve** ((rpm, torque) points) for the OMC 17HS19-2004S1, LDO-42STH48-2004AC or -2504AC at 24 V or 48 V.
- **Rotor inertia** for the OMC 17HS19-2004S1, LDO-42STH48-2504AC and the 0.9 deg LDO motors (only the LDO-42STH48-2004AC's 85 g·cm² was confirmed).
- The **official Voron BOM file** itself (motor part number, belt part number and lengths come from retailer listings and forum quotes; github.com directory listings and vorondesign.com were not readable).
- An **official or itemised mass budget**: Afterburner mass, X carriage alone, X beam + rail alone, total Y moving mass. Only one Stealthburner weighing (433 g) and one loosely defined gantry figure (~1350 g) exist here.
- **Belt EA from Gates** or any manufacturer for 2GT 6 mm / 9 mm, and the numeric fit coefficients from the Robotics 2018 GT-2 paper. No belt damping data at all.
- A controlled **"max accel before skipping at stock 0.8 A"** measurement naming motor, current and voltage together.
- **Measured ringing amplitude** (in mm or µm) before/after input shaping on a Voron, and any measured damping ratio (Klipper assumes 0.1 by default).
- An official or systematically measured **dimensional accuracy** figure for Voron printers.
- A complete Trident input-shaper result (X and Y together) and any 300 mm V2.4 frequency pair.
- Verified Bambu Lab X1 official specs (not fetched).
