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


# ---------------------------------------------------------------- blind study against three real machines
def test_blind_inputs_are_still_the_frozen_ones():
    """The three machines' parameters were frozen before their measured resonances were looked up
    (research_notes/calibration/FREEZE.md). Changing them afterwards would make the study worthless."""
    from mechloop.twin.calibration import frozen_hash

    assert frozen_hash() == "4561db2df882dafed988b5aa936d412a7cf222bd984e070ca477691f235dd7bf"


def test_blind_predictions_against_measured_resonances():
    """What the blind study found, pinned so that a change to the axis model shows up here.
    Gantry and bed axes (belts carry the compliance) land within 20 % of the owners' median;
    axes that carry only the toolhead are over-predicted, by 15 to 75 %, because the twin has no
    compliance between the belt and the nozzle unless a design's FEA case supplies it."""
    from mechloop.twin.calibration import compare

    c = compare(n=100, step_loss=False)
    rows = {(r["machine"], r["axis"]): r for r in c["rows"]}
    assert len(rows) == 6
    for r in rows.values():
        if r["kind"] == "gantry or bed":
            assert abs(r["error_pct"]) < 20.0, r
            assert r["inside_measured_iqr"], r
        else:
            assert 15.0 < r["error_pct"] < 75.0, r
    # the belt stiffness each gantry / bed axis implies stays inside the proposed range
    from mechloop.twin.calibration import PROPOSED

    lo, _, hi = PROPOSED["belt_ea_n_per_6mm"]
    for r in rows.values():
        if r["kind"] == "gantry or bed":
            assert lo - 500 <= r["implied"]["belt_ea_n_per_6mm"] <= hi + 500, r


def test_proposed_ranges_cover_the_measurements():
    """With the proposed parameter ranges, every measured median lies inside the predicted range."""
    from mechloop.twin.calibration import PROPOSED, machines, measurements, resonance

    ea = PROPOSED["belt_ea_n_per_6mm"]
    for key, mach in machines().items():
        mount = PROPOSED["toolhead_mount_n_per_mm"]["v_wheels" if key == "ender3" else "linear_rail_single_block"]
        for axis in "xy":
            f = [resonance(mach, axis, ea_per_mm=ea[i] / 6.0, frame=mount[i] if axis == "x" else None) for i in (0, 2)]
            m = measurements()[key][f"{axis}_hz"]["median"]
            assert f[0] * 0.97 <= m <= f[1] * 1.03, (key, axis, f, m)


def test_shaper_rule_matches_the_klipper_documentation_example():
    """Klipper's documented example: MZV at 34.6 Hz -> max_accel <= 3500, ZV at 34.4 -> 4500, EI at 41.4 -> 3200."""
    from mechloop.twin.calibration import shaper_accel

    for kind, f, a in (("mzv", 34.6, 3500.0), ("zv", 34.4, 4500.0), ("ei", 41.4, 3200.0)):
        assert abs(shaper_accel(f, kind) - a) / a < 0.10


def test_axis_range_brackets_the_point_value():
    from mechloop.twin.calibration import axis_range

    r = axis_range(1.66, 0.40, 416.0, 499.0, 1239.0)
    assert r["low_hz"] < r["median_hz"] < r["high_hz"]
    assert r["low_hz"] < r["point_hz"] < r["high_hz"] * 1.02          # the default (22 kN) sits inside the proposed range
    soft = axis_range(0.446, 0.086, 213.0, 269.0, 1773.0, toolhead_mount="linear_rail_single_block")
    assert soft["high_hz"] < soft["point_hz"]                         # a toolhead axis rings lower than the scored point


# ---------------------------------------------------------------- fitted twin (2026-11-15): toolhead term, damping, extrusion, ranges
FIT = ROOT / "research_notes" / "fitting"


def test_second_comparison_with_the_toolhead_term_is_marked_not_blind_and_closes_the_toolhead_gap():
    """The frozen inputs are untouched (hash test above); the term's geometry lives in its own post-hoc file."""
    from mechloop.twin.calibration import compare_posthoc

    c = compare_posthoc()
    assert c["blind"] is False
    rows = {(r["machine"], r["axis"]): r for r in c["rows"]}
    for (key, axis), r in rows.items():
        if r["kind"] == "gantry or bed":
            assert r["with_term_hz"] == r["blind_hz"]                      # nothing was added to the axes that were right
        else:
            assert 15.0 < r["blind_error_pct"] < 75.0 and abs(r["with_term_error_pct"]) < 5.0, r
    # the honest figure: each rail machine predicted with the block stiffness the OTHER one implies
    for key in ("voron0", "trident250"):
        loo = rows[(key, "x")]["leave_one_out"]
        assert loo["fitted_on"] != key and abs(loo["error_pct"]) < 6.0, loo
        assert 7.5 <= rows[(key, "x")]["implied_block_n_per_um"] <= 16.0     # inside the range the table carries
    assert rows[("ender3", "x")]["leave_one_out"] is None                   # one wheeled machine: nothing to hold out


