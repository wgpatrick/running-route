"""Reality check: does the twin's axis model, fed only documented values for a real,
well-measured printer, predict what its community measures?

Machine: Voron 2.4 (350 mm), CoreXY. Sources and confidence for every input are in
research_notes/"Voron reference data for twin validation.md". Inputs that are uncertain
are sampled over their plausible range, so each prediction is a range.

This checks the axis dynamics (masses, motor stiffness, belt compliance, torque-speed
behaviour). It does not check deposition, and it treats CoreXY as two motors acting
together on each axis, which is exact only for axis-aligned moves.
"""
from __future__ import annotations

import math

import numpy as np

from .planner import plan
from .stepper import simulate

TPR = 40.0  # mm per motor rev (20T x 2 mm), official config: rotation_distance 40

MOTORS = {  # from the Klipper motor database (community transcription of datasheets)
    "OMC 17HS19-2004S1 (1.8 deg, BOM)": {"hold_nm": 0.59, "i_rated": 2.0, "L_h": 3.0e-3, "R": 1.4, "poles": 50, "rotor_gcm2": 82.0},
    "LDO-42STH40-2004MAH (0.9 deg, LDO kit)": {"hold_nm": 0.35, "i_rated": 2.0, "L_h": 2.8e-3, "R": 1.1, "poles": 100, "rotor_gcm2": 54.0},
}
OBSERVED = {
    "x_resonance_hz": (54.0, 62.0), "y_resonance_hz": (38.0, 50.0),          # input-shaper measurements
    "stock": {"speed": 300.0, "accel": 3000.0, "current_rms": 0.8},          # official config: must not skip
    "tuned_ok": [{"speed": 450.0, "accel": 7000.0, "current_rms": 0.875},    # user configs that run without skipping
                 {"speed": 650.0, "accel": 20000.0, "current_rms": 1.4}],
    "top_speed_1p8_mm_s": (800.0, 1000.0), "top_speed_0p9_mm_s": (450.0, 450.0),  # Ellis' guide, 2 A motors
    "pressure_advance_s": (0.03, 0.06),
}
RANGES = {  # uncertain inputs: (low, high)
    "x_mass_kg": (0.45, 0.60), "y_mass_kg": (1.30, 1.60),       # inferred brackets from community weights (low confidence)
    "belt_ea_n": (15400.0, 28600.0),                             # 6 mm GT2 (the A/B belts in the Voron CAD are 6 mm, not 9): 22 kN +/- 30 % (hobby measurement, low confidence)
    "belt_length_mm": (1450.0, 1900.0),                          # each CoreXY belt on a 350 (not sourced: estimated)
}


def motor_force(m: dict, current_rms: float, speed_mm_s, volts: float = 24.0):
    """Force one motor can put on the belt at a given speed. Torque is proportional to phase
    current; the current the driver can push falls once the winding's impedance at the
    electrical frequency exceeds the supply (back-EMF ignored, so this is an upper bound)."""
    i_cmd = current_rms * math.sqrt(2)
    w_e = 2 * math.pi * np.asarray(speed_mm_s, dtype=float) / TPR * m["poles"]
    i_max = volts / np.sqrt(m["R"] ** 2 + (w_e * m["L_h"]) ** 2)
    i = np.minimum(i_cmd, i_max)
    torque = m["hold_nm"] * i / (m["i_rated"] * math.sqrt(2))
    return 2 * math.pi * torque / (TPR * 1e-3)


def corner_speed(m: dict, current_rms: float, volts: float = 24.0) -> float:
    """Speed (mm/s) above which the driver can no longer hold the commanded current."""
    i_cmd = current_rms * math.sqrt(2)
    z = volts / i_cmd
    if z <= m["R"]:
        return 0.0
    w_e = math.sqrt(z * z - m["R"] ** 2) / m["L_h"]
    return w_e / m["poles"] / (2 * math.pi) * TPR


def resonance(mass_kg, ea, length_mm, m: dict, current_rms: float):
    """Load resonance of one axis: two motors' magnetic springs in series with two belts."""
    f1 = float(motor_force(m, current_rms, 0.0))
    k_step = 2 * f1 * (2 * math.pi * m["poles"] / TPR) * 1e3          # N/m, two motors
    k_belt = 2 * 4.0 * ea / length_mm * 1e3                             # N/m, two belts, carriage mid-span
    k = 1.0 / (1.0 / k_step + 1.0 / k_belt)
    refl = 2 * m["rotor_gcm2"] * 1e-7 * (2 * math.pi / (TPR * 1e-3)) ** 2
    return math.sqrt(k / mass_kg) / (2 * math.pi), k_belt * 1e-3, refl


def skips(mass_kg, ea, length_mm, m, current_rms, speed, accel, travel=250.0, dt=0.0005) -> bool:
    """Run a there-and-back move at the given limits on the stepper model; True if steps are lost."""
    pts = np.array([[0.0], [travel], [0.0], [travel], [0.0]])
    Qc, Vc, *_ = plan(pts, np.full(4, speed), np.array([speed]), np.array([accel]), dt)
    hold = int(0.3 / dt)
    Qc = np.vstack([Qc, np.repeat(Qc[-1:], hold, 0)])
    Vc = np.vstack([Vc, np.zeros((hold, 1))])
    f = 2 * motor_force(m, current_rms, np.abs(Vc[:, 0]))[:, None]
    _, k_belt, refl = resonance(mass_kg, ea, length_mm, m, current_rms)
    _, _, info = simulate(Qc, Vc, np.array([mass_kg + refl]), f, np.array([TPR]), np.array([0.0]), np.array([3.0]), dt,
                          motor_mass=np.array([refl]), series_stiffness=[k_belt], pole_pairs=m["poles"])
    qm = info["motor_positions"]
    return bool(abs(qm[-1, 0] - Qc[-1, 0]) > TPR / (4 * m["poles"]))


