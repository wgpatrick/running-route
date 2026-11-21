# Inspection strategy

Status 2026-11-21. This is the top-level synthesis. It pulls together:

- [INSPECTION.md](INSPECTION.md): today's workflow (plan, scan, form, record, ledger).
- [inspection_research/01_instruments.md](inspection_research/01_instruments.md): instruments, their accuracy and cost, kits.
- [inspection_research/02_automated_in_cell.md](inspection_research/02_automated_in_cell.md): the printer and the arm as measuring machines, in-print monitoring, uncertainty, gauge studies.
- [inspection_research/03_strategy_and_feedback.md](inspection_research/03_strategy_and_feedback.md): what to measure and why, statistics, GD&T, the data model, and gaps G1-G15.

Figures marked (est.) are the research files' own estimates and have not been checked by us yet.

Where things stand: the owner has no printer yet. Build 1 is the printer. The arm comes after it. The first real part,
RP04 (SendCutSend order S7855707), has been in production since 2026-11-20. Its predictions were frozen before it
arrived (section 5.6).

---

## 1. Principle: inspect predictions, not features

A measurement is worth taking when three things are true:

1. A design decision depends on it.
2. mechloop has made a quantitative prediction of it.
3. That prediction is uncertain enough that the reading could change a rule, a parameter, a tolerance or the next design.

So the inspection plan is a list of **predictions**, each tied to the model parameter or shop rule it tests. It is not
a list of every feature the part has. There are three kinds:

- **dimensional**: the part as made;
- **functional**: does it assemble, does it sit flat;
- **machine performance**: the assembled printer or arm against the twin.

Run the functional test on every interface. Measure dimensionally where the functional test fails, or where a parameter
is still being learned.

| Family | Prediction lives in | Dimensional check | Functional check | Parameter it informs |
|---|---|---|---|---|
| Screw-pattern fit | `fits.screw_patterns` (p_all_start) | pitch, position, hole diameter | bolt the mate on: do all screws start by hand? | `PROCESS[*].pattern/pos/hole_bias/hole_sd` |
| Bores, shafts | `fits.bores_and_shafts` | pin gauge, 2 readings 90 deg apart | push / slide / loose | `hole_bias` per process and size |
| Bend allowance | `plan._predict_flange_shift`, supplier K and radius | flange length, hole-to-bend, radius | fits its mates without forcing | supplier `k_factor`, `bend_radius` |
| Bend angle | `bends.BEND_TOLERANCE` | angle gauge, later laser plane fit | flange lies flat on its mate | `angle_sd_deg`, new `angle_bias_deg` |
| Hole near bend | `dfm_sheet` hole-to-bend rule (yes/no) | two diameters | screw passes | rule threshold, then an ovality curve |
| Kerf, edges, small features | supplier kerf compensation and spec minima | slot width, edge web, small holes (RP04) | tab in slot | kerf compensation per material and thickness |
| Flatness of mating faces | `PROCESS[*].flat` | surface plate and feelers | rocks when bolted? | `flat`; distortion near cut-outs |
| Print scale, holes, warp | `PROCESS.printed`, `verifiers/warp.py` | scale bar, hole ladder, corner lift | pin-fit ladder; part sits flat | per-axis scale, hole-bias curve, warp thresholds |
| Rail parallelism, squareness | `tolerance/stackup.py` | indicator on the carriage, diagonals | carriage drag over travel | frame part tolerances, shims |
| Bed flatness | `verifiers/bed_support.py` | Klipper bed mesh, cold and hot | first-layer print | bed support model, thermal distortion |
| Resonance, backlash | twin (`twin/calibration.py`, stepper) | ADXL345 `TEST_RESONANCES`; indicator back and forth | ringing tower | belt EA, toolhead tilt stiffness, frame mode (30-70 Hz flag in PRINTER_V12) |
| Print quality | `twin/deposit.py`, print settings | coupon dimensions, layer maps | flow, PA and temperature towers | flow, pressure advance, cooling |

Coupons beat production parts for learning parameters. Each coupon feature isolates one parameter, and a coupon costs a
few dollars as a passenger on an order. The set for the next order:

