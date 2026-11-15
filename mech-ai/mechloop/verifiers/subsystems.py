"""The parts of a machine that are easy to leave out of the CAD and impossible to leave out of the
build: a way to home each axis, cables to everything electrical that moves, and for a printer an
extruder, cooling and electronics."""
from __future__ import annotations

import math

import numpy as np
from build123d import Vertex

from ..geom import forward_kinematics
from ..model import Design
from ..report import VerifierResult, timed
from .motion import sample_poses

ELECTRIC_SKU = ("NEMA", "HOTEND", "FAN", "ENDSTOP", "PROBE", "EXTRUDER", "CTRL", "PSU")


def _is_electric(c) -> bool:
    return bool(c.ratings.get("electrical")) or any((c.sku or "").startswith(p) for p in ELECTRIC_SKU)


def verify_subsystems(design: Design) -> VerifierResult:
    r = VerifierResult("subsystems")
    if not (design.joints or design.cables or design.endstops or design.printer):
        r.skipped = "nothing moves and nothing is declared"
        return r
    with timed(r):
        comps = {c.name: c for c in design.components}
        joints = {j.name: j for j in design.joints}
        m: dict = {}
        # ---- homing
        homed = {}
        for e in design.endstops:
            jn = e.get("joint")
            if jn not in joints:
                r.add("error", "endstop_unknown_joint", f"An endstop refers to joint '{jn}', which does not exist.")
                continue
            if e.get("sensorless"):
                homed[jn] = "sensorless"
                continue
            if e.get("probe"):
                homed[jn] = _probe_checks(design, e, r)
                continue
            sw = comps.get(e.get("switch"))
            if sw is None or "trigger" not in sw.meta.get("interfaces", {}):
                r.add("error", "endstop_missing_switch", f"Endstop for joint {jn}: '{e.get('switch')}' is not a catalog endstop switch.")
                continue
            j = joints[jn]
            q_end = j.range[0] if e.get("at", "min") == "min" else j.range[1]
            trig = np.array(sw.meta["interfaces"]["trigger"][0])
            other = j.child if sw.body != j.child and not _under(design, sw.body, j.child) else j.parent

            def gap(q):
                T = forward_kinematics(design, {jn: float(q)})
                p = (T[sw.body] @ np.array([*trig, 1.0]))[:3]
                best = 1e9
                for c in design.components:
                    moves_with_switch = (c.body == sw.body) or (_under(design, c.body, j.child) == _under(design, sw.body, j.child))
                    if c.name == sw.name or moves_with_switch:
                        continue
                    local = (np.linalg.inv(T[c.body]) @ np.array([*p, 1.0]))[:3]
                    try:
                        best = min(best, c.shape.distance_to(Vertex(*local)))
                    except Exception:
                        pass
                return best

            g_end = gap(q_end)
            back = q_end + (3.0 if e.get("at", "min") == "min" else -3.0)
            g_back = gap(back)
            homed[jn] = {"switch": sw.name, "at": e.get("at", "min"), "gap_at_end_mm": round(g_end, 2), "gap_3mm_before_mm": round(g_back, 2)}
            if g_end > 1.0:
                r.add("error", "endstop_not_reached",
                      f"Endstop {sw.name} on joint {jn}: at the {e.get('at', 'min')} end of travel nothing comes within "
                      f"{g_end:.1f} mm of its trigger point, so it is never pressed.", joint=jn, gap=round(g_end, 2),
                      hint="Move the switch, or add a tab on the moving part that reaches its trigger point at the end of travel.")
            elif g_back < 0.3:
                r.add("warning", "endstop_always_pressed",
                      f"Endstop {sw.name} on joint {jn} is already touched 3 mm before the end of travel.", joint=jn)
        if design.printer:
            for ax in ("x", "y", "z"):
                jn = design.printer.get(ax)
                if jn and jn not in homed:
                    r.add("error", "no_homing",
                          f"Axis {jn} has no endstop and is not declared sensorless: the machine cannot find its position at power-on.",
                          joint=jn, hint="Add a catalog endstop_switch() and list it in design.endstops, or declare "
                                         "{'joint': '" + jn + "', 'sensorless': True} if the drivers support stall detection.")
        if homed:
            m["homing"] = homed
        # ---- cables
        poses = sample_poses(design, per_joint=7, n_random=10) if design.joints else [{}]
        cab = {}
        cabled_bodies = set()
        for c in design.cables:
            (ba, pa), (bb, pb) = c.a, c.b
            cabled_bodies |= {ba, bb}
            dmax, dmin, worst = 0.0, 1e9, {}
            for q in poses:
                T = forward_kinematics(design, q)
                if ba not in T or bb not in T:
                    r.add("error", "cable_unknown_body", f"Cable {c.name} is attached to a body that does not exist.")
                    break
                A = (T[ba] @ np.array([*pa, 1.0]))[:3]
                B = (T[bb] @ np.array([*pb, 1.0]))[:3]
                d = float(np.linalg.norm(A - B))
                if d > dmax:
                    dmax, worst = d, q
                dmin = min(dmin, d)
            # the cable must reach the furthest position with a bend at each clamp, and still have room to fold when closest
            need = dmax + math.pi * c.min_bend_radius * 0.5
            cab[c.name] = {"length_mm": c.length, "furthest_apart_mm": round(dmax, 1), "closest_mm": round(dmin, 1),
                           "needed_mm": round(need, 1)}
            for body, pt in (c.a, c.b):
                near = min((x.shape.distance_to(Vertex(*pt)) for x in design.components if x.body == body), default=1e9)
                if near > 3.0:
                    r.add("error", "cable_clamp_in_air", f"Cable {c.name}: its clamp point on body '{body}' is {near:.0f} mm from any part.",
                          cable=c.name)
            if c.length < need:
                r.add("error", "cable_too_short",
                      f"Cable {c.name} is {c.length:.0f} mm but its ends get {dmax:.0f} mm apart at "
                      f"{ {k: round(v, 1) for k, v in worst.items()} }; with room to bend it needs at least {need:.0f} mm.",
                      cable=c.name, needed=round(need, 1), hint="Lengthen the cable or move a clamp point.")
            elif dmin < 2 * c.min_bend_radius and c.length - dmin > 4 * c.min_bend_radius * 4:
                r.add("warning", "cable_slack",
                      f"Cable {c.name} has {c.length - dmin:.0f} mm of slack when its ends are {dmin:.0f} mm apart; it needs a "
                      f"chain or guide so the loop does not snag.", cable=c.name)
        if cab:
            m["cables"] = cab
        moving_electrics = {}
        for c in design.components:
            if c.body != "world" and _is_electric(c):
                moving_electrics.setdefault(c.body, []).append(c.name)
        for body, names in moving_electrics.items():
            if body not in cabled_bodies:
                r.add("error", "no_cable_to_moving_electrics",
                      f"Body '{body}' carries {names[:4]} but no cable is routed to it.", body=body,
                      hint="Add a Cable from a clamp point on that body to one on the body it rides on (or the frame), "
                           "long enough for the whole travel.")
        # ---- printer essentials
        if design.printer:
            skus = [(c.sku or "") for c in design.components]
            tool_body = design.tool_point[0] if design.tool_point else None
            have = {"extruder": any(s.startswith("EXTRUDER") for s in skus) or design.printer.get("extruder") == "bowden",
                    "hotend_fan": any(s.startswith("FAN") and c.body == tool_body for s, c in zip(skus, design.components)),
                    "control_board": any(s.startswith("CTRL") for s in skus),
                    "power_supply": any(s.startswith("PSU") for s in skus)}
            m["printer_essentials"] = have
            if not have["extruder"]:
                r.add("error", "no_extruder", "The printer has a hotend but nothing that feeds filament into it.",
                      hint="Add a catalog extruder_direct() on the toolhead (its mass counts), or declare a bowden extruder on the frame.")
            if not have["hotend_fan"]:
                r.add("error", "no_hotend_cooling", "No fan on the toolhead: an all-metal hotend jams without one.",
                      hint="Add a catalog fan(30) on the toolhead for the heat sink, and usually a second for part cooling.")
            for k_, what in (("control_board", "control board"), ("power_supply", "power supply")):
                if not have[k_]:
                    r.add("error", "no_electronics", f"The design has no {what}; it needs a place on the frame and its mass and "
                          f"volume are missing.", hint="Add the catalog part, mounted to the frame with screws.")
            motors = [c for c in design.components if (c.sku or "").startswith("NEMA")] + \
                     [c for c in design.components if (c.sku or "").startswith("EXTRUDER")]
            drivers = max([c.ratings.get("stepper_drivers", 0) for c in design.components] or [0])
            m["motors"], m["stepper_drivers"] = len(motors), drivers
            shared = 0
            if getattr(design, "electrical", None) is not None:
                # motors wired together to one driver (declared in the electrical model, where the current each one
                # then gets and its torque at speed are checked) need one driver between them
                from ..electrical import motor_groups

                shared = sum(len(g["motors"]) - 1 for g in motor_groups(design.electrical).values())
                m["motors_sharing_a_driver"] = shared
            if have["control_board"] and len(motors) - shared > drivers:
                r.add("error", "not_enough_drivers", f"{len(motors)} motors (including the extruder) but the control board drives {drivers}.",
                      hint="Wire two motors of one axis to one driver (note it), or use a board with more drivers.")
        r.metrics = m
    return r


