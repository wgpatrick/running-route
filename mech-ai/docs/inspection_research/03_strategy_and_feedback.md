# Inspection strategy, and how measurements close the loop

Researcher 3 of 3, 2026-11-21. Topic: what to measure and why, how many and how well, how to draw it (GD&T), how each
measurement reaches a prediction, a rule or the next design, and what to change in `mechloop/inspect/`. Read for this:
docs/INSPECTION.md, docs/ROADMAP.md, mechloop/inspect/{plan,scan,record}.py, mechloop/twin/calibration.py,
docs/PRINTER_V12.md, plus mechloop/tolerance/{process,bends,fits}.py where the predictions come from. Web sources at the
end. Where a figure is recalled rather than sourced, the text says so.

## Summary

The pipeline we have is a good dimensional pipeline. It plans, scans, records, compares and proposes, and the owner
approves each change. Five things stop it from being the learning loop the roadmap describes.

1. **Inspection starts from features, not from predictions.** The plan lists the dimensions a part has, ranked by a
   hand-tuned score. It should list the predictions the design relies on: fits, pattern position, bend allowance, flatness
   of a mating face, resonance, bed flatness. Each line then names the model and parameter it tests. Most of the value is
   in functional and machine-level checks, and the plan does not cover those today.
2. **Predictions are not frozen.** `record.from_plan` copies the predicted value from whatever plan file exists when the
   reading is typed in. If a rule changes between ordering and measuring, the "prediction" silently becomes post hoc.
   `twin/calibration.py` already does this properly, with frozen inputs, a hash pinned by a test, and post-hoc results
   kept apart. Inspection should do the same.
3. **No uncertainty anywhere.** Predictions are point values. Measurements carry no standard uncertainty, there is no
   repeat structure, and no gauge study has been done. So the system cannot tell three things apart: a model error, shop
   scatter, and its own caliper technique.
4. **The statistics treat correlated readings as independent.** Four holes on one plate, two pieces from one order, and
   repeat readings are all pooled as separate samples. That inflates significance. The "leave-one-out" check leaves out
   one *measurement*, not one *part* or *order*, so it does not test whether a learning carries over to the next batch.
5. **Learnings stop at "accepted".** Nothing tracks whether an applied learning actually beat the old value on the next,
   independent order. That prospective check is the only one that really counts.

The fix is a small data model. A **prediction registry** holds frozen, uncertain predictions, each tied to a model
parameter. A **measurement** carries its uncertainty and its place in an order / piece / feature / repeat hierarchy. A
**learning** moves a parameter and must win on a held-out order, then on the next real order. Then we design cheap
coupons and machine tests that feed this model directly, instead of reverse-engineering parameters from production parts.

---

## 1. What to measure, and why

### 1.1 Principle: measure predictions and risks, not geometry

A dimension is worth measuring when three things hold: (a) a design decision depends on it, (b) we have a quantitative
prediction for it, and (c) the prediction is uncertain enough that a reading could change something: a rule, a parameter,
a tolerance or the next design. Measuring a nominal that nothing depends on, with no model behind it, teaches nothing.
Rank each line by its value of information:

    VOI ~ (consequence if wrong) x (prior uncertainty of the prediction / tolerance needed) x (parameters it informs) / cost to measure

Today `plan.build_dims` uses fixed scores, for example 90 for a pattern pitch and 80 for a bend angle. They encode the
right instinct, but they cannot change as we learn. Once a supplier's K-factor is pinned down, its flange lengths should
fall down the list. A parameter that has never been measured should rise.

### 1.2 The prediction catalogue: what each check tests

Each row is one family of predictions the design already makes. The model column says where the prediction lives, so a
measurement can be routed back to it.

