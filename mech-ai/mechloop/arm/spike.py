"""Run the Arm Build 1 concept spike: task poses, decisive tests 1 and 2 on three skeleton arms, figures.

    .venv/bin/python -m mechloop.arm.spike            # full run (~5 min), writes mechloop/data/arm/*.json, docs/arm_spike/*.png
    .venv/bin/python -m mechloop.arm.spike --quick    # smaller optimiser budget

Costs are est. (02_actuators.md section 6 single-unit prices, ARM_SCOPE budget table for the rest of the cell).
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
from pathlib import Path

import numpy as np

from . import accuracy as A
from . import cell as C
from . import poses as PZ
from . import reach as R
from .candidates import ENCODERS, K_TILT, TRANSMISSIONS, linear_spec, rotary_spec, servo_spec

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "mechloop" / "data" / "arm" / "spike_results.json"
FIG_DIR = ROOT / "docs" / "arm_spike"
TILT_UPGRADE_USD = 30.0       # est. per rotary joint: angular-contact pair + aluminium housing instead of printed
# rest of the cell from the ARM_SCOPE section 11 budget table (midpoints of its ranges, est.)
REST_OF_CELL = {"structure": 400, "controllers_computer": 275, "end_effectors": 250, "perception": 300, "safety": 350,
                "stations": 200}
REST_OF_CELL_CART = dict(REST_OF_CELL, controllers_computer=200)   # Klipper board instead of CAN servo drives


# ---------------------------------------------------------------- configurations for test 2
def scara_configs():
    for enc, kt, link in itertools.product([None, "AS5047P", "MT6835", "AksIM-2"], ["printed", "metal"],
                                           ["al_60x30x2", "al_80x40x3", "petg_60x30x3"]):
        specs = [rotary_spec("belt_2stage", enc), rotary_spec("belt_2stage", enc), linear_spec("leadscrew"),
                 servo_spec("XL430")]
        cost = sum(s["cost"] for s in specs) + 35 + (2 * TILT_UPGRADE_USD if kt == "metal" else 0)   # +Z rail est.
        yield dict(label=f"belt+{enc or 'motor-enc'} / {kt} bearings / {link}", specs=specs, k_tilt=K_TILT[kt],
                   link=link, cost=cost, enc=enc, tilt=kt)


def art_configs():
    wrists = {"XL430": servo_spec("XL430"), "XM430": servo_spec("XM430"),
              "belt+AS5047P": rotary_spec("belt_2stage", "AS5047P"), "belt+MT6835": rotary_spec("belt_2stage", "MT6835"),
              "strainwave_50": rotary_spec("strainwave_50", None)}
    for enc, wname, kt, link in itertools.product([None, "AS5047P", "MT6835"], list(wrists), ["printed", "metal"],
                                                  ["al_60x30x2", "petg_60x30x3"]):
        specs = [rotary_spec("belt_2stage", enc), rotary_spec("capstan_25", enc), rotary_spec("capstan_25", enc),
                 wrists[wname], servo_spec("XL430")]
        cost = sum(s["cost"] for s in specs) + 28 + (3 * TILT_UPGRADE_USD if kt == "metal" else 0)  # +brake motor (02)
        yield dict(label=f"{enc or 'motor-enc'} proximal / wrist {wname} / {kt} bearings / {link}", specs=specs,
                   k_tilt=K_TILT[kt], link=link, cost=cost, enc=enc, wrist=wname, tilt=kt)


def cart_configs(arm):
    xs = arm.params["x_max"] - arm.params["x_min"] + 300
    for ram in ["al_40x40x2", "al_60x30x2"]:
        specs = [linear_spec("belt"), linear_spec("leadscrew"), linear_spec("belt"), servo_spec("XL430")]
        rails = 2 * 60.0 * xs / 1000 + 35 + 45     # 2 x MGN15 along X at $60/m, Z and ram MGN12 rails (est.)
        yield dict(label=f"belts + T8 Z / ram {ram}", specs=specs, ram=ram, cost=sum(s["cost"] for s in specs) + rails)


def apply_config(arm, cfg):
    arm.joint_specs = cfg["specs"]
    if "k_tilt" in cfg:
        arm.k_tilt = cfg["k_tilt"]
    if "link" in cfg:
        arm.link_sec = cfg["link"]
    if "ram" in cfg:
        arm.ram_sec = cfg["ram"]


# ---------------------------------------------------------------- figures
def figure_workspace(results, arms, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Arc, Rectangle

    fig, axes = plt.subplots(1, 3, figsize=(16, 7.2), constrained_layout=True)
    poses = PZ.build_poses()
    for ax, (kind, arm) in zip(axes, arms.items()):
        res = results[kind]
        z_t = res["z_t"]
        lay = arm.layout
        ax.add_patch(Rectangle((-C.ENV_W / 2, 0), C.ENV_W, C.ENV_D, fc="#d9d9d9", ec="#555", lw=1))
        ax.add_patch(Rectangle((-C.OPEN_HALF_X, 0), 2 * C.OPEN_HALF_X, C.PLATE_FRONT, fc="#f2f2f2", ec="none"))
        ax.add_patch(Rectangle((C.SHEET_CX - 110, C.SHEET_FRONT), 220, 220, fc="#b7d3e8", ec="#3b6e91", lw=0.8))
        ax.text(0, 330, "printer v12 proxy", ha="center", fontsize=8)
        ax.add_patch(Rectangle((C.SHELF_X[0], C.SHELF_Y[0]), C.SHELF_X[1] - C.SHELF_X[0], C.SHELF_Y[1] - C.SHELF_Y[0],
                               fc="none", ec="#3b6e91", ls="--", lw=0.8))
        ax.add_patch(Rectangle((C.SHELF_X[0] + C.SHELF_TRAVEL, C.SHELF_Y[0]), C.SHELF_X[1] - C.SHELF_X[0],
                               C.SHELF_Y[1] - C.SHELF_Y[0], fc="#eef4f9", ec="#3b6e91", lw=0.8))
        ax.text(C.SHELF_X[0] + C.SHELF_TRAVEL + 125, -140, "shelf\n(stowed)", ha="center", fontsize=7)
        ax.text(-15, -140, "shelf (deployed)", ha="center", fontsize=7, color="#3b6e91")
        h = C.DOOR_HINGE
        ax.add_patch(Arc(h, 2 * C.HANDLE_R, 2 * C.HANDLE_R, theta1=-C.DOOR_OPEN_DEG, theta2=0, color="#c0504d", lw=0.8,
                         ls=":"))
        for d in (0.0, C.DOOR_OPEN_DEG):
            p1 = h + C.DOOR_W * C.door_dir(d)
            ax.plot([h[0], p1[0]], [h[1], p1[1]], color="#c0504d", lw=2)
        for n, (x0, x1, y0, y1, top) in C.stations(lay).items():
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="#fbe5c8", ec="#b07020", lw=0.8))
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, n.replace("_", "\n"), ha="center", va="center", fontsize=7)
        # reachable TCP points at station height (gripper, top-down) on a grid: IK + limits only
        xs, ys = np.meshgrid(np.arange(-1000, 1050, 25), np.arange(-950, 250, 25))
        ok = np.zeros(xs.shape, bool)
        for i, j in np.ndindex(xs.shape):
            for q in arm.ik(np.array([xs[i, j], ys[i, j], 120.0]), PZ.TOOLS["gripper"][0]):
                if arm.margin_deg(q) >= 0:
                    ok[i, j] = True
        ax.scatter(xs[ok], ys[ok], s=2, c="#7fb27f", alpha=0.5, lw=0)
        # arm drawn at three task poses
        byid = {r["id"]: r for r in res["reach"]}
        for pid, col in (("A2_tab_engage", "#1f4e79"), ("A5_pull_full", "#2e75b6"), ("A0_door_open", "#c0504d"),
                         ("C2_place_in_nest", "#7030a0")):
            r = byid.get(pid)
            if not r or not r["qs"]:
                continue
            pose = [p for p in poses if p["id"] == pid][0]
            q = np.array(r["qs"][-1])
            for c in arm.capsules(q, PZ.TOOLS[pose["tool"]]):
                if c.name in ("x_beam",):
                    continue
                ax.plot([c.a[0], c.b[0]], [c.a[1], c.b[1]], color=col, lw=2.2 if not c.tool else 1.2, alpha=0.85,
                        solid_capstyle="round")
        if kind == "cartesian":
            P = arm.params
            ax.add_patch(Rectangle((P["x_min"] - 120, P["y_m"] - 50), P["x_max"] - P["x_min"] + 240, 100, fc="#ccc",
                                   ec="#666", lw=0.8))
        ax.set_aspect("equal")
        ax.set_xlim(-1000, 1050)
        ax.set_ylim(-950, 450)
        s = res["summary"]
        ax.set_title(f"{arm.name}\nreach {'PASS' if s['reach_pass'] else 'FAIL'}, min clearance "
                     f"{s['min_clearance']:.0f} mm, z_T {z_t:.0f} mm", fontsize=10)
        ax.tick_params(labelsize=7)
        ax.set_xlabel("x (mm)", fontsize=8)
    axes[0].set_ylabel("y into printer (mm)", fontsize=8)
    fig.suptitle("Arm Build 1 concept spike: top view of each candidate over the cell (green: reachable TCP at z 120 "
                 "with a top-down gripper; arm drawn at tab engage, sheet fully out, door 85 deg, nest)", fontsize=10)
    fig.savefig(path, dpi=110)
    plt.close(fig)


def figure_errors(results, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), constrained_layout=True)
    for ax, cls in zip(axes, ("assembly", "sheet")):
        labels, vals, cols = [], [], []
        for kind, res in results.items():
            for row in res["accuracy_highlights"]:
                labels.append(f"{kind}: {row['short']}")
                vals.append(row[cls])
                cols.append({"scara": "#2e75b6", "cartesian": "#548235", "articulated5": "#c55a11"}[kind])
        y = np.arange(len(labels))
        ax.barh(y, vals, color=cols)
        ax.axvline(A.LIMITS[cls], color="k", ls="--", lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=7)
        ax.invert_yaxis()
        ax.set_xscale("log")
        ax.set_xlabel(f"worst 3-sigma error, mm ({'lateral' if cls == 'assembly' else '3D'}); limit {A.LIMITS[cls]} mm",
                      fontsize=8)
        ax.set_title(f"{cls} poses", fontsize=10)
    fig.suptitle("Decisive test 2: tool-point error Monte Carlo per candidate and joint recipe (est. inputs)", fontsize=10)
    fig.savefig(path, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------- main
def run(quick=False, log=print):
    t0 = time.time()
    poses = PZ.save()
    log(f"poses: {len(poses)} written to {PZ.DATA}")
    budget = dict(n_random=120, n_local=120) if quick else dict(n_random=300, n_local=300)
    results, arms = {}, {}
    for kind in ("scara", "cartesian", "articulated5"):
        b = dict(n_random=40, n_local=0) if kind == "cartesian" else budget
        arm, z_t, res, best = R.optimise(kind, poses, log=log, **b)
        arms[kind] = arm
        req = [r for r in res if r.required]
        reach_pass = all(r.ok for r in req)
        pull = R.max_straight_pull(arm, z_t)
        log(f"{kind}: reach {'PASS' if reach_pass else 'FAIL'} zT {z_t} params {arm.params} pull {pull}")
        # test 2 over the configuration grid
        cfgs = list(cart_configs(arm)) if kind == "cartesian" else list(scara_configs() if kind == "scara" else art_configs())
        acc = []
        for cfg in cfgs:
            apply_config(arm, cfg)
            rows = A.evaluate_arm(arm, poses, res, n=3000)
            s = A.summarise(rows)
            acc.append({"label": cfg["label"], "cost_actuation_usd": round(cfg["cost"]), "summary": s,
                        "passes": all(v["passes"] for v in s.values()),
                        "cfg": {k: v for k, v in cfg.items() if k not in ("specs",)},
                        "rows": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows]})
        passing = [a for a in acc if a["passes"]]
        chosen = min(passing, key=lambda a: a["cost_actuation_usd"]) if passing else \
            min(acc, key=lambda a: max(v["worst_p3s"] / v["limit"] for v in a["summary"].values()))
        apply_config(arm, [c for c in cfgs if c["label"] == chosen["label"]][0])
        rest = REST_OF_CELL_CART if kind == "cartesian" else REST_OF_CELL
        door = [r for r in res if r.id == "A0_door_open"][0]
        results[kind] = {
            "name": arm.name, "layout": arm.layout, "z_t": z_t,
            "params": {k: round(float(v), 1) for k, v in arm.params.items()},
            "max_straight_pull_mm": pull,
            "reach": [{"id": r.id, "required": r.required, "ok": r.ok, "reach": r.reach,
                       "clearance": None if not np.isfinite(r.clearance) else round(r.clearance, 1),
                       "limiter": r.limiter, "margin": round(float(r.margin), 1), "tilt": r.tilt, "note": r.note,
                       "qs": r.qs} for r in res],
            "summary": {"reach_pass": reach_pass, "min_clearance": min(r.clearance for r in req),
                        "min_clearance_at": min(req, key=lambda r: r.clearance).id,
                        "failed": [r.id for r in res if not r.ok], "door_ok": door.ok,
                        "door_clearance": round(door.clearance, 1)},
            "accuracy": [{k: v for k, v in a.items() if k != "rows"} for a in acc],
            "accuracy_chosen": chosen,
            "cost": {"actuation_usd": chosen["cost_actuation_usd"], "rest_of_cell_usd": rest,
                     "total_usd": chosen["cost_actuation_usd"] + sum(rest.values())},
        }
        log(f"  chosen: {chosen['label']} passes={chosen['passes']} "
            f"{ {c: round(v['worst_p3s'], 3) for c, v in chosen['summary'].items()} } ${chosen['cost_actuation_usd']}")
    # highlight rows for the error figure: cheapest, chosen, and a few named variants per candidate
    for kind, res in results.items():
        hl = []
        acc = res["accuracy"]
        want = {"scara": ["belt+motor-enc / printed bearings / al_60x30x2", "belt+AS5047P / printed bearings / al_60x30x2",
                          "belt+MT6835 / printed bearings / al_60x30x2", "belt+MT6835 / metal bearings / al_60x30x2",
                          "belt+MT6835 / metal bearings / petg_60x30x3"],
                "cartesian": [a["label"] for a in acc],
                "articulated5": ["motor-enc proximal / wrist XL430 / printed bearings / al_60x30x2",
                                 "MT6835 proximal / wrist XL430 / printed bearings / al_60x30x2",
                                 "MT6835 proximal / wrist XM430 / printed bearings / al_60x30x2",
                                 "MT6835 proximal / wrist belt+AS5047P / printed bearings / al_60x30x2",
                                 "MT6835 proximal / wrist strainwave_50 / metal bearings / al_60x30x2",
                                 "MT6835 proximal / wrist belt+AS5047P / metal bearings / petg_60x30x3"]}[kind]
        for a in acc:
            if a["label"] in want or a["label"] == res["accuracy_chosen"]["label"]:
                hl.append({"short": a["label"].replace(" bearings", "").replace("al_60x30x2", "Al").replace(
                    "petg_60x30x3", "PETG"), "assembly": a["summary"]["assembly"]["worst_p3s"],
                    "sheet": a["summary"]["sheet"]["worst_p3s"], "passes": a["passes"],
                    "cost": a["cost_actuation_usd"]})
        res["accuracy_highlights"] = hl
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    meta = {"generated_by": "python -m mechloop.arm.spike", "runtime_s": round(time.time() - t0),
            "limits_mm": A.LIMITS, "clearance_min_mm": R.CLEAR_MIN, "joint_margin_min": R.MARGIN_MIN,
            "encoders": ENCODERS, "transmissions": TRANSMISSIONS, "k_tilt": K_TILT, "rest_of_cell_usd": REST_OF_CELL,
            "note": "all inputs est. unless sourced in mechloop/arm/*.py; costs est."}
    OUT_JSON.write_text(json.dumps({"meta": meta, "results": results}, indent=1, default=float) + "\n")
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    figure_workspace(results, arms, FIG_DIR / "workspace_top.png")
    figure_errors(results, FIG_DIR / "error_budget.png")
    log(f"done in {time.time() - t0:.0f} s -> {OUT_JSON}, {FIG_DIR}")
    return results, arms


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    run(**vars(ap.parse_args()))
