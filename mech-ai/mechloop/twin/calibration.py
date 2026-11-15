"""How far can the twin's axis model be believed? A blind predict-then-compare study.

Three real machines are written down from design data only (`calibration_machines.json`,
frozen before their measured resonances were looked up), the twin's axis model predicts
their resonances and acceleration limits, and the predictions are compared with what
their owners measure (`calibration_measurements.json`). Then, and only then, a recalibrated
parameter set with uncertainty ranges is proposed (PROPOSED below; nothing in the twin's
defaults is changed by this module).

The axis model is the twin's own: load mass on the motors' magnetic spring in series with
the belts (4 EA / L per belt) and, when given, the frame. It is the formula in
`stepper.simulate` (`load_resonance_hz`) and `reference.resonance`.

    python -m mechloop.twin.calibration predict        # blind predictions for the frozen machines
    python -m mechloop.twin.calibration compare        # predictions against the measurements
    python -m mechloop.twin.calibration compare <frozen predictions.json>   # the blind ones themselves
    python -m mechloop.twin.calibration posthoc        # the same machines with the toolhead term (NOT blind)
    python -m mechloop.twin.calibration design <design.py> <print_report.json>   # a design's scores as ranges
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
MACHINES_FILE = HERE / "calibration_machines.json"
MEASUREMENTS_FILE = HERE / "calibration_measurements.json"

# The twin's defaults at the time of the blind prediction (PrinterMap.belt_ea_n = 22 kN per 6 mm).
BLIND = {"belt_ea_n_per_mm_width": 22000.0 / 6.0, "frame_n_per_mm": None, "belt_factor": 4.0}


def machines() -> dict:
    return json.loads(MACHINES_FILE.read_text())["machines"]


def frozen_hash() -> str:
    return hashlib.sha256(MACHINES_FILE.read_bytes()).hexdigest()


# ------------------------------------------------------------------ the axis model
def motor_force(m: dict, current_rms: float, speed_mm_s, volts: float, tpr: float):
    """Force of one motor on the belt (N). Same law as reference.motor_force."""
    i_cmd = current_rms * math.sqrt(2)
    w_e = 2 * math.pi * np.asarray(speed_mm_s, dtype=float) / tpr * m["poles"]
    i = np.minimum(i_cmd, volts / np.sqrt(m["R"] ** 2 + (w_e * m["L_h"]) ** 2))
    return 2 * math.pi * (m["hold_nm"] * i / (m["i_rated"] * math.sqrt(2))) / (tpr * 1e-3)


def stiffness(mach: dict, axis: str, mass=None, length=None, current=None, ea_per_mm=None, frame=None,
              belt_factor=4.0) -> dict:
    """Springs between the commanded position and the load, N/mm."""
    ax, m, tpr = mach["axes"][axis], mach["motor"], mach["travel_per_rev_mm"]
    current = mach["current_rms"][1] if current is None else current
    length = ax["belt_length_mm"][1] if length is None else length
    ea_per_mm = BLIND["belt_ea_n_per_mm_width"] if ea_per_mm is None else ea_per_mm
    f1 = float(motor_force(m, current, 0.0, mach["volts"], tpr))
    k_step = ax["motors"] * f1 * (2 * math.pi * m["poles"] / tpr)
    k_belt = ax["belts"] * belt_factor * ea_per_mm * ax["belt_width_mm"] / length
    inv = 1.0 / k_step + 1.0 / k_belt + (1.0 / frame if frame else 0.0)
    return {"motor": k_step, "belt": k_belt, "frame": frame, "total": 1.0 / inv}


def resonance(mach: dict, axis: str, mass=None, **kw) -> float:
    mass = mach["axes"][axis]["mass_kg"][1] if mass is None else mass
    return math.sqrt(stiffness(mach, axis, **kw)["total"] * 1e3 / mass) / (2 * math.pi)


def skips(mach: dict, axis: str, speed: float, accel: float, travel: float = 100.0, dt: float = 0.0005, current=None,
          ea_per_mm=None, frame=None, mass=None) -> bool:
    """There-and-back moves on the twin's stepper model; True if the motor ends on the wrong pole."""
    from .planner import plan
    from .stepper import simulate

    ax, m, tpr = mach["axes"][axis], mach["motor"], mach["travel_per_rev_mm"]
    current = mach["current_rms"][1] if current is None else current
    mass = ax["mass_kg"][1] if mass is None else mass
    pts = np.array([[0.0], [travel], [0.0], [travel], [0.0]])
    Qc, Vc, *_ = plan(pts, np.full(4, speed), np.array([speed]), np.array([accel]), dt)
    hold = int(0.3 / dt)
    Qc = np.vstack([Qc, np.repeat(Qc[-1:], hold, 0)])
    Vc = np.vstack([Vc, np.zeros((hold, 1))])
    f = ax["motors"] * motor_force(m, current, np.abs(Vc[:, 0]), mach["volts"], tpr)[:, None]
    k = stiffness(mach, axis, current=current, ea_per_mm=ea_per_mm, frame=frame)
    ks = k["belt"] if not frame else 1.0 / (1.0 / k["belt"] + 1.0 / frame)
    refl = ax["motors"] * m["rotor_gcm2"] * 1e-7 * (2 * math.pi / (tpr * 1e-3)) ** 2
    _, _, info = simulate(Qc, Vc, np.array([mass + refl]), f, np.array([tpr]), np.array([0.0]), np.array([3.0]), dt,
                          motor_mass=np.array([refl]), series_stiffness=[ks], pole_pairs=m["poles"])
    return bool(abs(info["motor_positions"][-1, 0] - Qc[-1, 0]) > tpr / (4 * m["poles"]))


