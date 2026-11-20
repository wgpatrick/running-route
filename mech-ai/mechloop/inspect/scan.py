"""Flatbed-scanner measurement of flat sheet parts (and flat faces of bent parts).

Input: a scan (PNG/TIFF, 600-1200 dpi) of a part lying on the glass, lid closed (the part is dark against the lid), and
the part's DXF / flat pattern. Optionally the printed calibration target (`make_target`) in the same scan beside the part
or in a separate scan with the same settings: it measures the scanner's own scale error in each direction (a flatbed's
nominal dpi is typically 0.1-0.5 % off, and differently along and across the carriage) and its non-linearity.

Pipeline (`measure`):
1. calibration: the target's dot grid (10 mm pitch) found and fitted with an affine map; its linear part, rotation removed,
   gives pixel -> mm for each image direction; residuals after the fit are the scanner's non-linearity;
2. segmentation: Otsu threshold, the largest dark blob is the part, its interior background regions are the holes;
3. sub-pixel edges: every contour point is moved along its normal to where the grey level crosses half-way between
   part and background (bilinear profile), so edges are not quantised to pixels;
4. circles fitted to round holes, outline points kept;
5. registration to the DXF: candidates from principal axes (four turns, mirrored or not: a part scanned face down is a
   mirror image), the best by hole matching and outline distance, then refined by a point-to-line ICP over the outline
   plus hole centres (best-fit rigid transform, no scale: scale is the calibration's job); outliers trimmed;
6. deviations per feature: hole diameter and position, straight-edge positions (signed, + = material outside nominal),
   overall size; a deviation plot (PNG/SVG).

Synthetic scans (`render_scan`) rasterise a DXF at a dpi with rotation, scanner scale error, blur, noise and chosen
feature changes, so the pipeline's accuracy is tested against known answers (tests/test_inspect_scan.py).

Bent parts (design note, not built): each flange that lies flat is scanned face-down like a flat part and registered to
that flange's own outline (cut from the 3D model at the flange face); holes near a bend are measured as ellipses (major
and minor axes) to quantify the stretching our checks predict. The bend angle is a later step: the part stands on one
flange on a printed angle grid (lines every degree about a pivot mark) and is photographed square from above, or stands
on its end on the scanner glass, whose image then shows the bend's end profile; fitting the two flange edges gives the
angle and fitting the inside arc gives the radius the shop actually formed.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

MM_PER_IN = 25.4
TARGET_PITCH_MM = 10.0
TARGET_DOT_MM = 2.0


# --------------------------------------------------------------------------------------------- DXF profile
@dataclass
class Profile:
    outline: np.ndarray                         # (N, 2) closed polygon, mm, counter-clockwise
    circles: list = field(default_factory=list)  # [{"center": (x, y), "d": d}]
    cutouts: list = field(default_factory=list)  # [(M, 2) polygons]: non-round interior loops
    source: str = ""

    def bounds(self):
        return self.outline.min(0), self.outline.max(0)


def _circle_fit(pts: np.ndarray):
    """Algebraic (Kasa) circle fit, then a few Gauss-Newton steps on the geometric distance. (cx, cy, r, rms)."""
    x, y = pts[:, 0], pts[:, 1]
    A = np.c_[2 * x, 2 * y, np.ones(len(x))]
    b = x * x + y * y
    (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
    r = math.sqrt(max(c + cx * cx + cy * cy, 1e-12))
    for _ in range(5):
        dx, dy = x - cx, y - cy
        rho = np.hypot(dx, dy) + 1e-12
        J = np.c_[-dx / rho, -dy / rho, -np.ones(len(x))]
        res = rho - r
        step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        cx, cy, r = cx + step[0], cy + step[1], r + step[2]
    res = np.hypot(x - cx, y - cy) - r
    return float(cx), float(cy), float(r), float(np.sqrt(np.mean(res ** 2)))


def load_dxf(path, tol: float = 0.01) -> Profile:
    """Outline, round holes and other cut-outs from a DXF in mm (lines, arcs, circles, polylines, splines)."""
    import ezdxf
    from ezdxf import path as ezpath
    from shapely.geometry import Polygon

    doc = ezdxf.readfile(str(path))
    msp = doc.modelspace()
    circles, segs = [], []
    for e in msp:
        t = e.dxftype()
        if t == "CIRCLE":
            circles.append({"center": (float(e.dxf.center.x), float(e.dxf.center.y)), "d": 2.0 * float(e.dxf.radius)})
            continue
        if t in ("TEXT", "MTEXT", "DIMENSION", "POINT", "INSERT", "HATCH"):
            continue
        try:
            p = ezpath.make_path(e)
        except Exception:
            continue
        pts = np.array([[v.x, v.y] for v in p.flattening(distance=tol)], dtype=float)
        if len(pts) >= 2:
            segs.append(pts)
    # chain open pieces into closed loops by matching end points
    loops = []
    pieces = [s for s in segs]
    while pieces:
        cur = pieces.pop(0)
        changed = True
        while changed and np.linalg.norm(cur[0] - cur[-1]) > 1e-3:
            changed = False
            for i, q in enumerate(pieces):
                if np.linalg.norm(cur[-1] - q[0]) < 1e-3:
                    cur = np.vstack([cur, q[1:]])
                elif np.linalg.norm(cur[-1] - q[-1]) < 1e-3:
                    cur = np.vstack([cur, q[::-1][1:]])
                elif np.linalg.norm(cur[0] - q[-1]) < 1e-3:
                    cur = np.vstack([q, cur[1:]])
                elif np.linalg.norm(cur[0] - q[0]) < 1e-3:
                    cur = np.vstack([q[::-1], cur[1:]])
                else:
                    continue
                pieces.pop(i)
                changed = True
                break
        if len(cur) >= 4 and np.linalg.norm(cur[0] - cur[-1]) <= 1e-3:
            loops.append(cur[:-1])
    if not loops:
        raise ValueError(f"{path}: no closed outline found")
    areas = [abs(Polygon(lp).area) for lp in loops]
    k = int(np.argmax(areas))
    outline = loops[k]
    if Polygon(outline).exterior.is_ccw is False:
        outline = outline[::-1]
    cutouts = []
    for i, lp in enumerate(loops):
        if i == k:
            continue
        cx, cy, r, rms = _circle_fit(lp)
        if rms < 1e-3 and len(lp) > 8:
            circles.append({"center": (cx, cy), "d": 2 * r})
        else:
            cutouts.append(lp)
    return Profile(outline=outline, circles=circles, cutouts=cutouts, source=str(path))


# --------------------------------------------------------------------------------------------- calibration target
def make_target(out_dir, name: str = "scan_target", pitch: float = TARGET_PITCH_MM, dot: float = TARGET_DOT_MM,
                cols: int = 18, rows: int = 24) -> dict:
    """A printable dot-grid target on A4 (SVG and PDF at 1:1): `cols` x `rows` dots of `dot` mm at `pitch` mm, an orientation
    mark (a ring at the origin dot), and a 150 mm scale bar to check the print scale with calipers. Print at 100 % ("actual
    size"), measure the bar, and pass bar_mm / 150 as `print_scale` to `calibrate` if it is not 150.00."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle, Rectangle

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    W, H = 210.0, 297.0
    x0, y0 = (W - (cols - 1) * pitch) / 2, 40.0
    fig = plt.figure(figsize=(W / MM_PER_IN, H / MM_PER_IN))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")
    for i in range(cols):
        for j in range(rows):
            ax.add_patch(Circle((x0 + i * pitch, y0 + j * pitch), dot / 2, color="black", lw=0))
    ax.add_patch(Circle((x0, y0), dot * 1.1, fill=False, ec="black", lw=0.8))
    # 150 mm scale bar with 10 mm ticks
    yb = 22.0
    ax.add_patch(Rectangle((x0, yb), 150.0, 1.2, color="black", lw=0))
    for k in range(16):
        ax.plot([x0 + 10 * k, x0 + 10 * k], [yb - 2.5, yb], color="black", lw=0.5)
    ax.text(x0, yb - 6, "150 mm bar: measure with calipers. Print at 100 %% (actual size). Dots: %g mm at %g mm pitch, ring = origin." % (dot, pitch),
            fontsize=6.5, va="top")
    ax.text(x0, H - 12, "mechloop scan calibration target (mechloop.inspect.scan.make_target)", fontsize=8, va="top")
    meta = {"pitch_mm": pitch, "dot_mm": dot, "cols": cols, "rows": rows, "origin_mm": [x0, y0], "bar_mm": 150.0, "page": "A4"}
    svg, pdf = out_dir / f"{name}.svg", out_dir / f"{name}.pdf"
    matplotlib.rcParams["svg.hashsalt"] = "mechloop-target"
    fig.savefig(svg, format="svg", metadata={"Date": None})
    fig.savefig(pdf, format="pdf", metadata={"CreationDate": None})
    plt.close(fig)
    (out_dir / f"{name}.json").write_text(json.dumps(meta, indent=1))
    return {"svg": str(svg), "pdf": str(pdf), **meta}


@dataclass
class Calibration:
    L: list                  # 2x2: pixel offsets (x right, y down) -> mm, rotation removed (symmetric)
    scale_x: float           # measured px per mm / nominal px per mm, image x
    scale_y: float
    skew_deg: float
    residual_rms_mm: float   # dot positions after the affine fit: scanner non-linearity + detection noise
    residual_max_mm: float
    n_dots: int
    dpi_nominal: float
    source: str = ""

    def to_mm(self, px: np.ndarray) -> np.ndarray:
        """Pixel (x right, y down) -> mm with y up: a part scanned with its top face on the glass reads as the DXF's top view."""
        q = np.asarray(px, float) @ np.asarray(self.L).T
        return q * np.array([1.0, -1.0])


def nominal_calibration(dpi: float) -> Calibration:
    s = MM_PER_IN / dpi
    return Calibration([[s, 0.0], [0.0, s]], 1.0, 1.0, 0.0, float("nan"), float("nan"), 0, dpi, "nominal dpi (no target)")


def _dots(gray: np.ndarray, dpi: float, dot_mm: float, exclude: np.ndarray | None = None) -> np.ndarray:
    """Centres (px, sub-pixel: intensity-weighted) of dark round dots of about `dot_mm`."""
    import cv2

    thr, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if exclude is not None:
        bw[exclude] = 0
    n, lab, stats, cents = cv2.connectedComponentsWithStats(bw, connectivity=8)
    ppm = dpi / MM_PER_IN
    a_nom = math.pi * (0.5 * dot_mm * ppm) ** 2
    out = []
    inv = 255.0 - gray.astype(np.float32)
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if not (0.4 * a_nom < a < 2.2 * a_nom) or not (0.6 < w / max(h, 1) < 1.6) or a < 0.6 * w * h:
            continue
        pad = 2
        x0, y0 = max(x - pad, 0), max(y - pad, 0)
        win = inv[y0:y + h + pad, x0:x + w + pad]
        win = np.clip(win - np.percentile(win, 10), 0, None)
        yy, xx = np.mgrid[0:win.shape[0], 0:win.shape[1]]
        s = win.sum()
        if s <= 0:
            continue
        out.append([x0 + (xx * win).sum() / s, y0 + (yy * win).sum() / s])
    return np.array(out, dtype=float).reshape(-1, 2)


def calibrate(gray: np.ndarray, dpi: float, pitch: float = TARGET_PITCH_MM, dot: float = TARGET_DOT_MM, print_scale: float = 1.0,
              exclude: np.ndarray | None = None, source: str = "") -> Calibration | None:
    """Scanner scale from the target's dots in `gray` (optionally masking out `exclude`, e.g. the part). None if fewer than
    6 dots are found."""
    from scipy.spatial import cKDTree

    pts = _dots(gray, dpi, dot, exclude)
    if len(pts) < 6:
        return None
    tree = cKDTree(pts)
    dist, idx = tree.query(pts, k=5)
    ppm = dpi / MM_PER_IN
    pitch_px = float(np.median(dist[:, 1]))
    if not (0.6 * pitch * ppm < pitch_px < 1.4 * pitch * ppm):
        return None
    # lattice vectors from the dot nearest the centroid
    c0 = int(np.argmin(np.linalg.norm(pts - pts.mean(0), axis=1)))
    nb = pts[idx[c0, 1:]] - pts[c0]
    nb = nb[np.abs(np.linalg.norm(nb, axis=1) - pitch_px) < 0.25 * pitch_px]
    if len(nb) < 2:
        return None
    a1 = nb[np.argmax(nb[:, 0])] if np.max(np.abs(nb[:, 0])) > np.max(np.abs(nb[:, 1])) else nb[np.argmax(np.abs(nb[:, 0]))]
    a1 = a1 if a1[0] >= 0 else -a1
    a2 = min(nb, key=lambda v: abs(v @ a1) / (np.linalg.norm(v) * np.linalg.norm(a1)))
    a2 = a2 if a2[1] >= 0 else -a2
    B = np.c_[a1, a2]
    ij = np.rint(np.linalg.solve(B, (pts - pts[c0]).T).T)
    # refine the lattice with an affine fit, re-index once, then fit: px = A @ mm + b
    g = pitch * print_scale
    for _ in range(2):
        M = np.c_[ij * g, np.ones(len(ij))]
        sol, *_ = np.linalg.lstsq(M, pts, rcond=None)
        A, b = sol[:2].T, sol[2]
        ij = np.rint(np.linalg.solve(A, (pts - b).T).T / g)
    M = np.c_[ij * g, np.ones(len(ij))]
    sol, *_ = np.linalg.lstsq(M, pts, rcond=None)
    A, b = sol[:2].T, sol[2]
    res_px = pts - (ij * g) @ A.T - b
    Linv = np.linalg.inv(A)                       # px -> mm (with the target's rotation)
    # polar decomposition Linv = U P: keep P (scale and skew in image axes), drop the rotation U
    U, S, Vt = np.linalg.svd(Linv)
    P = Vt.T @ np.diag(S) @ Vt
    res_mm = np.linalg.norm(res_px @ P.T, axis=1)
    sx = 1.0 / (P[0, 0] * ppm)
    sy = 1.0 / (P[1, 1] * ppm)
    cosang = (A[:, 0] @ A[:, 1]) / (np.linalg.norm(A[:, 0]) * np.linalg.norm(A[:, 1]))
    return Calibration(P.tolist(), float(sx), float(sy), float(90.0 - math.degrees(math.acos(abs(cosang)))),
                       float(np.sqrt(np.mean(res_mm ** 2))), float(res_mm.max()), int(len(pts)), float(dpi), source)


# --------------------------------------------------------------------------------------------- synthetic scans
def render_scan(profile: Profile, dpi: float, *, rotation_deg: float = 0.0, offset_mm=(15.0, 15.0), scale=(1.0, 1.0),
                mirror: bool = False, blur_px: float = 1.0, noise: float = 3.0, part_level: int = 45, bg_level: int = 225,
                target: dict | None = None, margin_mm: float = 15.0, supersample: int = 3, seed: int = 0) -> np.ndarray:
    """A synthetic scan of `profile` (mm) on the glass: rotated, placed, mirrored (scanned face down), with the scanner's
    scale error `scale` (true px per mm / nominal, along image x and y), Gaussian blur and noise. `target` =
    {"cols", "rows", "pitch", "dot", "at": (x, y) mm} draws calibration dots beside the part, same scale error."""
    import cv2
    from shapely.geometry import Polygon

    ppm = dpi / MM_PER_IN
    th = math.radians(rotation_deg)
    Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])

    def place(p):
        p = np.asarray(p, float)
        if mirror:
            p = p * np.array([-1.0, 1.0])
        return p @ Rm.T

    allp = place(profile.outline)
    lo = allp.min(0)
    shift = np.asarray(offset_mm, float) - lo
    ext = allp.max(0) - lo + np.asarray(offset_mm) + margin_mm
    if target:
        tx, ty = target["at"]
        ext = np.maximum(ext, [tx + (target["cols"] - 1) * target["pitch"] + margin_mm, ty + (target["rows"] - 1) * target["pitch"] + margin_mm])
    W, H = int(math.ceil(ext[0] * ppm * scale[0])), int(math.ceil(ext[1] * ppm * scale[1]))
    ss = supersample
    SH = 8                                            # fractional bits for cv2 drawing
    # cv2.fillPoly fills every pixel the polygon touches: about 0.5 px too wide on each side for straight edges and 0.6 px
    # for circles (measured over random placements). Each shape is shrunk by that much at the drawing resolution, so the
    # synthetic scan is not biased; the remaining error is a few hundredths of a pixel after downsampling.
    px_mm = 1.0 / (ppm * ss * float(np.mean(scale)))
    e_poly, e_circ = 0.5 * px_mm, 0.6 * px_mm

    def to_px(p, shift=shift):
        q = (p + shift) * ppm * np.asarray(scale)
        q[:, 1] = H - q[:, 1]                         # image rows run down; mm y runs up
        q = q * ss + 0.5 * (ss - 1)                   # pixel centres of the fine grid against the coarse one
        return np.round(q * (1 << SH)).astype(np.int64).astype(np.int32)

    def shrunk(poly):
        g = Polygon(poly).buffer(-e_poly, join_style=2)
        return np.asarray(g.exterior.coords)[:-1] if not g.is_empty else np.asarray(poly)

    def ring_of(c, d, n):
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        return np.c_[c[0] + (0.5 * d - e_circ) * np.cos(a), c[1] + (0.5 * d - e_circ) * np.sin(a)]
    img = np.full((H * ss, W * ss), bg_level, np.uint8)
    cv2.fillPoly(img, [to_px(shrunk(place(profile.outline)))], part_level, shift=SH)
    for c in profile.cutouts:
        cv2.fillPoly(img, [to_px(shrunk(place(c)))], bg_level, shift=SH)
    for c in profile.circles:
        n = max(96, int(c["d"] * ppm * ss * 2))
        cen = place(np.array([c["center"]]))[0]
        cv2.fillPoly(img, [to_px(ring_of(cen, c["d"], n))], bg_level, shift=SH)
    if target:
        tx, ty = target["at"]
        for i in range(target["cols"]):
            for j in range(target["rows"]):
                cpt = np.array([tx + i * target["pitch"], ty + j * target["pitch"]])
                cv2.fillPoly(img, [to_px(ring_of(cpt, target["dot"], 96), np.zeros(2))], 20, shift=SH)
    if ss > 1:
        img = cv2.resize(img, (W, H), interpolation=cv2.INTER_AREA)
    if blur_px > 0:
        img = cv2.GaussianBlur(img, (0, 0), blur_px)
    if noise > 0:
        rng = np.random.default_rng(seed)
        img = np.clip(img.astype(np.float32) + rng.normal(0, noise, img.shape).astype(np.float32), 0, 255).astype(np.uint8)
    return img


