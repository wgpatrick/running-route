"""Inspection plan for a fabricated part: what to measure when it arrives, in what order, against what, and how.

For one part (sheet first: flat and bent; machined and printed with the process-class figures) the plan lists the
dimensions that matter, ranked by what depends on them:

- hole-to-hole pitch inside a pattern that takes one mating part's screws (the fit of the assembly rests on it),
- holes near a bend that our checks expect to distort, bend angles, flange lengths and holes measured from a bend (the
  bend is the least accurate operation and the radius the shop forms at may differ from the model's),
- hole diameters that take a screw or a shaft, hole positions, overall size, flatness, plain holes, stock thickness.

Each dimension carries its nominal value (from the CAD), the tolerance (the assigned shop's published figure from
mechloop/data/supplier_rules where one exists, else the tolerance model's class value, always with its source), what our
checks predicted (a numeric prediction where a model gives one, e.g. a flange that comes out shorter because the shop
bends at its own radius; and the verbatim findings that speak about the feature: "hole near bend expected to distort"),
and the method with basic tools (calipers, square, feeler gauge, flatbed scanner).

Outputs: <out>/<part>.json (schema mechloop.inspection_plan/1) and <out>/<part>.svg (plan/front/side projections with a
numbered balloon per dimension). The projection helpers are the build package's (tools/build_package.py: _frame_for,
_to_local, _edges_2d), loaded from there so the inspection drawings use the same frame as the fabrication drawings.

    .venv/bin/python -m mechloop.inspect.plan --stage0 [--out inspect_form/plans]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import re
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "mechloop.inspection_plan/1"
MAX_DIMS = 40          # dimensions listed per part (the scanner measures every hole of a flat part regardless)

# ------------------------------------------------------------------------------------------- drawing helpers (reuse)
_BP = None


def _bp():
    """tools/build_package.py loaded as a module (its projection helpers), or None if it cannot be loaded."""
    global _BP
    if _BP is None:
        try:
            spec = importlib.util.spec_from_file_location("_mechloop_build_package", ROOT / "tools" / "build_package.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _BP = mod
        except Exception:      # the plan must not depend on the build tooling being importable
            _BP = False
    return _BP or None


def _frame_for(c, proc):
    bp = _bp()
    if bp is not None and hasattr(bp, "_frame_for"):
        return bp._frame_for(c, proc)
    from ..verifiers import dfm_geom as G

    fr = G.part_frame(c.shape)
    verts = np.array([[v.X, v.Y, v.Z] for v in c.shape.vertices()])
    ext = np.array([np.ptp(verts @ fr[i]) for i in range(3)])
    k = int(np.argmin(ext)) if proc == "sheet" else 2
    others = [i for i in range(3) if i != k]
    xi, yi = (others if ext[others[0]] >= ext[others[1]] else others[::-1])
    X, Z = fr[xi], fr[k]
    return np.array([X, np.cross(Z, X), Z])


def _to_local(shape, R):
    bp = _bp()
    if bp is not None and hasattr(bp, "_to_local"):
        return bp._to_local(shape, R)
    from build123d import Plane, Pos, Vector

    pl = Plane(origin=(0, 0, 0), x_dir=Vector(*R[0]), z_dir=Vector(*R[2]))
    loc = pl.to_local_coords(shape)
    bb = loc.bounding_box()
    off = np.array([bb.min.X, bb.min.Y, bb.min.Z])
    return Pos(*(-off)) * loc, off, np.array([bb.max.X, bb.max.Y, bb.max.Z]) - off


def _edges_2d(shape, origin, up):
    bp = _bp()
    if bp is not None and hasattr(bp, "_edges_2d"):
        return bp._edges_2d(shape, origin, up)
    from build123d import GeomType

    vis, hid = shape.project_to_viewport(origin, viewport_up=up, look_at=(0, 0, 0))

    def poly(e):
        n = 2 if e.geom_type == GeomType.LINE else 73
        return np.array([[p.X, p.Y] for p in (e.position_at(float(t)) for t in np.linspace(0, 1, n))])
    return [poly(e) for e in vis], [poly(e) for e in hid]


# ---------------------------------------------------------------------------------------------- tolerances
def _cnc3dp_rules() -> list[dict]:
    out = []
    for f in sorted((ROOT / "mechloop" / "data" / "supplier_rules_cnc_3dp").glob("*.json")):
        if f.name.startswith("_"):
            continue
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        for r in d.get("rules", []) if isinstance(d, dict) else []:
            r = dict(r)
            r.setdefault("supplier", f.stem)
            out.append(r)
    return out


def tolerances(shop: str, material: str, t: float | None, process: str) -> dict:
    """The +/- figures a plan uses, each with its source: {"cut", "hole", "bend_edge", "bend_angle_deg", "flat", "general"}.
    The shop's published value where mechloop/data/supplier_rules (or supplier_rules_cnc_3dp) has one; otherwise the
    tolerance model's class value (mechloop/tolerance/process.py, bends.py) at two standard deviations, their convention."""
    from ..shops import supplier_rules as SR
    from ..tolerance.bends import BEND_TOLERANCE
    from ..tolerance.process import PROCESS

    proc = process if process in PROCESS else "machined"
    cls = PROCESS[proc]
    sname = SR.name_of(shop) if shop else "?"

    def rule_entry(r, pm, unit="mm"):
        return {"pm": round(float(pm), 4), "unit": unit, "source": f"{sname} published ({r['id'] if 'id' in r else r.get('rule')})",
                "quote": r.get("quote"), "url": r.get("source_url"), "published": True}

    def cls_entry(pm, what, unit="mm"):
        return {"pm": round(float(pm), 4), "unit": unit, "published": False,
                "source": f"mechloop class value ({what}, 2 standard deviations); {sname} publishes none for this"}

    out = {}
    if proc == "sheet":
        cut = sorted(SR.applicable(shop, material, t, kinds={"tolerance_cut"}), key=lambda r: r.get("thickness_mm") is None)
        cut = [r for r in cut if isinstance(r.get("value_mm"), (int, float))]
        out["cut"] = rule_entry(cut[0], cut[0]["value_mm"]) if cut else cls_entry(2 * cls["pos"], "tolerance/process.py sheet pos")
        out["hole"] = dict(out["cut"]) if cut else cls_entry(2 * cls["hole_sd"], "tolerance/process.py sheet hole_sd")
        be = [r for r in SR.applicable(shop, material, t, kinds={"tolerance_bend"}) if isinstance(r.get("value_mm"), (int, float))]
        out["bend_edge"] = rule_entry(be[0], be[0]["value_mm"]) if be else cls_entry(2 * BEND_TOLERANCE["line_sd_mm"], "tolerance/bends.py line_sd_mm")
        ba = [r for r in SR.applicable(shop, material, t, kinds={"tolerance_bend_angle"}) if isinstance(r.get("value"), (int, float))]
        out["bend_angle_deg"] = rule_entry(ba[0], ba[0]["value"], "deg") if ba else cls_entry(2 * BEND_TOLERANCE["angle_sd_deg"], "tolerance/bends.py angle_sd_deg", "deg")
        out["flat"] = cls_entry(2 * cls["flat"], "tolerance/process.py sheet flat")
        out["general"] = dict(out["cut"])
    else:
        kind = "fdm" if proc == "printed" else "cnc_milling"
        rs = [r for r in _cnc3dp_rules() if r.get("supplier") == shop and r.get("rule") == "tolerance" and r.get("process") == kind]
        num = [r for r in rs if isinstance(r.get("value_mm"), (int, float))]
        if num:
            out["general"] = rule_entry(num[0], num[0]["value_mm"])
        elif proc == "printed":
            # Hubs / Protolabs: +/-0.5 % with a lower limit of +/-0.5 mm (docs/ROADMAP.md, Build 1 printed parts)
            q = next((r for r in _cnc3dp_rules() if r.get("supplier") == "hubs" and r.get("rule") == "tolerance" and r.get("process") == "fdm"), None)
            out["general"] = {"pm": 0.5, "unit": "mm", "published": True, "rule": "max(0.5 mm, 0.5 % of the dimension)",
                              "source": "Hubs published FDM tolerance", "quote": (q or {}).get("quote"), "url": (q or {}).get("source_url")}
        else:
            out["general"] = cls_entry(2 * cls["pos"], f"tolerance/process.py {proc} pos")
        out["cut"] = dict(out["general"])
        out["hole"] = dict(out["general"]) if num or proc == "printed" else cls_entry(2 * cls["hole_sd"], f"tolerance/process.py {proc} hole_sd")
        out["flat"] = cls_entry(2 * cls["flat"], f"tolerance/process.py {proc} flat")
    return out


