"""Catalogue parts added from the sixth batch of hand-collected vendor data (2026-11-15):

  leadscrew_motor_17e19()   StepperOnline 17E19S1684MB4-300RS: NEMA 17 motor with an integral Tr8x8 x 300 lead screw
  leadscrew_nut_17e19()     the flanged nut drawn on that screw in the vendor STEP
  manta_m5p()               BIGTREETECH MANTA M5P V1.0 controller (five driver sockets, core-board host)
  fan_cg3010u24()           Coolerguys CG3010U24, a 24 V 30 x 30 x 10 fan with a maker's sheet
  mgn15_rail(), mgn15h_carriage()   Hiwin MGN15 figures, geometry checked against LiMo's vendor-equivalent CAD
  print_sheet_pei180()      TRONXY PEI180 spring-steel sheet

Each value's source, and every conflict and gap, is in the part's vendor file (mechloop/parts/vendor/) and repeated in
the part's `source` / `ratings`. The large vendor STEP files (motor 6.2 MB, Manta 135 MB) stay in vendor_cad/staging/
and are NOT loaded when a design is built: their dimensions were measured once and recorded.
"""
from __future__ import annotations

import math

import numpy as np
from build123d import Box, Cylinder, Pos, Rot

from . import Stock, _source, part, vendor_data

G = 9.81


# ------------------------------------------------------------------ lead-screw motor
@part
def leadscrew_motor_17e19() -> Stock:
    """StepperOnline 17E19S1684MB4-300RS: NEMA 17 stepper (42.3 x 48 mm body) whose shaft IS a Tr8x8 lead screw, 298 mm
    of it above the mounting face (300 nominal). Motor and screw in one part: no coupler.
    Local frame: mounting face on Z=0, screw along +Z, body below; connector on the +X side at the rear.
    Use it as both motor and screw of a joint: drive={"motor": name, "kind": "leadscrew", "screw": name, "nut": <nut>}.
    Lead 8 mm (0.04 mm per full step): NOT the 2 mm-lead T8x2 the catalogue's `leadscrew_t8(L, lead=2)` gives; at the
    same torque it pushes a quarter as hard and it back-drives more easily.
    Mass: the drawing says 0.35 kg, the product page 454 g; the heavier is used. Axial (thrust) load rating: NOT STATED
    by the maker; the ratings verifier reports the axial load a design puts on it (`axial_load_rating_unknown`)."""
    d = vendor_data("stepperonline_17e19")
    v, sm = d["values"], d["step_measured_mm"]
    frame, body_l = v["frame_mm_max"]["value"], v["body_length_mm_max"]["value"]
    screw_l = sm["screw_above_mounting_face"]
    cn = sm["connector"]
    shape = (Pos(0, 0, -body_l / 2) * Box(frame, frame, body_l)
             + Pos(0, 0, v["pilot"]["height_mm"] / 2) * Cylinder(v["pilot"]["dia_mm"] / 2, v["pilot"]["height_mm"])
             + Pos(0, 0, screw_l / 2) * Cylinder(v["screw"]["diameter_mm"] / 2, screw_l)
             + Pos(frame / 2 + cn["stands_out"] / 2 - 0.5, 0, -body_l + cn["height_from_rear"] / 2)
             * Box(cn["stands_out"] + 1.0, cn["width"], cn["height_from_rear"]))
    h = v["hole_square_mm"]["value"] / 2
    holes = [(x, y, 0.0) for x in (-h, h) for y in (-h, h)]
    m = v["mass_kg"]
    torque = v["holding_torque_nm"]["value"] * 1000.0
    return Stock(shape, "NEMA17-48-LEADSCREW-TR8x8-300", "NEMA 17 lead-screw stepper, Tr8x8 x 300 mm (StepperOnline 17E19S1684MB4-300RS)",
                 m["used"], material="steel",
                 ratings={"holding_torque_nmm": torque, "rotor_inertia_gcm2": v["rotor_inertia_gcm2"]["value"],
                          "rated_current_a": v["rated_current_a"]["value"], "phase_resistance_ohm": v["phase_resistance_ohm"]["value"],
                          "phase_inductance_mh": v["phase_inductance_mh"]["value"], "vendor_part": "17E19S1684MB4-300RS",
                          "lead_mm": v["screw"]["lead_mm"], "efficiency": 0.5,
                          "efficiency_source": "typical for an 8 mm-lead trapezoidal screw with a plastic or brass nut; NOT stated by the maker",
                          "mass_kg_datasheet": m["datasheet_pdf"], "mass_kg_product_page": m["product_page"],
                          "mass_note": "maker's drawing 0.35 kg, product page 454 g: unresolved; the heavier is the part's mass",
                          "axial_load_rating_n": None,
                          "axial_load_rating_status": "NOT STATED by the maker (no thrust rating, thrust curve or bearing axial-load limit)",
                          "torque_curve_status": "no torque-speed curve published: without an electrical model 0.7 x holding torque is "
                                                 "assumed at every speed; with one, the curve comes from the winding figures",
                          "integral_leadscrew": True},
                 interfaces={"mount_holes_m3": holes, "pilot_dia": v["pilot"]["dia_mm"], "hole_square": v["hole_square_mm"]["value"],
                             "thread_depth": v["thread_depth_min_mm"]["value"], "screw_dia": v["screw"]["diameter_mm"],
                             "screw_length": screw_l, "screw_tip": [(0.0, 0.0, screw_l)], "connector_side": "+X"},
                 cost_usd=33.0,
                 source=_source("stepperonline_17e19", "partial", "17E19S1684MB4-300RS",
                                unverified=("mass_kg", "axial_load_rating_n", "efficiency", "torque-speed curve", "cost"),
                                note="electrical and mechanical figures were transcribed by the collector from the maker's image-only "
                                     "drawing; frame, holes, pilot and screw length were measured in the maker's STEP. Mass conflict "
                                     "(0.35 kg / 454 g), no axial rating, no efficiency, no curve"))