def check(n: int = 400, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    bom = MOTORS["OMC 17HS19-2004S1 (1.8 deg, BOM)"]
    ldo = MOTORS["LDO-42STH40-2004MAH (0.9 deg, LDO kit)"]
    S = {k: rng.uniform(*v, n) for k, v in RANGES.items()}
    cur = OBSERVED["stock"]["current_rms"]
    fx = np.array([resonance(S["x_mass_kg"][i], S["belt_ea_n"][i], S["belt_length_mm"][i], bom, cur)[0] for i in range(n)])
    fy = np.array([resonance(S["y_mass_kg"][i], S["belt_ea_n"][i], S["belt_length_mm"][i], bom, cur)[0] for i in range(n)])
    rows = []

    def band(name, pred, obs, unit, note=""):
        lo, hi = float(np.percentile(pred, 5)), float(np.percentile(pred, 95))
        inside = float(np.mean((pred >= obs[0]) & (pred <= obs[1])))
        overlap = not (hi < obs[0] or lo > obs[1])
        rows.append({"quantity": name, "predicted_5_95": [round(lo, 1), round(hi, 1)], "predicted_median": round(float(np.median(pred)), 1),
                     "observed": list(obs), "unit": unit, "fraction_of_predictions_inside_observed": round(inside, 2),
                     "verdict": "consistent" if overlap and inside >= 0.25 else ("marginal" if overlap else "inconsistent"),
                     "note": note})

    band("X resonance", fx, OBSERVED["x_resonance_hz"], "Hz")
    band("Y resonance", fy, OBSERVED["y_resonance_hz"], "Hz")
    mid = {k: float(np.mean(v)) for k, v in RANGES.items()}
    # settings that real machines run without losing steps: the twin must agree
    for label, st, motor in [("stock config", OBSERVED["stock"], bom)] + [
            (f"tuned config {i + 1}", s, bom) for i, s in enumerate(OBSERVED["tuned_ok"])]:
        res = {ax: skips(mid[f"{ax}_mass_kg"], mid["belt_ea_n"], mid["belt_length_mm"], motor, st["current_rms"],
                         st["speed"], st["accel"]) for ax in ("x", "y")}
        rows.append({"quantity": f"no step loss at {label} ({st['speed']:.0f} mm/s, {st['accel']:.0f} mm/s^2, {st['current_rms']} A)",
                     "predicted": "no skip" if not any(res.values()) else f"skips on {[a for a, v in res.items() if v]}",
                     "observed": "runs without skipping",
                     "verdict": "consistent" if not any(res.values()) else "inconsistent", "note": ""})
    # where the twin says steps are first lost at stock current (no measurement exists to compare against)
    lim = {}
    for ax in ("x", "y"):
        lo_a, hi_a = 3000.0, 400000.0
        for _ in range(12):
            a = math.sqrt(lo_a * hi_a)
            if skips(mid[f"{ax}_mass_kg"], mid["belt_ea_n"], mid["belt_length_mm"], bom, cur, 300.0, a):
                hi_a = a
            else:
                lo_a = a
        lim[ax] = round(lo_a, -2)
    rows.append({"quantity": "acceleration at which steps are first lost, stock current, 300 mm/s",
                 "predicted": lim, "observed": "no controlled measurement found; anecdotes pass 20,000-23,000",
                 "verdict": "not testable" if min(lim.values()) > 23000 else "inconsistent",
                 "note": "prediction only; it would be contradicted by a stock machine skipping below this"})
    # top speed: the model's corner speed is where torque starts to fall, the reports are where it runs out
    c18, c09 = corner_speed(bom, 1.4), corner_speed(ldo, 1.4)
    rows.append({"quantity": "speed where torque starts to fall, 1.4 A: 1.8 deg vs 0.9 deg motor",
                 "predicted": {"1.8 deg": round(c18), "0.9 deg": round(c09), "ratio": round(c18 / c09, 2)},
                 "observed": {"1.8 deg top speed": OBSERVED["top_speed_1p8_mm_s"], "0.9 deg top speed": OBSERVED["top_speed_0p9_mm_s"][0],
                              "ratio": [round(OBSERVED["top_speed_1p8_mm_s"][0] / 450, 2), round(OBSERVED["top_speed_1p8_mm_s"][1] / 450, 2)]},
                 "verdict": "consistent" if 1.6 <= c18 / c09 <= 2.4 else "marginal",
                 "note": "compares the ratio between motors; absolute top speed depends on the load during the test"})
    rows.append({"quantity": "extruder lag time constant", "predicted": 0.03, "observed": list(OBSERVED["pressure_advance_s"]),
                 "unit": "s", "verdict": "consistent",
                 "note": "the twin's assumed 30 ms lag sits inside the documented pressure-advance range for direct drive"})
    return {"machine": "Voron 2.4 350 (CoreXY), documented values only", "samples": n, "rows": rows,
            "inputs": {"ranges": RANGES, "stock": OBSERVED["stock"]}}
