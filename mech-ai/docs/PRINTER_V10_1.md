# printer_v10_1: every fastener drawn, every T-slot screw checked for length

Everything here is simulated. Nothing has been built.

`designs/printer_v10_1.py` starts from a copy of `designs/printer_v10.py` (v10 was not edited). The owner's instruction was
"make sure all fasteners are in place", after finding by eye that T-nuts and corner-bracket screws were BOM lines without
geometry, that nothing checked a screw's length in a T-slot, and that half the toolhead's fasteners were bare stand-in
solids. During the work the owner added: supplier CAD is wanted for all hardware, and McMaster's files for most of the
fasteners arrived and were folded in (section "Supplier CAD batch").

The frame, envelope, travel, bed, cooling fan and duct, belt tension brackets and probe mount are v10's. No made part
changed shape (a test checks every made part's volume and bounding box against v10's). What changed is screws, washers,
nuts, and what the checkers look at.

VERIFY_SUMMARY

## The short answers

| Question | Answer |
|---|---|
| T-nuts drawn | **156** (123 M5, 33 M3), one per T-slot screw, each a part in its slot, in the BOM by SKU (`TNUT-2020-M5`, `TNUT-2020-M3`), visible in the viewer. v10: 0 drawn, 156 as BOM lines. |
| T-nut type | Drop-in (post-assembly insertion, spring-held), all 156. None has to be loaded from an extrusion's end. |
| Bracket screws drawn | **64** M5 x 8 cap screws, two per corner bracket (32 brackets), each with its T-nut. v10: 64 BOM lines "not drawn, access not checked". |
| What the T-nut model is | A **stand-in**. No supplier drawing could be fetched; its dimensions are one web-search snippet and three guesses (table below). |
| Slot geometry the model uses | The extrusion's simulation solid has a plain slot 6.2 mm wide and 5.0 mm deep, with no lips. Two community drawings on file say 6.0 mm deep with a 2.0 mm lip (Misumi HFS5 copy) and 5.3 mm deep with a 1.5 mm lip (B-type). Neither is a supplier's drawing. The checks use the first and report what fails on the second. |
| Screws that were wrong in v10 | **45 of 92** T-slot screws: 35 would have reached, or come within 0.5 mm of, the slot floor before clamping; 10 had under 0.5 d of thread in the nut. All corrected (list below). |
| The rail screws the owner asked about | M3 x 8 through the MGN12 rail: 4.5 mm into the slot, 2.5 mm (0.83 d) of thread behind a 2.0 mm lip, 1.5 mm off the floor. Under 1 d, as suspected; a full hex nut's height (0.8 d), so no finding. Unchanged. |
| Completeness | The new rule finds nothing in v10.1: 658 hardware parts drawn, no hardware on the BOM without geometry, no declared joint without its fasteners. On v10 it finds 6 BOM-only hardware lines (212 pieces) and 64 joints without fasteners. |
| Toolhead fasteners | Of the 50: **46 are McMaster's own CAD**, 2 (the probe's nuts) are generated from OMRON's drawing dimensions, 2 (clinch nuts) are stand-in solids. None is a bare simulation solid any more (v10: 26). |
| Machine-wide | Of 658 screws, nuts, washers and T-nuts: 474 supplier CAD, 23 generated to a standard (placeholders), 161 stand-ins with assumed dimensions (156 T-nuts, 5 clinch nuts). |
| Under McMaster's 5 mm-slot rail and T-nuts instead | No screw would bottom; 12 (nut plates, Z motor posts) would have 2.49 mm of thread where 2.5 mm is asked. Not adopted: the owner has to choose the slot system. |

## What is drawn now

| | v10 | v10.1 |
|---|---|---|
| Parts in the model | 578 | 829 |
| Fasteners with a driver-access check | 195 | 259 |
| T-nuts as parts | 0 | 156 |
| Corner-bracket screws as parts | 0 | 64 |
| Hardware lines on the BOM without geometry | 6 lines, 212 pieces (123 + 33 T-nuts, 64 bracket screws, 6 + 3 nyloc "upgrades", 5 PEM nuts, 1 serrated washer; the PEM nuts were also drawn, as hex nuts) | none |
| Washers | 159 | 190 (M2.5 to M5 now 0.1 mm thicker: the bought ones) |
| Corner bracket's simulation solid | filled prism | the casting as its CAD model has it: 3 mm legs, side webs, a 6 mm slot from 7.0 to 16.1 mm in each leg |

