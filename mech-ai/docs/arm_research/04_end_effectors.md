# 04 - End-effectors and the tool interface

Scope: what goes on the end of the arm we design ourselves, how tools are swapped, and how the
printer (PLA/PETG only) iteratively remakes those tools in the mechloop design -> print -> test ->
measure -> redesign loop.

Labelling: figures with a cited source are marked [n] (sources at the end). Figures marked (est.)
are engineering estimates or recalled from general knowledge and were NOT verified in this search.
They should be checked before ordering parts or freezing a spec. Prices are late-2026 retail
snapshots and drift.

---

## 0. Summary and recommendation

1. **Tool interface:** a printed tool plate with **three steel balls on the tool and three printed
   V-groove pairs (Maxwell coupling) on the arm flange**. Preload comes from magnets (v0), then a
   servo-turned cam or twist latch (v1). Signals pass through **spring-loaded pogo pins** on a
   fixed pattern. Keep pneumatics out of the interface at first: put the vacuum source on the tool
   or run a dedicated tube. Expected repeatability with printed grooves is about 20 to 100 um
   (est.), which is far better than the arm itself will manage.
2. **First gripper:** a **parallel-jaw gripper driven by a serial-bus servo** (Feetech
   STS3215-class, about $17 to $31 [9]). It reports position and load, so the gripper is also a
   sensor. Finger pads are swappable printed parts, and they are the main thing the loop
   iterates.
3. **Second tool:** a **vacuum cup with a 12 V diaphragm pump, solenoid valve and pressure sensor**
   (about $25 to $40 [12][13]) for flat parts and for confirming each pick.
4. **Part removal from PEI:** do not pull parts off a hot or warm sheet. Wait until the bed cools,
   then **flex the spring-steel sheet** (the arm lifts the sheet off its magnets and bends it over
   a printed fixture). Use a printed wedge/scraper tool only as a fallback. Several published
   systems confirm that exchanging or flexing the plate is the robust route [14].
5. **Assembly tools, in order:** heat-set inserter (a fixed station on a Z-slide, which is easier
   than an arm-held iron), then a press-fit tool, then a screwdriver last.
6. **Twin:** MuJoCo is good enough to screen gripper kinematics, reach, collisions and gross grasp
   stability. It is not good enough to predict slip force, Fin-Ray or flexure compliance, or
   part damage without calibration against real tests. In the loop, the twin should rank and
   prune candidates, and real tests should be the score of record.

---

## 1. Quick-change tool interface

### 1.1 Kinematic couplings

A kinematic coupling constrains all 6 DOF exactly once. **Maxwell** uses 3 balls in 3 V-grooves
at 120 degrees, with 2 contacts per groove. **Kelvin** uses a ball in a trihedral socket, a ball
in a V-groove and a ball on a flat. Both give repeatability that depends on contact stiffness,
surface finish and friction, not on part tolerances. That property is what makes them suitable
for printed parts: the print can be off by 0.2 mm and the coupling still returns to the same
place every time.

Published data, all for metal couplings:
- Ball-and-groove couplings are routinely sub-micron. Quasi-kinematic (arc-contact) designs reach
  about 0.5 um [1][2].
- Slocum's tool-changer work used off-the-shelf hardened tooling balls and reported micrometre
  placement accuracy [3].
- Industrial trials of a kinematic coupling at a **robot wrist** gave about **0.05 mm
  repeatability** [4]. This is the closest analogue to our use.
- Wear on the contact elements limits repeatability as cycles accumulate. A suggested low-cost
  fix is to **burnish soft grooves with the harder balls** [1][2]. This is directly relevant to
  printed grooves.

**For printed grooves (PLA/PETG):**
- Keep the balls steel: 6 to 8 mm bearing balls (about $0.05 each) or tooling balls (est.).
- The printed V-groove carries the risk. PLA creeps under sustained preload, and layer lines
  make the flanks rough. Mitigations, in order of cost:
  1. Print the grooves so the flanks lie at 45 degrees to the layers, and run the coupling a few
     hundred times under load to burnish it.
  2. Press a pair of **steel dowel pins** (about 3 mm x 12 mm) into each printed groove, so the
     ball touches two parallel cylinders. This is the classic "ball on two rods" Maxwell variant.
     E3D's ToolChanger uses balls on dowel pins and asks for regular cleaning and inspection of
     both [5].
  3. Use hardened steel V-blocks only if creep shows up in measurement.
