# Design for manufacture: what the manufacture verifier checks, and where its numbers come from

`mechloop verify` runs the **manufacture** verifier on every custom part. Each part is checked against
the process that makes it: cut in 2D from sheet (`sheet`), FDM printed (`printed`) or CNC machined
(`machined`). This document records what was learned from the open-source project text-to-cad and from
fabricators' published design guides, the rule table with its sources, what the checks found on the
existing designs, and what is still not checked.

Code: `mechloop/verifiers/manufacture.py` (entry point), `dfm_rules.py` (the numbers), `dfm_geom.py`
(measurement), `dfm_sheet.py`, `dfm_print.py`, `dfm_cnc.py`. Tests: `tests/test_manufacture.py`
(one failing and one passing part per rule; the file runs in about 7 seconds).

## Declaring how a part is made

```python
d.add("tray", shape, material="al5052", process="sheet")
d.add("duct", shape, material="petg", process="printed", meta={"print_up": "+Z"})
d.manufacturing = {"shop": "sendcutsend", "sheet": {"method": "laser"},
                   "printer": {"build_volume": (256, 256, 256), "nozzle": 0.4},
                   "limits": {"fdm.bridge_max_mm": 60}}
```

- `process=` on a part (stored in `meta["process"]`, so `meta={"process": ...}` still works): `sheet`,
  `printed`, `machined`, `extrusion`, `purchased`; `laser`, `waterjet`, `fdm`, `cnc` and a few more are
  accepted as aliases. Unstated: plastics are printed, everything else machined. Catalog parts are never checked.
- `design.manufacturing["shop"]`: `generic` (common metric stock, general guide limits) or `sendcutsend`
  (their inch-gauge stock, per-thickness part sizes, bend radii and flange minimums; their limits are errors).
- `design.manufacturing["limits"]` or `meta["dfm"]["limits"]` on one part: replace any rule's limit by id.
  A finding judged against an override says `source: design override`. An unknown rule id, shop, process or
  orientation is reported as `bad_manufacturing_declaration`, never ignored.

Every finding carries `part`, `at` (world x, y, z; up to six places, worst first), `value`, `limit`, `unit`,
`rule`, `source` and `hint`. An error means the process cannot make the feature as drawn. A warning means it
can, for money (a second operation, another set-up, support material, special tooling) or at a risk.
A part whose check crashes is reported as `part_not_checked` (an error): unmeasured is not a pass.

## What was learned from text-to-cad

Project: https://github.com/earthtojake/text-to-cad (MIT licence). It was read, not run or installed.
No code was copied; the ideas below were reimplemented against this codebase's `Design` model.

Where its DFM lives:

| File | What it holds |
|---|---|
| `packages/cad/src/cad/_internal/dfm/rules.py` | the `Rule` / `RuleSet` / `Source` model: one limit on one measured field, cited |
| `packages/cad/src/cad/_internal/dfm/sheet.py`, `cnc.py`, `printing.py`, `molding.py` | one rule table per process |
| `packages/cad/src/cad/build123d/_dfm_sheet.py`, `_dfm_cnc*.py`, `_dfm_printing.py`, `_dfm_dxf.py`, `_dfm_brep.py`, `_flatten.py` | the measurements on exact B-rep geometry, the unfold, the DXF cut-file check |
| `packages/cad/src/cad/_internal/manufacturing.py` | the entry point and the ok / failed / not_checked states |
| `skills/cad/references/manufacturing-{review,sheet-metal,cnc,printing}.md` | how a designer is told to design for and read each check |
| `skills/sendcutsend/SKILL.md`, `references/official-sources.md` | a shop-specific preflight against SendCutSend's published specs |

Adopted:

- **Measurement and judgement are separate.** Measure facts from geometry, then compare with a table of rules,
  each with a published source; where no guide states a number, say the number is our own. (`dfm_rules.py`.)
- **Findings as data**: `rule`, `value`, `limit`, `source`, location, so nothing has to be parsed from a message.
- **General practice apart from a shop's limits**, and the designer's own numbers override both.
- **Unmeasured is never a pass** (`part_not_checked`). mechloop already held this view for verifiers.
- **Sheet**: one thickness with square edges or it is not sheet; a bend is an inside and an outside cylinder
  one thickness apart, and two boxes meeting sharp are an error (`sharp_bend`); flange height 2t + r from the outside
  of the bend; hole 2t from the bend's tangent line, t from an edge, holes 2t apart; webs and slots at least t and wider
  than the kerf; the 25.4 mm "this is plate, not sheet" floor; a standard 5 x 10 ft sheet as the default size limit;
  radius past 10t is rolled, not bent.
