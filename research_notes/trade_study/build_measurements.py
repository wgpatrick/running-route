"""Assemble research_notes/trade_study/measurements.json: every number with its method and source.

Usage: python build_measurements.py <scratch out dir> <mech-ai/viewer/data.json> <measurements.json>

Methods used in the output:
  cad        measured from STEP/STL/DXF geometry opened with OCP / trimesh / ezdxf
  cad-est    CAD volume x an assumed density, or a length solved from a CAD solid
  bom        read from a BOM / drawing / README in the cloned repository
  config     read from a published firmware configuration file
  docs       read from docs.vorondesign.com (fetched)
  recalled   a published specification recalled from memory; could NOT be re-fetched from this network
  ours       from mech-ai/viewer/data.json (the mechloop verifiers and twin)
"""
import csv, json, os, sys

o, ours_json, dst = sys.argv[1:4]
A = json.load(open(os.path.join(o, "asm_measure.json")))
B = json.load(open(os.path.join(o, "bom_counts.json")))
parts = {k: json.load(open(os.path.join(o, k + ".json"))) for k in
         ("prusa_mini_parts", "prusa_mk3s_parts", "vcore3_parts", "vminion_parts") if os.path.exists(os.path.join(o, k + ".json"))}
D = json.load(open(ours_json))
STEP = {"voron0": "VoronDesign/Voron-0: CAD/V0.2R1_Master_Assembly_STEP.zip -> 'V0.2R1 Master Assembly v63.step'",
        "trident": "VoronDesign/Voron-Trident: CAD/trident_assembly.step.zip -> trident_assembly.step",
        "voron24": "VoronDesign/Voron-2: CAD/Voron_2.4r2_Assembly_STEP.zip -> Voron_2.4r2_Assembly.step",
        "ender3": "Creality3DPrinting/Ender-3: 'Ender-3 Mechanical/STP/01 MAIN ASM Ender_3.STEP'",
        "k3": "Annex-Engineering/Gasherbrum-K3: 'Release_1_1/CAD/K3 - R1.1 - 2022-11-24 - STEP.rar' -> 'K3 - R1.1 - 2022-11-24.STEP'"}
M = {}


def v(value, method, source, note=None):
    d = dict(value=value, method=method, source=source)
    if note:
        d["note"] = note
    return d


for key, m in A.items():
    e = {}
    for k, val in m.items():
        if k in ("label", "source_json", "method"):
            continue
        meth = "cad-est" if k.endswith("_mass_kg") or k == "belts" or k == "printed_volume_cm3" else "cad"
        e[k] = v(val, meth, STEP[key])
    e["label"] = m["label"]
    M[key] = e

# ---------------- published configuration / documents ---------------------------------------------
VCFG = "VoronDesign/Voron-0: Firmware/bigtreetech-skr-mini-e3-v3.0.cfg"
M["voron0"].update(
    build_volume_mm=v([120, 120, 120], "config", VCFG + " (position_max) and README.md"),
    stock_max_accel_mm_s2=v(2000, "config", VCFG), stock_max_velocity_mm_s=v(200, "config", VCFG),
    z_screw=v("T8x8 integrated lead screw, rotation_distance 8", "config", VCFG),
    bed_heater=v("24 V DC silicone pad 100 x 100 mm, 60 W (config comment: 'max_power 0.6 only needed for 100w pads')", "config+recalled", VCFG),
    cost_usd=v("400 - 600", "docs", "https://docs.vorondesign.com/hardware.html"),
    scaling_remark=v("'The bed is also cantilevered, which restricts scaling further.'", "docs", "https://docs.vorondesign.com/hardware.html"),
    printed_stl_files=v(134, "bom", "VoronDesign/Voron-0 repository listing (*.stl)"),
    board=v("BTT SKR Mini E3 V3 (one of the stock configs; the CAD shows an SKR Pico), TMC2209, Mean Well LRS-150-24", "config+cad", VCFG))
