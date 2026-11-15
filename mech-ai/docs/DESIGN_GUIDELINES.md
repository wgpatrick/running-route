# Design guidelines (owner's practice)

Standing guidance from the owner, who intends to build the printer. Every design pass reads this file
alongside AGENT.md. Where a check enforces a guideline the check is named; the rest are reviewed by hand
until a check exists.

## Priorities

- **Functionality comes first.** Part count, assembly time and cost are reported, not optimised. More parts,
  time or cost are acceptable when the design is better; say what each addition buys.
- Never trade fit margins, bed stiffness or toolhead clearances for speed.

## Process choice

- **2D laser-cut aluminium plates first.** Plates are cheap and fast; CNC costs roughly ten times more and
  takes longer. Replace a CNC part with two or three stacked or bent plates where possible.
  - Locate stacked plates with tab-and-slot features or fitted bolts, not loose clearance holes.
  - Bearing seats in plates come from flanged bearings or clamping between plates, not precise bores.
  - Bends only in 5052 (6061-T6 cracks).
- **CNC only where it earns its place** (a precise bore, a 3D pocket, a flatness-critical face). Each CNC
  part carries a written reason in the design doc. Planned check: machined part with only through
  features is flagged as a 2D candidate (advisory).
- **3D printing only for light, non-load-bearing parts**: sensor holders, ducts, cable clips, electronics
  covers. Nothing that carries a guide, bearing, lead-screw nut, motor, belt tension, the bed's weight or a
  screw clamp in a load path. Planned check: `practice` rule, error unless waived with a written reason.
- Printed parts declare print settings (material, walls, top/bottom layers, infill and pattern,
  orientation); mass and strength follow from them, not from solid plastic.

## Suppliers

- 2D parts: **SendCutSend** (shop profile `sendcutsend`). CNC: **Xometry** or an equivalent online bureau
  (shop profile `xometry`). See docs/FABRICATORS.md.
- Draw sheet parts at the supplier's stocked gauges only (the shop profile enforces this).

## Materials

- CNC: 6061-T6. Bed: cast tooling plate (MIC-6) at a stocked thickness with faces as cast.
- 2D: 6061-T6 or 5052-H32 aluminium; Delrin only for low-friction, insulating, lightly loaded parts away
  from the bed and hotend.
- No generic "steel": name the grade, and give carbon steel a finish the supplier can apply, or use
  stainless or aluminium. Prefer aluminium on moving parts.

## Fasteners and threads

- **Do not tap aluminium parts we make** (strips easily). In order of preference: through-bolt with nut and
  washer; self-clinching (PEM) nut in sheet; steel thread insert where a thread in thick aluminium is
  unavoidable. Vendor parts with factory threads (guide blocks, rails, motors, extruder) follow the maker.
  No tapped extrusion ends: use corner brackets or T-nut fixings. Planned check: `practice` rule.
- **Washers** wherever a head or nut bears on a slot, an oversized hole, thin aluminium or plastic; not as a
  blanket rule on steel-on-steel joints. Check: washer / head-bearing check.
- Thread locking (nyloc or adhesive) on fasteners of moving or vibrating assemblies.
- Thread engagement where a thread in aluminium is unavoidable: 6061 error below 1.5 d, warning 1.5 to 2 d
  on load-bearing or often-removed joints; softer alloys 2 d minimum.

## Edges

- No sharp edges or corners on metal parts: rounded outside profile corners on sheet parts, broken edges on
  machined parts ("deburr; break all sharp edges 0.2 to 0.5 mm"), lead-in chamfers on hand-assembled bores
  and pins. Check: sharp-edge check.
