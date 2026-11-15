"""Detail models for the catalog parts: which STEP file, how it is brought into the part's local frame, and what
the proxy-match check must find in it. One function per part family; each returns (shape or None, model record).

The files are in vendor_cad/ (origins and licences in vendor_cad/SOURCES.md). When a file is missing the part simply
has no detail model ("proxy"). Frames are documented per function as: file axes -> part axes.
"""
from __future__ import annotations

from . import vendor_cad as vc
from .vendor_cad import hole_feature

FCL = "FreeCAD-library (community, CC-BY 3.0)"


def _rec(kind: str, file: str | None, source: str, **extra) -> dict:
    return {"kind": kind, "source": source, **({"file": f"vendor_cad/{file}"} if file else {}), **extra}


def _file(name: str):
    return vc.find_file(name)


# ------------------------------------------------------------------ motors
# StepperOnline's own STEP files (hand-downloaded, free account; licence not stated: vendor_cad/SOURCES.md), by
# catalogue length: file stem, the vendor part the file is of, and how the file is brought into the part frame.
#   17HS13-0404S1: rear face Z=0, mounting face Z=33.0, shaft +Z, leads leave towards -Y.
#   17HS19-2004S1: mounting face Z=0, shaft towards -Z, body to Z=48, leads leave towards -Y.
NEMA17_VENDOR_STEP = {34: dict(file="17HS13-0404S1", of="17HS13-0404S1", rot=(0, 0, 90), pos=(0, 0, -33.0), body=33.0),
                      48: dict(file="17HS19-2004S1", of="17HS19-2004S1", rot=(180, 0, -90), pos=(0, 0, 0), body=48.0)}
# Lead exit of those two motors, measured in the vendor STEP: four leads in a 4.0 x 2.5 mm bundle leaving one side face
# 4.5 to 7.0 mm from the rear. The STEP draws them as straight rigid stubs 18 mm long; they are flexible, so the detail
# model keeps 5.7 mm of them (room for the leads to turn) and the simulation solid has a block of that size.
NEMA17_LEAD_EXIT = dict(x0=21.15, x1=26.85, half_y=2.0, z_from_rear=(4.5, 7.0))   # "rear" = the STEP's rear face (body below)


def nema17(length: int, v: dict, part_number: str):
    """34 and 48 mm: StepperOnline's own STEP of the motor (see NEMA17_VENDOR_STEP), lead stubs cut to 5.7 mm.
    40 and 60 mm: community NEMA 17 (40 mm body, connector on one side) brought to the catalogue body and shaft length.
    Community file: rear face Z=0, mounting face Z=40.1, shaft along +Z, connector on +X.  Part: file Z - body length."""
    vs = NEMA17_VENDOR_STEP.get(length)
    fv = _file(vs["file"]) if vs else None
    if fv is not None:
        same = "" if vs["of"] == part_number else (f" (the file is of the {vs['of']}: the same motor as the catalogue's {part_number} "
                                                   "with a 1 m lead and connector instead of 300 mm bare leads)")
        rec = _rec("vendor CAD", f"{vs['file']}.step",
                   f"STEPPERONLINE {vs['of']}.STEP from the product page (hand-downloaded, free account; licence not stated){same}; "
                   "lead stubs cut 5.7 mm from the side face",
                   inbox=[part_number, f"{part_number}.STEP"],
                   features=[hole_feature("shaft_dia", (0, 0, v["shaft_length_mm"] - 3), v["shaft_dia_mm"], (0, 0, 1), tol_dia=0.05),
                             hole_feature("pilot_dia", (0, 0, 0.75), v["pilot_dia_mm"], (0, 0, 1), tol_dia=0.1)],
                   protrusions={"zmin": (-(length - vs["body"]), f"the vendor CAD draws the body {vs['body']:g} mm long; the "
                                         f"simulation solid keeps the drawing's maximum, {length} mm")} if length != vs["body"] else {},
                   notes=["the pilot boss is 2.0 mm high in the STEP (1.5 mm straight and a 0.5 mm chamfer), as on the drawing",
                          "the STEP has no connector block: four leads leave one side face 4.5 to 7.0 mm from the rear (drawn as rigid "
                          "18 mm stubs, cut to 5.7 mm here because they are flexible); the simulation solid has the same small block on +X",
                          "frame corners are chamfered in the model; the simulation solid keeps the full 42.3 mm square",
                          "mounting holes are drawn at the tap-drill size (2.5 mm), 4.5 mm deep"])

        def build_vendor():
            from build123d import Box, Pos

            s = vc.frame(vc.solids_of(vc.load_step(fv)), tuple(vs["rot"]), tuple(vs["pos"]))
            cut = s - Pos(NEMA17_LEAD_EXIT["x1"] + 50.0, 0, 0) * Box(100.0, 200.0, 400.0)
            return vc.bake(vc.solids_of(cut))

        return vc.cached(f"nema17_vendor:{length}:{vs['rot']}:{vs['pos']}:{NEMA17_LEAD_EXIT['x1']}", [fv], build_vendor), rec
    f = _file("nema17_40mm_with_connector")
    rec = _rec("community CAD", "nema17_40mm_with_connector.step",
               f"{FCL}: NEMA-17_Stepper_Motor_40mm_with_connector.step, body cut at the stator and brought to {length} mm, "
               f"shaft to {v['shaft_length_mm']:g} mm (no StepperOnline STEP for {part_number} is in vendor_cad/)",
               inbox=[part_number, f"{part_number}.STEP"],
               features=[hole_feature("shaft_dia", (0, 0, v["shaft_length_mm"] - 3), v["shaft_dia_mm"], (0, 0, 1), tol_dia=0.05),
                         hole_feature("pilot_dia", (0, 0, 1.0), v["pilot_dia_mm"], (0, 0, 1), tol_dia=0.1)],
               notes=["pilot boss is 1.6 mm high in the community model, 2.0 mm on the StepperOnline drawing",
                      "frame corners are chamfered in the model; the simulation solid keeps the full 42.3 mm square"])
    if f is None:
        return None, rec

    def build():
        s = vc.solids_of(vc.load_step(f))
        s = vc.stretch(s, "Z", 20.0, length - 40.1)
        s = vc.stretch(s, "Z", length + 12.0, v["shaft_length_mm"] - 20.0)
        return vc.frame(s, pos=(0, 0, -length))

    return vc.cached(f"nema17:{length}:{v['shaft_length_mm']}", [f], build), rec