def force_limit_accel(mach: dict, axis: str, speed: float = 0.0, current=None, mass=None) -> float:
    """Motor force over everything it has to accelerate (load and rotors), mm/s^2: the rigid-body
    ceiling on acceleration at a given speed. No dynamics; the simulated step-loss limit sits below it."""
    ax, m, tpr = mach["axes"][axis], mach["motor"], mach["travel_per_rev_mm"]
    current = mach["current_rms"][1] if current is None else current
    mass = ax["mass_kg"][1] if mass is None else mass
    refl = ax["motors"] * m["rotor_gcm2"] * 1e-7 * (2 * math.pi / (tpr * 1e-3)) ** 2
    f = ax["motors"] * float(motor_force(m, current, speed, mach["volts"], tpr))
    return round(f / (mass + refl) * 1e3, -2)


def step_loss_accel(mach: dict, axis: str, speed: float | None = None, **kw) -> float:
    """Highest acceleration (mm/s^2) the axis takes without losing steps: the limit the
    scorecard's `max_clean_accel_mm_s2` runs into first on every design scored so far."""
    speed = mach["stock"]["speed"] if speed is None else speed
    lo, hi = 500.0, 4.0e5   # above 400,000 the ramp is shorter than a time step: reported as "none found"
    if skips(mach, axis, speed, lo, **kw):
        return 0.0
    if not skips(mach, axis, speed, hi, **kw):
        return hi
    for _ in range(12):
        a = math.sqrt(lo * hi)
        if skips(mach, axis, speed, a, **kw):
            hi = a
        else:
            lo = a
    return round(lo, -2)


# ------------------------------------------------------------------ what a tuner would recommend at that resonance
def _shaper(kind: str, f: float, zeta: float = 0.1):
    """Input-shaper pulses (amplitudes, times) as published in the Klipper documentation
    (ZV, MZV, EI); written from the formulas, no Klipper code is imported."""
    df = math.sqrt(1 - zeta ** 2)
    td = 1.0 / (f * df)
    if kind == "zv":
        K = math.exp(-zeta * math.pi / df)
        return [1.0, K], [0.0, 0.5 * td]
    if kind == "mzv":
        K = math.exp(-0.75 * zeta * math.pi / df)
        a1 = 1 - 1 / math.sqrt(2)
        return [a1, (math.sqrt(2) - 1) * K, a1 * K * K], [0.0, 0.375 * td, 0.75 * td]
    if kind == "ei":
        K = math.exp(-zeta * math.pi / df)
        v = 0.05
        a1 = 0.25 * (1 + v)
        return [a1, 0.5 * (1 - v) * K, a1 * K * K], [0.0, 0.5 * td, td]
    raise ValueError(kind)


def _smoothing(A, T, accel: float, scv: float = 5.0) -> float:
    inv = 1.0 / sum(A)
    ts = sum(a * t for a, t in zip(A, T)) * inv
    o90 = o180 = 0.0
    for a, t in zip(A, T):
        if t >= ts:
            o90 += a * (scv + 0.5 * accel * (t - ts)) * (t - ts)
            o180 += a * 0.5 * accel * (t - ts) ** 2
    return max(o90 * inv * math.sqrt(2), o180 * inv)


