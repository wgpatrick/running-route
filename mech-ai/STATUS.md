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
| interference | exact overlap volume per pair, required clearances, floating parts, parts that touch but are not fastened |
| ratings | drive force from the real motor torque curve and transmission, guide block loads and overhung moments, proxy parts flagged, BOM and cost |
| motion | collisions over full travel of every joint; guide blocks and nuts staying on their rails/screws; belt path length, alignment, wrap and routing clearance; force needed (MuJoCo inverse dynamics, with rotor inertia) against force available; forward simulation of a motion program with force-limited drives (tracking error, collisions along the path) |
| assemblability | an assembly order in which each part goes on in a straight line onto something already in place, parts precede the screws that hold them, and each screw has driver access when installed |
| fea | linear static stress and deflection (Gmsh + CalculiX) for single parts and bonded assemblies; natural frequencies; each run checked for force balance, load area and mesh refinement |
| requirements | the brief's acceptance tests, evaluated last with access to every metric |

A check that could not run is reported as not run and fails the design; it never counts as a pass.

Catalog (`mechloop/parts`): NEMA 17, MGN12 rail and carriage, 2020 extrusion and
corner bracket, linear rod, GT2 pulley and idler, T8 lead screw and nut, shaft
coupler, ball bearings, socket head cap screws. Geometry is proxy geometry built
from datasheet dimensions; ratings are typical class values.

## Evidence that the checks work

- 29 tests. FEA matches beam theory for deflection, stress and first natural
  frequency; bonded two-part FEA matches the one-piece result; MuJoCo forces match
  F = m·a and m·g.
- Fault injection: the passing gantry is broken eleven ways and each break is
  caught by the matching verifier.
- Designs taken through the loop:
  - Motor bracket: failed on strength (factor of safety 1.14), passed on iteration 2.
  - XY gantry (85 parts): 35 errors on iteration 1. Later verifiers added during the
    night found more in the "passing" design: 20 unfastened parts, then a nozzle
    stiffness shortfall (40 N/mm against a 150 N/mm target), fixed with ribs.
  - Z-axis bed lift and pan-tilt camera head: designed by fresh agents from `AGENT.md`.
    Both passed within three runs, but both agents had read the verifier source first.

## What the agent trials taught

1. Agents design to the verifier. Anything a verifier does not check, they do not fix,
   and they say so in their reports (unretained bearings, over-constrained lead screw,
   no belt tension adjustment, a one-piece billet yoke).
2. Findings with a named part pair, a location and a hint were acted on in one step.
   The one misleading hint (curved-face FEA selection) cost an iteration.
3. A lenient check is worse than no check: the first assembly-order check passed
   orders that installed screws before the parts they hold.

## Known gaps

- No bolt preload or contact FEA; assemblies are bonded, which overstates stiffness.
- No tolerance stack-up, no fits (ISO 286), no thread engagement check.
- Kinematic trees only: no closed loops (CoreXY belts, four-bars, parallel lead screws).
- No over-constraint or binding detection; no axial retention check for bearings.
- Assemblability is straight-line and home-pose only; no sub-assemblies.
- Belt tension, tooth load and belt stretch are not modelled.
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
4. Sub-assemblies and multi-pose assemblability.
5. Printability checks and slicer output for the printed parts.
6. Vendor datasheet ingestion for the catalog, starting with motors and rails.
