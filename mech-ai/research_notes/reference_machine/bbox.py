import sys, glob, os, json
from build123d import import_step
out = {}
for f in sorted(glob.glob(os.path.join(sys.argv[1], "*.step"))):
    try:
        s = import_step(f)
        bb = s.bounding_box()
        out[os.path.basename(f)] = {"size": [round(bb.size.X,1), round(bb.size.Y,1), round(bb.size.Z,1)], "vol_cm3": round(s.volume/1000,2)}
    except Exception as e:
        out[os.path.basename(f)] = {"error": str(e)[:80]}
    print(os.path.basename(f), out[os.path.basename(f)], flush=True)
json.dump(out, open(sys.argv[2], "w"), indent=1)
