# Designing with mechloop (instructions for the agent)

You design mechanical parts and assemblies by writing a Python file and running
verifiers on it in a loop. You are done only when `mechloop verify` exits 0, and
you report what was verified and what was not.

## The loop

1. Write `designs/<name>.py` defining `build() -> mechloop.Design`.
2. Run `python -m mechloop verify designs/<name>.py`. It prints JSON:
   `summary` (per-verifier pass/FAIL/skipped), `findings` (errors first, each with a
   `code`, a one-line `message`, `data` and often a `hint`), `metrics`, `artifacts`.
3. Fix the design for the **errors**, cheapest verifier first (geometry → interference
   → ratings → motion → assemblability → fea → requirements). Change the design, not the check:
   never loosen a requirement, load, range or tolerance to get a pass unless the
   brief allows it, and say so if you do.
4. Re-run. Repeat until exit code 0. Then look at `out/<name>/views.png` (and
   `simulation.gif` if there is a motion program, else `motion.gif`) to confirm it is the thing you meant to build.
5. Report: iterations taken, final key metrics, and the "not checked" list below.

Use `--only geometry interference --no-render` while roughing out geometry; run
everything (with renders) before you finish. `python -m mechloop history <name>` shows the loop so far.

## Rules that keep results honest

- Units: mm, N, MPa, kg, degrees. Shapes are in the assembled home pose, world frame.
- Put every requirement from the brief into the design as something executable:
  `envelope`, `max_mass_kg`, `LoadCase(min_fos, max_deflection)`, joint `range`,
  `Requirement(name, check)`, `program`. A requirement that is not in the file is not verified.
- Off-the-shelf parts come only from `mechloop.parts` (`python -m mechloop catalog`).
  Never invent a part number or a rating. If the catalog lacks a part, say so; you may
  add a proxy with `Stock(...)` built from datasheet dimensions and flag it as unverified.
- Never modify catalog geometry. Make the custom parts fit the catalog parts.
- Declare intent, do not rely on luck: threads/press fits via `add_screw(threads_into=...)`
  or `design.allow_overlap`; non-screw joints via `design.join(a, b, kind)`.
- Every part must be held: screws (`add_screw`) or a declared join. Touching is not fastening.
- Select FEA faces by geometry in a lambda; check `load_area_mm2` in the metrics matches
  the face you meant. For curved faces (holes, bores) use `f.geom_type.name == "CYLINDER"`
  with `f.center(CenterOf.MASS)` (the axis point); plain `f.center()` lies on the surface.
- Hand-made proxy parts (`Stock(...)` you build yourself) get an `uncatalogued_cots`
  warning. Leave it; it is true.
- A verifier that is `skipped: not run` is not a pass, and neither is an `--only` run.
- Screws need real thread engagement in what they screw into: at least 1x diameter in steel,
  1.5x in aluminium, 2x in plastic (T-nut joints exempt). Engagement is measured as the length of
  overlap, along the screw, between the screw and each `threads_into` part, so the tapped part must be
  solid there (no clearance hole). For a through-bolt use `add_screw(..., clamps=(part_a, part_b))` plus
  `add_nut(design, name, size, at, direction, screw=<screw name>)`. Screws must not exceed a catalog part's tapped depth (NEMA 17: 4.5 mm).
  Belt-driven joints need a `Belt`.
- The envelope is checked at the home pose. Collision sampling covers each joint alone over its
  travel, every corner of the joint space and random combined poses, plus the whole motion program.

## Building blocks

```python
from build123d import Box, Cylinder, Location, Pos, Rot
from mechloop import Design, Joint, LoadCase, Requirement
from mechloop.parts import place, add_screw, clearance_hole, nema17, mgn12_rail, mgn12h_carriage

def build():
    d = Design("slider", envelope=(400, 100, 100), base="rail_beam")
    d.add("plate", Pos(0, 0, 15) * Box(40, 40, 4), material="al6061", body="carriage")
    place(d, "rail", mgn12_rail(300), Location((0, 0, 0)))               # catalog part, fixed
    place(d, "block", mgn12h_carriage(), Location((0, 0, 0)), body="carriage", guides="x")
    add_screw(d, "s0", "M3", 6, at=(10, 10, 17), body="carriage", threads_into="block")
    d.joints.append(Joint("x", "slide", "world", "carriage", (1, 0, 0), range=(-100, 100),
                          max_speed=200, max_accel=3000,
                          drive={"motor": "motor", "kind": "belt", "pulley": "drive_pulley"}))  # + a Belt
    d.program = [{"to": {"x": 100}}, {"to": {"x": -100}}, {"to": {"x": 0}}]
    d.loadcases.append(LoadCase("payload", "plate",
        fixed=lambda f: abs(f.center().Z - 13) < 1e-6,
        loaded=lambda f: abs(f.center().Z - 17) < 1e-6,
        force=(0, 0, -20), min_fos=3, max_deflection=0.1))
    return d
```