def _tol_for(tols: dict, key: str, nominal: float | None = None) -> dict:
    t = dict(tols.get(key) or tols["general"])
    if t.get("rule", "").startswith("max(0.5 mm") and nominal is not None:
        t["pm"] = round(max(0.5, 0.005 * abs(nominal)), 4)
    return t


# ------------------------------------------------------------------------------------------- analysis
def _capture_checks(design, c):
    """Run the manufacture checks on one part (process rules, shop profile, the assigned supplier's rules) and capture the
    supplier-rule feature dict they measured. Returns (findings, metrics row, features or None)."""
    from ..report import VerifierResult
    from ..verifiers import dfm_supplier as DSUP
    from ..verifiers import manufacture as MAN

    r = VerifierResult("manufacture")
    got = {}
    orig = DSUP.features_of

    def cap(*a, **k):
        f = orig(*a, **k)
        got["feat"] = f
        return f
    DSUP.features_of = cap
    try:
        row = MAN.check_part(r, design, c)
    finally:
        DSUP.features_of = orig
    return r.findings, row, got.get("feat")


def _fmt(x, n=2):
    return f"{x:.{n}f}".rstrip("0").rstrip(".") if isinstance(x, (int, float)) else str(x)


def _screw_size(sku: str) -> tuple[str, float] | tuple[None, None]:
    m = re.search(r"M(\d+(?:\.\d+)?)", sku or "")
    return (f"M{m.group(1)}", float(m.group(1))) if m else (None, None)


def _is_hardware(design, name: str) -> bool:
    """Nuts, washers, spacers and other screws: not a mating part whose pattern the hole must match."""
    if re.search(r"(washer|_nut|nut_|spacer|screw|bolt)", name):
        return True
    try:
        oc = design.get(name)
    except Exception:
        return False
    return bool(oc.cots and (oc.sku or "").upper().startswith(("NUT", "WASH", "WSH", "SPACER", "SHCS", "BHCS", "FHCS", "PEM")))


