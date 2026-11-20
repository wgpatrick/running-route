"""Catalogue parts added from the seventh batch of vendor data (2026-11-16):

  leadscrew_motor_17e19_ab4()        StepperOnline 17E19S1684AB4-330RA: NEMA 17 motor whose shaft is a Tr8x2 x 330 lead
                                     screw (the motor body; its screw is the next part)
  leadscrew_screw_17e19_ab4(length)  that motor's integral Tr8x2 screw, above the mounting face (cut to length by the builder
                                     or ordered short)
  octopus_v11()                      BIGTREETECH Octopus V1.1 controller (eight driver sockets)

Each value's source, and every gap, is in the part's vendor file (mechloop/parts/vendor/) and repeated in the part's
`source` / `ratings`. Values the vendor does not state are listed as unverified on the part.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos

from . import Stock, _source, part, vendor_data
from .batch6 import MANTA_DRIVERS

AB4 = "17E19S1684AB4-330RA"
AB4_SCREW_ABOVE_FACE = 328.0      # 330 nominal; 298 of 300 above the face on the sister model's STEP (assumed alike)


def _ab4_screw_mass(length: float) -> float:
    return math.pi * 4.0 ** 2 * length * 7.85e-6 * 0.85      # steel, 0.85 for the thread form


@part
def leadscrew_motor_17e19_ab4() -> Stock:
    """StepperOnline 17E19S1684AB4-330RA: NEMA 17 stepper (42 x 48 mm body, 1.68 A, 0.44 N.m, 1.65 ohm, 2.8 mH) whose shaft
    IS a Tr8x2 lead screw, 330 mm long, sold with an anti-backlash nut. No coupler.

    Drawn as TWO catalogue parts so that the checkers see an 8 mm screw and a motor body, not one 42 mm solid: this body,
    and `leadscrew_screw_17e19_ab4(length)` placed on its axis from the mounting face up (join them, "integral screw").
    Name both in the joint's drive: drive={"motor": [bodies], "kind": "leadscrew", "screw": [screws], "nut": [...]}.
    One item is bought; the body carries the price and the mass of the motor without its screw.
    Local frame: mounting face on Z=0, screw axis along +Z, body below, connector on the +X side at the rear.

    Lead 2 mm: 0.01 mm per full step, a quarter of the Tr8x8 17E19S1684MB4's travel per step and four times its force per
    unit torque. Lead angle 5.2 deg: with a trapezoidal flank and mu 0.10 to 0.15 the friction angle is 5.9 to 8.8 deg, so
    the screw does NOT back-drive under a static load (DERIVED, see the vendor file; the Tr8x8 does).
    NOT on the product page and taken from the sister model 17E19S1684MB4-300RS (same 48 mm, 1.68 A body): rotor inertia
    68 g.cm2, 42.3 mm frame maximum, 31 mm hole square, M3 threads 4.5 deep, 22 x 2 pilot. Mass 0.35 kg is the
    predecessor AB2's page figure. Axial (thrust) load rating: NOT STATED (`axial_load_rating_unknown` reports the load).
    Torque-speed curve: none published (the electrical model computes one from the winding)."""
    d = vendor_data("stepperonline_17e19_ab4")
    v, a = d["values"], d["assumed_from_17e19s1684mb4"]
    frame, body_l = a["frame_mm_max"], v["body_length_mm"]["value"]
    pil = a["pilot"]
    cn = a["connector"]
    shape = (Pos(0, 0, -body_l / 2) * Box(frame, frame, body_l)
             + Pos(0, 0, pil["height_mm"] / 2) * Cylinder(pil["dia_mm"] / 2, pil["height_mm"])
             + Pos(frame / 2 + cn["stands_out"] / 2 - 0.5, 0, -body_l + cn["height_from_rear"] / 2)
             * Box(cn["stands_out"] + 1.0, cn["width"], cn["height_from_rear"]))
    h = a["hole_square_mm"] / 2
    holes = [(x, y, 0.0) for x in (-h, h) for y in (-h, h)]
    m_total = v["mass_kg"]["value"]
    m_body = round(m_total - _ab4_screw_mass(AB4_SCREW_ABOVE_FACE), 4)
    sc = v["screw"]
    return Stock(shape, "NEMA17-48-LEADSCREW-TR8x2-330-AB4", f"NEMA 17 lead-screw stepper, Tr8x2 x 330 mm, anti-backlash nut (StepperOnline {AB4})",
                 m_body, material="steel",
                 ratings={"holding_torque_nmm": v["holding_torque_nm"]["value"] * 1000.0, "rotor_inertia_gcm2": a["rotor_inertia_gcm2"],
                          "rotor_inertia_basis": "NOT on the AB4 page: the 17E19S1684MB4-300RS drawing's 68 g.cm2 (same 48 mm, 1.68 A body), assumed",
                          "rated_current_a": v["rated_current_a"]["value"], "phase_resistance_ohm": v["phase_resistance_ohm"]["value"],
                          "phase_inductance_mh": v["phase_inductance_mh"]["value"], "vendor_part": AB4,
                          "lead_mm": sc["lead_mm"], "efficiency": 0.35,
                          "efficiency_source": "typical for a 2 mm-lead trapezoidal screw (the catalogue's leadscrew_t8 figure); NOT stated",
                          "self_locking": True, "self_locking_basis": d["self_locking"]["basis"] + " (DERIVED)",
                          "mass_kg_total": m_total, "mass_note": "0.35 kg is the predecessor AB2-330RA page's figure (the AB4 page gives none); "
                                                                "this body carries it less the drawn screw's mass",
                          "axial_load_rating_n": None,
                          "axial_load_rating_status": "NOT STATED by the maker (product page: no thrust rating; 'Has Torque/Thrust Curve? No')",
                          "torque_curve_status": "no torque-speed curve published: without an electrical model 0.7 x holding torque is "
                                                 "assumed at every speed; with one, the curve comes from the winding figures",
                          "integral_leadscrew": True, "supplied_nut": "anti-backlash nut, dimensions not published (datasheet not fetched)"},
                 interfaces={"mount_holes_m3": holes, "pilot_dia": pil["dia_mm"], "pilot_height": pil["height_mm"],
                             "hole_square": a["hole_square_mm"], "thread_depth": a["thread_depth_min_mm"], "screw_dia": sc["diameter_mm"],
                             "screw_length_above_face": AB4_SCREW_ABOVE_FACE, "connector_side": "+X",
                             "connector": {"stands_out": cn["stands_out"], "width": cn["width"], "height_from_rear": cn["height_from_rear"]}},
                 cost_usd=v["price_usd"]["value"],
                 source=_source("stepperonline_17e19_ab4", "partial", AB4,
                                unverified=("mass_kg", "rotor_inertia_gcm2", "frame_mm_max", "hole_square", "thread_depth", "pilot",
                                            "connector", "axial_load_rating_n", "efficiency", "torque-speed curve"),
                                note="torque, current, resistance, inductance, body length, screw (Tr8x2, 330 mm) and price are the maker's "
                                     "product page; the datasheet PDF was not reachable; body details are the sister 17E19S1684MB4-300RS's"))


@part
def leadscrew_screw_17e19_ab4(length: float = AB4_SCREW_ABOVE_FACE) -> Stock:
    """The integral Tr8x2 screw of the 17E19S1684AB4-330RA above the motor's mounting face. Local frame: axis along Z,
    the mounting face at Z=0, the screw's free end at Z=length. As sold it stands 328 mm above the face (330 nominal,
    assumed like its sister model); a shorter `length` means the builder cuts it (hacksaw, file a 0.5 mm chamfer and clean
    the thread with the nut before fitting) or orders it short (StepperOnline lists a custom-length service; not priced).
    Bought with its motor: no cost, its mass is the screw's own. Lead 2 mm; efficiency 0.35 typical (not stated)."""
    if not 50.0 <= length <= AB4_SCREW_ABOVE_FACE:
        raise ValueError(f"leadscrew_screw_17e19_ab4 length must be 50 to {AB4_SCREW_ABOVE_FACE:g} mm above the face")
    cut = length < AB4_SCREW_ABOVE_FACE - 1e-6
    v = vendor_data("stepperonline_17e19_ab4")["values"]["screw"]
    shape = Pos(0, 0, length / 2) * Cylinder(v["diameter_mm"] / 2, length)
    sku = f"TR8x2-INTEGRAL-{AB4}" + (f"-CUT{length:g}" if cut else "")
    return Stock(shape, sku, f"Tr8x2 integral screw of the {AB4}, {length:g} mm above the motor face" + (" (cut to length by the builder)" if cut else ""),
                 round(_ab4_screw_mass(length), 4), material="steel",
                 ratings={"lead_mm": v["lead_mm"], "efficiency": 0.35, "approximate": True, "integral_with": AB4, "cut_to_length": cut,
                          "efficiency_source": "typical for a 2 mm-lead trapezoidal screw; NOT stated"},
                 interfaces={"screw_tip": [(0.0, 0.0, length)], "length_above_face": length},
                 cost_usd=0.0,
                 source=_source("stepperonline_17e19_ab4", "partial", AB4,
                                unverified=("length above the face (sister model's figure)", "efficiency", "lead accuracy", "material grade"),
                                note="Tr8x2, 8 mm, 330 mm nominal are the maker's product page"))


