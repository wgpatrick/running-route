"""Off-the-shelf part checks: drive capability from the actual motor and
transmission, carriage/bearing load ratings, and a bill of materials."""
from __future__ import annotations

import math

import numpy as np

from ..model import Design
from ..report import VerifierResult, timed


# N/m radial stiffness of a small recirculating-ball block: ASSUMED. The fallback for a guide block whose catalogue part
# carries no maker's figure (`radial_stiffness_n_per_m`): an MGN12H at preload ZF (Hiwin publishes none for the clearance
# class), bearings, hand-made proxies. An MGN12H at Z0 / Z1 carries Hiwin's 63 / 81 N/um and does not use this.
BLOCK_K = 40e6


def block_track_length_m(block) -> float:
    """Length over which a guide block's balls bear on the rail (Hiwin's L1): from the part's own rating, the vendor
    table for an MGN12H, else 30 mm."""
    v = block.ratings.get("ball_track_length_m")
    if v:
        return float(v)
    if (block.sku or "") == "MGN12H":
        try:
            from ..parts import vendor_data

            return float(vendor_data("hiwin_mgn12")["parts"]["MGN12H_block"]["values"]["L1_mm"]) * 1e-3
        except Exception:
            pass
    return 0.030


def guide_tilt(design: Design, joint_name: str, point, k_n_per_m: float = BLOCK_K) -> dict | None:
    """How stiffly the guide blocks of one joint hold a point of the carried body against a force ALONG the rail.

    The force acts at `point` (world, home pose), off the rail by an arm r, so it turns the carried body about an axis
    across the rail. Each block is a spring of k_n_per_m spread along its ball track (length L): a block alone resists
    turning with k L^2 / 12, blocks spaced along the rail add k a_i^2 (a_i measured from their centroid), the same
    rule the cantilever check below uses. The stiffness left at the point is K_rot / r^2. The FEA cannot see this:
    it bonds block and rail. Returns None when the joint has no guide blocks."""
    blocks = [c for c in design.components if c.meta.get("guides") == joint_name and "static_load_n" in c.ratings]
    j = next((x for x in design.joints if x.name == joint_name), None)
    if not blocks or j is None:
        return None
    ax = np.array(j.axis, dtype=float) / np.linalg.norm(j.axis)
    pos = np.array([[b.shape.center().X, b.shape.center().Y, b.shape.center().Z] for b in blocks]) * 1e-3
    cen = pos.mean(axis=0)
    al = (pos - cen) @ ax
    track = block_track_length_m(blocks[0])
    d = np.asarray(point, dtype=float) * 1e-3 - cen
    arm = float(np.linalg.norm(d - (d @ ax) * ax))
    k_rot = float(k_n_per_m * (al ** 2).sum() + len(blocks) * k_n_per_m * track ** 2 / 12.0)      # N*m/rad
    return {"blocks": len(blocks), "block": blocks[0].sku, "spacing_along_rail_mm": round(float(al.max() - al.min()) * 1e3, 1),
            "ball_track_mm": round(track * 1e3, 1), "arm_mm": round(arm * 1e3, 1), "k_rot_nm_per_rad": round(k_rot, 1),
            "n_per_mm": (k_rot / arm ** 2) * 1e-3 if arm > 1e-6 else float("inf"), "block_stiffness_used_n_per_um": k_n_per_m * 1e-6}


def _torque_at(ratings: dict, rpm: float) -> float:
    hold = ratings["holding_torque_nmm"]
    curve = ratings.get("torque_curve_rpm_frac")
    if not curve:
        return hold * 0.7
    xs, ys = zip(*curve)
    return hold * float(np.interp(rpm, xs, ys))


