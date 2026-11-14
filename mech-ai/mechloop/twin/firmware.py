"""Firmware in the loop: the real Klipper host software plans the print, and its step commands drive the twin.

Klipper's host program (klippy) has an offline mode: given the printer's configuration, a G-code file and the
micro-controller's command dictionary, it writes the exact command stream it would send to the board.  This
module runs it on the printer.cfg generated from the design, decodes the stream into step times per motor, and
returns the commanded axis positions on the twin's time grid in place of the twin's own look-ahead planner.

Real: Klipper's config validation, G-code handling, limits, look-ahead, trapezoid generation, kinematics and
step compression (commit recorded in the result).  Simulated: everything after the step pulse (motor, belt,
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
    oid_axis, state, other, far = {}, {}, {}, {}
    FAR, WRAP = 3 << 28, (1 << 32) / clock_hz
    times: dict[int, list] = {}
    signs: dict[int, list] = {}
    rx = re.compile(r"(\w+)=(-?\w+)")
    for line in Path(dump).read_text().splitlines():
        name = line.split(" ", 1)[0]
        if name == "queue_step":
            a = dict(rx.findall(line))
            oid = int(a["oid"])
            if oid not in oid_axis:
                continue
            st = state[oid]
            interval, count, add = int(a["interval"]), int(a["count"]), int(a["add"])
            k = np.arange(1, count + 1, dtype=np.int64)
            ticks = st["clock"] + interval * k + add * (k * (k - 1) // 2)
            if count == 1 and interval >= FAR:      # a step after a long pause: its 32-bit interval may have wrapped
                far[oid].append(sum(len(x) for x in times[oid]))
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
                times[oid], signs[oid], far[oid] = [], [], []
        else:
            other[name] = other.get(name, 0) + 1
    out, wraps = {}, {}
    for oid, ax in oid_axis.items():
        if times[oid]:
            t = np.concatenate(times[oid]) / clock_hz
            out[ax] = (t, np.cumsum(np.concatenate(signs[oid]).astype(np.int64)))
        else:
            out[ax] = (np.zeros(0), np.zeros(0, dtype=np.int64))
    # A pause longer than the 32-bit clock (67 s at 64 MHz) cannot be read from the interval alone. Klipper runs moves
    # one after another, so a Z-only move starts while X and Y are still: push each such step back by whole clock
    # periods until it lands in a gap in the X and Y steps.
    ax_oid = {ax: oid for oid, ax in oid_axis.items()}
    if 2 in out and len(out[2][0]) and 0 in out and 1 in out:
        xy = np.sort(np.concatenate([out[0][0], out[1][0]]))
        t = out[2][0].copy()
        n_wrap = 0
        gaps = np.diff(t)
        # every Z move is a candidate, not only steps flagged as far: a wrapped interval can look short
        for i in [0] + [int(x) + 1 for x in np.where(gaps >= 0.02)[0]]:
            j = i                                   # the whole Z move this step starts
            while j < len(gaps) and gaps[j] < 0.02:
                j += 1
            for k in range(0, 60):
                a0, a1 = t[i] + k * WRAP - 0.0003, t[j] + k * WRAP + 0.0003
                if np.searchsorted(xy, a1) - np.searchsorted(xy, a0) == 0:
                    break
            else:
                raise FirmwareError("Could not place a Z move in a pause of X and Y; the command stream was not decoded.")
            if k:
                t[i:] += k * WRAP
                n_wrap += k
        out[2] = (t, out[2][1])
        wraps["Z"] = n_wrap
    return {"steps": out, "other_commands": other, "clock_wraps_resolved": wraps}


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


def commanded(design, info, gcode_path: Path, pts: np.ndarray, dt: float, workdir: Path, cfg_text: str | None = None) -> dict:
    """Run Klipper on the G-code and return its commanded joint positions on the twin's time grid.

    pts: (N+1, 3) joint positions of the G-code polyline, starting from the home pose (row 0), as run_print builds it.
    Returns {"Qc", "Vc", "seg", "frac", "seg_t", "report"}."""
    from . import from_joints

    if cfg_text is None:
        from ..electrical import klipper_config

        el = getattr(design, "electrical", None)
        if el is None:
            raise FirmwareNotAvailable("The design has no electrical model, so there is no printer.cfg to run.")
        cfg_text = klipper_config(el, design)
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
    job = (f"SET_KINEMATIC_POSITION X={start[0]:.4f} Y={start[1]:.4f} Z={start[2]:.4f}\n"
           f"SET_GCODE_OFFSET X={off_x:.4f} Y={off_y:.4f}\n" + body + "\nM400\n")
    # the one addition to the builder's configuration: permission to state the starting position, so that the
    # print can be run without the homing moves (homing is exercised separately by homing_check)
    run_cfg = cfg_text if "[force_move]" in cfg_text else cfg_text + "\n[force_move]\nenable_force_move: True\n"
    run = run_klippy(run_cfg, job, workdir)
    dec = decode(run["dump"], cfg_text, run["clock_hz"])
    steps = dec["steps"]
    if not all(k in steps and len(steps[k][0]) for k in (0, 1, 2)):
        raise FirmwareError("Klipper produced no steps on one of X, Y, Z. Its messages: " + "; ".join(run["messages"])[:400])
    t_first = min(steps[k][0][0] for k in (0, 1, 2))
    t_end = max(steps[k][0][-1] for k in (0, 1, 2))
    grid = np.arange(0.0, t_end - t_first + 0.05, dt)
    Qk = np.zeros((len(grid), 3))
    secs = ["stepper_x", "stepper_y", "stepper_z"]
    peak_rate = {}
    for k in range(3):
        t, n = steps[k]
        mm = _mm_per_step(c, secs[k])
        # the direction pin's sense is not in the stream: take the sign that ends where the G-code ends
        tgt = [pts[-1, 0] - lo[0] + xk0, pts[-1, 1] - lo[1] + yk0, float(from_joints(info, pts[-1])[2])][k]
        pos = np.interp(grid, t - t_first, n.astype(float), left=0.0, right=float(n[-1]))
        e_plus, e_minus = abs(start[k] + n[-1] * mm - tgt), abs(start[k] - n[-1] * mm - tgt)
        sgn = 1.0 if e_plus <= e_minus else -1.0
        if min(e_plus, e_minus) > 0.05:
            raise FirmwareError(f"Decoded {'XYZ'[k]} steps end {min(e_plus, e_minus):.3f} mm from the G-code's last position; "
                                "the stream was not decoded correctly (a pause longer than the 67 s clock wrap?).")
        Qk[:, k] = start[k] + sgn * pos * mm
        if len(t) > 1:
            peak_rate["XYZ"[k]] = float(1.0 / np.diff(t).min())
    # back to joint values
    Qc = np.empty_like(Qk)
    Qc[:, 0] = Qk[:, 0] - xk0 + lo[0]
    Qc[:, 1] = Qk[:, 1] - yk0 + lo[1]
    Qc[:, 2] = (info["gap0"] - Qk[:, 2]) * info["sz"]
    Vc = np.gradient(Qc, dt, axis=0)
    seg, frac = _march(Qc, pts)
    seg = np.minimum(seg, len(pts) - 2)
    dev = np.abs(Qc - (pts[seg] + (pts[seg + 1] - pts[seg]) * frac[:, None])).max(axis=1)
    # the approach from the home pose is one straight move in the twin's reading of the G-code and separate Z and XY
    # moves in Klipper's; compare from the first move after it
    after = seg >= 3
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
    report = {
        "firmware": "Klipper", "commit": run["commit"], "mcu": run["mcu"], "print_time_s": round(float(t_end - t_first), 1),
        "steps": {"XYZE"[k]: int(len(steps[k][0])) for k in steps},
        "peak_step_rate_hz": {k: round(v) for k, v in peak_rate.items()},
        "mcu_step_rate_limit_hz": round(limit) if limit else None,
        "peak_speed_mm_s": [round(float(x), 1) for x in np.abs(Vc).max(axis=0)],
        "peak_accel_mm_s2": [round(float(x)) for x in np.percentile(np.abs(acc), 99.9, axis=0)],
        "max_distance_from_gcode_path_mm": round(off_path, 4), "approach_differs_s": round(float((~after).sum() * dt), 1),
        "klipper_messages": run["messages"], "other_commands": dec["other_commands"],
        "clock_wraps_resolved": dec["clock_wraps_resolved"],
        "gcode_offset_applied_mm": [round(off_x, 3), round(off_y, 3)],
    }
    return {"Qc": Qc, "Vc": Vc, "seg": seg, "frac": frac, "seg_t": seg_t, "report": report}
