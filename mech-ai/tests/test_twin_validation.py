"""Is the digital twin right? Known-answer experiments, convergence, analytic and
independent cross-checks, and qualitative realism. All on a short 20x20x4 mm print."""
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from mechloop.runner import load_design
from mechloop.twin import PrinterMap, run_print
from mechloop.twin.evals import quick_cube
from mechloop.twin.gcode import Move

ROOT = Path(__file__).parent.parent


@pytest.fixture(scope="module")
def printer():
    return load_design(ROOT / "designs" / "printer.py")


@pytest.fixture(scope="module")
def base(printer, tmp_path_factory):
    return run_print(printer, quick_cube(), tmp_path_factory.mktemp("base"), PrinterMap(), name="q",
                     render=False, collisions=False)


def go(printer, tmp_path, pm=None, **kw):
    return run_print(printer, quick_cube(), tmp_path, pm or PrinterMap(), name="q", render=False, collisions=False, **kw)


# ---------------------------------------------------------------- independent cross-checks
def test_agrees_with_the_slicers_own_estimates(base):
    """PrusaSlicer computes print time and filament use with its own planner; ours must agree."""
    assert base["ok"]
    assert abs(base["plan"]["print_time_s"] - base["slicer"]["print_time_s"]) / base["slicer"]["print_time_s"] < 0.10
    assert abs(base["print"]["filament_used_mm"] - base["slicer"]["filament_mm"]) / base["slicer"]["filament_mm"] < 0.005
    assert abs(base["print"]["deposited_volume_cm3"] - base["slicer"]["filament_cm3"]) / base["slicer"]["filament_cm3"] < 0.01


def test_stepper_model_matches_mujoco():
    """Same axis, same force law, integrated by MuJoCo instead of our integrator."""
    import mujoco

    from mechloop.twin.planner import plan
    from mechloop.twin.stepper import simulate

    m, fmax, tpr, fric = 0.8, 40.0, 40.0, 0.0
    dt = 0.0005
    Qc, Vc, *_ = plan(np.array([[0.0], [40.0], [10.0]]), np.array([120.0, 120.0]), np.array([150.0]), np.array([6000.0]), dt)
    ours, _, _ = simulate(Qc, Vc, np.array([m]), np.full((len(Qc), 1), fmax), np.array([tpr]), np.array([0.0]),
                          np.array([fric]), dt, damping_ratio=0.25)
    k_e = 2 * math.pi * 50 / tpr
    c = 2 * 0.25 * math.sqrt(fmax * k_e * 1e3 * m) * 1e-3
    sub = 20
    model = mujoco.MjModel.from_xml_string(f"""<mujoco><option timestep="{dt / sub}" gravity="0 0 0" integrator="RK4"/>
      <worldbody><body><joint name="x" type="slide" axis="1 0 0"/><geom size="0.01" mass="{m}"/></body></worldbody></mujoco>""")
    data = mujoco.MjData(model)
    theirs = np.zeros(len(Qc))
    for i in range(len(Qc)):
        theirs[i] = data.qpos[0] * 1e3
        nq = Qc[i + 1, 0] if i + 1 < len(Qc) else Qc[i, 0]
        nv = Vc[i + 1, 0] if i + 1 < len(Qc) else 0.0
        for s in range(sub):
            w = (s + 0.5) / sub
            qc, vc = Qc[i, 0] + (nq - Qc[i, 0]) * w, Vc[i, 0] + (nv - Vc[i, 0]) * w
            data.qfrc_applied[0] = fmax * math.sin(k_e * (qc - data.qpos[0] * 1e3)) + c * (vc - data.qvel[0] * 1e3)
            mujoco.mj_step(model, data)
    lag = np.abs(ours[:, 0] - Qc[:, 0]).max()
    assert np.abs(ours[:, 0] - theirs).max() < 0.15 * lag    # the two integrators agree to a fraction of the lag itself


# ---------------------------------------------------------------- known answers
def test_reports_an_injected_layer_shift(printer, tmp_path, base):
    """Shift everything above Z=2 mm by 0.5 mm in X in the G-code: the comparison must say 0.5 mm."""
    def shift(moves):
        return [Move(m.x + (0.5 if m.z > 2.0 else 0.0), m.y, m.z, m.e, m.feed, m.line) for m in moves]

    rep = go(printer, tmp_path, gcode_edit=shift)
    assert abs(rep["print"]["layer_shift_mm_worst"] - 0.5) < 0.06
    assert "print_layer_shift" in [f["code"] for f in rep["findings"]]
    assert base["print"]["layer_shift_mm_worst"] < 0.1


