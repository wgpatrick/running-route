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
            homed[jn] = _switch_checks(design, e, sw, joints[jn], r)
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
        poses = sample_poses(design, per_joint=7, n_random=10, mechanical=True) if design.joints else [{}]
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
                near, on = clamp_distance(design, body, pt)
                cab[c.name].setdefault("clamp_to_surface_mm", {})[body] = None if near is None else round(near, 2)
                if near is None or near > CLAMP_MAX_MM + 1e-6:
                    r.add("error", "cable_clamp_in_air",
                          f"Cable {c.name}: its clamp point on body '{body}' is "
                          + (f"{near:.1f} mm from the nearest surface ({on}); a clamp must be within {CLAMP_MAX_MM:g} mm of a part."
                             if near is not None else "on a body with no parts."),
                          cable=c.name, body=body, distance_mm=None if near is None else round(near, 2), nearest=on)
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


CLAMP_MAX_MM = 3.0      # a cable clamp point must be within this of the surface of a part on its body


def surface_distance(shape, point) -> float:
    """Distance from a point to a solid part: 0 inside it or on its surface, else the true distance to the nearest
    point of its surface (which may be in the middle of a flat face, not only on an edge or vertex). The CAD kernel's
    own shape-to-vertex distance treats a solid as its skin, so a point inside reads as its depth: that is corrected."""
    pt = tuple(float(x) for x in point)
    try:
        solids = list(shape.solids())
    except Exception:
        solids = []
    for so in solids:
        try:
            if so.is_inside(pt, 1e-6):
                return 0.0
        except Exception:
            pass
    try:
        return float(shape.distance_to(Vertex(*pt)))
    except Exception:
        return float("inf")


def clamp_distance(design: Design, body: str, point) -> tuple:
    """(distance, part name) from a cable clamp point to the nearest part on `body`: to its simulation solid or, where
    the catalogue part has a detail model (vendor CAD), to that, whichever is nearer. A clamp sits on the real part."""
    best, on = None, None
    p = np.array(point, dtype=float)
    for x in design.components:
        if x.body != body:
            continue
        for shp, what in ((x.shape, ""), (x.detail, " (its CAD model)")):
            if shp is None:
                continue
            bb = shp.bounding_box()
            lo, hi = np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z])
            box_d = float(np.linalg.norm(np.maximum(np.maximum(lo - p, p - hi), 0.0)))     # never more than the true distance
            if best is not None and box_d >= best:
                continue
            d = surface_distance(shp, point)
            if best is None or d < best:
                best, on = d, x.name + what
    return best, on


REACH_TOL = 0.1         # mm a striker may stop short of the latest operating position (numerical / drawing tolerance)
RETRACT_MM = 5.0        # Klipper's default homing_retract_dist: after backing off this far the switch must have let go


