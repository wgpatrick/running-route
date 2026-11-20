"""The measurement form (inspect_form/index.html): embed the inspection plans in it, and import what it saved.

    .venv/bin/python -m mechloop.inspect.import_form --build [--plans inspect_form/plans]
    .venv/bin/python -m mechloop.inspect.import_form rows.json [--record mechloop/data/measurements/measurements.jsonl]

The form saves one document per submission to the artifact database (collection "measurements"), or shows the same
document as JSON to copy when no database is available. A submission is
{"schema": "mechloop.form_submission/1", "submission_id", "part", "revision", "supplier", "order", "sample", "who_id",
 "measured_by", "when", "notes", "photo", "readings": [{"dimension_id", "dimension_key", "kind", "nominal", "tol_pm",
 "predicted", "expect_out_of_tolerance", "measured", "unit", "instrument", "method"}]}.
The importer accepts one submission, a list of them, or an export of the collection ({"docs": [...]} or rows with a
"data" field) and writes one measurement per reading into the record (mechloop/inspect/record.py), skipping ones
already there.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import record as REC

ROOT = Path(__file__).resolve().parents[2]
FORM = ROOT / "inspect_form" / "index.html"
PLANS = ROOT / "inspect_form" / "plans"
BEGIN, END = "/*PLANS_BEGIN*/", "/*PLANS_END*/"


# ------------------------------------------------------------------------------------------------- build
def _short(s, n=320):
    s = str(s or "")
    return s if len(s) <= n else s[: n - 1] + "…"


def form_entry(plan: dict, svg: str) -> dict:
    """The part of a plan the form shows, kept small."""
    dims = []
    for d in plan["dimensions"]:
        pred = d.get("predicted") or {}
        f = (pred.get("findings") or [])
        dims.append({"id": d["id"], "key": d["key"], "kind": d["kind"], "label": d["label"], "nominal": d["nominal"], "unit": d.get("unit", "mm"),
                     "tol_pm": (d.get("tol") or {}).get("pm"), "tol_source": _short((d.get("tol") or {}).get("source"), 160),
                     "predicted": pred.get("value"), "basis": _short(pred.get("basis"), 260), "expect_out_of_tolerance": bool(pred.get("expect_out_of_tolerance")),
                     "finding": _short(f[0]["finding"], 260) if f else None, "instrument": (d.get("method") or {}).get("instrument"),
                     "how": (d.get("method") or {}).get("how")})
    return {"part_id": plan["part_id"], "part": plan["part"], "revision": plan.get("revision"), "generated": plan.get("generated"),
            "material": plan.get("material"), "thickness_mm": plan.get("thickness_mm"), "form": plan.get("form"), "process": plan.get("process"),
            "shop": plan.get("shop"), "shop_name": plan.get("shop_name"), "scanner_note": (plan.get("scanner") or {}).get("note"),
            "predictions": [{"severity": p["severity"], "finding": _short(p["finding"])} for p in plan.get("predictions", [])],
            "dimensions": dims, "svg": svg}


def build_form(plans_dir=PLANS, form=FORM, order: list[str] | None = None) -> dict:
    """Embed every plan in `plans_dir` (its index.json order, else by name) into the form, between the PLANS markers."""
    plans_dir, form = Path(plans_dir), Path(form)
    idx = plans_dir / "index.json"
    ids = order or ([r["part_id"] for r in json.loads(idx.read_text())] if idx.exists() else
                    sorted(p.stem for p in plans_dir.glob("*.json") if p.name != "index.json"))
    entries = []
    for pid in ids:
        plan = json.loads((plans_dir / f"{pid}.json").read_text())
        svgp = plans_dir / (plan.get("drawing") or f"{pid}.svg")
        entries.append(form_entry(plan, svgp.read_text() if svgp.exists() else ""))
    blob = json.dumps(entries, separators=(",", ":")).replace("</", "<\\/")
    html = form.read_text()
    a, b = html.index(BEGIN) + len(BEGIN), html.index(END)
    form.write_text(html[:a] + blob + html[b:])
    return {"form": str(form), "parts": ids, "bytes": len(form.read_text().encode())}


# ------------------------------------------------------------------------------------------------- import
def _submissions(data) -> list[dict]:
    if isinstance(data, dict):
        if "readings" in data:
            return [data]
        for k in ("docs", "documents", "rows", "items"):
            if k in data:
                return _submissions(data[k])
        return []
    out = []
    for r in data or []:
        if isinstance(r, dict) and "readings" not in r and isinstance(r.get("data"), dict):
            r = r["data"]
        if isinstance(r, dict) and "readings" in r:
            out.append(r)
    return out


def rows_from_form(data) -> list[REC.Measurement]:
    """Measurements from form submissions (any of the shapes in the module docstring)."""
    out = []
    for s in _submissions(data):
        who = s.get("measured_by") or s.get("who_id")
        for r in s.get("readings", []):
            if r.get("measured") is None:
                continue
            out.append(REC.Measurement(
                part=s["part"], dimension_key=r["dimension_key"], dimension_id=r.get("dimension_id"), kind=r.get("kind", ""),
                measured=float(r["measured"]), revision=s.get("revision"), supplier=s.get("supplier"), order=s.get("order"),
                material=s.get("material"), thickness_mm=s.get("thickness_mm"), nominal=r.get("nominal"), tol_pm=r.get("tol_pm"),
                predicted=r.get("predicted"), expect_out_of_tolerance=r.get("expect_out_of_tolerance"), unit=r.get("unit", "mm"),
                method=r.get("method", ""), instrument=r.get("instrument", ""), who=who, when=s.get("when"), photo=s.get("photo"),
                notes=s.get("notes", ""), source="form", manual_steps=1, sample=int(s.get("sample") or 1), submission=s.get("submission_id"),
                plan=s.get("plan_generated")))
    return out


def import_rows(path_or_data, record_path=REC.RECORD) -> dict:
    data = json.loads(Path(path_or_data).read_text()) if isinstance(path_or_data, (str, Path)) else path_or_data
    rows = rows_from_form(data)
    n = REC.add(rows, record_path)
    return {"readings": len(rows), "added": n, "submissions": len(_submissions(data))}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("rows", nargs="?", help="exported form rows (JSON)")
    ap.add_argument("--build", action="store_true", help="embed the inspection plans in the form")
    ap.add_argument("--plans", default=str(PLANS))
    ap.add_argument("--form", default=str(FORM))
    ap.add_argument("--record", default=str(REC.RECORD))
    a = ap.parse_args(argv)
    if a.build:
        print(json.dumps(build_form(a.plans, a.form)))
    if a.rows:
        print(json.dumps(import_rows(a.rows, a.record)))
    if not (a.build or a.rows):
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
