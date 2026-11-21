"""Catalogue parts added for printer_v12, the Build 1 candidate (2026-11-20). Every part names its maker, maker part number,
seller, and where its geometry and ratings come from (practice rule DG-07, docs/DESIGN_GUIDELINES.md key rule). A part whose
geometry or a rating has no maker source says so in its model / ratings and is reported as a placeholder.

  hiwin_mgn12_rail(length)     HIWIN MGNR12R rail, HIWIN's own section (official CAD, REQ-005) swept to a stock length, holes by
                               HIWIN's E rule (10 + n x 25 + 10 for 245 / 295)
  hiwin_mgn12h_block()         HIWIN MGN12H block, preload Z0, accuracy C (MGN12HZ0C set), HIWIN's own block solids
  bracket_misumi(kind)         MISUMI HBLFSN5 (30 x 30, re-made from the catalogue drawing) / HBLFSNF5 (30 x 20, MISUMI STEP)
  tnut_hntp5()                 MISUMI HNTP5-5 post-assembly spring nut (the -SEP set's nut), re-made from catalogue p.2716
  add_bracket_misumi(...)      a -SEP bracket on two T-slots: CBM5-10 into HNTP5-5 in each leg, every part drawn
  spacer_harwin(length, mat)   Harwin R30-620xx14 (aluminium) / R30-670xx94 (nylon) M3 round spacers, re-made from Harwin's drawings
  heater_keenovo_200()         Keenovo 200 x 200 mm 24 V 200 W silicone heater (stock product, maker-direct)
  thermostat_cs7()             Cantherm CS712025Y: CS-7 bimetal thermostat, 120 degC NC, 10 A at 24 V DC (maker's sheet)
  pi5_host()                   Raspberry Pi 5 8 GB (SC1432), the Klipper / Moonraker host, own 27 W supply
  contactor_finder_2232()      Finder 22.32.0.120.4320 25 A 2-pole modular contactor, 120 V coil (DIN rail)
  relay_phoenix_1119897()      Phoenix Contact PLC-RSC-5DC/21 interface relay, 5 V DC coil (DIN rail)
  din_rail_wago(length), din_endstop_wago()   WAGO 210-112 35 x 7.5 rail (cut by the builder) and 249-117 end stop
  probe_eddy_duo()             BIGTREETECH Eddy Duo eddy-current probe (re-made from BTT's dimensioned drawing)
  cam_arducam_b0454(), lens_cil062(), picam3()   nozzle camera board + lens, overview / top-down camera
  laser_vlm520()               Quarton VLM-520-56 LPO-D30-F10 green line laser (Class 1M)
  adxl345_btt(), sfs_v2(), cob_led(length)       accelerometer, filament motion sensor, 24 V COB LED segment
"""
from __future__ import annotations

import dataclasses
import math

from build123d import Box, Cylinder, Location, Plane, Polygon, Pos, Rot, extrude

from . import Stock, add_screw, mgn12_rail, mgn12h_carriage, part, place, vendor_data
from . import vendor_cad as vc
from .vendor_cad import hole_feature

CHECKED = "2026-11-20"
MC = {"name": "Motion Constrained (Colorado, US)", "part_number": "HIWIN MGN12HZ0C set", "url": "https://motionconstrained.com",
      "checked": f"{CHECKED} (owner's agent, REQ-009; stock and lead to confirm on ordering)",
      "note": "MGN12HZ0C set = MGNR12R rail + one MGN12H block, preload Z0, accuracy C: $79.64 per set at 295 mm, free US shipping; "
              "rail only $49.49 at 245 mm"}
HIWIN_SRC = ("HIWIN Corporation official CAD from configure.hiwin.com (collected for the owner, Instinct REQ-005 batch 6; "
             "checks in vendor_cad/staging/instinct_REQ-005/MANIFEST.md)")


def _tagged(st: Stock, sku: str, desc: str, real_part: dict, **kw) -> Stock:
    return dataclasses.replace(st, sku=sku, description=desc, real_part=real_part, **kw)


# ------------------------------------------------------------------ HIWIN rails and blocks
@part
def hiwin_mgn12_rail(length: float) -> Stock:
    """HIWIN MGNR12R rail at a HIWIN standard length (245, 295 ...). Local frame as mgn12_rail (along X, base Z=0). Display model:
    the section of HIWIN's own rail STEP (MGNR-12-R0300-H-M) swept to `length`, holes drilled per HIWIN's E rule (the same hole
    layout mgn12_rail computes: 10 + n x 25 + 10 at 245 and 295)."""
    base = mgn12_rail(length)
    v = vendor_data("hiwin_mgn12")["parts"]["MGNR12_rail"]["values"]
    holes = base.interfaces["mount_holes_m3"]
    e_end = (length - (len(holes) - 1) * v["hole_pitch_P_mm"]) / 2
    f = vc.find_file("HIWIN-MGNR12R-R0300", inbox_only=True)
    model = {"kind": "proxy", "source": "HIWIN STEP not in vendor_cad/inbox"}
    detail = None
    if f is not None:
        def build():
            from build123d import extrude as ex

            s = vc.frame(vc.solids_of(vc.load_step(f)), rot=(90, 0, 90))
            bb = s.bounding_box()
            thin = s & (Pos(bb.min.X + 25.0, 0, 4) * Box(0.02, 40, 40))
            face = max((q for q in thin.faces() if abs(abs(tuple(q.normal_at())[0]) - 1) < 1e-6), key=lambda q: q.center().X)
            bar = ex(Pos(-face.center().X - length / 2, 0, 0) * face, length, dir=(1, 0, 0))
            hr, cb = v["height_HR_mm"], v["counterbore_depth_h_mm"]
            for x, _, _ in holes:
                bar -= Pos(x, 0, hr / 2) * Cylinder(v["bolt_hole_d_mm"] / 2, hr + 1)
                bar -= Pos(x, 0, hr - cb / 2 + 0.5) * Cylinder(v["counterbore_D_mm"] / 2, cb + 1)
            return vc.bake(bar)

        detail = vc.cached(f"hiwin_rail:{length}", [f], build)
        model = {"kind": "vendor CAD", "file": f"vendor_cad/inbox/{f.name}", "no_auto_features": True,
                 "source": f"{HIWIN_SRC}: the MGNR-12-R0300-H-M rail's section swept to {length:g} mm, holes per HIWIN's E rule "
                           f"(E = {e_end:g} mm at each end, {len(holes)} holes at 25 mm; HIWIN's own 245 mm file has exactly this layout)",
                 "features": [hole_feature(f"mount_holes_m3[{i}]", (x, 0, 1.0), v["bolt_hole_d_mm"], (0, 0, 1), tol_dia=0.05)
                              for i, (x, _, _) in enumerate(holes)]}
    rp = {"maker": "HIWIN", "mpn": f"MGNR12R{int(length)} (rail of the MGN12HZ0C set)" if int(length) == 295 else f"MGNR12R{int(length)}H (rail only)",
          "sellers": [MC], "stock_size": f"{length:g} mm (HIWIN standard length; E = {e_end:g}/{e_end:g})",
          "datasheet": "vendor_docs/HIWIN_MG_series_catalog_excerpt_p79-93.pdf; vendor_docs/HIWIN_MGNR-12-R0245-H-M_drawing.pdf",
          "ratings_source": {"mass_kg_per_m": "HIWIN MG catalogue 0.65 kg/m"}}
    st = _tagged(base, f"HIWIN-MGNR12R-{int(length)}", f"HIWIN MGNR12R rail {length:g} mm (stock length, not cut)", rp,
                 detail=detail, model=model, cost_usd=49.49 if int(length) == 245 else 79.64)
    return st


@part
def hiwin_mgn12h_block() -> Stock:
    """HIWIN MGN12H block of an MGN12HZ0C set (preload Z0, accuracy C). Local frame as mgn12h_carriage. Display model: the block's
    nine solids (body, end caps, seals, plugs) from HIWIN's MGN-12-H-1R0300-ZF-H-M block + rail assembly STEP (the ZF file: the
    outside of a Z0 block is the same; preload is internal)."""
    base = mgn12h_carriage(preload="Z0")
    f = vc.find_file("HIWIN-MGN12H-ASSEMBLY", inbox_only=True)
    detail, model = None, {"kind": "proxy", "source": "HIWIN STEP not in vendor_cad/inbox"}
    if f is not None:
        def build():
            full = vc.load_step(f)
            sol = sorted(full.solids(), key=lambda so: so.bounding_box().size.Z)       # the rail is the one 300 mm long
            blk = vc.solids_of(full, keep=lambda so, bb: bb.size.Z < 100.0)
            s = vc.frame(blk, rot=(90, 0, 90))
            bb = s.bounding_box()
            return vc.frame(s, pos=(-(bb.min.X + bb.max.X) / 2, 0, 0))

        detail = vc.cached("hiwin_block", [f], build)
        model = {"kind": "vendor CAD", "file": f"vendor_cad/inbox/{f.name}", "no_auto_features": True, "mates_with": ("HIWIN-MGNR12R",),
                 "tolerance": {"volume_ratio": (0.6, 2.2)},
                 "protrusions": {"xmin": (1.11, "the end caps' lubrication plugs (HIWIN STEP), beyond the catalogue's 45.4 mm"),
                                 "xmax": (1.11, "the end caps' lubrication plugs (HIWIN STEP), beyond the catalogue's 45.4 mm")},
                 "source": f"{HIWIN_SRC}: the block's solids of MGN-12-H-1R0300-ZF-H-M (the rail solid left out)"}
    rp = {"maker": "HIWIN", "mpn": "MGN12HZ0C (block of the set)", "sellers": [MC], "stock_size": "MGN12H, Z0, C",
          "datasheet": "vendor_docs/HIWIN_MGN-12-H-1R0300-ZF-H-M_drawing.pdf; vendor_docs/Hiwin_MG_catalogue.pdf",
          "ratings_source": {k: "HIWIN MG catalogue GW-11-5-EN-2207-K Table 3.79 / 3.77 / 3.88" for k in
                             ("dynamic_load_n", "static_load_n", "static_moment_nm", "static_moment_mr_nm", "static_moment_mp_nm",
                              "static_moment_my_nm", "radial_stiffness_n_per_m", "allowable_parallelism_mm", "ball_track_length_m")}}
    st = _tagged(base, "HIWIN-MGN12HZ0C", "HIWIN MGN12H block, preload Z0, accuracy C (MGN12HZ0C set)", rp, detail=detail, model=model,
                 cost_usd=0.0)
    st.ratings["accuracy_class"] = "C"
    st.ratings["accuracy_class_source"] = "HIWIN MG excerpt p.79-93: C (normal) +/-40 um on H"
    return st


# ------------------------------------------------------------------ MISUMI tabbed brackets and spring nuts
HBLF_DRAWING = ("MISUMI 2019 US catalogue p.2692 (HBLFSN5 / HBLFSNF5, vendor_cad/staging/supplier_2026-11-19/BRKT-2020.pdf) and the "
                "owner-supplied MISUMI pages (docs/V11_1_PLAN.md)")


def _hblf_solid(leg_a: float, leg_b: float):
    """Reversal tabbed bracket in the catalogue frame: inside corner at the origin, leg A along +X lying on the plane y = 0 (its
    outside face on the extrusion), leg B along +Y on x = 0; width 20 along Z, centred. Legs 4.5 thick (drawing), side webs 2 mm
    (MISUMI's HBLFSNF5 STEP of the same series), tabs 1 mm proud and 6 mm wide in the slot opening (drawing: 1; width from the
    same STEP). Open between the side webs, so heads and drivers reach the leg holes from inside."""
    T, W, WEB, TAB_W = 4.5, 20.0, 2.0, 6.0
    s = Pos(leg_a / 2, T / 2, 0) * Box(leg_a, T, W) + Pos(T / 2, leg_b / 2, 0) * Box(T, leg_b, W)
    tri = extrude(Polygon((0, 0), (leg_a, 0), (0, leg_b), align=None), WEB / 2, both=True)
    for zc in (W / 2 - WEB / 2, -(W / 2 - WEB / 2)):
        s += Pos(0, 0, zc) * tri
    # Tabs (1 mm proud, 6 wide) where MISUMI's own STEPs (REQ-013) have them: the leg-A tabs stop short of the 18 mm hole on both
    # sides; leg B has small bosses round its hole instead of a tab
    if leg_b == 20.0:          # HBLFSNF5: leg A tabs 4.29-12.71 and 23.79-26.21; leg B a 5.74 square boss round the hole at 10
        for a0, a1 in ((4.29, 12.71), (23.79, 26.21)):
            s += Pos((a0 + a1) / 2, -0.5, 0) * Box(a1 - a0, 1.0, TAB_W)
        s += Pos(-0.5, 10.0, 0) * Box(1.0, 5.74, 5.74)
    else:                      # HBLFSN5: leg A tabs 5-11 and 21-24; leg B a dia 6 boss ring round 10
        for a0, a1 in ((5.0, 11.0), (21.0, 24.0)):
            s += Pos((a0 + a1) / 2, -0.5, 0) * Box(a1 - a0, 1.0, TAB_W)
        s += Pos(-0.5, 10.0, 0) * Rot(0, 90, 0) * Cylinder(3.0, 1.0)      # (the STEP's four arcs on a dia 6 ring, taken as the ring)
    return s


