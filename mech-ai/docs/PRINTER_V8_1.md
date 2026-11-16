# printer_v8_1: v8 rebuilt to the design guidelines

Everything here is simulated. Nothing has been built.

`designs/printer_v8_1.py` starts from a copy of `designs/printer_v8.py` (v8 was not edited) and applies
`docs/DESIGN_GUIDELINES.md` and the open items of `docs/build/printer_v8/OPEN_ITEMS.md`. It passes all 12
verifiers with **0 errors and 33 warnings** (`verify designs/printer_v8_1.py`, 2026-11-16, report in
`out/printer_v8_1/`). Every warning is explained below. No checker code was changed. Under today's checks v8
fails with 12 errors (two tapped extrusion ends too short, six head-seat and plastic-bearing errors, four FEA
errors on printed parts in the Z and X load paths; list at the end).

The kinematics, envelope, toolhead, probe, electronics and the Z concept (three T8 x 2 screws on one belt, one guide
block per rail) are v8's. What changed is how each part is made and held together, and the Z stage's nut seating.

## Result against the brief

| # | Brief | Result | Met |
|---|---|---|---|
| 1 | no load-bearing printed part; printed parts declare print settings | 5 printed parts: probe holder, part duct, three mains covers; each has `meta["print"]`; requirement "no printed part in a load path" passes | yes |
| 2 | 2D laser-cut first, SendCutSend stocked gauges, CNC only with a written reason | 54 laser-cut parts, **0 CNC parts**; the tool plate is two laser-cut plates; the bed is MIC-6 9.525 laser-cut with its faces as cast; `assign(d, sheet="sendcutsend", machined="xometry")`; every sheet part has `meta["finish"]` | yes |
| 3 | named materials, no generic steel | 6061-T6, 5052-H32 (bent parts), 304 (bent stainless), MIC-6 (bed), A2 rod; `steel` appears nowhere | yes |
| 4 | no tapped aluminium we make, no tapped extrusion ends | through-bolts with nuts and washers, captive nuts in laser-cut hex pockets, PEM nuts in the 5052 anchors, steel thread inserts in the bed plate only (its top face must stay flat); the bed carrier is a 2020 rectangle on cast corner brackets and T-nuts | yes |
| 5 | washers, thread locking, rounded corners, lead-ins | washers under every head or nut on a slot, an oversize hole, thin aluminium or plastic; medium threadlocker listed for Z top nuts, pulley set screws, jack screws and post jam nuts; every cut profile's outside corners rounded (1 mm, 2 mm on the bed); lead-ins: see "Open items" | yes, lead-ins partly |
| 6 | Z: nut lift-off at two screws at opposite lead limits; build-package findings | every nut seated at 0.142 mm (least margin 2.7 N; v8: rear nut lifts); see "Z stage" | yes |
| 7 | real catalogue parts, list stand-ins | TRONXY PEI180 sheet, CG3010U24 fan, MGN12 rails/blocks, catalogue 608, T8, NEMA17; stand-ins: the PEI180's magnetic base, four M5 threaded rods, two M5 thread inserts | yes |
| 8 | bed sag <= 0.02 mm under 1 kg at the worst corner incl. the lead budget | **0.0048 mm** screw-only bound (v8 0.0147); with two screws at opposite limits every nut stays seated, so the sag stays 0.0008 mm on the supports (v8: 0.041 mm after the rear nut lifts) | yes |
| 9 | 180 mm cube | travel 180 x 214.5 x 183 mm (as v8: Y is longer so the probe reaches) | yes |
| 10 | keep or improve stiffness and resonance | see "Numbers against v8" | see table |

## Numbers against v8

All figures from the same harness: `score --assembly`, `score --firmware klipper --firmware-only` and `tune` on the
final file, against `out/printer_v8/scores.jsonl` (2026-11-15). v8's FEA and bed figures are from a full verify of
`designs/printer_v8.py` under today's checks.

