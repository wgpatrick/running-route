"""Frozen predictions: what we said a part would measure, written down and hashed BEFORE the part is measured.

Same discipline as `twin/calibration.py` (inputs frozen, hash pinned by a test, post-hoc work kept apart), applied to
inspection (docs/INSPECTION_STRATEGY.md section 5; docs/inspection_research/03_strategy_and_feedback.md 4.3, gap G1).

One file per part and order: mechloop/data/measurements/predictions/<part>_<order>.json, with

- `predictions`: one entry per predicted quantity (plan dimension key, nominal, predicted value, sigma (1 standard
  uncertainty of the prediction), tolerance, basis/findings, and `tests`: the model parameter or shop rule it tests);
- `frozen_at`: UTC time of the freeze (ISO 8601, "Z");
- `sha256`: SHA-256 of the canonical JSON of everything else in the file (sorted keys, no whitespace, UTF-8).

`freeze()` refuses to overwrite an existing file: a frozen prediction is never edited. A re-prediction after a rule
change goes in a new file with a `posthoc` flag and is never used to claim fidelity. `record.compare` scores a
measurement against a frozen prediction only if the file verifies and was frozen no later than the measurement.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRED_DIR = ROOT / "mechloop" / "data" / "measurements" / "predictions"
SCHEMA = "mechloop.frozen_predictions/1"


def canonical(rec: dict) -> bytes:
    """The bytes the hash covers: the record without its `sha256` field, as sorted, compact JSON."""
    body = {k: v for k, v in rec.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(rec: dict) -> str:
    return hashlib.sha256(canonical(rec)).hexdigest()


def path_for(part: str, order: str, pred_dir=PRED_DIR) -> Path:
    return Path(pred_dir) / f"{part}_{order}.json"


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def freeze(rec: dict, pred_dir=PRED_DIR, frozen_at: str | None = None) -> dict:
    """Stamp `frozen_at` (UTC now unless given), hash, and write `<part>_<order>.json`. Refuses to overwrite."""
    for k in ("part", "order", "predictions"):
        if k not in rec:
            raise ValueError(f"frozen prediction record needs {k!r}")
    p = path_for(rec["part"], rec["order"], pred_dir)
    if p.exists():
        raise FileExistsError(f"{p} is already frozen; a new prediction goes in a new, post-hoc file")
    out = dict(rec)
    out.setdefault("schema", SCHEMA)
    out["frozen_at"] = frozen_at or utc_now()
    out.pop("sha256", None)
    out["sha256"] = digest(out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    return out


def load(part: str, order: str | None, pred_dir=PRED_DIR) -> dict | None:
    if not part or not order:
        return None
    p = path_for(part, order, pred_dir)
    return json.loads(p.read_text()) if p.exists() else None


def verify(rec: dict) -> bool:
    """True when the record's content still matches its stored hash."""
    return bool(rec.get("sha256")) and digest(rec) == rec["sha256"]


def parse_time(s: str | None) -> datetime | None:
    """ISO time or date as an aware UTC datetime. Times without a zone are taken as UTC; a bare date as 00:00 UTC,
    so a measurement dated the same day as the freeze counts as before it (the strict reading)."""
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def status(rec: dict | None, measured_when: str | None) -> str:
    """Whether a measurement taken at `measured_when` may be scored against `rec`:
    "frozen" (yes), "unfrozen" (no record), "hash_mismatch", "frozen_after_measurement", "no_date" (refused)."""
    if rec is None:
        return "unfrozen"
    if not verify(rec):
        return "hash_mismatch"
    fz, mw = parse_time(rec.get("frozen_at")), parse_time(measured_when)
    if fz is None or mw is None:
        return "no_date"
    return "frozen" if fz <= mw else "frozen_after_measurement"


def prediction(rec: dict, key: str) -> dict | None:
    return next((p for p in rec.get("predictions", []) if p.get("key") == key), None)


def from_plan(plan: dict, order: str, overrides: dict | None = None, extra: list | None = None, **meta) -> dict:
    """An unfrozen record from an inspection plan: every plan dimension with its nominal, predicted value, basis,
    findings and tolerance; `overrides[key]` adds or replaces fields (sigma, tests, notes, ...); `extra` appends
    predictions that are not plan dimensions."""
    overrides = overrides or {}
    preds = []
    for d in plan["dimensions"]:
        pr = d.get("predicted") or {}
        tol = d.get("tol") or {}
        e = {"key": d["key"], "plan_id": d.get("id"), "kind": d["kind"], "label": d.get("label"), "unit": d.get("unit", "mm"),
             "nominal": d.get("nominal"), "predicted": pr.get("value"), "basis": pr.get("basis"),
             "findings": [{k: f.get(k) for k in ("code", "severity", "rule", "finding")} for f in pr.get("findings", [])],
             "tol_pm": tol.get("pm"), "tol_source": tol.get("source"), "tol_published": tol.get("published"),
             "instrument": (d.get("method") or {}).get("instrument"), "origin": "plan"}
        e.update(overrides.get(d["key"], {}))
        preds.append(e)
    for x in extra or []:
        preds.append({"origin": "freeze_supplement", **x})
    plan_bytes = json.dumps(plan, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {"schema": SCHEMA, "part": plan["part_id"], "part_name": plan.get("part"), "revision": plan.get("revision"),
            "order": order, "supplier": plan.get("shop"), "material": plan.get("material"), "thickness_mm": plan.get("thickness_mm"),
            "plan_generated": plan.get("generated"), "plan_sha256": hashlib.sha256(plan_bytes).hexdigest(),
            "posthoc": False, **meta, "predictions": preds}
