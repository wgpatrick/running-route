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
    "klipper": "heater control: Klipper's own heaters.py / verify_heater.py / pid_calibrate.py classes are called when its source is "
               "installed (see heaters.<name>.control_code in the metrics); otherwise control laws ported from them. Also ported: "
               "thermistor.py, adc_temperature.py, tmc2208.py (github.com/Klipper3d/klipper, master, fetched 2026-11-14)",
    "convection": "natural convection: horizontal plate, hot side up Nu = 0.54 Ra^1/4 (Ra < 1e7) or 0.15 Ra^1/3; hot side "
                  "down Nu = 0.27 Ra^1/4; vertical/compact body Churchill-Chu (Incropera, Fundamentals of Heat and Mass "
                  "Transfer, ch. 9). Air properties from power-law fits around 300-400 K.",
    "enclosure_u": "sealed enclosure wall transmittance 5.5 W/m^2K (painted sheet steel, common enclosure-sizing rule): "
                   "typical, unverified",
    "motor_h": "stepper case to still air 12 W/m^2K over the motor's own surface, mounting plate ignored: ASSUMED "
               "(typical, unverified; it gives about the vendor's 80 K rise at rated current)",
    "stepper_model": "pull-out torque from the phasor model (V, R, L, back-EMF). Checked against StepperOnline's published "
                     "24 V pull-out curve for the 17HS13-0404S at 0.35 A rms: within 13 % from 120 to 900 rpm "
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
    "fan_out": {"fan"}, "fan": {"fan_out", "rail_5v"},
    "rail_5v": {"fan"},        # the board's always-on +5 V pins (add_board_5v_port): a 5 V fan may run from them
    "thermistor_in": {"thermistor"}, "thermistor": {"thermistor_in"},
    "endstop_in": {"endstop", "probe"}, "endstop": {"endstop_in"},
    "probe": {"endstop_in", "probe_in"}, "probe_in": {"probe"},
    "mains_out": {"mains_in", "series"}, "mains_in": {"mains_out", "series"},
    "pe": {"pe"},
    "signal_out": {"signal_in"}, "signal_in": {"signal_out"},
    "host": {"host"},
}
LOW_CURRENT = {"thermistor", "thermistor_in", "endstop", "endstop_in", "probe", "probe_in", "signal_out", "signal_in"}

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
    "steady_error_max_c": {"hotend": 2.0, "bed": 5.0},   # surface vs set point (the sensor is not at the surface)
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
    kind: str      # board psu inlet relay mosfet heater thermistor thermal_fuse fan stepper endstop probe host earth_point
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
    g_fan: float = 0.0            # further conductance to ambient with the part fan at full speed, W/K (ThermalNet.fan scales it)
    fan_law: tuple = (0.0, 1.0)   # (threshold, exponent): g_fan * (max(0, fan - threshold) / (1 - threshold)) ** exponent


class ThermalNet:
    """Nodes joined by conductances; each node loses heat to ambient through its surfaces.
    Conduction between nodes is integrated implicitly (it is stiff), ambient exchange explicitly."""

    def __init__(self, nodes, links, ambient_c: float = 25.0):
        self.nodes = list(nodes)
        self.idx = {n.name: i for i, n in enumerate(self.nodes)}
        self.links = [(self.idx[a], self.idx[b], g) for a, b, g in links]
        self.ambient = ambient_c
        self.fan = 0.0             # part-cooling fan speed, 0..1: raises the loss of nodes that have a g_fan
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
            if n.g_fan and self.fan > n.fan_law[0]:
                q += n.g_fan * ((self.fan - n.fan_law[0]) / (1.0 - n.fan_law[0])) ** n.fan_law[1] * (ti - ta)
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
    # A PTC heating element (E3D Revo HeaterCore): {"r_ohm_23c", "tempco_per_c", "volts", "r_series_ohm"}. Its resistance
    # rises with its own temperature, so the power at 100 % duty falls as it heats. `power_w` is then the cold figure.
    ptc: Optional[dict] = None
    # The hotend's heat sink, for a thermal cut-off mounted on it: {"capacity_j_k", "heatbreak_w_k", "fan_on_w_k",
    # "fan_off_w_k", "fan": 1.0 | 0.0, "from_node": "block"}. A side model: it is warmed through the heat break by the
    # node it hangs on and cooled by its fan or by still air. The heat it takes is already inside the fitted loss of the
    # block, so the heater's own (fitted) behaviour is unchanged by it. All four figures are assumed (HEAT_SINK_ASSUMED).
    heat_sink: Optional[dict] = None

    def heat_sink_g(self, fan: Optional[float] = None) -> float:
        hs = self.heat_sink
        fan = hs.get("fan", 1.0) if fan is None else fan
        return float(hs["fan_on_w_k"] if fan >= 0.5 else hs["fan_off_w_k"])

    def heat_sink_steady(self, t_from_c: float, fan: Optional[float] = None) -> float:
        """Heat-sink temperature once settled with the node it hangs on at t_from_c (fan: 1 running, 0 stopped;
        default the plant's own setting)."""
        hs, g = self.heat_sink, self.heat_sink_g(fan)
        return (hs["heatbreak_w_k"] * float(t_from_c) + g * self.net.ambient) / (hs["heatbreak_w_k"] + g)

    def power_at(self, t_heater_c: float) -> float:
        """Power at 100 % duty with the heating element at t_heater_c (constant for an ordinary cartridge or pad)."""
        if not self.ptc:
            return self.power_w
        r = self.ptc["r_ohm_23c"] * (1.0 + self.ptc["tempco_per_c"] * (float(t_heater_c) - 23.0))
        i = self.ptc["volts"] / (r + self.ptc.get("r_series_ohm", 0.0))
        return i * i * r

    def steady_full_duty(self, t_guess: float = 100.0) -> np.ndarray:
        """Node temperatures if the heater is left at 100 % duty for ever (a PTC element limits itself)."""
        ih = self.net.idx[self.heater_node]
        p = np.zeros(len(self.net.nodes))
        p[ih] = self.power_at(t_guess)
        T = self.net.steady(p, t_guess=t_guess)
        if self.ptc:
            for _ in range(60):
                p[ih] = 0.5 * p[ih] + 0.5 * self.power_at(T[ih])
                Tn = self.net.steady(p, t_guess=float(T[ih]))
                done = np.abs(Tn - T).max() < 0.02
                T = Tn
                if done:
                    break
        return T


def control_code() -> tuple:
    """(module, description) of the heater control code in use: Klipper's own classes when its source is installed
    (mechloop.twin.klippy_code), else None and the line-for-line port below. MECHLOOP_HEATER_CONTROL=port forces the port."""
    import os

    if os.environ.get("MECHLOOP_HEATER_CONTROL", "").lower() != "port":
        try:
            from .twin import klippy_code as K

            if K.available():
                return K, K.source() + ": heaters.ControlPID / ControlBangBang, verify_heater.HeaterCheck, pid_calibrate.ControlAutoTune"
        except Exception:
            pass
    return None, "port of Klipper's control laws in mechloop.electrical (Klipper's source is not installed, or the port was asked for)"


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
    ctl = tuner = None
    K, code = control_code()
    if duty_override is None and not autotune:
        kind = "pid" if cfg.get("control", "pid") == "pid" else "watermark"
        if K is not None:
            ctl = K.HeaterControl(kind, cfg, report_time=REPORT_TIME)
        elif kind == "pid":
            kp, ki, kd = cfg["pid"]
            ctl = _PID(kp, ki, kd, cfg.get("max_power", 1.0), cfg.get("smooth_time", 1.0))
        else:
            ctl = _BangBang(cfg.get("max_delta", 2.0), cfg.get("max_power", 1.0))
    elif autotune and K is not None:
        tuner = K.HeaterControl("autotune", cfg, target=target, report_time=REPORT_TIME)
    vh_cfg = cfg.get("verify_heater", {}) if duty_override is None else None
    if vh_cfg is None:
        vh = None
    elif K is not None:
        vh = K.HeaterVerify(plant.name, vh_cfg)
    else:
        vh = _VerifyHeater(**vh_cfg)
    smooth, inv_smooth = sensor, 1.0 / cfg.get("smooth_time", 1.0)
    duty, shutdown, shutdown_reason, t_shutdown = 0.0, False, "", None
    out_of_range = 0
    fused, t_fuse, relay_open, t_relay = False, None, False, None
    hs = plant.heat_sink
    if hs is not None:      # settled against the starting temperature of the node it hangs on (ambient on a cold start)
        # "fan" is the heat-sink fan's state once the fault has struck (or throughout, without a fault);
        # "fan_before_fault" its state until then (default: the same)
        i_hs = net.idx[hs.get("from_node", "block")]
        fan_before = hs.get("fan_before_fault", hs.get("fan", 1.0))
        t_hs = plant.heat_sink_steady(T[i_hs], fan_before)
        hs_peak = t_hs
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
                if tuner is not None:            # Klipper's ControlAutoTune decides when to switch and when it is done
                    duty = tuner.update(t, temp, target)
                    if not tuner.tuning():
                        break
                elif autotune:
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
        if hs is not None:
            g_hs = plant.heat_sink_g(None if (faulted or fault is None) else fan_before)
            t_hs += (hs["heatbreak_w_k"] * (T[i_hs] - t_hs) - g_hs * (t_hs - net.ambient)) * dt / hs["capacity_j_k"]
            hs_peak = max(hs_peak, t_hs)
        for c in plant.cutoffs:
            if c["kind"] == "thermal_fuse" and not fused and (t_hs if c["node"] == "heat_sink" else T[net.idx[c["node"]]]) >= c["trip_c"]:
                fused, t_fuse = True, t
            if c["kind"] == "psu_relay" and shutdown and not relay_open and t >= t_shutdown + c.get("delay_s", 0.05):
                relay_open, t_relay = True, t
        if fused or relay_open:
            applied = 0.0
        power[:] = 0.0
        power[ih] = applied * plant.power_at(T[ih])       # a PTC element makes less as it heats; a short does not switch it off
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
           "fuse_opened_at": t_fuse, "relay_opened_at": t_relay, "peaks": tuner.peaks() if tuner is not None else peaks,
           "control_code": code}
    if hs is not None:
        res["heat_sink_c"], res["heat_sink_peak_c"] = float(t_hs), float(hs_peak)
    if tuner is not None and len(res["peaks"]) >= 6:
        res["autotune_pid"] = tuner.final_pid()
    return res