- Expected printed-interface repeatability is about **20 to 100 um** (est.). The rod-insert
  variant should sit at the low end. Validate with a dial indicator or the loop's camera
  fiducial (section 4).

### 1.2 Preload and latching

| Latch | How | Pros | Cons | Fit for us |
|---|---|---|---|---|
| Permanent magnets | 2 to 4 N52 discs (e.g. 10 x 3 mm) in the flange, steel slugs or opposing magnets in the tool | Zero actuators, self-seating, trivially printable | Holding force is limited and fixed. Tool can be knocked off. Magnets attract swarf and steel screws | **v0** |
| Passive dock + magnets | Tool sits in a printed fork. The arm slides in and lifts out, so the dock strips the tool against the magnet force | No actuator in the arm | Needs repeatable dock geometry and a calibrated approach | v0/v1 |
| Twist-lock / cam (servo) | A small servo turns a helix or cam that pulls the tool plate up onto the balls | High, adjustable preload | One more actuator and wire in the wrist | **v1** |
| Wedge lock (Jubilee-style) | A rotating lock pulls the balls into the grooves. Jubilee uses a 6 mm ball and a **Delrin helix**, and locks **by torque, not position**, so it tolerates wear [6] | Proven open-source design, wear-tolerant | Delrin is not printable here, so PETG must stand in. Creep needs testing | **v1** |
| Electro-permanent magnet | A pulse switches it on or off and it holds with no power (Zubax FluxGrip FG40 / FG401M, about $149 to $169 [8]) | Power-off hold, no moving parts | Cost, mass, and it needs a steel target on the tool | Optional |

The E3D ToolChanger (balls + dowel pins + a cam-driven lock) and Jubilee (balls + V-grooves +
a torque-based helix lock) are the two open-source references worth copying. Jubilee's FAQ
notes the two tool plates are similar but not identical [6]. Neither project publishes a
measured repeatability figure that we could find. One "100% repeatable" claim traces back to
marketing [4][5], so we will need to measure our own.

### 1.3 Electrical and pneumatic pass-through

- **Electrical:** use a row of **spring-loaded pogo pins** (Mill-Max or generic, about $0.50 to $2
  per pin (est.)) against flat brass pads or a small PCB on the tool side. Because the kinematic
  coupling already fixes position, the pins only need to land on about 2 mm pads.
  - Suggested 6-pin pattern: GND, +12 V, +5 V, a half-duplex serial bus (Feetech/Dynamixel style,
    1 wire), TOOL_ID, spare.
  - TOOL_ID: a resistor divider read by the arm's ADC, or a 1-Wire EEPROM (DS28E07, about $1
    (est.)) holding the tool's version hash. The version hash lets the loop log exactly which
    printed iteration was mounted.
  - Make GND the longest pin so it mates first. Do not hot-swap the 12 V line under load: switch
    tool power off during a change.
- **Pneumatic:** a face-seal O-ring port (a printed boss with a 6 x 1.5 mm Buna O-ring) works
  but leaks under misalignment (est.). Simpler for v1: **mount the pump on the vacuum tool
  itself**, powered through the pogo pins. A small diaphragm pump weighs about 60 to 100 g
  (est.), and this removes the pneumatic joint entirely.

---

## 2. Grippers

Constraint: the printer prints only **PLA and PETG**, so TPU Fin-Ray fingers, the common
open-source choice [10][11], are out unless TPU is bought in. Compliance must come from
**geometry** (thin PETG flexures, Fin-Ray ribs in PETG) or from **bought pads** (silicone or
urethane sheet, or grip tape glued onto printed fingers).

### 2.1 Options