def resolve_drives(design: Design, r: VerifierResult | None = None) -> dict:
    """Turn each joint's declared drive (motor + transmission) into the force
    available at the joint at its stated speed. Fills joint.max_effort."""
    comps = {c.name: c for c in design.components}
    out = {}
    if getattr(design, "electrical", None) is not None:
        # one answer for torque at speed: the curve the motor's winding, driver current and supply voltage give
        from ..electrical import apply_motor_curves

        apply_motor_curves(design)
    for j in design.joints:
        drv = getattr(j, "drive", None)
        if not drv:
            continue
        motors = [drv["motor"]] if isinstance(drv["motor"], str) else list(drv["motor"])
        missing = [m for m in motors if m not in comps or "holding_torque_nmm" not in comps[m].ratings]
        if missing:
            if r:
                r.add("error", "drive_motor_missing",
                      f"Joint {j.name}: drive motor(s) {missing} not found or have no torque rating.", joint=j.name)
            continue
        kind = drv["kind"]
        # transmission parts named in the drive must exist; their ratings fill in the numbers
        # a Z axis on several lead screws names them as lists: {"screw": [..], "nut": [..], "coupler": [..]}
        refs_all = {k: ([drv[k]] if isinstance(drv[k], str) else list(drv[k])) for k in ("pulley", "screw", "nut", "coupler") if k in drv}
        refs = {k: v[0] for k, v in refs_all.items() if v}
        bad = [x for v in refs_all.values() for x in v if x not in comps]
        if bad:
            if r:
                r.add("error", "drive_part_missing", f"Joint {j.name}: drive refers to {bad}, not in the design.",
                      joint=j.name)
            continue
        if kind == "belt":
            teeth = comps[refs["pulley"]].ratings.get("teeth") if "pulley" in refs else None
            travel_per_rev = (teeth or drv.get("pulley_teeth", 20)) * drv.get("belt_pitch", 2.0)
            eff = drv.get("efficiency", 0.95)
        elif kind == "leadscrew":
            sr = comps[refs["screw"]].ratings if "screw" in refs else {}
            if "lead" not in drv and "lead_mm" not in sr:
                if r:
                    r.add("error", "drive_incomplete", f"Joint {j.name}: leadscrew drive needs 'screw' (a catalog "
                          f"lead screw part) or 'lead'.", joint=j.name)
                continue
            travel_per_rev = drv.get("lead", sr.get("lead_mm"))
            eff = drv.get("efficiency", sr.get("efficiency", 0.35))
            if r and "screw" not in refs:
                r.add("warning", "drive_screw_not_named",
                      f"Joint {j.name}: name the lead screw part in the drive ('screw': ...) so its presence, "
                      f"lead and efficiency are checked.", joint=j.name)
        elif kind == "direct":  # hinge driven through a gear ratio
            travel_per_rev = 360.0 / drv.get("ratio", 1.0)
            eff = drv.get("efficiency", 0.9)
        else:
            if r:
                r.add("error", "drive_unknown_kind", f"Joint {j.name}: unknown drive kind '{kind}'.", joint=j.name)
            continue
        rpm = (j.max_speed or 0.0) / travel_per_rev * 60.0
        torque = sum(_torque_at(comps[m].ratings, rpm) for m in motors)
        max_rpm = min(comps[m].ratings.get("max_rpm", 1e9) for m in motors)
        if j.kind == "slide":
            effort = 2 * math.pi * torque * eff / travel_per_rev  # N
        else:
            effort = torque * eff * drv.get("ratio", 1.0)  # N*mm
        j.max_effort = round(effort, 2)
        j.drive_resolved = {"motors": motors, "travel_per_rev": travel_per_rev, "efficiency": eff, "kind": kind}
        # rotor inertia reflected to the joint: kg for a slide, kg*mm^2 for a hinge
        Jr = sum(comps[m].ratings.get("rotor_inertia_gcm2", 0.0) for m in motors) * 1e-7  # kg m^2
        if j.kind == "slide":
            j.reflected_inertia = Jr * (2 * math.pi / (travel_per_rev * 1e-3)) ** 2
        else:
            j.reflected_inertia = Jr * drv.get("ratio", 1.0) ** 2 * 1e6
        if kind == "leadscrew" and len(refs_all.get("screw", [])) > 1:
            leads = {comps[x].ratings.get("lead_mm") for x in refs_all["screw"]}
            if len(leads) > 1 and r:
                r.add("error", "drive_screws_differ", f"Joint {j.name}: its lead screws have different leads {sorted(map(str, leads))}; "
                      f"they cannot move one body together.", joint=j.name)
            j.drive_resolved["screws"] = list(refs_all["screw"])
        out[j.name] = {"motors": motors, "kind": kind, **({"parts": {k: (v if len(v) > 1 else v[0]) for k, v in refs_all.items()}} if refs_all else {}),
                       "reflected_rotor_inertia": round(j.reflected_inertia, 4), "motor_rpm_at_max_speed": round(rpm, 1),
                       "motor_torque_nmm_at_speed": round(torque, 1), "available_effort": j.max_effort,
                       "unit": "N" if j.kind == "slide" else "N*mm",
                       "resolution_per_full_step": round(travel_per_rev / 200, 4)}
        if r and rpm > max_rpm:
            r.add("error", "motor_overspeed",
                  f"Joint {j.name}: {j.max_speed} {'mm/s' if j.kind == 'slide' else 'deg/s'} needs {rpm:.0f} rpm, "
                  f"above the motor's {max_rpm:.0f} rpm.", joint=j.name,
                  hint="Use a larger pulley / higher lead, or lower the speed target.")
    return out


