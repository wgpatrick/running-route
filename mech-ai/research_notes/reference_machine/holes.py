import sys, collections
from build123d import import_step, GeomType
for f in sys.argv[1:]:
    s = import_step(f)
    cnt = collections.Counter()
    pts = collections.defaultdict(list)
    for face in s.faces():
        if face.geom_type == GeomType.CYLINDER:
            from OCP.BRepAdaptor import BRepAdaptor_Surface
            r = round(BRepAdaptor_Surface(face.wrapped).Cylinder().Radius(), 2)
            if r <= 6.0:
                cnt[r] += 1
                c = face.center()
                pts[r].append((round(c.X, 1), round(c.Y, 1), round(c.Z, 1)))
    print(f.split('/')[-1], "cylindrical faces by radius (mm):", dict(sorted(cnt.items())))
    for r in (1.5, 1.6, 1.65, 1.7, 1.75, 1.8):
        if r in pts: print("   r", r, pts[r][:10])
