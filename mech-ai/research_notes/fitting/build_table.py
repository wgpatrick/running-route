"""Write mechloop/twin/fitted_parameters.json from the fit results in this directory.

    python -I build_table.py <this dir> <out.json>
Every number that a fit produced is read from that fit's JSON; the rest (ranges taken from published constants,
values kept from before) is written here with its source."""
import json, sys

HERE, OUT = sys.argv[1], sys.argv[2]
J = lambda n: json.load(open(f"{HERE}/{n}"))
damp, hot, hot2, ext = J("damping_fit.json"), J("hotend_fit.json"), J("hotend_fit_holdout_1927.json"), J("extrusion_fit.json")
try:
    relay = J("relay_check.json")
except FileNotFoundError:
    relay = None
try:
    ph = J("posthoc_comparison.json")          # python -m mechloop.twin.calibration posthoc > posthoc_comparison.json
    loo = {r["machine"]: r["leave_one_out"] for r in ph["rows"] if r.get("leave_one_out")}
    tilt = {"held_out_text": "each rail machine predicted with the block stiffness the other one implies: "
                             + ", ".join(f"{k} {v['error_pct']:+.1f} % (k = {v['block_n_per_um']} N/um from {v['fitted_on']})" for k, v in loo.items())
                             + ". Two machines; the comparison that uses the fitted value on both is not blind"}
except FileNotFoundError:
    tilt = None
P = {}
r3 = lambda v: float(f"{v:.3g}")

# ------------------------------------------------------------------ motion
P["belt_ea_n_per_6mm"] = {
    "status": "not fitted (kept)", "old": 22000.0, "value": 22000.0, "low": 15000.0, "high": 27000.0, "unit": "N per unit strain, 6 mm GT2",
    "source": "no tensile data could be fetched; the blind three-machine comparison (reports/Twin calibration study.md) implies 15, 21 and 27 kN "
              "on its three gantry / bed axes",
    "held_out": "blind prediction, +15 / -8 / +1 % on the three axes it governs", "used_by": "PrinterMap.belt_ea_n; scorecard ranges"}
P["toolhead_tilt_effective_n_per_um"] = {
    "status": "fitted (post hoc, two machines)", "old": None, "value": 10.0, "low": 7.5, "high": 16.0, "unit": "N/um per guide block, spread over its ball track",
    "source": "the spring missing between belt clamp and nozzle on the toolhead axes of the Voron 0.2 (MGN7H, nozzle 55.9 mm off the rail) and "
              "Trident 250 (MGN12H, 63.1 mm), expressed as a block stiffness through K_rot = k L1^2 / 12 and k_nozzle = K_rot / r^2: 9.5 and 10.5 N/um. "
              "Range: the same from the quartiles of the owners' frequencies. It lumps the block's tilt with printed mounts and belt clamp of "
              "those machines; it is NOT a measurement of block stiffness (ratings.BLOCK_K stays at its assumed 40 N/um)",
    "held_out": (tilt or {}).get("held_out_text", "leave one machine out: see reports/Twin fitting.md"),
    "used_by": "machine.toolhead_compliance (series spring on the axis that carries the nozzle on its own guide blocks)",
    "reference_geometry": {"voron0": {"nozzle_below_rail_mm": 50.5, "nozzle_horizontal_mm": 23.9, "block": "MGN7H", "L1_mm": 21.8,
                                      "L1_source": "Hiwin MG catalogue, recalled, unverified"},
                           "trident250": {"nozzle_below_rail_mm": 51.0, "nozzle_horizontal_mm": 37.2, "block": "MGN12H", "L1_mm": 32.4,
                                          "L1_source": "mechloop/parts/vendor/hiwin_mgn12.json"},
                           "offsets_source": "research_notes/trade_study/measurements.json (makers' CAD)"}}
P["toolhead_v_wheels_n_per_mm"] = {
    "status": "fitted (post hoc, ONE machine)", "old": None, "value": 40.0, "low": 30.0, "high": 60.0, "unit": "N/mm at the nozzle",
    "source": "Ender 3 X axis (wheels on extrusion): 41 N/mm implied by the owners' median frequency", "held_out": "none possible: one machine, one number",
    "used_by": "calibration.compare_posthoc only (no catalogue part rides on wheels)"}
