# printer_v10: X travel to the end of the beam, a bed sized to the reach, three levelling points

Everything here is simulated. Nothing has been built.

`designs/printer_v10.py` starts from a copy of `designs/printer_v9.py` (v9 was not edited). The owner approved four changes:
more nozzle travel in X without changing the frame; a bed and print sheet sized to that travel; three levelling points
instead of four; and a figure for how far the three Z motors may tilt the carrier.

The frame (every extrusion, the 340 x 373 x 404 mm cube, the 420 x 420 x 480 mm envelope), the Z rails and motors, the
carrier's 2020 square and the electronics are v9's and were not changed. A test checks that
(`tests/test_v10_support.py::test_v10_frame_extrusions_and_envelope_are_v9s`).

It passes all 13 verifiers with **0 errors and 58 warnings** (`verify designs/printer_v10.py`, report in
`out/printer_v10/`; v9: 0 and 51), all 33 requirements met (v9's 28, re-pointed where the design changed, plus five for
v10). Every warning is listed below.

## The short answers

| Question | Answer |
|---|---|
| X travel | **229.6 mm** working (232.6 mm mechanical). v9: 180. The owner's estimate was 210 to 230. |
| What sets X now | Both ends: the X guide block on its rail. The rail is as long as the beam (288 mm), the beam is as long as the space between the two Y blocks allows (2.5 mm left each side), the block is 45.4 mm long and 5 mm of rail is kept beyond it. The toolhead was arranged to fit that travel and no more: at the ends the Roto is 2.0 mm from the left top rail and the fan's plenum 2.4 mm from the right one. |
| Y travel | 214.5 mm, unchanged. Confirmed at its limit; nothing cheap is left (see "Y travel"). |
| Print area | **229.6 x 214.5 mm, 492 cm2** (v9: 180 x 214.5, 386 cm2): +28 %. |
| Bed | 235 x 235 mm PEI sheet (catalogue `print_sheet_pei235`) on a 241 x 241 x 12.7 mm MIC-6 plate, centred on the nozzle's reach. The print area is **89.2 % of the sheet** (v9: 58 % of a 257 mm sheet). |
| Heater | 230 x 207 mm, 180 W: the print area's whole width and 96.5 % of its area. The studs' washers keep it 3.75 mm short of the print area's front and rear edges. |
| Levelling | Three sprung studs with thumb nuts: front left (fitted hole), front right (slot), rear centre (free). Same stack as v9, no tapped aluminium. |
| What three points cost | The two rear print corners are 115 mm from the rear stud, so the plate went from 6.35 to 12.7 mm (+0.82 kg on Z). 1 kg on the worst print corner lowers it 0.012 mm (limit 0.02; v9 0.008). |
| Motor tilt | One Z motor may stand **1.24 mm** out of the plane of the other two (0.97 mm across the print area) before the first limit (the nuts' seats); guide blocks and webs follow at 1.72 and 1.78 mm. Every nut stays on its weight-bearing flank up to **0.40 mm**. |
| Division of labour | Thumb nuts: one-time coarse tram, until `Z_TILT_ADJUST`'s first pass asks for less than 0.40 mm at any screw (each nut has +/-1.5 mm). Motors: everything after that; routine need is 0.14 mm; never more than 1.24 mm. |
| Proposal A (probe without Y offset) | Does not work with this sensor and toolhead; not built. The front 34.5 mm stays unprobed, and with the sheet now close to the reach so do 9.3 mm at each side (see "Proposal A"). |

## What changed against v9

| | v9 | v10 |
|---|---|---|
| X rail | stock MGN12 250 mm | HIWIN MGNR12R cut to 288 mm, the beam's length |
| X hard stops | two rail-stop plates | a tab on each Y plate against the tool plates' edge, 1.5 mm beyond the travel; the two stop plates are gone |
| X motor and idler | on the beam's front face, pulley centres at +/-118 | still bolted to the beam's front face, but standing outboard of the block's travel over the Y plates: pulley centres -141.8 / +142.8; belt plane 8 mm higher; plates of v9's gauges, each with a wing over the Y plate |
| Y plates | 19.5 mm deep behind the beam's centre line over the beam; a land on the left for the X switch | 11 mm deep over the beam (in front of the X block's path); stop tabs; a land on the right for the X switch |
| Toolhead | nozzle on the block's centre line; HeaterCore's lead sleeve to the left | nozzle 15.5 mm left of the block's centre, so the Roto and the fan's plenum are centred on the block (31.7 left, 31.3 right); lead sleeve forward, under the tool plates |
| Tool plates | 46 x 56 mm outline, notch for the X switch, window | bottom edge 2 mm higher; front plate: striker tab for the X switch; both: upper right corner cut away for the Roto's motor lead |
| X switch | under the left Y plate's land; X homes at minimum | on top of the right Y plate's land; X homes at maximum; lead in the beam's top slot |
| Y switch | plate on the right top rail's inner face | bent 5052 bracket in the right top rail's top slot, behind the Y rail's end; worked by the right land's rear edge |
| Toolhead loom | anchored on the right top rail's inner face, drops in the rear right corner | anchored on top of the back rail, drops down the outside of the back wall |
| Print sheet | 257 x 257 | 235 x 235 |
| Bed plate | MIC-6 265 x 265 x 6.35, 1.25 kg | MIC-6 241 x 241 x 12.7, 2.07 kg, centred at x -15.5 |
| Bed mount | four studs at (+/-104, -93.5 and 102.5), M4 x 35, spring 14 mm (45.6 N), +/-2 mm, gap 18.8 mm | three studs at (-86, -105), (86, -105), (-15.5, 114), M4 x 40, spring 12 mm (60.8 N), +/-1.5 mm, gap 16.8 mm |
| Deck | ten M5, four stud holes | twelve M5 (one straight outboard of each stud), three stud holes; outline unchanged |
| Heater | 190 x 180 mm | 230 x 207 mm, same 180 W |
| Z rails | centred on the blocks' travel | where v9 had them in the frame (the blocks ride 4.85 mm lower; the rails would otherwise meet the control board) |
| Nut plates | 4.75 mm 6061 | 6.35 mm 6061, same outline (the bed is heavier) |
| Carrier square, carriage plates, keepers, motor plates | | unchanged |

