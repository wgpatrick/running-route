# Arm Build 1: scoping the robot arm that works with the printer

Status: scoping draft (2026-11-21). Nothing here is designed, simulated or built. Every number is an **estimate** or an
**assumption** unless a source is given; prices are web snapshots and must be re-checked live before any order (DG-07).

Detailed research behind this synthesis lives in `docs/arm_research/`:
[01 kinematics](arm_research/01_kinematics.md), [02 actuators](arm_research/02_actuators.md),
[03 prior art](arm_research/03_prior_art.md), [04 end-effectors](arm_research/04_end_effectors.md),
[05 digital twin](arm_research/05_digital_twin.md), [06 perception](arm_research/06_perception.md),
[07 safety and cell](arm_research/07_safety_cell.md). This file is the top-level scope; the survey sections below are kept
short on purpose.

**Owner decisions so far**
- We **design our own arm** (not buy one), with the same mechloop loop as the printer: real purchased parts (DG-07),
  generated fabricated parts, every verifier, a digital twin, pre-registered predictions, measured results in the ledger.
- The arm (a) **assembles** printed parts with off-the-shelf parts and (b) **operates the printer**.
- The printer **makes the arm's end-effectors**, so the arm improves by working with the printer.
- **Kinematics stay open**: SCARA, articulated, Cartesian and others are compared against the tasks below.

---

## 1. Goal, and how it serves recursive self-improvement

The roadmap's loop is: make a part, measure it, learn, improve the part and the loop. Today a human closes every step
that touches the physical world: take the print off, put it on the scanner, assemble it, start the next job. The loop's
**autonomy** metric (human touches per iteration) cannot improve past that. The arm is the loop's first **handling and
assembly tool**, the way the printer is its first fabrication tool.

It serves the goal three ways:
1. **Autonomy.** The arm removes the human from the print -> measure -> next-print cycle. Loop time drops from "when the
   owner is home" to minutes.
2. **A second improvement loop that the system owns end to end.** End-effectors are designed by mechloop, printed on our
   printer, unloaded and inspected by the arm, mounted by the arm, tested by the arm, and the result goes in the ledger.
   No human is needed between design change and measured result. This is the first loop where that is possible.
3. **Assembly.** Assembling printed + purchased parts makes the system able to build sub-assemblies (and later its own
   fixtures, tools and upgrades), which the roadmap names as the path to improving the loop itself.

### What "done" means for Arm Build 1 (staged)

Each stage is a gate with a measured pass figure (targets are **proposals** for the owner to confirm).