@part
def leadscrew_nut_17e19() -> Stock:
    """The flanged nut drawn on the 17E19S1684MB4-300RS's screw in the maker's STEP: flange 25.4 dia x 3.81, barrel 12.7 dia,
    19.05 long overall, three 3.56 mm holes on a 19.05 mm circle (inch sizes). Local frame: axis Z, flange bottom on Z=0,
    barrel above. Material and backlash are not stated (taken as acetal for mass)."""
    n = vendor_data("stepperonline_17e19")["step_measured_mm"]["nut"]
    fl, ft, bd, L = n["flange_dia"], n["flange_thickness"], n["barrel_dia"], n["overall_length"]
    r = 19.05 / 2
    holes = [(r * math.cos(a), r * math.sin(a), 0.0) for a in (math.radians(30), math.radians(150), math.radians(270))]
    shape = Pos(0, 0, ft / 2) * Cylinder(fl / 2, ft) + Pos(0, 0, L / 2) * Cylinder(bd / 2, L) - Pos(0, 0, L / 2) * Cylinder(4.0, L)
    for x, y, _ in holes:
        shape -= Pos(x, y, ft / 2) * Cylinder(3.56 / 2, ft)
    return Stock(shape, "NUT-TR8x8-17E19", "Flanged lead-screw nut Tr8x8 (supplied on the 17E19S1684MB4-300RS)", 0.004, material="abs",
                 ratings={"approximate": True, "lead_mm": 8.0},
                 interfaces={"mount_holes_m3": holes, "barrel_dia": bd, "flange_dia": fl, "length": L, "hole_dia": 3.56},
                 cost_usd=0.0,
                 source=_source("stepperonline_17e19", "partial", "nut of 17E19S1684MB4-300RS",
                                unverified=("material", "mass_kg", "backlash", "load rating", "angular position of the three holes"),
                                note="dimensions measured in the maker's STEP; nothing else about the nut is stated"))