TCFG = "VoronDesign/Voron-Trident: Firmware/Octopus/Trident_Octopus_Config.cfg"
M["trident"].update(
    build_volume_mm=v([250, 250, 250], "config", TCFG + " (position_max 250) ; CAD is the 250 size"),
    stock_max_accel_mm_s2=v(3000, "config", TCFG + " (comment: Max 4000)"), stock_max_velocity_mm_s=v(300, "config", TCFG),
    z_tilt=v("[z_tilt] with three independent Z steppers", "config", TCFG),
    bed_heater=v("mains silicone pad through an SSR; heater_bed max_power 0.6", "config", TCFG),
    cost_usd=v("1000 - 1300", "docs", "https://docs.vorondesign.com/hardware.html"),
    printed_stl_files=v(145, "bom", "VoronDesign/Voron-Trident repository listing (*.stl)"),
    board=v("BTT Octopus (8 drivers), TMC2209, 24 V LRS-200 + mains bed via SSR (SSR and LRS-200-24 are in the CAD)", "config+cad", TCFG))
V2CFG = "VoronDesign/Voron-2: firmware/klipper_configurations/Octopus/Voron2_Octopus_Config.cfg"
M["voron24"].update(
    build_volume_mm=v([250, 250, 230], "config+recalled", V2CFG + " ; Z height of the 250 build recalled"),
    stock_max_accel_mm_s2=v(3000, "config", V2CFG + " (comment: Max 4000)"), stock_max_velocity_mm_s=v(300, "config", V2CFG),
    z_reduction=v("gear_ratio 80:16 on each of 4 Z steppers; [quad_gantry_level]", "config", V2CFG),
    bed_heater=v("mains silicone pad through an SSR (config comment names an Omron G3NA SSR)", "config", V2CFG),
    cost_usd=v("1500 - 1900", "docs", "https://docs.vorondesign.com/hardware.html"),
    printed_stl_files=v(155, "bom", "VoronDesign/Voron-2 repository listing (*.stl)"),
    measured_resonance_hz=v({"x": "54 - 62", "y": "39 - 50"}, "docs", "research_notes/Voron reference data for twin validation.md section 5 (350 mm machines, user configs)"),
    board=v("BTT Octopus, 7 drivers used (A, B, 4 x Z, E)", "config", V2CFG))
ECFG = "Klipper3d/klipper: config/printer-creality-ender3-2018.cfg"
M["ender3"].update(
    build_volume_mm=v([220, 220, 250], "config+recalled", ECFG + " (position_max 235/235/250; printable 220 x 220)"),
    stock_max_accel_mm_s2=v(3000, "config", ECFG + " (Klipper example; Creality's own Marlin default is 500)"),
    stock_max_velocity_mm_s=v(300, "config", ECFG),
    z_screw=v("T8x8, rotation_distance 8, max_z_velocity 5", "config", ECFG),
    bed_heater=v("24 V DC, PCB-on-aluminium bed 235 x 235 x 3 mm; ~220 W", "cad+recalled", STEP["ender3"]),
    cost_usd=v("~170 - 200 retail (complete machine)", "recalled", "street price, not re-checked"),
    board=v("Creality 1.1.x 8-bit board, 4 x A4988, Mean Well style 24 V 15 A supply (the supply is in the CAD: '24V15A power supply')", "cad+recalled", STEP["ender3"]))

MINI = "prusa3d/Original-Prusa-MINI"
pm = parts.get("prusa_mini_parts", {})
def psz(d, name):
    for k, x in d.items():
        if k.endswith(name):
            return x
