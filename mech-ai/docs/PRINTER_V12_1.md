# printer_v12.1: the owner's review decisions on v12, one change set each

Everything here is simulated. Nothing has been built.

`designs/printer_v12_1.py` is a copy of `designs/printer_v12.py` (v12 untouched) with every owner decision of the 2026-11-21 review
behind its own **change flag** (docs/OPERATING_MODES.md, iterative mode). With every flag off it builds printer_v12 exactly (checked:
904 parts, every part's SKU, material, volume and bounding box identical). Each change was built as **v12 + that change** (plus the
changes it depends on), verified with the affected tier and the opt-in part-quality checks, and exported as a change set for the
review page's Changes tab (`review_v12_1/changes/`). The combined build (all flags on) is a preview only; the real v12.1 revision
(flags removed, clean code, full verify) comes later from the changes the owner accepts.

    MECHLOOP_CHANGES=none            -> printer_v12 (design name printer_v12_1-base)
    MECHLOOP_CHANGES=znut-direct     -> v12 + znut-direct (design name printer_v12_1+znut-direct)
    MECHLOOP_CHANGES=all  (default)  -> every change (printer_v12_1)
    .venv/bin/python tools/build_change.py designs/printer_v12_1.py <id> --verify     # build, check, export one change

| flag | depends on | status |
|---|---|---|
| `estop-mount` | | proposed |
| `zmotor-holes` | | proposed |
| `znut-direct` | | proposed |
| `carriage-plate-rigid` | | proposed |
| `rear-z-inside` | `znut-direct` | proposed, **with a deviation: x 0 collides, the screw stands at the rear-left** |

Not changed (owner, decision 6 pending at the start; decided "B" later as its own change `bed-thumb-reach`, not done here): the bed
thumb nuts.

## What changed, per decision

### 1. `estop-mount`: the A22E re-made, a stiffer mount
- **Model:** `estop_omron_a22e_m_02_v2(panel_t)` (mechloop/parts/batch12.py, new function; v12's part unchanged), re-made from OMRON's
  A22E data sheet p.41 drawing "A22E-M": head dia 40 x 6.5, 32 in front of the panel, (0.5) gasket, threaded bushing through the 22.3
  cut-out, knurled ring nut tight on the panel's back face, the 34 mm switch block 41.2 long **starting 13.5 behind the panel's front
  face** and ending 54.7 behind it. Not dimensioned on the drawing and drawn as estimates (flagged in the part): barrel and skirt
  diameters, bushing 22, ring nut 30 x 4, the block's width (34, square). The `allow_overlap("estop", "estop_bracket")` is gone: the
  block no longer meets the bracket.
- **Mount: bent L-bracket chosen** over an off-the-shelf one-hole control station. Why: no station with a maker's drawing is in
  vendor_docs (DG-07 needs the maker's CAD or a faithful re-make from a drawing); the L is two cheap laser parts held through the
  T-slots with no drilling, and it is stiff where v12's was weak (v12: a flat plate cantilevered 40 mm left of the post with both M5
  on one vertical line, so a push on the head pivoted it about that line).
  - `estop_bracket`: 5052-H32 .125 in, one bend at SendCutSend (3.18 mm inside radius, their only radius for the gauge), wrapping the
    front-left post's **front-right corner**: the panel leg on the post's front face carries the e-stop 30 mm left of the post; two M5
    into the post's front slot and two into its right-hand slot (**two columns on two faces at 90 degrees**). Spec docstring in
    `estop_bracket_local()`.
  - **Deviation: 5052, not 6061.** SendCutSend does not bend 6061 (its material page, recorded in mechloop/shops/sendcutsend.json).
  - `estop_spacer` (new, 6061 .125 flat): a bend's 3.18 mm inside radius cannot hug the post's square corner, so the panel leg stands
    off the front face by one 3.175 mm spacer under the front screws (the alternative, the .090 gauge with a 0.81 mm radius, is 2.8
    times less stiff). The head is 3.2 mm further forward than v12 (front of the head at y -231.4).
  - FEA load case `estop_slap`: 200 N (assumed palm strike) on the cut-out, the M5 holes held.
- Parts: removed 0, modified 4 (estop, estop_bracket, the two front-slot screws, now M5 x 12 with washers), added: estop_spacer, two
  right-slot screws with washers and T-nuts (exact lists in `review_v12_1/changes/index.json`).

### 2. `zmotor-holes`: the Z motors' M3 threads drawn
`leadscrew_motor_a4003_tapped()` (new function): drawing A4003's 4 x M3, DEPTH 4.5 MIN on the 31 +/-0.1 square, cut into the body's
front face as 2.5 mm tap-drill holes 4.5 deep. Used for all three Z motors. Nothing else changes.

### 3. `znut-direct`: the Z nuts bolted direct
- Each POM nut's 26 mm square flange is bolted to the underside of its 9.525 mm nut plate by **two M3 x 20 through-bolts in the
  flange's own two OUTER holes**, washer under the head, washer and thread-locked nut on the plate's top face. Flange hole pattern
  **confirmed from StepperOnline drawing A4003: 4-M4 on an 18.5 mm square** (the part model already had it). **Deviation from
  "screws into tapped holes in the plate":** SendCutSend taps M5 and up in 3/8 in 6061 (its tapping table), so M4 threads would be
  a builder's second operation, which the shop rules flag as errors and practice DG-02 rejects; the two inner flange holes are left
  empty because a nut on them would sit under the square's member (the flange's inner holes are 0.15 mm outside the member's face).
  The flange's own face carries the thrust; the two bolts hold the nut square and take the drive torque (0.44 N.m at most: 34 N of
  shear at 13 mm). M3 rather than M4 because McMaster numbers and STEPs are on record for the M3 sizes only (an M4 x 20 would be a
  new DG-07 placeholder). **Flagged:** A4003 writes "4-M4" without saying tapped or clearance: if they are tapped, drill two to
  4.0 at the bench. Heads and washers clear the nut's 18 mm barrel by 0.6 mm.