def leadscrew_axial_loads(design) -> dict:
    """Axial load each lead-screw drive puts on its screw, for screws whose axial rating matters: weight of what the joint
    carries along the screw's axis plus the force to accelerate it at the joint's max_accel. For a part whose maker
    states no axial rating (ratings["axial_load_rating_status"]) the result carries `rating: None`; with a rating
    (ratings["axial_load_rating_n"]) it carries the margin. Shared by motors that drive the joint together."""
    comps = {c.name: c for c in design.components}
    bodies = design.bodies()

    def carried(body):
        m = sum(c.mass() for c in bodies.get(body, []))
        return m + sum(carried(j.child) for j in design.joints if j.parent == body)

    out = {}
    g = np.array(design.gravity, dtype=float) * 1e-3
    for j in design.joints:
        drv = j.drive or {}
        if drv.get("kind") != "leadscrew" or j.kind != "slide":
            continue
        motors = [drv["motor"]] if isinstance(drv.get("motor"), str) else list(drv.get("motor") or [])
        screws = [n for n in ({drv.get("screw")} | set(motors)) if n in comps and
                  ("axial_load_rating_status" in comps[n].ratings or comps[n].ratings.get("axial_load_rating_n"))]
        if not screws:
            continue
        ax = np.array(j.axis, dtype=float) / np.linalg.norm(j.axis)
        m = carried(j.child)
        n_share = max(len([n for n in motors if comps.get(n) is not None and comps[n].ratings.get("integral_leadscrew")]), 1)
        weight = abs(float(m * (g @ ax)))
        accel = m * (j.max_accel or 0.0) * 1e-3
        for n in sorted(screws):
            rt = comps[n].ratings
            total = (weight + accel) / n_share
            e = {"joint": j.name, "carried_mass_kg": round(m, 3), "screws_sharing": n_share, "weight_along_axis_n": round(weight / n_share, 2),
                 "acceleration_force_n": round(accel / n_share, 2), "axial_load_n": round(total, 2),
                 "rating_n": rt.get("axial_load_rating_n"), "rating_status": rt.get("axial_load_rating_status", "catalogue rating")}
            if rt.get("axial_load_rating_n"):
                e["margin"] = round(rt["axial_load_rating_n"] / total, 2) if total > 0 else None
            out[n] = e
    return out


def check_leadscrew_axial_loads(design, r) -> dict:
    """Ratings-verifier hook: report the axial load on lead-screw motors. No maker's rating: a WARNING with the load
    (never a silent pass). A rating exceeded: an error."""
    loads = leadscrew_axial_loads(design)
    for n, e in loads.items():
        if e["rating_n"] is None:
            r.add("warning", "axial_load_rating_unknown",
                  f"{n} carries {e['axial_load_n']:.1f} N along its screw on joint {e['joint']} ({e['weight_along_axis_n']:.1f} N of "
                  f"weight, {e['acceleration_force_n']:.1f} N to accelerate {e['carried_mass_kg']:.2f} kg"
                  + (f", shared by {e['screws_sharing']} screws" if e["screws_sharing"] > 1 else "") + "). Its maker states no axial "
                  f"load rating ({e['rating_status']}), so this load is NOT checked against anything.", part=n, joint=e["joint"],
                  axial_load_n=e["axial_load_n"],
                  hint="Ask the maker for the thrust / bearing axial-load rating, keep the load small, or carry the weight on a "
                       "separate thrust bearing. Do not infer a limit from the holding torque.")
        elif e["axial_load_n"] > e["rating_n"]:
            r.add("error", "axial_load_over_rating",
                  f"{n} carries {e['axial_load_n']:.1f} N along its screw on joint {e['joint']}; its rating is {e['rating_n']:g} N.",
                  part=n, joint=e["joint"], axial_load_n=e["axial_load_n"], rating_n=e["rating_n"])
    return loads


# ------------------------------------------------------------------ controller
MANTA_DRIVERS = {"TMC2209": dict(driver="TMC2209", sense_resistor_ohm=0.11, driver_max_rms_a=1.74, driver_abs_max_rms_a=2.0,
                                 driver_rds_on_ohm=0.17, driver_max_v=28.0, sku="DRIVER-BTT-TMC2209", cost_usd=6.0)}


