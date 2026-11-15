# mechloop status

Built overnight on 2026-11-13. This file says what exists, what the trials showed,
and what is missing. Research behind the choices is in `../reports/`.

## What exists

A Python package (`mechloop/`) with a CLI: `python -m mechloop verify <design.py>`.
A design is a Python file that returns a `Design`: build123d parts (custom and
catalog), rigid bodies and joints, fasteners and other joins, belts, load cases,
a motion program and executable requirements.

Verifiers, in the order they run:

| Verifier | Checks |
|---|---|
| geometry | valid solids, envelope, mass |
| interference | exact overlap volume per pair, required clearances, floating parts, parts that touch but are not fastened, thread engagement and blind-hole depth |
| ratings | drive force from the real motor torque curve and transmission, guide block loads and overhung moments, proxy parts flagged, BOM and cost |
| motion | collisions over full travel of every joint; guide blocks and nuts staying on their rails/screws; belt path length, alignment, wrap and routing clearance; force needed (MuJoCo inverse dynamics, with rotor inertia) against force available; forward simulation of a motion program with force-limited drives (tracking error, collisions along the path) |
| assemblability | an assembly order in which each part goes on in a straight line onto something already in place, parts precede the screws that hold them, and each screw has driver access when installed |
| fea | linear static stress and deflection (Gmsh + CalculiX) for single parts and bonded assemblies; natural frequencies; each run checked for force balance, load area and mesh refinement |
| electrical | wiring completeness, off-the-shelf check, power budget, per-wire current and voltage drop, stepper drive, heater simulation and fault injection, mains safety, loom routing; generates wiring table and Klipper config (`docs/ELECTRICAL.md`) |
| requirements | the brief's acceptance tests, evaluated last with access to every metric |

A check that could not run is reported as not run and fails the design; it never counts as a pass.

Catalog (`mechloop/parts`): NEMA 17, MGN12 rail and carriage, 2020 extrusion and
corner bracket, linear rod, GT2 pulley and idler, T8 lead screw and nut, shaft
coupler, ball bearings, socket head cap screws, hex nuts. Each part has a simple simulation solid built
from datasheet dimensions and, for most, a detailed CAD model checked against it (`docs/VENDOR_CAD.md`);
ratings are vendor data where `docs/VENDOR_DATA.md` says so, typical class values otherwise.

## Digital twin (`mechloop/twin`)

`mechloop print <printer.py> <part>` prints a part on a printer design in simulation:
PrusaSlicer G-code, firmware-style look-ahead planning, open-loop stepper dynamics
with step loss, material deposited along the simulated nozzle path, per-layer
comparison with the intended part, machine collision checks over the whole print,
and renders of the printed part and of the machine printing it. A 43-minute print
takes about 6 minutes to simulate.

Results: a calibration cube and the motor bracket both print within 0.03 mm average
outline error; a what-if with 25x acceleration and 30% motor current loses steps and
produces a visibly layer-shifted part. Its first run found that the printer could not
reach its first layer (bed 1 mm short of the nozzle), which no static check had caught.

The twin now models belt stretch (and frame flex when given FEA stiffness). An
in-simulation evaluation of the printer and of the twin itself is in `docs/EVALUATION.md`.

Not in the twin: heat in the printed part (cooling, warping, adhesion, sag), position-dependent
stiffness. Since 2026-11-15 the ringing damping, the extruder lag (by drive type and nozzle), the
melt-rate cap and the hotend's thermal model are fitted to published data, and the toolhead's tilt on
its guide blocks is in the axis model (see "Twin fitted to published data" below). Friction, the
step-loss boundary, guide-block stiffness itself, frame joints and the bed's thermal constants are
still assumed. Every fitted or assumed number, with range and source, is in
`mechloop/twin/fitted_parameters.json`.

## Evidence that the checks work

- 46 tests, 13 of them validating the twin itself. FEA matches beam theory for deflection, stress and first natural
  frequency; bonded two-part FEA matches the one-piece result; MuJoCo forces match
  F = m·a and m·g.
