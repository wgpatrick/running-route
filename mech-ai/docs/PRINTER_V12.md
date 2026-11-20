# printer_v12: the Build 1 candidate (v11.1 + v12 merged)

Everything here is simulated. Nothing has been built.

`designs/printer_v12.py` starts from a copy of `designs/printer_v11.py` (v11 was not edited). It carries out the v11.1 plan
(every purchased part pinned to a real, orderable product with the maker's CAD or a faithful re-make, `docs/V11_1_PLAN.md`) and
the v12 plan (HIWIN rails, 9 mm belts, stock bed heater, the full electronics bay, sensing and feedback hardware,
`docs/V12_PLAN.md`), with the owner's answers to the v11 questions and the decisions made while it was built (listed in
"What changed"). Every part carries a build stage: **1** frame, electronics bay, bed and Z; **2** gantry and toolhead; **3**
feedback (cameras, filament sensor, lights, laser, accelerometer).

**Verify (all 13 verifiers, `--tier full --no-render`, on the final design, finished 2026-11-20 20:57 UTC): FAILS, 11 errors, 156
warnings.** All 11 errors are the DG-07 purchased-part rule: **8 placeholder SKUs (13 parts)**, listed by stage in the
next section. Every other verifier passes (geometry, interference, tolerance, manufacture, ratings, motion, subsystems,
electrical, assemblability, FEA, printing, requirements). **41 of 41 requirements met.** Report: `out/printer_v12/report.json`.

## Build 1 stage-1 readiness

**Gate: not yet clean.** Stage 1 (frame, bay, bed, Z) has 87 purchased SKUs; 83 are real parts with sourced geometry and
ratings; **4 are still placeholders**. Its fabricated parts (16 sheet parts at SendCutSend, 6 turned posts at Xometry, 2
printed covers at Hubs) pass every check, and their inspection plans are written.

| Stage | Placeholder SKU | What is missing | Who closes it |
|---|---|---|---|
| 1 | `HEATER-HYDRA-SQ1451144-210x210-24V-200W` | `max_temp_c` (no maker figure; 180 degC silicone class value). Geometry is a re-make of NPH drawing NPHSF365; its thickness (1.5 mm) is **assumed** (not dimensioned) | Hydra Research / NPH: max temperature; measure thickness on arrival |
| 1 | `NEMA17-48-LEADSCREW-TR8x2-330-AB4` (x3) | `rotor_inertia_gcm2`, `efficiency` (not on StepperOnline drawing A4003) | StepperOnline |
| 1 | `TR8x2-INTEGRAL-17E19S1684AB4-330RA` (x3) | `efficiency` (0.35 typical, not stated) | StepperOnline |
| 1 | `CTRL-OCTOPUS-V1.1` | geometry: BTT publishes CAD for the V1.0 only (its PCB is surfaces, 92,000 faces, not a solid), none for V1.1; 4 ratings typical (logic power, max ambient, output resistance, thermistor pull-up) | BTT (V1.1 STEP, schematic figures), or the owner accepts the V1.0 CAD |
| 2 | `EXTRUDER-E3D-ROTO` | 3 motor ratings (surface temperature, inductance, step angle) | E3D |
| 2 | `HOTEND-REVO-24V-40W` | resistance at 23 degC, volts (PTC figures) | E3D |
| 2 | `SPACER-AL-M5-10x5.1x9.75` | no real product at 9.75 mm (X idler spacer); no McMaster / MISUMI number confirmed | owner: pick a stock length (10 mm moves the belt 0.25 mm) |
| 2 | `ENDSTOP-MICRO` (x2) | the OMRON D2F-01L sits on a generated 20 x 12.5 board: no bought module named | owner: a module with a D2F-01L, or the bare switch on its own M2 holes |
| 3 | none | | |

Cost and lead times per stage: see "Sourcing and the Build 1 schedule" below (`out/sourcing/printer_v12/`).

Critical path for stage 1: the four placeholders above are paperwork (ratings and one CAD file), not missing parts; the
long-lead purchased items are listed in the schedule. The Hydra pad's thickness and the MIC-6 plate's flatness are
receiving checks.

## The short answers

