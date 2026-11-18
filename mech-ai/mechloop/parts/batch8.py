"""Catalogue parts added from the eighth batch of vendor data (2026-11-18), for printer_v9's sprung bed:

  die_spring_dj8x20(installed)   Century Spring DJ-8X20YCS: metric (JIS) die spring, 8 mm hole x 4 mm rod x 20 mm, 7.6 N/mm
  thumb_nut_din466(size)         high knurled thumb nut DIN 466 (Halder EH 24780), M4 only
  print_sheet_pei257()           257 x 257 mm double-sided PEI spring-steel sheet with magnetic base (3DJAKE and others)
  add_thumb_nut(...)             place a thumb nut on a screw, as add_nut does a hex nut

None of the three makers' sites could be reached from the session that added them: every figure is from web-search result
snippets of the makers' pages (source level "secondary"), so none of these parts counts as vendor-backed. Each value's
source, and every gap, is in the part's vendor file (mechloop/parts/vendor/) and repeated in the part's `source` / `ratings`.
"""
from __future__ import annotations

import math

from build123d import Box, Cylinder, Location, Plane, Pos, Vector

from . import SCREW, Stock, _source, part, place, vendor_data


@part
def die_spring_dj8x20(installed: float | None = None) -> Stock:
    """Century Spring DJ-8X20YCS: metric (JIS) die spring, extra light duty (yellow), for an 8 mm hole and a 4 mm rod, 20 mm
    free length, chrome-alloy steel, 7.6 N/mm (58.8 / 68.6 / 78.5 N at 8 / 9 / 10 mm of deflection). It goes over an M4
    screw. Local frame: axis Z, bottom at Z=0. `installed` draws it at its compressed height (10 to 20 mm: the maker lists
    no deflection beyond 10 mm); ratings["preload_n"] is then the force it pushes with. Drawn as a plain tube 7.6 OD x 4.4
    ID: the coil's real diameters and wire are NOT published in what was read, only the hole and rod it fits."""
    v = vendor_data("century_spring_dj8x20")["values"]["DJ-8X20YCS"]
    L0, k = float(v["free_length_mm"]), float(v["rate_n_per_mm"])
    max_defl = max(p["deflection_mm"] for p in v["load_points"])
    h = float(installed) if installed is not None else L0
    if not L0 - max_defl - 1e-9 <= h <= L0 + 1e-9:
        raise ValueError(f"die_spring_dj8x20: installed height must be between {L0 - max_defl:g} and {L0:g} mm")
    od, bore = 7.6, 4.4
    body = Pos(0, 0, h / 2) * (Cylinder(od / 2, h) - Cylinder(bore / 2, h))
    return Stock(body, "SPRING-DIE-DJ-8X20YCS", "Die spring DJ-8X20YCS (8 hole x 4 rod x 20 mm, yellow, 7.6 N/mm; Century Spring)", 0.0026,
                 material="steel", cost_usd=1.5,
                 ratings={"approximate": True, "rate_n_per_mm": k, "free_length_mm": L0, "installed_height_mm": h,
                          "preload_n": round(k * (L0 - h), 2), "max_deflection_mm": max_defl,
                          "load_points": [(p["deflection_mm"], p["load_n"]) for p in v["load_points"]],
                          "hole_mm": v["hole_mm"], "rod_mm": v["rod_mm"], "material_as_listed": v["material"],
                          "max_temp_c": None, "max_temp_basis": "NOT obtained (chrome-alloy die spring; recalled as well above 100 degC)"},
                 interfaces={"od": od, "bore": bore, "free_length": L0, "top": [(0.0, 0.0, h)]},
                 source=_source("century_spring_dj8x20", "secondary", "DJ-8X20YCS",
                                unverified=("coil OD / ID (drawn 7.6 / 4.4)", "mass_kg", "max temperature", "solid height",
                                            "allowed deflection for life", "cost", "rate (7.6 N/mm listed; the listed load points imply 7.4 to 7.9)"),
                                note="read through web-search snippets of the maker's product page only"))


