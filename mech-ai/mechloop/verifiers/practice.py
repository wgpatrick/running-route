"""The practice verifier: the habits an experienced designer applies without thinking, as checkable rules.

Rules and their evidence: docs/PRACTICE_RULES.md (section 5.2 lists the first 25; section 8 says which are implemented,
which are cross-referenced to the verifier that already enforces them, and which are deferred) and
research_notes/practice/rules.yaml. Three more rules are the owner's standing practice (docs/DESIGN_GUIDELINES.md):
DG-01 no 3D-printed part in a load path, DG-02 no tapped thread in aluminium we make (nor in an extrusion end), DG-03 a
machined part with only through-features is a 2D laser-cut candidate, DG-04 no thread in a printed part (through-bolt and
nut; a heat-set insert only with a written reason), DG-05 printed clearance holes at ISO 273 medium plus the FDM allowance.

Measurement is shared with the read-only audit (`mechloop/verifiers/fastener_stack.py`, promoted from
tools/practice_audit.py): point-in-solid probing of the B-rep at the home pose along and round every screw and round
every catalogue ball bearing.

Every finding carries `rule`, `parts`, `value`, `limit`, `evidence` (document / fetched / repo / derived / recalled /
owner), `source` and a one-line `hint`. A rule whose number rests on `recalled` or `derived` evidence is never an error
(a test enforces it).

Control, on the design:
    d.practice = {"disable": ["FST-081"], "severity": {"FST-050": "info"}, "limits": {"FST-050.min_edge_d": 1.2}}
    d.waive("DG-01", "probe_mount", reason="carries only the probe; the toolhead loads go through the tool plate")
A waiver names a rule id or finding code (optionally prefixed "practice."), the parts (fnmatch patterns; None = the
whole design) and a reason. A reason under 20 characters is an error (`waiver_without_reason`); a waiver that
suppresses nothing is a warning (`waiver_unused`). Every waiver in force is listed in the metrics with what it suppressed.
"""
from __future__ import annotations

import collections
import fnmatch
import math
from dataclasses import dataclass

import numpy as np

from ..model import Design
from ..report import VerifierResult, timed
from . import fastener_stack as FS

PLASTICS = ("pla", "petg", "abs", "nylon_pa12")
SEVERITY_RANK = {"info": 0, "warning": 1, "error": 2}
MIN_WAIVER_REASON = 20


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str                 # the most severe level the rule raises
    evidence: str                 # document | fetched | repo | derived | recalled | owner
    source: str
    status: str                   # implemented | xref | deferred
    checked_by: str = ""          # xref: verifier.check that enforces it
    note: str = ""                # deferred: why; implemented: what is and is not covered


RULES: dict[str, Rule] = {r.id: r for r in [
    # ---- implemented here --------------------------------------------------------------------------------------------
    Rule("FST-060", "Nuts and tapped parts sit on the threaded part of a partly threaded screw", "error", "document",
         "ISO 4762 thread length b (Westfield); DIN 912 full-thread rows (Aramfix)", "implemented",
         note="ISO 4762 cap screws; T-nut screws (nut not drawn) and screws declared meta['fully_threaded'] are skipped"),
    Rule("FST-070", "A locking provision that does not depend on preload on moving or vibrating assemblies", "warning",
         "document", "NASA-STD-5020B TFSR 16; NASA RP-1228", "implemented",
         note="moving body or holding a motor; declared by add_screw/add_nut(locking=...) or a join naming a locknut / adhesive"),
    Rule("BLT-010", "At least 6 teeth in mesh on every load-carrying sprocket", "error", "document",
         "Gates GT2 design manual (legacy, 12_Gates_GT2_drive_design.pdf)", "implemented",
         note="every loaded pulley except a joint's drive pulley, which motion.belt_low_wrap already judges"),
    Rule("BLT-011", "At least 60 degrees of wrap on every loaded sprocket", "warning", "document",
         "Gates GT2 design manual (legacy)", "implemented"),
    Rule("BLT-030", "Back-side idlers are flat and uncrowned", "warning", "document",
         "Gates GT2 (legacy) and Light Power and Precision manuals", "implemented"),
    Rule("BLT-031", "Idler diameters", "warning", "document", "Gates table 9 (2MGT GT3); legacy GT2 1.3 x 12-groove rule",
         "implemented"),
    Rule("BLT-040", "Pulley diameter not smaller than the belt width", "warning", "fetched", "SDP/SI belt handbook",
         "implemented"),
    Rule("BRG-020", "Retain the bearing axially on both faces of both rings", "warning", "document",
         "SKF rolling bearings, axial location", "implemented",
         note="something must stand against each face (0.4 mm); whether it is fixed to the right part is not judged"),
    Rule("BRG-023", "Axial load through a shoulder, collar or circlip, not set-screw friction", "warning", "document",
         "SKF; Unbrako / Holo-Krome set-screw holding", "implemented",
         note="flags an inner-ring face whose only abutment is a set-screwed hub on the shaft"),
    Rule("SHF-010", "Set screws bear on a flat and are locked", "warning", "document", "Unbrako; Gates stock pulleys",
         "implemented", note="declare d.join(hub, shaft, 'set_screw on flat, threadlocked') when both are true"),
    Rule("SHF-011", "Never seat a set screw or a bearing on a thread", "warning", "document",
         "SKF js5 / h5 journal; DIN 471 groove", "implemented",
         note="lead screws (T8) without meta['journal'] on the screw part"),
    Rule("FST-051", "A joint needs two fasteners or one plus an anti-rotation feature", "warning", "document",
         "Slocum, Fundamentals of Design", "implemented",
         note="pairs of parts joined by one screw and nothing else; T-nut screws are FST-101's"),
    Rule("FST-101", "A part on T-nuts wants two of them (or a key in the slot)", "warning", "recalled", "practice",
         "implemented"),
    Rule("FST-050", "Edge distance of fastener holes at least 1.5 d", "warning", "fetched",
         "NASA RP-1228 (1.5 d minimum, 2 d nominal); Bossard c = 1.5 d", "implemented"),
    Rule("FST-020", "Clearance holes to ISO 273; choose the class deliberately", "warning", "document",
         "ISO 273 (MMCC table)", "implemented",
         note="under fine in a metal part is a warning; larger than coarse under a bare head is info (the seat itself is ratings' FST-031)"),
    Rule("FST-034", "Leave at least 1 d of floor under a counterbored head", "warning", "document", "Slocum 9-10",
         "implemented"),
    Rule("FST-081", "No look-alike lengths of one size into blind catalogue threads", "warning", "recalled", "practice",
         "implemented"),
    Rule("LOC-006", "Every adjustment has a mover, a lock and access", "warning", "recalled", "practice", "implemented",
         note="mover and lock are read from Adjustment(mover=, lock=); access in the finished machine is not checked; "
              "z_offset (firmware) and float adjustments need no lock"),
    Rule("FST-072", "Nylon-insert lock nuts only below about 120 degC", "warning", "fetched", "NASA RP-1228 (nylon element)",
         "implemented", note="a screw or nut declared nyloc whose stack touches a part with meta['service_temp_c'] over the limit "
                             "(limit 'FST-072.max_temp_c', default 120) or a hotend / heater part"),
    Rule("FST-040", "State a tightening torque for every structural joint", "info", "document",
         "Bossard / VDI 2230 2015 at mu 0.14", "implemented",
         note="with DOC-012: a generated torque and locking table (metrics.practice.torque_table)"),
    Rule("DOC-012", "Torque and threadlocker call-outs in the build instructions", "info", "recalled", "practice",
         "implemented", note="the table is in the metrics; BUILD.md does not yet print it"),
    # ---- the owner's practice (docs/DESIGN_GUIDELINES.md) ------------------------------------------------------------
    Rule("DG-01", "No 3D-printed part in a load path unless waived with a reason", "error", "owner",
         "docs/DESIGN_GUIDELINES.md, Process choice", "implemented",
         note="carries a guide, bearing, lead-screw nut or screw, motor (incl. an extruder), belt tension (pulley, idler, "
              "belt clamp), the bed, or a part declared meta['load_path']; by a shared screw, a declared join or contact. Contact is "
              "not a load path where the clamp goes through a metal sleeve declared in the printed part (a join) and the "
              "printed part touches neither the head nor its washers"),
    Rule("DG-02", "No tapped thread in aluminium we make; no tapped extrusion ends", "warning", "owner",
         "docs/DESIGN_GUIDELINES.md, Fasteners and threads", "implemented",
         note="accepted: a through-bolt and nut, add_screw(insert='steel' | 'pem'), a T-nut"),
    Rule("DG-03", "A machined part with only through-features is a 2D laser-cut candidate", "info", "owner",
         "docs/DESIGN_GUIDELINES.md, Process choice", "implemented",
         note="2.5D profile, no blind pocket, counterbore or countersink, no fitted bore; meta['cnc_reason'] records why not"),
    Rule("DG-04", "No thread in a printed part: through-bolt with nut and washers; heat-set insert only with a reason",
         "error", "owner", "docs/DESIGN_GUIDELINES.md, Fasteners and threads", "implemented",
         note="a screw that threads into a printed part (tapped, self-tapped or a heat-set insert): warning, error when the "
              "joint is in a load path (DG-01's load parts); accepted: add_screw(..., insert=True, insert_reason='...') or a "
              "DG-04 waiver. Covers FST-090 (screws straight into plastic)"),
    Rule("DG-05", "Printed clearance holes: ISO 273 medium plus the FDM allowance", "warning", "owner",
         "docs/DESIGN_GUIDELINES.md, Fasteners and threads; ISO 273 (MMCC)", "implemented",
         note="smallest section of the hole under medium + allowance (0.2 vertical / 0.3 in the build plane, limits "
              "'DG-05.allowance_vertical_mm' / 'DG-05.allowance_in_plane_mm'), or over coarse + 0.4 under a bare head or nut; "
              "the metal-part classes stay FST-020's"),
    Rule("DG-06", "Every fastener is a drawn part: the BOM and the model list the same hardware", "error", "owner",
         "owner's instruction 2026-11-18 ('make sure all fasteners are in place'); docs/DESIGN_GUIDELINES.md, Purchased-part CAD",
         "implemented",
         note="hardware_bom_only: a screw, nut, washer, T-nut, insert or clinch nut that is only a BOM line (design.bom_extra); "
              "hardware_count_mismatch: a hardware SKU whose BOM quantity is not the number of parts drawn; tnut_not_drawn / "
              "tnut_without_screw: a tnut=True screw without its T-nut part, or the reverse; joint_without_fasteners: a declared "
              "join whose kind names a fastener (m5_tnut, through_bolt, bolted...) with no drawn fastener holding both parts. "
              "Set screws inside a bought pulley's hub are listed (metrics), not required as parts"),
    # ---- enforced by another verifier: cross-referenced, not duplicated ------------------------------------------------
    Rule("FST-031", "Washer under any head or nut on a slot or oversize hole", "warning", "document", "ISO 7089 / 7093",
         "xref", "ratings.head_bearing (screw_head_seat_too_small)"),
    Rule("PRT-030", "No preloaded seat on printed plastic without washer and sleeve", "warning", "derived",
         "derived limit 5 MPa", "xref", "ratings.head_bearing (screw_head_bearing_pressure, printed seats)"),
    Rule("FST-030", "Head and nut pressure under the seat's limiting surface pressure", "warning", "document",
         "VDI 2230 2015 via Bossard", "xref", "ratings.head_bearing (screw_head_bearing_pressure, metal seats)"),
    Rule("FST-010", "Thread engagement by tapped material", "error", "document", "Bossard engagement table", "xref",
         "interference.thread_engagement (thread_engagement, thread_engagement_marginal)"),
    Rule("FST-090", "Screws driven straight into printed plastic are for one-time, low-load joints", "warning", "fetched",
         "CNC Kitchen (inserts vs. direct threads)", "xref",
         "practice.DG-04 (thread_in_printed_part); interference.thread_engagement (2 d in plastic)"),
    Rule("FST-012", "Screw shorter than a catalogue part's tapped depth", "error", "repo", "maker drawings", "xref",
         "interference.thread_bottoms_out"),
    Rule("MCH-015", "Break all machined edges", "warning", "recalled", "ISO 13715 notation", "xref",
         "manufacture.edges (edges_not_broken)"),
    Rule("SHT-014", "Deburr / edge-finish note on sheet parts", "warning", "recalled", "practice", "xref",
         "manufacture.edges (edge_break_mm declaration honoured for sheet)"),
    Rule("DOC-010", "Edge-break note on every made metal part", "warning", "document", "ISO 13715", "xref",
         "manufacture.edges (edge_break_mm on the part or design.manufacturing)"),
    Rule("SHT-013", "Round the outside corners of sheet profiles", "warning", "recalled", "practice", "xref",
         "manufacture.edges (sharp_profile_corners)"),
    Rule("BRG-024", "What abuts a bearing ring stays inside that ring's abutment diameters", "warning", "document",
         "SKF 608 product data", "xref", "ratings.ring_abutment (bearing_abutment)"),
    Rule("BRG-022", "Axial load on a small bearing under 0.25 C0", "warning", "document", "SKF", "xref",
         "fea.bed_support (bearing_axial_overload)"),
    Rule("LSC-015", "Several screws on one body: budget their lead difference", "warning", "document",
         "Elesa GN 103; igus DryLin TR", "xref", "fea.bed_support.nut_seating_and_lead_error (z_tilt_over_constrained, z_nut_unseats)"),
    Rule("BLT-010d", "Teeth in mesh on a joint's drive pulley", "error", "document", "Gates", "xref",
         "motion.belt_low_wrap"),
    # ---- deferred -------------------------------------------------------------------------------------------------------
    Rule("BLT-041", "Flanges on belt pulleys", "warning", "fetched", "SDP/SI", "deferred",
         note="every catalogue GT2 pulley and idler is drawn double-flanged, so there is nothing to find until an unflanged part exists"),
    Rule("FST-052", "No sustained shear on screw friction when a stop can carry it", "warning", "fetched", "Bolt Science",
         "deferred", note="needs the service load across each slotted joint (belt pull on a motor mount, etc.), which no design declares"),
    Rule("STR-013", "Friction joints: check slip", "warning", "fetched", "practice", "deferred",
         note="as FST-052: no declared shear load per joint"),
    Rule("FST-100", "T-nut type against assembly order", "error", "recalled", "practice", "xref",
         "interference.tslot_screws (tnut_needs_end_loading) and assemblability (a drawn drop-in T-nut goes in through its "
         "slot's opening only, before what covers it); only in designs with design.tnut_style set"),
    Rule("ASM-030", "Service parts come out without tearing the machine down", "warning", "recalled", "practice",
         "deferred", note="needs a design.service list and a removal-path search like the assembly simulation's"),
]}