@part
def bracket_misumi(kind: str = "HBLFSN5") -> Stock:
    """MISUMI reversal tabbed bracket for HFS5 (slot 6) 2020, aluminium casting 383.0, no surface treatment, allowable load 1176 N,
    applicable screws CBM5-10 x 2 with spring nuts (-SEP set: CBM5-10 + HNTP5-5). HBLFSN5: legs 30 x 30, 3 x dia 5.3 (one in leg A at
    18 from the corner, two in leg B at 10 and 18: 'use one, depending on the mounting direction'), 15 g. HBLFSNF5: legs 30 x 20,
    2 x dia 5.2 (18 in the 30 leg, 10 in the 20 leg), 13 g; its display model is MISUMI's STEP."""
    if kind not in ("HBLFSN5", "HBLFSNF5"):
        raise ValueError("kind is HBLFSN5 or HBLFSNF5")
    la, lb = (30.0, 30.0) if kind == "HBLFSN5" else (30.0, 20.0)
    hd = 5.3 if kind == "HBLFSN5" else 5.2
    s = _hblf_solid(la, lb)
    holes_a = [18.0]
    holes_b = [10.5, 18.0] if kind == "HBLFSN5" else [10.0]   # HBLFSN5: 10.5 / 18.0 per MISUMI's STEP (REQ-013)
    for x in holes_a:
        s -= Pos(x, 2.25, 0) * Rot(90, 0, 0) * Cylinder(hd / 2, 8.0)
    for y in holes_b:
        s -= Pos(2.25, y, 0) * Rot(0, 90, 0) * Cylinder(hd / 2, 8.0)
    mass = 0.015 if kind == "HBLFSN5" else 0.013
    model = {"kind": "generated to standard", "remade_from": HBLF_DRAWING, "inbox": [kind],
             "tolerance": {"volume_ratio": (0.5, 2.5), "mass_ratio": (0.2, 5.0)},
             "source": (f"re-made from the maker's dimensioned drawing ({HBLF_DRAWING}): legs {la:g} / {lb:g}, width 20 (10 + 10), wall 4.5, "
                        f"tab height 1, holes {len(holes_a) + len(holes_b)} x dia {hd:g} at 18 / 12 / 10, all in the model. The drawing does "
                        "not dimension the tab width, the side webs and the inner fillets: those are taken from MISUMI's own HBLFSNF5 STEP "
                        "of the same series (tabs 6.0 wide, webs about 2 mm), nothing scaled or guessed beyond that"),
             "no_auto_features": True}
    rp = {"maker": "MISUMI", "mpn": f"{kind}-SEP", "sellers": [{"name": "MISUMI USA", "part_number": f"{kind}-SEP", "catalogue": True,
                                                              "url": "https://us.misumi-ec.com", "checked": CHECKED}],
          "stock_size": "set: bracket + 2 x CBM5-10 + 2 x HNTP5-5", "datasheet": HBLF_DRAWING,
          "ratings_source": {"allowable_load_n": "MISUMI p.2692 table: 1176 N"}}
    st = Stock(s, kind, f"MISUMI {kind} reversal tabbed bracket ({la:g} x {lb:g}), casting 383.0, -SEP set", mass, material="al6061",
               cost_usd=1.05 if kind == "HBLFSN5" else 1.0, ratings={"allowable_load_n": 1176.0, "maker_part": f"MISUMI {kind}-SEP"},
               interfaces={"holes_a": tuple(holes_a), "holes_b": tuple(holes_b), "leg_t": 4.5, "legs": (la, lb)}, model=model, real_part=rp,
               source={"level": "vendor", "vendor": "MISUMI", "part": kind, "url": HBLF_DRAWING, "retrieved": CHECKED, "unverified_fields": [],
                       "file": "docs/V11_1_PLAN.md"})
    return st


@part
def tnut_hntp5(flip: bool = False) -> Stock:
    """MISUMI HNTP5-5 post-assembly insertion spring nut (HFS5, M5), the nut of the -SEP bracket sets: 17 long, 8.3 wide, 3.8 high
    with a 3.2 body under the slot's lips, 5.8 neck, the M5 thread 6 mm from one end (L1), 1010 steel, trivalent chromate; a ball on a
    spring under it holds it in the slot (not dimensioned: left out). Local frame as tnut_2020: Z along the slot's outward normal,
    X along the slot, the face that bears on the lips at Z=0, the THREAD's axis at the origin (the body is 2.5 mm off centre)."""
    L, Wd, H, B, NW, L1 = 17.0, 8.3, 3.8, 3.2, 5.8, 6.0
    off = (L / 2 - L1) * (-1.0 if flip else 1.0)          # flip: the long end towards -X (a bracket turns its nuts away from the corner)
    # the drawing shows the body's lower edges chamfered (no dimension: 0.5 x 45 degrees taken, so the body is 7.3 wide at its bottom,
    # the width MISUMI makes it to sit in the HFS5 cavity's tapered walls)
    sec = Polygon((-Wd / 2, 0.0), (Wd / 2, 0.0), (Wd / 2, -(B - 0.5)), (Wd / 2 - 0.5, -B), (-(Wd / 2 - 0.5), -B), (-Wd / 2, -(B - 0.5)), align=None)
    shape = Location(Plane(origin=(off + L / 2, 0, 0), x_dir=(0, 1, 0), z_dir=(1, 0, 0))) * extrude(sec, L) + Pos(off, 0, (H - B) / 2) * Box(L, NW, H - B)
    detail = shape - Pos(0, 0, (H - B - B) / 2) * Cylinder(2.5, H)
    drawing = "MISUMI 2019 US catalogue p.2716 (vendor_docs/misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf): HNTP5, M5: 17, 8.3, 5.8, 3.8, 3.2, L1 = 6"
    return Stock(shape, "HNTP5-5", "MISUMI HNTP5-5 post-assembly spring nut M5 (-SEP set)", float(detail.volume) * 7.85e-6, material="steel",
                 cost_usd=0.0, detail=detail,
                 ratings={"insertion": "drop-in", "maker_part": "MISUMI HNTP5-5", "reference_tightening_torque_nm": 6.8},
                 interfaces={"thread_d": 5.0, "length": L, "span": Wd, "span_bottom": 7.3, "height": H, "neck": H - B, "neck_width": NW, "body_height": B,
                             "thread_length": H, "thread_offset": -(H - B), "insertion": "drop-in"},
                 model={"kind": "generated to standard", "remade_from": drawing, "no_auto_features": True,
                        "tolerance": {"volume_ratio": (0.8, 1.6), "mass_ratio": (0.5, 2.0)},
                        "source": f"re-made from the maker's dimensioned drawing ({drawing}); the ball and spring are drawn without "
                                  "dimensions and are left out"},
                 real_part={"maker": "MISUMI", "mpn": "HNTP5-5", "sellers": [{"name": "MISUMI USA", "part_number": "HNTP5-5 (in the -SEP set)",
                                                                            "catalogue": True, "checked": CHECKED}],
                            "datasheet": drawing, "ratings_source": {"reference_tightening_torque_nm": "MISUMI p.2716: 6.8 N.m (M5)"}},
                 source={"level": "vendor", "vendor": "MISUMI", "part": "HNTP5-5", "url": drawing, "retrieved": CHECKED,
                         "unverified_fields": [], "file": "vendor_docs/misumi_2019_US_2716_post_assembly_nuts_HFS5.pdf"})


def _cbm5_detail(sc):
    """The -SEP set's screw is MISUMI CBM5-10 (ISO 4762 M5 x 10, head 8.5 x 5, 4 mm hex: MISUMI's STEP, REQ-013): its own SKU and
    MISUMI's file as its display model, in place of McMaster's M5 x 10."""
    from build123d import Location as _L
    from OCP.gp import gp_Trsf

    from . import shcs

    sc.sku = "CBM5-10"
    ov = vc.inbox_override(["CBM5-10"], shcs("M5", 10.0).shape)
    if ov is None:
        return
    P = sc.meta.get("placement")
    tr = gp_Trsf()
    tr.SetValues(*[P[i][j] for i in range(3) for j in range(4)])
    sc.detail = ov[0].moved(_L(tr))
    sc.meta["model"] = {**(sc.meta.get("model") or {}), **ov[1], "source": "MISUMI CBM5-10 STEP (Instinct REQ-013)"}
    sc.ratings.pop("mcmaster_pn", None)
    sc.ratings.pop("mcmaster_pn_status", None)


def add_bracket_misumi(d, name: str, a: str, b: str, corner, u, v, body: str = "world", kind: str = "HBLFSN5",
                       locking: str | None = None, hole_b: float = 18.0):
    """A MISUMI -SEP tabbed bracket on two slotted extrusions: inside corner at `corner`, leg A along u on part a, leg B along v on
    part b. Each leg: a CBM5-10 (ISO 4762 M5 x 10) from inside the casting through its 4.5 mm leg into an HNTP5-5 spring nut in the
    slot, 18 mm from the corner (leg B of an HBLFSN5 may use its 10 mm hole, `hole_b`; leg B of an HBLFSNF5 is 10)."""
    import numpy as np

    st = bracket_misumi(kind)
    uv, vv = np.array(u, float), np.array(v, float)
    c = place(d, name, st, Location(Plane(origin=tuple(corner), x_dir=tuple(uv), z_dir=tuple(np.cross(uv, vv)))), body=body)
    hb = hole_b if kind == "HBLFSN5" else 10.0
    for part_name, along, out, off, sfx in ((a, uv, vv, 18.0, "_screw_a"), (b, vv, uv, hb, "_screw")):
        foot = np.array(corner, float) + along * off
        from .tslot import slot_frame

        fr = slot_frame(d.get(part_name), tuple(foot + out * 4.5), tuple(-out))
        flip = fr is not None and float(np.dot(np.asarray(fr["along"], float), along)) < 0      # the nut's long end away from the corner
        sc = add_screw(d, name + sfx, "M5", 10, at=tuple(foot + out * 4.5), direction=tuple(-out), body=body, threads_into=part_name,
                       tnut=True, clamps=(name,), locking=locking, tnut_stock=tnut_hntp5(flip))
        sc.meta["bracket_leg_of"] = name
        sc.meta["real_part"] = {"maker": "MISUMI", "mpn": "CBM5-10", "sellers": [{"name": "MISUMI USA", "part_number": "CBM5-10 (in the -SEP set)",
                                                                                "catalogue": True, "checked": CHECKED}]}
        _cbm5_detail(sc)
        d.join(name, part_name, "m5_tnut")
    return c


# ------------------------------------------------------------------ Harwin spacers
HARWIN = {"aluminium": ("R30-620{:02d}14", "Harwin_R30-620XX14_drawing.pdf", 5.0, 3.2, 2.7e-3, 0.50),
          "nylon": ("R30-670{:02d}94", "Harwin_R30-670XX94_drawing.pdf", 5.0, 3.2, 1.14e-3, 0.67)}
HARWIN_LENGTHS = (3, 4, 5, 6, 8, 10, 12, 15, 20)


@part
def spacer_harwin(length: float = 6.0, material: str = "nylon") -> Stock:
    """Harwin R30 M3 round spacer, dia 5.0 x dia 3.2 bore x `length` (stock lengths only), aluminium (R30-620xx14) or nylon 6.6
    (R30-670xx94). Local frame as spacer_round: axis Z, bottom at Z=0. Re-made from Harwin's drawing (OD, bore, length are all it has)."""
    if int(length) != length or int(length) not in HARWIN_LENGTHS:
        raise ValueError(f"Harwin R30 stock lengths used here: {HARWIN_LENGTHS}")
    pat, dwg, od, bore, rho, cost = HARWIN[material]
    mpn = pat.format(int(length))
    body = Pos(0, 0, length / 2) * (Cylinder(od / 2, length) - Cylinder(bore / 2, length))
    mass = math.pi * (od ** 2 - bore ** 2) / 4 * length * rho
    return Stock(body, f"SPACER-HARWIN-{mpn}", f"Harwin {mpn} round spacer M3, {od:g} x {bore:g} x {length:g} mm, {material}", mass,
                 material="al6061" if material == "aluminium" else "nylon_pa12", cost_usd=cost,
                 ratings={"screw": "M3", "vendor_part": f"Harwin {mpn}"},
                 interfaces={"od": od, "bore": bore, "length": float(length), "top": [(0.0, 0.0, float(length))]},
                 model={"kind": "generated to standard", "remade_from": f"vendor_docs/{dwg}", "no_auto_features": True,
                        "source": f"re-made from Harwin's drawing vendor_docs/{dwg}: OD {od:g}, bore {bore:g}, length {length:g}"},
                 real_part={"maker": "Harwin", "mpn": mpn, "sellers": [{"name": "Digi-Key", "part_number": f"Harwin {mpn}", "checked": CHECKED}],
                            "stock_size": f"{length:g} mm", "datasheet": f"vendor_docs/{dwg}"},
                 source={"level": "vendor", "vendor": "Harwin", "part": mpn, "url": f"vendor_docs/{dwg}", "retrieved": CHECKED,
                         "unverified_fields": [], "file": f"vendor_docs/{dwg}"})


