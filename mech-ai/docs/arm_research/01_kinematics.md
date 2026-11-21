# Arm research 01: kinematic architectures

Scope: which kinematic layout should mechloop's self-designed arm use? It must (a) serve the printer (remove the
220 x 220 mm PEI spring-steel sheet through the printer's front, clear purge, later open a door), (b) present parts to a
camera / flatbed-scanner station, (c) assemble printed parts with heat-set inserts, M2-M5 screws, small bearings and
magnets, and (d) swap printed end-effectors. This note compares SCARA, 4/5/6-DOF articulated, an overhead Cartesian gantry,
a delta, and an arm on a linear rail. It recommends three to carry into concept design and names the simulations and tests
that would pick between them. **No final choice is made.**

Numbers marked **(est.)** are my own back-of-envelope estimates. Printer geometry comes from `docs/PRINTER_V12.md`. Numbers
for commercial and open-source arms come from the sources cited inline (vendor figures, not independent measurements).

---

## 1. What the printer gives us (from PRINTER_V12.md)

| Item | Value | Consequence for the arm |
|---|---|---|
| Machine envelope | 388 W x 419.5 D x 475.9 H mm (2020 frame); 510 mm deep with the rear spool | The front face is the only free side. The spool takes the rear, and the side faces are kept for the enclosure. |
| Front opening | about 348 mm clear between the 2020 posts (est.: 388 - 2 x 20) | A sheet 220 mm wide plus a wide-jaw tool fits, with about 60 mm each side. |
| Bed | 240 x 240 MIC-6 plate; 220 x 220 x 0.4 mm PEI spring-steel sheet on a magnetic base; print area 186.6 x 208.1 | The sheet's front edge is reachable from the front. Its centre sits about 210 mm inside the front face (est.: bed centred in the 420 mm depth). |
| Z | Bed moves in Z only, 180 mm of travel; the gantry is at the top | **The printer can bring the bed to any transfer height.** The arm does not need a large Z range to meet the bed; Klipper puts the bed at the arm's height. |
| Front Z hardware | none at the front (owner) | The sheet can slide out horizontally towards the front. |

**Sheet-handling physics (est.).** A 0.4 mm steel sheet held by one edge sags under its own weight:
δ = wL⁴/8EI ≈ 0.0067 N/mm x 220⁴ / (8 x 200 GPa x 220 x 0.4³/12) ≈ **8 mm**, and more with a print on it. Lifting the sheet
free and carrying it cantilevered is therefore messy. **Sliding it** is cleaner: peel the front edge up 3-10 mm (the magnet
gives way easily in peel), pull it forward about 240 mm along the bed onto a receiving shelf docked at bed height, then carry
or flex it on that shelf. The core printer move is therefore a **1-D horizontal pull at bed height, 240-300 mm long**. The
arm also needs a short vertical peel and, ideally, a wide-jaw gripper tool. That shapes every comparison below.

## 2. Proposed cell layout (top view, all est.)

Origin at the centre of the printer's front face, on the table. +y points into the printer, +x to the right.

```
                        +y (into printer)
            +-----------------------------------+  y = +420  (rear; spool behind to +510)
            |          PRINTER 388 x 420         |
            |      sheet 220x220, centre y~+210  |
            |      sheet front edge   y~+100     |
            +-----------------------------------+  y = 0  (front face, opening ~348 wide)
              [sheet receiving shelf / flex station, 240 x 260, at bed transfer height]
                                                      y = 0 .. -260
   [INSPECTION]                                        [PARTS / FEEDERS]
   flatbed A4 (platen 216x297)      (ARM BASE)         trays 2 x 200x150,
   + camera mast, centre (-380,-300)  (0,-300)         insert/screw presenters
                                                       centre (+360,-300)
                 [TOOL RACK: 6 slots x 70 mm, y = -480, x = -210..+210]
                 [ASSEMBLY FIXTURE / insert press station, near (+200,-470)]
   Cell footprint about 1000 W x 1000 D mm (printer included), table height 0.
```

Reach from an arm base at (0, -300) (est.):