M["prusa_mini"] = dict(
    label="Prusa MINI+",
    architecture=v("cantilevered X arm on one Z column; bed slides in Y", "bom", MINI + ": BOM/*.md"),
    build_volume_mm=v([180, 180, 180], "config", "Klipper3d/klipper: config/printer-prusa-mini-plus-2020.cfg (position_max 180.4/180/185)"),
    y_carriage_plate_mm=v(psz(pm, "MINI-y-carriage.stp")["size"], "cad", MINI + ": STEP/MECHANICAL PARTS/MINI-y-carriage.stp"),
    steel_sheet_mm=v(psz(pm, "MINI-steel-sheet.stp")["size"], "cad", MINI + ": STEP/MECHANICAL PARTS/MINI-steel-sheet.stp"),
    rods=v({"X": "2 x 8 mm x 279", "Y": "2 x 8 mm x 279", "Z": "2 x 10 mm x 341"}, "bom", MINI + ": DOCUMENTATION/MECHANICAL PARTS/mini-[xyz]-rod.pdf"),
    extrusions=v({"Y": "2 x 262 mm (30 mm wide custom profile)", "Z": "1 x 289 mm"}, "bom", MINI + ": DOCUMENTATION/MECHANICAL PARTS/mini-[yz]-extrusion.pdf"),
    bearings=v({"X": "2 x LM8UU (plus 2 x LM10LUU listed in the X-axis BOM, which ride the Z rods)", "Y": "3 x LM8UU"}, "bom", MINI + ": BOM/X-AXIS.md, Y-AXIS.md"),
    belts=v({"X": "GT2 6 mm, 561 mm", "Y": "GT2 6 mm, 496 mm", "pulley": "GT2-16"}, "bom", MINI + ": BOM/X-AXIS.md, Y-AXIS.md"),
    z_drives=v(1, "bom", MINI + ": BOM/Z-AXIS.md"),
    printed_parts=v(B["prusa_mini"]["printed"], "bom", MINI + ": BOM/*.md"),
    printed_parts_volume_cm3=v(round(sum(x["vol_cm3"] for k, x in pm.items() if "PRINTED PARTS" in k)), "cad", MINI + ": STEP/PRINTED PARTS/*.stp (28 files)"),
    fasteners=v(B["prusa_mini"]["fasteners"], "bom", MINI + ": BOM/*.md"),
    fastener_types=v(B["prusa_mini"]["fastener_types"], "bom", MINI + ": BOM/*.md"),
    stock_max_accel_mm_s2=v(1250, "config", "Klipper3d/klipper: config/printer-prusa-mini-plus-2020.cfg"),
    stock_max_velocity_mm_s=v(180, "config", "same"),
    motor_current_a=v(0.35, "config", "same (run_current, X/Y/Z)"),
    bed_heater=v("24 V DC PCB heatbed (prusa3d/Heatbed-Mini-PCB)", "bom", MINI + ": BOM/Y-AXIS.md"),
    board=v("Prusa Buddy board, TMC2209, 24 V external brick", "bom+recalled", MINI + ": README.md"))

I3 = "prusa3d/Original-Prusa-i3 (branch MK3S)"
pk = parts.get("prusa_mk3s_parts", {})
M["prusa_mk3s"] = dict(
    label="Prusa i3 MK3S+",
    architecture=v("bed slides in Y; X beam (two rods) lifts in Z on two lead screws; X motor rides on the Z-moving X end", "cad", I3 + ": Printed-Parts/STL/x-end-motor.stl, z-axis-bottom.stl"),
    build_volume_mm=v([250, 210, 210], "config", "prusa3d/Prusa-Firmware: Firmware/variants/MK3S.h (X_MAX_POS 255, Y_MAX_POS 212.5, Z_MAX_POS 210)"),
    frame_plate_outline_mm=v([370.0, 370.3], "cad", I3 + ": Frame/MK3v8b.dxf (layer 0, ezdxf extents)"),
    frame_extrusions=v("3030: 2 x 205 mm + 2 x 120 mm, M5 tapped ends (blind joints into the plates)", "bom", I3 + ": Frame/Extrusions.pdf"),
    printed_part_files=v(len(pk), "cad", I3 + ": Printed-Parts/STL/*.stl"),
    printed_parts_volume_cm3=v(round(sum(x.get("vol_cm3", 0) for x in pk.values())), "cad", I3 + ": Printed-Parts/STL/*.stl (trimesh)"),
    z_drives=v(2, "recalled", "two Z motors with integrated lead screws (the two z-axis-bottom / z-axis-top printed mounts are in the STL set)"),
    guides=v("8 mm rods and LM8UU bearings on all axes", "recalled", "Prusa assembly manual; rods are not in the repository"),
    steps_per_mm=v([100, 100, 400], "config", "MK3S.h DEFAULT_AXIS_STEPS_PER_UNIT -> GT2 16-tooth pulleys, Tr8x8 screws at 16 microsteps"),
    stock_max_accel_mm_s2=v({"default print": 1250, "max normal mode": 2500, "max per axis default": 1000}, "config", "MK3S.h DEFAULT_ACCELERATION, NORMAL_MAX_ACCEL_XY, DEFAULT_MAX_ACCELERATION"),
    stock_max_velocity_mm_s=v(200, "config", "MK3S.h NORMAL_MAX_FEEDRATE_XY"),
    bed_heater=v("24 V DC PCB heatbed with magnets (MK52)", "recalled", "Prusa product documentation"),
    board=v("Einsy Rambo, TMC2130, 24 V 240 W supply", "recalled", "Prusa product documentation"))

