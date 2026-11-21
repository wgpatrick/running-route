# Arm Build 1: scoping the robot arm that works with the printer

Status: scoping synthesis (2026-11-21). Nothing here is designed, simulated or built. Every number is an **estimate (est.)**
or an **assumption** unless a source is given. Prices are web snapshots from November 2026 and must be re-checked live
before any order (DG-07).

This file is the top-level scope. The detailed research, with full source lists, is in `docs/arm_research/`:

| File | Covers |
|---|---|
| [01_kinematics.md](arm_research/01_kinematics.md) | cell geometry, sheet physics, architecture scoring, decisive tests |
| [02_actuators.md](arm_research/02_actuators.md) | torque and error budgets, motors, reductions, encoders, joint recipes A/B/C, twin data per joint |
| [03_prior_art.md](arm_research/03_prior_art.md) | open arms, print-farm automation, robotic assembly of printed parts |
| [04_end_effectors.md](arm_research/04_end_effectors.md) | tool interface, grippers, assembly tools, how each iteration is measured, first tool BOM |
| [05_digital_twin.md](arm_research/05_digital_twin.md) | simulation stack, controller in the loop, plant fidelity, 12 new verifiers, validation |
| [06_perception.md](arm_research/06_perception.md) | cameras, fiducials, hand-eye calibration, force sensing, measuring the arm |
| [07_safety_cell.md](arm_research/07_safety_cell.md) | standards in plain terms, hazards, limits, printer-arm handshake, safety architecture |

**Owner decisions so far**
- We **design our own arm** (not buy one), with the same mechloop loop as the printer: real purchased parts (DG-07),
  generated fabricated parts, every verifier, a digital twin, pre-registered predictions, measured results in the ledger.
- The arm (a) **assembles** printed parts with off-the-shelf parts and (b) **operates the printer**.
- The printer **makes the arm's end-effectors**, so the arm improves by working with the printer.
- **Kinematics stay open** until the decisive tests in section 4 have run.

---

## 1. Goal, and how it serves recursive self-improvement

The roadmap's loop is: make a part, measure it, learn, improve the part and the loop. Today a human closes every physical
step: take the print off, put it on the scanner, assemble it, start the next job. The **autonomy** metric (human touches
per iteration) cannot improve past that. The arm is the loop's first **handling and assembly tool**, as the printer is its
first fabrication tool.

It serves the goal three ways:
1. **Autonomy.** The arm takes the human out of print -> measure -> next print. Loop time drops from "when the owner is
   home" to minutes.
2. **A second loop the system owns end to end.** End-effectors are designed by mechloop, printed on our printer, unloaded
   and scanned by the arm, mounted by the arm, tested by the arm, and the result goes in the ledger. No human sits between
   design change and measured result. This is the first loop where that is possible.
3. **Assembly.** Building sub-assemblies from printed and purchased parts is the path to the system making its own
   fixtures, tools and upgrades.

### Staged plan: what "done" means for Arm Build 1

Targets are **proposals** for the owner to confirm. The tool-change coupling is designed first, because every stage uses a
different tool, but it is gated last.