## X travel: what was done and what limits it

v9's proposals B and C (redrawn rail stops, belt clamp, left Y plate's land; a longer rail) were worth about 197 mm together.
Going to the end of the beam needed four more things.

1. **Rail as long as the beam.** 288 mm. HIWIN's catalogue (in the repository) allows any length to 2000 mm with end
   distances of 5 to 20 mm; this one has 11 holes and 19 mm ends. It is not a stock length (see "Vendor data").
2. **Motor and idler outboard of the block's travel.** The belt clamp on the toolhead is 30 mm wide, so the pulleys must
   stand 26 mm beyond the block's last position: over the Y plates, outboard of the beam's ends. They are not "above or
   behind" the beam as the brief suggested: the mounts keep their two M5 bolts on the beam's front face (inside its ends)
   and each has a wing that reaches outward 1.5 mm above the Y plate and the heads of the Y block's screws. That is why
   the belt plane is 8 mm higher. Behind the beam is the X rail and the toolhead; above it the belt itself.
3. **Y plates out of the block's path.** Over the beam they now end 2 mm in front of the X block. From x 140.8 outward
   they reach back as before, and a tab reaches further back to stop the tool plates' edge.
4. **Toolhead centred on the block.** The Roto reaches 16.2 mm left and 40.9 mm right of its nozzle, the fan's plenum 46.8 mm
   right. With the nozzle on the block's centre line (v9) the right side would meet the top side rail 15 mm before the
   block reached the rail's end. The tool plates now sit 15.5 mm to the right of the nozzle. "Narrow the tool plate" was not
   needed: the plates are as wide as the block (46 mm against 45.4) and the Roto is wider than both.

Clearances at the ends of the mechanical travel, measured on the model (the motion verifier found no collision over the
whole travel; these are what would close first):

| End | What | Clearance |
|---|---|---|
| both | X block on its rail (5 mm is the requirement) | 5.0 mm: **the limit** |
| both | tool plates' edge to the Y plate's stop tab (the hard stop) | 1.5 mm |
| left | Roto (fan side) to the left top rail's inner face | 2.0 mm |
| right | part fan's plenum to the right top rail's inner face | 2.4 mm |
| right | plenum to the Y switch's bracket (with Y at its rear end) | 2.0 mm |
| left / right | belt bracket to the X pulley / idler | 3.0 / 3.0 mm |
| left | belt bracket to the X motor's plate | 2.0 mm (as v9) |
| both | tool plates to the Y blocks | 7.2 mm |
| both | Roto to the stop tabs, front to back (the Roto passes behind them) | 1.9 mm |

So the toolhead and the rail run out together, which was the aim: 0.5 mm after the hard stop the Roto would touch the
left top rail.

**What would give more, none of it built.** (a) A shorter X block: an MGN12C is 34.7 mm long against the H's 45.4, worth
10.7 mm, at the cost of the toolhead's stiffness against turning on its block (already the soft term in the twin's X
figure); not in the catalogue.
(b) Less than 5 mm of rail beyond the block: up to 6 mm. Both then need a toolhead narrower than 63 mm, which means moving
the part fan. (c) A wider frame (v9's proposal D). The 5 mm figure and the H block are v9's and were kept.

## Y travel: confirmed at its limit

| End | What | Clearance at the end of over-travel |
|---|---|---|
| front | Y plates to the Y idlers | 2.05 mm |
| front | the X mounts' bolt heads on the beam's front face to the top front rail | 3.5 mm (as v9) |
| front | Y blocks on their 300 mm rails (5 mm kept) | 0.4 mm spare |
| front | the 420 mm envelope: Y idlers at y -193.9, Y motors at 225.2 | 1 mm |
| rear | part fan's screws to the top back rail | 1.44 mm |

The Y idlers cannot move forward without leaving the envelope, and behind the toolhead there is the fan and then the back
rail. Moving the X mounts off the beam's front face would free 9 mm there, but the idlers and the envelope stop the gantry
2 mm later. Nothing was changed in Y.

## Proposal A: a probe with no Y offset. It does not work; here is why

The probe is an unshielded OMRON E2E-X5ME1. Its data sheet asks for a 40 mm diameter round the head free of metal.

- **Beside the nozzle in X.** The Roto's body is above the nozzle from 16.2 mm left to 40.9 mm right of it; a 12 mm barrel
  has to stand outside that, about 27 mm left or 49 mm right of the nozzle. That widens the toolhead by about 20 mm or
  more, which comes straight off the X travel, and then leaves an unprobed strip of the same 27 or 49 mm in X. Worse on
  both counts.
- **In front of the nozzle.** The tool plates are 15 mm in front of it.
- **Any fixed offset** leaves a strip as wide as the offset unprobed somewhere, unless the axis has that much travel beyond
  the print area. X now has none to spare (229.6 of 235) and Y never had.
- **A nozzle-contact probe** (the nozzle is the probe: load cell, sliding toolhead) is the only kind with no offset. The
  catalogue has none, and it is a toolhead redesign. Proposed, not built.

What v10 has instead: the same probe, 34.5 mm behind the nozzle. Unprobed: the front 34.5 mm, and, because the checker
keeps the probe 12 mm inside the sheet's edge, 9.3 mm at each side and 1.75 mm at the rear. In v9 the 257 mm sheet was wide
enough to hide the side strips; sizing the sheet to the reach exposes them. Three levelling points cannot twist the
plate, so what the mesh misses there is the plate's own bow (MIC-6 stock flatness 0.38 mm over the whole plate; held flat
by its own 12.7 mm, not by its mounts).

