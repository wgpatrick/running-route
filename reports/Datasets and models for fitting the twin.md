# Datasets and models for fitting the twin

Research pass of 2026-11-15. Scope: everything the digital twin (`mech-ai/mechloop/twin`, heater model in
`mech-ai/mechloop/electrical.py`) could be fitted to or checked against, except the blind resonance-frequency
comparison for three machines, which is in `Twin calibration study.md`.

## Answer in brief

- **There is no public input-output data set for a desktop printer's motion** (commanded motion together with measured
  nozzle or carriage position). Every motion source found is either a spectrum without the machine's masses and belt
  lengths, a vibration recording without the commanded motion, or a paper with fitted transfer functions and plots but
  no files. Belt stiffness and step-loss limits therefore still cannot be fitted from public data alone.
- **Three things can be fitted now from data that is downloaded and checked**: the damping ratio of the ringing mode
  (195 resonance tests from 58 machines), the hotend thermal model (nine logged runs with heater duty, plus four
  independent sets of fitted constants in firmware), and the extruder lag (factory pressure-advance values per nozzle
  and extruder type).
- **The first look says the twin is under-damped.** Median damping ratio of the main peak is 0.08 on X and 0.12 on Y
  across the corpus, against about 0.02 to 0.05 from the twin's two dampers and 0.05 proposed in the calibration study.
  The method used here reads high by perhaps 0.02 (see item 1), so 0.06 to 0.10 is the defensible range.
- **The single most valuable item that could not be fetched** is the only published tensile test of GT2 belt (Wang et
  al., *Robotics* 2018, CC BY). It would replace the assumed 22 kN per 6 mm. The host is blocked here.
- 46 MB was downloaded into `mech-ai/research_notes/datasets/` (the task said `research_notes/datasets/`; the tree's
  other research notes are one level up, but a checkpoint commit by another agent had already picked the files up at
  this path, so they stay there).

### Network limits of this session

Reachable: `raw.githubusercontent.com`, the GitHub search API, `huggingface.co`, `arxiv.org` (by curl only),
`klipper3d.org`, `reprap.org`, `e3d-online.com`, `omc-stepperonline.com`, `docs.vorondesign.com`, `s3.amazonaws.com`.

Blocked by the sandbox policy (fetch by hand): `zenodo.org`, `kaggle.com`, `figshare.com`, `data.mendeley.com`,
`ieee-dataport.org`, `data.nist.gov`, `nist.gov`, `mdpi.com`, `mdpi-res.com`, `sciencedirect.com`,
`link.springer.com`, `researchgate.net`, `par.nsf.gov`, `pmc.ncbi.nlm.nih.gov`, `duet3d.com`, `ellis3dp.com`,
`cnckitchen.com`, `wiki.bambulab.com`, `engrxiv.org`, `ntnuopen.ntnu.no`, `thk.com`, `hiwin.co.uk`, `osf.io`,
`archive.org`. `gates.com` answers 403 itself. For everything on those hosts this report relies on search-engine
summaries, and says so item by item.

Status words used below: **downloaded** (file is in `research_notes/datasets/` and was parsed), **read** (fetched to
a scratch directory, text read, not kept), **seen** (page or README fetched, files not), **described** (search
summary only; existence of downloadable files not confirmed).

## Ranked table

Value is for fitting or checking this twin, not general interest. Effort is to first usable number.