def belt_installation_tension(belt) -> tuple[float, str]:
    """Installation tension per span (N) of a belt: what the design declares (`Belt.tension`), else Gates' minimum
    recommended installation tension for the width (design manual Tables 7 and 8, p.65; interpolated between the listed
    widths 4, 6, 9 and 12 mm, in proportion to width outside them)."""
    if getattr(belt, "tension", None) is not None:
        return float(belt.tension), "declared on the belt (Belt.tension)"
    from ..parts import vendor_data

    tab = vendor_data("gates_gt2")["belt"]["installation_tension"]["minimum_tst_n"]
    ws = sorted((float(k[:-2]), float(v)) for k, v in tab.items())
    xs, ys = [w for w, _ in ws], [t for _, t in ws]
    w = float(belt.width)
    t = float(np.interp(w, xs, ys)) if xs[0] <= w <= xs[-1] else (ys[0] * w / xs[0] if w < xs[0] else ys[-1] * w / xs[-1])
    return t, f"default: Gates' minimum recommended installation tension for a {w:g} mm belt (design manual p.65)"


def belt_shaft_loads(design: Design, r: VerifierResult | None = None) -> dict:
    """Belt pull on each pulley that sits on a motor shaft, against the motor's radial shaft-load limit.

    A belt installed at tension T per span pulls a pulley it wraps with the vector sum of its two spans, T (u1 + u2)
    (2 T for a half turn). On a pulley carried by the motor shaft alone that is an overhung load, acting in the belt's
    plane at a distance a from the mounting face. The motor's limit F0 at distance L0 (catalogue rating
    `max_radial_load_n` at `max_radial_load_at_mm`) is carried to the belt plane at equal bending moment about the
    face: F_allowed = F0 * L0 / a. Motors without such a rating are listed but not judged. Home pose, belt at rest: under
    load the tight span rises and the slack span falls by about the same amount, so the sum barely changes."""
    from ..geom import forward_kinematics
    from .belts import route

    if not design.belts:
        return {}
    comps = {c.name: c for c in design.components}
    motors = [c for c in design.components if "holding_torque_nmm" in c.ratings and c.meta.get("placement")
              and (c.meta.get("interfaces") or {}).get("shaft_length")]
    T0 = forward_kinematics(design, {})
    out: dict = {}
    for b in design.belts:
        tension, basis = belt_installation_tension(b)
        try:
            rt = route(design, b, T0)
        except Exception:
            continue                      # the motion verifier reports a belt that cannot be routed
        segs = rt["segments"]
        n_nodes = len(b.path)
        for idx, node in enumerate(b.path):
            if node[0] != "pulley" or node[1] not in comps:
                continue
            pul = comps[node[1]]
            ctr = np.array(pul.meta["interfaces"]["belt_center"][0], dtype=float)
            motor = None
            for mc in motors:
                if mc.body != pul.body:
                    continue
                P = np.array(mc.meta["placement"], dtype=float)
                o, z = P[:, 3], P[:, 2]
                arm = float((ctr - o) @ z)
                off = float(np.linalg.norm((ctr - o) - arm * z))
                if off < 1.0 and -1.0 < arm <= float(mc.meta["interfaces"]["shaft_length"]) + 10.0:
                    motor = (mc, arm)
                    break
            if motor is None:
                continue
            mc, arm = motor
            # the spans that leave this pulley: segment idx starts here, segment idx-1 ends here
            dirs = []
            if idx < len(segs) and (rt["closed"] or idx < n_nodes - 1):
                p0, p1 = segs[idx]
                dirs.append((p1 - p0) / np.linalg.norm(p1 - p0))
            prev = (idx - 1) % n_nodes if rt["closed"] else idx - 1
            if prev >= 0 and prev < len(segs) and (rt["closed"] or idx > 0):
                p0, p1 = segs[prev]
                dirs.append((p0 - p1) / np.linalg.norm(p1 - p0))
            if not dirs:
                continue
            res = float(np.linalg.norm(tension * np.sum(dirs, axis=0)))
            lim, at = mc.ratings.get("max_radial_load_n"), mc.ratings.get("max_radial_load_at_mm")
            e = {"belt": b.name, "pulley": pul.name, "motor": mc.name, "motor_sku": mc.sku,
                 "tension_per_span_n": round(tension, 1), "tension_basis": basis, "belt_width_mm": b.width,
                 "wrap_deg": round(rt["wraps_deg"].get(pul.name, 0.0), 1), "shaft_load_n": round(res, 1),
                 "belt_plane_from_motor_face_mm": round(arm, 1)}
            supported = pul.name in tuple(getattr(b, "outboard_support", ()) or ())
            if supported:
                P = np.array(mc.meta["placement"], dtype=float)
                o, z = P[:, 3], P[:, 2]
                brg = [c for c in design.components if (c.sku or "").startswith("BRG-") and c.body == mc.body
                       and float((np.array(tuple(c.shape.center())) - o) @ z) > arm
                       and float(np.linalg.norm((np.array(tuple(c.shape.center())) - o)
                                                - ((np.array(tuple(c.shape.center())) - o) @ z) * z)) < 1.0]
                e["outboard_support"] = brg[0].name if brg else None
                if not brg and r is not None:
                    r.add("warning", "outboard_support_not_found",
                          f"Belt {b.name} declares an outboard support for pulley {pul.name}, but no catalog bearing sits on "
                          f"{mc.name}'s shaft axis beyond the pulley.", belt=b.name, pulley=pul.name, motor=mc.name)
                    supported = False
            if lim and at:
                allowed = float(lim) * float(at) / max(arm, 1e-6)
                e.update({"motor_limit_n": float(lim), "motor_limit_at_mm": float(at), "allowed_at_belt_plane_n": round(allowed, 1),
                          "limit_basis": mc.ratings.get("max_radial_load_basis", "catalogue rating"),
                          "load_over_allowed": round(res / allowed, 2)})
                if supported:
                    e["judged"] = "not judged: the shaft end is carried by an outboard bearing, the limit is for an overhung load"
                elif res > allowed and r is not None:
                    need_t = allowed / max(res / tension, 1e-9)
                    r.add("warning", "motor_shaft_radial_load",
                          f"Belt {b.name} pulls {res:.0f} N sideways on the shaft of {mc.name} ({mc.sku}) at {tension:.1f} N per "
                          f"span ({basis}), {arm:.1f} mm from the mounting face. The motor's limit is {float(lim):g} N at "
                          f"{float(at):g} mm ({e['limit_basis']}), i.e. {allowed:.0f} N at the belt plane: "
                          f"{res / allowed:.1f} times over.",
                          belt=b.name, motor=mc.name, pulley=pul.name, shaft_load_n=round(res, 1), allowed_n=round(allowed, 1),
                          tension_per_span_n=round(tension, 1), arm_mm=round(arm, 1), limit_n=float(lim), limit_at_mm=float(at),
                          tension_for_limit_n=round(need_t, 1),
                          hint=f"Carry the shaft end in an outboard support bearing (declare Belt.outboard_support), move the "
                               f"pulley closer to the motor face, use a motor with a larger shaft-load rating, or lower the "
                               f"tension: the limit is met at {need_t:.1f} N per span, which is "
                               f"{'below' if need_t < belt_installation_tension(type(b)(b.name, b.path, width=b.width))[0] else 'at or above'} "
                               f"Gates' minimum for this width.")
            else:
                e["judged"] = "not judged: the motor's catalogue entry has no radial shaft-load limit"
            out[f"{b.name}:{pul.name}"] = e
    return out