| Target | Horizontal distance | Height (above table) |
|---|---|---|
| Sheet front edge (grab and pull start) | 400 mm | bed transfer height, chosen 200-380 mm (est.; set by the bed's Z) |
| Sheet fully out, on the shelf | 150-300 mm | same |
| Sheet centre in the printer (only if parts are picked in place) | 510 mm | same, plus clearance under the parked gantry |
| Sheet rear edge (worst case, e.g. clearing purge at the back) | 620 mm | same |
| Scanner platen far corner | about 500 mm | 60-80 mm (scanner body) |
| Parts trays, far corner | about 480 mm | 0-60 mm |
| Tool rack ends | about 290 mm | 50-150 mm |

**Requirement derived (est.).**
- If the arm only pulls the sheet out and does all work outside the printer: horizontal reach **about 500 mm** and a
  vertical working range of **about 0-400 mm**.
- If it must reach the back of the bed (purge at the rear edge, picking parts off the bed in place): **about 620 mm**, and
  the forearm must enter the printer horizontally through a window roughly 150-200 mm tall (bed to parked gantry).

Recommendation for every architecture: put the purge or wipe at the **front** edge of the bed and move all part handling out
to the shelf. This keeps the reach near 500 mm.

## 3. Task requirements: repeatability, force, approach direction

| Task | Tool-point repeatability needed (est.) | Force / moment (est.) | Approach |
|---|---|---|---|
| Grab sheet front edge (tab or lip, funnelled jaw) | ±1-2 mm | 5-15 N peel, 5-20 N pull; up to 0.7 N·m about the jaw if the sheet + print is lifted | horizontal into the front, plus a small vertical peel |
| Re-seat sheet on bed (rear pins + front edge) | ±0.5-1 mm with chamfers and compliance | 5-10 N push | horizontal |
| Clear purge blob (front of bed or purge bin) | ±2 mm | 2-10 N sweep | horizontal / top-down |
| Open printer door (later) | ±3-5 mm (compliant hook) | 5-20 N along an arc | horizontal, arc path |
| Pick part from tray or fixture | ±0.3-0.5 mm | < 10 N | top-down |
| Present to camera / place on flatbed | ±1 mm (the camera measures the actual pose) | small | top-down; flipping needed to see the other side |
| Heat-set insert (M2-M5) | **±0.1-0.2 mm**, tilt < 1-2° | 5-30 N axial while hot | top-down (if the part is designed for it) |
| Screw start M2-M3 (compliant spindle, chamfered hole) | ±0.15-0.3 mm | 5-20 N axial, 0.1-1 N·m reaction torque | top-down |
| Press small bearing / magnet | ±0.1-0.2 mm + chamfer | 20-100 N press (bearing interference fit) | top-down |
| End-effector swap (kinematic coupling: balls / vees + tapered lead-in) | ±0.5-1 mm capture; the coupling itself repeats to ~10 µm | 10-40 N lock / unlock | top-down or horizontal slide-in |

Notes.
1. **Repeatability, not absolute accuracy, matters.** Points are taught, or located with a camera fiducial or a touch-off,
   so only scatter about a taught point counts. Local fiducials can repair accuracy; nothing repairs repeatability.
2. **Precision and force come together only in assembly.** Insert, screw and press work needs about ±0.1-0.2 mm while
   pushing 5-100 N. Every other task is ±0.5-2 mm at small force. This is the main lever on architecture. If insert pressing
   and bearing pressing move to a **fixed station** (a small rigid Z press over a fixture, and the printer itself is
   already such a machine), the arm only has to place parts into chamfered fixtures, at ±0.3-0.5 mm. Screw *starting* can
   then also be done by a compliant tool on the arm.
3. **Design for top-down assembly.** mechloop designs its own parts, so it can impose the classic DFA rule that every
   insertion goes along one axis (top-down). With that rule, every task except printer service is top-down. Printer service
   is horizontal, at one height chosen by the printer. **No task needs a general tilted approach**, except flipping a part
   for a second inspection view or a second assembly side. A passive flip fixture, or a 1-axis "flip tool" carried as a
   swappable end-effector, can do that.

## 4. Stiffness, torque and joint-error drivers (est., hand calculations, no FEA)

**4.1 Joint angular error times reach dominates rotary arms.** At 450 mm radius:

| Joint angular repeatability | Tool error at 450 mm |
|---|---|
| 0.1° (typical printed cycloidal or planetary backlash, or a 12-bit AS5600 encoder at 0.088°) | 0.79 mm |
| 0.022° (14-bit encoder, e.g. AS5047) | 0.17 mm |
| 0.013° (needed for ±0.1 mm) | 0.10 mm |

A rotary arm built from printed parts that must hold ±0.1-0.2 mm at 400-500 mm therefore needs **output-side 14-bit or
better absolute encoders** and zero-backlash transmissions (preloaded belts, capstans, or good cycloidal or strain-wave
drives) on the two proximal joints. Anchor points:
- Dobot MG400 (4-axis, 440 mm): ±0.05 mm ([Dobot MG400](https://www.dobot-robots.com/products/desktop-four-axis/mg400.html)).
- Dobot Magician Lite (340 mm): ±0.2 mm ([Dobot](https://dobot-robots.com/products/education/magician-lite.html)).
- Annin AR4 (6-axis, about 600-630 mm): about ±0.2 mm ([RoboDK AR4](https://robodk.com/robot/Annin-Robotics/AR4),
  [OSE wiki](https://wiki.opensourceecology.org/wiki/AR4_Robot_Arm)).
- UFACTORY Lite 6 (440 mm) and myCobot 280: ±0.5 mm
  ([RobotShop Lite 6](https://www.robotshop.com/products/ufactory-6-axis-robot-arm-lite-6),
  [myCobot specs](https://qviro.com/product/elephant-robotics/mycobot-280-m5/specifications)).
- Printed belt SCARA PyBot: 0.2-0.4 mm claimed
  ([Hackster](https://www.hackster.io/news/pybot-is-an-accurate-open-source-scara-robotic-arm-with-3dof-and-can-be-3d-printed-with-ease-fe7191e06fc9)).
- Printed capstan + belt arm "Forte" (467 mm, 0.63 kg): sub-mm ([arXiv 2507.15693](https://arxiv.org/abs/2507.15693)).

Takeaway: ±0.2 mm is the realistic ceiling of hobby-class rotary arms. ±0.05 mm takes MG400-class engineering. A Cartesian
axis on belts or screws routinely repeats to ±0.01-0.02 mm, as our printer does.

**4.2 Gravity torque: articulated vs SCARA.**
- Articulated shoulder, horizontal arm at 450 mm, 1 kg payload, with wrist motors carried on the arm: about
  **7.3 N·m static** (payload 4.4 + links 2.9). Elbow: about 3.4 N·m. With a 1.5x dynamic factor and a NEMA17 giving about
  0.3 N·m usable at speed, the shoulder needs about a **35-40:1** zero-backlash reducer (about 14:1 with NEMA23). Gravity
  also loads the reducer all the time, so printed-gear creep and wear matter.
- SCARA: the bearings take gravity, and only the Z axis lifts. A T8x8 leadscrew lifting 3 kg takes about 0.1 N·m. θ1 must
  only accelerate inertia: about 0.23 kg·m² with 1 kg at 400 mm, 180° in 1 s, gives about 2.9 N·m, so a **10-12:1 belt
  reduction** is enough. The SCARA's motors and transmissions are therefore smaller and simpler.

**4.3 Link bending under assembly force (20 N vertical at 400 mm).**

| Link section | EI (N·mm²) | Tip deflection over 400 mm |
|---|---|---|
| Printed PETG box 30 x 60 x 3 mm wall, E ≈ 2 GPa | 4.5e8 | **≈ 0.95 mm** |
| 2020 aluminium extrusion (I ≈ 7,000 mm⁴) | 4.9e8 | ≈ 0.9 mm (no better than the printed box) |
| 2040 extrusion on edge (I ≈ 45,000 mm⁴) | 3.2e9 | ≈ 0.13 mm |
| 40 x 40 x 2 aluminium tube | 5.1e9 | ≈ 0.08 mm |

Bearing tilt, joint compliance and creep come on top. Conclusions:
- Purely printed links cannot press inserts at full reach to ±0.1-0.2 mm. Either use **aluminium cores with printed
  joints and housings**, or move pressing to a fixed station.
- PLA near the heated bed (60-110 °C) creeps. Use PETG, ASA or PC (or aluminium) for anything that enters the printer.
- For an articulated printed arm the same 20 N push also adds about 8 N·m to the shoulder and wrist joints, so pressing
  directly with such an arm is the worst case.

## 5. Architecture-by-architecture comparison

### 5.1 SCARA (4-DOF: θ1, θ2, Z, roll), on the table in front of the printer
- **Workspace:** an annulus. Links of 250 + 250 mm give 500 mm reach (about 130 mm inner dead zone). Z stroke about
  400 mm on a column. The horizontal links pass straight through the printer's front window at whatever height the column
  sets. That is exactly the motion the sheet extraction needs.
- **Approach:** horizontal in-plane pull (printer service) and top-down (everything else). No tilt. Flipping goes to a
  fixture or a flip tool.
- **Precision:** belts with output encoders, about ±0.05-0.1 mm (est.; Epson T3: ±0.02 mm at 400 mm, 1-3 kg,
  [Epson T3-B](https://epson.com/For-Work/Robots/SCARA/Epson-T3-B-All-in-One-SCARA-Robot/p/RT3B-401SS)). It is stiff in
  the horizontal plane and weaker vertically (section 4.3), so the links need deep or aluminium-cored sections.
- **Actuators:** 4 plus the gripper. NEMA17 closed-loop steppers, belt reductions, no strain-wave gears. Parts about
  $350-700 (est.).
- **Printability:** good. Flat links, belt pulleys, simple joints. The Z column uses 2020/2040 extrusion and a rail, the
  same supply chain as the printer.
- **Control and simulation:** closed-form 2-link IK. RepRapFirmware supports SCARA natively
  ([Duet docs](https://docs.duet3d.com/User_manual/Machine_configuration/Configuration_SCARA)). Klipper does not (an
  unfinished PR exists; users fake it as polar,
  [Klipper forum](https://klipper.discourse.group/t/scara-kinematic/11663)). A small custom kinematics module or a
  host-side IK feeding Klipper `manual_stepper` is needed. The twin is easy: 4 joints, open chain.
- **Weak points:**
  - Reaching the back of the bed needs about 620 mm and a column in front of the printer.
  - The inner dead zone means stations must not sit near the base.
  - Door opening needs an arc in the plane. That is feasible (θ1/θ2 interpolation) if the door hinge is vertical.

### 5.2 Articulated 4/5/6-DOF
- **Workspace:** a sphere around the shoulder. 450-600 mm reach covers everything, including tilted and horizontal
  approaches into the printer.
  - 4-DOF palletising style (parallelogram, tool kept vertical, MG400 / Magician): behaves like a SCARA with a vertical
    workspace. MG400: 440 mm, 0.5-0.75 kg, ±0.05 mm.
  - 5-DOF adds tool pitch.
  - 6-DOF: any pose.
- **Approach:** any. That is the only architecture that opens an arbitrary door, flips parts in hand and reaches round
  obstacles.
- **Precision:** the proximal joints carry gravity (section 4.2). They need 30-40:1 zero-backlash reducers and output
  encoders to get near ±0.2 mm. Anchors:
  - AR4: about ±0.2 mm, 600-630 mm, 1-1.9 kg.
  - Arctos (printed, about $400): about 0.5 kg payload estimated by its team, no published repeatability
    ([Hackaday](https://hackaday.com/2023/05/08/arctos-robotics-build-a-robot-arm-out-of-3d-printer-spares)).
- **Actuators:** 5-6 plus the gripper, with reducers (printed cycloidal about $20-40 each in parts, strain-wave $100-300
  each). Parts about $600-2,000 (est.). The wrist motors ride on the arm, which raises proximal torque.
- **Printability:** possible (Arctos, Faze4, AR4 derivatives), but the reducers are the hard, wear-prone parts. Printed
  cycloidal backlash of 0.1° already gives about 0.8 mm at 450 mm.
- **Control and simulation:** hardest of the five. Numerical or analytic 6R IK, singularities, collision checking with the
  printer frame, payload-dependent sag. Needs ROS 2 / MoveIt or equivalent, not Klipper. The twin needs good joint
  compliance models to be predictive.
- **Weak points:** cost, complexity and gravity-loaded printed gears. The extra DOF buy little for a top-down DFA cell
  (section 3.3).

### 5.3 Cartesian gantry over the cell
- **Workspace:** a box. A gantry *over* the cell cannot reach into the printer, because the printer's own top gantry and
  frame are in the way.
- **Variant that works: the front-loading Cartesian.**
  - X runs along the cell front, about 900-1000 mm.
  - Z mast stroke is about 400 mm.
  - Y is a cantilevered "fork" or ram about 300 mm into the printer, plus roll and optional tilt at the tool.
  - It works like a CNC tool-loader or stacker crane. The Y ram is what enters the front window.
- **Approach:** horizontal (Y ram) and top-down (Z). Tilt only if a wrist axis is added.
- **Precision:** best of all. Rails and belts or screws give ±0.02-0.05 mm. Insert and press forces go into rails, not
  joints. The cantilevered Y ram is the stiffness driver: 300 mm, 20 N, 40 x 40 aluminium tube gives about 0.04 mm (est.).
- **Actuators:** 3 linear + 1-2 wrist. NEMA17s like the printer's. The linear hardware (rails, extrusion) makes it pricier
  per DOF: about $500-1,000 (est., with MGN rails), and it takes up the most space.
- **Printability:** the brackets, carriages and tools print. The rails and extrusion are bought, just as for the printer.
- **Control and simulation:** **Klipper-native.** Cartesian kinematics, plus `manual_stepper` for the wrist. The printer's
  firmware, input shaping, endstops and twin tooling all carry over. The simulation is trivial: decoupled axes, linear
  stiffness.
- **Weak points:**
  - Fixed, large footprint, and it partly blocks the human's access to the printer front.
  - It cannot open a hinged door without an extra axis.
  - Stations must lie inside its box.
  - It looks like "another printer", which also makes it the lowest-risk path to a working cell.

### 5.4 Delta
- **Workspace:** a short cylinder below a base mounted overhead. It cannot reach horizontally through the printer's front
  window, and it cannot reach the bed from above because of the printer's top gantry.
- **Precision and speed:** stiff and fast top-down. igus drylin delta: ±0.5 mm, 360/660 mm workspace, about 5 kg, from
  about $5,400 ([igus FAQ](https://blog.igus.ca/wp-content/uploads/2025/06/delta-robot-faqs.pdf)). Klipper supports
  `delta` and `rotary_delta` natively ([Klipper config reference](https://www.klipper3d.org/Config_Reference.html)).
- **Verdict:** **rejected as the main arm.** It fails the printer-service task. It may have a later role as a dedicated
  overhead assembly sub-station.

### 5.5 Arm on a linear rail (7th axis)
- A modifier, not a separate kinematic family: a SCARA or articulated arm on a 600-1,500 mm rail parallel to the cell front.
- **Gains:**
  - Short links (300-350 mm reach is enough per station), which improves the angular-error x reach product in section 4.1
    by about 30-40 %.
  - Unlimited stations along the rail.
  - Future multi-printer farm.
- **Costs:** +1 actuator, rail cost, and a redundant DOF to resolve (simple: index the rail to discrete stations).
- **Verdict:** keep as an **upgrade path** for 5.1 or 5.2. It is not needed for one printer.

## 6. Summary scoring (est.; 5 = best)

| Criterion | SCARA 4-DOF | Articulated 5/6-DOF | Front-loading Cartesian | Delta | Arm on rail |
|---|---|---|---|---|---|
| Horizontal entry into printer at bed height | 5 | 4 | 5 | 1 | 5 |
| Top-down assembly | 5 | 4 | 5 | 5 | 5 |
| Tilted / arbitrary approach, door, in-hand flip | 2 | 5 | 2 (3 with tilt) | 1 | as base arm |
| Repeatability achievable with printed parts | 4 | 2-3 | 5 | 4 | +1 over base arm |
| Stiffness under 20-100 N press | 3 | 1-2 | 5 | 4 | as base arm |
| Actuator count / cost | 4 (4 axes, ~$350-700) | 2 (6 axes + reducers, ~$600-2,000) | 3 (4-5 axes + rails, ~$500-1,000) | 3 | 2-3 |
| Printability of structure | 4 | 3 | 3 (rails bought) | 3 | 3 |
| Control effort (with Klipper ecosystem) | 3 | 1 | 5 | 5 | 2 |
| Simulation / twin fidelity effort | 4 | 2 | 5 | 4 | 3 |
| Footprint / human access | 4 | 4 | 2 | 2 | 3 |

## 7. Recommendation: carry three into concept design

1. **A. SCARA 4-DOF (θ1, θ2, Z, roll), about 250 + 250 mm links, 400 mm Z column, base about 300 mm in front of the
   printer.**
   - It is the natural fit to the task geometry: a horizontal pull at a bed height the printer chooses, plus top-down DFA
     assembly.
   - Its gravity-free horizontal joints allow belt reductions and NEMA17s.
   - Design requirements: aluminium-cored links, 14-bit output encoders on θ1/θ2, and a flip tool as a swappable
     end-effector.
2. **B. Front-loading Cartesian (X about 1,000, Z about 400, Y ram about 300 mm into the printer, plus roll).**
   - The precision and stiffness baseline: it can press inserts itself.
   - It is Klipper-native and has the cheapest digital twin, so the mechloop loop can start iterating soonest.
   - The cost is footprint and generality.
3. **C. Compact 5-DOF articulated (4-DOF parallelogram class + pitch, about 450 mm reach), optionally on a short rail
   later.**
   - It is the generality hedge: door opening, part flipping, approaches the DFA rule cannot remove.
   - Its tests decide whether a printed reducer can reach ±0.2 mm or whether precision work must go to a station.

Common decisions for all three:
- Fixed press station for inserts and bearings, so the arm only needs ±0.3-0.5 mm there.
- Purge at the front of the bed.
- A sheet receiving shelf at bed height, wide-jaw sheet tool.
- Kinematic-coupling tool changer.
- Payload rating 1 kg (sheet + print about 0.2-0.7 kg plus a tool of 0.1-0.3 kg).

## 8. Decisive simulations and tests (cheap first)

| # | Simulation / test | What it decides | Pass criterion (proposal) |
|---|---|---|---|
| 1 | **Reach and clearance sweep (kinematic only, no FEA).** Accurate printer twin (front opening, parked gantry, bed at transfer Z) + each candidate. Sweep the peel-and-pull sheet path, the tool rack and all station poses; check collisions and joint limits. | Link lengths, Z stroke, base position; whether A/C can enter the printer at all with real clearances; whether rear-of-bed access is needed. | All poses of section 2 reachable with ≥ 15 mm clearance; sheet pull ≥ 240 mm in a straight line. |
| 2 | **Tool-point error budget (Monte Carlo, analytic).** Encoder resolution, backlash, belt stretch, link bending at 0.2/1 kg and 20 N, per pose. | Whether A and C meet ±0.2 mm at assembly poses, or force a station; which encoder or reducer is needed. | 3σ ≤ 0.2 mm at insert/screw poses; ≤ 1 mm at sheet poses. |
| 3 | **Single-joint bench prototype.** Printed belt reduction (for A) and printed cycloidal (for C), with a 14-bit output encoder, 400 mm arm, dial indicator, 100 bidirectional approaches, 0.2 and 1 kg. | Real angular repeatability of our printed transmissions. This one test decides rotary vs Cartesian for precision work. | ≤ 0.02° (≈ ±0.15 mm at 450 mm). |
| 4 | **Insertion tolerance tests, using the printer itself as a precise Cartesian robot.** Offset an insert tool or compliant screwdriver by 0, 0.1, 0.2, 0.3, 0.5 mm and 0-3° tilt over printed test holes; also magnet and bearing seats. | The real tolerance windows behind section 3 (the ±0.1-0.2 mm figure is an estimate). Tells how much compliance or chamfer buys back. | Success rate vs offset curve; tolerance = largest offset with ≥ 98 % success. |
| 5 | **Sheet removal force and path test (hand jig + force gauge, then printer-mounted).** Peel force, pull force, sag with prints, reseat on pins. | Gripper and tool spec, payload and moment rating, whether sliding onto the shelf works. | Measured forces under the section 3 assumptions; reseat success ≥ 98 %. |
| 6 | **Stiffness check of the chosen link sections** (beam model now; FEA later when allowed). | Printed vs aluminium-cored links for A/C; Y-ram section for B. | ≤ 0.1 mm tool deflection under 20 N at the press pose (or move that task to the station). |
| 7 | **Control bring-up spike (1-2 days each).** A: host IK feeding Klipper `manual_stepper` (or RRF SCARA). B: stock Klipper Cartesian. C: ROS 2 / MoveIt with a URDF. Each with a MuJoCo or PyBullet twin replaying a sheet-pull and an insert-placement trajectory. | Real integration cost; how well the twin predicts the hardware (sim-to-real gap). | Twin-predicted vs measured tool pose within 0.5 mm on replay. |

Tests 1, 2 and 4 are cheap and can start now. Test 3 is the most decisive physical test. If printed rotary joints miss
0.02°, precision work goes to fixed stations, or B leads.

---

### Sources
- [Dobot MG400 product page](https://www.dobot-robots.com/products/desktop-four-axis/mg400.html); [MG400 spec sheet](https://cdn.shopify.com/s/files/1/0043/7154/6227/files/Dobot_MG400_SpecsSheet_C.pdf)
- [Dobot Magician Lite](https://dobot-robots.com/products/education/magician-lite.html)
- [Epson T3-B All-in-One SCARA](https://epson.com/For-Work/Robots/SCARA/Epson-T3-B-All-in-One-SCARA-Robot/p/RT3B-401SS); [Epson Synthis T3](https://epson.com/For-Work/Robots/SCARA/Epson-Synthis-T3-All-in-One-SCARA-Robots/p/RT3-401SS)
- [RoboDK: Annin AR4](https://robodk.com/robot/Annin-Robotics/AR4); [OSE wiki: AR4](https://wiki.opensourceecology.org/wiki/AR4_Robot_Arm)
- [RobotShop: UFACTORY Lite 6](https://www.robotshop.com/products/ufactory-6-axis-robot-arm-lite-6); [myCobot 280 specs (Qviro)](https://qviro.com/product/elephant-robotics/mycobot-280-m5/specifications)
- [SO-101 specs (roboticscenter.ai)](https://www.roboticscenter.ai/en/hardware/so-101/specs); [LeRobot SO-101 docs](https://huggingface.co/docs/lerobot/so101)
- [PyBot printed SCARA (Hackster)](https://www.hackster.io/news/pybot-is-an-accurate-open-source-scara-robotic-arm-with-3dof-and-can-be-3d-printed-with-ease-fe7191e06fc9); [Forte, arXiv 2507.15693](https://arxiv.org/abs/2507.15693); [KTH printed SCARA thesis](https://kth.se/polopoly_fs/1.1078072.1622113153!/gr23rapport2021-02.pdf)
- [Arctos (Hackaday)](https://hackaday.com/2023/05/08/arctos-robotics-build-a-robot-arm-out-of-3d-printer-spares); [Faze4](https://github.com/PCrnjak/Faze4-Robotic-arm)
- [igus delta robot FAQ](https://blog.igus.ca/wp-content/uploads/2025/06/delta-robot-faqs.pdf)
- [Klipper config reference](https://www.klipper3d.org/Config_Reference.html); [Klipper forum: SCARA kinematic](https://klipper.discourse.group/t/scara-kinematic/11663); [Duet RRF SCARA configuration](https://docs.duet3d.com/User_manual/Machine_configuration/Configuration_SCARA)
- [CNC Kitchen heat-set insert tips](https://www.cnckitchen.com/blog/tipps-amp-tricks-fr-gewindeeinstze-im-3d-druck-3awey)
- Plate-swap prior art (sheet handling through the front): [Swapmod / SimplyPrint](https://simplyprint.io/integrations/swapmod); [Chitu PlateCycler (Hackster)](https://www.hackster.io/news/the-popular-chitu-platecycler-is-coming-to-the-bambu-a1-0301a3b8e1e3)
