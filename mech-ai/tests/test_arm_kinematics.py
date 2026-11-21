"""Arm concept spike (mechloop.arm): FK/IK round trips, Jacobians, known-answer error cases, cell geometry."""
import numpy as np
import pytest

from mechloop.arm import accuracy as A
from mechloop.arm import cell as C
from mechloop.arm import poses as PZ
from mechloop.arm.candidates import SECTIONS, Articulated5, Cartesian, Scara, beam, rotary_spec

RNG = np.random.default_rng(3)


def _scara():
    return Scara(dict(bx=100.0, by=-500.0, L1=280.0, L2=340.0, zc_min=150.0, zc_max=500.0, home_deg=90.0))


def _art():
    return Articulated5(dict(bx=60.0, by=-450.0, h0=110.0, L2=250.0, L3=280.0, home_deg=90.0))


def _cart():
    return Cartesian(dict(y_m=-670.0, x_min=-800.0, x_max=900.0, zr_min=150.0, zr_max=400.0, e_min=200.0, e_max=740.0))


def test_scara_fk_ik_round_trip_both_branches():
    arm = _scara()
    n = 0
    for _ in range(200):
        r, a = RNG.uniform(80, 600), RNG.uniform(-np.pi, np.pi)
        p = np.array([100 + r * np.cos(a), -500 + r * np.sin(a), RNG.uniform(50, 300)])
        sols = arm.ik(p, 110.0)
        if not sols:
            continue
        assert len(sols) == 2 and {arm.branch(q) for q in sols} == {1, -1}
        for q in sols:
            assert np.allclose(arm.fk(q, 110.0), p, atol=1e-6)
        n += 1
    assert n > 150
    assert arm.ik(np.array([100.0 + 700, -500.0, 100.0]), 110.0) == []          # beyond L1 + L2


def test_articulated_fk_ik_round_trip_and_tool_axis():
    arm = _art()
    for tilt in (0.0, 30.0, 90.0):
        n = 0
        for _ in range(200):
            p = np.array([RNG.uniform(-300, 400), RNG.uniform(-200, 100), RNG.uniform(50, 350)])
            sols = arm.ik(p, 70.0, tilt)
            if not sols:
                continue
            q = sols[0]
            assert np.allclose(arm.fk(q, 70.0), p, atol=1e-6)
            *_, er, t = arm.fk_points(q, 70.0)
            assert np.isclose(np.degrees(np.arccos(np.clip(-t[2], -1, 1))), tilt, atol=1e-6)   # tilt from vertical
            assert q[2] <= 0.0                                                                 # elbow-up branch
            n += 1
        assert n > 50


def test_cartesian_round_trip():
    arm = _cart()
    for _ in range(50):
        p = RNG.uniform([-700, -400, 50], [800, 60, 250])
        (q,) = arm.ik(p, 70.0)
        assert np.allclose(arm.fk(q, 70.0), p)
    assert arm.ik(np.zeros(3), 70.0, tilt_deg=45.0) == []    # no tool pitch


@pytest.mark.parametrize("make,tool", [(_scara, 110.0), (_art, 70.0)])
def test_jacobian_matches_finite_difference(make, tool):
    arm = make()
    p = np.array([150.0, -150.0, 150.0])
    q = np.asarray(arm.ik(p, tool)[0], float)
    tcp, J = A.jacobian(arm, q, tool)
    for j in range(len(q)):
        dq = np.zeros_like(q)
        dq[j] = 1e-6
        fd = (arm.fk(q + dq, tool) - arm.fk(q - dq, tool)) / 2e-6
        assert np.allclose(J[j], fd, atol=1e-5), j


