# printer_v11: stock purchased parts, a bed sized to the print area, a radial blower, flat brackets

Everything here is simulated. Nothing has been built.

`designs/printer_v11.py` starts from a copy of `designs/printer_v10_1.py` (v10.1 was not edited, apart from one stale code
comment). It carries out the changes the owner approved on 2026-11-19 (A to F below; the blower and probe changes the owner made
later the same day are in C; G and H are the two new checks). The frame's extrusions, the 420 x 420 x
480 mm envelope, the Z rails, the electronics and the gantry's Y side are v10.1's except where a change below says otherwise.

**Verify (all 13 verifiers, on the final code, 2026-11-20 07:20): FAILS, 118 errors, 142 warnings** (v10.1: 0 errors, 61
warnings). The errors: **116 are the new DG-07 purchased-part rule** (section H; v11.1's work, not fixed here by instruction),
**1 is the FEA thermal case** (`thermal_gap_change`, -0.101 mm against 0.1) and **1 is its requirement, limit (b)** (section B).
Every other verifier passes. **39 of 40 requirements met** (v10.1: 33 of 33). Report: `out/printer_v11/report.json`; scorecard `out/printer_v11/scores.jsonl`.

## The short answers

| Question | Answer |
|---|---|
| X travel | **191.6 mm** (194.6 mechanical) on a stock HIWIN MGNR12R 250 mm, 5 mm of rail beyond the block at each end. v10.1: 229.6 on a rail cut to 288. What limits it: the rail. Below the top side rails' top the toolhead is 21.0 mm (left, the Roto) and 19.7 mm (right, the duct) from them at the ends of the mechanical travel; the Delta blower passes 10.5 mm above the right rail. The blower swap did not change X travel. |
| Y travel | 214.5 mm, unchanged (front: Y idlers and the envelope; rear: the toolhead and the top back rail). |
| Z travel | 180 mm + 1.65 mm over-travel, unchanged. |
| Print area | **191.6 x 214.5 mm, 411 cm2** (v10.1: 229.6 x 214.5, 492 cm2). |
| Print sheet | **220 x 220 mm textured PEI on 0.4 mm spring steel** with a magnetic base (a third-party stock size; Creality sells 235 x 235 only). The print area is 84.9 % of it. The magnetic base must be bought rated 120 degC continuous. |
| Bed plate | **MIC-6 232 x 232 x 6.35 mm** (v10.1: 241 x 241 x 12.7). 6.35 mm is the thinnest stock MIC-6. |
| Bed limits | (a) out of flat as installed: **0.131 mm** of 0.3 mm; (b) change after probing: **0.101 mm: FAILS** of 0.1 mm; (c) 1 kg at the worst corner: **0.035 mm** of 0.2 mm. **(b) fails by 0.001 mm** (it was 0.090 before the nut plates were enlarged for SendCutSend's web rule; it is a probed-cold bound: see B); (a) passes only on the owner's 0.13 mm figure for the plate as bought (see "The flatness figure"). |
| Part cooling | One **Delta BFB0524HH** 5015 24 V radial blower (two ball bearings; owner's change from the GDSTIME GDB4010) behind the Roto, outlet down into a short printed duct; a 14 x 3 mm outlet 24 mm from the nozzle on the rear-right diagonal aims the jet 14 degrees down at 0.5 mm under the tip. **Estimated** delivered flow **1.19 CFM (33.6 l/min)** (GDB4010 on its 10 x 3 outlet: 0.62 CFM). |
| Probe | **OMRON E2B-M12KS04-WP-C1 2M** (M12 shielded, 4 mm, NPN NO; owner's change from the E2E-X5ME1), OMRON's STEP; on a one-bend L of 2.286 mm 5052 under the Roto's two screws, clamped by its two nuts 15 mm behind its face. Metal in its zone (2.4 mm proud, 18 mm round the head): none (checked). Probed 191.6 x 170.75 mm (80 % of the print area). Temperature (estimate) 45 degC (55 degC hot case) against its 70 degC rating. |
| Supplier rules (new check) | All 30 sheet parts go to SendCutSend: **0 requirement failures, 56 recommendation warnings** (mostly hole-to-edge distance on the thick plates). Not assigned, for comparison: Protolabs would refuse the nut plates and keepers (6 parts, one rule each); OSH Cut, Xometry, Fictiv and Hubs pass all 30. Section G. |
| Bent parts | **2** (the X belt bracket, kept bent by the owner, and the probe L). v10.1: 8. |
| Z screws | Used at **330 mm as sold** (328 above the face). Front two inboard of the top side rails at x +/-144.5, rear one outboard of the back wall at y 202.5; motors on posts of two stacked stock spacers. Envelope unchanged. |
| POM nuts | The anti-backlash nuts the motors ship with, drawn as a **labelled stand-in** (no dimensions published), flange up under open-slotted nut plates, barrel hanging below, captive under open-slotted keepers. |
| Mass / cost / assembly | **13.82 kg / $1,110.99 / 154 min** (v10.1: 14.93 kg / $1,061.69 / 161 min). |

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
the rocking allowance is the keeper's play over the 23 mm flange. Results: the nuts are captive; with the screws at opposite lead limits (LSC-015) the height error is 0.142 mm, the least nut load margin 8.0 N, and the 1 kg print sags the supports 0.0009 mm.

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
| (a) out of flat as installed | plate flatness as bought (0.127 mm, the owner's figure) + sag under the bed's own weight on its three countersinks (FEA load case `bed_self_weight_sag`, plate alone, 14.7 N spread over its top face) | 0.127 + 0.0042 = **0.131 mm** (pass) | 0.3 |
| (b) change after probing | the whole heat growth from cold to 80 degC (bed 60 K above the frame, carrier 15 K: the thermal case), as if the bed were probed before it grew at all: the larger of the nozzle-gap change and the plate's bow | nozzle-gap change **-0.101 mm**, plate bow 0.030 mm: **fails by 0.001 mm** (20:03 run, before the nut plates grew: -0.090) | 0.1 |
| (c) 1 kg at the worst corner | the bed-support FEA, screw-only bound | **0.035 mm** at corner -x +y (bonded 0.034; guides and nuts 0.001) (pass) | 0.2 |

**(b) fails, by 0.001 mm.** On the final code the nozzle-gap change in the thermal case is **-0.101 mm** against the 0.1 mm
limit (the FEA verifier's `thermal_gap_change` and the (b) requirement, both errors). At 20:03 on 2026-11-19, before the nut
plates were enlarged for SendCutSend's web minimum (section G), it was -0.090 mm; nothing else in the bed, carrier or thermal
case changed between the two runs, and the mesh (490 k / 483 k nodes) moved the magnet contact's locating node by 3 mm, so
part of the 0.011 mm may be mesh. Either way there is no margin. It hardly depends on the plate: most of it is the studs,
springs and carrier warming. (a) and (c) are far inside their limits at 6.35 mm, which is the thinnest stock MIC-6, so
6.35 mm stays.

The figure is a bound computed as if the bed were probed cold and then heated through (judgement call 3): a printer probed
after its bed has soaked at temperature sees only the carrier's slower warming. Fixes for v11.1, for the owner to choose:
(1) make "heat the bed, soak, then probe" the commissioning and start-of-print procedure (a start G-code macro), and recompute
(b) as the carrier's warming after the soak (which needs a transient thermal case the checks do not have); (2) shorten or
stiffen the thermal path: shorter stud stacks under the plate (they are at 30 K), or a nut plate whose seat sits closer to
the carrier member it hangs from, then re-run the thermal case; (3) the owner relaxes (b) to, say, 0.12 mm. Not changed in
v11: the limit is the owner's. The levelling points, the springs'
preload margin (factor 2.82 at the weak end of the +/-1.5 mm range) and the tilt allowance (one Z motor may stand 1.14 mm out of the plane of the other two, 8.0 times the 0.142 mm routine height error) are kept and pass.

**The flatness figure.** The brief gives "MIC-6 ~0.13 mm per McMaster listing; check". McMaster's page could not be read from
here. The maker's brochure in the repository (Alcoa MIC 6, `cast_tooling_plate.json`) gives **0.381 mm (0.015 in) for 6.35 to
15.9 mm plate** and 0.127 mm for 19 mm and thicker; 0.127 mm is also the thickness tolerance. On the maker's figure (a) is
exceeded by the plate alone (0.385 mm) and no MIC-6 plate under 19 mm would pass. The design takes 0.127 mm as a
receiving-inspection limit on the cut 232 mm piece (a whole-plate figure says little about a 232 mm piece, but nothing
guarantees it either). Question 1.

### C. Toolhead

Two owner changes after the first v11 pass (2026-11-19, late): the part-cooling blower is now a **Delta BFB0524HH** (in
place of the GDSTIME GDB4010) and the bed probe an **OMRON E2B-M12KS04-WP-C1 2M** (in place of the E2E-X5ME1). Both are in
the design, the BOM and the checks below.

**Blower.** Delta BFB0524HH, 5015 class: 24 V (14 to 27.6), 0.11 A (0.16 max), 6500 rpm, 4.59 CFM free air, 22 mmH2O
(216 Pa) shut-off, 45 dB(A), **two ball bearings**, 28 g, Digi-Key 603-1116-ND, $17.00 (maker's specification
`vendor_docs/delta_BFB0524HH_spec.pdf`, record `delta_bfb0524hh.json`). The maker's STEP (`vendor_cad/inbox/BFB0524HH.step`)
is its display model and passes the proxy check: supplier CAD. It stands behind the Roto with its face in the XZ plane,
1.5 mm behind the Roto screws' heads and washers, x from 23 to 75.6 mm right of the nozzle (clear of the probe bracket and the
Roto's right-hand screw head), its outlet edge at z 424.5: above the Y switch board (z 422.6) and the top back rail at the
rear end of the Y travel. Its outlet (20 x 12.2 mm, Delta drawing p.6) is at the -x end of its lower edge and blows down into
the duct's riser. Two M3 x 25 through its two 4.5 mm holes (upper left, lower right, positions measured on Delta's STEP),
washer on the plastic, through the duct's printed cradle, washer and nut behind, thread-locked, 0.3 N.m.

**Duct.** v10.1's flange on the tool plates' tab (two M3 through-bolts into captured nyloc nuts), an arm under the Roto's
right side, a chamber under the Roto with a riser behind it up to the blower's outlet (deeper above z 406 for the 15 mm
blower), a cradle behind the blower for its two bolts, and a front-left extension carrying the outlet tube. The outlet is
**14 x 3 mm** (42 mm2; 10 x 3 for the GDB4010) at 24 mm out on the rear-right diagonal, pointing **14.0 degrees down** at a
point 0.5 mm under the nozzle tip. This pass found the duct drawn in two pieces: the riser's front wall had been cut
away, leaving it open to the Roto's back through a 0.6 mm slit (the geometry check's `multiple_solids` warning). It now has
its front wall and a bridge to the chamber under the Roto below the Roto's underside: one closed solid, 22 g. Measured on the model: the duct is 5.15 mm from the heater block (owner: 4 to 5) and its lowest face 2.88 mm above the tip (owner: >= 2.5); the jet's axis reaches the nozzle's axis 0.5 mm under the tip (off by 0.00 mm) and passes 0.41 mm under the heater core's edge. E3D's silicone sock is on the BOM.

**Flow estimate** (not measured): the blower's P-Q curve (read by eye from Delta's chart at 24 V, spec p.5) against a duct
loss of K = 1.85 at the outlet velocity (contraction 0.40, exit 1.00, tube friction 0.25, two 45-degree turns at chamber
velocity 0.20: handbook figures): **1.19 CFM (33.6 l/min)** at 13.3 m/s through the outlet, 197 Pa. With K 1.4 to 2.5 it is 1.03 to
1.35 CFM. On the same method the GDB4010 on its 10 x 3 mm outlet gave 0.62 CFM at 9.8 m/s (107 Pa), and v10.1's axial
fan about 0.8 CFM at about 5 m/s aimed at the heater: the Delta gives about twice the GDB4010's air at a third more speed,
aimed at the bead. An airflow model is not part of the checks.

**What the swap did to X travel and the toolhead's mass.** X travel is unchanged at 191.6 mm: the rail limits it, not the
toolhead. Below the top side rails' top (z 414) the toolhead's right-most part is still the duct, now **19.7 mm** from the
right top rail at the end of the mechanical travel (GDB4010 layout: 15.2 mm); the left side is unchanged (Roto, 21.0 mm). The
Delta is wider (52.6 mm) and stands higher: at the right end of the travel it and the duct's cradle reach 8.9 mm out over the
right top rail, 10.5 mm above its top, where nothing on the frame reaches in (the motion check sweeps it: no collision). The
X-travel requirement now measures only what is below the rails' top (it took each part's whole bounding box before, which
the taller duct made meaningless). Moving mass on the X block: **0.399 kg** (GDB4010: 0.379 kg) against the 0.40 kg target:
it passes with 2 g to spare.

**Probe.** OMRON E2B-M12KS04-WP-C1 2M: M12 x 1, **shielded**, double sensing distance **4 mm** (setting 0 to 3.2 mm), NPN
open collector, normally open, 10 to 30 V, ambient -25 to 70 degC, pre-wired 2 m, Digi-Key, $35.22 (OMRON E2B data sheet,
`vendor_docs/omron_E2B_datasheet_en.pdf`; record in `omron_e2e.json`). Its model is now **OMRON's own STEP**
(`vendor_cad/inbox/E2B-M12KS04-WP-C1.step`, collected 2026-11-19 through a browser session after OMRON's server refused
scripted downloads, adopted 2026-11-20; the file's two nuts are left out because the design draws the nuts as parts). It
confirmed the data sheet's 47 mm body but showed that the catalogue record split it wrongly (39.1 mm at 12 mm diameter + 7.9
protector); it is now 30 mm of thread + 7.9 mm rear body at 10.2 + 9.1 mm protector at 8.2 (D116-E1-02 p.14), plus a 4 mm
cable stub 10 mm long in the STEP. It sits where the E2E sat, 34.5 mm behind the nozzle on its X, face 2.0 mm above the tip,
clamped 15 mm behind its face by its two nuts in the bracket's 12.5 mm hole.

- **Surrounding metal** (E2B p.20, double distance, shielded, M12): face 2.4 mm proud of metal, an 18 mm diameter round the
  head clear, facing metal 12 mm away. Metal on the toolhead in those zones: **none** (requirement and the subsystems
  verifier). The 15 mm clamp height was kept from the unshielded E2E (it needed 15 mm and a 40 mm zone); the shielded sensor
  could be clamped much lower (a stiffer, shorter holder): question 7.
- **Trigger height:** the nozzle is 1.20 to 2.80 mm above the bed when the probe switches, over the unit spread and temperature drift (4 mm nominal, minus the face's 2.0 mm above the tip) (E2E: 2.00 to 4.00 mm). Z over-travel (1.65 mm) still ends short of the face (2.0 mm).
- **Probe coverage:** 191.6 x 170.75 mm of the 191.6 x 214.5 mm print area (80 %); unprobed strips: front 34.5 mm, rear 9.25 mm, sides none (unchanged from the E2E: same position). The front 34.5 mm strip is the probe's offset behind the nozzle; the mesh extrapolates
  there (`bed_mesh_does_not_cover_print_area`, a warning, as in v10.1).
- **Temperature** (owner: against the 70 degC rating): about **45 degC** at its bracket in the nominal case (air over the bed 55 degC, bracket 45, sock 150) and **55 degC** in a hot case (air 70, bracket 55, sock 180, weaker convection), against the **70 degC** rating: passes, with 15 degC to spare in the hot case. A lumped steady estimate: radiation from the 80 degC bed to
  the face 2.1 mm above it, convection from the warm air over the bed to the 15 mm of barrel below the bracket, radiation
  from the silicone sock seen at 34.5 mm, conduction up the shell to the bracket. The air and bracket temperatures are
  assumed, not computed; there is no enclosure. 55 degC is where OMRON's +/-10 % drift figure stops (+/-15 % to 70).

**Probe holder.** 2.286 mm 5052 (SendCutSend .090, inside radius 0.81). The upper leg lies on the Roto's rear face under its
two M3 x 50, each with two large washers (Accu HPLW-M3-A2, 0.9 mm), which brings the screw's tip inside the front tool plate.
Below z 396 the leg is 22 mm wide, beside the blower; it is 25.5 mm wide at the bend (SendCutSend: over half of the bend line
clear of the probe's hole) and reaches up to z 443, where the toolhead loom is clamped before it climbs past the blower's
left side, over its top and down the back of its cradle. The PEM nuts the Roto's screws thread into are now **S-M3-0**
(SendCutSend stocks no S-M3-1; mounting hole 4.27 mm).

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
0.36 mm towards the motors (arm 10.97 mm) and the load is 0.98 of the allowance: the warning is gone. The Y motor plates
keep 1.88 mm as the owner asked; the belt plane does move, by 0.36 mm, to fix the shaft load.

### E. Fasteners

| Decision | Done |
|---|---|
| Corner-bracket screws: flanged button heads | ISO 7380-2 M5 x 8 on all 66 (every bracket leg on a slot; 2 more, M5 x 10, through the Y motor plates) bracket legs (catalogue `bhcs_flanged`, collar 11.8, head 2.75, from distributors' listings: secondary). The collar covers the 6 mm slot; it fits between the casting's webs (12 mm apart) with 0.1 mm a side. v10.1's `screw_head_seat_too_small` warning is gone |
| 26 M5 x 10 with two washers -> M5 x 8 with one | done on the 20 that remain (deck 12, X motor and idler plates 4, tray 2, inlet panel 2; the X and Y tension anchors' 6 are gone). M5 x 8 with one washer ends 3.7 mm into the slot with 0.50 d of thread: they pass and are listed in the marginal-thread warning |
| Four beam bolts at 0.59 d | M5 x 12 with a second washer: through the whole T-nut |
| M2.5 nuts | thread locker (as v10.1 drew it) |
| Large washers | Accu HPLW-M3-A2 (9 x 3.2 x 0.9) and HPLW-M4-A2 (12 x 4.3 x 1.1), A2 stainless, re-made from Accu's drawings: outside diameter, bore and thickness with tolerances are all a flat washer has, so they are faithful re-makes. Every design's large M3 / M4 washer is now these (0.1 mm thicker than the ISO mid value) |
| M4 x 6 | McMaster 90128A208 zinc-plated, still a generated placeholder (its STEP is over 5 MB) |

New fasteners: M5 x 16 for the 9.525 mm nut plates, M5 x 65 post bolts, M3 x 25 with washers and nuts for the blower (M2 was
added to the catalogue's tables for the GDB4010 and is no longer used in v11), M2.5 x 20 nut pins, M5 x 30 tension screws with
jam nuts. The Roto's PEM nuts are S-M3-0 (SendCutSend's stock).

### F. Supplier CAD folded in

| File | Used as |
|---|---|
| Misumi HFS5-2020-500 STEP | `vendor_cad/inbox/HFS5-2020-500.step`: its section swept to each extrusion's length is the extrusions' display model (supplier CAD). The catalogue now records the section's area (182.13 mm2; catalogue 183) and the cavity's real shape (12 mm only for 0.939 mm under the lips, then 45-degree walls to a 5.878 mm floor); the T-nut fit check now also checks the nut's body against the tapered walls (9.08 mm available at its lower edge for its 8 mm). The BOM text no longer says Misumi was unreachable |
| KIPP K0143.04 thumb nut STEP | `THUMBNUT-DIN466-M4.step`; the part is now steel (KIPP), 6.2 g, thread through the full 9.5 mm |
| Century Spring DJ-8X20YCS STEP | `SPRING-DIE-DJ-8X20YCS.step` with a sidecar placing it and showing it at the installed height; OD 7.36 (catalogue 7.6, corrected) |
| Schurter DD11 STEP | `INLET-C14-SW-FUSE-T8A.step` with a sidecar; 33.5 mm deep with its terminals (data sheet 30): the inlet's printed hood is 2 mm deeper |
| OMRON E2E-X5ME1 STEP | `PROBE-OMRON-E2E-X5ME1.step`: the barrel solid (the file's two nuts are left out; the design draws the nuts as parts). No longer used by v11 (the probe is now the E2B) |
| Delta BFB0524HH STEP | `BFB0524HH.step` (the maker's download): the blower's display model, supplier CAD |
| OMRON E2B-M12KS04-WP-C1 STEP | `E2B-M12KS04-WP-C1.step` with a sidecar (body solid; the nuts are left out): the probe's display model, supplier CAD (adopted 2026-11-20; it corrected the catalogue's split of the 47 mm body) |
| ServoCity GT2 pulley | not used: it is for 6 mm belt; the 9 and 12 mm pulleys keep their stand-ins |

Each is recorded in `vendor_cad/SOURCES.md`.

### G. Supplier sheet-metal rules (the new manufacture check)

The manufacture verifier now judges every sheet part against the published design rules of six sheet suppliers
(`mechloop/data/supplier_rules/`, `mechloop/verifiers/dfm_supplier.py`, `docs/SUPPLIER_RULES.md`): a rule the supplier
states as a requirement is an error, one it phrases as a recommendation a warning. v11 has **30 sheet parts, all assigned to
SendCutSend** (no machined part). Result on the final code: **no supplier-rule error; 56 warnings (all SendCutSend recommendations)**, plus the general sheet
checks' 39 warnings (holes near edges, holes smaller than the thickness, sharp corners, one hole near a bend).

| Supplier | Assigned | v11's 30 sheet parts against its published rules |
|---|---|---|
| SendCutSend | all 30 | **0 requirement failures.** 4 parts pass every rule (the three carriage plates and the deck), 1 passes with no published hole-to-edge rule for its stock (the bed plate), 25 miss 1 to 4 recommendations: **56 warnings**, all on the cut: hole edge to part edge (41: SendCutSend's "1.5 to 2 x thickness" and "1 x hole diameter" advice, e.g. nut plates 5 mm against 14.3 mm for 9.525 mm stock, electronics tray 2.25 mm, Z motor plates 4.78 mm), holes smaller than the thickness (8: the nut plates' and Z motor plates' 3.4 to 4.8 mm holes in 6.35 / 9.525 mm plate), slot to edge (5: Y plates, X and Y motor mounts), one hole 3.14 mm from the probe bracket's bend (SendCutSend's die-width figure asks 6 mm), and the probe bracket's share of bend meeting the minimum flange |
| OSH Cut | none | all 30 pass what OSH Cut publishes; it publishes no hole-size or hole-to-edge rule for most of these stocks (its app is blocked by robots.txt) |
| Protolabs | none | 24 pass (10 with recommendations missed); **6 fail one requirement each: the three nut plates and the three nut keepers** |
| Xometry | none | all 30 pass; 25 miss 1 to 5 recommendations |
| Fictiv | none | all 30 pass; 22 miss 1 to 3 recommendations |
| Hubs | none | all 30 pass; 16 miss 1 to 3 recommendations |
| Fabworks | none | 2 pass (the two bent parts, 1 recommendation missed each); for the other 28 it publishes no rule for the material and thickness |

Before this check ran, SendCutSend's shop profile had stopped the 20:03 verify on four parts (`shop_web_below_minimum`: the
three nut plates had 3.25 mm between a hole and the edge, 4.76 asked; the electronics tray 1.25, 1.59 asked). The nut plates
were made 3.5 mm longer and 2 mm deeper beyond the nut (half length 27.75, reach 23.5 mm), the keepers 2 mm wider, and the
belt bracket's holes moved 0.25 mm off the bend (6.1 mm from it: SendCutSend's die width); the Roto's PEM nuts became S-M3-0,
the size SendCutSend installs. The bigger nut plates are what moved limit (b) over its line (below).
SendCutSend's recommendations were not all followed: holding 1.5 to 2 x thickness from the edge on 9.525 mm plate would grow
every nut plate by about 20 mm, and the rear one already reaches 57 mm out through the back wall. Question 8.

### H. Purchased parts against the new DG-07 rule

A practice rule added during this work (DG-07, `mechloop/verifiers/purchased.py`, owner's key rule for v11.1) requires every
purchased part to be a real, orderable product (maker, part number, seller), with the maker's CAD or a faithful re-make and a
maker's source for every rating a check reads. It is an error unless a design is marked exploratory, and v11 is not (the
coordinator's instruction: v11 is not the build candidate; the replacements are v11.1's work, `docs/V11_1_PLAN.md`). On v11
it gives **116 errors** on the final code (138 on an earlier run the same night, before the commodity lines were pinned):

| Category | SKUs (pieces) | Examples |
|---|---|---|
| Not pinned to a real product (`purchased_part_not_real`) | 55 (232 pieces: 52 drawn SKUs and 3 BOM-only lines, the two belts and the silicone sock; 22 more, the wire, connectors, cable ties, fuses, drivers and thread locker, were pinned by the sourcing work while v11 was being verified) | extrusions (no seller recorded although Misumi cuts them), corner brackets, flanged button heads, rails and blocks (no seller), motors, pulleys and idlers, spacers, the PEI sheet and its magnetic base, the heater, the POM nut, the E2B probe (no seller recorded), the Octopus |
| Geometry a stand-in (`purchased_geometry_not_sourced`) | 41 (212) | flanged button heads, corner brackets, pulleys, spacers, M5 x 16 / x 65 / M3 x 25 / M2.5 x 20 screws, MGN rails and blocks, the POM nut, the PEM S-M3-0, the probe's nuts, heater, magnetic base, sheet |
| A rating a check reads has no maker's source (`purchased_rating_not_sourced`) | 20 (43) | pulley pitch diameter and teeth, the Octopus's driver ratings, the Roto's motor figures, the E2B's repeatability and drift-rated-to figures (assumed in the catalogue), the PSU, the POM nut |

The Delta blower is not among them; the E2B now fails only on "no seller" and on ratings the data sheet does not give.

## v10.1 against v11

From the two full verify reports and the two scorecards, each on its design's final code.

| | v10.1 | v11 |
|---|---|---|
| Verify errors / warnings | 0 / 61 | 118 / 142 (116 from DG-07, which did not exist when v10.1 was verified; 1 FEA thermal + 1 requirement: limit (b)) |
| Requirements met | 33 of 33 | 39 of 40 (limit (b)) |
| X / Y / Z travel | 229.6 / 214.5 / 180 mm | 191.6 / 214.5 / 180 mm (+1.65 over-travel) |
| Print area | 229.6 x 214.5 mm (492 cm2) | 191.6 x 214.5 mm (411 cm2); probed 191.6 x 170.75 (80 %) |
| Parts in the model (made) | 825 (37) | 797 (34) |
| Mass | 14.93 kg | 13.82 kg (-1.11: the 6.35 mm bed plate, a smaller bed, fewer bent brackets) |
| Moving mass X / Y / Z | 0.360 / 1.289 / 5.59 kg | 0.399 / 1.275 / 4.42 kg |
| BOM cost (estimate) | $1,061.69 | $1,110.99 (+$49.30: the Delta blower $17, the E2B $35.22, POM-nut screws, flanged button heads) |
| Assembly time (estimate) | 161 min | 154 min |
| Fasteners with a driver-access check / types / tool changes | 259 / 22 / 22 | 251 / 24 / 33 |
| Assembly turned over / parts fitted from below / parts needing holding | 24 / 27 / 251 | 20 / 39 / 224 |
| Bounding box | 389.7 x 419.0 x 471.0 mm | 389.0 x 419.9 x 475.9 mm (the blower's cradle is the top; the envelope is 420 x 420 x 480) |
| Y motor shaft load against its allowance | 1.01 (warning) | 0.98 (no warning) |
| Resonance X / Y (scorecard) | 74.8 / 67.8 Hz | 73.1 / 68.2 Hz |
| Acceleration an owner would run | 8,200 mm/s2 | 8,200 mm/s2 |
| Step-loss ceiling | 24,000 mm/s2 | 20,000 mm/s2 (first failure at 24,000 is a print-outline defect, no step loss; one sweep step is not a real difference) |
| Cross-track error RMS / worst | 0.0109 / 0.1029 mm | 0.0103 / 0.1039 mm |
| Benchmark print time | 2,571 s | 2,571 s |
| Input shaper (tune, Klipper's code on the twin) | X EI 92.8 Hz, Y MZV 67.2 Hz | X EI 90.8 Hz, Y MZV 67.6 Hz (predicted resonance 71.8 / 67.3 Hz) |
| Pressure advance (tune) | 0.042 | 0.042 |
| Bed mesh (tune): first layer gap error with / without mesh | | worst 0.015 / 0.104 mm (RMS 0.008 / 0.074; on the assumed as-built bed 0.30 / 0.20 tilt, 0.15 bow) |
| Firmware-in-the-loop print (Klipper, STM32F446, motor bracket) | v10's: clean, 3,891 s, 0.055 mm from the path | clean: 3,891 s, the nozzle within 0.055 mm of the G-code path, no machine collision in 4,074 poses checked, one corner-bulge warning (0.40 mm, pressure advance off in this run) |
| Part cooling (estimate) | about 0.8 CFM at 5 m/s (axial fan, aimed at the heater) | 1.19 CFM at 13.3 m/s (Delta blower, aimed under the tip) |
| Probe | OMRON E2E-X5ME1 (unshielded) | OMRON E2B-M12KS04-WP-C1 (shielded), OMRON's STEP |

## Purchased-part CAD: three states

Counted on the final design (`vendor_cad.model_state` of each purchased part's display model): 763 purchased parts and 34
made parts (797 in all; v10.1: 825, 37 made).

| State | Parts | What |
|---|---|---|
| Supplier CAD | **380** | 345 fasteners (McMaster: cap screws, washers, nuts, nylocs) and 35 others: the 20 extrusions (Misumi's section), the Delta BFB0524HH blower and the **OMRON E2B probe** (both new in v11), the three KIPP thumb nuts, the three Century springs, the Schurter inlet, the X and Y motors, Roto, Revo and power supply |
| Faithful re-make from a named supplier drawing | 171 | the 152 T-nuts (Misumi HNTAJ5) and the 19 Accu large washers |
| Stand-in: generated to a standard | 103 | the 68 flanged button heads (ISO 7380-2; McMaster's 92137A412 / A414 STEPs are now staged, not yet adopted), M3 x 25, M5 x 16, M5 x 65, M4 x 6, M5 x 6 and M2.5 x 20 screws, the DIN 934 M5 nuts, the toothed washer, the probe's two nuts |
| Stand-in: community CAD | 50 | the 36 corner brackets, the guide rails and blocks, the two endstop boards |
| Stand-in: assumed dimensions or simulation solid | 59 | spacers (35), the three POM nuts, lead-screw motors and screws, the two PEM S-M3-0, pulleys and idlers, the sheet, magnetic base, heater, thermal fuse, Octopus, Pi and relay |

New supplier CAD in v11 (both owner changes): Delta's own STEP of the BFB0524HH, and OMRON's own STEP of the
E2B-M12KS04-WP-C1, adopted on 2026-11-20 when it arrived (it was drawn from the data sheet until then). Staged but **not
adopted** in v11 (left for v11.1): McMaster's STEPs for the M4 x 6 and M5 x 6 cap screws, the flanged button heads M5 x 8 / x 10,
the internal-tooth lock washer and the large washers (`vendor_cad/staging/instinct_REQ-001/`), and Misumi's HNTAJ5 and
HBLFSNF5 files.

## Judgement calls

1. **The flatness figure** (above): built with the owner's 0.13 mm as an inspection limit; on the maker's 0.381 mm the plate
   alone exceeds limit (a).
2. **Z screws**: front pair inboard of the top rails, rear one outside the back wall, rather than feet (envelope) or custom
   screws (not stock). The front screws stand 1.5 mm from the top side rails' inner faces at their free tops.
3. **Limit (b)** is bounded by the whole heat growth, as if the bed were probed cold: conservative. Probing after a heat soak
   leaves only the carrier's slower warming.
4. **The probe stays where it was**; the blower was fitted beside it and the holder redrawn (owner: keep X travel). The E2B
   took the E2E's place and clamp height unchanged.
5. **Y belt plane 0.36 mm nearer the motors** (thinner idler plates) to clear the shaft-load warning; the motor plates keep
   1.88 mm.
6. **The sheet requirement** is 84 % (v10: 85 %): 220 x 220 is the stock size the reach nearly fills, at 84.9 %.
7. **Nut plates 9.525 mm** for the rear plate's reach; all three alike in thickness so the nuts sit at one height.
8. **No part-cooling bench unit**: the blower sits where the driver for the Roto's right-hand screw goes, so the order is duct,
   Roto, screws, blower. The front Z drives go in as units with their nut stacks, before the top side rails.
9. **The tension screws are not driver-checked**: they are set by their jam nuts and their heads bear on the brackets.
10. **The Delta blower overhangs the right top rail** at the right end of the travel, 10.5 mm above it: X travel stays
    rail-limited, and the X-travel requirement counts only what is below the rails' top.
11. **Limit (b) is reported as a fail**, not relaxed and not designed round in v11 (the owner's limit; the fixes are listed).

## Checker and catalogue changes

1. `mechloop/parts/batch10.py`: `blower_bfb0524hh` (Delta's specification and STEP, P-Q curve in Pa) with
   `blower_flow_estimate_pa`, and `blower_gdb4010` (kept in the catalogue, no longer used by v11), `blower_flow_estimate`, `leadscrew_nut_pom_ab4`
   (stand-in), `print_sheet_pei220` (secondary), `bhcs_flanged` (ISO 7380-2, secondary). Vendor files `gdstime_gdb4010.json`,
   `generic_pei220.json`, `iso7380_2.json`, `accu_iso7093.json`, `delta_bfb0524hh.json`; the POM nut's estimate in
   `stepperonline_17e19_ab4.json`. `mechloop/parts/probes.py`: the E2B-M12KS04-WP-C1 (record in `omron_e2e.json`, shielded
   surrounding-metal figures, no internal pull-up), a narrower rear body and the cable stub's protrusion for OMRON's STEP.
   `hex_nut(..., "pem0")`: PEM S-M3-0.
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
8. Build package: v11 stage notes and open items (the blower and probe items now name the Delta and the E2B). Viewer: the POM
   nut kept visible with the drive parts.
10. The supplier sheet-metal rules (`mechloop/data/supplier_rules/`, `mechloop/verifiers/dfm_supplier.py`) now run inside the
   manufacture verifier; their findings for v11 are below.
9. Tests: `tests/test_v11_support.py` (16 tests).

## Unverified, assumed or not done

- The POM nut's dimensions (photographs); the magnetic base's thickness (1.5 mm) and rating (to be bought at 120 degC); the
  220 sheet (resellers' snippets); the blower's P-Q points (read by eye from Delta's chart); the flanged button head's
  dimensions (distributors' snippets); the HIWIN stock-length list (not obtained: 250 mm is the brief's figure).
- The flow estimate: handbook K values, no airflow model; the jet's spread and its effect on the sock and the nozzle.
- MIC-6 flatness: the owner's 0.13 mm against the maker's 0.381 mm (whole plate).
- The 330 mm screws' run-out and whip at their free tops, 1.5 mm from the top side rails.
- The probe bracket's stiffness; the E2B's switching distance on the 0.4 mm spring-steel sheet (OMRON's figure is for a
  1 mm iron target); the probe's temperature (a lumped estimate with assumed air and bracket temperatures).
- v10.1's open items that still stand (T-slot tolerances, the T-nut re-make, McMaster files not in hand).
- Not run: `score --firmware klipper` (the real firmware planning every benchmark print); a transient thermal case (what
  limit (b) would be after a heat soak); an airflow model of the new duct; any test of the generated drawings beyond the
  generator's own checks; nothing physical.
- Not adopted (staged for v11.1): McMaster's STEPs for M4 x 6, M5 x 6, the flanged button heads, the toothed washer and the
  large washers; Misumi's HNTAJ5 and corner-bracket files.

## Questions for the owner

1. **Limit (b) fails by 0.001 mm** (-0.101 mm; -0.090 before the nut plates grew for SendCutSend). Choose for v11.1: make
   "heat the bed, soak, then probe" the procedure and bound (b) on the carrier's warming after the soak; shorten or stiffen
   the thermal path (stud stacks, nut-plate seat); or relax (b).
2. **DG-07: 116 errors** on purchased parts (55 not pinned to a real product, 41 stand-in geometry, 20 unsourced ratings).
   Confirmed as v11.1's work (`docs/V11_1_PLAN.md`); v11 is not the build candidate.
3. MIC-6 flatness: accept 0.13 mm as a receiving check on the cut plate (and reject a worse piece), or go by the maker's
   0.381 mm, which no plate under 19 mm meets against limit (a)?
4. Z screws at 330 mm: is the arrangement acceptable (front screws 1.5 mm from the top side rails, rear motor outside the back
   wall, front Z drives fitted before the top side rails)? The alternatives are custom-length screws or feet.
5. The POM nut: can one be measured before the nut plates and keepers are cut?
6. The 220 x 220 sheet comes from resellers, not Creality: acceptable, or keep Creality's 235 (74 % used)?
7. The E2B is shielded: its holder could clamp it 2.4 mm behind its face instead of the E2E's 15 mm (a shorter, stiffer
   holder). Redraw the holder in v11.1, or keep the 15 mm?
8. SendCutSend's 56 recommendations (mostly hole-to-edge distance on the 6.35 and 9.525 mm plates): follow them where cheap
   (Y plates, tool plates, electronics tray), and accept them on the nut plates, where 1.5 to 2 x thickness would grow each plate
   by about 20 mm?
9. The toolhead is 0.399 kg against the 0.40 kg target (the Delta is 28 g against the GDB4010's 12 g; with its bigger duct and M3 bolts the toolhead gained 20 g): accept, or raise
   the target / save mass elsewhere?
10. The Y belt plane moved 0.36 mm (thinner Y idler plates) to clear the shaft-load warning (now 0.98): acceptable?

## What was run

All on 2026-11-19/20. The previous agent's last full verify was cut off by a container restart. This pass:

- **Full verify, five attempts on the way to the final one.** 00:48: lost to the second container restart. 00:48 to
  02:04 (complete): bed-support FEA killed for lack of memory (two agents' CalculiX runs, about 6.5 GB each, at once), and it
  found the X-travel requirement measuring the whole duct's bounding box (fixed: only what is below the rails' top counts)
  and limit (c) passing although its FEA had not run (fixed: (c) now fails when the flexure is not evaluated). 02:08 and
  02:59: stopped (memory). 02:59 to 04:07 (complete): the geometry check's `multiple_solids` warning showed the **part duct in
  two pieces**: the riser behind the Roto had no front wall, open to the Roto's back through a 0.6 mm slit (fixed: a bridge
  and a front wall; one solid, 22 g, toolhead 0.399 kg). 04:10 to 05:16: bed-support FEA failed with the disk full (5 GB of
  stale FEA scratch folders from the killed runs; removed). 05:18 to 06:04: bed-support FEA killed again (memory, against
  this pass's own scorecard run). **06:30 to 07:20: the final report**, on the final code, with nothing else running:
  all 13 verifiers ran, every FEA case ran, nothing was reused (`--tier affected`, whose cache held nothing usable; the
  report's `incremental` block lists each verifier as "ran"). Result at the top of this page.
- **`score --assembly`** (08:22, 61 min) on the final report: the comparison table. Its static check names the one real FEA
  error (`thermal_gap_change`); an earlier score run at 06:30 had memory-killed FEA and is superseded.
- **`tune`** (Klipper's shaper, pressure-advance and bed-mesh code on the twin): shaper, pressure advance and mesh in the table.
- **Firmware-in-the-loop print** of the standard part (`examples/motor_bracket.py:bracket`, real Klipper at commit 29d4ec2, the
  Octopus's STM32F446 dictionary, `--trajectory`): clean: 3,891 s, the nozzle within 0.055 mm of the G-code path, no machine collision in 4,074 poses checked, one corner-bulge warning (0.40 mm, pressure advance off in this run); output `out/printer_v11/fil/bracket/`, replayed in the viewer.
- **Electrical:** the generated `out/printer_v11/electrical/printer.cfg` is parsed against the board's pins and loaded by klippy
  itself inside the verify (`klipper_config_check`: no problems, klippy ok); the FIL print plans on it.
- **Assembly plan / simulation:** inside the verify (assemblability: pass, one `unsupported_step` warning for the thumb nuts),
  in `score --assembly` (154 min, 251 fasteners, 33 tool changes, 20 turn-overs) and in the build package (`ASSEMBLY.md`).
- **Viewer** (`tools/export_viewer.py`, with the assembly simulation and the FIL print): `viewer/meshes.txt` 16.1 MB, 800
  parts (the three belts as display parts). `viewer_v10_1/` and `review_v10_1/` are left as they were.
- **Build package** `docs/build/printer_v11/` (`tools/build_package.py --force`): the generator refuses a report with
  errors, so it was written with `--force`, and every document carries its banner "STALE PACKAGE (--force) ... the report is
  not a pass (errors present)". The report does describe this design file (md5 checked); the banner's reason line is the
  true one. Its README lists the 60 placeholder BOM lines first (DG-07).
- **Review data** (`tools/build_review.py printer_v11`): `review/data.json` (800 parts, 112 joints, 184 open items) and
  `review/drawings/` (34 SVGs; three stale v10.1 drawings of deleted tension anchors removed).
- `tools/mcmaster_wanted.py`: `vendor_cad/mcmaster_wanted.csv`, 42 hardware types, 621 parts.
- **Tests:** `tests/test_v11_support.py` 16 passed; the whole suite with `-k "not v11"`: {{TESTS}}.

## Files

- `designs/printer_v11.py`; `out/printer_v11/report.json`, `scores.jsonl`, `tune/tuning.json`, `fil/bracket/`,
  `electrical/printer.cfg` (not in git; `printer_v11.step`, 107 MB, also not)
- `mechloop/parts/batch10.py`, `mechloop/parts/probes.py` and the vendor files above (`delta_bfb0524hh.json`,
  `omron_e2e.json`); `tests/test_v11_support.py`; `tools/build_package.py` (v11 open items)
- `docs/build/printer_v11/`, `viewer/`, `review/data.json`, `review/drawings/` (generated; `review/drawings/` is not in git);
  v10.1's viewer and review data kept in `viewer_v10_1/` and `review_v10_1/`
- `vendor_cad/inbox/` (seven supplier files used by v11, among them `BFB0524HH.step` and `E2B-M12KS04-WP-C1.step`, and their
  sidecars), `vendor_cad/SOURCES.md`, `vendor_cad/mcmaster_wanted.csv`