LOCKING_WORDS = ("nyloc", "locknut", "lock nut", "prevailing", "all_metal", "all-metal", "adhesive", "threadlock", "loctite",
                 "locked", "locking")
PRELOAD_DEPENDENT = ("serrated", "flange", "jam", "split", "lock_washer", "spring")
SETSCREW_WORDS = ("set_screw", "set screw", "grub")


def _is_leadscrew(c) -> bool:
    return (c.sku or "").startswith("T8x")


class _Ctx:
    def __init__(self, design: Design, r: VerifierResult):
        self.d, self.r = design, r
        self.comps = {c.name: c for c in design.components}
        cfg = design.practice or {}
        self.disabled = set(cfg.get("disable") or [])
        self.sev_over = dict(cfg.get("severity") or {})
        self.limits = dict(cfg.get("limits") or {})
        self.count = collections.Counter()
        self.waivers = [dict(w, suppressed=[]) for w in (design.waivers or [])]
        self.turned = {}
        self.sleeved = {}             # DG-01: printed part -> load part -> the screws whose clamp a metal sleeve carries

    def limit(self, key: str, default: float) -> float:
        return float(self.limits.get(key, default))

    def on(self, rule: str) -> bool:
        return rule not in self.disabled

    def waived(self, rule: str, code: str, parts) -> bool:
        """True (and the waiver records it) when a waiver of this rule / code names any of `parts` (the finding's subject:
        a part, a screw, a bearing, an adjustment), or the whole design."""
        keys = {rule, code, f"practice.{rule}", f"practice.{code}"}
        parts = [p for p in (parts or []) if p]
        for w in self.waivers:
            if w["rule"] not in keys:
                continue
            pats = w.get("parts")
            if pats is None or any(fnmatch.fnmatchcase(p, pat) for p in parts for pat in pats):
                w["suppressed"].append({"rule": rule, "code": code, "parts": parts[:12]})
                return True
        return False

    def flag(self, rule: str, code: str, message: str, parts, value=None, limit=None, unit=None, hint="", severity=None,
             **data) -> None:
        R = RULES[rule]
        sev = severity or R.severity
        if rule in self.sev_over:
            sev = self.sev_over[rule]
        if R.evidence in ("recalled", "derived") and sev == "error":
            sev = "warning"             # a number from memory or our own derivation is never an error
        self.count[rule] += 1
        self.r.add(sev, code, f"{rule}: {message}", rule=rule, parts=list(parts)[:60], value=value, limit=limit,
                   **({"unit": unit} if unit else {}), evidence=R.evidence, source=R.source, hint=hint, **data)


# ------------------------------------------------------------------------------------------------------------------ rules
def _fst060(x: _Ctx, rows):
    for row in rows:
        if row["tnut"] or row["fully_threaded"]:
            continue
        thr0 = row["thread_starts_mm_under_head"]
        if thr0 <= 0:
            continue
        bad = {}
        for e in row["threaded"]:
            if "from_mm" in e and e["from_mm"] < thr0 - 0.3:
                bad[e["into"]] = (e["from_mm"], e["to_mm"])
        for e in row["stack"]:
            if e["role"] == "nut" and e["from_mm"] < thr0 - 0.3 and e["from_mm"] < row["length_mm"]:
                bad.setdefault(e["part"], (e["from_mm"], e["to_mm"]))
        if not bad or x.waived("FST-060", "nut_on_plain_shank", [row["screw"], *bad]):
            continue
        worst = min(v[0] for v in bad.values())
        b = FS.ISO4762_B.get(row["size"])
        on = {n: round(min(thr0, z) - a, 2) for n, (a, z) in bad.items()}
        x.flag("FST-060", "nut_on_plain_shank",
               f"{row['screw']} ({row['sku']}) is threaded only over its last {b:g} mm (ISO 4762: from {thr0:.1f} mm under the head), but "
               + ", ".join(f"{n} sits {a:.1f} to {z:.1f} mm under the head ({'entirely' if z <= thr0 else f'{on[n]:.1f} mm'} on the plain shank)"
                           for n, (a, z) in sorted(bad.items())) + ": it cannot be screwed there.",
               [row["screw"], *sorted(bad)], value=round(worst, 2), limit=round(thr0, 2), unit="mm under the head",
               hint="Use a fully threaded screw (ISO 4017 / DIN 933, or DIN 976 rod with nuts), a length that is fully threaded "
                    "(M3 to 20, M4/M5 to 25 mm), or move the nut past the thread start; a screw you will buy fully threaded: "
                    "screw.meta['fully_threaded'] = True.",
               screw=row["screw"], thread_starts_mm=thr0, on_shank=bad)