- a bend coupon with 3-4 bends and several flange lengths;
- a hole-to-bend sweep at 1t to 4t;
- a hole and slot ladder from 2 to 10 mm;
- a pattern plate (NEMA 17, 2020);
- a laser-cut metal dot target for the scanner.

## 2. How accurate the instrument must be

The usual rules on tolerance band to instrument uncertainty:

- **10:1** is the ideal.
- **4:1** is the floor for deciding conformance (MIL-STD-45662A / Z540-1 lineage).

Learning a bias is a different job from passing or failing a part. Averaging n parts reduces random error but not
instrument **bias**. Bias produces false learnings that look exactly like real process biases. So calibration against
references (gauge blocks, pins) matters more than precision.

| Process / feature | Tolerance (band) | Needed U at 10:1 / 4:1 | Instruments that meet 4:1 | Meet 10:1 |
|---|---|---|---|---|
| Laser-cut edge, hole position (SCS) | +/-0.127 (0.254) mm | 0.025 / 0.064 mm | scanner with full-field map (0.03-0.05 est.); caliper only just (0.02-0.03 real) | telecentric backlit (0.01-0.02 est.) |
| Laser-cut hole diameter | +/-0.127 mm | 0.025 / 0.064 mm | pin gauges (functional size); scanner (exit edge only) | pins; telecentric |
| Bend-to-edge, flange | +/-0.381 (0.76) mm | 0.08 / 0.19 mm | caliper, height gauge on plate, scanner | caliper, height gauge |
| Bend angle | +/-1 deg | 0.2 / 0.5 deg | digital angle gauge (0.1-0.2 deg), square and feelers | laser V-up plane fit (0.05-0.2 deg est.) |
| CNC 6061 | +/-0.05-0.13 mm | 0.010-0.026 / 0.025-0.065 mm | micrometer, pins, telecentric (in-plane) | micrometer only; a CMM otherwise |
| FDM prints | +/-0.1-0.3 mm | 0.02-0.06 / 0.05-0.15 mm | caliper, pins, laser height map, nozzle camera | micrometer, laser (opaque) |
| Bed flatness, rail parallelism | 0.05-0.1 mm over 200-300 mm | 0.005-0.01 / 0.012-0.025 mm | dial indicator on the carriage, eddy mesh (checked against the indicator) | indicator on a granite reference |

There is a stricter test for automated methods (02 section 6.2): a Type 1 study with Cg >= 1.33. That needs
s <= T/40, which is s <= 0.0064 mm for an SCS hole. No instrument in Tiers 1-2 is shown to meet it. We use 4:1 to judge
conformance, and the gauge study (section 5.4) to decide whether a method may feed learnings.

## 3. Staged plan

### Now: before the printer exists (Stage 0 parts, RP04)

Do now the parts of Stage A that need no printer:

- reference artefacts;
- the scanner's full distortion map;
- caliper data capture;
- frozen predictions.

**Measure RP04 with:**

| Feature | Method |
|---|---|
| Holes, outline | scanner and target (600 / 1200 dpi) |
| Holes, functional size | pin gauges, including the 1.2 mm hole and the 1.0 mm slot |
| Corner radius | USB microscope or a 1200 dpi scan |
| Thickness | caliper or micrometer |
| Flatness | feelers on the granite plate |

### Stage A: printer alone (after Build 1)

1. **In-print monitoring.**
   - Top-down snapshot every layer, compared with the G-code footprint (`twin/render.py`).
   - First-layer laser strips, before and after.
   - Base-corner warp profiles at layers 5, 20 and 50.
   - Obico on the overview camera.
   - ADXL345 windows and the SFS V2 logged.

   Detectors only pause and flag until their precision and recall have been measured on our own log.
2. **Scan each part on the bed before release.** Cool the bed to the measurement temperature (CTE: PLA reads about
   0.25 % large on a 60 °C bed). Then run a measurement job (`MEASURE_BEGIN` / `LASER_SCAN` / `CAM_GRAB` / `TAP_POINT`,
   02 section 2.5):
   - a laser height map;
   - nozzle-camera stills of the planned edges and holes;
   - Eddy tap on top faces (plastic only: over aluminium the coil sees the part).

   Write the rows with `who="printer"`. Record "on-bed" and "released" as separate states.
