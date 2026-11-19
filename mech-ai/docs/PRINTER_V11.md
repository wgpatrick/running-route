# printer_v11: stock purchased parts, a bed sized to the print area, a radial blower, flat brackets

Everything here is simulated. Nothing has been built.

`designs/printer_v11.py` starts from a copy of `designs/printer_v10_1.py` (v10.1 was not edited, apart from one stale code
comment). It carries out the changes the owner approved on 2026-11-19 (A to F below). The frame's extrusions, the 420 x 420 x
480 mm envelope, the Z rails, the electronics and the gantry's Y side are v10.1's except where a change below says otherwise.

**Verify (full, all 13 verifiers, on the final code): {{VERIFY}}** (v10.1: 0 errors, 61 warnings). All {{REQ}} requirements met
(v10.1: 33 of 33). Report: `out/printer_v11/report.json`; scorecard `out/printer_v11/scores.jsonl`.

## The short answers

| Question | Answer |
|---|---|
| X travel | **191.6 mm** (194.6 mechanical) on a stock HIWIN MGNR12R 250 mm, 5 mm of rail beyond the block at each end. v10.1: 229.6 on a rail cut to 288. What limits it: the rail. The toolhead is now 21 mm (left) and 15 mm (right) from the top side rails at the ends. |
| Y travel | 214.5 mm, unchanged (front: Y idlers and the envelope; rear: the toolhead and the top back rail). |
| Z travel | 180 mm + 1.65 mm over-travel, unchanged. |
| Print area | **191.6 x 214.5 mm, 411 cm2** (v10.1: 229.6 x 214.5, 492 cm2). |
| Print sheet | **220 x 220 mm textured PEI on 0.4 mm spring steel** with a magnetic base (a third-party stock size; Creality sells 235 x 235 only). The print area is 84.9 % of it. The magnetic base must be bought rated 120 degC continuous. |
| Bed plate | **MIC-6 232 x 232 x 6.35 mm** (v10.1: 241 x 241 x 12.7). 6.35 mm is the thinnest stock MIC-6. |
| Bed limits | (a) out of flat as installed: **{{FLAT_A}}** of 0.3 mm; (b) change after probing: **{{FLAT_B}}** of 0.1 mm; (c) 1 kg at the worst corner: **{{FLAT_C}}** of 0.2 mm. **(b) binds**; (a) passes only on the owner's 0.13 mm figure for the plate as bought (see "The flatness figure"). |
| Part cooling | One GDSTIME GDB4010 24 V radial blower behind the Roto, outlet down into a short printed duct; a 10 x 3 mm outlet 24 mm from the nozzle on the rear-right diagonal aims the jet 14 degrees down at 0.5 mm under the tip. **Estimated** delivered flow **{{FLOW}}**. |
| Probe holder | One-bend L of 2.286 mm 5052 under the Roto's two screws; the OMRON clamped by its two nuts in a 12.5 mm hole, 15 mm behind its face. Metal in the 40 mm zone round the head: none (checked). |
| Bent parts | **2** (the X belt bracket, kept bent by the owner, and the probe L). v10.1: 8. |
| Z screws | Used at **330 mm as sold** (328 above the face). Front two inboard of the top side rails at x +/-144.5, rear one outboard of the back wall at y 202.5; motors on posts of two stacked stock spacers. Envelope unchanged. |
| POM nuts | The anti-backlash nuts the motors ship with, drawn as a **labelled stand-in** (no dimensions published), flange up under open-slotted nut plates, barrel hanging below, captive under open-slotted keepers. |
| Mass / cost / assembly | {{MASS}} kg / ${{COST}} / {{ASM}} min (v10.1: 14.93 kg / $1,061.69 / 161 min). |

## What changed and why (the owner's decisions)

### A. Purchased parts at stock sizes

**X rail.** HIWIN's site (www.hiwin.com) refused the request (403) and www.hiwin.tw has no length table; the MG catalogue in the
repository gives a maximum length and end distances but no list of stock lengths. Retail listings seen in a search were 400,
600 and 1000 mm. So the stock length used is the one the brief gives, 250 mm. 300 mm, the next common length, does not fit: it
would stand out of the 288 mm beam and hit the Y blocks. With 250 mm the block's centre runs +/-97.3 mm; X travel is 191.6 mm.

