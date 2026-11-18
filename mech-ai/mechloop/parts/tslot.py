"""T-slot hardware for 20 x 20 slot-6 extrusion: the slot's section and drop-in T-nuts, as STAND-INS.

No supplier drawing of the slot or of a T-nut could be fetched (the suppliers' hosts are refused by the network proxy), so
nothing here is a faithful re-make. The slot section is measured from two community CAD files that are in the repository
and that disagree; the T-nut body is from one web-search snippet plus two guesses. Every figure, its source and its status
is in mechloop/parts/vendor/tslot_2020_hardware.json, and `assumed_dimensions()` lists the ones the screw-length checks
depend on. A supplier STEP saved as vendor_cad/inbox/TNUT-2020-M5.step (or -M3) replaces the display model.

  slot_2020()            the slot section the checks use (profile on the BOM) and the alternative section
  tnut_2020("M5")        drop-in T-nut, SKU TNUT-2020-M5 / TNUT-2020-M3
  slot_frame(...)        where a screw enters an extrusion's slot (depth of its tip, offset from the slot's centre line)
"""
from __future__ import annotations

import numpy as np
from build123d import Box, Pos

from . import Stock, _source, part, vendor_data

FAMILY = "tslot_2020_hardware"
TNUT_SIZES = ("M3", "M5")
SIM_SLOT_DEPTH = 5.0          # the plain slot of extrusion_2020's simulation solid
SIM_SLOT_WIDTH = 6.2


def slot_2020() -> dict:
    """The slot of a 2020 slot-6 extrusion as the checks use it: {"opening", "lip", "depth", "cavity_width", "profile",
    "status"} for the profile on the BOM, and under "alternative" the other section on file. Stand-in data: see the module
    docstring."""
    v = vendor_data(FAMILY)["slot"]
    u, a = v["used"], v["alternative"]
    out = {"opening": u["opening_mm"], "lip": u["lip_thickness_mm"], "depth": u["depth_mm"], "cavity_width": u["cavity_width_mm"],
           "profile": u["profile"], "source": u["source"], "status": u["status"],
           "sim_depth": SIM_SLOT_DEPTH, "sim_width": SIM_SLOT_WIDTH,
           "alternative": {"opening": a["opening_mm"], "lip": a["lip_thickness_mm"], "depth": a["depth_mm"],
                           "cavity_width": a["cavity_width_mm"], "profile": a["profile"], "source": a["source"], "status": a["status"]}}
    return out


def tnut_dims() -> dict:
    t = vendor_data(FAMILY)["tnut"]
    return {"span": t["span_across_slot_mm"]["value"], "width": t["width_along_slot_mm"]["value"],
            "height": t["overall_height_mm"]["value"], "neck": t["neck_height_mm"]["value"],
            "thread_length": t["thread_length_mm"]["value"]}


def assumed_dimensions() -> list[dict]:
    """Every assumed dimension the T-slot screw checks depend on: [{"what", "value_mm", "status"}]."""
    v = vendor_data(FAMILY)
    u, a, t = v["slot"]["used"], v["slot"]["alternative"], v["tnut"]
    return [
        {"what": "slot depth, face to floor (profile used)", "value_mm": u["depth_mm"], "status": u["status"] + "; " + u["source"].split(" (")[0]},
        {"what": "slot lip thickness (profile used)", "value_mm": u["lip_thickness_mm"], "status": u["status"]},
        {"what": "slot opening / cavity width (profile used)", "value_mm": [u["opening_mm"], u["cavity_width_mm"]], "status": u["status"]},
        {"what": "slot depth (alternative B-type section)", "value_mm": a["depth_mm"], "status": a["status"] + "; " + a["source"].split(" (")[0]},
        {"what": "slot lip thickness (alternative B-type section)", "value_mm": a["lip_thickness_mm"], "status": a["status"]},
        {"what": "T-nut overall height", "value_mm": t["overall_height_mm"]["value"], "status": t["overall_height_mm"]["status"]},
        {"what": "T-nut neck height (in the slot opening)", "value_mm": t["neck_height_mm"]["value"], "status": t["neck_height_mm"]["status"]},
        {"what": "T-nut thread length (body under the lips)", "value_mm": t["thread_length_mm"]["value"], "status": t["thread_length_mm"]["status"]},
        {"what": "T-nut span across the slot / width along it", "value_mm": [t["span_across_slot_mm"]["value"], t["width_along_slot_mm"]["value"]],
         "status": t["span_across_slot_mm"]["status"]},
        {"what": "clearance kept between a screw's tip and the slot floor", "value_mm": v["bottoming_margin_mm"]["value"], "status": v["bottoming_margin_mm"]["status"]},
        {"what": "thread engagement limits in a T-nut (x d)", "value_mm": [0.5, 0.8], "status": v["engagement_rule"]["status"]},
    ]


