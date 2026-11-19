"""Checks for the support code added with printer_v9: the eighth batch of catalogue parts (die spring, thumb nut, 257 mm
print sheet) and the tolerance verifier's solution for an axis on three or more rails or on floating block mounts."""
import numpy as np
import pytest
from build123d import Box, Location, Plane, Pos

from mechloop import parts as P
from mechloop.model import Adjustment, Design, Joint
from mechloop.parts import place, vendor_data
from mechloop.report import VerifierResult
from mechloop.tolerance import K_GUIDE, MU_BALL, _rail_set, thin_adjustment, verify_tolerance


def _size(st):
    bb = st.shape.bounding_box()
    return bb.size.X, bb.size.Y, bb.size.Z


# ---------------------------------------------------------------- batch 8 catalogue parts
def test_die_spring_matches_the_recorded_listing_and_is_not_verified():
    """DJ-8X20YCS: 20 mm free, 7.6 N/mm listed; compressed to 14 mm it pushes with 7.6 x 6 = 45.6 N."""
    v = vendor_data("century_spring_dj8x20")["values"]["DJ-8X20YCS"]
    st = P.die_spring_dj8x20()
    assert st.catalog and not st.verified and st.source["level"] == "secondary"
    assert _size(st)[2] == pytest.approx(v["free_length_mm"]) and st.ratings["rate_n_per_mm"] == v["rate_n_per_mm"] == 7.6
    assert st.ratings["preload_n"] == 0.0
    sq = P.die_spring_dj8x20(14.0)
    assert _size(sq)[2] == pytest.approx(14.0) and sq.ratings["preload_n"] == pytest.approx(45.6) and sq.sku == st.sku
    assert st.interfaces["bore"] > v["rod_mm"] and st.interfaces["od"] < v["hole_mm"]      # the drawn tube passes hole and rod
    assert st.ratings["max_temp_c"] is None and "max temperature" in st.source["unverified_fields"]
    for bad in (9.0, 21.0):          # the maker lists no deflection beyond 10 mm
        with pytest.raises(ValueError):
            P.die_spring_dj8x20(bad)


def test_thumb_nut_is_the_recorded_din466_row():
    v = vendor_data("halder_din466")["values"]["M4"]
    st = P.thumb_nut_din466("M4")
    assert _size(st) == pytest.approx((v["knurl_dia_d2_mm"], v["knurl_dia_d2_mm"], v["height_h_mm"]))
    # 2026-11-19: the nut bought is KIPP K0143.04 (steel, 6.2 g; same dimensions as Halder's row)
    assert st.mass_kg == pytest.approx(0.0062) and st.interfaces["thread_d"] == 4.0 and not st.verified
    # the collar's end is the bearing face at Z = 0; the knurled head is at the far end
    assert st.shape.bounding_box().min.Z == pytest.approx(0.0)
    assert not st.sku.startswith("NUT-")       # a tapped part, 1 d of engagement: not judged as a hex nut the screw must pass
    with pytest.raises(ValueError):
        P.thumb_nut_din466("M3")


def test_add_thumb_nut_records_the_thread_like_add_nut():
    d = Design("t", base="plate")
    d.add("plate", Pos(0, 0, 1.5) * Box(30, 30, 3), material="al6061")
    P.add_screw(d, "stud", "M4", 20, at=(0, 0, 3.0), clamps=("plate",))
    c = P.add_thumb_nut(d, "thumb", "M4", (0, 0, 0.0), (0, 0, -1), screw="stud")
    assert c.shape.bounding_box().max.Z == pytest.approx(0.0, abs=1e-6) and c.shape.bounding_box().min.Z == pytest.approx(-9.5)
    assert "thumb" in d.get("stud").meta["threads_into"] and "thread" in str(d.joins[frozenset(("stud", "thumb"))])


def test_print_sheet_257_says_what_is_not_published():
    """257 x 257 x 0.4 mm of steel: 0.2074 kg, computed; the seller's 120 degC; no base thickness."""
    st = P.print_sheet_pei257()
    assert _size(st) == pytest.approx((257.0, 257.0, 0.4)) and st.mass_kg == pytest.approx(257 * 257 * 0.4 * 7.85e-6, abs=1e-4)
    assert st.ratings["magnetic_base_max_temp_c"] == 120.0 and st.interfaces["magnetic_base_thickness"] is None
    assert not st.verified and st.source["level"] == "secondary"
    assert {"magnetic base thickness", "mass_kg"} <= set(st.source["unverified_fields"])