def _switch_checks(design: Design, e: dict, sw, j, r: VerifierResult) -> dict:
    """A lever switch homing one joint, with the switch's unit-to-unit spread.

    The switch operates when its lever is pushed to the operating position, which lies anywhere within
    +/-operating_position_tol of nominal (OMRON D2F hinge lever: 6.8 +/-1.5 mm). So at the end of the joint's mechanical
    travel (range plus declared over-travel) the striker must have pushed the lever to the LATEST operating position
    (`trigger_latest`), or some units never switch; and it must not push past the point where the lever lies on the
    switch case (`case_limit`). A unit at the other extreme switches earlier by up to twice the tolerance: the axis then
    homes that much before the end of travel, which costs working travel at the far end, and after backing off the
    lever must be released (earliest operating position plus the movement differential).
    Parts without the spread data (hand-made switches) are judged at their one trigger point as before."""
    jn = j.name
    itf = sw.meta["interfaces"]
    at = e.get("at", "min")
    q_work = j.range[0] if at == "min" else j.range[1]
    q_end = j.mechanical_range[0] if at == "min" else j.mechanical_range[1]
    P = np.vstack([np.array(sw.meta["placement"], dtype=float), [0, 0, 0, 1]]) if sw.meta.get("placement") else None
    trig = np.array(itf["trigger"][0], dtype=float)
    tol = float(itf.get("operating_position_tol", 0.0) or 0.0)
    press = None
    if P is not None and "press_direction" in itf:
        press = P[:3, :3] @ np.array(itf["press_direction"], dtype=float)
        press /= np.linalg.norm(press)

    def gap(q, point):
        T = forward_kinematics(design, {jn: float(q)})
        p = (T[sw.body] @ np.array([*point, 1.0]))[:3]
        best = 1e9
        for c in design.components:
            moves_with_switch = (c.body == sw.body) or (_under(design, c.body, j.child) == _under(design, sw.body, j.child))
            if c.name == sw.name or moves_with_switch:
                continue
            local = (np.linalg.inv(T[c.body]) @ np.array([*p, 1.0]))[:3]
            bb = c.shape.bounding_box()
            lo, hi = np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z])
            if float(np.linalg.norm(np.maximum(np.maximum(lo - local, local - hi), 0.0))) >= best:
                continue
            best = min(best, surface_distance(c.shape, local))       # 0 once the striker has passed the point
        return best

    out = {"switch": sw.name, "at": at, "gap_at_end_mm": round(gap(q_end, trig), 2)}
    if not tol or press is None:
        # a switch with one trigger point and no spread data: the earlier rule
        g_end = gap(q_end, trig)
        back = q_end + (3.0 if at == "min" else -3.0)
        g_back = gap(back, trig)
        out["gap_3mm_before_mm"] = round(g_back, 2)
        if g_end > 1.0:
            r.add("error", "endstop_not_reached",
                  f"Endstop {sw.name} on joint {jn}: at the {at} end of travel nothing comes within "
                  f"{g_end:.1f} mm of its trigger point, so it is never pressed.", joint=jn, gap=round(g_end, 2),
                  hint="Move the switch, or add a tab on the moving part that reaches its trigger point at the end of travel.")
        elif g_back < 0.3:
            r.add("warning", "endstop_always_pressed",
                  f"Endstop {sw.name} on joint {jn} is already touched 3 mm before the end of travel.", joint=jn)
        return out
    latest, earliest = trig + tol * press, trig - tol * press                # world points on the switch at home
    case = np.array(itf["case_limit"][0], dtype=float) if "case_limit" in itf else None
    md = float(itf.get("movement_differential", 0.0) or 0.0)
    g_nom, g_late = gap(q_end, trig), gap(q_end, latest)
    g_work_nom = gap(q_work, trig)
    out.update({"operating_position_tol_mm": tol, "mechanical_end": float(q_end), "working_end": float(q_work),
                "short_of_nominal_operating_position_mm": round(g_nom, 2),
                "short_of_latest_operating_position_mm": round(g_late, 2),
                "short_of_nominal_at_working_end_mm": round(g_work_nom, 2),
                "homes_before_end_of_travel_mm": [0.0, round(2 * tol, 2)],
                "overtravel_guaranteed_mm": itf.get("overtravel"), "overtravel_to_case_mm": itf.get("overtravel_to_case"),
                "note": "the axis must be stopped by the switch signal (homing), not by the striker: OMRON guarantees only "
                        f"{itf.get('overtravel')} mm of lever travel past each unit's own operating position"})
    where = "the end of its mechanical travel" if abs(q_end - q_work) > 1e-9 else f"the {at} end of travel"
    if g_late > REACH_TOL:
        r.add("error", "endstop_not_reached",
              f"Endstop {sw.name} on joint {jn}: at {where} ({jn}={q_end:g}) the striker stops {g_late:.2f} mm short of the "
              f"switch's latest operating position (nominal {g_nom:.2f} mm short; the operating position is nominal "
              f"+/-{tol:g} mm unit to unit), so "
              + ("it is never pressed." if g_nom > tol + 1e-6 else "a switch at the late end of that spread is never pressed."),
              joint=jn, gap=round(g_late, 2), short_of_latest_mm=round(g_late, 2), short_of_nominal_mm=round(g_nom, 2),
              operating_position_tol_mm=tol,
              hint=f"Move the switch {g_late:.2f} mm towards its striker along the lever's travel (or lengthen the striker, or "
                   f"declare that much over-travel on the joint if the axis really has it). The trigger point is "
                   f"interfaces['trigger']; the point to reach is interfaces['trigger_latest'].")
    elif case is not None:
        g_case = gap(q_end, case)
        out["clear_of_case_limit_mm"] = round(g_case, 2)
        if g_case < 0.02:
            r.add("error", "endstop_overtravel",
                  f"Endstop {sw.name} on joint {jn}: at {where} ({jn}={q_end:g}) the striker has pushed the lever down onto "
                  f"the switch case ({itf.get('overtravel_to_case')} mm below the latest operating position): the switch is "
                  f"crushed.", joint=jn, hint="Move the switch away from its striker: the striker must end between "
                                             "interfaces['trigger_latest'] and interfaces['case_limit'].")
    # release: after the firmware's retract move a unit at the EARLY end of the spread must have let go again
    back = q_end + (RETRACT_MM if at == "min" else -RETRACT_MM)
    g_rel = gap(back, earliest - md * press)
    out["clear_of_release_point_after_retract_mm"] = round(g_rel, 2)
    if g_late <= REACH_TOL and g_rel < 0.05:
        r.add("warning", "endstop_always_pressed",
              f"Endstop {sw.name} on joint {jn}: {RETRACT_MM:g} mm back from the end of travel the striker still holds the "
              f"lever at or below the release point of a switch at the early end of the spread (operating position +{tol:g} mm, "
              f"plus the {md:g} mm movement differential).", joint=jn)
    return out


