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

    nearest: dict = {}

    def gap(q, point):
        T = forward_kinematics(design, {jn: float(q)})
        p = (T[sw.body] @ np.array([*point, 1.0]))[:3]
        best = 1e9
        nearest.clear()
        for c in design.components:
            moves_with_switch = (c.body == sw.body) or (_under(design, c.body, j.child) == _under(design, sw.body, j.child))
            if c.name == sw.name or moves_with_switch:
                continue
            local = (np.linalg.inv(T[c.body]) @ np.array([*p, 1.0]))[:3]
            bb = c.shape.bounding_box()
            lo, hi = np.array([bb.min.X, bb.min.Y, bb.min.Z]), np.array([bb.max.X, bb.max.Y, bb.max.Z])
            if float(np.linalg.norm(np.maximum(np.maximum(lo - local, local - hi), 0.0))) >= best:
                continue
            dd = surface_distance(c.shape, local)                    # 0 once the striker has passed the point
            if dd < best:
                best = dd
                nearest.update(part=c.name, local=local)
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
    if g_late <= REACH_TOL and case is not None and "clear_of_case_limit_mm" in out:
        try:
            out["window_under_tolerance"] = _endstop_window_scatter(design, e, sw, j, r, gap, nearest, latest, press, q_end,
                                                                     g_late, out["clear_of_case_limit_mm"],
                                                                     float(np.linalg.norm(case - latest)))
        except Exception as ex:      # not evaluated is not a pass
            out["window_under_tolerance"] = {"evaluated": False, "why": f"{type(ex).__name__}: {ex}"}
            r.add("warning", "endstop_window_not_evaluated",
                  f"Endstop {sw.name} on joint {jn}: its trigger window could not be put through the tolerance stack-up "
                  f"({type(ex).__name__}: {ex}); it was judged on drawn positions only.", joint=jn)
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


WINDOW_P_ERROR = 0.01      # share of builds outside a functional window above which it is an error (as for clearances)


