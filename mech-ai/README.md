# mechloop

A verification loop for AI-driven mechanical design. An agent writes code-CAD
(build123d), `mechloop` runs simulation-based verifiers on it, and the agent
revises until everything passes: **CAD → verifiers → more CAD**.

![gantry simulation](docs/gantry_simulation.gif)

## What it checks

| Verifier | What it does | Engine |
|---|---|---|
| geometry | Solid validity, envelope, mass, executable requirements | OpenCASCADE |
| interference | Exact overlap volume for every part pair, required clearances, floating parts, parts that touch but are not fastened | OpenCASCADE |
| ratings | Force available from the actual motor and transmission, guide block loads, bill of materials | catalog data |
| motion | Collisions through full joint travel; force needed for the stated speed and acceleration; forward simulation of a motion program with force-limited drives | trimesh/FCL + OpenCASCADE, MuJoCo |
| assemblability | Finds a straight-line assembly order by disassembly; checks driver access to every screw at the moment it is installed | trimesh/FCL + OpenCASCADE |
| fea | Linear static stress and deflection per load case, with reaction balance, load-area and mesh-refinement checks | Gmsh + CalculiX |

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

## Examples (each taken through the loop)

- `examples/motor_bracket.py` — printed bracket holding a NEMA 17 against 80 N of belt
  pull. Iteration 1 failed (factor of safety 1.14, 6.5 mm deflection); gussets and a
  thicker wall passed on iteration 2 (FoS 20, 0.13 mm, 22 g).
- `examples/gantry.py` — XY printer gantry, 85 parts, 200 × 200 mm travel. Iteration 1
  had 35 errors (hotend crashing into the frame during travel, screws buried under the
  beam, motor overlapping a carriage, an unsupported motor). It passed the first five
  verifiers on iteration 3; the fastening check added afterwards then found 20 parts
  held by nothing, fixed on iteration 4 with corner brackets and rail screws.

## How much to trust a pass

`tests/test_fault_injection.py` breaks the passing gantry eleven different ways
and requires the matching verifier to catch each one. The FEA kit is checked
against beam theory in `tests/test_fea.py`. Known gaps are listed at the end of
`AGENT.md`; the main ones are no contact/bolt FEA, no belts, no tolerance
analysis, and catalog ratings that are typical class values, not vendor data.