| # | Item | Fits or checks | Status | Licence | Effort |
|---|---|---|---|---|---|
| 1 | Klipper resonance-test spectra, 274 files, 62 repositories | ringing damping ratio; number and spacing of modes; A/B belt asymmetry | downloaded (98 files), rest indexed | per repository, MIT / Apache / CC0 / GPL for stored ones | done for damping; 1 day to add masses from each `printer.cfg` |
| 2 | Ender 3 hotend logs and fitted 3-node model (batu63562) | hotend heat capacity, loss, fan cooling, sensor lag, heat taken by filament | downloaded, fitted | GPL-3.0 | half a day |
| 3 | Heater constants committed to firmware: Prusa thermal model, Marlin MPC, Klipper and Marlin PID sets | hotend and bed model across many machines (relay-test period and gain) | downloaded, tabulated | GPL-3.0 | half a day |
| 4 | Factory pressure-advance values (PrusaSlicer profiles, Klipper docs, Duet research posts) | extruder lag per extruder type and nozzle | downloaded (Prusa, Klipper); Duet described | AGPL / GPL | 2 hours |
| 5 | Wang et al. 2018, tensile tests of GT2 rubber-fibreglass belt | belt EA per mm width, and its non-linearity | described; host blocked | CC BY 4.0 | 1 hour once fetched |
| 6 | Okwudire group papers (Taz 6, Ender 3 Pro, Ender 5 H-frame, delta) | shape of the axis frequency response, amplitude dependence, racking | read (arXiv) | arXiv non-exclusive; no data files | 1 day to digitise or re-create from printed transfer functions |
| 7 | Volumetric flow limits: 2,107 Bambu filament profiles, 1,025 Prusa entries, Ellis hotend table | melt-rate limit per hotend and material (the twin has none) | downloaded | AGPL / unstated | 2 hours |
| 8 | Zenodo "Printer-bed dataset" (Prusa MK3S bed, high-speed camera and accelerometer modal test) | bed (Y axis) modes and damping of a bed-slinger | described; host blocked | not confirmed | half a day once fetched |
| 9 | Belt pluck recordings and per-belt sweeps (HelixScreen fixtures) | belt tension from pluck frequency; A/B path difference | downloaded | GPL-3.0 | done |
| 10 | NIST AM-Bench 2022 AMB2022-06 (polycarbonate and PLA extrusion) | extrudate temperature, rheology; later a cooling and warp model | described; host blocked | US government work, public | 1 to 2 days |
| 11 | Zenodo Ender 3 V2 ADXL345 set, 3200 Hz, 40 h, six states | vibration spectrum while printing, loose-carriage fault signature | described; host blocked | not confirmed | 1 day |
| 12 | ARTS Lab Ender 5 Plus lifecycle vibration, 15 recordings | spectrum while printing at hotend, feeder and frame; drift with wear | downloaded (1 of 15 raw, all features) | CC BY-SA 4.0 | 1 day, low yield |
| 13 | Nozzle pressure and feed-force papers (arXiv 2310.01901; Kazmer, Coogan, Colon; Tronvoll; Go and Hart; Serdeczny) | pressure against flow and temperature; start/stop time constant; force limit of the feeder | 2310.01901 read; rest described | mixed; no data files confirmed | 1 to 2 days of digitising |
| 14 | Kickstarter x Autodesk FDM assessment protocol | an outside scoring rule for the twin's printed-part output | seen (protocol text) | not stated | 1 day to script |
| 15 | Weiss 2014 thesis, closed-loop 3D printer gantry with linear encoders | open-loop tracking error of a belt axis measured at the carriage | read | thesis, no licence | half a day of digitising |
| 16 | Monkeyfab delta anomaly set (joanna-/3D-Printing-Data) | bed and head acceleration with firmware position and temperatures, including faults | seen (README) | CC BY 4.0 | 1 day; delta kinematics, low yield |
| 17 | Mass Portal thesis measurements (Univ. of Tartu) | bed heat-up energy logs to 60 and 110 C; resonance spectra | read | none stated | 2 hours |
| 18 | Hiwin MG rigidity, stepper torque curves | guide block stiffness; motor torque against speed | Hiwin 2025 US catalogue read (no rigidity table); StepperOnline curve PDFs reachable | vendor | half a day |
| 19 | Dimensional and warp studies (NIST artifact data-in-brief, fleet ringing study arXiv 2506.12252, warp papers) | tolerance and warp rules of thumb | described | mixed | low yield |

## Items

### 1. Klipper resonance-test spectra from public config repositories

- **What.** Owners of Klipper printers often commit the CSV that `TEST_RESONANCES` writes. Each is the power spectral
  density of toolhead acceleration against frequency during a swept excitation of one axis: columns
  `freq, psd_x, psd_y, psd_z, psd_xyz`, 0 to 133 or 200 Hz, about 1.5 Hz bins, 130 lines. Found by GitHub code search
  on the file names and on the header string.
- **Size.** 289 files found, 274 parsed, 62 repositories; 2 MB in all. 226 are toolhead X or Y tests, 36 are per-belt
  diagonal sweeps, 12 other. Mostly Voron 2.4, Trident and V0; also Ender 3, Sovol SV01, Prusa Bear, Creality K1,
  FlashForge AD5M, Snapmaker U1, Tronxy X5SA.
- **Licence.** 16 repositories carry MIT, Apache-2.0, CC0 or GPL-3.0 (98 files, stored). 46 have no licence file; their
  files were read in scratch and only the URL, peak and damping are kept in
  `klipper_resonance_psd_corpus/corpus_index_and_peaks.csv`.
- **Raw time series are not there.** The `raw_data_*.csv` files Klipper also writes are a few megabytes each and no
  public copy turned up in code search (it only indexes small files).
- **Maps to.** `damping_ratio` and `spring_damping_ratio` (through `calibration.modal_damping`), and the proposed
  `ringing_damping_ratio`. With masses and belt lengths from each repository's `printer.cfg` and the Voron bill of
  materials, the same files extend the other agent's three-machine frequency check to dozens of machines.