def perturb(profile: Profile, *, move_hole: dict | None = None, grow_hole: dict | None = None, kerf_mm: float = 0.0) -> Profile:
    """A copy of `profile` with known changes: move_hole={"index", "dx", "dy"}, grow_hole={"index", "dd"}, and every cut edge
    moved outward from the material by -kerf_mm (kerf_mm > 0: the part comes out smaller, holes bigger)."""
    from shapely.geometry import Polygon

    circles = [dict(c) for c in profile.circles]
    if move_hole:
        c = circles[move_hole["index"]]
        c["center"] = (c["center"][0] + move_hole.get("dx", 0.0), c["center"][1] + move_hole.get("dy", 0.0))
    if grow_hole:
        circles[grow_hole["index"]]["d"] += grow_hole["dd"]
    outline, cutouts = profile.outline, profile.cutouts
    if kerf_mm:
        circles = [dict(c, d=c["d"] + 2 * kerf_mm) for c in circles]
        outline = np.asarray(Polygon(outline).buffer(-kerf_mm, join_style=2).exterior.coords)[:-1]
        cutouts = [np.asarray(Polygon(c).buffer(kerf_mm, join_style=2).exterior.coords)[:-1] for c in cutouts]
    return Profile(outline=outline, circles=circles, cutouts=cutouts, source=profile.source + " (perturbed)")


