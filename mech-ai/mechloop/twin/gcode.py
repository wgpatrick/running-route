"""Slice a part with PrusaSlicer and read the G-code back as a list of moves."""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Move:
    x: float
    y: float
    z: float
    e: float  # filament length extruded during this move (mm, negative = retract)
    feed: float  # mm/s
    line: int


def slice_part(stl: Path, out: Path, *, layer_height: float = 0.2, nozzle: float = 0.4,
               filament_diameter: float = 1.75, center=(0.0, 0.0), perimeter_speed: float = 45.0,
               infill_speed: float = 60.0, travel_speed: float = 150.0, first_layer_speed: float = 20.0,
               fill_density: int = 20, extra: list[str] | None = None) -> Path:
    exe = shutil.which("prusa-slicer")
    if not exe:
        raise RuntimeError("prusa-slicer is not installed; the print was NOT sliced")
    cmd = [exe, "--export-gcode", str(stl), "--output", str(out),
           "--layer-height", str(layer_height), "--first-layer-height", str(layer_height),
           "--nozzle-diameter", str(nozzle), "--filament-diameter", str(filament_diameter),
           "--center", f"{center[0]},{center[1]}", "--gcode-flavor", "marlin",
           "--use-relative-e-distances", "--perimeters", "2", "--top-solid-layers", "4",
           "--bottom-solid-layers", "3", "--fill-density", f"{fill_density}%", "--fill-pattern", "rectilinear",
           "--perimeter-speed", str(perimeter_speed), "--external-perimeter-speed", str(perimeter_speed),
           "--infill-speed", str(infill_speed), "--solid-infill-speed", str(infill_speed),
           "--top-solid-infill-speed", str(perimeter_speed), "--travel-speed", str(travel_speed),
           "--first-layer-speed", str(first_layer_speed), "--skirts", "1", "--skirt-distance", "3",
           "--retract-length", "0.8", "--retract-speed", "35", "--temperature", "215",
           "--bed-temperature", "60", "--start-gcode", "G92 E0", "--end-gcode", "M104 S0",
           "--bed-shape", "-90x-90,90x-90,90x90,-90x90", "--gcode-comments", "--layer-gcode", "G92 E0"]
    p = subprocess.run(cmd + (extra or []), capture_output=True, text=True, timeout=1800)
    if p.returncode != 0 or not out.exists():
        raise RuntimeError("prusa-slicer failed: " + (p.stderr or p.stdout)[-500:])
    return out


_TOK = re.compile(r"([XYZEF])(-?\d*\.?\d+)")


def parse(path: Path) -> tuple[list[Move], dict]:
    """G0/G1 moves in absolute XYZ; E returned per move. Unknown codes are counted, not obeyed."""
    # start where the program first sends each axis (the machine's position before that is not in the file)
    first = {}
    for raw in open(path):
        line = raw.split(";", 1)[0].strip().upper()
        if line.startswith(("G0 ", "G1 ")):
            for k, v in _TOK.findall(line):
                first.setdefault(k, float(v))
        if all(k in first for k in "XYZ"):
            break
    x, y, z = first.get("X", 0.0), first.get("Y", 0.0), first.get("Z", 0.0)
    e_abs = 0.0
    feed = 20.0
    rel_e, rel_xyz = False, False
    moves: list[Move] = []
    ignored: dict[str, int] = {}
    for n, raw in enumerate(open(path), 1):
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        code = line.split()[0].upper()
        if code in ("G0", "G1"):
            t = dict(_TOK.findall(line.upper()))
            if "F" in t:
                feed = float(t["F"]) / 60.0
            nx = (x + float(t["X"]) if rel_xyz else float(t["X"])) if "X" in t else x
            ny = (y + float(t["Y"]) if rel_xyz else float(t["Y"])) if "Y" in t else y
            nz = (z + float(t["Z"]) if rel_xyz else float(t["Z"])) if "Z" in t else z
            de = 0.0
            if "E" in t:
                ev = float(t["E"])
                de = ev if rel_e else ev - e_abs
                e_abs = e_abs + ev if rel_e else ev
            if (nx, ny, nz) != (x, y, z) or de != 0.0:
                moves.append(Move(nx, ny, nz, de, feed, n))
            x, y, z = nx, ny, nz
        elif code == "G92":
            t = dict(_TOK.findall(line.upper()))
            if "E" in t:
                e_abs = float(t["E"])
        elif code == "M82":
            rel_e = False
        elif code == "M83":
            rel_e = True
        elif code == "G90":
            rel_xyz = False
        elif code == "G91":
            rel_xyz = True
        else:
            ignored[code] = ignored.get(code, 0) + 1
    return moves, ignored
