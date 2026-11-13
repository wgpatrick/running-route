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
        Material("pla", 1240, 3500, 0.36, 50),
        Material("petg", 1270, 2100, 0.38, 45),
        Material("abs", 1040, 2200, 0.35, 40),
        Material("nylon_pa12", 1010, 1700, 0.39, 45),
        Material("brass", 8500, 100000, 0.34, 200),
        Material("rubber_gt2", 1200, 50, 0.48, 10),
    ]
}


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

    def mass(self) -> float:
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
    base: Optional[str] = None  # part everything else is assembled onto (default: largest fixed part)
    gravity: tuple[float, float, float] = (0.0, 0.0, -9810.0)  # mm/s^2

    # -- helpers ---------------------------------------------------------
    def add(self, name: str, shape: Shape, **kw) -> Component:
        if any(c.name == name for c in self.components):
            raise ValueError(f"duplicate component name: {name}")
        c = Component(name, shape, **kw)
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

    def bom_extra(self, sku: str, qty: int = 1, unit_cost_usd: float | None = None) -> None:
        e = self.bom_extras.setdefault(sku, {"qty": 0, "unit_cost_usd": unit_cost_usd})
        e["qty"] += qty

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
            self.add(nm(c.name), c.shape.moved(loc), material=c.material, body=bd(c.body), cots=c.cots,
                     sku=c.sku, mass_kg=c.mass_kg, ratings=dict(c.ratings), meta=meta, color=c.color)
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
            self.belts.append(Belt(nm(b.name), path, vec(b.axis), b.width, b.thickness, b.stock_length, b.adjust))
        for sku, e in other.bom_extras.items():
            self.bom_extra(sku, e["qty"], e["unit_cost_usd"])
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
