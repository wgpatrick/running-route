# printer_v12.1 change queue (owner review, 2026-11-21)

Base: printer_v12. Process: docs/OPERATING_MODES.md (iterative mode). Each item is ONE change behind a named flag in
designs/printer_v12_1.py, built as v12 + that change, affected-tier verified, part_quality-checked on changed parts, and
exported as a change set (format below). A change is listed as "proposed" only if it adds NO new errors against v12;
otherwise status "needs work" with a one-line reason. Rebuild changed parts from a short spec (functions, mates, loads,
process, envelope) in their own function in local coordinates; derive holes from mating parts. Real parts only (DG-07).
Owner guidance: fixes only, no new features.

## Change-set format (review page Changes tab)
- review_v12_1/changes/index.json: {"base":"printer_v12","changes":[{"id","title","summary","threads":[...],"status",
  "depends_on":[...],"removed":[...],"modified":[...],"added":[...],"checks","file":"changes/<id>.json"}]}
- review_v12_1/changes/<id>.json: {"mesh":"changes/<id>.txt","parts":[data.json-style records + "v":[off,count],"t":[off,count]]}
- review_v12_1/changes/<id>.txt: base64 blob (float32 xyz, uint32 tris), offsets from 0. Tool: tools/build_change.py.
- "checks": plain, self-consistent: affected-tier result vs v12 (new / cleared errors), part count change, part_quality.

## Memory rule (16 GB, 4 cores, several workers)
Wrap every design build / verify / FEA run in `flock /tmp/mechloop_heavy.lock <command>` so only one heavy job runs at a time.

## Group A: Z axis and bed
1. znut-direct (thread 10eab134-e341-4786-bae2-d085e018c34d): bolt each POM nut flange straight to its nut plate (flange holes
   from drawing A4003; flag if unknown); remove nut_keeper*, spacers, keeper bolts/washers/nuts, nut_pin*, sleeve, pin nut.
   Fix the tool-access errors this created. Re-run Z binding/tolerance.
2. carriage-plate-rigid (13a834f6-56df-4aa7-aa8e-9cdb9fec30e1, 9f8b0379-a448-4333-a410-5e3f42595fe6): straight 6.35 mm 6061
   plate, no notch, short (block moved up beside the square), 4 x M3 to block, 2 x M5 to T-nuts in the square; rigid; delete
   guide_float; assembly alignment procedure (one rail datum, other run-in then tightened) in build steps. Fallback: cut stock
   6061 angle (McMaster, 1/4 in wall).
3. rear-z-inside (cc37dd59-6fa9-4d22-91dc-1ba874609e41): rear Z same design as the fronts, inside the frame, about y 154.5;
   check toolhead / gantry rear travel; if blocked move sideways or move the square forward, never outboard. Update Z_TILT.
4. spool-closer (f2ab0822-37c9-47a9-a7c7-ba113e35cbd2), depends on rear-z-inside: spool starts about y 192; shorten
   spool_sleeve_0; shortest stock SFAL8 axle.
5. bed-thumb-reach (2211e7e2-0d7e-485a-adfb-083c2c2d279c): keep hand levelling (springs, thumb nuts). Move the three points so
   each thumb nut has >= 20 mm finger clearance all round (or a larger knob below the 2020). Keep fitted / slot / oversize.
   Add a finger-clearance requirement for all hand-adjusted parts.

## Group B: electronics and frame base
6. estop-mount (2f0e34d2-c001-48b0-b638-0124835243d0): faithful A22E re-make (bushing, ring nut, block behind the panel), no
   allow_overlap, stiffer L-bracket. Fix the newly failing requirement "v11" and the old-format checks line.
7. electronics-under-deck (f1532e90-c206-456d-be9b-58200136befb, 4a441af3-7ee8-40a2-a9e6-2572f186fa46,
   9b01f6b8-350d-4237-800b-c18ab0f3b679): tray becomes a raised deck; board, Pi, PSU, contactor, interface relay, G9SE
   safety relay (moved off the back wall, rail oriented so its 111.6 depth is horizontal), inlet bay on its underside;
   vented removable bottom cover; grommets; front Z motors stay above. Service by removing the cover and tipping the printer
   over (owner confirmed). Check bed lowest Z vs deck, temperatures, cable reach, mains/SELV separation, feet height
   (stock MISUMI), tip-over safety. Plain one-line role descriptions for the mains-bay parts and a wiring sequence on the
   electronics sheet. G9SE reset button (placeholder) beside the e-stop.
8. octopus-full (258b63db-2f81-45ba-94c5-b5d941e9af25): viewer mesh from the full BTT STEP (decimated); checks use a keep-out
   solid of the full board outline and component heights.
9. foot-washers (1e658c86-8c6c-4222-8e7f-745c4f4b023a): DIN 9021 M5 washer between each foot jam nut and the rail.

## Group C: gantry, toolhead, top
10. y-motor-mount-stiff (ab6949c1-785c-4e48-b181-d6364f466607): 4.8 mm 6061, extended down post_rb with at least one more M5
    T-nut fastener spaced from the others; handling load 100 N at the motor: no yield, < 0.5 mm.
11. y-idler-mount-stiff (4d13dc1c-0a9c-4f01-a331-48419d3eff9e): 4.8 mm 6061 plus a bent stiffening flange on the free edge
    (SendCutSend rules); idler axle deflection < 0.05 mm under belt tension.
12. y-belt-clamp (ec55504e-d24e-4a31-a988-f6e1ecb6a297): replace the slot weave with a toothed clamp (like the X clamp),
    remove slots, draw the belt into the clamp, holding force >= 3 x working tension.
13. x-belt-low: X belt plane as close to the X rail / block as clearances allow (motor mount, idler mount, clamp, pulley
    heights); report old/new offset and block moment per N of belt force.
14. part-cooling-rebuild: check blower outlet direction (Delta drawing), fix if reversed; rebuild part_duct from a spec (inlet
    = blower outlet, smooth path, jet at the nozzle tip, >= 1.2 mm walls, no internal supports, real screws); add a
    duct/fan alignment check.
15. topdown-camera (e27554c6-9501-4b74-97a3-08679ac0af62): Pi Camera Module 3 Wide (SC1224), tilted down about 55 deg from
    frame_top_back; gantry parked for photos; camera-view check (full sheet + calibration target visible, unoccluded) on
    both cameras, rendered views saved.

## After the groups
16. sheet-stiffness-sweep: stiffness check for every sheet part carrying belt, motor, guide, bearing or handling loads
    (working: belt/guide deflection < 0.05 mm; handling 100 N: no yield, < 0.5 mm); one change per failing part.
17. Low priority: endstop carriers' 0.09 mm web; z_motor_plate outlines with true arcs (when touched).