NEMA17_CONNECTOR = dict(x0=21.15, x1=26.85, half_y=8.6, z_from_rear=(1.5, 9.5))   # measured in the community model


# ------------------------------------------------------------------ linear guides
def mgn12_rail(length: float, v: dict, holes: list):
    """Section of the community MGN12 rail swept to length, holes drilled to the Hiwin table (the community model has
    the same holes: 3.5 through, 6 x 4.5 counterbore, 25 pitch). File: along Z, width X, height Y (base Y=0).
    Part: file Z -> X, file X -> Y, file Y -> Z."""
    f = _file("mgn12_rail_100mm")
    rec = _rec("community CAD", "mgn12_rail_100mm.step",
               f"{FCL}: LinearSlide-MGN12-Rail.step (100 mm sample): its section swept to {length:g} mm, holes to the MG table",
               inbox=[f"MGNR12R{int(length)}", "MGNR12"], no_auto_features=True,
               features=[hole_feature(f"mount_holes_m3[{i}]", (x, 0, 1.0), v["bolt_hole_d_mm"], (0, 0, 1), tol_dia=0.05)
                         for i, (x, _, _) in enumerate(holes)]
               + [hole_feature("counterbore[0]", (holes[0][0], 0, 7.0), v["counterbore_D_mm"], (0, 0, 1), tol_dia=0.05)])
    if f is None:
        return None, rec

    def build():
        from build123d import Box, Cylinder, Pos, extrude

        s = vc.frame(vc.solids_of(vc.load_step(f)), rot=(90, 0, 90))      # file Z -> X, X -> Y, Y -> Z
        thin = s & (Pos(22.5, 0, 4) * Box(0.02, 40, 40))                  # between the holes at 10 and 35
        face = max((q for q in thin.faces() if abs(abs(tuple(q.normal_at())[0]) - 1) < 1e-6), key=lambda q: q.center().X)
        bar = extrude(Pos(-face.center().X - length / 2, 0, 0) * face, length, dir=(1, 0, 0))
        hr, cb = v["height_HR_mm"], v["counterbore_depth_h_mm"]
        for x, _, _ in holes:
            bar -= Pos(x, 0, hr / 2) * Cylinder(v["bolt_hole_d_mm"] / 2, hr + 1)
            bar -= Pos(x, 0, hr - cb / 2 + 0.5) * Cylinder(v["counterbore_D_mm"] / 2, cb + 1)
        return vc.bake(bar)

    return vc.cached(f"mgn12_rail:{length}", [f], build), rec


def mgn12h(v: dict):
    """Community MGN12H block. File: length along Z (0..45.4), width X, height Y (3..13 above the rail base).
    Part: file Z -> X (centred), file X -> Y, file Y -> Z."""
    f = _file("mgn12h_block")
    rec = _rec("community CAD", "mgn12h_block.step", f"{FCL}: LinearSlide-MGN12H.step", inbox=["MGN12H"],
               mates_with=("MGN12-R",),   # the model's ball rows are drawn 25 mm^3 into the community rail's grooves
               notes=["the community model draws the four M3 threads 3.5 mm deep, the same as Hiwin's Table 3.79 (M3 x 3.5)",
                      "end caps are not drawn, so the catalogue's L1 (32.4 mm body without end caps) is not in the model"])
    if f is None:
        return None, rec
    return vc.cached("mgn12h", [f], lambda: vc.frame(vc.solids_of(vc.load_step(f)), rot=(90, 0, 90),
                                                      pos=(-v["length_L_mm"] / 2, 0, 0))), rec