def shaper_accel(f_hz: float, kind: str = "mzv", target: float = 0.12) -> float:
    """Acceleration at which an input shaper tuned to f_hz rounds corners by `target` mm: the
    'suggested max_accel' rule a resonance tuner applies. It scales as f^2 (about 2.9 f^2 for MZV)."""
    A, T = _shaper(kind, f_hz)
    lo, hi = 1.0, 1.0e6
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if _smoothing(A, T, mid) <= target else (lo, mid)
    return round(lo, -2)


# ------------------------------------------------------------------ predictions
def _samples(mach: dict, axis: str, n: int, rng) -> dict:
    ax = mach["axes"][axis]

    def tri(lo, mid, hi):
        return rng.triangular(lo, mid, hi, n)

    return {"mass": tri(*ax["mass_kg"]), "length": tri(*ax["belt_length_mm"]), "current": tri(*mach["current_rms"])}


def predict(params: dict | None = None, n: int = 400, seed: int = 0, step_loss: bool = True) -> dict:
    """Twin predictions for every frozen machine. `params`: belt_ea_n_per_mm_width, frame_n_per_mm
    ({axis: N/mm} or None), belt_factor. Bands are 5-95 % over the input ranges in the frozen file."""
    p = {**BLIND, **(params or {})}
    rng = np.random.default_rng(seed)
    out = {}
    for key, mach in machines().items():
        row = {"label": mach["label"], "axes": {}}
        for axis in mach["axes"]:
            frame = (p["frame_n_per_mm"] or {}).get(axis) if isinstance(p["frame_n_per_mm"], dict) else p["frame_n_per_mm"]
            kw = {"ea_per_mm": p["belt_ea_n_per_mm_width"], "frame": frame}
            S = _samples(mach, axis, n, rng)
            f = np.array([resonance(mach, axis, mass=S["mass"][i], length=S["length"][i], current=S["current"][i],
                                    belt_factor=p["belt_factor"], **kw) for i in range(n)])
            f0 = resonance(mach, axis, belt_factor=p["belt_factor"], **kw)
            k = stiffness(mach, axis, belt_factor=p["belt_factor"], **kw)
            a = {"resonance_hz": round(f0, 1),
                 "resonance_hz_5_95": [round(float(np.percentile(f, 5)), 1), round(float(np.percentile(f, 95)), 1)],
                 "stiffness_n_per_mm": {q: (round(v, 1) if v else None) for q, v in k.items()},
                 "shaper_accel_mm_s2": {s: shaper_accel(f0, s) for s in ("zv", "mzv", "ei")},
                 "shaper_accel_mzv_5_95": [shaper_accel(float(np.percentile(f, 5))), shaper_accel(float(np.percentile(f, 95)))]}
            if step_loss:
                a["step_loss_accel_mm_s2"] = step_loss_accel(mach, axis, **kw)
                a["step_loss_at_speed_mm_s"] = mach["stock"]["speed"]
            a["force_limit_accel_mm_s2"] = {"standstill": force_limit_accel(mach, axis),
                                            "at_stock_speed": force_limit_accel(mach, axis, mach["stock"]["speed"])}
            row["axes"][axis] = a
        out[key] = row
    return {"params": p, "frozen_machines_sha256": frozen_hash(), "machines": out}


def sensitivity(key: str, axis: str) -> dict:
    """d ln(f) / d ln(parameter) at the nominal point: how many percent the predicted resonance
    moves for one percent of each input."""
    mach = machines()[key]
    ax = mach["axes"][axis]
    f0 = resonance(mach, axis)
    h = 1.01
    return {"belt stiffness (EA per mm width)": round(math.log(resonance(mach, axis, ea_per_mm=BLIND["belt_ea_n_per_mm_width"] * h) / f0) / math.log(h), 2),
            "belt length": round(math.log(resonance(mach, axis, length=ax["belt_length_mm"][1] * h) / f0) / math.log(h), 2),
            "moving mass": round(math.log(resonance(mach, axis, mass=ax["mass_kg"][1] * h) / f0) / math.log(h), 2),
            "motor current (magnetic spring)": round(math.log(resonance(mach, axis, current=mach["current_rms"][1] * h) / f0) / math.log(h), 2)}


# ------------------------------------------------------------------ comparison with what owners measure
def measurements() -> dict:
    return json.loads(MEASUREMENTS_FILE.read_text())["machines"]


