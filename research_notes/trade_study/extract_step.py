"""Walk a STEP assembly with OpenCASCADE XCAF and dump one record per leaf part instance.

Usage:  python -I extract_step.py <file.step> <out.json> [memory_limit_GB]

For every leaf instance the record holds: the chain of assembly names down to the part,
the world-space bounding box (mm), solid volume (mm^3), centre of mass (world) and the
number of solids (plus surface area for parts named 'belt'). Nothing in the STEP file is executed; it is parsed as data only.
All downstream measurements (measure_*.py) work from the JSON this writes.
"""
import json, re, sys, time, resource

src, out = sys.argv[1], sys.argv[2]
lim = float(sys.argv[3]) if len(sys.argv) > 3 else 11.0
resource.setrlimit(resource.RLIMIT_AS, (int(lim * 2**30), int(lim * 2**30)))

from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.TCollection import TCollection_ExtendedString
from OCP.TDF import TDF_Label
from OCP.collections import Sequence_TDF_Label as TDF_LabelSequence
from OCP.TDataStd import TDataStd_Name
from OCP.IFSelect import IFSelect_RetDone
from OCP.TopLoc import TopLoc_Location
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID, TopAbs_FACE
from OCP.gp import gp_Pnt

t0 = time.time()
doc = TDocStd_Document(TCollection_ExtendedString("XmlOcaf"))
rd = STEPCAFControl_Reader()
rd.SetNameMode(True)
rd.SetColorMode(False)
rd.SetLayerMode(False)
if rd.ReadFile(src) != IFSelect_RetDone:
    sys.exit("read failed")
print("read", round(time.time() - t0), "s", flush=True)
rd.Transfer(doc)
print("transfer", round(time.time() - t0), "s", flush=True)
st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())


def name(lab):
    a = TDataStd_Name()
    if lab.FindAttribute(TDataStd_Name.GetID_s(), a):
        return a.Get().ToExtString()
    return ""


cache = {}


def props(lab, shape):
    key = lab.Tag(), lab.Father().Tag()
    if key not in cache:
        ns = nf = 0
        e = TopExp_Explorer(shape, TopAbs_SOLID)
        while e.More():
            ns += 1
            e.Next()
        e = TopExp_Explorer(shape, TopAbs_FACE)
        while e.More():
            nf += 1
            e.Next()
        g = GProp_GProps()
        vol, com = 0.0, (0.0, 0.0, 0.0)
        try:
            BRepGProp.VolumeProperties_s(shape, g)
            vol = g.Mass()
            c = g.CentreOfMass()
            com = (c.X(), c.Y(), c.Z())
        except Exception:
            pass
        cache[key] = (ns, nf, vol, com)
    return cache[key]


recs = []


def walk(lab, loc, path):
    ref = TDF_Label()
    nm = name(lab)
    if st.IsReference_s(lab):
        st.GetReferredShape_s(lab, ref)
        loc = loc.Multiplied(st.GetLocation_s(lab))
        rn = name(ref)
        walk(ref, loc, path[:-1] + [rn or nm] if path else [rn or nm])
        return
    if st.IsAssembly_s(lab):
        comps = TDF_LabelSequence()
        st.GetComponents_s(lab, comps, False)
        for i in range(1, comps.Length() + 1):
            walk(comps.Value(i), loc, path + [name(comps.Value(i))])
        return
    shape = st.GetShape_s(lab)
    if shape.IsNull():
        return
    ns, nf, vol, com = props(lab, shape)
    moved = shape.Moved(loc)
    b = Bnd_Box()
    try:
        BRepBndLib.AddOptimal_s(moved, b, False, False)
    except Exception:
        BRepBndLib.Add_s(moved, b)
    if b.IsVoid():
        return
    lo, hi = b.CornerMin(), b.CornerMax()
    x0, y0, z0, x1, y1, z1 = lo.X(), lo.Y(), lo.Z(), hi.X(), hi.Y(), hi.Z()
    p = gp_Pnt(*com).Transformed(loc.Transformation())
    area = None
    if re.search(r"belt", "/".join(path), re.I) and vol > 0:
        ga = GProp_GProps()
        BRepGProp.SurfaceProperties_s(shape, ga)
        area = round(ga.Mass(), 1)      # lets a belt's length be solved from area and volume
    recs.append(dict(path=path, area=area, bbox=[round(v, 3) for v in (x0, y0, z0, x1, y1, z1)],
                     vol=round(vol, 2), com=[round(p.X(), 2), round(p.Y(), 2), round(p.Z(), 2)],
                     solids=ns, faces=nf))
    if len(recs) % 500 == 0:
        print(len(recs), "leaves", round(time.time() - t0), "s", flush=True)


free = TDF_LabelSequence()
st.GetFreeShapes(free)
for i in range(1, free.Length() + 1):
    walk(free.Value(i), TopLoc_Location(), [name(free.Value(i))])
json.dump(dict(source=src, leaves=recs, seconds=round(time.time() - t0)), open(out, "w"))
print("done", len(recs), "leaves", round(time.time() - t0), "s")
