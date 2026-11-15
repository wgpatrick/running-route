"""Digital twin of a printer design: slice a part, plan the motion like firmware
does, run it on the machine's stepper dynamics, lay material down where the
simulated nozzle actually went, and compare the result with the intended part.

Modelled: G-code from a real slicer, look-ahead planning with the machine's own
speed/acceleration limits, axis masses from the CAD, motor torque curves, step
loss, belt stretch, frame flex, the carriage turning on its guide blocks, extruder lag
by drive type, a melt-rate cap per hotend class, bead width from extruded volume,
machine collisions along the print.
Not modelled: heat in the part (cooling, warping, bed adhesion), ooze and stringing, vibration of the printed part.
Which numbers are fitted to published data and which are still assumed: fitted_parameters.json (fitted.py).
With firmware="klipper" the motion, input shaping, pressure advance and bed-mesh compensation are whatever real
Klipper puts in its step stream (firmware.py, tuning.py); the built-in planner has none of the three.
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
from . import fitted as _fit


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
    # first-order melt-flow lag: the factory pressure-advance constant of direct-drive machines with a 0.4 mm nozzle.
    # printer_map_for() picks the value for the design's drive type (Bowden: about eight times longer), nozzle and tube length
    extruder_lag_s: float = field(default_factory=lambda: _fit.extruder_lag("direct", 0.4))
    extruder_lag_basis: str = "direct drive, 0.4 mm nozzle (default; no design given)"
    damping_ratio: float = field(default_factory=lambda: float(_fit.value("stepper_damping_ratio")))  # of the stepper's magnetic spring (assumed)
    filament_density: float = 1.24  # g/cm^3 (PLA)
    compliant: bool = True  # belts stretch and the frame flexes; False = perfectly rigid machine
    # belt tensile stiffness EA (N per unit strain) per 6 mm of width, glass-fibre GT2: fitted_parameters.json
    # `belt_ea_n_per_6mm`. 19 kN (15 to 27): between Gates' own figure (16.9 kN, design manual Table 6) and the 21 kN
    # three reference machines imply. It scales linearly with each belt's width (Gates: 4 to 9 mm) and rises with
    # tension; all belts on an axis act in parallel. Until 2026-11-15 this was 22 kN.
    belt_ea_n: float = field(default_factory=lambda: float(_fit.value("belt_ea_n_per_6mm")))
    perimeter_speed: float = 45.0  # mm/s, the design's intended print speeds (design.printer["speeds"])
    infill_speed: float = 60.0
    travel_speed: float = 150.0
    struct_stiffness: dict = field(default_factory=dict)  # nozzle stiffness from FEA, N/mm, e.g. {"x": 3000}
    backlash_mm: dict = field(default_factory=dict)  # lost motion per axis (slack belt, loose pulley)
    # belt/frame damper. None (default): each axis's damper is set so that the mode its load rings in has the damping
    # ratio fitted to resonance spectra (ringing_damping_ratio). A number forces that damper ratio on every axis.
    spring_damping_ratio: float | None = None
    ringing_damping_ratio: dict = field(default_factory=lambda: dict(_fit.value("ringing_damping_ratio")))
    # the carriage turning on its guide blocks between belt clamp and nozzle (machine.toolhead_compliance)
    toolhead_compliance: bool = True
    toolhead_tilt_n_per_um: float = field(default_factory=lambda: float(_fit.value("toolhead_tilt_effective_n_per_um")))
    toolhead_stiffness: dict = field(default_factory=dict)  # override, N/mm at the nozzle, e.g. {"x": 170.0}
    # melt-rate cap of the hotend, mm^3/s (None: no cap). printer_map_for() sets it from the design's hotend class
    max_volumetric_flow: float | None = None
    max_volumetric_flow_basis: dict = field(default_factory=dict)
    raster_px_per_mm: int = 20
    # the bed surface as built, relative to the flat plane the firmware assumes (all assumed inputs, mm):
    # {"tilt_x_mm": rise across the bed's width, "tilt_y_mm": across its depth, "bow_mm": centre above the corners,
    #  "ref_xy": bed-centred point where Z was referenced (homing/probe point), "z_ref_error_mm": error of that reference}
    bed_surface: dict = field(default_factory=dict)


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


def bed_deviation(pm: PrinterMap, info: dict, gx, gy):
    """Height of the real bed surface above the plane the firmware believes in, at bed-centred (gx, gy), given that Z
    was referenced at pm.bed_surface["ref_xy"]. Zero everywhere for a flat bed (the default)."""
    bs = pm.bed_surface or {}
    if not bs:
        return np.zeros_like(np.asarray(gx, dtype=float))
    W, D = info["bed_size"]

    def raw(x, y):
        u, v = np.asarray(x, dtype=float) / W, np.asarray(y, dtype=float) / D
        return (bs.get("tilt_x_mm", 0.0) * u + bs.get("tilt_y_mm", 0.0) * v
                - bs.get("bow_mm", 0.0) * 2.0 * (u * u + v * v))       # bow: centre this much above the corners

    rx, ry = bs.get("ref_xy", (0.0, 0.0))
    return raw(gx, gy) - raw(rx, ry) + bs.get("z_ref_error_mm", 0.0)


def run_print(design: Design, part, out: Path, pm: PrinterMap | None = None, name: str = "part",
              dt: float = 0.001, render: bool = True, slicer_args: dict | None = None,
              accel_scale: float = 1.0, torque_scale: float = 1.0, speed_scale: float = 1.0,
              at: tuple = (0.0, 0.0), z_datum_error: float = 0.0, mass_extra: dict | None = None,
              gcode_edit=None, collisions: bool = True, firmware: str | None = None, trajectory: bool = False,
              firmware_opts: dict | None = None) -> dict:
    """Print `part` (a build123d shape sitting on Z=0, centred on XY) on `design`.
    Returns a report dict and writes artefacts into `out`. accel_scale multiplies the
    joints' acceleration limits and torque_scale the motor torque (e.g. reduced driver current)
    for what-if runs. speed_scale multiplies slicer speeds and XY speed limits. `at` places the part
    on the bed (mm from bed centre). z_datum_error is how far the real nozzle sits above (+) or below (-)
    where the firmware believes it is. mass_extra adds kg to axes, e.g. {"x": 0.3, "y": 0.3}.
    gcode_edit(moves) -> moves lets a test tamper with the program.
    firmware="klipper" has the real Klipper host software plan the motion from the design's generated printer.cfg
    (see firmware.py) in place of the twin's own planner; if Klipper is not installed the print is an error, not a pass.
    firmware_opts (Klipper only): {"input_shaper": True|False|{"x": {...}, "y": {...}}, "pressure_advance": True|False|K,
    "bed_mesh": True|False} choose what the generated printer.cfg turns on (default: input shaper and pressure
    advance on, bed mesh on when the design has a probe and pm.bed_surface is given). See tuning.py.
    trajectory=True saves the simulated nozzle path to <name>_trajectory.npz for replay."""
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
        sa = {"perimeter_speed": pm.perimeter_speed * speed_scale, "infill_speed": pm.infill_speed * speed_scale,
              "travel_speed": min(pm.travel_speed, jl[0].max_speed or 1e9, jl[1].max_speed or 1e9) * speed_scale,
              "center": at,
              "machine": {"accel": jl[0].max_accel * accel_scale, "speed": jl[0].max_speed * speed_scale,
                          "z_speed": jl[2].max_speed, "z_accel": jl[2].max_accel},
              **(slicer_args or {})}
        if pm.max_volumetric_flow:      # the slicer holds every extruding move to the hotend's melt rate, as a filament profile does
            sa["extra"] = list(sa.get("extra") or []) + ["--max-volumetric-speed", f"{pm.max_volumetric_flow:g}",
                                                         "--filament-max-volumetric-speed", f"{pm.max_volumetric_flow:g}"]
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
    rep["flow"] = flow_report(pm, moves, sa)
    if rep["flow"].get("limited"):
        r.add("warning", "flow_limited",
              f"The hotend melts about {pm.max_volumetric_flow:g} mm^3/s; the requested "
              + ", ".join(f"{k} speed {v['requested_mm_s']:g} mm/s needs {v['requested_flow_mm3_s']:g}" for k, v in rep["flow"]["limited"].items())
              + f". Those moves were slowed to the cap (about {rep['flow']['speed_at_cap_mm_s']:g} mm/s at this bead).",
              cap_mm3_s=pm.max_volumetric_flow, limited=rep["flow"]["limited"],
              hint="A higher-flow hotend, a larger nozzle or thinner layers raise the cap; otherwise the speed is not real.")
    if rep["flow"].get("over_cap_moves"):
        r.add("error", "flow_cap_not_respected",
              f"{rep['flow']['over_cap_moves']} extruding moves ask for up to {rep['flow']['peak_flow_in_gcode_mm3_s']:g} mm^3/s, above the "
              f"hotend's {pm.max_volumetric_flow:g} mm^3/s: the G-code was not held to the melt rate.")
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
    if firmware:
        from . import firmware as fw

        try:
            if gcode_edit is not None:
                raise fw.FirmwareError("gcode_edit cannot be combined with firmware in the loop")
            res_fw = fw.commanded(design, info, gpath, pts, dt, out / "firmware", pm=pm, opts=firmware_opts,
                                  accel_scale=accel_scale, speed_scale=speed_scale, mass_extra=mass_extra)
        except (fw.FirmwareNotAvailable, fw.FirmwareError) as ex:
            r.add("error", "firmware_not_run" if isinstance(ex, fw.FirmwareNotAvailable) else "firmware_error", str(ex),
                  hint="tools/setup_klipper.sh installs Klipper for these runs." if isinstance(ex, fw.FirmwareNotAvailable) else "")
            return finish()
        Qc, Vc, seg, frac, seg_t = (res_fw[k] for k in ("Qc", "Vc", "seg", "frac", "seg_t"))
        Qn, e_cmd = res_fw["Qn"], res_fw["E"]
        rep["firmware"] = res_fw["report"]
        for msg, n in res_fw["report"]["klipper_messages"].items():
            r.add("error", "firmware_rejected_move", f"Klipper: {msg} ({n} times)")
        lim = res_fw["report"]["mcu_step_rate_limit_hz"]
        for ax, hz in res_fw["report"]["peak_step_rate_hz"].items():
            if lim and hz > lim:
                r.add("error", "step_rate_over_mcu_limit", f"{ax} peaks at {hz:.0f} steps/s; the board manages about {lim:.0f}.")
        if not r.ok:
            return finish()
    else:
        Qc, Vc, seg, frac, seg_t = plan(pts, feeds, vmax, amax, dt, dwell=dwell)
        Qn, e_cmd = Qc, None
    n_settle = int(0.3 / dt)
    planned_is_commanded = Qn is Qc
    Qc = np.vstack([Qc, np.repeat(Qc[-1:], n_settle, 0)])
    Vc = np.vstack([Vc, np.zeros((n_settle, 3))])
    seg = np.concatenate([seg, np.full(n_settle, len(moves) - 1)])
    frac = np.concatenate([frac, np.ones(n_settle)])
    Qn = Qc if planned_is_commanded else np.vstack([Qn, np.repeat(Qn[-1:], n_settle, 0)])
    if e_cmd is not None:
        e_cmd = np.concatenate([e_cmd, np.full(n_settle, e_cmd[-1])])
    rep["plan"] = {"print_time_s": round(float(seg_t.sum()), 1), "samples": len(Qc),
                   "peak_speed_mm_s": [round(float(x), 1) for x in np.abs(Vc).max(axis=0)],
                   "accel_limits_mm_s2": amax.tolist()}
    if getattr(design, "electrical", None) is not None:
        # heat-up before the first move, from the electrical model's heater simulation (bed and hotend heat together)
        try:
            from ..verifiers.electrical import heatup_for_print

            hu = heatup_for_print(design)
            if hu and hu["heatup_s"] is not None:
                rep["plan"]["heatup_s"] = hu["heatup_s"]
                rep["plan"]["job_time_s"] = round(rep["plan"]["print_time_s"] + hu["heatup_s"], 1)
                rep["plan"]["heatup"] = hu["heaters"]
        except Exception as ex:
            rep["plan"]["heatup_error"] = f"{type(ex).__name__}: {ex}"
    # ---- machine dynamics
    from .machine import drive_force, machine_model

    try:
        mm = machine_model(design, pm, mass_extra)
    except ValueError as ex:
        r.add("error", "twin_setup", str(ex))
        return finish()
    mass, bias, tpr, series, motor_mass, belts_used, fric, back = (mm[k_] for k_ in (
        "mass", "bias", "tpr", "series", "motor_mass", "belts_used", "fric", "back"))
    fmax = drive_force(mm, Vc, torque_scale)
    if mm["coupled"]:
        r.add("warning", "axes_coupled", "Axis inertias are coupled; the twin treats them as independent.")
    Qa, worst, sinfo = simulate(Qc, Vc, np.array(mass), fmax, np.array(tpr), np.array(bias), np.array(fric), dt,
                                damping_ratio=pm.damping_ratio, motor_mass=np.array(motor_mass),
                                series_stiffness=series, backlash=back,
                                spring_damping_ratio=mm["spring_damping"])
    Qm = sinfo.pop("motor_positions")
    if trajectory:
        every = max(1, int(round(0.02 / dt)))
        ext = (np.array(e)[seg] > 0) & (np.linalg.norm(pts[seg + 1] - pts[seg], axis=1) > 1e-9)
        np.savez_compressed(out / f"{name}_trajectory.npz", dt=dt * every, q=Qa[::every].astype(np.float32),
                            qc=Qc[::every].astype(np.float32), extruding=ext[::every], nozzle=info["nozzle"],
                            bed_top=info["bed_top"])
    quarter = np.array(sinfo["quarter_cycle_mm"])
    final_err = np.abs(Qm[-1] - Qc[-1])   # where the motor ended up vs where the firmware thinks it is
    lag = np.abs(Qa - Qc)                 # how far the nozzle/bed is from the command at each instant
    mlag = np.abs(Qm - Qc)
    rep["dynamics"] = {"axis_mass_kg": [round(float(x), 3) for x in mass],
                       "gravity_bias_n": [round(float(x), 2) for x in bias],
                       "friction_n_assumed": fric, "belts_per_axis": belts_used, **sinfo,
                       "toolhead_compliance": mm["toolhead"], "damping": mm["damping"],
                       "worst_lag_mm": [round(float(x), 4) for x in lag.max(axis=0)],
                       "rms_lag_mm": [round(float(x), 4) for x in np.sqrt((lag ** 2).mean(axis=0))],
                       "worst_motor_error_mm": [round(float(x), 4) for x in mlag.max(axis=0)],
                       "final_position_error_mm": [round(float(x), 4) for x in final_err]}
    # vibration that shows on the part: how far the nozzle is sideways from the path the G-code asked for (the
    # planned trajectory before any input shaping), as opposed to merely being late along it. Without firmware
    # shaping the planned and the commanded trajectory are the same thing.
    Vn = Vc if Qn is Qc else np.gradient(Qn, dt, axis=0)
    sp = np.hypot(Vn[:, 0], Vn[:, 1])
    moving = sp > 5.0
    if moving.any():
        ex, ey = (Qa[:, 0] - Qn[:, 0])[moving], (Qa[:, 1] - Qn[:, 1])[moving]
        cross = np.abs(ex * (-Vn[moving, 1] / sp[moving]) + ey * (Vn[moving, 0] / sp[moving]))
        rep["dynamics"]["cross_track_rms_mm"] = round(float(np.sqrt((cross ** 2).mean())), 4)
        rep["dynamics"]["cross_track_worst_mm"] = round(float(cross.max()), 4)
        rep["dynamics"]["cross_track_p99_mm"] = round(float(np.percentile(cross, 99.0)), 4)
        if Qn is not Qc:      # how much of that the firmware's own smoothing of the command accounts for
            cx_, cy_ = (Qc[:, 0] - Qn[:, 0])[moving], (Qc[:, 1] - Qn[:, 1])[moving]
            cc = np.abs(cx_ * (-Vn[moving, 1] / sp[moving]) + cy_ * (Vn[moving, 0] / sp[moving]))
            rep["dynamics"]["command_smoothing_worst_mm"] = round(float(cc.max()), 4)
            rep["dynamics"]["command_smoothing_rms_mm"] = round(float(np.sqrt((cc ** 2).mean())), 4)
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
        res = dep.deposit_and_compare(info, pm, moves, e, seg, frac, Qn, Qa, dt, stl, out, name, r,
                                      at=at, z_datum_error=z_datum_error, e_cmd=e_cmd)
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


def flow_report(pm: PrinterMap, moves, slicer_args: dict) -> dict:
    """Volumetric flow the print asks for against the hotend's melt-rate cap: what the design's speeds would need at
    this bead, which of them the cap limits, and the largest flow actually in the G-code."""
    import numpy as _np

    a_fil = math.pi * pm.filament_diameter ** 2 / 4.0
    width = 1.125 * pm.nozzle                      # PrusaSlicer's default extrusion width for a nozzle
    bead = pm.layer_height * (width - pm.layer_height * (1 - math.pi / 4))      # its rounded-rectangle bead section
    out = {"cap_mm3_s": pm.max_volumetric_flow, "bead_section_mm2": round(bead, 4), "basis": pm.max_volumetric_flow_basis or None}
    req = {k: float(slicer_args[f"{k}_speed"]) for k in ("perimeter", "infill")}
    out["requested_flow_mm3_s"] = {k: round(v * bead, 2) for k, v in req.items()}
    g = _np.array([[m.x, m.y, m.z, m.e, m.feed] for m in moves])
    d = _np.linalg.norm(_np.diff(_np.vstack([g[:1, :3], g[:, :3]]), axis=0), axis=1)
    ext = (g[:, 3] > 0) & (d > 0.05)
    q = _np.where(ext, g[:, 3] * a_fil / _np.maximum(d, 1e-9) * g[:, 4], 0.0)
    out["peak_flow_in_gcode_mm3_s"] = round(float(q.max()), 2) if ext.any() else 0.0
    if pm.max_volumetric_flow:
        cap = float(pm.max_volumetric_flow)
        out["speed_at_cap_mm_s"] = round(cap / bead, 1)
        out["limited"] = {k: {"requested_mm_s": v, "requested_flow_mm3_s": round(v * bead, 2), "speed_at_cap_mm_s": round(cap / bead, 1)}
                          for k, v in req.items() if v * bead > cap * 1.001}
        over = ext & (q > cap * 1.10)              # the slicer rounds feeds; 10 % over means the cap was not applied
        out["over_cap_moves"] = int(over.sum())
    return out


def extruder_of(design: Design) -> dict:
    """Drive type, Bowden tube length and hotend of a printer design, as the twin uses them."""
    spec = design.printer or {}
    drive = "bowden" if spec.get("extruder") == "bowden" else "direct"
    tube = None
    if drive == "bowden":
        tube = spec.get("bowden_length") or next((c.length for c in getattr(design, "cables", []) if "bowden" in c.name.lower()), None)
    tool_body = design.tool_point[0] if design.tool_point else None
    hot = next((c for c in design.components if (c.sku or "").upper().startswith("HOTEND") and (tool_body is None or c.body == tool_body)), None)
    return {"drive": drive, "bowden_length_mm": float(tube) if tube else None, "hotend": hot.name if hot is not None else None,
            "hotend_sku": hot.sku if hot is not None else None,
            "hotend_vendor_max_flow": hot.ratings.get("max_flow_mm3_s") if hot is not None else None}


def printer_map_for(design: Design, metrics: dict | None = None, **overrides) -> PrinterMap:
    """PrinterMap for a design that declares `design.printer`, with the simulations coupled:
    belt stiffness from the belts' width, frame stiffness at the nozzle from the design's own FEA, extruder lag from
    the drive type (direct or Bowden, with the tube's length) and nozzle, melt-rate cap from the hotend's class."""
    spec = design.printer or {}
    kw = {k: spec[k] for k in ("x", "y", "z", "bed", "layer_height", "nozzle", "bed_surface") if k in spec}
    ex = extruder_of(design)
    noz = float(spec.get("nozzle", 0.4))
    kw["extruder_lag_s"] = _fit.extruder_lag(ex["drive"], noz, ex["bowden_length_mm"])
    kw["extruder_lag_basis"] = (f"{ex['drive']} drive, {noz:g} mm nozzle"
                                + (f", Bowden tube {ex['bowden_length_mm']:g} mm" if ex["bowden_length_mm"] else "")
                                + ": factory pressure-advance values (fitted_parameters.json: extruder_lag_s), range "
                                + f"{_fit.extruder_lag(ex['drive'], noz, ex['bowden_length_mm'], 'low'):g} to "
                                + f"{_fit.extruder_lag(ex['drive'], noz, ex['bowden_length_mm'], 'high'):g} s")
    cap = _fit.melt_cap(ex["hotend_sku"], noz, ex["hotend_vendor_max_flow"])
    kw["max_volumetric_flow"] = cap["value"]
    kw["max_volumetric_flow_basis"] = {**cap, "hotend": ex["hotend"], "hotend_sku": ex["hotend_sku"],
                                       "class_assumed": ex["hotend_sku"] is None}
    for k_, f_ in (("perimeter", "perimeter_speed"), ("infill", "infill_speed"), ("travel", "travel_speed")):
        if k_ in (spec.get("speeds") or {}):
            kw[f_] = float(spec["speeds"][k_])
    stiff = {}
    fea = (metrics or {}).get("fea", {})
    for ax, case in (spec.get("stiffness") or {}).items():
        # be conservative: use the lower bound (joints held only around their screws) when there is one
        k = (fea.get(case) or {}).get("stiffness_low_n_per_mm") or (fea.get(case) or {}).get("stiffness_n_per_mm")
        if k:
            stiff[ax] = float(k)
    if stiff:
        kw["struct_stiffness"] = stiff
    kw.update(overrides)
    return PrinterMap(**kw)
