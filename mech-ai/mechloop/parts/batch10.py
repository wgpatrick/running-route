"""Catalogue parts added for printer_v11 (2026-11-19):

  blower_gdb4010()              GDSTIME GDB4010 A-type 40 x 40 x 10 mm radial blower, 24 V (maker's data sheet, read by eye)
  leadscrew_nut_pom_ab4()       the POM anti-backlash nut the 17E19S1684AB4-330RA ships with (STAND-IN: estimated from photographs)
  print_sheet_pei220()          220 x 220 mm PEI spring-steel sheet with magnetic base (third-party sellers; secondary)
  bhcs_flanged(size, length)    ISO 7380-2 hexagon socket button head screw with collar (figures from distributors; secondary)

Each part says what is read, what is estimated and what is a stand-in, in its `source`, `ratings` and `model`.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Pos

from . import Stock, _source, part, vendor_data

INH2O_PA = 249.089
CFM_M3S = 4.71947e-4


@part
def blower_gdb4010() -> Stock:
    """GDSTIME GDB4010 A-type radial blower, 24 V, 9500 rpm, 0.08 A, 0.52 inH2O shut-off (maker's sheet). Local frame: the
    40 x 40 face in XY centred on the origin, 10 mm thick along Z (-5..5); the outlet (28 x 7.44 mm) on the -Y edge, air
    leaving along -Y. Four 2.2 mm holes on a 35 mm square (M2). The solid is the frame's envelope (the impeller is inside);
    the outlet's position across the thickness is not clear on the drawing and is taken as centred. Bearing type: NOT stated
    for this part (the family lists ball, sleeve and hydraulic)."""
    v = vendor_data("gdstime_gdb4010")["values"]
    sx, sy, sz = v["size_mm"]
    body = Box(sx, sy, sz)
    p = v["mount_holes"]["pitch_mm"] / 2
    holes = [(x, y, -sz / 2) for x in (-p, p) for y in (-p, p)]
    for x, y, _ in holes:
        body -= Pos(x, y, 0) * Cylinder(v["mount_holes"]["dia_mm"] / 2, sz)
    ol, ow = v["outlet_mm"]["length"], v["outlet_mm"]["width"]
    pq = v["pq_curve_9500rpm_cfm_inh2o"]["points"]
    return Stock(body, "BLOWER-4010-24V-GDB4010", "Radial blower 40 x 40 x 10 mm, 24 V (GDSTIME GDB4010 A-type)", v["mass_g"] / 1000.0,
                 material="abs", cost_usd=6.0,
                 detail=body, model={"kind": "proxy", "source": "envelope from the maker's dimension drawing (40 x 40 x 10, holes on 35, "
                                     "outlet 28 x 7.44); the maker offers no CAD", "state": "stand-in"},
                 interfaces={"mount_holes_m2": holes, "mount_hole_dia": v["mount_holes"]["dia_mm"],
                             "outlet_centre": [(0.0, -sy / 2, 0.0)], "outlet_size": (ol, ow), "outlet_direction": (0.0, -1.0, 0.0),
                             "thickness": sz},
                 ratings={"electrical": {"kind": "fan", "ports": {"in": dict(kind="fan", connector="JST-XH", max_a=3.0)},
                                         "ratings": {"current_a": v["rated_current_a"], "volts": v["rated_voltage_v"]},
                                         "sources": {"current_a": "GDSTIME GDB4010 data sheet: 24 V 0.08 A",
                                                     "volts": "GDSTIME GDB4010 data sheet: 24 V DC"}, "params": {},
                                         "product": dict(product="24 V radial blower 40 x 40 x 10 mm, 2-wire (GDSTIME GDB4010 A-type)",
                                                         vendor="GDSTIME", part_number="GDB4010 (24 V)", form="component",
                                                         off_the_shelf=True, custom_pcb=False, builder_work="crimp a 2-way JST-XH")},
                          "rated_voltage_v": v["rated_voltage_v"], "rated_current_a": v["rated_current_a"],
                          "speed_rpm": v["speed_rpm"], "static_pressure_pa": round(v["max_static_pressure_inh2o"] * INH2O_PA, 1),
                          "air_flow_cfm": pq[-1][0], "air_flow_m3_min": round(pq[-1][0] * 0.0283168, 4),
                          "pq_curve_cfm_inh2o": [tuple(x) for x in pq], "noise_dba": v["noise_dba"], "vendor_part": "GDB4010 (A-type), 24 V",
                          "bearing": "NOT STATED (ball / sleeve / hydraulic: unverified)",
                          "rated_current_source": "GDSTIME GDB4010 data sheet: 24 V 0.08 A",
                          "rated_voltage_source": "GDSTIME GDB4010 data sheet: 24 V DC"},
                 source=_source("gdstime_gdb4010", "partial", "GDB4010 A-type 24 V",
                                unverified=("bearing type", "outlet position across the thickness", "P-Q points (read by eye)", "cost"),
                                note="size, holes, outlet, voltage, current, speed, pressure, noise, mass and the P-Q curve are the maker's sheet"))


def blower_flow_estimate(outlet_area_mm2: float, k_total: float, pq=None, rho: float = 1.2) -> dict:
    """Operating point of the blower on a duct whose loss is k_total x (1/2 rho v^2) at the outlet velocity v: where the
    maker's P-Q curve meets the duct's curve. An ESTIMATE: K values from handbook figures, the P-Q curve read by eye."""
    pq = pq or vendor_data("gdstime_gdb4010")["values"]["pq_curve_9500rpm_cfm_inh2o"]["points"]

    def fan_pa(q_cfm):
        for (q0, p0), (q1, p1) in zip(pq, pq[1:]):
            if q0 <= q_cfm <= q1:
                return (p0 + (p1 - p0) * (q_cfm - q0) / (q1 - q0)) * INH2O_PA
        return 0.0

    def duct_pa(q_cfm):
        v = q_cfm * CFM_M3S / (outlet_area_mm2 * 1e-6)
        return k_total * 0.5 * rho * v * v

    lo, hi = 0.0, pq[-1][0]
    for _ in range(60):
        mid = (lo + hi) / 2
        if fan_pa(mid) > duct_pa(mid):
            lo = mid
        else:
            hi = mid
    q = (lo + hi) / 2
    v = q * CFM_M3S / (outlet_area_mm2 * 1e-6)
    return {"flow_cfm": round(q, 3), "flow_l_per_min": round(q * 28.3168, 1), "outlet_velocity_m_s": round(v, 1),
            "pressure_pa": round(fan_pa(q), 1), "outlet_area_mm2": round(outlet_area_mm2, 1), "k_total": k_total,
            "free_air_cfm": pq[-1][0], "shutoff_pa": round(pq[0][1] * INH2O_PA, 1)}


AB4_NUT = "NUT-T8x2-POM-AB-17E19S1684AB4"


@part
def leadscrew_nut_pom_ab4() -> Stock:
    """The anti-backlash nut StepperOnline ships on the 17E19S1684AB4-330RA's Tr8x2 screw: black POM, square flange with
    four holes, a barrel holding a spring and a second half-nut. STAND-IN: no dimension is published on the product page and
    the datasheet could not be fetched; flange 23 x 23 x 6, barrel 12.7 x 26, holes 4 x 3.4 on 16 mm are ESTIMATED from the
    maker's photographs scaled to the 42 mm motor (+/-1.5 mm). Local frame: axis Z, the flange's flat face (the face the
    carrier's nut plate bears on) at Z=0, flange below to Z=-6, barrel below to Z=-32. Bought with the motor: no cost."""
    v = vendor_data("stepperonline_17e19_ab4")["values"]["nut"]["standin_2026_11_19"]
    fw, _, ft = v["flange_mm"]
    bd, bl = v["barrel_dia_mm"], v["barrel_length_below_flange_mm"]
    h = v["holes"]["square_mm"] / 2
    shape = Pos(0, 0, -ft / 2) * Box(fw, fw, ft) + Pos(0, 0, -ft - bl / 2) * Cylinder(bd / 2, bl)
    shape -= Pos(0, 0, -(ft + bl) / 2) * Cylinder(4.0, ft + bl)
    holes = [(sx * h, sy * h, 0.0) for sx in (-1, 1) for sy in (-1, 1)]
    for x, y, _ in holes:
        shape -= Pos(x, y, -ft / 2) * Cylinder(v["holes"]["dia_mm"] / 2, ft)
    vol = fw * fw * ft + math.pi * (bd / 2) ** 2 * bl - math.pi * 16 * (ft + bl)
    return Stock(shape, AB4_NUT, "POM anti-backlash nut, square flange, for Tr8x2 (supplied on the 17E19S1684AB4-330RA; STAND-IN dimensions)",
                 round(vol * 1.41e-6 + 0.002, 4), material="abs", cost_usd=0.0,
                 detail=shape, model={"kind": "proxy", "state": "stand-in",
                                      "source": "dimensions ESTIMATED from the maker's product photographs (no drawing published)"},
                 interfaces={"flange_width": fw, "flange_thickness": ft, "barrel_dia": bd, "barrel_length": bl,
                             "mount_holes_m3": holes, "hole_dia": v["holes"]["dia_mm"], "flange_dia": fw},
                 ratings={"approximate": True, "material_as_seen": "POM (acetal)", "anti_backlash": True, "backlash_mm": 0.0,
                          "backlash_basis": v["backlash_mm"]["status"], "bought_with": "17E19S1684AB4-330RA"},
                 source=_source("stepperonline_17e19_ab4", "proxy", AB4_NUT,
                                unverified=("every dimension (estimated from photographs)", "material grade", "preload", "mass"),
                                note=v["basis"]))


@part
def print_sheet_pei220() -> Stock:
    """220 x 220 mm PEI spring-steel print sheet with a magnetic base (a common third-party size; no Creality part of this
    size was found). Local frame: centred, underside on Z=0, print surface at Z=0.4. Only the 0.4 mm steel is drawn. The
    magnetic base's thickness and temperature rating are not published by any seller read."""
    v = vendor_data("generic_pei220")["values"]
    sx, sy = v["size_mm"]
    t = v["steel_thickness_mm"]["value"]
    return Stock(Pos(0, 0, t / 2) * Box(sx, sy, t), "SHEET-PEI-220", "PEI spring-steel print sheet 220 x 220 x 0.4 with magnetic base (third-party sellers)",
                 round(sx * sy * t * 7.85e-6, 4), material="steel", cost_usd=v["price_usd"]["value"],
                 ratings={"approximate": True, "max_bed_temp_c": v["max_temp_c"]["value"], "max_temp_basis": v["max_temp_c"]["basis"],
                          "print_surface": "PEI (textured, as the owner wants)", "steel_grade": None},
                 interfaces={"size": (sx, sy), "thickness": t, "print_surface_z": t, "magnetic_base_thickness": None},
                 source=_source("generic_pei220", "secondary", "220 x 220 PEI spring-steel sheet with magnetic base",
                                unverified=("seller", "steel grade", "magnetic base thickness and temperature rating", "flatness", "mass"),
                                note="size, 0.4 mm steel and 130 degC are resellers' listings read only through search snippets"))


BHCS_FL = {"M4": None, "M5": None}


@part
def bhcs_flanged(size: str = "M5", length: float = 8.0) -> Stock:
    """Hexagon socket button head screw with collar, ISO 7380-2 (flanged button head). Local frame as `shcs`: underside of
    the collar at Z=0, thread along -Z. M5: collar 11.8, head 2.75 high, button 9.5, 3 mm key (distributors' listings,
    secondary); the collar is what bears, so it covers a 6 mm slot without a washer. Generated solid: a stand-in until the
    supplier's STEP is in vendor_cad/inbox/ under the SKU BHCS-FL-<size>x<length>."""
    from . import SCREW

    tab = vendor_data("iso7380_2")["values"]
    if size not in tab:
        raise ValueError(f"bhcs_flanged: size one of {sorted(tab)}")
    v = tab[size]
    d = SCREW[size][0]
    dc, k, dk, kc = v["collar_dia_dc"], v["head_height_k"], v["button_dia_dk"], v["collar_height"]
    shape = (Pos(0, 0, -length / 2) * Cylinder(d / 2, length) + Pos(0, 0, kc / 2) * Cylinder(dc / 2, kc)
             + Pos(0, 0, kc + (k - kc) / 2) * Cylinder(dk / 2, k - kc))
    mass = (math.pi * (d / 2) ** 2 * length + math.pi * (dc / 2) ** 2 * kc + math.pi * (dk / 2) ** 2 * (k - kc) * 0.7) * 7.85e-6
    sku = f"BHCS-FL-{size}x{length:g}"
    return Stock(shape, sku, f"Flanged button head screw {size} x {length:g} (ISO 7380-2)", round(mass, 5),
                 detail=shape, model={"kind": "generated to standard", "state": "stand-in",
                                      "source": "ISO 7380-2 figures from distributors' listings (collar, head height, button), plain solids"},
                 ratings={"proof_load_n": SCREW[size][6] * 0.8, "head": "flanged_button"},
                 interfaces={"thread_d": d, "head_d": dc, "head_h": k, "hex_key": v["hex_s"], "head": "flanged_button",
                             "button_dia": dk, "collar_height": kc},
                 cost_usd=0.12,
                 source=_source("iso7380_2", "secondary", f"ISO 7380-2 {size}", unverified=("every head dimension (listings, not the standard)",
                                                                                         "proof_load_n"), note=v["basis"]))
