"""Design model: what the agent writes, and what every verifier reads.

Units: mm, N, MPa, kg (mass), degrees for hinge joints. All shapes are given in
the assembled "home" pose in one world frame.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence

from build123d import Face, Part, Shape


@dataclass(frozen=True)
class Material:
    name: str
    density: float  # kg/m^3
    E: float  # MPa
    nu: float
    yield_mpa: float


MATERIALS = {
    m.name: m
    for m in [
        Material("al6061", 2700, 68900, 0.33, 276),
        Material("steel", 7850, 200000, 0.29, 250),
        Material("stainless304", 8000, 193000, 0.29, 215),
        Material("al5052", 2680, 70300, 0.33, 193),  # H32: the aluminium sheet that bends (6061-T6 cracks)
        Material("pla", 1240, 3500, 0.36, 50),
        Material("petg", 1270, 2100, 0.38, 45),
        Material("abs", 1040, 2200, 0.35, 40),
        Material("nylon_pa12", 1010, 1700, 0.39, 45),
        Material("brass", 8500, 100000, 0.34, 200),
        Material("rubber_gt2", 1200, 50, 0.48, 10),
        # Cast aluminium tooling plate (stress-relieved, milled both faces): the flat, stable plate for a print bed.
        # MIC-6: yield 105 MPa (15 ksi) from distributor data seen in search snippets; density (0.101 lb/in^3) and
        # E (10.3 Msi) recalled. ATP-5 (5083-type): density, E (10.1 Msi = 70,000 MPa) and yield from Vista Metals' product
        # sheet (vendor_docs/ATP5_datasheet.pdf); Poisson's ratio typical. Sources and what is confirmed:
        # mechloop/parts/vendor/cast_tooling_plate.json. Thermal expansion 23.6e-6 /K (both), not in this table.
        # al_mic6 since 2026-11-15: E 71,000 and yield 105 are the Alcoa MIC 6 brochure's typical figures (tensile 166 MPa,
        # 142 W/m.K, 23.6e-6 /K); DENSITY 2800 IS NOT IN THE BROCHURE (a third-party report's input; kept), nu is typical.
        Material("al_mic6", 2800, 71000, 0.33, 105),
        Material("al_atp5", 2660, 70000, 0.33, 124),
    ]
}


_PLASTICS = ("pla", "petg", "abs", "nylon_pa12")


@dataclass
class Component:
    """One part instance in the assembly."""

    name: str
    shape: Shape
    material: str = "al6061"
    body: str = "world"  # rigid body this part rides on (see Joint)
    cots: bool = False  # off-the-shelf: never modified, checked against ratings
    sku: Optional[str] = None
    mass_kg: Optional[float] = None  # override (COTS parts with simplified geometry)
    ratings: dict = field(default_factory=dict)  # e.g. {"holding_torque_nmm": 450}
    meta: dict = field(default_factory=dict)
    color: Optional[str] = None
    # How the part is made: "printed" (FDM), "machined" (CNC), "sheet" (laser / waterjet cut, optionally bent),
    # "extrusion", "purchased". None: chosen from the material (see tolerance/process.py). Kept in meta["process"].
    process: Optional[str] = None
    # Detailed geometry of the same part in the same place (vendor STEP for catalog parts), for display and export.
    # Verifiers work on `shape`; the geometry verifier checks `shape` against `detail` (see parts/vendor_cad.py).
    detail: Optional[Shape] = None

    def __post_init__(self):
        if self.process:
            self.meta["process"] = self.process
        elif self.meta.get("process"):
            self.process = self.meta["process"]

    def mass(self) -> float:
        """Mass, kg. A printed part (process "printed", or a plastic with no process stated) is its shell plus its
        infilled core, from its print settings (mechloop.printsettings: meta["print"], else the design's
        manufacturing["print_settings"], else the stated default); every other part is solid."""
        if self.mass_kg is not None:
            return self.mass_kg
        solid = self.shape.volume * 1e-9 * MATERIALS[self.material].density
        if not self.cots and self.material in _PLASTICS:
            from .printsettings import solid_fraction

            return solid * solid_fraction(self)
        return solid

    def solid_mass(self) -> float:
        """Mass as if the part were solid (for a printed part, 100 % infill)."""
        if self.mass_kg is not None:
            return self.mass_kg
        return self.shape.volume * 1e-9 * MATERIALS[self.material].density


@dataclass
class Joint:
    """A 1-DOF joint between two rigid bodies, defined in the home pose, world frame."""

    name: str
    kind: str  # "slide" (mm) or "hinge" (deg)
    parent: str
    child: str
    axis: tuple[float, float, float]
    origin: tuple[float, float, float] = (0.0, 0.0, 0.0)
    range: tuple[float, float] = (0.0, 0.0)  # travel relative to home (home = 0)
    # Drive: max force (N, slide) or torque (N*mm, hinge) available at the joint.
    max_effort: Optional[float] = None
    max_speed: Optional[float] = None  # mm/s or deg/s
    max_accel: Optional[float] = None  # mm/s^2 or deg/s^2
    # Motor + transmission, resolved to max_effort by the ratings verifier, e.g.
    # {"motor": "x_motor", "kind": "belt", "pulley_teeth": 20} or
    # {"motor": ["z1", "z2"], "kind": "leadscrew", "lead": 8, "efficiency": 0.4}
    drive: Optional[dict] = None
    min_drive_margin: float = 1.5  # available / required effort; friction is not modelled, so keep > 1
    reflected_inertia: float = 0.0  # motor rotor inertia seen at the joint (filled in from the drive)
    # Mechanical over-travel beyond `range`, as (past the low end, past the high end), both >= 0. `range` is the WORKING
    # range (what programs, prints and the firmware's working coordinates use); the joint can physically move over
    # `mechanical_range`. Use it for travel that exists but is not working travel: a bed that can rise past the nominal
    # nozzle plane (what a probe's z_offset and a bed mesh need: the firmware's position_min goes negative by it), or
    # room past an endstop's nominal trigger point. Collisions, guide run-off, belts and cables are checked over the
    # mechanical range. A printer's Z over-travel towards the nozzle is allowance for where the nozzle really ends up
    # relative to the bed, not a motion through the nozzle: there the bed meeting the nozzle tip is by declaration not
    # a collision, parts on the nozzle's body ride with it and are checked at nozzle contact plus their toolhead
    # margin (mechloop.tolerance.toolhead), and every other pair is checked through the whole over-travel.
    overtravel: tuple[float, float] = (0.0, 0.0)

    @property
    def mechanical_range(self) -> tuple[float, float]:
        lo, hi = self.range
        a, b = (tuple(self.overtravel) + (0.0, 0.0))[:2]
        return (lo - max(float(a), 0.0), hi + max(float(b), 0.0))


@dataclass
class Fastener:
    """A threaded fastener, for assemblability/tool-access checks."""

    name: str  # must match a Component name
    axis: tuple[float, float, float]  # direction the screw is removed along (head side)
    head_center: tuple[float, float, float]
    tool_diameter: float = 6.0  # driver/hex-key shaft envelope
    tool_length: float = 60.0
    clamps: Sequence[str] = ()  # components it holds together


@dataclass
class LoadCase:
    """A static structural check on one component."""

    name: str
    component: str
    fixed: Callable[[Face], bool]  # faces fully fixed
    loaded: Callable[[Face], bool]  # faces carrying the load
    force: tuple[float, float, float]  # total N, distributed over loaded faces
    min_fos: float = 2.0
    max_deflection: Optional[float] = None  # mm
    mesh_size: Optional[float] = None


@dataclass
class ModalCase:
    """Natural-frequency check on one component (resonance / stiffness-to-mass)."""

    name: str
    component: str
    fixed: Callable[[Face], bool]
    min_frequency_hz: float
    mesh_size: Optional[float] = None


@dataclass
class AssemblyCase:
    """Static check across several parts meshed together and bonded wherever they touch.

    `fixed` and `loaded` are (component name, face predicate). Deflection is the
    largest displacement anywhere, or at `probe` (a world point) when given.
    Bonded contact is stiffer than bolted joints: treat deflection as a lower bound.
    """

    name: str
    components: Sequence[str]
    fixed: Sequence[tuple]  # [(component, predicate), ...]
    loaded: tuple  # (component, predicate)
    force: tuple[float, float, float]
    max_deflection: Optional[float] = None
    min_fos: Optional[float] = None
    probe: Optional[tuple[float, float, float]] = None
    mesh_size: Optional[float] = None


@dataclass
class Belt:
    """A timing belt routed around pulleys, optionally with its two ends clamped.

    `path` is the route in order. Each node is either
      ("pulley", component_name, "ccw" | "cw")   belt wraps that pulley in that sense, seen
                                                  looking down the belt's `axis` direction
      ("anchor", body_name, (x, y, z))            belt end clamped at a world point on that body
    A closed loop has only pulleys; an open belt starts and ends with an anchor.
    """

    name: str
    path: Sequence[tuple]
    axis: tuple[float, float, float] = (0.0, 0.0, 1.0)  # pulley axis direction
    width: float = 6.0
    thickness: float = 1.4
    stock_length: Optional[float] = None  # closed-loop belt length you intend to buy
    adjust: float = 3.0  # mm of tensioner/slot adjustment available
    # Installation tension per span, N (what the tensioner is set to). None: Gates' minimum recommended installation
    # tension for the width (mechloop/parts/vendor/gates_gt2.json: 6.2 / 9.3 / 14.2 / 18.7 N for 4 / 6 / 9 / 12 mm).
    # The ratings verifier compares the pull it puts on a motor shaft with the motor's radial load limit.
    tension: Optional[float] = None
    # Pulleys on a motor shaft whose shaft end runs in an outboard support bearing (a catalog bearing on the same
    # axis beyond the pulley): the belt pull is then not an overhung load on the motor.
    outboard_support: Sequence[str] = ()


# Join kinds that hold two parts together across their contact face and let them slide along it (no shear carried):
# a magnet-held sheet, or any contact declared as sliding. The thermal analysis ties such a pair in the normal
# direction only; every other verifier treats the join as it treats any declared join (the parts are held).
SLIDING_JOIN_PREFIXES = ("magnet", "sliding")


@dataclass
class ThermalCase:
    """Thermal growth of several parts meshed together.

    temps: {part name: temperature rise in K}; "*" sets the default for parts not named.
    probes: {label: (x, y, z)} points whose movement is reported.
    gaps: {name: (probe_a, probe_b, "x"|"y"|"z", limit_mm or None)} change in (a - b) along an axis.
    flatness: (part, "x"|"y"|"z", limit_mm or None) bow of that part's top face along the axis.

    Parts are bonded where they touch, except a pair joined with a sliding kind (`design.join(a, b, "magnet")` or
    `"sliding"`): that contact carries normal load and slides in its plane, so a steel sheet held by a magnet does
    not bend the plate under it as a bonded bimetal would. A kind that starts with "sliding free" is not located in
    its plane at all (only the normal tie): a washer held on a plate by a spring.
    stick: pairs of part names whose sliding contact is taken as stuck (bonded) in THIS case: the bound where friction
    never lets go.
    """

    name: str
    components: Sequence[str]
    fixed: Sequence[tuple]
    temps: dict
    probes: dict = field(default_factory=dict)
    gaps: dict = field(default_factory=dict)
    flatness: Optional[tuple] = None
    mesh_size: Optional[float] = None
    stick: Sequence[tuple] = ()


@dataclass
class Cable:
    """A cable or hose between two points, usually one on a moving body.

    a, b: (body name, (x, y, z)) at the home pose. length is the cable length between the two clamps.
    """

    name: str
    a: tuple
    b: tuple
    length: float
    min_bend_radius: float = 15.0


@dataclass
class Adjustment:
    """A way the built machine can absorb error: a slot, a levelling screw, a firmware offset.

    kind: "bed_level" (three or four screws under the bed), "z_offset" (firmware/endstop offset),
    "belt_tension" (slot on a motor or idler), "rail_align" (rail screwed down while a gauge or the
    carriage plate sets its position), "float" (a mount left free in one direction, e.g. a floating nut),
    "endstop" (a switch on a slot, set against its striker at assembly: takes the stack-up out of the endstop window).
    `joint` names the axis it serves where that matters. range_mm is +/- travel available.
    """

    name: str
    kind: str
    range_mm: float
    joint: Optional[str] = None
    note: str = ""
    # How it is moved and what holds it once set (practice rule LOC-006): mover e.g. "M3 jack screw", "slot by hand";
    # lock e.g. "two M3 screws" or ["jam nut", "thread adhesive"]. A mechanical adjustment without a lock drifts.
    mover: str = ""
    lock: object = ""


@dataclass
class Requirement:
    """A named, executable acceptance test. `check` returns (ok, detail)."""

    name: str
    check: Callable[["Design"], tuple[bool, str]]


@dataclass
class Design:
    name: str
    components: list[Component] = field(default_factory=list)
    joints: list[Joint] = field(default_factory=list)
    fasteners: list[Fastener] = field(default_factory=list)
    loadcases: list[LoadCase] = field(default_factory=list)
    modalcases: list[ModalCase] = field(default_factory=list)
    assemblycases: list[AssemblyCase] = field(default_factory=list)
    thermalcases: list[ThermalCase] = field(default_factory=list)
    belts: list[Belt] = field(default_factory=list)
    requirements: list[Requirement] = field(default_factory=list)
    # Pairs allowed to overlap (threads, press fits): {frozenset({a, b}): max_volume_mm3}
    allowed_overlaps: dict = field(default_factory=dict)
    # Pairs that must keep a minimum gap: {frozenset({a, b}): min_gap_mm}
    min_clearances: dict = field(default_factory=dict)
    # Non-screw joints between two parts: {frozenset({a, b}): kind} (press, bond, clamp, set_screw, tnut...)
    joins: dict = field(default_factory=dict)
    # Hardware bought but not modelled as geometry (T-nuts, set screws): {sku: {qty, unit_cost_usd}}
    bom_extras: dict = field(default_factory=dict)
    envelope: Optional[tuple[float, float, float]] = None  # max overall X, Y, Z size
    max_mass_kg: Optional[float] = None
    # Motion program run in forward simulation: [{"to": {joint: value}, "speed": mm/s}, ...]
    program: list = field(default_factory=list)
    tracking_tolerance: float = 0.2  # mm (or deg) allowed between commanded and simulated position
    tool_point: Optional[tuple] = None  # (body, (x, y, z)) traced in the motion render
    adjustments: list[Adjustment] = field(default_factory=list)
    cables: list[Cable] = field(default_factory=list)
    # homing: [{"joint": name, "switch": part, "at": "min"|"max"}] or {"joint": name, "sensorless": True};
    # a bed probe that homes Z: {"joint": "z", "probe": <probe part>, "at": "min"|"max"} (the part needs a
    # 'sensing_face' interface and an electrical template of kind "probe"; checked by the subsystems verifier)
    endstops: list = field(default_factory=list)
    # Groups built on the bench and installed as one unit: {name: [part names]}
    subassemblies: dict = field(default_factory=dict)
    # Separate free-standing units of the fixed world (an electronics box on the bench, joined to the machine only by
    # cables): {name: [part names]}. Such a unit need not touch or be fastened to the rest; its own parts must still
    # hold together (interference verifier). Screws and nuts of the unit need not be listed.
    free_standing: dict = field(default_factory=dict)
    # A printer design declares how to print on it: {"bed": part, "x"/"y"/"z": joint names,
    # "stiffness": {"x": <AssemblyCase name>, "y": ...}} so the digital twin runs as a verifier
    printer: Optional[dict] = None
    base: Optional[str] = None  # part everything else is assembled onto (default: largest fixed part)
    # How custom parts are made, for the manufacture verifier: {"shop": "generic" | "sendcutsend",
    # "limits": {rule id: value}, "printer": {"build_volume": (x, y, z), "nozzle": 0.4, "layer": 0.2},
    # "cnc": {"tools": [3, 6, 10]}, "sheet": {"method": "laser" | "waterjet" | "router"}}
    manufacturing: dict = field(default_factory=dict)
    gravity: tuple[float, float, float] = (0.0, 0.0, -9810.0)  # mm/s^2
    # Electrical system (mechloop.electrical.Electrical): devices, wires, looms, firmware settings. Checked by the
    # electrical verifier; its motor data replaces the catalog's class torque curve (see ratings.resolve_drives).
    electrical: Optional[object] = None
    # Practice verifier (mechloop/verifiers/practice.py): per-rule control, {"disable": [rule ids], "severity":
    # {rule id: "info" | "warning" | "error"}, "limits": {"FST-050.min_edge_d": 1.2}}.
    practice: dict = field(default_factory=dict)
    # Declared exceptions to practice rules, each {"rule", "parts", "reason"}: see `waive`.
    waivers: list = field(default_factory=list)
    # A design still being explored, not presented as buildable: practice DG-07 (purchased parts that are not real, orderable
    # products with the maker's CAD and ratings: placeholders) reports warnings instead of errors. Default: buildable, errors.
    exploratory: bool = False
    # T-nut type for every add_screw(..., tnut=True) and corner-bracket leg on a slot. None (older designs): T-nuts and
    # bracket screws are BOM lines only. "drop_in": each is a drawn catalogue part (parts.tslot.tnut_2020, post-assembly
    # insertion), bracket screws are real screws, and the T-slot screw checks of the interference verifier run.
    tnut_style: Optional[str] = None
    # A design frozen for release (to be built / ordered): `mechloop verify --tier quick|affected` runs a full verify on it
    # anyway, with no reused results (mechloop.incremental).
    release: bool = False

    # -- helpers ---------------------------------------------------------
    def waive(self, rule: str, parts=None, reason: str = "") -> None:
        """Declare a deliberate exception to a practice rule. `rule` is the rule id ("DG-01", "FST-070"), its finding
        code ("printed_load_path") or either with a "practice." prefix. `parts`: a part name, a list of names, or
        fnmatch patterns ("nut_pin*"); a finding is waived when any part it names matches (for a screw rule the screw's
        name); None waives the rule for the whole design. `reason` is required: a waiver whose
        reason is under 20 characters is itself an error, and one that suppresses nothing is a warning."""
        if isinstance(parts, str):
            parts = [parts]
        self.waivers.append({"rule": str(rule), "parts": list(parts) if parts is not None else None, "reason": str(reason or "")})

    def add(self, name: str, shape: Shape, **kw) -> Component:
        if any(c.name == name for c in self.components):
            raise ValueError(f"duplicate component name: {name}")
        c = Component(name, shape, **kw)
        import weakref

        object.__setattr__(c, "_design_ref", weakref.ref(self))     # the design's print settings reach the part's mass
        self.components.append(c)
        return c

    def get(self, name: str) -> Component:
        for c in self.components:
            if c.name == name:
                return c
        raise KeyError(name)

    def allow_overlap(self, a: str, b: str, max_volume: float = 1e9) -> None:
        self.allowed_overlaps[frozenset((a, b))] = max_volume

    def join(self, a: str, b: str, kind: str = "bond") -> None:
        self.joins[frozenset((a, b))] = kind

    def slides_on(self, a: str, b: str) -> bool:
        """True when the declared join between a and b carries load across the contact but lets the two slide along
        it: a join whose kind starts with "magnet" (a print sheet on a magnetic base) or "sliding" (any declared
        sliding contact: `design.join(a, b, "sliding")`). See SLIDING_JOIN_PREFIXES."""
        kind = str(self.joins.get(frozenset((a, b)), "")).strip().lower()
        return kind.startswith(SLIDING_JOIN_PREFIXES)

    def bom_extra(self, sku: str, qty: int = 1, unit_cost_usd: float | None = None, real_part: dict | None = None,
                  stage: int | None = None) -> None:
        """A bought item with no geometry. real_part: the orderable product (maker, mpn, sellers ...; practice DG-07).
        stage: the build stage it is first needed at (staged Build 1: 1 frame/bay/bed/Z, 2 gantry/toolhead, 3 feedback)."""
        e = self.bom_extras.setdefault(sku, {"qty": 0, "unit_cost_usd": unit_cost_usd})
        e["qty"] += qty
        if stage is not None and (e.get("stage") is None or stage < e["stage"]):
            e["stage"] = int(stage)
        if real_part:
            e["real_part"] = dict(real_part)

    def require_clearance(self, a: str, b: str, gap: float) -> None:
        self.min_clearances[frozenset((a, b))] = gap

    def include(self, other: "Design", loc=None, prefix: str = "") -> None:
        """Bring another design into this one as a sub-assembly, moved by `loc` and with
        every name prefixed. Parts, bodies, joints, fasteners, joins, belts and BOM extras
        come across. Load/modal/assembly cases come across only when `loc` is None (their
        face predicates are written in the other design's coordinates); requirements and
        the motion program are not copied."""
        import copy

        import numpy as np
        from build123d import Location

        moved = loc is not None
        loc = loc or Location()
        trsf = loc.wrapped.Transformation()
        M = np.array([[trsf.Value(i, j) for j in range(1, 5)] for i in range(1, 4)])

        def pt(p):
            return tuple(float(x) for x in M[:, :3] @ np.array(p, dtype=float) + M[:, 3])

        def vec(v):
            return tuple(float(x) for x in M[:, :3] @ np.array(v, dtype=float))

        def nm(n):
            return prefix + n

        def bd(b):
            return b if b == "world" else prefix + b

        for c in other.components:
            meta = copy.deepcopy(c.meta)
            if "interfaces" in meta:
                meta["interfaces"] = {k: [pt(p) for p in v] if isinstance(v, list) else v
                                      for k, v in meta["interfaces"].items()}
            if "threads_into" in meta:
                meta["threads_into"] = [nm(t) for t in meta["threads_into"]]
            if "guides" in meta:
                meta["guides"] = nm(meta["guides"])
            if "placement" in meta:
                P = np.vstack([np.array(meta["placement"], dtype=float), [0, 0, 0, 1]])
                meta["placement"] = (np.vstack([M, [0, 0, 0, 1]]) @ P)[:3].tolist()
            self.add(nm(c.name), c.shape.moved(loc), material=c.material, body=bd(c.body), cots=c.cots,
                     sku=c.sku, mass_kg=c.mass_kg, ratings=dict(c.ratings), meta=meta, color=c.color,
                     detail=c.detail.moved(loc) if c.detail is not None else None)
        for j in other.joints:
            j2 = copy.copy(j)
            j2.name, j2.parent, j2.child = nm(j.name), bd(j.parent), bd(j.child)
            j2.axis, j2.origin = vec(j.axis), pt(j.origin)
            if j.drive:
                d = dict(j.drive)
                for k in ("motor", "pulley", "screw", "nut", "coupler"):
                    if k in d:
                        d[k] = [nm(x) for x in d[k]] if isinstance(d[k], (list, tuple)) else nm(d[k])
                j2.drive = d
            self.joints.append(j2)
        for f in other.fasteners:
            self.fasteners.append(Fastener(nm(f.name), vec(f.axis), pt(f.head_center), f.tool_diameter,
                                           f.tool_length, tuple(nm(x) for x in f.clamps)))
        for src, dst in ((other.joins, self.joins), (other.allowed_overlaps, self.allowed_overlaps),
                         (other.min_clearances, self.min_clearances)):
            for k, v in src.items():
                dst[frozenset(nm(x) for x in k)] = v
        for b in other.belts:
            path = [(n[0], nm(n[1]), n[2]) if n[0] == "pulley" else (n[0], bd(n[1]), pt(n[2])) for n in b.path]
            self.belts.append(Belt(nm(b.name), path, vec(b.axis), b.width, b.thickness, b.stock_length, b.adjust, b.tension,
                                   tuple(nm(x) for x in b.outboard_support)))
        for sku, e in other.bom_extras.items():
            self.bom_extra(sku, e["qty"], e["unit_cost_usd"])
        for w in other.waivers:
            self.waivers.append({**w, "parts": [nm(p) for p in w["parts"]] if w.get("parts") is not None else None})
        if not moved:
            for lst_o, lst_s in ((other.loadcases, self.loadcases), (other.modalcases, self.modalcases)):
                for case in lst_o:
                    c2 = copy.copy(case)
                    c2.name, c2.component = nm(case.name), nm(case.component)
                    lst_s.append(c2)
            for ac in other.assemblycases:
                a2 = copy.copy(ac)
                a2.name = nm(ac.name)
                a2.components = [nm(x) for x in ac.components]
                a2.fixed = [(nm(n), p) for n, p in ac.fixed]
                a2.loaded = (nm(ac.loaded[0]), ac.loaded[1])
                self.assemblycases.append(a2)

    def bodies(self) -> dict[str, list[Component]]:
        out: dict[str, list[Component]] = {}
        for c in self.components:
            out.setdefault(c.body, []).append(c)
        return out

    def total_mass(self) -> float:
        return sum(c.mass() for c in self.components)
