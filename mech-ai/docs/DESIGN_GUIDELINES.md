# Design guidelines (owner's practice)

Standing guidance from the owner, who intends to build the printer. Every design pass reads this file
alongside AGENT.md. Where a check enforces a guideline the check is named; the rest are reviewed by hand
until a check exists.

## Key rule: off-the-shelf parts are real parts (owner, 2026-11-20)

- **Only parts we fabricate are generated.** Geometry made by our code is allowed only for parts we will make or have made
  to our design (laser-cut and bent sheet, machined parts, printed parts). Every other part in the model is a purchased part
  and follows the rules below; no purchased part is drawn from a generic or "standard-typical" generator.
- **Every off-the-shelf part is a real, orderable product**: a named maker, the maker's part number, and a seller where it can
  be bought (distributor or maker) at the stock size used. No generic, "typical", "class value" or "any to the standard"
  purchased parts in a design that is presented as buildable. Commodity hardware (screws, nuts, washers, wire, ferrules) is
  pinned to a real catalogue item too (e.g. a McMaster, Misumi, Accu or distributor part number).
- **Its geometry comes from the maker**: ideally the maker's own CAD file; otherwise a faithful re-make from the maker's
  dimensioned drawing (every dimension on the drawing in the model, nothing un-dimensioned, the drawing recorded). Its
  ratings (current, torque, temperature, load) come from the maker's datasheet, with source and quote.
- **Domestic (US) sources only** (owner, 2026-11-20): every purchased part must be orderable from a seller that ships
  within the US (no international shipping). A part sold only abroad is not a real option for Build 1.
- Anything else is a **placeholder**. Placeholders are allowed while designing, but must be impossible to miss: named
  `PLACEHOLDER-...` in the BOM, drawn in a distinct warning colour in the viewer and review page, listed at the top of the
  design doc and the build package with the real part (or the search) that will replace each one, and reported by the
  check as an **error** ("must be fixed before buying"), never as a pass or a quiet info line. A design with any
  placeholder is not buildable.
- Check: `practice` DG-07 (mechloop/verifiers/purchased.py): `purchased_part_not_real` / `purchased_geometry_not_sourced` /
  `purchased_rating_not_sourced`, errors, one per SKU; warnings only in a design that sets `design.exploratory = True`. Real-part
  facts go on the part (`place(..., real_part={...})`, `bom_extra(..., real_part={...})`) or in mechloop/data/real_parts.json.
  The viewer export flags each placeholder (`placeholder: true`, magenta), the BOM names it `PLACEHOLDER-<sku>` and the build
  package README lists them first. Audit of the current catalogue: docs/PROVENANCE_AUDIT.md.

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
  part carries a written reason in the design doc. Check: `practice` DG-03, a machined part with only
  through features is flagged as a 2D candidate (info) unless `meta["cnc_reason"]` records the reason.
- **3D printing only for light, non-load-bearing parts**: sensor holders, ducts, cable clips, electronics
  covers. Nothing that carries a guide, bearing, lead-screw nut, motor, belt tension, the bed's weight or a
  screw clamp in a load path. Check: `practice` DG-01 (`printed_load_path`), an error unless waived with a
  written reason (`d.waive("DG-01", part, reason=...)`).
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
  No tapped extrusion ends: use corner brackets or T-nut fixings. Check: `practice` DG-02 (`tapped_aluminium`,
  `tapped_extrusion_end`, warnings); declare a PEM nut or steel insert with `add_screw(..., insert="pem" | "steel")`.
- **Screws through printed parts are through-bolts with a nut**, with a washer under the head and under the nut
  wherever either bears on plastic. No thread is tapped, cut or self-tapped into a printed part. A heat-set insert is
  allowed only with a written reason, for example where there is no access for a nut; where a nut cannot be reached,
  first try a nut (with its washer) captured in a printed pocket, or a PEM stud in the metal part with the nut outside.
  Check: `practice` DG-04 (`thread_in_printed_part`; a warning, an error when the joint is in a load path; it covers
  FST-090). Declare an accepted insert with `add_screw(..., insert=True, insert_reason="...")`.
