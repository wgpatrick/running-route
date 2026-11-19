"""Export a design and its verification report for the browser viewer (viewer/index.html).

    python tools/export_viewer.py designs/printer_v4.py [--no-assembly] [--print out/<name>/fil/<part>]

--print takes the folder of a `mechloop print ... --trajectory` run and adds its nozzle path for replay
(viewer/print.txt). Without it an existing viewer/print.txt and the print block in data.json are kept.

Writes viewer/meshes.txt (base64 of float32 positions and uint32 triangles) and viewer/data.json.
Run `python -m mechloop verify <design>` first: the report in out/<name>/report.json is read, not recomputed.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

from mechloop.geom import to_trimesh
from mechloop.runner import load_design

LEADSCREW_NUT_SKUS = ("T8-NUT", "NUT-TR8")
FAST = re.compile(r"(_screw|_bolt|_nut|_locknut|_pin|_stud)(_[a-z]+)?(_\d+)?$")


def group_of(c, electronics):
    n = c.name
    if n in electronics or n.startswith(("electronics_tray", "tray_bolt", "inlet", "earth", "psu", "control_board", "host",
                                         "bed_mosfet")):
        return "Electronics bay"
    if c.body == "xbody":
        return "Toolhead (X carriage)"
    if c.body == "ybody":
        return "Gantry beam (moves in Y)"
    if c.body == "zbody":
        return "Bed and Z stage"
    if n.startswith(("z_", "leadscrew", "upright", "brkt_up")):
        return "Z drive and rails"
    if n.startswith("y_"):
        return "Y drive and rails"
    return "Frame"


def kind_of(c):
    # lead-screw nuts are drive parts, not hardware: keep them visible with fasteners hidden (T8-NUT: brass T8 nut;
    # NUT-TR8...: the nut supplied on a StepperOnline lead-screw motor, whose SKU would otherwise read as a hex nut)
    if (c.sku or "").startswith(LEADSCREW_NUT_SKUS):
        return "purchased"
    if FAST.search(c.name) or (c.sku or "").startswith(("SHCS", "NUT", "HEX", "TNUT", "WASHER")):
        return "fastener"
    if c.ratings.get("electrical") or "electrical" in c.ratings:
        return "electrical"
    return "purchased" if c.cots else "fabricated"


_DETAIL_MESH: dict = {}


def detail_mesh(c):
    """Tessellation of a part's detail model, made once per catalog part in its local frame and moved to each
    instance. Big models are tessellated more coarsely."""
    import trimesh

    from mechloop.parts import vendor_cad

    key = (c.meta.get("model") or {}).get("key")
    st = vendor_cad.STOCKS.get(key)
    P = c.meta.get("placement")
    if st is None or st.detail is None or P is None:
        return to_trimesh(c.detail, 0.12, 0.45)
    if key not in _DETAIL_MESH:
        nf = len(st.detail.faces())
        tol, ang = (0.08, 0.4) if nf < 200 else (0.15, 0.6) if nf < 1500 else (0.3, 0.9)
        verts, tris = st.detail.tessellate(tol, ang)
        _DETAIL_MESH[key] = (np.array([(p.X, p.Y, p.Z) for p in verts], dtype=float), np.array(tris, dtype=int))
    v, t = _DETAIL_MESH[key]
    P = np.asarray(P, dtype=float)
    return trimesh.Trimesh(v @ P[:, :3].T + P[:, 3], t, process=False)


FASTENER_TRI_BUDGET = 1500      # triangles a fastener may cost in viewer/meshes.txt
_LIGHT: dict = {}


def light_fastener_mesh(c):
    """A light display mesh for a fastener whose supplier CAD is too heavy for the page (McMaster's screws carry a modelled
    helical thread: 8,000 to 29,000 triangles each, and there are several hundred). Cap screws and countersunk screws are
    shown as their ISO outline (the geometry generated to the standard, same dimensions, thread not cut); washers, nuts and
    the rest as their simulation solid. The part's record still says what the model is (the supplier's file); only this
    page's picture is simplified, and the part's `model_note` says so. STEP export and drawings use the supplier's file."""
    import trimesh

    from mechloop.parts import details

    P = c.meta.get("placement")
    m = re.match(r"(SHCS|FHCS)-(M[\d.]+)x([\d.]+)$", c.sku or "")
    if m and P is not None:
        key = (m.group(1), m.group(2), float(m.group(3)))
        if key not in _LIGHT:
            gen = (details.shcs if key[0] == "SHCS" else details.fhcs)(key[1], key[2])[0]
            if gen is not None:
                verts, tris = gen.tessellate(0.08, 0.4)
                _LIGHT[key] = (np.array([(p.X, p.Y, p.Z) for p in verts], dtype=float), np.array(tris, dtype=int))
            else:
                _LIGHT[key] = None
        if _LIGHT[key] is not None:
            v, t = _LIGHT[key]
            P = np.asarray(P, dtype=float)
            return trimesh.Trimesh(v @ P[:, :3].T + P[:, 3], t, process=False), "its ISO outline (thread not drawn)"
    return to_trimesh(c.shape, 0.12, 0.45), "its plain simulation solid"


