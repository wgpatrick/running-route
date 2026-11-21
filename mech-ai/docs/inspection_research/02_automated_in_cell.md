# Inspection research 02: automated and in-cell inspection (2026-11-21)

Question: how far can inspection run with no human touch, using what the cell already has (printer_v12 with Klipper on a
Pi 5, overview and top-down Pi Camera Module 3, the Arducam nozzle camera at 16-19 µm/px, the BTT Eddy Duo, the Quarton
VLM-520 Class 1M line laser, the ADXL345, the SFS V2 filament sensor, the flatbed scanner) and, later, the robot arm?
Builds on docs/INSPECTION.md (the scanner pipeline and the ledger), docs/HEIGHT_SENSING.md (Eddy and laser figures),
docs/NOZZLE_CAMERA.md, docs/ARM_SCOPE.md (task B: inspection handling) and docs/arm_research/06_perception.md.

Numbers marked **(est.)** are this file's own estimates from first principles and must be measured before anything
relies on them. Numbers with a link come from the cited page; vendor claims are called vendor claims.

## 1. Summary

| Question | Recommendation |
|---|---|
| Can the printer be the measuring machine? | **Yes, for 2.5D measurements of parts still on the bed or in a nest on the bed**: laser-line height maps (about 5-10 µm per point on opaque surfaces, 10-30 µm on translucent plastic, per HEIGHT_SENSING section 3), nozzle-camera images stitched by printer XY for edges and holes, and Eddy **tap** as a Z touch probe on top faces. XY accuracy is set by the belt motion system, not the sensors: expect 50-150 µm absolute uncorrected and 15-40 µm after mapping the XY error against a glass grid **(est.)** |
| Can the Eddy probe scan parts? | Only **conductive** parts (the SendCutSend aluminium and steel), and only broad faces: its footprint is about the coil size, so edges and holes blur. Plastic is invisible to it, which is useful in a different way: tap mode on top of a plastic part still reads the steel sheet underneath |
| In-process monitoring | Cheapest wins first: layer-change snapshots from the top-down camera, a first-layer laser scan (bed before, layer 1 after, as Bambu does with its micro-lidar), SFS V2 for runout/jams, Obico (self-hosted) for spaghetti, ADXL345 logging for a later anomaly model. Published accuracies (90-99 %) come from small lab studies; plan to measure our own precision and recall |
| Fixed station for the arm | A **scale** (0.01 g) first, then the flatbed scanner (already a calibrated silhouette instrument), then a **backlit silhouette camera** with a telecentric lens. Turntable structured light last and only if a part needs true 3D |
| Software | Register to CAD by **datum**, not by whole-part best fit; deviation maps with Open3D or CloudCompare; feature fits (circle, plane, cylinder, minimum-zone flatness by linear programming); every result carries an uncertainty and a three-state verdict (conform / non-conform / undecided) per ISO 14253-1 |
| Gauge R&R | No operators, so replace "appraiser" by **reload** and **day**: a Type 1 study (Cg, Cgk >= 1.33) per instrument and feature kind, a crossed parts x reload x day study for each automated method, and a daily check standard. For the learning ledger, **instrument bias matters more than repeatability**; it must be removed with calibrated artefacts |
| Staging | Stage A (now, printer alone): in-print monitoring plus a **post-print in-place scan** of every part before it leaves the bed. Stage B (arm): scale, scanner and nest-on-bed workflows with zero touches. Stage C: drift tracking and self-verification of the instruments |

## 2. The printer as a measuring machine

### 2.1 What limits it: the motion system, temperature and the reference

A sensor on the toolhead measures relative to the toolhead, so every printer error enters the measurement:

- **XY scale, skew and periodic error.** Belt-driven gantries carry systematic errors: rail skew, scale, rotation,
  bowed rails, backlash ([US patent 12691641 describes exactly this error set for a printer used as a measurer](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12691641));
  belt tension imbalance adds skew ([Ultimaker support](https://support.ultimaker.com/articles/Knowledge/Factor4-Skewed-X-beam)).
  printer_v12 has HIWIN MGNR12R rails (good straightness and repeatability) but GT2 belts: pulley eccentricity and tooth
  pitch error give a periodic error of a few tens of µm per pulley revolution, and belt stretch a scale error of the order
  of 0.05-0.2 % under acceleration loads **(est.)**. Uncorrected absolute XY: **50-150 µm over the bed (est.)**.
  Repeatability to a point approached from the same side: **5-15 µm (est.)**.
- **Correction.** Map the XY error once (and recheck monthly) by stepping the nozzle camera over a **glass dot-grid
  target** (chrome on soda-lime, a certificate of a few µm; tens to a few hundred USD (est.)): the camera measures the
  residual of each dot from the image centre, the map is a smooth 2D polynomial plus the pulley-period terms, and it is
  applied in software to every measurement (not in firmware). Expected residual after mapping: **15-40 µm (est.)**.
  A printed paper target is not good enough here: the scanner pipeline's target is itself only as good as a caliper
  reading of its 150 mm bar.
- **Z.** Lead-screw Z with POM nuts: fine resolution, some backlash; approach Z always from the same direction. Bed and
  gantry flex matter for tap (it pushes).
- **Temperature.** Aluminium (MIC-6 plate, sheet parts) grows 23 µm/m/K and PLA about 70 µm/m/K **(handbook values)**.
  A PLA part measured on a 60 °C bed reads about 0.25 % large (0.5 mm over 200 mm) compared with 23 °C. Rule: measure at
  a recorded bed and air temperature, at a fixed temperature where possible (bed off, cooled to < 30 °C, or held at 35 °C),
  and correct to 20 °C with the material's CTE, carrying the CTE uncertainty into the budget.
- **Reference.** Klipper's own advice is to check probe bias across XY and temperature with `PROBE_ACCURACY` at several
  points, cold and hot ([Klipper Probe_Calibrate](https://www.klipper3d.org/Probe_Calibrate.html));
  [zellneralex/probe_accuracy](https://github.com/zellneralex/probe_accuracy) automates the repeated test and charts it.
  The same discipline applies to every in-printer measurement.

### 2.2 Touch probing

- **Eddy tap (Z only, any material).** Klipper's mainline `[probe_eddy_current]` has a `tap` method: the nozzle touches
  and the probe detects the moment of contact; it has no thermal drift and no XY offset (HEIGHT_SENSING 1.2). Because
  the coil reads the steel sheet and plastic is transparent to it, tap works on top of a **plastic** part clamped or
  still stuck to the bed, giving the height of a top face at a point with a **cold, clean nozzle**. Repeatability is
  likely 5-20 µm (est.); no published figure for tap repeatability was found (Beacon's 0.5 µm figure is sensing
  resolution, not repeatability: [All3DP on Beacon Contact](https://all3dp.com/4/beacon-announces-beacon-contact-3d-printer-probing-system/)).
  Contact force is small (Beacon quotes < 30 g for its similar contact mode, [Beacon docs](https://docs.beacon3d.com/contact/)),
  but a loose part still moves: tap only parts that are stuck or nested. Over an **aluminium** part tap is unreliable,
  because the coil then sees the part instead of the sheet.
- **Eddy scan (conductive faces).** `rapid_scan` produces a dense height map at about 1 mm stand-off with sub-µm noise
  on steel (HEIGHT_SENSING 1.2). For a SendCutSend aluminium plate clamped to the bed it gives a flatness/bow map of the
  plate, after recalibrating the frequency-to-height curve **on aluminium** (the curve depends on the target material).
  The sensing footprint is about the coil diameter, so near edges, holes and bends the reading mixes part and sheet;
  trim a margin of about one coil diameter from every edge **(est.)**.
- **Lateral touch probe (later, optional).** Measuring hole walls and edges by touch needs a probe that triggers
  sideways: a three-ball kinematic touch probe with a ruby stylus (commercial ones repeat to about 1 µm; a DIY one to
  perhaps 5-10 µm (est.)) on a spare endstop input. Mainline Klipper has no G38-style "move until triggered in XY"
  command as far as this research found; a small Klipper extra or stepwise approach moves with `QUERY_PROBE` would be
  needed. The closest public project probes a part on the plate with a microswitch over a rectangle grid
  ([contour-probe](https://github.com/laneboysrc/contour-probe), self-described as crude). Because the nozzle camera
  measures edges without contact, this probe is low priority.

### 2.3 Laser-line triangulation from the toolhead

HEIGHT_SENSING section 3 sizes the nozzle camera plus VLM-520 laser as a triangulation sensor: about 14-27 µm per pixel,
2-6 µm with sub-pixel fitting, a speckle floor near 4 µm, so **5-10 µm real on opaque surfaces and 10-30 µm on
translucent plastic** (light scatters under the surface and biases the peak). Calibration is by stepping Z over a flat
plate and fitting row vs Z per column, which needs no angle measurement.

As a scanner: the line is about the camera's field (15-20 mm), so a part is covered in swaths. At 30 fps and 0.1 mm
between profiles the toolhead moves at 3 mm/s; a 100 x 100 mm part in seven swaths takes about 4 minutes **(est.)**.
The result is a **2.5D height map** (no undercuts, steep walls shadowed). That covers a lot:

| Measurand | How | Expected uncertainty (est.) |
|---|---|---|
| Printed part warp / corner lift | heights along the base perimeter vs the bed plane | 10-30 µm |
| Top-face flatness, step heights | plane fits, minimum-zone flatness | 10-20 µm |
| Bend angle of a sheet part | lay it V-up (both flanges visible), fit a plane to each flange, angle between normals | 0.05-0.2° (dominated by the Z-vs-XY scale calibration, not noise) |
| Outside bend radius | fit a cylinder to the bend zone of the same scan | 0.05-0.1 mm |
| Layer height, first-layer squish | profile across lines vs the bare-bed scan | 5-15 µm |

Published work does the same on material-extrusion printers with commercial blue-laser profilometers: layer height,
defects and surface quality from per-layer point clouds compared with the CAD-derived ideal cloud
([Int. J. Adv. Manuf. Technol. 127, 2023](https://link.springer.com/10.1007/s00170-023-11864-6)); overfill and
underfill maps layer by layer ([Fayazbakhsh group, TMU 2025](https://www.torontomu.ca/content/dam/frames/publications/Rana_Fayazbakhsh_2025.pdf));
single-pass roughness tracking ground truth closely ([arXiv 2210.15239](https://arxiv.org/pdf/2210.15239)). Open
turntable laser scanners (FabScan, Ciclop, FreeLSS) and a scanner built from printer motion parts
([NSF PAR 10174305](https://par.nsf.gov/servlets/purl/10174305)) show the same triangulation in a cheaper form. Note that
patents cover printers with a toolhead laser scanner and camera ([US 9172829](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9172829),
[US 9789649](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9789649)); for a private research cell
this is a note, not a blocker.

Safety: the laser is Class 1M; the cell rules already turn it off with the door open or the arm holding the lock
(ARM_SCOPE section 3). Scans are printer-only operations.

### 2.4 The nozzle camera and the top-down camera as measuring microscopes

- **Nozzle camera (16-19 µm/px, 15-20 mm field).** Edges found to 0.1-0.2 px give about 2-4 µm repeatability in the
  image **(est.)**. Accuracy is limited by three things: (1) the lens is not telecentric, so magnification changes about
  3 % per mm of height at a 35 mm object distance (est., from the thin-lens model in NOZZLE_CAMERA section 2): the height
  must be known, which the laser or the printer Z supplies; (2) lens distortion, removed by an OpenCV ChArUco calibration
  at a **fixed focus** (06_perception 2.1: autofocus is a metrology hazard); (3) stitching across images inherits the
  printer XY error of section 2.1. Lighting is the hard part on the bed: no backlight through the steel sheet, so edges of
  plastic parts are found against the textured PEI with a low-angle ring light; holes in plastic parts are measured as
  dark rims, which biases diameter by the edge-detection threshold **(calibrate with a ring gauge or a pin gauge on the bed)**.
  Camera-on-motion-system alignment is proven in toolchanger practice: TAMV and kTAMV use a Pi camera and machine vision
  to find nozzle XY offsets in Klipper/Duet ([kTAMV](https://github.com/TypQxQ/kTAMV),
  [Jubilee TAMV](https://jubilee3d.com/index.php?title=TAMV)), though no measured µm figures were published.
- **Top-down Pi Camera Module 3 (about 0.05 mm/px at best, 0.2-0.5 mm realistic, 06_perception 2.1).** Use it for
  presence, pose (where on the bed is the part, did it shift), gross shape, layer images; not for tolerances.
- **Flatbed scanner.** It remains the best 2D instrument in the cell for flat parts: synthetic tests show 0.01 mm on hole
  diameter and position with the dot target (INSPECTION section 2). In-cell automation keeps it, with the arm loading it.

### 2.5 A Klipper/Moonraker shape for measurement jobs

A measurement job is a G-code file like any print, so the queue, the CELL lock and the twin treat it the same way:

```
MEASURE_BEGIN JOB=<id> TEMP_BED=30          ; wait for bed/air temperature, laser enable interlock
LASER_SCAN X0=.. Y0=.. X1=.. Y1=.. STEP=0.1 ; macro: moves + camera trigger; frames streamed to the Pi
CAM_GRAB  X=.. Y=.. Z=.. LIGHT=ring          ; nozzle-camera stills at planned XY for edges/holes
TAP_POINT X=.. Y=..                          ; Eddy tap on top faces, n repeats
MEASURE_END                                  ; laser off; job id + temperatures + firmware hash logged
```

The macros only move and trigger; all processing runs in Python on the Pi or a workstation, reading frames and
`toolhead` positions through Moonraker. The inspection plan (`inspect_form/plans/<part>.json`) already lists which
dimensions matter; a planner turns each into a scan region, a camera station or tap points.

## 3. In-situ process monitoring during printing

| Signal | Detects | Published performance | Our implementation |
|---|---|---|---|
| Top-down / overview camera, CNN (Obico, formerly The Spaghetti Detective) | spaghetti, detachment, gross failure | No precision/recall published; Obico says it targets catastrophic failures, admits false positives (bed clips, reflections, logos) and that the threshold trades misses against false alarms ([Obico](https://www.obico.io/blog/how-obico-ai-failure-detection-works/), [false alarms](https://www.obico.io/docs/user-guides/failure-detection-false-alarms)) | Self-host Obico against Moonraker; log every alert and outcome to measure our own rates |
| Layer-change snapshot (toolhead parked) vs a render of the sliced layer | missing regions, layer shift, warp outline | Several vision papers; layer shift by comparing to G-code is simple image registration | Stage A: snapshot every layer; compare silhouette to the G-code's footprint rendered by `twin/render.py` |
| Nozzle camera, multi-head CNN (CAXTON) | flow, Z offset, hotend temperature, speed; online correction | Brion and Pattinson trained one network on 1.2 M images from eight printers and corrected errors across geometries, materials and printers ([Nat. Commun. 13, 4654, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646)) | ROADMAP phase 2-3 already: dataset first |
| Laser line, first layer (before/after) | first layer too high or too low, missing lines | Bambu's micro-lidar scans the bed, then layer 1; it flags a first layer above or below nominal; "7 µm resolution" is a marketing figure and users report mixed reliability on PEI ([Bambu wiki](https://wiki.bambulab.com/en/x1/manual/micro-lidar-model), [forum](https://forum.bambulab.com/t/first-layer-inspection-x1c/3909)) | Scan two or three strips across the first layer's skirt and part outline; compare to the bare-bed scan of the same strips; pass if mean line height is within ±0.05 mm of nominal **(est. threshold)** |
| Laser line, warp check every N layers | corner lift | CNN on camera images: 99.2 % over 16 tests ([Xi et al. 2022](https://www.torontomu.ca/content/dam/frames/publications/Xi_et_al_2022.pdf)); a Cambridge hybrid CNN also grades severity and adjusts settings ([Apollo](https://www.repository.cam.ac.uk/handle/1810/336241)) | Direct measurement is better than a classifier: profile the base corners at layer 5, 20, 50; a lift of > 0.2 mm **(est.)** pauses and flags |
| Eddy | not first layer of plastic (plastic is invisible), but **sheet seated** before a job, and bed shape | - | Already in ARM_SCOPE task A |
| ADXL345 on the toolhead | crashes, clogs (changed extruder vibration), loose parts, belt/bearing wear | Accelerometer on the extruder mount detects nozzle clogging; sensor near the nozzle reacts fastest ([Sensors 2019, PMC6603584](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6603584)); acoustic emission classified normal / runout / clog with > 90 % (LS-SVM) and filament breakage ([Yang et al. 2018](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5877116)) | Log windows of ADXL data through Klipper's accelerometer API during prints; build a per-move-type baseline; anomaly model later. Results are small lab studies, not comparable |
| SFS V2, TMC driver status | runout, jam, skipped steps | Driver stall detection for layer shifts is reported as unreliable ([Duet forum](https://forum.duet3d.com/post/140970)) | SFS already wired; do not rely on stallguard |

Two conclusions. First, none of the published accuracy numbers transfers: each was measured on its authors' printers,
lighting and failure mix. The cell should log every alert with the outcome (true failure, false alarm, missed failure
found at inspection) and report precision and recall per detector, the same way `record.py metrics` reports fidelity.
Second, the in-process data are themselves inspection data: a layer-height map and a first-layer verdict belong in the
measurement record with the part's job id.

## 4. A fixed inspection station the arm loads

ARM_SCOPE task B already places parts on the flatbed scanner. In order of value per dollar:

| Instrument | Measures | Expected performance | Cost (est.) | Notes |
|---|---|---|---|---|
| **Scale** under the drop bin and at the station (0.01 g, 200-500 g range) | mass vs slicer estimate: under-extrusion, missing layers, retained support, broken parts | a 50 g PLA part at 5 % under-extrusion is 2.5 g low, 250 x the resolution | $30-100 | The slicer's mass is only as good as the density setting ([MatterHackers](https://www.matterhackers.com/articles/quick-tip-using-filament-weight-to-avoid-3d-print-failures)); learn the per-profile ratio measured/estimated from history and flag outliers at 3 sigma. Weighing the printed object is patented as an in-print monitor ([US 12496769](https://patentsgazette.uspto.gov/week50/OG/html/1541-3/US12496769-20251216.html)); a post-print check is ordinary practice |
| **Flatbed scanner** | flat faces: holes, outline, slots | 0.01 mm synthetic (INSPECTION 2) | owned | Lid closing is an arm task, or replace the lid by a fixed light box the arm slides parts under |
| **Backlit silhouette camera**: LED panel + diffuser (or a telecentric backlight) under a glass plate, camera above with a **telecentric lens** | outlines of non-flat parts in several stable poses; hole positions through the part; bend profiles seen end-on | a telecentric lens removes magnification change with height, the main error of a normal lens; backlight gives the highest edge contrast ([Edmund Optics](https://www.edmundoptics.com/knowledge-center/application-notes/imaging/telecentric-illumination-why-you-need-it-in-machine-vision-applications/)). With a 5 MP global-shutter sensor over 60-100 mm: 20-40 µm/px, about 5-10 µm edge repeatability (est.) | $300-900 | Industrial reference: Keyence TM-X5000 uses dual telecentric optics ([Keyence](https://www.keyence.com/products/measure/micrometer/tm-x5000)). This is the "fixed metrology camera" in 06_perception 2.3 |
| **Kinematic nest on the printer bed** | the printer's laser, nozzle camera and tap measure any part the arm puts in it, in any pose, including flipped | as section 2 | printed nest + steel balls/dowels | The nest has three balls in three grooves (or three pins as A-B-C datum stops) and AprilTags; its pose is measured once with the nozzle camera. It realises the drawing's datum reference frame physically |
| **Turntable + structured light or laser** | true 3D: undercuts, all faces | open low-cost turntable systems exist; few report checked accuracy ([ORION, ISPRS 2017](https://isprs-archives.copernicus.org/articles/XLII-2-W8/155/2017/isprs-archives-XLII-2-W8-155-2017.pdf); a Pi photogrammetry rig checked against an ATOS 5 ([HCU 2024](https://repos.hcu-hamburg.de/bitstream/hcu/1091/1/isprs-archives-XLVIII-2-W8-2024-219-2024.pdf))). Desktop structured-light scanners claim 20-50 µm (vendor class, unverified) | $200-1000 | Last; only when a part needs it. Multi-view stitching and dark/shiny surfaces dominate the error |

**Fixturing.** Measurement repeatability is often limited by how the part sits, not by the sensor. Kinematic couplings
(three balls in three V-grooves) locate repeatably because each contact constrains exactly one degree of freedom; for
sheet parts a flat plate with 2 + 1 datum pins against which the arm pushes the part with a compliant finger realises
datums A (face), B (edge, two pins) and C (edge, one pin). A printed nest is good to perhaps 10-30 µm in repeat
placement (est.); put steel dowels or balls where the part touches. Each nest carries an AprilTag (06_perception 3) so
the cell knows which nest a camera sees.

## 5. Software: from point cloud or image to a tolerance verdict

### 5.1 Pipeline

1. **Acquire** with metadata: instrument id, calibration id, temperatures, job id, nest id, pose prior from G-code or nest.
2. **Coarse registration** from the prior (the G-code placement or the nest pose), else global registration (FPFH +
   RANSAC). Open3D documents this split: the initial alignment usually comes from global registration, then ICP refines
   ([Open3D ICP tutorial](https://www.open3d.org/html/tutorial/t_pipelines/t_icp_registration.html); library paper
   [arXiv 1801.09847](https://arxiv.org/pdf/1801.09847)).
3. **Fine registration by datum, not by best fit.** Whole-part ICP (point-to-plane, needs target normals) is right for a
   *deviation map* but wrong for *tolerances*: a best fit spreads a real error over the whole part and hides it. For
   GD&T, establish the datum reference frame the drawing names (primary plane by a constrained fit to datum A's points,
   secondary line on B, tertiary point on C) and evaluate features in that frame. Report both: the best-fit map for
   "where is it off", the datum frame for "is it in tolerance". The existing scanner code's rigid fit (`scan.register`,
   Kabsch on outline and holes) is a best fit; for position tolerances it should get a datum-frame option.
4. **Deviation map.** Signed distance from each scan point to the CAD mesh (Open3D `RaycastingScene.compute_signed_distance`,
   or `PointCloud.compute_point_cloud_distance` to a densely sampled CAD cloud, unsigned), coloured and saved like
   `<scan>.deviation.png`. CloudCompare does the same headless: `C2M_DIST` (cloud to mesh) and M3C2 (cloud to cloud,
   robust to noise, with a parameters file) in command-line mode
   ([CloudCompare command line](https://www.cloudcompare.org/doc/wiki/index.php/Command_line_mode),
   [C2M](https://www.cloudcompare.org/doc/wiki/index.php/Cloud-to-Mesh_Distance), [M3C2](https://cloudcompare.org/doc/wiki/index.php/PluginM3C2)).
   Recommendation: Open3D in-process (Python, already our stack); CloudCompare as an independent cross-check tool.
5. **Feature extraction**, each feature from the points the CAD says belong to it (segment by proximity to the CAD face
   after registration, which is far more robust than blind RANSAC segmentation):
   - **Hole** (2D image or 2.5D map): least-squares circle (already `_circle_fit`), plus max-inscribed circle for
     a functional (mating) size; two diameters for ovality near bends.
   - **Plane / flatness**: least-squares plane for orientation; **minimum-zone** flatness as a linear program
     (minimise t subject to all points within ±t/2 of a plane; `scipy.optimize.linprog`, a few lines). A best-fit plane
     over-reports flatness compared with the minimum zone the standard defines ([FARO on flatness](https://www.faro.com/en/Resource-Library/Article/how-to-evaluate-flatness-in-gd-t)).
   - **Cylinder** (true 3D only): RANSAC then least squares (PyRANSAC-3D, py-cylinder-fitting are used in a recent
     thesis comparing them with CloudCompare: [Aalto](https://aaltodoc.aalto.fi/server/api/core/bitstreams/528da405-7b59-4338-9133-aefa18cc1122/content)).
     A verified reference library of CMM fitting algorithms (least squares, minimum zone, min-circumscribed, max-inscribed)
     is described in [Mohan, ASU thesis](https://keep.lib.asu.edu/system/files/c7/113887/Mohan_asu_0010N_13765.pdf);
     use its test cases to verify our fits.
   - **Bend angle and radius**: planes on each flange (angle between normals), cylinder or arc on the bend zone.
6. **Tolerance evaluation**: size (diameter ± tol), position (2·sqrt(dx² + dy²) in the datum frame vs the position
   tolerance diameter, with MMC bonus when the drawing says so), flatness, angle. The plan JSON already stores nominal,
   tolerance and prediction; add the datum references and the feature-control frame.
7. **Uncertainty and verdict** (section 6), then **record** rows with `who="printer"` or `"arm"`, `method`, `u_mm` and
   `k`, and the calibration ids, so `record.py propose` can weight measurements by their uncertainty.

### 5.2 Uncertainty of a computed feature

Two complementary routes:

- **Monte Carlo (GUM Supplement 1 style).** Perturb the inputs by their uncertainties (point noise; instrument scale,
  distortion and XY-map parameters drawn from their calibration covariance; temperature and CTE), rerun the fit and the
  evaluation a few hundred times, take the spread of the output. Cheap for 2D fits; this is how the uncertainty of a
  hole position from a stitched nozzle-camera image is obtained honestly.
- **Substitution with a calibrated workpiece (ISO 15530-3).** Measure a calibrated artefact similar to the part with
  the same automated procedure many times; the difference from its certificate gives the bias and the scatter gives the
  procedure's repeatability, both carried over to production parts measured the same way
  ([ISO 15530-3:2011](https://www.iso.org/standard/53627.html); explanation in [arXiv 2606.09385](https://arxiv.org/pdf/2606.09385)).
  For mechloop: one "golden" sheet part and one printed artefact (holes, steps, a flat face, a 90° bend) measured once
  by an outside lab CMM, plus gauge blocks, a ring gauge and pin gauges for the simple features. This is also the
  cheapest way to remove **bias**, which is what corrupts learnings.

## 6. Measurement uncertainty, decision rules and gauge R&R for automated measurements

### 6.1 Decision rules

ISO 14253-1:2017 makes the decision rule explicit: conformance is proved only when the measured value lies inside the
specification by a guard band derived from the uncertainty; the current edition defaults to a 95 % conformance
probability ([ISO 14253-1](https://www.iso.org/standard/70137.html); background on the move from a full k = 2 guard band
to the 95th-percentile one, about 82.5 % of U in most cases, in
[Shakarji and Phillips, NIST](https://www.nist.gov/publications/understanding-ramifications-important-proposed-changes-decision-rules-three-standards)).
Choosing the rule is a business decision, uncertainty evaluation is a technical one
([Phillips and Krystek, NIST](https://www.nist.gov/node/570426)). For the cell: every verdict is **conform**,
**non-conform** or **undecided** (inside the guard band). Undecided parts go to a better instrument (scanner, outside
CMM) or to the human, and their count is a loop metric: fewer undecided parts means better instruments.

### 6.2 Is the instrument good enough? Type 1 study, then a crossed study

- **Type 1 (bias and repeatability).** Measure one reference (calibrated) part 25-50 times with full reload. Cg =
  (0.2·T)/(6·s) and Cgk = (0.1·T − |bias|)/(3·s), both >= 1.33 is the common acceptance
  ([JMP Type 1 gauge study](https://www.jmp.com/support/help/en/18.0/jmp/the-type-1-gauge-study-report.shtml)).
  This shows how demanding sheet-metal tolerances are: a SendCutSend hole at ±0.127 mm (T = 0.254 mm) needs
  s <= 0.0064 mm. The scanner's synthetic 0.01 mm figure would fail that until shown on real parts; a printed-part hole at
  ±0.3 mm needs s <= 0.015 mm, which the laser and nozzle camera may reach.
- **%GRR with no operators.** The classic AIAG bands (< 10 % acceptable, 10-30 % conditional, > 30 % unacceptable, and
  ndc >= 5; [Quality Magazine](https://www.qualitymag.com/articles/94385-gage-rr-repeatability-and-reproducibility))
  assume appraisers. In an automated cell the reproducibility factors are instead **reload** (pick, place, re-seat in the
  nest or on the glass), **day** (temperature, recalibration) and, for the arm, **placement pose**. Design: 10 parts that
  span the tolerance x 3 reloads x 3 days, measured by the automated job, ANOVA for part, reload, day and
  interactions; report %GRR of tolerance and ndc. Run it once per method and feature kind (hole diameter on the scanner;
  flatness by laser; bend angle by laser; mass), and again after any instrument change.
- **Attribute detectors** (spaghetti, first-layer pass/fail): precision, recall and Cohen's kappa against the
  confirmed outcome, on a held-out log; not %GRR.
- **Interim checks.** A check standard (a gauge block on the bed corner, the golden part in a nest) measured at the
  start of every measurement session; a control chart of its result catches drift. ISO 15530-3 includes reverification
  and interim checks in its scope ([DIN TOC](https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:146938600/toc-1853693/download)).

### 6.3 What matters for the learning loop

`record.py propose` flags a learning when a mean deviation exceeds twice its standard error. Instrument **noise** only
widens that standard error (more parts needed); instrument **bias** shifts the mean and produces false learnings
indistinguishable from real process biases. So, in order: (1) remove bias with calibrated artefacts and the substitution
method; (2) record `u` and the calibration id with every row so learnings can be recomputed when a calibration changes;
(3) only then chase repeatability. A learning proposed from automated measurements should state the instrument and its
last Type 1 result.

## 7. Recommended architecture

### Stage A: printer alone, now (zero added touches for printed parts)

1. **Pre-print**: Eddy confirms the sheet is seated (task A of ARM_SCOPE); laser scans the bare-bed strips under the
   first layer's outline.
2. **During print**: first-layer laser check after layer 1; top-down snapshot each layer with the G-code footprint
   overlay; warp profile of base corners at a few layers; Obico on the overview camera; ADXL345 windows logged; SFS V2.
   Detectors only pause and flag at first; their precision/recall is measured before any auto-cancel.
3. **Post-print, in place, before release**: the part is still fixed by adhesion at a known G-code pose, so no fixture
   is needed. Cool to the measurement temperature, then run a measurement job: laser height map of the part (height,
   top flatness, step heights, base warp), nozzle-camera stills of planned edges and holes, tap points on top faces.
   Write rows with `who="printer"`. Caveat: adhesion suppresses warp; record "on-bed" and "released" as different
   states, and in Stage B re-measure some parts after release to learn the difference.
4. **Sheet parts**: flatbed scanner as today (one human touch per scan); add a V-up laser scan on the bed for bend
   angles and outside radii, which replaces the square, feeler gauge and radius gauge (one touch to place, none to read).
5. **Instruments**: glass grid XY map of the printer, ChArUco calibration of the nozzle camera at fixed focus, laser
   Z calibration on a lapped plate or gauge blocks, Type 1 studies; a check standard on the bed.

Hardware to buy for Stage A: a glass dot-grid target, a small gauge-block set or a few grade-1 blocks, a ring gauge and
a pin-gauge set covering 3-8 mm, a 0.01 g scale; about $200-500 total **(est.)**. Software: `mechloop/inspect/`
modules for laser scans, camera stations, feature fits, datum-frame evaluation, Monte Carlo uncertainty and the
three-state verdict (to be written; nothing here is implemented yet).

### Stage B: with the arm (zero touches end to end)

1. Arm releases the part (task A), puts it on the **scale** (mass vs learned estimate), then routes it by the plan:
   flat face -> **flatbed scanner** (arm-operated lid or light box); non-flat profile -> **backlit telecentric
   station** in 2-3 stable poses; 2.5D features on any face -> **kinematic nest on the printer bed** for laser, camera
   and tap, flipping the part for the bottom face. Every placement is confirmed by camera (06_perception) and every
   nest by AprilTag.
2. Undecided parts go to a queue for the outside CMM or the human; non-conforming parts to a reject tray; all rows to
   the record with `who="arm"` and the method.
3. Gauge R&R reruns with arm reloads as the reproducibility factor (section 6.2); the arm's placement scatter becomes a
   measured input to the uncertainty.

### Stage C: self-verifying cell

Check standards in fixed nests measured automatically at every session start; control charts of the printer XY map,
laser scale and scanner scale; a drift beyond limits blocks measurement jobs and proposes a recalibration (a learning
like any other, with evidence). In-process signals (first-layer height, layer maps, mass ratios) are joined to final
inspection by job id so the twin can learn which process signals predict final dimensions, and inspection can later be
sampled rather than total for parts whose in-process signals were normal.

### Loop metrics this adds

Touches per part (target 0 for printed parts in Stage A except sheet parts, 0 for all in Stage B); fraction of
undecided verdicts; detector precision/recall; Cg/%GRR per method; instrument drift between check-standard readings;
inspection time per part.

## 8. Open questions

- Real tap repeatability on top of a stuck PLA part, and whether the part's compliance biases it: measure with
  `PROBE_ACCURACY`-style repeats on a gauge block vs on PLA.
- Laser bias on translucent PLA/PETG colours (HEIGHT_SENSING estimates 10-30 µm): characterise per filament with a
  printed step artefact measured by tap and by an outside CMM.
- Whether the printer's XY error map is stable enough over weeks to keep the 15-40 µm estimate.
- Arm-operated scanner lid vs a fixed light box: decide in the arm concept spike.
- Which outside lab measures the golden parts, and at what cost.

## Sources

- Klipper Probe_Calibrate: https://www.klipper3d.org/Probe_Calibrate.html
- probe_accuracy macro/script: https://github.com/zellneralex/probe_accuracy
- contour-probe (microswitch part probing): https://github.com/laneboysrc/contour-probe
- Beacon Contact docs: https://docs.beacon3d.com/contact/ ; All3DP article: https://all3dp.com/4/beacon-announces-beacon-contact-3d-printer-probing-system/
- US 12691641 (printing and measurement apparatus, gantry error set): https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/12691641
- Ultimaker skewed X beam: https://support.ultimaker.com/articles/Knowledge/Factor4-Skewed-X-beam
- Layerwise laser profilometry in MEX, IJAMT 127 (2023): https://link.springer.com/10.1007/s00170-023-11864-6
- Fayazbakhsh group, laser profiler in-situ (TMU 2025): https://www.torontomu.ca/content/dam/frames/publications/Rana_Fayazbakhsh_2025.pdf
- Data-driven FFF optimisation from in-situ measurements: https://arxiv.org/pdf/2210.15239
- Low-cost laser line scanner from printer motion parts: https://par.nsf.gov/servlets/purl/10174305
- Printer with laser line scanner patents: https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9172829 , https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9789649
- kTAMV: https://github.com/TypQxQ/kTAMV ; Jubilee TAMV: https://jubilee3d.com/index.php?title=TAMV
- Obico failure detection: https://www.obico.io/blog/how-obico-ai-failure-detection-works/ ; false alarms: https://www.obico.io/docs/user-guides/failure-detection-false-alarms
- Brion and Pattinson, Nat. Commun. 13, 4654 (2022): https://pmc.ncbi.nlm.nih.gov/articles/PMC9378646
- Bambu micro-lidar: https://wiki.bambulab.com/en/x1/manual/micro-lidar-model ; forum: https://forum.bambulab.com/t/first-layer-inspection-x1c/3909
- Xi et al. 2022 warping CNN: https://www.torontomu.ca/content/dam/frames/publications/Xi_et_al_2022.pdf ; Cambridge hybrid warp detection: https://www.repository.cam.ac.uk/handle/1810/336241
- Vibration-sensor FFF monitoring (Sensors 2019): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6603584 ; AE filament breakage (Sensors 2018): https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5877116
- Duet forum on stall detection for layer shifts: https://forum.duet3d.com/post/140970
- MatterHackers on filament/print mass: https://www.matterhackers.com/articles/quick-tip-using-filament-weight-to-avoid-3d-print-failures ; US 12496769: https://patentsgazette.uspto.gov/week50/OG/html/1541-3/US12496769-20251216.html
- Edmund Optics telecentric illumination: https://www.edmundoptics.com/knowledge-center/application-notes/imaging/telecentric-illumination-why-you-need-it-in-machine-vision-applications/ ; Keyence TM-X5000: https://www.keyence.com/products/measure/micrometer/tm-x5000
- ORION turntable (ISPRS 2017): https://isprs-archives.copernicus.org/articles/XLII-2-W8/155/2017/isprs-archives-XLII-2-W8-155-2017.pdf ; Pi photogrammetry vs ATOS 5 (2024): https://repos.hcu-hamburg.de/bitstream/hcu/1091/1/isprs-archives-XLVIII-2-W8-2024-219-2024.pdf
- Open3D ICP: https://www.open3d.org/html/tutorial/t_pipelines/t_icp_registration.html ; Open3D paper: https://arxiv.org/pdf/1801.09847
- CloudCompare command line: https://www.cloudcompare.org/doc/wiki/index.php/Command_line_mode ; C2M: https://www.cloudcompare.org/doc/wiki/index.php/Cloud-to-Mesh_Distance ; M3C2: https://cloudcompare.org/doc/wiki/index.php/PluginM3C2
- FARO flatness evaluation: https://www.faro.com/en/Resource-Library/Article/how-to-evaluate-flatness-in-gd-t
- Aalto thesis on Python cylinder fitting: https://aaltodoc.aalto.fi/server/api/core/bitstreams/528da405-7b59-4338-9133-aefa18cc1122/content ; Mohan ASU fitting library: https://keep.lib.asu.edu/system/files/c7/113887/Mohan_asu_0010N_13765.pdf
- ISO 15530-3:2011: https://www.iso.org/standard/53627.html ; measurement uncertainty introduction: https://arxiv.org/pdf/2606.09385 ; DIN TOC: https://www.din.de/de/mitwirken/normenausschuesse/natg/veroeffentlichungen/wdc-beuth:din21:146938600/toc-1853693/download
- ISO 14253-1:2017: https://www.iso.org/standard/70137.html ; Shakarji and Phillips (NIST): https://www.nist.gov/publications/understanding-ramifications-important-proposed-changes-decision-rules-three-standards ; Phillips and Krystek (NIST): https://www.nist.gov/node/570426
- JMP Type 1 gauge study: https://www.jmp.com/support/help/en/18.0/jmp/the-type-1-gauge-study-report.shtml ; Quality Magazine gage R&R: https://www.qualitymag.com/articles/94385-gage-rr-repeatability-and-reproducibility