@part
def manta_m5p(drivers: str = "TMC2209") -> Stock:
    """BIGTREETECH MANTA M5P V1.0 controller: 137.39 x 95 mm PCB, four mounting holes on 128.39 x 86 mm, FIVE plug-in
    stepper driver sockets (M1..M5; drivers are NOT included), bed 10 A, two heaters 5.5 A each, fans 1 A each (2.5 A
    together), 12 or 24 V input. Local frame: PCB centred, underside on Z=0 (stand it on >= 5 mm spacers), X long edge.
    drivers: the driver module fitted in every socket. Only "TMC2209" (BIGTREETECH TMC2209 stick, UART) is in the
      catalogue; buy one per motor channel used and add them to the BOM: design.bom_extra("DRIVER-BTT-TMC2209", n, 6.0).
    Host: the board carries a core board (Raspberry Pi CM4 or BIGTREETECH CB1, bought separately) on its own headers,
      with that host's USB, LAN and HDMI on the board. A design using it needs no separate Pi and no host wiring; the
      core board's current draw is not stated (interfaces/ratings say so) and is not in the 5 V budget.
    Ports (electrical model): POWER, HB, HE0, HE1, FAN0, FAN1, M1..M5 (M3 has a second connector M3B on the same driver),
      MIN1..MIN4, PROBE, THB, TH0, TH1. Five sockets are X, Y, extruder and two independent Z; three independent Z leave
      no socket for an extruder. Pins are Klipper's generic-bigtreetech-manta-m5p.cfg: one UART pin per driver.
    The envelope is the PCB plus an 18.7 mm component allowance (vendor STEP bounding box 20.3 mm high overall); the
    135 MB vendor STEP is not loaded and connector positions along the edges are approximate."""
    if drivers not in MANTA_DRIVERS:
        raise ValueError(f"manta_m5p drivers must be one of {sorted(MANTA_DRIVERS)} (no data for other modules: needed data)")
    d = vendor_data("bigtreetech_manta_m5p")
    v, pins = d["values"], d["pins"]
    W, H = v["board_mm"]["used"]
    T = 1.6
    hx, hy = v["hole_pattern_mm"]["value"][0] / 2, v["hole_pattern_mm"]["value"][1] / 2
    holes = [(x, y, 0.0) for x in (-hx, hx) for y in (-hy, hy)]
    EH = v["assembly_bbox_mm"]["value"][2] - T
    pcb = Pos(0, 0, T / 2) * Box(W, H, T)
    env = Pos(0, 0, T + EH / 2) * Box(W - 1.0, H - 1.0, EH)
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.6, T)
        env -= Pos(x, y, T + EH / 2) * Cylinder(4.0, EH)
    z, up, edge = T + 8.0, (0, 0, 1), (0, -1, 0)
    xh = dict(connector="JST-XH", max_a=3.0)
    es = dict(logic_v=3.3, pin_max_v=3.6)
    fa = v["fan_a"]["continuous"]

    def drv(k):
        p = pins[k]
        return {"step": p["step"], "dir": p["dir"], "enable": p["enable"], "uart": p["uart"], "diag": p["diag"],
                "diag_jumper": f"{k} DIAG" if p["diag"] else None}

    def at(fx, fy):          # fractions of the board: approximate positions
        return ((fx - 0.5) * W, (fy - 0.5) * H, z)

    ports = {
        "POWER": dict(kind="power_in", connector="screw-5.08", max_a=20.0, at=at(0.06, 0.05), dir=edge),
        "HB": dict(kind="heater_out", connector="screw-5.08", max_a=v["bed_a"]["continuous"], pin=pins["HB"], at=at(0.18, 0.05), dir=edge),
        "HE0": dict(kind="heater_out", connector="screw-5.08", max_a=v["heater_a"]["continuous"], pin=pins["HE0"], at=at(0.28, 0.05), dir=edge),
        "HE1": dict(kind="heater_out", connector="screw-5.08", max_a=v["heater_a"]["continuous"], pin=pins["HE1"], at=at(0.36, 0.05), dir=edge),
        "FAN0": dict(kind="fan_out", connector="JST-XH", max_a=fa, pin=pins["FAN0"], at=at(0.46, 0.05), dir=up),
        "FAN1": dict(kind="fan_out", connector="JST-XH", max_a=fa, pin=pins["FAN1"], at=at(0.52, 0.05), dir=up),
        "MIN1": dict(kind="endstop_in", **es, pin=pins["MIN1"], at=at(0.60, 0.05), dir=up, **xh),
        "MIN2": dict(kind="endstop_in", **es, pin=pins["MIN2"], at=at(0.66, 0.05), dir=up, **xh),
        "MIN3": dict(kind="endstop_in", **es, pin=pins["MIN3"], at=at(0.72, 0.05), dir=up, **xh),
        "MIN4": dict(kind="endstop_in", **es, pin=pins["MIN4"], at=at(0.78, 0.05), dir=up, **xh),
        "PROBE": dict(kind="endstop_in", **es, pin=pins["PROBE"], at=at(0.84, 0.05), dir=up, **xh),
        "THB": dict(kind="thermistor_in", pin=pins["THB"], at=at(0.88, 0.12), dir=up, pullup_ohm=4700.0, adc_bits=12, **xh),
        "TH0": dict(kind="thermistor_in", pin=pins["TH0"], at=at(0.92, 0.12), dir=up, pullup_ohm=4700.0, adc_bits=12, **xh),
        "TH1": dict(kind="thermistor_in", pin=pins["TH1"], at=at(0.96, 0.12), dir=up, pullup_ohm=4700.0, adc_bits=12, **xh),
    }
    for i, k in enumerate(("M1", "M2", "M3", "M4", "M5")):
        ports[k] = dict(kind="stepper_out", pin=drv(k), group=k, conductors=4, at=at(0.12 + 0.15 * i, 0.95), dir=up, **xh)
    ports["M3B"] = dict(kind="stepper_out", pin=drv("M3"), group="M3", conductors=4, at=at(0.49, 0.95), dir=up, **xh)
    dm = MANTA_DRIVERS[drivers]
    ratings = {"supply_v": tuple(v["input_v"]["value"]), "input_fuse_a": None, "stepper_drivers": 5, "driver_sockets": 5,
               "driver": dm["driver"], "driver_modules_included": False, "driver_module_sku": dm["sku"],
               "sense_resistor_ohm": dm["sense_resistor_ohm"], "driver_max_rms_a": dm["driver_max_rms_a"],
               "driver_abs_max_rms_a": dm["driver_abs_max_rms_a"], "driver_rds_on_ohm": dm["driver_rds_on_ohm"], "driver_max_v": dm["driver_max_v"],
               "output_resistance_ohm": 0.012, "logic_w": 1.5, "adc_bits": 12, "thermistor_pullup_ohm": 4700.0,
               "fan_total_max_a": v["fan_a"]["all_fans_total_max"], "host_on_board": "core board: Raspberry Pi CM4 or BIGTREETECH CB1 (not included)",
               "max_ambient_c": 60.0}
    TU = "typical, unverified"
    sources = {"outline_holes": "[BTT] MANTA M5P SIZE-top drawing: 137.39 x 95 mm, holes on 128.39 x 86 mm (hole diameter not transcribed)",
               "HB.max_a / HE.max_a / fan max_a": "[BTT] MANTA M5P manual p.6: bed 10 A continuous, heaters 5.5 A, fans 1 A each and < 2.5 A together",
               "supply_v": "[BTT] manual p.6: VIN DC 12 V or 24 V",
               "pins": "[KLIP] generic-bigtreetech-manta-m5p.cfg (the manual's pinout is an image, not transcribed)",
               "connector_positions": f"NOT from the drawing: spread along the edges ({TU}); the vendor STEP (135 MB) was not loaded",
               "driver": "[BTT] TMC2209 stick: 2 A rms / 2.8 A peak, 28 V (module manual); current limits as Klipper's tmc2208.py (CS=31: 1.74 A rms)",
               "input_fuse_a": "replaceable fuse fitted (manual p.5); its rating was not transcribed", "thermistor_pullup_ohm": f"4.7 k for 100K NTC ({TU}); "
               "PT1000 pull-up selectable by jumper", "host": "[BTT] manual p.5, p.13, p.20-26: BTB headers for CM4 / CB1; their current draw is not stated",
               "max_ambient_c": TU, "logic_w": TU, "output_resistance_ohm": TU, "mass": TU, "cost": TU}
    prod = dict(product="BIGTREETECH MANTA M5P V1.0 (bare board: five driver modules and a CM4 / CB1 core board to be added)",
                vendor="BIGTREETECH (Shenzhen Big Tree Technology)", part_number="MANTA M5P V1.0", form="assembled board", off_the_shelf=True,
                custom_pcb=False, builder_work=f"plug in one {dm['driver']} module per motor channel used and set its UART jumpers; plug in the "
                                               "core board; set the fan-voltage and probe jumpers")
    from . import electrical as _pe

    return Stock(pcb + env, "CTRL-MANTA-M5P", "BIGTREETECH MANTA M5P V1.0 control board (5 driver sockets, CM4/CB1 host on board)", 0.11,
                 material="abs",
                 ratings={"electrical": {"kind": "board", "ports": ports, "ratings": ratings, "sources": sources, "product": prod, "params": {}},
                          "stepper_drivers": 5, "approximate": True},
                 interfaces={"mount_holes_m3": holes, "standoff_min": 5.0, "size": (W, H), "hole_pattern": tuple(v["hole_pattern_mm"]["value"]),
                             **_pe._ports_to_interfaces(ports)},
                 cost_usd=60.0,
                 source=_source("bigtreetech_manta_m5p", "partial", "MANTA M5P V1.0",
                                unverified=("mass_kg", "mount hole diameter", "connector positions", "input fuse rating", "core board current",
                                            "height (bounding box of the vendor STEP as reported by the collector)"),
                                note="outline, hole pattern and current limits are BIGTREETECH's; pins are Klipper's example config; "
                                     "driver modules and the core-board host are separate purchases"))


