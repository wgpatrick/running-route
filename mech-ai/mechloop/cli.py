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
    v.add_argument("--only", nargs="*", help="subset of: geometry interference tolerance manufacture ratings motion subsystems electrical assemblability fea printing requirements")
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
    asm = sub.add_parser("assemble", help="simulate building the design: order, holding, tools, time, instructions")
    asm.add_argument("design")
    asm.add_argument("--out", default="out")
    asm.add_argument("--no-render", action="store_true")
    sc = sub.add_parser("score", help="scorecard for a printer design (things to improve, not just pass)")
    sc.add_argument("design")
    sc.add_argument("--out", default="out")
    sc.add_argument("--assembly", action="store_true", help="also run the assembly simulation (slower)")
    c = sub.add_parser("catalog", help="list off-the-shelf parts")
    c.add_argument("query", nargs="?", default="")
    a = p.parse_args(argv)
    if a.cmd == "verify":
        from .runner import run

        from .runner import ORDER
        only = [n for item in (a.only or []) for n in item.split(",") if n] or None
        known = [o if isinstance(o, str) else o[0] for o in ORDER] + ["requirements"]
        bad = [n for n in (only or []) if n not in known]
        if bad:
            sys.exit(f"unknown verifier(s) {bad}; choose from: {' '.join(known)}")
        rep = run(a.design, a.out, only, render=not a.no_render)
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
                          "trapped": res["plan"].trapped, "artifacts": arts}, indent=1, default=str))
        return 0 if res["metrics"]["complete"] else 1
    if a.cmd == "score":
        from .twin.score import score

        res = score(a.design, a.out, assembly=a.assembly)
        print(json.dumps(res, indent=1, default=float))
        return 0 if res.get("static_checks_ok") and res.get("nominal_print_ok") else 1
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