def extrusion_2020(length: float):
    """Section of a community 20x20 slot-6 profile swept to length. File: along Y, section in XZ.
    Part: file Y -> X, file X -> Y, file Z -> Z (the section has four-fold symmetry)."""
    f = _file("profile_2020_slot6")
    rec = _rec("community CAD", "profile_2020_slot6.step",
               f"{FCL}: Profile-20x20-B-Type_Slot6_A.step: its section swept to {length:g} mm",
               inbox=[f"HFS5-2020-{int(length)}", "HFS5-2020"],
               tolerance={"volume_ratio": (0.6, 1.7)},
               notes=["community section: area 174.3 mm^2 (0.47 kg/m at 2700 kg/m^3; catalogue 0.45 kg/m), slot opening 6.0 mm "
                      "(simulation solid: 6.2 mm wide, 5 mm deep plain slots, no T cavity)"])
    if f is None:
        return None, rec

    def build():
        from build123d import Box, Pos, extrude

        s = vc.frame(vc.solids_of(vc.load_step(f)), rot=(0, 0, -90))      # file Y -> X, file X -> -Y
        thin = s & (Pos(-190, 0, 0) * Box(0.02, 40, 40))
        face = max((q for q in thin.faces() if abs(abs(tuple(q.normal_at())[0]) - 1) < 1e-6), key=lambda q: q.center().X)
        return vc.bake(extrude(Pos(-face.center().X - length / 2, 0, 0) * face, length, dir=(1, 0, 0)))

    return vc.cached(f"extrusion_2020:{length}", [f], build), rec


def corner_bracket_2020():
    """Community cast corner bracket (20 x 20 legs, 17 wide). File: width along X (0..17), one leg face on Y=0 (body in
    -Y), the other on Z=0 (body in +Z), 1 mm locating nubs proud of both faces.
    Part: file Z -> X, file -Y -> Y, file X -> Z (centred)."""
    f = _file("corner_bracket_2020")
    rec = _rec("community CAD", "corner_bracket_2020.step", f"{FCL}: 2020_corner_bracket-Corner.step",
               inbox=["BRKT-2020"], protrusions={"xmin": (1.0, "locating nubs that sit in the T-slot"),
                                                 "ymin": (1.0, "locating nubs that sit in the T-slot")},
               tolerance={"volume_ratio": (0.6, 1.9), "mass_ratio": (0.2, 3.0)})
    if f is None:
        return None, rec

    def build():
        import numpy as np

        from ..geom import location_from_matrix

        T = np.eye(4)
        T[:3, :3] = np.array([[0, 0, 1], [0, -1, 0], [1, 0, 0]], dtype=float)   # rows: part X, Y, Z from file x, y, z
        T[:3, 3] = (0, 0, -8.5)
        return vc.bake(vc.solids_of(vc.load_step(f)).moved(location_from_matrix(T)))

    return vc.cached("corner_bracket_2020", [f], build), rec


# ------------------------------------------------------------------ transmission
def gt2_idler(teeth: int, bore: float, belt_width: float):
    """Community 20-tooth-size idler for 6 mm belt (smooth running surface; the tooth form is not drawn).
    File: axis Z, flanges at Z = 0.1 .. 8.4. Part: same frame."""
    rec = _rec("community CAD", "gt2_20t_idler_5mm_bore.step",
               f"{FCL}: GT2_20T_Smooth_5mm_Bore.step (smooth idler of the same size; teeth not drawn)",
               inbox=[f"GT2-IDLER-{teeth}T-B{bore:g}-W{belt_width:g}"],
               features=[hole_feature("bore", (0, 0, 4.0), bore, (0, 0, 1), tol_dia=0.05)])
    f = _file("gt2_20t_idler_5mm_bore") if (teeth, bore, belt_width) == (20, 5.0, 6.0) else None
    if f is None:
        return None, {"inbox": rec["inbox"]}
    return vc.cached("gt2_idler_20_5_6", [f], lambda: vc.frame(vc.solids_of(vc.load_step(f)))), rec


COUPLER_STEP_AXIS = (-1.378, -0.015)       # axis of the vendor STEP in its own frame; the 5 mm end is at file Z = 28.256