def modal_damping(mach: dict, axis: str, damping_ratio: float = 0.25, spring_damping_ratio: float = 0.05, **kw) -> float:
    """Damping ratio of the mode the load rings in, from the twin's two dampers (the stepper's and the
    belt's) as `stepper.simulate` sets them: eigenvalues of the motor-spring-load pair."""
    ax, m, tpr = mach["axes"][axis], mach["motor"], mach["travel_per_rev_mm"]
    k = stiffness(mach, axis, **kw)
    ks = k["belt"] if not k["frame"] else 1.0 / (1.0 / k["belt"] + 1.0 / k["frame"])
    k1, k2 = k["motor"] * 1e3, ks * 1e3
    m1 = ax["motors"] * m["rotor_gcm2"] * 1e-7 * (2 * math.pi / (tpr * 1e-3)) ** 2
    m2 = ax["mass_kg"][1]
    c1 = 2 * damping_ratio * math.sqrt(k1 * m1)
    c2 = 2 * spring_damping_ratio * math.sqrt(k2 * m1 * m2 / (m1 + m2))
    A = np.array([[0, 0, 1, 0], [0, 0, 0, 1],
                  [-(k1 + k2) / m1, k2 / m1, -(c1 + c2) / m1, c2 / m1],
                  [k2 / m2, -k2 / m2, c2 / m2, -c2 / m2]])
    ev = [e for e in np.linalg.eigvals(A) if e.imag > 1e-9]
    low = min(ev, key=abs) if ev else None
    return round(float(-low.real / abs(low)), 3) if low is not None else 1.0


def implied(mach: dict, axis: str, f_measured: float) -> dict:
    """What one parameter would have to be for the model to hit the measured frequency, the others
    left at their frozen values. None = no physical value does it."""
    ax = mach["axes"][axis]
    k = stiffness(mach, axis)
    k_meas = ax["mass_kg"][1] * (2 * math.pi * f_measured) ** 2 * 1e-3     # N/mm
    inv_b = 1.0 / k_meas - 1.0 / k["motor"]
    ea6 = (1.0 / inv_b) * ax["belt_length_mm"][1] / (ax["belts"] * 4.0) / ax["belt_width_mm"] * 6.0 if inv_b > 0 else None
    inv_x = 1.0 / k_meas - 1.0 / k["total"]
    return {"stiffness_measured_n_per_mm": round(k_meas, 1), "stiffness_model_n_per_mm": round(k["total"], 1),
            "belt_ea_n_per_6mm": round(ea6, -2) if ea6 else None,
            "extra_series_stiffness_n_per_mm": round(1.0 / inv_x, 1) if inv_x > 0 else None,
            "mass_kg": round(k["total"] * 1e3 / (2 * math.pi * f_measured) ** 2, 3)}


# which axis carries only the toolhead on its guide (the nozzle hangs below the carriage) and which
# carries a whole gantry or a bed
TOOLHEAD_AXES = {("voron0", "x"), ("trident250", "x"), ("ender3", "x")}