def _interfaces(design, c, hole_world) -> list[dict]:
    """Fasteners and parts that pass through one hole: [{"kind", "name", "size", "d", "mates"}]."""
    if design is None:
        return []
    o, ax, d = hole_world["origin"], hole_world["axis"], hole_world["d"]
    out = []
    for f in getattr(design, "fasteners", []) or []:
        try:
            sc = design.get(f.name)
        except Exception:
            continue
        clamps = set(f.clamps or ()) | set((sc.meta or {}).get("threads_into") or [])
        fa = np.asarray(f.axis, float)
        fa = fa / (np.linalg.norm(fa) or 1.0)
        if abs(abs(fa @ ax) - 1.0) > 1e-3:
            continue
        rel = o - np.asarray(f.head_center, float)
        along = float(rel @ -fa)            # the shank runs from the head along -axis
        perp = float(np.linalg.norm(rel - (rel @ fa) * fa))
        if perp > 0.5 * d + 0.3:
            continue
        m_len = re.search(r"x(\d+(?:\.\d+)?)", sc.sku or "")
        length = float(m_len.group(1)) if m_len else 60.0
        if c.name not in clamps and not (-1.0 <= along <= length + 1.0):
            continue
        size, sd = _screw_size(sc.sku or f.name)
        threads = c.name in ((sc.meta or {}).get("threads_into") or [])
        out.append({"kind": "tapped" if threads else "fastener", "name": f.name, "sku": sc.sku, "size": size, "d": sd,
                    "mates": sorted(n for n in clamps if n != c.name and not _is_hardware(design, n))})
    # shafts, bearings and pins on the hole's axis (a part, not a fastener, whose own axis runs through the hole)
    fasteners = {f.name for f in getattr(design, "fasteners", []) or []}
    for oc in design.components:
        if oc.name == c.name or oc.name in fasteners or not oc.cots:
            continue
        sku = oc.sku or ""
        if not sku.startswith(("BRG", "SHAFT", "ROD", "PIN", "DOWEL", "T8")):
            continue
        bb = oc.shape.bounding_box()
        cen = np.array([bb.center().X, bb.center().Y, bb.center().Z])
        rel = cen - o
        perp = float(np.linalg.norm(rel - (rel @ ax) * ax))
        if perp < 0.25 * d + 0.3 and abs(rel @ ax) < max(bb.size.X, bb.size.Y, bb.size.Z):
            out.append({"kind": "shaft_or_bearing", "name": oc.name, "sku": sku, "size": None, "d": None, "mates": [oc.name]})
    return out


def _on_hole(hr, q, t) -> bool:
    """A point (a cut-out's centre on one face) on this hole's axis, within the sheet thickness of its middle."""
    o, ax = hr["world"]["origin"], hr["world"]["axis"]
    rel = np.asarray(q, float) - o
    along = float(rel @ ax)
    return float(np.linalg.norm(rel - along * ax)) <= 0.6 and abs(along) <= float(t or 0) + 1.0


def _near(p, q, tol):
    return p is not None and q is not None and float(np.linalg.norm(np.asarray(p, float) - np.asarray(q, float))) <= tol


def _finding_points(f) -> list:
    at = f.data.get("at")
    if at is None:
        return []
    arr = np.asarray(at, dtype=float) if not isinstance(at, dict) else None
    if arr is None or arr.size == 0:
        return []
    return [arr] if arr.ndim == 1 else list(arr)


def _quote(f) -> dict:
    return {"code": f.code, "severity": f.severity, "rule": f.data.get("rule"), "finding": f.message}


def analyse(design, c) -> dict:
    """Everything a plan needs from one part: drawing frame, local geometry, holes (with interfaces), bends, findings."""
    from ..shops import supplier_rules as SR
    from ..tolerance.process import process_of
    from ..verifiers import dfm_geom as G
    from ..verifiers import dfm_sheet as DS

    proc = process_of(c)
    R = _frame_for(c, proc)
    local, off, size = _to_local(c.shape, R)

    def w2l(p):
        return R @ np.asarray(p, float) - off

    findings, row, feat = _capture_checks(design, c)
    sm = G.sample_surface(c.shape, n=400)
    cyls = G.cylinders(c.shape)
    holes = G.holes(c.shape, sm, cyls)
    form = row.get("form") or (feat or {}).get("form") or ("flat" if proc == "sheet" else proc)
    t = row.get("thickness_mm") or (feat or {}).get("thickness_mm")
    shop = SR.shop_for(c, design, proc) if proc in ("sheet", "machined") else ((c.meta.get("dfm") or {}).get("shop") or "hubs")
    hole_rows = []
    for h in holes:
        hw = {"origin": np.asarray(h.origin, float), "axis": np.asarray(h.axis, float), "d": float(h.diameter)}
        hole_rows.append({"world": hw, "center": w2l(h.origin), "axis": R @ np.asarray(h.axis, float), "d": float(h.diameter),
                          "through": bool(h.through), "depth": float(h.depth), "round": True,
                          "interfaces": _interfaces(design, c, hw)})
    # non-round cut-outs and slots the supplier-rule features found (sheet): listed too, with their width
    for ring in (feat or {}).get("holes", []):
        if ring.get("round"):
            continue
        at = np.asarray(ring["at"], float)
        hole_rows.append({"world": {"origin": at, "axis": R[2], "d": float(ring["d"])}, "center": w2l(at), "axis": np.array([0, 0, 1.0]),
                          "d": float(ring["d"]), "through": True, "depth": float(t or 0), "round": False, "slot": bool(ring.get("slot")),
                          "interfaces": []})
    # webs to the edge and to the next feature, from the supplier-rule features (sheet)
    for ring in (feat or {}).get("holes", []):
        for hr in hole_rows:
            if _on_hole(hr, ring["at"], t) and abs(hr["d"] - float(ring["d"])) < 0.3:
                hr["edge_web"], hr["web"] = ring.get("edge_web"), ring.get("web")
    bends = []
    if form == "bent":
        bent = DS.bent_sheet(c.shape, sm, cyls)
        geo = (bent or {}).get("bends") or []
        for i, b in enumerate((feat or {}).get("bends", [])):
            g = geo[i] if i < len(geo) else None
            bends.append({"radius": float(b["radius"]), "angle": float(b["angle"]), "length": float(b["length"]), "at": w2l(b["at"]),
                          "at_world": np.asarray(b["at"], float),
                          "axis": None if g is None else R @ np.asarray(g["axis"], float),
                          "origin": None if g is None else w2l(g["origin"]),
                          "flanges": [{"length": float(f["length"]), "reach": float(f["reach"]), "at": w2l(f["at"]), "at_world": np.asarray(f["at"], float)}
                                      for f in b["flanges"]]})
        for hb in (feat or {}).get("hole_bend", []):
            for hr in hole_rows:
                if _on_hole(hr, hb["at"], t):
                    hr.setdefault("to_bend", []).append({"d_tan": float(hb["d_tan"]), "r": float(hb["r"]), "angle": float(hb["angle"])})
    return {"c": c, "proc": proc, "form": form, "t": t, "shop": shop, "R": R, "off": off, "size": size, "local": local, "w2l": w2l,
            "findings": [f for f in findings if f.severity in ("error", "warning")], "row": row, "feat": feat, "holes": hole_rows, "bends": bends}


