"""Digital-twin runs on designs/printer.py: `python designs/print_runs.py cube|bracket|shift`."""
import json
import sys
from pathlib import Path

from build123d import Box, Pos

from mechloop.runner import load_design
from mechloop.twin import PrinterMap, run_print

HERE = Path(__file__).parent


def main(which: str) -> int:
    printer = load_design(HERE / "printer.py")
    if which == "cube":
        rep = run_print(printer, Pos(0, 0, 10) * Box(20, 20, 20), Path("out/twin_cube"), PrinterMap(), name="cube")
    elif which == "bracket":   # the PETG motor bracket from examples/motor_bracket.py, printed base-down
        br = load_design(HERE.parent / "examples" / "motor_bracket.py").get("bracket").shape
        rep = run_print(printer, br, Path("out/twin_bracket"), PrinterMap(layer_height=0.3), name="bracket")
    elif which == "shift":     # what if acceleration were set 25x too high with motor current turned down to 30%?
        rep = run_print(printer, Pos(0, 0, 5) * Box(20, 20, 10), Path("out/twin_shift"), PrinterMap(),
                        name="cube_fast", accel_scale=25.0, torque_scale=0.3)
    else:
        print("unknown run"); return 2
    slim = {k: v for k, v in rep.items() if k != "gcode"}
    print(json.dumps(slim, indent=1, default=float))
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "cube"))
