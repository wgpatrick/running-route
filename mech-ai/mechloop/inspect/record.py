"""Measurement record, comparison with nominal and prediction, proposed learnings, and the loop's own metrics.

Record (mechloop/data/measurements/measurements.jsonl, one JSON object per measured dimension): part, revision,
supplier, order, dimension id and key (from the inspection plan), kind, nominal, tolerance, predicted, measured, unit,
method, instrument, who, when, photo / scan path, notes, source (form / scan / manual), manual_steps.

Learnings ledger (mechloop/data/learnings/ledger.jsonl, append-only): each systematic deviation found in the record
becomes a PROPOSED learning with its evidence (the measurement ids, n, mean, sd), the target it would change (a supplier
rule value in mechloop/data/supplier_rules, a bend scatter value in mechloop/tolerance/bends.py, a hole allowance in
mechloop/tolerance/process.py, ...), and the prediction error before and after applying it (after: leave-one-out, so a
learning is not credited with fitting its own data). Status changes are appended as events (`set_status`); nothing here
edits a rule: accepting a learning is the owner's or the parent agent's call, and applying it is a separate, reviewed
change.

Loop metrics (`loop_metrics`): loop time (order placed -> first measurement, and design change -> measurement where
known), fidelity (|predicted - measured| per check kind, against |nominal - measured| as the do-nothing baseline), and
autonomy (manual steps per part per order).
"""
from __future__ import annotations

import hashlib
import json
import math
import time
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from . import predictions as P

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "mechloop" / "data" / "measurements" / "measurements.jsonl"
ORDERS = ROOT / "mechloop" / "data" / "measurements" / "orders.jsonl"
LEDGER = ROOT / "mechloop" / "data" / "learnings" / "ledger.jsonl"
SCHEMA = "mechloop.measurement/1"
MIN_N = 3                 # measurements of one kind in one group before a learning is proposed
INSTRUMENTS = ("calipers", "micrometer", "pin_gauge", "square_feeler", "feeler", "radius_gauge", "scanner", "protractor", "ruler", "other")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class Measurement:
    part: str                       # plan part_id (e.g. "RP03" or "printer_v10_1.x_belt_bracket")
    dimension_key: str              # plan dimension key (e.g. "B1.angle", "H3.dia")
    measured: float | None
    kind: str = ""
    dimension_id: int | None = None
    revision: str | None = None
    supplier: str | None = None
    order: str | None = None
    material: str | None = None
    thickness_mm: float | None = None
    nominal: float | None = None
    tol_pm: float | None = None
    predicted: float | None = None
    expect_out_of_tolerance: bool | None = None
    unit: str = "mm"
    method: str = ""
    instrument: str = ""
    who: str | None = None
    when: str | None = None
    photo: str | None = None
    scan: str | None = None
    notes: str = ""
    source: str = "manual"          # form | scan | manual
    manual_steps: int = 1
    sample: int = 1                 # which physical piece of the order (qty > 1)
    submission: str | None = None   # form submission id (one typing session)
    plan: str | None = None
    schema: str = SCHEMA
    id: str = ""

    def __post_init__(self):
        if not self.when:
            self.when = _now()
        if not self.id:
            key = json.dumps([self.part, self.revision, self.order, self.sample, self.dimension_key, self.measured, self.when, self.who, self.source])
            self.id = "M-" + hashlib.sha1(key.encode()).hexdigest()[:12]


def from_plan(plan: dict, key_or_id, measured: float | None, **meta) -> Measurement:
    """A measurement of one plan dimension (by key or number), with nominal, tolerance and prediction taken from the plan."""
    dim = next((d for d in plan["dimensions"] if d["key"] == key_or_id or d["id"] == key_or_id), None)
    if dim is None:
        raise KeyError(f"{plan['part_id']}: no dimension {key_or_id!r} in the plan")
    pred = dim.get("predicted") or {}
    m = dict(part=plan["part_id"], dimension_key=dim["key"], dimension_id=dim["id"], kind=dim["kind"], measured=measured,
             revision=plan.get("revision"), supplier=plan.get("shop"), material=plan.get("material"), thickness_mm=plan.get("thickness_mm"),
             nominal=dim.get("nominal"), tol_pm=(dim.get("tol") or {}).get("pm"), predicted=pred.get("value"),
             expect_out_of_tolerance=pred.get("expect_out_of_tolerance"), unit=dim.get("unit", "mm"),
             method=(dim.get("method") or {}).get("how", ""), instrument=(dim.get("method") or {}).get("instrument", ""))
    m.update({k: v for k, v in meta.items() if v is not None})
    return Measurement(**m)


