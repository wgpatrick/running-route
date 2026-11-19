# printer_v10_1: every fastener drawn, every T-slot screw checked for length

Everything here is simulated. Nothing has been built.

`designs/printer_v10_1.py` starts from a copy of `designs/printer_v10.py` (v10 was not edited). The owner's instruction was
"make sure all fasteners are in place", after finding by eye that T-nuts and corner-bracket screws were BOM lines without
geometry, that nothing checked a screw's length in a T-slot, and that half the toolhead's fasteners were bare stand-in
solids.

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
| Toolhead fasteners | All 50 have generated geometry now: 48 to their standard (ISO 4762, 4032, 7089, 10511; OMRON's drawing for the probe's two nuts), 2 clinch nuts as stand-in solids. None is supplier CAD: all 50 are placeholders. |
| Machine-wide | The same fix is in the catalogue, so every washer (ISO 7089 / 7093), nyloc nut and countersunk screw in the machine has generated geometry. |

## What is drawn now

| | v10 | v10.1 |
|---|---|---|
| Parts in the model | 578 | 829 |
| Fasteners with a driver-access check | 195 | 259 |
| T-nuts as parts | 0 | 156 |
| Corner-bracket screws as parts | 0 | 64 |
| Hardware lines on the BOM without geometry | 6 lines, 212 pieces (123 + 33 T-nuts, 64 bracket screws, 6 + 3 nyloc "upgrades", 5 PEM nuts, 1 serrated washer; the PEM nuts were also drawn, as hex nuts) | none |
| Washers | 159 | 190 |
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
| Slot depth, other section on file | 5.3 mm | ASSUMED. Measured by probing `vendor_cad/profile_2020_slot6.step` (FreeCAD-library "B-Type Slot 6"), the file the viewer shows. A search snippet of a reseller's page (Motedis) gives 5.5 mm for B-type; unverified |
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
a different lip or depth the same screws can pass or fail: 108 of the 156 pass on the section used and would end closer
than 0.5 mm to the floor of the other section on file (one grouped warning, `tslot_profile_sensitive`, names them). Measure
the extrusion and the T-nut that are bought, put the figures in that file, and run verify again.

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
| `z_deck_bolt_0..11` (12) | M5 x 10, 1 washer, 3.2 mm deck | 5.83 mm | 0.17 mm from the floor | M5 x 10, 2 washers | 4.83 mm, 0.57 d |
| `x_motor_mount_bolt_0,1`, `x_idler_mount_bolt_0,1`, `x_tension_anchor_bolt_0,1` (6) | M5 x 10, 1 washer, 3.2 mm | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.83, 0.57 d |
| `y_tension_anchor_bolt_0,1`, `y_tension_anchor_l_bolt_0,1` (4) | M5 x 10, 1 washer, 3.2 mm | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.83, 0.57 d |
| `tray_bolt_0,1` (2) | M5 x 10, 1 washer, 3.2 mm tray | 5.83 | 0.17 mm from the floor | M5 x 10, 2 washers | 4.83, 0.57 d |
| `y_motor_mount_bolt_0,1`, `y_motor_mount_l_bolt_0,1`, `y_idler_mount_bolt_0,1`, `y_idler_mount_l_bolt_0,1` (8) | M5 x 10, 1 washer, 1.9 mm stainless | 7.12 | **1.12 mm into the floor** | M5 x 8, 1 washer | 5.12, 0.62 d |
| `inlet_panel_bolt_0,1` (2) | M5 x 10, 1 washer, 2.5 mm panel | 6.46 | **0.46 mm into the floor** | M5 x 10, 2 washers | 5.46, 0.68 d |
| `earth_stud` (1) | M5 x 10, head 2 mm off the rail | 8.0 | **2.0 mm into the floor** | M5 x 6 on a drawn toothed washer and a 0.8 mm ring terminal | 4.6, 0.52 d |
| `nut_plate_bolt_0,1`, `nut_plate_fl_bolt_0,1`, `nut_plate_fr_bolt_0,1` (6) | M5 x 10, 1 washer, 6.35 mm plate | 2.65 | **0.65 mm of thread (0.13 d)** | M5 x 12, 1 washer | 4.65, 0.53 d |
| `beam_bolt_left`, `_left_1`, `_right`, `_right_1` (4) | M5 x 10, 1 washer, 4.75 mm Y plate | 4.25 | 2.25 mm of thread (0.45 d) | M5 x 12, 2 washers | 5.25, 0.65 d |

