"""CNC milled (and plainly turned) parts on a 3-axis machine.

The part is measured in its own frame. From the exact geometry: inside corners (sharp, or a radius against
the depth a tool of that radius must reach), holes (depth to diameter, standard drill sizes) and the
threads screws need in it. From rays over the sampled surface: which of the six directions a cutter can
reach each bit of surface from (set-ups, undercuts), wall and floor thickness, and how deep and narrow the
slots and pockets are. From the bounding box: the stock, how much of it becomes chips, and a rough time
and cost, labelled as an estimate.
"""
from __future__ import annotations

import math

import numpy as np

from . import dfm_geom as G
from .dfm_rules import MACHINING, PLASTICS, PROGRAM_MIN, SETUP_MIN, SHOP_RATE_USD_H, Limits, standard_drill
from .dfm_sheet import plate_of

ROUND_BAR_MM = (6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100, 120, 150, 200)


def _dir_name(axes: dict, v: np.ndarray) -> str | None:
    for nm, a in axes.items():
        if a @ v > 0.9995:
            return nm
    return None


def check_machined(r, design, c, sm: G.Sampled, frame: np.ndarray, cyls: list, holes: list, lim: Limits, proc: str) -> dict:
    from ..model import MATERIALS

    name, shape = c.name, c.shape
    plastic = c.material in PLASTICS
    axes = G.axis_names(frame)
    world = bool(np.allclose(frame, np.eye(3), atol=1e-6))
    lo, hi = G.extents(sm, frame)
    size = hi - lo
    row: dict = {}
    if not world:
        row["frame"] = "the part's own axes (it sits at an angle in the assembly)"

    def add(sev, code, msg, rule=None, value=None, at=None, hint=None, **more):
        data = {"part": name}
        if rule:
            data.update(lim.data(rule, value))
        if at is not None:
            data["at"] = at
        if hint:
            data["hint"] = hint
        data.update(more)
        r.add(sev, code, f"{name}: {msg}", **data)

    turned = G.turned_axis(shape, cyls)
    plate = None if turned else plate_of(shape, frame, sm)
    tapped = G.tapped_holes(design, c, sm)

    # ------------------------------------------------------------------ form and stock
    if turned:
        o, a = turned
        ext = np.asarray(sm.mesh.vertices) - o
        length = float(np.ptp(ext @ a))
        dia = 2 * float(np.linalg.norm(ext - np.outer(ext @ a, a), axis=1).max())
        bar = next((b for b in ROUND_BAR_MM if b >= dia - 1e-6), math.ceil(dia))
        stock_vol = math.pi * bar ** 2 / 4 * (length + 3.0)
        row.update({"form": "turned", "stock": f"round bar {bar:g} mm x {length + 3:.0f} mm", "diameter_mm": round(dia, 2),
                    "length_mm": round(length, 2), "setups_estimate": 1 if not holes or all(len(h.open_dirs) for h in holes) else 2,
                    "cut_from": ["lathe"]})
        if length / max(dia, 1e-9) > 10:
            add("warning", "slender_turned_part", f"{length:.0f} mm long at {dia:g} mm diameter ({length / dia:.0f}:1): it deflects under the "
                f"tool and needs a steady rest or tailstock.", value=length / dia, limit=10.0, source=lim.rule("cnc.part_max_mm").source_text,
                hint="Shorten it, thicken it, or buy ground shaft and cut it to length.")
    elif plate:
        t = plate["thickness"]
        stock = lim.stock("plate_stock", c.material)
        near = min(stock, key=lambda s_: abs(s_ - t))
        row.update({"form": "plate", "thickness_mm": round(t, 2), "tool_axis": "XYZ"[plate["k"]]})
        others = sorted((size[i] for i in range(3) if i != plate["k"]), reverse=True)
        if abs(near - t) > 0.05:
            up = next((s_ for s_ in stock if s_ >= t), None)
            add("warning", "non_stock_thickness",
                f"{t:.2f} mm thick is not a stock plate thickness (nearest {near:g} mm), so both faces would need machining"
                + (f" down from {up:g} mm." if up else "."), part_thickness=round(t, 3), value=round(t, 3), limit=near,
                source=lim.rule("cnc.setups_max").source_text, hint=f"Use {near:g} mm if the design allows.")
            st = up or math.ceil(t + 1)
        else:
            st = near
        stock_vol = (others[0] + 4) * (others[1] + 4) * st
        row["stock"] = f"plate {st:g} mm, blank {others[0] + 4:.0f} x {others[1] + 4:.0f} mm"
        row["could_be_cut_2d"] = bool(not plate["steps"] and not plate["countersinks"])
    else:
        blank = [math.ceil(s_ + 2.0) for s_ in size]
        stock_vol = float(np.prod(blank))
        row.update({"form": "block", "stock": f"block {blank[0]} x {blank[1]} x {blank[2]} mm"})
    removed = 1.0 - float(shape.volume) / max(stock_vol, 1e-9)
    row["material_removed_fraction"] = round(removed, 2)
    if removed > lim("cnc.removed_max_fraction") and not turned:
        add("warning", "mostly_chips", f"{removed:.0%} of the {row['stock']} is machined away.", rule="cnc.removed_max_fraction", value=removed,
            hint="Build it from plates or bar bolted together, start from an extrusion or angle section, or print it if loads allow.")
    if max(size) > lim("cnc.part_max_mm"):
        add("warning", "too_big_to_mill", f"{max(size):.0f} mm long: beyond a general shop's mill travel.", rule="cnc.part_max_mm", value=float(max(size)))

    # ------------------------------------------------------------------ surfaces a 3-axis mill dislikes
    fc = G.face_classes(shape, frame)
    if not turned and (fc["angled_planes"] or fc["angled_cyls"] or fc["tori"] or fc["other"]):
        at = (fc["angled_at"] + fc["curved_at"])[:6]
        add("warning", "angled_faces", f"has {fc['angled_planes'] + fc['angled_cyls']} face(s) at an angle to all three of its axes and "
            f"{fc['tori'] + fc['other']} doubly curved face(s) (first at {at[0]}); needs a tilted set-up, form or ball tooling, or a 5-axis machine.",
            at=at, source=lim.rule("cnc.corner_radius_min_mm").source_text,
            hint="Square the feature to the part's faces, or accept the extra set-up; chamfers are cheap, compound angles are not.")

    # ------------------------------------------------------------------ holes
    deep, deep_err, odd, tiny = [], [], [], []
    for h in holes:
        ratio = h.depth / h.diameter
        if ratio > lim("cnc.hole_depth_limit"):
            deep_err.append((ratio, h))
        elif ratio > lim("cnc.hole_depth_ratio"):
            deep.append((ratio, h))
        if h.diameter < lim("cnc.hole_min_mm") - 1e-9:
            tiny.append(h)
        if h.diameter <= lim("cnc.drill_max_mm"):
            std, off = standard_drill(h.diameter)
            if off > lim("cnc.drill_tolerance_mm"):
                odd.append((h, std))
    row["holes"] = len(holes)
    for lst, sev, code, rid, tail in ((deep_err, "error", "hole_too_deep", "cnc.hole_depth_limit", "no drill reaches that far"),
                                      (deep, "warning", "deep_hole", "cnc.hole_depth_ratio", "it needs a long-series or gun drill and pecking")):
        if lst:
            ratio, h = max(lst, key=lambda q: q[0])
            add(sev, code, f"{len(lst)} hole(s) deeper than {lim(rid):g} diameters (worst {h.diameter:g} mm x {h.depth:.1f} mm deep = {ratio:.0f}:1 "
                f"at {G.xyz(h.origin)}); {tail}.", rule=rid, value=ratio, at=[G.xyz(q[1].origin) for q in lst[:6]],
                hint="Drill from both ends, step the hole to a larger diameter for most of its depth, or split the part.")
    if tiny:
        h = min(tiny, key=lambda q: q.diameter)
        add("warning", "tiny_hole", f"{len(tiny)} hole(s) under {lim('cnc.hole_min_mm'):g} mm (smallest {h.diameter:g} mm at {G.xyz(h.origin)}): micro-drilling.",
            rule="cnc.hole_min_mm", value=h.diameter, at=[G.xyz(q.origin) for q in tiny[:6]])
    if odd:
        sizes = sorted({(round(h.diameter, 3), std) for h, std in odd})
        add("warning", "non_standard_drill", f"{len(odd)} hole(s) at a diameter no standard drill makes: "
            + ", ".join(f"{d:g} mm (nearest {s_:g})" for d, s_ in sizes[:4]) + "; each must be interpolated with an end mill or reamed.",
            rule="cnc.drill_tolerance_mm", value=max(abs(d - s_) for d, s_ in sizes), at=[G.xyz(h.origin) for h, _ in odd[:6]],
            hint="Use the nearest standard size unless the fit needs this one (then state the tolerance).")

    # ------------------------------------------------------------------ threads the screws need
    if tapped:
        row["tapped_holes"] = len(tapped)
        small = [tp for tp in tapped if tp["d"] < lim("cnc.thread_min_mm") - 1e-9]
        long_ = [tp for tp in tapped if tp["engagement"] > lim("cnc.thread_depth_ratio") * tp["d"] + 0.3]
        runout = [tp for tp in tapped if tp["d"] < 6.0 and 0.3 < tp["beyond_tip"] < lim("cnc.blind_tap_runout_d_ratio") * tp["d"] - 1e-6]
        if small:
            add("warning", "thread_too_small", f"{len(small)} thread(s) under M{lim('cnc.thread_min_mm'):g}; taps that small break.",
                rule="cnc.thread_min_mm", value=min(tp["d"] for tp in small), at=[tp["at"] for tp in small[:6]])
        if long_:
            tp = max(long_, key=lambda q: q["engagement"] / q["d"])
            add("warning", "thread_deeper_than_needed", f"{len(long_)} tapped hole(s) threaded deeper than {lim('cnc.thread_depth_ratio'):g} diameters "
                f"(M{tp['d']:g} engaged {tp['engagement']:.1f} mm at {tp['at']}): the extra depth carries no load and risks a broken tap.",
                rule="cnc.thread_depth_ratio", value=tp["engagement"] / tp["d"], at=[q["at"] for q in long_[:6]], hint="Use a shorter screw.")
        if runout:
            tp = min(runout, key=lambda q: q["beyond_tip"] / q["d"])
            add("warning", "blind_tap_runout",
                f"{len(runout)} tapped hole(s) end {tp['beyond_tip']:.1f} mm short of the far face (M{tp['d']:g}, screw {tp['screw']}, at {tp['at']}): a tapped "
                f"blind hole needs {lim('cnc.blind_tap_runout_d_ratio'):g} x d = {lim('cnc.blind_tap_runout_d_ratio') * tp['d']:.1f} mm of plain hole below the "
                f"thread, so the tap drill breaks out or leaves a paper-thin floor.", rule="cnc.blind_tap_runout_d_ratio",
                value=tp["beyond_tip"] / tp["d"], at=[q["at"] for q in runout[:6]],
                hint="Tap it right through (cheaper, and chips clear), or leave more material below the screw.")

    # ------------------------------------------------------------------ inside corners
    sharp = [] if turned else G.sharp_inside_edges(shape, sm, frame)
    never = [e for e in sharp if not e["reach"]]
    made = [e for e in sharp if e["reach"]]
    # on a plate, a corner between two walls that only a cutter lying in the plate's plane can square up
    side = [e for e in made if plate and not any(abs(nd @ plate["axis"]) > 0.99 for nd in e["reach"])]
    row["sharp_inside_corners"] = len(never)
    if never:
        add("error", "sharp_inside_corner",
            f"{len(never)} inside corner(s) with no radius that no cutter can reach square-on (first at {never[0]['at']}); a rotating cutter leaves "
            f"a radius there, so the corner cannot be made as drawn and a square mating part will not seat.",
            rule="cnc.corner_radius_min_mm", value=0.0, at=[e["at"] for e in never[:6]],
            hint="Add an inside radius of at least 1.5 mm (3 mm cutter), relieve the corner with a dog-bone, or chamfer/radius the mating part.")
    fillets = [cy for cy in cyls if cy.concave and cy.angle < 300 and np.max(np.abs(frame @ cy.axis)) > 0.9995]
    small_r, deep_c, deep_c_err = [], [], []
    for cy in fillets:
        depth = cy.hi - cy.lo
        ratio = depth / (2 * cy.radius)
        if cy.radius < lim("cnc.corner_radius_min_mm") - 1e-6:
            small_r.append(cy)
        if ratio > lim("cnc.corner_depth_limit"):
            deep_c_err.append((ratio, cy))
        elif ratio > lim("cnc.corner_depth_ratio"):
            deep_c.append((ratio, cy))
    if small_r:
        cy = min(small_r, key=lambda q: q.radius)
        add("warning", "small_inside_radius", f"{len(small_r)} inside corner radius(es) under {lim('cnc.corner_radius_min_mm'):g} mm (smallest "
            f"{cy.radius:g} mm at {G.xyz(cy.mid)}): needs a cutter under {2 * lim('cnc.corner_radius_min_mm'):g} mm, slow and fragile.",
            rule="cnc.corner_radius_min_mm", value=cy.radius, at=[G.xyz(q.mid) for q in small_r[:6]],
            hint="Open the radius to 1.5 mm or more (a little over the cutter radius lets the tool sweep the corner).")
    for lst, sev, code, rid in ((deep_c_err, "error", "corner_too_deep", "cnc.corner_depth_limit"), (deep_c, "warning", "deep_inside_corner", "cnc.corner_depth_ratio")):
        if lst:
            ratio, cy = max(lst, key=lambda q: q[0])
            add(sev, code, f"{len(lst)} inside corner(s) deeper than {lim(rid):g} x the cutter that fits them (worst: radius {cy.radius:g} mm, "
                f"{cy.hi - cy.lo:.1f} mm deep = {ratio:.1f}:1 at {G.xyz(cy.mid)}); a cutter that slender chatters and deflects.",
                rule=rid, value=ratio, at=[G.xyz(q[1].mid) for q in lst[:6]],
                hint=f"Make the radius at least a third of the depth ({(cy.hi - cy.lo) / 3:.1f} mm here), or make the feature shallower.")
    tool_limits = [2 * cy.radius for cy in fillets]

    # ------------------------------------------------------------------ walls, floors, slots
    wt = G.wall_thickness(sm)
    w_err = lim("cnc.wall_min_plastic_mm" if plastic else "cnc.wall_min_metal_mm")
    w_rec = lim("cnc.wall_recommended_plastic_mm" if plastic else "cnc.wall_recommended_metal_mm")
    row["min_wall_mm"] = round(float(wt[np.isfinite(wt)].min()), 2) if np.isfinite(wt).any() else None
    thin = wt < w_rec - 1e-6
    if thin.sum() >= 2:
        pts, vals = sm.pts[thin], wt[thin]
        sel = G.spread(pts, vals, k=6, min_sep=4.0)
        bad = float(vals.min()) < w_err - 1e-6
        rid = ("cnc.wall_min_" if bad else "cnc.wall_recommended_") + ("plastic_mm" if plastic else "metal_mm")
        add("error" if bad else "warning", "thin_wall",
            f"wall or floor as thin as {vals.min():.2f} mm at {G.xyz(pts[sel[0]])} (about {sm.w[thin].sum():.0f} mm² under {w_rec:g} mm): "
            + ("it tears or folds under the cutter." if bad else "it rings and deflects under the cutter, so it is slow to cut and inaccurate."),
            rule=rid, value=float(vals.min()), at=[G.xyz(pts[i]) for i in sel],
            hint=f"Thicken to {w_rec:g} mm or more, or move the feature that thins it.")
    hole_mask = np.zeros(len(sm.pts), dtype=bool)
    for h in holes:
        rel = sm.pts - h.origin
        ax = rel @ h.axis
        rad = np.linalg.norm(rel - np.outer(ax, h.axis), axis=1)
        hole_mask |= (np.abs(rad - h.diameter / 2) < 0.06) & (np.abs(ax) <= h.depth / 2 + 0.05)
        for dd, dp in h.steps:
            hole_mask |= (np.abs(rad - dd / 2) < 0.06)
    gp = np.where(hole_mask, np.inf, G.gap_width(sm))      # holes are judged as holes, not as slots
    cand = np.nonzero(np.isfinite(gp) & (gp < 60.0))[0]
    slot_ratio = np.zeros(len(cand))
    for nm, d in axes.items():
        if not len(cand):
            break
        perp = np.abs(sm.nrm[cand] @ d) < 0.02
        ok = perp & G.clear_along(sm, d)[cand]
        if not ok.any():
            continue
        sub = cand[ok]
        # how far the wall runs on towards the opening: a ray just inside the material, towards the cutter
        depth, _ = G.ray_hits(sm.tris, sm.pts[sub] - sm.nrm[sub] * 0.02, d)
        ratio = np.where(np.isfinite(depth), depth, 0.0) / gp[sub]
        cur = slot_ratio[ok]
        slot_ratio[ok] = np.where(cur == 0, ratio, np.minimum(cur, ratio))     # the cutter comes from the shallowest side
    narrow = cand[(gp[cand] < lim("cnc.slot_min_mm") - 1e-6) & (slot_ratio > 0)]
    if len(narrow) >= 2:
        k = narrow[int(np.argmin(gp[narrow]))]
        add("warning", "narrow_slot", f"slot or gap {gp[k]:.2f} mm wide at {G.xyz(sm.pts[k] + sm.nrm[k] * gp[k] / 2)}: narrower than the "
            f"{lim('cnc.slot_min_mm'):g} mm of a standard small end mill.", rule="cnc.slot_min_mm", value=float(gp[k]),
            at=[G.xyz(sm.pts[i] + sm.nrm[i] * gp[i] / 2) for i in narrow[G.spread(sm.pts[narrow], gp[narrow], k=6)]],
            hint="Widen it, or cut it with a slitting saw if it is open at both ends.")
        tool_limits.append(float(gp[narrow].min()))
    for rid, sev, code in (("cnc.pocket_depth_limit", "error", "slot_too_deep"), ("cnc.pocket_depth_ratio", "warning", "deep_narrow_slot")):
        sel = slot_ratio > lim(rid)
        if sel.sum() >= 2:
            idx = cand[sel]
            k = idx[int(np.argmax(slot_ratio[sel]))]
            rr = float(slot_ratio[sel].max())
            add(sev, code, f"slot or pocket {gp[k]:.1f} mm wide and {rr * gp[k]:.1f} mm deep ({rr:.1f}:1) at {G.xyz(sm.pts[k] + sm.nrm[k] * gp[k] / 2)}; "
                f"beyond {lim(rid):g}:1 " + ("no end mill reaches the bottom." if sev == "error" else "the cutter is long and slender: slow, chatter, taper."),
                rule=rid, value=rr, at=[G.xyz(sm.pts[i] + sm.nrm[i] * gp[i] / 2) for i in idx[G.spread(sm.pts[idx], -slot_ratio[sel], k=6)]],
                hint="Widen the slot, make it shallower, or open one end so a larger cutter can come in from the side.")
            if sev == "error":
                break
            slot_ratio = np.where(slot_ratio > lim("cnc.pocket_depth_limit"), 0, slot_ratio)
    if np.isfinite(gp).any():
        row["narrowest_gap_mm"] = round(float(gp[np.isfinite(gp)].min()), 2)
    if tool_limits:
        row["min_tool_mm"] = round(min(tool_limits), 2)

    # ------------------------------------------------------------------ reach: set-ups and undercuts
    if not turned:
        # faces that are the outside of the stock need no cutter of their own
        pf = sm.pts @ frame.T
        nf = sm.nrm @ frame.T
        skin = np.zeros(len(sm.pts), dtype=bool)
        for k in ([plate["k"]] if plate else range(3)):     # plate stock gives two finished faces, a sawn block six
            skin |= (nf[:, k] > 0.98) & (np.abs(pf[:, k] - hi[k]) < 0.05)
            skin |= (nf[:, k] < -0.98) & (np.abs(pf[:, k] - lo[k]) < 0.05)
        feat = ~hole_mask & ~skin
        names = list(axes)
        reach = np.zeros((len(sm.pts), 6), dtype=bool)
        for j, nm in enumerate(names):
            d = axes[nm]
            reach[:, j] = (sm.nrm @ d > -0.02) & G.clear_along(sm, d)
        none = feat & ~reach.any(axis=1)
        frac = float(sm.w[none].sum() / max(sm.w.sum(), 1e-9))
        row["unreachable_fraction"] = round(frac, 3)
        feats: list[set] = []
        blocked_holes = []
        for h in holes:
            nm_p, nm_n = _dir_name(axes, h.axis), _dir_name(axes, -h.axis)
            if nm_p is None and nm_n is None:
                continue                                  # an angled hole: reported with the angled faces
            ok = set()
            for s_ in h.open_dirs:
                ok.add(_dir_name(axes, s_ * h.axis))
            ok.discard(None)
            if h.steps and len(ok) == 2:
                pass                                      # a counterbore fixes the side, but not knowable cheaply: either
            if ok:
                feats.append(ok)
            else:
                blocked_holes.append(h)
        for tp in tapped:
            nm = _dir_name(axes, -tp["dir"])
            if nm:
                feats.append({nm} if tp["beyond_tip"] > 0.3 else {nm, _dir_name(axes, tp["dir"])} - {None})
        for e in made:
            ok = {_dir_name(axes, nd) for nd in e["reach"]} - {None}
            if ok:
                feats.append(ok)
        if frac > lim("cnc.unreachable_fraction") or blocked_holes:
            pts = sm.pts[none]
            sel = G.spread(pts, -sm.w[none], k=6, min_sep=6.0) if len(pts) else []
            at = [G.xyz(pts[i]) for i in sel] + [G.xyz(h.origin) for h in blocked_holes[:3]]
            add("error", "feature_unreachable",
                f"{frac:.0%} of the surface ({sm.w[none].sum():.0f} mm²)" + (f" and {len(blocked_holes)} hole(s)" if blocked_holes else "")
                + f" cannot be reached by a straight cutter from any of the part's six sides (first at {at[0]}): an undercut or an internal face.",
                rule="cnc.unreachable_fraction", value=frac, at=at,
                hint="Open the feature to one side, split the part there, or call out a T-slot / keyseat cutter and expect to pay for it.")
        # fewest directions that reach everything reachable
        w = sm.w.copy()
        left = feat & reach.any(axis=1)
        chosen = []
        fl = [set(x) for x in feats]
        total = float(w[left].sum()) + 1e-9
        while True:
            gain = [float(w[left & reach[:, j]].sum()) / total + sum(1 for x in fl if names[j] in x) + (0.001 if names[j] == "+Z" else 0) for j in range(6)]
            j = int(np.argmax(gain))
            if gain[j] < 0.004 and not any(names[j] in x for x in fl):
                break
            chosen.append(names[j])
            left &= ~reach[:, j]
            fl = [x for x in fl if names[j] not in x]
            if len(chosen) == 6:
                break
        setups = max(1, len(chosen))
        row.update({"cut_from": sorted(chosen), "setups_estimate": setups})
        if side and plate:
            e = side[0]
            frm = sorted({_dir_name(axes, nd) or "an angle" for q in side for nd in q["reach"]})
            add("warning", "sharp_corner_side_milled",
                f"{len(side)} square inside corner(s) between two walls with no radius (first at {e['at']}): a cutter working down the plate's "
                f"{row['tool_axis']} axis leaves its own radius there, so they can only be squared up from the side ({', '.join(frm)}), an extra set-up.",
                rule="cnc.corner_radius_min_mm", value=0.0, at=[q["at"] for q in side[:6]],
                hint="Give them a radius of 1.5 mm or more and they are cut in the same set-up as the rest, or dog-bone them.")
        if setups > lim("cnc.setups_max"):
            add("warning", "many_setups", f"must be cut from {setups} directions ({', '.join(sorted(chosen))}); that is {setups} set-ups on a 3-axis mill.",
                rule="cnc.setups_max", value=setups,
                hint="Make it from two or three plates bolted together, or print it if loads allow.")

    # ------------------------------------------------------------------ rough time and cost
    mrr, usd_kg = MACHINING.get(c.material) or MACHINING["*plastic" if plastic else "*"]
    rho = MATERIALS[c.material].density if c.material in MATERIALS else 2700.0
    chips_cm3 = max(stock_vol - float(shape.volume), 0.0) / 1000.0
    setups = row.get("setups_estimate", 1)
    cut_min = chips_cm3 / mrr + float(sm.mesh.area) / 100.0 * 0.4 / (4.0 if c.material.startswith("al") or plastic else 1.0) \
        + 0.3 * len(holes) + 0.6 * len(tapped)
    setup_min = SETUP_MIN * setups
    stock_usd = stock_vol * 1e-9 * rho * usd_kg
    row["estimate"] = {"machining_min": round(cut_min, 1), "setup_min": round(setup_min, 0),
                       "stock_usd": round(stock_usd, 2),
                       "cost_usd_each_qty1": round((cut_min + setup_min + PROGRAM_MIN) / 60 * SHOP_RATE_USD_H + stock_usd, 0),
                       "cost_usd_each_qty10": round((cut_min + (setup_min + PROGRAM_MIN) / 10) / 60 * SHOP_RATE_USD_H + stock_usd, 0),
                       "basis": f"estimate, not a quote: {mrr:g} cm3/min roughing, {SETUP_MIN:g} min per set-up, {PROGRAM_MIN:g} min programming, "
                                f"${SHOP_RATE_USD_H:g}/h, stock ${usd_kg:g}/kg"}
    drivers = []
    if setups > 2:
        drivers.append(f"{setups} set-ups")
    if removed > 0.7 and not turned:
        drivers.append(f"{removed:.0%} of the stock removed")
    if row.get("min_tool_mm", 99) < 3.0:
        drivers.append(f"{row['min_tool_mm']:g} mm cutter needed")
    if len(tapped) > 4:
        drivers.append(f"{len(tapped)} tapped holes")
    if row.get("form") == "plate" and "non_stock" in " ".join(f.code for f in r.findings if f.data.get("part") == name):
        drivers.append("non-stock thickness")
    row["cost_drivers"] = drivers
    return row
