"""mechloop CLI. JSON on stdout, bounded size, exit code 0 = all pass, 1 = findings, 2 = usage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="mechloop")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="build a design script and run the verifiers")
    v.add_argument("design", help="python file defining build() -> Design")
    v.add_argument("--only", nargs="*", help="subset of: geometry interference ratings motion assemblability fea requirements")
    v.add_argument("--out", default="out")
    v.add_argument("--no-render", action="store_true")
    v.add_argument("--max-findings", type=int, default=25)
    h = sub.add_parser("history", help="show the loop history of a design")
    h.add_argument("name")
    h.add_argument("--out", default="out")
    pr = sub.add_parser("print", help="digital twin: slice a part and print it on a printer design")
    pr.add_argument("printer", help="python file defining build() -> Design of the printer")
    pr.add_argument("part", help="<design.py>:<component> or a .stl/.step file; printed as modelled, base on the bed")
    pr.add_argument("--out", default="out/twin")
    pr.add_argument("--layer-height", type=float, default=0.2)
    pr.add_argument("--accel-scale", type=float, default=1.0, help="what-if multiplier on XY acceleration limits")
    pr.add_argument("--no-render", action="store_true")
    c = sub.add_parser("catalog", help="list off-the-shelf parts")
    c.add_argument("query", nargs="?", default="")
    a = p.parse_args(argv)
    if a.cmd == "verify":
        from .runner import run

        rep = run(a.design, a.out, a.only, render=not a.no_render)
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
        rep = run_print(printer, shape, Path(a.out) / name, PrinterMap(layer_height=a.layer_height), name=name,
                        render=not a.no_render, accel_scale=a.accel_scale)
        print(json.dumps({k: v for k, v in rep.items() if k != "gcode"}, indent=1, default=float))
        return 0 if rep["ok"] else 1
    if a.cmd == "history":
        f = Path(a.out) / a.name / "history.jsonl"
        if not f.exists():
            print(json.dumps({"error": f"no history at {f}"}))
            return 2
        print(f.read_text().strip())
        return 0
    if a.cmd == "catalog":
        from .parts import catalog

        print(json.dumps(catalog(a.query), indent=1))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
