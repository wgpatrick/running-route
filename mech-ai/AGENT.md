# Designing with mechloop (instructions for the agent)

You design mechanical parts and assemblies by writing a Python file and running
verifiers on it in a loop. You are done only when `mechloop verify` exits 0, and
you report what was verified and what was not.

## The loop

1. Write `designs/<name>.py` defining `build() -> mechloop.Design`.
2. Run `python -m mechloop verify designs/<name>.py`. It prints JSON:
   `summary` (per-verifier pass/FAIL/skipped), `findings` (errors first, each with a
   `code`, a one-line `message`, `data` and often a `hint`), `metrics`, `artifacts`.
   `--out` is the ROOT folder (default `out`): files go to `<out>/<design name>/`. Leave it at the default, or pass
   the same root to `verify`, `score`, `tune` and `assemble`. `--out out/<name>` nests to `out/<name>/<name>/` (verify
   warns on stderr), and `score`, `tune` and `print` then do not find the report: `tune` says so on stderr and under
   `warnings`, naming the file it looked for, and its figures then rest on belt stiffness only.
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
- Catalog parts carry a detailed CAD model (`component.detail`, kind in `component.meta["model"]`: vendor CAD,
  community CAD, generated to standard, or proxy) next to the simple solid the verifiers use. The geometry verifier
  reports `proxy_mismatch` (a catalog solid disagrees with its CAD: fix the catalog, not the design) and
  `detail_clash` (a connector, lever, terminal or pin that only the CAD has runs into one of your parts: move or
  turn the part, or cut a relief). See `docs/VENDOR_CAD.md`; missing models are listed in `vendor_cad/inbox/README.md`.
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
- `mgn12h_carriage(preload="Z0" | "Z1" | "ZF")`: Hiwin's preload class of the block you will buy. It sets the block's
  radial rigidity (63 N/um at Z0, 81 at Z1; none is published for the clearance class ZF, which falls back to an
  assumed 40) and how far out of parallel two rails may be (9 um at ZF / Z0, 5 um at Z1). Left out, Z0 is assumed and
  the metrics say "assumed". The carriage's M3 threads are 3.5 mm deep (Hiwin): a screw that goes deeper is
  `thread_bottoms_out`.
- `shaft_coupler(5, 8)`: its bores are short. A shaft may enter `interfaces["max_insertion_a"]` (5 mm side, 12.05 mm)
  or `["max_insertion_b"]` (8 mm side, 8.6 mm) before it meets the elastomer spider; the hub clamps 7.5 mm. Deeper is
  an `interference` and a `shaft_too_deep_in_coupler` error with the excess.
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
- Belt tension: `Belt(..., tension=<N per span>)` is the installation tension the tensioner is set to. Left out, it is
  Gates' minimum recommended installation tension for the width (6.2 / 9.3 / 14.2 / 18.7 N for 4 / 6 / 9 / 12 mm).
  The ratings verifier works out the pull on every pulley that sits on a motor shaft (two spans: 2 x tension for a half
  turn of wrap) and compares it with the motor's radial shaft-load limit, carried to the belt plane (`nema17(48)`:
  21 N at 20 mm from the face, read from one terse drawing line; the other motors have no figure and are not judged).
  Over the limit is a warning, `motor_shaft_radial_load`, with the numbers. Remedies: an outboard support bearing on
  the shaft end (a catalog `bearing()` on the motor's axis beyond the pulley, declared with
  `Belt(..., outboard_support=("<pulley part>",))`), the pulley closer to the motor face, a lower tension (say so if
  it is below Gates' minimum), or a motor with a higher limit. 12 mm belt and 5 mm-bore 20-tooth pulleys are generic
  parts, not Gates stock (the BOM source text says so).
- Over-travel: `Joint(..., range=(lo, hi), overtravel=(past_lo, past_hi))`. `range` is the WORKING range (programs,
  prints, firmware coordinates); the joint can physically move `overtravel` mm further at each end
  (`joint.mechanical_range`). Collisions, guide run-off, belts, cables and endstops are checked over the mechanical
  range. For a printer's Z joint, end the working range where the bed meets the nozzle plane and declare what the bed
  can rise beyond it as over-travel; the generated `position_min` is negative by that amount, which is what a probe's
  z_offset and a bed mesh need. Do not extend `range` past the nozzle plane. That over-travel is not a motion in which
  the bed passes through the nozzle: it is allowance for where the nozzle really ends up relative to the bed in a built
  machine. So in it (a) the bed meeting the part that carries the nozzle tip is not a collision; (b) everything else
  on the nozzle's body (probe, fan duct, the toolhead's screws) rides with the nozzle, and is checked with the bed at
  nozzle contact plus that part's **toolhead margin**, not through the whole over-travel; (c) every other pair (bed
  against gantry or frame) is checked through the whole over-travel. The toolhead margin of a part
  (`mechloop.tolerance.toolhead.height_margin`) is the stack-up inside the toolhead between the part and the nozzle
  tip (the tolerance simulation run on the nozzle's body alone, 99.7th percentile; 0.5 mm or more, assumed, for screws
  and for parts not tied to the nozzle part by touching or joined toolhead parts) plus how much higher the bed can
  stand under the part than under the nozzle (plate flatness as a bow, 0.381 mm for cast plate and assumed for any
  other, plus the levelling residual). A toolhead part that hangs below the nozzle tip, or less than its margin above
  it over the bed, is a `motion_collision` naming the margin. Typical margins: 0.3 to 0.6 mm for a machined or bought
  part bolted straight to the hotend's carrier, 0.8 to 1.1 mm for something on a printed arm 30 to 40 mm away.
  Z over-travel no longer has to stay below a probe's face height.
