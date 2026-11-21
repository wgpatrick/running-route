"""Three skeleton arms for the concept spike (all exploratory): SCARA 4-axis, front-loading Cartesian, compact 5-axis.

Each arm gives forward / inverse kinematics of the tool centre point (TCP), capsules for the clearance sweep, its joints
(axis, point) for the error Monte Carlo, and lumped compliances (beams split into segments, bearing tilt springs, belt
stretch) for the deflection model. Section and stiffness values are est. unless a source is named; see JOINT_OPTIONS and
SECTIONS for what each assumes.
"""
from __future__ import annotations

import numpy as np

from .cell import Capsule

Z = np.array([0.0, 0.0, 1.0])
E_AL, G_AL = 69e3, 26e3     # MPa, 6061
E_PETG, G_PETG = 2.0e3, 0.75e3  # MPa, printed PETG (est., 01 uses E ~ 2 GPa)


def tube_rect(b, h, t, E=E_AL, G=G_AL):
    """Rectangular tube b wide x h deep, wall t: (EI about the axis that bends in the h direction, EI other, GJ)."""
    ih = (b * h ** 3 - (b - 2 * t) * (h - 2 * t) ** 3) / 12
    ib = (h * b ** 3 - (h - 2 * t) * (b - 2 * t) ** 3) / 12
    am, s = (b - t) * (h - t), 2 * ((b - t) + (h - t))
    return E * ih, E * ib, G * 4 * am ** 2 * t / s


SECTIONS = {   # (EI_1 in-plane / vertical, EI_2 other, GJ), N·mm²
    "al_60x30x2": tube_rect(30, 60, 2),         # link core, 60 deep
    "al_40x40x2": tube_rect(40, 40, 2),         # 01's ram / link section (EI 5.1e9)
    "al_60x60x3": tube_rect(60, 60, 3),         # column / mast
    "al_80x40x3": tube_rect(40, 80, 3),         # stiffer link core, 80 deep
    "petg_60x30x3": tube_rect(30, 60, 3, E_PETG, G_PETG),   # printed-only box link (DG-01 arm exception), 01's 4.5e8
}

# ---------------------------------------------------------------- joint options (est. unless sourced)
# step: servo dither +/- one count (deg or mm); noise: 1 sigma; backlash: total play, random side when the load sign is
# uncertain; k_axis: compliance of the transmission seen at the TCP when the loop does not close on the joint output
ENCODERS = {   # output encoders, 02 section 4. Noise values est. (verify on the datasheet / bench).
    "AS5047P": dict(lsb=360 / 2 ** 14, noise=0.011, cost=16),     # 14-bit; DigiKey adapter board ~$16 (02)
    "MT6835": dict(lsb=360 / 2 ** 21, noise=0.003, cost=25),      # 21-bit; chip $5-10 (02) + board est.
    "AksIM-2": dict(lsb=360 / 2 ** 20, noise=0.0008, cost=220),   # RLS off-axis ring, $150-300 est. (02)
}
TRANSMISSIONS = {   # backlash deg at the output, stiffness N·mm/rad at the output, ratio, cost of the joint (est., 02 sec 6)
    "belt_2stage": dict(backlash=0.03, k=1.0e6, ratio=12, cost=90),   # GT2 + HTD 15 mm 2 stages (my calc ~1000 N·m/rad)
    "capstan_25": dict(backlash=0.0, k=1.0e7, ratio=25, cost=105),    # printed 2-stage capstan, recipe A ($80-130)
    "cycloid_15": dict(backlash=0.117, k=5.0e5, ratio=15, cost=85),   # 7 arcmin preloaded (arXiv 2410.16591)
    "strainwave_50": dict(backlash=20 / 3600, k=5.0e6, ratio=50, cost=300),   # StepperOnline HSS-14-50 (20 arcsec), recipe C
}
SERVOS = {   # smart servos, 02 section 2.3; backlash est. 0.25-0.3 deg (02), k from a raised P gain (est.)
    "XL430": dict(step=360 / 4096, noise=0.0, backlash=0.25, k=1.0e5, cost=50),
    "XM430": dict(step=360 / 4096, noise=0.0, backlash=0.25, k=2.0e5, cost=310),
}
# Tilt (moment) stiffness of a rotary joint's bearing set, N·mm/rad (est.): two deep-groove bearings ~30 mm apart in a
# printed housing vs an angular-contact (or crossed-roller) pair in an aluminium housing. Upgrade est. +$30 per joint.
K_TILT = {"printed": 2.0e7, "metal": 1.0e8}
MOTOR_CPR = 4000    # StepperOnline 17HS24-2104-ME1K: 1000 PPR = 4000 CPR (02)


