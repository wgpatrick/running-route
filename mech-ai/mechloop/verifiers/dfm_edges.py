"""Sharp edges and corners, and lead-ins (manufacture verifier).

A part drawn as plain boxes and holes has every edge dead sharp. Made that way a sheet part has needle corners, a
machined part cuts the hand that fits it, and a shaft meets its bore edge to edge. This module classifies the edges of
the part's B-rep (no meshing): an edge is SHARP when it joins two faces that meet at an angle (60 to 120 degrees
between their normals) with no blend between them: a fillet makes its edges tangent and a chamfer makes them 45
degrees, so neither counts. Convex edges are the outside ones; a hole's mouth is the circle where a hole's wall meets a
flat face.

(a) sheet:    `sharp_profile_corners` (warning): convex corners of the cut profile (edges through the thickness)
              with no radius. A radius is free in laser or waterjet cutting. Count and places.
(b) machined: `edges_not_broken` (warning): unbroken outside edges, unless the part or the design declares an edge
              break, the usual drawing note: component.meta["edge_break_mm"] = 0.3, or for every machined part
              design.manufacturing["edge_break_mm"] = 0.3 ("break all sharp edges 0.2 to 0.5 mm"), or the edges are
              modelled with chamfers / fillets.
(c) printed:  `printed_edges` (one info for the design): sharp edges on the bed face (elephant's foot: chamfer them)
              and hole mouths without a lead-in chamfer. Information only.
(d) lead-in:  `no_lead_in` (warning): a shaft in a bore (the pairs the fit check finds) where neither the end of the
              shaft nor the mouth of the bore has a chamfer or radius. A bought part's simulation solid usually has no
              chamfers although the real part does: a bought part is taken to have its lead-in only when its solid
              shows one, and the finding says which side is the bought one.

Not judged: burrs, edges between curved faces, whether a person actually handles the part (every custom part is taken
as handled), sheet edges along the cut (a deburring note covers those; the declaration above is honoured for sheet too).
"""
from __future__ import annotations

import math

import numpy as np

from ..model import Design
from ..report import VerifierResult

SHARP_MIN_DEG, SHARP_MAX_DEG = 60.0, 120.0
MIN_EDGE_MM = 1.0
CORNER_RADIUS_MIN_MM = 0.5


def edge_break_of(design: Design, c) -> float | None:
    v = c.meta.get("edge_break_mm")
    if v is None:
        v = (design.manufacturing or {}).get("edge_break_mm")
    return float(v) if v else None


def _edges_with_faces(shape):
    """(edge, face, face) for every edge shared by exactly two faces. Edges are matched by place (midpoint and length),
    which is what two faces of one solid share."""
    seen: dict = {}
    for f in shape.faces():
        for e in f.edges():
            try:
                m = e.position_at(0.5)
                key = (round(m.X, 4), round(m.Y, 4), round(m.Z, 4), round(float(e.length), 4))
            except Exception:
                continue
            seen.setdefault(key, []).append((e, f))
    for key in sorted(seen):
        fs = seen[key]
        if len(fs) == 2:
            yield fs[0][0], fs[0][1], fs[1][1]


def _v(p):
    return np.array([p.X, p.Y, p.Z])