| Stage | Capability | Done when (proposed) |
|---|---|---|
| **A. Unload** | Lift the spring-steel PEI sheet off the printer, release the print at a flex station, clear purge, put the sheet back, start the next queued job | 100 cycles of mixed PLA/PETG prints, >= 95 % with zero human touches; sheet re-seated within +/-0.3 mm (checked by the Eddy probe and the top-down camera); no PEI damage visible in scans |
| **B. Inspect** | Pick the part from the release tray, place it on the flatbed scanner or camera stage, trigger the scan, file the result, sort the part into a tray | 50 parts measured end to end with zero touches; measurement rows written by `mechloop.inspect` with `who = "arm"`; placement repeatable within +/-1 mm and +/-2 degrees |
| **C. Assemble** | Heat-set inserts, M3 screws, press-fit bearings, magnets, on fixtured printed parts | Each operation >= 95 % over 50 tries (insert depth +/-0.2 mm, tilt < 2 deg; screw torque +/-15 %; bearing seated flush within 0.1 mm; magnet polarity and depth right), then one real sub-assembly built unattended (e.g. a camera mount, or the arm's own gripper) |
| **D. Tool change** | Swap printed end-effectors on a quick-change coupling from a rack; the loop prints, mounts and tests a new version | 200 changes >= 99 % success; coupling repeatability <= 0.05 mm measured; >= 3 tools in use; one end-effector taken through >= 3 loop iterations to its target with no human design step |

D is listed last but its coupling is designed first: stages A to C each want a different tool.

---

## 2. Task catalogue

Printer facts used (from docs/PRINTER_V12.md, docs/PRINTER_V11.md, docs/V13_IDEAS.md): 2020 frame 388 x 419.5 x 476 mm;
**front side has no Z rail** (Z rails left, right, rear) and gets the hinged door in V13; 220 x 220 textured PEI on
0.4 mm spring steel on a magnetic base; print area 186.6 x 208.1 mm, Z 180 mm; bed moves in Z; Klipper on Octopus + Pi 5
with Moonraker; Eddy probe, overview and top-down cameras, Class 1M line laser; Roto extruder fed by PTFE from a 1 kg spool
**at the rear**; Revo hotend; PLA/PETG only.

Estimated access (to be measured from the model in the spike): front opening about 340 mm wide between the posts; bed
surface roughly 150 to 350 mm above the bench depending on Z; rear edge of the sheet about 330 mm behind the front face.
With the arm base about 150 mm in front of the printer, the tool must reach **about 480 to 550 mm horizontally** and
enter **roughly horizontally** under the gantry.

### 2.1 Printer operation

| Task | Realistic for Build 1? | Payload | Force / torque | Accuracy / repeatability | Workspace | Cycle time | Sensing |
|---|---|---|---|---|---|---|---|
| **Lift the flex sheet off and replace it** (primary unload method) | **Yes** | sheet ~0.15 kg (0.4 mm steel, 220 x 220) + print up to ~0.5 kg + tool ~0.2 kg: **~0.85 kg** | peel off the magnet from one edge: ~10-40 N (estimate; measure) | grasp the sheet tab +/-1 mm; replace +/-0.3 mm (needs locating pins or stops on the bed: **open question**) | into the printer through the front, bed lowered to a fixed unload Z | 60-120 s round trip | sheet-present check (Eddy probe reading at a fixed XY; top-down camera), gripper contact switch |
| **Release the print from the sheet** (off the printer) | **Yes** | as above | flex the sheet over a fixed mandrel (the arm bends it); the station does the work | +/-2 mm | flex station beside the printer | 20-40 s | camera: print gone from sheet; tray load cell (optional) |
| Scrape the print in place | **No** (avoid) | tool only | 20-50 N tangential (estimate) | +/-0.5 mm in Z or it gouges the PEI | inside the printer | 30 s | force |
| Clear purge line / blobs | Yes, with the sheet (purge on the sheet goes with it); brush or vacuum on the flex station | <0.1 kg | <5 N | +/-2 mm | flex station | 10 s | camera |
| Open / close the V13 front door | Possible; **recommend a door actuator on Klipper instead** | - | hinge torque low; door polycarbonate | +/-3 mm on a handle | front face | 5 s | door switch |
| Load / unload filament | **No** for Build 1 | - | - | feeding a 1.75 mm tip into a PTFE tube: <0.3 mm | spool and tube at the **rear** | - | - |
| Change the spool | **No** for Build 1 | 1.25 kg | lift off the axle | +/-2 mm | **rear** of the printer, out of a front-mounted arm's reach | - | - |
| Swap a Revo nozzle | **No** (stretch, later) | <0.05 kg | hand-tight, low torque | <0.2 mm, under the toolhead | top of the machine, from below | - | camera |

Why not scrape in place: the bed's thumb-nut washers are designed to **slip** on the deck under heat (PRINTER_V12,
"Bed"); a lateral load on the bed could move it and invalidate the mesh. Lifting the sheet puts almost no load on the bed.

Filament and spool tasks need a front-mounted arm to work at the rear, or a printer change (front spool or a filament
changer). Defer them to a later build; Klipper's own unload macro covers the unload half.

### 2.2 Inspection handling

| Task | Payload | Force | Accuracy | Workspace | Cycle | Sensing |
|---|---|---|---|---|---|---|
| Place a part face-down on the flatbed scanner glass, scan, pick it up | <0.3 kg | <5 N (do not press the glass) | +/-1 mm, +/-2 deg; part flat | scanner station, glass ~220 x 300 mm | 30 s handling + scan time | camera confirms placement; scan result itself |
| Lid handling | - | lift a hinged lid | +/-3 mm | scanner | 5 s | - |

The scanner lid is a problem for an arm. Options for the spike: remove the lid and use a fixed dark hood over the glass
(the scan pipeline needs a dark part on a light background, docs/INSPECTION.md: so a light hood instead); or let the arm
lift it with a hook. A camera stage (fixed camera over a backlit plate, calibration target in view) is the fallback for
parts that are not flat.

### 2.3 Assembly