| Gripper | Actuation | Printable in PLA/PETG? | Best for | Notes |
|---|---|---|---|---|
| Parallel jaw, rack-and-pinion or linkage | Serial-bus servo (STS3215 class: 19 kg.cm at 7.4 V / 30 kg.cm at 12 V, 4096-count encoder, reports position/load/speed/voltage/temp, about $17 to $31 [9]) | Yes, all structure | Picking small parts, holding parts for inspection, grasping a flexed print | **First build.** The servo load reading gives grasp force and object width for free. Waveshare Gripper-A (STS3215) is a $47 to $80 reference design [9] |
| Parallel jaw, leadscrew | NEMA 8/11 stepper + TR6 screw (est. $15 to $25) | Yes | High force, self-locking hold | Slow. Needs a homing switch. Better resolution |
| Fin-Ray fingers | Same as above | **PETG only**, thin ribs about 0.8 to 1.2 mm (est.); TPU is the norm [10][11] | Irregular or fragile parts | PETG Fin-Ray is stiffer and fatigues; it is a loop experiment, not v1 |
| Compliant flexure finger (monolithic) | Same | Yes (PETG) | Gentle grasp, built-in force limit | Co-design of printable flexure fingers measurably raised grasp success in sim and hardware [17] |
| Vacuum cup | 12 V diaphragm pump + 3-way solenoid valve + bellows cup | Cup must be bought (silicone/nitrile). The mount is printed | Flat parts, PEI-released prints, thin plates | Kit about $26 [13]; bare SparkFun 12 V pump $25.50, 0 to 16 inHg [12]. Add a pressure sensor (e.g. MPXV6115V, about $10 to $15 (est.)) to detect a seal |
| Venturi ejector | Compressed air | Body printable, but needs a compressor | Fast cycles | Cheaper, smaller and faster-responding than pumps, but needs an air supply, and compressed-air systems lift 4 to 10x more than mini pumps [15]. **Skip**: no shop air |
| Permanent-magnet / EPM | Zubax FG401M about $149 [8] | Mount yes | Steel parts: screws, nuts, the printer's spring-steel sheet | Useful for carrying the PEI sheet itself, not for plastic parts |
| Soft pneumatic (PneuNet) | Air | Requires cast silicone | Delicate objects | Out of scope for PLA/PETG |

### 2.2 Matching task to tool

| Task | Recommended | Why |
|---|---|---|
| Removing a part from PEI | 1) Flex the spring-steel sheet after the bed cools, then pick with jaw or vacuum. 2) Fallback: a printed wedge on the jaw, angled about 15 to 25 degrees (est.) | PEI parts usually release once cool, even PETG (anecdotal [14]). Removal force rises sharply when the bed is near PEI's glass transition [14]. Pushing parts off needs free plate edges [14] |
| Moving the sheet itself | Magnetic/EPM pad, or a jaw on a printed handle tab | The sheet is steel, about 0.5 mm thick |
| Small parts (M3 nuts, inserts, 5 to 20 mm prints) | Parallel jaw with V-notch fingertips; vacuum with a 4 to 6 mm cup for flat faces | V-notches self-centre cylinders. Vacuum avoids pushing small parts sideways |
| Holding a part for camera inspection | Parallel jaw, plus a printed **nest** fixture for repeatable pose | Inspection needs a known pose. A jaw plus a datum fixture beats a soft gripper here |
| Feeding the printer (placing inserts or magnets mid-print) | Jaw with tweezer-tip fingers | Needs about 0.2 mm placement accuracy (est.) |

### 2.3 Fingertip friction

Grasp success depends heavily on the fingertip surface. Berkeley's ICRA 2017 study tested 37 jaw
surface designs over 1377 automated grasps: factory tips succeeded 28.7% of the time and simply
taping the tips raised that to 68.7% [16]. Printed PLA/PETG has low friction against printed
PLA/PETG (mu about 0.2 to 0.35 (est.)). The cheapest early win is therefore glued silicone or
grip-tape pads, or printed micro-ridges.

---

## 3. Assembly tools

### 3.1 Heat-set inserts

- **Temperature:** most sources say to set the iron **10 to 20 C above the print temperature**.
  CNC Kitchen gives about **225 C for PLA** and **245 C for PETG** [7]. UW-Madison suggests 240 to
  260 C for PLA [7b]. EPFL uses the print temperature itself (230 C for PETG) [7c]. One table
  gives PLA 177 to 204 C with a 2 to 3 s press and PETG 218 to 246 C with a 3 to 4 s press [7d].
  These sources disagree, so treat temperature as a **loop parameter to calibrate**.