# ------------------------------------------------------------------------------------------------- storage
def _read_jsonl(path) -> list[dict]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            out.append(json.loads(line))
    return out


def _append_jsonl(path, rows) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def load(path=RECORD) -> list[dict]:
    return _read_jsonl(path)


def add(rows, path=RECORD) -> int:
    """Append measurements (Measurement or dict); ones whose id is already in the record are skipped. Returns the number added."""
    have = {r.get("id") for r in load(path)}
    new = []
    for r in rows:
        d = asdict(r) if isinstance(r, Measurement) else dict(Measurement(**{k: v for k, v in r.items() if k in Measurement.__dataclass_fields__}).__dict__)
        if d["id"] not in have:
            new.append(d)
            have.add(d["id"])
    _append_jsonl(path, new)
    return len(new)


def add_order(order: str, supplier: str, parts: list[str], placed: str, received: str | None = None, design_changed: str | None = None,
              path=ORDERS, **extra) -> dict:
    row = {"order": order, "supplier": supplier, "parts": parts, "placed": placed, "received": received, "design_changed": design_changed, **extra}
    _append_jsonl(path, [row])
    return row


# ------------------------------------------------------------------------------------------------- comparison
class PredictionWarning(UserWarning):
    """A measurement scored against an unfrozen prediction, or refused against one frozen after it."""


def _frozen_prediction(r: dict, pred_dir, cache: dict, warned: set):
    """(status, frozen entry or None) for a measurement row; warns once per (part, order) and status."""
    part, order = r.get("part"), r.get("order")
    if (part, order) not in cache:
        rec = P.load(part, order, pred_dir)
        cache[(part, order)] = rec
    rec = cache[(part, order)]
    st = P.status(rec, r.get("when"))
    if st != "frozen" and (part, order, st) not in warned:
        warned.add((part, order, st))
        msg = {"unfrozen": "scored against the plan's current prediction, which was never frozen (post hoc risk)",
               "hash_mismatch": "frozen prediction file fails its sha256 check: prediction not scored",
               "frozen_after_measurement": "prediction frozen after the measurement was taken: prediction not scored",
               "no_date": "measurement or freeze has no usable date: prediction not scored"}[st]
        warnings.warn(f"{part} / order {order}: {msg}", PredictionWarning, stacklevel=3)
    return st, (P.prediction(rec, r.get("dimension_key")) if st == "frozen" else None)


def compare(rows: list[dict], pred_dir=None) -> list[dict]:
    """Each measurement against nominal and prediction: dev_nominal, dev_predicted, in_tolerance, prediction_better.

    The prediction comes from the frozen file for the row's part and order (mechloop.inspect.predictions) when there is
    one: it is scored only if the file verifies and was frozen no later than the measurement (`prediction_status`
    "frozen"); otherwise the prediction is refused (dev_predicted None). With no frozen file the row's copied plan
    prediction is used, with a PredictionWarning (`prediction_status` "unfrozen")."""
    pred_dir = P.PRED_DIR if pred_dir is None else pred_dir
    cache: dict = {}
    warned: set = set()
    out = []
    for r in rows:
        m, n, p, tol = r.get("measured"), r.get("nominal"), r.get("predicted"), r.get("tol_pm")
        if m is None:
            continue
        c = dict(r)
        st, fp = _frozen_prediction(r, pred_dir, cache, warned)
        c["prediction_status"] = st
        if st == "frozen" and fp is not None:
            p = fp.get("predicted")
            c["predicted"], c["pred_sigma"] = p, fp.get("sigma")
            u = r.get("u") or 0.0
            if p is not None and fp.get("sigma"):
                c["z"] = round((m - p) / math.sqrt(fp["sigma"] ** 2 + u ** 2), 3)
        else:
            if st == "frozen":                  # the order is frozen but this quantity was not in it
                c["prediction_status"] = "not_in_frozen_record"
            if st != "unfrozen":
                p = None
                c["predicted"] = None
        c["dev_nominal"] = None if n is None else round(m - n, 4)
        c["dev_predicted"] = None if p is None else round(m - p, 4)
        c["in_tolerance"] = None if (n is None or tol is None) else bool(abs(m - n) <= tol + 1e-9)
        if r.get("expect_out_of_tolerance") is not None and c["in_tolerance"] is not None:
            c["prediction_flag_right"] = bool(r["expect_out_of_tolerance"]) == (not c["in_tolerance"])
        if n is not None and p is not None:
            c["prediction_better"] = abs(m - p) < abs(m - n) - 1e-9 if abs(p - n) > 1e-9 else None
        out.append(c)
    return out