def _probe_checks(design: Design, e: dict, r: VerifierResult) -> dict:
    """A bed probe homing Z: its real sensing distance against the bed and nozzle geometry. The probe must switch
    before the nozzle touches (for every unit within the sensing-distance spread), the Z travel must bring the bed
    within range, and the probe must be over the plate wherever it is asked to measure."""
    from ..electrical import probe_geometry

    name = e.get("probe")
    try:
        pg = probe_geometry(design)
    except ValueError as ex:
        r.add("error", "probe_not_usable", f"Bed probe '{name}': {ex}.", part=name,
              hint="Give the probe part a 'sensing_face' interface and an electrical template of kind 'probe' "
                   "(mechloop.parts.electrical.inductive_probe_template), and set design.tool_point and printer['bed'].")
        return {"probe": name, "checked": False}
    out = {"probe": name, "checked": True, **{k: pg.get(k) for k in (
        "target", "sensing_distance_mm", "sensing_distance_tolerance_frac", "repeatability_mm", "x_offset", "y_offset",
        "face_above_nozzle_mm", "z_offset", "z_offset_range_mm", "nozzle_above_bed_at_end_of_z_travel_mm", "edge_margin_mm",
        "mesh_min", "mesh_max", "home_xy", "home_probe_xy", "print_area", "unprobed_strip_mm", "assumed", "sources")}}
    if not pg["rides_with_nozzle"]:
        r.add("error", "probe_not_on_toolhead", f"Bed probe '{name}' is on body '{pg['on_body']}', not on the body that carries the "
              "nozzle: its offset from the nozzle is not fixed.", part=name)
    if pg["sensing_distance_mm"] is None:
        r.add("error", "probe_cannot_sense_bed",
              f"Bed probe '{name}' has no switching distance for the bed's material ('{pg['bed_material']}'): an inductive probe "
              "senses metal only, and its range depends on which.", part=name,
              hint="Use a metal bed plate (or a steel sheet on it) and give the probe a switching_distance_<steel|aluminium>_mm rating.")
        return out
    sn, tol = pg["sensing_distance_mm"], pg["sensing_distance_tolerance_frac"]
    z_off, (z_lo, z_hi) = pg["z_offset"], pg["z_offset_range_mm"]
    what = (f"switching distance {sn:g} mm on {pg['target']} ({pg['sources'].get('switching_distance_' + pg['target'] + '_mm', 'not stated')}), "
            f"+/-{tol:.0%} unit to unit ({'assumed' if 'sensing_distance_tolerance_frac' in pg['assumed'] else 'from its ratings'})")
    if z_off <= 0.0:
        r.add("error", "probe_triggers_after_nozzle_touches",
              f"Bed probe '{name}': its sensing face is {pg['face_above_nozzle_mm']:.2f} mm above the nozzle tip and it switches "
              f"{sn:g} mm from the bed, so the nozzle reaches the bed {-z_off:.2f} mm before the probe switches.", part=name,
              z_offset=z_off, hint="Mount the probe lower (face above the nozzle by less than its switching distance, with margin).")
    elif z_lo <= 0.0:
        r.add("error", "probe_trigger_margin",
              f"Bed probe '{name}' switches with the nozzle only {z_off:.2f} mm above the bed ({what}). A unit at the short end "
              f"of that spread switches at {z_lo:+.2f} mm, i.e. the nozzle is on the bed first; the firmware's z_offset cannot "
              f"correct that, it can only be positive.", part=name, z_offset=z_off, z_offset_range=[z_lo, z_hi],
              needed_margin_mm=round(tol * sn, 3),
              hint=f"Lower the probe so it switches at least {tol * sn + 0.3:.1f} mm before the nozzle touches (1-2 mm is usual), "
                   "or mount it on a slot so its height can be set on the machine.")
    if pg["face_above_nozzle_mm"] < 1.0:
        r.add("warning", "probe_face_near_nozzle_plane",
              f"Bed probe '{name}': its face is {pg['face_above_nozzle_mm']:.2f} mm above the nozzle tip; a curled print edge "
              "will hit it.", part=name)
    end = pg.get("nozzle_above_bed_at_end_of_z_travel_mm")
    if end is not None and end > z_lo:
        r.add("error", "probe_not_reached",
              f"Bed probe '{name}': at the end of Z travel the nozzle is still {end:.2f} mm above the bed; a unit at the short "
              f"end of its range does not switch until {z_lo:.2f} mm.", part=name, joint=e.get("joint"),
              hint="Extend the Z travel toward the nozzle or lower the probe.")
    if "mesh_min" in pg:
        (mx0, my0), (mx1, my1) = pg["mesh_min"], pg["mesh_max"]
        if mx1 - mx0 < 10.0 or my1 - my0 < 10.0:
            r.add("error", "probe_cannot_reach_bed",
                  f"Bed probe '{name}': the area where it is both over the plate (inset {pg['edge_margin_mm']:g} mm) and within "
                  f"X/Y travel is {max(mx1 - mx0, 0):.0f} x {max(my1 - my0, 0):.0f} mm.", part=name)
        hx, hy = pg["home_probe_xy"]
        m_ = pg["edge_margin_mm"]
        if not (pg["bed_min"][0] + m_ <= hx <= pg["bed_max"][0] - m_ and pg["bed_min"][1] + m_ <= hy <= pg["bed_max"][1] - m_):
            r.add("error", "probe_off_bed_when_homing",
                  f"Bed probe '{name}': with the nozzle at the Z-homing position {pg['home_xy']} the probe is at ({hx:g}, {hy:g}), "
                  "not over the plate.", part=name)
        strips = {k: v for k, v in pg["unprobed_strip_mm"].items() if v > 1.0}
        if strips:
            r.add("warning", "bed_mesh_does_not_cover_print_area",
                  f"Bed probe '{name}' is offset ({pg['x_offset']:g}, {pg['y_offset']:g}) mm from the nozzle and kept "
                  f"{pg['edge_margin_mm']:g} mm inside the plate edge, so strips of the printable area are never probed: {strips} "
                  "(mm wide). The firmware holds the nearest measured value there.", part=name, strips=strips,
                  hint="Acceptable if the bed is flat at the edges; otherwise move the probe closer to the nozzle or shrink the print area.")
    return out


def _under(design: Design, body: str, ancestor: str) -> bool:
    parent = {j.child: j.parent for j in design.joints}
    while True:
        if body == ancestor:
            return True
        if body not in parent:
            return False
        body = parent[body]
