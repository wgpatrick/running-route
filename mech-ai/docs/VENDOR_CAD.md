# Vendor CAD behind the catalog parts

Added 2026-11-14. Until now every catalog part was a hand-drawn proxy (boxes and cylinders from data-sheet
dimensions). Each catalog `Stock` and each placed `Component` now has two representations:

- `shape`: the **simulation solid**. Simple and clean; every verifier still works on it (exact booleans over 292
  parts, meshing, sweeps, tolerance cylinders, assembly planning).
- `detail`: the **detailed model**, in exactly the same local frame: a vendor STEP where one could be had, a
  community-drawn STEP otherwise, or geometry generated to a standard. It is what the STEP export
  (`out/<name>/<name>.step`), the renders and the browser viewer show, and it is the reference the simulation solid
  is checked against.

`stock.model` / `component.meta["model"]` says which: `kind` is `vendor CAD`, `community CAD`,
`generated to standard` or `proxy`, with `source` and `file`. Community CAD is never labelled as the vendor's.

Code: `mechloop/parts/vendor_cad.py` (loader, cache, alignment, checks), `mechloop/parts/details.py` (one function
per part: file, frame, what must be found in it). Files: `vendor_cad/` with `vendor_cad/SOURCES.md` (origin, commit,
licence, who made it). Tests: `tests/test_vendor_cad.py`.

## The two checks (in the geometry verifier)

**`proxy_mismatch`** ("proxy matches vendor CAD"). For every part type with a detail model: the six bounding-box
faces (0.5 mm or 1.5 %), the volume ratio, mass against the model's volume for one-material parts, and every
mounting hole and shaft named in `interfaces`: a cylindrical face must exist in the CAD whose axis passes within
0.3 mm of the stated position with a diameter that fits (tapped to clearance for `mount_holes_m*`; exact for
shafts, bores and pilots). A mismatch is an error carrying both values. Deliberate differences are declared per
part with the reason (`protrusions`, `tolerance`, `notes` in `details.py`) and are printed in
`metrics["geometry"]["vendor_cad"]["checked"]`.

**`detail_clash`** (the envelope check). Whatever the detail model has outside the simulation solid by more than
0.4 mm (a connector, lever, terminal, pin, cable exit) is collected as convex hulls. Each hull is tested against
the neighbouring parts' simulation solids (bounding boxes, then a hull-against-mesh test, then an exact boolean of
the detail geometry; against the neighbour's own detail model where it has one). More than 0.5 mm^3 is an error
naming both parts and the place. Declared overlaps (`allow_overlap`) and a part's declared mate (nut on its lead
screw, carriage on its rail) are skipped. Home pose only. Set `design.detail_envelope = False` to switch it off.

Cost on printer_v4: proxy match 3 s, envelope about 12 s (646 candidate pairs, 409 exact booleans). STEP imports and
derived shapes are cached as BREP in `vendor_cad/.cache/` (not committed), keyed by file hash.

## Part by part