def _group_key(r) -> tuple:
    t = r.get("thickness_mm")
    return (r.get("supplier"), r.get("material"), None if t is None else round(float(t), 3), r.get("kind"))


def summarize(rows: list[dict]) -> list[dict]:
    """Per (supplier, material, thickness, kind): n, mean and sd of measured - nominal and measured - predicted."""
    groups: dict[tuple, list] = {}
    for c in compare(rows):
        groups.setdefault(_group_key(c), []).append(c)
    out = []
    for (sup, mat, t, kind), cs in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        dn = np.array([c["dev_nominal"] for c in cs if c["dev_nominal"] is not None], float)
        dp = np.array([c["dev_predicted"] for c in cs if c["dev_predicted"] is not None], float)
        out.append({"supplier": sup, "material": mat, "thickness_mm": t, "kind": kind, "n": len(cs),
                    "mean_dev_nominal": round(float(dn.mean()), 4) if len(dn) else None, "sd_dev_nominal": round(float(dn.std(ddof=1)), 4) if len(dn) > 1 else None,
                    "mean_dev_predicted": round(float(dp.mean()), 4) if len(dp) else None,
                    "mean_abs_err_predicted": round(float(np.abs(dp).mean()), 4) if len(dp) else None,
                    "mean_abs_err_nominal": round(float(np.abs(dn).mean()), 4) if len(dn) else None,
                    "in_tolerance": sum(1 for c in cs if c.get("in_tolerance")), "out_of_tolerance": sum(1 for c in cs if c.get("in_tolerance") is False)})
    return out


# ------------------------------------------------------------------------------------------------- learnings
def _loo_abs_err(values: np.ndarray, baseline: np.ndarray | None = None) -> float:
    """Mean |v_i - mean(v_others)|: the error of a learned constant on a measurement it was not fitted to."""
    v = np.asarray(values, float)
    n = len(v)
    if n < 2:
        return float("nan")
    s = v.sum()
    return float(np.mean(np.abs(v - (s - v) / (n - 1))))


def _significant(dev: np.ndarray, floor: float) -> bool:
    n = len(dev)
    if n < 2:
        return False
    sem = dev.std(ddof=1) / math.sqrt(n)
    return abs(dev.mean()) > max(2.0 * sem, floor)


def _fmt_t(t):
    if t is None:
        return "?"
    inch = t / 25.4
    return f"{inch:.3f} in ({t:g} mm)".replace("0.", ".", 1) if abs(inch * 1000 - round(inch * 1000)) < 0.6 else f"{t:g} mm"


def _rule_for(supplier, material, t, kind):
    try:
        from ..shops import supplier_rules as SR

        rs = [r for r in SR.applicable(supplier, material, t, kinds={kind}) if r.get("evaluate") is not False and not r.get("duplicate_of")]
        return rs[0] if rs else None
    except Exception:
        return None