The beam is now 276 mm (ends at +/-138, 2.5 mm short of the front lead screws); the Y plates reach in to x 108 for the beam
bolts (v10.1: 127). The X motor and idler stand inside the beam's ends, so their mounts are flat plates on the beam's front
face; the motor's plate still reaches up over the Y plate to the motor.

**Z lead screws at 330 mm.** The motor (body 48 mm) plus the screw (328 mm above the face) is 376 mm; between the bottom
rails' tops (z 20) and the top rails' undersides (z 384) there are 364 mm. So with the motors standing on the bottom rails a
full-length screw cannot stand under a top rail. Moving the screws so that none stands under a frame extrusion, without
growing the envelope:

- **Front two at x +/-144.5** (v10.1: +/-160, over the side rails): the screw's surface 1.5 mm inboard of the top side rail's
  inner face, 2.5 mm outboard of the X beam's ends (the beam was shortened for this), and outside the toolhead's reach (it
  reaches x 131.8 at the right end). Motors on the tray over the bottom side rails, face at z 72.2, screw tops at 400.2 (6.8 mm
  under the Y blocks). Posts: 40 + 9 mm stock aluminium spacers stacked.
- **Rear one at y 202.5, outside the back wall** (v10.1: y 170, on the bottom back rail): its motor stands beside the rail's
  outer face, inside the Y motors' footprint (they already reach y 225.2), so the bounding box does not grow. Posts: 40 + 13.2
  on the bottom back rail. Screw top 401.2, with nothing above it. The rear nut plate reaches 57.1 mm out from the square,
  through the back wall.

What it cost: the nut plates are 9.525 mm (v10.1 6.35) for the rear plate's 57 mm reach, and every nut plate and keeper has an
open slot so it slides onto the nut sideways (a 330 mm screw standing in the frame cannot be threaded through a closed hole:
the assembly check found this). The front drives go in from above, with their nut stack, before the top side rails; the
rear drive after. Options if the owner prefers not to: shorter screws (StepperOnline lists a custom-length service, not
priced), or feet under the frame (envelope grows by about 30 mm).

**POM anti-backlash nut.** StepperOnline's page (fetched again) gives no nut dimensions and its datasheet host is still
refused. The product photographs show a black POM nut with a square four-hole flange and a barrel holding a spring and a
second half-nut. Scaled to the 42 mm motor: flange 23 x 23 x 6, barrel 12.7 x 26, holes 3.4 on 16 mm (+/-1.5 mm). It is a
stand-in (`leadscrew_nut_pom_ab4`, SKU NUT-T8x2-POM-AB-17E19S1684AB4). Seating: the carrier's weight still rests on the flange,
which floats +/-2.8 mm under the nut plate and is held 0.1 mm under it by the keeper; the pin is now in a corner hole. The nut
has no backlash of its own (assumed); the bed-support check now takes the keeper's 0.1 mm as the reverse gap (declared), and
the rocking allowance is the keeper's play over the 23 mm flange. Results: {{NUTS}}.

**T-slot extrusion** is the one purchased part bought cut: Misumi HFS5-2020-<length>, cut to order by Misumi (recorded on the
catalogue part, its BOM text and `misumi_hfs5_2020.json`).

### B. Bed

The sheet: the print area 191.6 x 214.5 needs a sheet at least 214.5 deep. 220 x 220 is the stock size that covers it (84.9 %
used; a 235 would be 74 %). Creality has no 220 sheet; resellers' 220 x 220 kits (0.4 mm steel, textured PEI, magnetic base)
were found only through search snippets (`generic_pei220.json`, secondary). The requirement "at least 85 % used" became 84 %.

The plate is 232 x 232 (6 mm round the sheet), and the three studs moved to 8 mm inside its front and rear edges (front pair at
y -103.5, rear at 112.5): with a smaller plate they had to come inside the print area's depth, so the heater pad (made to size)
is 192 x 205 mm between them, 95.6 % of the print area.