| Catalog part | Model kind | Source | Proxy-match result and what was corrected (old -> new) |
|---|---|---|---|
| `psu_lrs("LRS-350-24")`, `psu_24v(350)` | **vendor CAD** | MEAN WELL `LRS-350-3D.zip` (meanwell.com), unchanged, 3.2 MB | Case 215 x 115 x 30 and the four M4 base holes at (+/-75, +/-25) agree exactly (drawn 3.1 mm for the thread). **Terminal strip position corrected**: the strip is centred 9.5 mm towards -Y, so port Y positions moved from -38..38 to -47.5..28.5 (was "read off the drawing, +/-2 mm"). The vendor STEP has one internal bracket drawn 0.9 mm *through* the base, against the data sheet's 30 mm height: trimmed at the base plane, and said here. Volume ratio 4.5 is declared (hollow sheet-metal box vs. solid envelope). |
| `psu_lrs("LRS-200-24")`, `psu_24v(200)` | vendor CAD of the LRS-350 | same file; same 215 x 115 x 30 case per the data sheets | The LRS-200 3D download is a RAR archive that could not be unpacked here: on the wish list. |
| `skr_mini_e3_v3()`, `control_board()` | **vendor CAD**, reduced | BIGTREETECH's STEP from their GitHub repository (17.7 MB), reduced to the 41 solids over 40 mm^3 (4.6 MB) | Outline 103.75 x 70.25 agrees. **Component envelope height 13.0 -> 14.2 mm** above the PCB (`control_board()`: box 18 -> 15.8 mm). The five motor connectors are within 0.5 mm of the catalogue's port positions. USB / micro-SD overhang the +X edge by 1.4 mm (declared). **Vendor CAD and vendor drawing disagree twice**: the STEP draws the PCB 0.8 mm thick (kept 1.6), and it has *no* holes where the SIZE drawing puts the five 3.1 mm mounting holes; it has two 3.1 mm holes at (-30.68, 16.6) and (9.33, 16.6) instead. The catalogue keeps the dimensioned drawing; the hole check is switched off for this part. Measure a real board before drilling the tray. |
| `nema17(34/40/48/60)` | community CAD | FreeCAD-library NEMA 17 (40 mm, with connector), cut at the stator and brought to each body length and shaft length in code | Frame 42.3, pilot 22, shaft 5, four M3 on 31 mm, 4.5 mm thread all agree. **Connector added to the simulation solid**: a 5.7 x 17.2 x 8 mm block on the +X side at the rear (new interface `connector_side`). Model pilot height 1.6 vs. drawing 2.0 (noted). StepperOnline's own STEP files need a login: wish list. |
| `mgn12_rail(L)` | community CAD | FreeCAD-library MGN12 rail: section swept to length, holes to the MG table | Section 12 x 8, holes 3.5 / counterbore 6 x 4.5 / pitch 25 / end distance 10 in the community model equal the recorded table. No change. |
| `mgn12h_carriage()` | community CAD | FreeCAD-library MGN12H | 27 x 45.4, 3..13 mm high, M3 on 20 x 20 agree. The model draws the threads 3.5 mm deep: a second (community) source for `thread_depth_unverified`; still not Hiwin's. Its ball rows are drawn 25 mm^3 into the rail model's grooves (declared mate). No change. |
| `extrusion_2020(L)` | community CAD | FreeCAD-library 20x20 slot-6 profile: section swept to length | Outline agrees. Not applied, recorded: section area 174.3 mm^2 (0.47 kg/m; catalogue 0.45), slot opening 6.0 (simulation solid 6.2 wide, plain 5 mm deep slots, no T cavity). Misumi's own data still not reachable. |
| `corner_bracket_2020()` | community CAD | FreeCAD-library 2020 corner bracket | **Width 18 -> 17 mm.** The model's 1 mm locating nubs sit in the T-slots (declared). Solid prism kept as the simulation solid. |
| `gt2_idler(20, 5, 6)` | community CAD | FreeCAD-library 20-tooth-size idler (smooth; teeth not drawn) | **Flange diameter 15 -> 18 mm** (all idlers: flange = tooth OD + 6). Height 8.5, bore 5, belt centre 4.25 agree. Other widths (printer_v4 uses 12 mm belt) stay proxy. |
| `gt2_pulley(...)` | proxy | none used | A community model (Voron 0 assembly, 20 T, 6 mm belt) is 16 dia x 16 long with the belt centre at 11.35; the proxy is 16 x 15 with the centre at 10.5, and a FreeCAD-library model differs again (18 dia, 14.6 long). Three sources, no vendor drawing: not applied, on the wish list. |
| `leadscrew_nut_t8()` | community CAD | FreeCAD-library T8 flange nut | Flange 22 x 3.5, four 3.4 mm holes on 16 mm agree. **The barrel stands 1.5 mm proud below the flange**: simulation solid changed from flange-at-the-end (barrel 0..15) to barrel -1.5..13.5; new interface `stub_below_flange`. Barrel 10.0 in the model vs. 10.2 catalogue (within tolerance). |
| `fan(30)` | community CAD | Voron 0.2 master assembly (GPL-3.0), part "3010 DC Axial Fan" | 30 x 30 x 10, 3.4 mm holes on 24 mm agree. No change. |
| `fan(40)` | community CAD | FreeCAD-library 40 mm fan | 40 x 40 x 10, holes on 32 mm agree in position; the model draws them 4.3 mm (M4 size), the catalogue calls them M3 holes (noted). |
| `endstop_switch()` | community CAD + generated board | FreeCAD-library D2F-size hinge-lever microswitch (PCB terminals) on a generated 20 x 12.5 x 1.6 mm board | Rebuilt, see below. |
| `shcs(size, L)` | generated to standard | ISO 4762 via `bd_warehouse` (head, socket, chamfers) | Agrees. Generated head is the knurled-head maximum (M3: 5.68), simulation solid the plain-head 5.5 (0.09 mm per side, noted). |
| `hex_nut(size)` | generated to standard | ISO 4032 via `bd_warehouse` | Agrees. The simulation solid stays hole-less (the thread is the overlap with the screw). |
| `shaft_coupler`, `leadscrew_t8`, `linear_rod`, `bearing`, `extruder_direct`, `iec_inlet_c14`, `relay_btt_v12`, `raspberry_pi_zero2w`, `mosfet_module`, `bed_heater_pad`, heater / thermistor cartridges, `thermal_fuse`, `psu_24v(150)` | proxy | see "Still proxy" | |