def classify(shape) -> dict:
    """{"sharp_convex": [...], "sharp_concave": n, "hole_mouths": [...], "blended": n}. Each sharp convex edge:
    {"at", "length", "dir" (unit, for a straight edge), "normals"}; each hole mouth: {"at", "dia", "axis", "sharp"}."""
    from build123d import GeomType
    from OCP.BRepAdaptor import BRepAdaptor_Surface

    out = {"sharp_convex": [], "sharp_concave": 0, "hole_mouths": [], "shaft_ends": [], "blended": 0}
    for e, f1, f2 in _edges_with_faces(shape):
        try:
            L = float(e.length)
            if L < MIN_EDGE_MM:
                continue
            p = e.position_at(0.5)
            t = _v(e.tangent_at(0.5))
            n1, n2 = _v(f1.normal_at(p)), _v(f2.normal_at(p))
        except Exception:
            continue
        ang = math.degrees(math.acos(float(np.clip(n1 @ n2, -1.0, 1.0))))
        g1, g2 = f1.geom_type, f2.geom_type
        if not (SHARP_MIN_DEG <= ang <= SHARP_MAX_DEG):
            out["blended"] += ang < SHARP_MIN_DEG and (GeomType.CYLINDER in (g1, g2) or GeomType.TORUS in (g1, g2) or ang > 20.0)
            continue
        d1 = np.cross(n1, t)
        # which way lies face 1 from the edge: towards its own material side of the edge
        try:
            from build123d import Vertex

            q = _v(p) + 0.02 * d1
            if f1.distance_to(Vertex(*q)) > 1e-4:
                d1 = -d1
        except Exception:
            pass
        convex = float(d1 @ n2) < 0
        if g1 == GeomType.PLANE and g2 == GeomType.PLANE:
            if convex:
                out["sharp_convex"].append({"at": [round(float(x), 1) for x in _v(p)], "length": round(L, 2),
                                            "dir": t / max(np.linalg.norm(t), 1e-12), "normals": (n1, n2)})
            else:
                out["sharp_concave"] += 1
        elif {g1, g2} == {GeomType.PLANE, GeomType.CYLINDER}:
            fc = f1 if g1 == GeomType.CYLINDER else f2
            fp = f2 if fc is f1 else f1
            cy = BRepAdaptor_Surface(fc.wrapped).Cylinder()
            a = np.array([cy.Axis().Direction().X(), cy.Axis().Direction().Y(), cy.Axis().Direction().Z()])
            o = np.array([cy.Axis().Location().X(), cy.Axis().Location().Y(), cy.Axis().Location().Z()])
            npl = _v(fp.normal_at(p))
            if abs(abs(float(npl @ a)) - 1.0) > 1e-3:
                continue                                 # not a hole's mouth or a shaft's end: the plane is not square to the axis
            radial = _v(p) - (o + ((_v(p) - o) @ a) * a)
            nc = _v(fc.normal_at(p))
            rec = {"at": [round(float(x), 1) for x in o + ((_v(p) - o) @ a) * a], "dia": round(2 * float(cy.Radius()), 3), "axis": a,
                   "centre": o + ((_v(p) - o) @ a) * a}
            (out["hole_mouths"] if float(nc @ radial) < 0 else out["shaft_ends"]).append(rec)
    return out


def _dedupe(recs, tol=0.05):
    seen, out = [], []
    for r_ in recs:
        key = np.append(np.asarray(r_["centre"], dtype=float), r_["dia"])
        if any(np.linalg.norm(key - k) < tol for k in seen):
            continue
        seen.append(key)
        out.append(r_)
    return out


def check_edges(r: VerifierResult, design: Design, c, proc: str, row: dict, printed_info: dict) -> dict:
    """Findings (a) to (c) for one custom part; returns its metrics and keeps the classification for (d)."""
    cl = classify(c.shape)
    sharp = cl["sharp_convex"]
    mouths = _dedupe(cl["hole_mouths"])
    brk = edge_break_of(design, c)
    out = {"sharp_outside_edges": len(sharp), "sharp_hole_mouths": len(mouths), "blended_edges": int(cl["blended"]),
           "edge_break_declared_mm": brk}
    if proc == "sheet":
        t = row.get("thickness_mm")
        if t is None:
            bb = c.shape.bounding_box()
            t = min(bb.size.X, bb.size.Y, bb.size.Z)
        corners = [e for e in sharp if abs(e["length"] - float(t)) <= 0.05 * float(t) + 0.02]
        out["sharp_profile_corners"] = len(corners)
        if corners:
            r.add("warning", "sharp_profile_corners",
                  f"{c.name}: {len(corners)} outside corner(s) of the cut profile are dead sharp (no radius). A sheet part with needle "
                  f"corners cuts hands and cables and chips its paint; a corner radius costs nothing in laser or waterjet cutting.",
                  part=c.name, count=len(corners), at=[e["at"] for e in corners[:8]], value=0.0, limit=CORNER_RADIUS_MIN_MM,
                  rule="sheet.outside_corner_radius_mm", source="mechloop's own rule: a radius is free in 2D cutting",
                  hint=f"Round every outside corner to at least {CORNER_RADIUS_MIN_MM:g} mm (1 to 3 mm on corners a hand meets).")
    elif proc == "machined":
        if sharp and not brk:
            r.add("warning", "edges_not_broken",
                  f"{c.name}: {len(sharp)} outside edge(s) are drawn dead sharp and no edge break is declared. A machined part comes "
                  f"off the cutter with a burr on such edges; without a note the shop may leave them.",
                  part=c.name, count=len(sharp), at=[e["at"] for e in sharp[:8]],
                  rule="cnc.edge_break_mm", source="usual drawing note: break all sharp edges 0.2 to 0.5 mm",
                  hint="Declare the drawing note: add(..., meta={'edge_break_mm': 0.3}) or design.manufacturing['edge_break_mm'] = 0.3 "
                       "for every machined part; or model chamfers / fillets on the outside edges.")
    elif proc == "printed":
        up = row.get("up")
        on_bed = []
        if up:
            from .manufacture import AXES

            u = np.array(AXES[up], dtype=float)
            zs = [float(np.array(e["at"]) @ u) for e in sharp]
            if zs:
                z0 = min(zs)
                on_bed = [e for e, z in zip(sharp, zs) if z - z0 < 0.05 and (abs(e["normals"][0] @ u) > 0.99 or abs(e["normals"][1] @ u) > 0.99)]
        out["sharp_edges_on_bed_face"] = len(on_bed)
        if on_bed or mouths:
            printed_info[c.name] = {"sharp_edges_on_bed_face": len(on_bed), "hole_mouths_without_lead_in": len(mouths)}
    out["_class"] = cl
    return out


