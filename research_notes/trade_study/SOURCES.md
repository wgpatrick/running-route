# Sources for the printer trade study

Retrieved 2026-11-14. Repositories were cloned shallow and sparse into a scratch directory
(not into this repository); the files were parsed as data only and nothing from them was executed.

## Repositories

| Machine | Repository | Commit (date) | Licence | Files opened |
|---|---|---|---|---|
| Voron 0.2r1 | https://github.com/VoronDesign/Voron-0 | `a0d5d1bc91d1` (2026-11-08) | GPL-3.0 | `CAD/V0.2R1_Master_Assembly_STEP.zip` -> `V0.2R1 Master Assembly v63.step` (179 MB, 1,683 solids); `Firmware/bigtreetech-skr-mini-e3-v3.0.cfg`; `README.md`; file listing of `STLs/` |
| Voron Trident (250) | https://github.com/VoronDesign/Voron-Trident | `7fcb3257a306` (2026-10-21) | GPL-3.0 | `CAD/trident_assembly.step.zip` -> `trident_assembly.step` (185 MB, 1,414 solids); `Firmware/Octopus/Trident_Octopus_Config.cfg`; file listing |
| Voron 2.4r2 (250) | https://github.com/VoronDesign/Voron-2 | `7b32e405f071` (2026-10-21) | GPL-3.0 | `CAD/Voron_2.4r2_Assembly_STEP.zip` -> `Voron_2.4r2_Assembly.step` (242 MB, 1,428 solids); `firmware/klipper_configurations/Octopus/Voron2_Octopus_Config.cfg`; file listing |
| Annex K3 (Gasherbrum) R1.1 | https://github.com/Annex-Engineering/Gasherbrum-K3 | `1a470008b8f9` (2026-05-04) | ANNEX Engineering License Agreement (linked from `LICENSE.md`; not an OSI licence, text not fetched) | `Release_1_1/CAD/K3 - R1.1 - 2022-11-24 - STEP.rar` -> `K3 - R1.1 - 2022-11-24.STEP` (403 MB, 1,789 solids, 16 min to load); `Release_1_1/DXFs/Bottom_Panel_*.DXF`, `Side_Panel_*.DXF`; `Release_1_1/PDFs/*` (bed and heater drawings); `README.md` |
| Creality Ender 3 | https://github.com/Creality3DPrinting/Ender-3 | `88c7758cea9d` (2019-12-11) | GPL-3.0 | `Ender-3 Mechanical/STP/01 MAIN ASM Ender_3.STEP` (45 MB, 300 solids) |
| Prusa MINI / MINI+ | https://github.com/prusa3d/Original-Prusa-MINI | `853bc30c4b10` (2021-02-14) | GPL-3.0 | `STEP/MECHANICAL PARTS/*.stp` (7), `STEP/PRINTED PARTS/*.stp` (28); `BOM/*.md`; drawings `DOCUMENTATION/MECHANICAL PARTS/mini-{x,y,z}-rod.pdf`, `mini-{y,z}-extrusion.pdf`, `mini-y-carriage.pdf` |
| Prusa i3 MK3S+ | https://github.com/prusa3d/Original-Prusa-i3 (branch `MK3S`) | `529e5ad6892c` (2022-11-14) | GPL-2.0 | `Printed-Parts/STL/*.stl` (45); `Frame/MK3v8b.dxf`, `Frame/Extrusions.pdf`. There is no assembly CAD, and no rods, bed or motors in the repository. |
| Rat Rig V-Core 3.1 | https://github.com/Rat-Rig/V-Core-3 | `4f5d91f42c9a` (2023-07-25) | CC BY-NC-SA 4.0 | `cad/printed_parts/step/core/*.step` (27); `docs/src/bom/vcore31_bom.csv`, `printed_parts_*.csv`; `docs/src/electronics.md`. No assembly CAD in the repository. |
| Rat Rig V-Minion | https://github.com/Rat-Rig/V-Minion | `6811558082d6` (2023-04-20) | CC BY-NC-SA 4.0 | `cad/printed_parts/machine/step/*.step` (31); `docs/src/bom/vminion_20042023_1212.csv`. No assembly CAD in the repository. |

## Configuration files and documents (fetched)