- Composing: `design.include(other_design, Location(...), prefix="z_")` brings a whole sub-assembly in
  (parts, bodies, joints, fasteners, joins, belts), moved and renamed. Its requirements, program and (when
  moved) load cases are not copied; restate them.
- Orienting catalog parts: `Location((x, y, z), (rx, ry, rz))` (degrees) or
  `Location(Plane(origin=..., x_dir=..., z_dir=...))`. Each catalog function's docstring gives its
  local frame; `part.meta["interfaces"]` holds its hole positions in world coordinates after `place`.
- `add_corner_bracket(design, name, a, b, corner, u, v)`: a leg on a 2020 extrusion takes a T-nut (BOM only). A leg on
  anything else (a plate, a printed part) is through-bolted with a real M5 screw `<name>_screw` and nut `<name>_nut`,
  which are checked like any other fastener: draw the M5 clearance hole 11.5 mm from the corner (`screw_offset=`).
- Other helpers: `design.bom_extra(sku, qty, cost)`, `design.tool_point`,
  `belt_length(teeth_a, teeth_b, center)`, program steps `{"to": {...}, "speed": v}` / `{"to": {}, "dwell": s}`.
- `add_screw(design, name, size, length, at=<underside of head>, direction=<thread direction>,
  threads_into=..., tnut=False)` adds the screw, its driver-access check and the joint.

## Printers: the digital twin and the improvement loop

A printer design declares how to print on it:

```python
d.tool_point = ("xbody", nozzle_tip_xyz)
d.printer = {"bed": "bed", "x": "x", "y": "y", "z": "z",
             "stiffness": {"x": "<AssemblyCase giving nozzle stiffness in X>", "y": "<... in Y>"},
             "speeds": {"perimeter": 45, "infill": 60, "travel": 150},   # mm/s the machine is meant to print at
             "extruder": "bowden"}                                       # only if the extruder is on the frame; default: direct drive
```

What the twin takes from the design besides masses, motors and belts:

- **Extruder lag** from the drive type: direct drive 0.03 s, Bowden about 0.24 s at a 0.4 mm nozzle (factory
  pressure-advance values), scaled with the Bowden tube's length (a `Cable` whose name contains "bowden", or
  `printer["bowden_length"]`) and the nozzle size (`printer["nozzle"]`).
- **Melt-rate cap** from the hotend's class (the part on the tool body whose SKU starts with `HOTEND`): V6 class
  11 mm^3/s, Revo 12. The slicer is held to it. If a speed you asked for needs more, the print is slowed and the
  report says so (`flow_limited` warning, `melt_rate` in the scorecard): that speed is then not real.
- **The toolhead turning on its guide blocks**: the axis whose body carries the nozzle gets a spring between belt
  clamp and nozzle, from the number of blocks with `guides=` on that joint, their spacing along the rail and the
  nozzle's distance from the rail. One block with the nozzle 60 mm away is about 200 N/mm, softer than the belts; two
  blocks 40 mm apart are more than ten times stiffer. Your FEA nozzle-stiffness case does not contain this (it bonds
  block and rail), so both are used, in series.

Then `mechloop verify` also runs the **printing** verifier: the digital twin prints a short test
cube on the machine (real slicer G-code, firmware-style planning, stepper motors that can lose
steps, belts that stretch, the frame flexing by the stiffness your own FEA cases report) and fails
the design if the print is wrong, the machine collides, or the bed cannot reach the nozzle (the gap
at the end of Z travel must be <= the first layer height).

Passing is the floor. To make a design **better**, use the scorecard:

    python -m mechloop score designs/<printer>.py        # a few minutes; appends to out/<name>/scores.jsonl

| Score | Meaning | Direction |
|---|---|---|
| `accel_owners_would_run_mm_s2` | the acceleration an owner would run with input shaping: 0.5 (0.4 to 0.65) x Klipper's shaper smoothing rule at the lower of the two resonances, calibrated on three real machines. This is the usable acceleration figure | up |
| `step_loss_ceiling_accel_mm_s2`, `accel_margin` | the acceleration (at 2x speed) at which the simulated motors first lose steps. A ceiling, not an acceleration to run: on three real machines it sat 6 to 8 times above what their owners set. Old name, still written: `max_clean_accel_mm_s2`. Margin is relative to the joints' own `max_accel` | up |
| `resonance_hz` | frequency the toolhead rings at on each axis | up |
| `cross_track_rms_mm`, `cross_track_worst_mm` | how far the nozzle strays sideways from the commanded path at nominal settings (vibration that shows on the part) | down |
| `benchmark_time_s` | time to print three benchmark parts at the design's own `speeds` and joint acceleration limits | down |
| `moving_mass_kg`, `total_mass_kg`, `bom_cost_usd` | from the CAD and BOM | down |
| `frame_stiffness_n_per_mm` | nozzle stiffness from your AssemblyCases | up |