METALS = ("steel", "stainless304", "al6061", "al5052", "al_mic6", "al_atp5", "brass")


def _probe_mount_checks(design: Design, name: str, r: VerifierResult) -> dict | None:
    """Mounting of a threaded cylindrical proximity sensor (a catalogue part with interfaces["mounting"]), by the
    maker's rules: it is clamped in a hole by its two nuts, and an UNSHIELDED sensor needs its sensing face `l` mm
    proud of any metal with a cylinder `d` mm in diameter round the head free of metal (OMRON E2E sheet p.25: M12
    15 / 40, M18 22 / 55). Metal inside that zone pulls the switching point in and can hold the sensor on. A shielded
    sensor may sit flush. The sensor's own nuts and the bed (its target) are not counted. Home pose."""
    from build123d import Cylinder, Pos

    from ..geom import location_from_matrix

    pc = next((c for c in design.components if c.name == name), None)
    mt = (pc.meta.get("interfaces") or {}).get("mounting") if pc is not None else None
    if not mt or not pc.meta.get("placement"):
        return None
    P = np.vstack([np.array(pc.meta["placement"], dtype=float), [0, 0, 0, 1]])
    loc = location_from_matrix(P)
    o, z = P[:3, 3], P[:3, 2]
    out = {"thread": mt["thread"], "shielded": mt["shielded"], "hole_dia_mm": mt["hole_dia"], "source": mt["source"]}
    bed = (design.printer or {}).get("bed")
    # ---- clamped by its two nuts in a plate
    cl = mt.get("clamp")
    if cl is None:
        r.add("error", "probe_mount_not_declared",
              f"Bed probe '{name}' is a threaded {mt['thread']} sensor held by two nuts through a {mt['hole_dia']:g} mm hole, but the "
              "part was made without `clamp=`: where its nuts sit is not declared.", part=name,
              hint="probe_omron_e2e(model, clamp=(z_lo, z_hi)): the two faces of the plate it is clamped in, above the sensing face.")
    else:
        rr = mt["thread_dia"] / 2 + 0.6 * (mt["nut_across_flats"] / 2 - mt["thread_dia"] / 2)      # under the nut's bearing face
        zm = (cl[0] + cl[1]) / 2
        held: dict = {}
        for k in range(8):
            a = 2 * np.pi * k / 8
            wp = (P @ np.array([rr * np.cos(a), rr * np.sin(a), zm, 1.0]))[:3]
            for c in design.components:
                if c is pc or c.body != pc.body:
                    continue
                bb = c.shape.bounding_box()
                if not (bb.min.X - 1e-6 <= wp[0] <= bb.max.X + 1e-6 and bb.min.Y - 1e-6 <= wp[1] <= bb.max.Y + 1e-6
                        and bb.min.Z - 1e-6 <= wp[2] <= bb.max.Z + 1e-6):
                    continue
                if surface_distance(c.shape, wp) <= 1e-6:
                    held[c.name] = held.get(c.name, 0) + 1
        best = max(held.items(), key=lambda kv: kv[1], default=(None, 0))
        out["clamped_in"], out["clamp_mm"] = best[0], [cl[0], cl[1]]
        if best[1] < 6:
            r.add("error", "probe_not_clamped",
                  f"Bed probe '{name}': its two nuts are drawn {cl[0]:g} and {cl[1]:g} mm above the sensing face, but no part on "
                  f"body '{pc.body}' fills the space between them round the thread (material under {best[1]} of 8 points of the "
                  "nut face).", part=name,
                  hint=f"Give the toolhead a plate or tab {cl[1] - cl[0]:g} mm thick there with a {mt['hole_dia']:g} mm hole, and "
                       "join the probe to it (design.join(probe, plate, 'clamped by its two nuts')).")
    # ---- metal-free zone of an unshielded sensor
    l, d = float(mt["head_proud_of_metal_l"]), float(mt["metal_free_dia_d"])
    out["metal_free_zone"] = {"dia_mm": d, "from_face_mm": l}
    if not mt["shielded"] and l > 0:
        zone = (Pos(0, 0, l / 2) * Cylinder(d / 2, l)).moved(loc)
        hits = []
        for c in design.components:
            if c is pc or c.name == bed or c.material not in METALS:
                continue
            if c.body != pc.body:
                continue                      # what rides with the sensor is always in its zone; the rest moves
            if not bboxes_overlap_shapes(c.shape, zone):
                continue
            try:
                common = c.shape & zone
                sols = list(common.solids()) if common is not None else []
            except Exception:
                sols = []
            vol = sum(x.volume for x in sols)
            if vol < 0.5:
                continue
            from build123d import Edge

            axis_seg = Edge.make_line(tuple(o), tuple(o + l * z))
            zs, rs = [], []
            for so in sols:
                for v in so.vertices():
                    zs.append(float((np.array([v.X, v.Y, v.Z]) - o) @ z))
                rs.append(float(so.distance_to(axis_seg)))            # true distance from the sensor's axis
            hits.append({"part": c.name, "material": c.material, "volume_mm3": round(vol, 1),
                         "nearest_to_face_mm": round(max(min(zs), 0.0), 2), "nearest_to_axis_mm": round(min(rs), 2)})
        out["metal_in_zone"] = hits
        if hits:
            worst = min(hits, key=lambda h: h["nearest_to_face_mm"])
            r.add("error", "probe_metal_in_clear_zone",
                  f"Bed probe '{name}' is an unshielded {mt['thread']} sensor: its sensing face must stand {l:g} mm proud of any "
                  f"metal, with {d:g} mm diameter round the head free of metal ({mt['source']}). In that zone: "
                  + ", ".join(f"{h['part']} ({h['material']}, from {h['nearest_to_face_mm']:g} mm behind the face, "
                              f"{h['nearest_to_axis_mm']:g} mm from the axis)" for h in sorted(hits, key=lambda h: h["nearest_to_face_mm"])[:6])
                  + ".", part=name, metal=hits, zone_dia_mm=d, zone_depth_mm=l,
                  hint=f"Clamp the sensor at least {l:g} mm behind its face (nearest metal now {worst['nearest_to_face_mm']:g} mm), keep "
                       f"other metal {d / 2:g} mm from its axis there, carry it on a plastic bracket, or use a shielded type "
                       "(flush-mountable, shorter range).")
    return out