# ------------------------------------------------------------------ bed heater and thermostat
@part
def heater_keenovo_200() -> Stock:
    """Keenovo standard square silicone heater 200 x 200 mm, 24 V, 200 W, 3M adhesive, with Keenovo's NTC 100K B3950 (not used: the
    bed is read by a Semitec 104NT-4 clamped to the plate). Maker-direct, keenovo.store, $43.28 (REQ-003). Thickness and lead exit are
    NOT published on the maker's page: 1.5 mm and the -Y edge are assumed (geometry pending: measure on arrival)."""
    from .electrical import bed_heater_pad

    st = bed_heater_pad(200.0, 200.0, 200.0, 24.0)
    e = st.ratings["electrical"]
    e["sources"] = {**e["sources"], "watts": "Keenovo product page (vendor_docs/Keenovo_200x200-24V-200W_page_2026-11-20.pdf): 200 W, 24 V",
                    "volts": "Keenovo product page: 24 V"}
    e["product"] = dict(e["product"], vendor="Keenovo", part_number="Keenovo silicone heater 200x200 mm 24 V 200 W (standard square)")
    rp = {"maker": "Keenovo", "mpn": "Silicone heater 200x200 mm 24V 200W (standard square, 3M adhesive)",
          "sellers": [{"name": "Keenovo (keenovo.store, maker direct)", "part_number": "200x200 24V 200W", "checked": CHECKED,
                       "note": "$43.28, available (REQ-003); ships from Keenovo: confirm US shipping cost and lead"}],
          "sold_by_maker": True, "stock_size": "200 x 200 mm", "datasheet": "vendor_docs/Keenovo_200x200-24V-200W_page_2026-11-20.pdf",
          "ratings_source": {"watts": "Keenovo page: 200 W", "volts": "Keenovo page: 24 V"},
          "replace_with": "Keenovo's drawing with thickness and lead exit (ask Keenovo), or measure the delivered pad"}
    return _tagged(st, "HEATER-KEENOVO-200x200-24V-200W", "Keenovo silicone heater 200 x 200 mm 24 V 200 W (stock)", rp, cost_usd=43.28,
                   model={"kind": "proxy", "source": "plain 200 x 200 x 1.5 sheet: thickness not published (geometry pending)",
                          "state": "stand-in"})


HYDRA_DWG = "vendor_docs/NPH_NPHSF365_HydraResearch-SQ1451144_24V-200W-210x210_heater_drawing.pdf"


@part
def heater_hydra_sq1451144() -> Stock:
    """Hydra Research SQ1451144 silicone bed heater (made by National Plastic Heater, drawing NPHSF365): 24 V, 200 W, 210 x 210 mm,
    adhesive backed, NTC 3950 (R25 not stated: 100 k ASSUMED, unused here: the bed is read by the Semitec 104NT-4), Molex 43640-0401
    connector on 130 mm leads. Hydra Research, Portland OR, $9.99 (owner, 2026-11-20). Thickness is NOT dimensioned on the drawing:
    1.5 mm (Keenovo class) ASSUMED until measured. Local frame: as bed_heater_pad (centred, adhesive face on Z=0, leads at -Y)."""
    from .electrical import bed_heater_pad

    st = bed_heater_pad(210.0, 210.0, 200.0, 24.0)
    e = st.ratings["electrical"]
    e["sources"] = {**e["sources"], "watts": "Hydra Research SQ1451144 listing / NPH drawing NPHSF365: 200 W at 24 V",
                    "volts": "Hydra Research SQ1451144: 24 V",
                    "ntc": "NTC 3950 per Hydra; R25 not stated: 100 k ASSUMED (the pad's NTC is not wired: Semitec 104NT-4 reads the bed)"}
    e["product"] = dict(e["product"], vendor="Hydra Research (National Plastic Heater)", part_number="SQ1451144")
    rp = {"maker": "National Plastic Heater (for Hydra Research)", "mpn": "SQ1451144 (drawing NPHSF365)",
          "sellers": [{"name": "Hydra Research (Portland, OR)", "part_number": "SQ1451144", "checked": CHECKED,
                       "note": "$9.99, 6 in stock (owner, 2026-11-20)"}],
          "stock_size": "210 x 210 mm", "datasheet": HYDRA_DWG,
          "ratings_source": {"watts": "Hydra / NPHSF365: 200 W", "volts": "Hydra / NPHSF365: 24 V"},
          "replace_with": "measure the thickness on arrival; fallback Keenovo SKU 10133 200 x 200 (China, $43.28, 2-6 weeks)",
          "note": "leads end in a Molex 43640-0401 (Micro-Fit 3.0, 4 positions: about 5 A per contact, under the 8.3 A heater current): "
                  "cut it off and crimp the bed loom's Mini-Fit HCS (16 AWG max) onto the heater pair; the lead gauge is not stated"}
    return _tagged(st, "HEATER-HYDRA-SQ1451144-210x210-24V-200W", "Hydra Research SQ1451144 silicone heater 210 x 210 mm 24 V 200 W", rp,
                   cost_usd=9.99,
                   model={"kind": "generated to standard", "remade_from": HYDRA_DWG, "no_auto_features": True,
                          "assumed": ["thickness 1.5 mm (not dimensioned on NPHSF365; Keenovo-class figure): measure on arrival"],
                          "source": "re-made from NPH drawing NPHSF365 rev 0: 210 x 210 outline, leads leaving the middle of one edge (130 +/-15 "
                                    "to the Molex 43640-0401); thickness 1.5 ASSUMED (not on the drawing); the terminal and thermistor "
                                    "patches (about 30 x 20 and 21 x 31, scaled, not dimensioned) are not modelled"})


@part
def thermostat_cs7() -> Stock:
    """Cantherm CS712025Y: CS-7 bimetal disc thermostat, normally closed, opens at 120 degC (+/-5 typical), resets 20 K lower, rated
    24 V DC 10 A (20,000 cycles, not agency-listed), 250 V AC 10 A; R53 housing (thermoset, metal cap, loose bracket). Clamped
    against the bed plate's underside. Local frame: cap face (the sensing face) on Z=0 looking up +Z, body below. Its outline is a
    re-make of the R53 drawing's main dimensions; terminals and bracket are left out (geometry pending)."""
    from .electrical import thermal_fuse

    st = thermal_fuse(120.0, 100.0, 10.0)
    e = st.ratings["electrical"]
    e["ratings"] = {**e["ratings"], "auto_reset": True}
    e["sources"] = {"trip_c": "Cantherm CS-7 / R53 data sheet (vendor_docs/Cantherm_CS7_R53_thermostat_datasheet.pdf): temperature steps of "
                              "5 degC, tolerance +/-5 typical; 120 degC NC per the order code CS712025Y (V12_PLAN, Digi-Key listing)",
                    "hold_c": "reset 20 K +/- 5 K below the opening temperature (data sheet: hysteresis 20K +/-5K)",
                    "amps": "data sheet: 'Additional ratings for CS-7 only: 24VDC 10A / 20,000 switching cycles (Not UL, CSA, VDE)'",
                    "resistance_ohm": "data sheet: contact resistance < 50 mOhm"}
    e["product"] = dict(product="Cantherm CS712025Y bimetal thermostat, 120 degC NC, 10 A 24 V DC", vendor="Cantherm",
                        part_number="CS712025Y", form="component", off_the_shelf=True, custom_pcb=False,
                        builder_work="FASTON 6.3 receptacles; clamp the cap to the plate with the laser-cut clamp plate and thermal paste")
    e["ratings"]["resistance_ohm"] = 0.05
    # R53, horizontal (Y) terminals, as drawn in vendor_docs/Cantherm_R53_CS712025Y_datasheet_rev2017-04.pdf p.2: cap dia 16.2, 12.3 over
    # the housing; the loose mounting ring (23.8) is not used (the thermostat is bonded); the terminals' length is not dimensioned
    shape = Pos(0, 0, -6.15) * Cylinder(8.1, 12.3)
    rp = {"maker": "Cantherm", "mpn": "CS712025Y", "sellers": [{"name": "Digi-Key", "part_number": "Cantherm CS712025Y", "checked": CHECKED,
                                                               "note": "$5.38, 427 in stock (V12_PLAN, distributor API 2026-11-19)"}],
          "datasheet": "vendor_docs/Cantherm_CS7_R53_thermostat_datasheet.pdf",
          "ratings_source": {"trip_c": "Cantherm data sheet (120 degC NC per the order code CS712025Y)", "hold_c": "data sheet hysteresis 20K +/-5K",
                             "amps": "data sheet: 24VDC 10A", "resistance_ohm": "data sheet: contact resistance < 50 mOhm"},
          "replace_with": "the R53 drawing's full outline (terminals, bracket) in the model"}
    rp.pop("replace_with", None)
    return _tagged(st, "THERMOSTAT-CANTHERM-CS712025Y", "Cantherm CS712025Y bimetal thermostat 120 degC NC (bed cut-off)", rp,
                   shape=shape, mass_kg=0.006, cost_usd=5.38,
                   model={"kind": "generated to standard", "remade_from": "vendor_docs/Cantherm_R53_CS712025Y_datasheet_rev2017-04.pdf p.2 (R53, Y terminals: "
                          "dia 16.2 x 12.3)", "source": "cap dia 16.2, housing 12.3 (Cantherm's R53 drawing); terminals (not dimensioned) and the "
                          "loose ring (not used) left out", "no_auto_features": True})


# ------------------------------------------------------------------ electronics
def _ports(ports):
    from .electrical import _ports_to_interfaces

    return _ports_to_interfaces(ports)


def _step_model(name: str, src: str, rot=(0, 0, 0), pos=(0, 0, 0), tol=(0.2, 6.0), keep=None):
    """(detail, model) from a maker STEP in vendor_cad/inbox/, framed by rot/pos; None detail when the file is absent."""
    f = vc.find_file(name, inbox_only=True)
    if f is None:
        return None, {"kind": "proxy", "source": f"{name} not in vendor_cad/inbox (maker STEP staged, not moved)"}
    detail = vc.cached(f"b12:{name}:{rot}:{pos}", [f], lambda: vc.frame(vc.solids_of(vc.load_step(f), keep=keep), rot, pos))
    return detail, {"kind": "vendor CAD", "file": f"vendor_cad/inbox/{f.name}", "source": src, "no_auto_features": True,
                    "tolerance": {"volume_ratio": tol, "mass_ratio": (0.05, 20.0)}, "assembly": True}