def test_reports_injected_under_extrusion_and_scale_error(printer, tmp_path, base):
    under = go(printer, tmp_path / "u", gcode_edit=lambda ms: [Move(m.x, m.y, m.z, m.e * 0.9, m.feed, m.line) for m in ms])
    ratio = under["print"]["deposited_volume_cm3"] / base["print"]["deposited_volume_cm3"]
    assert abs(ratio - 0.9) < 0.006
    assert under["print"]["outline_offset_mm"]["mean"] < base["print"]["outline_offset_mm"]["mean"]
    # a part printed 3% too big in XY: each face of a 20 mm cube moves out by 0.3 mm
    big = go(printer, tmp_path / "b", gcode_edit=lambda ms: [Move(m.x * 1.03, m.y * 1.03, m.z, m.e, m.feed, m.line) for m in ms])
    grow = big["print"]["outline_offset_mm"]["mean"] - base["print"]["outline_offset_mm"]["mean"]
    assert abs(grow - 0.3) < 0.05
    assert "print_dimension_error" in [f["code"] for f in big["findings"]]


def test_bed_datum_errors_are_caught(printer, tmp_path):
    high = go(printer, tmp_path / "h", z_datum_error=0.3)
    assert "first_layer_height" in [f["code"] for f in high["findings"]]
    low = go(printer, tmp_path / "l", z_datum_error=-0.3)
    assert "nozzle_in_bed" in [f["code"] for f in low["findings"]]


# ---------------------------------------------------------------- convergence
def test_results_do_not_depend_on_time_step_or_raster(printer, tmp_path, base):
    fine_t = go(printer, tmp_path / "t", dt=0.0005)
    for k in (0, 1):
        a, b = base["dynamics"]["rms_lag_mm"][k], fine_t["dynamics"]["rms_lag_mm"][k]
        assert abs(a - b) / max(b, 1e-9) < 0.10
    assert abs(base["print"]["outline_offset_mm"]["mean"] - fine_t["print"]["outline_offset_mm"]["mean"]) < 0.01
    fine_r = go(printer, tmp_path / "r", pm=replace(PrinterMap(), raster_px_per_mm=40))
    assert abs(base["print"]["outline_offset_mm"]["mean"] - fine_r["print"]["outline_offset_mm"]["mean"]) < 0.02
    assert abs(base["print"]["outline_iou_min"] - fine_r["print"]["outline_iou_min"]) < 0.01
    assert abs(base["print"]["deposited_volume_cm3"] - fine_r["print"]["deposited_volume_cm3"]) < 1e-6


# ---------------------------------------------------------------- qualitative realism
def test_axis_rings_at_the_predicted_frequency():
    """After an abrupt stop, the load on a stretchy belt oscillates at sqrt(k/m)."""
    from mechloop.twin.stepper import simulate

    dt = 0.0002
    n = int(0.4 / dt)
    Qc = np.concatenate([np.linspace(0, 3, 60), np.full(n, 3.0)])[:, None]
    Vc = np.concatenate([np.full(60, 3 / (60 * dt)), np.zeros(n)])[:, None]
    q, _, info = simulate(Qc, Vc, np.array([0.6]), np.full((len(Qc), 1), 60.0), np.array([40.0]), np.array([0.0]),
                          np.array([0.0]), dt, motor_mass=np.array([0.13]), series_stiffness=[80.0],
                          spring_damping_ratio=0.01)
    y = q[60:, 0] - 3.0
    y = y - y.mean()
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y))))
    f = np.fft.rfftfreq(len(y), dt)
    band = f > 10.0
    peak = f[band][spec[band].argmax()]
    assert abs(peak - info["load_resonance_hz"][0]) / info["load_resonance_hz"][0] < 0.12


def test_rigid_machine_tracks_better_than_a_compliant_one(printer, tmp_path, base):
    rigid = go(printer, tmp_path, pm=replace(PrinterMap(), compliant=False))
    assert rigid["dynamics"]["rms_lag_mm"][1] < 0.5 * base["dynamics"]["rms_lag_mm"][1]


def test_quality_degrades_with_speed_and_acceleration(printer, tmp_path, base):
    fast = go(printer, tmp_path, speed_scale=3.0, accel_scale=5.0)
    assert fast["plan"]["print_time_s"] < 0.75 * base["plan"]["print_time_s"]
    assert fast["dynamics"]["rms_lag_mm"][1] > 1.5 * base["dynamics"]["rms_lag_mm"][1]
    assert fast["print"]["max_bulge_mm"] >= base["print"]["max_bulge_mm"]
    assert fast["print"]["boundary_deviation_mm"]["mean"] > base["print"]["boundary_deviation_mm"]["mean"]


def test_voron_reference_predictions():
    """Fed only documented Voron 2.4 values, the axis model must land on its measured behaviour."""
    from mechloop.twin.reference import check

    rows = {r["quantity"]: r for r in check(n=200)["rows"]}
    assert rows["X resonance"]["verdict"] != "inconsistent"
    assert rows["Y resonance"]["verdict"] != "inconsistent"
    assert all(r["verdict"] == "consistent" for q, r in rows.items() if q.startswith("no step loss"))
