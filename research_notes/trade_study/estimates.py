"""Closed-form, like-for-like engineering estimates for the trade study.

Usage: python -I estimates.py <measurements.json> <out.json>
Every function states its assumption. These are order-of-magnitude comparisons between
architectures, not predictions for any one machine.
"""
import json, math, sys

E_AL = 69e9          # Pa, 6061 / cast plate
NU = 0.33
G = 9.81
# 2020 T-slot section (mech-ai/mechloop/parts/vendor/misumi_hfs5_2020.json): I = 7419 mm4, 0.491 kg/m
I_2020, M_2020 = 7419e-12, 0.491
# other sections: thin-wall scaling from 2020 where no data was fetched (ASSUMPTION): I ~ b^4, mass ~ b^2
I_1515, M_1515 = I_2020 * (15 / 20) ** 4, M_2020 * (15 / 20) ** 2
I_3030, M_3030 = I_2020 * (30 / 20) ** 4, M_2020 * (30 / 20) ** 2
# belt: the twin's own assumption (mech-ai/mechloop/twin/__init__.py: belt_ea_n = 15 kN for 6 mm GT2, linear in width)
EA_PER_MM_WIDTH = 15000.0 / 6.0
# miniature guide block: radial stiffness per block. No vendor rigidity table could be fetched, so this is an
# ASSUMED class value; results that use it are shown with a x0.5 .. x2 band.
K_BLOCK = {"MGN7H": 15e6, "MGN9C": 15e6, "MGN9H": 25e6, "MGN12C": 25e6, "MGN12H": 40e6, "MGN15H": 60e6}   # N/m
L_BLOCK = {"MGN7H": 0.0214, "MGN9C": 0.0194, "MGN9H": 0.0298, "MGN12C": 0.0217, "MGN12H": 0.0324, "MGN15H": 0.0437}  # loaded length, m
CLEARANCE = 5e-6     # m, radial play of a light-clearance (Z0/ZF) miniature block: ASSUMPTION for the "rock" figure


def plate_D(t):
    return E_AL * t ** 3 / (12 * (1 - NU ** 2))


def cantilever_bed(block, blocks_per_rail, block_pitch, n_rails, arm_load, arm_edge, arm_I=None, n_arms=2,
                   load_n=G * 1.0):
    """Bed hanging off vertical rails behind it. Load at arm_load (m) in front of the rail plane, deflection
    read at arm_edge. Rotation = M / k_theta where k_theta comes from the blocks: one block resists pitch only
    by its own loaded length (k L^2 / 12); two blocks a pitch p apart give k p^2 / 2 per rail. Arm bending is
    added as a cantilever beam (F a^2 (3L - a) / 6EI) when a section is given."""
    k, lb = K_BLOCK[block], L_BLOCK[block]
    if blocks_per_rail == 1:
        kth = n_rails * k * lb ** 2 / 12
        rock = CLEARANCE / lb * arm_edge
    else:
        kth = n_rails * (k * block_pitch ** 2 / 2 + 2 * k * lb ** 2 / 12)
        rock = CLEARANCE / block_pitch * arm_edge
    m = load_n * arm_load
    tilt = m / kth
    d_blocks = tilt * arm_edge
    d_arm = 0.0
    if arm_I:
        d_arm = load_n * arm_load ** 2 * (3 * arm_edge - arm_load) / (6 * E_AL * arm_I * n_arms)
    return dict(pitch_stiffness_nm_per_rad=round(kth), edge_sag_blocks_mm=round(d_blocks * 1e3, 4),
                edge_sag_arms_mm=round(d_arm * 1e3, 4), edge_sag_total_mm=round((d_blocks + d_arm) * 1e3, 4),
                band_mm=[round((d_blocks / 2 + d_arm) * 1e3, 4), round((d_blocks * 2 + d_arm) * 1e3, 4)],
                edge_rock_from_clearance_mm=round(rock * 1e3, 4))


def three_point_bed(t, radius, load_n=G * 1.0):
    """Plate on three supports near its edge, load at the centre: bounded by a simply supported circular plate of
    the same radius, w = F a^2 (3 + nu) / (16 pi D (1 + nu)). Screw and nut axial compliance is neglected."""
    w = load_n * radius ** 2 * (3 + NU) / (16 * math.pi * plate_D(t) * (1 + NU))
    return dict(centre_sag_mm=round(w * 1e3, 4))


def beam_freq(I, m_per_m, span, m_tool, extra_per_m=0.0):
    """First bending mode of a simply supported beam with a point mass at mid-span:
    k = 48 E I / L^3, effective mass = m_tool + 0.49 * beam mass. Rail stiffness is ignored (conservative),
    rail mass is included through extra_per_m."""
    k = 48 * E_AL * I / span ** 3
    m = m_tool + 0.49 * (m_per_m + extra_per_m) * span
    return dict(k_n_per_mm=round(k / 1e3, 1), f_hz=round(math.sqrt(k / m) / (2 * math.pi), 1))