def bboxes_overlap_shapes(a, b) -> bool:
    A, B = a.bounding_box(), b.bounding_box()
    return not (A.max.X < B.min.X or B.max.X < A.min.X or A.max.Y < B.min.Y or B.max.Y < A.min.Y or A.max.Z < B.min.Z or B.max.Z < A.min.Z)


def _probe_checks(design: Design, e: dict, r: VerifierResult) -> dict:
    """A bed probe homing Z: its real sensing distance against the bed and nozzle geometry. The probe must switch
    before the nozzle touches (for every unit within the sensing-distance spread), the Z travel must bring the bed
    within range, and the probe must be over the plate wherever it is asked to measure."""
    from ..electrical import probe_geometry

    name = e.get("probe")
    mount = _probe_mount_checks(design, name, r)
    try:
        pg = probe_geometry(design)
    except ValueError as ex:
        r.add("error", "probe_not_usable", f"Bed probe '{name}': {ex}.", part=name,
              hint="Give the probe part a 'sensing_face' interface and an electrical template of kind 'probe' "
                   "(mechloop.parts.electrical.inductive_probe_template), and set design.tool_point and printer['bed'].")
        return {"probe": name, "checked": False, **({"mounting": mount} if mount else {})}
    out = {"probe": name, "checked": True, **({"mounting": mount} if mount else {}), **{k: pg.get(k) for k in (
        "sensing_distance_range_mm", "temperature_drift_frac", "z_offset_range_unit_spread_mm",
        "target", "sensing_distance_mm", "sensing_distance_tolerance_frac", "repeatability_mm", "x_offset", "y_offset",
        "face_above_nozzle_mm", "z_offset", "z_offset_range_mm", "nozzle_above_bed_at_end_of_z_travel_mm", "edge_margin_mm",
        "nozzle_above_bed_at_end_of_working_z_range_mm", "z_overtravel_past_working_range_mm",
        "mesh_min", "mesh_max", "home_xy", "home_probe_xy", "print_area", "print_area_basis", "print_area_declared",
        "print_area_outside_nozzle_reach_mm", "nozzle_reach_over_plate", "unprobed_strip_mm", "assumed", "sources")}}
    off_reach = {k: v for k, v in (pg.get("print_area_outside_nozzle_reach_mm") or {}).items() if v > 0.05}
    if off_reach:
        r.add("error", "print_area_not_reachable",
              f"The declared print area ({pg['print_area_basis']}) extends past where the nozzle can be over the plate: "
              f"{off_reach} (mm).", strips=off_reach,
              hint="Extend the X/Y travel, enlarge or move the plate, or declare a smaller print area.")
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
    drift = pg.get("temperature_drift_frac") or 0.0
    what = (f"switching distance {sn:g} mm on {pg['target']} ({pg['sources'].get('switching_distance_' + pg['target'] + '_mm', 'not stated')}), "
            f"+/-{tol:.0%} unit to unit ({'assumed' if 'sensing_distance_tolerance_frac' in pg['assumed'] else 'from its ratings'})"
            + (f" and +/-{drift:.0%} with temperature" if drift else ""))
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
              needed_margin_mm=round(z_off - z_lo, 3),
              hint=f"Lower the probe so it switches at least {z_off - z_lo + 0.3:.1f} mm before the nozzle touches (1-2 mm is usual), "
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
              hint="Extend the Z travel toward the nozzle or lower the probe. The same travel is what lets a bed mesh "
                   "bring a low part of the bed up to the nozzle: with none in hand, low spots stay low.")
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
                  f"{pg['edge_margin_mm']:g} mm inside the plate edge, so strips of the print area are never probed: {strips} "
                  f"(mm wide; print area {pg.get('print_area_basis', '')}). The firmware holds the nearest measured value there.",
                  part=name, strips=strips,
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
