"""How well is a printer's bed held? Measures that tell a cantilevered bed from a two-screw or three-point one.

The guide check in the ratings verifier ("tilt mode on the guide blocks") and a design's own payload case in the FEA
both assume ideal joints: blocks rigid on their rails, vertical load taken wherever the case fixes it. Neither says
what a hand on the front edge or a kilogram of print does at the print surface, nor what a screw that is not under the
mass centre asks of the guides. This module does, for any design that declares a printer bed (design.printer) whose Z
joint is driven by one or more lead screws.

1. THE BED AS A RIGID BODY ON ITS SUPPORTS (`support_model`). Every guide block or bearing tagged `guides=<z joint>` is
   a spring across its rail (maker's radial rigidity where the catalogue has it, e.g. Hiwin MGN12H 63 N/um at Z0;
   ratings.BLOCK_K assumed otherwise; the same figure is ASSUMED sideways, Hiwin publishes none) with a tilt stiffness
   from its ball-track length; it is free along the rail. Every lead-screw nut is a spring along its screw: the screw
   as a column (E A / free length) in series with NUT_AXIAL_K_ASSUMED for thread contact and the motor's bearings (no
   catalogue figure for either; backlash is not in it because the bed's weight keeps the nut seated; said in the
   metrics). The 6 x 6 stiffness of the body on those springs gives, for any load: deflection and tilt at the print
   surface, the force and moment on every block and nut, and whether the body is held at all (a mechanism is
   reported, not solved). It works unchanged for 1, 2, 3 or 4 screws and for rails or rods on one side or both.
2. FLEXURE OF ARMS AND PLATE (`flexure`, FEA). The parts that carry the bed, meshed together, held across the rail at
   the guide blocks and along the screw at the nut seat(s) (the real load path), loaded at the worst point of the
   print area. Solved twice, as every AssemblyCase is: all touching faces bonded, and screwed joints held only round
   their screws. The two figures bracket the bolted joints. Parts: design.printer["bed_support"] = {"parts": [...]},
   else those of the design's AssemblyCase that contains the bed and its guide blocks, plus what the nut sits in.
3. TOTAL at the print surface = flexure + support compliance (the FEA's supports are rigid, the springs' body is
   rigid, so the two add). Reported in mm at the worst point and as tilt across the print area, for
     (i)  a hand load, HAND_LOAD_N = 20 N, at the worst point of the print area;
     (ii) a print of PRINT_MASS_KG = 1 kg at the worst corner.
   `bed_sags_under_print_weight` (warning) when (ii) exceeds SAG_FRACTION_OF_LAYER = 0.1 of a layer (0.02 mm at the
   default 0.2 mm) on the screw-only bound: the bed is levelled and its mesh measured empty, so what the print's own
   weight moves it by is an error no adjustment or mesh sees, and a tenth of a layer is the first-layer height band
   a tuned machine holds (the same order as the 0.01 to 0.02 mm a probe repeats to). A judgement, stated as one.
   `bed_moves_under_hand_load` (warning) when (i) exceeds one layer: touching the bed then disturbs a paper or
   feeler-gauge setting by more than the thing being set.
4. THE SCREW AGAINST THE MASS CENTRE. With the moving mass on the supports: the moment the guides must supply
   (weight x horizontal offset between the screw's line of action and the mass centre for one screw), each block's
   force and moment against its static ratings, the friction the block forces add (as a share of the weight and of
   the drive force) and, for plain bearings, the binding ratio.
5. LEVEL OVER THE TRAVEL. The support springs and the moment are the same at every height, so compliance shifts the
   bed but does not tilt it as it moves. What does: the rails' running accuracy acting on the block spacing (Hiwin
   Table 3.86, class C assumed) and, with more than one screw, the screws getting out of step.
6. MORE THAN ONE SCREW. N screws and rails over-constrain the bed in tilt (N - 1 redundant supports): a height
   difference between the screws is either tilt (soft guides) or force on the guides (stiff guides); both are
   computed for the synchronisation error of the declared arrangement (drive["sync"]: "belt", one motor turning all
   screws through a closed belt; "independent", one motor per screw) and judged against whether the firmware can
   re-level (el.firmware["z_tilt"] with as many Z drivers as screws).

Declaring several screws: Joint(..., drive={"motor": [m1, m2], "kind": "leadscrew", "screw": [s1, s2],
"nut": [n1, n2], "coupler": [c1, c2], "sync": "independent"}). One screw is written as before.
"""
from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path

import numpy as np

from ..model import MATERIALS, Design
from ..report import VerifierResult

HAND_LOAD_N = 20.0
PRINT_MASS_KG = 1.0
SAG_FRACTION_OF_LAYER = 0.1
NUT_AXIAL_K_ASSUMED = 10_000.0      # N/mm: thread contact of a brass nut plus the motor's bearings (ASSUMED, no catalogue figure)
NUT_BACKLASH_ASSUMED_MM = 0.1       # typical for a plain brass T8 nut (ASSUMED); does not act while the bed's weight seats the nut
MU_BALL, MU_PLAIN = 0.005, 0.15     # recirculating balls; plain bushing on a rod (both assumed, as in the tolerance verifier)
RAIL_CLASS_ASSUMED = "C"
SYNC_BELT_MM = 0.02                 # screws tied by one closed belt: pitch and tension differences (ASSUMED)
# Lead accuracy of a rolled trapezoidal screw: +/-0.1 mm per 300 mm of travel is the usual class figure for rolled Tr
# screws (recalled from makers' catalogues, e.g. standard-grade rolled lead screws at 0.1 mm / 300 mm; no document
# fetched, and the catalogue's StepperOnline record lists "lead accuracy" under not_obtained). ASSUMED, and reported so.
# A screw part that carries ratings["lead_accuracy_mm_per_300mm"] overrides it.
LEAD_ACCURACY_ASSUMED_MM_PER_300 = 0.1
GUIDES_HOLD_TILT_RATIO = 0.5        # a tilt mode counts as held by the guides too when they are at least half as stiff in it as the screws
G = 9.81


def _aslist(v) -> list:
    return [v] if isinstance(v, str) else list(v or [])


def _center(c) -> np.ndarray:
    bb = c.shape.bounding_box()
    return np.array([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2])


def _under(design: Design, body: str, anc: str) -> bool:
    parent = {j.child: j.parent for j in design.joints}
    seen = set()
    while body not in seen:
        if body == anc:
            return True
        seen.add(body)
        if body not in parent:
            return False
        body = parent[body]
    return False


def layout(design: Design) -> dict | None:
    """The bed, its Z joint, guides, screws and print area; None when the design declares no printer bed."""
    pr = design.printer or {}
    comps = {c.name: c for c in design.components}
    j = next((x for x in design.joints if x.name == pr.get("z")), None)
    bed = comps.get(pr.get("bed"))
    if j is None or bed is None:
        return None
    a = np.array(j.axis, dtype=float)
    a /= np.linalg.norm(a)
    drv = j.drive or {}
    bed_rides = _under(design, bed.body, j.child)
    moving = [c for c in design.components if _under(design, c.body, j.child)]
    blocks = [c for c in design.components if c.meta.get("guides") == j.name]
    screws, nuts, motors = _aslist(drv.get("screw")), _aslist(drv.get("nut")), _aslist(drv.get("motor"))
    nuts = [n for n in nuts if n in comps]
    blocks = [b for b in blocks if b.name not in nuts]
    bb = bed.shape.bounding_box()
    up = -np.array(design.gravity, dtype=float)
    up /= np.linalg.norm(up)
    top = np.array([(bb.min.X + bb.max.X) / 2, (bb.min.Y + bb.max.Y) / 2, bb.max.Z])
    pa = pr.get("print_area")
    ext = (float(pa[0]), float(pa[1])) if pa else (0.8 * bb.size.X, 0.8 * bb.size.Y)
    sync = drv.get("sync") or ("none" if len(screws) <= 1 else "belt" if len(motors) == 1 else "independent")
    return {"joint": j, "axis": a, "bed": bed, "bed_rides": bed_rides, "moving": moving, "blocks": blocks, "screws": screws,
            "nuts": nuts, "motors": motors, "kind": drv.get("kind"), "top": top, "print_area": ext, "up": up, "sync": sync,
            "print_area_basis": "declared (design.printer['print_area'])" if pa else "80 % of the plate (no print area declared)",
            "layer": float(pr.get("layer_height", 0.2))}


