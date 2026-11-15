"""Known answers for printed-part print settings (mechloop.printsettings): mass, the info finding, the FEA lower bound
and the local checks (heat-set insert walls; the head on sparse infill is in test_known_answers_v8.py)."""
import math
import shutil

import pytest
from build123d import Box, Pos

from mechloop import Design, LoadCase
from mechloop.parts import add_screw
from mechloop.report import VerifierResult

ccx = pytest.mark.skipif(not shutil.which("ccx"), reason="CalculiX is not installed")


def cube(material="petg", **kw):
    d = Design("ps")
    d.add("c", Box(40, 40, 40), material=material, **kw)
    return d


def test_a_printed_cube_weighs_its_shell_plus_its_infilled_core():
    """40 mm PETG cube, default settings (3 walls x 0.45 = 1.35 mm on the sides, 5 x 0.2 = 1.0 mm on top, 4 x 0.2 = 0.8 mm
    below, 25 % infill): shell = 4 x 1600 x 1.35 + 1600 x (1.0 + 0.8) = 11,520 mm^3 of 64,000: 0.18; solid fraction
    0.18 + 0.82 x 0.25 = 0.385. The design's settings replace the default, the part's own replace the design's; a
    plastic part declared machined, and a bought part, are solid."""
    d = cube()
    solid = 64000e-9 * 1270
    assert d.get("c").mass() == pytest.approx(solid * (0.18 + 0.82 * 0.25), rel=1e-3)
    assert d.get("c").solid_mass() == pytest.approx(solid)
    d.manufacturing["print_settings"] = {"infill": 1.0}
    assert d.get("c").mass() == pytest.approx(solid, rel=1e-6)
    d.get("c").meta["print"] = {"infill": 0.0, "walls": 2}
    sh = (4 * 1600 * 0.9 + 1600 * 1.8) / 64000
    assert d.get("c").mass() == pytest.approx(solid * sh, rel=1e-3)
    assert cube(process="machined").get("c").mass() == pytest.approx(solid)
    assert cube(material="al6061").get("c").mass() == pytest.approx(64000e-9 * 2700)
    with pytest.raises(ValueError):
        d.get("c").meta["print"] = {"infil": 0.3}
        d.get("c").mass()


def test_parts_printed_to_the_default_are_named_in_an_info_finding_and_declared_ones_are_not():
    from mechloop.verifiers.manufacture import print_settings_report

    d = cube()
    r = VerifierResult("manufacture")
    m = print_settings_report(r, d)
    f = [x for x in r.findings if x.code == "print_settings_default"]
    assert len(f) == 1 and f[0].severity == "info" and f[0].data["parts"] == ["c"] and m["on_default_settings"] == 1
    assert m["parts"]["c"]["solid_fraction"] == pytest.approx(0.385, abs=1e-3)
    d.manufacturing["print_settings"] = {"walls": 4, "infill": 0.4}
    r = VerifierResult("manufacture")
    m = print_settings_report(r, d)
    assert r.findings == [] and m["parts"]["c"]["from"] == "design" and m["parts"]["c"]["walls"] == 4


def test_a_heat_set_insert_needs_perimeters_as_thick_as_the_makers_minimum_wall():
    """ruthex RX M3: minimum wall 1.6 mm. Three 0.45 mm walls are 1.35 mm: warning, asks for 4 walls; with 4 walls
    (1.8 mm) nothing. A screw threading straight into the print (no insert) is not this check."""
    from mechloop.verifiers.manufacture import print_settings_report

    def build(walls=None, insert=True):
        d = Design("ins", base="boss")
        d.add("boss", Pos(0, 0, -10) * Box(20, 20, 20), material="petg", meta={"print": {"walls": walls}} if walls else {})
        d.add("lid", Pos(0, 0, 1.5) * Box(20, 20, 3), material="al6061")
        add_screw(d, "s", "M3", 10, at=(0, 0, 3), threads_into="boss", clamps=("lid",), insert=insert)
        return d

    r = VerifierResult("manufacture")
    m = print_settings_report(r, build())
    f = [x for x in r.findings if x.code == "insert_in_sparse_infill"]
    assert len(f) == 1 and f[0].severity == "warning" and m["inserts_in_thin_perimeters"][0]["walls_needed"] == 4
    assert m["inserts_in_thin_perimeters"][0]["perimeters_mm"] == pytest.approx(1.35)
    r = VerifierResult("manufacture")
    print_settings_report(r, build(walls=4))
    assert not [x for x in r.findings if x.code == "insert_in_sparse_infill"]
    r = VerifierResult("manufacture")
    print_settings_report(r, build(insert=False))
    assert not [x for x in r.findings if x.code == "insert_in_sparse_infill"]
    assert build().bom_extras["INSERT-HEATSET-M3"]["qty"] == 1