# --------------------------------------------------------------------------------------------- measurement
def _subpixel(gray: np.ndarray, contour: np.ndarray, level: float, inside_dark: bool = True, span: float = 3.0) -> np.ndarray:
    """Contour points (px) moved along their normals to the `level` crossing of the bilinear grey profile."""
    from scipy.ndimage import map_coordinates

    p = contour.astype(float)
    n = len(p)
    if n < 5:
        return p
    k = 2
    tang = np.roll(p, -k, axis=0) - np.roll(p, k, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True) + 1e-12
    nrm = np.c_[tang[:, 1], -tang[:, 0]]
    steps = np.arange(-span, span + 1e-9, 0.25)
    S = p[:, None, :] + steps[None, :, None] * nrm[:, None, :]
    prof = map_coordinates(gray.astype(np.float32), [S[..., 1].ravel(), S[..., 0].ravel()], order=1, mode="nearest").reshape(n, len(steps))
    d = prof - level
    out = p.copy()
    for i in range(n):
        s = np.sign(d[i])
        idx = np.where(s[:-1] * s[1:] < 0)[0]
        if not len(idx):
            continue
        j = idx[np.argmin(np.abs(steps[idx]))]
        f = d[i, j] / (d[i, j] - d[i, j + 1])
        out[i] = p[i] + (steps[j] + f * 0.25) * nrm[i]
    return out


