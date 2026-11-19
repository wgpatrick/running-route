"""Known-answer tests for the checker problems reported by the printer_v8 design pass (docs/PRINTER_V8.md, "Checker
behaviour I think is wrong or worth a look") and by the reference machine. Small purpose-built designs; answers by
hand or by construction; each tested both ways (the bad case fails, the good case passes)."""
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from build123d import Box, Cylinder, Location, Pos

sys.path.insert(0, str(Path(__file__).parent))

from test_known_answers_fit import bed_machine, clearances, codes, find, support      # noqa: E402

from mechloop.model import Adjustment, Design, LoadCase, ThermalCase                  # noqa: E402
from mechloop.parts import add_screw, clearance_hole, place                           # noqa: E402
from mechloop.report import VerifierResult, without_timings                           # noqa: E402
from mechloop.tolerance import stackup as SU                                          # noqa: E402
from mechloop.verifiers import bed_support as BS                                      # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
THREE = ((-90.0, -90.0), (90.0, -90.0), (0.0, 120.0))


# ===================================================================== 1. a part clamped by screws is located by them
def deck_on_posts(screws=True):
    """A machined deck 30 mm ABOVE a machined base, held by four M5 screws that pass through it and thread into the base
    (in reality with a spacer or jam nuts on each; none is drawn, so the two plates do not touch)."""
    d = Design("deck", base="base")
    d.add("base", Pos(0, 0, -5) * Box(100, 100, 10), material="al6061")
    deck = Pos(0, 0, 32.5) * Box(100, 100, 5)
    pts = [(-40, -40), (40, -40), (-40, 40), (40, 40)]
    for x, y in pts:
        deck -= Pos(x, y, 32.5) * Cylinder(clearance_hole("M5") / 2, 5)
    d.add("deck", deck, material="al6061")
    if screws:
        for i, (x, y) in enumerate(pts):
            add_screw(d, f"post{i}", "M5", 45, at=(x, y, 35), threads_into="base", clamps=("deck",))
    return d


def test_a_plate_held_on_screws_without_touching_is_located_by_those_screws():
    """Four screws clamp the deck to the base across a 30 mm gap. The deck is located by that screwed joint: it is in
    the stack-up, its height scatters by the two parts' seating accuracy (hundredths of a millimetre, not millimetres),
    and it stays level to the same order. Without the rule (the old behaviour) it was "not tied to the base". A deck
    that merely hovers, with no screws, is still not located."""
    B = SU.Build(deck_on_posts(), 2000)
    assert "deck" in B.A and B.unplaced == []
    assert B.screwed_apart == [{"parts": ["base", "deck"], "screws": ["post0", "post1", "post2", "post3"]}]
    z = B.at("deck", (0, 0, 35))[:, 2] - 35.0
    assert 0.005 < z.std() < 0.15
    tilt = B.at("deck", (40, 0, 35))[:, 2] - B.at("deck", (-40, 0, 35))[:, 2]
    assert np.percentile(np.abs(tilt), 99.7) < 0.3
    SU.SCREWED_JOINTS = False
    try:
        old = SU.Build(deck_on_posts(), 2000)
        assert old.unplaced == ["deck"] and "deck" not in old.A          # what the v8 pass saw: four screws, "not tied to the base"
    finally:
        SU.SCREWED_JOINTS = True
    loose = SU.Build(deck_on_posts(screws=False), 2000)
    assert loose.unplaced == ["deck"]                                     # nothing holds it: still reported, never located


# ===================================================================== 2. three screws and one block per rail is not a cantilever
def floating(d):
    d.adjustments.append(Adjustment("floating nut", "float", range_mm=0.5, joint="z"))
    return d


def ratings_z(d):
    from mechloop.verifiers.ratings import verify_ratings

    r = verify_ratings(d)
    return r.metrics["guide_loads"]["z"], [f for f in r.findings if f.code == "cantilever_on_guide_blocks"]


def test_lead_screw_nuts_count_as_supports_in_the_cantilever_finding():
    """3 kg 200 mm in front of the bed, one guide block per rail. On ONE screw behind the bed it hangs from the blocks
    (which resist tilt only over their own ball track): the body nods well below 100 Hz and the finding is raised. On
    THREE screws round the bed the same mass sits between supports: hundreds of hertz, no finding, and the metrics
    say the nuts were counted. Three screws in ONE LINE do not hold tilt across that line: the finding must stay."""
    far = dict(blocks_per_rail=1, payload_at=(0.0, -100.0))
    g, f = ratings_z(bed_machine(**far))
    assert len(f) == 1 and g["tilt_mode_hz"] < 100 and "supports_counted" not in g
    g3, f3 = ratings_z(bed_machine(screws=THREE, sync="belt", **far))
    assert f3 == [] and g3["tilt_mode_hz"] > 3 * g["tilt_mode_hz"]
    assert g3["supports_counted"]["lead_screw_nuts"] == ["nut0", "nut1", "nut2"] and "along its screw only" in g3["supports_counted"]["nut_holds"]
    assert g3["sag_at_mass_centre_mm_per_kg"] < 0.2 * g["sag_at_mass_centre_mm_per_kg"]
    gl, fl = ratings_z(bed_machine(screws=((-90.0, 120.0), (0.0, 120.0), (90.0, 120.0)), sync="belt", **far))
    assert len(fl) == 1 and "3 lead-screw nuts" in fl[0].message and gl["tilt_mode_hz"] < 100


def test_level_over_travel_uses_all_supports_and_agrees_with_the_old_formula_where_guides_alone_hold_tilt():
    """Rail running accuracy by Hiwin's table for the travel (class C). One block per rail and ONE screw: the block follows its rail's slope
    over its 32.4 mm ball track and nothing else holds the tilt: parallelism / 32.4 x the reach to the far corner, the
    earlier formula, within a few per cent, and the finding at a 0.1 mm layer. The same blocks with THREE screws: the
    screws hold the plane, the blocks' wander barely moves a corner (under a tenth of that), no finding."""
    d1 = bed_machine(blocks_per_rail=1)
    d1.printer["layer_height"] = 0.1
    m1, r1 = support(d1)
    lv = m1["level_over_travel"]
    assert lv["from_rail_running_accuracy_mm"] == pytest.approx(lv["guides_alone_formula_mm"], rel=0.05)
    assert lv["guides_alone_formula_mm"] == pytest.approx(lv["rail_running_parallelism_mm"] / 32.4 * lv["furthest_print_corner_from_guides_mm"], rel=0.01)
    assert "bed_level_changes_over_travel" in codes(r1, "warning")
    d3 = floating(bed_machine(screws=THREE, blocks_per_rail=1, sync="belt"))
    d3.printer["layer_height"] = 0.1
    m3, r3 = support(d3)
    assert m3["level_over_travel"]["from_rail_running_accuracy_mm"] < 0.1 * lv["from_rail_running_accuracy_mm"]
    assert not [f for f in find(r3, "bed_level_changes_over_travel") if "running accuracy" in f.message]
    # two blocks per rail, one screw: the old formula's own case (slope over the block spacing), same answer within 15 %
    m2, _ = support(bed_machine())
    lv2 = m2["level_over_travel"]
    assert lv2["from_rail_running_accuracy_mm"] == pytest.approx(lv2["guides_alone_formula_mm"], rel=0.15)


def test_rails_and_screws_both_holding_the_tilt_is_an_over_constraint_and_screws_alone_is_not():
    """Three screws. With TWO blocks per rail the rails hold the bed's tilt as stiffly as the screws: two redundant
    supports, and a screw height error turns into force (tens of newtons on a block for 0.02 mm) that unseats
    gravity-seated nuts: warning z_tilt_over_constrained. With ONE block per rail the blocks do not resist the plane
    the screws set: no redundant support, no force on a block, no over-constraint finding."""
    m2, r2 = support(floating(bed_machine(screws=THREE, blocks_per_rail=2, sync="belt")))
    assert m2["constraint"]["redundant_screw_supports"] == 2 and m2["constraint"]["redundancy"]["modes_held_by_guides_too"] == 2
    f = find(r2, "z_tilt_over_constrained")
    assert len(f) == 1 and f[0].severity == "warning" and f[0].data["unseats_on_synchronisation_error_alone"]
    assert m2["screw_synchronisation"]["force_on_a_guide_block_n"] > 20
    m1, r1 = support(floating(bed_machine(screws=THREE, blocks_per_rail=1, sync="belt")))
    assert m1["constraint"]["redundant_screw_supports"] == 0 and find(r1, "z_tilt_over_constrained") == []
    assert m1["screw_synchronisation"]["force_on_a_guide_block_n"] < 1.0
    assert max(m1["constraint"]["redundancy"]["guide_over_screw_stiffness_by_mode"]) < BS.GUIDES_HOLD_TILT_RATIO
    # one screw, two blocks per rail: the rails alone hold the tilt, nothing is redundant
    m0, r0 = support(bed_machine())
    assert m0["constraint"]["redundant_screw_supports"] == 0 and "nut_seating_and_lead_error" not in m0