- Fault injection: the passing gantry is broken eleven ways and each break is
  caught by the matching verifier.
- Five designs pass the final harness (see the table in `README.md`): motor bracket,
  103-part belted XY gantry, Z-axis bed lift, pan-tilt head, and a 154-part XYZ printer
  built by an agent that was not allowed to read the verifier code.
- Each time a check was added or tightened, it found real errors in designs that had
  been passing: 20 unfastened parts, a 4x stiffness shortfall, 36 screws with too little
  thread across four designs, and two machines whose belt drives had no belts.

## What the agent trials taught

1. Agents design to the verifier. Anything a verifier does not check, they do not fix,
   and they say so in their reports (unretained bearings, over-constrained lead screw,
   no belt tension adjustment, a one-piece billet yoke).
2. Findings with a named part pair, a location and a hint were acted on in one step.
   The one misleading hint (curved-face FEA selection) cost an iteration.
3. A lenient check is worse than no check: the first assembly-order check passed
   orders that installed screws before the parts they hold.
4. Agents with an engineering brief lay most of the geometry out correctly by hand.
   The verifiers earn their keep on what is tedious to track by hand (thread depths,
   fastening, sweeps of many parts) and on physics (stiffness, drive sizing).
5. Every agent report ended with a list of things it knew were wrong and no verifier
   checked. Those lists are the best source of the next verifier to write.

## Buildability checks (added 2026-11-14)

Tolerance and fit, adjustment, binding, manufacturability, screw-only joint stiffness,
subsystems and thermal growth are now verifiers. `designs/printer_v2.py`, which passed
everything before, has 20 errors under them; `designs/printer_v3.py` was redesigned to pass
all 11 verifiers. Results, the cost in performance, and what is still not covered are in
`docs/BUILDABILITY.md`.

The intermittent wrong FEA answer was traced to multi-threaded CalculiX under concurrent
solves (about 1 wrong run in 48); the solver now runs single-threaded (200 of 200 correct).


## Vendor data, manufacturability rules and electronics (added 2026-11-14)

- Catalog motors, power supplies, control board, coupler and fastener dimensions now come from
  vendor documents (`docs/VENDOR_DATA.md`). Hiwin, Gates, Misumi and the TMC2209 chip data sheet
  could not be fetched and stay marked unverified.
- The manufacture verifier checks sheet-cut, FDM and CNC parts against 63 cited rules
  (`docs/DFM.md`), learned from text-to-cad and fabricators' guidelines.
- A new `electrical` verifier covers wiring completeness, power budget, wire and connector
  currents, stepper drive, heaters by simulation with fault injection, and off-the-shelf status
  (`docs/ELECTRICAL.md`). The generated Klipper config and wiring table for the printer are in
  `docs/electrical/`.
- `designs/printer_v4.py` (292 parts, all electronics off the shelf, no custom PCB) passes all
  12 verifiers. `designs/printer_v3.py` no longer passes: the real control board has 4 drivers
  for its 5 motors, and one belt clamp has a 0.1 mm wall. v4 fixes both.
- Firmware in the loop: real Klipper plans prints from the generated config and its step commands
  drive the twin (`docs/FIRMWARE_IN_THE_LOOP.md`). Heater control is still a port of Klipper's
  control law, not Klipper's code.
- `designs/printer_v5.py` applies the printer trade study (`../reports/Printer trade study.md`) to v4:
  4 machined, 8 sheet-cut and 12 printed parts in place of 35 machined (fabrication estimate $2,386
  to $375); a bed carrier built from a sheet plate and two 2020 arms; two guide blocks per Z rail
  (bed tilt mode 76 to 562 Hz, the `cantilever_on_guide_blocks` warning cleared); X and Y belt
  tensioners; an inductive bed probe in place of the Z switch; the extruder moved to the frame
  (Bowden), toolhead 0.60 to 0.36 kg. It passes all 12 verifiers and a firmware-in-the-loop print.
  Scored the same day as v4: resonance 68.5 / 57.2 to 88.6 / 62.2 Hz, cross-track RMS 0.015 to
  0.011 mm. It has 55 more parts, 11 minutes more assembly and a $52 dearer bill of materials.
  `docs/PRINTER_V5.md` has the evidence, what got worse and seven checker behaviours to look at.
  `viewer/` now shows v5; the v4 export is kept in `viewer_v4/`.
