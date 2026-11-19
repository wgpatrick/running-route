# printer_v10_1: every fastener drawn, every T-slot screw checked for length

Everything here is simulated. Nothing has been built.

`designs/printer_v10_1.py` starts from a copy of `designs/printer_v10.py` (v10 was not edited). The owner's instruction was
"make sure all fasteners are in place", after finding by eye that T-nuts and corner-bracket screws were BOM lines without
geometry, that nothing checked a screw's length in a T-slot, and that half the toolhead's fasteners were bare stand-in
solids. During the work the owner added three things, all folded in: supplier CAD is wanted for all hardware and McMaster's
files for most fasteners arrived; a purchased part may only be re-made from a supplier drawing if every dimension is used;
and the frame stays on the common 2020 profile with the 6 mm slot (McMaster's 5 mm-slot rail is not used).

The frame, envelope, travel, bed, cooling fan and duct, belt tension brackets and probe mount are v10's. No made part
changed shape (a test checks every made part's volume and bounding box against v10's). What changed is screws, washers,
nuts, and what the checkers look at.

VERIFY_SUMMARY

## The short answers

| Question | Answer |
|---|---|
| T-nuts drawn | **156** (123 M5, 33 M3), one per T-slot screw, each a part in its slot, in the BOM by SKU (`TNUT-2020-M5`, `TNUT-2020-M3`), visible in the viewer. v10: none drawn, 156 as BOM lines. |
| T-nut chosen | **Misumi HNTAJ5-5 / HNTAJ5-3**, "post-assembly insertion short nut" for the HFS5 series: a drop-in nut with a leaf spring. None has to be loaded from an extrusion's end. |
| What the T-nut model is | A **re-make from Misumi's dimensioned catalogue drawing** (MISUMI USA 2019 catalogue p.2717, fetched, copy in `vendor_docs/`): all six dimensions used, nothing guessed; three drawn but un-dimensioned features left out (edge chamfers, leaf spring, countersink ring). Not supplier CAD: Misumi's STEP needs a login. |
| Bracket screws drawn | **64** M5 x 8 cap screws, two per corner bracket (32 brackets), each with its T-nut. v10: 64 BOM lines "not drawn, access not checked". |
| Slot geometry | Misumi's catalogue drawing for the HFS5 series (p.2686, fetched): opening 6, lip 2, lip to floor 4 (so 6.0 deep), cavity 12. The extrusion's simulation solid has a plain slot 6.2 wide and 5.0 deep with no lip: shallower, so it could not judge bottoming. The checks use the drawing's figures. |
| Screws that were wrong in v10 | **41 of 92** T-slot screws: 35 would have reached, or come within 0.5 mm of, the slot floor before clamping; 6 (the nut plates') had 1.45 mm of thread. All corrected (list below). |
| The rail screws the owner asked about | M3 x 8 through the MGN12 rail: 4.5 mm into the slot, through the nut's whole 3.2 mm of thread (1.07 d), 1.5 mm off the floor. Right as they were. |
| Completeness | The new rule finds nothing in v10.1: 654 hardware parts drawn, no hardware on the BOM without geometry, no declared joint without its fasteners. On v10 it finds 6 BOM-only hardware lines (212 pieces) and 64 joints without fasteners. |
| Toolhead fasteners | Of the 50: **46 are McMaster's own CAD**, 2 (the probe's nuts) are generated from OMRON's drawing dimensions, 2 (clinch nuts) are stand-in solids. None is a bare simulation solid any more (v10: 26). |
| Machine-wide | Of 654 screws, nuts, washers and T-nuts: 470 supplier CAD, 156 re-made from a supplier drawing (the T-nuts), 23 generated to a standard (placeholders), 5 stand-ins (clinch nuts). |

## What is drawn now

| | v10 | v10.1 |
|---|---|---|
| Parts in the model | 578 | 825 |
| Fasteners with a driver-access check | 195 | 259 |
| T-nuts as parts | 0 | 156 |
| Corner-bracket screws as parts | 0 | 64 |
| Hardware lines on the BOM without geometry | 6 lines, 212 pieces (123 + 33 T-nuts, 64 bracket screws, 6 + 3 nyloc "upgrades", 5 PEM nuts, 1 serrated washer; the PEM nuts were also drawn, as hex nuts) | none |
| Washers | 159 | 186 (M2.5 to M5 now 0.1 mm thicker: the bought ones) |
| Corner bracket's simulation solid | filled prism | the casting as its CAD model has it: 3 mm legs, side webs, a 6 mm slot from 7.0 to 16.1 mm in each leg |

Each `add_screw(..., tnut=True)` now places `<screw>_tnut` in the slot of the extrusion the screw enters: its 8 mm body
against the underside of the slot's lips, its neck up in the opening, centred on the screw. This happens in designs that
set `design.tnut_style = "drop_in"`; older designs are unchanged and get one info saying their T-slot screws were not
checked.

## The slot and the T-nut: where the figures come from

`us.misumi-ec.com` became reachable during the work. Its product pages refuse automated requests, but the catalogue's PDF
pages are served, and two were fetched and are kept in `vendor_docs/`:

- `misumi_2019_US_2686_HFS5_extrusions_slot_details.pdf`: HFS5 series extrusions. "Slot Details (Common to All Series)":
  6 (opening), 2 (lip), 4 (lip underside to floor), 12 (T slot width). "Slot Bottom Details": a 120 degree V, 0.3 deep. The
  HFS5-2020 section: 20 square, 4-R1, centre hole 4.2; 0.5 kg/m, 183 mm2, Ix = Iy = 0.742 x 10^4 mm4.
- `misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf`: nuts for the HFS5 series. HNTAJ5: 10 (length), 8 (width), 3.2
  (overall height), 2.4 (height of the 8 mm body), 5.8 (width of the neck), thread M3 / M4 / M5 through. Reference
  tightening torque for M5 in these nuts: 6.8 N.m.

| What the screw-length verdicts depend on | Value | Status |
|---|---|---|
| Slot depth, face to floor | 6.0 mm (2 + 4) | READ from Misumi's catalogue drawing. No tolerance is given |
| Slot lip thickness | 2.0 mm | READ, same drawing |
| Slot opening / cavity width | 6.0 / 12.0 mm | READ, same drawing |
| T-nut overall height / body under the lips | 3.2 / 2.4 mm | READ from Misumi's drawing of HNTAJ5 |
| T-nut thread length | 3.2 mm | READ: the thread is drawn through the whole height |
| T-nut length / width / neck width | 10 / 8 / 5.8 mm | READ, same drawing |
| How the nut seats: body against the lips' underside, neck up in the opening, so its thread runs from 1.2 to 4.4 mm below the extrusion's face | | OUR READING of the catalogue's application sketch; the drawing does not say it in words |
| Tolerances of slot and nut | | NOT GIVEN on either drawing |
| That the extrusion bought is Misumi HFS5-2020, or has the same slot | | ASSUMED. The owner's decision names the class, not the make. Another make's 2020 slot-6 section on file (a community STEP, "B-type") is 5.3 mm deep with a 1.5 mm lip |
| Clearance kept between a screw's tip and the slot floor | 0.5 mm | DERIVED by us: screw length tolerance (ISO 4762, js15: +/-0.29 mm to 10 mm; recalled) plus washer and sheet thickness |
| Least thread in a T-nut | 0.5 d is an error; the nut's whole thread, or 0.8 d, raises no finding | DERIVED by us from standard nut heights (thin nut ISO 4035 about 0.5 d, recalled; hex nut ISO 4032 0.8 d). Misumi rates the M5 nut at 6.8 N.m on its own 3.2 mm (0.64 d) of thread, which is why a screw through the whole nut raises nothing |

All of these are in `mechloop/parts/vendor/tslot_2020_hardware.json`, and the interference verifier's metrics repeat them
(`interference.tslot_screws.assumed_dimensions`). The slot and nut geometry is data: put other figures in that file and
run verify again. The community DXF of the HFS5-2020 section that was already in the repository agrees with Misumi's
drawing on every dimension.

Is the T-nut a "faithful re-make" in the owner's sense? Every dimension on the drawing is in the model and no feature of
the model is un-dimensioned, so it is labelled one, with the drawing named. It is not a complete copy: the chamfers on the
body's edges, the leaf spring and a countersink ring round the hole are drawn in the catalogue without dimensions, and
were left out rather than guessed. If the owner counts that as a stand-in, the label is one line in
`mechloop/parts/tslot.py`. Either way Misumi's STEP is still wanted (`vendor_cad/inbox/TNUT-2020-M5.step`, `-M3.step`).

## The slot the model uses against the drawings

| | Simulation solid (`extrusion_2020`) | Misumi HFS5, catalogue drawing | B-type slot 6, community STEP (the viewer's picture) |
|---|---|---|---|
| Opening | 6.2 mm | 6.0 | 6.0 |
| Depth from the face | 5.0 mm, flat | 6.0 (6.3 in the centre V) | 5.3 (5.7 in a centre groove) |
| Lip | none: a plain rectangular slot | 2.0 mm | 1.5 mm |
| T cavity | none | 12.0 mm wide | 12.0 mm wide |

So the solid's slot is 1 mm shallower than Misumi's and has no lip. Two consequences. First, bottoming cannot be judged
from the solid: a screw 5.8 mm into the slot overlaps the solid by 16 mm3 and is still 0.2 mm off the real floor. Second,
the solid cannot say where a T-nut's thread starts. The solid was left alone (changing it would change every FEA result
and every older design); the real section is recorded beside it (`interfaces["slot"]`) and the checks use that. The
viewer's picture of the extrusion is still the community B-type section, which is not Misumi's: a stand-in.

On that other section (5.3 mm deep, 1.5 mm lip) 80 of v10.1's 156 T-slot screws would end closer than 0.5 mm to the floor:
the 64 bracket screws (0.3 mm), the 6 carriage-plate bolts (on it), the 8 Y motor and idler mount bolts and the 2 inlet
panel bolts. One grouped warning names them. It matters only if an extrusion with a shallower slot than Misumi's is bought.

## What the new checks found in v10

The tip must end at least 0.5 mm above the floor (so at most 5.5 mm below the extrusion's face) and have at least 0.5 d of
thread in the nut, whose thread runs from 1.2 to 4.4 mm below the face. For an M5 that means ending 3.7 to 5.5 mm down, and
4.4 mm or more to use the whole nut.

| Screws (count) | v10 | Depth in slot | Wrong because | v10.1 | Depth, thread |
|---|---|---|---|---|---|
| `z_deck_bolt_0..11` (12) | M5 x 10, 1 washer, 3.2 mm deck | 5.83 mm | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63 mm, whole nut |
| `x_motor_mount_bolt_0,1`, `x_idler_mount_bolt_0,1`, `x_tension_anchor_bolt_0,1` (6) | M5 x 10, 1 washer, 3.2 mm | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63, whole nut |
| `y_tension_anchor_bolt_0,1`, `y_tension_anchor_l_bolt_0,1` (4) | M5 x 10, 1 washer, 3.2 mm | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63, whole nut |
| `tray_bolt_0,1` (2) | M5 x 10, 1 washer, 3.2 mm tray | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63, whole nut |
| `y_motor_mount_bolt_0,1`, `y_motor_mount_l_bolt_0,1`, `y_idler_mount_bolt_0,1`, `y_idler_mount_l_bolt_0,1` (8) | M5 x 10, 1 washer, 1.9 mm stainless | 7.12 | **1.12 mm into the floor** | M5 x 8, 1 washer | 5.02, whole nut |
| `inlet_panel_bolt_0,1` (2) | M5 x 10, 1 washer, 2.5 mm panel | 6.46 | **0.46 mm into the floor** | M5 x 10, 2 washers | 5.26, whole nut |
| `earth_stud` (1) | M5 x 10, head 2 mm off the rail | 8.0 | **2.0 mm into the floor** | M5 x 6 on a drawn toothed washer and a 0.8 mm ring terminal | 4.60, whole nut |
| `nut_plate_bolt_0,1`, `nut_plate_fl_bolt_0,1`, `nut_plate_fr_bolt_0,1` (6) | M5 x 10, 1 washer, 6.35 mm plate | 2.65 | **1.45 mm of thread (0.29 d)** | M5 x 12, 1 washer | 4.55, whole nut |

The v10 columns are v10 as it was verified, with 1.0 mm M5 washers. The v10.1 columns have the washers that are bought,
1.1 mm, so each washer takes 0.1 mm more of the screw.

35 would have bottomed or come within the margin (24 + 8 + 2 + 1), 6 had too little thread: **41**. Eleven would have
stopped on the floor outright with the joint loose. The six nut-plate screws matter most: they hang the bed carrier from
its three lead-screw nuts, and v10 gave them less than a third of a diameter of thread (v10 made the nut plates 6.35 mm
thick and kept v9's screws).

The other 51 were right and are unchanged: 33 rail screws (M3 x 8), 6 carriage-plate bolts (M5 x 8, 5.3 mm down with the
bought washer), 6 Z motor post bolts (M5 x 70, 4.55 mm), 2 Y switch bracket bolts (M5 x 8, 4.61 mm), all through the whole
nut; and the 4 beam bolts (M5 x 10 through the 4.75 mm Y plate and a washer, 4.15 mm down), which have 2.95 mm of thread
(0.59 d) and stop 0.25 mm short of the nut's far side. Those four carry a warning (`tnut_thread_engagement_marginal`):
M5 x 12 with a second washer would use the whole nut. Left as v10 had them; the owner may prefer the change.

The interference check did not see any of this in v10 because `add_screw(threads_into=...)` allowed a screw to overlap the
part it threads into by its whole volume. For a T-slot screw that allowance is now only what the real slot is deeper than
the drawn one (1.0 mm of screw: 19.6 mm3 for an M5).

An earlier pass of this work, before Misumi's drawings could be read, used a guessed T-nut (4.4 mm high, thread counted
only behind the lip) and found 45 wrong, the 4 beam bolts among them. With the maker's figures it is 41.

## What the drawn hardware found beyond length

- **A washer does not fit under a corner-bracket screw.** The casting's legs have a 6 mm slot from 7.0 to 16.1 mm from the
  corner, between side webs 12 mm apart. Two cap-screw heads in one bracket clear each other, and each other's driver, only
  with no washer under them; with a washer under each, the heads collide inside the slots. So each leg has a bare M5 x 8
  head on the slot, 11.5 and 13.1 mm from the corner, heads 0.85 mm apart (at 12.5 mm the gap was 0.25 mm and closed in
  about 1 build in 15 in the tolerance simulation). The seat is 27 % of what the head has on a round hole: one grouped
  `screw_head_seat_too_small` warning for the 64. **The guideline "washers on slots" is not met at the brackets.** A
  flanged button-head screw (ISO 7380-2 M5 x 8) would meet it; the catalogue has none and it was not checked. Misumi's own
  brackets for this series (HBLFSN5, catalogue p.2692) have round 5.2 mm holes, which would also solve it; not adopted, the
  bracket is the community casting as before. A question for the owner.
- **The catalogue's corner bracket was wrong about its slot.** Its helper took the slot to run 4 to 19 mm (it used the CAD
  model's slot ends as the centres of the end radii). The CAD model says 7.0 to 16.1 mm. Corrected for designs that draw
  the bracket screws; older designs keep the old solid.
- **T-nut order.** A drop-in T-nut goes in through its slot's opening, and may arrive on its screw through the part that
  screw holds (how post-assembly nuts are used). With that, the assembly check finds an order for all 156. Without it
  there is none: each nut plate goes on before the carrier member above it, so a nut that had to be in the member's slot
  first could never be placed.

## Screws with a second washer

One washer on a 3.2 mm plate leaves two choices: M5 x 8, which ends 3.7 mm down with 2.5 mm of thread (0.505 d, a pass by
0.03 mm and not the whole nut), or M5 x 10, which ends 5.7 mm down, 0.3 mm from the floor. A second ISO 7089 washer under
an M5 x 10 (`add_screw(..., washer=True, washers=2)`) puts the tip 4.6 mm down, through the whole nut and 1.4 mm off the
floor. That is 26 screws (the deck, the X plates, the Y tension anchors, the tray, the inlet panel). Stacked washers are
not elegant; M5 x 8 with one washer is the alternative and passes by a hair. Listed as an open item.

## Other hardware that was BOM-only

| v10 | v10.1 |
|---|---|
| 5 PEM S-M3-1 clinch nuts: a BOM line, and also drawn as ISO 4032 hex nuts under another SKU | catalogue part `hex_nut("M3", "pem")`, SKU `NUT-PEM-S-M3-1`, one BOM line. Same solid as before (the plates' hex holes were drawn for it): a stand-in, PennEngineering's drawing was not read |
| 6 "NYLOC-M3-UPGRADE" lines for the nut keepers' bolts, drawn as plain hex nuts | drawn as the nylocs they are (1.6 mm taller) |
| 3 M2.5 nylocs for the nut pins, drawn as plain hex nuts | the drawn hex nut, thread-locked. The catalogue has no M2.5 nyloc; the pin's nut clamps a sleeve, so adhesive holds it. A change of locking method |
| 1 serrated washer under the earth stud | drawn: catalogue `washer_toothed("M5")`, DIN 6797 J sizes (recalled) |

Not drawn, and stated: the set screws inside the three bought pulleys' hubs (they come with the pulley; the completeness
check lists them), and the earth wire's ring terminal (an electrical BOM line; its tongue is taken as 0.8 mm in the earth
stud's stack).

## Supplier CAD batch (arrived 2026-11-18, folded in 2026-11-19)

McMaster's own STEP files and part numbers, collected for the owner and staged in
`vendor_cad/staging/supplier_2026-11-18/` with a report and a manifest. What was done with them:

| | |
|---|---|
| Promoted to `vendor_cad/inbox/` under the SKU (29 files) | 19 cap screw sizes, FHCS-M4x40, washers M2.5 / M3 / M4 / M5, nuts M2.5 / M3 / M4, the M3 nyloc, and the DIN 934 M5 nut as `NUT-M5-DIN934.step`. Each is now its part's detail model, aligned automatically, and passes the proxy check. Recorded per file in `vendor_cad/SOURCES.md` |
| McMaster numbers | corrected in `mechloop/parts/vendor/mcmaster_fasteners.json` from the report (30 SKUs). 91290A400 (M3 x 8) and 91290A500 (M3 x 12), which had been doubted, are McMaster's real numbers |
| Washers | the bought ones are 0.1 mm thicker than the catalogue had: M2.5 0.6, M3 0.6, M4 0.9, M5 1.1 mm. The catalogue's table now has these, for every design. In v10.1 every washered screw reaches 0.1 mm less far per washer; one nut position in the design file had 0.5 mm typed in and is now taken from the table |
| M5 hex nut | McMaster's 90591A260 is DIN 934, 4.0 mm high, not ISO 4032 (4.7 mm). The three M5 nuts (X and Y idler bolts) are now `hex_nut("M5", "din934")` |
| Partly threaded screws | M3 x 40 / 45 / 50 are threaded over 18 mm only; M5 x 30 / 35 / 70 are fully threaded although ISO 4762 would thread 22 mm. Both facts are on the catalogue parts (`interfaces["thread_length"]`) and the nut-on-plain-shank rule (practice FST-060) uses them. It finds nothing: every nut on those M3 screws sits on thread |
| M4 x 6 cap screw | 90128A208, zinc-plated (McMaster has no black-oxide M4 x 6); drawing only, its STEP is over 5 MB. The generated geometry stays, a stand-in |
| Large washers M3 (9 mm OD, 12 off) and M4 (12 mm OD, 3 off) | not sold by McMaster. Stand-ins, open item; nothing substituted |
| McMaster's 5 mm-slot extrusion, T-nuts, corner bracket | not used (owner's decision: standard 2020, 6 mm slot). Files left in `_DEVIATIONS/` |
| Probe, spring, inlet, pulleys, data sheets | left for the next revision |

A consequence of the thicker washers that was not asked for: the Y belt plane sits on two M5 washers beside each idler, so
it and the Y motor pulleys moved 0.2 mm outward (see the comparison table).

In the viewer, McMaster's screws would cost 8,000 to 29,000 triangles each (their thread is modelled) and the washers
2,500. A fastener over 1,500 triangles is therefore shown on the page as its ISO outline (screws) or its plain solid
(washers, nuts); its record says what the model is and that the picture is simplified. The STEP export and the drawings
use McMaster's files.

## Geometry of purchased parts: three states

| State | Parts | What |
|---|---|---|
| Supplier CAD | 476 | 470 fasteners (McMaster: 251 cap screws, 3 countersunk screws, 170 washers, 46 nuts) and the 6 parts that had it before (X and Y motors, Roto, Revo, power supply) |
| Faithful re-make from a named supplier drawing | 156 | the T-nuts (Misumi HNTAJ5, catalogue p.2717), with three un-dimensioned features left out |
| Stand-in: generated to a standard (placeholder) | 23 | 15 large washers, 4 M4 x 6 and 1 M5 x 6 cap screws, 1 toothed washer, the probe's 2 nuts |
| Stand-in: community CAD | 70 | extrusions, corner brackets, guide rails and blocks, and others as before |
| Stand-in: assumed dimensions or simulation solid only | 63 | 5 clinch nuts and 58 purchased parts that had no model before this revision |

788 purchased parts in all, and 37 made parts.

Every fastener and T-nut is a catalogue part with a stable SKU, so a STEP saved as `vendor_cad/inbox/<SKU>.step` replaces
its display model with no code change (`TNUT-2020-M5.step`, `WASHER-M3-LARGE.step`, `NUT-PEM-S-M3-1.step`...).
`vendor_cad/mcmaster_wanted.csv` lists all 39 hardware types with quantities, the McMaster number where there is one
(plain when read from McMaster's page, marked unverified otherwise, or "not sold by McMaster") and the state of the
geometry (regenerate with `tools/mcmaster_wanted.py`).

## v10 against v10.1

V10_TABLE

## Checker changes

1. **T-slot screw check** (`mechloop/verifiers/interference.py`, `_tslot_screws`; metrics `interference.tslot_screws`). For
   every screw into a T-nut: the T-nut is a part, sits under the lips on the screw's axis, its neck stands in the opening,
   it fits the cavity and stays inside the extrusion's length (`tnut_missing`, `tnut_misplaced`, `tnut_does_not_fit`,
   errors); the screw is on the slot's centre line (`screw_off_slot_centre`); its tip ends at least 0.5 mm above the slot
   floor (`screw_bottoms_in_slot`, error); it has at least 0.5 d of thread in the nut (`tnut_thread_engagement`, error;
   from 0.5 d to 0.8 d without passing the nut's whole thread is one grouped warning). Each error's hint names the
   standard length that fits the same stack, or says none does. The slot and the nut's thread come from data, and every
   other geometry in the data file is judged and reported beside the one used (`verdicts_by_geometry`).
   **Why 0.5 d, and why a warning above it:** the guidelines ask 1 d in steel, which no 2020 T-nut gives an M5 (Misumi's
   is 3.2 mm, 0.64 d), and the older rule exempted T-nuts entirely. A thin standard nut is about 0.5 d: less than that is
   an error. A screw through the whole nut uses it as its maker rates it (6.8 N.m for M5): no finding. In between, a
   warning. The 0.5 d limit is ours, not a maker's.
2. **No blanket overlap excuse** (`add_screw`): a T-slot screw may overlap its extrusion's solid only by what the real slot
   is deeper than the drawn one.
3. **Completeness** (`mechloop/verifiers/practice.py`, rule DG-06, errors): `hardware_bom_only`, `hardware_count_mismatch`,
   `tnut_not_drawn`, `tnut_without_screw`, `joint_without_fasteners`. No exceptions are built in; a waiver needs a written
   reason like any other.
4. **Assembly** (`mechloop/assembly/planner.py`, the assemblability verifier, the assembly simulation): a drop-in T-nut
   leaves its slot only through the opening, is swept 12 mm clear of it rather than out of the machine, and may pass the
   parts its own screw goes through. A T-nut step costs 6 s and needs no holding (spring-held).
5. **Corner brackets** (`add_corner_bracket`): legs on slots get real screws and T-nuts; the casting's slots as its CAD
   model has them; a screw position outside the slot is refused.
6. **Catalogue**: `tnut_2020` (Misumi HNTAJ5), `washer_toothed`, `hex_nut(standard="pem")`; generated display models for
   washers, nyloc nuts, countersunk screws and the probe's nuts where no supplier file exists; `add_screw(washers=2)`; the
   three states (`vendor_cad.model_state`); the fastener stack rows leave a T-nut out of the joint's parts; the bought
   washer thicknesses; McMaster numbers and thread lengths from the supplier batch.
7. **Build package and review data**: a "CAD in the model" column and a count by state in BOM.md; T-nuts attached to their
   screw's joint in the review data.
8. **Viewer export**: a light display mesh for fasteners whose supplier file is heavy; each part's state.
9. Tests: `tests/test_v10_1_support.py` (33 tests); four older tests updated for the bought washer thickness and for
   supplier files in the inbox.

## Unverified, assumed or not done

- The rows marked OUR READING, NOT GIVEN, ASSUMED and DERIVED in the slot and T-nut table.
- McMaster's numbers and files are as the supplier report gives them; this session fetched nothing from McMaster (login
  wall). The files were loaded, aligned and checked against the catalogue's dimensions, nothing more.
- Misumi: two catalogue pages were fetched as PDFs with the default client; product pages and CAD were refused and not
  pursued. The catalogue is the 2019 US edition; the current product page was not compared.
- ISO 7093 large washer sizes are from a distributor's table already in the repository; DIN 6797 and ISO 4035 are recalled.
- The clinch nuts are drawn as hex nuts.
- The flanged button-head screw and the Misumi bracket proposed for the corners are not in the catalogue and were not
  checked.
- No torque is stated for M3 screws in T-nuts (the catalogue gives M5 only), and the torque table still gives class
  values for every screw.
- The extrusion's own model: the simulation solid's slot and the viewer's community section are not Misumi's, and the
  catalogue's mass (0.45 kg/m) and second moment (6,900 mm4) were not changed to Misumi's (0.5 kg/m, 7,420 mm4).
- The T-nut's leaf spring and chamfers are not modelled; its fit along the slot's 45 degree walls is by its drawn
  rectangle only.
- v10's open items stand (docs/PRINTER_V10.md). One decision the owner has taken since is not acted on here: purchased
  parts at stock sizes with no cutting (v10's cut X rail and cut lead screws remain, for the next revision).

RUN_SECTION

## Questions for the owner

1. Corner brackets: bare cap-screw heads on the casting's slots (not to the guideline), flanged button-head screws, or
   Misumi's bracket with round holes?
2. Is the T-nut's re-make acceptable as "faithful" with its chamfers, leaf spring and countersink ring left out, or should
   it be called a stand-in until Misumi's STEP is in hand?
3. Is the extrusion Misumi HFS5-2020? If another make is bought, its slot depth decides up to 80 screw lengths.
4. Two washers under 26 M5 x 10 screws, or M5 x 8 with one washer (2.5 mm of thread, a pass by 0.03 mm)?
5. The four beam bolts: leave at 0.59 d, or M5 x 12 with a second washer?
6. Is thread locker on the nut pins' M2.5 nuts acceptable in place of nylocs?
7. The two large washer sizes McMaster does not sell (M3 9 mm OD, M4 12 mm OD): another supplier, or another size?