# ===================================================================== 3. lead error and nut seating
def test_lead_error_accumulates_over_travel_and_uses_the_catalogue_figure_when_there_is_one():
    """Travel 100 mm. No lead accuracy on the screw part: the class value, 0.1 mm per 300 mm, marked assumed:
    0.0333 mm per screw; the three levels are sync, sync + that, sync + twice that (0.02, 0.0533, 0.0867 for a belt).
    With ratings['lead_accuracy_mm_per_300mm'] = 0.03 on every screw: 0.01 mm, not assumed. Independent motors carry
    the same lead error on top of their own synchronisation error (2 full steps of an 8 mm lead: 0.08 mm)."""
    d = floating(bed_machine(screws=THREE, blocks_per_rail=1, sync="belt"))
    st = support(d)[0]["nut_seating_and_lead_error"]
    assert st["lead_accuracy"]["assumed"] and st["lead_accuracy"]["mm_per_300mm"] == BS.LEAD_ACCURACY_ASSUMED_MM_PER_300 == 0.1
    assert st["lead_error_over_travel_mm"] == pytest.approx(0.1 / 300 * 100, abs=1e-4)
    assert [lv["height_error_mm"] for lv in st["levels"]] == pytest.approx([0.02, 0.02 + 0.0333, 0.02 + 0.0667], abs=2e-4)
    for c in d.components:
        if c.name.startswith("screw"):
            c.ratings["lead_accuracy_mm_per_300mm"] = 0.03
    st2 = support(d)[0]["nut_seating_and_lead_error"]
    assert not st2["lead_accuracy"]["assumed"] and st2["lead_error_over_travel_mm"] == pytest.approx(0.01, abs=1e-4)
    ind = support(floating(bed_machine(screws=THREE, blocks_per_rail=1)))[0]["nut_seating_and_lead_error"]
    assert [lv["height_error_mm"] for lv in ind["levels"]] == pytest.approx([0.08, 0.08 + 0.0333, 0.08 + 0.0667], abs=2e-4)


def test_nut_seating_loads_balance_the_weight_and_a_gravity_seated_nut_lifts_when_its_load_would_go_negative():
    """The seating loads are statics: they add up to the moving weight. A nut's linear margin at a height error E is its
    seating load less E times its sensitivity. Two blocks per rail (rails hold the tilt): the sensitivity is thousands
    of N/mm, the margin at 0.02 mm is far below zero, and the contact solution has that nut carrying exactly nothing
    while the nuts still seated carry the whole weight (the guides are free along the rail). One block per rail: the
    sensitivity is ten times smaller."""
    d = floating(bed_machine(screws=THREE, blocks_per_rail=2, sync="belt"))
    m, r = support(d)
    st = m["nut_seating_and_lead_error"]
    W = m["moving_mass_on_guides"]["moving_mass_kg"] * BS.G
    assert sum(v["seating_load_n"] for v in st["nuts"].values()) == pytest.approx(W, rel=2e-3)
    assert st["nut_seating"]["kind"] == "gravity" and st["nut_seating"]["reverse_gap_mm"] is None
    n0 = st["nuts"]["nut0"]
    assert n0["unloads_at_height_error_mm"] == pytest.approx(n0["seating_load_n"] / n0["load_change_n_per_mm_of_height_error"], abs=2e-4)
    lv = st["levels"][0]
    assert lv["nut_load_margin_n"]["nut0"] == pytest.approx(n0["seating_load_n"] - 0.02 * n0["load_change_n_per_mm_of_height_error"], abs=0.1)
    assert lv["nut_load_margin_n"]["nut0"] < 0
    assert lv["a_nut_unseats"] and lv["worst_case"]["least_nut_load_n"] == 0.0 and lv["worst_case"]["nuts_not_seated"]
    # the contact solution itself: weight carried by the seated nuts only, never a pulling nut
    lay = BS.layout(d)
    model = BS.support_model(d, lay)
    com = np.array(m["moving_mass_on_guides"]["mass_centre"])
    grav = np.concatenate([[0, 0, -W], np.cross(com - model["O"], [0, 0, -W])])
    sol = BS.contact_solve(model, lay, grav, {"nut0": -0.05}, None)
    assert sol["state"]["nut0"] == "free" and sol["nut_force_n"]["nut0"] == 0.0
    assert min(sol["nut_force_n"].values()) >= 0.0 and sum(sol["nut_force_n"].values()) == pytest.approx(W, rel=5e-3)
    # a captive nut (fixed both ways, 0.1 mm backlash assumed) bears again on its other flank once the gap is taken up
    d.joints[-1].drive["nut_seating"] = "captive"
    cap = support(d)[0]["nut_seating_and_lead_error"]
    assert cap["nut_seating"]["kind"] == "captive" and cap["nut_seating"]["reverse_gap_mm"] == BS.NUT_BACKLASH_ASSUMED_MM
    sol2 = BS.contact_solve(model, lay, grav, {"nut0": -0.5}, 0.1)
    assert sol2["state"]["nut0"] == "reversed" and sol2["nut_force_n"]["nut0"] < 0
    one = support(floating(bed_machine(screws=THREE, blocks_per_rail=1, sync="belt")))[0]["nut_seating_and_lead_error"]
    assert one["nuts"]["nut0"]["load_change_n_per_mm_of_height_error"] < 0.2 * n0["load_change_n_per_mm_of_height_error"]


# ===================================================================== 4. a magnet-held sheet slides on its plate
def strip(kind):
    d = Design("bimetal", base="plate")
    d.add("plate", Pos(0, 0, 1.5) * Box(120, 20, 3), material="al6061")
    d.add("sheet", Pos(0, 0, 3.5) * Box(120, 20, 1), material="steel")
    d.join("sheet", "plate", kind)
    d.thermalcases.append(ThermalCase("hot", ["plate", "sheet"], fixed=[("plate", lambda f: abs(f.center().X + 60) < 1e-6)],
                                      temps={"plate": 60.0, "sheet": 60.0}, flatness=("sheet", "z", None), mesh_size=3.0))
    return d


def test_a_bonded_bimetal_bows_by_timoshenko_and_a_magnet_held_sheet_does_not():
    """3 mm aluminium under 1 mm steel, 120 mm long, clamped at one end, heated 60 K. Bonded, it is a bimetal strip:
    curvature 6 (a1 - a2) dT (1 + m)^2 / (h (3 (1 + m)^2 + (1 + m n)(m^2 + 1 / (m n)))) with m = 3, n = 68.9 / 200,
    h = 4 mm: 2.45e-4 / mm, tip 1.76 mm (FEA within 10 %). Joined "magnet" or "sliding" the sheet carries normal load
    and slides in its plane: nothing bends it, the bow is under 3 % of the bonded one. The design can say which."""
    from mechloop.verifiers.fea import ALPHA, run_thermal

    if not __import__("shutil").which("ccx"):
        pytest.skip("CalculiX is not installed")
    m_, n_, h = 3.0, 68900.0 / 200000.0, 4.0
    kappa = 6 * (ALPHA["al6061"] - ALPHA["steel"]) * 60.0 * (1 + m_) ** 2 / (h * (3 * (1 + m_) ** 2 + (1 + m_ * n_) * (m_ ** 2 + 1 / (m_ * n_))))
    bow = {}
    for kind in ("bond", "magnet", "sliding"):
        d = strip(kind)
        r = VerifierResult("fea")
        m = run_thermal(d, d.thermalcases[0], r)
        assert not r.findings
        bow[kind] = m["bow_mm"]["sheet"]
        assert ("sliding_contacts" in m) == (kind != "bond") and d.slides_on("sheet", "plate") == (kind != "bond")
    assert bow["bond"] == pytest.approx(kappa * 120.0 ** 2 / 2, rel=0.10)
    assert bow["magnet"] < 0.03 * bow["bond"] and bow["sliding"] == pytest.approx(bow["magnet"], abs=1e-4)


# ===================================================================== 5. tension, compression and shear across the layers
def printed_post(force, held_z, loaded_z, loaded_x=None):
    from mechloop.verifiers.manufacture import verify_manufacture

    d = Design("t")
    d.add("p", Pos(0, 0, 20) * Box(20, 20, 40) + Pos(20, 0, 12.5) * Box(20, 20, 5), material="petg", meta={"print_up": "+Z"})      # a ledge on its side, 10 to 15 mm up
    loaded = (lambda f: abs(f.center().Z - loaded_z) < 1e-6) if loaded_x is None else \
        (lambda f: abs(f.center().Z - loaded_z) < 1e-6 and f.center().X > loaded_x)
    d.loadcases.append(LoadCase("load", "p", fixed=lambda f: abs(f.center().Z - held_z) < 1e-6 and f.center().X < 9.0, loaded=loaded, force=force))
    r = verify_manufacture(d)
    return {f.code: f for f in r.findings}, r.metrics["parts"]["p"]