3. **Reference artefacts.**
   - Glass dot grid for the printer's XY error map: 50-150 µm uncorrected, 15-40 µm mapped (est.).
   - ChArUco calibration of the nozzle camera at fixed focus.
   - Laser Z calibration on gauge blocks.
   - A check standard on a bed corner.
4. **Flatbed scanner.**
   - Fit a full-field distortion map to every dot, not just scale.
   - Replace the paper target with the laser-cut metal dot target. Paper swells 0.1-0.3 % (est.). Measure the metal
     target once against gauge blocks.
5. **Sheet parts.** Use a V-up laser scan on the bed for bend angle and outside radius. This replaces the square,
   feelers and radius gauge.
6. **Caliper data capture.** An RP2040 reads the SPC port and acts as a USB HID keyboard, with a foot switch. It types
   into the existing form and tags each reading with its balloon number.

### Stage B: with the arm (zero touches)

The arm releases the part and puts it on the **scale**: mass against a learned per-profile ratio, flagged at 3 sigma.
It then routes the part by the plan:

| Part shape | Station |
|---|---|
| Flat face | **flatbed** (arm-worked lid or light box) |
| Non-flat profile | **telecentric backlit station**, 2-3 stable poses, bend end profiles |
| 2.5D features on any face | **kinematic nest on the printer bed** (3 balls in 3 grooves or 2+1 datum pins, AprilTag, pose measured once by the nozzle camera) for laser, camera and tap |

Each verdict is conform, non-conform or undecided (ISO 14253-1 guard band). Undecided parts go to a queue. Rerun the
gauge R&R with the arm's reload as the reproducibility factor.

### Stage C: self-checking instruments

- Check standards sit in fixed nests and are measured at the start of every session.
- Control charts track the printer XY map, laser scale, scanner scale and arm placement scatter.
- Drift beyond limits blocks measurement jobs and proposes a recalibration, as a learning with evidence.
- In-process signals are joined to final inspection by job id. Parts whose in-process signals were normal can later be
  sampled instead of all measured.

## 4. Recommended kit

| Tier | Contents | Cost |
|---|---|---|
| **1 Basic (buy now)** | granite plate 12x18 grade B ($70-130), iGaging Absolute Origin 150 mm SPC caliper ($70), DIY SPC-to-USB reader with foot switch ($30), metric pin gauge set 1-6 mm ($70), digital angle gauge ($40), dial test indicator and magnetic base ($40), three grade-2 gauge blocks (25/50/100 mm, about $40-60), 0.01 g scale ($30). Plus scanner upgrades: full-field map (software, free) and a laser-cut aluminium dot target as a passenger on the next SCS order (about $15-30) | **about $400-500** |
| 2 Station (when the arm arrives) | Tier 1 plus Mitutoyo 0-25 mm SPC micrometer ($180-320), iGaging 300 mm SPC height gauge ($200-410), gauge block set and ring gauges ($120-200), M3/M4/M5 thread plugs ($60-150), glass dot grid ($50-300), and a **telecentric backlit station**: 0.1x lens, 5-12 MP global-shutter camera, LED backlight, printed frame ($900-1,500) | **about $1,600-2,800 more** |
| 3 3D and ground truth | Tier 2 plus a structured-light scanner with turntable and spray ($1,200-1,800), 3D artefacts ($100-300), certified plate ($270-300), more SPC readers or U-WAVE ($100-600), a touch probe and ball plate ($300-600), sine bar, straightedge and level ($250-500), CT service for coupon batches ($500-1,000) | **about $5,000 total** |

**Recommendation: Tier 1 and the scanner upgrades now. Build the telecentric station when the arm arrives.**

Reasons:

1. **Tier 1 covers Stage 0.** Stage 0 is flat laser-cut and simply bent sheet. Tier 1 covers it at 4:1:
   - pins for holes;
   - the angle gauge for bends;
   - the mapped scanner for outlines and positions;
   - the plate for flatness.

   The plate, pins and blocks are references, and references make every later instrument trustworthy.
