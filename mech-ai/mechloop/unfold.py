"""Flat patterns of bent sheet parts (single-bend parts unfolded exactly; more bends: refused, ship the STEP).

The part is cut at the two tangent planes of its bend (found by mechloop.tolerance.bends.find_bends), the child flange is
turned back about the bend's axis onto the parent's plane and moved on by the bend allowance BA = theta (r + K t) (r the
inside radius, t the thickness, K the shop's K-factor: SendCutSend publishes 0.37 for its press brakes), and the bend's
sector is replaced by a flat strip BA long. The flat profile is the outer skin of that solid, written as a DXF with the cut
on layer CUT and the bend line (the middle of the bend allowance) on layer BEND.

`unfold_check` compares area x thickness with the part's volume: a flat whose area is off by more than 2 % is not the
part (a top face exported as the 'flat' of a bent part was 60 to 95 % short; this check is what stops that recurring).
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

K_FACTOR = {"sendcutsend": 0.37}       # SendCutSend's published K-factor (docs/SOLIDCRAFT_TRIAL.md); other shops: same until read
K_DEFAULT = 0.37


def _rot_about(v, axis, ang):
    axis = axis / np.linalg.norm(axis)
    return v * math.cos(ang) + np.cross(axis, v) * math.sin(ang) + axis * (axis @ v) * (1 - math.cos(ang))


def unfold(shape, k_factor: float = K_DEFAULT) -> dict:
    """{"bends": n, "flat": solid (flat, in world space), "plane": (origin, x_dir, z_dir) of its outer skin, "bend_lines": [(p0, p1)],
    "bend_allowance_mm", "k_factor", "thickness", "angle_deg", "radius"} for a one-bend part; {"bends": 0} for a flat part;
    {"bends": n, "error": "..."} otherwise."""
    from build123d import Box, Keep, Location, Plane, Pos

    from .tolerance.bends import find_bends

    fb = find_bends(shape)
    if fb is None or not fb["bends"]:
        return {"bends": 0}
    if len(fb["bends"]) != 1:
        return {"bends": len(fb["bends"]), "error": f"{len(fb['bends'])} bends: only one-bend parts are unfolded here; ship the STEP and mark the bends"}
    b = fb["bends"][0]
    t, r, phi = float(fb["thickness"]), float(b["radius"]), math.radians(float(b["angle_deg"]))
    a = np.asarray(b["axis"], float)
    a /= np.linalg.norm(a)
    o = np.asarray(b["origin"], float)
    tan_p, tan_c = -np.asarray(b["u"], float), np.asarray(b["v"], float)     # out of the arc into the parent / child flange
    pieces = fb["pieces"]

    def rad_for(tan, piece):
        rd = np.cross(a, tan)
        rd /= np.linalg.norm(rd)
        cen = np.array(tuple(piece.center()))
        return rd if (cen - o) @ rd > 0 else -rd

    rad_p, rad_c = rad_for(tan_p, pieces[b["parent"]]), rad_for(tan_c, pieces[b["child"]])

    def side(tan):
        return shape.split(Plane(origin=tuple(o), z_dir=tuple(tan)), keep=Keep.TOP)

    par, chi = side(tan_p), side(tan_c)
    # turn the child about the bend's axis so its arc end lands on the parent's, then move it on by the bend allowance
    cr = np.cross(rad_c, rad_p)
    ang = math.atan2(float(cr @ a), float(rad_c @ rad_p))
    ba = phi * (r + k_factor * t)
    from build123d import Axis, Vector

    chi = chi.rotate(Axis(tuple(o), tuple(a)), math.degrees(ang))
    chi = Pos(*(-tan_p * ba)) * chi
    strip = Box(t, ba, float(b["length"]) + 0.0).moved(Location(Plane(origin=tuple(o + rad_p * (r + t / 2) - tan_p * ba / 2),
                                                                        x_dir=tuple(rad_p), z_dir=tuple(a))))
    flat = par.fuse(strip, chi).clean()
    sk_o = o + rad_p * (r + t)
    bl_mid = sk_o - tan_p * (ba / 2)
    half = a * float(b["length"]) / 2
    return {"bends": 1, "flat": flat, "plane": (sk_o, -tan_p, rad_p), "bend_lines": [(bl_mid - half, bl_mid + half)],
            "bend_allowance_mm": round(ba, 3), "k_factor": k_factor, "thickness": t, "angle_deg": math.degrees(phi), "radius": r}


def write_flat_dxf(res: dict, path) -> dict:
    """The unfolded profile (outer skin) as a DXF: CUT and BEND layers. Returns {"area_mm2", "extent"}."""
    from build123d import ExportDXF, Line, Plane, Unit, Vector

    o, xd, zd = res["plane"]
    pl = Plane(origin=Vector(*o), x_dir=Vector(*xd), z_dir=Vector(*zd))
    faces = [f for f in res["flat"].faces() if f.geom_type.name == "PLANE"
             and abs(abs(float(np.dot(np.array(tuple(f.normal_at(f.center()))), zd))) - 1) < 1e-4
             and abs(float(np.dot(np.array(tuple(f.center())) - o, zd))) < 0.02]
    if not faces:
        raise ValueError("no outer skin face found on the unfolded solid")
    from build123d import Pos

    loc = []
    for f in faces:                      # each skin face into the plane's frame, snapped to z = 0 (the pieces meet within microns)
        lf = pl.to_local_coords(f)
        loc.append(Pos(0, 0, -lf.center().Z) * lf)
    prof = loc[0] if len(loc) == 1 else loc[0].fuse(*loc[1:]).clean()
    ex = ExportDXF(unit=Unit.MM)
    ex.add_layer("CUT")
    ex.add_layer("BEND")
    area = sum(f.area for f in prof.faces())
    ex.add_shape(prof, layer="CUT")
    for p0, p1 in res["bend_lines"]:
        ex.add_shape(pl.to_local_coords(Line(tuple(p0), tuple(p1))), layer="BEND")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ex.write(str(path))
    bb = prof.bounding_box()
    return {"area_mm2": round(area, 2), "extent_mm": [round(bb.size.X, 3), round(bb.size.Y, 3)], "faces": len(prof.faces())}


def unfold_check(area_mm2: float, thickness: float, volume_mm3: float, tol: float = 0.02) -> dict:
    """Flat area x thickness against the part's volume (holes and the bend allowance included)."""
    ratio = area_mm2 * thickness / volume_mm3 if volume_mm3 else float("nan")
    return {"area_x_t_over_volume": round(ratio, 4), "ok": abs(ratio - 1) <= tol, "tolerance": tol}