def test_a_load_pressing_the_layers_together_is_not_flagged_and_one_pulling_or_shearing_them_is():
    """A post printed standing up, held on its foot. A load on its top face pointing DOWN presses the layers together:
    benign, an info only. The same load pointing UP pulls them apart: warning, "tension". A downward load on a ledge
    BESIDE the post (the loaded face 20 mm to the side of the held one and only 15 mm above it) crosses the layers in shear and bending:
    warning, "shear". The direction of the force alone (all three are 100 % along the build direction) cannot tell."""
    f, row = printed_post((0, 0, -100.0), held_z=0.0, loaded_z=40.0)
    assert "load_across_layers" not in f and f["load_presses_layers_together"].severity == "info"
    assert row["loads_against_layers"]["load"] == {"share_along_build_axis": 1.0, "kind": "compression"}
    f, row = printed_post((0, 0, 100.0), held_z=0.0, loaded_z=40.0)
    assert f["load_across_layers"].severity == "warning" and f["load_across_layers"].data["kind"] == "tension"
    assert "pulls the layers apart" in f["load_across_layers"].message and "load_presses_layers_together" not in f
    f, row = printed_post((0, 0, -100.0), held_z=0.0, loaded_z=15.0, loaded_x=12.0)
    assert f["load_across_layers"].data["kind"] == "shear" and "shear and bending" in f["load_across_layers"].message
    assert "pulls the layers apart" not in f["load_across_layers"].message


def test_layer_load_kind_by_geometry():
    from mechloop.verifiers.dfm_print import layer_load_kind

    up = np.array([0, 0, 1.0])
    assert layer_load_kind([0, 0, -1], [0, 0, 40], up) == "compression" and layer_load_kind([0, 0, 1], [0, 0, 40], up) == "tension"
    assert layer_load_kind([0, 0, 1], [0, 0, -40], up) == "compression" and layer_load_kind([0, 0, -1], [0, 0, -40], up) == "tension"
    assert layer_load_kind([0, 0, -1], [30, 0, 5], up) == "shear"
    assert layer_load_kind([0, 0, -1], [0, 0, 0], up) == "unknown" and layer_load_kind([0, 0, -1], None, up) == "unknown"


# ===================================================================== 6. the sensor's own nuts and its metal-free zone
def test_own_nuts_on_the_clamp_faces_are_mounting_not_surrounding_metal_and_still_clamp():
    """E2E-X10ME1 (unshielded M18: 22 mm of head proud of metal, 55 mm diameter clear), clamped in a plastic bracket
    22 to 25 mm above the face with its two nuts as separate parts. The front nut's bearing face is at 22 mm and its
    body reaches to 18 mm: inside the zone's depth, and it is not counted, because it is the sensor's own mounting; the
    metrics name it. Both nuts are counted for clamping, and taking the rear one away is `probe_nuts_missing`. A THIRD
    nut run further down the barrel (bearing at 14 mm, not on a clamp face) is not doing the mounting: it is metal in
    the zone like any other part, although it carries the same tag."""
    from test_known_answers_checkers import homing_z, probe_head

    from mechloop.parts.probes import e2e_nut
    from mechloop.verifiers.subsystems import verify_subsystems

    d = probe_head(nuts="separate")
    f, z = homing_z(d)
    mz = z["mounting"]["metal_free_zone"]
    assert "probe_metal_in_clear_zone" not in f and "probe_nuts_missing" not in f and "probe_not_clamped" not in f
    assert z["mounting"]["nuts"] == {"front": ["probe_nut_front"], "rear": ["probe_nut_rear"]}
    assert mz["own_nuts_not_counted"]["probe_nut_front"] == {"bearing_face_behind_sensing_face_mm": 22.0, "inside_zone_depth": False}
    assert set(mz["own_nuts_not_counted"]) == {"probe_nut_front", "probe_nut_rear"} and "mounting" in mz["own_nuts_basis"]
    assert z["mounting"]["metal_in_zone"] == []
    # a nut that is not on a clamp face is surrounding metal
    d2 = probe_head(nuts="separate")
    pc = d2.get("probe")
    P = np.array(pc.meta["placement"], dtype=float)
    from build123d import Plane

    place(d2, "stray_nut", e2e_nut("E2E-X10ME1"), Location(Plane(origin=tuple(P[:, 3] + 14.0 * P[:, 2]), z_dir=tuple(-P[:, 2]))),
          body=pc.body, probe_nut_of="probe")
    d2.join("stray_nut", "probe", "thread")
    f2, z2 = homing_z(d2)
    assert f2["probe_metal_in_clear_zone"].severity == "error"
    assert [h["part"] for h in z2["mounting"]["metal_in_zone"]] == ["stray_nut"] and "stray_nut" not in z2["mounting"]["metal_free_zone"]["own_nuts_not_counted"]
    assert "are part of its mounting" in f2["probe_metal_in_clear_zone"].message
    # and the nuts still count for clamping: without the rear one the sensor is not held
    d3 = probe_head(nuts="separate")
    d3.components[:] = [c for c in d3.components if c.name != "probe_nut_rear"]
    f3, _ = homing_z(d3)
    assert f3["probe_nuts_missing"].severity == "error"


# ===================================================================== 7. a stream that could not be read is "not run"
def _stream(tmp_path, exit_time, last_step_s, motor_off=True):
    from test_firmware import _dump

    hz = 64_000_000
    ticks = int(last_step_s * hz)
    lines = [f"queue_step oid=0 interval={ticks // 1000} count=1000 add=0"]
    if motor_off:
        lines.append(f"queue_digital_out oid=16 clock={int((exit_time + 0.1) * hz) % (1 << 32)} on_ticks=1")
    log = f"INFO:root:Exiting (print time {exit_time:.3f}s)\n"
    return _dump(tmp_path, lines), log


def test_a_stream_that_stops_before_the_print_time_klippy_logged_is_cut_short(tmp_path):
    """Klipper logs "Exiting (print time 221.311s)". A complete stream carries the motor-off commands at that time and
    its last step a fraction of a second earlier (measured: 0.11 to 0.16 s). The two v8 runs that "could not be
    decoded" stopped 1.78 and 4.82 s early with a clean log: cut short, by the measured gap."""
    from test_firmware import CFG, HZ

    from mechloop.twin import firmware as fw

    for exit_t, last, off, cut in ((221.311, 221.165, True, False), (221.311, 221.165, False, False),
                                   (221.311, 219.534, False, True), (213.109, 208.285, False, True)):
        p, log = _stream(tmp_path, exit_t, last, off)
        dec = fw.decode(p, CFG, HZ)
        got = fw.stream_cut_short(p, log, dec["steps"], HZ)
        assert (got is not None) == cut
        if cut:
            assert got["missing_s"] == pytest.approx(exit_t - last, abs=0.01) and got["last_command"] == "queue_step"
    p, _ = _stream(tmp_path, 100.0, 50.0, False)
    assert fw.stream_cut_short(p, "no exit line", fw.decode(p, CFG, HZ)["steps"], HZ) is None       # nothing to compare with: not judged here


def test_a_sweep_point_that_was_not_run_is_neither_clean_nor_the_first_failure():
    """Sweep 1x to 6x of 4,000 mm/s^2: clean, NOT RUN, clean, clean, lost steps. Highest clean is 4x (16,000), the
    first failure 5x (20,000); the point that was not run is listed, loudly, and counts as neither. Before, it was
    scored as the first failure and "highest clean" came out as 1x. A point not run ABOVE the last clean one leaves
    the figure open, and the summary says so."""
    from mechloop.twin.score import sweep_summary

    ok = {"ok": True, "errors": [], "not_run": None}
    nr = {"ok": False, "errors": ["firmware_not_decoded"], "not_run": {"reason": "firmware_not_decoded", "detail": "cut short"}}
    bad = {"ok": False, "errors": ["lost_steps"], "not_run": None, "lost_step_axes": ["x"]}
    s = sweep_summary({1: ok, 2: nr, 3: ok, 4: ok, 5: bad, 6: bad}, 4000.0)
    assert s["highest_clean_accel_mm_s2"] == 16000.0 and s["first_failure"]["accel_mm_s2"] == 20000.0
    assert [r_["status"] for r_ in s["table"]] == ["clean", "NOT RUN", "clean", "clean", "failed", "failed"] and s["table"][1]["ok"] is None
    assert s["not_run"][0]["accel_mm_s2"] == 8000.0 and "NOT RUN" in s["not_run_warning"] and "stands on its neighbours" in s["not_run_warning"]
    s2 = sweep_summary({1: ok, 2: ok, 3: nr, 4: bad}, 4000.0)
    assert s2["highest_clean_accel_mm_s2"] == 8000.0 and "may be higher" in s2["not_run_warning"] and "12000" in s2["not_run_warning"]
    s3 = sweep_summary({1: ok, 2: bad, 3: ok}, 4000.0)                # a real failure still ends the clean run
    assert s3["highest_clean_accel_mm_s2"] == 4000.0 and "not_run" not in s3


