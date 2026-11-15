"""Bent sheet parts in the tolerance simulation: bend angle and bend-line position scatter.

Before this module a laser-cut and bent part was toleranced like a flat one: the "sheet" class gives a feature a
position error of 0.08 mm and a mating face a flatness of 0.10 mm (mechloop/tolerance/process.py), wherever the feature
is on the part. A press-brake bend is far less accurate than the laser that cut the blank: the angle comes out about a
degree either way and the bend line lands a few tenths of a millimetre from where the flat pattern put it. A hole on a
flange therefore moves by (angle error) x (its distance from the bend line), plus the bend-line error.

How bends are found. The design language has no bend declaration and does not need one: a bent part is drawn as it is
made (inside radius r, outside radius r + t, see AGENT.md "Can each part be made?"), and the manufacture verifier
already recognises that geometry (dfm_sheet.bent_sheet: an inside and an outside cylinder about one axis whose radii
differ by the sheet thickness). The same recognition is used here, so the two verifiers agree on what is a bend. A
part declared `process="sheet"` that is not flat and in which no bend is recognised is reported
(`sheet_bends_not_recognised`): its flanges are then toleranced as a flat part's, which is optimistic.

Model. The part is cut through the middle of each bend into pieces (flanges). The largest piece is the datum flange.
Every other piece hangs from it through one or more bends; for each bend between a point and the datum flange the
point is turned about the bend's axis by the angle error and shifted by the bend-line error e: e along the parent
flange (the bend line moved) and -e along the child flange (the flat pattern keeps its developed length, so the
feature is that much closer to the bend). Small displacements, summed along the chain. Which flange is called the
datum does not matter to the result: the stack-up solves for the part's rigid position from the joints it has.

Values (one standard deviation, like the PROCESS table): angle 0.5 degree, bend line 0.19 mm. These are the usual
press-brake (air bending) shop tolerances of +/-1 degree and +/-0.38 mm (0.015 in) taken as two standard deviations,
the table's "a little pessimistic" convention. RECALLED CLASS VALUES: the usual figures quoted by sheet-metal services
(SendCutSend's bending guidelines give +/-1 degree and +/-0.015 in per bend; Protocase and Xometry quote +/-1 degree
and +/-0.25 to 0.5 mm). No document was fetched for them (sendcutsend.com was not reachable from the session that
wrote this), so they are marked `recalled` in the provenance below; replace them with the shop's own figures through
`design.manufacturing["bend_tolerance"] = {"angle_deg": ..., "line_mm": ...}` (one standard deviation each).
"""
from __future__ import annotations

import math
import zlib

import numpy as np

from .process import process_of

BEND_TOLERANCE = {
    "angle_sd_deg": 0.5, "line_sd_mm": 0.19,
    "provenance": "recalled class values, no document fetched: press-brake air bending +/-1 degree on the angle and "
                  "+/-0.38 mm (0.015 in) on the bend line per bend, taken as two standard deviations",
    "status": "recalled",
}

_CACHE: dict = {}


def bend_tolerance(design) -> dict:
    """The bend scatter in use: the class values above, or the design's own (design.manufacturing["bend_tolerance"])."""
    own = (getattr(design, "manufacturing", None) or {}).get("bend_tolerance")
    if not own:
        return dict(BEND_TOLERANCE)
    return {"angle_sd_deg": float(own.get("angle_deg", BEND_TOLERANCE["angle_sd_deg"])),
            "line_sd_mm": float(own.get("line_mm", BEND_TOLERANCE["line_sd_mm"])),
            "provenance": "declared by the design (design.manufacturing['bend_tolerance'])", "status": "declared"}


def _rot(v, axis, deg):
    """v turned about a unit axis by deg (Rodrigues)."""
    a = math.radians(deg)
    return v * math.cos(a) + np.cross(axis, v) * math.sin(a) + axis * (axis @ v) * (1 - math.cos(a))


def _dist(solid, p) -> float:
    from build123d import Vertex

    try:
        if solid.is_inside(tuple(float(x) for x in p), 1e-6):
            return 0.0
    except Exception:
        pass
    try:
        return float(solid.distance_to(Vertex(*[float(x) for x in p])))
    except Exception:
        return float("inf")


