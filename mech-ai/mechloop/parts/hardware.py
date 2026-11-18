"""Bought small hardware as catalog parts: round unthreaded spacers and silicone bed-levelling columns.

Vendor-backed: Pololu's nylon spacers for M2.5 and M3 screws (item numbers and sizes read from pololu.com). Everything
else here was only seen through search-result snippets or is a usual size, and says so: `verified` stays False.
See mechloop/parts/vendor/pololu_spacers.json, openbuilds_spacers.json, silicone_bed_column.json and docs/VENDOR_DATA.md.
"""
from __future__ import annotations

import math

from build123d import Cylinder, Pos

from . import Stock, _source, part, vendor_data

_DENSITY = {"nylon": 1.14e-6, "aluminium": 2.70e-6}          # kg/mm^3: PA66 and aluminium, typical (mass is not on any page)
_MATERIAL = {"nylon": "nylon_pa12", "aluminium": "al6061"}   # nearest entries of the materials table
# sizes with no source at all: usual catalogue sizes (od, id), no part number
_GENERIC = {("M3", "aluminium"): (6.0, 3.2), ("M5", "nylon"): (10.0, 5.3), ("M4", "nylon"): (8.0, 4.3), ("M4", "aluminium"): (8.0, 4.3),
            ("M2.5", "aluminium"): (5.0, 2.7)}
SPACER_SIZES = ("M2.5", "M3", "M4", "M5")
SPACER_MATERIALS = ("nylon", "aluminium")


def spacer_lengths(size: str = "M3", material: str = "nylon") -> list[float]:
    """Lengths a named vendor range offers for this size and material (empty when there is no sourced range)."""
    if material == "nylon" and size in vendor_data("pololu_spacers")["ranges"]:
        return sorted(float(k) for k in vendor_data("pololu_spacers")["ranges"][size]["items"])
    if material == "aluminium" and size == "M5":
        v = vendor_data("openbuilds_spacers")["values"]
        return sorted(v["lengths_seen_in_snippets_mm"] + v["lengths_recalled_mm"])
    return []


@part
def spacer_round(size: str = "M3", length: float = 6.0, material: str = "nylon") -> Stock:
    """Round unthreaded spacer (a plain sleeve a screw passes through). Local frame: axis Z, bottom at Z=0.
    nylon M2.5 (4 OD x 2.7 ID) and M3 (5 OD x 3.3 ID): Pololu items 1970-1988 in the lengths of `spacer_lengths()`,
    vendor-backed. aluminium M5 (10 OD x 5.1 ID): OpenBuilds range, known only from search snippets. Any other
    size/material or length: a usual size with no part number, unverified."""
    if size not in SPACER_SIZES or material not in SPACER_MATERIALS:
        raise ValueError(f"spacer_round: size one of {SPACER_SIZES}, material one of {SPACER_MATERIALS}")
    src, pn, note = {}, None, ""
    stock_len = float(length) in spacer_lengths(size, material)
    if material == "nylon" and size in vendor_data("pololu_spacers")["ranges"]:
        r = vendor_data("pololu_spacers")["ranges"][size]
        od, bore = r["od_mm"], r["id_mm"]
        if stock_len:
            it = r["items"][f"{length:g}"]
            pn = f"Pololu {it['pololu_item']}"
            src = _source("pololu_spacers", "vendor", pn, f"https://www.pololu.com/product/{it['pololu_item']}",
                          unverified=("mass_kg (from the volume at 1.14 g/cm^3)", "nylon grade"), note=f"sold in packs of {it['pack']}")
        else:
            src = _source("pololu_spacers", "partial", None, unverified=("length",),
                          note=f"{length:g} mm is not a length of the Pololu range {spacer_lengths(size, material)}: cut one down or pick a stock length")
    elif material == "aluminium" and size == "M5":
        v = vendor_data("openbuilds_spacers")["values"]
        od, bore = v["od_mm"], v["id_mm"]
        src = _source("openbuilds_spacers", "secondary", None, unverified=("part number", "mass_kg") + (() if stock_len else ("length",)),
                      note="OpenBuilds 10 mm OD x M5 aluminium spacers, seen only in search-result snippets (3, 6 and 13.2 mm confirmed there)"
                           + ("" if stock_len else f"; {length:g} mm is not a known length of the range"))
    else:
        od, bore = _GENERIC[(size, material)]
        note = "usual size, no vendor range recorded"
    body = Pos(0, 0, length / 2) * (Cylinder(od / 2, length) - Cylinder(bore / 2, length))
    mass = math.pi * (od ** 2 - bore ** 2) / 4 * length * _DENSITY[material]
    tag = {"nylon": "NYLON", "aluminium": "AL"}[material]
    return Stock(body, f"SPACER-{tag}-{size}-{od:g}x{bore:g}x{length:g}",
                 f"Round {material} spacer for {size}, {od:g} OD x {bore:g} ID x {length:g} mm" + (f" ({pn})" if pn else ""), mass,
                 material=_MATERIAL[material], cost_usd={"nylon": 0.07, "aluminium": 0.6}[material],
                 ratings={"approximate": True, "screw": size, **({"vendor_part": pn} if pn else {}), **({"note": note} if note else {})},
                 interfaces={"od": od, "bore": bore, "length": float(length), "top": [(0.0, 0.0, float(length))]}, source=src)