VC = "Rat-Rig/V-Core-3"
b = B["ratrig_vcore31_200"]
vp = parts.get("vcore3_parts", {})
core_q = sum(int(r[2]) for r in csv.reader(open(os.path.join(o, "..", "Rat-Rig_V-Core-3/repo/docs/src/bom/printed_parts_core.csv"))) if len(r) > 2 and r[2].isdigit())
eva_q = sum(int(r[2]) for r in csv.reader(open(os.path.join(o, "..", "Rat-Rig_V-Core-3/repo/docs/src/bom/printed_parts_eva3_0_2.csv"))) if len(r) > 2 and r[2].isdigit())
M["ratrig_vcore31_200"] = dict(
    label="Rat Rig V-Core 3.1 (200 mm)",
    architecture=v("CoreXY; bed moves in Z on three lead screws with a ball-and-pin kinematic mount", "bom", VC + ": docs/src/bom/vcore31_bom.csv"),
    build_volume_mm=v([200, 200, 200], "bom", VC + ": kit name 'V-Core 3.1 - 200mm'"),
    frame_extrusions=v(b["extrusions"], "bom", VC + ": docs/src/bom/vcore31_bom.csv (3030 T-slot, 18 pieces; 2020 V-slot X beam 322 mm)"),
    frame_joints=v("20 joining plates + 12 cast corner brackets, M6 into drop-in T-nuts (176 x M6x12, 195 x M6 T-nuts)", "bom", VC + ": vcore31_bom.csv"),
    rails=v(b["rails"], "bom", VC + ": vcore31_bom.csv (6 x MGN12 with MGN12C carriages: 4 x 300, 2 x 250)"),
    lead_screws=v(b["lead_screws"], "bom", VC + ": vcore31_bom.csv (3 x TR8x4, 280 mm)"),
    kinematic_mount=v("3 x steel ball 12 mm (M5), 6 x dowel pin 3 x 35 mm, 3 x magnet 20 x 10 x 5, 3 x 'bi-material lead screw decoupler', 3 x thrust bearing F8-16M", "bom", VC + ": vcore31_bom.csv"),
    bed_plate_mm=v([229, 229, 5], "bom", VC + ": vcore31_bom.csv ('Bed Plate - Cast tooling plate - Pre-Machined - 229*229*5mm')"),
    belts=v("GT2 9 mm, 5.8 m supplied for both loops (all sizes); 20T 9 mm pulleys", "bom", VC + ": vcore31_bom.csv"),
    bed_arm_printed_mm=v({k.split("/")[-1]: x["size"] for k, x in vp.items() if "bed_arm" in k}, "cad", VC + ": cad/printed_parts/step/core/bed_arm_*.step"),
    printed_parts=v({"core": core_q, "toolhead (EVA 3)": eva_q}, "bom", VC + ": docs/src/bom/printed_parts_core.csv, printed_parts_eva3_0_2.csv"),
    printed_core_volume_cm3=v(round(sum(x["vol_cm3"] for x in vp.values())), "cad", VC + ": cad/printed_parts/step/core/*.step (27 files)"),
    machined_or_sheet_parts=v(b["plates"], "bom", VC + ": vcore31_bom.csv (laser-cut / machined plates)"),
    fasteners=v(b["fasteners"], "bom", VC + ": vcore31_bom.csv, 200 mm mechanical kit incl. T-nuts, washers, shims"),
    fastener_types=v(b["fastener_types"], "bom", VC + ": vcore31_bom.csv"),
    stock_max_accel_mm_s2=v(1500, "config", "Rat-OS/RatOS-configuration v2.1.x: printers/v-core-3/v-core-3.cfg ('only safeguards for first time users')"),
    stock_max_velocity_mm_s=v(300, "config", "same"),
    bed_heater=v("mains silicone pad through an SSR (config sets pwm_cycle_time for '50hz european AC')", "config", "Rat-OS/RatOS-configuration v2.1.x: printers/v-core-3/v-core-3.cfg"),
    board=v("BTT Octopus v1.1 preferred (6 drivers needed: A, B, 3 x Z, E)", "bom", VC + ": docs/src/electronics.md"))

