"""Digital twin of a printer design: slice a part, plan the motion like firmware
does, run it on the machine's stepper dynamics, lay material down where the
simulated nozzle actually went, and compare the result with the intended part.

Modelled: G-code from a real slicer, look-ahead planning with the machine's own
speed/acceleration limits, axis masses from the CAD, motor torque curves, step
loss, extruder lag, bead width from extruded volume, machine collisions along
the print.
Not modelled: heat (melting, cooling, warping, bed adhesion), pressure advance,
ooze and stringing, belt stretch, frame flex, vibration of the printed part.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..geom import forward_kinematics
from ..model import Design
from ..report import VerifierResult


@dataclass
class PrinterMap:
    """How G-code axes map onto the design's joints."""

    x: str = "x"
    y: str = "y"
    z: str = "z"
    bed: str = "bed"  # component whose top face is the print surface
    layer_height: float = 0.2
    nozzle: float = 0.4
    filament_diameter: float = 1.75
    friction_n: dict = field(default_factory=lambda: {"x": 2.0, "y": 3.0, "z": 5.0})  # assumed rail/screw friction
    extruder_lag_s: float = 0.03  # first-order melt-flow lag (assumed)
    damping_ratio: float = 0.25  # of the stepper's electromagnetic spring (assumed)
    filament_density: float = 1.24  # g/cm^3 (PLA)
    compliant: bool = True  # belts stretch and the frame flexes; False = perfectly rigid machine
    # belt tensile stiffness EA (N per unit strain) for 6 mm glass-fibre GT2. 15 kN is a hobby measurement
    # (RepRap wiki); no manufacturer figure exists, so treat it as +/- 30 %. 9 mm belt: about 22 kN.
    belt_ea_n: float = 15000.0
    struct_stiffness: dict = field(default_factory=dict)  # nozzle stiffness from FEA, N/mm, e.g. {"x": 3000}
    backlash_mm: dict = field(default_factory=dict)  # lost motion per axis (slack belt, loose pulley)
    spring_damping_ratio: float = 0.05  # of belt/frame vibration (assumed)
    raster_px_per_mm: int = 20


def _axis_info(design: Design, pm: PrinterMap):
    from ..verifiers.ratings import resolve_drives

    resolve_drives(design)
    joints = {j.name: j for j in design.joints}
    for n in (pm.x, pm.y, pm.z):
        if n not in joints:
            raise ValueError(f"design has no joint '{n}'")
        if joints[n].kind != "slide":
            raise ValueError("the twin supports sliding axes only")
    if design.tool_point is None:
        raise ValueError("design.tool_point (the nozzle tip) is not set")
    comps = {c.name: c for c in design.components}
    if pm.bed not in comps:
        raise ValueError(f"design has no bed component '{pm.bed}'")
    bed = comps[pm.bed]
    bb = bed.shape.bounding_box()
    T0 = forward_kinematics(design, {})
    body, p = design.tool_point
    noz = (T0[body] @ np.array([*p, 1.0]))[:3]
    info = {"bed_center": np.array([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2]),
            "bed_size": (bb.size.X, bb.size.Y), "bed_top": bb.max.Z, "nozzle": noz,
            "gap0": float(noz[2] - bb.max.Z)}
    jx, jy, jz = joints[pm.x], joints[pm.y], joints[pm.z]
    info["sx"] = float(np.sign(jx.axis[0])) or 1.0
    info["sy"] = float(np.sign(jy.axis[1])) or 1.0
    # does +z joint travel bring the bed toward the nozzle?
    info["sz"] = float(np.sign(jz.axis[2])) * (1.0 if bed.body == jz.child or _descends(design, bed.body, jz.child) else -1.0)
    return joints, info


def _descends(design: Design, body: str, ancestor: str) -> bool:
    parent = {j.child: j.parent for j in design.joints}
    while body in parent:
        if body == ancestor:
            return True
        body = parent[body]
    return body == ancestor


def to_joints(info: dict, gx, gy, gz):
    """G-code position (bed-centred XY, Z above the bed) -> joint values."""
    qx = (info["bed_center"][0] + gx - info["nozzle"][0]) * info["sx"]
    qy = (info["bed_center"][1] + gy - info["nozzle"][1]) * info["sy"]
    qz = (info["gap0"] - gz) * info["sz"]
    return qx, qy, qz


def from_joints(info: dict, q):
    """Joint values -> nozzle position in the bed frame (x, y, height above bed)."""
    gx = info["nozzle"][0] + info["sx"] * q[..., 0] - info["bed_center"][0]
    gy = info["nozzle"][1] + info["sy"] * q[..., 1] - info["bed_center"][1]
    gz = info["gap0"] - info["sz"] * q[..., 2]
    return gx, gy, gz


