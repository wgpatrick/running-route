"""Digital twin building blocks."""
import numpy as np

from mechloop.twin.planner import plan
from mechloop.twin.stepper import simulate


def test_planner_respects_limits_and_reaches_every_point():
    pts = np.array([[0, 0, 0], [50, 0, 0], [50, 30, 0], [0, 30, 0], [0, 30, 2], [0, 0, 2]], dtype=float)
    vmax, amax = np.array([200.0, 200.0, 10.0]), np.array([3000.0, 3000.0, 100.0])
    Q, V, seg, frac, seg_t = plan(pts, np.full(5, 150.0), vmax, amax, 0.001)
    assert np.all(np.abs(V) <= vmax + 1e-6)
    # acceleration within limits except the deliberate junction-speed steps at corners
    acc = np.abs(np.diff(V, axis=0)) / 0.001
    inside = np.diff(seg) == 0
    assert np.all(acc[inside] <= amax * 1.02 + 1e-6)
    assert np.allclose(Q[-1], pts[-1], atol=0.2)
    for k in range(1, len(pts)):          # passes through every corner
        assert np.min(np.linalg.norm(Q - pts[k], axis=1)) < 0.2
    # time for a 50 mm move from rest to rest at 150 mm/s, 3000 mm/s^2: L/v + v/a (corners slow it slightly)
    assert 50 / 150 + 150 / 3000 - 0.05 < seg_t[0] < 50 / 150 + 150 / 3000 + 0.01


def ramp(accel, v=100.0, dist=60.0, dt=0.001):
    pts = np.array([[0.0], [dist]])
    Q, V, *_ = plan(pts, np.array([v]), np.array([v]), np.array([accel]), dt)
    hold = int(0.3 / dt)
    return np.vstack([Q, np.repeat(Q[-1:], hold, 0)]), np.vstack([V, np.zeros((hold, 1))])


def test_stepper_follows_when_strong_and_loses_steps_when_weak():
    # 1 kg axis on a 40 mm/rev belt
    Qc, Vc = ramp(2000.0)
    strong = np.full((len(Qc), 1), 40.0)   # needs m*a = 2 N
    Qa, _, info = simulate(Qc, Vc, np.array([1.0]), strong, np.array([40.0]), np.array([0.0]), np.array([0.5]), 0.001)
    assert np.abs(Qa - Qc).max() < 0.05 and abs(Qa[-1, 0] - Qc[-1, 0]) < 0.01
    weak = np.full((len(Qc), 1), 1.2)      # cannot supply 2 N: falls out of step
    Qa, _, _ = simulate(Qc, Vc, np.array([1.0]), weak, np.array([40.0]), np.array([0.0]), np.array([0.5]), 0.001)
    lost = abs(Qa[-1, 0] - Qc[-1, 0])
    assert lost > info["quarter_cycle_mm"][0]
    # it comes to rest a whole number of electrical cycles (0.8 mm) away: a layer shift
    assert abs(lost / 0.8 - round(lost / 0.8)) < 0.1


def test_gravity_load_shows_as_a_steady_offset():
    Qc = np.zeros((1500, 1)); Vc = np.zeros((1500, 1))
    f = np.full((1500, 1), 100.0)
    Qa, _, _ = simulate(Qc, Vc, np.array([2.0]), f, np.array([2.0]), np.array([-50.0]), np.array([0.0]), 0.001)
    # sin(k_e * err) = 50/100 -> err = (pi/6) / (2 pi 50 / 2) mm
    assert abs(Qa[-1, 0] + (np.pi / 6) / (2 * np.pi * 50 / 2)) < 2e-4


# ---------------------------------------------------------------- firmware features: known answers
def _klippy():
    import pytest

    from mechloop.twin import klippy_code as K

    if not K.available():
        pytest.skip("Klipper's source is not installed (tools/setup_klipper.sh)")
    return K


def _oscillator_residual(u, dt, f0, zeta, t_after):
    """Largest |x - u_final| of x'' + 2 z w x' + w^2 x = w^2 u after time t_after."""
    from scipy.signal import lsim

    w = 2 * np.pi * f0
    t = np.arange(len(u)) * dt
    _, x, _ = lsim(([w * w], [1.0, 2 * zeta * w, w * w]), u, t)
    return float(np.abs(x[t >= t_after] - u[-1]).max())