- **Technique:** melt the insert in about 90% of the way, then press the last 10% flush with a
  cold flat tool so it seats square and the melt does not wick into the thread [7].
- **Parts:** Ruthex M3x5.7 inserts are about $8.30 per 100 [18]; Prusa and CNC Kitchen sell
  equivalents. Ruthex and others sell insert-specific soldering tips (M2 to M8) [18], about $15
  to $25 for a set (est.). A TS101/Pinecil-class USB-C iron (about $25 to $60 (est.)) can be
  set over serial or USB and reports tip temperature, which suits automation.
- **How a robot should do it:** we found no published robotic heat-set procedure. Recommended
  design:
  - Mount the iron as a **fixed vertical station on a stepper Z-slide with a load cell**, not on
    the arm. The arm presents the part, held in a printed nest, under the station.
  - Control **position plus force**: descend at about 0.5 to 1 mm/s while force stays under about
    20 to 40 N (est.), stop at 90% depth, dwell, retract, then use a cold pressing pin.
  - An arm-held iron is possible but puts a 250 C, about 40 W tool in the arm's workspace and
    needs stiff, low-backlash Z motion that a printed arm may lack.
  - Feeding inserts: a vibratory or gravity tube feeder, or simply a printed tray the arm picks
    from.
- **Measures:** insert depth (height gauge or camera), perpendicularity (tilt), pull-out force
  (sampled destructively), and melt bloom around the rim (camera).

### 3.2 Screwdriving

- Commercial robot screwdrivers (Robotiq, OnRobot) cover about **0.15 to 5 N.m**, pick screws by
  **vacuum through the bit**, and use a feeder with presence sensing [19]. Both cost thousands of
  dollars. Use them only as the design reference.
- **DIY design:**
  - Use a small geared DC or brushless motor or a STS3215 in wheel mode. Motor current is
    proportional to torque, so current-based torque sensing is standard practice [19]. A CMU
    thesis builds an "intelligent" small-screw driver from current, velocity and axial force
    [19b].
  - Hold the screw with a **magnetic bit** (steel screws) or vacuum through a hollow bit.
  - Mount the bit on an axial spring with a travel sensor, so the driver detects screw engagement
    (cam-out) and seating.
  - M3 into a heat-set insert needs about 0.4 to 0.8 N.m (est.); M3 self-tapping into PLA needs
    about 0.2 to 0.4 N.m (est.).
  - **Feeder:** v1 is a printed vertical tray with countersunk pockets the bit plunges into. A
    proper screw presenter (est. $150 to $400) can come later.
- **Measures:** torque-vs-angle curve per screw (classifies seated, stripped, cross-threaded or
  missing), cycle time, and success rate.
- Priority: low. Heat-set inserts plus snap-fits cover most early printed assemblies.

### 3.3 Press-fit tooling

- Press-fit work covers bearings into printed housings, dowels into couplings, and magnets into
  pockets.
- Use a printed pusher with a **steel face** on the arm, or better, the heat-set station's Z-slide
  with its load cell (one station, two jobs).
- Log **force vs displacement**: the curve's peak and slope give interference fit and part cracking
  directly. Expected loads are about 50 to 300 N for a 608 bearing in PETG (est.), which is
  likely beyond a small arm's payload. That is another reason to use a station rather than the
  arm.

---

## 4. Measuring each end-effector iteration

### 4.1 Metrics

| Metric | How to measure automatically | Instrument |
|---|---|---|
| Grasp success rate | Pick, lift 50 mm, shake (2 to 3 small moves), place. Success = object still held (servo load above threshold or vacuum pressure held) and present at the place location (camera) | Servo load / pressure sensor + camera |
| Placement / alignment error | Fiducial (AprilTag or printed dot pattern) on the part or nest; measure the placed pose against the target | Overhead camera, about 0.1 mm/px (est.) |
| Tool-change repeatability | Fiducial on each tool tip. Do N changes and report the spread (std, max) | Camera, or a dial indicator / USB microscope at the dock |
| Slip / pull-out force | Gripper holds a test coupon tethered to a load cell (HX711 + 5 kg bar, about $10 (est.)). The arm pulls until slip, detected by encoder displacement or force drop | Load cell |
| Grip force | Squeeze a load-cell coupon at commanded settings to calibrate servo-load-to-newtons | Load cell |
| Cycle time | Timestamps from the arm controller | Software |
| Part damage | Before/after photo diff (scratches, whitening), dimensional check on a stress coupon, crack inspection | Camera, calipers |
| Tool wear / creep | Repeat the slip and repeatability tests every N cycles. Track the drift | Same as above |
| Heat-set quality | Depth, tilt, pull-out on samples | Camera + load cell |