- **CNC**: judge the part in its own frame, not the world's; a square inside corner is makeable when a square end
  mill can reach it end-on from some side, and is then one more set-up rather than an error; a floor-to-wall root may
  stay sharp; corner depth against the tool that fits it (4:1 warning, 30:1 error); pocket depth to width; wall minimums
  for metal and plastic; hole depth 40:1 limit; standard drill series; thread length 1.5 to 3 diameters; line-of-sight
  reach from six directions with a 2% tolerance; set-ups as the fewest directions that reach everything.
- **FDM**: 45 degree overhang; walls of two beads of the nozzle; horizontal round holes up to 10 mm excused (its own
  figure); bridges and cantilevers treated differently from slopes; orientation candidates ranked by support, height and
  bed contact; warp-prone materials.
- **Flat pattern as DXF**, in millimetres with `$INSUNITS` set, on a named cut layer.

Not adopted, and why:

- **Unfolding bent parts** (its `unfold` with K-factor tables and bend allowance). Substantial, and a production
  blank needs the shop's own K-factor anyway. Bent parts are judged but no DXF is written for them.
- **Bend reliefs, hems, joggles, curls, notch/tab length-to-width**, and the DXF cut-file linter (open contours,
  duplicate curves). Our DXF is generated from a valid solid's face, so the linter's cases do not arise.
- **Injection moulding, SLA / SLS / MJF / metal PBF, turning rules** (grooves, live tooling). Out of scope; a part
  that is a plain body of revolution is recognised as turned and gets holes, walls, bar stock and slenderness only.
- **Special-cutter classification** (T-slot, dovetail, keyseat, slitting saw, engraving, ball-mill creases). Here an
  undercut is simply an error with a hint.
- **Exact rays on the B-rep and per-face refs.** We cast rays on a sampled mesh (about 2000 points per part): fast
  (well under a second a part) and located by x, y, z, at the cost of missing features smaller than the sample
  spacing (see limitations).
- **Knife edges, trapped volumes, stair-stepping, support volume, clearance between printed parts.**
- Its micro-tool reach interpolation and other own-floor refinements.

## Fabricators' guides read (2026-11-14)

| Source | Used for |
|---|---|
| https://sendcutsend.com/guidelines/laser-cutting/ | hole at least 50% of thickness (laser), 0.070 in (waterjet), 0.125 in (router); inside radius per method; 50% material removal; full-depth cuts only |
| https://sendcutsend.com/materials/min-max/ | stocked thicknesses and min/max part size per material and thickness (6061, 5052, mild steel, 304, brass) |
| https://sendcutsend.com/materials/processing-min-max/ | bend radius, max bend length, min flange per material and thickness; 6061 absent from bending; tap sizes per thickness |
| https://sendcutsend.com/guidelines/bending/ , /tapping/ , /countersinking/ | no custom bend radii; tapping from 0.059 in; countersinking from 0.125 in |
| https://www.hubs.com/guides/sheet-metal-fabrication/ | 0.5-10 mm laser, 0.5-6 mm bending; 0.3 mm kerf; hole >= t; holes 2t apart, t from edge, 2t from bend; bend radius >= t |
| https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ | cavity depth 4x width, 30:1 feasible; corner radius 1/3 depth; walls 0.8/0.5 mm metal, 1.5/1.0 plastic; hole depth 4/10/40 x; standard drills; thread length; tools down to 2.5 mm; undercuts |
| https://www.protolabs.com/services/cnc-machining/cnc-milling/design-guidelines/ | threads M2 to M12; inside corners radiused |
| https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/ | 45 degree overhang; bridges under 5 mm clean; elephant's foot; pins under 5 mm weak; layer-direction weakness |
| https://www.hubs.com/3d-printing/fdm/ , /knowledge-base/3d-printing-geometry-restrictions/ , /dfm-tips-for-3d-printed-parts-with-thin-walls/ | walls 0.8 mm; min feature and hole 2.0 mm; typical build sizes |
| https://www.hubs.com/knowledge-base/how-assemble-3d-printed-parts-threaded-fasteners/ | wall around a thread equals the screw diameter; inserts |

