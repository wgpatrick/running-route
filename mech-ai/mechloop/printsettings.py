"""How a printed (FDM) part is printed, and what that does to its mass, stiffness and strength.

A printed part is not solid plastic: it is a shell of perimeters (walls) and top / bottom skins round a sparse infill.
Declare the settings per part, or once for the design:

    d.add("bracket", shape, material="petg", meta={"print": {"walls": 4, "infill": 0.4, "orientation": "+Z"}})
    d.manufacturing["print_settings"] = {"walls": 4, "top_layers": 5, "bottom_layers": 4, "infill": 0.4}

Keys (DEFAULT_PRINT_SETTINGS gives the value taken when neither the part nor the design says): line_width_mm,
layer_height_mm, walls (perimeters), top_layers, bottom_layers, infill (fraction 0..1), infill_pattern, orientation
(the build direction in the part's own frame, "+Z" etc.; the same thing as meta["print_up"], which wins if both are
given). The material is the part's own `material`.

What is computed from them (all labelled in the reports):
- MASS (Component.mass, so every verifier that uses mass): the shell is estimated as each face's area times the
  thickness the slicer lays against it (walls x line width on a side face or a hole, top / bottom layers x layer height
  on a face square to the build direction), capped at the part's volume; the rest is core, filled to the infill
  fraction. Edges are counted twice (a thin part comes out solid, which it is). Mass centre and inertia are still
  those of the solid shape.
- STIFFNESS, two bounds: upper = the materials table's solid modulus (what the bonded FEA uses); lower = the printed
  modulus from the maker's data sheet x ACROSS_LAYER_MODULUS (0.66, the weakest direction measured for printed PETG in
  practice_refs/14_PETG_creep_UTS_research.pdf) x (shell fraction + core fraction x infill^2: a sparse lattice in
  bending, Gibson-Ashby). The FEA's lower-bound solves use it.
- STRENGTH: along the layers the data sheet's printed tensile yield; across the layers (tension or shear on the layer
  plane) the across-layer figure below. FEA stresses are smeared over the part's whole section, so the material's own
  stress is taken as stress / (shell fraction + core fraction x infill) for the lower-bound factor of safety.

Material figures (PRINTED). PETG: Prusament PETG TDS (practice_refs/14_Prusament_PETG_TDS.pdf): printed tensile yield
47 MPa (horizontal), tensile modulus 1.5 GPa, interlayer adhesion 18 +/- 4 MPa -> across the layers 14 MPa (mean less
one deviation). ABS: Stratasys ABS-M30 TDS (14_Stratasys_ABSM30_TDS.pdf): XZ yield 30.8 MPa, modulus 2.30 GPa (ZX); its
ZX (across layers) 27.5 MPa is a heated-chamber Fortus figure, which an open desktop print does not reach, so across
the layers is DERIVED as PETG's ratio 14 / 47 times 30.8 = 9.2 MPa. PLA and PA12: no data sheet in the references;
ASSUMED from the materials table with the same ratios.
"""
from __future__ import annotations

import math

import numpy as np

DEFAULT_PRINT_SETTINGS = {"line_width_mm": 0.45, "layer_height_mm": 0.2, "walls": 3, "top_layers": 5, "bottom_layers": 4,
                          "infill": 0.25, "infill_pattern": "gyroid", "orientation": None}
DEFAULT_NOTE = ("a 0.4 mm nozzle's usual functional profile: 0.45 mm lines, 0.2 mm layers, 3 walls, 5 top / 4 bottom "
                "layers, 25 % gyroid (ASSUMED; declare meta['print'] or design.manufacturing['print_settings'])")
KEYS = set(DEFAULT_PRINT_SETTINGS)
ACROSS_LAYER_MODULUS = 0.66
_PETG_ACROSS_RATIO = 14.0 / 47.0
PRINTED = {
    "petg": {"tensile_yield_mpa": 47.0, "across_layers_mpa": 14.0, "modulus_mpa": 1500.0,
             "source": "Prusament PETG TDS: yield 47 MPa printed horizontal, modulus 1.5 GPa, interlayer adhesion 18 +/- 4 MPa"},
    "abs": {"tensile_yield_mpa": 30.8, "across_layers_mpa": round(_PETG_ACROSS_RATIO * 30.8, 1), "modulus_mpa": 2300.0,
            "source": "Stratasys ABS-M30 TDS: XZ yield 30.8 MPa, ZX modulus 2.30 GPa; across layers DERIVED (PETG's 14/47 ratio)"},
    "pla": {"tensile_yield_mpa": 50.0, "across_layers_mpa": round(_PETG_ACROSS_RATIO * 50.0, 1), "modulus_mpa": 3500.0,
            "source": "ASSUMED: materials table (no data sheet in the references), PETG's across-layer ratio"},
    "nylon_pa12": {"tensile_yield_mpa": 45.0, "across_layers_mpa": round(_PETG_ACROSS_RATIO * 45.0, 1), "modulus_mpa": 1700.0,
                   "source": "ASSUMED: materials table (no data sheet in the references), PETG's across-layer ratio"},
}