def _locked(x: _Ctx, row) -> tuple[bool, str]:
    lk = str(row["locking"] or "").lower()
    plastic = any(x.comps[e["part"]].material in PLASTICS and not x.comps[e["part"]].cots for e in row["stack"]) or \
        any(x.comps[t].material in PLASTICS for t in row["threads_into"])
    cands = [lk] + [str(x.comps[e["part"]].meta.get("locking") or "").lower() for e in row["stack"] if e["role"] == "nut"] + \
            [str(x.comps[t].meta.get("locking") or "").lower() for t in row["threads_into"]]
    for t in [e["part"] for e in row["stack"]] + row["threads_into"]:
        cands.append(str(x.d.joins.get(frozenset((row["screw"], t)), "")).lower())
    cands = [c for c in cands if c]
    if any(any(w in c for w in LOCKING_WORDS) for c in cands):
        return True, ""
    pre = [c for c in cands if any(w in c for w in PRELOAD_DEPENDENT)]
    if pre:
        if plastic:
            return False, f"'{pre[0]}' depends on preload and a printed seat creeps"
        if any(w in pre[0] for w in ("split", "lock_washer", "spring")):
            return False, f"'{pre[0]}': split / spring lock washers give little or no locking (NASA RP-1228, NASA-STD-5020B)"
        return True, ""
    return False, "none declared"


def _fst070(x: _Ctx, rows):
    motors = {c.name for c in x.d.components if (c.sku or "").startswith("NEMA")}
    for j in x.d.joints:
        m = (j.drive or {}).get("motor")
        motors |= set(m if isinstance(m, (list, tuple)) else [m] if m else [])
    by_body = collections.defaultdict(list)
    for row in rows:
        touched = {e["part"] for e in row["stack"]} | set(row["threads_into"])
        moving = row["body"] != "world"
        motor = bool(touched & motors)
        if not (moving or motor):
            continue
        ok, why = _locked(x, row)
        if ok or x.waived("FST-070", "no_locking_feature", [row["screw"]]):
            continue
        by_body[row["body"]].append({"screw": row["screw"], "why": why, "motor": motor})
    nyloc_bom = {k: v["qty"] for k, v in x.d.bom_extras.items() if any(w in k.upper() for w in ("NYLOC", "THREADLOCK", "LOCTITE"))}
    for body, items in sorted(by_body.items()):
        what = "a moving body" if body != "world" else "the frame, holding a motor"
        x.flag("FST-070", "no_locking_feature",
               f"{len(items)} screw(s) on {body} ({what}) have no locking provision that works without preload "
               f"(e.g. {', '.join(i['screw'] for i in items[:5])}{' ...' if len(items) > 5 else ''})"
               + (f"; the BOM's {', '.join(f'{k} x {v}' for k, v in nyloc_bom.items())} are not tied to any screw" if nyloc_bom else "") + ".",
               [i["screw"] for i in items], value=len(items), limit=0, unit="screws without locking",
               hint="Declare it: add_screw(..., locking='nyloc') with add_nut(..., locking='nyloc'), or locking='adhesive' (metal "
                    "threads); serrated flanges and jam nuts depend on preload and are not accepted on printed seats.",
               body=body, screws=items[:80])


def _belts(x: _Ctx):
    from ..geom import forward_kinematics
    from .belts import route

    try:
        T = forward_kinematics(x.d, {})
    except Exception:
        return {}
    drive = {j.drive.get("pulley") for j in x.d.joints if j.drive and j.drive.get("pulley")}
    out = {}
    for b in x.d.belts:
        try:
            rt = route(x.d, b, T)
        except Exception:
            continue
        senses = [n[2] for n in b.path if n[0] == "pulley"]
        cnt = collections.Counter(senses)
        major, nmaj = cnt.most_common(1)[0]
        tie = len(cnt) > 1 and min(cnt.values()) == nmaj
        rows = []
        for node in b.path:
            if node[0] != "pulley" or node[1] not in x.comps:
                continue
            c = x.comps[node[1]]
            sku = c.sku or ""
            teeth, wrap = c.ratings.get("teeth"), rt["wraps_deg"].get(node[1])
            idler = "IDLER" in sku or bool(c.meta.get("idler"))
            smooth = "SMOOTH" in sku or bool(c.meta.get("smooth"))
            backside = (not tie) and node[2] != major
            od = (c.meta.get("interfaces") or {}).get("od") if smooth else c.ratings.get("pitch_diameter_mm", 0) - 0.76
            mesh = wrap * teeth / 360.0 if (wrap is not None and teeth and not smooth) else None
            p = {"part": node[1], "teeth": teeth, "wrap_deg": None if wrap is None else round(wrap, 1),
                 "teeth_in_mesh": None if mesh is None else round(mesh, 2), "idler": idler, "backside": backside,
                 "od_mm": None if od is None else round(od, 2), "drive_pulley": node[1] in drive}
            rows.append(p)
            loaded = not idler
            nm = node[1]
            if loaded and mesh is not None and x.on("BLT-010") and not p["drive_pulley"] and mesh < 6 - 1e-9 \
                    and not x.waived("BLT-010", "pulley_few_teeth", [nm]):
                derate = max(0.0, 1 - 0.2 * (6 - math.floor(mesh + 1e-9)))
                x.flag("BLT-010", "pulley_few_teeth",
                       f"{nm} (belt {b.name}): {mesh:.1f} teeth in mesh at {wrap:.0f} deg of wrap; a load-carrying sprocket wants at "
                       f"least 6 (Gates: the torque rating falls 20 % per missing tooth, x {derate:.1f} here; under 2 it is not rated).",
                       [nm], value=round(mesh, 2), limit=6, unit="teeth in mesh", severity="error" if mesh < 2 else "warning",
                       hint="Move an idler to wrap more of the pulley, or use a larger pulley.", belt=b.name, rating_factor=round(derate, 2))
            if loaded and wrap is not None and x.on("BLT-011") and wrap < 60.0 and not x.waived("BLT-011", "pulley_low_wrap", [nm]):
                x.flag("BLT-011", "pulley_low_wrap", f"{nm} (belt {b.name}): {wrap:.0f} deg of wrap; Gates asks at least 60 deg on a "
                       f"loaded sprocket.", [nm], value=round(wrap, 1), limit=60, unit="deg",
                       hint="Re-route the belt or add an idler so it wraps the pulley further.", belt=b.name)
            if backside and not smooth and x.on("BLT-030") and not x.waived("BLT-030", "toothed_backside_idler", [nm]):
                x.flag("BLT-030", "toothed_backside_idler",
                       f"{nm} (belt {b.name}) runs on the belt's smooth back but is toothed; Gates: back-side idlers flat and uncrowned.",
                       [nm], value="toothed", limit="flat, uncrowned", hint="Use a smooth (flat) idler on the belt's back.", belt=b.name)
            if x.on("BLT-031") and od is not None:
                msg = lim = None
                if backside and od < 12.7 - 1e-6:
                    legacy = 1.3 * 12 * 2.0 / math.pi
                    msg, lim = (f"{nm} (belt {b.name}): back-side idler OD {od:.1f} mm, under the current Gates table's 12.7 mm "
                                + (f"(it meets the legacy GT2 rule, {legacy:.1f} mm)" if od >= legacy else "and under the legacy GT2 rule")), 12.7
                elif idler and not backside and not smooth and teeth and teeth < 12:
                    msg, lim = f"{nm} (belt {b.name}): inside idler with {teeth} grooves, under Gates' 12.", 12
                elif idler and not backside and smooth and od < 25.4 - 1e-6:
                    msg, lim = f"{nm} (belt {b.name}): flat idler on the tooth side, OD {od:.1f} mm, under Gates' 25.4 mm.", 25.4
                if msg and not x.waived("BLT-031", "idler_too_small", [nm]):
                    x.flag("BLT-031", "idler_too_small", msg, [nm], value=round(od, 2) if lim != 12 else teeth, limit=lim,
                           hint="Use a larger idler.", belt=b.name)
            if x.on("BLT-040") and od is not None and od < b.width - 1e-6 and not x.waived("BLT-040", "pulley_narrower_than_belt", [nm]):
                x.flag("BLT-040", "pulley_narrower_than_belt",
                       f"{nm} (belt {b.name}): OD {od:.2f} mm under the belt's width {b.width:g} mm (SDP/SI: tracking and edge wear).",
                       [nm], value=round(od, 2), limit=b.width, unit="mm", hint="A larger pulley or a narrower belt.", belt=b.name)
        out[b.name] = rows
    return out


def _bearings(x: _Ctx, bcs):
    for e in bcs:
        nm = e["bearing"]
        miss = [f"{ring.replace('_', ' ')} {side}" for ring in ("outer_ring", "inner_ring") for side in ("above", "below")
                if not e[ring][side]]
        if miss and x.on("BRG-020") and not x.waived("BRG-020", "bearing_not_retained", [nm]):
            x.flag("BRG-020", "bearing_not_retained",
                   f"{nm}: nothing stands against the {', '.join(miss)} face(s) (no shoulder, circlip, cover or collar within 0.4 mm): "
                   f"an axial force that way moves the bearing.", [nm], value=len(miss), limit=0, unit="free ring faces",
                   hint="A shoulder or cover on the housing side and a collar, circlip or shoulder on the shaft side, on both faces.",
                   free_faces=miss, axis=e["axis"], centre=e["centre"])
        shaft = e["inner_ring"]["shaft"]
        for side in ("above", "below"):
            ab = e["inner_ring"][side]
            if not ab or not shaft or not x.on("BRG-023"):
                continue
            kinds = {a: [str(x.d.joins.get(frozenset((a, s)), "")).lower() for s in shaft] for a in ab}
            hubs = [a for a, ks in kinds.items() if any(any(w in k for w in SETSCREW_WORDS) for k in ks)]
            if hubs and len(hubs) == len(ab) and not x.waived("BRG-023", "axial_load_through_set_screw", [nm, *hubs]):
                x.flag("BRG-023", "axial_load_through_set_screw",
                       f"{nm}: the only thing against its inner ring {side} is {', '.join(hubs)}, held on {', '.join(shaft)} by set-screw "
                       f"friction; axial load in that direction goes through it and slips in service.",
                       [nm, *hubs], value="set-screw friction", limit="shoulder, collar or circlip",
                       hint="Put a clamp collar or a shoulder (journal step) against the inner ring; let the hub only drive.", side=side)
        screws = [s for s in shaft if _is_leadscrew(x.comps[s]) and not x.comps[s].meta.get("journal")]
        if screws and x.on("SHF-011") and not x.waived("SHF-011", "seat_on_thread", [nm, *screws]):
            x.flag("SHF-011", "seat_on_thread",
                   f"{nm} sits on the thread of {', '.join(screws)}: a thread crest is not a bearing seat (SKF asks js5 / h5 on 8 mm).",
                   [nm, *screws], value="thread crests", limit="plain journal js5 / h5",
                   hint="Buy lead screws with machined journal ends (screw.meta['journal'] = True once they are).")


