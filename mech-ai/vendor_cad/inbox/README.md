# Hand-download wish list

Drop a STEP file into this folder under the exact name given below and the catalogue part picks it up the next
time a design is built: no code change. What happens to it:

1. The file is found by name (case and `.step` / `.stp` do not matter). Any catalogue part also accepts a file
   named after its SKU, e.g. `SHCS-M3x8.step`, `NUT-M3.step`, `MGN12H.step`.
2. Its solids are aligned to the part's local frame automatically (the axis-aligned orientation whose bounding box
   and centre of volume agree best with the model it replaces). If that guess is wrong, put a sidecar next to it,
   `<file>.json`: `{"rot": [rx, ry, rz], "pos": [x, y, z], "kind": "vendor CAD", "source": "where it came from"}`
   (degrees about fixed X, Y, Z, then a translation in mm).
3. It becomes the part's `detail` model (display, STEP export, viewer), marked "vendor CAD" unless the sidecar says
   otherwise, and it must pass the same `proxy_matches_cad` check as every other model in `mechloop verify`. A
   mismatch is reported with the measured values: that is either an alignment problem or a real difference between
   the catalogue and the vendor's part.
4. Then add a line to `vendor_cad/SOURCES.md` and, once checked, move the file up into `vendor_cad/`.

Keep each file under about 5 MB. Part numbers marked "look up" are not known with confidence; use the description.

## Could not be fetched (login, blocked host, or not published)