2. **The telecentric station mainly buys automation.** It reaches 10:1 too, but its real value is that the arm can load
   it, which serves the autonomy metric. Without the arm, the scanner does the same job with one touch.
3. **The glass grid and scale can wait** until the printer exists.

Buy the telecentric station earlier only if the Stage 0 gauge study shows the scanner cannot reach 4:1 on real holes.
Tier 3 waits until a part needs real 3D: the 2026 ISPRS benchmark found systematic errors in sub-$2k scanners.

## 5. Statistics and data model

### 5.1 Frozen prediction registry (gap G1)

Freeze each part's predictions per order **before** the part is measured. Every frozen file carries:

- a sha256 of its canonical JSON;
- a `frozen_at` time in UTC.

How the code uses it:

- `record.compare` scores only against a frozen file that verifies and was frozen no later than the measurement.
- If a part and order has no frozen file, `compare` warns and scores against the plan's current values. This is post hoc
  and marked `prediction_status = "unfrozen"`.
- A re-prediction after a rule change goes in a new file flagged `posthoc` and is never used to claim fidelity.

The same discipline as `twin/calibration.py`. The minimal version is implemented: `mechloop/inspect/predictions.py`
(`freeze` / `load` / `verify` / `status`) and `mechloop/data/measurements/predictions/`. Later (G11), move the twin's
resonance study into the same registry.

### 5.2 Uncertainties, and three tolerances kept apart

| Tolerance | Meaning | Used for |
|---|---|---|
| `spec_tol` | what the shop promises | disputes |
| `requirement` | what the function needs | the design verdict |
| `sigma` | the prediction's own standard uncertainty | learning and scoring |

Every measurement carries:

- `u`, its GUM budget: Type A from repeats, plus Type B (resolution/sqrt(12), calibration, temperature, Abbe, scanner
  target residual);
- `instrument_id`;
- `repeat`.

Score with z = (measured - predicted) / sqrt(sigma² + u²). Report **coverage**, the share inside the predicted 95 %
interval, beside mean |error|.

Take 3 repeats for any reading used to learn, or within 25 % of a limit. Record each repeat, not the average.

### 5.3 Variance split

measured = nominal + model bias + order effect + piece effect + feature effect + measurement error.

| Pattern in the residuals | Diagnosis | Action |
|---|---|---|
| Bias stable across orders | model bias | change the parameter |
| Order means scatter more than within-order spread explains | batch variation | widen `*_sd` |
| Residual tracks a design variable | model form is wrong | new model term (e.g. hole bias vs diameter) |
| Residual inside u | confirms the model | narrow the parameter's uncertainty |

A confident bias needs at least 2 orders, 2 or more pieces each, and several features per piece. Four holes on one plate
are not four independent samples.

### 5.4 Gauge study before learning

One-person reduced study per instrument and method (03 section 2.4):

1. 5 features x 5 readings, re-placing the part each time;
2. bias against blocks and pins;
3. scanner against caliper and pins on the same 10 features.

Automated methods add a Type 1 study (Cg/Cgk) and a crossed parts x reload x day study (02 section 6.2). The results go
in an instrument record that every measurement cites.

### 5.5 Learning lifecycle

The lifecycle is proposed -> accepted -> applied (commit sha) -> validated or refuted.

| Gate | Test |
|---|---|
| Propose | today's rule: n >= 3, mean > 2 SE and a floor. Compute the SE from order-level (or piece-level) means once there are 2 or more orders |
| Accept | **leave-one-ORDER-out**: refit without order k, predict order k, and the new value must beat the old on held-out data. With one order, leave one piece out and mark the learning `provisional` |
| Validate | the next order's frozen predictions, made with the new value, beat the counterfactual old value. Otherwise refute and roll back |

Shrink toward the published value: new = (pub/s_pub² + mean/SE²)/(1/s_pub² + 1/SE²). Supplier rules keep `published`
verbatim and gain an `as_measured` block. Each applied learning re-runs the verifiers and attaches the design diff.

**K-factor caveat.** Who unfolded the part decides what a flange error means:

- **We unfolded the DXF**: the error tests the published K, or our unfold.
- **The shop unfolded from STEP**: it tests only the shop's consistency (`bend_line_sd`), not K.