def propose_learnings(rows: list[dict], min_n: int = MIN_N) -> list[dict]:
    """Systematic deviations in the record turned into proposed learnings (not written; see `update_ledger`)."""
    from ..shops import supplier_rules as SR
    from ..tolerance.bends import BEND_TOLERANCE
    from ..tolerance.process import PROCESS

    cs = compare(rows)
    groups: dict[tuple, list] = {}
    for c in cs:
        groups.setdefault(_group_key(c), []).append(c)
    out = []

    def learning(kind, title, target, members, values, before, after, extra=None):
        ids = sorted(m["id"] for m in members)
        key = json.dumps([kind, target.get("file"), target.get("rule_id") or target.get("key"), ids])
        return {"id": "L-" + hashlib.sha1(key.encode()).hexdigest()[:10], "event": "proposed", "created": _now(), "status": "proposed", "kind": kind,
                "title": title, "target": target,
                "evidence": {"measurement_ids": ids, "n": len(values), "mean": round(float(np.mean(values)), 4),
                             "sd": round(float(np.std(values, ddof=1)), 4) if len(values) > 1 else None, "values": [round(float(v), 4) for v in values],
                             "parts": sorted({m["part"] for m in members}), "orders": sorted({str(m.get("order")) for m in members})},
                "error_before": before, "error_after": after, "proposed_by": "mechloop.inspect.record.propose_learnings",
                "decision": None, "note": "Proposed only: accepting is the owner's or parent's call; no rule file is edited by this module.", **(extra or {})}

    for (sup, mat, t, kind), g in groups.items():
        sname = SR.name_of(sup) if sup else "?"
        meas = np.array([c["measured"] for c in g], float)
        if len(g) < min_n:
            continue
        dp = np.array([c["dev_predicted"] if c["dev_predicted"] is not None else c["dev_nominal"] for c in g], float)
        dn = np.array([c["dev_nominal"] for c in g], float)
        if kind == "bend_radius":
            rule = _rule_for(sup, mat, t, "bend_radius")
            cur = float(rule["value_mm"]) if rule else None
            if cur is None:
                continue
            m = float(meas.mean())
            err_b = float(np.mean(np.abs(meas - cur)))
            if not _significant(meas - cur, 0.02):
                continue
            out.append(learning("supplier_bend_radius",
                                f"{sname} {mat} {_fmt_t(t)} inside bend radius measured {m:.2f} mm vs rule {cur:g} mm (n={len(g)})",
                                {"type": "supplier_rule", "file": f"mechloop/data/supplier_rules/{sup}.json", "rule_id": rule["id"], "field": "value_mm",
                                 "current": cur, "proposed": round(m, 3)},
                                g, meas, {"mean_abs_mm": round(err_b, 4), "basis": "rule value as the prediction"},
                                {"mean_abs_mm": round(_loo_abs_err(meas), 4), "basis": "measured mean, leave-one-out"}))
        elif kind == "bend_angle":
            dev = meas - np.array([c["nominal"] for c in g], float)
            sd_model = BEND_TOLERANCE["angle_sd_deg"]
            if _significant(dev, 0.1):
                out.append(learning("bend_angle_bias",
                                    f"{sname} {mat} {_fmt_t(t)} bends come out {dev.mean():+.2f} deg from nominal on average (n={len(g)})",
                                    {"type": "model_value", "file": "mechloop/tolerance/bends.py", "key": "BEND_TOLERANCE['angle_bias_deg'] (new field)",
                                     "current": 0.0, "proposed": round(float(dev.mean()), 3), "scope": {"supplier": sup, "material": mat, "thickness_mm": t}},
                                    g, dev, {"mean_abs_deg": round(float(np.abs(dev).mean()), 4), "basis": "nominal angle as the prediction"},
                                    {"mean_abs_deg": round(_loo_abs_err(dev), 4), "basis": "nominal + measured bias, leave-one-out"}))
            if len(g) >= 5:
                sd = float(dev.std(ddof=1))
                if abs(sd - sd_model) > 0.3 * sd_model:
                    out.append(learning("bend_angle_scatter",
                                        f"{sname} {mat} {_fmt_t(t)} bend angle scatter {sd:.2f} deg (1 sd) vs model {sd_model:g} deg (n={len(g)})",
                                        {"type": "model_value", "file": "mechloop/tolerance/bends.py", "key": "BEND_TOLERANCE['angle_sd_deg']",
                                         "current": sd_model, "proposed": round(sd, 3), "scope": {"supplier": sup, "material": mat, "thickness_mm": t}},
                                        g, dev, {"model_sd": sd_model}, {"measured_sd": round(sd, 4)}))
        elif kind in ("flange_length", "hole_to_bend", "web_width"):
            if not _significant(dp, 0.05):
                continue
            k_rule = _rule_for(sup, mat, t, "k_factor")
            # a constant flange error e per bend is a bend-allowance error: dBA = -2 e => dK = -2 e / (t * angle) at 90 degrees
            per_bend = dp.mean() / (2.0 if kind == "web_width" else 1.0)
            dk = None
            if k_rule and t:
                dk = -2.0 * per_bend / (float(t) * math.pi / 2)
            target = ({"type": "supplier_rule", "file": f"mechloop/data/supplier_rules/{sup}.json", "rule_id": k_rule["id"], "field": "value",
                       "current": k_rule.get("value"), "proposed": round(float(k_rule.get("value")) + dk, 3),
                       "derivation": "per-bend flange error e -> K-factor change dK = -2 e / (t x bend angle in rad)"} if dk is not None else
                      {"type": "model_value", "file": "mechloop/inspect/plan.py", "key": "_predict_flange_shift (bend allowance)", "current": 0.0,
                       "proposed": round(float(per_bend), 3)})
            out.append(learning("bend_allowance",
                                f"{sname} {mat} {_fmt_t(t)} {kind.replace('_', ' ')} off the prediction by {dp.mean():+.2f} mm on average (n={len(g)})",
                                target, g, dp, {"mean_abs_mm": round(float(np.abs(dp).mean()), 4), "basis": "plan prediction"},
                                {"mean_abs_mm": round(_loo_abs_err(dp), 4), "basis": "prediction + measured bias, leave-one-out"}))
            if len(g) >= 5:
                sd = float(dp.std(ddof=1))
                model = BEND_TOLERANCE["line_sd_mm"] * (math.sqrt(2) if kind == "web_width" else 1.0)
                if abs(sd - model) > 0.3 * model:
                    out.append(learning("bend_line_scatter", f"{sname} {mat} {_fmt_t(t)} bend-line scatter {sd:.2f} mm (1 sd) vs model {model:.2f} mm (n={len(g)})",
                                        {"type": "model_value", "file": "mechloop/tolerance/bends.py", "key": "BEND_TOLERANCE['line_sd_mm']",
                                         "current": BEND_TOLERANCE["line_sd_mm"], "proposed": round(sd / (math.sqrt(2) if kind == "web_width" else 1.0), 3)},
                                        g, dp, {"model_sd": model}, {"measured_sd": round(sd, 4)}))
        elif kind in ("hole_diameter", "hole_ovality"):
            sub = [c for c in g if kind == "hole_diameter" or c["dimension_key"].endswith("dia_along")]
            if len(sub) < min_n:
                sub = []
            if sub:
                d = np.array([c["dev_predicted"] if c["dev_predicted"] is not None else c["dev_nominal"] for c in sub], float)
                if _significant(d, 0.02):
                    proc = "sheet"
                    cur = PROCESS[proc]["hole_bias"]
                    out.append(learning("hole_allowance",
                                        f"{sname} {mat} {_fmt_t(t)} holes come out {d.mean():+.3f} mm on diameter (n={len(sub)})",
                                        {"type": "model_value", "file": "mechloop/tolerance/process.py", "key": f"PROCESS['{proc}']['hole_bias'] (or a per-shop allowance)",
                                         "current": cur, "proposed": round(cur + float(d.mean()), 3), "scope": {"supplier": sup, "material": mat, "thickness_mm": t}},
                                        sub, d, {"mean_abs_mm": round(float(np.abs(d).mean()), 4)},
                                        {"mean_abs_mm": round(_loo_abs_err(d), 4), "basis": "leave-one-out"}))
            if kind == "hole_ovality":
                # pair across / along readings of one hole: ovality = across - along; did the predicted distortion happen?
                by_hole: dict = {}
                for c in g:
                    h = (c["part"], c.get("order"), c.get("sample"), c["dimension_key"].rsplit(".", 1)[0])
                    by_hole.setdefault(h, {})["across" if c["dimension_key"].endswith("across") else "along"] = c
                ov, mem = [], []
                for h, pair in by_hole.items():
                    if "across" in pair and "along" in pair:
                        ov.append(pair["across"]["measured"] - pair["along"]["measured"])
                        mem += [pair["across"], pair["along"]]
                tol = float(np.median([c["tol_pm"] for c in g if c.get("tol_pm") is not None] or [0.127]))
                if len(ov) >= min_n:
                    ov = np.array(ov)
                    hit = float(ov.mean()) > tol
                    out.append(learning("hole_near_bend",
                                        f"{sname} {mat} {_fmt_t(t)} holes near a bend: ovality {ov.mean():+.3f} mm (n={len(ov)}): "
                                        + ("the predicted distortion happened" if hit else "smaller than the cut tolerance: the hole-near-bend rule may be conservative here"),
                                        {"type": "rule_evidence", "file": "mechloop/verifiers/dfm_sheet.py", "key": "sheet.hole_to_bend_t_ratio (hole_too_close_to_bend)",
                                         "current": "warning at < 2 x thickness", "proposed": "confirmed" if hit else "review the limit with this evidence"},
                                        mem, ov, {"predicted": "out of tolerance (oval)"}, {"measured_mean_ovality_mm": round(float(ov.mean()), 4), "tolerance_mm": tol}))
        elif kind in ("hole_position", "hole_pitch", "overall", "edge_web", "slot_width"):
            if kind in ("hole_pitch", "overall"):
                nom = np.array([c["nominal"] for c in g], float)
                frac = dn / np.maximum(nom, 1e-9)
                if _significant(frac * 100, 0.02) and nom.max() > 20:
                    out.append(learning("scale",
                                        f"{sname} {mat} {_fmt_t(t)} {kind.replace('_', ' ')}s come out {frac.mean() * 100:+.3f} % of nominal (n={len(g)})",
                                        {"type": "model_value", "file": "mechloop/tolerance/process.py", "key": "PROCESS['sheet']['scale'] (as a bias)",
                                         "current": 0.0, "proposed": round(float(frac.mean()), 6)},
                                        g, frac, {"mean_abs_mm": round(float(np.abs(dn).mean()), 4)},
                                        {"mean_abs_mm": round(float(np.mean(np.abs(dn - nom * (frac.sum() - frac) / max(len(frac) - 1, 1)))), 4),
                                         "basis": "nominal x (1 + bias), leave-one-out"}))
            elif kind in ("edge_web", "slot_width") and _significant(dn, 0.03):
                out.append(learning("kerf",
                                    f"{sname} {mat} {_fmt_t(t)} {kind.replace('_', ' ')} off nominal by {dn.mean():+.3f} mm (n={len(g)}): a kerf-compensation error",
                                    {"type": "supplier_rule", "file": f"mechloop/data/supplier_rules/{sup}.json", "rule_id": (_rule_for(sup, mat, t, "kerf") or {}).get("id"),
                                     "field": "note (kerf compensation as made)", "current": None, "proposed": round(float(dn.mean()), 4)},
                                    g, dn, {"mean_abs_mm": round(float(np.abs(dn).mean()), 4)}, {"mean_abs_mm": round(_loo_abs_err(dn), 4)}))
    return out