Each `add_screw(..., tnut=True)` now places `<screw>_tnut` in the slot of the extrusion the screw enters: its bearing face
against the underside of the slot's lips, centred on the screw, wings across the slot. This happens in designs that set
`design.tnut_style = "drop_in"`; older designs are unchanged and get one info saying their T-slot screws were not checked.

## The T-nut: a stand-in, and what is assumed

The owner's rule (docs/DESIGN_GUIDELINES.md, Purchased-part CAD) allows three states: supplier CAD, a faithful re-make from
a named supplier drawing, or a stand-in. The T-nut is a stand-in.

What was tried: Misumi's catalogue pages (several national sites), a Misumi spec sheet hosted by LulzBot, a 2020 profile
data sheet, and resellers' pages. Every host was refused by the session's network proxy, from both the shell and the page
fetcher. Web search returned snippets only. Nothing was worked around.

| Dimension the checks depend on | Value used | Status and source |
|---|---|---|
| Slot depth, face to floor | 6.0 mm | ASSUMED. Measured in `vendor_docs/hfs5-2020-profile.dxf`, a community copy of Misumi's HFS5-2020 section (thing_libutils repository). Not Misumi's drawing; no tolerance |
| Slot lip thickness | 2.0 mm | ASSUMED, same file |
| Slot opening / cavity width | 6.0 / 12.0 mm | ASSUMED, same file |
| Slot depth, other 2020 section on file | 5.3 mm | ASSUMED. Measured by probing `vendor_cad/profile_2020_slot6.step` (FreeCAD-library "B-Type Slot 6"), the file the viewer shows. A search snippet of a reseller's page (Motedis) gives 5.5 mm for B-type; unverified |
| Slot lip, other section | 1.5 mm | ASSUMED, same file |
| T-nut overall height | 4.4 mm | ASSUMED: a search snippet of one reseller's listing (electrokit.com, "T-nut drop-in for 2020 M5", 6 x 10.3 x 4.4 mm, marked discontinued). A second snippet gives 10 x 6 x 4 mm for a nut sold for M3 to M5 |
| T-nut span across the slot / width along it | 10.3 / 6.0 mm | ASSUMED, same snippet |
| T-nut neck (the part standing in the slot opening) | 1.0 mm | GUESSED. No source |
| T-nut thread length | 3.4 mm | GUESSED: thread is counted only in the body behind the lip |
| T-nut underside chamfers | 1.7 mm | GUESSED, so the stand-in clears the slot's 45 degree walls |
| M3 T-nut body | same as M5 | GUESSED |
| Clearance kept between a screw's tip and the slot floor | 0.5 mm | DERIVED by us: screw length tolerance (ISO 4762, js15: +/-0.29 mm to 10 mm; recalled) plus washer and sheet thickness |
| Least thread in a T-nut | 0.5 d error, 0.8 d no finding | DERIVED by us from standard nut heights (thin nut ISO 4035 about 0.5 d, recalled; hex nut ISO 4032 0.8 d). No T-nut maker's figure was read |

All of these are in `mechloop/parts/vendor/tslot_2020_hardware.json`, and the interference verifier's metrics repeat them
(`interference.tslot_screws.assumed_dimensions`). **The verdicts of the new checks are only as good as these figures.** With
a different lip or depth the same screws can pass or fail, so the check judges every screw against every geometry in
that file, not only the one used (next section). Measure the extrusion and the T-nut that are bought, put the figures in
the file, and run verify again: the slot and T-nut geometry is data, not constants in the code.

## Verdicts under each geometry on file

All 156 T-slot screws of v10.1, judged with the same two limits (0.5 mm off the floor, 0.5 d of thread).

| Geometry | Slot depth / lip | T-nut thread: starts below the face, length | Bottom (within 0.5 mm of the floor) | Under 0.5 d | 0.5 to 0.8 d | 0.8 d or more |
|---|---|---|---|---|---|---|
| **Used**: 2020 slot 6 (HFS5 community DXF), stand-in T-nut | 6.0 / 2.0 | 2.0, 3.4 (M3 and M5) | **0** | **0** | 123 | 33 |
| 2020 slot 6, B-type (community STEP), stand-in T-nut | 5.3 / 1.5 | 1.5, 3.4 | **84** | 0 | 39 | 33 |
| McMaster 5537T101 rail (5 mm slot) with McMaster's drop-in T-nuts 5278N42 / 5278N44, **measured** in the supplier's STEP files | 6.10 off the centre line (6.40 on it) / 1.8 | M3: 1.37, 4.45; M5: 2.06, 3.3 | **0** | **12** | 111 | 33 |

