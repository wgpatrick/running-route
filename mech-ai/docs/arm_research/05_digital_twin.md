# Arm research 05: digital twin and simulation stack

Scope: what simulates, plans, and checks a robot arm we design ourselves, held to the same standard as the printer
(PRINTER_V12: geometry, interference, motion with pose sweep + MuJoCo + belts, FEA via Gmsh -> CalculiX, tolerance,
thermal, DFM, assemblability, electrical, and a digital twin that runs the real firmware offline). Written 2026-11-21.
Nothing here was run; it is a reading of the repo plus web research (sources at the end).

## 1. What we already have that matters

Read briefly in `mechloop/`:

- `model.py`: `Joint` is already a general 1-DOF joint (`slide` in mm or `hinge` in deg), with `range`,
  `overtravel`/`mechanical_range`, `max_effort/speed/accel`, a `drive` dict resolved by `verifiers/ratings.py`,
  `reflected_inertia` and `min_drive_margin` (whose comment says friction is not modelled). An arm is a chain of
  hinges; the data model needs no new joint kind, only richer drive data (see 4.2).
- `verifiers/motion.py`: `sample_poses` (per-joint grid + corners + random), `colliding_pairs`, `build_mujoco`
  (bodies and inertials from the CAD), and `_dynamics`, which runs `mujoco.mj_inverse` over static poses and
  trapezoidal moves to get required effort per joint. That is already the core of an arm torque check; for a serial
  arm the coupling between joints matters much more than on a gantry, which the pose sweep already captures.
- `twin/stepper.py` (numba): motor inertia + torque-angle curve + series spring + backlash + friction, with step
  loss. Built for belts, but the equations are those of a stepper-driven geared joint (swap belt stiffness for
  gearbox torsional stiffness).
- `twin/firmware.py`, `klippy_code.py`, docs/FIRMWARE_IN_THE_LOOP.md: the pattern of running the real planner
  offline and feeding its step stream into the plant model. The lessons there (homing refused, origin mismatch, a
  67 s clock wrap) are exactly the kind of bug a controller-in-the-loop arm twin should catch.
- `twin/calibration.py`: a blind predict-then-compare protocol with frozen, hashed predictions and a separate
  "posthoc (NOT blind)" mode. The arm's validation plan (section 7) should reuse this structure verbatim.
- `tolerance/process.py`: per-process sigma tables (printed: pos 0.12 mm, hole bias -0.15 mm, hole sd 0.07). These
  feed the arm's kinematic-error Monte Carlo and the press-fit model directly.

## 2. Physics engine comparison

