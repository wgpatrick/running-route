# mechloop

A verification loop for AI-driven mechanical design. An agent writes code-CAD
(build123d), `mechloop` runs simulation-based verifiers on it, and the agent
revises until everything passes: **CAD → verifiers → more CAD**.

![gantry simulation](docs/gantry_simulation.gif)

## What it checks

| Verifier | What it does | Engine |
|---|---|---|
| geometry | Solid validity, envelope, mass, executable requirements | OpenCASCADE |
| interference | Exact overlap volume for every part pair, required clearances, floating parts, parts that touch but are not fastened, thread engagement | OpenCASCADE |
| ratings | Force available from the actual motor and transmission, guide block loads, bill of materials | catalog data |
| motion | Collisions through full joint travel; guide run-off; belt routing; force needed for the stated speed and acceleration; forward simulation of a motion program with force-limited drives | trimesh/FCL + OpenCASCADE, MuJoCo |
| assemblability | Finds a straight-line assembly order by disassembly; checks driver access to every screw at the moment it is installed | trimesh/FCL + OpenCASCADE |
| fea | Linear static stress and deflection for parts and bonded assemblies, natural frequencies, with reaction balance, load-area and mesh-refinement checks | Gmsh + CalculiX |
| requirements | The brief's acceptance tests, evaluated last with every metric available | |

Off-the-shelf parts (steppers, MGN rails and carriages, 2020 extrusion, GT2
pulleys, lead screws, bearings, screws, corner brackets) come from a typed
catalog with mass, ratings and interfaces: `python -m mechloop catalog`.

## Use

```bash
uv venv .venv && uv pip install -p .venv -e . pytest
apt-get install -y calculix-ccx libglu1-mesa libgl1 libxrender1 libosmesa6 libegl1
.venv/bin/python -m mechloop verify examples/gantry.py     # JSON on stdout, exit 0 = all pass
.venv/bin/python -m pytest                                   # includes fault-injection tests
```

Outputs land in `out/<design>/`: `report.json`, `views.png`, `motion.gif`,
`simulation.gif`, a STEP file and `history.jsonl` (one line per loop iteration).

`AGENT.md` is the instruction file for an agent using the loop.

## Designs taken through the loop

| Design | Parts | Who designed it | What the verifiers caught along the way |
|---|---|---|---|
| `examples/motor_bracket.py` | 9 | written directly | factor of safety 1.14 and 6.5 mm deflection (fixed with gussets); later, motor screws with 1 mm of thread |
| `examples/gantry.py` | 103 | written directly, belts added by an agent | hotend crashing into the frame, screws buried under the beam, 20 unfastened parts, nozzle stiffness 40 N/mm against a 150 N/mm target, 16 screws with too little thread |
| `designs/z_axis.py` | 86 | agent, from `AGENT.md` | bed screws with 2 mm of thread; curved-face FEA selection (a harness bug, since fixed) |
| `designs/pan_tilt.py` | 41 | agent, from `AGENT.md` | none in its own runs (see caveat) |
| `designs/printer.py` | 154 | agent, not allowed to read the verifier code | tool plate too soft at the real nozzle tip; 14 short thread engagements; both axes missing belts |

![printer](docs/printer_views.png)

Caveat: the agents avoided most collisions by working out the layout by hand
before the first run, and two of them read the verifier source. Most of what
the verifiers caught, they caught after a check was added or tightened.

## Digital twin: printing on the simulated printer

`python -m mechloop print designs/printer.py examples/motor_bracket.py:bracket`
slices a part with PrusaSlicer, plans the motion the way printer firmware does
(look-ahead, per-axis limits, junction deviation), runs it on the machine's own
dynamics (axis masses from the CAD, motor torque curves, open-loop steppers that can
lose steps), lays material down where the simulated nozzle actually went, and
compares each layer with the intended part.

![bracket printing](docs/twin/bracket_printing.gif)
![printed bracket](docs/twin/bracket_printed.png)

| Run (`designs/print_runs.py`) | Result |
|---|---|
| 20 mm cube, 0.2 mm layers | passes: 15 min print, outline 99.3% match, average outline offset 0.02 mm, worst motor lag 0.04 mm |
| Motor bracket, 0.3 mm layers | passes: 43 min print, 15.6 g, outline 98.2% match, largest unsupported gap 3 mm |
| What-if: 25x acceleration, motor current at 30% | fails as it should: Y axis loses steps 26 s in, layers displaced up to 8.8 mm (`docs/twin/layer_shift_printed.png`) |

The first twin run found that the printer, which passed every static check, could
not print at all: the bed stopped 1 mm short of the nozzle, so the first layer
was unreachable. The brief had allowed that gap.

Modelled: real slicer G-code, firmware-style planning, stepper torque-angle
dynamics and step loss, gravity on the Z axis, extruder lag, bead width from
extruded volume, machine collisions over every pose of the print, bridges over
thin air. Not modelled: heat (melting, cooling, warping, bed adhesion, sag),
pressure advance, stringing, belt stretch, frame flex. Rail friction, extruder
lag and stepper damping are assumed values in `PrinterMap`.

## How much to trust a pass

`tests/test_fault_injection.py` breaks the passing gantry eleven different ways
and requires the matching verifier to catch each one. The FEA kit is checked
against beam theory in `tests/test_fea.py`. Known gaps are in `STATUS.md`; the
main ones are no contact or bolt-preload FEA, no tolerance analysis, no closed
kinematic loops, and catalog ratings that are typical class values, not vendor data.