Not reachable or not usable: cdn.sendcutsend.com (the per-SKU specs JSON text-to-cad's skill uses; blocked by the
proxy), so per-material minimum hole and bridge values are the general "50% of thickness" rule, not SendCutSend's
per-SKU figures; xometry.com answered 429, so Xometry numbers appear only where text-to-cad cites them.

## The rule table

Generated from `dfm_rules.py` (`rule_table_markdown()`); override any limit by its id.

| Rule | Limit | Severity | What | Source |
|---|---|---|---|---|
| `sheet.hole_min_t_ratio` | 0.5 x thickness | error | smallest hole or cut-out, laser. Laser cutting: holes and cut-outs at least 50% of material thickness; smaller ones distort, char or fail to cut | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.hole_recommended_t_ratio` | 1 x thickness | warning | hole diameter. Specify hole diameters larger than the sheet thickness; smaller is possible but may deform or be inaccurate | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.hole_min_waterjet_mm` | 1.78 mm | error | smallest hole or cut-out, waterjet. no less than 0.070 in for most waterjet cut parts | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.hole_min_router_mm` | 3.175 mm | error | smallest hole or cut-out, CNC router. 0.125 in, the bit diameter | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.hole_to_edge_t_ratio` | 1 x thickness | warning | material between a hole and the edge. Holes should be at least the sheet's thickness from the edge | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.hole_spacing_t_ratio` | 2 x thickness | warning | material between two holes. Space holes at least 2 times the sheet thickness apart | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.feature_width_t_ratio` | 1 x thickness | warning | width of a slot, tab or neck. text-to-cad applies Hubs's hole-to-edge minimum and Protolabs' notch/tab minimum (the thickness) to any web or slot | text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py |
| `sheet.kerf_laser_mm` | 0.3 mm | error | laser kerf. laser cutting produces the lowest kerf at 0.3 mm on average; a slot narrower than the kerf cannot be cut | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.kerf_waterjet_mm` | 0.8 mm | error | waterjet stream. 0.032 in stream diameter (Hubs gives 0.5-1 mm) | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.kerf_router_mm` | 3.175 mm | error | router bit. 0.125 in bit | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.inside_radius_laser_mm` | 0.15 mm | warning | inside corner radius, laser. approximately the kerf width (very small): a drawn-sharp corner comes out practically sharp | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.inside_radius_waterjet_mm` | 0.81 mm | warning | inside corner radius, waterjet. 0.032 in | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.inside_radius_router_mm` | 1.6 mm | warning | inside corner radius, CNC router. 0.063 in, the radius of a 0.125 in bit; use dog-bones where a square part must seat | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.thickness_min_mm` | 0.5 mm | warning | sheet thickness. recommended range 0.5-10 mm for laser cutting | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.thickness_max_laser_mm` | 10 mm | warning | sheet thickness. recommended range 0.5-10 mm for laser cutting | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.thickness_limit_mm` | 25.4 mm | error | sheet thickness. text-to-cad's own floor: sheet lasers stop near an inch of steel; thicker plate is machined | text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py |
| `sheet.max_long_mm` | 3048 mm | warning | flat part's long side. a standard 5 x 10 ft sheet, the largest standard blank (text-to-cad, citing Xometry) | text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py |
| `sheet.max_short_mm` | 1524 mm | warning | flat part's short side. a standard 5 x 10 ft sheet | text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py |
| `sheet.min_long_mm` | 9.5 mm | warning | flat part's long side. SendCutSend's smallest laser part in thin stock is 0.25 x 0.375 in; smaller parts fall through the bed or need tabs | https://sendcutsend.com/materials/min-max/ |
| `sheet.min_short_mm` | 6.35 mm | warning | flat part's short side. 0.25 in | https://sendcutsend.com/materials/min-max/ |
| `sheet.removed_max_fraction` | 0.5 fraction | warning | share of the blank cut away inside the outline. keep material removal under 50% (said of routed parts: grilles shift or break while being cut) | https://sendcutsend.com/guidelines/laser-cutting/ |
| `sheet.countersink_min_thickness_mm` | 3.18 mm | warning | thickness of a countersunk sheet. materials must be at least 0.125 in thick for countersinking | https://sendcutsend.com/guidelines/countersinking/ |
| `sheet.tap_min_thickness_mm` | 1.5 mm | warning | thickness of a tapped sheet. tapping offered from 0.059 in thick | https://sendcutsend.com/guidelines/tapping/ |
| `sheet.bend_radius_t_ratio` | 1 x thickness | warning | inside bend radius. Keep the interior bend radii at least as large as the material thickness | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.bend_thickness_max_mm` | 6 mm | warning | thickness of a bent sheet. 0.5-6 mm recommended for bending | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.flange_min_t_ratio` | 2 x thickness (plus the inside radius) | error | flange height from the outside of the bend. minimum bend height 2 t + r (Hubs's figure as text-to-cad reads it, from the outside mould line) | text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py |
| `sheet.hole_to_bend_t_ratio` | 2 x thickness | warning | hole edge to the start of the bend radius. Ensure holes are at least 2 times the sheet thickness from the start of the bend radius, or they distort | https://www.hubs.com/guides/sheet-metal-fabrication/ |
| `sheet.bend_radius_max_t_ratio` | 10 x thickness | warning | inside bend radius. text-to-cad's own line: a radius past 10 t is bump-formed or rolled, not one hit of the brake | text-to-cad: packages/cad/src/cad/_internal/dfm/sheet.py |
| `fdm.overhang_angle_deg` | 45 deg from vertical | warning | overhang angle. an overhang can usually be printed up to 45 deg; above that support is required | https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/ |
| `fdm.support_area_mm2` | 150 mm2 | warning | area needing support in the chosen orientation. below this the support is a few minutes of clean-up; above it, it costs material, time and surface finish | mechloop's own figure: no published guide read here states one |
| `fdm.bridge_clean_mm` | 5 mm | info | bridge span. sagging or marks are always present to some extent unless the bridge is less than 5 mm | https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/ |
| `fdm.bridge_max_mm` | 30 mm | warning | bridge span printed without support. a desktop printer with part cooling bridges a few tens of mm with visible sag; set your printer's figure | mechloop's own figure: no published guide read here states one |
| `fdm.horizontal_hole_max_mm` | 10 mm | warning | diameter of a horizontal round hole. text-to-cad's own figure: up to 10 mm a horizontal hole prints unsupported; wider, its crown sags | text-to-cad: packages/cad/src/cad/_internal/dfm/printing.py |
| `fdm.wall_min_mm` | 0.8 mm | error | wall thickness. FDM minimum wall 0.8 mm supported and free (two beads of a 0.4 mm nozzle) | https://www.hubs.com/knowledge-base/dfm-tips-for-3d-printed-parts-with-thin-walls/ |
| `fdm.wall_beads` | 2 x nozzle | error | wall thickness. text-to-cad's scaling of Hubs's 0.8 mm: two beads of the nozzle actually fitted | text-to-cad: packages/cad/src/cad/_internal/dfm/printing.py |
| `fdm.feature_min_mm` | 2 mm | warning | pin or boss diameter. minimum feature size 2.0 mm recommended; pins under 5 mm are perimeters only and snap off | https://www.hubs.com/3d-printing/fdm/ |
| `fdm.hole_min_mm` | 2 mm | warning | hole diameter. minimum hole diameter 2.0 mm recommended; holes print undersize, drill critical ones after printing | https://www.hubs.com/3d-printing/fdm/ |
| `fdm.slenderness_max` | 6 height / sqrt(bed contact area) | warning | height over footprint. tall parts on a small footprint wobble under the nozzle or come off the bed | mechloop's own figure: no published guide read here states one |
| `fdm.bed_contact_min_fraction` | 0.1 fraction of the part's shadow | warning | first-layer contact area. a part that touches the bed on a small share of its outline needs a brim, a raft or support to stay put | mechloop's own figure: no published guide read here states one |
| `fdm.thread_wall_d_ratio` | 1 x screw diameter | warning | wall around a threaded hole or insert. the minimum wall thickness around a thread should match the diameter of the fastener (M5: 5 mm) | https://www.hubs.com/knowledge-base/how-assemble-3d-printed-parts-threaded-fasteners/ |
| `fdm.layer_load_fraction` | 0.5 share of the load along the build direction | warning | load pulling layers apart. FDM parts are inherently weaker in one direction due to layer orientation; the share that triggers this is mechloop's own | https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/ |
| `cnc.corner_radius_min_mm` | 1.25 mm | warning | inside corner radius. most shops machine with tools down to 2.5 mm diameter; below that is micro-machining | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.corner_depth_ratio` | 4 depth / tool diameter | warning | corner depth over the tool that fits it. end mills have a cutting length of typically 3-4 times their diameter; recommended corner radius is 1/3 of cavity depth | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.corner_depth_limit` | 30 depth / tool diameter | error | corner depth over the tool that fits it. a tool diameter to cavity depth ratio of up to 30:1 is possible using specialised tooling | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.pocket_depth_ratio` | 4 depth / width | warning | pocket or slot depth over its width. recommended cavity depth: 4 times cavity width | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.pocket_depth_limit` | 30 depth / width | error | pocket or slot depth over its width. 30:1 with specialised tooling | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.slot_min_mm` | 2.5 mm | warning | slot or gap width. tools down to 2.5 mm are standard | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.wall_min_metal_mm` | 0.5 mm | error | wall thickness. feasible: 0.5 mm (metals) | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.wall_recommended_metal_mm` | 0.8 mm | warning | wall thickness. recommended: 0.8 mm (metals) | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.wall_min_plastic_mm` | 1 mm | error | wall thickness. feasible: 1.0 mm (plastics) | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.wall_recommended_plastic_mm` | 1.5 mm | warning | wall thickness. recommended: 1.5 mm (plastics) | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.hole_depth_ratio` | 10 depth / diameter | warning | hole depth over diameter. recommended 4, typical 10; deeper needs specialised drills | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.hole_depth_limit` | 40 depth / diameter | error | hole depth over diameter. feasible: 40 times nominal diameter | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.hole_min_mm` | 1 mm | warning | hole diameter. feasible: any diameter larger than 1 mm; smaller is micro-drilling | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.drill_tolerance_mm` | 0.005 mm | warning | distance from the nearest standard drill. Hubs: use a standard drill bit size; text-to-cad's tolerance for 'is that drill' | text-to-cad: packages/cad/src/cad/build123d/_dfm_cnc_holes.py |
| `cnc.drill_max_mm` | 13 mm | info | largest hole judged as drilled. jobber drills in 0.1 mm steps stop near 13 mm; larger holes are milled or bored, any diameter | mechloop's own figure: no published guide read here states one |
| `cnc.thread_depth_ratio` | 3 x diameter | warning | thread length over diameter. threads longer than 3 times the nominal diameter are unnecessary | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.thread_min_mm` | 2 mm | warning | thread size. taps cut threads down to M2 (Protolabs supports M2 to M12) | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.blind_tap_runout_d_ratio` | 1.5 x diameter | warning | unthreaded depth below a tapped blind hole. for threads smaller than M6 add an unthreaded length of 1.5 times the nominal diameter at the bottom of the hole | https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ |
| `cnc.setups_max` | 3 set-ups | warning | set-ups on a 3-axis mill. each side a cutter must face is a re-fixturing; text-to-cad warns past five, Hubs says three to four rotations | mechloop's own figure: no published guide read here states one |
| `cnc.part_max_mm` | 2000 mm | warning | longest side. past a general shop's mill (text-to-cad, citing Hubs's CNC service page) | text-to-cad: packages/cad/src/cad/_internal/dfm/cnc.py |
| `cnc.removed_max_fraction` | 0.85 fraction of the stock | warning | share of the stock turned into chips. a cost signal, not a limit: consider a nearer-net stock shape or a built-up part | mechloop's own figure: no published guide read here states one |
| `cnc.unreachable_fraction` | 0.02 fraction of the surface | error | surface no straight cutter reaches. Hubs: undercuts cannot be machined with standard tools; the 2% tolerance on the sampled surface is text-to-cad's | text-to-cad: packages/cad/src/cad/_internal/dfm/cnc.py |

Shop data (not single limits): `SHOPS["generic"]` uses common metric gauges (our own list: sheet 0.5 to 25 mm,
plate 1.5 to 50 mm). `SHOPS["sendcutsend"]` holds the stocked thickness, largest instant-quote size and smallest
part for each of five metals, the bend table for 5052, mild steel, 304 and brass, and the tap range for aluminium.

Assumptions behind the estimates (our own, in `dfm_rules.py`): roughing 12 cm³/min in aluminium, 3 in steel, 1.8 in
stainless; 12 min per set-up; 20 min programming; $75/h; stock $3-14/kg; printing 5 mm³/s with 1.2 mm walls and 20%
infill; laser $1.50 per metre of cut. They are for comparing two versions of a design, not for quoting.

## How each thing is measured

- **Part frame**: the direction carrying the most flat area is the part's Z; six tool / build directions follow.
- **Holes**: concave cylinders on one axis and radius that together sweep 300 degrees or more, split where the wall
  stops (two ears bored in line are two holes); coaxial wider bores are counterbores; through or blind by a ray along the axis.
- **Wall thickness / gap**: from each surface sample a ray straight into the material (or out through the air) to
  the next surface that faces back.
- **Reach**: a sample is reachable from a direction when its face does not look away from it and a ray towards the
  cutter is clear. Set-ups: greedy fewest directions covering all samples, holes, tapped holes and side-milled corners.
- **Tapped holes** are not modelled in a design (a screw that `threads_into` a part overlaps it), so they are read from
  the screws: entry point, engaged length, material left beyond the tip.
- **Sheet profile**: the top face's wires projected to 2D exactly (arcs every 3 degrees) into a shapely polygon;
  necks and slots by morphological opening and closing at the limit width; inside corners by rolling the cutter's radius.
- **Print orientation**: six directions scored `support area - 0.2 x bed contact + 0.5 x height`, a large penalty
  if it does not fit, and a penalty when a load case acts mostly along the build direction. Flat ceilings are tested
  for a wall on both sides in four directions; spans up to `fdm.bridge_max_mm` are excused from support.

## Results on the existing designs

`python -m mechloop verify <design> --no-render --only geometry manufacture`, generic shop, no overrides. The designs
were not edited.

| Design | Parts | Result | Findings by code |
|---|---|---|---|
| examples/motor_bracket.py | 1 printed | pass, 1 warning | horizontal_hole_droop 1, elephant_foot 1 (info) |
| examples/gantry.py | 8 machined, 1 printed | pass, 13 warnings | sharp_corner_side_milled 5, thin_wall 2, non_stock_thickness 2, blind_tap_runout 1, needs_support 1, thin_wall_around_thread 1, load_across_layers 1, printed_threads 1 (info) |
| designs/printer_v3.py | 18 machined, 1 sheet | FAIL, 1 error, 6 warnings | thin_wall 1 error + 2 warnings, mostly_chips 1, angled_faces 1, many_setups 1, blind_tap_runout 1 |
| designs/z_axis_v2.py | 8 machined | pass, 2 warnings | mostly_chips 1, angled_faces 1 |
| designs/pan_tilt.py | 6 machined, 1 printed | FAIL, 1 error, 2 warnings | sharp_inside_corner 1 error, blind_tap_runout 1, mostly_chips 1, elephant_foot 1 (info) |

Notable findings ("checked" means the geometry at the reported point was inspected by hand):

- **printer_v3 `y_belt_clamp_l`, thin_wall error, 0.10 mm.** Checked: faces at x = -183.05 and x = -182.95, 1.5 mm
  tall, 22.5 mm long: the belt pocket stops 0.1 mm short of the clamp's side face. Real; the pocket should run out
  through the side or stop at least 0.8 mm short. The right-hand `y_belt_clamp` has 0.8 mm there and passes.
- **pan_tilt `yoke`, sharp_inside_corner error, 4 corners.** Checked in the design source: `y -= Box(ta, 44, 44)`
  cuts a square window through one arm for the tilt motor with no corner radius. A closed window cannot be squared by
  any cutter. Real. The previous verifier did not see it (it only looked for corners on plates).
- **printer_v3 and gantry `y_plate_left/right`, thin_wall warnings, 0.51-0.58 mm.** Checked: a 6 mm counterbore
  centred 3.5 mm from the plate's edge leaves 0.5 mm of wall. Real.
- **printer_v3 and z_axis_v2 `carrier`, mostly_chips 95-96%, many_setups, angled_faces.** The carrier is drawn as
  one solid 210 x 270 x 56 mm; machined from a block almost all of it is chips. The angled faces were checked: rib
  undersides with normal (0, -0.19, -0.98). Real as modelled; in practice it would be plates bolted together.
- **gantry plates, sharp_corner_side_milled.** `y_plate_left` at (-155, 25, 226) is the same inside corner the old check
  reported as an error; it is open to the side, so a square end mill can make it in another set-up: now a warning.
  The belt clamps' corners are the ends of 1.5 mm deep belt pockets (checked in the source: `Box(14, 1.5, 7.2)`).
- **gantry `tool_plate` (PETG): needs_support 524 mm², load_across_layers, thin_wall_around_thread.** Not checked by
  hand beyond the numbers; the old check chose -X up with 1006 mm² of support because it had no notion of bridges.
- **motor_bracket: horizontal_hole_droop.** The 23 mm motor bore is horizontal with +Z up. +X up would need no support,
  but the load case would then pull the layers apart; the metrics say so in `orientation_note`.
- **blind_tap_runout** (gantry M5 idler bolt 1.2 mm short of the far face; printer_v3 tool plate; pan_tilt yoke at
  4.0 mm against 4.5): arithmetic on screw length and part thickness, not checked further. These are the least
  important findings; tapping through fixes each.
- `electronics_tray` (the one declared sheet part) passes clean: 3 mm stock, 340 x 120 mm, 11 holes of 4 mm and up.
- DXF profiles are written for the tray and for 8 machined plates that are plain through-cut profiles
  (`could_be_cut_2d: true` in the metrics): candidates for laser cutting instead of milling.

False positives found and fixed while doing this:

1. **Deep hole 11:1 and 18:1 on the yoke and cradle.** Two ears bored on one axis were read as one hole spanning the
   air between them. Holes are now split where the wall stops.
2. **Ten "side-milled corners" on a belt clamp.** Floor-to-wall roots of a pocket were counted with wall-to-wall
   corners. A root is made by the end of the cutter and is now ignored.
3. **Deep narrow slot on a block with one 3.4 mm hole.** Samples inside holes were treated as slot walls. Holes are
   now excluded from slot analysis.
4. **Lathe spacers reported as non-stock-thickness plates** (old check) and their "71% of the stock removed" cost
   driver: round parts are now recognised as turned from bar.
5. **Generic bend-radius warning on a part modelled at the shop's own tooling radius**: suppressed when the radius
   matches the selected shop's.
6. **Sharp-folded sheet read as a 30 mm pocketed plate**: now reported once as `sharp_bend`.
7. A wall of exactly the limit thickness failing by 0.0001 mm (ray start offset).

Speed: 1.4 to 4.6 s for the manufacture verifier on these designs (0.1 to 0.5 s per part).

## What is still not checked

- **Sampling**: thin walls, gaps and unreachable regions smaller than about one sample (surface area / 2000, so
  roughly 1 mm² on a small part and 50 mm² on a 300 mm plate) can be missed. Holes, corners and sheet profiles are
  exact and do not depend on sampling.
- **Sheet**: bent parts are not unfolded (no flat pattern, no bend allowance, no check that the flat fits the sheet);
  bend reliefs, bend order and brake tooling collisions, hems, joggles; grain direction; hardware (PEM) clearances;
  SendCutSend's per-SKU minimum hole and bridge figures; nesting; heat distortion of dense patterns; DXF kerf compensation.
- **FDM**: only six axis-aligned orientations; no slicing, so no real support volume, print time or seam; cantilever
  reach is all-or-nothing; a bending load across a tall part is not recognised as loading the layers (direction of the
  force only); knife edges, trapped cavities, clearance between mating printed parts (the tolerance verifier covers
  hole size), embossed detail, stringing; warp remains a rule of thumb.
- **CNC**: 3-axis only; tool holder and spindle collisions; fixturing and how the part is held; whether the cutter that
  fits a corner is also long enough for the neighbouring wall; through slots are assumed cut from both sides (depth is
  halved); T-slots and dovetails open at both ends pass the line-of-sight test although they need a special cutter;
  counterbore side is not used to fix the hole's set-up; surface finish and tolerances; turned parts get only basic
  checks; inch drills are accepted only as fractions.
- **Cost**: the time and cost figures are coarse estimates from volume removed and set-up count, with assumed rates.
- **Castings, moulding, welding, other printing technologies**: not covered.