| Engine | Fit with Python/build123d/MuJoCo | Strengths for us | Weaknesses for us | Verdict |
|---|---|---|---|---|
| MuJoCo 3.x (CPU, `pip install mujoco`) | Already in `motion.py`; MJCF generated from the CAD | Fast, deterministic, `mj_inverse` for torque checks, `dcmotor` actuator with a torque-speed envelope and current saturation, joint `armature`/`frictionloss`/`damping`, offscreen `mujoco.Renderer` with RGB, depth and segmentation; 3.7 lets joint-transmission actuators contribute armature and damping | Soft, convex-hull contact by default is optimistic for grasps; plain Coulomb-viscous friction misses low-speed servo behaviour (Duclusaud et al. 2024); no native backlash element (model it, 4.2) | **Primary** |
| MuJoCo Warp / MJX | Same models | GPU batch for large randomized sweeps (grasp randomization, RL) | Needs an NVIDIA GPU for speed (CPU only for debugging); MJX-Warp has no autodiff | Optional later, not needed for verification |
| Drake (`pip install drake`) | Reads URDF/SDF; can be generated alongside MJCF | Hydroelastic contact (pressure-field patches, matches analytic results within 1.3 % in Elandt/Masterjohn's tests, captures torque-holding a TRI point contact gets wrong); rigorous `MultibodyPlant`; KinematicTrajectoryOptimization; GCS planner (experimental) | Heavier API, slower than point contact, compliant geometry needs tet meshes; second model to keep in sync | **Secondary**: grasp cross-check and optimisation-based planning |
| PyBullet | Easy | Familiar | Development largely stalled since 2023 (last releases 3.2.6 Nov 2023, 3.2.7 Jan 2025; Snyk "inactive") | Reject |
| Isaac Sim / Isaac Lab | Python, USD | Best photoreal cameras, GPU physics, RL | Isaac Sim 5.x reference GPU RTX 4080 16 GB+, RT cores required; Linux container; huge stack; not deterministic CI material | Reject for the verifier; revisit only for learned policies |
| Gazebo (Jetty, LTS Sep 2025) + gz_ros2_control | ROS-centric, C++ | Natural if the arm's firmware is ROS 2; gz_ros2_control added an actuator-dynamics demo plugin | Physics (DART/Bullet) no better than MuJoCo for our purpose; adds a ROS install to CI | Only if we adopt ROS 2 on the arm (see 3.2); otherwise reject |

## 3. Planning and controller in the loop

### 3.1 Motion planning

| Option | Notes | Verdict |
|---|---|---|
| MoveIt 2 | Full stack (OMPL, Pilz, CHOMP/STOMP, time parameterization) over ROS 2; mock hardware available | Use only if the arm runs ROS 2 |
| OMPL | 2.0 rewrote the Python bindings (nanobind) and ships pip wheels; 1.7 wheels reported fragile | **Use OMPL 2.0 RRT-Connect/BIT\***, collision callback = MuJoCo `mj_collision` on the same model the motion verifier uses |
| cuRobo | ~50 ms collision-free IK + trajectory optimisation on GPU, PyTorch; cuRoboV2 adds torque limits | Needs CUDA GPU; reject for CI, note as the fast option if a GPU appears |
| Drake planners | KinematicTrajectoryOptimization (stable), GcsTrajectoryOptimization (experimental) | Second opinion for cycle-time optimality |
| Ruckig | Time-optimal, jerk-limited, multi-DoF synchronised OTG; Python module; community version is real-time only without intermediate waypoints | **Use for time parameterization**, and run the same library on the arm controller so planned and executed profiles match |

The verifier does not need a clever planner; it needs the plan the arm will actually execute. So whatever generates
trajectories on the real arm is what runs in the twin (3.2), and OMPL is the path finder for the benchmark task.

### 3.2 Controller in the loop (the arm's "Klipper offline")

Klipper is not a good arm firmware: it has no built-in SCARA or serial-arm kinematics and community attempts at
SCARA remained unfinished. For a 5-6 DOF arm the realistic choices are:

| Firmware family | Offline option | What is real in the twin |
|---|---|---|
| ROS 2 + ros2_control + MoveIt 2 | `mock_components/GenericSystem` mirrors commands to states (ideal, optional `calculate_dynamics`); write our own `hardware_interface` plugin that forwards commands to the MuJoCo plant over a socket | Planner, controllers (joint_trajectory_controller), limits, URDF, launch wiring |
| Custom host planner (Python/C) + joint drivers | Same pattern as klippy offline: the host program writes its command stream to a file given a job file; decode and drive the plant | Everything on the host; the drive's own loop is modelled |
| Steppers (TMC drivers, open loop or closed loop) | Command stream = step times, exactly the printer path; reuse `twin/stepper.py` with gearbox stiffness/backlash | Step timing, step loss |
| BLDC + FOC (moteus, ODrive) | No vendor simulator found. Model the drive as torque = setpoint through a current-loop bandwidth (ODrive forum advice: current loop auto-tunes, treat as passthrough) plus the drive's position/velocity PID with gains read from the same config file we flash | Our gains and limits; the drive's firmware itself is not run |

Recommendation: keep the trajectory generator and joint-space controller in a host-side program we own, with a
hardware abstraction layer whose "sim" backend talks to MuJoCo at the controller's real rate (e.g. 1 kHz, MuJoCo
stepping at 0.5-1 ms). This gives a Real / Simulated / Not covered table like FIRMWARE_IN_THE_LOOP.md. If ROS 2 is
chosen, the same plant is reached through a custom ros2_control hardware plugin, and `mock_components` is used only
for wiring tests.

## 4. Plant model fidelity