| Operation | Payload | Force / torque | Accuracy | Cycle | Sensing / tool |
|---|---|---|---|---|---|
| **Heat-set insert** (M3, brass) | tool ~0.1-0.2 kg incl. heater | press 20-50 N (estimate) | axis +/-0.2 mm, tilt < 2 deg, depth +/-0.1 mm | 10-20 s (dwell 3-8 s) | hot tip at print temperature + 10-20 degC ([Prusa / CNC Kitchen insert listing](https://www.prusa3d.com/product/heat-set-inserts-m3-standard-100-pcs/)): ~220-260 degC for PLA/PETG; tip thermistor, Z position, force or motor current |
| **M3 screw** | screwdriver tool ~0.2 kg | 0.4-1.2 N·m (estimate: lower into inserts and plastic, higher steel-on-steel) | +/-0.3 mm to the hole | 10-20 s | torque by motor current or slip clutch; angle count to detect cross-threading; screw presented by a feeder |
| **Press-fit bearing** (e.g. 608 into a printed seat) | <0.1 kg part | 50-200 N (estimate, depends on interference) | +/-0.1 mm, square | 10 s | **a press station** (arm loads, press pushes) rather than the arm pushing |
| **Magnet** (e.g. 6 x 3 mm NdFeB) | tiny | snap-in, <20 N | +/-0.3 mm; polarity | 5 s | non-magnetic fingers, a tube dispenser that fixes polarity |

Consequences:
- DG-04 says screws through printed parts are **through-bolts with a nut**. A single arm cannot hold the nut on the far
  side. Assembly tasks should use **nuts captured in printed pockets** (already DG-04's first fallback), or a fixture that
  holds the nut. This is a design rule the arm work will push back into the guidelines.
- High forces (press fits) go into **station fixtures**, not through the arm. The arm then needs only ~1 kg payload and
  ~50 N push, which keeps every architecture affordable.
- Heat-set inserts are also restricted by DG-04 (allowed with a written reason). They are in scope as a capability the
  owner asked for, not as a change to that rule.

### 2.4 Requirement summary (drives the kinematics comparison)

| Requirement | Value (estimate) | Hardest task |
|---|---|---|
| Payload incl. tool | 1.0 kg | sheet + large print |
| Horizontal reach | 480-550 mm | rear edge of the sheet |
| Vertical range | ~400 mm (bench trays to raised bed) | trays vs bed |
| Approach | horizontal into a ~340 mm wide opening under the gantry | sheet grasp |
| Repeatability at the tool | 0.1 mm (assembly), 0.3 mm (sheet) | inserts |
| Push along the tool axis | 50 N | inserts |
| DOF needed | X, Y, Z + yaw minimum; tilt for flexing / angled approach optional | - |
| Cycle | full unload < 3 min | stage A |

---

## 3. Work cell

### Layout (proposal)

```
                 wall / rear (spool, electronics bay side)
        +------------------------------------------+
        |              PRINTER v12                  |
        |   (door = front, no Z rail on this side)  |
        +------------------------------------------+
   [tool rack]   [flex / release station]   [scanner + camera stage]
        [fastener feeders]   ARM BASE   [press station]
             [parts trays / kitting]   [finished tray]
                      front of the bench (human side)
```

- The arm stands **in front of the printer**, centred on the door. Everything it serves sits in an arc in front: flex
  station, scanner, camera stage, tool rack, feeders, press station, trays.
- Bench footprint (estimate): 1.0-1.2 m wide x 0.8-0.9 m deep, printer included. **Open question**: what bench the owner has.
- The cell is drawn as one mechloop `Design` (printer as a fixed body with its moving bed and gantry, arm, stations), so
  interference and reachability are checked over the whole cell.

### Coordination with the printer

- **Moonraker JSON-RPC over its websocket** for state and commands: query or subscribe to `print_stats` (state, filename)
  and run G-code macros ([Moonraker printer API](https://moonraker.readthedocs.io/en/latest/external_api/printer/),
  [printer objects](https://moonraker.readthedocs.io/en/stable/printer_objects/)). Moonraker's docs warn not to rely on
  catching async state changes at connect: query state on connect, then subscribe.
- Handshake (proposal): `END_PRINT` parks the toolhead at the rear top, lowers the bed to a fixed `UNLOAD_Z`, waits for
  the bed to cool (PEI releases cool; target < 35 degC, estimate), turns the laser off, then sets a `ready_for_unload` flag.
  The arm unloads, replaces the sheet, and calls `SHEET_CHECK` (Eddy reading at a known XY + top-down photo). The arm
  controller (or the existing agent loop) then starts the next queued job.
- **Separate computer for the arm** (a second Pi 5 or a small x86 PC; decision in the spike), on the LAN with the printer
  Pi. Reason: a fault in one must not stall the other, and the arm planner may need more CPU than the Pi spare. Sharing the
  printer's Pi is possible for a Klipper-driven Cartesian arm.
- **Hardware interlocks are wired, not networked**: an "arm in printer" signal (beam break across the door opening plus the
  arm's own state) holds the printer's motion; a "printer moving" signal holds the arm out.

### Safety

| Hazard | Mitigation (proposal; detail in [07 safety and cell](arm_research/07_safety_cell.md)) |
|---|---|
| Pinch / crush between arm and printer frame or stations | speed and force limits near fixed objects; torque/current limit per joint; collision checks in the twin over every task trajectory |
| Hot nozzle (up to ~260 degC) and bed | toolhead parked at rear top before the arm enters; arm never plans within a keep-out box around the hotend; heater state checked before entry |
| Hot insert tip | tip parked in an insulated holder; heater off when the tool is racked; Klipper-style thermal runaway checks on the tip heater |
| Class 1M line laser | laser output pin off whenever the door is open or the arm is in the printer; arm cameras never aimed into the beam |
| People near an unattended arm | e-stop mushroom cutting motor power to **both** machines through hardware (in series with the printer's contactor chain); low-power collaborative limits or a guarded cell (owner decision) |
| Dropped sheet / part | grasp check before lift; slow moves while carrying the sheet |

---

## 4. Kinematics research plan (no choice yet)

### Candidates scored against the task catalogue

Scores 1 (poor) to 5 (good), **first-pass judgement, to be replaced by simulation**.

| Architecture | Reach in through the front | Accuracy / stiffness | Payload 1 kg at 0.5 m | Cost | Printability / our process rules | Controllability | Verifiability with our tools | Notes |
|---|---|---|---|---|---|---|---|---|
| **SCARA + tall Z** (+ optional wrist roll/tilt) | 5 (horizontal approach is natural) | 4 (gravity taken by the Z rail, not the joints) | 4 | 4 | 4 (plates, extrusion, bought bearings) | 3 (no native Klipper SCARA ([forum](https://klipper.discourse.group/t/feature-request-scara-kinematics/3650))) | 5 (few joints, planar) | cannot tilt for flexing without a wrist |
| 4/5-DOF articulated | 3 | 2-3 | 2-3 (shoulder carries gravity) | 3 | 3 | 3 | 4 | cheaper than 6-DOF, loses arbitrary tool orientation |
| **6-DOF articulated** | 4 | 2-3 (backlash and compliance stack up) | 3 | 2 | 3 | 2-3 (needs IK, planner; ROS 2 / MoveIt class) | 4 | most flexible: door, angled approaches, flexing in the hand |
| **Cartesian gantry + horizontal ram** (a forklift-like Y fork that reaches into the printer) | 4 | 5 | 5 | 5 | 5 (reuses printer parts: HIWIN rails, GT2 belts, 2020) | **5** (Klipper `generic_cartesian` ([thread](https://klipper.discourse.group/t/new-generic-cartesian-kinematics-incl-corexyu-corexyuv-generic-idex-and-awd/17510)), so Klipper-offline-in-the-loop already exists) | 5 | big footprint over the cell; ram cantilever sag is the design problem |
| Delta | 1 (approaches from above; cannot enter under the gantry) | 4 | 2 | 3 | 3 | 4 | 3 | dropped |
| Mobile base / linear-rail-mounted arm | 3-4 | 2 | 3 | 1-2 | 2 | 2 | 2 | only useful with several printers; dropped for Build 1 (a rail under a SCARA or articulated arm stays a later option) |

Torque check behind the "payload" column (estimate): 1 kg at 0.5 m is ~4.9 N·m at the shoulder, plus ~2-4 N·m of link mass,
so an articulated shoulder needs ~15-20 N·m with a factor of 2 (a NEMA 23 with a 10-20:1 gearbox, or a geared BLDC). A SCARA
shoulder carries no gravity torque, only inertia; its Z axis lifts the load through a screw or belt.

### What simulations decide it

| Question | Simulation | Verifier |
|---|---|---|
| Can it reach every task pose, entering through the opening without touching the frame? | IK over the task pose list; swept-volume collision against the cell model over full task trajectories | new reachability + extended `motion` |
| Is it accurate enough at the tool under 1 kg? | FEA of links and bearing compliance at 3-5 poses; backlash and joint stiffness in series; stack-up of joint tolerances to tool error | `fea`, extended `tolerance.stackup` |
| Are the drives big enough and the cycle fast enough? | MuJoCo inverse and forward dynamics on the stage A trajectory with torque-speed curves | extended `motion` / `sim` |
| Can the controller do it? | controller-in-the-loop: the real planner (Klipper offline, or the arm's planner) drives the MuJoCo model | new |
| What does it cost and can it be bought? | BOM with DG-07 parts and live prices | `ratings`, `purchased` |

### Recommendation: carry three into concept design

1. **SCARA with a tall Z axis.** Best fit to "reach in horizontally under the gantry". Gravity goes into a linear rail,
   so cheap steppers and plates give good stiffness and 0.1 mm-class repeatability. Few joints: easy to verify.
2. **Cartesian gantry with a horizontal ram.** Cheapest, stiffest, most accurate, built from parts and verifiers we
   already have, and **Klipper drives it natively**, so firmware-in-the-loop is already solved. Its risk (footprint, ram
   sag at 330 mm reach) is exactly what FEA answers.
3. **6-DOF articulated (stepper + cycloidal/planetary).** The only candidate that can open a door, flex a sheet in hand
   and approach at angles. It tests how far our verifiers stretch (serial-chain compliance, IK, planning). Carried as the
   capability benchmark, knowing it is the most expensive and least stiff.

The 4/5-DOF articulated arm is the fallback if the 6-DOF is too costly; delta and mobile are dropped.

---

## 5. Digital twin and verifiers for the arm

The arm goes through the same pipeline as the printer: a mechloop `Design`, all verifiers, a twin, pre-registered
predictions, measurement, learnings. Detail: [05 digital twin](arm_research/05_digital_twin.md).

### Carry over as-is

| Verifier / module | Use on the arm |
|---|---|
| `geometry`, `interference`, `assemblability` | per-part validity, static clearances, assembly-by-disassembly of each joint and link sub-assembly |
| `manufacture` + `dfm_*` (sheet, CNC, print), `dfm_supplier`, `dfm_process_rules` | links and plates at SendCutSend / Xometry; printed end-effectors at the print service, then on our printer |
| `purchased` (DG-07), `practice` (DG-01..06), `fastener_stack`, `bearing` | real-part rule, owner's practice, screw stacks, head bearing |
| `warp`, `dfm_print` | printed end-effectors |
| **Printing twin** (PrusaSlicer -> Klipper offline -> stepper/belt/frame -> deposit) | every printed end-effector is printed on the **printer twin** first; its predicted as-printed geometry feeds the grasp simulation |
| `electrical` | wiring, supply sizing, current per wire, stepper torque at speed, heater simulation (insert tip) |

### Extend

| Module | Extension |
|---|---|
| `motion` (sweep + MuJoCo inverse dynamics; already handles `hinge` joints) | sweep **task trajectories**, not only joint-space corners; collision against the whole cell including the printer's bed and gantry positions |
| `sim` (MuJoCo forward dynamics, PD servo) | gearbox **backlash** and joint **compliance**, motor **torque-speed curves**, closed-loop stepper / FOC current limits; tracking error at the tool |
| `fea` (Gmsh + CalculiX) | link cases at several poses; bearings and gearboxes as springs from datasheet stiffness; result = **tool sag and repeatability under payload** |
| `ratings` | crossed-roller / angular-contact moment ratings, gearbox rated and peak torque, backlash from datasheets |
| `tolerance.stackup` | serial chain: joint and part tolerances to tool position error; what calibration recovers |
| `subsystems` | homing per joint, cables through rotating joints, tool-changer electrical contacts |
| `twin.calibration` (blind predict-then-compare) | the same protocol for arm repeatability, backlash, sag and cycle time |

### New

| Verifier | What it checks |
|---|---|
| **Reachability / workspace** | IK for every task pose in the cell, joint-limit margin, manipulability, approach through the front opening |
| **Controller-in-the-loop** | the arm's real planner and firmware run offline and drive the twin, as Klipper offline does for the printer (Klipper itself for the Cartesian; the planner / closed-loop driver firmware for SCARA and articulated) |
| **Grasp and contact** | MuJoCo contact: friction, compliant fingers, sheet peel and flex; grasp success over pose noise |
| **Process models** | heat-set insert (temperature, force, depth over time), screw driving (torque-angle, cross-thread), press fit (interference vs force, from the printed material's modulus), magnet insertion; each calibrated by coupons |
| **Vision in sim** | render the cell cameras from the CAD; fiducial and part-pose error; synthetic images for grasp checks (detail: [06 perception](arm_research/06_perception.md)) |
| **Cell coordination** | printer and arm state machines exchanging the Moonraker handshake, with fault injection (sheet missing, print stuck, door open) |
| **Safety** | speed and force at contact, pinch gaps between the arm and fixed objects along every trajectory |

### Validation against the built arm

- **Pre-registered predictions**, frozen before measuring (as in `twin/calibration.py`): repeatability at the tool (ISO
  9283-style, 30 cycles to 5 poses), backlash per joint, sag under 0.5 and 1 kg at three poses, maximum speed, stage A
  cycle time, grasp success rate per tool.
- Measured with a dial indicator, the cell cameras with a calibration target, and printed test artefacts on the scanner.
- Each prediction error goes into the ledger with its provenance; twin parameters are refitted only after the blind
  comparison is recorded.

### Coupling to the printer twin

- **One cell model**: the printer design (v12 and later) is a body in the cell; the arm's collision checks use the
  printer's real bed Z and gantry park positions.
- **End-effector geometry flows straight through the printer pipeline**: mechloop design -> PrusaSlicer -> Klipper
  offline -> printer twin's as-printed part -> grasp sim and FEA of the as-printed tool -> real print -> scan -> compare.
- The Moonraker handshake is simulated on both sides, so a cell run is one simulation.

---

## 6. End-effector loop

### Quick-change interface

- **Kinematic coupling** (three balls or dowel pins in three grooves, Maxwell type) for location, as used by the E3D /
  Jubilee tool changers ([Hackaday on Jubilee](https://hackaday.com/2019/11/14/jubilee-a-toolchanging-homage-to-3d-printer-hackers-everywhere),
  [Jubilee repo, CC BY 4.0](https://github.com/machineagency/jubilee)), plus a lock: Jubilee's spring twist-lock (remote
  elastic lock) or a magnetic preload ([magnetic Maxwell changer](https://github.com/totaldesaster/toolchanger/blob/main/README.md)).
- The arm-side and tool-side coupling plates are **metal** (laser-cut or bought); only the tool body behind the coupling is
  printed. Pogo-pin contacts for power, heater, thermistor and a tool ID; a vacuum port.
- Target: repeatability <= 0.05 mm, holding force > 3 x (payload x peak acceleration), lock and release by the arm's own
  motion at the rack (no extra actuator if possible). The Berkeley printed passive changer reached 92 of 100 connect/release
  cycles ([CASE 2018 paper](https://goldberg.berkeley.edu/pubs/CASE2018-ron-tool-changer-submitted.pdf)): a baseline to beat.

### Tools to iterate

Sheet gripper (tab clamp or magnetic edge grip), parallel gripper with printed fingers, vacuum cup, heat-set insert tool,
screwdriver, magnet placer. Detail: [04 end-effectors](arm_research/04_end_effectors.md).

### The loop

1. **Design** a tool version in mechloop (parametric), with its target (e.g. grasp success >= 98 % on the release tray).
2. **Verify**: DFM for printing, FEA of fingers with declared print settings, MuJoCo grasp over pose noise, printer twin.
3. **Print automatically**: slice with PrusaSlicer, upload and start through Moonraker; at first, the owner approves each
   job (one touch), later only when a verifier warns.
4. **Unload and inspect**: stage A takes it off the sheet, stage B scans it; the record gets the as-printed dimensions.
5. **Mount**: the arm drops the new tool into a rack slot from the release tray and picks it up by its coupling. (Bootstrap:
   the owner puts the first coupling plates on by hand.)
6. **Test**: a fixed trial, e.g. 50 grasps per object, logging success, alignment error (camera), cycle time, damage
   (scan of the object before and after).
7. **Learn**: rows in the measurement record; learnings in `mechloop/data/learnings/ledger.jsonl` (e.g. PETG-on-PLA
   friction, compliant-finger stiffness predicted vs measured, insert depth vs dwell), each with the prediction error
   before and after.
8. Next version, until the target is met. "Iterations to target" is a loop metric (section 9).

DG-01 note: printed fingers carry the gripped part's load, so a printed end-effector is in a (small) load path. This needs
the owner's waiver or a rule change (open question 1).

---

## 7. Off-the-shelf building blocks (brief survey)

Every part chosen later must meet the real-part rule (named maker, part number, seller, maker CAD or faithful re-make,
datasheet ratings) and prefer US sellers. Prices are snapshots. Detail: [02 actuators](arm_research/02_actuators.md).

| Block | Candidate (real product) | Seller / price (snapshot) | Fit |
|---|---|---|---|
| Geared closed-loop stepper | StepperOnline 17HS19-1684D-PG5-E1000 (NEMA 17, 5:1 planetary, 1000 PPR encoder) | [StepperOnline, ~$34](https://www.omc-stepperonline.com/Nema-17-Closed-loop-Geared-Stepper-L48mm-Gear-Raio-51-Encoder-1000CPR.html) | SCARA joints, wrist |
| Precision planetary stepper | StepperOnline 17HS15-1684S-HG20 (20:1) | [StepperOnline, ~$62](https://www.omc-stepperonline.com/nema-17-stepper-motor-l-39mm-gear-ratio-20-1-high-precision-planetary-gearbox-17hs15-1684s-hg20) | wrist; articulated elbow |
| Closed-loop driver on CAN | Makerbase MKS SERVO42D CAN | [Abra Electronics, ~$27 (board only)](https://abra-electronics.com/electromechanical/motors/motor-controllers/mot-servo42d-can-mks-servo42d-can-mb-closed-loop-stepper-motor-board-without-motor.html) | any stepper joint |
| Smart servo | ROBOTIS Dynamixel XM430-W350 | [ROBOTIS US, ~$310](https://robotis.us/dynamixel-xm430-w350-r) | wrist or gripper only (too weak for a 0.5 m shoulder) |
| Low-cost bus servo | Feetech STS3215 (12 V, 30 kg·cm) | [RobotShop, ~$49](https://robotshop.com/products/feetech-12v-30kgcm-magnetic-encoding-servo-sts3215) | gripper / tool actuation |
| Geared BLDC actuator | SteadyWin GIM6010-8 | [Robotics Center (San Francisco), ~$70, backorder](https://www.roboticscenter.ai/store/product/steadywin-gim6010-8-planetary-reducer-servo-motor/) | articulated shoulder / elbow |
| FOC controller | ODrive S1; mjbots moteus r4.11 | [ODrive, $149 (sold out at check)](https://shop.odriverobotics.com/products/odrive-s1); [moteus ~$59-79](https://reach.dog/shop/mjbots-robotic-systems/products/moteus-r4-11) | BLDC joints |
| Strain-wave gearbox | none found at a US hobby seller in this pass | - | to be surveyed in 02 |
| Depth camera | Luxonis OAK-D Lite | [Luxonis, $269](https://shop.luxonis.com/products/oak-d-lite-1) | cell perception; the printer's Pi cameras may cover most needs |
| Force / torque | 6-axis F/T sensors cost thousands ([UFACTORY ~$3,300](https://top3dshop.com/product/ufactory-6-axis-force-torque-sensor)); single-axis load cells in a tool, or motor current, instead | - | insert press force, screw torque |
| Vacuum | SparkFun 12 V diaphragm pump ROB-10398 (0-16 inHg) | [SparkFun, $25.50](https://www.sparkfun.com/vacuum-pump-12v.html) | vacuum cup; no compressor needed |
| Compressed air | shop compressor + solenoid valves | - | only if the owner already has air (open question) |

Encoders (absolute magnetic on the joint output), controllers (a Klipper board for the Cartesian; CAN drivers + a planner
for the others) and bearings (crossed-roller or angular-contact pairs) are surveyed in 02.

---

## 8. Prior art (brief)

Detail: [03 prior art](arm_research/03_prior_art.md).

| Project | What it is | What to borrow |
|---|---|---|
| [Annin AR4 Mk5](https://www.hackster.io/news/chris-annin-calls-the-open-source-ar4-robot-arm-done-with-the-new-final-mark-5-revision-62b51e0ae555) | open 6-DOF stepper arm; combo kit ~$1,189 + ~$699 motor package ([OSE wiki](https://wiki.opensourceecology.org/wiki/AR4_Robot_Arm), 2026 review figures) | cost baseline for a 6-DOF; reviewers note backlash ([Hackster](https://www.hackster.io/news/is-the-annin-ar4-the-workhorse-robot-arm-for-you-6a26487fb517)) |
| [PAROL6](https://github.com/PCrnjak/PAROL6-Desktop-robot-arm) | printed 6-DOF desktop arm, 408 mm reach, 0.5-1 kg, 0.1 mm repeatability claimed | stepper + gearbox joint layouts at our size |
| [Arctos](https://hackaday.com/2023/05/08/arctos-robotics-build-a-robot-arm-out-of-3d-printer-spares) | 6-DOF from 3D-printer parts, cycloidal + belt joints, ~$400 parts ([Arduino blog](https://blog.arduino.cc/?p=34636)) | printer-part reuse; paid plans (not open hardware) |
| [SO-100/101 (LeRobot)](https://github.com/TheRobotStudio/SO-ARM100) | ~$100-220 arm with STS3215 servos, Apache 2.0 | software stack for learned manipulation; too weak for our payload |
| [Faze4](https://github.com/PCrnjak/Faze4-Robotic-arm) | MIT-licensed 6-DOF with cycloidal gearboxes | cycloidal drive geometry |
| [PyBot SCARA](https://hackaday.com/2020/10/19/pybot-is-a-3d-printed-scara-arm-for-the-masses), [PR3 SCARA](https://hackaday.io/project/204557-pr3-scara) | printed SCARAs on NEMA 17 + belts (PyBot claims 0.2 mm repeatability) | SCARA belt reductions, FluidNC control |
| [Jubilee](https://github.com/machineagency/jubilee) | open toolchanging motion platform | kinematic coupling + twist-lock |
| [3DQue Quinly / VAAPR](https://all3dp.com/1/3dque-quinly-review-automated-3d-printing/) | gravity part removal by a special bed + queue software | queueing and a bed surface that releases easily |
| [SwapMod](https://hackaday.com/2024/09/30/3d-printer-swaps-build-plates-to-automate-print-jobs) | swaps whole build plates from a stack | **plate swapping beats scraping**: supports our sheet-lift approach |
| [Bambu auto-ejection kit](https://tomshardware.com/3d-printing/new-auto-ejection-tool-for-bambu-lab-print-farms-automatically-ejects-finished-3d-prints-from-the-machine-usd129-kit-includes-auto-door-opener-and-special-bed-surface-for-frictionless-part-ejection) | $129 kit incl. an auto door opener | a cheap door actuator instead of the arm opening the door |
| [OSE part remover](https://wiki.opensourceecology.org/wiki/Open_Source_Automated_Printed_Part_Remover), [WPI bed-flexing MQP](https://digitalcommons.wpi.edu/mqp-all/289), [KUKA print tending (Springer)](https://link.springer.com/chapter/10.1007/978-981-99-3330-3_27), [mobile printer-tending robot](https://hackaday.io/project/181649-a-robot-for-automating-3d-printers) | removal methods: bump, bed lift, flex, arm | flexing the sheet is the reliable release |
| [Berkeley tool changer](https://github.com/BerkeleyAutomation/RobotToolChanger) | printed passive changer, 92/100 cycles | baseline and failure modes |

---

## 9. Loop metrics for the arm

| Metric | Definition | How measured |
|---|---|---|
| **Human touches per printed part** | manual interventions / parts that left the printer | every manual action logged with one button or form entry (the same "touch" count `record.loop_metrics` uses); arm and Moonraker logs give the part count |
| **Unattended hours** | longest stretch, and hours per week, of printing + handling with zero touches | timestamps from Moonraker job history and the touch log |
| **Grasp / assembly success rate** | successes / attempts per task and tool version | arm controller result per attempt, confirmed by camera or scan |
| **End-effector iterations to target** | versions printed until the target is met | ledger entries per tool |
| **Cycle time** | per task (unload, inspect, each assembly op) and per full loop (design change -> measured) | arm log + Moonraker timestamps; design-change time from git |
| **Fidelity** | prediction vs measurement for repeatability, sag, cycle time, grasp success | pre-registered predictions vs measured, in the ledger |

---

## 10. Budget, risks, open questions

### Budget ranges for Arm Build 1 (estimates, arm + cell, excluding the printer)

| Architecture | Arm hardware | Cell (stations, tools, couplings, camera, vacuum, e-stop, feeders) | Total |
|---|---|---|---|
| Cartesian gantry + ram | $600-1,200 | $500-1,000 | **$1,100-2,200** |
| SCARA + tall Z | $700-1,500 | $500-1,000 | **$1,200-2,500** |
| 4/5-DOF articulated (steppers) | $900-2,000 | $500-1,000 | **$1,400-3,000** |
| 6-DOF articulated (steppers + planetary/cycloidal) | $1,200-3,000 | $500-1,000 | **$1,700-4,000** |
| 6-DOF articulated (geared BLDC + FOC) | $1,500-3,500 | $500-1,000 | **$2,000-4,500** |

Basis: the component snapshots in section 7 and the AR4 kit figures; fabricated plates at SendCutSend-class prices;
print-service end-effectors until the printer runs. A 6-axis F/T sensor (~$3,000+) is excluded.

### Risks

| Risk | Effect | Mitigation |
|---|---|---|
| The sheet does not re-seat repeatably | stage A fails or the first layer fails | locating pins / stops on the bed (printer change); Eddy + camera check before every print |
| DG-01 (no printed load paths) vs printed end-effectors | the loop's subject is blocked | owner waiver scoped to end-effectors behind a metal coupling |
| Serial-arm compliance and backlash | 0.1 mm not reached | carry SCARA and Cartesian; measure one real joint early (spike step 6) |
| SCARA / articulated not native in Klipper | no free firmware-in-the-loop | separate planner with its own offline mode; or a Klipper kinematics module (a firmware project) |
| The printer is not built yet; the owner has no printer | the end-effector loop cannot start | concept design runs now; arm hardware waits for the printer to run; first tools from the print service |
| Reach to the rear spool | filament tasks impossible | defer; later printer change |
| Unattended operation with people nearby | injury | low-power limits or a guarded cell, hardware e-stop, owner decision |
| Scope creep (6 tasks x 3 architectures) | slow | stage gates; stage A first |

### Open questions for the owner

1. **DG-01**: allow printed end-effector bodies (behind a metal coupling) in a small load path, with a waiver? Arm links stay
   metal.
2. **Bench**: what bench, how big, against a wall? Can the arm stand in front of the printer?
3. **Bed locating**: add pins or stops for the flex sheet (a v12.x / v13 printer change)?
4. **Door**: motorise the V13 door (cheap, Klipper-controlled), or have the arm open it?
5. **Filament and spool tasks**: drop from Arm Build 1 (recommended)?
6. **Budget ceiling** for Arm Build 1?
7. **Air**: is compressed air available, or vacuum pump only?
8. **Compute**: separate controller for the arm (recommended), or share the printer's Pi?
9. **First assembly target**: which real sub-assembly should stage C build (proposal: the arm's own gripper, or a camera
   mount with inserts)?
10. **People in the room** during unattended runs: collaborative limits, or a guarded cell?
11. Confirm the stage targets in section 1.

---

## 11. Next steps: concept design spike, in parallel with the printer build

The printer build comes first and is not slowed: the spike is design work only (owner's caution: design is cheap, build
late). Arm hardware is ordered only once the printer runs.

| Step | Work | Output | Weeks (estimate) |
|---|---|---|---|
| 1 | Cell model: printer v12 as a light proxy (envelope, opening, bed at its Z range, gantry park) after the v12 build finishes; stations placed | `designs/arm_cell.py` (proxy only, no heavy imports) | 0.5 |
| 2 | Task pose list and trajectories for stages A-D, with payloads and forces | data file + requirements in the design | 0.5 |
| 3 | Three skeleton arms (SCARA + Z, Cartesian + ram, 6-DOF) as mechloop joint chains with real candidate drives | three exploratory designs (`design.exploratory = True`) | 1.5 |
| 4 | New and extended verifiers, minimum set: reachability, task-trajectory sweep, MuJoCo with backlash and torque-speed, link FEA at poses | verifier code + tests | 2 |
| 5 | Score the three; pick one (or two) for detailed design; owner review | a comparison page and a decision record | 0.5 |
| 6 | Cheap physical tests: one real joint (a geared closed-loop stepper on a test link) to measure backlash and stiffness; a coupling coupon set and finger coupons from the print service; magnet-base peel force of the sheet | measured numbers in the ledger before committing | parallel, ~2 |
| 7 | Detailed design of the chosen arm + end-effector interface; the same buildability gate as the printer (zero placeholders) | Arm Build 1 package | 3-4 |
| 8 | Order and build after the printer's first closed loops; stage A first | - | - |

Steps 1-6 fit in the printer's ordering and lead-time window (print service 4-11 days; long-lead parts longer).
