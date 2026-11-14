# Buildability: will the parts fit and the machine work when it is made?

Seven checks were added to answer that question in simulation, and the printer was redesigned
against them. Everything here is simulated; nothing has been built.

## What was added

| # | Check | Where | What it does |
|---|---|---|---|
| 1 | Tolerance and fit | `mechloop/tolerance` | Gives every part a size and position error typical of how it is made (machined, sheet, saw-cut extrusion, purchased), builds the machine 3,000 times, and reports how often screw patterns start, shafts fit bores, belts stay in plane and the nozzle reaches the bed. Errors are solved over all joints at once, so closed loops such as a frame are handled. |
| 2 | Adjustment | same | Compares the adjustment each build needs (Z offset, bed level, rail alignment, nut float) with the adjustment the design declares. A machine that only works at nominal size fails. |
| 3 | Binding | same | For paired rails and lead screws, turns the built misalignment into side load and added drag, and compares the drag with the drive force. |
| 4 | Manufacture | `verifiers/manufacture.py` | For each custom part: plate or block, stock thickness, number of set-ups, sharp inside corners a cutter cannot make. |
| 5 | Real joints | `verifiers/fea.py` | Assembly stiffness is now a range: every touching face bonded (upper bound) and faces held only around their screws (lower bound). The digital twin uses the lower bound. |
| 6 | Subsystems | `verifiers/subsystems.py` | Endstops that are actually struck at the end of travel, cables long enough over the whole travel, extruder, hotend fan, control board and power supply present. |
| 7 | Heat | `verifiers/fea.py` | Thermal growth of the machine with the bed hot (CalculiX), reported as nozzle gap change and bed bow. Warping of the printed part is a rule of thumb and a warning only. |

## What they found in the printer that had been passing

`designs/printer_v2.py` passed every earlier check and printed well in the twin. Under the new
checks it has 20 errors:

| Finding | Detail |
|---|---|
| Nozzle gap not adjustable | built gap error 0.75 mm (99th percentile) against a 0.1 mm first layer; no Z offset adjustment |
| Bed not levelable | 1.33 mm out of level as built; bed bolted solid |
| Rails not parallel (Y and Z) | about 1 mm over the travel against 0.025 mm allowable; thousands of newtons of side load if tightened as built |
| Lead screw binding | nut 1.07 mm off the screw line, 341 N of added drag against 217 N of drive force |
| Fit not toleranced | hotend in a bore with zero nominal clearance: about half of builds do not go together |
| Five parts with sharp inside corners | not machinable as drawn |
| No endstops, cables, extruder, hotend fan or electronics | 9 errors |

None of these shows up in a nominal-geometry check or in the twin, which simulates the machine as drawn.

## The redesign: `designs/printer_v3.py`

An agent redesigned the printer through the loop without reading the verifier code. I then
re-ran everything myself after fixing the simulator defects the agent reported.

Result: passes all 11 verifiers, with 7 warnings (6 for parts not in the catalog, 1 for a part
that must be held during assembly).

| | v2 | v3 |
|---|---|---|
| New-check errors | 20 | 0 |
| Parts | 173 | 225 |
| Mass | not recorded | 9.22 kg |
| Bill of materials | $375 | $515 |
| Lowest resonance, X / Y | 69 Hz (Y) | 67 / 61 Hz |
| Cross-track error, RMS | 0.011 mm | 0.016 mm |
| Highest clean acceleration | 32,000 mm/s² | 14,000 mm/s² (3.5x the design value) |
| Assembly time estimate | 34 min | 45 min |

Buildability cost some performance: v3 is heavier, dearer, slower to build and has less
acceleration margin. Part of the acceleration drop is honest accounting rather than a worse
design, because the twin now uses the screw-only joint stiffness (1,279 N/mm in Y) instead of
the bonded value (1,636 N/mm).

Adjustment needed (99th percentile of 3,000 builds) against adjustment provided:

| Adjustment | Needed | Provided | How |
|---|---|---|---|
| Z offset | 0.67 mm | ±3.0 mm | jack screw striking the Z endstop |
| Bed level | 0.63 mm | ±1.5 mm | nuts on silicone columns |
| Y rail alignment | 1.01 mm | ±1.5 mm | rails on sliding T-nuts, set at assembly |
| Z rail alignment | 0.94 mm | ±1.5 mm | same |
| Lead-screw nut float | 1.10 mm | ±1.3 mm | floating nut |

As built and before adjustment, only 34% of machines reach the first layer and 5% are level
within half a layer. That is normal for this kind of machine; the point is that every one can be adjusted in.

Other v3 changes: the hotend no longer sits in a fitted bore (it seats in a corner under two
set screws); every custom part is a flat plate of stock thickness or a two-sided block with
radiused inside corners; three endstops, three cable looms, extruder, fan, control board and
power supply are in the model. With the bed 60 K hot, the bed rises 0.074 mm and bows 0.007 mm.

## Defects the redesign exposed in the simulators

Found by the agent or while re-verifying, and fixed:

- The extruder was classed as saw-cut extrusion because its part number starts with "EXT".
- Screws into sliding T-nuts were failing the pattern check; a T-nut moves to meet its screw.
- A shaft and a bore on the same line but not overlapping were reported as a fit.
- A thermal probe placed away from any meshed part silently reported the nearest part instead.
- Endstop and fan catalog parts had no mounting holes, so a screw through them read as a clash.
  Correcting the endstop then exposed a real clash in v3 at the end of Y travel, which was fixed.
- `--only` with a mistyped verifier name ran nothing and printed `ok: true`. It now stops with an error.
- **The intermittent wrong FEA answer is explained.** CalculiX, run multi-threaded, returned a
  wrong result for an identical input about once in 48 runs when other solves ran at the same
  time. Single-threaded, 200 of 200 concurrent runs were correct. The solver now runs single-threaded.

Known and not fixed:

- An adjustment is believed if it is declared. Nothing checks that the slot, jack screw or
  T-nut that provides it exists in the geometry with that much travel.
- The assemblability verifier's output when it cannot find an order is long and hard to act on.
- Process tolerances are typical values for each process, not a specific shop's.

## What still stands between this design and a machine that works

1. Tolerances and ratings are typical values. Real vendor data for rails, motors and extrusion would change the numbers.
2. Adjustments are declared, not verified against geometry.
3. Joint stiffness is a range, not a value. No bolt preload, friction or contact.
4. Print warping, cooling, bed adhesion and extrusion pressure are not simulated.
5. Wiring is three cable lengths. No connectors, strain relief, cable chains or routing collisions.
6. No fatigue, wear, belt tension or thermal drift over a long print.
7. The assembly time and holding counts come from a simulation of rigid parts with no hands in it.

The first build will still find things. The claim is narrower: the classes of first-build failure
listed in the table above are now caught before anything is cut.
