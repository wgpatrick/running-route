"""Pictures of the twin: the printed part, and the machine printing it."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..geom import forward_kinematics
from ..render import _belt_lines, _polys, _pv


def render_print(design, info, pm, jl, Qa, seg, frac, moves, e, dt, out: Path, name: str,
                 frames: int = 90, size=(900, 700)) -> dict:
    import imageio.v2 as imageio

    from . import from_joints

    pv = _pv()
    arts = {}
    # ---- the printed part, reconstructed from the deposited layers
    z = np.load(out / f"{name}_printed.npz")
    vol, sp, org = z["vol"], z["spacing"], z["origin"]
    grid = pv.ImageData(dimensions=(vol.shape[2], vol.shape[1], vol.shape[0] + 2),
                        spacing=(sp[2], sp[1], sp[0]), origin=(org[0], org[1], -sp[0]))
    padded = np.concatenate([np.zeros_like(vol[:1]), vol, np.zeros_like(vol[:1])])
    grid.point_data["m"] = padded.astype(np.float32).ravel()
    surf = grid.contour([0.5], scalars="m")
    pl = pv.Plotter(off_screen=True, window_size=(1400, 700), shape=(1, 2))
    for k, (cam, title) in enumerate(((None, "printed (simulated)"), ("xy", "top view"))):
        pl.subplot(0, k)
        pl.set_background("white")
        if surf.n_points:
            pl.add_mesh(surf, color="#3c78c8", smooth_shading=False, specular=0.1)
        pl.add_text(title, font_size=10, color="black")
        if cam == "xy":
            pl.view_xy()
            pl.enable_parallel_projection()
        else:
            pl.view_isometric()
    pl.screenshot(str(out / f"{name}_printed.png"))
    pl.close()
    arts["printed_part"] = str(out / f"{name}_printed.png")
    # ---- the machine printing
    gx, gy, gz = from_joints(info, Qa)
    cum = np.concatenate([[0.0], np.cumsum(e)])
    E = np.maximum.accumulate(cum[seg] + np.array(e)[seg] * frac)
    ext = np.diff(E, prepend=E[0]) > 1e-9
    step = max(1, int(0.004 / dt))
    k_idx = np.arange(0, len(Qa), step)
    bed_xy, bed_top, sz = info["bed_center"], info["bed_top"], info["sz"]
    polys = _polys(design, pv)
    names = [j.name for j in jl]
    pl = pv.Plotter(off_screen=True, window_size=size)
    pl.set_background("white")
    actors = []
    for c, pd, color in polys:
        a = pl.add_mesh(pd, color=color, specular=0.2, ambient=0.25)
        actors.append((c.body, a))
    # camera: look at the bed region from the front-right, close in
    zq_end = Qa[-1, 2]
    focus = np.array([bed_xy[0], bed_xy[1], info["nozzle"][2] - 10])
    span = max(info["bed_size"]) * 0.9
    pl.camera_position = [tuple(focus + np.array([span * 0.9, -span * 1.25, span * 0.75])), tuple(focus), (0, 0, 1)]
    out_frames, dep_actor = [], None
    stops = np.linspace(0, len(Qa) - 1, frames).astype(int)
    for stop in stops:
        q = {n: float(Qa[stop, i]) for i, n in enumerate(names)}
        T = forward_kinematics(design, q)
        for body, a in actors:
            a.user_matrix = T[body]
        sel = k_idx[(k_idx <= stop)]
        sel = sel[ext[sel]]
        if dep_actor is not None:
            pl.remove_actor(dep_actor)
            dep_actor = None
        if len(sel) > 1:
            if len(sel) > 60000:
                sel = sel[:: len(sel) // 60000 + 1]
            bed_z_now = bed_top + sz * Qa[stop, 2]
            pts = np.c_[bed_xy[0] + gx[sel], bed_xy[1] + gy[sel], bed_z_now + gz[sel] - pm.layer_height / 2]
            cloud = pv.PolyData(pts)
            dep_actor = pl.add_mesh(cloud, color="#1c3f8f", point_size=4, render_points_as_spheres=False)
        out_frames.append(pl.screenshot(return_img=True))
    pl.close()
    imageio.mimsave(str(out / f"{name}_printing.gif"), out_frames + [out_frames[-1]] * 10, duration=0.09, loop=0)
    arts["printing"] = str(out / f"{name}_printing.gif")
    return arts