def test_known_answer_scara_encoder_error_at_full_extension():
    """Straight SCARA (theta2 = 0) along y: an encoder step on theta1 moves the TCP by (L1 + L2) * step, sideways."""
    arm = Scara(dict(bx=0.0, by=0.0, L1=250.0, L2=250.0, zc_min=0.0, zc_max=1000.0, home_deg=90.0))
    q = np.array([0.0, 0.0, 300.0, 0.0])
    tcp, J = A.jacobian(arm, q, 100.0)
    assert np.allclose(tcp[:2], [0.0, 500.0])
    assert np.allclose(J[0], [-500.0, 0.0, 0.0]) and np.allclose(J[1], [-250.0, 0.0, 0.0])
    # 14-bit encoder on theta1 only (others perfect): worst error = 500 mm x 1 LSB (servo dither +/- 1 count)
    spec = rotary_spec("belt_2stage", "AS5047P")
    spec = dict(spec, noise=0.0)
    zero = dict(kind="R", step=0.0, noise=0.0, backlash=0.0, k=None, label="perfect", cost=0)
    arm.joint_specs = [spec, zero, dict(zero, kind="P"), zero]
    dq = A.joint_samples(arm.joint_specs, 20000, np.random.default_rng(0))
    err = np.abs(dq @ J)[:, 0]
    lsb = np.radians(360 / 2 ** 14)
    assert err.max() == pytest.approx(500 * lsb, rel=1e-3)        # 0.19 mm, the 02_actuators.md table value
    assert 500 * lsb == pytest.approx(0.19, abs=0.005)


def test_known_answer_cantilever_from_beam_segments():
    """A tip load on a cantilever modelled as segment springs gives F L^3 / (3 EI) (and F L^2 / 2EI slope)."""
    L, F = 400.0, 20.0
    el = beam([0, 0, 0], [L, 0, 0], [0, 1, 0], "al_40x40x2", n=40)
    tcp = np.array([L, 0.0, 0.0])
    d = sum(A._element(tcp, p, Cr, Ct, np.array([0, 0, -F]), np.zeros(3)) for p, Cr, Ct, _ in el)
    ei = SECTIONS["al_40x40x2"][0]
    assert d[2] == pytest.approx(-F * L ** 3 / (3 * ei), rel=2e-3)
    assert ei == pytest.approx(5.1e9, rel=0.02)                    # 01_kinematics.md 4.3: 40 x 40 x 2 tube EI 5.1e9
    assert -F * L ** 3 / (3 * ei) == pytest.approx(-0.084, abs=0.002)   # 01: ~0.08 mm under 20 N at 400 mm


def test_cell_geometry_and_distances():
    assert C.BED_TOP_MIN == pytest.approx(228.95) and C.BED_TOP_MAX - C.BED_TOP_MIN == 180.0
    assert np.linalg.norm(C.handle_xy(37.0) - C.DOOR_HINGE) == pytest.approx(C.HANDLE_R)
    b = C.Box("b", (0, 0, 0), (10, 10, 10))
    d = C.dist_points_box(np.array([[5, 5, 5], [13, 14, 5], [5, 5, 12]], float), b)
    assert np.allclose(d, [-5, 5, 2])
    door = [o for o in C.obstacles(C.CellState(door_deg=90.0)) if isinstance(o, C.Panel)][0]
    assert np.allclose(door.p1, C.DOOR_HINGE + [0, -C.DOOR_W])
    # every station sits outside the door's sweep (the loop's radius plus 15 mm) in both layouts
    for lay in C.LAYOUTS:
        for n, (x0, x1, y0, y1, top) in C.stations(lay).items():
            corners = np.array([[x, y] for x in (x0, x1) for y in (y0, y1)]) - C.DOOR_HINGE
            ang = np.degrees(np.arctan2(-corners[:, 1], corners[:, 0]))
            inside = (ang >= 0) & (ang <= C.DOOR_OPEN_DEG) & (np.linalg.norm(corners, axis=1) < C.HANDLE_R + 15)
            assert not inside.any(), (lay, n)


def test_task_poses_file_matches_generator():
    saved = PZ.load()
    gen = PZ.build_poses()
    assert [p["id"] for p in saved] == [p["id"] for p in gen]
    classes = {p["accuracy_class"] for p in gen}
    assert classes == {"sheet", "assembly"}
    assert {p["stage"] for p in gen} == {"A", "B", "C", "D"}
    pull = [p for p in gen if p["id"] == "A4_pull_240"][0]
    pts = np.array(pull["points"])
    assert np.ptp(pts[:, 1]) == pytest.approx(C.PULL_TEST) and np.ptp(pts[:, 0]) == 0 and np.ptp(pts[:, 2]) == 0