def _env_of(detail, fallback):
    if detail is None:
        return fallback
    bb = detail.bounding_box()
    return Pos((bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2) * Box(bb.size.X, bb.size.Y, bb.size.Z)


@part
def pi5_host() -> Stock:
    """Raspberry Pi 5 8 GB (SC1432) with the Active Cooler (SC1148), powered by its own official 27 W USB-C supply (SC1153) from its
    own mains plug, so it stays up when the printer's contactor cuts the 24 V supply. Klipper host and Moonraker; UART to the Octopus
    (no 5 V on that lead), two CSI cameras, USB for the nozzle camera, the Eddy and the accelerometer, GPIO for the contactor's driver.
    Local frame: PCB centred, underside on Z=0; four M2.5 holes on 58 x 49 (3.5 from the edges; RPi mechanical drawing)."""
    T = 1.5
    pcb = Pos(0, 0, T / 2) * Box(85.0, 56.0, T)
    cooler = Pos(-6.0, 0.0, T + 7.0) * Box(52.0, 42.0, 13.0)
    holes = [(x, y, 0.0) for x in (-85 / 2 + 3.5, -85 / 2 + 3.5 + 58.0) for y in (-24.5, 24.5)]
    for x, y, _ in holes:
        pcb -= Pos(x, y, T / 2) * Cylinder(1.35, T)
    ports = {"GPIO": dict(kind="host", connector="dupont", max_a=2.0, conductors=3, at=(-10.0, 24.5, T + 3.0), dir=(0, 0, 1),
                          pin="GND, GPIO14 TXD, GPIO15 RXD (no 5 V: the Pi has its own supply)"),
             "PWR": dict(kind="signal_out", connector="dupont", max_a=0.1, conductors=2, at=(10.0, 24.5, T + 3.0), dir=(0, 0, 1),
                         pin="GPIO26 + GND (drives the PN2222A of the contactor's interface relay)"),
             # the Eddy's USB link, represented for the wiring checks as a 3.3 V logic input tolerant to 5 V (the Eddy is its own MCU on
             # USB: Klipper's [mcu eddy]); a right-angle (up) plug, the port faces the front-right Z motor 6 mm away
             "USB": dict(kind="endstop_in", connector="usb-a", max_a=0.6, conductors=4, at=(40.0, -10.0, T + 16.0), dir=(0, 0, 1),
                         logic_v=3.3, pin_max_v=5.5, pin="USB 2.0 port (Eddy Duo; the nozzle camera and the accelerometer on the others)")}
    ratings = {"supply_w": 0.0, "volts": 5.0, "min_ambient_c": 0.0, "max_ambient_c": 50.0}
    sources = {"geometry": "Raspberry Pi 5 mechanical drawing (vendor_docs/RaspberryPi_Pi5_mechanical_drawing.pdf): 85 x 56, holes 2.7 on 58 x 49, "
                           "3.5 from the edge; Active Cooler outline from its product brief",
               "supply_w": "drawn from its own 27 W USB-C supply (SC1153), not from the board's 5 V rail: 0 W on the Octopus rail",
               "max_ambient_c": "Raspberry Pi 5 product brief: 0 to 50 degC"}
    detail, model = _step_model("RPi5_SC1432", "Raspberry Pi Ltd STEP of the Pi 5 (vendor_cad/staging/provenance_2026-11-19)")
    if detail is not None:
        model = {**model, "protrusions": {}, "tolerance": {"volume_ratio": (0.2, 8.0)}}
    rp = {"maker": "Raspberry Pi Ltd", "mpn": "SC1432 (Raspberry Pi 5 8GB)",
          "sellers": [{"name": "Digi-Key", "part_number": "SC1432", "checked": CHECKED, "note": "$175.00, 19,347 in stock (V12_PLAN)"}],
          "datasheet": "vendor_docs/RaspberryPi_Pi5_mechanical_drawing.pdf",
          "ratings_source": {"supply_w": "own 27 W supply SC1153 (not the board's rail)", "volts": "Raspberry Pi 5 product brief: 5 V DC via USB-C",
                             "min_ambient_c": "Raspberry Pi 5 product brief: 0 to 50 degC", "max_ambient_c": "Raspberry Pi 5 product brief: 0 to 50 degC"}}
    from .electrical import _ots

    return Stock(pcb + cooler, "HOST-RPI5-8GB-SC1432", "Raspberry Pi 5 8 GB + Active Cooler (Klipper host, own 27 W supply)", 0.073,
                 material="abs", detail=None, model={"kind": "proxy", "source": "board + cooler envelope from the RPi mechanical drawing",
                                                    "remade_from": "vendor_docs/RaspberryPi_Pi5_mechanical_drawing.pdf"},
                 ratings={"electrical": {"kind": "host", "ports": ports, "ratings": ratings, "sources": sources,
                                         "product": _ots("Raspberry Pi 5 8 GB", "Raspberry Pi Ltd", "SC1432", "assembled board",
                                                         "fit the Active Cooler; own 27 W USB-C supply; 3-wire UART lead to the Octopus"),
                                         "params": {}}},
                 interfaces={"mount_holes_m2.5": holes, "standoff_min": 3.0, **_ports(ports)}, cost_usd=175.0, real_part=rp)


@part
def contactor_finder_2232() -> Stock:
    """Finder 22.32.0.120.4320 modular contactor: 2 NO, 25 A (AC-1, 250 V), 120 V AC/DC coil (2 VA), 17.5 mm wide on 35 mm DIN rail,
    88.8 high. Both poles switched: L and N of the supply's feed. Its coil is fed from the inlet's L through the Phoenix
    PLC-RSC-5DC/21 contact, which a Pi GPIO switches through a PN2222A (Moonraker [power], off_when_shutdown). Local frame: rail
    clip on Z=0 (the rail's top face), centred on the rail's axis X; 17.5 along X, 88.8 along Y, front face up +Z."""
    W, H, D = 17.5, 88.85, 55.8
    body = Pos(0, 0, D / 2) * Box(W, H, D)
    sc = dict(connector="screw-box", max_a=25.0)
    ports = {"LIN": dict(kind="series", at=(0.0, H / 2 - 6.0, 40.0), dir=(0, 1, 0), **sc),
             "LOT": dict(kind="series", at=(0.0, -H / 2 + 6.0, 40.0), dir=(0, -1, 0), **sc),
             "NIN": dict(kind="series", at=(4.0, H / 2 - 6.0, 40.0), dir=(0, 1, 0), **sc),
             "NOT": dict(kind="series", at=(4.0, -H / 2 + 6.0, 40.0), dir=(0, -1, 0), **sc),
             "ctrl": dict(kind="signal_in", connector="screw-box", max_a=2.0, at=(-4.0, H / 2 - 6.0, 46.0), dir=(0, 1, 0), conductors=2)}
    ratings = {"contact_a": 25.0, "volts": 250.0, "resistance_ohm": 0.0, "supply_w": 2.2, "coil_v": 120.0}
    sources = {"contact_a": "Finder 22 series data sheet S22EN p.2 (vendor_docs/Finder_22-series_datasheet.pdf): 22.32, rated current 25 A, "
                            "AC-1 6250 VA per pole at 250 V",
               "supply_w": "S22EN: rated coil power 2 VA / 2.2 W", "coil_v": "order code .120: 120 V AC/DC coil",
               "volts": "S22EN: 250 V AC contacts", "resistance_ohm": "contact resistance neglected"}
    detail, model = _step_model("Finder_22.32_2NO", "Finder's STEP of the 22.32 2NO (Instinct REQ-006; 88.8 high as on p.14)",
                                rot=(90, 0, 90), pos=(5.25, 17.425, 0.0))
    model["protrusions"] = {"zmin": (5.0, "the rail clip, inside the DIN rail's channel")}
    from .electrical import _ots

    rp = {"maker": "Finder", "mpn": "22.32.0.120.4320", "sellers": [{"name": "Digi-Key", "part_number": "22.32.0.120.4320", "checked": CHECKED,
                                                                    "note": "$46.34, 205 in stock (V12_PLAN)"}],
          "datasheet": "vendor_docs/Finder_22-series_datasheet.pdf",
          "ratings_source": {k: "Finder S22EN data sheet" for k in ratings}}
    st = Stock(body, "CONTACTOR-FINDER-22.32.0.120.4320", "Finder 22.32 25 A 2-pole contactor, 120 V coil (mains switching)", 0.12,
               material="abs", detail=detail, model=model,
               ratings={"electrical": {"kind": "relay", "ports": ports, "ratings": ratings, "sources": sources,
                                       "product": _ots("Finder 22.32.0.120.4320 modular contactor", "Finder", "22.32.0.120.4320", "module",
                                                       "snap on the DIN rail; ferrules on every conductor"),
                                       "params": {"through": {"LIN": "LOT", "LOT": "LIN", "NIN": "NOT", "NOT": "NIN"}, "cuts": "psu",
                                                  "switched_by": "host", "host_pin": "gpiochip0/gpio26"}}},
               interfaces={"rail_width": W, **_ports(ports)}, cost_usd=46.34, real_part=rp)
    return st


@part
def relay_phoenix_1119897() -> Stock:
    """Phoenix Contact PLC-RSC-5DC/21 (1119897) interface relay: 5 V DC coil (38 mA), 1 changeover 6 A, 6.2 wide x 80 high x 94 deep
    on 35 mm DIN rail. Switches the contactor's 120 V coil; its own coil is driven from a Pi GPIO by a PN2222A (1 kOhm base). Local
    frame: rail clip on Z=0, 6.2 along X, 80 along Y, up +Z."""
    W, H, D = 6.1, 80.0, 92.6
    detail, model = _step_model("Phoenix_1119897", "Phoenix Contact STEP of PLC-RSC-5DC/21 (Instinct REQ-008)", pos=(-3.05, -40.0, 0.0))
    return Stock(Pos(0, 0, D / 2) * Box(W, H, D), "PLC-RSC-PHOENIX-1119897", "Phoenix Contact PLC-RSC-5DC/21 interface relay (5 V DC coil)",
                 0.035, material="abs", detail=detail, model=model, cost_usd=17.30,
                 ratings={"coil_v": 5.0, "coil_ma": 38.0, "contact_a": 6.0},
                 interfaces={"rail_width": W},
                 real_part={"maker": "Phoenix Contact", "mpn": "1119897 (PLC-RSC- 5DC/21)",
                            "sellers": [{"name": "Digi-Key", "part_number": "1119897", "checked": CHECKED, "note": "$17.30, 1,407 in stock"}],
                            "datasheet": "vendor_docs/Phoenix_1119897_PLC-RSC-5DC-21_datasheet.pdf",
                            "ratings_source": {"coil_v": "data sheet: nominal input 5 V DC", "coil_ma": "data sheet: 38 mA typical",
                                               "contact_a": "data sheet: limiting continuous current 6 A"}},
                 source={"level": "vendor", "vendor": "Phoenix Contact", "part": "1119897", "url": "vendor_docs/Phoenix_1119897_PLC-RSC-5DC-21_datasheet.pdf",
                         "retrieved": CHECKED, "unverified_fields": [], "file": "vendor_docs/Phoenix_1119897_PLC-RSC-5DC-21_datasheet.pdf"})


@part
def din_rail_wago(length: float = 100.0) -> Stock:
    """WAGO 210-112 steel carrier rail, EN 60715 35 x 7.5, 1 mm, slotted, sold 2 m: CUT TO LENGTH BY THE BUILDER (hacksaw, deburr;
    the one purchased part cut on the bench, like the extrusions Misumi cuts). Local frame: along X centred, base on Z=0, top Z=7.5."""
    t, w, h = 1.0, 35.0, 7.5
    sec = (Pos(0, 0, t / 2) * Box(length, 27.0 - 2 * t + 2 * t, t) + Pos(0, 27.0 / 2 - t / 2, h / 2) * Box(length, t, h)
           + Pos(0, -27.0 / 2 + t / 2, h / 2) * Box(length, t, h) + Pos(0, (27.0 + w) / 4, h - t / 2) * Box(length, (w - 27.0) / 2, t)
           + Pos(0, -(27.0 + w) / 4, h - t / 2) * Box(length, (w - 27.0) / 2, t))
    holes = [(x, 0.0, 0.0) for x in (-length / 2 + 12.5, length / 2 - 12.5)]
    for x, y, _ in holes:
        sec -= Pos(x, y, t / 2) * Box(15.0, 5.2, t) + Pos(x - 7.5, y, t / 2) * Cylinder(2.6, t) + Pos(x + 7.5, y, t / 2) * Cylinder(2.6, t)
    dwg = "vendor_docs/WAGO_210-112_datasheet.pdf"
    return Stock(sec, f"DIN-RAIL-WAGO-210-112-{int(length)}", f"WAGO 210-112 DIN rail 35 x 7.5, cut to {length:g} mm", 0.0005 * length,
                 material="steel", cost_usd=8.0 * length / 2000.0 + 0.5,
                 interfaces={"slots": holes, "top_z": h},
                 model={"kind": "generated to standard", "remade_from": dwg, "no_auto_features": True,
                        "source": f"re-made from WAGO's dimensioned drawing ({dwg}): 35 x 7.5 top hat, 1 mm, slots 5.2 x 15 on 25 mm "
                                  f"(slot positions after cutting are the builder's)"},
                 real_part={"maker": "WAGO", "mpn": "210-112", "sellers": [{"name": "Newark", "part_number": "WAGO 210-112", "checked": CHECKED,
                                                                          "note": "Digi-Key backorder; Newark stocks it (REQ-003)"}],
                            "stock_size": "2 m, cut to length by the builder", "datasheet": dwg})


@part
def din_endstop_wago() -> Stock:
    """WAGO 249-117 screwless end stop for 35 mm rail, 10 wide x 44 high x 35 deep. Local frame: on the rail top (Z=0), 10 along X."""
    dwg = "vendor_docs/WAGO_249-117_datasheet.pdf"
    return Stock(Pos(0, 0, 35.0 / 2) * Box(10.0, 44.0, 35.0), "DIN-ENDSTOP-WAGO-249-117", "WAGO 249-117 screwless end stop", 0.006,
                 material="nylon_pa12", cost_usd=1.0,
                 model={"kind": "generated to standard", "remade_from": dwg, "no_auto_features": True,
                        "source": f"envelope re-made from WAGO's dimensioned drawing ({dwg}): 10 x 44 x 35"},
                 real_part={"maker": "WAGO", "mpn": "249-117", "sellers": [{"name": "Digi-Key", "part_number": "WAGO 249-117", "checked": CHECKED}],
                            "datasheet": dwg})


# ------------------------------------------------------------------ feedback hardware (stage 3) and the probe
@part
def probe_eddy_duo() -> Stock:
    """BIGTREETECH Eddy Duo (LDC1612 + RP2040, coil thermistor), USB to the Pi 5. Body 18.1 x 33.8 x 15.3 (18.3 at the cable boss),
    2 x dia 3.15 holes 10.5 apart, 13.9 from the top (BTT dimensioned drawing). Local frame: coil face (the bottom) on Z=0 looking
    down, centre of the coil at the origin; holes along X on the face Y = +9.05 (the mounting face, towards +Y)."""
    W, L, Hh = 18.1, 33.8, 15.3
    body = Pos(0, 0, L / 2) * Box(W, Hh, L)
    holes = [(x, Hh / 2, L - 13.9) for x in (-5.25, 5.25)]
    for x, y, z in holes:
        body -= Pos(x, 0, z) * Rot(90, 0, 0) * Cylinder(3.15 / 2, Hh)
    from .electrical import inductive_probe_template

    tpl = inductive_probe_template(4.0, 4.0, "pnp_no", (4.75, 5.25), internal_pullup=False)
    MAN = "BTT Eddy manual (vendor_docs/BTT_Eddy_Series_User_Manual_20250507.pdf)"
    tpl["ratings"].update({"max_ambient_c": 60.0, "repeatability_mm": 0.001, "switching_distance_tolerance_frac": 0.10,
                           "supply_current_a": 0.03, "output_max_a": 0.0})
    tpl["sources"].update({
        "max_ambient_c": f"{MAN} 1: operating temperature <= 60 degC ambient",
        "supply_v_min": "USB 2.0 VBUS at the device 4.75-5.25 V (USB-IF specification); " + MAN + " 1: 5 V",
        "supply_v_max": "USB 2.0 VBUS at the device 4.75-5.25 V (USB-IF specification); " + MAN + " 1: 5 V",
        "supply_current_a": f"{MAN} 1: static and operating current 30 mA",
        "output": "no switched output: USB device read by Klipper (probe_eddy_current); 'pnp_no' only names the electrical template",
        "output_max_a": f"{MAN} 1: USB connection, no switched output: nothing is drawn from one (0 A)",
        "repeatability_mm": f"{MAN} 1: 'standard error 0.5 um'; taken as 1 um (twice the maker's figure)",
        "switching_distance_steel_mm": f"{MAN} 4.1: mounted 2-3 mm above the tip, coil current calibrated at 20 mm, so it reads over at "
                                       "least 2-20 mm; Klipper probe_eddy_current triggers at the height PROBE_EDDY_CURRENT_CALIBRATE sets: 4 mm "
                                       "is a setting inside that range",
        "switching_distance_aluminium_mm": f"{MAN} 4.1: as steel (the calibration is made on the printer's own bed sheet)",
        "switching_distance_tolerance_frac": "IEC 60947-5-2 real switching distance 0.9-1.1 x nominal (standard); the Eddy's trigger is a "
                                             "calibrated firmware setting, so this bounds it generously",
        "internal_pullup": "no switched output (USB device): no pull-up"})
    tpl["product"] = {"product": "BIGTREETECH Eddy Duo", "vendor": "BIGTREETECH", "part_number": "Eddy Duo", "form": "module",
                      "off_the_shelf": True, "custom_pcb": False, "builder_work": "its own 2.5 m USB lead (supplied with it, Eddy manual 1) to the Pi 5 in the toolhead loom"}
    tpl["params"] = {"interface": "usb", "usb_host": "Pi 5"}
    return Stock(body, "PROBE-BTT-EDDY-DUO", "BIGTREETECH Eddy Duo eddy-current bed probe (USB)", 0.012, material="abs", cost_usd=38.99,
                 ratings={"electrical": tpl, "max_ambient_c": 60.0},
                 interfaces={"sensing_face": [(0.0, 0.0, 0.0)], "mount_holes_m3": holes, **_ports(tpl["ports"])},
                 model={"kind": "generated to standard", "remade_from": "vendor_docs/BTT_Eddy_dimensions.jpg (BTT dimensioned drawing)",
                        "no_auto_features": True,
                        "source": "re-made from BTT's dimensioned drawing: 18.1 x 33.8 x 15.3, holes 2 x 3.15 on 10.5, 13.9 from the top; "
                                  "BTT's 48 MB STEP is staged (vendor_cad/staging/BTT_EDDY.STEP.gz), not used for display"},
                 real_part={"maker": "BIGTREETECH", "mpn": "Eddy Duo", "sellers": [{"name": "BIQU US store (us.biqu.equipment)", "checked": CHECKED,
                                                                                   "note": "$38.99 (search); variant, stock and ship-from to confirm"}],
                            "sold_by_maker": True, "datasheet": "vendor_docs/BTT_Eddy_Series_User_Manual_20250507.pdf",
                            "ratings_source": {"max_ambient_c": "BTT Eddy manual 1: operating temperature <= 60 degC ambient"},
                            "replace_with": "confirm the BIQU listing; the switching-distance stand-in is Klipper's calibrated height"})


def _simple(sku, desc, shape, mass, cost, rp, model, ratings=None, interfaces=None, material="abs"):
    return Stock(shape, sku, desc, mass, material=material, cost_usd=cost, ratings=ratings or {}, interfaces=interfaces or {},
                 model=model, real_part=rp)


@part
def cam_arducam_b0454() -> Stock:
    """Arducam B0454 USB UVC camera (OV5648, M12 x 0.5 lens holder), 38 x 38 board, holes 28 x 28 (dia 2.8) and 34 x 34 (dia 2.4),
    lens centred; -20 to 70 degC. Local frame: board centred, its back on Z=0, lens holder up +Z (optical axis +Z)."""
    s = Pos(0, 0, 0.8) * Box(38.0, 38.0, 1.6) + Pos(0, 0, 1.6 + 11.45) * Cylinder(8.7, 22.9)
    holes = [(x, y, 0.0) for x in (-14.0, 14.0) for y in (-14.0, 14.0)]
    return _simple("CAM-ARDUCAM-B0454", "Arducam B0454 USB nozzle camera (M12 mount)", s, 0.02, 38.99,
                   {"maker": "Arducam", "mpn": "B0454", "sellers": [{"name": "UCTRONICS (Arducam's store)", "checked": CHECKED,
                                                                     "note": "from $38.99; ship origin and cost to confirm"}],
                    "sold_by_maker": True, "datasheet": "vendor_docs/Arducam_B0454_datasheet.pdf",
                    "ratings_source": {"max_ambient_c": "B0454 data sheet: -20 to 70 degC"}},
                   {"kind": "generated to standard", "remade_from": "vendor_docs/Arducam_B0454_datasheet.pdf (overall dimension and lens diagrams)",
                    "no_auto_features": True, "source": "board 38 x 38, holes 28 x 28 / 34 x 34, holder dia 17.4 x 22.9 from Arducam's drawing"},
                   ratings={"max_ambient_c": 70.0}, interfaces={"mount_holes_m2.5": holes})


@part
def lens_cil062() -> Stock:
    """Commonlands CIL062-F4.0-M12A650 M12 lens, 6.2 mm F4.0, 650 nm IR cut. Local frame: thread axis Z, flange at Z=0."""
    return _simple("LENS-COMMONLANDS-CIL062-F4.0", "Commonlands CIL062-F4.0-M12A650 lens", Pos(0, 0, 8.0) * Cylinder(7.0, 16.0), 0.006, 23.0,
                   {"maker": "Commonlands", "mpn": "CIL062-F4.0-M12A650", "sellers": [{"name": "Digi-Key Marketplace",
                                                                                      "part_number": "4946-CIL062-F4.0-M12A650-ND", "checked": CHECKED}],
                    "datasheet": "vendor_docs/Commonlands_CIL062-F4.0-M12A650_drawing.pdf",
                    "replace_with": "the lens drawing's outline (envelope only so far)"},
                   {"kind": "proxy", "source": "dia 14 x 16 envelope (drawing not transcribed)", "state": "stand-in"})


@part
def picam3() -> Stock:
    """Raspberry Pi Camera Module 3 (SC1223), 25 x 23.862 board, depth 11.3 (RPi drawing), 0-50 degC. Local frame: board back on Z=0,
    lens up +Z, centred on the board; holes 2.2 on 21 x 12.5 (RPi drawing)."""
    s = Pos(0, 0, 0.5) * Box(25.0, 23.862, 1.0) + Pos(0, 2.0, 1.0 + 5.15) * Box(8.5, 8.5, 10.3)
    holes = [(x, y, 0.0) for x in (-10.5, 10.5) for y in (-23.862 / 2 + 2.0, -23.862 / 2 + 14.5)]
    for x, y, _ in holes:
        s -= Pos(x, y, 0.5) * Cylinder(1.1, 1.0)
    return _simple("CAM-RPI-CM3-SC1223", "Raspberry Pi Camera Module 3 (overview / top-down)", s, 0.004, 25.0,
                   {"maker": "Raspberry Pi Ltd", "mpn": "SC1223", "sellers": [{"name": "Digi-Key", "part_number": "SC1223", "checked": CHECKED,
                                                                               "note": "$25.00, 1,231 in stock"}],
                    "datasheet": "vendor_docs/RaspberryPi_Camera-Module-3_std_mechanical_drawing.pdf",
                    "ratings_source": {"max_ambient_c": "product brief 0-50 degC"}},
                   {"kind": "generated to standard", "remade_from": "vendor_docs/RaspberryPi_Camera-Module-3_std_mechanical_drawing.pdf",
                    "no_auto_features": True, "source": "25 x 23.862 board, 11.3 deep, holes from Raspberry Pi's mechanical drawing (envelope)"},
                   ratings={"max_ambient_c": 50.0}, interfaces={"mount_holes_m2": holes})


@part
def laser_vlm520() -> Stock:
    """Quarton VLM-520-56 LPO-D30-F10 green line laser, 520 nm, 30 degree fan, Class 1M, 3-6 V 80 mA, dia 10 mm brass body (case may
    be live: insulating clamp). Local frame: axis +Z = the beam, front face on Z=0, body towards -Z. Body length not read (30 mm
    assumed: geometry pending)."""
    return _simple("LASER-QUARTON-VLM-520-56-LPO-D30-F10", "Quarton VLM-520-56 LPO-D30-F10 green line laser (Class 1M)",
                   Pos(0, 0, -15.0) * Cylinder(5.0, 30.0), 0.01, 98.40,
                   {"maker": "Quarton", "mpn": "VLM-520-56 LPO-D30-F10", "sellers": [{"name": "Digi-Key", "part_number": "100-VLM-520-56LPO-D30-F10-ND",
                                                                                     "checked": CHECKED, "note": "$98.40, 3 in stock; 4-week maker lead after"}],
                    "replace_with": "Quarton's VLM-520-56 30 degree datasheet (body length, line width table)"},
                   {"kind": "proxy", "source": "dia 10 x 30 (length assumed)", "state": "stand-in"}, material="brass")


@part
def adxl345_btt() -> Stock:
    """BIGTREETECH ADXL345 V2.0 USB accelerometer board: PCB 33.25 x 15.50 x 0.35 mm... (BTT STEP), two dia 3.2 holes 15.5 apart.
    Local frame: PCB centred, underside on Z=0, holes along X."""
    s = Pos(0, 0, 0.8) * Box(33.25, 15.5, 1.6) + Pos(10.0, 0, 1.6 + 1.3) * Box(9.0, 9.0, 2.6)
    holes = [(x, -15.5 / 2 + 2.5, 0.0) for x in (-7.75, 7.75)]
    return _simple("ADXL345-BTT-V2", "BIGTREETECH ADXL345 V2.0 USB accelerometer", s, 0.004, 9.25,
                   {"maker": "BIGTREETECH", "mpn": "ADXL345 V2.0.1", "sellers": [{"name": "biqu.equipment (BTT store)", "checked": CHECKED,
                                                                                  "note": "$9.25, in stock (REQ-003)"}],
                    "sold_by_maker": True, "datasheet": "vendor_docs/BTT_ADXL345-V2.0_manual.pdf"},
                   {"kind": "generated to standard", "remade_from": "BTT ADXL345 V2.0 STEP (vendor_cad/staging/instinct_REQ-003, measured: PCB 33.25 x 15.50, "
                                                                    "holes 3.2 on 15.5 at y 2.5)",
                    "no_auto_features": True, "source": "PCB outline and holes measured on BTT's STEP (38.7 MB, not used for display)"},
                   interfaces={"mount_holes_m3": holes})


@part
def sfs_v2() -> Stock:
    """BIGTREETECH SFS V2.0 smart filament (motion) sensor. Envelope from BTT's STEP (staged, provenance_2026-11-19); not transcribed
    here: 40 x 28 x 26 assumed (geometry pending). Local frame: filament axis along Z, centred."""
    return _simple("SFS-BTT-V2", "BIGTREETECH SFS V2.0 filament motion sensor", Box(53.15, 30.3, 27.3), 0.025, 12.0,
                   {"maker": "BIGTREETECH", "mpn": "SFS V2.0", "sellers": [{"name": "biqu.equipment (BTT store)", "checked": CHECKED}],
                    "sold_by_maker": True, "datasheet": "vendor_docs/BTT_SFS_V2.0_user_manual_20231123.pdf",
                    "replace_with": "the outline from BTT's STEP (vendor_cad/staging/provenance_2026-11-19/BTT_SFS_V2.0_Model.step.gz)"},
                   {"kind": "generated to standard", "remade_from": "BTT's SFS V2.0 STEP (vendor_cad/staging/provenance_2026-11-19/BTT_SFS_V2.0_Model.step.gz): "
                    "envelope 53.15 x 30.3 x 27.3 measured", "no_auto_features": True,
                    "source": "the envelope of BTT's own STEP (25 MB, 248 solids: not used for display)"})


@part
def cob_led(length: float = 50.0) -> Stock:
    """Inspired LED 24V-COB-4000K-12M flexible COB strip segment, 8 mm wide, cut at 50 mm marks (1.97 in), 3.15 W/ft, CRI 91. Local
    frame: along X centred, back on Z=0, light up +Z."""
    return _simple(f"LED-COB-INSPIRED-24V-4000K-{int(length)}", f"Inspired LED 24 V COB strip, {length:g} mm segment", Pos(0, 0, 1.0) * Box(length, 8.0, 2.0),
                   0.002, 1.23, {"maker": "Inspired LED", "mpn": "24V-COB-4000K-12M", "sellers": [{"name": "Digi-Key", "part_number": "1647-24V-COB-4000K-12MCT-ND",
                                                                                                 "checked": CHECKED}],
                                 "datasheet": "vendor_docs/InspiredLED_24V-COB_flex_spec.pdf", "stock_size": "cut at the strip's 50 mm cut marks"},
                   {"kind": "generated to standard", "remade_from": "vendor_docs/InspiredLED_24V-COB_flex_spec.pdf", "no_auto_features": True,
                    "source": "8 mm wide flex strip, cut points every 1.97 in (maker's spec)"}, ratings={"watts_per_m": 10.3})


# ------------------------------------------------------------------ StepperOnline 17E19S1684AB4-330RA from its drawing A4003
A4003 = "vendor_docs/StepperOnline_17E19S1684AB4-330RA_Full_Datasheet.pdf (drawing A4003 rev 0; mechloop/parts/vendor/stepperonline_17e19_ab4.json datasheet_drawing)"
SO_SELLER = {"name": "StepperOnline (OMC, US warehouse)", "part_number": "17E19S1684AB4-330RA", "checked": CHECKED,
             "note": "maker direct; price $ from the product page (stepperonline_17e19_ab4.json)"}


@part
def leadscrew_nut_pom_a4003() -> Stock:
    """The POM anti-backlash nut supplied on the 17E19S1684AB4-330RA, re-made from StepperOnline's drawing A4003: square flange
    26 +/-0.1 (corners within dia 35), 5 thick, 4 x M4 on an 18.5 square; barrel dia 18, 16 long, a 2 mm gap, then the threaded
    preload section dia 18; 33 max overall; Tr8x2. Local frame as leadscrew_nut_pom_ab4: axis Z, the flange's flat face at Z=0, the
    flange below to Z=-5, the barrel below to Z=-33. Bought with the motor."""
    fw, ft, bd, L = 26.0, 5.0, 18.0, 33.0
    shape = (Pos(0, 0, -ft / 2) * Box(fw, fw, ft) + Pos(0, 0, -ft - 8.0) * Cylinder(bd / 2, 16.0)
             + Pos(0, 0, -(ft + 18.0 + (L - ft - 18.0) / 2)) * Cylinder(bd / 2, L - ft - 18.0) + Pos(0, 0, -(ft + 17.0)) * Cylinder(4.5, 2.0))
    shape -= Pos(0, 0, -L / 2) * Cylinder(4.0, L)
    h = 18.5 / 2
    holes = [(sx * h, sy * h, 0.0) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y, _ in holes:
        shape -= Pos(x, y, -ft / 2) * Cylinder(2.0, ft)
    vol = float(shape.volume)
    return Stock(shape, "NUT-T8x2-POM-AB-17E19S1684AB4-A4003", "POM anti-backlash nut Tr8x2 (supplied with the 17E19S1684AB4-330RA; drawing A4003)",
                 round(vol * 1.41e-6, 4), material="abs", cost_usd=0.0, detail=shape,
                 model={"kind": "generated to standard", "remade_from": A4003, "no_auto_features": True,
                        "source": f"re-made from {A4003}: every outer dimension on the drawing; thread and spring internals are not dimensioned"},
                 interfaces={"flange_width": fw, "flange_thickness": ft, "barrel_dia": bd, "barrel_length": L - ft, "mount_holes_m4": holes,
                             "hole_dia": 4.0, "flange_dia": fw},
                 ratings={"material_as_seen": "POM (acetal)", "anti_backlash": True, "bought_with": "17E19S1684AB4-330RA"},
                 real_part={"maker": "StepperOnline (OMC)", "mpn": "supplied with 17E19S1684AB4-330RA", "sellers": [SO_SELLER],
                            "datasheet": A4003},
                 source={"level": "vendor", "vendor": "StepperOnline", "part": "17E19S1684AB4-330RA nut", "url": A4003, "retrieved": CHECKED,
                         "unverified_fields": [], "file": "mechloop/parts/vendor/stepperonline_17e19_ab4.json"})


def _a4003_retag(st: Stock, sku: str, desc: str, sources: dict) -> Stock:
    rp = {"maker": "StepperOnline (OMC)", "mpn": "17E19S1684AB4-330RA", "sellers": [SO_SELLER], "datasheet": A4003,
          "ratings_source": sources,
          "replace_with": "StepperOnline: rotor inertia and screw efficiency (not on drawing A4003)"}
    m = {**st.model, "remade_from": A4003}
    m.pop("state", None)
    return dataclasses.replace(st, sku=sku, description=desc, real_part=rp, model=m)


@part
def leadscrew_motor_a4003() -> Stock:
    """The 17E19S1684AB4-330RA motor body, its geometry checked against drawing A4003 (42.3 max square, 48 max long, 4 x M3 4.5 deep on
    31 +/-0.1, pilot 22 x 2, JST PH 6-pin connector housing 16 x 11 at 6.5); electrical figures from A4003 (1.68 A, 1.65 ohm, 2.8 mH,
    0.44 N.m). Rotor inertia and screw efficiency are NOT on the drawing (sister-model / typical figures, flagged)."""
    from .batch7 import leadscrew_motor_17e19_ab4

    st = leadscrew_motor_17e19_ab4()
    src = {k: "drawing A4003" for k in ("holding_torque_nmm", "rated_current_a", "phase_resistance_ohm", "phase_inductance_mh", "lead_mm")}
    return _a4003_retag(st, st.sku, "StepperOnline 17E19S1684AB4-330RA lead-screw stepper (drawing A4003)", src)


@part
def leadscrew_screw_a4003(length: float = 328.0) -> Stock:
    """The motor's integral Tr8x2 screw, 330 +/-1 from the mounting face per drawing A4003 (328 drawn above the face, inside the
    tolerance band of the sister model's STEP figure)."""
    from .batch7 import leadscrew_screw_17e19_ab4

    st = leadscrew_screw_17e19_ab4(length)
    return _a4003_retag(st, "TR8x2-INTEGRAL-17E19S1684AB4-330RA", st.description, {"lead_mm": "drawing A4003: Tr8x2"})


# ------------------------------------------------------------------ Wham Bam 220 PEI kit
WB_PLATE = "vendor_docs/WhamBam_PEI-plate-220_page_2026-11-20.pdf"
WB_BASE = "vendor_docs/WhamBam_magnetic-base-220_page_2026-11-20.pdf"


@part
def whambam_base_220() -> Stock:
    """Wham Bam magnetic base 220 x 220, 1 mm, 3M 468MP adhesive, rated 150 degC continual (maker's page). Local frame: centred, its
    adhesive face on Z=0, 1 mm up."""
    t = 1.0
    return Stock(Pos(0, 0, t / 2) * Box(220.0, 220.0, t), "WHAMBAM-MAGNETIC-BASE-220", "Wham Bam magnetic base 220 x 220 x 1 mm (150 degC)",
                 220 * 220 * t * 3.7e-6, material="rubber_gt2", cost_usd=30.0, ratings={"max_temp_c": 150.0},
                 model={"kind": "generated to standard", "remade_from": WB_BASE, "no_auto_features": True,
                        "source": f"220 x 220 x 1 mm from the maker's page ({WB_BASE})"},
                 real_part={"maker": "Wham Bam Systems", "mpn": "Magnetic Base 220 x 220", "sellers": [{"name": "whambam3d.com (maker direct, US)",
                                                                                                       "checked": "2026-11-20"}],
                            "sold_by_maker": True, "datasheet": WB_BASE, "ratings_source": {"max_temp_c": "maker's page: 150 degC continual"}})


@part
def whambam_plate_220() -> Stock:
    """Wham Bam textured PEI flexi plate 220 x 220: 0.4 mm high-chromium spring steel, 0.12 mm ULTEM PEI each side (0.64 mm). SOLD OUT
    at the maker on 2026-11-20 (REQ-003): a restock or a second source is an open item. Local frame: centred, bottom on Z=0."""
    t = 0.64
    return Stock(Pos(0, 0, t / 2) * Box(220.0, 220.0, t), "WHAMBAM-PEI-PLATE-220", "Wham Bam PEX textured PEI flexi plate 220 x 220 (0.4 steel)",
                 220 * 220 * 0.4 * 7.85e-6, material="steel", cost_usd=35.0, ratings={"steel_thickness_mm": 0.4},
                 interfaces={"steel_thickness": 0.4, "size": 220.0},
                 model={"kind": "generated to standard", "remade_from": WB_PLATE, "no_auto_features": True,
                        "source": f"220 x 220, 0.4 steel + 2 x 0.12 PEI, from the maker's page ({WB_PLATE})"},
                 real_part={"maker": "Wham Bam Systems", "mpn": "PEX Flexi Plate 220 x 220", "sellers": [{"name": "whambam3d.com (maker direct, US)",
                                                                                                         "checked": "2026-11-20", "note": "$35.00, SOLD OUT on 2026-11-20"}],
                            "sold_by_maker": True, "datasheet": WB_PLATE, "ratings_source": {"steel_thickness_mm": "maker's page: 0.4 mm"}})


# ------------------------------------------------------------------ X / Y drive pulleys and idlers (owner, 2026-11-20)
@part
def pulley_mcmaster_3684n13() -> Stock:
    """McMaster-Carr 3684N13 GT2 timing pulley: 20 teeth, for belts up to 9 mm, 5 mm finished bore, one flange, two M4 set screws 90
    degrees apart in the hub. Dimensions from McMaster's STEP and drawing (vendor_docs/McMaster_3684N13_drawing.pdf): hub dia 15 x 8,
    toothed section OD 12.1 x 11, flange dia 15 x 1, 20 overall. Local frame: axis Z, the hub's end at Z=0, the flange at Z 19..20."""
    pd = 20 * 2.0 / math.pi
    shape = Pos(0, 0, 4.0) * Cylinder(7.5, 8.0) + Pos(0, 0, 13.5) * Cylinder(6.05, 11.0) + Pos(0, 0, 19.5) * Cylinder(7.5, 1.0)
    shape -= Pos(0, 0, 10.0) * Cylinder(2.5, 20.0)
    dwg = "vendor_docs/McMaster_3684N13_drawing.pdf"
    return Stock(shape, "GT2-20T-B5-W9", "McMaster-Carr 3684N13 GT2 pulley 20T, 9 mm belt, 5 mm bore, two set screws, one flange", 0.012,
                 material="al6061", cost_usd=5.99,
                 ratings={"pitch_diameter_mm": pd, "teeth": 20, "belt_pitch_mm": 2.0, "belt_width_mm": 9.0,
                          "mcmaster_pn": "3684N13", "mcmaster_pn_status": "confirmed: McMaster's STEP and drawing (Instinct REQ-013, 2026-11-20)"},
                 interfaces={"bore": 5.0, "height": 20.0, "belt_center_z": 13.5, "belt_center": [(0.0, 0.0, 13.5)], "set_screws": "2 x M4, 90 degrees, in the hub"},
                 model={"tolerance": {"volume_ratio": (0.6, 1.8)}, "no_auto_features": True},
                 real_part={"maker": "McMaster-Carr", "mpn": "3684N13", "sellers": [{"name": "McMaster-Carr", "part_number": "3684N13", "catalogue": True,
                                                                                    "checked": CHECKED, "note": "$5.99, in stock (owner)"}],
                            "datasheet": dwg, "ratings_source": {"pitch_diameter_mm": "GT2 20 teeth, 2 mm pitch (McMaster listing)", "teeth": "McMaster: 20",
                                                                 "belt_pitch_mm": "McMaster: GT2 2 mm", "belt_width_mm": "McMaster: for 9 mm max belt width"}},
                 source={"level": "vendor", "vendor": "McMaster-Carr", "part": "3684N13", "url": dwg, "retrieved": CHECKED, "unverified_fields": [],
                         "file": dwg})


@part
def idler_misumi_agtfw30() -> Stock:
    """MISUMI AGTFW30-GT2090-5 toothed idler: 30 teeth 2GT, 9 mm belt, 5 mm bore, bearings both sides, two flanges. Dimensions from
    MISUMI's STEP and catalogue pp.1424-1425: flanges dia 24, toothed section dia 18.5 x 10, 13.3 overall. Local frame: axis Z, one
    flange's face at Z=0; the belt's centre at Z=6.5."""
    pd = 30 * 2.0 / math.pi
    shape = Pos(0, 0, 0.75) * Cylinder(12.0, 1.5) + Pos(0, 0, 6.5) * Cylinder(9.26, 10.0) + Pos(0, 0, 12.4) * Cylinder(12.0, 1.8)
    shape -= Pos(0, 0, 6.65) * Cylinder(2.5, 13.3)
    dwg = "vendor_docs/Misumi_AGTFW_flanged-idlers-with-teeth_catalog_p1424-1425.pdf"
    return Stock(shape, "GT2-IDLER-30T-B5-W9", "MISUMI AGTFW30-GT2090-5 toothed idler 30T, 9 mm belt, 5 mm bore, bearings both sides", 0.025,
                 material="al6061", cost_usd=41.41,
                 ratings={"pitch_diameter_mm": pd, "teeth": 30, "belt_pitch_mm": 2.0, "belt_width_mm": 9.0},
                 interfaces={"bore": 5.0, "height": 13.3, "belt_center_z": 6.5, "belt_center": [(0.0, 0.0, 6.5)], "flange_dia": 24.0},
                 model={"tolerance": {"volume_ratio": (0.6, 1.8)}, "no_auto_features": True},
                 real_part={"maker": "MISUMI", "mpn": "AGTFW30-GT2090-5", "sellers": [{"name": "MISUMI USA", "part_number": "AGTFW30-GT2090-5", "catalogue": True,
                                                                                     "checked": CHECKED, "note": "$41.41 each (owner)"}],
                            "datasheet": dwg, "ratings_source": {k: "MISUMI catalogue p.1424: AGTFW30, 2GT, 9 mm" for k in
                                                                 ("pitch_diameter_mm", "teeth", "belt_pitch_mm", "belt_width_mm")}},
                 source={"level": "vendor", "vendor": "MISUMI", "part": "AGTFW30-GT2090-5", "url": dwg, "retrieved": CHECKED, "unverified_fields": [],
                         "file": dwg})


# ---- connectors and DIN rail re-made from the makers' public drawings (owner, 2026-11-20: JST / Molex / Phoenix CAD sits behind
# licence or sign-up forms, so these are faithful re-makes; every modelled dimension is the drawing's) ------------------------------
JST_XH = "vendor_docs/JST_XH_datasheet.pdf"
MOLEX_5557 = "vendor_docs/Molex_39-01-2020_drawing.pdf"
PHOENIX_NS35 = "vendor_docs/Phoenix_0801733_NS35-7.5-PERF_datasheet.pdf"
DK = {"name": "Digi-Key", "catalogue": True, "checked": CHECKED}


def _remake(dwg, what):
    return {"kind": "generated to standard", "remade_from": dwg, "no_auto_features": True, "source": f"re-made from {dwg}: {what}"}


@part
def jst_xhp_housing(n: int = 2) -> Stock:
    """JST XHP-n crimp housing (PA 6), 2.5 mm pitch. JST XH datasheet p.4: length B = 2.5 (n - 1) + 4.8 (XHP-2 7.3, -3 9.8, -4 12.3),
    height 7.5 (+0.25 lock), depth 5.7. Local frame: mating face on Z=0, wires out +Z, circuits along X centred."""
    if n not in (2, 3, 4):
        raise ValueError("XHP-2, -3 or -4")
    b = 2.5 * (n - 1) + 4.8
    s = Pos(0, 0, 7.5 / 2) * Box(b, 5.7, 7.5) + Pos(0, 5.7 / 2 + 0.125, 7.5 / 2) * Box(2.5, 0.25, 3.0)
    for i in range(n):
        s -= Pos((i - (n - 1) / 2) * 2.5, 0, 7.5 / 2) * Box(1.6, 1.6, 7.5)
    return _simple(f"JST-XHP-{n}", f"JST XHP-{n} housing, 2.5 mm pitch", s, 0.0002 * n, 0.1,
                   {"maker": "JST", "mpn": f"XHP-{n}", "sellers": [{**DK, "part_number": f"XHP-{n}"}],
                    "datasheet": JST_XH},
                   _remake(JST_XH, f"p.4 housing table: B {b:g}, height 7.5 + 0.25, depth 5.7; cavities 2.5 pitch (1.6 square drawn)"),
                   interfaces={"pitch": 2.5, "circuits": n}, material="nylon")


@part
def jst_xh_header(n: int = 2) -> Stock:
    """JST B<n>B-XH-A top-entry header (PA 66 wafer, tin-plated posts). JST XH datasheet p.5: B = 2.5 (n - 1) + 4.9 (B2B 7.4, B3B 9.9,
    B4B 12.4), depth 5.75, 7 above the board, posts 0.64 square 3.4 below, row 2.35 from the back; PCB holes dia 1.0 (2 circuits) /
    0.9 (3 or more), p.2. Local frame: board top Z=0, circuits along X centred, back face at Y=+5.75/2."""
    if n not in (2, 3, 4):
        raise ValueError("B2B, B3B or B4B")
    b = 2.5 * (n - 1) + 4.9
    shell = Pos(0, 0, 3.5) * Box(b, 5.75, 7.0) - Pos(0, -0.6, 4.0) * Box(b - 1.6, 4.55 - 0.4, 6.0)
    yp = 5.75 / 2 - 2.35
    for i in range(n):
        shell += Pos((i - (n - 1) / 2) * 2.5, yp, (6.5 - 3.4) / 2) * Box(0.64, 0.64, 6.5 + 3.4)        # posts 3.4 below the board
    holes = [((i - (n - 1) / 2) * 2.5, yp, 0.0) for i in range(n)]
    return _simple(f"JST-B{n}B-XH-A", f"JST B{n}B-XH-A header, top entry", shell, 0.0003 * n, 0.12,
                   {"maker": "JST", "mpn": f"B{n}B-XH-A", "sellers": [{**DK, "part_number": f"B{n}B-XH-A"}], "datasheet": JST_XH},
                   _remake(JST_XH, f"p.5 top-entry header: B {b:g}, 5.75 deep, 7 high, posts 0.64 sq x 3.4 below at 2.35 from the back"),
                   interfaces={"pcb_holes": holes, "pcb_hole_d": 1.0 if n == 2 else 0.9, "pitch": 2.5}, material="nylon")


@part
def jst_sxh_contact() -> Stock:
    """JST SXH-001T-P0.6 crimp contact (phosphor bronze, tin), AWG 28-22, insulation 0.9-1.9: shape B, 6.1 long, 1.95 wide, 2.4 high
    (JST XH datasheet p.3). Drawn as its envelope. Local frame: mating end at Z=0, crimp towards +Z."""
    s = Pos(0, 0, 6.1 / 2) * Box(1.95, 2.4, 6.1)
    return _simple("JST-SXH-001T-P0.6", "JST SXH-001T-P0.6 crimp contact", s, 0.00005, 0.03,
                   {"maker": "JST", "mpn": "SXH-001T-P0.6", "sellers": [{**DK, "part_number": "SXH-001T-P0.6"}], "datasheet": JST_XH},
                   _remake(JST_XH, "p.3 contact shape B: 6.1 x 1.95 x 2.4 envelope"), material="brass")


@part
def molex_minifit_39_01_2020() -> Stock:
    """Molex 39-01-2020 Mini-Fit Jr. receptacle housing, 2 circuits, dual row (nylon 6/6). Drawing SD-5557-003: width A 5.40 (2 ckt),
    9.6 across the rows (4.20 pitch), 11.6 body, 19.6 overall with the latch arm. Display model: Molex's STEP (CADENAS / 3dfindit, REQ-015;
    a simplified solid, no cavities): pin positions and the 4.20 pitch come from the drawing, not from it. Local frame: the STEP's own
    (X across, 5.4; Y along, 19.6, the latch arm towards -Y; Z across the rows, base Z=-0.25). The simulation solid is the drawing's
    body (5.4 x 9.85 x 11.6) and the 3.4-wide latch arm (12.1 high over 7.9) as the STEP has them."""
    s = Pos(0, 4.85, 4.675) * Box(5.4, 11.7, 9.85) + Pos(0, -4.95, 7.05) * Box(3.4, 7.9, 12.1) + Pos(0, 10.2, -0.625) * Box(5.4, 1.0, 0.75)   # + the STEP's 0.75 rib at the end
    return _simple("MOLEX-39-01-2020", "Molex 39-01-2020 Mini-Fit Jr. receptacle housing, 2 circuits", s, 0.0006, 0.27,
                   {"maker": "Molex", "mpn": "39-01-2020", "sellers": [{**DK, "part_number": "39-01-2020"}], "datasheet": MOLEX_5557},
                   _remake(MOLEX_5557, "SD-5557-003 sheet 1: A 5.40, 9.6 / 10.6, 19.6, latch 3.0 x 1.0 x 8.5, cavities 4.20 pitch (3.6 drawn)"),
                   material="nylon")


@part
def din_rail_phoenix(length: float = 100.0) -> Stock:
    """Phoenix Contact 0801733 NS 35/7,5 PERF steel rail (EN 60715), sold 2 m, cut to length by the builder. Datasheet drawing: 35 wide,
    27 between the walls, 7.5 high, 1 thick, slots 15 x 6.2 on 25 mm. Local frame: along X centred, base on Z=0."""
    t, w, h = 1.0, 35.0, 7.5
    sec = (Pos(0, 0, t / 2) * Box(length, 27.0, t) + Pos(0, 27.0 / 2 - t / 2, h / 2) * Box(length, t, h)
           + Pos(0, -27.0 / 2 + t / 2, h / 2) * Box(length, t, h) + Pos(0, (27.0 + w) / 4, h - t / 2) * Box(length, (w - 27.0) / 2, t)
           + Pos(0, -(27.0 + w) / 4, h - t / 2) * Box(length, (w - 27.0) / 2, t))
    n = int((length - 15.0) // 25.0) + 1
    xs = [(i - (n - 1) / 2) * 25.0 for i in range(n)]
    for x in xs:
        sec -= Pos(x, 0, t / 2) * (Box(15.0 - 6.2, 6.2, t) + Pos(-(15.0 - 6.2) / 2, 0, 0) * Cylinder(3.1, t)
                                   + Pos((15.0 - 6.2) / 2, 0, 0) * Cylinder(3.1, t))
    model, detail = _remake(PHOENIX_NS35, "35 / 27 / 7.5 / 1, slots 15 x 6.2 on 25"), None
    f = vc.find_file("DIN-RAIL-PHOENIX-0801733-2000", inbox_only=True)
    if f is not None:          # Phoenix's own 2 m STEP (3dfindit, REQ-015), cut to this length about a slot centre (odd count) or between two
        cx = 1000.0 if n % 2 else 1012.5

        def build():
            full = vc.solids_of(vc.load_step(f))
            return vc.bake(Pos(-cx, -17.5, 0) * (full & Pos(cx, 17.5, h / 2) * Box(length, 40.0, h + 2.0)))

        detail = vc.cached(f"phoenix_0801733:{length}", [f], build)
        model = {"kind": "vendor CAD", "file": f"vendor_cad/inbox/{f.name}", "no_auto_features": True,
                 "source": f"Phoenix Contact's STEP of the 2 m 0801733 (CADENAS / 3dfindit, REQ-015), cut to {length:g} mm as the builder cuts it"}
    return Stock(sec, f"DIN-RAIL-PHOENIX-0801733-{int(length)}", f"Phoenix 0801733 NS 35/7,5 PERF rail, cut to {length:g} mm",
                 0.0005 * length, material="steel", cost_usd=12.0 * length / 2000.0 + 0.5, interfaces={"slots": [(x, 0.0, 0.0) for x in xs], "top_z": h},
                 model=model, detail=detail,
                 real_part={"maker": "Phoenix Contact", "mpn": "0801733", "sellers": [{**DK, "part_number": "0801733"}],
                            "stock_size": "2 m, cut to length by the builder", "datasheet": PHOENIX_NS35})


@part
def foot_levelling_m5_placeholder() -> Stock:
    """PLACEHOLDER (owner, 2026-11-20; maker CAD via Instinct REQ-017): a levelling foot with an M5 stud and a firm rubber pad,
    drawn as a 25 x 8 mm pad-and-base disc and a 10 mm stud. Local frame: the base's top face on Z=0, stud up +Z, pad down."""
    s = Pos(0, 0, -4.0) * Cylinder(12.5, 8.0) + Pos(0, 0, 5.0) * Cylinder(2.5, 10.0)
    return Stock(s, "FOOT-LEVELLING-M5", "Levelling foot, M5 stud, firm rubber pad (placeholder: product pending REQ-017)", 0.02,
                 material="steel", cost_usd=3.0, ratings={"approximate": True},
                 interfaces={"stud": "M5", "stud_length": 10.0, "pad_d": 25.0},
                 model={"kind": "proxy", "state": "stand-in", "source": "placeholder outline: no product chosen yet (REQ-017)"})


@part
def spool_1kg_placeholder() -> Stock:
    """A full 1 kg filament spool as the envelope of Prusa Research's Prusament spool STEP (REQ-018: 199.89 OD x 64.13 wide, ribbed hub
    bore 51.25; 1 solid, 25 MB, too heavy for the verifier as a display model): 199.89 x 64.13 with a 51.25 bore, 1.25 kg with filament
    (owner's figure). Local frame: axis along Z, centred."""
    s = Cylinder(199.89 / 2, 64.13) - Cylinder(51.25 / 2, 64.13)
    return Stock(s, "SPOOL-1KG-FILAMENT", "1 kg filament spool, full (envelope of the Prusament spool STEP)", 1.25, material="pla",
                 cost_usd=29.99, ratings={"mass_full_kg": 1.25},
                 interfaces={"hub_bore": 51.25, "od": 199.89, "width": 64.13},
                 model={"kind": "generated to standard", "remade_from": "vendor_cad/staging/instinct_REQ-018/Prusament_dummy_spool_1kg.step.zip",
                        "no_auto_features": True, "source": "envelope of Prusa's spool STEP: 199.89 OD, 64.13 wide, 51.25 bore"},
                 real_part={"maker": "Prusa Research", "mpn": "Prusament PLA 1 kg (any colour)", "sellers": [{"name": "Prusa Research (US warehouse)",
                            "checked": "2026-11-20", "note": "filament: the owner's choice; price to confirm"}], "sold_by_maker": True})


@part
def spacer_tube_m8_placeholder(length: float) -> Stock:
    """PLACEHOLDER: an M8 spacer sleeve (12 OD x 8.4 ID) on the spool axle, product pending REQ-018. Local frame: axis Z, bottom Z=0."""
    s = Pos(0, 0, length / 2) * (Cylinder(6.0, length) - Cylinder(4.2, length))
    return Stock(s, f"SPACER-M8-12x8.4x{length:g}", f"M8 spacer sleeve 12 x 8.4 x {length:g} mm (placeholder)", 0.0001 * length,
                 material="al6061", cost_usd=1.0, ratings={"approximate": True}, interfaces={"length": length},
                 model={"kind": "proxy", "state": "stand-in", "source": "placeholder sleeve (REQ-018)"})


@part
def coupler_mcmaster_2333n214() -> Stock:
    """McMaster-Carr 2333N214 push-to-connect fitting for 4 mm OD tube, M10 x 1 male thread (3.0 mm path), $11.98 (REQ-018). Display
    model: McMaster's STEP. The SFS V2's port thread is ASSUMED M10 x 1 (the common PC4-M10 port; BTT's manual does not state it):
    check on arrival. Local frame: axis Z, centred, 19 long, 13 across the hex."""
    from build123d import RegularPolygon
    s = extrude(RegularPolygon(13.0 / 2, 6, major_radius=False), 19.0).moved(Pos(0, 0, -9.5))
    return Stock(s, "MCMASTER-2333N214", "McMaster 2333N214 push-to-connect fitting, 4 mm tube, M10 x 1", 0.01, material="brass", cost_usd=11.98,
                 model={"inbox": ["MCMASTER-2333N214"], "no_auto_features": True, "tolerance": {"volume_ratio": (0.8, 3.0), "mass_ratio": (0.2, 5.0)}},
                 real_part={"maker": "McMaster-Carr", "mpn": "2333N214", "sellers": [{"name": "McMaster-Carr", "part_number": "2333N214", "catalogue": True,
                            "checked": "2026-11-20", "note": "$11.98 each"}], "sold_by_maker": True})


NFJN_PAGE = "vendor_docs/Misumi_NFJN_leveling-mounts_2019US_p3166-3167.pdf"


@part
def foot_misumi_nfjn5_30() -> Stock:
    """MISUMI NFJN5-30 levelling mount ('Standard'): M5 x 30 screw on a 30 mm swivel foot, all metal (1018 steel, trivalent chromate),
    L 40.5, allowable vertical load 1.5 kN, 15 g (catalogue p.3166). Display model: MISUMI's STEP (solid, simplified; its mass is
    overridden by the catalogue's 15 g). Local frame: the foot's base on Z=0, screw up +Z (tip at Z=40.5)."""
    s = Pos(0, 0, 3.5) * Cylinder(15.0, 7.0) + Pos(0, 0, 7.0 + 33.5 / 2) * Cylinder(2.5, 33.5)
    return Stock(s, "NFJN5-30", "MISUMI NFJN5-30 levelling mount, M5 x 30, 30 mm swivel foot", 0.015, material="steel", cost_usd=4.32,
                 ratings={"allowable_vertical_load_n": 1500.0},
                 interfaces={"screw": "M5", "screw_length": 30.0, "overall": 40.5, "foot_d": 30.0},
                 model={"inbox": ["NFJN5-30"], "no_auto_features": True,
                        "tolerance": {"volume_ratio": (0.6, 1.7), "mass_ratio": (0.2, 3.0)}},
                 real_part={"maker": "MISUMI", "mpn": "NFJN5-30", "sellers": [{"name": "MISUMI USA", "part_number": "NFJN5-30", "catalogue": True,
                                                                             "checked": CHECKED, "note": "$4.32 each, ships Nov 24 (REQ-017)"}],
                            "datasheet": NFJN_PAGE, "ratings_source": {"allowable_vertical_load_n": "MISUMI p.3166 table: NFJN5-30 1.5 kN"}})


D2F_DS = "vendor_docs/Omron_D2F_datasheet_digikey_0318.pdf"


@part
def switch_omron_d2f_01l() -> Stock:
    """OMRON D2F-01L hinge-lever subminiature switch (gold-alloy contacts, 0.1 A 30 VDC, PCB terminals), re-made from OMRON's D2F data
    sheet (p.4): body 12.7 x 6.5 x 5.8, hinge lever free position 10 max / operating position 6.8 +/-1.5 from the mounting-hole line,
    overtravel 0.55 min, two 2.0 mm holes on 5.2. The same local frame and operating interfaces as `endstop_switch()` (whose 20 x 12.5
    board is now a separate fabricated carrier in the design), without the board: the switch's body lies on Z=1.6 (the carrier's
    top), lever towards +Y."""
    from . import details, endstop_switch

    base = endstop_switch()
    e = details.ENDSTOP
    bxr, byr, bzr = e["body_x"], e["body_y"], e["body_z"]
    body = Pos(0, (byr[0] + byr[1]) / 2, (bzr[0] + bzr[1]) / 2) * Box(bxr[1] - bxr[0], byr[1] - byr[0], bzr[1] - bzr[0])
    iface = {k: v for k, v in base.interfaces.items() if k != "mount_holes_m3"}
    return Stock(body, "ENDSTOP-OMRON-D2F-01L", "OMRON D2F-01L hinge-lever switch (gold contacts)", 0.0008, material="abs", cost_usd=1.44,
                 ratings=dict(base.ratings), interfaces=iface,
                 model={"kind": "generated to standard", "remade_from": D2F_DS, "no_auto_features": True,
                        "source": "re-made from OMRON's D2F data sheet p.4: body 12.7 x 6.5 x 5.8; lever and terminals not drawn (the lever's "
                                  "positions are interfaces: free, operating +/- spread, case limit)"},
                 real_part={"maker": "OMRON", "mpn": "D2F-01L", "sellers": [{"name": "Digi-Key", "part_number": "D2F-01L", "catalogue": True,
                            "checked": "2026-11-20", "note": "$1.44; Digi-Key and Mouser stock confirmed by the coordinator's API lookups"}],
                            "datasheet": D2F_DS, "ratings_source": {"operating_force_n": "OMRON D2F data sheet p.4: OF 0.78 N max (D2F-01L)"}})


@part
def spacer_mcmaster_94669a079() -> Stock:
    """McMaster-Carr 94669A079 aluminium unthreaded spacer for M5: OD 10.00, bore 5.30 (+0.30/0), length 10.00, $2.53 (REQ-019; drawing
    vendor_docs/McMaster_94669A079_Al_spacer_M5_10x10_drawing.pdf). Display model: McMaster's STEP. Local frame: axis Z, bottom Z=0."""
    s = Pos(0, 0, 5.0) * (Cylinder(5.0, 10.0) - Cylinder(2.65, 10.0))
    return Stock(s, "MCMASTER-94669A079", "McMaster 94669A079 aluminium spacer M5, 10 OD x 5.3 ID x 10", 0.0015, material="al6061", cost_usd=2.53,
                 interfaces={"od": 10.0, "bore": 5.3, "length": 10.0, "top": [(0.0, 0.0, 10.0)]},
                 model={"inbox": ["MCMASTER-94669A079"], "no_auto_features": True},
                 real_part={"maker": "McMaster-Carr", "mpn": "94669A079", "sellers": [{"name": "McMaster-Carr", "part_number": "94669A079", "catalogue": True,
                            "checked": "2026-11-21", "note": "$2.53"}], "sold_by_maker": True,
                            "datasheet": "vendor_docs/McMaster_94669A079_Al_spacer_M5_10x10_drawing.pdf"})


SFAL_PAGE = "vendor_docs/Misumi_SFAL_both-ends-threaded_shaft_catalog_p228-229.pdf"


@part
def shaft_misumi_sfal8(l_plain: int) -> Stock:
    """MISUMI SFAL8-<L>-B15-S15 both-ends-threaded linear shaft: 52100 steel, D 8 g6, M8 x 1.25 x 15 at both ends, overall L + 30 (MISUMI
    catalogue p.228; REQ-020's STEP of SFAL8-90 is the same family). Re-made from the catalogue drawing as a plain 8 mm rod (threads
    not drawn). Local frame: axis Z, one end at Z=0, `thread_ends` the two 15 mm zones."""
    L = float(l_plain) + 30.0
    s = Pos(0, 0, L / 2) * Cylinder(4.0, L)
    return Stock(s, f"SFAL8-{int(l_plain)}-B15-S15", f"MISUMI SFAL8-{int(l_plain)}-B15-S15 shaft, D8, M8 both ends, {L:g} overall", 0.0004 * L,
                 material="steel", cost_usd=37.87, interfaces={"length": L, "thread_ends": [(0.0, 15.0), (L - 15.0, L)]},
                 model={"kind": "generated to standard", "remade_from": SFAL_PAGE, "no_auto_features": True,
                        "source": f"re-made from MISUMI's SFAL page: D 8, L {int(l_plain)}, B = S = 15 (M8 x 1.25)"},
                 real_part={"maker": "MISUMI", "mpn": f"SFAL8-{int(l_plain)}-B15-S15", "sellers": [{"name": "MISUMI USA", "part_number": f"SFAL8-{int(l_plain)}-B15-S15",
                            "catalogue": True, "checked": "2026-11-21", "note": "SFAL8-90 was $37.87 (REQ-020); this L to confirm"}],
                            "datasheet": SFAL_PAGE})


@part
def dowel_pin_3x8_placeholder() -> Stock:
    """PLACEHOLDER (owner, 2026-11-21): a 4 x 8 mm hardened dowel pin, product pending (McMaster / MISUMI number with CAD). Local frame:
    axis Z, bottom at Z=0."""
    s = Pos(0, 0, 4.0) * Cylinder(2.0, 8.0)
    return Stock(s, "DOWEL-PIN-4x8", "Dowel pin 4 x 8 mm, hardened (placeholder)", 0.0008, material="steel", cost_usd=0.3,
                 ratings={"approximate": True},
                 model={"kind": "proxy", "state": "stand-in", "source": "placeholder pin 4 x 8 (product to be named)"})