dx, dy = damp["per_axis"]["x"]["zeta_one_file"], damp["per_axis"]["y"]["zeta_one_file"]
hx, hy = damp["held_out"]["x"], damp["held_out"]["y"]
P["ringing_damping_ratio"] = {
    "status": "fitted", "old": "0.02 to 0.05 (what the two assumed dampers, 0.25 and 0.05, gave)",
    "value": {"toolhead_axis": round(dx["median"], 3), "gantry_or_bed_axis": round(dy["median"], 3)},
    "low": {"toolhead_axis": dx["p10"], "gantry_or_bed_axis": dy["p10"]}, "high": {"toolhead_axis": dx["p90"], "gantry_or_bed_axis": dy["p90"]},
    "unit": "damping ratio of the mode the load rings in",
    "source": f"mode fit of {damp['files_fitted']} Klipper resonance spectra, one file per machine and axis ({dx['n']} X, {dy['n']} Y, "
              f"{damp['repositories']} repositories); X files are the toolhead axis, Y files a gantry or a bed (research_notes/fitting/fit_damping.py). "
              "Range: 10th to 90th percentile over machines",
    "held_out": f"machines split in two by a hash of the repository name: X {hx['fit_half']['median']} (n={hx['fit_half']['n']}) against "
                f"{hx['held_out_half']['median']} (n={hx['held_out_half']['n']}), Y {hy['fit_half']['median']} (n={hy['fit_half']['n']}) against "
                f"{hy['held_out_half']['median']} (n={hy['held_out_half']['n']}): the halves differ by more than the X/Y difference, so the range, "
                "not the second digit, is the result. Independent check: 39 owner-entered values, 0.03 to 0.09, medians 0.05 to 0.07 "
                "(calibration study): inside the range. Estimator check on synthetic spectra: unbiased to 0.001",
    "used_by": "machine.machine_model sets each axis's belt/frame damper so that its ringing mode has this ratio"}
P["stepper_damping_ratio"] = {"status": "not fitted (kept)", "old": 0.25, "value": 0.25, "low": 0.125, "high": 0.375, "unit": "of the motor's magnetic spring",
                              "source": "assumed; no data separates it from the belt damper (only their combined effect on the ringing mode is fitted)",
                              "held_out": "no", "used_by": "PrinterMap.damping_ratio"}
P["used_accel_over_shaper_rule"] = {
    "status": "calibrated (three machines)", "old": None, "value": 0.5, "low": 0.4, "high": 0.65, "unit": "fraction of Klipper's MZV smoothing rule at the lower resonance",
    "source": "max_accel owners run with input shaping, over the rule at their own measured resonance: 0.44 (Ender 3), 0.51 (Voron 0), 0.62 (Trident 250)",
    "held_out": "no (three machines; the range is their spread)", "used_by": "scorecard: accel_owners_would_run_mm_s2"}

# ------------------------------------------------------------------ extrusion
pa = ext["pressure_advance"]
tab = lambda drive, q: {k.split()[1]: pa[k][q] for k in pa if k.startswith(drive + " ")}
ns = ext["nozzle_scaling"]
P["extruder_lag_s"] = {
    "status": "fitted", "old": 0.03, "unit": "s (first-order melt-flow lag = pressure-advance constant)",
    "value": {"direct": tab("direct", "median"), "bowden": tab("bowden", "median")},
    "low": {"direct": tab("direct", "min"), "bowden": tab("bowden", "min")}, "high": {"direct": tab("direct", "max"), "bowden": tab("bowden", "max")},
    "bowden_reference_length_mm": 430.0,
    "bowden_reference_note": "the Bowden values are the Prusa MINI's; its tube length (about 0.43 m) is recalled, not verified. A design's tube "
                             "length scales the part above the direct-drive value linearly: an assumption, not fitted",
    "source": f"PrusaSlicer factory profiles, every distinct M572 expression for rigid filaments: {pa['direct 0.4']['n']} direct-drive "
              f"(Nextruder, MK3.5), {pa['bowden 0.4']['n']} Bowden (MINI); median per nozzle size, range = smallest to largest factory value "
              "(the spread is between filaments). research_notes/fitting/fit_extrusion.py",
    "held_out": f"nozzle sizes left out of a power law fitted on 0.4 and 0.6 mm: direct 0.5 mm {ns['direct']['held_out']['0.5']['error_pct']:+.0f} %, "
                f"0.8 mm {ns['direct']['held_out']['0.8']['error_pct']:+.0f} %, Bowden 0.8 mm {ns['bowden']['held_out']['0.8']['error_pct']:+.0f} %; "
                f"below 0.4 mm the law fails ({ns['direct']['held_out']['0.25']['error_pct']:+.0f} % at 0.25 mm), so the table is used, not the law. "
                f"Leaving one filament's value out at 0.4 mm: median error {ns['direct']['leave_one_out_0.4_median_abs_error_pct']:.0f} % direct, "
                f"{ns['bowden']['leave_one_out_0.4_median_abs_error_pct']:.0f} % Bowden. One maker's machines; a K equals the lag only for a linear compliance",
    "used_by": "printer_map_for -> PrinterMap.extruder_lag_s (design.printer['extruder'], nozzle, Bowden tube length); tuning.pressure_advance"}
