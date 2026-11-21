# Arm research 06: perception, calibration and measurement (2026-11-21)

Scope: how the arm we design ourselves sees, calibrates itself, feels contact, and how we measure its own repeatability
and accuracy cheaply so the numbers feed the learnings ledger (`mechloop/inspect/record.py`) and correct the arm's
digital twin the same way `mechloop/twin/calibration.py` treats the printer: predict first, measure, then propose a
recalibrated parameter set with uncertainty, never silently overwrite.

Prices are approximate (late 2026, single units, USD unless stated). Prices marked "(search)" came from retailer
listings found in this research; prices marked "(approx.)" are from general knowledge and must be checked before
ordering. Accuracy figures marked "estimate" are worked out here, not measured; they are predictions to be tested.

## 1. Recommendations in one table

| Question | Recommendation | Why |
|---|---|---|
| Wrist camera? | Yes, one small **global-shutter mono** camera on the last link, **USB UVC**, fixed focus, with a ring of LEDs | Close-range fiducial reads give 10-50 µm lateral resolution where the overview camera gives ~0.3 mm; global shutter allows reading while moving; the Pi 5's two CSI ports are already used by the overview and top-down cameras and a round USB cable flexes through joints better than a ribbon (the same reasoning as `docs/NOZZLE_CAMERA.md`) |
| Fixed cameras? | Keep the existing Pi Camera Module 3 overview and top-down cameras for coarse work (is the print there, did it fail, where is the tray) | Already in the cell; no new hardware |
| Fiducials | **ChArUco** boards for intrinsic and hand-eye calibration; **AprilTag 36h11** for identity and pose of beds, trays, fixtures; both laser-printed on paper and bonded to flat aluminium or glass, never printed in plastic for metrology | ChArUco gives many sub-pixel corners and tolerates partial views; AprilTag 36h11 has the lowest false-positive rate; printed plastic is neither flat nor dimensionally trustworthy to <0.1 mm |
| Hand-eye method | OpenCV `calibrateHandEye` (Park or Daniilidis) as an initial value, then a **joint bundle adjustment** of hand-eye transform plus kinematic parameters | With a printed arm the kinematic error is larger than the hand-eye error; calibrating them separately makes the hand-eye transform absorb kinematic errors |
| Finding prints and parts | Prior knowledge first (G-code footprint, tray CAD with kinematic pockets and a tag per tray), vision only to confirm and correct; final millimetre by chamfers and compliance | Fixtures beat vision on cost and reliability; the cell already knows where every print should be |
| Force sensing | Phase 1: joint current (free) plus **one single-axis load cell** on the tool axis with a **NAU7802** (or ADS1220) amplifier, ~$20. Phase 2 if insertion data demand it: a DIY 6-axis wrist (TAMS printed design) before any commercial F/T sensor | Insertion and screwdriving are dominated by the tool-axis force and torque; commercial 6-axis sensors cost $4k-12k, more than the arm |
| Measuring the arm | ISO 9283 5-pose / 30-cycle protocol with three instruments cross-checking: (a) three dial indicators on a tool ball, (b) the flatbed scanner measuring placed tokens, (c) the printer's own camera/motion as a reference stage | Dial indicators give µm-level truth at one pose; the scanner gives 2D place repeatability and accuracy over 200 x 300 mm reusing our existing pipeline; the printer is a free precision positioner already in the cell |
| Twin correction | Identify joint offsets, link lengths, joint axis misalignments, gear backlash and joint stiffness by least squares, validate leave-one-out, write a `PROPOSED` learning with before/after error | Same discipline as `record.py` and `twin/calibration.py` |

## 2. Cameras: on the arm vs fixed

### 2.1 What the existing cell cameras can and cannot do

The overview and top-down Pi Camera Module 3 units (Sony IMX708, 4608 x 2592, 1.4 µm pixels, autofocus, ~$25 standard,
~$35 wide (approx.)) see the whole bed. Over a ~250 mm field at 4608 px that is ~0.055 mm/px at best; realistically,
with lens distortion, autofocus changing the intrinsics, and viewing angle, 0.2-0.5 mm absolute position on the bed is a
fair estimate. That is enough to tell "print present / absent / spaghetti", to find a tray, and to give the arm a
starting estimate. It is not enough to place a 3 mm pin in a 3.1 mm hole.

**Autofocus is a metrology hazard.** The IMX708's lens moves with focus, which changes focal length and distortion. For
any camera used for measurement, set a fixed lens position (libcamera `AfMode=Manual`, `LensPosition=<diopters>`),
calibrate at that position, and record the lens position in the calibration file. Recalibrate if it changes.

### 2.2 Wrist camera

