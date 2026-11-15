"""Tolerance verifier: will the parts fit, and will the machine still work, when everything is
made and assembled as accurately as its processes allow and no better?"""
from __future__ import annotations

import math

import numpy as np

from ..model import Design
from ..report import VerifierResult, timed
from .fits import bores_and_shafts, screw_patterns
from .process import PROCESS, process_of
from .stackup import SEED, Build, _bb, near_limit, std_error

MU_BALL, MU_NUT = 0.005, 0.2          # rolling guide, sliding bronze/steel nut (assumed)
K_GUIDE = 15000.0                      # N/mm lateral stiffness of a small recirculating guide block (assumed)


class _SkipPrinter(Exception):
    pass


def _adj(design: Design, kind: str, joint: str | None = None):
    for a in design.adjustments:
        if a.kind == kind and (joint is None or a.joint in (None, joint)):
            return a
    return None


def _rng99(x) -> float:
    return float(np.percentile(np.abs(x), 99.7))


ADJUSTMENT_MARGIN_THIN = 0.9      # an adjustment used beyond this share of its range (99.7th percentile of builds) is flagged


def thin_adjustment(r: VerifierResult, adj, need: float, what: str, n: int = 3000, **data) -> dict:
    """An adjustment whose range covers what the builds need, but only just: more than ADJUSTMENT_MARGIN_THIN of the range
    is used at the 99.7th percentile. That percentile rests on about 0.3 % of the simulated builds (9 of 3000), so a
    margin of a few per cent is inside its own sampling noise, and nothing is left for what the stack-up does not
    model. Adds the warning `adjustment_margin_thin`; returns the metrics to put beside the figures."""
    rng_ = float(adj.range_mm)
    used = need / rng_ if rng_ > 0 else float("inf")
    out = {"share_of_range_used_99": round(used, 3), "margin_thin": bool(ADJUSTMENT_MARGIN_THIN < used <= 1.0)}
    if out["margin_thin"]:
        r.add("warning", "adjustment_margin_thin",
              f"{what}: needs up to {need:.3f} mm (99.7th percentile of {n} builds) of the {rng_:g} mm that '{adj.name}' provides: "
              f"{used:.0%} of the range, {rng_ - need:.3f} mm to spare. That percentile rests on the few most extreme builds, so the "
              f"margin is within its own sampling noise, and nothing is left for what the stack-up does not model.",
              adjustment=adj.name, needed_mm=round(need, 3), available_mm=rng_, share_used=round(used, 3), **data,
              hint=f"Give the adjustment more range (about {need / 0.75:.1f} mm would leave a quarter in hand) or shorten the tolerance chain.")
    return out


