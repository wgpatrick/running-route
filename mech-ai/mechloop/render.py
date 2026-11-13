"""Headless renders for the human (and as a secondary signal for the agent)."""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from .geom import forward_kinematics, to_trimesh
from .model import Design

PALETTE = ["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2", "#eeca3b", "#b279a2",
           "#ff9da6", "#9d755d", "#bab0ac"]
COTS_COLOR = "#8a8f98"


def _pv():
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv
    import vtk

    vtk.vtkObject.GlobalWarningDisplayOff()
    pv.OFF_SCREEN = True
    return pv


def _polys(design: Design, pv):
    out = []
    i = 0
    for c in design.components:
        tm = to_trimesh(c.shape)
        faces = np.hstack([np.full((len(tm.faces), 1), 3), tm.faces]).astype(np.int64)
        color = c.color or (COTS_COLOR if c.cots else PALETTE[i % len(PALETTE)])
        if not c.cots and not c.color:
            i += 1
        out.append((c, pv.PolyData(tm.vertices.copy(), faces), color))
    return out


def _add(pl, polys, T):
    for c, pd, color in polys:
        m = pd.copy()
        m.transform(T[c.body], inplace=True)
        pl.add_mesh(m, color=color, smooth_shading=False, show_edges=False,
                    specular=0.2, ambient=0.25)
        edges = m.extract_feature_edges(feature_angle=35)
        if edges.n_points:
            pl.add_mesh(edges, color="#1b1b1b", line_width=1)


def render_views(design: Design, path: Path, q: dict | None = None, size=(1600, 1200)) -> Path:
    pv = _pv()
    polys = _polys(design, pv)
    T = forward_kinematics(design, q or {})
    pl = pv.Plotter(off_screen=True, shape=(2, 2), window_size=size)
    views = [("iso", None), ("front (-Y)", "xz"), ("top (+Z)", "xy"), ("right (+X)", "yz")]
    for k, (title, plane) in enumerate(views):
        pl.subplot(k // 2, k % 2)
        _add(pl, polys, T)
        pl.add_text(title, font_size=10, color="black")
        if plane is None:
            pl.view_isometric()
        elif plane == "xz":
            pl.view_xz()
        elif plane == "xy":
            pl.view_xy()
        else:
            pl.view_yz()
        if plane:
            pl.enable_parallel_projection()
        pl.show_axes()
        pl.set_background("white")
    path.parent.mkdir(parents=True, exist_ok=True)
    pl.screenshot(str(path))
    pl.close()
    return path


def render_motion(design: Design, path: Path, frames_per_joint: int = 16, size=(800, 600)) -> Path | None:
    """Animated GIF: each joint travels across its range in turn."""
    joints = [j for j in design.joints if j.range[0] != j.range[1]]
    if not joints:
        return None
    import imageio.v2 as imageio

    pv = _pv()
    polys = _polys(design, pv)
    poses = []
    for j in joints:
        lo, hi = j.range
        seq = np.concatenate([np.linspace(0, hi, frames_per_joint // 4), np.linspace(hi, lo, frames_per_joint // 2),
                              np.linspace(lo, 0, frames_per_joint // 4)])
        poses += [{j.name: float(v)} for v in seq]
    # final segment: all joints together corner to corner
    for t in np.linspace(0, 1, frames_per_joint // 2):
        poses.append({j.name: float(j.range[0] + t * (j.range[1] - j.range[0])) for j in joints})
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    # fix the camera on the union of extreme poses so the view does not jump
    _add(pl, polys, forward_kinematics(design, {}))
    for corner in ({j.name: j.range[0] for j in joints}, {j.name: j.range[1] for j in joints}):
        _add(pl, polys, forward_kinematics(design, corner))
    pl.view_isometric()
    cam = pl.camera_position
    frames = []
    for q in poses:
        pl.clear()
        _add(pl, polys, forward_kinematics(design, q))
        pl.camera_position = cam
        frames.append(pl.screenshot(return_img=True))
    pl.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(path), frames, duration=0.08, loop=0)
    return path