VM = "Rat-Rig/V-Minion"
b = B["ratrig_vminion"]
M["ratrig_vminion"] = dict(
    label="Rat Rig V-Minion",
    architecture=v("cantilevered X arm on one Z column (3060 extrusion); bed slides in Y on two MGN15 rails", "bom", VM + ": docs/src/bom/vminion_20042023_1212.csv"),
    build_volume_mm=v([180, 180, 180], "config", "Klipper3d/klipper: config/printer-ratrig-v-minion-2021.cfg (position_max 180)"),
    frame_extrusions=v(b["extrusions"], "bom", VM + ": vminion BOM (3060: 345, 270, 115 mm; 3030: 120 mm; 2020 X beam 362 mm)"),
    rails=v(b["rails"], "bom", VM + ": vminion BOM (X: 1 x MGN12 250; Y or Z: 2 x MGN15 250 with MGN15H)"),
    lead_screws=v(b["lead_screws"], "bom", VM + ": vminion BOM (1 x TR8x4 250 mm, anti-backlash nut block)"),
    belts=v(b["belts"], "bom", VM + ": vminion BOM (6 mm x 650 mm and 9 mm x 700 mm)"),
    bed_plate=v("5 mm cast tooling plate + 4 mm sub-plate", "bom", VM + ": vminion BOM"),
    fasteners=v(b["fasteners"], "bom", VM + ": vminion BOM mechanical kit"),
    fastener_types=v(b["fastener_types"], "bom", VM + ": vminion BOM"),
    printed_part_step_files=v(len(parts.get("vminion_parts", {})), "cad", VM + ": cad/printed_parts/machine/step/*.step"),
    printed_parts_volume_cm3=v(round(sum(x.get("vol_cm3", 0) for x in parts.get("vminion_parts", {}).values())), "cad", VM + ": cad/printed_parts/machine/step/*.step"),
    stock_max_accel_mm_s2=v(20000, "config", "Klipper3d/klipper: config/printer-ratrig-v-minion-2021.cfg"),
    stock_max_velocity_mm_s=v(500, "config", "same"),
    motor_current_a=v(0.8, "config", "same"))

for key, lab, txt in (
    ("bambu_x1_p1", "Bambu Lab X1 / P1 (no open CAD)", dict(
        architecture="CoreXY; bed moves in Z on three lead screws turned by ONE motor through a belt (not independently levelled); fixed-height gantry on carbon or steel rods",
        build_volume_mm=[256, 256, 256], published_max_accel_mm_s2=20000, published_max_speed_mm_s=500)),
    ("prusa_core_one", "Prusa CORE One (no open CAD opened here)", dict(
        architecture="CoreXY in a steel sheet exoskeleton; bed moves in Z", build_volume_mm=[250, 220, 270]))):
    M[key] = dict(label=lab, **{k: v(x, "recalled", "manufacturer's published specification, recalled from memory; vendor sites are not reachable from this network and no CAD was opened") for k, x in txt.items()})