def shaft_coupler(od: float, length: float):
    """StepperOnline's own STEP of the MH2025-5-8 jaw coupling: two clamp hubs, the elastomer spider and two M3 x 10
    clamp screws (five solids, kept as an assembly). File: axis along Z at COUPLER_STEP_AXIS, 8 mm bore end at
    Z=3.156, 5 mm bore end at Z=28.256.  Part: axis on Z, 5 mm bore end on Z=0 (file turned 180 deg about X)."""
    f = _file("COUPLER-5x8")
    rec = _rec("vendor CAD", "COUPLER-5x8.step",
               "STEPPERONLINE MH2025-5-8.STEP from the product page (hand-downloaded, free account; licence not stated): hubs, "
               "spider and clamp screws, re-centred on the part axis",
               inbox=["MH2025-5-8"], assembly=True, no_auto_features=True,
               features=[hole_feature("bore_a", (0, 0, 3.0), 5.0, (0, 0, 1), tol_dia=0.05),
                         hole_feature("bore_b", (0, 0, length - 3.0), 8.0, (0, 0, 1), tol_dia=0.05)],
               tolerance={"volume_ratio": (0.6, 1.7)},
               notes=["the STEP is 25.1 mm long (drawing: 25)",
                      "each bore is 7.3 mm of cylinder behind a 0.2 mm chamfer; past it the hub is open to the spider. A 5 mm shaft "
                      "meets the spider's web 12.05 mm in, an 8 mm shaft meets the spider 8.6 mm in (its centre hole is 7 mm)"])
    if f is None:
        return None, rec
    ax, ay = COUPLER_STEP_AXIS
    return vc.cached("shaft_coupler_5x8:2", [f],
                     lambda: vc.frame(vc.solids_of(vc.load_step(f)), rot=(180, 0, 0), pos=(0, 0, 28.256), pre=(-ax, -ay, 0.0))), rec


def t8_nut():
    """Community T8 flanged nut. File: axis Z, barrel Z = 0..15, flange Z = 1.5..5. Part: file Z - 1.5 (flange
    bottom on Z=0, a 1.5 mm stub of the barrel below it)."""
    f = _file("t8_flange_nut")
    rec = _rec("community CAD", "t8_flange_nut.step", f"{FCL}: T8_Flange_nut.step", inbox=["T8-NUT"],
               mates_with=("T8x",),      # its thread form overlaps the lead screw's plain cylinder by design
               features=[hole_feature("barrel_dia", (0, 0, 10.0), 10.2, (0, 0, 1), tol_dia=0.25),
                         hole_feature("flange_dia", (0, 0, 2.0), 22.0, (0, 0, 1), tol_dia=0.1)])
    if f is None:
        return None, rec
    return vc.cached("t8_nut", [f], lambda: vc.frame(vc.solids_of(vc.load_step(f)), pos=(0, 0, -1.5))), rec


# ------------------------------------------------------------------ fans, switches
def fan(size: int):
    """30 mm: fan from the Voron 0.2 assembly; 40 mm: FreeCAD-library. Both files: axis Z, Z = 0..10, centred in XY.
    Part: file Z - 5."""
    name, src = {30: ("voron0_3010_axial_fan", "Voron-0 V0.2R1 master assembly STEP, part '3010 DC Axial Fan' (community, GPL-3.0)"),
                 40: ("fan_40x40x10", f"{FCL}: fan-40x40mm.step")}[size]
    f = _file(name)
    pitch = {30: 24.0, 40: 32.0}[size]
    rec = _rec("community CAD", f"{name}.step", src, inbox=[f"FAN-{size}10"], tolerance={"volume_ratio": (0.5, 1.9)},
               assembly=True, no_auto_features=True,
               features=[hole_feature(f"mount_holes_m3[{i}]", (x, y, 0), 3.0, (0, 0, 1), dia_range=(1.0, 1.5))
                         for i, (x, y) in enumerate((a, b) for a in (-pitch / 2, pitch / 2) for b in (-pitch / 2, pitch / 2))],
               notes=["40 mm model: the screw holes are drawn 4.3 mm (M4 size); the catalogue lists them as M3 holes"] if size == 40 else [])
    if f is None:
        return None, rec
    return vc.cached(f"fan:{size}", [f], lambda: vc.frame(vc.solids_of(vc.load_step(f)), pos=(0, 0, -5.0))), rec


def _d2f() -> dict:
    """OMRON's D2F data sheet figures for the hinge-lever models (mechloop/parts/vendor/omron_d2f.json)."""
    import json
    from pathlib import Path

    return json.loads((Path(__file__).parent / "vendor" / "omron_d2f.json").read_text(encoding="utf-8"))["hinge_lever_models"]


