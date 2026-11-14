"""The digital twin as a verifier: a printer design must print a short test part cleanly."""
from __future__ import annotations

import tempfile
from pathlib import Path

from ..model import Design
from ..report import VerifierResult, timed


def verify_printing(design: Design, metrics: dict) -> VerifierResult:
    r = VerifierResult("printing")
    if not design.printer:
        r.skipped = "design does not declare design.printer"
        return r
    with timed(r):
        from build123d import Box, Pos

        from ..twin import printer_map_for, run_print

        pm = printer_map_for(design, metrics)
        with tempfile.TemporaryDirectory(prefix="mechloop_print_") as tmp:
            rep = run_print(design, Pos(0, 0, 2) * Box(20, 20, 4), Path(tmp), pm, name="test_cube",
                            render=False, collisions=True)
        for f in rep.get("findings", []):
            r.add(f["severity"], f["code"], "Test print: " + f["message"], **{k: v for k, v in f.get("data", {}).items() if k != "hint"},
                  **({"hint": f["data"]["hint"]} if "hint" in f.get("data", {}) else {}))
        d, p = rep.get("dynamics", {}), rep.get("print", {})
        r.metrics = {"test_part": "20 x 20 x 4 mm cube", "print_time_s": rep.get("plan", {}).get("print_time_s"),
                     "heatup_s": rep.get("plan", {}).get("heatup_s"), "job_time_s": rep.get("plan", {}).get("job_time_s"),
                     "load_resonance_hz": d.get("load_resonance_hz"),
                     "series_stiffness_n_per_mm": d.get("series_stiffness_n_per_mm"),
                     "frame_stiffness_from_fea_n_per_mm": pm.struct_stiffness or "not coupled",
                     "belts_per_axis": d.get("belts_per_axis"),
                     "print_speeds_mm_s": {"perimeter": pm.perimeter_speed, "infill": pm.infill_speed, "travel": pm.travel_speed},
                     "worst_lag_mm": d.get("worst_lag_mm"), "cross_track_rms_mm": d.get("cross_track_rms_mm"),
                     "cross_track_worst_mm": d.get("cross_track_worst_mm"),
                     "outline_match_min": p.get("outline_iou_min"), "outline_offset_mm": p.get("outline_offset_mm"),
                     "max_bulge_mm": p.get("max_bulge_mm"), "machine_collisions": rep.get("machine_collisions")}
    return r