def _set_screws(x: _Ctx):
    for pair, kind in x.d.joins.items():
        k = str(kind).lower()
        if not any(w in k for w in SETSCREW_WORDS):
            continue
        a, b = sorted(pair)
        ca, cb = x.comps.get(a), x.comps.get(b)
        if ca is None or cb is None:
            continue
        shaft, hub = (a, b) if (_is_leadscrew(ca) or (ca.sku or "").startswith(("NEMA", "ROD"))) else (b, a)
        cs = x.comps[shaft]
        if _is_leadscrew(cs) and not cs.meta.get("journal"):
            if x.on("SHF-011") and not x.waived("SHF-011", "seat_on_thread", [hub, shaft]):
                x.flag("SHF-011", "seat_on_thread", f"{hub} is set-screwed onto the thread of {shaft}: the screw bites thread crests "
                       f"(no flat, no repeatable seat; holding on a thread has no data).", [hub, shaft], value="thread",
                       limit="plain journal with a flat", hint="Lead screw with a turned journal end and a flat for the set screw.")
            continue
        flat = "flat" in k or "d-cut" in k or "d_cut" in k or cs.meta.get("shaft_flat")
        locked = any(w in k for w in ("adhesive", "threadlock", "loctite", "locked"))
        miss = [m for m, ok in (("a flat on the shaft", flat), ("thread adhesive", locked)) if not ok]
        if miss and x.on("SHF-010") and not x.waived("SHF-010", "set_screw_without_flat", [hub, shaft]):
            x.flag("SHF-010", "set_screw_without_flat",
                   f"{hub} on {shaft} by set screws: not declared {' or '.join(miss)} (the classic layer-shift failure).",
                   [hub, shaft], value=", ".join(miss) + " missing", limit="on a flat, locked",
                   hint="Seat the set screw on the shaft's flat, threadlock it, and say so: d.join(hub, shaft, 'set_screw on flat, threadlocked').")


AXLE_WORDS = ("axle", "shaft", "pivot", "pin", "runs on", "turns on")


def _turns_on(x: _Ctx, screw: str, part: str) -> bool:
    """The part turns on the screw's shank (an idler, bearing or spacer with a bore, or a declared axle join): the screw is
    its axle, not a fastener holding it (the same test as the tolerance verifier's shaft-in-bore pairs)."""
    if any(w in str(x.d.joins.get(frozenset((screw, part)), "")).lower() for w in AXLE_WORDS):
        return True
    c = x.comps[part]
    return bool(c.cots and not c.meta.get("thread_d") and "bore" in (c.meta.get("interfaces") or {})
                and frozenset((screw, part)) not in x.d.allowed_overlaps and not FS.is_spacer(c))


def _round_about_screw(x: _Ctx, part: str, row) -> bool:
    """A made part that is a solid of revolution about the screw's own axis (a standoff, sleeve or round retainer):
    turning it about the screw changes nothing, so one screw is enough for it."""
    c = x.comps[part]
    if c.cots:
        return False
    if part not in x.turned:
        try:
            from .dfm_geom import turned_axis

            x.turned[part] = turned_axis(c.shape)
        except Exception:
            x.turned[part] = None
    ta = x.turned[part]
    if not ta:
        return False
    o, a = (np.asarray(v, float) for v in ta)
    s = np.asarray(row["axis_towards_head"], float)
    if abs(abs(float(a @ s)) - 1.0) > 1e-3:
        return False
    w = np.asarray(row["under_head"], float) - o
    return float(np.linalg.norm(w - (w @ a) * a)) < 0.1


def _joint_pairs(x: _Ctx, rows):
    pairs = collections.defaultdict(list)
    tn = collections.defaultdict(list)
    tpairs = collections.defaultdict(list)
    for row in rows:
        parts = [p for p in row["joint"] if not _turns_on(x, row["screw"], p)
                 and not (x.comps[p].sku or "").startswith("BRKT")]
        if row["tnut"]:
            ext = [t for t in row["threads_into"] if (x.comps[t].sku or "").startswith("EXT")]
            held = [e["part"] for e in row["stack"] if e["role"] == "clamped" and not (x.comps[e["part"]].sku or "").startswith(("EXT", "BRKT"))
                    and not FS.is_spacer(x.comps[e["part"]]) and not FS.is_washer(x.comps[e["part"]])]
            if ext and held:
                tn[(held[0], ext[0])].append(row["screw"])
                for p in held:          # a T-nut screw is still a second constraint for a pair that also has a tapped screw
                    tpairs[frozenset((p, ext[0]))].append(row["screw"])
            parts = [p for p in parts if p not in ext]
        parts = [p for p in parts if not _round_about_screw(x, p, row)]
        for i, a in enumerate(parts):
            for b in parts[i + 1:]:
                pairs[frozenset((a, b))].append(row["screw"])
    return pairs, tn, tpairs


def _other_join(x: _Ctx, a, b) -> str | None:
    k = x.d.joins.get(frozenset((a, b)))
    if k is None:
        return None
    k = str(k).lower()
    return None if k in ("thread", "tnut", "washer", "m5_tnut") else k     # a screw's own join is not a second constraint


def _fst051_101(x: _Ctx, rows):
    pairs, tn, tpairs = _joint_pairs(x, rows)
    single = []
    for pr, screws in sorted(pairs.items(), key=lambda kv: sorted(kv[0])):
        a, b = sorted(pr)
        if len(screws) != 1 or tpairs.get(pr) or _other_join(x, a, b) or x.waived("FST-051", "single_screw_joint", [a, b]):
            continue
        single.append({"parts": [a, b], "screw": screws[0]})
    if single and x.on("FST-051"):
        x.flag("FST-051", "single_screw_joint",
               f"{len(single)} pair(s) of parts held by one screw and nothing else, which lets them turn about it under vibration: "
               + "; ".join(f"{s['parts'][0]} + {s['parts'][1]} ({s['screw']})" for s in single[:6]) + (" ..." if len(single) > 6 else ""),
               sorted({p for s in single for p in s["parts"]}), value=1, limit=2, unit="screws per joint",
               hint="A second screw, or a pin / key / rib-in-slot declared as a join (d.join(a, b, 'keyed in a slot')).", joints=single[:80])
    one = []
    by_part = collections.defaultdict(list)
    for (held, ext), screws in tn.items():
        by_part[held] += [(ext, s) for s in screws]
    fasteners = {f.name for f in x.d.fasteners}
    for held, lst in sorted(by_part.items()):
        if len(lst) != 1:
            continue        # two T-nuts, in one slot or in two extrusions
        ext, screw = lst[0]
        fixed_elsewhere = any(held in pr for pr in pairs) or any(
            held in pr and not (set(pr) & fasteners) and not any(FS.is_nut(x.comps[q]) for q in pr if q in x.comps)
            and _other_join(x, *sorted(pr)) for pr in x.d.joins)
        if fixed_elsewhere or x.waived("FST-101", "single_tnut", [held]):
            continue
        one.append({"part": held, "extrusion": ext, "screw": screw})
    if one and x.on("FST-101"):
        x.flag("FST-101", "single_tnut",
               f"{len(one)} part(s) held to an extrusion by a single T-nut screw, which pivots and slides: "
               + ", ".join(f"{o['part']} ({o['screw']})" for o in one[:8]) + (" ..." if len(one) > 8 else ""),
               [o["part"] for o in one], value=1, limit=2, unit="T-nuts", hint="Two T-nuts, or a key that rides in the slot.",
               items=one[:80])