T-nuts and washers are BOM lines only (no geometry in any design), so they have no model.

### The endstop

The old proxy was a 12.8 x 5.8 x 6 block on a board, pressed at a point 1.1 mm in front of the block on its centre
line. It is now a D2F-size hinge-lever switch lying on the board, in the same local frame, with the same two M3
holes at (+/-7.5, -4.2):

| | old | new |
|---|---|---|
| switch body | X +/-6.4, Y -1.4..4.4, Z 1.6..7.6 | X +/-6.4, Y 0.1..6.65, Z 1.6..7.4 (overhangs the board edge by 1.65) |
| `trigger` | (0, 5.5, 5.0) | (-9.0, 10.6, 4.5): the lever's operating position at its tip |
| new: `lever_free` | | (-9.4, 11.59, 4.5): lever tip at rest (in the detail model; not in the simulation solid, it moves) |
| new: `pretravel`, `overtravel` | | 0.99 mm from rest to the trigger; 3.95 mm from the trigger until the lever is on the case |
| new: `pin_holes`, `pin_length_below` | | three terminals 2.62 mm out of the underside at X = -5.08, 0, 5.08, Y = -0.8 |

Honest limits: the board is generated (no maker publishes the generic module); the switch model is community CAD;
the operating position is Omron's D2F-L figure, 10 +/- 1 mm from the mounting-hole line (its low limit, 9 mm, is
used so that reaching the trigger guarantees switching), **recalled, not fetched** (omron.com is not reachable).
The community model draws the lever tip at 10.0 mm, taken as the free position. A community STEP of the "Makerbot
mechanical endstop v1.2" module was tried first and rejected: its mounting holes cannot take a cap screw next to
the switch and connector, and nothing reachable confirms its dimensions. Replace all of this with the STEP of the
module actually bought (wish list).

## What the checks found in printer_v4, and the fixes

All in `designs/printer_v4.py`; search for "vendor-CAD pass" and `ES_`.

| # | Finding | Fix |
|---|---|---|
| 1 | `detail_clash` x3: the endstop switch terminals (2.6 mm below each board) run into `z_endstop_bracket`, `y_plate_left` and `y_idler_mount_l`: a through-hole board flat on bare aluminium, which would also short the switch. | Three 2.5 mm clearance holes under each switch (`ES_PIN_D`), taken from the part's `pin_holes`. |
| 2 | `endstop_not_reached` on Z (5.0 mm short), and X and Y strikers 0.6 to 0.75 mm off the lever tip: the trigger is now the lever's operating position, 10.6 mm from the switch origin (was 5.5) and 9 mm to one side. | Each switch moved 5.1 mm back along its stroke and 9 mm sideways so the lever tip is on the striker (`ES_TRIG`, `ES_SIDE`): X switch origin (-115.5, -17.9) -> (-120.6, -26.9) with its land on the left Y plate lengthened from 9 to 16.9 mm; Y switch origin (y -143.0, z 340) -> (y -148.1, z 349); Z switch origin x 8 -> -1 with its bracket widened from 58 to 67 mm. Gap at the end of travel is now 0.0 mm on all three axes and 3.0 mm three millimetres before. |
| 3 | Consequence of 2 on Z: the switch's screws and nuts would have risen 5.1 mm into the top back rail. | Jack screw shortened from M3x35 to M3x30 (`JACK_L`), which puts the switch back at its old height. BOM: SHCS-M3x35 -> SHCS-M3x30. |
| 4 | Motor connectors (now in the simulation solid), 18 mm idler flanges, the T8 nut's 1.5 mm stub, 17 mm brackets, the taller control-board envelope, PSU terminals 9.5 mm over. | No clash and no failed check: nothing to change. The PSU wire lengths in the wiring table move by a few millimetres. |

## What they find in the older designs (not edited)

Run: `mechloop verify <design> --no-render --only geometry interference subsystems`, compared with each design's
last report.

