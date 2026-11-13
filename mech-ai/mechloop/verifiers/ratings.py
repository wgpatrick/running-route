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
        if kind == "belt":
            travel_per_rev = drv.get("pulley_teeth", 20) * drv.get("belt_pitch", 2.0)
            eff = drv.get("efficiency", 0.95)
        elif kind == "leadscrew":
            travel_per_rev = drv["lead"]
            eff = drv.get("efficiency", 0.4)
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
        out[j.name] = {"motors": motors, "kind": kind, "motor_rpm_at_max_speed": round(rpm, 1),
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
            loads[jn] = {"blocks": len(blocks), "carried_mass_kg": round(m, 3),
                         "load_per_block_n": round(per_block, 2), "static_safety": round(sf, 1)}
            if sf < 3.0:
                r.add("error", "guide_overloaded",
                      f"Joint {jn}: {per_block:.0f} N per guide block vs static rating "
                      f"{blocks[0].ratings['static_load_n']:.0f} N (safety {sf:.1f} < 3).", joint=jn)
        if loads:
            r.metrics["guide_loads"] = loads
            r.add("info", "guide_moments_not_checked",
                  "Guide block checks use direct load only; moment loads from overhung masses are not included.")
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
        if any(c.ratings.get("approximate") for c in design.components):
            r.add("info", "approximate_ratings",
                  "Some part ratings are typical class values; confirm against the chosen vendor's datasheet.")
    return r
