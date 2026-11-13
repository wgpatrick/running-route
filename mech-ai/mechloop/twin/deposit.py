"""Lay material down along the simulated nozzle path and compare with the intended part."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.signal import lfilter

RES = 20  # pixels per mm (default; PrinterMap.raster_px_per_mm overrides per run)
CHUNK = 0.2  # mm of path per deposited bead segment


def _target_layers(stl: Path, n_layers: int, lh: float):
    import trimesh
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    mesh = trimesh.load(str(stl))
    lo, hi = mesh.bounds
    shift = np.array([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])  # slicer centres it and drops it on the bed
    mesh.apply_translation(shift)
    polys = []
    for L in range(n_layers):
        sec = mesh.section(plane_origin=[0, 0, (L + 0.5) * lh], plane_normal=[0, 0, 1])
        shape = None
        if sec is not None:
            loops = [Polygon(d[:, :2]) for d in sec.discrete if len(d) >= 4]
            loops = [p.buffer(0) for p in loops if p.area > 1e-6]
            loops.sort(key=lambda p: -p.area)
            for p in loops:  # even-odd nesting gives holes
                shape = p if shape is None else shape.symmetric_difference(p)
        polys.append(shape)
    return polys, mesh


def _raster_poly(shape, x0, y0, w, h):
    img = Image.new("L", (w, h), 0)
    if shape is None or shape.is_empty:
        return np.zeros((h, w), dtype=bool)
    dr = ImageDraw.Draw(img)
    geoms = getattr(shape, "geoms", [shape])
    for g in geoms:
        if g.geom_type != "Polygon":
            continue
        dr.polygon([((x - x0) * RES, (y - y0) * RES) for x, y in g.exterior.coords], fill=255)
        for hole in g.interiors:
            dr.polygon([((x - x0) * RES, (y - y0) * RES) for x, y in hole.coords], fill=0)
    return np.array(img) > 0


def _draw_layers(gx, gy, vol, layer, ext_mask, n_layers, lh, x0, y0, w, h, nozzle):
    """Rasterise beads: chunks of path, width from the volume laid down along them."""
    imgs = [Image.new("L", (w, h), 0) for _ in range(n_layers)]
    draws = [ImageDraw.Draw(i) for i in imgs]
    idx = np.flatnonzero(ext_mask)
    if len(idx) < 2:
        return [np.array(i) > 0 for i in imgs], 0.0
    # break into runs of consecutive samples on one layer
    brk = np.flatnonzero((np.diff(idx) > 1) | (np.diff(layer[idx]) != 0)) + 1
    total_len = 0.0
    for run in np.split(idx, brk):
        if len(run) < 2:
            continue
        L = int(layer[run[0]])
        if not (0 <= L < n_layers):
            continue
        x, y, v = gx[run], gy[run], vol[run]
        d = np.hypot(np.diff(x), np.diff(y))
        s = np.concatenate([[0.0], np.cumsum(d)])
        if s[-1] < 1e-6:
            continue
        nseg = max(1, int(s[-1] / CHUNK))
        cuts = np.searchsorted(s, np.linspace(0, s[-1], nseg + 1))
        cuts[-1] = len(s) - 1
        cv = np.concatenate([[0.0], np.cumsum(v[1:])])
        for a, b in zip(cuts[:-1], cuts[1:]):
            if b <= a:
                continue
            seg_len = s[b] - s[a]
            if seg_len < 1e-6:
                continue
            width = (cv[b] - cv[a]) / (seg_len * lh)
            if width < 0.12:
                continue  # a wisp, not a bead
            width = min(width, 3 * nozzle)
            total_len += seg_len
            pts = [((x[k] - x0) * RES, (y[k] - y0) * RES) for k in (a, b)]
            draws[L].line(pts, fill=255, width=max(1, int(round(width * RES))))
            rad = width * RES / 2
            for px, py in pts:
                draws[L].ellipse([px - rad, py - rad, px + rad, py + rad], fill=255)
    return [np.array(i) > 0 for i in imgs], total_len


def deposit_and_compare(info, pm, moves, e, seg, frac, Qc, Qa, dt, stl, out: Path, name, r,
                        at=(0.0, 0.0), z_datum_error: float = 0.0) -> dict:
    from . import from_joints

    global RES
    RES = int(pm.raster_px_per_mm)

    lh = pm.layer_height
    a_fil = math.pi * (pm.filament_diameter / 2) ** 2
    gz_move = np.array([m.z for m in moves])
    n_layers = int(round(gz_move[np.array(e) > 0].max() / lh))
    # filament actually pushed out: running maximum of the commanded E (retract/unretract cancel)
    cum = np.concatenate([[0.0], np.cumsum(e)])
    E = cum[seg] + np.array(e)[seg] * frac
    Eeff = np.maximum.accumulate(E)
    dE = np.diff(Eeff, prepend=Eeff[0])
    # melt pressure follows the filament drive with a first-order lag; a retract pulls it back down,
    # so material only leaves the nozzle while the lagged position is making new ground
    alpha = dt / max(pm.extruder_lag_s, dt)
    E_lag = lfilter([alpha], [1, alpha - 1], E - E[0]) + E[0]
    Elag_eff = np.maximum.accumulate(E_lag)
    dE_lag = np.diff(Elag_eff, prepend=Elag_eff[0])
    layer = np.round(gz_move[seg] / lh).astype(int) - 1
    cx, cy, cz = from_joints(info, Qc)
    ax, ay, az = from_joints(info, Qa)
    cx, cy, ax, ay = cx - at[0], cy - at[1], ax - at[0], ay - at[1]   # compare in the part's own frame
    az = az + z_datum_error                                            # where the nozzle really is
    polys, mesh = _target_layers(stl, n_layers, lh)
    lo, hi = mesh.bounds
    pad = 6.0
    x0, y0 = lo[0] - pad, lo[1] - pad
    w, h = int((hi[0] - lo[0] + 2 * pad) * RES), int((hi[1] - lo[1] + 2 * pad) * RES)
    targets = [_raster_poly(p, x0, y0, w, h) for p in polys]
    ideal, _ = _draw_layers(cx, cy, dE * a_fil, layer, dE > 1e-9, n_layers, lh, x0, y0, w, h, pm.nozzle)
    actual, path_len = _draw_layers(ax, ay, dE_lag * a_fil, layer, dE_lag > 1e-9, n_layers, lh, x0, y0, w, h, pm.nozzle)
    px = 1.0 / RES
    rows = []
    near_struct = ndimage.generate_binary_structure(2, 1)
    for L in range(n_layers):
        T = targets[L]
        if not T.any():
            continue
        near = ndimage.binary_dilation(T, near_struct, iterations=int(1.5 * RES))  # excludes the skirt
        # sparse infill leaves voids inside the part that are meant to be there; fill those, but inside
        # the part's real holes (screw holes, bores) count only material that was actually laid down
        holes_T = ndimage.binary_fill_holes(T) & ~T
        A = ndimage.binary_fill_holes(actual[L] & near)
        A &= ~(holes_T & ~actual[L])
        if not A.any():
            rows.append({"layer": L, "iou": 0.0, "dx": None, "dy": None, "dev": None, "motion": None})
            continue
        iou = (A & T).sum() / (A | T).sum()
        perim = polys[L].length
        dev = (A ^ T).sum() * px * px / perim
        ya, xa = np.nonzero(A)
        yt, xt = np.nonzero(T)

        # average outline offset (uniform growth/shrink) and the worst local bulge / recess
        offset = float((int(A.sum()) - int(T.sum())) * px * px / perim)
        out_px, in_px = A & ~T, T & ~A
        bulge = float(ndimage.distance_transform_edt(~T)[out_px].max() * px) if out_px.any() else 0.0
        recess = float(ndimage.distance_transform_edt(T)[in_px].max() * px) if in_px.any() else 0.0
        dxs, dys = offset, bulge
        # displacement of the layer as a whole: the translation that best lines its silhouette up with
        # the target's, found from the row and column profiles (robust to thin or under-filled walls)
        def best_shift(a_prof, t_prof):
            a_prof = a_prof - a_prof.mean()
            t_prof = t_prof - t_prof.mean()
            c = np.correlate(a_prof, t_prof, mode="full")
            return (int(c.argmax()) - (len(t_prof) - 1)) * px

        shift_x = best_shift(A.sum(axis=0).astype(float), T.sum(axis=0).astype(float))
        shift_y = best_shift(A.sum(axis=1).astype(float), T.sum(axis=1).astype(float))
        motion = (actual[L] ^ ideal[L]).sum() * px * px
        hole_open = float((holes_T & ~actual[L]).sum() / holes_T.sum()) if holes_T.any() else None
        rows.append({"layer": L, "iou": float(iou), "dx": float(dxs), "dy": float(dys), "dev": float(dev),
                     "hole_open": hole_open,
                     "recess": recess, "shift": float(math.hypot(shift_x, shift_y)), "motion": float(motion),
                     "cover": float((actual[L] & T).sum() / T.sum())})
    good = [x for x in rows if x["dx"] is not None]
    ext = dE_lag > 1e-9
    z_err = np.abs(az - cz)[ext]
    vol_mm3 = float((dE * a_fil).sum())
    top = rows[-1] if rows else None
    res = {"layers": n_layers, "layer_height_mm": lh,
           "extruded_path_m": round(float(path_len) / 1000, 2),
           "filament_used_mm": round(float(dE.sum()), 1), "filament_mass_g": round(vol_mm3 * 1e-3 * pm.filament_density, 2),
           "deposited_volume_cm3": round(vol_mm3 * 1e-3, 3), "solid_part_volume_cm3": round(float(mesh.volume) * 1e-3, 3),
           "outline_iou_mean": round(float(np.mean([x["iou"] for x in rows])), 4) if rows else None,
           "outline_iou_min": round(float(np.min([x["iou"] for x in rows])), 4) if rows else None,
           "outline_offset_mm": {"mean": round(float(np.mean([x["dx"] for x in good])), 3),
                                 "worst": round(float(max((x["dx"] for x in good), key=abs)), 3)} if good else None,
           "max_bulge_mm": round(float(max(x["dy"] for x in good)), 3) if good else None,
           "max_recess_mm": round(float(max(x["recess"] for x in good)), 3) if good else None,
           "boundary_deviation_mm": {"mean": round(float(np.mean([x["dev"] for x in good])), 3),
                                     "worst": round(float(np.max([x["dev"] for x in good])), 3)} if good else None,
           "holes_open_fraction": (round(float(np.mean([x["hole_open"] for x in good if x.get("hole_open") is not None])), 3)
                                   if any(x.get("hole_open") is not None for x in good) else None),
           "layer_shift_mm_worst": round(float(np.max([x["shift"] for x in good])), 3) if good else None,
           "motion_induced_area_mm2_per_layer": round(float(np.mean([x["motion"] for x in good])), 3) if good else None,
           "top_layer_coverage": round(top["cover"], 3) if top and top.get("cover") is not None else None,
           "nozzle_height_error_mm_worst": round(float(z_err.max()), 4) if len(z_err) else None,
           "pixel_mm": px}
    # material laid over thin air: anything not resting on the layer below (allowing a 45 degree overhang)
    reach = max(1, int(round(max(lh, 0.5 * pm.nozzle) * RES)))
    worst_ov = {"span_mm": 0.0, "layer": None, "area_mm2": 0.0}
    for L in range(1, n_layers):
        if not actual[L].any():
            continue
        below = ndimage.binary_dilation(actual[L - 1], near_struct, iterations=reach)
        air = actual[L] & ~below
        if air.sum() * px * px < 0.5:
            continue
        # bridge span = twice the furthest any unsupported material is from something to rest on
        span = 2.0 * float(ndimage.distance_transform_edt(~below)[air].max()) * px
        if span > worst_ov["span_mm"]:
            worst_ov = {"span_mm": round(span, 2), "layer": L, "area_mm2": round(float(air.sum() * px * px), 2)}
    res["worst_unsupported_span_mm"] = worst_ov
    if worst_ov["span_mm"] > 8.0:
        r.add("warning", "unsupported_material",
              f"At layer {worst_ov['layer']} (Z={(worst_ov['layer'] + 1) * lh:.1f}) material is printed across a "
              f"{worst_ov['span_mm']:.0f} mm gap of thin air (a bridge or overhang with no "
              f"support). The twin does not model sag, so the real result there is unknown.",
              layer=worst_ov["layer"], hint="Re-orient the part, add supports in the slicer, or redesign the feature (teardrop holes, chamfers).")
    first = ext & (layer == 0)
    if first.any():
        h1 = float(np.median(az[first]))
        res["first_layer_nozzle_height_mm"] = round(h1, 3)
        if h1 <= 0.03:
            r.add("error", "nozzle_in_bed",
                  f"On the first layer the nozzle is {h1:.2f} mm above the bed (commanded {lh:.2f}): it drags on "
                  f"the bed and cannot extrude.", height=h1,
                  hint="Bed/nozzle datum is too low: re-level or correct the Z offset.")
        elif abs(h1 - lh) > 0.5 * lh:
            r.add("error", "first_layer_height",
                  f"On the first layer the nozzle is {h1:.2f} mm above the bed where {lh:.2f} mm was commanded; "
                  f"{'the bead is not pressed onto the bed and will not stick' if h1 > lh else 'the bead is over-squashed'}.",
                  height=h1, hint="Correct the Z offset / bed datum.")
    empty = [x["layer"] for x in rows if x["dx"] is None]
    if empty:
        r.add("error", "layer_missing", f"Nothing was deposited on layers {empty[:8]} where the part exists.")
    if good:
        if abs(res["outline_offset_mm"]["worst"]) > 0.15:
            bad = max(good, key=lambda x: abs(x["dx"]))
            r.add("error", "print_dimension_error",
                  f"Printed outline is on average {bad['dx']:+.2f} mm off the intended one at layer {bad['layer']} "
                  f"(Z={(bad['layer'] + 1) * lh:.1f}), i.e. about {2 * bad['dx']:+.2f} mm across a feature; "
                  f"tolerance 0.15 mm.", layer=bad["layer"])
        if res["max_bulge_mm"] > 1.0 or res["max_recess_mm"] > 1.0:
            bad = max(good, key=lambda x: max(x["dy"], x["recess"]))
            r.add("error", "print_outline_defect",
                  f"Layer {bad['layer']} has a {bad['dy']:.2f} mm bulge / {bad['recess']:.2f} mm recess relative "
                  f"to the intended outline.", layer=bad["layer"])
        elif res["max_bulge_mm"] > 0.3:
            r.add("warning", "corner_bulge",
                  f"Corners and seams bulge up to {res['max_bulge_mm']:.2f} mm (material keeps flowing while the "
                  f"nozzle slows; size depends on the assumed {pm.extruder_lag_s * 1e3:.0f} ms extruder lag).")
        if res["layer_shift_mm_worst"] > 0.25:
            bad = max(good, key=lambda x: x["shift"])
            r.add("error", "print_layer_shift",
                  f"Layer {bad['layer']} is displaced {bad['shift']:.2f} mm from where it should be.",
                  layer=bad["layer"])
        if res["max_recess_mm"] is not None and 0.3 < res["max_recess_mm"] <= 1.0:
            r.add("warning", "thin_feature_underfilled",
                  f"Parts of the outline are up to {res['max_recess_mm']:.2f} mm short of material (walls thinner than "
                  f"two beads print as one bead, or gaps were left).")
        if res["outline_iou_min"] < 0.9:
            bad = min(good, key=lambda x: x["iou"])
            r.add("error", "print_outline_poor",
                  f"Layer {bad['layer']} matches the intended outline only {bad['iou']:.0%}.", layer=bad["layer"])
    # artefacts: the printed volume for rendering, and a layer contact sheet
    step = 2
    vol = np.stack([a[::step, ::step] for a in actual]).astype(np.uint8)
    np.savez_compressed(out / f"{name}_printed.npz", vol=vol, spacing=np.array([lh, step * px, step * px]),
                        origin=np.array([x0, y0]))
    picks = sorted({0, n_layers // 4, n_layers // 2, (3 * n_layers) // 4, n_layers - 1})
    tiles = []
    for L in picks:
        rgb = np.full((h, w, 3), 255, dtype=np.uint8)
        rgb[actual[L]] = (60, 120, 200)
        edge = targets[L] ^ ndimage.binary_erosion(targets[L], iterations=2)
        rgb[edge] = (220, 40, 40)
        tiles.append(Image.fromarray(rgb[::-1]))
    sheet = Image.new("RGB", (sum(t.width for t in tiles) + 10 * (len(tiles) - 1), tiles[0].height), "white")
    xo = 0
    for t in tiles:
        sheet.paste(t, (xo, 0))
        xo += t.width + 10
    if sheet.width > 3000:
        sheet = sheet.resize((3000, int(sheet.height * 3000 / sheet.width)))
    sheet.save(out / f"{name}_layers.png")
    res["layer_sheet"] = {"file": str(out / f"{name}_layers.png"), "layers_shown": picks,
                          "legend": "blue = deposited material, red = intended outline"}
    return res
