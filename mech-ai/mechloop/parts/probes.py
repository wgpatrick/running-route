"""Bed probes as catalogue parts: OMRON E2E cylindrical inductive proximity sensors.

Figures are OMRON's E2E data sheet (vendor_docs/BED-PROBE_datasheet.pdf; mechloop/parts/vendor/omron_e2e.json, block
`catalogue_models`). What is NOT the maker's is said on each part: the sensing distance on aluminium is read by eye
from a reference chart for small 1 mm plates, repeatability is not in the sheet, the head's mass is estimated.

No microswitch (touch) probe is offered. The only switch data in the repository is OMRON's D2F sheet, and a bare
D2F-01L on a carrier is an endstop: to probe a bed it needs something that lowers and stows it (a servo arm, a dock, a
solenoid pin), and no off-the-shelf module of that kind has vendor data here. One is not invented.
"""
from __future__ import annotations

from build123d import Cylinder, Pos

from . import Stock, _source, part, vendor_data

E2E_MODELS = ("E2E-X8MD1", "E2E-X5ME1", "E2E-X10ME1", "E2E-X5E1")
NUT_GAP = 0.0          # nuts sit directly on the clamped plate (the toothed washer is under the rear nut)


@part
def probe_omron_e2e(model: str = "E2E-X5ME1", clamp: tuple | None = None) -> Stock:
    """OMRON E2E inductive proximity sensor as a bed probe. Local frame: sensing face on Z=0 looking along -Z (at the
    bed), barrel along +Z, cable leaving the top.

    model:
      "E2E-X5ME1"   M12 unshielded, NPN three-wire NO, 5 mm on iron, about 1.6 mm on aluminium
      "E2E-X10ME1"  M18 unshielded, NPN three-wire NO, 10 mm on iron, about 3.0 mm on aluminium
      "E2E-X5E1"    M18 SHIELDED (flush-mountable), NPN three-wire NO, 5 mm on iron, about 1.75 mm on aluminium
      "E2E-X8MD1"   M12 unshielded, DC TWO-WIRE NO, 8 mm on iron, about 2.8 mm on aluminium. A two-wire sensor cannot be
                    read by a logic input directly (see AGENT.md); prefer a three-wire type.
    clamp: (z_lo, z_hi), the two faces of the plate or tab the sensor is clamped in, in this frame (mm above the
      sensing face). The two nuts supplied with the sensor are drawn against those faces (4 mm each, a 1 mm toothed
      washer under the upper one). The plate needs a clearance hole for the thread (12.5 / 18.5 mm). Without `clamp`
      the part has no nuts and the subsystems verifier reports that its mounting is not declared.

    Mounting rule (data sheet p.25), checked by the subsystems verifier: an UNSHIELDED sensor must have its sensing
    face `l` mm proud of any metal (M12 15, M18 22) with a cylinder `d` mm in diameter round the head free of metal
    (M12 40, M18 55): interfaces["mounting"]. So clamp z_lo >= l when the plate is metal. A SHIELDED sensor may sit
    flush in metal. The sensor's own nuts are not counted.
    Sensing: switching distance +/-10 % unit to unit and a further +/-10 % with temperature (-25 to 70 degC); the
    probe checks use both."""
    if model not in E2E_MODELS:
        raise ValueError(f"probe_omron_e2e model must be one of {E2E_MODELS}")
    v = vendor_data("omron_e2e")["catalogue_models"][model]
    b, sm = v["body_mm"], v["surrounding_metal_mm"]
    dia = v["thread_dia_mm"]
    z_thread0 = b["head_length"]
    z_thread1 = z_thread0 + b["threaded_length"]
    z_body1 = z_thread0 + b["body_length"]          # head taken as in front of the drawing's body length (the longer reading)
    shape = Pos(0, 0, (z_thread0 + z_body1) / 2) * Cylinder(dia / 2, z_body1 - z_thread0)
    if b["head_length"] > 0:
        shape += Pos(0, 0, z_thread0 / 2) * Cylinder(b["head_dia"] / 2, z_thread0)
    shape += Pos(0, 0, z_body1 + b["cable_protector"] / 2) * Cylinder(dia / 2 - 2.0, b["cable_protector"])
    nut_r, nut_t, wash = b["nut_across_flats"] / 2, b["nut_thickness"], b["washer"]
    nuts = None
    if clamp is not None:
        z_lo, z_hi = float(clamp[0]), float(clamp[1])
        if not z_lo < z_hi:
            raise ValueError("probe_omron_e2e clamp must be (z_lo, z_hi) with z_lo < z_hi")
        if z_lo - nut_t < z_thread0 - 1e-9 or z_hi + wash + nut_t > z_thread1 + 1e-9:
            raise ValueError(f"probe_omron_e2e({model!r}): a plate from {z_lo:g} to {z_hi:g} mm with a {nut_t:g} mm nut each side "
                             f"(and a {wash:g} mm washer) does not fit on the thread, which runs from {z_thread0:g} to "
                             f"{z_thread1:g} mm above the sensing face")
        # the nuts as round collars of the across-flats size: what clamps the plate
        nuts = [(z_lo - nut_t, z_lo), (z_hi, z_hi + wash + nut_t)]
        for a, c in nuts:
            shape += Pos(0, 0, (a + c) / 2) * (Cylinder(nut_r, c - a) - Cylinder(dia / 2, c - a))
    two_wire = v["wires"] == 2
    sheet = "OMRON E2E data sheet CSM_E2E_DS_E_12_4"
    al_src = (f"{sheet}, chart 'Influence of Sensing Object Size and Material' ({'p.17' if two_wire else 'p.18'}): REFERENCE value read "
              f"by eye (+/-0.15 mm) for a 1 mm aluminium plate; {v['aluminium_note']}. A 6 mm bed plate 200 mm square is outside the chart")
    rt = {"switching_distance_steel_mm": v["sensing_distance_mm"], "switching_distance_aluminium_mm": v["aluminium_mm"],
          "switching_distance_aluminium_range_mm": list(v["aluminium_range_mm"]),
          "switching_distance_tolerance_frac": v["tolerance_frac"], "temperature_drift_frac": v["temperature_drift_frac"],
          "differential_travel_frac": v["differential_travel_frac"], "repeatability_mm": 0.01,
          "supply_v_min": v["supply_v"][0], "supply_v_max": v["supply_v"][1], "output": v["output"],
          "max_ambient_c": 70.0 if two_wire else v["ambient_c"][1], "drift_rated_to_c": 70.0}
    src = {"switching_distance_steel_mm": f"{sheet}: {v['sensing_distance_mm']:g} mm +/-10 % on the standard iron target",
           "switching_distance_aluminium_mm": al_src,
           "switching_distance_tolerance_frac": f"{sheet}: sensing distance +/-10 %",
           "temperature_drift_frac": f"{sheet}: temperature influence +/-10 % of the sensing distance at 23 degC over -25 to 70 degC",
           "repeatability_mm": "ASSUMED 0.01 mm (one standard deviation): the data sheet gives no repeatability",
           "supply_v_min": f"{sheet}: operating voltage 10 to 30 VDC", "supply_v_max": f"{sheet}: operating voltage 10 to 30 VDC",
           "output": f"{sheet}: model code and I/O circuit", "max_ambient_c": f"{sheet}: operating temperature"}
    if two_wire:
        rt.update({"leakage_current_ma_max": v["leakage_current_ma_max"], "min_load_current_ma": v["load_current_ma"][0],
                   "max_load_current_ma": v["load_current_ma"][1], "residual_voltage_v_max": v["residual_voltage_v_max"],
                   "internal_pullup": False, "supply_current_a": 0.0})
        work = ("two leads, in series with a load: brown to +V, blue to the load. It needs a load of at least 3 mA and an "
                "interface stage between it and a logic input (declare params['interface']); it cannot go straight on an endstop pin")
        desc = "DC two-wire, normally open"
    else:
        rt.update({"internal_pullup": True, "internal_pullup_ma": list(v["internal_pullup_ma"]), "output_max_a": v["load_current_ma_max"] / 1000.0,
                   "supply_current_a": v["current_consumption_ma_max"] / 1000.0, "residual_voltage_v_max": v["residual_voltage_v_max"]})
        src["internal_pullup"] = (f"{sheet} p.21 output circuit: a constant-current source of 1.5 to 3 mA from +V to the output (black "
                                  "lead), so the output sits at the supply voltage when the sensor is not switched")
        work = ("brown to the 24 V rail, blue to 0 V, black (output) to the endstop / probe input through a BAT85-class diode, "
                "cathode to the sensor, because the output is pulled up to the supply inside the sensor (declare "
                "params['series_diode']=True); crimp a 3-way JST-XH")
        desc = "NPN three-wire, normally open"
    kind = "shielded" if v["shielded"] else "unshielded"
    tpl = {"kind": "probe", "ports": {"out": dict(kind="probe", connector="JST-XH", max_a=1.0, conductors=v["conductors"])},
           "ratings": rt, "sources": src, "params": {},
           "product": dict(product=f"OMRON {model} 2M inductive proximity sensor, {v['thread']} {kind}, {v['sensing_distance_mm']:g} mm, {desc}",
                           vendor="OMRON", part_number=f"{model} 2M", form="component", off_the_shelf=True, custom_pcb=False, builder_work=work)}
    mass = {12.0: 0.030, 18.0: 0.070}[dia]
    mounting = {"thread": v["thread"], "thread_dia": dia, "hole_dia": dia + 0.5, "shielded": bool(v["shielded"]),
                "head_proud_of_metal_l": sm["l"], "metal_free_dia_d": sm["d"], "to_facing_metal_m": sm["m"],
                "between_sensors_n": sm["n"], "thread_z": (z_thread0, z_thread1), "clamp": None if clamp is None else (float(clamp[0]), float(clamp[1])),
                "nut_across_flats": b["nut_across_flats"], "nut_over_corners": b["nut_over_corners"], "nut_thickness": nut_t,
                "source": f"{sheet} p.25 'Influence of Surrounding Metal' and p.27-28 dimensions"}
    return Stock(shape, f"PROBE-OMRON-{model}", f"OMRON {model} inductive bed probe ({v['thread']} {kind}, {desc}, with its two nuts)",
                 mass, material="brass", ratings={"electrical": tpl},
                 interfaces={"sensing_face": [(0.0, 0.0, 0.0)], "cable_exit": [(0.0, 0.0, z_body1 + b["cable_protector"])],
                             "axis_point": [(0.0, 0.0, 10.0)], "mounting": mounting, "length": z_body1 + b["cable_protector"]},
                 cost_usd=25.0,
                 source=_source("omron_e2e", "partial", f"{model} 2M",
                                unverified=("mass_kg", "switching_distance_aluminium_mm", "repeatability_mm", "overall length"),
                                note="ratings, thread, nuts and surrounding-metal clearances are OMRON's. Aluminium distance: chart "
                                     "reading for a small 1 mm plate. Mass: estimated for the barrel, nuts and a short cable (packed "
                                     f"with 2 m of cable: {v['packed_weight_g']} g). Length: the unthreaded head is taken as in front "
                                     "of the drawing's body length"))
