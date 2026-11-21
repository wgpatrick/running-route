"""Frozen predictions (mechloop.inspect.predictions) and record.compare's refusal to score post-hoc predictions."""
import json
import warnings
from pathlib import Path

import pytest

from mechloop.inspect import predictions as P
from mechloop.inspect import record as R

ROOT = Path(__file__).resolve().parents[1]
RP04_SHA256 = "320a55fd679612505ef7b79b26c30b4ed5736f899aa91de0ab2bc83145bf70bd"


def test_rp04_frozen_file_is_pinned_and_complete():
    rec = P.load("RP04", "S7855707")
    assert rec is not None and P.verify(rec)
    assert rec["sha256"] == RP04_SHA256                       # a frozen file never changes (as calibration_machines.json)
    plan = json.loads((ROOT / "inspect_form" / "plans" / "RP04.json").read_text())
    keys = {p["key"] for p in rec["predictions"]}
    assert {d["key"] for d in plan["dimensions"]} <= keys     # every plan dimension is frozen
    assert all(p.get("tests") for p in rec["predictions"])
    assert rec["unfold"]["by"] == "us"


@pytest.fixture()
def frozen(tmp_path):
    rec = {"part": "RPX", "order": "O1", "predictions": [{"key": "H1.dia", "nominal": 5.5, "predicted": 5.45, "sigma": 0.05}]}
    out = P.freeze(rec, pred_dir=tmp_path, frozen_at="2026-11-21T00:00:00Z")
    with pytest.raises(FileExistsError):
        P.freeze(rec, pred_dir=tmp_path)
    return tmp_path, out


def _row(when, measured=5.40, predicted=5.5, order="O1"):
    return {"part": "RPX", "order": order, "dimension_key": "H1.dia", "kind": "hole_diameter", "measured": measured,
            "nominal": 5.5, "predicted": predicted, "tol_pm": 0.127, "when": when}


def test_scored_against_frozen_value_when_frozen_before(frozen):
    d, _ = frozen
    c = R.compare([_row("2026-12-01T10:00:00")], pred_dir=d)[0]
    assert c["prediction_status"] == "frozen" and c["predicted"] == 5.45      # the frozen value, not the row's copy
    assert c["dev_predicted"] == pytest.approx(-0.05) and c["z"] == pytest.approx(-1.0)


def test_refused_when_frozen_after_measurement(frozen):
    d, _ = frozen
    with pytest.warns(R.PredictionWarning, match="frozen after"):
        c = R.compare([_row("2026-11-20T23:00:00")], pred_dir=d)[0]
    assert c["prediction_status"] == "frozen_after_measurement" and c["dev_predicted"] is None
    assert c["dev_nominal"] == pytest.approx(-0.10)                           # nominal comparison still made


def test_refused_when_tampered(frozen):
    d, out = frozen
    p = P.path_for("RPX", "O1", d)
    bad = dict(out, predictions=[dict(out["predictions"][0], predicted=5.40)])
    p.write_text(json.dumps(bad))
    with pytest.warns(R.PredictionWarning, match="sha256"):
        c = R.compare([_row("2026-12-01T10:00:00")], pred_dir=d)[0]
    assert c["prediction_status"] == "hash_mismatch" and c["dev_predicted"] is None


def test_unfrozen_warns_but_scores(tmp_path):
    with pytest.warns(R.PredictionWarning, match="never frozen"):
        c = R.compare([_row("2026-12-01T10:00:00", order="O2")], pred_dir=tmp_path)[0]
    assert c["prediction_status"] == "unfrozen" and c["dev_predicted"] == pytest.approx(-0.10)