P["melt_rate_cap_mm3_s"] = {
    "status": "taken from published tables (not a fit)", "old": None, "unit": "mm^3/s, 0.4 mm brass nozzle, PLA",
    "value": {"v6": 11.0, "revo": 12.0}, "low": {"v6": 10.0, "revo": 11.0}, "high": {"v6": 15.0, "revo": 13.0}, "nozzle_exponent": 1.0,
    "source": "V6 class: E3D 600 mm^3/min = 10 (vendor file e3d_v6.json), Ellis' table 11, PrusaSlicer PLA profiles for the MK3 family and MINI "
              f"{ext['prusa_max_volumetric_speed_0.4']['v6_mk3_family | PLA']['median']:g} at most. Revo: E3D 13 (PLA 220 degC, e3d_revo.json), Ellis 11. "
              "Bambu's PLA profiles: median 12 on their own hotend. research_notes/fitting/extrusion_fit.json",
    "held_out": "no fit: three independent sources per class agree to within the range", "used_by": "run_print: the slicer is given the cap "
                "(max volumetric speed) and the report says which requested speeds it limits"}

# ------------------------------------------------------------------ hotend
x, d = hot["parameters"], hot["derived"]
free = J("hotend_fit_free.json")
ender = {"cartridge_capacity_j_k": x["C_h"], "block_capacity_j_k": x["C_b"], "nozzle_capacity_j_k": x["C_n"],
         "cartridge_block_w_k": x["G_hb"], "block_nozzle_w_k": x["G_bn"], "block_loss_w_k": x["g_b"], "nozzle_loss_w_k": x["g_n"],
         "fan_loss_w_k": x["g_fan"], "fan_exponent": x["fan_exp"], "fan_threshold": x["fan_f0"], "radiation_w_k4": x["c_rad"],
         "sensor_tau_s": x["tau_s"], "total_capacity_j_k": d["total_capacity_j_k"], "loss_still_w_k_at_245c": d["loss_still_air_w_k_at_245c"],
         "loss_full_fan_w_k_at_245c": d["loss_full_fan_w_k_at_245c"], "heater_w_assumed_in_fit": hot["assumed"]["heater_w"]}


def scaled(C, loss_still, loss_fan, tau):
    """The fitted structure (how the capacity splits over the three nodes, which share of the loss grows as T^4, the fan
    law's shape) carried to another hotend's published totals."""
    kc, kl = C / d["total_capacity_j_k"], loss_still / d["loss_still_air_w_k_at_245c"]
    return {"cartridge_capacity_j_k": r3(x["C_h"] * kc), "block_capacity_j_k": r3(x["C_b"] * kc), "nozzle_capacity_j_k": r3(x["C_n"] * kc),
            "cartridge_block_w_k": r3(x["G_hb"] * kc), "block_nozzle_w_k": r3(x["G_bn"] * kc), "block_loss_w_k": r3(x["g_b"] * kl),
            "nozzle_loss_w_k": r3(x["g_n"] * kl), "fan_loss_w_k": r3(loss_fan - loss_still), "fan_exponent": x["fan_exp"],
            "fan_threshold": x["fan_f0"], "radiation_w_k4": r3(x["c_rad"] * kl), "sensor_tau_s": tau, "total_capacity_j_k": C,
            "loss_still_w_k_at_245c": r3(loss_still), "loss_full_fan_w_k_at_245c": r3(loss_fan)}


