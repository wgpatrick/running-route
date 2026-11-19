"""T-slot hardware for 20 x 20 slot-6 extrusion (Misumi HFS5 series): the slot's section and drop-in T-nuts.

Both are read from Misumi's dimensioned catalogue drawings (MISUMI USA 2019 catalogue p.2686 and p.2717, fetched
2026-11-19, copies in vendor_docs/): the slot is 6 wide, 2 of lip, 4 from lip to floor, 12 across the cavity; the nut is
HNTAJ5, 10 x 8 x 3.2 with a 2.4 mm body and a 5.8 mm neck. The T-nut part is a re-make from that drawing (every
dimension used, nothing guessed, two un-dimensioned features left out), not supplier CAD. Every figure, its source and
its status is in mechloop/parts/vendor/tslot_2020_hardware.json, and `assumed_dimensions()` lists what the screw-length
checks still take on trust. A supplier STEP saved as vendor_cad/inbox/TNUT-2020-M5.step (or -M3) replaces the display model.

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
           # v11: the cavity's real shape (Misumi's STEP): full width only just under the lips, then 45 degree walls
           "cavity_full_depth": u.get("cavity_full_width_below_lip_mm"), "floor_width": u.get("floor_width_mm"),
           "sim_depth": SIM_SLOT_DEPTH, "sim_width": SIM_SLOT_WIDTH,
           # other slot + T-nut geometries on file, each judged and reported beside the one used (data, not constants):
           # the B-type community section, and McMaster's measured 5 mm-slot rail with its own T-nuts
           "alternatives": [{"name": g["name"], "report_as": g.get("report_as", "warning"), "opening": g["opening_mm"], "lip": g["lip_mm"],
                             "depth": g["depth_mm"], "cavity_width": g["cavity_width_mm"], "status": g["status"],
                             "tnut": {k: {"thread_start": t["thread_start_mm"], "thread_length": t["thread_length_mm"]}
                                      for k, t in g["tnut"].items()}}
                            for g in vendor_data(FAMILY)["geometries"]["alternatives"]]}
    return out


def tnut_dims() -> dict:
    t = vendor_data(FAMILY)["tnut"]
    return {"length": t["length_along_slot_mm"]["value"], "span": t["span_across_slot_mm"]["value"],
            "height": t["overall_height_mm"]["value"], "body": t["body_height_mm"]["value"], "neck": t["neck_height_mm"]["value"],
            "neck_width": t["neck_width_mm"]["value"], "thread_length": t["thread_length_mm"]["value"],
            "torque": dict(t["reference_tightening_torque_nm"])}


def assumed_dimensions() -> list[dict]:
    """Every figure the T-slot screw checks depend on, with where it comes from: [{"what", "value_mm", "status"}]. Since
    2026-11-19 the slot and the T-nut are read from Misumi's dimensioned catalogue drawings; what is still ours is listed
    as DERIVED or as our reading."""
    v = vendor_data(FAMILY)
    u, a, t = v["slot"]["used"], v["slot"]["alternative"], v["tnut"]
    return [
        {"what": "slot depth, face to floor", "value_mm": u["depth_mm"], "status": u["status"] + " (2 + 4)"},
        {"what": "slot lip thickness", "value_mm": u["lip_thickness_mm"], "status": u["status"]},
        {"what": "slot opening / cavity width", "value_mm": [u["opening_mm"], u["cavity_width_mm"]], "status": u["status"]},
        {"what": "T-nut overall height / height of the body under the lips", "value_mm": [t["overall_height_mm"]["value"], t["body_height_mm"]["value"]],
         "status": "READ from the maker's catalogue drawing of HNTAJ5 (fetched 2026-11-19)"},
        {"what": "T-nut thread length", "value_mm": t["thread_length_mm"]["value"], "status": "READ: " + t["thread_length_mm"]["status"]},
        {"what": "T-nut length along the slot / span across it / neck width", "value_mm": [t["length_along_slot_mm"]["value"], t["span_across_slot_mm"]["value"], t["neck_width_mm"]["value"]],
         "status": "READ from the same drawing"},
        {"what": "how the T-nut seats (body against the lips' underside, neck up in the opening)", "value_mm": None, "status": "OUR READING: " + t["read_by_us"]},
        {"what": "tolerances of the slot and the nut", "value_mm": None, "status": "NOT GIVEN on either drawing"},
        {"what": "that the extrusion bought is Misumi HFS5-2020 or has the same slot", "value_mm": None,
         "status": "ASSUMED. Another make's 2020 slot-6 profile on file is " + f"{a['depth_mm']} mm deep with a {a['lip_thickness_mm']} mm lip ({a['status']})"},
        {"what": "clearance kept between a screw's tip and the slot floor", "value_mm": v["bottoming_margin_mm"]["value"], "status": v["bottoming_margin_mm"]["status"]},
        {"what": "thread engagement limits in a T-nut (x d)", "value_mm": [0.5, 0.8], "status": v["engagement_rule"]["status"]},
    ]


@part
def tnut_2020(size: str = "M5") -> Stock:
    """Drop-in T-nut for 2020 slot-6 extrusion, M3 or M5: Misumi HNTAJ5 ("Post-Assembly Insertion Short Nut" for the HFS5
    series), re-made from the dimensioned drawing in Misumi's catalogue: 10 long, 8 wide, 3.2 high, a 2.4 mm body under
    the slot's lips and a 5.8 mm wide neck in the opening, threaded through. It goes into the slot through the opening
    anywhere along the extrusion (never from an end) and a leaf spring holds it. The chamfers and the leaf spring are
    drawn in the catalogue without dimensions and are left out. Local frame: Z along the slot's outward normal, X along
    the slot; the face that bears on the underside of the lips is Z=0, the body below it, the neck above it. Place it
    `lip` mm below the extrusion's face."""
    if size not in TNUT_SIZES:
        raise ValueError(f"tnut_2020 size must be one of {TNUT_SIZES}")
    from build123d import Cylinder

    d = tnut_dims()
    shape = (Pos(0, 0, -d["body"] / 2) * Box(d["length"], d["span"], d["body"])
             + Pos(0, 0, d["neck"] / 2) * Box(d["length"], d["neck_width"], d["neck"]))
    thread_d = float(size[1:])
    hole = Pos(0, 0, (d["neck"] - d["body"]) / 2) * Cylinder(thread_d / 2, d["height"])
    detail = shape - hole                       # the display model has the thread's hole; the simulation solid does not
    mass = float(detail.volume) * 7.85e-6
    v = vendor_data(FAMILY)
    drawing = v["tnut"]["source"]
    return Stock(shape, f"TNUT-2020-{size}", f"Drop-in T-nut {size} for 2020 slot 6: Misumi HNTAJ5-{size[1:]} (post-assembly insertion short nut)",
                 mass, material="steel", cost_usd=0.5,
                 ratings={"approximate": True, "insertion": "drop-in", "maker_part": f"MISUMI HNTAJ5-{size[1:]}",
                          **({"reference_tightening_torque_nm": d["torque"][size]} if size in d["torque"] else {}),
                          "left_out_of_the_model": list(v["tnut"]["left_out_of_the_model"])},
                 interfaces={"thread_d": thread_d, "length": d["length"], "span": d["span"], "height": d["height"], "neck": d["neck"],
                             "neck_width": d["neck_width"], "body_height": d["body"], "thread_length": d["thread_length"],
                             # the thread starts at the top of the neck: this far above the face that bears on the lips
                             "thread_offset": -d["neck"], "insertion": "drop-in"},
                 detail=detail,
                 model={"kind": "generated to standard", "inbox": [f"TNUT-2020-{size}", f"HNTAJ5-{size[1:]}"],
                        "remade_from": drawing,
                        "source": "re-made from the maker's dimensioned drawing: " + drawing + ". All six dimensions are in the model and "
                                  "nothing is guessed; the chamfers, the leaf spring and the countersink ring are drawn there without "
                                  "dimensions and are left out. Misumi's own STEP is still wanted (vendor_cad/inbox/TNUT-2020-" + size + ".step)",
                        "tolerance": {"volume_ratio": (0.8, 1.6), "mass_ratio": (0.5, 2.0)}},
                 source=_source(FAMILY, "vendor", f"MISUMI HNTAJ5-{size[1:]}", unverified=("mass_kg", "cost"),
                                note="dimensions from the maker's catalogue drawing (copy in vendor_docs/); mass from the drawn solid; price not read"))


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