- **First look** (`_first_look/psd_corpus_damping.png`). Half-power width of the largest peak between 15 and 135 Hz,
  files whose peak is at least 5 times the band median:

  | Axis | Files | Peak frequency, 10th / median / 90th percentile (Hz) | Damping ratio, 10th / median / 90th |
  |---|---|---|---|
  | X | 94 | 42 / 60 / 127 | 0.058 / 0.083 / 0.129 |
  | Y | 101 | 32 / 41 / 58 | 0.068 / 0.115 / 0.205 |

  CoreXY machines alone: X 58 Hz and 0.082 (67 files), Y 42 Hz and 0.109 (69 files).
- **Limits.** Several files per machine, so these are not 195 independent machines. The half-power method on 1.5 Hz
  bins cannot return less than about 0.02 to 0.03 and reads high when two modes sit close together, which is common on
  Y. Machine class is guessed from the repository name. The owner-entered values in the calibration study (0.03 to
  0.09, median 0.05 to 0.07) come from a narrower fit and sit lower; the two together bracket the truth.

### 2. Ender 3 hotend logs and fitted model

- **URL.** https://github.com/batu63562/ender3-hotend-twin (GPL-3.0).
- **What.** One Ender 3 with a V6-style all-metal hotend, 40 W cartridge, Klipper. Nine runs in `benchmark/`: full-power
  heat-up, holds at 150, 180, 220 and 245 C, part-fan steps, free cool-down, one print. Columns are time, thermistor
  temperature, heater duty, fan state, extruder velocity. 1.6 MB, 3 to 4 samples a second. The repository lists about
  115 more logs under `loglar/` that were not fetched.
- **The author's model** is three lumped masses (cartridge, block at the thermistor, nozzle and heat-break), with
  convection plus radiation from the block, a fan term with a 19 % duty threshold and exponent 0.5, heat capacity rising
  0.12 % per kelvin, and a term for heat carried off by filament. Fitted constants are in `calibration.example.json`.
  An earlier two-node fit gave 5.57 J/K, 0.075 W/K in still air and 0.143 W/K with the fan.
- **Maps to.** The hotend `ThermalNet` nodes (capacities, link conductances), `g_ambient`, `sensor_tau_s` in
  `electrical.py`.
- **First look** (`_first_look/hotend_log_fit.png`). Open-loop simulation driven by the logged heater duty on the
  570 s run to 245 C with fan and cool-down:

  | Model | Fitted values | RMSE |
  |---|---|---|
  | one mass | 6.9 J/K, 0.084 W/K still air, +0.023 W/K with fan, time constant 82 s | 6.5 C |
  | two masses | heater 0.2 J/K (at its lower bound), block 6.8 J/K, 0.65 K/W between | 4.8 C |

  Both lag the heat-up by 15 to 25 C, as the author reports for a single mass; the third node is what fixes it. The
  transport lag did not identify in this fit (it stayed at its starting value). The data is usable as it stands.
- **Limit.** One machine. Ambient is assumed 25 C, not logged.

### 3. Heater constants that makers and users fitted and committed to firmware

Downloaded to `firmware_fitted_parameters/`; all GPL-3.0.

- **Prusa MK3 thermal model** (`Prusa-Firmware/Firmware/thermal_model/`). E3D V6: 38 W, block 12.1 J/K, block to
  ambient 20.5 K/W with the fan off falling to 10.1 K/W at full fan in 16 steps, sensor lag 2.1 s. Also Revo and Revo
  HF 60 W. This is a maker's calibration of a named hotend and gives the fan-speed curve directly.
- **Marlin model-predictive control constants** (`MarlinFirmware/Configurations`, 425 files read). Eight distinct sets,
  six machines with it enabled: heater 40 to 60 W, block 6.5 to 16.8 J/K, ambient transfer 0.052 to 0.140 W/K fan off
  and 0.063 to 0.174 W/K fan on, sensor responsiveness 0.10 to 0.35 per second.
- **PID sets** (`derived/klipper_config_pid.csv`, `derived/marlin_config_pid_mpc.csv`). Klipper's autotune is a relay
  test and stores Kp = 0.6 Ku x 255, Ki = 2 Kp / Tu, Kd = Kp Tu / 8, so each set gives back the ultimate period Tu and
  gain Ku of the real heater. The Kd identity holds to 0.1 % in the Klipper files, which confirms where the numbers came
  from. Distinct sets only:

  | Heater | Distinct sets | Tu, 10th / median / 90th (s) | Ku, median (duty per K) |
  |---|---|---|---|
  | Klipper extruders | 81 | 24 / 37 / 55 | 0.16 |
  | Klipper beds | 70 | 20 / 89 / 160 | 0.46 |
  | Marlin hotends | 152 | 16 / 27 / 41 | not derived |

  86 of 226 Klipper extruder entries are the Marlin default 22.2 / 1.08 / 114 copied over, so counts by row would
  mislead. Marlin's bed values are mixed in origin and are not reliable for this.
