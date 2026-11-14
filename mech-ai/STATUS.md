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
coupler, ball bearings, socket head cap screws, hex nuts. Geometry is proxy geometry built
from datasheet dimensions; ratings are typical class values.

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

Not in the twin: any thermal behaviour (cooling, warping, adhesion, sag), pressure
advance, position-dependent stiffness. Friction, extruder lag and stepper damping are
assumed values, so corner bulge and lag figures are indicative, not calibrated.

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

63 tests pass.

## Known gaps

- No bolt preload or contact FEA; joint stiffness is a bonded/screw-only range.
- Tolerances are typical values per process; ISO 286 fit classes are not used.
- Declared adjustments are not checked against the geometry that should provide them.
- Kinematic trees only: no closed loops (CoreXY belts, four-bars, parallel lead screws).
- No axial retention check for bearings.
- Belt tension and tooth load are not modelled.
- No fatigue or buckling checks; FEA ignores self-weight. Print warping is a rule of thumb.
- Wiring is cable lengths only: no connectors, routing or strain relief.
- No CAM output.
- Catalog is small and its ratings are not vendor data.

## Suggested next steps

1. Check declared adjustments against geometry (slot length, screw travel).
2. Vendor datasheet ingestion for the catalog, starting with motors and rails (needs network access to vendor sites).
3. Run the published CAD-plus-FEA benchmark (Hephaestus-CCX) through this harness to get an outside measure.
4. Trial earthtojake's `text-to-cad` in this sandbox (its telemetry is on by default).
5. Contact and preload FEA for the few joints that set nozzle stiffness.
6. Thermal model of the print itself (warping, cooling) in the twin.
