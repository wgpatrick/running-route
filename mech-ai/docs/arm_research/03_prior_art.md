# Arm research 03: prior art

Scope: what already exists for (1) low-cost and open-source 6-axis arms, (2) automated 3D-printer tending and print-farm
harvesting, and (3) robotic assembly of printed parts (inserts, screws, peg-in-hole, tool changing). For each item the
question is: what worked, what failed, what was measured (versus only claimed), and what mechloop should borrow or avoid.

Context from this repo that shapes the reading: the current printer design uses a **220 x 220 mm textured PEI sheet on
0.4 mm spring steel on a magnetic base** (see `docs/PRINTER_V11.md`), so "pull the flex sheet, flex it, put it back" is
directly applicable.

Evidence labels used below:
- **measured (independent)**: a third party or a paper with a described method measured it.
- **measured (self)**: the designer measured it and described the method.
- **claim**: a spec-sheet or README number with no published method.
- **unverified**: appears only in secondary blogs or aggregators.

Research method note: sources were found by web search only (no full-text fetch was available), so figures come from
search snippets of the cited pages. Where snippets conflicted, both values are given.

---

## 1. Open-source and low-cost arms

### 1.1 Summary table

| Arm | Architecture / actuators | Cost (as stated) | Payload | Repeatability | Evidence | Software | Licence |
|---|---|---|---|---|---|---|---|
| **Annin AR4 (MK3 to MK5)** | 6-DoF, aluminium + printed covers, NEMA17/23 steppers with planetary and belt reductions, Teensy 4.1 | ~USD 1,189 combo kit; OSE wiki estimates ~USD 1,791 complete without end effector ([OSE wiki](https://wiki.opensourceecology.org/wiki/AR4_Robot_Arm)) | 1.0 kg ([RoboDK](https://robodk.com/robot/Annin-Robotics/AR4)) to 1.9 kg (MK5 maker figure, [DEV](https://dev.to/circuitrocks/ar4-mark-5-this-open-source-6-axis-robot-arm-is-finally-done-44jm)) | 0.2 mm | claim; an independent MK3 review (Thomas Sanladerer) found "disappointing accuracy and repeatability", attributed to encoders fitted but closed loop not implemented in firmware ([Hackster](https://www.hackster.io/news/is-the-annin-ar4-the-workhorse-robot-arm-for-you-6a26487fb517)) | Own Python GUI, ROS 2 driver (community), RoboDK post | Open hardware (check repo for exact terms) |
| **PAROL6** (Source Robotics) | 6-DoF, fully printed structure, steppers with belt + printed/planetary reductions, closed-source control board | ~USD 1,000-1,500 class (kit) | 1 kg near base, 0.5 kg full workspace ([docs](https://source-robotics.github.io/PAROL-docs/page2_2)) | 0.1 mm ([docs](https://source-robotics.github.io/PAROL-docs/page2_2)); 0.08 mm in a press piece ([Hackster](https://www.hackster.io/news/petar-crnjak-s-parol6-is-an-industrial-style-robot-arm-you-can-print-and-build-at-home-366866022a7b)) | claim. Hackaday commenters note that open-loop stepper repeatability is motor-position repeatability, not TCP repeatability, and drifts without encoders or external calibration ([Hackaday](https://hackaday.com/2023/08/15/hackaday-prize-2023-parol6-a-gpl-desktop-robotic-arm)) | Commander GUI, Python API, ROS 2 + MoveIt ([README](https://raw.githubusercontent.com/PCrnjak/PAROL6-Desktop-robot-arm/main/README.md)) | GPL for software and STLs; CAD source paid (~USD 50); control board not open ([Hackaday](https://hackaday.com/2023/08/15/hackaday-prize-2023-parol6-a-gpl-desktop-robotic-arm)) |
| **Faze4** (same author, earlier) | 6-DoF, printed cycloidal gearboxes, steppers, Teensy 3.5 | <USD 1,000 (README) to USD 1,000-1,500 (docs) ([docs](https://faze4-robotic-arm-docs.readthedocs.io/en/latest/About_faze4.html)) | not found | none published | none | Low level on Teensy, IK in MATLAB only; author marks it work in progress | MIT ([GitHub](https://github.com/PCrnjak/Faze4-Robotic-arm)) |
| **Thor** (AngelLM) | 6-DoF, printed, steppers, belts + printed planetary reductions, Arduino Mega shield | <EUR 350 components ([GitHub](https://github.com/AngelLM/Thor)) | 750 g (blog) | not found | unverified | Modified GRBL with joint angles sent as custom G-code; ROS 2 / MoveIt 2 configs in Thor-ROS | CC-BY-SA-4.0; designed in FreeCAD/KiCad ([FreeCAD blog](https://blog.freecad.org/2024/03/05/forged-in-freecad-thor-an-opensource-robotic-arm/)) |
| **BCN3D Moveo** | 5-DoF, printed, steppers with long belt runs, Arduino/RAMPS | low hundreds EUR | not reliably reported (one paper's "5 kg" is not credible for this arm) | not found | none | Marlin/RAMPS-style, community ROS ports | Open source (CC) ([GitHub](https://github.com/jsechovec/BCN3D-Moveo)) |
| **SO-100 / SO-101** (TheRobotStudio + Hugging Face LeRobot) | 5-DoF + gripper, printed, 6x Feetech STS3215 serial-bus servos (12-bit magnetic encoder, ~15 kg.cm stall) | ~USD 130 non-printed parts per arm (HF estimate); USD 220 motor kit ([Hackster](https://www.hackster.io/news/hugging-face-launches-the-so-101-an-upgraded-low-cost-3d-printable-autonomous-robot-arm-532360f441eb)) | ~0.5 kg (unverified, [spec page](https://roboticscenter.ai/hardware/so-101/specs)) | community dial-indicator test: ~1 deg free-play backlash per servo, +/-0.3 mm at a 10 cm lever, firmware deadband <10 encoder steps (~0.9 deg) ([SO-ARM100 issue 134](https://github-users.yhajoa.workers.dev/TheRobotStudio/SO-ARM100/issues/134)); open backlash test-stand paper ([Zenodo](https://zenodo.org/records/19261714)) | measured (community, small sample) | LeRobot (Python, teleop leader/follower, imitation learning policies) ([docs](https://huggingface.co/docs/lerobot/en/so101)) | Apache-2.0 hardware/software |
| **Forte** (arXiv 2507.15693, 2025) | 6-DoF, fully printed; steel-cable capstan + timing belt hybrid on shoulder and elbow, differential wrist | <USD 215 materials (abstract; an earlier version said <USD 400) | 0.63 kg | 0.5 mm, reach 0.467 m | measured (self), paper ([arXiv](https://arxiv.org/abs/2507.15693)) | research code | see paper |
| **NeuralNexus Arm** (arXiv 2608.22799, 2026) | 6-DoF, STM32H743 custom PCB driving mixed external stepper drivers + onboard TMC2209 on the wrist | low cost (student) | not checked | not checked | paper | Web Serial browser UI, MATLAB/Simscape IK, vision pipeline ([summary](https://tldr.takara.ai/p/2608.22799)) | open |

### 1.2 Commercial small arms (reference points, all figures are maker claims)

| Arm | Payload | Reach | Repeatability | Price | Source |
|---|---|---|---|---|---|
| uFactory Lite 6 | 600 g | 440 mm | +/-0.5 mm | from USD 2,999 (USD 3,639 with gripper) | [uFactory](https://www.ufactory.cc/lite-6-collaborative-robot) |
| Dobot Magician (4-axis, steppers) | 500 g | 320 mm | +/-0.2 mm | ~USD 1,500 class | [RobotLAB](https://www.robotlab.com/store/dobot-magician-e6/), [RoboDK](https://robodk.com/robot/Dobot/Magician) |
| Dobot MG400 (4-axis SCARA-like) | 500 g (750 g max) | 440 mm | +/-0.05 mm | ~USD 4-5k | [spec sheet](https://cdn.shopify.com/s/files/1/0043/7154/6227/files/Dobot_MG400_SpecsSheet_C.pdf) |
| Elephant myCobot 280 | 200-250 g | 280 mm | 0.5 mm (aggregator only) | ~USD 700-1,000 | [RoboDK](https://robodk.com/robot/it/Elephant-Robotics/myCobot-280-M5), [review](https://the-gadgeteer.com/2023/06/02/elephant-robotics-mycobot-280-robotic-arm-review-a-cool-robotic-arm-that-costs-an-arm-and-a-leg/) |

Note the shape of the market: the commercial arms that publish +/-0.05-0.2 mm at this price are **4-axis** (Magician,
MG400), not 6-axis. A 4-axis (XYZ + wrist yaw) arm covers top-down pick-and-place and vertical insertion, which is most
of the mechloop task list, at a fraction of the error budget of a 6-axis serial chain.

### 1.3 What worked, what failed

Worked:
- **Steppers + timing belts + printed structure** is the proven cheap recipe (Thor, PAROL6, AR4, Moveo). Builders get
  arms that move and pick; the community is large; ROS 2 / MoveIt configs exist for most.
- **Capstan cable drives** (Forte) are the one cheap transmission with a published, method-described sub-mm result and
  zero backlash by construction. Forte only uses them on the two high-torque joints to limit complexity.
- **Serial-bus smart servos** (SO-101) give the cheapest full arm with absolute joint encoders and telemetry
  (position, load, temperature, voltage) over one wire. This is what made LeRobot's data collection practical.
- **Cycloidal printed gearboxes** (Faze4) print well and are easily repaired, but no published accuracy figure exists.

Failed or weak:
- **Encoders fitted but loop not closed** (AR4 MK3): independent review found disappointing accuracy. Open-loop
  steppers lose steps silently; a stall during a print pull would leave the arm "believing" it is elsewhere.
- **Repeatability numbers are almost all claims.** None of AR4, PAROL6, Thor, Moveo, Faze4 publishes an ISO 9283-style
  test (fixed pose, N cycles, dial indicator or camera, stated load and temperature). Forte and the SO-101 community
  test are the exceptions.
- **Long belt runs** (Moveo) need careful tensioning and give compliance at the TCP.
- **Closed parts of "open" stacks** (PAROL6 control board, paid CAD) block modification: exactly what a recursive
  self-improving loop needs to do.
- **SO-101 wear**: forum reports of repeatability degrading after repeated use from loosening set screws and servo
  horn play ([forum](https://www.roboticscenter.ai/en/forum/posts/so-101-backlash-after-repeated-demos-and-set-screw-checks-for-educators-schools-intermediate)).
  Hobby servos also have ~1 deg backlash, which at a 300 mm reach is ~5 mm of slop before any compensation.
- **Faze4's IK in MATLAB only** shows the software gap: the mechanics shipped before a usable control stack.

### 1.4 Borrow / avoid for mechloop

- **Borrow** Forte's error-budget-first approach: name backlash and drivetrain stiffness as the design drivers and put
  zero-backlash transmissions (capstan or tensioned belt) where the lever arm is longest.
- **Borrow** encoder-closed joints (either closed-loop steppers, magnetic encoder on the output shaft, or bus servos with
  output-side sensing). Output-side absolute encoders also remove homing switches.
- **Borrow** the LeRobot software model (Python, open dataset format, leader/follower teleop) as a data path even if the
  hardware is ours; it makes demonstration-based tuning possible.
- **Borrow** Thor's "joint angles as G-code over serial" trick: the printer's Klipper/G-code tooling can then drive the
  arm, and the digital twin can replay the same file.
- **Avoid** publishing a repeatability number without a test method; plan our own ISO 9283-style fixture (dial
  indicator plus camera fiducial) as a first-class deliverable, so the twin can be calibrated against it.
- **Avoid** 6 DoF unless a task needs it. Seriously evaluate 4-axis (SCARA or vertical-articulated with wrist yaw) and
  a 5th axis (wrist pitch) only for sheet flexing.

---

## 2. 3D-printer tending and print-farm automation

### 2.1 Approaches seen

| Approach | Example | How parts come off | Evidence | Notes |
|---|---|---|---|---|
| **Arm swaps whole plates** | Voodoo Manufacturing Project Skywalker: UR10 on a mobile base, printers in racks, plate hopper ([UR case](https://www.universal-robots.com/case-stories/voodoo-manufacturing/), [Medium](https://medium.com/voodoo-manufacturing/announcing-project-skywalker-bf9efa99a677)) | Arm pulls the plate, places it on a conveyor; humans remove parts offline | company-reported: harvesting had been up to 10 % of labour; utilisation rose from ~30-40 % to ~90 %; output tripled; ROI "within six months" ([3DPI](https://3dprintingindustry.com/?p=131339), [Robot Report](https://www.therobotreport.com/voodoo-manufacturing-triples-3d-printing-production-collaborative-robots/)) | Arm never touches parts. Fleet size reported as 100 to 200+ printers per arm depending on date. Company later closed, so long-run data is absent. |
| **Robotic harvester + sheet storage, productised** | Prusa Pro AFS: 9-printer cell, robotic harvester, sheet storage, Prusa Connect Farm ([Prusa](https://www.prusa3d.com/en/applications/prusa-pro-afs_236928/)) | Harvester removes the spring-steel sheet, drops parts into storage, loads a fresh sheet | claim only; ORNL customer webinar due 7 Dec 2026 may give real data | Closest commercial analogue to our PEI-flex-sheet printer. Printers are swappable while 8 keep running. |
| **Arm swaps flexible beds, research** | KUKA 7-DoF + Robotiq 2F-85 tending Ender 3 V2 ([Springer](https://link.springer.com/chapter/10.1007/978-981-99-3330-3_27)) | Arm exchanges flexible magnetic beds; also proposes arm-applied glue | paper (results not in snippets) | Related work cites flexible-bed swapping because the arm never contacts the part. |
| **Arm handles parts for an autonomous experiment loop** | BEAR (Gongora et al., Sci. Adv. 2020): 5 FDM printers, 6-axis arm, scale, universal testing machine ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC7148087)) | Arm removes specimens, weighs them, loads the tester | measured: >2,500 structures tested autonomously over 3 campaigns; Bayesian optimisation needed ~60x fewer experiments than grid search ([BU](https://www.bu.edu/eng/2020/07/08/when-the-robot-becomes-the-researcher)) | **The closest prior art to mechloop's loop** (print, handle, measure, update model, print again). Simple, repeatable specimen geometry made gripping easy. |
| **Arm sweeps parts off (vision-triggered)** | 2016 RPJ paper ([Emerald](https://www.emerald.com/insight/content/doi/10.1108/RPJ-02-2016-0029/full/html)) | Vision detects job end, arm pushes part off | paper | Requires free plate edges so parts can slide off. |
| **Hybrid print + pick-and-place workcell** | Kosmal et al. 2022, 6-DoF arm with FFF head + PnP tool, drone case study ([record](https://katalog.lib.cas.cz/KNAV/EdsRecord/edsdoj,edsdoj.99520ae8614e4236925d9bc2f10d836f), DOI 10.1016/j.addlet.2022.100100) | Includes an "autonomous part tending mechanism" | paper | Prints enclosure, inserts electronics, embeds them. |
| **Flexible bed through a curved track (no arm)** | WPI MQP ([WPI](https://digitalwpi.wpi.edu/downloads/bg257h749?locale=fr)) | Bending the spring-steel sheet breaks adhesion | student project | Physically the same release mechanism we would use with an arm. |
| **Printer's own gantry pushes parts off** | 3DQue Quinly / AutoFarm3D with VAAPR bed ([All3DP review](https://all3dp.com/1/3dque-quinly-review-automated-3d-printing/)); Bambu auto-ejection kit ([Tom's HW](https://tomshardware.com/3d-printing/new-auto-ejection-tool-for-bambu-lab-print-farms-automatically-ejects-finished-3d-prints-from-the-machine-usd129-kit-includes-auto-door-opener-and-special-bed-surface-for-frictionless-part-ejection)) | Bed grips hot, releases cold; X carriage sweeps | reviewer: "does what it's supposed to"; critics: cool-down wait, gantry wear and lost accuracy from repeated pushing, failures on thin/small parts | Cheapest, but uses the printer as a bulldozer. |
| **Add-on scraper arm** | Prusa MK3 "Chain Production" ([Hackaday](https://hackaday.com/2020/07/20/automated-part-removal-gets-serious-with-the-chain-production-add-on)) | Two-stepper arm with angled blades sweeps cooled bed | anecdotal; commenters: no way to confirm the part actually came off | Matte steel sheet: sticks hot, "practically no stick" cold. |
| **Plate changers (stacks of sheets)** | Chitu PlateCycler (A1 mini, up to 10 PEI plates), SwapMod, AutoSwap, JobOx ([Hackaday](https://hackaday.com/2024/09/30/3d-printer-swaps-build-plates-to-automate-print-jobs), [Hackaday 2026 test](https://hackaday.com/2026/01/16/testing-a-continuous-printing-mod-for-the-bambu-lab-a1-mini)) | Ejects the full plate along Y, loads a blank from a stack | vendor claims plus hobby tests | Works because a bed slinger's Y axis does the transfer. A forum view: a 6-DoF arm for this is "ridiculously overengineered" ([Bambu forum](https://forum.bambulab.com/t/automation-for-a1-3d-print-farm/117207)). |
| **Resin: build-platform flex release** | Formlabs Form Auto, USD 299 ([Formlabs](https://formlabs.com/3d-printers/form-auto/)) | Actuates a flexing build platform to drop parts into a bin | vendor | Again: flex the substrate, do not pry the part. |

### 2.2 What worked, what failed

Worked:
- **Never grip the print on the bed; move the sheet.** Voodoo, Prusa AFS, the KUKA paper and plate changers all handle
  the substrate, not the part. The sheet is a known, rigid-enough, fixtured object with a repeatable grasp; parts are
  not.
- **Release by temperature and flexing.** Spring steel sticks hot and releases cold (Chain Production, VAAPR, WPI curved
  track, Form Auto's flex platform). Flexing is gentler and more reliable than scraping.
- **Value is unattended hours,** not speed. Voodoo's gains came from running overnight (utilisation 30-40 % to ~90 %).
- **Closed-loop experimentation works with a dumb arm** (BEAR): the arm's job was simple and repetitive; intelligence
  lived in the optimiser and the measurement station.

Failed or open:
- **Detecting that the part is actually off** is the recurring unsolved complaint (Chain Production comments). Every
  system needs a post-removal check (camera, weight, or bed-mesh probe).
- **Small/thin parts** defeat push-off and sweep methods (Quinly critics); also parts with low bed contact.
- **Using the printer's gantry as a pusher** loads belts and rollers repeatedly and may degrade print accuracy.
- **No independent long-run reliability data** exists for any productised system found (Prusa AFS, Quinly, plate
  changers). Voodoo's numbers are company-reported and the company is gone.

### 2.3 Borrow / avoid for mechloop

- **Borrow**: arm task 1 is "grip the PEI sheet tab, lift it off the magnetic base, carry it to a flexing station (or
  flex it in a two-point grip), let parts drop or present them, return the sheet." This needs ~0.5-1 mm placement
  repeatability onto locating pins, not 0.1 mm, because the bed's own pins do the final locating.
- **Borrow**: add sheet-locating pins/notches and a grip tab to the printer's sheet; the Prusa-style rear pins are the
  pattern. This is a printer change that makes the arm cheaper.
- **Borrow**: a verification step after every unload (camera image of the empty sheet plus a scale under the drop bin);
  log it to the twin.
- **Borrow** BEAR's architecture for mechloop's outer loop: printer(s) + arm + measurement station + optimiser.
- **Avoid** scraping printed parts off with an arm-mounted blade: high force, PEI damage, and failure on small parts.
- **Avoid** reusing the printer gantry as the ejector if print accuracy is itself a loop metric.

---

## 3. Robotic assembly of printed parts

### 3.1 What exists

| Task | Prior art | Evidence | Takeaway |
|---|---|---|---|
| **Heat-set inserts** | No robotic system found in search. Manual rigs (drill-press style iron holders) exist because perpendicularity matters ([Adafruit rig](https://learn.adafruit.com/heat-set-rig?view=all)); iron 343-399 C, 0.3-0.5 mm chamfer guide ([LulzBot](https://lulzbot.com/learn/tips-and-tricks-heat-set-inserts), [EPFL](https://make.epfl.ch/wiki/public/spot_-_3d_printing/how_to_use_threaded_inserts)) | practice guides | Do it as a **fixed station** (vertical heated press with a linear axis) that the arm loads, not as an arm-held iron. The arm only places the part in a nest and drops an insert on the hole. |
| **Screw driving** | O2AC (WRS assembly challenge) 3D-printed screw tool driven by a ~USD 24 servo with a compliant tip, versus USD 1,000-1,500 commercial tools ([O2AC wiki](https://github.imc.re/o2ac/o2ac-ur/wiki/tools)); UT Austin autonomous assembly platform with screw delivery for printed robots ([UT SFF 2024](https://utw10945.utweb.utexas.edu/sites/default/files/2024/100%20Automated%20Assembly%20and%203D%20Printing%20for%20the%20Man.pdf)) | research build notes | Compliant tip + magnetic or vacuum bit + torque sensing by motor current is the cheap recipe. A screw presenter/feeder simplifies the arm's job. |
| **Peg-in-hole on printed parts** | Barrett WAM with 3D-printed pegs at <0.25 mm clearance ([arXiv 2106.14070](https://arxiv.org/pdf/2106.14070)); compliant robot hitting <0.25 mm without known hole pose ([Morgan ICRA 2023](https://www.eng.yale.edu/grablab/pubs/Morgan_ICRA2023.pdf)); dynamic compliance tuning at 0.02-0.05 mm on printed parts ([arXiv 2311.07499](https://arxiv.org/pdf/2311.07499)); contact-manifold pose estimation with 0.1-1.0 mm clearance ([arXiv 2507.03925](https://arxiv.org/pdf/2507.03925)) | measured, but on research-grade arms | Every success used **compliance** (passive wrist, impedance control, or a compliant hand) plus sensing; position control alone does not insert tight fits. No low-cost-arm insertion benchmark found. |
| **Tool / end-effector changing** | Berkeley CASE 2018 open two-cone mostly-printed tool changer on a Fetch: 92/100 successful couplings, failures from arm positioning error ([paper](https://goldberg.berkeley.edu/pubs/CASE2018-ron-tool-changer-submitted.pdf)); open small-robot changer, PETG + 8 mm balls, servo lock, tool-present sensor ([Instructables](https://www.instructables.com/Open-Source-Tool-Changer-for-Small-Industrial-Robo)); kinematic coupling + servo magnetic twist lock prototype, printed cam wears ([Instructables](https://www.instructables.com/Magnetic-3D-Printed-Toolchnager/)); SwapBot self-aligning electromagnetic hub, ~50 N ([arXiv 2610.40646](https://arxiv.org/pdf/2610.40646)); Jubilee / E3D printer toolchangers (kinematic balls/pins + twist lock) | measured (Berkeley), others prototypes | Kinematic coupling (3 balls in 3 V-grooves or pins) gives repeatable seating; the cone/chamfer capture range must exceed the arm's positioning error. Wear surfaces should be metal (balls, dowels), not printed. |
| **Hybrid print + place** | Kosmal et al. 2022 (see 2.1) | paper | Printing and assembly in one cell is demonstrated; electromagnetic PnP is enough for steel fasteners. |

### 3.2 Borrow / avoid for mechloop

- **Borrow**: design-for-robot-assembly in the printed parts themselves: chamfers and lead-ins sized to the arm's
  measured error, self-locating snap/press features, and vertical-only insertion directions. This is cheaper than a
  more precise arm and is something the printer loop can improve each iteration.
- **Borrow**: a passive compliant wrist (remote centre compliance made from a printed flexure) on assembly tools.
- **Borrow**: Berkeley's lesson for the end-effector changer: measure success over 100+ cycles and size the capture
  cone to the arm's real error. Use steel balls/dowels on printed bodies, magnets or a servo lock for retention, and an
  electrical or Hall "tool present / which tool" signal.
- **Avoid**: an arm-held soldering iron for inserts (cable, heat, perpendicularity); a stiff, position-controlled
  insertion with no compliance.

---

## 4. Cross-cutting lessons

1. **Handle the sheet, not the print.** Every working farm automation moves the substrate and releases parts by
   cooling and flexing. Our printer already has a magnetic PEI spring-steel sheet; add grip tab and locating pins.
2. **Repeatability claims in this class are mostly unmeasured.** Plan our own ISO 9283-style test fixture from day one
   and feed results into the digital twin; treat "0.1 mm" from an open-loop stepper arm as motor repeatability only.
3. **Close the loop at the joint output.** Missing or unused encoders (AR4 MK3) and ~1 deg servo backlash (STS3215) are
   the two documented failure modes. Zero-backlash transmissions on the long-lever joints (Forte's capstan) plus
   output-side absolute encoders are the cheapest fix with published evidence.
4. **Put precision in fixtures and part features, not the arm.** Locating pins on the sheet, nests for assembly,
   chamfers/lead-ins, a passive compliant wrist, and fixed stations (insert press, screw presenter) let a ~0.5 mm arm do
   jobs that would otherwise need 0.05 mm.
5. **Verify every step.** Part-off detection is the most common unsolved complaint; tool-changer failures came from
   positioning error. Camera + scale + tool-present sensing, logged per cycle, is what turns the cell into a loop (as
   BEAR did).
6. **Consider fewer axes.** The commercial arms with the best published repeatability at low cost are 4-axis; most of
   our tasks are top-down. A 5th axis may be needed only for sheet flexing/tilting.
7. **Openness matters for recursion.** Prefer fully editable stacks (MIT/Apache/CC-BY-SA, CAD source available, open
   control electronics). PAROL6's paid CAD and closed board would block the self-improvement loop.

## 5. Gaps found

- No independent repeatability measurement found for AR4 MK5, PAROL6, Thor, Moveo or Faze4.
- No robotic heat-set insert system found in public sources.
- No low-cost-arm peg-in-hole benchmark found.
- No independent reliability data for Prusa Pro AFS, Quinly, or plate changers (the 7 Dec 2026 ORNL webinar is a lead).
- BEAR's arm model and the KUKA/Ender paper's quantitative results were not visible in search snippets; read the full
  texts before citing numbers from them.
