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
range (the Z axis also needs that much extra travel), and say in a comment how it is set. The
verifier reports how much adjustment each one needs (`*_needed_mm_99`) against what you declared.

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
  `endstop_switch()`; something on the other body must reach the switch's trigger point at that end of
  travel (`part.meta["interfaces"]["trigger"]`: the lever's operating position at its tip, 9 mm to one side of
  the switch centre). The seat needs a clearance hole at each of `interfaces["pin_holes"]` (the terminals stand
  2.6 mm out of the board). Or `{"joint": "x", "sensorless": True}`.
- Cables: `d.cables.append(Cable("toolhead loom", ("xbody", clamp_xyz), ("world", clamp_xyz), length=450))`.
  Every moving body that carries something electrical needs one; its length is checked over the travel.
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
  relay ahead of the supply). Every motor needs a `run_current`. Mains needs an inlet with fuse, and earth wires to
  the supply and to an `earth_point` on the frame.
- Limits live in `mechloop.electrical.DEFAULT_REQUIREMENTS`; override one in `el.requirements` only if the brief
  allows, and say so.
- The motor torque curve used by ratings, motion and the twin comes from the electrical model once
  `design.electrical` exists (winding R and L, driver current, supply voltage). Lowering a run current lowers force.
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
| assemblability | a build order exists in which each part goes on in a straight line onto something already there, parts go on before the screws that hold them, and every screw has driver access when it is installed (home pose only) | split parts, add access holes, reorder |
| tolerance | fits, stack-ups and binding over thousands of imperfect builds; adjustment needed against adjustment provided | open clearances, add adjustment, locate from one part |
| manufacture | each custom part against its process (sheet, printed, machined), with the limit and its source on every finding | radius corners, stock thickness, move holes off edges and bends, split blocks, re-orient prints |
| subsystems | homing, cables, extruder, cooling, electronics | add the parts and declare them |
| electrical | devices wired and off the shelf, power budget, wires and connectors, stepper torque at speed, heaters and their faults by simulation, mains safety, looms in the CAD | bigger supply or gauge, external MOSFET module, lower run current, thermal fuse / relay, re-route |
| requirements | your `Requirement`s, evaluated last with all metrics | fix the design |
| fea | factor of safety and deflection per load case, with force balance and refinement checks | ribs, fillets, thicker sections, material |

## Not checked (say this in your report)

Bolt preload and contact (stiffness is bracketed, not predicted), fatigue, buckling, the
thermal behaviour of a part while it prints (warping is a rule of thumb only), belt tension
and tooth load, cable paths (only lengths), tolerance stack-up, over-constraint and binding, axial
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