_D2F = _d2f()
ENDSTOP = {   # the endstop module, part frame (see parts.endstop_switch)
    "pcb": (20.0, 12.5, 1.6), "pcb_y": (-7.5, 5.0), "holes": ((-7.5, -4.2), (7.5, -4.2)), "hole_d": 3.2,
    # switch body (D2F size): 12.8 long, 6.55 high (Y), 5.8 thick (Z, lying on the board). It overhangs the board's
    # +Y edge by 1.65 mm so that its terminals clear the mounting holes.
    "shift_y": 1.6, "body_x": (-6.4, 6.4), "body_y": (0.1, 6.65), "body_z": (1.6, 7.4), "hole_line_y": 1.6,
    "lever_tip_free": (-9.4, 11.59, 4.5),      # as drawn in the community model: 10.0 mm from the mounting-hole line (Omron: FP 10 max)
    # OMRON D2F data sheet, hinge lever models (vendor_docs/ENDSTOP-MICRO_datasheet.pdf p.4): operating position
    # 6.8 +/-1.5 mm from the mounting-hole line. Until 2026-11-15 this was 10.6 (9.0 from the hole line), a recalled
    # figure that was really the FREE position.
    "operate_y": 1.6 + _D2F["operating_position_mm"], "operate_tol": _D2F["operating_position_tol_mm"],
    "overtravel_min": _D2F["overtravel_min_mm"][0], "movement_differential": _D2F["movement_differential_max_mm"][0],
    "operating_force_n": _D2F["operating_force_max_n"][0], "free_max_y": 1.6 + _D2F["free_position_max_mm"],
    # Terminal row and length: those of the GENERATED carrier board (no maker), kept. An Omron right-angled D2F (-A) on a
    # board would have its legs 2.6 +/-0.2 mm below the body bottom (here 0.9) and 1.5 mm through the board (here 2.62).
    "pins": ((-5.08, -0.8), (0.0, -0.8), (5.08, -0.8)), "pins_z": -2.62,
    "omron_angled_terminals": {"row_below_body_bottom_mm": 2.6, "row_tol_mm": 0.2, "through_a_1.6mm_board_mm": 1.5},
}


def endstop():
    """Generic lever-microswitch endstop: a community model of a D2F-size hinge-lever switch (PCB terminals) on a
    plain 20 x 12.5 x 1.6 board with two M3 holes (the board is generated; no maker publishes one).
    Switch file: length X, thickness Y (terminals leave towards -Y), height Z (lever above +Z, tip towards +X).
    Part: file X -> -X, file Z -> Y (+1.6), file Y -> Z (+4.5)."""
    f = _file("microswitch_spdt_lever")
    e = ENDSTOP
    rec = _rec("community CAD", "microswitch_spdt_lever.step",
               f"{FCL}: Microswitch_SPDT_Horizontal_L.step (D2F-size lever switch) on a generated 20 x 12.5 mm board",
               inbox=["ENDSTOP-MICRO"],
               protrusions={"ymax": (e["lever_tip_free"][1] - e["body_y"][1], "lever at its free position (it moves)"),
                            "xmin": (-e["lever_tip_free"][0] + 0.98 - 10.0, "lever tip past the end of the board"),
                            "zmin": (-e["pins_z"], "switch terminals through the board")},
               tolerance={"volume_ratio": (0.6, 1.9)}, assembly=True,
               notes=["operating position is OMRON's D2F hinge-lever figure, 6.8 +/-1.5 mm from the mounting-hole line (data sheet p.4); "
                      "the lever is drawn at its free position (10 mm from that line), 3.2 mm before it operates",
                      "the community model's lever is 1.45 mm longer than OMRON's point A (9.0 against 7.55 mm from the body centre)",
                      "the board is a generic generated one, not a named product: its terminal row (0.9 mm below the body bottom, "
                      "2.62 mm through the board) is NOT OMRON's right-angled terminal (2.6 +/-0.2 mm below the body, 1.5 mm through)"])
    if f is None:
        return None, rec

    def build():
        import numpy as np
        from build123d import Box, Compound, Cylinder, Pos

        from ..geom import location_from_matrix

        T = np.eye(4)
        T[:3, :3] = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], dtype=float)
        T[:3, 3] = (0, e["shift_y"], 4.5)
        sw = vc.bake(vc.solids_of(vc.load_step(f)).moved(location_from_matrix(T)))
        w, dpt, t = e["pcb"]
        board = Pos(0, (e["pcb_y"][0] + e["pcb_y"][1]) / 2, t / 2) * Box(w, dpt, t)
        for x, y in e["holes"]:
            board -= Pos(x, y, t / 2) * Cylinder(e["hole_d"] / 2, t + 1)
        return Compound(children=[vc.bake(board)] + list(sw.solids()))

    return vc.cached("endstop:2", [f], build), rec


