"""Scanner measurement (mechloop.inspect.scan) against synthetic scans rendered from the DXF with known errors."""
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("cv2")
from mechloop.inspect import scan as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DXF = ROOT / "reference_parts" / "batch01" / "RP04_laser_plate.dxf"
TARGET = {"cols": 3, "rows": 9, "pitch": 10.0, "dot": 2.0, "at": (160.0, 12.0)}


@pytest.fixture(scope="module")
def prof():
    return S.load_dxf(DXF)


@pytest.fixture(scope="module")
def scanned(prof):
    """RP04 with hole 0 moved (+0.30, -0.10) mm and hole 1 grown by 0.20 mm, scanned at 600 dpi, rotated 7 degrees, with a
    scanner scale error of +0.4 % / -0.3 % and the calibration target beside the part."""
    pp = S.perturb(prof, move_hole={"index": 0, "dx": 0.30, "dy": -0.10}, grow_hole={"index": 1, "dd": 0.20})
    img = S.render_scan(pp, 600, rotation_deg=7.0, offset_mm=(18, 18), scale=(1.004, 0.997), blur_px=1.2, noise=4.0,
                        target=TARGET, supersample=2, seed=3)
    return img


def test_dxf_profile(prof):
    assert len(prof.circles) == 6 and len(prof.cutouts) == 2
    lo, hi = prof.bounds()
    assert np.allclose(hi - lo, [120.0, 80.0], atol=1e-6)
    assert sorted(round(c["d"], 3) for c in prof.circles) == [1.2, 4.0, 5.5, 5.5, 5.5, 5.5]


def test_recovers_scale_and_known_offsets(prof, scanned, tmp_path):
    r = S.measure(scanned, prof, 600, calibration="auto", out_dir=tmp_path, name="rp04")
    cal = r.calibration
    assert cal["n_dots"] == 27
    assert abs(cal["scale_x"] - 1.004) < 3e-4 and abs(cal["scale_y"] - 0.997) < 3e-4
    assert r.fit["holes_matched"] == 6 and not r.transform["mirrored"]
    assert abs(abs(r.transform["rotation_deg"]) - 7.0) < 0.05
    h = {x["dxf_index"]: x for x in r.holes}
    assert abs(h[0]["dx"] - 0.30) < 0.03 and abs(h[0]["dy"] + 0.10) < 0.03          # the moved hole
    assert abs(h[1]["d_error"] - 0.20) < 0.03                                        # the grown hole
    for j in (2, 3, 4, 5):                                                            # the untouched ones
        assert h[j]["position_error"] < 0.03 and abs(h[j]["d_error"]) < 0.03
    assert max(abs(e) for e in r.overall["error"]) < 0.05
    assert all(abs(e["offset_mean"]) < 0.04 for e in r.edges)
    assert (tmp_path / "rp04.scan.json").exists() and (tmp_path / "rp04.deviation.png").exists()
    json.loads((tmp_path / "rp04.scan.json").read_text())


def test_without_target_the_scale_error_shows(prof, scanned):
    r = S.measure(scanned, prof, 600, calibration=None)
    assert abs(r.overall["error"][0]) > 0.3          # 0.4 % of 120 mm, uncorrected


def test_mirrored_scan_and_kerf(prof):
    pp = S.perturb(prof, kerf_mm=0.05)               # every edge 0.05 mm into the material
    img = S.render_scan(pp, 600, rotation_deg=-3.0, mirror=True, blur_px=1.0, noise=3.0, supersample=2, seed=5)
    r = S.measure(img, prof, 600, calibration=None)
    assert r.transform["mirrored"] and r.fit["holes_matched"] == 6
    assert all(abs(x["d_error"] - 0.10) < 0.03 for x in r.holes if "d_error" in x)
    assert all(abs(e["offset_mean"] + 0.05) < 0.03 for e in r.edges)
    assert all(abs(e + 0.10) < 0.05 for e in r.overall["error"])


def test_target_files_and_separate_calibration_scan(tmp_path):
    t = S.make_target(tmp_path)
    assert Path(t["svg"]).exists() and Path(t["pdf"]).exists() and t["pitch_mm"] == 10.0
    # a scan of a patch of the target alone, at 1200 dpi with a scale error, calibrates the scanner
    blank = S.Profile(outline=np.array([[0, 0], [1, 0], [1, 1], [0, 1.0]]) * 0.01)
    img = S.render_scan(blank, 1200, offset_mm=(2, 2), scale=(0.998, 1.002), blur_px=1.5, noise=3.0, supersample=1,
                        target={"cols": 5, "rows": 5, "pitch": 10.0, "dot": 2.0, "at": (8.0, 8.0)}, margin_mm=6.0)
    cal = S.calibrate(img, 1200)
    assert cal is not None and cal.n_dots >= 24
    assert abs(cal.scale_x - 0.998) < 3e-4 and abs(cal.scale_y - 1.002) < 3e-4 and cal.residual_rms_mm < 0.01


def test_plan_frame_and_rows_from_scan(prof, scanned):
    from mechloop.inspect import record as REC

    plan = json.loads((ROOT / "inspect_form" / "plans" / "RP04.json").read_text())
    pf = S.plan_frame(plan, prof)
    assert len(pf["ids"]) == 6
    r = S.measure(scanned, prof, 600, calibration="auto", plan=plan)
    rows = REC.rows_from_scan(r.to_json(), plan, order="TEST")
    by = {m.dimension_key: m for m in rows}
    moved = pf["ids"][0]
    grown = pf["ids"][1]
    assert abs(by[f"{grown}.dia"].measured - (by[f"{grown}.dia"].nominal + 0.2)) < 0.03
    assert abs(by["overall.X"].measured - 120.0) < 0.05
    # the moved hole's plan-frame position differs from nominal by the move (0.316 mm in total)
    dx = by[f"{moved}.x"].measured - by[f"{moved}.x"].nominal
    dy = by[f"{moved}.y"].measured - by[f"{moved}.y"].nominal
    assert abs(np.hypot(dx, dy) - np.hypot(0.30, 0.10)) < 0.04
    assert all(m.instrument == "scanner" and m.source == "scan" for m in rows)