**Standard test objects:** print a fixed "grasp benchmark set" (cube, cylinder, sphere, thin
plate, M3 nut, an insert, a tall slender part, a part with a curled corner). Log every attempt
with the gripper's version hash, object ID, pose, metrics and outcome. YCB-style object sets are
the academic norm. A printed set is reproducible and costs only filament.

### 4.2 The closed loop

Use the printer, arm, camera and load cell together:

1. **Propose.** A parametric CAD template (finger length, pad geometry, flexure thickness, V-notch
   angle, groove angle) plus an optimizer (Bayesian optimization or CMA-ES) proposes K variants.
2. **Screen in the twin.** MuJoCo rejects variants that collide, cannot reach, exceed servo
   torque, or are grossly unstable. Rank the survivors by sim score.
3. **Print** the top 2 to 4 finger or tool variants. They are small, about 15 to 40 min each
   (est.). Finger pads mount on the jaw via the kinematic tool plate or a dovetail/screw.
4. **Install.** The arm swaps fingers itself if the finger interface is a passive magnetic or
   dovetail dock. Otherwise this is the one human step at the start.
5. **Test** on the benchmark set, about 20 to 50 grasps per object (est.), with automated reset.
   Berkeley's loop needed a 4-axis robot with automated reset to run 1377 physical grasps [16].
   Reset is what makes the loop autonomous: use a funnel or tray that returns dropped objects
   to a known area.
6. **Measure and score** with the metrics in 4.1. Real tests are the score of record.
7. **Update.** Feed real results back to the optimizer and **recalibrate the twin's contact
   parameters** (friction, solref/solimp) on the real slip-force data. Berkeley expanded the
   design set around the best design each round, a resampling-style search [16].

**Budget:** a round of 4 variants x 8 objects x 30 trials is about 1000 grasps. At about 15 s per
grasp that is about 4 hours of arm time plus about 2 hours of printing. Two rounds a day is
realistic (est.).

### 4.3 What MuJoCo can and cannot predict for grippers

MuJoCo models contact as **soft constraints**. Contacts always allow small penetration, governed
by `solref` (time constant, damping) and `solimp` (impedance), with pyramidal or elliptic
friction cones [20].

**Can predict (useful for screening):**
- Kinematics, reach, finger stroke, collisions with the dock, sheet or printer frame.
- Required actuator torque and whether the servo saturates.
- Rigid grasp stability: whether the object stays in a closed jaw under gravity and arm
  accelerations, given friction mu.
- Tool-change approach paths and the coupling's self-centring motion, qualitatively.
- Relative ranking of rigid geometric variants: V-notch vs flat, finger length, opening width.

**Cannot predict well without calibration:**
- **Absolute slip force.** It depends on real friction (printed surfaces, pads, dust) and on
  contact area, which MuJoCo's rigid geoms do not model. Calibrate mu against load-cell tests.
- **Compliant fingers** (Fin-Ray, flexures). The ribs could be built as chains of bodies with
  joint springs, as the docs suggest for deformables [20b], or with MuJoCo's newer `flex`
  elements (est., check current docs). Either way, stiffness must be fitted to measured
  force-deflection. The literature calls compliant-rigid contact "notoriously difficult" and
  notes coupled deformation-friction effects and failures on near-edge grasps [21]. Others
  calibrate MuJoCo contact parameters against a few real samples [21].
- **Part damage, creep, wear, layer delamination.** None of these are modelled.
- **PEI adhesion and peel force.** These are not modelled and must be measured.
- **Vacuum seal** quality on textured printed surfaces. Model it as a weld or adhesion actuator
  with a success probability taken from real data.
- **Heat-set insertion** (melt flow). Out of scope: treat it as a black box with measured
  outcomes.

