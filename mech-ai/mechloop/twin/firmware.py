"""Firmware in the loop: the real Klipper host software plans the print, and its step commands drive the twin.

Klipper's host program (klippy) has an offline mode: given the printer's configuration, a G-code file and the
micro-controller's command dictionary, it writes the exact command stream it would send to the board.  This
module runs it on the printer.cfg generated from the design, decodes the stream into step times per motor, and
returns the commanded axis positions on the twin's time grid in place of the twin's own look-ahead planner.

Real: Klipper's config validation, G-code handling, limits, look-ahead, trapezoid generation, kinematics, input
shaping, pressure advance, bed-mesh compensation and step compression (commit recorded in the result).  Simulated: everything after the step pulse (motor, belt,
frame, deposition).  Not covered: the micro-controller's own C code and timing, serial latency, driver UART
set-up, and closed-loop heater control (the offline mode has no temperature feedback).

Klipper is not vendored.  `tools/setup_klipper.sh` fetches and builds it into third_party/; or point
MECHLOOP_KLIPPER at a checkout that has out/klipper.dict and MECHLOOP_KLIPPER_PYTHON at a Python that can run it.
"""
from __future__ import annotations

import configparser
import os
import re
import subprocess
from pathlib import Path

import numpy as np

AXES = {"stepper_x": 0, "stepper_y": 1, "stepper_z": 2, "extruder": 3}
# Klipper docs/Benchmarks.md, STM32G0B1, three steppers stepping at once: 243 ticks per step at 64 MHz
MCU_STEP_RATE_LIMIT = {"stm32g0b1xx": 64_000_000 / 243}


class FirmwareNotAvailable(RuntimeError):
    pass


class FirmwareError(RuntimeError):
    pass