- `nut_plate_direct_local()`: rebuilt from a spec (docstring): screw hole 9 mm (0.5 mm all round), closed (motor, screw, nut and plate are one bench unit put in from above before the top side rail, as v12's front units; an open slot would leave 2.4 mm webs, under the shop's 4.76)
  ; two M5 into the member's bottom slot.
- **Motor plates lined up at assembly** (needed once the nut cannot float): the three motor plates are redrawn from a spec with true
  arcs (`motor_plate_arcs()`, 8 mm round the hull of the motor screws and posts; v12's were hulls of 40-gons with slivers) and their
  post holes are 8 mm (inside the 10 mm posts' faces, covered by the M5 washers): each plate slides +/-1.25 mm. Assembly: post bolts
  loose, bed at the BOTTOM of its travel (nut nearest the motor, where the screw is stiffest), turn the screw by hand until it runs
  free, tighten the post bolts. Declared to the tolerance model as the Z axis's alignment range.
- Removed, per corner (42 parts in all): `nut_keeper*`, its two spacers, two keeper bolts with their washers and nuts, the
  anti-rotation `nut_pin*` screw, its sleeve and nut. The joint now declares a bolted nut: reverse gap 0 (anti-backlash nut,
  assumed), no nut-tilt allowance (the nut cannot rock; the screw, free at its top end, bends instead, as on a Voron Trident).
- FEA `nut_thrust` loads the plate on its underside (where the flange bears).
- **Z binding with the fixed nut** (tolerance model, 3000 builds, 99.7th percentile): the nut sits up to 0.16 mm off its screw at
  the bottom of the travel (taken out by the motor-plate alignment) and the screw-to-rail angle adds up to 1.32 .. 1.73 mm over the
  180 mm travel. That drift is met at the top of the travel, where the screw is a 227 mm cantilever from the motor's bearings:
  3 E I x / L^3 with the 6.24 mm root (I = 74.5 mm4) gives at most **6.4 N sideways on the nut, about 1.3 N of drag (mu 0.2)
  against 691 N of drive: 0.2 %** (hand calculation from the tolerance model's figures; the verifier's own bending model reports 0
  because it counts the alignment range against the whole misalignment). v12's floating nut had the same small figure (0.27 N).

### 4. `carriage-plate-rigid`: rigid carriage brackets
- **Deviation from "a straight 1/4 in plate":** the block's mounting face (x 137) and the square's outer face (x 135.4) are 1.6 mm
  apart, the thickness of v12's flexure plate, and the square's position is fixed by the bed and deck layout. A straight plate of
  6.35 mm between them would move the square 4.75 mm inboard on three sides, which shrinks the carrier and puts the bed thumb nuts
  (already 0.9 mm from the members) into the members and the stud washers onto the heater pad. So the owner's **fallback** is used:
  a 52 mm length of **6061-T6 angle, 2 x 1 x 1/4 in**, saw cut, leg A milled down to 29 mm wide, drilled (Xometry,
  `carriage_angle_local()`, spec docstring). Leg A on the block's face (four M3 x 10 into the block), leg B under the square's
  member (two M5 x 12 with washers up into T-nuts in its **bottom** slot, standing beside the trimmed leg A; the side slot cannot be
  reached by any part that also sits on the block's face). Root radius taken as 1/8 in (assumed); McMaster part number to pick.
  - No catalogue bracket matching MGN12H holes and a 2020 bottom slot was found in the parts at hand.
- The block is raised to sit 1 mm under the square (block centre 23.65 mm higher); the three Z rails rise with it (rail centre z 225.7,
  top 373.2, 10.8 mm under the top rails), so the block's travel on its rail is unchanged.
- `guide_float` (the flexure model) is deleted from the three blocks, the `carriage_plate_web` FEA case and its requirement go, and the
  three-rail requirement now asks that the assembly alignment covers the as-built error and reports the side load left after it.
- **Assembly and commissioning step (written into the Z rails' adjustment note, which the build package prints):** the rear rail is
  the datum, set square and tightened. The left and right rails' M3 screws are left finger-loose; with the bed on, the carrier is run
  up and down its full travel two or three times so those rails settle where the carrier puts them; then their screws are tightened
  from the top down, the carrier moved to stay beside each screw as it is tightened. Check: the carrier runs its travel with the Z
  motors' current at 30 % without stalling.

### 5. `rear-z-inside`: the rear screw inside the frame (deviation)
- **x 0 does not fit.** With the screw at (0, 154.5) (inside the back wall, 9.1 mm from the square's rear face, like the fronts), at
  the rear end of the Y travel the Eddy probe, its holder and bolts and the part duct (down to z 376) pass through y 150.5 .. 158.5 for
  every X from -138 to +128 (the toolhead's sweep), and the as-sold screw's top is at z 401. Moving the square forward does not move
  the toolhead (it reaches y 161 at the rear stop), and no y inside the back wall is behind it. The X beam itself clears (it does not
  reach y 150 at the rear stop).
- **What fits:** the toolhead never goes left of x -140.5 (the front-left screw at x -144.5 proves it), so the rear screw stands on
  the front-left screw's line, **x -144.5, y 108** (9.1 mm outside the square's left face, 1.5 mm from the side wall's inner face).
  Further back is blocked by its motor: the 42.3 mm body overhangs the bottom left rail like the fronts' and must end in front of the
  frame corner bracket `bracket_6` (on that rail from y 130 to 160, z 20 to 50). The right side is no better (the duct sweeps to
  x 128, and the right-rear corner bracket blocks the motor the same way).
- Same design as the fronts: the fronts' direct-bolted nut plate under `sq_left` (identical shape), the nut bolted direct, the motor
  hung under a 6.35 mm plate (outline now true arcs, `motor_plate_arcs()`) on two turned posts on the bottom back rail's top slot
  (x -125 and -95).
- **The cost (open question for the owner):** the three screws now stand at (-144.5, -101), (144.5, -101), (-144.5, 108). The bed's
  centre (-15.5, 4.5) is only about 7 mm inside the line from the front-right to the rear-left screw. With bolted nuts (they hold both
  ways) the bed cannot tip off, and Z_TILT_ADJUST works with any three non-collinear screws, but the rear-left and front-right nuts
  share most of the load and a heavy print at the rear right is carried partly in tension. Alternatives: (a) a shorter screw at x 0
  (StepperOnline lists a custom-length service; with the top below about z 374 it clears the toolhead; not priced, and it breaks the
  "as sold" rule); (b) keep v12's rear screw outside the back wall.
- `Z_TILT` positions follow: the rear screw is at firmware (-35.7, 207.55), on the front-left screw's firmware X (both outside the nozzle's reach, as before for the fronts).

## Verifier results

Per change (affected tier from v12's cache, then part-quality on the changed custom parts); the exact text is in each change's
"checks" in `review_v12_1/changes/index.json`.

RESULTS_TABLE

## Open items
- e-stop: the A22E's undimensioned features (barrel, bushing, ring nut, block width) are estimates; the 200 N palm strike is assumed.
- e-stop bracket in 5052 (SendCutSend does not bend 6061).
- A4003 "4-M4" flange holes: tapped or clearance not stated.
- Carriage angle: needs a sharp-corner 2 x 1 x 1/4 in 6061 angle (supplier part number to pick).
- Rear Z at the rear-left: the owner's call (see 5).
- Bed thumb nuts (decision 6 = B, change `bed-thumb-reach`) not done in this run.

## Files
- `designs/printer_v12_1.py` (flags, CHANGE_INFO), `mechloop/parts/batch12.py` (new: `estop_omron_a22e_m_02_v2`,
  `leadscrew_motor_a4003_tapped`), `tools/build_change.py`
- `review_v12_1/changes/index.json`, `review_v12_1/changes/<id>.json`, `review_v12_1/changes/<id>.txt`
