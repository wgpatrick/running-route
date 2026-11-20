"""Ours: folded parts from mechloop's own code (same frame as the SolidCraft scripts) and the hand-calculated flat
(bend allowance BA = (r + K t) * angle, K and r from our SendCutSend rules / the model), written as STEP + JSON."""
import json, math, sys
sys.path.insert(0, "/home/user/running-route/mech-ai"); sys.path.insert(0, "/home/user/running-route/mech-ai/designs")
from build123d import Location, Plane, export_step, Matrix, Pos
sys.path.insert(0, "/home/user/running-route/mech-ai/tools")
import make_reference_parts as MRP
import printer_v11 as P
from mechloop.shops import supplier_rules as SR
import pathlib
OUT = str(pathlib.Path(__file__).resolve().parent / "ours")
t = P.B23
K = SR._k_factor("sendcutsend", "al5052", t); r_scs = SR._shop_radius("sendcutsend", "al5052", t)
print("K", K, "SCS r", r_scs, "BD90", SR.bend_deduction("sendcutsend", "al5052", t, 90))
BA = lambda r: (r + K * t) * math.pi / 2
info = {"K": K, "t": t, "r_scs": r_scs}

# RP03
rp03, i3 = MRP.rp03_sheet_channel()
export_step(rp03, f"{OUT}/RP03.step")
r = t; c = r + t
a, base, b = 25 - c, 60 - 2 * c, 6 - c
L = a + base + b + 2 * BA(r)
info["RP03"] = {"r": r, "flat": [L, 40.0], "bends_from_tall_edge": [a + BA(r) / 2, a + BA(r) + base + BA(r) / 2],
                "holes_from_tall_edge": sorted([25 - (t + r + 1.5 + 2.75), a + BA(r) + (-12 - (-30 + c)), a + BA(r) + (12 - (-30 + c))]),
                "holes_y": [0, 0, 0], "BA": BA(r)}

# x_belt_bracket (bent_L local frame)
r = P.R_B23; c = r + t
z_leg = P.Z_XL + 0.7
xbb = P.round_profile(P.bent_L(t, r, 13.0, P.R_TPF + 8.0, 30.0,
                 holes_a=[(-x, (z_leg + t) - (P.Z_BEAM + P.BRK_Z), P.clearance_hole("M3")) for x, _ in P.BLK_SCREWS],
                 holes_b=[(P.R_TPF - yy, -xx, P.clearance_hole("M3")) for xx in (-10.0, 10.0) for yy in P.CLAMP_Y]), 0.8, t)
export_step(xbb, f"{OUT}/XBB.step")
a, b = 13.0 - c, P.R_TPF + 8.0 - c
za = (z_leg + t) - (P.Z_BEAM + P.BRK_Z)
info["XBB"] = {"r": r, "flat": [a + b + BA(r), 30.0], "bends_from_legA_edge": [a + BA(r) / 2],
               "holes_from_legA_edge": sorted([13.0 - za] * 2 + [a + BA(r) + (x - c) for x in (P.R_TPF - yy for yy in P.CLAMP_Y) for _ in (0, 1)]),
               "za": za, "BA": BA(r)}

# probe_mount: world shape -> bent_L local -> SolidCraft frame (X,Y,Z)_sc = (y, z, x)_local
z_b = P.Z_PRB + P.PRB_CLAMP[0]; xl0, xl1 = P.NOZ_X - 13.0, P.NOZ_X + 12.5; x_c = (xl0 + xl1) / 2
l_b = 21.69
y_face = (P.YB0 + P.PRB_Y + 10.5) - l_b
world = P.round_profile(P.probe_bracket_shape(y_face), 0.8, t)
to_local = Location(Plane(origin=(x_c, y_face, z_b), x_dir=(0, 1, 0), z_dir=(0, 0, 1))).inverse()
loc = to_local * world
# local (x,y,z) -> sc (y,z,x): plane whose x_dir/ y_dir/ z_dir expressed: sc X = local y, sc Y = local z, sc Z = local x
perm = Location(Plane(origin=(0, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))   # maps local x->sc Z? verified numerically below
prb = perm * loc
bb = prb.bounding_box()
print("probe bbox after perm", bb.min, bb.max)
export_step(prb, f"{OUT}/PRB.step")
h_a = P.Z_BEAM + 36.0 - z_b
r = P.R_B23; c = r + t
info["PRB"] = {"r": r, "h_a": h_a, "l_b": l_b, "flat": [33.0, (h_a - c) + (l_b - c) + BA(r)], "BA": BA(r),
               "bend_from_legA_top": (h_a - c) + BA(r) / 2, "legB_hole_from_legB_end": 10.5,
               "roto_holes_local_yz": [(-(x - x_c), z - z_b) for x, z in P.ROTO_HOLES()]}
json.dump(info, open(f"{OUT}/hand.json", "w"), indent=1)
print(json.dumps(info, indent=1))