def _holes(x: _Ctx, rows):
    k_edge = x.limit("FST-050.min_edge_d", 1.5)
    edge, tight, loose = {}, [], []
    classes = collections.Counter()
    axle = {frozenset(p) for p, k in x.d.joins.items() if any(w in str(k).lower() for w in AXLE_WORDS)}
    for row in rows:
        d = row["d"]
        for i, e in enumerate(row["stack"]):
            if e["role"] != "clamped":
                continue
            c = x.comps[e["part"]]
            if c.cots:
                continue
            if e.get("iso273"):
                classes[f"{row['size']} {e['iso273']}"] += 1
            if e.get("edge_mm") is not None and e["edge_mm"] < k_edge * d - 0.26:
                w = edge.get(e["part"])
                if w is None or e["edge_mm"] < w["edge_mm"]:
                    edge[e["part"]] = {"part": e["part"], "screw": row["screw"], "edge_mm": e["edge_mm"], "edge_d": round(e["edge_mm"] / d, 2),
                                       "limit_mm": round(k_edge * d, 2)}
                edge[e["part"]]["holes"] = edge[e["part"]].get("holes", 0) + 1
            if e.get("iso273") == "tighter than fine" and c.material not in PLASTICS and frozenset((row["screw"], e["part"])) not in axle:
                tight.append({"part": e["part"], "screw": row["screw"], "hole_mm": e["hole_mm"], "fine_mm": FS.ISO273[row["size"]][0]})
            if e.get("iso273") == "larger than coarse" and i == 0 and not _printed(c):     # printed holes: DG-05
                loose.append({"part": e["part"], "screw": row["screw"], "hole_mm": e["hole_mm"], "coarse_mm": FS.ISO273[row["size"]][2]})
    items = [v for v in sorted(edge.values(), key=lambda v: v["edge_d"]) if not x.waived("FST-050", "hole_near_edge", [v["part"]])]
    if items and x.on("FST-050"):
        w = items[0]
        x.flag("FST-050", "hole_near_edge",
               f"{len(items)} part(s) have fastener holes closer than {k_edge:g} d to an edge or cut-out; worst {w['part']} "
               f"({w['screw']}): {w['edge_mm']:.1f} mm = {w['edge_d']:.2f} d. Others: "
               + ", ".join(f"{v['part']} {v['edge_d']:.2f} d" for v in items[1:8]) + (" ..." if len(items) > 8 else ""),
               [v["part"] for v in items], value=w["edge_d"], limit=k_edge, unit="d (hole centre to edge)",
               hint="Move the hole in or the edge out to 1.5 d (2 d nominal); M5: 7.5 mm, M3: 4.5 mm.", items=items[:80])
    tight = [t for t in tight if not x.waived("FST-020", "hole_under_fine", [t["part"]])]
    if tight and x.on("FST-020"):
        x.flag("FST-020", "hole_under_fine",
               f"{len(tight)} clearance hole(s) in metal parts are under ISO 273 fine, e.g. {tight[0]['part']} {tight[0]['hole_mm']} mm for "
               f"{tight[0]['screw']} (fine {tight[0]['fine_mm']} mm).", sorted({t["part"] for t in tight}),
               value=tight[0]["hole_mm"], limit=tight[0]["fine_mm"], unit="mm", hint="Open the hole to medium (M3 3.4, M5 5.5).",
               items=tight[:80])
    loose = [t for t in loose if not x.waived("FST-020", "hole_over_coarse", [t["part"]])]
    if loose and x.on("FST-020"):
        x.flag("FST-020", "hole_over_coarse",
               f"{len(loose)} hole(s) under a head are larger than ISO 273 coarse, e.g. {loose[0]['part']} {loose[0]['hole_mm']} mm for "
               f"{loose[0]['screw']}: a washer belongs there; whether the head's seat is enough is ratings' FST-031 check.",
               sorted({t["part"] for t in loose}), value=loose[0]["hole_mm"], limit=loose[0]["coarse_mm"], unit="mm", severity="info",
               hint="A washer (add_screw(..., washer=True)) or a smaller hole.", items=loose[:80])
    return dict(sorted(classes.items()))


def _fst034(x: _Ctx, rows):
    items = []
    for row in rows:
        h = row["head"]
        if not h or not h["counterbored"] or h["hole_mm"] is None:
            continue
        c = x.comps[h["on"]]
        if c.cots or c.material in PLASTICS or h["thickness_mm"] >= row["d"] - 0.05:
            continue
        if x.waived("FST-034", "counterbore_floor_thin", [h["on"]]):
            continue
        items.append({"part": h["on"], "screw": row["screw"], "floor_mm": h["thickness_mm"], "floor_d": round(h["thickness_mm"] / row["d"], 2)})
    if items and x.on("FST-034"):
        items.sort(key=lambda i: i["floor_d"])
        w = items[0]
        x.flag("FST-034", "counterbore_floor_thin",
               f"{len(items)} counterbored head(s) sit on a floor thinner than 1 d; worst {w['part']} under {w['screw']}: "
               f"{w['floor_mm']:.1f} mm = {w['floor_d']:.2f} d (Slocum: typically 1 to 3 d).",
               sorted({i["part"] for i in items}), value=w["floor_d"], limit=1.0, unit="d",
               hint="A shallower counterbore (head proud, or a thicker part), or a washer in a wider counterbore.", items=items[:80])


def _fst081(x: _Ctx, rows):
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for row in rows:
        for t in row["threads_into"]:
            c = x.comps[t]
            depth = (c.meta.get("interfaces") or {}).get("thread_depth")
            if c.cots and depth and not FS.is_nut(c):
                groups[(row["size"], c.sku, float(depth))][row["length_mm"]].append(row["screw"])
    for (size, sku, depth), by_len in sorted(groups.items()):
        lens = sorted(by_len)
        close = [(a, b) for a, b in zip(lens, lens[1:]) if b - a <= 2.0 + 1e-9]
        if not close:
            continue
        screws = [s for L in lens for s in by_len[L]]
        if x.waived("FST-081", "lookalike_screw_lengths", screws) or not x.on("FST-081"):
            continue
        a, b = close[0]
        x.flag("FST-081", "lookalike_screw_lengths",
               f"{size} x {a:g} ({len(by_len[a])}) and {size} x {b:g} ({len(by_len[b])}) both thread into {sku} blind threads "
               f"({depth:g} mm deep): "
               f"a {b - a:g} mm difference is easy to mix up, and the longer one bottoms out where the shorter is needed.",
               screws, value=b - a, limit="> 2 mm apart, or one length", unit="mm",
               hint="Use one length into these parts, or key them apart (different size or head).",
               lengths={f"{L:g}": by_len[L][:30] for L in lens})


def _loc006(x: _Ctx):
    items = []
    for a in x.d.adjustments:
        if a.kind in ("z_offset", "float"):
            continue
        if not getattr(a, "lock", None) and not x.waived("LOC-006", "adjustment_without_lock", [a.name]):
            items.append({"adjustment": a.name, "kind": a.kind, "mover": getattr(a, "mover", "") or None})
    if items and x.on("LOC-006"):
        x.flag("LOC-006", "adjustment_without_lock",
               f"{len(items)} adjustment(s) name no lock: " + "; ".join(i["adjustment"] for i in items[:6]) + (" ..." if len(items) > 6 else ""),
               [i["adjustment"] for i in items], value=len(items), limit=0, unit="adjustments without a lock",
               hint="Adjustment(..., mover='M3 jack screw', lock='two M3 screws, threadlocked'); a lock that does not disturb the setting.",
               items=items)


def _torque_table(x: _Ctx, rows):
    from .bearing import PLASTICS as BP
    from .bearing import torque_for

    table = collections.defaultdict(lambda: {"screws": 0, "locking_declared": 0})
    undeclared = 0
    for row in rows:
        c = x.comps[row["screw"]]
        soft = any(x.comps[e["part"]].material in BP and not x.comps[e["part"]].cots for e in row["stack"]) or \
            any(x.comps[t].material in BP for t in row["threads_into"])
        t, basis = torque_for(x.d, c, row["size"], soft)
        declared = c.meta.get("torque_nm") is not None or row["size"] in ((x.d.manufacturing or {}).get("tightening_torque_nm") or {})
        undeclared += 0 if declared else 1
        key = (row["size"], "printed seat or thread" if soft else "metal only", t)
        e = table[key]
        e.update({"size": row["size"], "seat": key[1], "torque_nm": t, "basis": basis})
        e["screws"] += 1
        e["locking_declared"] += bool(_locked(x, row)[0])
    rows_out = sorted(table.values(), key=lambda e: (e["size"], e["seat"]))
    if rows and undeclared and x.on("FST-040"):
        x.flag("FST-040", "torque_not_stated",
               f"{undeclared} of {len(rows)} screws have no stated tightening torque; the generated table (metrics.practice.torque_table) "
               f"gives Bossard's class 8.8 maximum at mu 0.14 for metal joints and the assumed torque for printed seats "
               f"(ratings.head_bearing gives each printed seat's own limit).", [], value=undeclared, limit=0, unit="screws",
               hint="d.manufacturing['tightening_torque_nm'] = {'M3': 1.0, ...} or meta['torque_nm'] on a screw; print the table in BUILD.md.",
               table=rows_out)
    return rows_out


# ---------------------------------------------------------------------------------------------------- owner's rules
def _load_kinds(x: _Ctx) -> dict:
    d = x.d
    nuts, screws, motors = set(), set(), set()
    for j in d.joints:
        dr = j.drive or {}
        for key, s in (("nut", nuts), ("screw", screws), ("motor", motors)):
            v = dr.get(key)
            s |= set(v if isinstance(v, (list, tuple)) else [v] if v else [])
    bed = (d.printer or {}).get("bed")
    out = {}
    for c in d.components:
        sku = c.sku or ""
        kind = None
        if c.name == bed:
            kind = "the bed's weight"
        elif sku.startswith("BRG-"):
            kind = "a bearing"
        elif sku.startswith("MGN12") or (c.meta.get("guides") and not sku.startswith("T8")):
            kind = "a linear guide"
        elif c.name in nuts or sku.startswith("T8-NUT"):
            kind = "a lead-screw nut"
        elif c.name in screws or _is_leadscrew(c):
            kind = "a lead screw"
        elif c.name in motors or sku.startswith("NEMA"):
            kind = "a motor"
        elif sku.startswith("EXTRUDER"):
            kind = "the extruder (its motor and drive)"
        elif sku.startswith("GT2"):
            kind = "a belt pulley or idler (belt tension)"
        elif c.meta.get("load_path"):
            kind = "a part declared in the load path"
        if kind:
            out[c.name] = kind
    return out