def test_klipper_output_cut_short_is_rerun_and_if_it_stays_cut_the_print_is_not_run(tmp_path, monkeypatch):
    """Real Klipper on printer_v4, with its output file cut 3,000 commands short after the fact (what a loaded machine
    does to it). Cut once: the run is repeated and the print goes through, with the repeat on record. Cut every time:
    the print is NOT RUN (`firmware_not_decoded`, `not_run` in the report), never a failed print."""
    from test_firmware import _klipper

    from mechloop.runner import load_design
    from mechloop.twin import firmware as fw
    from mechloop.twin import printer_map_for, run_print
    from mechloop.twin.evals import summarise

    _klipper()
    real = fw.run_klippy
    calls = {"n": 0, "cut": 1}

    def cutting(cfg_text, gcode_text, workdir):
        run = real(cfg_text, gcode_text, workdir)
        calls["n"] += 1
        if calls["n"] <= calls["cut"]:
            lines = Path(run["dump"]).read_text().splitlines()
            keep = max(i for i, ln in enumerate(lines[:-3000]) if ln.startswith("queue_step"))
            Path(run["dump"]).write_text("\n".join(lines[:keep + 1]) + "\n")
        return run

    monkeypatch.setattr(fw, "run_klippy", cutting)
    d = load_design(ROOT / "designs" / "printer_v4.py")
    kw = dict(name="chip", render=False, collisions=False, firmware="klipper", firmware_opts={"input_shaper": False, "pressure_advance": False, "bed_mesh": False})
    rep = run_print(d, Pos(0, 0, 1) * Box(10, 10, 2), tmp_path / "a", printer_map_for(d), **kw)
    assert rep["ok"] and calls["n"] == 2 and len(rep["firmware"]["stream_cut_short_and_rerun"]) == 1
    assert rep["firmware"]["stream_cut_short_and_rerun"][0]["missing_s"] > 1.0 and "not_run" not in rep
    calls.update(n=0, cut=99)
    rep = run_print(d, Pos(0, 0, 1) * Box(10, 10, 2), tmp_path / "b", printer_map_for(d), **kw)
    assert not rep["ok"] and calls["n"] == fw.STREAM_ATTEMPTS
    assert [f["code"] for f in rep["findings"]] == ["firmware_not_decoded"] and rep["not_run"]["reason"] == "firmware_not_decoded"
    assert "NOT RUN" in rep["findings"][0]["message"] and summarise(rep)["not_run"]["reason"] == "firmware_not_decoded"
    # second line of defence: the CONFIGURED run (input shaper on) cut short while the planned run is whole, and the
    # cut-short test switched off. Its motion then stops millimetres from where the planned run ends; that used to pass
    # as "command smoothing" with a 9 mm cross-track error and ok: true. Now: not run.
    monkeypatch.setattr(fw, "stream_cut_short", lambda *a, **k: None)
    calls.update(n=0, cut=0)

    def cut_second(cfg_text, gcode_text, workdir):
        run = real(cfg_text, gcode_text, workdir)
        calls["n"] += 1
        if calls["n"] == 2:
            lines = Path(run["dump"]).read_text().splitlines()
            keep = max(i for i, ln in enumerate(lines[:-3000]) if ln.startswith("queue_step"))
            Path(run["dump"]).write_text("\n".join(lines[:keep + 1]) + "\n")
        return run

    monkeypatch.setattr(fw, "run_klippy", cut_second)
    rep = run_print(d, Pos(0, 0, 1) * Box(10, 10, 2), tmp_path / "c", printer_map_for(d), name="chip", render=False, collisions=False,
                    firmware="klipper")
    assert calls["n"] == 2 and not rep["ok"] and rep["not_run"]["reason"] == "firmware_not_decoded"
    assert "configured Klipper run ends" in rep["findings"][0]["message"] or "different numbers of Z steps" in rep["findings"][0]["message"]


# ===================================================================== 8. a verify is a function of the design alone
MINI = '''
import sys
sys.path.insert(0, {tests!r})
from build123d import Box, Cylinder, Pos
from mechloop import Design, Joint
from mechloop.parts import add_screw, clearance_hole


def build():
    if {electrical!r}:
        from test_electrical import rig
        return rig()
    d = Design("mini", envelope=(300, 200, 120), base="base")
    d.add("base", Pos(0, 0, -5) * Box(200, 120, 10), material="al6061")
    names = []
    for i, x in enumerate((-70, -35, 0, 35, 70)):
        post = Pos(x, 0, 15) * Box(20, 60, 30) - Pos(x, 20, 15) * Cylinder(clearance_hole("M4") / 2, 30) - Pos(x, -20, 15) * Cylinder(clearance_hole("M4") / 2, 30)
        d.add(f"post{{i}}", post, material="petg")
        names.append(f"post{{i}}")
        for k, y in enumerate((20, -20)):
            add_screw(d, f"s{{i}}{{k}}", "M4", 35, at=(x, y, 30), threads_into="base", clamps=(f"post{{i}}",))
    d.add("lid", Pos(0, 0, 32.5) * Box(190, 60, 5) - sum((Pos(x, y, 32.5) * Cylinder(4.5, 5) for x in (-70, -35, 0, 35, 70) for y in (20, -20)), Pos(0, 0, 0) * Box(0.1, 0.1, 0.1)), material="petg")
    d.join("lid", "post0", "bond")
    d.add("car", Pos(0, 50, 5) * Box(30, 20, 10), material="al6061", body="car")
    d.joints.append(Joint("x", "slide", "world", "car", (1, 0, 0), range=(-60, 60), max_effort=10))
    return d
'''


def _verify_in_a_fresh_process(path, out, seed, only):
    env = {**os.environ, "PYTHONHASHSEED": str(seed)}
    p = subprocess.run([sys.executable, "-m", "mechloop", "verify", str(path), "--no-render", "--out", str(out), "--only", *only],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=900)
    return json.loads(p.stdout)


@pytest.mark.parametrize("electrical,only", [(False, ["geometry", "interference", "tolerance", "manufacture", "ratings", "motion", "assemblability"]),
                                            (True, ["geometry", "electrical", "subsystems"])])
def test_two_verifies_in_separate_processes_with_different_hash_seeds_agree_apart_from_timings(tmp_path, electrical, only):
    """The same small design verified twice, each time in a fresh interpreter with a different PYTHONHASHSEED (so every
    set and dict keyed by strings iterates in a different order) and into a different folder (so nothing an earlier run
    left on disk is there). Everything but timings
    and file paths (mechloop.report.without_timings) must be identical."""
    f = tmp_path / ("mini_el.py" if electrical else "mini.py")
    f.write_text(MINI.format(tests=str(Path(__file__).parent), electrical=electrical))
    a = _verify_in_a_fresh_process(f, tmp_path / "a", 1, only)
    b = _verify_in_a_fresh_process(f, tmp_path / "b", 4242, only)
    assert a["metrics"] and without_timings(a) == without_timings(b)
    assert a["summary"] != without_timings(a)["summary"]                # the timings are there, labelled, and were what was removed


def test_without_timings_removes_only_timings_and_paths():
    rep = {"summary": {"geometry": "pass (0 errors, 0 warnings, 15.1s)", "electrical": "skipped: not declared"},
           "metrics": {"geometry": {"vendor_cad": {"envelope": {"seconds": 11.0, "pairs_tested": 4}, "proxy_match_seconds": 3.5}},
                       "electrical": {"artifacts": {"printer_cfg": "/tmp/x"}, "power_w": 120.0}},
           "artifacts": {"seconds": {"verify": 3.0}, "iteration": 7}}
    assert without_timings(rep) == {"summary": {"geometry": "pass (0 errors, 0 warnings)", "electrical": "skipped: not declared"},
                                    "metrics": {"geometry": {"vendor_cad": {"envelope": {"pairs_tested": 4}}}, "electrical": {"power_w": 120.0}}}


def test_a_verify_does_not_read_the_pressure_advance_sweep_a_tune_left_on_disk(tmp_path, monkeypatch):
    """`mechloop tune` stores its sweep in <out>/<design>/tune/tuning.json and `score` / `print` use its best K. A verify
    must not: with such a file present and with none, the tuning a verify asks for is the same (the twin's assumed
    lag); only a caller that allows stored sweeps gets the swept value."""
    from mechloop.twin import PrinterMap, tuning

    class D:
        name = "toy"
        electrical = None

    pm = PrinterMap()
    (tmp_path / "toy" / "tune").mkdir(parents=True)
    (tmp_path / "toy" / "tune" / "tuning.json").write_text(json.dumps(
        {"pressure_advance": {"sweep": {"best": 0.077, "assumed_extruder_lag_s": pm.extruder_lag_s}}}))
    monkeypatch.setattr(tuning, "TUNING_ROOTS", [str(tmp_path)])
    assert tuning.pressure_advance(D, pm)["value"] == 0.077
    v = tuning.pressure_advance(D, pm, use_stored=False)
    assert v["value"] == pytest.approx(pm.extruder_lag_s) and "from_sweep" not in v


