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
   the starting position without homing.
2. Klipper reads the sliced G-code and produces the command stream for the STM32G0B1 on the board.
3. The stream is decoded into the time of every step on X, Y, Z and the extruder.
4. Those step times become the commanded motion in the twin, in place of the twin's own planner. The stepper,
   belt and frame model, the deposition and the comparison with the intended part run as before.

| Real | Simulated | Not covered |
|---|---|---|
| Klipper's config checks, G-code handling, travel and extrusion limits, look-ahead, acceleration planning, kinematics and step timing (commit `29d4ec2`) | Motor torque and step loss, belt stretch, frame flex, material laid down | The board's own C code and its timing, serial delays, driver set-up over UART, closed-loop heater control (the offline mode has no temperature feedback), homing against a real switch |

Heater control and thermal-runaway protection are still simulated with control laws ported from Klipper's source,
not with Klipper's code running.

## What it found

- **The print never homed.** Klipper refused every move in the twin's G-code with "Must home axis first". The
  twin's own planner had never needed homing. A real print needs `G28` in its start G-code.
- **The G-code origin was wrong for the configuration.** The slicer output is centred on the bed; the generated
  configuration counts X and Y from the end of travel. Klipper rejected the moves as out of range. The run applies
  a 90 mm offset; a real slicer profile must put the origin at the bed corner, or the configuration must be changed.
- **A 67-second trap in reading the stream.** The board's clock counter wraps every 67 s, so a Z move after a
  longer pause looks earlier than it is. The decoder places each Z move in a pause of X and Y, and refuses to
  report a result if the decoded motion is more than 0.1 mm from the G-code path.

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

## Set-up

`tools/setup_klipper.sh` fetches Klipper at the pinned commit, builds the board dictionary and makes a Python
environment for it under `third_party/` (not committed). It needs `gcc-arm-none-eabi`. Nothing is flashed.
Without Klipper, a `--firmware klipper` print is an error, not a pass.
