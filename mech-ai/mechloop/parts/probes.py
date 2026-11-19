"""Bed probes as catalogue parts: OMRON E2E cylindrical inductive proximity sensors.

Figures are OMRON's E2E data sheet (vendor_docs/BED-PROBE_datasheet.pdf; mechloop/parts/vendor/omron_e2e.json, block
`catalogue_models`). What is NOT the maker's is said on each part: the sensing distance on aluminium is read by eye
from a reference chart for small 1 mm plates, repeatability is not in the sheet, the head's mass is estimated.

No microswitch (touch) probe is offered. The only switch data in the repository is OMRON's D2F sheet, and a bare
D2F-01L on a carrier is an endstop: to probe a bed it needs something that lowers and stows it (a servo arm, a dock, a
solenoid pin), and no off-the-shelf module of that kind has vendor data here. One is not invented.
"""
from __future__ import annotations

from build123d import Cylinder, Location, Plane, Pos

from . import Stock, _source, part, place, vendor_data

E2E_MODELS = ("E2E-X8MD1", "E2E-X5ME1", "E2E-X10ME1", "E2E-X5E1", "E2B-M12KS04-WP-C1")
NUT_GAP = 0.0          # nuts sit directly on the clamped plate (the toothed washer is under the rear nut)


@part
def probe_omron_e2e(model: str = "E2E-X5ME1", clamp: tuple | None = None, nuts: str = "fused") -> Stock:
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
    nuts: "fused" (default, as before) draws the two nuts as part of the sensor: one rigid part, which can only be slid
      sideways into a slot (it cannot enter a closed hole with a nut on each side of the plate, and the assembly check
      says so). "separate" is how the sensor is really fitted: the part is the barrel alone, and the two nuts are their
      own catalogue parts (`e2e_nut`), placed with `add_probe_nuts(design, "<probe>")` after the probe: one nut comes
      off, the barrel goes through a closed clearance hole, the nut goes back on. Use "separate" for a closed hole.

    Mounting rule (data sheet p.25), checked by the subsystems verifier: an UNSHIELDED sensor must have its sensing
    face `l` mm proud of any metal (M12 15, M18 22) with a cylinder `d` mm in diameter round the head free of metal
    (M12 40, M18 55): interfaces["mounting"]. So clamp z_lo >= l when the plate is metal. A SHIELDED sensor may sit
    flush in metal. The sensor's own nuts are not counted.
    Sensing: switching distance +/-10 % unit to unit and a further +/-10 % with temperature (-25 to 70 degC); the
    probe checks use both."""
    if model not in E2E_MODELS:
        raise ValueError(f"probe_omron_e2e model must be one of {E2E_MODELS}")
    if nuts not in ("fused", "separate"):
        raise ValueError("probe_omron_e2e nuts must be 'fused' or 'separate'")
    if nuts == "separate" and clamp is None:
        raise ValueError("probe_omron_e2e(nuts='separate') needs clamp=(z_lo, z_hi): where the two nuts sit")
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
    if clamp is not None:
        z_lo, z_hi = float(clamp[0]), float(clamp[1])
        if not z_lo < z_hi:
            raise ValueError("probe_omron_e2e clamp must be (z_lo, z_hi) with z_lo < z_hi")
        if z_lo - nut_t < z_thread0 - 1e-9 or z_hi + wash + nut_t > z_thread1 + 1e-9:
            raise ValueError(f"probe_omron_e2e({model!r}): a plate from {z_lo:g} to {z_hi:g} mm with a {nut_t:g} mm nut each side "
                             f"(and a {wash:g} mm washer) does not fit on the thread, which runs from {z_thread0:g} to "
                             f"{z_thread1:g} mm above the sensing face")
        # the nuts as round collars of the across-flats size: what clamps the plate
        if nuts == "fused":
            for a, c in [(z_lo - nut_t, z_lo), (z_hi, z_hi + wash + nut_t)]:
                shape += Pos(0, 0, (a + c) / 2) * (Cylinder(nut_r, c - a) - Cylinder(dia / 2, c - a))
    two_wire = v["wires"] == 2
    sheet = v.get("sheet", "OMRON E2E data sheet CSM_E2E_DS_E_12_4")     # v11: the E2B-M12KS04-WP-C1 record names its own basis
    al_src = (f"{sheet}, chart 'Influence of Sensing Object Size and Material' ({'p.17' if two_wire else 'p.18'}): REFERENCE value read "
              f"by eye (+/-0.15 mm) for a 1 mm aluminium plate; {v['aluminium_note']}. A 6 mm bed plate 200 mm square is outside the chart")
    rt = {"switching_distance_steel_mm": v["sensing_distance_mm"], "switching_distance_aluminium_mm": v["aluminium_mm"],
          "switching_distance_aluminium_range_mm": list(v["aluminium_range_mm"]),
          "switching_distance_tolerance_frac": v["tolerance_frac"], "temperature_drift_frac": v["temperature_drift_frac"],
          "differential_travel_frac": v["differential_travel_frac"], "repeatability_mm": 0.01,
          "supply_v_min": v["supply_v"][0], "supply_v_max": v["supply_v"][1], "output": v["output"],
          "max_ambient_c": 70.0 if two_wire else v["ambient_c"][1], "drift_rated_to_c": 70.0}
    if v.get("temperature_drift_full_range_frac"):      # three-wire types: +/-15 % over the whole -40 to 85 degC
        rt["temperature_drift_full_range_frac"] = v["temperature_drift_full_range_frac"]
    src = {"switching_distance_steel_mm": f"{sheet}: {v['sensing_distance_mm']:g} mm +/-10 % on the standard iron target",
           "switching_distance_aluminium_mm": al_src,
           "switching_distance_tolerance_frac": f"{sheet}: sensing distance +/-10 %",
           "temperature_drift_frac": f"{sheet}: temperature influence +/-10 % of the sensing distance at 23 degC over -25 to 70 degC",
           "repeatability_mm": "ASSUMED 0.01 mm (one standard deviation): the data sheet gives no repeatability",
           "supply_v_min": f"{sheet}: operating voltage 10 to 30 VDC", "supply_v_max": f"{sheet}: operating voltage 10 to 30 VDC",
           "output": f"{sheet}: model code and I/O circuit",
           "max_ambient_c": (f"{sheet} p.13, DC two-wire: ambient operating -25 to 70 degC" if two_wire else
                             f"{sheet} p.16, DC three-wire: ambient operating -40 to 85 degC; the +/-10 % drift figure holds to 70 degC, "
                             "+/-15 % over the whole range")}
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
    if nuts == "separate":      # the estimate includes the two nuts: they are their own parts now
        mass -= _nut_mass(dia, nut_r, nut_t) + _nut_mass(dia, nut_r, nut_t + wash)
    mounting = {"thread": v["thread"], "thread_dia": dia, "hole_dia": dia + 0.5, "shielded": bool(v["shielded"]),
                "head_proud_of_metal_l": sm["l"], "metal_free_dia_d": sm["d"], "to_facing_metal_m": sm["m"],
                "between_sensors_n": sm["n"], "thread_z": (z_thread0, z_thread1), "clamp": None if clamp is None else (float(clamp[0]), float(clamp[1])),
                "nuts": nuts, "model": model, "washer": wash,
                "nut_across_flats": b["nut_across_flats"], "nut_over_corners": b["nut_over_corners"], "nut_thickness": nut_t,
                "source": f"{sheet} p.25 'Influence of Surrounding Metal' and p.27-28 dimensions"}
    return Stock(shape, f"PROBE-OMRON-{model}", f"OMRON {model} inductive bed probe ({v['thread']} {kind}, {desc}, "
                 + ("with its two nuts)" if nuts == "fused" else "barrel; its two nuts are separate parts)"),
                 mass, material="brass", ratings={"electrical": tpl},
                 interfaces={"sensing_face": [(0.0, 0.0, 0.0)], "cable_exit": [(0.0, 0.0, z_body1 + b["cable_protector"])],
                             "axis_point": [(0.0, 0.0, 10.0)], "mounting": mounting, "length": z_body1 + b["cable_protector"]},
                 cost_usd=float(v.get("price_usd", 25.0)),
                 # v11: OMRON's own STEP (vendor_cad/inbox/PROBE-OMRON-E2E-X5ME1.step) is 3 mm longer at the cable end than
                 # this solid's reading of the drawing; the face, the thread and the diameters agree
                 model={"protrusions": {"zmax": (3.2, "OMRON's STEP: the cable protector ends 3 mm further than the catalogue's reading of the drawing")},
                        "inbox": [model]},     # v11: a file named after the bare model (E2B-M12KS04-WP-C1.step) is picked up too
                 source=_source("omron_e2e", "partial", f"{model} 2M",
                                unverified=("mass_kg", "switching_distance_aluminium_mm", "repeatability_mm", "overall length"),
                                note="ratings, thread, nuts and surrounding-metal clearances are OMRON's. Aluminium distance: chart "
                                     "reading for a small 1 mm plate. Mass: estimated for the barrel, nuts and a short cable (packed "
                                     f"with 2 m of cable: {v['packed_weight_g']} g). Length: the unthreaded head is taken as in front "
                                     "of the drawing's body length"))


BRASS_G_MM3 = 8.5e-3


def _nut_mass(dia: float, nut_r: float, t: float) -> float:
    """kg of a brass collar of the nut's across-flats size (the drawn solid)."""
    import math

    return math.pi * (nut_r ** 2 - (dia / 2) ** 2) * t * BRASS_G_MM3 / 1000.0


