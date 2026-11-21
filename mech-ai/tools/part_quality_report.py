"""Markdown report from a part-quality result (mechloop.verifiers.part_quality --json).

    .venv/bin/python -m mechloop.verifiers.part_quality designs/printer_v12.py --json mechloop/data/part_quality/printer_v12.json
    .venv/bin/python tools/part_quality_report.py mechloop/data/part_quality/printer_v12.json docs/part_quality_v12.md

The generated tables are followed by the hand-written notes in NOTES (false positives seen, blind spots)."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict

PLAIN = {
    "not_one_solid": "The part is several solids (or none): a shop cannot make it as one piece.",
    "invalid_brep": "The CAD kernel's own validity check fails: exports and booleans on it may go wrong.",
    "open_shell": "The skin has a gap: it does not enclose a volume.",
    "non_manifold_edge": "Two bodies touch along a line only.",
    "internal_void": "A sealed cavity inside the material.",
    "tiny_edge": "Edges a few hundredths of a millimetre long: two cuts or blocks that nearly, but not exactly, line up.",
    "sliver_face": "A face a hair wide: the left-over of two features that nearly coincide.",
    "bad_volume": "Volume is zero, negative or larger than the bounding box: the solid is inside out or broken.",
    "mesh_not_watertight": "The STL a print shop or quoting tool would get has holes.",
    "self_intersection": "The surfaces cut through each other.",
    "sparse_bbox": "The part fills under 1 % of its bounding box: maybe a stray feature far from the body.",
    "thin_wall": "A wall or web thinner than the process can make reliably.",
    "near_coincident_faces": "Two faces of the part sit a hair apart across an air gap (a slit that should be closed or opened).",
    "small_step": "A ledge under 0.5 mm between two parallel faces: two features that should share one face.",
    "near_parallel_faces": "Two adjacent flat faces meet at a fraction of a degree: a face that should be one plane.",
    "weak_attachment": "A feature hangs on the body through a thin contact patch.",
    "hole_unused": "A hole or slot that nothing passes through: no screw, pin, shaft, spacer or tool. Left over from an earlier "
                   "version, or a part that is missing.",
    "outside_envelope": "Material outside the part's declared envelope or inside a keep-out.",
    "odd_dimension": "An overall size off the 0.1 mm grid (stock sheet gauges excepted): usually a derived or patched size.",
    "odd_hole_diameter": "A hole diameter off the 0.1 mm grid.",
    "nonstandard_hole": "A hole diameter that is no standard clearance, tap drill, insert, press, bearing or panel size.",
    "allowed_overlap_large": "Allowed to overlap another part, and does by more than a thread would: allow_overlap hides a real clash.",
    "screw_through_solid": "A screw runs through solid material: no hole is drawn for it.",
    "attachment_not_drawn": "Declared attached by hardware the join note names, but that hardware is not drawn.",
    "attachment_by_note": "Held only by a join note (press fit, bond, snap ...): fine when true, nothing in the model shows it.",
    "stock_hole_missing": "A purchased part's data lists holes its solid does not have.",
    "stock_hole_misaligned": "A purchased part's listed hole has no matching hole in the custom part it sits on.",
    "slot_nut_overlap": "Catalogue T-nuts overlap their extrusion.",
}
SEV = {"error": 0, "warning": 1, "info": 2}
CLASS_OF = {"broken": "broken", "weird": "weird", "odd": "odd dims", "purchased": "purchased", "other": "other"}

NOTES = r"""
## What the flags on the worst parts are (read in the design script)

- **part_duct** (`part_duct_shape`): built from overlapping boxes at absolute coordinates with hand offsets of 0.01 to
  0.6 mm (`y_rf - 0.01, y_rf + 0.61` "bridges chamber A to the riser", passages cut `+ 0.01` past a wall). Those offsets
  leave the 0.03 mm edges, 0.014 mm sliver faces, 0.03 mm ledges and a 0.10 mm wall the checks report: the textbook
  copy-forward patch artefact.
- **nut_keeper, _fl, _fr** (`nut_keeper_local`): the keeper's opening is the union of a circle, a slot and two rounded
  rectangles, then filleted; the profiles nearly meet and leave a 0.084 mm wide face.
- **z_motor_plate_fl/_fr** (`motor_plate_shape`): the outline is the convex hull of four 40-gon "circles", so its edge
  is short straight facets; two of them meet at 0.35 deg (and a 0.004 / 0.11 mm offset). A rounded outline drawn as
  tangent lines and arcs would have none of this (and round overall dimensions, cf. 80.994 mm).
- **x_endstop_carrier / y_endstop_carrier** (`endstop_carrier_local`): the 13 x 4.5 mm terminal slot comes within
  0.09 mm of an M3 clearance hole: a web no laser shop can cut.
