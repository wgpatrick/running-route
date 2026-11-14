# Where every CAD file in this folder came from

Retrieved 2026-11-14. "Vendor-made" means the part's maker published the file. "Community-made" means someone
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

Not files: socket head cap screws and hex nuts are generated to ISO 4762 / ISO 4032 by the `bd_warehouse` package
(Apache-2.0) at run time; nothing is stored.

Licence notes: the FreeCAD-library files are CC-BY 3.0 and must keep this attribution. The Voron file is GPL-3.0:
keep this notice with it, and take it out (and use the wish-list replacement) before distributing this repository
under terms that are not compatible with the GPL. The two vendor files carry no licence grant; they are the makers'
published downloads and are kept here for internal design use.
