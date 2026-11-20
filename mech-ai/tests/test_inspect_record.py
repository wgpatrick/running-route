"""Measurement record, proposed learnings and loop metrics (mechloop.inspect.record), and the form importer."""
import json
from pathlib import Path

import pytest

from mechloop.inspect import import_form as IF
from mechloop.inspect import record as R

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def paths(tmp_path):
    return {"record": tmp_path / "m.jsonl", "ledger": tmp_path / "ledger.jsonl", "orders": tmp_path / "orders.jsonl"}


@pytest.fixture(scope="module")
def rp03():
    return json.loads((ROOT / "inspect_form" / "plans" / "RP03.json").read_text())


def _rp03_rows(plan, order, when, radii, angles, flange6):
    out = []
    for i, (r, a, f) in enumerate(zip(radii, angles, flange6)):
        meta = dict(order=order, sample=i + 1, who="AB", when=when, instrument=None)
        out.append(R.from_plan(plan, "B1.radius", r, **meta))
        out.append(R.from_plan(plan, "B1.angle", a, **meta))
        out.append(R.from_plan(plan, "B2.F2", f, **meta))
    return out


def test_record_add_dedupes_and_compares(paths, rp03):
    rows = _rp03_rows(rp03, "SCS-1", "2026-12-01T10:00:00", [0.84, 0.85, 0.83], [90.5, 90.7, 90.6], [5.70, 5.66, 5.69])
    assert R.add(rows, paths["record"]) == 9
    assert R.add(rows, paths["record"]) == 0
    got = R.load(paths["record"])
    c = {x["id"]: x for x in R.compare(got)}
    rad = next(x for x in c.values() if x["dimension_key"] == "B1.radius")
    assert rad["nominal"] == pytest.approx(2.286) and rad["predicted"] == pytest.approx(0.813)
    assert rad["in_tolerance"] is False and rad["prediction_better"] is True
    s = {x["kind"]: x for x in R.summarize(got)}
    assert s["bend_radius"]["n"] == 3 and s["bend_radius"]["mean_abs_err_predicted"] < s["bend_radius"]["mean_abs_err_nominal"]


def test_learnings_are_proposed_with_evidence_and_not_applied(paths, rp03):
    rows = _rp03_rows(rp03, "SCS-1", "2026-12-01T10:00:00", [0.84, 0.85, 0.83], [90.5, 90.7, 90.6], [5.70, 5.66, 5.69])
    R.add(rows, paths["record"])
    before = (ROOT / "mechloop" / "data" / "supplier_rules" / "sendcutsend.json").read_text()
    new = R.update_ledger(path=paths["ledger"], record_path=paths["record"])
    kinds = {L["kind"]: L for L in new}
    rad = kinds["supplier_bend_radius"]
    assert rad["title"] == "SendCutSend al5052 .090 in (2.286 mm) inside bend radius measured 0.84 mm vs rule 0.813 mm (n=3)"
    assert rad["target"]["rule_id"] == "sendcutsend.bend.radius.al5052.2.286mm" and rad["target"]["proposed"] == pytest.approx(0.84)
    assert rad["error_after"]["mean_abs_mm"] < rad["error_before"]["mean_abs_mm"]
    assert rad["status"] == "proposed" and len(rad["evidence"]["measurement_ids"]) == 3
    assert "bend_angle_bias" in kinds and kinds["bend_angle_bias"]["target"]["file"] == "mechloop/tolerance/bends.py"
    assert (ROOT / "mechloop" / "data" / "supplier_rules" / "sendcutsend.json").read_text() == before      # nothing edited
    assert R.update_ledger(path=paths["ledger"], record_path=paths["record"]) == []                        # same evidence: no repeat
    R.set_status(rad["id"], "accepted", by="owner", note="checked with a radius gauge", path=paths["ledger"])
    assert R.ledger(paths["ledger"])[rad["id"]]["status"] == "accepted"
    with pytest.raises(ValueError):
        R.set_status(rad["id"], "maybe", by="x", path=paths["ledger"])


def test_no_learning_from_too_few_or_noise(rp03):
    rows = [R.Measurement(**{k: v for k, v in vars(m).items()}) for m in
            _rp03_rows(rp03, "O", "2026-12-01", [0.81, 0.82], [90.0, 90.1], [5.68, 5.69])]
    assert R.propose_learnings([vars(r) for r in rows]) == []


def test_loop_metrics(paths, rp03):
    R.add(_rp03_rows(rp03, "SCS-1", "2026-12-08T10:00:00", [0.84, 0.85, 0.83], [90.5, 90.7, 90.6], [5.70, 5.66, 5.69]), paths["record"])
    R.add_order("SCS-1", "sendcutsend", ["RP03"], placed="2026-12-01", received="2026-12-06", design_changed="2026-11-28", path=paths["orders"])
    m = R.loop_metrics(record_path=paths["record"], orders_path=paths["orders"])
    lt = m["loop_time"][0]
    assert lt["order_to_received_days"] == pytest.approx(5.0, abs=0.05) and lt["order_to_measured_days"] == pytest.approx(7.42, abs=0.05)
    assert lt["design_change_to_measured_days"] == pytest.approx(10.42, abs=0.05)
    fid = {f["kind"]: f for f in m["fidelity"]}
    assert fid["bend_radius"]["mean_abs_err_predicted"] == pytest.approx(0.027, abs=0.002)
    assert m["autonomy"][0]["manual_steps"] == 3 and m["totals"]["manual_steps_per_part"] == 3


def test_form_import_roundtrip(paths, rp03):
    sub = {"schema": "mechloop.form_submission/1", "submission_id": "S-1", "part": "RP03", "revision": "batch01", "supplier": "sendcutsend",
           "order": "SCS-9", "sample": 2, "who_id": "u_abc", "measured_by": "AB", "when": "2026-12-02T09:00:00", "notes": "burr on H1",
           "photo": None, "material": "al5052", "thickness_mm": 2.286,
           "readings": [{"dimension_id": 4, "dimension_key": "B1.angle", "kind": "bend_angle", "nominal": 90.0, "tol_pm": 1.0, "predicted": 90.0,
                         "measured": 90.8, "unit": "deg", "instrument": "square_feeler", "method": "square"},
                        {"dimension_id": 6, "dimension_key": "B1.radius", "kind": "bend_radius", "nominal": 2.286, "tol_pm": 0.15,
                         "predicted": 0.813, "measured": 0.86, "unit": "mm", "instrument": "radius_gauge", "method": "gauge"}]}
    export = {"docs": [{"id": "S-1", "data": sub}]}
    f = paths["record"].parent / "rows.json"
    f.write_text(json.dumps(export))
    out = IF.import_rows(f, paths["record"])
    assert out == {"readings": 2, "added": 2, "submissions": 1}
    assert IF.import_rows(sub, paths["record"])["added"] == 0
    rows = R.load(paths["record"])
    assert {r["dimension_key"] for r in rows} == {"B1.angle", "B1.radius"}
    assert all(r["source"] == "form" and r["order"] == "SCS-9" and r["sample"] == 2 and r["who"] == "AB" for r in rows)


def test_form_entry_is_small(rp03):
    svg = (ROOT / "inspect_form" / "plans" / "RP03.svg").read_text()
    e = IF.form_entry(rp03, svg)
    assert len(e["dimensions"]) == len(rp03["dimensions"]) and e["dimensions"][0]["how"]
