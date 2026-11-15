"""Trade-study variant (c) for printer_v8: three lead screws with TWO guide blocks per Z rail. NOT the design (the
design has one block per rail): see docs/PRINTER_V8.md. Everything else is printer_v8.
Run: verify designs/studies/v8_bed_c_three_screws_two_blocks.py --only geometry interference ratings tolerance fea --no-render"""
import importlib.util
import os
import pathlib

os.environ["V8_Z_BLOCKS"] = "2"       # this variant: two guide blocks per Z rail (the design has one)
_spec = importlib.util.spec_from_file_location("printer_v8_c", pathlib.Path(__file__).resolve().parents[1] / "printer_v8.py")
_m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_m)
os.environ.pop("V8_Z_BLOCKS", None)


def build():
    _m.Z_LAYOUT = "three"
    d = _m.build()
    d.name = "v8_bed_c_three_screws_two_blocks"
    return d