- **estop_bracket**: the e-stop clash and the undrawn ring nut (below).
- **sfs_mount**: the filament sensor is held by two cable ties that are not drawn.

## Known true positives (from the owner's review)

- **estop / estop_bracket**: `allowed_overlap_large`, 2430 mm3. The e-stop's simulation solid
  (`estop_omron_a22e_m_02`, mechloop/parts/batch12.py) has its 34 x 34 mm switch block starting at the panel's front face, so
  the block passes straight through the 3.175 mm bracket; `d.allow_overlap("estop", "estop_bracket")` in `add_safety_chain`
  hid it from the interference check. The real part has a 22 mm threaded neck through the panel and the block behind it.
  Also `attachment_not_drawn`: the join says "held by its own ring nut through the 22.3 mm hole", but neither the ring nut
  nor the neck is modelled, so nothing in the model shows how it attaches. Both checks fire on it.
- **z_motor, z_motor_fl, z_motor_fr** (`leadscrew_motor_17e19_ab4`, mechloop/parts/batch7.py): `stock_hole_missing`.
  `interfaces["mount_holes_m3"]` lists four M3 holes (31 mm square, 4.5 mm deep) but the solid is a plain box and there is
  no detailed CAD. The four listed points do line up with the 3.4 mm holes in z_motor_plate*, so the plate is right and the
  motor model is the problem.

## False positives seen, and how the thresholds were set