def autotune_pid(plant: HeaterPlant, cfg: dict, target: float) -> tuple:
    """Klipper's PID_CALIBRATE (relay test, Astrom-Hagglund) run on the model. Returns (Kp, Ki, Kd)."""
    tau = float(plant.net.C.sum()) / max(1e-6, plant.power_w / max(target - plant.net.ambient, 1.0))
    r = simulate_heater(plant, {**cfg, "verify_heater": None}, target, t_end=max(600.0, 6 * tau), autotune=True)
    pk = r["peaks"]
    if len(pk) < 6:
        raise RuntimeError(f"autotune of {plant.name} did not oscillate ({len(pk)} peaks): target not reachable?")
    if "autotune_pid" in r:      # Klipper's own calc_final_pid on the peaks its ControlAutoTune recorded
        return tuple(round(float(x), 3) for x in r["autotune_pid"])

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
    Ts = plant.steady_full_duty(t_guess=max(targets) + 100.0)
    out["max_temp_c"] = float(Ts[plant.net.idx[plant.report_node]])
    out["duty_at"], out["power_w_at"] = {}, {}
    for tg in targets:      # steady duty = loss at target / heater power there (all nodes at about the target)
        loss = float(plant.net.loss(np.full(len(plant.net.nodes), float(tg))).sum())
        pw = plant.power_at(tg)
        out["power_w_at"][tg] = pw
        out["duty_at"][tg] = loss / pw if pw > 0 else float("inf")
    return out


def closed_loop_metrics(r: dict, target: float) -> dict:
    """Overshoot, settling and ripple of the temperature that matters (block, plate surface). The firmware regulates
    the SENSOR; a sensor that sits nearer the heater than the surface leaves a steady offset, reported as
    steady_error_c. Overshoot and settling are measured against the level the surface finally holds."""
    T, t = r["T"], r["t"]
    n_tail = int(30.0 / PWM_CYCLE)
    tail = T[-n_tail:]
    final = float(tail.mean())
    held = abs(float(r["sensor"][-n_tail:].mean()) - target) < 2.0 and float(r["duty"][-n_tail:].mean()) < 0.98
    if not held:
        return {"reached": False, "final_c": round(final, 2)}
    i0 = int(np.argmax(T >= final - 1.0))
    over = float(T[i0:].max() - final)
    outside = np.where(np.abs(T - final) > 1.0)[0]
    i_settle = int(outside[-1]) + 1 if len(outside) else 0
    settled = i_settle < len(T) - int(20.0 / PWM_CYCLE)
    return {"reached": True, "time_to_target_s": float(t[i0]), "overshoot_c": round(over, 2),
            "settled": bool(settled), "settling_time_s": float(t[min(i_settle, len(t) - 1)]) if settled else None,
            "ripple_c": round(float(tail.max() - tail.min()), 3), "steady_error_c": round(final - target, 3),
            "steady_duty": round(float(r["duty"][-n_tail:].mean()), 3)}


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
def fan_port(dev: Device) -> str:
    """Name of a fan device's supply port ("in" on catalog fans; "out" when it was made with embedded_device)."""
    return next((p.name for p in dev.ports.values() if p.kind == "fan"), "in")


def add_board_5v_port(el: "Electrical", board: str, name: str = "5V", at=None, connector: str = "dupont", max_a: float = 2.0) -> Port:
    """Declare the board's always-on +5 V / GND header pins as a port a 5 V fan may be wired to (kind "rail_5v").
    The SKR Mini E3 V3.0 brings +5V out on its header pins (BTT PIN drawing). Whatever is wired here is added to the
    host's draw in the board's 5 V budget (`board_5v_overloaded`). A fan on this port runs whenever the machine is
    powered: there is no firmware section for it."""
    b = el.devices[board]
    if name in b.ports:
        return b.ports[name]
    ref = next((p for p in b.ports.values() if p.kind == "host"), None) or next(iter(b.ports.values()))
    b.ports[name] = Port(name, "rail_5v", connector, max_a, None, 2, tuple(at) if at is not None else ref.at, ref.direction,
                         None, True, {**{k: v for k, v in ref.extra.items() if k == "body"}, "volts": 5.0})
    return b.ports[name]


