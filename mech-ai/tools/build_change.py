"""Build, check and export ONE design change as a review-page change set (docs/OPERATING_MODES.md, iterative mode).

    .venv/bin/python tools/build_change.py designs/printer_v12_1.py <change-id> [--verify] [--checks "extra text"]
                                           [--out review_v12_1/changes] [--base-report out/printer_v12/report.json]

The design file declares its change flags (CHANGE_IDS, CHANGE_DEPENDS, CHANGE_INFO) and reads MECHLOOP_CHANGES from the
environment ("none" = the base, "a,b" = the base plus those changes). This tool

1. with --verify: seeds out/<variant>/verify_cache from the base's cache (so the affected tier re-runs only what the change
   touches) and runs `python -m mechloop verify <design> --tier affected --no-render` for base + the change (+ the changes it
   depends on). One heavy job: run nothing else beside it.
2. builds the base (all flags off) and the variant in this process, diffs them part by part (name, SKU, material, volume,
   bounding box): removed / modified / added;
3. writes <out>/<id>.json (part records with the review page's fields and "v"/"t" offsets), <out>/<id>.txt (base64 of float32
   vertices + uint32 triangles for the modified and added parts only, offsets from 0) and merges the entry into <out>/index.json.

"checks" in the index is generated from the variant's report against the base report (verifier errors / warnings and failed
requirements, part count), plus --checks text.
"""
from __future__ import annotations

import argparse
import re as _re
import base64
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

MAX_TXT_BYTES = 12_000_000          # keep each change blob well under the host's 16 MB per file


def build(design: str, on: list[str]):
    from mechloop.runner import load_design

    os.environ["MECHLOOP_CHANGES"] = ",".join(on) if on else "none"
    return load_design(design)


def design_module(design: str):
    import importlib.util

    os.environ["MECHLOOP_CHANGES"] = "none"
    spec = importlib.util.spec_from_file_location("design_flags_probe", Path(design).resolve())
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def signature(c) -> tuple:
    bb = c.shape.bounding_box()
    return (c.sku, c.material, round(float(c.shape.volume), 1),
            tuple(round(v, 2) for v in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)))


def with_deps(cid: str, deps: dict) -> list[str]:
    out, todo = [], [cid]
    while todo:
        k = todo.pop()
        if k not in out:
            out.append(k)
            todo += list(deps.get(k, ()))
    return out


def run_verify(design: str, on: list[str], name: str, base_name: str) -> Path:
    out = ROOT / "out" / name
    seed = ROOT / "out" / base_name / "verify_cache"
    # the newest cache of a sibling variant (same design file) is usually fresher than the base's (its code manifest matches)
    sib = sorted((p_ for p_ in (ROOT / "out").glob(name.split("+")[0] + "+*/verify_cache") if (p_.parent / "report.json").exists()),
                 key=lambda p_: (p_.parent / "report.json").stat().st_mtime)
    if sib:
        seed = sib[-1]
    if not (out / "verify_cache").exists() and seed.exists():
        out.mkdir(parents=True, exist_ok=True)
        shutil.copytree(seed, out / "verify_cache")
    env = dict(os.environ, MECHLOOP_CHANGES=",".join(on))
    t = time.time()
    r = subprocess.run([sys.executable, "-m", "mechloop", "verify", design, "--tier", "affected", "--no-render"],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=7200)
    (out / "build_change_verify.log").write_text(r.stdout[-20000:] + "\n---\n" + r.stderr[-20000:])
    print(f"verify {name}: exit {r.returncode} in {time.time() - t:.0f} s")
    return out / "report.json"


def _key(f):
    return (f["verifier"], f["code"], f.get("message", "").split(":")[0][:120])