def find_bends(shape) -> dict | None:
    """The bends of a bent sheet part and the flanges they join, or None for a part with no recognisable bend.

    Returns {"thickness", "bends": [{"origin", "axis", "radius", "angle_deg", "length", "parent", "child", "u", "v"}],
    "pieces": [solid, ...], "base": index of the datum flange, "chain": {piece index: [bend indices from the datum]}}.
    `u` is the unit direction in the parent flange towards the bend line, `v` the direction in the child flange away
    from it. A bend whose two sides cannot be told apart (the cut did not separate the part there) is listed under
    "not_separated" and carries no scatter."""
    from build123d import Box, Location, Plane

    from ..verifiers import dfm_geom as G
    from ..verifiers import dfm_sheet

    key = id(shape.wrapped)
    if key in _CACHE and _CACHE[key][0] is shape.wrapped:
        return _CACHE[key][1]
    out = None
    try:
        cyls = G.cylinders(shape)
        # cheap test first: a bend needs a concave partial cylinder with a coaxial convex partner
        maybe = any(ci.concave and ci.angle <= 200 and any(
            (not co.concave) and co.radius > ci.radius + 0.05 and abs(co.angle - ci.angle) <= 3.0
            and G._same_axis(ci.origin, ci.axis, co.origin, co.axis) for co in cyls) for ci in cyls)
        bent = dfm_sheet.bent_sheet(shape, G.sample_surface(shape), cyls) if maybe else None
    except Exception:
        bent = None
    if bent is not None:
        t = float(bent["thickness"])
        cut = shape
        raw = []
        for b in bent["bends"]:
            a = np.asarray(b["axis"], dtype=float)
            a = a / np.linalg.norm(a)
            o = np.asarray(b["origin"], dtype=float)
            ci = b["inside"]
            mid_s = np.asarray(ci.mid, dtype=float)
            o_mid = o + a * 0.5 * (ci.lo + ci.hi)
            m = mid_s - (o + ((mid_s - o) @ a) * a)                 # radial direction to the middle of the bend arc
            m = m / np.linalg.norm(m)
            rin, phi = float(b["radius"]), float(b["angle"])
            w = np.cross(a, m)
            # a thin slab through the middle of the bend, only as large as the sheet's section there
            centre = o_mid + m * (rin + t / 2)
            slab = Box(t + 0.6, 0.02, (ci.hi - ci.lo) + 0.6).moved(
                Location(Plane(origin=tuple(centre), x_dir=tuple(m), z_dir=tuple(a))))
            try:
                cut = cut - slab
            except Exception:
                pass
            ends = []
            for sgn in (+1.0, -1.0):
                rad = _rot(m, a, sgn * phi / 2)                    # radial direction at this end of the arc
                tan = sgn * np.cross(a, rad)                        # leaves the arc into the flange
                ends.append((o_mid + rad * (rin + t / 2) + tan * 0.5, tan))
            raw.append({"origin": o_mid, "axis": a, "radius": rin, "angle_deg": phi, "length": float(ci.hi - ci.lo),
                        "ends": ends, "w": w})
        try:
            pieces = list(cut.solids())
        except Exception:
            pieces = []
        bends, lost = [], []
        if len(pieces) >= 2:
            base = int(np.argmax([p.volume for p in pieces]))
            links = []
            for k, b in enumerate(raw):
                side = [int(np.argmin([_dist(p, q) for p in pieces])) for q, _ in b["ends"]]
                if side[0] == side[1]:
                    lost.append(k)
                    continue
                links.append((k, side))
            # walk out from the datum flange
            chain = {base: []}
            grew = True
            while grew:
                grew = False
                for k, side in links:
                    for parent_end, child_end in ((0, 1), (1, 0)):
                        p_, c_ = side[parent_end], side[child_end]
                        if p_ in chain and c_ not in chain:
                            b = raw[k]
                            u = -b["ends"][parent_end][1]
                            v = b["ends"][child_end][1]
                            bends.append({"origin": b["origin"], "axis": b["axis"], "radius": b["radius"],
                                          "angle_deg": b["angle_deg"], "length": b["length"], "parent": p_, "child": c_,
                                          "u": u, "v": v})
                            chain[c_] = chain[p_] + [len(bends) - 1]
                            grew = True
            out = {"thickness": t, "bends": bends, "pieces": pieces, "base": base, "chain": chain,
                   "not_separated": len(lost) + sum(1 for i in range(len(pieces)) if i not in chain)}
        else:
            out = {"thickness": t, "bends": [], "pieces": pieces, "base": 0, "chain": {0: []}, "not_separated": len(raw)}
    _CACHE[key] = (shape.wrapped, out)
    return out


