"""Measure the reference machines from the extracted assembly JSON (extract_step.py output).

Usage: python -I measure_assemblies.py <dir with *.json from extract_step.py> <out.json>

For each machine a small config names the parts by regular expression on the STEP assembly path;
everything numeric below is then read from bounding boxes / volumes of those solids.
Method tags: "cad" = measured from STEP geometry; "cad-est" = CAD volume x assumed density, or a
length inferred from a volume. Coordinates are the CAD's own (mm).
"""
import collections, json, os, re, sys
import numpy as np
from asm import load, sel, union, size, centre, is_fastener, mass_kg, name, klass, RHO

src, out = sys.argv[1], sys.argv[2]

CFG = {
    "voron0": dict(
        file="voron0.json", up=2, default="printed", label="Voron 0.2r1", arch="CoreXY, bed moves in Z on 1 screw",
        frame=r"/Frame/.*Extrusions.*/1515|Extrusion Tophat/.*1515", frame_core=r"/Frame/.*Extrusions.*/1515",
        rails=r"MGN\d+ Rail.*/SOLID$", carriages=r"MGN\d+H? Carriage",
        bed=r"Build Plate/120x120mm MIC6", heater=r"Silicone Bed Heater",
        zscrew=r"Integrated Leadscrew Stepper", zmotor=r"Integrated Leadscrew Stepper",
        zstage=r"/Z Axis/Bed Assembly/", zstage_not=r"Drag Chain",
        belts=r"Belts/[AB] Belt", belt_w=6.0,
        toolhead=r"Gantry/Mini Stealthburner/", nozzle=r"Hotend Assembly/Revo Voron/SOLID",
        xrail=r"Gantry/.*MGN7 Rail 150mm/MGN7 Rail \(4\)/SOLID", xbeam=None,
        ybody=r"Gantry/(Mini Stealthburner|X Axis|XY Joint|.*MGN7 Rail 150mm/MGN7 Rail \(4\))|Printed Parts \((11|14)\)/XY Joint",
        printed=r"Printed Parts|Printed", skip=r"^[^/]*/(Electronics/.*(MCU|Pico|Pi 4|Raspberry Pi|Display PCB|LRS)|Filament Spool|Banana|Tools)|\(Unsaved\)/Banana",
        xy_motors=r"Motor Assembly.*/Nema14", zdrive_note="1 NEMA17 with integrated T8x8 lead screw"),
    "trident": dict(
        file="trident.json", up=2, default="printed", label="Voron Trident 250", arch="CoreXY, bed moves in Z on 3 screws",
        frame=r"/Frame/(Corner|Bottom|Top|Rear|Bed) Extrusions?/", frame_core=r"/Frame/(Corner|Bottom|Top) Extrusions/",
        rails=r"MGN(9|12)( - 300mm| rail)/SOLID$", carriages=r"MGN(9|12)H.*(Carriage|PRODUCT_NAME)",
        bed=r"MIC6 Bed/SOLID", heater=r"Bed heater",
        zscrew=r"NEMA17 Leadscrew 300mm/Leadscrew", zmotor=r"NEMA17 Leadscrew 300mm/Motor_Body",
        zstage=r"/Z Assembly/(Bed Components|Z_Left|Z_Right|Z_Rear)/|/Frame/Bed Extrusions/", zstage_not=None,
        belts=r"Gantry/[AB]_Belt", belt_w=6.0,
        toolhead=r"Gantry/X Axis/Toolhead_Assembly/", nozzle=r"e3d Revo Voron /V7_wo_fan",
        xrail=r"Gantry/X Axis/MGN12 rail/SOLID", xbeam=r"Gantry/X Axis/.*2020.*Extrusion",
        ybody=r"Gantry/X Axis/", printed=r"_Printed|Printed/|\[a\]_", skip=r"/(Tools|Filament_Path/Spool)|Electronics/(Controllers|Pi Assembly|Meanwell|SSR)/.*/",
        xy_motors=r"[AB]_Drive_Motion/NEMA17", zdrive_note="3 NEMA17 with integrated T8 lead screws"),
    "voron24": dict(
        file="voron24.json", up=2, default="printed", label="Voron 2.4r2 250", arch="CoreXY, bed fixed, gantry on 4 belts",
        frame=r"/Frame/(Verticals|Top|Bottom) Extrusions/[^/]*/SOLID|/Frame/Bed Supports/[^/]*/SOLID",
        frame_core=r"/Frame/(Verticals|Top|Bottom) Extrusions/[^/]*/SOLID",
        rails=r"MGN(9|12)( - 300mm| rail)[^/]*/SOLID$", carriages=r"MGN(9|12)H",
        bed=r"10in MIC6 Plate", heater=r"Bed heater",
        zscrew=r"Z Belts/Z Belt", zmotor=r"Z Motor Unit[^/]*/NEMA17 Stepper",
        zstage=r"^[^/]*/Gantry/", zstage_not=r"Cable Chain|Y Cable",
        belts=r"Gantry/[AB] Belt", belt_w=6.0,
        toolhead=r"Gantry/X Axis/X Carriage/", nozzle=r"P6 Assembly \(RevC\)/V7_wo_fan",
        xrail=r"Gantry/X Axis/HFSB5-20-330/MGN12 rail[^/]*/SOLID", xbeam=r"Gantry/X Axis/HFSB5-20-330/SOLID",
        ybody=r"Gantry/X Axis/", printed=r"_Printed|Printed/|\[a\]_|COMPOUND|Z Bearing Block|Belt Clamp", skip=r"/(Spool Holder)|Electronics/(Controllers|Pi Assembly|Meanwell|SSR)[^/]*/.*/",
        xy_motors=r"[AB] Drive/NEMA17", zdrive_note="4 NEMA17, each through a 16:80 closed belt reduction to a 9 mm open belt that lifts one gantry corner"),
    "k3": dict(
        file="k3.json", up=1, default="printed", label="Annex K3 R1.1", arch="cross gantry, bed moves in Z on 3 belts",
        frame=r"Frame, Assembly[^/]*/Frame (Horizontal|Corner|Vertical)", frame_core=r"Frame, Assembly[^/]*/Frame (Horizontal|Corner)",
        rails=r"MGN9 (Gantry|Cross|Z) Rail", carriages=r"MGN9CZFC",
        bed=r"Build Plate - 180x180", heater=r"Build Plate - 180x180",
        zscrew=r"Maxwell, 8mm Rod", zmotor=r"Z_?Drive.*Nema17",
        zstage=r"/Bed Frame\.step\(BeltyZ\)/", zstage_not=r"MGN9 Z Rail|MGN9C \+ Rail",
        belts=r"/[XY]-Belt\^", belt_w=9.0,
        toolhead=r"K3 Sherpa Mini Toolhead\(QD2 ascender", nozzle=r"QD2 ascender[^/]*/MOSQUITO_HOTEND",
        xrail=r"Gantry, X-Axis/.*MGN9 Cross Rail", xbeam=None,
        ybody=r"K3 Sherpa Mini Toolhead\(QD2 ascender|Gantry, Y-Axis/MGN9C \+ Rail \[Cross\]",
        printed=r"(?!x)x", skip=r"(?!x)x", xy_motors=r"Corner_Drive[^/]*/Nema17",
        zdrive_note="3 NEMA17, each through a closed 200 mm belt and 80-tooth pulley to an open belt; bed frame rests on three Maxwell rods (z_drives counts those rods)"),
    "ender3": dict(
        file="ender3.json", up=1, label="Creality Ender 3", arch="bed slides in Y, gantry lifts in Z",
        frame=r"ASM Frame/.*profile", frame_core=r"ASM Frame/.*profile",
        rails=r"ASM (X|Y)-Axis/20(20|40)(-2)? profile|ASM Frame/2040-3[LR] profile", carriages=r"/Rollers$",
        bed=r"ASM Bed/Hot bed", heater=r"ASM Bed/Hot bed",
        zscrew=r"Z threaded rod", zmotor=r"ASM Z-Axis/42-34 motor",
        zstage=r"ASM X-Axis/", zstage_not=None,
        belts=r"/[XY] belt", belt_w=6.0,
        toolhead=r"ASM Printing Head/|ASM (Eccentrical )?Roller X-Axis/", nozzle=r"Heating Unit/nozzle",
        xrail=r"ASM X-Axis/2020 profile", xbeam=r"ASM X-Axis/2020 profile",
        ybody=r"ASM Y-Axis/ASM Bed/", printed=r"(?!x)x", skip=r"ASM Spool Holder",
        xy_motors=r"ASM (X|Y)-Axis/42-34 motor", zdrive_note="1 NEMA17 + T8 lead screw on the left; right side of the X beam is not driven"),
}