def _dg01(x: _Ctx, rows):
    from ..tolerance.process import process_of

    printed = [c for c in x.d.components if not c.cots and _proc(c, process_of) == "printed"]
    if not printed:
        return []
    loads = _load_kinds(x)
    fasteners = {f.name for f in x.d.fasteners}
    links = collections.defaultdict(lambda: collections.defaultdict(set))   # printed -> load part -> how
    pset = {c.name for c in printed}
    carriers = collections.defaultdict(set)          # a made, non-printed part -> the load parts it holds directly
    row_parts = {}
    for row in rows:
        parts = {n for n in row["held"] if not FS.is_washer(x.comps[n])}
        row_parts[row["screw"]] = parts
        for p in parts & pset:
            for q in parts:
                if q in loads and q != p:
                    links[p][q].add(f"screw {row['screw']}")
        for q in parts - pset:
            if q not in loads:
                carriers[q] |= {l for l in parts if l in loads}
    for pair, kind in x.d.joins.items():
        a_b = sorted(pair)
        if len(a_b) != 2 or any(n in fasteners for n in a_b):
            continue
        for p, q in (a_b, a_b[::-1]):
            if p in pset and q in loads:
                links[p][q].add(f"join '{kind}'")
            elif p not in pset and p not in loads and q in loads:
                carriers[p].add(q)
    for row in rows:                                  # a jack screw held in a printed block, its tip pushing a loaded part
        for t in row.get("tip_on") or []:
            held = ({t} if t in loads else set()) | carriers.get(t, set())
            for p in row_parts[row["screw"]] & pset:
                for q in held:
                    links[p][q].add(f"jack screw {row['screw']} pushing {t}")
    from build123d import Vertex

    from ..geom import bboxes_overlap
    for c in printed:
        for q in loads:
            if q in links[c.name] or q == c.name:
                continue
            qc = x.comps[q]
            if not bboxes_overlap(c.shape, qc.shape, 0.05):
                continue
            try:
                touching = c.shape.distance_to(qc.shape) < 0.05
            except Exception:
                continue
            if not touching:
                continue
            via = _sleeves_carry(x, c.name, q, rows)
            if via:
                x.sleeved.setdefault(c.name, {})[q] = via
                continue
            links[c.name][q].add("contact")
    for b in x.d.belts:
        for node in b.path:
            if node[0] != "anchor":
                continue
            v = Vertex(*node[2])
            for c in printed:
                if c.body == node[1]:
                    try:
                        if c.shape.distance_to(v) <= 3.0:
                            links[c.name][f"belt {b.name} end"].add("belt clamp")
                    except Exception:
                        continue
    flagged = []
    for c in printed:
        carried = links.get(c.name)
        if not carried:
            continue
        what = sorted({loads.get(q, "belt tension (a belt end is clamped on it)") for q in carried})
        if x.waived("DG-01", "printed_load_path", [c.name]) or not x.on("DG-01"):
            continue
        via = {q: sorted(h)[:4] for q, h in sorted(carried.items())}
        flagged.append(c.name)
        x.flag("DG-01", "printed_load_path",
               f"{c.name} ({c.material}, printed) carries {', '.join(what)}: "
               + "; ".join(f"{q} by {', '.join(h)}" for q, h in list(via.items())[:5]) + (" ..." if len(via) > 5 else "")
               + ". The owner's practice keeps printing to light, non-load-bearing parts.",
               [c.name, *list(via)[:20]], value=what, limit="no load path (sensor holders, ducts, clips, covers only)",
               hint=f"Make it a laser-cut or machined aluminium part (two or three stacked plates where it is a block), or declare "
                    f"the exception: d.waive('DG-01', '{c.name}', reason='...').", part=c.name, carries=via)
    return flagged


METALS_PREFIX = ("al", "steel", "stainless", "brass", "bronze")


def _printed(c) -> bool:
    from ..tolerance.process import process_of

    return not c.cots and _proc(c, process_of) == "printed"


def _sleeves_carry(x: _Ctx, p: str, q: str, rows) -> list:
    """DG-01: printed part p touches load part q, but the screws that clamp q next to p pass through metal sleeves
    (compression limiters) declared in p (a join between sleeve and p), the head bears on the sleeve (directly or
    through washers), and p touches neither the head nor those washers: the clamp load goes through the metal, and p is
    only located on it. Returns [{screw, sleeve}] when that holds for at least one screw and p is clamped by none; [] when
    p is clamped by a screw that holds q, or no declared sleeve is found."""
    from ..geom import bboxes_overlap

    P = x.comps[p]
    out = []
    for row in rows:
        if q not in row["held"]:
            continue
        if p in row["held"] or any(e["part"] == p for e in row["stack"]):
            return []
        sl = [e for e in row["stack"] if e["role"] == "clamped" and FS.is_spacer(x.comps[e["part"]])
              and str(x.comps[e["part"]].material).startswith(METALS_PREFIX) and frozenset((e["part"], p)) in x.d.joins]
        head_chain = [row["screw"]]
        if sl:
            before = [e["part"] for e in row["stack"] if e["from_mm"] < sl[0]["from_mm"] - 1e-6]
            if any(not FS.is_washer(x.comps[n]) for n in before):
                sl = []
            head_chain += before
        for n in head_chain:          # p under the head or its washer: p is in the clamp, whatever the sleeve does
            o = x.comps[n]
            try:
                if bboxes_overlap(P.shape, o.shape, 0.05) and P.shape.distance_to(o.shape) < 0.05:
                    return []
            except Exception:
                return []
        if sl:
            out.append({"screw": row["screw"], "sleeve": sl[0]["part"], "sleeve_length_mm": sl[0]["thickness_mm"]})
    return out


def _dg04(x: _Ctx, rows, flagged_dg01):
    """Screws that thread into a printed part: tapped, self-tapped or into a heat-set insert (FST-090's case)."""
    loads = _load_kinds(x)
    per_part = collections.defaultdict(list)
    accepted = []
    for row in rows:
        if row["tnut"]:
            continue
        for t in row["threads_into"]:
            c = x.comps[t]
            if FS.is_nut(c) or not _printed(c):
                continue
            reason = str(x.comps[row["screw"]].meta.get("insert_reason") or "").strip()
            if row["heatset_insert"] and len(reason) >= MIN_WAIVER_REASON:
                accepted.append({"screw": row["screw"], "part": t, "insert_reason": reason})
                continue
            load = sorted({loads[n] for n in row["joint"] if n != t and n in loads})
            per_part[t].append({"screw": row["screw"], "kind": "heat-set insert" if row["heatset_insert"] else "thread in the plastic",
                                "load_path": bool(load or t in flagged_dg01), "loads": load,
                                **({"insert_reason_too_short": reason} if reason else {})})
    if x.on("DG-04"):
        for part, items in sorted(per_part.items()):
            if x.waived("DG-04", "thread_in_printed_part", [part]):
                continue
            in_load = [i for i in items if i["load_path"]]
            kinds = sorted({i["kind"] for i in items})
            x.flag("DG-04", "thread_in_printed_part",
                   f"{part} (printed) takes {len(items)} screw(s) threaded into it ({', '.join(kinds)}: "
                   f"{', '.join(i['screw'] for i in items[:6])}{' ...' if len(items) > 6 else ''})"
                   + (f", {len(in_load)} of them in a load path ({', '.join(sorted({l for i in in_load for l in i['loads']}) or ['the part is in DG-01'])})" if in_load else "")
                   + ". The owner's practice: through-bolt with a nut and washers; no thread in plastic (FST-090).",
                   [part, *[i["screw"] for i in items][:40]], value=len(items), limit=0, unit="threads in a printed part",
                   severity="error" if in_load else "warning",
                   hint="Through-bolt: clearance hole at printed_clearance_hole(size), washer under head and nut, nyloc nut on the "
                        "side with access; no access: a nut captured in a printed pocket or a PEM stud in the metal part; a "
                        "heat-set insert only with add_screw(..., insert=True, insert_reason='...').",
                   part=part, screws=items[:80], see_also=["FST-090", "FST-010"])
    return {"threads": {p: [i["screw"] for i in v] for p, v in sorted(per_part.items())}, "accepted_inserts": accepted}


def _up_vector(c):
    up = c.meta.get("print_up") or (c.meta.get("print") or {}).get("orientation")
    if not isinstance(up, str) or len(up) != 2 or up[0] not in "+-" or up[1].upper() not in "XYZ":
        return None
    v = np.zeros(3)
    v["XYZ".index(up[1].upper())] = 1.0 if up[0] == "+" else -1.0
    return v


def _dg05(x: _Ctx, rows, pr):
    """Printed clearance holes against ISO 273 medium + the FDM allowance; oversize ones under a bare head or nut."""
    av = x.limit("DG-05.allowance_vertical_mm", 0.2)
    ah = x.limit("DG-05.allowance_in_plane_mm", 0.3)
    small, big, seen = [], [], []
    for row in rows:
        size = row["size"]
        if size not in FS.ISO273:
            continue
        a = np.asarray(row["axis_towards_head"], float)
        _, u, v = FS.frame(a)
        under, tdir, L, d = np.asarray(row["under_head"], float), -a, row["length_mm"], row["d"]
        stack = sorted(row["stack"], key=lambda e: e["from_mm"])
        for i, e in enumerate(stack):
            c = x.comps[e["part"]]
            if e["role"] != "clamped" or not _printed(c):
                continue
            lo, hi = e["from_mm"] + 0.15, min(e["to_mm"], L) - 0.15
            best = None
            for s_ in np.arange(lo, max(hi, lo) + 1e-9, 0.5):       # the narrowest closed section is the clearance hole
                h = FS.hole(pr, e["part"], under + tdir * s_, u, v, d)
                if h.get("hole_mm") is None or h.get("slot"):
                    continue
                best = h["hole_mm"] if best is None else min(best, h["hole_mm"])
            if best is None:
                continue
            up = _up_vector(c)
            in_plane = up is not None and abs(float(up @ a)) < 0.5
            allow = ah if in_plane else av
            fine, med, coarse = FS.ISO273[size]
            item = {"part": e["part"], "screw": row["screw"], "hole_mm": best, "orientation": "in the build plane" if in_plane else
                    ("vertical" if up is not None else "vertical (assumed: no print_up)"), "allowance_mm": allow,
                    "min_mm": round(med + allow, 2), "max_bare_mm": round(coarse + 0.4, 2)}
            seen.append(item)
            if best < med + allow - 0.02:
                small.append(item)
            elif best > coarse + 0.4 + 0.02:
                prev = stack[i - 1] if i else None
                nxt = stack[i + 1] if i + 1 < len(stack) else None
                bare_head = i == 0 and e["from_mm"] < 0.5
                bare_nut = any(n is not None and n["role"] == "nut" and abs(n["from_mm"] - (e["to_mm"] if n is nxt else e["from_mm"])) < 0.6
                               for n in (prev, nxt))
                if bare_head or bare_nut:
                    big.append(dict(item, under="head" if bare_head else "nut"))
    if x.on("DG-05"):
        small = [t for t in small if not x.waived("DG-05", "printed_hole_too_small", [t["part"]])]
        if small:
            w = min(small, key=lambda t: t["hole_mm"] - t["min_mm"])
            x.flag("DG-05", "printed_hole_too_small",
                   f"{len(small)} clearance hole(s) in printed parts are drawn under ISO 273 medium plus the FDM allowance, e.g. "
                   f"{w['part']} {w['hole_mm']} mm for {w['screw']} ({w['orientation']}: at least {w['min_mm']} mm); vertical holes "
                   f"print about 0.2 to 0.3 mm small, so the screw binds or the hole needs drilling.",
                   sorted({t["part"] for t in small}), value=w["hole_mm"], limit=w["min_mm"], unit="mm",
                   hint="Draw printed_clearance_hole(size) (M3 3.6, M5 5.7; +0.1 more and a teardrop for a hole in the build "
                        "plane); calibrate the allowance with a coupon on the printer.", items=small[:80], see_also=["FST-020"])
        big = [t for t in big if not x.waived("DG-05", "printed_hole_oversize_no_washer", [t["part"]])]
        if big:
            w = max(big, key=lambda t: t["hole_mm"])
            x.flag("DG-05", "printed_hole_oversize_no_washer",
                   f"{len(big)} clearance hole(s) in printed parts are larger than ISO 273 coarse + 0.4 mm under a bare {w['under']}, "
                   f"e.g. {w['part']} {w['hole_mm']} mm for {w['screw']} (over {w['max_bare_mm']} mm): the head or nut sinks into the plastic.",
                   sorted({t["part"] for t in big}), value=w["hole_mm"], limit=w["max_bare_mm"], unit="mm",
                   hint="A washer under the head and the nut (add_screw(..., washer=True), add_washer), or a smaller hole.",
                   items=big[:80], see_also=["FST-020", "FST-031", "PRT-030"])
    return seen