# ------------------------------------------------------------------------------------------- dimensions
def _method(kind: str, a: dict, d: float | None = None) -> dict:
    flat = a["form"] == "flat" and a["proc"] == "sheet"
    scan_ok = a["proc"] == "sheet" and (flat or kind in ("hole_diameter", "hole_pitch", "hole_position"))
    M = {
        "hole_pitch": ("scanner" if scan_ok else "calipers",
                       "Scanner: centre-to-centre from the fitted circles (scan.py)." if scan_ok else
                       "Calipers: outside-to-outside of the two holes with the inside jaws reversed, or inside jaws edge-to-edge; "
                       "pitch = edge-to-edge + (d1 + d2) / 2."),
        "hole_position": ("scanner" if scan_ok else "calipers",
                          "Scanner: hole centre against the registered outline (scan.py)." if scan_ok else
                          "Calipers depth bar or step: datum edge to the near edge of the hole, plus half the measured diameter."),
        "hole_diameter": ("calipers" if (d or 0) >= 2.5 else "pin_gauge",
                          "Calipers inside jaws, two readings 90 degrees apart (record the mean; note ovality)." if (d or 0) >= 2.5 else
                          "Too small for caliper jaws: largest drill shank or pin gauge that passes (record its size)."),
        "hole_ovality": ("calipers", "Calipers inside jaws: across the bend (perpendicular to the bend line) and along it; record both."),
        "hole_to_bend": ("calipers", "Calipers step (or depth bar) on the outside face of the other flange; jaw tip to the near edge "
                                     "of the hole; add half the hole diameter."),
        "bend_angle": ("square_feeler", "Engineer's square on the outside faces of the two flanges; feeler gauge at the open end; "
                                        "angle error = atan(gap / flange length). Record the angle (90 + error) and which way it opened."),
        "bend_radius": ("radius_gauge", "Radius gauge set on the inside of the bend; or stand the part on its end on the scanner glass and "
                                        "scan the bend's end profile (fit the inside arc)."),
        "flange_length": ("calipers", "Calipers outside jaws: outside face of the bend (the other flange's outside face) to the flange's free edge, "
                                      "near each end of the bend; record the mean."),
        "web_width": ("calipers", "Calipers outside jaws across the outside faces of the two flanges, near each end; record the mean."),
        "overall": ("scanner" if flat else "calipers", "Scanner: extent of the registered outline." if flat else "Calipers outside jaws across the part."),
        "edge_web": ("scanner" if flat else "calipers", "Scanner: hole edge to part edge from the registered outline." if flat else
                     "Calipers depth bar: part edge to the hole edge."),
        "slot_width": ("scanner" if flat else "calipers", "Scanner: slot width from the outline; or a feeler gauge stack that just enters."),
        "flatness": ("feeler", "Lay the part on the scanner glass (or a known-flat surface), press lightly at each corner in turn and slide "
                               "feeler leaves under the opposite corner; record the largest leaf that enters."),
        "thickness": ("calipers", "Calipers outside jaws (micrometer if available) at three places away from holes and bends; record the mean."),
    }
    m, how = M[kind]
    return {"instrument": m, "how": how, "alternates": ["calipers"] if m == "scanner" else []}


def _predict_flange_shift(a: dict, b: dict) -> dict | None:
    """Shift (mm) of the outside dimension of a flange (bend outside to a point on the flange) when the shop forms the bend at
    its own radius from a flat pattern developed at ours: the flat position is kept from the bend centre, so the straight part
    gains half the difference in bend allowance and the outside setback changes with the radius."""
    from ..shops import supplier_rules as SR

    t = float(a["t"] or 0)
    rs = SR._shop_radius(a["shop"], a["c"].material, t)
    k = SR._k_factor(a["shop"], a["c"].material, t)
    rm, ang = b["radius"], b["angle"]
    if rs is None or abs(rs - rm) <= 0.15 or not (0 < ang < 179):
        return None
    k_basis = "supplier K-factor" if k is not None else "K = 0.44 (no K-factor published)"
    k = 0.44 if k is None else k
    A = math.radians(ang)
    ba = lambda r: (r + k * t) * A
    sb = lambda r: (r + t) * math.tan(A / 2)
    delta = 0.5 * (ba(rm) - ba(rs)) + (sb(rs) - sb(rm))
    return {"delta": round(delta, 3), "shop_radius": rs, "model_radius": rm, "k": k,
            "basis": f"the shop bends at its own {rs:g} mm inside radius (model {rm:g} mm) from a flat pattern developed at the model's radius "
                     f"({k_basis} {k:g}); each flange's outside dimension moves by {delta:+.2f} mm per bend"}


def _related_findings(a: dict, point_world, reach: float, codes=None) -> list[dict]:
    out = []
    for f in a["findings"]:
        if codes and f.code not in codes:
            continue
        if any(_near(p, point_world, reach) for p in _finding_points(f)):
            out.append(_quote(f))
    return out