@part
def e2e_nut(model: str = "E2E-X5ME1", washer: bool = False) -> Stock:
    """One of the two clamping nuts supplied with an OMRON E2E sensor (M12 x 1: 17 across flats; M18 x 1: 24; 4 thick).
    Local frame: bearing face on Z=0, body along +Z. washer=True adds the 1 mm toothed washer under it (the rear nut).
    Drawn, like the fused nuts, as a round collar of the across-flats size. Not bought separately: it comes with the
    sensor (cost 0). Place the pair with `add_probe_nuts`."""
    if model not in E2E_MODELS:
        raise ValueError(f"e2e_nut model must be one of {E2E_MODELS}")
    v = vendor_data("omron_e2e")["catalogue_models"][model]
    b, dia = v["body_mm"], v["thread_dia_mm"]
    t = b["nut_thickness"] + (b["washer"] if washer else 0.0)
    nut_r = b["nut_across_flats"] / 2
    shape = Pos(0, 0, t / 2) * (Cylinder(nut_r, t) - Cylinder(dia / 2, t))
    from build123d import RegularPolygon, extrude

    # display model: a hexagon of OMRON's across-flats size and thickness with the thread's bore (the toothed washer,
    # where there is one, as a ring of the same size under it); the simulation solid stays the round collar
    w = b["washer"] if washer else 0.0
    detail = Pos(0, 0, w) * extrude(RegularPolygon(nut_r, 6, major_radius=False), b["nut_thickness"]) - Pos(0, 0, t / 2) * Cylinder(dia / 2, t)
    if washer:
        detail = detail + Pos(0, 0, w / 2) * (Cylinder(nut_r, w) - Cylinder(dia / 2, w))
    return Stock(shape, f"NUT-OMRON-E2E-M{dia:g}" + ("-W" if washer else ""),
                 f"clamping nut of an OMRON E2E {v['thread']} sensor" + (" with its toothed washer" if washer else "") + " (supplied with the sensor)",
                 _nut_mass(dia, nut_r, t), material="brass",
                 interfaces={"across_flats": b["nut_across_flats"], "thickness": t, "thread_dia": dia},
                 cost_usd=0.0, detail=detail,
                 model={"kind": "generated to standard", "source": "hexagon generated from OMRON's drawing dimensions (across flats, "
                        "thickness; p.27-28 of the E2E data sheet); chamfers and thread not drawn; placeholder for OMRON's CAD",
                        "protrusions": {k: (1.31, "the hexagon's corners (the simulation solid is a round collar of the across-flats size)")
                                        for k in ("xmin", "xmax")},
                        "tolerance": {"volume_ratio": (0.7, 1.6), "mass_ratio": (0.5, 2.0)}},
                 source=_source("omron_e2e", "partial", f"{model} 2M (nut)", unverified=("mass_kg",),
                                note="across flats and thickness are OMRON's (p.27-28); drawn round; mass from the drawn solid in brass"))