def run_print(design: Design, part, out: Path, pm: PrinterMap | None = None, name: str = "part",
              dt: float = 0.001, render: bool = True, slicer_args: dict | None = None,
              accel_scale: float = 1.0, torque_scale: float = 1.0, speed_scale: float = 1.0,
              at: tuple = (0.0, 0.0), z_datum_error: float = 0.0, mass_extra: dict | None = None,
              gcode_edit=None, collisions: bool = True) -> dict:
    """Print `part` (a build123d shape sitting on Z=0, centred on XY) on `design`.
    Returns a report dict and writes artefacts into `out`. accel_scale multiplies the
    joints' acceleration limits and torque_scale the motor torque (e.g. reduced driver current)
    for what-if runs. speed_scale multiplies slicer speeds and XY speed limits. `at` places the part
    on the bed (mm from bed centre). z_datum_error is how far the real nozzle sits above (+) or below (-)
    where the firmware believes it is. mass_extra adds kg to axes, e.g. {"x": 0.3, "y": 0.3}.
    gcode_edit(moves) -> moves lets a test tamper with the program."""
    from build123d import export_stl

    from . import deposit as dep
    from .gcode import parse, slice_part
    from .planner import plan
    from .stepper import simulate

    pm = pm or PrinterMap()
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    r = VerifierResult("print")
    t0 = time.time()
    rep: dict = {"design": design.name, "part": name}
    wi = {"accel_scale": accel_scale, "torque_scale": torque_scale, "speed_scale": speed_scale,
          "z_datum_error": z_datum_error}
    if any(v != d0 for v, d0 in zip(wi.values(), (1.0, 1.0, 1.0, 0.0))) or mass_extra:
        rep["what_if"] = {**wi, "mass_extra": mass_extra or {}}

    def finish():
        rep["ok"] = r.ok
        rep["findings"] = [{"severity": f.severity, "code": f.code, "message": f.message, "data": f.data}
                           for f in r.findings]
        rep["seconds"] = round(time.time() - t0, 1)
        (out / "print_report.json").write_text(json.dumps(rep, indent=1, default=float))
        return rep

    try:
        joints, info = _axis_info(design, pm)
    except ValueError as e:
        r.add("error", "twin_setup", str(e))
        return finish()
    bb = part.bounding_box()
    rep["part_size_mm"] = [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)]
    stl, gpath = out / f"{name}.stl", out / f"{name}.gcode"
    export_stl(part, str(stl), tolerance=0.01, angular_tolerance=0.1)
    jl = [joints[pm.x], joints[pm.y], joints[pm.z]]
    try:
        sa = {"perimeter_speed": 45.0 * speed_scale, "infill_speed": 60.0 * speed_scale,
              "travel_speed": 150.0 * speed_scale, "center": at,
              "machine": {"accel": jl[0].max_accel * accel_scale, "speed": jl[0].max_speed * speed_scale,
                          "z_speed": jl[2].max_speed, "z_accel": jl[2].max_accel},
              **(slicer_args or {})}
        slice_part(stl, gpath, layer_height=pm.layer_height, nozzle=pm.nozzle,
                   filament_diameter=pm.filament_diameter, **sa)
    except RuntimeError as e:
        r.add("error", "slicer_failed", str(e))
        return finish()
    moves, ignored = parse(gpath)
    from .gcode import slicer_estimates

    rep["slicer"] = slicer_estimates(gpath)
    if gcode_edit is not None:
        moves = gcode_edit(moves)
    rep["gcode"] = {"moves": len(moves), "file": str(gpath),
                    "codes_ignored": {k: v for k, v in sorted(ignored.items())}}
    if not moves:
        r.add("error", "empty_gcode", "The slicer produced no moves.")
        return finish()
    # ---- reachability: can this machine physically put the nozzle where the G-code says?
    g = np.array([[m.x, m.y, m.z] for m in moves])
    q = np.stack(to_joints(info, g[:, 0], g[:, 1], g[:, 2]), axis=1)
    for k, (j, ax) in enumerate(zip(jl, "XYZ")):
        lo, hi = j.range
        below, above = lo - q[:, k].min(), q[:, k].max() - hi
        if below > 1e-6 or above > 1e-6:
            worst = int(np.argmax(np.maximum(lo - q[:, k], q[:, k] - hi)))
            extra = ""
            if ax == "Z":
                extra = (f" With the bed at the end of its travel the nozzle is still "
                         f"{info['gap0'] - info['sz'] * (hi if info['sz'] > 0 else lo):.2f} mm above it.")
            r.add("error", "unreachable",
                  f"G-code {ax}={g[worst, k]:.2f} (line {moves[worst].line}) needs joint {j.name}="
                  f"{q[worst, k]:.2f}, outside its travel {j.range}.{extra}",
                  axis=ax, joint=j.name, needed=round(float(q[worst, k]), 3), range=list(j.range),
                  hint="Extend the travel, move the bed/nozzle datum, or place the part elsewhere on the bed.")
    if not r.ok:
        return finish()
    # ---- plan
    pts = np.vstack([np.zeros((1, 3)), q])
    feeds = np.array([m.feed for m in moves])
    e = np.array([m.e for m in moves])
    vmax = np.array([j.max_speed or 1e9 for j in jl]) * np.array([speed_scale, speed_scale, 1.0])
    amax = np.array([(j.max_accel or 1e9) for j in jl]) * np.array([accel_scale, accel_scale, 1.0])
    dwell = np.abs(e) / np.maximum(feeds, 1e-6)
    Qc, Vc, seg, frac, seg_t = plan(pts, feeds, vmax, amax, dt, dwell=dwell)
    n_settle = int(0.3 / dt)
    Qc = np.vstack([Qc, np.repeat(Qc[-1:], n_settle, 0)])
    Vc = np.vstack([Vc, np.zeros((n_settle, 3))])
    seg = np.concatenate([seg, np.full(n_settle, len(moves) - 1)])
    frac = np.concatenate([frac, np.ones(n_settle)])
    rep["plan"] = {"print_time_s": round(float(seg_t.sum()), 1), "samples": len(Qc),
                   "peak_speed_mm_s": [round(float(x), 1) for x in np.abs(Vc).max(axis=0)],
                   "accel_limits_mm_s2": amax.tolist()}
    # ---- machine dynamics
    import mujoco

    from ..verifiers.motion import build_mujoco
    from ..verifiers.ratings import _torque_at

    model = build_mujoco(design)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    M = np.zeros((model.nv, model.nv))
    mujoco.mj_fullM(model, data, M)
    dof = [model.joint(j.name).dofadr[0] for j in jl]
    data.qvel[:] = 0
    data.qacc[:] = 0
    mujoco.mj_inverse(model, data)  # force each axis must supply to hold still = gravity load
    comps = {c.name: c for c in design.components}
    mass, bias, tpr, fmax = [], [], [], np.zeros((len(Qc), 3))
    for k, j in enumerate(jl):
        dr = getattr(j, "drive_resolved", None)
        if not dr:
            r.add("error", "twin_setup", f"Joint {j.name} has no resolved drive (motor + transmission).")
            return finish()
        mass.append(M[dof[k], dof[k]] + j.reflected_inertia + (mass_extra or {}).get("xyz"[k], 0.0))
        bias.append(-float(data.qfrc_inverse[dof[k]]))
        tpr.append(dr["travel_per_rev"])
        rpm = np.abs(Vc[:, k]) / dr["travel_per_rev"] * 60.0
        curve = comps[dr["motors"][0]].ratings.get("torque_curve_rpm_frac") or [(0, 0.7), (1e6, 0.7)]
        xs, ys = zip(*curve)
        torque = sum(comps[m].ratings["holding_torque_nmm"] for m in dr["motors"]) * np.interp(rpm, xs, ys)
        fmax[:, k] = 2 * math.pi * torque * dr["efficiency"] / dr["travel_per_rev"] * torque_scale
    off = M[np.ix_(dof, dof)] - np.diag(np.diag(M[np.ix_(dof, dof)]))
    if np.abs(off).max() > 1e-6:
        r.add("warning", "axes_coupled", "Axis inertias are coupled; the twin treats them as independent.")
    fric = [pm.friction_n.get(a, 2.0) for a in "xyz"]
    # series compliance: belt stretch (from the belt's routed length) in series with frame flex (from FEA)
    series, motor_mass = [], []
    for k, (j, ax) in enumerate(zip(jl, "xyz")):
        ks = None
        dr = j.drive_resolved
        if pm.compliant and dr["kind"] == "belt":
            from ..verifiers.belts import route

            pul = (j.drive or {}).get("pulley")
            belt = next((b for b in design.belts if any(n[0] == "pulley" and n[1] == pul for n in b.path)), None)
            if belt is not None:
                L = route(design, belt, forward_kinematics(design, {}))["length"]
                ks = 4.0 * pm.belt_ea_n / L  # two runs in parallel, carriage at mid-travel
        if pm.compliant and ax in pm.struct_stiffness:
            kst = float(pm.struct_stiffness[ax])
            ks = kst if ks is None else 1.0 / (1.0 / ks + 1.0 / kst)
        series.append(ks)
        motor_mass.append(j.reflected_inertia)
    back = [pm.backlash_mm.get(a, 0.0) for a in "xyz"]
    Qa, worst, sinfo = simulate(Qc, Vc, np.array(mass), fmax, np.array(tpr), np.array(bias), np.array(fric), dt,
                                damping_ratio=pm.damping_ratio, motor_mass=np.array(motor_mass),
                                series_stiffness=series, backlash=back,
                                spring_damping_ratio=pm.spring_damping_ratio)
    Qm = sinfo.pop("motor_positions")
    quarter = np.array(sinfo["quarter_cycle_mm"])
    final_err = np.abs(Qm[-1] - Qc[-1])   # where the motor ended up vs where the firmware thinks it is
    lag = np.abs(Qa - Qc)                 # how far the nozzle/bed is from the command at each instant
    mlag = np.abs(Qm - Qc)
    rep["dynamics"] = {"axis_mass_kg": [round(float(x), 3) for x in mass],
                       "gravity_bias_n": [round(float(x), 2) for x in bias],
                       "friction_n_assumed": fric, **sinfo,
                       "worst_lag_mm": [round(float(x), 4) for x in lag.max(axis=0)],
                       "rms_lag_mm": [round(float(x), 4) for x in np.sqrt((lag ** 2).mean(axis=0))],
                       "worst_motor_error_mm": [round(float(x), 4) for x in mlag.max(axis=0)],
                       "final_position_error_mm": [round(float(x), 4) for x in final_err]}
    for k, (j, ax) in enumerate(zip(jl, "XYZ")):
        if final_err[k] > quarter[k]:
            i_slip = int(np.argmax(mlag[:, k] > 2 * quarter[k]))
            gz_at = float(g[min(seg[i_slip], len(g) - 1), 2])
            r.add("error", "lost_steps",
                  f"{ax} axis lost steps: it ends {final_err[k]:.2f} mm from where the firmware thinks it is "
                  f"(a layer shift), first slipping about {i_slip * dt:.1f} s in at Z={gz_at:.2f}.",
                  axis=ax, joint=j.name, shift_mm=round(float(final_err[k]), 3), time_s=round(i_slip * dt, 2),
                  hint="Lower acceleration or speed, cut moving mass, or use a stronger motor / lower gearing.")
        elif mlag[:, k].max() > 0.6 * quarter[k]:
            r.add("warning", "near_step_loss",
                  f"{ax} motor error peaks at {mlag[:, k].max():.3f} mm, {mlag[:, k].max() / quarter[k]:.0%} of the "
                  f"{quarter[k]:.3f} mm at which it falls out of step.", axis=ax)
    if collisions:
        # ---- collisions of the machine itself along the print (bed rising under a sweeping gantry)
        from ..sim import program_collisions

        # a print revisits the same poses thousands of times: check each distinct pose once
        sub_i = np.arange(0, len(Qa), max(1, int(0.02 / dt)))
        key = np.round(Qa[sub_i] / np.array([3.0, 3.0, 1.0])).astype(np.int64)
        _, first = np.unique(key, axis=0, return_index=True)
        first.sort()
        pick = sub_i[first]
        full = np.zeros((len(pick), len(design.joints)))
        for k, j in enumerate(jl):
            full[:, design.joints.index(j)] = Qa[pick, k]
        simd = {"q": full, "names": [j.name for j in design.joints], "t": pick * dt}
        rep["poses_checked_for_collision"] = len(pick)
        hits = program_collisions(design, simd, every_mm=0.0)
        for h in hits:
            r.add("error", "print_collision",
                  f"{h['parts'][0]} hits {h['parts'][1]} {h['time_s']:.0f} s into the print, pose {h['pose']}.", **h)
    else:
        hits = None
    # clearance between the growing part and everything on the toolhead except the nozzle itself
    tool_body = design.tool_point[0]
    noz_z = info["nozzle"][2]
    lows = {c.name: c.shape.bounding_box().min.Z - noz_z for c in design.components if c.body == tool_body}
    hot = min(lows, key=lows.get)
    others = {k: v for k, v in lows.items() if k != hot}
    rep["toolhead"] = {"lowest_part": hot,
                       "next_lowest": min(others, key=others.get) if others else None,
                       "clearance_above_nozzle_plane_mm": round(min(others.values()), 2) if others else None}
    rep["machine_collisions"] = len(hits) if hits is not None else "not checked"
    # ---- deposition and comparison with the intended part
    try:
        res = dep.deposit_and_compare(info, pm, moves, e, seg, frac, Qc, Qa, dt, stl, out, name, r,
                                      at=at, z_datum_error=z_datum_error)
        rep["print"] = res
    except Exception as ex:
        r.add("error", "deposition_failed", f"Deposition/comparison did not run: {type(ex).__name__}: {ex}")
    if render and r.ok or render and "print" in rep:
        try:
            from .render import render_print

            rep["artifacts"] = render_print(design, info, pm, jl, Qa, seg, frac, moves, e, dt, out, name)
        except Exception as ex:
            rep["render_error"] = f"{type(ex).__name__}: {ex}"
    return finish()
