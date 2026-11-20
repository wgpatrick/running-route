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

Camera choice (owner, 2026-11-20): Raspberry Pi Camera Module 3 (SC1223) for both the overview and the top-down camera;
the HQ Camera (SC1220) is out of stock at Digi-Key with a 26-week factory lead, which alone set the critical path.

## Wiring decisions from commodity pinning (2026-11-20; docs/COMMODITY_PARTS.md)

- Earth to frame: 16 AWG green/yellow (LAPP 4160400, per foot, in stock) instead of 13 AWG (not a stocked gauge; 14 AWG only
  as a 100 ft minimum with no stock). 16 AWG is heavier than the 18 AWG supply conductors, as required.
- Inlet PE: one conductor per 4.8 mm tab — take PE from the inlet to the frame earth stud, and bond the PSU FG and the bed
  plate from that stud (ring lugs with star washers), instead of two conductors on one tab.
- Flexing runs (X motor, left-Y motor, toolhead loom, bed): igus chainflex (CF130 signal, CF880 power) per this plan, not
  UL1007/1569 hook-up wire.
- Merge the duplicate THREADLOCKER-MEDIUM BOM line (one bottle: Henkel 1329837, Loctite 243 10 ml).
- Braided sleeve: the distributors list only a 200 ft spool (Techflex PTN0.25BK200, ~$44); look for a short length from a
  US seller with the maker's datasheet before ordering.

## Height sensing (owner, 2026-11-20; docs/HEIGHT_SENSING.md)

- Bed probe: BTT Eddy Duo (eddy current, mainline Klipper [probe_eddy_current], coil thermistor) replaces the Omron E2B;
  new printed mount 2-3 mm above the nozzle tip with clearance to aluminium; re-run the probe temperature check against its
  60 °C rating.
- Line laser for camera triangulation: Quarton VLM-520-56 LPO-D30-F10 (520 nm, 30° fan, Class 1M). Owner accepts Class 1M
  with controls: off by default, switched on only by the measurement macro for a few seconds, maker's warning label on the
  toolhead, insulating printed clamp (case may be live). Mount beside the hotend, out of the heater plume and cooling jet.

## Inlet correction (2026-11-20)

DD11.0114.1111 is the 1-pole fuseholder variant (Schurter DD11 datasheet p.5), but the plan pairs it with the 2-pole drawer
4301.1401 and two fuses (L and N). Keep 2-pole fusing (non-polarised plugs) and change the module to DD11.0124.1111 (2-pole,
same options) — confirm the part number, stock and STEP. The Schurter SPT STEP files delivered are the wire-lead (pigtail)
variant; model the 5x20 cartridge from the SPT datasheet (dia 5.2 caps, 20 mm long, caps 5.1 mm) as a faithful re-make.