def _skew(r):
    return np.array([[0, -r[2], r[1]], [r[2], 0, -r[0]], [-r[1], r[0], 0]])


def joint_layout(design: Design, j) -> dict:
    """What support_model needs, for ANY joint (the ratings verifier uses it for a body on guide blocks and several
    lead-screw nuts): axis, guide blocks, screws, nuts, motors, a reference point."""
    comps = {c.name: c for c in design.components}
    a = np.array(j.axis, dtype=float)
    a /= np.linalg.norm(a)
    drv = j.drive or {}
    screws, nuts, motors = _aslist(drv.get("screw")), _aslist(drv.get("nut")), _aslist(drv.get("motor"))
    nuts = [n for n in nuts if n in comps]
    blocks = [c for c in design.components if c.meta.get("guides") == j.name and c.name not in nuts]
    pts = [_center(b) for b in blocks] + [_center(comps[n]) for n in nuts]
    top = np.mean(pts, axis=0) if pts else np.zeros(3)
    return {"joint": j, "axis": a, "blocks": blocks, "screws": screws, "nuts": nuts, "motors": motors, "top": top,
            "print_area": (100.0, 100.0), "kind": drv.get("kind")}


def lead_accuracy(design: Design, lay: dict) -> dict:
    """Lead accuracy of the Z screws, mm per 300 mm: the catalogue's where a screw part records it, else the class value."""
    comps = {c.name: c for c in design.components}
    vals = [comps[s_].ratings.get("lead_accuracy_mm_per_300mm") for s_ in lay["screws"] if s_ in comps]
    if vals and all(v is not None for v in vals):
        return {"mm_per_300mm": float(max(vals)), "basis": "catalogue (ratings['lead_accuracy_mm_per_300mm'] of the screw part)", "assumed": False}
    return {"mm_per_300mm": LEAD_ACCURACY_ASSUMED_MM_PER_300, "assumed": True,
            "basis": f"ASSUMED: +/-{LEAD_ACCURACY_ASSUMED_MM_PER_300:g} mm per 300 mm, the usual class figure for a rolled trapezoidal screw "
                     f"(recalled; the catalogue has no lead accuracy for this screw: set ratings['lead_accuracy_mm_per_300mm'] on the part when the maker's is known)"}


def nut_seating(design: Design, lay: dict) -> dict:
    """How each nut carries load. "gravity": the nut only bears one way (the body sits on it; a floating nut is this
    unless said otherwise); "captive": fixed both ways, with backlash between the flanks.
    drive["nut_seating"] = "gravity" | "captive" states it; left out, a design that declares a floating nut
    (Adjustment kind "float" on the joint) is taken as gravity-seated and any other as captive."""
    j = lay["joint"]
    said = (j.drive or {}).get("nut_seating")
    floats = any(ad.kind == "float" and ad.joint in (None, j.name) for ad in design.adjustments)
    kind = said if said in ("gravity", "captive") else ("gravity" if floats else "captive")
    return {"kind": kind, "basis": ("declared (drive['nut_seating'])" if said in ("gravity", "captive") else
                                    "a floating nut is declared (Adjustment 'float'): taken as seated by the load only" if floats else
                                    "no floating nut declared: taken as fixed both ways"),
            "reverse_gap_mm": None if kind == "gravity" else NUT_BACKLASH_ASSUMED_MM,
            "reverse_gap_note": ("nothing pulls a gravity-seated nut back: once its load reaches zero it carries nothing"
                                 if kind == "gravity" else
                                 f"a captive nut bears again on its other flank after {NUT_BACKLASH_ASSUMED_MM} mm of backlash (ASSUMED)")}


def split_stiffness(model: dict, lay: dict) -> tuple:
    """(K of the guides alone, [(nut support, 6-vector c with c @ x = the body's rise at the nut along `up`, k axial)])."""
    up = lay.get("up")
    if up is None:
        up = lay["axis"] * (1.0 if lay["axis"] @ np.array([0, 0, 1.0]) >= 0 else -1.0)
    Kg = np.zeros((6, 6))
    nuts = []
    for s_ in model["supports"]:
        J = np.hstack([np.eye(3), -_skew(s_["r"])])
        if s_["kind"] == "guide":
            Kg += J.T @ s_["k"] @ J
            Kg[3:, 3:] += s_["kappa"]
        else:
            a = lay["axis"]
            nuts.append((s_, J.T @ up, float(a @ s_["k"] @ a)))
    return Kg, nuts


def tilt_redundancy(model: dict, lay: dict) -> dict:
    """How many screws are redundant, by stiffness and not by counting parts.

    The nuts hold the body's height at their points. The guides hold a pattern of nut heights too when moving the
    nuts in that pattern against the guides alone takes force comparable to the screws' own stiffness. With S the
    guides' stiffness seen at the nuts (the force at the nuts per unit of imposed nut heights, the body held only by
    its guides) and D the nuts' axial stiffness, the modes of D^-1/2 S D^-1/2 above GUIDES_HOLD_TILT_RATIO are held
    twice: each is one redundant support. Nuts beyond three (or that do not span a plane) add the rest."""
    Kg, nuts = split_stiffness(model, lay)
    n = len(nuts)
    if n == 0:
        return {"redundant": 0, "modes": []}
    B = np.column_stack([c for _, c, _ in nuts])
    k = np.array([kk for _, _, kk in nuts])
    Lc = max(float(max(lay["print_area"])), 50.0)
    Sc = np.diag([1, 1, 1, 1 / Lc, 1 / Lc, 1 / Lc])
    Kgs = Sc @ Kg @ Sc
    eps = 1e-9 * max(float(np.abs(np.diag(Kgs)).max()), float(k.max()), 1e-9)
    F = (Sc @ B).T @ np.linalg.inv(Kgs + eps * np.eye(6)) @ (Sc @ B)       # compliance of the guide-held body at the nuts
    rank = int(np.linalg.matrix_rank(B, tol=1e-6 * np.abs(B).max()))
    S = np.linalg.pinv(F, rcond=1e-9)
    Dm = np.diag(1.0 / np.sqrt(k))
    lam = np.sort(np.linalg.eigvalsh(Dm @ S @ Dm))[::-1][:rank]
    held = [float(x) for x in lam if x > GUIDES_HOLD_TILT_RATIO]
    return {"redundant": len(held) + (n - rank), "nuts_spanning": rank,
            "guide_over_screw_stiffness_by_mode": [round(float(x), 3) for x in lam],
            "modes_held_by_guides_too": len(held), "threshold": GUIDES_HOLD_TILT_RATIO}


def contact_solve(model: dict, lay: dict, wrench, offsets: dict, gap) -> dict:
    """The body on its guides (springs both ways) and on nuts that bear ONE way: nut i pushes up with
    k_i (h_i - z_i) while that is positive (h_i: how far its screw stands high, z_i: the body's rise there); with a
    reverse gap g it pulls down with k_i (h_i + g - z_i) once the body has risen g clear of it (a captive nut's other
    flank); in between it carries nothing. Active-set iteration; the wrench is (force, moment about model["O"])."""
    Kg, nuts = split_stiffness(model, lay)
    w = np.asarray(wrench, dtype=float)
    state = ["seated"] * len(nuts)
    x = np.zeros(6)
    for _ in range(40):
        K = Kg.copy()
        rhs = w.copy()
        for (s_, c, k), st in zip(nuts, state):
            if st == "free":
                continue
            h = offsets.get(s_["name"], 0.0) + (gap if st == "reversed" else 0.0)
            K += k * np.outer(c, c)
            rhs += k * h * c
        x = np.linalg.lstsq(K, rhs, rcond=None)[0]
        new = []
        for (s_, c, k) in nuts:
            z = float(c @ x)
            h = offsets.get(s_["name"], 0.0)
            new.append("seated" if h - z > 1e-12 else "reversed" if (gap is not None and z - h > gap) else "free")
        if new == state:
            break
        state = new
    forces = {}
    for (s_, c, k), st in zip(nuts, state):
        h = offsets.get(s_["name"], 0.0) + (gap if st == "reversed" else 0.0)
        forces[s_["name"]] = 0.0 if st == "free" else float(k * (h - c @ x))
    Kf = Kg.copy()
    for (s_, c, k), st in zip(nuts, state):
        if st != "free":
            Kf += k * np.outer(c, c)
    return {"u": x[:3], "theta": x[3:], "state": dict(zip([s_["name"] for s_, _, _ in nuts], state)), "nut_force_n": forces, "K": Kf, "Kg": Kg}


