"""Electrical verifier: is everything wired, can the supply and every wire carry it, do the heaters reach
temperature and fail safe (by simulation), do the steppers have torque at speed, and do the looms fit the CAD.

Every check runs from the design's own `design.electrical` declaration (mechloop.electrical). A check that
cannot run is an error, never a pass."""
from __future__ import annotations

import json
import math
import traceback
from pathlib import Path

import numpy as np
from build123d import Vertex

from .. import electrical as E
from ..geom import forward_kinematics
from ..model import Design
from ..report import VerifierResult, timed

ELECTRIC_SKU = ("NEMA", "FAN", "ENDSTOP", "EXTRUDER", "CTRL", "PSU", "HEATER", "THERMISTOR", "INLET", "RELAY", "HOST", "MOSFET", "TCO")
OUT_ROOT = "out"


def verify_electrical(design: Design) -> VerifierResult:
    r = VerifierResult("electrical")
    el = getattr(design, "electrical", None)
    if el is None:
        r.skipped = "design.electrical is not declared: nothing electrical was verified"
        return r
    with timed(r):
        m: dict = {}
        ctx: dict = {"design": design, "el": el}
        E.axis_motors(el, design)
        for name, fn in (("completeness", _completeness), ("off_the_shelf", _off_the_shelf), ("circuit", _circuit), ("wires", _wires), ("mains", _mains),
                         ("steppers", _steppers), ("heaters", _heaters), ("physical", _physical), ("thermal", _bay_and_motors),
                         ("artifacts", _artifacts)):
            try:
                fn(ctx, r, m)
            except Exception as e:   # a check that cannot run fails
                r.add("error", "check_crashed", f"Electrical check '{name}' could not run: {type(e).__name__}: {e}",
                      check=name, trace=traceback.format_exc()[-700:])
        r.metrics = m
        r.add("info", "electrical_not_modelled",
              "Not modelled: EMC and noise coupling, firmware bugs, crimp and solder quality, connector wear, real PID "
              "autotune on the real heater, heater tolerance (+/-10 %), mains transients. See docs/ELECTRICAL.md.")
    return r


# ====================================================================== completeness
def _completeness(ctx, r, m):
    design, el = ctx["design"], ctx["el"]
    comps = {c.name: c for c in design.components}
    fw = el.firmware or {}
    used: dict = {}
    for w in el.wires:
        ends = []
        for ref in (w.a, w.b):
            dev, port = el.port(ref)
            if port is None:
                r.add("error", "wire_unknown_port", f"Wire '{w.name}' ends at '{ref}', which is not a port of any device.",
                      wire=w.name, port=ref, hint="Use '<device>.<port>'; the device's ports are in its catalog part.")
            else:
                used.setdefault(ref, []).append(w.name)
                ends.append((ref, dev, port))
        for ln in w.via:
            if ln not in el.looms:
                r.add("error", "wire_unknown_loom", f"Wire '{w.name}' is routed via loom '{ln}', which is not declared.", wire=w.name)
        if len(ends) == 2:
            (ra, da, pa), (rb, db, pb) = ends
            if pb.kind not in E.COMPATIBLE.get(pa.kind, set()):
                r.add("error", "incompatible_ports",
                      f"Wire '{w.name}' joins {ra} ({pa.kind}) to {rb} ({pb.kind}); these do not belong together.",
                      wire=w.name, a=pa.kind, b=pb.kind, hint=f"A {pa.kind} port takes: {sorted(E.COMPATIBLE.get(pa.kind, []))}.")
            for ref, port, override in ((ra, pa, w.connector_a), (rb, pb, w.connector_b)):
                if w.conductors < min(port.conductors, 4) and port.kind not in ("pe", "series", "mains_in", "mains_out", "power_in", "power_out"):
                    r.add("error", "too_few_conductors", f"Wire '{w.name}' has {w.conductors} conductors; {ref} needs {port.conductors}.",
                          wire=w.name, port=ref)
                cn = override or port.connector
                lim = E.CONNECTOR_MIN_AWG.get(cn)
                if lim is not None and w.awg < lim:
                    r.add("error", "wire_too_thick_for_connector",
                          f"Wire '{w.name}' is AWG {w.awg}; a {cn} contact at {ref} takes AWG {lim} or thinner.", wire=w.name,
                          port=ref, awg=w.awg, connector_max_awg=lim,
                          hint="Use a thinner wire if the current allows, or land it on a screw terminal / larger connector.")
    for ref, ws in used.items():
        dev, port = el.port(ref)
        if len(ws) > 1 and not port.multi:
            r.add("error", "port_used_twice", f"Port {ref} has {len(ws)} wires on it: {ws}.", port=ref, wires=ws,
                  hint="One wire per port; use another output, or a port declared for several lugs (a stud or bus).")
    # every load, sensor and switch is wired to something that can drive / read it
    need = {"stepper": "stepper_out", "heater": "heater_out", "thermistor": "thermistor_in", "fan": "fan_out", "endstop": "endstop_in"}
    wired_to_board = {}
    for d in el.devices.values():
        if d.kind not in need:
            continue
        pn = next((p.name for p in d.ports.values() if p.kind == d.kind), None)
        wires, series, src = E.trace_supply(el, f"{d.name}.{pn}") if pn else ([], [], None)
        sp = el.port(src)[1] if src else None
        if sp is None or sp.kind != need[d.kind]:
            r.add("error", "device_not_wired",
                  f"{d.kind.capitalize()} '{d.name}' is not wired to a {need[d.kind]} port"
                  + (f" (it ends at {src})." if src else "."), device=d.name,
                  hint=f"Add el.wire(name, '<board>.<{need[d.kind]} port>', '{d.name}.{pn}', awg, via=[looms]).")
        else:
            wired_to_board[d.name] = src
    m["connections"] = wired_to_board
    # every electrical CAD part is in the model, and every device has a CAD part that is held
    have = {d.component for d in el.devices.values() if d.component}
    for c in design.components:
        if (isinstance(c.ratings.get("electrical"), (dict, bool)) and c.ratings.get("electrical")) or \
                any((c.sku or "").startswith(p) for p in ELECTRIC_SKU):
            if c.name not in have:
                r.add("error", "electric_part_not_in_model", f"{c.name} ({c.sku}) is an electrical part but no device represents it.",
                      part=c.name, hint="Add it with mechloop.parts.electrical.device_from(el, design, part) and wire it.")
    held = set()
    for pair in design.joins:
        held |= set(pair)
    for f in design.fasteners:
        held |= set(f.clamps) | {f.name}
    for c in design.components:
        held |= set(c.meta.get("threads_into", []))
    for d in el.devices.values():
        if not d.component or d.component not in comps:
            r.add("error", "device_without_cad", f"Device '{d.name}' ({d.kind}) has no CAD part"
                  + (f": '{d.component}' is not in the design." if d.component else "."), device=d.name,
                  hint="Place its catalog part in the design so its volume, mass, mounting and collisions are checked.")
        elif d.component not in held:
            r.add("error", "device_not_fastened", f"Device '{d.name}': its part '{d.component}' is not screwed, clamped or bonded to anything.",
                  device=d.name, part=d.component)
    # firmware needs
    heaters = fw.get("heaters") or {}
    for d in el.devices.values():
        if d.kind == "heater" and not any(h.get("heater") == d.name for h in heaters.values()):
            r.add("error", "heater_not_in_firmware", f"Heater '{d.name}' is not controlled by any firmware heater.", device=d.name)
    for hn, hc in heaters.items():
        sd = el.devices.get(hc.get("sensor") or "")
        if sd is None or sd.kind != "thermistor" or sd.name not in wired_to_board:
            r.add("error", "heater_without_thermistor",
                  f"Firmware heater '{hn}' has no thermistor wired to a thermistor input: it cannot be controlled or protected.",
                  heater=hn, hint="Add the sensor device, wire it to a TH input and name it in firmware['heaters'][...]['sensor'].")
        if hc.get("heater") not in el.devices:
            r.add("error", "heater_missing", f"Firmware heater '{hn}' names heater device '{hc.get('heater')}', which does not exist.", heater=hn)
    homed = {e.get("joint"): e for e in design.endstops}
    sw_dev = {d.component: d for d in el.devices.values() if d.kind == "endstop"}
    for ax in ("x", "y", "z"):
        jn = (design.printer or {}).get(ax)
        if not jn:
            continue
        st = (fw.get("steppers") or {}).get(jn) or {}
        if not st.get("motors") or st.get("unwired_components") or any(mn not in wired_to_board for mn in st.get("motors", [])):
            r.add("error", "axis_without_driver", f"Axis {jn}: not every motor of its drive is wired to a stepper driver "
                  f"(motors {st.get('motors')}, not in the model {st.get('unwired_components')}).", joint=jn)
        e = homed.get(jn)
        if e is None:
            r.add("error", "axis_without_endstop", f"Axis {jn} has neither an endstop nor sensorless homing declared.", joint=jn)
        elif not e.get("sensorless"):
            d = sw_dev.get(e.get("switch"))
            if d is None or d.name not in wired_to_board:
                r.add("error", "endstop_not_wired", f"Axis {jn}: endstop switch '{e.get('switch')}' is not wired to an endstop input.", joint=jn)
    if design.printer and "extruder" in heaters:
        ex = (fw.get("steppers") or {}).get("extruder") or {}
        if not ex.get("motors") or any(mn not in wired_to_board for mn in ex["motors"]):
            r.add("error", "axis_without_driver", "The extruder motor is not wired to a stepper driver.", joint="extruder")
    boards = [d for d in el.devices.values() if d.kind == "board"]
    for b in boards:
        _, _, src = E.trace_supply(el, f"{b.name}.{b.params.get('power_port', 'POWER')}")
        sd = el.port(src)[0] if src else None
        if sd is None or sd.kind != "psu":
            r.add("error", "board_not_powered", f"Board '{b.name}' power input is not wired to the supply.", device=b.name)
    if fw.get("kind", "klipper") == "klipper":
        host = next((d for d in el.devices.values() if d.kind == "host"), None)
        if host is None or not any(el.wires_at(f"{host.name}.{p}") for p in host.ports):
            r.add("error", "no_host", "Klipper firmware needs a host computer wired to the board; none is declared and wired.",
                  hint="Add a host (raspberry_pi_zero2w) and wire it to the board's serial header, or choose firmware that runs on the board alone.")
    m["devices"] = {k: sum(1 for d in el.devices.values() if d.kind == k) for k in sorted({d.kind for d in el.devices.values()})}
    m["wires"] = len(el.wires)