# ------------------------------------------------------------------ fan
@part
def fan_cg3010u24() -> Stock:
    """Coolerguys CG3010U24: 30 x 30 x 10 mm axial fan, 24 V, 0.07 A, 5.45 CFM free air, 8.01 mmH2O shut-off, 13,400 rpm,
    31.5 dBA, 8 g (maker's sheet). The 24 V 30 mm fan with data; `fan(30)` is a 24 V fan without a sheet and `fan(30, 12)`
    is the 12 V Sunon. Local frame: centred, air along Z. Hole pattern (24 mm, 3.2 mm) is the usual 3010 frame's, not on
    the sheet as transcribed. SKU FAN-3010-CG3010U24."""
    v = vendor_data("coolerguys_cg3010u24")["values"]
    size, pitch = 30, 24.0
    body = Box(size, size, 10) - Cylinder(size / 2 - 1.5, 10)
    holes = [(x, y, -5.0) for x in (-pitch / 2, pitch / 2) for y in (-pitch / 2, pitch / 2)]
    for x, y, _ in holes:
        body -= Pos(x, y, 0) * Cylinder(1.6, 10)
    from . import details

    detail, model = details.fan(30)
    return Stock(body, "FAN-3010-CG3010U24", "30 mm axial fan, 24 V (Coolerguys CG3010U24)", v["mass_g"] / 1000.0, material="abs",
                 detail=detail, model=model, interfaces={"mount_holes_m3": holes},
                 ratings={"electrical": True, "rated_voltage_v": v["rated_voltage_v"], "rated_current_a": v["rated_current_a"],
                          "air_flow_cfm": v["air_flow_cfm"], "air_flow_m3_min": round(v["air_flow_cfm"] * 0.0283168, 4),
                          "static_pressure_pa": v["static_pressure_pa"], "static_pressure_mmh2o": v["static_pressure_mmh2o"],
                          "speed_rpm": v["speed_rpm"], "noise_dba": v["noise_dba"], "vendor_part": "CG3010U24",
                          "rated_current_source": "Coolerguys CG3010U24 product sheet: 0.07 A at 24 V",
                          "rated_voltage_source": "Coolerguys CG3010U24 product sheet: 24 V DC"},
                 cost_usd=7.0,
                 source=_source("coolerguys_cg3010u24", "partial", "CG3010U24",
                                unverified=("mount hole pattern", "operating voltage range", "detail model (a generic 3010 fan)"),
                                note="voltage, current, air flow, pressure, speed, noise and mass are the maker's sheet; maximum flow "
                                     "and maximum pressure are not one operating point"))