# ===================================================================== 9. a recessed screw head under a cover
def covered_screw(recess=0.2, sunk=True, cover="seated"):
    """A machined block with an M4 cap screw from the top (head 4 mm high, 7 mm across). sunk: the head sits in a
    counterbore `recess` deeper than the head; else on the block's top face. cover: "seated", a sheet lying on the
    block's top face over the screw; "bridge", a plate standing on two posts beside the block, `recess` above the
    proud head."""
    d = Design("covered", base="base")
    d.add("base", Pos(0, 0, -25) * Box(120, 60, 10), material="al6061")
    blk = Pos(0, 0, 0) * Box(40, 40, 20)
    blk -= Pos(0, 0, 0) * Cylinder(clearance_hole("M4") / 2, 20)
    top = 10.0
    if sunk:
        blk -= Pos(0, 0, top - (4.0 + recess) / 2) * Cylinder(4.0, 4.0 + recess)
    d.add("block", blk, material="al6061")
    d.add("foot", Pos(0, 0, -15) * Box(40, 40, 10) - Pos(0, 0, -15) * Cylinder(clearance_hole("M4") / 2 + 1.0, 10), material="al6061")
    d.join("foot", "base", "bond")
    head_under = top - (4.0 + recess) if sunk else top
    add_screw(d, "screw", "M4", 16 if sunk else 30, at=(0, 0, head_under), clamps=("block",), threads_into="foot")
    if cover == "seated":
        d.add("cover", Pos(0, 0, top + 0.4) * Box(40, 40, 0.8), material="steel")
        d.join("cover", "block", "magnet")
    elif cover == "bridge":
        for sx in (-1, 1):
            d.add(f"leg{sx}", Pos(sx * 40, 0, -20 + (top + 4.0 + recess + 20) / 2) * Box(10, 40, top + 4.0 + recess + 20), material="al6061")
        d.add("cover", Pos(0, 0, top + 4.0 + recess + 1.0) * Box(90, 40, 2), material="al6061")
    return d


def test_a_recessed_head_under_a_seated_cover_is_a_designed_fit_and_a_proud_head_under_a_bridge_is_a_clearance():
    """A screw head 0.2 mm below the face of the block it clamps, with a sheet lying on that face: the gap is the
    counterbore's depth less the head's height, both features of one part and its screw: a designed fit, not reported
    (the reference machine's bed sheet over its three bed screws). A head standing PROUD of the block with a plate on
    two legs 0.2 mm above it is a real clearance between separately located parts: reported. So is a cover that is
    not seated on the block the screw is let into."""
    m, r = clearances(covered_screw())
    assert codes(r) == []
    assert m["search"]["designed_contacts_skipped"].get("a screw head recessed in a counterbore, under a part seated on that face") == 1
    m, r = clearances(covered_screw(sunk=False, cover="bridge"))
    pairs = [set(p["parts"]) for p in m["pairs"]]
    assert {"cover", "screw"} in pairs
    assert any(set(f.data["parts"]) == {"cover", "screw"} for f in find(r, "clearance_closes_under_tolerance") + find(r, "clearance_below_minimum"))
    assert "a screw head recessed in a counterbore, under a part seated on that face" not in m["search"]["designed_contacts_skipped"]