# ====================================================================== off the shelf: no custom PCBs
def off_the_shelf_table(el) -> list:
    """One row per electrical element: what it physically is and what the builder still does by hand."""
    rows = []
    for d in el.devices.values():
        p = d.product or {}
        rows.append({"element": d.name, "kind": d.kind, "cad_part": d.component, "product": p.get("product"), "vendor": p.get("vendor"),
                     "part_number": p.get("part_number"), "form": p.get("form"), "off_the_shelf": p.get("off_the_shelf"),
                     "custom_pcb": p.get("custom_pcb"), "builder_work": p.get("builder_work")})
    rows.append({"element": "wiring", "kind": "cable", "cad_part": None,
                 "product": "hook-up wire by the metre (gauges and insulation in the BOM), JST-XH housings and crimps, ferrules, "
                            "ring and faston terminals, braided sleeve, cable ties", "vendor": "commodity", "part_number": None,
                 "form": "cable", "off_the_shelf": True, "custom_pcb": False,
                 "builder_work": "cut each wire to the length in wiring.csv, strip, crimp the connector named for each end, sleeve and tie the looms"})
    return rows


def _off_the_shelf(ctx, r, m):
    el = ctx["el"]
    rows = off_the_shelf_table(el)
    custom, unknown, generic = [], [], []
    for row in rows:
        if not row["product"] or row["off_the_shelf"] is None or row["custom_pcb"] is None:
            unknown.append(row["element"])
            r.add("error", "product_not_identified",
                  f"Electrical element '{row['element']}' ({row['kind']}) does not say what purchasable product it is.", device=row["element"],
                  hint="Give the device a product record: Device(..., product={'product', 'vendor', 'part_number', 'form', "
                       "'off_the_shelf', 'custom_pcb', 'builder_work'}); catalog parts carry one.")
        elif row["custom_pcb"] or not row["off_the_shelf"]:
            custom.append(row["element"])
            r.add("error", "custom_electronics_required",
                  f"Electrical element '{row['element']}' is not an off-the-shelf product"
                  + (" and needs a custom PCB" if row["custom_pcb"] else "") + f": {row['product']}.", device=row["element"],
                  hint="Replace it with a stock board or module (e.g. an external MOSFET module or SSR for a load the "
                       "control board cannot carry).")
        elif row["part_number"] is None and row["kind"] != "cable":
            generic.append(row["element"])
    if generic:
        r.add("info", "commodity_parts_without_part_number",
              f"{len(generic)} elements are commodity parts with no single vendor part number fixed: {generic}. "
              "Their ratings are class values (see sources); fix a vendor part before purchase.")
    m["off_the_shelf"] = {"custom_pcbs_needed": sum(1 for row in rows if row["custom_pcb"]), "not_off_the_shelf": custom,
                          "not_identified": unknown, "commodity_without_part_number": generic,
                          "statement": ("No custom PCB is needed: every electrical element is a purchasable board, module or "
                                        "component; the builder cuts and terminates wire." if not custom and not unknown else
                                        "NOT all off the shelf: see not_off_the_shelf / not_identified."),
                          "table": rows}


# ====================================================================== power budget
def _circuit(ctx, r, m):
    el = ctx["el"]
    c = ctx["circuit"] = E.solve_circuit(el, ctx["design"])
    psu = next((d for d in el.devices.values() if d.kind == "psu"), None)
    m["power_budget"] = {"loads_w": c["loads_w"], "wire_loss_w": c["wire_loss_w"], "worst_case_dc_load_w": c["dc_load_w"],
                         "board_current_a": c["board_current"], "heaters": c["heaters"]}
    if psu is None:
        r.add("error", "no_power_supply", "No power supply device is declared.")
        return
    lim = el.req("psu_max_load_frac")
    m["power_budget"].update({"psu": psu.name, "psu_rated_w": psu.ratings["watts"], "psu_load_frac": c["psu"]["load_frac"],
                              "psu_load_limit_frac": lim, "psu_loss_w": c["psu"]["loss_w"], "mains_current_a": c.get("mains_current_a"),
                              "inrush_a": psu.ratings.get("inrush_a")})
    if c["psu"]["load_frac"] > lim:
        r.add("error", "psu_undersized",
              f"Worst-case load (every heater on, motors at run current, fans on) is {c['dc_load_w']:.0f} W = "
              f"{c['psu']['load_frac']:.0%} of the {psu.ratings['watts']:.0f} W supply '{psu.name}'; limit {lim:.0%}.",
              part=psu.component, load_w=c["dc_load_w"], rated_w=psu.ratings["watts"], limit_frac=lim,
              hint=f"Use a supply of at least {c['dc_load_w'] / lim:.0f} W, or a smaller bed heater.")
    for b in el.devices.values():
        if b.kind != "board":
            continue
        ib = c["board_current"].get(b.name, 0.0)
        fuse = b.ratings.get("input_fuse_a")
        if fuse and ib > fuse * el.req("output_max_load_frac"):
            r.add("error", "board_fuse_overloaded",
                  f"Board '{b.name}' draws {ib:.1f} A worst case through its {fuse:g} A input fuse (limit "
                  f"{el.req('output_max_load_frac'):.0%} = {fuse * el.req('output_max_load_frac'):.1f} A).", part=b.component,
                  current_a=round(ib, 2), fuse_a=fuse, hint="Feed the bed through an external MOSFET module wired straight to the supply.")
        vmax = b.ratings.get("driver_max_v")
        if vmax and el.supply_v > vmax:
            r.add("error", "supply_above_driver_rating", f"{el.supply_v:g} V supply exceeds the {vmax:g} V rating of {b.name}'s drivers.")
        m["power_budget"].setdefault("board_fuse_a", {})[b.name] = fuse
        rail = sum(d.ratings.get("supply_w", 0.0) / d.ratings.get("volts", 5.0) for d in el.devices.values()
                   if d.kind == "host" and any(el.port(el.other_end(w, f"{d.name}.{p}"))[0] is b for p in d.ports for w in el.wires_at(f"{d.name}.{p}")))
        if rail > b.ratings.get("rail_5v_max_a", 1e9) * el.req("output_max_load_frac"):
            r.add("error", "board_5v_overloaded", f"Board '{b.name}' 5 V rail: {rail:.2f} A drawn by the host, rail limit "
                  f"{b.ratings['rail_5v_max_a']:g} A.", part=b.component)
        m["power_budget"].setdefault("board_5v_a", {})[b.name] = round(rail, 2)


# ====================================================================== wires, connectors, outputs
def _loaded_in_loom(el, circuit) -> dict:
    out = {}
    for lm in el.looms:
        out[lm] = sum(w.conductors for w in el.wires if lm in w.via and circuit["wire_current"].get(w.name, 0.0) > 0.5)
    return out