def _slider(n_blocks: int, pitch: float = 40.0, nozzle=(0.0, -30.0, -40.0)):
    from build123d import Box, Location, Pos

    from mechloop.model import Design, Joint
    from mechloop.parts import mgn12_rail, mgn12h_carriage, place

    d = Design("tilt")
    place(d, "rail", mgn12_rail(250), Location((0, 0, 0)))
    xs = [0.0] if n_blocks == 1 else [-pitch / 2, pitch / 2]
    for i, x in enumerate(xs):
        place(d, f"block{i}", mgn12h_carriage(), Location((x, 0, 0)), body="car", guides="x")
    d.add("head", Pos(0, -15, -10) * Box(30, 30, 40), body="car")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50)))
    d.tool_point = ("car", nozzle)
    return d


def test_toolhead_term_follows_block_count_spacing_and_nozzle_offset():
    """K_rot = k (n L^2 / 12 + sum a_i^2), stiffness at the nozzle K_rot / arm^2 (verifiers.ratings.guide_tilt)."""
    from mechloop.verifiers.ratings import block_track_length_m, guide_tilt

    d1 = _slider(1)
    blk = d1.get("block0")
    L = block_track_length_m(blk)
    assert abs(L - 0.0324) < 1e-9                                           # Hiwin's L1 for the MGN12H, from the vendor file
    c = blk.shape.center()
    noz = np.array(d1.tool_point[1], dtype=float)
    arm = math.hypot(noz[1] - c.Y, noz[2] - c.Z) * 1e-3                     # distance from the rail line, any direction across it
    g1 = guide_tilt(d1, "x", noz, k_n_per_m=10e6)
    assert abs(g1["k_rot_nm_per_rad"] - 10e6 * L ** 2 / 12) < 0.1 and abs(g1["arm_mm"] - arm * 1e3) < 0.06
    assert abs(g1["n_per_mm"] - 10e6 * L ** 2 / 12 / arm ** 2 * 1e-3) < 0.5
    # twice as far from the rail: a quarter of the stiffness
    far = guide_tilt(_slider(1, nozzle=(0.0, 2 * (noz[1] - c.Y) + c.Y, 2 * (noz[2] - c.Z) + c.Z)), "x",
                     (0.0, 2 * (noz[1] - c.Y) + c.Y, 2 * (noz[2] - c.Z) + c.Z), k_n_per_m=10e6)
    assert abs(far["n_per_mm"] / g1["n_per_mm"] - 0.25) < 0.01
    # two blocks 40 mm apart: the couple dominates
    g2 = guide_tilt(_slider(2), "x", noz, k_n_per_m=10e6)
    assert abs(g2["k_rot_nm_per_rad"] - 10e6 * (2 * L ** 2 / 12 + 2 * 0.02 ** 2)) < 0.1
    assert g2["n_per_mm"] > 9 * g1["n_per_mm"]
    # the twin applies it to the axis whose body carries the nozzle, with the fitted block stiffness, and can be told otherwise
    from mechloop.twin.machine import toolhead_compliance

    th = toolhead_compliance(d1, PrinterMap())
    assert set(th) == {"x"} and abs(th["x"]["n_per_mm"] - g1["n_per_mm"] * PrinterMap().toolhead_tilt_n_per_um / 10.0) < 0.2
    assert toolhead_compliance(d1, PrinterMap(toolhead_compliance=False)) == {}
    assert toolhead_compliance(d1, PrinterMap(toolhead_stiffness={"x": 170.0}))["x"]["n_per_mm"] == 170.0