| Design | New findings from the corrected solids and the two checks |
|---|---|
| `designs/printer_v3.py` | `detail_clash` x3: endstop terminals into `z_endstop_bracket`, `y_plate_left`, `y_idler_mount_l` (the same three as v4 before its fix). `endstop_not_reached`: Y striker 2.2 mm and Z jack screw 5.0 mm from the lever's operating position (X is 0.6 mm off and passes). No interference from the motor connectors, idler flanges or nut stub. (It already failed on `not_enough_drivers`.) |
| `designs/pan_tilt.py` | The tilt motor's connector runs into the yoke: `interference` yoke / tilt_motor 667 mm^3 near (56.5, 0, 73.6) with the connector now in the solid, and `detail_clash` 93.5 mm^3 for the connector pins. Turn the motor about its shaft so the connector faces away from the yoke. |
| `designs/z_axis.py`, `designs/z_axis_v2.py` | `detail_clash` x2 each: the 1 mm locating nubs of `brkt_up_out_left` / `brkt_up_out_right` run into `base_left` / `base_right` (14.3 mm^3 each): those two brackets sit where there is no T-slot under their nubs. Real brackets of this kind need the nubs filed off there, or the bracket turned onto a slotted face. |
| `designs/printer.py`, `designs/printer_v2.py`, `examples/gantry.py` | Nothing new in geometry or interference. (Their subsystems errors, such as no endstops or no cable to moving electrics, are older than this work.) |


## Still proxy, and why

| Part | Why |
|---|---|
| NEMA 17 motors as *vendor* CAD | StepperOnline lists a STEP per motor but behind a login; the file host is blocked. Community model used meanwhile. |
| `shaft_coupler(5, 8)` (MH2025-5-8) | Same login. The FreeCAD-library coupler is a different part (25 x 34 mm). |
| `leadscrew_t8` | The only model found is 150 mm long and 5 MB of helical faces; the plain 8 mm cylinder is kept. |
| `gt2_pulley`, 12 mm idler | Community models disagree with each other and with the proxy (above); printer_v4 uses 12 mm belt, for which no model was found. |
| `extruder_direct`, hotend (design-local proxy) | No CAD on E3D's product pages; their GitHub repositories were not found under the names tried. The community V6-style hotend in FreeCAD-library is 62.8 mm long against the design's 60 mm proxy: not applied, because the nozzle position is a design datum. |
| `raspberry_pi_zero2w` | Raspberry Pi's STEP is on datasheets.raspberrypi.com, which the proxy blocks. |
| `relay_btt_v12` | BIGTREETECH's repository has drawings only. |
| `mosfet_module`, `iec_inlet_c14`, heater pad, cartridges, thermal fuse, `psu_24v(150)`, bearings, rod | Generic or commodity parts with no named maker (LRS-150: MEAN WELL's STEP is 6.4 MB, over the 5 MB limit, and no design uses it). |
| Hiwin, Misumi vendor CAD | hiwin.tw / hiwin.com / us.misumi-ec.com refuse automated requests. Community models used meanwhile. |
| McMaster fastener models | Not reachable. Generated to ISO; drop `SHCS-M3x8.step` etc. into the inbox to replace them. |

## Hand-download wish list

`vendor_cad/inbox/README.md` is the exact list: part, vendor part number, where it is, and the file name to save
it under. A file saved there under that name (or under the part's SKU) is picked up on the next build with no code
change, aligned automatically, marked "vendor CAD", and put through `proxy_mismatch` like every other model.

## Viewer data

`tools/export_viewer.py` now tessellates the detail model where a part has one (once per catalog part, moved to
each instance; coarser for models with many faces). New per-part fields in `viewer/data.json`:

| field | meaning |
|---|---|
| `model` | `"vendor CAD"`, `"community CAD"`, `"generated to standard"`, `"proxy"` (catalog parts) or `"design"` (custom parts) |
| `model_source` | one line: where the model came from |
| `model_file` | the STEP file in `vendor_cad/`, or null |
| `model_note` | set for a hand-downloaded file ("aligned automatically") |

printer_v4 after the change: 292 parts (2 vendor CAD, 59 community CAD, 172 generated to standard, 22 proxy, 37
design parts), 274,230 triangles, `viewer/meshes.txt` 8.5 MB (was 2.6 MB; limit about 12 MB), `data.json` 0.34 MB.
The exported assembly `out/printer_v4/printer_v4.step` is 28 MB with the detail geometry (was 7 MB).

Full `mechloop verify designs/printer_v4.py`: all 12 verifiers pass; 450 s of verification (geometry 15 s of it,
including both new checks) plus 184 s of rendering and export, measured while a print simulation and a test run
shared the machine. The previous full run took 343 s in all.

## Not done / limits

- The envelope check is at the home pose only; the motion sweeps still use the simulation solids (now with the
  motor connectors in them).
- A lever is not checked for being crushed: the switch case is the hard stop and is in the simulation solid;
  `overtravel` is there for a design to use.
- Connector positions were compared with the vendor CAD for the SKR's motor connectors and the PSU strip only.
- Automatic alignment of an inbox file picks among the 24 axis-aligned orientations and centres bounding boxes; a
  file with a cable or a different origin needs the JSON sidecar.