### 4.1 Rigid bodies and inertia
From build123d solids with material densities (already done by `body_inertials`). Add purchased-part masses
(motors, gearboxes, bearings) from vendor data; the printer's purchased-part placeholders show this is where mass
errors hide.

### 4.2 Drivetrain per joint
Model each joint as motor rotor -> gearbox -> link, in MJCF:

- Motor: MuJoCo `dcmotor` actuator (or `motor` + explicit clamp) giving the torque-speed parallelogram, stall torque,
  no-load speed, current limit; for steppers, the torque-angle model of `twin/stepper.py` with pull-out torque vs
  speed from the datasheet.
- Reflected inertia: `armature = J_rotor * N^2` (watch the 3.7 change so it is not counted twice).
- Backlash and compliance: insert a passive hinge between the gearbox output body and the link with `range = +/- b/2`
  (backlash as a hard limit band) and `stiffness = k_gearbox` (torsional stiffness). With `range` the slack is free
  motion, with the limit the stiffness acts. For hysteresis (harmonic or cycloidal), Bouc-Wen or Maxwell-slip
  elements in a passive callback are the literature models; start with deadband + linear spring.
- Friction: `frictionloss` (Coulomb) + `damping` (viscous), identified at several speeds; add gearbox efficiency as an
  asymmetric torque loss (drive vs backdrive), since a printed cycloid or planetary may not be backdrivable at all.
  Duclusaud et al. show plain Coulomb-viscous misfits servos at low gains; mjlab/BAM offer extended models if needed.
- Link compliance: derive lumped bending/torsion stiffness per link from the existing FEA pipeline (unit loads at
  the distal interface, CalculiX), then insert as extra passive hinges. This keeps CalculiX out of the time loop.

Printed gear trains: lost motion depends on tolerance as much as stiffness (cycloid FE studies), so `b` comes from the
tolerance Monte Carlo, not a constant.

### 4.3 Contact and grasp
Known sim-to-real gaps: coarse friction approximation and optimistic antipodal-grasp evaluation are the top causes
of sim-only grasps failing (domain randomization literature); rigid printed fingers amplify slip; Fit2Form used
finger friction 1.0, which is optimistic for bare PLA. Real tip surface changes success hugely (Berkeley: 28.7 % ->
68.7 % by taping tips). So:

- MuJoCo with `condim=4` or `6`, elliptic cones, `noslip` iterations on, finger meshes as convex decompositions,
  friction drawn from a range (bare PLA/PETG vs object, TPU pads) rather than a point value.
- Grasp passes only if robust over the randomized set (friction x0.6-1.0 of nominal, object pose +/- tolerances,
  mass +/- 20 %), and cross-checked in Drake hydroelastic for the worst cases. Report success rate with a Wilson
  interval, not a single number.
- Compliant fingers (TPU, flexures): IPC-GraspSim shows modelling tip compliance reduces the gap; for us, a flexure
  finger is better modelled as a chain of hinged segments with FEA-derived stiffness than as a rigid body.

### 4.4 Cameras
`mujoco.Renderer` gives RGB, depth and segmentation offscreen on a headless server. Add a camera model per real
camera (intrinsics, resolution, lens distortion applied in post, noise, motion blur from link velocity, exposure).
Use for: wrist/overview camera field-of-view and occlusion checks over the task, ChArUco hand-eye calibration
reprojection error in sim, and detection of the benchmark objects. Photorealism is not needed for these geometric
checks; Isaac is not justified. This links to the existing NOZZLE_CAMERA/INSPECTION work.

### 4.5 Joining-process models (heat-set inserts, screws, press fits)
Static, rule-plus-formula checks, not simulation:
- Heat-set insert: pull-out and torque-out capacity per size and material (Kastner et al. 2023 need >= 2.4 mm wall
  around their insert for full pull-out force; a vendor test ranks PLA above PETG; Sculpteo's PA12 data 477 N M2 to
  >1800 N M5/M6 for scale). Check boss wall, insert depth vs part thickness, axis vs layer direction, and load per
  insert from the FEA reaction forces with a creep knock-down for sustained load.