**Practical stance:** the twin is a filter and a ranking prior, not the score. The quantity worth
tracking over loop iterations is the **gap between predicted and measured** grasp success and
slip force. If calibration is working, that gap should shrink.

---

## 5. Bill of materials (first end-effector set)

| Item | Example part | Approx. price | Source |
|---|---|---|---|
| Gripper servo | Feetech STS3215 (12 V, 30 kg.cm) | $17 to $31 | [9] |
| Reference gripper kit | Waveshare Gripper-A (STS3215) | $47 to $80 | [9] |
| Vacuum pump | SparkFun ROB-10398 12 V, 0 to 16 inHg | $25.50 | [12] |
| Vacuum kit (pump + valve + cup) | Little Bird robot-arm suction set | about $26 | [13] |
| Pressure sensor | NXP MPXV6115V or similar | $10 to $15 | (est.) |
| EPM (optional) | Zubax FluxGrip FG401M | $149 | [8] |
| Coupling balls | 6 to 8 mm chrome-steel balls (x3 per tool) | under $1 per tool | (est.) |
| Groove inserts | 3 mm x 12 mm steel dowel pins (x6 per flange) | about $5 per 50 | (est.) |
| Preload magnets | N52 10 x 3 mm discs | about $0.30 each | (est.) |
| Pogo pins | Mill-Max spring pins, 6 per interface | $3 to $12 per interface | (est.) |
| Tool ID | DS28E07 1-Wire EEPROM or resistor | about $1 | (est.) |
| Heat-set inserts | Ruthex M3x5.7, 100 pcs | about $8.30 | [18] |
| Insert tips | Ruthex M2 to M8 tip set | $15 to $25 | [18] (price est.) |
| Iron | Pinecil / TS101 class | $25 to $60 | (est.) |
| Force sensing | 5 to 20 kg load cell + HX711 | about $10 | (est.) |
| Finger pads | Silicone sheet 1 to 2 mm / grip tape | about $10 | (est.) |

Total for a gripper, vacuum tool, tool changer and heat-set station is about **$200 to $300**
excluding the EPM.

---

## 6. Suggested build order for the loop

1. Fixed parallel jaw (STS3215) with swappable printed finger pads. Measure grasp success and slip
   on the benchmark set. **This is the first closed loop: iterate the pads.**
2. Maxwell tool plate with magnet preload and pogo pins, plus a passive dock. Measure tool-change
   repeatability. Iterate the groove geometry (angle, dowel vs printed flank).
3. Vacuum tool (on-tool pump). Add the PEI sheet-flex fixture. Measure part-removal success and
   damage.
4. Heat-set station (iron on a Z-slide with load cell). Iterate the temperature/force/dwell
   recipe, then the hole geometry in printed parts.
5. Servo-cam latch (v1 interface), then the screwdriver.

---

## Sources