def build_dims(a: dict) -> list[dict]:
    tols = tolerances(a["shop"], a["c"].material, a["t"], a["proc"])
    a["tols"] = tols
    dims: list[dict] = []
    t = float(a["t"] or 0)

    def add(kind, key, label, nominal, tol, score, at, view, predicted=None, depends=(), unit="mm", **extra):
        pred = {"value": nominal, "basis": "as modelled (no model predicts a departure)", "findings": []}
        if predicted:
            pred.update(predicted)
        if isinstance(pred.get("value"), float):
            pred["value"] = round(pred["value"], 4)
        dims.append({"key": key, "kind": kind, "label": label, "nominal": None if nominal is None else round(float(nominal), 4), "unit": unit,
                     "tol": tol, "predicted": pred, "method": _method(kind, a, extra.pop("d", None)), "depends": list(depends),
                     "score": round(float(score), 1), "at": [round(float(x), 3) for x in at], "view": view, **extra})

    # ---- holes: name them by position (plan view rows), round ones first
    H = sorted(a["holes"], key=lambda h: (not h["round"], round(-h["center"][1], 0), round(h["center"][0], 1)))
    for i, h in enumerate(H):
        h["id"] = f"H{i + 1}" if h["round"] else f"C{i + 1}"
    hole_view = lambda h: "plan" if abs(h["axis"][2]) > 0.9 else ("front" if abs(h["axis"][1]) > 0.9 else "side")
    # patterns: holes that take the screws of one mating part
    groups: dict[tuple, list] = {}
    for h in H:
        for itf in h["interfaces"]:
            for m in itf["mates"] or [itf["name"]]:
                groups.setdefault((m,), []).append(h)
    for (mate,), hs in sorted(groups.items()):
        hs = sorted({id(x): x for x in hs}.values(), key=lambda x: x["id"])
        if len(hs) < 2:
            continue
        # adjacent pairs along the pattern (a chain covers the pattern without listing every pair)
        for h0, h1 in zip(hs[:-1], hs[1:]):
            if abs(h0["axis"] @ h1["axis"]) < 0.999:
                continue
            p = float(np.linalg.norm(h0["center"] - h1["center"]))
            add("hole_pitch", f"{h0['id']}-{h1['id']}.pitch", f"Pitch {h0['id']} to {h1['id']} (pattern for {mate})", p,
                _tol_for(tols, "cut"), 90, 0.5 * (h0["center"] + h1["center"]), hole_view(h0),
                depends=[f"screws of {mate} pass through both holes: the pattern must match {mate}'s"], features=[h0["id"], h1["id"]])
    for h in H:
        view = hole_view(h)
        itf = h["interfaces"]
        depends = [f"{x['name']} ({x['sku'] or x['kind']})" + (f" clamps {', '.join(x['mates'])}" if x["mates"] else "") for x in itf]
        rel = _related_findings(a, h["world"]["origin"], 0.5 * h["d"] + 1.0)
        near_bend = [f for f in rel if f["code"] in ("hole_too_close_to_bend",) or "bend" in (f.get("rule") or "")]
        if not h["round"]:
            kind = "slot_width"
            add(kind, f"{h['id']}.width", f"{'Slot' if h.get('slot') else 'Cut-out'} {h['id']} width", h["d"], _tol_for(tols, "cut"),
                70 if rel else 25, h["center"], view, predicted={"findings": rel}, features=[h["id"]], d=h["d"])
            continue
        fit = None
        if itf and itf[0].get("d"):
            sd = itf[0]["d"]
            if itf[0]["kind"] == "tapped":
                fit = f"tap drill for {itf[0]['size']} (thread cut by the shop or an insert)"
            else:
                fit = f"clearance for {itf[0]['size']}: {h['d'] - sd:.2f} mm over the screw; the screw passes while the hole is above {sd + 0.05:.2f} mm"
        score = 30 + (40 if itf else 0) + (15 if rel else 0)
        if near_bend:
            score = max(score, 85)
            for along, ang_txt in (("across", "across the bend"), ("along", "along the bend")):
                add("hole_ovality", f"{h['id']}.dia_{along}", f"Hole {h['id']} diameter {ang_txt}", h["d"], _tol_for(tols, "hole"), score + (1 if along == "across" else 0),
                    h["center"], view, depends=depends, features=[h["id"]],
                    predicted={"findings": rel, "expect_out_of_tolerance": along == "across",
                               "basis": "our check expects the hole to stretch into an oval when the bend is formed (no numeric model: the "
                                        "measurement sets one)" if along == "across" else "along the bend the hole is expected to keep its size"},
                    fit=fit)
        else:
            add("hole_diameter", f"{h['id']}.dia", f"Hole {h['id']} diameter" + (f" ({itf[0]['size']} {itf[0]['kind']})" if itf and itf[0].get("size") else ""),
                h["d"], _tol_for(tols, "hole"), score, h["center"], view, depends=depends, features=[h["id"]],
                predicted={"findings": rel, **({"value": h["d"] + (-0.15 if a["proc"] == "printed" else 0.0),
                                                "basis": "printed holes come out small (tolerance/process.py hole_bias -0.15 mm)"} if a["proc"] == "printed" else {})},
                fit=fit, d=h["d"])
        # distance to a bend (bent parts): the interface position relative to the least accurate operation
        for tb in h.get("to_bend", [])[:1]:
            b = min(a["bends"], key=lambda b: abs(b["radius"] - tb["r"]) + abs(b["angle"] - tb["angle"])) if a["bends"] else None
            sb = (tb["r"] + t) * math.tan(math.radians(min(tb["angle"], 179.0)) / 2)
            nom = tb["d_tan"] + 0.5 * h["d"] + sb
            shift = _predict_flange_shift(a, b) if b else None
            pred = {"findings": near_bend}
            if shift:
                pred.update({"value": round(nom + shift["delta"], 3), "basis": shift["basis"]})
            tol = _tol_for(tols, "bend_edge")
            tol = {**tol, "pm": round(tol["pm"] + _tol_for(tols, "cut")["pm"], 4), "source": tol["source"] + " + the cut tolerance (hole to edge)"}
            add("hole_to_bend", f"{h['id']}.to_bend", f"Hole {h['id']} centre to the outside of the nearest bend", nom, tol,
                75 + (10 if itf else 0) + (5 if near_bend else 0), h["center"], view, predicted=pred, depends=depends, features=[h["id"]])
        if a["form"] == "flat" or not h.get("to_bend"):
            sc = 60 if itf else 35
            for ax_i, ax_n, datum in ((0, "x", "C (x = 0 edge)"), (1, "y", "B (y = 0 edge)")):
                if view == "plan":
                    add("hole_position", f"{h['id']}.{ax_n}", f"Hole {h['id']} centre {ax_n.upper()} from datum {datum}", h["center"][ax_i],
                        _tol_for(tols, "cut"), sc - ax_i * 0.5, h["center"], view, depends=depends, features=[h["id"]])
        ew = h.get("edge_web")
        if ew is not None and any("edge" in (f.get("rule") or "") for f in rel):
            add("edge_web", f"{h['id']}.edge_web", f"Material from hole {h['id']} to the part edge", ew, _tol_for(tols, "cut"), 72, h["center"], view,
                predicted={"findings": rel}, features=[h["id"]])
    # ---- bends
    for bi, b in enumerate(a["bends"]):
        bid = f"B{bi + 1}"
        b["id"] = bid
        bview = "plan"
        if b["axis"] is not None:
            k = int(np.argmax(np.abs(b["axis"])))
            bview = {0: "side", 1: "front", 2: "plan"}[k]
        bf = _related_findings(a, b["at_world"], b["radius"] + t + 2.0, codes={"bend_radius_differs", "supplier_rule"})
        rad_f = [f for f in a["findings"] if f.code == "bend_radius_differs" or (f.code == "supplier_rule" and "bend.radius" in (f.data.get("rule") or ""))]
        add("bend_angle", f"{bid}.angle", f"Bend {bid} angle", b["angle"], _tol_for(tols, "bend_angle_deg"), 80, b["at"], bview, unit="deg",
            features=[bid], depends=["every feature on the flange moves by (angle error) x (its distance from the bend)"])
        shift = _predict_flange_shift(a, b)
        add("bend_radius", f"{bid}.radius", f"Bend {bid} inside radius", b["radius"],
            {"pm": 0.15, "unit": "mm", "published": False, "source": "mechloop supplier_rules match tolerance (a radius within 0.15 mm is taken as the shop's)"},
            78 if rad_f else 40, b["at"], bview, features=[bid],
            predicted={"value": shift["shop_radius"] if shift else b["radius"], "findings": [_quote(f) for f in rad_f[:2]],
                       "basis": shift["basis"] if shift else "the shop's radius matches the model's"})
        others = [x for x in a["bends"] if x is not b and x["origin"] is not None and x["axis"] is not None]
        for fi, f in enumerate(b["flanges"]):
            # a flange that ends at another bend is a web: measured outside-to-outside across both bends
            web_of = None
            for o in others:
                rel = f["at"] - o["origin"]
                dist = float(np.linalg.norm(rel - (rel @ o["axis"]) * o["axis"]))
                if dist < o["radius"] + t + 0.6:
                    web_of = o
            ff = _related_findings(a, f["at_world"], 3.0, codes={"flange_too_short", "supplier_rule"})
            ff = [q for q in ff if "flange" in q["finding"]]
            if web_of is not None:
                if a["bends"].index(web_of) < bi:
                    continue        # listed once, from the first bend
                o = web_of
                sb_o = (o["radius"] + t) * math.tan(math.radians(min(o["angle"], 179.0)) / 2)
                nom = f["length"] + sb_o
                s1, s2 = _predict_flange_shift(a, b), _predict_flange_shift(a, o)
                pred = {"findings": ff}
                if s1 or s2:
                    pred.update({"value": round(nom + (s1["delta"] if s1 else 0) + (s2["delta"] if s2 else 0), 3), "basis": (s1 or s2)["basis"]})
                tol = _tol_for(tols, "bend_edge")
                tol = {**tol, "pm": round(2 * tol["pm"], 4), "source": tol["source"] + " x 2 (two bends)"}
                add("web_width", f"{bid}-{o.get('id', 'B?')}.web", f"Outside width across bends {bid} and the next", nom, tol, 70, f["at"], bview, predicted=pred, features=[bid])
            else:
                pred = {"findings": ff}
                if shift:
                    pred.update({"value": round(f["length"] + shift["delta"], 3), "basis": shift["basis"]})
                add("flange_length", f"{bid}.F{fi + 1}", f"Flange {fi + 1} of bend {bid}: outside of the bend to the free edge", f["length"],
                    _tol_for(tols, "bend_edge"), 72 + (10 if ff else 0), f["at"], bview, predicted=pred, features=[bid])
    # ---- overall, flatness, thickness
    W, Hh, D = (float(x) for x in a["size"])
    for i, (n, v) in enumerate((("X", W), ("Y", Hh)) + ((("Z", D),) if a["form"] != "flat" else ())):
        cen = 0.5 * a["size"]
        at = cen.copy()
        at[{"X": 1, "Y": 0, "Z": 1}[n]] = 0.0 if n != "Z" else at[1]
        tol = _tol_for(tols, "bend_edge" if a["form"] == "bent" else "cut", v)
        add("overall", f"overall.{n}", f"Overall size along {n}", v, tol, 50 - i, at, "plan" if n != "Z" else "front")
    if a["proc"] == "sheet" or a["form"] == "flat" or W * Hh > 4000:
        big = W * Hh > 20000
        add("flatness", "flatness", "Flatness (largest gap under a corner with the opposite corner pressed down)", 0.0, _tol_for(tols, "flat"),
            65 if big else 45, 0.5 * a["size"], "plan", depends=["mating face" if big else "general"])
    if a["t"]:
        add("thickness", "thickness", "Stock thickness", float(a["t"]), {"pm": 0.1, "unit": "mm", "published": False,
                                                                           "source": "typical stock thickness tolerance (not a shop figure: the shop does not cut it)"},
            20, np.array([W * 0.9, Hh * 0.5, 0.0]), "plan")
    dims.sort(key=lambda d: -d["score"])
    for i, d in enumerate(dims):
        d["id"] = i + 1
    return dims