| Family | Prediction (model, file) | Dimensional check | Functional check (preferred where cheap) | Parameter it informs |
|---|---|---|---|---|
| Screw-pattern fit | `fits.screw_patterns`: p_all_start, p_all_start_freely | hole pitch, hole position to datums, hole diameter | **Bolt the mating part on**: do all screws start by hand (yes/no), and is there any binding? | `PROCESS[*]["pattern"]`, `["pos"]`, `hole_bias`, `hole_sd` |
| Bores / shafts | `fits.bores_and_shafts` | bore diameter (pin gauge, 2 readings 90 deg apart) | shaft or bearing pushes in / slides / is loose; pin-gauge go/no-go | `hole_bias` per process and size |
| Bend allowance | `plan._predict_flange_shift`; supplier K-factor and radius in `data/supplier_rules` | flange length, hole-to-bend, web width, bend radius | the bent part fits its mating parts without forcing | supplier `k_factor`, `bend_radius` |
| Bend angle | `bends.BEND_TOLERANCE` (recalled class values) | angle (square + feeler, later photo) | the flange face lies flat on its mate (feeler at its edge) | `angle_sd_deg`, new `angle_bias_deg` |
| Hole near bend | DFM rule `hole_too_close_to_bend` (a yes/no warning) | hole diameter across vs along the bend | the screw still passes | rule threshold (t-ratio); later a numeric ovality model |
| Kerf / edges | supplier kerf compensation | slot width, edge web, edge offsets from scan | tab-in-slot fit | kerf compensation per material and thickness |
| Flatness of mating faces | `PROCESS[*]["flat"]` | flatness on a surface plate (see 3.4) | the part rocks or doesn't when bolted; gap under it at full torque | `flat` per process; distortion near cut-outs |
| Print scale / shrink | `PROCESS["printed"]["scale"]` | X, Y, Z of a known-size coupon (per axis) | | per-axis scale per service and material |
| Printed holes | `hole_bias = -0.15` for all sizes | hole ladder (several diameters, vertical and horizontal) | pin / screw fit ladder | hole bias **as a function of diameter and orientation** (not a constant) |
| Warp | `verifiers/warp.py` warp risk (rule of thumb) | corner lift on a plate (feeler) | the part sits flat | calibrates warp.py's thresholds |
| Rail parallelism / squareness | assembly stack-up (`tolerance/stackup.py`) | dial indicator on the carriage along the rail; diagonal check | carriage drag (force gauge or motor current) over travel | frame part flatness / position, shim needs |
| Bed flatness | `verifiers/bed_support.py` (sag, tilt, lead accuracy) | Klipper `BED_MESH_CALIBRATE` mesh, range and shape | first-layer test print | bed support model, heater / plate distortion |
| Resonance | twin axis model (`twin/calibration.py`, `stepper`, `reference`) | ADXL345 `TEST_RESONANCES` per axis, peak frequency and damping | ringing tower: measured ringing wavelength gives frequency | belt EA, toolhead tilt stiffness, frame modes (PRINTER_V12 flags a 30-70 Hz frame rocking mode) |
| Backlash / lost motion | twin (stepper, belts) | dial indicator with small moves back and forth | circle / califlower print | belt tension, pulley fit |
| Print quality | twin deposit model (`twin/deposit.py`), print settings | coupon dimensions; layer photos | flow cube, PA tower, temperature tower, overhang test | flow, pressure advance, cooling |