def _guide_forces(model: dict, x) -> float:
    u, th = x[:3], x[3:]
    return max((float(np.linalg.norm(s_["k"] @ (u + np.cross(th, s_["r"])))) for s_ in model["supports"] if s_["kind"] == "guide"), default=0.0)


def seating_study(design: Design, lay: dict, model: dict, W: float, com, wc, sync_err: float, travel: float) -> dict:
    """Screw height errors against nut seating (several screws).

    Height error between screws = the synchronisation error of the arrangement + the screws' lead error accumulated
    over the travel since the bed was trammed. For each nut: the load the moving mass seats it with, how much one
    screw standing high or low takes off it per mm (linear), hence the height error at which it unloads; and, with
    nuts that bear one way, what the bed does at each error level: which nuts lift, the change of bed level across the
    print area, the largest force on a guide block and a nut, and how far 1 kg at the worst corner then lowers the bed
    on its supports (guides and the nuts still seated)."""
    up = lay["up"]
    la = lead_accuracy(design, lay)
    seat = nut_seating(design, lay)
    e_lead = la["mm_per_300mm"] / 300.0 * travel
    Kg, nuts = split_stiffness(model, lay)
    O = model["O"]
    grav = np.concatenate([-up * W, np.cross(np.asarray(com) - O, -up * W)])
    K_all = Kg + sum(k * np.outer(c, c) for _, c, k in nuts)
    x0 = np.linalg.lstsq(K_all, grav, rcond=None)[0]
    f0 = {s_["name"]: float(-k * (c @ x0)) for s_, c, k in nuts}
    sens = {s_["name"]: 0.0 for s_, _, _ in nuts}          # N taken off this nut per mm of height error on the worst screw
    for sk, ck, kk in nuts:
        xk = np.linalg.lstsq(K_all, kk * ck, rcond=None)[0]       # screw k high by 1 mm
        for s_, c, k in nuts:
            df = k * ((1.0 if s_ is sk else 0.0) - c @ xk)
            sens[s_["name"]] = max(sens[s_["name"]], abs(float(df)))
    rows = {}
    for n_ in f0:
        crit = f0[n_] / sens[n_] if sens[n_] > 1e-9 else None
        rows[n_] = {"seating_load_n": round(f0[n_], 2), "load_change_n_per_mm_of_height_error": round(sens[n_], 1),
                    "unloads_at_height_error_mm": None if crit is None else round(max(crit, 0.0), 4)}
    levels = [("synchronisation only", sync_err),
              ("synchronisation + lead error over the travel, one screw at its class limit", sync_err + e_lead),
              ("synchronisation + lead error over the travel, two screws at opposite limits", sync_err + 2.0 * e_lead)]
    pw = PRINT_MASS_KG * G
    lvl_rows = []
    f_pw = np.concatenate([-up * pw, np.cross(np.asarray(wc) - O, -up * pw)])

    def sag_on(K):
        xx = np.linalg.lstsq(K, f_pw, rcond=None)[0]
        return float(-((xx[:3] + np.cross(xx[3:], np.asarray(wc) - O)) @ up))

    sag_seated = sag_on(K_all)
    for label, E in levels:
        worst = None
        for sk, _, _ in nuts:
            for sgn in (1.0, -1.0):
                sol = contact_solve(model, lay, grav, {sk["name"]: sgn * E}, seat["reverse_gap_mm"])
                lifted = sorted(n_ for n_, st in sol["state"].items() if st != "seated")
                tilt = _tilt_mm(sol["theta"] - x0[3:], lay)
                xs = np.concatenate([sol["u"], sol["theta"]])
                row = {"screw": sk["name"], "stands": "high" if sgn > 0 else "low", "nuts_not_seated": lifted,
                       "bed_level_change_across_print_area_mm": round(tilt, 4),
                       "largest_force_on_a_guide_block_n": round(_guide_forces(model, xs), 1),
                       "largest_nut_load_n": round(max(sol["nut_force_n"].values()), 1),
                       "least_nut_load_n": round(min(sol["nut_force_n"].values()), 2),
                       "print_weight_sag_on_supports_mm": round(sag_on(sol["K"]), 4)}
                key = (len(lifted), row["print_weight_sag_on_supports_mm"], tilt)
                if worst is None or key > worst[0]:
                    worst = (key, row)
        # the linear margin at this level: the least load any nut is left with if every nut stayed seated
        margin = {n_: round(f0[n_] - E * sens[n_], 2) for n_ in f0}
        lvl_rows.append({"case": label, "height_error_mm": round(E, 4), "nut_load_margin_n": margin,
                         "a_nut_unseats": bool(worst[1]["nuts_not_seated"]), "worst_case": worst[1]})
    return {"nut_seating": seat, "lead_accuracy": la, "travel_mm": round(travel, 1),
            "lead_error_over_travel_mm": round(e_lead, 4),
            "lead_error_note": "per screw, at the class limit; the difference between two screws is between 0 (same error) and twice this "
                               "(opposite limits). It grows with the distance moved from the height the bed was trammed at; neither a belt "
                               "nor independent motors remove it (a firmware re-level corrects it only at the height it is run at)",
            "nuts": rows, "print_weight_sag_on_supports_all_seated_mm": round(sag_seated, 4), "levels": lvl_rows,
            "how": "rigid body on guide springs and one-way nut springs (active-set contact); flexure of arms and plate is not in these "
                   "figures; guide forces are those of the support model"}