@part
def thumb_nut_din466(size: str = "M4") -> Stock:
    """High knurled thumb nut DIN 466, stainless 1.4305 (Halder EH 24780.0240 for M4): knurled head 16 dia x 3.5, collar
    8 dia, 9.5 mm high overall, 6.7 g. Local frame: axis Z, the COLLAR's end face (the face that bears on the part) at Z=0,
    the knurled head at the far end. Only M4 was read. The solid has no hole, like the catalogue's hex nuts: the thread
    is its overlap with the screw."""
    tab = vendor_data("halder_din466")["values"]
    if size not in tab:
        raise ValueError(f"thumb_nut_din466: only {sorted(tab)} recorded")
    v = tab[size]
    d2, d3, h, kk = v["knurl_dia_d2_mm"], v["collar_dia_d3_mm"], v["height_h_mm"], v["knurl_height_k_mm"]
    body = Pos(0, 0, (h - kk) / 2) * Cylinder(d3 / 2, h - kk) + Pos(0, 0, h - kk / 2) * Cylinder(d2 / 2, kk)
    return Stock(body, f"THUMBNUT-DIN466-{size}", f"Knurled thumb nut {size}, DIN 466 high type, {d2:g} x {h:g} mm, stainless (Halder {v['article']})",
                 v["mass_g"] / 1000.0, material="stainless304", cost_usd=1.2,
                 ratings={"approximate": True, "thread": v["thread"], "material_as_listed": v["material"]},
                 interfaces={"knurl_dia": d2, "collar_dia": d3, "height": h, "knurl_height": kk, "thread_d": SCREW[size][0]},
                 source=_source("halder_din466", "secondary", f"DIN 466 {size} ({v['article']})",
                                unverified=("thread length (taken as through)", "cost", "every dimension (snippet of the maker's data sheet)"),
                                note="read through web-search snippets of the maker's data sheet only"))


def add_thumb_nut(design, name: str, size: str, at, direction=(0, 0, -1), body: str = "world", screw: str | None = None):
    """Place a DIN 466 thumb nut with its collar's end face at `at`, the nut extending along `direction`; `screw=` records
    the screw it runs on (a thread join, as add_nut)."""
    dvec = Vector(*direction).normalized()
    c = place(design, name, thumb_nut_din466(size), Location(Plane(origin=at, z_dir=dvec)), body=body)
    if screw:
        design.join(screw, name, "thread")
        design.allow_overlap(screw, name)
        design.get(screw).meta.setdefault("threads_into", []).append(name)
    return c


@part
def print_sheet_pei257() -> Stock:
    """257 x 257 mm double-sided textured PEI spring-steel print sheet sold with a magnetic base (3DJAKE 'Textured PEI Build
    Plate - Dual Sided'; the Bambu Lab plate size, sold by many makers). Local frame: centred, underside on Z=0, print
    surface at Z=0.4. Only the steel is drawn; the seller publishes no thickness (0.4 mm is a third-party figure for the
    same kind of plate) and no magnetic-base thickness (interfaces["magnetic_base_thickness"] is None). Mass from the
    steel alone. Join it to the magnetic base with design.join(sheet, base, "magnet")."""
    v = vendor_data("threedjake_pei257")["values"]
    sx, sy = v["size_mm"]
    t = v["steel_thickness_mm"]["value"]
    mass = round(sx * sy * t * 7.85e-6, 4)
    return Stock(Pos(0, 0, t / 2) * Box(sx, sy, t), "SHEET-PEI-257", "PEI spring-steel print sheet 257 x 257 x 0.4, double-sided, with magnetic base (3DJAKE and others)",
                 mass, material="steel",
                 ratings={"approximate": True, "max_bed_temp_c": v["max_bed_temp_c"]["value"],
                          "magnetic_base_max_temp_c": v["max_bed_temp_c"]["value"],
                          "magnetic_base_max_temp_basis": "seller's 'maximum print bed temperature' for the plate; the base's own limit is not published",
                          "mass_basis": "computed: 257 x 257 x 0.4 mm of steel at 7850 kg/m3; the magnetic base and coating are not included",
                          "steel_grade": None, "print_surface": "PEI"},
                 interfaces={"size": (sx, sy), "thickness": t, "print_surface_z": t, "magnetic_base_thickness": None},
                 cost_usd=20.0,
                 source=_source("threedjake_pei257", "secondary", "257 x 257 dual-sided PEI plate",
                                unverified=("steel thickness (third-party figure)", "mass_kg", "steel grade", "magnetic base thickness",
                                            "total stack thickness", "flatness", "cost", "max temperature (seller's claim, snippet)"),
                                note="size, magnetic base and the 120 degC claim are from snippets of the seller's page; nothing was fetched"))