- `viewer/` is an interactive page for the whole design, with a replay of a simulated print
  (`tools/export_viewer.py`).

134 tests passed at that date (282 on 2026-11-15, see the last section).

- Four checker defects that v5 exposed were fixed on 2026-11-15, each with a known-answer test
  (`tests/test_known_answers.py`): a captive-nut slot is no longer read as the screw's clearance hole; the screw-only
  FEA bound decides which joints are screwed from what each screw holds, not from distance; `add_corner_bracket`
  through-bolts a non-extrusion part with a real screw and nut; the machining estimate no longer finishes the stock
  faces of a stock-thickness plate. Before and after figures are in `docs/PRINTER_V5.md` (items 1, 2, 5, 6).

## Twin fitted to published data (added 2026-11-15)

Full account: `../reports/Twin fitting.md`. Every number below, with range, source and held-out check, is in
`mechloop/twin/fitted_parameters.json`, which the twin and the heater model load.

- **Toolhead tilt on its guide blocks** is now a spring in series on the axis that carries the nozzle, derived from
  the design (block count, spacing, ball-track length, nozzle distance from the rail) with one fitted block stiffness
  (10 N/um, 7.5 to 16). On the three reference machines the toolhead-axis errors go from +42 / +18 / +70 % to
  +1 / -1 / -1 %. That comparison is not blind; each rail machine predicted from the other is +2.3 % and -1.3 %.
  The FEA nozzle-stiffness case still bonds rail and block.
- **Ringing damping** 0.065 (toolhead axis) and 0.069 (gantry or bed axis), range 0.04 to 0.12, from a mode fit of
  resonance spectra of 35 machine-axes.
- **Extruder lag** by drive type and nozzle from factory pressure-advance values: direct 0.03 s, Bowden 0.24 s at
  0.4 mm. printer_v5 (Bowden, 420 mm tube) now gets 0.235 s.
- **Melt-rate cap** per hotend class (V6 11, Revo 12 mm^3/s): the slicer is held to it and a flow-limited speed is
  reported. Neither v4 nor v5 is limited.
- **Hotend thermal model**: three nodes with a fan-dependent loss, fitted to one Ender 3's logs (held-out run within
  6 degC over 20 minutes). That hotend is too light to stand for a V6, so the default class uses the fitted structure
  with Prusa's published totals, and its sensor lag was adjusted (to 8 s) so that a simulated relay autotune cycles in
  25 s, inside the 24 to 55 s of public PID sets. The Revo class is scaled, not fitted, and has the HeaterCore's PTC
  power law. Beds are unchanged: their relay period (48 s) is inside the public range.
