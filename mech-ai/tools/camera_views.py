"""Render what each fixed camera of a design sees at its photo pose (mechloop.camera_view.render_view), with the sheet's and the
calibration target's corners marked in red.

    .venv/bin/python tools/camera_views.py designs/printer_v12_1.py --out review_v12_1/changes/topdown-camera_views

The design module provides PHOTO_POSE, camera_targets(design, pose) and the cameras: "cam_topdown" (optics in its interfaces) and
"cam_overview" (optics PICAM3_OPTICS). MECHLOOP_CHANGES selects the variant as for any build.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1200)
    a = ap.parse_args()
    from mechloop.runner import load_design
    from mechloop.camera_view import render_view
    import numpy as np

    d = load_design(a.design)
    mod = sys.modules.get(d.meta.get("module", "")) if hasattr(d, "meta") else None
    if mod is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location("design_for_views", Path(a.design).resolve())
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    pose = mod.PHOTO_POSE
    sheet, target = mod.camera_targets(d, pose)
    xs = sorted({round(p[0], 3) for p in sheet}); ys = sorted({round(p[1], 3) for p in sheet})
    corners = [p for p in sheet if round(p[0], 3) in (xs[0], xs[-1]) and round(p[1], 3) in (ys[0], ys[-1])]
    tx = sorted({round(p[0], 3) for p in target}); ty = sorted({round(p[1], 3) for p in target})
    corners += [p for p in target if round(p[0], 3) in (tx[0], tx[-1]) and round(p[1], 3) in (ty[0], ty[-1])]
    out = Path(a.out)
    for cam, optics in (("cam_topdown", None), ("cam_overview", mod.PICAM3_OPTICS)):
        p = render_view(d, cam, out / f"{cam}.png", pose, size=(a.width, 800), optics=optics, marks=np.array(corners))
        print("wrote", p)


if __name__ == "__main__":
    main()