# ------------------------------------------------------------------------------------------- drawing
def _view_defs(a):
    W, H, D = (float(x) for x in a["size"])
    views = {"plan": ((0, 0, 1000), (0, 1, 0), (0, 1), (W, H))}
    if a["form"] != "flat" or a["proc"] != "sheet":
        views["front"] = ((0, -1000, 0), (0, 0, 1), (0, 2), (W, D))
        views["side"] = ((1000, 0, 0), (0, 0, 1), (1, 2), (H, D))
    return views


def drawing_svg(a: dict, plan: dict) -> str:
    """Projections of the part with a numbered balloon per dimension. Strokes use currentColor (light/dark friendly)."""
    views = _view_defs(a)
    gap, margin, title_h = 18.0, 14.0, 26.0
    # layout: plan top-left, front below it, side to the right of the plan
    W, H, D = (float(x) for x in a["size"])
    pos = {"plan": (margin, title_h + margin)}
    if "front" in views:
        pos["front"] = (margin, title_h + margin + H + gap)
        pos["side"] = (margin + W + gap, title_h + margin)
    tot_w = margin * 2 + W + (gap + H if "side" in views else 0)
    tot_h = title_h + margin * 2 + H + (gap + D if "front" in views else 0)
    tot_w = max(tot_w, 120.0)
    k = 1.0
    sw = max(tot_w, tot_h) / 220.0          # stroke and text scale with the part
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {tot_w:.1f} {tot_h:.1f}" width="100%" class="mechloop-inspect" '
           f'data-part="{plan["part"]}" font-family="sans-serif">',
           "<style>.e{fill:none;stroke:currentColor;stroke-linecap:round}.h{fill:none;stroke:currentColor;opacity:.35}"
           ".b circle{fill:#d9480f;stroke:none}.b text{fill:#fff;font-weight:700;text-anchor:middle;dominant-baseline:central}"
           ".l{stroke:#d9480f;fill:none}.t{fill:currentColor}</style>",
           f'<text class="t" x="{margin:.1f}" y="{margin + 4:.1f}" font-size="{6 * sw:.2f}" font-weight="700">{plan["part"]}</text>',
           f'<text class="t" x="{margin:.1f}" y="{margin + 4 + 7 * sw:.1f}" font-size="{3.6 * sw:.2f}">{plan["material"]}, {_fmt(plan.get("thickness_mm"))} mm, '
           f'{plan["form"]}, {plan["shop_name"]} - numbered balloons = dimension ids (mm; view frame: X right, Y up in PLAN)</text>']
    to_svg = {}
    for name, (origin, up, axes, ext) in views.items():
        x0, y0 = pos[name]
        ex, ey = ext

        def tf(q, x0=x0, y0=y0, ey=ey):
            return x0 + k * q[:, 0], y0 + k * (ey - q[:, 1])
        to_svg[name] = (lambda p, axes=axes, tf=tf: tuple(float(v[0]) for v in tf(np.array([[p[axes[0]], p[axes[1]]]]))))
        try:
            vis, hid = _edges_2d(a["local"], origin, up)
        except Exception:
            vis, hid = [], []
        for cls_, polys in (("h", hid), ("e", vis)):
            for q in polys:
                if len(q) > 2:          # projected straight edges come back as 73-point curves: keep the shape, drop the points
                    from shapely.geometry import LineString
                    q = np.asarray(LineString(q).simplify(0.01).coords)
                xs, ys = tf(q)
                pts = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(xs, ys))
                out.append(f'<polyline class="{cls_}" stroke-width="{(0.25 if cls_ == "h" else 0.4) * sw:.3f}" points="{pts}"/>')
        out.append(f'<text class="t" x="{x0:.1f}" y="{y0 - 2 * sw:.1f}" font-size="{3.2 * sw:.2f}" opacity=".7">{name.upper()}</text>')
    # balloons
    placed = []
    r_b = 3.2 * sw
    for d in plan["dimensions"]:
        v = d["view"] if d["view"] in to_svg else "plan"
        px, py = to_svg[v](d["at"])
        ang = math.radians(40 + 47 * (d["id"] % 7))
        for _ in range(12):
            bx, by = px + (r_b * 2.6) * math.cos(ang), py - (r_b * 2.6) * math.sin(ang)
            if all(math.hypot(bx - qx, by - qy) > 2.1 * r_b for qx, qy in placed):
                break
            ang += math.radians(31)
        placed.append((bx, by))
        out.append(f'<line class="l" stroke-width="{0.3 * sw:.3f}" x1="{px:.2f}" y1="{py:.2f}" x2="{bx:.2f}" y2="{by:.2f}"/>')
        out.append(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{0.6 * sw:.2f}" fill="#d9480f"/>')
        out.append(f'<g class="b"><circle cx="{bx:.2f}" cy="{by:.2f}" r="{r_b:.2f}"/><text x="{bx:.2f}" y="{by:.2f}" font-size="{3.4 * sw:.2f}">{d["id"]}</text></g>')
    out.append("</svg>")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------- plan
def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_jsonable(v) for v in x.tolist()]
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    return x


