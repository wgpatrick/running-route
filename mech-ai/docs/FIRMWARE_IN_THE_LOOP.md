# Firmware in the loop

`mechloop print <printer.py> <part> --firmware klipper` has the real firmware plan the print. The simulated
motors, belts and frame are then driven by the firmware's own step commands.

## What Klipper is

Klipper is open-source 3D-printer firmware. It runs in two halves: a host program (Python, normally on a
Raspberry Pi) that reads G-code, plans the motion and works out when every motor step should happen, and a small
program on the control board that fires those steps at the commanded times. The printer_v4 electronics use it
(SKR Mini E3 V3.0 board, Pi Zero 2 W host).

The host has an offline mode: given the printer's configuration, a G-code file and the board's command
dictionary, it writes the exact command stream it would send to the board. That is what is used here.

## What happens in a run

1. The printer.cfg generated from the design is given to Klipper unchanged, plus one line that lets the run state
   the starting position without homing. It now carries `[input_shaper]`, `pressure_advance`, `[probe]`,
   `[safe_z_home]` and `[bed_mesh]` (see "Input shaping, pressure advance, probe and bed mesh" below).
2. Klipper reads the sliced G-code and produces the command stream for the STM32G0B1 on the board.
3. The stream is decoded into the time of every step on X, Y, Z and the extruder.
4. Those step times become the commanded motion in the twin, in place of the twin's own planner. The stepper,
   belt and frame model, the deposition and the comparison with the intended part run as before. The extruder's
   steps drive the twin's melt-flow model, and the Z steps carry whatever bed-mesh adjustment Klipper applied.
5. When input shaping or pressure advance is on, Klipper is run a second time with both off. That run is the
   planned motion: it is what is checked against the G-code path, and what "sideways from the path" is measured
   from. The two runs are lined up on their Z steps, which neither feature touches.

| Real | Simulated | Not covered |
|---|---|---|
| Klipper's config checks, G-code handling, travel and extrusion limits, look-ahead, acceleration planning, kinematics, input shaping, pressure advance, bed-mesh compensation and step timing (commit `29d4ec2`); its shaper selection, mesh interpolation, PID, bang-bang, `verify_heater` and PID autotune classes, called directly | Motor torque and step loss, belt stretch, frame flex, melt-flow lag, material laid down, the heater's thermal network, the bed's shape, the probe's reading | The board's own C code and its timing, serial delays, driver set-up over UART, homing and probing against a real switch (the offline mode has no micro-controller to answer), `BED_MESH_CALIBRATE` itself |

## What it found

- **The print never homed.** Klipper refused every move in the twin's G-code with "Must home axis first". The
  twin's own planner had never needed homing. A real print needs `G28` in its start G-code.
- **The G-code origin was wrong for the configuration.** The slicer output is centred on the bed; the generated
  configuration counts X and Y from the end of travel. Klipper rejected the moves as out of range. The run applies
  a 90 mm offset; a real slicer profile must put the origin at the bed corner, or the configuration must be changed.
- **A 67-second trap in reading the stream.** The board's clock counter wraps every 67 s, so a Z step after a
  longer pause looks earlier than it is. The decoder first placed each Z move in a pause of X and Y. That stopped
  working with a bed mesh (Z steps during X/Y moves) and with input shaping (a shaped X/Y move runs a few
  milliseconds past its planned end, into the Z move). It now uses the order of the stream: Klipper writes commands
  in the order of the clock they are wanted at, so a lone Z step cannot be earlier than the start of an X or Y
  command already written. It still refuses to report a result if the planned motion is more than 0.1 mm from the
  G-code path, or cannot be followed to the end of the G-code.

## Results on printer_v4

20 mm cube, 0.2 mm layers:

| | Klipper | Twin's own planner |
|---|---|---|
| Print time | 907 s | 875 s |
| Path error, RMS | 0.012 mm | 0.018 mm |
| Path error, worst | 0.12 mm | 0.18 mm |
| Outline match | 99.1% | 99.2% |

