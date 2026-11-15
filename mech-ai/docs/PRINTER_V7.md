# printer_v7: printer_v6 corrected against the vendor data

Everything here is simulated. Nothing has been built.

`designs/printer_v7.py` starts from `designs/printer_v6.py` (v4, v5 and v6 were not edited). It passes all 12
verifiers: 0 errors, 7 warnings (full run of 2026-11-15, 08:02 to 08:18 UTC, report in `out/printer_v7/`; an
identical full run at 07:33 to 07:48 gave the same result). The
designer worked from findings, hints, `AGENT.md`, the documents, the parts catalogue and the public helpers of
`mechloop/electrical.py`. Verifier, tolerance, twin and assembly sources were not read. No catalogue part was
added and `mechloop/` was not edited.

v6 passed when it was designed. The vendor data sheets collected afterwards
(`reports/Vendor documents - what they change.md`, four batches) corrected the catalogue and the checks, and v6
then failed interference (coupler), subsystems (both endstops) and electrical (relay neutral), with a warning on
both Y motor shafts. v7 is the design work that follows.

## The stated target, line by line

A 180 x 180 x 180 mm open-frame demonstration printer whose every purchased part is off the shelf and every
fabricated part is printed, laser-cut or a single-set-up plate. Same target as v6.

| Target | Result | Met |
|---|---|---|
| 180 x 180 x 180 mm | working travel 180 x 180 x 183 (Z: 180 above home, 3 below); nozzle 0.10 mm above the bed at the top. Beyond that, declared over-travel: X and Y 1.5 mm at each end (homing), Z 1.65 mm past the nozzle plane | yes |
| every fabricated part printed, laser-cut or a single-set-up plate | 9 printed, 13 laser-cut, 2 plates machined in one set-up each (bed, tool plate) | yes |
| parts cost + fabrication estimate <= $900 | $727 parts + $129 fabrication ($112 machining, $15 cutting, $2 filament) = **$856** | yes |
| <= 320 parts | **309** | yes |
| assembly estimate <= 65 min | **64.6 min** (`score --assembly`; 64.7 in a separate `assemble` run) | yes, by 0.3 to 0.4 min. That is one or two fasteners: treat it as "at the target", not under it |
| direct drive, <= 0.40 kg moving in X | Roto + Revo on the guide block, **0.394 kg** with the block | yes, by 6 g |
| both Y belts within 1 mm of plane in >= 98 % of builds | **99.3 % and 99.1 %**, standard error 0.16 % and 0.17 % (3,000 builds); seven tolerance runs of the last geometries gave 99.0 to 99.3 % | yes, by more than six standard errors |
| a bed probe that works across the whole print area | it switches with the nozzle 0.60 to 2.16 mm above the bed over unit spread and temperature (0.90 to 1.50 over unit spread alone); it reaches **139.5 x 163 mm of the 180 x 180 mm** | **no**: strips of 36.5 mm (high X), 13 mm (low Y) and 4 mm (low X, high Y) are not probed |
| no stand-in purchased part | none: the probe is the catalogue's OMRON E2E-X10ME1 | yes |

Why the probe line is not met, with the numbers for every catalogue probe:

| | E2E-X5ME1 | E2E-X5E1 | E2E-X8MD1 | **E2E-X10ME1 (chosen)** |
|---|---|---|---|---|
| Body, kind | M12 unshielded | M18 shielded | M12 unshielded | M18 unshielded |
| On aluminium, nominal | 1.6 mm | 1.75 mm | 2.8 mm | 3.0 mm |
| Over +/-10 % unit and +/-10 % temperature | 1.28 to 1.94 | 1.40 to 2.12 | 2.24 to 3.39 | 2.40 to 3.63 |
| Highest face above the nozzle that still switches first | about 1.0 mm | about 1.1 mm | about 1.9 mm | 1.8 mm used |
| Z over-travel it then allows (must stay below the face) | under 1.0 mm | under 1.1 mm | under 1.9 mm | 1.65 mm |
| Z offset the build needs (99th percentile) | 1.48 mm | 1.48 mm | 1.48 mm | 1.48 mm |
| Electrical | NPN three-wire | NPN three-wire | two-wire: needs an interface module the catalogue does not have | NPN three-wire |
| Metal-free zone | 40 mm dia, 15 mm | none | 40 mm dia, 15 mm | 55 mm dia, 22 mm |
| Nearest place on this toolhead | about 29 mm left | about 31 mm left | about 29 mm left | 36.5 mm left, 13 mm behind |
| Mass (catalogue estimate) | 30 g | 70 g | 30 g | 70 g |
| Verdict | cannot have both a trigger margin and the Z over-travel the build needs | same | not wireable with catalogue parts | works; widest unprobed strip |