def measure(key, c):
    L = load(os.path.join(src, c["file"]))
    up = c["up"]
    horiz = [i for i in range(3) if i != up]
    m = dict(label=c["label"], source_json=c["file"], method="cad")
    keep = [l for l in L if not re.search(c["skip"], "/".join(l["path"]), re.I)]
    m["leaf_solids_in_step"] = len(L)
    m["part_instances_counted"] = len(keep)
    fast = [l for l in keep if is_fastener(l)]
    m["fasteners"] = len(fast)
    m["fastener_types"] = len({re.sub(r"\s*\(\d+\)", "", l["path"][-1]).strip().lower() for l in fast})
    pr = [l for l in keep if re.search(c["printed"], "/".join(l["path"]), re.I) and not is_fastener(l) and l["vol"] > 200]
    m["printed_part_instances"] = len(pr)
    m["printed_volume_cm3"] = round(sum(l["vol"] for l in pr) / 1000)
    # frame
    fr = [l for l in sel(L, c["frame"], 2000) if max(size(l)) > 50]
    core = [l for l in sel(L, c["frame_core"], 2000) if max(size(l)) > 50]
    u = union(core)
    m["frame_outer_mm"] = dict(x=u["size"][horiz[0]], y=u["size"][horiz[1]], z=u["size"][up])
    inv = collections.Counter()
    for l in fr:
        s = sorted(size(l))
        inv[f"{s[0]:.0f}x{s[1]:.0f} L{s[2]:.0f}"] += 1
    m["frame_extrusions"] = dict(inv)
    m["frame_extrusion_count"] = len(fr)
    m["frame_extrusion_total_length_mm"] = round(sum(max(size(l)) for l in fr))
    # rails
    rl = []
    for l in sel(L, c["rails"], 1000):
        s = size(l)
        ax = int(np.argmax(s))
        rl.append(dict(part=name(l, 2), length=max(s), section=sorted(s)[:2],
                       direction="vertical (Z)" if ax == up else "horizontal", long_axis_index=ax, centre=centre(l)))
    m["rails"] = rl
    m["carriages"] = len(sel(L, c["carriages"], 300))
    for ax in horiz:                                   # the pair of parallel horizontal rails carries the X beam
        pr_ = [r for r in rl if r["long_axis_index"] == ax and r["direction"] == "horizontal"]
        if len(pr_) == 2:
            dd = [abs(pr_[0]["centre"][i] - pr_[1]["centre"][i]) for i in horiz]
            if max(dd) > 100:
                m["x_beam_span_mm"] = round(max(dd), 1)
    # bed
    b = sel(L, c["bed"], 1000)[0]
    s = size(b)
    m["bed_plate_mm"] = dict(a=s[horiz[0]], b=s[horiz[1]], t=s[up])
    bc = centre(b)
    m["bed_centre"] = bc
    # Z drive
    zs = sel(L, c["zscrew"], 1000)
    m["z_drives"] = len(zs)
    m["z_drive_note"] = c["zdrive_note"]
    pts = [[centre(l)[horiz[0]] - bc[horiz[0]], centre(l)[horiz[1]] - bc[horiz[1]]] for l in zs]
    m["z_drive_positions_rel_bed_centre_mm"] = [[round(p[0], 1), round(p[1], 1)] for p in pts]
    zr = [r for r in rl if r["long_axis_index"] == up]
    if zr:
        rel = [[round(r["centre"][horiz[0]] - bc[horiz[0]], 1), round(r["centre"][horiz[1]] - bc[horiz[1]], 1)] for r in zr]
        m["z_rail_positions_rel_bed_centre_mm"] = rel
        if len(zr) == 2:      # cantilever layouts: both rails on one side of the bed
            d = [abs(rel[0][i] - rel[1][i]) for i in range(2)]
            along = int(np.argmax(d))
            m["z_rail_spacing_mm"] = round(d[along], 1)
            off = abs(rel[0][1 - along])
            half = (m["bed_plate_mm"]["b"] if (1 - along) == 1 else m["bed_plate_mm"]["a"]) / 2
            m["bed_centre_to_z_rail_plane_mm"] = round(off, 1)
            m["bed_front_edge_to_z_rail_plane_mm"] = round(off + half, 1)
    # belts
    bl = sel(L, c["belts"], 500)
    m["belt_width_mm"] = c["belt_w"]
    m["belts"] = []
    for l in bl:
        w = c["belt_w"]
        e = dict(part=name(l, 1), bbox=size(l), vol_cm3=round(l["vol"] / 1000, 2))
        sb = sorted(size(l))
        e["length_from_bbox_perimeter_mm"] = round(2 * (sb[1] + sb[2]))
        if l.get("area"):
            # ribbon of width w, thickness t, length L: A = 2L(w+t), V = Lwt  ->  L = (A - 2V/w) / (2w)
            e["length_from_area_volume_mm"] = round((l["area"] - 2 * l["vol"] / w) / (2 * w))
            e["modelled_thickness_mm"] = round(l["vol"] / (w * e["length_from_area_volume_mm"]), 2)
        lav, lp = e.get("length_from_area_volume_mm"), e["length_from_bbox_perimeter_mm"]
        if lav and 1.2 <= e["modelled_thickness_mm"] <= 1.5:      # plain ribbon at real GT2 thickness: trust it
            e["length_best_mm"], e["length_range_mm"] = lav, [round(lav * 0.97), round(lav * 1.03)]
        elif lav:                                                  # toothed or thinned model: bracket it
            e["length_best_mm"], e["length_range_mm"] = round((lav + lp) / 2), sorted([lp, lav])
        else:
            e["length_best_mm"], e["length_range_mm"] = lp, [round(lp * 0.9), round(lp * 1.1)]
        e["method"] = "cad-est: solved from the belt solid's surface area and volume (ribbon model); bbox perimeter as a cross-check"
        m["belts"].append(e)
    # toolhead
    th = sel(L, c["toolhead"])
    u = union(th)
    m["toolhead_envelope_mm"] = dict(zip("xyz", u["size"])) if up == 2 else dict(x=u["size"][0], y=u["size"][2], z=u["size"][1])
    mk, by = mass_kg(th, c["printed"], c.get("default", "other"))
    m["toolhead_mass_kg"] = dict(value=mk, by_class=by, method="cad-est: solid volume x assumed densities (asm.RHO)")
    nz = sel(L, c["nozzle"])[0]
    tip = [centre(nz)[0], centre(nz)[1], centre(nz)[2]]
    tip[up] = nz["bbox"][up]
    xr = sel(L, c["xrail"])[0]
    xc = centre(xr)
    perp = [i for i in horiz if i != int(np.argmax(size(xr)))][0]
    m["nozzle_to_x_rail_mm"] = dict(horizontal=round(abs(tip[perp] - xc[perp]), 1), below=round(xc[up] - tip[up], 1))
    m["x_rail_length_mm"] = max(size(xr))
    if c["xbeam"]:
        xb = sel(L, c["xbeam"], 2000)
        if xb:
            m["x_beam_mm"] = dict(length=max(size(xb[0])), section=sorted(size(xb[0]))[:2])
    # moving masses
    yb = sel(L, c["ybody"])
    mk, by = mass_kg(yb, c["printed"], c.get("default", "other"))
    m["y_moving_mass_kg"] = dict(value=mk, by_class=by, method="cad-est", note="X beam / joints / toolhead (or the bed for a bed-slinger); belts and chains excluded")
    zb = sel(L, c["zstage"], 0, c["zstage_not"])
    mk, by = mass_kg(zb, c["printed"], c.get("default", "other"))
    m["z_moving_mass_kg"] = dict(value=mk, by_class=by, method="cad-est")
    m["xy_motors"] = len(sel(L, c["xy_motors"], 5000))
    return m, L


if __name__ == "__main__":
    res = {}
    for key, c in CFG.items():
        if not os.path.exists(os.path.join(src, c["file"])):
            continue
        res[key], _ = measure(key, c)
        print("==", key)
        print(json.dumps({k: v for k, v in res[key].items() if k not in ("rails",)}, indent=None)[:2500])
        for r in res[key]["rails"]:
            print("   rail", r)
    json.dump(res, open(out, "w"), indent=1)
