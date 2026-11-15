"""Trade-study variant (a) for printer_v8: v7's cantilevered bed, stiffened. NOT the design: see docs/PRINTER_V8.md.
One rear lead screw (on the two bearings and the belt of v8), the back plate on four blocks (two per rail), two 2020
arms with a 3 mm steel gusset on each, the v8 bed (8 mm plate on four posts).
Run: verify designs/studies/v8_bed_a_cantilever.py --only geometry interference ratings tolerance fea --no-render"""
import importlib.util
import os
import pathlib

os.environ["V8_Z_BLOCKS"] = "2"       # this variant: two guide blocks per Z rail (the design has one)
_spec = importlib.util.spec_from_file_location("printer_v8_a", pathlib.Path(__file__).resolve().parents[1] / "printer_v8.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
os.environ.pop("V8_Z_BLOCKS", None)


def build():
    _m.Z_LAYOUT = "cantilever"
    d = _m.build()
    d.name = "v8_bed_a_cantilever"
    return d