def rotary_spec(trans: str, enc: str | None) -> dict:
    t = TRANSMISSIONS[trans]
    if enc is None:     # loop closed on the motor encoder only: backlash and windup are seen at the TCP
        return dict(kind="R", step=360 / (MOTOR_CPR * t["ratio"]), noise=0.0, backlash=t["backlash"], k=t["k"],
                    label=f"{trans}+motor-enc", cost=t["cost"])
    e = ENCODERS[enc]
    return dict(kind="R", step=e["lsb"], noise=e["noise"], backlash=0.0, k=None, label=f"{trans}+{enc}",
                cost=t["cost"] + e["cost"])


def servo_spec(name: str) -> dict:
    s = SERVOS[name]
    return dict(kind="R", step=s["step"], noise=s["noise"], backlash=s["backlash"], k=s["k"], label=name, cost=s["cost"])


def linear_spec(kind: str) -> dict:
    if kind == "belt":      # closed-loop NEMA17 + 20T GT2 (40 mm/rev): 0.01 mm per count; repeatability est.
        return dict(kind="P", step=0.01, noise=0.005, backlash=0.0, k=None, label="belt+closed-loop", cost=70)
    if kind == "leadscrew":  # T8x8 + anti-backlash nut (est. 0.01 mm), closed loop: 0.002 mm per count
        return dict(kind="P", step=0.002, noise=0.003, backlash=0.01, k=2.0e4, label="T8 leadscrew", cost=60)
    raise KeyError(kind)


def beam(a, b, n1, sec: str, n: int = 12, label: str = "beam") -> list:
    """Beam a->b split into n segments: list of (point, C_rot (rad per N·mm), C_trans). n1: axis of the EI_1 bending."""
    a, b, n1 = map(np.asarray, (a, b, n1))
    L = np.linalg.norm(b - a)
    if L < 1e-6:
        return []
    u = (b - a) / L
    n1 = n1 - u * (n1 @ u)
    n1 /= np.linalg.norm(n1)
    n2 = np.cross(u, n1)
    ei1, ei2, gj = SECTIONS[sec]
    ds = L / n
    Cr = ds * (np.outer(n1, n1) / ei1 + np.outer(n2, n2) / ei2 + np.outer(u, u) / gj)
    return [(a + u * ds * (i + 0.5), Cr, None, label) for i in range(n)]


def tilt(p, axis, k, label="tilt") -> tuple:
    """Bearing / guide tilt spring: compliance 1/k about every axis perpendicular to `axis` (N·mm/rad)."""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    return (np.asarray(p, float), (np.eye(3) - np.outer(axis, axis)) / k, None, label)


def rot_all(p, k, label="mount") -> tuple:
    return (np.asarray(p, float), np.eye(3) / k, None, label)


def trans(p, axis, k, label="axial") -> tuple:
    axis = np.asarray(axis, float)
    return (np.asarray(p, float), None, np.outer(axis, axis) / k, label)


def _wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


class Arm:
    name = "arm"
    layout = "ring"     # station layout the arm works in (mechloop.arm.cell.LAYOUTS)
    WRAP_INDEX = None   # index of a continuous base joint (path continuity check), None for linear axes

    def __init__(self, params: dict, joint_specs: list | None = None):
        self.params = dict(params)
        self.joint_specs = list(joint_specs or [])

    def margin_deg(self, q) -> float:     # smallest distance to a joint limit (deg or mm/ - for prismatic)
        raise NotImplementedError


