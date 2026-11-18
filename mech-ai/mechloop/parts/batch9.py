"""Catalogue part added from the ninth batch of vendor data (2026-11-18), for printer_v10's bed, sized to the nozzle's reach:

  print_sheet_pei235()           235 x 235 mm double-sided PEI spring-steel sheet with magnetic base (Creality and others)

No seller's page could be fetched from the session that added it: every figure is from web-search result snippets of
resellers' listings (source level "secondary"), so the part does not count as vendor-backed. Each value's source, and every
gap, is in mechloop/parts/vendor/creality_pei235.json and repeated in the part's `source` / `ratings`.
"""
from __future__ import annotations

from build123d import Box, Pos

from . import Stock, _source, part, vendor_data


@part
def print_sheet_pei235() -> Stock:
    """235 x 235 mm double-sided PEI spring-steel print sheet sold with a magnetic base (Creality's Ender-3 plate size; sold
    by many makers). Local frame: centred, underside on Z=0, print surface at Z=0.4. Only the steel is drawn; the listings
    disagree on thickness (0.4 mm on one, 1.2 mm overall on two: 0.4 mm of steel is drawn, as for `print_sheet_pei257`) and
    give no magnetic-base thickness (interfaces["magnetic_base_thickness"] is None). Mass from the steel alone. Join it to
    the magnetic base with design.join(sheet, base, "magnet")."""
    v = vendor_data("creality_pei235")["values"]
    sx, sy = v["size_mm"]
    t = v["steel_thickness_mm"]["value"]
    mass = round(sx * sy * t * 7.85e-6, 4)
    return Stock(Pos(0, 0, t / 2) * Box(sx, sy, t), "SHEET-PEI-235", "PEI spring-steel print sheet 235 x 235 x 0.4, double-sided, with magnetic base (Creality and others)",
                 mass, material="steel",
                 ratings={"approximate": True, "max_bed_temp_c": v["max_bed_temp_c"]["value"],
                          "magnetic_base_max_temp_c": v["max_bed_temp_c"]["value"],
                          "magnetic_base_max_temp_basis": "NOT read for this sheet: the 257 mm sheet's seller's 'maximum print bed temperature', carried over; "
                                                          "the base's own limit is not published",
                          "mass_basis": "computed: 235 x 235 x 0.4 mm of steel at 7850 kg/m3; the magnetic base and coating are not included",
                          "steel_grade": None, "print_surface": "PEI"},
                 interfaces={"size": (sx, sy), "thickness": t, "print_surface_z": t, "magnetic_base_thickness": None},
                 cost_usd=18.0,
                 source=_source("creality_pei235", "secondary", "235 x 235 dual-sided PEI plate",
                                unverified=("steel thickness (0.4 on one listing, 1.2 mm overall on two)", "mass_kg", "steel grade",
                                            "magnetic base thickness", "total stack thickness", "flatness", "cost",
                                            "max temperature (carried over from the 257 mm sheet's seller)"),
                                note="size and magnetic base are from snippets of resellers' listings; nothing was fetched"))