# ------------------------------------------------------------------ electronics
def psu_lrs(model: str):
    """MEAN WELL's own STEP of the LRS-350 (the LRS-200 shares the 215 x 115 x 30 case; its 3D file is a RAR archive
    that could not be unpacked here). File: length X (terminals at low X), width Y, up Z, base at Z=1.5.
    Part: centred in XY, base on Z=0. One internal part of the vendor file is drawn 0.9 mm through the base; the
    model is trimmed at the base plane."""
    f = _file("meanwell_LRS-350")
    rec = _rec("vendor CAD", "meanwell_LRS-350.stp",
               "MEAN WELL LRS-350-3D.zip (www.meanwell.com), file LRS-350(N2).stp"
               + ("" if model.startswith("LRS-350") else f"; used for the {model}, which has the same case (not confirmed by a 3D file)"),
               inbox=[model, f"{model}-3D"], tolerance={"volume_ratio": (0.6, 6.0)}, assembly=True,
               no_auto_features=True,
               features=[hole_feature(f"mount_holes_m4[{i}]", (x, y, 1.5), 4.0, (0, 0, 1), dia_range=(0.75, 1.2))
                         for i, (x, y) in enumerate(((-75, -25), (-75, 25), (75, -25), (75, 25)))],
               notes=["volume: the case is a hollow sheet-metal box, the simulation solid is the full 215 x 115 x 30 envelope",
                      "the vendor STEP has one internal bracket drawn 0.9 mm below the base (data sheet height: 30 mm); trimmed"])
    if f is None or not model.startswith(("LRS-350", "LRS-200")):
        return None, rec

    def build():
        from build123d import Box, Compound, Pos

        s = vc.frame(vc.solids_of(vc.load_step(f)), pos=(-155.58, -229.79, -1.5))
        keep = Pos(0, 0, 50) * Box(400, 400, 100)
        out = []
        for so in s.solids():
            out += list((so & keep).solids()) if so.bounding_box().min.Z < -1e-6 else [so]
        return Compound(children=out)

    return vc.cached("psu_lrs350", [f], build), rec


def skr_mini_e3_v3():
    """BIGTREETECH's own STEP of the SKR Mini E3 V3.0, with the solids under 40 mm^3 (SMD passives, small ICs) removed
    to keep the file under 5 MB. File: board X = 28.65..132.4, Y = -1.05..69.2, PCB top at Z=0 (drawn 0.8 mm thick).
    Part: centred, PCB top at Z=1.6 (a 1.6 mm board standing on Z=0)."""
    f = _file("btt_skr_mini_e3_v3.0_reduced")
    rec = _rec("vendor CAD", "btt_skr_mini_e3_v3.0_reduced.step",
               "BIGTREETECH-SKR-mini-E3 repository, hardware/BTT SKR MINI E3 V3.0/3D/BTT E3 SKR MINI V3.0.step, reduced "
               "(41 of 732 solids kept: every solid over 40 mm^3)",
               inbox=["BTT E3 SKR MINI V3.0", "CTRL-SKR-MINI-E3-V3"],
               protrusions={"zmin": (-0.65, "the vendor model's board is only 0.8 mm thick"),
                            "xmax": (1.375, "USB and micro-SD connectors overhang the board edge")},
               tolerance={"volume_ratio": (0.6, 10.0)}, assembly=True, no_auto_features=True,
               notes=["the vendor STEP draws the PCB 0.8 mm thick; the simulation solid keeps a 1.6 mm board (top faces aligned)",
                      "VENDOR CAD AND VENDOR DRAWING DISAGREE: the STEP has no mounting holes where BIGTREETECH's SIZE drawing "
                      "puts the five 3.1 mm holes; it has two 3.1 mm holes at (-30.68, 16.6) and (9.33, 16.6) instead. The "
                      "catalogue keeps the drawing's holes, so the hole check is switched off for this part",
                      "connector positions agree with the catalogue's port positions within 0.5 mm (motor connectors checked)"])
    if f is None:
        return None, rec
    return vc.cached("skr_mini_e3_v3", [f], lambda: vc.frame(vc.load_step(f), pos=(-80.525, -34.075, 1.6))), rec


# ------------------------------------------------------------------ fasteners
_ISO = {"M2.5": "M2.5-0.45", "M3": "M3-0.5", "M4": "M4-0.7", "M5": "M5-0.8", "M6": "M6-1", "M8": "M8-1.25"}


