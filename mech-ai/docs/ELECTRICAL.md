# Electrical system: model, verifier and the printer_v4 result

Everything here is simulated. Nothing has been built, wired or powered.

`designs/printer_v4.py` is printer_v3 with a complete electrical system. It passes all 12 verifiers,
including the new `electrical` one, with 0 errors. **No custom PCB is needed**: every electrical element
is a board, module or component that can be bought; the builder cuts and terminates wire.

## The model (`mechloop/electrical.py`)

A design declares `design.electrical = Electrical(...)`:

| Object | What it holds |
|---|---|
| `Device` | kind (board, psu, inlet, relay, mosfet, heater, thermistor, thermal_fuse, fan, stepper, endstop, host, earth_point), the CAD part that represents it, typed `Port`s, ratings, the source of each rating, and a `product` record (what to buy) |
| `Port` | kind (power in/out, heater output, stepper output, fan output, thermistor input, endstop input, mains, PE, series, signal), connector type, current rating, MCU pin, position and plug direction in the CAD |
| `Wire` | from port, to port, AWG, conductor count, insulation, the looms it runs through, optional high-temperature pigtail at the device end; length is computed from the route |
| `Loom` | waypoints tied to bodies; two consecutive waypoints on different bodies are a flexing span with its own cable length; each flexing span is also written into `design.cables`, so the existing subsystems check does the length-over-travel test (not duplicated) |
| `firmware` | Klipper settings: run current per axis, heater/sensor pairs, control law, min/max temperature, `verify_heater`, fans |
| `Bay` | which devices share the electronics bay and how it is ventilated |

Catalog parts are in `mechloop/parts/electrical.py` (`python -m mechloop catalog`). Entry points for
other tools: `electrical_loads(design)` (currents, delivered voltages, power), `thermal_plants(design)`
(one `HeaterPlant` per firmware heater: thermal network, heater node, sensor node, thermistor, cut-offs),
`simulate_heater(plant, cfg, target, t_end, fault=...)` and `klipper_config_path(design)` =
`out/<name>/electrical/printer.cfg`.

## What the verifier checks (`mechloop/verifiers/electrical.py`)

Each finding names the part or wire, the value, the limit and a hint. Limits are in
`DEFAULT_REQUIREMENTS` and can be overridden per design in `electrical.requirements`. A check that
raises is reported as an error (`check_crashed`), never as a pass. A design with no `design.electrical`
is reported as `skipped` with the reason, not as a pass of anything electrical.

| Check | Basis | Default limit |
|---|---|---|
| Completeness | every motor, heater, sensor, fan and endstop traced through the wiring to a compatible board port; one wire per port; each heater has a thermistor and a firmware entry; each printer axis has a driver and an endstop or sensorless homing; Klipper has a host; every electrical CAD part has a device and every device a fastened CAD part | none missing |
| Off the shelf | every device has a `product` record; `custom_pcb` or not `off_the_shelf` is an error | zero custom PCBs |
| Power budget | all heaters at 100 %, all motors at run current (copper loss + driver loss), fans, board, host, wire loss, against the supply rating; board input fuse; 5 V rail | load <= 85 % of supply, <= 80 % of fuse |
| Wires | conductor temperature from I^2R against heat loss from the wire surface (12 W/m^2K, still air), derated by the IEC 60364-5-52 grouping factor for the loaded conductors sharing a loom | conductor <= 70 degC or the insulation rating |
| Connectors, outputs, series devices | current against the port rating and the connector class rating | <= 80 % continuous |
| Voltage drop | routed length, gauge, conductor temperature, board output resistance, feed wire carrying the whole board current; solved iteratively | <= 3 % from supply to heater |
| Mains | current from the supply's data-sheet AC current scaled by load, at the lowest declared mains voltage; fuse present, time-lag, >= 1.25 x current and <= inlet rating; mains wire carries the fuse rating and is >= 0.75 mm^2; not bundled with low voltage; PE wire to the supply and to an earth point on a metal frame part, no thinner than the mains wire | as stated |
| Stepper drive | run current against the driver's limit and the motor's rating (per motor, for motors sharing a driver); torque at the design's top speed from supply voltage, winding R and L and back-EMF; resulting drive margin | margin >= the joint's `min_drive_margin` |
| Heaters | lumped thermal simulation (below): reach, heat-up time, closed-loop overshoot / settling / ripple / offset, thermistor resolution, melt capacity | hotend 250 degC in 240 s; bed 60 degC in 600 s, 100 degC in 1500 s; 20 K in hand at 100 % duty; overshoot 10 K (hotend) / 5 K (bed); ripple 2 K; <= 0.5 K per ADC count at target |
| Heater faults | fault injection in the same simulation (below) | detected within 60 s (hotend) / 180 s (bed); peak <= 300 degC (hotend) / 150 degC (bed) |
| Physical | 12 mm keep-out in front of every plugged connector, checked against every part over the sampled poses; fixed loom runs >= 3 mm clear of parts that move relative to them over the whole travel and not through any part; bend radius; a clamp on a real part at both ends of every flexing span; insulation rating within 12 mm of a declared hot part | as stated |
| Thermal effect | bay air temperature from dissipated power with buoyant flow through the declared openings (and wall loss if enclosed, and a fan if declared); supply derating at that temperature; motor case temperature from copper loss over its own surface | bay <= 50 degC; motor case <= 80 degC |
| Artifacts | `wiring.csv`, `wiring.md`, `pin_map.json`, `printer.cfg`, electrical BOM with cost; the config is parsed and checked | no problems |