def test_ringing_mode_gets_the_fitted_damping_ratio_and_the_fit_is_what_the_table_says():
    from mechloop.twin import fitted as F
    from mechloop.twin.machine import _low_mode_damping, spring_damping_for

    for target in (0.043, 0.065, 0.116):
        zs = spring_damping_for(target, 2.1e5, 1.1e5, 0.086, 0.36, 0.25)
        assert abs(_low_mode_damping(2.1e5, 1.1e5, 0.086, 0.36, 0.25, zs) - target) < 1e-4
    # a stepper damper that already gives more than the target leaves the belt damper at zero
    assert spring_damping_for(0.001, 2.1e5, 1.1e5, 0.086, 0.36, 0.25) == 0.0
    fit = __import__("json").loads((FIT / "damping_fit.json").read_text())
    for row in fit["synthetic_check"]:                                      # the estimator, on spectra of known damping
        assert abs(row["mode_fit_median"] - row["zeta_true"]) < 0.003 < row["half_power_median"] - row["zeta_true"]
    v, e = F.value("ringing_damping_ratio"), F.entry("ringing_damping_ratio")
    assert v == {"toolhead_axis": fit["per_axis"]["x"]["zeta_one_file"]["median"], "gantry_or_bed_axis": fit["per_axis"]["y"]["zeta_one_file"]["median"]}
    for k in v:
        assert e["low"][k] < v[k] < e["high"][k]
        assert e["low"][k] <= 0.05 <= e["high"][k] and e["low"][k] <= 0.07                # the owner-entered values (0.05 to 0.07) are inside
        assert all(e["low"][k] <= fit["held_out"][a][h]["median"] <= e["high"][k] for a in "xy" for h in ("fit_half", "held_out_half"))


def test_extruder_lag_is_selected_by_drive_type_nozzle_and_tube_length():
    from mechloop.twin import fitted as F

    ext = __import__("json").loads((FIT / "extrusion_fit.json").read_text())
    assert F.extruder_lag("direct", 0.4) == ext["pressure_advance"]["direct 0.4"]["median"] == PrinterMap().extruder_lag_s
    assert F.extruder_lag("bowden", 0.4) == ext["pressure_advance"]["bowden 0.4"]["median"]
    assert 6.0 < F.extruder_lag("bowden", 0.4) / F.extruder_lag("direct", 0.4) < 10.0
    assert F.extruder_lag("direct", 0.6) < F.extruder_lag("direct", 0.5) < F.extruder_lag("direct", 0.4) < F.extruder_lag("direct", 0.25)
    # a nozzle size left out of the table is recovered from its neighbours to within the spread between filaments
    lo, hi, mid = (ext["pressure_advance"][f"direct {d}"]["median"] for d in ("0.4", "0.6", "0.5"))
    assert abs(math.sqrt(lo * hi) / mid - 1) < 0.15
    # a shorter Bowden tube lags less, a tube of no length is a direct drive
    assert F.extruder_lag("bowden", 0.4, 215.0) < F.extruder_lag("bowden", 0.4, 430.0) == F.extruder_lag("bowden", 0.4)
    assert abs(F.extruder_lag("bowden", 0.4, 1e-9) - F.extruder_lag("direct", 0.4)) < 1e-4
    assert F.extruder_lag("bowden", 0.4, 420.0, "low") < F.extruder_lag("bowden", 0.4, 420.0) < F.extruder_lag("bowden", 0.4, 420.0, "high")


@pytest.fixture(scope="module")
def v5():
    return load_design(ROOT / "designs" / "printer_v5.py")


def test_printer_v5_gets_the_bowden_lag_a_v6_class_melt_cap_and_a_softer_x_axis(v5):
    from mechloop.twin import extruder_of, fitted as F, printer_map_for
    from mechloop.twin.machine import linear_axis, machine_model

    ex = extruder_of(v5)
    assert ex["drive"] == "bowden" and ex["bowden_length_mm"] == 420.0 and ex["hotend_sku"] == "HOTEND-V6"
    pm = printer_map_for(v5, None, struct_stiffness={"x": 1773.0, "y": 1239.0})
    assert pm.extruder_lag_s == F.extruder_lag("bowden", 0.4, 420.0) and 0.2 < pm.extruder_lag_s < 0.26
    assert pm.max_volumetric_flow == 11.0 and pm.max_volumetric_flow_basis["class"] == "v6"
    mm = machine_model(v5, pm)
    th = mm["toolhead"]
    assert set(th) == {"x"} and th["x"]["blocks"] == 1 and 150.0 < th["x"]["n_per_mm"] < 280.0
    fx, fy = (linear_axis(mm, k, pm)["modes"][0] for k in (0, 1))
    stiff = machine_model(v5, replace(pm, toolhead_compliance=False))
    fx0, fy0 = (linear_axis(stiff, k, pm)["modes"][0]["hz"] for k in (0, 1))
    assert 60.0 < fx["hz"] < 78.0 < fx0                                     # was 88.6 Hz without the term
    assert abs(fy["hz"] - fy0) < 0.5                                         # the gantry axis is not touched
    assert abs(fx["damping_ratio"] - 0.065) < 1e-3 and abs(fy["damping_ratio"] - 0.069) < 1e-3