Record `unfold.by` on every order. RP04 was drawn by us but is flat, so it carries no K test.

### 5.6 RP04, frozen

File: `mechloop/data/measurements/predictions/RP04_S7855707.json`.

- **Frozen** 2026-11-21T02:49:41Z, before the part arrived.
- **Hash** sha256 `320a55fd...bf70bd`, pinned by `tests/test_inspect_predictions.py`.
- **Contents**: 33 predictions, the plan's 29 plus 4 supplements (C8 leg widths, C8 corner radius, C7 length).

**What RP04 tests:**

- **Hole size vs kerf**: 5.5 mm x4, 4.0 mm, 1.2 mm.
- **Hole-to-edge web, 0.8 mm at H6.** SCS's flag for order review was correctly predicted by
  `sendcutsend.specs.min_hole_to_edge` = 0.965 mm.
- **The 1.0 mm slot.** mechloop's generic minimum says it is too small. SCS's spec allows down to 0.813 mm. The frozen
  prediction backs SCS's spec: it predicts "cut, p about 0.8-0.85".
- **The sharp corner of the L cut-out**: a kerf radius of about 0.12 mm is predicted.
- **Overall size, positions, rock and thickness.**

Point predictions equal nominal: no mechloop model predicts a departure for a flat cut part. The information is in
**sigma**, which is honest judgement, not fitted: 0.05 mm on holes, 0.08 on positions, 0.10-0.15 on the small and
thin-web features.

## 6. GD&T on our drawings (ASME Y14.5-2018, minimum set)

1. **Datums from function, not the bounding box:**
   - A = the mounting face;
   - B = the locating hole or registering edge;
   - C = the anti-rotation feature;
   - for plates with no locating feature, use the hole pattern as datum (best fit).

   `plan.py` picks A from the largest mating face and B/C from the holes with the most important `interfaces`. Today's
   positions are measured from laser-cut edges (G8).
2. **Position at MMC on every fastener pattern.** Size it with the fastener formulas: T = H - F for a floating fastener,
   T = (H - F)/2 for a fixed one, the same as `fits.screw_patterns`. Ø0.359 position replaces ±0.127 coordinates and
   gives 57 % more usable zone.
3. **Composite position where the pattern matters more than its location.**
   - Upper segment: the pattern to A|B|C. Feeds `pos`.
   - Lower segment: hole to hole, relative to A. Feeds `pattern`.
4. **Flatness only on mating faces.** Measure it on a granite plate as a range of feeler readings, or as minimum-zone
   flatness by LP from scans. Rename today's "feeler under a corner" line to **rock/twist**.
5. **Everything else**: plain ± or a general note citing the shop's published figure. Box every basic dimension.

Generate the inspection plan from these annotations, so the drawing, plan, fit model and record share one source. When
evaluating against a scan:

- register to the datum frame to judge tolerance;
- use the best-fit registration only for the deviation map.

## 7. The 15 gaps in `mechloop/inspect` and the implementation plan