1. Slocum, "Kinematic couplings: a review of design principles and applications", MIT 2.70 reading: https://web.mit.edu/course/2/2.70/Reading%20Materials/Kinematic%20coupling%20review%20article.pdf
2. Culpepper 2004 (quasi-kinematic couplings): https://wp.optics.arizona.edu/optomech/wp-content/uploads/sites/53/2016/10/culpepper-2004.pdf ; Schouten 1997: https://wp.optics.arizona.edu/optomech/wp-content/uploads/sites/53/2016/10/Schouten-1997.pdf
3. Slocum, MIT DSpace thesis/paper: https://dspace.mit.edu/bitstream/1721.1/1669/2/A_Slocum.pdf
4. MIT Precision Engineering, "Experimental determination of kinematic coupling repeatability in industrial and laboratory conditions": https://mechanosynthesis.mit.edu/experimental-determination-of-kinematic-coupling-repeatability-in-industrial-and-laboratory-conditions ; forum thread on E3D coupling claims: https://groups.google.com/g/3dp-ideas/c/tJcuWiYh7mA/m/3ZlruVTYAgAJ
5. E3D ToolChanger datasheet/maintenance (Zendesk attachment): https://e3d-online.zendesk.com/hc/en-us/article_attachments/360016170597
6. Jubilee FAQ, E3D vs Jubilee tool plates: https://jubilee3d.github.io/faqs/e3d_toolplates.html
7. CNC Kitchen, heat-set insert tips: https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey ; [7b] UW-Madison ME Design Lab: https://medesignlab.me.wisc.edu/?p=162 ; [7c] EPFL: https://make.epfl.ch/wiki/public/spot_-_3d_printing/how_to_use_threaded_inserts ; [7d] Albany County Fasteners spec: https://www.albanycountyfasteners.com/media/64/3d/5a/1764619189/heat-set-insert-specs.pdf
8. Zubax FG401M on RobotShop: https://robotshop.com/products/zubax-zubax-fg401m-electro-permanent-magnetic-gripper-epm ; OpenGrab EPM v3 discontinued: https://ardupilot.org/copter/docs/common-electro-permanent-magnet-V3.html
9. Waveshare ST3215: https://www.waveshare.com/st3215-servo.htm ; RobotShop STS3215: https://www.robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215 ; Core Electronics: https://core-electronics.com.au/feetech-sts3215-smart-servo.html ; Waveshare Gripper-A: https://www.waveshare.com/product/robotics/robot-arm-control/robot-arm/gripper-a.htm
10. Crooks et al. 2016, Fin Ray-inspired gripper: https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2016.00070/full
11. InstaGrasp (Imperial): https://www.imperial.ac.uk/manipulation-touch/research/instagrasp/ ; CUBE Fin-Ray hybrid (MakerWorld): https://makerworld.com/models/2866227
12. SparkFun 12 V vacuum pump ROB-10398: https://www.sparkfun.com/vacuum-pump-12v.html
13. Little Bird robot-arm pump/valve/suction-cup set: https://littlebirdelectronics.com.au/products/robotic-arm-air-pump-valve-controller-vacuum-suction-cup-set
14. Automated part removal: MIT thesis (PEI removal force): https://dspace.mit.edu/handle/1721.1/92203 ; Rapid Prototyping Journal push-off arm: https://www.emerald.com/insight/content/doi/10.1108/RPJ-02-2016-0029/full/html ; Monash bed-exchange (Springer): https://link.springer.com/chapter/10.1007/978-981-99-3330-3_27 ; Hackaday chain-production add-on: https://hackaday.com/2020/07/20/automated-part-removal-gets-serious-with-the-chain-production-add-on ; Bambu forum: https://forum.bambulab.com/t/bambu-labs-robot-to-remove-prints-and-restart/6329
15. A3, "Choose your cobot vacuum gripper wisely": https://www.automate.org/tech-papers/choose-your-cobot-vacuum-gripper-wisely ; GlobalSpec venturi generators: https://www.globalspec.com/learnmore/manufacturing_process_equipment/vacuum_equipment/vacuum_pumps/venturi_vacuum_generators
16. Berkeley AUTOLAB, gripper tip surface design (ICRA 2017): https://goldberg.berkeley.edu/pubs/gripper-tip-surface-design-icra-2017-camera-ready.pdf
17. Co-Design of Soft Gripper with Neural Physics (arXiv 2505.20404): https://arxiv.org/html/2505.20404v2 ; Fit2Form (arXiv 2011.06498): https://arxiv.org/pdf/2011.06498v1.pdf
18. 3DJake Ruthex M3 inserts: https://www.3djake.com/ruthex/threaded-insert-m3-100-pieces ; Prusa heat-set inserts: https://www.prusa3d.com/en/product/heat-set-inserts-m3-standard-100-pcs/
19. Robotiq screwdriving solution: https://robotiq.com/solutions/assembly/ ; OnRobot screwdriver: https://onrobot.com/en/node/2355 ; [19b] CMU master's thesis on small-screw driving: https://www.ri.cmu.edu/app/uploads/2019/08/master_thesis-4.pdf
20. MuJoCo computation docs (soft contact, solref/solimp, friction cones): https://mujoco.readthedocs.io/en/stable/computation/ ; [20b] MuJoCo overview (deformables from bodies/constraints): https://mujoco.readthedocs.io/en/3.9.0/overview.html
21. IPC-GraspSim (sim2real gap for parallel-jaw grasping): https://arxiv.org/pdf/2111.01391 ; MuJoCo soft-hand / evolutionary parameterization (arXiv 2604.05531): https://arxiv.org/html/2604.05531