**Functional before dimensional.** A functional check answers the question the design actually asks ("do the screws
start?") with zero inference. It is usually faster, it often needs no instrument, and it catches what the dimensional
plan misses: a burr, an oval hole, a pattern that is right relative to itself but wrong relative to the datum. Its
weakness is that a yes/no tells you little about the parameter. So pair the two: run the functional test on every
interface, and the dimensional check where the functional one fails or where a parameter is still being learned. The
`fits` verifier already predicts a probability (`p_all_start`, with its standard error), so a yes/no outcome *is*
quantitative evidence. Score it with a Brier score or log-likelihood across many interfaces.

### 1.3 Assemblies and the machine are inspection objects too

After Build 1, the most informative measurements are of the assembled machine, not of single parts. Klipper gives
accelerometer resonance testing and bed meshing as standard procedures. Ellis' print tuning guide and the common
califlower / ringing / PA towers turn the printer into its own measuring instrument. Each of these is a prediction the
twin already makes, or should make:

- **Resonance (ADXL345):** the twin predicts each axis's frequency with a range (`calibration.design_ranges`). The
  measured peak is a direct test, and it is exactly the blind-predict-then-compare study calibration.py already ran on
  three public machines, now on our own machine. Record the frame on its feet too: PRINTER_V12 flags a 30-70 Hz frame
  mode that could land on the shaper range.
- **Bed mesh:** predict mesh range and shape (sag between supports, tilt) from `bed_support`, then compare with the
  mesh. Repeat cold and at temperature: the difference is thermal distortion, a separate parameter.
- **Calibration prints:** scale per axis, skew (califlower-type print), hole bias by diameter, ringing wavelength (gives
  frequency = speed / wavelength; a cross-check on the accelerometer), and PA / flow. These close the
  `printed` process model for *our* printer, separately from the print service's.
- **Assembly checks during the build:** rail parallelism and carriage drag over travel, belt tension by frequency, gantry
  squareness by diagonals. The stack-up model predicts each, and each tells us whether the part-level tolerances add up
  the way the model says.

### 1.4 Coupons beat production parts for learning parameters

Fitting a K-factor from whichever flanges the printer parts happen to have is inefficient. A purpose-made coupon is
cheap: a few dollars at SendCutSend, and it rides in the same order. It is designed so each feature isolates one
parameter. Recommended Stage-0/1 coupon set (sheet):

- **Bend coupon** per material and thickness that matters: a U or Z channel with 3-4 bends, long flanges (a long flange
  turns angle error into a big, measurable offset), flanges of several lengths.
- **Hole-to-bend sweep**: a row of the same hole at 1.0t, 1.5t, 2t, 3t, 4t from the bend line. This turns the yes/no rule
  into a measured ovality-vs-distance curve that we can fit and use.
- **Hole and slot ladder**: holes from 2 to 10 mm and slots, to separate a constant kerf error from a size-dependent one.
- **Pattern plate**: a 4-hole NEMA 17 pattern (31 mm) and a 2020-extrusion pattern, so pattern accuracy is measured on
  the patterns we actually use.

Print coupons (for the print service now, our printer later): a hole ladder vertical and horizontal, a pin-fit ladder
(clearance 0 to 0.4 mm in 0.05 mm steps; fit / no-fit gives the clearance at which p(fit) = 0.5), a 100 mm scale bar per
axis, a warp plate. SendCutSend itself suggests checking bends by measuring overall length and bend-line locations
against its calculator layout. The coupon is the formal version of that.

An important subtlety about K-factor (SendCutSend). SendCutSend sets its bend radius and K-factor per material and
thickness, and publishes them in its calculator and on its material pages. **Who unfolds the part decides what a flange
error means.** If we upload a flat DXF that *we* unfolded with SendCutSend's published K, then a flange error measures
how wrong the published K (or our unfold) is for the parts as made. If we upload STEP and the shop unfolds it, a
flange error measures the shop's own consistency and has nothing to do with our K. The plan and the learning must record
which case applies. Today `propose_learnings` assumes the first.

---

## 2. Sampling and statistics

### 2.1 Four sources of variation, and why we must keep them apart

Every reading is

    measured = true value + measurement error
    true value = nominal + model bias (what a learning fixes) + between-order variation + between-piece variation + within-part feature variation

| Source | What it is | How to estimate it | What it changes |
|---|---|---|---|
| Measurement error | caliper technique, scanner noise, operator | gauge study: repeat readings, cross-instrument checks, reference artefacts | nothing in the design; sets the smallest effect we can learn |
| Model bias | consistent offset of reality from prediction (wrong K, hole bias, scale) | mean residual that persists **across orders** | a parameter value (a learning) |
| Between-order (batch) variation | different machine, operator, sheet lot, day at the shop | variance of order means | the tolerance (spread) the design must absorb, not a bias correction |
| Within-order (piece, feature) variation | repeatability of the process | variance inside an order | the `*_sd` values in process.py / bends.py |

A mean deviation found in a single order is **confounded** with that batch's offset. Only replication across orders turns
"this order was 0.1 mm long" into "this shop makes them 0.1 mm long". The minimum design for a confident bias learning:
**at least 2 orders, at least 2 pieces each, several features per piece.** A nested random-effects model
(order / piece / feature / repeat) separates the variance components. With the small n we will have, a simple
method-of-moments estimate is enough, or a Bayesian hierarchical model with weak priors centred on the published values.

### 2.2 How many

Effective sample size is set by the top level that varies, not by the reading count. Rough guide (normal approximation,
2-SE detection):

    n_needed ~ (2 sigma / delta)^2   where sigma = the spread at the level being replicated, delta = the bias worth detecting

Worked examples using the current recalled class values:
- Bend angle, sd 0.5 deg (bends.py), detecting a 0.3 deg bias: n of about 11 independent bends. A 4-bend coupon x 3
  pieces covers it in one order, *if* within-order bends are close to independent. Check that with the variance split.
- Flange length, bend-line sd 0.19 mm, detecting 0.1 mm: n of about 14. The SendCutSend published bend-to-edge tolerance
  of +/-0.381 mm means single parts cannot tell us a 0.1 mm K error. Averaging is the whole point of coupons.
- Hole bias, hole_sd 0.04 mm (sheet), detecting 0.02 mm: n of about 16 holes. A ladder plate gives that in one piece, but
  holes on one plate share a kerf setting, so treat it as one order-level observation until a second order arrives.
- Binary fit outcomes carry far less information per trial. Locating a p = 0.5 fit clearance to +/-0.05 mm needs a ladder
  of about 8 steps x 3-5 repeats.

The current `MIN_N = 3` with a 2-SEM test is a fine trigger for *proposing*. It is not enough for *accepting*. See 4.4.

### 2.3 Repeat readings and the uncertainty budget

- **Repeats:** take 3 readings for any value used to learn a parameter or within 25 % of a tolerance limit. Take 1 for a
  pass/fail far from the limits. Record every repeat, not the average: the spread *is* the Type A repeatability.
- **Budget per reading (GUM):** combine Type A (from repeats) and Type B (instrument resolution / sqrt(12), calibration
  error, temperature, Abbe offset for calipers measured away from the jaw root, scanner residual from the target fit) by
  root-sum-of-squares. Report the standard uncertainty u, and use k = 2 for expanded intervals. Store u on the
  measurement row. scan.py already measures the target-fit residuals, so it can write u per scan for free.
- **Ratio to tolerance:** the classic rule of thumb is a test uncertainty ratio of at least 4:1 (tolerance : expanded
  uncertainty; MIL-STD-45662A, then ANSI/NCSL Z540-1). Calipers (about 0.02-0.03 mm in practice, recalled) are fine for
  +/-0.127 mm cut tolerance only just. They are inadequate for learning a 0.02 mm hole bias. For that use pin gauges or
  the scanner at 1200 dpi.

### 2.4 Gauge R&R, scaled to a one-person lab

The AIAG MSA criteria: %GRR under 10 % acceptable, 10-30 % conditional, over 30 % not acceptable, and the number of
distinct categories at least 5. The textbook study is 10 parts x 3 operators x 2-3 trials. We have one operator, so do a
reduced study once per instrument and method, before Stage 0 results are trusted:

1. **Repeatability:** 5 features x 5 readings each, with the part removed and re-placed between readings. For the scanner,
   re-scan with the part rotated.
2. **Bias against a reference:** gauge blocks or pins (a cheap set) for calipers; for the scanner, a precision artefact or
   the same part measured with calipers / pin gauges.
3. **Cross-method agreement:** the scanner and the calipers on the same 10 features. Their mean difference is a bias one of
   them has. Their scatter bounds both.
4. **Reproducibility:** when the robot arm (stage B) presents parts to the scanner, its placement becomes the second
   "operator". Rerun the study then.

Store the result as an instrument record (`instrument id, method, sigma_repeat, bias, reference, date`). Every
measurement then cites it, and the uncertainty budget picks it up automatically.

### 2.5 Telling model error from shop variation, in practice

For each parameter, after each order:
- Mean residual stable across orders and larger than its SE: **model bias**. Propose a parameter change.
- Order means scatter more than within-order spread explains: **batch variation**. Propose widening the tolerance (`*_sd`),
  not a bias.
- Residual tracks a design variable (hole diameter, flange length, distance to bend, orientation): **model form is wrong**.
  Propose a new model term, for example hole bias as a function of diameter. That is a model change, not a number change.
- Residual within measurement uncertainty: **nothing learned**. Record it as confirming evidence, which narrows the
  parameter's uncertainty.

---

## 3. GD&T we should adopt (practical level)

ASME Y14.5 is the reference (2018 edition; check which revision a drawing cites, since 1994 / 2009 / 2018 differ in
details). We need very little of it, but the bit we need fixes real problems in the current plans.

### 3.1 Datums from function, not from the bounding box

`plan.py` measures hole positions "from datum C (x = 0 edge)" and "datum B (y = 0 edge)", the bounding-box edges.
`rows_from_scan` notes in a comment that it ignores the outline's offset. But a laser-cut edge carries kerf error and
plays no part in the fit. Use a datum reference frame built the way the part is used:

- **A (primary):** the face that bolts down: the mounting face. Three points of contact.
- **B (secondary):** the locating feature: a dowel or locating hole, or the edge that registers against a stop (a
  2020-extrusion face).
- **C (tertiary):** the second hole or edge that stops rotation.

For plates without locating features, use the pattern itself as the datum (best fit of its holes). That is what the
scanner's rigid ICP fit already approximates. The plan generator can pick datums automatically: A = the largest planar
face contacting a mate, B/C = the holes with interfaces to the most important mate (it already knows `interfaces` and
`mates`).

### 3.2 Position instead of +/- coordinates

A +/-0.127 mm coordinate tolerance gives a square zone 0.254 mm wide. A position tolerance of diameter 0.359 mm is the
circle that circumscribes it: about 57 % more usable area, with the same parts still functional. Position also comes
with the fastener formulas that link tolerance to function directly:

    floating fastener (clearance holes in both parts):  T (each part) = H - F
    fixed fastener (one part threaded / insert):         T (each part) = (H - F) / 2
    H = hole at maximum material (smallest), F = fastener at maximum material (largest), T = positional tolerance diameter

These are what `fits.screw_patterns` computes by Monte Carlo. Putting the position tolerance on the drawing makes the
inspection plan and the fit model speak the same language, so a position reading maps straight onto the fit prediction.
Use the **maximum material condition** modifier on clearance-hole patterns: a hole that came out big gets bonus position
tolerance, which is exactly what makes the screw still start.

### 3.3 Composite position: pattern vs location

process.py already distinguishes `pos` (feature to datum faces) from `pattern` (hole to hole in one set-up), with a good
note on why. Composite position tolerancing is the standard notation for that idea. The upper segment is a looser zone
locating the pattern to A|B|C. The lower segment is a tighter zone controlling hole-to-hole spacing, relative to A only.
Use it on drawings, and let the plan emit two kinds of check that feed the two parameters separately: pattern-relating
(pitch, best-fit pattern residuals) goes to `pattern`; pattern-locating (pattern centroid and rotation relative to the
datums) goes to `pos`.

### 3.4 Flatness, and what the feeler-under-a-corner test actually measures

Flatness is a form tolerance: two parallel planes, no datum. The current method ("largest gap under a corner with the
opposite corner pressed down") measures **rock / twist**, not flatness. It is still the functionally relevant number for
a plate that will be clamped, but it should be named as such. For real flatness: lay the part on a reference surface (a
granite surface plate; a cheap grade-B plate is far flatter than any sheet part, recalled), measure the feeler gap at
several points around the perimeter and middle, and take the range. Apply flatness only to mating faces. Profile of a
surface is the right control for printed organic shapes (ducts, covers), and it is what a later 3D scan would compare
against.

### 3.5 What to put on our drawings (minimum set)

1. A datum frame on every part that mates (A face, B/C locating features).
2. Position, at MMC, on every fastener pattern, composite where the pattern matters more than its location.
3. Flatness on mating faces only.
4. Plain +/- (or a general tolerance note citing the shop's published figure) for everything else.
5. A basic dimension (boxed) for every position target, so the plan's nominal *is* the drawing's basic.

The inspection plan should then be generated from these annotations, not alongside them. One source for drawing, plan,
fit model and measurement record.

---

## 4. Data model: from a reading to a better prediction

### 4.1 Objects

**Prediction** (new; frozen at order time)

| field | meaning |
|---|---|
| `pred_id` | stable id, e.g. `P-<hash of (subject, quantity, model, inputs)>` |
| `subject` | part / feature (plan key), assembly interface, or machine quantity (`x_resonance_hz`, `bed_mesh_range_mm`) |
| `quantity`, `unit` | |
| `value`, `sigma` (or `[low, nominal, high]`) | **with uncertainty**: from process.py / bends.py sd values, Monte Carlo (fits), or calibration ranges (twin) |
| `model`, `model_version`, `params` | which function and which parameter values (with their ledger ids) produced it |
| `informs` | parameter ids this prediction tests, with sensitivity d(value)/d(param), e.g. `sendcutsend.bend.k_factor.al5052.2.286mm: -1.8 mm per unit K` |
| `requirement` | what the design needs (fit limit, function), separate from the shop's spec tolerance |
| `spec_tol` | the shop's published +/- (what we can claim from the shop) |
| `protocol` | measurement method id (instrument, datum set-up, repeats) |
| `frozen` | timestamp + order id + hash of the plan file |

Keep three tolerances separate. Today the plan's single `tol` blends the first two:
- `spec_tol`: what the shop promises; used for disputes.
- `requirement`: what the function needs; used for the design verdict.
- `sigma`: what we predict will happen; used for learning and scoring.

**Measurement** (extend `Measurement`): add `pred_id`, `u` (standard uncertainty) with `u_budget`, `instrument_id`
(links to the gauge-study record), `repeat` index, `datum_setup`, `conditions` (temperature for printed parts and the bed
mesh), and `outcome` for yes/no functional checks. Keep `predicted` only as a copy, for readability. The truth is the
frozen prediction.

**Parameter** (new; one per learnable number): `param_id`, current value with uncertainty, `scope` (supplier, material,
thickness, process, machine), `published_value` + source (never overwritten), `as_measured` value + evidence, history
of ledger ids. Examples: SendCutSend K-factor per material/thickness; `PROCESS["sheet"]["hole_bias"]`, ideally per shop;
`BEND_TOLERANCE["angle_sd_deg"]`; printed-hole bias curve coefficients; belt EA; toolhead tilt stiffness; damping. The
twin's `fitted_parameters.json` / `fitted.triple()` already has the right low / nominal / high shape. Generalise that.

**Learning** (extend the ledger): `params` changed (old → new, with uncertainty), `estimator`, `evidence` (measurement
ids grouped by order), `validation` (see 4.4), status lifecycle
`proposed → accepted → applied (commit sha) → validated | refuted (by order id)`, and the next-design consequences it
triggers (4.6).

### 4.2 Residuals that account for both uncertainties

For each measurement linked to a prediction:

    r = measured - predicted
    z = r / sqrt(sigma_pred^2 + u^2)

- |z| consistently above 2 for one parameter: the model is biased or overconfident.
- z spread much below 1: predictions are underconfident, so tolerances are too pessimistic (the process.py header says
  they are "deliberately a little pessimistic"; we can now measure by how much).
- Fidelity metric: keep mean |r| (what `loop_metrics` reports today, beside the do-nothing |nominal - measured|), and add
  **coverage**: the fraction of measurements inside the predicted 95 % interval, which should be about 95 %. Also add the
  mean log-likelihood. A model that is right on average but overconfident should not score well.

### 4.3 Pre-registration (borrow calibration.py's discipline)

`twin/calibration.py` already did this right for resonances. The machines were written down from design data, frozen,
hash-pinned by a test, and compared; post-hoc additions sit in a separate file with a loud "NOT blind" note. Apply the
same to every order:

1. At `add_order`, write `mechloop/data/measurements/frozen/<order>/predictions.jsonl`, plus copies of the plan JSON
   and SVG, and store their SHA-256 in the order row.
2. `compare` / `propose` read predictions **only** from the frozen file for that order.
3. Re-predicting after a rule change is allowed, but it goes in a `posthoc` field and is never used to claim fidelity.
4. A test asserts that frozen files never change, as `calibration_machines.json`'s hash is pinned today.

This matters most for the loop metric. If we let fidelity be computed against predictions regenerated *after* a learning
was applied, the loop will appear to improve whether or not it does.

### 4.4 Validation: when may a learning be accepted and applied?

Three gates, stricter as we go:

1. **Propose:** the current rule (n of at least 3, mean > 2 SE and a floor). Keep it, but compute the SE from **order-level**
   (or piece-level) means once there are two or more orders, not from raw rows.
2. **Accept: leave-one-order-out (LOOO).** Refit the parameter without order k and predict order k's measurements.
   Average over k. Accept only if LOOO error with the new value beats the old value's error on the same held-out data,
   and the coverage is sane. With a single order, use leave-one-piece-out and mark the learning `provisional`. That is
   the honest version of today's leave-one-measurement-out, which mostly measures within-part repeatability.
3. **Validated:** after applying, the *next* order's frozen predictions (made with the new value) must beat what the old
   value would have predicted for the same parts (the counterfactual is easy to compute). If they don't, mark the
   learning `refuted`, roll it back, and look at the model form. This prospective test is the loop's real fidelity
   measure, and the roadmap's "prediction error before and after" should report this number.

Shrinkage: with small n, do not jump to the measured mean. Update the published value towards it, weighted by evidence:

    new = (published / s_pub^2 + mean / SE^2) / (1 / s_pub^2 + 1 / SE^2)

Take s_pub from the shop's published tolerance or the class value. This stops one odd batch from overwriting a published
figure. It also pools across thicknesses: K-factor varies smoothly with R/t, so a model K(R/t) fitted across all
SendCutSend thicknesses beats one free value per thickness.

### 4.5 Where each learning lands

| Evidence | Target | Notes |
|---|---|---|
| Flange / hole-to-bend / web residuals (we unfolded) | supplier K-factor (`data/supplier_rules/<shop>.json`, new `as_measured`) | generalise `dK = -2e/(t x theta)` to the actual bend angle; today it assumes 90 deg. Fit K and radius jointly from coupons with several flange lengths |
| Same, shop unfolded | shop consistency (`bend_line_sd`) | not K |
| Bend radius readings | supplier `bend_radius.value_mm` as_measured | radius gauge resolution is coarse; prefer the end-on scan |
| Angle bias / scatter | `bends.py` per-shop `angle_bias_deg`, `angle_sd_deg` | per shop, not global |
| Hole diameter vs size | process hole allowance **per shop and diameter range**; printed hole-bias curve | constant bias is a model-form assumption to test |
| Pattern pitch / best-fit residual | `PROCESS[*]["pattern"]` | via composite-position split |
| Pattern location | `PROCESS[*]["pos"]` | |
| Scale | `PROCESS[*]["scale"]` per axis (printed: X, Y, Z separately) | |
| Hole-near-bend ovality vs distance | numeric ovality model replacing the yes/no rule in `dfm_sheet.py` | from the coupon sweep |
| Functional fit outcomes | calibrates `fits.py`'s p_all_start (Brier score), `PLASTIC_HOLE_YIELD_MM` | |
| Warp / corner lift | `warp.py` thresholds | |
| Resonance, damping | twin `fitted_parameters.json` (belt EA, toolhead tilt stiffness, damping) | same flow as calibration.py's PROPOSED |
| Bed mesh | `bed_support` model inputs | cold vs hot split |
| Calibration prints | `printsettings.py` (flow, PA, hole compensation) and the twin's deposit model | per filament / printer |

Supplier rules: keep the **published** value and its source verbatim (the rule files already carry quotes and URLs) and
add an `as_measured` block (value, uncertainty, n orders, ledger id). Checks use as_measured where it exists, but report
both. A large gap between published and measured is itself a finding worth a polite note to the shop.

### 4.6 From learning to the next design

A learning should not stop at a number. After a parameter changes, re-run the verifiers on the current design
automatically and list what changed: a fit's p_all_start that dropped below threshold, a flange that now predicts out of
tolerance, a printed hole that should be resized. Attach that diff to the learning. That is how a measurement becomes a
design change, and it gives the "design change" timestamp that `loop_metrics` needs for loop time.

---

## 5. Gaps in the current pipeline, and a plan

### 5.1 Gaps found in the code

| # | Where | Gap |
|---|---|---|
| G1 | `record.from_plan` | prediction copied from the *current* plan file; nothing freezes it at order time |
| G2 | `plan.build_dims` | predictions are point values; no sigma; `tol` mixes the shop spec with the predicted spread; no `requirement` |
| G3 | `Measurement` | no uncertainty, no instrument id, no repeat index; repeats indistinguishable from features |
| G4 | `record._significant`, `propose_learnings` | SE from raw rows: features on one part and pieces in one order counted as independent, so significance is overstated |
| G5 | `record._loo_abs_err` | leave-one-measurement-out within a group; should be leave-one-order-out (or piece-out with a single order) |
| G6 | `record._group_key` | groups by (supplier, material, thickness, kind) only: no order / batch, process, unfold source, hole size range, print orientation |
| G7 | `propose_learnings` bend_allowance | K derivation assumes 90 deg; ignores who unfolded; mixes flange_length and hole_to_bend in one group without separating the cut-tolerance part |
| G8 | `plan` / `rows_from_scan` | hole positions referenced to bounding-box edges; the outline offset is ignored (noted in code); no functional datums |
| G9 | `plan` flatness | "flatness" is really rock / twist; no proposal path for flatness in `propose_learnings` |
| G10 | `plan` | no functional checks (fit trials, screw starts, rocking) and no assembly / machine checks; only part dimensions |
| G11 | `twin/calibration.py` vs `inspect/` | two separate predict-measure systems with different formats; resonance and bed mesh are not in the measurement record or ledger |
| G12 | ledger | lifecycle ends at accepted / rejected; no `applied` (commit) or prospective `validated` / `refuted`; no automatic re-verification of the design after a learning |
| G13 | ranking | fixed scores; nothing raises unmeasured parameters or lowers well-known ones |
| G14 | supplier rules | no field for measured-vs-published; a learning proposes overwriting `value_mm` directly |
| G15 | metrics | fidelity is mean absolute error only; no coverage / calibration of the predicted intervals |

### 5.2 Improvement plan (in order; each step small and testable)

**Step 1, before the Stage-0 order (cheap, the highest value):**
- Freeze predictions at `add_order` (frozen dir + hash in the order row; a test that pins it). Fixes G1.
- Add `sigma` to each plan prediction from process.py / bends.py sd values, and split `tol` into `spec_tol` and
  `requirement` (requirement from fits / stack-up where known, else null). Fixes G2.
- Add `u`, `instrument_id`, `repeat` to `Measurement`, and the repeat entry to the form (3 boxes for learning-grade
  lines). scan.py writes u from its target residuals. Fixes G3.
- Add the coupon parts (bend, hole-to-bend sweep, hole ladder, pattern plate) to the Stage-0 order. A dozen dollars buys
  more parameter information than all five planned parts together. Record "unfolded by: us / shop" in the plan.
- Run the one-person gauge study (2.4) when the box arrives, before measuring for learning.

**Step 2, the statistics (with the first data):**
- Order- and piece-level aggregation in `propose_learnings`, with a variance-component split (order / piece / feature /
  repeat). Leave-one-order-out (piece-out fallback, flagged `provisional`). Shrink toward published values. Fixes G4,
  G5, G6.
- Generalise the K-factor derivation to the measured bend angle, and fit K and radius jointly from coupons. Fixes G7.
- Add z-scores and coverage to `summary` and `metrics`. Fixes G15.

**Step 3, the data model:**
- A prediction registry (`mechloop/data/predictions/`) shared by `inspect` and `twin`. Move the calibration.py
  resonance study into it as the first machine-level prediction set. Fixes G11.
- Parameter records with `published` and `as_measured` blocks. Learnings target parameters, not raw rule fields. Fixes
  G14.
- Ledger lifecycle with `applied` (commit sha) and prospective `validated` / `refuted` on the next order, plus an
  automatic verifier re-run whose design diff is attached to the learning. Fixes G12.

**Step 4, drawings and plans:**
- Functional datum selection in `plan.analyse` (mounting face, locating holes from `interfaces`). Position at MMC and
  composite position for patterns. The scanner reports pattern-relating vs pattern-locating errors separately. Fixes G8.
- Rename the current flatness line to "rock / twist", and add a surface-plate flatness method for mating faces. Fixes G9.
- Add functional checks to the plan and the form: for each interface, a yes/no line linked to its `fits` prediction.
  Fixes G10.
- VOI ranking from parameter uncertainty x sensitivity x consequence. Fixes G13.

**Step 5, Build 1 and after (machine as inspection object):**
- A machine inspection plan generated from the twin: resonance per axis and the frame mode (ADXL345), bed mesh cold /
  hot, belt tension, rail parallelism / drag, califlower-type skew and scale, ringing tower, hole and fit ladders, PA /
  flow. Each line has a frozen prediction with a range.
- Automate the capture. Klipper writes resonance CSVs and the mesh; the Pi pushes them (roadmap phase 1). Coupon
  photos and scans go through the same pipeline. Each automated capture lowers `loop_metrics` autonomy (manual steps per
  part), which is the third loop metric.
- Later, the arm presents parts to the scanner: rerun the gauge study with the arm as operator.

### 5.3 What success looks like

After two Stage-0/1 orders: a gauge study on file. SendCutSend K-factor and radius as_measured, with uncertainty, for the
thicknesses we use. A measured hole-to-bend ovality curve. Per-shop hole bias. Each of these validated by
leave-one-order-out, and the first one prospectively validated on the next order. After Build 1: the twin's resonance
and bed predictions scored on our own machine, with coverage near the nominal 95 %. In loop terms: fidelity (on frozen
predictions) improves order over order, coverage stays calibrated, and manual steps per part fall as scans and machine
logs replace caliper readings.

## Sources

- AIAG gauge R&R criteria (via Minitab): https://support.minitab.com/en-us/minitab/help-and-how-to/quality-and-process-improvement/measurement-system-analysis/supporting-topics/gage-r-r-and-wheeler-s-emp-studies/is-my-measurement-system-acceptable/
- JMP gauge R&R (Barrentine bands, alternative scheme): https://www.jmp.com/support/help/en/16.2/jmp/gauge-rr-option.shtml
- Quality Magazine, Gage R&R: https://www.qualitymag.com/articles/94385-gage-rr-repeatability-and-reproducibility
- GUM (JCGM 100), Type A / Type B evaluation: https://www.iso.org/sites/JCGM/GUM/JCGM100/C045315e-html/C045315e_FILES/MAIN_C045315e/04_e.html
- NPL, Beginner's guide to uncertainty of measurement: https://www.npl.co.uk/getmedia/fe8d80ee-d5af-43d5-b7ea-bb3699233523/section1.pdf
- UKAS M3003, Expression of uncertainty: https://www.ukas.com/wp-content/uploads/2023/05/M3003-The-expression-of-uncertainty-and-confidence-in-measurement.pdf
- NIST paper on 4:1 TUR history (MIL-STD-45662A, Z540-1): https://www.nist.gov/node/661216
- NASA-HDBK-8739.19-4, critique of 4:1 TUR: https://standards.nasa.gov/sites/default/files/standards/NASA/Baseline/0/nasa-hdbk-873919-4.pdf
- ASME Y14.5-2018 preview (datum reference frames): https://webstore.ansi.org/preview-pages/asme/preview_y14-5_2018.pdf
- PTC Creo MBD tutorial (DRF, position, flatness examples): https://support.ptc.com/help/creo/creo_pma/r7.0/usascii/model-based_definition/asme/getting_started.html
- GD&T overview (position, bilateral zones): https://en.wikipedia.org/wiki/Geometric_dimensioning_and_tolerancing
- Zeiss, Y14.5 revision differences: https://qualityforum.zeiss.com/migration/images/1125_062f4ff4fce87faf710f8f80cb59f32d.pdf
- SendCutSend bending calculator (K-factor and radius per material): https://sendcutsend.com/bending-calculator/
- SendCutSend, bend allowance and deduction guide: https://sendcutsend.com/blog/guide-to-calculating-bend-allowance-and-bend-deduction/
- SendCutSend, K-factor guide: https://www.sendcutsend.com/blog/what-is-k-factor-in-sheet-metal-bending-the-ultimate-guide/
- SendCutSend, sheet metal bending step by step (verifying bends against the layout): https://sendcutsend.com/blog/step-by-step-guide-to-sheet-metal-bending/
- Klipper, Measuring Resonances: https://www.klipper3d.org/Measuring_Resonances.html
- Klipper, Bed Mesh (not fetched in this study; the standard reference): https://www.klipper3d.org/Bed_Mesh.html
- Fastener formulas (floating / fixed, T = H - F, T = (H - F)/2) and the MMC bonus: standard Y14.5 practice, recalled, not fetched here.