def compare(params: dict | None = None, pred: dict | None = None, **predict_kw) -> dict:
    """Predicted against measured, per machine and axis, with errors. `pred` defaults to a fresh
    `predict(params)`; pass the frozen file's content to compare the blind predictions themselves."""
    pred = pred or predict(params, **predict_kw)
    meas, mm = measurements(), machines()
    rows, acc = [], []
    for key, m in pred["machines"].items():
        ms = meas.get(key)
        if not ms:
            continue
        f_meas = {}
        for axis, a in m["axes"].items():
            q = ms[f"{axis}_hz"]
            f_meas[axis] = q["median"]
            err = a["resonance_hz"] / q["median"] - 1.0
            lo, hi = a["resonance_hz_5_95"]
            rows.append({"machine": key, "axis": axis, "kind": "toolhead" if (key, axis) in TOOLHEAD_AXES else "gantry or bed",
                         "predicted_hz": a["resonance_hz"], "predicted_5_95": [lo, hi],
                         "measured_median_hz": q["median"], "measured_iqr_hz": [q["p25"], q["p75"]],
                         "measured_p10_p90_hz": [q["p10"], q["p90"]], "configs": q["n"],
                         "measured_autosaved_median_hz": (ms.get(f"{axis}_hz_autosaved") or {}).get("median"),
                         "error_pct": round(100 * err, 1),
                         "inside_measured_iqr": bool(q["p25"] <= a["resonance_hz"] <= q["p75"]),
                         "bands_overlap": bool(not (hi < q["p10"] or lo > q["p90"])),
                         "implied": implied(mm[key], axis, q["median"]),
                         "twin_modal_damping_ratio": modal_damping(mm[key], axis),
                         "measured_damping_ratio": ms.get(f"damping_ratio_{axis}")})
        used = ms["max_accel_mm_s2"]
        worst = min(m["axes"], key=lambda ax: m["axes"][ax]["resonance_hz"])
        rule_pred = min(a["shaper_accel_mm_s2"]["mzv"] for a in m["axes"].values())
        rule_meas = shaper_accel(min(f_meas.values()))
        step = min(a.get("step_loss_accel_mm_s2", float("inf")) for a in m["axes"].values())
        step_ratio = round(step / used["median"], 1) if math.isfinite(step) else None
        acc.append({"machine": key, "stock_config_accel_mm_s2": mm[key]["stock"]["accel"],
                    "owners_max_accel_median_mm_s2": used["median"], "owners_max_accel_iqr_mm_s2": [used["p25"], used["p75"]],
                    "predicted_shaper_rule_mm_s2": rule_pred, "limiting_axis": worst,
                    "shaper_rule_at_measured_resonance_mm_s2": rule_meas,
                    "predicted_step_loss_mm_s2": step if math.isfinite(step) else None,
                    "shaper_rule_over_owners": round(rule_pred / used["median"], 2),
                    "step_loss_over_owners": step_ratio,
                    "owners_over_rule_at_measured": round(used["median"] / rule_meas, 2)})
    e = np.array([r["error_pct"] for r in rows])
    kinds = {k: np.array([r["error_pct"] for r in rows if r["kind"] == k]) for k in ("toolhead", "gantry or bed")}
    return {"params": pred["params"], "rows": rows, "acceleration": acc,
            "summary": {"axes": len(rows), "mean_abs_error_pct": round(float(np.abs(e).mean()), 1),
                        "mean_signed_error_pct": round(float(e.mean()), 1), "worst_error_pct": round(float(e[np.abs(e).argmax()]), 1),
                        **{f"{k}: mean signed / mean abs error pct": [round(float(v.mean()), 1), round(float(np.abs(v).mean()), 1)]
                           for k, v in kinds.items() if len(v)}}}


# ------------------------------------------------------------------ second comparison, with the toolhead term (NOT blind)
POSTHOC_FILE = HERE / "calibration_posthoc.json"


def posthoc() -> dict:
    return json.loads(POSTHOC_FILE.read_text())["machines"]


def toolhead_term(key: str, k_block_n_per_um: float | None = None, wheels_n_per_mm: float | None = None) -> float | None:
    """Belt-clamp-to-nozzle stiffness (N/mm) of a reference machine's toolhead axis, by the rule the twin applies to a
    design (machine.toolhead_compliance): one guide block turning over its ball track, K_rot = k L^2 / 12, seen at the
    nozzle's distance from the rail. Wheels: the flat fitted figure."""
    from . import fitted

    g = posthoc()[key]
    if g["guide"] == "v_wheels":
        return float(fitted.value("toolhead_v_wheels_n_per_mm") if wheels_n_per_mm is None else wheels_n_per_mm)
    k = (fitted.value("toolhead_tilt_effective_n_per_um") if k_block_n_per_um is None else k_block_n_per_um) * 1e6
    arm = math.hypot(g["nozzle_below_rail_mm"], g["nozzle_horizontal_mm"]) * 1e-3
    k_rot = g["blocks"] * k * (g["ball_track_mm"] * 1e-3) ** 2 / 12.0
    return k_rot / arm ** 2 * 1e-3


def implied_block_stiffness(key: str, f_measured: float) -> float | None:
    """Effective block stiffness (N/um) that makes the toolhead axis of a rail machine ring at f_measured."""
    g, mach = posthoc()[key], machines()[key]
    if g["guide"] != "linear_rail":
        return None
    kx = implied(mach, g["toolhead_axis"], f_measured)["extra_series_stiffness_n_per_mm"]
    if kx is None:
        return None
    arm = math.hypot(g["nozzle_below_rail_mm"], g["nozzle_horizontal_mm"]) * 1e-3
    return kx * 1e3 * arm ** 2 * 12.0 / (g["blocks"] * (g["ball_track_mm"] * 1e-3) ** 2) * 1e-6


