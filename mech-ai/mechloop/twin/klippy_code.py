"""Klipper's own Python code, loaded from the checkout and called directly (no MCU, no reactor).

What is loaded is the unmodified source under third_party/klipper/klippy (or MECHLOOP_KLIPPER):

  extras/shaper_calibrate.py, extras/shaper_defs.py   input-shaper selection from a frequency response
  extras/heaters.py                                   ControlPID, ControlBangBang
  extras/verify_heater.py                             HeaterCheck.check_event (thermal runaway check)
  extras/pid_calibrate.py                             ControlAutoTune (the PID_CALIBRATE relay test)
  extras/bed_mesh.py                                  ZMesh (mesh interpolation), for reading a mesh back

The classes are given small stand-ins for the objects they talk to (heater, config section, printer, reactor);
the stand-ins hold numbers and nothing else, so every decision is made by Klipper's code. If the checkout is not
there, `available()` is False and callers must say so; they never report a Klipper result that was not produced.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

_MODS: dict = {}
_ERR: str | None = None


def klippy_dir() -> Path:
    root = Path(__file__).resolve().parents[2]
    return Path(os.environ.get("MECHLOOP_KLIPPER", root / "third_party" / "klipper")) / "klippy"


def _load(name: str):
    """Import klippy's `extras.<name>` (cached). Klippy's modules import each other by bare name (`import pins`,
    `from . import heaters`), so its directory goes on sys.path for the import only."""
    global _ERR
    if name in _MODS:
        return _MODS[name]
    kd = klippy_dir()
    if not (kd / "extras" / f"{name}.py").exists():
        _ERR = f"Klipper source not found at {kd} (tools/setup_klipper.sh fetches it)"
        raise ImportError(_ERR)
    ex = sys.modules.get("extras")
    if ex is not None and str(kd) not in str(getattr(ex, "__file__", "") or list(getattr(ex, "__path__", [""]))[0]):
        raise ImportError("a different top-level module named 'extras' is already imported; cannot load klippy's")
    sys.path.insert(0, str(kd))
    try:
        _MODS[name] = importlib.import_module(f"extras.{name}")
    finally:
        try:
            sys.path.remove(str(kd))
        except ValueError:
            pass
    return _MODS[name]


def available() -> bool:
    try:
        _load("heaters")
        return True
    except Exception:
        return False


def commit() -> str:
    import subprocess

    try:
        return subprocess.run(["git", "-C", str(klippy_dir().parent), "rev-parse", "--short", "HEAD"], capture_output=True,
                              text=True).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def source() -> str:
    return f"Klipper's own code (klippy/extras, commit {commit()}) called directly"


# ------------------------------------------------------------------ stand-ins
class _Section:
    """A config section: the getfloat/getint/get calls Klipper's classes make, answered from a dict."""

    error = ValueError

    def __init__(self, name: str, values: dict, printer=None):
        self._name, self._v, self._printer = name, values, printer

    def get_name(self):
        return self._name

    def get_printer(self):
        return self._printer

    def _get(self, key, default, conv):
        if key in self._v and self._v[key] is not None:
            return conv(self._v[key])
        if default is _NONE:
            raise self.error(f"option '{key}' in section '{self._name}' must be specified")
        return default

    def getfloat(self, key, default=None, minval=None, maxval=None, above=None, below=None, note_valid=True):
        default = _NONE if default is None and key not in self._v and key.startswith("pid_") else default
        return self._get(key, default, float)

    def getint(self, key, default=None, minval=None, maxval=None, note_valid=True):
        return self._get(key, default, int)

    def get(self, key, default=None, note_valid=True):
        return self._get(key, default, str)


_NONE = object()


class _Reactor:
    NEVER = 9999999999999999.0
    NOW = 0.0


class _Printer:
    """Records a shutdown request instead of stopping a machine."""

    command_error = RuntimeError
    config_error = ValueError

    def __init__(self):
        self.shutdown_msg = None
        self._reactor = _Reactor()

    def register_event_handler(self, *a):
        pass

    def get_reactor(self):
        return self._reactor

    def get_start_args(self):
        return {}

    def invoke_shutdown(self, msg):
        if self.shutdown_msg is None:
            self.shutdown_msg = msg.strip().splitlines()[0]


