"""Build the design-review data for a printer design.

Reads what the pipeline already wrote (the viewer export, the build package and the shop profiles) and
writes review/data.json: assemblies, parts and bolted joints, each with material, process, tolerances,
the checks that apply, verifier findings, open items and a list of review flags measured against
docs/DESIGN_GUIDELINES.md. The 3D meshes and the drawings are not copied: the published review page maps
viewer/meshes.txt and docs/build/<design>/drawings/*.svg next to it.

    .venv/bin/python tools/build_review.py [printer_v8]
"""
from __future__ import annotations

import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = sys.argv[1] if len(sys.argv) > 1 else "printer_v8"
PKG = ROOT / "docs" / "build" / DESIGN
OUT = ROOT / "review"

MATERIAL = {
    "al6061": "Aluminium 6061-T6",
    "al_mic6": "Cast aluminium tooling plate (MIC-6 class)",
    "steel": "Steel, grade not named",
    "stainless304": "Stainless steel 304",
    "abs": "ABS",
    "petg": "PETG",
    "nylon_pa12": "Nylon PA12",
    "brass": "Brass",
    "rubber_gt2": "Rubber belt (glass-fibre cord)",
}
PROCESS = {
    "sheet": "2D laser-cut plate",
    "machined": "CNC machined",
    "printed": "3D printed (FDM)",
}
SHOP = {"sheet": "SendCutSend", "machined": "Xometry", "printed": "Printed in-house"}

# Printed parts that carry load in v8 (a guide, a lead-screw nut, a bearing, a motor or belt tension).
PRINTED_LOAD = {
    "nut_block": "carries a lead-screw nut and the bed's share of weight and thrust",
    "nut_block_fl": "carries a lead-screw nut and the bed's share of weight and thrust",
    "nut_block_fr": "carries a lead-screw nut and the bed's share of weight and thrust",
    "z_drive_mount": "holds the Z motor, two 608 bearings and the belt tension",
    "z_sleeve": "spaces the two 608 bearings that carry the main lead screw",
    "z_pedestal_fl": "holds a lead screw's bearing and the bed thrust",
    "z_pedestal_fr": "holds a lead screw's bearing and the bed thrust",
    "x_belt_block": "clamps the X belt: carries the full belt tension and acceleration load",
    "x_tension_anchor": "anchors a belt end: carries the belt tension",
    "y_tension_anchor": "anchors a belt end: carries the belt tension",
    "y_tension_anchor_l": "anchors a belt end: carries the belt tension",
}

# Assembly-level design criteria: (label, how it is read from the report, target).
GENERIC = {"bed", "host", "inlet", "extruder", "psu", "hotend"}
GROUP_ORDER = ["Frame", "Y drive and rails", "Gantry beam (moves in Y)", "Toolhead (X carriage)",
               "Z drive and rails", "Bed and Z stage", "Electronics bay"]


def md_inline(s: str) -> str:
    s = html.escape(s, quote=False)
    s = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def md_block(text: str) -> str:
    """Small Markdown subset: bullets (two levels), tables, paragraphs, bold, code."""
    out, lines, i = [], text.strip("\n").split("\n"), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            head, *body = rows
            t = "<div class='tw'><table><thead><tr>" + "".join(f"<th>{md_inline(c)}</th>" for c in head)
            t += "</tr></thead><tbody>"
            for r in body:
                t += "<tr>" + "".join(f"<td>{md_inline(c)}</td>" for c in r) + "</tr>"
            out.append(t + "</tbody></table></div>")
            continue
        if re.match(r"\s*- ", ln):
            items = []
            while i < len(lines) and re.match(r"\s*- ", lines[i]):
                depth = (len(lines[i]) - len(lines[i].lstrip())) // 2
                items.append((depth, lines[i].strip()[2:]))
                i += 1
            h, d0 = "<ul>", 0
            for depth, txt in items:
                while depth > d0:
                    h, d0 = h + "<ul>", d0 + 1
                while depth < d0:
                    h, d0 = h + "</ul>", d0 - 1
                h += f"<li>{md_inline(txt)}</li>"
            out.append(h + "</ul>" * (d0 + 1))
            continue
        if ln.strip() and not ln.startswith("!["):
            out.append(f"<p>{md_inline(ln)}</p>")
        i += 1
    return "".join(out)