def _wires(ctx, r, m):
    el, c = ctx["el"], ctx.get("circuit")
    if c is None:
        raise RuntimeError("no circuit solution (the power-budget check did not run)")
    amb = el.req("ambient_c")
    loaded = _loaded_in_loom(el, c)
    rows = E.wiring_rows(el, c)
    table, worst = {}, {"ampacity_frac": (0.0, None), "drop_v": (0.0, None)}
    olim = el.req("output_max_load_frac")
    for w, row in zip(el.wires, rows):
        i = c["wire_current"].get(w.name, 0.0)
        od1 = E.awg_diameter(w.awg) * 1.15 + 2 * E.INSULATION_WALL_MM.get(w.insulation, 0.4)
        n_b = max([loaded.get(l, 0) for l in w.via] + [w.conductors if i > 0.5 else 1])
        t_lim = min(E.INSULATION_MAX_C.get(w.insulation, 80.0), el.req("wire_max_temp_c"))
        amp = E.wire_ampacity(w.awg, od1, amb, t_lim, n_b)
        temp = E.wire_temperature(i, w.awg, od1, amb, n_b)
        L = row["length_mm"]
        drop = i * 2.0 * E.wire_resistance(w.awg, L, max(temp, 20.0))
        kinds = {(el.port(ref)[1].kind if el.port(ref)[1] else "?") for ref in (w.a, w.b)}
        table[w.name] = {"awg": w.awg, "length_mm": L, "current_a": round(i, 3), "ampacity_a": round(amp, 2),
                         "bundle_loaded_conductors": n_b, "conductor_temp_c": round(temp, 1), "drop_v": round(drop, 3)}
        if amp > 0 and i / amp > worst["ampacity_frac"][0]:
            worst["ampacity_frac"] = (round(i / amp, 3), w.name)
        if drop > worst["drop_v"][0] and not kinds & {"mains_in", "mains_out"}:
            worst["drop_v"] = (round(drop, 3), w.name)
        if i > amp:
            r.add("error", "wire_overloaded",
                  f"Wire '{w.name}' (AWG {w.awg} {w.insulation}, {n_b} loaded conductors bundled) carries {i:.1f} A; its ampacity "
                  f"there is {amp:.1f} A (conductor would reach {temp:.0f} degC, limit {t_lim:.0f}).", wire=w.name, current_a=round(i, 2),
                  ampacity_a=round(amp, 2), conductor_temp_c=round(temp, 1), limit_c=t_lim,
                  hint="Use a heavier gauge (lower AWG number), or take it out of the bundle.")
        for ref, override in ((w.a, w.connector_a), (w.b, w.connector_b)):
            dev, port = el.port(ref)
            if port is None:
                continue
            cn = override or port.connector
            lim = min([x for x in (port.max_current_a, E.CONNECTOR_MAX_A.get(cn)) if x is not None] or [1e9])
            if i > lim * olim + 1e-9 and port.kind not in ("mains_in", "mains_out", "pe"):
                what = "output" if port.kind.endswith("_out") else "connector"
                r.add("error", "output_overloaded" if what == "output" else "connector_overloaded",
                      f"{ref} ({cn or port.kind}) carries {i:.2f} A through wire '{w.name}'; its rating is {lim:g} A and the "
                      f"continuous limit is {olim:.0%} = {lim * olim:.1f} A.", port=ref, wire=w.name, current_a=round(i, 2),
                      rating_a=lim, limit_a=round(lim * olim, 2),
                      hint="Move the load to an external MOSFET module fed from the supply, use a higher-rated terminal, or reduce the load.")
    m["wire_table"] = table
    m["wire_worst"] = {"highest_fraction_of_ampacity": worst["ampacity_frac"], "largest_drop_v": worst["drop_v"]}
    # series devices (thermal fuse, relay, MOSFET module) carry the load current
    for h, f in c.get("heater_feed", {}).items():
        i = c["heaters"][h]["current_a"]
        _, series, _ = E.trace_supply(el, f"{h}.in")
        for dev, _, _ in series:
            lim = dev.ratings.get("amps") or dev.ratings.get("contact_a")
            if lim and i > lim * olim:
                r.add("error", "series_device_overloaded", f"{dev.name} ({dev.kind}) carries the {i:.1f} A of heater '{h}'; rated "
                      f"{lim:g} A, continuous limit {lim * olim:.1f} A.", device=dev.name, part=dev.component, current_a=i, rating_a=lim)
    # voltage delivered to each heater
    vlim = el.req("max_heater_vdrop_frac")
    for h, hv in c["heaters"].items():
        if hv["drop_frac"] > vlim:
            f = c["heater_feed"].get(h, {})
            names = [w.name for w in f.get("load_wires", []) + f.get("feed_wires", [])]
            r.add("error", "heater_voltage_drop",
                  f"Heater '{h}' receives {hv['volts_at_heater']:.2f} V of {el.supply_v:g} V: {hv['drop_frac']:.1%} is lost on the way "
                  f"(limit {vlim:.0%}), so it makes {hv['power_w']:.0f} W of its {hv['rated_w']:.0f} W.", heater=h, wires=names,
                  drop_frac=hv["drop_frac"], limit_frac=vlim, hint="Shorten the run or use a heavier gauge on " + ", ".join(names) + ".")


# ====================================================================== mains and protective earth
def _mains(ctx, r, m):
    el, c = ctx["el"], ctx.get("circuit") or {}
    inlet = next((d for d in el.devices.values() if d.kind == "inlet"), None)
    psu = next((d for d in el.devices.values() if d.kind == "psu"), None)
    out = {}
    if psu is None:
        return
    if inlet is None:
        r.add("error", "no_mains_inlet", "The supply has no mains inlet: nothing fuses or switches the mains.",
              hint="Add iec_inlet_c14(fuse_a=...) on a panel and wire L/N to the supply.")
        m["mains"] = out
        return
    i_m = max((c.get("mains_current_a") or {0: 0.0}).values())
    fuse, rated = inlet.ratings.get("fuse_a"), inlet.ratings.get("amps", 10.0)
    out.update({"mains_current_a": c.get("mains_current_a"), "fuse_a": fuse, "inlet_rating_a": rated,
                "inrush_a": psu.ratings.get("inrush_a")})
    if not fuse:
        r.add("error", "no_mains_fuse", f"Inlet '{inlet.name}' has no fuse.", part=inlet.component)
    else:
        need = el.req("fuse_min_factor") * i_m
        if fuse < need:
            r.add("error", "mains_fuse_too_small", f"Mains fuse {fuse:g} A; the supply draws {i_m:.2f} A at the lowest mains voltage "
                  f"{min(el.mains_v):g} V, so the fuse must be at least {need:.2f} A.", part=inlet.component, fuse_a=fuse, needed_a=round(need, 2),
                  hint="Next standard 5x20 values: 4, 5, 6.3, 8, 10 A.")
        if fuse > rated:
            r.add("error", "mains_fuse_above_inlet", f"Mains fuse {fuse:g} A exceeds the inlet's {rated:g} A rating.", part=inlet.component)
        if "T" not in str(inlet.ratings.get("fuse_type", "")):
            r.add("error", "mains_fuse_not_time_lag", f"The supply's inrush is {psu.ratings.get('inrush_a')} A; a fast fuse will blow at switch-on.")
    r.add("info", "inrush", f"Cold-start inrush of {psu.name} is {psu.ratings.get('inrush_a')} A (data sheet, typical): the "
          f"T{fuse:g}A time-lag fuse is assumed to ride through it; I2t was not checked.")
    amb = el.req("ambient_c")
    mains_wires = [w for w in el.wires if {(el.port(x)[1].kind if el.port(x)[1] else "") for x in (w.a, w.b)} & {"mains_in", "mains_out"}]
    pe_wires = [w for w in el.wires if all((el.port(x)[1].kind if el.port(x)[1] else "") == "pe" for x in (w.a, w.b))]
    for ln in ("L", "N"):
        _, _, src = E.trace_supply(el, f"{psu.name}.{ln}")
        if not src or el.port(src)[0] is not inlet:
            r.add("error", "mains_not_wired", f"Supply terminal {ln} is not wired to the inlet.", part=psu.component)
    for w in mains_wires:
        od1 = E.awg_diameter(w.awg) * 1.15 + 2 * E.INSULATION_WALL_MM.get(w.insulation, 0.4)
        amp = E.wire_ampacity(w.awg, od1, amb, min(E.INSULATION_MAX_C.get(w.insulation, 80.0), el.req("wire_max_temp_c")), 2)
        if fuse and amp < fuse or E.awg_area_mm2(w.awg) < 0.75:
            r.add("error", "mains_wire_too_thin", f"Mains wire '{w.name}' is AWG {w.awg} ({E.awg_area_mm2(w.awg):.2f} mm^2, "
                  f"{amp:.1f} A): it must carry the {fuse:g} A fuse rating and be at least 0.75 mm^2.", wire=w.name,
                  hint="Use AWG 18 (0.82 mm^2) or heavier for all mains wiring.")
        low = [x.name for x in el.wires if x is not w and x not in mains_wires and x not in pe_wires and set(x.via) & set(w.via)]
        if low:
            r.add("error", "mains_bundled_with_low_voltage", f"Mains wire '{w.name}' shares a loom with low-voltage wires {low[:4]}.",
                  wire=w.name, hint="Route mains in its own loom, away from signal wiring.")
    for dev in el.devices.values():
        if dev.kind == "relay" and dev.params.get("cuts") == "psu":
            lim = dev.ratings.get("contact_a", 0.0)
            if fuse and lim < i_m * el.req("fuse_min_factor"):
                r.add("error", "relay_contact_too_small", f"Relay '{dev.name}' contact {lim:g} A for {i_m:.1f} A of mains current.", part=dev.component)
    # protective earth: inlet PE -> supply FG, inlet PE -> frame
    def pe_link(a_dev, b_kind):
        for w in pe_wires:
            ends = [el.port(x)[0] for x in (w.a, w.b)]
            if a_dev in ends and any(e is not a_dev and e.kind == b_kind for e in ends):
                return w
        return None

    w_psu, w_frame = pe_link(inlet, "psu"), pe_link(inlet, "earth_point")
    if w_frame is None:      # daisy-chained through the supply's FG terminal is also a bond
        w_frame = pe_link(psu, "earth_point") if w_psu is not None else None
    out["pe_to_psu"], out["pe_to_frame"] = (w_psu.name if w_psu else None), (w_frame.name if w_frame else None)
    if w_psu is None:
        r.add("error", "psu_not_earthed", "No protective-earth wire from the inlet's PE pin to the supply's FG terminal.",
              part=psu.component, hint="el.wire('pe psu', 'inlet.PE', 'psu.FG', awg=18, conductors=1)")
    if w_frame is None:
        r.add("error", "frame_not_earthed", "The metal frame is not bonded to protective earth: a mains fault to the frame would make it live.",
              hint="Add an earth point (ring terminal under a frame screw) as a device of kind 'earth_point' and wire it to the inlet's PE.")
    else:
        ep = next(el.port(x)[0] for x in (w_frame.a, w_frame.b) if el.port(x)[0].kind == "earth_point")
        comp = next((cc for cc in ctx["design"].components if cc.name == ep.params.get("bonds", ep.component)), None)
        if comp is None or comp.material not in ("al6061", "steel", "stainless304", "brass"):
            r.add("error", "earth_point_not_on_metal", f"Earth point '{ep.name}' is not on a metal frame part.", device=ep.name)
    thinnest_mains = max((w.awg for w in mains_wires), default=None)
    for w in (w_psu, w_frame):
        if w is not None and thinnest_mains is not None and w.awg > min(thinnest_mains, 18):
            r.add("error", "pe_wire_too_thin", f"Earth wire '{w.name}' (AWG {w.awg}) is thinner than the mains conductors (AWG "
                  f"{thinnest_mains}); it must carry the fault current until the fuse opens.", wire=w.name)
    m["mains"] = out