def segment(gray: np.ndarray, exclude_small_mm2: float = 20.0, ppm: float = 600 / MM_PER_IN):
    """(outline contour px, [hole contours px], part mask, threshold, part level, background level)."""
    import cv2

    thr, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(bw, connectivity=8)
    if n < 2:
        raise ValueError("no part found in the scan")
    k = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    mask = (lab == k).astype(np.uint8) * 255
    cs, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    hier = hier[0]
    outer = max((i for i in range(len(cs)) if hier[i][3] < 0), key=lambda i: cv2.contourArea(cs[i]))
    holes = [cs[i][:, 0, :] for i in range(len(cs)) if hier[i][3] == outer and cv2.contourArea(cs[i]) > 4]
    part_level = float(np.median(gray[mask > 0]))
    bg_level = float(np.median(gray[bw == 0]))
    return cs[outer][:, 0, :], holes, mask, float(thr), part_level, bg_level


def _kabsch(P, Q, w=None):
    """Rigid (R, t) minimising sum w |R p + t - q|^2 (no reflection)."""
    w = np.ones(len(P)) if w is None else np.asarray(w, float)
    pc, qc = (w[:, None] * P).sum(0) / w.sum(), (w[:, None] * Q).sum(0) / w.sum()
    H = ((P - pc) * w[:, None]).T @ (Q - qc)
    U, S, Vt = np.linalg.svd(H)
    D = np.diag([1.0, np.sign(np.linalg.det(Vt.T @ U.T))])
    R = Vt.T @ D @ U.T
    return R, qc - R @ pc