| What | URL |
|---|---|
| Klipper example configs (Ender 3, Prusa MINI+, V-Minion) | https://raw.githubusercontent.com/Klipper3d/klipper/master/config/printer-creality-ender3-2018.cfg, `printer-prusa-mini-plus-2020.cfg`, `printer-ratrig-v-minion-2021.cfg` (repository head `29d4ec2d6d84`) |
| Prusa MK3S firmware limits | https://raw.githubusercontent.com/prusa3d/Prusa-Firmware/MK3/Firmware/variants/MK3S.h |
| RatOS V-Core 3 defaults | https://raw.githubusercontent.com/Rat-OS/RatOS-configuration/v2.1.x/printers/v-core-3/v-core-3.cfg |
| Voron printer overview (costs, "the bed is also cantilevered, which restricts scaling further") | https://docs.vorondesign.com/hardware.html |
| Measured Voron resonances and stock limits | `research_notes/Voron reference data for twin validation.md` (compiled 2026-11-13) |

## Our design

`mech-ai/designs/printer_v4.py` (docstring and constants), `mech-ai/viewer/data.json`, `mech-ai/docs/*.md`,
`mech-ai/mechloop/twin/__init__.py` (belt stiffness assumption), `mech-ai/mechloop/parts/vendor/*.json`.

## Not obtained

- Rat Rig V-Core 4, Prusa MK4, Prusa XL, Ender 3 V2: no public repository reachable under the names tried.
- Bambu Lab X1 / P1 and Prusa CORE One: no open CAD opened; the two lines about them in the report are
  recalled published specifications, marked as such.
- Voron BOM spreadsheets (the configurator at vorondesign.com) and the Annex K3 sourcing guide (Google Sheets):
  hosts not reachable. Fastener and part counts for those machines are counted from the STEP assemblies instead.
- Vendor rigidity tables for miniature linear guides (Hiwin): not reachable; block stiffness in `estimates.py`
  is an assumed class value and is shown with a band.

## Scripts in this folder

| Script | Purpose |
|---|---|
| `extract_step.py` | Walk a STEP assembly (OpenCASCADE XCAF) and write one record per part instance: name path, world bounding box, volume, centre of mass |
| `asm.py` | Shared selectors, fastener recogniser, material classes and assumed densities |
| `measure_assemblies.py` | Per-machine part selectors; frame, rails, bed, Z drives, belts, toolhead, masses, counts |
| `measure_parts.py` | Bounding box and volume of single-part STEP / STL files |
| `bom_counts.py` | Fastener / rail / belt counts from the Rat Rig CSV and Prusa Markdown BOMs |
| `build_measurements.py` | Merge everything into `measurements.json`, each value tagged with method and source |
| `estimates.py` | Closed-form beam / plate / belt estimates; writes `estimates.json` |
| `draw_side_views.py` | Same-scale side views from the measured bounding boxes |
| `draw_plan_views.py` | Same-scale plan views of bed plate, Z guides and Z drives |
| `step_product_tree.py` | Part names and instance counts from a STEP file's product structure, read as text (used for the K3 alongside the geometry) |
| `explore.py` | Helper used while finding part names |

## How to reproduce

```
PY=mech-ai/.venv/bin/python ; T=research_notes/trade_study ; S=<scratch dir holding the clones>
$PY -I $T/extract_step.py <assembly.step> $S/out/<machine>.json 8     # voron0, trident, voron24, k3, ender3
$PY -I $T/measure_parts.py $S/out/prusa_mini_parts.json <Original-Prusa-MINI>/STEP   # likewise prusa_mk3s_parts, vcore3_parts, vminion_parts
$PY -I $T/bom_counts.py $S $S/out/bom_counts.json
grep -E "^#[0-9]+ *= *(PRODUCT|PRODUCT_DEFINITION|PRODUCT_DEFINITION_FORMATION[A-Z_]*|NEXT_ASSEMBLY_USAGE_OCCURRENCE) *\(" <K3.STEP> > $S/out/k3_structure.txt
$PY -I $T/step_product_tree.py $S/out/k3_structure.txt $S/out/k3_tree.json
cd $T
$PY measure_assemblies.py $S/out $S/out/asm_measure.json
$PY build_measurements.py $S/out ../../mech-ai/viewer/data.json measurements.json
$PY estimates.py measurements.json estimates.json
$PY draw_side_views.py $S/out ../../mech-ai/viewer/data.json ../../reports/img/trade_study/side_views_same_scale.png
$PY draw_plan_views.py measurements.json ../../reports/img/trade_study/plan_views_bed_support.png
```

The K3 fastener figure of 767 in `build_measurements.py` is the count printed by a one-off query of `k3_tree.json`
(names matching screws, washers, nuts and heat-set inserts) and is entered there as a constant.