def is_printed(c) -> bool:
    if c.cots or c.mass_kg is not None:
        return False
    from .tolerance.process import process_of

    try:
        return process_of(c) == "printed"
    except Exception:
        return False


def _design_settings(c) -> dict:
    ref = getattr(c, "_design_ref", None)
    d = ref() if ref is not None else None
    return dict(((getattr(d, "manufacturing", None) or {}).get("print_settings")) or {}) if d is not None else {}


def settings_for(c) -> tuple[dict, str]:
    """(settings, where they came from: 'part', 'design', 'part+design' or 'default')."""
    own = dict(c.meta.get("print") or {})
    des = _design_settings(c)
    bad = (set(own) | set(des)) - KEYS - {"material", "inserts"}
    if bad:
        raise ValueError(f"{c.name}: unknown print setting(s) {sorted(bad)}; use {sorted(KEYS)}")
    s = dict(DEFAULT_PRINT_SETTINGS)
    s.update(des)
    s.update(own)
    if c.meta.get("print_up"):
        s["orientation"] = c.meta["print_up"]
    src = "part+design" if own and des else "part" if own else "design" if des else "default"
    if src == "design" and c.meta.get("print_up"):
        src = "design"
    s["infill"] = min(max(float(s["infill"]), 0.0), 1.0)
    return s, src


def build_direction(c, s: dict | None = None):
    """(unit vector of the build direction in world coordinates or None when not declared, frame)."""
    from .verifiers.dfm_geom import axis_names, part_frame

    s = s or settings_for(c)[0]
    frame = part_frame(c.shape)
    o = s.get("orientation")
    if not o:
        return None, frame
    axes = axis_names(frame)
    if o not in axes:
        raise ValueError(f"{c.name}: print orientation {o!r}; use one of {sorted(axes)}")
    return np.asarray(axes[o], dtype=float), frame


def _key(c, s):
    return (id(c.shape), tuple(sorted((k, str(v)) for k, v in s.items())))


def fractions(c) -> dict:
    """Volume fractions of shell and core and the solid fraction (mass over solid mass). Cached on the component."""
    s, src = settings_for(c)
    k = _key(c, s)
    cache = getattr(c, "_ps_cache", None)
    if cache and cache[0] == k and cache[2] is c.shape:
        return cache[1]
    up, frame = build_direction(c, s)
    upv = up if up is not None else frame[2]
    V = float(c.shape.volume)
    t_wall = float(s["walls"]) * float(s["line_width_mm"])
    t_top, t_bot = float(s["top_layers"]) * float(s["layer_height_mm"]), float(s["bottom_layers"]) * float(s["layer_height_mm"])
    shell = 0.0
    for f in c.shape.faces():
        try:
            n = f.normal_at(f.center())
            nz = float(np.dot([n.X, n.Y, n.Z], upv))
        except Exception:
            nz = 0.0
        shell += f.area * (t_wall if abs(nz) < 0.5 else (t_top if nz > 0 else t_bot))
    shell = min(shell, V) if V > 0 else 0.0
    f_shell = shell / V if V > 0 else 1.0
    f_core = 1.0 - f_shell
    rho = float(s["infill"])
    out = {"settings": s, "settings_from": src, "f_shell": round(f_shell, 4), "f_core": round(f_core, 4),
           "solid_fraction": round(f_shell + f_core * rho, 4),
           "structural_fraction_lower": round(f_shell + f_core * rho ** 2, 4),
           "orientation_declared": up is not None, "wall_mm": round(t_wall, 3), "top_mm": round(t_top, 3), "bottom_mm": round(t_bot, 3)}
    object.__setattr__(c, "_ps_cache", (k, out, c.shape))
    return out


def solid_fraction(c) -> float:
    return fractions(c)["solid_fraction"] if is_printed(c) else 1.0


def material_figures(material: str) -> dict:
    from .model import MATERIALS

    if material in PRINTED:
        return PRINTED[material]
    m = MATERIALS[material]
    return {"tensile_yield_mpa": m.yield_mpa, "across_layers_mpa": round(_PETG_ACROSS_RATIO * m.yield_mpa, 1), "modulus_mpa": m.E,
            "source": "ASSUMED: materials table, PETG's across-layer ratio"}