def make_plan(design, c, *, part_id: str | None = None, revision: str | None = None, source: dict | None = None,
              dxf: str | None = None) -> tuple[dict, str]:
    """(plan dict, SVG text) for one component of a design."""
    from ..shops import supplier_rules as SR

    a = analyse(design, c)
    dims = build_dims(a)
    listed = dims[:MAX_DIMS]
    holes = [{"id": h["id"], "center": h["center"], "axis": h["axis"], "d": round(h["d"], 3), "round": h["round"], "through": h["through"],
              "interfaces": h["interfaces"], "edge_web": h.get("edge_web"), "to_bend": h.get("to_bend", [])} for h in a["holes"]]
    bends = [{"id": b.get("id"), "radius": b["radius"], "angle": b["angle"], "length": b["length"], "at": b["at"], "axis": b["axis"],
              "flanges": [{"length": f["length"], "reach": f["reach"], "at": f["at"]} for f in b["flanges"]]} for b in a["bends"]]
    preds = [{"code": f.code, "severity": f.severity, "rule": f.data.get("rule"), "finding": f.message} for f in a["findings"]]
    plan = {
        "schema": SCHEMA, "part": c.name, "part_id": part_id or c.name, "revision": revision, "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "process": a["proc"], "form": a["form"], "material": c.material, "thickness_mm": a["t"], "shop": a["shop"],
        "shop_name": SR.name_of(a["shop"]) if a["shop"] else None, "source": source or {}, "dxf": dxf,
        "frame": {"note": "drawing frame: origin at the part's bounding-box corner; Z = sheet normal (flat) or the smallest extent; X the longer "
                          "of the other two. Datum C = the x = 0 edge, B = the y = 0 edge, A = the z = 0 face.",
                  "R_world_to_local": a["R"], "offset": a["off"]},
        "size_mm": a["size"], "tolerances": a["tols"], "holes": holes, "bends": bends, "predictions": preds,
        "dimensions": listed, "dimensions_not_listed": len(dims) - len(listed),
        "scanner": {"suitable": a["proc"] == "sheet" and a["form"] == "flat",
                    "note": ("Flat part: scan it on the glass with the calibration target (mechloop.inspect.scan); the scan measures every hole, "
                             "the outline and overall size against the DXF.") if a["form"] == "flat" else
                            ("Bent part: lay each flange flat on the glass where it fits and scan the holes on it; bend angles, flanges and "
                             "holes-to-bend by calipers and square (see docs/INSPECTION.md).")},
    }
    plan = _jsonable(plan)
    svg = drawing_svg(a, plan)
    return plan, svg