@part
def bed_column_silicone(height: float = 18.0, installed: float | None = None) -> Stock:
    """Silicone bed-levelling column (solid bed mount that replaces a spring): 16 OD x 4 bore, 18 mm (high) or 16.2 mm
    (short) free height. Local frame: axis Z, bottom at Z=0. `installed` draws it at its compressed height (the solid
    keeps its diameter). Sizes are from reseller listings seen in search snippets only; stiffness is not sourced.
    Material is the table's belt rubber (E = 50 MPa): real silicone is several times softer."""
    v = vendor_data("silicone_bed_column")["values"]
    if height not in v["heights_mm"]:
        raise ValueError(f"bed_column_silicone height must be one of {v['heights_mm']}")
    h = float(installed) if installed is not None else float(height)
    if not 0.6 * height <= h <= height:
        raise ValueError("bed_column_silicone: installed height must be between 60 % and 100 % of the free height")
    od, bore = v["od_mm"], v["id_mm"]
    body = Pos(0, 0, h / 2) * (Cylinder(od / 2, h) - Cylinder(bore / 2, h))
    mass = math.pi * (od ** 2 - bore ** 2) / 4 * height * 1.15e-6       # silicone about 1.15 g/cm^3, typical
    return Stock(body, f"BED-COLUMN-SIL-16x{height:g}", f"Silicone bed levelling column 16 OD x 4 bore x {height:g} mm", mass,
                 material="rubber_gt2", cost_usd=0.6,
                 ratings={"approximate": True, "free_height_mm": float(height), "installed_height_mm": h,
                          "max_temp_c_seller_claim": v["max_temperature_c_seller_claim"]},
                 interfaces={"od": od, "bore": bore, "free_height": float(height), "top": [(0.0, 0.0, h)]},
                 source=_source("silicone_bed_column", "secondary", None,
                                unverified=("stiffness / hardness", "mass_kg", "max temperature (seller claim)", "maker"),
                                note="16 x 4 x 18 / 16.2 mm from two reseller listings seen in search snippets; no maker's drawing"))


# ISO 7089 (normal series, DIN 125 A) and ISO 7093-1 (large series, DIN 9021): (inside d1, outside d2, thickness h), mm.
# Nominal (min) inside diameter, nominal outside diameter, mid of the thickness limits, from a distributor's reproduction
# of the standards' tables: vendor_cad/staging/practice_refs/06_RC_ISO_washers.pdf, page 1 (ISO 7089: M2.5 2.7-2.84 /
# 6 / 0.45-0.55 ... M8 8.4-8.62 / 16 / 1.4-1.8) and page 3 (ISO 7093: M3 3.2 / 9 / 0.7-0.9 ... M8 8.4 / 24 / 1.8-2.2).
# ISO 7093-1's scope starts at M3 (no large M2.5). A distributor's table, not the licensed standard.
WASHER = {"normal": {"M2.5": (2.7, 6.0, 0.5), "M3": (3.2, 7.0, 0.5), "M4": (4.3, 9.0, 0.8), "M5": (5.3, 10.0, 1.0),
                     "M6": (6.4, 12.0, 1.6), "M8": (8.4, 16.0, 1.6)},
          "large": {"M3": (3.2, 9.0, 0.8), "M4": (4.3, 12.0, 1.0), "M5": (5.3, 15.0, 1.2), "M6": (6.4, 18.0, 1.6),
                    "M8": (8.4, 24.0, 2.0)}}


