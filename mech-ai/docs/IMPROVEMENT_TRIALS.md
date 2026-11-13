# Improvement trials: simulation in the design loop

Two agents were each given a passing design, a score from simulation, and the instruction to make
real design changes that raise the score while every verifier still passes. Neither could read the
simulator code. Numbers below are from the simulators as corrected after the trials.

## Printer: print quality (digital twin + FEA + drive sizing)

`designs/printer.py` → `designs/printer_v2.py`. Both pass all eight verifiers.

| Score | Baseline | Improved | |
|---|---|---|---|
| Y resonance | 39 Hz | 69 Hz | better |
| X resonance | 77 Hz | 93 Hz | better |
| Sideways error at nominal settings, RMS / worst | 0.036 / 0.24 mm | 0.011 / 0.10 mm | better |
| Highest clean acceleration (at 2x speed) | 16,000 mm/s² | 32,000 mm/s² | better, but this score is coarse and noisy |
| Benchmark print time | 2,564 s | 2,564 s | unchanged |
| Moving mass on Y | 1.18 kg | 1.16 kg | |
| BOM cost | $343 | $375 | +9% |
| Estimated assembly time | 30 min | 34 min | worse |
| Parts / screws | 154 / 84 | 173 / 97 | worse |

What the agent changed: 12 mm belts in place of 6 mm on all axes, a second Y motor and belt on the
other rail, a smaller X motor (it rides on the Y axis). It tried raising speed and acceleration
limits three times and reverted each: the time gain was 2-3% and vibration got worse.

How much to believe:
- Wider belts and a second Y drive are sound in kind. The size of the gain rests on an assumed belt
  stiffness that is known only to about ±30% and is taken as proportional to width.
- The agent's own caveats: a 12 mm belt on a 20-tooth pulley on a 5 mm shaft is an unusual part; the
  catalog prices pulleys the same at any width; two open-loop motors on one axis can fight; the new
  motor ear and belt clamp tower are in no FEA case; racking, the main real benefit of driving both
  sides, is not modelled at all.
- The print-quality gain cost assembly effort. Nothing in the trial weighed one against the other.

## Z axis: ease of assembly (assembly simulation)

`designs/z_axis.py` → `designs/z_axis_v2.py`. Both pass every verifier.

| Metric | Baseline | Improved |
|---|---|---|
| Parts | 86 | 76 |
| Screws | 51 | 43 |
| Parts that need holding until fastened | 16 | 13 |
| Estimated assembly time | 16.0 min | 13.3 min |
| Screw types / tools | 4 / 2 | 4 / 2 |

What the agent changed: the motor, its mount and coupler became a bench sub-assembly; locating
pockets for the bed standoffs; a ledge for the rails and lower carriages; a rib that spaces the
carriage pairs; top brackets moved above the beam so they rest on it; two brackets and eight rail
screws removed, each with a stated structural reason.

How much to believe:
- Most of the time saving is fewer screws and parts, which is real. The time allowances themselves
  are rough and should only be used to compare designs.
- The agent flagged that two of its features (ledge, rib) scored partly because the simulation
  fitted loose carriages one by one, which nobody does. Their real value is as locating datums.
- Removing rail screws gives up the rail's rated straightness; acceptable here only because the
  load is about 3 kg.

## What the trials found wrong with the simulators

Found by the agents, all fixed:
- The twin used one belt stiffness for the whole machine, so widening an unrelated belt was
  rewarded and a second belt on an axis got no credit. Now per axis, parallel belts summed.
- The design's speed limit had no effect on any score. Print speeds are now declared by the design.
- Assembly results changed from run to run (12 or 19 parts needing holding for the same file).
  Now identical on every run.
- Screws and holds inside a sub-assembly were not counted, so making sub-assemblies looked better
  than it was.
- The tip test used the middle of the bounding box instead of the centre of mass.
- A held part could "support" another part. Now anything resting only on loose parts needs holding.
- Screws were all driven at the end. Now each part is fastened as it goes on.

Not fixed:
- The highest-clean-acceleration score is coarse and jumps a step for no physical reason.
- Screw access is checked at the home pose only, so a rail cannot be modelled with its carriages
  already on it.
- The FEA occasionally returns a result whose forces do not balance (seen three times, never
  reproduced on demand). It is now detected, the evidence saved, and the identical model re-solved.
- Neither simulator models what the agents wanted most: a frame-mounted X motor (needs belts
  spanning two axes), belt tension, input shaping, or fastening order chosen to minimise holding.