def _fst072(x: _Ctx, rows):
    lim = x.limit("FST-072.max_temp_c", 120.0)
    items = []
    for row in rows:
        lk = [str(row["locking"] or "").lower()] + [str(x.comps[e["part"]].meta.get("locking") or "").lower()
                                                    for e in row["stack"] if e["role"] == "nut"]
        if not any("nyloc" in k or "nylon" in k for k in lk):
            continue
        parts = [e["part"] for e in row["stack"]] + list(row["threads_into"])
        temps = [(float(x.comps[n].meta["service_temp_c"]), n) for n in parts if x.comps[n].meta.get("service_temp_c") is not None]
        hot = [n for n in parts if (x.comps[n].sku or "").startswith(("HOTEND", "HEATER", "BED-HEATER"))]
        t = max(temps) if temps else None
        if hot or (t and t[0] > lim):
            if not x.waived("FST-072", "nyloc_too_hot", [row["screw"]]):
                items.append({"screw": row["screw"], "temp_c": t[0] if t else None, "part": (hot or [t[1]])[0]})
    if items and x.on("FST-072"):
        w = items[0]
        x.flag("FST-072", "nyloc_too_hot",
               f"{len(items)} nylon-insert lock nut(s) sit on parts hotter than {lim:g} degC or on a heater, e.g. {w['screw']} on {w['part']}"
               + (f" ({w['temp_c']:g} degC)" if w["temp_c"] is not None else "") + ".",
               [i["screw"] for i in items], value=w["temp_c"], limit=lim, unit="degC",
               hint="An all-metal lock nut (ISO 7042 / DIN 980) or a thread adhesive rated for the temperature.", items=items[:80])
    return {"nyloc_screws": sum(any("nyloc" in str(k).lower() for k in [row["locking"]] + [x.comps[e["part"]].meta.get("locking")
                                                                                       for e in row["stack"] if e["role"] == "nut"]) for row in rows),
            "too_hot": items}


def _proc(c, process_of):
    try:
        return process_of(c)
    except Exception:
        return None


def _dg02(x: _Ctx, rows):
    from ..tolerance.process import process_of

    per_part, ext = collections.defaultdict(list), []
    for row in rows:
        if row["tnut"]:
            continue
        for t in row["threads_into"]:
            c = x.comps[t]
            if FS.is_nut(c):
                continue
            if c.cots and (c.sku or "").startswith("EXT20"):
                ext.append({"screw": row["screw"], "extrusion": t})
            elif not c.cots and c.material.startswith("al") and _proc(c, process_of) in ("sheet", "machined") \
                    and not row["thread_insert"]:
                per_part[t].append(row["screw"])
    if x.on("DG-02"):
        for part, screws in sorted(per_part.items()):
            if x.waived("DG-02", "tapped_aluminium", [part]):
                continue
            c = x.comps[part]
            x.flag("DG-02", "tapped_aluminium",
                   f"{part} ({c.material}, {_proc(c, process_of)}) is tapped for {len(screws)} screw(s) ({', '.join(screws[:6])}"
                   f"{' ...' if len(screws) > 6 else ''}): threads in aluminium we make strip easily.",
                   [part, *screws[:40]], value=len(screws), limit=0, unit="tapped holes",
                   hint="Through-bolt with nut and washer; a PEM self-clinching nut in sheet (add_screw(..., insert='pem')); a steel "
                        "thread insert in thick aluminium (insert='steel').", part=part, screws=screws[:80])
        ext = [e for e in ext if not x.waived("DG-02", "tapped_extrusion_end", [e["extrusion"]])]
        if ext:
            x.flag("DG-02", "tapped_extrusion_end",
                   f"{len(ext)} screw(s) thread into tapped 2020 extrusion ends: " + ", ".join(f"{e['screw']} -> {e['extrusion']}" for e in ext[:6])
                   + (" ..." if len(ext) > 6 else "") + ".", sorted({e["extrusion"] for e in ext}) + [e["screw"] for e in ext][:40],
                   value=len(ext), limit=0, unit="tapped extrusion ends",
                   hint="Use corner brackets or T-nut fixings (add_corner_bracket, add_screw(..., tnut=True)).", items=ext[:80])


def _fit_bores(x: _Ctx, c) -> list:
    """Bores of part c that a shaft, bearing or pin of another (non-screw) part sits in, coaxial and within 0.26 mm in
    radius: a toleranced bore, a reason for machining."""
    from ..geom import bboxes_overlap
    from ..tolerance.fits import _cylinders

    fasteners = {f.name for f in x.d.fasteners}
    own = [b for b in _cylinders(c.shape) if not b["shaft"] and b["len"] >= 1.5]
    if not own:
        return []
    out = []
    for o in x.d.components:
        if o.name == c.name or o.name in fasteners or not bboxes_overlap(c.shape, o.shape, 0.05):
            continue
        for S in _cylinders(o.shape):
            if not S["shaft"] or S["len"] < 1.5:
                continue
            for B in own:
                if abs(B["r"] - S["r"]) > 0.26 or abs(abs(S["d"] @ B["d"]) - 1) > 1e-3:
                    continue
                off = (B["p"] - S["p"]) - ((B["p"] - S["p"]) @ S["d"]) * S["d"]
                if np.linalg.norm(off) <= 0.05:
                    out.append({"with": o.name, "dia": round(2 * B["r"], 2)})
                    break
    for pair, kind in x.d.joins.items():
        if c.name in pair and any(w in str(kind).lower() for w in ("press", "interference", "fit")):
            out.append({"with": next(iter(pair - {c.name}), c.name), "join": str(kind)})
    return out


def _dg03(x: _Ctx):
    from ..tolerance.process import process_of
    from . import dfm_geom as G
    from .dfm_sheet import plate_of

    out = []
    for c in x.d.components:
        if c.cots or c.material in PLASTICS or _proc(c, process_of) != "machined":
            continue
        reason = c.meta.get("cnc_reason")
        if reason:
            out.append({"part": c.name, "candidate": None, "cnc_reason": reason})
            continue
        try:
            frame = G.part_frame(c.shape)
            sm = G.sample_surface(c.shape)
            if G.turned_axis(c.shape):
                out.append({"part": c.name, "candidate": False, "why": "turned part"})
                continue
            plate = plate_of(c.shape, frame, sm)
        except Exception as e:
            out.append({"part": c.name, "candidate": None, "why": f"not measured: {type(e).__name__}"})
            continue
        if plate is None:
            out.append({"part": c.name, "candidate": False, "why": "3D form (not a plate)"})
            continue
        if plate["steps"] or plate["countersinks"]:
            out.append({"part": c.name, "candidate": False, "why": f"{len(plate['steps'])} blind level(s), {plate['countersinks']} countersink(s)"})
            continue
        fits = _fit_bores(x, c)
        if fits:
            out.append({"part": c.name, "candidate": False, "why": "fitted bore(s)", "fits": fits[:6]})
            continue
        out.append({"part": c.name, "candidate": True, "thickness_mm": round(plate["thickness"], 2)})
        if x.on("DG-03") and not x.waived("DG-03", "cnc_2d_candidate", [c.name]):
            x.flag("DG-03", "cnc_2d_candidate",
                   f"{c.name} is machined but every feature goes straight through a {plate['thickness']:.1f} mm plate (no blind pocket, "
                   f"counterbore, countersink or fitted bore): a laser-cut plate costs about a tenth.",
                   [c.name], value="through-features only", limit="a CNC reason: precise bore, 3D pocket, flatness-critical face",
                   hint=f"Make it process='sheet' (SendCutSend), or record why it must be machined: meta['cnc_reason'] = '...'.",
                   part=c.name, thickness_mm=round(plate["thickness"], 2))
    return out