def support_model(design: Design, lay: dict) -> dict:
    """The body the bed rides on as a rigid body on springs. Returns {"K": 6x6 about the bed's top centre, "supports":
    [...], "held": bool, "free_directions": [...], "assumed": [...]}."""
    from .ratings import BLOCK_K, block_track_length_m

    comps = {c.name: c for c in design.components}
    a, O = lay["axis"], lay["top"]
    P = np.eye(3) - np.outer(a, a)
    K = np.zeros((6, 6))
    sup, assumed = [], set()
    for b in lay["blocks"]:
        kr = b.ratings.get("radial_stiffness_n_per_m")
        if kr:
            k = float(kr) * 1e-3
            src = b.ratings.get("radial_stiffness_source", "catalogue")
            assumed.add("guide block stiffness sideways taken equal to the maker's radial figure (none is published)")
        else:
            k = BLOCK_K * 1e-3
            src = "ASSUMED (ratings.BLOCK_K): no maker's rigidity for this part"
            assumed.add(f"stiffness of {b.sku or b.name}: {BLOCK_K * 1e-6:g} N/um assumed, no maker's figure")
        L = block_track_length_m(b) * 1e3
        bbx = b.shape.bounding_box()
        size = np.array([bbx.size.X, bbx.size.Y, bbx.size.Z])
        w = 0.45 * float(np.sort(size[np.abs(a) < 0.5])[0]) if np.sum(np.abs(a) < 0.5) else 5.0
        kt = k * P
        kap = k * L ** 2 / 12.0 * P + k * w ** 2 / 12.0 * np.outer(a, a)
        r_ = _center(b) - O
        J = np.hstack([np.eye(3), -_skew(r_)])
        K += J.T @ kt @ J
        K[3:, 3:] += kap
        plain = "static_load_n" not in b.ratings or (b.sku or "").upper().startswith(("LM", "BUSH"))
        sup.append({"name": b.name, "kind": "guide", "r": r_, "k": kt, "kappa": kap, "k_n_per_um": k * 1e-3, "source": src, "track_mm": L,
                    "mu": float(b.ratings.get("friction_coefficient", MU_PLAIN if plain else MU_BALL)),
                    "static_load_n": b.ratings.get("static_load_n"), "static_moment_nm": b.ratings.get("static_moment_nm")})
    assumed.add("guide block roll stiffness about the rail from an assumed ball gauge of 0.45 x the block's width")
    j = lay["joint"]
    floats = any(ad.kind == "float" and ad.joint in (None, j.name) for ad in design.adjustments)
    for i, nn in enumerate(lay["nuts"]):
        nut = comps[nn]
        scr = comps.get(lay["screws"][i]) if i < len(lay["screws"]) else None
        k_col, free_len = None, None
        if scr is not None:
            sb = scr.shape.bounding_box()
            lo = np.array([sb.min.X, sb.min.Y, sb.min.Z]) @ np.abs(a)
            hi = np.array([sb.max.X, sb.max.Y, sb.max.Z]) @ np.abs(a)
            dia = float(np.sort(np.array([sb.size.X, sb.size.Y, sb.size.Z]))[1])
            npos = float(_center(nut) @ np.abs(a))
            # the driven (fixed) end is the one a coupler or motor is at; else the nearer end
            free_len = max(min(abs(npos - lo), abs(npos - hi)) if not lay["motors"] else
                           abs(npos - (lo if abs(float(_center(comps[lay["motors"][min(i, len(lay["motors"]) - 1)]]) @ np.abs(a)) - lo)
                                       < abs(float(_center(comps[lay["motors"][min(i, len(lay["motors"]) - 1)]]) @ np.abs(a)) - hi) else hi)), 5.0)
            area = math.pi * (0.78 * dia) ** 2 / 4.0          # root diameter about 0.78 x nominal for a trapezoidal thread
            k_col = MATERIALS[scr.material].E * area / free_len
        k_ax = 1.0 / (1.0 / NUT_AXIAL_K_ASSUMED + (1.0 / k_col if k_col else 0.0))
        r_ = _center(nut) - O
        kt = k_ax * np.outer(a, a)
        J = np.hstack([np.eye(3), -_skew(r_)])
        K += J.T @ kt @ J
        sup.append({"name": nn, "kind": "nut", "r": r_, "k": kt, "kappa": np.zeros((3, 3)), "k_axial_n_per_um": k_ax * 1e-3,
                    "screw_column_n_per_um": None if k_col is None else k_col * 1e-3, "free_length_mm": free_len,
                    "floats_sideways": floats, "screw": scr.name if scr is not None else None})
    if lay["nuts"]:
        assumed.add(f"nut axial stiffness: screw column in series with {NUT_AXIAL_K_ASSUMED * 1e-3:g} N/um ASSUMED for thread contact "
                    f"and motor bearings (not catalogued)")
        assumed.add(f"nut backlash {NUT_BACKLASH_ASSUMED_MM} mm ASSUMED (not catalogued); it does not act while the weight seats the nut")
    # is the body held? scale rotations by a typical arm so the eigenvalues compare
    Lc = max(float(max(lay["print_area"])), 50.0)
    S = np.diag([1, 1, 1, 1 / Lc, 1 / Lc, 1 / Lc])
    w_, v_ = np.linalg.eigh(S @ K @ S)
    free = []
    names = ["x", "y", "z", "turning about x", "turning about y", "turning about z"]
    if w_.max() > 0:
        for lam, vec in zip(w_, v_.T):
            if lam < 1e-7 * w_.max():
                free.append(names[int(np.argmax(np.abs(vec)))])
    return {"K": K, "supports": sup, "held": bool(sup) and not free, "free_directions": free, "assumed": sorted(assumed), "O": O}


def respond(model: dict, force, point) -> dict:
    """Displacement of the body for a force at a world point: {"u", "theta", "at": lambda p -> displacement there,
    "reactions": [{name, force_n, moment_nmm}]}."""
    r_ = np.asarray(point, dtype=float) - model["O"]
    f = np.asarray(force, dtype=float)
    w = np.concatenate([f, np.cross(r_, f)])
    x = np.linalg.lstsq(model["K"], w, rcond=None)[0]
    u, th = x[:3], x[3:]
    reac = []
    for s in model["supports"]:
        d = u + np.cross(th, s["r"])
        reac.append({"name": s["name"], "kind": s["kind"], "force": s["k"] @ d, "moment": s["kappa"] @ th})
    return {"u": u, "theta": th, "at": lambda p: u + np.cross(th, np.asarray(p, dtype=float) - model["O"]), "reactions": reac}


def _grid(lay: dict, k: int = 5) -> list:
    ex, ey = lay["print_area"]
    t = lay["top"]
    return [t + np.array([x, y, 0.0]) for x in np.linspace(-ex / 2, ex / 2, k) for y in np.linspace(-ey / 2, ey / 2, k)]


def _tilt_mm(th, lay) -> float:
    """Height difference across the print area for a small rotation."""
    ex, ey = lay["print_area"]
    return float(abs(th[1]) * ex + abs(th[0]) * ey)