def compare_posthoc() -> dict:
    """The frozen three-machine comparison again, with the toolhead term in series on the toolhead axes. The frozen
    inputs are not touched; the term's geometry comes from calibration_posthoc.json. NOT blind: the term's parameter
    was fitted to the two rail machines here (the wheeled machine has a parameter of its own, so its row is a fit by
    construction). `leave_one_out` predicts each rail machine with the stiffness implied by the other one alone."""
    meas, mm_ = measurements(), machines()
    rows = []
    for key, mach in mm_.items():
        g = posthoc()[key]
        for axis in mach["axes"]:
            f_meas = meas[key][f"{axis}_hz"]["median"]
            before = resonance(mach, axis)
            is_tool = axis == g["toolhead_axis"]
            after = resonance(mach, axis, frame=toolhead_term(key)) if is_tool else before
            row = {"machine": key, "axis": axis, "kind": "toolhead" if is_tool else "gantry or bed", "measured_median_hz": f_meas,
                   "blind_hz": round(before, 1), "blind_error_pct": round(100 * (before / f_meas - 1), 1),
                   "with_term_hz": round(after, 1), "with_term_error_pct": round(100 * (after / f_meas - 1), 1),
                   "term_n_per_mm": round(toolhead_term(key), 1) if is_tool else None, "guide": g["guide"] if is_tool else None}
            if is_tool and g["guide"] == "linear_rail":
                other = next(k for k, v in posthoc().items() if v["guide"] == "linear_rail" and k != key)
                k_other = implied_block_stiffness(other, meas[other][f"{posthoc()[other]['toolhead_axis']}_hz"]["median"])
                loo = resonance(mach, axis, frame=toolhead_term(key, k_block_n_per_um=k_other))
                row.update({"implied_block_n_per_um": round(implied_block_stiffness(key, f_meas), 2),
                            "leave_one_out": {"fitted_on": other, "block_n_per_um": round(k_other, 2), "hz": round(loo, 1),
                                              "error_pct": round(100 * (loo / f_meas - 1), 1)}})
            elif is_tool:
                row["leave_one_out"] = None        # one wheeled machine: nothing to hold out
            rows.append(row)
    e0 = np.array([r["blind_error_pct"] for r in rows])
    e1 = np.array([r["with_term_error_pct"] for r in rows])
    tool = np.array([r["kind"] == "toolhead" for r in rows])
    loo = np.array([r["leave_one_out"]["error_pct"] for r in rows if r.get("leave_one_out")])
    return {"blind": False, "note": "second comparison, made after the measurements were seen; the toolhead term's parameter was fitted to "
                                    "these machines. Frozen inputs unchanged (sha256 %s)" % frozen_hash()[:16],
            "rows": rows,
            "summary": {"all axes: mean abs error pct, blind / with term": [round(float(np.abs(e0).mean()), 1), round(float(np.abs(e1).mean()), 1)],
                        "toolhead axes: mean signed error pct, blind / with term": [round(float(e0[tool].mean()), 1), round(float(e1[tool].mean()), 1)],
                        "toolhead axes: worst error pct, blind / with term": [round(float(e0[tool][np.abs(e0[tool]).argmax()]), 1),
                                                                             round(float(e1[tool][np.abs(e1[tool]).argmax()]), 1)],
                        "rail toolhead axes, leave one machine out: errors pct": [float(x) for x in loo],
                        "gantry and bed axes": "unchanged (no term): mean abs %.1f pct" % float(np.abs(e0[~tool]).mean())}}


# ------------------------------------------------------------------ proposal (made after the comparison; applied 2026-11-15, see fitted.py)
def _proposed() -> dict:
    from . import fitted

    return {
        # Belt EA of glass-cord GT2, N per unit strain for 6 mm of width, as [low, nominal, high]. From the three gantry /
        # bed axes (their implied EA: 15, 21, 27 kN). The twin's default (22 kN) is inside it. Width scaling to 9 and
        # 12 mm is not tested by any of the three machines.
        "belt_ea_n_per_6mm": [15000.0, 21000.0, 27000.0],
        # The flat figures of the first study (kept for reference): compliance between belt and nozzle on an axis that
        # carries only the toolhead on one guide block, N/mm in series. The twin now derives the rail figure from the
        # design's geometry with one fitted block stiffness (toolhead_tilt_effective_n_per_um below).
        "toolhead_mount_n_per_mm": {"linear_rail_single_block": [120.0, 170.0, 230.0], "v_wheels": [30.0, 40.0, 60.0]},
        "toolhead_tilt_effective_n_per_um": fitted.triple("toolhead_tilt_effective_n_per_um"),
        # Damping ratio of the ringing mode. First study: what owners enter (n = 39). Now fitted to resonance spectra.
        "ringing_damping_ratio": [0.03, 0.05, 0.09],
        "ringing_damping_ratio_fitted": {k: [fitted.entry("ringing_damping_ratio")["low"][k], v, fitted.entry("ringing_damping_ratio")["high"][k]]
                                         for k, v in fitted.value("ringing_damping_ratio").items()},
        # Acceleration owners actually run with input shaping, as a fraction of the shaper smoothing rule (MZV)
        # evaluated at the lower measured resonance: 0.44 (Ender 3), 0.51 (Voron 0), 0.62 (Trident 250).
        "used_accel_over_shaper_rule": fitted.triple("used_accel_over_shaper_rule"),
    }