def new_errors(rep: dict, base: dict, changed: set) -> tuple[list, list]:
    """Errors of the variant not in the base, split into (new, noise). Matched on verifier, code and the message's subject
    (the text before its first colon: a part, a pair "a to b", a screw). `noise`: the base has the same finding as a WARNING
    and none of the parts it names is changed by the change: a Monte Carlo share sitting at its limit (e.g. 0.90 % in v12,
    1.1 % here, limit 1 %) that crossed it because the sampling differs, not because of the change."""
    e0 = {_key(f) for f in base["findings"] if f["severity"] == "error"}
    w0 = {_key(f) for f in base["findings"] if f["severity"] == "warning"}
    new, noise = [], []
    for f in rep["findings"]:
        if f["severity"] != "error" or _key(f) in e0:
            continue
        names = set(_re.findall(r"[A-Za-z][A-Za-z0-9_]+", _key(f)[2]))
        (noise if _key(f) in w0 and not (names & changed) else new).append(f)
    return new, noise


def summarize(rep: dict, base: dict | None, n_parts: int, n_base: int, changed: set = frozenset()) -> str:
    """Plain, self-consistent text: the affected-tier result against v12's, errors new / cleared, warnings delta, part count."""
    def nwarn(r):
        return sum(1 for f in r["findings"] if f["severity"] == "warning")

    errs = [f for f in rep["findings"] if f["severity"] == "error"]
    out = [f"affected-tier verify: {len(errs)} errors, {nwarn(rep)} warnings"]
    if base:
        e0 = [f for f in base["findings"] if f["severity"] == "error"]
        out[0] += f" (v12: {len(e0)} errors, {nwarn(base)} warnings)"
        new, noise = new_errors(rep, base, set(changed))
        k_now = {_key(f) for f in errs}
        gone = [f for f in e0 if _key(f) not in k_now]
        if not new and not gone:
            out.append("no error new or cleared against v12")
        if new:
            out.append(f"{len(new)} NEW error(s): " + "; ".join(f"{f['verifier']}/{f['code']}: {f['message'][:140]}" for f in new[:4]))
        if gone:
            out.append(f"{len(gone)} error(s) cleared: " + "; ".join(f"{f['verifier']}/{f['code']}: {f['message'][:140]}" for f in gone[:4]))
        if noise:
            out.append("not caused by the change (a v12 warning at its Monte Carlo limit, on parts the change does not touch, "
                       "crossing it by sampling): " + "; ".join(f"{f['verifier']}/{f['code']}: {f['message'][:200]}" for f in noise[:3]))
        rest = [f for f in errs if f not in new and f not in noise]
        if rest and all(f["verifier"] == "practice" and "DG-07" in f["message"] for f in rest):
            out.append("the other errors are the existing practice DG-07 placeholder-part rule (as in v12)")
    else:
        out.append("no base report to compare")
    out.append(f"parts {n_base} -> {n_parts} ({n_parts - n_base:+d})")
    return "; ".join(out)


def _pq_keys(d, parts, names):
    from mechloop.verifiers.part_quality import verify_part_quality

    res = verify_part_quality(d, parts or None, audits=True)
    return {f"{(f.data or {}).get('part', '?')} {f.code}" for f in res.findings if f.severity != "info"
            and ((f.data or {}).get("part") in names or any(_re.search(r"(?<![A-Za-z0-9_])" + _re.escape(n) + r"(?![A-Za-z0-9_])", f.message) for n in names))}