def _endstop_window_scatter(design, e, sw, j, r, gap, nearest, latest, press, q_end, g_late, g_case, width) -> dict:
    """The endstop's trigger window with the machine as built. On the drawing the striker ends, at the end of the
    mechanical travel, between the switch's latest operating position and the point where the lever lies on the case
    (`width` apart: 0.25 mm on the OMRON D2F). As built, striker and switch are each where their own chain of parts and
    joints puts them: the stack-up's relative error along the lever's travel is added to the drawn position and the
    share of builds that end outside the window is reported (short: a late unit never switches; long: the lever is on
    the case). A switch whose position is SET at assembly (a slotted mount) takes that error out: declare
    Adjustment(name, "endstop", range_mm, joint=<joint>); the range must cover the error (99.7 %)."""
    from ..tolerance.clearance import Scatter
    from ..tolerance.stackup import build_for, std_error

    jn = j.name
    gap(q_end, latest)                       # who is the striker: the part nearest the point to be reached
    striker, local = nearest.get("part"), nearest.get("local")
    if striker is None:
        raise ValueError("no striker found")
    B = build_for(design)
    S = Scatter(design, B)
    comps = {c.name: c for c in design.components}
    T = forward_kinematics(design, {jn: float(q_end)})
    # the striker's point at the HOME pose of its own body; the switch's point is given at home already
    q = {jn: float(q_end)}
    # which side moves: displacement() adds the joint's travel for parts under the joint's child
    press_w = press / np.linalg.norm(press)
    da, db = S.displacement(sw.name, latest, q), S.displacement(striker, local, q)
    if da is None or db is None:
        raise ValueError(f"'{sw.name if da is None else striker}' is not tied to the stack-up")
    delta = (db - da) @ press_w + S.rng.normal(0.0, S.local_sd(sw.name, striker), B.n)
    s0 = -g_late if g_late > 1e-9 else width - g_case       # drawn position past the latest operating position
    pos = s0 + delta
    p_short = float((pos < -REACH_TOL).mean())
    p_long = float((pos > width - 0.02).mean())
    p_out = p_short + p_long
    need = float(np.percentile(np.abs(delta), 99.7))
    adj = next((a for a in design.adjustments if a.kind == "endstop" and a.joint in (None, jn)), None)
    out = {"evaluated": True, "striker": striker, "window_mm": [round(-REACH_TOL, 3), round(width - 0.02, 3)],
           "drawn_position_in_window_mm": round(s0, 3), "relative_error_sd_mm": round(float(delta.std()), 3),
           "relative_error_mm_99": round(need, 3), "p_outside_window": round(p_out, 4),
           "p_outside_window_standard_error": round(std_error(p_out, B.n), 4), "limit": WINDOW_P_ERROR,
           "p_late_unit_never_switches": round(p_short, 4), "p_lever_on_case": round(p_long, 4), "builds": B.n,
           "processes": S.chain_note(sw.name, striker, q)["processes"],
           "basis": "stack-up between switch and striker along the lever's travel, at the declared end of mechanical travel"}
    if adj is not None:
        out.update({"set_at_assembly": adj.name, "adjustment_needed_mm_99": round(need, 2), "adjustment_available_mm": adj.range_mm})
        if need > adj.range_mm:
            r.add("error", "adjustment_too_small",
                  f"Endstop {sw.name} on joint {jn}: setting the switch against its striker needs up to {need:.2f} mm, but "
                  f"'{adj.name}' gives {adj.range_mm} mm.", joint=jn, needed=round(need, 2))
        return out
    if p_out > 0.0:
        # A warning, not an error: the window is judged at the DECLARED end of mechanical travel, but nothing in the model
        # says what stops the axis there. A machine that homes on the switch signal and is never driven further works
        # with its switch a few tenths off (the reference kit in docs/REFERENCE_MACHINE.md does); what the share says is
        # that the drawn window itself is not something the parts can hold.
        r.add("warning", "endstop_window_under_tolerance",
              f"Endstop {sw.name} on joint {jn}: on the drawing {striker} ends {s0:+.2f} mm past the switch's latest operating "
              f"position, inside a window of {-REACH_TOL:g} to {width - 0.02:g} mm before the lever lies on the case. Built from "
              f"real parts the two are {delta.std():.2f} mm (one standard deviation) from where they are drawn relative to each "
              f"other: {p_out:.0%} of {B.n} simulated builds end outside the window (standard error "
              f"{std_error(p_out, B.n):.1%}, limit {WINDOW_P_ERROR:.0%}): in {p_short:.0%} a switch at the late end of its "
              f"spread never operates, in {p_long:.0%} the lever is pressed onto the case, IF the axis really goes "
              f"to its declared end of travel: what stops it there is not modelled, and a machine that only ever homes on the "
              f"switch signal is not affected.",
              joint=jn, **{k: v for k, v in out.items() if k != "basis"},
              hint=f"A {width:g} mm window cannot be held by part accuracy. Mount the switch on a slot and set it against the "
                   f"striker at assembly (declare Adjustment(name, 'endstop', range_mm >= {need:.1f}, joint='{jn}')), or let "
                   f"the striker pass alongside the lever (a ramp) so that over-travel cannot crush the switch, or use "
                   f"sensorless homing.")
    return out