K3 = "Annex-Engineering/Gasherbrum-K3"
tree = os.path.join(o, "k3_tree.json")
if os.path.exists(tree):
    T = json.load(open(tree))
    C = T["counts"]
    import re
    def cnt(rx):
        return sum(n for k, n in C.items() if re.search(rx, k, re.I))
    ST = STEP["k3"] + " (product structure read at text level with step_product_tree.py: names and instance counts, no geometry)"
    k3 = M.setdefault("k3", {})
    k3.update(
        label="Annex K3 (Gasherbrum) R1.1",
        architecture=v("cross gantry (X and Y beams cross at the toolhead), 4 XY motors on the frame (2 per axis); bed moves in Z on three belts with a three-point Maxwell kinematic mount", "bom+cad-structure", K3 + ": README.md; " + ST),
        build_volume_mm=v([180, 180, 180], "bom", K3 + ": README.md ('Build Volume of ~180^3 mm')"),
        frame_footprint_from_panel_dxf_mm=v([320.0, 320.0], "cad", K3 + ": Release_1_1/DXFs/Bottom_Panel_180mm_x_180mm_x1_Rev1.DXF (ezdxf extents)"),
        side_panel_mm=v([320.0, 483.0], "cad", K3 + ": Release_1_1/DXFs/Side_Panel_180mm_x_180mm_x2_Rev2.DXF"),
        frame_members=v({"Frame Horizontal": cnt(r"^Frame Horizontal"), "Frame Corner": cnt(r"^Frame Corner"), "section": "2020 (README)"}, "cad-structure", ST),
        bed_plate_drawing_mm=v([180, 180, 6.35], "bom", K3 + ": Release_1_1/PDFs/ANNEX_Engineering_K3_180mm_x_180mm_Bed_Drawing.PDF (MIC6/ATP5, three mounting points)"),
        bed_heater=v("mains silicone pad 170 x 170 mm, 110/220 V, 'ideal wattage 300 W', through a 30 A SSR (the SSR is in the CAD)", "bom+cad-structure", K3 + ": Release_1_1/PDFs/ANNEX_Engineering_Custom_Silicone_Heaters_180mm_x_180mm.pdf"),
        rail_counts=v({"MGN9 gantry rails": cnt(r"^MGN9 Gantry Rail"), "MGN9 cross rails": cnt(r"^MGN9 Cross Rail"), "MGN9 Z rails": cnt(r"^MGN9 Z Rail"), "MGN9C carriages": cnt(r"^MGN9CZFC")}, "cad-structure", ST),
        nema17_motors=v(cnt(r"^Nema17 Stepper Motor"), "cad-structure", ST + " ; README: 2 per X, 2 per Y, plus 3 Z"),
        z_drive_evidence=v(3, "cad-structure", ST + " ('Frame Bed Front/Rear [3 Point]', 3 x 'Maxwell, 8mm Rod', 3 Z belts, 'Z Drive, Closed Loop 200mm Belt' x 3, 'Pulley, 80t')"),
        belt_counts=v({"X": cnt(r"^X-Belt"), "Y": cnt(r"^Y-Belt"), "Z": cnt(r"^Z-Belt"), "width": "9 mm on XYZ (README)", "belt tensioners": cnt(r"^Belt Tensioner")}, "cad-structure+bom", ST),
        part_instances=v(T["leaf_instances"], "cad-structure", ST), unique_parts=v(T["unique_leaf_parts"], "cad-structure", ST),
        fasteners_incl_inserts_and_washers=v(767, "cad-structure", ST + " ; names matched as screws, washers, nuts, heat-set inserts (incl. McMaster part numbers); approximate"),
        belts_in_parallel=v(2, "cad", STEP["k3"] + " (two X belts and two Y belts, one at each end of the cross rail)"),
        printed_stl_files=v(492, "bom", K3 + " repository listing (*.stl, all options and releases)"),
        board=v("Fysetc Spider (8 drivers; 7 motors + extruder), 30 A SSR, 24 V standard / 48 V optional", "cad-structure+bom", ST + "; README.md"),
        probe=v("dockable microswitch probe ('QuickDraw V2', 'Probe_holder_d2f')", "cad-structure", ST),
        stock_max_accel_mm_s2=v(None, "not obtained", "no stock configuration file was reachable"))

# ---------------- ours ---------------------------------------------------------------------------
sc, bd, man = D["score"], D["build"]["metrics"], D["manufacture"]
P = {p["name"]: p for p in D["parts"]}
src = "mech-ai/viewer/data.json"
kinds = {}
for p in D["parts"]:
    k = p["process"] if p["kind"] == "fabricated" else p["kind"]
    kinds[k] = kinds.get(k, 0) + 1