def part_quality_text(d, parts: list[str], changed: list[str], removed: list[str], base=None) -> str:
    """The opt-in part-quality checks (mechloop/verifiers/part_quality.py): the per-part checks on the change's custom parts,
    and the design-wide audits (allowed overlaps, joins by note, purchased-part holes) wherever they name a changed part."""
    from mechloop.verifiers.part_quality import verify_part_quality

    res = verify_part_quality(d, parts or None, audits=True)
    names = set(changed)
    mine = [f for f in res.findings if f.severity != "info"
            and ((f.data or {}).get("part") in names or any(_re.search(r"(?<![A-Za-z0-9_])" + _re.escape(n) + r"(?![A-Za-z0-9_])", f.message) for n in names))]
    head = f"part_quality ({len(parts)} changed custom part(s), audits on every changed part)"
    cleared = ""
    if base is not None:
        bnames = {c.name for c in base.components}
        was = _pq_keys(base, [n for n in parts if n in bnames], names & bnames | set(removed))
        now = {f"{(f.data or {}).get('part', '?')} {f.code}" for f in mine}
        gone = sorted(was - now)
        if gone:
            cleared = "; cleared against v12: " + ", ".join(gone)
    if not mine:
        return head + ": clean (no errors or warnings)" + cleared
    by = {}
    for f in mine:
        by.setdefault(f.severity, []).append(f"{(f.data or {}).get('part', '?')} {f.code}")
    return head + ": " + "; ".join(f"{len(v)} {k}(s): {', '.join(sorted(set(v)))}" for k, v in sorted(by.items())) + cleared