def test_batch8_parts_place_without_uncatalogued_warning():
    from mechloop.verifiers.ratings import verify_ratings

    d = Design("b8")
    for i, st in enumerate((P.die_spring_dj8x20(14.0), P.thumb_nut_din466(), P.print_sheet_pei257())):
        place(d, f"p{i}", st, Location((300.0 * i, 0, 0)))
    r = verify_ratings(d)
    assert not [f for f in r.findings if f.code == "uncatalogued_cots"]
    assert {"SPRING-DIE-DJ-8X20YCS", "THUMBNUT-DIN466-M4", "SHEET-PEI-257"} <= set(r.metrics["unverified_parts"])


# ---------------------------------------------------------------- three or more rails, floating mounts
class FakeBuild:
    """Rails whose directions are given per build, in place of the stack-up."""

    def __init__(self, dirs):
        self.dirs = dirs

    def direction(self, name, ax):
        return self.dirs[name]


def _blocks(positions, floats=None):
    d = Design("rs", base="base")
    d.add("base", Pos(0, 0, -5) * Box(300, 300, 10), material="al6061")
    out = []
    for i, (y, z) in enumerate(positions):
        rail = place(d, f"rail{i}", P.mgn12_rail(200), Location((0, y, z)))
        blk = place(d, f"blk{i}", P.mgn12h_carriage(), Location((0, y, z)), body="car", guides="x")
        if floats and floats[i]:
            blk.meta["guide_float"] = floats[i]
        out.append((blk, rail))
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(0, 100), max_effort=50))
    return d, out


def _solve(positions, lean, floats=None, adjust=False):
    """lean: per rail, its sideways drift (y, z) in mm over the 100 mm travel (one build)."""
    d, pairs = _blocks(positions, floats)
    if adjust:
        d.adjustments.append(Adjustment("rails set against the carrier", "rail_align", range_mm=2.0, joint="x"))
    dirs = {f"rail{i}": np.array([[1.0, ly / 100.0, lz / 100.0]]) for i, (ly, lz) in enumerate(lean)}
    r = VerifierResult("tolerance")
    share = lambda p, limit=None, what="", builds=1: {"standard_error": 0.0}
    out = _rail_set(d, r, FakeBuild(dirs), d.joints[0], pairs, 1, share, thin_adjustment)
    return out, r


def test_two_blocks_bind_only_along_the_line_between_them():
    """Two plain blocks 100 mm apart in y. Rail 1 drifts 0.1 mm towards rail 0: each block carries K x 0.1 / 2 (the two-rail
    formula). Rail 1 drifts 0.1 mm ACROSS the line between them (in z): the body turns to follow and nothing is loaded."""
    along, _ = _solve([(-50, 0), (50, 0)], [(0, 0), (0.1, 0)])
    assert along["side_load_on_blocks_n_99"] == pytest.approx(K_GUIDE * 0.1 / 2, rel=1e-3)
    assert along["added_drag_n_99"] == pytest.approx(2 * MU_BALL * K_GUIDE * 0.1 / 2, rel=1e-2)
    across, _ = _solve([(-50, 0), (50, 0)], [(0, 0), (0, 0.1)])
    assert across["side_load_on_blocks_n_99"] == pytest.approx(0.0, abs=0.5)
    assert across["in_plane_constraints"]["redundant"] == 1


def test_a_float_along_the_line_carries_only_its_own_stiffness():
    """The same pair, block 1 on a mount that floats along y with 250 N/mm: 0.1 mm of drift is shared by the two blocks
    and the float in series: 0.1 / (2 / K + 1 / 250) = 24.2 N, and the float moves 0.097 mm."""
    fl = {"axis": (0, 1, 0), "stiffness_n_per_mm": 250.0, "range_mm": 0.3}
    out, r = _solve([(-50, 0), (50, 0)], [(0, 0), (0.1, 0)], floats=[None, fl])
    f = 0.1 / (2 / K_GUIDE + 1 / 250.0)
    assert out["side_load_on_blocks_n_99"] == pytest.approx(f, rel=1e-3)
    assert out["float_used_as_built_mm_99"]["blk1"] == pytest.approx(f / 250.0, abs=1e-3)
    assert out["in_plane_constraints"] == {**out["in_plane_constraints"], "stiff_directions_held": 3, "redundant": 0}
    assert not [x for x in r.findings if x.code == "guide_float_exceeded"]
    small = {"axis": (0, 1, 0), "stiffness_n_per_mm": 250.0, "range_mm": 0.05}
    _, r2 = _solve([(-50, 0), (50, 0)], [(0, 0), (0.1, 0)], floats=[None, small])
    assert [x for x in r2.findings if x.code == "guide_float_exceeded" and x.severity == "error"]


