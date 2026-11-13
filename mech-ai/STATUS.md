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

Not in the twin: any thermal behaviour (cooling, warping, adhesion, sag), pressure
advance, belt stretch, frame flex. Friction, extruder lag and stepper damping are
assumed values, so corner bulge and lag figures are indicative, not calibrated.

## Evidence that the checks work

- 36 tests. FEA matches beam theory for deflection, stress and first natural
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

## Known gaps

- No bolt preload or contact FEA; assemblies are bonded, which overstates stiffness.
- No tolerance stack-up, no fits (ISO 286), no thread engagement check.
- Kinematic trees only: no closed loops (CoreXY belts, four-bars, parallel lead screws).
- No over-constraint or binding detection; no axial retention check for bearings.
- Assemblability is straight-line and home-pose only; no sub-assemblies.
- Belt tension, tooth load and belt stretch are not modelled; belt clearance is pass/fail with no minimum gap.
- Single-sided Y drive racking, slot/tensioner travel and blind-hole thread run-out are not checked.
- No thermal, fatigue or buckling checks; FEA ignores self-weight.
- No cables, endstops or wiring.
- No manufacturing checks (printability, machinability) and no CAM output.
- Catalog is small and its ratings are not vendor data.
- One force-balance failure in the assembly FEA appeared once and did not recur in
  eight reruns; diagnostics were added to catch it if it returns.

## Suggested next steps

1. Run the published CAD-plus-FEA benchmark (Hephaestus-CCX) through this harness to
   get an outside measure.
2. Trial earthtojake's `text-to-cad` in this sandbox and decide which of its pieces to
   adopt (its viewer, DFM checks and URDF export overlap little with mechloop).
3. Bolted-joint and contact FEA for the critical joints only.
4. Sub-assemblies and multi-pose assemblability; the reported build order is valid but still not how a person would build it.
5. Extend the twin: frame and belt compliance from the FEA stiffness results, a thermal model for warping
   and cooling, input shaping, and running the twin as a verifier inside the design loop for printers.
6. Vendor datasheet ingestion for the catalog, starting with motors and rails.