A camera on the arm's last link (eye-in-hand) brings the sensor close to whatever matters: at 100-200 mm it resolves
0.05-0.1 mm per pixel even at 1 MP, it sees fiducials head-on (the best case for pose accuracy, see 3.2), and it moves
with the tool so occlusion by the arm itself is not a problem. Its costs: it adds mass and a cable at the wrist, it
needs hand-eye calibration, and its pose is only as good as the arm's kinematics unless it measures relative to a
fiducial near the target (which is the main way to use it: "look at the tray tag, then move relative to the tag").

Requirements for the wrist camera:

- **Global shutter** so tags can be read while the arm moves or vibrates after a move (a rolling shutter skews the
  image by the motion during readout and biases pose).
- **Mono** sensor (no Bayer demosaic softening corners); a ring of white or 850 nm LEDs with a matching filter makes
  exposure independent of room light.
- **Fixed focus** M12 or C/CS lens, glued once focused.
- **USB UVC** interface: both Pi 5 CSI ports are taken by the overview and top-down cameras, and USB cable flexes
  through a cable chain or along links better than an FFC. The Pi 5's USB 3 ports have the bandwidth.

| Camera | Maker | Sensor / shutter | Resolution, pixel | Interface | Price | Fit |
|---|---|---|---|---|---|---|
| OV9281 1 MP mono global shutter module | Arducam (also Waveshare OV9281-110/120/160) | OmniVision OV9281, global | 1280 x 800, 3 µm | CSI (Arducam also sells a USB UVC version) | $26 CSI (search); USB UVC version ~$50-70 (approx.) | **Recommended wrist camera** in its USB UVC form: small, light, fast (120 fps), mono global shutter |
| Global Shutter Camera | Raspberry Pi (SC0926) | Sony IMX296, global | 1456 x 1088, 3.45 µm | CSI | $50 launch; $38-64 retail (search) | Best image quality per dollar, C/CS lens, but 38 x 38 x 20 mm plus lens is heavy for a small wrist and needs CSI: better as a **fixed metrology camera** for the arm-measurement station |
| IMX296 M12 mono | Waveshare | IMX296, global | 1456 x 1088 | CSI | $63 (search) | Same sensor, smaller M12 lens |
| Camera Module 3 | Raspberry Pi | IMX708, rolling, AF | 4608 x 2592, 1.4 µm | CSI | ~$25 (approx.) | Already in the cell as fixed cameras; poor wrist choice (rolling shutter, autofocus, CSI) |
| B0454 / B045401 USB modules | Arducam | OV5648, rolling | 2592 x 1944 | USB UVC | $39-62 (see NOZZLE_CAMERA.md) | Fallback if no global-shutter USB unit is stocked; read only when stationary |

Estimate for the OV9281 with a ~3.6 mm lens at 150 mm: horizontal FOV ~160 mm, ~0.125 mm/px. With sub-pixel corner
refinement at ~0.05-0.1 px, a single corner is located to ~6-12 µm laterally, and a ChArUco board with 20-50 corners
gives board position repeatability of a few µm laterally and tens of µm in depth (depth is always weaker for a single
camera; the depth error grows roughly with distance squared over focal length times board size). These are estimates:
the first job of the arm-measurement station (section 7) is to measure them.

### 2.3 Fixed metrology camera

For measuring the arm itself, one fixed IMX296 (Raspberry Pi Global Shutter Camera with a 6-16 mm C-mount lens,
~$50 + $25-50 lens) looking at a ChArUco plate or tag cube on the arm's tool gives a second, independent measurement
of tool pose. It can plug into a CSI port temporarily (swap with the top-down camera during a calibration run) or into
a second Pi. It is cheaper than any commercial tracker and good to tens of µm laterally over a small volume.

## 3. Fiducials

### 3.1 Which marker for what

| Marker | Use in the cell | Notes |
|---|---|---|
| **ChArUco** (chessboard with ArUco markers in the white squares) | Camera intrinsics; hand-eye calibration; the reference plate in the arm-measurement station | Chessboard corners are saddle points, refined to sub-pixel far better than marker corners; the ArUco IDs let partially visible boards still be used. A 2026 study found ChArUco gives lower translation and rotation errors than ArUco for hand-eye because each ArUco marker gives only four corners [strawberry arXiv 2606.28555]. An online ChArUco hand-eye method reports 0.4-0.6 mm accuracy, matching offline methods [PMC9147787] |
| **AprilTag 36h11** | Identity and pose of printer bed / build sheet, trays, fixtures, the scanner glass, the screw feeder | Very low false-positive rate; robust detection; supported by OpenCV (ArUco module includes AprilTag dictionaries) and `pupil-apriltags` / `apriltag` Python bindings. Pose error grows with distance and off-axis angle; head-on views are best [Abbas et al., Sensors 2019] |
| ArUco 4x4/5x5 | Small, cheap IDs where a tag must be tiny (part carriers) | Weaker error correction than 36h11 |
| Our dot grid (`inspect/scan.py`, 10 mm pitch, 2 mm dots) | Scale reference in scanner images, including the arm-placement test in 7.3 | Already built and tested: affine fit, residuals give non-linearity |

