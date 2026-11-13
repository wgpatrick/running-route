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
    c = sub.add_parser("catalog", help="list off-the-shelf parts")
    c.add_argument("query", nargs="?", default="")
    a = p.parse_args(argv)
    if a.cmd == "verify":
        from .runner import run

        rep = run(a.design, a.out, a.only, render=not a.no_render)
        print(rep.to_json(max_findings=a.max_findings))
        return 0 if rep.ok else 1
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
