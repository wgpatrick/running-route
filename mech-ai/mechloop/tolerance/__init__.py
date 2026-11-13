"""Tolerance verifier: will the parts fit, and will the machine still work, when everything is
made and assembled as accurately as its processes allow and no better?"""
from __future__ import annotations

import math

import numpy as np

from ..model import Design
from ..report import VerifierResult, timed
from .fits import bores_and_shafts, screw_patterns
from .process import PROCESS, process_of
from .stackup import Build, _bb

MU_BALL, MU_NUT = 0.005, 0.2          # rolling guide, sliding bronze/steel nut (assumed)
K_GUIDE = 15000.0                      # N/mm lateral stiffness of a small recirculating guide block (assumed)


def _adj(design: Design, kind: str, joint: str | None = None):
    for a in design.adjustments:
        if a.kind == kind and (joint is None or a.joint in (None, joint)):
            return a
    return None


def _rng99(x) -> float:
    return float(np.percentile(np.abs(x), 99.7))


def verify_tolerance(design: Design, n: int = 3000) -> VerifierResult:
    r = VerifierResult("tolerance")
    with timed(r):
        from ..verifiers.ratings import resolve_drives

        resolve_drives(design)
        comps = {c.name: c for c in design.components}
        m: dict = {"builds_simulated": n,
                   "processes": {p: sum(1 for c in design.components if process_of(c) == p) for p in PROCESS
                                 if any(process_of(c) == p for c in design.components)}}
        sp = screw_patterns(design, r, n)
        m["screw_patterns"] = {"groups": len(sp), "worst": dict(sorted(sp.items(), key=lambda kv: kv[1]["p_all_start"])[:5])}
        bs = bores_and_shafts(design, r, n)
        m["shaft_bore_pairs"] = {"found": len(bs), "worst": dict(sorted(bs.items(), key=lambda kv: -kv[1]["p_bad"])[:5])}
        play = {}
        for key, v in sp.items():
            a, b = key.split(" -> ")
            play[frozenset((a, b))] = max(v["nominal_radial_clearance_mm"], 0.0)
        B = Build(design, n, screw_play=play)
        if B.unplaced:
            m["not_in_stackup"] = B.unplaced[:20]
        joints = {j.name: j for j in design.joints}

        def partner(blk, j):
            other = j.parent if blk.body == j.child else j.child
            best, bd = None, 1.0
            for c in design.components:
                if c.body != other or c.name not in B.A:
                    continue
                try:
                    dd = blk.shape.distance_to(c.shape)
                except Exception:
                    continue
                if dd < bd:
                    best, bd = c, dd
            return best

        # ---- belts: pulleys and clamps must stay in one plane
        belts = {}
        for b in design.belts:
            ax = np.array(b.axis, dtype=float); ax /= np.linalg.norm(ax)
            hs, fixed_h = [], []
            for node in b.path:
                if node[0] == "pulley" and node[1] in B.A:
                    c = comps[node[1]]
                    p = c.meta.get("interfaces", {}).get("belt_center", [None])[0]
                    if p is None:
                        continue
                    h = B.at(node[1], p) @ ax
                    on_shaft = any(len(k) == 2 and node[1] in k and "set_screw" in str(v) for k, v in design.joins.items())
                    (fixed_h if on_shaft else hs).append(h)   # a pulley on a set screw can be slid along its shaft
                elif node[0] == "anchor":
                    part = B.nearest_part(node[1], node[2])
                    if part:
                        hs.append(B.at(part, node[2]) @ ax)
            if len(hs) < 2:
                continue
            H = np.stack(hs, axis=1)
            spread = H.max(axis=1) - H.min(axis=1)
            nominal = float(np.ptp([float(np.mean(h)) for h in hs]))
            p_ok = float((spread <= 1.0).mean())
            belts[b.name] = {"out_of_plane_mm_99": round(_rng99(spread), 2), "p_within_1mm": round(p_ok, 3)}
            if p_ok < 0.95:
                r.add("error" if p_ok < 0.8 else "warning", "belt_out_of_plane",
                      f"Belt {b.name}: its idlers and clamps end up more than 1 mm out of plane in {1 - p_ok:.0%} of builds "
                      f"(up to {_rng99(spread):.1f} mm); the belt would ride up a flange.", belt=b.name,
                      hint="Mount both ends of the belt path on one part, add a locating shoulder, or allow the idler height to be shimmed.")
        if belts:
            m["belts"] = belts
        # ---- axes guided by two or more rails: do the rails end up parallel?
        guides: dict[str, list] = {}
        for c in design.components:
            jn = c.meta.get("guides")
            if jn in joints and "static_load_n" in c.ratings and c.name in B.A:
                guides.setdefault(jn, []).append(c)
        rails_m = {}
        rail_of_joint: dict[str, list[str]] = {}
        for jn, blocks in guides.items():
            j = joints[jn]
            rails = []
            for blk in blocks:
                p = partner(blk, j)
                if p is not None and p.name not in rails:
                    rails.append(p.name)
            rail_of_joint[jn] = rails
            if len(rails) < 2:
                continue
            ax = np.array(j.axis, dtype=float); ax /= np.linalg.norm(ax)
            travel = abs(j.range[1] - j.range[0])
            d0, d1 = B.direction(rails[0], ax), B.direction(rails[1], ax)
            drift = np.linalg.norm((d0 - d1) - ((d0 - d1) @ ax)[:, None] * ax[None, :], axis=1) * travel
            allow = min((comps[b.name].ratings.get("allowable_parallelism_mm", 0.025) for b in blocks))
            adj = _adj(design, "rail_align", jn)
            side = K_GUIDE * drift / 2
            drag = 2 * MU_BALL * side
            p_ok = float((drift <= allow).mean())
            rails_m[jn] = {"rails": rails, "parallelism_error_over_travel_mm_99": round(_rng99(drift), 3),
                           "allowable_mm": allow, "p_within_allowable": round(p_ok, 3),
                           "side_load_on_blocks_n_99": round(_rng99(side), 0), "added_drag_n_99": round(_rng99(drag), 1),
                           "aligned_at_assembly": bool(adj)}
            if not adj and p_ok < 0.9:
                r.add("error", "rails_not_parallel",
                      f"Axis {jn}: its two rails ({rails[0]}, {rails[1]}) drift {_rng99(drift):.2f} mm apart over the "
                      f"{travel:.0f} mm travel as built; the guide blocks allow {allow} mm. Built to drawing only "
                      f"{p_ok:.0%} of machines would run freely; the rest would bind.",
                      joint=jn, p_ok=round(p_ok, 3),
                      hint="Declare how the rails are aligned at assembly (Adjustment kind='rail_align': one rail fixed, the other "
                           "screwed down while the moving plate is run along it), or let one side float.")
            elif adj and _rng99(drift) > adj.range_mm:
                r.add("error", "adjustment_too_small",
                      f"Axis {jn}: aligning the rails needs up to {_rng99(drift):.2f} mm of movement but '{adj.name}' gives "
                      f"{adj.range_mm} mm.", joint=jn)
        if rails_m:
            m["paired_rails"] = rails_m
        # ---- lead screws: screw and rail must be parallel or the nut is forced sideways
        screws_m = {}
        for jn, j in joints.items():
            drv = j.drive or {}
            if drv.get("kind") != "leadscrew" or drv.get("screw") not in B.A or not rail_of_joint.get(jn):
                continue
            ax = np.array(j.axis, dtype=float); ax /= np.linalg.norm(ax)
            scr = comps[drv["screw"]]
            ds, dr = B.direction(scr.name, ax), B.direction(rail_of_joint[jn][0], ax)
            travel = abs(j.range[1] - j.range[0])
            nut = drv.get("nut") if drv.get("nut") in B.A else None
            lo, hi = _bb(scr.shape)
            s_lo, s_hi = float(lo @ np.abs(ax)), float(hi @ np.abs(ax))
            if nut:
                nlo, nhi = _bb(comps[nut].shape)
                nc = (nlo + nhi) / 2
                off = B.at(nut, nc) - B.at(scr.name, nc)
                off = off - (off @ ax)[:, None] * ax[None, :]
                e0 = np.linalg.norm(off, axis=1)
                npos = float(nc @ np.abs(ax))
                a_min = max(min(abs(npos + q * float(np.sign(ax @ np.abs(ax))) - s_lo) for q in j.range), 15.0)
            else:
                e0, a_min = np.zeros(n), 30.0
            run = np.linalg.norm((ds - dr) - ((ds - dr) @ ax)[:, None] * ax[None, :], axis=1) * travel
            err = e0 + run
            d_root = 0.78 * (2 * float(np.max((hi - lo)[np.abs(ax) < 0.5])) / 2)
            I = math.pi * d_root ** 4 / 64
            k_side = 3 * 193000.0 * I / a_min ** 3
            adj = _adj(design, "float", jn)
            side = k_side * err
            drag = MU_NUT * side
            avail = j.max_effort or 0.0
            screws_m[jn] = {"nut_misalignment_mm_99": round(_rng99(err), 2), "screw_side_stiffness_n_per_mm": round(k_side, 1),
                            "nut_closest_to_fixed_end_mm": round(a_min, 0), "side_force_n_99": round(_rng99(side), 0),
                            "added_drag_n_99": round(_rng99(drag), 1), "drive_force_n": avail, "nut_floats": bool(adj)}
            if not adj and avail and _rng99(drag) > 0.3 * avail:
                r.add("error", "leadscrew_binding",
                      f"Axis {jn}: the nut is up to {_rng99(err):.2f} mm off the screw's axis as built, and the screw is "
                      f"stiff sideways near its fixed end ({k_side:.0f} N/mm at {a_min:.0f} mm). That forces up to "
                      f"{_rng99(side):.0f} N sideways on the nut, adding {_rng99(drag):.0f} N of drag to a drive that has {avail:.0f} N.",
                      joint=jn, hint="Let the nut float sideways (Adjustment kind='float'), keep the nut away from the fixed end, "
                                     "or locate screw and rails from one part.")
            elif not adj and avail and _rng99(drag) > 0.1 * avail:
                r.add("warning", "leadscrew_side_load",
                      f"Axis {jn}: nut misalignment adds up to {_rng99(drag):.0f} N of drag ({_rng99(drag) / avail:.0%} of the drive force).",
                      joint=jn)
        if screws_m:
            m["lead_screws"] = screws_m
        # ---- printers: does the nozzle meet the bed, and is the bed level under it?
        if design.printer and design.tool_point and design.printer.get("bed") in B.A:
            spec = design.printer
            body, p = design.tool_point
            noz_part = B.nearest_part(body, p)
            jz, jx, jy = joints[spec["z"]], joints[spec["x"]], joints[spec["y"]]
            bed = spec["bed"]
            blo, bhi = _bb(comps[bed].shape)
            top = bhi[2]
            zdir = np.array(jz.axis, dtype=float)
            zr, xr, yr = (rail_of_joint.get(spec[k], [None])[0] for k in ("z", "x", "y"))
            z_travel = max(jz.range, key=abs)
            dz = B.direction(zr, zdir) if zr else np.tile(zdir, (n, 1))
            dx = B.direction(xr, np.array(jx.axis, dtype=float)) if xr else np.tile(np.array(jx.axis, dtype=float), (n, 1))
            dy = B.direction(yr, np.array(jy.axis, dtype=float)) if yr else np.tile(np.array(jy.axis, dtype=float), (n, 1))
            pn = np.array(p, dtype=float)
            fx, fy = 0.8 * (bhi[0] - blo[0]) / 2, 0.8 * (bhi[1] - blo[1]) / 2
            cx, cy = (blo[0] + bhi[0]) / 2, (blo[1] + bhi[1]) / 2
            pts = [(cx, cy), (cx - fx, cy - fy), (cx + fx, cy - fy), (cx - fx, cy + fy), (cx + fx, cy + fy)]
            gaps = []
            for (bx, by) in pts:
                qx = (bx - pn[0]) * np.sign(jx.axis[0] or 1.0)
                qy = (by - pn[1]) * np.sign(jy.axis[1] or 1.0)
                nz = (B.at(noz_part, pn) + qx * dx + qy * dy)[:, 2]
                bz = (B.at(bed, (bx, by, top)) + z_travel * dz)[:, 2]
                gaps.append(nz - bz)
            G = np.stack(gaps, axis=1)
            nominal = float(pn[2] - (top + z_travel * zdir[2]))
            offset = G[:, 0] - nominal
            tilt = G[:, 1:].max(axis=1) - G[:, 1:].min(axis=1)
            lh = float(spec.get("layer_height", 0.2))
            a_z, a_lvl = _adj(design, "z_offset"), _adj(design, "bed_level")
            pm = {"nominal_gap_mm": round(nominal, 3), "gap_error_mm_99": round(_rng99(offset), 2),
                  "bed_out_of_level_mm_99": round(_rng99(tilt), 2),
                  "largest_contributors_to_gap": B.blame(offset), "largest_contributors_to_level": B.blame(tilt)}
            p_gap = float(((G[:, 0] >= 0) & (G[:, 0] <= lh)).mean())
            p_lvl = float((tilt <= lh / 2).mean())
            pm["p_first_layer_reachable_as_built"] = round(p_gap, 3)
            pm["p_bed_level_within_half_a_layer_as_built"] = round(p_lvl, 3)
            if a_z:
                pm["z_offset_needed_mm_99"], pm["z_offset_available_mm"] = round(_rng99(offset), 2), a_z.range_mm
                if _rng99(offset) > a_z.range_mm:
                    r.add("error", "adjustment_too_small",
                          f"The nozzle-to-bed gap is off by up to {_rng99(offset):.2f} mm as built, but '{a_z.name}' only "
                          f"adjusts {a_z.range_mm} mm.", needed=round(_rng99(offset), 2))
            elif p_gap < 0.95:
                r.add("error", "nozzle_gap_not_adjustable",
                      f"The nozzle-to-bed gap is drawn at {nominal:.2f} mm and must land between 0 and {lh} mm, but it varies "
                      f"by up to +/-{_rng99(offset):.2f} mm from build to build: only {p_gap:.0%} of machines could print their "
                      f"first layer. There is no adjustment for it.", p_ok=round(p_gap, 3),
                      hint="Add a Z offset adjustment (Adjustment kind='z_offset': an adjustable endstop or probe) with a few mm of "
                           "range, and give the Z axis that much extra travel.")
            if a_lvl:
                pm["levelling_needed_mm_99"], pm["levelling_available_mm"] = round(_rng99(tilt) / 2, 2), a_lvl.range_mm
                if _rng99(tilt) / 2 > a_lvl.range_mm:
                    r.add("error", "adjustment_too_small",
                          f"The bed is up to {_rng99(tilt):.2f} mm out of level under the nozzle as built, but '{a_lvl.name}' only "
                          f"adjusts +/-{a_lvl.range_mm} mm.", needed=round(_rng99(tilt) / 2, 2))
            elif p_lvl < 0.95:
                r.add("error", "bed_not_levelable",
                      f"The bed ends up to {_rng99(tilt):.2f} mm out of level relative to the nozzle's travel (limit {lh / 2:.2f} mm, "
                      f"half a layer): only {p_lvl:.0%} of machines would lay a good first layer. There is no bed levelling.",
                      p_ok=round(p_lvl, 3),
                      hint="Add bed levelling (Adjustment kind='bed_level': three sprung screws or a probe with mesh compensation).")
            m["printer"] = pm
        m["adjustments_declared"] = [{"name": a.name, "kind": a.kind, "range_mm": a.range_mm, "joint": a.joint} for a in design.adjustments]
        r.metrics = m
    return r
