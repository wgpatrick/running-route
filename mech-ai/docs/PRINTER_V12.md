# printer_v12: the Build 1 candidate (v11.1 + v12 merged)

Everything here is simulated. Nothing has been built.

`designs/printer_v12.py` starts from a copy of `designs/printer_v11.py` (v11 was not edited). It carries out the v11.1 plan
(every purchased part pinned to a real, orderable product with the maker's CAD or a faithful re-make, `docs/V11_1_PLAN.md`) and
the v12 plan (HIWIN rails, 9 mm belts, stock bed heater, the full electronics bay, sensing and feedback hardware,
`docs/V12_PLAN.md`), with the owner's answers to the v11 questions and the decisions made while it was built (listed in
"What changed"). Every part carries a build stage: **1** frame, electronics bay, bed and Z; **2** gantry and toolhead; **3**
feedback (cameras, filament sensor, lights, laser, accelerometer).

**Verify (final code, affected tier, finished 2026-11-21 04:02 UTC; earlier full runs in "What was run"): FAILS on the
purchased-part rule only: 10 errors (7 placeholder SKUs, 13 parts), 171 warnings.** The other 12 verifiers pass; **45 of 45
requirements met.** Report: `out/printer_v12/report.json`.

## Build 1 stage-1 readiness

**Gate: not yet clean, but the stage-1 items left are ratings paperwork, not missing parts.** Owner (2026-11-20): the missing
maker figures are being requested by email and are **non-blocking for the stage-1 ordering list**; they stay flagged.
Stage-1 fabricated parts (16 sheet parts at SendCutSend, 6 turned posts at Xometry, 2 printed covers at Hubs) pass every
check; their inspection plans are in `inspect_form/plans/printer_v12/`.

| Stage | Placeholder SKU | What is missing | Who closes it |
|---|---|---|---|
| 1 | `HEATER-HYDRA-SQ1451144-210x210-24V-200W` | `max_temp_c` (180 degC silicone class value). Geometry: re-make of NPH drawing NPHSF365, thickness 1.5 mm **assumed** (not dimensioned) | Hydra / NPH (email); measure on arrival |
| 1 | `NEMA17-48-LEADSCREW-TR8x2-330-AB4` (x3) | `rotor_inertia_gcm2`, `efficiency` (not on drawing A4003) | StepperOnline (email) |
| 1 | `TR8x2-INTEGRAL-17E19S1684AB4-330RA` (x3) | `efficiency` (0.35 typical) | StepperOnline (email) |
| 1 | `CTRL-OCTOPUS-V1.1` | 4 typical ratings (logic power, max ambient, output resistance, thermistor pull-up). Geometry now BTT's V1.0 STEP, accepted by the owner for the V1.1 | BTT (email) |
| 1 | `RESET-PUSHBUTTON-22MM-1NO` (BOM line) | the G9SE-201's manual-reset button (T33/T34), to sit beside the e-stop: product to name | Instinct |
| 2 | `EXTRUDER-E3D-ROTO` | 3 motor ratings | E3D (email) |
| 2 | `HOTEND-REVO-24V-40W` | resistance at 23 degC, volts | E3D (email) |
| 3 | none | the spool axle is MISUMI SFAL8-108-B15-S15 with McMaster 90592A022 nuts, NSK 608ZZ (MISUMI B608ZZ STEP), turned sleeves; the X idler spacer is McMaster 94669A079 | |

Cost and lead times per stage: "Sourcing and the Build 1 schedule" below.

## The short answers

