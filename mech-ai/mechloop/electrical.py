"""Electrical model of a machine: devices with typed ports, wires routed through the CAD, the firmware's
settings, and the physics the electrical verifier runs on them.

Units: V, A, W, ohm, degC, s, J/K, W/K; lengths in mm (wire resistance uses metres internally).

What lives here
- the declaration a design writes: `Electrical`, `Device`, `Port`, `Wire`, `Loom`, `Waypoint`, `Bay`
- wire physics: resistance, self-heating in still air, grouping derating
- NTC thermistor + ADC (Steinhart-Hart, the same arithmetic as Klipper's thermistor.py)
- a lumped thermal network with natural convection and radiation, and a closed-loop heater simulation
  that runs ports of Klipper's control laws (ControlPID, ControlBangBang, verify_heater, the ADC range
  check, PID_CALIBRATE's relay autotune) against it, with fault injection
- the stepper's electrical torque-speed limit (supply voltage, R, L, back-EMF)
- the circuit solution (currents, delivered voltages) and the generated wiring table / Klipper config

Every default number that is not derived from the design carries its basis in SOURCES below.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

SOURCES = {
    "copper": "resistivity 1.724e-8 ohm*m at 20 degC, temperature coefficient 0.00393 /K (IACS annealed copper)",
    "awg": "AWG diameter d = 0.127 mm * 92^((36 - n) / 39) (ASTM B258 definition)",
    "wire_h": "wire surface heat transfer 12 W/m^2K, convection + radiation in still air: ASSUMED (typical, unverified); "
              "it reproduces the common chassis-wiring ampacity tables to about 20 %",
    "grouping": "bundle derating factors as in IEC 60364-5-52 table B.52.17 (bunched in air): recalled, typical, unverified",
    "insulation": "PVC hook-up wire 80 degC (UL 1007), silicone 200 degC (UL 3135), PTFE/FEP 200 degC (UL 1332), "
                  "glass-fibre sleeved heater leads 300 degC: typical, unverified",
    "klipper": "control laws ported from Klipper klippy/extras heaters.py, verify_heater.py, pid_calibrate.py, "
               "thermistor.py, adc_temperature.py, tmc2208.py (github.com/Klipper3d/klipper, master, fetched 2026-11-14)",
    "convection": "natural convection: horizontal plate, hot side up Nu = 0.54 Ra^1/4 (Ra < 1e7) or 0.15 Ra^1/3; hot side "
                  "down Nu = 0.27 Ra^1/4; vertical/compact body Churchill-Chu (Incropera, Fundamentals of Heat and Mass "
                  "Transfer, ch. 9). Air properties from power-law fits around 300-400 K.",
    "enclosure_u": "sealed enclosure wall transmittance 5.5 W/m^2K (painted sheet steel, common enclosure-sizing rule): "
                   "typical, unverified",
    "motor_h": "stepper case to still air 12 W/m^2K over the motor's own surface, mounting plate ignored: ASSUMED "
               "(typical, unverified; it gives about the vendor's 80 K rise at rated current)",
    "stepper_model": "pull-out torque from the phasor model (V, R, L, back-EMF). Checked against StepperOnline's published "
                     "24 V pull-out curve for the 17HS13-0404S at 0.35 A rms: within 10 % from 120 to 900 rpm "
                     "(tests/test_electrical.py). No extra derating is applied; mid-band resonance is not modelled.",
}

KELVIN = 273.15
SIGMA = 5.670e-8

# kind of port -> kinds it may be wired to
COMPATIBLE = {
    "power_out": {"power_in"}, "power_in": {"power_out"},
    "heater_out": {"heater", "series", "switch_in"}, "heater": {"heater_out", "series", "switched_out"},
    "series": {"heater_out", "heater", "series", "switched_out", "power_out", "power_in", "mains_out", "mains_in"},
    "switched_out": {"heater", "series"}, "switch_in": {"heater_out"},
    "stepper_out": {"stepper"}, "stepper": {"stepper_out"},
    "fan_out": {"fan"}, "fan": {"fan_out"},
    "thermistor_in": {"thermistor"}, "thermistor": {"thermistor_in"},
    "endstop_in": {"endstop"}, "endstop": {"endstop_in"},
    "mains_out": {"mains_in", "series"}, "mains_in": {"mains_out", "series"},
    "pe": {"pe"},
    "signal_out": {"signal_in"}, "signal_in": {"signal_out"},
    "host": {"host"},
}
LOW_CURRENT = {"thermistor", "thermistor_in", "endstop", "endstop_in", "signal_out", "signal_in"}

INSULATION_MAX_C = {"pvc": 80.0, "pvc105": 105.0, "silicone": 200.0, "ptfe": 200.0, "fiberglass": 300.0}
INSULATION_WALL_MM = {"pvc": 0.4, "pvc105": 0.8, "silicone": 0.6, "ptfe": 0.25, "fiberglass": 0.5}
GROUPING = [(1, 1.0), (2, 0.8), (3, 0.7), (4, 0.65), (5, 0.6), (6, 0.57), (7, 0.54), (8, 0.52), (9, 0.5), (12, 0.45),
            (16, 0.41), (20, 0.38)]
CONNECTOR_MAX_A = {  # per contact
    "JST-XH": 3.0,       # JST XH series data sheet: 3 A, AWG 30-22 (recalled, unverified)
    "JST-VH": 10.0,      # JST VH series data sheet: 10 A, AWG 22-16 (recalled, unverified)
    "screw-5.08": 15.0,  # 5.08 mm PCB terminal block, typical 15-16 A (typical, unverified)
    "screw-psu": 20.0,   # barrier strip of an enclosed supply (typical, unverified; above the supply's own rating)
    "ferrule": 20.0, "ring-M4": 20.0, "faston-6.3": 15.0, "faston-4.8": 10.0, "dupont": 2.0, "solder": 20.0,
    "molex-microfit": 5.0, "usb": 1.0}
CONNECTOR_MIN_AWG = {"JST-XH": 22, "JST-VH": 16, "dupont": 22, "molex-microfit": 18}   # largest conductor the contact takes
DEFAULT_REQUIREMENTS = {
    "psu_max_load_frac": 0.85,       # worst-case simultaneous load / supply rating
    "output_max_load_frac": 0.8,     # continuous current / rating of a board output, terminal or connector
    "fuse_min_factor": 1.25,         # fuse rating / steady current
    "max_heater_vdrop_frac": 0.03,   # supply terminals -> heater
    "wire_max_temp_c": 70.0,         # conductor temperature allowed in a loom (PVC neighbours, plastic clips)
    "min_bend_radius_x_od": 5.0,     # flexing looms; static bends are held to half of this
    "wire_clearance_mm": 3.0,        # fixed runs to parts that move relative to them
    "hot_zone_mm": 12.0,             # closer than this to a hot part needs insulation rated for its temperature
    "connector_keepout_mm": 12.0,    # room in front of a connector for the plug and the first bend
    "thermistor_max_deg_per_count": 0.5,
    "hotend_heatup_max_s": 240.0, "bed_heatup_max_s": {60.0: 600.0, 100.0: 1500.0},
    "max_reach_margin_c": 20.0,      # a heater must be able to reach target + this at 100 % duty
    "overshoot_max_c": {"hotend": 10.0, "bed": 5.0}, "ripple_max_c": {"hotend": 2.0, "bed": 2.0},
    "fault_peak_limit_c": {"hotend": 300.0, "bed": 150.0},   # see docs/ELECTRICAL.md for what these protect
    "fault_trip_max_s": {"hotend": 60.0, "bed": 180.0},
    "bay_max_c": 50.0,               # Mean Well LRS full-load ambient limit
    "motor_max_case_c": 80.0,        # belts, printed parts and fingers nearby
    "ambient_c": 25.0,
}


# ============================================================ declaration
@dataclass
class Port:
    name: str
    kind: str
    connector: str = ""
    max_current_a: Optional[float] = None   # per contact, continuous
    pin: Optional[str] = None               # MCU pin (board ports)
    conductors: int = 2
    at: Optional[tuple] = None              # home-pose world position of the connector on the device's body
    direction: Optional[tuple] = None       # the way the plug pulls out
    group: Optional[str] = None             # ports that share one driver/output
    multi: bool = False                     # more than one wire may land here (stud, bus)
    extra: dict = field(default_factory=dict)


@dataclass
class Device:
    name: str
    kind: str      # board psu inlet relay mosfet heater thermistor thermal_fuse fan stepper endstop host earth_point
    component: Optional[str] = None        # CAD part that represents it
    ports: dict = field(default_factory=dict)
    ratings: dict = field(default_factory=dict)
    sources: dict = field(default_factory=dict)   # rating name -> where the number comes from
    params: dict = field(default_factory=dict)
    # what it physically is: {"product", "vendor", "part_number" (None = commodity part, any vendor), "form":
    # "assembled board" | "module" | "component" | "hardware", "off_the_shelf": bool, "custom_pcb": bool, "builder_work": str}
    product: dict = field(default_factory=dict)

    def port(self, name: str) -> Port:
        return self.ports[name]


@dataclass
class Waypoint:
    body: str
    xyz: tuple
    clamp: Optional[str] = None    # CAD part the loom is tied to here (strain relief)


@dataclass
class Loom:
    """A bundle path through the machine. Consecutive waypoints on different bodies are a flexing span:
    give its cable length in flex_length ({index of the span's first waypoint: mm}, or one number)."""

    name: str
    route: list
    flex_length: object = None
    retention: str = "ties"        # ties | sleeve | chain
    min_bend_radius: Optional[float] = None   # default: requirement x bundle OD

    def spans(self):
        out = []
        for i in range(len(self.route) - 1):
            a, b = self.route[i], self.route[i + 1]
            flex = a.body != b.body
            L = None
            if flex:
                L = self.flex_length.get(i) if isinstance(self.flex_length, dict) else self.flex_length
            out.append((i, a, b, flex, L))
        return out

    def length(self) -> float:
        tot = 0.0
        for _, a, b, flex, L in self.spans():
            tot += L if (flex and L) else float(np.linalg.norm(np.subtract(a.xyz, b.xyz)))
        return tot


@dataclass
class Wire:
    """One cable: `conductors` cores of one gauge from port a to port b ("device.port")."""

    name: str
    a: str
    b: str
    awg: int
    conductors: int = 2
    insulation: str = "pvc"
    via: list = field(default_factory=list)      # loom names, in order from a to b
    length: Optional[float] = None               # mm; default: routed length + terminations, rounded up
    connector_a: Optional[str] = None            # default: the port's connector
    connector_b: Optional[str] = None
    pigtail: Optional[tuple] = None              # (mm, insulation) of the device's own lead at end b
    note: str = ""


@dataclass
class Bay:
    """The space the electronics sit in. Air temperature is estimated from the power dissipated there."""

    devices: list
    enclosed: bool = False
    surface_m2: float = 0.0       # wall area of an enclosure
    vent_area_m2: float = 0.0     # free opening (each of inlet and outlet), or the open sides of a tray
    height_m: float = 0.1         # stack height between inlet and outlet
    fan_m3h: float = 0.0


@dataclass
class Electrical:
    supply_v: float = 24.0
    mains_v: tuple = (115.0, 230.0)       # every mains voltage the machine is meant for (worst case is used)
    devices: dict = field(default_factory=dict)
    wires: list = field(default_factory=list)
    looms: dict = field(default_factory=dict)
    firmware: dict = field(default_factory=dict)
    bay: Optional[Bay] = None
    requirements: dict = field(default_factory=dict)   # overrides of DEFAULT_REQUIREMENTS
    hot_parts: dict = field(default_factory=dict)      # CAD part -> its working temperature (degC)
    notes: list = field(default_factory=list)

    # ---- building
    def add(self, dev: Device) -> Device:
        if dev.name in self.devices:
            raise ValueError(f"duplicate electrical device: {dev.name}")
        self.devices[dev.name] = dev
        return dev

    def wire(self, name, a, b, awg, **kw) -> Wire:
        w = Wire(name, a, b, awg, **kw)
        self.wires.append(w)
        return w

    def loom(self, name, route, **kw) -> Loom:
        lm = Loom(name, [p if isinstance(p, Waypoint) else Waypoint(*p) for p in route], **kw)
        self.looms[name] = lm
        return lm

    def req(self, key):
        return self.requirements.get(key, DEFAULT_REQUIREMENTS[key])

    def port(self, ref: str):
        dn, _, pn = ref.partition(".")
        dev = self.devices.get(dn)
        if dev is None or pn not in dev.ports:
            return None, None
        return dev, dev.ports[pn]

    def wires_at(self, ref: str) -> list:
        return [w for w in self.wires if ref in (w.a, w.b)]

    def other_end(self, w: Wire, ref: str) -> str:
        return w.b if w.a == ref else w.a

    # ---- the hook into the existing cable check: every flexing span becomes a model.Cable
    def sync_cables(self, design) -> None:
        from .model import Cable

        have = {c.name for c in design.cables}
        for lm in self.looms.values():
            for i, a, b, flex, L in lm.spans():
                nm = f"{lm.name} [{a.body}-{b.body}]"
                if flex and nm not in have:
                    design.cables.append(Cable(nm, (a.body, tuple(a.xyz)), (b.body, tuple(b.xyz)), float(L or 0.0),
                                               min_bend_radius=self.loom_bend_radius(lm)))

    # ---- geometry of wires
    def wire_od(self, w: Wire) -> float:
        d = awg_diameter(w.awg) * 1.15 + 2 * INSULATION_WALL_MM.get(w.insulation, 0.4)
        return d if w.conductors == 1 else d * (1.0 + 0.55 * math.sqrt(w.conductors))   # jacketed/twisted cores

    def loom_od(self, lm: Loom) -> float:
        ws = [w for w in self.wires if lm.name in w.via]
        return 1.25 * math.sqrt(sum(self.wire_od(w) ** 2 for w in ws)) if ws else 0.0

    def loom_bend_radius(self, lm: Loom) -> float:
        return lm.min_bend_radius or max(10.0, self.req("min_bend_radius_x_od") * self.loom_od(lm))

    def wire_points(self, w: Wire) -> list:
        """Route as [(body, xyz, flex_length_to_next or None)], from port a to port b through the looms in `via`."""
        da, pa = self.port(w.a)
        db, pb = self.port(w.b)
        pts = []
        if pa is not None and pa.at is not None:
            pts.append((pa.extra.get("body", "world"), tuple(pa.at), None))
        for ln in w.via:
            lm = self.looms.get(ln)
            if lm is None:
                continue
            seq = [(wp.body, tuple(wp.xyz)) for wp in lm.route]
            fl = {i: L for i, _, _, flex, L in lm.spans() if flex}
            n = len(seq)
            rev = False
            if pts and pts[-1][0] == seq[-1][0] and pts[-1][0] != seq[0][0]:
                rev = True       # the previous point rides on the body this loom ends on
            elif pts and pts[-1][0] == seq[0][0] and pts[-1][0] != seq[-1][0]:
                rev = False
            elif pts:            # same frame at both ends: enter at the nearer end
                rev = (np.linalg.norm(np.subtract(pts[-1][1], seq[-1][1])) < np.linalg.norm(np.subtract(pts[-1][1], seq[0][1])))
            order = range(n - 1, -1, -1) if rev else range(n)
            for k, i in enumerate(order):
                nxt = (i - 1) if rev else i      # span index between this point and the next one
                last = k == n - 1
                pts.append((seq[i][0], seq[i][1], None if last else fl.get(nxt)))
        if pb is not None and pb.at is not None:
            pts.append((pb.extra.get("body", "world"), tuple(pb.at), None))
        return pts

    def wire_length(self, w: Wire) -> float:
        if w.length:
            return float(w.length)
        pts = self.wire_points(w)
        tot = 0.0
        for (b0, p0, f0), (b1, p1, _) in zip(pts, pts[1:]):
            tot += f0 if f0 else float(np.linalg.norm(np.subtract(p0, p1)))
        # 8 % routing slack plus 30 mm at each end for the termination and a service loop, rounded up to 10 mm
        return math.ceil((tot * 1.08 + 60.0) / 10.0) * 10.0


# ============================================================ wire physics
def awg_diameter(awg: float) -> float:
    return 0.127 * 92 ** ((36 - awg) / 39.0)


def awg_area_mm2(awg: float) -> float:
    return math.pi * awg_diameter(awg) ** 2 / 4.0


def wire_resistance(awg: float, length_mm: float, temp_c: float = 20.0) -> float:
    """One conductor, ohm."""
    return 1.724e-8 * (1 + 0.00393 * (temp_c - 20.0)) * (length_mm * 1e-3) / (awg_area_mm2(awg) * 1e-6)


def grouping_factor(n: int) -> float:
    xs, ys = zip(*GROUPING)
    return float(np.interp(max(1, n), xs, ys))


def wire_temperature(current_a: float, awg: float, od_mm: float, ambient_c: float, n_loaded: int = 1, h: float = 12.0) -> float:
    """Conductor temperature of a wire in still air; in a bundle the same wire behaves as if it carried I / k."""
    i_eq = current_a / grouping_factor(n_loaded)
    t = ambient_c
    for _ in range(30):
        p = i_eq ** 2 * wire_resistance(awg, 1000.0, t)           # W per metre
        t_new = ambient_c + p / (h * math.pi * od_mm * 1e-3)
        if abs(t_new - t) < 0.01:
            break
        t = min(t_new, 2000.0)
    return t


def wire_ampacity(awg: float, od_mm: float, ambient_c: float, limit_c: float, n_loaded: int = 1, h: float = 12.0) -> float:
    if limit_c <= ambient_c:
        return 0.0
    p = h * math.pi * od_mm * 1e-3 * (limit_c - ambient_c)
    return grouping_factor(n_loaded) * math.sqrt(p / wire_resistance(awg, 1000.0, limit_c))


# ============================================================ thermistor + ADC (Klipper thermistor.py)
class Thermistor:
    def __init__(self, points=None, beta=None, pullup: float = 4700.0, adc_bits: int = 12, name: str = ""):
        self.pullup, self.adc_bits, self.name = pullup, adc_bits, name
        if beta is not None:
            t1, r1 = points[0]
            self.c3, self.c2 = 0.0, 1.0 / beta
            self.c1 = 1.0 / (t1 + KELVIN) - self.c2 * math.log(r1)
        else:
            (t1, r1), (t2, r2), (t3, r3) = points
            i1, i2, i3 = (1.0 / (t + KELVIN) for t in (t1, t2, t3))
            l1, l2, l3 = math.log(r1), math.log(r2), math.log(r3)
            c1, c2, c3 = l1 ** 3, l2 ** 3, l3 ** 3
            i12, i13, l12, l13, c12, c13 = i1 - i2, i1 - i3, l1 - l2, l1 - l3, c1 - c2, c1 - c3
            self.c3 = (i12 - i13 * l12 / l13) / (c12 - c13 * l12 / l13)
            if self.c3 <= 0.0:
                self.c3, self.c2 = 0.0, i13 / l13
                self.c1 = i1 - self.c2 * l1
            else:
                self.c2 = (i12 - self.c3 * c12) / l12
                self.c1 = i1 - self.c2 * l1 - self.c3 * c1

    def resistance(self, temp_c: float) -> float:
        inv_t = 1.0 / (max(temp_c, -270.0) + KELVIN)
        if self.c3:
            y = (self.c1 - inv_t) / (2.0 * self.c3)
            x = math.sqrt((self.c2 / (3.0 * self.c3)) ** 3 + y * y)
            ln_r = (x - y) ** (1.0 / 3.0) - (x + y) ** (1.0 / 3.0)
        else:
            ln_r = (inv_t - self.c1) / self.c2
        return math.exp(ln_r)

    def adc(self, temp_c: float) -> float:
        r = self.resistance(temp_c)
        return r / (self.pullup + r)

    def temp_from_adc(self, adc: float) -> float:
        adc = max(1e-5, min(0.99999, adc))
        ln_r = math.log(self.pullup * adc / (1.0 - adc))
        return 1.0 / (self.c1 + self.c2 * ln_r + self.c3 * ln_r ** 3) - KELVIN

    def quantise(self, adc: float) -> float:
        n = (1 << self.adc_bits) - 1
        return round(max(0.0, min(1.0, adc)) * n) / n

    def read(self, temp_c: float) -> float:
        """Temperature the firmware computes for a sensor really at temp_c (one ADC count of quantisation)."""
        return self.temp_from_adc(self.quantise(self.adc(temp_c)))

    def deg_per_count(self, temp_c: float) -> float:
        n = (1 << self.adc_bits) - 1
        d = (self.adc(temp_c - 0.5) - self.adc(temp_c + 0.5)) * n
        return 1.0 / d if d > 1e-9 else float("inf")


# ============================================================ lumped thermal network
def _air(t_film_k: float):
    """k (W/mK), nu (m^2/s), alpha (m^2/s) of air, power-law fits good to a few % between 280 and 600 K."""
    r = t_film_k / 300.0
    return 0.0263 * r ** 0.81, 1.589e-5 * r ** 1.74, 2.25e-5 * r ** 1.78


def h_natural(kind: str, t_surf_c: float, t_amb_c: float, length_m: float) -> float:
    dt = abs(t_surf_c - t_amb_c)
    if dt < 1e-3 or length_m <= 0:
        return 0.0
    tf = (t_surf_c + t_amb_c) / 2.0 + KELVIN
    k, nu, al = _air(tf)
    ra = 9.81 * dt * length_m ** 3 / (tf * nu * al)
    if kind == "plate_up":
        nu_ = 0.54 * ra ** 0.25 if ra < 1e7 else 0.15 * ra ** (1.0 / 3.0)
    elif kind == "plate_down":
        nu_ = 0.27 * ra ** 0.25
    else:   # vertical plate / compact body: Churchill-Chu, all Ra
        pr = nu / al
        nu_ = (0.825 + 0.387 * ra ** (1.0 / 6.0) / (1 + (0.492 / pr) ** (9.0 / 16.0)) ** (8.0 / 27.0)) ** 2
    return max(nu_, 1.0 if kind == "body" else 0.0) * k / length_m


@dataclass
class Surface:
    area_m2: float
    kind: str = "body"            # plate_up | plate_down | body | fixed
    length_m: float = 0.02        # characteristic length (plates: area / perimeter; bodies: height)
    emissivity: float = 0.0
    h_fixed: float = 0.0          # W/m^2K, used when kind == "fixed" (forced air), or added to the natural value


@dataclass
class ThermalNode:
    name: str
    capacity: float               # J/K
    surfaces: list = field(default_factory=list)
    g_ambient: float = 0.0        # extra fixed conductance to ambient, W/K (e.g. conduction up a heat break)


class ThermalNet:
    """Nodes joined by conductances; each node loses heat to ambient through its surfaces.
    Conduction between nodes is integrated implicitly (it is stiff), ambient exchange explicitly."""

    def __init__(self, nodes, links, ambient_c: float = 25.0):
        self.nodes = list(nodes)
        self.idx = {n.name: i for i, n in enumerate(self.nodes)}
        self.links = [(self.idx[a], self.idx[b], g) for a, b, g in links]
        self.ambient = ambient_c
        self.C = np.array([n.capacity for n in self.nodes], dtype=float)
        n = len(self.nodes)
        self.G = np.zeros((n, n))
        for i, j, g in self.links:
            self.G[i, i] += g
            self.G[j, j] += g
            self.G[i, j] -= g
            self.G[j, i] -= g
        self._inv = {}

    def loss(self, T: np.ndarray) -> np.ndarray:
        """Heat leaving each node to ambient, W. Film coefficients are re-evaluated when a node has moved 1 K."""
        out = np.zeros(len(self.nodes))
        ta = self.ambient
        cache = self.__dict__.setdefault("_hc", {})
        for i, n in enumerate(self.nodes):
            ti = float(T[i])
            q = n.g_ambient * (ti - ta)
            for k, s in enumerate(n.surfaces):
                c = cache.get((i, k))
                if c is None or abs(c[0] - ti) > 1.0:
                    h = s.h_fixed + (0.0 if s.kind == "fixed" else h_natural(s.kind, ti, ta, s.length_m))
                    c = cache[(i, k)] = (ti, h)
                q += c[1] * s.area_m2 * (ti - ta)
                if s.emissivity:
                    q += s.emissivity * SIGMA * s.area_m2 * ((ti + KELVIN) ** 4 - (ta + KELVIN) ** 4)
            out[i] = q
        return out

    def step(self, T: np.ndarray, power: np.ndarray, dt: float) -> np.ndarray:
        if dt not in self._inv:
            self._inv[dt] = np.linalg.inv(np.diag(self.C / dt) + self.G)
        return self._inv[dt] @ (self.C / dt * T + power - self.loss(T))

    def start(self) -> np.ndarray:
        return np.full(len(self.nodes), float(self.ambient))

    def steady(self, power: np.ndarray, t_guess: float = 100.0) -> np.ndarray:
        """Steady-state temperatures for constant node powers (damped fixed-point on the ambient loss)."""
        T = np.full(len(self.nodes), float(t_guess))
        for _ in range(400):
            q = self.loss(T)
            geff = np.where(np.abs(T - self.ambient) > 1e-6, q / (T - self.ambient), 1e-3)
            A = self.G + np.diag(np.maximum(geff, 1e-6))
            Tn = np.linalg.solve(A, power + np.maximum(geff, 1e-6) * self.ambient)
            if np.abs(Tn - T).max() < 1e-3:
                T = Tn
                break
            T = 0.5 * T + 0.5 * Tn
        return T


@dataclass
class HeaterPlant:
    """A heater as the firmware sees it: the thermal network, where the power goes in, where the sensor sits."""

    name: str
    net: ThermalNet
    heater_node: str
    sensor_node: str
    report_node: str              # the temperature that matters (block, plate)
    power_w: float                # at 100 % duty and the delivered voltage
    sensor_tau_s: float = 4.5
    thermistor: Optional[Thermistor] = None
    cutoffs: list = field(default_factory=list)   # [{"kind": "thermal_fuse", "node": n, "trip_c": T} | {"kind": "psu_relay"}]
    basis: dict = field(default_factory=dict)


class _PID:      # Klipper ControlPID
    def __init__(self, kp, ki, kd, max_power=1.0, smooth_time=1.0):
        self.Kp, self.Ki, self.Kd = kp / 255.0, ki / 255.0, kd / 255.0
        self.max_power, self.min_deriv_time = max_power, smooth_time
        self.integ_max = max_power / self.Ki if self.Ki else 0.0
        self.prev_temp, self.prev_time, self.prev_deriv, self.prev_integ = 25.0, 0.0, 0.0, 0.0

    def update(self, t, temp, target):
        td = t - self.prev_time
        diff = temp - self.prev_temp
        deriv = diff / td if td >= self.min_deriv_time else (self.prev_deriv * (self.min_deriv_time - td) + diff) / self.min_deriv_time
        err = target - temp
        integ = max(0.0, min(self.integ_max, self.prev_integ + err * td))
        co = self.Kp * err + self.Ki * integ - self.Kd * deriv
        bounded = max(0.0, min(self.max_power, co))
        self.prev_temp, self.prev_time, self.prev_deriv = temp, t, deriv
        if co == bounded:
            self.prev_integ = integ
        return bounded


class _BangBang:   # Klipper ControlBangBang ("watermark")
    def __init__(self, max_delta=2.0, max_power=1.0):
        self.max_delta, self.max_power, self.heating = max_delta, max_power, False

    def update(self, t, temp, target):
        if self.heating and temp >= target + self.max_delta:
            self.heating = False
        elif not self.heating and temp <= target - self.max_delta:
            self.heating = True
        return self.max_power if self.heating else 0.0


class _VerifyHeater:   # Klipper verify_heater.HeaterCheck.check_event, called once a second
    def __init__(self, hysteresis=5.0, max_error=120.0, heating_gain=2.0, check_gain_time=20.0):
        self.hysteresis, self.max_error, self.heating_gain, self.check_gain_time = hysteresis, max_error, heating_gain, check_gain_time
        self.approaching = self.starting = False
        self.last_target = self.goal_temp = self.error = 0.0
        self.goal_time = float("inf")

    def check(self, t, temp, target) -> bool:
        """True = fault ("not heating at expected rate")."""
        if temp >= target - self.hysteresis or target <= 0.0:
            self.approaching = self.starting = False
            if temp <= target + self.hysteresis:
                self.error = 0.0
            self.last_target = target
            return False
        self.error += (target - self.hysteresis) - temp
        if not self.approaching:
            if target != self.last_target:
                self.approaching = self.starting = True
                self.goal_temp = temp + self.heating_gain
                self.goal_time = t + self.check_gain_time
            elif self.error >= self.max_error:
                return True
        elif temp >= self.goal_temp:
            self.starting = False
            self.error = 0.0
            self.goal_temp = temp + self.heating_gain
            self.goal_time = t + self.check_gain_time
        elif t >= self.goal_time:
            self.approaching = False
        elif self.starting:
            self.goal_temp = min(self.goal_temp, temp + self.heating_gain)
        self.last_target = target
        return False


REPORT_TIME, RANGE_CHECK_COUNT, PWM_CYCLE = 0.3, 4, 0.1     # Klipper adc_temperature.py / heaters.py


def simulate_heater(plant: HeaterPlant, cfg: dict, target: float, t_end: float, fault: Optional[dict] = None,
                    duty_override: Optional[float] = None, t0_state: Optional[np.ndarray] = None,
                    autotune: bool = False, stop_when_settled: bool = False) -> dict:
    """Closed-loop run of one heater under the firmware configuration `cfg`:
    {"control": "pid"|"watermark", "pid": (Kp, Ki, Kd), "max_delta": 2, "min_temp": 0, "max_temp": 285,
     "smooth_time": 1.0, "max_power": 1.0, "verify_heater": {...} | None}
    fault: {"kind": "sensor_detached"|"sensor_short"|"sensor_open"|"mosfet_short", "at": seconds}
    duty_override: open loop at that duty (no firmware). Sampling as Klipper: ADC report every 0.3 s,
    verify_heater every 1 s, PWM averaged over its 0.1 s cycle.
    """
    net = plant.net
    T = net.start() if t0_state is None else t0_state.copy()
    ih, isn, irep = net.idx[plant.heater_node], net.idx[plant.sensor_node], net.idx[plant.report_node]
    th = plant.thermistor
    sensor = float(T[isn])
    dt = PWM_CYCLE
    n = int(round(t_end / dt))
    ctl = None
    if duty_override is None and not autotune:
        if cfg.get("control", "pid") == "pid":
            kp, ki, kd = cfg["pid"]
            ctl = _PID(kp, ki, kd, cfg.get("max_power", 1.0), cfg.get("smooth_time", 1.0))
        else:
            ctl = _BangBang(cfg.get("max_delta", 2.0), cfg.get("max_power", 1.0))
    vh_cfg = cfg.get("verify_heater", {}) if duty_override is None else None
    vh = _VerifyHeater(**vh_cfg) if vh_cfg is not None else None
    smooth, inv_smooth = sensor, 1.0 / cfg.get("smooth_time", 1.0)
    duty, shutdown, shutdown_reason, t_shutdown = 0.0, False, "", None
    out_of_range = 0
    fused, t_fuse, relay_open, t_relay = False, None, False, None
    fkind = (fault or {}).get("kind")
    t_fault = (fault or {}).get("at", 0.0)
    detached_temp = None
    tr_t, tr_T, tr_s, tr_d = [], [], [], []
    peaks, peak, peak_time, heating_at = [], 0.0, 0.0, False     # autotune (Klipper ControlAutoTune)
    tune_target = target
    next_report, next_check = 0.0, 0.0
    settled_since = None
    power = np.zeros(len(net.nodes))
    for k in range(n + 1):
        t = k * dt
        faulted = fault is not None and t >= t_fault
        # ---- sensor (first-order lag behind its node; in free air once it has fallen out)
        if faulted and fkind == "sensor_detached":
            if detached_temp is None:
                detached_temp = sensor
            detached_temp += (net.ambient - detached_temp) * dt / fault.get("tau_s", 15.0)
            sensor = detached_temp
        else:
            sensor += (T[isn] - sensor) * min(1.0, dt / max(plant.sensor_tau_s, dt))
        # ---- firmware
        if duty_override is None and t >= next_report - 1e-9:
            next_report += REPORT_TIME
            if faulted and fkind == "sensor_short":
                adc = 0.0
            elif faulted and fkind == "sensor_open":
                adc = 1.0
            else:
                adc = th.quantise(th.adc(sensor)) if th else None
            temp = th.temp_from_adc(adc) if th else sensor
            if th:    # the MCU's range check: 4 consecutive reports outside [max_temp, min_temp] -> shutdown
                lo, hi = th.adc(cfg.get("max_temp", 300.0)), th.adc(cfg.get("min_temp", 0.0))
                out_of_range = out_of_range + 1 if not (lo <= adc <= hi) else 0
            else:
                out_of_range = out_of_range + 1 if not (cfg.get("min_temp", 0.0) <= temp <= cfg.get("max_temp", 300.0)) else 0
            if out_of_range >= RANGE_CHECK_COUNT and not shutdown:
                shutdown, shutdown_reason, t_shutdown = True, "ADC out of range (min_temp/max_temp)", t
            smooth += (temp - smooth) * min(REPORT_TIME * inv_smooth, 1.0)
            if not shutdown:
                if autotune:
                    if heating_at and temp >= tune_target:
                        heating_at = False
                        peaks.append((peak_time, peak)); peak = -9999999.0
                        tune_target = target - 2.5
                    elif not heating_at and temp <= tune_target:
                        heating_at = True
                        peaks.append((peak_time, peak)); peak = 9999999.0
                        tune_target = target
                    if heating_at:
                        duty = cfg.get("max_power", 1.0)
                        if temp < peak:
                            peak, peak_time = temp, t
                    else:
                        duty = 0.0
                        if temp > peak:
                            peak, peak_time = temp, t
                    if not heating_at and len(peaks) >= 12:
                        break
                else:
                    duty = ctl.update(t, temp, target)
        if duty_override is None and vh is not None and not shutdown and t >= next_check - 1e-9:
            next_check += 1.0
            if vh.check(t, smooth, target):
                shutdown, shutdown_reason, t_shutdown = True, "verify_heater: not heating at expected rate", t
        if duty_override is not None:
            duty = duty_override
        if shutdown:
            duty = 0.0
        # ---- power stage and independent cut-offs
        applied = duty
        if faulted and fkind == "mosfet_short":
            applied = 1.0
        for c in plant.cutoffs:
            if c["kind"] == "thermal_fuse" and not fused and T[net.idx[c["node"]]] >= c["trip_c"]:
                fused, t_fuse = True, t
            if c["kind"] == "psu_relay" and shutdown and not relay_open and t >= t_shutdown + c.get("delay_s", 0.05):
                relay_open, t_relay = True, t
        if fused or relay_open:
            applied = 0.0
        power[:] = 0.0
        power[ih] = applied * plant.power_w
        tr_t.append(t); tr_T.append(float(T[irep])); tr_s.append(float(sensor)); tr_d.append(applied)
        T = net.step(T, power, dt)
        if stop_when_settled and duty_override is None and not autotune:
            if abs(smooth - target) < 0.5:
                settled_since = t if settled_since is None else settled_since
                if t - settled_since > 60.0:
                    break
            else:
                settled_since = None
    res = {"t": np.array(tr_t), "T": np.array(tr_T), "sensor": np.array(tr_s), "duty": np.array(tr_d),
           "state": T, "shutdown": shutdown, "shutdown_reason": shutdown_reason, "t_shutdown": t_shutdown,
           "fuse_opened_at": t_fuse, "relay_opened_at": t_relay, "peaks": peaks}
    return res


def autotune_pid(plant: HeaterPlant, cfg: dict, target: float) -> tuple:
    """Klipper's PID_CALIBRATE (relay test, Astrom-Hagglund) run on the model. Returns (Kp, Ki, Kd)."""
    tau = float(plant.net.C.sum()) / max(1e-6, plant.power_w / max(target - plant.net.ambient, 1.0))
    r = simulate_heater(plant, {**cfg, "verify_heater": None}, target, t_end=max(600.0, 6 * tau), autotune=True)
    pk = r["peaks"]
    if len(pk) < 6:
        raise RuntimeError(f"autotune of {plant.name} did not oscillate ({len(pk)} peaks): target not reachable?")

    def calc(pos):
        amp = 0.5 * abs(pk[pos][1] - pk[pos - 1][1])
        tu = pk[pos][0] - pk[pos - 2][0]
        ku = 4.0 * 0.5 * cfg.get("max_power", 1.0) / (math.pi * max(amp, 1e-6))
        kp = 0.6 * ku * 255.0
        return kp, kp / (0.5 * tu), kp * 0.125 * tu

    cyc = sorted((pk[p][0] - pk[p - 2][0], p) for p in range(4, len(pk)))
    return tuple(round(x, 3) for x in calc(cyc[len(cyc) // 2][1]))


def heater_characteristics(plant: HeaterPlant, targets, t_max: float) -> dict:
    """Open loop at 100 % duty: time to each target and the temperature it would reach if left on."""
    r = simulate_heater(plant, {}, max(targets), t_max, duty_override=1.0)
    out = {"heatup_s": {}}
    for tg in targets:
        i = np.argmax(r["T"] >= tg)
        out["heatup_s"][tg] = float(r["t"][i]) if r["T"][i] >= tg else None
    p = np.zeros(len(plant.net.nodes))
    p[plant.net.idx[plant.heater_node]] = plant.power_w
    Ts = plant.net.steady(p, t_guess=max(targets) + 100.0)
    out["max_temp_c"] = float(Ts[plant.net.idx[plant.report_node]])
    out["duty_at"] = {}
    for tg in targets:      # steady duty = loss at target / heater power (all nodes at about the target)
        loss = float(plant.net.loss(np.full(len(plant.net.nodes), float(tg))).sum())
        out["duty_at"][tg] = loss / plant.power_w if plant.power_w > 0 else float("inf")
    return out


def closed_loop_metrics(r: dict, target: float) -> dict:
    T, t = r["T"], r["t"]
    reached = T >= target - 1.0
    if not reached.any():
        return {"reached": False}
    i0 = int(np.argmax(reached))
    over = float(T[i0:].max() - target)
    band = np.abs(T - target) <= 1.0
    outside = np.where(~band)[0]
    i_settle = int(outside[-1]) + 1 if len(outside) else 0
    settled = i_settle < len(T) - int(20.0 / PWM_CYCLE)
    tail = T[-int(30.0 / PWM_CYCLE):]
    return {"reached": True, "time_to_target_s": float(t[i0]), "overshoot_c": round(over, 2),
            "settled": bool(settled), "settling_time_s": float(t[min(i_settle, len(t) - 1)]) if settled else None,
            "ripple_c": round(float(tail.max() - tail.min()), 3), "steady_error_c": round(float(tail.mean() - target), 3),
            "steady_duty": round(float(r["duty"][-int(30.0 / PWM_CYCLE):].mean()), 3)}


# ============================================================ steppers
def stepper_torque_curve(hold_nm: float, rated_a: float, r_ohm: float, l_h: float, run_rms_a: float, v_bus: float,
                         rpms, pole_pairs: int = 50, driver_r: float = 0.0) -> np.ndarray:
    """Pull-out torque (N*m) of a 2-phase hybrid stepper on a current-chopping driver, per motor.
    Phasor model per phase: v = R i + j w_e L i + e, e = Kt w_m on the q axis; torque = Kt i_q for sinusoidal
    (microstepped) currents of peak i. Maximised over the current vector within |i| <= sqrt(2) I_rms and
    |v| <= V_bus. Holding torque = Kt * sqrt(2) * I_rated (two phases on)."""
    kt = hold_nm / (math.sqrt(2.0) * rated_a)
    ipk = math.sqrt(2.0) * run_rms_a
    mag = np.linspace(0.0, ipk, 60)[None, :, None]
    gam = np.linspace(0.0, math.pi / 2, 91)[None, None, :]      # field-weakening angle
    iq, id_ = mag * np.cos(gam), -mag * np.sin(gam)
    wm = (np.asarray(rpms, dtype=float) * 2 * math.pi / 60.0)[:, None, None]
    we = wm * pole_pairs
    R = r_ohm + driver_r
    vd = R * id_ - we * l_h * iq
    vq = R * iq + we * l_h * id_ + kt * wm
    ok = vd ** 2 + vq ** 2 <= v_bus ** 2
    return (np.where(ok, kt * iq, 0.0)).max(axis=(1, 2))


CURVE_RPM = (0, 60, 120, 200, 300, 400, 500, 600, 750, 900, 1200, 1500, 1800, 2400, 3000)


# ============================================================ circuit
def _series_partner(dev: Device, port_name: str):
    """A pass-through device's other power port."""
    pair = dev.params.get("through") or {}
    return pair.get(port_name)


def trace_supply(el: Electrical, ref: str, limit: int = 12):
    """Follow the wiring from a load port back to the port that sources it (a board output, the supply).
    Returns (wires, series devices, source ref or None)."""
    wires, series, seen = [], [], set()
    cur = ref
    for _ in range(limit):
        ws = [w for w in el.wires_at(cur) if id(w) not in seen]
        if not ws:
            return wires, series, None
        w = ws[0]
        seen.add(id(w))
        wires.append(w)
        other = el.other_end(w, cur)
        dev, port = el.port(other)
        if dev is None:
            return wires, series, None
        nxt = _series_partner(dev, port.name)
        if nxt is None:
            return wires, series, other
        series.append((dev, port.name, nxt))
        cur = f"{dev.name}.{nxt}"
    return wires, series, None


def motor_groups(el: Electrical) -> dict:
    """{driver group: {"board": dev, "ports": [...], "motors": [stepper devices]}} from the wiring."""
    groups = {}
    for w in el.wires:
        for ref_m, ref_b in ((w.a, w.b), (w.b, w.a)):
            dm, pm = el.port(ref_m)
            db, pb = el.port(ref_b)
            if dm is not None and db is not None and pm.kind == "stepper" and pb.kind == "stepper_out":
                g = groups.setdefault((db.name, pb.group or pb.name), {"board": db, "ports": [], "motors": [], "wires": []})
                g["ports"].append(pb)
                g["motors"].append(dm)
                g["wires"].append(w)
    return groups


def solve_circuit(el: Electrical, design=None) -> dict:
    """Worst-case simultaneous currents: every heater at 100 %, every motor at its run current, fans on.
    Returns per-wire current, delivered heater voltages and powers, board and supply totals."""
    V = el.supply_v
    fw = el.firmware or {}
    res = {"wire_current": {}, "heaters": {}, "loads_w": {}, "port_current": {}, "motors": {}}
    amb = el.req("ambient_c")

    def loop_r(w: Wire, temp=40.0):
        return 2.0 * wire_resistance(w.awg, el.wire_length(w), temp)

    # ---- motors
    scur = fw.get("steppers", {})
    drv_supply = 0.0
    for (bname, grp), g in motor_groups(el).items():
        n = len(g["motors"])
        conn = g["motors"][0].params.get("connection", "parallel") if n > 1 else "single"
        key = next((k for k, v in scur.items() if set(v.get("motors", [])) & {m.name for m in g["motors"]}), None)
        run = float(scur.get(key, {}).get("run_current", 0.0)) if key else 0.0
        per_motor = run / n if conn == "parallel" else run
        p_tot = 0.0
        for m, w in zip(g["motors"], g["wires"]):
            rr = m.ratings.get("phase_resistance_ohm", 0.0) * (1 + 0.00393 * 40.0)     # warm winding
            p_m = 2.0 * per_motor ** 2 * rr
            p_tot += p_m
            res["wire_current"][w.name] = per_motor
            res["motors"][m.name] = {"driver": f"{bname}.{grp}", "axis": key, "connection": conn, "driver_run_current_a": run,
                                     "motor_current_a": round(per_motor, 3), "copper_loss_w": round(p_m, 2)}
        rds = g["board"].ratings.get("driver_rds_on_ohm", 0.0)
        p_drv = 2.0 * run ** 2 * 2.0 * rds        # two bridges, two switches conducting in each
        res["loads_w"][f"driver {grp}"] = round(p_tot + p_drv, 2)
        res["motors"][f"_driver:{bname}.{grp}"] = {"loss_w": round(p_drv, 2), "run_current_a": run}
        drv_supply += (p_tot + p_drv) / V
    # ---- fans
    fan_i = {}
    for d in el.devices.values():
        if d.kind == "fan":
            i = float(d.ratings.get("current_a", 0.0))
            fan_i[d.name] = i
            for w in el.wires_at(f"{d.name}.in"):
                res["wire_current"][w.name] = i
            res["loads_w"][d.name] = round(i * V, 2)
    # ---- board logic, host
    logic = {}
    for d in el.devices.values():
        if d.kind == "board":
            logic[d.name] = float(d.ratings.get("logic_w", 1.5))
            res["loads_w"][f"{d.name} logic"] = logic[d.name]
        if d.kind in ("host", "relay", "mosfet") and d.ratings.get("supply_w"):
            res["loads_w"][d.name] = float(d.ratings["supply_w"])
    aux_i = sum(v for k, v in res["loads_w"].items() if not k.startswith("driver ") and k not in fan_i) / V
    # ---- heaters: iterate the delivered voltage (the feed wire carries everything)
    heaters = [d for d in el.devices.values() if d.kind == "heater"]
    paths = {h.name: trace_supply(el, f"{h.name}.in") for h in heaters}
    i_h = {h.name: h.ratings["watts"] / h.ratings["volts"] for h in heaters}
    feed = {}       # source device -> (wires from the supply, source ref)
    for _ in range(6):
        board_i = {}
        for h in heaters:
            wires, series, src = paths[h.name]
            sdev = el.port(src)[0] if src else None
            # a heater switched by an external module draws from the module's own feed, not through the board
            for dev, pin_, pout in series:
                if dev.kind in ("mosfet", "relay") and dev.params.get("feed"):
                    sdev = dev
            if sdev is not None:
                board_i[sdev.name] = board_i.get(sdev.name, 0.0) + i_h[h.name]
        for b in el.devices.values():
            if b.kind == "board":
                board_i[b.name] = board_i.get(b.name, 0.0) + drv_supply + sum(fan_i.values()) + aux_i
        for h in heaters:
            wires, series, src = paths[h.name]
            rh = h.ratings["volts"] ** 2 / h.ratings["watts"]
            r_path, v_feed_drop, sdev = 0.0, 0.0, (el.port(src)[0] if src else None)
            switched = None
            for dev, pin_, pout in series:
                r_path += float(dev.ratings.get("resistance_ohm", 0.0))
                if dev.kind in ("mosfet", "relay") and dev.params.get("feed"):
                    switched = dev
            if switched is not None:
                # only the wires on the load side of the module carry heater current; its control wire does not
                load_wires, feed_ref = [], f"{switched.name}.{switched.params['feed']}"
                for w in wires:
                    load_wires.append(w)
                    if switched.name in (w.a.split('.')[0], w.b.split('.')[0]):
                        break
                fw_, _, fsrc = trace_supply(el, feed_ref)
                r_path += sum(loop_r(w) for w in load_wires) + sum(loop_r(w) for w in fw_)
                feed[h.name] = {"load_wires": load_wires, "feed_wires": fw_, "control_wires": [w for w in wires if w not in load_wires],
                                "source": fsrc, "module": switched.name}
            else:
                r_path += sum(loop_r(w) for w in wires)
                if sdev is not None and sdev.kind == "board":
                    r_path += float(sdev.ratings.get("output_resistance_ohm", 0.0))
                    fw_, _, fsrc = trace_supply(el, f"{sdev.name}.{sdev.params.get('power_port', 'POWER')}")
                    v_feed_drop = board_i.get(sdev.name, 0.0) * sum(loop_r(w) for w in fw_)
                    feed[h.name] = {"load_wires": wires, "feed_wires": fw_, "control_wires": [], "source": fsrc, "module": None,
                                    "board": sdev.name}
                else:
                    feed[h.name] = {"load_wires": wires, "feed_wires": [], "control_wires": [], "source": src, "module": None}
            i = (V - v_feed_drop) / (rh + r_path)
            i_h[h.name] = i
            res["heaters"][h.name] = {"current_a": round(i, 3), "volts_at_heater": round(i * rh, 3),
                                      "power_w": round(i * i * rh, 2), "rated_w": h.ratings["watts"],
                                      "drop_frac": round(1.0 - i * rh / V, 4), "resistance_ohm": round(rh, 3)}
    for h in heaters:
        f = feed.get(h.name, {})
        for w in f.get("load_wires", []):
            res["wire_current"][w.name] = i_h[h.name]
        for w in f.get("control_wires", []):
            res["wire_current"][w.name] = 0.02
        if f.get("module"):
            for w in f.get("feed_wires", []):
                res["wire_current"][w.name] = res["wire_current"].get(w.name, 0.0) + i_h[h.name]
        res["loads_w"][h.name] = res["heaters"][h.name]["power_w"]
    res["heater_feed"] = feed
    # ---- board feed wires and totals
    res["board_current"] = {}
    for b in el.devices.values():
        if b.kind != "board":
            continue
        ib = board_i.get(b.name, drv_supply + sum(fan_i.values()) + aux_i) if heaters else drv_supply + sum(fan_i.values()) + aux_i
        res["board_current"][b.name] = round(ib, 3)
        fw_, _, _ = trace_supply(el, f"{b.name}.{b.params.get('power_port', 'POWER')}")
        for w in fw_:
            res["wire_current"][w.name] = ib
    # low-current signal wires
    for w in el.wires:
        if w.name not in res["wire_current"]:
            da, pa = el.port(w.a)
            db, pb = el.port(w.b)
            kinds = {p.kind for p in (pa, pb) if p is not None}
            res["wire_current"][w.name] = 0.001 if kinds & LOW_CURRENT else (0.5 if "host" in kinds else 0.0)
    wire_loss = sum(res["wire_current"][w.name] ** 2 * loop_r(w) for w in el.wires
                    if not ({(el.port(w.a)[1] or Port("", "")).kind, (el.port(w.b)[1] or Port("", "")).kind} & {"mains_in", "mains_out", "pe"}))
    res["wire_loss_w"] = round(wire_loss, 2)
    res["dc_load_w"] = round(sum(res["loads_w"].values()) + wire_loss, 1)
    # ---- mains side
    psu = next((d for d in el.devices.values() if d.kind == "psu"), None)
    if psu is not None:
        frac = res["dc_load_w"] / psu.ratings["watts"]
        res["psu"] = {"name": psu.name, "rated_w": psu.ratings["watts"], "load_frac": round(frac, 3),
                      "loss_w": round(res["dc_load_w"] * (1.0 / psu.ratings.get("efficiency", 0.88) - 1.0), 1)}
        mains = {}
        for vm in el.mains_v:
            i_full = psu.ratings.get("ac_current_a", {}).get(int(vm))
            if i_full is None:   # no data sheet figure: real power / (V * assumed power factor 0.55, no PFC)
                i_full = psu.ratings["watts"] / psu.ratings.get("efficiency", 0.88) / (vm * 0.55)
            mains[int(vm)] = round(i_full * min(1.0, frac), 2)
        res["mains_current_a"] = mains
        im = max(mains.values()) if mains else 0.0
        for w in el.wires:
            kinds = {(el.port(w.a)[1] or Port("", "")).kind, (el.port(w.b)[1] or Port("", "")).kind}
            if kinds & {"mains_in", "mains_out"}:
                res["wire_current"][w.name] = im
            elif "pe" in kinds:
                res["wire_current"][w.name] = 0.0
    return res


# ============================================================ coupling to the mechanical model
def axis_motors(el: Electrical, design) -> dict:
    """Fill firmware["steppers"][axis]["motors"] (device names) from the joints' drives. The extruder entry
    names its device itself."""
    st = el.firmware.setdefault("steppers", {})
    by_comp = {d.component: d.name for d in el.devices.values() if d.kind == "stepper" and d.component}
    for j in design.joints:
        drv = getattr(j, "drive", None)
        if not drv:
            continue
        ms = [drv["motor"]] if isinstance(drv["motor"], str) else list(drv["motor"])
        e = st.setdefault(j.name, {})
        e.setdefault("joint", j.name)
        e["motors"] = [by_comp[m] for m in ms if m in by_comp]
        e["unwired_components"] = [m for m in ms if m not in by_comp]
    return st


def motor_curves(el: Electrical, design) -> dict:
    """Electrical torque-speed curve of every wired stepper at its configured current and the bus voltage.
    {device: {"rpm": [...], "torque_nmm": [...], "frac_of_holding": [...], ...}}"""
    axis_motors(el, design)
    comps = {c.name: c for c in design.components}
    out = {}
    scur = el.firmware.get("steppers", {})
    for (bname, grp), g in motor_groups(el).items():
        n = len(g["motors"])
        conn = g["motors"][0].params.get("connection", "parallel") if n > 1 else "single"
        key = next((k for k, v in scur.items() if set(v.get("motors", [])) & {m.name for m in g["motors"]}), None)
        run = float(scur.get(key, {}).get("run_current", 0.0)) if key else 0.0
        board = g["board"]
        v_bus = el.supply_v - 2.0 * board.ratings.get("driver_rds_on_ohm", 0.0) * math.sqrt(2.0) * run
        for m in g["motors"]:
            c = comps.get(m.component)
            hold = (c.ratings.get("holding_torque_nmm") if c else None) or m.ratings.get("holding_torque_nmm")
            need = ("rated_current_a", "phase_resistance_ohm", "phase_inductance_mh")
            if hold is None or any(k not in m.ratings for k in need) or run <= 0:
                continue
            i_m = run / n if conn == "parallel" else run
            v_m = v_bus / n if conn == "series" else v_bus
            t = stepper_torque_curve(hold * 1e-3, m.ratings["rated_current_a"], m.ratings["phase_resistance_ohm"],
                                     m.ratings["phase_inductance_mh"] * 1e-3, i_m, v_m, CURVE_RPM) * 1e3
            out[m.name] = {"component": m.component, "axis": key, "driver": f"{bname}.{grp}", "connection": conn,
                           "motor_current_a": round(i_m, 3), "bus_v": round(v_m, 2), "holding_torque_nmm": hold,
                           "rpm": list(CURVE_RPM), "torque_nmm": [round(float(x), 1) for x in t],
                           "frac_of_holding": [round(float(x) / hold, 4) for x in t]}
    return out


def apply_motor_curves(design) -> dict:
    """Replace each wired motor's class torque curve with the one its winding, driver current and supply voltage
    give, so the ratings verifier, the motion verifier and the digital twin all use one answer. Idempotent."""
    el = getattr(design, "electrical", None)
    if el is None:
        return {}
    curves = motor_curves(el, design)
    comps = {c.name: c for c in design.components}
    for name, cv in curves.items():
        c = comps.get(cv["component"])
        if c is None:
            continue
        if "torque_curve_class" not in c.ratings:
            c.ratings["torque_curve_class"] = c.ratings.get("torque_curve_rpm_frac")
        c.ratings["torque_curve_rpm_frac"] = list(zip(cv["rpm"], cv["frac_of_holding"]))
        c.ratings["torque_curve_source"] = (f"electrical model: {cv['motor_current_a']} A rms per motor on {cv['bus_v']} V "
                                            f"({cv['connection']})")
    return curves


# ============================================================ heater plants from the design
def build_plants(el: Electrical, design, circuit: dict) -> dict:
    """One HeaterPlant per firmware heater, from the heater device's parameters, the CAD and the delivered power."""
    comps = {c.name: c for c in design.components} if design is not None else {}
    amb = el.req("ambient_c")
    plants = {}
    for hname, hc in (el.firmware.get("heaters") or {}).items():
        hd = el.devices.get(hc.get("heater"))
        sd = el.devices.get(hc.get("sensor"))
        if hd is None:
            continue
        p = hd.params
        power = circuit["heaters"].get(hd.name, {}).get("power_w", hd.ratings["watts"])
        basis = {"heater_power_w": power}
        cut = []
        wires, series, src = trace_supply(el, f"{hd.name}.in")
        for dev, _, _ in series:
            if dev.kind == "thermal_fuse":
                cut.append({"kind": "thermal_fuse", "node": dev.params.get("node", "plate"), "trip_c": dev.ratings["trip_c"],
                            "device": dev.name})
        if any(d.kind == "relay" and d.params.get("cuts") == "psu" and el.wires_at(f"{d.name}.ctrl") for d in el.devices.values()):
            cut.append({"kind": "psu_relay", "delay_s": 0.05})
        if p.get("model") == "plate":
            plate = comps.get(p["plate"])
            bb = plate.shape.bounding_box()
            dims = sorted([bb.size.X, bb.size.Y, bb.size.Z])
            area = dims[1] * dims[2] * 1e-6
            from .model import MATERIALS

            vol = plate.shape.volume * 1e-9
            mass = vol * MATERIALS[plate.material].density      # the plate's own mass (payload overrides excluded)
            cp = p.get("plate_cp", 896.0)
            c_plate = mass * cp + p.get("extra_capacity", 0.0)
            pad = comps.get(hd.component)
            a_pad = min(area, (pad.shape.bounding_box().size.X * pad.shape.bounding_box().size.Y * 1e-6) if pad else area)
            c_pad = p.get("pad_capacity", (pad.mass() if pad else 0.06) * 1100.0)
            g_bond = p.get("bond_w_m2k", 1000.0) * a_pad
            L = area / (2 * (dims[1] + dims[2]) * 1e-3)
            nodes = [ThermalNode("pad", c_pad, [Surface(a_pad, "plate_down", L, p.get("emissivity_bottom", 0.9))]),
                     ThermalNode("plate", c_plate, [Surface(area, "plate_up", L, p.get("emissivity_top", 0.9)),
                                                    Surface(max(area - a_pad, 0.0), "plate_down", L, p.get("emissivity_plate", 0.1)),
                                                    Surface(2 * (dims[1] + dims[2]) * dims[0] * 1e-6, "body", dims[0] * 1e-3,
                                                            p.get("emissivity_plate", 0.1))],
                                 g_ambient=p.get("mount_w_k", 0.0))]
            net = ThermalNet(nodes, [("pad", "plate", g_bond)], amb)
            basis.update({"plate_mass_kg": round(mass, 3), "plate_area_m2": round(area, 4), "plate_capacity_j_k": round(c_plate, 1),
                          "pad_area_m2": round(a_pad, 4), "bond_w_k": round(g_bond, 1)})
            sens_node = (sd.params.get("node") if sd else None) or "pad"
            plants[hname] = HeaterPlant(hname, net, "pad", sens_node, "plate", power,
                                        sensor_tau_s=(sd.params.get("tau_s", 10.0) if sd else 10.0), cutoffs=cut, basis=basis)
        else:   # "block": a heater cartridge in a hot block
            c_block = p.get("block_capacity_j_k", 12.0)
            c_cart = p.get("cartridge_capacity_j_k", 1.5)
            a_blk = p.get("block_area_m2", 1.6e-3)
            nodes = [ThermalNode("cartridge", c_cart),
                     ThermalNode("block", c_block, [Surface(a_blk, "body", p.get("block_height_m", 0.0115), p.get("emissivity", 0.3),
                                                            h_fixed=p.get("h_forced", 0.0))],
                                 g_ambient=p.get("heatbreak_w_k", 0.02))]
            net = ThermalNet(nodes, [("cartridge", "block", p.get("cartridge_contact_w_k", 2.0))], amb)
            basis.update({"block_capacity_j_k": c_block, "block_area_m2": a_blk, "heatbreak_w_k": p.get("heatbreak_w_k", 0.02)})
            plants[hname] = HeaterPlant(hname, net, "cartridge", "block", "block", power,
                                        sensor_tau_s=(sd.params.get("tau_s", 4.5) if sd else 4.5), cutoffs=cut, basis=basis)
        if sd is not None and sd.params.get("points"):
            board_in = next((el.port(el.other_end(w, f"{sd.name}.out"))[1] for w in el.wires_at(f"{sd.name}.out")), None)
            pull = (board_in.extra.get("pullup_ohm") if board_in else None) or 4700.0
            bits = (board_in.extra.get("adc_bits") if board_in else None) or 12
            plants[hname].thermistor = Thermistor(sd.params["points"], sd.params.get("beta"), pull, bits, sd.params.get("sensor_type", ""))
    return plants


# ============================================================ artefacts
def wiring_rows(el: Electrical, circuit: dict) -> list:
    rows = []
    for w in el.wires:
        da, pa = el.port(w.a)
        db, pb = el.port(w.b)
        L = el.wire_length(w)
        i = circuit["wire_current"].get(w.name, 0.0)
        rows.append({"wire": w.name, "from": w.a, "to": w.b, "awg": w.awg, "mm2": round(awg_area_mm2(w.awg), 3),
                     "conductors": w.conductors, "insulation": w.insulation, "length_mm": L,
                     "connector_from": w.connector_a or (pa.connector if pa else ""), "connector_to": w.connector_b or (pb.connector if pb else ""),
                     "current_a": round(i, 3), "via": "; ".join(w.via), "note": w.note})
    return rows


def wiring_table_md(rows: list) -> str:
    cols = ["wire", "from", "to", "awg", "conductors", "insulation", "length_mm", "connector_from", "connector_to", "current_a", "via", "note"]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(out) + "\n"


def wiring_table_csv(rows: list) -> str:
    import csv
    import io

    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else ["wire"])
    wr.writeheader()
    for r in rows:
        wr.writerow(r)
    return buf.getvalue()


def pin_map(el: Electrical) -> list:
    rows = []
    for d in el.devices.values():
        if d.kind != "board":
            continue
        for p in d.ports.values():
            ws = el.wires_at(f"{d.name}.{p.name}")
            pins = p.pin if isinstance(p.pin, str) else (", ".join(f"{k}={v}" for k, v in p.pin.items()) if p.pin else "")
            rows.append({"board": d.name, "port": p.name, "kind": p.kind, "pins": pins,
                         "connected_to": ", ".join(el.other_end(w, f"{d.name}.{p.name}") for w in ws) or "-"})
    return rows


def _board_port_of(el: Electrical, dev_name: str, port: str = None):
    """The board port a device ends up on (following series devices), or None."""
    d = el.devices.get(dev_name)
    if d is None:
        return None
    for pn in ([port] if port else list(d.ports)):
        wires, series, src = trace_supply(el, f"{dev_name}.{pn}")
        if src:
            sd, sp = el.port(src)
            if sd.kind == "board":
                return sp
    return None


def klipper_config(el: Electrical, design, sim: dict | None = None) -> str:
    """printer.cfg from the pin map, the design's transmissions and joints, and the heater simulation."""
    from .verifiers.ratings import resolve_drives

    resolve_drives(design)
    fw = el.firmware
    axis_motors(el, design)
    joints = {j.name: j for j in design.joints}
    pr = design.printer or {}
    L = [f"# printer.cfg for {design.name}: GENERATED by mechloop from the electrical model. Do not edit by hand;",
         "# change the design and regenerate. Directions (dir_pin '!') and the extruder rotation_distance must be",
         "# confirmed on the machine; PID values come from a simulated PID_CALIBRATE and should be re-run on the real heater.", ""]
    board = next((d for d in el.devices.values() if d.kind == "board"), None)
    host = next((d for d in el.devices.values() if d.kind == "host"), None)
    L += ["[mcu]", f"serial: {fw.get('serial', '/dev/ttyAMA0' if host else '/dev/serial/by-id/usb-Klipper')}", "restart_method: command", ""]
    vmax = min((joints[pr[a]].max_speed for a in "xy" if pr.get(a) in joints), default=200.0)
    amax = min((joints[pr[a]].max_accel for a in "xy" if pr.get(a) in joints), default=1000.0)
    zj = joints.get(pr.get("z", "z"))
    L += ["[printer]", "kinematics: cartesian", f"max_velocity: {vmax:g}", f"max_accel: {amax:g}"]
    if zj is not None:
        L += [f"max_z_velocity: {zj.max_speed:g}", f"max_z_accel: {zj.max_accel:g}"]
    L += [""]
    ends = {e["joint"]: e for e in design.endstops}
    sw_dev = {d.component: d for d in el.devices.values() if d.kind == "endstop"}
    for ax in ("x", "y", "z"):
        jn = pr.get(ax, ax)
        j = joints.get(jn)
        st = fw.get("steppers", {}).get(jn)
        if j is None or not st or not st.get("motors"):
            continue
        port = _board_port_of(el, st["motors"][0])
        if port is None:
            continue
        pins = port.pin
        dr = getattr(j, "drive_resolved", {}) or {}
        lo, hi = j.range
        e = ends.get(jn, {})
        L += [f"[stepper_{ax}]", f"step_pin: {pins['step']}", f"dir_pin: {pins['dir']}", f"enable_pin: !{pins['enable']}",
              f"microsteps: {st.get('microsteps', 16)}", f"rotation_distance: {dr.get('travel_per_rev', 40):g}"]
        if e.get("sensorless"):
            L += [f"endstop_pin: tmc2209_stepper_{ax}:virtual_endstop"]
        else:
            ep = _board_port_of(el, sw_dev[e["switch"]].name) if e.get("switch") in sw_dev else None
            L += [f"endstop_pin: ^{ep.pin}" if ep else "# endstop_pin: NOT WIRED"]
        if ax == "z":   # the bed moves; firmware Z is the nozzle's height above it
            gap = None
            if design.tool_point and pr.get("bed"):
                bb = design.get(pr["bed"]).shape.bounding_box()
                gap = design.tool_point[1][2] - bb.max.Z
            at_max = e.get("at", "min") == "max"
            z_end = (gap - hi) if (gap is not None and at_max) else 0.0
            L += [f"position_endstop: {z_end:.3f}", f"position_min: {min(0.0, z_end) - 0.5:.3f}",
                  f"position_max: {(gap - lo) if gap is not None else hi - lo:.3f}", "homing_speed: 5", "second_homing_speed: 1"]
        else:
            at_max = e.get("at", "min") == "max"
            L += [f"position_endstop: {(hi - lo) if at_max else 0:g}", "position_min: 0", f"position_max: {hi - lo:g}",
                  f"homing_speed: {min(50.0, j.max_speed or 50.0):g}"]
            if at_max:
                L += ["homing_positive_dir: true"]
        L += ["", f"[tmc2209 stepper_{ax}]", f"uart_pin: {pins['uart']}", f"tx_pin: {pins['tx']}", f"uart_address: {pins['uart_address']}",
              f"run_current: {st['run_current']:.3f}", f"sense_resistor: {board.ratings.get('sense_resistor_ohm', 0.11):.3f}",
              "stealthchop_threshold: 0", ""]
    ex = fw.get("steppers", {}).get("extruder")
    hx = (fw.get("heaters") or {}).get("extruder")
    if ex and hx:
        port = _board_port_of(el, ex["motors"][0])
        hp = _board_port_of(el, hx["heater"], "in")
        sp = _board_port_of(el, hx["sensor"], "out")
        sd = el.devices.get(hx["sensor"])
        L += ["[extruder]"]
        if port is not None:
            pins = port.pin
            L += [f"step_pin: {pins['step']}", f"dir_pin: {pins['dir']}", f"enable_pin: !{pins['enable']}",
                  f"microsteps: {ex.get('microsteps', 16)}", f"rotation_distance: {ex.get('rotation_distance', 7.71):g}"]
        L += [f"nozzle_diameter: {pr.get('nozzle', 0.4):.3f}", "filament_diameter: 1.750",
              f"heater_pin: {hp.pin if hp else 'NOT WIRED'}", f"sensor_type: {sd.params.get('sensor_type', 'Generic 3950') if sd else '?'}",
              f"sensor_pin: {sp.pin if sp else 'NOT WIRED'}"]
        L += _heater_lines(hx, (sim or {}).get("extruder"))
        L += [""]
        if port is not None:
            L += ["[tmc2209 extruder]", f"uart_pin: {pins['uart']}", f"tx_pin: {pins['tx']}", f"uart_address: {pins['uart_address']}",
                  f"run_current: {ex['run_current']:.3f}", f"sense_resistor: {board.ratings.get('sense_resistor_ohm', 0.11):.3f}", ""]
    hb = (fw.get("heaters") or {}).get("heater_bed")
    if hb:
        hp = _board_port_of(el, hb["heater"], "in")
        sp = _board_port_of(el, hb["sensor"], "out")
        sd = el.devices.get(hb["sensor"])
        L += ["[heater_bed]", f"heater_pin: {hp.pin if hp else 'NOT WIRED'}",
              f"sensor_type: {sd.params.get('sensor_type', 'Generic 3950') if sd else '?'}", f"sensor_pin: {sp.pin if sp else 'NOT WIRED'}"]
        L += _heater_lines(hb, (sim or {}).get("heater_bed"))
        L += [""]
    for hname, hc in (fw.get("heaters") or {}).items():
        vh = hc.get("verify_heater", {})
        if vh is None:
            L += [f"# [verify_heater {hname}] DISABLED in the design: thermal runaway protection is off", ""]
            continue
        d = {"max_error": 120.0, "check_gain_time": 60.0 if hname == "heater_bed" else 20.0, "hysteresis": 5.0, "heating_gain": 2.0, **vh}
        L += [f"[verify_heater {hname}]"] + [f"{k}: {v:g}" for k, v in d.items()] + [""]
    for fname, fc in (fw.get("fans") or {}).items():
        fp = _board_port_of(el, fc["device"], "in")
        if fc.get("role") == "part":
            L += ["[fan]", f"pin: {fp.pin if fp else 'NOT WIRED'}", ""]
        elif fc.get("role") == "heatsink":
            L += [f"[heater_fan {fname}]", f"pin: {fp.pin if fp else 'NOT WIRED'}", "heater: extruder", "heater_temp: 50.0", ""]
        else:
            L += [f"[controller_fan {fname}]", f"pin: {fp.pin if fp else 'NOT WIRED'}", ""]
    for d in el.devices.values():
        if d.kind == "relay" and d.params.get("cuts") == "psu":
            bp = _board_port_of(el, d.name, "ctrl")
            L += ["# mains relay ahead of the 24 V supply: energised while the firmware runs, dropped on any shutdown",
                  "[output_pin ps_on]", f"pin: {bp.pin if bp else 'NOT WIRED'}", "value: 1", "shutdown_value: 0", ""]
    return "\n".join(L)


def _heater_lines(hc: dict, sim: dict | None) -> list:
    out = []
    if hc.get("control", "pid") == "pid":
        kp, ki, kd = (sim or {}).get("pid") or hc.get("pid") or (0, 0, 0)
        out += ["control: pid", f"pid_Kp: {kp:.3f}", f"pid_Ki: {ki:.3f}", f"pid_Kd: {kd:.3f}"]
    else:
        out += ["control: watermark", f"max_delta: {hc.get('max_delta', 2.0):g}"]
    out += [f"min_temp: {hc.get('min_temp', 0):g}", f"max_temp: {hc.get('max_temp', 250):g}"]
    if hc.get("max_power", 1.0) != 1.0:
        out += [f"max_power: {hc['max_power']:g}"]
    return out


KLIPPER_REQUIRED = {   # section prefix -> options klippy refuses to start without
    "stepper_": ["step_pin", "dir_pin", "enable_pin", "microsteps", "rotation_distance", "endstop_pin", "position_max"],
    "extruder": ["step_pin", "dir_pin", "enable_pin", "microsteps", "rotation_distance", "nozzle_diameter", "filament_diameter",
                 "heater_pin", "sensor_type", "sensor_pin", "control", "min_temp", "max_temp"],
    "heater_bed": ["heater_pin", "sensor_type", "sensor_pin", "control", "min_temp", "max_temp"],
    "tmc2209": ["uart_pin", "run_current"], "printer": ["kinematics", "max_velocity", "max_accel"], "mcu": ["serial"],
    "fan": ["pin"], "heater_fan": ["pin"], "controller_fan": ["pin"], "output_pin": ["pin"], "verify_heater": [],
}


def check_klipper_config(text: str, board_pins: set, sensor_types: set) -> list:
    """Offline sanity check (NOT klippy): parse with the same configparser settings Klipper uses, then check
    required options, that every pin exists on the board, and that no pin is claimed twice (shared UART pins
    excepted, as Klipper allows). Returns a list of problems."""
    import configparser
    import re

    cp = configparser.RawConfigParser(strict=False, inline_comment_prefixes=(";", "#"))
    problems = []
    try:
        cp.read_string(text)
    except configparser.Error as e:
        return [f"does not parse: {e}"]
    used = {}
    for sec in cp.sections():
        key = next((k for k in KLIPPER_REQUIRED if sec == k or sec.startswith(k + " ") or (k.endswith("_") and sec.startswith(k))), None)
        if key is None:
            problems.append(f"[{sec}]: section not known to this checker")
            continue
        for opt in KLIPPER_REQUIRED[key]:
            if not cp.has_option(sec, opt):
                problems.append(f"[{sec}]: missing {opt}")
        if cp.has_option(sec, "control") and cp.get(sec, "control") == "pid":
            for opt in ("pid_kp", "pid_ki", "pid_kd"):
                if not cp.has_option(sec, opt):
                    problems.append(f"[{sec}]: control pid without {opt}")
        if cp.has_option(sec, "sensor_type") and cp.get(sec, "sensor_type") not in sensor_types:
            problems.append(f"[{sec}]: sensor_type '{cp.get(sec, 'sensor_type')}' is not a Klipper built-in")
        for opt, val in cp.items(sec):
            if not opt.endswith("_pin") and opt != "pin":
                continue
            if "virtual_endstop" in val:
                continue
            pin = re.sub(r"^[\^~!]+", "", val.strip())
            if "NOT WIRED" in val or pin not in board_pins:
                problems.append(f"[{sec}] {opt}: '{val}' is not a pin of the board")
                continue
            if opt in ("uart_pin", "tx_pin"):
                continue
            if pin in used:
                problems.append(f"[{sec}] {opt}: pin {pin} already used by [{used[pin]}]")
            used[pin] = sec
    return problems