def write_plan(plan: dict, svg: str, out_dir) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pj, ps = out_dir / f"{plan['part_id']}.json", out_dir / f"{plan['part_id']}.svg"
    plan = dict(plan, drawing=ps.name)
    pj.write_text(json.dumps(plan, indent=1))
    ps.write_text(svg)
    return {"json": str(pj), "svg": str(ps)}


def plan_for_step(path, material: str, *, process: str = "sheet", shop: str = "sendcutsend", part_id: str | None = None,
                  revision: str | None = None, name: str | None = None, dxf: str | None = None, source: dict | None = None):
    """Plan for one part read from a STEP file (reference parts and parts outside a design)."""
    from build123d import import_step

    from ..model import Design

    shape = import_step(str(path))
    name = name or Path(path).stem
    d = Design(f"file:{Path(path).name}")
    c = d.add(name, shape, material=material, process=process, meta={"dfm": {"shop": shop}} if shop else {})
    return make_plan(d, c, part_id=part_id or name, revision=revision, dxf=dxf, source=source or {"step": str(path)})


# ------------------------------------------------------------------------------------------- stage 0
REF_MATERIAL = {"RP03": ("al5052", "sheet"), "RP04": ("al6061", "sheet")}
STAGE0_PARTS = ("x_belt_bracket", "y_plate_left", "z_deck")      # z_deck: the bed carrier's sheet deck


def _rel(p) -> str:
    p = Path(p)
    return str(p.relative_to(ROOT)) if p.is_absolute() and p.is_relative_to(ROOT) else str(p)


def stage0(out_dir=None, design_file="designs/printer_v10_1.py", parts=STAGE0_PARTS, refs=("RP03", "RP04")) -> list[dict]:
    """Plans for the reference parts and the likely stage-0 printer parts. Returns [{"part_id", "json", "svg"}]."""
    out_dir = Path(out_dir or ROOT / "inspect_form" / "plans")
    done = []
    batch = ROOT / "reference_parts" / "batch01"
    man = {m["id"]: m for m in json.loads((batch / "manifest.json").read_text())}
    for rid in refs:
        m = man[rid]
        step = next(batch / f for f in m["files"] if f.endswith(".step"))
        dxf = next((_rel(batch / f) for f in m["files"] if f.endswith(".dxf")), None)
        mat, proc = REF_MATERIAL.get(rid, ("al6061", "sheet"))
        plan, svg = plan_for_step(step, mat, process=proc, shop="sendcutsend", part_id=rid, revision="batch01", name=f"{rid}_{m['name']}",
                                  dxf=dxf, source={"step": _rel(step), "manifest": _rel(batch / "manifest.json"), "expected": m.get("expect")})
        done.append({"part_id": rid, **write_plan(plan, svg, out_dir)})
    if parts:
        spec = importlib.util.spec_from_file_location("_inspect_design", ROOT / design_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        d = mod.build()
        dname = Path(design_file).stem
        for n in parts:
            c = d.get(n)
            dxf = ROOT / "out" / dname / "dxf" / f"{n}.dxf"
            plan, svg = make_plan(d, c, part_id=f"{dname}.{n}", revision=dname, dxf=_rel(dxf) if dxf.exists() else None,
                                  source={"design": design_file, "component": n})
            done.append({"part_id": plan["part_id"], **write_plan(plan, svg, out_dir)})
        del d
    done = [{k: (_rel(v) if k in ("json", "svg") else v) for k, v in r.items()} for r in done]
    (out_dir / "index.json").write_text(json.dumps(done, indent=1))
    return done


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage0", action="store_true", help="reference parts RP03, RP04 and printer_v10_1's likely stage-0 parts")
    ap.add_argument("--step", help="one STEP file")
    ap.add_argument("--material", default="al5052")
    ap.add_argument("--process", default="sheet")
    ap.add_argument("--shop", default="sendcutsend")
    ap.add_argument("--design", default="designs/printer_v10_1.py")
    ap.add_argument("--parts", nargs="*")
    ap.add_argument("--out", default=str(ROOT / "inspect_form" / "plans"))
    a = ap.parse_args(argv)
    if a.step:
        plan, svg = plan_for_step(a.step, a.material, process=a.process, shop=a.shop)
        print(json.dumps(write_plan(plan, svg, a.out)))
    elif a.stage0 or a.parts:
        for r in stage0(a.out, a.design, tuple(a.parts or STAGE0_PARTS), refs=("RP03", "RP04") if a.stage0 else ()):
            print(r["part_id"], r["json"])
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
