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