### One answer for torque at speed

`ratings.resolve_drives` used a torque curve stored on the motor. When a design has an electrical model,
`apply_motor_curves` replaces that curve with the one the phasor model gives for the actual winding, the
configured run current, the supply voltage and how the motors share a driver (the published curve is
kept as `torque_curve_class`). Ratings, motion and the twin all read the same curve, so there is one
answer. The model was checked against StepperOnline's published 24 V pull-out curve for the
17HS13-0404S at 0.35 A rms: within 13 % from 120 to 900 rpm (`tests/test_electrical.py`), so no extra
derating factor is applied.

### Heater simulation

- Bed: two nodes, heater pad and plate. Plate mass and area come from the CAD part (0.783 kg, 0.0484 m^2,
  701 J/K for the 220 x 220 x 6 aluminium plate; the 1 kg payload mass override is excluded). Natural
  convection from the top (hot side up), the underside (hot side down) and the edges by standard
  correlations, radiation with emissivity 0.9 (top sheet and pad) and 0.1 (bare aluminium). Pad to plate
  through an adhesive layer of 1000 W/m^2K (assumed).
- Hotend: two nodes, cartridge and block (12 J/K, from the V6 block's size), natural convection and
  radiation from 16 cm^2 of block, 0.025 W/K up the heat break (assumed).
- Heater power is the wattage at the voltage actually delivered (from the circuit solution).
- Firmware: ports of Klipper's `ControlPID`, `ControlBangBang`, `verify_heater`, the ADC min/max range
  check (4 consecutive reports), sampled as Klipper does (ADC report every 0.3 s, `verify_heater` every 1 s,
  1 s smoothing, PWM averaged over its 0.1 s cycle), with sensor lag and 12-bit ADC quantisation through
  the thermistor and pull-up. PID gains come from Klipper's `PID_CALIBRATE` relay test run on the model.
- Validation: a one-node network against the closed-form RC step response (within 0.5 K), energy
  conservation on two nodes, and Marlin's published MPC example hotend (40 W, 16.7 J/K, 0.068 W/K), for
  which model and closed form both give 86 s to 200 degC, "a minute or two". The 30 W catalog cartridge
  model gives 96 s to 200 degC.

Faults injected for each heater, at its highest target after it has settled: thermistor falls out
(reading decays to ambient with a 15 s time constant, assumed), thermistor shorted, thermistor open,
heater MOSFET shorted (power stays at 100 % whatever the firmware does); plus thermistor out before
heat-up starts. For the MOSFET short the simulation honours independent cut-offs found in the wiring: a
thermal fuse in series with the heater, and a relay ahead of the supply that the firmware drops on
shutdown. It also reports the temperature reached with no cut-off at all.

Limits used for fault peaks: hotend 300 degC (rating of the glass thermistor and typical heater leads;
PTFE begins to decompose above about 260 degC and the block is far below aluminium's melting point);
bed 150 degC (short-term limit of the pad's acrylic adhesive; printed PLA/PETG parts nearby soften at
60-80 degC, which no cut-off prevents and is not a fire limit). These are typical values, unverified, and
are requirements a design can override.

## printer_v4 results

### Off-the-shelf table

Statement from the verifier: *No custom PCB is needed: every electrical element is a purchasable board,
module or component; the builder cuts and terminates wire.* Custom PCBs: **0**.

| Element | Product | Vendor part number | Off the shelf | Custom PCB | What the builder still does |
|---|---|---|---|---|---|
| control_board | BIGTREETECH SKR Mini E3 V3.0 (assembled, 4 x TMC2209 on board) | SKR MINI E3 V3.0 | yes | no | mount on spacers; ferruled wires in the screw terminals; plug JST-XH housings; flash Klipper from SD card |
| psu | MEAN WELL LRS-350-24 | LRS-350-24 | yes | no | set the 115/230 V selector; ring or fork terminals on mains, earth and DC wires |
| inlet | IEC 60320 C14 inlet module with rocker switch and 5x20 mm fuse drawer, 10 A 250 V | commodity, not fixed | yes | no | cut the panel opening; crimp 6.3 mm faston receptacles; fit the T8A fuse |
| psu_relay | BIGTREETECH Relay V1.2 | Relay V1.2 | yes | no | mount on spacers; ferrules on the mains wires; 3-wire JST-XH lead to PS-ON |
| bed_mosfet | heated-bed MOSFET module, 25 A | commodity, not fixed | yes | no | mount on spacers; ferruled wires in the screw terminals |
| host | Raspberry Pi Zero 2 W | Raspberry Pi Zero 2 W | yes | no | fit the 40-pin header; 4-wire lead to the board's TFT header; install Klipper |
| hotend_heater | E3D V6 heater cartridge 24 V 30 W (6 x 20 mm) | E3D, number not fixed | yes | no | clamp in the block; ferrules or butt splices |
| hotend_thermistor | E3D V6 thermistor cartridge (Semitec 104NT-4-R025H42G) | E3D, number not fixed | yes | no | crimp JST-XH at the board end |
| bed_heater + bed_ntc | silicone pad 140 x 200 mm, 24 V 200 W, adhesive, embedded 100k NTC 3950 | commodity, not fixed | yes | no | stick to the plate; ferrules on power leads; JST-XH on the NTC leads |
| bed_tco | axial thermal cut-off, Tf 133 degC, 15 A | commodity, not fixed | yes | no | crimp (never solder) in series with the heater; tape against the plate |
| x_motor, z_motor | STEPPERONLINE NEMA 17 | 17HS13-0404S | yes | no | 4-way JST-XH on the lead |
| y_motor, y_motor_l | STEPPERONLINE NEMA 17 | 17HS19-2004S1 | yes | no | 4-way JST-XH on the lead; swap one coil pair on the mirrored motor |
| extruder | direct-drive extruder with pancake NEMA 17 | commodity, not fixed | yes | no | 4-way JST-XH |
| hotend_fan, part_fan | 24 V axial fan 30 x 30 x 10 mm | commodity, not fixed | yes | no | 2-way JST-XH |
| x/y/z_endstop | mechanical endstop module (microswitch on a small stock PCB) | commodity, not fixed | yes | no | 3-way JST-XH |
| frame_earth | M5 ring terminals under an M5 screw and star washer in a T-nut | hardware | yes | no | crimp ring terminals; break the anodising under the washer |
| wiring | hook-up wire by the metre, JST-XH housings and crimps, ferrules, ring and faston terminals, sleeve, ties | commodity | yes | no | cut each wire to the length in `wiring.csv`, strip, crimp, sleeve and tie |

Fourteen elements are commodity parts with no single vendor part number fixed (the verifier lists them
as an info finding). Their ratings are class values; fix a vendor part before purchase.

### Five motors on four drivers

The stock board has four drivers and the printer has five motors. Chosen solution, stock parts only: the
two Y motors (17HS19-2004S1, 2.0 A, 1.6 ohm, 3.0 mH) are wired in parallel to one driver through the
board's two paralleled "Z" motor connectors (ZAM/ZBM); the Z motor uses the "Y" driver; the pin mapping is
done in the generated config. Electrical consequences, checked by the verifier:

- driver set to 1.20 A rms (limit 1.74 A with the board's 0.11 ohm sense resistors), so 0.60 A per motor
  (rated 2.0 A);
- each motor sees the full 24 V, so the pair holds 354 N*mm from standstill to beyond 900 rpm; at
  250 mm/s (375 rpm) that is 52.8 N at the belt, margin 7.0 (motion verifier) against the required 3;
- in series the pair would see half the voltage each and lose torque sooner; parallel was chosen for that;
- not checked: equal current sharing between two paralleled windings (assumed equal), and that the mirrored
  motor is wired with one coil reversed (written as a note on that wire in `wiring.csv`).

The subsystems verifier's driver count now takes motors that share a driver from the electrical model
(5 motors, 1 sharing, 4 drivers).

### Power budget

| Load (worst case, all at once) | W |
|---|---|
| bed heater (200 W pad at the 23.7 V delivered) | 195.6 |
| hotend heater (30 W at 23.9 V) | 29.7 |
| four drivers with their motors | 17.5 |
| fans, board logic, host, relay | 7.4 |
| wire loss | 2.0 |
| **total** | **252** |

Supply: Mean Well LRS-350-24 (350.4 W), load 72 % against the 85 % limit. LRS-200-24 would be at 119 %.
Mains current 4.9 A at 115 V, 2.5 A at 230 V; T8A fuse in a 10 A inlet; inrush 60 A (data sheet), assumed
ridden through by the time-lag fuse. Board input 2.3 A through its 20 A fuse, because the bed current goes
through the MOSFET module straight from the supply.

### Wires (worst cases)

25 wires, 11 looms, 3 flexing spans. Full table: `out/printer_v4/electrical/wiring.csv`.

| Wire | AWG | Length mm | A | Ampacity there, A | Conductor degC | Drop V |
|---|---|---|---|---|---|---|
| bed heater (module to cut-off, in the bed loom) | 16 silicone | 580 | 8.24 | 13.6 | 40 | 0.136 |
| 24 V to bed module | 14 silicone | 180 | 8.24 | 18.3 | 33 | 0.026 |
| mains N | 18 PVC 105 | 310 | 4.89 | 11.0 | 33 | - |
| hotend heater | 20 silicone | 1260 | 1.24 | 4.6 (10 loaded conductors in the loom) | 28 | 0.108 |
| extruder motor | 24 | 1180 | 0.60 | 2.3 | 28 | 0.123 |

Highest use of ampacity: 61 % (bed heater). Voltage lost on the way to the heaters: bed 1.1 %, hotend
0.6 % (limit 3 %).

### Heaters

| | Hotend (30 W) | Bed (200 W) |
|---|---|---|
| Heat-up from 25 degC, 100 % duty | 133 s to 250 degC | 164 s to 60 degC; 422 s to 100 degC |
| Temperature at 100 % duty left on | 451 degC | 150.5 degC |
| Steady duty | 44 % at 250 degC | 19 % at 60 degC; 50 % at 100 degC |
| PID from simulated PID_CALIBRATE (Kp, Ki, Kd) | 34.1, 3.12, 93.4 | 69.5, 4.83, 250 |
| Closed loop: overshoot, ripple | 1.9 K, 0.33 K | 0.1 K, < 0.01 K |
| Surface against set point | -0.1 K | -1.0 K at 60, -2.5 K at 100 (the NTC is in the pad, the plate is cooler) |
| Thermistor resolution | 0.42 K per count at 250 degC (0.73 at 280) | 0.05 K at 60, 0.03 K at 100 |

Hotend melt capacity at the 60 mm/s infill speed: 2.7 W needed for 5.4 mm^3/s of PLA, 16.6 W spare.

### Fault injection

| Fault | Hotend, holding 250 degC | Bed, holding 100 degC |
|---|---|---|
| Thermistor falls out | `verify_heater` trips after 5.0 s; peak 256 degC | trips after 9.0 s; peak 98 degC |
| Thermistor shorted | ADC range check after 0.9 s; peak 251 degC | 0.9 s; peak 97 degC |
| Thermistor open | 0.9 s; peak 251 degC | 0.9 s; peak 97 degC |
| Thermistor out before heat-up | trips after 21 s; block at 69 degC | trips after 61 s; plate at 39 degC |
| MOSFET shorted, with the cut-offs fitted | passes max_temp after 31.5 s, firmware drops the supply relay; peak 286 degC | after 180 s, relay; peak 116 degC |
| MOSFET shorted, no cut-off | 451 degC, still powered | 150.5 degC, still powered (the 133 degC thermal fuse would open first) |

The bed has a hardware cut-off (thermal fuse on the plate, holding temperature 109 degC against the
100 degC target) and the relay. The hotend has only the relay, which needs the controller to be running:
the verifier keeps this as a warning (`cutoff_depends_on_mcu`). A shorted hotend MOSFET together with a
hung controller is not covered.

### Bay and motors

Open tray under the bed: 41 W dissipated (supply loss 34 W, board 2.8 W, host 3 W, relay 0.5 W, MOSFET
module 0.5 W); bay air about 39 degC against the supply's 50 degC full-load limit; no fan needed. If the
tray were boxed in, declare it `enclosed` and the check is repeated with wall loss only.

Motor case temperature at the set currents: X and Z (0.28 A in a 30 ohm winding, 5.4 W) 61 degC;
extruder 49 degC; Y motors 31 degC.

### What the verifier caught in the first attempts

Reproduce with `MECHLOOP_V4_ATTEMPT=1` or `2`.

| Attempt | Finding | Fix |
|---|---|---|
| 1 (v3's placeholders carried over) | `psu_undersized`: 216 W on the 211 W LRS-200 (102 %) | LRS-350-24 |
| 1 | `wire_overloaded`: AWG 22 PVC bed wire, 6.1 A against 5.1 A, 94 degC | AWG 16 silicone |
| 1 | `wire_not_rated_for_heat`: PVC bed and thermistor wires within 12 mm of the 100 degC plate | silicone |
| 1 | `mains_fuse_too_small`: 4 A fuse, 5 A needed at 115 V | T8A |
| 1 | `runaway_not_detected` x4: with `verify_heater` off, a fallen-out thermistor is never noticed (hotend 375 degC and rising) | `verify_heater` on |
| 1 | `no_independent_cutoff`: hotend settles at 450 degC with a shorted MOSFET | relay ahead of the supply; thermal fuse on the bed |
| 1, 2 | `motor_too_hot`: X and Z at their rated 0.40 A dissipate 11 W, 98 degC case | 0.28 A (torque at 375 rpm is voltage-limited to 100 N*mm either way) |
| 2 (200 W pad for the 100 degC bed) | `output_overloaded`: 8.2 A on the board's bed terminal, limit 80 % of 10 A | stock MOSFET module fed from the supply |
| 3 | `connector_overloaded`, `series_device_overloaded`: 10 A thermal cut-off at 8.2 A | 15 A cut-off |
| 3 | interference: board screws over the bottom rail; inlet nuts in the inlet body | moved the board; corrected the inlet proxy |
| 3 | `cable_clamp_in_air` (subsystems): clamp points 5-6 mm off the parts | moved to within 3 mm |
| 3 | assemblability: 80 errors, the larger tray and the rear boards sat under screws driven from below (beam bolts, extruder screws) and under the hotend's way in | driver holes in the tray, boards moved clear |

Checks I changed because the check was wrong:

- `interference._threads`: a catalog part that states its own tapped depth (the LRS supply: M4, 3 mm) is
  satisfied by a screw that uses that depth; before, 3 mm in a steel case failed the generic 1 x d rule.
- connector keep-out no longer applies to leads moulded or soldered into a part (heater pad, cartridges,
  thermal fuse); it reported the bed plate as blocking the pad's own leads.
- closed-loop metrics measure overshoot and settling against the level the surface finally holds and
  report the sensor-to-surface offset separately; before, a bed whose NTC sits in the pad "never reached"
  100 degC.

### Verify and score

`python -m mechloop verify designs/printer_v4.py --no-render`: all 12 pass; 0 errors, 18 warnings
(10 manufacture, 5 hand-made proxy parts, 2 electrical, 1 assembly).

| | v3 | v4 |
|---|---|---|
| Parts | 225 | 292 |
| Mass | 9.22 kg | 10.02 kg |
| Bill of materials | $515 | $598 (electrical items $270) |
| Resonance X / Y | 67 / 61 Hz | 63 / 53 Hz |
| Cross-track RMS | 0.016 mm | 0.019 mm |
| Highest clean acceleration | 14,000 mm/s^2 | 6,000 mm/s^2 (1.5 x the design value) |
| Drive margins X / Y / Z | not recorded here | 5.5 / 7.0 / 3.6 |
| Assembly time estimate | 45 min | 59 min |
| Benchmark print time | not recorded here | 2564 s; 3055 s with heat-up (164 s per cold start) |

The fall in clean acceleration and resonance is the motors being modelled as what they are: the v3
figures used class torque curves at full holding torque; v4 uses the real windings at the currents their
temperature allows (X at 0.28 A, Y pair at 0.6 A each). v3 was not re-scored with the vendor data, so
the two columns are not like for like.

Generated config: `out/printer_v4/electrical/printer.cfg`. It was parsed with Klipper's configparser
settings and checked for required options, known sensor types, pins that exist on the board and pins
used twice: no problems. **It was not run through klippy**: that needs an MCU dictionary from a firmware
build, which was not done.

## Sources of ratings

| Item | Source |
|---|---|
| LRS-350/200: power, current, efficiency, AC current, inrush, size, mass, base holes (4-M4, 3 mm deep), derating | Mean Well LRS-350 / LRS-200 specification sheets (meanwell.com), also `parts/vendor/meanwell_lrs.json` |
| SKR Mini E3 V3.0: outline, five holes, pins, 20 A and 1.1 A fuses, 0.11 ohm sense resistors, 4.7 k pull-ups, 14.2 mm component height | BIGTREETECH-SKR-mini-E3 repository: SIZE and PIN drawings, schematic, STEP; pins cross-checked with Klipper's `generic-bigtreetech-skr-mini-e3-v3.0.cfg` |
| Connector positions on the board | scaled from the vendor drawings, +/- 1 mm |
| Driver current limit 1.74 A rms (2.0 A firmware cap) | Klipper `tmc2208.py` current scaling with the board's sense resistors |
| TMC2209 RDS(on) 0.17 ohm, 29 V max | recalled from the data sheet; analog.com not reachable: **typical, unverified** |
| Board bed/heater/fan channel limits (10 A / 5 A / 3 A), output resistance, logic power, 5 V rail | not in the V3.0 documents: **typical, unverified** |
| Relay V1.2 size and holes | BIGTREETECH-Relay-V1.2 operating instruction; contact rating **typical, unverified** |
| Motors: rated current, resistance, inductance, holding torque, published pull-out curve | StepperOnline product pages and `parts/vendor/stepperonline_nema17.json` |
| Thermistor R-T points | Klipper `temperature_sensors.cfg` (which cites the makers' tables) |
| Control laws, sampling, autotune | Klipper `heaters.py`, `verify_heater.py`, `pid_calibrate.py`, `adc_temperature.py`, `thermistor.py` |
| Hotend cross-check | Marlin 2.1.x `Configuration.h` MPC example values |
| E3D V6: 30 W cartridge, 300 degC with the supplied thermistor | `parts/vendor/e3d_v6.json` (product page) |
| IEC C14: 10 A 250 V | IEC 60320 standard rating |
| Inlet geometry, MOSFET module, Raspberry Pi drawing, thermal cut-off, bed pad, fans, extruder winding, hotend block capacity, connector ratings (JST-XH 3 A etc.), grouping factors, insulation ratings, wire surface heat transfer, costs | **typical, unverified** (marked so in each device's `sources`) |

## Not modelled, or assumed

- EMC, noise on thermistor and endstop lines, ground loops, stepper cable crosstalk.
- Firmware bugs; the firmware itself is not run (its control laws are ported). klippy has not parsed the config.
- Crimp and solder quality, connector wear, wire fatigue in the flexing looms (only length, bend radius and strain relief).
- The real PID tune, heater tolerance (+/-10 %), supply voltage tolerance and adjustment, mains voltage variation.
- Fuse I^2t against inrush; DC interrupting rating of the thermal cut-off at 24 V; relay contact life.
- Current sharing between the two paralleled Y motors; which way each motor turns.
- Driver junction temperature (only dissipation), mid-band resonance, stall detection.
- The short stubs between a loom end or a connector and the device: their length is counted but their path is not checked for collisions.
- The shape of a flexing loop: only its length, bend radius, clamps and whether the straight line between the clamps passes through a part (a warning; printer_v4 has one, toolhead loom against the heat-sink fan at one corner of the travel).
- Bonding between anodised extrusions is assumed to be made by the brackets and T-nuts; one earth point is checked.
- Thermal model: lumped nodes, no temperature gradient across the plate, no part-cooling airflow on the block, no enclosure, bed convection for a free plate. Sensor detachment time constant, adhesive conductance, heat-break conductance and emissivities are assumed values.
- Bay temperature is a single-zone estimate; the heated bed above the bay is not included.
- Motor temperature ignores the mounting plate (conservative) and the heat from the bed.
- The part-cooling duct, wire ferrules, crimp housings and cable ties are in the BOM but not in the CAD.