def shcs(size: str, length: float):
    """ISO 4762 socket head cap screw from bd_warehouse (head, socket, chamfers; threads not cut). Same frame as the
    catalog part. A McMaster (or other) STEP named SHCS-<size>x<length>.step in vendor_cad/inbox/ replaces it."""
    rec = _rec("generated to standard", None, "ISO 4762, generated by bd_warehouse.fastener.SocketHeadCapScrew (simple thread)",
               tolerance={"volume_ratio": (0.8, 1.35)},
               notes=["head diameter is the standard's maximum for knurled heads (M3: 5.68); the simulation solid uses the plain-head "
                      "maximum (5.5)"])

    def build():
        from bd_warehouse.fastener import SocketHeadCapScrew

        return vc.bake(SocketHeadCapScrew(size=_ISO[size], length=length, fastener_type="iso4762", simple=True))

    try:
        return vc.cached(f"shcs:{size}:{length}", [], build), rec
    except Exception:       # a length outside the standard's range: no detail model
        return None, {}


def hex_nut(size: str):
    """ISO 4032 hex nut from bd_warehouse (chamfered, with its hole). Same frame as the catalog part."""
    rec = _rec("generated to standard", None, "ISO 4032, generated by bd_warehouse.fastener.HexNut (simple thread)",
               tolerance={"volume_ratio": (0.9, 1.9)},
               notes=["the simulation solid has no hole (the thread is the overlap with the screw) and sharp corners"])

    def build():
        from bd_warehouse.fastener import HexNut

        return vc.bake(HexNut(size=_ISO[size], fastener_type="iso4032", simple=True))

    try:
        return vc.cached(f"hex_nut:{size}", [], build), rec
    except Exception:
        return None, {}


# ------------------------------------------------------------------ toolhead
def hotend_v6(tip_z: float):
    """Community V6-style hotend (FreeCAD-library hotend-3d-printer.step: heat sink, groove mount, heater block and
    nozzle as one solid; no fan or duct). File: axis Z, top of the groove mount at Z=3.7, nozzle tip at Z=-59.1 (62.8
    long; E3D's drawing: 62.55), heater block towards -X. Part: file Z - 3.7 (top of the groove mount on Z=0)."""
    f = _file("hotend_v6_style")
    rec = _rec("community CAD", "hotend_v6_style.step",
               f"{FCL}: Electrical Parts/Hotend/hotend-3d-printer.step (a V6-style hotend drawn by a community author; "
               "not E3D's model)", inbox=["V6-175-24V", "HOTEND-V6"], no_auto_features=True,
               features=[hole_feature("groove_dia", (0, 0, -6.7), 12.0, (0, 0, 1), tol_dia=0.1),
                         hole_feature("flange_dia", (0, 0, -1.8), 16.0, (0, 0, 1), tol_dia=0.1)],
               protrusions={"zmin": (0.3, "the community model is 62.8 mm long, E3D's drawing 62.55")},
               tolerance={"volume_ratio": (0.4, 2.3), "mass_ratio": (0.1, 3.0), "bbox": 1.6},
               notes=["volume: the community model has real fins, the simulation solid is the finned envelope",
                      "community model: lower groove flange 2.0 mm thick (E3D drawing 3.0), heater block 11.5 high",
                      f"nozzle tip in the simulation solid: Z={tip_z:g} (E3D drawing)"])
    if f is None:
        return None, rec
    return vc.cached("hotend_v6", [f], lambda: vc.frame(vc.solids_of(vc.load_step(f)), pos=(0, 0, -3.7))), rec


E3D_REF = "E3D 'Roto Reference' CAD (printables.com model 655950, file REVO-ROTO-24V-AS-REFERENCE.STEP, hand-downloaded 2026-11-15)"
E3D_REF_FILE = "e3d_roto_reference_cad.step"      # the unchanged download; the two files below are cut from it


def _sidecar(f) -> dict:
    """The `<file>.json` next to a STEP file ("rot", "pos": the file's frame -> the part's frame), or {}."""
    import json

    p = f.with_suffix(f.suffix + ".json")
    return json.loads(p.read_text()) if p.exists() else {}