def test_three_plain_rails_are_over_constrained_and_three_tangential_mounts_are_not():
    """Three blocks in a row (y -60, 0, 60). Plain, each holds two directions: six for a body that needs three. With the
    rails set to 0.02 mm of each other the blocks still carry more than the 67.5 N a rigid pair sees at Hiwin's 9 um.
    With the outer two floating along y and the middle one along z, three stiff directions are left and the same residual
    loads the blocks with a few newtons."""
    pos, lean = [(-60, 0), (0, 0), (60, 0)], [(0.3, 0.1), (-0.2, 0.25), (0.1, -0.3)]
    plain, r = _solve(pos, lean, adjust=True)
    assert plain["in_plane_constraints"]["redundant"] == 3 and plain["side_load_allowed_n"] == pytest.approx(K_GUIDE * 0.009 / 2)
    assert not plain["after_alignment"]["within_allowed_side_load"]
    assert [x for x in r.findings if x.code == "rails_over_constrained"]
    k = 250.0
    fl = [{"axis": (0, 1, 0), "stiffness_n_per_mm": k, "range_mm": 0.3}, {"axis": (0, 0, 1), "stiffness_n_per_mm": k, "range_mm": 0.3},
          {"axis": (0, 1, 0), "stiffness_n_per_mm": k, "range_mm": 0.3}]
    soft, r2 = _solve(pos, lean, floats=fl, adjust=True)
    assert soft["in_plane_constraints"]["redundant"] == 0 and soft["after_alignment"]["within_allowed_side_load"]
    assert soft["after_alignment"]["side_load_on_blocks_n_99"] < 0.1 * plain["after_alignment"]["side_load_on_blocks_n_99"]
    assert not [x for x in r2.findings if x.severity != "info"]
    assert soft["alignment_needed_mm_99"] == pytest.approx(max(np.hypot(0.5, 0.15), np.hypot(0.2, 0.4), np.hypot(0.3, 0.55)), abs=2e-3)


def test_unaligned_three_rails_fail_as_built_and_two_plain_rails_keep_the_old_path():
    pos, lean = [(-60, 0), (0, 0), (60, 0)], [(0.3, 0.1), (-0.2, 0.25), (0.1, -0.3)]
    out, r = _solve(pos, lean)
    assert out["p_within_allowable"] == 0.0 and [x for x in r.findings if x.code == "rails_not_parallel"]
    # two plain rails through the whole verifier still give the two-rail record (no "model" key: the old formula)
    d = Design("pair", base="base")
    d.add("base", Pos(0, 0, -5) * Box(240, 160, 10), material="al6061")
    for i, y in enumerate((-50, 50)):
        place(d, f"rail{i}", P.mgn12_rail(200), Location((0, y, 0)))
        place(d, f"blk{i}", P.mgn12h_carriage(), Location((0, y, 0)), body="car", guides="x")
        d.join(f"rail{i}", "base", "screwed")
        d.join(f"blk{i}", "plate", "screwed")
    d.add("plate", Pos(0, 0, 15.5) * Box(60, 130, 5), material="al6061", body="car")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-50, 50), max_effort=50))
    pr = verify_tolerance(d, n=200).metrics["paired_rails"]["x"]
    assert "model" not in pr and pr["rails"] == ["rail0", "rail1"]


def test_stiff_directions_through_one_point_do_not_locate_the_body():
    """Three blocks whose only stiff directions all pass through the middle block: the body can turn about it."""
    fl = [{"axis": (0, 0, 1), "stiffness_n_per_mm": 250.0, "range_mm": 1.0}, {"axis": (0, 0, 1), "stiffness_n_per_mm": 250.0, "range_mm": 1.0},
          {"axis": (0, 0, 1), "stiffness_n_per_mm": 250.0, "range_mm": 1.0}]
    _, r = _solve([(-60, 0), (0, 0), (60, 0)], [(0, 0), (0, 0), (0, 0)], floats=fl, adjust=True)
    assert [x for x in r.findings if x.code == "guides_locate_through_floats"]


