"""Trade-study variant (b) for printer_v8: two lead screws, a rail on each side. NOT the design: see docs/PRINTER_V8.md.
A 2020 upright with a rail and two blocks at each side of the bed, a sheet side plate on each pair of blocks, two 2020
cross arms, a lead screw in front of each upright, the v8 bed (8 mm plate on four posts). No tie for the plate and no
worked-out belt route.
Run: verify designs/studies/v8_bed_b_two_screws.py --only geometry interference ratings tolerance fea --no-render"""
import importlib.util
import os
import pathlib

os.environ["V8_Z_BLOCKS"] = "2"       # this variant: two guide blocks per Z rail (the design has one)
_spec = importlib.util.spec_from_file_location("printer_v8_b", pathlib.Path(__file__).resolve().parents[1] / "printer_v8.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
os.environ.pop("V8_Z_BLOCKS", None)


def build():
    _m.Z_LAYOUT = "two"
    d = _m.build()
    d.name = "v8_bed_b_two_screws"
    return d
