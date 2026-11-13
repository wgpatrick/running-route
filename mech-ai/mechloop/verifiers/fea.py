"""Linear static FEA per load case: build123d part -> Gmsh tet10 -> CalculiX.

The agent never writes a solver deck. It declares a LoadCase (fixed faces,
loaded faces, total force, targets) and gets typed numbers back, with built-in
sanity checks: applied-vs-reaction force balance, load-area check, fixture
stress-peak flagging and an automatic refinement run when margins are thin.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from ..model import MATERIALS, Design, LoadCase
from ..report import VerifierResult, timed

MAX_NODES = 250_000


def _mesh(shape, fixed_pred, load_pred, size: float, workdir: Path):
    import gmsh
    from build123d import export_brep

    faces = shape.faces()
    fixed = [f for f in faces if fixed_pred(f)]
    loaded = [f for f in faces if load_pred(f)]
    if not fixed or not loaded:
        return {"error": f"face selection matched fixed={len(fixed)} loaded={len(loaded)} faces"}
    brep = workdir / "part.brep"
    export_brep(shape, str(brep))
    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.occ.importShapes(str(brep))
        gmsh.model.occ.synchronize()
        surfs = [t for _, t in gmsh.model.getEntities(2)]
        info = [(t, np.array(gmsh.model.occ.getCenterOfMass(2, t)), gmsh.model.occ.getMass(2, t)) for t in surfs]

        def match(face):
            c = face.center()
            c = np.array([c.X, c.Y, c.Z])
            best = min(info, key=lambda i: np.linalg.norm(i[1] - c) + abs(i[2] - face.area) / max(face.area, 1e-9))
            ok = np.linalg.norm(best[1] - c) < 1e-3 * max(1.0, np.sqrt(face.area)) + 1e-3 and \
                abs(best[2] - face.area) < 1e-3 * max(face.area, 1.0)
            return best[0] if ok else None

        ftags = [match(f) for f in fixed]
        ltags = [match(f) for f in loaded]
        if None in ftags or None in ltags:
            return {"error": "could not map selected CAD faces onto mesh surfaces"}
        if set(ftags) & set(ltags):
            return {"error": "a face is both fixed and loaded"}
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.MeshSizeMin", size / 8)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 12)
        gmsh.option.setNumber("Mesh.ElementOrder", 2)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.model.mesh.generate(3)
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        xyz = xyz.reshape(-1, 3)
        idx = np.zeros(int(tags.max()) + 1, dtype=int)
        idx[tags.astype(int)] = np.arange(len(tags))
        etypes, _, enodes = gmsh.model.mesh.getElements(3)
        tets = None
        for et, en in zip(etypes, enodes):
            if et == 11:
                tets = idx[en.astype(int)].reshape(-1, 10)
        if tets is None:
            return {"error": "mesher produced no 10-node tetrahedra"}

        def tris(tag_list):
            out = []
            for t in tag_list:
                ets, _, ens = gmsh.model.mesh.getElements(2, t)
                for et, en in zip(ets, ens):
                    if et == 9:
                        out.append(idx[en.astype(int)].reshape(-1, 6))
            return np.vstack(out)

        return {"xyz": xyz, "tets": tets, "fixed_tris": tris(ftags), "load_tris": tris(ltags),
                "load_area_cad": sum(f.area for f in loaded), "fixed_area_cad": sum(f.area for f in fixed)}
    finally:
        gmsh.finalize()


def _tri_areas(xyz, tris):
    a, b, c = xyz[tris[:, 0]], xyz[tris[:, 1]], xyz[tris[:, 2]]
    return 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)


def _solve(mesh, material, force, workdir: Path, tag: str):
    xyz, tets = mesh["xyz"], mesh["tets"]
    fixed_nodes = np.unique(mesh["fixed_tris"])
    # consistent nodal loads for uniform traction on 6-node triangles: midside nodes carry A/3 each
    areas = _tri_areas(xyz, mesh["load_tris"])
    total_area = areas.sum()
    traction = np.array(force, dtype=float) / total_area
    nodal = {}
    for tri, A in zip(mesh["load_tris"], areas):
        for n in tri[3:]:
            nodal[n] = nodal.get(n, 0.0) + A / 3.0
    ccx_order = [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]  # gmsh tet10 -> CalculiX C3D10
    inp = workdir / f"{tag}.inp"
    with open(inp, "w") as f:
        f.write("*NODE, NSET=NALL\n")
        for i, p in enumerate(xyz, 1):
            f.write(f"{i},{p[0]:.9g},{p[1]:.9g},{p[2]:.9g}\n")
        f.write("*ELEMENT, TYPE=C3D10, ELSET=EALL\n")
        for i, t in enumerate(tets, 1):
            f.write(f"{i}," + ",".join(str(int(t[k]) + 1) for k in ccx_order) + "\n")
        f.write("*NSET, NSET=NFIX\n")
        for n in fixed_nodes:
            f.write(f"{int(n) + 1},\n")
        f.write(f"*MATERIAL, NAME=M\n*ELASTIC\n{material.E},{material.nu}\n")
        f.write("*SOLID SECTION, ELSET=EALL, MATERIAL=M\n")
        f.write("*BOUNDARY\nNFIX,1,3\n")
        f.write("*STEP\n*STATIC\n*CLOAD\n")
        for n, w in nodal.items():
            for d in range(3):
                v = traction[d] * w
                if abs(v) > 0:
                    f.write(f"{int(n) + 1},{d + 1},{v:.9g}\n")
        f.write("*NODE PRINT, NSET=NALL\nU\n")
        f.write("*NODE PRINT, NSET=NFIX, TOTALS=ONLY\nRF\n")
        f.write("*EL PRINT, ELSET=EALL\nS\n*END STEP\n")
    env = dict(os.environ, OMP_NUM_THREADS=str(os.cpu_count() or 1))
    p = subprocess.run(["ccx", tag], cwd=workdir, capture_output=True, text=True, env=env, timeout=1800)
    dat = workdir / f"{tag}.dat"
    if p.returncode != 0 or not dat.exists() or dat.stat().st_size == 0:
        return {"error": "CalculiX failed: " + (p.stdout[-400:] + p.stderr[-200:]).strip()}
    return _parse_dat(dat, len(xyz), len(tets)) | {"load_area_mesh": float(total_area),
                                                   "fixed_nodes": fixed_nodes}


def _parse_dat(dat: Path, n_nodes: int, n_el: int):
    U = np.zeros((n_nodes, 3))
    vm_el = np.zeros(n_el)
    rf = None
    mode = None
    with open(dat) as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            low = s.lower()
            if low.startswith("displacements"):
                mode = "u"; continue
            if low.startswith("total force"):
                mode = "rf"; continue
            if low.startswith("stresses"):
                mode = "s"; continue
            parts = s.split()
            try:
                if mode == "u" and len(parts) == 4:
                    U[int(parts[0]) - 1] = [float(x) for x in parts[1:]]
                elif mode == "rf" and len(parts) == 3:
                    rf = np.array([float(x) for x in parts])
                elif mode == "s" and len(parts) == 8:
                    e = int(parts[0]) - 1
                    sx, sy, sz, sxy, sxz, syz = (float(x) for x in parts[2:])
                    vm = np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2)
                                 + 3 * (sxy ** 2 + sxz ** 2 + syz ** 2))
                    if vm > vm_el[e]:
                        vm_el[e] = vm
            except ValueError:
                continue
    return {"U": U, "vm_el": vm_el, "rf": rf}


def run_loadcase(design: Design, lc: LoadCase, r: VerifierResult, keep_dir: Path | None = None) -> dict:
    comp = design.get(lc.component)
    mat = MATERIALS[comp.material]
    bb = comp.shape.bounding_box()
    diag = float(np.linalg.norm([bb.size.X, bb.size.Y, bb.size.Z]))
    size = lc.mesh_size or max(diag / 30.0, 0.4)
    force = np.array(lc.force, dtype=float)
    out: dict = {"component": lc.component, "material": mat.name}
    workdir = Path(tempfile.mkdtemp(prefix="mechloop_fea_"))
    try:
        runs = []
        for attempt in range(2):
            mesh = _mesh(comp.shape, lc.fixed, lc.loaded, size, workdir)
            if "error" in mesh:
                r.add("error", "fea_setup", f"{lc.name}: {mesh['error']}.", loadcase=lc.name,
                      hint="Check the fixed/loaded face predicates select the faces you intend.")
                return out
            if len(mesh["xyz"]) > MAX_NODES:
                if not runs:
                    r.add("error", "fea_too_large",
                          f"{lc.name}: mesh has {len(mesh['xyz'])} nodes (> {MAX_NODES}); set a larger mesh_size.",
                          loadcase=lc.name)
                    return out
                break
            res = _solve(mesh, mat, force, workdir, f"run{attempt}")
            if "error" in res:
                r.add("error", "fea_solver", f"{lc.name}: {res['error']}", loadcase=lc.name)
                return out
            tets, xyz = mesh["tets"], mesh["xyz"]
            fixed_mask = np.zeros(len(xyz), dtype=bool)
            fixed_mask[res["fixed_nodes"]] = True
            at_fixture = fixed_mask[tets].any(axis=1)
            vm = res["vm_el"]
            peak_all = float(vm.max())
            free = vm[~at_fixture]
            peak = float(free.max()) if len(free) else peak_all
            e_peak = int(np.flatnonzero(~at_fixture)[free.argmax()]) if len(free) else int(vm.argmax())
            where = xyz[tets[e_peak, :4]].mean(axis=0).round(1).tolist()
            umag = np.linalg.norm(res["U"], axis=1)
            runs.append({"mesh_size": round(size, 3), "nodes": len(xyz), "elements": len(tets),
                         "peak_vm_mpa": round(peak, 2), "peak_vm_incl_fixture_mpa": round(peak_all, 2),
                         "peak_at": where, "max_deflection_mm": float(umag.max()),
                         "deflection_at": xyz[umag.argmax()].round(1).tolist(),
                         "rf": res["rf"], "load_area_mesh": res["load_area_mesh"],
                         "load_area_cad": mesh["load_area_cad"]})
            fos = mat.yield_mpa / peak if peak > 0 else float("inf")
            # refine once when the margin is thin enough for mesh error to change the verdict
            if attempt == 0 and fos < 2.0 * lc.min_fos and len(xyz) < MAX_NODES / 3:
                size *= 0.6
                continue
            break
        last = runs[-1]
        # --- sanity checks -------------------------------------------------
        rf = last.pop("rf")
        fmag = float(np.linalg.norm(force))
        if rf is None:
            r.add("error", "fea_no_reactions", f"{lc.name}: no reaction forces in solver output.", loadcase=lc.name)
        else:
            imbalance = float(np.linalg.norm(rf + force)) / max(fmag, 1e-12)
            out["reaction_imbalance"] = round(imbalance, 5)
            if imbalance > 0.01:
                r.add("error", "fea_unbalanced",
                      f"{lc.name}: reactions {rf.round(2).tolist()} do not balance applied load "
                      f"{force.tolist()} ({imbalance:.1%} off); result is not trustworthy.", loadcase=lc.name)
        a_err = abs(last["load_area_mesh"] - last["load_area_cad"]) / last["load_area_cad"]
        if a_err > 0.03:
            r.add("warning", "fea_load_area", f"{lc.name}: meshed load area differs from CAD by {a_err:.1%}.",
                  loadcase=lc.name)
        peak = last["peak_vm_mpa"]
        fos = mat.yield_mpa / peak if peak > 0 else float("inf")
        out.update({"fos": round(fos, 2), "min_fos": lc.min_fos, "yield_mpa": mat.yield_mpa,
                    "peak_vm_mpa": peak, "peak_at": last["peak_at"],
                    "max_deflection_mm": round(last["max_deflection_mm"], 4),
                    "deflection_at": last["deflection_at"], "nodes": last["nodes"],
                    "mesh_size": last["mesh_size"],
                    "applied_force_n": force.tolist(), "load_area_mm2": round(last["load_area_cad"], 2)})
        if len(runs) == 2:
            change = abs(runs[1]["peak_vm_mpa"] - runs[0]["peak_vm_mpa"]) / max(runs[1]["peak_vm_mpa"], 1e-9)
            out["refinement_change"] = round(change, 3)
            if change > 0.15:
                r.add("warning", "fea_not_converged",
                      f"{lc.name}: peak stress moved {change:.0%} on refinement "
                      f"({runs[0]['peak_vm_mpa']} -> {runs[1]['peak_vm_mpa']} MPa); likely a stress "
                      f"concentration (sharp inside corner?) - add a fillet or treat the FoS as approximate.",
                      loadcase=lc.name, peak_at=last["peak_at"])
        if last["peak_vm_incl_fixture_mpa"] > 1.5 * peak:
            r.add("info", "fea_fixture_peak",
                  f"{lc.name}: raw peak {last['peak_vm_incl_fixture_mpa']} MPa is at the fixed boundary "
                  f"(artificially stiff clamp); governing stress taken away from it.", loadcase=lc.name)
        if fos < lc.min_fos:
            r.add("error", "fos_low",
                  f"{lc.name}: factor of safety {fos:.2f} < {lc.min_fos} on {lc.component} "
                  f"(peak von Mises {peak:.1f} MPa vs yield {mat.yield_mpa} MPa at {last['peak_at']}).",
                  loadcase=lc.name, fos=round(fos, 2), peak_at=last["peak_at"],
                  hint="Add material or a fillet/rib near the peak location, shorten the load path, or use a stronger material.")
        if lc.max_deflection is not None and last["max_deflection_mm"] > lc.max_deflection:
            r.add("error", "deflection_high",
                  f"{lc.name}: deflection {last['max_deflection_mm']:.3f} mm > {lc.max_deflection} mm "
                  f"at {last['deflection_at']}.", loadcase=lc.name,
                  deflection=round(last["max_deflection_mm"], 4),
                  hint="Stiffness scales with section depth cubed: deepen the section or add ribs/gussets.")
        if fos > 8 * lc.min_fos and not comp.cots:
            r.add("info", "overbuilt", f"{lc.name}: FoS {fos:.1f} is far above the {lc.min_fos} target; "
                  f"mass could be removed.", loadcase=lc.name)
        if keep_dir:
            keep_dir.mkdir(parents=True, exist_ok=True)
            for p in workdir.glob("run*.inp"):
                shutil.copy(p, keep_dir / f"{lc.name}_{p.name}")
        return out
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def verify_fea(design: Design, keep_dir: Path | None = None) -> VerifierResult:
    r = VerifierResult("fea")
    if not design.loadcases:
        r.skipped = "design has no load cases"
        return r
    if not shutil.which("ccx"):
        r.add("error", "fea_unavailable", "CalculiX (ccx) is not installed; FEA was NOT run.")
        return r
    with timed(r):
        for lc in design.loadcases:
            try:
                r.metrics[lc.name] = run_loadcase(design, lc, r, keep_dir)
            except Exception as e:
                r.add("error", "fea_crashed", f"{lc.name}: {type(e).__name__}: {e}", loadcase=lc.name)
    return r