def test_a_single_mode_driven_through_klippers_zv_and_mzv_shapers_at_its_frequency_does_not_ring():
    K = _klippy()
    dt, f0, zeta = 1e-4, 50.0, 0.05
    t = np.arange(0, 0.6, dt)
    u = np.clip((t - 0.05) / 0.013, 0.0, 1.0)          # a 1 mm move in 13 ms: about two thirds of a period, so it rings
    after = 0.05 + 0.013 + 0.025                         # the move, plus the longest shaper here
    plain = _oscillator_residual(u, dt, f0, zeta, after)
    assert plain > 0.2
    for name, limit in (("zv", 0.02), ("mzv", 0.02)):
        A, T = K.shaper_impulses(name, f0, zeta)
        A = np.array(A) / sum(A)
        shaped = sum(a * np.interp(t - ti, t, u, left=0.0) for a, ti in zip(A, T))
        assert _oscillator_residual(shaped, dt, f0, zeta, after) < limit * plain, name
    # a shaper tuned 30 % off does not cancel it
    A, T = K.shaper_impulses("zv", 1.3 * f0, zeta)
    A = np.array(A) / sum(A)
    off = sum(a * np.interp(t - ti, t, u, left=0.0) for a, ti in zip(A, T))
    assert _oscillator_residual(off, dt, f0, zeta, after) > 0.25 * plain


def test_klippers_shaper_choice_lands_on_the_resonance_it_is_given():
    K = _klippy()
    f = np.arange(5.0, 200.0, 0.5)
    for f0 in (40.0, 75.0):
        H = 1.0 / np.sqrt((1 - (f / f0) ** 2) ** 2 + (2 * 0.1 * f / f0) ** 2)
        got = K.choose_shaper(f, (f * H) ** 2)
        zv = next(c for c in got["candidates"] if c["shaper_type"] == "zv")
        assert abs(zv["shaper_freq"] - f0) < 0.05 * f0
        assert got["shaper_type"] in ("zv", "mzv", "ei", "2hump_ei", "3hump_ei") and got["remaining_vibrations_frac"] < 0.05


def test_linearised_axis_reproduces_a_one_mass_oscillator_and_the_stepper_simulation():
    from mechloop.twin import PrinterMap
    from mechloop.twin.machine import linear_axis

    pm = PrinterMap(damping_ratio=0.2)
    drive = {"curve": [(0, 1.0), (1e6, 1.0)], "holding_nmm": 300.0, "efficiency": 1.0, "travel_per_rev": 40.0}
    mm = {"drives": [drive] * 3, "tpr": np.array([40.0] * 3), "series": [None] * 3, "mass": np.array([1.0] * 3),
          "motor_mass": np.array([0.0] * 3)}
    lin = linear_axis(mm, 0, pm)
    f_max = 2 * np.pi * 300.0 / 40.0                      # N
    k = f_max * (2 * np.pi * 50 / 40.0) * 1e3             # N/m: slope of F_max sin(k_e x) at zero
    assert abs(lin["modes"][0]["hz"] - np.sqrt(k / 1.0) / 2 / np.pi) < 1e-6
    assert abs(lin["modes"][0]["damping_ratio"] - 0.2) < 1e-9
    assert abs(abs(lin["H"](0.0)) - 1.0) < 1e-12
    # the time-domain stepper model rings at that frequency after a small step in the command
    Qc = np.full((4000, 1), 0.01); Qc[:10] = 0.0
    Qa, _, _ = simulate(Qc, np.zeros_like(Qc), np.array([1.0]), np.full((4000, 1), f_max), np.array([40.0]), np.array([0.0]),
                        np.array([0.0]), 0.0001, damping_ratio=0.2)
    x = Qa[:, 0] - 0.01
    up = np.flatnonzero((x[:-1] < 0) & (x[1:] >= 0))
    f_sim = 1.0 / (np.diff(up).mean() * 0.0001)
    assert abs(f_sim - lin["modes"][0]["hz"] * np.sqrt(1 - 0.2 ** 2)) < 0.03 * f_sim


