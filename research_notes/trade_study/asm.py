"""Shared helpers for measuring the extracted assembly JSON (see extract_step.py)."""
import json, re
import numpy as np

FASTENER = re.compile(r"(^|[\s/_-])(M\d(\.\d)?\s?[xX×]\s?\d+|M\d+\s?(hex|nut|washer|thread|heat|nyl|t-?nut|roll|x)|"
                      r"[SBF]HCS|screw|washer|t-?nut|hex ?nut|locking nut|self-locking|heat ?set|threaded insert|"
                      r"self tapper|grub|set ?screw|bolt|shim|split washer|DIN ?\d+|ISO ?\d+)", re.I)
# effective densities, g/cm3 of CAD solid volume (assumptions, stated in the report)
RHO = dict(printed=0.70,      # ABS 1.04 x ~0.67 fill (4 walls, 40 % infill: the Voron print settings)
           aluminium=2.70, steel=7.85, motor=4.6, belt=1.2, plastic=1.1, other=1.5)


def load(path):
    return json.load(open(path))["leaves"]


def name(l, n=3):
    return "/".join(l["path"][-n:])


def sel(L, rx, minvol=0.0, not_rx=None):
    r = re.compile(rx, re.I)
    nr = re.compile(not_rx, re.I) if not_rx else None
    return [l for l in L if r.search("/".join(l["path"])) and l["vol"] >= minvol
            and not (nr and nr.search("/".join(l["path"])))]


def union(ls):
    b = np.array([l["bbox"] for l in ls])
    lo, hi = b[:, :3].min(0), b[:, 3:].max(0)
    return dict(min=[round(float(x), 1) for x in lo], max=[round(float(x), 1) for x in hi],
                size=[round(float(x), 1) for x in hi - lo])


def size(l):
    b = l["bbox"]
    return [round(b[i + 3] - b[i], 1) for i in range(3)]


def centre(l):
    b = l["bbox"]
    return [round((b[i + 3] + b[i]) / 2, 1) for i in range(3)]


def is_fastener(l):
    return bool(FASTENER.search(l["path"][-1])) or bool(FASTENER.search(l["path"][-2] if len(l["path"]) > 1 else ""))


def klass(l, printed_rx, default="other"):
    """Material class of one solid, from its name (last two levels of the assembly path)."""
    p = "/".join(l["path"])
    p2 = "/".join(l["path"][-2:])
    if is_fastener(l):
        return "steel"
    if re.search(printed_rx, p, re.I):
        return "printed"
    if re.search(r"nema|stepper|\d\dSTH|motor(?![ _](plate|mount|bracket|panel|holder|cage))", l["path"][-1], re.I):
        return "motor"
    if re.search(r"mgn|rail|bearing|\brod\b|shaft|lead ?screw|gear|magnet|spring|heat ?block|nozzle|flex ?(plate|sheet)|"
                 r"F6\d\d|\b62\d|pillow|roller", p2, re.I):
        return "steel"
    if re.search(r"extrusion|profile|HFSB|1515|2020|2040|3030|4040|mic6|bed plate|hot bed|y plate|heat ?sink|radiator|"
                 r"bracket|stent|pulley|idler|tooling", p2, re.I):
        return "aluminium"
    if re.search(r"belt", p2, re.I):
        return "belt"
    if re.search(r"fan|panel|acrylic|cover|duct|chain", p2, re.I):
        return "plastic"
    return default


def mass_kg(ls, printed_rx=r"Printed Parts", default="other"):
    m, by = 0.0, {}
    for l in ls:
        k = klass(l, printed_rx, default)
        g = l["vol"] / 1000 * RHO[k]
        m += g
        by[k] = by.get(k, 0.0) + g
    return round(m / 1000, 3), {k: round(v / 1000, 3) for k, v in by.items()}
