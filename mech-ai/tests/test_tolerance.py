"""Tolerance and fit simulation."""
import numpy as np
from build123d import Box, Cylinder, Pos

from mechloop.model import Adjustment, Design
from mechloop.parts import add_screw
from mechloop.report import VerifierResult
from mechloop.tolerance.fits import bores_and_shafts, screw_patterns
from mechloop.tolerance.stackup import Build


def plate_on_block(hole_d, process="printed", n_screws=4):
    d = Design("fit", base="block")
    d.add("block", Box(80, 80, 20), material="al6061")
    plate = Pos(0, 0, 12.5) * Box(80, 80, 5)
    pts = [(-30, -30), (30, -30), (-30, 30), (30, 30)][:n_screws]
    for x, y in pts:
        plate -= Pos(x, y, 12.5) * Cylinder(hole_d / 2, 5)
    d.add("plate", plate, material="petg" if process == "printed" else "al6061")
    for i, (x, y) in enumerate(pts):
        add_screw(d, f"s{i}", "M3", 12, at=(x, y, 15), threads_into="block", clamps=("plate",))
    return d


def test_tight_printed_holes_fail_and_opened_ones_pass():
    r = VerifierResult("t")
    tight = screw_patterns(plate_on_block(3.2), r)["plate -> block"]["p_all_start"]
    easy = screw_patterns(plate_on_block(3.8), VerifierResult("t"))["plate -> block"]["p_all_start"]
    assert tight < 0.6 and easy > 0.95
    assert "screws_may_not_align" in [f.code for f in r.findings]
    # the same tight hole is fine when machined, and a single screw always finds its hole
    assert screw_patterns(plate_on_block(3.4, "machined"), VerifierResult("t"))["plate -> block"]["p_all_start"] > 0.97


def test_shaft_drawn_at_bore_size_is_flagged():
    def shaft_in(bore, kind=None):
        d = Design("sb", base="housing")
        d.add("housing", Box(40, 40, 20) - Cylinder(bore / 2, 20), material="al6061")
        d.add("pin", Cylinder(5.0, 30), material="steel")
        if kind:
            d.join("pin", "housing", kind)
        r = VerifierResult("t")
        return bores_and_shafts(d, r), [f.code for f in r.findings]

    out, codes = shaft_in(10.0)
    assert codes == ["fit_not_toleranced"] and 0.4 < list(out.values())[0]["p_bad"] < 0.6
    out, codes = shaft_in(10.12)
    assert codes == [] and list(out.values())[0]["p_bad"] < 0.02
    out, codes = shaft_in(10.0, "press")          # meant to be pressed but drawn line-to-line: loose half the time
    assert codes == ["fit_not_toleranced"]
    out, codes = shaft_in(9.90, "press")
    assert codes == []


def test_a_closed_frame_is_squarer_than_an_open_chain():
    """Four bars as an open U against the same bars closed into a ring by a fifth: closing the loop
    must reduce how far the far end wanders."""
    def frame(closed):
        d = Design("frame", base="a")
        d.add("a", Pos(0, 0, 0) * Box(200, 20, 20))
        d.add("b", Pos(-90, 110, 0) * Box(20, 200, 20))
        d.add("c", Pos(90, 110, 0) * Box(20, 200, 20))
        d.add("d", Pos(-90, 220, 0) * Box(20, 20, 20))
        if closed:
            d.add("e", Pos(0, 220, 0) * Box(160, 20, 20))
        return d

    spread = {}
    for closed in (False, True):
        B = Build(frame(closed), n=3000, seed=3)
        spread[closed] = float(B.at("d", (-90, 220, 0))[:, 0].std())
    assert spread[True] < 0.8 * spread[False]


def test_point_error_grows_with_distance_from_the_joint():
    d = Design("arm", base="base")
    d.add("base", Box(40, 40, 20))
    d.add("arm", Pos(0, 0, 110) * Box(20, 20, 200), material="petg")
    B = Build(d, n=4000)
    near = B.at("arm", (0, 0, 15))[:, 0].std()
    far = B.at("arm", (0, 0, 210))[:, 0].std()
    assert far > 2 * near