def flexure(design: Design, lay: dict, load_point, r: VerifierResult | None = None) -> dict:
    """FEA of the bed's carrying parts for a unit load at `load_point` on the print surface. Returns per-newton
    deflection and tilt, bonded and screw-only, or {"evaluated": False, "why": ...}."""
    from build123d import Vertex

    from . import fea as F

    if not shutil.which("ccx"):
        return {"evaluated": False, "why": "CalculiX (ccx) is not installed"}
    comps = {c.name: c for c in design.components}
    pr = design.printer or {}
    j, a, bed = lay["joint"], lay["axis"], lay["bed"]
    k_ax = int(np.argmax(np.abs(a)))
    if abs(a[k_ax]) < 0.999:
        return {"evaluated": False, "why": "the Z axis is not along a world axis: the supports cannot be written as plain boundary conditions"}
    blocks = [b.name for b in lay["blocks"]]
    want = (pr.get("bed_support") or {}).get("parts")
    basis = "design.printer['bed_support']['parts']"
    if not want:
        case = next((ac for ac in sorted(design.assemblycases, key=lambda c_: -len(c_.components))
                     if bed.name in ac.components and any(b in ac.components for b in blocks)), None)
        if case is None:
            return {"evaluated": False, "why": "no parts given: declare design.printer['bed_support'] = {'parts': [...]} (the bed, what "
                                               "carries it and its guide blocks) or an AssemblyCase containing the bed and its guide blocks"}
        want, basis = list(case.components), f"the parts of AssemblyCase '{case.name}'"
    names = [n for n in want if n in comps]
    fast = {f.name for f in design.fasteners}
    # what the nut sits in: parts of the moving body that touch a nut
    seats = []
    for nn in lay["nuts"]:
        nut = comps[nn]
        for c in lay["moving"]:
            if c.name in fast or c.name == nn or (c.sku or "").startswith(("SHCS", "NUT")):
                continue
            try:
                if c.shape.distance_to(nut.shape) <= 0.05:
                    seats.append((c.name, nn))
                    if c.name not in names:
                        names.append(c.name)
            except Exception:
                pass
    rails = {}
    for b in lay["blocks"]:
        if b.name not in names:
            continue
        other = j.parent if b.body == j.child else j.child
        best = None
        for c in design.components:
            if c.body != other:
                continue
            try:
                d = b.shape.distance_to(c.shape)
            except Exception:
                continue
            if d < 1.0 and (best is None or d < best[0]):
                best = (d, c)
        if best is not None:
            rails[b.name] = best[1]
    if not rails:
        return {"evaluated": False, "why": "none of the bed's guide blocks is among the parts"}

    def near(shape, tol_):
        def pred(f):
            c = f.center()
            try:
                return shape.distance_to(Vertex(c.X, c.Y, c.Z)) <= tol_
            except Exception:
                return False
        return pred

    up = lay["up"]
    top_z = float(lay["top"] @ up)

    def top_face(f):
        try:
            n_ = f.normal_at(f.center())
        except Exception:
            return False
        return abs(float(np.array([n_.X, n_.Y, n_.Z]) @ up) - 1.0) < 1e-6 and abs(float(np.array(tuple(f.center())) @ up) - top_z) < 1e-3

    sel = {"load": [(bed.name, top_face)], "guides": [(b, near(rl.shape, 0.35)) for b, rl in rails.items()]}
    seat_sel = [(c, near(comps[nn].shape, 0.05)) for c, nn in seats]
    if seat_sel:
        sel["seat"] = seat_sel
    workdir = Path(tempfile.mkdtemp(prefix="mechloop_bed_"))
    try:
        try:
            mesh = F._asm_mesh(design, names, sel, None, workdir)
        except Exception as e:
            return {"evaluated": False, "why": f"meshing failed: {type(e).__name__}: {e}", "parts": names}
        xyz = mesh["xyz"]
        g_nodes = np.unique(mesh["sel_tris"]["guides"]) if len(mesh["sel_tris"]["guides"]) else np.array([], dtype=int)
        s_nodes = np.unique(mesh["sel_tris"]["seat"]) if "seat" in mesh["sel_tris"] and len(mesh["sel_tris"]["seat"]) else np.array([], dtype=int)
        if not len(g_nodes):
            return {"evaluated": False, "why": "no face of a guide block was found on its rail", "parts": names}
        perp = [d + 1 for d in range(3) if d != k_ax]
        if len(s_nodes):
            bc = [(g_nodes, d) for d in perp] + [(s_nodes, k_ax + 1)]
            support = "held across the rail at the guide blocks and along the screw at the nut seat"
        else:
            bc = [(g_nodes, d) for d in (1, 2, 3)]
            support = ("IDEAL: fully fixed at the guide blocks (no nut seat among the parts: the vertical load is taken at the "
                       "blocks, which overstates stiffness)")
        top_nodes = np.unique(mesh["sel_tris"]["load"])
        if not len(top_nodes):
            return {"evaluated": False, "why": "the bed's top face was not found in the mesh", "parts": names}
        lp = np.asarray(load_point, dtype=float)
        dist = np.linalg.norm(xyz[top_nodes] - lp, axis=1)
        pick = top_nodes[dist <= 10.0]
        if len(pick) < 3:
            pick = top_nodes[np.argsort(dist)[:6]]
        force = -up * 10.0
        nodal = {int(n_): 1.0 / len(pick) for n_ in pick}
        fixed_all = np.unique(np.concatenate([b_[0] for b_ in bc]))
        out = {"evaluated": True, "parts": names, "parts_from": basis, "supports": support, "nodes": int(len(xyz)),
               "nut_seat": [f"{c} under {nn}" for c, nn in seats] or None, "unit_load_n": 10.0}

        ex, ey = lay["print_area"]
        rel = xyz[top_nodes] - lay["top"]
        inside = top_nodes[(np.abs(rel[:, 0]) <= ex / 2 + 1e-6) & (np.abs(rel[:, 1]) <= ey / 2 + 1e-6)]

        def read(U, pts):
            d_load = float(-(U[pick] @ up).mean())
            A = np.column_stack([pts[inside][:, 0], pts[inside][:, 1], np.ones(len(inside))])
            coef = np.linalg.lstsq(A, U[inside] @ up, rcond=None)[0]
            return d_load / 10.0, float(abs(coef[0]) * ex + abs(coef[1]) * ey) / 10.0

        res = F._asm_solve(workdir, "bed", xyz, mesh["part_tets"], mesh["comps"], fixed_all, nodal, force, force, "bed support", None, bc=bc)
        if "error" in res:
            return {"evaluated": False, "why": f"solver: {res['error']}", "parts": names}
        out["bonded_mm_per_n"], out["bonded_tilt_mm_per_n"] = read(res["U"], xyz)
        try:
            xyz2, tets2, info = F._unbond_away_from_screws(design, mesh, names)
            if info:
                res2 = F._asm_solve(workdir, "bed_screwed", xyz2, tets2, mesh["comps"], fixed_all, nodal, force, force,
                                    "bed support (screwed joints)", None, bc=bc)
                if "error" not in res2 and res2["rf"] is not None and float(np.linalg.norm(res2["rf"] + force)) / 10.0 < 0.01:
                    out["screwed_mm_per_n"], out["screwed_tilt_mm_per_n"] = read(res2["U"], xyz2[:len(xyz)])
                    out["screwed_joints"] = len(info)
                else:
                    out["screwed_note"] = "the screw-only model did not solve cleanly (a part came free): only the bonded figure is given"
            else:
                out["screwed_note"] = "no screwed joint among the parts: the screw-only bound equals the bonded one"
                out["screwed_mm_per_n"], out["screwed_tilt_mm_per_n"] = out["bonded_mm_per_n"], out["bonded_tilt_mm_per_n"]
        except Exception as e:
            out["screwed_note"] = f"screw-only model not run: {type(e).__name__}: {e}"
        return out
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _sync(design: Design, lay: dict) -> dict:
    """Height error between screws for the declared synchronisation, and whether the firmware can take it out."""
    comps = {c.name: c for c in design.components}
    n_s = len(lay["screws"])
    lead = float((comps[lay["screws"][0]].ratings.get("lead_mm") or (lay["joint"].drive or {}).get("lead") or 8.0)) if lay["screws"] else 8.0
    el = getattr(design, "electrical", None)
    fw = (el.firmware if el is not None else {}) or {}
    zt = fw.get("z_tilt") or (design.printer or {}).get("z_tilt")
    drivers = None
    if el is not None:
        try:
            from ..electrical import _board_port_of, axis_motors

            st = axis_motors(el, design).get(lay["joint"].name, {})
            ports = [_board_port_of(el, m_) for m_ in st.get("motors", [])]
            drivers = len({str(p_.pin.get("step")) if isinstance(p_.pin, dict) else id(p_) for p_ in ports if p_ is not None})
        except Exception:
            drivers = None
    if lay["sync"] == "belt":
        err, basis = SYNC_BELT_MM, f"one motor, screws tied by a closed belt: {SYNC_BELT_MM} mm ASSUMED for pitch and tension differences"
    else:
        err = 2.0 * lead / 200.0
        basis = (f"one motor per screw: at power-up each motor settles on its nearest full-step detent, up to 2 full steps "
                 f"({lead:g} mm lead / 200 x 2 = {err:g} mm) apart; lost steps add without limit until re-levelled")
    can = bool(zt) and lay["sync"] == "independent" and (drivers is None or drivers >= n_s)
    return {"screws": n_s, "sync": lay["sync"], "height_error_mm": err, "basis": basis, "z_drivers": drivers,
            "firmware_tilt_adjust_declared": bool(zt),
            "firmware_can_relevel": can,
            "why_not": None if can else ("screws tied together by a belt cannot be moved against each other by the firmware"
                                         if lay["sync"] == "belt" else
                                         "el.firmware['z_tilt'] is not declared" if not zt else
                                         f"{drivers} Z driver(s) for {n_s} screws: motors sharing a driver cannot be moved against each other")}


