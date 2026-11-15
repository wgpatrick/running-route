"""Showcase stage 'fea': re-run mechloop's bed-support FEA for two designs and keep the displacement field.

The verifier solves the bed's carrying parts as one finite-element body, reads two numbers off the result and deletes
the rest. Here the same function is called unchanged (mechloop.verifiers.bed_support.bed_support) with the solver
wrapped so the nodal displacements survive. Nothing in mechloop is edited. The pictures show the vertical
displacement of that body under a 1 kg print at the worst print corner, screw-only joints (the soft bound), both
designs on one colour scale and one exaggeration.

The field is the flexure of the parts only. The verifier adds the give of the guide blocks and nuts (a rigid-body
term, `support_compliance_mm`) to get the totals quoted elsewhere; both are written to fea_fields.json.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "out" / "showcase_cache"
# one-hue sequential ramp, light to dark (near zero recedes)
RAMP = ["#e6f0fd", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b", "#07244a"]
EXAGGERATION = 250.0


def solve_field(design_path: Path, force: bool = False) -> dict:
    """Run the verifier's bed-support case and return {"xyz", "tets", "part", "uz_bonded", "uz_screwed", "metrics"}."""
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / f"fea_{design_path.stem}.npz"
    src_time = design_path.stat().st_mtime
    if cache.exists() and not force and cache.stat().st_mtime > src_time:
        z = np.load(cache, allow_pickle=True)
        return {k: (z[k].item() if z[k].dtype == object else z[k]) for k in z.files}
    from mechloop.report import VerifierResult
    from mechloop.runner import load_design
    from mechloop.verifiers import bed_support as B
    from mechloop.verifiers import fea as F

    design = load_design(str(design_path))
    got = {"mesh": None, "U": {}}
    mesh0, solve0 = F._asm_mesh, F._asm_solve

    def mesh_(*a, **k):
        m = mesh0(*a, **k)
        got["mesh"] = m
        return m

    def solve_(workdir, job, xyz, *a, **k):
        res = solve0(workdir, job, xyz, *a, **k)
        if isinstance(res, dict) and "U" in res:
            got["U"][job] = np.array(res["U"], dtype=float)
        return res

    F._asm_mesh, F._asm_solve = mesh_, solve_
    try:
        r = VerifierResult("fea")
        out = B.bed_support(design, r, with_fea=True)
    finally:
        F._asm_mesh, F._asm_solve = mesh0, solve0
    if got["mesh"] is None or "bed" not in got["U"]:
        raise RuntimeError(f"bed-support FEA did not run for {design_path.name}: {(out or {}).get('flexure')}")
    m = got["mesh"]
    n = len(m["xyz"])
    tets, part = [], []
    for i, t in enumerate(m["part_tets"]):
        t = np.asarray(t)[:, :4]
        tets.append(t)
        part.append(np.full(len(t), i))
    up = -np.array(design.gravity, dtype=float)
    up /= np.linalg.norm(up)
    unit = float(out["flexure"]["unit_load_n"])
    w = float(out["print_weight"]["load_n"]) / unit
    fld = {
        "xyz": np.asarray(m["xyz"], dtype=np.float32),
        "tets": np.vstack(tets).astype(np.int32),
        "part": np.concatenate(part).astype(np.int16),
        "names": np.array([c.name for c in m["comps"]]),
        # sag (downward positive), mm, under the 1 kg print
        "sag_bonded": (-(got["U"]["bed"][:n] @ up) * w).astype(np.float32),
        "sag_screwed": (-(got["U"].get("bed_screwed", got["U"]["bed"])[:n] @ up) * w).astype(np.float32),
        "metrics": np.array({k: out.get(k) for k in ("print_weight", "hand_load", "flexure", "constraint")}, dtype=object),
        "design": np.array(design.name),
    }
    np.savez_compressed(cache, **fld)
    return {k: (v.item() if isinstance(v, np.ndarray) and v.dtype == object else v) for k, v in fld.items()}


