"""Animation of a build plan: each unit arrives along its insertion path."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..render import _polys, _pv
from .planner import DIRS


def _vec(dn: str, axis) -> np.ndarray:
    if dn == "axis" and axis is not None:
        v = np.array(axis, dtype=float)
        return v / (np.linalg.norm(v) or 1.0)
    return np.array(DIRS.get(dn, (0, 0, -1)), dtype=float)


def render_build(design, res: dict, path: Path, size=(900, 700), approach: float = 70.0, max_frames: int = 170) -> Path:
    import imageio.v2 as imageio

    pv = _pv()
    polys = {c.name: (pd, color) for c, pd, color in _polys(design, pv)}
    steps = res["plan"].steps
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    # frame the camera on the finished assembly
    for pd, _ in polys.values():
        pl.add_mesh(pd, opacity=0.0)
    pl.view_isometric()
    cam = pl.camera_position
    pl.clear()
    pl.enable_lightkit()
    # group screws with the part before them so the film is not hundreds of single-screw frames
    groups, cur = [], []
    for st in steps:
        if st.kind == "fastener" and cur:
            cur.append(st)
        else:
            if cur:
                groups.append(cur)
            cur = [st]
    if cur:
        groups.append(cur)
    per = max(1, min(4, max_frames // max(len(groups), 1)))
    frames, placed = [], {}
    for g in groups:
        actors = []
        for st in g:
            v = _vec(st.path[-1][0], st.axis) if st.path else np.zeros(3)
            for p in st.parts:
                pd, color = polys[p]
                a = pl.add_mesh(pd, color="#f0a020" if st is g[0] else "#303030", specular=0.2, ambient=0.3,
                                show_edges=False, smooth_shading=False)
                actors.append((a, v, p, color))
        for k in range(per):
            t = 1.0 - (k + 1) / per
            for a, v, _, _ in actors:
                M = np.eye(4)
                M[:3, 3] = -v * approach * t
                a.user_matrix = M
            pl.camera_position = cam
            frames.append(pl.screenshot(return_img=True))
        for a, _, p, color in actors:  # settle into its final colour
            a.prop.color = color
    pl.camera_position = cam
    frames += [pl.screenshot(return_img=True)] * 12
    pl.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(path), frames, duration=0.12, loop=0)
    return path
