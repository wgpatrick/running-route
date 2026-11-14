from build123d import Box, Pos

from mechloop.model import Design, LoadCase
from mechloop.verifiers.fea import verify_fea


def cantilever(F=100.0, h=10.0, **kw):
    d = Design("beam")
    d.add("beam", Pos(50, 0, 0) * Box(100, 10, h), material="al6061")
    d.loadcases.append(LoadCase(
        "tip", "beam",
        fixed=lambda f: abs(f.center().X) < 1e-6,
        loaded=lambda f: abs(f.center().X - 100) < 1e-6,
        force=(0, 0, -F), **kw))
    return d


def test_cantilever_matches_beam_theory():
    r = verify_fea(cantilever(mesh_size=2.5))
    m = r.metrics["tip"]
    # Euler-Bernoulli: sigma = 6FL/(b h^2) = 60 MPa, delta = F L^3 / (3 E I) = 0.5806 mm
    # (+ ~1.6% shear deflection for L/h = 10)
    assert abs(m["max_deflection_mm"] - 0.59) / 0.59 < 0.03, m
    assert abs(m["peak_vm_mpa"] - 60) / 60 < 0.12, m
    assert m["reaction_imbalance"] < 1e-3
    assert r.ok


def test_fos_failure_and_bad_selection():
    r = verify_fea(cantilever(F=600.0, mesh_size=3.0))
    assert "fos_low" in [f.code for f in r.findings]
    d = cantilever()
    d.loadcases[0].loaded = lambda f: False
    assert [f.code for f in verify_fea(d).findings] == ["fea_setup"]


def test_cantilever_first_mode():
    from mechloop.model import ModalCase

    d = Design("beam")
    d.add("beam", Pos(50, 0, 0) * Box(100, 10, 10), material="al6061")
    d.modalcases.append(ModalCase("mode1", "beam", fixed=lambda f: abs(f.center().X) < 1e-6,
                                  min_frequency_hz=500, mesh_size=3.0))
    r = verify_fea(d)
    # Euler-Bernoulli: f1 = (1.875^2 / 2 pi) sqrt(E I / (rho A L^4)) = 816 Hz
    assert abs(r.metrics["mode1"]["modes_hz"][0] - 816) / 816 < 0.03, r.metrics
    assert r.ok
    d.modalcases[0].min_frequency_hz = 2000
    assert "frequency_low" in [f.code for f in verify_fea(d).findings]


def test_bonded_assembly_matches_single_beam():
    from mechloop.model import AssemblyCase

    d = Design("two")
    d.add("a", Pos(25, 0, 0) * Box(50, 10, 10), material="al6061")
    d.add("b", Pos(75, 0, 0) * Box(50, 10, 10), material="al6061")
    d.assemblycases.append(AssemblyCase(
        "tip", ["a", "b"], fixed=[("a", lambda f: abs(f.center().X) < 1e-6)],
        loaded=("b", lambda f: abs(f.center().X - 100) < 1e-6), force=(0, 0, -100),
        max_deflection=1.0, min_fos=2.0, mesh_size=2.5))
    r = verify_fea(d)
    m = r.metrics["tip"]
    assert abs(m["deflection_mm"] - 0.59) / 0.59 < 0.03, m   # same as the one-piece cantilever
    assert m["reaction_imbalance"] < 1e-3 and r.ok
    # a part that touches nothing must be reported, not silently solved
    d.add("c", Pos(300, 0, 0) * Box(10, 10, 10))
    d.assemblycases[0].components = ["a", "b", "c"]
    assert "fea_unconnected" in [f.code for f in verify_fea(d).findings]


def test_thermal_growth_matches_alpha_L_dT_and_a_clamped_plate_bows():
    from mechloop.model import ThermalCase

    # a free aluminium bar fixed at one end grows alpha * L * dT
    d = Design("bar")
    d.add("bar", Pos(100, 0, 0) * Box(200, 10, 10), material="al6061")
    d.thermalcases.append(ThermalCase("heat", ["bar"], fixed=[("bar", lambda f: abs(f.center().X) < 1e-6)],
                                      temps={"bar": 50.0}, probes={"tip": (200, 0, 0), "root": (50, 0, 0)},
                                      gaps={"length": ("tip", "root", "x", None)}, mesh_size=4.0))
    r = verify_fea(d)
    grow = r.metrics["heat"]["gap_change_mm"]["length"]
    # measured between two points clear of the clamped end (the clamp itself distorts locally)
    assert abs(grow - 23.6e-6 * 150 * 50) / (23.6e-6 * 150 * 50) < 0.02, grow       # 0.177 mm
    # a hot plate pinned at its four corners to a cold frame cannot grow freely, so it bows
    d2 = Design("bed")
    d2.add("frame", Pos(0, 0, -15) * Box(200, 200, 10), material="steel")
    names = ["frame", "plate"]
    for i, (x, y) in enumerate([(-90, -90), (90, -90), (-90, 90), (90, 90)]):
        d2.add(f"post{i}", Pos(x, y, -5) * Box(12, 12, 10), material="steel")
        names.append(f"post{i}")
    d2.add("plate", Pos(0, 0, 1.5) * Box(200, 200, 3), material="al6061")
    d2.thermalcases.append(ThermalCase("hot_bed", names,
                                       fixed=[("frame", lambda f: abs(f.center().Z + 20) < 1e-6)],
                                       temps={"plate": 60.0}, flatness=("plate", "z", 0.02), mesh_size=8.0))
    r2 = verify_fea(d2)
    assert r2.metrics["hot_bed"]["bow_mm"]["plate"] > 0.05, r2.metrics
    assert "thermal_bow" in [f.code for f in r2.findings]


def test_screw_only_joint_is_softer_than_bonded():
    from mechloop.model import AssemblyCase
    from mechloop.parts import add_screw

    d = Design("lap")
    d.add("a", Pos(50, 0, 0) * Box(100, 30, 6), material="al6061")
    d.add("b", Pos(120, 0, 6) * Box(100, 30, 6), material="al6061")          # overlaps a by 30 mm, sits on top
    add_screw(d, "s", "M5", 10, at=(85, 0, 9), threads_into="a", clamps=("b",))
    d.assemblycases.append(AssemblyCase("tip", ["a", "b"], fixed=[("a", lambda f: abs(f.center().X) < 1e-6)],
                                        loaded=("b", lambda f: abs(f.center().X - 170) < 1e-6), force=(0, 0, -20),
                                        mesh_size=3.0))
    m = verify_fea(d).metrics["tip"]
    assert m["stiffness_low_n_per_mm"] < 0.97 * m["stiffness_n_per_mm"], m