def _render(fld: dict, path: Path, clim: float, camera: dict, size=(1100, 760), ss: int = 2):
    import os
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    import pyvista as pv
    from matplotlib.colors import LinearSegmentedColormap
    from PIL import Image

    xyz = np.asarray(fld["xyz"], dtype=float)
    tets = np.asarray(fld["tets"])
    cells = np.hstack([np.full((len(tets), 1), 4), tets]).ravel()
    grid = pv.UnstructuredGrid(cells, np.full(len(tets), 10, dtype=np.uint8), xyz)
    sag = np.asarray(fld["sag_screwed"], dtype=float)
    grid.point_data["sag_um"] = sag * 1000.0
    grid.cell_data["part"] = np.asarray(fld["part"])
    surf = grid.extract_surface()
    warped = surf.copy()
    pts = warped.points.copy()
    pts[:, 2] -= surf.point_data["sag_um"] / 1000.0 * EXAGGERATION
    warped.points = pts
    cmap = LinearSegmentedColormap.from_list("seq", RAMP)
    W, H = size
    pl = pv.Plotter(off_screen=True, window_size=(W * ss, H * ss), lighting="none")
    pl.add_mesh(warped, scalars="sag_um", cmap=cmap, clim=(0.0, clim * 1000.0), show_scalar_bar=False, lighting=False,
                n_colors=18)
    e = warped.extract_feature_edges(feature_angle=40, boundary_edges=True, non_manifold_edges=False, manifold_edges=False)
    if e.n_points:
        pl.add_mesh(e, color="#1c2026", line_width=1.0 * ss, lighting=False)
    # undeformed outline of the print sheet for reference
    pl.add_mesh(surf.outline(), color="#7f8896", line_width=1.0 * ss, lighting=False)
    pl.camera.position = camera["pos"]
    pl.camera.focal_point = camera["focal"]
    pl.camera.up = (0, 0, 1)
    pl.camera.view_angle = camera.get("angle", 24)
    img = pl.screenshot(None, transparent_background=True, return_img=True)
    pl.close()
    Image.fromarray(img).resize((W, H), Image.LANCZOS).save(path, "WEBP", quality=88, method=6)


def run(design_path: Path, img: Path, data: Path, compare: Path | None = None) -> None:
    t0 = time.time()
    compare = compare or design_path.with_name("printer_v7.py")
    flds = {}
    for p in (compare, design_path):
        if not p.exists():
            continue
        flds[p.stem] = solve_field(p)
        print(f"  bed-support field for {p.stem} ({time.time() - t0:.0f} s)")
    clim = max(float(np.max(f["sag_screwed"])) for f in flds.values())
    out = {"exaggeration": EXAGGERATION, "colour_max_mm": round(clim, 4), "ramp": RAMP, "designs": {}}
    for name, f in flds.items():
        xyz = np.asarray(f["xyz"], dtype=float)
        c = (xyz.min(0) + xyz.max(0)) / 2
        span = float(np.linalg.norm(xyz.max(0) - xyz.min(0)))
        cam = {"pos": (c[0] + 0.95 * span, c[1] - 1.25 * span, c[2] + 0.95 * span), "focal": (c[0], c[1], c[2] - 0.06 * span),
               "angle": 24}
        _render(f, img / f"fea_{name}.webp", clim, cam)
        m = f["metrics"]
        out["designs"][name] = {
            "file": f"fea_{name}.webp", "nodes": int(len(xyz)), "parts": int(len(f["names"])),
            "field_max_sag_screwed_mm": round(float(np.max(f["sag_screwed"])), 4),
            "field_max_sag_bonded_mm": round(float(np.max(f["sag_bonded"])), 4),
            "print_weight": m.get("print_weight"), "hand_load": m.get("hand_load"),
            "constraint": m.get("constraint"),
            "flexure": {k: v for k, v in (m.get("flexure") or {}).items() if k != "parts"},
        }
    (data / "fea_fields.json").write_text(json.dumps(out, indent=1, default=str))