def lead_ins(r: VerifierResult, design: Design, classes: dict) -> list:
    """(d): shaft-in-bore pairs with no chamfer on either part."""
    from ..tolerance.fits import bores_and_shafts

    comps = {c.name: c for c in design.components}
    pairs = bores_and_shafts(design, VerifierResult("fits"), n=8)
    rows = []

    def cls(name):
        if name not in classes:
            try:
                classes[name] = classify(comps[name].shape)
            except Exception:
                classes[name] = {"hole_mouths": [], "shaft_ends": []}
        return classes[name]

    seen = set()
    for key in sorted(pairs):
        try:
            shaft, rest = key.split(" in ", 1)
            bore, dia = rest.rsplit(" (dia ", 1)
            dia = float(dia.rstrip(")"))
        except ValueError:
            continue
        if (shaft, bore) in seen or shaft not in comps or bore not in comps:
            continue
        seen.add((shaft, bore))
        if comps[shaft].cots and comps[bore].cots:
            continue                                   # two bought parts: their makers' business
        if comps[shaft].meta.get("thread_d"):
            continue                                   # a screw's rolled thread end is its own lead-in
        sharp_end = [e for e in cls(shaft)["shaft_ends"] if abs(e["dia"] - dia) < 0.3]
        sharp_mouth = [m_ for m_ in cls(bore)["hole_mouths"] if abs(m_["dia"] - dia) < 0.6]
        # a chamfer or radius on that diameter removes the sharp plane-to-cylinder edge; no such edge left = lead-in there
        shaft_has = not sharp_end
        bore_has = not sharp_mouth
        row = {"shaft": shaft, "bore": bore, "dia_mm": dia, "shaft_end_chamfered": shaft_has, "bore_mouth_chamfered": bore_has}
        rows.append(row)
        if not shaft_has and not bore_has:
            bought = [x for x in (shaft, bore) if comps[x].cots]
            r.add("warning", "no_lead_in",
                  f"{shaft} (dia {dia:g}) goes into {bore} edge to edge: neither the end of the shaft nor the mouth of the bore has a "
                  f"chamfer or radius. Fitted by hand it jams on its first millimetre or shaves the bore."
                  + (f" ({bought[0]} is a bought part whose simulation solid may not show its real chamfer: put the lead-in on your part.)"
                     if bought else ""),
                  parts=[shaft, bore], dia_mm=dia, at=(sharp_mouth[0]["at"] if sharp_mouth else None),
                  rule="assembly.lead_in", source="mechloop's own rule",
                  hint="Chamfer the bore's mouth 0.5 mm x 45 degrees (or 0.1 x the diameter), or the shaft's end.")
    return rows