def verify_tolerance(design: Design, n: int = 3000) -> VerifierResult:
    r = VerifierResult("tolerance")
    with timed(r):
        from ..verifiers.ratings import resolve_drives

        resolve_drives(design)
        comps = {c.name: c for c in design.components}
        noise: list = []     # results the simulation cannot place on one side of their limit

        def share(p: float, limit: float | None = None, what: str = "", builds: int = n) -> dict:
            """Standard error of a simulated share, and whether it is within sampling error (2 s.e.) of its limit."""
            d = {"standard_error": round(std_error(p, builds), 4)}
            if limit is not None:
                d["limit"] = limit
                d["within_sampling_error_of_the_limit"] = near_limit(p, builds, limit)
                if d["within_sampling_error_of_the_limit"]:
                    noise.append(f"{what}: {p:.1%} +/-{std_error(p, builds):.1%} against {limit:.0%}")
            return d

        m: dict = {"builds_simulated": n, "seed": SEED,
                   "monte_carlo": f"{n} simulated builds, fixed seed {SEED} and a fixed order of draws: an identical run gives "
                                  f"identical numbers. Each share p has a sampling error of sqrt(p(1-p)/{n}), given beside it as "
                                  f"standard_error; a share within two standard errors of its limit is flagged.",
                   "processes": {p: sum(1 for c in design.components if process_of(c) == p) for p in PROCESS
                                 if any(process_of(c) == p for c in design.components)}}
        sp = screw_patterns(design, r, n)
        m["screw_patterns"] = {"groups": len(sp), "worst": dict(sorted(sp.items(), key=lambda kv: kv[1]["p_all_start"])[:5])}
        bs = bores_and_shafts(design, r, n)
        sim = {k: v for k, v in bs.items() if v.get("class") != "catalogue fit, trusted"}
        cat = {k: v for k, v in bs.items() if v.get("class") == "catalogue fit, trusted"}
        m["shaft_bore_pairs"] = {"found": len(bs), "simulated": len(sim), "catalogue_fits_trusted": len(cat),
                                 "worst": dict(sorted(sim.items(), key=lambda kv: -kv[1]["p_bad"])[:5]),
                                 "catalogue_fits": cat}
        play = {}
        for key, v in sp.items():
            a, b = key.split(" -> ")
            play[frozenset((a, b))] = max(v["nominal_radial_clearance_mm"], 0.0)
        B = Build(design, n, screw_play=play)
        from .stackup import remember

        remember(design, B)      # the subsystems verifier's endstop and probe windows reuse these builds
        if B.bends or B.bends_not_recognised:
            from .bends import bend_tolerance

            m["bent_sheet_parts"] = {"tolerance": bend_tolerance(design), "parts": {k: v.summary() for k, v in sorted(B.bends.items())},
                                     "how": "each bend: angle and bend-line error; a feature on a flange moves by the angle "
                                            "error times its distance from the bend line, plus the line error"}
            if B.bends_not_recognised:
                m["bent_sheet_parts"]["bends_not_recognised"] = B.bends_not_recognised
                r.add("warning", "sheet_bends_not_recognised",
                      f"{len(B.bends_not_recognised)} sheet part(s) are not flat plates but no bend (inside radius r, outside "
                      f"radius r + t about one axis) could be separated in them: {', '.join(B.bends_not_recognised[:6])}. They are "
                      f"toleranced as flat parts, without bend angle or bend-line scatter, which is optimistic.",
                      parts=B.bends_not_recognised,
                      hint="Model each bend with its inside and outside radius (see 'Can each part be made?').")
        if B.unplaced:
            m["not_in_stackup"] = B.unplaced[:20]
        if B.screwed_apart:      # parts that do not touch but are clamped to each other by screws: located by that joint
            m["located_by_screws_without_contact"] = B.screwed_apart[:40]
        if B.clashes:
            # reported here too so that a `--only tolerance` run shows them; the interference verifier is the judge
            m["clashes_not_used_as_joints"] = B.clashes[:20]
            worst_c = max(B.clashes, key=lambda c: c["overlap_mm3"])
            r.add("warning", "clash_in_stackup",
                  f"{len(B.clashes)} pair(s) of parts overlap in the model without a declared thread, press fit or join "
                  f"(largest: {worst_c['parts'][0]} and {worst_c['parts'][1]}, {worst_c['overlap_mm3']} mm^3). An overlap is a "
                  f"clash, not a seat: it is left out of the stack-up, so it cannot tighten any tolerance chain. Fix the clash "
                  f"(see the interference verifier) before reading the figures below.", pairs=B.clashes[:20])
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
            sh = share(p_ok, 0.95 if p_ok >= 0.875 else 0.8, f"belt {b.name} within 1 mm of plane")
            belts[b.name] = {"out_of_plane_mm_99": round(_rng99(spread), 2), "p_within_1mm": round(p_ok, 3),
                             "p_within_1mm_standard_error": sh["standard_error"], "limit": sh["limit"],
                             "within_sampling_error_of_the_limit": sh["within_sampling_error_of_the_limit"]}
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
                           "allowable_mm": allow,
                           "allowable_source": next((comps[b.name].ratings["allowable_parallelism_source"] for b in blocks
                                                     if comps[b.name].ratings.get("allowable_parallelism_mm") == allow
                                                     and comps[b.name].ratings.get("allowable_parallelism_source")),
                                                    "default 0.025 mm (assumed: the guide blocks carry no maker's figure)"),
                           **({"preload_class": "/".join(sorted({str(comps[b.name].ratings["preload_class"]) for b in blocks
                                                                 if comps[b.name].ratings.get("preload_class")}))}
                              if any(comps[b.name].ratings.get("preload_class") for b in blocks) else {}),
                           "p_within_allowable": round(p_ok, 3),
                           "p_within_allowable_standard_error": share(p_ok, None if adj else 0.9, f"rails of {jn} parallel")["standard_error"],
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
            if adj:
                rails_m[jn].update({"alignment_needed_mm_99": round(_rng99(drift), 3), "alignment_available_mm": adj.range_mm,
                                    **thin_adjustment(r, adj, _rng99(drift), f"Axis {jn}: aligning its two rails", n, joint=jn)})
            if adj and _rng99(drift) > adj.range_mm:
                r.add("error", "adjustment_too_small",
                      f"Axis {jn}: aligning the rails needs up to {_rng99(drift):.2f} mm of movement but '{adj.name}' gives "
                      f"{adj.range_mm} mm.", joint=jn)
        if rails_m:
            m["paired_rails"] = rails_m
        # ---- lead screws: screw and rail must be parallel or the nut is forced sideways
        screws_m = {}
        def _one_screw(jn0, jn, j, drv):
            if drv.get("screw") not in B.A or not rail_of_joint.get(jn0):
                return
            ax = np.array(j.axis, dtype=float); ax /= np.linalg.norm(ax)
            scr = comps[drv["screw"]]
            ds, dr = B.direction(scr.name, ax), B.direction(rail_of_joint[jn0][0], ax)
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
            perp = (ds - dr) - ((ds - dr) @ ax)[:, None] * ax[None, :]
            ang = np.degrees(np.linalg.norm(perp, axis=1))
            run = np.linalg.norm(perp, axis=1) * travel
            # A flexible coupler lets a screw with a free far end swing to follow the nut. The swing it needs is never more
            # than the angle between screw and rails, so a coupler rated for that angle takes the drift over the travel;
            # only the offset where the nut sits when it is nearest the motor is left for the nut mount to absorb.
            cpl = comps.get(drv.get("coupler")) if drv.get("coupler") else None
            cpl_deg = (cpl.ratings.get("angular_misalignment_deg") if cpl else None)
            follows = bool(cpl_deg) and _rng99(ang) <= cpl_deg
            err = e0 if follows else e0 + run
            d_root = 0.78 * (2 * float(np.max((hi - lo)[np.abs(ax) < 0.5])) / 2)
            I = math.pi * d_root ** 4 / 64
            k_side = 3 * 193000.0 * I / a_min ** 3
            adj = _adj(design, "float", jn0)
            side = k_side * err
            drag = MU_NUT * side
            avail = j.max_effort or 0.0
            screws_m[jn] = {"nut_misalignment_mm_99": round(_rng99(err), 2), "offset_at_nut_mm_99": round(_rng99(e0), 2),
                            "drift_over_travel_mm_99": round(_rng99(run), 2), "screw_to_rail_angle_deg_99": round(_rng99(ang), 2),
                            "coupler_angle_rating_deg": cpl_deg, "drift_taken_by_coupler": follows,
                            "nut_in_stackup": bool(nut),
                            "screw_side_stiffness_n_per_mm": round(k_side, 1),
                            "nut_closest_to_fixed_end_mm": round(a_min, 0), "side_force_n_99": round(_rng99(side), 0),
                            "added_drag_n_99": round(_rng99(drag), 1), "drive_force_n": avail, "nut_floats": bool(adj)}
            if cpl_deg and not follows:
                r.add("warning", "coupler_angle_exceeded",
                      f"Axis {jn}: screw and rails are up to {_rng99(ang):.2f} deg out of parallel as built, more than the "
                      f"coupler's {cpl_deg} deg. The drift over the travel then has to be taken at the nut.", joint=jn)
            if not nut:
                r.add("warning", "nut_not_in_stackup",
                      f"Axis {jn}: the drive names no nut, so the offset between the nut's seat and the screw is not checked.",
                      joint=jn, hint="Name the nut in the joint's drive (drive={..., 'nut': '<part>'}).")
            if adj:
                screws_m[jn]["float_available_mm"] = adj.range_mm
                screws_m[jn].update(thin_adjustment(r, adj, _rng99(err), f"Axis {jn}: the nut's float against the screw's axis", n, joint=jn))
            if adj and _rng99(err) > adj.range_mm:
                r.add("error", "adjustment_too_small",
                      f"Axis {jn}: the nut is up to {_rng99(err):.2f} mm off the screw's axis as built, but '{adj.name}' lets it "
                      f"move only +/-{adj.range_mm} mm. Past that the nut is forced sideways and the screw binds.",
                      joint=jn, needed=round(_rng99(err), 2),
                      hint="Give the nut more sideways room, shorten the tolerance chain between screw and rails, "
                           "couple the screw through a flexible coupler rated for the angle, or locate the screw's "
                           "bearing and the rails from one part.")
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

        for jn0, j in joints.items():
            drv0 = j.drive or {}
            if drv0.get("kind") != "leadscrew":
                continue
            # one screw, or several (drive={"screw": [..], "nut": [..], "coupler": [..]}): each screw against the rails
            as_list = lambda v: [v] if isinstance(v, str) else list(v or [])
            scr_l, nut_l, cpl_l = as_list(drv0.get("screw")), as_list(drv0.get("nut")), as_list(drv0.get("coupler"))
            for i_s, scr_n in enumerate(scr_l):
                drv = {"kind": "leadscrew", "screw": scr_n, "nut": nut_l[i_s] if i_s < len(nut_l) else None,
                       "coupler": cpl_l[i_s] if i_s < len(cpl_l) else None}
                jn = jn0 if len(scr_l) == 1 else f"{jn0}:{scr_n}"
                _one_screw(jn0, jn, j, drv)
        if screws_m:
            m["lead_screws"] = screws_m
        # ---- printers: does the nozzle meet the bed, and is the bed level under it?
        try:
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
              # Which of the two rides the Z joint? Either arrangement is a printer: a bed that rises to a fixed gantry, or
              # a gantry / arm that comes down to a fixed bed (a bed-slinger's Z, a cantilever machine). The end of the Z
              # working range at which nozzle and bed meet is found from the drawing, not assumed.
              from ..verifiers.motion import _under_body

              def rides(body, j):
                  return _under_body(design, body, j.child)

              bed_body = comps[bed].body
              noz_z, bed_z = rides(body, jz), rides(bed_body, jz)
              pn = np.array(p, dtype=float)
              if noz_z == bed_z:
                  r.add("error", "printer_z_arrangement",
                        f"Joint '{jz.name}' is declared as the printer's Z, but "
                        + ("both the nozzle's body and the bed ride on it" if noz_z else "neither the nozzle's body nor the bed rides on it")
                        + ": it cannot change the nozzle-to-bed gap. The nozzle-to-bed checks were NOT run.", joint=jz.name,
                        hint="design.printer['z'] must name the joint that moves the bed towards the nozzle or the nozzle "
                             "towards the bed.")
                  raise _SkipPrinter()

              def drawn_gap(q):
                  return float(pn[2] + (q * zdir[2] if noz_z else 0.0) - (top + (q * zdir[2] if bed_z else 0.0)))

              z_travel = min(jz.range, key=lambda q: abs(drawn_gap(q)))
              dz = B.direction(zr, zdir) if zr else np.tile(zdir, (n, 1))
              dx = B.direction(xr, np.array(jx.axis, dtype=float)) if xr else np.tile(np.array(jx.axis, dtype=float), (n, 1))
              dy = B.direction(yr, np.array(jy.axis, dtype=float)) if yr else np.tile(np.array(jy.axis, dtype=float), (n, 1))
              fx, fy = 0.8 * (bhi[0] - blo[0]) / 2, 0.8 * (bhi[1] - blo[1]) / 2
              cx, cy = (blo[0] + bhi[0]) / 2, (blo[1] + bhi[1]) / 2
              pts = [(cx, cy), (cx - fx, cy - fy), (cx + fx, cy - fy), (cx - fx, cy + fy), (cx + fx, cy + fy)]
              gaps = []
              for (bx, by) in pts:
                  qx = (bx - pn[0]) * np.sign(jx.axis[0] or 1.0)
                  qy = (by - pn[1]) * np.sign(jy.axis[1] or 1.0)
                  # the travel that brings this bed point under the nozzle is the nozzle's on the joints its body rides
                  # and the bed's (the other way) on the joints the bed rides
                  noz_move = sum(q_ * d_ for q_, d_, j_ in ((qx, dx, jx), (qy, dy, jy)) if not rides(bed_body, j_))
                  bed_move = sum(-q_ * d_ for q_, d_, j_ in ((qx, dx, jx), (qy, dy, jy)) if rides(bed_body, j_))
                  nz = (B.at(noz_part, pn) + noz_move + (z_travel * dz if noz_z else 0.0))[:, 2]
                  bz = (B.at(bed, (bx, by, top)) + bed_move + (z_travel * dz if bed_z else 0.0))[:, 2]
                  gaps.append(nz - bz)
              G = np.stack(gaps, axis=1)
              nominal = drawn_gap(z_travel)
              offset = G[:, 0] - nominal
              tilt = G[:, 1:].max(axis=1) - G[:, 1:].min(axis=1)
              lh = float(spec.get("layer_height", 0.2))
              a_z, a_lvl = _adj(design, "z_offset"), _adj(design, "bed_level")
              pm = {"z_arrangement": "the bed rides Z" if bed_z else "the nozzle rides Z", "nozzle_meets_bed_at": {jz.name: z_travel},
                    "nominal_gap_mm": round(nominal, 3), "gap_error_mm_99": round(_rng99(offset), 2),
                    "bed_out_of_level_mm_99": round(_rng99(tilt), 2),
                    "largest_contributors_to_gap": B.blame(offset), "largest_contributors_to_level": B.blame(tilt)}
              p_gap = float(((G[:, 0] >= 0) & (G[:, 0] <= lh)).mean())
              p_lvl = float((tilt <= lh / 2).mean())
              pm["p_first_layer_reachable_as_built"] = round(p_gap, 3)
              pm["p_bed_level_within_half_a_layer_as_built"] = round(p_lvl, 3)
              pm["p_first_layer_reachable_standard_error"] = share(p_gap, None if a_z else 0.95, "first layer reachable as built")["standard_error"]
              pm["p_bed_level_standard_error"] = share(p_lvl, None if a_lvl else 0.95, "bed level within half a layer as built")["standard_error"]
              # declared over-travel past the working range (Joint.overtravel): a bed built low can still be brought up
              ot_z = abs(jz.mechanical_range[1] - jz.range[1]) if z_travel == jz.range[1] else abs(jz.range[0] - jz.mechanical_range[0])
              if ot_z > 0:
                  p_ot = float((G[:, 0] <= lh + ot_z).mean())
                  pm["z_overtravel_mm"] = round(ot_z, 3)
                  pm["p_bed_reaches_nozzle_with_overtravel"] = round(p_ot, 3)
                  pm["p_bed_reaches_nozzle_with_overtravel_standard_error"] = round(std_error(p_ot, n), 4)
              if a_z:
                  pm["z_offset_needed_mm_99"], pm["z_offset_available_mm"] = round(_rng99(offset), 2), a_z.range_mm
                  pm["z_offset_margin"] = thin_adjustment(r, a_z, _rng99(offset), "The nozzle-to-bed gap", n)
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
                  pm["levelling_note"] = ("levelling_needed is HALF of bed_out_of_level: a level adjustment of +/- its range at each "
                                          "corner takes out twice its range of height difference")
                  pm["levelling_margin"] = thin_adjustment(r, a_lvl, _rng99(tilt) / 2, "Levelling the bed", n)
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
              from .process import stock_plate_flatness

              spf = stock_plate_flatness(comps[bed].material, float(min(bhi - blo)))
              if spf:      # reference only: the bed-level figures above are about tilt, not the plate's own bow
                  pm["bed_plate_stock_flatness"] = {**spf, "note": "maker's guarantee for the plate as supplied; a reference value, "
                                                    "not applied to the stack-up. A probed bed mesh is what takes it up"}
              m["printer"] = pm
        except _SkipPrinter:
            pass
        # ---- clearances: gaps that are drawn open, across the same builds
        try:
            from .clearance import clearance_check

            pairs_bs = []
            for key in bs:
                na, rest = key.split(" in ", 1)
                pairs_bs.append((na, rest.rsplit(" (dia", 1)[0]))
            m["clearances"] = clearance_check(design, B, r, shaft_pairs=pairs_bs)
        except Exception as e:      # not evaluated must never read as a pass
            import traceback

            r.add("error", "clearance_check_failed", f"The clearance-under-tolerance check did not run: {type(e).__name__}: {e}",
                  trace=traceback.format_exc()[-600:])
        if noise:
            m["within_sampling_error_of_a_limit"] = noise
            r.add("info", "within_sampling_error_of_the_limit",
                  f"{len(noise)} result(s) are within sampling error (two standard errors, {n} builds) of the limit they are "
                  f"judged against, so the pass or fail could go either way with more builds: " + "; ".join(noise[:6]) + ".",
                  results=noise)
        m["adjustments_declared"] = [{"name": a.name, "kind": a.kind, "range_mm": a.range_mm, "joint": a.joint} for a in design.adjustments]
        r.metrics = m
    return r
