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
            "model_note": model.get("note"),
            "vendor": bool(c.meta.get("vendor_backed")), "source": src if isinstance(src, str) else json.dumps(src)[:300] if src else "",
            "product": (c.ratings.get("electrical") or {}).get("product") if isinstance(c.ratings.get("electrical"), dict) else None,
            "bbox": [round(x, 2) for x in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)],
            "v": [off, len(v)], "t": [off + len(vb), len(t)],
            "mfg": mfg.get(c.name), "dxf": c.name in dxf, "findings": by_part.get(c.name, []), "color": c.color,
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