def modulus_bounds(c) -> dict:
    """{'upper': table modulus, 'lower': printed lower bound, 'basis': ...} for a printed part; equal for any other part."""
    from .model import MATERIALS

    E = MATERIALS[c.material].E
    if not is_printed(c):
        return {"upper": E, "lower": E, "basis": "solid"}
    fr = fractions(c)
    mf = material_figures(c.material)
    lo = mf["modulus_mpa"] * ACROSS_LAYER_MODULUS * fr["structural_fraction_lower"]
    return {"upper": E, "lower": round(min(lo, E), 1),
            "basis": (f"lower: printed modulus {mf['modulus_mpa']:g} MPa ({mf['source']}) x {ACROSS_LAYER_MODULUS} across layers x "
                      f"(shell {fr['f_shell']:.2f} + core {fr['f_core']:.2f} x infill {fr['settings']['infill']:g}^2); upper: solid {E:g} MPa")}


def lower_bound_fos(c, S6: np.ndarray, vm: np.ndarray, mask=None) -> dict:
    """Factor of safety of a printed part on the lower bound, from element stresses (n x 6: sxx syy szz sxy sxz syz at
    each element's peak point) and von Mises (n). Along the layers: von Mises against the printed yield. Across them:
    the normal stress on the layer plane (tension only) and the shear on it against the across-layer strength. Both are
    material stresses: smeared stress / (shell + core x infill). With the orientation undeclared every one of the
    part's three axes is tried as the build direction and the worst is taken."""
    fr = fractions(c)
    mf = material_figures(c.material)
    phi = max(fr["solid_fraction"], 1e-3)
    S6 = np.asarray(S6, dtype=float)
    vm = np.asarray(vm, dtype=float)
    if mask is not None:
        S6, vm = S6[mask], vm[mask]
    if not len(vm):
        return {}
    up, frame = build_direction(c, fr["settings"])
    cands = [up] if up is not None else [frame[0], frame[1], frame[2]]
    sx, sy, sz, sxy, sxz, syz = (S6[:, i] for i in range(6))
    u_vm = float(vm.max()) / phi / mf["tensile_yield_mpa"]
    worst = (0.0, None, 0.0, 0.0)
    for n in cands:
        n = np.asarray(n, dtype=float)
        t = np.stack([sx * n[0] + sxy * n[1] + sxz * n[2], sxy * n[0] + sy * n[1] + syz * n[2], sxz * n[0] + syz * n[1] + sz * n[2]], axis=1)
        sn = t @ n
        tau = np.sqrt(np.maximum((t * t).sum(axis=1) - sn * sn, 0.0))
        u = np.maximum(np.maximum(sn, 0.0), tau) / phi / mf["across_layers_mpa"]
        i = int(u.argmax())
        if u[i] >= worst[0]:
            worst = (float(u[i]), n, float(max(sn[i], 0.0)), float(tau[i]))
    u = max(u_vm, worst[0])
    return {"fos_lower": round(1.0 / u, 2) if u > 0 else 9999.0, "governed_by": "across the layers" if worst[0] > u_vm else "along the layers",
            "fos_along_layers": round(1.0 / u_vm, 2) if u_vm > 0 else 9999.0,
            "fos_across_layers": round(1.0 / worst[0], 2) if worst[0] > 0 else 9999.0,
            "layer_normal": None if worst[1] is None else [round(float(x), 3) for x in worst[1]],
            "orientation": fr["settings"].get("orientation") or "not declared: the worst of the part's three axes",
            "material_stress_factor": round(1.0 / phi, 3), "printed_yield_mpa": mf["tensile_yield_mpa"],
            "across_layers_mpa": mf["across_layers_mpa"], "strength_source": mf["source"],
            "settings_from": fr["settings_from"]}


# Heat-set inserts: the least wall the insert maker asks round the insert (ruthex RX series data sheet, column "W min",
# practice_refs/07_Ruthex_RX_insert_data.pdf), mm. The perimeters round the hole should carry it: an insert in walls
# thinner than that is anchored partly in sparse infill.
INSERT_WALL_MIN = {2.0: 1.3, 2.5: 1.6, 3.0: 1.6, 4.0: 2.1, 5.0: 2.6, 6.0: 3.3, 8.0: 4.5}


def infill_bearing_factor(c, screw_axis) -> tuple[float, str]:
    """Share of the plastic's bearing allowable that sparse infill under a skin carries: along the build direction the
    infill's walls stand under the load like a honeycomb loaded along its cells (~ infill fraction); square to it they
    bend (~ infill^1.5). DERIVED from Gibson-Ashby's honeycomb scaling, not from a test."""
    fr = fractions(c)
    rho = fr["settings"]["infill"]
    up, frame = build_direction(c, fr["settings"])
    upv = up if up is not None else frame[2]
    along = abs(float(np.dot(np.asarray(screw_axis, dtype=float), upv))) > 0.7
    if along:
        return rho, "infill walls loaded along their height (~ infill fraction)"
    return rho ** 1.5, "infill walls loaded across (~ infill^1.5)"


def mass_note(c) -> str:
    fr = fractions(c)
    return f"{fr['solid_fraction']:.2f} of solid ({fr['settings_from']} print settings)"


def circle_area(r):
    return math.pi * r * r