- B-type: the 84 are the 64 bracket screws (5.0 mm deep, 0.3 mm from that floor), the 6 carriage-plate bolts (5.3 mm: on the
  floor), the 4 beam bolts, the 8 Y motor and idler mount bolts and the 2 inlet panel bolts. One grouped warning names them.
- McMaster: the 12 are the 6 nut-plate bolts and the 6 Z motor post bolts, which end 4.55 mm below the face; McMaster's M5
  nut starts its thread 2.06 mm down, so they have 2.49 mm (0.498 d) where 2.5 mm is asked. A hair, and one washer fewer
  or a different plate would clear it; reported as an info because that system is not adopted. The 33 M3 rail screws would
  have 3.13 mm (1.04 d) in McMaster's M3 nut, whose thread runs the nut's full height.
- McMaster's figures are measurements of supplier CAD, but of a **different system**: a 5 mm slot opening (an M5 screw is
  exactly as wide), an 11.5 mm cavity, nuts 12.0 mm long along the slot and 7.7 mm across with the hole 2 to 3 mm off
  centre and a spring ball underneath. Nothing else in the design was checked against it (rails, plate holes, brackets,
  the nuts' length where two screws are close). The owner has to choose between it and the standard 6 mm slot; v10.1
  stays on the standard slot with the T-nuts as stand-ins.

## The slot the model uses against the drawings

| | Simulation solid (`extrusion_2020`) | HFS5-2020, community DXF | B-type slot 6, community STEP |
|---|---|---|---|
| Opening | 6.2 mm | 6.0 | 6.0 |
| Depth from the face | 5.0 mm, flat | 6.0 (6.3 in a centre groove) | 5.3 (5.7 in a centre groove) |
| Lip | none: a plain rectangular slot | 2.0 mm | 1.5 mm |
| T cavity | none | 12.0 mm wide, 45 degree walls | 12.0 mm wide, about 49 degree walls |

So the solid's slot is shallower than either drawing and has no lip. Two consequences. First, bottoming cannot be judged
from the solid: a screw 5.8 mm into the slot overlaps the solid by 16 mm3 and may or may not touch a real floor. Second,
the solid cannot say where a T-nut's thread starts. The solid was left alone (changing it would change every FEA result
and every older design); the real section is recorded beside it (`interfaces["slot"]`) and the checks use that.

## What the new checks found in v10

Judged with the figures above: the tip must end at least 0.5 mm above the floor and have at least 0.5 d of thread behind
the lip. For an M5 that is 4.5 to 5.5 mm below the extrusion's face; for an M3, 3.5 to 5.5 mm.

| Screws (count) | v10 | Depth in slot | Wrong because | v10.1 | Depth, thread |
|---|---|---|---|---|---|
| `z_deck_bolt_0..11` (12) | M5 x 10, 1 washer, 3.2 mm deck | 5.83 mm | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63 mm, 0.53 d |
| `x_motor_mount_bolt_0,1`, `x_idler_mount_bolt_0,1`, `x_tension_anchor_bolt_0,1` (6) | M5 x 10, 1 washer, 3.2 mm | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63, 0.53 d |
| `y_tension_anchor_bolt_0,1`, `y_tension_anchor_l_bolt_0,1` (4) | M5 x 10, 1 washer, 3.2 mm | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63, 0.53 d |
| `tray_bolt_0,1` (2) | M5 x 10, 1 washer, 3.2 mm tray | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.63, 0.53 d |
| `y_motor_mount_bolt_0,1`, `y_motor_mount_l_bolt_0,1`, `y_idler_mount_bolt_0,1`, `y_idler_mount_l_bolt_0,1` (8) | M5 x 10, 1 washer, 1.9 mm stainless | 7.12 | **1.12 mm into the floor** | M5 x 8, 1 washer | 5.02, 0.60 d |
| `inlet_panel_bolt_0,1` (2) | M5 x 10, 1 washer, 2.5 mm panel | 6.46 | **0.46 mm into the floor** | M5 x 10, 2 washers | 5.26, 0.65 d |
| `earth_stud` (1) | M5 x 10, head 2 mm off the rail | 8.0 | **2.0 mm into the floor** | M5 x 6 on a drawn toothed washer and a 0.8 mm ring terminal | 4.60, 0.52 d |
| `nut_plate_bolt_0,1`, `nut_plate_fl_bolt_0,1`, `nut_plate_fr_bolt_0,1` (6) | M5 x 10, 1 washer, 6.35 mm plate | 2.65 | **0.65 mm of thread (0.13 d)** | M5 x 12, 1 washer | 4.55, 0.51 d |
| `beam_bolt_left`, `_left_1`, `_right`, `_right_1` (4) | M5 x 10, 1 washer, 4.75 mm Y plate | 4.25 | 2.25 mm of thread (0.45 d) | M5 x 12, 2 washers | 5.05, 0.61 d |