# ====================================================================== steppers
def _steppers(ctx, r, m):
    design, el = ctx["design"], ctx["el"]
    from .ratings import resolve_drives

    comps = {c.name: c for c in design.components}
    curves = E.apply_motor_curves(design)
    drives = resolve_drives(design)
    ctx["curves"] = curves
    c = ctx.get("circuit") or {"motors": {}}
    out = {}
    scur = el.firmware.get("steppers", {})
    for (bname, grp), g in E.motor_groups(el).items():
        board = g["board"]
        names = [x.name for x in g["motors"]]
        key = next((k for k, v in scur.items() if set(v.get("motors", [])) & set(names)), None)
        st = scur.get(key, {}) if key else {}
        run = st.get("run_current")
        if not run:
            r.add("error", "no_run_current", f"Driver {bname}.{grp} (motors {names}) has no run_current in the firmware settings.", driver=grp)
            continue
        n = len(names)
        conn = g["motors"][0].params.get("connection", "parallel") if n > 1 else "single"
        lim, absmax = board.ratings.get("driver_max_rms_a", 1e9), board.ratings.get("driver_abs_max_rms_a", 1e9)
        if run > lim:
            r.add("error", "driver_current_over_limit",
                  f"Driver {bname}.{grp}: run_current {run:.2f} A rms exceeds what the {board.ratings.get('driver', 'driver')} can set with its "
                  f"{board.ratings.get('sense_resistor_ohm')} ohm sense resistors ({lim:.2f} A rms; firmware cap {absmax:g} A).",
                  driver=grp, run_current_a=run, limit_a=lim, hint="Lower the current, or split the motors over two drivers.")
        elif run > 0.8 * lim:
            r.add("warning", "driver_current_high", f"Driver {bname}.{grp} is set to {run:.2f} A rms, {run / lim:.0%} of its maximum: "
                  f"it needs the board's heat sink in moving air.", driver=grp)
        for mdev in g["motors"]:
            i_m = run / n if conn == "parallel" else run
            rated = mdev.ratings.get("rated_current_a")
            miss = [k for k in ("rated_current_a", "phase_resistance_ohm", "phase_inductance_mh") if k not in mdev.ratings]
            if miss:
                r.add("error", "motor_electrical_data_missing", f"Motor '{mdev.name}' has no {miss}: its drive cannot be checked.", device=mdev.name)
                continue
            if i_m > rated * 1.001:
                r.add("error", "motor_current_over_rating",
                      f"Motor '{mdev.name}' gets {i_m:.2f} A rms per phase from driver {grp}; its winding is rated {rated:g} A.",
                      device=mdev.name, part=mdev.component, current_a=round(i_m, 3), rated_a=rated,
                      hint=f"Set run_current of '{key}' to {rated * (n if conn == 'parallel' else 1):.2f} A or less.")
            cv = curves.get(mdev.name)
            out[mdev.name] = {"driver": f"{bname}.{grp}", "axis": key, "connection": conn, "driver_run_current_a": run,
                              "motor_current_a": round(i_m, 3), "rated_current_a": rated,
                              "torque_curve_nmm": dict(zip(cv["rpm"], cv["torque_nmm"])) if cv else None}
    # torque at the design's top speed, and the margin that leaves (same formula as the motion verifier's inputs)
    g0 = float(np.linalg.norm(design.gravity)) * 1e-3
    bodies = design.bodies()

    def carried(body):
        return sum(cc.mass() for cc in bodies.get(body, [])) + sum(carried(j.child) for j in design.joints if j.parent == body)

    axes = {}
    for j in design.joints:
        d = drives.get(j.name)
        if not d:
            continue
        rpm = d["motor_rpm_at_max_speed"]
        ms = d["motors"]
        t_el = sum(float(np.interp(rpm, *zip(*comps[mn].ratings["torque_curve_rpm_frac"]))) * comps[mn].ratings["holding_torque_nmm"] for mn in ms)
        t_cls = None
        if all(comps[mn].ratings.get("torque_curve_class") for mn in ms):
            t_cls = sum(float(np.interp(rpm, *zip(*comps[mn].ratings["torque_curve_class"]))) * comps[mn].ratings["holding_torque_nmm"] for mn in ms)
        t_zero = sum(comps[mn].ratings["torque_curve_rpm_frac"][0][1] * comps[mn].ratings["holding_torque_nmm"] for mn in ms)
        mass = carried(j.child) + j.reflected_inertia
        ax = np.array(j.axis, dtype=float) / np.linalg.norm(j.axis)
        grav = abs(float(ax @ (np.array(design.gravity) / max(np.linalg.norm(design.gravity), 1e-9)))) * g0 * carried(j.child)
        need = mass * (j.max_accel or 0.0) * 1e-3 + grav if j.kind == "slide" else None
        margin = (j.max_effort / need) if need else None
        axes[j.name] = {"motor_rpm_at_max_speed": rpm, "torque_at_speed_nmm": round(t_el, 1), "torque_at_standstill_nmm": round(t_zero, 1),
                        "class_curve_torque_nmm": round(t_cls, 1) if t_cls is not None else None,
                        "available_effort": j.max_effort, "needed_effort_estimate": round(need, 2) if need else None,
                        "margin_estimate": round(margin, 2) if margin else None, "required_margin": j.min_drive_margin}
        if margin is not None and margin < j.min_drive_margin:
            r.add("error", "torque_at_speed_too_low",
                  f"Joint {j.name}: at {j.max_speed:g} mm/s the motor(s) {ms} turn {rpm:.0f} rpm, where supply voltage, winding "
                  f"inductance and back-EMF leave {t_el:.0f} N*mm of the {t_zero:.0f} N*mm available at standstill; that is "
                  f"{j.max_effort:.0f} N against {need:.1f} N needed (margin {margin:.1f} < {j.min_drive_margin:g}).",
                  joint=j.name, motors=ms, rpm=rpm, torque_nmm=round(t_el, 1), margin=round(margin, 2), required_margin=j.min_drive_margin,
                  hint="Use a low-inductance (higher-current) winding, a higher supply voltage, a smaller pulley, or lower the top speed.")
    m["steppers"] = {"motors": out, "axes": axes,
                     "consistency": "ratings.resolve_drives, the motion verifier and the twin read the electrical curve "
                                    "(component.ratings['torque_curve_rpm_frac']); the class curve is kept as 'torque_curve_class'"}


# ====================================================================== heaters: simulation and fault injection
def _kind(plant) -> str:
    return "bed" if "plate" in plant.net.idx else "hotend"


def heater_report(el, design, circuit, quick: bool = False) -> dict:
    """Everything the simulation says about each firmware heater. Used by the verifier and by the twin (heat-up time)."""
    plants = E.build_plants(el, design, circuit)
    rep = {}
    for hn, plant in plants.items():
        hc = dict(el.firmware["heaters"][hn])
        kind = _kind(plant)
        targets = [float(t) for t in hc.get("targets", [60.0 if kind == "bed" else 250.0])]
        lim = el.req("bed_heatup_max_s") if kind == "bed" else el.req("hotend_heatup_max_s")
        t_max = 2.5 * (max(lim.values()) if isinstance(lim, dict) else lim)
        ch = E.heater_characteristics(plant, targets, t_max)
        out = {"kind": kind, "targets_c": targets, "power_w": plant.power_w, "basis": plant.basis, "heatup_s": ch["heatup_s"],
               "max_temp_at_full_duty_c": round(ch["max_temp_c"], 1), "steady_duty": {k: round(v, 3) for k, v in ch["duty_at"].items()},
               "cutoffs": plant.cutoffs, "plant": plant}
        rep[hn] = out
        if quick or plant.thermistor is None:
            continue
        reachable = [t for t in targets if ch["heatup_s"][t] is not None]
        if not reachable:
            continue
        cfg = {"control": hc.get("control", "pid"), "max_delta": hc.get("max_delta", 2.0), "min_temp": hc.get("min_temp", 0.0),
               "max_temp": hc.get("max_temp", 250.0), "max_power": hc.get("max_power", 1.0), "smooth_time": hc.get("smooth_time", 1.0)}
        vh = hc.get("verify_heater", {})
        cfg["verify_heater"] = None if vh is None else {"check_gain_time": 60.0 if hn == "heater_bed" else 20.0, **vh}
        if cfg["control"] == "pid":
            cfg["pid"] = tuple(hc["pid"]) if hc.get("pid") else E.autotune_pid(plant, cfg, float(hc.get("tune_at", max(reachable))))
            out["pid"] = cfg["pid"]
            out["pid_source"] = "design" if hc.get("pid") else "simulated PID_CALIBRATE (relay autotune on the model)"
        out["cfg"] = cfg
        out["closed_loop"] = {}
        last = None
        for tg in reachable:
            run = E.simulate_heater(plant, cfg, tg, t_end=ch["heatup_s"][tg] * 2.0 + (900.0 if kind == "bed" else 240.0), stop_when_settled=False)
            cm = E.closed_loop_metrics(run, tg)
            cm["false_trip"] = run["shutdown_reason"] if run["shutdown"] else None
            out["closed_loop"][tg] = cm
            last = (tg, run)
        # ---- fault injection at the highest reachable target, from the settled state
        tg, run = last
        hold = run["state"]
        horizon = el.req("fault_trip_max_s")[kind] * 3.0
        faults = {}
        for fk in ("sensor_detached", "sensor_short", "sensor_open", "mosfet_short"):
            fr = _fault_run(plant, cfg, tg, hold, {"kind": fk, "at": 30.0}, horizon)
            faults[f"{fk} while holding {tg:g} degC"] = fr
        cold = E.simulate_heater(plant, cfg, tg, t_end=horizon, fault={"kind": "sensor_detached", "at": 0.0})
        faults[f"sensor_detached before heating to {tg:g} degC"] = _fault_summary(cold, 0.0, tg)
        bare = E.HeaterPlant(plant.name, plant.net, plant.heater_node, plant.sensor_node, plant.report_node, plant.power_w,
                             plant.sensor_tau_s, plant.thermistor, [])
        fr = _fault_run(bare, cfg, tg, hold, {"kind": "mosfet_short", "at": 30.0}, horizon)
        fr["settles_at_c"] = round(ch["max_temp_c"], 1)
        faults["mosfet_short with no independent cut-off"] = fr
        out["faults"] = faults
        th = plant.thermistor
        out["thermistor"] = {"sensor_type": th.name, "pullup_ohm": th.pullup, "adc_bits": th.adc_bits,
                             "deg_per_count": {t: round(th.deg_per_count(t), 3) for t in sorted(set([25.0] + targets + [cfg["max_temp"]]))}}
    return rep