# ------------------------------------------------------------------ MGN15
_MGN15_NOTE = ("dimensions, load ratings, rigidity and parallelism are HIWIN's catalogue GW-11-5-EN-2207-K (Tables 3.76, 3.77, 3.79, "
               "3.81, 3.88) for a HIWIN MGN15H / MGNR15. The geometry was cross-checked against LiMo Bearing's SZ15L assembly STEP, a "
               "VENDOR-EQUIVALENT model (not Hiwin's CAD), which agrees on every dimension measured. A LiMo or other equivalent "
               "block does not carry Hiwin's ratings")
_MGN15_URL = "vendor_docs/Hiwin_MG_catalogue.pdf (HIWIN GmbH catalogue GW-11-5-EN-2207-K, printed pages 92-105; hand-collected)"
_MGN15_MODEL = {"kind": "proxy", "source": "simulation solid from Hiwin's table; checked against LiMo's vendor-equivalent assembly STEP "
                                           "(vendor_cad/staging/MGN15H-150mm-assembly_LiMo-vendor-equivalent.step), which is not attached "
                                           "as a detail model"}


@part
def mgn15_rail(length: float) -> Stock:
    """MGN15 miniature linear rail (15 wide, 10 high, holes 3.5 with 6 x 4.5 counterbore every 40 mm).
    Local frame: rail along X centred at origin, base at Z=0, top at Z=10."""
    cat = vendor_data("hiwin_mgn12")["catalogue"]["rail_dimensions"]
    r = dict(zip(cat["columns"], cat["MGNR15R"]))
    wr, hr, pitch, cb = r["WR_mm"], r["HR_mm"], r["P_mm"], r["h_mm"]
    rail = Pos(0, 0, hr / 2) * Box(length, wr, hr)
    n = int((length - 2 * r["E_min_mm"]) // pitch) + 1
    x0 = -(n - 1) * pitch / 2
    holes = [(x0 + i * pitch, 0.0, 0.0) for i in range(n)]
    for x, _, _ in holes:
        rail -= Pos(x, 0, hr / 2) * Cylinder(r["d_mm"] / 2, hr)
        rail -= Pos(x, 0, hr - cb / 2) * Cylinder(r["D_mm"] / 2, cb)
    return Stock(rail, f"MGN15-R-{int(length)}", f"MGN15 rail, {length:.0f} mm", r["kg_per_m"] * length / 1000, model=dict(_MGN15_MODEL),
                 interfaces={"mount_holes_m3": holes, "hole_pitch": pitch, "screw_seat_z": hr - cb,
                             "end_distance": round(length / 2 + x0, 3)},
                 cost_usd=8 + 0.05 * length, source=_source("hiwin_mgn12", "vendor", "MGNR15", _MGN15_URL, note=_MGN15_NOTE))


@part
def mgn15h_carriage(preload: str | None = None) -> Stock:
    """MGN15H carriage block (long): 58.8 x 32, top 16 mm above the rail base, four M3 x 4 deep on 25 x 25.
    Local frame: sits on an MGN15 rail whose base is Z=0; top face at Z=16; length along X.
    preload "ZF" | "Z0" | "Z1" as for mgn12h_carriage (Z0 assumed when left out): radial rigidity 87 N/um at Z0, 113 at
    Z1, none published for ZF; two rails may be 10 um out of parallel at ZF / Z0, 6 um at Z1."""
    cat = vendor_data("hiwin_mgn12")["catalogue"]
    b = cat["block_dimensions"]["MGN15H"]
    rr = dict(zip(cat["rail_dimensions"]["columns"], cat["rail_dimensions"]["MGNR15R"]))
    cls = preload or "Z0"
    if cls not in ("ZF", "Z0", "Z1"):
        raise ValueError("mgn15h_carriage preload must be one of ('ZF', 'Z0', 'Z1')")
    H, H1, W, L = b["H_mm"], b["H1_mm"], b["W_mm"], b["L_mm"]
    block = Pos(0, 0, (H + H1) / 2) * Box(L, W, H - H1) \
        - Pos(0, 0, (rr["HR_mm"] + H1) / 2) * Box(L, rr["WR_mm"] + 0.4, rr["HR_mm"] - H1)
    holes = [(x, y, float(H)) for x in (-b["C_mm"] / 2, b["C_mm"] / 2) for y in (-b["B_mm"] / 2, b["B_mm"] / 2)]
    lr = dict(zip(cat["load_ratings"]["columns"], cat["load_ratings"]["MGN15H"]))
    rig, par = cat["radial_rigidity_n_per_um"], cat["mounting_surface"]["max_parallelism_of_two_rails_um"]
    stiff = {}
    if cls in rig["columns"]:
        stiff = {"radial_stiffness_n_per_m": rig["MGN15H"][rig["columns"].index(cls)] * 1e6,
                 "radial_stiffness_source": f"Hiwin MG catalogue Table 3.77 (p.96): MGN15H, preload {cls}, radial, per block"}
    depth = float(b["mount_thread_Mxl"].split("x")[1])
    return Stock(block, "MGN15H", "MGN15H carriage block" + (f" (preload {cls})" if preload else ""), b["mass_kg"], model=dict(_MGN15_MODEL),
                 ratings={"dynamic_load_n": float(lr["Cdyn_N"]), "static_load_n": float(lr["C0_N"]),
                          "static_moment_nm": min(lr["M0X_Nm"], lr["M0Y_Nm"], lr["M0Z_Nm"]), "static_moment_mr_nm": lr["M0X_Nm"],
                          "static_moment_mp_nm": lr["M0Y_Nm"], "static_moment_my_nm": lr["M0Z_Nm"], "preload_class": cls,
                          "preload_class_basis": "declared by the design" if preload else "assumed (catalogue default Z0; not declared)",
                          "ball_track_length_m": b["L1_mm"] * 1e-3, **stiff,
                          "allowable_parallelism_mm": round(par["MG_15"][par["columns"].index(cls)] * 1e-3, 6),
                          "allowable_parallelism_source": f"Hiwin MG catalogue Table 3.88 (p.104): MG_15, preload {cls}"},
                 interfaces={"mount_holes_m3": holes, "top_z": float(H), "thread_depth": depth},
                 cost_usd=12.0, source=_source("hiwin_mgn12", "vendor", "MGN15H", _MGN15_URL, note=_MGN15_NOTE))


# ------------------------------------------------------------------ print sheet
@part
def print_sheet_pei180() -> Stock:
    """TRONXY PEI180: 180 x 180 mm PEI-coated spring-steel sheet, 0.4 mm, sold with a magnetic base said to hold to 130 degC.
    Local frame: centred, underside on Z=0, print surface at Z=0.4. Only the steel sheet is drawn: the magnetic base's
    thickness is not published, so the stack height on the bed is NOT known (interfaces["magnetic_base_thickness"] is
    None). Mass is computed from the steel alone (0.102 kg); the maker publishes none. Join it to the bed plate with
    design.join(sheet, bed, "magnetic")."""
    v = vendor_data("tronxy_pei180")["values"]
    sx, sy = v["size_mm"]
    t = v["steel_thickness_mm"]["value"]
    mass = round(sx * sy * t * 7.85e-6, 4)
    return Stock(Pos(0, 0, t / 2) * Box(sx, sy, t), "SHEET-PEI-TRONXY-180", "PEI spring-steel print sheet 180 x 180 x 0.4 with magnetic base (TRONXY PEI180)",
                 mass, material="steel",
                 ratings={"approximate": True, "magnetic_base_max_temp_c": v["magnetic_base_max_temp_c"]["value"],
                          "magnetic_base_max_temp_basis": "seller's claim; not independently qualified",
                          "mass_basis": "computed: 180 x 180 x 0.4 mm of steel at 7850 kg/m3; the magnetic base and coating are not included",
                          "steel_grade": None, "print_surface": "PEI"},
                 interfaces={"size": (sx, sy), "thickness": t, "print_surface_z": t, "magnetic_base_thickness": None},
                 cost_usd=15.0,
                 source=_source("tronxy_pei180", "partial", "PEI180",
                                unverified=("mass_kg", "steel grade", "magnetic base thickness", "total stack thickness", "flatness", "cost"),
                                note="size, 0.4 mm steel and the 130 degC claim are the seller's page; everything else is unpublished"))