- **Printed clearance holes: ISO 273 medium plus an FDM allowance of 0.2 mm on the diameter**, because vertical holes
  print undersize: M2.5 3.1, M3 3.6, M4 4.7, M5 5.7, M6 6.8 (`mechloop.parts.printed_clearance_hole(size)`). A hole
  whose axis lies in the build plane gets 0.3 mm (M3 3.7) and a teardrop or flat top, so it prints without support.
  Holes in metal parts stay at ISO 273 (`clearance_hole`, FST-020). This replaces the older convention of drawing
  printed holes M3 4.2 and M5 6.0. Bearing seats and insert pockets are not clearance holes and keep their own figures.
  The allowance is a starting value: print a calibration coupon on the owner's printer with M3 holes from 3.4 to 3.8 mm
  in 0.1 mm steps, then set the allowance (`d.practice["limits"]["DG-05.allowance_vertical_mm"]`, and
  `"DG-05.allowance_in_plane_mm"`) and the slicer's hole (horizontal-expansion) compensation to match. Check:
  `practice` DG-05 (`printed_hole_too_small` under medium + allowance; `printed_hole_oversize_no_washer` over coarse
  + 0.4 mm under a bare head or nut). Sources read for this guidance:
  - zbotic, "3D print tolerances: hole sizes and clearance guide"
    (https://zbotic.in/3d-print-tolerances-hole-sizes-and-clearance-guide/): an M3 hole drawn 3.0 mm in PETG prints at
    about 2.7 mm; a 3.4 mm clearance is used.
  - FIRST Tech Challenge docs, tolerancing
    (https://ftc-docs.firstinspires.org/manufacturing/3d_printing/designing_and_slicing/tolerancing/tolerancing.html):
    the slicer's horizontal-expansion compensation, and test coupons to find the printer's offset.
  - GrabCAD, "Fused deposition modeling (FDM) design guidelines"
    (https://grabcad.com/tutorials/fused-deposition-modeling-fdm-design-guidelines): vertical holes print undersize; the
    amount varies by printer and material; drill holes that are critical.
- Nylon-insert lock nuts only where the part stays below about 120 degC; nearer heat use all-metal lock nuts. Check:
  `practice` FST-072 (from each part's `meta["service_temp_c"]`).
- **Washers** wherever a head or nut bears on a slot, an oversized hole, thin aluminium or plastic; not as a
  blanket rule on steel-on-steel joints. Check: washer / head-bearing check.
- **Every fastener is drawn.** Screws, nuts, washers, T-nuts and bracket screws are parts in the model, not BOM lines,
  so their length, fit and access are checked. T-nuts are the drop-in type (none is loaded from an extrusion end).
  Check: `practice` DG-06 (`hardware_bom_only`, `hardware_count_mismatch`, `joint_without_fasteners`; errors) and
  `interference` `tslot_screws` (`screw_bottoms_in_slot`, `tnut_thread_engagement`; errors), in designs with
  `design.tnut_style = "drop_in"`. The slot and T-nut dimensions those checks use are stand-ins until a supplier
  drawing is read (`mechloop/parts/tslot.py`).
- Thread locking (nyloc or adhesive) on fasteners of moving or vibrating assemblies. Check: `practice`
  FST-070 (declare it with `add_screw(..., locking=...)` / `add_nut(..., locking=...)`).
- Thread engagement where a thread in aluminium is unavoidable: 6061 error below 1.5 d, warning 1.5 to 2 d
  on load-bearing or often-removed joints; softer alloys 2 d minimum.

## Edges

- No sharp edges or corners on metal parts: rounded outside profile corners on sheet parts, broken edges on
  machined parts ("deburr; break all sharp edges 0.2 to 0.5 mm"), lead-in chamfers on hand-assembled bores
  and pins. Check: sharp-edge check.

## Sub-assemblies first

- Design the machine as sub-assemblies of components. Create and validate each sub-assembly on its own
  (fit, fastener access, alignment and adjustment, the checks that apply to it), then assemble the
  validated sub-assemblies in place in the machine.
- The assembly plan is written down as part of the design: what is built first, which sub-assemblies are
  built and checked on the bench, and the order they go into the machine. Checks run against that plan.
  Check: not implemented yet (today the order is found by the assemblability search, not stated).
- Every assembly step respects gravity. The plan states which way up each sub-assembly and the machine sit
  on the bench at every step. At each step every placed part rests on something that supports it (no part
  in thin air), and the work in progress cannot tip over or slide: its centre of mass stays inside what it
  stands on, with margin. A part or fastener that must be held until fastened is a stated, deliberate step
  (one hand, one part), not the norm; nuts and washers go on with their screw, not before it. Turning the
  assembly over is a stated step, done only when it is stable in both positions.
  Check: partly implemented (the build simulation reports parts that would fall or tip and counts holds
  and turns); to become pass/fail against the written plan.

## Purchased-part CAD

- Hardware and purchased parts use the supplier's own CAD file (for fasteners: McMaster's STEP for the part
  number), not geometry generated to a standard or a stand-in solid. Generated or stand-in geometry is a
  placeholder until the supplier file is in `vendor_cad/inbox/`, and is reported as such.
- A purchased part may be re-made from the supplier's drawing only if it is faithful: every dimension on the
  drawing is in the model, and no feature of the model is un-dimensioned (nothing guessed or scaled). Record the
  drawing it was made from. Anything less is a stand-in and is reported as one.
- Purchased parts are used at stock sizes, as sold. Do not assume a purchased part is cut, shortened or
  otherwise modified (rails, lead screws, shafts, belts sold in closed lengths). Where a part is only sold
  cut to order (T-slot extrusion), say so and name the supplier's cutting service.
- Frame: the common 2020 profile with the 6 mm slot (Misumi HFS5-2020 class); McMaster's 20 mm rail with a 5 mm slot,
  its T-nuts and its bracket are not used (owner, 2026-11-19). T-nuts and corner brackets are standard-2020 parts.
