"""Generate the first reference parts for supplier DFM/quote trials.

Each part is simple, made by us (no supplier CAD), and carries known features: some built to pass, some
built to break a published rule, so the suppliers' DFM feedback can be compared with our own checks.
Writes STEP (all parts) and DXF (flat laser part) plus MANIFEST.md into reference_parts/batch01/.
"""
from __future__ import annotations

import json
from pathlib import Path

from build123d import (Align, Axis, Box, BuildPart, BuildSketch, Circle, Cylinder, ExportDXF, Locations, Mode,
                       Plane, Polygon, Polyline, Pos, Rectangle, RectangleRounded, SlotCenterToCenter, Unit, chamfer,
                       export_step, extrude, fillet, make_face)

OUT = Path(__file__).resolve().parents[1] / "reference_parts" / "batch01"
IN = 25.4


def rp01_cnc_bracket_sharp():
    """6061-T6 block with a sharp-cornered pocket, a deep narrow slot and a blind tap-drill hole."""
    with BuildPart() as p:
        Box(80, 50, 20, align=(Align.CENTER, Align.CENTER, Align.MIN))
        # pocket 50 x 30 x 12 deep, vertical inside corners left sharp (R0): not millable with a round tool
        with Locations((0, 0, 20)):
            Box(50, 30, 12, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        # slot 3 mm wide, 18 mm long, 16 mm deep (depth = 5.3 x width)
        with Locations((0, 21, 20)):
            Box(18, 3, 16, align=(Align.CENTER, Align.CENTER, Align.MAX), mode=Mode.SUBTRACT)
        # 4 x 5.5 through holes
        with Locations((-34, -19, 10), (34, -19, 10), (-34, 19, 10), (34, 19, 10)):
            Cylinder(2.75, 20, mode=Mode.SUBTRACT)
        # blind 3.3 mm hole, 18 mm deep, in the end face (M4 tap drill; thread to be called out as M4x0.7, 10 deep)
        with Locations(Pos(40, 0, 10) * Plane.YZ.location):
            Cylinder(1.65, 36, mode=Mode.SUBTRACT)
    return p.part


def rp02_cnc_plate_clean():
    """6061-T6 plate with a radiused pocket and plain holes: built to pass (control part)."""
    with BuildPart() as p:
        Box(100, 60, 10, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with BuildSketch(Plane.XY.offset(10)):
            RectangleRounded(60, 30, 4)
        extrude(amount=-4, mode=Mode.SUBTRACT)
        with Locations((-42, -22, 5), (42, -22, 5), (-42, 22, 5), (42, 22, 5)):
            Cylinder(2.75, 10, mode=Mode.SUBTRACT)
        chamfer(p.edges().filter_by(Axis.Z).group_by(Axis.X)[0] + p.edges().filter_by(Axis.Z).group_by(Axis.X)[-1],
                length=1.0)
    return p.part


def rp03_sheet_channel():
    """5052-H32 0.090 in channel: one flange too short and one hole too close to a bend."""
    t = 0.090 * IN            # 2.286 mm
    r = t                     # inside bend radius about 1 x t
    w, h_long, h_short, depth = 60.0, 25.0, 6.0, 40.0
    # U channel: left flange 25 mm tall, right flange 6 mm tall (both outside), bends filleted
    with BuildPart() as p:
        Box(w, depth, t, align=(Align.CENTER, Align.CENTER, Align.MIN))
        with Locations((-w / 2, 0, 0)):
            Box(t, depth, h_long, align=(Align.MIN, Align.CENTER, Align.MIN))
        with Locations((w / 2, 0, 0)):
            Box(t, depth, h_short, align=(Align.MAX, Align.CENTER, Align.MIN))
        outer = p.edges().filter_by(Axis.Y).filter_by_position(Axis.Z, -0.01, 0.01)
        outer = [e for e in outer if abs(abs(e.center().X) - w / 2) < 0.01]
        fillet(outer, radius=r + t)
        inner = [e for e in p.edges().filter_by(Axis.Y)
                 if abs(e.center().Z - t) < 0.01 and abs(abs(e.center().X) - (w / 2 - t)) < 0.01]
        fillet(inner, radius=r)
        # 2 x 5.5 holes in the base, well placed
        with Locations((-12, 0, t / 2), (12, 0, t / 2)):
            Cylinder(2.75, t, mode=Mode.SUBTRACT)
        # 5.5 hole in the tall flange with its edge 1.5 mm above the bend tangent (too close to the bend)
        z_hole = t + r + 1.5 + 2.75
        with Locations(Pos(-w / 2 + t / 2, 0, z_hole) * Plane.YZ.location):
            Cylinder(2.75, t * 2, mode=Mode.SUBTRACT)
    return p.part, {"thickness_mm": round(t, 3), "inside_bend_radius_mm": round(r, 3)}


def rp04_laser_plate():
    """6061-T6 0.125 in flat plate: small hole, hole near edge, narrow slot, sharp inside corner."""
    t = 0.125 * IN            # 3.175 mm
    with BuildPart() as p:
        with BuildSketch() as s:
            RectangleRounded(120, 80, 3)
            # 4 x 5.5 corner holes, 8 mm from the edges (fine)
            with Locations((-52, -32), (52, -32), (-52, 32), (52, 32)):
                Circle(2.75, mode=Mode.SUBTRACT)
            # 1.2 mm hole: smaller than half the thickness
            with Locations((-20, 0)):
                Circle(0.6, mode=Mode.SUBTRACT)
            # 4.0 mm hole with only 0.8 mm of material to the edge
            with Locations((0, -40 + 0.8 + 2.0)):
                Circle(2.0, mode=Mode.SUBTRACT)
            # 1.0 mm wide slot, 20 mm long
            with Locations((20, 10)):
                SlotCenterToCenter(19, 1.0, mode=Mode.SUBTRACT)
            # L-shaped cutout with a sharp inside corner
            with Locations((25, -15)):
                Polygon((0, 0), (20, 0), (20, 6), (6, 6), (6, 20), (0, 20), align=None, mode=Mode.SUBTRACT)
        extrude(amount=t)
    return p.part, s.sketch, {"thickness_mm": round(t, 3)}


def rp05_fdm_clip():
    """PETG printed clip: a 0.6 mm wall, an unsupported flat overhang and a 1.5 mm pin."""
    with BuildPart() as p:
        Box(60, 20, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))           # base
        with Locations((-28, 0, 0)):
            Box(4, 20, 15, align=(Align.CENTER, Align.CENTER, Align.MIN))        # solid post
        with Locations((28, 0, 0)):
            Box(0.6, 20, 15, align=(Align.CENTER, Align.CENTER, Align.MIN))      # 0.6 mm wall (thin)
        with Locations((-26, 0, 12)):
            Box(20, 20, 3, align=(Align.MIN, Align.CENTER, Align.MIN))           # 20 mm flat overhang from post
        with Locations((0, 0, 3)):
            Cylinder(0.75, 8, align=(Align.CENTER, Align.CENTER, Align.MIN))     # 1.5 mm pin, 8 mm tall
    return p.part


PARTS = [
    dict(id="RP01", name="cnc_bracket_sharp", process="CNC milling", material="Aluminium 6061-T6",
         finish="as machined", qty=[1, 10],
         notes="Thread: the 3.3 mm blind hole in the +X end face is M4x0.7, 10 mm deep (state in the quote's "
               "thread callout if the site allows).",
         expect=["sharp internal pocket corners (R0) cannot be milled with a round tool",
                 "3 mm slot 16 mm deep: depth 5.3 x width, needs a long small cutter",
                 "blind tapped hole: check thread depth/drill depth rules"]),
    dict(id="RP02", name="cnc_plate_clean", process="CNC milling", material="Aluminium 6061-T6",
         finish="as machined", qty=[1, 10], notes="Control part: built to pass.",
         expect=["no issues expected (R4 pocket corners, 4 mm deep pocket, plain through holes)"]),
    dict(id="RP03", name="sheet_channel", process="Sheet metal: laser cut + bend",
         material="Aluminium 5052-H32, 0.090 in (2.29 mm)", finish="none", qty=[1, 10],
         notes="Inside bend radius about 1 x thickness.",
         expect=["6 mm flange (outside; 1.4 mm straight after the bend) is shorter than typical minimum flange for 0.090 in",
                 "5.5 mm hole in the tall flange 1.5 mm from the bend tangent: too close, will distort"]),
    dict(id="RP04", name="laser_plate", process="2D laser cutting",
         material="Aluminium 6061-T6, 0.125 in (3.18 mm)", finish="none", qty=[1, 10],
         notes="Upload the DXF where a site wants 2D; STEP otherwise. Units: mm.",
         expect=["1.2 mm hole: below the usual minimum hole (about 50-100 % of thickness)",
                 "4 mm hole with 0.8 mm to the edge: too close",
                 "1.0 mm slot: narrower than the usual minimum feature width",
                 "sharp inside corner of the L cutout (laser leaves a kerf radius; usually acceptable)"]),
    dict(id="RP05", name="fdm_clip", process="3D printing: FDM", material="PETG (or PLA)",
         finish="standard", qty=[1, 10], notes="Print flat on the 60 x 20 base.",
         expect=["0.6 mm wall: below a typical 0.8-1.2 mm minimum FDM wall",
                 "20 mm flat unsupported overhang: needs support",
                 "1.5 mm pin: fragile / below minimum feature for some services"]),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = {
        "RP01": rp01_cnc_bracket_sharp(),
        "RP02": rp02_cnc_plate_clean(),
    }
    part3, info3 = rp03_sheet_channel()
    built["RP03"] = part3
    part4, sketch4, info4 = rp04_laser_plate()
    built["RP04"] = part4
    built["RP05"] = rp05_fdm_clip()
    extra = {"RP03": info3, "RP04": info4}
    rows = []
    for meta in PARTS:
        part = built[meta["id"]]
        base = f'{meta["id"]}_{meta["name"]}'
        export_step(part, str(OUT / f"{base}.step"))
        files = [f"{base}.step"]
        if meta["id"] == "RP04":
            dxf = ExportDXF(unit=Unit.MM)
            dxf.add_shape(sketch4)
            dxf.write(str(OUT / f"{base}.dxf"))
            files.append(f"{base}.dxf")
        bb = part.bounding_box()
        rows.append({**meta, **extra.get(meta["id"], {}), "files": files,
                     "bbox_mm": [round(bb.size.X, 2), round(bb.size.Y, 2), round(bb.size.Z, 2)],
                     "volume_mm3": round(part.volume, 1)})
    (OUT / "manifest.json").write_text(json.dumps(rows, indent=2))
    lines = ["# Reference parts, batch 01", "",
             "Made by mechloop (our own geometry, no supplier CAD). Units: mm. Each part lists the issues we",
             "expect a supplier's DFM check to raise; RP02 is a control built to pass.", ""]
    for r in rows:
        lines += [f'## {r["id"]} {r["name"]}', "",
                  f'- Files: {", ".join(r["files"])}',
                  f'- Process: {r["process"]}', f'- Material: {r["material"]}', f'- Finish: {r["finish"]}',
                  f'- Quantities to quote: {", ".join(map(str, r["qty"]))}',
                  f'- Size: {" x ".join(map(str, r["bbox_mm"]))} mm',
                  f'- Notes: {r["notes"]}', "- Expected findings:"] + [f"  - {e}" for e in r["expect"]] + [""]
    (OUT / "MANIFEST.md").write_text("\n".join(lines))
    for r in rows:
        print(r["id"], r["files"], r["bbox_mm"], r["volume_mm3"])


if __name__ == "__main__":
    main()
