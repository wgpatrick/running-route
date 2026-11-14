"""Off-the-shelf part checks: drive capability from the actual motor and
transmission, carriage/bearing load ratings, and a bill of materials."""
from __future__ import annotations

import math

import numpy as np

from ..model import Design
from ..report import VerifierResult, timed


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
        refs = {k: drv[k] for k in ("pulley", "screw", "nut", "coupler") if k in drv}
        bad = [v for v in refs.values() if v not in comps]
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
        out[j.name] = {"motors": motors, "kind": kind, **({"parts": refs} if refs else {}),
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
            if sf < 3.0:
                r.add("error", "guide_overloaded",
                      f"Joint {jn}: {per_block:.0f} N per guide block vs static rating "
                      f"{blocks[0].ratings['static_load_n']:.0f} N (safety {sf:.1f} < 3).", joint=jn)
        if loads:
            r.metrics["guide_loads"] = loads
            r.add("info", "guide_moments_approximate",
                  "Guide moment checks use the home pose and bounding-box centres of mass; treat them as estimates.")
        # bill of materials
        bom: dict[str, dict] = {}
        for c in design.components:
            if c.cots:
                if not c.meta.get("catalog"):
                    r.add("warning", "uncatalogued_cots",
                          f"{c.name} is marked off-the-shelf but did not come from the parts catalog "
                          f"(dimensions and ratings unverified).", part=c.name)
                e = bom.setdefault(c.sku or c.name, {"qty": 0, "mass_kg": 0.0, "unit_cost_usd": c.meta.get("cost_usd")})
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