Klipper is 4% slower and gentler in corners than the twin's planner, so the twin's own figures have been slightly
pessimistic on path error and optimistic on time. Peak step rate was 19,753 steps/s against about 263,000 the
board manages (Klipper's published benchmark for this processor with three motors stepping).

## Input shaping, pressure advance, probe and bed mesh (added 2026-11-15)

Everything in this section is simulated. Each figure rests on assumed values, named with it.

### Where the settings come from

| Setting | How it is found | Real Klipper code | Assumed |
|---|---|---|---|
| `[input_shaper]` type and frequency per axis | The twin's axis model, linearised (stepper spring, belt and frame spring, two masses), gives a frequency response per axis as a resonance test would record it. Klipper's `shaper_calibrate.find_best_shaper` picks from it, exactly as it does from accelerometer data. | the selection; the shaping itself, in the step stream | stepper damping ratio 0.25, belt/frame damping ratio 0.05, belt stiffness; FEA frame stiffness |
| `pressure_advance` | A sweep on the twin (`mechloop tune`): the test cube printed once per K by Klipper, corner bulge and recess read off each result. Without a sweep, K = the twin's melt-flow lag. | pressure advance in the extruder's steps | the melt-flow lag: first order, 30 ms, one value for every flow rate. Not measured. |
| `[probe]` offsets, `[safe_z_home]`, `[bed_mesh]` bounds | The CAD: sensing face against nozzle tip and bed plate; the plate inset by the probe's edge margin and cut to X/Y travel | config validation; mesh interpolation and the Z adjustment in the step stream | switching distance and its +/-10 % spread (recalled class values), repeatability 0.01 mm, edge margin |
| the mesh itself | klippy's offline mode cannot run a probe sequence (nothing answers the probe), so `BED_MESH_CALIBRATE` is not run. The twin probes its own as-built bed point by point (median of 3 samples with the probe's scatter) and hands Klipper the result as the stored `[bed_mesh default]` profile a real machine would have saved; the job loads it with `BED_MESH_PROFILE LOAD=default`. | loading the profile, interpolating it, adjusting Z | the bed's shape (tilt and bow given as input) |
| heater PID gains, runaway check | Klipper's `ControlAutoTune`, `ControlPID`, `ControlBangBang` and `verify_heater.HeaterCheck` classes run against the lumped thermal model | all four | the thermal constants of the model (see `docs/ELECTRICAL.md`) |

`mechloop/twin/klippy_code.py` loads Klipper's Python modules unmodified and gives them small stand-ins for the
objects they talk to. `mechloop/twin/tuning.py` does the tuning; `mechloop tune <printer.py>` runs all of it and
writes `out/<name>/tune/tuning.json`.

### Results on printer_v5

All with real Klipper planning the motion, FEA frame stiffness from the last verify, 20 x 20 x 4 mm cube.

| At the design's own settings (4000 mm/s^2) | Shaper and pressure advance off | As configured |
|---|---|---|
| Input shaper | none | X: EI 108.4 Hz (predicted resonance 85.9 Hz); Y: MZV 60.6 Hz (60.2 Hz) |
| Pressure advance | 0 | 0.04 s (sweep; 0.03 s lag assumed) |
| Sideways error from the planned path, RMS | 0.0066 mm | 0.0039 mm |
| Sideways error, worst | 0.081 mm | 0.037 mm |
| of which the shaper's own smoothing of the command, worst | 0 | 0.053 mm |
| Corner bulge | 0.40 mm | 0.15 mm |
| Print time | 297.6 s | 297.6 s |

| Acceleration sweep at 2x speed | Shaper and pressure advance off | As configured |
|---|---|---|
| Highest clean acceleration | 12,000 mm/s^2 | 48,000 mm/s^2, the highest tried: no failure found |
| First failure | 16,000: layer shift, outline defect | none up to 48,000 |
| Sideways error at 12,000, RMS / worst | 0.026 / 0.26 mm | 0.005 / 0.06 mm |
| Sideways error at 48,000, RMS / worst | 2.7 / 10.7 mm (lost steps) | 0.008 / 0.16 mm |

Read the second column of the sweep with care. Shaping spreads every change of speed over about one period of
the resonance, so above roughly 10,000 mm/s^2 the toolhead never sees the acceleration that was asked for: the
print is clean because it is being rounded. Klipper's own advice from the same calculation is to keep
`max_accel` at or below 10,700 mm/s^2 (Y) and 21,400 (X) to limit that smoothing. The built-in planner's
figure for the same machine is 10,000 mm/s^2 (score of 2026-11-14); it has no shaper and plans corners
differently, so it is recorded under its own name and not compared.

Residual vibration, measured directly (`ringing_test`: fourteen moves per axis of 5 to 40 mm at 40 to 150 mm/s,
each followed by a stop; largest excursion after the command has stopped):

| | X, no shaper | X, shaped | Y, no shaper | Y, shaped |
|---|---|---|---|---|
| 4000 mm/s^2 | 0.012 mm | 0.014 mm | 0.042 mm | 0.013 mm |
| 12,000 mm/s^2 | 0.067 mm | 0.015 mm | 0.155 mm | 0.013 mm |

About 0.013 mm of every shaped figure is not ringing: it is the axis relaxing from its friction lag (assumed
rail friction over the belt stiffness) when it stops, which no shaper removes. At the design's own acceleration
the X axis gains nothing from shaping in this model.

Pressure-advance sweep (shaper on):

| K, s | 0 | 0.01 | 0.02 | 0.03 | 0.04 | 0.05 | 0.06 |
|---|---|---|---|---|---|---|---|
| Corner bulge, mm | 0.30 | 0.25 | 0.25 | 0.20 | 0.15 | 0.10 | 0.05 |
| Corner recess, mm | 0.15 | 0.20 | 0.20 | 0.20 | 0.15 | 0.20 | 0.35 |