class _Heater:
    """What ControlPID / ControlBangBang / ControlAutoTune ask of klippy's Heater: limits in, PWM value out."""

    def __init__(self, max_power=1.0, smooth_time=1.0, pwm_delay=0.3):
        self.max_power, self.smooth_time, self.pwm_delay = max_power, smooth_time, pwm_delay
        self.pwm = 0.0
        self.target = 0.0
        self.temp = 0.0          # smoothed temperature, as Heater.get_temp returns

    def get_max_power(self):
        return self.max_power

    def get_smooth_time(self):
        return self.smooth_time

    def get_pwm_delay(self):
        return self.pwm_delay

    def set_pwm(self, read_time, value):
        self.pwm = float(value)

    def alter_target(self, target):
        self.target = float(target)

    def get_temp(self, eventtime):
        return self.temp, self.target


# ------------------------------------------------------------------ heater control
class HeaterControl:
    """Klipper's control law for one heater. kind: 'pid' (ControlPID), 'watermark' (ControlBangBang) or 'autotune'
    (pid_calibrate.ControlAutoTune). update(t, temp, target) -> duty, exactly as Heater.temperature_callback would
    call control.temperature_update."""

    def __init__(self, kind: str, cfg: dict, target: float = 0.0, report_time: float = 0.3):
        hm = _load("heaters")
        self.heater = _Heater(cfg.get("max_power", 1.0), cfg.get("smooth_time", 1.0), report_time)
        self.kind = kind
        if kind == "pid":
            kp, ki, kd = cfg["pid"]
            self.ctl = hm.ControlPID(self.heater, _Section("heater", {"pid_Kp": kp, "pid_Ki": ki, "pid_Kd": kd}))
        elif kind == "watermark":
            self.ctl = hm.ControlBangBang(self.heater, _Section("heater", {"max_delta": cfg.get("max_delta", 2.0)}))
        elif kind == "autotune":
            self.ctl = _load("pid_calibrate").ControlAutoTune(self.heater, target)
            self.heater.target = target
        else:
            raise ValueError(kind)

    def update(self, t: float, temp: float, target: float) -> float:
        import logging

        if self.kind == "autotune":
            target = self.heater.target        # ControlAutoTune moves the target itself (alter_target)
        prev = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            self.ctl.temperature_update(t, temp, target)
        finally:
            logging.disable(prev)
        return self.heater.pwm

    # autotune only
    def tuning(self) -> bool:
        return self.ctl.check_busy(0.0, 0.0, 0.0)

    def peaks(self) -> list:
        return list(self.ctl.peaks)

    def final_pid(self) -> tuple:
        return self.ctl.calc_final_pid()


class HeaterVerify:
    """Klipper's verify_heater.HeaterCheck. check(t, smoothed_temp, target) -> True when it would shut the machine down."""

    def __init__(self, heater_name: str, vh_cfg: dict):
        vm = _load("verify_heater")
        self.printer = _Printer()
        self.chk = vm.HeaterCheck(_Section(f"verify_heater {heater_name}", dict(vh_cfg), self.printer))
        self.chk.heater = self.heater = _Heater()

    def check(self, t: float, temp: float, target: float) -> bool:
        import logging

        self.heater.temp, self.heater.target = temp, target
        prev = logging.root.manager.disable
        logging.disable(logging.CRITICAL)        # klippy logs each decision to the root logger; the result is returned instead
        try:
            self.chk.check_event(t)
        finally:
            logging.disable(prev)
        return self.printer.shutdown_msg is not None


# ------------------------------------------------------------------ input shaper
def shaper_impulses(shaper_type: str, freq: float, damping_ratio: float):
    """(amplitudes, times) of a Klipper input shaper, from shaper_defs."""
    _load("shaper_calibrate")
    sd = sys.modules["extras.shaper_defs"]
    return sd.init_shaper(shaper_type, freq, damping_ratio)