PROPOSED = _proposed()


def axis_range(mass_kg: float, reflected_kg: float, k_motor: float, k_belt_default: float, k_frame: float | None,
               toolhead_mount: str | None = None, belt_ea_default: float = 22000.0, n: int = 2000, seed: int = 0,
               k_toolhead: float | None = None) -> dict:
    """Resonance of one axis as a range under the fitted parameter ranges. Stiffnesses in N/mm; `k_belt_default` is
    the belt stiffness the twin computed at `belt_ea_default`; mass includes the reflected rotor inertia.
    k_toolhead: the design's own toolhead term at the fitted block stiffness (it scales in proportion to that
    stiffness, so its range is the parameter's). toolhead_mount: the older flat figure, used only when k_toolhead is None."""
    rng = np.random.default_rng(seed)
    ea = rng.triangular(*PROPOSED["belt_ea_n_per_6mm"], n) / belt_ea_default
    inv = 1.0 / k_motor + 1.0 / (k_belt_default * ea) + (1.0 / k_frame if k_frame else 0.0)
    inv0 = 1.0 / k_motor + 1.0 / k_belt_default + (1.0 / k_frame if k_frame else 0.0)
    if k_toolhead:
        lo, mid, hi = PROPOSED["toolhead_tilt_effective_n_per_um"]
        inv = inv + 1.0 / (k_toolhead * rng.triangular(lo, mid, hi, n) / mid)
        inv0 += 1.0 / k_toolhead
    elif toolhead_mount:
        inv = inv + 1.0 / rng.triangular(*PROPOSED["toolhead_mount_n_per_mm"][toolhead_mount], n)
    f = np.sqrt(1e3 / inv / (mass_kg - reflected_kg)) / (2 * math.pi)

    def corner(i):       # every ranged stiffness at the same end of its range: the low and high the scorecard reports
        e = PROPOSED["belt_ea_n_per_6mm"]
        iv = 1.0 / k_motor + 1.0 / (k_belt_default * e[i] / belt_ea_default) + (1.0 / k_frame if k_frame else 0.0)
        if k_toolhead:
            t = PROPOSED["toolhead_tilt_effective_n_per_um"]
            iv += 1.0 / (k_toolhead * t[i] / t[1])
        elif toolhead_mount:
            iv += 1.0 / PROPOSED["toolhead_mount_n_per_mm"][toolhead_mount][i]
        return round(math.sqrt(1e3 / iv / (mass_kg - reflected_kg)) / (2 * math.pi), 1)

    return {"point_hz": round(math.sqrt(1e3 / inv0 / (mass_kg - reflected_kg)) / (2 * math.pi), 1),
            "low_hz": corner(0), "median_hz": round(float(np.median(f)), 1), "high_hz": corner(2),
            "p5_hz": round(float(np.percentile(f, 5)), 1), "p95_hz": round(float(np.percentile(f, 95)), 1)}