def add_probe_nuts(design, probe: str) -> tuple:
    """Place the two nuts of a probe made with `probe_omron_e2e(..., clamp=(z_lo, z_hi), nuts="separate")` and already
    placed in the design: `<probe>_nut_front` under the plate (towards the sensing face) and `<probe>_nut_rear` above it
    with the toothed washer, each joined to the probe as a thread. The plate between them still needs
    `design.join(probe, plate, "clamped by its two nuts")`. Returns the two components."""
    import numpy as np

    pc = design.get(probe)
    mt = (pc.meta.get("interfaces") or {}).get("mounting") or {}
    if mt.get("nuts") != "separate" or not mt.get("clamp") or not pc.meta.get("placement"):
        raise ValueError(f"add_probe_nuts: '{probe}' is not a placed probe_omron_e2e(..., clamp=..., nuts='separate')")
    P = np.array(pc.meta["placement"], dtype=float)
    o, z = P[:, 3], P[:, 2]
    z_lo, z_hi = mt["clamp"]
    out = []
    for tag, zc, sgn, washer in (("front", z_lo, -1.0, False), ("rear", z_hi, 1.0, True)):
        loc = Location(Plane(origin=tuple(o + zc * z), z_dir=tuple(sgn * z)))
        c = place(design, f"{probe}_nut_{tag}", e2e_nut(mt["model"], washer=washer), loc, body=pc.body, probe_nut_of=probe)
        design.join(c.name, probe, "thread")
        out.append(c)
    return tuple(out)
