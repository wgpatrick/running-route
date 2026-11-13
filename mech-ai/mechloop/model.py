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

    def bodies(self) -> dict[str, list[Component]]:
        out: dict[str, list[Component]] = {}
        for c in self.components:
            out.setdefault(c.body, []).append(c)
        return out

    def total_mass(self) -> float:
        return sum(c.mass() for c in self.components)