- **Maps to.** Run the same relay test on the twin's `HeaterPlant` for the hotend and bed and compare Tu and Ku with
  these distributions. It checks dead time and sensor lag together, which a heat-up curve alone does not.
- **Also here.** Prusa's factory input-shaper defaults per printer (MK4 50.7 / 40.6 Hz, MINI 118.2 / 32.8, XL 35.8 /
  35.4, Core One 60 / 48), all with damping ratio 0.1. These are six more resonance points for the other agent's table,
  from the maker.
- **Limit.** Heater power is not in the PID files, so Ku cannot be turned into watts per kelvin without the machine's
  heater rating.

### 4. Pressure-advance values as a measure of extruder lag

- **PrusaSlicer vendor profile** (`slicer_profiles/prusaslicer_profiles/PrusaResearch_2.3.0.ini`, 1.4 MB). Factory
  values per printer, filament and nozzle. Direct-drive Nextruder: 0.03 to 0.058 s at 0.4 mm, 0.018 to 0.039 s at
  0.6 mm, 0.012 to 0.028 s at 0.8 mm, 0.1 to 0.2 s at 0.25 mm. Bowden MINI: 0.23 to 0.24 s at 0.4 mm, 0.14 to 0.15 at
  0.6 mm, 0.72 to 0.75 at 0.25 mm.
- **Klipper documentation** (`community_tables/klipper_docs/Pressure_Advance.md`): typical 0.05 to 1.0 s, the high end
  for Bowden.
- **Duet3D research posts** (described; `duet3d.com` blocked): a spiral-track test found extrusion decaying with a
  half-life of about 0.06 s, a constant of about 0.041 s, and a dependence on extruder jerk.
- **Bambu profiles carry no pressure-advance value**; the machines calibrate it per spool.
- **Maps to.** `extruder_lag_s`. The assumed 30 ms is right for a 0.4 mm nozzle on a short direct-drive path. The data
  shows what the twin lacks: the lag should scale with nozzle size (roughly halving from 0.4 to 0.6 mm) and be about
  eight times longer for the Bowden layout that `printer_v5` uses.
- **Limit.** A pressure-advance constant equals the lag only for a linear compliance; items 13 show it is not.

### 5. Wang et al. 2018, GT2 belt tensile stiffness

- **Citation.** Wang, Si, Chadha, Allison, Patterson, "Nominal Stiffness of GT-2 Rubber-Fiberglass Timing Belts for
  Dynamic System Modeling and Design", *Robotics* 7(4), 75. https://doi.org/10.3390/robotics7040075 (CC BY). Preprint
  at https://engrxiv.org/preprint/view/309/.
- **What (from summaries only).** Two belt lengths, 400 and 760 mm, pulled to rupture three times each on a screw-driven
  stand; six force-extension curves and a regression for nominal stiffness per unit width and length. The authors report
  the compliance as clearly non-linear.
- **Maps to.** `belt_ea_n_per_mm_width`, and a tension-dependent stiffness if the non-linearity is as large as stated.
  The calibration study brackets EA at 15 to 27 kN per 6 mm from resonances; this is the only direct measurement found.
- **Not confirmed.** The numbers, and whether the test was on 6 mm belt. No Gates document giving EA for GT2 was found;
  distributor sheets give breaking strength only (about 86 N per mm of width).

### 6. Okwudire group, University of Michigan

Read from arXiv; plots and fitted models, no data files, no code.

| Paper | Machine | What it gives |
|---|---|---|
| arXiv 2004.06697, servo error pre-compensation and feedrate optimisation | Lulzbot Taz 6 | Sixth-order discrete transfer functions for X and Y at 1 kHz, printed in full (Eq. 15), fitted to swept-sine tests with two ADXL335 measuring nozzle relative to bed. Bandwidth about 30 Hz. Contour error of 54 um judged acceptable. |
| arXiv 2206.11960, physics-guided data-driven feedforward | Creality Ender 3 Pro | X and Y frequency responses at several excitation amplitudes, which differ markedly; fifth-order continuous model printed; effect of 200 g added to the carriage. |
| arXiv 2105.09878, racking of H-frame printers | Ender 5 rebuilt as H-frame | Coupled model in which gantry rotation depends on carriage position; frequency response of racking measured and fitted. |
| arXiv 2209.06791, delta printer | Monoprice Delta Pro | Position-varying dynamics measured at several bed positions. |

- **Maps to.** The Taz 6 transfer functions can be simulated directly and compared with the twin's axis model for a
  machine of that layout; that tests the response shape above the first mode, which a single frequency does not.
- **Related.** Ulendo, the group's company, publishes an OctoPrint calibration plugin (`S2AUlendo/UlendoCaaS`); the
  repository has no data.

### 7. Volumetric flow limits