def verify_ratings(design: Design) -> VerifierResult:
    r = VerifierResult("ratings")
    with timed(r):
        drives = resolve_drives(design, r)
        if drives:
            r.metrics["drives"] = drives
        g = float(np.linalg.norm(design.gravity)) * 1e-3
        bodies = design.bodies()
        by_child = {j.child: j for j in design.joints}

        def carried_mass(body: str) -> float:
            m = sum(c.mass() for c in bodies.get(body, []))
            for j in design.joints:
                if j.parent == body:
                    m += carried_mass(j.child)
            return m

        def carried_com(body: str) -> np.ndarray:
            acc, mt = np.zeros(3), 0.0

            def walk(b):
                nonlocal acc, mt
                for c in bodies.get(b, []):
                    bb = c.shape.bounding_box()
                    ctr = np.array([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2])
                    acc = acc + c.mass() * ctr
                    mt += c.mass()
                for jj in design.joints:
                    if jj.parent == b:
                        walk(jj.child)

            walk(body)
            return acc / mt if mt else acc

        # guide blocks: components tagged with the joint they guide share the carried load
        guides: dict[str, list] = {}
        for c in design.components:
            jn = c.meta.get("guides")
            if jn and "static_load_n" in c.ratings:
                guides.setdefault(jn, []).append(c)
        loads = {}
        for jn, blocks in guides.items():
            j = next((x for x in design.joints if x.name == jn), None)
            if j is None:
                r.add("error", "guide_unknown_joint", f"Guide blocks reference unknown joint '{jn}'.")
                continue
            m = carried_mass(j.child)
            accel = (j.max_accel or 0.0) * 1e-3
            per_block = m * (g + accel) / len(blocks)
            sf = blocks[0].ratings["static_load_n"] / per_block if per_block > 0 else float("inf")
            # overhung load: moment of the carried mass about the centroid of the blocks
            com = carried_com(j.child)
            cen = np.mean([[b.shape.center().X, b.shape.center().Y, b.shape.center().Z] for b in blocks], axis=0)
            arm = (com - cen) * 1e-3
            gdir = np.array(design.gravity) / np.linalg.norm(design.gravity)
            moment = float(np.linalg.norm(np.cross(arm, m * (g + accel) * gdir)))  # N*m
            loads[jn] = {"blocks": len(blocks), "carried_mass_kg": round(m, 3),
                         "load_per_block_n": round(per_block, 2), "static_safety": round(sf, 1),
                         "overhang_mm": round(float(np.linalg.norm(arm)) * 1e3, 1), "moment_nm": round(moment, 3)}
            pcs = sorted({str(b.ratings.get("preload_class")) for b in blocks if b.ratings.get("preload_class")})
            if pcs:      # which preload class the block figures (rigidity, allowable parallelism) are for, and whether it was declared
                loads[jn]["preload_class"] = "/".join(pcs)
                loads[jn]["preload_class_basis"] = "; ".join(sorted({str(b.ratings.get("preload_class_basis")) for b in blocks}))
            rated_m = blocks[0].ratings.get("static_moment_nm")
            if rated_m:
                pos = np.array([[b.shape.center().X, b.shape.center().Y, b.shape.center().Z] for b in blocks])
                # only spacing ALONG the rail turns a pitch moment into a force couple; blocks side by
                # side on parallel rails each take their share of the moment directly (conservative)
                ax = np.array(j.axis, dtype=float) / np.linalg.norm(j.axis)
                along = (pos - cen) @ ax
                span = float(along.max() - along.min()) * 1e-3
                rails = max(1, len({round(float(x), 0) for x in np.linalg.norm((pos - cen) - np.outer(along, ax), axis=1)}))
                loads[jn]["block_spacing_along_rail_mm"] = round(span * 1e3, 1)
                if len(blocks) == 1 or span < 0.02:
                    moment = moment / len(blocks)
                    loads[jn]["moment_per_block_nm"] = round(moment, 3)
                    msf = rated_m / moment if moment > 0 else float("inf")
                    loads[jn]["moment_safety"] = round(min(msf, 9999.0), 1)
                    if msf < 3.0:
                        r.add("error", "guide_moment_overloaded",
                              f"Joint {jn}: {moment:.2f} N*m overhung moment per guide block (no spacing along the rail) vs static "
                              f"moment rating {rated_m:.1f} N*m (safety {msf:.1f} < 3).", joint=jn,
                              hint="Add a second block spaced along the rail, or bring the load's centre of mass over the block.")
                else:
                    couple = moment / span / max(1, len(blocks) // 2)
                    sf2 = blocks[0].ratings["static_load_n"] / (per_block + couple)
                    loads[jn]["couple_force_n"] = round(couple, 1)
                    loads[jn]["static_safety_with_moment"] = round(min(sf2, 9999.0), 1)
                    if sf2 < 3.0:
                        r.add("error", "guide_overloaded",
                              f"Joint {jn}: with the {moment:.2f} N*m overhung moment each block sees "
                              f"{per_block + couple:.0f} N (safety {sf2:.1f} < 3).", joint=jn)
            # Tilt of the carried body on the compliance of the guide blocks themselves (the FEA clamps parts at the
            # blocks, so it cannot see this). Each block is a spring of BLOCK_K along the load line; a block alone resists
            # tilting only over its own ball-track length, blocks spaced along the rail resist it as a couple.
            arm_len = float(np.linalg.norm(arm - (arm @ gdir) * gdir))        # horizontal overhang of the mass, m
            if rated_m and arm_len > 0.02 and abs(float(np.array(j.axis, dtype=float) @ gdir)) > 0.5:
                maker_k = min((b.ratings["radial_stiffness_n_per_m"] for b in blocks if b.ratings.get("radial_stiffness_n_per_m")),
                              default=None) if all(b.ratings.get("radial_stiffness_n_per_m") for b in blocks) else None
                k = float(maker_k if maker_k else BLOCK_K)
                track = float(blocks[0].ratings.get("ball_track_length_m", 0.030))
                classes = sorted({str(b.ratings.get("preload_class")) for b in blocks if b.ratings.get("preload_class")})
                pos_ = np.array([[b.shape.center().X, b.shape.center().Y, b.shape.center().Z] for b in blocks]) * 1e-3
                ax_ = np.array(j.axis, dtype=float) / np.linalg.norm(j.axis)
                al = (pos_ - pos_.mean(axis=0)) @ ax_
                k_tilt = float((k * al ** 2).sum() + len(blocks) * k * track ** 2 / 12.0)      # N*m/rad
                sag = 9.81 * arm_len / k_tilt * arm_len * 1e3                                # mm at the mass centre, per kg there
                f_tilt = float(np.sqrt(k_tilt / max(m * arm_len ** 2, 1e-9)) / (2 * np.pi))
                # A body that also sits on several lead-screw nuts does not hang from its blocks: the nuts are supports
                # (each holds along its screw only, which is all a floating nut can do). Then the same two figures come
                # from the body on ALL its supports: compliance c at the mass centre for a vertical load, sag = g c per
                # kg, nod frequency sqrt(1 / (m c)) / 2 pi. With guide blocks alone this is the formula above.
                nut_names = []
                try:
                    from . import bed_support as BS

                    lay_ = BS.joint_layout(design, j)
                    if len(lay_["nuts"]) >= 2 and lay_["kind"] == "leadscrew":
                        mdl_ = BS.support_model(design, lay_)
                        if mdl_["held"]:
                            res_ = BS.respond(mdl_, gdir, com)
                            c_mm_n = float(res_["at"](com) @ gdir)
                            if c_mm_n > 0:
                                nut_names = list(lay_["nuts"])
                                sag = 9.81 * c_mm_n
                                f_tilt = float(np.sqrt(1.0 / (m * c_mm_n * 1e-3)) / (2 * np.pi))
                                loads[jn]["supports_counted"] = {"guide_blocks": len(blocks), "lead_screw_nuts": nut_names,
                                                                 "nut_holds": "along its screw only (as a floating nut does)",
                                                                 "compliance_at_mass_centre_mm_per_n": round(c_mm_n, 6),
                                                                 "assumed": mdl_["assumed"]}
                except Exception as e_:
                    loads[jn]["supports_counted"] = {"error": f"{type(e_).__name__}: {e_}; guide blocks only"}
                loads[jn].update({"tilt_stiffness_nm_per_rad": round(k_tilt), "sag_at_mass_centre_mm_per_kg": round(sag, 4),
                                  "tilt_mode_hz": round(f_tilt, 1), "block_stiffness_assumed_n_per_um": round(k * 1e-6, 1),
                                  "block_stiffness_source": (blocks[0].ratings.get("radial_stiffness_source") if maker_k else None)
                                  or "assumed (ratings.BLOCK_K): no maker's rigidity figure for this block"
                                  + (f" at preload {'/'.join(classes)}" if classes else ""),
                                  "ball_track_mm": round(track * 1e3, 1)})
                if classes:
                    loads[jn]["preload_class"] = "/".join(classes)
                    loads[jn]["preload_class_basis"] = "; ".join(sorted({str(b.ratings.get("preload_class_basis")) for b in blocks}))
                if f_tilt < 100.0:
                    r.add("warning", "cantilever_on_guide_blocks",
                          f"Joint {jn}: the {m:.2f} kg it carries hangs {arm_len * 1e3:.0f} mm from its {len(blocks)} guide blocks, which "
                          f"have {float(al.max() - al.min()) * 1e3:.0f} mm of spacing along the rail"
                          + (f", and sits on {len(nut_names)} lead-screw nuts (counted as supports along their screws). On blocks and nuts "
                             f"together it" if nut_names else ". On the blocks' own give it")
                          + f" nods at about "
                          f"{f_tilt:.0f} Hz and sags {sag:.3f} mm per kg (estimate: block stiffness {k * 1e-6:.0f} N/um, "
                          + (f"the maker's radial figure at preload {'/'.join(classes)}, {loads[jn].get('preload_class_basis', '')})." if maker_k
                             else "assumed)."),
                          joint=jn, tilt_mode_hz=round(f_tilt, 1),
                          hint="Put two blocks on each rail, spaced along it, or support the body on a third point.")
            if sf < 3.0:
                r.add("error", "guide_overloaded",
                      f"Joint {jn}: {per_block:.0f} N per guide block vs static rating "
                      f"{blocks[0].ratings['static_load_n']:.0f} N (safety {sf:.1f} < 3).", joint=jn)
        if loads:
            r.metrics["guide_loads"] = loads
            r.add("info", "guide_moments_approximate",
                  "Guide moment checks use the home pose and bounding-box centres of mass; treat them as estimates.")
        try:
            sl = belt_shaft_loads(design, r)
            if sl:
                r.metrics["belt_shaft_loads"] = sl
        except Exception as e:      # a belt the routing check will report; never lose the other ratings checks to it
            r.add("warning", "belt_shaft_load_not_checked", f"Belt pull on motor shafts was not checked: {type(e).__name__}: {e}")
        # bill of materials
        bom: dict[str, dict] = {}
        for c in design.components:
            if c.cots:
                if not c.meta.get("catalog"):
                    r.add("warning", "uncatalogued_cots",
                          f"{c.name} is marked off-the-shelf but did not come from the parts catalog "
                          f"(dimensions and ratings unverified).", part=c.name)
                e = bom.setdefault(c.sku or c.name, {"qty": 0, "mass_kg": 0.0, "unit_cost_usd": c.meta.get("cost_usd")})
                if c.ratings.get("mcmaster_pn"):      # a recorded supplier part number, and whether it was confirmed
                    e["mcmaster_pn"], e["mcmaster_pn_status"] = c.ratings["mcmaster_pn"], c.ratings.get("mcmaster_pn_status")
                e["qty"] += 1
                e["mass_kg"] = round(e["mass_kg"] + c.mass(), 4)
        for sku, e in design.bom_extras.items():
            b = bom.setdefault(sku, {"qty": 0, "mass_kg": 0.0, "unit_cost_usd": e["unit_cost_usd"]})
            b["qty"] += e["qty"]
        if bom:
            r.metrics["bom"] = bom
            costs = [e["unit_cost_usd"] * e["qty"] for e in bom.values() if e["unit_cost_usd"] is not None]
            r.metrics["bom_cost_usd_estimate"] = round(sum(costs), 2)
        custom = [c.name for c in design.components if not c.cots]
        r.metrics["custom_parts"] = custom if len(custom) <= 40 else len(custom)
        # which off-the-shelf parts rest on vendor documents and which are still typical class values
        backed = sorted({c.sku or c.name for c in design.components if c.cots and c.meta.get("vendor_backed")})
        proxy = sorted({c.sku or c.name for c in design.components
                        if not c.meta.get("vendor_backed") and (c.ratings.get("approximate") or (c.cots and c.meta.get("catalog")))})
        if backed or proxy:
            r.metrics["vendor_backed_parts"] = backed
            r.metrics["unverified_parts"] = proxy
        if proxy:
            shown = ", ".join(proxy[:12]) + (f" and {len(proxy) - 12} more" if len(proxy) > 12 else "")
            r.add("info", "approximate_ratings",
                  f"{len(proxy)} off-the-shelf part type(s) still use typical class values, not vendor data: {shown}. "
                  f"Confirm against the chosen vendor's datasheet ({len(backed)} part type(s) are vendor-backed; "
                  f"see docs/VENDOR_DATA.md).", parts=proxy)
    return r
