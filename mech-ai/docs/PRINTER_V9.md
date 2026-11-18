# printer_v9: three Z rails, a 2020 square with a deck, a 257 mm bed on four sprung studs

Everything here is simulated. Nothing has been built.

`designs/printer_v9.py` starts from a copy of `designs/printer_v8_2.py` (v8.2 was not edited). The owner sent a hand
sketch and notes: keep the three lead-screw steppers, guide the Z stage on three vertical linear rails (one near each
screw), make the bed as large as the cube allows, make the carrier a closed square of 2020 extrusion under the bed, hang
six simple brackets off that square (three to the nuts, three to the rail carriages), put a thin (1/8 in) aluminium deck
on the square, and float the bed a small distance above the deck on four spring-loaded levelling screws with thumb nuts.

The gantry, toolhead, frame cube and electronics are v8.2's and were not changed.

It passes all 13 verifiers with **0 errors and 51 warnings** (`verify designs/printer_v9.py`, report in
`out/printer_v9/`), all 28 requirements met. Every warning is listed below.

## The short answers

| Question | Answer |
|---|---|
| How big is the bed now? | Print sheet 257 x 257 mm on a 265 x 265 x 6.35 mm MIC-6 plate (v8.2: 180 x 180 on 220 x 256.5 x 9.525). Sheet area 2.04 times v8.2's. |
| What limits the bed? | The cube's clear width: 300 mm between the posts, less a rail (8 mm), a block (5 mm more) and a 1.6 mm plate on each side: 270.8 mm for the carrier, 265 for the plate. The next catalogue sheet size above 257 is 300, which does not fit a 300 mm opening. Depth is not the limit (333 mm clear; 281.8 used). |
| What can the nozzle really reach? | 180 mm in X, 214.5 mm in Y: the same travel as v8.2, because the gantry is the same. v8.2 printed on 180 x 180 of it; the other 34.5 mm of Y was travel for the probe. v9 puts sheet under all of it: **print area 180 x 214.5 mm** (+19 %), of which the rear 180 x 180 is probed. |
| Is XY travel what limits the useful area? | Yes. 180 x 214.5 mm is 58 % of the sheet. X is held to 2 to 3.5 mm by three gantry details, Y to 3.5 and 1.4 mm by the frame's front and back top rails. Nothing within "the existing XY mechanics" gives more; the changes that would are proposed below and were NOT made. |
| Z moving mass | 4.715 kg with the 1 kg payload (v8.2 4.401): +0.31 kg for a plate 24 % larger in area (and a third thinner), a deck and a third block. |
| Bed sag, 1 kg at the worst print corner | 0.0081 mm on the screw-only bound (limit 0.02; v8.2 0.0063, on a print area 19 % smaller). |
| Four spring points or three? | Four were built, as asked, and they work: the bed is held by its studs, not by its springs, with a preload margin of 2.04 at the weak end of the levelling range. Three would be the better mount (no way to twist the plate, one fewer part set); see "Judgement calls". |

## What changed against v8.2

| | v8.2 | v9 |
|---|---|---|
| Print sheet | TRONXY PEI180, 180 x 180 | 257 x 257 double-sided PEI with magnetic base (catalogue `print_sheet_pei257`) |
| Bed plate | MIC-6 220 x 256.5 x 9.525, 1.51 kg | MIC-6 265 x 265 x 6.35, 1.25 kg |
| Bed mount | four M5 threaded-rod posts 49 mm long on tabs, a bent stainless tie; levelled once with two nuts per post | four M4 studs, die springs and knurled thumb nuts on a deck 18.8 mm under the plate |
| Carrier | 2020 rectangle of rear beam, two arms, front beam with a 4.75 mm back plate; eight cast brackets | closed 2020 rectangle 270.8 x 281.8 mm, four cast brackets inside, 3.175 mm 6061 deck on top (ten M5) |
| Z guides | two MGN12 rails on the back wall, one ZF block each, both on one rigid back plate | three MGN12 rails (left wall, right wall, back wall), one ZF block each, each on a 1.6 mm plate with a flexure web |
| Brackets off the carrier | back plate, three nut plates of two shapes (9.525 mm), four post tabs, tie | **three carriage plates of one shape, three nut plates of one shape** (4.75 mm); three keepers of one shape |
| Z motor plates | two shapes (rear posts across the rail, front along it, front notched) | one shape: the rear screw moved onto the back rail's centre line (y 170; v8.2 180) |
| Lead screws | cut to 252 mm above the motor face | cut to 258 mm: the nuts ride 40 mm higher because the bed sits close above the carrier |
| Heater | 200 x 130 mm, 180 W | 190 x 180 mm, 180 W (same output of the board) |
| Print area declared | 180 x 180 | 180 x 214.5 (home pose 17.25 mm further forward; the travel's ends are where they were) |

### Bed size: what the cube allows

Clear opening inside the frame, at every height the bed passes: x -150 to 150 (the posts), y -173 to 160 (front and back
rails and posts). Nothing on the gantry hangs below the nozzle plane, so the top of travel sets no limit either.

Width. The side rails stand on uprights in the side walls, so only the rail (8 mm), the rest of the block (5 mm) and
the carriage plate (1.6 mm) come out of the 300 mm: the carrier's square is 2 x (150 - 13 - 1.6) = **270.8 mm** wide. The
plate is 265 (2.9 mm inside the square each side, 9.5 mm clear of the rails; the blocks are below it). A 257 mm sheet
leaves 4 mm of plate round it. Putting the side rails somewhere else (two on the back wall, as v8.2) would free the
width to about 290 mm, but no catalogue print sheet lies between 257 and 300 mm, and a 300 mm sheet needs a 310 mm
opening. So 257 is what this cube takes whichever way the rails go, and the rails went where the sketch has them.

Depth. 333 mm clear; the square is 281.8 mm deep, set by the plate and by centring the bed on the nozzle's reach. A
deeper plate fits (about 310 mm) but there is no 257 x 310 sheet and no nozzle to print on it.

### Print area: what limits X and Y

Read from the model's own dimensions at the ends of travel (the motion verifier confirms no collision over the whole
mechanical travel; these are the clearances that would close first):