- Screw into plastic: thread-forming engagement length, strip torque vs specified torque.
- Press-fit bearing seats: interference from nominal + printed hole bias/sd (`process.py`), thick-walled-cylinder
  hoop stress against yield, and creep-loss of retention over time; prefer a clamped design if the MC gives loose fits
  in more than a small fraction.
- Preload loss in printed clamped joints (creep) affecting joint stiffness and backlash over time.

## 5. New verifiers to build

| # | Verifier | Inputs | Outputs | Pass criteria (initial, tune per spec) |
|---|---|---|---|---|
| 1 | `arm_kinematics` | Design joints, TCP frame, task poses | Workspace samples, IK success per task pose, manipulability and min singular value along tasks, joint-limit margins | Every task pose reachable with >= 5 deg limit margin; Yoshikawa manipulability above a threshold along all task paths; no path through a singularity |
| 2 | `arm_dynamics` (extends `motion._dynamics`) | Inertials, drive data (motor curve, ratio, efficiency), payload, trajectories | Peak and RMS torque per joint vs envelope at the actual speed, holding torque at worst pose | Peak <= available/1.5 at that speed; RMS <= continuous; holding torque at full payload worst pose <= 50 % of continuous (or brake/non-backdrivable declared) |
| 3 | `drivetrain_stiffness` | Gear backlash (from tolerance MC), gearbox stiffness, FEA link stiffness | TCP deflection and lost motion per pose and payload | Payload sag at full reach <= spec (e.g. 1 mm at rated load); lost motion at TCP <= spec |
| 4 | `arm_accuracy` (tolerance MC) | `process.py` sigmas, kinematic chain, encoder/step resolution, backlash distribution | Predicted repeatability (ISO 9283 RP) and absolute accuracy before/after calibration | Predicted RP 95th percentile <= target (e.g. 0.5 mm) |
| 5 | `arm_cycle` | Benchmark task (pick-place list), OMPL + Ruckig | Collision-free path, cycle time, min clearance | Collision-free with >= 5 mm clearance including cables; cycle time <= target |
| 6 | `arm_controller_loop` (SIL) | Our controller code with sim HAL, MuJoCo plant with 4.2 drivetrain | Tracking error RMS/max, overshoot, settling time, step loss, limit/torque saturation events, stop distance on e-stop | No step loss/saturation on benchmark; max tracking error <= spec; stop distance within the guarded zone; no "planned motion vs executed" divergence > threshold (as in FIRMWARE_IN_THE_LOOP) |
| 7 | `grasp` | Finger CAD, materials, objects, gripper drive | Success rate under randomization, slip margin, required grip force vs available | Lower Wilson bound of success >= target on each object; Drake agrees on worst cases |
| 8 | `vision` | Camera specs and mounts, task scene | FOV/occlusion over task, simulated hand-eye calibration error, marker detection rate | Target visible in >= 95 % of task frames; sim calibration reprojection error <= 0.5 px |
| 9 | `joint_processes` | Fastener/insert/press-fit list, FEA loads | Capacity/demand per insert, screw, seat | Margin >= 2 on pull-out/torque-out, press-fit retention in >= 99 % of MC samples |
| 10 | `arm_thermal` | Duty cycle from #5/#6, motor thermal resistances, enclosure | Winding and gearbox temperature | Below class limit and below printed-part softening (PLA HDT ~55 C) at mounts |
| 11 | `cable_wrap` (extends cable checks) | Cable routes through joints | Bend radius and twist over full joint range | Bend radius >= min, no snag/interference over mechanical range |
| 12 | `modal_arm` | Lumped stiffness + inertia, MuJoCo linearisation or CalculiX modal | First modes per pose | First mode above controller bandwidth x3 (or input shaping declared) |

## 6. What carries over from the printer verifiers