BELT_BODY = {"x_belt": "ybody"}      # the X belt's pulleys ride on the gantry beam; Y belts' pulleys are on the frame
BELT_DENSITY = 1.2e-6                # kg/mm3, rubber with glass cord: an estimate, the BOM line carries no mass


def belt_parts(d, bom: dict):
    """Each design belt as a display part: a ribbon of the belt's width and thickness along its routed pitch line at the
    home pose (straight runs from mechloop.verifiers.belts.route plus arcs round each pulley it wraps). Belts are not
    components of the design, so this is display only; the verifiers judge them from design.belts."""
    import math

    import trimesh

    from mechloop.geom import forward_kinematics
    from mechloop.verifiers.belts import _basis, route

    T = forward_kinematics(d, {})
    comps = {c.name: c for c in (d.components.values() if isinstance(d.components, dict) else d.components)}
    out = []
    for b in d.belts:
        try:
            rt = route(d, b, T)
        except Exception as e:                                       # noqa: BLE001  shown as missing, not fatal
            print(f"belt {b.name}: not drawn ({e})")
            continue
        a, u, v = _basis(b.axis)
        segs = rt["segments"]
        nodes = []                                                   # (centre 3D, radius, sense) per path node
        for node in b.path:
            if node[0] == "pulley":
                c = comps[node[1]]
                ctr = c.meta["interfaces"]["belt_center"][0]
                nodes.append(((T[c.body] @ np.array([*ctr, 1.0]))[:3], c.ratings["pitch_diameter_mm"] / 2,
                              1.0 if node[2] == "ccw" else -1.0))
            else:
                nodes.append((None, 0.0, 1.0))
        pts = []
        n = len(segs)
        for k, (p0, p1) in enumerate(segs):
            pts += [np.asarray(p0, float), np.asarray(p1, float)]
            j = (k + 1) % len(nodes)                                 # the node between this run and the next
            if not (rt["closed"] or k + 1 < n):
                continue
            ctr, r, s = nodes[j]
            if ctr is None or r <= 0:
                continue
            q0, q1 = np.asarray(p1, float) - ctr, np.asarray(segs[(k + 1) % n][0], float) - ctr
            a_in, a_out = math.atan2(q0 @ v, q0 @ u), math.atan2(q1 @ v, q1 @ u)
            sweep = ((a_out - a_in) * s) % (2 * math.pi)
            h0, h1 = q0 @ a, q1 @ a
            m = max(2, int(math.degrees(sweep) / 12))
            for i in range(1, m):
                t = i / m
                th = a_in + s * sweep * t
                pts.append(ctr + r * (math.cos(th) * u + math.sin(th) * v) + (h0 + (h1 - h0) * t) * a)
        if rt["closed"]:
            pts.append(pts[0])
        P = [pts[0]]
        for p in pts[1:]:
            if np.linalg.norm(p - P[-1]) > 1e-6:
                P.append(p)
        P = np.array(P)
        # cross-section: width along the pulley axis, thickness in the belt's plane, normal to the run
        V, F = [], []
        hw, ht = b.width / 2, b.thickness / 2
        for i, p in enumerate(P):
            tan = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
            tan = tan - (tan @ a) * a
            tan /= max(np.linalg.norm(tan), 1e-9)
            nrm = np.cross(a, tan)
            V += [p + hw * a + ht * nrm, p - hw * a + ht * nrm, p - hw * a - ht * nrm, p + hw * a - ht * nrm]
        for i in range(len(P) - 1):
            for e in range(4):
                i0, i1 = 4 * i + e, 4 * i + (e + 1) % 4
                F += [[i0, i1, i1 + 4], [i0, i1 + 4, i0 + 4]]
        if not rt["closed"]:
            last = 4 * (len(P) - 1)
            F += [[0, 2, 1], [0, 3, 2], [last, last + 1, last + 2], [last, last + 2, last + 3]]
        tm = trimesh.Trimesh(np.array(V), np.array(F)[:, ::-1], process=False)       # reversed: normals outward
        sku = next((k for k in bom if k.startswith(f"GT2-BELT-{b.width:g}MM")), None)
        vol = rt["length"] * b.width * b.thickness
        body = BELT_BODY.get(b.name, "world")
        name = b.name if b.name.startswith("belt_") else "belt_" + b.name.replace("_belt", "").lstrip("_")
        out.append((name, body, sku, tm, round(vol * BELT_DENSITY, 4), rt["length"], b))
    return out