METALS = ("steel", "stainless304", "al6061", "al5052", "al_mic6", "al_atp5", "brass")
CLAMP_RING_POINTS = 72          # samples round the nut's bearing circle
CLAMP_RING_MIN_FRAC = 0.75      # share of that circle that must have plate under it (6 of 8 points before 2026-11-15)


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
        # The ring of plate the nut bears on: a circle under the nut's bearing face, at mid-thickness of the plate,
        # sampled every 5 degrees from a direction fixed in the WORLD (not in the sensor: a round sensor turned about
        # its own axis must not change the answer). Material of ANY part on the sensor's body counts, so a fork closed
        # by a key is a complete ring; the sensor itself and its own nuts do not.
        rr = mt["thread_dia"] / 2 + 0.6 * (mt["nut_across_flats"] / 2 - mt["thread_dia"] / 2)      # under the nut's bearing face
        zm = (cl[0] + cl[1]) / 2
        ref = np.array([1.0, 0.0, 0.0]) if abs(z[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = ref - (ref @ z) * z
        u /= np.linalg.norm(u)
        v = np.cross(z, u)
        centre = o + zm * z
        others = [c for c in design.components if c is not pc and c.body == pc.body and c.meta.get("probe_nut_of") != name]
        boxes = {c.name: c.shape.bounding_box() for c in others}
        held: dict = {}
        covered = 0
        for k in range(CLAMP_RING_POINTS):
            a = 2 * np.pi * (k + 0.5) / CLAMP_RING_POINTS
            wp = centre + rr * (np.cos(a) * u + np.sin(a) * v)
            hit = False
            for c in others:
                bb = boxes[c.name]
                if not (bb.min.X - 1e-6 <= wp[0] <= bb.max.X + 1e-6 and bb.min.Y - 1e-6 <= wp[1] <= bb.max.Y + 1e-6
                        and bb.min.Z - 1e-6 <= wp[2] <= bb.max.Z + 1e-6):
                    continue
                if surface_distance(c.shape, wp) <= 1e-6:
                    held[c.name] = held.get(c.name, 0) + 1
                    hit = True
            covered += hit
        frac = covered / CLAMP_RING_POINTS
        best = max(held.items(), key=lambda kv: kv[1], default=(None, 0))
        out["clamped_in"], out["clamp_mm"] = best[0], [cl[0], cl[1]]
        out["clamp_ring_covered_frac"] = round(frac, 3)
        out["clamp_ring_parts"] = {k_: round(n_ / CLAMP_RING_POINTS, 3) for k_, n_ in sorted(held.items(), key=lambda kv: -kv[1])}
        if frac < CLAMP_RING_MIN_FRAC - 1e-9:
            r.add("error", "probe_not_clamped",
                  f"Bed probe '{name}': its two nuts are drawn {cl[0]:g} and {cl[1]:g} mm above the sensing face, but the parts on "
                  f"body '{pc.body}' fill only {frac:.0%} of the ring between them round the thread (the nut's bearing circle, "
                  f"{2 * rr:.1f} mm diameter; at least {CLAMP_RING_MIN_FRAC:.0%} is required"
                  + (f"; found: {out['clamp_ring_parts']}" if held else "; nothing is there") + ").", part=name,
                  covered_frac=round(frac, 3), parts=out["clamp_ring_parts"],
                  hint=f"Give the toolhead a plate or tab {cl[1] - cl[0]:g} mm thick there with a {mt['hole_dia']:g} mm hole, and "
                       "join the probe to it (design.join(probe, plate, 'clamped by its two nuts')). An open fork needs a key "
                       "that closes it; a closed hole needs the sensor's nuts as separate parts "
                       "(probe_omron_e2e(..., nuts='separate') and add_probe_nuts).")
        if mt.get("nuts") == "separate":
            # the two nuts are their own parts: each must be there, on the thread, with its bearing face on the plate
            seats = {}
            for c in design.components:
                if c.meta.get("probe_nut_of") == name and c.meta.get("placement") and c.body == pc.body:
                    Pn = np.array(c.meta["placement"], dtype=float)
                    off = Pn[:, 3] - o
                    seats[c.name] = (float(off @ z), float(np.linalg.norm(off - (off @ z) * z)), float(Pn[:, 2] @ z))
            front = [n_ for n_, (h, rad, dz) in seats.items() if abs(h - cl[0]) < 0.05 and rad < 0.05 and dz < -0.99]
            rear = [n_ for n_, (h, rad, dz) in seats.items() if abs(h - cl[1]) < 0.05 and rad < 0.05 and dz > 0.99]
            out["nuts"] = {"front": front, "rear": rear}
            if not front or not rear:
                r.add("error", "probe_nuts_missing",
                      f"Bed probe '{name}' was made with nuts='separate', but "
                      + " and ".join(w for w, ok in (("no nut bears on the plate's lower face", front), ("no nut bears on its upper face", rear)) if not ok)
                      + f" (clamp faces {cl[0]:g} and {cl[1]:g} mm above the sensing face).", part=name,
                      hint=f"Call add_probe_nuts(design, '{name}') after placing the probe.")
    # ---- metal-free zone of an unshielded sensor
    l, d = float(mt["head_proud_of_metal_l"]), float(mt["metal_free_dia_d"])
    out["metal_free_zone"] = {"dia_mm": d, "from_face_mm": l}
    if not mt["shielded"] and l > 0:
        zone = (Pos(0, 0, l / 2) * Cylinder(d / 2, l)).moved(loc)
        hits = []
        for c in design.components:
            if c is pc or c.name == bed or c.material not in METALS or c.meta.get("probe_nut_of") == name:
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
        try:
            out["metal_near_zone_under_tolerance"] = _zone_scatter(design, pc, zone, bed, name, {h["part"] for h in hits}, r, mt)
        except Exception as ex:
            out["metal_near_zone_under_tolerance"] = {"evaluated": False, "why": f"{type(ex).__name__}: {ex}"}
            r.add("warning", "probe_zone_not_evaluated",
                  f"Bed probe '{name}': its metal-free zone could not be put through the tolerance stack-up "
                  f"({type(ex).__name__}: {ex}); it was judged on drawn positions only.", part=name)
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


def _zone_scatter(design, pc, zone, bed, name, already: set, r, mt) -> dict:
    """Metal parts drawn just OUTSIDE an unshielded sensor's metal-free zone: with the toolhead as built, in what share
    of builds are they inside it? The zone rides on the sensor; the gap between it and each metal part of the same body
    closer than the clearance check's threshold is put through the stack-up (relative error of sensor and part along
    the gap), exactly as a gap between two parts is."""
    from ..tolerance.clearance import THRESHOLD_MM, Scatter, _exact, severity_of, share_closed
    from ..tolerance.stackup import build_for

    near = []
    S = None
    for c in design.components:
        if c is pc or c.name == bed or c.material not in METALS or c.meta.get("probe_nut_of") == name or c.body != pc.body:
            continue
        if c.name in already:
            continue
        zb, cb = zone.bounding_box(), c.shape.bounding_box()
        if (cb.min.X - zb.max.X > THRESHOLD_MM or zb.min.X - cb.max.X > THRESHOLD_MM or cb.min.Y - zb.max.Y > THRESHOLD_MM
                or zb.min.Y - cb.max.Y > THRESHOLD_MM or cb.min.Z - zb.max.Z > THRESHOLD_MM or zb.min.Z - cb.max.Z > THRESHOLD_MM):
            continue
        ex = _exact(zone, c.shape)
        if ex is None or ex[0] >= THRESHOLD_MM or ex[0] <= 1e-9:
            continue
        g, p_zone, p_part = ex
        if S is None:
            S = Scatter(design, build_for(design))
        rel = S.relative(pc.name, p_zone, c.name, p_part, {}, p_part - p_zone)
        if rel is None:
            near.append({"part": c.name, "gap_mm": round(g, 3), "evaluated": False})
            continue
        sh = share_closed(g, rel, WINDOW_P_ERROR)
        near.append({"part": c.name, "material": c.material, "gap_mm": round(g, 3), **sh, "severity": severity_of(sh)})
    for h in near:
        if not h.get("evaluated", True):
            r.add("warning", "probe_zone_not_evaluated", f"Bed probe '{name}': {h['part']} is {h['gap_mm']} mm outside its metal-free "
                  f"zone but is not tied to the stack-up, so whether it ends up inside was not evaluated.", part=name)
        elif h["severity"]:
            share = (f"in {h['p_closed']:.1%} of {h['builds']} simulated builds (standard error {h['p_closed_standard_error']:.1%}; "
                     f"limit {h['limit']:.0%})" if h["p_closed"] > 0 else
                     f"in none of {h['builds']} simulated builds, but by the spread in about {h['p_closed_normal_estimate']:.1g} of builds")
            r.add(h["severity"], "probe_metal_zone_under_tolerance",
                  f"Bed probe '{name}': {h['part']} ({h['material']}) is drawn {h['gap_mm']:.2f} mm outside the sensor's metal-free zone "
                  f"({mt['metal_free_dia_d']:g} mm diameter, {mt['head_proud_of_metal_l']:g} mm behind the face). As built the gap is "
                  f"{h['gap_mm']:.2f} +/-{h['gap_sd_mm']:.2f} mm (one standard deviation): the part is inside the zone {share}.",
                  part=name, metal_part=h["part"], **{k: v for k, v in h.items() if k not in ("part", "severity")},
                  hint=f"Keep metal at least {max(3.3 * h['gap_sd_mm'], 0.5):.1f} mm outside the zone, or mount the sensor and that "
                       f"part on one part.")
    return {"evaluated": True, "parts_within_mm": THRESHOLD_MM, "near": near}


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
    # The probe rides on the toolhead with the nozzle, so the Z over-travel (the z-offset stack-up between bed and
    # toolhead) is common to both and does not bring the bed to the probe. What can is local: the stack-up inside the
    # toolhead between sensing face and nozzle tip, and the bed not being flat over the distance between them. The
    # same margin applies on both sides: the face must be that far ABOVE the tip (or the face meets the bed when the
    # nozzle does), and the shortest unit must switch with the nozzle still that far above the bed (or, with the
    # face drawn that much too high or the bed that much higher under the nozzle, the nozzle is on the bed first).
    hm = None
    if pg["rides_with_nozzle"]:
        from ..tolerance.toolhead import height_margin

        pc_ = next(c for c in design.components if c.name == name)
        hm = height_margin(design, name, pc_.meta["interfaces"]["sensing_face"][0])
    if hm is not None:
        M = hm["margin_mm"]
        out["probe_to_nozzle_margin"] = {
            "margin_mm": M, "stackup_mm": hm["stackup_mm"], "stackup_basis": hm["stackup_basis"],
            "bed_rise_mm": hm["bed_rise_mm"], "bed_rise": hm["bed_rise"], **({"assumed": True} if hm.get("assumed") else {}),
            "largest_contributors": hm.get("largest_contributors"),
            "face_above_nozzle_mm": pg["face_above_nozzle_mm"], "face_clear_by_mm": round(pg["face_above_nozzle_mm"] - M, 3),
            "shortest_trigger_above_bed_mm": z_lo, "trigger_clear_by_mm": round(z_lo - M, 3),
            "face_window_mm": [M, round(pg["face_above_nozzle_mm"] + z_lo - M, 3)],
            "tolerance_aware": "yes: the margin on both sides is the toolhead's own stack-up between sensing face and "
                               "nozzle tip (99.7th percentile of the simulated builds) plus the bed's flatness",
            "note": "face_window_mm: sensing-face heights above the nozzle tip that keep the margin on both sides (empty when "
                    "the second is below the first). Declared Z over-travel does not enter: it is common to nozzle and probe."}
        if pg["face_above_nozzle_mm"] < M:
            r.add("error", "probe_face_below_nozzle_margin",
                  f"Bed probe '{name}': its sensing face is drawn {pg['face_above_nozzle_mm']:.2f} mm above the nozzle tip. Between "
                  f"face and tip the toolhead's own stack-up is {hm['stackup_mm']:.2f} mm (99.7 %) and the bed can stand "
                  f"{hm['bed_rise_mm']:.2f} mm higher under the probe than under the nozzle ({hm['bed_rise']['offset_mm']:g} mm "
                  f"away): the face needs {M:.2f} mm, or in some builds it meets the bed before the nozzle does.", part=name,
                  face_above_nozzle_mm=pg["face_above_nozzle_mm"], needed_mm=M, stackup_mm=hm["stackup_mm"],
                  bed_rise_mm=hm["bed_rise_mm"],
                  hint=f"Raise the sensing face to at least {M:.2f} mm above the nozzle tip, mount the probe closer to the nozzle, "
                       "or shorten the chain of parts between probe and nozzle.")
        elif 0.0 < z_lo < M:
            r.add("warning", "probe_trigger_margin_thin",
                  f"Bed probe '{name}': a unit at the short end of its spread ({what}) switches with the nozzle {z_lo:.2f} mm above "
                  f"the bed as drawn. The toolhead's stack-up between face and tip ({hm['stackup_mm']:.2f} mm, 99.7 %) and the bed's "
                  f"flatness over the {hm['bed_rise']['offset_mm']:g} mm between them ({hm['bed_rise_mm']:.2f} mm) add up to "
                  f"{M:.2f} mm: with the face that much too high, or the bed that much higher under the nozzle, the nozzle "
                  "touches first.", part=name, shortest_trigger_above_bed_mm=z_lo, margin_mm=M,
                  hint=f"Lower the face (it may come down to {M:.2f} mm above the tip), use a sensor with more range on this bed, "
                       "or set the sensor's height on the built machine with its nuts against a gauge and say so in the build "
                       "instructions (that removes the stack-up, not the bed's flatness).")
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