- `body=` names the rigid body a part rides on; `Joint(name, "slide"|"hinge", parent, child, axis, origin, range)`
  connects bodies in a tree rooted at `"world"`. Ranges are relative to the home pose (0).
- `drive=` ties a joint to a real motor and transmission (`belt`, `leadscrew`, `direct`);
  available force is computed from the motor's torque curve at the stated speed.
  Drive dicts: `{"motor": name or [names], "kind": "belt", "pulley": <pulley part>}`,
  `{"kind": "leadscrew", "screw": <lead screw part>}` (lead and efficiency come from the part),
  `{"kind": "direct", "ratio": 3, "efficiency": 0.9}` for a hinge through a reduction.
  `Joint(min_drive_margin=1.5)` is the required available/required ratio; rotor inertia is included.
- `guides="<joint>"` on carriage blocks, nuts and bearings: loads and overhung moments are checked
  against ratings, and blocks/nuts must stay on their rail/screw over the whole travel.
- `Requirement(name, check)`: `check(design)` or `check(design, metrics)` returns `(ok, detail)`;
  `metrics[verifier]` is that verifier's metrics from this run, e.g.
  `metrics["motion"]["drives"]["x"]["margin"]`.
- More checks: `ModalCase(name, component, fixed, min_frequency_hz)` in `design.modalcases`;
  `AssemblyCase(name, components, fixed=[(part, pred)], loaded=(part, pred), force, probe, max_deflection)`
  in `design.assemblycases` meshes several touching parts as one bonded body.
- Belts: `design.belts.append(Belt(name, path, axis=(0, 0, 1), stock_length=None))`. `path` lists the route
  in order: `("pulley", part_name, "ccw"|"cw")` for catalog `gt2_pulley`/`gt2_idler` parts (wrap sense by the
  right-hand rule about `axis`: "ccw" is counter-clockwise when you look from the tip of the axis vector
  back at the pulley), and `("anchor", body, (x, y, z))` where a belt end is clamped (home-pose world point
  on that body). Open belt = anchor ... anchor; closed loop = pulleys only. The motion verifier checks that
  the path length stays constant over the travel, pulleys are coplanar, the drive pulley has enough teeth
  engaged, a closed loop matches `stock_length`, and no straight run passes through a part. Pulley centre
  heights are in `part.meta["interfaces"]["belt_center"]`. A belt-driven joint without a `Belt` is not
  checked for routing; add one.
- Composing: `design.include(other_design, Location(...), prefix="z_")` brings a whole sub-assembly in
  (parts, bodies, joints, fasteners, joins, belts), moved and renamed. Its requirements, program and (when
  moved) load cases are not copied; restate them.
- Orienting catalog parts: `Location((x, y, z), (rx, ry, rz))` (degrees) or
  `Location(Plane(origin=..., x_dir=..., z_dir=...))`. Each catalog function's docstring gives its
  local frame; `part.meta["interfaces"]` holds its hole positions in world coordinates after `place`.
- Other helpers: `add_corner_bracket`, `design.bom_extra(sku, qty, cost)`, `design.tool_point`,
  `belt_length(teeth_a, teeth_b, center)`, program steps `{"to": {...}, "speed": v}` / `{"to": {}, "dwell": s}`.
- `add_screw(design, name, size, length, at=<underside of head>, direction=<thread direction>,
  threads_into=..., tnut=False)` adds the screw, its driver-access check and the joint.

## Printers: the digital twin and the improvement loop

A printer design declares how to print on it:

```python
d.tool_point = ("xbody", nozzle_tip_xyz)
d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
             "stiffness": {"x": "<AssemblyCase giving nozzle stiffness in X>", "y": "<... in Y>"},
             "speeds": {"perimeter": 45, "infill": 60, "travel": 150}}   # mm/s the machine is meant to print at
```