def test_pressure_advance_equal_to_the_melt_lag_cancels_it():
    from mechloop.twin.deposit import melt_flow

    dt, lag = 0.0005, 0.03
    t = np.arange(0, 1.0, dt)
    v = np.where((t > 0.1) & (t < 0.6), 5.0, 0.0)                    # filament speed: on, steady, off (a line and its end)
    v = np.convolve(v, np.ones(40) / 40, mode="same")                # with finite acceleration
    E = np.cumsum(v) * dt
    late = np.abs(melt_flow(E, lag, dt) - E).max()
    assert abs(late - 5.0 * lag) < 0.01                              # without it the nozzle runs v * lag behind: the corner blob
    for K, worst in ((lag, 0.004), (0.5 * lag, 0.5 * 5.0 * lag + 0.005)):      # 0.004: one time step of filament
        out = melt_flow(E + K * v, lag, dt)
        assert np.abs(out - E).max() < worst, K
    over = melt_flow(E + 2 * lag * v, lag, dt) - E                   # too much advance: ahead by the same amount
    assert over.max() > 0.9 * 5.0 * lag


def test_a_planar_tilted_bed_is_reproduced_exactly_by_klippers_mesh_and_removed():
    K = _klippy()
    from mechloop.twin.firmware import remove_mesh

    plane = lambda x, y: 0.002 * (x - 90) - 0.0015 * (y - 90)       # 0.36 mm across 180 in X, 0.27 mm in Y, zero mid-bed
    xs, ys = np.linspace(33, 182, 5), np.linspace(0, 180, 5)
    rng = np.random.default_rng(1)
    pts = rng.uniform([33, 0], [182, 180], size=(200, 2))
    for algo in ("bicubic", "lagrange"):
        prof = {"points": [[plane(x, y) for x in xs] for y in ys], "min_x": 33, "max_x": 182, "min_y": 0, "max_y": 180,
                "mesh_x_pps": 2, "mesh_y_pps": 2, "algo": algo, "tension": 0.2, "fade_start": 1.0, "fade_end": 10.0}
        z = K.mesh_z(prof, pts)                                       # Klipper's ZMesh.calc_z
        # Klipper's lagrange interpolation returns the plane; its bicubic (tension 0.2) is up to 0.01 mm off it
        assert np.abs(z - plane(pts[:, 0], pts[:, 1])).max() < (1e-6 if algo == "lagrange" else 0.01), algo
        assert np.abs(K.mesh_z_fast(prof, pts[:, 0], pts[:, 1]) - z).max() < 1e-6
        # what Klipper adds to Z (all of it below fade_start, fading to none at fade_end) is taken back out exactly
        for zg in (0.2, 0.9, 3.0, 9.5, 20.0):
            factor = 1.0 if zg <= 1.0 else max(0.0, (10.0 - zg) / 9.0)
            back, _ = remove_mesh(prof, pts[:, 0], pts[:, 1], zg + factor * z)
            assert np.abs(back - zg).max() < 1e-6, (algo, zg)
    # outside the probed area Klipper holds the edge value: the unprobed strip keeps the error of the tilt beyond it
    assert abs(float(K.mesh_z(prof, [(0.0, 90.0)])[0]) - plane(33.0, 90.0)) < 1e-6      # prof: the lagrange one


def test_bed_deviation_is_zero_at_the_reference_and_follows_tilt_and_bow():
    from mechloop.twin import PrinterMap, bed_deviation

    info = {"bed_size": (200.0, 100.0)}
    assert float(bed_deviation(PrinterMap(), info, 30.0, 20.0)) == 0.0
    pm = PrinterMap(bed_surface={"tilt_x_mm": 0.4, "tilt_y_mm": -0.2, "ref_xy": (10.0, 0.0)})
    assert abs(float(bed_deviation(pm, info, 10.0, 0.0))) < 1e-12
    assert abs(float(bed_deviation(pm, info, 110.0, 0.0)) - 0.2) < 1e-12          # half the width: half the rise
    assert abs(float(bed_deviation(pm, info, 10.0, 50.0)) + 0.1) < 1e-12
    bow = PrinterMap(bed_surface={"bow_mm": 0.3})
    assert abs(float(bed_deviation(bow, info, 100.0, 50.0)) + 0.3) < 1e-12        # corners 0.3 below the centre