The same metal-free zone decided where the HeaterCore's lead sleeve points. Backward, anywhere within the Roto's width, it
is inside the zone (the checker caught the first attempt); to the left, as v9, it would meet the top side rail 14 mm
before the Roto does. It points forward, 2.2 mm under the tool plates.

## Bed and sheet

| | |
|---|---|
| Nozzle reach | x -130.3 to 99.3, y -102.75 to 111.75 (centre -15.5, 4.5) |
| Sheet | 235 x 235 mm: 2.7 mm beyond the reach at each side, 10.25 mm at front and rear |
| Other common sheet sizes considered (none is in the catalogue; not searched) | 220 x 220 (9.6 mm of the X travel would have no sheet under it), 254 x 241 (80 % used), 257 x 257 (75 %) |
| Plate | 241 x 241 x 12.7 mm MIC-6, 3 mm of margin round the sheet; 6 mm from the left Z rail, 37 mm from the right one |
| Carrier | v9's square and deck outline (270.8 x 281.8 mm). Not resized: its width is set by the Z rails in the walls. The bed sits 15.5 mm left of its centre |

The bed is off the carrier's centre because the Roto is not symmetrical about its nozzle and the frame is. The three
screws carry 21.0 / 18.1 / 15.0 N (rear, front left, front right) instead of v9's 18.0 / 14.0 / 14.3.

## Three levelling points

Layout. Two studs at the front, 172 mm apart, 11.4 mm inside the square's front member; one at the rear on the bed's
centre line, 11.4 mm inside the rear member. Each is 58 to 74 mm from a lead-screw nut and has a deck bolt straight
outboard of it. They span a triangle of 188 cm2; the bed's own weight divides 0.30 / 0.20 / 0.50 between them (front left,
front right, rear). All three are outside the print area in Y (2.25 mm in front of it, 2.25 mm behind), which is what lets
the heater run the full width.

Why this triangle and not a better one for sag. A plate on three points always leaves corners hanging. Plate theory (a
thin-plate finite-element estimate, not the verifier) for 1 kg on the worst print corner of the plate alone:

| Plate | this layout (front pair, rear centre) | pair moved 60 mm in from the rear, one at the front | v9: four studs, 6.35 mm |
|---|---|---|---|
| 6.35 mm | 0.064 mm | 0.044 mm | 0.001 mm |
| 9.525 mm | 0.019 mm | 0.013 mm | |
| 12.7 mm | 0.008 mm | 0.006 mm | |

The second layout sags a third less but puts two studs 25 mm inside the print area, where the heater would need holes and
the studs would stand in mid-deck, far from a member. With either layout the 0.02 mm limit (plate plus carrier) needs
12.7 mm. So: the layout that keeps the heater whole and the studs beside the members, and the thicker plate.

What the verifiers say, against v9's four points:

| | v9: four studs, 6.35 mm plate | v10: three studs, 12.7 mm plate | |
|---|---|---|---|
| Bed sag, 1 kg at the worst print corner (screw-only bound) | 0.0081 mm | **0.0119 mm** | limit 0.02. Worst: rear left. By corner: front left 0.0052, front right 0.0035, rear left 0.0119, rear right 0.0115; centre 0.0022 |
| ... bonded bound | 0.0064 mm | 0.0108 mm | |
| 20 N hand load, worst corner | 0.0166 mm | 0.0242 mm | limit 0.2 |
| Does a 20 N hand lift the bed off a thumb nut? | in the worst case, yes: at the weak end of the range with the 1 kg print on that corner 16 N is left between nut and deck, less than the hand's 20 | **no**: the same worst case leaves 26 N at the rear stud, 6 N with the hand on that corner as well; on an empty bed a 20 N hand on any print corner leaves 16 N or more | the springs are set at 8 mm instead of 6: 49 N at the weak end against 30 |
| Spring | 6 mm compressed, 45.6 N; 30.4 to 60.8 N over +/-2 mm | 8 mm compressed, 60.8 N; 49.4 to 72.2 N over +/-1.5 mm | the maker lists deflection to 10 mm; v10 uses 6.5 to 9.5 |
| Worst stud's load (bed share + 1 kg where it loads that stud most) | 14.9 N | 23.4 N (the rear stud: half the bed, 13.5 N, and the payload on a rear corner) | bed without payload 2.70 kg (v9 1.95) |
| Preload margin at the weak end of the levelling range | 2.04 | 2.11 | requirement: 2 |
| Levelling range per nut | +/-2.0 mm | +/-1.5 mm | the stack-up needs 0.75 mm (99.7 % of builds): half the range |
| Carrier acceleration that lifts the bed off its nuts | 31 m/s2 | 30 m/s2 | Z runs 0.2 |
| Bed on its springs alone (only if preload is lost) | 16 Hz | 12.5 Hz | |
| Plate's first bending mode on its studs (FEA, rigid seats, 1 kg spread on it) | 369 Hz | 408 Hz | limit 100 |
| Hot bed (+60 K), as designed: surface rise at centre / plate out of flat | 0.083 / 0.035 mm | **0.0985 / 0.016 mm** | limit 0.1 on both. The rise passes by 0.0015 mm; see judgement call 4 |
| ... bound, every stud stuck | 0.206 / 0.247 mm | 0.131 / 0.058 mm | three points cannot bow the plate the way four can |
| Stud movement in the deck at +60 K | 0.29 (slot), 0.28, 0.40 mm | 0.24 (slot), 0.33 mm (oversize hole, 0.75 mm radial) | |
| Can the mounts twist the plate? | yes: about 56 N/mm at a corner, under the springs' preload | no | |
| Payload x3 on the bed, stiffness at the front right print corner, bonded / screwed | 40,632 / 25,462 N/mm | 61,535 / 38,799 N/mm | the same probe point as v9. At a rear corner, where v10 is softest: 15,125 / 11,327 N/mm (first full run, 4.75 mm nut plates; not re-run) |
| Carrier bounce, estimate sqrt(k_screwed / m) / 2 pi | 370 Hz | 422 Hz with the front-corner figure, 228 Hz with the rear-corner one | hand estimate, no modal case of the carrier |
| Nut plates | 4.75 mm: 0.049 mm, safety 17.6 under 3 x the bed's weight on one plate | 6.35 mm: 0.029 mm, safety 22.6 | limit 0.05. With 4.75 mm the heavier bed gave 0.067 mm |
| Bed heat-up to 60 / 80 degC (180 W, one-lump model) | 295 / 538 s | **469 / 847 s** | duty to hold: 28 % / 49 % |