# ---------------------------------------------------------------------------------------------------------- the verifier
HARDWARE_SKU = ("SHCS", "FHCS", "NUT-", "NUT_", "WASHER", "TNUT", "NYLOC", "PEM", "INSERT", "STUD", "SETSCREW", "RIVET")
FASTENED_KIND = __import__("re").compile(r"(^|[^a-z0-9])m\d+(\.\d+)?[ _x-]|tnut|t-nut|through[_ ]bolt|bolted|screwed|riveted")


def _is_hardware_sku(sku: str) -> bool:
    return (sku or "").upper().startswith(HARDWARE_SKU)


def _dg06(x: _Ctx):
    """Completeness of the hardware: BOM-only lines, BOM quantity against parts drawn, T-nuts against their screws, and
    declared joins that name a fastener against the fasteners drawn."""
    d = x.d
    drawn = collections.Counter(c.sku for c in d.components if _is_hardware_sku(c.sku))
    bom_only = {sku: int(e.get("qty", 0)) for sku, e in (d.bom_extras or {}).items() if _is_hardware_sku(sku)}
    for sku, qty in sorted(bom_only.items()):
        base = sku.split(" ")[0]
        if drawn.get(base):
            if not x.waived("DG-06", "hardware_count_mismatch", [base]):
                x.flag("DG-06", "hardware_count_mismatch",
                       f"{base}: the BOM lists {drawn[base] + qty} ({qty} of them as a BOM-only line '{sku}') but {drawn[base]} are drawn.",
                       [base], value=drawn[base], limit=drawn[base] + qty,
                       hint="Draw the missing ones (add_screw / add_nut / add_washer) or remove the extra BOM line.")
        elif not x.waived("DG-06", "hardware_bom_only", [base]):
            x.flag("DG-06", "hardware_bom_only",
                   f"{qty} x {sku} is on the BOM only: no part of that SKU is in the model, so its fit, length and access are not checked.",
                   [base], value=0, limit=qty,
                   hint="Draw it as a catalogue part (for T-nuts and bracket screws: design.tnut_style = 'drop_in'), or remove the line.")
    # T-nuts against their screws
    by_name = x.comps
    tnut_screws = [c for c in d.components if c.meta.get("tnut")]
    tnuts = [c for c in d.components if c.meta.get("tnut_of")]
    missing = [c.name for c in tnut_screws if c.meta.get("tnut_part") not in by_name]
    if missing and not any(k.startswith("TNUT") for k in bom_only) and not x.waived("DG-06", "tnut_not_drawn", missing):
        x.flag("DG-06", "tnut_not_drawn", f"{len(missing)} screw(s) are declared into a T-nut but have neither a T-nut part nor a BOM line "
               f"(e.g. {', '.join(missing[:4])}).", missing, value=0, limit=len(missing))
    orphan = [c.name for c in tnuts if c.meta["tnut_of"] not in by_name or by_name[c.meta["tnut_of"]].meta.get("tnut_part") != c.name]
    if orphan and not x.waived("DG-06", "tnut_without_screw", orphan):
        x.flag("DG-06", "tnut_without_screw", f"{len(orphan)} T-nut(s) have no screw (e.g. {', '.join(orphan[:4])}).", orphan,
               value=len(orphan), limit=0)
    # declared joins that name a fastener: some drawn fastener must hold both parts
    fast = {f.name: f for f in d.fasteners if f.name in by_name}
    holds = {}
    for n, f in fast.items():
        c = by_name[n]
        h = set(f.clamps) | set(c.meta.get("threads_into") or [])
        for pair in d.joins:
            if n in pair and len(pair) == 2:
                h |= set(pair) - {n}
        holds[n] = h
    undrawn, integral = [], []
    for pair, kind in d.joins.items():
        if len(pair) != 2:
            continue
        a, b = sorted(pair)
        if a not in by_name or b not in by_name or a in fast or b in fast or _is_hardware_sku(by_name[a].sku) or _is_hardware_sku(by_name[b].sku):
            continue
        k = str(kind).lower()
        if any(w in k for w in SETSCREW_WORDS):
            integral.append({"parts": [a, b], "kind": str(kind)})
            continue
        if not FASTENED_KIND.search(k):
            continue
        if not any(a in h and b in h for h in holds.values()):
            undrawn.append((a, b, str(kind)))
    for a, b, kind in undrawn:
        if not x.waived("DG-06", "joint_without_fasteners", [a, b]):
            x.flag("DG-06", "joint_without_fasteners",
                   f"{a} and {b} are declared joined by '{kind}', but no drawn fastener holds both.", [a, b], value=0, limit=1,
                   hint="Draw the screw (and its nut or T-nut): add_screw(..., clamps=..., threads_into=...).")
    return {"hardware_parts_drawn": sum(drawn.values()), "hardware_skus_drawn": len(drawn), "bom_only_hardware": bom_only,
            "tnut_screws": len(tnut_screws), "tnuts_drawn": len(tnuts), "tnut_screws_without_part": len(missing),
            "joins_naming_fasteners_without_one": len(undrawn),
            "set_screw_joins_not_drawn": integral,
            "note": "set screws are inside the bought pulley's hub and come with it: listed here, not required as parts"}


def verify_practice(design: Design) -> VerifierResult:
    r = VerifierResult("practice")
    with timed(r):
        x = _Ctx(design, r)
        unknown = sorted((set(x.disabled) | set(x.sev_over)) - set(RULES))
        for rid in unknown:
            r.add("warning", "unknown_practice_rule", f"design.practice names rule {rid!r}, which is not a practice rule.", rule=rid)
        for rid, sev in x.sev_over.items():
            if sev not in SEVERITY_RANK:
                r.add("warning", "bad_practice_severity", f"design.practice severity for {rid} is {sev!r}; use info, warning or error.", rule=rid)
                x.sev_over.pop(rid, None)
        pr = FS.Probe(design)
        rows = FS.fastener_stack(design, pr)
        bcs = FS.bearing_contacts(design, pr)
        steps = [("FST-060", lambda: _fst060(x, rows)), ("FST-070", lambda: _fst070(x, rows)), ("belts", lambda: _belts(x)),
                 ("bearings", lambda: _bearings(x, bcs)), ("set screws", lambda: _set_screws(x)),
                 ("FST-051/101", lambda: _fst051_101(x, rows)), ("holes", lambda: _holes(x, rows)), ("FST-034", lambda: _fst034(x, rows)),
                 ("FST-081", lambda: _fst081(x, rows)), ("LOC-006", lambda: _loc006(x)), ("FST-040", lambda: _torque_table(x, rows)),
                 ("FST-072", lambda: _fst072(x, rows)),
                 ("DG-01", lambda: _dg01(x, rows)), ("DG-02", lambda: _dg02(x, rows)), ("DG-03", lambda: _dg03(x)),
                 ("DG-04", lambda: _dg04(x, rows, results.get("DG-01") or [])), ("DG-05", lambda: _dg05(x, rows, pr)),
                 ("DG-06", lambda: _dg06(x))]
        results = {}
        for name, fn in steps:
            try:
                results[name] = fn()
            except Exception as e:      # one rule failing must not hide the others; unmeasured is not a pass
                import traceback

                r.add("error", "practice_rule_not_checked", f"practice rule {name} could not be checked: {type(e).__name__}: {e}",
                      rule=name, trace=traceback.format_exc()[-600:])
        # waivers: every one listed; no reason is an error, unused is a warning
        wout = []
        for w in x.waivers:
            if len(w["reason"].strip()) < MIN_WAIVER_REASON:
                r.add("error", "waiver_without_reason",
                      f"Waiver of {w['rule']} for {w['parts'] or 'the whole design'} has no written reason (at least {MIN_WAIVER_REASON} "
                      f"characters): say why the rule does not apply.", rule=w["rule"], parts=w["parts"], reason=w["reason"])
            if not w["suppressed"]:
                r.add("warning", "waiver_unused", f"Waiver of {w['rule']} for {w['parts'] or 'the whole design'} suppresses nothing: "
                      f"remove it, or correct the rule id / part names.", rule=w["rule"], parts=w["parts"])
            wout.append({"rule": w["rule"], "parts": w["parts"], "reason": w["reason"], "suppressed": w["suppressed"][:40]})
        rule_table = {}
        for rid, R in RULES.items():
            e = {"title": R.title, "status": R.status, "severity": x.sev_over.get(rid, R.severity), "evidence": R.evidence}
            if R.status == "xref":
                e["checked_by"] = R.checked_by
            elif R.status == "deferred":
                e["reason"] = R.note
            else:
                e["findings"] = x.count.get(rid, 0)
                e["enabled"] = rid not in x.disabled
                if R.note:
                    e["scope"] = R.note
            rule_table[rid] = e
        r.metrics = {
            "rules": rule_table,
            "counts": {"implemented": sum(R.status == "implemented" for R in RULES.values()),
                       "cross_referenced": sum(R.status == "xref" for R in RULES.values()),
                       "deferred": sum(R.status == "deferred" for R in RULES.values())},
            "findings_by_rule": dict(sorted(x.count.items())),
            "waivers": wout,
            "screws_measured": len(rows), "bearings_measured": len(bcs),
            "screws_with_declared_locking": sum(bool(_locked(x, row)[0]) for row in rows),
            "hole_classes_iso273": results.get("holes"),
            "torque_table": results.get("FST-040"),
            "belt_pulleys": results.get("belts"),
            "printed_parts_in_load_path": results.get("DG-01"),
            "printed_parts_on_metal_sleeves": x.sleeved or None,
            "threads_in_printed_parts": results.get("DG-04"),
            "printed_clearance_holes": results.get("DG-05"),
            "hardware_completeness": results.get("DG-06"),
            "nyloc_temperature": results.get("FST-072"),
            "machined_parts": results.get("DG-03"),
            "limits_overridden": dict(x.limits) or None, "disabled": sorted(x.disabled) or None,
            "method": "point-in-solid probing of the B-rep at the home pose (mechloop/verifiers/fastener_stack.py); "
                      "stations every 0.25 mm along each screw, hole radius in 0.05 mm steps refined by bisection",
            "point_tests": pr.calls,
        }
    return r
