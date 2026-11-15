"""Showcase stage 'page': read every number from the verification files and write showcase/index.html.

Charts are plain HTML and CSS (rows with marks placed by percentage), so their text stays readable at phone width and
follows the page's light and dark themes. Pictures are referenced by relative path. The file is written without
<html>/<head>/<body> wrappers because the publishing step adds them.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path("/tmp/claude-0/-home-user-running-route/87481e0a-8f62-5246-a6fc-1c1f80e15b45/scratchpad")
VERIFIERS = ["geometry", "interference", "tolerance", "manufacture", "ratings", "motion", "subsystems", "electrical",
             "assemblability", "fea", "printing", "requirements"]
VERIFIER_WHAT = {
    "geometry": "parts are valid solids, inside the envelope, mass and vendor CAD agree",
    "interference": "no two parts overlap; screws reach thread and do not bottom out",
    "tolerance": "3,000 simulated builds: do screws start, do gaps close, is there enough adjustment",
    "manufacture": "each made part can be cut, printed or machined as drawn",
    "ratings": "motors, guides, belts and bearings are inside their makers' ratings",
    "motion": "nothing collides anywhere in the travel, belts route, drives have margin",
    "subsystems": "homing switches, bed probe, cables, the things a printer needs",
    "electrical": "wiring, power budget, mains safety, heater faults, the generated firmware config",
    "assemblability": "an order exists in which every part can be placed and every screw driven",
    "fea": "stiffness and stress of loaded parts and assemblies, heated bed, bed support",
    "printing": "a test print on the dynamic model of the machine",
    "requirements": "the design's own stated requirements",
}
# Reports made under the current checks that live outside the repository. --refresh copies a small extract of each
# into showcase/data/inputs/ so the page can be rebuilt after the scratch folders are gone.
INPUT_SOURCES = {
    "verify_today_printer_v7": SCRATCH / "showcase/vout/printer_v7/report.json",
    "verify_today_printer_v6": SCRATCH / "showcase/vout/printer_v6/report.json",
    "verify_today_ref_vminion": SCRATCH / "showcase/vout/ref_vminion/report.json",
    "study_a": SCRATCH / "agentV8/out_study/v8_bed_a_cantilever/report_partial.json",
    "study_b": SCRATCH / "agentV8/out_study/v8_bed_b_two_screws/report_partial.json",
    "study_c": SCRATCH / "agentV8/out_study/v8_bed_c_three_screws_two_blocks/report_partial.json",
}
# docs/REFERENCE_MACHINE.md section 5 classifies every error raised on the known-good machine. The classes are that
# document's; the counts come from out/ref_vminion/report.json.
REF_CLASS = {
    "screws_may_not_align": "checker", "thread_engagement": "checker", "floating_parts": "checker",
    "unfastened": "checker", "heater_overshoot": "checker_probable", "requirement_failed": "modelling",
    "thread_bottoms_out": "missing", "probe_signal_over_voltage": "missing", "adjustment_too_small": "missing",
    "no_independent_cutoff": "real", "frame_not_earthed": "real", "mains_fuse_too_small": "real",
}
REF_CLASS_LABEL = {
    "checker": "Checker's fault", "checker_probable": "Checker's fault, probable", "missing": "Catalogue part or data missing",
    "modelling": "Modelling mistake", "real": "Real property of the machine", "new": "Raised by checks added later, not classified",
}


# ------------------------------------------------------------------------------------------- reading

def _utc(p: Path) -> str:
    return dt.datetime.fromtimestamp(p.stat().st_mtime, dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _summary(rep: dict) -> dict:
    out = {}
    for k, v in (rep.get("summary") or {}).items():
        m = re.match(r"(\w+) \((\d+) errors?, (\d+) warnings?", v)
        out[k] = {"status": m.group(1).lower(), "errors": int(m.group(2)), "warnings": int(m.group(3))} if m else {
            "status": "not run", "errors": 0, "warnings": 0}
    return out


def slim(rep: dict, src: Path) -> dict:
    """The part of a verify report the page uses."""
    m = rep.get("metrics") or {}
    tol = m.get("tolerance") or {}
    cl = tol.get("clearances") or {}
    z = ((m.get("subsystems") or {}).get("homing") or {}).get("z") or {}
    bs = (m.get("fea") or {}).get("bed_support") or {}
    return {
        "design": rep.get("design"), "ok": rep.get("ok"), "source": str(src), "report_time": _utc(src),
        "summary": rep.get("summary"),
        "findings": [{"verifier": f["verifier"], "severity": f["severity"], "code": f["code"], "message": f["message"][:420]}
                     for f in rep.get("findings", []) if f["severity"] in ("error", "warning")],
        "parts": (m.get("geometry") or {}).get("parts"),
        "tolerance_printer": {k: v for k, v in (tol.get("printer") or {}).items() if not isinstance(v, (list, dict))},
        "clearances": {"pairs_examined": cl.get("pairs_examined"), "pairs_closing": cl.get("pairs_closing"),
                       "threshold_mm": cl.get("threshold_mm"), "builds": tol.get("builds_simulated"),
                       "pairs": [{k: p.get(k) for k in ("parts", "gap_mm", "gap_sd_mm", "p_closed", "p_closed_standard_error",
                                                        "gap_mm_0p15_percentile", "p_closed_normal_estimate", "severity", "processes")}
                                 for p in cl.get("pairs", [])]},
        "probe": {k: z.get(k) for k in ("x_offset", "y_offset", "unprobed_strip_mm", "edge_margin_mm", "print_area", "mesh_min",
                                        "mesh_max", "target", "sensing_distance_mm", "face_above_nozzle_mm", "z_offset_range_mm")},
        "probe_metal_near": ((z.get("mounting") or {}).get("metal_near_zone_under_tolerance") or {}).get("near"),
        "bed_support": {k: bs.get(k) for k in ("print_weight", "hand_load", "constraint")} if bs else None,
    }


def refresh_inputs(inputs: Path) -> None:
    inputs.mkdir(parents=True, exist_ok=True)
    for key, src in INPUT_SOURCES.items():
        if not src.exists():
            print(f"  input {key}: {src} not there; keeping the stored extract" if (inputs / f"{key}.json").exists()
                  else f"  input {key}: {src} not there and no stored extract: that row is left off the page")
            continue
        rep = json.loads(src.read_text())
        old = src.with_name("report_old.json")
        if old.exists() and old.read_bytes() == src.read_bytes():
            print(f"  input {key}: the run has not finished (report unchanged); skipped")
            continue
        (inputs / f"{key}.json").write_text(json.dumps(slim(rep, src), indent=1, default=str))


def _load(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def _last_score(p: Path):
    if not p.exists():
        return None, None
    rows = [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
    full = next((r for r in reversed(rows) if r.get("ranges")), None)
    fw = next((r for r in reversed(rows) if (r.get("klipper") or {}).get("ran")), None)
    return full, fw


def md_section_bullets(md: Path, heading: str) -> list:
    out, on, cur = [], False, None
    for line in md.read_text().splitlines():
        if line.startswith("## "):
            on = line[3:].strip().lower() == heading.lower()
            continue
        if not on:
            continue
        if line.startswith("- "):
            cur = line[2:].strip()
            out.append(cur)
        elif line.startswith("  ") and out:
            out[-1] += " " + line.strip()
    return out


def collect(design_path: Path, show: Path) -> dict:
    name = design_path.stem
    out_dir = ROOT / "out" / name
    inputs = show / "data" / "inputs"
    rep_path = out_dir / "report.json"
    rep = json.loads(rep_path.read_text())
    m = rep["metrics"]
    F: dict = {"design": name, "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
               "report_time": _utc(rep_path), "sources": {}}
    F["renders"] = _load(show / "data" / "renders.json") or {}
    F["fea_fields"] = _load(show / "data" / "fea_fields.json")
    g = m["geometry"]
    s = _summary(rep)
    F["headline"] = {
        "parts": g["parts"], "cots_parts": g["cots_parts"], "custom_parts": m["manufacture"]["custom_parts"],
        "by_process": m["manufacture"]["by_process"], "mass_kg": g["mass_kg"], "bbox_mm": g["bbox_mm"],
        "bom_usd": m["ratings"]["bom_cost_usd_estimate"], "machining_usd": m["manufacture"].get("machining_cost_estimate_usd_qty1"),
        "errors": sum(v["errors"] for v in s.values()), "warnings": sum(v["warnings"] for v in s.values()),
        "verifiers": len(s), "passed": sum(1 for v in s.values() if v["status"] == "pass"),
        "verify_seconds": (rep.get("artifacts") or {}).get("seconds", {}).get("verify"),
        "requirements": m["requirements"], "builds": m["tolerance"]["builds_simulated"],
        "pairs_considered": m["interference"]["pairs"], "poses_checked": m["motion"]["poses_checked"],
    }
    # ---- verifier strips
    strips = []

    def strip(label, basis, rp_or_slim, src_label):
        if rp_or_slim is None:
            return
        sm = _summary(rp_or_slim)
        strips.append({"label": label, "basis": basis, "summary": sm, "when": rp_or_slim.get("report_time"),
                       "errors": sum(v["errors"] for v in sm.values()), "warnings": sum(v["warnings"] for v in sm.values()),
                       "source": src_label,
                       "error_findings": [f for f in rp_or_slim.get("findings", []) if f["severity"] == "error"]})

    for v in ("printer_v6", "printer_v7"):
        p = ROOT / "out" / v / "report.json"
        if p.exists():
            r_ = json.loads(p.read_text())
            r_["report_time"] = _utc(p)
            strip(v, "when it was designed", r_, f"out/{v}/report.json")
        strip(v, "today's checks", _load(inputs / f"verify_today_{v}.json"), f"showcase/data/inputs/verify_today_{v}.json")
    rep["report_time"] = F["report_time"]
    strip(name, "today's checks", rep, f"out/{name}/report.json")
    F["strips"] = strips
    F["warnings"] = [{"verifier": f["verifier"], "code": f["code"], "message": f["message"][:300]}
                     for f in rep["findings"] if f["severity"] == "warning"]
    # ---- bed support
    bed = []

    def bedrow(label, sub, bs, src):
        if not bs or not bs.get("print_weight"):
            return
        pw, hl = bs["print_weight"], bs["hand_load"]
        bed.append({"label": label, "sub": sub, "print": [pw.get("total_bonded_mm"), pw.get("total_screwed_mm")],
                    "hand": [hl.get("total_bonded_mm"), hl.get("total_screwed_mm")],
                    "tilt": pw.get("tilt_across_print_area_screwed_mm"), "limit": pw.get("limit_mm"), "source": src,
                    "constraint": (bs.get("constraint") or {}).get("note")})

    v7 = _load(inputs / "verify_today_printer_v7.json")
    v6 = _load(inputs / "verify_today_printer_v6.json")
    bedrow("v7", "one rear screw, back plate cantilevered on four blocks, 6 mm plate on silicone", (v7 or {}).get("bed_support"),
           "inputs/verify_today_printer_v7.json")
    for key, lab, sub in (("study_a", "Study (a)", "v7's cantilever, stiffened with steel gussets"),
                          ("study_b", "Study (b)", "two screws, a rail each side"),
                          ("study_c", "Study (c)", "three screws, two blocks per rail")):
        st = _load(inputs / f"{key}.json")
        bedrow(lab, sub, (st or {}).get("bed_support"), f"inputs/{key}.json")
    bedrow("v8 (d)", "three screws, one block per rail: chosen", m["fea"].get("bed_support"), f"out/{name}/report.json")
    F["bed"] = bed
    F["bed_limit"] = (m["fea"].get("bed_support") or {}).get("print_weight", {}).get("limit_mm")
    # ---- tolerance
    cl8 = m["tolerance"]["clearances"]
    F["clear"] = {
        "v8": {"examined": cl8["pairs_examined"], "closing": cl8["pairs_closing"], "threshold": cl8["threshold_mm"],
               "min_by_process": cl8["minimum_clearance_mm_by_process"], "search": cl8["search"],
               "pairs": sorted([{k: p.get(k) for k in ("parts", "gap_mm", "gap_sd_mm", "p_closed", "gap_mm_0p15_percentile",
                                                       "p_closed_normal_estimate", "severity", "processes")}
                                for p in cl8["pairs"]], key=lambda p: p["gap_mm"] - 3 * p["gap_sd_mm"])},
        "v7": ({"examined": v7["clearances"]["pairs_examined"], "closing": v7["clearances"]["pairs_closing"],
                "pairs": [p for p in v7["clearances"]["pairs"] if p.get("severity")],
                "probe_metal": [p for p in (v7.get("probe_metal_near") or []) if p.get("severity")]} if v7 else None),
    }
    tp = m["tolerance"]["printer"]
    hz = m["subsystems"]["homing"]
    ls = m["tolerance"]["lead_screws"]
    pr = m["tolerance"]["paired_rails"]
    adj_decl = {(a["kind"], a.get("joint")): a for a in m["tolerance"]["adjustments_declared"]}
    adj = [
        {"label": "Nozzle height (Z offset)", "how": "probe offset in the firmware, inside the declared Z over-travel",
         "need": tp["z_offset_needed_mm_99"], "have": tp["z_offset_available_mm"]},
        {"label": "Bed level", "how": "two nuts at the tab of each bed post, set once at assembly",
         "need": tp["levelling_needed_mm_99"], "have": tp["levelling_available_mm"]},
    ]
    for ax in ("x", "y"):
        w = (hz.get(ax) or {}).get("window_under_tolerance") or {}
        if w.get("adjustment_available_mm"):
            adj.append({"label": f"{ax.upper()} endstop position", "how": w.get("set_at_assembly", ""),
                        "need": w["adjustment_needed_mm_99"], "have": w["adjustment_available_mm"]})
    if ls:
        worst = max(ls.values(), key=lambda v: v["nut_misalignment_mm_99"])
        adj.append({"label": "Lead-screw nut off its screw's axis", "how": "floating nut in each nut block (worst of the three screws)",
                    "need": worst["nut_misalignment_mm_99"], "have": round(worst["float_available_mm"], 2)})
    for ax in ("y", "z"):
        a = adj_decl.get(("rail_align", ax))
        if a and ax in pr:
            adj.append({"label": f"{ax.upper()} rails parallel", "how": a["name"] + " (the maker allows " +
                        f"{pr[ax]['allowable_mm']} mm, so the pair must be aligned at assembly)",
                        "need": pr[ax]["parallelism_error_over_travel_mm_99"], "have": a["range_mm"]})
    F["adjust"] = adj
    F["adjust_versions"] = [
        {"label": lab, "z_need": (r_ or {}).get("tolerance_printer", {}).get("z_offset_needed_mm_99"),
         "z_have": (r_ or {}).get("tolerance_printer", {}).get("z_offset_available_mm"),
         "l_need": (r_ or {}).get("tolerance_printer", {}).get("levelling_needed_mm_99"),
         "l_have": (r_ or {}).get("tolerance_printer", {}).get("levelling_available_mm")}
        for lab, r_ in (("v6", v6), ("v7", v7)) if r_] + [
        {"label": "v8", "z_need": tp["z_offset_needed_mm_99"], "z_have": tp["z_offset_available_mm"],
         "l_need": tp["levelling_needed_mm_99"], "l_have": tp["levelling_available_mm"]}]
    F["tol_misc"] = {"as_built_first_layer": tp.get("p_first_layer_reachable_as_built"),
                     "as_built_level": tp.get("p_bed_level_within_half_a_layer_as_built"),
                     "bed_out_of_level_99": tp.get("bed_out_of_level_mm_99"), "belts": m["tolerance"]["belts"],
                     "monte_carlo": m["tolerance"]["monte_carlo"]}
    # ---- probe
    z8 = hz["z"]
    F["probe"] = {"v8": {k: z8.get(k) for k in ("x_offset", "y_offset", "unprobed_strip_mm", "edge_margin_mm", "print_area",
                                                "target", "sensing_distance_mm", "face_above_nozzle_mm", "z_offset_range_mm",
                                                "z_offset_range_unit_spread_mm")},
                  "v8_margin": z8.get("probe_to_nozzle_margin", {}).get("face_window_mm"),
                  "v8_metal_zone": (z8.get("mounting") or {}).get("metal_free_zone"),
                  "v7": (v7 or {}).get("probe")}
    tune = _load(out_dir / "tune" / "tuning.json") or {}
    F["tune"] = {"input_shaper": {ax: {k: (tune.get("input_shaper", {}).get(ax) or {}).get(k) for k in
                                       ("shaper_type", "shaper_freq", "predicted_resonance_hz", "suggested_max_accel",
                                        "remaining_vibrations_frac", "candidates")} for ax in ("x", "y")},
                 "selected_by": tune.get("input_shaper", {}).get("selected_by"),
                 "pressure_advance": (tune.get("pressure_advance") or {}).get("sweep", {}).get("best"),
                 "bed_mesh": {k: (tune.get("bed_mesh") or {}).get(k) for k in ("over_print_area", "bed_surface_assumed_mm")},
                 "mesh_points": ((tune.get("bed_mesh") or {}).get("mesh") or {}).get("points"),
                 "klipper_commit": (tune.get("klipper_commit") or "")[:7]}
    # ---- twin, every version that has a scored range
    twin = []
    for p in sorted((ROOT / "out").glob("printer_v*/scores.jsonl"), key=lambda q: int(re.sub(r"\D", "", q.parent.name) or 0)):
        full, fw = _last_score(p)
        if not full:
            continue
        r_ = full["ranges"]
        twin.append({"label": p.parent.name.replace("printer_", ""), "time": full.get("time"),
                     "res_x": r_["resonance_hz"]["x"], "res_y": r_["resonance_hz"]["y"],
                     "accel": r_.get("accel_owners_would_run_mm_s2"), "ceiling": r_.get("step_loss_ceiling_accel_mm_s2"),
                     "accel_klipper": ((fw or {}).get("klipper") or {}).get("accel_owners_would_run_range_mm_s2"),
                     "cross_rms": r_.get("cross_track_rms_mm")})
    F["twin"] = twin
    full, fw = _last_score(out_dir / "scores.jsonl")
    F["twin_notes"] = {"varied": (full or {}).get("ranges_varied"), "not_varied": (full or {}).get("ranges_not_varied"),
                       "accel_meaning": ((full or {}).get("headline") or {}).get("accel_owners_would_run_mm_s2", {}).get("meaning")}
    k = (fw or {}).get("klipper") or {}
    F["fw_sweep"] = {"on": (k.get("as_configured") or {}).get("table"), "off": (k.get("shaper_and_pressure_advance_off") or {}).get("table"),
                     "nominal_on": (k.get("as_configured") or {}).get("nominal"),
                     "nominal_off": (k.get("shaper_and_pressure_advance_off") or {}).get("nominal"),
                     "commit": (k.get("commit") or "")[:7], "speed_scale": k.get("speed_scale_in_sweep")}
    # ---- firmware in the loop print
    pr_dirs = sorted((out_dir / "fil").glob("*/*/print_report.json")) if (out_dir / "fil").exists() else []
    if pr_dirs:
        pp = json.loads(pr_dirs[0].read_text())
        F["print"] = {"dir": str(pr_dirs[0].parent.relative_to(ROOT)), "part": pp["part"], "size": pp["part_size_mm"],
                      "print": {k: pp["print"].get(k) for k in ("layers", "layer_height_mm", "filament_mass_g", "outline_iou_mean",
                                                                "outline_iou_min", "boundary_deviation_mm", "max_bulge_mm",
                                                                "layer_shift_mm_worst", "first_layer_gap_error_mm")},
                      "time_s": pp["plan"]["print_time_s"], "poses": pp.get("poses_checked_for_collision"),
                      "collisions": pp.get("machine_collisions"), "cross": {k: pp["dynamics"].get(k) for k in
                                                                            ("cross_track_rms_mm", "cross_track_worst_mm", "cross_track_p99_mm")},
                      "fw": {k: pp["firmware"].get(k) for k in ("firmware", "mcu", "peak_step_rate_hz", "mcu_step_rate_limit_hz",
                                                                "max_distance_from_gcode_path_mm", "klipper_messages")},
                      "commit": (pp["firmware"].get("commit") or "")[:7], "moves": pp["gcode"]["moves"],
                      "axis_mass_kg": pp["dynamics"].get("axis_mass_kg"),
                      "findings": [f["message"][:260] for f in pp.get("findings", [])]}
    # ---- known-good machine
    refp = ROOT / "out" / "ref_vminion" / "report.json"
    if refp.exists():
        rr = json.loads(refp.read_text())
        by: dict = {}
        for f in rr["findings"]:
            if f["severity"] == "error":
                c = REF_CLASS.get(f["code"], "new")
                by.setdefault(c, {}).setdefault(f["code"], 0)
                by[c][f["code"]] += 1
        F["ref"] = {"when": _utc(refp), "by_class": by, "total": sum(sum(v.values()) for v in by.values()),
                    "summary": _summary(rr), "warnings": sum(v["warnings"] for v in _summary(rr).values())}
        later = _load(inputs / "verify_today_ref_vminion.json")
        if later:
            by2: dict = {}
            for f in later["findings"]:
                if f["severity"] == "error":
                    c = REF_CLASS.get(f["code"], "new")
                    by2.setdefault(c, {}).setdefault(f["code"], 0)
                    by2[c][f["code"]] += 1
            F["ref"]["later"] = {"when": later["report_time"], "by_class": by2, "total": sum(sum(v.values()) for v in by2.values())}
    # ---- versions
    vers = []
    for p in sorted((ROOT / "out").glob("printer_v*/report.json"), key=lambda q: int(re.sub(r"\D", "", q.parent.name) or 0)):
        r_ = json.loads(p.read_text())
        mm = r_.get("metrics") or {}
        if not (mm.get("geometry") or {}).get("parts"):
            continue
        vers.append({"label": p.parent.name.replace("printer_", ""), "parts": mm["geometry"]["parts"],
                     "mass_kg": mm["geometry"].get("mass_kg"), "bom_usd": (mm.get("ratings") or {}).get("bom_cost_usd_estimate"),
                     "by_process": (mm.get("manufacture") or {}).get("by_process") or {},
                     "machining_usd": (mm.get("manufacture") or {}).get("machining_cost_estimate_usd_qty1")})
    F["versions"] = vers
    for f in rep["findings"]:
        mm_ = re.search(r"within 1 mm of plane in >= (\d+)\s*%", f.get("message", ""))
        if mm_:
            F["belt_req"] = int(mm_.group(1))
    doc = ROOT / "docs" / f"{name.upper()}.md"
    F["unverified"] = md_section_bullets(doc, "Still unverified") if doc.exists() else []
    F["unverified_source"] = f"docs/{doc.name}"
    return F


# ------------------------------------------------------------------------------------------- html helpers

def e(s) -> str:
    return html.escape(str(s), quote=True)


def num(v, d=2) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, (int,)) or (isinstance(v, float) and abs(v) >= 1000):
        return f"{v:,.0f}"
    return f"{v:.{d}f}"


def md_inline(s: str) -> str:
    s = e(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)


class Scale:
    def __init__(self, lo, hi, log=False):
        self.lo, self.hi, self.log = lo, hi, log

    def __call__(self, v) -> float:
        if self.log:
            t = (math.log10(max(v, self.lo)) - math.log10(self.lo)) / (math.log10(self.hi) - math.log10(self.lo))
        else:
            t = (v - self.lo) / (self.hi - self.lo)
        return round(100.0 * min(1.0, max(0.0, t)), 2)


def rowchart(rows, sc: Scale, ticks, *, refs=(), unit="", legend=(), label="", axis_title="", shade=None, wide_label=False, val_title="") -> str:
    """rows: [{label, sub, marks: [("range", a, b, cls) | ("dot", v, cls) | ("bar", v, cls) | ("tick", v, cls)], value, tip}]"""
    def track_bg():
        s = "".join(f'<span class="g" style="left:{sc(t)}%"></span>' for t in ticks)
        if shade:
            s += f'<span class="shade" style="left:{sc(shade[0])}%;width:{round(sc(shade[1]) - sc(shade[0]), 2)}%"></span>'
        s += "".join(f'<span class="ref {r[2] if len(r) > 2 else ""}" style="left:{sc(r[0])}%"></span>' for r in refs)
        return s

    h = [f'<div class="rc{" rc-wide" if wide_label else ""}" role="group" aria-label="{e(label)}">']
    if legend:
        h.append('<div class="legend">' + "".join(
            f'<span class="lg"><span class="sw {c} {shape}"></span>{e(t)}</span>' for t, c, shape in legend) + "</div>")
    ax = "".join(f'<span class="tk" style="left:{sc(t)}%">{e(lab)}</span>' for t, lab in
                 ((t, (f"{t:g}")) for t in ticks))
    refl = "".join(f'<span class="refl {r[2] if len(r) > 2 else ""}" style="left:{sc(r[0])}%">{e(r[1])}</span>' for r in refs if r[1])
    h.append(f'<div class="rc-row rc-axis" aria-hidden="true"><div class="rc-label"></div><div class="rc-track">{refl}</div><div class="rc-val">{e(val_title)}</div></div>')
    for r in rows:
        marks = []
        for mk in r["marks"]:
            if mk[0] == "range" and mk[1] is not None and mk[2] is not None:
                a, b = sorted((sc(mk[1]), sc(mk[2])))
                marks.append(f'<span class="m rg {mk[3]}" style="left:{a}%;width:{max(0.6, round(b - a, 2))}%"></span>')
            elif mk[0] == "dot" and mk[1] is not None:
                marks.append(f'<span class="m dot {mk[2]}" style="left:{sc(mk[1])}%"></span>')
            elif mk[0] == "bar" and mk[1] is not None:
                marks.append(f'<span class="m bar {mk[2]}" style="width:{sc(mk[1])}%"></span>')
            elif mk[0] == "tick" and mk[1] is not None:
                marks.append(f'<span class="m tick {mk[2]}" style="left:{sc(mk[1])}%"></span>')
        sub = f'<span class="sub">{e(r["sub"])}</span>' if r.get("sub") else ""
        cls = " " + r["cls"] if r.get("cls") else ""
        h.append(f'<div class="rc-row{cls}" tabindex="0" data-tip="{e(r.get("tip", ""))}"><div class="rc-label"><span class="nm">{e(r["label"])}</span>{sub}</div>'
                 f'<div class="rc-track">{track_bg()}{"".join(marks)}</div><div class="rc-val">{r.get("value", "")}</div></div>')
    h.append(f'<div class="rc-row rc-axis" aria-hidden="true"><div class="rc-label"></div><div class="rc-track">{ax}</div><div class="rc-val"></div></div>')
    if axis_title:
        h.append(f'<div class="rc-row rc-axis"><div class="rc-label"></div><div class="rc-track rc-title">{e(axis_title)}</div><div class="rc-val"></div></div>')
    h.append("</div>")
    return "".join(h)


def table(head, rows, cls="") -> str:
    th = "".join(f"<th>{e(x)}</th>" for x in head)
    tr = "".join("<tr>" + "".join(f"<td>{x}</td>" for x in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>'


def details(summary, body) -> str:
    return f'<details class="more"><summary>{e(summary)}</summary>{body}</details>'


def figure_render(F, key, title, caption, alt, extra_overlay="", cls="") -> str:
    v = (F["renders"].get("views") or {}).get(key)
    if not v:
        return ""
    w, h = v["size"]
    pins = "".join(f'<span class="pin" data-k="{key}-{i}" style="left:{c["x"] * 100:.2f}%;top:{c["y"] * 100:.2f}%">{i}</span>'
                   for i, c in enumerate(v["callouts"], 1))
    items = "".join(f'<li data-k="{key}-{i}"><span class="n">{i}</span><span>{e(c["label"])}</span></li>'
                    for i, c in enumerate(v["callouts"], 1))
    lst = f'<ol class="callouts">{items}</ol>' if items else ""
    scroll = " scrollx" if len(v["callouts"]) > 10 else ""
    return (f'<figure class="shot {cls}{" has-list" if items else ""}"><div class="stagewrap{scroll}"><div class="stage" style="aspect-ratio:{w}/{h}">'
            f'<img src="img/{e(v["file"])}" alt="{e(alt)}" width="{w}" height="{h}" loading="lazy">{pins}{extra_overlay}</div></div>'
            f'<div class="shot-text"><h3>{e(title)}</h3>{lst}<figcaption>{caption}</figcaption></div></figure>')


# ------------------------------------------------------------------------------------------- sections

def sec_header(F) -> str:
    H = F["headline"]
    mf = (F["renders"].get("model") or {})
    j = mf.get("joints") or {}
    travel = " x ".join(f"{(j[a][1] - j[a][0]):g}" for a in ("x", "y", "z") if a in j)
    pa = mf.get("print_area") or []
    bb = H["bbox_mm"]
    spec = [
        ("Print volume", f"{pa[0]:g} x {pa[1]:g} x {j['z'][1]:g} mm" if pa and "z" in j else "n/a", f"axis travel {travel} mm"),
        ("Overall size", f"{bb[0]:.0f} x {bb[1]:.0f} x {bb[2]:.0f} mm", "at the home pose"),
        ("Parts", f"{H['parts']}", f"{H['custom_parts']} made, {H['cots_parts']} bought"),
        ("Mass", f"{H['mass_kg']:.1f} kg", "model total"),
        ("Bought parts", f"${H['bom_usd']:,.0f}", "catalogue estimate"),
        ("Checks", f"{H['passed']} of {H['verifiers']} pass", f"{H['errors']} errors, {H['warnings']} warnings"),
    ]
    tiles = "".join(f'<div class="spec"><dt>{e(a)}</dt><dd>{e(b)}</dd><span>{e(c)}</span></div>' for a, b, c in spec)
    return f'''
<header class="top"><div class="wrap">
  <p class="eyebrow">Design study, checked in software</p>
  <h1>printer_v8</h1>
  <p class="lede">A 180 mm cube 3D printer drawn as code, then checked by twelve automated verifiers, a tolerance simulation of {H["builds"]:,} builds, finite-element load cases and real Klipper firmware planning its prints.</p>
  <div class="notice" role="note"><strong>Simulated. Never built.</strong> Every figure on this page is the output of a model, read from the verification files when the page was generated ({e(F["generated"])}; design report of {e(F["report_time"])}). Nothing here was measured on hardware. Where the models give a range, the range is shown.</div>
  <dl class="specs">{tiles}</dl>
  <nav class="toc" aria-label="Sections"><a href="#features">Key features</a><a href="#checks">Verification</a><a href="#bed">Bed support</a><a href="#tolerance">Tolerance</a><a href="#probe">Probe</a><a href="#twin">Dynamics</a><a href="#firmware">Firmware</a><a href="#wolf">Checking the checks</a><a href="#history">History</a><a href="#open">Unverified</a></nav>
</div></header>'''


def sec_features(F) -> str:
    R = F["renders"]
    cc, col, lab = R.get("class_counts", {}), R.get("class_color", {}), R.get("class_label", {})
    order = ["sheet", "printed", "machined", "extrusion", "purchased", "fastener"]
    total = sum(cc.values()) or 1
    seg = "".join(f'<span class="seg" style="flex:{cc.get(k, 0)} 1 0;background:{col[k]}" tabindex="0" data-tip="{e(lab[k])}: {cc.get(k, 0)} parts ({100 * cc.get(k, 0) / total:.0f}%)"></span>'
                  for k in order if cc.get(k))
    leg = "".join(f'<span class="lg"><span class="sw" style="background:{col[k]}"></span>{e(lab[k])} <b>{cc.get(k, 0)}</b></span>' for k in order if cc.get(k))
    mf = R.get("model") or {}
    po = mf.get("probe_offset_mm") or [0, 0]
    # dimension overlay on the side view, from points projected through the same camera as the picture
    side = (R.get("views") or {}).get("toolhead_side") or {}
    mk = side.get("marks") or {}
    ov = ""
    if {"nozzle", "probe", "bed_under_nozzle"} <= set(mk):
        nx, ny = mk["nozzle"]
        px, py = mk["probe"]
        by = mk["bed_under_nozzle"][1]
        dy = by + 0.085
        ov = (f'<svg class="dim" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">'
              f'<line x1="{nx * 100:.2f}" y1="{ny * 100:.2f}" x2="{nx * 100:.2f}" y2="{dy * 100 + 2:.2f}"/>'
              f'<line x1="{px * 100:.2f}" y1="{py * 100:.2f}" x2="{px * 100:.2f}" y2="{dy * 100 + 2:.2f}"/>'
              f'<line class="d" x1="{px * 100:.2f}" y1="{dy * 100:.2f}" x2="{nx * 100:.2f}" y2="{dy * 100:.2f}"/>'
              f'<line x1="{px * 100 - 9:.2f}" y1="{py * 100:.2f}" x2="{px * 100 - 1:.2f}" y2="{py * 100:.2f}"/>'
              f'<line x1="{px * 100 - 9:.2f}" y1="{ny * 100:.2f}" x2="{nx * 100 - 1:.2f}" y2="{ny * 100:.2f}"/>'
              f'<line class="d" x1="{px * 100 - 7:.2f}" y1="{py * 100:.2f}" x2="{px * 100 - 7:.2f}" y2="{ny * 100:.2f}"/></svg>'
              f'<span class="dimlab" style="left:{(nx + px) * 50:.2f}%;top:{dy * 100 + 1:.2f}%">probe axis {abs(po[1]):g} mm behind the nozzle</span>'
              f'<span class="dimlab left" style="left:{px * 100 - 8:.2f}%;top:{(py + ny) * 50:.2f}%">face {mf.get("probe_face_above_nozzle_mm", 0):.1f} mm above the tip</span>')
    P = F["probe"]["v8"]
    H = F["headline"]
    bp = H["by_process"]
    out = [f'''
<section id="features"><div class="wrap">
  <h2>Key features</h2>
  <p class="intro">These pictures are drawn from the design's own solid model, the same one the checks run on. Colour shows how each part is made. A numbered pin sits on the part it names: its position is found by drawing that part alone through the same camera, so a pin cannot land on something else.</p>
  <div class="proc" role="group" aria-label="Parts by how they are made">
    <div class="segbar">{seg}</div><div class="legend">{leg}</div>
  </div>''']
    out.append(figure_render(
        F, "hero", "The whole machine",
        f"A fixed 2020 extrusion frame. The gantry moves the toolhead in X and Y at the top; the bed rises on three lead screws. Bed shown {110} mm below the nozzle. "
        f"Of {H['parts']} parts, {H['custom_parts']} are made for this machine ({bp.get('sheet', 0)} laser-cut, {bp.get('printed', 0)} printed, {bp.get('machined', 0)} machined) and {H['cots_parts']} are bought.",
        "Three-quarter view of the printer: open aluminium frame, gantry on top, bed plate in the middle, electronics tray at the bottom"))
    out.append(figure_render(
        F, "bed_top", "Bed carrier and Z stage, plate removed",
        "The bed plate and frame are drawn as outlines so the carrier shows. Three screws stand at the rear centre and the two front corners, so the bed's weight sits inside the triangle they make. "
        "Each rear rail has one guide block: the rails hold the bed sideways and the screws set its tilt. The plate stands on four M5 screws that bend to let it grow when hot, and the rear tie keeps it from sliding.",
        "Bed carrier seen from above with the plate removed: back plate, two arms, front plate, four posts, three lead screws and the belt"))
    out.append(figure_render(
        F, "bed_low", "One motor, one closed belt, three screws",
        "A single motor turns all three screws through one closed belt, so they cannot fall out of step at power-up. Each screw stands in a pair of ball bearings and has no coupler; its top is free. "
        "What is given up: the firmware cannot re-level the bed by itself. Levelling is done once, by hand, on the post nuts.",
        "Low view of the Z drive: three lead screws on printed bearing pedestals joined by a belt to one motor at the rear"))
    out.append(figure_render(
        F, "toolhead", "Toolhead, seen from behind",
        f"The probe is an industrial M12 inductive sensor that reads the steel print sheet, so it measures the surface the nozzle prints on. "
        f"It sits in a closed hole and is clamped by its own two nuts. The smallest gap between toolhead parts that do not mate is {F['clear']['v8']['pairs'] and min(p['gap_mm'] for p in F['clear']['v8']['pairs']):.1f} mm as drawn; see the tolerance section for what that becomes when built.",
        "Rear view of the toolhead: extruder, hotend with nozzle, cylindrical probe in a printed mount, part fan, above the print sheet"))
    out.append(figure_render(
        F, "toolhead_side", "Probe and nozzle in profile",
        f"Side elevation without perspective, bed lowered 8 mm. The probe's sensing face is {mf.get('probe_face_above_nozzle_mm', 0):.1f} mm above the nozzle tip and it switches with the nozzle {P['z_offset_range_mm'][0]:g} to {P['z_offset_range_mm'][1]:g} mm above the sheet across unit spread and temperature. "
        f"The Y axis travels {abs(po[1]):g} mm further than the print area so the probe can reach every point the nozzle prints.",
        "Side elevation of the toolhead showing the probe behind the nozzle with dimension lines", extra_overlay=ov, cls="narrow"))
    out.append(figure_render(
        F, "gantry", "Gantry",
        f"The X beam hangs under two laser-cut steel Y plates, each on one guide block. Both Y belts are {mf.get('belts', {}).get('y_belt', 0):g} mm wide and each has its own motor; the two motors share one driver. "
        "Every belt has a screw tensioner. The X endstop hangs under the left Y plate (hidden here) and its screws run in slots.",
        "Gantry from above: two Y rails on the top frame rails, X beam between two blue sheet-metal plates, three motors, belts"))
    out.append(figure_render(
        F, "gantry_corner", "Y drive and endstop, rear right corner",
        "The motor mount is 2 mm sheet and the pulley is fitted hub-outboard, which puts the belt close to the motor's face and keeps the sideways load on the shaft inside its limit. "
        "The Y endstop's mount slides along the rail, so the switch is set at assembly instead of relying on drawn dimensions.",
        "Close view of the rear right corner: Y motor on a sheet mount, pulley and belt, endstop switch on a sliding mount", cls="narrow"))
    out.append(figure_render(
        F, "electronics", "Electronics tray",
        "Everything electrical is on one laser-cut tray under the bed. Mains enters through a fused, switched inlet; a relay that the controller holds closed feeds the supply, so the firmware can drop mains to the heaters. "
        "The checks trace every wire, connector and terminal on this tray; wires are not drawn in these pictures.",
        "Electronics tray from above: power supply, control board, relay board, host computer, mains inlet on a small panel"))
    out.append(figure_render(
        F, "exploded", "Pulled apart by sub-assembly",
        "The four groups are moved apart for the picture only. Part counts are from the model.",
        "Exploded view: gantry lifted above the frame, bed and Z stage pulled out to the left, electronics tray dropped below"))
    out.append('<p class="aside" id="inspector-link">An interactive 3D inspector of this model exists as a separate page.</p></div></section>')
    return "".join(out)


def badge(v) -> str:
    if v["status"] == "pass":
        cls, ic = ("ok", "&#10003;") if not v["warnings"] else ("warn", "&#10003;")
    elif v["status"] == "fail":
        cls, ic = "bad", "&#10007;"
    else:
        cls, ic = "na", "&#8211;"
    txt = f'{v["errors"]}E' if v["errors"] else (f'{v["warnings"]}W' if v["warnings"] else "")
    full = f'{v["status"]}: {v["errors"]} errors, {v["warnings"]} warnings'
    return f'<span class="bd {cls}" title="{e(full)}"><span class="ic" aria-hidden="true">{ic}</span>{txt}<span class="vh">{e(full)}</span></span>'


def sec_checks(F) -> str:
    head = "<th>Design, checks</th>" + "".join(f'<th><span class="rot">{e(v)}</span></th>' for v in VERIFIERS) + "<th>Total</th>"
    rows = []
    for s in F["strips"]:
        cells = "".join(f"<td>{badge(s['summary'].get(v, {'status': 'not run', 'errors': 0, 'warnings': 0}))}</td>" for v in VERIFIERS)
        cur = " cur" if s["label"] == F["design"] else ""
        rows.append(f'<tr class="{"today" if "today" in s["basis"] else "then"}{cur}"><th scope="row"><b>{e(s["label"].replace("printer_", ""))}</b> <span>{e(s["basis"])}</span><small>{e(s["when"] or "")}</small></th>{cells}'
                    f'<td class="tot">{s["errors"]} errors<br>{s["warnings"]} warnings</td></tr>')
    strip = f'<div class="tw"><table class="strip"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
    key = ('<div class="legend"><span class="lg"><span class="bd ok"><span class="ic">&#10003;</span></span>pass</span>'
           '<span class="lg"><span class="bd warn"><span class="ic">&#10003;</span>3W</span>pass with warnings</span>'
           '<span class="lg"><span class="bd bad"><span class="ic">&#10007;</span>5E</span>fail, with error count</span></div>')
    errs = []
    for s in F["strips"]:
        if "today" in s["basis"] and s["error_findings"]:
            li = "".join(f'<li><code>{e(f["verifier"])}.{e(f["code"])}</code> {e(f["message"])}</li>' for f in s["error_findings"])
            errs.append(details(f'{s["label"]} under today\'s checks: the {len(s["error_findings"])} errors', f"<ul class='finds'>{li}</ul>"))
    warn = "".join(f'<li><code>{e(w["verifier"])}.{e(w["code"])}</code> {e(w["message"])}</li>' for w in F["warnings"])
    what = "".join(f"<li><b>{e(k)}</b> {e(v)}</li>" for k, v in VERIFIER_WHAT.items())
    H = F["headline"]
    vs = H.get("verify_seconds")
    t6 = next((s for s in F["strips"] if s["label"] == "printer_v6" and "today" in s["basis"]), None)
    t7 = next((s for s in F["strips"] if s["label"] == "printer_v7" and "today" in s["basis"]), None)
    told = []
    for s in (t6, t7):
        if s:
            told.append(f"{s['label'].replace('printer_', '')} now has {s['errors']} error{'s' if s['errors'] != 1 else ''}")
    return f'''
<section id="checks"><div class="wrap">
  <h2>Verification</h2>
  <p class="intro">A design is a Python file. One command builds its model and runs twelve verifiers over it{f" (about {vs / 60:.0f} minutes for this design)" if vs else ""}. v8 passes all twelve with {H["errors"]} errors and {H["warnings"]} warnings. That result needs context, because the checks themselves kept changing.</p>
  <h3>Twelve verifiers, three designs, and what tightening the checks exposed</h3>
  {key}{strip}
  <p class="cap"><b>What was checked.</b> Each row is one full run of all twelve verifiers. v6 and v7 each passed with no errors on the day they were designed. They were re-run for this page against the checks as they stand now, without changing the designs. <b>What it means.</b> {"; ".join(told) + ". " if told else ""}The designs did not get worse: the checks got stricter (gaps are now tested as built, not as drawn; vendor data sheets corrected the catalogue). A pass is a statement about the checks of that day. <b>Assumed.</b> The checks changed again while this page was being made, so these counts can move.</p>
  {"".join(errs)}
  {details(f"v8: every one of the {len(F['warnings'])} warnings", f"<ul class='finds'>{warn}</ul><p class='cap'>docs/PRINTER_V8.md explains each warning and argues that two of them (the bed judged as a cantilever, level change over travel) come from formulas that ignore the lead screws.</p>")}
  {details("What each verifier looks at", f"<ul class='finds two'>{what}</ul>")}
</div></section>'''


def sec_bed(F) -> str:
    rows, tb = [], []
    lim = F.get("bed_limit")
    sc = Scale(0.002, 0.3, log=True)
    for b in F["bed"]:
        cur = "cur" if b["label"].startswith("v8") else ""
        rows.append({"label": b["label"], "sub": b["sub"], "cls": cur,
                     "marks": [("range", b["print"][0], b["print"][1], "s1"), ("dot", b["print"][0], "s1 hollow"), ("dot", b["print"][1], "s1"),
                               ("range", b["hand"][0], b["hand"][1], "s2"), ("dot", b["hand"][0], "s2 hollow"), ("dot", b["hand"][1], "s2")],
                     "value": f'<b>{b["print"][1]:.3f}</b> mm',
                     "tip": f'{b["label"]}: 1 kg print {b["print"][0]:.3f} to {b["print"][1]:.3f} mm; 20 N push {b["hand"][0]:.3f} to {b["hand"][1]:.3f} mm (bonded to screw-only)'})
        tb.append([e(b["label"]), e(b["sub"]), f'{b["print"][0]:.4f}', f'{b["print"][1]:.4f}', f'{b["hand"][0]:.4f}', f'{b["hand"][1]:.4f}',
                   num(b["tilt"], 3), e(b["source"])])
    chart = rowchart(rows, sc, [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2], refs=[(lim, f"{lim:g} mm guide", "limit")] if lim else [],
                     legend=[("1 kg print", "s1", "dot"), ("20 N hand push", "s2", "dot"), ("screw-only joints (soft bound)", "ink", "dot"),
                             ("bonded joints (stiff bound)", "ink hollow", "dot")],
                     label="Bed deflection at the worst print corner", val_title="1 kg, screw-only", axis_title="deflection at the worst print corner, mm (log scale)")
    v7 = next((b for b in F["bed"] if b["label"] == "v7"), None)
    v8 = next((b for b in F["bed"] if b["label"].startswith("v8")), None)
    ratio = f"{v7['print'][1] / v8['print'][1]:.0f}" if v7 and v8 else "n/a"
    lh = ((F.get("print") or {}).get("print") or {}).get("layer_height_mm") or 0.2
    over = f"{v7['print'][1] / lim:.1f}" if v7 and lim else "n/a"
    fea = ""
    ff = F.get("fea_fields")
    if ff and ff.get("designs"):
        cards = []
        for nm, d in ff["designs"].items():
            pw = d.get("print_weight") or {}
            cards.append(f'<figure class="feac"><div class="stage"><img src="img/{e(d["file"])}" alt="Deflected shape of the bed carrier of {e(nm)}, coloured by vertical sag" loading="lazy"></div>'
                         f'<figcaption><b>{e(nm.replace("printer_", ""))}</b> largest sag in the field {d["field_max_sag_screwed_mm"]:.3f} mm '
                         f'(the verifier adds {num(pw.get("support_compliance_mm"), 4)} mm for guide blocks and nuts and reports {num(pw.get("total_screwed_mm"), 4)} mm at the load point). {d["nodes"]:,} nodes, {d["parts"]} parts.</figcaption></figure>')
        grad = ",".join(ff["ramp"])
        fea = (f'<h3>The same load on both beds, one colour scale</h3><div class="feagrid">{"".join(cards)}</div>'
               f'<div class="cbar" aria-hidden="true"><span>0</span><span class="bar" style="background:linear-gradient(90deg,{grad})"></span><span>{ff["colour_max_mm"]:.3f} mm down</span></div>'
               f'<p class="cap"><b>What was checked.</b> The verifier\'s own finite-element case, run again with the displacement field kept: the bed plate and everything that carries it as one meshed body, held sideways at the guide blocks and vertically at the nut seats, with a 1 kg print at the worst corner of the print area. Joints are held only round their screws (the soft bound). '
               f'<b>What it means.</b> Shapes are exaggerated {ff["exaggeration"]:.0f} times, equally for both. v7\'s plate tips forward off its rear support; v8\'s barely moves. '
               f'<b>Assumed.</b> Linear elastic parts, no gaps or friction in joints, nut and bearing stiffness taken from assumed figures (10 N/um thread contact). The grey box is the undeformed outline.</p>')
    return f'''
<section id="bed"><div class="wrap">
  <h2>Bed support</h2>
  <p class="intro">v7 held its bed from the back, like a shelf. Today's checks measure how far the printing surface drops when a heavy print sits on its worst corner. v7 dropped {v7["print"][1]:.3f} mm under 1 kg, which is {100 * v7["print"][1] / lh:.0f}% of a {lh:g} mm layer, so v8 began with a trade study of four ways to hold the bed.</p>
  <h3>How far the bed drops: v7, three study variants and v8</h3>
  {chart}
  <p class="cap"><b>What was checked.</b> Deflection of the print surface at the worst corner of the 180 mm print area under a 1 kg print and under a 20 N push of a hand. Each bar spans two models of the same joints: every touching face bonded (stiff) and joints held only round their screws (soft). The truth should lie between. <b>What it means.</b> Against the {lim:g} mm guide ({100 * lim / lh:.0f}% of a layer, applied to the 1 kg case on the soft bound) v7 is {over} times over and v8 has room: about {ratio} times less sag than v7. Variants (b) and (c) are stiffer still but were rejected because a small height difference between screws loads their nuts until one lifts. <b>Assumed.</b> The variants are trade-study models, not finished machines; the guide is the harness's own, not a standard.</p>
  {details("Table of these values", table(["Design", "Layout", "1 kg bonded, mm", "1 kg screw-only, mm", "20 N bonded, mm", "20 N screw-only, mm", "Tilt across print area under 1 kg, mm", "Source"], tb))}
  {fea}
</div></section>'''


def sec_tolerance(F) -> str:
    C = F["clear"]
    sc = Scale(-1.0, 2.0)
    rows, tb = [], []

    def add(p, ver, cur=""):
        a, sd = p["gap_mm"], p["gap_sd_mm"]
        pc = p.get("p_closed") or 0.0
        val = (f'<b>{100 * pc:.1f}%</b> close' if pc >= 0.0005 else "0 of 3,000")
        rows.append({"label": f'{ver}  {p["parts"][0]} / {p["parts"][1]}', "sub": f'drawn {a:.2f} mm, spread {sd:.2f} mm (1 SD)', "cls": cur,
                     "marks": [("range", a - 3 * sd, a + 3 * sd, "s2" if ver == "v7" else "s1"), ("dot", a, "s2" if ver == "v7" else "s1")],
                     "value": val, "tip": f'{p["parts"][0]} to {p["parts"][1]}: drawn {a:.2f} mm, 1 SD {sd:.3f} mm, 0.15th percentile {p.get("gap_mm_0p15_percentile")} mm, closed in {100 * pc:.2f}% of builds'})
        tb.append([ver, e(" / ".join(p["parts"])), f"{a:.3f}", f"{sd:.3f}", num(p.get("gap_mm_0p15_percentile"), 3), f"{100 * pc:.2f}%", e(p.get("severity") or "none")])

    if C["v7"]:
        for p in sorted(C["v7"]["pairs"], key=lambda p: -(p.get("p_closed") or 0)):
            add(p, "v7")
    n8 = 8
    for p in C["v8"]["pairs"][:n8]:
        add(p, "v8", "cur")
    chart = rowchart(rows, sc, [-1.0, -0.5, 0, 0.5, 1.0, 1.5, 2.0], refs=[(0, "parts touch", "limit")], shade=(-1.0, 0),
                     legend=[("v7, gaps flagged today", "s2", "dot"), (f"v8, the {n8} gaps with the least margin", "s1", "dot")],
                     label="Clearances as built", val_title="builds in which it closes", axis_title="gap as built, mm: dot = as drawn, bar = 3 standard deviations either side", wide_label=True)
    v7txt = ""
    if C["v7"]:
        worst = max(C["v7"]["pairs"], key=lambda p: p.get("p_closed") or 0)
        pm = (C["v7"].get("probe_metal") or [None])[0]
        v7txt = (f"In v7 the worst gap, {worst['parts'][0]} to {worst['parts'][1]}, was drawn at {worst['gap_mm']:.2f} mm and closes in {100 * worst['p_closed']:.1f}% of simulated builds; "
                 f"{C['v7']['closing']['error']} gaps are errors and {C['v7']['closing']['warning']} are warnings."
                 + (f" Separately, v7's probe had the {pm['part']} drawn {pm['gap_mm']:.2f} mm outside its metal-free zone, and inside it in {100 * pm['p_closed']:.1f}% of builds." if pm else ""))
    s8 = C["v8"]["search"]
    # adjustments
    arows, atb = [], []
    amax = max(a["have"] for a in F["adjust"])
    asc = Scale(0, 100)
    for a in F["adjust"]:
        used = 100 * a["need"] / a["have"]
        arows.append({"label": a["label"], "sub": a["how"], "marks": [("bar", used, "s1" if used < 85 else "s2"), ("tick", 100, "ink")],
                      "value": f'<b>{a["need"]:.2f}</b> of {a["have"]:g} mm', "cls": "thin" if used >= 85 else "",
                      "tip": f'{a["label"]}: {a["need"]:.2f} mm needed in the worst 1% of builds, {a["have"]:g} mm provided ({used:.0f}% used)'})
        atb.append([e(a["label"]), f'{a["need"]:.2f}', f'{a["have"]:g}', f"{used:.0f}%", e(a["how"])])
    achart = rowchart(arows, asc, [0, 25, 50, 75, 100], legend=[("needed (99th percentile of builds), as a share of what is provided", "s1", "barsw"),
                                                                 ("85% or more of the range used", "s2", "barsw")],
                      label="Adjustment needed against adjustment provided", val_title="needed of provided", axis_title="share of the provided adjustment that the worst 1% of builds needs, %", wide_label=True)
    av = F["adjust_versions"]
    avt = table(["Design", "Z offset needed (99%), mm", "provided, mm", "Bed level needed (99%), mm", "provided, mm"],
                [[e(a["label"]), num(a["z_need"]), num(a["z_have"]), num(a["l_need"]), num(a["l_have"])] for a in av])
    tm = F["tol_misc"]
    yb = tm["belts"].get("y_belt", {})
    return f'''
<section id="tolerance"><div class="wrap">
  <h2>Tolerance: 3,000 simulated builds</h2>
  <p class="intro">Parts are never made exactly as drawn. The tolerance verifier builds the machine {F["headline"]["builds"]:,} times, each time drawing every hole position, thickness and fit from the spread its process usually gives, and asks what still works.</p>
  <h3>Gaps that can close</h3>
  {chart}
  <p class="cap"><b>What was checked.</b> For v8 the verifier measured {s8["measured_exactly"]} near pairs exactly out of {s8["pairs"]:,} part pairs, set aside designed contacts, and simulated the {C["v8"]["examined"]} pairs drawn closer than {C["v8"]["threshold"]:g} mm. <b>What it means.</b> {v7txt} In v8 no examined gap closed in any build, and the smallest drawn gap is {min(p["gap_mm"] for p in C["v8"]["pairs"]):.2f} mm. <b>Assumed.</b> The per-process spreads are typical values that the harness itself calls a little pessimistic. Only the standard deviation and a low percentile of each gap are saved, so the bars are three standard deviations, not the simulated histogram.</p>
  {details("Table of these gaps", table(["Design", "Pair", "Drawn, mm", "1 SD, mm", "0.15th percentile, mm", "Closed in", "Finding"], tb))}
  <h3>Is there enough adjustment?</h3>
  {achart}
  <p class="cap"><b>What was checked.</b> Where the as-built machine cannot be right by dimensions alone, the design declares an adjustment and the verifier compares its range with what the worst 1% of builds need. <b>What it means.</b> Without adjustment only {100 * (tm["as_built_first_layer"] or 0):.0f}% of builds could print a first layer and {100 * (tm["as_built_level"] or 0):.1f}% would be level within half a layer, so the adjustments are not optional. All have enough range; the Y rail pair and the lead-screw nut float use most of theirs. Both Y belts stay within 1 mm of their plane in {100 * yb.get("p_within_1mm", 0):.1f}% of builds (standard error {100 * yb.get("p_within_1mm_standard_error", 0):.2f}%) against the design's own requirement{f" of {F['belt_req']}%" if F.get("belt_req") else ""}. <b>Assumed.</b> That whoever builds it makes each adjustment correctly.</p>
  {details("Table of adjustments, and Z offset and bed level for v6, v7 and v8", table(["Adjustment", "Needed (99%), mm", "Provided, mm", "Used", "How"], atb) + avt)}
</div></section>'''


def probe_svg(p, title) -> str:
    """Print area to scale with the strips the probe cannot reach. 1 unit = 1 mm; y is drawn upwards (rear at top)."""
    (x0, x1), (y0, y1) = p["print_area"]
    w, h = x1 - x0, y1 - y0
    u = p["unprobed_strip_mm"]
    ox, oy = p["x_offset"], p["y_offset"]
    pad = 26
    W, Hh = w + 2 * pad, h + 2 * pad
    rx, ry = pad + u["x_low"], pad + u["y_high"]
    rw, rh = w - u["x_low"] - u["x_high"], h - u["y_low"] - u["y_high"]
    # nozzle drawn at the print-area corner where the probe overhang is worst
    nx = pad + (w if ox < 0 else 0 if ox > 0 else w * 0.5)
    ny = pad + (h if oy > 0 else 0 if oy < 0 else h * 0.5)   # screen y: front (low y) at the bottom
    px, py = nx + ox, ny - oy
    full = all(abs(v) < 1e-6 for v in u.values())
    s = [f'<svg viewBox="0 0 {W:g} {Hh:g}" role="img" aria-label="{e(title)}">',
         f'<rect class="pa" x="{pad}" y="{pad}" width="{w:g}" height="{h:g}"/>',
         f'<rect class="hatch" x="{pad}" y="{pad}" width="{w:g}" height="{h:g}"/>' if not full else "",
         f'<rect class="ok" x="{rx:g}" y="{ry:g}" width="{rw:g}" height="{rh:g}"/>',
         f'<line class="off" x1="{nx:g}" y1="{ny:g}" x2="{px:g}" y2="{py:g}"/>',
         f'<circle class="pr" cx="{px:g}" cy="{py:g}" r="6"/>', f'<circle class="nz" cx="{nx:g}" cy="{ny:g}" r="3.2"/>',
         "</svg>"]
    return "".join(s)


def sec_probe(F) -> str:
    P = F["probe"]
    cards = []
    for lab, p in (("v7", P.get("v7")), ("v8", P.get("v8"))):
        if not p or not p.get("print_area"):
            continue
        (x0, x1), (y0, y1) = p["print_area"]
        u = p["unprobed_strip_mm"]
        rw, rh = (x1 - x0) - u["x_low"] - u["x_high"], (y1 - y0) - u["y_low"] - u["y_high"]
        pct = 100 * rw * rh / ((x1 - x0) * (y1 - y0))
        strips = ", ".join(f"{round(v, 1):g} mm" for v in sorted(u.values(), reverse=True) if v > 1e-6) or "none"
        cards.append(f'<figure class="pm"><div class="pmsvg">{probe_svg(p, f"{lab} probe coverage")}</div>'
                     f'<figcaption><b>{lab}</b> probes {round(rw, 1):g} x {round(rh, 1):g} mm of {x1 - x0:g} x {y1 - y0:g} mm ({pct:.0f}%). Probe {(f"{abs(p['x_offset']):g} mm to the side and " if abs(p["x_offset"]) > 1e-6 else "straight behind the nozzle, ")}{round(abs(p["y_offset"]), 1):g} mm back, kept {p["edge_margin_mm"]:g} mm inside the plate edge. Unprobed strips: {strips}.</figcaption></figure>')
    t = F["tune"]
    bm = (t.get("bed_mesh") or {}).get("over_print_area") or {}
    asm = (t.get("bed_mesh") or {}).get("bed_surface_assumed_mm") or {}
    mesh_txt = ""
    if bm:
        mesh_txt = (f' On a bed assumed tilted {asm.get("tilt_x_mm")} and {asm.get("tilt_y_mm")} mm and bowed {asm.get("bow_mm")} mm, the first-layer gap error over the print area is '
                    f'{bm["without_mesh_mm"]["rms"]:.3f} mm RMS ({bm["without_mesh_mm"]["worst"]:.3f} worst) without the mesh and {bm["with_mesh_mm"]["rms"]:.3f} mm RMS ({bm["with_mesh_mm"]["worst"]:.3f} worst) with it, using Klipper\'s own mesh interpolation.')
    v8 = P["v8"]
    return f'''
<section id="probe"><div class="wrap">
  <h2>Probe coverage</h2>
  <p class="intro">The probe measures the bed's height so the firmware can follow its shape. It can only measure where it can reach, and it is not where the nozzle is.</p>
  <div class="pmgrid">{"".join(cards)}</div>
  <div class="legend"><span class="lg"><span class="sw okfill"></span>probed</span><span class="lg"><span class="sw hatchfill"></span>inside the print area, never probed</span><span class="lg"><span class="sw nzdot"></span>nozzle at the corner</span><span class="lg"><span class="sw prdot"></span>probe at that moment</span></div>
  <p class="cap"><b>What was checked.</b> The subsystems verifier works out where the probe can stand over the plate from its offset, the axis travel and the margin its sensing field needs from the plate edge. Both drawings are the same scale, front of the machine at the bottom. <b>What it means.</b> v7 left strips at the right and front that were never measured; the firmware holds the nearest measured value there. v8 puts the probe straight behind the nozzle and gives Y the extra travel, so the whole print area is measured.{mesh_txt} <b>Assumed.</b> That a thin spring-steel sheet on a magnet switches the sensor at the {v8["sensing_distance_mm"]:g} mm its data sheet gives for an iron target. That is the first thing to test on a bench.</p>
</div></section>'''


def sec_twin(F) -> str:
    tw = F["twin"]
    lo = min(min(t["res_x"][0], t["res_y"][0]) for t in tw)
    hi = max(max(t["res_x"][2], t["res_y"][2]) for t in tw)
    sc = Scale(10 * math.floor(lo / 10) - 0, 10 * math.ceil(hi / 10))
    rows, tb = [], []
    for t in tw:
        cur = "cur" if t["label"] == F["design"].replace("printer_", "") else ""
        rows.append({"label": t["label"], "cls": cur,
                     "marks": [("range", t["res_x"][0], t["res_x"][2], "s1"), ("dot", t["res_x"][1], "s1"),
                               ("range", t["res_y"][0], t["res_y"][2], "s2 lowrow"), ("dot", t["res_y"][1], "s2 lowrow")],
                     "value": f'X <b>{t["res_x"][1]:.0f}</b> Y <b>{t["res_y"][1]:.0f}</b> Hz',
                     "tip": f'{t["label"]}: X {t["res_x"][0]} to {t["res_x"][2]} Hz (expected {t["res_x"][1]}); Y {t["res_y"][0]} to {t["res_y"][2]} Hz (expected {t["res_y"][1]})'})
        tb.append([e(t["label"]), " / ".join(f"{v:g}" for v in t["res_x"]), " / ".join(f"{v:g}" for v in t["res_y"]),
                   " / ".join(f"{v:,.0f}" for v in t["accel"]), " / ".join(f"{v:,.0f}" for v in (t["accel_klipper"] or [])) or "n/a",
                   " / ".join(f"{v:,.0f}" for v in (t["ceiling"] or [])), e(t["time"] or "")])
    ticks = list(range(int(sc.lo), int(sc.hi) + 1, 10))
    c1 = rowchart(rows, sc, ticks, legend=[("X axis (toolhead on the beam)", "s1", "dot"), ("Y axis (whole gantry)", "s2", "dot")],
                  label="Predicted resonance by version", axis_title="frequency each axis rings at, Hz: dot = expected, bar = low to high")
    amax = max(t["accel"][2] for t in tw)
    sa = Scale(0, 1000 * math.ceil(amax / 1000))
    arows = []
    for t in tw:
        cur = "cur" if t["label"] == F["design"].replace("printer_", "") else ""
        mk = [("range", t["accel"][0], t["accel"][2], "s1"), ("dot", t["accel"][1], "s1")]
        if t["accel_klipper"]:
            mk += [("range", t["accel_klipper"][0], t["accel_klipper"][2], "s3 lowrow"), ("dot", t["accel_klipper"][1], "s3 lowrow")]
        arows.append({"label": t["label"], "cls": cur, "marks": mk, "value": f'<b>{t["accel"][1]:,.0f}</b> mm/s²',
                      "tip": f'{t["label"]}: {t["accel"][0]:,.0f} to {t["accel"][2]:,.0f} mm/s² (expected {t["accel"][1]:,.0f})' +
                             (f'; from Klipper\'s own shaper choice {t["accel_klipper"][0]:,.0f} to {t["accel_klipper"][2]:,.0f} (expected {t["accel_klipper"][1]:,.0f})' if t["accel_klipper"] else "")})
    c2 = rowchart(arows, sa, list(range(0, int(sa.hi) + 1, 2000)),
                  legend=[("from the twin's resonance and a smoothing rule", "s1", "dot"), ("from the shapers Klipper's own code picked", "s3", "dot")],
                  label="Acceleration an owner would run", axis_title="acceleration an owner would likely run with input shaping, mm/s²")
    sh = F["tune"]["input_shaper"]
    shrows = []
    for ax in ("x", "y"):
        s = sh.get(ax) or {}
        if not s.get("shaper_type"):
            continue
        cand = ", ".join(f'{c["shaper_type"].upper()} {c["shaper_freq"]:g} Hz' for c in (s.get("candidates") or []))
        shrows.append([ax.upper(), f'<b>{e(s["shaper_type"].upper())}</b> at {s["shaper_freq"]:g} Hz', f'{s["predicted_resonance_hz"]:g} Hz',
                       f'{100 * s["remaining_vibrations_frac"]:.1f}%', f'{s["suggested_max_accel"]:,.0f} mm/s²', e(cand)])
    v8 = next((t for t in tw if t["label"] == F["design"].replace("printer_", "")), tw[-1])
    v6 = next((t for t in tw if t["label"] == "v6"), None)
    cmp6 = (f"v8's Y range ({v8['res_y'][0]:g} to {v8['res_y'][2]:g} Hz) and v6's ({v6['res_y'][0]:g} to {v6['res_y'][2]:g} Hz) overlap almost entirely, so the model cannot tell them apart. The brief asked v8 to beat v6 on speed; it does not." if v6 else "")
    n = F["twin_notes"]
    return f'''
<section id="twin"><div class="wrap">
  <h2>Dynamics: how fast could it print?</h2>
  <p class="intro">A dynamic model of the machine (belts as springs, the frame's stiffness from FEA, motors with their torque curves) predicts where each axis resonates. Resonance sets how hard the machine can accelerate before prints show ringing.</p>
  <h3>Predicted resonance, v4 to v8</h3>
  {c1}
  <h3>Acceleration an owner would run</h3>
  {c2}
  <p class="cap"><b>What was checked.</b> Each design's latest scorecard, with a low, expected and high value from running the model at both ends of its fitted parameter ranges ({e(n.get("varied") or "")}). <b>What it means.</b> The ranges are wide and overlap. {cmp6} v8 is clearly ahead of v7 only at the expected value. <b>Assumed.</b> Not varied, for lack of data: {e(n.get("not_varied") or "")}. The acceleration figure is half (0.4 to 0.65) of a Klipper smoothing rule, a ratio taken from three real machines.</p>
  <h3>Input shaper chosen by Klipper's own code</h3>
  {table(["Axis", "Chosen shaper", "Predicted resonance", "Vibration left", "Klipper's suggested max accel", "Candidates it weighed"], shrows)}
  <p class="cap">{e(F["tune"].get("selected_by") or "")}. The frequency response is synthetic: on a real machine an accelerometer run replaces it.</p>
  {details("Table of resonance and acceleration ranges (low / expected / high)", table(["Design", "X resonance, Hz", "Y resonance, Hz", "Owner acceleration, mm/s²", "Same from Klipper's shapers", "Step-loss ceiling, mm/s²", "Scored"], tb))}
</div></section>'''


def sec_firmware(F) -> str:
    P = F.get("print")
    if not P:
        return ""
    pr = P["print"]
    media = F.get("media", {})
    vid = (f'<video controls loop muted playsinline preload="metadata" poster="img/{e(media["poster"])}" aria-label="Animation of the simulated print growing layer by layer"><source src="img/{e(media["video"])}" type="video/mp4"></video>'
           if media.get("video") else (f'<img src="img/{e(media["poster"])}" alt="Simulated print" loading="lazy">' if media.get("poster") else ""))
    stats = [
        ("Layers", f'{pr["layers"]}', f'{pr["layer_height_mm"]:g} mm each'),
        ("Print time", f'{P["time_s"] / 60:.0f} min', f'{P["moves"]:,} G-code moves'),
        ("Outline match", f'{100 * pr["outline_iou_mean"]:.1f}%', f'worst layer {100 * pr["outline_iou_min"]:.1f}%'),
        ("Edge deviation", f'{pr["boundary_deviation_mm"]["mean"]:.3f} mm', f'worst {pr["boundary_deviation_mm"]["worst"]:.3f} mm'),
        ("Path error", f'{P["cross"]["cross_track_rms_mm"]:.4f} mm RMS', f'worst {P["cross"]["cross_track_worst_mm"]:.3f} mm'),
        ("Collisions", f'{P["collisions"]}', f'in {P["poses"]:,} poses checked'),
    ]
    tiles = "".join(f'<div class="spec"><dt>{e(a)}</dt><dd>{e(b)}</dd><span>{e(c)}</span></div>' for a, b, c in stats)
    sw = F["fw_sweep"]
    sweep = ""
    if sw.get("on") and sw.get("off"):
        accs = sorted({r["accel_mm_s2"] for r in sw["on"]} | {r["accel_mm_s2"] for r in sw["off"]})
        on = {r["accel_mm_s2"]: r for r in sw["on"]}
        off = {r["accel_mm_s2"]: r for r in sw["off"]}
        vals = [r["cross_track_rms_mm"] for r in sw["on"] + sw["off"] if r.get("cross_track_rms_mm")]
        sc = Scale(0.005, 10 ** math.ceil(math.log10(max(vals))), log=True)
        rows, tb, odd = [], [], []
        for a in accs:
            o, f_ = on.get(a, {}), off.get(a, {})
            vo, vf = o.get("cross_track_rms_mm"), f_.get("cross_track_rms_mm")
            note = []
            if f_ and not f_.get("ok"):
                note.append("off: " + ", ".join(f_.get("errors") or ["failed"]).replace("_", " "))
            if o and o.get("ok") and (o.get("cross_track_worst_mm") or 0) > 1.0:
                note.append(f'on: marked clean with {o["cross_track_worst_mm"]:.1f} mm worst error')
                odd.append(a)
            rows.append({"label": f"{a:,.0f}", "sub": "; ".join(note), "cls": "thin" if note else "",
                         "marks": [("dot", vf, "s2"), ("dot", vo, "s1")],
                         "value": f'{num(vo, 4)} / {num(vf, 4)}',
                         "tip": f'{a:,.0f} mm/s²: shaper on {num(vo, 4)} mm RMS (worst {num(o.get("cross_track_worst_mm"), 3)}), off {num(vf, 4)} mm RMS (worst {num(f_.get("cross_track_worst_mm"), 3)})'})
            tb.append([f"{a:,.0f}", num(vo, 4), num(o.get("cross_track_worst_mm"), 3), "clean" if o.get("ok") else e(", ".join(o.get("errors") or [])),
                       num(vf, 4), num(f_.get("cross_track_worst_mm"), 3), "clean" if f_.get("ok") else e(", ".join(f_.get("errors") or []))])
        ticks = [t for t in (0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0) if t <= sc.hi]
        nfe = sum(1 for r in sw["off"] if "firmware_error" in (r.get("errors") or []))
        chart = rowchart(rows, sc, ticks, legend=[("input shaper and pressure advance on", "s1", "dot"), ("both off", "s2", "dot")],
                         label="Path error against acceleration", val_title="on / off, mm RMS", axis_title="sideways path error on the test cube, mm RMS (log scale); rows are acceleration in mm/s²")
        oddtxt = (f' Two rows look wrong and are shown as recorded: at {" and ".join(f"{a:,.0f}" for a in odd)} mm/s² with shaping on, the scorer marks the print clean while its worst path error is several millimetres.' if odd else "")
        sweep = (f'<h3>Pushing the acceleration with real firmware</h3>{chart}'
                 f'<p class="cap"><b>What was checked.</b> Klipper (commit {e(sw["commit"])}) planned a test cube at rising acceleration and {sw["speed_scale"]:g} times speed, and the dynamic model followed its step pulses. <b>What it means.</b> With shaping on, path error stays near 0.01 mm far beyond any acceleration an owner would run; with it off, error grows steadily.{oddtxt} {f"With shaping off, {nfe} of {len(sw['off'])} prints could not be decoded from the firmware's output; docs/PRINTER_V8.md puts that on the decoder, not the machine." if nfe else ""} <b>Assumed.</b> The sweep is a ceiling test of the model, not a recommended setting.</p>'
                 + details("Table of the sweep", table(["Acceleration, mm/s²", "On: RMS, mm", "On: worst, mm", "On: result", "Off: RMS, mm", "Off: worst, mm", "Off: result"], tb)))
    imgs = ""
    if media.get("printed"):
        imgs += f'<figure class="paper"><img src="img/{e(media["printed"])}" alt="The simulated printed bracket, deposited material rendered in 3D beside its intended shape" loading="lazy"><figcaption>The deposited part, as the model laid it down.</figcaption></figure>'
    if media.get("layers"):
        imgs += f'<figure class="paper"><div class="scrollx"><img class="wideimg" src="img/{e(media["layers"])}" alt="Five layers of the print: deposited material in blue against the intended outline in red" loading="lazy"></div><figcaption>Five of the {pr["layers"]} layers: blue is deposited material, red the intended outline.</figcaption></figure>'
    fl = pr.get("first_layer_gap_error_mm") or {}
    return f'''
<section id="firmware"><div class="wrap">
  <h2>Firmware in the loop</h2>
  <p class="intro">The harness writes a Klipper configuration for the machine. Real Klipper loads it, plans a sliced part and emits step pulses; the dynamic model moves under those pulses and lays down material. This tests the configuration, the kinematics and the motion together.</p>
  <div class="fwgrid"><div class="vid">{vid}</div><dl class="specs tight">{tiles}</dl></div>
  {imgs}
  <p class="cap"><b>What was checked.</b> A {P["size"][0]:g} x {P["size"][1]:g} x {P["size"][2]:g} mm motor bracket, sliced and printed in simulation on {e(P["fw"]["firmware"])} {e(P["commit"])} for an {e(P["fw"]["mcu"])} controller. <b>What it means.</b> Klipper accepted the generated configuration and raised no message; the toolhead never left the planned path by more than {P["fw"]["max_distance_from_gcode_path_mm"]:.3f} mm in the firmware's own plan, no layer shifted, and peak step rate was {max(P["fw"]["peak_step_rate_hz"].values()):,} of {P["fw"]["mcu_step_rate_limit_hz"]:,} steps per second. Corners bulge up to {pr["max_bulge_mm"]:.2f} mm, which is the one warning. <b>Assumed.</b> Material flow is a first-order lag; cooling, warping and adhesion are not modelled; homing and probing against real switches are not exercised.</p>
  {sweep}
</div></section>'''


def sec_wolf(F) -> str:
    R = F.get("ref")
    if not R:
        return ""
    order = ["checker", "checker_probable", "missing", "modelling", "real", "new"]
    cls = {"checker": "c1", "checker_probable": "c1b", "missing": "c3", "modelling": "c4", "real": "c2", "new": "c5"}

    def bar(by, total, scale_total):
        segs = []
        for k in order:
            n = sum((by.get(k) or {}).values())
            if n:
                codes = ", ".join(f"{c} x{v}" for c, v in by[k].items())
                segs.append(f'<span class="seg {cls[k]}" style="flex:{n} 1 0" tabindex="0" data-tip="{e(REF_CLASS_LABEL[k])}: {n} ({e(codes)})"><b>{n}</b></span>')
        pad = scale_total - total
        return f'<div class="segbar tall">{"".join(segs)}{f"<span class=pad style=flex:{pad}_1_0></span>".replace("_", " ") if pad > 0 else ""}</div>'

    later = R.get("later")
    mx = max(R["total"], (later or {}).get("total", 0))
    rows = f'<div class="wr"><div class="wl"><b>{R["total"]} errors</b><span>first full run, {e(R["when"])}</span></div>{bar(R["by_class"], R["total"], mx)}</div>'
    latertxt = ""
    if later:
        rows += f'<div class="wr"><div class="wl"><b>{later["total"]} errors</b><span>same model, today\'s checks, {e(later["when"])}</span></div>{bar(later["by_class"], later["total"], mx)}</div>'
        gone = {c: n for k in R["by_class"] for c, n in R["by_class"][k].items() if c not in {c2 for kk in later["by_class"] for c2 in later["by_class"][kk]}}
        new = later["by_class"].get("new") or {}
        latertxt = (f' Re-run for this page against today\'s checks, the same model gives {later["total"]} errors: '
                    + (f'{sum(gone.values())} of the original errors are gone ({", ".join(f"{c} x{n}" for c, n in gone.items())})' if gone else "none of the original errors are gone")
                    + (f', and checks added since raise {sum(new.values())} new ones ({", ".join(f"{c} x{n}" for c, n in new.items())}) that nobody has classified yet.' if new else "."))
    used = [k for k in order if sum((R["by_class"].get(k) or {}).values()) or sum(((later or {}).get("by_class", {}).get(k) or {}).values())]
    leg = "".join(f'<span class="lg"><span class="sw {cls[k]}"></span>{e(REF_CLASS_LABEL[k])}</span>' for k in used)
    tb = []
    for k in order:
        for c, n in (R["by_class"].get(k) or {}).items():
            n2 = sum(v.get(c, 0) for v in ((later or {}).get("by_class") or {}).values()) if later else None
            tb.append([e(REF_CLASS_LABEL[k]), f"<code>{e(c)}</code>", n, "n/a" if n2 is None else n2])
    if later:
        for c, n in (later["by_class"].get("new") or {}).items():
            tb.append([e(REF_CLASS_LABEL["new"]), f"<code>{e(c)}</code>", 0, n])
    nchk = sum((R["by_class"].get("checker") or {}).values()) + sum((R["by_class"].get("checker_probable") or {}).values())
    return f'''
<section id="wolf"><div class="wrap">
  <h2>Checking the checks</h2>
  <p class="intro">A pass only means something if the checks fail the right things. So the harness was pointed at a printer that is known to work: a model of the Rat Rig V-Minion, a 180 mm kit sold since 2021. A good checker should find little wrong with it.</p>
  <div class="wolf" role="group" aria-label="Errors raised on the known-good machine, by cause">{rows}</div>
  <div class="legend">{leg}</div>
  <p class="cap"><b>What was checked.</b> All twelve verifiers on a model of the kit, re-drawn from its published dimensions and bill of materials, with every error then traced to its cause by hand (docs/REFERENCE_MACHINE.md). <b>What it means.</b> Of {R["total"]} errors, {nchk} were the checker's own fault, {sum((R["by_class"].get("missing") or {}).values())} came from parts the catalogue lacks, {sum((R["by_class"].get("modelling") or {}).values())} was a modelling mistake and only {sum((R["by_class"].get("real") or {}).values())} describe the real machine. More than half of the alarms on a working printer were false.{latertxt} <b>Assumed.</b> The model of the kit is simplified and its classification is one reviewer's reading. v8's clean result was earned against checks with this record.</p>
  {details("Table of error codes on the known-good machine", table(["Cause", "Error code", "First run", "Today"], tb))}
</div></section>'''


HISTORY = [
    ("v4", "First complete machine", "Passed, but almost every custom part was machined and the bed stage tilted on one guide block per rail. A trade study, not a failed check, sent it back.",
     ["cost of manufacture", "bed tilt mode at 76 Hz"]),
    ("v5", "Printed and laser-cut instead of machined", "The tolerance simulation found screw patterns through printed holes that would not start; interference found captive nuts fouling their pockets and screws short of thread; vendor CAD exposed a locating rib that hit a plate.",
     ["screws that may not align", "thread engagement", "vendor CAD detail clashes"]),
    ("v6", "Direct drive on the rail, real catalogue parts", "The assembly simulation raised 54 errors from four causes (nuts in blind tunnels, a guide block that could not slide on, screws blocked by the tray). Wiring checks found blocked connectors and tight bends; Klipper rejected a generated configuration.",
     ["assembly order and tool access", "wiring and connectors", "collisions at the ends of travel", "firmware rejects the config"]),
    ("v7", "Corrected against vendor data sheets", "Data sheets collected after v6 corrected the catalogue, and v6 then failed: the coupler bore was shallower than drawn, both endstops operated at a different position, the relay needed a neutral, and the Y motor shafts were overloaded sideways.",
     ["catalogue part data was wrong", "endstops never reached", "motor shaft radial load", "mains wiring"]),
    ("v8", "Redesigned for function", "Checks added after v7 test gaps as built and measure how the bed is held. v7 then showed five gaps that close in 3% to 24% of builds, a probe with metal in its quiet zone in 44% of builds, and a bed that sags 0.09 mm under a 1 kg print.",
     ["clearances that close under tolerance", "probe metal-free zone", "bed sag under print weight", "probe coverage"]),
]


def sec_history(F) -> str:
    vers = {v["label"]: v for v in F["versions"]}
    cmax = max(sum(v["by_process"].values()) for v in F["versions"])
    cards = []
    for lab, title, text, tags in HISTORY:
        v = vers.get(lab)
        if not v:
            continue
        bp = v["by_process"]
        tot = sum(bp.values()) or 1
        seg = "".join(f'<span class="seg p-{k}" style="flex:{bp.get(k, 0)} 1 0" tabindex="0" data-tip="{k}: {bp.get(k, 0)} custom parts"></span>' for k in ("machined", "sheet", "printed") if bp.get(k))
        seg += f'<span class="pad" style="flex:{cmax - tot} 1 0"></span>' if cmax > tot else ""
        if lab == "v8" and F["clear"].get("v7") and F["bed"]:
            c7 = F["clear"]["v7"]
            pcs = [p["p_closed"] for p in c7["pairs"] if p.get("severity") == "error"]
            pm = (c7.get("probe_metal") or [None])[0]
            b7 = next((b for b in F["bed"] if b["label"] == "v7"), None)
            text = (f"Checks added after v7 test gaps as built and measure how the bed is held. v7 then showed {len(pcs)} gaps that close in {100 * min(pcs):.0f}% to {100 * max(pcs):.0f}% of builds"
                    + (f", a probe with metal in its quiet zone in {100 * pm['p_closed']:.0f}% of builds" if pm else "")
                    + (f", and a bed that sags {b7['print'][1]:.2f} mm under a 1 kg print." if b7 else "."))
        chips = "".join(f"<li>{e(t)}</li>" for t in tags)
        cards.append(f'<li class="hv{" cur" if lab == F["design"].replace("printer_", "") else ""}"><div class="hvh"><b>{e(lab)}</b><span>{e(title)}</span></div>'
                     f'<p>{e(text)}</p><ul class="chips">{chips}</ul>'
                     f'<div class="hvd"><span><b>{v["parts"]}</b> parts</span><span><b>{v["mass_kg"]:.1f}</b> kg</span><span><b>${v["bom_usd"]:,.0f}</b> bought parts</span>'
                     f'<span class="mini"><span class="segbar">{seg}</span>{bp.get("machined", 0)} machined, {bp.get("sheet", 0)} cut, {bp.get("printed", 0)} printed</span></div></li>')
    return f'''
<section id="history"><div class="wrap">
  <h2>What each round exposed</h2>
  <p class="intro">{len(cards)} designs, each a full pass through the same loop. Each began from the one before and from whatever the checks, or new data, had just shown to be wrong. The chips name the class of defect that drove each round.</p>
  <ol class="hist">{"".join(cards)}</ol>
  <div class="legend"><span class="lg"><span class="sw p-machined"></span>machined</span><span class="lg"><span class="sw p-sheet"></span>laser-cut sheet</span><span class="lg"><span class="sw p-printed"></span>3D printed</span></div>
  <p class="cap">Part counts, mass and cost are from each design's own report in <code>out/</code>, made on the day it was designed. The narrative is condensed from docs/PRINTER_V5.md to PRINTER_V8.md. v8 costs more than v7 in parts, mass and money; the owner's brief for it put function first.</p>
</div></section>'''


def sec_open(F) -> str:
    li = "".join(f"<li>{md_inline(x)}</li>" for x in F["unverified"])
    return f'''
<section id="open"><div class="wrap">
  <h2>What is still unverified</h2>
  <p class="intro">Passing every check does not make the machine real. These are the things no check covers, taken word for word from {e(F["unverified_source"])}.</p>
  <ul class="open">{li}</ul>
  <p class="cap">Beyond this list: the frame's own stiffness does not enter the dynamic model, the tolerance spreads are typical values and not a supplier's, and no number on this page has been compared with a measurement of this machine, because there is no machine.</p>
</div></section>
<footer><div class="wrap"><p>Generated {e(F["generated"])} by <code>tools/build_showcase.py</code> from <code>out/{e(F["design"])}/</code> and the documents under <code>docs/</code>. Simulated; never built.</p></div></footer>'''


# ------------------------------------------------------------------------------------------- media

def make_media(F, show: Path) -> dict:
    """Copy the print pictures as WebP and turn the animated GIF into a small MP4."""
    from PIL import Image

    P = F.get("print")
    img = show / "img"
    out = {}
    if not P:
        return out
    d = ROOT / P["dir"]
    for key, pat in (("printed", "*_printed.png"), ("layers", "*_layers.png")):
        src = next(iter(sorted(d.glob(pat))), None)
        if src:
            im = Image.open(src).convert("RGB")
            if im.width > 2200:
                im = im.resize((2200, round(im.height * 2200 / im.width)), Image.LANCZOS)
            im.save(img / f"print_{key}.webp", "WEBP", quality=88, method=6)
            out[key] = f"print_{key}.webp"
    gif = next(iter(sorted(d.glob("*_printing.gif"))), None)
    if gif:
        g = Image.open(gif)
        g.seek(g.n_frames - 1)
        g.convert("RGB").save(img / "print_poster.webp", "WEBP", quality=86)
        out["poster"] = "print_poster.webp"
        if shutil.which("ffmpeg"):
            mp4 = img / "print_printing.mp4"
            r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(gif), "-movflags", "+faststart", "-pix_fmt", "yuv420p",
                                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-crf", "26", "-preset", "slow", str(mp4)],
                               capture_output=True, text=True)
            if r.returncode == 0 and mp4.exists():
                out["video"] = mp4.name
            else:
                print("  ffmpeg failed:", r.stderr[-200:])
    return out


def run(design_path: Path, show: Path, refresh: bool = False) -> None:
    if refresh:
        refresh_inputs(show / "data" / "inputs")
    F = collect(design_path, show)
    F["media"] = make_media(F, show)
    (show / "data" / "facts.json").write_text(json.dumps({k: v for k, v in F.items() if k != "renders"}, indent=1, default=str))
    css = (ROOT / "tools" / "showcase_page.css").read_text()
    js = (ROOT / "tools" / "showcase_page.js").read_text()
    body = "".join([sec_header(F), "<main>", sec_features(F), sec_checks(F), sec_bed(F), sec_tolerance(F), sec_probe(F), sec_twin(F),
                    sec_firmware(F), sec_wolf(F), sec_history(F), sec_open(F), "</main>"])
    page = ('<title>Printer v8 Showcase</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">\n'
            f"<style>\n{css}\n</style>\n{body}\n<div id=\"tip\" role=\"status\" hidden></div>\n<script>\n{js}\n</script>\n")
    (show / "index.html").write_text(page)
    size = sum(p.stat().st_size for p in show.rglob("*") if p.is_file())
    print(f"  wrote {show / 'index.html'} ({len(page) / 1024:.0f} kB); showcase/ is {size / 1e6:.1f} MB in all")