def _sample_outline(poly: np.ndarray, step: float = 0.05):
    """Dense points on a closed polygon with their outward normals (polygon counter-clockwise)."""
    pts, nrm = [], []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        L = float(np.linalg.norm(b - a))
        if L < 1e-9:
            continue
        n = max(1, int(L / step))
        t = (np.arange(n) + 0.5) / n
        pts.append(a + np.outer(t, b - a))
        d = (b - a) / L
        nrm.append(np.repeat([[d[1], -d[0]]], n, axis=0))
    return np.vstack(pts), np.vstack(nrm)


@dataclass
class ScanResult:
    calibration: dict
    transform: dict
    holes: list
    cutouts: list
    edges: list
    overall: dict
    fit: dict
    image: str = ""
    dxf: str = ""
    plan_ids: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


def _match_holes(meas_c, meas_d, nom_c, nom_d, R, t, tol=1.5):
    """[(i_meas, j_nom)] nearest matches with similar diameter after transform (R, t)."""
    if not len(meas_c) or not len(nom_c):
        return []
    q = meas_c @ R.T + t
    pairs, used = [], set()
    D = np.linalg.norm(q[:, None, :] - nom_c[None, :, :], axis=2) + 2.0 * np.abs(meas_d[:, None] - nom_d[None, :])
    for i in np.argsort(D.min(1)):
        j = int(np.argmin(np.where(np.isin(np.arange(len(nom_c)), list(used)), np.inf, D[i])))
        if D[i, j] < tol and j not in used:
            pairs.append((int(i), j))
            used.add(j)
    return pairs


