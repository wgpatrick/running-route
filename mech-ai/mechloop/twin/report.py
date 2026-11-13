"""Turn out/eval/evaluation.json into a readable markdown report."""
from __future__ import annotations

import json
from pathlib import Path

from .evals import FAULTS


def _f(v, nd=2):
    if v is None:
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return f"{v:.{nd}f}"
    if isinstance(v, list):
        return " / ".join(_f(x, nd) for x in v)
    return str(v)


def _status(r):
    if r["ok"]:
        return "pass" + (" (warnings)" if r["warnings"] else "")
    return "FAIL: " + ", ".join(sorted(set(r["errors"])))


def write(eval_json: Path, out_md: Path) -> str:
    d = json.loads(Path(eval_json).read_text())
    L = ["# Printer and digital-twin evaluation", "",
         "Everything here was computed in simulation. Friction, extruder lag, damping and belt stiffness are assumed "
         "values; the sensitivity section shows which of them matter.", ""]
    b = d.get("benchmark")
    if b:
        L += ["## Benchmark print suite", "",
              "| Part | Tests | Result | Print time (s) | Slicer's estimate (s) | Outline match (min) | Avg outline offset (mm) | Worst bulge / recess (mm) | Holes open | Longest unsupported gap (mm) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for n, r in b.items():
            L.append(f"| {n} | {r.get('tests', '')} | {_status(r)} | {_f(r['print_time_s'], 0)} | {_f(r['slicer_time_s'], 0)} | "
                     f"{_f(r['outline_iou_min'], 3)} | {_f(r['outline_offset_mm'], 3)} | {_f(r['max_bulge_mm'])} / {_f(r['max_recess_mm'])} | "
                     f"{_f(r['holes_open_fraction'])} | {_f(r['worst_unsupported_span_mm'], 1)} |")
        L += ["", f"Passed {sum(r['ok'] for r in b.values())} of {len(b)}. The twin has no thermal model, so overhang and bridge "
              "parts are scored on geometry only: it reports how far material spans thin air, not how much it sags.", ""]
    e = d.get("envelope")
    if e:
        speeds = list(e["grid"])
        accels = list(e["grid"][speeds[0]])
        L += ["## Speed and acceleration envelope", "",
              "Short cube printed at multiples of the nominal speeds (45-60 mm/s printing, 150 mm/s travel) and of the "
              "nominal 4000 mm/s² acceleration. Each cell: result, print time, worst nozzle lag on Y.", "",
              "| Speed × | " + " | ".join(f"accel ×{a}" for a in accels) + " |", "|---|" + "---|" * len(accels)]
        for v in speeds:
            cells = []
            for a in accels:
                r = e["grid"][v][a]
                tag = "ok" if r["ok"] else "FAIL"
                cells.append(f"{tag}, {_f(r['print_time_s'], 0)} s, {_f((r['worst_lag_mm'] or [0, 0])[1])} mm")
            L.append(f"| ×{v} | " + " | ".join(cells) + " |")
        fp = e.get("fastest_passing")
        if fp:
            L += ["", f"Fastest passing setting: speed ×{fp['speed_scale']}, acceleration ×{fp['accel_scale']} "
                  f"({_f(fp['print_time_s'], 0)} s against {_f(e['baseline_time_s'], 0)} s at nominal).", ""]
    c = d.get("coverage")
    if c:
        L += ["## Build-volume coverage", "", "| Where | Result | Collisions during print | Outline match (min) | Worst lag X / Y / Z (mm) |", "|---|---|---|---|---|"]
        for n, r in c.items():
            L.append(f"| {n} | {_status(r)} | {r['machine_collisions']} | {_f(r['outline_iou_min'], 3)} | {_f(r['worst_lag_mm'], 3)} |")
        L += ["", "The twin's dynamics do not vary with position (stiffness is taken at mid-travel), so this section checks "
              "reachability and collisions across the bed and over the full Z travel, not position-dependent quality.", ""]

    def table(title, rows, intro, extra=None):
        out = [f"## {title}", "", intro, "",
               "| Case | " + (extra[0] + " | " if extra else "") + "Result | RMS lag X / Y (mm) | Worst lag X / Y (mm) | Worst motor error X / Y (mm) | Outline offset (mm) | Bulge (mm) | Outline match |",
               "|---|" + ("---|" if extra else "") + "---|---|---|---|---|---|---|"]
        for n, r in rows.items():
            out.append(f"| {n} | " + (extra[1](n) + " | " if extra else "") + f"{_status(r)} | {_f((r['rms_lag_mm'] or [None] * 2)[:2], 3)} | "
                       f"{_f((r['worst_lag_mm'] or [None] * 2)[:2], 3)} | {_f((r['worst_motor_error_mm'] or [None] * 2)[:2], 3)} | "
                       f"{_f(r['outline_offset_mm'], 3)} | {_f(r['max_bulge_mm'])} | {_f(r['outline_iou_min'], 3)} |")
        return out + [""]

    if d.get("robustness"):
        L += table("Robustness to assumed values", d["robustness"],
                   "The same short print with the assumptions made worse. A sound design keeps passing.")
    if d.get("faults"):
        L += table("Machine faults", d["faults"],
                   "Faults injected into the machine. 'Expected' is what a real printer would do.",
                   ("Expected", lambda n: FAULTS[n][2]))
        L += ["Rail misalignment and binding are not modelled, so they are not in this table.", ""]
    v = d.get("variants")
    if v:
        L += ["## Design variants", "",
              "Each variant at nominal settings, then the highest acceleration it prints cleanly at with speeds doubled "
              "(nominal acceleration is 4000 mm/s²).", "",
              "| Variant | Resonance X / Y (Hz) | Nominal: RMS lag Y (mm) | Nominal: outline match | Highest clean acceleration (mm/s²) | What fails first above that |",
              "|---|---|---|---|---|---|"]
        for n, r in v.items():
            a = r["nominal"]
            mx = r.get("max_passing_accel_scale")
            ff = r.get("first_failure")
            L.append(f"| {n} | {_f((a['resonance_hz'] or [None] * 2)[:2], 0)} | {_f((a['rms_lag_mm'] or [None] * 2)[1], 3)} | "
                     f"{_f(a['outline_iou_min'], 3)} | {('%d' % (mx * 4000)) if mx else 'none'} | "
                     f"{(', '.join(ff['errors']) + ' at %d' % (ff['accel_scale'] * 4000)) if ff else 'nothing up to 40000'} |")
        L += ["", "Variants are what-if changes to mass, torque and belt stiffness on the same CAD; they were not "
              "re-verified as full designs.", ""]
    s = d.get("sensitivity")
    if s:
        keys = list(s["base"])
        rank = sorted(s["parameters"].items(), key=lambda kv: -sum(
            kv[1][k]["swing"] / max(abs(s["base"][k]), 1e-6) for k in keys))
        L += ["## Sensitivity to assumed parameters", "",
              "Each parameter moved to 50% and 150% of its assumed value (torque and mass over a similar range). "
              "Cells show low → high; parameters are ranked by total relative effect.", "",
              "| Parameter | " + " | ".join(k.replace("_", " ") for k in keys) + " | Changes pass/fail? |", "|---|" + "---|" * (len(keys) + 1)]
        L.append("| (baseline) | " + " | ".join(_f(s["base"][k], 3) for k in keys) + " | |")
        for n, r in rank:
            L.append(f"| {n} | " + " | ".join(f"{_f(r[k]['low'], 3)} → {_f(r[k]['high'], 3)}" for k in keys) + f" | {_f(r['verdict_changes'])} |")
        L.append("")
    ref = d.get("voron_reference")
    if ref:
        L += ["## Reality check against a documented printer", "",
              f"{ref['machine']}. Uncertain inputs were sampled over their plausible ranges ({ref['samples']} samples).", "",
              "| Quantity | Twin predicts | Reported for real machines | Verdict | Note |", "|---|---|---|---|---|"]
        for r in ref["rows"]:
            pred = r.get("predicted")
            if isinstance(pred, dict):
                pred = ", ".join(f"{k}: {v}" for k, v in pred.items())
            if pred is None:
                pred = f"{r['predicted_5_95'][0]}–{r['predicted_5_95'][1]} {r.get('unit', '')} (median {r['predicted_median']})"
            obs = r["observed"]
            if isinstance(obs, dict):
                obs = ", ".join(f"{k}: {v}" for k, v in obs.items())
            if isinstance(obs, list) and len(obs) == 2:
                obs = f"{obs[0]}–{obs[1]} {r.get('unit', '')}"
            L.append(f"| {r['quantity']} | {pred} | {obs} | {r['verdict']} | {r.get('note', '')} |")
        L.append("")
    if d.get("seconds"):
        L += [f"Compute time: {d['seconds'].get('total', 0) / 60:.0f} minutes on 4 cores.", ""]
    text = "\n".join(L)
    Path(out_md).write_text(text)
    return text