| Question | Answer |
|---|---|
| X travel | **186.6 mm** (189.6 mechanical) on a stock HIWIN MGNR12R **245 mm** rail (5 mm of rail beyond the block at each end). v11: 191.6 on a 250 mm rail. |
| Y travel | **208.1 mm** (v11: 214.5): the owner's 30T idlers (MISUMI AGTFW30) are 3.2 mm larger in radius; the Y idlers sit 0.7 mm further forward than v11's formula and the rear lead screw 0.9 mm forward (envelope 420 mm kept); front over-travel is 0.5 mm (soft limit) instead of 1.5. |
| Z travel | 180 mm + 1.65 mm over-travel. HIWIN MGNR12R 295 mm Z rails. |
| Print area | **186.6 x 208.1 mm** (388 cm2; v11: 411). On a 220 x 220 sheet: 80.2 % of it. |
| Bed | **Hydra Research SQ1451144** 210 x 210 mm 24 V 200 W pad (owner, 2026-11-20; NPH drawing NPHSF365) under a **240 x 240 x 6.35 mm MIC-6** plate (v11: 232): the three studs moved out to 112 mm so their washers clear the pad by 2.5 mm; the pad covers 100 % of the print area. Cantherm CS712025Y thermostat in the rear-right corner (1.1 mm off the pad's corner). |
| Bed limits | (a) 0.131 mm of 0.3; **(b) after the START_PRINT soak (3 carrier time constants, 30 min): 0.0026 mm** of 0.1 (cold-probed bound 0.085 mm; v11 failed (b) at 0.101); (c) 0.031 mm of 0.2. |
| Bed current | 200 W at 24 V = 8.33 A on the Octopus HB output (12.5 A, 67 %), a Littelfuse 0297010 10 A MINI blade fuse and the CS712025Y (10 A): **both 10 A parts are at 83 % (81 % with Klipper `max_power: 0.95`): THIN.** Heater voltage drop 3.0 % or less (passes): 189 W delivered. |
| Probe | **BTT Eddy Duo** on USB, coil face 2.5 mm above the tip, on a printed PETG holder on a one-bend 5052 L; no metal in its 5 mm coil band; temperature 55 degC nominal (60 degC rating), 67 degC in a hot case (open question). |
| Toolhead (moving in X) | **0.401 kg** (target < 0.45). |
| Electronics | Raspberry Pi 5 (+ active cooler, 27 W PSU) as host; mains through a Schurter DD11 inlet with a 4301.1405 fuse drawer (T8A), a Finder 22.32 contactor switched by a Phoenix PLC-RSC relay driven by a PN2222A from Pi GPIO26 (Moonraker power device); Octopus V1.1 with TMC2209 sticks; DIN-rail bay with covers; 16 AWG earth star. Firmware: Klipper with the Eddy, ADXL345, SFS V2, LED and laser pins, loaded by klippy offline with the RP2040 and Linux host-MCU dictionaries. |
| Mass / BOM cost | **17.25 kg / $2,094.58** (BOM estimate in the verify; v11: 13.82 kg / $1,110.99). The increase is the electronics and feedback hardware (Pi 5, cameras, laser, Eddy, contactor bay), HIWIN rails and MISUMI idlers. |

## What changed and why

### Purchased parts (v11.1)
- **Rails:** HIWIN MGN12HZ0C blocks and MGNR12R rails (Motion Constrained, US) from HIWIN's own STEPs: X 245, Y and Z 295
  (stock lengths, not cut). Travels re-checked (above).
- **Belts and pulleys:** 9 mm GT2 (Gates LL2MR09); McMaster 3684N13 20T drive pulleys (two M4 set screws at 90 degrees;
  hex-key access to them is not modelled: check at assembly) and MISUMI AGTFW30-GT2090-5 30T idlers (owner), both from the makers' STEPs.
- **Brackets:** MISUMI HBLFSN5-SEP and HBLFSNF5-SEP (CBM5-10 + HNTP5-5) everywhere a 2020 corner bracket was, HBLFSNF5 where a
  30 mm leg does not fit (the square's corners, the lower upright brackets, the Y tension pairs); tabs as in MISUMI's STEPs;
  CBM5-10 head clearance checked at every bracket.
- **Spacers:** Harwin R30 aluminium / nylon standoffs and spacers for every M3 stack.
- **Lead-screw motors:** StepperOnline 17E19S1684AB4-330RA checked against drawing A4003; the anti-backlash POM nut from the
  drawing (A4003 dimensions). Nut plates and keepers re-laid round it.
- **Fasteners:** McMaster part numbers for every screw, nut and washer in the model, display models from McMaster's STEPs.
- **PEM nuts:** PEM S-M3-0ZI (McMaster 95185A520) from McMaster's STEP; the rear tool plate's pockets round their heads are
  8.1 mm (6.9 closed in 31 % of simulated builds).

### Bed (v12)
- Bed heater: stock pad (owner's choice moved Keenovo 200 x 200 -> Hydra SQ1451144 210 x 210 on 2026-11-20); plate grown to
  240 mm, studs to 112 mm, thermostat moved to the corner. The pad's Molex 43640-0401 is a Micro-Fit 3.0 (about 5 A per
  contact): it is to be cut off and the bed loom's Mini-Fit HCS crimped on (lead gauge not stated: check on arrival).
- Limit (b) after heat soak: a `bed_after_soak` thermal case (the warming left after 3 carrier time constants: carrier
  0.75 K, studs 0.01 K) gives 0.0026 mm. **Stiffer / shorter thermal path, evaluated:** the cold-probed bound is dominated by
  the plate and studs growing (0.085 mm); after the soak almost nothing is left to grow, so a shorter or stiffer stud path
  buys under 0.003 mm and is not worth a change. What does matter is that the thumb-nut washers slip on the deck: if they
  stick, the cold-probed case grows to 0.20 mm (FEA case `bed_heated_60K_studs_stuck`). A 10-minute soak (1 time constant)
  would leave roughly 5.5 K in the carrier and 2.4 K in the studs: by linearity about 0.02 mm, still inside (b).

### Electronics (v12)
Pi 5 host and power switching as in the table; Semitec 104NT-4 bed thermistor; Omron D2F-01L endstops; Molex Mini-Fit HCS
and igus CF880 / chainflex in the moving looms; LAPP 16 AWG earth, one conductor per tab to the stud; DIN rail (WAGO 210-112,
cut by the builder) with WAGO end stops; mains covers printed in PETG with cord grips; the bay re-laid out. Klipper's
config is generated (`out/printer_v12/electrical/printer.cfg`) and loaded by klippy with three MCUs (Octopus, Eddy RP2040,
ADXL RP2040) plus the Pi's host MCU.

### Sensing and feedback (v12, stage 3 unless noted)
BTT Eddy Duo (stage 2); Arducam B0454 nozzle camera with a CIL062 lens; Quarton VLM-520 line laser with an insulating clamp
and a Klipper output pin; Pi Camera 3 overview (top front rail) and top-down (top back rail) cameras; BTT ADXL345 V2 on USB;
BTT SFS V2 on the top back rail; 24 V COB LEDs in printed clips. **Open item:** the nozzle camera, lens, laser, nozzle LEDs and
toolhead ADXL are BOM lines only: their toolhead bracket is not drawn (the Eddy fills the rear view).

### Printed parts
PETG, all at Hubs (assigned per part); none in a load path: part duct, two mains covers, Eddy holder, two camera mounts, SFS
mount, two LED clips.

### Catalogue additions made while building v12
JST XH housings and headers (JST's STEPs; the SXH contact re-made from the datasheet), Molex 39-01-2020 and Phoenix 0801733
(the makers' STEPs via CADENAS, REQ-015), Hydra SQ1451144 (re-make of NPHSF365), a true sheet-metal unfold for bent parts
(`mechloop/unfold.py`: the build package's flat DXFs, checked against volume within 2 %).

## Judgement calls (flagged)
- **Front Y over-travel 0.5 mm** (rear stays 1.5): Klipper's soft limit stops the carriage at the front; only following
  error passes it. This is what keeps the Y carriages and plates 1.4 to 1.55 mm off the 30T idlers.
- **Eddy ratings:** supply voltage taken from the USB 2.0 specification (BTT gives "5 V"); repeatability taken as 1 um
  (twice BTT's 0.5 um standard error); trigger height is a firmware calibration, so the "switching distance" is the
  calibrated height inside BTT's 2 to 20 mm reading range.
- **Nyloc temperature:** McMaster 90576A102's 250 degF nylon limit, 120 degC used.
- **CC BY-ND 4.0** on the Molex and Phoenix STEPs: the files are kept unchanged; cutting the Phoenix rail to length makes a
  derived shape in exported assemblies (the rail is not in v12's model: the WAGO rail is).

## Unverified, assumed or not done
- Hydra pad thickness (1.5 assumed); its NTC R25 (100 k assumed; not wired: the Semitec reads the bed); its max temperature.
- Octopus V1.1 geometry is BTT's outline and hole pattern only; envelope height assumed.
- Rotor inertia and screw efficiency of the Z motors.
- Stage-3 toolhead bracket not drawn.
- Eddy hot-case temperature 67 degC over its 60 degC rating (estimate).

## Questions for the owner
1. Accept the 10 A blade fuse and 10 A thermostat at 81 to 83 % on the 200 W bed, or cap the bed at `max_power: 0.8` (6.7 A,
   80 %: slower heat-up), or fit a 15 A fuse with a 14 AWG bed run (then the Mini-Fit HCS, 16 AWG max, must change)?
2. Octopus V1.1: accept BTT's V1.0 CAD as the display model (same outline per BTT's shared SIZE drawing), or keep the outline
   re-make until BTT publishes V1.1?
3. X idler spacer: a stock 10 mm M5 aluminium spacer (belt plane 0.25 mm off), or a stack?
4. Endstops: which bought D2F-01L module (or the bare switch on new mounts)?
5. The stage-3 toolhead bracket for the nozzle camera, laser and LEDs: design it in v12.x, or move those items to Build 2?

## Files
- `designs/printer_v12.py`; `mechloop/parts/batch12.py`; `mechloop/unfold.py`; `tests/test_v12_support.py`
- `out/printer_v12/report.json` (not in git); `inspect_form/plans/printer_v12/` (16 stage-1 sheet-part inspection plans)
- `docs/build/printer_v12/`, `viewer/`, `review/data.json` (v11's viewer and review data kept in `viewer_v11/`, `review_v11/`)
- `vendor_cad/inbox/` (supplier files used by v12), `vendor_cad/SOURCES.md`