# ---------------------------------------------------------------- bed support: a block on a floating mount
def test_a_floating_mount_is_in_series_with_its_block_in_the_bed_support_model():
    """Blocks of the test bed (rails standing on the back wall, normal -Y) declared on mounts that float along Y with
    250 N/mm and turn about X with 2e6 N.mm/rad. Along the float the support is 1 / (1 / k_block + 1 / 250); across it
    the block's own figure; about the float axis 1 / (1 / (k L^2 / 12) + 1 / 2e6), which is under the block's own. With
    three screws the nuts then lose less load per mm of height error than on rigidly mounted blocks."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    from test_known_answers_fit import bed_machine, support

    from mechloop.verifiers import bed_support as BS

    three = ((-90.0, -90.0), (90.0, -90.0), (0.0, 120.0))

    def machine(float_, per_rail=2):
        d = bed_machine(screws=three, blocks_per_rail=per_rail, sync="belt")
        d.adjustments.append(Adjustment("floating nut", "float", range_mm=0.5, joint="z"))
        if float_:
            for c in d.components:
                if c.meta.get("guides") == "z":
                    c.meta["guide_float"] = {"axis": (0, -1, 0), "stiffness_n_per_mm": 250.0, "range_mm": 0.3,
                                             "rotation_n_mm_per_rad": {"about_float_axis": 2.0e6, "about_across": 2.0e4, "about_travel": 3.0e4}}
        return d

    rigid, soft = machine(False), machine(True)
    g0 = next(s for s in BS.support_model(rigid, BS.layout(rigid))["supports"] if s["kind"] == "guide")
    g1 = next(s for s in BS.support_model(soft, BS.layout(soft))["supports"] if s["kind"] == "guide")
    k = g0["k"][0, 0]
    assert g0["k"][1, 1] == pytest.approx(k) and "mount" not in g0
    assert g1["k"][1, 1] == pytest.approx(1 / (1 / k + 1 / 250.0)) and g1["k"][0, 0] == pytest.approx(k) and g1["k"][2, 2] == pytest.approx(0.0)
    kap = g0["kappa"][1, 1]                                    # about Y, the float axis: k L^2 / 12
    assert g1["kappa"][1, 1] == pytest.approx(1 / (1 / kap + 1 / 2.0e6)) and g1["kappa"][0, 0] == pytest.approx(1 / (1 / kap + 1 / 2.0e4))
    assert g1["mount"]["stiffness_n_per_mm"] == 250.0
    sens = lambda d: support(d)[0]["nut_seating_and_lead_error"]["nuts"]["nut0"]["load_change_n_per_mm_of_height_error"]
    assert sens(soft) < sens(rigid)
    # one block per rail: only the blocks' moment stiffness resists a tilt, and the mounts take most of that away
    assert sens(machine(True, 1)) < 0.5 * sens(machine(False, 1))


# ---------------------------------------------------------------- FEA: the assembly mesher makes a second, finer attempt
def test_assembly_mesher_retries_with_finer_curved_faces(tmp_path, monkeypatch):
    """A countersunk M4 screw through a large washer into a thumb nut: on the nut's face the screw (4.0) and the washer's
    bore (4.3) leave a ring 0.15 mm wide, which eight elements per circle cannot mesh. The mesher must still return a mesh,
    and say how many elements per circle it used. A failure of the first attempt is retried; a wrong selection is not."""
    from mechloop.verifiers import fea as F

    d = Design("ring", base="plate")
    d.add("plate", Pos(0, 0, 1.5) * (Box(30, 30, 3) - Pos(0, 0, 0) * __import__("build123d").Cylinder(2.75, 3)), material="al6061")
    P.add_screw(d, "stud", "M4", 35, at=(0, 0, 20.0), clamps=("plate",), head="countersunk")
    P.add_washer(d, "w", "M4", (0, 0, 0.0), (0, 0, -1), series="large")
    P.add_thumb_nut(d, "thumb", "M4", (0, 0, -1.0), (0, 0, -1), screw="stud")
    m = F._asm_mesh(d, ["plate", "stud", "w", "thumb"], {}, 7.5, tmp_path)
    assert m["elements_per_circle"] in F.ASM_CURVATURE_STEPS and len(m["xyz"]) > 100 and all(len(t) for t in m["part_tets"])
    calls = []
    real = F._asm_mesh_once

    def flaky(design, names, selections, size, workdir, curv):
        calls.append(curv)
        if len(calls) == 1:
            raise Exception("PLC Error:  A segment and a facet intersect at point")
        return real(design, names, selections, size, workdir, curv)

    monkeypatch.setattr(F, "_asm_mesh_once", flaky)
    m2 = F._asm_mesh(d, ["plate", "w"], {}, 7.5, tmp_path)
    assert calls == list(F.ASM_CURVATURE_STEPS[:2]) and m2["elements_per_circle"] == F.ASM_CURVATURE_STEPS[1]
    with pytest.raises(ValueError):
        F._asm_mesh(d, ["plate", "w"], {"x": [("stud", lambda f: True)]}, 7.5, tmp_path)


# ---------------------------------------------------------------- thermal: a contact that slips, and the bound where it sticks
def _bar_on_pads(kind, stick=()):
    """A cold steel base, two steel pads 100 mm apart on it, a hot aluminium bar across the pads: bonded to pad a, joined
    `kind` to pad b."""
    from mechloop.model import ThermalCase

    d = Design("bar", base="base")
    d.add("base", Pos(0, 0, -3) * Box(140, 20, 6), material="steel")
    d.add("pad_a", Pos(-50, 0, 2) * Box(12, 12, 4), material="steel")
    d.add("pad_b", Pos(50, 0, 2) * Box(12, 12, 4), material="steel")
    d.add("bar", Pos(0, 0, 6) * Box(130, 12, 4), material="al6061")
    for p in ("pad_a", "pad_b"):
        d.join(p, "base", "bond")
    d.join("bar", "pad_a", "bond")
    d.join("bar", "pad_b", kind)
    d.thermalcases.append(ThermalCase("hot", ["base", "pad_a", "pad_b", "bar"], fixed=[("base", lambda f: abs(f.center().Z + 6) < 1e-6)],
                                      temps={"bar": 60.0}, probes={"end": (65.0, 0.0, 6.0)}, flatness=("bar", "z", None), mesh_size=3.0,
                                      stick=stick))
    return d


def test_a_free_sliding_contact_lets_a_hot_bar_grow_and_the_stuck_bound_bows_it():
    """Bar 60 K warmer than the base, held at pad a. On a "sliding free" contact at pad b it grows as if nothing held it:
    its far end (115 mm from pad a's centre) moves about 23.6e-6 x 60 x 115 = 0.16 mm and it stays flat. With that
    contact taken as stuck (ThermalCase.stick), or bonded outright, the pads hold 100 mm of it back and it bows."""
    from mechloop.verifiers.fea import ALPHA, run_thermal

    if not __import__("shutil").which("ccx"):
        pytest.skip("CalculiX is not installed")

    def solve(kind, stick=()):
        d = _bar_on_pads(kind, stick)
        r = VerifierResult("fea")
        m = run_thermal(d, d.thermalcases[0], r)
        assert not [f for f in r.findings if f.severity == "error"]
        return m

    free = solve("sliding free: a washer under a spring")
    assert free["sliding_contacts"][0]["located_in_plane_at"] is None
    assert free["probe_movement_mm"]["end"][0] == pytest.approx(ALPHA["al6061"] * 60.0 * 115.0, rel=0.12)
    stuck = solve("sliding free: a washer under a spring", stick=[("bar", "pad_b")])
    bonded = solve("bond")
    assert "sliding_contacts" not in stuck and stuck["sliding_contacts_taken_as_stuck"] == ["bar / pad_b"]
    assert stuck["bow_mm"]["bar"] == pytest.approx(bonded["bow_mm"]["bar"], rel=1e-6)
    assert free["bow_mm"]["bar"] < 0.6 * stuck["bow_mm"]["bar"]          # what is left is the bimetal at the bonded pad a
    assert stuck["probe_movement_mm"]["end"][0] < 0.6 * free["probe_movement_mm"]["end"][0]