| | v8 | v8.1 | |
|---|---|---|---|
| Errors / warnings (today's checks) | 12 / 48 | **0 / 33** | |
| Total mass | 12.44 kg | 13.72 kg | +10 %: 9.5 mm bed, aluminium plates for printed parts, nut plates |
| BOM cost (estimate) | $787 | $823 | +5 %; SendCutSend/Xometry prices are not in it |
| Parts / fasteners | 386 / 172 | 583 / 180 | the extra parts are washers, nuts, tower plates and brackets |
| Assembly time (estimate) | 84.7 min | 135.9 min | 242 placements need holding (v8 96), 12 tool changes (6), turned 17 times (12) |
| Resonance X / Y (built-in) | 79.3 / 58.8 Hz | 77.6 / 61.0 Hz | ranges 72.1 to 85.4 / 57.5 to 65.7 |
| Frame stiffness at the nozzle, screwed-joint bound X / Y | 1,542 / 2,075 N/mm | 1,443 / 1,917 N/mm | bonded bound 2,350 / 2,447 (v8 2,332 / 2,438) |
| Nozzle deflection, FEA load case (bonded) X / Y | 1.55 / 1.48 um | 1.53 / 1.47 um | |
| Toolhead tilt term X | 466 N/mm | 467 N/mm | one MGN12H, arm 43 mm |
| Acceleration an owner would run (built-in) | 6,000 (4,200 to 9,200) | 6,500 (4,600 to 9,900) mm/s^2 | |
| ... with Klipper | 4,800 (3,800 to 6,200) | 5,200 (4,100 to 6,700) mm/s^2 | shapers X EI 96.2 Hz, Y MZV 59.4 Hz (v8 98.2 / 57.4) |
| Step-loss ceiling / first failure | 10,000 / 12,000 | 12,000 / 14,000 mm/s^2 | |
| Klipper, shaper off: highest clean | 6,000 (two undecoded points) | 16,000 mm/s^2 | v8.1 sweep decoded every point |
| Klipper, as configured: cross-track RMS / worst | 0.0059 / 0.047 mm | 0.0059 / 0.041 mm | clean to 48,000, the highest tried, in both |
| Cross-track RMS / worst (built-in) | 0.0125 / 0.107 mm | 0.0119 / 0.108 mm | |
| Moving mass X / Y / Z | 0.344 / 1.339 / 4.21 kg | 0.358 / 1.237 / 5.11 kg | Z heavier on purpose (nut seating) |
| Bed sag, 1 kg at worst corner, screw-only bound | 0.0147 mm | **0.0048 mm** | target 0.02 |
| Bed sag at the lead budget (two screws at opposite limits, 0.142 mm) | 0.041 mm, rear nut lifts | **0.0008 mm on supports, all nuts seated** (least margin 2.7 N) | |
| 20 N hand load at the worst corner | 0.030 mm | 0.010 mm | |
| Payload x3 on bed (FEA) | 5.2 um | 2.2 um | |
| Heated bed +60 K, growth | 0.31 mm | 0.39 mm | now includes the magnet-held sheet as a sliding contact |
| Nut thrust FEA (rear / front) | printed ABS, factor of safety 1.6 / 1.4 (errors) | 6061, 22.2 / 24.9; 0.022 / 0.035 mm | |
| X belt clamp FEA | printed, 4.6; 0.015 mm | 5052 bent, 18.6; 0.007 mm | |
| Benchmark time | 2,571 s | 2,571 s | held by the hotend's melt rate, not the frame |

## Per-verifier result and every warning

| Verifier | Errors | Warnings | What the warnings are |
|---|---|---|---|
| geometry | 0 | 0 | |
| interference | 0 | 0 | |
| tolerance | 0 | 5 | (1) `sheet_bends_not_recognised`, the three 8 x 12 shims: they are flat rings with two flats, not bent (checker note 3). (2) `z_fl_r1` to `psu_relay` 0.54 mm, closes in 0.30 % (sd 0.10 %) of builds: the relay sits on the tray next to the front-left tower's base plate; both are on the frame's bottom rails. (3) `back_plate` to `z_rear_r4` 0.77 mm at the bottom over-travel, 0.07 %: the carrier's back plate passes the rear tower's top plate at Z -3. (4) extruder to part duct 1.35 mm, 0.03 % (printed duct, as v8's duct). (5) X carriage to the Roto's screw tip 0.42 mm, none of 3,000 builds closed it (normal estimate 0.06 %). All five are under the 1 % the checker calls an error |
| manufacture | 0 | 17 | (1) `front_plate`, 2 holes 11.6 mm from the edge (12.7 wanted, 1 x t; shop minimum 6.35 met): 12.8 mm holes for the large washers, the plate is 12.7 thick. (2, 3) `nut_plate` (rear, 9.525): 6.5 mm bolt holes narrower than the sheet and 6.75 mm to the edge; the plate sits on the rear 2020 beam with the back plate 10 mm behind the bolts, so the edge cannot move. (4) `bed_plate`, six 5.2 mm pilot holes in 9.525 mm MIC-6: they are drilled out and tapped for the inserts by the builder anyway (FABRICATION). (5) `z_drive_plate` 5 hole pairs 7.1 mm apart (12.7 wanted): NEMA 17's own 31 mm pattern next to the 22 mm boss hole. (6 to 8) `mostly_holes`, the three shims: a 12.1 mm ring with an 8.55 mm bore is 50 % hole by area; it is a washer, not a grille (checker note 4). (9 to 14) both Y plates: 3.5 mm guide-block screw holes in 4.75 mm sheet (MGN12H's M3 pattern), 3.35 mm from a belt slot to the plate edge and 2.56 mm between a belt slot and a block screw hole (4.75 wanted; above SendCutSend's 2.38 minimum). v8 had the same pattern at 2.05 mm. (15) `tool_plate`: the PEM nuts' 4.22 mm holes are 6.23 mm from the block screws' holes (6.35 wanted, 2 x t). (16, 17) `tool_plate_rear`: 3.1 mm from a hole to the edge and 3.0 mm between the belt bracket's nut pocket and the lightening window (4.75 wanted; SendCutSend's minimum 2.38 met); the outline is the Roto's own footprint and the block's 20 mm pattern |
| ratings | 0 | 8 | (1) `screw_head_seat_too_small`, five M3 PEM nuts (three tension anchors, the two Roto screws' nuts in the front tool plate): the checker sees a hex nut over a 4.2 mm hole, 65 % of a standard seat (marginal, the checker's word). A PEM nut is clinched into the sheet; it does not bear on a seat (checker note 8). The jack screws are turned to 0.3 N m and only push. (2 to 8) `uncatalogued_cots`: the seven declared stand-ins (magnetic base, four threaded rods, two thread inserts) |
| motion | 0 | 0 | |
| subsystems | 0 | 1 | `bed_mesh_does_not_cover_print_area`: 12 mm strips at the sheet's edge. The print area is the whole 180 mm PEI sheet and the probe keeps 12 mm inside the plate edge; the firmware holds the nearest probed value there. As v8 under today's check (owner decision 4) |
| electrical | 0 | 1 | `cutoff_depends_on_mcu`, hotend: as v7 and v8 |
| assemblability | 0 | 1 | `unsupported_step`: the back plate and electronics bay are placed before the frame closes; as v8 |
| fea | 0 | 0 | |
| printing | 0 | 0 | |
| requirements | 0 | 0 | all 20 pass |

## What changed, part by part

### Z stage (the main change)

v8's rear nut lifted when two screws sit at opposite lead limits (0.142 mm: 0.02 belt sync + 2 x 0.061 lead
error over 183 mm), and its nut blocks, Z drive mount, sleeve and pedestals were printed.

- **Guide blocks: Hiwin clearance class ZF** in place of Z0 (catalogue `mgn12h_carriage(preload="ZF")`). The three
  screws hold the carrier's tilt; the blocks only locate it. A preloaded block resists tilt and turns a height
  difference between screws into load taken off a nut; a clearance block does much less of that. The checker
  takes ZF at 40 N/um (Z0: 63); this is an assumption of the harness (checker note 6). Nut sensitivity fell from
  136 to 87 N per mm of height error.
- **Heavier carrier, mass centre over the screws.** The bed plate is 9.525 mm MIC-6 (v8 8 mm, not a stocked
  thickness) and reaches 36.5 mm past the sheet at the front (v8 16.5), the front stiffener is 12.7 mm 6061, the
  nut plates are 6061 (9.525 rear, 6.35 front). Moving mass on Z 5.11 kg (v8 4.18); the screw-line-to-mass-centre
  distance 14.9 mm (v8 26.9). Seating loads rose to 19.3 / 15.4 / 15.4 N (v8 17.5 / 11.8 / 11.8).
- Result: at 0.142 mm every nut stays seated, least margin 2.7 N (front nuts); rear 6.9 N. v8: rear nut
  -1.8 N (lifts). The bed's level still changes 0.12 mm across the print area over the travel at that budget: that
  is the screws' lead error itself, which one belt cannot correct (see "Owner decisions" 1).
- **Nut plates** (replace the printed nut blocks): laser-cut 6061 on the beams' top faces, two M5 bolts with
  washers into T-nuts each. The T8 nut hangs below in a 16.4 mm float hole (2.6 mm of float, 2.2 mm needed at 99 % of builds),
  turned by an M2.5 pin screw through a 5 mm aluminium sleeve in a radial slot, nyloc nut. The rear plate's tongue
  is a 48 mm cantilever through a window in the back plate; it is 9.525 mm so the nut seat moves 0.022 mm under
  3 x the bed weight (6.35 gave 0.070, over the 0.05 limit I set; v8's printed block: 0.147 with a 0.3 limit).
- **Screw towers** (replace the printed Z drive mount, sleeve and pedestals): each lead screw stands in a stack of
  laser-cut 6061 plates on the frame's bottom rails: base plate (R1, 6.35, hex pockets for the post bolts' nuts),
  lower bearing plate (H1, 4.75), spacer (R3, 4.75), upper bearing plate (H2a 4.75 + H2b 5052 2.286), top plate
  (R4 3.175); the rear tower has an extra base (R0). Two M5 x 65 posts with captive nuts clamp the stack; each
  plate has its own rail bolts with washers into T-nuts. Two 608s per screw sit in laser-cut 22.1 mm holes,
  clamped between plates, so the bearings sit on their outer rings and every plate sees only bearing load.
- **Axial retention without set screws in the weight path.** The upper 608 is the thrust bearing: a brass T8 nut
  (inverted, threadlocked) screwed down onto its inner ring carries the bed's weight. The GT2 pulley under it is
  set-screwed for torque only; with a 6061 shim (8.55 x 12.1 x 1.6, two flats) on the lower inner ring it holds
  the screw down against an upward load. Open item B in v8 (pulley set screws carrying the bed) is closed.
- **Z belt**: one closed GT2 6 mm belt, 1138 mm (route 1138.7 mm, idler adjustment 3 mm), motor on a laser-cut
  6.35 mm drive plate at (44, 128), moved clear of the carrier's under-arm bracket.
- **Carrier** (replaces v8's bed arms on tapped extrusion ends): a 2020 rectangle (rear beam, two arms, front beam)
  joined by eight cast corner brackets on T-nuts (inboard corner and under each arm end), back plate 4.75 mm 6061
  on the two blocks (screw heads with washers), rear beam bolted to the back plate.
- **Kept**: three T8 x 2 screws, one belt, one 40 mm motor, one block per rail. I looked at independent Z motors on a
  BTT Manta M5P (owner decision 1): it would let `z_tilt_adjust` re-level at the print height, but it does not
  stop a nut lifting (the lead error is the same), and the M5P has five drivers where X, two Y motors, E and three
  Z motors need seven (or six with the Y motors paralleled on one driver, as now). It would also mean two more
  motors and a new board and wiring. With every nut now seated I kept the SKR Mini E3 V3 and one Z motor.

### Bed

- **Bed plate**: MIC-6 cast plate 9.525 mm (SendCutSend stocks it), laser-cut, faces as cast, corners rounded
  2 mm. v8 was 8 mm machined. The four posts' and the tie's holes are 5.2 mm pilots; the builder taps them for
  M5 steel thread inserts (FABRICATION lists the step). No tapped aluminium carries load.
- **Print sheet**: TRONXY PEI180 from the catalogue (`print_sheet_pei180`, 0.4 mm spring steel). Its magnetic base
  is a declared stand-in (thickness not published; 1.0 mm assumed).
- **Posts**: four M5 A2 threaded rods (stand-in: not in the catalogue), drawn at the stress-area diameter 4.48 mm so
  the FEA mesher can fill the gap to the washers. Each has a jam nut under the bed plate and two nuts clamping a
  4.75 mm 6061 tab, every nut on a washer, threadlocker on the jam nuts. The nuts sit on threaded rod: open item
  "post nuts on an unthreaded shank" is closed.
- **Tie**: bent 304 stainless 1.524 mm (soft vertically, stiff in X, Y and yaw), bolted to the back plate with
  washers and to the bed plate through 8 mm spacers into the two thread inserts.
- **Post tabs**: 6061 4.75 mm, two M5 bolts each into T-nuts on the arm, with washers.

### Y and X axes

- **Y plates** (v8 steel): 6061 4.75 mm; beam bolts M5 with washers on slots; belt slots as wide as the sheet is
  thick.
- **Y motor mounts and idler mounts** (v8 steel): bent 304 stainless 1.88 mm (SendCutSend's 304 bend gauge and
  radius), fin bent up for stiffness.
- **Y tension anchors** (v8 printed PETG): bent 5052 3.175 mm on two T-nuts, a PEM M3 nut clinched in the fin
  (SendCutSend hardware service), M3 jack screw with washer, 0.3 N m.
- **X beam, rail and rail stops**: as v8; stops 6061 3.175 mm.
- **X motor mount**: 6061 3.175 mm flat; **X idler mount**: bent 5052 2.286 with a lug; **X tension anchor**: bent
  5052 with a PEM nut and jack screw (v8 printed).
- **X belt bracket** (v8 printed belt block): bent 5052 2.286 mm with a 2.032 mm 6061 clamp plate, four M3 with
  nuts in the tool plate's hex pockets. FEA x_belt_pull: factor of safety 18.6, 0.007 mm (v8 4.6, 0.015).

### Toolhead

- **Tool plate** (v8 machined 6061 with counterbores): two laser-cut 6061 plates. The front plate (3.175) sits on
  the X block; four M3 x 6 from the rear. The rear plate (4.75) has 6.5 mm holes that are the counterbores for those
  heads, and hex pockets for the belt bracket's nuts. The Roto's two M3 x 50 screws thread into PEM S-M3 nuts
  clinched in the front plate (SendCutSend hardware service), their heads sitting in hex holes of the rear plate, so
  each screw clamps sleeve, Roto, rear plate and front plate together. A first version had plain nuts in hex
  pockets of the front plate: those screws then held only the Roto to the rear plate, and the two plates were
  clamped together only by the duct screws. The FEA's screwed-joint bound showed it (nozzle stiffness X 349 N/mm,
  Y 632, against v8's 1,542 and 2,075); with the PEM nuts it is X 1,443 and Y 1,917 N/mm. No machining.
- **Probe holder** (printed ABS, 4 mm): the Roto's two screws pass through 3.5 mm aluminium compression sleeves in
  it, so the screws clamp metal, not plastic; the OMRON E2E's own nuts clamp it with washers.
- **Part duct** (printed ABS) with brass heat-set inserts drawn solid to their thread; **part fan** CG3010U24
  (catalogue).

### Frame and electronics

- **Electronics tray**: 6061 3.175 mm (v8 3.0, not stocked). Boards on nylon spacers with washers and nuts.
- **Mains covers** (printed PETG): over the relay, the PSU's terminal strip and the inlet's terminals, each held by
  two screws into heat-set inserts in printed bosses. Open item A3 (live terminals uncovered) is closed.
- **Earth**: an M5 ring terminal on an M5 earth stud (they now match); the frame's protective conductor is
  2.5 mm^2 (AWG 13) and runs on its own; the supply's earth AWG 18 like the line conductors.
- **Probe supply**: a "bed probe 24 V" wire from the PSU's V+ to the probe connector (v8's probe had no supply in
  the wiring).
- **Inlet panel**: 6061 2.54 mm.

### Printed parts and their settings

| Part | Material | Why printed | Print settings |
|---|---|---|---|
| probe_mount | ABS | holds the probe's position only; the toolhead screws clamp aluminium sleeves through it | 4 walls, 5 top/bottom, 40 % gyroid, 0.2 mm |
| part_duct | ABS | air guide near the hotend | as above |
| mains_cover_relay, _psu, _inlet | PETG | touch covers over live terminals | 4 walls, 5 top/bottom, 40 % gyroid, 0.2 mm |

## CNC parts and their reasons

None. Every metal part is laser-cut (54) or bought. The two candidates were the tool plate (v8's had machined
counterbores: replaced by a second plate with through holes) and the bed (v8's 8 mm plate was machined to a
non-stocked thickness: replaced by MIC-6 9.525 laser-cut, faces as cast, which is how MIC-6 is sold flat).

## Stand-ins

| Part | Why | What would replace it |
|---|---|---|
| bed_magnet | the PEI180's magnetic base thickness and grade are not published | the seller's data, or a catalogued magnetic base |
| bed_post_0..3 | M5 x ~150 A2 threaded rod (DIN 976) is not in the catalogue | a catalogue entry for threaded rod |
| bed_insert_0..1 (and the four post inserts, a BOM line) | M5 x 1.5D stainless wire thread inserts are not in the catalogue | a catalogue insert |

## Open items

1. **Lead-ins.** Laser cutting gives no chamfer. The bearing bores, nut float holes and post holes are plain
   through-holes; deburring is listed in FABRICATION. SendCutSend's deburring service is an option, not specified.
2. **ZF blocks at 40 N/um** are the checker's assumption, not Hiwin's figure; the seating margin (2.7 N) depends on
   it. If a ZF block is stiffer in tilt, the margin shrinks. Matched screws (measured lead) are the fallback.
3. **Magnetic base** and the bed's 80 degC limit as v8.
4. **Part count rose** (583 parts, v8 386): mostly fasteners, washers and nuts that replace tapped holes, the
   tower plates and the carrier's brackets. Reported, not limited.
5. **Build package**: `docs/build/printer_v8_1/OPEN_ITEMS.md` lists the generator's items.

## Owner decisions

1. **One motor and one belt for three screws** (kept), with ZF blocks. The bed level changes up to 0.12 mm across
   the print area over the full height if two screws sit at opposite lead limits; a mesh at the print height takes
   it out, but not over the height. Independent motors (Manta M5P, `z_tilt_adjust`) would re-level at any height.
2. **Bed plate 9.525 mm MIC-6, 36.5 mm longer at the front**: heavier carrier (5.1 kg on Z) for nut seating.
3. **Thread inserts in the bed plate** (the only threads in aluminium we make), tapped by the builder.
4. **The print area is the whole 180 mm sheet** and the probe keeps 12 mm inside the plate edge.

## Checker behaviour worth a look

1. **Interference is slow with filleted profiles.** Each pair's bounding box is recomputed per pair; with fillets on
   every edge (torus and sphere faces) the box took about 1,000 times longer and interference ran over 15 minutes.
   I round only the through-thickness edges, which is also all a laser cut gives.
2. **An edge of length close to the thickness is counted as a sharp corner.** `sharp_profile_corners` flagged the
   short straight edges of a faceted outline (48 facets on a 2.286 mm part gave facets 2.29 mm long) and a 10 mm
   edge on the 9.525 mm rear nut plate. I changed the geometry (40 facets; base 78 mm wide), not the check.
3. **A flat ring with two flats is "not a flat plate"** (`sheet_bends_not_recognised`, the shims).
4. **`mostly_holes` reads a washer as a grille** (the 50 % shims).
5. **No way to declare a preloaded or spring-loaded nut** (anti-backlash nut with a spring, or a wave washer under
   the flange) to the seating study; the only kinds are gravity-seated.
6. **ZF blocks fall back to a stiffness class (40 N/um)**; worth a catalogue value.
7. **Thin gaps in an assembly FEA case crash the mesher** ("PLC Error: A segment and a facet intersect"): a
   0.15 mm radial gap between an M5 rod and a 5.3 mm washer bore. The hint names the cause; drawing the rod at
   its stress-area diameter fixed it.
8. **A PEM self-clinching nut is judged as a loose hex nut on an oversize hole** (`screw_head_seat_too_small`); a
   join kind for clinched hardware would let the check skip it.
9. **The screwed-joint stiffness bound found a real weakness**: it is what showed that the two tool plates were held
   together only by the duct screws. Not a checker problem; worth keeping.
10. **AGENT.md's caveat "the catalogue has no board with more than four drivers" is out of date**: `manta_m5p` is in
    `mechloop/parts/batch6.py`. The build package quotes the caveat in OPEN_ITEMS.md.

## v8 under today's checks (12 errors)

Two `thread_engagement` (bed arm bolts in tapped extrusion ends, 9 mm of 10); three `screw_head_seat_too_small`
(M3 and M5 heads and nuts on slots and oversize holes in the printed nut blocks, Z drive mount and probe mount and
in the steel back plate, tie, front plate and Y plates, down to 21 % of a standard seat); three
`screw_head_bearing_pressure` (M3 and M5 heads and nuts bearing directly on ABS and PETG at 109 to 114 MPa); four
FEA errors on the printed nut blocks and Z drive mount (factor of safety 1.4 and 1.6, deflection 0.43 and
0.11 mm). v8.1 takes every printed part out of those load paths and puts a washer under every head on a slot.

## Files

- `designs/printer_v8_1.py`: the design
- `out/printer_v8_1/report.json`: full verify
- `docs/build/printer_v8_1/`: build package (generated)
- `viewer/` and `review/`: 3D viewer and review data for printer_v8_1 (generated)
- `tools/build_package.py`, `tools/build_review.py`: v8-specific text replaced by text read from the design and
  report (see the commit)
