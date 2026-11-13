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


def _belt_lines(design: Design, T, pv):
    """Polyline segments for every belt at this pose (straight runs plus pulley arcs)."""
    if not design.belts:
        return None
    from .verifiers.belts import route

    pts = []
    for b in design.belts:
        try:
            rt = route(design, b, T)
        except Exception:
            continue
        segs = rt["segments"]
        for i, (p0, p1) in enumerate(segs):
            pts += [p0, p1]
            nxt = segs[(i + 1) % len(segs)] if (rt["closed"] or i + 1 < len(segs)) else None
            if nxt is not None:
                pts += [p1, nxt[0]]  # chord across the pulley wrap
    if not pts:
        return None
    arr = np.array(pts)
    cells = np.hstack([[2, 2 * i, 2 * i + 1] for i in range(len(arr) // 2)])
    return pv.PolyData(arr, lines=cells)


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
        bl = _belt_lines(design, T, pv)
        if bl is not None:
            pl.add_mesh(bl, color="#111111", line_width=4)
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


def sweep_poses(design: Design, frames_per_joint: int = 16) -> list[dict]:
    joints = [j for j in design.joints if j.range[0] != j.range[1]]
    poses = []
    for j in joints:
        lo, hi = j.range
        seq = np.concatenate([np.linspace(0, hi, frames_per_joint // 4), np.linspace(hi, lo, frames_per_joint // 2),
                              np.linspace(lo, 0, frames_per_joint // 4)])
        poses += [{j.name: float(v)} for v in seq]
    for t in np.linspace(0, 1, frames_per_joint // 2):
        poses.append({j.name: float(j.range[0] + t * (j.range[1] - j.range[0])) for j in joints})
    return poses


def render_motion(design: Design, path: Path, poses: list[dict] | None = None, size=(800, 600),
                  frame_s: float = 0.08) -> Path | None:
    """Animated GIF. Default: each joint sweeps its range in turn. Pass `poses`
    (e.g. sampled from a simulation) to replay a run; the tool point is traced."""
    joints = [j for j in design.joints if j.range[0] != j.range[1]]
    if not joints:
        return None
    import imageio.v2 as imageio

    pv = _pv()
    polys = _polys(design, pv)
    poses = poses or sweep_poses(design)
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    actors = []
    for c, pd, color in polys:
        a = pl.add_mesh(pd, color=color, smooth_shading=False, specular=0.2, ambient=0.25)
        edges = pd.extract_feature_edges(feature_angle=35)
        e = pl.add_mesh(edges, color="#1b1b1b", line_width=1) if edges.n_points else None
        actors.append((c.body, a, e))
    # frame the camera on the whole swept envelope so the view does not jump
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for q in [{}] + [{j.name: v for j, v in zip(joints, corner)} for corner in
                     ([j.range[0] for j in joints], [j.range[1] for j in joints])]:
        T = forward_kinematics(design, q)
        for c, pd, _ in polys:
            b = np.array(pd.bounds).reshape(3, 2).T
            pts = (T[c.body] @ np.c_[b, np.ones(2)].T).T[:, :3]
            lo, hi = np.minimum(lo, pts.min(0)), np.maximum(hi, pts.max(0))
    pl.add_mesh(pv.Box(bounds=(lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])), opacity=0.0)
    pl.view_isometric()
    trace, trace_actor, belt_actor, frames = [], None, None, []
    for q in poses:
        T = forward_kinematics(design, q)
        if design.belts:
            if belt_actor is not None:
                pl.remove_actor(belt_actor)
            bl = _belt_lines(design, T, pv)
            belt_actor = pl.add_mesh(bl, color="#111111", line_width=4) if bl is not None else None
        for body, a, e in actors:
            a.user_matrix = T[body]
            if e is not None:
                e.user_matrix = T[body]
        if design.tool_point:
            body, p = design.tool_point
            trace.append((T[body] @ np.array([*p, 1.0]))[:3])
            if len(trace) > 1:
                if trace_actor is not None:
                    pl.remove_actor(trace_actor)
                trace_actor = pl.add_mesh(pv.lines_from_points(np.array(trace)), color="#d62728", line_width=3)
        frames.append(pl.screenshot(return_img=True))
    pl.close()
    path.parent.mkdir(parents=True, exist_ok=True)
    imageio.mimsave(str(path), frames, duration=frame_s, loop=0)
    return path


def render_simulation(design: Design, sim: dict, path: Path, fps: int = 20, **kw) -> Path | None:
    step = max(1, int(round(1.0 / fps / (sim["t"][1] - sim["t"][0]))), len(sim["q"]) // 120)
    poses = [{n: float(sim["q"][i, k]) for k, n in enumerate(sim["names"])} for i in range(0, len(sim["q"]), step)]
    return render_motion(design, path, poses=poses, frame_s=1.0 / fps, **kw)