def _fault_run(plant, cfg, tg, hold, fault, horizon):
    # warm controller: a short healthy hold first so the PID integrator and verify_heater are in their steady state
    pre = E.simulate_heater(plant, cfg, tg, t_end=horizon, fault=fault, t0_state=hold)
    return _fault_summary(pre, fault["at"], tg)


def _fault_summary(run, t_fault, tg):
    i0 = int(np.argmax(run["t"] >= t_fault))
    events = [(run["t_shutdown"], "firmware shutdown: " + run["shutdown_reason"]) if run["shutdown"] else None,
              (run["fuse_opened_at"], "thermal fuse opened") if run["fuse_opened_at"] is not None else None,
              (run["relay_opened_at"], "supply relay dropped") if run["relay_opened_at"] is not None else None]
    events = sorted(e for e in events if e)
    off = np.where(run["duty"][i0:] <= 0.0)[0]
    return {"detected": bool(run["shutdown"]), "detected_after_s": round(run["t_shutdown"] - t_fault, 1) if run["shutdown"] else None,
            "detected_by": run["shutdown_reason"] or None,
            "power_removed_after_s": (round(float(run["t"][i0 + off[0]] - t_fault), 1) if len(off) and run["duty"][-1] <= 0.0 and
                                      (run["shutdown"] or run["fuse_opened_at"] is not None) else None),
            "events": [(round(t - t_fault, 1), what) for t, what in events],
            "peak_c": round(float(run["T"][i0:].max()), 1), "final_c": round(float(run["T"][-1]), 1),
            "still_heating_at_end": bool(run["duty"][-1] > 0.0)}


def _heaters(ctx, r, m):
    design, el = ctx["design"], ctx["el"]
    c = ctx.get("circuit")
    if c is None:
        raise RuntimeError("no circuit solution")
    if not (el.firmware.get("heaters")):
        return
    rep = heater_report(el, design, c)
    ctx["heaters"] = rep
    out = {}
    for hn, h in rep.items():
        kind, plant = h["kind"], h["plant"]
        hd = el.devices[el.firmware["heaters"][hn]["heater"]]
        hc = el.firmware["heaters"][hn]
        res = {k: v for k, v in h.items() if k not in ("plant", "cfg")}
        out[hn] = res
        lim = el.req("bed_heatup_max_s") if kind == "bed" else el.req("hotend_heatup_max_s")
        margin = el.req("max_reach_margin_c")
        for tg in h["targets_c"]:
            t = h["heatup_s"][tg]
            tl = (lim.get(tg) or max(lim.values())) if isinstance(lim, dict) else lim
            if h["max_temp_at_full_duty_c"] < tg + margin:
                r.add("error", "heater_cannot_reach",
                      f"Heater '{hn}' ({h['power_w']:.0f} W delivered) levels off at {h['max_temp_at_full_duty_c']:.0f} degC at 100 % duty; "
                      f"the target is {tg:g} degC and it needs {margin:g} K in hand.", heater=hn, part=hd.component, target_c=tg,
                      max_c=h["max_temp_at_full_duty_c"], hint="More heater power, or insulate the underside of the plate.")
            elif t is None or t > tl:
                r.add("error", "heatup_too_slow",
                      f"Heater '{hn}' takes {'more than ' + format(2.5 * tl, '.0f') if t is None else format(t, '.0f')} s to reach {tg:g} degC "
                      f"from {el.req('ambient_c'):g} degC ({h['power_w']:.0f} W delivered); the limit is {tl:.0f} s.", heater=hn,
                      part=hd.component, target_c=tg, heatup_s=t, limit_s=tl,
                      hint="More heater power (check the supply and the wiring can carry it), or relax the requirement in "
                           "electrical.requirements if the brief allows.")
        mx = hc.get("max_temp", 250.0)
        if mx < max(h["targets_c"]) + 10.0:
            r.add("error", "max_temp_too_low", f"Firmware max_temp {mx:g} for '{hn}' is within 10 K of the {max(h['targets_c']):g} degC target.", heater=hn)
        dev_max = min(hd.ratings.get("max_temp_c", 1e9), (el.devices[hc["sensor"]].ratings.get("max_temp_c", 1e9) if hc.get("sensor") in el.devices else 1e9))
        if mx > dev_max:
            r.add("error", "max_temp_above_part_rating", f"Firmware max_temp {mx:g} for '{hn}' is above what the heater/sensor are rated for ({dev_max:g} degC).", heater=hn)
        if plant.thermistor is None:
            r.add("error", "heater_not_simulated", f"Heater '{hn}' has no thermistor model: its control loop and fault behaviour were not simulated.", heater=hn)
            continue
        if "closed_loop" not in h:
            continue
        olim, rlim = el.req("overshoot_max_c")[kind], el.req("ripple_max_c")[kind]
        for tg, cm in h["closed_loop"].items():
            if cm.get("false_trip"):
                r.add("error", "false_runaway_trip", f"Heater '{hn}': heating normally to {tg:g} degC trips the firmware ({cm['false_trip']}).",
                      heater=hn, target_c=tg, hint="The heater is too weak for verify_heater's heating_gain/check_gain_time; add power or widen them knowingly.")
                continue
            if not cm.get("reached"):
                r.add("error", "target_not_reached_closed_loop", f"Heater '{hn}' did not reach {tg:g} degC under closed-loop control.", heater=hn)
                continue
            if cm["overshoot_c"] > olim:
                r.add("error", "heater_overshoot", f"Heater '{hn}' overshoots {tg:g} degC by {cm['overshoot_c']:.1f} K (limit {olim:g}) with "
                      f"{h.get('pid_source', 'the configured control')}.", heater=hn, overshoot_c=cm["overshoot_c"], limit_c=olim,
                      hint="Tune at the temperature you print at ('tune_at'), or lower Kp/raise Kd.")
            if not cm["settled"] or cm["ripple_c"] > rlim:
                r.add("error", "heater_not_stable", f"Heater '{hn}' at {tg:g} degC: ripple {cm['ripple_c']:.2f} K (limit {rlim:g}), settled={cm['settled']}.",
                      heater=hn, ripple_c=cm["ripple_c"], hint="Bang-bang control ripples by design; use PID, or accept it by raising ripple_max_c.")
        # thermistor resolution
        dlim = el.req("thermistor_max_deg_per_count")
        for t, dpc in h["thermistor"]["deg_per_count"].items():
            if t in h["targets_c"] and dpc > dlim:
                r.add("error", "thermistor_resolution", f"Heater '{hn}': at {t:g} degC one ADC count is {dpc:.2f} K (limit {dlim:g}) with "
                      f"{h['thermistor']['sensor_type']} and a {h['thermistor']['pullup_ohm']:g} ohm pull-up.", heater=hn,
                      hint="Use a sensor suited to the range (PT1000 with a suitable pull-up) or a lower pull-up.")
        # faults
        plim, tlim = el.req("fault_peak_limit_c")[kind], el.req("fault_trip_max_s")[kind]
        for fname, f in h["faults"].items():
            bare = "no independent cut-off" in fname
            if fname.startswith("mosfet_short"):
                if bare:
                    continue
                hard = [cu for cu in h["cutoffs"] if cu["kind"] == "thermal_fuse"]
                if f["still_heating_at_end"] or f["peak_c"] > plim:
                    settle = h["faults"]["mosfet_short with no independent cut-off"]["settles_at_c"]
                    r.add("error", "no_independent_cutoff",
                          f"Heater '{hn}': with its MOSFET failed shorted the firmware cannot remove power. "
                          + (f"Nothing else does either: the {kind} settles at {settle:.0f} degC" if f["still_heating_at_end"]
                             else f"The cut-off acts too late: it peaks at {f['peak_c']:.0f} degC")
                          + f" (limit {plim:g} degC).", heater=hn, part=hd.component, peak_c=f["peak_c"], settles_at_c=settle, limit_c=plim,
                          hint="Put a thermal fuse on the heated part in series with the heater, and/or a relay ahead of the supply "
                               "that the firmware drops on shutdown.")
                elif not hard:
                    r.add("warning", "cutoff_depends_on_mcu",
                          f"Heater '{hn}': a shorted MOSFET is survived only because the firmware drops the supply relay "
                          f"(peak {f['peak_c']:.0f} degC). There is no cut-off that works if the controller has also hung.", heater=hn)
                continue
            if not f["detected"]:
                r.add("error", "runaway_not_detected",
                      f"Heater '{hn}', fault '{fname}': the firmware never shuts down; the {kind} reaches {f['peak_c']:.0f} degC and is still heating."
                      if f["still_heating_at_end"] else
                      f"Heater '{hn}', fault '{fname}': not detected by the firmware (peak {f['peak_c']:.0f} degC).",
                      heater=hn, fault=fname, peak_c=f["peak_c"],
                      hint="Enable verify_heater (thermal runaway protection) and min_temp/max_temp for this heater.")
            elif f["detected_after_s"] > tlim or f["peak_c"] > plim:
                r.add("error", "runaway_detected_too_late",
                      f"Heater '{hn}', fault '{fname}': detected after {f['detected_after_s']:.0f} s (limit {tlim:g}), peak "
                      f"{f['peak_c']:.0f} degC (limit {plim:g}).", heater=hn, fault=fname, detected_after_s=f["detected_after_s"], peak_c=f["peak_c"],
                      hint="Tighten verify_heater max_error / check_gain_time, or lower max_temp.")
        for cu in h["cutoffs"]:
            if cu["kind"] == "thermal_fuse":
                dv = el.devices[cu["device"]]
                if dv.ratings.get("hold_c", 1e9) < max(h["targets_c"]) + 5.0:
                    r.add("error", "thermal_fuse_nuisance", f"Thermal fuse '{dv.name}' holds only to {dv.ratings['hold_c']:g} degC; the {kind} runs at "
                          f"{max(h['targets_c']):g} degC, so it will age and open in normal use.", device=dv.name, part=dv.component)
        # melt capacity at the design's print speeds (hotend only)
        if kind == "hotend" and design.printer:
            sp = (design.printer.get("speeds") or {})
            v = float(sp.get("infill", 60.0))
            flow = v * design.printer.get("layer_height", 0.2) * design.printer.get("nozzle", 0.4) * 1.125     # mm^3/s
            tg = max(h["targets_c"])
            p_melt = flow * 1e-9 * 1240.0 * 1800.0 * (tg - el.req("ambient_c"))
            spare = h["power_w"] * (1.0 - h["steady_duty"][tg])
            res["melt"] = {"flow_mm3_s": round(flow, 2), "melt_power_w": round(p_melt, 2), "spare_power_w": round(spare, 1),
                           "basis": "PLA: 1240 kg/m^3, cp 1800 J/kgK (typical, unverified); latent heat ignored"}
            if p_melt > spare:
                r.add("error", "melt_capacity", f"Hotend needs {p_melt:.1f} W to melt {flow:.1f} mm^3/s but has {spare:.1f} W spare at {tg:g} degC.", heater=hn)
    m["heaters"] = out