# ===================================================================== 10. the autotune without klippy
def test_the_ported_relay_autotune_gives_klippers_own_gains_on_the_same_plant(monkeypatch):
    """PID_CALIBRATE on one thermal plant, twice: decided by Klipper's ControlAutoTune (pid_calibrate.py, when its
    source is installed) and by the line-for-line port in mechloop.electrical. Same peaks, same Ku = 4 (P / 2) / (pi a),
    same Kp, Ki, Kd to three decimals, for a hotend and a bed. (A report that the port gave half of Klipper's Ku could
    not be reproduced: at this Klipper commit the two agree exactly.)"""
    from test_electrical import rig

    from mechloop import electrical as E

    monkeypatch.delenv("MECHLOOP_HEATER_CONTROL", raising=False)
    if E.control_code()[0] is None:
        pytest.skip("Klipper's source is not installed: nothing to compare the port with")
    plants = E.thermal_plants(rig())
    for name, target in (("extruder", 210.0), ("extruder", 250.0), ("heater_bed", 60.0)):
        cfg = {"control": "pid", "max_power": 1.0, "max_temp": 400}
        monkeypatch.delenv("MECHLOOP_HEATER_CONTROL", raising=False)
        klippy = E.autotune_pid(plants[name], cfg, target)
        ra = E.simulate_heater(plants[name], {**cfg, "verify_heater": None}, target, 900.0, autotune=True)
        monkeypatch.setenv("MECHLOOP_HEATER_CONTROL", "port")
        port = E.autotune_pid(plants[name], cfg, target)
        rb = E.simulate_heater(plants[name], {**cfg, "verify_heater": None}, target, 900.0, autotune=True)
        assert "port" in rb["control_code"] and "ControlAutoTune" in ra["control_code"]
        assert [tuple(np.round(p, 6)) for p in ra["peaks"]] == [tuple(np.round(p, 6)) for p in rb["peaks"]]
        assert port == pytest.approx(klippy, rel=1e-6) and klippy[0] > 0
        # and the formula itself, on the port's peaks: amplitude a = half the last swing at the median cycle
        pk = rb["peaks"]
        pos = sorted((pk[p][0] - pk[p - 2][0], p) for p in range(4, len(pk)))[len(range(4, len(pk))) // 2][1]
        ku = 4.0 * 0.5 / (math.pi * 0.5 * abs(pk[pos][1] - pk[pos - 1][1]))
        assert port[0] == pytest.approx(0.6 * ku * 255.0, abs=2e-3)


# ===================================================================== 11. what a screw head bears on; washers
def seated_screw(material="al6061", hole="standard", washer=False, size="M5", torque=None):
    """A steel block (top at z = 0) with a 5 mm plate of `material` on it, held by one cap screw from the top that
    threads into the block. hole: "standard" (close clearance), "slot" (clearance width, 20 mm long), or a diameter."""
    from mechloop.parts import SCREW

    d = Design("seat", base="block")
    d.add("block", Pos(0, 0, -10) * Box(60, 60, 20), material="steel")
    clr = SCREW[size][4]
    plate = Pos(0, 0, 2.5) * Box(60, 60, 5)
    if hole == "slot":
        plate -= Pos(0, 0, 2.5) * Box(20, clr, 5)
    else:
        plate -= Pos(0, 0, 2.5) * Cylinder((clr if hole == "standard" else float(hole)) / 2, 5)
    d.add("plate", plate, material=material)
    add_screw(d, "s", size, 16, at=(0, 0, 5), threads_into="block", clamps=("plate",), washer=washer)
    if torque:
        d.manufacturing = {"tightening_torque_nm": {size: torque}}
    return d


def bearing(d):
    from mechloop.verifiers.bearing import head_bearing

    r = VerifierResult("ratings")
    return head_bearing(d, r), {f.code: f for f in r.findings}


def test_a_steel_head_on_steel_or_wrought_aluminium_at_the_class_torque_is_not_flagged():
    """M5 class 8.8 at Bossard's maximum for mu 0.14 (6.5 N.m, 7.0 kN; FST-040) on the head's ring over a 5.5 mm hole,
    pi (3.91^2 - 2.75^2) = 24.3 mm^2: 288 MPa. Under VDI 2230's p_G for AW-6082 (360, mapped to 6061) and S235 (490):
    no finding, no blanket "needs a washer"."""
    for mat in ("al6061", "steel"):
        m, f = bearing(seated_screw(mat))
        assert f == {} and m["seats_examined"] == 1
        w = m["worst"][0]
        assert w["seat_area_mm2"] == pytest.approx(math.pi * ((0.92 * 8.5 / 2) ** 2 - 2.76 ** 2), rel=0.02)
        assert w["preload_n"] == 7000 and w["tightening_torque_nm"] == 6.5 and w["bearing_pressure_mpa"] == pytest.approx(290, abs=6)
        assert "Bossard" in w["torque_basis"] and w["allowable_mpa"] == {"al6061": 360.0, "steel": 490.0}[mat] and "VDI 2230" in w["allowable_basis"]


def test_a_head_over_a_slot_or_an_oversize_hole_needs_a_washer_and_a_washer_clears_it():
    """M5 head (bearing diameter 7.8 mm) over a 5.5 mm slot: only the two slivers beside the slot carry it, about a
    third of the standard ring: error. Over a 6.6 mm hole: pi (3.91^2 - 3.3^2) = 13.8 mm^2, 57 %: error; over 6.0 mm,
    81 %: warning (marginal). An ISO 7089 washer (10 mm) over the same slot has more seat than a bare head on a
    standard hole: no finding. It is a catalogue part in the BOM and the head sits its 1 mm higher."""
    m, f = bearing(seated_screw(hole="slot"))
    assert f["screw_head_seat_too_small"].severity == "error" and 0.2 < f["screw_head_seat_too_small"].data["least_ratio"] < 0.45
    m, f = bearing(seated_screw(hole=6.6))
    assert f["screw_head_seat_too_small"].severity == "error" and f["screw_head_seat_too_small"].data["least_ratio"] == pytest.approx(0.57, abs=0.03)
    m, f = bearing(seated_screw(hole=6.0))
    assert f["screw_head_seat_too_small"].severity == "warning" and f["screw_head_seat_too_small"].data["least_ratio"] == pytest.approx(0.81, abs=0.03)
    d = seated_screw(hole="slot", washer=True)
    m, f = bearing(d)
    assert f == {} and m["on_washers"] == 1 and m["worst"][0]["bears_with"] == "head on washer s_washer"
    assert m["worst"][0]["seat_area_over_standard"] > 1.0
    w = d.get("s_washer")
    assert w.sku == "WASHER-M5" and w.meta["interfaces"] == {"od": 10.0, "bore": 5.3, "thickness": 1.1}
    assert d.joins[frozenset(("s", "s_washer"))] == "washer" and "s_washer" in d.fasteners[0].clamps
    zs = lambda dd: (dd.get("s").shape.bounding_box().min.Z, dd.get("s").shape.bounding_box().max.Z)
    assert zs(d) == pytest.approx(tuple(z + 1.1 for z in zs(seated_screw(hole="slot"))), abs=1e-6)       # 1.1 mm less thread in the block (the bought washer)
    from mechloop.verifiers.ratings import verify_ratings

    assert verify_ratings(d).metrics["bom"]["WASHER-M5"]["qty"] == 1


def test_a_bare_head_crushes_printed_plastic_and_a_washer_or_a_stated_torque_clears_it():
    """M3 clamping printed PETG, 0.5 N.m assumed for a joint with plastic in it: F = 0.5 / 0.58 mm = 862 N on
    pi (2.53^2 - 1.71^2) = 10.9 mm^2 = 79 MPa, above the printed yield (47 MPa, Prusament TDS): error. The sustained
    limit is PRT-030's DERIVED 5 MPa. Bare at a stated 0.02 N.m: 3 MPa, no finding; at 0.1 N.m: 16 MPa, over the limit and
    under yield: warning, which says what the seat carries. With an ISO 7089 washer (7 mm, 29.3 mm^2) at 0.06 N.m on a
    part printed solid: 3.5 MPa, no finding."""
    m, f = bearing(seated_screw("petg", size="M3"))
    assert f["screw_head_bearing_pressure"].severity == "error" and f["screw_head_bearing_pressure"].data["worst_mpa"] == pytest.approx(79, abs=3)
    assert f["screw_head_bearing_pressure"].data["allowable_mpa"] == 5.0 and "PRT-030" in m["worst"][0]["allowable_basis"]
    assert f["screw_head_bearing_pressure"].data["rule"] == "PRT-030"
    assert bearing(seated_screw("petg", size="M3", torque=0.02))[1] == {}
    m, f = bearing(seated_screw("petg", size="M3", torque=0.1))
    assert f["screw_head_bearing_pressure"].severity == "warning" and "declared" in m["worst"][0]["torque_basis"]
    assert m["worst"][0]["allowed_preload_n"] == pytest.approx(5.0 * m["worst"][0]["seat_area_mm2"], rel=0.01)
    d = seated_screw("petg", size="M3", washer=True, torque=0.06)
    d.get("plate").meta["print"] = {"infill": 1.0}
    m, f = bearing(d)
    assert f == {} and m["worst"][0]["bearing_pressure_mpa"] == pytest.approx(3.5, abs=0.3)


def test_the_printed_seat_limit_halves_between_40_and_60_degc_and_there_is_none_above():
    """PRT-030: 5 MPa to 40 degC, 2.5 MPa to 60 degC, no sustained clamp above 60. The washer joint at 0.06 N.m (3.5 MPa)
    passes at room temperature, is a warning on a part declared at 50 degC, and at 70 degC any clamp is."""
    for temp, ok in ((None, True), (50, False), (70, False)):
        d = seated_screw("petg", size="M3", washer=True, torque=0.06)
        d.get("plate").meta["print"] = {"infill": 1.0}
        if temp:
            d.get("plate").meta["service_temp_c"] = temp
        m, f = bearing(d)
        assert (f == {}) == ok
        assert m["worst"][0]["allowable_mpa"] == {None: 5.0, 50: 2.5, 70: 0.0}[temp]


def test_a_washer_over_sparse_infill_carries_less_than_over_solid_plastic():
    """The same washer (7 mm) at 0.075 N.m: 129 N on 29.3 mm^2 = 4.4 MPa. On a part printed solid that is under PRT-030's
    5 MPa: no finding. Printed to the default (3 walls of 0.45 mm round the hole, a 1.0 mm top skin, 25 % infill) the
    ring is 1.79 mm wide, wider than the skin: the 1.35 mm of perimeters round the hole carry their share in full, the
    rest (31 % of the ring) bears on infill at 25 %: the limit falls to 0.77 x 5 = 3.9 MPa and the same joint is a
    warning, which says so."""
    d = seated_screw("petg", size="M3", washer=True, torque=0.075)
    d.get("plate").meta["print"] = {"infill": 1.0}
    assert bearing(d)[1] == {}
    m, f = bearing(seated_screw("petg", size="M3", washer=True, torque=0.075))
    w = m["worst"][0]
    a_all, a_sol = math.pi * (3.5 ** 2 - 1.71 ** 2), math.pi * (3.06 ** 2 - 1.71 ** 2)
    assert f["screw_head_bearing_pressure"].severity == "warning" and "sparse infill" in w["over_sparse_infill"]
    assert w["allowable_mpa"] == pytest.approx(5.0 * (a_sol + 0.25 * (a_all - a_sol)) / a_all, abs=0.1)


def test_soft_aluminium_under_a_bare_head_is_a_warning_and_a_washer_spreads_it():
    """M5 at the class torque (7.0 kN, 290 MPa bare) on 5052-H32 sheet (p_G DERIVED from AW-5083: 285 MPa): warning
    (the seat embeds). On cast MIC-6 (p_G of cast AlSi9Cu3: 200 MPa) likewise. With an ISO 7089 washer the ring is
    pi (5^2 - 2.76^2) = 54.6 mm^2: 128 MPa, fine on both; the large series (15 mm) spreads it to 46 MPa."""
    assert bearing(seated_screw("al5052"))[1]["screw_head_bearing_pressure"].severity == "warning"
    assert bearing(seated_screw("al_mic6"))[1]["screw_head_bearing_pressure"].data["rule"] == "FST-030"
    assert bearing(seated_screw("al5052", washer=True))[1] == {}
    m, f = bearing(seated_screw("al_mic6", washer=True))
    assert f == {} and m["worst"][0]["bearing_pressure_mpa"] == pytest.approx(7000 / (math.pi * (5 ** 2 - 2.76 ** 2)), rel=0.03)
    m, f = bearing(seated_screw("al_mic6", washer="large"))
    assert f == {} and m["worst"][0]["bearing_pressure_mpa"] == pytest.approx(7000 / (math.pi * (7.5 ** 2 - 2.76 ** 2)), rel=0.03)


def test_washer_dimensions_are_the_tabulated_iso_7089_and_7093_sizes_m2_5_to_m8():
    """From the distributor's reproduction of the standards (practice_refs/06_RC_ISO_washers.pdf): ISO 7089 M8 is
    8.4 x 16 x 1.6 (thickness 1.4-1.8), ISO 7093 M8 8.4 x 24 x 2.0 (1.8-2.2); there is no ISO 7093 M2.5."""
    from mechloop.parts.hardware import WASHER, washer_flat

    assert WASHER["normal"]["M8"] == (8.4, 16.0, 1.6) and WASHER["large"]["M8"] == (8.4, 24.0, 2.0)
    # M2 added 2026-11-19 (printer_v11's blower screws)
    assert set(WASHER["normal"]) == {"M2", "M2.5", "M3", "M4", "M5", "M6", "M8"} and "M2.5" not in WASHER["large"]
    st = washer_flat("M8", "large")
    assert st.sku == "WASHER-M8-LARGE" and "06_RC_ISO_washers" in st.source.get("note", "")


def test_a_washer_is_one_more_part_to_put_on_in_the_assembly_estimate():
    from mechloop.assembly.simulate import analyse

    bare, with_w = analyse(seated_screw("petg", size="M3")), analyse(seated_screw("petg", size="M3", washer=True))
    assert [r_["unit"] for r_ in with_w["rows"]] == ["block", "plate", "s_washer", "s"]                 # the washer goes on before its screw
    assert with_w["metrics"]["estimated_time_min"] > bare["metrics"]["estimated_time_min"]


# ===================================================================== 12. sharp edges, corners and lead-ins
def edge_findings(shape, process, material="al6061", meta=None, man=None):
    from mechloop.verifiers.manufacture import verify_manufacture

    d = Design("e")
    if man:
        d.manufacturing = man
    d.add("p", shape, material=material, process=process, meta=meta or {})
    r = verify_manufacture(d)
    return {f.code: f for f in r.findings}, r.metrics["parts"]["p"]["edges"]


def test_edge_classification_of_a_box_a_filleted_box_and_a_chamfered_box():
    """A box has 12 edges, all convex, all between faces at 90 degrees: 12 sharp. With every edge filleted the edges
    that remain are tangent: none sharp. With every edge chamfered the faces meet at 45 degrees: none sharp. A hole
    through a box adds two sharp mouths; chamfering them removes both."""
    from build123d import chamfer, fillet

    from mechloop.verifiers.dfm_edges import _dedupe, classify

    box = Box(40, 30, 10)
    assert len(classify(box)["sharp_convex"]) == 12 and classify(box)["sharp_concave"] == 0
    assert classify(fillet(box.edges(), 1.0))["sharp_convex"] == []
    assert classify(chamfer(box.edges(), 1.0))["sharp_convex"] == []
    holed = box - Cylinder(3, 10)
    cl = classify(holed)
    assert len(_dedupe(cl["hole_mouths"])) == 2 and cl["shaft_ends"] == [] and {m_["dia"] for m_ in cl["hole_mouths"]} == {6.0}
    mouths = [e for e in holed.edges() if e.geom_type.name == "CIRCLE"]
    assert classify(chamfer(mouths, 0.5))["hole_mouths"] == []
    pin = Cylinder(3, 20)
    assert len(_dedupe(classify(pin)["shaft_ends"])) == 2 and classify(pin)["hole_mouths"] == []


def test_sheet_corners_machined_edges_and_printed_edges_are_reported_by_process():
    """The same 60 x 40 plate. As 3 mm SHEET: its four profile corners are dead sharp: warning with the count; with the
    corners rounded 2 mm: nothing. As a 10 mm MACHINED plate: 12 unbroken outside edges: warning; with the drawing
    note declared on the part, or for the whole design, or with every edge chamfered: nothing. PRINTED: information
    only (four sharp edges on the bed face)."""
    from build123d import Axis, chamfer, fillet

    sheet = Box(60, 40, 3)
    f, e = edge_findings(sheet, "sheet")
    assert f["sharp_profile_corners"].severity == "warning" and f["sharp_profile_corners"].data["count"] == 4 and e["sharp_profile_corners"] == 4
    assert len(f["sharp_profile_corners"].data["at"]) == 4
    f, e = edge_findings(fillet(sheet.edges().filter_by(Axis.Z), 2.0), "sheet")
    assert "sharp_profile_corners" not in f and e["sharp_profile_corners"] == 0
    plate = Box(60, 40, 10)
    f, e = edge_findings(plate, "machined")
    assert f["edges_not_broken"].severity == "warning" and f["edges_not_broken"].data["count"] == 12
    assert "edges_not_broken" not in edge_findings(plate, "machined", meta={"edge_break_mm": 0.3})[0]
    f, e = edge_findings(plate, "machined", man={"edge_break_mm": 0.3})
    assert "edges_not_broken" not in f and e["edge_break_declared_mm"] == 0.3 and e["sharp_outside_edges"] == 12
    assert "edges_not_broken" not in edge_findings(chamfer(plate.edges(), 0.5), "machined")[0]
    f, e = edge_findings(plate, "printed", material="petg", meta={"print_up": "+Z"})
    assert "edges_not_broken" not in f and "sharp_profile_corners" not in f
    assert f["printed_edges"].severity == "info" and f["printed_edges"].data["parts"]["p"]["sharp_edges_on_bed_face"] == 4


def pin_in_block(chamfer_bore=False, chamfer_pin=False):
    from build123d import chamfer

    d = Design("pin", base="block")
    block = Pos(0, 0, 10) * Box(40, 40, 20) - Pos(0, 0, 10) * Cylinder(4.05, 20)
    if chamfer_bore:
        block = chamfer([e for e in block.edges() if e.geom_type.name == "CIRCLE"], 0.5)
    pin = Pos(0, 0, 20) * Cylinder(4.0, 60)
    if chamfer_pin:
        pin = chamfer(pin.edges(), 0.5)
    d.add("block", block, material="al6061", meta={"edge_break_mm": 0.3})
    d.add("pin", pin, material="steel", meta={"edge_break_mm": 0.3})
    d.join("pin", "block", "sliding")
    return d


def test_a_shaft_meeting_its_bore_edge_to_edge_has_no_lead_in_and_a_chamfer_on_either_gives_one():
    from mechloop.verifiers.manufacture import verify_manufacture

    r = verify_manufacture(pin_in_block())
    f = [x for x in r.findings if x.code == "no_lead_in"]
    assert len(f) == 1 and f[0].severity == "warning" and f[0].data["parts"] == ["pin", "block"]
    for kw in (dict(chamfer_bore=True), dict(chamfer_pin=True)):
        r = verify_manufacture(pin_in_block(**kw))
        assert [x for x in r.findings if x.code == "no_lead_in"] == []
        row = r.metrics["edges"]["shaft_bore_lead_ins"][0]
        assert row["bore_mouth_chamfered"] == bool(kw.get("chamfer_bore")) and row["shaft_end_chamfered"] == bool(kw.get("chamfer_pin"))


# ===================================================================== bed-support FEA: every declared support must hold
OUTSIDE = ((-115.0, -60.0), (115.0, -60.0), (0.0, 120.0))        # three screws just outside the plate's outline


def seated_bed(screws=OUTSIDE, lift=None):
    """bed_machine with what each nut sits in drawn: an aluminium bracket bonded under the plate's edge with a shelf
    that lies against the nut's lower face (the plate hangs on the three nuts by its brackets). lift: the name of one
    nut whose shelf is drawn 0.5 mm clear of it."""
    d = floating(bed_machine(screws=screws, blocks_per_rail=1, sync="belt" if len(screws) > 1 else None))
    parts = ["bed"] + [c.name for c in d.components if c.name.startswith("blk")]
    for i, (x, y) in enumerate(screws):
        low = d.get(f"nut{i}").shape.bounding_box().min.Z
        top = low - (0.5 if lift == f"nut{i}" else 0.0)
        shelf = Pos(x, y, (86.0 + top) / 2) * (Box(30, 30, top - 86.0) - Cylinder(5.0, top - 86.0))
        if abs(x) > 1:           # a side screw: the riser stands under the plate's side edge
            riser = Pos(x - math.copysign(23.0, x), y, 93.0) * Box(16, 30, 14)
        else:                    # the rear screw: under the rear edge
            riser = Pos(x, y - 27.0, 93.0) * Box(30, 24, 14)
        d.add(f"pad{i}", shelf + riser, material="al6061", body="zb")
        d.join(f"pad{i}", "bed", "bond")
        parts.append(f"pad{i}")
    d.printer["bed_support"] = {"parts": parts}
    return d


def test_every_declared_support_holds_nodes_and_a_support_that_holds_none_is_an_error_not_a_figure():
    """A plate on three screws (a bracket under the plate's edge on each nut) and one guide block per rail. All three seats hold
    nodes: evaluated, with the node count per support, the five print points each loaded in turn, and the worst taken
    from those. With one bracket's shelf drawn 0.5 mm clear of its nut that seat holds nothing: before, the FEA ran on the two that
    were found and reported the lot as held; now it is `bed_support_not_held_in_fea` (error) and no figure. And
    un-holding a support does change the answer: the same plate on TWO screws (the rear one removed from the drive)
    sinks several times further at the rear corners than on three."""
    if not __import__("shutil").which("ccx"):
        pytest.skip("CalculiX is not installed")
    r = VerifierResult("fea")
    m = BS.bed_support(seated_bed(), r)
    fx = m["flexure"]
    assert fx["evaluated"] and not fx["idealised"] and "bed_support_not_held_in_fea" not in codes(r)
    assert set(fx["constrained_nodes"]) == {"blk00", "blk10", "nut0", "nut1", "nut2"} and min(fx["constrained_nodes"].values()) >= 3
    assert set(fx["by_point"]) == {"corner -x -y", "corner -x +y", "corner +x -y", "corner +x +y", "centre"}
    pw = m["print_weight"]
    assert pw["worst_point"] == max(pw["by_point_mm"], key=lambda k: pw["by_point_mm"][k]["judged_mm"])
    assert pw["judged_mm"] == max(v["judged_mm"] for v in pw["by_point_mm"].values())
    assert fx["bonded_mm_per_n"] == fx["by_point"][fx["worst_point"]]["bonded_mm_per_n"]
    # a load at one corner moves that corner most: the field under it is read at the other points too
    row = fx["by_point"]["corner +x +y"]
    assert row["bonded_elsewhere_mm_per_n"]["corner +x +y"] == pytest.approx(row["bonded_mm_per_n"], abs=1e-6)
    assert row["bonded_mm_per_n"] > row["bonded_elsewhere_mm_per_n"]["corner -x -y"]

    r2 = VerifierResult("fea")
    m2 = BS.bed_support(seated_bed(lift="nut2"), r2)
    f2 = find(r2, "bed_support_not_held_in_fea")
    assert len(f2) == 1 and f2[0].severity == "error" and f2[0].data["unheld"] == ["nut2"]
    assert not m2["flexure"]["evaluated"] and m2["flexure"]["constrained_nodes"]["nut2"] == 0 and m2["flexure"]["constrained_nodes"]["nut0"] >= 3
    assert "total_bonded_mm" not in m2["print_weight"]                    # no flexure figure is reported for a model that is not held

    r3 = VerifierResult("fea")
    m3 = BS.bed_support(seated_bed(screws=OUTSIDE[:2]), r3)                # the rear screw taken away: the rear edge hangs
    rear3 = max(m["print_weight"]["by_point_mm"][k]["total_bonded_mm"] for k in ("corner -x +y", "corner +x +y"))
    rear2 = max(m3["print_weight"]["by_point_mm"][k]["total_bonded_mm"] for k in ("corner -x +y", "corner +x +y"))
    assert m3["flexure"]["evaluated"] and rear2 > 3.0 * rear3


def test_the_displacement_field_of_the_bed_support_case_is_saved_for_rendering(tmp_path, monkeypatch):
    if not __import__("shutil").which("ccx"):
        pytest.skip("CalculiX is not installed")
    monkeypatch.setattr(BS, "FIELD_DIR", tmp_path / "fea")
    m = BS.bed_support(seated_bed(), VerifierResult("fea"))
    z = np.load(m["flexure"]["displacement_fields"])
    assert z["xyz"].shape[1] == 3 and len(z["print_point_labels"]) == 5 and len(z["part"]) == len(z["xyz"])
    u = z["U_corner_px_py__bonded"]
    assert u.shape == z["xyz"].shape and float(np.abs(u).max()) > 0


# ===================================================================== review anomalies
def test_an_adjustment_used_beyond_nine_tenths_of_its_range_is_flagged_and_one_with_room_is_not():
    """Needed 1.453 of 1.5 mm (97 %): `adjustment_margin_thin`, with the share. 1.2 of 1.5 (80 %): nothing. 1.6 of
    1.5: not this warning (the error `adjustment_too_small` is the caller's)."""
    from mechloop.tolerance import ADJUSTMENT_MARGIN_THIN, thin_adjustment

    adj = Adjustment("y rail set to the plate", "rail_align", range_mm=1.5, joint="y")
    r = VerifierResult("tolerance")
    out = thin_adjustment(r, adj, 1.453, "Axis y: aligning its two rails")
    assert out == {"share_of_range_used_99": 0.969, "margin_thin": True} and ADJUSTMENT_MARGIN_THIN == 0.9
    f = find(r, "adjustment_margin_thin")
    assert len(f) == 1 and f[0].severity == "warning" and f[0].data["share_used"] == 0.969 and "97%" in f[0].message
    r = VerifierResult("tolerance")
    assert not thin_adjustment(r, adj, 1.2, "x")["margin_thin"] and not thin_adjustment(r, adj, 1.6, "x")["margin_thin"] and r.findings == []


def test_reports_carry_the_hash_of_the_checker_and_of_the_design_file(tmp_path):
    from mechloop.report import provenance_of, source_hash
    from mechloop.runner import run

    f = tmp_path / "tiny.py"
    f.write_text("from build123d import Box\nfrom mechloop import Design\n\n\ndef build():\n    d = Design('tiny')\n    d.add('a', Box(10, 10, 10))\n    return d\n")
    rep = run(f, tmp_path / "out", only=["geometry"], render=False).to_dict()
    h = rep["provenance"]
    assert h["mechloop_source_sha256"] == source_hash()["mechloop_source_sha256"] and len(h["mechloop_source_sha256"]) == 16
    assert h["design_file"] == "tiny.py" and h["design_file_sha256"] == provenance_of(f)["design_file_sha256"]
    f.write_text(f.read_text() + "# changed\n")
    assert provenance_of(f)["design_file_sha256"] != h["design_file_sha256"]
    assert json.loads((tmp_path / "out" / "tiny" / "report_partial.json").read_text())["provenance"] == h


def test_a_nozzle_nine_millimetres_off_its_path_is_never_a_clean_print():
    """Review anomaly (a): shaper-on sweep rows at 10,000 and 16,000 mm/s^2 were `ok` with the nozzle 9.34 / 8.55 mm
    sideways from its path. Any cross-track error over 1 mm is `nozzle_off_path` (error), so the print report's ok is
    False and the sweep row with it; 0.4 mm is not flagged."""
    from mechloop.twin import PATH_ERROR_LIMIT_MM, judge_path_error
    from mechloop.twin.evals import summarise

    r = VerifierResult("print")
    assert not judge_path_error(r, np.array([0.01, 0.4, 0.2])) and r.ok
    assert judge_path_error(r, np.array([0.02, 9.34, 0.3])) and not r.ok and PATH_ERROR_LIMIT_MM == 1.0
    f = find(r, "nozzle_off_path")[0]
    assert f.severity == "error" and f.data["worst_mm"] == 9.34
    row = summarise({"ok": r.ok, "findings": [x.to_dict() if hasattr(x, "to_dict") else {"code": x.code, "severity": x.severity, "data": x.data} for x in r.findings]})
    assert row["ok"] is False and row["errors"] == ["nozzle_off_path"]


def test_thread_engagement_in_aluminium_follows_the_alloy():
    """FST-010 (Bossard's engagement table): M5 into a block of 6061 by 6 mm (1.2 d): error; by 8.5 mm (1.7 d): passes
    the 1.5 d floor but is under 2 d: one grouped warning; by 11 mm (2.2 d): nothing. In cast MIC-6 (soft aluminium)
    8.5 mm is an error (2 d)."""
    from mechloop.verifiers.interference import _threads

    def run(mat, depth):
        d = Design("eng", base="block")
        d.add("block", Pos(0, 0, -15) * Box(30, 30, 30), material=mat)
        d.add("plate", Pos(0, 0, 2.5) * Box(30, 30, 5) - Pos(0, 0, 2.5) * Cylinder(2.75, 5), material="steel")
        add_screw(d, "s", "M5", 5 + depth, at=(0, 0, 5), threads_into="block", clamps=("plate",))
        r = VerifierResult("interference")
        _threads(d, r)
        return {f.code: f for f in r.findings}

    f = run("al6061", 6)
    assert f["thread_engagement"].severity == "error" and f["thread_engagement"].data["rule"] == "FST-010"
    f = run("al6061", 8.5)
    assert set(f) == {"thread_engagement_marginal"} and f["thread_engagement_marginal"].severity == "warning"
    assert f["thread_engagement_marginal"].data["least"]["ratio"] == pytest.approx(1.7, abs=0.05)
    assert run("al6061", 11) == {}
    assert run("al_mic6", 8.5)["thread_engagement"].severity == "error"


def test_what_bears_on_a_608_must_stay_on_the_ring_it_abuts():
    """BRG-024 (SKF 608: inner ring shoulder d1 12.15, outer ring D2 19.2 mm). A pulley hub 15.5 mm across on the inner
    ring reaches past d1: it rubs the shield (warning). A 12 mm shim between: inside d1, nothing. A flat plate against the
    whole face touches both rings (warning: the turning ring drags)."""
    from mechloop.parts import bearing as brg, place
    from mechloop.verifiers.bearing import ring_abutment

    def run(other):
        d = Design("brg")
        place(d, "b", brg("608"))
        if other is not None:
            d.add("x", other, material="al6061")
        r = VerifierResult("ratings")
        m = ring_abutment(d, r)
        return m, {f.code: f for f in r.findings}

    m, f = run(Pos(0, 0, 3.5 + 2) * (Cylinder(7.75, 4) - Cylinder(4, 4)))
    assert f["bearing_abutment"].data["rule"] == "BRG-024" and "shield" in f["bearing_abutment"].data["contacts"][0]["problem"]
    assert f["bearing_abutment"].data["contacts"][0]["contact_to_mm"] == pytest.approx(15.5, abs=1.2)
    m, f = run(Pos(0, 0, 3.5 + 0.5) * (Cylinder(6.0, 1) - Cylinder(4, 1)))
    assert f == {} and m["contacts"][0]["contact_to_mm"] < 12.15
    m, f = run(Pos(0, 0, 3.5 + 2) * (Box(40, 40, 4) - Cylinder(4.5, 4)))
    assert "both rings" in f["bearing_abutment"].data["contacts"][0]["problem"]
    assert brg("608").interfaces["axial_limit_n"] == pytest.approx(342.5)


def test_nut_findings_are_judged_at_two_screws_at_opposite_lead_limits():
    """LSC-015: two screws tied by a belt can differ by up to 2 x 0.1 mm / 300 mm x travel. The nut finding is judged at
    that level (levels[2]): whenever a nut unseats there, `z_nut_unseats` or `z_tilt_over_constrained` is raised; and
    the level's height error is the synchronisation error plus twice the per-screw lead error."""
    m, r = support(floating(bed_machine(screws=THREE, blocks_per_rail=1, sync="belt")))
    st = m["nut_seating_and_lead_error"]
    lv = st["levels"][2]
    assert lv["height_error_mm"] == pytest.approx(m["screw_synchronisation"]["height_error_mm"] + 2 * st["lead_error_over_travel_mm"], abs=1e-4)
    raised = find(r, "z_nut_unseats") + find(r, "z_tilt_over_constrained")
    assert bool(raised) == lv["a_nut_unseats"]
    if raised:
        assert raised[0].data["rule"] == "LSC-015" and raised[0].data["height_error_mm"] == lv["height_error_mm"]


def test_a_sweep_row_says_when_the_test_part_never_reached_its_acceleration_limit():
    """Klipper shaper-on sweep for printer_v8: the row labelled 48,000 mm/s^2 was clean, but on the 20 mm test cube the
    firmware's own 99.9th-percentile acceleration was 15,568 / 13,337 mm/s^2. The summary keeps the label and says what
    was reached; when the label is within reach (16,000 against 13,481) nothing is added."""
    from mechloop.twin.score import sweep_summary

    ok = lambda pk: {"ok": True, "errors": [], "not_run": None, "peak_accel_mm_s2": pk}
    s = sweep_summary({4: ok([12689, 11575, 203]), 12: ok([15568, 13337, 202])}, 4000.0)
    assert s["highest_clean_accel_mm_s2"] == 48000.0 and s["highest_clean_peak_reached_mm_s2"] == 15568
    assert "never reached" in s["highest_clean_note"] and s["table"][1]["peak_accel_reached_mm_s2"][0] == 15568
    s = sweep_summary({4: ok([13481, 12733, 203])}, 4000.0)
    assert "highest_clean_note" not in s and s["highest_clean_peak_reached_mm_s2"] == 13481