def ledger(path=LEDGER) -> dict:
    """The ledger folded: {learning id: current state} (proposals plus their status events)."""
    state: dict = {}
    for row in _read_jsonl(path):
        if row.get("event") == "proposed":
            state[row["id"]] = dict(row)
        elif row.get("event") == "status" and row.get("id") in state:
            state[row["id"]].update({"status": row["status"], "decision": {k: row.get(k) for k in ("by", "when", "note")}})
    return state


def update_ledger(rows: list[dict] | None = None, path=LEDGER, record_path=RECORD, min_n: int = MIN_N) -> list[dict]:
    """Propose learnings from the record and append the new ones (same id = same evidence: skipped). A proposal whose
    target already has an open proposal on fewer measurements is marked as superseding it."""
    rows = load(record_path) if rows is None else rows
    have = ledger(path)
    new = []
    for L in propose_learnings(rows, min_n=min_n):
        if L["id"] in have:
            continue
        tkey = (L["target"].get("file"), L["target"].get("rule_id") or L["target"].get("key"), L["kind"])
        older = [o for o in have.values() if (o["target"].get("file"), o["target"].get("rule_id") or o["target"].get("key"), o["kind"]) == tkey
                 and o["status"] == "proposed"]
        if older:
            L["supersedes"] = [o["id"] for o in older]
        new.append(L)
    _append_jsonl(path, new)
    return new