K equal to the lag does not remove the bulge completely, although for a pure first-order lag it would
(`tests/test_twin.py`): Klipper smooths the advance over 40 ms (`pressure_advance_smooth_time`), longer than a
corner's braking takes, so part of the lag gets through. Without any lag the same print shows 0.05 mm. The
sweep picks 0.04. This says how the method behaves; it does not say what K a real extruder needs. printer_v5
has a Bowden extruder, for which K on real machines is commonly some ten times larger (recalled, not measured):
the twin's 30 ms lag is very likely too short for this design.

Bed mesh. Assumed bed: 0.30 mm tilt across X, 0.20 mm across Y, centre 0.15 mm above the corners; Z referenced
with the probe over the middle. 5 x 5 mesh probed by the twin (range 0.33 mm).

| First-layer gap error (commanded 0.20 mm) | Without mesh | With mesh |
|---|---|---|
| 70 x 70 mm patch printed 45 mm off centre in X and Y: RMS | 0.073 mm | 0.007 mm |
| same patch: worst | 0.103 mm | 0.015 mm |
| whole printable area (mesh as Klipper interpolates it, against the bed): RMS | 0.097 mm | 0.023 mm |
| whole printable area: worst | 0.305 mm | 0.088 mm |

The 0.088 mm that remains is in the 33 mm strip at low X that the probe cannot reach (it sits 33 mm to the right
of the nozzle): Klipper holds the nearest measured value there.

Heaters: with Klipper's own classes in the loop the gains and behaviour are the same as with the port, to the
last digit (hotend Kp 31.7, Ki 2.90, Kd 86.8; 250 degC in 133 s, 1.9 K overshoot; bed 60 degC in 162 s, 0.06 K
overshoot; every injected fault trips at the same second).

### What the new checks found in printer_v5

- **The probe switches too late.** Its face is 3.1 mm above the nozzle and its switching distance on aluminium
  is taken as 3.2 mm, so it switches with the nozzle 0.10 mm above the bed. With the +/-10 % spread such sensors
  are allowed, a short-range unit switches only at -0.22 mm: the nozzle is on the bed first. The firmware's
  `z_offset` cannot fix that. (`subsystems: probe_trigger_margin`, an error.)
- **No Z travel beyond the nozzle.** The Z joint ends with the nozzle 0.10 mm above the bed, so the bed cannot
  come up far enough to switch a short-range probe, and a bed mesh has only 0.10 mm in hand to lift a low part
  of the bed (`subsystems: probe_not_reached`, an error; `position_min` comes out as 0).
- A 33 mm strip of the print area is never probed (warning).
- The probe is NPN on 24 V and it is not known whether it has an internal pull-up; if it has, the board pin sees
  24 V (warning; fit a diode). It is rated 70 degC and works a few mm above a bed at up to 100 degC (warning).

printer_v5 therefore no longer passes `subsystems`. The geometry was not changed.

### Scoring with firmware

`mechloop score <printer.py> --firmware klipper` adds a `klipper` block to the scorecard: the nominal print and
the acceleration sweep planned by Klipper, once as configured and once with shaper and pressure advance off.
The top-level `max_clean_accel_mm_s2`, `cross_track_*` and `benchmark_time_s` remain the built-in planner's and
the row says so (`planner`). `--firmware-only` skips the built-in sweep and benchmark; their keys are then
`None`. If Klipper is not installed the block says `ran: false` and the command exits 1.

`cross_track_*` is now measured from the planned path (the G-code as planned, before shaping) and no longer from
the commanded one. For the built-in planner and for Klipper without a shaper the two are the same thing, so old
figures are unchanged (printer_v5, built-in: 0.0114 / 0.1133 mm before and after).

### Limits

- The shaper is tuned on the same model it is then tested on, so the test cannot show a mistuned shaper. A real
  machine's resonance will differ from the prediction; the comparison shows what shaping is worth if the
  prediction is right.
- One resonance per axis, the same everywhere in the travel; no cross-coupling between axes; damping assumed.
- Melt flow is a first-order lag with an assumed constant; no nozzle pressure, no compliance of a Bowden tube.
- The bed's shape is an input. The tolerance verifier's as-built figure for printer_v5 is 2.1 mm out of level
  at the 99th percentile before any levelling; what is left after levelling with the four screws is not
  modelled, so the mesh study uses a stated, assumed surface.
- The probe's reading is the bed height under it plus Gaussian scatter. No temperature drift, no change of
  switching distance near the plate edge or over the heater's screws.
- Homing and probing moves are not run through Klipper: its offline mode ends a homing move without a trigger.

## Set-up

`tools/setup_klipper.sh` fetches Klipper at the pinned commit, builds the board dictionary and makes a Python
environment for it under `third_party/` (not committed). It needs `gcc-arm-none-eabi`. Nothing is flashed.
Without Klipper, a `--firmware klipper` print is an error, not a pass; so is a firmware score or a `mechloop tune`.
The electrical verifier says in its metrics which heater control code ran and whether klippy loaded the generated
configuration; when Klipper is missing both are stated as not run.