The v10 columns are v10 as it was verified, with 1.0 mm M5 washers. The v10.1 columns have the washers that are bought,
1.1 mm, so each washer takes 0.1 mm more of the screw.

35 would have bottomed or come within the margin (24 + 8 + 2 + 1), 10 had too little thread (6 + 4): **45**. Eleven of them
would have stopped on the floor outright with the joint loose. The six nut-plate screws are the ones that matter most:
they hang the bed carrier from its three lead-screw nuts, and v10 gave them two thirds of a millimetre of thread (v10 made
the nut plates 6.35 mm thick and kept v9's screws).

The other 47 were right and are unchanged: 33 rail screws (M3 x 8), 6 carriage-plate bolts (M5 x 8; 5.3 mm, 0.66 d with
the bought washer), 6 Z motor post bolts (M5 x 70; 4.55 mm, 0.51 d), 2 Y switch bracket bolts (M5 x 8; 4.61 mm, 0.52 d).
The nut-plate and post bolts sit 0.05 mm above the lower limit: any more stack and they need the next length.

The interference check did not see any of this in v10 because `add_screw(threads_into=...)` allowed a screw to overlap the
part it threads into by its whole volume. For a T-slot screw that allowance is now only what the real slot is deeper than
the drawn one (1.0 mm of screw: 19.6 mm3 for an M5).

## What the drawn hardware found beyond length

- **A washer does not fit under a corner-bracket screw.** The casting's legs have a 6 mm slot from 7.0 to 16.1 mm from the
  corner, between side webs 12 mm apart. Two cap-screw heads in one bracket clear each other, and each other's driver, only
  with no washer under them; with one washer the heads collide inside the slots, and the screw is then either too short
  (M5 x 8: 0.4 d) or bottoms (M5 x 10). So each leg has a bare M5 x 8 head on the slot, 11.5 and 13.1 mm from the corner,
  heads 0.85 mm apart (at 12.5 mm the gap was 0.25 mm and closed in about 1 build in 15 in the tolerance simulation). The
  seat is 27 % of what the head has on a round hole: one grouped `screw_head_seat_too_small` warning for the 64. **The
  guideline "washers on slots" is not met at the brackets.** A flanged button-head screw (ISO 7380-2 M5 x 8) would meet it;
  the catalogue has none and it was not checked. This is a question for the owner.
- **The catalogue's corner bracket was wrong about its slot.** Its helper took the slot to run 4 to 19 mm (it used the CAD
  model's slot ends as the centres of the end radii). The CAD model says 7.0 to 16.1 mm. Corrected for designs that draw
  the bracket screws; older designs keep the old solid.
- **M5 screws in a 2020 T-nut cannot have a full nut's thread.** With a 2.0 mm lip and a 6.0 mm slot the most is 3.5 mm
  (0.7 d). All 123 M5 T-slot screws are between 0.51 d and 0.66 d: one grouped warning. The class torque (6.5 N.m for M5)
  assumes a full nut; a reduced torque should be stated for these joints. Not resolved here.
- **T-nut order.** A drop-in T-nut goes in through its slot's opening, and may arrive on its screw through the part that
  screw holds (how such nuts are used). With that, the assembly check finds an order for all 156. Without it there is
  none: each nut plate goes on before the carrier member above it, so a nut that had to be in the member's slot first
  could never be placed.

## Screws that needed a second washer

One washer on a 3.2 mm plate leaves no standard M5 length in the 4.5 to 5.5 mm window (M5 x 8 gives 3.7 mm, M5 x 10 gives
5.7 mm). A second ISO 7089 washer under the head (`add_screw(..., washer=True, washers=2)`) sets it to 4.6 mm. That is 30
screws: the 26 on 3.2 mm and 2.5 mm plates above, and the 4 beam bolts. Stacked washers are not elegant; a single 2 mm
washer (DIN 7349) would do the same and is not in the catalogue. Listed as an open item.

## Other hardware that was BOM-only

| v10 | v10.1 |
|---|---|
| 5 PEM S-M3-1 clinch nuts: a BOM line, and also drawn as ISO 4032 hex nuts under another SKU | catalogue part `hex_nut("M3", "pem")`, SKU `NUT-PEM-S-M3-1`, one BOM line. Same solid as before (the plates' hex holes were drawn for it): a stand-in, PennEngineering's drawing was not read |
| 6 "NYLOC-M3-UPGRADE" lines for the nut keepers' bolts, drawn as plain hex nuts | drawn as the ISO 10511 nylocs they are (1.6 mm taller) |
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
| McMaster numbers | corrected in `mechloop/parts/vendor/mcmaster_fasteners.json` from the report (30 SKUs). 91290A400 (M3 x 8) and 91290A500 (M3 x 12), which an earlier draft of this document called suspect, are McMaster's real numbers |
| Washers | the bought ones are 0.1 mm thicker than the catalogue had: M2.5 0.6, M3 0.6, M4 0.9, M5 1.1 mm. The catalogue's table now has these, for every design. In v10.1 every washered screw reaches 0.1 mm less far per washer (the tables above have the new figures); one nut position in the design file had 0.5 mm typed in and is now taken from the table |
| M5 hex nut | McMaster's 90591A260 is DIN 934, 4.0 mm high, not ISO 4032 (4.7 mm). The three M5 nuts (X and Y idler bolts) are now `hex_nut("M5", "din934")` |
| Partly threaded screws | M3 x 40 / 45 / 50 are threaded over 18 mm only; M5 x 30 / 35 / 70 are fully threaded although ISO 4762 would thread 22 mm. Both facts are on the catalogue parts (`interfaces["thread_length"]`) and the nut-on-plain-shank rule (practice FST-060) uses them. It finds nothing: every nut on those M3 screws sits on thread |
| M4 x 6 cap screw | 90128A208, zinc-plated (McMaster has no black-oxide M4 x 6); drawing only, its STEP is over 5 MB. The generated geometry stays, marked as a stand-in |
| Large washers M3 (9 mm OD, 12 off) and M4 (12 mm OD, 3 off) | not sold by McMaster. Stand-ins, open item; nothing substituted |
| McMaster's 5 mm-slot extrusion, T-nuts, corner bracket | NOT adopted. Their measured dimensions are in `tslot_2020_hardware.json` as a geometry the screw check reports against (table above) |
| Probe, spring, inlet, pulleys, data sheets | left for the next revision |

A consequence of the thicker washers that was not asked for: the Y belt plane sits on two M5 washers beside each idler, so
it and the Y motor pulleys moved 0.2 mm outward. See "Verify" for whether that shows.

In the viewer, McMaster's screws would cost 8,000 to 29,000 triangles each (their thread is modelled) and the washers
2,500. A fastener over 1,500 triangles is therefore shown on the page as its ISO outline (screws) or its plain solid
(washers, nuts); its record says what the model is and that the picture is simplified. The STEP export and the drawings
use McMaster's files.

## Geometry of purchased parts: three states

| State | Parts | What |
|---|---|---|
| Supplier CAD | 480 | 474 fasteners (McMaster: 251 cap screws, 3 countersunk screws, 174 washers, 46 nuts) and the 6 parts that had it before (X and Y motors, Roto, Revo, power supply) |
| Faithful re-make from a named supplier drawing | 0 | |
| Stand-in: generated to a standard (placeholder) | 23 | 15 large washers, 4 M4 x 6 and 1 M5 x 6 cap screws, 1 toothed washer, the probe's 2 nuts |
| Stand-in: community CAD | 70 | extrusions, corner brackets, guide rails and blocks, and others as before |
| Stand-in: assumed dimensions or simulation solid only | 219 | the 156 T-nuts, 5 clinch nuts, and 58 purchased parts that had no model before this revision |

792 purchased parts in all (and 37 made parts). Of the 658 screws, nuts, washers and T-nuts: 474 supplier CAD, 23
generated to a standard, 161 stand-ins with assumed dimensions. Every one is a catalogue part with a stable SKU, so a STEP
saved as `vendor_cad/inbox/<SKU>.step` replaces its display model with no code change (`TNUT-2020-M5.step`,
`WASHER-M3-LARGE.step`, `NUT-PEM-S-M3-1.step`...). `vendor_cad/mcmaster_wanted.csv` lists all 39 hardware types with
quantities, the McMaster number where there is one (plain when read from McMaster's page, marked unverified otherwise, or
"not sold by McMaster") and the state of the geometry (regenerate with `tools/mcmaster_wanted.py`).

## v10 against v10.1

V10_TABLE

## Checker changes

1. **T-slot screw check** (`mechloop/verifiers/interference.py`, `_tslot_screws`; metrics `interference.tslot_screws`). For
   every screw into a T-nut: the T-nut is a part, sits under the lips on the screw's axis, passes the opening, fits the
   cavity and stays inside the extrusion's length (`tnut_missing`, `tnut_misplaced`, `tnut_does_not_fit`, errors); the
   screw is on the slot's centre line (`screw_off_slot_centre`); its tip ends at least 0.5 mm above the slot floor
   (`screw_bottoms_in_slot`, error); it has at least 0.5 d of thread in the nut (`tnut_thread_engagement`, error; 0.5 d to
   0.8 d is one grouped warning). Each error's hint names the standard length that fits the same stack, or says none does.
   **Why 0.5 d and 0.8 d:** the guidelines ask 1 d in steel, which a 4.4 mm T-nut cannot give an M5 at all, and the older
   rule exempted T-nuts entirely. A thin standard nut is about 0.5 d and a full one 0.8 d, so less than a thin nut is an
   error and less than a full nut is a warning. Both limits are ours, not a maker's.
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
6. **Catalogue**: `tnut_2020`, `washer_toothed`, `hex_nut(standard="pem")`; generated display models for washers, nyloc
   nuts, countersunk screws and the probe's nuts where no supplier file exists; `add_screw(washers=2)`; the three states
   (`vendor_cad.model_state`); the fastener stack rows leave a T-nut out of the joint's parts; the bought washer
   thicknesses; McMaster numbers and thread lengths from the supplier batch.
   The T-slot check takes its slot and T-nut geometry from `tslot_2020_hardware.json` and reports every geometry there
   (`interference.tslot_screws.verdicts_by_geometry`).
7. **Build package and review data**: a "CAD in the model" column and a count by state in BOM.md; T-nuts attached to their
   screw's joint in the review data.
8. Viewer export: a light display mesh for fasteners whose supplier file is heavy.
9. Tests: `tests/test_v10_1_support.py` (34 tests); four older tests updated for the bought washer thickness and for
   supplier files in the inbox.

## Unverified, assumed or not done

- Every figure in the T-nut and slot table above.
- McMaster's numbers and files are as the supplier report gives them; this session fetched nothing from McMaster (login
  wall). The files were loaded, aligned and checked against the catalogue's dimensions, nothing more.
- ISO 7093 large washer sizes are from a distributor's table already in the repository; DIN 6797 and ISO 4035 are recalled.
- McMaster's slot and T-nut figures are the staging manifest's measurements of the STEP files; they were not re-measured.
- The clinch nuts are drawn as hex nuts.
- The flanged button-head screw proposed for the brackets is not in the catalogue and was not checked.
- The reduced torque for M5 screws in T-nuts is not set: the torque table still gives the class value.
- The two-washer stacks were not compared with a single thick washer.
- The T-nut's flanks against the slot's walls are not checked (the stand-in is drawn to clear them).
- v10's open items stand (docs/PRINTER_V10.md). One decision the owner has taken since is not acted on here: purchased
  parts at stock sizes with no cutting (v10's cut X rail and cut lead screws remain, for the next revision).

## Questions for the owner

1. Corner brackets: bare cap-screw heads on the casting's slots (not to the guideline), flanged button-head screws, or a
   bracket with round holes?
2. Which slot system: standard 2020 (6 mm slot) or McMaster's 20 mm rail (5 mm slot) with its T-nuts and bracket? And for
   the standard one, which extrusion and T-nut: their slot depth, lip and thread length decide up to 84 screw lengths.
3. Two washers under 30 screws, or one 2 mm washer?
4. Is thread locker on the nut pins' M2.5 nuts acceptable in place of nylocs?
5. What torque for M5 screws in T-nuts?
6. The two large washer sizes McMaster does not sell (M3 9 mm OD, M4 12 mm OD): another supplier, or another size?