| part (catalogue call) | vendor part number | where to get it | save as |
|---|---|---|---|
| ~~NEMA 17, 34 mm (`nema17(34)`: X and Z motors)~~ | StepperOnline 17HS13-0404S | **DONE 2026-11-15**: `vendor_cad/17HS13-0404S1.step` (the S1 variant, same motor) is the detail model | |
| NEMA 17, 40 mm (`nema17(40)`) | StepperOnline 17HS16-2004S1 | same | `17HS16-2004S1.step` |
| ~~NEMA 17, 48 mm (`nema17(48)`: both Y motors)~~ | StepperOnline 17HS19-2004S1 | **DONE 2026-11-15**: `vendor_cad/17HS19-2004S1.step` is the detail model | |
| NEMA 17, 60 mm (`nema17(60)`) | StepperOnline 17HS24-2104S | same | `17HS24-2104S.step` |
| ~~Jaw coupling 5 x 8 mm (`shaft_coupler(5, 8)`)~~ | StepperOnline MH2025-5-8 | **DONE 2026-11-15**: `vendor_cad/COUPLER-5x8.step` is the detail model | |
| T8 lead screw and brass nut | StepperOnline LSN-S-MB-320 (lead 8); the design uses lead 2 mm: look up | StepperOnline, or the screw's seller | `T8x2-200.step` (screw, 200 mm), `T8-NUT.step` (nut) |
| MGN12H carriage | Hiwin MGN12H (e.g. MGN12H1R...Z0CM set: look up) | www.hiwin.tw / www.hiwin.com 3D CAD download (refused automated requests) | `MGN12H.step` |
| MGN12 rail, 215 / 250 / 300 mm | Hiwin MGNR12R215CM, MGNR12R250CM, MGNR12R300CM (confirm on the configurator) | same | `MGN12-R-215.step`, `MGN12-R-250.step`, `MGN12-R-300.step` |
| 2020 extrusion, slot 6 | Misumi HFS5-2020-[L] (L = 284, 300, 340, 360 in printer_v4) | us.misumi-ec.com part page, CAD download (proxy refused) | `EXT2020-284.step`, `EXT2020-300.step`, `EXT2020-340.step`, `EXT2020-360.step` |
| 2020 corner bracket | Misumi HBLFSN5 (look up) | us.misumi-ec.com | `BRKT-2020.step` |
| GT2 pulley, 20 teeth, 5 mm bore, 12 mm belt (`gt2_pulley(20, 5, 12)`) | look up (e.g. Gates / Misumi GPA20GT2090-A-P5: look up) | pulley maker | `GT2-20T-B5.step` |
| GT2 idler, 20 teeth, 5 mm bore, 12 mm belt (`gt2_idler(20, 5, 12)`) | look up | idler maker | `GT2-IDLER-20T-B5.step` |
| Endstop module (lever microswitch on a board) | the exact module you will buy; for the switch alone: Omron D2F-L (hinge lever, PCB terminals) | omron.com component 3D download, or the module seller | `ENDSTOP-MICRO.step` |
| 30 mm fan 30 x 30 x 10, 24 V | look up (e.g. Sunon MF30102V1 family: look up) | fan maker | `FAN-3010.step` |
| Direct-drive extruder with pancake motor (`extruder_direct`) | the unit you will buy (e.g. E3D Titan Aero + pancake NEMA 17: look up) | e3d-online.com | `EXTRUDER-DD.step` |
| ~~E3D Roto extruder (`extruder_roto()`)~~ | E3D REVO-ROTO-COLDSIDE-AS | **DONE 2026-11-15**: the owner downloaded "Roto Reference" (printables.com model 655950). It is `vendor_cad/e3d_roto_reference_cad.step`; the cold side cut from it is `vendor_cad/EXTRUDER-E3D-ROTO.step` with its sidecar, and is the part's detail model. Still open: read the licence on the Printables page | - |
| ~~E3D Revo hot side (`hotend_revo()`)~~ | E3D RC-CORE-24V-AS-SPRING + RC-NOZZLE-0400-AS-SPK | **DONE 2026-11-15**: the hot-side solid of the same file is `vendor_cad/HOTEND-REVO-24V-40W.step` with its sidecar. It has no lead sleeve; a HeaterCore model with its leads (e.g. from https://www.printables.com/model/713137-e3d-revo-voron-reference-cad) would still be worth having | optional: `RC-CORE-24V-AS-SPRING.step` |
| Roto part-cooling duct (printed part, E3D's design; not a catalogue part) | - | https://www.printables.com/model/661438-e3d-revo-roto-part-cooling-fan | keep with the design |
| Round nylon spacers (`spacer_round`) | Pololu 1970-1988 | pololu.com has no 3D files for them; plain sleeves, the generated solid is exact | not needed |
| Aluminium spacer 10 OD x M5 (`spacer_round("M5", L, "aluminium")`) | OpenBuilds "Aluminum Spacers": look up the SKU per length | https://openbuildspartstore.com/aluminum-spacers/ (not reachable here): confirm 5.1 mm ID and the length list | `SPACER-AL-M5-10x5.1x6.step` etc. (optional) |
| Silicone bed column 16 x 4 x 18 (`bed_column_silicone`) | the set you will buy (e.g. FYSETC solid bed mounts: look up) | seller; measure OD, bore, free height and note the hardness | `BED-COLUMN-SIL-16x18.step` |
| GT2 pulley and idler for 9 mm belt (`gt2_pulley(20, 5, 9)`, `gt2_idler(20, 5, 9)`) | look up (Gates 2GT 9 mm; e.g. a 20-tooth 5 mm bore pulley and toothed idler sold for 9 mm belt) | pulley maker; gates.com refuses automated requests | `GT2-20T-B5-W9.step`, `GT2-IDLER-20T-B5-W9.step` |
| E3D V6 hotend (`hotend_v6()`; a community model is shown meanwhile) | E3D V6-175-24V | e3d-online.com has no CAD link for the V6; ask E3D support (their GitHub ToolChanger repository holds printed tool parts only) | `HOTEND-V6.step` or `V6-175-24V.step` |
| Raspberry Pi Zero 2 W | Raspberry Pi Zero 2 W | datasheets.raspberrypi.com `rpizero2/raspberry-pi-zero-2-w-step.zip`: look up (host blocked here) | `HOST-RPI-ZERO-2W.step` |
| BIGTREETECH Relay V1.2 | Relay V1.2 | no 3D file in BIGTREETECH's repository; ask BIGTREETECH or measure | `RELAY-BTT-V1.2.step` |
| Heated-bed MOSFET module 25 A | the module you will buy | seller | `MOSFET-BED-25A.step` |
| IEC C14 inlet with switch and fuse drawer, screw flange | e.g. Schurter DD11 / Schaffner FN 9260 family: look up the exact one | maker's site (schurter.com) | `INLET-C14-SW-FUSE-T8A.step` |
| MEAN WELL LRS-200-24 (only if you use the 200 W supply) | LRS-200-24 | https://www.meanwell.com/upload/pdf/LRS-200/LRS-200-3D.zip (it is a RAR archive: unpack by hand) | `LRS-200-24.step` |
| BIGTREETECH SKR Mini E3 V3.0, full model | SKR MINI E3 V3.0 | already fetched; the full 17.7 MB file can replace the reduced one | `BTT E3 SKR MINI V3.0.step` |

## Fasteners (McMaster-Carr was not reachable)

Screws and nuts are generated to ISO 4762 / ISO 4032. To use McMaster models instead, save each under its SKU
name. McMaster numbers below are from memory for alloy steel 12.9 socket head cap screws (91290A...) and zinc-plated
steel hex nuts (90592A...): check each on the page before ordering. "look up" where not known.

| SKU in the printer_v4 BOM | McMaster number | save as |
|---|---|---|
| `NUT-M2.5` x 4: M2.5 hex nut | look up | `NUT-M2.5.step` |
| `NUT-M3` x 24: M3 hex nut | 90592A085 (believed) | `NUT-M3.step` |
| `NUT-M5` x 3: M5 hex nut | 90592A095 (believed) | `NUT-M5.step` |
| `SHCS-M2.5x12` x 4: M2.5 x 12 mm socket head cap screw, class 12.9 | look up | `SHCS-M2.5x12.step` |
| `SHCS-M3x10` x 23: M3 x 10 mm socket head cap screw, class 12.9 | 91290A115 (believed) | `SHCS-M3x10.step` |
| `SHCS-M3x12` x 11: M3 x 12 mm socket head cap screw, class 12.9 | 91290A117 (believed) | `SHCS-M3x12.step` |
| `SHCS-M3x14` x 5: M3 x 14 mm socket head cap screw, class 12.9 | look up | `SHCS-M3x14.step` |
| `SHCS-M3x16` x 4: M3 x 16 mm socket head cap screw, class 12.9 | 91290A120 (believed) | `SHCS-M3x16.step` |
| `SHCS-M3x30` x 5: M3 x 30 mm socket head cap screw, class 12.9 | look up | `SHCS-M3x30.step` |
| `SHCS-M3x6` x 12: M3 x 6 mm socket head cap screw, class 12.9 | 91290A111 (believed) | `SHCS-M3x6.step` |
| `SHCS-M3x8` x 47: M3 x 8 mm socket head cap screw, class 12.9 | 91290A113 (believed) | `SHCS-M3x8.step` |
| `SHCS-M4x6` x 4: M4 x 6 mm socket head cap screw, class 12.9 | look up | `SHCS-M4x6.step` |
| `SHCS-M5x10` x 2: M5 x 10 mm socket head cap screw, class 12.9 | look up | `SHCS-M5x10.step` |
| `SHCS-M5x30` x 1: M5 x 30 mm socket head cap screw, class 12.9 | look up | `SHCS-M5x30.step` |
| `SHCS-M5x35` x 2: M5 x 35 mm socket head cap screw, class 12.9 | look up | `SHCS-M5x35.step` |
| `SHCS-M5x6` x 4: M5 x 6 mm socket head cap screw, class 12.9 | look up | `SHCS-M5x6.step` |
| `SHCS-M5x8` x 65: M5 x 8 mm socket head cap screw, class 12.9 | look up | `SHCS-M5x8.step` |
| `TNUT-2020-M3` x 25: T-nut for 2020 slot 6, M3 (not modelled as geometry; BOM only) | look up | `TNUT-2020-M3.step` |
| `TNUT-2020-M5` x 71: T-nut for 2020 slot 6, M5 (not modelled as geometry; BOM only) | look up | `TNUT-2020-M5.step` |
| `WASHER-M3` x 4: M3 washer (BOM only) | look up | `WASHER-M3.step` |
| `WASHER-M5-STAR` x 1: M5 star washer for the earth point (BOM only) | look up | `WASHER-M5-STAR.step` |

## Documents (not CAD) that would turn recalled values into vendor values

Save PDFs into `vendor_docs/inbox/`; nothing reads them automatically, but each one closes a line of
`docs/VENDOR_DATA.md` ("Still not vendor data").

| what | where | closes |
|---|---|---|
| Roto motor inductance | ask E3D support (the Roto data-sheet page gives resistance, torque and inertia but no inductance), or measure the motor with an LCR meter | `extruder_roto()` uses an 11 mH estimate |
| MIC-6 data sheet | Arconic / Kaiser "MIC-6 precision machined cast aluminum plate" PDF, or https://www.upmet.com/sites/default/files/datasheets/mic-6.pdf | density and modulus of `al_mic6` (recalled) |
| ATP-5 data sheet | Vista Metals ATP-5 technical data sheet (vistametals.com) | every `al_atp5` number (recalled) |
| Gates PowerGrip GT2 / GT3 2 mm design manual | gates.com "Light Power and Precision Drive Design Manual" (PDF) | belt stiffness and working tension per width, minimum pulley teeth, 9 mm belt part numbers |
| OpenBuilds spacer page | https://openbuildspartstore.com/aluminum-spacers/ | SKUs and lengths of the 10 mm aluminium spacers |