35 would have bottomed or come within the margin (24 + 8 + 2 + 1), 10 had too little thread (6 + 4): **45**. Eleven of them
would have stopped on the floor outright with the joint loose. The six nut-plate screws are the ones that matter most:
they hang the bed carrier from its three lead-screw nuts, and v10 gave them two thirds of a millimetre of thread (v10 made
the nut plates 6.35 mm thick and kept v9's screws).

The other 47 were right and are unchanged: 33 rail screws (M3 x 8), 6 carriage-plate bolts (M5 x 8, 5.4 mm, 0.68 d), 6 Z
motor post bolts (M5 x 70, 4.65 mm, 0.53 d), 2 Y switch bracket bolts (M5 x 8, 4.71 mm, 0.54 d).

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
  (0.7 d). All 123 M5 T-slot screws are between 0.52 d and 0.70 d: one grouped warning. The class torque (6.5 N.m for M5)
  assumes a full nut; a reduced torque should be stated for these joints. Not resolved here.
- **T-nut order.** A drop-in T-nut goes in through its slot's opening, and may arrive on its screw through the part that
  screw holds (how such nuts are used). With that, the assembly check finds an order for all 156. Without it there is
  none: each nut plate goes on before the carrier member above it, so a nut that had to be in the member's slot first
  could never be placed.

## Screws that needed a second washer

One washer on a 3.2 mm plate leaves no standard M5 length in the 4.5 to 5.5 mm window (M5 x 8 gives 3.8 mm, M5 x 10 gives
5.8 mm). A second ISO 7089 washer under the head (`add_screw(..., washer=True, washers=2)`) sets it to 4.8 mm. That is 30
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

## Geometry of purchased parts: three states

| State | Parts | What |
|---|---|---|
| Supplier CAD | 6 | X and Y motors, Roto, Revo, power supply (as recorded before this revision) |
| Faithful re-make from a named supplier drawing | 0 | |
| Stand-in: generated to a standard | 497 | 256 cap screws (ISO 4762), 190 washers (ISO 7089 / 7093, DIN 6797), 46 hex and nyloc nuts, 3 countersunk screws, 2 probe nuts. Placeholders until the supplier's STEP is in `vendor_cad/inbox/` |
| Stand-in: community CAD | 70 | extrusions, corner brackets, guide rails and blocks, and others as before |
| Stand-in: assumed dimensions or simulation solid only | 219 | the 156 T-nuts, 5 clinch nuts, and the purchased parts that had no model before this revision |

Of the 658 screws, nuts, washers and T-nuts, 497 are generated to a standard and 161 are stand-in solids (the T-nuts and
clinch nuts). None is supplier CAD. Every one is a catalogue part with a stable SKU, so a STEP saved as
`vendor_cad/inbox/<SKU>.step` replaces its display model with no code change (`TNUT-2020-M5.step`, `WASHER-M5.step`,
`NUT-M3-NYLOC.step`, `NUT-PEM-S-M3-1.step`...). `vendor_cad/mcmaster_wanted.csv` lists all 39 hardware types with quantities
(regenerate with `tools/mcmaster_wanted.py`). Every McMaster number in it is marked unverified: none was ever checked on
McMaster's pages, and 91290A400 (M3 x 8) and 91290A500 (M3 x 12) do not fit the series' numbering.

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
6. **Catalogue**: `tnut_2020`, `washer_toothed`, `hex_nut(standard="pem")`; display models for washers, nyloc nuts,
   countersunk screws and the probe's nuts; `add_screw(washers=2)`; the three states (`vendor_cad.model_state`); the
   fastener stack rows leave a T-nut out of the joint's parts.
7. **Build package and review data**: a "CAD in the model" column and a count by state in BOM.md; T-nuts attached to their
   screw's joint in the review data.
8. Tests: `tests/test_v10_1_support.py` (31 tests).

## Unverified, assumed or not done

- Every figure in the T-nut and slot table above.
- No McMaster part number. McMaster's site shows a login wall; nothing was fetched from it.
- ISO 7089 / 7093 washer sizes are from a distributor's table already in the repository; DIN 6797, ISO 10511 heights and
  ISO 4035 are recalled.
- The nyloc's collar diameter in its display model is a guess (0.9 x across flats).
- The clinch nuts are drawn as hex nuts.
- The flanged button-head screw proposed for the brackets is not in the catalogue and was not checked.
- The reduced torque for M5 screws in T-nuts is not set: the torque table still gives the class value.
- The two-washer stacks were not compared with a single thick washer.
- The T-nut's flanks against the slot's walls are not checked (the stand-in is drawn to clear them).
- v10's open items stand (docs/PRINTER_V10.md). Two decisions the owner has taken since are not acted on here: purchased
  parts at stock sizes with no cutting (v10's cut X rail and cut lead screws remain), and supplier CAD for all hardware.

## Questions for the owner

1. Corner brackets: bare cap-screw heads on the casting's slots (not to the guideline), flanged button-head screws, or a
   bracket with round holes?
2. Which extrusion and which T-nut will be bought? Their slot depth, lip and nut thread length decide 108 screw lengths.
3. Two washers under 30 screws, or one 2 mm washer?
4. Is thread locker on the nut pins' M2.5 nuts acceptable in place of nylocs?
5. What torque for M5 screws in T-nuts?