| Printer verifier | Carry-over |
|---|---|
| geometry, interference, assemblability, DFM (`dfm_*`), manufacture, purchased, practice | Unchanged; they operate on parts |
| motion (`sample_poses`, `colliding_pairs`, `build_mujoco`, `_dynamics`) | Directly; serial chains just have more coupled joints; extend with drivetrain bodies and dcmotor actuators |
| belts | Not used, except a belt-reduced joint (common in printed arms) |
| ratings (`resolve_drives`) | Extend drive kinds: planetary, cycloidal, strain-wave, capstan, with ratio, efficiency, backlash, stiffness |
| FEA | Reused for link stiffness extraction and insert/boss loads; add load cases at worst pose with payload and peak acceleration (from #2) |
| tolerance | Reused for kinematic parameter errors and gear backlash distributions |
| thermal | Reused for motor and electronics heat |
| electrical | Reused (supply, wire gauges, fuses), plus motor peak current and regen |
| fastener_stack, bearing | Reused for joint bearings and clamps |
| printing twin (PrusaSlicer -> Klipper -> physics) | Still applies to printing the arm's parts; the arm twin's structure (real planner offline -> plant -> compare) mirrors it |
| twin/stepper.py | Reused for stepper-driven joints |
| twin/calibration.py | Reused protocol for blind predictions |

## 7. Validation plan on the built arm

Follow `twin/calibration.py`: freeze predictions with intervals before any measurement, store the hash, measure,
compare, and label any refit "posthoc (NOT blind)".

| Quantity | Prediction source | Measurement | Protocol |
|---|---|---|---|
| Pose repeatability RP | `arm_accuracy` | Dial indicators on a fixture cube or camera + ChArUco at TCP | ISO 9283-style: 5 poses on a test cube, 30 cycles, RP = mean distance to barycentre + 3 sd; at 50 % and 100 % speed and rated load |
| Backlash / lost motion per joint and at TCP | `drivetrain_stiffness` | Dial indicator at a known radius, torque reversal +/- with a spring scale | Hysteresis loop; report deadband and stiffness slope |
| Payload sag | `drivetrain_stiffness` + FEA | Indicator at TCP, 0 / 50 / 100 / 120 % rated load, extended pose | Linear fit; compare slope and offset |
| Joint and link stiffness, first mode | `modal_arm` | Tap test with the ADXL345 already in the printer stack | Peaks vs predicted modes per pose |
| Tracking error and torque | `arm_controller_loop` | Controller logs (encoder, current) on the benchmark trajectory | Overlay sim vs real; RMS difference |
| Cycle time | `arm_cycle` | Logged timestamps | Benchmark task, 10 runs |
| Grasp success | `grasp` | 50 trials per object, scripted positions with injected pose noise | Success rate with Wilson interval vs predicted interval |
| Motor temperature | `arm_thermal` | Thermocouple on motor case after 30 min duty cycle | Steady-state rise |
| Insert pull-out | `joint_processes` | Pull test on coupons printed with the same settings | 5 coupons per size |

Pass for the twin: measurement inside the pre-registered interval for each quantity. Misses are kept in the record
and drive a posthoc parameter update with uncertainty, never a silent change of defaults.

## 8. Recommended stack, in short

MuJoCo (CPU) as the plant and dynamics engine, MJCF generated from build123d via the existing `build_mujoco`,
extended with dcmotor actuators, armature, friction, and backlash/compliance hinges; OMPL 2.0 pip for paths with
MuJoCo collision checks; Ruckig for time-parameterization on both twin and arm; our own host controller with a
sim HAL running in the loop (ros2_control hardware plugin only if ROS 2 is adopted); Drake as the grasp and
trajectory-optimisation cross-check; `mujoco.Renderer` for cameras; CalculiX kept out of the time loop through
lumped stiffness. Not used: PyBullet (stalled), Isaac and cuRobo (GPU-bound), Gazebo (unless ROS 2), Klipper
(no arm kinematics).

## Sources

- MuJoCo DC motor technical note: https://mujoco.readthedocs.io/en/latest/_static/dcmotor.pdf
- MuJoCo 3.7.0 changelog: https://mujoco.readthedocs.io/en/3.7.0/changelog.html
- Duclusaud et al., Extended friction models for servo actuators: https://arxiv.org/html/2410.08650v2
- mjlab actuators: https://mujocolab.github.io/mjlab/main/source/actuators.html ; BAM: https://bam.readthedocs.io/en/latest/usage/mjlab_gpu.html
- MuJoCo Warp: https://github.com/google-deepmind/mujoco_warp ; MJX: https://mujoco.readthedocs.io/en/stable/mjx.html
- MuJoCo rendering tutorial: https://raw.githubusercontent.com/tayalmanan28/MuJoCo-Tutorial/main/tutorial/02_rendering.ipynb
- Drake hydroelastic: https://drake.mit.edu/doxygen_cxx/group__hydroelastic__user__guide.html ; https://arxiv.org/pdf/2110.04157 ; TRI: https://medium.com/toyotaresearch/rethinking-contact-simulation-for-robot-manipulation-434a56b5ec88
- Drake pip and planning: https://drake.mit.edu/pip.html ; https://drake.mit.edu/release_notes/v1.32.0.html
- PyBullet status: https://pypi.python.org/pypi/pybullet ; https://snyk.io/advisor/python/pybullet ; https://kushal-a.github.io/robot_RL_guide/news.html
- Isaac Sim requirements: https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/requirements.html ; Isaac Lab: https://arxiv.org/html/2511.04831v1
- Gazebo Jetty: https://discourse.openrobotics.org/t/gazebo-jetty-released/50349 ; gz_ros2_control: https://control.ros.org/jazzy/doc/gz_ros2_control/doc/index.html
- ros2_control mock components: https://control.ros.org/jazzy/doc/ros2_control/hardware_interface/doc/mock_components_userdoc.html
- cuRobo: https://arxiv.org/abs/2310.17274 ; https://research.nvidia.com/labs/lpr/curobov2-fast/paper.pdf
- OMPL releases and Python: https://github.com/ompl/ompl/releases ; https://pypi.org/project/ompl/ ; https://wilsonfok2020.github.io/robotics/2026/03/28/OMPL
- Ruckig: https://arxiv.org/abs/2105.04830
- Klipper SCARA discussion: https://klipper.discourse.group/t/scara-kinematic/11663
- ODrive modelling advice: https://discourse.odriverobotics.com/t/controlling-odrive-with-stm32-board-and-matlab/12090
- Cycloid lost motion and hysteresis: https://link.springer.com/article/10.1007/s12541-016-0123-8 ; https://link.springer.com/article/10.1007/s12541-017-0045-0 ; printed cycloid thesis: https://essay.utwente.nl/fileshare/file/103595/103595_Volbeda_MA_EEMCS.pdf ; harmonic drive models: https://arxiv.org/pdf/2310.15875
- Grasp sim-to-real: https://arxiv.org/pdf/2310.04517 ; IPC-GraspSim: https://arxiv.org/abs/2111.01391v2 ; Fit2Form: https://arxiv.org/pdf/2011.06498 ; gripper tips: https://goldberg.berkeley.edu/pubs/gripper-tip-surface-design-icra-2017-camera-ready.pdf ; https://arxiv.org/pdf/2606.11767
- Heat-set inserts: https://www2.mdpi.com/2504-4494/7/1/42 ; https://felix-manley-n4jm.squarespace.com/s/Threaded-Inserts-White-Paper-V1.pdf ; https://www.sculpteo.com/en/3d-learning-hub/design-guidelines/pull-out-resistance-of-threaded-inserts-testing-and-results/ ; https://www.spirol.com/assets/files/inserts-for-3d-printed-assemblies-us.pdf
- ISO 9283 summaries: https://documentation-be.hexagon.com/bundle/04_ISO9283_Basics/raw/resource/enus/04_ISO9283_Basics.pdf ; https://kavs.uniza.sk/images/PDF/Measurement_of_industrial_robot_pose_repeatability_1.pdf
- Printed arm repeatability baselines: PAROL6 https://hackaday.com/2023/08/15/hackaday-prize-2023-parol6-a-gpl-desktop-robotic-arm ; HELENE (ISO 9283, 0.87 mm) https://mdpi.com/2813-6640/3/3/7 ; Forte https://arxiv.org/html/2507.15693v1

Caveats: the MuJoCo dcmotor note's backlash mechanism could not be read (host blocked in this session), so the
deadband-hinge approach above is our own proposal; moteus/ODrive simulators were searched for and not found.