def set_status(learning_id: str, status: str, by: str, note: str = "", path=LEDGER) -> dict:
    """Record a decision on a learning (accepted / rejected / applied / superseded). Does not apply it."""
    if status not in ("accepted", "rejected", "applied", "superseded", "proposed"):
        raise ValueError(f"unknown status {status!r}")
    if learning_id not in ledger(path):
        raise KeyError(learning_id)
    ev = {"event": "status", "id": learning_id, "status": status, "by": by, "when": _now(), "note": note}
    _append_jsonl(path, [ev])
    return ev


# ------------------------------------------------------------------------------------------------- loop metrics
def _t(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return time.mktime(time.strptime(s[:19], fmt))
        except ValueError:
            continue
    return None


def loop_metrics(rows: list[dict] | None = None, orders: list[dict] | None = None, record_path=RECORD, orders_path=ORDERS) -> dict:
    """Loop time, fidelity and autonomy from the record (docs/ROADMAP.md: measure the loop, not just the parts)."""
    rows = load(record_path) if rows is None else rows
    orders = _read_jsonl(orders_path) if orders is None else orders
    merged: dict = {}                 # an order may be appended again later (received date): later non-empty fields win
    for o in orders:
        cur = merged.setdefault(o["order"], {})
        cur.update({k: v for k, v in o.items() if v not in (None, "", [])})
    orders = list(merged.values())
    by_order: dict = {}
    for r in rows:
        by_order.setdefault(r.get("order"), []).append(r)
    loop = []
    for o in orders:
        ms = by_order.get(o["order"], [])
        first = min((_t(r.get("when")) for r in ms if _t(r.get("when"))), default=None)
        placed, received, changed = _t(o.get("placed")), _t(o.get("received")), _t(o.get("design_changed"))
        day = 86400.0
        loop.append({"order": o["order"], "supplier": o.get("supplier"), "parts": o.get("parts"),
                     "order_to_received_days": round((received - placed) / day, 2) if placed and received else None,
                     "received_to_measured_days": round((first - received) / day, 2) if first and received else None,
                     "order_to_measured_days": round((first - placed) / day, 2) if first and placed else None,
                     "design_change_to_measured_days": round((first - changed) / day, 2) if first and changed else None,
                     "measurements": len(ms)})
    fid = []
    for s in summarize(rows):
        fid.append({k: s[k] for k in ("supplier", "material", "thickness_mm", "kind", "n", "mean_abs_err_predicted", "mean_abs_err_nominal")})
    # autonomy: human actions per part per order. A scan is one action however many features it measures; every other
    # reading is one action; a form submission adds one (typing it in); steps the importer or scanner did are not counted.
    auto = []
    groups: dict = {}
    for r in rows:
        groups.setdefault((r.get("part"), r.get("order"), r.get("sample", 1)), []).append(r)
    for (part, order, sample), ms in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        scans = {r.get("scan") for r in ms if r.get("instrument") == "scanner" and r.get("scan")}
        manual = sum(int(r.get("manual_steps", 1)) for r in ms if r.get("instrument") != "scanner")
        subs = {r.get("submission") for r in ms if r.get("source") == "form" and r.get("submission")}
        auto.append({"part": part, "order": order, "sample": sample, "manual_steps": manual + len(scans) + len(subs), "readings": len(ms),
                     "scans": len(scans)})
    return {"loop_time": loop, "fidelity": fid, "autonomy": auto,
            "totals": {"measurements": len(rows), "orders": len(orders),
                       "manual_steps_per_part": round(float(np.mean([a["manual_steps"] for a in auto])), 2) if auto else None}}


# ------------------------------------------------------------------------------------------------- from a scan
def rows_from_scan(scan: dict, plan: dict, **meta) -> list[Measurement]:
    """Measurements of the plan's scanner-measurable dimensions from a scan result (scan.ScanResult.to_json(), measured
    with the plan so that `plan_ids` maps DXF features to plan ids)."""
    pf = scan.get("plan_ids") or {}
    ids = {str(k): v for k, v in (pf.get("ids") or {}).items()}
    A, b = pf.get("A"), pf.get("b")
    if A is None:
        return []
    A, b = np.asarray(A, float), np.asarray(b, float)
    holes = {}
    for h in scan.get("holes", []):
        j = h.get("dxf_index")
        if j is not None and str(j) in ids:
            holes[ids[str(j)]] = h
    meta = {"source": "scan", "instrument": "scanner", "scan": scan.get("image"), "manual_steps": 0, **meta}
    out = []
    for d in plan["dimensions"]:
        kind, feats = d["kind"], d.get("features") or []
        val = None
        if kind in ("hole_diameter",) and feats and feats[0] in holes:
            val = holes[feats[0]]["measured_d"]
        elif kind == "hole_position" and feats and feats[0] in holes:
            p = A @ np.asarray(holes[feats[0]]["measured_center"], float) + b
            # the plan's datums are the bounding-box edges: shift by the outline's measured extreme offset is ignored here
            val = float(p[0] if d["key"].endswith(".x") else p[1])
        elif kind == "hole_pitch" and len(feats) == 2 and all(f in holes for f in feats):
            val = float(np.linalg.norm(np.asarray(holes[feats[0]]["measured_center"]) - np.asarray(holes[feats[1]]["measured_center"])))
        elif kind == "edge_web" and feats and feats[0] in holes:
            val = holes[feats[0]].get("edge_web")
        elif kind == "overall":
            ov = scan.get("overall") or {}
            ax = d["key"].split(".")[-1]
            if ax in ("X", "Y") and ov.get("measured"):
                k = int(np.argmax(np.abs(A[{"X": 0, "Y": 1}[ax]])))      # which DXF axis the plan axis lies along
                val = float(ov["measured"][k])
        if val is not None:
            out.append(from_plan(plan, d["key"], round(float(val), 4), **meta))
    return out


def report(record_path=RECORD, ledger_path=LEDGER, orders_path=ORDERS) -> dict:
    rows = load(record_path)
    return {"summary": summarize(rows), "learnings": list(ledger(ledger_path).values()), "loop": loop_metrics(rows, record_path=record_path, orders_path=orders_path)}


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Measurement record: summary, proposed learnings, loop metrics.")
    ap.add_argument("cmd", choices=["summary", "propose", "metrics", "accept", "reject"])
    ap.add_argument("--id")
    ap.add_argument("--by", default="owner")
    ap.add_argument("--note", default="")
    ap.add_argument("--record", default=str(RECORD))
    ap.add_argument("--ledger", default=str(LEDGER))
    a = ap.parse_args(argv)
    if a.cmd == "summary":
        print(json.dumps(summarize(load(a.record)), indent=1))
    elif a.cmd == "propose":
        print(json.dumps(update_ledger(path=a.ledger, record_path=a.record), indent=1))
    elif a.cmd == "metrics":
        print(json.dumps(loop_metrics(record_path=a.record), indent=1))
    else:
        print(json.dumps(set_status(a.id, "accepted" if a.cmd == "accept" else "rejected", a.by, a.note, path=a.ledger)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