def beam(orientation=None, infill=1.0):
    """PETG cantilever 100 x 10 x 10 mm along X, held at x = 0, 20 N down on its free end face."""
    d = Design("beam")
    pr = {"infill": infill}
    if orientation:
        pr["orientation"] = orientation
    d.add("b", Pos(50, 0, 0) * Box(100, 10, 10), material="petg", meta={"print": pr})
    d.loadcases.append(LoadCase("tip", "b", fixed=lambda f: f.center().X < 1e-6, loaded=lambda f: f.center().X > 100 - 1e-6,
                                force=(0, 0, -20), min_fos=2.0, mesh_size=2.0))
    return d


@ccx
def test_a_printed_beam_is_judged_on_its_lower_bound_and_bending_across_the_layers_is_the_weak_case():
    """Bending stress sigma_xx = 6 F L / (b h^2) = 6 x 20 x 100 / 1000 = 12 MPa at the root. Printed solid with Z up the
    layers lie along the beam: the lower bound is along the layers, about the solid figure (printed yield 47 MPa
    against the table's 45). Printed standing on its end (+X up) the bending stress pulls the layers apart: the across-
    layer strength (14 MPa) governs and the factor drops by about 14 / 47. With no orientation declared the worst of
    the three axes is taken: the same as standing up. At 25 % infill the core is sparse and the factor falls further
    (material stress = smeared / (shell + core x infill)); the lower-bound deflection is the solid one x E_upper / E_lower."""
    from mechloop.verifiers import fea as F

    res = {}
    for o in ("+Z", "+X", None):
        r = VerifierResult("fea")
        res[o] = (F.run_loadcase(beam(o), beam(o).loadcases[0], r), r)
    flat, up, unk = res["+Z"][0]["printed"], res["+X"][0]["printed"], res[None][0]["printed"]
    assert flat["governed_by"] == "along the layers" and flat["fos_lower"] == pytest.approx(flat["fos_solid"] * 47 / 45, rel=0.05)
    assert up["governed_by"] == "across the layers" and up["fos_lower"] == pytest.approx(flat["fos_lower"] * 14 / 47, rel=0.2)
    assert unk["fos_lower"] == pytest.approx(up["fos_lower"], rel=0.02) and "not declared" in unk["orientation"]
    assert res["+X"][0]["fos"] == up["fos_lower"]
    r = VerifierResult("fea")
    sparse = F.run_loadcase(beam("+Z", 0.25), beam("+Z", 0.25).loadcases[0], r)["printed"]
    assert sparse["fos_lower"] < 0.75 * flat["fos_lower"]
    mb = sparse["modulus_bounds"]
    assert sparse["deflection_lower_bound_mm"] == pytest.approx(sparse["deflection_upper_bound_mm"] * mb["upper"] / mb["lower"], rel=1e-3)
    assert mb["lower"] < 0.66 * 1500


@ccx
def test_a_printed_part_that_passes_as_solid_but_not_on_its_lower_bound_is_an_error():
    """The same beam, 30 N on its end (18 MPa bending at the root). Standing up (+X): as solid plastic its factor is
    45 / 18 = 2.5, above the 2.0 asked; on the lower bound the bending stress crosses the layers (14 MPa): about 0.8,
    `fos_low_printed` (error). Lying flat (+Z), printed solid, the same load passes."""
    from mechloop.verifiers import fea as F

    def run(o, n):
        d = beam(o)
        d.loadcases[0].force = (0, 0, -n)
        r = VerifierResult("fea")
        return F.run_loadcase(d, d.loadcases[0], r), r

    out, r = run("+X", 30)
    codes = {f.code: f for f in r.findings}
    assert out["printed"]["fos_solid"] >= 2.0 and "fos_low_printed" in codes and codes["fos_low_printed"].severity == "error"
    out, r = run("+Z", 30)
    assert "fos_low_printed" not in {f.code for f in r.findings} and "fos_low" not in {f.code for f in r.findings}