def choose_shaper(freq_bins, psd, damping_ratio=None, scv: float = 5.0, max_smoothing=None) -> dict:
    """Run Klipper's shaper_calibrate.ShaperCalibrate.find_best_shaper on a frequency response (as its
    calibrate_shaper script does on accelerometer data: normalise, then fit every shaper type)."""
    import numpy as np

    sc = _load("shaper_calibrate")
    helper = sc.ShaperCalibrate(printer=None)          # printer None: the fit runs in this process
    f = np.asarray(freq_bins, dtype=float)
    p = np.asarray(psd, dtype=float).copy()
    data = sc.CalibrationData("twin", f, p, p.copy(), np.zeros_like(p), np.zeros_like(p))
    data.set_numpy(np)
    data.normalize_to_frequencies()
    log: list = []
    best, all_shapers = helper.find_best_shaper(data, damping_ratio=damping_ratio, scv=scv, max_smoothing=max_smoothing,
                                                logger=log.append)
    return {"shaper_type": best.name, "shaper_freq": round(float(best.freq), 1),
            "remaining_vibrations_frac": round(float(best.vibrs), 4), "smoothing": round(float(best.smoothing), 4),
            "suggested_max_accel": round(float(best.max_accel) / 100.0) * 100.0,
            "candidates": [{"shaper_type": s.name, "shaper_freq": round(float(s.freq), 1), "vibrations_frac": round(float(s.vibrs), 4),
                            "smoothing": round(float(s.smoothing), 4), "max_accel": round(float(s.max_accel) / 100.0) * 100.0}
                           for s in all_shapers],
            "log": log}


# ------------------------------------------------------------------ bed mesh
def mesh_z(profile: dict, xy) -> "np.ndarray":
    """Height Klipper's bed_mesh.ZMesh gives at each (x, y) for a stored profile:
    {"points": rows of z (y ascending), "min_x", "max_x", "min_y", "max_y", "mesh_x_pps", "mesh_y_pps", "algo", "tension"}."""
    import numpy as np

    bm = _load("bed_mesh")
    pts = [list(map(float, row)) for row in profile["points"]]
    params = {"min_x": profile["min_x"], "max_x": profile["max_x"], "min_y": profile["min_y"], "max_y": profile["max_y"],
              "x_count": len(pts[0]), "y_count": len(pts), "mesh_x_pps": profile.get("mesh_x_pps", 2),
              "mesh_y_pps": profile.get("mesh_y_pps", 2), "algo": profile.get("algo", "lagrange"),
              "tension": profile.get("tension", 0.2)}
    zm = bm.ZMesh(params, "default")
    zm.build_mesh(pts)
    xy = np.atleast_2d(np.asarray(xy, dtype=float))
    return np.array([zm.calc_z(float(x), float(y)) for x, y in xy])


def mesh_grid(profile: dict):
    """(xs, ys, Z[y, x]) of the interpolated mesh Klipper builds from a stored profile (ZMesh.build_mesh); between
    those nodes Klipper's calc_z is bilinear and outside them it holds the edge value."""
    import numpy as np

    bm = _load("bed_mesh")
    pts = [list(map(float, row)) for row in profile["points"]]
    params = {"min_x": profile["min_x"], "max_x": profile["max_x"], "min_y": profile["min_y"], "max_y": profile["max_y"],
              "x_count": len(pts[0]), "y_count": len(pts), "mesh_x_pps": profile.get("mesh_x_pps", 2),
              "mesh_y_pps": profile.get("mesh_y_pps", 2), "algo": profile.get("algo", "lagrange"),
              "tension": profile.get("tension", 0.2)}
    zm = bm.ZMesh(params, "default")
    zm.build_mesh(pts)
    Z = np.array(zm.get_mesh_matrix(), dtype=float)
    return (np.linspace(params["min_x"], params["max_x"], Z.shape[1]), np.linspace(params["min_y"], params["max_y"], Z.shape[0]), Z)


def mesh_z_fast(profile: dict, x, y):
    """Vectorised equivalent of ZMesh.calc_z over the grid Klipper built (checked against calc_z in the tests)."""
    import numpy as np

    xs, ys, Z = mesh_grid(profile)
    x = np.clip(np.asarray(x, dtype=float), xs[0], xs[-1])
    y = np.clip(np.asarray(y, dtype=float), ys[0], ys[-1])
    i = np.clip(np.searchsorted(xs, x, side="right") - 1, 0, len(xs) - 2)
    j = np.clip(np.searchsorted(ys, y, side="right") - 1, 0, len(ys) - 2)
    tx = (x - xs[i]) / (xs[i + 1] - xs[i])
    ty = (y - ys[j]) / (ys[j + 1] - ys[j])
    return ((1 - tx) * (1 - ty) * Z[j, i] + tx * (1 - ty) * Z[j, i + 1] + (1 - tx) * ty * Z[j + 1, i] + tx * ty * Z[j + 1, i + 1])