What three points buy: the mounts cannot twist the plate, the hot plate stays flatter, and one stud set less. What they
cost: the sag at the rear corners, the heat-up time and 0.8 kg on Z, all through the thicker plate.

## Motor tilt: how far the Z motors may level the bed

New in the bed-support checker (`fea.bed_support.tilt_allowance`, also a requirement in the design). One screw is driven
h mm out of the plane of the other two; the carrier is a rigid body on its three blocks, their flexure plates and its
nuts. Everything is linear in h, so each limit is a height.

What resists the tilt. A block cannot turn on its rail. When the carrier tilts about an axis square to a wall, that wall's
carriage plate must turn in its own plane against its block: the 24 mm wide web bent edgewise, 4.2e6 N.mm/rad, in series
with the block's own 3.5e6. About the other axis the same web bends the easy way (1.9e4 N.mm/rad). So the two side blocks
resist front-to-back tilt, the rear block resists side-to-side tilt, and each does it through one web.

Per millimetre that one screw stands high:

| | rear screw | a front screw |
|---|---|---|
| Carrier tilt | 3.66 mrad | 3.61 mrad |
| Bed level change across the print area | 0.78 mm | 1.11 mm |
| Moment on a side block, about its mount's normal | 7.0 N.m | 3.5 N.m |
| Moment on the rear block, about its mount's normal | 0 | 6.0 N.m |
| Stress in the most loaded web (edgewise bending, with a stress concentration of 1.7, assumed) | 78 MPa | 69 MPa |
| Load the high screw's nut gains / the others lose | +52 / -26, -26 N | +32 / -26, -6 N |

Limits, as the height one screw may stand out of plane:

| Limit | Height | Basis |
|---|---|---|
| A nut leaves its weight-bearing flank ("seated range") | **0.40 mm** (rear), 0.47 and 0.57 mm (front) | the moving mass seats the nuts with 21.0 / 18.1 / 15.0 N. Not damage: the nuts are captive, but beyond this the bed's height at that screw is loose by the thread's backlash and the motors no longer set the plane exactly |
| A nut's flange rocks out of its seat | **1.24 mm** | 0.1 mm of keeper play over the 22 mm flange: 4.5 mrad. Declared in the design (`drive["nut_tilt_allowance_rad"]`) |
| Guide block: static moment and load over 3 | 1.72 mm (side blocks, rear screw) | HIWIN MGN12H static moments 36 to 38 N.m; safety 3, the figure the checker already asks under the bed's weight |
| Carriage plate's web: half of 6061-T6's yield (138 MPa) | 1.78 mm | the web's dimensions are declared on the block (`guide_float["web"]`) |
| Front screws: rear block / rear web | 2.0 / 2.0 mm | |

So: **overload-free up to 1.24 mm at one screw (0.97 mm across the print area)**, 8.8 times the routine height error of
0.142 mm (two screws at opposite lead limits over the travel plus two full steps at power-up, the LSC-015 budget). The
requirement asks for 3 times.

**Division of labour.**

- As built, before any adjustment, the bed is up to 1.49 mm out of level across the print area (tolerance verifier, 99.7 %
  of builds). That is more than the motors may take (0.97 mm) and far outside their seated range (0.31 mm across the
  print area), so **the thumb nuts do the first tram**: +/-1.5 mm each, of which the stack-up needs 0.75 mm.
- Tram with the thumb nuts until the first pass of `Z_TILT_ADJUST` asks for **less than 0.4 mm at every screw** (a quarter
  turn of a thumb nut is 0.175 mm, so this is two or three rounds of quarter turns).
- From then on **the motors level the bed at every print start**. Their routine work is 0.14 mm.
- **Never more than 1.2 mm from the motors.** Klipper's `[z_tilt]` has no limit of its own; if it ever asks for more than
  about 1 mm, something has moved and the thumb nuts are the tool.

What the figure rests on, and what is not in it. The carrier is rigid in this model (its flexure would add tilt for
free). The ZF blocks' 4 to 10 um of clearance is ignored (it would add about 0.3 mrad of free turning, 0.08 mm at a screw).
The web's stress concentration and the safety of 3 on the blocks are judgements. The block's own turning stiffness uses
40 N/um, assumed, because HIWIN publishes no rigidity for the ZF class. Fatigue of the webs is not analysed: at the routine
0.14 mm the web sees 11 MPa. The stiffness that sets all of this is the web bent edgewise; a web with a narrow neck would
let the motors do several millimetres, and is the change to make if the owner wants the thumb nuts gone (proposed, not
built).

## Judgement calls

### 1. Rail cut to length, flush with the beam

229.6 mm needs a 288 mm rail. A stock 250 gives 191.6 mm; nothing stocked lies between 250 and 300, and 300 does not fit
between the Y blocks. HIWIN's catalogue allows the length; the supply is unverified (see below). If the rail arrives
short, the 5 mm beyond the block shrinks at one end; the travel does not. The 5 mm itself is v9's requirement and was
kept.

### 2. The bed is 15.5 mm off the machine's centre