def bed_support(design: Design, r: VerifierResult, with_fea: bool = True) -> dict | None:
    """All of the above; adds findings to r and returns the metrics (None: no printer bed declared)."""
    lay = layout(design)
    if lay is None:
        return None
    from .ratings import resolve_drives

    resolve_drives(design)
    j = lay["joint"]
    out: dict = {"z_joint": j.name, "bed": lay["bed"].name, "bed_rides_z": lay["bed_rides"],
                 "print_area_mm": list(lay["print_area"]), "print_area_basis": lay["print_area_basis"],
                 "guides": [b.name for b in lay["blocks"]], "screws": lay["screws"], "nuts": lay["nuts"]}
    if not lay["bed_rides"]:
        out["evaluated"] = False
        out["why"] = "the bed does not ride the Z joint (the nozzle does): the bed's support is the frame, which these measures do not cover"
        r.add("info", "bed_support_not_evaluated", f"Bed support measures were NOT evaluated: {out['why']}.")
        return out
    if lay["kind"] != "leadscrew" or not lay["nuts"]:
        out["evaluated"] = False
        out["why"] = ("the Z joint is not driven by a lead screw with a named nut (drive={'kind': 'leadscrew', 'screw': ..., 'nut': ...}): "
                      "what carries the bed's weight is not declared")
        r.add("warning", "bed_support_not_evaluated", f"Bed support measures were NOT evaluated: {out['why']}. Not evaluated is not a pass.")
        return out
    if len(lay["nuts"]) != len(lay["screws"]):
        r.add("error", "z_drive_incomplete", f"Joint {j.name}: {len(lay['screws'])} lead screw(s) but {len(lay['nuts'])} nut(s) named in its "
              f"drive; each screw needs its nut.", joint=j.name)
    model = support_model(design, lay)
    out["supports"] = [{k: (round(float(v), 2) if isinstance(v, float) else v) for k, v in s.items() if k not in ("r", "k", "kappa")} | {"mu": s.get("mu")} if s["kind"] == "guide" else
                       {k: (round(float(v), 2) if isinstance(v, float) else v) for k, v in s.items() if k not in ("r", "k", "kappa")}
                       for s in model["supports"]]
    out["assumed"] = model["assumed"]
    n_s = len(lay["nuts"])
    rails = len({tuple(np.round((s["r"] - (s["r"] @ lay["axis"]) * lay["axis"]), 0)) for s in model["supports"] if s["kind"] == "guide"})
    red = tilt_redundancy(model, {**lay}) if model["supports"] else {"redundant": 0}
    n_red = int(red["redundant"])
    out["constraint"] = {"lead_screws": n_s, "guide_rails_or_rods": rails, "guide_blocks": len(lay["blocks"]),
                         "redundant_screw_supports": n_red, "redundancy": red,
                         "note": ("one screw sets the height, the guides hold the tilt: exactly constrained in height" if n_s == 1 else
                                  f"{n_s} screws and {rails} guide(s), {len(lay['blocks'])} block(s): "
                                  + (f"over-constrained by {n_red} support(s): the guides hold the bed's tilt as stiffly as the screws do in "
                                     f"{red.get('modes_held_by_guides_too', 0)} mode(s), so a height difference between screws becomes force on "
                                     f"guides and nuts" if n_red else
                                     "the screws set the bed's plane and the guides do not resist it (their stiffness in tilt is small "
                                     "beside the screws'): a height difference between screws becomes tilt, not force"))}
    if not model["held"]:
        out["evaluated"] = False
        out["why"] = f"the bed is not held in: {', '.join(model['free_directions']) or 'anything (no supports found)'}"
        r.add("error", "bed_not_held", f"The body that carries the bed is a mechanism on its declared supports: free in "
              f"{', '.join(model['free_directions']) or 'every direction'}. Guide blocks need guides='{j.name}' and the drive its nut(s).",
              joint=j.name)
        return out
    out["evaluated"] = True
    up = lay["up"]
    # ---- worst point of the print area for a downward load (by the support model), and the corners
    pts = _grid(lay)
    sag = [float(-(respond(model, -up, p)["at"](p) @ up)) for p in pts]
    worst = pts[int(np.argmax(sag))]
    ex, ey = lay["print_area"]
    corners = [lay["top"] + np.array([sx * ex / 2, sy * ey / 2, 0.0]) for sx in (-1, 1) for sy in (-1, 1)]
    csag = [float(-(respond(model, -up, p)["at"](p) @ up)) for p in corners]
    wc = corners[int(np.argmax(csag))]
    flex = flexure(design, lay, wc, r) if with_fea else {"evaluated": False, "why": "FEA not requested"}
    out["flexure"] = flex
    if not flex.get("evaluated"):
        r.add("warning", "bed_flexure_not_evaluated",
              f"Bed support: the flexure of the parts that carry the bed was NOT evaluated ({flex.get('why')}). The deflections "
              f"below contain the guides' and the nut's compliance only and are a lower bound.")
    w_print = PRINT_MASS_KG * G

    def case(load_n, point, label):
        res = respond(model, -up * load_n, point)
        sup_mm = float(-(res["at"](point) @ up))
        sup_tilt = _tilt_mm(res["theta"], lay)
        row = {"load_n": round(load_n, 2), "at": [round(float(x), 1) for x in point],
               "support_compliance_mm": round(sup_mm, 4), "support_compliance_tilt_mm": round(sup_tilt, 4)}
        if flex.get("evaluated"):
            for key in ("bonded", "screwed"):
                if f"{key}_mm_per_n" in flex:
                    row[f"flexure_{key}_mm"] = round(flex[f"{key}_mm_per_n"] * load_n, 4)
                    row[f"total_{key}_mm"] = round(flex[f"{key}_mm_per_n"] * load_n + sup_mm, 4)
                    row[f"tilt_across_print_area_{key}_mm"] = round(flex[f"{key}_tilt_mm_per_n"] * load_n + sup_tilt, 4)
            row["range_note"] = "bonded: every touching face joined (stiff bound); screwed: joints held only round their screws (soft bound)"
        else:
            row["total_supports_only_mm"] = round(sup_mm, 4)
        row["judged_mm"] = row.get("total_screwed_mm", row.get("total_bonded_mm", sup_mm))
        return row

    out["hand_load"] = case(HAND_LOAD_N, wc if flex.get("evaluated") else worst, "hand")
    out["print_weight"] = case(w_print, wc, "print")
    out["hand_load"]["point_basis"] = ("worst corner of the print area (the flexure was solved there)" if flex.get("evaluated")
                                       else "worst point of the print area by the support model")
    lim = SAG_FRACTION_OF_LAYER * lay["layer"]
    out["print_weight"]["limit_mm"] = round(lim, 4)
    if out["print_weight"]["judged_mm"] > lim:
        pw = out["print_weight"]
        r.add("warning", "bed_sags_under_print_weight",
              f"A {PRINT_MASS_KG:g} kg print at the worst corner of the print area lowers the print surface there by "
              f"{pw['judged_mm']:.3f} mm" + (f" (bonded joints {pw['total_bonded_mm']:.3f}, screw-only joints {pw.get('total_screwed_mm', pw['total_bonded_mm']):.3f}; "
                                               f"of which guides and nut {pw['support_compliance_mm']:.3f})" if "total_bonded_mm" in pw else
                                               " (guides and nut only: flexure not evaluated)")
              + f", more than {SAG_FRACTION_OF_LAYER:g} of a {lay['layer']:g} mm layer ({lim:.3f} mm). The bed is levelled and "
              f"meshed empty, so neither sees it.", deflection_mm=pw["judged_mm"], limit_mm=round(lim, 4),
              hint="Shorten the overhang, space the guide blocks further apart along the rail, stiffen the arms, or support the bed "
                   "at a second or third point.")
    if out["hand_load"]["judged_mm"] > lay["layer"]:
        hl = out["hand_load"]
        r.add("warning", "bed_moves_under_hand_load",
              f"A {HAND_LOAD_N:g} N hand load at the worst point of the print area moves the print surface {hl['judged_mm']:.2f} mm, "
              f"more than a {lay['layer']:g} mm layer: setting the nozzle gap by feel or with a gauge disturbs what is being set.",
              deflection_mm=hl["judged_mm"])
    # ---- the moving mass on the supports: what the screw's position asks of the guides
    mass = sum(c.mass() for c in lay["moving"])
    com = sum(c.mass() * _center(c) for c in lay["moving"]) / max(mass, 1e-12)
    W = mass * G
    res = respond(model, -up * W, com)
    a = lay["axis"]
    nut_c = np.mean([s["r"] + model["O"] for s in model["supports"] if s["kind"] == "nut"], axis=0)
    off = (com - nut_c) - ((com - nut_c) @ up) * up
    offset = float(np.linalg.norm(off))
    drive_n = j.max_effort
    fric, rows, worst_m, worst_f = 0.0, {}, None, None
    for s, q in zip(model["supports"], res["reactions"]):
        fn_, mn_ = float(np.linalg.norm(q["force"])), float(np.linalg.norm(q["moment"])) * 1e-3
        row = {"force_n": round(fn_, 2)}
        if s["kind"] == "guide":
            # a moment on a block is carried as edge loads half a ball track apart: they rub like any other load
            fric += s["mu"] * (fn_ + 2.0 * float(np.linalg.norm(q["moment"])) / max(s.get("track_mm", 30.0), 1.0))
            row["moment_nm"] = round(mn_, 4)
            if s.get("static_moment_nm"):
                row["moment_safety"] = round(min(s["static_moment_nm"] / mn_, 9999.0), 1) if mn_ > 1e-9 else 9999.0
                worst_m = row["moment_safety"] if worst_m is None else min(worst_m, row["moment_safety"])
            if s.get("static_load_n"):
                row["load_safety"] = round(min(s["static_load_n"] / fn_, 9999.0), 1) if fn_ > 1e-9 else 9999.0
                worst_f = row["load_safety"] if worst_f is None else min(worst_f, row["load_safety"])
        rows[s["name"]] = row
    mus = sorted({s["mu"] for s in model["supports"] if s["kind"] == "guide"})
    gm = {"moving_mass_kg": round(mass, 3), "mass_centre": [round(float(x), 1) for x in com],
          "screw_line_to_mass_centre_mm": round(offset, 1),
          "moment_on_guides_nm": round(W * offset * 1e-3, 3) if n_s == 1 else None,
          **({"moment_note": "with several screws the moment is shared between screws and guides by their stiffness: see the reactions"} if n_s > 1 else {}),
          "reactions": rows, "least_moment_safety": worst_m, "least_load_safety": worst_f,
          "friction_added_n": round(fric, 3), "friction_coefficients": mus,
          "friction_over_weight": round(fric / W, 4) if W > 0 else None,
          "friction_over_drive_force": round(fric / drive_n, 4) if drive_n else None,
          "sag_at_mass_centre_mm": round(float(-(res["at"](com) @ up)), 4),
          "tilt_across_print_area_mm": round(_tilt_mm(res["theta"], lay), 4),
          "note": "tilt under the machine's own weight is the same at every height: bed levelling takes it out"}
    out["moving_mass_on_guides"] = gm
    if (worst_m is not None and worst_m < 3.0) or (worst_f is not None and worst_f < 3.0):
        r.add("error", "guide_overloaded_by_screw_offset",
              f"Joint {j.name}: the lead screw's line of action is {offset:.0f} mm from the {mass:.2f} kg moving mass centre; the guide "
              f"blocks then carry the moment with a safety of {worst_m} on their static moment and {worst_f} on their static load "
              f"(3 is required).", joint=j.name)
    if gm["friction_over_weight"] is not None and gm["friction_over_weight"] >= 1.0:
        r.add("error", "z_guides_bind",
              f"Joint {j.name}: with the screw {offset:.0f} mm from the mass centre the guides' friction ({fric:.1f} N at friction "
              f"coefficient {mus}) is as large as the weight it resists ({W:.1f} N): the bed jams instead of following the screw.",
              joint=j.name, hint="Bring the screw under the mass centre, lengthen the guide spacing, or use rolling guides.")
    elif gm["friction_over_weight"] is not None and (gm["friction_over_weight"] > 0.3 or (drive_n and fric > 0.1 * drive_n)):
        r.add("warning", "z_guide_friction_from_screw_offset",
              f"Joint {j.name}: the offset of {offset:.0f} mm between screw and mass centre loads the guides enough to add {fric:.1f} N "
              f"of friction ({gm['friction_over_weight']:.0%} of the weight"
              + (f", {fric / drive_n:.0%} of the drive force" if drive_n else "") + "): stick-slip and uneven layers are likely.",
              joint=j.name)
    # ---- level over the travel
    lvl: dict = {"from_support_compliance_mm": 0.0,
                 "from_support_compliance_note": "same blocks, same springs and same moment at every height"}
    try:
        from ..parts import vendor_data

        rp = vendor_data("hiwin_mgn12")["catalogue"]["running_parallelism_um"]
        travel = abs(j.mechanical_range[1] - j.mechanical_range[0])
        if any((b.sku or "").startswith("MGN") for b in lay["blocks"]):
            rail_len = max(travel, 1.0)
            key = next(k for k, hi_ in (("up_to_50", 50), ("50_80", 80), ("80_125", 125), ("125_200", 200), ("200_250", 250),
                                        ("250_315", 315), ("315_400", 400), ("400_500", 500)) if rail_len <= hi_ or k == "400_500")
            run = rp[key][rp["columns"].index(RAIL_CLASS_ASSUMED)] * 1e-3
            al = np.array([(s["r"] @ a) for s in model["supports"] if s["kind"] == "guide"])
            span = float(al.max() - al.min())
            from .ratings import block_track_length_m

            base = max(span, block_track_length_m(lay["blocks"][0]) * 1e3)
            reach = float(max(np.linalg.norm((c_ - (np.mean([s["r"] for s in model["supports"] if s["kind"] == "guide"], axis=0) + model["O"]))
                                             - ((c_ - (np.mean([s["r"] for s in model["supports"] if s["kind"] == "guide"], axis=0) + model["O"])) @ a) * a)
                              for c_ in corners))
            # What the wander does to the bed is found on the support model, so that screws which hold the bed's plane
            # count: each block in turn is moved sideways by the running parallelism (both directions across the
            # rail) and, because a block follows its rail's slope over its own ball track, turned by
            # parallelism / track length (both axes across the rail). The bed's height change at the print corners
            # is read off; the worst single disturbance is reported.
            worst_lv, worst_what = 0.0, None
            lat = [v_ for v_ in np.eye(3) if abs(v_ @ a) < 0.5]
            for s_ in model["supports"]:
                if s_["kind"] != "guide":
                    continue
                Jb = np.hstack([np.eye(3), -_skew(s_["r"])])
                for v_ in lat:
                    for kind_, wr in (("moved sideways", Jb.T @ (s_["k"] @ (v_ * run))),
                                      ("turned with its rail", np.concatenate([np.zeros(3), s_["kappa"] @ (v_ * run / max(s_.get("track_mm", 30.0), 1.0))]))):
                        xx = np.linalg.lstsq(model["K"], wr, rcond=None)[0]
                        dz = max(abs(float((xx[:3] + np.cross(xx[3:], c_ - model["O"])) @ up)) for c_ in corners)
                        if dz > worst_lv:
                            worst_lv, worst_what = dz, f"{s_['name']} {kind_}"
            lvl.update({"rail_running_parallelism_mm": run, "rail_class": f"{RAIL_CLASS_ASSUMED} (ASSUMED: the design does not state the accuracy class)",
                        "source": rp["ref"], "block_spacing_along_rail_mm": round(span, 1), "furthest_print_corner_from_guides_mm": round(reach, 1),
                        "from_rail_running_accuracy_mm": round(worst_lv, 4), "worst_disturbance": worst_what,
                        "guides_alone_formula_mm": round(run / base * reach, 4),
                        "how": "each guide block in turn wanders by the running parallelism (sideways, and turned by parallelism / "
                               "ball-track length); the bed's height change at the print corners on ALL its supports (guide blocks and "
                               "lead-screw nuts, a nut holding along its screw only). guides_alone_formula_mm is the earlier estimate "
                               "(slope over the block spacing carried to the far corner), right when nothing but the guides holds the tilt"})
        else:
            lvl["from_rail_running_accuracy_mm"] = None
            lvl["rail_note"] = "NOT evaluated: no running accuracy catalogued for these guides"
    except Exception as e:
        lvl["rail_note"] = f"NOT evaluated: {type(e).__name__}: {e}"
    lvl["not_included"] = "straightness of what the rails are screwed to (T-slot extrusion: not catalogued) and screw wobble through a nut that does not float"
    out["level_over_travel"] = lvl
    if lvl.get("from_rail_running_accuracy_mm") and lvl["from_rail_running_accuracy_mm"] > lay["layer"] / 2:
        r.add("warning", "bed_level_changes_over_travel",
              f"Joint {j.name}: the rails' running accuracy ({lvl['rail_running_parallelism_mm'] * 1e3:.0f} um, class "
              f"{RAIL_CLASS_ASSUMED} assumed) changes the bed's level by up to {lvl['from_rail_running_accuracy_mm']:.3f} mm at a print "
              f"corner over the travel (limit half a layer): worst is {lvl['worst_disturbance']}, on {len(lay['blocks'])} guide block(s) "
              f"with {lvl['block_spacing_along_rail_mm']:g} mm of spacing along the rail and {n_s} lead-screw nut(s), which hold along "
              f"their screws only; the far print corner is {lvl['furthest_print_corner_from_guides_mm']:g} mm from the guides.", joint=j.name,
              hint="Space the blocks further apart along the rail, or carry the bed on three screws so that the screws set its plane.")
    # ---- several screws
    if n_s > 1:
        sy = _sync(design, lay)
        nuts = [s for s in model["supports"] if s["kind"] == "nut"]
        worst_t, worst_block, worst_nut = 0.0, 0.0, 0.0
        for s in nuts:        # one screw high by the error: a force pair through its spring
            kax = float(a @ s["k"] @ a)
            f = a * kax * sy["height_error_mm"]
            w = np.concatenate([f, np.cross(s["r"], f)])
            x = np.linalg.lstsq(model["K"], w, rcond=None)[0]
            u, th = x[:3], x[3:]
            worst_t = max(worst_t, _tilt_mm(th, lay))
            for s2 in model["supports"]:
                d = u + np.cross(th, s2["r"])
                fo = float(np.linalg.norm(s2["k"] @ d - (f if s2 is s else 0.0)))
                if s2["kind"] == "guide":
                    worst_block = max(worst_block, fo)
                else:
                    worst_nut = max(worst_nut, fo)
        sy.update({"bed_tilt_across_print_area_mm": round(worst_t, 4), "force_on_a_guide_block_n": round(worst_block, 1),
                   "force_on_a_nut_n": round(worst_nut, 1),
                   "how": "one screw high by the height error, the bed on its supports' stiffness: part becomes tilt, part force "
                          "(linear: every nut taken as seated; see nut_seating_and_lead_error for what happens when one is not)"})
        out["screw_synchronisation"] = sy
        travel = abs(j.range[1] - j.range[0])
        st = None
        if abs(float(a @ up)) > 0.99:
            try:
                st = seating_study(design, lay, model, W, com, wc, sy["height_error_mm"], travel)
            except Exception as e:      # never lose the other measures to this one; say so
                out["nut_seating_and_lead_error"] = {"evaluated": False, "why": f"{type(e).__name__}: {e}"}
                r.add("warning", "nut_seating_not_evaluated", f"Joint {j.name}: nut seating under screw height errors was NOT evaluated ({type(e).__name__}: {e}).")
        else:
            out["nut_seating_and_lead_error"] = {"evaluated": False, "why": "the Z axis is not vertical: the nuts are not seated by weight"}
        if st is not None:
            st["evaluated"] = True
            out["nut_seating_and_lead_error"] = st
            lvl["from_screw_lead_error_mm"] = st["levels"][1]["worst_case"]["bed_level_change_across_print_area_mm"]
            lvl["from_screw_lead_error_note"] = (f"one screw at its lead-accuracy limit over the {travel:g} mm travel "
                                                 f"({st['lead_error_over_travel_mm']:g} mm; {st['lead_accuracy']['basis']})")
        half = lay["layer"] / 2
        expected = st["levels"][1] if st is not None else None
        sync_only = st["levels"][0] if st is not None else None
        seat_txt = ""
        if expected is not None:
            wc_ = expected["worst_case"]
            least = min(expected["nut_load_margin_n"].values())
            seat_txt = (f" Nut seating ({st['nut_seating']['kind']}: {st['nut_seating']['basis']}): the moving mass seats the nuts with "
                        + ", ".join(f"{v['seating_load_n']:.1f}" for v in st["nuts"].values()) + f" N. With the screws' lead error over the "
                        f"{travel:g} mm travel added ({st['lead_error_over_travel_mm']:.3f} mm, {'ASSUMED class value' if st['lead_accuracy']['assumed'] else 'catalogue'}) "
                        f"the height error is {expected['height_error_mm']:.3f} mm and the least nut load would be {least:.1f} N"
                        + (f": {', '.join(wc_['nuts_not_seated'])} unseat(s) ({wc_['screw']} standing {wc_['stands']}); the bed's level then "
                           f"changes {wc_['bed_level_change_across_print_area_mm']:.3f} mm across the print area, a guide block carries "
                           f"{wc_['largest_force_on_a_guide_block_n']:.0f} N, and 1 kg at the worst corner lowers the bed "
                           f"{wc_['print_weight_sag_on_supports_mm']:.3f} mm on its supports instead of "
                           f"{st['print_weight_sag_on_supports_all_seated_mm']:.3f} mm." if expected["a_nut_unseats"] else
                           f": every nut stays seated; the bed's level changes {wc_['bed_level_change_across_print_area_mm']:.3f} mm across the print area."))
        if expected is not None and expected["a_nut_unseats"] and n_red > 0:
            r.add("warning", "z_tilt_over_constrained",
                  f"Joint {j.name}: {n_s} lead screws and {len(lay['blocks'])} guide block(s) on {rails} rail(s) both hold the bed's tilt "
                  f"({n_red} redundant support(s)): the rails fight the screws. A screw height error of {sy['height_error_mm']:g} mm "
                  f"({sy['sync']}) alone puts {worst_block:.0f} N on a guide block and {worst_nut:.0f} N on a nut." + seat_txt
                  + " The deflection figures above assume every nut seated and are then not what the machine does.",
                  joint=j.name, redundant_supports=n_red, height_error_mm=expected["height_error_mm"],
                  nuts_not_seated=expected["worst_case"]["nuts_not_seated"],
                  unseats_on_synchronisation_error_alone=bool(sync_only and sync_only["a_nut_unseats"]),
                  hint="Let one thing hold the tilt: one guide block per rail with three screws (the screws set the plane), or one "
                       "screw with two blocks per rail (the rails set it); or make the nuts carry load both ways without backlash.")
        elif expected is not None and expected["a_nut_unseats"]:
            r.add("warning", "z_nut_unseats",
                  f"Joint {j.name}: on {n_s} lead screws ({sy['sync']}) a nut can lose its load." + seat_txt,
                  joint=j.name, height_error_mm=expected["height_error_mm"], nuts_not_seated=expected["worst_case"]["nuts_not_seated"],
                  hint="Bring the mass centre inside the triangle of the screws with more margin, add weight or a spring on the "
                       "light nut, or use nuts that carry load both ways.")
        if not sy["firmware_can_relevel"] and (worst_t > half or (drive_n and worst_nut > 0.3 * drive_n)):
            r.add("warning", "z_screws_not_levelled",
                  f"Joint {j.name} rides on {n_s} lead screws ({sy['sync']}): {sy['basis']}. On the supports' stiffness that is "
                  f"{worst_t:.3f} mm of tilt across the print area and {worst_block:.0f} N on a guide block, and the firmware cannot "
                  f"take it out ({sy['why_not']}).", joint=j.name, **{k: v for k, v in sy.items() if k != "how"},
                  hint="Declare el.firmware['z_tilt'] = {'z_positions': [...], 'points': [...]} with one driver per Z motor, or tie the "
                       "screws with a closed belt and level the bed mechanically once.")
        else:
            r.add("info", "z_over_constrained" if n_red else "z_several_screws",
                  f"Joint {j.name}: {n_s} lead screws with {rails} guide(s), {out['constraint']['note'].split(': ', 1)[1]}. Screw height error "
                  f"{sy['height_error_mm']:g} mm ({sy['sync']}) gives {worst_t:.3f} mm of tilt across the print area and "
                  f"{worst_block:.0f} N on a guide block; "
                  + ("the firmware re-levels the screws (z_tilt)." if sy["firmware_can_relevel"] else f"not correctable by firmware: {sy['why_not']}.")
                  + ("" if (expected is not None and expected["a_nut_unseats"]) else seat_txt), joint=j.name)
        if lvl.get("from_screw_lead_error_mm") and lvl["from_screw_lead_error_mm"] > half:
            r.add("warning", "bed_level_changes_over_travel",
                  f"Joint {j.name}: the screws' lead error ({lvl['from_screw_lead_error_note']}) changes the bed's level by "
                  f"{lvl['from_screw_lead_error_mm']:.3f} mm across the print area over the travel (limit half a layer).", joint=j.name,
                  hint="Screws cut from one bar of the same lot differ far less than the class limit; a mesh taken at print height "
                       "does not see what accumulates above it.")
    return out
