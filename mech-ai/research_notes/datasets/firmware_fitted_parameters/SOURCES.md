# Heater and resonance parameters that printer makers and users fitted and committed to firmware

Fetched 2026-11-15 from `raw.githubusercontent.com`.

| Sub-directory | Source URL | Licence | Content |
|---|---|---|---|
| `prusa_thermal_model/` | https://github.com/prusa3d/Prusa-Firmware/tree/HEAD/Firmware/thermal_model | GPL-3.0 (LICENSE copied) | Prusa MK3-family hotend model constants for E3D V6, Revo and Revo HF 60 W: heater power, block heat capacity (12.1 J/K for V6), block-to-ambient resistance at 16 fan speeds (20.5 down to 10.1 K/W), sensor lag (2.1 s) and filter factor. |
| `prusa_buddy_input_shaper/` | https://github.com/prusa3d/Prusa-Firmware-Buddy/blob/HEAD/lib/Marlin/Marlin/src/feature/input_shaper/input_shaper_config.hpp | GPL-3.0 (repository licence; no LICENSE file at the root path tried) | Factory default input-shaper frequencies per printer: MK4 50.7 / 40.6 Hz, MINI 118.2 / 32.8, XL 35.8 / 35.4, Core One 60 / 48, Core One L 56 / 42, iX 53 / 42; damping ratio 0.1 for all. |
| `kalico_mpc_doc/` | https://github.com/KalicoCrew/kalico/blob/HEAD/docs/MPC.md | GPL-3.0 (COPYING copied) | Documentation of the model-predictive heater control: model structure, calibration procedure, example calibrated constants and a table of filament density and heat capacity. |
| `derived/klipper_config_pid.csv` | every `config/*.cfg` in https://github.com/Klipper3d/klipper that contains `pid_Kp` (216 files) | GPL-3.0 | 350 heater PID sets (226 extruders, 123 beds) with the relay-test quantities recovered from them: Klipper stores Kp = 0.6 Ku x 255, Ki = Kp / (Tu/2), Kd = Kp Tu / 8, so Tu = 2 Kp / Ki and Ku = Kp / 153. The Kd check column is 1.000 for almost every row, which confirms the values came from `PID_CALIBRATE`. |
| `derived/marlin_config_pid_mpc.csv` | 425 `Configuration.h` files in https://github.com/MarlinFirmware/Configurations (default branch) | GPL-3.0 | Default hotend and bed PID constants per machine, and the model-predictive-control constants (heater power, block heat capacity, sensor responsiveness, ambient transfer coefficient with fan off and on). Only 6 configurations enable MPC and 8 distinct MPC sets exist; many PID sets are copies of the Marlin default (22.2 / 1.08 / 114). |

The Klipper and Marlin configuration files themselves were read in a scratch directory and are not stored; the CSVs name each source file.
