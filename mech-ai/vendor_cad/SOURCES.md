# Where every CAD file in this folder came from

Retrieved 2026-11-14 (three StepperOnline files added 2026-11-15 from `staging/`; the others left in `staging/` are not used by any part). "Vendor-made" means the part's maker published the file. "Community-made" means someone
else drew the part; such a model is never presented as the vendor's. The catalogue code that uses each file, and
the frame it is placed in, is `mechloop/parts/details.py`. See `docs/VENDOR_CAD.md`.

| file | part | origin | commit / retrieved | licence | made by |
|---|---|---|---|---|---|
| `meanwell_LRS-350.stp` | MEAN WELL LRS-350 power supply (`psu_lrs`, `psu_24v(350)`; also shown for the LRS-200, same case) | https://www.meanwell.com/upload/pdf/LRS-350/LRS-350-3D.zip, file `LRS-350(N2).stp` (dated 2024-11-26), unchanged | retrieved 2026-11-14 | MEAN WELL's published 3D file; no licence text in the archive (vendor copyright) | vendor-made |
| `btt_skr_mini_e3_v3.0_reduced.step` | BIGTREETECH SKR Mini E3 V3.0 (`skr_mini_e3_v3`, `control_board`) | https://github.com/bigtreetech/BIGTREETECH-SKR-mini-E3 `hardware/BTT SKR MINI E3 V3.0/3D/BTT E3 SKR MINI V3.0.step` (17.7 MB), REDUCED here: the 41 solids over 40 mm^3 kept of 732 (SMD passives and small ICs dropped), re-exported | commit d7fd822006628143222d1c3c8cdea85ffee29e66 | no licence file in the repository (vendor copyright) | vendor-made, reduced by us |
| `nema17_40mm_with_connector.step` | NEMA 17 stepper (`nema17`; body and shaft brought to each catalogue length in code) | https://github.com/FreeCAD/FreeCAD-library `Electrical Parts/Motors/Stepper/NEMA/Old/NEMA-17_Stepper_Motor_40mm_with_connector.step` | commit f5ca01cdcaa2f69b9295a6382719c2d90628780c | CC-BY 3.0 (FreeCAD-library; authors in that repository's commit history) | community-made |
| `mgn12_rail_100mm.step` | MGN12 rail (`mgn12_rail`; section swept to length) | FreeCAD-library `Mechanical Parts/Bearings/linear_bearings/LinearSlide-MGN12-Rail.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `mgn12h_block.step` | MGN12H carriage (`mgn12h_carriage`) | FreeCAD-library `Mechanical Parts/Bearings/linear_bearings/LinearSlide-MGN12H.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `profile_2020_slot6.step` | 20x20 slot-6 extrusion (`extrusion_2020`; section swept to length) | FreeCAD-library `Mechanical Parts/Profiles EN/Generic/Profile-20x20-B-Type_Slot6_A.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `corner_bracket_2020.step` | 2020 cast corner bracket (`corner_bracket_2020`) | FreeCAD-library `Mechanical Parts/Mountings/Corner/2020_corner_bracket-Corner.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `gt2_20t_idler_5mm_bore.step` | GT2 20-tooth-size idler, 6 mm belt, 5 mm bore (`gt2_idler(20, 5, 6)`; smooth variant, teeth not drawn) | FreeCAD-library `Mechanical Parts/Pulleys/GT2_20T_Smooth_5mm_Bore.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `t8_flange_nut.step` | T8 flanged brass nut (`leadscrew_nut_t8`) | FreeCAD-library `Mechanical Parts/Mountings/T8_screw_nut/Flange_nut/T8_Flange_nut.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `fan_40x40x10.step` | 40 mm axial fan (`fan(40)`) | FreeCAD-library `Electrical Parts/fans/fan-40x40mm.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `voron0_3010_axial_fan.step` | 30 mm axial fan (`fan(30)`) | https://github.com/VoronDesign/Voron-0 `CAD/V0.2R1_Master_Assembly_STEP.zip`, part "3010 DC Axial Fan" extracted from the assembly and re-exported | commit a0d5d1bc91d1b3bc0af6109384d8704f2bf97d10 | GPL-3.0 (Voron-0 repository) | community-made |
| `microswitch_spdt_lever.step` | lever microswitch of the endstop module (`endstop_switch`; the 20 x 12.5 mm board under it is generated) | FreeCAD-library `Electronics Parts/Switch/Limit switch/Microswitch_SPDT_Horizontal_L.step` | commit f5ca01cd | CC-BY 3.0 | community-made |
| `hotend_v6_style.step` | V6-style hotend: heat sink with groove mount, heater block, nozzle (`hotend_v6`; no fan or duct) | FreeCAD-library `Electrical Parts/Hotend/hotend-3d-printer.step`, unchanged (retrieved 2026-11-15) | commit f5ca01cd | CC-BY 3.0 | community-made (not E3D's model) |
| `e3d_roto_reference_cad.step` | E3D Roto extruder with Revo hot side, complete (source file of the two below; not used directly by a part) | E3D "Roto Reference" CAD, https://www.printables.com/model/655950-e3d-roto-reference-cad (linked from E3D's Roto data-sheet page); STEP header `REVO-ROTO-24V-AS-REFERENCE.STEP`, SolidWorks 2022, 2024-01-24; 11 solids; unchanged | hand-downloaded by the owner on 2026-11-15 | CC BY-NC-ND 4.0 (stated on the Printables page; non-commercial, no derivatives: private use only, do not redistribute the cut files) (printables.com was not reachable from this session; E3D's published reference model, vendor copyright) | vendor-made |
| `EXTRUDER-E3D-ROTO.step` | E3D Roto cold side (`extruder_roto`): gearbox cover, heat sink, ring gear, fan, idler lever, motor, four screws | cut from `e3d_roto_reference_cad.step`: 10 of its 11 solids (hot side removed), the motor's four lead wires (0.8 mm rods, 60.5 mm^3) cut off at the lead block, re-exported in the file's own frame; frame change in `EXTRUDER-E3D-ROTO.step.json` | same download, split 2026-11-15 | CC BY-NC-ND 4.0 (stated on the Printables page; non-commercial, no derivatives: private use only, do not redistribute the cut files) (printables.com was not reachable from this session; E3D's published reference model, vendor copyright) | vendor-made, split and trimmed by us |
| `HOTEND-REVO-24V-40W.step` | E3D Revo hot side (`hotend_revo`, 12 V and 24 V): HeaterCore + nozzle as one simplified solid, no lead sleeve | cut from `e3d_roto_reference_cad.step`: its solid `REVO-HOTSIDE-REFERENCE`, geometry unchanged, re-exported; frame change in `HOTEND-REVO-24V-40W.step.json` | same download, split 2026-11-15 | CC BY-NC-ND 4.0 (stated on the Printables page; non-commercial, no derivatives: private use only, do not redistribute the cut files) (printables.com was not reachable from this session; E3D's published reference model, vendor copyright) | vendor-made, split by us |
| `17HS13-0404S1.step` | NEMA 17 stepper, 34 mm (`nema17(34)`; the catalogue part is the 17HS13-0404S, the same motor with 300 mm bare leads instead of a 1 m lead with connector) | STEPPERONLINE product page https://www.omc-stepperonline.com/nema-17-bipolar-1-8deg-26ncm-36-8oz-in-0-4a-12v-42x42x34mm-4-wires-17hs13-0404s1, file `17HS13-0404S1.STEP` (SolidWorks, one solid), unchanged; in code the four lead stubs are cut 5.7 mm from the side face and the file is turned into the part frame | hand-downloaded by the owner (free account), 2026-11-14; integrated 2026-11-15 | not stated on the page (vendor copyright; internal design use) | vendor-made |
| `17HS19-2004S1.step` | NEMA 17 stepper, 48 mm (`nema17(48)`) | STEPPERONLINE product page https://www.omc-stepperonline.com/nema-17-bipolar-59ncm-84oz-in-2a-42x48mm-4-wires-w-1m-cable-connector-17hs19-2004s1, file `17HS19-2004S1.STEP` (one solid), unchanged; lead stubs cut and frame changed in code | hand-downloaded by the owner (free account), 2026-11-14; integrated 2026-11-15 | not stated on the page (vendor copyright; internal design use) | vendor-made |
| `COUPLER-5x8.step` | 5 x 8 mm jaw coupling MH2025-5-8 (`shaft_coupler(5, 8)`): two clamp hubs, elastomer spider, two M3 x 10 clamp screws | STEPPERONLINE product page https://www.omc-stepperonline.com/5mm-8mm-flexible-jaw-coupling-20x25mm-cnc-stepper-motor-shaft-coupler-mh2025-5-8, STEP header `MH2025-5-8.STEP` (SolidWorks 2016, 2023-01-12; five solids), unchanged; re-centred on the part axis and turned 5 mm end down in code | hand-downloaded by the owner (free account), 2026-11-14; integrated 2026-11-15 | not stated on the page (vendor copyright; internal design use) | vendor-made |

## Supplier CAD batch 2026-11-18 (in `inbox/`, under the catalogue SKU)

Collected for the owner from McMaster-Carr's product pages (with a login) and staged in `staging/supplier_2026-11-18/`
with its report (`00-REPORT-supplier-cad-table.md`: part number, description and page per file) and `MANIFEST.md`
(bounding box and check per file). The exact matches were copied unchanged into `inbox/` on 2026-11-19; each is aligned to
its part's frame automatically and passes the same proxy-match check as every other model. They are the detail models
(display, STEP export) of these catalogue parts; the simulation solids are unchanged except the washers' thickness.

| file in `inbox/` | catalogue part | McMaster-Carr | note |
|---|---|---|---|
| `SHCS-M2.5x12.step`, `SHCS-M2.5x16.step` | `shcs("M2.5", L)` | 91290A008, 91290A200 | ISO 4762, black-oxide alloy steel, fully threaded |
| `SHCS-M3x5`, `x6`, `x8`, `x10`, `x12`, `x16`, `x18`, `x20.step` | `shcs("M3", L)` | 91290A110, A111, A400, A115, A500, A120, A121, A123 | fully threaded |
| `SHCS-M3x40`, `x45`, `x50.step` | `shcs("M3", L)` | 91290A136, 91290A079, 91290A137 | partly threaded: 18 mm of thread (the catalogue part's `interfaces["thread_length"]`; practice FST-060 uses it) |
| `SHCS-M5x8`, `x10`, `x12.step` | `shcs("M5", L)` | 91290A222, A224, A228 | fully threaded |
| `SHCS-M5x30`, `x35`, `x70.step` | `shcs("M5", L)` | 91290A194, A195, A201 | fully threaded per McMaster's page (ISO 4762 would thread 22 mm): `interfaces["thread_length"]` = the full length |
| `FHCS-M4x40.step` | `fhcs("M4", 40)` | 91294A204 | DIN 7991 / ISO 10642, fully threaded |
| `WASHER-M2.5`, `-M3`, `-M4`, `-M5.step` | `washer_flat(size)` | 91166A190, A210, A230, A240 | DIN 125 / ISO 7089; 0.6, 0.6, 0.9, 1.1 mm thick, 0.1 mm more than the catalogue had: `hardware.WASHER` changed to these |
| `NUT-M2.5`, `-M3`, `-M4.step` | `hex_nut(size)` | 90591A270, A250, A255 | DIN 934; same height as ISO 4032 at these sizes |
| `NUT-M3-NYLOC.step` | `hex_nut("M3", "iso10511")` | 90576A102 | DIN 985 / ISO 10511, 4.0 mm high; two solids (nut, nylon insert) |
| `NUT-M5-DIN934.step` | `hex_nut("M5", "din934")` | 90591A260 | DIN 934, 4.0 mm high. Staged as `_DEVIATIONS/NUT-M5.step` (it is not the ISO 4032 nut, 4.7 mm); filed here under the SKU of the DIN 934 part, which printer_v10_1 uses |

Not promoted from that batch, deliberately: McMaster's 5 mm-slot extrusion, T-nuts and corner bracket (a different system
from the 2020 6 mm slot; the owner has to choose; their measured dimensions are in
`mechloop/parts/vendor/tslot_2020_hardware.json` as a geometry the T-slot check reports against); `SHCS-M4x6` (90128A208,
zinc-plated, drawing only: its STEP is over 5 MB); the probe, spring, inlet, pulleys and data sheets (next revision).
Not sold by McMaster: `WASHER-M3-LARGE` (9 mm OD) and `WASHER-M4-LARGE` (12 mm OD), which stay stand-ins.
McMaster's files carry no licence grant; they are the supplier's published downloads, kept for internal design use.

Not files: where no supplier file is in `inbox/`, socket head cap screws and hex nuts are generated to ISO 4762 / ISO 4032
by the `bd_warehouse` package (Apache-2.0) at run time; nothing is stored.

Licence notes: the FreeCAD-library files are CC-BY 3.0 and must keep this attribution. The Voron file is GPL-3.0:
keep this notice with it, and take it out (and use the wish-list replacement) before distributing this repository
under terms that are not compatible with the GPL. The MEAN WELL, BIGTREETECH and STEPPERONLINE files carry no licence grant; they are
the makers' published downloads and are kept here for internal design use. The three E3D files come from E3D's
"Roto Reference" model on Printables; the licence shown on that page was NOT read (the host is blocked here): check
it before distributing them, and treat them as internal-use only until then.