# ------------------------------------------------------------------ controller
@part
def octopus_v11(drivers: str = "TMC2209") -> Stock:
    """BIGTREETECH Octopus V1.1 controller: 160 x 100 mm PCB, four mounting holes on 150 x 90 mm, EIGHT plug-in stepper
    driver sockets (MOTOR0..MOTOR7; MOTOR2 has two connectors, MOTOR2_1 and MOTOR2_2, on one driver; drivers are NOT
    included), four heater outputs (HE0..HE3), heated bed up to 300 W, six PWM fans, eight endstop / DIAG inputs, a
    'SENSOR' probe port, a Raspberry Pi UART header. 12 or 24 V (logic > 14.1 V); three power inputs (motor, main, bed)
    with common grounds, modelled as one POWER port (run three pairs from the supply, or link them at the terminal).
    Local frame: PCB centred, underside on Z=0 (stand it on >= 5 mm spacers), X along the 160 mm edge, motor connectors
    along +Y, power terminals at -X.
    drivers: the module in every socket. Only "TMC2209" (BIGTREETECH TMC2209 stick, UART) is in the catalogue; buy one per
      driver used: design.bom_extra("DRIVER-BTT-TMC2209", n, 6.0).
    Ports (electrical model): POWER, HB, HE0..HE3, FAN0..FAN5, M0, M1, M2 (+ M2B on the same driver), M3..M7,
      STOP0..STOP7, PROBE, THB, TH0..TH3, PS-ON, RPI (host: 5 V, GND, PD6 RX, PD5 TX). Pins: BTT's pin drawing and
      Klipper's generic-bigtreetech-octopus-v1.1.cfg (one UART pin per socket). Heater and fan current limits are NOT in
      the manual's text: typical values, marked so. Connector positions are approximate (spread along the edges as on the
      pin drawing); the vendor STEP was not loaded, so the envelope height (22 mm with driver modules) is assumed."""
    if drivers not in MANTA_DRIVERS:
        raise ValueError(f"octopus_v11 drivers must be one of {sorted(MANTA_DRIVERS)} (no data for other modules: needed data)")
    d = vendor_data("bigtreetech_octopus_v11")
    v = d["values"]
    W, H = v["board_mm"]["value"]
    T = 1.6
    hx, hy = v["hole_pattern_mm"]["value"][0] / 2, v["hole_pattern_mm"]["value"][1] / 2
    holes = [(x, y, 0.0) for x in (-hx, hx) for y in (-hy, hy)]
    EH = 22.0
    pcb = Pos(0, 0, T / 2) * Box(W, H, T)
    env = Pos(0, 0, T + EH / 2) * Box(W - 1.0, H - 1.0, EH)
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.6, T)
        env -= Pos(x, y, T + EH / 2) * Cylinder(4.0, EH)
    z, up, edge = T + 8.0, (0, 0, 1), (-1, 0, 0)
    xh = dict(connector="JST-XH", max_a=3.0)
    es = dict(logic_v=3.3, pin_max_v=3.6)
    mp = v["motor_pins"]

    def at(fx, fy):
        return ((fx - 0.5) * W, (fy - 0.5) * H, z)

    def drv(k):
        p = mp[f"MOTOR{k}"]
        return {"step": p["step"], "dir": p["dir"], "enable": p["enable"], "uart": p["uart"], "diag": p["diag"], "diag_jumper": f"DIAG{k}"}

    hp, fp, tp, sp = v["heater_pins"], v["fan_pins"], v["thermistor_pins"], v["endstops"]["pins"]
    bed_a = round(v["bed"]["max_w"] / 24.0, 2)
    ports = {
        "POWER": dict(kind="power_in", connector="screw-5.08", max_a=20.0, at=at(0.03, 0.62), dir=edge),
        "HB": dict(kind="heater_out", connector="screw-5.08", max_a=bed_a, pin=hp["HB"], at=at(0.03, 0.22), dir=edge),
        "PS-ON": dict(kind="signal_out", pin=v["ps_on_pin"]["value"], at=at(0.62, 0.55), dir=up, **xh),
        "RPI": dict(kind="host", connector="dupont", max_a=2.0, pin=v["raspberry_pi_header"]["value"], conductors=4, at=at(0.70, 0.80), dir=up),
        "PROBE": dict(kind="endstop_in", logic_v=3.3, pin_max_v=30.0, pin=v["probe_port"]["pin"], at=at(0.90, 0.30), dir=up, **xh),
    }
    for i, k in enumerate(("HE0", "HE1", "HE2", "HE3")):
        ports[k] = dict(kind="heater_out", connector="screw-5.08", max_a=5.0, pin=hp[k], at=at(0.20 + 0.06 * i, 0.04), dir=(0, -1, 0))
    for i, k in enumerate(("FAN0", "FAN1", "FAN2", "FAN3", "FAN4", "FAN5")):
        ports[k] = dict(kind="fan_out", connector="JST-XH", max_a=1.0, pin=fp[k], at=at(0.45 + 0.035 * i, 0.06), dir=up)
    for i in range(8):
        ports[f"STOP{i}"] = dict(kind="endstop_in", **es, pin=sp[f"STOP{i}"], at=at(0.72 + 0.045 * (i % 4), 0.08 if i < 4 else 0.18), dir=up, **xh)
    for i, k in enumerate(("THB", "TH0", "TH1", "TH2", "TH3")):
        ports[k] = dict(kind="thermistor_in", pin=tp["TB" if k == "THB" else "T" + k[2]], at=at(0.78 + 0.04 * i, 0.70), dir=up,
                        pullup_ohm=4700.0, adc_bits=12, **xh)
    for i in range(8):
        ports[f"M{i}"] = dict(kind="stepper_out", pin=drv(i), group=f"M{i}", conductors=4, at=at(0.08 + 0.105 * i + (0.05 if i > 2 else 0.0), 0.95),
                              dir=up, **xh)
    ports["M2B"] = dict(kind="stepper_out", pin=drv(2), group="M2", conductors=4, at=at(0.08 + 0.105 * 2 + 0.05, 0.95), dir=up, **xh)
    dm = MANTA_DRIVERS[drivers]
    rails = v["rails"]
    ratings = {"supply_v": tuple(v["input_v"]["value"]), "input_fuse_a": None, "stepper_drivers": 8, "driver_sockets": 8,
               "driver": dm["driver"], "driver_modules_included": False, "driver_module_sku": dm["sku"],
               "sense_resistor_ohm": dm["sense_resistor_ohm"], "driver_max_rms_a": dm["driver_max_rms_a"],
               "driver_abs_max_rms_a": dm["driver_abs_max_rms_a"], "driver_rds_on_ohm": dm["driver_rds_on_ohm"], "driver_max_v": dm["driver_max_v"],
               "output_resistance_ohm": 0.012, "logic_w": 1.5, "adc_bits": 12, "thermistor_pullup_ohm": 4700.0,
               "rail_5v_max_a": rails["5V_a"], "rail_12v_max_a": rails["12V_a"], "bed_max_w": v["bed"]["max_w"], "max_ambient_c": 60.0,
               "power_inputs": v["power_inputs"]["value"],
               "klipper_mcu": "stm32f446"}      # firmware-in-the-loop dictionary (out_stm32f446/, tools/setup_klipper.sh); some boards carry an F429
    TU = "typical, unverified"
    sources = {"outline_holes": "[BTT] Octopus manual 1.2: 160 x 100 mm, holes 150 x 90 mm (hole diameter not transcribed)",
               "HB.max_a": f"[BTT] manual 8 item 3: beds up to 300 W; {bed_a} A at 24 V DERIVED",
               "HE.max_a / fan max_a": f"5 A per heater, 1 A per fan: {TU} (not in the manual's text)",
               "supply_v": "[BTT] manual 1.1 item 6: 12 V or 24 V; logic needs > 14.1 V; 24 V recommended",
               "power_inputs": "[BTT] manual 2.1: motor, main and bed inputs with common grounds; one POWER port in this model",
               "rail_5v_max_a": "[BTT] manual 2.1: 5 V rail up to 8 A, 12 V up to 4 A, 3.3 V up to 1 A (not recommended at the maximum)",
               "pins": "[BTT] pin drawing (rev 2026-02-01), cross-checked with [KLIP] generic-bigtreetech-octopus-v1.1.cfg",
               "PROBE": "[BTT] manual 2.7: optocoupler input (no BAT85), NPN probes need an external 4k7 pull-up and the pin's pull-down; "
                        "pin_max_v 30 V stands for 'isolated', not a rating; the firmware polarity for it is NOT modelled",
               "connector_positions": f"spread along the edges as on the pin drawing ({TU}); the vendor STEP was not loaded",
               "driver": "[BTT] TMC2209 stick (as manta_m5p); current limits as Klipper's tmc2208.py (CS=31: 1.74 A rms)",
               "input_fuse_a": "replaceable fuses fitted (manual 1.1 item 14); ratings not transcribed",
               "thermistor_pullup_ohm": f"4.7 k ({TU})", "envelope_height": f"22 mm with driver modules ({TU})",
               "max_ambient_c": TU, "logic_w": TU, "output_resistance_ohm": TU, "mass": TU, "cost": TU}
    prod = dict(product="BIGTREETECH Octopus V1.1 (bare board: driver modules to be added)", vendor="BIGTREETECH (Shenzhen Big Tree Technology)",
                part_number="Octopus V1.1", form="assembled board", off_the_shelf=True, custom_pcb=False,
                builder_work=f"plug in one {dm['driver']} module per driver used and set its UART jumpers; remove the DIAG jumpers of "
                             "any STOP input used for a switch or probe; set the fan-voltage jumpers; wire motor, main and bed power")
    from . import electrical as _pe

    return Stock(pcb + env, "CTRL-OCTOPUS-V1.1", "BIGTREETECH Octopus V1.1 control board (8 driver sockets)", 0.15, material="abs",
                 ratings={"electrical": {"kind": "board", "ports": ports, "ratings": ratings, "sources": sources, "product": prod,
                                         "params": {"power_port": "POWER"}},
                          "stepper_drivers": 8, "approximate": True},
                 interfaces={"mount_holes_m3": holes, "standoff_min": 5.0, "size": (W, H), "hole_pattern": tuple(v["hole_pattern_mm"]["value"]),
                             **_pe._ports_to_interfaces(ports)},
                 cost_usd=55.0,
                 # display model (when vendor_cad/inbox/CTRL-OCTOPUS-V1.1.step is present): BTT's V1.0 STEP, accepted by the owner for the
                 # V1.1 (same outline and mounting holes, 2026-11-20). It has no driver modules and its PCB is surfaces only, so the
                 # simulation solid (PCB + a 22 mm envelope with the TMC2209 sticks plugged in) is larger than the CAD's solids
                 model={"inbox": ["CTRL-OCTOPUS-V1.1"], "no_auto_features": True,
                        "provenance": "maker CAD for V1.0, accepted by owner for V1.1, 2026-11-20",
                        "tolerance": {"volume_ratio": (2.0, 12.0), "mass_ratio": (0.2, 10.0)},
                        "protrusions": {"zmin": (3.12, "through-hole pins below the board"),
                                        "zmax": (-7.4, "the simulation envelope includes plugged-in driver modules, not in BTT's CAD"),
                                        "xmax": (2.2, "connector bodies past the board edge"),
                                        "xmin": (0.6, "connector bodies past the board edge")}},
                 source=_source("bigtreetech_octopus_v11", "partial", "Octopus V1.1",
                                unverified=("mass_kg", "mount hole diameter", "connector positions", "heater and fan current limits",
                                            "input fuse ratings", "envelope height", "cost"),
                                note="outline, hole pattern, bed power and rail currents are BIGTREETECH's manual; pins are BTT's pin "
                                     "drawing and Klipper's example config; driver modules are separate purchases"))