def test_print_planning_respects_the_melt_rate_and_says_when_a_speed_is_flow_limited(printer, tmp_path, base):
    fast = replace(PrinterMap(), perimeter_speed=120.0, infill_speed=160.0)
    free = go(printer, tmp_path / "free", fast)
    capped = go(printer, tmp_path / "cap", replace(fast, max_volumetric_flow=6.0))
    assert free["flow"]["cap_mm3_s"] is None and "limited" not in free["flow"] and free["flow"]["peak_flow_in_gcode_mm3_s"] > 9.0
    f = capped["flow"]
    assert set(f["limited"]) == {"perimeter", "infill"} and f["limited"]["infill"]["requested_flow_mm3_s"] > 6.0
    assert f["peak_flow_in_gcode_mm3_s"] <= 6.0 * 1.10 and f["over_cap_moves"] == 0
    assert abs(f["speed_at_cap_mm_s"] - 6.0 / f["bead_section_mm2"]) < 0.06
    assert "flow_limited" in [x["code"] for x in capped["findings"]] and capped["ok"]
    assert capped["plan"]["print_time_s"] > free["plan"]["print_time_s"] * 1.1          # the slowed moves cost time
    # at the design's own speeds nothing is limited by an 11 mm^3/s hotend, and the print is the same print
    same = go(printer, tmp_path / "same", replace(PrinterMap(), max_volumetric_flow=11.0))
    assert same["flow"]["limited"] == {} and abs(same["plan"]["print_time_s"] - base["plan"]["print_time_s"]) < 0.5


def test_scorecard_ranges_bracket_the_point_and_the_ceiling_keeps_its_old_key():
    from mechloop.twin import fitted as F
    from mechloop.twin.calibration import design_ranges, shaper_accel
    from mechloop.twin.evals import uncertainty_sets

    rep = {"dynamics": {"belts_per_axis": {"x": [{"n_per_mm": 269.1}], "y": [{"n_per_mm": 499.0}]},
                        "series_stiffness_n_per_mm": [110.6, 355.7, None], "load_resonance_hz": [71.6, 62.2, 146.2],
                        "axis_mass_kg": [0.446, 1.66, 3.0], "toolhead_compliance": {"x": {"n_per_mm": 210.1}}}}
    r = design_ranges(None, rep, frame_stiffness={"x": 1773.0, "y": 1239.0}, max_clean_accel=10000.0, reflected_kg={"x": 0.086, "y": 0.40})
    for ax in "xy":
        lo, mid, hi = r["resonance_hz"][ax]
        assert lo < mid < hi and mid == rep["dynamics"]["load_resonance_hz"]["xy".index(ax)]
    assert (r["resonance_hz"]["x"][2] - r["resonance_hz"]["x"][0]) > (r["resonance_hz"]["y"][2] - r["resonance_hz"]["y"][0])   # the toolhead axis is the less certain
    u = F.triple("used_accel_over_shaper_rule")
    assert u == [0.4, 0.5, 0.65]
    own = r["accel_owners_would_run_mm_s2"]
    assert own[0] < own[1] < own[2] < r["step_loss_ceiling_accel_mm_s2"] == r["scorecard_max_clean_accel_mm_s2"]
    assert abs(own[1] - 0.5 * shaper_accel(min(r["resonance_hz"][a][1] for a in "xy"))) <= 100.0
    sets = uncertainty_sets(PrinterMap())
    assert sets["soft"]["belt_ea_n"] < sets["expected"]["belt_ea_n"] == 22000.0 < sets["stiff"]["belt_ea_n"]
    assert sets["soft"]["extruder_lag_s"] > sets["expected"]["extruder_lag_s"] > sets["stiff"]["extruder_lag_s"]
    assert sets["soft"]["ringing_damping_ratio"]["toolhead_axis"] < sets["stiff"]["ringing_damping_ratio"]["toolhead_axis"]


def test_every_parameter_in_the_table_states_source_range_and_held_out_check():
    from mechloop.twin import fitted as F

    rows = F.summary_rows()
    keys = {r["parameter"] for r in rows}
    assert {"belt_ea_n_per_6mm", "toolhead_tilt_effective_n_per_um", "ringing_damping_ratio", "extruder_lag_s", "melt_rate_cap_mm3_s",
            "hotend_thermal", "heater_relay_test", "used_accel_over_shaper_rule", "friction_n", "step_loss_boundary",
            "guide_block_radial_n_per_um", "frame_and_joint_stiffness", "bed_thermal", "warp_cooling_adhesion"} <= keys
    for r in rows:
        assert r["status"] and r["source"] and r["held_out"], r["parameter"]
        if not r["status"].startswith("NOT FITTED"):
            assert r["low"] is not None and r["high"] is not None, r["parameter"]
