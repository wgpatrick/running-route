"""Arm Build 1 cell (EXPLORATORY): a light printer proxy and placeholder stations on the bench, as boxes.

Concept-spike geometry only (docs/ARM_CONCEPT_SPIKE.md, ARM_SCOPE.md section 12 step 1). Every box comes from
mechloop/arm/cell.py, which holds the numbers and their sources; nothing here imports a printer design file. Frame: x
right, y into the printer, z up, origin on the bench under the centre of the printer frame's front face.

Contents: printer envelope with the 300 mm front opening, bed (sheet top) at the transfer height, toolhead parked rear
top, the v12 e-stop head; V13 front door (hinged left, 3 mm polycarbonate) at a chosen angle with its free-edge loop;
the stowable sheet shelf (deployed or stowed); inspection stage, tool rack, parts tray, screw station and release tray
in the "ring" (rotary arm) or "row" (Cartesian) layout; the bench plane. A skeleton arm can be added for a look.

Not buildable: no parts are real, nothing is fastened; exploratory = True (practice DG-07 reports warnings only).
"""
from build123d import Box, Pos

from mechloop import Design
from mechloop.arm import cell as C

Z_T = 229.0   # bed transfer height chosen by all three candidates in the spike (lowest bed position)


def _box(d, name, lo, hi, material="pla", **meta):
    lo, hi = [float(v) for v in lo], [float(v) for v in hi]
    size = [h - l for l, h in zip(lo, hi)]
    if min(size) <= 0:
        return None
    centre = [(l + h) / 2 for l, h in zip(lo, hi)]
    return d.add(name, Pos(*centre) * Box(*size), material=material, mass_kg=0.0,
                 meta={"placeholder": True, "exploratory": True, **meta})


def build(layout: str = "ring", door_deg: float = 0.0, shelf_deployed: bool = False, z_t: float = Z_T,
          arm: str | None = None) -> Design:
    d = Design("arm_cell")
    d.exploratory = True
    state = C.CellState(z_t, door_deg, 0.0 if shelf_deployed else C.SHELF_TRAVEL, layout)
    _box(d, "bench", (-1100, -1000, -20), (1100, 600, 0), material="pla", role="bench plane")
    for o in C.obstacles(state):
        if isinstance(o, C.Box):
            name = "door_loop" if o.name == "door" else o.name
            _box(d, name, o.lo, o.hi, material="al6061" if o.name.startswith("printer") else "pla", role=o.name)
        else:   # door panel: an axis-aligned stand-in at 0 or 90 deg, else its bounding box (display only)
            x0, x1 = sorted((o.p0[0], o.p1[0]))
            y0, y1 = sorted((o.p0[1], o.p1[1]))
            _box(d, "door_panel", (x0, y0 - o.t / 2, o.z0), (x1 + (o.t if x1 - x0 < 1 else 0), y1 + o.t / 2, o.z1),
                 material="petg", role="V13 door, 3 mm polycarbonate (bounding box when partly open)")
    if arm:
        _add_skeleton(d, arm, z_t)
    return d


def _add_skeleton(d, kind, z_t):
    """Capsules of a spike candidate at the tab-engage pose, as thin boxes along each segment's bounding box."""
    import json
    from pathlib import Path

    import numpy as np

    from mechloop.arm import poses as PZ
    from mechloop.arm import reach as R
    res = json.loads((Path(__file__).resolve().parents[1] / "mechloop/data/arm/spike_results.json").read_text())
    r = res["results"][kind]
    maker = R.CANDIDATES[kind][0]
    keys = {"scara": ("bx", "by", "L1", "L2"), "cartesian": ("y_m",), "articulated5": ("bx", "by", "h0", "L2", "L3")}
    a = maker([r["params"][k] for k in keys[kind]], r["z_t"], PZ.build_poses())
    q = [x for x in r["reach"] if x["id"] == "A2_tab_engage"][0]["qs"][0]
    for c in a.capsules(np.array(q), PZ.TOOLS["hook_pin"]):
        lo = np.minimum(c.a, c.b) - c.r
        hi = np.maximum(c.a, c.b) + c.r
        _box(d, f"arm_{c.name}", lo, hi, role=f"{kind} skeleton (bounding box of a capsule)")


if __name__ == "__main__":
    dd = build()
    print(dd.name, len(dd.components), "boxes:", ", ".join(c.name for c in dd.components))