@part
def tnut_2020(size: str = "M5") -> Stock:
    """Drop-in T-nut for 2020 slot-6 extrusion, M3 or M5 (STAND-IN: dimensions assumed, see the module docstring).
    Drop-in type (post-assembly insertion, held by a spring ball or leaf): it goes into the slot through the opening
    anywhere along the extrusion, so it never has to be loaded from an end. Local frame: Z along the slot's outward
    normal, X along the slot; the face that bears on the underside of the slot's lips is Z=0, the body below it, the
    neck that stands in the slot opening above it. Place it `lip` mm below the extrusion's face."""
    if size not in TNUT_SIZES:
        raise ValueError(f"tnut_2020 size must be one of {TNUT_SIZES}")
    d = tnut_dims()
    body_h = d["height"] - d["neck"]
    shape = (Pos(0, 0, -body_h / 2) * Box(d["width"], d["span"], body_h)
             + Pos(0, 0, d["neck"] / 2) * Box(d["width"], 5.8, d["neck"]))
    thread_d = float(size[1:])
    mass = (d["width"] * d["span"] * body_h + d["width"] * 5.8 * d["neck"] - np.pi * (thread_d / 2) ** 2 * d["height"]) * 7.85e-6
    assumed = [f"{a['what']}: {a['value_mm']} mm ({a['status']})" for a in assumed_dimensions() if a["what"].startswith("T-nut")]
    return Stock(shape, f"TNUT-2020-{size}", f"Drop-in T-nut {size} for 2020 slot 6 (post-assembly insertion, spring-held)", float(mass),
                 material="steel", cost_usd=0.15,
                 ratings={"approximate": True, "insertion": "drop-in"},
                 interfaces={"thread_d": thread_d, "span": d["span"], "width": d["width"], "height": d["height"], "neck": d["neck"],
                             "body_height": body_h, "thread_length": d["thread_length"], "insertion": "drop-in",
                             "assumed": assumed},
                 detail=shape,
                 model={"kind": "proxy", "state": "stand-in", "inbox": [f"TNUT-2020-{size}"],
                        "source": "STAND-IN: a block and neck of assumed dimensions (search snippet 6 x 10.3 x 4.4 mm; neck 1.0 mm and thread "
                                  "length 3.4 mm guessed). Wanted: the supplier's STEP as vendor_cad/inbox/TNUT-2020-" + size + ".step",
                        "tolerance": {"volume_ratio": (0.3, 3.0), "mass_ratio": (0.2, 5.0)}},
                 source=_source(FAMILY, "proxy", f"drop-in T-nut {size}, 2020 slot 6",
                                unverified=("span", "width", "height", "neck", "thread_length", "mass_kg", "cost"),
                                note="stand-in: no supplier drawing was fetched; dimensions from a web-search snippet and two guesses"))


def slot_frame(ext, point, direction) -> dict | None:
    """Where a screw meets a 2020 extrusion's slot. `ext`: the placed extrusion component; `point`: a point on the screw's
    axis; `direction`: the way the thread points. Returns {"normal" (outward, world), "along" (the extrusion's axis, world),
    "depth" (of `point` below the face the screw enters through, mm; negative outside), "offset" (of the axis from the
    slot's centre line, mm), "along_mm" (position along the extrusion from its centre), "half_length"} or None when the
    part is not a placed slotted extrusion or the screw does not point into one of its four faces."""
    P = ext.meta.get("placement")
    itf = ext.meta.get("interfaces") or {}
    if P is None or "slot_width" not in itf:
        return None
    P = np.array(P, dtype=float)
    R, o = P[:, :3], P[:, 3]
    lp = R.T @ (np.array(point, dtype=float) - o)
    ld = R.T @ (np.array(direction, dtype=float) / np.linalg.norm(direction))
    ax = int(np.argmax(np.abs(ld)))
    if ax == 0 or abs(ld[ax]) < 0.999:
        return None
    n_local = np.zeros(3)
    n_local[ax] = -np.sign(ld[ax])
    other = 3 - ax                                   # the remaining transverse axis (1 <-> 2)
    bb = ext.shape.bounding_box()
    half = 0.5 * float(np.abs(R[:, 0]) @ np.array([bb.size.X, bb.size.Y, bb.size.Z]))
    return {"normal": R @ n_local, "along": R[:, 0], "depth": 10.0 - float(n_local[ax] * lp[ax]), "offset": float(lp[other]),
            "along_mm": float(lp[0]), "half_length": half}
