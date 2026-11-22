"""What a fixed camera sees: field-of-view and occlusion check of target points, and a render from the camera's own viewpoint.

A camera is a placed part whose interfaces give its optics (local frame of the part, moved to world by place()):
    "lens_centre": [(x, y, z)]      the entrance pupil (taken at the front of the lens)
    "lens_axis": [(x, y, z)]        a second point on the optical axis, in front of the lens
    "image_up": [(x, y, z)]         a point from lens_centre towards the image's top edge
    "fov_deg": (horizontal, vertical)
A part without them can be described by `optics` (the same keys in its local frame) and its meta["placement"].

view_check(design, cam, points, pose) -> {"inside": [...], "occluded": [(point, part)], ...}: each point must lie inside the
field of view (less `margin_deg` at each edge) and the straight line from it to the lens must meet no other part, with the
bodies at joint values `pose` (mechloop.geom.forward_kinematics). Parts are meshed (to_trimesh) and ray-cast with trimesh.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from .geom import forward_kinematics, to_trimesh


def camera_frame(c, optics: dict | None = None) -> dict:
    """World lens centre, unit optical axis, image up and right, and the FOV of camera part `c`."""
    itf = c.meta.get("interfaces") or {}
    if optics:
        M = np.array(c.meta["placement"], float)
        w = lambda p: M[:, :3] @ np.asarray(p, float) + M[:, 3]
        lc, la, lu = (w(optics[k][0]) for k in ("lens_centre", "lens_axis", "image_up"))
        fov = optics["fov_deg"]
    else:
        lc, la, lu = (np.asarray(itf[k][0], float) for k in ("lens_centre", "lens_axis", "image_up"))
        fov = itf["fov_deg"]
    f = la - lc
    f /= np.linalg.norm(f)
    u = lu - lc
    u -= f * (u @ f)
    u /= np.linalg.norm(u)
    r = np.cross(f, u)
    return {"centre": lc, "axis": f, "up": u, "right": r, "fov": tuple(float(x) for x in fov)}


def _scene(design, pose, exclude, near_box=None):
    T = forward_kinematics(design, pose or {})
    vs, fs, owner, n = [], [], [], 0
    for c in design.components:
        if c.name in exclude:
            continue
        bb = c.shape.bounding_box()
        M = T[c.body]
        if near_box is not None:
            lo = M[:3, :3] @ np.array([bb.min.X, bb.min.Y, bb.min.Z]) + M[:3, 3]
            hi = M[:3, :3] @ np.array([bb.max.X, bb.max.Y, bb.max.Z]) + M[:3, 3]
            lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
            if np.any(hi < near_box[0]) or np.any(lo > near_box[1]):
                continue
        tm = to_trimesh(c.shape, 0.3, 0.8)
        if not len(tm.faces):
            continue
        v = tm.vertices @ M[:3, :3].T + M[:3, 3]
        vs.append(v)
        fs.append(tm.faces + n)
        owner += [c.name] * len(tm.faces)
        n += len(v)
    import trimesh

    return trimesh.Trimesh(np.vstack(vs), np.vstack(fs), process=False), np.array(owner), T


def view_check(design, cam: str, points, pose=None, margin_deg: float = 1.0, exclude=(), optics=None) -> dict:
    """Points (world, at the pose's body positions: pass them already posed) against camera `cam` (its body posed too)."""
    c = design.get(cam)
    fr = camera_frame(c, optics)
    T = forward_kinematics(design, pose or {})
    M = T[c.body]
    ctr = M[:3, :3] @ fr["centre"] + M[:3, 3]
    f, u, r = (M[:3, :3] @ fr[k] for k in ("axis", "up", "right"))
    hx, hy = (math.tan(math.radians(a / 2 - margin_deg)) for a in fr["fov"])
    pts = np.asarray(points, float)
    d = pts - ctr
    z = d @ f
    tx, ty = (d @ r) / np.maximum(z, 1e-9), (d @ u) / np.maximum(z, 1e-9)
    inside = (z > 0) & (np.abs(tx) <= hx) & (np.abs(ty) <= hy)
    lo, hi = np.minimum(pts.min(0), ctr) - 1.0, np.maximum(pts.max(0), ctr) + 1.0
    mesh, owner, _ = _scene(design, pose, {cam, *exclude}, (lo, hi))
    dist = np.linalg.norm(d, axis=1)
    dirs = -d / dist[:, None]                     # from the point towards the lens
    occl = [None] * len(pts)
    loc, ri, ti = mesh.ray.intersects_location(pts, dirs, multiple_hits=True)
    for p_, i, t in zip(loc, ri, ti):
        s = np.linalg.norm(p_ - pts[i])
        if 0.05 < s < dist[i] - 0.5 and (occl[i] is None or s < occl[i][1]):
            occl[i] = (owner[t], s)
    ang = np.degrees(np.arctan(np.abs(tx))), np.degrees(np.arctan(np.abs(ty)))
    return {"centre": ctr, "axis": f, "fov": fr["fov"], "inside": inside, "occluded_by": [o[0] if o else None for o in occl],
            "angles_deg": np.stack(ang, 1), "n": len(pts),
            "n_ok": int(sum(1 for k in range(len(pts)) if inside[k] and occl[k] is None))}


def render_view(design, cam: str, path: Path, pose=None, size=(1600, 1050), optics=None, marks=None, exclude=()) -> Path:
    """The scene as camera `cam` sees it (pinhole, its vertical FOV; the window's aspect from the horizontal one), at `pose`.
    `marks`: world points drawn as red dots (e.g. the sheet's corners and the calibration target's)."""
    from .render import _pv

    pv = _pv()
    c = design.get(cam)
    fr = camera_frame(c, optics)
    T = forward_kinematics(design, pose or {})
    M = T[c.body]
    ctr = M[:3, :3] @ fr["centre"] + M[:3, 3]
    f, u = M[:3, :3] @ fr["axis"], M[:3, :3] @ fr["up"]
    hfov, vfov = fr["fov"]
    w = size[0]
    h = int(round(w * math.tan(math.radians(vfov / 2)) / math.tan(math.radians(hfov / 2))))
    pl = pv.Plotter(off_screen=True, window_size=(w, h))
    for o in design.components:
        if o.name == cam or o.name in exclude:
            continue
        tm = to_trimesh(o.shape, 0.3, 0.8)
        if not len(tm.faces):
            continue
        faces = np.hstack([np.full((len(tm.faces), 1), 3), tm.faces]).astype(np.int64)
        m = pv.PolyData(tm.vertices.copy(), faces)
        m.transform(T[o.body], inplace=True)
        pl.add_mesh(m, color=o.color or ("#8a8f98" if o.cots else "#4c78a8"), ambient=0.3)
    if marks is not None and len(marks):
        pl.add_mesh(pv.PolyData(np.asarray(marks, float)), color="red", point_size=10, render_points_as_spheres=True)
    pl.set_background("white")
    pl.camera.position = tuple(ctr)
    pl.camera.focal_point = tuple(ctr + 100.0 * f)
    pl.camera.up = tuple(u)
    pl.camera.view_angle = vfov
    pl.camera.clipping_range = (1.0, 2000.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.screenshot(str(path))
    pl.close()
    return path