- **Scorecard**: `max_clean_accel_mm_s2` is now `step_loss_ceiling_accel_mm_s2` (the old key is still written) and is
  named as a ceiling. `accel_owners_would_run_mm_s2` (0.5, range 0.4 to 0.65, of Klipper's shaper smoothing rule) is
  reported beside it. Every headline number has `[low, expected, high]` under `headline` and `ranges`.
- **Re-scored** (built-in planner; before the fit in brackets): printer_v4 X 55.4 Hz, range 50 to 61 [68.4], Y 56.9
  [56.9], step-loss ceiling 8,000 mm/s^2, range 6,000 to 12,000 [8,000], an owner would run 5,300, range 3,400 to
  7,900. printer_v5 X 71.6 Hz, range 64 to 79 [88.5], Y 62.0 [62.0], ceiling 12,000, range 8,000 to 14,000 [10,000],
  an owner would run 6,800, range 4,500 to 9,500. The v4-to-v5 gain in X resonance survives the ranges; the gains in
  cross-track error and in Y do not. No verifier changed between pass and fail on either design.
- **Also added**: `[extruder]` gearing (`gear_ratio`, `full_steps_per_rotation`) from the extruder part; the Revo
  HeaterCore's PTC behaviour in the heater simulation, stuck-on fault included; a checked 5 V fan supply (regulator
  board or the board's 5 V rail); `al_mic6` / `al_atp5` in the material-keyed tables.
- **Still assumed**: belt stiffness (kept; range 15 to 27 kN per 6 mm from the blind test), friction, the step-loss
  boundary, guide-block stiffness itself, frame joints, the bed's thermal constants, everything about heat in the
  printed part.
- 229 tests pass; 13 of them were added with this work.

## Vendor CAD (added 2026-11-14)

- Catalog parts have two representations: the simulation solid and a detail model in the same frame (vendor STEP for
  the Mean Well supply and the SKR board, community STEP for motors, MGN12, 2020 extrusion and bracket, idler, T8 nut,
  fans and the endstop's lever switch, ISO-generated screws and nuts). STEP export, renders and the viewer show the
  detail; verifiers use the solid. `docs/VENDOR_CAD.md`, `vendor_cad/SOURCES.md`.
- Two new checks in the geometry verifier: `proxy_mismatch` (solid against its CAD: box, volume, holes, shafts) and
  `detail_clash` (what only the CAD has, against the neighbours). Seven catalog solids were corrected; in
  `designs/printer_v4.py` the checks found the endstop terminals shorting on three mounts and all three strikers
  missing the real lever position; v4 was fixed and passes all 12 verifiers.
- Not yet vendor CAD: motors, coupler, rails, extrusion (login or blocked hosts), pulleys, extruder, hotend, Pi,
  relay, inlet, MOSFET module. `vendor_cad/inbox/README.md` is the hand-download list; a file dropped there is
  picked up with no code change.

## Known gaps

- No bolt preload or contact FEA; joint stiffness is a bonded/screw-only range.
- Tolerances are typical values per process; ISO 286 fit classes are not used.
- Declared adjustments are not checked against the geometry that should provide them.
- Kinematic trees only: no closed loops (CoreXY belts, four-bars, parallel lead screws).
- No axial retention check for bearings.
- Belt tooth load is not modelled, nor what belt tension does to belt stiffness. (Since 2026-11-15 the pull an
  installed belt puts on a motor shaft is compared with the motor's shaft-load limit, where the catalogue has one.)
- No fatigue or buckling checks; FEA ignores self-weight. Print warping is a rule of thumb.
- Wiring is cable lengths only: no connectors, routing or strain relief.
- No CAM output.
- Catalog is small; which ratings are vendor data is listed in `docs/VENDOR_DATA.md`.

## Suggested next steps

1. Check declared adjustments against geometry (slot length, screw travel).
2. Vendor datasheet ingestion for the catalog, starting with motors and rails (needs network access to vendor sites).
3. Run the published CAD-plus-FEA benchmark (Hephaestus-CCX) through this harness to get an outside measure.
4. Trial earthtojake's `text-to-cad` in this sandbox (its telemetry is on by default).
5. Contact and preload FEA for the few joints that set nozzle stiffness.
6. Thermal model of the print itself (warping, cooling) in the twin.

## printer_v6 (added 2026-11-15)

`designs/printer_v6.py` takes v5 to a stated target: 180 x 180 x 180 mm, direct drive at 0.40 kg or less on the X
axis, parts plus fabrication at $900 or less, 320 parts or fewer, both Y belts within 1 mm of plane in 98 % of
builds, a probe that works. It passes all 12 verifiers with 8 warnings (v5: 39, and two probe errors). E3D Roto and
Revo sit on one 8 mm plate on the X guide block, whose rail moved to the rear face of the beam (nozzle 44 mm from
the block centre, v5 64 mm; 0.351 kg). The beam hangs under laser-cut Y plates, the Y belts are tied through slots
in those plates (belt-plane figure 92.8 % to 98.4 %, with no margin over the simulation's own scatter), 317 parts,
$848. Not met: the probe leaves a 32 mm strip unprobed, and the assembly estimate is 66 minutes against 65. The
hotend still has no cut-off that works without the controller. `docs/PRINTER_V6.md` has the evidence, eight
checker behaviours with reproductions, and seven decisions to confirm.


## Vendor findings applied and eight checker fixes (added 2026-11-15, later)

All sixteen proposals of `../reports/Vendor documents - what they change.md` were applied to the catalogue, the
verifiers and the twin (two as records only), and the eight checker defects listed in `docs/PRINTER_V6.md` were
fixed. Each has a known-answer test in `tests/test_known_answers_v6.py` (39 tests). 282 tests pass. `designs/` was
not edited: **printer_v4, v5 and v6 no longer pass**, and are left failing for the design work that follows.
Declarations a design can now make are in `AGENT.md` (belt tension, over-travel, print area, preload class,
sensorless homing, where a thermal cut-off sits).

What changed in the checks:

- Belt stiffness 22 -> 19 kN per 6 mm (twin). New warning: belt pull on a motor shaft against the motor's shaft-load
  limit. MGN12H rigidity and allowable rail parallelism from Hiwin by preload class; MGN12 vendor-backed, so carriage
  screws are checked against the 3.5 mm thread. Coupler bores as in the vendor STEP, with an insertion check. Endstop
  operating position 6.8 +/-1.5 mm (was 9.0), and the check uses the spread. StepperOnline's STEP files are the detail
  models of the 34 and 48 mm motors and the coupler. Details: `docs/VENDOR_DATA.md`, `docs/VENDOR_CAD.md`.
- A thermal cut-off on a hotend no longer crashes the heater check: it sits on a heat-sink side model and is
  simulated with the fan running and stopped (figures assumed). Sensorless homing writes a configuration klippy
  loads (diag pin, jumper note). Over-travel past the working range can be declared on a joint
  (`Joint.overtravel`); in a printer's Z over-travel the bed meeting the nozzle tip is not a collision, anything else
  is, and `position_min` goes negative by it. An overlap between parts is no longer taken as a joint of the tolerance
  stack-up (it made a clashing model read better). The tolerance simulation is repeatable (the size errors were drawn
  in set order, which changes from run to run) and reports the sampling error of every share. Mesh coverage uses a
  declared print area. Cable clamp distance is to the true surface, including the part's CAD model, with 3.0 mm
  allowed. The assemblability verifier honours `design.subassemblies`, and an incomplete assembly result always lists
  what was not placed and why.

What the three designs show now (full verifies, 2026-11-15, no design edits):

| | printer_v4 | printer_v5 | printer_v6 |
|---|---|---|---|
| interference | FAIL: lead screw 12.5 mm into the coupler's 8 mm bore, limit 8.6 (196 mm^3); eight Z carriage screws 4.0 mm into 3.5 mm threads | FAIL: coupler, as v4 | FAIL: coupler, as v4 |
| subsystems | FAIL: X, Y and Z endstops 3.70 mm short of the latest operating position (2.20 short of nominal) | FAIL: X and Y endstops, as v4; the two probe errors it already had (z_offset 0.10 mm) | FAIL: X and Y endstops, as v4 |
| assemblability | not run (the runner skips it while parts overlap). Run on its own: everything but the clashing lead screw and coupler is placed, 290 of 292 | same, 349 of 351 | same, 315 of 317 |
| ratings (warnings) | both Y motors: 37.4 N belt pull against 24.3 / 21.8 N allowed; the Z tilt warning is gone (75.6 -> 102.5 Hz) | 37.4 N against 25.8 / 23.0 N | 37.4 N against 25.8 N on both |
| geometry, tolerance, manufacture, motion, electrical, fea, printing, requirements | pass | pass | pass |
| twin resonance X / Y, Hz | 54.2 / 55.3 | 70.1 / 60.2 | 78.2 / 60.0 (was 80.2 / 62.0) |

Known limits of what was added: the heat-sink figures are assumed; stall detection is not simulated; the shaft-load
limit rests on one terse drawing line and exists only for the 48 mm motor; the plain assemblability check (designs
without sub-assemblies) still withdraws a screw past the whole assembly, so a part far along a screw's axis can read
as blocking it; no baseline scores were re-run at 19 kN.