Only the 10 mm sensor has enough range on aluminium to leave both a real trigger margin and the Z over-travel
the tolerance simulation asks for. Its price is its metal-free zone: the head must be 27.5 mm from the Roto's heat
sink, the HeaterCore, the tool plate and the guide block, which puts it 36.5 mm left of the nozzle and 13 mm behind
it, in a printed arm. A further 4 mm all round is lost because an M18 head must stay 24 mm inside the plate edge
and the 220 mm bed is only 20 mm larger than the print area on each side. Covering the strips would take about
35 mm more X travel on one side (a longer rail than the beam, a wider frame), 13 mm more Y travel at the front
(the idler mounts are already at the frame's end) and a 230 mm bed. That is bending the machine for a number.
The honest statement of the result: **the nozzle prints 180 x 180 mm; the mesh is measured over 139.5 x 163 mm and
held at its edge value outside**. `mechloop tune` puts a number on what that costs (below).

Bed temperature. The three-wire E2E sensors are rated for 85 degC ambient, and their +/-10 % drift figure covers
up to 70 degC. v6 allowed a 100 degC bed over a 70 degC stand-in. v7 **limits the bed to 85 degC** in the firmware
block (`BED_MAX_C`, targets 60 and 85, `max_temp` 95): on an open-frame machine that gives up little (PLA, PETG),
and with it the `probe_near_hot_bed` warning is gone. Probe and mesh with the bed at 70 degC or below, which is
where the drift figure applies. The sensor's own temperature 1.8 mm above an 85 degC plate is not simulated.

## What changed from v6, and why

### 1. Endstops (OMRON D2F data sheet: operating position 6.8 +/-1.5 mm, not 9.0)

Every v6 striker stopped 3.7 mm short of the latest operating position. In v7:

- Both lever switches moved 2.3 mm towards their strikers (`ES_TRIG` 10.6 to 8.3 in the part frame).
- X and Y each declare 1.5 mm of **over-travel at both ends** (`Joint.overtravel`). The nominal operating position
  is at the end of the working range (x, y = -90). At the mechanical end (-91.5) the striker is 0.1 mm past the
  latest operating position, so every unit switches, and 0.15 mm short of the switch case. A unit at the early end
  switches 3 mm before that; the axis then believes it is 1.5 mm further than it is, which is what the 1.5 mm at
  the far end is for. The rails have it: 10.8 mm (X) and 12.6 mm (Y) left beyond the mechanical ends.
- The axis must be stopped by the switch signal, not by the striker: OMRON guarantees 0.55 mm of lever travel past
  each unit's own operating position, and 0.25 mm separates the latest operating position from the case.
- What had to move for it: the X switch stands on 8 mm spacers (its screws ended in the X rail's end once it moved
  2.3 mm inboard); the Y idlers moved 3.5 mm forward so the Y switch's screws can still be driven past them; the
  right idler mount grew 2 mm at the back for the switch's lower hole.
- Buy the gold-contact D2F-01L type (the catalogue part and BOM line now say so).

**Sensorless homing: considered, not used.** X: the 34 mm motor is a 30 ohm, 0.4 A winding run at 0.28 A. At
Klipper's sensorless homing speed (half a turn per second) its back-EMF is about 2 V against about 12 V of
resistive drop, which is the weak case for stall detection. Y: the back-EMF ratio is better (0.9 V against 1.4 V),
but two motors share one driver and the gantry would be squared by whichever side stalls first. Stall detection is
not simulated either. Switches are checked end to end, so both stay. The saving given up: 7 parts and about
70 s per axis.

### 2. Coupler (MH2025-5-8 vendor CAD: 8 mm bore 8.6 mm deep, hub clamps 7.5 mm)

The lead screw sits 8.0 mm in the 8 mm bore (v6: 12.5 mm, 3.9 mm into the spider). So that the stock 250 mm
screw still ends under the top back rail, the coupler sits 3 mm lower on the motor shaft: the shaft is 11.5 mm in
the 5 mm bore (12.05 allowed). Screw 81.5 to 331.5: 2.5 mm under the rail (v6 drew 4 mm; uncorrected it would have
been -0.5). Nut travel re-checked: the nut clears the coupler by 9.5 mm at the bottom; with the Z over-travel
32.9 mm of screw is left above the nut and 9.65 mm of rail above the upper blocks (Requirements).

### 3. Y belts 9 mm, pulleys turned round (motor drawing: 21 N at 20 mm; Gates: no 12 mm belt in 2 mm pitch)

| Y drive | Pull on the shaft | Belt plane from the motor face | Allowed there | Y resonance (range) | Owner's acceleration (range) |
|---|---|---|---|---|---|
| v6: 12 mm belt, hub towards the motor | 37.4 N | 16.25 mm | 25.8 N: **1.45 x over** | 60.0 Hz (STATUS.md, at 19 kN) | not re-scored |
| 12 mm belt, pulley turned, 3 mm idler spacer (trial) | 37.4 N | 13.25 mm | 31.7 N: 1.18 x over | 58.5 Hz (55.2 to 62.9) | 6,000 (4,200 to 9,000) |
| **v7: 9 mm belt, pulley turned, 3 mm spacer** | **28.4 N** | **11.75 mm** | **35.7 N: 0.79** | **54.6 Hz (51.1 to 59.5)** | **5,200 (3,600 to 8,100)** |

- The Y pulleys are turned hub-outboard, toothed end towards the motor, and the idlers stand on 3 mm stock
  spacers (v6: 6 mm). The belt plane is 4.5 mm closer to the motor face.
- An outboard support bearing was ruled out: the motor's shaft is 24 mm long and a 20-tooth pulley for a 9 mm
  belt is 18 mm (21 mm for 12 mm), so no shaft is left for a bearing; and it would add 8 parts.
- 9 mm is a Gates stock width with a stock sprocket (2MR-20S-09, 4.76 mm bore; ours is the generic 5 mm bore).
  12 mm is neither. All three belts are now one width.
- Cost: 3.9 Hz of Y resonance and about 13 % of the acceleration an owner would run, against the same machine on
  12 mm belts. The ranges overlap, so by the scorecard's own rule the difference is not shown; it is systematic
  (belt stiffness scales with width) and I take it as real. The motor limit rests on one drawing line whose
  meaning is inferred; Gates' *general* installation tension (75.6 N per span on 9 mm) would be 151 N on the
  shaft, which no NEMA 17 belt drive of this kind meets.

### 4. Z over-travel and print area

`Joint("z", range=(-3, 180), overtravel=(0, 1.65))`: the working range ends at the nozzle plane, the bed can rise
1.65 mm further. The generated config has `position_min: -1.55`. `design.printer["print_area"] = (180, 180)`.
The z_offset adjustment is that 1.65 mm against 1.48 mm needed. The probe's face is 1.8 mm above the nozzle, so
the nominal bed stops 0.15 mm short of it at the end of the over-travel.

### 5. Bed probe: OMRON E2E-X10ME1 (catalogue part)

Choice and numbers are in the target section. Mounting, per the data sheet's rules:

- A printed ABS arm (plastic is allowed inside the metal-free zone): an 8 mm flange on the rear face of the tool
  plate's left tab, two M3x16 from the rear into the tab (tapped through), and a 6 mm slab running back under the
  Roto's fan to the sensor. The slab is the plate the sensor's own two nuts clamp, 16 to 22 mm above the face.
- Nothing metal within 27.5 mm of the head in the 22 mm above the face: the verifier lists none. The margins are
  small where it matters: heat sink 28.75 mm, tab 28.2 mm, HeaterCore 30.4 mm; the Roto's fan starts 0.05 mm above
  the zone's top. The arm's screws sit above the zone.
- The hole is a fork open to the rear, closed by a printed key that the nuts also clamp, so the sensor (nuts on)
  slides in from behind. See checker note 1.
- Wiring: brown to the 24 V rail at the board, blue to 0 V, black to Z-STOP through a BAT85 diode
  (`series_diode=True`, BOM line), because the sensor pulls its output up to 24 V inside.
- The Revo is turned so its leads leave straight back (100 degrees), between the sensor and the fan plenum.

### 6. Relay neutral (BIGTREETECH Relay V1.2 manual: terminals LIN, N, LOT)

The neutral now runs inlet N to relay N to supply N (two wires, one twin ferrule in the relay terminal). v6 ran
the neutral past the relay: the real module would never have pulled in.

### 7. Part fan and duct

- **Fan: the catalogue's 24 V 30 mm fan on the board's 24 V fan output.** The sheet in hand (Sunon
  MF30101V2-1000U-A99) is the 12 V member of the family; using it needs a 24 to 12 V regulator module, and the
  catalogue has none (`add_regulator` needs a placed part; a hand-made one would be a stand-in). The 24 V sibling
  is what to buy; its current (0.05 A) is a typical figure with no sheet. `fan_voltage_mismatch` does not fire.
- **Duct drawn** (`part_duct`, printed ABS, replaces v6's carrier): a plenum behind the Roto that the fan bolts
  to, a closed 20.8 x 15.1 mm channel under the Roto's motor, a flange on the tool plate's right tab, and a
  12 x 6 mm outlet in the channel's left wall, 13 mm from the nozzle axis, 4.5 to 10.5 mm above the nozzle plane.
  Underside 2.55 mm above the nozzle plane. Checked: geometry, clearances over the whole travel, printability
  (30 mm bridge, 0.93 mm thinnest wall), assembly. Not checked: air. It blows from one side and partly at the
  nozzle block; a blower would be the right part and the catalogue has none.
- The fan is 6 mm further back than in v6, so bed and gantry moved 3 mm forward (`BED_Y1`, arms 213 mm): the fan's
  screw heads stay 2.7 mm clear of the Z uprights at the rear end of the Y over-travel.

### 8. Mains inlet (SCHURTER DD11 drawing)

The panel takes its cut-out (28.1 x 47.1, R1) and hole pattern (56 mm) from the part. The `holes_too_close`
warning stays at 2.75 mm against 3.0: it is SCHURTER's own pattern and clears only in sheet of 2.5 mm or thinner.
The order number, fuse drawer and fuse-link are still to be pinned (the catalogue part says so).

### 9. v6's weak points

| Weak point | v7 | Result |
|---|---|---|
| X rail on a vertical face, located only by its T-nut screws | **two laser-cut stops** (one part, used twice) on the beam's rear face beyond the block's travel: each stop's top edge sits against the underside of the Y plate (the face the beam top sits against) and a finger reaches under the rail; the rail is laid on the fingers and screwed | `x_beam / x_rail` is no longer among the contributors; nozzle-height scatter 1.62 to 1.48 mm. The rest is screw-hole play at the guide block and the Roto (3.2 mm holes on the block were tried: no change) |
| X nozzle stiffness 1,435 N/mm, single-bolt beam joints | **two M5 per side** under each Y plate, 12 mm apart (the idler pulley and the belt block leave no room further in) | 1,535 N/mm (+7 %), Y 2,099. Small. The twin's X figure is governed by the block's tilt and the belt, not by this |
| Assembly 66.0 min | bed heater 180 W on the board's own output: **no MOSFET module** (10 parts, 3 screw sets, 2 wires fewer); the relay board on three of its four holes | 64.6 min with 4 parts and 3 fasteners added for the datum and bolts |
| Belt-plane share within sampling error of 98 % | pulleys nearer the mounts, 3 mm idler spacers, two-bolt beam joints | 99.3 / 99.1 %, +/-0.17 % |
| Sub-assemblies not used by the check | `design.subassemblies` as in v6 (electronics, bed carrier with its bracket screws, motors on plates, X idler unit, fan on duct); the verifier builds them as units | complete, 151 of 151 fasteners drivable |

The MOSFET module was there because a 200 W pad overloaded the board's bed output (8.2 A against 8 A allowed).
With the bed limited to 85 degC a 180 W pad is enough: 7.4 A, board total 10.1 A on its 20 A fuse, supply at 69 %.

Tried and dropped: more bench sub-assemblies (tool plate unit, Y idler units, rail with its block) made the
estimate worse (67.0 to 67.4 min: one more turn of the assembly); a 22.5 degree fork for the sensor (the planner
only moves parts along the axes); 3.2 mm holes in the tool plate.

## What the verifiers caught, and the fixes

| Run | Finding | Fix |
|---|---|---|
| v6 copy | interference + `shaft_too_deep_in_coupler` (3.9 mm); `endstop_not_reached` x2 (3.70 mm); `motor_shaft_radial_load` x2 | sections 2, 1, 3 |
| fast 1 | interference: X switch screw in the X rail's end | 8 mm spacers under the X switch |
| fast 1 | motion: part fan into a rear corner bracket at the new over-travel corner | fan moved left (its right edge decides) |
| fast 2 | interference: inlet body in the old cut-out (the part changed) | section 8 |
| fast 2 | interference: Roto screw head in the plenum; manufacture: beam-bolt slot 0.25 mm from the tongue's edge, slots 2.5 mm apart; hole 1.4 mm from the idler mount's edge (three times, as the switch moved) | pocket; bolts at 127 and 139 with the tongue 7.5 mm longer; mount edge tied to the switch hole |
| fast 2 | subsystems `probe_metal_in_clear_zone`: Revo's lead stub 27.35 mm from the sensor | Revo turned to 100 degrees |
| fast 3 | requirements: 329 parts, 0.4007 kg toolhead | two lightening windows in the tool plate (same set-up); relay and MOSFET boards on three screws; later no MOSFET module |
| full-length 1 | motion: fan screw heads into both Z uprights and a bracket at the rear | bed and gantry forward (5 mm, later 3 mm with a 6 mm plenum) |
| full-length 1 | assemblability, 27 errors: the sensor with its nuts cannot enter a closed hole; bed carrier unit without its bracket screws | fork; bracket screws and nuts added to the unit |
| partial | subsystems `probe_not_clamped` (5 of 8 points) with the fork | key; sensor turned 22.5 degrees about its axis (checker note 1) |
| partial | assemblability: Y switch screw blocked by the Y idler | idlers 3.5 mm forward |
| partial | manufacture `wall_too_thin_to_print` on the key (cusps) | key shortened |
| partial | electrical `flex_span_crosses_part` (gantry loom through the Y guide block, then a corner bracket, then the X motor plate) after the gantry moved forward | 3 mm instead of 5; frame clamp at y = -134.4 |
| partial | tolerance `adjustment_too_small` (1.61 mm against 1.5) | rail stops; over-travel 1.65 with the sensor face at 1.8 |
| full 1, full 2 | pass | |

Two full verifies (the second only to write the report into `out/printer_v7/` directly), about 45 partial runs,
11 `assemble` runs, 2 belt-width score runs on scratch outputs.

## v6 against v7

v6 figures: `out/printer_v6/report.json` and `docs/PRINTER_V6.md` (full run of 2026-11-15 04:35 UTC, before the
checks were corrected); its resonance at 19 kN from `STATUS.md`. v6 was not re-scored at 19 kN, so its acceleration
figures are at the old 22 kN belt stiffness and are not comparable. v7: full verify and `score --assembly` of
2026-11-15, about 08:00 UTC.

| | v6 | v7 |
|---|---|---|
| Passes all 12 (against today's checks) | no: interference, subsystems, electrical | yes |
| Parts | 317 | 309 |
| Total mass | 10.24 kg | 10.25 kg |
| Bill of materials | $719 | $727 |
| Fabrication: machining / cutting / filament | $112 / $15 / $2 = $129 | $112 / $15 / $2 = $129 |
| Parts + fabrication | $848 | $856 |
| Custom parts: machined / sheet / printed | 2 / 11 / 7 | 2 / 13 / 9 |
| Printed | 62 g, 4.4 h | 69 g, 4.9 h |
| Moving mass X / Y / Z | 0.351 / 1.319 / 2.677 kg | 0.394 / 1.382 / 2.679 kg |
| Nozzle stiffness X / Y, screw-only (bonded) | 1,435 / 2,036 (2,311 / 2,409) N/mm | 1,535 / 2,099 (2,342 / 2,466) N/mm |
| Resonance X / Y at 19 kN belt stiffness | 78.2 / 60.0 Hz | 74.0 / 54.6 Hz (ranges 68.8 to 81.5 / 51.1 to 59.5) |
| Acceleration an owner would run | 6,800 mm/s^2 at 22 kN (4,400 to 9,600) | 5,200 mm/s^2 (3,600 to 8,100) |
| Step-loss ceiling | 10,000 at 22 kN | 8,000 (6,000 to 12,000); Y loses steps first, at 10,000 |
| Cross-track RMS / worst (test cube) | 0.012 / 0.107 mm | 0.014 / 0.139 mm |
| Benchmark print time | 2,571 s | 2,571 s |
| Y shaft load / allowed | 37.4 / 25.8 N | 28.4 / 35.7 N |
| Y belts within 1 mm of plane | 98.4 / 99.0 % (no error stated; +/-0.3 % seen) | 99.3 / 99.1 % (standard error 0.16 / 0.17 %) |
| X belt within 1 mm | 99.4 % | 99.4 % (0.14 %) |
| Bed with 3x payload, screw-only | 432 N/mm | 418 N/mm (arms 3 mm longer) |
| Drive margin X / Y / Z | 8.5 / 7.7 / 3.4 | 7.8 / 7.4 / 3.4 |
| Bed heater, supply load | 200 W through a MOSFET module, 75 % | 180 W on the board, 69 % |
| Assembly time estimate | 66.0 min | 64.6 min |
| Needs holding / fasteners / fastener types | 88 / 152 / 10 | 81 / 151 / 10 |
| From below / turned / tool changes | 14 / 5 / 5 | 17 / 4 / 7 |
| Probe | stand-in, 32 and 6 mm strips, 70 degC under a 100 degC bed | catalogue part, 36.5 / 13 / 4 / 4 mm strips, 85 degC over an 85 degC bed |
| Warnings | 8 | 7: 3 manufacture (two small-hole notes, the inlet's web), mesh strips, hotend cut-off, one unsupported assembly step, corner bulge 0.35 mm |

Adjustment needed (99th percentile of 3,000 builds) against provided:

| Adjustment | v6 needed | v7 needed | v7 provided |
|---|---|---|---|
| Z offset | 1.62 mm | 1.48 mm | 1.65 mm of declared Z over-travel (probe offset in the firmware) |
| Bed level | 1.21 mm | 1.17 mm | +/-1.5 mm |
| Y rail alignment | 1.05 mm | 1.08 mm | +/-1.5 mm |
| Z rail alignment | 0.83 mm | 0.89 mm | +/-1.5 mm |
| Lead-screw nut offset | 0.16 mm | 0.16 mm | +/-1.3 mm float |
| Screw to rail angle | 0.84 deg | 0.62 deg | coupler 1.0 deg (assumed figure) |
| Belt tension X, Y | not modelled | not modelled | +/-3 mm each |

### What got worse

- **Dynamics.** X 78.2 to 74.0 Hz (the real probe and its arm add 43 g to the toolhead), Y 60.0 to 54.6 Hz (9 mm
  belts, 63 g more on the gantry). The acceleration an owner would run is 5,200 mm/s^2; its low end (3,600) is
  under the 4,000 the joints declare. With Klipper planning and input shaping the figure is 4,200 (3,400 to 5,500).
- **Probe coverage**: 139.5 x 163 mm against v6's 148 x 174 (of a stand-in that could not have worked as wired).
- **Bed limited to 85 degC**, 180 W: 60 degC is reached later than with 200 W.
- **Margins that are thin**: toolhead 6 g under its limit; assembly 0.4 min under; Z over-travel 0.17 mm over the
  need; the sensor's metal-free zone by 0.05 to 1.3 mm; endstop window 0.1 / 0.15 mm.
- From below 14 to 17 (the rail stops go on from below), tool changes 5 to 7.

## Allowances and overrides

- `allow_overlap("hotend", "extruder")`: the Revo screws 0.7 mm into the Roto's seat (a real thread), as in v6.
- The automatic thread overlaps of `add_screw(threads_into=...)` and `add_nut(screw=...)`.
- `process="purchased"` on the extruder, `meta={"print_up": ...}` on printed parts, as in v6.
- `d.join("bed_probe", "probe_arm", ...)` and `d.join("probe_key", "bed_probe", ...)`: clamped by the sensor's nuts.
- The sensor is placed turned 22.5 degrees about its own axis (checker note 1). It changes nothing physical.
- No limit, threshold, DFM limit or electrical requirement was changed. One of **my own** settings changed: the
  bed's firmware targets (60 / 100 to 60 / 85 degC), which is the stated remedy for the probe's rating.
- Requirements: the rail-margin and Z-beyond requirements now read the joints' mechanical ranges (stricter); the
  "no stand-in" requirement now demands an empty list (v6 allowed the probe); one new requirement (probe switches
  first, over-travel below its face).

## Checker behaviour I think is wrong or worth a look

1. **`probe_not_clamped` counts eight fixed points per part, in the sensor's own frame.** The catalogue sensor
   has its nuts fused to its body, so it cannot be assembled through a closed hole (`trapped_part`: "no straight
   way in: blocked by ['probe_arm']"). Any slot wide enough for the thread and open along an axis removes three
   of the eight points, and a second part filling the slot is not counted. Reproduce: in `designs/printer_v7.py`
   set `PRB_TURN = 0.0` and run `--only subsystems`: `probe_not_clamped ... material under 5 of 8 points`, with the
   key in place and the ring complete. With `PRB_TURN = 22.5` (a round part turned about its own axis) it passes.
   A fork opened at 22.5 degrees also passes it but the assembly planner cannot insert along a diagonal.
2. **Z over-travel is checked against parts that move with the nozzle.** With `Z_UP = 2.2` (above the sensor's
   1.8 mm): `motion_collision: bed hits bed_probe ... at pose {'z': 182.2}`. In a build that needs the over-travel
   the nozzle and the probe are both that much higher, so nothing meets. As it stands the rule ties the z_offset
   adjustment to the probe's range and is what rules out the two 5 mm sensors here. A nominal machine driven to
   the end of its over-travel would crush its nozzle first, which the check already allows.
3. **Declaring more bench sub-assemblies raises the time estimate** (66.6 to 67.0 / 67.4 min for units that
   plainly save handling), through one more turn of the assembly and a tool change. The estimate also differs
   between `score --assembly` (64.6) and `assemble` (64.7) on the same file.
4. **The generated `printer.cfg` calls the probe's distance a "recalled class value"** in its comment
   (`[probe]`, z_offset line) although the part is the catalogue's OMRON sensor with a chart reading.
5. **`probe_near_hot_bed` is a comparison of two numbers**: it disappears at a bed limit equal to the rating
   (85 against 85) with no margin and no temperature model. Not wrong, but a pass here is thin evidence.
6. `mechloop verify --out out/printer_v7` writes into `out/printer_v7/printer_v7/`; `score`, `tune` and `print`
   then do not find the report (tune silently fell back to "belt stiffness only"). The default `--out` is right.

## Still unverified

- Stall-free homing against the 0.1 / 0.15 mm switch window: it rests on the firmware stopping on the signal.
- The probe: sensing distance on a large 6 mm aluminium plate (the chart is for small 1 mm plates and "still
  falling" with size), repeatability (assumed 0.01 mm), its temperature next to an 85 degC bed, its mass (70 g
  is an estimate), the fork-and-key clamp, the arm's stiffness (not in any FEA case), the 0.05 mm by which the
  Roto's fan clears the metal-free zone.
- The motor's shaft-load limit (one drawing line), belt stiffness against tension, 5 mm bore pulleys as stock.
- The 24 V fan (no sheet), the duct's air flow, heat on the duct 4 mm from the HeaterCore.
- The rail stops: the tolerance model takes them as the rail's datum; that the rail really seats on two 3 mm
  fingers while its screws are tightened is a bench matter.
- 180 W to 85 degC: heat-up time and the PID are simulated on assumed pad and plate figures.
- Relay contact rating and its state at power-up (not in the manual); the inlet's order number.
- Everything v6 listed that v7 did not touch (Roto housing stiffness, single-block tilt, frame stiffness, cable
  ties as belt anchors) and everything `AGENT.md` and `docs/ELECTRICAL.md` list as not checked.

## Scores and firmware in the loop

All on 2026-11-15 on the final design file; twin parameters as committed that day (belt stiffness 19 kN per 6 mm).

`mechloop score designs/printer_v7.py --assembly` (07:48 to 08:01 UTC, built-in planner):

| Score | Value | Range |
|---|---|---|
| Resonance X / Y | 74.0 / 54.6 Hz | 68.8 to 81.5 / 51.1 to 59.5 |
| Acceleration an owner would run | 5,200 mm/s^2 | 3,600 to 8,100 |
| Step-loss ceiling (first failure 10,000, Y loses steps) | 8,000 mm/s^2 | 6,000 to 12,000 |
| Cross-track RMS / worst | 0.0139 / 0.139 mm | 0.0094 to 0.0203 / 0.089 to 0.182 |
| Benchmark time | 2,571 s | |
| Moving mass X / Y / Z | 0.394 / 1.382 / 2.679 kg | |
| Toolhead tilt term on X (one MGN12H, arm 43 mm) | 466 N/mm at the nozzle | |
| Melt rate | cap 12 mm^3/s (Revo), 4.9 asked for: not limited | |
| Assembly | 64.6 min, 309 parts, 151 fasteners, 81 to hold, 17 from below, turned 4 times, complete | |

Belt-width trial (same file, Y belt width only, scratch outputs): 12 mm 58.5 Hz, 6,000 mm/s^2, ceiling 10,000;
9 mm 54.6 Hz, 5,200, ceiling 8,000 (one sweep step, which the scorecard says is not a real difference).

`mechloop score designs/printer_v7.py --firmware klipper --firmware-only` (07:48 to 07:55 UTC, Klipper `29d4ec2`):

| | Shaper and pressure advance off | As configured |
|---|---|---|
| Input shaper | none | X: EI 91.8 Hz; Y: MZV 53.6 Hz |
| Cross-track RMS / worst at 4,000 mm/s^2 | 0.0095 / 0.106 mm | 0.0063 / 0.049 mm |
| Corner bulge | 0.40 mm | 0.20 mm |
| Highest clean acceleration in the sweep | 12,000 (16,000: Y loses steps) | 48,000, the highest tried |
| Klipper's shaper rule / what an owner would run | | 8,400 / 4,200 mm/s^2 (3,400 to 5,500) |

v6's figures in the same table were 10,600 / 5,300 (at 22 kN). The joints' 4,000 mm/s^2 is inside the range and
just under the expected value: this machine is not a fast one, and the Y axis is why.

`mechloop tune designs/printer_v7.py` (08:02 to 08:04 UTC, with the report's FEA stiffness): shapers as above
(predicted resonances 72.7 / 53.3 Hz); pressure advance 0.042 s from the sweep (bulge 0.30 to 0.15 mm); bed mesh
on the assumed surface (0.30 / 0.20 mm tilt, 0.15 mm bow), 5 x 5 points over the 139.5 x 163 mm the probe reaches:
first-layer gap error over the whole 180 x 180 mm 0.097 mm RMS / 0.305 worst without the mesh, **0.011 / 0.036
with it, the unprobed strips included** (v6: 0.010 / 0.031). So on a plate that is tilted and bowed smoothly the
strips cost about 0.005 mm; a local dip inside a strip would not be seen at all.

Firmware in the loop, `mechloop print designs/printer_v7.py examples/motor_bracket.py:bracket --firmware klipper
--trajectory --out out/printer_v7/fil/bracket` (08:02 to 08:14 UTC): Klipper accepted the generated `printer.cfg`
and planned the whole print with no message. 255 layers, 3,891 s, 15.3 g. Outline match 98.3 % mean, 97.6 % worst;
boundary deviation 0.033 mm mean, 0.046 worst; no layer shift; 0 collisions in 4,074 poses; the lowest thing after
the nozzle is the probe, 1.8 mm above the nozzle plane; peak step rate 19,753 /s of 263,000. One warning: corner
bulge 0.35 mm (that print ran at the default pressure advance, 0.0315 s, not the tuned 0.042).

The design file did not change after the first full verify; scores, tune and the bracket print are of that file.

## Decisions that should be confirmed

1. **Probe: OMRON E2E-X10ME1** in a printed arm 36.5 mm left and 13 mm behind the nozzle; coverage target not
   met and reported as such; bed limited to 85 degC.
2. **9 mm belts on Y** with the pulleys turned round, for the shaft load and for stock parts, at 54.6 Hz.
3. **Lever switches on X and Y** with 1.5 mm of declared over-travel; no sensorless homing.
4. **24 V part fan** from the catalogue (no sheet) rather than the 12 V Sunon part with a regulator that is not in
   the catalogue. Parts I would want added: a 24 to 12 V regulator module or the 24 V fan's sheet, a 4010 blower,
   an interface module for two-wire sensors (the 8 mm M12 sensor would fit better than the M18).
5. **No MOSFET module**, 180 W bed heater on the board's own output.
6. Rail stops and two beam bolts per side kept although they cost about 100 s of assembly.

## Files

- `designs/printer_v7.py`: the design.
- `out/printer_v7/`: `report.json`, `views.png`, `simulation.gif`, STEP, DXF profiles of the 13 sheet parts,
  `electrical/printer.cfg`, `wiring.csv`, `scores.jsonl`, `score/`, `tune/`, `fil/bracket/`.
- `docs/PRINTER_V7.md`: this file. One row in `README.md`, one paragraph in `STATUS.md`.