def d_density(c):
    from mechloop.model import MATERIALS
    mat = MATERIALS.get(c.material)
    return getattr(mat, "density", 2700.0) if mat else 2700.0


def export_print(folder: Path, out: Path):
    """Simulated nozzle path, thinned to the points where it turns, for replay in the viewer."""
    import base64

    rep = json.loads((folder / "print_report.json").read_text())
    z = np.load(folder / f"{rep['part']}_trajectory.npz")
    q, ext, dt = z["q"].astype(np.float64), z["extruding"], float(z["dt"])
    keep = [0]
    last_dir = np.zeros(3)
    for i in range(1, len(q) - 1):
        v = q[i + 1] - q[i]
        n = np.linalg.norm(v)
        d = v / n if n > 1e-6 else np.zeros(3)
        if ext[i] != ext[i - 1] or np.abs(d - last_dir).max() > 0.03 or (i - keep[-1]) * dt > 1.0:
            keep.append(i)
            last_dir = d
    keep.append(len(q) - 1)
    k = np.array(keep)
    arr = np.column_stack([k * dt, q[k]]).astype(np.float32)
    (out / "print.txt").write_text(base64.b64encode(arr.tobytes() + ext[k].astype(np.uint8).tobytes()).decode())
    pr, dy, fw = rep.get("print", {}), rep.get("dynamics", {}), rep.get("firmware")
    return {"part": rep["part"], "n": len(k), "nozzle": [float(x) for x in z["nozzle"]], "ok": rep["ok"],
            "size": rep.get("part_size_mm"), "time_s": (fw or rep["plan"])["print_time_s"], "heatup_s": rep["plan"].get("heatup_s"),
            "firmware": fw and {a: fw.get(a) for a in ("firmware", "commit", "mcu", "steps", "peak_step_rate_hz",
                                                         "mcu_step_rate_limit_hz", "peak_speed_mm_s", "max_distance_from_gcode_path_mm")},
            "layers": pr.get("layers"), "layer_height": pr.get("layer_height_mm"), "filament_g": pr.get("filament_mass_g"),
            "outline_match": pr.get("outline_iou_mean"), "outline_offset": (pr.get("outline_offset_mm") or {}).get("mean"),
            "cross_track_rms": dy.get("cross_track_rms_mm"), "cross_track_worst": dy.get("cross_track_worst_mm"),
            "worst_lag": dy.get("worst_lag_mm"),
            "findings": [{"severity": f["severity"], "code": f["code"], "message": f["message"]} for f in rep["findings"]]}