# ====================================================================== physical: connectors, routes, bends, strain relief
def _poses(design):
    from .motion import sample_poses

    return sample_poses(design, per_joint=5, n_random=8) if design.joints else [{}]


class _Scene:
    """Distance queries from points riding on one body to parts riding on another, over sampled poses."""

    def __init__(self, design):
        self.design = design
        self.comps = list(design.components)
        self.box = np.array([[*(lambda b: (b.min.X, b.min.Y, b.min.Z, b.max.X, b.max.Y, b.max.Z))(c.shape.bounding_box())] for c in self.comps])
        self.body = [c.body for c in self.comps]
        self.poses = _poses(design)
        self.T = [forward_kinematics(design, q) for q in self.poses]

    def near(self, body: str, pts: np.ndarray, radius: float, other_bodies: bool, exclude=()) -> list:
        """[(component name, min distance, pose, point index)] for parts closer than `radius` to any point.
        other_bodies=True: parts that move relative to `body`, all poses. False: parts on the same body (home pose)."""
        hits = {}
        pts = np.asarray(pts, dtype=float).reshape(-1, 3)
        bodies = sorted(set(self.body))
        for b2 in bodies:
            same = b2 == body
            if same == other_bodies:
                continue
            idx = [i for i, bb in enumerate(self.body) if bb == b2 and self.comps[i].name not in exclude]
            if not idx:
                continue
            seen_local = set()
            for q, T in (zip(self.poses, self.T) if not same else [(self.poses[0], self.T[0])]):
                if body not in T or b2 not in T:
                    continue
                M = np.linalg.inv(T[b2]) @ T[body]
                loc = pts @ M[:3, :3].T + M[:3, 3]
                key = tuple(np.round(M[:3, 3], 2))
                if key in seen_local:
                    continue
                seen_local.add(key)
                bx = self.box[idx]
                inside = ((loc[:, None, :] >= bx[None, :, :3] - radius) & (loc[:, None, :] <= bx[None, :, 3:] + radius)).all(axis=2)
                for pi, ci in zip(*np.nonzero(inside)):
                    c = self.comps[idx[ci]]
                    try:
                        dist = float(c.shape.distance_to(Vertex(*[float(x) for x in loc[pi]])))
                    except Exception:
                        continue
                    if dist < radius and (c.name not in hits or dist < hits[c.name][1]):
                        hits[c.name] = (c.name, dist, q, int(pi))
        return sorted(hits.values(), key=lambda h: h[1])


def _sample(p0, p1, step=5.0, inset=0.0):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1 - p0))
    if L <= 2 * inset + 1e-9:
        return np.empty((0, 3))
    n = max(2, int(math.ceil((L - 2 * inset) / step)) + 1)
    s = np.linspace(inset / L, 1 - inset / L, n)
    return p0[None, :] + (p1 - p0)[None, :] * s[:, None]