Then `mechloop verify` also runs the **printing** verifier: the digital twin prints a short test
cube on the machine (real slicer G-code, firmware-style planning, stepper motors that can lose
steps, belts that stretch, the frame flexing by the stiffness your own FEA cases report) and fails
the design if the print is wrong, the machine collides, or the bed cannot reach the nozzle (the gap
at the end of Z travel must be <= the first layer height).

Passing is the floor. To make a design **better**, use the scorecard:

    python -m mechloop score designs/<printer>.py        # about a minute; appends to out/<name>/scores.jsonl

| Score | Meaning | Direction |
|---|---|---|
| `max_clean_accel_mm_s2`, `accel_margin` | highest acceleration (at 2x speed) that still prints cleanly; margin is relative to the joints' own `max_accel` | up |
| `resonance_hz` | frequency the toolhead rings at on each axis | up |
| `cross_track_rms_mm`, `cross_track_worst_mm` | how far the nozzle strays sideways from the commanded path at nominal settings (vibration that shows on the part) | down |
| `benchmark_time_s` | time to print three benchmark parts at the design's own `speeds` and joint acceleration limits | down |
| `moving_mass_kg`, `total_mass_kg`, `bom_cost_usd` | from the CAD and BOM | down |
| `frame_stiffness_n_per_mm` | nozzle stiffness from your AssemblyCases | up |

The improvement loop: score the baseline; pick the weakest number; make ONE real design change
(geometry, a catalog part, a transmission, a joint limit); run `mechloop verify` (everything must
still pass) and `mechloop score`; keep the change only if the score improved and nothing you care
about got worse; otherwise revert. Log every attempt, including the reverted ones.
Scores near the step-loss boundary are noisy: do not count a change of one acceleration step as real.
The twin has no thermal model, and friction, extruder lag, damping and belt stiffness are assumed
values, so prefer changes that are robust in kind (less mass, more stiffness, more torque margin).
`python -m mechloop print <printer.py> <design.py>:<part>` prints any part and renders the result.

## Building it: the assembly simulation

    python -m mechloop assemble designs/<name>.py     # writes out/<name>/BUILD.md and build.gif

simulates building the design at a bench. It finds an order in which every part has a way in
(a straight move, or two straight moves), parts go on before their screws, and each screw can be
reached. Then for every step it asks what a person would face: if you let go of the part, does it
stay (or fall, tip or slide), which way does it go in, which tool. The assembly may be turned onto
any of its six sides between steps, and the turning schedule is chosen to minimise holding.

Metrics (all better lower; also in `mechloop score` under `assembly`): `estimated_time_min` (rough
allowances, for comparing designs), `needs_holding` (parts that must be held or clamped until
fastened), `from_below`, `times_assembly_is_turned`, `two_move_paths`, `fasteners`,
`fastener_types`, `tool_changes`. `trapped` parts cannot be installed at all.

Design levers: add a ledge, pocket, pin or tab so a part locates and rests before it is screwed;
put fasteners on one side; reduce screw sizes to one or two; make bench sub-assemblies with
`design.subassemblies["name"] = [part names]` (the group is built separately and installed as one
unit); split or open up a part that traps another.

## What each verifier tells you

| Verifier | Checks | Typical fix |
|---|---|---|
| geometry | valid solids, envelope, mass, your `Requirement`s | repair the CAD, slim or shrink |
| interference | overlaps, required gaps, floating parts, unfastened parts | move, pocket, add screws/joins |
| ratings | drive force from the real motor, guide loads, BOM and cost | change motor, ratio, speed |
| motion | collisions through full joint travel, guide run-off, belt routing, force needed vs available (with rotor inertia), forward simulation of `program` (tracking, collisions on the path) | shorten travel, move parts, lower accel |
| assemblability | a build order exists in which each part goes on in a straight line onto something already there, parts go on before the screws that hold them, and every screw has driver access when it is installed (home pose only) | split parts, add access holes, reorder |
| requirements | your `Requirement`s, evaluated last with all metrics | fix the design |
| fea | factor of safety and deflection per load case, with force balance and refinement checks | ribs, fillets, thicker sections, material |

## Not checked (say this in your report)

Bolt preload and contact, fatigue, buckling, thermal effects, belt tension and tooth
load, cable routing, tolerance stack-up, over-constraint and binding, axial
retention of bearings, closed kinematic loops, curved insertion paths, cables,
manufacturing cost and process limits. FEA is linear static with idealised
fixtures and no self-weight; assemblies are bonded, which overstates stiffness.
Guide moments are estimates. Catalog ratings are typical values.