def main():
    path = sys.argv[1]
    d = load_design(path)
    out = Path("viewer")
    out.mkdir(exist_ok=True)
    rep = json.loads((Path("out") / d.name / "report.json").read_text())
    m = rep["metrics"]
    comps = list(d.components.values()) if isinstance(d.components, dict) else list(d.components)
    electronics = set(d.subassemblies.get("electronics", []))
    mfg = m.get("manufacture", {}).get("parts", {})
    masses = m.get("geometry", {}).get("mass_by_part_kg", {})
    masses = masses if isinstance(masses, dict) else {}
    dxf = rep.get("artifacts", {}).get("dxf", {})
    by_part = {}
    for f in rep["findings"]:
        p = (f.get("data") or {}).get("part")
        if not p and ":" in f["message"]:
            head = f["message"].split(":")[0].strip()
            p = head if any(c.name == head for c in comps) else None
        if p:
            by_part.setdefault(p, []).append({k: f[k] for k in ("verifier", "severity", "code", "message")} | {
                "hint": (f.get("data") or {}).get("hint", "")})
    blob, parts = [], []
    off = 0
    for c in comps:
        model = c.meta.get("model") or {"kind": "proxy" if c.cots else "design", "source": ""}
        # display the detail model (vendor / community CAD) where there is one; verifiers used c.shape
        tm = detail_mesh(c) if c.detail is not None else to_trimesh(c.shape, 0.12, 0.45)
        shown_as = None
        if kind_of(c) == "fastener" and len(tm.faces) > FASTENER_TRI_BUDGET:
            full = len(tm.faces)
            tm, how = light_fastener_mesh(c)
            shown_as = (f"Shown on this page as {how}: the model's own file has {full} triangles for this one part. "
                        f"The model, its STEP export and the drawings use the file named above.")
        v = np.asarray(tm.vertices, dtype=np.float32)
        t = np.asarray(tm.faces, dtype=np.uint32)
        vb, tb = v.tobytes(), t.tobytes()
        bb = c.shape.bounding_box()
        src = c.meta.get("source")
        parts.append({
            "name": c.name, "body": c.body, "kind": kind_of(c), "group": group_of(c, electronics),
            "material": c.material, "process": c.meta.get("process") or (mfg.get(c.name) or {}).get("process"),
            "sku": c.sku, "desc": c.meta.get("description", ""), "cost": c.meta.get("cost_usd"),
            "mass": round(float(masses.get(c.name) or c.mass_kg or c.shape.volume * 1e-9 * d_density(c)), 4),
            # what the displayed geometry is: "vendor CAD" | "community CAD" | "generated to standard" | "proxy"
            # (catalog parts) or "design" (custom parts), where it came from, and the STEP file behind it
            "model": model.get("kind"), "model_source": model.get("source", ""), "model_file": model.get("file"),
            "model_note": " ".join(x for x in (model.get("note"), shown_as) if x) or None,
            "model_state": __import__("mechloop.parts.vendor_cad", fromlist=["x"]).model_state(model) if c.cots else None,
            "vendor": bool(c.meta.get("vendor_backed")), "source": src if isinstance(src, str) else json.dumps(src)[:300] if src else "",
            "product": (c.ratings.get("electrical") or {}).get("product") if isinstance(c.ratings.get("electrical"), dict) else None,
            "bbox": [round(x, 2) for x in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)],
            "v": [off, len(v)], "t": [off + len(vb), len(t)],
            "mfg": mfg.get(c.name), "dxf": c.name in dxf, "findings": by_part.get(c.name, []), "color": c.color,
        })
        blob += [vb, tb]
        off += len(vb) + len(tb)
    groups = {"world": "Y drive and rails", "ybody": "Gantry beam (moves in Y)"}
    for name, body, sku, tm, mass, length, b in belt_parts(d, m.get("ratings", {}).get("bom", {}) or {}):
        v = np.asarray(tm.vertices, dtype=np.float32)
        t = np.asarray(tm.faces, dtype=np.uint32)
        vb, tb = v.tobytes(), t.tobytes()
        lo, hi = v.min(axis=0), v.max(axis=0)
        bl = (m.get("ratings", {}).get("bom", {}) or {}).get(sku) or {}
        parts.append({
            "name": name, "body": body, "kind": "purchased", "group": groups.get(body, "Frame"),
            "material": "rubber_gt2", "process": None, "sku": sku,
            "desc": f"GT2 timing belt, {b.width:g} mm wide, open length (cut from the BOM line's 1 m): {length:.0f} mm routed",
            "cost": bl.get("unit_cost_usd"), "mass": mass,
            "model": "proxy", "model_source": "belt route at the home pose (mechloop.verifiers.belts.route); display only",
            "model_file": None,
            "model_note": (f"Not a part of the design model: drawn from design.belts ({b.name}) as a {b.width:g} x {b.thickness:g} mm "
                           f"ribbon on the pitch line at the home pose. It moves with {'the gantry beam' if body != 'world' else 'the frame'} "
                           f"on this page and does not follow the carriage. Mass estimated at {BELT_DENSITY * 1e6:g} g/cm3."),
            "model_state": "stand-in", "vendor": False, "source": "", "product": None,
            "bbox": [round(float(x), 2) for x in (*lo, *hi)],
            "v": [off, len(v)], "t": [off + len(vb), len(t)],
            "mfg": None, "dxf": False, "findings": by_part.get(b.name, []), "color": "#161616",
        })
        blob += [vb, tb]
        off += len(vb) + len(tb)
    # base64 text: the page host serves text and JSON but not raw binary
    import base64

    (out / "meshes.txt").write_text(base64.b64encode(b"".join(blob)).decode())
    joints = [{"name": j.name, "parent": j.parent, "child": j.child, "axis": list(j.axis),
               "range": list(j.range) if j.range else [0, 0]} for j in d.joints]
    build = None
    if "--no-assembly" not in sys.argv:
        from mechloop.assembly.simulate import analyse, instructions

        res = analyse(d)
        res["metrics"].pop("_skus", None)
        build = {"metrics": res["metrics"],
                 "steps": [{k: r.get(k) for k in ("unit", "kind", "parts", "direction", "rests_stably", "tool", "note",
                                                  "seconds", "orientation") if k in r} for r in res["rows"]]}
        (out / "BUILD.md").write_text(instructions(d, res))
    el = m.get("electrical", {})
    scores = None
    sp = Path("out") / d.name / "scores.jsonl"
    if sp.exists():
        scores = json.loads(sp.read_text().strip().splitlines()[-1])
    cfg = Path("out") / d.name / "electrical" / "printer.cfg"
    data = {
        "design": d.name, "ok": rep["ok"], "summary": rep["summary"], "findings": rep["findings"],
        "parts": parts, "joints": joints, "build": build, "score": scores,
        "bom": m.get("ratings", {}).get("bom", {}), "bom_cost": m.get("ratings", {}).get("bom_cost_usd_estimate"),
        "mass": m.get("geometry", {}).get("mass_kg"), "bbox": m.get("geometry", {}).get("bbox_mm"),
        "tolerance": {k: m.get("tolerance", {}).get(k) for k in ("printer", "paired_rails", "lead_screws",
                                                                   "adjustments_declared", "builds_simulated")},
        "manufacture": {k: v for k, v in m.get("manufacture", {}).items() if k != "parts"},
        "electrical": {k: el.get(k) for k in ("off_the_shelf", "power_budget", "wire_table", "mains", "heaters", "bay",
                                              "steppers", "motor_temperature", "electrical_bom_cost_usd")},
        "motion": {"drives": m.get("motion", {}).get("drives"), "joints": m.get("motion", {}).get("joints")},
        "fea": m.get("fea"), "printing": m.get("printing"), "requirements": [f for f in rep["findings"] if f["verifier"] == "requirements"],
        "printer_cfg": cfg.read_text() if cfg.exists() else "",
    }
    if "--print" in sys.argv:
        data["print"] = export_print(Path(sys.argv[sys.argv.index("--print") + 1]), out)
    elif (out / "data.json").exists():
        data["print"] = json.loads((out / "data.json").read_text()).get("print")
    if "--no-assembly" in sys.argv and (out / "data.json").exists():
        data["build"] = json.loads((out / "data.json").read_text()).get("build")
    (out / "data.json").write_text(json.dumps(data, default=str, separators=(",", ":")))
    kinds = {}
    for p in parts:
        kinds[p["model"]] = kinds.get(p["model"], 0) + 1
    print("models:", kinds, "; meshes.txt", round((out / "meshes.txt").stat().st_size / 1e6, 2), "MB")
    print(len(parts), "parts;", round(off / 1e6, 2), "MB meshes;", round((out / "data.json").stat().st_size / 1e6, 2), "MB data;",
          sum(p["t"][1] for p in parts), "triangles")


if __name__ == "__main__":
    main()