- **Bambu Studio filament profiles**, 2,107 resolved profiles (`slicer_profiles/bambustudio_filament_derived/`,
  AGPL-3.0). Maximum volumetric speed: PLA median 12 mm3/s (0.5 to 30), PETG 13, ABS 15, PC 18, TPU 3.6, PA-CF 8, with
  nozzle temperature, flow ratio, density and glass-transition temperature per profile and the printers each applies to.
- **PrusaSlicer profile**: 1,025 `filament_max_volumetric_speed` entries.
- **Ellis tuning guide table** (no licence stated): E3D V6 11, Revo 11, Dragon SF 15, Dragon HF 24, Rapido HF 24,
  Rapido UHF 30, Mosquito 20 mm3/s with a 0.4 mm brass nozzle.
- **CNC Kitchen** publishes the test generator (`CNCKitchen/ExtrusionSystemBenchmark`, a spreadsheet with macros, not
  fetched) but no table of results in the repository; results are in videos and on a blocked site.
- **Maps to.** The twin has no melt-rate limit. These give a per-hotend cap and an under-extrusion onset to add to
  `deposit.py`, and a check that a design's hotend and heater power support its commanded speeds.

### 8. Zenodo "Printer-bed dataset"

https://zenodo.org/records/21476609 and https://zenodo.org/records/22770610. Described as high-speed-camera and
accelerometer modal measurements of a suspended Prusa i3 MK3S bed. If the files hold mode frequencies and damping for
the bed assembly, it is the only modal test of a printer part found. Files, size and licence not confirmed.

### 9. HelixScreen belt fixtures

https://github.com/prestonbrown/helixscreen (GPL-3.0), `tests/fixtures/`. Eight raw 0.5 s ring-downs at 3.09 kHz of a
plucked belt on a Voron 2.4 300 with a 151 mm span, stated at 86 Hz (A) and 82 Hz (B); and 36 diagonal sweeps of each
belt path on a Voron 2.4, Creality K1C and K2 Plus, FlashForge AD5M and AD5X, and Snapmaker U1. From T = 4 rho L^2 f^2
with 8.4 g/m, 86 Hz on 151 mm is 5.7 N. The fixture's own note says all pluck files are one machine on one evening. A
naive spectrum peak picks the second harmonic (172.8 Hz) on one file, so use a harmonic-aware estimator
(`_first_look/belt_pluck_spectra.png`). Maps to belt tension, which the twin does not yet model.

### 10. NIST AM-Bench 2022, AMB2022-06

Material extrusion of polycarbonate and PLA test objects. Data at https://doi.org/10.18434/mds2-2711 ("Polymer
properties and printer calibration": rheology and extrudate temperature); description at
https://www.nist.gov/ambench/am-bench-2022-challenge-problems-and-measurement-results. It is the reference benchmark for
the thermal side of extrusion and the natural target once the twin gets a cooling model. Not confirmed: file list and
sizes; NIST advises against bulk download.

### 11. Other vibration and monitoring sets (all described only unless stated)

| Set | URL | Content | Use |
|---|---|---|---|
| Ender 3 V2 fault detection | https://zenodo.org/records/22716165 | ADXL345 at 3200 Hz, 27 acquisitions, about 40 h, six states including a loose X carriage; 200 Hz version and code | spectrum while printing; fault signature for the twin's slack-belt case |
| Federated learning, six identical printers | https://zenodo.org/records/5747732 | acceleration while printing cubes at several speeds; raw zip 90.6 MB | machine-to-machine spread at fixed design |
| Audio and vibration side channels | https://zenodo.org/records/13329934 | Bambu P1P and A1 Mini, 100 and 500 Hz, 10.8 GB, CC BY 4.0 | too coarse and too large |
| "Motion Analysis of Digital Twin of FDM 3D Printer" | https://zenodo.org/records/4527141 | a paper record, content not confirmed | unknown |
| "Digital Twin for FFF" | https://zenodo.org/records/18270596 | framework description | unknown |
| ARTS Lab lifecycle (downloaded) | https://github.com/ARTS-Laboratory/dataset-FFF-printer-full-lifecycle-vibration-monitoring | see item 12 | |
| Monkeyfab delta anomalies (README seen) | https://github.com/joanna-/3D-Printing-Data | two accelerometers (bed, head), belt tension sensor, firmware JSON with positions and temperatures; CC BY 4.0 | item 16 |
| `adiparamartha/fdm_dataset` (README seen) | https://github.com/adiparamartha/fdm_dataset | "sensory" fault data, 3.6 MB, undocumented, no licence | skip |
| UR16e robotic extrusion data release | https://github.com/antonmadto/ur16e-robotic-fff-data | plans, executed trajectories, bed metrology for a six-axis arm | different machine class |