# ================================================================ SCARA 4-axis
class Scara(Arm):
    """theta1, theta2 (vertical axes), Z carriage on a column, roll. Link2 hangs 45 mm under link1; flange 25 mm under
    link2; the tool hangs down from the flange."""
    name = "SCARA 4-axis"
    WRAP_INDEX = 0
    LINK_DZ, FLANGE_DZ = 45.0, 25.0
    T1_LIM, T2_LIM = np.radians(165), np.radians(150)

    def __init__(self, params, joint_specs=None, link_sec="al_60x30x2", k_tilt=K_TILT["printed"]):
        super().__init__(params, joint_specs or [])
        self.link_sec, self.k_tilt = link_sec, k_tilt

    def zc_for(self, tcp_z, tool_len):
        return tcp_z + tool_len + self.LINK_DZ + self.FLANGE_DZ

    def ik(self, p, tool_len, tilt_deg=0.0):
        if tilt_deg:
            return []
        P = self.params
        dx, dy = p[0] - P["bx"], p[1] - P["by"]
        r2 = dx * dx + dy * dy
        L1, L2 = P["L1"], P["L2"]
        c2 = (r2 - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
        if abs(c2) > 1:
            return []
        zc = self.zc_for(p[2], tool_len)
        sols = []
        for s in (1, -1):
            t2 = s * np.arccos(c2)
            t1 = np.arctan2(dy, dx) - np.arctan2(L2 * np.sin(t2), L1 + L2 * np.cos(t2))
            sols.append(np.array([_wrap(t1 - np.radians(P.get("home_deg", 90.0))), t2, zc, 0.0]))
        return sols

    def branch(self, q):
        return int(np.sign(q[1]))

    def fk_points(self, q, tool_len):
        P = self.params
        t1 = q[0] + np.radians(P.get("home_deg", 90.0))
        b = np.array([P["bx"], P["by"], q[2]])
        e = b + P["L1"] * np.array([np.cos(t1), np.sin(t1), 0])
        w = e + P["L2"] * np.array([np.cos(t1 + q[1]), np.sin(t1 + q[1]), 0]) - Z * self.LINK_DZ
        f = w - Z * self.FLANGE_DZ
        return b, e, w, f, f - Z * tool_len

    def fk(self, q, tool_len):
        return self.fk_points(q, tool_len)[-1]

    def margin_deg(self, q):
        P = self.params
        m = min(np.degrees(self.T1_LIM - abs(q[0])), np.degrees(self.T2_LIM - abs(q[1])))
        zm = min(q[2] - P["zc_min"], P["zc_max"] - q[2])
        return m if zm >= 0 else -1.0

    def capsules(self, q, tool):
        P = self.params
        b, e, w, f, tcp = self.fk_points(q, tool[0])
        col_top = P["zc_max"] + 80
        return [Capsule("column", np.array([P["bx"], P["by"], 0.0]), np.array([P["bx"], P["by"], col_top]), 40.0),
                Capsule("link1", b, e, 30.0),
                Capsule("elbow", e, e - Z * self.LINK_DZ, 30.0),
                Capsule("link2", e - Z * self.LINK_DZ, w, 27.0),
                Capsule("tool", f, tcp + Z * 25.0, tool[1], tool=True)]

    def joints(self, q, tool_len):
        b, e, w, f, tcp = self.fk_points(q, tool_len)
        return [("R", Z, b), ("R", Z, e), ("P", Z, b), ("R", Z, w)]

    def compliance(self, q, tool_len):
        P = self.params
        b, e, w, f, tcp = self.fk_points(q, tool_len)
        base = np.array([P["bx"], P["by"], 0.0])
        u1 = (e - b) / np.linalg.norm(e - b)
        u2 = (w - (e - Z * self.LINK_DZ)) / max(1e-9, np.linalg.norm(w - (e - Z * self.LINK_DZ)))
        el = []
        el += [rot_all(base, 1.0e8, "column foot")]                   # column foot on the bench plate (est.)
        el += beam(base, b, [1, 0, 0], "al_60x60x3", label="column")  # column up to the carriage
        el += [tilt(b, Z, 1.0e8, "Z carriage")]                       # Z carriage on 2 MGN12 blocks (est.)
        el += [tilt(b, Z, self.k_tilt, "theta1 bearings")]            # theta1 bearing pair (K_TILT)
        el += beam(b, e, np.cross(Z, u1), self.link_sec, label="link1")
        el += [tilt(e, Z, self.k_tilt, "theta2 bearings")]            # theta2 bearing pair
        el += beam(e - Z * self.LINK_DZ, w, np.cross(Z, u2), self.link_sec, label="link2")
        el += [tilt(f, Z, 1.0e7, "roll bearing")]                     # roll servo bearing (est.)
        return el

    def default_specs(self, enc="AS5047P"):
        return [rotary_spec("belt_2stage", enc), rotary_spec("belt_2stage", enc), linear_spec("leadscrew"),
                servo_spec("XL430")]


# ================================================================ front-loading Cartesian
class Cartesian(Arm):
    """X along the bench front (rail line at y_m), mast at X - 65, Z carriage, a Y ram (40x40 tube) at x = X pointing
    into the printer; the tool hangs from the ram's tip. q = [X, Zr (ram axis height), E (ram tip y - y_m), roll]."""
    name = "front-loading Cartesian"
    MAST_DX, RAM_HALF = -65.0, 20.0

    def __init__(self, params, joint_specs=None, ram_sec="al_40x40x2"):
        super().__init__(params, joint_specs or [])
        self.ram_sec = ram_sec

    @property
    def ram_len(self):
        P = self.params
        return P["e_max"] - P["e_min"] + 250.0

    def ik(self, p, tool_len, tilt_deg=0.0):
        if tilt_deg:
            return []
        P = self.params
        return [np.array([p[0], p[2] + tool_len + self.RAM_HALF + 5.0, p[1] - P["y_m"], 0.0])]

    def branch(self, q):
        return 0

    def fk(self, q, tool_len):
        P = self.params
        return np.array([q[0], P["y_m"] + q[2], q[1] - self.RAM_HALF - 5.0 - tool_len])

    def margin_deg(self, q):
        P = self.params
        return min(q[0] - P["x_min"], P["x_max"] - q[0], q[1] - P["zr_min"], P["zr_max"] - q[1], q[2] - P["e_min"],
                   P["e_max"] - q[2])

    def capsules(self, q, tool):
        P = self.params
        x, zr, e = q[0], q[1], q[2]
        ym = P["y_m"]
        tip = np.array([x, ym + e, zr])
        mx = x + self.MAST_DX
        tcp = self.fk(q, tool[0])
        return [Capsule("mast", np.array([mx, ym, 0.0]), np.array([mx, ym, P["zr_max"] + 100]), 38.0),
                Capsule("x_beam", np.array([P["x_min"] - 120, ym, 40.0]), np.array([P["x_max"] + 120, ym, 40.0]), 50.0),
                Capsule("ram", tip - np.array([0, self.ram_len, 0]), tip, 29.0),
                Capsule("tool", tip - Z * (self.RAM_HALF + 5), tcp + Z * 25.0, tool[1], tool=True)]

    def joints(self, q, tool_len):
        tcp = self.fk(q, tool_len)
        return [("P", np.array([1.0, 0, 0]), tcp), ("P", Z, tcp), ("P", np.array([0, 1.0, 0]), tcp), ("R", Z, tcp)]

    def compliance(self, q, tool_len):
        P = self.params
        x, zr, e = q[0], q[1], q[2]
        ym = P["y_m"]
        mx = x + self.MAST_DX
        foot = np.array([mx, ym, 60.0])
        top = np.array([mx, ym, zr])
        el = [rot_all(foot, 5.0e8, "X carriage")]                    # X carriage, 4 blocks on 2 rails (est.)
        L1, L2 = x - (P["x_min"] - 120), (P["x_max"] + 120) - x     # X belt spans each side
        ea = 3.0e4                                                    # 9 mm GT2 EA, N (est.)
        el += [trans(foot, [1, 0, 0], ea * (1 / L1 + 1 / L2), "X belt")]
        el += beam(foot, top, [1, 0, 0], "al_60x60x3", label="mast")
        el += [rot_all(top, 1.0e8, "Z carriage")]                     # Z carriage on the mast (est.)
        el += [trans(top, Z, 2.0e4, "Z leadscrew")]                   # Z leadscrew axial (est.)
        sup = np.array([x, ym, zr])
        el += [tilt(sup, [0, 1, 0], 2.0e8, "ram guide")]              # ram rail blocks, 150 mm apart (est.)
        Lr1 = e - P["e_min"] + 125.0
        el += [trans(sup, [0, 1, 0], ea * (1 / Lr1 + 1 / max(50.0, self.ram_len - Lr1)), "ram belt")]
        front = sup + np.array([0, 75.0, 0])
        tip = np.array([x, ym + e, zr])
        if tip[1] > front[1]:
            el += beam(front, tip, [1, 0, 0], self.ram_sec, label="ram")
        el += [tilt(tip - Z * 25, Z, 1.0e7, "roll bearing")]          # roll servo bearing (est.)
        return el

    def default_specs(self, enc=None):
        return [linear_spec("belt"), linear_spec("leadscrew"), linear_spec("belt"), servo_spec("XL430")]


# ================================================================ compact 5-axis articulated
class Articulated5(Arm):
    """Base yaw, shoulder, elbow, wrist pitch, wrist roll. Planar angles: a = upper arm elevation, b = elbow relative
    (b <= 0: elbow up), c = wrist pitch relative; tool direction psi = a + b + c in the arm's vertical plane."""
    name = "compact 5-axis"
    WRAP_INDEX = 0
    LW = 60.0    # wrist pitch axis to flange (est.)
    LIM = {"q1": 170, "a": (-20, 160), "b": (-165, 0), "c": (-135, 135)}

    def __init__(self, params, joint_specs=None, link_sec="al_60x30x2", k_tilt=K_TILT["printed"]):
        super().__init__(params, joint_specs or [])
        self.link_sec, self.k_tilt = link_sec, k_tilt

    def ik(self, p, tool_len, tilt_deg=0.0):
        P = self.params
        dx, dy = p[0] - P["bx"], p[1] - P["by"]
        rho = np.hypot(dx, dy)
        q1 = np.arctan2(dy, dx)
        psi = np.radians(-90.0 + tilt_deg)     # tilt leans the tool outward, away from the base
        D = self.LW + tool_len
        wr, wz = rho - D * np.cos(psi), p[2] - D * np.sin(psi) - P["h0"]
        L2, L3 = P["L2"], P["L3"]
        cb = (wr ** 2 + wz ** 2 - L2 ** 2 - L3 ** 2) / (2 * L2 * L3)
        if abs(cb) > 1:
            return []
        b = -np.arccos(cb)
        a = np.arctan2(wz, wr) - np.arctan2(L3 * np.sin(b), L2 + L3 * np.cos(b))
        c = psi - a - b
        return [np.array([_wrap(q1 - np.radians(P.get("home_deg", 90.0))), a, b, _wrap(c), 0.0])]

    def branch(self, q):
        return 0

    def fk_points(self, q, tool_len):
        P = self.params
        q1 = q[0] + np.radians(P.get("home_deg", 90.0))
        er = np.array([np.cos(q1), np.sin(q1), 0.0])
        base = np.array([P["bx"], P["by"], 0.0])
        s = base + Z * P["h0"]
        a, phi, psi = q[1], q[1] + q[2], q[1] + q[2] + q[3]
        e = s + P["L2"] * (np.cos(a) * er + np.sin(a) * Z)
        w = e + P["L3"] * (np.cos(phi) * er + np.sin(phi) * Z)
        t = np.cos(psi) * er + np.sin(psi) * Z
        f = w + self.LW * t
        return base, s, e, w, f, f + tool_len * t, er, t

    def fk(self, q, tool_len):
        return self.fk_points(q, tool_len)[5]

    def margin_deg(self, q):
        d = np.degrees(q)
        L = self.LIM
        return min(L["q1"] - abs(d[0]), d[1] - L["a"][0], L["a"][1] - d[1], d[2] - L["b"][0], L["b"][1] - d[2],
                   d[3] - L["c"][0], L["c"][1] - d[3])

    def capsules(self, q, tool):
        base, s, e, w, f, tcp, er, t = self.fk_points(q, tool[0])
        return [Capsule("base", base, s, 50.0), Capsule("upper_arm", s, e, 32.0), Capsule("forearm", e, w, 28.0),
                Capsule("wrist", w, f, 26.0), Capsule("tool", f, tcp - t * 25.0, tool[1], tool=True)]

    def joints(self, q, tool_len):
        base, s, e, w, f, tcp, er, t = self.fk_points(q, tool_len)
        k = np.cross(er, Z)       # pitch axis
        return [("R", Z, base), ("R", k, s), ("R", k, e), ("R", k, w), ("R", t, f)]

    def compliance(self, q, tool_len):
        base, s, e, w, f, tcp, er, t = self.fk_points(q, tool_len)
        k = np.cross(er, Z)
        el = [rot_all(base, 1.0e8, "base foot")]                      # base on the bench plate (est.)
        el += beam(base, s, [1, 0, 0], "al_60x60x3", label="base column")
        el += [tilt(s, Z, 5.0e7, "yaw bearing")]                      # base yaw bearing, large (est.)
        el += [tilt(s, k, self.k_tilt, "shoulder bearings")]          # shoulder bearings, out of plane (K_TILT)
        el += beam(s, e, k, self.link_sec, label="upper arm")
        el += [tilt(e, k, self.k_tilt, "elbow bearings")]
        el += beam(e, w, k, self.link_sec, label="forearm")
        el += [tilt(w, k, 1.0e7, "wrist bearing")]                    # wrist pitch bearing (est.)
        return el

    def default_specs(self, enc="AS5047P", wrist="XL430"):
        wr = servo_spec(wrist) if wrist in SERVOS else rotary_spec(*wrist)
        return [rotary_spec("belt_2stage", enc), rotary_spec("capstan_25", enc), rotary_spec("capstan_25", enc), wr,
                servo_spec("XL430")]