Rules for metrology fiducials:

1. **Print on paper with a laser printer** (or have them printed on photo paper / dibond by a print shop), check the
   scale with calipers against a printed 150 mm bar (as `docs/INSPECTION.md` already does for the scan target), and
   bond to a flat substrate: 3 mm aluminium, a glass tile, or a ground steel plate. Record the measured square size,
   not the nominal, in the board definition.
2. **Do not 3D-print fiducials for measurement.** Two-colour printed tags are fine for identity (which tray is this),
   but their flatness, edge sharpness and scale (shrinkage 0.2-0.5 %) are not good enough for pose to <0.1 mm.
3. Size tags so the smallest one spans at least ~40-60 px in the camera that reads it; at the wrist camera's
   ~0.125 mm/px, a 10 mm tag is ~80 px.
4. Put three or more tags on anything whose pose matters (bed, tray, scanner) rather than one large tag: three
   separated tags give orientation from their positions, which is much better than one tag's own orientation estimate.

### 3.2 Expected accuracy

Published AprilTag studies at room scale report centimetre errors at 1-2 m [arXiv 2502.03510] and show accuracy improving
sharply at short range and with head-on views [Abbas et al.; arXiv 2305.05673]. The cell works at 0.1-0.4 m, so with
calibrated, fixed-focus cameras the realistic figures are (estimate): wrist camera at 150 mm on a tag cluster,
0.02-0.05 mm lateral and 0.1-0.2 mm depth; fixed overview camera at 400-600 mm, 0.2-0.5 mm.

## 4. Hand-eye calibration

### 4.1 The problem

- **Eye-in-hand** (wrist camera): find X, the camera pose in the flange frame, from pairs (flange pose A_i from
  kinematics, board pose B_i from the camera): solve AX = XB.
- **Eye-to-hand** (fixed camera) and the **arm-to-printer / arm-to-scanner** transforms: robot-world-hand-eye,
  AX = ZB, solved for both the camera-in-world and target-in-flange transforms at once.

OpenCV provides both: `cv2.calibrateHandEye` with methods Tsai, Park, Horaud, Andreff and Daniilidis, and
`cv2.calibrateRobotWorldHandEye` with Shah and Li. Studies disagree on which classic method is best (Park often edges
Tsai in simulation [arXiv 2406.11392]); the differences are small next to the effect of pose diversity and
robot accuracy, so try two methods and compare residuals.

### 4.2 Procedure for our arm

1. Calibrate intrinsics first (ChArUco, 20-40 images covering the whole sensor and tilted ±45°, reprojection error
   target <0.2 px; record lens position if autofocus).
2. Collect 15-30 poses with **large rotations about at least two non-parallel axes** (>30° between poses); pure
   translations make AX = XB degenerate.
3. Solve with Park and Daniilidis; reject poses with high residual; report rotation residual (deg) and translation
   residual (mm).
4. **Then refine jointly with the kinematic calibration** (section 8): unknowns = hand-eye transform + board pose in
   world + kinematic parameter errors; residual = predicted vs observed image corner positions (a bundle adjustment
   in pixel space, which weights good observations correctly). With a printed arm whose uncalibrated absolute error
   may be several millimetres, calibrating hand-eye alone would push those errors into X.

### 4.3 Achievable accuracy

Hand-eye accuracy is bounded by the arm's own pose accuracy. Industrial arms with ChArUco get 0.4-0.6 mm
[PMC9147787]. For our arm expect 1-3 mm before kinematic calibration and roughly the arm's calibrated accuracy after
(0.3-1 mm, estimate). That is why the cell should rely on **relative** measurements: the wrist camera reads a tag
next to the target and the arm moves relative to that tag, so absolute arm error mostly cancels; only the
repeatability and local accuracy over a few centimetres matter.

## 5. Locating prints on the bed and parts in trays

### 5.1 Prints on the bed

The cell already knows where each print should be: the slicer's G-code gives the footprint, the twin renders the part,
and Klipper knows the bed position. The chain:

1. **Printer to arm frame.** Three AprilTags on the printer frame (or on the build-plate carrier) are read by the
   wrist camera at the start of each session ("touch-up"). If the bed moves (a bed-slinger Y axis), command it to a
   fixed park position first. A change of more than a threshold (e.g. 0.3 mm) from the stored transform raises a
   flag instead of silently re-zeroing: something got bumped.
2. **Is the print there and intact?** The top-down camera compares the observed silhouette with the rendered
   expected silhouette (difference image or IoU); a failed print or spaghetti fails the check and the arm does not
   grab.