@part
def washer_flat(size: str = "M3", series: str = "normal") -> Stock:
    """Plain flat steel washer. Local frame: axis Z, the face that bears on the part at Z=0, washer above.
    series "normal": ISO 7089 (DIN 125 A), M2.5 to M8; "large": ISO 7093-1 (DIN 9021), M3 to M8, for slots and soft
    seats. Nominal sizes of the standards, generated (no vendor part number); SKU WASHER-<size>[-LARGE]."""
    if series not in WASHER or size not in WASHER[series]:
        raise ValueError(f"washer_flat: series one of {tuple(WASHER)}, size one of {tuple(WASHER.get(series, {}))}")
    d1, d2, h = WASHER[series][size]
    body = Pos(0, 0, h / 2) * (Cylinder(d2 / 2, h) - Cylinder(d1 / 2, h))
    std = "ISO 7089" if series == "normal" else "ISO 7093-1"
    return Stock(body, f"WASHER-{size}" + ("-LARGE" if series == "large" else ""),
                 f"Flat washer {size}, {d2:g} x {d1:g} x {h:g} mm ({std})", math.pi * (d2 ** 2 - d1 ** 2) / 4 * h * 7.85e-6,
                 material="steel", cost_usd=0.02, ratings={"approximate": True, "screw": size},
                 interfaces={"od": d2, "bore": d1, "thickness": h},
                 # the ring at the standard's nominal sizes IS the standard's shape (no chamfer is specified for the display):
                 # a placeholder until the supplier's STEP is in vendor_cad/inbox/ under the SKU
                 detail=body, model={"kind": "generated to standard", "source": f"{std} nominal outside diameter, bore and thickness "
                                     f"(plain ring, generated); placeholder for the supplier's CAD",
                                     "tolerance": {"volume_ratio": (0.8, 1.25)}},
                 source=_source("iso_fasteners", "standard", f"{std} {size}", unverified=("mass_kg",),
                         note="dimensions: vendor_cad/staging/practice_refs/06_RC_ISO_washers.pdf (distributor's table of the standard)"))


# DIN 6797 form J (internal teeth) lock washers, for an earth bond: (bore d1, outside d2, material thickness s), mm.
# RECALLED from the standard's table (not fetched); bd_warehouse draws the same sizes for its display model.
WASHER_TOOTHED = {"M3": (3.2, 6.0, 0.4), "M4": (4.3, 8.0, 0.5), "M5": (5.3, 10.0, 0.6), "M6": (6.4, 11.0, 0.7)}


@part
def washer_toothed(size: str = "M5") -> Stock:
    """Internal-tooth lock washer (DIN 6797 J), for a protective-earth stud: its teeth bite through anodising and paint.
    Local frame: axis Z, the face on the part at Z=0, washer above. The simulation solid is a plain ring of the
    material thickness (the teeth's set is not drawn); SKU WASHER-<size>-SERRATED. Dimensions recalled, not fetched."""
    if size not in WASHER_TOOTHED:
        raise ValueError(f"washer_toothed: size one of {tuple(WASHER_TOOTHED)}")
    d1, d2, h = WASHER_TOOTHED[size]
    body = Pos(0, 0, h / 2) * (Cylinder(d2 / 2, h) - Cylinder(d1 / 2, h))
    return Stock(body, f"WASHER-{size}-SERRATED", f"Internal-tooth lock washer {size}, {d2:g} x {d1:g} x {h:g} mm (DIN 6797 J)",
                 math.pi * (d2 ** 2 - d1 ** 2) / 4 * h * 7.85e-6 * 0.8, material="steel", cost_usd=0.05,
                 ratings={"approximate": True, "screw": size, "locking": "serrated"},
                 interfaces={"od": d2, "bore": d1, "thickness": h},
                 detail=body, model={"kind": "generated to standard", "source": "DIN 6797 J sizes (recalled), drawn as a plain ring; "
                                     "placeholder for the supplier's CAD", "tolerance": {"volume_ratio": (0.8, 1.25)}},
                 source=_source("iso_fasteners", "partial", f"DIN 6797 J {size}", unverified=("od", "bore", "thickness", "mass_kg"),
                                note="DIN 6797 sizes recalled from the standard's table, not fetched"))