| Axis, end | What is in the way | Clearance at the end of over-travel |
|---|---|---|
| X, both | the X carriage against the rail stops' tongues | 2.3 mm |
| X, right / left | the belt clamp plate against the X idler / the X pulley | 2.5 / 3.5 mm |
| X, left | the tool plate against the left Y plate's land (which carries the X switch) | 2.0 mm |
| X, both | the X carriage on its 250 mm rail (5 mm kept) | 5.8 mm spare |
| X, right | part fan and duct against the top side rail | 11.7 mm |
| Y, front | the X mounts' bolt heads against the top front rail (v8.2's flush rail) | 3.5 mm |
| Y, front | the Y carriages on their 300 mm rails (5 mm kept) | 0.4 mm spare |
| Y, rear | the part fan's screws against the top back rail | 1.44 mm |

So the 180 x 214.5 mm the nozzle covers is all this gantry has in this frame. v9 gains its 19 % only by printing on
the 34.5 mm of Y that v8.2 kept for the probe.

### Proposed, NOT made: what would unlock more

| | Change | Gain | Cost |
|---|---|---|---|
| A | A probe with no Y offset (beside the nozzle within the tool plate's width, or a nozzle-contact / eddy-current probe) | the front 34.5 mm becomes probed: 180 x 214.5 fully meshed. No more area | toolhead redesign; the E2E-X5ME1's 40 mm metal-free zone is why it sits behind the Roto today |
| B | Gantry details only: rail stops moved to the rail's ends, belt clamp 5 mm narrower each side or pulleys 6 mm further out, the left Y plate's land cut back with the X switch moved | X 180 -> about 191 mm (the 250 mm rail's limit) | four laser-cut parts redrawn; X switch position |
| C | B plus a 275 mm X rail (the beam is 288) | X -> about 197 mm (then the part fan meets the top side rail) | one rail |
| D | Frame 26 mm wider and 36 mm deeper (clear 326 x 369), 300 / 350 mm rails, with A | 250 x 250 mm, the whole sheet less its 3.5 mm rim | envelope 415 x 455 mm: over the brief's 420 mm in Y, so the brief has to move; Z stage and bed are unchanged except that the three uprights move out with the walls and the square's members grow by the same amounts |

D is the only one that uses the bed v9 now carries. Without it the plate's outer 38 mm in X and 21 mm in Y are never
printed on. That is the cost of "as large as the cube allows" with this gantry: 0.31 kg more on Z and a heater
that covers less of the plate. If D is not wanted, a 235 mm sheet on a 243 mm plate would carry the same print area.

### Z guides: three rails, three flexure plates

Layout. Lead screws stay where v8.2 had them in plan: front left and front right over the bottom side rails
(x +/-160, y -101), rear over the bottom back rail (x 0; now y 170). One rail near each: new 2020 uprights in the left
and right walls at y -32 (between the front motor mounts and the mains inlet's hood) and one in the back wall at x 65
(beside the rear motor plate), each on two cast brackets per end; MGN12 x 250 rails on their inner faces; one
clearance-class (ZF) MGN12H block per rail. v8.2's two uprights at x +/-90 are gone.

Why this layout and not three rigid brackets. A carrier needs three constraints across the Z axis (two shifts and a
turn). One block holds two, so three blocks hold six: three too many, and any error between the rails, or any growth of
the warm carrier, is forced through the balls. So each block is tied to the square by a flat plate with a 30 x 24 x
1.6 mm web between the block's face and the square's face. The web is stiff in its own plane (along the wall) and soft
across it (square to the wall): 12 E I / L^3 = 251 N/mm. Then:

- left and right blocks hold Y, and between them (270 mm apart) the yaw;
- the rear block holds X;
- every block floats square to its own wall.

Three stiff directions whose lines do not meet in a point: exactly what a body in a plane needs. The tilt is held by
the three screws, as in v8.2, which is why the blocks are the clearance class.

What the tolerance verifier says (new solution for three or more rails, `tolerance.paired_rails.z`; 3000 builds):

| | three rails, flexure plates (v9) | the same three rails on rigid plates (a comparison run, not the design) |
|---|---|---|
| Stiff directions held / needed | 3 / 3 | 6 / 3 |
| Rails out of parallel as built, over the 183 mm travel (99.7 %) | 1.09 mm | 1.09 mm |
| ... so the rails are set against the carrier at assembly (`rail_align`, 1.6 mm available) | 68 % of the range used | the same |
| With 0.02 mm left between rails (assumed): side load on a block | 12.8 N | 193.5 N |
| Allowed (what a rigid pair carries at Hiwin's 9 um) | 67.5 N | 67.5 N |
| Web deflection then | 0.03 mm of 0.35 mm | |

Built to drawing without alignment the webs would have to bend 0.7 to 1.0 mm (0.35 allowed), so the alignment step is
needed, as it is for any pair of rails: rear rail square to the frame; left and right rails tightened last with the
carrier on all three blocks, run up and down. Rail parallelism needed after that: with the webs, 0.1 mm between rails
loads a block with about 64 N (the allowed figure); rigid, the same force comes at 0.007 mm.

The web's stiffness is checked by FEA as a beam test (`carriage_plate_web`: 5 N on the block, the block free to
turn, because the harness cannot hold a face against turning only): 0.418 mm bonded against 0.418 mm from beam
theory, 0.558 mm with the joints held only round their screws. On its rail the block cannot turn and the same web
gives 251 N/mm (188 N/mm on the screwed bound). Web stress at the declared 0.35 mm limit: 129 MPa (half of
6061-T6's yield); at the 0.03 to 0.06 mm of service: 11 to 22 MPa.

Thermal growth of the carrier. Taken 15 K warm under the heater (assumed), the square grows 0.047 mm at each side block
and 0.061 mm at the rear block: 12 and 15 N on the webs. Rigid brackets would put that growth straight into the blocks.

Lead screws against the rails: nut misalignment over the travel 2.3 to 2.5 mm at the 99.7th percentile (v8.2 up to 3.4)
against 2.6 mm of nut float; the rear nut uses 98 % of it (warning, as v8.2's 99 %), no screw has to bend.

### Carrier: square, deck, six brackets

- **Square**: left and right members 281.8 mm, front and rear 230.8 mm between them, one cast bracket in each inside
  corner (T-nuts in both legs). No tapped ends.
- **Deck**: 3.175 mm 6061, 270.8 x 281.8 mm, flush with the square, ten M5 x 10 into T-nuts in the members' top slots
  (thread-locked). It closes the rectangle in shear, shields the carrier from the heater and is the levelling datum.
- **Carriage plates** (3, one shape, 1.6 mm 6061, 50 x 97 mm): two M5 x 8 into T-nuts in the square's outer slot, four
  M3 x 5 with washers into the block (2.9 mm in the block's 3.5 mm threads).
- **Nut plates** (3, one shape, 4.75 mm 6061, 64 x 66 mm): under the square's member, two M5 x 10 from below into
  T-nuts; the nut hangs 24.6 mm outboard of the member's face. Floating brass T8 nut, anti-rotation pin and keeper are
  v8.2's, unchanged ("keep the captive nut keepers unless a simpler sound option exists": none was found that also
  keeps the float). The keepers' opening is now one rounded profile (v8.2's sharp corners, open item 8, are gone).
  FEA `nut_thrust` (three times the whole bed's weight, 66 N, on one plate held only at its two bolt holes): factor of
  safety 17.6, 0.049 mm against a limit of 0.05; in service a plate carries 14 to 18 N.

All six brackets are flat laser-cut parts with through holes only. Two drawings.

### Bed mount: studs, springs, thumb nuts

Each of the four points, top to bottom:

1. **M4 x 35 countersunk screw** (ISO 10642, fully threaded) from the plate's top face, in a 90 degree countersink:
   head 0.72 mm below the surface, under the magnetic base.
2. **M4 washer and nut under the plate**, thread-locked: the screw is now a stud fixed in the plate (through-bolt and
   nut, no tapped aluminium). It cannot turn when the thumb nut is turned, which a bare countersunk screw held only by
   spring force does.
3. **Die spring, Century Spring DJ-8X20YCS** (8 mm hole, 4 mm rod, 20 mm free, chrome alloy, 7.6 N/mm), compressed to
   14 mm: 45.6 N. An M4 washer under it on the deck.
4. **Deck**, 3.175 mm. Stud 0 (front left) passes a fitted 4.3 mm hole and locates the bed; stud 1 (front right) a
   4.3 mm slot pointing at stud 0; studs 2 and 3 5.5 mm holes.
5. **Large M4 washer and DIN 466 M4 knurled thumb nut** (16 mm knurl, 9.5 mm high, stainless) under the deck. The
   stud's end stays 3 mm inside the nut: no thread to catch a finger. 0.7 mm per turn, +/-2 mm.

Gap, plate underside to deck: 0.8 + 3.2 + 14 + 0.8 = **18.8 mm**. The studs are at (+/-104, +/-98) from the bed's centre,
inboard of the square, so the thumb nuts hang under the deck inside the carrier and are reached from below; the heater
pad (190 x 180) lies between them.

The spring pushes the plate up against the thumb nut. Spring and nut act on the same spot of the deck from opposite
sides, so the 182 N of total preload does not bend the deck: it is an internal clamp. A load on the bed only reduces
the force between nut and deck; the bed does not move until that force reaches zero. So in service the bed stands on
its studs, and the springs' softness does not appear in any deflection figure. The FEA therefore models the studs and
thumb nuts and leaves the springs out; the preload margin is a requirement in the design file.

## Judgement calls

### 1. Four spring points over-constrain the plate. Built as asked; three would be better

Three points define a plane; the fourth can only agree with it or bend the plate.

- **How easily the plate bends.** Twisting a 6.35 mm MIC-6 plate on supports 208 x 196 mm apart takes
  2 D (1 - nu) / (a b) = 56 N per mm at one corner (D = E t^3 / 12 (1 - nu^2) = 1.70e6 N.mm). The force between a thumb
  nut and the deck is 41 N nominally (16 N in the worst case of the requirement below). So a fourth nut that is up to
  0.7 mm (0.28 mm worst case) off the plane of the other three does not lift off: the springs pull the plate down
  onto all four nuts and **the plate takes the twist that was set**, at about 2 MPa. Past that one corner floats on
  its spring.
- **What that means.** With four points the bed's flatness is whatever the four nuts say. A quarter turn is 0.175 mm.
  Level with the probe (`SCREWS_TILT_CALCULATE`, or a mesh and its twist term), not by feel.
- **Manual levelling is mostly redundant here.** `Z_TILT_ADJUST` already puts the plane of the three screws parallel
  to the gantry at every print start. The thumb nuts are left with two jobs: bringing the bed within the motors'
  correction once, and twist, which only a fourth point can add or remove.
- **Would three be better?** Yes, on balance. Three points (front left, front right, rear centre, over the three
  screws) cannot twist the plate, need no agreement between nuts, and save a stud, spring, nut and four washers. What
  four buy: support near all four corners of the print area instead of three (with a single rear support the rear print
  corners overhang it by 90 mm; that case was not analysed, and I would expect it to want the 9.5 mm plate back,
  +0.6 kg), and the possibility of taking out a plate's own twist. MIC-6's stock flatness tolerance is 0.38 mm, so that
  possibility is not worthless. If the owner prefers three, the change is small: three holes instead of four in
  plate and deck.

### 2. Springs: preload against bed mass and Z acceleration

Requirement `spring_preload` in the design file (numbers from the model's masses):

> bed without payload 1.95 kg; worst point carries 14.9 N (a quarter of the bed, all of the 1 kg payload, Z at 200 mm/s^2);
> spring preload 30.4 / 45.6 / 60.8 N over the +/-2 mm levelling range: factor 2.04 at the weak end. The bed leaves its
> thumb nuts only above 31.4 m/s^2 of upward carrier acceleration (Z runs 0.2); on the springs alone it would bounce at
> 16.2 Hz

The bed's own weight is 4.7 N per point; the requirement puts the whole 1 kg payload on one point as well and asks
the spring to exceed twice that at the weak end of the levelling range (spring at 16 mm, 30.4 N). It does, by a small
margin, so the levelling range is held to +/-2 mm; at the nominal setting the factor is 3.1. Thumb-nut torque at 61 N:
0.06 N.m, 8 N at the fingers. The nuts are held only by the spring's friction on the thread (30 to 61 N): the usual
arrangement, and on some machines they creep. Open item.

Spring data are from search snippets of the maker's page (7.6 N/mm listed; its own load points imply 7.4 to 7.9). The
maker lists no deflection beyond 10 mm; the design uses 4 to 8 mm. Maximum temperature not obtained (the spring sits
under an 80 degC plate, 4 mm from it).

### 3. Thermal growth of the heated plate against fixed screw positions

At 60 K above the deck the studs move 0.30 mm (stud 1, along its slot), 0.28 mm (stud 2) and 0.41 mm (stud 3, on the
diagonal) from the fitted stud. The slot has +/-1 mm and the oversize holes 0.75 mm radially; a requirement checks
that with 0.2 mm kept for hole position. So no stud is bent: the thumb-nut washers slip on the deck.

Two FEA thermal cases (plate, magnetic base and sheet at +60 K, studs +30 K, carrier and deck +15 K, assumed):

| | as designed (three washers slip: "sliding free") | bound: all four stuck |
|---|---|---|
| Bed surface at its centre rises (limit 0.1 on the designed case) | 0.083 mm | 0.206 mm |
| Plate out of flat (max - min of its top face) | 0.035 mm | 0.247 mm |

The stuck case is not a state the machine can hold: a stuck stud would have to carry about 700 N sideways (M4, 15 mm
free, 0.2 mm), and friction under a thumb-nut washer gives 8 to 25 N (0.2 to 0.6 x 41 N). At 25 N the stud's bending
stress is 60 MPa and the plate sees 0.2 N.m at each corner. The stick-slip that is left is why the mesh should be
probed hot. Friction itself is not modelled.

### 4. Resonance of the sprung bed

| Mode | Figure | Basis |
|---|---|---|
| Bed on its studs, plate bending | 369 Hz | FEA modal case `bed_plate_on_four_studs`: plate alone with 1 kg spread over it, the four countersinks held rigidly (upper bound); 206 to 232 Hz by plate theory with pinned corners |
| Whole carrier bouncing on its nuts and blocks | 370 Hz (v8.2 304) | hand estimate sqrt(k / m) / 2 pi from the payload case's screw-only stiffness and the Z moving mass |
| Bed on its springs alone | 16 Hz loaded, 20 Hz empty | 4 x 7.6 N/mm; only if the preload is lost |

The 16 Hz mode exists only when a nut leaves the deck. That needs the carrier to accelerate upward at more than
32 m/s^2 at the weak end of the levelling range (Z runs 0.2 m/s^2), or a push down on the bed above the force between
nut and deck: 41 N over one stud at the nominal setting (164 N at the bed's centre), 16 N in the worst case of the
requirement (weak end of the range with the 1 kg print on that corner). The bed-support check's 20 N hand load is under
the first and over the second: pressed that hard in that state the corner gives about 0.5 mm on its spring and comes
back. v8.2's posts did not do that; it is the price of the sprung mount the owner asked for. A print's weight does
not come near it. Sideways the bed is located by stud 0 in its hole and stud 1 in its slot (0.15 mm of
clearance each): two M4 studs 15 mm long, about 3,500 N/mm each. The twin does not model any of this (the bed does not
move in X or Y on this machine).

### 5. Three rails and three screws

Covered above: the rails do not over-constrain the carrier across Z because each mount keeps only one stiff
direction; the screws do not over-constrain the tilt because the blocks are clearance class, one per rail, on webs.
The bed-support model now puts each web in series with its block (`fea.bed_support.supports[].mount`): guide stiffness
in tilt is 0.004 to 0.009 of the screws' (v8.2 0.014), so a height difference between screws becomes tilt, not force. At
the LSC-015 budget (two screws at opposite lead limits, 0.142 mm) **every nut stays seated**, least margin
9.4 N (v8.2: a front nut unloaded into its backlash, -0.6 N, and the bed then sagged 0.0185 mm); the
`z_nut_unseats` warning is gone.

### 6. Plate 6.35 mm instead of 9.525

Four supports near the print area's corners make the thinner plate stiff enough (0.0081 mm under 1 kg, limit 0.02) and
it saves 0.62 kg on Z and a third of the warm-up energy. Its twist stiffness is what lets four points bend it (call 1).
Stock flatness tolerance is the same for both gauges (0.381 mm).

### 7. Heater smaller than the print area

190 x 180 mm, 180 W (0.53 W/cm^2 under the pad, 0.26 W/cm^2 over the plate), because the studs stand inside the plate
and the board's bed output is at 7.5 of its 8 A. The print area is 180 x 214.5: its front and back 17 mm, and the
plate's whole rim, are heated by conduction through 6.35 mm of aluminium (142 W/m.K). No temperature map was
simulated; the electrical verifier's heater model treats the plate as one lump (60 degC in 295 s, 80 degC in 538 s, 30 % and 52 % duty to hold them; v8.2 334 s, 588 s, 25 %, 43 %). Open item.

### 8. Print area declared as the whole reach

`print_area` is 180 x 214.5 mm and the bed is centred on it, so the bed-support figures are judged at the corners the
nozzle can really reach. The price is the mesh warning (front 34.5 mm not probed). The alternative, keeping 180 x 180,
would have needed a print area that is not centred on the plate, which the checkers do not take.

### 9. Guideline conflicts

| Guideline | v9 |
|---|---|
| 2D laser-cut over CNC | every made part of the Z stage is a flat laser-cut plate with through holes; no CNC part in the machine |
| No load-bearing printed parts | none (the five printed parts are v8.2's holder, duct and covers) |
| No tapping aluminium | none: T-nuts, through-bolts with nuts, the blocks' own threads. The bed studs are through-bolted |
| Washers on slots and oversize holes | large washers under the thumb nuts and keeper bolts; washers under every head on the 1.6 and 3.175 mm sheets |
| Named materials | 6061-T6 (deck, plates), MIC-6 (bed), A2 / 1.4305 stainless (studs' hardware as catalogued), chrome-alloy steel (springs) |
| SendCutSend / Xometry | all sheet parts at SendCutSend gauges (1.6, 3.175, 4.75, 6.35); nothing for Xometry |
| Thread locking on moving assemblies | every new screw on the Z stage is declared thread-locked or nyloc; left without: the three nut pins (nyloc in the BOM, as v8.2) and the thumb nuts (spring preload) |
| Conflict | **countersinks**: four in the bed plate, a second operation after laser cutting (v8.2 had six). **Thin sheet**: the 1.6 mm carriage plates are deliberately thin (they are flexures); M3 x 5 is an unusual length and must not be swapped for x 6 (it would bottom out in the block) |

### 10. Checker changes made for this design

All are in `mechloop/` with tests in `tests/test_v9_support.py`; each is a judgement in the checker and is said here.

- **Tolerance, three or more rails** (`_rail_set`): the two-rail formula could not judge three rails or a floating
  mount. Two plain rails still take the old path, so earlier designs' figures do not move.
- **Bed support, floating mounts**: a block's declared mount is in series with it. Without this the model credited
  v9's blocks with a rigid mount and predicted a nut unseating; with it, none does.
- **FEA mesher**: a second, finer attempt when the volume mesher fails on two close concentric circles (the stud in
  its washer on the thumb nut's face). The bed model is 431,000 nodes (v8.2 205,000) and the FEA verifier takes about
  45 minutes instead of 15.
- **Thermal cases**: a "sliding free" contact (normal load only) and a per-case stuck bound (`ThermalCase.stick`).
- **Thumb nut SKU** does not start `NUT-`: the engagement rule for hex nuts asks the screw to pass the whole nut
  (9.5 mm here); a thumb nut is judged as a tapped stainless part (1 d).

## Verify, per verifier

Full run, 2026-11-18, about 67 minutes (FEA 44 of them).

| Verifier | Errors | Warnings | What the warnings are |
|---|---|---|---|
| geometry | 0 | 0 | |
| interference | 0 | 0 | |
| tolerance | 0 | 4 | rear screw's nut float 98 % used (`adjustment_margin_thin`, 2.54 of 2.6 mm; v8.2 99 %); extruder screw to probe 1.31 mm (0.7 % of builds), two part-fan screws to the top back rail 1.44 mm: as v8.2 |
| manufacture | 0 | 22 | (v8.2: 34) **None on a new Z-stage part.** Four countersinks in the bed plate (second operation; v8.2 six); hole-size, edge and web warnings on the three motor plates (M3 holes in 6.35 mm), both Y plates and both tool plates, and no lead-in on the motors' pilots: all as v8.2. Gone: the nut plates' and keepers' twelve |
| practice | 0 | 15 | FST-070 locking on 56 screws (v8.2 83): frame motors, toolhead, gantry and the three nut pins; on the Z stage every new screw is declared thread-locked or nyloc. BLT-040 x 4, SHF-010 x 3, FST-101, FST-050 (12 parts, none new), LOC-006 (six adjustments; bed levelling now names its mover and lock), FST-081: **M3 x 5 (carriage plates) and M3 x 6 both go into MGN12H threads: do not mix them** |
| ratings | 0 | 7 | `axial_load_rating_unknown` x 3 (15.7 N per motor, no rating), M3 PEM nuts on oversize holes, washers on printed parts x 2 (as v8.2), one stand-in: the magnetic base (v8.2 nine: rods and coupling nuts are gone) |
| motion | 0 | 0 | |
| subsystems | 0 | 1 | bed mesh: the front 34.5 mm of the print area is not probed (v8.2: 12 mm strips all round a sheet the size of its print area) |
| electrical | 0 | 1 | `cutoff_depends_on_mcu` (as v8.2) |
| assemblability | 0 | 1 | `unsupported_step` (as v8.2) |
| fea | 0 | 0 | v8.2's `z_nut_unseats` is gone: every nut stays seated at the LSC-015 budget |
| printing | 0 | 0 | |
| requirements | 0 | 0 | all 28 pass (v8.2's 22 with the bed-post stand-ins removed from the allowed list, plus six for v9: three rails, the web as a flexure, square / deck / shared brackets, spring preload, plate growth, bed and print area reported) |

Total 51 warnings (v8.2 72).

## Numbers against v8.2

`score --assembly` on both (v8.2: out/printer_v8_2/scores.jsonl, 2026-11-17; v9: 2026-11-18). FEA and tolerance figures are
from each design's full verify.

| | v8.2 | v9 | |
|---|---|---|---|
| Errors / warnings | 0 / 72 | 0 / 51 | |
| Print sheet | 180 x 180 mm | **257 x 257 mm** | |
| Bed plate | 220 x 256.5 x 9.525 mm, 1.51 kg | **265 x 265 x 6.35 mm**, 1.25 kg | |
| Print area (nozzle over the sheet) | 180 x 180 mm, 324 cm2 | **180 x 214.5 mm, 386 cm2** | +19 %, all from Y travel that was already there |
| ... of which probed | 156 x 156 mm (12 mm strips all round) | 180 x 180 mm (front 34.5 mm not) | |
| Bed to carrier gap | 75 mm of posts | **18.8 mm** | |
| Total mass | 12.98 kg | 13.65 kg | +0.67 kg: third rail and block, three uprights for two, deck, larger sheet and base |
| Moving mass X / Y / Z | 0.359 / 1.236 / 4.401 kg | 0.359 / 1.236 / **4.715 kg** | Z +0.31 kg (with the 1 kg payload in both) |
| Z drive margin | 8.2 | 7.9 | 691 N available, three motors at 0.8 A |
| BOM cost (estimate) | $963 | $1,008 | +$45: rail, block, extrusion, deck, larger sheet, springs and thumb nuts; rods, coupling nuts, tie and back plate out |
| Parts / fasteners | 584 / 187 | 584 / 195 | |
| Made (laser-cut or printed) part drawings | 41 parts | 39 parts | six brackets in two shapes, three keepers and three motor plates in one each |
| Assembly time (estimate) | 138.2 min | 138.1 min | 269 placements held (241), 20 from below (41), 18 tool changes (9) |
| Bed sag, 1 kg at the worst print corner (screw-only bound) | 0.0063 mm | 0.0081 mm | limit 0.02; v9's corner is 17 mm further out |
| ... bonded bound | 0.0055 mm | 0.0064 mm | |
| 20 N hand load, worst corner | 0.0129 mm | 0.0166 mm | on the studs; see judgement call 4 for when a corner gives on its spring |
| Payload x3 on the bed, stiffness bonded / screwed | 25,165 / 16,051 N/mm | **40,632 / 25,462 N/mm** | the deck closes the rectangle; the bed sits close on it |
| Carrier bounce, estimate sqrt(k_screwed / m) / 2 pi | 304 Hz | 370 Hz | hand estimate, no modal case of the carrier |
| Bed plate's first mode on its mounts | not analysed | 369 Hz (FEA, rigid seats) | 206 to 232 Hz by plate theory with pinned corners |
| Nut seating at the LSC-015 budget (0.142 mm) | a front nut unloads (-0.6 N); 1 kg then sags 0.0185 mm | **all seated, least margin 9.4 N** | |
| Load a nut loses per mm of height error | 87 to 89 N/mm | 32 to 52 N/mm | guides resist tilt less (webs) |
| Bed level change over the travel from lead error | 0.071 mm | 0.077 mm | re-levelled at each print start by Z_TILT_ADJUST |
| Nut misalignment over the travel (99.7 %) | up to 3.4 mm (screws bend 0.8 mm) | 2.3 to 2.5 mm (inside the 2.6 mm float) | |
| Hot bed (+60 K): surface rise at centre / plate out of flat | 0.062 / 0.054 mm | 0.083 / 0.035 mm (studs slip); 0.206 / 0.247 mm (bound: all stuck) | limit 0.1 on the first |
| Bed heat-up to 60 / 80 degC | 334 / 588 s | 295 / 538 s | same 180 W; less plate mass, more surface |
| Resonance X / Y | 77.4 / 69.0 Hz | 77.4 / 69.0 Hz | gantry unchanged |
| Acceleration an owner would run | 8,400 (5,800 to 13,500) mm/s^2 | the same | |
| Step-loss ceiling | 24,000 mm/s^2 | the same | |
| Cross-track RMS / worst | 0.0101 / 0.101 mm | the same | |
| Frame stiffness at the nozzle, screwed X / Y | 1,450 / 1,921 N/mm | 1,450 / 1,920 N/mm | |
| Benchmark time | 2,571 s | 2,571 s | melt-rate bound |
| Full verify time | 35 min | 67 min | the bed's FEA model is twice the size |

The scorecard does not see this revision: its figures are the gantry's, and the twin has one Z drive and no bed
dynamics. They were re-run to confirm that nothing moved. A firmware-in-the-loop print (real Klipper, the Octopus's
STM32F446 dictionary, `examples/motor_bracket.py:bracket`) was run on v9 for the viewer: clean, 3,891 s, nozzle within
0.055 mm of the G-code path.

## Vendor data: what is and is not verified

No maker's or seller's site for the new parts could be reached: the session's network proxy refused centuryspring.com,
mwcomponents.com, halder.com, 3djake.com, mcmaster.com, leespring.com, tronxy3d.com and every other one tried. Nothing was
downloaded. Each new part is recorded from web-search result snippets of the maker's own page, source level
"secondary", listed by the ratings verifier as unverified:

| Part | Record | Read | Not known |
|---|---|---|---|
| Die spring DJ-8X20YCS | `mechloop/parts/vendor/century_spring_dj8x20.json` | 8 hole, 4 rod, 20 free, 7.6 N/mm, three load points | coil diameters (drawn as a tube), solid height, temperature limit, mass, price |
| Thumb nut DIN 466 M4 | `halder_din466.json` | 16 x 9.5 mm, collar 8, knurl 3.5, 6.7 g | thread length, price; M3 / M5 rows |
| 257 mm PEI sheet | `threedjake_pei257.json` | size, magnetic base, 120 degC | steel thickness (0.4 from another listing), **magnetic base thickness (1.5 mm drawn, a stand-in)**, mass, flatness, price |

Also unverified: that M4 x 35 countersunk screws are stocked fully threaded; the 190 x 180 mm heater pad (the
catalogue's pad is generic; a custom size).

## Not tested, not checked

- No full-machine modal analysis; the carrier's bounce frequency is a hand estimate.
- Friction at the levelling points; spring fatigue and relaxation at 80 degC; creep of the thumb nuts.
- Fatigue of the carriage plates' webs.
- A temperature map of the plate (heater smaller than the print area).
- The digital twin has one Z drive and no bed dynamics: the scorecard's resonances and accelerations are the gantry's
  and are unchanged by this revision; they were re-run to confirm that.
- The assembly order in BUILD.md is the simulation's, part by part in the machine; the practical order (carrier built
  upside down on the deck) is in the build package's stage notes.
- As v8.2: bolt preload and contact, buckling, belt tooth load, cable paths, the lead-screw motors' thrust rating.
What was run for this revision, all on 2026-11-18: the full `verify` (67 min, every verifier, report above); `score
--assembly` (59 min); `tune` (Klipper's shaper, pressure-advance and bed-mesh code on the twin); one firmware-in-the-loop
print; the viewer export with the assembly simulation; the build package with its drawings; the review data; and the
whole test suite, twice, the second time on the final code: 485 passed in 16 min (`pytest -q`, 13 of them new in
`tests/test_v9_support.py`). Not run: `score --firmware klipper` (the real firmware planning every benchmark print);
any test of the generated drawings beyond the generator's own checks; nothing physical.

## Open items

1. **Decide on proposals A to D.** The bed is larger than the gantry can use.
2. **Front 34.5 mm of the print area is not probed** (proposal A removes it).
3. **Springs, thumb nuts, print sheet**: check against the makers' pages before ordering; measure the magnetic
   base's thickness and re-set the probe's z_offset; get the spring's temperature limit.
4. **Fully threaded M4 x 35 countersunk screws**: confirm stock, or cut down M4 x 40.
5. **Four points or three**: the owner's call (judgement call 1).
6. **Thumb nuts held by spring preload only**: paint-mark and re-check; a second (jam) thumb nut is the fix if they creep.
7. **Heater coverage** of the 214.5 mm print length: measure on the machine, or order a 190 x 200 pad with clipped corners.
8. **Lead-screw motors' thrust rating** (about 16 N each, none stated) and datasheet: as v8.2.
9. **Screw cut to 258 mm** by the builder.
10. **Rear nut's float 98 % used** at the 99.7th percentile: align each motor plate to its nut at assembly, as v8.2.
11. **Web fatigue** of the carriage plates: inspect.
12. As v8.2: thread backlash at the Z nuts, power-off self-locking by calculation only, Octopus heater / fan limits,
    part cooling not modelled, frame stiffness not in the twin.

## Files

- `designs/printer_v9.py`; `out/printer_v9/report.json`, `scores.jsonl`
- catalogue: `mechloop/parts/batch8.py`, `mechloop/parts/vendor/century_spring_dj8x20.json`, `halder_din466.json`,
  `threedjake_pei257.json`; `docs/VENDOR_DATA.md` (eighth batch)
- checker changes: `mechloop/tolerance/__init__.py` (`_rail_set`), `mechloop/verifiers/bed_support.py` (floating mounts),
  `mechloop/verifiers/fea.py` (mesher retry, sliding free, stuck bound), `mechloop/model.py` (`ThermalCase.stick`);
  `tests/test_v9_support.py`; `tools/build_package.py` (v9 stage notes and open items)
- `docs/build/printer_v9/`, `viewer/`, `review/data.json` (generated); v8.2's viewer and review data kept in
  `viewer_v8_2/` and `review_v8_2/`
