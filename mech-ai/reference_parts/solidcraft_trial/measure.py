"""Measure folded STEP (build123d) and flat DXF (ezdxf) the same way for both sides. Run with python -I."""
import json, math, sys
from build123d import import_step
import ezdxf

RHO = 2.68e-3  # g/mm3

def folded(path):
    s = import_step(path)
    bb = s.bounding_box()
    com = s.center()  # center of mass by default (CenterOf.MASS)
    v = s.volume
    return {"volume_mm3": v, "area_mm2": s.area, "mass_g": v * RHO, "com": [com.X, com.Y, com.Z],
            "bbox_min": [bb.min.X, bb.min.Y, bb.min.Z], "bbox_size": [bb.size.X, bb.size.Y, bb.size.Z],
            "solids": len(s.solids())}

def dxf(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    xs, ys, per, circles, bends, layers, types = [], [], 0.0, [], [], {}, {}
    for e in msp:
        L = e.dxf.layer; T = e.dxftype()
        layers[L] = layers.get(L, 0) + 1; types[T] = types.get(T, 0) + 1
        if "BEND" in L.upper():
            if T == "LINE":
                bends.append([list(e.dxf.start)[:2], list(e.dxf.end)[:2]])
            continue
        if L.upper() in ("BEND_NOTES",) or T in ("TEXT", "MTEXT"):
            continue
        if T == "CIRCLE":
            c, r = e.dxf.center, e.dxf.radius
            circles.append([c[0], c[1], 2 * r]); per += 2 * math.pi * r
            xs += [c[0] - r, c[0] + r]; ys += [c[1] - r, c[1] + r]
        else:
            try:
                pts = [tuple(p)[:2] for p in e.flattening(0.001)] if T != "LINE" else [tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]]
            except Exception:
                pts = [tuple(p)[:2] for p in ezdxf.path.make_path(e).flattening(0.001)]
            per += sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            xs += [p[0] for p in pts]; ys += [p[1] for p in pts]
    x0, y0 = min(xs), min(ys)
    return {"bbox": [max(xs) - x0, max(ys) - y0], "min": [x0, y0], "perimeter": per, "layers": layers, "types": types,
            "holes_rel_min": sorted([[round(c[0] - x0, 4), round(c[1] - y0, 4), round(c[2], 4)] for c in circles]),
            "bends_rel_min": [[[p[0] - x0, p[1] - y0] for p in b] for b in bends]}

out = {}
args = sys.argv[1:]
for a in args:
    kind, name, path = a.split("=", 2)
    out[name] = folded(path) if kind == "step" else dxf(path)
print(json.dumps(out, indent=1))