| # | Gap | Priority | Status / step |
|---|---|---|---|
| G1 | prediction copied from the current plan; never frozen | P0 | **minimal version done** (predictions.py; compare refuses post-freeze or tampered predictions). Next: freeze automatically in `add_order` and store the hash in the order row |
| G3 | no `u`, `instrument_id`, `repeat` on `Measurement` | P1 | add the fields; scan.py writes u from target residuals; 3 repeat boxes in the form |
| G2 | point predictions, no sigma; `tol` mixes spec and spread | P1 | sigma from process.py / bends.py; split `spec_tol` / `requirement` (RP04's frozen file already has sigma) |
| G6 | grouping ignores order, process, unfold source, size range | P1 | extend `_group_key`; record `unfold.by` in plan and order |
| G4 | SE from raw rows (correlated readings) | P2 | order- and piece-level aggregation, variance components |
| G5 | leave-one-measurement-out | P2 | leave-one-order-out (piece-out fallback, `provisional`) |
| G15 | fidelity is MAE only | P2 | z, coverage, log-likelihood in `summary` and `metrics` |
| G9 | "flatness" is rock/twist; no learning path | P2 | rename; add a surface-plate flatness method and a proposal path |
| G7 | K derivation assumes 90 deg, ignores who unfolded | P2 | general bend angle; joint K and radius fit from coupons |
| G8 | positions from bounding-box edges; outline offset ignored | P3 | functional datum frame; scan.py datum-frame option; pattern vs location split |
| G14 | no published-vs-measured in supplier rules | P3 | `as_measured` block; learnings target parameters |
| G12 | ledger stops at accepted | P3 | `applied` (sha), `validated` / `refuted`, automatic verifier re-run and diff |
| G10 | no functional or assembly checks | P3 | yes/no lines per interface linked to `fits` p_all_start (Brier score) |
| G11 | twin calibration and inspect are separate systems | P4 | shared prediction registry; resonance and bed mesh as machine predictions |
| G13 | fixed ranking scores | P4 | VOI = consequence x (sigma / requirement) x parameters informed / cost |

**Order of work:**

1. **Before RP04 arrives:**
   - G1 automatic freeze in `add_order`;
   - G3 fields;
   - G2 sigma in `plan.build_dims`;
   - coupons and the metal target in the next order;
   - run the gauge study when the box arrives.
2. **With the first data:** G6, G4, G5, G15, G9, G7.
3. **Data model:** G14, G12, G11.
4. **Drawings and plans:** G8, G10, G13.
5. **Build 1 machine plan from the twin:**
   - resonance and frame mode;
   - bed mesh, cold and hot;
   - belt tension;
   - rail drag;
   - skew and scale prints.

   Each line is a frozen prediction with a range.

## 8. Disagreements between the sources

**Reconciled:**

| Topic | The sources say | Resolution |
|---|---|---|
| Scanner accuracy | INSPECTION: 0.01 mm (synthetic); 01: 0.03-0.05 mm with a full-field map, 0.05-0.1 mm scale-only (est.) | Synthetic is not real. Plan with 01's figures until the gauge study measures it |
| Telecentric station cost | 01: $1,200-3,000 (12-20 MP); 02: $300-900 (5 MP) | The difference is lens price and sensor size. Budget $900-1,500: a 5-12 MP global-shutter camera is enough for 20-40 µm/px on 60-100 mm |
| Reference target | 01: laser-cut metal for the scanner; 02: glass grid for the printer XY map | Both, for different jobs: the metal target now, the glass grid when the printer exists |
| Hole size | pins (01), scanner (INSPECTION), nozzle camera (02) | They measure different quantities: functional (smallest through the thickness) vs exit-edge diameter. Record the method and learn each separately |
| Bend angle | 01: angle gauge; 02: laser V-up; INSPECTION: square and feelers | Angle gauge now, laser plane fit once the printer runs |
| Gauge study size | 03: reduced 5x5; 02: Type 1 with 25-50 repeats plus crossed | 03's study for hand instruments; 02's for automated methods |
| Arm station order | 01: telecentric first; 02: scale, then scanner, then telecentric | The scanner is owned and works now, so the telecentric station waits for the arm |

**Still open:**

- the scanner's real accuracy on laser-cut edges with dross;
- whether a Type 1 study of Cg >= 1.33 is reachable at all for SCS hole tolerances with Tier 1-2 kit;
- whether SCS's kerf compensation makes the hole bias zero (RP04 is the first evidence);
- Eddy tap repeatability on stuck PLA;
- laser bias on translucent filaments;
- XY-map stability over weeks.

## 9. Open questions for the owner

1. Approve Tier 1 (about $400-500) now? Buy metric pins (they cover RP04's 1.0-1.2 mm) or inch?
2. Add the coupon set and a laser-cut dot target to the next SendCutSend order (about $20-40)?
3. How many RP04 pieces were ordered? The frozen file assumes 1. Two or more allow a piece-level variance split.
4. Is there an outside lab or university CMM for one or two "golden" parts (ISO 15530-3 substitution)? What budget?
5. Should we upload our own unfolded DXFs for all bent parts (so flanges test our K), or STEP to some shops (testing
   their consistency)? This decides what the bend learnings mean.
6. When should `add_order` start freezing predictions automatically? And should a measurement with no frozen prediction
   be refused outright, not just warned about?
