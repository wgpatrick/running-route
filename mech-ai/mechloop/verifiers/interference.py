"""Static assembly checks: interference, required clearances, floating parts."""
from __future__ import annotations

from itertools import combinations

from ..geom import bboxes_overlap, overlap_volume
from ..model import Design
from ..report import VerifierResult, timed

VOL_TOL = 0.5  # mm^3: below this an overlap is treated as touching
TOUCH_TOL = 0.02  # mm: parts closer than this are "in contact"


def verify_interference(design: Design) -> VerifierResult:
    r = VerifierResult("interference")
    with timed(r):
        comps = design.components
        contacts: dict[str, set[str]] = {c.name: set() for c in comps}
        n_pairs = n_exact = 0
        worst = 0.0
        for a, b in combinations(comps, 2):
            n_pairs += 1
            key = frozenset((a.name, b.name))
            need_gap = design.min_clearances.get(key)
            margin = max(TOUCH_TOL, need_gap or 0.0)
            if not bboxes_overlap(a.shape, b.shape, margin):
                continue
            n_exact += 1
            vol, where = overlap_volume(a.shape, b.shape)
            allowed = design.allowed_overlaps.get(key)
            if vol > VOL_TOL:
                contacts[a.name].add(b.name)
                contacts[b.name].add(a.name)
                if allowed is None or vol > allowed:
                    worst = max(worst, vol)
                    r.add("error", "interference",
                          f"{a.name} and {b.name} overlap by {vol:.1f} mm^3 near {where}.",
                          parts=[a.name, b.name], volume_mm3=round(vol, 2), at=where,
                          hint="Move/resize one part, add a pocket or hole, or declare allow_overlap for a real thread/press fit.")
                continue
            try:
                gap = a.shape.distance_to(b.shape)
            except Exception:
                gap = None
            if gap is not None and gap <= TOUCH_TOL:
                contacts[a.name].add(b.name)
                contacts[b.name].add(a.name)
            if need_gap is not None and gap is not None and gap < need_gap - 1e-6:
                r.add("error", "clearance",
                      f"{a.name} to {b.name} gap is {gap:.2f} mm, need >= {need_gap:.2f} mm.",
                      parts=[a.name, b.name], gap_mm=round(gap, 3), required_mm=need_gap)
        # Floating parts: within each rigid body every part must touch the rest of that body.
        for body, members in design.bodies().items():
            if len(members) < 2:
                continue
            names = {m.name for m in members}
            seen, stack = set(), [members[0].name]
            while stack:
                n = stack.pop()
                if n in seen:
                    continue
                seen.add(n)
                stack.extend((contacts[n] & names) - seen)
            # choose the largest connected group as the reference
            groups, left = [seen], names - seen
            while left:
                g, stack = set(), [next(iter(left))]
                while stack:
                    n = stack.pop()
                    if n in g:
                        continue
                    g.add(n)
                    stack.extend((contacts[n] & names) - g)
                groups.append(g)
                left -= g
            if len(groups) > 1:
                groups.sort(key=len, reverse=True)
                groups = groups[:1] + _not_free_standing(design, body, groups, r, "floating_parts")
                for g in groups[1:]:
                    r.add("error", "floating_parts",
                          f"In body '{body}', {sorted(g)} do not touch the rest of the body "
                          f"(nothing holds them in place).",
                          body=body, parts=sorted(g),
                          hint="Parts in one rigid body must be in contact (bolted, seated or bonded). Close the gap or add the connecting part.")
        _fastening(design, contacts, r)
        _threads(design, r)
        tsl = _tslot_screws(design, r)
        cpl = _coupler_insertion(design, r)
        r.metrics = {**({"coupler_shaft_insertion": cpl} if cpl else {}), **({"tslot_screws": tsl} if tsl else {}), "pairs": n_pairs, "pairs_checked_exactly": n_exact,
                     "worst_overlap_mm3": round(worst, 2),
                     "contact_pairs": sum(len(v) for v in contacts.values()) // 2}
    return r


def _not_free_standing(design: Design, body: str, groups: list, r, what: str) -> list:
    """Of the connected groups of a body (largest first), those that are still a fault once declared free-standing
    units (design.free_standing) are taken out. A unit is accepted only on the fixed world, only as ONE connected
    group (a unit whose own parts fall apart is still reported), and only if every part of the group other than
    screws and nuts is listed in it. The reference group (groups[0]) may itself be a unit; it is never returned."""
    units = {k: set(v) for k, v in (getattr(design, "free_standing", None) or {}).items()}
    if not units:
        return groups[1:]
    hardware = {f.name for f in design.fasteners} | {c.name for c in design.components if (c.sku or "").startswith(("SHCS", "NUT"))}
    known = {c.name for c in design.components}
    if r is not None:
        for k, v in units.items():
            for n in sorted(v - known):
                r.add("error", "unknown_part_reference", f"Free-standing unit '{k}' lists '{n}', which is not a part.", name=n)
    used = set()

    def unit_of(g):
        core = g - hardware
        return next((k for k, v in units.items() if core and core <= v), None)

    u0 = unit_of(groups[0])
    if u0:
        used.add(u0)
    bad = []
    for g in groups[1:]:
        u = unit_of(g)
        if body == "world" and u is not None and u not in used:
            used.add(u)
            continue
        bad.append(g)
    return bad


def _fastening(design: Design, contacts: dict[str, set[str]], r: VerifierResult) -> None:
    """Touching is not holding. Within each rigid body, every part must be tied to
    the rest by a fastener it touches or by a declared joint (design.join)."""
    fasteners = {f.name for f in design.fasteners}
    if not fasteners and not design.joins:
        r.add("info", "fastening_not_checked",
              "No fasteners or joins declared, so how parts are held together was not checked.")
        return
    known = {c.name for c in design.components}
    for pair in list(design.joins) + list(design.allowed_overlaps) + list(design.min_clearances):
        for n in pair:
            if n not in known:
                r.add("error", "unknown_part_reference", f"A join/overlap/clearance refers to '{n}', which is not a part.",
                      name=n)
    for body, members in design.bodies().items():
        names = {m.name for m in members}
        if len(names - fasteners) < 2:
            continue
        adj: dict[str, set[str]] = {n: set() for n in names}
        for fn in fasteners & names:
            for other in contacts[fn] & names:
                adj[fn].add(other)
                adj[other].add(fn)
        for f in design.fasteners:  # parts a screw is declared to clamp (it may pass through clearance holes)
            if f.name in names:
                for other in set(f.clamps) & names:
                    adj[f.name].add(other)
                    adj[other].add(f.name)
        for pair in design.joins:
            if len(pair) != 2:
                continue
            a, b = tuple(pair)
            if a in names and b in names:
                adj[a].add(b)
                adj[b].add(a)
        groups, left = [], set(names)
        while left:
            g, stack = set(), [next(iter(left))]
            while stack:
                n = stack.pop()
                if n in g:
                    continue
                g.add(n)
                stack.extend(adj[n] - g)
            groups.append(g)
            left -= g
        groups = [g for g in groups if g - fasteners]
        if len(groups) > 1:
            groups.sort(key=lambda g: -sum(design.get(n).mass() for n in g))
            groups = groups[:1] + _not_free_standing(design, body, groups, None, "unfastened")
            for g in groups[1:]:
                parts = sorted(g - fasteners)
                touching = sorted({t for n in parts for t in contacts[n] & names} - g)
                r.add("error", "unfastened",
                      f"In body '{body}', {parts} {'is' if len(parts) == 1 else 'are'} not fastened to the rest "
                      f"(only resting against {touching or 'nothing'}).",
                      body=body, parts=parts, touching=touching,
                      hint="Add screws that pass through/into both parts (parts.add_screw), or declare the "
                           "real joint with design.join(a, b, kind) for a press fit, bond, clamp or set screw.")


STANDARD_LENGTHS_MM = (3, 4, 5, 6, 8, 10, 12, 16, 20, 25, 30, 35, 40, 45, 50, 55, 60)      # ISO 4762 preferred lengths

THREAD_FACTOR = {"steel": 1.0, "stainless304": 1.0, "brass": 1.0, "al6061": 1.5,  # x thread diameter; plastics 2.0
                 # soft aluminium (practice rule FST-010, Bossard's engagement table: AlMg3 F18 2 d): cast tooling plate,
                 # 5052 sheet; 6061 / 6082 sits just under Bossard's AlMgSi1 F32 row (1.4 d): error below 1.5 d
                 "al_mic6": 2.0, "al_atp5": 2.0, "al5052": 2.0}
# FST-010: in 6061 an engagement between 1.5 d and 2 d is a WARNING (load-bearing or often-removed joints; Bossard's
# trials cover M6-M16 only). A 2020 T-slot extrusion's end tap is in 6063, soft aluminium: 2 d (the extrusion alloy is not
# in the vendor record: the 6063 mapping is ours, DERIVED).
THREAD_WARN_FACTOR = {"al6061": 2.0}
EXTRUSION_TAP_FACTOR = 2.0


def _threads(design: Design, r: VerifierResult) -> None:
    """Each screw must engage enough thread in the part it screws into."""
    import numpy as np

    comps = {c.name: c for c in design.components}
    axis_of = {f.name: np.array(f.axis, dtype=float) for f in design.fasteners}
    short = 0
    marginal = []
    for c in design.components:
        d = c.meta.get("thread_d")
        if not d or c.meta.get("tnut") or c.name not in axis_of:
            continue
        a = axis_of[c.name] / np.linalg.norm(axis_of[c.name])
        for tgt in c.meta.get("threads_into", []):
            if tgt not in comps:
                continue
            try:
                common = c.shape.intersect(comps[tgt].shape)
            except Exception:
                common = None
            eng = 0.0
            items = common if isinstance(common, (list, tuple)) else ([common] if common is not None else [])
            for it in items:
                try:
                    bb = it.bounding_box()
                except Exception:
                    continue
                corners = np.array([[x, y, z] for x in (bb.min.X, bb.max.X) for y in (bb.min.Y, bb.max.Y)
                                    for z in (bb.min.Z, bb.max.Z)])
                pr = corners @ a
                eng = max(eng, float(pr.max() - pr.min()))
            tsku = comps[tgt].sku or ""
            soft_ext = tsku.startswith("EXT20")
            need = (EXTRUSION_TAP_FACTOR if soft_ext else THREAD_FACTOR.get(comps[tgt].material, 2.0)) * d
            warn_need = None if soft_ext else (THREAD_WARN_FACTOR.get(comps[tgt].material, 0.0) * d or None)
            if tsku.startswith("NUT-"):  # a standard nut is full strength once the screw passes through it
                need = comps[tgt].meta.get("interfaces", {}).get("height", d * 0.8)
            depth = comps[tgt].meta.get("interfaces", {}).get("thread_depth")
            fits = None
            if depth is not None:  # a catalog part's own tapped hole: using its full depth is what the vendor intends
                need = min(need, depth - 0.3)
                # The vendor's depth is a MAXIMUM penetration, not a requirement. Screws come in standard lengths, so
                # through a given stack only some engagements exist. If no standard length reaches `need` without
                # bottoming out, the longest one that stays inside the hole is what the vendor's own screw does
                # (Mean Well "4-M4 L=3mm" through a 4 mm panel: M4 x 6 gives 2.0 mm, M4 x 8 would give 4.0): accept
                # it, down to half a diameter of thread (2 to 3 turns), below which the stack must change.
                sb_ = c.shape.bounding_box()
                length = float(abs(np.array([sb_.size.X, sb_.size.Y, sb_.size.Z]) @ np.abs(a))) - float(c.meta.get("interfaces", {}).get("head_h", 0.0))
                grip = length - eng                      # what the screw passes through before the thread starts
                fits = [L - grip for L in STANDARD_LENGTHS_MM if 0.0 < L - grip <= depth + 0.05]
                if fits and max(fits) < need - 0.05:
                    need = max(max(fits), 0.5 * d)
            if depth is not None and eng > depth + 0.05:
                r.add("error", "thread_bottoms_out",
                      f"{c.name} goes {eng:.1f} mm into {tgt}, whose tapped holes are only {depth:.1f} mm deep.",
                      screw=c.name, into=tgt, engagement_mm=round(eng, 2), depth_mm=depth,
                      hint="Use a shorter screw or a thicker part under the head.")
            if eng < need - 0.05:
                short += 1
                what = ("6063 extrusion end tap (soft aluminium, mapping DERIVED)" if soft_ext else comps[tgt].material)
                r.add("error", "thread_engagement",
                      f"{c.name} engages only {eng:.1f} mm of thread in {tgt} ({what}); "
                      f"an M{d:g} needs >= {need:.1f} mm there (FST-010, Bossard engagement table).",
                      screw=c.name, into=tgt, engagement_mm=round(eng, 2), required_mm=round(need, 2), rule="FST-010",
                      hint="Use a longer screw, thicken the tapped part, or use a nut / threaded insert.")
            elif warn_need and depth is None and not tsku.startswith("NUT-") and eng < warn_need - 0.05:
                marginal.append({"screw": c.name, "into": tgt, "engagement_mm": round(eng, 2), "d": d, "ratio": round(eng / d, 2)})

    if marginal:
        w = min(marginal, key=lambda x: x["ratio"])
        r.add("warning", "thread_engagement_marginal",
              f"{len(marginal)} screw(s) engage between 1.5 d and 2 d in 6061 aluminium (least: {w['screw']} in {w['into']}, "
              f"{w['engagement_mm']:.1f} mm = {w['ratio']:.2f} d). Enough for a static joint; on a load-bearing or often-removed joint "
              f"FST-010 asks 2 d (Bossard: 6061 is just under the AlMgSi1 F32 row; the trials cover M6-M16 only).",
              screws=[x["screw"] for x in marginal][:60], least=w, count=len(marginal), rule="FST-010",
              hint="A longer screw where the joint carries load or is opened often; a nut or insert otherwise.")


TNUT_ENGAGEMENT_FULL_D = 0.8        # thread in a T-nut, x d: the height of an ISO 4032 hex nut (0.8 to 0.94 d). No finding
TNUT_ENGAGEMENT_MIN_D = 0.5         # ISO 4035 thin nut (about 0.5 d; recalled): below this an error, between the two a warning
SLOT_BOTTOM_MARGIN_MM = 0.5         # kept between a screw's tip and the slot floor (screw length js15, washer, sheet: DERIVED)


def _tslot_screws(design: Design, r: VerifierResult) -> dict:
    """Screws into T-nuts in a 2020 extrusion's slot (add_screw(..., tnut=True), corner-bracket legs).

    In a design with `design.tnut_style` set, every such screw has a drawn T-nut and is judged against the slot's real
    section (the extrusion's interfaces["slot"]; the simulation solid's slot is plainer and shallower) and the T-nut's
    own dimensions, both of which are STAND-IN data today (mechloop/parts/tslot.py):

      tnut_missing / tnut_misplaced / tnut_does_not_fit   the nut is a part, sits under the lips on the screw's axis,
                               passes the slot opening (drop-in), fits the cavity and stays inside the extrusion's length
      screw_off_slot_centre    the screw's axis is not on the slot's centre line
      screw_bottoms_in_slot    (error) the tip comes within SLOT_BOTTOM_MARGIN_MM of the slot floor: the screw would stop on
                               the floor before the joint is clamped
      tnut_thread_engagement   (error) under 0.5 d of thread in the nut; counted only in the nut's body under the lips
      tnut_thread_engagement_marginal  (one grouped warning) 0.5 d to 0.8 d
      tslot_profile_sensitive  (one grouped warning) screws that pass on the profile used but would bottom or fall under
                               0.5 d on the alternative slot section on file
      tnut_needs_end_loading   (warning) a nut that is not a drop-in type

    The 0.5 d / 0.8 d limits are ours (standard thin and full nut heights), not a T-nut maker's: the design guidelines ask
    1 d in steel, which no 2020 T-nut reaches, so under 0.5 d is the error and the band below a full nut's height is a
    warning. In a design without `tnut_style` the T-nuts are not parts and nothing can be judged: one info says so."""
    import numpy as np

    from ..parts.tslot import assumed_dimensions, slot_frame

    comps = {c.name: c for c in design.components}
    fast = {f.name: f for f in design.fasteners}
    screws = [c for c in design.components if c.meta.get("tnut") and c.name in fast]
    if not screws:
        return {}
    if not getattr(design, "tnut_style", None):
        r.add("info", "tslot_screws_not_checked",
              f"{len(screws)} screw(s) go into T-nuts that are BOM lines, not parts (design.tnut_style is not set): their length "
              f"against the slot floor and their thread in the nut were not checked.", count=len(screws))
        return {"checked": False, "screws": len(screws)}
    rows, marginal, sensitive, n_err = [], [], {}, 0
    verdicts = {"used": {"bottoms": [], "short": [], "thin": [], "full": []}}
    for c in screws:
        f = fast[c.name]
        a = np.array(f.axis, dtype=float)
        a /= np.linalg.norm(a)
        itf = c.meta.get("interfaces") or {}
        d = float(c.meta.get("thread_d") or itf.get("thread_d"))
        try:
            L = float((c.sku or "").split("x")[-1])
        except ValueError:
            continue
        under = np.array(f.head_center, dtype=float) - a * float(itf.get("head_h", 0.0))
        ext = next((comps[t] for t in c.meta.get("threads_into", []) if t in comps and "slot" in (comps[t].meta.get("interfaces") or {})), None)
        fr = slot_frame(ext, under, -a) if ext is not None else None
        if fr is None:
            n_err += 1
            r.add("error", "tnut_screw_not_in_a_slot", f"{c.name} is declared tnut=True but does not point square into a slot face of a "
                  f"slotted extrusion it threads into ({c.meta.get('threads_into')}).", screw=c.name)
            continue
        slot = ext.meta["interfaces"]["slot"]
        grip, p = -fr["depth"], fr["depth"] + L               # under the head to the extrusion's face; tip below the face
        row = {"screw": c.name, "sku": c.sku, "into": ext.name, "grip_mm": round(grip, 3), "depth_in_slot_mm": round(p, 3)}
        if abs(fr["offset"]) > 0.3:
            n_err += 1
            r.add("error", "screw_off_slot_centre", f"{c.name} is {abs(fr['offset']):.2f} mm off the centre line of the slot of {ext.name}.",
                  screw=c.name, into=ext.name, offset_mm=round(fr["offset"], 3), hint="Put the hole on the slot's centre line.")
        tn = comps.get(c.meta.get("tnut_part") or "")
        if tn is None:
            n_err += 1
            r.add("error", "tnut_missing", f"{c.name} threads into a T-nut in {ext.name}, but no T-nut part is drawn for it.",
                  screw=c.name, into=ext.name, hint="add_screw(..., tnut=True) draws it when design.tnut_style is set before the screw is added.")
            rows.append(row)
            continue
        ti = tn.meta.get("interfaces") or {}
        row["tnut"] = tn.name
        body_h, thread_len = float(ti.get("body_height", 0.0)), float(ti.get("thread_length", 0.0))
        P = np.array(tn.meta["placement"], dtype=float)
        tfr = slot_frame(ext, P[:, 3], -P[:, 2])
        off_axis = float(np.linalg.norm(np.cross(P[:, 3] - under, a)))
        if tfr is None or abs(tfr["depth"] - slot["lip"]) > 0.05 or off_axis > 0.05 or float(P[:, 2] @ fr["normal"]) < 0.999:
            n_err += 1
            r.add("error", "tnut_misplaced",
                  f"{tn.name} is not seated under the lips of the slot of {ext.name} on the axis of {c.name} "
                  f"(bearing face {('%.2f' % tfr['depth']) if tfr else '?'} mm below the face, lips {slot['lip']:g} mm; {off_axis:.2f} mm off the axis).",
                  tnut=tn.name, screw=c.name, into=ext.name)
        problems = []
        if ti.get("insertion") == "drop-in" and float(ti.get("width", 0.0)) > slot["opening"] + 1e-6:
            problems.append(f"{ti.get('width')} mm wide: does not pass the {slot['opening']:g} mm opening")
        if float(ti.get("span", 0.0)) > slot["cavity_width"] + 1e-6:
            problems.append(f"{ti.get('span')} mm across: wider than the {slot['cavity_width']:g} mm cavity")
        if slot["lip"] + body_h > slot["depth"] + 1e-6:
            problems.append(f"body {body_h:g} mm under a {slot['lip']:g} mm lip: deeper than the {slot['depth']:g} mm slot")
        if float(ti.get("neck", 0.0)) > slot["lip"] + 1e-6:
            problems.append(f"neck {ti.get('neck')} mm stands proud of the {slot['lip']:g} mm lip")
        if tfr is not None and abs(tfr["along_mm"]) + float(ti.get("width", 0.0)) / 2 > tfr["half_length"] + 1e-6:
            problems.append("hangs out of the end of the extrusion")
        if problems:
            n_err += 1
            r.add("error", "tnut_does_not_fit", f"{tn.name} does not fit the slot of {ext.name}: " + "; ".join(problems) + ".",
                  tnut=tn.name, into=ext.name, problems=problems)
        if ti.get("insertion") != "drop-in":
            r.add("warning", "tnut_needs_end_loading",
                  f"{tn.name} is not a drop-in T-nut: it has to be slid into the slot of {ext.name} from an open end before that end is closed.",
                  tnut=tn.name, into=ext.name)

        size = f"M{d:g}"
        # where the nut's thread starts and how long it is come from the T-nut part and the slot (data, not constants)
        thr_start = slot["lip"] + float(ti.get("thread_offset", 0.0))

        def judge(start, length, depth, p_=p):
            return max(0.0, min(p_, start + length) - start), depth - p_

        eng, clear = judge(thr_start, thread_len, slot["depth"])
        row.update(engagement_mm=round(eng, 3), engagement_d=round(eng / d, 3), tip_to_floor_mm=round(clear, 3))
        # what the standard lengths would do through the same grip, for the hint
        fits = []
        for Ls in STANDARD_LENGTHS_MM:
            e_, c_ = judge(thr_start, thread_len, slot["depth"], Ls - grip)
            if c_ >= SLOT_BOTTOM_MARGIN_MM - 1e-6 and e_ >= TNUT_ENGAGEMENT_MIN_D * d - 1e-6:
                fits.append((Ls, round(e_, 2)))
        best = max(fits, key=lambda x: x[1]) if fits else None
        row["standard_lengths_that_fit"] = [x[0] for x in fits]
        how = (f"{size} x {best[0]:g} through the same stack gives {best[1]:.1f} mm of thread and stays {slot['depth'] - (best[0] - grip):.1f} mm off the floor."
               if best else f"No standard length works through a {grip:.2f} mm stack: change the stack (one washer more or less, or the plate) so that "
                            f"a standard length ends {thr_start + TNUT_ENGAGEMENT_MIN_D * d:.1f} to {slot['depth'] - SLOT_BOTTOM_MARGIN_MM:.1f} mm below the extrusion's face.")
        bad = False
        if clear < SLOT_BOTTOM_MARGIN_MM - 1e-6:
            bad = True
            n_err += 1
            what = (f"reaches the slot floor {-clear:.2f} mm before the joint is clamped" if clear < 0 else
                    f"ends {clear:.2f} mm from the slot floor (at least {SLOT_BOTTOM_MARGIN_MM:g} mm is kept for length and thickness tolerances)")
            r.add("error", "screw_bottoms_in_slot",
                  f"{c.name} ({c.sku}) goes {p:.2f} mm into the slot of {ext.name} through a {grip:.2f} mm stack; the slot is "
                  f"{slot['depth']:g} mm deep, so it {what}.",
                  screw=c.name, into=ext.name, depth_in_slot_mm=round(p, 3), slot_depth_mm=slot["depth"], tip_to_floor_mm=round(clear, 3),
                  grip_mm=round(grip, 3), hint=how)
        if eng < TNUT_ENGAGEMENT_MIN_D * d - 1e-6:
            bad = True
            n_err += 1
            r.add("error", "tnut_thread_engagement",
                  f"{c.name} ({c.sku}) has only {eng:.2f} mm of thread ({eng / d:.2f} d) in its T-nut in {ext.name}: it ends {p:.2f} mm "
                  f"below the face and the nut's thread starts {thr_start:g} mm below it. At least {TNUT_ENGAGEMENT_MIN_D:g} d "
                  f"({TNUT_ENGAGEMENT_MIN_D * d:.1f} mm) is needed.",
                  screw=c.name, into=ext.name, engagement_mm=round(eng, 3), required_mm=TNUT_ENGAGEMENT_MIN_D * d, grip_mm=round(grip, 3), hint=how)
        elif eng < TNUT_ENGAGEMENT_FULL_D * d - 1e-6:
            marginal.append({"screw": c.name, "engagement_mm": round(eng, 2), "d": round(eng / d, 2)})
        verdicts["used"]["bottoms" if clear < SLOT_BOTTOM_MARGIN_MM - 1e-6 else "short" if eng < TNUT_ENGAGEMENT_MIN_D * d - 1e-6
                         else "thin" if eng < TNUT_ENGAGEMENT_FULL_D * d - 1e-6 else "full"].append(c.name)
        row["alternatives"] = {}
        for g in slot.get("alternatives") or []:
            tg = (g.get("tnut") or {}).get(size)
            if tg is None:
                continue
            e2, c2 = judge(tg["thread_start"], tg["thread_length"], g["depth"])
            row["alternatives"][g["name"]] = {"engagement_mm": round(e2, 3), "tip_to_floor_mm": round(c2, 3)}
            v = verdicts.setdefault(g["name"], {"bottoms": [], "short": [], "thin": [], "full": []})
            kind = ("bottoms" if c2 < SLOT_BOTTOM_MARGIN_MM - 1e-6 else "short" if e2 < TNUT_ENGAGEMENT_MIN_D * d - 1e-6
                    else "thin" if e2 < TNUT_ENGAGEMENT_FULL_D * d - 1e-6 else "full")
            v[kind].append(c.name)
            if not bad and kind in ("bottoms", "short"):
                sensitive.setdefault(g["name"], []).append({"screw": c.name, "tip_to_floor_mm": round(c2, 2), "engagement_mm": round(e2, 2),
                                                           "engagement_d": round(e2 / d, 2), "why": kind})
        rows.append(row)
    slot_any = next((c.meta["interfaces"]["slot"] for c in design.components if "slot" in (c.meta.get("interfaces") or {})), {})
    if marginal:
        w = min(marginal, key=lambda x: x["d"])
        r.add("warning", "tnut_thread_engagement_marginal",
              f"{len(marginal)} screw(s) have between {TNUT_ENGAGEMENT_MIN_D:g} d and {TNUT_ENGAGEMENT_FULL_D:g} d of thread in their T-nut "
              f"(least: {w['screw']}, {w['engagement_mm']:.2f} mm = {w['d']:.2f} d). That is a thin nut's thread, not a full nut's: "
              f"tighten to a reduced torque. With a {slot_any['lip']:g} mm lip and a {slot_any['depth']:g} mm deep slot the most any screw can "
              f"have without coming within {SLOT_BOTTOM_MARGIN_MM:g} mm of the floor is {slot_any['depth'] - SLOT_BOTTOM_MARGIN_MM - slot_any['lip']:.1f} mm, "
              f"so an M5 cannot reach {TNUT_ENGAGEMENT_FULL_D:g} d in this slot. Slot and T-nut dimensions are assumed (stand-in data).",
              screws=[x["screw"] for x in marginal][:200], least=w, count=len(marginal),
              hint="State a reduced tightening torque for these joints, or confirm the bought T-nut's thread length and the slot's lip.")
    for g in slot_any.get("alternatives") or []:
        lst = sensitive.get(g["name"])
        if not lst:
            continue
        w = min(lst, key=lambda x: (x["why"] != "bottoms", x["tip_to_floor_mm"] if x["why"] == "bottoms" else x["engagement_d"]))
        nb, ns = sum(x["why"] == "bottoms" for x in lst), sum(x["why"] == "short" for x in lst)
        r.add(g.get("report_as", "warning"), "tslot_profile_sensitive",
              f"{len(lst)} screw(s) pass on the slot and T-nut geometry used but not on '{g['name']}' (slot {g['depth']:g} mm deep, lip "
              f"{g['lip']:g} mm): {nb} would end within {SLOT_BOTTOM_MARGIN_MM:g} mm of that floor or on it, {ns} would have under "
              f"{TNUT_ENGAGEMENT_MIN_D:g} d of thread; worst: {w['screw']} ({w['tip_to_floor_mm']:.2f} mm from the floor, {w['engagement_d']:.2f} d). "
              f"Measure what is bought before fitting these.",
              screws=[x["screw"] for x in lst][:200], count=len(lst), bottoms=nb, short=ns, geometry=g["name"], status=g.get("status"),
              hint="Put the bought extrusion's and T-nut's figures in mechloop/parts/vendor/tslot_2020_hardware.json and run verify again.")
    slot0 = next((c.meta["interfaces"]["slot"] for c in design.components if "slot" in (c.meta.get("interfaces") or {})), {})
    types = sorted({(comps[x["tnut"]].meta.get("interfaces") or {}).get("insertion", "?") for x in rows if x.get("tnut")})
    return {"checked": True, "screws": len(screws), "tnuts_drawn": sum(1 for x in rows if x.get("tnut")), "tnut_types": types,
            "errors": n_err, "marginal_engagement": len(marginal),
            "profile_sensitive": {k: len(v) for k, v in sensitive.items()},
            # every screw judged on every geometry on file: counts, and the screws that would bottom or be short
            "verdicts_by_geometry": {k: {"bottoms": len(v["bottoms"]), "short": len(v["short"]), "thin_nut_thread": len(v["thin"]),
                                         "full_nut_thread": len(v["full"]), "bottoming_screws": v["bottoms"][:200], "short_screws": v["short"][:200]}
                                     for k, v in verdicts.items()},
            "limits": {"bottom_margin_mm": SLOT_BOTTOM_MARGIN_MM, "engagement_min_d": TNUT_ENGAGEMENT_MIN_D, "engagement_full_d": TNUT_ENGAGEMENT_FULL_D},
            "slot": {k: v for k, v in slot0.items() if k != "alternatives"}, "slot_alternatives": slot0.get("alternatives"),
            "assumed_dimensions": assumed_dimensions(), "rows": rows}


def _coupler_insertion(design: Design, r: VerifierResult) -> dict:
    """How far each shaft goes into a coupler, against how far a shaft of that size can go (`max_insertion_a` /
    `max_insertion_b` of the catalogue coupler: where it would meet the elastomer spider). Measured as the reach, along
    the coupler's axis from that end, of whatever other part lies on the axis inside the bore's diameter. A shaft drawn
    deeper also overlaps the coupler's solid (reported as `interference`); this finding gives the numbers, and holds
    even where an overlap was allowed."""
    import numpy as np
    from build123d import Cylinder, Pos

    from ..geom import location_from_matrix

    out: dict = {}
    for c in design.components:
        itf = c.meta.get("interfaces") or {}
        if "max_insertion_a" not in itf or not c.meta.get("placement"):
            continue
        P = np.vstack([np.array(c.meta["placement"], dtype=float), [0, 0, 0, 1]])
        o, z = P[:3, 3], P[:3, 2]
        L = float(itf["length"])
        loc = location_from_matrix(P)
        ends = (("a", float(itf["bore_a"]), float(itf["max_insertion_a"]), 1.0, 0.0),
                ("b", float(itf["bore_b"]), float(itf["max_insertion_b"]), -1.0, L))
        for end, bore, limit, sgn, z_end in ends:
            probe = (Pos(0, 0, L / 2) * Cylinder(bore / 2 - 0.05, L)).moved(loc)
            best = None
            for other in design.components:
                if other is c or other.body != c.body or (other.sku or "").startswith(("SHCS", "NUT")):
                    continue
                if not bboxes_overlap(other.shape, probe, 0.0):
                    continue
                try:
                    common = other.shape & probe
                except Exception:
                    continue
                sols = common.solids() if common is not None else []
                if not sols or sum(x.volume for x in sols) < VOL_TOL:
                    continue
                zs = []
                for so in sols:
                    bb = so.bounding_box()
                    for x in (bb.min.X, bb.max.X):
                        for y in (bb.min.Y, bb.max.Y):
                            for zz in (bb.min.Z, bb.max.Z):
                                zs.append(float((np.array([x, y, zz]) - o) @ z))
                # the part must enter from this end: it reaches the end face and the larger part of it is outside that end
                ob = other.shape.bounding_box()
                ctr = float((np.array([(ob.min.X + ob.max.X) / 2, (ob.min.Y + ob.max.Y) / 2, (ob.min.Z + ob.max.Z) / 2]) - o) @ z)
                if (sgn > 0 and (min(zs) > 0.3 or ctr > L / 2)) or (sgn < 0 and (max(zs) < L - 0.3 or ctr < L / 2)):
                    continue
                depth = (max(zs) - z_end) if sgn > 0 else (z_end - min(zs))
                if best is None or depth > best[1]:
                    best = (other.name, depth)
            if best is None:
                continue
            name, depth = best
            out[f"{c.name}:{end}"] = {"shaft": name, "bore_mm": bore, "insertion_mm": round(depth, 2), "max_insertion_mm": limit,
                                      **({"clamped_bore_depth_mm": itf["bore_depth"]} if "bore_depth" in itf else {})}
            if depth > limit + 0.05:
                r.add("error", "shaft_too_deep_in_coupler",
                      f"{name} is drawn {depth:.1f} mm into the {bore:g} mm bore of {c.name}, but a shaft of that size can enter "
                      f"only {limit:g} mm before it meets the coupler's elastomer spider: {depth - limit:.1f} mm too deep.",
                      shaft=name, coupler=c.name, insertion_mm=round(depth, 2), max_insertion_mm=limit,
                      too_deep_mm=round(depth - limit, 2),
                      hint=f"Move the shaft {depth - limit:.1f} mm out of the coupler (or the coupler and what drives it the other "
                           f"way). The hub clamps {itf.get('bore_depth', limit):g} mm of shaft.")
    return out