def add_regulator(el: "Electrical", design, name: str, component: str, out_v: float = 5.0, max_a: float = 1.0,
                  efficiency: float | None = None, in_v_max: float = 28.0, product: dict | None = None, sources: dict | None = None) -> Device:
    """A stock step-down board in line between a board fan output and a low-voltage fan (E3D's REVO-MICRO-BOARD-REG for
    the Roto's 5 V fan on a 24 V machine). `component` is its CAD part. `efficiency=None` treats it as a linear
    regulator (input current = output current, the rest is heat): the safe assumption when the vendor gives no figure.
    max_a, in_v_max and efficiency are the caller's figures; say where they come from in `sources`."""
    c = design.get(component)
    bb = c.shape.bounding_box()
    ctr = ((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2)
    ports = {"in": Port("in", "fan", "JST-XH", 3.0, None, 2, ctr, None, extra={"body": c.body}),
             "out": Port("out", "fan_out", "JST-XH", 3.0, None, 2, ctr, None, extra={"body": c.body})}
    dev = Device(name, "regulator", component, ports,
                 {"out_v": float(out_v), "max_a": float(max_a), "efficiency": efficiency, "in_v_max": float(in_v_max)},
                 {"out_v": "caller", "max_a": "caller (typical, unverified unless a data sheet is cited)", **(sources or {})},
                 {"through": {"in": "out", "out": "in"}},
                 product or {"product": "E3D 5 V regulator board for 12 / 24 V machines", "vendor": "E3D-Online",
                             "part_number": "REVO-MICRO-BOARD-REG", "form": "assembled board", "off_the_shelf": True, "custom_pcb": False,
                             "builder_work": "plug in line between the board's fan output and the fan lead"})
    return el.add(dev)


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
    res["fans"], res["rail_5v_a"], res["regulators"] = {}, {}, {}
    for d in el.devices.values():
        if d.kind == "fan":
            i = float(d.ratings.get("current_a", 0.0))
            rated_v = float(d.ratings.get("volts", V))
            wires, series, src = trace_supply(el, f"{d.name}.{fan_port(d)}")
            sdev, sport = el.port(src) if src else (None, None)
            reg = next((dev for dev, _, _ in series if dev.kind == "regulator"), None)
            supplied_v, i_in, via = V, i, "supply voltage, switched by the board"
            if sport is not None and sport.kind == "rail_5v":
                supplied_v = float(sport.extra.get("volts", 5.0))
                eff = float(sdev.ratings.get("rail_5v_efficiency", 0.85))
                i_in = i * supplied_v / (eff * V)
                res["rail_5v_a"][sdev.name] = res["rail_5v_a"].get(sdev.name, 0.0) + i
                via = f"{sdev.name} +5 V rail (always on)"
            if reg is not None:       # a step-down board between the output and the fan
                out_v = float(reg.ratings.get("out_v", 5.0))
                eff = reg.ratings.get("efficiency")        # None: taken as a linear regulator (input current = output current)
                i_reg_in = i * out_v / (float(eff) * supplied_v) if eff else i
                rg = res["regulators"].setdefault(reg.name, {"out_a": 0.0, "in_a": 0.0, "in_v": supplied_v, "out_v": out_v, "loss_w": 0.0})
                rg["out_a"] += i
                rg["in_a"] += i_reg_in
                rg["loss_w"] = round(rg["loss_w"] + i_reg_in * supplied_v - i * out_v, 3)
                i_in = i_in * i_reg_in / i if i > 0 else 0.0
                supplied_v, via = out_v, f"{reg.name} ({out_v:g} V regulator) from " + via
            seen_reg, i_side = False, (i_reg_in if reg is not None else i)
            for w in wires:           # fan side of a regulator carries the fan's current, the supply side the regulator's input
                res["wire_current"][w.name] = i_side if seen_reg else i
                if reg is not None and reg.name in (w.a.split(".")[0], w.b.split(".")[0]):
                    seen_reg = True
            fan_i[d.name] = i_in
            res["fans"][d.name] = {"rated_v": rated_v, "supplied_v": supplied_v, "via": via, "current_a": i,
                                   "supply_current_a": round(i_in, 4), "source": src}
            res["loads_w"][d.name] = round(i_in * V, 2)
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
# A hotend's heat sink, as seen by a thermal cut-off taped to it. ASSUMED values for a V6-size finned aluminium sink with
# a 30 mm fan (no measurement, no vendor figure): override on the cut-off device, device_from(el, d, "<tco>",
# heat_sink={"capacity_j_k": ..., "fan_on_w_k": ..., "fan_off_w_k": ...}); the heat break comes from the heater's
# own "heatbreak_w_k" when it has one.
HEAT_SINK_ASSUMED = {"capacity_j_k": 10.0,      # about 11 g of aluminium
                     "heatbreak_w_k": 0.02,     # block to sink through the heat break: about 4.5 W at 250 degC
                     "fan_on_w_k": 0.25,        # sink to air with its fan running: about 4 K/W
                     "fan_off_w_k": 0.03}       # sink to still air: natural convection and radiation from about 30 cm^2
HEAT_SINK_NOTE = ("heat sink as a side model: warmed through the heat break by the block, cooled by its fan (fan_on_w_k) or by "
                  "still air (fan_off_w_k). All figures ASSUMED for a V6-size sink with a 30 mm fan, not measured and not from a "
                  "vendor; the heat it takes is already in the block's fitted loss")


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
        is_plate = p.get("model") == "plate"
        heat_sink = None
        for dev, _, _ in series:
            if dev.kind == "thermal_fuse":
                # where the cut-off sits: on the plate of a bed; on a hotend, the heat sink unless the design says "block"
                # (no common thermal cut-off survives on a 250 degC block; the nuisance check says so if one is put there)
                node = dev.params.get("node") or ("plate" if is_plate else "heat_sink")
                cut.append({"kind": "thermal_fuse", "node": node, "trip_c": dev.ratings["trip_c"], "device": dev.name})
                if node == "heat_sink" and not is_plate:
                    heat_sink = {**HEAT_SINK_ASSUMED, "heatbreak_w_k": float(p.get("heatbreak_w_k", HEAT_SINK_ASSUMED["heatbreak_w_k"])),
                                 **{k: float(v) for k, v in (dev.params.get("heat_sink") or {}).items()}, "fan": 1.0, "from_node": "block"}
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
            import os

            from .twin import fitted as _fit

            hcomp = comps.get(hd.component)
            cls = _fit.hotend_class(hcomp.sku if hcomp is not None else None, ptc=bool(p.get("ptc")))
            use_fit = p.get("thermal_model", os.environ.get("MECHLOOP_HOTEND_MODEL", "fitted")) != "catalog"
            if use_fit:
                # Three masses fitted to logged runs of a V6-class hotend (twin/fitted_parameters.json: hotend_thermal): the
                # cartridge, the block where the sensor sits, and the nozzle side behind it; loss from the block as a
                # fixed conductance plus a T^4 term, more with the part fan (net.fan), and a little from the nozzle.
                # The part's own capacity and area estimates are replaced; they stay in `basis` for comparison.
                ft = _fit.hotend_thermal(cls)
                rad_area = ft["radiation_w_k4"] / SIGMA          # an area with emissivity 1 that radiates the fitted T^4 term
                nodes = [ThermalNode("cartridge", ft["cartridge_capacity_j_k"]),
                         ThermalNode("block", ft["block_capacity_j_k"], [Surface(rad_area, "fixed", 0.01, 1.0, h_fixed=0.0)],
                                     g_ambient=ft["block_loss_w_k"], g_fan=ft["fan_loss_w_k"],
                                     fan_law=(ft["fan_threshold"], ft["fan_exponent"])),
                         ThermalNode("nozzle", ft["nozzle_capacity_j_k"], g_ambient=ft["nozzle_loss_w_k"])]
                net = ThermalNet(nodes, [("cartridge", "block", ft["cartridge_block_w_k"]), ("block", "nozzle", ft["block_nozzle_w_k"])], amb)
                tau = float(ft["sensor_tau_s"])
                basis.update({"thermal_model": f"fitted three-node, class '{cls}' (mechloop/twin/fitted_parameters.json: hotend_thermal)",
                              "total_capacity_j_k": ft["total_capacity_j_k"], "loss_still_w_k_at_245c": ft["loss_still_w_k_at_245c"],
                              "loss_full_fan_w_k_at_245c": ft["loss_full_fan_w_k_at_245c"], "sensor_tau_s": tau,
                              "what_is_fitted": ("fitted to one Ender 3's logs; range from Prusa's and Marlin's constants" if cls == "v6" else
                                                 "NOT fitted: totals from Prusa's Revo model, node split and loss law scaled from the V6-class fit"),
                              "catalog_estimates_replaced": {"block_capacity_j_k": p.get("block_capacity_j_k", 12.0),
                                                             "cartridge_capacity_j_k": p.get("cartridge_capacity_j_k", 1.5),
                                                             "sensor_tau_s": (sd.params.get("tau_s", 4.5) if sd else 4.5)}})
            else:
                c_block = p.get("block_capacity_j_k", 12.0)
                c_cart = p.get("cartridge_capacity_j_k", 1.5)
                a_blk = p.get("block_area_m2", 1.6e-3)
                nodes = [ThermalNode("cartridge", c_cart),
                         ThermalNode("block", c_block, [Surface(a_blk, "body", p.get("block_height_m", 0.0115), p.get("emissivity", 0.3),
                                                                h_fixed=p.get("h_forced", 0.0))],
                                     g_ambient=p.get("heatbreak_w_k", 0.02))]
                net = ThermalNet(nodes, [("cartridge", "block", p.get("cartridge_contact_w_k", 2.0))], amb)
                tau = float(sd.params.get("tau_s", 4.5) if sd else 4.5)
                basis.update({"thermal_model": "catalogue estimates (assumed values)", "block_capacity_j_k": c_block, "block_area_m2": a_blk,
                              "heatbreak_w_k": p.get("heatbreak_w_k", 0.02)})
            ptc = None
            if p.get("ptc"):      # resistance rises with temperature: power at 100 % duty falls as the element heats
                hv = circuit["heaters"].get(hd.name, {})
                r0 = float(p["ptc"]["r_ohm_23c"])
                r_ser = max(0.0, el.supply_v / hv["current_a"] - hv.get("resistance_ohm", r0)) if hv.get("current_a") else 0.0
                ptc = {"r_ohm_23c": r0, "tempco_per_c": float(p["ptc"]["tempco_per_c"]), "volts": el.supply_v,
                       "r_series_ohm": round(r_ser, 4)}
                basis["ptc"] = {**ptc, "note": "PTC element: power at 100 % duty falls with the element's temperature; "
                                               "heater_power_w is the cold (23 degC) figure"}
            if heat_sink is not None:
                basis["heat_sink"] = {**heat_sink, "note": HEAT_SINK_NOTE}
            plants[hname] = HeaterPlant(hname, net, "cartridge", "block", "block", power,
                                        sensor_tau_s=tau, cutoffs=cut, basis=basis, ptc=ptc, heat_sink=heat_sink)
        if sd is not None and sd.params.get("points"):
            board_in = next((el.port(el.other_end(w, f"{sd.name}.out"))[1] for w in el.wires_at(f"{sd.name}.out")), None)
            pull = (board_in.extra.get("pullup_ohm") if board_in else None) or 4700.0
            bits = (board_in.extra.get("adc_bits") if board_in else None) or 12
            plants[hname].thermistor = Thermistor(sd.params["points"], sd.params.get("beta"), pull, bits, sd.params.get("sensor_type", ""))
    for hname, pl in plants.items():      # a cut-off said to sit on a node this heater's model does not have: say so, do not crash
        bad = [c for c in pl.cutoffs if c["kind"] == "thermal_fuse" and c["node"] not in pl.net.idx
               and not (c["node"] == "heat_sink" and pl.heat_sink is not None)]
        if bad:
            pl.cutoffs = [c for c in pl.cutoffs if c not in bad]
            pl.basis["cutoffs_not_modelled"] = [
                {"device": c["device"], "node": c["node"],
                 "why": f"this heater's thermal model has no node '{c['node']}': use one of {sorted(pl.net.idx)}"
                        + ("" if "plate" in pl.net.idx else " or 'heat_sink'") + " (device_from(..., node=...))"} for c in bad]
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


# Assumed where the probe's own ratings do not say (IEC 60947-5-2 class figures, recalled, unverified):
PROBE_DEFAULTS = {
    "switching_distance_tolerance_frac": 0.10,   # unit-to-unit spread of the real sensing distance about nominal
    "repeatability_mm": 0.01,                    # trigger-point scatter probe to probe at one spot (assumed)
    "edge_margin_mm": None,                      # keep the sensing face this far inside the plate edge; default = face size
}


# A proximity sensor's own temperature a few millimetres above a heated bed (see probe_temperature_estimate).
PROBE_THERMAL = {
    "k_air_w_mk": 0.0285,        # air at about 55 degC
    "emissivity": 0.9,           # bed surface and sensor face taken as near-black in the infrared (the high side)
    "h_out_w_m2k": 10.0,         # barrel to the surrounding air: free convection plus radiation in still air (the low side)
    "min_gap_mm": 0.5,
    "margin_k": 10.0,            # asked between the HIGH estimate and the sensor's ambient rating
}


def probe_temperature_estimate(bed_c: float, room_c: float, gap_mm: float, face_area_mm2: float, side_area_mm2: float) -> dict:
    """Steady temperature of a sensor body whose face hangs `gap_mm` above a plate at `bed_c`, as a range.

    One lump (the metal barrel is a good conductor next to the air films): heat comes in through the face from the bed,
    by conduction across the air gap (k_air / gap) and radiation (4 sigma eps T^3), and leaves from the barrel's side
    to the air round it (h_out). So the body sits a fraction f = G_in / (G_in + G_out) of the way from that air's
    temperature to the bed's. The unknown is the air round the barrel:
      low  = room air (the toolhead is moving, or a fan stirs the air);
      high = the film temperature (bed + room) / 2, the usual reference for the air in a free-convection layer over a
             hot plate (the toolhead parked over the middle of the bed while it soaks).
    Never above the bed, never below the room. NOT validated against a measurement: h_out, the emissivity and the choice
    of the film temperature are textbook values, which is why the check asks PROBE_THERMAL['margin_k'] on top of `high`
    (a still corner at 5 W/m2K, or a room 6 K warmer, each moves `high` by about 3 to 6 K)."""
    c = PROBE_THERMAL
    gap = max(float(gap_mm), c["min_gap_mm"])
    t_film = 0.5 * (bed_c + room_c)
    h_rad = 4.0 * 5.67e-8 * c["emissivity"] * (t_film + 273.15) ** 3
    g_in = (c["k_air_w_mk"] / (gap * 1e-3) + h_rad) * face_area_mm2 * 1e-6
    g_out = c["h_out_w_m2k"] * side_area_mm2 * 1e-6
    f = g_in / (g_in + g_out) if (g_in + g_out) > 0 else 1.0
    low = room_c + f * (bed_c - room_c)
    high = t_film + f * (bed_c - t_film)
    if bed_c <= room_c:
        low = high = room_c
    return {"low_c": round(low, 1), "high_c": round(high, 1), "bed_c": float(bed_c), "room_c": float(room_c), "gap_mm": round(gap, 2),
            "face_area_mm2": round(face_area_mm2, 1), "side_area_mm2": round(side_area_mm2, 1),
            "fraction_of_the_way_to_the_bed": round(f, 3), "air_round_the_barrel_c": [float(room_c), round(t_film, 1)],
            "validated": False,
            "basis": "one-lump balance: in through the face across the air gap (conduction k_air/gap + radiation), out from the "
                     f"barrel's side at {c['h_out_w_m2k']:g} W/m2K to air between room temperature (low) and the film temperature "
                     "(bed + room) / 2 (high). Textbook values, not validated against a measurement"}


def _probe_areas(pc) -> tuple:
    """(face area, side area) in mm^2 of a probe part: from its thread data when it is a threaded barrel, else from its
    bounding box (footprint as the face, which is the high side for heat coming in; pi/4 of the box's sides)."""
    mt = (pc.meta.get("interfaces") or {}).get("mounting") or {}
    if mt.get("thread_dia") and mt.get("thread_z"):
        d = float(mt["thread_dia"])
        return math.pi * d * d / 4.0, math.pi * d * float(mt["thread_z"][1])      # the metal barrel, face to the end of the thread
    bs = pc.shape.bounding_box().size
    sz = sorted((float(bs.X), float(bs.Y), float(bs.Z)))
    a, b, h = sz[0], sz[1], sz[2]
    return a * b, math.pi / 4.0 * 2.0 * (a + b) * h


def probe_of(design):
    """(endstop entry, component) of the design's bed probe, or (None, None). A probe is declared as
    design.endstops += [{"joint": <z joint>, "probe": <part>}]; its part carries an electrical template of kind 'probe'."""
    comps = {c.name: c for c in design.components}
    for e in getattr(design, "endstops", []):
        if e.get("probe"):
            return e, comps.get(e["probe"])
    return None, None


def probe_geometry(design) -> dict | None:
    """Where the bed probe is and what it can do, from the CAD and the probe's ratings. None when the design has no
    probe. Lengths in mm. Machine coordinates are the firmware's: X and Y count from the low end of each joint's
    travel, Z is the nozzle's height above the bed. Raises ValueError when the declaration cannot be used."""
    from .geom import forward_kinematics

    e, pc = probe_of(design)
    if e is None:
        return None
    if pc is None:
        raise ValueError(f"the probe part '{e.get('probe')}' is not in the design")
    pr = design.printer or {}
    joints = {j.name: j for j in design.joints}
    if design.tool_point is None or pr.get("bed") is None:
        raise ValueError("a bed probe needs design.tool_point and design.printer['bed']")
    tpl = pc.ratings.get("electrical") if isinstance(pc.ratings.get("electrical"), dict) else {}
    rt = dict(tpl.get("ratings", {}))
    src = dict(tpl.get("sources", {}))
    itf = pc.meta.get("interfaces", {})
    if "sensing_face" not in itf:
        raise ValueError(f"probe part '{pc.name}' has no 'sensing_face' interface (centre of the face that looks at the bed)")
    T0 = forward_kinematics(design, {})
    tb, tp = design.tool_point
    noz = (T0[tb] @ np.array([*tp, 1.0]))[:3]
    face = (T0[pc.body] @ np.array([*itf["sensing_face"][0], 1.0]))[:3] if pc.body in T0 else np.array(itf["sensing_face"][0])
    bed = design.get(pr["bed"])
    bb = bed.shape.bounding_box()
    mat = (bed.material or "").lower()
    target = "aluminium" if mat.startswith("al") else ("steel" if "steel" in mat else None)
    sn = rt.get(f"switching_distance_{target}_mm") if target else None
    tol = rt.get("switching_distance_tolerance_frac", PROBE_DEFAULTS["switching_distance_tolerance_frac"])
    rep = rt.get("repeatability_mm", PROBE_DEFAULTS["repeatability_mm"])
    jx, jy, jz = (joints.get(pr.get(a, a)) for a in "xyz")
    out = {"probe": pc.name, "joint": e.get("joint"), "on_body": pc.body, "rides_with_nozzle": pc.body == tb,
           "bed_material": bed.material, "target": target, "sensing_distance_mm": sn,
           "sensing_distance_tolerance_frac": tol, "repeatability_mm": rep,
           "assumed": [k for k, v in (("sensing_distance_tolerance_frac", "switching_distance_tolerance_frac" not in rt),
                                      ("repeatability_mm", "repeatability_mm" not in rt)) if v],
           "sources": {k: src.get(k, "not stated") for k in rt if k.startswith("switching_distance") or k == "repeatability_mm"},
           "x_offset": round(float(face[0] - noz[0]), 3), "y_offset": round(float(face[1] - noz[1]), 3),
           "face_above_nozzle_mm": round(float(face[2] - noz[2]), 3)}
    if sn is None:
        out["z_offset"] = None
        return out
    # the firmware's z_offset: nozzle height above the bed at the moment the probe switches
    z_off = sn - (face[2] - noz[2])
    out["z_offset"] = round(float(z_off), 3)
    # the spread of the real switching distance: unit to unit (tol), with temperature where the part's sheet gives a
    # drift (temperature_drift_frac), and over the range a chart gives for the target material where it gives one
    drift = float(rt.get("temperature_drift_frac", 0.0) or 0.0)
    sn_lo, sn_hi = (rt.get(f"switching_distance_{target}_range_mm") or [sn, sn])[:2]
    h_face = float(face[2] - noz[2])
    # The sensor's own temperature over the heated bed, where the design says how hot the bed runs: the maker's drift
    # figure holds up to `drift_rated_to_c`; if the sensor may run hotter, the wider figure for its full range applies.
    el = getattr(design, "electrical", None)
    hot = getattr(el, "hot_parts", None) or {}
    bed_t = hot.get("bed")
    bed_t = bed_t.get("temp") if isinstance(bed_t, dict) else bed_t
    if bed_t is not None:
        room = float({**DEFAULT_REQUIREMENTS, **(getattr(el, "requirements", None) or {})}.get("ambient_c", 25.0))
        a_face, a_side = _probe_areas(pc)
        est = probe_temperature_estimate(float(bed_t), room, h_face + float(pr.get("layer_height", 0.2)), a_face, a_side)
        out["sensor_temperature_estimate"] = est
        rated_to = rt.get("drift_rated_to_c")
        out["temperature_drift_basis"] = (f"+/-{drift:.0%}" + (f", the maker's figure up to {rated_to:g} degC" if rated_to is not None else "")
                                          + f"; sensor estimated at {est['low_c']:g} to {est['high_c']:g} degC over a {float(bed_t):g} degC bed")
        if drift and rated_to is not None and est["high_c"] > float(rated_to):
            full = rt.get("temperature_drift_full_range_frac")
            if full:
                drift = float(full)
                out["temperature_drift_basis"] = (f"+/-{drift:.0%}: the sensor is estimated at up to {est['high_c']:g} degC over a "
                                                  f"{float(bed_t):g} degC bed, above the {rated_to:g} degC to which the +/-"
                                                  f"{float(rt['temperature_drift_frac']):.0%} figure holds, so the maker's figure for the "
                                                  "full range is used")
            else:
                out["temperature_drift_basis"] += f": ABOVE the {rated_to:g} degC the figure holds to, and no wider figure is known"
                out["assumed"].append("temperature_drift_frac above its rated temperature")
    out["sensing_distance_range_mm"] = [round(float(sn_lo), 3), round(float(sn_hi), 3)]
    out["temperature_drift_frac"] = drift
    out["z_offset_range_unit_spread_mm"] = [round(float(z_off - tol * sn), 3), round(float(z_off + tol * sn), 3)]
    out["z_offset_range_mm"] = [round(float(sn_lo * (1.0 - tol - drift) - h_face), 3), round(float(sn_hi * (1.0 + tol + drift) - h_face), 3)]
    gap0 = float(noz[2] - bb.max.Z)
    out["nozzle_above_bed_at_home_pose_mm"] = round(gap0, 3)
    if jz is not None:   # how close to the nozzle the Z travel can bring the bed (firmware Z at the joint's upper end)
        # the mechanical end: the working range plus any declared over-travel (Joint.overtravel)
        out["nozzle_above_bed_at_end_of_z_travel_mm"] = round(gap0 - jz.mechanical_range[1], 3)
        out["nozzle_above_bed_at_end_of_working_z_range_mm"] = round(gap0 - jz.range[1], 3)
        out["z_overtravel_past_working_range_mm"] = round(jz.mechanical_range[1] - jz.range[1], 3)
    if jx is None or jy is None:
        return out
    # machine coordinates: nozzle at X = q - lo; the bed's centre and extent in the same frame
    off = [float(face[0] - noz[0]), float(face[1] - noz[1])]
    trav = [jx.range[1] - jx.range[0], jy.range[1] - jy.range[0]]
    bmin = [bb.min.X - noz[0] - jx.range[0], bb.min.Y - noz[1] - jy.range[0]]
    bmax = [bb.max.X - noz[0] - jx.range[0], bb.max.Y - noz[1] - jy.range[0]]
    size = pc.shape.bounding_box().size
    margin = rt.get("edge_margin_mm") or PROBE_DEFAULTS["edge_margin_mm"] or round(max(min(size.X, size.Y), 2.0 * sn), 1)
    reach = [[max(0.0, bmin[k]), min(trav[k], bmax[k])] for k in (0, 1)]             # where the nozzle can be over the plate
    centre_ = [(bmin[k] + bmax[k]) / 2 for k in (0, 1)]
    declared = print_area_size(design)
    if declared is not None:
        # the DECLARED print area (design.printer["print_area"], centred on the plate): travel beyond it, e.g. added so
        # the probe can reach, is not print area
        want = [[centre_[k] - declared[k] / 2, centre_[k] + declared[k] / 2] for k in (0, 1)]
        area = [[max(reach[k][0], want[k][0]), min(reach[k][1], want[k][1])] for k in (0, 1)]
        out["print_area_basis"] = f"declared: design.printer['print_area'] = {declared[0]:g} x {declared[1]:g} mm, centred on the plate"
        out["print_area_declared"] = [[round(v, 3) for v in a] for a in want]
        out["print_area_outside_nozzle_reach_mm"] = {
            "x_low": round(max(0.0, reach[0][0] - want[0][0]), 3), "x_high": round(max(0.0, want[0][1] - reach[0][1]), 3),
            "y_low": round(max(0.0, reach[1][0] - want[1][0]), 3), "y_high": round(max(0.0, want[1][1] - reach[1][1]), 3)}
    else:
        area = reach
        out["print_area_basis"] = ("not declared (design.printer['print_area']): taken as the whole XY travel over the plate, so "
                                   "travel added for probing counts as print area")
    out["nozzle_reach_over_plate"] = [[round(v, 3) for v in a] for a in reach]
    mesh = [[max(bmin[k] + margin, off[k]), min(bmax[k] - margin, trav[k] + off[k])] for k in (0, 1)]   # where the probe can sense
    centre = [(bmin[k] + bmax[k]) / 2 for k in (0, 1)]
    home = [min(max(centre[k] - off[k], 0.0), trav[k]) for k in (0, 1)]              # nozzle position that puts the probe mid-bed
    out.update({"edge_margin_mm": margin, "bed_min": [round(v, 3) for v in bmin], "bed_max": [round(v, 3) for v in bmax],
                "travel": [round(v, 3) for v in trav],
                "print_area": [[round(v, 3) for v in a] for a in area], "mesh_min": [round(mesh[0][0], 2), round(mesh[1][0], 2)],
                "mesh_max": [round(mesh[0][1], 2), round(mesh[1][1], 2)],
                "home_xy": [round(v, 2) for v in home], "home_probe_xy": [round(home[k] + off[k], 2) for k in (0, 1)],
                "bed_centre": [round(v, 3) for v in centre],
                "unprobed_strip_mm": {"x_low": round(max(0.0, mesh[0][0] - area[0][0]), 2), "x_high": round(max(0.0, area[0][1] - mesh[0][1]), 2),
                                      "y_low": round(max(0.0, mesh[1][0] - area[1][0]), 2), "y_high": round(max(0.0, area[1][1] - mesh[1][1]), 2)}})
    return out


def print_area_size(design) -> tuple | None:
    """The print area a printer design claims, (x, y) in mm, centred on the bed plate: design.printer["print_area"] as
    (x, y) or (x, y, z). None when the design does not say."""
    pa = (getattr(design, "printer", None) or {}).get("print_area")
    if pa is None:
        return None
    try:
        x, y = float(pa[0]), float(pa[1])
    except Exception:
        raise ValueError("design.printer['print_area'] must be (x, y) or (x, y, z) in mm, centred on the bed plate")
    if x <= 0 or y <= 0:
        raise ValueError("design.printer['print_area'] sizes must be positive")
    return (x, y)


def _probe_pin(el: Electrical, design) -> tuple:
    """(pin string with pull-up and inversion as Klipper wants it, device, board port) for the design's probe."""
    _, pc = probe_of(design)
    dev = next((d for d in el.devices.values() if d.kind == "probe" and (pc is None or d.component == pc.name)), None)
    if dev is None:
        return None, None, None
    bp = _board_port_of(el, dev.name)
    if bp is None:
        return None, dev, None
    out = str(dev.ratings.get("output", "npn_no")).lower()
    # open-collector NPN needs the board's pull-up ('^'); normally-open NPN pulls the pin low when it switches ('!')
    pre = ("^" if out.startswith("npn") else "") + ("!" if out in ("npn_no", "pnp_nc") else "")
    return f"{pre}{bp.pin}", dev, bp


def extruder_gearing(el: Electrical, ex: dict) -> dict:
    """rotation_distance, gear_ratio and full_steps_per_rotation of the extruder as Klipper wants them.
    The design's firmware block wins; what it leaves out comes from the extruder part (the motor device's params,
    e.g. `extruder_roto`: 26.8937 mm per turn of the hobb, 11.262:1, 400 full steps). A part's gear_ratio and
    full_steps_per_rotation are only attached to the part's own rotation_distance: a firmware block that states a
    different rotation_distance (a per-motor-rev figure such as the 1.194 fallback) is taken as complete."""
    dev = el.devices.get((ex.get("motors") or [None])[0])
    pp = dev.params if dev is not None else {}
    rd, part_rd = ex.get("rotation_distance"), pp.get("rotation_distance")
    use_part = part_rd is not None and (rd is None or abs(float(rd) - float(part_rd)) <= 1e-3 * float(part_rd))
    out = {"rotation_distance": float(rd if rd is not None else (part_rd if part_rd is not None else 7.71)),
           "gear_ratio": ex.get("gear_ratio", pp.get("gear_ratio") if use_part else None),
           "full_steps_per_rotation": ex.get("full_steps_per_rotation", pp.get("full_steps_per_rotation") if use_part else None),
           "microsteps": int(ex.get("microsteps", 16)), "from_part": bool(use_part)}
    gr = out["gear_ratio"]
    if isinstance(gr, (int, float)):
        out["gear_ratio"] = f"{gr:g}:1"
    ratio = 1.0
    for term in str(out["gear_ratio"] or "1:1").split(","):
        a, b = term.split(":")
        ratio *= float(a) / float(b)
    out["steps_per_mm"] = (out["full_steps_per_rotation"] or 200) * out["microsteps"] * ratio / out["rotation_distance"]
    return out


def extruder_gearing_lines(el: Electrical, ex: dict) -> list:
    g = extruder_gearing(el, ex)
    L = [f"rotation_distance: {g['rotation_distance']:.6g}"]
    if g["gear_ratio"]:
        L.append(f"gear_ratio: {g['gear_ratio']}")
    if g["full_steps_per_rotation"]:
        L.append(f"full_steps_per_rotation: {int(g['full_steps_per_rotation'])}")
    return L


def _tmc_uart_lines(pins: dict) -> list:
    """UART lines of a [tmc2209 ...] section: a board with one shared UART bus gives uart, tx and an address per driver
    (SKR Mini E3 V3); a board with one UART pin per driver socket gives only that pin (MANTA M5P)."""
    out = [f"uart_pin: {pins['uart']}"]
    if pins.get("tx"):
        out.append(f"tx_pin: {pins['tx']}")
    if pins.get("uart_address") is not None:
        out.append(f"uart_address: {pins['uart_address']}")
    return out


SENSORLESS_SGTHRS_START = 100      # StallGuard threshold written for a sensorless axis: a starting point, not a prediction


def z_sense(design, j) -> dict:
    """How a printer's Z joint relates to the nozzle-to-bed gap: {"rides": "bed" | "nozzle" | None,
    "closes_with_joint": +1 when the gap closes as the joint's value rises, -1 when it opens, "error": text or None}.
    Either the bed or the nozzle's body must ride the joint (not both, not neither), and its axis must have a vertical
    component."""
    pr = design.printer or {}
    parent = {x.child: x.parent for x in design.joints}

    def under(body):
        seen = set()
        while body not in seen:
            if body == j.child:
                return True
            seen.add(body)
            if body not in parent:
                return False
            body = parent[body]
        return False

    try:
        bed_body = design.get(pr["bed"]).body
    except Exception:
        return {"rides": None, "closes_with_joint": 1, "error": "no bed part declared (design.printer['bed'])"}
    if design.tool_point is None:
        return {"rides": None, "closes_with_joint": 1, "error": "no tool point declared (design.tool_point)"}
    bed_r, noz_r = under(bed_body), under(design.tool_point[0])
    az = float(j.axis[2]) / (sum(float(x) ** 2 for x in j.axis) ** 0.5 or 1.0)
    if bed_r == noz_r:
        return {"rides": None, "closes_with_joint": 1,
                "error": f"joint '{j.name}' is declared as Z but " + ("both the bed and the nozzle ride on it" if bed_r else
                                                                      "neither the bed nor the nozzle rides on it")}
    if abs(az) < 0.5:
        return {"rides": "bed" if bed_r else "nozzle", "closes_with_joint": 1,
                "error": f"joint '{j.name}' is declared as Z but its axis {tuple(j.axis)} is not vertical"}
    # the bed rising (+Z) closes the gap; the nozzle rising opens it
    return {"rides": "bed" if bed_r else "nozzle", "closes_with_joint": 1 if (az > 0) == bed_r else -1, "error": None}


def _mirrored(j):
    """The same joint with its value's sign turned (range and over-travel swapped), for the firmware's Z arithmetic."""
    import copy

    m = copy.copy(j)
    m.range = (-j.range[1], -j.range[0])
    m.overtravel = tuple(reversed((tuple(j.overtravel) + (0.0, 0.0))[:2]))
    return m


def klipper_config(el: Electrical, design, sim: dict | None = None, tuning: dict | None = None) -> str:
    """printer.cfg from the pin map, the design's transmissions and joints, the heater simulation and the twin's
    tuning (mechloop.twin.tuning.firmware_tuning: input shaper, pressure advance, probe and bed mesh). With
    tuning=None the tuning is computed from the design alone (belt stiffness only, no FEA frame stiffness)."""
    from .verifiers.ratings import resolve_drives

    resolve_drives(design)
    fw = el.firmware
    axis_motors(el, design)
    joints = {j.name: j for j in design.joints}
    pr = design.printer or {}
    if tuning is None and pr:
        try:
            from .twin.tuning import firmware_tuning

            tuning = firmware_tuning(design, strict=False)
        except Exception as ex:      # the config is still written; the missing sections are named in it
            tuning = {"error": f"{type(ex).__name__}: {ex}"}
    tuning = tuning or {}
    L = [f"# printer.cfg for {design.name}: GENERATED by mechloop from the electrical model. Do not edit by hand;",
         "# change the design and regenerate. Directions (dir_pin '!') and the extruder rotation_distance must be",
         "# confirmed on the machine; PID values come from a simulated PID_CALIBRATE and should be re-run on the real heater.",
         "# Input shaper, pressure advance and probe offsets below are PREDICTIONS from the simulation, each resting on",
         "# assumed values named beside it: re-measure on the machine (SHAPER_CALIBRATE, a pressure-advance test print,",
         "# PROBE_CALIBRATE, BED_MESH_CALIBRATE)."]
    if tuning.get("error"):
        L += [f"# TUNING NOT GENERATED ({tuning['error']}): no [input_shaper], pressure_advance or mesh settings below."]
    for ng in tuning.get("not_generated") or []:
        L += [f"# NOT GENERATED: {ng}"]
    L += [""]
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
    pg = tuning.get("probe")
    probe_pin, probe_dev, _ = _probe_pin(el, design)
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
        sensorless = bool(e.get("sensorless"))
        if sensorless:
            L += [f"endstop_pin: tmc2209_stepper_{ax}:virtual_endstop"]
        elif e.get("probe"):
            L += ["endstop_pin: probe:z_virtual_endstop" if probe_pin else "# endstop_pin: PROBE NOT WIRED"]
        else:
            ep = _board_port_of(el, sw_dev[e["switch"]].name) if e.get("switch") in sw_dev else None
            L += [f"endstop_pin: ^{ep.pin}" if ep else "# endstop_pin: NOT WIRED"]
        if ax == "z":   # firmware Z is the nozzle's height above the bed
            gap = None
            if design.tool_point and pr.get("bed"):
                bb = design.get(pr["bed"]).shape.bounding_box()
                gap = design.tool_point[1][2] - bb.max.Z
            at_max = e.get("at", "min") == "max"
            # Z sign convention. The lines below are written for a joint whose value RISES as nozzle and bed come
            # together (a bed that rises on +Z, or a nozzle that descends on an axis of (0, 0, -1)). A joint drawn the
            # other way (value rising as they part) is the same machine with the joint's sign turned: mirror it.
            zs = z_sense(design, j)
            if zs["error"]:
                L += [f"# Z AXIS NOT CONFIGURED: {zs['error']}"]
                lo, hi = j.range
            elif zs["closes_with_joint"] < 0:
                lo, hi = -j.range[1], -j.range[0]
                at_max = not at_max
                j = _mirrored(j)
            z_end = (gap - hi) if (gap is not None and at_max) else 0.0
            zmax = (gap - lo) if gap is not None else hi - lo
            ot_lo, ot_hi = j.mechanical_range[0] - lo, j.mechanical_range[1] - hi     # declared over-travel (<= 0, >= 0)
            if e.get("probe"):     # Z = 0 comes from the probe's z_offset; travel may go below it by what the joint has
                # down to the MECHANICAL end of travel: the working range plus the declared over-travel past the nozzle
                # plane (Joint.overtravel), which is what a low-built bed and a bed mesh need
                z_low = (gap - (hi + ot_hi)) if gap is not None else -2.0
                L += [f"position_min: {min(0.0, z_low):.3f}", f"position_max: {zmax:.3f}", "homing_speed: 5", "second_homing_speed: 1",
                      "homing_retract_dist: 3"]
            else:
                L += [f"position_endstop: {z_end:.3f}", f"position_min: {min(0.0, z_end) - 0.5:.3f}",
                      f"position_max: {zmax:.3f}", "homing_speed: 5", "second_homing_speed: 1"]
        else:
            at_max = e.get("at", "min") == "max"
            L += [f"position_endstop: {(hi - lo) if at_max else 0:g}", "position_min: 0", f"position_max: {hi - lo:g}"]
            if sensorless:
                # Klipper docs/TMC_Drivers.md, "Sensorless Homing": half a motor turn per second, no second homing move
                L += [f"homing_speed: {dr.get('travel_per_rev', 40) / 2:g}", "homing_retract_dist: 0"]
            else:
                L += [f"homing_speed: {min(50.0, j.max_speed or 50.0):g}"]
            if at_max:
                L += ["homing_positive_dir: true"]
        L += ["", f"[tmc2209 stepper_{ax}]", *_tmc_uart_lines(pins),
              f"run_current: {st['run_current']:.3f}", f"sense_resistor: {board.ratings.get('sense_resistor_ohm', 0.11):.3f}",
              "stealthchop_threshold: 0"]
        # further motors of this axis on their OWN drivers (a Z on two or three screws, each with a motor): Klipper's
        # [stepper_z1], [stepper_z2] ... Motors that share the first motor's driver need no section.
        # (two connectors of one driver, like a board's doubled Z socket, are one driver: the step pin tells)
        extra_ports, seen_ports = [], {str(pins.get("step"))}
        for mn in st["motors"][1:]:
            p2 = _board_port_of(el, mn)
            if p2 is not None and isinstance(p2.pin, dict) and str(p2.pin.get("step")) not in seen_ports:
                seen_ports.add(str(p2.pin.get("step")))
                extra_ports.append(p2)
        for k2, p2 in enumerate(extra_ports, 1):
            q2 = p2.pin
            L += ["", f"[stepper_{ax}{k2}]", f"step_pin: {q2['step']}", f"dir_pin: {q2['dir']}", f"enable_pin: !{q2['enable']}",
                  f"microsteps: {st.get('microsteps', 16)}", f"rotation_distance: {dr.get('travel_per_rev', 40):g}",
                  "", f"[tmc2209 stepper_{ax}{k2}]", *_tmc_uart_lines(q2),
                  f"run_current: {st['run_current']:.3f}", f"sense_resistor: {board.ratings.get('sense_resistor_ohm', 0.11):.3f}",
                  "stealthchop_threshold: 0"]
        if ax == "z" and extra_ports:
            zt = fw.get("z_tilt")
            if zt and zt.get("z_positions") and zt.get("points"):
                L += ["", "[z_tilt]", "z_positions:"] + [f"    {x:g}, {y:g}" for x, y in zt["z_positions"]] + \
                     ["points:"] + [f"    {x:g}, {y:g}" for x, y in zt["points"]] + \
                     [f"speed: {zt.get('speed', 100):g}", f"horizontal_move_z: {zt.get('horizontal_move_z', 5):g}",
                      f"retries: {zt.get('retries', 5)}", f"retry_tolerance: {zt.get('retry_tolerance', 0.01):g}"]
            else:
                L += ["", f"# NO [z_tilt]: {1 + len(extra_ports)} Z motors on their own drivers but el.firmware['z_tilt'] = "
                          "{'z_positions': [(x, y), ...], 'points': [(x, y), ...]} is not declared;",
                      "# the screws are then never levelled against each other by the firmware."]
        if sensorless:
            sg = int((fw.get("sensorless") or {}).get(jn, {}).get("sgthrs", SENSORLESS_SGTHRS_START))
            if pins.get("diag"):
                L += [f"# sensorless homing: the driver's DIAG output reaches {pins['diag']} ONLY with a jumper fitted on the board's "
                      f"{pins.get('diag_jumper', 'DIAG')} header,",
                      f"# and with nothing plugged into that axis's endstop connector (same MCU pin). driver_SGTHRS is a STARTING "
                      f"value: tune it on the machine",
                      "# (Klipper docs/TMC_Drivers.md, 'Sensorless Homing': 255 is most sensitive, 0 never triggers).",
                      f"diag_pin: ^{pins['diag']}", f"driver_SGTHRS: {sg}"]
            else:
                L += ["# diag_pin: THIS BOARD'S CATALOGUE ENTRY NAMES NO DIAG PIN FOR THIS DRIVER: sensorless homing cannot be configured"]
        L += [""]
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
                  f"microsteps: {ex.get('microsteps', 16)}"] + extruder_gearing_lines(el, ex)
        L += [f"nozzle_diameter: {pr.get('nozzle', 0.4):.3f}", "filament_diameter: 1.750",
              f"heater_pin: {hp.pin if hp else 'NOT WIRED'}", f"sensor_type: {sd.params.get('sensor_type', 'Generic 3950') if sd else '?'}",
              f"sensor_pin: {sp.pin if sp else 'NOT WIRED'}"]
        L += _heater_lines(hx, (sim or {}).get("extruder"))
        # filament-only moves (retract, purge, load): limits from the design's firmware block or Klipper-style defaults
        xo = ex.get("extrude_only") or {}
        L += [f"max_extrude_only_distance: {xo.get('distance', 100.0):g}", f"max_extrude_only_velocity: {xo.get('velocity', 60.0):g}",
              f"max_extrude_only_accel: {xo.get('accel', 3000.0):g}"]
        pa = tuning.get("pressure_advance")
        if pa and pa.get("value") is not None:
            L += [f"# pressure advance: {pa.get('basis', '')}",
                  f"pressure_advance: {pa['value']:.4f}", f"pressure_advance_smooth_time: {pa.get('smooth_time', 0.04):g}"]
        L += [""]
        if port is not None:
            L += ["[tmc2209 extruder]", *_tmc_uart_lines(pins),
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
        fdev = el.devices.get(fc["device"])
        fp = _board_port_of(el, fc["device"], fan_port(fdev) if fdev is not None else "in")
        if fp is not None and fp.kind == "rail_5v":
            L += [f"# fan '{fname}' is wired to the board's +5 V rail: it runs whenever the machine is powered (no firmware section)", ""]
        elif fc.get("role") == "part":
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
    # ---- input shaper (Klipper shapes its own step stream; nothing else in the config changes)
    sh = tuning.get("input_shaper")
    if sh:
        L += [f"# input shaper: {sh.get('basis', '')}"]
        L += ["[input_shaper]"]
        for ax in ("x", "y"):
            if ax in sh:
                L += [f"shaper_type_{ax}: {sh[ax]['shaper_type']}", f"shaper_freq_{ax}: {sh[ax]['shaper_freq']:g}",
                      f"damping_ratio_{ax}: {sh[ax]['damping_ratio']:.3f}"]
        L += [""]
    # ---- probe, Z homing over the bed, bed mesh
    if pg and probe_pin and pg.get("z_offset") is not None:
        prov = _one_line((pg.get("sources") or {}).get(f"switching_distance_{pg.get('target')}_mm") or "source not stated")
        L += [f"# probe: offsets from the CAD; z_offset from the probe's nominal switching distance on {pg.get('target')} "
              f"({pg.get('sensing_distance_mm')} mm) - set it on the machine with PROBE_CALIBRATE",
              f"# that distance: {prov}",
              "[probe]", f"pin: {probe_pin}", f"x_offset: {pg['x_offset']:g}", f"y_offset: {pg['y_offset']:g}",
              f"z_offset: {pg['z_offset']:.3f}", "speed: 5", "lift_speed: 10", "samples: 3", "samples_result: median",
              "sample_retract_dist: 2", f"samples_tolerance: {max(0.02, 4 * pg.get('repeatability_mm', 0.01)):g}",
              "samples_tolerance_retries: 3", ""]
        if "home_xy" in pg:
            L += ["# Z homes with the probe over the middle of the bed",
                  "[safe_z_home]", f"home_xy_position: {pg['home_xy'][0]:g}, {pg['home_xy'][1]:g}", f"speed: {min(100.0, vmax):g}",
                  "z_hop: 5", "z_hop_speed: 5", ""]
            bmc = tuning.get("bed_mesh") or {}
            n = bmc.get("probe_count", (5, 5))
            L += ["# mesh bounds are probe positions: the bed inset by the probe's edge margin, cut to where the probe can reach",
                  "[bed_mesh]", f"speed: {min(100.0, vmax):g}", "horizontal_move_z: 5",
                  f"mesh_min: {pg['mesh_min'][0]:g}, {pg['mesh_min'][1]:g}", f"mesh_max: {pg['mesh_max'][0]:g}, {pg['mesh_max'][1]:g}",
                  f"probe_count: {n[0]}, {n[1]}", f"algorithm: {bmc.get('algorithm', 'lagrange')}",
                  f"mesh_pps: {bmc.get('mesh_pps', (2, 2))[0]}, {bmc.get('mesh_pps', (2, 2))[1]}",
                  f"fade_start: {bmc.get('fade_start', 1.0):g}", f"fade_end: {bmc.get('fade_end', 10.0):g}", "fade_target: 0",
                  f"split_delta_z: {bmc.get('split_delta_z', 0.01):g}",
                  f"zero_reference_position: {pg['home_probe_xy'][0]:g}, {pg['home_probe_xy'][1]:g}", ""]
            prof = bmc.get("profile")
            if prof:
                L += [f"# stored mesh: {prof.get('basis', 'measured by the twin on its as-built bed')}"]
                L += mesh_profile_lines(prof) + [""]
    return "\n".join(L)


def mesh_profile_lines(prof: dict, name: str = "default") -> list:
    """A saved bed mesh as Klipper's SAVE_CONFIG writes it ([bed_mesh <name>]); rows are Y ascending, X along the row."""
    pts = prof["points"]
    return [f"[bed_mesh {name}]", "version: 1", "points:"] + ["    " + ", ".join(f"{z:.6f}" for z in row) for row in pts] + [
        f"x_count: {len(pts[0])}", f"y_count: {len(pts)}", f"mesh_x_pps: {prof.get('mesh_x_pps', 2)}", f"mesh_y_pps: {prof.get('mesh_y_pps', 2)}",
        f"algo: {prof.get('algo', 'lagrange')}", f"tension: {prof.get('tension', 0.2):g}",
        f"min_x: {prof['min_x']:g}", f"max_x: {prof['max_x']:g}", f"min_y: {prof['min_y']:g}", f"max_y: {prof['max_y']:g}"]


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
    "input_shaper": [], "probe": ["pin", "z_offset"], "safe_z_home": ["home_xy_position"],
    "bed_mesh": [],     # [bed_mesh] itself is checked below; [bed_mesh <name>] is a stored profile
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
        if sec == "bed_mesh":
            for opt in ("mesh_min", "mesh_max"):
                if not cp.has_option(sec, opt):
                    problems.append(f"[{sec}]: missing {opt}")
            if not cp.has_section("probe"):
                problems.append("[bed_mesh] without a [probe]")
            elif cp.has_option(sec, "mesh_min") and cp.has_option(sec, "mesh_max"):
                lo_, hi_ = ([float(v) for v in cp.get(sec, o).split(",")] for o in ("mesh_min", "mesh_max"))
                if not (lo_[0] < hi_[0] and lo_[1] < hi_[1]):
                    problems.append(f"[bed_mesh]: empty mesh area {lo_} .. {hi_} (the probe cannot reach the bed)")
                for k_, ax_ in enumerate("xy"):      # the nozzle must be able to carry the probe to every mesh point
                    if cp.has_section(f"stepper_{ax_}"):
                        off_ = cp.getfloat("probe", f"{ax_}_offset", fallback=0.0)
                        a0, a1 = cp.getfloat(f"stepper_{ax_}", "position_min", fallback=0.0), cp.getfloat(f"stepper_{ax_}", "position_max")
                        if lo_[k_] - off_ < a0 - 1e-6 or hi_[k_] - off_ > a1 + 1e-6:
                            problems.append(f"[bed_mesh]: mesh {ax_.upper()} {lo_[k_]:g}..{hi_[k_]:g} needs the nozzle at "
                                            f"{lo_[k_] - off_:g}..{hi_[k_] - off_:g}, outside its travel {a0:g}..{a1:g}")
        if sec == "input_shaper":
            for ax_ in "xy":
                if cp.has_option(sec, f"shaper_freq_{ax_}") and not (0.0 < cp.getfloat(sec, f"shaper_freq_{ax_}") <= 200.0):
                    problems.append(f"[input_shaper]: shaper_freq_{ax_} out of range")
        if sec == "extruder" and cp.has_option(sec, "pressure_advance") and not (0.0 <= cp.getfloat(sec, "pressure_advance") <= 2.0):
            problems.append("[extruder]: pressure_advance out of range")
        if cp.has_option(sec, "sensor_type") and cp.get(sec, "sensor_type") not in sensor_types:
            problems.append(f"[{sec}]: sensor_type '{cp.get(sec, 'sensor_type')}' is not a Klipper built-in")
        for opt, val in cp.items(sec):
            if not opt.endswith("_pin") and opt != "pin":
                continue
            if "virtual_endstop" in val:
                if val.strip().startswith("probe:") and not cp.has_section("probe"):
                    problems.append(f"[{sec}] {opt}: homes on the probe but there is no [probe] section")
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


# ============================================================ entry points for other tools (firmware-in-the-loop etc.)
def electrical_loads(design) -> dict:
    """Worst-case electrical load model of a design: solve_circuit() on design.electrical.
    Returns {"wire_current": {wire: A}, "heaters": {device: {current_a, volts_at_heater, power_w, ...}},
    "loads_w": {...}, "dc_load_w", "board_current": {...}, "psu": {...}, "mains_current_a": {...}, "motors": {...}}."""
    el = design.electrical
    axis_motors(el, design)
    return solve_circuit(el, design)


def thermal_plants(design, circuit: dict | None = None) -> dict:
    """{firmware heater name ("extruder", "heater_bed"): HeaterPlant} for a design. A HeaterPlant holds the lumped
    ThermalNet (plant.net.step(T, power_vector, dt) advances it), the node the power enters, the node the sensor
    reads, the delivered power at 100 % duty, the Thermistor (adc <-> temperature) and the independent cut-offs.
    simulate_heater(plant, cfg, target, t_end, fault=...) runs it under Klipper's control laws."""
    return build_plants(design.electrical, design, circuit or electrical_loads(design))


def _one_line(text, limit: int = 300) -> str:
    """A provenance string as one config comment line (no line breaks, no '#', bounded)."""
    t = " ".join(str(text).replace("#", "no.").split())
    return t if len(t) <= limit else t[:limit - 3] + "..."


def klipper_config_path(design, out_root: str = "out") -> str:
    """Where the electrical verifier writes the generated printer.cfg for a design (stable path)."""
    return f"{out_root}/{design.name}/electrical/printer.cfg"