def sections(md: str, level: str) -> dict[str, str]:
    parts, cur, buf = {}, None, []
    for ln in md.split("\n"):
        if ln.startswith(level + " "):
            if cur:
                parts[cur] = "\n".join(buf)
            cur, buf = ln[len(level) + 1:].strip(), []
        elif re.match(r"#{1,%d} " % (len(level) - 1), ln):
            if cur:
                parts[cur] = "\n".join(buf)
            cur, buf = None, []
        elif cur:
            buf.append(ln)
    if cur:
        parts[cur] = "\n".join(buf)
    return parts


def stem(name: str) -> str:
    if name.endswith("_tnut"):          # a drawn T-nut is named after its screw: it belongs to that screw's joint
        name = name[:-5]
    return re.sub(r"_(screw|bolt|nut|washer|spacer|fbolt)(_[a-z0-9]+)?$", "", name)


def into_text(j, tapped, into_tnut, hw, parts_by_name) -> str:
    skus = " ".join(hw)
    if tapped:
        return "a thread tapped in " + ", ".join(sorted({h["part"] for h in tapped}))
    if "NUT" in skus.upper() and "TNUT" not in skus.upper():
        return "a nut"
    if "TNUT" in skus.upper():
        return "a drop-in T-nut in the 2020 extrusion's slot (a drawn part; its dimensions are a stand-in)"
    if into_tnut:
        return "a T-nut in the 2020 extrusion slot, or the extrusion's end thread"
    vend = [m for m in j["members"] if parts_by_name.get(m, {}).get("kind") in ("purchased", "electrical")]
    if vend:
        return "factory threads in " + ", ".join(vend)
    return "not recorded"