Hugging Face was searched through its API with nine terms. It holds image sets of print failures, G-code corpora
(`kpoc/FDM-gcodes`, `ablam/gcode`) and robot-arm recordings; nothing with printer sensor traces.
Kaggle: only small tabular sets were found (for example "3D Printer Dataset for Mechanical Engineers", 50 prints,
settings against roughness and strength) and simulated ones.

### 12. ARTS Lab lifecycle vibration (downloaded)

Ender 5 Plus over 1,600 h; three laboratory accelerometers on hotend, feeder motor and frame; 15 recordings of 639 s at
1,651.6 samples/s while printing tensile bars. One raw file (41.5 MB, 1,056,000 rows) and the feature table are in
`arts_fff_lifecycle_vibration/`; the format parses. The commanded motion is not recorded, so it supports only a
comparison of spectra while printing a known part, after re-slicing that part.

### 13. Extrusion pressure, force and lag

- **arXiv 2310.01901** (read): UltiMaker print head with a load cell behind the nozzle and one on the feeder; PLA at
  1 to 7 mm3/s and 195, 205, 215 C; pressure drop against flow compared with a viscoelastic simulation; back-flow
  height. Results are recorded as HDF5 but no link is given.
- **Kazmer, Colon, Peterson, Kim 2021**, *Additive Manufacturing*, DOI 10.1016/j.addma.2021.102106 (described): melt
  pressure in an instrumented nozzle, compressibility of ABS from a blocked nozzle, joint fit of viscosity and
  compressibility; the model over-predicts capacitance at start and stop.
- **Colon, Kazmer, Peterson** (described): first-order gain and time constant of the pressure response to extrusion
  start, with their dependence on process factors.
- **Coogan and Kazmer 2019**, *J. Rheology* 63(1) (described): in-line rheometer on a printer.
- **University of Texas SFF 2023 system-identification paper** (described): measured extrusion time constants ranged
  from 61 % to 279 % of nominal, attributed to non-linearity.
- **Tronvoll, Popp, Elverum, Welo 2019**, pressure-advance algorithms, theory and simulation (described; CC BY at
  https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2629741).
- **Go and Hart 2017**, rate limits of extrusion (described): pinch-wheel feed limited to about 60 N and 9 mm/s.
- **Serdeczny, Comminal, Mollah, Spangenberg (DTU)** (described): strand cross-section and corner swelling by CFD with
  printed validation at corner angles of 15 to 90 degrees.
- **Maps to.** A flow-dependent lag and a feeder force limit in place of one fixed `extruder_lag_s`, and the corner
  bulge size in `deposit.py`. None has a confirmed data file; all need curves digitised.

### 14. Kickstarter x Autodesk FDM assessment protocol

https://github.com/kickstarter/kickstarter-autodesk-3d, `FDM-protocol/README.md` and `ksr_fdmtest_v4.stl`. Seven scored
features, 30 points: dimensional accuracy (5 points for mean error up to 0.10 mm, 1 point above 0.40 mm), fine flow
(spires and stringing), negative features, overhangs, bridging, XY resonance, Z alignment. Published scores exist for
real machines (Prusa MK3 22.5, per press coverage). It is the only outside benchmark found whose scoring could be
applied to the twin's simulated print. No licence file was found.

### 15 to 19. Smaller items

- **Weiss 2014 thesis** (https://reprap.org/mediawiki/images/e/ea/2014_Weiss_Closed-Loop_Control_of_a_3D_Printer_Gantry_Fig_12.pdf,
  71 pages, skimmed). MakerBot Replicator-class gantry with linear encoders at the carriage; measured step size
  10.6 um; open-loop mean trajectory error 0.40 mm against 0.09 mm closed loop (from a search summary, not checked in the text). The
  only measurement found of a belt axis's open-loop tracking error at the load.
