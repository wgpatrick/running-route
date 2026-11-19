# printer_v12 plan (owner decisions, 2026-11-19)

v12 starts from the finished v11. These changes were agreed by the owner and are deferred from v11 because
they change the electronics bay and add the feedback hardware (docs/ROADMAP.md, priority 3).

## Electronics (from the distributor review of 2026-11-19; prices from Digi-Key/Mouser/Newark APIs that day)

| Item | v11 | v12 | Why |
|---|---|---|---|
| Host | Raspberry Pi Zero 2 W | Raspberry Pi 5 8 GB (SC1432, $175, in stock; 4 GB SC1431 is enough if back in stock) + Active Cooler SC1148 + official 27 W USB-C PSU SC1153; Hailo AI HAT+ (SC1785) later | Cameras (two CSI + USB 3), local failure detection, PCIe for an AI board. Official PSU keeps the host on when the printer's mains is cut. |
| Mains switching | BIGTREETECH Relay V1.2 | Finder 22.32.0.120.4320 DIN-rail contactor (22.32.0.230.4340 for 230 V), coil switched by Phoenix PLC-RSC-5DC/21 (1119897) via an NPN driver (PN2222A) from a Pi GPIO; Moonraker `[power]` with `off_when_shutdown: True`, `locked_while_printing: True` | Listed, touch-safe, rated for the PSU's inrush; any Klipper shutdown (incl. thermal runaway) cuts mains. |
| Inlet | Schurter DD11 (order number not pinned, no fuse drawer) | DD11.0114.1111 + 2-pole drawer 4301.1401 + Schurter SPT ceramic 5x20: 0001.2513 T8A (120 V) / 0001.2511 T5A (230 V); confirm lamp voltage of 0114 vs 0113 | The DD11 ships without its drawer; ceramic fuses for breaking capacity; fuses L and N. |
| Bed switching | external bed MOSFET module | none: bed driven from the Octopus HB output; Littelfuse 0297010.WXNV 10 A blade fuse in the board's bed fuse slot | Board FET (IPD036N04L) dissipates about 0.2 W at 7.5 A; one less failure point. Confirm BTT's HB rating. |
| Bed thermal cut-off | unspecified 133 °C 15 A TCO | Cantherm CS712025Y, 120 °C NC bimetal, 10 A at 24 V DC, clamped to the bed plate | Only distributor TCO found with a stated 24 V DC rating. Auto-resets; the contactor gives the latching shutdown. |
| Bed thermistor | generic 100k 3950 | Semitec 104NT-4-R025H42G | Klipper has its exact table. |
| Endstops | "D2F-01L type" | genuine Omron D2F-01L | Genuine part, $1.44. |
| Bed wiring | JST-XH (rated ~3 A) | Molex Mini-Fit Jr housing 39-01-2020 + Mini-Fit Plus HCS 16 AWG sockets 0457503111 (mating plug to pin); igus CF880-15-02 high-flex for the moving run; igus CF130-03-02 for flexing signal runs | 7.5 A bed current. |
| Other connectors | generic | JST XHP-n / SXH-001T-P0.6 / B*B-XH-A; Molex Micro-Fit 43025-0200 / 43030-0001 / 43031-0001 / 43020-0200 (hotend heater); Phoenix ferrules 3200519 / 3200014; TE FASTON 187 2-520182-2 | Genuine part numbers with supplier CAD. |
| Safety extras | missing | green/yellow 18 AWG earth from inlet to PSU, frame and bed plate (ring lug + star washer on its own stud); cover over the inlet rear and PSU terminals; cord grips where cables cross the frame; Klipper `verify_heater` and `max_temp` left at defaults | Earth bonding, touch safety, strain relief. |
| Kept | | Octopus V1.1, Mean Well LRS-350-24 (label the 115/230 V selector; UHP-350-24 optional), E3D Revo + Roto, 30 mm hotend fan, StepperOnline motors, Omron E2B-M12KS04 probe + BAT85, Delta BFB0524HH blower | |

Estimated change: about +$70 plus the Pi (about +$250 with the 8 GB Pi 5, cooler and PSU).

## Feedback hardware (ROADMAP priority 3, phase 1, plus phase-2 mounts)

Overview camera mount and lighting strip; fixed top-down camera mount with a printed calibration target on
the bed corner; nozzle-camera bracket on the blower duct, outside the heater plume; ADXL345 accelerometer
mount on the toolhead; filament motion sensor on the filament path; Pi 5 placement, camera cable routing and
strain relief. All checked like every other part (clearances, heat, cable routing, assembly).

## Supplier-rule findings to fix (from the v10_1 check against SendCutSend)

- Holes in `x_belt_bracket` and `y_endstop_mount` sit 5.87 / 5.93 mm from the bend centre against SendCutSend's
  6.0 mm half-die limit: move them out (if v11 has not already).
- PEM nuts drawn as `S-M3-1` (not in SendCutSend's catalogue): use `S-M3-0` where the sheet thickness allows.
- Review the hole-to-edge warnings against the reference-part results once the supplier uploads come back.