3. **Where exactly?** Prints on a PEI sheet are where the G-code put them to within the sheet's placement error
   (sheets on magnetic beds locate on pins to ~0.2-0.5 mm). The wrist camera looks at the print from above and
   matches its edges to the expected outline (2D ICP like `scan.py`'s registration step), giving a sub-millimetre
   grasp pose.
4. **Height.** The printer's Class 1M line laser plus a camera gives a triangulated height profile; it also catches
   prints that warped or detached.

A design option that removes most of this: the arm lifts the whole spring-steel sheet off the bed (kinematic
pins plus a handle tab with a tag), flexes it at a fixture to release the parts, and replaces it. The sheet's pose is
then known by fixture design, not vision.

### 5.2 Parts in trays

Trays should be printed with **one pocket per part** (draft and chamfers so a 1-2 mm placement error self-corrects),
**kinematic location** on the table (three balls in three V-grooves, or two pins in a hole and a slot), and an
**AprilTag that encodes the tray type**; the tray CAD then gives every pocket's pose. The wrist camera reads the tag
(or tags) to correct the tray pose, then optionally verifies the pocket is occupied. Off-the-shelf parts (screws,
nuts, bearings, pins) come from a feeder or a pocket tray rather than a bin: bin picking needs depth sensing and
grasp planning that this cell does not need.

### 5.3 The last millimetre

Vision gets within ~0.2-0.5 mm; chamfers, compliance and force feedback do the rest (section 6). The design rule for
printed parts that the arm assembles: lead-in chamfers at least 2x the expected placement error, and a known insertion
force window.

## 6. Low-cost force and torque sensing

### 6.1 What the tasks need

| Task | Signal that matters | Range / resolution |
|---|---|---|
| Unloading a print (detaching from PEI) | Tool-axis force, slip | 5-50 N, ~0.5 N |
| Pin / bearing insertion | Tool-axis force vs depth; lateral force to detect jamming | 2-50 N axial, ~0.1-0.2 N |
| Press-fit | Force-displacement curve (accept if within an envelope) | up to 50-100 N |
| Screwdriving M2-M4 | Driver torque, axial force, turn count | 0.05-1 N·m, axial 5-20 N |
| Contact detection (touch-off, collisions) | Any force jump | ~0.5 N |

Most of this is one axis (the tool axis) plus torque about that axis. A full 6-axis sensor helps with search
strategies (spiral search for a hole, tilt correction), but it is not where to start.

### 6.2 Options

| Option | Example products | Approx. price | Resolution / notes |
|---|---|---|---|
| **Joint motor current** | Any FOC BLDC driver (moteus, ODrive, SimpleFOC boards) reports current; TMC2209/TMC5160 stepper drivers give StallGuard load values | $0 extra | Coarse: friction, gear efficiency and cogging dominate, especially through high-ratio gearing; useful for collision and contact detection. Model-based estimation is "highly sensitive" to friction errors [FACTR 2, arXiv 2606.12406] and inaccurate during dynamic motion [Yen et al., Sensors 2019]; a 2026 preprint shows usable wrench estimates and admittance control from servo / QDD current after calibrating torque constants [arXiv 2603.00913]. Quasi-direct-drive joints (ratio <10:1) make this far better |
| **Screwdriver motor current + encoder** | Small geared DC motor with encoder (e.g. Pololu micro metal gearmotor with encoder) and a current-sense driver | $20-40 (approx.) | Torque ~ current x Kt x ratio x efficiency; seating shows as a current spike after N turns; calibrate on a torque screwdriver once |
| **Single-axis load cell + amplifier** | TAL220 straight-bar cells (SparkFun, 1-10 kg); button / S-type cells; amplifier NAU7802 (SparkFun Qwiic Scale) or HX711 | Cell ~$8-15 (approx.); NAU7802 board $6, HX711 board $11.50 (SparkFun, search) | NAU7802: 24-bit, I2C, up to 320 SPS, shares the bus; HX711: 10/80 SPS, bit-banged, interference-prone (SparkFun reviewer anecdote). For faster or multi-channel: TI ADS1220 (2 kSPS, SPI) or ADS131M04 (4 simultaneous channels, for a DIY multi-axis sensor), ~$5-10 chip |
| **DIY 6-axis** | TAMS printed F/T sensors (OpenSCAD + software, optical, < $20 parts) [github.com/TAMS-Group/tams_printed_ft]; Ouyang & Howe webcam + fiducial F/T sensor [arXiv 2005.14250]; machined-aluminium strain-gauge cross with an ADS131M04 | $20-150 | The TAMS approach fits mechloop well: we print the flexure, our twin predicts its stiffness, and calibration against known weights is a learning in its own right. Expect ~0.1-0.5 N resolution, drift and hysteresis from the printed flexure |
| **Commercial small 6-axis** | Bota Systems MiniONE / MiniONE Pro; ATI Nano17 (±50 N, 0.0125 N resolution); OnRobot HEX-E; Robotiq FT 300-S | Bota: quote (a Korean reseller lists MiniONE Pro at ~KRW 16.3 M, ~$11-12k); ATI: quote (typically several $k); OnRobot HEX-E $3,938 (Vention); Robotiq FT 300-S ~$10,600 (reseller) | Excellent, but each costs more than the arm. Keep as a later reference instrument for calibrating the DIY sensor if the project ever borrows one |

### 6.3 Recommended path

1. Design the joints with current sensing (a choice for researcher on actuators); use it for contact and collision
   detection from day one.
2. Put a **single-axis load cell in the tool axis** (between the wrist flange and the gripper / driver, with an
   overload stop) read by a **NAU7802** at 80-320 SPS, or an ADS1220 if faster control loops are needed. Calibrate with
   known weights; record the calibration as a measurement row.
3. A small motorised screwdriver with encoder and current sense for screws; torque calibrated once against a
   torque screwdriver or a lever arm on the load cell.
4. Log every insertion as a force-depth curve; these curves are the evidence for press-fit allowance learnings
   (e.g. "PETG 3.0 mm pin in printed 3.0 mm hole: insertion force 18 ± 4 N, n=12"), which feed hole allowances in
   `mechloop/tolerance/process.py` just as scanner measurements do.
5. Only if insertion failures show lateral jams that the axial signal cannot detect, build the TAMS-style printed
   6-axis wrist.

## 7. Measuring the arm's own repeatability and accuracy cheaply

### 7.1 The ISO 9283 protocol (adapted)

ISO 9283 (current edition 1998) defines, among others, pose accuracy (AP), pose repeatability (RP), distance
accuracy, pose stabilisation, drift and path performance. The core pose test:

- Choose a test cube in the most-used part of the workspace (for our arm perhaps 100-150 mm on a side; a low-cost
  arm study used a 250 mm cube [arXiv 2502.16908]).
- Five poses on a diagonal plane of the cube: P1 at the centre, P2-P5 near the corners (at 10 % of the diagonal
  from them).
- Visit P1 -> P5 in sequence, **30 cycles**, approaching each from the same direction, at the speed and payload
  stated.
- For each pose: barycentre of the 30 attained positions; **RP = l̄ + 3 S_l**, where l̄ is the mean distance of the
  attained positions from the barycentre and S_l the sample standard deviation of those distances [arXiv
  2010.05247; Hexagon ISO 9283 basics]. Orientation repeatability is ±3σ of each angle.
- **AP** = distance from the commanded position to the barycentre (needs the measurement in the arm's frame,
  hence a registered instrument).

Add three cell-specific tests on top: approach from opposite directions (exposes backlash directly); hang known
weights (0.2, 0.5, 1 kg) at the tool and record deflection (joint and link stiffness for the twin); and repeat the
RP test cold and after 1-2 h of running (thermal drift of printed links and motors).

### 7.2 Instruments, from cheapest to most informative

| Instrument | What it measures | Resolution | Cost | Notes |
|---|---|---|---|---|
| **Three dial / digital indicators on a tool ball** | 3D repeatability at one pose, backlash, stiffness under load, drift | 1-10 µm | Mitutoyo 2046A (10 mm, 0.01 mm) ~£45-81 ex VAT (RS, search); generic digital indicators ~$20-30 (approx.); magnetic bases ~$15 each; a 20-25 mm bearing ball ~$3 | The classic method: tool holds a precision ball (or a ground cube), three indicators on orthogonal axes touch it. Only one pose at a time and it measures repeatability, not accuracy. The best "truth" we can afford. A cube is easier (flat faces give clean x, y, z readings); a ball makes the reading insensitive to small orientation changes |
| **Electrical-contact or microswitch touch probe** | Repeatability and local accuracy by touching fixed reference surfaces | ~1-5 µm repeatable for a good kinematic probe | $5-30 | A conductive tool ball touching a grounded steel block, sensed as continuity, is the cheapest µm-level probe; move slowly toward the block and record joint positions at contact. A three-ball kinematic (Renishaw-style) DIY probe is another option. Lets the arm measure a printed or machined reference artifact |
| **Flatbed scanner + placed tokens** | 2D place repeatability and accuracy (x, y, θ) of the whole pick-and-place chain, over ~210 x 297 mm | ~10 µm per feature with sub-pixel edges and the dot-grid target (our synthetic tests: 0.01 mm on hole position, `docs/INSPECTION.md`) | $0 (scanner exists) | See 7.3. The most relevant number for this cell: where the arm actually puts a part, including gripper slop |
| **Wrist camera on a fixed ChArUco plate** | 6D pose of the camera at each test pose, in the plate frame | lateral ~5-20 µm, depth ~20-100 µm (estimate, to be verified against the indicators) | $0 extra once the wrist camera exists | Fast: hundreds of poses in an hour, enough for kinematic calibration. Measures the camera, so hand-eye error enters accuracy (not repeatability) |
| **Fixed IMX296 camera on a tag cube held by the arm** | Same as above, independent of hand-eye | similar | ~$75-100 | A second, independent opinion |
| **The printer as a reference stage** | Arm accuracy over the printer's XY area, in the printer's frame | the printer's positioning, ~0.01-0.05 mm (to be measured) | $0 | The nozzle camera (or the top-down camera) on the gantry is driven by Klipper to known coordinates and images a tag or a sharp crosshair on the arm's tool; or the arm brings its tool ball under the printer's bed probe / a dial indicator on the toolhead. The printer becomes a cheap 2- or 3-axis CMM for the arm, and the arm-to-printer transform is calibrated as a by-product |
| Line laser + camera | Height profile of tool or reference objects | ~0.05-0.1 mm (estimate) | $0 (in cell) | Mostly for prints; useful for checking Z of a placed part |
| Laser tracker, Renishaw ballbar, commercial CMM | Reference-grade | µm | $10k-100k+ | Out of scope; a DIY ballbar (two magnetic sockets and a linear indicator on a printed bar) is possible later |

### 7.3 The scanner placement test (uses what we already have)

1. A token: a flat 40 x 40 mm aluminium or acrylic plate (laser-cut, or machined from SendCutSend-class stock that
   the inspection pipeline already handles), with two holes and an asymmetric notch so its pose is unambiguous.
2. A cut strip of the existing dot-grid target taped to the glass, plus two or three AprilTags on the scanner frame
   so the arm's wrist camera can register the scanner to the arm.
3. The arm picks the token from a fixture and places it on the glass at commanded poses (a 3 x 3 grid and the five
   ISO poses projected to the glass), lifts clear, the scanner scans at 600 dpi, the arm picks it again. 30 cycles
   per pose overnight.
4. `inspect/scan.py`'s calibration (dot grid) and registration (holes + outline, rigid fit) give each token pose in
   millimetres; repeatability and accuracy follow from the spread and from the offset to the commanded pose.

This measures the number the cell cares about (where does a part end up?) including gripper compliance and part slip,
and reuses tested code. Its limits: 2D only, the lid must be closed or the room dark for good contrast (scan with the
lid open and a black cloth over the area, or use a lid-down approach where the token is dark on a light background),
and it measures place-on-glass, not insertion.

### 7.4 What to measure for every arm revision

| Metric | Method | Target to state in each design (prediction) |
|---|---|---|
| Pose repeatability RP at 5 ISO poses | indicators at P1, camera at all five | e.g. ≤0.1 mm |
| Place repeatability (x, y, θ) | scanner tokens | e.g. ≤0.2 mm, ≤0.2° |
| Pose accuracy AP before and after calibration | wrist camera on plate + printer stage | e.g. 2 mm -> 0.5 mm |
| Backlash per joint | bidirectional approach, indicators | arcmin per joint |
| Stiffness at tool | hanging weights, indicators | µm/N in x, y, z |
| Thermal drift | RP cold vs warm | µm over 2 h |
| Force sensor calibration | known weights | N per count, offset drift |

Each design states its predicted values from the twin before it is built; the measured values then score the twin,
as `twin/calibration.py` does for printer resonances.

## 8. Kinematic calibration and the digital twin

### 8.1 Error model

Parameterise the arm with modified DH or, better for nearly parallel axes, product-of-exponentials (POE), and add:

- joint zero offsets (usually the largest error after assembly; for printed arms, also homing-switch repeatability);
- link lengths and twist / axis misalignments (printed parts are 0.2-0.5 % off scale and warp);
- gear backlash per joint (a dead band, direction dependent);
- joint stiffness (deflection proportional to gravity torque: a big term for printed links and belt or cycloidal
  reducers);
- optionally encoder eccentricity (a once-per-revolution sine) and gear transmission error.

### 8.2 Identification

Collect 50-200 poses measured by the wrist camera on a fixed ChArUco plate (plus touch-probe points on a reference
artifact for absolute scale), each pose approached from a consistent direction, with gravity load computed from the
twin. Solve by Levenberg-Marquardt on stacked residuals (scipy `least_squares`), with the hand-eye transform and plate
pose as unknowns (section 4.2). Choose poses to maximise an observability index; drop parameters that are not
identifiable rather than letting them soak up noise. A 2024 study on a lightweight manipulator found that DH
identification significantly improves 6D accuracy and that the choice among algorithms matters little [BPASTS 2024];
the measurement data and pose selection matter more.

Expected gains from the literature: 5.71 mm -> 0.29 mm average with low-cost motion capture against a laser tracker
reference; ~10 mm -> 0.2 mm for Franka and KUKA arms; 0.33 mm mean after calibration of a KUKA KR6 with a low-cost
device [search results summarised in Sources]. A camera-based calibration of a low-cost educational arm was reported by
a University of Ljubljana group [Čehovin Zajc, ERK 2019]. For our printed arm, a fair prediction is several mm before
calibration and 0.3-1 mm after, with repeatability (backlash, stiffness, homing) as the floor no calibration can beat.

### 8.3 How measurements feed the ledger and the twin

Follow the existing pattern exactly:

1. **Measurement rows.** Every arm measurement is a row like `mechloop/data/measurements/measurements.jsonl`: arm
   revision, joint/test id, kind (`arm_rp`, `arm_ap`, `arm_backlash`, `arm_stiffness`, `place_xy`, `insert_force`,
   `ft_calibration`), nominal / predicted / measured, unit, method (`iso9283_indicators`, `scanner_token`,
   `wrist_charuco`, `printer_stage`), instrument (with its own calibration id), who, when, raw-data path.
2. **Twin parameters with uncertainty.** A `fitted_parameters`-style file for the arm (the printer has
   `mechloop/twin/fitted_parameters.json`) holding each identified parameter with its standard error and the data it
   came from. The twin's defaults are not changed by identification: it produces a PROPOSED set.
3. **Learnings.** A systematic deviation becomes a PROPOSED learning in `mechloop/data/learnings/ledger.jsonl` with
   evidence, the target it would change, and the prediction error before and after, **leave-one-out** (record.py's
   rule: a learning is not credited with fitting its own data). Two kinds:
   - *instance learnings*: "arm r3 joint 2 zero offset +0.41° ± 0.03°" (applies to this physical arm; goes into its
     calibration file);
   - *design learnings*: "printed PETG 15 mm-wide link, 120 mm long: stiffness 0.6 of predicted (n=3 links)", "GT2
     belt reduction backlash 6 arcmin vs predicted 2" - these change the twin's material and joint models, so the
     **next arm design** is predicted better. This is the recursive part of mechloop: the arm measures itself, the twin
     learns, the next arm revision is designed with the corrected twin.
4. **Accepting a learning** stays the owner's or parent agent's call, as for every other learning.
5. **Drift watch.** A short daily check (wrist camera reads the bed and scanner tags, plus RP at P1 with 5 cycles)
   is recorded as rows; a trend beyond its uncertainty proposes recalibration rather than applying it silently.
6. **Loop metrics.** Fidelity = |predicted - measured| per arm metric against |nominal - measured| as the do-nothing
   baseline, and autonomy = manual steps per calibration run (goal: the arm runs the scanner and camera tests
   unattended overnight; indicators need a human to set up).

## 9. Starter bill of materials for perception and measurement

| Item | Example | Qty | Approx. cost |
|---|---|---|---|
| Wrist camera, global shutter mono, USB UVC | Arducam OV9281 USB | 1 | $50-70 |
| LED ring / IR LEDs + filter for wrist camera | generic | 1 | $10 |
| Fixed metrology camera | Raspberry Pi Global Shutter Camera + 8-12 mm C-mount lens | 1 | $75-100 |
| ChArUco and AprilTag boards on aluminium / glass | laser print + 3 mm Al plate | 3-5 | $20-40 |
| Tool-axis load cell + amplifier | TAL220 1-5 kg + SparkFun Qwiic Scale (NAU7802) | 1 | ~$20 |
| Screwdriver motor with encoder + current sense driver | geared DC + driver | 1 | $25-40 |
| Dial indicators + magnetic bases | Mitutoyo 2046A or generic digital | 3 | $100-300 |
| Precision ball / ground cube for the tool | bearing ball, 1-2-3 block | 1 each | $10-25 |
| Steel contact block + wiring for touch-off | ground steel | 1 | $10 |
| Scanner tokens (laser-cut Al) | from existing fab route | 3 | $10-20 |
| **Total** | | | **~$330-640** |

## 10. Open questions for the other researchers

- Actuators: will joints have current sensing and how high is the gear ratio (sensorless force is only useful below
  ~10:1 or with well-modelled servos)?
- Kinematics: is there room and mass budget for a ~15 g camera plus cable at the wrist, and does the wrist roll need
  a slip ring or limited rotation for the USB cable?
- Printer: is the bed a moving Y (bed-slinger), and what is its measured positioning repeatability (it becomes the
  reference stage)?
- Gripper: is the load cell inline with the gripper, or does the gripper carry it in a finger?

## Sources

- Raspberry Pi Global Shutter Camera: [raspberrypi.com product page](https://www.raspberrypi.com/products/raspberry-pi-global-shutter-camera/), [launch news](https://www.raspberrypi.com/news/new-raspberry-pi-global-shutter-camera/), [SparkFun listing](https://www.sparkfun.com/raspberry-pi-global-shutter-camera.html), [Farnell SC0926](https://uk.farnell.com/raspberry-pi/sc0926/global-shutter-camera-computer/dp/4163984), [Waveshare IMX296 M12](https://www.waveshare.com/product/imx296-130-bw-camera.htm)
- Arducam / Waveshare OV9281: [Core Electronics](https://core-electronics.com.au/ov9281-monochrome-global-shutter-1mp-camera-module.html), [The Pi Hut](https://thepihut.com/collections/latest-raspberry-pi-products/products/arducam-ov9281-monochrome-global-shutter-camera-module-for-raspberry-pi), [Waveshare OV9281-110](https://www.waveshare.com/ov9281-110-camera.htm)
- Camera Module 3 and USB camera prices: `mech-ai/docs/NOZZLE_CAMERA.md` (this repo)
- ChArUco online hand-eye calibration, 0.4-0.6 mm: [PMC9147787](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9147787/)
- ChArUco vs ArUco for hand-eye: [arXiv 2606.28555](https://arxiv.org/pdf/2606.28555)
- Multi-camera hand-eye, Tsai vs Park: [arXiv 2406.11392](https://arxiv.org/pdf/2406.11392)
- AprilTag vs ArUco robustness in grasping and hand-eye: [doongli grasp.pdf](https://doongli.github.io/doc/grasp.pdf)
- AprilTag accuracy vs distance and angle: [Abbas et al., Sensors 2019 (PMC6960891)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6960891), [arXiv 2502.03510](https://arxiv.org/pdf/2502.03510), [arXiv 2610.06215](https://arxiv.org/pdf/2610.06215), [arXiv 2305.05673](https://arxiv.org/abs/2305.05673v1)
- ISO 9283: [Hexagon ISO 9283 basics](https://documentation-be.hexagon.com/bundle/04_ISO9283_Basics/raw/resource/enus/04_ISO9283_Basics.pdf), [ETS Montréal repeatability paper](https://espace2.etsmtl.ca/32361/1/124%20-%20Experimental%20repeatability%20assessm.pdf), [arXiv 2010.05247](https://arxiv.org/pdf/2010.05247), [low-cost bimanual arm, arXiv 2502.16908](https://arxiv.org/pdf/2502.16908), [ISO 9283:1998 catalogue entry](https://standards.iteh.ai/catalog/standards/iso/b00c9665-53ff-4265-933d-77a544eb4e26/iso-9283-1998)
- Kinematic calibration: [Čehovin Zajc, low-cost manipulator calibration, ERK 2019](https://erk.fe.uni-lj.si/2019/papers/cehovin_zajc(kalibracija_nizkocenovnega).pdf), [BPASTS 2024 lightweight manipulator DH identification](https://czasopisma.pan.pl//Content/132450/PDF/BPASTS_2024_72_6_4449.pdf), [arXiv 1908.07273](https://arxiv.org/pdf/1908.07273v1.pdf), [arXiv 2503.12584](https://arxiv.org/abs/2503.12584v1), [PMC6210369](https://pmc.ncbi.nlm.nih.gov/articles/PMC6210369), [PMC7589031](https://pmc.ncbi.nlm.nih.gov/articles/PMC7589031), [Lu & Hayes, Carleton](https://carleton.ca/johnhayes/wp-content/uploads/P14_LuHayes_CR.pdf)
- Sensorless force from motor current: [Minimalist Compliance Control, arXiv 2603.00913](https://arxiv.org/pdf/2603.00913), [FACTR 2, arXiv 2606.12406](https://arxiv.org/pdf/2606.12406), [Yen et al., virtual force sensor, Sensors 2019](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6612363/)
- DIY F/T sensors: [TAMS printed F/T (GitHub)](https://github.com/TAMS-Group/tams_printed_ft), [Hendrich et al., IEEE Access 2020 (DOAJ)](https://doaj.org/article/70780dc4a6d749a3bd73019fed59a3a4), [Ouyang & Howe, fiducial F/T sensor, arXiv 2005.14250](https://arxiv.org/abs/2005.14250)
- Commercial F/T: [ATI Nano17](https://ati.novanta.com/product/nano17-force-torque-sensor/), [Bota MiniONE Pro (Robot Report)](https://www.therobotreport.com/bota-systems-launches-upgraded-force-torque-sensor-for-small-cobots/), [MiniONE Pro reseller price (Devicemart)](https://www.devicemart.co.kr/goods/view?no=16005663), [OnRobot HEX-E (Vention)](https://www.vention.io/parts/onrobot-force-torque-sensor-1422), [Robotiq FT 300-S (roboticscenter.ai)](https://www.roboticscenter.ai/es/store/product/robotiq-ft-300s-force-torque-sensor)
- Load cell amplifiers: [SparkFun Qwiic Scale NAU7802](https://www.sparkfun.com/sparkfun-qwiic-scale-nau7802.html), [SparkFun HX711](https://www.sparkfun.com/sparkfun-load-cell-amplifier-hx711.html), [Qwiic Scale hookup guide](https://learn.sparkfun.com/tutorials/qwiic-scale-hookup-guide/all)
- Dial indicator: [Mitutoyo 2046A at RS](https://uk.rs-online.com/web/p/dial-indicators/3976629)
- This repo: `mech-ai/mechloop/inspect/scan.py`, `mech-ai/mechloop/inspect/record.py`, `mech-ai/docs/INSPECTION.md`, `mech-ai/mechloop/twin/calibration.py`