tau_v6 = (relay or {}).get("chosen_v6_sensor_tau_s", 2.1)
tau_revo = (relay or {}).get("chosen_revo_sensor_tau_s", 0.27)
# E3D V6: totals from Prusa's own model of that hotend (thermal_model/e3d_v6.h: 12.1 J/K, 20.5 K/W fan off, 10.1 K/W full fan, lag 2.1 s)
v6 = scaled(12.1, 1 / 20.5, 1 / 10.1, tau_v6)
# Revo: thermal_model/e3d_REVO.h: 8.77 J/K, 25.3 K/W fan off, 15.4 K/W full fan, lag 0.27 s
revo = scaled(8.77, 1 / 25.3, 1 / 15.4, tau_revo)
ho, ho2 = hot["held_out_runs"][0], hot2["held_out_runs"][0]
P["hotend_thermal"] = {
    "status": "structure fitted (one Ender 3); totals of the v6 and revo classes taken from Prusa's models, NOT fitted; sensor lag set by the relay check",
    "old": "block 12 J/K + cartridge 1.5 J/K behind 2 W/K, free convection on 1.6e-3 m^2 with emissivity 0.3, 0.02 W/K up the heat break, "
           "sensor lag 4.5 s (all assumed); Revo: 6.9 J/K estimated from part masses, lag 2 s assumed",
    "unit": "J/K, W/K, W/K^4, s", "value": {"ender3_fitted": ender, "v6": v6, "revo": revo},
    "low": {"v6": {"total_capacity_j_k": 6.5, "loss_still_w_k": 0.049, "loss_full_fan_w_k": 0.063, "sensor_tau_s": 2.1},
            "revo": {"total_capacity_j_k": 6.9, "loss_still_w_k": 0.033, "sensor_tau_s": 0.27}},
    "high": {"v6": {"total_capacity_j_k": 16.8, "loss_still_w_k": 0.14, "loss_full_fan_w_k": 0.174, "sensor_tau_s": 10.0},
             "revo": {"total_capacity_j_k": 9.1, "loss_still_w_k": 0.085, "sensor_tau_s": 2.0}},
    "source": "ender3_fitted: three-node model fitted to eight logged runs of one Ender 3 with a V6-style hotend and 40 W cartridge "
              f"(batu63562/ender3-hotend-twin, GPL-3.0): {d['total_capacity_j_k']} J/K, {d['loss_still_air_w_k_at_245c']} W/K still air and "
              f"{d['loss_full_fan_w_k_at_245c']} W/K full fan at 245 degC, calibration RMSE {hot['calibration_rmse_c']} degC against "
              f"{hot['one_node_same_runs']['rmse_c']} for one mass. The logs do not pin down the fast path from heater to sensor (bounds wide open, the "
              f"cartridge shrinks to {free['parameters']['C_h']} J/K with no worse an RMSE, {free['calibration_rmse_c']}), so cartridge and contact are held "
              "to what the parts are and end on those bounds. That hotend is light and lossy (it cools 2.6 K/s at 245 degC): its capacity is at the "
              "bottom of Marlin's MPC range (6.5 to 16.8 J/K) and about half Prusa's E3D V6. v6 (the default for a cartridge in a block): the fitted "
              "STRUCTURE scaled to Prusa's E3D V6 totals (12.1 J/K, 20.5 to 10.1 K/W). revo: the same structure scaled to Prusa's Revo totals "
              "(8.77 J/K, 25.3 to 15.4 K/W); heater power from E3D's PTC figures. Ranges: Marlin's eight MPC sets and Prusa's models. "
              "research_notes/fitting/fit_hotend.py",
    "held_out": f"ender3_fitted: the print run was held out: open loop over {ho['duration_s']} s the model is {ho['bias_c']:+.1f} degC off on average "
                f"(RMSE {ho['rmse_c']}), i.e. it needs {hot['held_out_hold_duty'][0]['error_pct']:+.1f} % more power than was logged; without the (unfitted, "
                f"physical) heat taken by the filament the error is {hot['held_out_without_filament_term'][0]['bias_c']:+.0f} degC. Second fit with the heat / "
                f"fan / 150 degC hold / cool run held out as well: RMSE {ho2['rmse_c']} degC on it (calibration {hot2['calibration_rmse_c']}). "
                "v6 and revo: no log of either hotend; checked only by the relay test (heater_relay_test)",
    "used_by": "mechloop.electrical.build_plants (heaters of model 'block'): heat-up, PID autotune, fault simulation, melt-capacity margin"}
if relay is not None:
    P["heater_relay_test"] = relay["table_entry"]
    for k, v in relay.get("more_entries", {}).items():
        P[k] = v

# ------------------------------------------------------------------ not fitted
for key, val, unit, why in (
        ("friction_n", {"x": 2.0, "y": 3.0, "z": 5.0}, "N per axis", "no measured data for miniature guides under printer loads"),
        ("step_loss_boundary", None, "mm/s^2", "comes out of the motor torque curve and the stepper model; no controlled measurement of the acceleration "
                                               "at which a printer first loses steps was found. On three reference machines it sat 6 to 8 times above what owners run"),
        ("guide_block_radial_n_per_um", 40.0, "N/um", "ratings.BLOCK_K: catalogue editions disagree (44 / 67 N/um for MGN12C) and none was read"),
        ("frame_and_joint_stiffness", None, "N/mm", "from the design's own FEA (bonded / screw-only bracket); no modal test of a printer frame"),
        ("bed_thermal", None, "", "plate capacity from the CAD and the bond conductance are assumed; only the relay-test period is checked against "
                                  "public configurations (heater_relay_test)"),
        ("warp_cooling_adhesion", None, "", "not in the twin")):
    P[key] = {"status": "NOT FITTED", "old": val, "value": val, "low": None, "high": None, "unit": unit, "source": why, "held_out": "no", "used_by": ""}
json.dump({"_note": "Written by research_notes/fitting/build_table.py from the fits in that directory. Loaded by mechloop.twin.fitted. "
                    "status: fitted | calibrated | taken from published tables | not fitted (kept) | NOT FITTED. See reports/Twin fitting.md.",
           "date": "2026-11-15", "parameters": P}, open(OUT, "w"), indent=1)
print("wrote", OUT, len(P), "parameters")