Centring the toolhead on its block puts the nozzle's travel at x -131.8 to 100.8. The alternative, a toolhead symmetrical
about its nozzle, is 82 mm wide (twice the Roto's 40.9 mm side) and costs 19 mm of travel. The carrier stays centred
(the Z rails are in the walls); the bed sits left on it, 6 mm from the left Z rail. The front screws carry 18.1 and 15.0 N
instead of v9's 14.0 and 14.3.

### 3. Plate 12.7 mm, nut plates 6.35 mm

See "Three levelling points". The plate's thickness follows from the 0.02 mm sag limit, which was not loosened; the nut
plates' from the nut_thrust case's 0.05 mm, also not loosened. Both checks scale with the bed's weight, and the heavier
plate is what the three points cost. A 9.525 mm plate would sag about 0.023 mm on the same model (the plate's share
scaled by plate theory, not run).

### 4. Hot-bed surface rise: 0.0985 mm against a limit of 0.1

The margin is 0.0015 mm of an FEA figure that moved by 0.0002 mm between two meshes of nearly the same geometry. The limit
is v9's own (it had 0.083). The rise is taken out when the probe's z_offset is calibrated hot, which the build package
asks for; the plate's flatness under heat, which nothing takes out, is better than v9's (0.016 against 0.035 mm). The
limit was not changed and the case passes, but it should not be read as margin.

### 5. X motor plate: 3.175 mm, and the belt 8 mm higher

A 4.75 mm plate was tried for the overhung motor. It brought three laser-cutting warnings (M3 holes under the sheet's
thickness) and took 1.6 mm from the 3.5 mm between the plate's bolt heads and the top front rail at the front of Y. With
the belt plane 8 mm above v9's the motor's body clears the Y block's screw heads by 2.1 mm vertically, and the plate stays
v9's gauge. The wing that carries half the motor beyond the beam's end is not in any stiffness case (the belt's pull is in
the plate's own plane).

### 6. X belt out of plane in 6 % of builds

New warning. The idler and the belt clamp end up 1.5 mm out of plane at the 99th percentile and more than 1 mm apart in
5.8 % of builds (limit 5 %, inside its sampling error; v9 2.1 %). A trial with the pulleys back at +/-118 gave 3.9 %, so
about half of the loss comes with the pulleys' distance (285 mm apart against 236); the rest was not traced. Belt height
and plate gauge made no difference. The fix is at assembly: shim the idler on its spacer. Not designed out.

### 7. Endstops

X homes at the right end now. The switch could not stay on the left: the Roto is 8.7 mm wider than the tool plates on that
side and passes behind the Y plate where the switch hung. On the right it sits on top of the Y plate's land, outboard of
the Roto's reach, and a 4.9 mm tab on the front tool plate reaches past the Roto to work it. Its screws' nuts pass 1.3 mm
above the right Y rail; the front one's washer is 0.7 mm from the Y block (warning; a normal washer, not a large one, on
the 3.6 mm slot). The lever engages the 3.175 mm tab over 1.8 mm of its length: check on the machine.

The Y switch's old plate stood where the toolhead now passes. Its bracket is one more bent part (5052, 2.286 mm).

### 8. HeaterCore's lead sleeve points forward

Forced by the probe's metal-free zone and the side rails (see "Proposal A"). The leads have to turn back under the beam to
reach the toolhead loom. Not tried; open item.

### 9. Toolhead loom outside the back wall

The toolhead comes within 2.4 mm of the right top rail and 1.4 mm of the back rail, so nothing can be clamped in the rear
right corner where v9's loom dropped. The loom is clamped on top of the back rail and goes over its rear edge on a 30 mm
radius (the 10 mm bundle needs 26), down the outside beside the right Y motor (inside the Y motors' depth, so inside the
envelope) and in again over the bottom back rail. 480 mm of free loom (v9 460).

### 10. Stud holes in a 12.7 mm plate

4.5 mm holes and 8.96 mm countersinks in 12.7 mm plate, 6.5 mm from the edge: the laser-cutting checks warn (holes narrower
than the sheet; web under one thickness). They are drilled and countersunk, not laser cut. Whether SendCutSend's
countersinking service takes them in this gauge was not checked.

### 11. Sub-assemblies (a guideline added while this revision was being made)

`docs/DESIGN_GUIDELINES.md` gained a section during this work: design the machine as sub-assemblies, validate each on its
own, assemble the validated sub-assemblies in place, and write the assembly plan down as part of the design. It says no
check exists yet. Where v10 stands:

| | |
|---|---|
| Declared in the design and checked as bench units by the assemblability verifier (built on the bench with driver access among their own parts, then installed as one unit) | ten, as v9: `electronics`, `z_drive_rear` / `_fl` / `_fr`, `bed_unit` (plate, three studs with their washers and lock nuts, heater, cut-off, springs and seats), `x_drive`, `x_idler_unit`, `y_drive`, `y_drive_l`, `part_cooling`. All ten were used; 578 of 578 parts placed, 195 of 195 fasteners drivable |
| Built as units in practice but NOT declared, so not checked as units | the carrier (square, deck, six brackets, nuts and keepers: the build package's stage notes build it upside down on the deck), the gantry beam (beam, X rail and block, both Y plates), the toolhead (tool plates, Roto, hot side, probe holder, duct) |
| Assembly plan | stated in words in the build package's stage notes (`tools/build_package.py`, generator text) and in `docs/build/printer_v10/ASSEMBLY.md`; the order in BUILD.md is found by the search. It is not data in the design file, and no check runs against it |

Declaring the three missing units changes the assemblability result and needs a full re-verify; it was not done in this
revision because the guideline arrived after the design had been verified. It is the first thing to do in the next one.

### 12. Guideline conflicts

| Guideline | v10 |
|---|---|
| 2D laser-cut over CNC | every made part is a flat or bent laser-cut plate; no CNC part |
| No load-bearing printed parts | none (the five printed parts are v9's holder, duct and covers) |
| No tapping aluminium | none: T-nuts, through-bolts with nuts, PEM nuts where v9 had them, the blocks' and motors' own threads |
| Washers on slots and soft parts | X switch: washers under head (on the board) and under the land's slot; bed studs as v9 |
| Named materials | 6061-T6, 5052-H32 (three bent parts: X idler plate, X tension anchor, new Y switch bracket), MIC-6, 304 |
| SendCutSend gauges | 1.6, 2.286, 3.175, 4.75, 6.35 and 12.7 mm, all stocked for their alloys in the shop profile |
| Bends only in 5052 | yes |
| Conflict | **holes under the sheet's thickness** in the nut plates (5.5 and 4.8 mm in 6.35) and the bed plate (above); **countersinks**, three (v9 four); **a normal washer on a slot** where a large one does not fit (X switch) |

### 13. Checker changes made for this design

One, in `mechloop/` with tests in `tests/test_v10_support.py` (14 tests); it is a judgement in the checker and is said here.

- **Bed support, allowable screw tilt** (`mechloop/verifiers/bed_support.py`, `tilt_allowance`; documented in `AGENT.md`).
  For several screws on independent motors: the height at which a nut's seating load reaches zero, and the heights at
  which a guide block's static moments and load (added, over a safety of 3), a declared flexure web (bending and torsion,
  half of yield) or a declared nut seat (rocking angle) reach their limits. New metrics under
  `fea.bed_support.tilt_allowance`; new findings `z_tilt_allowance` (info), `z_tilt_allowance_exceeded` (warning, when
  the routine height error is already more than the allowance) and `z_tilt_allowance_not_evaluated` (warning). Nothing
  that existed was changed: v9's report would gain the metrics and one info finding. The safety of 3, the half-yield
  limit and the linear adding of moment shares are the judgements; the tests check the arithmetic against hand sums
  (tilt per mm from the screws' triangle, block moment from the series stiffness, web stress from the declared section),
  not the judgements.
- No existing check, limit, load or tolerance was loosened for v10. Two of the design's own requirement texts were
  re-pointed (spring preload and plate growth now work for three studs by statics), and v9's `carrier_square` check now
  also asserts the deck's outline is v9's.
- Catalogue: `print_sheet_pei235()` (batch 9, secondary source). `tools/build_package.py` gained v10's stage notes and
  open items (generator text, not a check).

## Verify, per verifier

Full run, 2026-11-18, about 66 minutes (FEA 45 of them).

| Verifier | Errors | Warnings | What the warnings are |
|---|---|---|---|
| geometry | 0 | 0 | |
| interference | 0 | 0 | |
| tolerance | 0 | 7 | (v9: 4) **new:** X belt out of plane in 6 % of builds; the X switch's front washer 0.7 mm from the Y block (closes in none of 3,000 builds); the front right screw's nut float 97 % used (v9 87 %; the percentile rests on a handful of builds). As v9: rear screw's nut float 98 % used, extruder screw to probe 1.31 mm, two part-fan screws to the top back rail 1.44 mm |
| manufacture | 0 | 27 | (v9: 22) **new:** nut plates x 3 (four holes each under the 6.35 mm thickness); bed plate x 2 more (stud holes narrower than 12.7 mm; 6.5 mm of web to the edge). As v9: bed countersinks (three now), motor plates x 9, both Y plates x 6, both tool plates x 3, no lead-in on the motors' pilots x 3. None on the new X motor plate, idler plate or Y switch bracket |
| practice | 0 | 14 | (v9: 15) FST-070 locking on 55 screws (frame motors, toolhead, gantry, the three nut pins); BLT-040 x 4, SHF-010 x 3, FST-050 (11 parts), FST-081 (M3 x 5 and M3 x 6 in MGN12H threads), LOC-006 (six adjustments name no lock). Gone: v9's single-T-nut warning (the rail stops) |
| ratings | 0 | 7 | as v9: `axial_load_rating_unknown` x 3 (18.4 N per motor now), M3 PEM nuts on oversize holes, washers on printed parts x 2, one stand-in (the magnetic base) |
| motion | 0 | 0 | |
| subsystems | 0 | 1 | bed mesh: front 34.5 mm, 9.3 mm at each side and 1.75 mm at the rear are not probed (v9: front 34.5 mm only) |
| electrical | 0 | 1 | `cutoff_depends_on_mcu` (as v9) |
| assemblability | 0 | 1 | `unsupported_step` (as v9); 195 of 195 fasteners drivable |
| fea | 0 | 0 | |
| printing | 0 | 0 | |
| requirements | 0 | 0 | all 33 pass |

Total 58 warnings (v9 51). The seven more: three on the thicker nut plates, two on the thicker bed plate, the X belt, the
X switch's washer, a second nut-float warning, less one practice warning.

The first full run (same day) failed on two things, both from the heavier bed: the nut plates (0.067 mm, limit 0.05) and
the spring preload (factor 1.79, limit 2). The design was changed for both (6.35 mm nut plates; springs at 8 mm and a
+/-1.5 mm range), not the checks. The figures above are from the second full run.

## Numbers against v9

`score --assembly` on both (v9: out/printer_v9/scores.jsonl, 2026-11-18 10:16; v10: out/printer_v10/scores.jsonl,
2026-11-18 23:03). FEA and tolerance figures are from each design's full verify.

| | v9 | v10 | |
|---|---|---|---|
| Errors / warnings | 0 / 51 | 0 / 58 | |
| X travel, working / mechanical | 180 / 183 mm | **229.6 / 232.6 mm** | +27.6 % |
| Y travel | 214.5 mm | 214.5 mm | |
| Print area | 180 x 214.5 mm, 386 cm2 | **229.6 x 214.5 mm, 492 cm2** | +28 % |
| ... of which probed | 180 x 180 mm (84 %) | 211 x 178.25 mm (76 %) | the sheet is no longer wider than the reach |
| Print sheet / share of it printed on | 257 x 257 / 58 % | **235 x 235 / 89 %** | |
| Bed plate | MIC-6 265 x 265 x 6.35, 1.25 kg | MIC-6 241 x 241 x 12.7, 2.07 kg | |
| Levelling points | four | **three** | |
| Bed to deck gap | 18.8 mm | 16.8 mm | |
| Total mass | 13.65 kg | 14.47 kg | +0.82 kg: the plate (+0.82), nut plates (+0.05), rail (+0.02), less a stud set, two stop plates and a smaller sheet |
| Moving mass X / Y / Z | 0.359 / 1.236 / 4.715 kg | 0.360 / 1.261 / **5.510 kg** | Z with the 1 kg payload in both |
| Drive margin X / Y / Z | 8.4 / 16.1 / 7.9 | 8.4 / 15.9 / 7.2 | requirement 3 |
| BOM cost (estimate) | $1,008 | $1,007 | the cut-to-length HIWIN rail is priced by the catalogue's generic rail formula ($17.5): expect more |
| Parts / fasteners | 584 / 195 | 578 / 195 | |
| Made (laser-cut or printed) parts | 39 | 37 | two rail stops gone; the Y switch's mount is still one part |
| Assembly time (estimate) | 138.1 min | 136.0 min | 236 placements held (269), 21 from below (20), 17 tool changes (18) |
| Bed sag, 1 kg at the worst print corner (screw-only bound) | 0.0081 mm | 0.0119 mm | limit 0.02 |
| 20 N hand load, worst corner | 0.0166 mm | 0.0242 mm | |
| Nut seating at the LSC-015 budget (0.142 mm) | all seated, least margin 9.4 N | all seated, least margin 10.4 N | |
| Load a nut loses per mm of height error | 32 to 52 N/mm | 32 to 52 N/mm | the guides are v9's |
| Allowable height of one screw out of plane | not worked out (the same checker on v9: 1.24 mm, seated to 0.35 mm) | **1.24 mm**, seated to 0.40 mm | new figure |
| Bed level change over the travel from lead error | 0.077 mm | 0.090 mm | wider print area; re-levelled at each print start |
| Bed out of level as built (99.7 %) | 1.45 mm | 1.49 mm | what the thumb nuts take out |
| Probe z_offset range needed (99.7 %) of 1.65 mm | 1.08 mm | 1.27 mm | 77 % of the range |
| Nut misalignment over the travel (99.7 %) | 2.3 to 2.5 mm | 2.4 to 2.6 mm of 2.6 mm float | two warnings instead of one |
| Hot bed (+60 K): surface rise at centre / plate out of flat | 0.083 / 0.035 mm | 0.0985 / 0.016 mm | limit 0.1 |
| Bed heat-up to 60 / 80 degC | 295 / 538 s | 469 / 847 s | same 180 W |
| Resonance X / Y | 77.4 / 69.0 Hz | 74.8 / 68.6 Hz | X: the belt is 49 mm longer between pulleys. Ranges 69 to 83 and 64 to 76 Hz: inside v9's |
| Acceleration an owner would run | 8,400 (5,800 to 13,500) mm/s^2 | 8,400 (5,700 to 13,400) mm/s^2 | not a change |
| Step-loss ceiling | 24,000 mm/s^2 | 24,000 mm/s^2 | |
| Cross-track RMS / worst | 0.0101 / 0.101 mm | 0.0107 / 0.103 mm | inside each other's ranges |
| Frame stiffness at the nozzle, screwed X / Y | 1,450 / 1,920 N/mm | 1,570 / 2,011 N/mm | the Y plates are shorter over the beam; the nozzle is 15.5 mm off the block's centre |
| X belt within 1 mm of plane | 97.9 % of builds | 94.2 % | warning under 95 % |
| Benchmark time | 2,571 s | 2,571 s | melt-rate bound |
| Envelope (bounding box at home) | 389 x 419 x 463 mm | 389 x 419 x 471 mm | the X motor stands 8 mm higher; limit 420 x 420 x 480 |
| Full verify time | 67 min | 66 min | |

The scorecard barely sees this revision, as with v9: its figures are the gantry's, and the twin has one Z drive and no
bed dynamics. The gantry did change here, and the twin's answer is that it made no difference it can resolve (3 % in X
resonance against a believability of 15 %). What the twin does not have: the nozzle's 15.5 mm offset along the rail from
the block's centre (its toolhead-turning term uses the nozzle's distance from the rail only), the X motor plate's wing, and
the frame.

A firmware-in-the-loop print (real Klipper, the Octopus's STM32F446 dictionary, `examples/motor_bracket.py:bracket`) was
run on v10 for the viewer: clean, 3,891 s, nozzle within 0.055 mm of the G-code path, no machine collision.

## Vendor data: what is and is not verified

No maker's or seller's site was fetched for this revision; the session's network proxy refuses most supplier sites and
that was not worked around. Nothing was downloaded. What is new is from web-search result snippets, source level
"secondary", listed by the ratings verifier as unverified:

| Part | Record | Read | Not known |
|---|---|---|---|
| 235 x 235 mm PEI sheet | `mechloop/parts/vendor/creality_pei235.json`, `print_sheet_pei235()` | size; double-sided PEI on spring steel; sold with a magnetic base (Creality, resold by Digitec, Bastelgarage; SainSmart sells the same size) | steel thickness (one listing 0.4 mm, two list 235 x 235 x 1.2 mm: 0.4 mm drawn), magnetic base thickness (1.5 mm drawn, carried over), maximum temperature (carried over from the 257 mm sheet's seller), mass, flatness, price |
| X rail, HIWIN MGNR12R x 288 mm | the existing HIWIN record (catalogue Table 3.81: any length to 2000 mm, end distance 5 to 20 mm) | resellers that cut MGN12 rail to order exist (one lists "MGNR12R-LENGTH-HM, length can be customised"); one seller of cut HIWIN rail warns of pieces 2 to 3 mm short | price, lead time, who cuts it for this owner, the cut's tolerance. The catalogue's cost model prices it as any other rail (USD 17.5) |
| Heater pad 230 x 207 mm, 180 W | the catalogue's generic pad at a custom size | | a made-to-order size; no supplier checked |
| M4 x 40 countersunk screws, fully threaded | ISO 10642 from the catalogue's generator | | that the length is stocked fully threaded |

The build package's README carries a freshness warning: six fastener lines (washers, M5 x 10, M3 x 16, M3 nuts) whose mass in
the report's BOM differs from the modelled components'. v9's package carries the same six. The catalogue was not changed
between the verify and the package; the cause was not investigated.

Unchanged from v9 and still unverified: the die spring (now used at 6.5 to 9.5 mm of its listed 10 mm), the DIN 466 thumb
nut, the magnetic base stand-in, the lead-screw motors' thrust rating.

## Not tested, not checked, not run

- No full-machine modal analysis; the carrier's bounce frequency is a hand estimate.
- The allowable motor tilt is a rigid-body calculation on the support model (blocks, webs, nuts as springs). No FEA of a
  tilted carrier was made; the web's edgewise stiffness is beam theory (the FEA beam test of the web is of its easy
  direction only).
- A 9.525 mm plate, and the rear-corner stiffness with the 6.35 mm nut plates: scaled or taken from the first run, not
  re-run.
- Friction at the levelling points; spring fatigue and relaxation at 80 degC; creep of the thumb nuts.
- A temperature map of the plate; the one-lump heater model gives the times above.
- Airflow of the part duct (its shape is v9's, moved 15.5 mm with the Roto).
- The X switch's lever against a 3.175 mm tab; the HeaterCore's lead dress; the loom outside the back wall. Geometry
  only: the cable check found no clash and enough length.
- The assembly order in BUILD.md is the simulation's; the practical order is in the build package's stage notes.
- As v9: bolt preload and contact, buckling, belt tooth load, the lead-screw motors' thrust rating.

What was run for this revision, all on 2026-11-18. The full `verify` twice (66 min each): the first, on an earlier state of
the design, failed on two items and the design was changed; the second, on the final code, is the report above. Then, all on
the final code and that report: `score --assembly` (62 min); `tune`
(Klipper's shaper, pressure-advance and bed-mesh code on the twin); one firmware-in-the-loop print; the viewer export with
the assembly simulation; the build package with its drawings; the review data; and the whole test suite: 500 passed in
17 min (`pytest -q`, 14 of them new in `tests/test_v10_support.py`; those 14 were run again after the last export).
Not run: `score --firmware klipper` (the real firmware planning every benchmark print); any test of the generated drawings
beyond the generator's own checks; nothing physical.

## Open items and questions for the owner

1. **Order the X rail to length** (288 +0 / -1 mm) and confirm a supplier; or decide on a stock 250 mm rail and 191.6 mm of
   travel, which needs no other change than the rail (the bed would then be oversized again).
2. **The mesh covers 76 % of the print area** (211 x 178 mm of 229.6 x 214.5). Decide whether that is acceptable, whether
   to declare a smaller print area, or whether to plan a nozzle-contact probe.
3. **Hot-bed rise 0.0985 of 0.1 mm**: keep the limit, or state what the limit should be.
4. **Bed heat-up 469 s to 60 degC** (v9 295 s) with the 180 W the board's bed output allows. A mains-voltage heater on a
   relay would cut it; not designed.
5. **Stud holes in the 12.7 mm plate**: ask SendCutSend whether they drill and countersink them; otherwise drill at home.
6. **Check on the machine**: the X switch's lever on the 3.175 mm striker tab; the HeaterCore's leads turning back under
   the beam; the toolhead loom's path outside the back wall; the X belt's plane (shim the idler).
7. **Springs, thumb nuts, print sheet, magnetic base**: check against the makers' pages before ordering; measure the
   sheet and base and re-set the probe's z_offset; get the spring's temperature limit.
8. **Thumb nuts held by spring preload only** (49 to 72 N): paint-mark and re-check, as v9.
9. As v9: lead-screw motors' thrust rating and datasheet; screws cut to 258 mm by the builder; rear and front right nuts'
   float 97 to 98 % used at the 99.7th percentile (align each motor plate to its nut at assembly); web fatigue of the
   carriage plates; thread backlash at the Z nuts; Octopus heater and fan limits; part cooling not modelled; frame
   stiffness not in the twin.

**Questions for the owner**

- Is a cut-to-length HIWIN rail acceptable (item 1)?
- Is the 12.7 mm plate, with its slower heat-up and 0.8 kg more on Z, the right price for three points, or would you
  rather relax the 0.02 mm sag limit and take a 9.525 mm plate (about 0.023 mm, 0.5 kg lighter)?
- Do you want the thumb nuts to remain the coarse adjustment, or should the carriage plates' webs be necked so that the
  motors can take the whole as-built error (then the three studs could be fixed)?
- Homing X at the right end and the bed 15.5 mm left of centre: any objection?
- The front 34.5 mm is still unprobed (item 2). Is a nozzle-contact probe worth a toolhead redesign?

## Files

- `designs/printer_v10.py`; `out/printer_v10/report.json`, `scores.jsonl`
- catalogue: `mechloop/parts/batch9.py`, `mechloop/parts/vendor/creality_pei235.json`; `docs/VENDOR_DATA.md` (ninth batch)
- checker: `mechloop/verifiers/bed_support.py` (`tilt_allowance`), `AGENT.md`; `tests/test_v10_support.py`;
  `tools/build_package.py` (v10 stage notes and open items)
- `docs/build/printer_v10/`, `viewer/`, `review/data.json` (generated); v9's viewer and review data kept in `viewer_v9/`
  and `review_v9/`