def extruder_roto(c: dict):
    """E3D's own reference CAD of the Roto, cold side: gearbox cover (with the mounting ears), heat sink, ring gear,
    fan, idler lever, motor and four screws (10 solids). Cut from E3D's 11-solid reference file: the hot side went to
    `hotend_revo`, and the motor's four lead wires (drawn as straight 0.8 mm rods 30.9 mm long) are cut off at the
    lead block, because they are flexible and would otherwise read as a rigid spike 17.7 mm past the side face.
    File: nozzle tip at the origin, filament +Y, motor at -Z. Part: frame from the sidecar (rot 90, 0, 270; origin on
    the lower mounting-hole axis at mid-width). `c` is reference_cad.measured_mm of the vendor file."""
    f = _file("EXTRUDER-E3D-ROTO")
    ey = sum(c["mount_ears_y_abs"]) / 2
    lo, up, mo, fa = c["mount_hole_lower"], c["mount_hole_upper"], c["motor"], c["fan"]
    tip = c["nozzle_tip"]
    feats = []
    for i, h in enumerate((lo, up)):
        for side, y in (("+Y", ey), ("-Y", -ey)):      # each hole exists only in two 7 mm ears
            feats.append(hole_feature(f"mount_holes_m3[{i}] ({side} ear)", (h["xz"][0], y, h["xz"][1]), 3.3, (0, 1, 0), dia_range=(0.99, 1.04)))
    feats += [hole_feature("filament_bore", (tip[0], tip[1], 10.0), c["filament_bore_dia"], (0, 0, 1), tol_dia=0.05),
              hole_feature("motor_dia", (mo["x"][1] - 2.0, mo["axis_yz"][0], mo["axis_yz"][1]), mo["dia"], (1, 0, 0), tol_dia=0.05),
              hole_feature("fan_opening", (sum(fa["x"]) / 2, mo["axis_yz"][0], mo["axis_yz"][1]), 33.4, (1, 0, 0), tol_dia=0.1)]
    rec = _rec("vendor CAD", "EXTRUDER-E3D-ROTO.step",
               f"{E3D_REF}: cold side, 10 of its 11 solids, motor lead wires cut off at the lead block",
               inbox=["REVO-ROTO-COLDSIDE-AS", "Roto Reference", "e3d-roto-reference-cad"], derived_from=f"vendor_cad/{E3D_REF_FILE}",
               assembly=True, no_auto_features=True, features=feats,
               notes=["mounting holes: the CAD draws the lower one 3.39 mm and the upper one 3.30 mm (drawing: 2 x 3.3 +/-0.08); each is in "
                      "two 7 mm ears at |Y| 12.25..19.25",
                      "the motor's four leads (40 mm per the data sheet) are not in the model or the simulation solid: they leave the lead "
                      "block at `motor_lead_exit`, diagonally towards -Y +Z",
                      "the idler lever is drawn in one position; its travel is not in the CAD",
                      "simulation solid: the heat sink's underside around the nozzle is 0.7 mm higher than the box (Z -10.75, not -11.45)"])
    if f is None:
        return None, rec
    sc = _sidecar(f)
    return vc.cached(f"extruder_roto:{sc.get('rot')}:{sc.get('pos')}", [f],
                     lambda: vc.frame(vc.solids_of(vc.load_step(f)), tuple(sc.get("rot", (90, 0, 270))),
                                      tuple(sc.get("pos", (-9.058, -4.06, -33.55))))), rec


def hotend_revo(c: dict, sleeve_length: float, part_number: str):
    """E3D's reference solid of the Revo hot side (HeaterCore + nozzle as one body of revolution; no lead sleeve, no
    spring), taken unchanged from the Roto reference file. File: tip at the origin, axis +Y. Part: axis Z, seat on
    Z=0, tip at Z=-22.8 (sidecar: rot 90, 0, 270, the Roto's own turn). `c` is reference_cad.measured_mm."""
    f = _file("HOTEND-REVO-24V-40W")
    z = lambda above_tip: above_tip - c["seat_to_tip"]
    hc, nb = c["heatercore"], c["nozzle_block"]
    rec = _rec("vendor CAD", "HOTEND-REVO-24V-40W.step", f"{E3D_REF}: solid REVO-HOTSIDE-REFERENCE, unchanged",
               inbox=[part_number, "Revo HeaterCore", "HOTEND-REVO"], derived_from=f"vendor_cad/{E3D_REF_FILE}", no_auto_features=True,
               features=[hole_feature("heatercore_dia", (0, 0, z(sum(hc["z"]) / 2)), hc["dia"], (0, 0, 1), tol_dia=0.05),
                         hole_feature("nozzle_block_dia", (0, 0, z(sum(nb["z"]) / 2)), nb["dia"], (0, 0, 1), tol_dia=0.05)],
               protrusions={"xmax": (-sleeve_length, "the HeaterCore's lead sleeve is in the simulation solid (from E3D's HeaterCore "
                                                     "drawing) but not in the reference CAD")},
               tolerance={"volume_ratio": (0.6, 1.7), "mass_ratio": (0.2, 3.0)},
               notes=["the reference CAD has no lead sleeve; the simulation solid keeps it (22 mm towards +X, scaled from the HeaterCore drawing)",
                      "above the HeaterCore the CAD draws a 2.5 mm neck and a 6 mm head; the simulation solid is a 6 mm tube up to the seat",
                      "one model for the 12 V and 24 V HeaterCore (same body)"])
    if f is None:
        return None, rec
    sc = _sidecar(f)
    return vc.cached(f"hotend_revo:{sc.get('rot')}:{sc.get('pos')}", [f],
                     lambda: vc.frame(vc.solids_of(vc.load_step(f)), tuple(sc.get("rot", (90, 0, 270))),
                                      tuple(sc.get("pos", (0.0, 0.0, -c["seat_to_tip"]))))), rec