| Question | Answer |
|---|---|
| X travel | **186.6 mm** (189.6 mechanical) on a stock HIWIN MGNR12R **245 mm** rail (5 mm of rail beyond the block at each end). v11: 191.6 on a 250 mm rail. |
| Y travel | **208.1 mm** (v11: 214.5): the owner's 30T idlers (MISUMI AGTFW30) are 3.2 mm larger in radius; the Y idlers sit 0.7 mm further forward than v11's formula and the rear lead screw 0.9 mm forward (envelope 420 mm kept); front over-travel is 0.5 mm (soft limit) instead of 1.5. |
| Z travel | 180 mm + 1.65 mm over-travel. HIWIN MGNR12R 295 mm Z rails. |
| Size | Machine **388 x 419.5 x 475.9 mm** (inside the owner's 420 x 420 x 480). With the owner's later requests, the rear spool holder and the NFJN5-30 feet: **389 x 510.4 x 511.4 mm** (the design's envelope check is set to 420 x 515 x 515; a requirement holds the machine itself to 420 x 420 x 480). |
| Print area | **186.6 x 208.1 mm** (388 cm2; v11: 411). On a 220 x 220 sheet: 80.2 % of it. |
| Bed | **Hydra Research SQ1451144** 210 x 210 mm 24 V 200 W pad (owner, 2026-11-20; NPH drawing NPHSF365) under a **240 x 240 x 6.35 mm MIC-6** plate (v11: 232): the three studs moved out to 112 mm so their washers clear the pad by 2.5 mm; the pad covers 100 % of the print area. Cantherm CS712025Y thermostat in the rear-right corner (1.1 mm off the pad's corner). |
| Bed limits | (a) 0.131 mm of 0.3; **(b) after the START_PRINT soak (3 carrier time constants, 30 min): 0.0026 mm** of 0.1 (cold-probed bound 0.085 mm; v11 failed (b) at 0.101); (c) 0.031 mm of 0.2. |
| Bed current | 200 W at 24 V = 8.33 A on the Octopus HB output (12.5 A, 67 %), a Littelfuse 0297010 10 A MINI blade fuse and the CS712025Y (10 A): **both 10 A parts are at 83 % (81 % with Klipper `max_power: 0.95`): THIN.** Heater voltage drop 3.0 % or less (passes): 189 W delivered. |
| Probe | **BTT Eddy Duo** on USB, coil face 2.5 mm above the tip, on a printed PETG holder on a one-bend 5052 L; no metal in its 5 mm coil band; temperature 55 degC nominal (60 degC rating), 67 degC in a hot case (open question). |
| Toolhead (moving in X) | **0.401 kg** (target < 0.45). |
| Electronics | Raspberry Pi 5 (+ active cooler, 27 W PSU) as host; **XP Power LBA350PS24** 24 V 350 W supply (owner, 2026-11-21: a drop-in for the out-of-stock LRS-350-24; universal input, no selector; inrush 30 / 60 A at 115 / 230 VAC); mains through a Schurter DD11 inlet with a 4301.1405 fuse drawer (T8A), a Finder 22.32 contactor switched by a Phoenix PLC-RSC relay driven by a PN2222A from Pi GPIO26 (Moonraker power device); Octopus V1.1 with TMC2209 sticks; DIN-rail bay with covers; 16 AWG earth star. Firmware: Klipper with the Eddy, ADXL345, SFS V2, LED and laser pins, loaded by klippy offline with the RP2040 and Linux host-MCU dictionaries. |
| Mass / BOM cost | **18.74 kg / $2,353.93** with the full spool and the safety-chain placeholders (BOM estimate in the verify; v11: 13.82 kg / $1,110.99). Live sourcing: see below. The increase is the electronics and feedback hardware (Pi 5, cameras, laser, Eddy, contactor bay), HIWIN rails, MISUMI idlers, feet and filament supply. |
| Score (on the design before feet / spool) | resonance X 72.8 Hz, Y 58.7 Hz; acceleration an owner would run about 6,000 mm/s2; frame stiffness X 1,634 / Y 2,007 N/mm; toolhead 0.401 kg; assembly 166 min, 268 fasteners. Tune: X shaper EI 90.4 Hz, Y MZV 58.6 Hz, pressure advance 0.042, mesh RMS 0.018 mm. Firmware-in-the-loop print of the standard bracket on real Klipper: 3,891 s, nozzle within 0.060 mm of the path, no collision in 4,074 poses, one corner-bulge warning. |

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

### Safety chain (owner, 2026-11-21, stage 1)
**OMRON A22E-M-02** e-stop (40 mm mushroom, twist release, 2 NC; re-made from OMRON's A22E data sheet; panel cut-out 22.3 mm is
Digi-Key's figure, flagged until read on OMRON's page) on a flat 6061 bracket on the **front face of the front-left post**,
left of the post, head forward at z 300 (35 mm proud of the frame's front), its body running back outside the frame's left side.
**OMRON G9SE-201** safety relay (17.5 x 124 x 111.6, 2 NO 5 A, manual reset; re-made from data sheet J198) on a WAGO rail across the
back wall's rear faces (post_lb and upright_rear) at z 345, **outside the frame**: at 111.6 mm deep it cannot stand in the bay
under the carrier (the carrier comes down to z 142), and its rail sits above the rear nut plate's highest reach through the back
wall. Bracket and rail are held through the T-slots (MISUMI HNTP5-5), nothing drilled. Loop: Phoenix PLC-RSC contact (GPIO path) in
series with the G9SE's two safety outputs in series with the Finder coil; G9SE inputs: the e-stop's two NC channels, a spare pair
for a door interlock (future) and one for a smoke / heat detector contact (future); a reset button (BOM placeholder). The GPIO path
can only drop the contactor. A requirement checks the parts are drawn and real and the outputs carry the coil; **the electrical
verifier's own circuit model still switches the coil from the Phoenix relay alone** (the series loop is not in its netlist).
What covers heater runaway: as the requirement says (Klipper's MCU-side max_duration and the bed thermostat; nothing automatic
for the hotend if the MCU itself hangs with a heater on).

### Sensing and feedback (v12, stage 3 unless noted)
BTT Eddy Duo (stage 2); Arducam B0454 nozzle camera with a CIL062 lens; Quarton VLM-520 line laser with an insulating clamp
and a Klipper output pin; Pi Camera 3 overview (top front rail) and top-down (top back rail) cameras; BTT ADXL345 V2 on USB;
BTT SFS V2 on the top back rail; 24 V COB LEDs in printed clips. **Open item:** the nozzle camera, lens, laser, nozzle LEDs and
toolhead ADXL are BOM lines only: their toolhead bracket is not drawn (the Eddy fills the rear view).

### Feet (owner, 2026-11-20, stage 1; pending the owner's confirmation)
Four **MISUMI NFJN5-30** levelling mounts (M5 x 30, 30 mm swivel foot, all metal, 1.5 kN, 15 g; MISUMI's STEP, catalogue p.3166).
**The frame's corners are on the bottom side rails** (horizontal: the posts stand on them), so there is no downward end tap and
no MISUMI end-tap alteration applies. Each mount screws into a drop-in T-nut (MISUMI HNTAJ5) in the rail's **bottom** slot, 25 mm
in from the post, locked by a DIN 934 nut against the rail's underside; the screw reaches 5 mm into the slot (0.5 mm off its
floor). Frame 35.5 mm above the floor; nothing hangs below the bottom rails, so that is also the clearance under the bay
(the tray is on top of the rails). The outer side faces stay free for the enclosure. **Rocking mode (estimate):** 18.5 kg
(with a full spool) on four feet 320 mm apart, CoG about 200 mm up: f = 15 Hz at 100 N/mm per foot, 26 at 300, 33 at 500, 47 at
1000, about 67 at 2000. The all-metal NFJN is stiff in compression, but its swivel and a soft desk set the real figure:
**anywhere from 30 to 70 Hz can land on the Y input shaper (MZV 58.6 Hz) or the X (EI 90.4 Hz) range: flag. Measure with the
ADXL345 on the frame (TEST_RESONANCES with the chip on the frame) before trusting the shaper.** A rigid-body rocking moves nozzle
and bed together, so its print error is smaller than its amplitude. Fallback: MISUMI HAJP5-2020-6 plate + McMaster 6301K78 M6
rubber foot (both staged; needs the plate on a rail end, i.e. a frame change at the corners).

### Filament supply (owner, 2026-11-20, stage 3)
A 1 kg spool (the envelope of Prusa's Prusament spool STEP: 199.89 OD, 51.25 bore, 64.13 wide; 1.25 kg full) behind the frame, its front face at y 236 (clear of the rear nut
plate and Y motors, which reach y 226), hanging by its hub on two NSK 608ZZ bearings (MISUMI) on a cantilevered M8 x 140 axle (spool lifts off
the free end: no tools), the axle clamped in a flat 6061 .125 plate (SendCutSend) on the top back rail's rear face, inboard of
the right Y motor. Filament from the spool's top to the **SFS V2, now standing vertical** (in at the bottom, out at the top),
then a 4 mm PTFE tube from a McMaster 2333N214 push-fit (M10 x 1; the SFS's port thread is **assumed**, BTT does not state it: check on arrival) straight into the Roto's own bowdaptor collet (E3D's reference CAD: no coupler there). **Check (requirement):** the tube, taken as straight up from
both ends joined by a half circle, touches no part over the whole X / Y travel; least bend radius **52 mm** (limit 50 until
the datasheet: thin), at the rear corners; path 187 to 557 mm: **cut the tube about 610 mm**. Drag (estimate) under 2 N against
the Roto's tens of newtons. Spool mass on the frame: 1.25 kg at the top rear (the frame-mode FEA is of the frame alone; the
spool lowers the rocking mode above by about 3 %).

### Enclosure (V13, owner): nothing added in v12. The outer faces used: the top front rail's top (overview camera), the top
back rail's rear face (top-down camera, SFS, spool plate), the top right rail's top slot (Y switch), the bottom left rail's
side (inlet panel, earth stud). The feet use the bottom slots.

### Endstops (v12)
Each endstop is now the real **OMRON D2F-01L** (Digi-Key, $1.44; re-made from OMRON's D2F data sheet: body 12.7 x 6.5 x 5.8,
operating position 6.8 +/-1.5 from the hole line, overtravel 0.55) **bonded (epoxy) to a fabricated 20 x 12.5 x 1.6 mm 6061
carrier** (SendCutSend) that keeps the old generated board's outline and M3 holes, so both switch mounts and their screw stacks
are unchanged; the terminals pass through a 4.5 x 13 mm slot (tape them) and the leads are soldered on. The switch's own
2.0 mm holes (M2) are not used: no McMaster M2 numbers of the right length are in hand.

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

## Sourcing and the Build 1 schedule

`python -m mechloop.sourcing --design designs/printer_v12.py` (live distributor APIs, 2026-11-21; `out/sourcing/printer_v12/`):

| Stage | Purchased lines | Purchased $ (build of 1) | Earliest finish | Gated by |
|---|---|---|---|---|
| 1 frame, bay, bed, Z | 91 | $2,391.06 | **138 business days** (11 with an in-stock supply) | the Mean Well LRS-350-24 (no stock); otherwise the printed mains covers |
| 2 gantry, toolhead | 29 | $596.22 | 11 business days | the printed Eddy holder and duct |
| 3 feedback, filament supply | 19 | $336.01 | 11 business days | the printed camera / SFS mounts and LED clips |

Purchased total $3,323.29 for one machine (old verify estimate $2,353.92); fabricated parts carry no live price (SendCutSend / Xometry / Hubs quotes are not automated: about $24 of design floors).
The purchased total is inflated by about $640: the 16 AWG silicone wire is priced as two 500 ft spools (the tool takes the
smallest offer it found). **The Mean Well LRS-350-24 has no distributor stock (Mouser 0, 189-day lead) and sets a 138-business-day
critical path.** Alternatives checked live the same day (`--list`, all universal input, no 115/230 switch needed):

| Supply | Best offer | Stock | Price | Note |
|---|---|---|---|---|
| **XP Power LBA350PS24** (350 W, 14.6 A, 90-264 VAC) | Digi-Key | 63 | $44.75 | **recommended (REQ-021)**: a mechanical drop-in for the LRS-350-24 (215 x 115 x 30, same 4 x M4 on 150 x 50 and side holes, terminal block and fan in the same places); universal input, so the 115/230 selector label goes |
| Mean Well RSP-320-24 (320 W, 13.4 A, PFC, fan) | Mouser 709-RSP320-24 | 921 (Newark 231) | $53.20 | 270 W peak need is 84 % of it; 215 x 115 x 30 per its 2026-09-04 datasheet and STEP (the LRS case size); hole pattern to check |
| Mean Well UHP-350-24 (350 W, slim, fanless) | Newark 01AH8022 | 17 | $88.47 | single source; Mouser 0 |
| TDK-Lambda RWS300B-24 (300 W) | Digi-Key | 513 (Mouser 456) | $97.90 | the non-Mean Well option; 300 W is 90 % of the peak |
| Mean Well SE-350-24 | Digi-Key | 0 | $56.13 | obsolete |
| CUI VGS-350-24 | not found at the distributors | | | |

## Unverified, assumed or not done
- Hydra pad thickness (1.5 assumed); its NTC R25 (100 k assumed; not wired: the Semitec reads the bed); its max temperature.
- Octopus V1.1 geometry is BTT's outline and hole pattern only; envelope height assumed.
- Rotor inertia and screw efficiency of the Z motors.
- Stage-3 toolhead bracket not drawn.
- Eddy hot-case temperature 67 degC over its 60 degC rating (estimate).

## Questions for the owner
0. The safety relay sits outside the back wall and the e-stop's head 35 mm in front of the frame: acceptable, or should v12.1 re-lay
   the bay (e.g. a side box) to bring the G9SE inside?
1. Accept the 10 A blade fuse and 10 A thermostat at 81 to 83 % on the 200 W bed, or cap the bed at `max_power: 0.8` (6.7 A,
   80 %: slower heat-up), or fit a 15 A fuse with a 14 AWG bed run (then the Mini-Fit HCS, 16 AWG max, must change)?
2. The rear spool and the feet take the machine to 389 x 510 x 511 mm: acceptable against the 420 x 420 x 480 envelope?
3. The SFS V2's port thread (M10 x 1 assumed for the McMaster 2333N214): confirm on the part.
4. A frame rocking mode on the feet may sit at 30 to 70 Hz (estimate): measure it with the ADXL345 on the frame before tuning.
5. The stage-3 toolhead bracket for the nozzle camera, laser and LEDs: design it in v12.x, or move those items to Build 2?

## What was run (2026-11-20 / 21)
- Full verifies (`--tier full --no-render`) on each major state: 20:57 (11 errors, all DG-07), then after the feet / spool /
  Octopus / JST changes (17 errors, DG-07 only, 01:49), then **affected-tier verifies after each later owner change, the last on
  the final code: FAILS on the purchased-part rule only: 10 errors (7 placeholder SKUs, 13 parts), 171 warnings; all other 12 verifiers pass; 45 of 45 requirements met (affected tier, finished 2026-11-21 04:02 UTC)**. Memory: two runs died (signal 9) when a second job ran beside a verify and when the full
  Octopus STEP was loaded; both fixed (one heavy job at a time; the Octopus display model reduced to BTT's 59 large solids).
- `score --assembly`, `tune`, and the firmware-in-the-loop print (`out/printer_v12/fil/bracket/`) on the design before the feet
  and spool were added (the toolhead and gantry are unchanged since).
- `python -m mechloop.sourcing --design designs/printer_v12.py` (live APIs) and a `--list` run of the supply alternatives.
- Viewer export with the FIL print (`viewer/`), build package (`docs/build/printer_v12/`, STALE banner: the report has DG-07
  errors), review data (`review/data.json`, `review/drawings/`, `review/meshes_a.txt` + `meshes_b.txt`), inspection plans for the
  16 stage-1 sheet parts (`inspect_form/plans/printer_v12/`). `tests/test_v12_support.py`: 5 passed.

## Files
- `designs/printer_v12.py`; `mechloop/parts/batch12.py`; `mechloop/unfold.py`; `tests/test_v12_support.py`
- `out/printer_v12/report.json` (not in git); `inspect_form/plans/printer_v12/` (16 stage-1 sheet-part inspection plans)
- `docs/build/printer_v12/`, `viewer/`, `review/data.json` (v11's viewer and review data kept in `viewer_v11/`, `review_v11/`)
- `vendor_cad/inbox/` (supplier files used by v12), `vendor_cad/SOURCES.md`
