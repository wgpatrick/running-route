"""mechloop CLI. JSON on stdout, bounded size, exit code 0 = all pass, 1 = findings, 2 = usage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


OUT_HELP = ("ROOT folder for outputs (default: out). Files are written to <out>/<design name>/ (report.json, renders, STEP, "
            "electrical/printer.cfg, score/, tune/), so pass the same root to verify, score, tune and assemble: "
            "`--out out` gives out/printer_v7/report.json; `--out out/printer_v7` gives out/printer_v7/printer_v7/report.json, "
            "which score, tune and print started with the default root will not find")


def _warn_nested_out(out, name: str) -> None:
    """--out is a root, not the design's own folder: say so when the two were probably confused."""
    if Path(out).name == name:
        print(f"WARNING: --out {out} ends in the design's name: outputs go to {Path(out) / name}/ (--out is the ROOT folder; "
              f"<out>/<design name>/ is added). `mechloop score`, `tune` and `print` run without the same --out will not find "
              f"this run's report.json. Use --out {Path(out).parent} to write to {out}/.", file=sys.stderr, flush=True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mechloop")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="build a design script and run the verifiers")
    v.add_argument("design", help="python file defining build() -> Design")
    v.add_argument("--only", nargs="*", help="subset of: geometry interference tolerance manufacture practice ratings motion subsystems electrical assemblability fea printing requirements; opt-in (only when named): part_quality")
    v.add_argument("--out", default="out", help=OUT_HELP)
    v.add_argument("--no-render", action="store_true")
    v.add_argument("--max-findings", type=int, default=25)
    v.add_argument("--tier", choices=["quick", "affected", "full"], default=None,
                   help="staged verify (mechloop.incremental): quick = geometry, interference on changed parts, manufacture, "
                        "practice, ratings (other verifiers reused if their inputs are unchanged, else NOT RUN: a partial "
                        "report); affected = re-run every verifier (FEA case by case, interference pair by pair) whose inputs "
                        "changed and reuse the rest; full = everything, nothing reused (required before release; a design "
                        "with release = True always gets it). Default (no --tier): a full verify, as before")
    v.add_argument("--no-cache", action="store_true",
                   help="neither read nor write the result cache (out/<design>/verify_cache/)")
    v.add_argument("--jobs", type=int, default=None,
                   help="parallel processes for verifiers and FEA cases (default for --tier runs: the CPU count up to 4; "
                        "a plain verify is serial). Memory-aware: at most 2 heavy CalculiX cases at once, within --memory-budget")
    v.add_argument("--serial", action="store_true", help="run everything in this process, one after the other (= --jobs 1)")
    v.add_argument("--memory-budget", type=int, default=None, metavar="MB",
                   help="memory the parallel jobs may add, MB (default 12500 of the 15 GB container)")
    v.add_argument("--no-wait", action="store_true",
                   help="if another heavy FEA run holds the machine-wide solver lock (/tmp/mechloop_heavy.lock), report the "
                        "FEA cases that need it as not run instead of waiting for it")
    v.add_argument("--render", action="store_true", help="render views / motion even in the quick and affected tiers")
    v.add_argument("--step", action="store_true", help="export the STEP model even in the quick and affected tiers")
    h = sub.add_parser("history", help="show the loop history of a design")
    h.add_argument("name")
    h.add_argument("--out", default="out", help="ROOT folder the verify runs wrote to (reads <out>/<name>/history.jsonl)")
    pr = sub.add_parser("print", help="digital twin: slice a part and print it on a printer design")
    pr.add_argument("printer", help="python file defining build() -> Design of the printer")
    pr.add_argument("part", help="<design.py>:<component> or a .stl/.step file; printed as modelled, base on the bed")
    pr.add_argument("--out", default="out/twin", help="folder for this print's outputs: <out>/<part name>/ (default out/twin). The "
                    "printer's frame stiffness is read from out/<printer name>/report.json (the default verify root)")
    pr.add_argument("--layer-height", type=float, default=0.2)
    pr.add_argument("--accel-scale", type=float, default=1.0, help="what-if multiplier on XY acceleration limits")
    pr.add_argument("--no-render", action="store_true")
    pr.add_argument("--firmware", choices=["klipper"], help="plan the motion with the real firmware (tools/setup_klipper.sh)")
    pr.add_argument("--trajectory", action="store_true", help="save the simulated nozzle path for replay in the viewer")
    asm = sub.add_parser("assemble", help="simulate building the design: order, holding, tools, time, instructions")
    asm.add_argument("design")
    asm.add_argument("--out", default="out", help=OUT_HELP)
    asm.add_argument("--no-render", action="store_true")
    sc = sub.add_parser("score", help="scorecard for a printer design (things to improve, not just pass); every headline number "
                                      "comes with a [low, expected, high] range under 'headline' and 'ranges'")
    sc.add_argument("design")
    sc.add_argument("--out", default="out", help=OUT_HELP)
    sc.add_argument("--assembly", action="store_true", help="also run the assembly simulation (slower)")
    sc.add_argument("--firmware", choices=["klipper"], help="also score with the real firmware planning every print from the "
                    "generated printer.cfg (input shaper and pressure advance on, and off for comparison); reported under 'klipper'")
    sc.add_argument("--firmware-only", action="store_true", help="with --firmware: skip the built-in planner's sweep and benchmark")
    sc.add_argument("--no-ranges", action="store_true", help="skip the re-runs behind the [low, expected, high] of the step-loss ceiling "
                    "and cross-track error (resonance and the acceleration an owner would run keep their ranges)")
    tu = sub.add_parser("tune", help="firmware tuning on the twin: input shaper, pressure-advance sweep, bed mesh (needs Klipper)")
    tu.add_argument("design")
    tu.add_argument("--out", default="out", help=OUT_HELP + ". tune reads the frame's FEA stiffness from <out>/<design name>/report.json "
                    "(then out/<design name>/report.json) and warns on stderr, and under 'warnings', when neither is usable")
    tu.add_argument("--only", nargs="*", choices=["shaper", "pressure_advance", "bed_mesh"], help="default: all three")
    tu.add_argument("--bed", nargs=3, type=float, metavar=("TILT_X", "TILT_Y", "BOW"), default=None,
                    help="assumed as-built bed surface for the mesh study, mm (default 0.30 0.20 0.15)")
    c = sub.add_parser("catalog", help="list off-the-shelf parts")
    c.add_argument("query", nargs="?", default="")
    a = p.parse_args(argv)
    if a.cmd in ("verify", "print", "assemble", "score", "tune"):
        try:      # scratch folders that killed runs left in /tmp (a bed-support case leaves gigabytes)
            from .resources import sweep_stale

            sweep_stale()
        except Exception:
            pass
    if a.cmd == "verify":
        from .runner import run

        from .runner import OPTIONAL, ORDER
        only = [n for item in (a.only or []) for n in item.split(",") if n] or None
        known = [o if isinstance(o, str) else o[0] for o in ORDER] + ["requirements"] + OPTIONAL
        bad = [n for n in (only or []) if n not in known]
        if bad:
            sys.exit(f"unknown verifier(s) {bad}; choose from: {' '.join(known)}")
        from .verifiers import electrical as _ve

        _ve.OUT_ROOT = a.out      # the electrical verifier writes printer.cfg and the wiring tables under the same root
        if a.no_wait:
            import os

            os.environ["MECHLOOP_NO_WAIT"] = "1"
        rep = run(a.design, a.out, only, render=False if a.no_render else (True if a.render else None), tier=a.tier,
                  use_cache=not a.no_cache, jobs=1 if a.serial else a.jobs, step=True if a.step else None,
                  memory_budget_mb=a.memory_budget)
        _warn_nested_out(a.out, rep.design)
        print(rep.to_json(max_findings=a.max_findings))
        return 0 if rep.ok else 1
    if a.cmd == "print":
        from .runner import load_design
        from .twin import PrinterMap, run_print

        printer = load_design(a.printer)
        if ":" in a.part and a.part.split(":")[0].endswith(".py"):
            f, comp = a.part.rsplit(":", 1)
            shape, name = load_design(f).get(comp).shape, comp
        else:
            from build123d import import_step, import_stl

            shape = import_step(a.part) if a.part.lower().endswith((".step", ".stp")) else import_stl(a.part)
            name = Path(a.part).stem
        pm = PrinterMap(layer_height=a.layer_height)
        if printer.printer:
            from .twin import printer_map_for

            prev = Path("out") / printer.name / "report.json"   # belt and frame stiffness from the last verify, if any
            if not prev.exists() and (printer.printer or {}).get("stiffness"):
                print(f"WARNING: {prev} not found: the print is simulated WITHOUT the frame's FEA stiffness (belt stiffness only). "
                      f"Run `mechloop verify {a.printer}` with the default --out first.", file=sys.stderr, flush=True)
            pm = printer_map_for(printer, json.loads(prev.read_text())["metrics"] if prev.exists() else None,
                                 layer_height=a.layer_height)
        if a.firmware:      # a pressure-advance sweep made by `mechloop tune` with the same --out root is used if there
            from .twin import tuning as _tuning

            for root in (str(Path(a.out).parent), str(a.out)):
                if root not in _tuning.TUNING_ROOTS:
                    _tuning.TUNING_ROOTS.insert(0, root)
        rep = run_print(printer, shape, Path(a.out) / name, pm, name=name, render=not a.no_render,
                        accel_scale=a.accel_scale, firmware=a.firmware, trajectory=a.trajectory)
        print(json.dumps({k: v for k, v in rep.items() if k != "gcode"}, indent=1, default=float))
        return 0 if rep["ok"] else 1
    if a.cmd == "assemble":
        from .assembly.simulate import analyse, instructions
        from .runner import load_design

        d = load_design(a.design)
        res = analyse(d)
        out = Path(a.out) / d.name
        out.mkdir(parents=True, exist_ok=True)
        (out / "BUILD.md").write_text(instructions(d, res))
        arts = {"instructions": str(out / "BUILD.md")}
        if not a.no_render:
            from .assembly.render import render_build

            arts["animation"] = str(render_build(d, res, out / "build.gif"))
        holds = [r["unit"] for r in res["rows"] if r.get("rests_stably") is False]
        res["metrics"].pop("_skus", None)
        print(json.dumps({"design": d.name, "metrics": res["metrics"],
                          "needs_holding": holds[:30], "from_below": [r["unit"] for r in res["rows"] if r.get("direction") == "from below"][:30],
                          "trapped": res["plan"].trapped, "not_placed": res["metrics"]["not_placed"],
                          "artifacts": arts}, indent=1, default=str))
        return 0 if res["metrics"]["complete"] else 1
    if a.cmd == "score":
        from .twin.score import score

        if a.firmware_only and not a.firmware:
            sys.exit("--firmware-only needs --firmware klipper")
        res = score(a.design, a.out, assembly=a.assembly, firmware=a.firmware, builtin=not a.firmware_only, uncertainty=not a.no_ranges)
        print(json.dumps(res, indent=1, default=float))
        fw_ok = True
        if a.firmware:      # a firmware score that did not run, or whose nominal print failed, is not a pass
            k = res.get("klipper") or {}
            fw_ok = bool(k.get("ran")) and bool(k.get("as_configured", {}).get("nominal", {}).get("ok"))
            for w in k.get("prints_not_run") or []:
                print(f"mechloop score: NOT RUN: {w}", file=sys.stderr)
        builtin_ok = res.get("nominal_print_ok") if not a.firmware_only else True
        return 0 if res.get("static_checks_ok") and builtin_ok and fw_ok else 1
    if a.cmd == "tune":
        from .twin.tuning import tune_report

        res = tune_report(a.design, a.out, only=a.only, bed=a.bed)
        print(json.dumps(res, indent=1, default=float))
        return 0 if res.get("ok") else 1
    if a.cmd == "history":
        f = Path(a.out) / a.name / "history.jsonl"
        if not f.exists():
            print(json.dumps({"error": f"no history at {f}"}))
            return 2
        print(f.read_text().strip())
        return 0
    if a.cmd == "catalog":
        from .parts import catalog
        from .parts import electrical as _electrical_parts  # noqa: F401  (registers the electrical catalog parts)

        print(json.dumps(catalog(a.query), indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