def main() -> None:
    v = json.loads((ROOT / "viewer" / "data.json").read_text())
    if v["design"] != DESIGN:
        sys.exit(f"viewer/ holds {v['design']}, not {DESIGN}: re-export the viewer first")
    plan = json.loads((PKG / "data" / "assembly_plan.json").read_text())
    fab = sections((PKG / "FABRICATION.md").read_text(), "###")
    fab_top = sections((PKG / "FABRICATION.md").read_text(), "##")
    scs = json.loads((ROOT / "mechloop" / "shops" / "sendcutsend.json").read_text())
    holes = defaultdict(list)
    for r in csv.DictReader(open(PKG / "hole_tables.csv")):
        holes[r["part"]].append(r)
    by_screw = defaultdict(list)
    for part, rows in holes.items():
        for r in rows:
            for s in filter(None, r["screws"].split()):
                by_screw[s].append({"part": part, "id": r["id"], "function": r["function"],
                                    "dia": r["dia_or_width"], "kind": r["kind"], "slot": r["slot_length"]})
    washers = {r["fastener"]: r for r in csv.DictReader(open(PKG / "washer_audit.csv"))}
    fasteners_csv = {r["sku"]: r for r in csv.DictReader(open(PKG / "fasteners.csv"))}
    bom = {r["sku"]: r for r in csv.DictReader(open(PKG / "bom.csv"))}

    # Stock gauges at SendCutSend.
    stock = {}
    for mat, m in scs["materials"].items():
        th = []
        for t in m.get("thicknesses", []):
            val = t.get("t_mm") if isinstance(t, dict) else t
            if isinstance(val, (int, float)):
                th.append(float(val))
        stock[mat] = sorted(th)

    # Open items (A/B/C tables).
    oi_md = (PKG / "OPEN_ITEMS.md").read_text()
    open_items = []
    for sec, body in sections(oi_md, "##").items():
        m = re.match(r"([ABC]) - (.*)", sec)
        if not m:
            continue
        for ln in body.split("\n"):
            if not ln.startswith("| ") or ln.startswith("| #") or ln.startswith("|---"):
                continue
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) < 4:
                continue
            open_items.append({"rank": m.group(1), "rank_label": m.group(2), "n": cells[0],
                               "title": re.sub(r"\*\*", "", cells[1]), "known": md_inline(cells[2]),
                               "check": md_inline(cells[3]), "raw": " ".join(cells[1:4])})

    parts_by_name = {p["name"]: p for p in v["parts"]}
    names_sorted = sorted(parts_by_name, key=len, reverse=True)

    def mentions(text: str) -> list[str]:
        found = set()
        for n in names_sorted:
            if n in GENERIC and not re.search(r"`" + re.escape(n) + r"`", text):
                continue
            if re.search(r"(?<![A-Za-z0-9_])" + re.escape(n) + r"(?![A-Za-z0-9_])", text):
                found.add(n)
        return sorted(found)

    for k, it in enumerate(open_items):
        it["id"] = f"OI-{it['rank']}{it['n']}"
        it["parts"] = sorted(set(mentions(it["raw"])) | {n for n, pp in parts_by_name.items()
                                                       if pp.get("sku") and re.search(r"`" + re.escape(pp["sku"]) + r"[ `]", it["raw"])})
        del it["raw"]

    # Joints from the assembly plan: every fastener row with what it goes onto.
    fast_rows = [r for r in plan["rows"] if r["kind"] == "fastener"]
    for sub in plan["subassemblies"].values():
        fast_rows += [dict(r, sub=True) for r in sub["rows"] if r["kind"] == "fastener"]
    joints: dict[tuple, dict] = {}
    seen = set()
    for r in fast_rows:
        if r["unit"] in seen:
            continue
        seen.add(r["unit"])
        onto = tuple(sorted(o for o in r.get("onto") or [] if parts_by_name.get(o, {}).get("kind") != "fastener"))
        if not onto:
            continue
        j = joints.setdefault(onto, {"members": list(onto), "fasteners": [], "tools": set(),
                                     "directions": set(), "steps": []})
        j["fasteners"].append(r["unit"])
        if r.get("tool"):
            j["tools"].add(r["tool"])
        if r.get("direction"):
            j["directions"].add(r["direction"])
        j["steps"].append(r["step"])
    # Attach nuts, washers and spacers that share a stem with a joint's screws.
    stem_to_joint = {}
    for key, j in joints.items():
        for f in j["fasteners"]:
            stem_to_joint[stem(f)] = key
    for p in v["parts"]:
        if p["kind"] != "fastener" or p["name"] in seen:
            continue
        key = stem_to_joint.get(stem(p["name"]))
        if key:
            joints[key]["fasteners"].append(p["name"])

    joint_list = []
    for key, j in joints.items():
        hw = defaultdict(int)
        for f in j["fasteners"]:
            hw[parts_by_name[f]["sku"] if f in parts_by_name else f] += 1
        holes_used, wnotes = [], []
        for f in j["fasteners"]:
            for h in by_screw.get(f, []):
                holes_used.append(dict(h, screw=f))
            if f in washers:
                w = washers[f]
                wnotes.append({"fastener": f, "bears_on": w["bears_on"], "why": w["why"],
                               "coverage": w["coverage"]})
        member_parts = [parts_by_name[m] for m in j["members"] if m in parts_by_name]
        group = member_parts[0]["group"] if member_parts else "Frame"
        fab_members = [m for m in member_parts if m["kind"] == "fabricated"]
        if fab_members:
            group = fab_members[0]["group"]
        tapped = [h for h in holes_used if "TAP" in h["function"]]
        into_tnut = any((parts_by_name.get(m, {}).get("sku") or "").startswith("EXT2020") for m in j["members"])
        flags = []
        for h in tapped:
            mp = parts_by_name.get(h["part"], {})
            if (mp.get("material") or "").startswith("al") and mp.get("kind") == "fabricated":
                flags.append({"sev": "error", "rule": "No tapped aluminium",
                              "text": f"{h['screw']} runs into a thread tapped in {h['part']} ({mp['material']}, hole {h['id']}). "
                                      "Guideline: through-bolt with nut and washer, a PEM nut, or a steel insert."})
        for w in wnotes:
            flags.append({"sev": "warning", "rule": "Washer needed",
                          "text": f"{w['fastener']}: head or nut bears on {w['bears_on']}: {w['why']}. No washer in the model."})
        seen_flag = set()
        flags = [f for f in flags if not (f["text"] in seen_flag or seen_flag.add(f["text"]))]
        jid = "J-" + "--".join(j["members"])
        joint_list.append({
            "id": jid, "name": " + ".join(j["members"]), "members": j["members"], "group": group,
            "fasteners": sorted(set(j["fasteners"])), "hardware": dict(sorted(hw.items())),
            "tools": sorted(j["tools"]), "directions": sorted(j["directions"]),
            "steps": sorted(j["steps"]), "holes": holes_used, "washers": wnotes, "flags": flags,
            "into": into_text(j, tapped, into_tnut, hw, parts_by_name),
        })
    joint_list.sort(key=lambda j: (GROUP_ORDER.index(j["group"]) if j["group"] in GROUP_ORDER else 99, j["name"]))
    joints_of_part = defaultdict(list)
    for j in joint_list:
        for m in j["members"]:
            joints_of_part[m].append(j["id"])
        for f in j["fasteners"]:
            joints_of_part[f].append(j["id"])

    # FEA load cases per component.
    fea_by_part = defaultdict(list)
    for case, r in v["fea"].items():
        if isinstance(r, dict) and "component" in r:
            fea_by_part[r["component"]].append({
                "case": case, "material": r.get("material"), "fos": r.get("fos"), "min_fos": r.get("min_fos"),
                "peak_mpa": r.get("peak_vm_mpa"), "yield_mpa": r.get("yield_mpa"),
                "deflection_mm": r.get("max_deflection_mm"), "force_n": r.get("applied_force_n")})

    out_parts = []
    for p in v["parts"]:
        name, kind = p["name"], p["kind"]
        proc = p["process"]
        mfg = p.get("mfg") or {}
        q = {k: p[k] for k in ("name", "kind", "group", "sku", "desc", "cost", "mass", "bbox", "v", "t", "body")}
        q["material_code"] = p["material"]
        q["material"] = MATERIAL.get(p["material"], p["material"])
        q["process"] = PROCESS.get(proc, None) if kind == "fabricated" else None
        q["process_code"] = proc
        q["shop"] = SHOP.get(proc) if kind == "fabricated" else None
        q["model"] = p["model"]
        q["model_source"] = p["model_source"]
        try:
            src = json.loads(p["source"]) if p.get("source") else None
        except json.JSONDecodeError:
            src = None
        q["catalogue"] = ({"level": src.get("level"), "vendor": src.get("vendor"), "part": src.get("part"),
                           "unverified": src.get("unverified_fields")} if isinstance(src, dict) else None)
        b = bom.get(p["sku"] or "")
        if b:
            q["maker"] = b["maker"]
            q["maker_pn"] = b["maker_part_number"]
            q["mcmaster"] = b["mcmaster_number"]
            q["key_spec"] = b["key_spec"]
            q["bom_basis"] = b["basis"]
        q["findings"] = [{"verifier": f["verifier"], "severity": f["severity"], "code": f["code"],
                          "message": f["message"], "hint": f.get("hint")} for f in p["findings"]]
        q["joints"] = sorted(set(joints_of_part.get(name, [])))
        q["open_items"] = [it["id"] for it in open_items if name in it["parts"]]
        q["fea"] = fea_by_part.get(name, [])
        q["holes"] = holes.get(name, [])
        flags = []
        if kind == "fabricated":
            q["mfg"] = mfg
            q["fab_html"] = md_block(fab.get(name, ""))
            q["drawing"] = f"drawings/{name}.svg" if (PKG / "drawings" / f"{name}.svg").exists() else None
            thick = mfg.get("thickness_mm") or mfg.get("stock_mm")
            q["thickness_mm"] = thick
            crit = [h for h in q["holes"] if h["critical"] and h["critical"] != "-"]
            q["critical"] = [{"id": h["id"], "what": h["critical"], "dia": h["dia_or_width"],
                              "function": h["function"]} for h in crit]
            if proc == "printed" and name in PRINTED_LOAD:
                flags.append({"sev": "error", "rule": "No load-bearing printed parts",
                              "text": f"Printed, but it {PRINTED_LOAD[name]}. v8.1 moves this to laser-cut aluminium or metal."})
            if proc == "printed":
                flags.append({"sev": "warning", "rule": "Print settings",
                              "text": "No print settings declared (walls, infill, orientation reason). Mass and FEA assume solid plastic."})
            if p["material"] == "steel":
                flags.append({"sev": "warning", "rule": "Named material",
                              "text": "Steel with no grade or finish. Guideline: 6061-T6 or 5052-H32 aluminium, stainless, or a named carbon steel with a finish the shop applies."})
            if proc == "sheet" and thick:
                st = stock.get(p["material"], [])
                near = min(st, key=lambda t: abs(t - thick)) if st else None
                if near is not None and abs(near - thick) > 0.05:
                    lo = max([t for t in st if t <= thick], default=None)
                    hi = min([t for t in st if t >= thick], default=None)
                    flags.append({"sev": "warning", "rule": "Stocked gauge",
                                  "text": f"Drawn {thick:g} mm; SendCutSend stocks {p['material']} at "
                                          f"{lo if lo is not None else '-'} or {hi if hi is not None else '-'} mm nearby."})
            if proc == "machined":
                if p["material"] == "al_mic6":
                    flags.append({"sev": "info", "rule": "CNC needs a reason",
                                  "text": "Bed plate: flatness-critical cast plate. Could be laser-cut from stocked MIC-6 (6.35 or 9.53 mm) if the holes are plain through holes."})
                else:
                    flags.append({"sev": "warning", "rule": "CNC needs a reason",
                                  "text": "Machined part. Guideline: 2D plates first; write down why this needs CNC or replace it with stacked plates."})
            for h in q["holes"]:
                if "TAP" in h["function"] and p["material"].startswith("al"):
                    flags.append({"sev": "error", "rule": "No tapped aluminium",
                                  "text": f"Hole {h['id']}: {h['function']} in {q['material']}."})
            if proc in ("sheet", "machined") and p["material"] != "abs":
                flags.append({"sev": "warning", "rule": "Broken edges",
                              "text": "Edge breaks and corner radii are a drawing note only, not in the model."})
        if kind == "fastener":
            fc = fasteners_csv.get(p["sku"] or "")
            if fc:
                q["fastener"] = {"size": fc["size"], "length": fc["length"], "kind": fc["kind"], "hex_key": fc["hex_key"]}
            hs = by_screw.get(name, [])
            q["through"] = hs
            if name in washers:
                w = washers[name]
                flags.append({"sev": "warning", "rule": "Washer needed",
                              "text": f"Bears on {w['bears_on']}: {w['why']}."})
        q["flags"] = flags
        out_parts.append(q)

    # Assemblies.
    def fea_line(case):
        r = v["fea"].get(case) or {}
        if "fos" in r:
            return f"factor of safety {r['fos']:.1f} (need {r['min_fos']:g}); peak {r['peak_vm_mpa']:.2f} MPa; deflection {r['max_deflection_mm']:.3f} mm"
        if "deflection_mm" in r:
            return f"nozzle deflection {r['deflection_mm']*1000:.2f} µm under the load case"
        if "max_growth_mm" in r:
            return f"largest thermal growth {r['max_growth_mm']:.3f} mm ({r.get('joints', '')})"
        return None

    tol = v["tolerance"]["printer"]
    req = {r["data"]["requirement"]: r["message"] for r in v["requirements"] if r.get("data")}
    sc = v["score"]
    bs = v["fea"].get("bed_support", {})

    def reqf(key):
        # Requirement text by its name; designs word the same requirement slightly differently, so fall back to the
        # requirement whose name shares the most words with the key.
        if key in req:
            return req[key]
        words = set(key.lower().split())
        best = max(req, key=lambda k: len(words & set(k.lower().split())), default=None)
        return req[best] if best and len(words & set(best.lower().split())) >= max(3, len(words) // 2) else ""

    def bed_support_text():
        # Read from the design's own bed requirements (sag and nut seating) when it states them, else the bed_support study.
        lines = [m for k, m in req.items() if "sag" in k.lower() or "seated" in k.lower()]
        if lines:
            return " ".join(lines)[:600]
        pw = bs.get("print_weight", {})
        return f"print weight at the worst corner: {pw.get('judged_mm', '?')} mm (limit {pw.get('limit_mm', '?')} mm)" if pw else ""

    def mains_text():
        covers = [p["name"] for p in v["parts"] if p["name"].startswith("mains_cover") and p["kind"] == "fabricated"]
        if covers:
            return f"Live terminals under {len(covers)} printed covers ({', '.join(covers)}), each held by screws into inserts."
        return "Open frame; live terminals not covered."

    def board_text():
        b = next((p for p in v["parts"] if p["name"] == "control_board"), None)
        return f"{b['sku']}: {b.get('desc') or ''}".strip(": ") if b else ""

    crit = {
        "Frame": [
            ("Frame stiffness at the nozzle", f"X {sc['frame_stiffness_n_per_mm']['x']:.0f} N/mm, Y {sc['frame_stiffness_n_per_mm']['y']:.0f} N/mm (FEA, lower bound: joints held only round their screws)"),
            ("Print volume", reqf("print volume: travel >= 180 x 180 x 180 mm")),
            ("General tolerance, extrusion", "position ±0.30 mm, cut length ±0.20 %"),
        ],
        "Y drive and rails": [
            ("Belt plane", reqf("target: both Y belts within 1 mm of plane in >= 98% of builds")),
            ("Resonance (Y)", f"{sc['resonance_hz']['y']} Hz"),
            ("Drive margin", reqf("drive margin >= 3x on every axis")),
            ("Carriage on rail", reqf("every carriage stays >= 5 mm inside its rail ends over the mechanical travel (over-travel included)")[:200]),
        ],
        "Gantry beam (moves in Y)": [
            ("Nozzle stiffness", f"Y: {fea_line('nozzle_stiffness_y')}; X: {fea_line('nozzle_stiffness_x')}"),
            ("Resonance (X)", f"{sc['resonance_hz']['x']} Hz"),
        ],
        "Toolhead (X carriage)": [
            ("Moving mass on X", reqf("target: direct drive, at most 0.4 kg moving in X")),
            ("Belt clamp", f"x_belt_pull: {fea_line('x_belt_pull')}"),
            ("Nozzle-to-bed gap scatter", f"99 % of builds within ±{tol['gap_error_mm_99']} mm; biggest contributors: "
             + ", ".join(c["joint"] for c in tol["largest_contributors_to_gap"][:3])),
            ("Probe", reqf("the bed probe switches before the nozzle touches for every unit, and over-travel ends short of its face")[:220]),
        ],
        "Z drive and rails": [
            ("Lead screws", "three T8×2 screws on one closed belt from one motor; self-locking " + reqf("Z lead screw self-locking (efficiency < 0.5)")),
        ] + [(f"Load case {c}", f"{', '.join(v['fea'][c].get('parts', [])[:2]) or c}: {fea_line(c)}")
             for c in v["fea"] if ("thrust" in c) and fea_line(c)] + [
            ("Rail and screw tops", reqf("Z rails and lead screw end below the top back extrusion (no rubbing)")),
        ],
        "Bed and Z stage": [
            ("Bed level as built", f"bed out of level 99th percentile {tol['bed_out_of_level_mm_99']} mm before levelling; three-screw Z, one guide block per rail"),
            ("Payload", f"payload_x3_on_bed: {fea_line('payload_x3_on_bed') or 'see report'}"),
            ("Heated bed +60 K", f"bed_heated_60K: {fea_line('bed_heated_60K') or 'see report'}"),
            ("Bed support result", bed_support_text()),
            ("Bed reaches nozzle", reqf("bed can reach the nozzle: 0-0.2 mm gap at the top of the print height")),
        ],
        "Electronics bay": [
            ("Mains", mains_text()),
            ("Board", board_text()),
        ],
    }
    subs_of_group = defaultdict(list)
    for sname, sub in plan["subassemblies"].items():
        units = [r["unit"] for r in sub["rows"]]
        grp = next((parts_by_name[u]["group"] for u in units if parts_by_name.get(u, {}).get("kind") == "fabricated"), None)
        subs_of_group[grp].append({"name": sname, "parts": units, "minutes": sub["metrics"]["estimated_time_min"],
                                   "steps": sub["metrics"]["steps"], "tools": sub["metrics"]["tools"]})
    assemblies = []
    for g in GROUP_ORDER:
        ps = [p for p in out_parts if p["group"] == g]
        assemblies.append({
            "id": "A-" + re.sub(r"[^a-z0-9]+", "-", g.lower()).strip("-"), "name": g,
            "parts": [p["name"] for p in ps],
            "counts": {k: sum(1 for p in ps if p["kind"] == k) for k in ("fabricated", "purchased", "electrical", "fastener")},
            "mass": round(sum(p["mass"] or 0 for p in ps), 3),
            "cost": round(sum(p["cost"] or 0 for p in ps), 2),
            "criteria": [{"label": a, "value": b} for a, b in crit.get(g, []) if b],
            "subassemblies": subs_of_group.get(g, []),
            "joints": [j["id"] for j in joint_list if j["group"] == g],
            "open_items": sorted({oi for p in ps for oi in p["open_items"]}),
        })

    tol_html = md_block(fab_top.get("Tolerances: where the numbers come from", ""))
    print_html = md_block(fab_top.get("Printing", ""))
    data = {
        "design": DESIGN,
        "generated_from": {"viewer": "viewer/data.json", "package": f"docs/build/{DESIGN}", "design_md5": plan["design_md5"]},
        "summary": {"parts": len(out_parts), "custom": sum(1 for p in out_parts if p["kind"] == "fabricated"),
                    "joints": len(joint_list), "mass_kg": v["mass"], "bom_cost": v["bom_cost"],
                    "assembly_min": plan["metrics"]["estimated_time_min"],
                    "verifiers": {k: {"ok": s.get("ok"), "errors": s.get("errors"), "warnings": s.get("warnings")}
                                  for k, s in v["summary"].items() if isinstance(s, dict)},
                    "resonance_hz": sc["resonance_hz"]},
        "tolerance_html": tol_html,
        "printing_html": print_html,
        "shops": {"sheet": {"name": "SendCutSend", "tolerance": "±0.127 mm under 12 in, ±0.254 mm over",
                            "stock": {k: v2 for k, v2 in stock.items() if v2}},
                  "machined": {"name": "Xometry", "tolerance": "±0.127 mm default (ISO 2768-m class)"}},
        "assemblies": assemblies,
        "joints": joint_list,
        "parts": out_parts,
        "joints_top": [],
        "open_items": open_items,
        "joint_list": None,
    }
    data.pop("joints_top"); data.pop("joint_list")
    OUT.mkdir(exist_ok=True)
    # Drawing sheets without their XML prolog/DOCTYPE (the artifact host refuses DTDs). Git-ignored copies.
    dw = OUT / "drawings"
    dw.mkdir(exist_ok=True)
    for svg in sorted((PKG / "drawings").glob("*.svg")):
        txt = svg.read_text()
        txt = re.sub(r"<\?xml[^>]*\?>\s*", "", txt, count=1)
        txt = re.sub(r"<!DOCTYPE[^>\[]*(\[[^\]]*\])?\s*>\s*", "", txt, count=1)
        (dw / svg.name).write_text(txt)
    (OUT / "data.json").write_text(json.dumps(data, separators=(",", ":"), default=list))
    print(f"wrote review/data.json: {len(out_parts)} parts, {len(joint_list)} joints, {len(assemblies)} assemblies, "
          f"{len(open_items)} open items, {(OUT / 'data.json').stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main()