bedb, railb, lsb = P["bed"]["bbox"], P["z_rail_left"]["bbox"], P["leadscrew"]["bbox"]
bed_c = (bedb[1] + bedb[4]) / 2
rail_y = (railb[1] + railb[4]) / 2
M["ours"] = dict(
    label="Ours: printer_v4",
    architecture=v("cartesian: toolhead on X beam, X beam on two Y rails (X motor rides the beam, two Y motors on one driver); bed cantilevered, moves in Z on two rails and one lead screw", "ours", "mech-ai/designs/printer_v4.py docstring"),
    build_volume_mm=v([180, 180, 150], "ours", "mech-ai/designs/printer_v4.py PRINT_X/Y/Z"),
    frame_outer_mm=v(dict(x=340, y=360, z=324), "ours", "printer_v4.py FX, FY, FZ + 10"),
    envelope_mm=v(D["bbox"], "ours", src + " bbox"),
    parts=v(bd["parts"], "ours", src), part_kinds=v(kinds, "ours", src + " parts[].kind/process"),
    custom_parts=v(man["by_process"], "ours", src + " manufacture"),
    machining_cost_estimate_usd_qty1=v(man["machining_cost_estimate_usd_qty1"], "ours", src + " manufacture"),
    machining_setups_total=v(man["machining_setups_total"], "ours", src),
    fasteners=v(bd["fasteners"], "ours", src), fastener_types=v(bd["fastener_types"], "ours", src),
    assembly_time_min=v(bd["estimated_time_min"], "ours", src),
    total_mass_kg=v(sc["total_mass_kg"], "ours", src), bom_cost_usd=v(sc["bom_cost_usd"], "ours", src),
    moving_mass_kg=v(sc["moving_mass_kg"], "ours", src), resonance_hz=v(sc["resonance_hz"], "ours", src),
    nozzle_stiffness_n_per_mm=v(sc["frame_stiffness_n_per_mm"], "ours", src),
    max_clean_accel_mm_s2=v(sc["max_clean_accel_mm_s2"], "ours", src + " (twin, no input shaping)"),
    design_accel_mm_s2=v(4000, "ours", "printer_v4.py A_XY"), design_speed_mm_s=v(250, "ours", "printer_v4.py V_XY"),
    belts=v(D["printing"]["belts_per_axis"], "ours", src + " printing.belts_per_axis (12 mm GT2; X 674 mm, Y 676 and 738 mm)"),
    bed_plate_mm=v([bedb[3] - bedb[0], bedb[4] - bedb[1], bedb[5] - bedb[2]], "ours", src + " parts[bed].bbox"),
    bed_mass_kg=v(P["bed"]["mass"], "ours", src), carrier_mass_kg=v(P["carrier"]["mass"], "ours", src),
    carrier_bbox_mm=v([round(P["carrier"]["bbox"][i + 3] - P["carrier"]["bbox"][i]) for i in range(3)], "ours", src),
    z_rail_spacing_mm=v(180.0, "ours", "printer_v4.py UP_X = 90"),
    z_carriages=v(sum(1 for n in P if n in ("z_carriage_left", "z_carriage_right")), "ours", src + " (one MGN12H per Z rail)"),
    bed_centre_to_z_rail_plane_mm=v(round(rail_y - bed_c, 1), "ours", src + " bboxes of bed and z_rail_left"),
    bed_front_edge_to_z_rail_plane_mm=v(round(rail_y - bedb[1], 1), "ours", src),
    leadscrew_behind_bed_centre_mm=v(round((lsb[1] + lsb[4]) / 2 - bed_c, 1), "ours", src),
    carrier_fea_edge_deflection_mm_at_3kg=v(D["fea"]["payload_x3_on_bed"]["max_deflection_mm"], "ours", src + " fea.payload_x3_on_bed (carrier alone, clamped at the carriages)"),
    bed_heater=v("24 V DC silicone pad 140 x 200 mm, 200 W, external MOSFET, 133 C thermal cut-off", "ours", "mech-ai/docs/ELECTRICAL.md"),
    board=v("BTT SKR Mini E3 V3 (4 x TMC2209 for 5 motors), Raspberry Pi Zero 2 W, Mean Well LRS-350-24", "ours", "mech-ai/docs/ELECTRICAL.md"),
    nozzle_to_x_rail_mm=v(dict(horizontal=32.5, below=51.0), "ours", "printer_v4.py HOT_OFF; Z of x_rail centre minus Z_NOZZLE"),
    tolerance=v({k: D["tolerance"]["printer"][k] for k in ("gap_error_mm_99", "bed_out_of_level_mm_99", "z_offset_available_mm", "levelling_available_mm")}, "ours", src + " tolerance.printer"))
json.dump(M, open(dst, "w"), indent=1)
print("machines:", list(M), "fields:", sum(len(x) for x in M.values()))
