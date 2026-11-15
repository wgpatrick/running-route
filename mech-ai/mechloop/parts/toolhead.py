"""Toolhead catalog parts with vendor data: E3D Roto extruder, E3D Revo hot side (HeaterCore + nozzle), E3D V6 hotend.

Every number comes from mechloop/parts/vendor/e3d_roto.json, e3d_revo.json or e3d_v6.json (E3D's own data-sheet pages
and drawings, retrieved 2026-11-15; copies in vendor_docs/). The geometry of the Roto and of the Revo hot side is
measured in E3D's own reference CAD (`reference_cad` in the two vendor files; the STEP is in vendor_cad/ and is the
parts' detail model). What E3D does not give is an estimate and is listed in `source["unverified_fields"]`.
See docs/VENDOR_DATA.md and docs/VENDOR_CAD.md.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos, Rot

from . import Stock, _source, details, part, vendor_data

TU = "typical, unverified"
_ROTO_URL = "https://e3d-online.com/pages/revo-support-roto-standard-sensored"
ROTO_INDUCTANCE_EST_MH = 11.0   # NOT published by E3D. Estimate: 7.5 ohm x 1.5 ms (usual L/R of a small hybrid stepper).


def _pts(ports: dict) -> dict:
    out = {}
    for name, p in ports.items():
        a, d = p["at"], p.get("dir", (0, 0, 1))
        out[f"port:{name}"] = [tuple(a), (a[0] + d[0], a[1] + d[1], a[2] + d[2])]
    return out


@part
def extruder_roto() -> Stock:
    """E3D Roto direct-drive extruder (REVO-ROTO-COLDSIDE-AS): 140 g with its motor, heat sink and 35 mm fan; takes a
    Revo hot side (`hotend_revo`), 157 g complete. Geometry measured in E3D's reference CAD (the detail model).
    Local frame = E3D's drawing datum: origin on the axis of the LOWER mounting hole at mid-width; +X towards the motor
    (fan at -X), Y across the 38.5 mm width, +Z up. Both 3.3 mm mounting holes run along Y, each through two 7 mm ears
    at |Y| = 12.25..19.25 (`mount_ears_y`); second hole at (6.8, 30.5). Filament runs down -Z on the line X=-9.058,
    Y=-4.06 and enters the heat sink at Z=27.05; the nozzle tip of the fitted hot side is at Z=-33.55 (`nozzle_tip`).
    Place `hotend_revo()` at `hotend_seat`. Envelope X -25.26..31.85, Y +/-19.25, Z -11.75..44.15. The idler lever
    stands on top on the +Y side of the filament (`lever_box`, to Z=44.15); the CAD shows one position, so keep the
    space around it free. The motor's four leads (not in the solid: flexible) leave at `motor_lead_exit`, diagonally
    towards -Y and +Z. The fan is 5 V (E3D's regulator board for 24 V machines)."""
    d = vendor_data("e3d_roto")
    v, c = d["values"], d["reference_cad"]["measured_mm"]
    box = lambda x, y, z: Pos(sum(x) / 2, sum(y) / 2, sum(z) / 2) * Box(x[1] - x[0], y[1] - y[0], z[1] - z[0])
    xcyl = lambda dia, x, y, z: Pos(sum(x) / 2, y, z) * Rot(0, 90, 0) * Cylinder(dia / 2, x[1] - x[0])
    bd, mo, fa, fs, lv, ue = c["body"], c["motor"], c["fan"], c["fan_screw_heads"], c["idler_lever"], c["upper_ears"]
    tip = tuple(c["nozzle_tip"])
    seat = (tip[0], tip[1], c["hotend_seat_z"])
    hw = c["width"] / 2
    zt = bd["z"][1]
    body = box(bd["x"], bd["y"], bd["z"])                                               # heat sink + gearbox cover + ring gear
    nb = c["nozzle_boss"]
    body += Pos(tip[0], tip[1], sum(nb["z"]) / 2) * Cylinder(nb["dia"] / 2, nb["z"][1] - nb["z"][0])   # seat boss under the heat sink
    ay, az = mo["axis_yz"]
    fl, lb = mo["flange"], mo["lead_block"]
    motor = xcyl(mo["dia"], mo["x"], ay, az) + box(fl["x"], fl["y"], fl["z"])
    ldir = tuple(lb["direction"])                                                       # radially out of the motor, in the YZ plane
    r_in = mo["dia"] / 2 - 1.0                                                          # the block starts inside the round body
    r_mid = (r_in + lb["radius_outer"]) / 2
    motor += (Pos(lb["centre"][0], ay + r_mid * ldir[1], az + r_mid * ldir[2]) * Rot(math.degrees(math.atan2(-ldir[1], ldir[2])), 0, 0)
              * Box(lb["size_x_tangential_radial"][0], lb["size_x_tangential_radial"][1], lb["radius_outer"] - r_in))
    lead_exit = (lb["centre"][0], round(ay + lb["radius_outer"] * ldir[1], 3), round(az + lb["radius_outer"] * ldir[2], 3))
    fw = fa["half_width"]
    fan = box(fa["x"], (-fw, fw), fa["z"])
    for y, z in fs["yz"]:                                                               # the two button heads of the fan screws
        fan += xcyl(fs["dia"], fs["x"], y, z)
    lever = box(lv["block"]["x"], lv["block"]["y"], lv["block"]["z"]) + box(lv["tab"]["x"], lv["tab"]["y"], lv["tab"]["z"])
    ey0, ey1 = c["mount_ears_y_abs"]
    ears = box(ue["x"], (ey0, ey1), (zt, ue["z_top"])) + box(ue["x"], (-ey1, -ey0), (zt, ue["z_top"]))
    shape = body + motor + fan + lever + ears
    lo, up = c["mount_hole_lower"]["xz"], c["mount_hole_upper"]["xz"]
    holes = [(lo[0], 0.0, lo[1]), (up[0], 0.0, up[1])]
    for x, _, z in holes:
        shape -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(1.65, 2 * hw + 2)
    xf, xm = fa["x"][0], mo["x"][1]
    detail, model = details.extruder_roto(c)
    m, k = v["motor"], d["klipper"]
    ports = {"coils": dict(kind="stepper", connector="molex-microfit", max_a=3.0, conductors=4, at=lead_exit, dir=ldir)}
    mratings = {"rated_current_a": v["current_max_a_rms"], "phase_resistance_ohm": m["phase_resistance_ohm"],
                "phase_inductance_mh": ROTO_INDUCTANCE_EST_MH, "holding_torque_nmm": float(m["holding_torque_nmm"]),
                "rotor_inertia_gcm2": m["rotor_inertia_gcm2"], "step_angle_deg": m["step_angle_deg"],
                "run_current_min_a": v["current_min_recommended_a_rms"], "max_surface_temp_c": v["service_temp_c"]["motor_surface"]}
    E3D = f"E3D Roto data-sheet page ({_ROTO_URL})"
    msources = {"rated_current_a": f"{E3D}: 'Do not exceed 0.6A Peak (0.424A RMS)'; rms, the unit of Klipper's run_current. "
                                   "Rated voltage 4.5 V / 7.5 ohm = 0.6 A, the current the holding torque is quoted at",
                "phase_resistance_ohm": f"{E3D}: 7.5 ohm +/-10 % per phase at 20 degC", "holding_torque_nmm": f"{E3D}: 75 mNm",
                "phase_inductance_mh": f"ESTIMATED {ROTO_INDUCTANCE_EST_MH:g} mH: E3D does not publish it ({TU}); measure the motor",
                "rotor_inertia_gcm2": f"{E3D}: 7 gcm2", "run_current_min_a": f"{E3D}: 0.45 A peak (0.318 A rms) minimum recommended",
                "connector": f"{E3D}, motor wiring image: Molex 43025-0400 (on 40 mm leads that leave the motor at the port position: E3D reference CAD)", "max_a": TU, "cost": "e3d-online.com list price GBP 115 (2026-11-15), taken as USD"}
    tpl = {"kind": "stepper", "ports": ports, "ratings": mratings, "sources": msources,
           "params": {"rotation_distance": k["as_published"]["rotation_distance"], "gear_ratio": f"{v['gear_ratio']:g}:1",
                      "full_steps_per_rotation": v["full_steps_per_rotation"], "microsteps": 16,
                      "run_current": k["as_published"]["run_current"]},
           "product": dict(product="E3D Roto Extruder (standard), with its NEMA 14 motor, heat sink and 5 V fan", vendor="E3D-Online",
                           part_number=d["part_number"], form="component", off_the_shelf=True, custom_pcb=False,
                           builder_work="two M3 screws through the body; plug the motor lead (Molex Micro-Fit 4-way) into its extension; "
                                        "feed the 5 V fan through E3D's regulator board (REVO-MICRO-BOARD-REG)")}
    fan_v = v["fan"]
    ratings = {"electrical": tpl,
               "rotation_distance": v["rotation_distance_mm"], "gear_ratio": v["gear_ratio"],
               "full_steps_per_rotation": v["full_steps_per_rotation"], "steps_per_mm_16x": v["steps_per_mm_16x"],
               "rotation_distance_per_motor_rev": k["derived"]["mm_per_motor_rev"],
               "rotation_distance_200_steps_no_gear_ratio": k["derived"]["rotation_distance_for_200_steps_no_gear_ratio"],
               "rotation_distance_note": "26.8937 is per turn of the hobb: Klipper needs gear_ratio 11.262:1 and full_steps_per_rotation 400 "
                                         "with it. A config writer that emits only rotation_distance must use 1.194.",
               "extrusion_force_n": float(v["extrusion_force_n"]), "filament_diameter_mm": v["filament_diameter_mm"],
               "run_current_a_rms": (v["current_min_recommended_a_rms"], v["current_max_a_rms"]),
               "holding_torque_nmm": float(m["holding_torque_nmm"]), "rated_current_a": v["current_max_a_rms"],
               "phase_resistance_ohm": m["phase_resistance_ohm"], "rotor_inertia_gcm2": m["rotor_inertia_gcm2"],
               "max_ambient_c": v["max_ambient_c_pla"],
               "fan": {"volts": fan_v["rated_voltage_v"], "current_a": fan_v["rated_current_a"], "size_mm": tuple(fan_v["size_mm"]),
                       "regulator": "REVO-MICRO-BOARD-REG"},
               "heatsink_sensor_type": v["heatsink_sensor_type"], "vendor_part": d["part_number"]}
    return Stock(shape, "EXTRUDER-E3D-ROTO", "E3D Roto direct-drive extruder with NEMA 14 motor, heat sink and fan (takes a Revo hot side)",
                 v["mass_g"] / 1000.0, material="al6061", ratings=ratings, cost_usd=115.0,
                 detail=detail, model=model,
                 interfaces={"mount_holes_m3": holes, "mount_hole_axis": (0.0, 1.0, 0.0), "mount_hole_dia": 3.3,
                             "mount_width": c["width"], "mount_ears_y": (ey0, ey1),
                             "filament_axis": [(tip[0], tip[1], lv["tab"]["z"][1]), tip],
                             "filament_exit": [seat], "hotend_seat": [seat], "nozzle_tip": [tip],
                             "filament_entry": [(tip[0], tip[1], c["filament_entry_z"])], "lever_top": [tuple(lv["top_face_centre"])],
                             "lever_box": [(lv["tab"]["x"][0], lv["tab"]["y"][0], lv["block"]["z"][0]), (lv["tab"]["x"][1], lv["block"]["y"][1], lv["tab"]["z"][1])],
                             "fan_face_x": xf, "fan_centre": [(xf, ay, az)], "motor_rear_x": xm, "motor_axis": [(mo["x"][0], ay, az), (xm, ay, az)],
                             "motor_dia": mo["dia"], "motor_lead_exit": [lead_exit, tuple(round(p + 10.0 * q, 3) for p, q in zip(lead_exit, ldir))],
                             "body_box": [(bd["x"][0], bd["y"][0], bd["z"][0]), (bd["x"][1], bd["y"][1], bd["z"][1])], **_pts(ports)},
                 source=_source("e3d_roto", "vendor", d["part_number"],
                                unverified=("phase_inductance_mh (estimated)", "idler lever travel (the reference CAD shows one position)",
                                            "licence of the reference CAD (not confirmed)", "cost_usd"),
                                note="mass, gearing, rotation distance, currents, resistance and torque are E3D's published figures; hole pattern, "
                                     "nozzle position and every outline are measured in E3D's reference CAD and agree with E3D's drawing; "
                                     "E3D's Klipper block omits gear_ratio (see the vendor file)"))


@part
def hotend_revo(watts: int = 40, volts: float = 24.0, nozzle: float = 0.4) -> Stock:
    """E3D Revo hot side: HeaterCore (heater + Semitec 104NT thermistor in one part) on a Revo brass nozzle; screws
    finger-tight into a Revo cold side such as `extruder_roto()`. Local frame: nozzle axis Z, the nozzle's seat flange on
    Z=0 (place at the extruder's `hotend_seat`), tip at Z=-22.8; the HeaterCore's lead sleeve leaves towards +X (the
    sleeve is from E3D's HeaterCore drawing; everything else is measured in E3D's reference CAD, which has no sleeve:
    HeaterCore 16.7 dia from 7.13 to 19.01 mm above the tip, 13 mm nozzle block from 2.0 to 7.13). The
    18.3 mm of nozzle tube above the seat is inside the cold side and is not in the solid. Heater: 40 W at 24 V
    (14.4 ohm at 23 degC, PTC). Electrical ports: "in" (heater) and "ntc" (thermistor). In a design:
    `device_from(el, d, "hotend")` (the heater device takes the component's name), then
    `embedded_device(el, d, "hotend", "hotend_thermistor", "thermistor", "ntc", "thermistor", **stock.ratings["thermistor"])`."""
    d = vendor_data("e3d_revo")
    hc, nz, th = d["heatercore"], d["nozzle"], d["thermal_estimates"]
    if watts != 40 or str(int(volts)) not in hc["part_number"]:
        raise ValueError("hotend_revo: only the 40 W HeaterCore at 12 V or 24 V is recorded")
    if str(nozzle) not in nz["part_number"]:
        raise ValueError(f"hotend_revo nozzle must be one of {sorted(nz['part_number'])}")
    hv, nd = hc["values"], nz["drawing"]["dimensioned"]
    cs = hc["drawing"]["scaled_from_drawing_mm"]              # the lead sleeve only (the reference CAD has none)
    c = d["reference_cad"]["measured_mm"]                     # heights above the nozzle tip, measured in E3D's reference CAD
    tip = -nd["seat_flange_to_tip_mm"]
    blk_bot, blk_top = round(tip + c["nozzle_block"]["z"][0], 3), round(tip + c["nozzle_block"]["z"][1], 3)
    core_top = round(tip + c["heatercore"]["z"][1], 3)
    core_dia = c["heatercore"]["dia"]
    cyl = lambda dia, z0, z1: Pos(0, 0, (z0 + z1) / 2) * Cylinder(dia / 2, z1 - z0)
    shape = (cyl(c["above_heatercore"]["head_dia"], core_top, 0.0) + cyl(core_dia, blk_top, core_top)
             + cyl(c["nozzle_block"]["dia"], blk_bot, blk_top) + cyl(4.0, tip, blk_bot))
    zc = round((blk_top + core_top) / 2, 3)
    x0 = core_dia / 2
    shape += Pos(x0 + cs["lead_sleeve_length"] / 2 - 1.0, 0, zc) * Box(cs["lead_sleeve_length"] + 2.0, 5.0, cs["lead_sleeve_height"])
    r23 = hv["resistance_24v_40w_at_23c_ohm"] * (volts / 24.0) ** 2
    a = hv["temp_coefficient_per_c"]
    p_at = lambda t: round(volts ** 2 / (r23 * (1 + a * (t - 23.0))), 1)
    lead = (x0 + cs["lead_sleeve_length"], 0.0, zc)
    ports = {"in": dict(flying=True, kind="heater", connector="molex-microfit", max_a=5.0, at=lead, dir=(1, 0, 0)),
             "ntc": dict(flying=True, kind="thermistor", connector="molex-microfit", max_a=1.0, at=lead, dir=(1, 0, 0))}
    HC = f"E3D 40W 104NT HeaterCore data-sheet page ({d['source_url']})"
    from .electrical import THERMISTORS     # Klipper's R-T points for the sensor (read only)

    sensor = hv["klipper_sensor_type"]
    hratings = {"watts": float(watts), "volts": float(volts), "max_temp_c": float(hv["max_printing_temperature_c"]),
                "resistance_ohm_23c": round(r23, 2), "resistance_tempco_per_c": a,
                "power_w_at_c": {t: p_at(t) for t in (23, 100, 200, 250, 300, 400, 500)}}
    hsources = {"watts": f"{HC}: 40 W; initial resistance of a 40 W 24 V heater at 23 degC: 14.4 ohm"
                         + ("" if volts == 24.0 else " (12 V resistance scaled from the 24 V figure: not published)"),
                "resistance_tempco_per_c": f"{HC}: temp coefficient of a 40 W HeaterCore 0.002078 1/degC (a plain cartridge: 0.0004)",
                "power_w_at_c": "computed from the two figures above; E3D's own graph shows the same curve",
                "max_temp_c": f"{HC}: max printing temperature 300 degC",
                "thermal": "block capacity and area are ESTIMATES from the part masses and drawings, not E3D data (see thermal_estimates in the vendor file)",
                "max_a": TU, "cost": "e3d-online.com list prices GBP 21.50 + 18.50 (2026-11-15), taken as USD"}
    params = {"model": "block", "block_capacity_j_k": th["block_capacity_j_k"], "cartridge_capacity_j_k": 1.0,
              "block_area_m2": th["block_area_m2"], "block_height_m": th["block_height_m"], "emissivity": 0.3,
              "heatbreak_w_k": 0.02, "cartridge_contact_w_k": 5.0, "ptc": {"r_ohm_23c": round(r23, 2), "tempco_per_c": a}}
    tpl = {"kind": "heater", "ports": ports, "ratings": hratings, "sources": hsources, "params": params,
           "product": dict(product=f"E3D Revo HeaterCore {volts:g} V {watts} W (104NT) with Revo brass nozzle {nozzle:g} mm", vendor="E3D-Online",
                           part_number=f"{hc['part_number'][str(int(volts))]} + {nz['part_number'][str(nozzle)]}", form="component",
                           off_the_shelf=True, custom_pcb=False,
                           builder_work="clip the HeaterCore on with its spring, screw the nozzle in by hand; plug both Micro-Fit leads into E3D's extension cables")}
    thermistor = {"ratings": {"max_temp_c": float(hv["max_printing_temperature_c"])},
                  "sources": {"points": "[KLIP] temperature_sensors.cfg", "sensor_type": f"{HC}: Klipper 'ATC Semitec 104NT-4-R025H42G'",
                              "tau_s": f"assumed 2 s for a sensor potted in the HeaterCore ({TU})"},
                  "sensor_type": sensor, "points": THERMISTORS[sensor], "tau_s": 2.0, "node": "block"}
    mass = (hc["derived"]["mass_g"] + nz["values"]["mass_g"]) / 1000.0
    detail, model = details.hotend_revo(c, cs["lead_sleeve_length"], hc["part_number"][str(int(volts))])
    return Stock(shape, f"HOTEND-REVO-{volts:g}V-{watts}W", f"E3D Revo hot side: HeaterCore {volts:g} V {watts} W + brass nozzle {nozzle:g} mm",
                 mass, material="brass", cost_usd=40.0, detail=detail, model=model,
                 ratings={"electrical": tpl, "thermistor": thermistor, "max_temp_c": float(hv["max_printing_temperature_c"]),
                          "heater_w": float(watts), "heater_v": float(volts), "heater_resistance_ohm_23c": round(r23, 2),
                          "heater_tempco_per_c": a, "heater_power_w_at_250c": p_at(250), "sensor_type": sensor,
                          "nozzle_mm": nozzle, "max_flow_mm3_s": nz["values"]["max_flow_mm3_s"].get(str(nozzle)),
                          "hardware_cutoff": "none built in; PTC heater (power falls with temperature) - see the vendor file",
                          "vendor_part": tpl["product"]["part_number"]},
                 interfaces={"seat": [(0.0, 0.0, 0.0)], "nozzle_tip": [(0.0, 0.0, tip)], "heater_block_box": [(-x0, -x0, blk_bot), (x0, x0, core_top)],
                             "nozzle_block_dia": c["nozzle_block"]["dia"], "heatercore_dia": core_dia, "lead_exit": [lead], "tube_above_seat": nd["overall_length_mm"] + tip,
                             **_pts(ports)},
                 source=_source("e3d_revo", "vendor", tpl["product"]["part_number"],
                                unverified=("lead sleeve 22 x 5 x 4.6 and its direction (scaled from the HeaterCore drawing; not in the reference CAD)",
                                            "mass split (9 g HeaterCore derived from 157 - 140 - 8)", "thermal capacity and area (estimated)",
                                            "thermistor response time", "cost_usd") + (("12 V resistance",) if volts != 24.0 else ()),
                                note="power, resistance, temperature coefficient, sensor type, 300 degC limit, nozzle mass and the 22.8 / 41.1 / 13 mm "
                                     "nozzle dimensions are E3D's published figures; HeaterCore and nozzle-block outline measured in E3D's reference CAD"))


@part
def hotend_v6() -> Stock:
    """E3D V6 all-metal hotend, 1.75 mm, 24 V (V6-175-24V), without its fan duct. Local frame: axis Z, top of the
    groove mount on Z=0, nozzle tip at Z=-62.55 (E3D drawing); heater block towards -X. Groove mount: 16 mm flanges,
    12 mm neck from Z=-9.7 to Z=-3.7. Heater 30 W and thermistor cartridge are separate electrical parts
    (`heater_cartridge(30, 24)`, `thermistor_cartridge()`), clamped in the block at `heater_bore` / `sensor_bore`."""
    d = vendor_data("e3d_v6")["added_2026-11-15"]
    v, dr = d["values"], d["drawing"]
    h, g, sv = dr["heights_above_nozzle_tip_mm"], dr["groove_mount_from_fins_top_mm"], dr["side_view_from_axis_mm"]
    top = h["heatsink_top"]
    z = lambda above_tip: above_tip - top
    cyl = lambda dia, z0, z1: Pos(0, 0, (z0 + z1) / 2) * Cylinder(dia / 2, z1 - z0)
    f0 = h["heatsink_fins_top"]
    shape = (cyl(2 * g["flange_radius"], z(f0 + g["groove_top"]), 0.0) + cyl(2 * g["groove_radius"], z(f0 + g["lower_flange_top"]), z(f0 + g["groove_top"]))
             + cyl(2 * g["flange_radius"], z(f0), z(f0 + g["lower_flange_top"])) + cyl(2 * sv["heatsink_radius"], z(h["heatsink_bottom"]), z(f0)))
    bl, bw, bh = 23.0, 16.0, 11.5                    # heater block: recalled / community model, not on E3D's drawing
    bz0 = z(h["block_bottom"])
    shape += Pos(-4.0, 0, bz0 + bh / 2) * Box(bl, bw, bh)                       # block: X = -15.5 .. 7.5
    shape += cyl(2.8, bz0 + bh, z(h["heatsink_bottom"])) + cyl(5.0, z(1.5), bz0) + cyl(2.0, z(0.0), z(1.5))   # heat break, nozzle
    detail, model = details.hotend_v6(z(0.0))
    rr = v["heater_resistance_range_ohm"]
    return Stock(shape, "HOTEND-V6", "E3D V6 all-metal hotend 1.75 mm, 24 V (V6-175-24V)", 0.065, material="al6061", cost_usd=50.0,
                 detail=detail, model=model,
                 ratings={"max_temp_c": float(v["max_operating_temperature_e3d_thermistor_no_sock_c"]),
                          "max_temp_with_sock_c": float(v["max_operating_temperature_with_sock_c"]),
                          "max_rated_temp_c": float(v["max_rated_temperature_c"]), "heater_w": float(v["nominal_heater_power_w"]), "heater_v": 24.0,
                          "heater_resistance_ohm": tuple(rr["24V 30W"]), "heater_resistance_40w_ohm": tuple(rr["24V 40W"]),
                          "sensor_type": d["thermistor"]["klipper_sensor_type"], "max_flow_mm3_s": v["max_flow_pla_220c_mm3_min"] / 60.0,
                          "hardware_cutoff": "none built in", "vendor_part": d["part_number"], "approximate": True},
                 interfaces={"nozzle_tip": [(0.0, 0.0, z(0.0))], "top": [(0.0, 0.0, 0.0)],
                             "groove_mount": {"flange_dia": 2 * g["flange_radius"], "neck_dia": 2 * g["groove_radius"],
                                              "neck_z": (z(f0 + g["lower_flange_top"]), z(f0 + g["groove_top"])), "lower_flange_z": z(f0)},
                             "heatsink_dia": 2 * sv["heatsink_radius"], "heatsink_z": (z(h["heatsink_bottom"]), z(f0)),
                             "heater_block_box": [(-15.5, -bw / 2, bz0), (7.5, bw / 2, bz0 + bh)],
                             "heater_bore": [(-7.0, 0.0, bz0 + 3.9)], "sensor_bore": [(0.0, -6.5, bz0 + 4.7)], "fan_side": "+Y"},
                 source=_source("e3d_v6", "vendor", d["part_number"], d["source_url"],
                                unverified=("mass_kg (0.065 recalled: not on E3D's pages)", "heater block 23 x 16 x 11.5 and its bore positions (community model)",
                                            "cost_usd"),
                                note="heights above the nozzle tip, groove mount, heat-sink radius, temperature limits, heater power and resistance "
                                     "range are E3D's published figures"))