- **Monkeyfab delta set.** Useful only if a delta design is ever in scope.
- **Mass Portal thesis** (https://github.com/ut-ims-robotics/siilak-thesis-2025-massportal, `Measurements/`). Mains
  power logged once a minute while a large bed heats to 60 and 110 C, and two resonance spectra. No licence, not kept.
- **Hiwin MG rigidity.** The 2025 US MG-series catalogue
  (https://s3.amazonaws.com/www.motionusa.com/hiwin/2025/MG%20Series-2025.pdf, read) has no rigidity table. Search
  summaries of the German catalogue give MGN12C at 44 N/um (older edition) or 67 N/um (newer) for light preload and
  about 105 to 109 N/um for Z1; the editions disagree and neither was read. THK and NSK hosts are blocked.
- **Stepper torque curves.** StepperOnline serves per-motor torque-speed PDFs (for example
  https://www.omc-stepperonline.com/download/17HS19-2004S1_Torque_Curve.pdf, fetched). They are plots at one voltage
  and driver. No measured pull-out data in CSV, and nothing on mid-band resonance, was found for any NEMA 17.
- **Dimensional accuracy and warp.** A data-in-brief article on the NIST test artifact (14 FDM prints, percent error
  per feature; PMC8427264, data on Mendeley), arXiv 2506.12252 (ringing roughness against speed and acceleration on ten
  printers, scanned cubes), and several warp papers with a handful of measured deflections each. No deposited warp data
  set was found.
- **Not found at all.** Measured lead-screw nut friction; measured coupler misalignment data; any work by Duenser at
  ETH on printers (the ETH work found is from the automatic control laboratory, see below).

## Existing twins and simulators, and what they do that ours does not

| Model | What it is | What it has that the twin lacks |
|---|---|---|
| Klipper `scripts/graph_motion.py` (GPL-3.0) | The developers' own toy: a move list through a spring-mass with hard-coded 35 Hz and damping ratio 0.05, with input shapers, smoothing and pressure advance | Nothing physical. It confirms that upstream reasons with the same single-mode model, and that 0.05 is their working figure. |
| Klipper `motan` | Logs commanded step positions, the planner's trapezoids and accelerometer samples on a real machine | It is the tool that would produce the missing input-output data set on any Klipper printer. |
| `Jumpybeetroot/shaper-sim` (GPL-3.0) | Browser model of a CoreXY axis: belt, motor magnetic spring and frame in series; overlays a real calibration CSV | Stiffening of the belt with tension; all-wheel-drive belt layouts; softening of the motor spring at speed from back-EMF; extra peaks from the toolhead's centre-of-mass offset and nozzle flex; belt-tooth forcing at v/2 Hz. Its constants are stated to be provisional. |
| `batu63562/ender3-hotend-twin` (GPL-3.0) | Three-node hotend model run beside the printer, with logs | Fan-dependent loss with threshold; heat carried off by filament; temperature-dependent capacity; an online loss factor that absorbs drift; power residual rather than temperature residual as the fault signal; a calibration and test split with an acceptance gate. |
| Prusa thermal model; Marlin and Kalico MPC | One- and four-mass hotend models with autotune | A calibration procedure that runs on the machine in minutes, and published constants for named hotends. |
| Okwudire group | Fitted linear and position-varying axis models used for feedforward | Amplitude-dependent response, racking coupled to carriage position, dynamics that vary over the build volume. |
| ETH Zurich automatic control laboratory (arXiv 2512.24905, 2512.16333; described) | Extrusion and cornering dynamics identified from two printed patterns and a phone camera, then used to optimise the reference | A way to fit the extrusion model from photographs of prints, with no added sensors. |
| DTU and others, CFD of strand deposition | Bead cross-section and corner swelling from melt flow | A physical bead shape; the twin uses an assumed bulge. |
| `Dicklesworthstone/frankensim` (README seen, 140 kB) | Rust print simulator said to have reduced models of hotend heating, extrusion pressure and lag, bead sections and cooling | Unverified; worth a read before writing a cooling model. |
| MK404 / MINI404, MarlinSimUI | Run the real Prusa or Marlin firmware against simulated hardware | Firmware in the loop for non-Klipper firmware; no mechanics. |
| `manmit97/mujoco-corexy-printer-sim`, `Tejas-025/3D_printing_simulation` (Simulink) | Kinematic animations | Nothing; neither has compliance or validation. No Modelica printer model was found. |
| `jjepleting/Material_Extrusion_Digital_Twin_Code` | Random-forest prediction of dimensional error on a Bambu A1 Mini with live telemetry | A data-driven dimensional model; its training data is not in the repository. |

## Proposed fitting plan

In order. Each step names the parameter, the data and what would count as done.

1. **Ringing damping.** Set the stepper and belt dampers so `calibration.modal_damping` returns 0.07 on X-type and
   0.09 on Y-type axes, with a range of 0.05 to 0.13. Data: item 1, cross-checked against the owner-entered values in
   the calibration study. Before applying, re-fit the corpus with a two-mode curve fit in place of the half-power
   width, on one file per machine, to remove the upward bias.
2. **Hotend thermal model.** Replace the assumed capacities and losses with a three-node structure fitted to the nine
   Ender 3 logs (item 2), holding out the print run. Check the result against the Prusa V6 constants (12.1 J/K, 20.5 to
   10.1 K/W) and the Marlin sets (6.5 to 16.8 J/K, 0.05 to 0.14 W/K). Add the fan-speed dependence of loss.
3. **Heater dead time and sensor lag.** Run a simulated relay autotune on hotend and bed and require Tu and Ku inside
   the 10th to 90th percentile of item 3 (hotend Tu 24 to 55 s; bed 20 to 160 s, median 89 s). Adjust `sensor_tau_s`
   and any transport lag.
4. **Extruder lag.** Make `extruder_lag_s` a function of drive type and nozzle: 0.03 to 0.06 s direct drive at 0.4 mm,
   scaling down with nozzle area, 0.2 to 0.25 s Bowden (item 4). Re-run the corner-bulge benchmark on `printer_v5`,
   which is Bowden and currently simulated with the direct-drive value.
5. **Melt-rate limit.** Add a per-hotend volumetric cap from item 7 and report under-extrusion above it.
6. **Belt stiffness.** When item 5 is fetched, set EA per mm width from the tensile curves at working tension, and
   decide whether the non-linearity needs a tension-dependent stiffness. Until then keep 22 kN per 6 mm with the 15 to
   27 kN range.
7. **Response shape.** Simulate the printed Taz 6 transfer functions (item 6) and compare gain and phase with the twin's
   axis model for a matching layout up to 100 Hz. This is a check, not a fit.
8. **Wider frequency check.** For the 16 licensed repositories of item 1, read masses and belt lengths from the
   configuration and the machine's bill of materials and extend the three-machine blind test.
9. **Outside score.** Script the Kickstarter x Autodesk protocol on the twin's printed part and compare with published
   scores.

### What stays unfitted

| Parameter | Why |
|---|---|
| Rail and bearing friction | No measured data found for miniature guides under printer loads. |
| Stepper torque at speed, step-loss acceleration | Only maker plots at one voltage; no controlled measurement of the acceleration at which a printer first loses steps. |
| Stepper mid-band resonance and detent effects | Nothing found. |
| Guide block stiffness | Catalogue editions disagree and none was read; no independent measurement. |
| Frame and joint stiffness | Comes from the design's own FEA; no public modal test of a printer frame except possibly item 8. |
| Position dependence of stiffness | Shown to matter (item 6) but no data to fit it. |
| Belt tension and its effect on stiffness | Only item 9 and, if fetched, item 5. |
| Bed heater | Only relay-test periods (item 3) and one unlicensed heat-up log; no logged heat-up with power for a named bed. |
| Warp, cooling, sag, adhesion | No model in the twin and no deposited data set found; NIST AM-Bench is the place to start. |
| Lead-screw nut friction, coupler misalignment | Nothing found. |

### The data set worth making

Everything above the first mode, the step-loss boundary and the friction terms need one thing nobody has published:
commanded motion and measured response on a machine whose masses and belt lengths are known. Klipper's `motan` logger
records step timing and accelerometer samples on a common clock. One evening on any Klipper printer, with the raw
resonance files kept rather than only the spectra, would settle more of the table above than every source in this
report together.

## Hand-download list

| What | URL | Why |
|---|---|---|
| GT2 belt stiffness paper (CC BY) | https://www.mdpi.com/2218-6581/7/4/75 | belt EA |
| Printer-bed modal data | https://zenodo.org/records/22770610 | bed modes and damping |
| Ender 3 V2 vibration set | https://zenodo.org/records/22716165 | spectra while printing, loose-carriage state |
| Six-printer vibration set | https://zenodo.org/records/5747732 | unit-to-unit spread |
| AM-Bench 2022-06 data | https://doi.org/10.18434/mds2-2711 | extrudate temperature, rheology |
| Kazmer et al. 2021 (paywalled journal; open copy at par.nsf.gov) | https://par.nsf.gov/biblio/10274466 | nozzle pressure transients |
| Tronvoll et al. 2019 (CC BY) | https://ntnuopen.ntnu.no/ntnu-xmlui/handle/11250/2629741 | pressure-advance theory |
| Duet3D research posts | https://www.duet3d.com/blog/duet3d-research-extrusion-behaviour-and-pressure-advance-part-2 | measured extrusion decay |
| Hiwin MG catalogue with rigidity table | https://hiwin.co.uk/wp-content/uploads/2017/05/CRD-Hiwin-Linear-guides-MG-series.pdf | guide stiffness |
| NIST artifact dimensions data-in-brief | https://pmc.ncbi.nlm.nih.gov/articles/PMC8427264/ | measured feature errors |
| Remaining 14 ARTS raw recordings (41 MB each, reachable from here) | repository in item 12, `raw_vibration/` | only if the wear trend is wanted |

Paid sources: the journal versions of Kazmer 2021, Go and Hart 2017, Coogan and Kazmer 2019 and the Okwudire
*Mechatronics* and *Additive Manufacturing* papers; arXiv or repository copies exist for most.

## Limits of this pass

- Nothing on a blocked host was opened. For those items the description, file list, size and licence come from search
  summaries and may be wrong.
- Repository licences were read from each repository's LICENSE file only; a licence stated elsewhere would have been
  missed, and a repository licence may not have been meant to cover committed measurement files.
- The damping figures are a first look with a simple estimator, not a calibration.
- GitHub code search only indexes small files on default branches, so larger raw recordings in public repositories
  would not have been found this way.