| Stage | Capability | Done when (proposed) |
|---|---|---|
| **A. Sheet handling** | Printer cools the bed and brings it to a transfer height; arm peels the front edge of the PEI spring-steel sheet 3-10 mm, **slides it out ~240 mm onto a receiving shelf at bed height**, flexes it on the shelf to release the print and purge, slides it back onto locating pins; the next queued job starts | 100 cycles of mixed PLA/PETG prints, >= 95 % with zero human touches; sheet re-seated within +/-0.3 mm (Eddy reading + top-down camera); every unload verified (camera of the empty sheet; scale under the drop bin) |
| **B. Inspection** | Pick the released part, place it on the flatbed scanner or camera stage, trigger the scan, file the result, sort the part into a tray | 50 parts measured end to end with zero touches; rows written by `mechloop.inspect` with `who = "arm"`; placement within +/-1 mm and +/-2 deg |
| **C. Assembly at fixed stations** | Arm loads parts into nests at a **heat-set press station** and a **screw station** (screw presenter, compliant driver), a press-fit station for bearings, and places magnets | Each operation >= 95 % over 50 tries (insert depth +/-0.2 mm, tilt < 2 deg; screw torque +/-15 %; bearing flush within 0.1 mm; magnet polarity and depth right); then one real sub-assembly built unattended (proposal: the arm's own gripper, or a camera mount) |
| **D. Tool change and the end-effector loop** | Swap printed end-effectors on a kinematic coupling from a rack; the loop prints, mounts and tests a new version | 200 changes >= 99 % success; coupling repeatability <= 0.05 mm measured; >= 3 tools in use; one end-effector taken through >= 3 loop iterations to its target with no human design step |

---

## 2. Task catalogue

Printer facts used (docs/PRINTER_V12.md, PRINTER_V11.md, V13_IDEAS.md): 2020 frame 388 x 419.5 x 476 mm (510 deep with the
rear spool); **front side has no Z rail** and gets the hinged door in V13; 220 x 220 textured PEI on 0.4 mm spring steel on
a magnetic base; print area 186.6 x 208.1 mm; **the bed moves in Z only (180 mm), so the printer can bring it to any
transfer height**; Klipper on Octopus + Pi 5 with Moonraker; Eddy probe, overview and top-down cameras, Class 1M line
laser; Roto extruder fed by PTFE from a 1 kg spool **at the rear**; Revo hotend; PLA/PETG only.

Geometry (est., [01](arm_research/01_kinematics.md) section 1): front opening about **348 mm** clear between the posts;
sheet centre about 210 mm inside the front face. A 0.4 mm sheet held by one edge sags about **8 mm** under its own weight
(more with a print on it), so carrying it cantilevered is messy: **slide it, do not lift it**. The core printer move is a
1-D horizontal pull at bed height, 240-300 mm long, plus a short vertical peel.

### 2.1 Printer operation

| Task | Build 1? | Payload | Force | Accuracy | Workspace | Cycle | Sensing |
|---|---|---|---|---|---|---|---|
| **Peel and slide the sheet out to the shelf, slide it back** | **Yes (primary)** | sheet ~0.15 kg + print up to ~0.5 kg + tool 0.1-0.3 kg: **rating 1 kg** | peel off the magnet: low (gives way in peel; measure, test 5 in 01) | grip tab +/-1 mm; final location by bed pins: arm needs 0.5-1 mm ([03](arm_research/03_prior_art.md) 2.3) | through the front at the transfer height | 60-120 s round trip | sheet-present (Eddy at a fixed XY, top-down camera), gripper load |
| **Flex the sheet on the shelf to release the print** | **Yes** | as above | the shelf fixture bends the sheet; the arm pushes one edge | +/-2 mm | shelf station | 20-40 s | camera (print gone), scale under the drop bin |
| Clear purge | **Yes**: purge at the front of the bed, so it leaves with the sheet | - | - | - | shelf | - | camera |
| Scrape the print in place | **No** | - | 20-50 N tangential | PEI gouging | - | - | - |
| Open / close the V13 door | Possible; **a Klipper door actuator is cheaper** (cf. the $129 Bambu auto-eject kit with door opener, section 8) | - | low | +/-3 mm | front | 5 s | door interlock switch |
| Load / unload filament | **No** | - | - | 1.75 mm tip into PTFE | rear | - | - |
| Change spool | **No** | 1.25 kg | - | - | rear, out of reach | - | - |
| Swap Revo nozzle | **No** (later) | - | low torque | <0.2 mm under the toolhead | top | - | camera |

Why not scrape: high force, PEI damage, fails on small parts ([03](arm_research/03_prior_art.md)), and the bed's thumb-nut
washers are meant to slip on the deck (PRINTER_V12 "Bed"), so a sideways load could move the bed.

### 2.2 Inspection handling

| Task | Payload | Force | Accuracy | Cycle | Sensing |
|---|---|---|---|---|---|
| Place a part face-down on the scanner glass, scan, pick it up | <0.3 kg | <5 N on the glass | +/-1 mm, +/-2 deg, flat | 30 s + scan | camera confirms placement; the scan itself |

The scanner lid is a problem for an arm. The scan pipeline needs the part dark against a light lid
(docs/INSPECTION.md). Options for the spike: a fixed open-sided light hood instead of the lid, or a hook tool that lifts the
lid. A fixed metrology camera over a backlit plate covers parts that are not flat ([06](arm_research/06_perception.md)).

### 2.3 Assembly (fixed stations do the precise and forceful work)

| Operation | Station / tool | Force / torque | Arm accuracy needed | Sensing |
|---|---|---|---|---|
| **Heat-set insert** (M3 brass) | **press station**: iron on a Z slide with a load cell; arm places the part in a nest and drops the insert on the hole | 20-50 N (est.) | +/-0.3-0.5 mm (nest locates) | tip temperature, Z, load cell |
| **M3 screw** | screw presenter + compliant screwdriver tool (servo or gearmotor with encoder) | 0.4-1.2 N·m (est.) | +/-0.3 mm with lead-in + compliance | motor current x Kt, turn count for cross-threading |
| **Press-fit bearing** | press station | 50-200 N (est.) | +/-0.3-0.5 mm | load cell; force-distance curve |
| **Magnet** | tube dispenser fixes polarity; non-magnetic fingers | <20 N | +/-0.3 mm | camera |

Consequences:
- **Precision goes into fixtures and part features, not the arm**: nests, chamfers and lead-ins sized to the arm's measured
  error, a passive compliant wrist, vertical-only insertion ([03](arm_research/03_prior_art.md) section 4). Every
  published tight-fit insertion used compliance plus sensing; position control alone did not.
- DG-04 wants through-bolts with nuts. A single arm cannot hold the far nut, so robot-assembled parts use **nuts captured
  in printed pockets** (DG-04's first fallback) or a nest that holds the nut.
- Heat-set inserts stay restricted by DG-04 (written reason needed); the station is a capability, not a rule change.
- Insert temperature: sources disagree (print temperature + 10-20 degC from
  [Prusa's insert listing](https://www.prusa3d.com/product/heat-set-inserts-m3-standard-100-pcs/) vs iron set points of
  343-399 degC in LulzBot's guide, cited in 03). The station finds the recipe by coupon sweeps; that is a learning.

### 2.4 Requirement summary

| Requirement | Value (est.) |
|---|---|
| Payload incl. tool | 1 kg |
| Horizontal reach | to the sheet's front edge + 240-300 mm pull; stations in an arc in front |
| Approach | horizontal into the 348 mm opening at the transfer height; top-down at stations |
| Repeatability at the tool | 3 sigma <= 0.2 mm at insert/screw poses, <= 1 mm at sheet poses (01 test 2) |
| Static tool force | <= 50 N (also a safety cap, section 3) |
| DOF | x, y, z + roll minimum; pitch only for flexing or flipping |
| Cycle | full unload < 3 min |

---

## 3. Work cell and safety

### Layout (proposal; 01 section 2)

```
                rear: spool, electronics bay
        +--------------------------------------+
        |            PRINTER v12               |
        |   front = door side, opening ~348    |
        +--------------------------------------+
        [sheet shelf + flex fixture at bed height]
 [tool rack]  [scanner + metrology camera]  [press station]
     [screw presenter]   ARM BASE    [magnet / insert feeders]
          [parts trays (kinematic pockets, AprilTags)]  [finished tray]
                     front of the bench (human side)
```

- Bench footprint (est.) 1.0-1.2 m wide x 0.8-0.9 m deep with the printer; the front-loading Cartesian needs about 1 m of X.
- The cell is one mechloop `Design` (printer as a body with its bed Z and gantry park positions, arm, stations, cameras).

### Printer-arm coordination ([07](arm_research/07_safety_cell.md) section 5)

- **Moonraker JSON-RPC websocket**, subscribe (not poll) to `webhooks.state`, `print_stats.state`, heater temperatures,
  `toolhead.position` / `homed_axes` ([Moonraker printer API](https://moonraker.readthedocs.io/en/latest/external_api/printer/)).
  Query state on connect: Moonraker warns subscribers can miss startup transitions.
- **The lock lives in Klipper**: a `[gcode_macro CELL]` with variables persisted by `[save_variables]`.
  `CELL_REQUEST_ACCESS` is allowed only when idle/complete; it parks the toolhead rear-top, brings the bed to the transfer
  height, waits for temperature gates, turns the laser off and grants a **lease** the supervisor renews every few seconds.
  `PRINT_START` and move macros refuse while the arm holds it. `CELL_RELEASE_ACCESS` needs the arm's own state **and a
  physical "arm parked" switch** read by Klipper (`[gcode_button]`). A lease that expires with the arm inside keeps the
  printer locked and raises a fault.
- A supervisor state machine (SAFE_OFF, IDLE, PRINTING, COOLDOWN, ARM_ACCESS_REQUESTED, ARM_IN_PRINTER, ARM_TASK,
  PAUSED_PRESENCE, FAULT): one owner of the shared space at a time, every transition has a timeout, any unexpected value
  goes to FAULT, never "retry and continue".
- Compute: a **separate computer for the arm** (second Pi 5 or small PC) on the LAN; a fault in one must not stall the
  other. Sharing the printer's Pi is possible only for a Klipper-driven Cartesian.

### Safety

**Finding: printer_v12's power cut is software-only.** The mains contactor is switched from a Pi GPIO by Moonraker
(`[power printer] type: gpio, off_when_shutdown: True`). Every path that removes printer power runs through Klipper ->
Moonraker -> GPIO. If the Pi hangs, Moonraker crashes or the SD card corrupts, nothing removes power. The hotend has no
independent thermal cut-off (the bed has a 133 degC one). An e-stop that calls `printer.emergency_stop` has the same
weakness. This matters for the printer alone as soon as it runs unattended, before any arm exists
([07](arm_research/07_safety_cell.md) section 0).

**Recommended architecture: three independent layers** (07 section 6):

| Layer | Content |
|---|---|
| **A. Hardwired, no software** | E-stops, door interlock, smoke-detector relay and a heat bimetal in one de-energise-to-trip chain into a **dual-channel safety relay with manual reset** (the one part worth buying new). It drops **K1** (printer mains contactor, force-guided contacts with feedback) and **K2** (arm motor supply). The Moonraker GPIO and a supervisor relay sit in series **inside** the chain: software may open it, never close past it. Category 1 stop (K2 delayed ~0.5 s) unless the shoulder and elbow hold their pose unpowered. |
| **B. Firmware / supervisor** | Klipper `verify_heater` and limits, the CELL lock; arm speed modes, joint and Cartesian keep-out zones (printer envelope, a larger hot zone around the nozzle, PSU corner, laser plane), collision detection by current or following error, payload check after each pick, driver watchdog (~100 ms) |
| **C. Environment** | non-combustible bench, automatic clean-agent extinguisher above the printer, room smoke alarm, owner notification |

Design limits (07 section 3, conservative against ISO/TS 15066 orders of magnitude):

| Quantity | Target |
|---|---|
| Static force at the tool or any pinch point | <= 50 N, set by joint current/torque limits in the driver |
| Gripper finger force | <= 20 N, mechanically limited where possible |
| Tool speed, person possibly present | <= 250 mm/s (ISO 10218 reduced speed) |
| Tool speed, cell confirmed empty, door closed | <= 1000 mm/s |
| Collision reaction | stop within 50 ms; <= 10 mm extra travel at 250 mm/s |
| Gap between moving arm and fixed structure | >= 25 mm, or >= 120 mm where an arm or hand could enter |

Other rules: laser off whenever the door is open or the arm holds the lock (Class 1M: hazardous with optics); no mains on
the arm (24 V or less); each joint states its unpowered behaviour; the gripper holds its part on power loss; presence
sensors (mmWave, ToF) only slow or pause, never count as the safety layer; the arm and printer never move inside the
printer envelope at the same time; no unattended runs until layer C is installed and tested.

---

## 4. Kinematics: comparison and decisive tests (no choice yet)

Summary scoring from [01](arm_research/01_kinematics.md) section 6 (est.; 5 = best):

| Criterion | SCARA 4-DOF | Articulated 5/6-DOF | Front-loading Cartesian | Delta | Arm on rail |
|---|---|---|---|---|---|
| Horizontal entry at bed height | 5 | 4 | 5 | 1 | 5 |
| Top-down assembly | 5 | 4 | 5 | 5 | 5 |
| Tilted approach, door, in-hand flip | 2 | 5 | 2 (3 with tilt) | 1 | as base arm |
| Repeatability achievable | 4 | 2-3 | 5 | 4 | +1 over base |
| Stiffness under 20-100 N | 3 | 1-2 | 5 | 4 | as base |
| Actuator count / cost | 4 (~$350-700) | 2 (~$600-2,000) | 3 (~$500-1,000) | 3 | 2-3 |
| Printability of structure | 4 | 3 | 3 (rails bought) | 3 | 3 |
| Control effort | 3 | 1 | 5 | 5 | 2 |
| Twin / simulation effort | 4 | 2 | 5 | 4 | 3 |

Torque reasoning behind it ([02](arm_research/02_actuators.md) 1.1): an articulated shoulder at 0.6 m and 1 kg needs about
8.6 N·m static, 12-15 N·m peak (a counterbalance spring cancels most of it); a SCARA's horizontal joints carry no gravity
torque, and its Z axis lifts the load. The **angular error budget** drives more than torque: +/-0.1 mm at 500 mm allows the
shoulder about 0.2 mrad (~0.7 arcmin). An economy NEMA 17 planetary (<= 1-3 deg backlash) or a "high precision" one (~0.8
deg) moves the tool about 7 mm at 500 mm. Long-lever rotary joints therefore need zero-backlash reductions (capstan,
belt, strain-wave, preloaded cycloid) **and an encoder on the joint output**.

### Carry three into concept design

1. **SCARA 4-axis** (theta1, theta2, Z, roll; ~250 + 250 mm links, ~400 mm Z column, base ~300 mm in front of the printer).
   Natural fit to "horizontal pull at a height the printer chooses" plus top-down assembly. Gravity-free horizontal joints
   allow belt reductions and NEMA 17s. Needs stiff link cores, 14-bit output encoders on theta1/theta2, a flip tool as an
   end-effector.
2. **Front-loading Cartesian** (X ~1,000, Z ~400, a Y ram ~300 mm into the printer, plus roll). The precision and stiffness
   baseline: it can press inserts itself. Klipper drives it natively, so firmware-in-the-loop already exists and its twin is
   cheapest; the loop can start iterating soonest. Costs footprint and generality; ram sag is its design problem.
3. **Compact 5-axis articulated** (~450 mm reach, 4-DOF parallelogram class + wrist pitch; a short rail later if needed).
   The generality hedge: door, part flipping, approaches that design-for-assembly cannot remove. Its tests decide whether a
   rotary printed-reducer arm reaches +/-0.2 mm or precision work must go to stations.

Dropped: delta (cannot enter under the gantry), 6-DOF (prior art says avoid it unless a task needs it,
[03](arm_research/03_prior_art.md) 1.4; no Build 1 task does), mobile base (only useful with several printers).

### Decisive tests (cheap first; 01 section 8)

| # | Test | Decides | Pass (proposal) |
|---|---|---|---|
| 1 | **Reach and clearance sweep** (kinematic only): printer proxy with the opening, parked gantry, bed at transfer Z; sheet peel-and-pull path, rack and station poses | link lengths, Z stroke, base position; whether SCARA and 5-axis enter at all | all poses reachable with >= 15 mm clearance; straight sheet pull >= 240 mm |
| 2 | **Tool-point error Monte Carlo** (analytic): encoder resolution, backlash, belt stretch, link bending at 0.2/1 kg and 20 N per pose | whether SCARA and 5-axis meet the target or force a station; which encoder/reducer | 3 sigma <= 0.2 mm at insert/screw poses, <= 1 mm at sheet poses |
| 3 | **Single printed joint repeatability bench test**: printed belt reduction (SCARA) and printed cycloid or capstan (5-axis), 14-bit output encoder, 400 mm arm, dial indicator, 100 bidirectional approaches at 0.2 and 1 kg | real repeatability of our transmissions; **this one test decides rotary vs Cartesian for precision work** | <= 0.02 deg (~ +/-0.15 mm at 450 mm) |
| 4 | Insertion tolerance windows, using **the printer as a precise Cartesian robot** (offset 0-0.5 mm, tilt 0-3 deg over printed holes) | the real tolerance behind the +/-0.1-0.2 mm figure; what compliance and chamfers buy | largest offset with >= 98 % success |
| 5 | Sheet peel/pull force and reseat test (hand jig + force gauge) | gripper spec, payload, whether the shelf slide works | reseat >= 98 % |
| 6 | Link section stiffness (beam model now, FEA later) | printed vs aluminium-cored links; ram section | <= 0.1 mm under 20 N at the press pose |
| 7 | Control bring-up spike per candidate (1-2 days each) | real integration cost; sim-to-real gap on replay | twin vs measured tool pose within 0.5 mm |

Tests 1, 2 and 4 can start now. If printed rotary joints miss 0.02 deg, precision work goes to stations or the Cartesian
leads.

---

## 5. Actuators (brief; [02](arm_research/02_actuators.md))

Joint recipes, single-unit costs (est.) for the assembled joint, excluding printed plastic and the supply. Costs are for a
5-DOF arm + gripper servo:

| Recipe | Shoulder / elbow | Base | Wrist | Arm actuation total |
|---|---|---|---|---|
| **A. Budget stepper + zero-backlash printed reduction** | StepperOnline 17HS24-2104-ME1K closed-loop NEMA 17 (~$22) + MKS SERVO42D CAN driver (~$27; [Abra](https://abra-electronics.com/electromechanical/motors/motor-controllers/mot-servo42d-can-mks-servo42d-can-mb-closed-loop-stepper-motor-board-without-motor.html)); 2-stage printed capstan ~25:1 (~14 N·m); AS5047P or MT6835 output encoder; brake motor + counterbalance on the shoulder: **$80-130/joint** | belt or cycloid, $70-100 | 2x Dynamixel XL430 or 2x Feetech STS3215, $60-110 | **$400-600** |
| **B. BLDC FOC + capstan/cycloid** (02's recommendation) | ODrive M8325s + S1, or mj5208 + moteus-c1 ($143); printed capstan or preloaded cycloid 15-30:1; output encoder; pin brake + counterbalance: $200-400 shoulder, $170-200 elbow | $170-200 | XL430 x2 (~$100) to XM430 x2 (~$620) | **$800-1,300** |
| **C. Buy precision** | StepperOnline HSS-14-50 strain-wave (~$222, 20 arcsec) + closed-loop NEMA 17 + SERVO42D + AS5047P: ~$300/joint; or CubeMars AK80-9 ($480-580) | similar | XM430 x2 | **$1,300-1,900** |

B is recommended for contact tasks and twin fidelity: motor current gives joint torque (compliant insertion, collision
detection, dynamics identification). A is the fallback where cost matters more. Suggested first purchase: one B elbow
joint on a test fixture (test 3 above). SCARA and Cartesian need fewer, simpler drives (stepper + belt; the Cartesian
reuses printer-class HIWIN rails, GT2 belts and a Klipper board).

Other building blocks: [ROBOTIS XM430-W350, ~$310](https://robotis.us/dynamixel-xm430-w350-r) (wrist only);
[Feetech STS3215 12 V, ~$49 at RobotShop](https://robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215)
(gripper; ~1 deg backlash, so not for long joints); [SteadyWin GIM6010-8, ~$70](https://www.roboticscenter.ai/store/product/steadywin-gim6010-8-planetary-reducer-servo-motor/);
[ODrive S1, $149](https://shop.odriverobotics.com/products/odrive-s1);
[SparkFun 12 V vacuum pump, $25.50](https://www.sparkfun.com/vacuum-pump-12v.html) (no compressor needed).

**Real-part rule:** every chosen part must later have a maker, part number, US seller where one exists, maker CAD or a
faithful re-make, and datasheet ratings. Feetech and Makerbase publish no formal maker CAD (02 section 8): they need a
dimensioned maker drawing, or we prefer ROBOTIS and StepperOnline.

---

## 6. Digital twin and verifiers for the arm ([05](arm_research/05_digital_twin.md))

The arm goes through the printer's pipeline: a mechloop `Design`, all verifiers, a twin, pre-registered predictions,
measurement, learnings. `model.Joint` already supports `hinge` joints, `motion.py` already builds a MuJoCo model from the
CAD and runs inverse dynamics, and `twin/stepper.py` already models motor + series spring + backlash + friction.

### Carry over

| Printer verifier / module | Use on the arm |
|---|---|
| geometry, interference, assemblability, `dfm_*`, manufacture, purchased (DG-07), practice, fastener_stack, bearing | unchanged; they work on parts |
| motion (`sample_poses`, `colliding_pairs`, `build_mujoco`, `_dynamics`) | directly; extend with drivetrain bodies and dcmotor actuators |
| ratings (`resolve_drives`) | extend drive kinds: planetary, cycloidal, strain-wave, capstan, with ratio, efficiency, backlash, stiffness |
| FEA (Gmsh -> CalculiX) | link stiffness extraction (lumped springs, kept out of the time loop); load cases at worst pose with payload and peak acceleration |
| tolerance | kinematic parameter errors and backlash distributions (printed sigmas from `tolerance/process.py`) |
| thermal, electrical | motor and electronics heat; supply, gauges, fuses, motor peak current and regen |
| printing twin (PrusaSlicer -> Klipper offline -> physics -> deposit) | prints every arm and end-effector part first; its as-printed geometry feeds the grasp sim |
| `twin/stepper.py`, `twin/calibration.py` | stepper-driven joints; the blind predict-then-compare protocol, reused verbatim |
| belts | only for belt-reduced joints |

### New verifiers (12)

| # | Verifier | Pass (initial) |
|---|---|---|
| 1 | `arm_kinematics`: IK per task pose, manipulability, joint-limit margin | every task pose reachable, >= 5 deg margin, no path through a singularity |
| 2 | `arm_dynamics` (extends `motion._dynamics`): torque vs envelope at actual speed | peak <= available/1.5; RMS <= continuous; holding <= 50 % continuous or brake declared |
| 3 | `drivetrain_stiffness`: backlash + gearbox + link stiffness -> tool deflection | payload sag at full reach <= spec (e.g. 1 mm) |
| 4 | `arm_accuracy`: tolerance Monte Carlo -> predicted ISO 9283 repeatability, accuracy before/after calibration | RP 95th percentile <= target |
| 5 | `arm_cycle`: OMPL 2.0 path + Ruckig timing on the benchmark task | collision-free, >= 5 mm clearance incl. cables; cycle <= target |
| 6 | `arm_controller_loop` (software in the loop): our controller with a sim HAL drives the MuJoCo plant | no step loss or saturation; tracking error <= spec; stop distance inside the guarded zone |
| 7 | `grasp`: MuJoCo contact (condim 4/6, elliptic cones, noslip), friction randomized x0.6-1.0, Drake hydroelastic on worst cases | lower Wilson bound of success >= target per object |
| 8 | `vision`: field of view and occlusion over the task, simulated hand-eye error, marker detection | target visible >= 95 % of frames; reprojection <= 0.5 px |
| 9 | `joint_processes`: inserts, screws, press fits | margin >= 2 on pull-out / torque-out; press-fit retention in >= 99 % of samples |
| 10 | `arm_thermal`: duty cycle -> winding and mount temperature | below class limit and below PLA softening (~55 degC) at printed mounts |
| 11 | `cable_wrap`: bend radius and twist through joints | >= minimum radius, no snag over the mechanical range |
| 12 | `modal_arm`: first modes per pose | >= 3x controller bandwidth, or input shaping declared |

Plus the cell-level checks: printer and arm state machines exchanging the CELL handshake with fault injection, and the
safety checklist items in 07 section 9 that can be design-time checks (keep-out zones, pinch gaps, force caps).

### Controller in the loop (disagreement, partly resolved)

01 sees the Cartesian as Klipper-native and suggests a SCARA could feed host IK into Klipper `manual_stepper`; 05 says
Klipper is not arm firmware (no SCARA or serial-arm kinematics; [forum](https://klipper.discourse.group/t/feature-request-scara-kinematics/3650)).
**Resolution:** the Cartesian runs on Klipper and reuses `twin/firmware.py` unchanged. SCARA and articulated arms run a
host program we own (Ruckig on both the twin and the arm, so planned and executed profiles match) with a hardware
abstraction layer whose sim backend steps MuJoCo at the controller rate. Steppers emit step times and reuse
`twin/stepper.py`; BLDC drives are modelled as their PID with the gains from the same config we flash (no vendor simulator
exists). ROS 2 only if adopted later. Test 7 settles the SCARA question.

### Validation on the built arm

Frozen, hashed predictions with intervals before any measurement (as `twin/calibration.py`); any refit labelled "posthoc
(NOT blind)".

| Quantity | Measurement |
|---|---|
| Pose repeatability (ISO 9283-style: 5 poses, 30 cycles, 50/100 % speed, rated load) | three dial indicators on a tool ball/cube; wrist camera on a ChArUco plate |
| Backlash / lost motion per joint and at the tool | dial indicator at a known radius, torque reversal |
| Payload sag at 0/50/100/120 % load | indicator at the tool, extended pose |
| First modes | tap test with the ADXL345 already in the printer kit |
| Tracking error, torque | controller logs vs sim overlay |
| Cycle time, grasp success, motor temperature, insert pull-out | timestamps; 50 trials with Wilson interval; thermocouple; 5 coupons per size |

Pass: each measurement inside its pre-registered interval. Misses stay in the record and drive a posthoc update with
uncertainty, never a silent change of defaults.

### Coupling to the printer twin

- **One cell model**: the printer design is a body in the cell; collision checks use its real transfer Z and park pose.
- **End-effector geometry flows straight through the printer pipeline**: mechloop design -> PrusaSlicer -> Klipper
  offline -> printer twin's as-printed part -> grasp sim and FEA -> real print -> scan -> compare.
- The CELL handshake is simulated on both sides, so a whole cell run is one simulation.

---

## 7. End-effector loop ([04](arm_research/04_end_effectors.md))

### Tool interface

- **Maxwell kinematic coupling**: three steel balls on the tool, three V-groove pairs (steel dowel pins) on the arm flange;
  preload by magnets (v0), then a servo-turned cam or twist latch (v1), as the E3D / Jubilee changers do
  ([Jubilee, CC BY 4.0](https://github.com/machineagency/jubilee)). Wear surfaces metal, not printed.
- Spring-loaded pogo pins on a fixed pattern for power and signals, plus a 1-Wire tool ID. Vacuum on the tool or a
  dedicated tube, not through the interface at first.
- Expected repeatability with printed groove carriers 20-100 um (est.), better than the arm. The capture range (cones,
  chamfers) must exceed the arm's positioning error: the Berkeley printed changer's 8 failures in 100 came from arm error
  ([CASE 2018](https://goldberg.berkeley.edu/pubs/CASE2018-ron-tool-changer-submitted.pdf)).

### Tools, in build order

1. Parallel-jaw gripper on a serial-bus servo (reports position and load) with **swappable printed finger pads: the first
   closed loop**.
2. Maxwell tool plate + passive dock: iterate groove geometry; measure tool-change repeatability.
3. Vacuum tool (12 V pump, valve, pressure sensor, ~$25-40): flat parts and pick confirmation; the sheet-flex fixture.
4. Heat-set station (iron on a Z slide with load cell): iterate temperature / force / dwell, then the hole geometry.
5. Servo-cam latch (v1 interface), then the screwdriver.

First set BOM about **$200-300** (04 section 5).

### The loop

1. **Propose** a version from a parametric template (finger length, pad geometry, flexure thickness) with its target.
2. **Verify**: print DFM, FEA with declared print settings, `grasp` over randomized friction and pose, printer twin.
   MuJoCo ranks and prunes; **real tests are the score of record** (04: it does not predict slip force or flexure
   compliance without calibration).
3. **Print**: slice, upload and start through Moonraker; the owner approves each job at first (one touch), later only on a
   verifier warning.
4. **Unload and scan** (stages A, B); **mount** from the release tray into a rack slot (bootstrap: the owner fits the first
   coupling plates).
5. **Test** on a printed grasp benchmark set (cube, cylinder, sphere, thin plate, M3 nut, insert, slender part, curled
   corner): grasp success (lift, shake, place), placement error by fiducial, slip force on a load-cell coupon, cycle time,
   damage by before/after photo and scan, drift every N cycles. Each attempt logged with the tool's version hash.
6. **Learn**: measurement rows and ledger entries (`mechloop/data/learnings/ledger.jsonl`), e.g. pad friction on PLA,
   flexure stiffness predicted vs measured, insert depth vs dwell, each with prediction error before and after.
7. Next version until the target is met; "iterations to target" is a loop metric.

---

## 8. Perception and measurement ([06](arm_research/06_perception.md))

| Need | Plan |
|---|---|
| Wrist camera | one small global-shutter mono USB UVC camera (Arducam OV9281 class, ~$50-70) with an LED ring; 10-50 um lateral at close range |
| Fixed cameras | keep the printer's Pi Camera 3 overview and top-down for coarse checks (print present, failed, tray state) |
| Fiducials | ChArUco for intrinsic and hand-eye calibration; AprilTag 36h11 on beds, trays, fixtures; printed on paper, bonded to flat aluminium or glass (never printed plastic for metrology) |
| Hand-eye | OpenCV `calibrateHandEye` as a start, then joint bundle adjustment of hand-eye + kinematic parameters |
| Finding parts | prior knowledge first (G-code footprint, tray CAD with tagged kinematic pockets); vision only confirms and corrects; chamfers and compliance do the last millimetre |
| Force | joint current (free) + one single-axis load cell on the tool axis with a NAU7802 (~$20). DIY 6-axis (TAMS printed design) only if insertion data demand it; commercial 6-axis sensors ($4k-12k) cost more than the arm |
| Measuring the arm | ISO 9283 5-pose / 30-cycle protocol with three cross-checking instruments: dial indicators on a tool ball, the **flatbed scanner measuring placed tokens** (reuses `mechloop.inspect`), and **the printer as a reference stage** (Klipper drives the nozzle or top-down camera to known coordinates over a tag on the arm's tool; the arm-to-printer transform comes free) |
| Twin correction | least-squares identification of joint offsets, link lengths, axis misalignment, backlash, stiffness; leave-one-out validation; a PROPOSED learning with before/after error |

---

## 9. Prior art (brief; [03](arm_research/03_prior_art.md))

Lessons that shape this scope:
1. **Handle the sheet, not the print.** Working farm automation moves the substrate and releases parts by cooling and
   flexing ([SwapMod](https://hackaday.com/2024/09/30/3d-printer-swaps-build-plates-to-automate-print-jobs),
   [3DQue VAAPR](https://all3dp.com/1/3dque-quinly-review-automated-3d-printing/),
   [WPI bed-flexing MQP](https://digitalcommons.wpi.edu/mqp-all/289)). Add a grip tab and locating pins to our sheet.
2. **Repeatability claims in this class are mostly unmeasured.** Build our ISO 9283 fixture from day one.
3. **Close the loop at the joint output.** Unused encoders (AR4 MK3) and ~1 deg servo backlash (STS3215) are the documented
   failure modes; zero-backlash long-lever joints (Forte's capstan, 0.5 mm measured by its authors, arXiv 2507.15693) plus
   output encoders are the cheapest fix with evidence.
4. **Precision in fixtures and part features**, not the arm.
5. **Verify every step**: part-off detection is the most common unsolved complaint.

Reference arms: [Annin AR4](https://wiki.opensourceecology.org/wiki/AR4_Robot_Arm) (~$1,189 kit + ~$699 motors, backlash
reported), [PAROL6](https://github.com/PCrnjak/PAROL6-Desktop-robot-arm), [Arctos](https://hackaday.com/2023/05/08/arctos-robotics-build-a-robot-arm-out-of-3d-printer-spares),
[Faze4](https://github.com/PCrnjak/Faze4-Robotic-arm), [SO-100/101](https://github.com/TheRobotStudio/SO-ARM100),
[PyBot SCARA](https://hackaday.com/2020/10/19/pybot-is-a-3d-printed-scara-arm-for-the-masses). Borrow: Thor's "joint
angles as G-code" so the twin replays the same file; LeRobot's data format for demonstrations.

---

## 10. Loop metrics for the arm

| Metric | Definition | How measured |
|---|---|---|
| **Human touches per printed part** | manual interventions / parts off the printer | every manual action logged (one button or form entry; the touch count `record.loop_metrics` uses); part count from Moonraker and the arm log |
| **Unattended hours** | longest stretch, and hours per week, with zero touches | Moonraker job history + touch log |
| **Grasp / assembly success rate** | successes / attempts per task and tool version, with Wilson interval | supervisor result per attempt, confirmed by camera, scale or scan |
| **End-effector iterations to target** | versions printed until the target is met | ledger entries per tool |
| **Cycle time** | per task and per loop (design change -> measured) | arm log + Moonraker timestamps; design change from git |
| **Fidelity** | prediction vs measurement (repeatability, sag, cycle, grasp success) | pre-registered predictions vs measured, in the ledger |

---

## 11. Budget, disagreements, risks, open questions

### Combined budget range for Arm Build 1 (est.; arm + cell, printer excluded)

| Item | SCARA 4-axis | Front-loading Cartesian | Compact 5-axis (recipe A / B / C) |
|---|---|---|---|
| Actuation | $350-700 | $500-1,000 | $400-600 / $800-1,300 / $1,300-1,900 |
| Structure: plates, bearings, rails, fasteners (est.) | $200-600 | $200-600 | $200-600 |
| Controllers, arm computer, CAN, 24 V supply (est.) | $150-400 | $100-300 (Klipper board) | $150-400 |
| End-effector set, tool changer, heat-set station (04) | $200-300 | $200-300 | $200-300 |
| Perception and measurement: wrist + metrology cameras, load cell, indicators (06, est.) | $250-350 | $250-350 | $250-350 |
| Safety layers A and C: safety relay, e-stops, interlock, contactor, extinguisher, smoke relay (est.) | $200-500 | $200-500 | $200-500 |
| Stations: sheet shelf + flex fixture, press, screw presenter, trays (est.) | $100-300 | $100-300 | $100-300 |
| **Total** | **$1,450-3,150** | **$1,550-3,350** | **$1,500-3,050 / $1,900-3,750 / $2,400-4,350** |

**Overall: about $1,500-4,400; most likely $2,000-3,000.** Excludes a commercial 6-axis F/T sensor and shipping. Part of
the safety layer (hardwired e-stop chain, hotend cut-off) is worth adding to the printer itself regardless.

### Disagreements between the research files (stated, with the position taken here)

| Topic | Positions | Taken here |
|---|---|---|
| Sheet removal | 01: slide out to a shelf (8 mm sag when lifted); 03/04: lift off the magnets, carry and flex | **slide to a shelf at bed height, flex there**; test 5 confirms |
| Klipper for the arm | 01: Cartesian native, SCARA via host IK + `manual_stepper`; 05: Klipper is not arm firmware | Cartesian on Klipper; SCARA/articulated on our own host controller; test 7 settles SCARA |
| Third architecture | first draft: 6-DOF; 01/03: compact 5-axis, avoid 6-DOF unless needed | **compact 5-axis** |
| Insert tool | owner's list implies an arm-held hot tip; 01/03/04: fixed press station | **fixed station**; arm loads it |
| Insert temperature | print temp + 10-20 degC (Prusa) vs 343-399 degC iron (LulzBot) | coupon sweep at the station |
| Printed structure and reducers | 01/02/03 assume printed links, capstan drums, cycloid discs; **DG-01 forbids printed parts in a load path** | **open: owner decision** (question 1); default metal-cored links |
| Gripper servo | 04: Feetech STS3215; 02: Feetech lacks maker CAD (DG-07) | prefer a ROBOTIS servo unless Feetech gives a dimensioned drawing |

### Risks

| Risk | Mitigation |
|---|---|
| Printed rotary joints miss 0.02 deg | test 3 before committing; stations; Cartesian leads |
| Sheet does not slide or re-seat reliably | locating pins + grip tab (a printer change); Eddy + camera check before every print; test 5 |
| DG-01 blocks printed reducers, links or end-effectors | owner waiver scoped by part type, or metal cores with printed covers |
| Printed parts creep under constant gravity load (capstan drums, cycloid discs) | counterbalance, CF-filled materials, metal pins, a creep test |
| Software-only power cut (exists today on the printer) | hardwired layer A before any unattended run, printer included |
| Unattended fire risk | layer C installed and tested first |
| Printer not built yet; owner has no printer | concept design now; first tools from the print service; arm hardware after the printer runs |
| Stale prices and sold-out parts (ODrive kit, XM430) | live re-check at the gate |
| Scope creep | stage gates; stage A first |

### Open questions for the owner

1. **DG-01**: may the arm use printed load-bearing parts (capstan drums, cycloid discs, links, end-effector bodies behind a
   metal coupling) under a scoped waiver, or must links and reducers be metal?
2. **Bench**: size, against a wall? Room for ~1 m of Cartesian X in front of the printer?
3. **Printer changes for the arm**: add sheet locating pins + grip tab, a front purge position, and a hardwired e-stop /
   contactor chain and hotend cut-off (worth doing in v12.x even without the arm)?
4. **Door**: motorise the V13 door on Klipper (recommended), or have the arm open it?
5. **Filament, spool, nozzle tasks**: drop from Arm Build 1 (recommended)?
6. **Budget ceiling** for Arm Build 1 (range above: $1,500-4,400)?
7. **Air**: compressed air available, or vacuum pump only?
8. **Compute**: separate arm computer (recommended), or share the printer's Pi?
9. **First assembly target** for stage C: the arm's own gripper, or a printer sub-assembly such as a camera mount?
10. **People in the room** during unattended runs: collaborative limits only, or a guarded cell with a door interlock?
11. Confirm the stage targets in section 1 and the 1 kg / 0.2 mm requirements.

---

## 12. Next steps: concept design spike, in parallel with the printer build

The printer build comes first and is not slowed. The spike is design work plus a few cheap physical tests (owner's
caution: design is cheap, build late). Arm hardware is ordered only once the printer runs its first closed loops.

| Step | Work | Output | Weeks (est.) |
|---|---|---|---|
| 1 | Cell model with a light printer proxy (envelope, opening, bed transfer Z range, gantry park) once the v12 build finishes; stations placed | `designs/arm_cell.py` (proxy only, no heavy imports) | 0.5 |
| 2 | Task pose list and trajectories for stages A-D with payloads and forces | data file + requirements | 0.5 |
| 3 | Decisive tests 1 (reach sweep) and 2 (error Monte Carlo) on three skeleton arms (`design.exploratory = True`) | scored comparison | 1.5 |
| 4 | Verifiers, minimum set: `arm_kinematics`, `arm_dynamics`, `drivetrain_stiffness`, `arm_accuracy` | code + tests | 2 |
| 5 | Physical tests: test 3 (one printed joint, recipe B elbow), test 4 (insertion windows on the printer, once it runs), test 5 (sheet peel/pull, hand jig), coupling and finger coupons from the print service | measured numbers in the ledger | parallel, ~2-3 |
| 6 | Pick one architecture (or two); owner review | decision record | 0.5 |
| 7 | Detailed design of the arm, end-effector interface and stations; same buildability gate as the printer (zero placeholders) | Arm Build 1 package | 3-4 |
| 8 | Order and build after the printer's first closed loops; stage A first | - | - |

Steps 1-5 fit inside the printer's ordering and lead-time window (print service 4-11 days; long-lead parts longer).

**Steps 1-3 done (2026-11-21):** [ARM_CONCEPT_SPIKE.md](ARM_CONCEPT_SPIKE.md). All three skeletons pass tests 1 and 2 only with
the parts listed there; recommendation: keep the Cartesian (lead) and the 5-axis, drop the SCARA; tighten test 3 to about +/-0.016 deg.

## Owner decisions (2026-11-21)

- Design our own arm, run through the same loop (digital twin, verifiers, pre-registered validation).
- Load-bearing 3D-printed parts are fine for the arm (DG-01 arm exception in docs/DESIGN_GUIDELINES.md, with FEA on
  printed properties, a creep check and a measured test as the safeguard).
- Floor space for the cell is not a constraint (the front-loading Cartesian stays a candidate).
- Printer changes adopted: flex-sheet locating pins and grip tab so the sheet slides out to be flexed; purge at the front;
  hardwired e-stop and safety relay (added to printer_v12 now).
- Budget: no hard ceiling, but a few thousand dollars or less for Arm Build 1.
- Kinematics stay open as design research (SCARA, front-loading Cartesian, compact 5-axis carried forward).
- Stage C revised (owner comment on the doc, 2026-11-21): start with simple assemblies (2-3 printed parts joined by screws
  into captured nuts) and grow in complexity. Which further operations and stations come next (heat-set inserts, press-fit
  bearings, magnets, others) stays open, added only when a target assembly needs them. The live, commentable version of
  this scope is the Claude Doc "Robot Arm Scope" (https://claude.ai/artifact/96CZGsQoQJbsV2aMJt1LwS).
- Stage D reframed (owner comment, 2026-11-21): "building tools for itself". Each tool starts from a concrete goal, is then
  generalized (parametric, standard coupling, documented capabilities and limits) and kept in a reusable tool library; new
  jobs check the library first. Success needs at least one tool reused on a job it was not first built for; tool reuse
  (jobs served per tool) is a loop metric.
- Inspection method left open (owner comment, 2026-11-21): vision/scanning is the ideal, but contact tools (digital
  calipers, pin gauges, indicators) in an arm-loaded fixture, or by hand at first, may be needed; the arm presents each part
  to whichever method a dimension needs. See docs/INSPECTION_STRATEGY.md.
- No dedicated work cell for now (owner comment, 2026-11-21): the arm is small and low-force, so it sits on the bench in
  front of the printer with whatever stations a job needs. Kept: the Klipper/Moonraker handshake and light safety (shared
  hardwired e-stop also cutting arm motor power, 24 V, current-limited joints, laser off with the arm inside). Detailed
  cell layout, standards and guarded-cell items are deferred.
- Open-source 5-axis references (owner comment, 2026-11-21): SO-100/SO-101 (5 + gripper, Feetech servos, LeRobot
  ecosystem; https://github.com/TheRobotStudio/SO-ARM100), BCN3D Moveo (5 axes per BCN3D, printed;
  https://github.com/jsechovec/BCN3D-Moveo), DEXTER (5 axes, harmonic drives, carbon tubes), Koch v1.1 (Dynamixel, LeRobot;
  https://github.com/jess-moss/koch-v1-1), UtiliArm (fully printed, link to confirm), Forte (printed capstan drives,
  sub-mm measured; arXiv 2507.15693). Likely route: Moveo/DEXTER layout + LeRobot software conventions + capstan long joints.
- Fixed cameras (owner comment, 2026-11-21): overhead plus 2-3 side cameras around both the printer and the arm (frame or
  light stand) to watch moves, confirm picks/placements, see trays and stations, track the tool by its tag and give the twin
  ground truth; the printer's two Pi cameras are part of the set, extra cameras over USB or on the arm computer.
- Door (owner comment, 2026-11-21): the arm opens the V13 door; it stays a plain manual door so a person can open it too
  (no Klipper door actuator).
- Filament, spool and nozzle tasks: dropped from Arm Build 1 (owner, 2026-11-21).
- Air (owner, 2026-11-21): no shop air; a small 12 V vacuum pump only if a suction tool earns its place; no compressor.
- Compute (owner, 2026-11-21): a separate arm computer.
- People in the room during unattended runs (owner, 2026-11-21): not a concern for now; deferred.
- Stage targets and requirements (owner deferred to the design agent, 2026-11-21): keep the 1 kg payload, since the sheet
  pull sets it (sheet + print + tool about 0.8 kg). Keep 0.2 mm (3 sigma) at assembly poses as a provisional target; test 4
  (the printer used as a precise Cartesian robot) measures the real insertion window with chamfers and compliance, and that
  number replaces it. A wider window (about 0.5 mm) would make printed rotary joints viable. Sheet poses: 1 mm.