def part_record(c, electronics, findings) -> tuple[dict, bytes, bytes]:
    from export_viewer import FASTENER_TRI_BUDGET, _placeholder, d_density, detail_mesh, group_of, kind_of, light_fastener_mesh
    from build_review import MATERIAL, PROCESS, SHOP
    from mechloop.geom import to_trimesh

    try:
        tm = detail_mesh(c) if c.detail is not None else to_trimesh(c.shape, 0.12, 0.45)
    except AttributeError:
        tm = to_trimesh(c.shape, 0.12, 0.45)
    if kind_of(c) == "fastener" and len(tm.faces) > FASTENER_TRI_BUDGET:
        tm, _ = light_fastener_mesh(c)
    v = np.asarray(tm.vertices, dtype=np.float32)
    t = np.asarray(tm.faces, dtype=np.uint32)
    bb = c.shape.bounding_box()
    kind = kind_of(c)
    proc = c.meta.get("process") or c.process if hasattr(c, "process") else c.meta.get("process")
    model = c.meta.get("model") or {"kind": "proxy" if c.cots else "design", "source": ""}
    rec = {"name": c.name, "kind": kind, "group": group_of(c, electronics), "sku": c.sku, "desc": c.meta.get("description", ""),
           "cost": c.meta.get("cost_usd"), "mass": round(float(c.mass_kg or c.shape.volume * 1e-9 * d_density(c)), 4),
           "bbox": [round(x, 2) for x in (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)], "body": c.body,
           "material_code": c.material, "material": MATERIAL.get(c.material, c.material),
           "process": PROCESS.get(proc) if kind == "fabricated" else None, "process_code": proc,
           "shop": SHOP.get(proc) if kind == "fabricated" else None, "model": model.get("kind"), "model_source": model.get("source", ""),
           "findings": findings.get(c.name, []), "color": c.color}
    rec.update({k: v_ for k, v_ in _placeholder(c).items() if k in ("real_part_state", "placeholder", "placeholder_why", "color")})
    return rec, v.tobytes(), t.tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("design")
    ap.add_argument("change")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--checks", default="")
    ap.add_argument("--out", default="review_v12_1/changes")
    ap.add_argument("--base-report", default=None, help="report of the base design (default out/<base name>/report.json)")
    ap.add_argument("--base-name", default="printer_v12", help="the base revision's design name (its out/ folder)")
    ap.add_argument("--status", default="proposed")
    a = ap.parse_args()

    mod = design_module(a.design)
    ids, deps, info = mod.CHANGE_IDS, getattr(mod, "CHANGE_DEPENDS", {}), getattr(mod, "CHANGE_INFO", {})
    if a.change not in ids:
        sys.exit(f"{a.change} is not a change of {a.design}: {ids}")
    on = [k for k in ids if k in with_deps(a.change, deps)]

    rep_path = None
    if a.verify:
        probe = build(a.design, on)
        rep_path = run_verify(a.design, on, probe.name, a.base_name)
        del probe
    base = build(a.design, [])
    var = build(a.design, on)
    sb = {c.name: signature(c) for c in base.components}
    sv = {c.name: c for c in var.components}
    removed = sorted(n for n in sb if n not in sv)
    added = sorted(n for n in sv if n not in sb)
    modified = sorted(n for n in sv if n in sb and signature(sv[n]) != sb[n])
    print(f"{a.change} (flags {on}): removed {len(removed)}, modified {len(modified)}, added {len(added)}")

    rep = None
    rp = Path(rep_path) if rep_path else ROOT / "out" / var.name / "report.json"
    if rp.exists():
        rep = json.loads(rp.read_text())
    findings = {}
    if rep:
        for f in rep["findings"]:
            p = (f.get("data") or {}).get("part")
            if p:
                findings.setdefault(p, []).append({k: f[k] for k in ("verifier", "severity", "code", "message")} | {"hint": (f.get("data") or {}).get("hint", "")})
    bpath = Path(a.base_report) if a.base_report else ROOT / "out" / a.base_name / "report.json"
    brep = json.loads(bpath.read_text()) if bpath.exists() else None

    electronics = set(var.subassemblies.get("electronics", []))
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    blob, recs, off = [], [], 0
    for n in modified + added:
        rec, vb, tb = part_record(sv[n], electronics, findings)
        rec["change"] = "modified" if n in modified else "added"
        rec["v"] = [off, len(vb) // 12]
        rec["t"] = [off + len(vb), len(tb) // 12]
        blob += [vb, tb]
        off += len(vb) + len(tb)
        recs.append(rec)
    txt = base64.b64encode(b"".join(blob)).decode()
    if len(txt) > MAX_TXT_BYTES:
        print(f"WARNING: {a.change}.txt is {len(txt) / 1e6:.1f} MB (limit {MAX_TXT_BYTES / 1e6:.0f})")
    (out / f"{a.change}.txt").write_text(txt)
    (out / f"{a.change}.json").write_text(json.dumps({"mesh": f"changes/{a.change}.txt", "parts": recs}, separators=(",", ":"), default=str))

    checks = summarize(rep, brep, len(var.components) + len(var.belts), len(base.components) + len(base.belts), set(modified + added + removed)) if rep else "not verified (run with --verify)"
    pq = part_quality_text(var, [n for n in modified + added if not sv[n].cots], modified + added, removed, base)
    if pq:
        checks += "; " + pq
    if a.checks:
        checks += "; " + a.checks
    status, why = a.status, None
    if rep and brep:
        new, _ = new_errors(rep, brep, set(modified + added + removed))
        if new:
            status = "needs work"
            why = f"{len(new)} error(s) not in v12: " + ", ".join(sorted({f"{f['verifier']}/{f['code']}" for f in new})[:4])
    elif not rep:
        status = "needs work"
        why = "not verified"
    ci = info.get(a.change, {})
    entry = {"id": a.change, "title": ci.get("title", a.change), "summary": ci.get("summary", ""), "threads": ci.get("threads", []),
             "status": status, **({"status_reason": why} if why else {}), "depends_on": [k for k in on if k != a.change], "removed": removed, "modified": modified,
             "added": added, "checks": checks, "file": f"changes/{a.change}.json", "design": var.name}
    ip = out / "index.json"
    idx = json.loads(ip.read_text()) if ip.exists() else {"base": a.base_name, "changes": []}
    idx["changes"] = [c for c in idx["changes"] if c["id"] != a.change] + [entry]
    order = {k: i for i, k in enumerate(ids)}
    idx["changes"].sort(key=lambda c: order.get(c["id"], 99))
    ip.write_text(json.dumps(idx, indent=1))
    print(f"wrote {out}/{a.change}.json ({len(recs)} parts), {a.change}.txt ({len(txt) / 1e6:.2f} MB); checks: {checks}")


if __name__ == "__main__":
    main()
