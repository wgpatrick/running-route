"""Renders for the showcase page (tools/build_showcase.py imports this).

Every picture is made from the design's own build123d model: each part is tessellated (vendor CAD where the part has
it), coloured by how it is made, and drawn off screen with pyvista. Callout points are not placed by eye: a second
pass draws each called-out part in a flat identity colour through the same camera, and the callout is put on the
deepest point of the largest patch of that part that is actually visible. A part that is hidden gets no callout and
the build says so.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np

FAST = re.compile(r"(_screw|_bolt|_fbolt|_nut|_locknut|_pin|_stud|_spacer)(_[a-z]+)?(_\d+)?$")

# colour by process: three categorical hues for the custom parts, neutrals for what is bought
CLASS_COLOR = {
    "sheet": "#2a78d6",
    "printed": "#eb6834",
    "machined": "#1baf7a",
    "extrusion": "#c9ced6",
    "purchased": "#8b929c",
    "fastener": "#4d535c",
}
CLASS_LABEL = {
    "sheet": "Laser-cut sheet",
    "printed": "3D printed",
    "machined": "Machined",
    "extrusion": "Aluminium extrusion (bought, cut to length)",
    "purchased": "Purchased parts",
    "fastener": "Screws, nuts, spacers, brackets",
}


def part_class(c) -> str:
    if not c.cots and c.process in ("sheet", "printed", "machined"):
        return c.process
    sku = c.sku or ""
    if sku.startswith("EXT"):
        return "extrusion"
    if sku.startswith(("SHCS", "NUT-M", "SPACER", "BRKT", "TNUT", "WASHER", "HEX")) or FAST.search(c.name):
        return "fastener"
    return "purchased"


def _pv():
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv
    import vtk

    vtk.vtkObject.GlobalWarningDisplayOff()
    pv.OFF_SCREEN = True
    return pv


class Scene:
    def __init__(self, design):
        from mechloop.geom import to_trimesh

        self.pv = _pv()
        self.design = design
        self.comps = {c.name: c for c in design.components}
        self.cls = {c.name: part_class(c) for c in design.components}
        self.mesh = {}
        try:
            import export_viewer as ev
            detail = ev.detail_mesh
        except Exception:  # the viewer exporter moved: fall back to the plain tessellation
            detail = lambda c: to_trimesh(c.detail, 0.15, 0.6)  # noqa: E731
        for c in design.components:
            tm = detail(c) if getattr(c, "detail", None) is not None else to_trimesh(c.shape)
            faces = np.hstack([np.full((len(tm.faces), 1), 3), tm.faces]).astype(np.int64)
            self.mesh[c.name] = self.pv.PolyData(np.asarray(tm.vertices, dtype=float).copy(), faces)

    def placed(self, q: dict, offsets: dict | None = None) -> dict:
        """name -> PolyData in world coordinates at pose q; offsets: name -> (dx, dy, dz) for exploded views."""
        from mechloop.geom import forward_kinematics

        T = forward_kinematics(self.design, q or {})
        out = {}
        for n, c in self.comps.items():
            m = self.mesh[n].copy()
            m.transform(np.asarray(T[c.body], dtype=float), inplace=True)
            if offsets and n in offsets:
                m.translate(offsets[n], inplace=True)
            out[n] = m
        return out

    def belts(self, q: dict, offsets_by_belt: dict | None = None):
        from mechloop.geom import forward_kinematics
        try:
            from mechloop.verifiers.belts import route
        except Exception:
            return []
        T = forward_kinematics(self.design, q or {})
        out = []
        for b in self.design.belts:
            try:
                rt = route(self.design, b, T)
            except Exception:
                continue
            segs = rt["segments"]
            pts = []
            for i, (p0, p1) in enumerate(segs):
                pts += [p0, p1]
                nxt = segs[(i + 1) % len(segs)] if (rt["closed"] or i + 1 < len(segs)) else None
                if nxt is not None:
                    pts += [p1, nxt[0]]
            if not pts:
                continue
            arr = np.array(pts, dtype=float)
            if offsets_by_belt and b.name in offsets_by_belt:
                arr = arr + np.asarray(offsets_by_belt[b.name], dtype=float)
            cells = np.hstack([[2, 2 * i, 2 * i + 1] for i in range(len(arr) // 2)])
            out.append((b.name, self.pv.PolyData(arr, lines=cells), float(getattr(b, "width", 6.0) or 6.0)))
        return out


def render_view(scene: Scene, path: Path, *, q: dict, show, camera: dict, size=(1500, 1000), ghost=(),
                callouts=(), offsets=None, belt_names=None, belt_offsets=None, color_override=None, ss: int = 2,
                extra=None, marks=None, ghost_color="#7f8896") -> dict:
    """Draw one view. `show`/`ghost`: sets of part names. camera: {"pos", "focal", "up", "angle"} or with
    "parallel_scale". callouts: [(key, label, [part names])]. Returns {"size": [w, h], "callouts": [...]}; callout x, y
    are fractions of the picture from its top-left corner."""
    from PIL import Image
    from scipy import ndimage

    pv = scene.pv
    W, H = size
    parts = scene.placed(q, offsets)
    show = [n for n in scene.comps if n in show]
    ghost = [n for n in scene.comps if n in ghost and n not in show]

    def cam(pl):
        pl.camera.position = camera["pos"]
        pl.camera.focal_point = camera["focal"]
        pl.camera.up = camera.get("up", (0, 0, 1))
        if "parallel_scale" in camera:
            pl.enable_parallel_projection()
            pl.camera.parallel_scale = camera["parallel_scale"]
        else:
            pl.camera.view_angle = camera.get("angle", 26)
        pl.camera.clipping_range = camera.get("clip", (20.0, 6000.0))

    pl = pv.Plotter(off_screen=True, window_size=(W * ss, H * ss), lighting="none")
    for pos, inten in (((1.0, -1.6, 2.2), 0.95), ((-2.0, -0.6, 0.8), 0.45), ((0.6, 2.0, 1.0), 0.30), ((0, 0, -1), 0.18)):
        lt = pv.Light(position=pos, focal_point=(0, 0, 0), intensity=inten, light_type="scene light")
        lt.positional = False
        pl.add_light(lt)
    for n in show:
        col = (color_override or {}).get(n) or CLASS_COLOR[scene.cls[n]]
        m = parts[n]
        pl.add_mesh(m, color=col, smooth_shading=False, ambient=0.32, diffuse=0.75, specular=0.12, specular_power=18)
        e = m.extract_feature_edges(feature_angle=38, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
        if e.n_points:
            pl.add_mesh(e, color="#20242b", line_width=1.0 * ss, lighting=False)
    for n in ghost:  # phantom outline: the part's bounding box, not its detail
        pl.add_mesh(parts[n].outline(), color=ghost_color, line_width=1.0 * ss, lighting=False)
    for name, bl, width in scene.belts(q, belt_offsets):
        if belt_names is not None and name not in belt_names:
            continue
        pl.add_mesh(bl, color="#17191d", line_width=max(2.0, width / 3.0) * ss, lighting=False,
                    render_lines_as_tubes=True)
    if extra:
        extra(pl, pv, ss)
    cam(pl)
    img = pl.screenshot(None, transparent_background=True, return_img=True)
    proj = {}
    if marks:
        import vtk
        co = vtk.vtkCoordinate()
        co.SetCoordinateSystemToWorld()
        for k, p in marks.items():
            co.SetValue(float(p[0]), float(p[1]), float(p[2]))
            dx, dy = co.GetComputedDoubleDisplayValue(pl.renderer)
            proj[k] = [round(dx / (W * ss), 4), round(1.0 - dy / (H * ss), 4)]
    pl.close()
    im = Image.fromarray(img).resize((W, H), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "WEBP", quality=86, method=6)

    out = {"size": [W, H], "callouts": [], "file": path.name, "marks": proj}
    if callouts:
        # identity pass: same camera, every shown part black, each called-out part its own flat colour
        pl2 = pv.Plotter(off_screen=True, window_size=(W, H), lighting="none")
        pl2.set_background("black")
        ids = {}
        for k, (key, _label, names) in enumerate(callouts, 1):
            for n in names:
                ids[n] = k
        for n in show:
            k = ids.get(n, 0)
            pl2.add_mesh(parts[n], color=[k * 8, 0, 255 if k else 0], lighting=False)
        cam(pl2)
        pl2.disable_anti_aliasing()
        idimg = pl2.screenshot(None, return_img=True)
        pl2.close()
        for k, (key, label, names) in enumerate(callouts, 1):
            mask = (idimg[:, :, 0] == k * 8) & (idimg[:, :, 2] > 250)
            mx, my = int(W * 0.035), int(H * 0.035)   # keep the callout clear of the picture's edge
            inner = np.zeros_like(mask)
            inner[my:H - my, mx:W - mx] = mask[my:H - my, mx:W - mx]
            if inner.sum() >= 12:
                mask = inner
            if mask.sum() < 12:
                out["callouts"].append({"key": key, "label": label, "visible": False, "parts": list(names)})
                continue
            lab, nlab = ndimage.label(mask)
            sizes = ndimage.sum(mask, lab, range(1, nlab + 1))
            big = lab == (int(np.argmax(sizes)) + 1)
            dist = ndimage.distance_transform_edt(big)
            y, x = np.unravel_index(int(np.argmax(dist)), dist.shape)
            out["callouts"].append({"key": key, "label": label, "visible": True, "x": round(float(x + 0.5) / W, 4),
                                    "y": round(float(y + 0.5) / H, 4), "visible_px": int(mask.sum()), "parts": list(names)})
    return out