def register(meas_outline, meas_hc, meas_hd, prof: Profile, iters: int = 30):
    """Best-fit rigid transform (measured mm -> DXF mm), trying mirror. Returns dict(R, t, mirror, pairs, rms)."""
    from scipy.spatial import cKDTree
    from shapely.geometry import Polygon

    nom_pts, nom_nrm = _sample_outline(prof.outline, 0.05)
    tree = cKDTree(nom_pts)
    nom_c = np.array([c["center"] for c in prof.circles], float).reshape(-1, 2)
    nom_d = np.array([c["d"] for c in prof.circles], float)
    npoly = Polygon(prof.outline)

    def axes(poly_pts):
        pg = Polygon(poly_pts)
        c = np.array(pg.centroid.coords[0])
        X = poly_pts - c
        ev, evec = np.linalg.eigh(X.T @ X)
        return c, evec[:, ::-1]
    cn, En = axes(prof.outline)
    best = None
    sub = meas_outline[:: max(1, len(meas_outline) // 2000)]
    for mirror in (False, True):
        M = np.diag([-1.0, 1.0]) if mirror else np.eye(2)
        mo = sub @ M.T
        mc_, Em = axes(meas_outline @ M.T)
        for sgn in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            Em_s = Em * np.array(sgn)
            R0 = En @ Em_s.T
            if np.linalg.det(R0) < 0:
                continue
            t0 = cn - R0 @ mc_
            q = mo @ R0.T + t0
            d_out = float(np.mean(tree.query(q)[0]))
            pairs = _match_holes(meas_hc @ M.T, meas_hd, nom_c, nom_d, R0, t0, tol=3.0)
            cost = d_out + 0.5 * (len(nom_c) - len(pairs))
            if best is None or cost < best[0]:
                best = (cost, mirror, R0, t0)
    _, mirror, R, t = best
    M = np.diag([-1.0, 1.0]) if mirror else np.eye(2)
    mo_all = meas_outline @ M.T
    hc = meas_hc @ M.T
    w_hole = None
    keep_o = np.ones(len(mo_all), bool)
    for it in range(iters):
        q = mo_all @ R.T + t
        dist, idx = tree.query(q)
        nr = nom_nrm[idx]
        r_o = np.einsum("ij,ij->i", q - nom_pts[idx], nr)
        if it >= 3:
            mad = np.median(np.abs(r_o - np.median(r_o))) + 1e-6
            keep_o = np.abs(r_o - np.median(r_o)) < max(6 * 1.4826 * mad, 0.05)
        pairs = _match_holes(hc, meas_hd, nom_c, nom_d, R, t)
        # linearised point-to-line (outline) + point-to-point (hole centres): unknowns (dtheta, dx, dy)
        J_o = np.c_[np.einsum("ij,ij->i", np.c_[-q[:, 1], q[:, 0]], nr), nr]
        rows, rhs, wts = [J_o[keep_o]], [-r_o[keep_o]], [np.ones(keep_o.sum())]
        if pairs:
            pi, pj = np.array(pairs).T
            qh = hc[pi] @ R.T + t
            e = qh - nom_c[pj]
            rh = np.linalg.norm(e, axis=1)
            if it >= 3 and len(rh) >= 4:          # trim holes that are far off (a feature that moved should not drag the fit)
                med = np.median(rh)
                ok = rh <= max(3 * med, 0.05)
                pi, pj, qh, e = pi[ok], pj[ok], qh[ok], e[ok]
            wh = keep_o.sum() / max(len(pi), 1) * 0.5 / 2.0      # holes together weigh half as much as the outline
            for ax_ in (0, 1):
                Jh = np.c_[(np.c_[-qh[:, 1], qh[:, 0]])[:, ax_], np.eye(2)[ax_][None, :].repeat(len(qh), 0)]
                rows.append(Jh)
                rhs.append(-e[:, ax_])
                wts.append(np.full(len(qh), wh))
        J = np.vstack(rows)
        r = np.concatenate(rhs)
        W = np.concatenate(wts)
        sol = np.linalg.solve(J.T @ (J * W[:, None]), J.T @ (r * W))
        dth, dt = sol[0], sol[1:]
        Rd = np.array([[math.cos(dth), -math.sin(dth)], [math.sin(dth), math.cos(dth)]])
        R, t = Rd @ R, Rd @ t + dt
        if it >= 5 and abs(dth) < 1e-9 and np.linalg.norm(dt) < 1e-7:      # trimming starts at iteration 3
            break
    q = mo_all @ R.T + t
    dist, idx = tree.query(q)
    r_o = np.einsum("ij,ij->i", q - nom_pts[idx], nom_nrm[idx])
    return {"R": R, "t": t, "mirror": mirror, "M": M, "pairs": _match_holes(hc, meas_hd, nom_c, nom_d, R, t),
            "outline_rms": float(np.sqrt(np.mean(r_o[keep_o] ** 2))), "outline_resid": r_o, "outline_mm": q,
            "nominal_at": nom_pts[idx], "normal_at": nom_nrm[idx], "keep": keep_o}


def _straight_edges(poly: np.ndarray, min_len: float = 4.0):
    out = []
    for i, (a, b) in enumerate(zip(poly, np.roll(poly, -1, axis=0))):
        L = float(np.linalg.norm(b - a))
        if L >= min_len:
            out.append((i, a, b, L))
    return out


def measure(image, dxf, dpi: float, *, calibration: Calibration | str | None = "auto", plan: dict | None = None,
            out_dir=None, name: str | None = None, target_pitch: float = TARGET_PITCH_MM, target_dot: float = TARGET_DOT_MM,
            print_scale: float = 1.0) -> ScanResult:
    """Measure a scanned flat part against its DXF. `image`: path or 2D uint8 array. `calibration`: a Calibration, "auto"
    (look for target dots beside the part in this scan; nominal dpi if none) or None (nominal dpi)."""
    import cv2

    if isinstance(image, (str, Path)):
        gray = cv2.imread(str(image), cv2.IMREAD_GRAYSCALE)
        if gray is None:
            raise ValueError(f"cannot read {image}")
        img_name = str(image)
    else:
        gray = np.asarray(image)
        img_name = "<array>"
    if gray.ndim == 3:
        gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
    prof = dxf if isinstance(dxf, Profile) else load_dxf(dxf)
    outline_px, holes_px, mask, thr, lv_part, lv_bg = segment(gray, ppm=dpi / MM_PER_IN)
    if calibration == "auto":
        excl = cv2.dilate(mask, np.ones((15, 15), np.uint8)) > 0
        cal = calibrate(gray, dpi, target_pitch, target_dot, print_scale, exclude=excl, source="target dots in this scan")
        cal = cal or nominal_calibration(dpi)
    elif calibration is None:
        cal = nominal_calibration(dpi)
    else:
        cal = calibration
    level = 0.5 * (lv_part + lv_bg)
    o_sub = _subpixel(gray, outline_px, level)
    h_sub = [_subpixel(gray, h, level) for h in holes_px]
    o_mm = cal.to_mm(o_sub)
    from shapely.geometry import Polygon

    hole_fits, cut_meas = [], []
    for h in h_sub:
        hm = cal.to_mm(h)
        cx, cy, r, rms = _circle_fit(hm)
        area = abs(Polygon(hm).area)
        if rms < max(0.02 * r, 0.015) and len(hm) >= 12 and abs(area / (math.pi * r * r) - 1.0) < 0.05:
            hole_fits.append({"center": np.array([cx, cy]), "d": 2 * r, "rms": rms, "pts": hm})
        else:
            cut_meas.append(hm)
    hc = np.array([h["center"] for h in hole_fits]).reshape(-1, 2)
    hd = np.array([h["d"] for h in hole_fits])
    reg = register(o_mm, hc, hd, prof)
    R, t, M = reg["R"], reg["t"], reg["M"]
    tf = lambda p: (np.asarray(p) @ M.T) @ R.T + t
    holes_out = []
    nom_c = np.array([c["center"] for c in prof.circles], float).reshape(-1, 2)
    matched = dict((i, j) for i, j in reg["pairs"])
    for i, h in enumerate(hole_fits):
        c = tf(h["center"])
        web = float(np.min(np.linalg.norm(reg["outline_mm"] - c, axis=1)) - 0.5 * h["d"])
        row = {"measured_center": c.round(4).tolist(), "measured_d": round(h["d"], 4), "roundness_rms": round(h["rms"], 4),
               "edge_web": round(web, 4)}
        if i in matched:
            j = matched[i]
            nc, nd = prof.circles[j]["center"], prof.circles[j]["d"]
            dv = c - np.asarray(nc)
            row.update({"dxf_index": j, "nominal_center": [round(nc[0], 4), round(nc[1], 4)], "nominal_d": round(nd, 4),
                        "dx": round(float(dv[0]), 4), "dy": round(float(dv[1]), 4), "position_error": round(float(np.linalg.norm(dv)), 4),
                        "d_error": round(h["d"] - nd, 4)})
        holes_out.append(row)
    holes_out.sort(key=lambda r: r.get("dxf_index", 1e9))
    # cut-outs: centroid and area against the nearest nominal cut-out
    cuts = []
    for cm in cut_meas:
        pm = Polygon(tf(cm)).buffer(0)
        if pm.is_empty:
            continue
        best = None
        for j, cn in enumerate(prof.cutouts):
            pn = Polygon(cn)
            dd = pm.centroid.distance(pn.centroid)
            if best is None or dd < best[0]:
                best = (dd, j, pn)
        row = {"measured_centroid": [round(pm.centroid.x, 4), round(pm.centroid.y, 4)], "measured_area": round(pm.area, 4)}
        if best and best[0] < 3.0:
            dd, j, pn = best
            row.update({"dxf_cutout": j, "nominal_area": round(pn.area, 4), "centroid_error": round(dd, 4),
                        "mean_edge_offset": round((pm.area - pn.area) / max(pn.length, 1e-9), 4)})
        cuts.append(row)
    # straight edges of the outline: mean signed offset of measured points (+ = material outside nominal)
    q, r_o = reg["outline_mm"], reg["outline_resid"]
    edges = []
    for k, a, b, L in _straight_edges(prof.outline):
        d = (b - a) / L
        nrm = np.array([d[1], -d[0]])
        rel = q - a
        s = rel @ d
        off = rel @ nrm
        sel = (s > 1.0) & (s < L - 1.0) & (np.abs(off) < 1.0)
        if sel.sum() < 10:
            continue
        mid = 0.5 * (a + b)
        edges.append({"edge": k, "from": a.round(3).tolist(), "to": b.round(3).tolist(), "length": round(L, 3),
                      "offset_mean": round(float(np.mean(off[sel])), 4), "offset_sd": round(float(np.std(off[sel])), 4),
                      "straightness": round(float(np.ptp(off[sel])), 4), "n": int(sel.sum()), "mid": mid.round(3).tolist()})
    # overall size: nominal extent + the median outward offset of the measured points on each extreme face (robust to
    # stray edge points, which a plain max - min would pick up)
    lo_n, hi_n = prof.outline.min(0), prof.outline.max(0)
    na, nn, keep = reg["nominal_at"], reg["normal_at"], reg["keep"]
    err = []
    for k in (0, 1):
        sel_hi = keep & (na[:, k] > hi_n[k] - 0.05) & (nn[:, k] > 0.9)
        sel_lo = keep & (na[:, k] < lo_n[k] + 0.05) & (nn[:, k] < -0.9)
        if sel_hi.sum() >= 5 and sel_lo.sum() >= 5:
            err.append(float(np.median(r_o[sel_hi]) + np.median(r_o[sel_lo])))
        else:                       # no straight face at the extreme (round part): plain extents
            err.append(float(np.ptp(q[keep][:, k]) - (hi_n[k] - lo_n[k])))
    err = np.array(err)
    overall = {"nominal": (hi_n - lo_n).round(4).tolist(), "measured": (hi_n - lo_n + err).round(4).tolist(), "error": err.round(4).tolist(),
               "method": "nominal extent + median offset of the measured outline on the two extreme faces"}
    ang = math.degrees(math.atan2(R[1, 0], R[0, 0]))
    res = ScanResult(calibration=asdict(cal), transform={"rotation_deg": round(ang, 4), "t_mm": t.round(4).tolist(), "mirrored": bool(reg["mirror"]),
                                                         "note": "measured (scanner mm, mirrored first if scanned face down) -> DXF mm"},
                     holes=holes_out, cutouts=cuts, edges=edges, overall=overall,
                     fit={"outline_rms_mm": round(reg["outline_rms"], 4), "holes_matched": len(reg["pairs"]), "holes_nominal": len(prof.circles),
                          "holes_found": len(hole_fits), "cutouts_found": len(cut_meas), "threshold": thr, "part_level": lv_part, "bg_level": lv_bg,
                          "dpi_nominal": dpi},
                     image=img_name, dxf=prof.source)
    if plan:
        res.plan_ids = plan_frame(plan, prof)
    if out_dir:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = name or (Path(img_name).stem if img_name != "<array>" else "scan")
        (out_dir / f"{stem}.scan.json").write_text(json.dumps(res.to_json(), indent=1))
        deviation_plot(res, prof, out_dir / f"{stem}.deviation.png", outline_mm=q)
    return res


def plan_frame(plan: dict, prof: Profile) -> dict:
    """How the inspection plan's drawing frame sits on the DXF: {"ids": {DXF circle index: plan hole id}, "cut_ids": {DXF cut-out
    index: plan id}, "A", "b"} with plan_xy = A @ dxf_xy + b (A may include a reflection). Found by registering the plan's
    features (round holes, and cut-out centres as tie-breakers) to the DXF's."""
    from shapely.geometry import Polygon

    hs = [h for h in plan.get("holes", []) if abs((h.get("axis") or [0, 0, 1])[2]) > 0.9]
    rh = [h for h in hs if h.get("round")]
    if not rh or not prof.circles:
        return {"ids": {}, "cut_ids": {}, "A": None, "b": None}
    P = np.array([h["center"][:2] for h in rh], float)
    Pd = np.array([h["d"] for h in rh])
    Q = np.array([c["center"] for c in prof.circles], float)
    Qd = np.array([c["d"] for c in prof.circles])
    ch = [h for h in hs if not h.get("round")]
    Pc = np.array([h["center"][:2] for h in ch], float).reshape(-1, 2)
    Qc = np.array([Polygon(c).centroid.coords[0] for c in prof.cutouts], float).reshape(-1, 2)
    best = None
    for mirror in (False, True):
        Mx = np.diag([-1.0, 1.0]) if mirror else np.eye(2)
        Pm = P @ Mx.T
        for k in range(4):
            th = k * math.pi / 2
            R0 = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
            Pr = Pm @ R0.T
            t0 = (Q.min(0) + Q.max(0)) / 2 - (Pr.min(0) + Pr.max(0)) / 2
            pairs = _match_holes(Pm, Pd, Q, Qd, R0, t0, tol=2.0)
            R1, t1 = R0, t0
            if len(pairs) >= 2:
                pi, pj = np.array(pairs).T
                R1, t1 = _kabsch(Pm[pi], Q[pj])
                pairs = _match_holes(Pm, Pd, Q, Qd, R1, t1, tol=0.5)
            cut_err = 0.0
            if len(Pc) and len(Qc):
                pc = (Pc @ Mx.T) @ R1.T + t1
                cut_err = float(np.mean(np.min(np.linalg.norm(pc[:, None] - Qc[None], axis=2), axis=1)))
            key = (len(pairs), -cut_err)
            if best is None or key > best[0]:
                best = (key, pairs, Mx, R1, t1)
    _, pairs, Mx, R1, t1 = best
    A = Mx @ R1.T
    b = -A @ t1
    cut_ids = {}
    if len(Pc) and len(Qc):
        qc = Qc @ A.T + b
        for j, q in enumerate(qc):
            i = int(np.argmin(np.linalg.norm(Pc - q, axis=1)))
            if np.linalg.norm(Pc[i] - q) < 1.0:
                cut_ids[int(j)] = ch[i]["id"]
    return {"ids": {int(j): rh[i]["id"] for i, j in pairs}, "cut_ids": cut_ids, "A": A.round(9).tolist(), "b": b.round(6).tolist()}


def map_plan_ids(plan: dict, prof: Profile) -> dict:
    """{DXF circle index: plan hole id}."""
    return plan_frame(plan, prof)["ids"]


def deviation_plot(res: ScanResult, prof: Profile, path, outline_mm=None, gain: float = 50.0) -> str:
    """Nominal outline and holes in grey; measured outline offsets and hole displacements magnified `gain` times."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 8 * np.ptp(prof.outline[:, 1]) / max(np.ptp(prof.outline[:, 0]), 1e-6) + 1.0))
    P = np.vstack([prof.outline, prof.outline[:1]])
    ax.plot(P[:, 0], P[:, 1], color="0.6", lw=1, label="nominal (DXF)")
    for c in prof.cutouts:
        C = np.vstack([c, c[:1]])
        ax.plot(C[:, 0], C[:, 1], color="0.6", lw=1)
    for c in prof.circles:
        ax.add_patch(plt.Circle(c["center"], c["d"] / 2, fill=False, color="0.6", lw=1))
    for e in res.edges:
        a, b = np.array(e["from"]), np.array(e["to"])
        d = (b - a) / e["length"]
        n = np.array([d[1], -d[0]])
        off = n * e["offset_mean"] * gain
        ax.plot([a[0] + off[0], b[0] + off[0]], [a[1] + off[1], b[1] + off[1]], color="#d9480f", lw=1.5)
        m = np.array(e["mid"]) + off
        ax.annotate(f"{e['offset_mean'] * 1000:+.0f} um", m, fontsize=7, color="#d9480f", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
    for h in res.holes:
        if "dxf_index" not in h:
            continue
        nc = np.array(h["nominal_center"])
        dv = np.array([h["dx"], h["dy"]])
        ax.annotate("", nc + dv * gain, nc, arrowprops=dict(arrowstyle="->", color="#1971c2", lw=1.2))
        ax.add_patch(plt.Circle(nc + dv * gain, h["measured_d"] / 2 + h["d_error"] * (gain - 1) / 2, fill=False, color="#1971c2", lw=1))
        ax.text(nc[0], nc[1] - h["nominal_d"] / 2 - 1.5, f"pos {h['position_error'] * 1000:.0f} um\nd {h['d_error'] * 1000:+.0f} um", fontsize=6,
                ha="center", va="top", color="#1971c2")
    ax.set_aspect("equal")
    ov = res.overall
    ax.set_title(f"Scan vs DXF (deviations x{gain:g}). Overall error {ov['error'][0]:+.3f} x {ov['error'][1]:+.3f} mm; "
                 f"scale x {res.calibration['scale_x']:.4f} y {res.calibration['scale_y']:.4f}", fontsize=8)
    ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    fig.savefig(str(Path(path).with_suffix(".svg")))
    plt.close(fig)
    return str(path)


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Measure a flatbed scan of a flat part against its DXF, or write the calibration target.")
    ap.add_argument("image", nargs="?")
    ap.add_argument("--dxf")
    ap.add_argument("--dpi", type=float, default=600)
    ap.add_argument("--plan", help="inspection plan JSON (maps DXF holes to the plan's hole ids)")
    ap.add_argument("--target-scan", help="a separate scan of the calibration target, same settings")
    ap.add_argument("--print-scale", type=float, default=1.0, help="measured 150 mm bar / 150")
    ap.add_argument("--out", default="out/inspect/scans")
    ap.add_argument("--make-target", action="store_true")
    a = ap.parse_args(argv)
    if a.make_target:
        print(json.dumps(make_target(a.out)))
        return 0
    import cv2

    cal = "auto"
    if a.target_scan:
        cal = calibrate(cv2.imread(a.target_scan, cv2.IMREAD_GRAYSCALE), a.dpi, print_scale=a.print_scale, source=a.target_scan)
    plan = json.loads(Path(a.plan).read_text()) if a.plan else None
    res = measure(a.image, a.dxf, a.dpi, calibration=cal, plan=plan, out_dir=a.out, print_scale=a.print_scale)
    print(json.dumps({"overall": res.overall, "fit": res.fit, "holes": res.holes}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
