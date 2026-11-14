"""Bounding box and volume of single-part STEP / STL files (data only; nothing is executed).

Usage: python -I measure_parts.py <out.json> <file-or-dir> [...]
"""
import json, sys, os, glob, resource
resource.setrlimit(resource.RLIMIT_AS, (6 * 2**30, 6 * 2**30))
from OCP.STEPControl import STEPControl_Reader
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
import trimesh

out, srcs = sys.argv[1], sys.argv[2:]
files = []
for s in srcs:
    if os.path.isdir(s):
        for ext in ("step", "stp", "STEP", "stl", "STL"):
            files += glob.glob(os.path.join(s, "**", "*." + ext), recursive=True)
    else:
        files.append(s)
res = {}
for f in sorted(set(files)):
    try:
        if f.lower().endswith(".stl"):
            m = trimesh.load(f, force="mesh")
            lo, hi = m.bounds
            res[f] = dict(method="measured from STL (trimesh)", size=[round(float(b - a), 2) for a, b in zip(lo, hi)],
                          vol_cm3=round(float(abs(m.volume)) / 1000, 2), watertight=bool(m.is_watertight))
        else:
            r = STEPControl_Reader()
            r.ReadFile(f)
            r.TransferRoots()
            sh = r.OneShape()
            b = Bnd_Box()
            BRepBndLib.AddOptimal_s(sh, b, False, False)
            lo, hi = b.CornerMin(), b.CornerMax()
            g = GProp_GProps()
            BRepGProp.VolumeProperties_s(sh, g)
            res[f] = dict(method="measured from STEP (OCP)",
                          size=[round(hi.X() - lo.X(), 2), round(hi.Y() - lo.Y(), 2), round(hi.Z() - lo.Z(), 2)],
                          vol_cm3=round(g.Mass() / 1000, 2))
    except Exception as e:
        res[f] = dict(error=str(e)[:200])
json.dump(res, open(out, "w"), indent=1)
for k, v in res.items():
    print(os.path.basename(k), v.get("size"), v.get("vol_cm3"), v.get("error", ""))