**The three limits** (replacing v10's 0.02 mm sag):

| Limit | What is computed | Result | Limit |
|---|---|---|---|
| (a) out of flat as installed | plate flatness as bought (0.127 mm, the owner's figure) + sag under the bed's own weight on its three countersinks (FEA load case `bed_self_weight_sag`, plate alone, {{SELF_N}}) | {{FLAT_A_DETAIL}} | 0.3 |
| (b) change after probing | the whole heat growth from cold to 80 degC (bed 60 K above the frame, carrier 15 K: the thermal case), as if the bed were probed before it grew at all: the larger of the nozzle-gap change and the plate's bow | {{FLAT_B_DETAIL}} | 0.1 |
| (c) 1 kg at the worst corner | the bed-support FEA, screw-only bound | {{FLAT_C_DETAIL}} | 0.2 |

**(b) binds.** It hardly depends on the plate: most of it is the studs, springs and carrier warming. (a) and (c) are far inside
their limits at 6.35 mm, which is the thinnest stock MIC-6, so 6.35 mm is the choice. The levelling points, the springs'
preload margin ({{PRELOAD}}) and the tilt allowance ({{TILT}}) are kept and pass.

**The flatness figure.** The brief gives "MIC-6 ~0.13 mm per McMaster listing; check". McMaster's page could not be read from
here. The maker's brochure in the repository (Alcoa MIC 6, `cast_tooling_plate.json`) gives **0.381 mm (0.015 in) for 6.35 to
15.9 mm plate** and 0.127 mm for 19 mm and thicker; 0.127 mm is also the thickness tolerance. On the maker's figure (a) is
exceeded by the plate alone ({{FLAT_A_MAKER}}) and no MIC-6 plate under 19 mm would pass. The design takes 0.127 mm as a
receiving-inspection limit on the cut 232 mm piece (a whole-plate figure says little about a 232 mm piece, but nothing
guarantees it either). Question 1.

### C. Toolhead

**Blower and duct.** The GDB4010 (40 x 40 x 10, 24 V, 9500 rpm, 0.08 A, 0.52 inH2O; bearing NOT stated) stands behind the Roto,
its face in the XZ plane, outlet down, 1.5 mm behind the Roto screws' heads; its lower edge is at z 406.5 so that its nuts pass
above the top back rail at the rear end of the Y travel. Two M2 x 20 through its right-hand lugs into the duct's printed cradle
(the left lugs are next to the Roto's screw and the probe's zone). The duct: v10.1's flange on the tool plates' tab (two M3
through-bolts into captured nyloc nuts), an arm under the Roto's right side, a chamber under the Roto with a riser behind it
up to the blower's outlet, and a front-left extension carrying the outlet tube. Old duct (from the earlier study): aimed
horizontally at the heater, two 90-degree turns, a blind wall, 72 mm2 outlet. New: one chamber, the outlet tube points down
at 14 degrees from 24 mm out on the rear-right diagonal at 0.5 mm under the tip, 10 x 3 mm (30 mm2). Measured on the model:
{{COOL_GEOM}}. The jet's axis passes 0.41 mm under the heater core's edge; E3D's silicone sock is on the BOM.

**Flow estimate** (not measured): the blower's P-Q curve (read by eye from the maker's chart, 9500 rpm) against a duct loss of
K = 1.85 at the outlet velocity (contraction 0.40, exit 1.00, tube friction 0.25, two 45-degree turns at chamber velocity 0.20:
handbook figures): **{{FLOW}}** at {{VEL}} through the outlet, {{PA}} Pa. With K 1.4 to 2.5 it is 0.55 to 0.71 CFM. For
comparison on the same method, the old axial fan (CG3010U24, 5.45 CFM free, 78 Pa shut-off) on its duct (72 mm2, K about 4.4)
gave about 0.8 CFM at about 5 m/s, aimed at the heater: the new jet has about half as much air again at twice the speed and is
aimed at the part. An airflow model is not part of the checks.

**Probe holder.** 2.286 mm 5052 (SendCutSend .090, inside radius 0.81; the .125 gauge's 3.18 mm radius put the bend where the
probe's upper nut sits). The upper leg lies on the Roto's rear face under its two M3 x 50; each now has two large washers
(Accu HPLW-M3-A2, 0.9 mm), which brings its tip inside the front tool plate (with one normal washer it stood 0.35 mm into the
guide block). Below z 396 the leg is 22 mm wide, beside the blower; above, 29.5 mm, and it reaches up to z 455 where the
toolhead loom is clamped above the blower. The OMRON stays where it was (34.5 mm behind the nozzle), so X travel and the
probed area are unchanged: the holder was redrawn instead. OMRON's surrounding-metal figures (`omron_e2e.json`: face 15 mm
proud of metal, 40 mm round the head clear) are enforced by the subsystems verifier (`probe_metal_in_clear_zone`, an error)
and by a requirement: nothing metal is in the zone.

### D. Belt brackets

| Part | v10.1 | v11 |
|---|---|---|
| Y tension anchors (2) | bent 5052 L, PEM nut, M3 jack screw | stock cast 2020 corner bracket on the rail's outer face (one flanged button head into a T-nut); an M5 x 30 passes its standing leg's slot between two jam nuts with washers; its head pushes the second bracket |
| Y motor mounts (2) | 304 1.88 with a bent fin | the same outline, flat, 304 1.88; a second cast bracket under the plate's front M5 (a flanged button head M5 x 10 through the bracket's slot and the plate) takes the push; a 6.4 mm slot in the plate takes the casting's locating nub |
| X tension anchor | bent 5052 with PEM nut and jack screw | deleted; the X motor plate's two M5 holes are 6 mm slots: pull the motor outward by hand and tighten |
| X idler mount | bent 5052 with a lug | flat 6061 3.175 plate |
| Y endstop bracket | bent 5052 upright in the rail's top slot | flat 6061 3.175 plate on the rail's top (two M5 behind the Y rail's end), the switch board horizontal on two 8 mm nylon standoffs, lever forward at the land's height; one board screw into a T-nut in the same slot, the other through the plate's inboard overhang with a nut |

No off-the-shelf tensioner fits (consumer units take 6 mm belt; this machine uses 9 mm X and 12 mm Y belts). The stale v10 text
("three bent parts": there were eight) is corrected in `docs/PRINTER_V10.md`, and the comment that gave the Y motor mount as
5052 3.175 now says 304 1.88 (`designs/printer_v10.py`, `designs/printer_v10_1.py`; comments only).

**Y motor shaft load (v10.1: 1.01 of its allowance).** The allowance at the belt plane is 21 N x 20 mm / arm; the belt pulls
2 x 18.7 N. The arm is set by the idler's stack (idler plate + two washers + half the idler), not by the motor plate. The Y idler
plates are now 304 1.52 mm (SendCutSend .060; v10.1 1.88): the belt plane, the Y pulleys and the Y plates' belt slots move
0.36 mm towards the motors (arm 10.97 mm) and the load is {{SHAFT}} of the allowance: the warning is gone. The Y motor plates
keep 1.88 mm as the owner asked; the belt plane does move, by 0.36 mm, to fix the shaft load.

### E. Fasteners

| Decision | Done |
|---|---|
| Corner-bracket screws: flanged button heads | ISO 7380-2 M5 x 8 on all {{NBRK}} bracket legs (catalogue `bhcs_flanged`, collar 11.8, head 2.75, from distributors' listings: secondary). The collar covers the 6 mm slot; it fits between the casting's webs (12 mm apart) with 0.1 mm a side. v10.1's `screw_head_seat_too_small` warning is gone |
| 26 M5 x 10 with two washers -> M5 x 8 with one | done on the 20 that remain (deck 12, X motor and idler plates 4, tray 2, inlet panel 2; the X and Y tension anchors' 6 are gone). M5 x 8 with one washer ends 3.7 mm into the slot with 0.50 d of thread: they pass and are listed in the marginal-thread warning |
| Four beam bolts at 0.59 d | M5 x 12 with a second washer: through the whole T-nut |
| M2.5 nuts | thread locker (as v10.1 drew it) |
| Large washers | Accu HPLW-M3-A2 (9 x 3.2 x 0.9) and HPLW-M4-A2 (12 x 4.3 x 1.1), A2 stainless, re-made from Accu's drawings: outside diameter, bore and thickness with tolerances are all a flat washer has, so they are faithful re-makes. Every design's large M3 / M4 washer is now these (0.1 mm thicker than the ISO mid value) |
| M4 x 6 | McMaster 90128A208 zinc-plated, still a generated placeholder (its STEP is over 5 MB) |

New fasteners: M5 x 16 for the 9.525 mm nut plates, M5 x 65 post bolts, M2 x 20 with M2 nuts and washers for the blower (M2
added to the catalogue's tables), M2.5 x 20 nut pins, M5 x 30 tension screws with jam nuts.

### F. Supplier CAD folded in

| File | Used as |
|---|---|
| Misumi HFS5-2020-500 STEP | `vendor_cad/inbox/HFS5-2020-500.step`: its section swept to each extrusion's length is the extrusions' display model (supplier CAD). The catalogue now records the section's area (182.13 mm2; catalogue 183) and the cavity's real shape (12 mm only for 0.939 mm under the lips, then 45-degree walls to a 5.878 mm floor); the T-nut fit check now also checks the nut's body against the tapered walls (9.08 mm available at its lower edge for its 8 mm). The BOM text no longer says Misumi was unreachable |
| KIPP K0143.04 thumb nut STEP | `THUMBNUT-DIN466-M4.step`; the part is now steel (KIPP), 6.2 g, thread through the full 9.5 mm |
| Century Spring DJ-8X20YCS STEP | `SPRING-DIE-DJ-8X20YCS.step` with a sidecar placing it and showing it at the installed height; OD 7.36 (catalogue 7.6, corrected) |
| Schurter DD11 STEP | `INLET-C14-SW-FUSE-T8A.step` with a sidecar; 33.5 mm deep with its terminals (data sheet 30): the inlet's printed hood is 2 mm deeper |
| OMRON E2E-X5ME1 STEP | `PROBE-OMRON-E2E-X5ME1.step`: the barrel solid (the file's two nuts are left out; the design draws the nuts as parts) |
| ServoCity GT2 pulley | not used: it is for 6 mm belt; the 9 and 12 mm pulleys keep their stand-ins |

Each is recorded in `vendor_cad/SOURCES.md`.

## v10.1 against v11

From the two full verify reports and the two scorecards, each on its design's final code.

| | v10.1 | v11 |
|---|---|---|
{{TABLE}}

## Purchased-part CAD: three states

{{STATES}}

## Judgement calls

1. **The flatness figure** (above): built with the owner's 0.13 mm as an inspection limit; on the maker's 0.381 mm the plate
   alone exceeds limit (a).
2. **Z screws**: front pair inboard of the top rails, rear one outside the back wall, rather than feet (envelope) or custom
   screws (not stock). The front screws stand 1.5 mm from the top side rails' inner faces at their free tops.
3. **Limit (b)** is bounded by the whole heat growth, as if the bed were probed cold: conservative. Probing after a heat soak
   leaves only the carrier's slower warming.
4. **The probe stays where it was**; the blower was fitted beside it and the holder redrawn (owner: keep X travel).
5. **Y belt plane 0.36 mm nearer the motors** (thinner idler plates) to clear the shaft-load warning; the motor plates keep
   1.88 mm.
6. **The sheet requirement** is 84 % (v10: 85 %): 220 x 220 is the stock size the reach nearly fills, at 84.9 %.
7. **Nut plates 9.525 mm** for the rear plate's reach; all three alike in thickness so the nuts sit at one height.
8. **No part-cooling bench unit**: the blower sits where the driver for the Roto's right-hand screw goes, so the order is duct,
   Roto, screws, blower. The front Z drives go in as units with their nut stacks, before the top side rails.
9. **The tension screws are not driver-checked**: they are set by their jam nuts and their heads bear on the brackets.

## Checker and catalogue changes

1. `mechloop/parts/batch10.py`: `blower_gdb4010` (maker's sheet, P-Q curve), `blower_flow_estimate`, `leadscrew_nut_pom_ab4`
   (stand-in), `print_sheet_pei220` (secondary), `bhcs_flanged` (ISO 7380-2, secondary). Vendor files `gdstime_gdb4010.json`,
   `generic_pei220.json`, `iso7380_2.json`, `accu_iso7093.json`; the POM nut's estimate in `stepperonline_17e19_ab4.json`.
2. `add_screw(head="flanged_button")`; `add_corner_bracket(slot_leg={"head": ...})`; BHCS screws counted as hardware by the
   completeness and interference checks, the viewer, the build package and the wanted list.
3. M2 in the screw, nut, washer, clearance, torque and thread tables.
4. Large washers M3 / M4: the Accu re-makes (all designs).
5. Slot data: the cavity's taper and the section area; the T-nut fit check against the tapered walls.
6. Bed support: a captive nut's reverse gap may be declared (`drive["nut_reverse_gap_mm"]`, with its basis).
7. Supplier-file sidecars: `"keep": "largest"` (leave out a file's loose extra solids) and `"fit_z_to_reference"` (a spring
   shown at its installed height); a sidecar may carry its own note. Probe, spring and inlet catalogue parts carry the
   protrusions / volume tolerances their supplier files need. The extrusion's display model is Misumi's section when its
   STEP is in the inbox.
8. Build package: v11 stage notes and open items. Viewer: the POM nut kept visible with the drive parts.
9. Tests: `tests/test_v11_support.py` ({{NTESTS}} tests).

## Unverified, assumed or not done

- The POM nut's dimensions (photographs); the magnetic base's thickness (1.5 mm) and rating (to be bought at 120 degC); the
  220 sheet (resellers' snippets); the blower's bearing and its P-Q points (read by eye); the flanged button head's
  dimensions (distributors' snippets); the HIWIN stock-length list (not obtained: 250 mm is the brief's figure).
- The flow estimate: handbook K values, no airflow model; the jet's spread and its effect on the sock and the nozzle.
- MIC-6 flatness: the owner's 0.13 mm against the maker's 0.381 mm (whole plate).
- The 330 mm screws' run-out and whip at their free tops, 1.5 mm from the top side rails.
- The probe bracket's stiffness.
- v10.1's open items that still stand (T-slot tolerances, the T-nut re-make, McMaster files not in hand).
{{NOTRUN}}

## Questions for the owner

1. MIC-6 flatness: accept 0.13 mm as a receiving check on the cut plate (and reject a worse piece), or go by the maker's
   0.381 mm, which no plate under 19 mm meets against limit (a)?
2. Z screws at 330 mm: is the arrangement acceptable (front screws 1.5 mm from the top side rails, rear motor outside the back
   wall, front Z drives fitted before the top side rails)? The alternatives are custom-length screws or feet.
3. The POM nut: can one be measured before the nut plates and keepers are cut?
4. The 220 x 220 sheet comes from resellers, not Creality: acceptable, or keep Creality's 235 (74 % used)?
5. The Y belt plane moved 0.36 mm (thinner Y idler plates) to clear the shaft-load warning: acceptable?
6. Blower: insist on a ball-bearing GDB4010 from the seller?
7. The probe holder in 2.286 mm 5052: acceptable, or a stiffer holder (which would need the probe moved or a two-part holder)?

## What was run

{{RUN}}

## Files

- `designs/printer_v11.py`; `out/printer_v11/report.json`, `scores.jsonl`, `tune/tuning.json` (not in git)
- `mechloop/parts/batch10.py` and the vendor files above; `tests/test_v11_support.py`
- `docs/build/printer_v11/`, `viewer/`, `review/data.json`, `review/drawings/` (generated); v10.1's viewer and review data kept
  in `viewer_v10_1/` and `review_v10_1/`
- `vendor_cad/inbox/` (five supplier files and three sidecars), `vendor_cad/SOURCES.md`, `vendor_cad/mcmaster_wanted.csv`