class PartBends:
    """The bend scatter of one bent part across n builds."""

    def __init__(self, name: str, found: dict, n: int, seed: int, tol: dict):
        self.name, self.found, self.n = name, found, n
        rng = np.random.default_rng([int(seed), zlib.crc32(name.encode())])      # its own stream: other draws do not move
        k = len(found["bends"])
        self.dth = np.radians(rng.normal(0.0, tol["angle_sd_deg"], (k, n)))
        self.de = rng.normal(0.0, tol["line_sd_mm"], (k, n))
        self._piece: dict = {}

    def piece_of(self, point) -> int:
        key = tuple(np.round(np.asarray(point, dtype=float), 3))
        if key not in self._piece:
            d = [_dist(p, key) for p in self.found["pieces"]]
            self._piece[key] = int(np.argmin(d))
        return self._piece[key]

    def _chain(self, point) -> list:
        return self.found["chain"].get(self.piece_of(point), [])

    def displacement(self, point) -> np.ndarray:
        """(n, 3): how far the bends move a point of the part (drawn position) relative to the datum flange."""
        p = np.asarray(point, dtype=float)
        out = np.zeros((self.n, 3))
        for k in self._chain(p):
            b = self.found["bends"][k]
            out += self.dth[k][:, None] * np.cross(b["axis"], p - b["origin"])[None, :]
            out += self.de[k][:, None] * (b["u"] - b["v"])[None, :]
        return out

    def rotation(self, point) -> np.ndarray:
        """(n, 3): small rotation vector of the flange the point is on, relative to the datum flange."""
        out = np.zeros((self.n, 3))
        for k in self._chain(point):
            out += self.dth[k][:, None] * self.found["bends"][k]["axis"][None, :]
        return out

    def summary(self) -> dict:
        f = self.found
        return {"bends": len(f["bends"]), "thickness_mm": round(f["thickness"], 3), "flanges": len(f["pieces"]),
                "bend_angles_deg": [round(b["angle_deg"], 1) for b in f["bends"]],
                **({"bends_not_separated": f["not_separated"]} if f.get("not_separated") else {})}


def bends_of(design, n: int, seed: int) -> tuple[dict, list]:
    """({part name: PartBends} for every sheet part with bends, [names of sheet parts that are not flat and in which
    no bend was recognised])."""
    tol = bend_tolerance(design)
    out, unknown = {}, []
    for c in design.components:
        try:
            if process_of(c) != "sheet":
                continue
        except ValueError:
            continue
        found = find_bends(c.shape)
        if found is not None and found["bends"]:
            out[c.name] = PartBends(c.name, found, n, seed, tol)
        if found is None or found.get("not_separated"):
            if found is not None or not _is_flat(c.shape):
                unknown.append(c.name)
    return out, unknown


def _is_flat(shape) -> bool:
    """True for a plate: one pair of parallel faces carries most of the area and their spacing is the smallest extent."""
    from build123d import GeomType

    try:
        acc: dict = {}
        total = 0.0
        for f in shape.faces():
            total += f.area
            if f.geom_type != GeomType.PLANE:
                continue
            nv = f.normal_at(f.center())
            nrm = np.array([nv.X, nv.Y, nv.Z])
            key = tuple(np.round(np.abs(nrm) if nrm[np.argmax(np.abs(nrm))] > 0 else np.abs(-nrm), 2))
            acc[key] = acc.get(key, 0.0) + f.area
        return bool(acc) and max(acc.values()) > 0.6 * total
    except Exception:
        return True
