"""Run the whole in-simulation evaluation of designs/printer.py and write out/eval/evaluation.json."""
import json
import sys
from pathlib import Path

from mechloop.twin.evals import benchmark_suite, run_everything
from mechloop.twin.reference import check

if __name__ == "__main__":
    here = Path(__file__).parent
    out = Path("out/eval")
    if len(sys.argv) > 1 and sys.argv[1] == "bench":
        res = benchmark_suite(here / "printer.py", out / "bench")
        out.mkdir(parents=True, exist_ok=True)
        (out / "bench.json").write_text(json.dumps(res, indent=1, default=float))
    else:
        res = run_everything(here / "printer.py", out)
        res["voron_reference"] = check()
        (out / "evaluation.json").write_text(json.dumps(res, indent=1, default=float))
    print("done")