- First pass, before tuning: 46 `hole_unused`, 361 `screw_through_solid`, 8 `allowed_overlap_large` per pair and
  32 `odd_dimension`. Causes and fixes:
  - concave quarter-round faces (inside corners of cut-outs, rounded pocket corners) were taken as holes: a hole must now
    be at least half a turn, and the two half-round ends of a slot are merged into one slot and probed along its length;
  - screws filling catalogue T-nuts and extrusions (stand-in solids drawn without threads): reported only where the
    material belongs to a custom part (none in v12); the count for purchased parts is in the metrics
    (`overlaps.screws_filling_cots_part`, 361);
  - nuts on screws, threaded rods and axles count as threads; T-nuts in their slot do not, and are summarised in one
    `slot_nut_overlap` line, since that is how the catalogue T-nuts are drawn rather than a defect of a custom part;
  - imperial sheet gauges (3.175, 6.35, 9.525, 1.88, 1.524, 2.032, 2.54, 4.75 mm) are stock sizes, not odd dimensions;
  - wall thickness measured on the triangulation is short by up to the meshing tolerance on curved walls (the
    0.8 mm spool sleeves read 0.79): the limit allows 2 x 0.02 + 0.01 mm;
  - a purchased part's listed hole in the mouth of the mate's hole is more than 1 mm from material: the mate's holes
    are now matched first; cameras use two of their four holes, so a listed hole is a warning only when NONE of the
    part's listed holes lines up with a hole in the part it is screwed to;
  - `pin_holes` of the D2F switch are where its terminals come out, not holes: keys with "pin" are skipped;
  - "integral screw" (the lead screw that is the motor's shaft) and a bearing's "inner ring" are not undrawn hardware;
    a hardware word that names one of the two parts ("held in the clip's channel" of led_clip_0) is that part;
  - the y_plate_left/right 4.8 x 10 mm slots looked empty: the Y belt's ends are looped through them, and belts are
    not solids. Belt ends (15 mm round the anchor point), belt spans (12 mm off the line between pulley centres) and
    cable ends (10 mm) now count as using a hole. With that, `hole_unused` finds nothing in v12. To make sure it still
    can, a run with estop_bracket_screw_0 and its Fastener record deleted flags that 5.5 mm hole (and the tests cover it).
- Likely still false or debatable in this run:
  - `allowed_overlap_large` on **foot_*/foot_*_nut** (79 mm3 each): the levelling foot's threaded stud and its jam nut,
    i.e. a thread, but the foot is not recognisable as a screw from its name or SKU;
  - `allowed_overlap_large` on **extruder / hotend** (28 mm3, "clamp"): two vendor models meeting in the heatsink
    groove; small, but it is a real overlap between two purchased models;
  - `attachment_not_drawn` on **filament_sensor / sfs_mount** (two cable ties) and **spool_axle / spool_plate** (nuts
    each side of the plate: the nuts are drawn but not joined to the plate): correct by the rule, the owner may accept
    a cable tie as drawn-by-note;

## What each check cannot catch

- Broken checks see only the simulation solid (`Component.shape`); a part whose displayed `detail` differs is not checked.
- `thin_wall` / `near_coincident_faces` sample up to 4000 triangle centres per part (area-weighted) along the surface
  normal: a thin web away from every sample, or one measured obliquely, can be missed; walls are compared with one
  process minimum (printed 0.8, machined 0.8, sheet the smaller of 1.0 and 0.95 x the sheet's thickness).
- `small_step` and `near_parallel_faces` look at planar faces only: a 0.1 mm step between two coaxial holes or between
  curved faces is not seen.
- `weak_attachment` looks only at planes where the part has flat faces of both senses (a feature standing on another)
  and judges the contact patch by width (< 0.8 mm) and share (< 15 %); a feature joined through a thin neck elsewhere is
  left to `thin_wall`. It found nothing in v12.
- `hole_unused` probes 3 x 7 points inside each hole against every other part's solid; a hole used by a cable or a hose
  (not modelled as solids), a hole for an optional part, or a lightening hole over 25 mm is not judged. A hole a screw
  axis runs through (tool access) counts as used.
- Feature-purpose beyond holes (a boss or a rib that carries nothing) is not checked: that needs the part's spec
  (docs/CAD_QUALITY_PLAN.md, fix 1).
- `outside_envelope` runs only where a part declares `meta["envelope"]` or `meta["keep_out"]`; no v12 part does.
- `odd_dimension` measures the part in the axes of its largest flat face; for a part with no flat face the world axes.
- None of this judges whether a part is a GOOD design (class (c)): that is the reviewer's job (plan, fix 3).
"""


def main(src: str, dst: str) -> None:
    j = json.load(open(src))
    F = j["findings"]
    M = j["metrics"]
    parts = M["parts"]
    by_part = defaultdict(list)
    for f in F:
        p = f["data"].get("part")
        by_part[p].append(f)
    custom = set(parts)
    L = []
    L.append(f"# Part quality: {j['design']}\n")
    L.append("Generated by `tools/part_quality_report.py` from `mechloop/data/part_quality/printer_v12.json` "
             "(`python -m mechloop.verifiers.part_quality designs/printer_v12.py --json ...`, "
             f"{j.get('seconds', '?')} s for the checks). The checks and thresholds are in the docstring of "
             "`mechloop/verifiers/part_quality.py`; the plan behind them is docs/CAD_QUALITY_PLAN.md. "
             "Severities: error = broken, warning = weird, info = odd dimension or for reading. "
             "Locations are world coordinates (mm) in the home pose.\n")
    n_err = sum(1 for p in custom if any(f["severity"] == "error" for f in by_part[p]))
    n_warn = sum(1 for p in custom if any(f["severity"] == "warning" for f in by_part[p]))
    n_clean = sum(1 for p in custom if not any(f["severity"] in ("error", "warning") for f in by_part[p]))
    L.append("## Summary\n")
    L.append("| | count |\n|---|---|")
    L.append(f"| custom (non-COTS) parts checked | {len(custom)} |")
    L.append(f"| parts with errors (broken) | {n_err} |")
    L.append(f"| parts with warnings (weird; incl. audit findings on the part) | {n_warn} |")
    L.append(f"| parts with neither | {n_clean} |")
    ov = M.get("overlaps", {})
    L.append(f"| allow_overlap pairs audited / with real overlap / flagged | {ov.get('pairs')} / {ov.get('nonzero')} / "
             f"{sum(1 for f in F if f['code'] == 'allowed_overlap_large')} |")
    L.append(f"| purchased-part hole lists checked | {M.get('stock_holes', {}).get('interfaces_checked')} |")
    L.append("")
    L.append("| check | class | severity | findings | parts / pairs |\n|---|---|---|---|---|")
    cnt = Counter((f["code"], f["severity"], f["data"].get("check_class", "")) for f in F)
    for (code, sev, cls), n in sorted(cnt.items(), key=lambda t: (SEV[t[0][1]], t[0][0])):
        np_ = len({f["data"].get("part") for f in F if f["code"] == code and f["severity"] == sev})
        L.append(f"| `{code}` | {CLASS_OF.get(cls, cls)} | {sev} | {n} | {np_} |")
    L.append("")
    L.append("Checks that found nothing in v12: " + ", ".join(
        f"`{c}`" for c in PLAIN if c not in {k[0] for k in cnt}) + ".\n")

    def score(p):
        fs = by_part[p]
        return (-sum(f["severity"] == "error" for f in fs), -sum(f["severity"] == "warning" for f in fs),
                -sum(f["severity"] == "info" for f in fs), p)

    flagged = sorted([p for p in custom if any(f["severity"] in ("error", "warning") for f in by_part[p])], key=score)
    L.append("## Worst parts\n")
    L.append("| # | part | process / material | errors | warnings | info | main flags |\n|---|---|---|---|---|---|---|")
    for i, p in enumerate(flagged, 1):
        fs = by_part[p]
        main = sorted({f["code"] for f in fs if f["severity"] != "info"}, key=lambda c: min(SEV[f["severity"]] for f in fs if f["code"] == c))
        L.append(f"| {i} | {p} | {parts[p]['process']} / {parts[p]['material']} | {sum(f['severity'] == 'error' for f in fs)} | "
                 f"{sum(f['severity'] == 'warning' for f in fs)} | {sum(f['severity'] == 'info' for f in fs)} | "
                 f"{', '.join(main)} |")
    L.append("")
    L.append("## Per part (worst first)\n")
    for p in sorted(custom, key=score):
        fs = sorted(by_part[p], key=lambda f: (SEV[f["severity"]], f["code"]))
        if not fs:
            continue
        L.append(f"### {p}\n")
        L.append(f"{parts[p]['process']} / {parts[p]['material']}\n")
        seen_plain = set()
        for f in fs:
            at = f["data"].get("at")
            msg = f["message"]
            if msg.startswith(p + ": "):
                msg = msg[len(p) + 2:]
            L.append(f"- **{f['severity']}** `{f['code']}`: {msg}" + (f" (at {at})" if at else ""))
            if f["code"] not in seen_plain and f["code"] in PLAIN:
                seen_plain.add(f["code"])
                L.append(f"  - {PLAIN[f['code']]}")
        L.append("")
    clean = sorted(p for p in custom if not by_part[p])
    L.append(f"Parts with no finding at all ({len(clean)}): {', '.join(clean)}.\n")

    L.append("## Allowed-overlap audit (every `d.allow_overlap` pair)\n")
    L.append(f"{ov.get('pairs')} pairs; {ov.get('nonzero')} overlap for real. A pair counts as a thread when one part is a "
             "screw (a `Fastener`), or a nut / insert on a screw, rod or axle, or the join says thread / insert / PEM / stud. "
             f"Everything else over {M['thresholds']['overlap_warn_mm3']} mm3 is flagged. Screws filling a purchased part's "
             f"material (stand-in T-nuts and extrusions drawn without threads): {ov.get('screws_filling_cots_part')}. "
             "Every pair's volume is in the JSON (`metrics.overlaps.rows`).\n")
    L.append("Largest overlaps that are not threads:\n")
    L.append("| a | b | overlap mm3 | declared max | join |\n|---|---|---|---|---|")
    import re

    for r in [r for r in ov.get("rows", []) if not r["threaded"] and not re.search(r"t-?nut|spring nut", r["join"].lower())][:15]:
        mx = "unlimited" if r["declared_max_mm3"] is None else f"{r['declared_max_mm3']:.0f}"
        L.append(f"| {r['a']} | {r['b']} | {r['volume_mm3']:.0f} | {mx} | {r['join'] or '-'} |")
    L.append("\n(T-nuts and spring nuts in their slots are left out of this table: see `slot_nut_overlap` below.)")
    L.append("")
    for f in F:
        if f["code"] in ("allowed_overlap_large", "slot_nut_overlap"):
            L.append(f"- **{f['severity']}** `{f['code']}`: {f['message']}")
    L.append("")
    L.append("## Joins with no drawn fastener\n")
    L.append("A join between two parts (neither of them a screw, nut, washer or T-nut) that no drawn fastener connects. A warning "
             "when the join note names hardware (nut, screw, clip, ring nut, cable tie ...) that is not drawn; info otherwise.\n")
    for f in sorted([f for f in F if f["code"] in ("attachment_not_drawn", "attachment_by_note")], key=lambda f: SEV[f["severity"]]):
        L.append(f"- **{f['severity']}** {f['message']}")
    L.append("")
    L.append("## Purchased parts: listed holes against the solid and the mating part\n")
    L.append("For every purchased part whose `interfaces` list hole positions (keys with \"hole\"): is there a hole in its "
             "simulation solid on each listed point (a concave cylinder whose axis passes within 0.5 mm), and if not, in its "
             "detailed CAD? And does each listed hole meet a hole (axis within 0.3 mm) in the custom part it sits on (within 1 mm)?\n")
    L.append("| part | SKU | key | listed | missing in solid | missing in detail | unmatched in mate |\n|---|---|---|---|---|---|---|")
    for r in M.get("stock_holes", {}).get("rows", []):
        mis = ", ".join(sorted({m["mate"] for m in r["misaligned"]}))
        L.append(f"| {r['part']} | {r['sku']} | {r['key']} | {r['listed']} | {r['missing_in_solid']} | "
                 f"{'-' if r['missing_in_detail'] is None else r['missing_in_detail']} | "
                 f"{len(r['misaligned'])}{' (' + mis + ')' if mis else ''} |")
    L.append("")
    for f in sorted([f for f in F if f["code"].startswith("stock_hole")], key=lambda f: SEV[f["severity"]]):
        if f["severity"] == "warning":
            L.append(f"- **{f['severity']}** {f['message']}")
    L.append("")
    L.append(NOTES.strip() + "\n")
    open(dst, "w").write("\n".join(L))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