def _physical(ctx, r, m):
    design, el = ctx["design"], ctx["el"]
    comps = {c.name: c for c in design.components}
    sc = _Scene(design)
    out = {"poses_checked": len(sc.poses), "looms": {}, "connectors_checked": 0}
    fmt = lambda q: {k: round(v, 1) for k, v in q.items()}
    # ---- connector keep-out: room to plug in
    depth = el.req("connector_keepout_mm")
    for d in el.devices.values():
        if not d.component or d.component not in comps:
            continue
        for p in d.ports.values():
            if p.direction is None or p.at is None or not el.wires_at(f"{d.name}.{p.name}"):
                continue
            dv = np.array(p.direction, float)
            dv /= max(np.linalg.norm(dv), 1e-9)
            pts = np.array(p.at, float)[None, :] + dv[None, :] * np.linspace(3.0, depth, 4)[:, None]
            out["connectors_checked"] += 1
            body = comps[d.component].body
            hits = sc.near(body, pts, 2.5, other_bodies=False, exclude=(d.component,)) + sc.near(body, pts, 2.5, other_bodies=True)
            if hits:
                nm, dist, q, _ = hits[0]
                r.add("error", "connector_blocked",
                      f"Connector {d.name}.{p.name}: '{nm}' is in the {depth:g} mm in front of it that the plug and the first bend of the "
                      f"wire need" + (f" at pose {fmt(q)}." if q else "."), port=f"{d.name}.{p.name}", part=d.component, blocked_by=nm,
                      hint="Move or turn the device, or the part in front of it.")
    # ---- looms
    clr = el.req("wire_clearance_mm")
    cable_names = {c.name for c in design.cables}
    for lm in el.looms.values():
        od = el.loom_od(lm)
        rad = od / 2.0
        rb = el.loom_bend_radius(lm)
        info = {"od_mm": round(od, 1), "length_mm": round(lm.length(), 0), "min_bend_radius_mm": round(rb, 1),
                "wires": [w.name for w in el.wires if lm.name in w.via], "flex_spans": 0}
        out["looms"][lm.name] = info
        if not info["wires"]:
            r.add("warning", "empty_loom", f"Loom '{lm.name}' carries no wires.", loom=lm.name)
        bodies_known = set(design.bodies()) | {"world"}
        if any(wp.body not in bodies_known for wp in lm.route):
            r.add("error", "loom_unknown_body", f"Loom '{lm.name}' has a waypoint on a body that does not exist.", loom=lm.name)
            continue
        for i, a, b, flex, L in lm.spans():
            if flex:
                info["flex_spans"] += 1
                nm = f"{lm.name} [{a.body}-{b.body}]"
                if not L:
                    r.add("error", "flex_span_without_length", f"Loom '{lm.name}' crosses from body '{a.body}' to '{b.body}' with no "
                          f"flex_length given.", loom=lm.name, hint="Loom(..., flex_length={index: mm}) for the free cable between the two clamps.")
                if nm not in cable_names:
                    r.add("error", "loom_not_in_cable_check", f"Loom '{lm.name}' flexing span {a.body}-{b.body} is not in design.cables, so its "
                          f"length over the travel was not checked.", loom=lm.name, hint="Call design.electrical.sync_cables(design) at the end of build().")
                for wp in (a, b):
                    cp = comps.get(wp.clamp) if wp.clamp else None
                    if cp is None or cp.body != wp.body:
                        r.add("error", "no_strain_relief",
                              f"Loom '{lm.name}': the end of its flexing span on body '{wp.body}' at {tuple(round(x, 1) for x in wp.xyz)} "
                              f"is not clamped to a part" + (f" ('{wp.clamp}' is not a part on that body)." if wp.clamp else "."),
                              loom=lm.name, body=wp.body, hint="Tie the loom to a part there: Waypoint(body, xyz, clamp='<part>'). "
                              "Without it every stroke works the wires at their terminals.")
                    else:
                        gap = float(cp.shape.distance_to(Vertex(*wp.xyz)))
                        if gap > rad + 6.0:
                            r.add("error", "strain_relief_in_air", f"Loom '{lm.name}': clamp point on '{wp.clamp}' is {gap:.0f} mm from that part.",
                                  loom=lm.name, part=wp.clamp)
                # the straight line between the clamps: if a part sits on it, the loop has to drape round that part
                chord = _sample(a.xyz, b.xyz, 6.0, inset=max(8.0, rad + 4.0))
                hit = []
                for q, T in zip(sc.poses, sc.T):
                    pa = (T[a.body] @ np.array([*a.xyz, 1.0]))[:3]
                    pb = (T[b.body] @ np.array([*b.xyz, 1.0]))[:3]
                    pts = _sample(pa, pb, 6.0, inset=max(8.0, rad + 4.0))
                    if len(pts):
                        hit += [(h, q) for h in _Scene.near_world(sc, pts, rad, T, exclude=(a.clamp, b.clamp))]
                if hit:
                    (nm_, dist), q = min(hit, key=lambda x: x[0][1])
                    r.add("warning", "flex_span_crosses_part", f"Loom '{lm.name}': the straight line between its two clamps passes through "
                          f"'{nm_}' at pose {fmt(q)}; the free loop has to bend round it and may rub.", loom=lm.name, part=nm_)
                continue
            # fixed run on one body
            pts = _sample(a.xyz, b.xyz, 5.0)
            moving = sc.near(a.body, pts, rad + clr, other_bodies=True)
            if moving:
                nm_, dist, q, _ = moving[0]
                r.add("error", "wire_hits_moving_part",
                      f"Loom '{lm.name}' between {tuple(round(x) for x in a.xyz)} and {tuple(round(x) for x in b.xyz)} (on '{a.body}') comes within "
                      f"{max(dist - rad, 0.0):.1f} mm of '{nm_}', which moves relative to it, at pose {fmt(q)}; {clr:g} mm clearance is required.",
                      loom=lm.name, part=nm_, pose=fmt(q), clearance_mm=round(dist - rad, 1), hint="Re-route the loom outside the swept volume of that part.")
            inner = _sample(a.xyz, b.xyz, 5.0, inset=min(8.0, float(np.linalg.norm(np.subtract(a.xyz, b.xyz))) / 3))
            through = [h for h in sc.near(a.body, inner, 0.05, other_bodies=False)] if len(inner) else []
            if through:
                r.add("error", "wire_through_part", f"Loom '{lm.name}' between {tuple(round(x) for x in a.xyz)} and {tuple(round(x) for x in b.xyz)} "
                      f"passes through '{through[0][0]}'.", loom=lm.name, part=through[0][0],
                      hint="Add waypoints round the part; keep the centre line one bundle radius off surfaces.")
        # bends at interior waypoints of fixed runs
        for i in range(1, len(lm.route) - 1):
            a, b, c_ = lm.route[i - 1], lm.route[i], lm.route[i + 1]
            if a.body != b.body or b.body != c_.body:
                continue
            u, v = np.subtract(b.xyz, a.xyz), np.subtract(c_.xyz, b.xyz)
            lu, lv = np.linalg.norm(u), np.linalg.norm(v)
            if lu < 1e-6 or lv < 1e-6:
                continue
            th = math.acos(max(-1.0, min(1.0, float(u @ v) / (lu * lv))))
            if th < math.radians(5):
                continue
            rr = min(lu, lv) / 2.0 / math.tan(th / 2.0)
            need = 0.5 * rb
            if rr < need:
                r.add("error", "bend_too_tight", f"Loom '{lm.name}' turns {math.degrees(th):.0f} deg at {tuple(round(x) for x in b.xyz)} with room for "
                      f"only a {rr:.0f} mm radius; a fixed bend of this {od:.0f} mm bundle needs {need:.0f} mm.", loom=lm.name, radius_mm=round(rr, 1),
                      needed_mm=round(need, 1), hint="Space the waypoints further apart around the corner or split the turn in two.")
    # ---- every wire: continuity across bodies, and insulation near hot parts
    hot = {n: t for n, t in el.hot_parts.items() if n in comps}
    hz = el.req("hot_zone_mm")
    for w in el.wires:
        pts = el.wire_points(w)
        for (b0, p0, f0), (b1, p1, _) in zip(pts, pts[1:]):
            if b0 != b1 and not f0:
                r.add("error", "wire_jumps_bodies", f"Wire '{w.name}' goes from body '{b0}' to body '{b1}' without a flexing loom span between them.",
                      wire=w.name, hint="Route it via a loom that crosses between those bodies (via=[...]).")
        if not hot or len(pts) < 2:
            continue
        dist_from_b = 0.0
        need = {}
        for (b0, p0, f0), (b1, p1, _) in zip(reversed(pts[:-1]), reversed(pts[1:])):     # walk from end b
            seg = float(np.linalg.norm(np.subtract(p0, p1)))
            if b0 == b1:
                sp = _sample(p1, p0, 5.0)
                for hn_, ht in hot.items():
                    hc_ = comps[hn_]
                    if hc_.body != b0:
                        continue      # looms on other bodies are covered by the moving-part clearance
                    region = ht.get("box") if isinstance(ht, dict) else None      # only part of the component is hot
                    ht = ht["temp"] if isinstance(ht, dict) else ht
                    bb = hc_.shape.bounding_box()
                    blo, bhi = (np.array(region[:3]), np.array(region[3:])) if region else (
                        np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z]))
                    lo, hi = blo - hz, bhi + hz
                    for k, pt in enumerate(sp):
                        if not ((pt >= lo).all() and (pt <= hi).all()):
                            continue
                        dd = (float(np.linalg.norm(np.maximum(np.maximum(blo - pt, pt - bhi), 0.0))) if region
                              else float(hc_.shape.distance_to(Vertex(*pt))))
                        if dd < hz:
                            s_b = dist_from_b + seg * k / max(len(sp) - 1, 1)
                            ins = w.pigtail[1] if (w.pigtail and s_b <= w.pigtail[0]) else w.insulation
                            if E.INSULATION_MAX_C.get(ins, 80.0) < ht:
                                need[hn_] = (ins, ht, round(s_b))
            dist_from_b += f0 or seg
        for hn_, (ins, ht, s_b) in need.items():
            r.add("error", "wire_not_rated_for_heat",
                  f"Wire '{w.name}' runs within {hz:g} mm of '{hn_}' ({ht:g} degC) about {s_b} mm from its {w.b} end, in {ins} insulation "
                  f"rated {E.INSULATION_MAX_C.get(ins, 80.0):g} degC.", wire=w.name, part=hn_, insulation=ins,
                  hint="Use silicone or PTFE wire there (or declare the device's own high-temperature lead with pigtail=(mm, insulation)), "
                       "or route it further from the hot part.")
    m["physical"] = out


def _near_world(sc, pts, radius, T, exclude=()):
    """Parts within `radius` of world-frame points at one pose (any body). [(name, distance)]"""
    out = []
    for b2 in sorted(set(sc.body)):
        if b2 not in T:
            continue
        Mi = np.linalg.inv(T[b2])
        loc = pts @ Mi[:3, :3].T + Mi[:3, 3]
        idx = [i for i, bb in enumerate(sc.body) if bb == b2 and sc.comps[i].name not in exclude]
        if not idx:
            continue
        bx = sc.box[idx]
        inside = ((loc[:, None, :] >= bx[None, :, :3] - radius) & (loc[:, None, :] <= bx[None, :, 3:] + radius)).all(axis=2)
        for pi, ci in zip(*np.nonzero(inside)):
            c = sc.comps[idx[ci]]
            try:
                dist = float(c.shape.distance_to(Vertex(*[float(x) for x in loc[pi]])))
            except Exception:
                continue
            if dist < radius:
                out.append((c.name, dist))
    return out


_Scene.near_world = staticmethod(_near_world)


# ====================================================================== bay temperature, motor temperature
def bay_temperature(el, circuit) -> dict:
    bay = el.bay
    amb = el.req("ambient_c")
    p = 0.0
    parts = {}
    for dn in bay.devices:
        d = el.devices.get(dn)
        if d is None:
            continue
        if d.kind == "psu":
            q = circuit["psu"]["loss_w"]
        elif d.kind == "board":
            q = d.ratings.get("logic_w", 1.5) + sum(v["loss_w"] for k, v in circuit["motors"].items() if k.startswith(f"_driver:{d.name}."))
            ib = circuit["board_current"].get(d.name, 0.0)
            q += sum(hv["current_a"] ** 2 * d.ratings.get("output_resistance_ohm", 0.0) for h, hv in circuit["heaters"].items()
                     if circuit["heater_feed"].get(h, {}).get("board") == d.name)
        elif d.kind == "mosfet":
            q = sum(hv["current_a"] ** 2 * d.ratings.get("resistance_ohm", 0.0) for h, hv in circuit["heaters"].items()
                    if circuit["heater_feed"].get(h, {}).get("module") == d.name)
        else:
            q = d.ratings.get("supply_w", 0.0)
        parts[dn] = round(q, 2)
        p += q

    def rise(fan_m3h):
        dt = 5.0
        for _ in range(60):
            g = 5.5 * bay.surface_m2 if bay.enclosed else 0.0
            # buoyancy-driven flow through the openings (orifice equation, Cd 0.6) plus any fan
            v = 0.6 * bay.vent_area_m2 * math.sqrt(2 * 9.81 * bay.height_m * max(dt, 1e-3) / (amb + 273.15)) + fan_m3h / 3600.0
            g += 1.16 * 1006.0 * v
            new = p / max(g, 1e-6)
            if abs(new - dt) < 0.01:
                break
            dt = 0.5 * dt + 0.5 * min(new, 500.0)
        return dt

    dt0, dt1 = rise(0.0), rise(bay.fan_m3h)
    return {"dissipated_w": round(p, 1), "by_device_w": parts, "rise_without_fan_k": round(dt0, 1), "air_temp_without_fan_c": round(amb + dt0, 1),
            "air_temp_c": round(amb + dt1, 1), "fan_m3h": bay.fan_m3h, "enclosed": bay.enclosed,
            "basis": "worst-case continuous dissipation; heat leaves by buoyant flow through the declared openings (orifice, Cd 0.6)"
                     + (", through the walls at 5.5 W/m^2K" if bay.enclosed else "") + (" and the fan" if bay.fan_m3h else "")}