The improvement loop: score the baseline; pick the weakest number; make ONE real design change
(geometry, a catalog part, a transmission, a joint limit); run `mechloop verify` (everything must
still pass) and `mechloop score`; keep the change only if the score improved and nothing you care
about got worse; otherwise revert. Log every attempt, including the reverted ones.
Every headline number comes with a range: `headline.<score>.range` (and `ranges.<score>`) is
`[low, expected, high]` under the ranges of the twin's fitted parameters (belt stiffness, toolhead block
stiffness, ringing damping, extruder lag; `mechloop/twin/fitted_parameters.json`). A change that moves a score
by less than the width of its range is not shown to be an improvement; say so when you report it.
Scores near the step-loss boundary are noisy: do not count a change of one acceleration step as real.
Resonance is believable to about +/-15 % (blind test on three machines for gantry and bed axes; the toolhead
axis rests on a term fitted to two of them). Damping, extruder lag and the melt-rate cap are fitted to published
data; friction, the step-loss boundary, guide-block stiffness and frame joints are still assumed, and the twin has
no model of heat in the part (warping, cooling). So prefer changes that are robust in kind (less mass, more
stiffness, a second guide block, more torque margin).
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

What a bench sub-assembly does to `estimated_time_min`: its parts and screws are costed like any others, its first
part is free (it is laid on the bench, whichever way up suits the steps that follow: that is not a turn), and the
finished unit costs 12 s to carry over and locate against 6 s for a single part, plus holding and direction like any
part. So a sub-assembly adds about 6 s unless the bench makes its steps cheaper (parts that rest instead of being
held, nothing from below, no turn of the whole machine). Declaring one for parts that would be held either way raises
the estimate slightly; that is the model, not an error. Turning a sub-assembly over is costed like turning the
machine (25 s), which is high for a unit that fits in a hand. `mechloop assemble` and `mechloop score --assembly` run
the same simulation and give the same figures.