def belt_k(width_mm, length_mm, kind="loop"):
    """Stiffness seen by the carriage at mid-travel. Open loop clamped to the carriage, motor at one end:
    two runs of L/2 in parallel -> k = 4 EA / L (the twin's formula). CoreXY: each belt has one short run and
    one long run from the motors to the carriage; for a move along X both belts act in parallel, and the
    carriage sees roughly 2 x (EA / (L/2)) = 4 EA / L with L the length of ONE belt."""
    ea = EA_PER_MM_WIDTH * width_mm
    return round(4 * ea / length_mm, 1)


def axis_freq(k_n_per_mm, mass_kg):
    return round(math.sqrt(k_n_per_mm * 1e3 / mass_kg) / (2 * math.pi), 1)


if __name__ == "__main__":
    RAW = json.load(open(sys.argv[1]))
    M = {}
    for key, fields in RAW.items():          # flatten {field: {value, method, source}} and derive the inputs used below
        f = {k: (x["value"] if isinstance(x, dict) and "value" in x else x) for k, x in fields.items()}
        if isinstance(f.get("belts"), list) and f["belts"] and isinstance(f["belts"][0], dict):
            b = f["belts"][0]
            f["belt_length_mm"] = b.get("length_best_mm")
        if isinstance(f.get("toolhead_mass_kg"), dict):
            f["toolhead_mass_kg"] = f["toolhead_mass_kg"]["value"]
            f["x_moving_mass_kg"] = f["toolhead_mass_kg"]
        if key == "k3" and isinstance(f.get("y_moving_mass_kg"), dict):
            f["x_moving_mass_kg"] = f["y_moving_mass_kg"]["value"]      # cross gantry: toolhead plus one cross rail
        M[key] = f
    out = {}
    ours = M["ours"]
    A_EDGE, A_LOAD = ours["bed_front_edge_to_z_rail_plane_mm"] / 1e3, ours["bed_centre_to_z_rail_plane_mm"] / 1e3
    # ---- 1. bed support -------------------------------------------------------------------------
    bed = {}
    bed["ours: 1 MGN12H per rail, 2 rails (as designed)"] = cantilever_bed("MGN12H", 1, 0, 2, A_LOAD, A_EDGE)
    bed["ours + carrier bending from our FEA (0.0325 mm at 3 kg -> 0.011 mm at 1 kg)"] = dict(
        edge_sag_total_mm=round(bed["ours: 1 MGN12H per rail, 2 rails (as designed)"]["edge_sag_total_mm"] + 0.0325 / 3, 4))
    bed["ours with 2 MGN12H per rail, 50 mm pitch (fits a 250 mm rail)"] = cantilever_bed("MGN12H", 2, 0.050, 2, A_LOAD, A_EDGE)
    bed["ours with 2 MGN12H per rail, 60 mm pitch"] = cantilever_bed("MGN12H", 2, 0.060, 2, A_LOAD, A_EDGE)
    bed["ours with 2 MGN12H per rail, 100 mm pitch"] = cantilever_bed("MGN12H", 2, 0.100, 2, A_LOAD, A_EDGE)
    v0 = M["voron0"]
    bed["Voron 0.2: 1 MGN7H per rail, 2 rails, 1515 arms (scaled to its own 120 mm bed)"] = cantilever_bed(
        "MGN7H", 1, 0, 2, v0["bed_centre_to_z_rail_plane_mm"] / 1e3, v0["bed_front_edge_to_z_rail_plane_mm"] / 1e3,
        arm_I=I_1515)
    bed["ours with the carrier replaced by two 2020 arms (Trident / V0 style), arms only"] = dict(
        edge_sag_arms_mm=round(G * A_LOAD ** 2 * (3 * A_EDGE - A_LOAD) / (6 * E_AL * I_2020 * 2) * 1e3, 4))
    bed["3-point bed, 220 x 220 x 6 mm plate (our plate on three screws)"] = three_point_bed(0.006, 0.110)
    bed["3-point bed, 5 mm cast plate 229 x 229 (V-Core 3.1 200 plate)"] = three_point_bed(0.005, 0.115)
    bed["note"] = ("1 kg at the bed centre. Cantilever numbers scale linearly with the ASSUMED block stiffness "
                   "(band = x0.5 .. x2). A print's weight builds up slowly and is mostly taken out by the first "
                   "layer being laid on the already-loaded bed, so the static number matters less than the "
                   "pitch stiffness, which sets how much the bed nods when the Z axis hops or the nozzle drags.")
    # pitch-mode frequency of our Z stage: I about the rail plane = m (d^2 + L^2/12)
    m_z, d = ours["moving_mass_kg"]["z"], A_LOAD
    Iz = m_z * (d ** 2 + 0.22 ** 2 / 12)
    for label, key in (("as designed", "ours: 1 MGN12H per rail, 2 rails (as designed)"),
                       ("2 blocks per rail, 50 mm pitch", "ours with 2 MGN12H per rail, 50 mm pitch (fits a 250 mm rail)"),
                       ("2 blocks per rail, 100 mm pitch", "ours with 2 MGN12H per rail, 100 mm pitch")):
        kth = bed[key]["pitch_stiffness_nm_per_rad"]
        bed[f"ours bed nodding frequency, {label}"] = dict(f_hz=round(math.sqrt(kth / Iz) / (2 * math.pi), 1))
    out["bed_support"] = bed
    # ---- 2. gantry beam -----------------------------------------------------------------------------
    beam = {}
    beam["ours: 2020 + MGN12 rail, span 320 mm, 0.60 kg toolhead"] = beam_freq(I_2020, M_2020, 0.320, 0.60, 0.65)
    for key, label, I, mpm, rail in (("voron24", "Voron 2.4 250: 2020 + MGN12", I_2020, M_2020, 0.65),
                                     ("trident", "Voron Trident: 2020 + MGN12", I_2020, M_2020, 0.65)):
        if key in M and M[key].get("x_beam_span_mm"):
            beam[f"{label}, span {M[key]['x_beam_span_mm']:.0f} mm, {M[key].get('toolhead_mass_kg', 0.45)} kg toolhead"] = beam_freq(
                I, mpm, M[key]["x_beam_span_mm"] / 1e3, M[key].get("toolhead_mass_kg", 0.45), rail)
    beam["note"] = "beam bending is not what limits any of these machines; compare with the belt numbers below"
    out["gantry_beam"] = beam
    # ---- 3. belts -----------------------------------------------------------------------------------
    belt = {}
    for w in (6, 9, 12):
        for L in (500, 700, 1000, 1500, 2000):
            belt[f"{w} mm x {L} mm"] = belt_k(w, L)
    out["belt_stiffness_n_per_mm"] = belt
    cmp_ = {}
    mm = ours["moving_mass_kg"]
    cmp_["ours X: 12 mm x 674 mm, 0.60 kg"] = dict(k=belt_k(12, 674), f_hz=axis_freq(belt_k(12, 674), mm["x"]),
                                                   twin_hz=ours["resonance_hz"]["x"])
    ky = belt_k(12, 676) + belt_k(12, 737.5)
    cmp_["ours Y: 2 x 12 mm (676 + 738 mm), 1.49 kg"] = dict(k=round(ky, 1), f_hz=axis_freq(ky, mm["y"]),
                                                             twin_hz=ours["resonance_hz"]["y"])
    cmp_["ours X with 9 mm belt"] = dict(k=belt_k(9, 674), f_hz=axis_freq(belt_k(9, 674), mm["x"]))
    cmp_["ours X with 6 mm belt"] = dict(k=belt_k(6, 674), f_hz=axis_freq(belt_k(6, 674), mm["x"]))
    for key, label in (("voron0", "Voron 0.2"), ("voron24", "Voron 2.4 250"), ("trident", "Voron Trident"),
                       ("k3", "Annex K3"), ("ender3", "Ender 3 X")):
        m = M.get(key, {})
        if m.get("belt_length_mm") and m.get("belt_width_mm"):
            k = belt_k(m["belt_width_mm"], m["belt_length_mm"]) * m.get("belts_in_parallel", 1)
            cmp_[f"{label}: {m['belt_width_mm']} mm x {m['belt_length_mm']:.0f} mm"] = dict(
                k=round(k, 1), x_mass_kg=m.get("x_moving_mass_kg"),
                f_hz=axis_freq(k, m["x_moving_mass_kg"]) if m.get("x_moving_mass_kg") else None)
    out["belt_comparison"] = cmp_
    # ---- 4. moving motor ----------------------------------------------------------------------------
    xm = 0.23 + 0.016           # NEMA17-34 + pulley riding on our Y beam (BOM masses)
    f0 = ours["resonance_hz"]["y"]
    out["moving_motor"] = dict(
        x_motor_and_pulley_on_y_kg=xm, y_mass_now_kg=mm["y"], y_mass_without_kg=round(mm["y"] - xm, 3),
        y_resonance_now_hz=f0, y_resonance_without_hz=round(f0 * math.sqrt(mm["y"] / (mm["y"] - xm)), 1),
        accel_gain_same_force="%.0f %%" % (100 * (mm["y"] / (mm["y"] - xm) - 1)),
        note="frequency scales with 1/sqrt(mass); acceleration at the same belt force with 1/mass. A CoreXY "
             "conversion also changes belt length (longer, so softer), which can cancel this gain: see belt table.")
    json.dump(out, open(sys.argv[2], "w"), indent=1)
    print(json.dumps(out, indent=1))
