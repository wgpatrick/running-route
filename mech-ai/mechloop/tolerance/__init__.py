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


RAIL_RESIDUAL_AFTER_ALIGNMENT = 0.02   # mm over the travel left between two rails set against the carrier (ASSUMED)


def _rail_set(design: Design, r: VerifierResult, B, j, pairs, n: int, share, thin) -> dict:
    """An axis guided by THREE OR MORE rails, or by blocks whose mounts float (meta["guide_float"] on the block:
    {"axis": (x, y, z), "stiffness_n_per_mm": k, "range_mm": r}: the mount is a flexure or a slot that is soft along
    `axis` and stiff across it).

    As built each rail leans its own way, so over the travel rail i wanders e_i sideways. The moving body is one rigid
    body in the plane across the axis (two shifts and a turn about the axis); each block holds it with K_GUIDE across its
    rail, except along a declared float, where the mount's own stiffness is in series. The body takes the position of
    least strain energy; what is left is a force on every block. Two blocks on one body can always turn to follow rails
    that drift apart ACROSS the line between them; three blocks that each hold two directions cannot, which is why three
    plain rails over-constrain a carrier and three blocks that each hold only their tangential direction do not.

    Judged like the two-rail case: the force on a block must stay under what a rigid pair sees at the maker's allowable
    parallelism error (K_GUIDE x allowable / 2); with a declared rail alignment (Adjustment kind "rail_align") the as-built
    drift is what the alignment must cover, and the forces are also given for the residual left after it
    (RAIL_RESIDUAL_AFTER_ALIGNMENT, assumed)."""
    comps = {c.name: c for c in design.components}
    ax = np.array(j.axis, dtype=float); ax /= np.linalg.norm(ax)
    travel = abs(j.range[1] - j.range[0])
    t1 = np.cross(ax, [1.0, 0.0, 0.0] if abs(ax[0]) < 0.9 else [0.0, 1.0, 0.0]); t1 /= np.linalg.norm(t1)
    t2 = np.cross(ax, t1)
    T = np.stack([t1, t2])                                   # 2 x 3: world -> plane across the axis
    pairs = [(b, p) for b, p in pairs if p is not None]
    pos = []
    for b, _ in pairs:
        lo, hi = _bb(b.shape)
        pos.append((lo + hi) / 2)
    c0 = np.mean(pos, axis=0)
    Js, Ks, Kstiff, es, fl = [], [], [], [], []
    for (b, rail), p in zip(pairs, pos):
        rr = T @ np.cross(ax, p - c0)                        # in-plane displacement per unit turn about the axis
        Js.append(np.column_stack([np.eye(2), rr]))          # 2 x 3
        d = B.direction(rail.name, ax)
        e = (d - (d @ ax)[:, None] * ax[None, :]) * travel   # n x 3, across the axis
        es.append(e @ T.T)                                   # n x 2
        gf = b.meta.get("guide_float") or None
        if gf:
            f = T @ np.array(gf["axis"], dtype=float)
            f /= max(np.linalg.norm(f), 1e-12)
            kf = float(gf["stiffness_n_per_mm"])
            ks = 1.0 / (1.0 / K_GUIDE + 1.0 / kf)
            P = np.outer(f, f)
            Ks.append(K_GUIDE * (np.eye(2) - P) + ks * P)
            Kstiff.append(K_GUIDE * (np.eye(2) - P))
            fl.append((f, kf, float(gf.get("range_mm", 0.0)), gf.get("by", "")))
        else:
            Ks.append(K_GUIDE * np.eye(2))
            Kstiff.append(K_GUIDE * np.eye(2))
            fl.append(None)
    H = sum(J.T @ K @ J for J, K in zip(Js, Ks))
    Hs = sum(J.T @ K @ J for J, K in zip(Js, Kstiff))
    span = max(float(np.max(np.linalg.norm(np.array(pos) - c0, axis=1))), 1.0)
    S = np.diag([1.0, 1.0, 1.0 / span])                      # the turn scaled to a displacement at the blocks
    ev = np.linalg.eigvalsh(S @ Hs @ S)
    n_stiff = sum(2 - (1 if f is not None else 0) for f in fl)

    def solve(E):
        g = sum(np.einsum("ij,nj->ni", J.T @ K, e) for J, K, e in zip(Js, Ks, E))      # n x 3
        q = np.linalg.solve(H, g.T).T
        F = [np.einsum("ij,nj->ni", K, np.einsum("ij,nj->ni", J, q) - e) for J, K, e in zip(Js, Ks, E)]
        return q, F

    q, F = solve(es)
    side = np.max([np.linalg.norm(Fi, axis=1) for Fi in F], axis=0)
    drag = MU_BALL * np.sum([np.linalg.norm(Fi, axis=1) for Fi in F], axis=0)
    drifts = {}
    for a_ in range(len(pairs)):
        for b_ in range(a_ + 1, len(pairs)):
            if pairs[a_][1].name != pairs[b_][1].name:
                drifts[f"{pairs[a_][1].name} / {pairs[b_][1].name}"] = np.linalg.norm(es[a_] - es[b_], axis=1)
    worst_pair = max(drifts, key=lambda k_: _rng99(drifts[k_]))
    drift = np.max(list(drifts.values()), axis=0)
    blocks = [b for b, _ in pairs]
    allow = min((comps[b.name].ratings.get("allowable_parallelism_mm", 0.025) for b in blocks))
    f_allow = K_GUIDE * allow / 2
    p_ok = float((side <= f_allow).mean())
    adj = _adj(design, "rail_align", j.name)
    out = {"rails": [p.name for _, p in pairs], "blocks": [b.name for b in blocks], "model": "rigid body on its blocks, least strain energy",
           "parallelism_error_over_travel_mm_99": round(_rng99(drift), 3), "worst_pair": worst_pair,
           "by_pair_mm_99": {k_: round(_rng99(v), 3) for k_, v in drifts.items()},
           "allowable_mm": allow,
           "allowable_source": next((comps[b.name].ratings["allowable_parallelism_source"] for b in blocks
                                     if comps[b.name].ratings.get("allowable_parallelism_mm") == allow
                                     and comps[b.name].ratings.get("allowable_parallelism_source")),
                                    "default 0.025 mm (assumed: the guide blocks carry no maker's figure)"),
           "side_load_allowed_n": round(f_allow, 1),
           "side_load_allowed_basis": "what each block of a rigid pair carries at the allowable parallelism error: K_GUIDE x allowable / 2",
           "in_plane_constraints": {"stiff_directions_held": n_stiff, "needed": 3, "redundant": n_stiff - 3,
                                    "note": ("exactly constrained across the axis: no rail error can load the blocks except through the floats"
                                             if n_stiff == 3 else f"{n_stiff - 3} more stiff direction(s) than the three a body needs: rail errors load the blocks"
                                             if n_stiff > 3 else "fewer than three stiff directions: the body is located through a float")},
           "floats": {b.name: {"axis_in_plane": [round(float(v), 3) for v in (f[0] @ T)], "stiffness_n_per_mm": f[1], "range_mm": f[2], "by": f[3]}
                      for b, f in zip(blocks, fl) if f is not None},
           "p_within_allowable": round(p_ok, 3),
           "p_within_allowable_standard_error": share(p_ok, None if adj else 0.9, f"rails of {j.name} parallel")["standard_error"],
           "side_load_on_blocks_n_99": round(_rng99(side), 1), "added_drag_n_99": round(_rng99(drag), 2),
           "by_block_side_load_n_99": {b.name: round(_rng99(np.linalg.norm(Fi, axis=1)), 1) for b, Fi in zip(blocks, F)},
           "aligned_at_assembly": bool(adj)}
    if ev[0] < 1e-6 * K_GUIDE:
        r.add("warning", "guides_locate_through_floats",
              f"Axis {j.name}: the stiff directions of its guide blocks leave the moving body free in one direction across the axis "
              f"(it is held there only by the floating mounts).", joint=j.name,
              hint="Three stiff directions whose lines do not meet in one point locate a body in a plane.")
    def float_use(Fs):
        return {b.name: round(_rng99(np.abs(Fi @ f[0]) / f[1]), 3) for b, f, Fi in zip(blocks, fl, Fs) if f is not None}

    used = float_use(F)                      # as built to drawing, before any alignment
    if used:
        out["float_used_as_built_mm_99"] = used
    F_judged = F
    if not adj and p_ok < 0.9:
        r.add("error", "rails_not_parallel",
              f"Axis {j.name}: its {len({p.name for _, p in pairs})} rails drift up to {_rng99(drift):.2f} mm apart over the {travel:.0f} mm "
              f"travel as built ({worst_pair}); with the blocks' mounts as declared that loads a block with up to {_rng99(side):.0f} N "
              f"sideways, against {f_allow:.0f} N at the maker's allowable error. Built to drawing only {p_ok:.0%} of machines would run "
              f"freely.", joint=j.name, p_ok=round(p_ok, 3),
              hint="Declare how the rails are aligned at assembly (Adjustment kind='rail_align'), or let the mounts float "
                   "(meta['guide_float'] on the blocks) so that only three stiff directions are left.")
    if adj:
        need = _rng99(drift)
        out.update({"alignment_needed_mm_99": round(need, 3), "alignment_available_mm": adj.range_mm,
                    **thin(r, adj, need, f"Axis {j.name}: aligning its rails", n, joint=j.name)})
        if need > adj.range_mm:
            r.add("error", "adjustment_too_small",
                  f"Axis {j.name}: aligning the rails needs up to {need:.2f} mm of movement but '{adj.name}' gives {adj.range_mm} mm.",
                  joint=j.name)
        # after the alignment: the same builds scaled so that the worst pair is RAIL_RESIDUAL_AFTER_ALIGNMENT apart
        scale = RAIL_RESIDUAL_AFTER_ALIGNMENT / np.maximum(drift, 1e-12)
        _, F2 = solve([e * scale[:, None] for e in es])
        side2 = np.max([np.linalg.norm(Fi, axis=1) for Fi in F2], axis=0)
        out["after_alignment"] = {"residual_between_rails_mm": RAIL_RESIDUAL_AFTER_ALIGNMENT, "residual_basis": "ASSUMED",
                                  "side_load_on_blocks_n_99": round(_rng99(side2), 1),
                                  "added_drag_n_99": round(_rng99(MU_BALL * np.sum([np.linalg.norm(Fi, axis=1) for Fi in F2], axis=0)), 2),
                                  "within_allowed_side_load": bool(_rng99(side2) <= f_allow)}
        F_judged = F2
        if used:
            out["after_alignment"]["float_used_mm_99"] = float_use(F2)
        if _rng99(side2) > f_allow:
            r.add("warning", "rails_over_constrained",
                  f"Axis {j.name}: even with its rails set to within {RAIL_RESIDUAL_AFTER_ALIGNMENT} mm of each other (assumed), a block "
                  f"carries up to {_rng99(side2):.0f} N sideways, more than the {f_allow:.0f} N a rigid pair sees at the maker's allowable "
                  f"parallelism error ({allow} mm): {n_stiff} stiff directions hold a body that needs three.", joint=j.name,
                  hint="Let the mounts of all but three stiff directions float (meta['guide_float']), or align the rails more closely.")
    # the floats are judged on what they must take in the machine as it is set up: after the declared alignment if there
    # is one (the rails are then moved, not the mounts), as built otherwise
    for b, f, Fi in zip(blocks, fl, F_judged):
        if f is None or not f[2]:
            continue
        need = _rng99(np.abs(Fi @ f[0]) / f[1])
        if need > f[2]:
            r.add("error", "guide_float_exceeded",
                  f"Axis {j.name}: the floating mount of {b.name} must move {need:.2f} mm to follow its rail"
                  f"{' after the rails are aligned' if adj else ' as built'}, more than the {f[2]:g} mm it is declared to allow.",
                  joint=j.name, part=b.name)
    return out


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
            if len(rails) > 2 or any(b.meta.get("guide_float") for b in blocks):
                # three or more rails, or a block whose mount is declared to float: the general solution
                rails_m[jn] = _rail_set(design, r, B, j, [(b, partner(b, j)) for b in blocks], n, share, thin_adjustment)
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
            # An integral lead-screw motor's screw (the motor's own shaft, ratings["integral_with"]) with no bearing at its
            # far end is a cantilever from the motor's bearings: the part of the drift the nut's float does not take, it
            # takes by bending, at the force 3 E I x / L^3 (L: the nut's height above the motor face at that end of the
            # travel). That force, not a binding nut, is then what is judged (as a drag against the drive force).
            bends = bool(scr.ratings.get("integral_with")) and not follows and not any(
                (c.meta.get("interfaces") or {}).get("axial_limit_n") and c.meta.get("placement") and
                np.linalg.norm(np.cross(np.array(c.meta["placement"], float)[:3, 3] - np.array(scr.meta["placement"], float)[:3, 3], ax)) < 0.5
                for c in design.components if scr.meta.get("placement"))
            err = e0 if follows else e0 + run
            d_root = 0.78 * (2 * float(np.max((hi - lo)[np.abs(ax) < 0.5])) / 2)
            I = math.pi * d_root ** 4 / 64
            k_side = 3 * 193000.0 * I / a_min ** 3
            adj = _adj(design, "float", jn0)
            side = k_side * err
            drag = MU_NUT * side
            avail = j.max_effort or 0.0
            bend = None
            if bends and adj:
                d_sc = float(np.sort(hi - lo)[1]) if len(hi) else 8.0
                I_s = math.pi * (0.78 * d_sc) ** 4 / 64
                L_far = max(abs(npos + q * float(np.sign(ax @ np.abs(ax))) - s_lo) for q in j.range) if nut else (s_hi - s_lo)
                excess = np.maximum(err - adj.range_mm, 0.0)
                f_b = 3 * 193000.0 * I_s * excess / L_far ** 3
                bend = {"screw_follows_by_bending": True, "excess_over_float_mm_99": round(_rng99(excess), 2),
                        "bending_side_force_n_99": round(_rng99(f_b), 1), "bending_drag_n_99": round(_rng99(MU_NUT * f_b), 2),
                        "free_length_at_far_end_mm": round(L_far, 0),
                        "basis": "integral screw, no bearing at its far end: a cantilever from the motor's bearings (root 0.78 d)"}
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
            if bend is not None:
                screws_m[jn].update(bend)
                if avail and bend["bending_drag_n_99"] > 0.3 * avail:
                    r.add("error", "leadscrew_binding",
                          f"Axis {jn}: the integral screw must bend {bend['excess_over_float_mm_99']:.2f} mm beyond the nut's float to follow "
                          f"it ({bend['bending_side_force_n_99']:.0f} N sideways, {bend['bending_drag_n_99']:.1f} N of drag against {avail:.0f} N).",
                          joint=jn)
                elif avail and bend["bending_drag_n_99"] > 0.1 * avail:
                    r.add("warning", "leadscrew_side_load",
                          f"Axis {jn}: the integral screw bends {bend['excess_over_float_mm_99']:.2f} mm beyond the nut's float to follow it, "
                          f"adding {bend['bending_drag_n_99']:.1f} N of drag ({bend['bending_drag_n_99'] / avail:.0%} of the drive force).", joint=jn)
            if adj and _rng99(err) > adj.range_mm and bend is None:
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