The assemblability verifier honours the same declaration: with `design.subassemblies` set, each group is checked as
built on the bench (its screws need driver access among its own parts only) and then as one unit going straight into
the main assembly. A result that is not complete lists every unit that was not placed and why, in the main assembly
and inside each sub-assembly (`not_placed`, in the verifier's metrics and in `mechloop assemble`).

## Will it fit when it is really made? Tolerances, adjustment, binding

The **tolerance** verifier builds the machine thousands of times with every part made only as
accurately as its process allows, and every joint seated with the play its screws allow.
Processes are assigned automatically (catalog parts: purchased; 2020 extrusion: saw-cut; plastics:
printed; other custom parts: machined) or set with `component.meta["process"]` =
"printed" | "machined" | "sheet" | "extrusion" | "purchased".

It checks: every screw pattern can be started at once (printed holes come out about 0.15 mm
small); every shaft has real clearance or real interference in its bore (a shaft drawn at its bore
size fits half the time; say which you mean with `design.join(a, b, "press")`, otherwise it is
taken as a sliding fit); belts stay in plane; two rails guiding one axis stay parallel; a lead
screw stays in line with its rails (or it side-loads the nut); and, for a printer, the nozzle
still meets the bed and the bed is level under it.

Real machines absorb error with adjustment. Declare what the design provides:

```python
from mechloop import Adjustment
d.adjustments += [
    Adjustment("z endstop screw", "z_offset", range_mm=3.0),          # sets the nozzle-to-bed gap
    Adjustment("bed levelling screws", "bed_level", range_mm=2.0),    # +/- travel at each corner
    Adjustment("y rail set to the plate", "rail_align", range_mm=0.3, joint="y"),
    Adjustment("floating nut", "float", range_mm=0.5, joint="z"),
]
```

An adjustment must be real: model the slot, spring, jack screw or oversize hole that provides the
range (the Z axis also needs that much extra travel: declare it as `overtravel` on the Z joint), and say in a comment
how it is set. The verifier reports how much adjustment each one needs (`*_needed_mm_99`) against what you declared.

The simulation is repeatable: fixed seed, fixed order of draws, so an identical run gives identical numbers. Every
percentage comes with its sampling error (`..._standard_error`, sqrt(p(1-p)/builds), about 0.3 % at 97 % over 3000
builds), and a result within two standard errors of the limit it is judged against is flagged
(`within_sampling_error_of_the_limit`): do not claim a margin smaller than that. Parts that overlap in the model
(without `allow_overlap` or a `join`) are a clash, not a seat: they are left out of the stack-up and listed
(`clash_in_stackup`), so a clash can never improve a figure. The two-rail figure is judged against the maker's
allowable (Hiwin MG_12: 9 um, 5 um at preload Z1); cast-plate beds get the maker's stock flatness beside the bed
figures as a reference (0.381 mm for plate up to 12.7 mm thick).

## Can each part be made? (the manufacture verifier)

Every custom part is checked against the process that makes it. Say how each part is made:

```python
d.add("tray", shape, material="al5052", process="sheet")       # laser / waterjet cut, optionally bent
d.add("mount", shape, material="al6061", process="machined")   # 3-axis CNC (round parts: lathe)
d.add("duct", shape, material="petg", process="printed",       # FDM
      meta={"print_up": "+Z"})                                 # pin the print orientation (else the best of six is chosen)
d.manufacturing = {"shop": "sendcutsend",                      # that shop's stock, sizes and bend tooling ("generic" by default)
                   "sheet": {"method": "laser"},               # or "waterjet", "router"
                   "printer": {"build_volume": (256, 256, 256), "nozzle": 0.4},
                   "limits": {"fdm.bridge_max_mm": 60}}        # your own machine's or shop's number for any rule id
```

Left unsaid, plastics (pla, petg, abs, nylon_pa12) are printed and everything else is machined. One part can
override with `meta={"dfm": {"limits": {...}, "method": "waterjet", "shop": "sendcutsend"}}`. Rule ids, limits and
their sources are in `mechloop/verifiers/dfm_rules.py` and `docs/DFM.md`. Every finding carries `part`, `at` (x, y, z),
`value`, `limit`, `rule`, `source` and a `hint`. Errors cannot be made as drawn; warnings can, for money or at a risk.

- **sheet** (2D cut): one thickness cut straight through (a pocket, counterbore or step is an error), stocked thickness,
  hole size against thickness and cutter, material between holes and to the edge, thin tabs and narrow slots, inside
  corners against the cutter (a laser's are practically sharp; a router leaves 1.6 mm), part size, grilles more than half
  cut away, countersinks and tapped holes as second operations. Bent parts: model each bend with an inside radius r and
  an outside radius r + t (two boxes meeting sharp is an error); flange length, bend radius and hole-to-bend distance are
  checked; use al5052 or steel (6061 cracks). A full run writes each flat profile to `out/<name>/dxf/<part>.dxf`.
- **printed**: orientation (reported with all six scored), overhang area past 45 degrees less what bridges or sits in a
  small horizontal hole, long bridges, horizontal holes over 10 mm, walls under two beads, small holes and pins, first-layer
  contact and tall-thin parts, build volume, plastic around threads (heat-set insert guidance), a load case pulling
  along the build direction, and a rule-of-thumb warp warning.
- **machined**: plate (stock thickness), block or turned; sharp inside corners no cutter can reach (error) or only from the
  side (warning); corner radius against depth; deep or narrow slots; thin walls and floors; hole depth and non-standard
  drill sizes; the threads your screws need (depth, blind run-out); surface no straight cutter reaches from six sides
  (undercuts, error); set-ups; stock size, share machined away, and a rough time and cost (an estimate, for comparing
  alternatives). Prefer flat plates from stock; a block needing four or more set-ups, or mostly machined away, is usually
  better as two or three plates bolted together. Give pocket corners a radius of at least 1.5 mm, a third of the depth if
  you can.

## Everything else a machine needs (the subsystems verifier)

- Homing: `d.endstops.append({"joint": "x", "switch": "<endstop part>", "at": "min"})` with a catalog
  `endstop_switch()`. `part.meta["interfaces"]["trigger"]` is the lever's NOMINAL operating position at its tip (9 mm
  to one side of the switch centre, 6.8 mm from the switch's mounting-hole line: Y = 8.4 in the part frame; it was
  10.6 until 2026-11-15, which was the lever's free position). Unit to unit the operating position is anywhere
  within +/-1.5 mm of that, so at the end of the joint's mechanical travel the striker must have pushed the lever to
  `interfaces["trigger_latest"]` (1.5 mm further in, Y = 6.9), or `endstop_not_reached` says how far short it is; and
  it must stop before `interfaces["case_limit"]` (Y = 6.65, 0.25 mm further), or `endstop_overtravel`. A unit at the
  early end switches up to 3 mm before the end of travel: the axis homes there, so allow for that at the far end.
  Either place the switch so the end of `range` is at `trigger_latest`, or put the nominal trigger at the end of
  `range` and declare 1.5 mm of `overtravel` on the joint if the axis really has it. The seat needs a clearance hole
  at each of `interfaces["pin_holes"]` (the terminals stand 2.6 mm out of the board; that row is the generated carrier
  board's, not a bought module's: re-check it when the module is known). Buy the gold-contact low-current switch
  (OMRON D2F-01L type) for a logic-level input.
- Sensorless homing: `{"joint": "x", "sensorless": True}` (X or Y on a belt). The generated printer.cfg gets the
  TMC2209 virtual endstop, `diag_pin`, a starting `driver_SGTHRS` (tune it on the machine; override with
  `el.firmware["sensorless"] = {"x": {"sgthrs": 90}}`), `homing_retract_dist: 0` and half a motor turn per second, and
  klippy loads it. On the SKR Mini E3 V3.0 the driver's DIAG output reaches the MCU only through a jumper on the
  board's X-DIAG / Y-DIAG header and shares the axis's endstop pin, so leave that endstop connector empty
  (`sensorless_pin_shared` otherwise). Stall detection itself is not simulated.
  A bed probe that homes Z is declared the same way: `d.endstops.append({"joint": "z", "probe": "<probe part>", "at": "max"})`.
  **Catalogue bed probes** (OMRON E2E inductive sensors, maker's data sheet; `mechloop/parts/probes.py`):
  `probe_omron_e2e(model, clamp=(z_lo, z_hi))`. Local frame: sensing face on Z=0 looking down, barrel up +Z.

  | model | thread, hole | kind | on iron | on aluminium (chart reading) | electrical |
  |---|---|---|---|---|---|
  | `"E2E-X5ME1"` (default) | M12, 12.5 mm | unshielded | 5 mm | 1.6 mm | NPN three-wire |
  | `"E2E-X10ME1"` | M18, 18.5 mm | unshielded | 10 mm | 3.0 mm (3.0 to 3.3) | NPN three-wire |
  | `"E2E-X5E1"` | M18, 18.5 mm | **shielded** | 5 mm | 1.75 mm | NPN three-wire |
  | `"E2E-X8MD1"` | M12, 12.5 mm | unshielded | 8 mm | 2.8 mm (2.8 to 3.2) | **DC two-wire** |

  (In OMRON's code M = unshielded: the E2E-X5ME1 is unshielded. The shielded M12 three-wire type senses only about
  0.6 mm on aluminium and is not offered.) Every distance is +/-10 % unit to unit and a further +/-10 % with
  temperature up to 70 degC (+/-15 % over the three-wire types' whole range to 85 degC: used when the sensor is
  estimated to pass 70 degC, see "Heat" below); the probe checks use both, so place the sensing face so that the SHORT
  end still switches before the nozzle touches (`z_offset_range_mm` in the metrics; e.g. E2E-X10ME1: 3.0 x 0.8 =
  2.4 mm). Aluminium figures are read from a chart for small 1 mm plates,
  repeatability (0.01 mm) is assumed, the mass (30 g M12, 70 g M18) is estimated: all said on the part.
  - **How high the face may sit.** The probe rides with the nozzle, so Z over-travel does not bring the bed to it (see
    "Over-travel"). What separates face and nozzle tip is local: the probe's toolhead margin M
    (`homing.z.probe_to_nozzle_margin` in the subsystems metrics: stack-up between face and tip, plus bed flatness
    over the distance between them). The face must be at least M above the tip (`probe_face_below_nozzle_margin`,
    error: in some builds the face meets the bed before the nozzle), and the short end should still switch with the
    nozzle M above the bed (`probe_trigger_margin_thin`, warning; at or below 0 it is the error `probe_trigger_margin`).
    So the face belongs between M and (short end - M) above the tip: `face_window_mm`. With M about 1.0 mm (printed
    arm, 35 to 40 mm from the nozzle): E2E-X10ME1 on aluminium 1.0 to 1.4 mm; E2E-X5ME1 on aluminium (short end
    1.28 mm) has no such window: 1.0 to 1.28 mm passes with the warning; on a steel bed (5 mm, short end 4.0)
    1.0 to 3.0 mm. Below 1 mm the curled-edge warning also applies. A shorter, stiffer mount closer to the nozzle
    lowers M. Setting the sensor's height on the built machine with its nuts removes the stack-up part in practice;
    the checks do not model that, so say it in your report if you rely on it.
  - **Mounting.** The sensor is clamped in a plate or tab by its own two nuts (4 mm each, 17 mm across flats on M12,
    24 mm on M18): `clamp=(z_lo, z_hi)` are the plate's two faces above the sensing face; the plate needs the
    clearance hole from the table; `d.join(probe, plate, "clamped by its two nuts")`. The thread runs 7 to 40 mm
    (M12 unshielded), 10 to 48 mm (M18 unshielded) or 0 to 38 mm (M18 shielded) above the face.
    For a **closed hole** make the nuts their own parts, which is how the sensor is really fitted (one nut off, barrel
    through the hole, nut back on): `place(d, "bed_probe", probe_omron_e2e(model, clamp=..., nuts="separate"), ...)`
    then `add_probe_nuts(d, "bed_probe")` (adds `bed_probe_nut_front` and `bed_probe_nut_rear`, catalogue parts
    `e2e_nut`, joined to the probe; two more parts in the count, no cost). With the default `nuts="fused"` the nuts are
    part of the sensor's solid: it can only slide sideways into an open fork, and a closed hole is `trapped_part`.
    `probe_not_clamped` looks at the circle the nut bears on, at mid-thickness of the plate: at least 75 % of it must
    have material of parts on the probe's body under it. Material of several parts counts together (a fork closed by
    a key is a full ring; an open fork the width of the hole is about 67 % and fails), and the answer does not depend
    on how the round sensor is turned about its axis.
  - **Unshielded** sensors need metal kept away from the head: the face must stand `l` mm proud of any metal and a
    cylinder `d` mm in diameter round the head must hold no metal (M12: l 15, d 40; M18: l 22, d 55;
    `interfaces["mounting"]`). Any metal part of the toolhead in that zone (the tab itself, the heater block, the
    extruder, screws) is `probe_metal_in_clear_zone`, with each part's distance. So: a metal tab at `z_lo >= l` and at
    least d/2 from other metal, or a printed (plastic) bracket, which may be anywhere. A **shielded** sensor may sit
    flush in metal, at the price of range.
  - **Electrical.** `device_from(el, d, "<probe>")`, wire its `out` port to an endstop input, and declare its supply:
    `el.devices[name].params.update(supply_v=24.0, supply_from="...")` (10 to 30 V). Three-wire NPN types pull their
    output up to the supply inside the sensor, so a 3.3 V input needs a BAT85-class diode in the signal lead, cathode
    to the sensor: `params["series_diode"] = True` and `d.bom_extra("DIODE-BAT85", 1, 0.1)`; without it,
    `probe_signal_over_voltage`. The **two-wire** E2E-X8MD1 is a switch in series with a load (at least 3 mA, 3 V
    left across it when on, 0.8 mA leakage when off): straight on a logic input it is `probe_two_wire_needs_interface`.
    It is accepted only with an off-the-shelf interface stage placed in the design and declared,
    `params["interface"] = {"part": "<part>", "load_ohm": R, "on_current_ma_min": I, "off_current_ma_max": I}`; the
    catalogue has no such module, so prefer a three-wire type.
  - **Heat.** `probe_near_hot_bed` (electrical verifier, warning) no longer compares the bed's temperature with the
    sensor's ambient rating directly. The sensor's own temperature is estimated as a range
    (`mechloop.electrical.probe_temperature_estimate`: heat in through the face across the air gap, out from the barrel
    to air between room temperature and the film temperature (bed + room) / 2; textbook values, not validated) and the
    HIGH end plus 10 K must stay under the rating: 85 degC for the three-wire types, 70 degC for the two-wire
    E2E-X8MD1 (OMRON's sheet). An M18 sensor 2 mm above an 85 degC bed is estimated at 35 to 60 degC; over 100 degC,
    38 to 69. Where the estimate cannot be made, the bed temperature itself must be 10 K under the rating.
  - No touch (microswitch) probe is in the catalogue: the only switch data is OMRON's D2F sheet, and a bare switch
    needs a deploy mechanism for which no off-the-shelf module has vendor data. A hand-made probe stays possible as
    before (below) and is flagged `uncatalogued_cots`.
  The probe part rides on the toolhead, has a `sensing_face` interface (centre of the face that looks at the bed) and
  an electrical template of kind `probe` (`mechloop.parts.electrical.inductive_probe_template(...)`). The verifier
  checks that it switches before the nozzle touches for every unit within the sensing-distance spread, that Z travel
  brings the bed within range, and reports the strip of bed it cannot reach. See `designs/printer_v5.py`.
- Cables: `d.cables.append(Cable("toolhead loom", ("xbody", clamp_xyz), ("world", clamp_xyz), length=450))`.
  Every moving body that carries something electrical needs one; its length is checked over the travel. Each clamp
  point must be within 3.0 mm of the surface of a part on its body (true distance to the surface, measured to the
  part's CAD model where it has one; `cable_clamp_in_air` gives the distance and the nearest part).
- Print area: `d.printer["print_area"] = (x, y)` in mm, centred on the bed plate. The bed-mesh coverage check then
  judges the probe against that area, not against the whole XY travel (travel added so the probe can reach is not
  print area); a declared area the nozzle cannot reach is `print_area_not_reachable`.
- A printer also needs an extruder (`extruder_direct()` on the toolhead, or
  `design.printer["extruder"] = "bowden"`), a `fan(30)` on the toolhead, a `control_board()` and a
  `psu_24v()` on the frame, and enough stepper drivers for its motors.

## Electrical (the electrical verifier; details in docs/ELECTRICAL.md)

Declare the electrical system in `design.electrical` (see `build_electrical` in `designs/printer_v4.py`):

```python
from mechloop.electrical import Bay, Electrical, Waypoint
from mechloop.parts.electrical import device_from, add_electrical_bom, skr_mini_e3_v3, psu_lrs   # python -m mechloop catalog

place(d, "control_board", skr_mini_e3_v3(), Location(...))        # electrical catalog parts are placed like any other
el = d.electrical = Electrical(supply_v=24.0, mains_v=(115.0, 230.0))
device_from(el, d, "control_board")                               # one Device per placed part: ports, ratings, sources, product
device_from(el, d, "y_motor_l", connection="parallel")            # motors sharing a driver say how they are joined
el.loom("toolhead", [Waypoint("xbody", xyz, clamp="extruder"),    # waypoints ride on bodies; a change of body is a flexing
                     Waypoint("world", xyz, clamp="frame_top_back"), ("world", xyz)], flex_length={0: 420.0})   # span
el.wire("hotend heater", "control_board.E0", "hotend_heater.in", 20, insulation="silicone",
        via=["tray", "drop", "toolhead"], pigtail=(150.0, "fiberglass"))     # from port, to port, AWG, looms in order
el.firmware = {"kind": "klipper", "steppers": {"x": {"run_current": 0.28}, ...},
               "heaters": {"extruder": {"heater": "hotend_heater", "sensor": "hotend_thermistor", "max_temp": 280,
                                        "targets": [250.0], "verify_heater": {}}, ...}, "fans": {...}}
el.hot_parts = {"bed": 100.0}; el.bay = Bay(devices=[...], enclosed=False, vent_area_m2=0.02, height_m=0.05)
el.sync_cables(d); add_electrical_bom(el, d)                      # flexing spans -> the cable check; wire -> the BOM
```

- Use only electrical catalog parts (stock boards, modules, components). A device whose `product` record says
  `custom_pcb` or not `off_the_shelf` is an error; if the board cannot carry a load, add a stock module
  (`mosfet_module`, `relay_btt_v12`), never a custom board.
- Every heater needs a thermistor, a firmware entry and an independent cut-off (thermal fuse in series, and/or a
  relay ahead of the supply). A `thermal_fuse` sits thermally where its device says: `device_from(el, d, "<tco>",
  node=...)`, by default the plate of a bed heater and the HEAT SINK of a hotend (`node="heat_sink"`; `"block"` is the
  alternative). A cut-off on the heat sink follows the sink, which stays near 45 degC while its fan runs: the heater
  check simulates the heater stuck on with the fan running and with it stopped and reports both
  (`cutoff_on_heat_sink_needs_fan_failure` when it opens only once the fan has stopped: it then guards against heat
  creep, not against a stuck-on heater). The heat-sink figures are assumed; override them with
  `device_from(..., heat_sink={"fan_on_w_k": ..., "fan_off_w_k": ..., "capacity_j_k": ...})`. Every motor needs a `run_current`. Mains needs an inlet with fuse, and earth wires to
  the supply and to an `earth_point` on the frame.
- Limits live in `mechloop.electrical.DEFAULT_REQUIREMENTS`; override one in `el.requirements` only if the brief
  allows, and say so.
- The motor torque curve used by ratings, motion and the twin comes from the electrical model once
  `design.electrical` exists (winding R and L, driver current, supply voltage). Lowering a run current lowers force.
- The mains relay `relay_btt_v12()` has three mains terminals, `LIN`, `N`, `LOT`. It switches the live only and powers
  itself from the mains, so its `N` must be wired or it never pulls in (`device_supply_not_connected`): run the
  neutral through it, `el.wire("N inlet-relay", "inlet.N", "psu_relay.N", 18, ...)` and
  `el.wire("N relay-supply", "psu_relay.N", "psu.N", 18, ...)` (the terminal takes both wires in one twin ferrule).
  Any catalogue device may name ports that need a supply (`params["required_supply_ports"]`); the same check covers them.
- Fans carry their rated voltage: `fan(30)` and `fan(40)` are 24 V; `fan(30, 12)` is the Sunon MF30101V2-1000U-A99
  (12 V, 6 to 13.8 V, 32 mA; maker's sheet). The 24 V 30 mm fan's sheet is not in hand: its 0.05 A is a typical figure.
  Every fan's rated voltage is compared with what its port supplies.
- A fan gets the voltage it is made for (`fan_voltage_mismatch` otherwise). For a 5 V fan on a 24 V machine (the E3D
  Roto's heat-sink fan) either put a stock regulator board in line, `mechloop.electrical.add_regulator(el, d, "fan_reg",
  "<its CAD part>", out_v=5.0, max_a=..., efficiency=...)`, wired board fan output -> `fan_reg.in`, `fan_reg.out` -> fan; or run it
  from the board's +5 V pins, `add_board_5v_port(el, "control_board")` then wire `control_board.5V` -> fan (it then runs
  whenever the machine is on, and is added to the host's draw in the board's 5 V budget: SKR Mini E3 V3.0 1.1 A fuse,
  80 % limit, Pi Zero 2 W 0.6 A). A fan made with `embedded_device(..., port_kind="fan")` is found by its port kind.
- An extruder part that states its gearing (`extruder_roto`: 26.8937 mm per turn of the hobb, 11.262:1, 400 full steps)
  is written to `[extruder]` with `gear_ratio` and `full_steps_per_rotation`: leave `rotation_distance` out of the
  firmware block's `steppers["extruder"]` (or give the part's own value). A different `rotation_distance` there is taken
  as complete and written alone.
- A PTC heater (`hotend_revo`: `params["ptc"]`) is simulated with its resistance rising with temperature: 40 W cold,
  27 W at 250 degC, self-limiting near 485 degC if its MOSFET fails shorted (it limits; it does not switch off, so the
  cut-off rules apply as for any heater). The melt-capacity margin uses the hot power and the part fan at full speed.
- Hotend thermal constants are no longer the part's estimates: a cartridge in a block is the V6 class, a HeaterCore the
  Revo class (`mechloop/twin/fitted_parameters.json`: `hotend_thermal`). `params["thermal_model"] = "catalog"` on the
  heater device brings the part's own figures back.
- Outputs: `out/<name>/electrical/printer.cfg`, `wiring.csv`, `wiring.md`, `pin_map.json`.
- Not checked: EMC, firmware bugs, crimp quality, the short stubs between loom ends and connectors (length only),
  I2t of fuses, the real heater's tolerance and the real PID tune.

## Heat and real joints (in the fea verifier)

- `ThermalCase(name, components, fixed=[(part, pred)], temps={"bed": 60.0}, probes={"nozzle": xyz, "bed": xyz},
  gaps={"nozzle gap": ("nozzle", "bed", "z", 0.05)}, flatness=("bed", "z", 0.1))` in `design.thermalcases`
  heats parts by the given rise in kelvin and reports how probe points move, how gaps change and how
  much a part bows. A heated bed should be fixed at one point and free to grow at the others.
- Every `AssemblyCase` is solved twice: every touching face bonded (`stiffness_n_per_mm`, the upper
  bound) and screwed joints held only around their screws (`stiffness_low_n_per_mm`, the lower bound).
  Deflection limits are judged on the lower bound, and the digital twin uses it.

## What each verifier tells you

| Verifier | Checks | Typical fix |
|---|---|---|
| geometry | valid solids, envelope, mass, your `Requirement`s; catalog solids against their vendor CAD, and what that CAD adds (connectors, levers, pins) against your parts | repair the CAD, slim or shrink; move, turn or relieve around the vendor part |
| interference | overlaps, required gaps, floating parts, unfastened parts | move, pocket, add screws/joins |
| ratings | drive force from the real motor, guide loads, BOM and cost | change motor, ratio, speed |
| motion | collisions through full joint travel, guide run-off, belt routing, force needed vs available (with rotor inertia), forward simulation of `program` (tracking, collisions on the path) | shorten travel, move parts, lower accel |
| assemblability | a build order exists in which each part (or declared bench sub-assembly) goes on in a straight line onto something already there, parts go on before the screws that hold them, and every screw has driver access when it is installed (home pose only) | split parts, add access holes, reorder, declare a sub-assembly |
| tolerance | fits, stack-ups and binding over thousands of imperfect builds; adjustment needed against adjustment provided | open clearances, add adjustment, locate from one part |
| manufacture | each custom part against its process (sheet, printed, machined), with the limit and its source on every finding | radius corners, stock thickness, move holes off edges and bends, split blocks, re-orient prints |
| subsystems | homing, cables, extruder, cooling, electronics | add the parts and declare them |
| electrical | devices wired and off the shelf, power budget, wires and connectors, stepper torque at speed, heaters and their faults by simulation, mains safety, looms in the CAD | bigger supply or gauge, external MOSFET module, lower run current, thermal fuse / relay, re-route |
| requirements | your `Requirement`s, evaluated last with all metrics | fix the design |
| fea | factor of safety and deflection per load case, with force balance and refinement checks | ribs, fillets, thicker sections, material |

## Not checked (say this in your report)

Bolt preload and contact (stiffness is bracketed, not predicted), fatigue, buckling, the
thermal behaviour of a part while it prints (warping is a rule of thumb only), belt tooth load and what belt
tension does to belt stiffness (only the pull on a motor shaft is checked), stall detection in sensorless homing,
cable paths (only lengths), tolerance stack-up, over-constraint and binding, axial
retention of bearings, closed kinematic loops, curved insertion paths, cables,
real manufacturing cost (the estimate is rough) and tolerances a process can hold on a feature. FEA is linear static with idealised
fixtures and no self-weight; assemblies are bonded, which overstates stiffness.
Guide moments are estimates. Catalog ratings are typical values.

## Firmware in the loop

`python -m mechloop print <printer.py> <design.py>:<part> --firmware klipper` plans the print with real Klipper
from the design's generated printer.cfg (needs `tools/setup_klipper.sh` once). Treat anything Klipper refuses
(`firmware_rejected_move`, `firmware_error`) as a design or configuration error. Add `--trajectory` to save the
nozzle path, then `python tools/export_viewer.py <printer.py> --no-assembly --print <print folder>` to replay it
in `viewer/`. See `docs/FIRMWARE_IN_THE_LOOP.md` for what is and is not real.