def find_klipper():
    root = Path(__file__).resolve().parents[2]
    kdir = Path(os.environ.get("MECHLOOP_KLIPPER", root / "third_party" / "klipper"))
    py = Path(os.environ.get("MECHLOOP_KLIPPER_PYTHON", root / "third_party" / "kenv" / "bin" / "python"))
    if not (kdir / "klippy" / "klippy.py").exists() or not (kdir / "out" / "klipper.dict").exists() or not py.exists():
        raise FirmwareNotAvailable(
            f"Klipper was not found at {kdir} (need klippy/klippy.py and out/klipper.dict) with Python {py}. "
            "Run tools/setup_klipper.sh, or set MECHLOOP_KLIPPER and MECHLOOP_KLIPPER_PYTHON.")
    try:
        commit = subprocess.run(["git", "-C", str(kdir), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        commit = "unknown"
    return kdir, py, commit


def run_klippy(cfg_text: str, gcode_text: str, workdir: Path) -> dict:
    """Run klippy offline. Returns {"dump": path, "messages": [...], "commit": ...}; raises FirmwareError when
    Klipper rejects the configuration or stops."""
    kdir, py, commit = find_klipper()
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "printer.cfg").write_text(cfg_text)
    (workdir / "job.gcode").write_text(gcode_text)
    p = subprocess.run([str(py), str(kdir / "klippy" / "klippy.py"), "printer.cfg", "-i", "job.gcode", "-o", "out.serial",
                        "-d", str(kdir / "out" / "klipper.dict")], cwd=workdir, capture_output=True, text=True, timeout=3600)
    log = p.stdout + p.stderr
    (workdir / "klippy.log").write_text(log)
    msgs: dict[str, int] = {}
    for line in log.splitlines():
        m = re.match(r"(?:WARNING|ERROR):root:(.*)", line)
        if m and "device-tree" not in line and "dmi/id" not in line:
            key = re.sub(r"-?\d+\.\d+", "#", m.group(1))[:160]
            msgs.setdefault(key, 0)
            msgs[key] += 1
    fatal = [ln for ln in log.splitlines() if "Config error" in ln or "Internal error" in ln or "Error in" in ln
             or ln.startswith("configparser.") or "Unhandled exception" in ln]
    if fatal or not (workdir / "out.serial").exists():
        raise FirmwareError("Klipper stopped: " + " | ".join(fatal[:4] or log.splitlines()[-3:]))
    d = subprocess.run([str(py), str(kdir / "klippy" / "parsedump.py"), str(kdir / "out" / "klipper.dict"), "out.serial"],
                       cwd=workdir, capture_output=True, text=True, timeout=3600)
    (workdir / "commands.txt").write_text(d.stdout)
    import json

    mcu = json.loads((kdir / "out" / "klipper.dict").read_text())["config"]
    return {"dump": workdir / "commands.txt", "messages": msgs, "commit": commit, "mcu": mcu.get("MCU"),
            "clock_hz": float(mcu["CLOCK_FREQ"])}


def _cfg(cfg_text: str):
    c = configparser.RawConfigParser(strict=False, inline_comment_prefixes=(";", "#"))
    c.read_string(cfg_text)
    return c


def decode(dump: Path, cfg_text: str, clock_hz: float) -> dict:
    """Step times per motor from the command stream. Returns {axis_index: (t_seconds, signed_step_count_after)} and
    counts of the other commands."""
    c = _cfg(cfg_text)
    pin_axis = {}
    for sec, k in AXES.items():
        if c.has_section(sec):
            pin_axis[c.get(sec, "step_pin").strip().lstrip("!^~")] = k
    oid_axis, state, other = {}, {}, {}
    WRAP_TICKS = 1 << 32
    times: dict[int, list] = {}
    signs: dict[int, list] = {}
    rx = re.compile(r"(\w+)=(-?\w+)")
    xy_start = 0            # latest clock at which an X or Y command began, so far in the stream
    slack = int(0.05 * clock_hz)
    n_wrap = {"Z": 0}
    for line in Path(dump).read_text().splitlines():
        name = line.split(" ", 1)[0]
        if name == "queue_step":
            a = dict(rx.findall(line))
            oid = int(a["oid"])
            if oid not in oid_axis:
                continue
            st = state[oid]
            interval, count, add = int(a["interval"]), int(a["count"]), int(a["add"])
            if oid_axis[oid] in (0, 1):
                xy_start = max(xy_start, st["clock"])
            elif oid_axis[oid] == 2 and count == 1:
                # A step after a pause longer than the 32-bit clock (67 s at 64 MHz) arrives with its interval cut to
                # 32 bits. Klipper writes commands in the order of the clock they are wanted at (a lone far step: its
                # own time; any other: the time of the stepper's previous step), so this step cannot be earlier than
                # the start of an X or Y command already written. Add whole clock periods until it is not.
                while st["clock"] + interval < xy_start - slack:
                    interval += WRAP_TICKS
                    n_wrap["Z"] += 1
            k = np.arange(1, count + 1, dtype=np.int64)
            ticks = st["clock"] + interval * k + add * (k * (k - 1) // 2)
            st["clock"] = int(ticks[-1])
            times[oid].append(ticks)
            signs[oid].append(np.full(count, st["dir"], dtype=np.int8))
        elif name == "set_next_step_dir":
            a = dict(rx.findall(line))
            if int(a["oid"]) in state:
                state[int(a["oid"])]["dir"] = 1 if int(a["dir"]) else -1
        elif name == "reset_step_clock":
            a = dict(rx.findall(line))
            if int(a["oid"]) in state:
                st = state[int(a["oid"])]
                clk = int(a["clock"])   # 32-bit clock: take the first value at or after the last step
                base = st["clock"] - (st["clock"] % (1 << 32)) + clk
                st["clock"] = base if base >= st["clock"] else base + (1 << 32)
        elif name == "config_stepper":
            a = dict(rx.findall(line))
            if a["step_pin"] in pin_axis:
                oid = int(a["oid"])
                oid_axis[oid] = pin_axis[a["step_pin"]]
                state[oid] = {"clock": 0, "dir": 1}
                times[oid], signs[oid] = [], []
        else:
            other[name] = other.get(name, 0) + 1
    out = {}
    for oid, ax in oid_axis.items():
        if times[oid]:
            t = np.concatenate(times[oid]) / clock_hz
            out[ax] = (t, np.cumsum(np.concatenate(signs[oid]).astype(np.int64)))
        else:
            out[ax] = (np.zeros(0), np.zeros(0, dtype=np.int64))
    return {"steps": out, "other_commands": other, "clock_wraps_resolved": n_wrap}


def _mm_per_step(c, sec):
    return c.getfloat(sec, "rotation_distance") / (c.getint(sec, "full_steps_per_rotation", fallback=200)
                                                   * c.getint(sec, "microsteps", fallback=1))


def _march(Q, P, tol=0.03):
    """Which G-code move each commanded sample lies on, and how far along it (the stream follows the same polyline)."""
    from numba import njit

    @njit(cache=True)
    def go(Q, P, L, tol):
        T, N = len(Q), len(P) - 1
        seg = np.zeros(T, np.int64)
        frac = np.zeros(T)
        i = 0
        for k in range(T):
            while i < N - 1:
                if L[i] < 1e-9:
                    i += 1
                    continue
                u = ((Q[k, 0] - P[i, 0]) * (P[i + 1, 0] - P[i, 0]) + (Q[k, 1] - P[i, 1]) * (P[i + 1, 1] - P[i, 1])
                     + (Q[k, 2] - P[i, 2]) * (P[i + 1, 2] - P[i, 2])) / (L[i] * L[i])
                if u >= 1.0 - tol / L[i]:
                    i += 1
                    continue
                break
            if L[i] < 1e-9:
                u = 1.0
            else:
                u = ((Q[k, 0] - P[i, 0]) * (P[i + 1, 0] - P[i, 0]) + (Q[k, 1] - P[i, 1]) * (P[i + 1, 1] - P[i, 1])
                     + (Q[k, 2] - P[i, 2]) * (P[i + 1, 2] - P[i, 2])) / (L[i] * L[i])
            seg[k] = i
            frac[k] = min(1.0, max(0.0, u))
        return seg, frac

    L = np.linalg.norm(np.diff(P, axis=0), axis=1)
    return go(np.ascontiguousarray(Q), np.ascontiguousarray(P), L, tol)


def _strip_tuning(cfg_text: str) -> str:
    """The same configuration with input shaping and pressure advance off (bed mesh kept): the planned motion."""
    out, skip = [], False
    for ln in cfg_text.splitlines():
        t = ln.strip()
        if t.startswith("["):
            skip = t.startswith("[input_shaper")
        if skip or t.startswith("pressure_advance"):
            continue
        out.append(ln)
    return "\n".join(out) + "\n"


def _what_if(cfg_text: str, accel_scale: float, speed_scale: float) -> str:
    """Scale [printer] max_accel / max_velocity for a what-if run (the generated file itself is not changed)."""
    if accel_scale == 1.0 and speed_scale == 1.0:
        return cfg_text
    out, sec = [], ""
    for ln in cfg_text.splitlines():
        t = ln.strip()
        if t.startswith("["):
            sec = t
        if sec == "[printer]" and t.startswith("max_accel:"):
            ln = f"max_accel: {float(t.split(':')[1]) * accel_scale:g}"
        elif sec == "[printer]" and t.startswith("max_velocity:"):
            ln = f"max_velocity: {float(t.split(':')[1]) * speed_scale:g}"
        out.append(ln)
    return "\n".join(out) + "\n"


def _mesh_profile(c) -> dict | None:
    """The stored [bed_mesh default] profile of a configuration, with its fade settings, or None."""
    if not c.has_section("bed_mesh default"):
        return None
    rows = [[float(v) for v in ln.split(",")] for ln in c.get("bed_mesh default", "points").strip().splitlines() if ln.strip()]
    g = lambda k, d=None: c.get("bed_mesh default", k, fallback=d)
    prof = {"points": rows, "min_x": float(g("min_x")), "max_x": float(g("max_x")), "min_y": float(g("min_y")), "max_y": float(g("max_y")),
            "mesh_x_pps": int(g("mesh_x_pps", 2)), "mesh_y_pps": int(g("mesh_y_pps", 2)), "algo": g("algo", "lagrange").strip(),
            "tension": float(g("tension", 0.2))}
    prof["fade_start"] = c.getfloat("bed_mesh", "fade_start", fallback=1.0)
    prof["fade_end"] = c.getfloat("bed_mesh", "fade_end", fallback=0.0)
    if c.getfloat("bed_mesh", "fade_target", fallback=0.0) != 0.0:
        raise FirmwareError("the twin reads bed meshes with fade_target 0 only")
    return prof


def remove_mesh(prof: dict, x, y, z_stepper):
    """Undo Klipper's bed-mesh adjustment: the G-code Z that put the Z stepper at z_stepper over machine point (x, y).
    Klipper adds factor(z) * mesh(x, y), with factor fading linearly from 1 at fade_start to 0 at fade_end."""
    from . import klippy_code as K

    m = K.mesh_z_fast(prof, x, y)
    fs, fe = prof.get("fade_start", 1.0), prof.get("fade_end", 0.0)
    zs = np.asarray(z_stepper, dtype=float)
    if fe <= fs:                      # fade disabled
        return zs - m, m
    low = zs - m                      # below fade_start the whole adjustment applies
    mid = (zs - fe * m / (fe - fs)) / (1.0 - m / (fe - fs))
    zg = np.where(low <= fs, low, np.where(mid <= fe, mid, zs))
    return zg, m


def _run_decode(cfg_text: str, job: str, workdir: Path, c) -> dict:
    run = run_klippy(cfg_text, job, workdir)
    dec = decode(run["dump"], cfg_text, run["clock_hz"])
    steps = dec["steps"]
    if not all(k in steps and len(steps[k][0]) for k in (0, 1, 2)):
        raise FirmwareError("Klipper produced no steps on one of X, Y, Z. Its messages: " + "; ".join(run["messages"])[:400])
    return {"run": run, "dec": dec, "steps": steps}


def commanded(design, info, gcode_path: Path, pts: np.ndarray, dt: float, workdir: Path, cfg_text: str | None = None,
              pm=None, opts: dict | None = None, accel_scale: float = 1.0, speed_scale: float = 1.0,
              mass_extra: dict | None = None) -> dict:
    """Run Klipper on the G-code and return its commanded joint positions on the twin's time grid.

    pts: (N+1, 3) joint positions of the G-code polyline, starting from the home pose (row 0), as run_print builds it.
    The configuration is the design's generated printer.cfg with the tuning `opts` selects (tuning.firmware_tuning).
    Klipper is run once with input shaping and pressure advance off (the planned motion, which is checked against the
    G-code path) and, when either is on, once more as configured; the two runs are lined up on the Z steps, which
    neither feature touches.
    Returns {"Qc" commanded joints, "Qn" planned joints, "Vc", "E" commanded filament, "seg", "frac", "seg_t", "report"}."""
    from . import from_joints

    tuning = None
    if cfg_text is None:
        from ..electrical import klipper_config
        from .tuning import firmware_tuning

        el = getattr(design, "electrical", None)
        if el is None:
            raise FirmwareNotAvailable("The design has no electrical model, so there is no printer.cfg to run.")
        try:
            tuning = firmware_tuning(design, pm, opts, mass_extra)
        except ImportError as ex:
            raise FirmwareNotAvailable(f"Klipper's source is needed to choose the input shaper: {ex}")
        except ValueError as ex:
            raise FirmwareError(f"Firmware tuning could not be generated: {ex}")
        cfg_text = klipper_config(el, design, tuning=tuning)
    cfg_text = _what_if(cfg_text, accel_scale, speed_scale)
    c = _cfg(cfg_text)
    jr = {j.name: j.range for j in design.joints}
    spec = design.printer or {}
    names = [spec.get("x", "x"), spec.get("y", "y"), spec.get("z", "z")]
    # machine coordinates as the configuration defines them: X and Y count from the low end of travel, Z is the
    # nozzle's height above the bed. The slicer's G-code here is centred on the bed, so it is shifted to match.
    lo = [jr[names[0]][0], jr[names[1]][0]]
    xk0 = c.getfloat("stepper_x", "position_min", fallback=0.0)
    yk0 = c.getfloat("stepper_y", "position_min", fallback=0.0)
    g0 = from_joints(info, np.zeros(3))            # where the nozzle is, in G-code coordinates, at the home pose
    q_of_g0 = pts[0]
    off_x = (-info["sx"] * g0[0]) + (q_of_g0[0] - lo[0]) * 1.0 + xk0      # X_klipper = g_x + off_x at sx = +1
    off_y = (-info["sy"] * g0[1]) + (q_of_g0[1] - lo[1]) * 1.0 + yk0
    if info["sx"] < 0 or info["sy"] < 0:
        raise FirmwareError("Firmware in the loop assumes +X and +Y joint travel move the nozzle in +X and +Y.")
    start = (q_of_g0[0] - lo[0] + xk0, q_of_g0[1] - lo[1] + yk0, float(g0[2]))
    body = Path(gcode_path).read_text()
    mesh = _mesh_profile(c)
    shaped = c.has_section("input_shaper")
    pa = c.getfloat("extruder", "pressure_advance", fallback=0.0) if c.has_section("extruder") else 0.0
    # the stored mesh is loaded the way a start G-code does; Z is stated as the Z stepper's position (above the plane
    # the firmware believes in) before the mesh is switched on
    job = (f"SET_KINEMATIC_POSITION X={start[0]:.4f} Y={start[1]:.4f} Z={start[2]:.4f}\n"
           + ("BED_MESH_PROFILE LOAD=default\n" if mesh else "")
           + f"SET_GCODE_OFFSET X={off_x:.4f} Y={off_y:.4f}\n" + body + "\nM400\n")
    # the one addition to the builder's configuration: permission to state the starting position, so that the
    # print can be run without the homing moves (homing against a real switch or probe is not covered)
    add = "" if "[force_move]" in cfg_text else "\n[force_move]\nenable_force_move: True\n"
    workdir = Path(workdir)
    ref = _run_decode(_strip_tuning(cfg_text) + add, job, workdir / "planned" if (shaped or pa > 0) else workdir, c)
    act = _run_decode(cfg_text + add, job, workdir, c) if (shaped or pa > 0) else ref
    run, dec = act["run"], act["dec"]
    rs, as_ = ref["steps"], act["steps"]
    # ---- line the two runs up in time (Klipper's start-up delay depends on the shaper): Z is planned identically
    shift = 0.0
    if act is not ref:
        tz_r, tz_a = rs[2][0], as_[2][0]
        if len(tz_r) != len(tz_a):
            raise FirmwareError(f"The planned and the tuned Klipper runs made different numbers of Z steps ({len(tz_r)} / {len(tz_a)}).")
        # the tuned run's Z moves can overlap the tail of a shaped X/Y move, which defeats decode()'s search for an
        # X/Y pause to put them in: take whole clock periods from the planned run, where that search is sound
        wrap = (1 << 32) / run["clock_hz"]
        d = tz_a - tz_r
        tz_a = tz_a - np.round(d / wrap) * wrap        # the true offset between the runs is milliseconds
        as_[2] = (tz_a, as_[2][1])
        shift = float(np.median(tz_a - tz_r))
        drift = float(np.abs(tz_a - tz_r - shift).max())
        if drift > 2e-4:
            raise FirmwareError(f"The planned and the tuned Klipper runs drift apart by {drift * 1e3:.2f} ms; they cannot be lined up.")
    pad = 0.05
    t0 = min(rs[k][0][0] for k in (0, 1, 2)) - pad
    t_end = max(max(rs[k][0][-1] for k in (0, 1, 2)), max(as_[k][0][-1] for k in (0, 1, 2)) - shift)
    grid = np.arange(0.0, t_end - t0 + 0.05, dt)
    secs = ["stepper_x", "stepper_y", "stepper_z"]
    # where the planned run must end, in machine coordinates; with a mesh the Z stepper ends off the G-code's Z
    end_g = [pts[-1, 0] - lo[0] + xk0, pts[-1, 1] - lo[1] + yk0, float(from_joints(info, pts[-1])[2])]
    Qk_ref, Qk = np.zeros((len(grid), 3)), np.zeros((len(grid), 3))
    peak_rate, sgns = {}, []
    for k in range(3):
        t, n = rs[k]
        mm = _mm_per_step(c, secs[k])
        pos = np.interp(grid, t - t0, n.astype(float), left=0.0, right=float(n[-1]))
        if k == 2 and mesh is not None:
            cand = {s_: float(remove_mesh(mesh, Qk_ref[-1, 0], Qk_ref[-1, 1], start[2] + s_ * n[-1] * mm)[0]) for s_ in (1.0, -1.0)}
            e_plus, e_minus = abs(cand[1.0] - end_g[2]), abs(cand[-1.0] - end_g[2])
        else:
            # the direction pin's sense is not in the stream: take the sign that ends where the G-code ends
            e_plus, e_minus = abs(start[k] + n[-1] * mm - end_g[k]), abs(start[k] - n[-1] * mm - end_g[k])
        sgn = 1.0 if e_plus <= e_minus else -1.0
        if min(e_plus, e_minus) > 0.05:
            raise FirmwareError(f"Decoded {'XYZ'[k]} steps end {min(e_plus, e_minus):.3f} mm from the G-code's last position; "
                                "the stream was not decoded correctly (a pause longer than the 67 s clock wrap?).")
        sgns.append(sgn)
        Qk_ref[:, k] = start[k] + sgn * pos * mm
        ta, na = as_[k]
        Qk[:, k] = start[k] + sgn * np.interp(grid, ta - shift - t0, na.astype(float), left=0.0, right=float(na[-1])) * mm
        if len(ta) > 1:
            peak_rate["XYZ"[k]] = float(1.0 / np.diff(ta).min())
    # ---- filament the firmware commanded (extruder steps, pressure advance included)
    E = None
    e_total = None
    if 3 in as_ and len(as_[3][0]) and c.has_section("extruder"):
        from .gcode import parse

        mm_e = _mm_per_step(c, "extruder")
        e_total = float(sum(m.e for m in parse(gcode_path)[0]))
        te, ne = rs[3]
        e_end = float(ne[-1]) * mm_e
        sgn_e = 1.0 if abs(e_end - e_total) <= abs(-e_end - e_total) else -1.0
        if abs(sgn_e * e_end - e_total) > max(0.5, 0.01 * abs(e_total)):
            raise FirmwareError(f"Decoded extruder steps add up to {sgn_e * e_end:.2f} mm of filament; the G-code asks for {e_total:.2f}.")
        ta, na = as_[3]
        E = sgn_e * np.interp(grid, ta - shift - t0, na.astype(float), left=0.0, right=float(na[-1])) * mm_e

    def to_joints_k(Q):
        out = np.empty_like(Q)
        out[:, 0] = Q[:, 0] - xk0 + lo[0]
        out[:, 1] = Q[:, 1] - yk0 + lo[1]
        out[:, 2] = (info["gap0"] - Q[:, 2]) * info["sz"]
        return out

    Qn, Qc = to_joints_k(Qk_ref), to_joints_k(Qk)
    Vc = np.gradient(Qc, dt, axis=0)
    # ---- the planned motion must lie on the G-code path (with the mesh adjustment taken back out of Z)
    Qchk = Qk_ref.copy()
    mesh_rep = None
    if mesh is not None:
        zg, m_at = remove_mesh(mesh, Qk_ref[:, 0], Qk_ref[:, 1], Qk_ref[:, 2])
        Qchk[:, 2] = zg
        mesh_rep = {"profile_points": [len(mesh["points"][0]), len(mesh["points"])], "range_mm": round(float(np.ptp(mesh["points"])), 4),
                    "z_adjust_applied_mm": [round(float((Qk_ref[:, 2] - zg).min()), 4), round(float((Qk_ref[:, 2] - zg).max()), 4)],
                    "fade_mm": [mesh["fade_start"], mesh["fade_end"]]}
    Qj = to_joints_k(Qchk)
    seg, frac = _march(Qj, pts)
    seg = np.minimum(seg, len(pts) - 2)
    dev = np.abs(Qj - (pts[seg] + (pts[seg + 1] - pts[seg]) * frac[:, None])).max(axis=1)
    # the approach from the home pose is one straight move in the twin's reading of the G-code and separate Z and XY
    # moves in Klipper's; compare from the first move after it
    after = seg >= 3
    if len(pts) > 6 and seg[-1] < len(pts) - 3:
        raise FirmwareError(f"The decoded motion could be followed only as far as G-code move {int(seg[-1])} of {len(pts) - 1}; "
                            "the command stream was not decoded correctly, so no result is reported.")
    off_path = float(dev[after].max()) if after.any() else 0.0
    if off_path > 0.1:
        k = int(np.argmax(np.where(after, dev, 0.0)))
        raise FirmwareError(f"The decoded motion is {off_path:.2f} mm from the G-code path {k * dt:.0f} s into the print; "
                            "the command stream was not decoded correctly, so no result is reported.")
    seg_t = np.bincount(seg, minlength=len(pts) - 1) * dt
    w = max(1, int(round(0.015 / dt)))   # steps are discrete: smooth over 15 ms before differentiating again
    Vs = np.apply_along_axis(lambda v: np.convolve(v, np.ones(w) / w, mode="same"), 0, Vc)
    acc = np.gradient(Vs, dt, axis=0)
    limit = MCU_STEP_RATE_LIMIT.get(run["mcu"])
    t_last = max(as_[k][0][-1] for k in (0, 1, 2)) - shift
    msgs = dict(ref["run"]["messages"])
    for k_, v_ in run["messages"].items():
        msgs[k_] = max(msgs.get(k_, 0), v_)
    report = {
        "firmware": "Klipper", "commit": run["commit"], "mcu": run["mcu"], "print_time_s": round(float(t_last - t0 - pad), 1),
        "steps": {"XYZE"[k]: int(len(as_[k][0])) for k in as_},
        "peak_step_rate_hz": {k: round(v) for k, v in peak_rate.items()},
        "mcu_step_rate_limit_hz": round(limit) if limit else None,
        "peak_speed_mm_s": [round(float(x), 1) for x in np.abs(Vc).max(axis=0)],
        "peak_accel_mm_s2": [round(float(x)) for x in np.percentile(np.abs(acc), 99.9, axis=0)],
        "max_distance_from_gcode_path_mm": round(off_path, 4), "approach_differs_s": round(float((~after).sum() * dt), 1),
        "klipper_messages": msgs, "other_commands": dec["other_commands"],
        "clock_wraps_resolved": dec["clock_wraps_resolved"],
        "gcode_offset_applied_mm": [round(off_x, 3), round(off_y, 3)],
        "what_if": {"accel_scale": accel_scale, "speed_scale": speed_scale,
                    "max_accel": c.getfloat("printer", "max_accel"), "max_velocity": c.getfloat("printer", "max_velocity")},
        "klipper_runs": 1 if act is ref else 2,
        "features": {
            "input_shaper": ({ax: {"shaper_type": c.get("input_shaper", f"shaper_type_{ax}", fallback=None),
                                   "shaper_freq": c.getfloat("input_shaper", f"shaper_freq_{ax}", fallback=0.0),
                                   "damping_ratio": c.getfloat("input_shaper", f"damping_ratio_{ax}", fallback=0.1)} for ax in "xy"}
                             if shaped else None),
            "pressure_advance": pa if pa > 0 else None,
            "pressure_advance_smooth_time": (c.getfloat("extruder", "pressure_advance_smooth_time", fallback=0.04) if pa > 0 else None),
            "bed_mesh": mesh_rep,
            "time_shift_between_runs_s": round(shift, 5) if act is not ref else None,
            "largest_gap_between_commanded_and_planned_mm": [round(float(x), 4) for x in np.abs(Qc - Qn).max(axis=0)],
        },
        "filament_commanded_mm": round(float(E[-1] - E[0]), 2) if E is not None else None, "filament_in_gcode_mm": e_total,
        "tuning": ({k_: ({kk: vv for kk, vv in v_.items() if kk not in ("candidates",)} if isinstance(v_, dict) else v_)
                    for k_, v_ in tuning.items() if k_ in ("input_shaper", "pressure_advance")} if tuning else None),
    }
    if tuning and tuning.get("input_shaper"):     # keep the per-axis choice readable, without the candidate tables
        report["tuning"]["input_shaper"] = {k_: ({kk: vv for kk, vv in v_.items() if kk != "candidates"} if isinstance(v_, dict) else v_)
                                            for k_, v_ in tuning["input_shaper"].items()}
    return {"Qc": Qc, "Qn": Qn, "Vc": Vc, "E": E, "seg": seg, "frac": frac, "seg_t": seg_t, "report": report}