def _bay_and_motors(ctx, r, m):
    design, el = ctx["design"], ctx["el"]
    c = ctx.get("circuit")
    if c is None:
        raise RuntimeError("no circuit solution")
    comps = {cc.name: cc for cc in design.components}
    amb = el.req("ambient_c")
    t_bay = amb
    if el.bay is None:
        r.add("error", "no_bay_declared", "The electronics bay is not declared (electrical.bay), so its temperature cannot be estimated.",
              hint="el.bay = Bay(devices=[...], enclosed=False, vent_area_m2=..., height_m=...)")
    else:
        b = bay_temperature(el, c)
        lim = el.req("bay_max_c")
        b["limit_c"] = lim
        b["fan_needed"] = b["air_temp_without_fan_c"] > lim
        m["bay"] = b
        t_bay = b["air_temp_c"]
        if b["air_temp_c"] > lim:
            r.add("error", "bay_too_hot",
                  f"Electronics bay air reaches about {b['air_temp_c']:.0f} degC ({b['dissipated_w']:.0f} W dissipated: {b['by_device_w']}); "
                  f"the supply is rated for full load only to {lim:g} degC.", bay_c=b["air_temp_c"], limit_c=lim,
                  hint="Open the bay, or add a fan (Bay(fan_m3h=...)) on a controller-fan output and include it in the wiring.")
        psu = next((d for d in el.devices.values() if d.kind == "psu"), None)
        if psu is not None and psu.name in el.bay.devices:
            full = psu.ratings.get("full_load_ambient_c", 50.0)
            allowed = 1.0 if t_bay <= full else max(0.0, 1.0 - (1.0 - psu.ratings.get("derate_to_frac_at_70c", 0.6)) * (t_bay - full) / (70.0 - full))
            b["psu_allowed_load_frac"] = round(allowed, 3)
            if c["psu"]["load_frac"] > allowed:
                r.add("error", "psu_derated", f"At {t_bay:.0f} degC the supply may deliver {allowed:.0%} of its rating; the load is {c['psu']['load_frac']:.0%}.")
    mt = {}
    lim = el.req("motor_max_case_c")
    for name, mv in c["motors"].items():
        if name.startswith("_driver"):
            continue
        d = el.devices[name]
        cc = comps.get(d.component)
        if cc is None:
            continue
        bb = cc.shape.bounding_box()
        area = 2 * (bb.size.X * bb.size.Y + bb.size.Y * bb.size.Z + bb.size.X * bb.size.Z) * 1e-6
        t_amb = t_bay if (el.bay and name in el.bay.devices) else amb
        rise = mv["copper_loss_w"] / (12.0 * area)
        mt[name] = {"copper_loss_w": mv["copper_loss_w"], "surface_m2": round(area, 4), "rise_k": round(rise, 1), "case_c": round(t_amb + rise, 1)}
        if t_amb + rise > lim:
            r.add("error", "motor_too_hot",
                  f"Motor '{name}' at {mv['motor_current_a']:.2f} A rms dissipates {mv['copper_loss_w']:.1f} W and settles about {rise:.0f} K above "
                  f"ambient ({t_amb + rise:.0f} degC case; limit {lim:g}).", device=name, part=d.component, case_c=round(t_amb + rise, 1), limit_c=lim,
                  hint="Lower run_current (torque falls in proportion below the corner speed), or use a lower-resistance winding.")
    m["motor_temperature"] = mt


# ====================================================================== artefacts
def _artifacts(ctx, r, m):
    design, el = ctx["design"], ctx["el"]
    c = ctx.get("circuit")
    if c is None:
        raise RuntimeError("no circuit solution")
    out = Path(OUT_ROOT) / design.name / "electrical"
    out.mkdir(parents=True, exist_ok=True)
    rows = E.wiring_rows(el, c)
    (out / "wiring.csv").write_text(E.wiring_table_csv(rows))
    pins = E.pin_map(el)
    md = [f"# Wiring of {design.name}", "", "Generated by the electrical verifier. Currents are worst-case simultaneous.", "",
          E.wiring_table_md(rows), "## Pin map", "", "| board | port | kind | pins | connected to |", "|---|---|---|---|---|"]
    md += [f"| {p['board']} | {p['port']} | {p['kind']} | {p['pins']} | {p['connected_to']} |" for p in pins]
    (out / "wiring.md").write_text("\n".join(md) + "\n")
    (out / "pin_map.json").write_text(json.dumps(pins, indent=1))
    arts = {"wiring_csv": str(out / "wiring.csv"), "wiring_md": str(out / "wiring.md"), "pin_map": str(out / "pin_map.json")}
    if el.firmware.get("kind", "klipper") == "klipper":
        sim = {hn: {"pid": h.get("pid")} for hn, h in (ctx.get("heaters") or {}).items()}
        cfg = E.klipper_config(el, design, sim)
        (out / "printer.cfg").write_text(cfg + "\n")
        arts["printer_cfg"] = str(out / "printer.cfg")
        board_pins = set()
        for d in el.devices.values():
            if d.kind == "board":
                for p in d.ports.values():
                    if isinstance(p.pin, str):
                        board_pins.add(p.pin)
                    elif isinstance(p.pin, dict):
                        board_pins |= {str(v).lstrip("!") for k, v in p.pin.items() if k != "uart_address"}
        from ..parts.electrical import THERMISTORS

        problems = E.check_klipper_config(cfg, board_pins, set(THERMISTORS))
        m["klipper_config_check"] = {"problems": problems, "method": "parsed with Klipper's configparser settings and checked against "
                                     "required options and the board's pins; NOT run through klippy (that needs an MCU dictionary from a firmware build)"}
        for pb in problems:
            r.add("error", "klipper_config_invalid", f"Generated printer.cfg: {pb}", hint="Usually a device that is not wired to a board port.")
    # electrical bill of materials
    bom, cost = {}, 0.0
    for d in el.devices.values():
        cc = next((x for x in design.components if x.name == d.component), None)
        if cc is not None and cc.cots:
            e = bom.setdefault(cc.sku or cc.name, {"qty": 0, "unit_cost_usd": cc.meta.get("cost_usd"), "parts": set()})
            if cc.name not in e["parts"]:
                e["parts"].add(cc.name)
                e["qty"] += 1
    for sku, e in design.bom_extras.items():
        if sku.startswith(("WIRE-", "CONN-", "SLEEVE-", "CABLE-TIE", "FUSE-", "RING-")):
            bom[sku] = {"qty": e["qty"], "unit_cost_usd": e["unit_cost_usd"], "parts": set()}
    for e in bom.values():
        e.pop("parts")
        cost += (e["unit_cost_usd"] or 0.0) * e["qty"]
    m["electrical_bom"] = bom
    m["electrical_bom_cost_usd"] = round(cost, 2)
    if not any(k.startswith("WIRE-") for k in bom):
        r.add("error", "wire_not_in_bom", "Wire and connectors are not in the bill of materials.",
              hint="Call mechloop.parts.electrical.add_electrical_bom(el, design) at the end of build().")
    m["artifacts"] = arts
    m["sources"] = {"physics_and_rules": E.SOURCES, "devices": {d.name: d.sources for d in el.devices.values() if d.sources}}


def heatup_for_print(design, bed_target: float | None = None) -> dict | None:
    """Time from cold until bed and hotend are both at temperature (they heat together), from the same simulation
    the verifier runs. Used by the digital twin. None when the design has no electrical model or no heaters."""
    el = getattr(design, "electrical", None)
    if el is None or not (el.firmware.get("heaters")):
        return None
    cache = el.__dict__.setdefault("_heatup_cache", {})
    if bed_target not in cache:
        E.axis_motors(el, design)
        rep = heater_report(el, design, E.solve_circuit(el, design), quick=True)
        times = {}
        for hn, h in rep.items():
            tg = min(h["targets_c"]) if h["kind"] == "bed" else max(h["targets_c"])
            if h["kind"] == "bed" and bed_target is not None:
                tg = min(h["targets_c"], key=lambda t: abs(t - bed_target))
            times[hn] = {"target_c": tg, "heatup_s": h["heatup_s"].get(tg)}
        vals = [v["heatup_s"] for v in times.values()]
        cache[bed_target] = {"heaters": times, "heatup_s": None if any(v is None for v in vals) else round(max(vals), 1),
                             "basis": "open-loop 100 % duty to target from ambient; bed at its lower target, hotend at its highest"}
    return cache[bed_target]
