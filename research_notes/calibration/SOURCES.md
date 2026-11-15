# Sources for the twin calibration study

Compiled 2026-11-15. Two passes, in this order: design data (pass 1), freeze and predict, measurements (pass 2).
See `FREEZE.md` for the timestamps, hashes and what had been seen before predicting.

## Pass 1: design data (inputs to the twin)

| What | Source | How used |
|---|---|---|
| Moving masses, belt widths and lengths, kinematics of Voron 0.2r1, Voron Trident 250, Creality Ender 3 | `../trade_study/measurements.json` (STEP assemblies: VoronDesign/Voron-0 `a0d5d1bc`, VoronDesign/Voron-Trident `7fcb3257`, Creality3DPrinting/Ender-3 `88c7758c`) | masses are solid volume x assumed density (CAD estimate), belt length from the belt solid |
| Voron 0.2 stock config (rotation_distance 40, max_accel 2000, max_velocity 200, run-current rule) | https://raw.githubusercontent.com/VoronDesign/Voron-0/Voron0.2r1/Firmware/bigtreetech-skr-mini-e3-v3.0.cfg | read directly |
| Trident stock config (run_current 0.8, max_accel 3000, max_velocity 300) | https://raw.githubusercontent.com/VoronDesign/Voron-Trident/main/Firmware/Octopus/Trident_Octopus_Config.cfg | read directly |
| Ender 3 Klipper example config (rotation_distance 40, max_accel 3000, max_velocity 300) | https://raw.githubusercontent.com/Klipper3d/klipper/master/config/printer-creality-ender3-2018.cfg | read directly |
| Motor constants (R, L, holding torque, rated current, step angle): LDO-35STH52-1504AH, LDO-42STH48-2004AC, Creality 42-34 | https://raw.githubusercontent.com/andrewmcgr/klipper_tmc_autotune/main/motor_database.cfg | community transcription of datasheets; read directly |
| Rotor inertias (20, 82, 38 g cm^2) | class values, assumed | used only by the step-loss simulation, not by the resonance prediction |
| Ender 3 motor current 0.58 A RMS | recalled, low confidence | 14 % of the resonance sensitivity runs through it |

## Pass 2: measurements

Primary data: input-shaper settings that owners saved in public Klipper configs on GitHub.

- Method: GitHub code search (`gh api search/code`) for `shaper_freq_x` with machine words (14 queries, listed in
  `scripts/ghsearch.py`); 998 hits, 910 distinct files fetched from raw.githubusercontent.com as data
  (`scripts/ghfetch.py`); parsed for `[input_shaper]` values, the SAVE_CONFIG block, kinematics, travel,
  `max_accel`, run current and damping ratio (`scripts/ghparse.py`); classified by kinematics, X travel and
  names (`scripts/ghstats.py`); one entry kept per distinct (x, y) frequency pair so forks and copies count once,
  and pairs that are identical round numbers on both axes dropped as template defaults (`scripts/ghsummary.py`).
- Every kept entry with its URL: `measured_configs.json`. Raw search hits: `search_hits.json`.
- Summary used by the twin: `mech-ai/mechloop/twin/calibration_measurements.json`.

| Class | Rule | Configs kept | Of which written by SHAPER_CALIBRATE (accelerometer) |
|---|---|---|---|
| Voron 0 (0.1 and 0.2 share the gantry) | corexy, X travel 115-125, names V0 / Voron 0 | 91 | 48 |
| Trident 250 | corexy, X travel 240-262, names Trident | 11 | 6 |
| Trident 300 / 350 (secondary, not frozen) | as above, 290-312 / 340-362 | 55 / 8 | 31 / 3 |
| Ender 3 / Pro / V2 / Neo | cartesian, X travel 218-252, names Ender, not S1 / Sprite / V3 / other brands | 42 | 17 |
| Ender 3 S1 or Sprite head (side note) | as above with S1 or Sprite | 20 | 9 |

What these numbers are and are not:
- A shaper frequency is the tuner's fit to the measured vibration spectrum; for MZV it sits close to the main
  resonance peak, for EI and multi-hump shapers it can sit 10-20 % above it. All shaper types are pooled.
- Entries typed by hand (not in the SAVE_CONFIG block) may come from an accelerometer run, a ringing-tower
  print, or a copied value. The accelerometer-only subset has the same medians within 1.5 Hz on five of the six
  axes (Ender 3 Y: 50.6 against 45.0).
- Owners modify their machines (toolheads, rails, beds, belts). The spread between configs is the spread of
  real machines of that type, not measurement noise.
- `max_accel` in a config is what the owner runs, with input shaping on; it is not a measured limit. The Ender 3
  median of 3000 is also the example config's default, so it carries little information.

Corroboration from other places (search-engine summaries; the pages themselves could not be opened):
- Klipper Discourse, "Interpreting the Input Shaper Graphs" (klipper.discourse.group/t/9879): a modified Ender 3 with
  a Y peak "around 42 Hz", retested at 48 Hz. Consistent with the Ender 3 Y median of 45 Hz.
- Voron forum thread 1379 (forum.vorondesign.com): Trident 300, X MZV 56.8 Hz. Consistent with the Trident 300
  X median of 58.8 Hz. (This one was already in `../Voron reference data for twin validation.md`, opened after the freeze.)
- Klipper documentation example used to check the smoothing rule: MZV 34.6 Hz -> max_accel <= 3500, ZV 34.4 -> 4500,
  EI 41.4 -> 3200 (https://www.klipper3d.org/Measuring_Resonances.html). The re-implementation in
  `calibration.shaper_accel` gives 3800 / 4500 / 3400.

## Hosts that were blocked by the network policy

klipper.discourse.group, forum.vorondesign.com, ellis3dp.com, forum.prusa3d.com, www.reddit.com, forum.duet3d.com,
wiki.bambulab.com, os.ratrig.com. The GitHub API for individual repositories was also refused (403), so files were
read from raw.githubusercontent.com instead. Reachable: api.github.com (search), raw.githubusercontent.com,
www.klipper3d.org, docs.vorondesign.com.

## Not obtained

- Raw resonance spectra (CSV) for any of the three machines: only the fitted shaper values.
- Any measured dimensional accuracy, ringing amplitude, or controlled maximum-speed / step-loss test.
- Prusa MK3 / MK4 and RatRig V-Core 3: no assembly CAD in the trade-study data, so they could not be
  parameterised from design data alone and were not used.
