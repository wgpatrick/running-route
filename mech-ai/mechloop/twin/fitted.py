"""Parameters of the twin that were fitted to published data, with their ranges, in one machine-readable table.

`fitted_parameters.json` (next to this file) holds, per parameter: the value in use, [low, high], the value it replaced,
the source, whether it was checked on data held out of the fit, and what it is used by. The twin's defaults
(PrinterMap, machine.py, deposit.py) and the heater model (mechloop.electrical.build_plants) read their numbers from
it; nothing else in the code carries a second copy. The table also lists what is NOT fitted, so that a reader of a
score can see which assumptions it still rests on. The fits themselves: research_notes/fitting/ and
reports/Twin fitting.md.  `python -m mechloop.twin.fitted` prints the table."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

FILE = Path(__file__).parent / "fitted_parameters.json"


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(FILE.read_text())


def entry(key: str) -> dict:
    return table()["parameters"][key]


def value(key: str):
    return entry(key)["value"]


def triple(key: str) -> list:
    """[low, value, high] of a scalar parameter."""
    e = entry(key)
    return [e["low"], e["value"], e["high"]]


def _interp_log(tab: dict, d: float) -> float:
    xs = sorted(float(k) for k in tab)
    d = min(max(float(d), xs[0]), xs[-1])
    for a, b in zip(xs, xs[1:]):
        if a <= d <= b:
            w = (math.log(d) - math.log(a)) / (math.log(b) - math.log(a))
            return float(math.exp((1 - w) * math.log(tab[f"{a:g}"]) + w * math.log(tab[f"{b:g}"])))
    return float(tab[f"{xs[0]:g}"])


def extruder_lag(drive: str = "direct", nozzle: float = 0.4, bowden_length_mm: float | None = None, which: str = "value") -> float:
    """Melt-flow lag (s) for a drive type and nozzle: the factory pressure-advance constant of machines of that kind
    (for a first-order lag the two are the same number). Between tabulated nozzle sizes: log interpolation.
    Bowden: the tabulated value is for the reference tube length; the part above the direct-drive value is scaled
    with the design's tube length when it is given (an assumption: compliance in proportion to length).
    which: "value" | "low" | "high"."""
    e = entry("extruder_lag_s")
    tabs = e[which]
    lag_d = _interp_log(tabs["direct"], nozzle)
    if drive != "bowden":
        return round(lag_d, 4)
    lag_b = _interp_log(tabs["bowden"], nozzle)
    if bowden_length_mm:
        lag_b = lag_d + (lag_b - lag_d) * float(bowden_length_mm) / e["bowden_reference_length_mm"]
    return round(lag_b, 4)


def hotend_class(sku: str | None, ptc: bool = False) -> str:
    s = (sku or "").upper()
    return "revo" if ("REVO" in s or ptc) else "v6"


def melt_cap(sku: str | None = None, nozzle: float = 0.4, part_rating=None) -> dict:
    """Volumetric flow a hotend class melts cleanly (mm^3/s) as {"value", "low", "high", "class", "source"}.
    The catalogue part's own vendor figure, when it has one, sits inside the class range and is reported too."""
    e = entry("melt_rate_cap_mm3_s")
    cls = hotend_class(sku)
    c = e["value"][cls]
    scale = (float(nozzle) / 0.4) ** e["nozzle_exponent"] if abs(nozzle - 0.4) > 1e-9 else 1.0
    out = {"class": cls, "value": round(c * scale, 2), "low": round(e["low"][cls] * scale, 2), "high": round(e["high"][cls] * scale, 2),
           "source": e["source"], "nozzle_scaling": None if scale == 1.0 else f"x (d/0.4)^{e['nozzle_exponent']:g} (assumed, not fitted)"}
    if part_rating:
        out["part_vendor_figure"] = part_rating
    return out


def hotend_thermal(cls: str) -> dict:
    return entry("hotend_thermal")["value"][cls]


def summary_rows() -> list:
    """One row per parameter for reports: key, old, value, range, source, held-out check."""
    rows = []
    for k, e in table()["parameters"].items():
        rows.append({"parameter": k, "status": e.get("status"), "old": e.get("old"), "value": e.get("value"), "low": e.get("low"),
                     "high": e.get("high"), "unit": e.get("unit"), "source": e.get("source"), "held_out": e.get("held_out"),
                     "used_by": e.get("used_by")})
    return rows


if __name__ == "__main__":
    print(json.dumps(table(), indent=1))