def design_ranges(design_path, print_report, frame_stiffness: dict | None = None,
                  toolhead_axis: str | None = "x", toolhead_mount: str = "linear_rail_single_block",
                  max_clean_accel: float | None = None, reflected_kg: dict | None = None,
                  belt_ea_default: float = 22000.0) -> dict:
    """The scorecard's resonance and acceleration for a design, as [low, expected, high] under the fitted ranges
    (belt stiffness; the toolhead term's block stiffness), in closed form from a twin `print_report.json`.

    design_path: the design file (loaded only to read each drive's reflected rotor inertia; not loaded
    when `reflected_kg` = {"x": kg, "y": kg} is given).
    print_report: dict or path, e.g. out/<name>/score/nominal/print_report.json. A report written by the fitted twin
    carries its own toolhead term (dynamics.toolhead_compliance); for an older report the flat figure
    `toolhead_mount` is put on `toolhead_axis` instead.
    frame_stiffness: the scorecard's `frame_stiffness_n_per_mm`."""
    rep = json.loads(Path(print_report).read_text()) if not isinstance(print_report, dict) else print_report
    dyn = rep["dynamics"]
    if reflected_kg is None:
        from ..runner import load_design
        from ..verifiers.ratings import resolve_drives
        from . import printer_map_for

        design = load_design(design_path)
        resolve_drives(design)
        pm = printer_map_for(design)
        jl = {j.name: j for j in design.joints}
        reflected_kg = {ax: jl[getattr(pm, ax)].reflected_inertia for ax in "xy"}
        belt_ea_default = pm.belt_ea_n
    has_term = "toolhead_compliance" in dyn
    out = {"axes": {}}
    for i, ax in enumerate("xy"):
        refl = reflected_kg[ax]
        kb = sum(b["n_per_mm"] for b in dyn.get("belts_per_axis", {}).get(ax, []))
        ks, f0, mass = dyn["series_stiffness_n_per_mm"][i], dyn["load_resonance_hz"][i], dyn["axis_mass_kg"][i]
        if not kb or not ks:
            continue
        kt = (dyn.get("toolhead_compliance") or {}).get(ax, {}).get("n_per_mm")
        inv_f = 1.0 / ks - 1.0 / kb - (1.0 / kt if kt else 0.0)
        k_frame = (frame_stiffness or {}).get(ax) or (1.0 / inv_f if inv_f > 1e-9 else None)
        k_eff = (mass - refl) * (2 * math.pi * f0) ** 2 * 1e-3
        k_motor = 1.0 / (1.0 / k_eff - 1.0 / ks)
        flat = toolhead_mount if (not has_term and ax == toolhead_axis) else None
        r = axis_range(mass, refl, k_motor, kb, k_frame, flat, belt_ea_default=belt_ea_default, k_toolhead=kt)
        r.update({"stiffness_n_per_mm": {"motor": round(k_motor, 1), "belt": round(kb, 1), "frame": round(k_frame, 1) if k_frame else None,
                                         "toolhead": round(kt, 1) if kt else None},
                  "toolhead_mount_term": ("derived from the design (guide blocks, nozzle offset)" if kt else flat),
                  "scorecard_hz": f0})
        out["axes"][ax] = r
    lo = min(a["low_hz"] for a in out["axes"].values())
    med = min((a["scorecard_hz"] if has_term else a["median_hz"]) for a in out["axes"].values())
    hi = min(a["high_hz"] for a in out["axes"].values())
    u = PROPOSED["used_accel_over_shaper_rule"]
    out["resonance_hz"] = {ax: [a["low_hz"], (a["scorecard_hz"] if has_term else a["median_hz"]), a["high_hz"]] for ax, a in out["axes"].items()}
    out["shaper_rule_accel_mm_s2"] = [shaper_accel(lo), shaper_accel(med), shaper_accel(hi)]
    out["accel_owners_would_run_mm_s2"] = [round(shaper_accel(lo) * u[0], -2), round(shaper_accel(med) * u[1], -2),
                                           round(shaper_accel(hi) * u[2], -2)]
    if max_clean_accel is not None:
        out["step_loss_ceiling_accel_mm_s2"] = max_clean_accel
        out["scorecard_max_clean_accel_mm_s2"] = max_clean_accel
        out["note"] = ("The step-loss ceiling is where the simulated motors lose steps. On the three reference machines that limit "
                       "sat 6 to 8 times above what owners run; treat it as a ceiling and accel_owners_would_run as the usable figure.")
    out["proposed_parameters"] = PROPOSED
    return out


def _main(argv):
    if argv and argv[0] == "predict":
        print(json.dumps(predict(), indent=1))
    elif argv and argv[0] == "compare":
        frozen = argv[1] if len(argv) > 1 else None
        print(json.dumps(compare(pred=json.loads(Path(frozen).read_text()) if frozen else None), indent=1))
    elif argv and argv[0] == "posthoc":
        print(json.dumps(compare_posthoc(), indent=1))
    elif argv and argv[0] == "design" and len(argv) >= 3:
        print(json.dumps(design_ranges(argv[1], argv[2]), indent=1))
    else:
        print(__doc__)


if __name__ == "__main__":
    import sys

    _main(sys.argv[1:])
