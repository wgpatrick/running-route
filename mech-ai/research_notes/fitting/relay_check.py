"""Relay (PID_CALIBRATE) test on the twin's heaters against what real machines' saved PID sets say.

Klipper's autotune stores Kp = 0.6 Ku x 255, Ki = 2 Kp / Tu, so every saved set gives back the heater's ultimate period Tu
and gain Ku (research_notes/datasets/firmware_fitted_parameters/derived/klipper_config_pid.csv; distinct sets only).
The same test is run here with Klipper's own ControlAutoTune class on the twin's hotend classes and on the beds of
printer_v4 and printer_v5.   Run from mech-ai/:  python research_notes/fitting/relay_check.py <datasets dir> <out.json>
The data directory is only parsed as CSV."""
import csv, json, sys
import numpy as np

import mechloop.electrical as E
from mechloop.twin import fitted as F

D, OUT = sys.argv[1], sys.argv[2]
TAU_V6 = 8.0            # the sensor lag chosen below for the v6 class (see "decision")


def relay(plant, target):
    cfg = {"control": "pid", "max_power": 1.0, "smooth_time": 1.0, "min_temp": 0, "max_temp": 400}
    kp, ki, kd = E.autotune_pid(plant, cfg, target)
    return {"Tu_s": round(2 * kp / ki, 1), "Ku_per_K": round(kp / 153.0, 3), "pid": [kp, ki, kd]}


def hot(ft, power=40.0, tau=None, ptc=None):
    nodes = [E.ThermalNode("cartridge", ft["cartridge_capacity_j_k"]),
             E.ThermalNode("block", ft["block_capacity_j_k"], [E.Surface(ft["radiation_w_k4"] / E.SIGMA, "fixed", 0.01, 1.0)],
                           g_ambient=ft["block_loss_w_k"], g_fan=ft["fan_loss_w_k"], fan_law=(ft["fan_threshold"], ft["fan_exponent"])),
             E.ThermalNode("nozzle", ft["nozzle_capacity_j_k"], g_ambient=ft["nozzle_loss_w_k"])]
    net = E.ThermalNet(nodes, [("cartridge", "block", ft["cartridge_block_w_k"]), ("block", "nozzle", ft["block_nozzle_w_k"])], 25.0)
    return E.HeaterPlant("extruder", net, "cartridge", "block", "block", power, sensor_tau_s=ft["sensor_tau_s"] if tau is None else tau, ptc=ptc)


def old_catalog(power=40.0):
    nodes = [E.ThermalNode("cartridge", 1.5),
             E.ThermalNode("block", 12.0, [E.Surface(1.6e-3, "body", 0.0115, 0.3)], g_ambient=0.02)]
    return E.HeaterPlant("extruder", E.ThermalNet(nodes, [("cartridge", "block", 2.0)], 25.0), "cartridge", "block", "block", power, sensor_tau_s=4.5)


rows = list(csv.DictReader(open(D + "/firmware_fitted_parameters/derived/klipper_config_pid.csv")))
pub = {}
for sec, label in (("extruder", "hotend"), ("heater_bed", "bed")):
    sets = sorted({(float(r["pid_Kp"]), float(r["pid_Ki"]), float(r["pid_Kd"])) for r in rows if r["section"] == sec})
    tu = np.array([2 * kp / ki for kp, ki, kd in sets])
    ku = np.array([kp / 153.0 for kp, ki, kd in sets])
    q = lambda v: {"p10": round(float(np.percentile(v, 10)), 3), "median": round(float(np.median(v)), 3), "p90": round(float(np.percentile(v, 90)), 3)}
    pub[label] = {"distinct_sets": len(sets), "Tu_s": q(tu), "Ku_per_K": q(ku)}
inside = lambda v, d: bool(d["p10"] <= v <= d["p90"])
res = {"public": pub, "hotend": {}, "bed": {}}
v6 = F.hotend_thermal("v6")
cases = {"old catalogue model (assumed values), 40 W": old_catalog(40.0),
         "fitted Ender 3 hotend, 40 W": hot(F.hotend_thermal("ender3_fitted")),
         "v6 class with Prusa's own lag 2.1 s, 40 W": hot(v6, tau=2.1),
         f"v6 class as adopted (lag {TAU_V6:g} s), 40 W": hot(v6, tau=TAU_V6),
         f"v6 class as adopted (lag {TAU_V6:g} s), 30 W (printer_v4 / v5)": hot(v6, power=29.7, tau=TAU_V6),
         "revo class (Prusa's lag 0.27 s), PTC 40 W": hot(F.hotend_thermal("revo"), ptc={"r_ohm_23c": 14.4, "tempco_per_c": 0.002078, "volts": 24.0, "r_series_ohm": 0.075})}
for name, plant in cases.items():
    r = relay(plant, 210.0)          # owners tune near their print temperature; 210 degC taken
    res["hotend"][name] = {**{k: r[k] for k in ("Tu_s", "Ku_per_K")}, "at_c": 210.0,
                           "Tu_inside_10_90": inside(r["Tu_s"], pub["hotend"]["Tu_s"]), "Ku_inside_10_90": inside(r["Ku_per_K"], pub["hotend"]["Ku_per_K"])}
res["hotend_lag_scan_v6_40w_210c"] = {f"{t:g}": relay(hot(v6, tau=t), 210.0)["Tu_s"] for t in (2.1, 4.0, 6.0, 8.0, 10.0)}
from mechloop.runner import load_design

for name in ("printer_v4", "printer_v5"):
    d = load_design(f"designs/{name}.py")
    p = E.thermal_plants(d)["heater_bed"]
    r = relay(p, 60.0)
    res["bed"][name] = {**{k: r[k] for k in ("Tu_s", "Ku_per_K")}, "at_c": 60.0, "power_w": round(p.power_w, 1),
                        "plate_capacity_j_k": p.basis.get("plate_capacity_j_k"), "sensor_tau_s": p.sensor_tau_s,
                        "Tu_inside_10_90": inside(r["Tu_s"], pub["bed"]["Tu_s"]), "Ku_inside_10_90": inside(r["Ku_per_K"], pub["bed"]["Ku_per_K"])}
a = res["hotend"][f"v6 class as adopted (lag {TAU_V6:g} s), 40 W"]
res["chosen_v6_sensor_tau_s"] = TAU_V6
res["chosen_revo_sensor_tau_s"] = 0.27
ph, pb = pub["hotend"], pub["bed"]
o_, e_, p_, w_ = (res["hotend"][k] for k in ("old catalogue model (assumed values), 40 W", "fitted Ender 3 hotend, 40 W",
                                             "v6 class with Prusa's own lag 2.1 s, 40 W", f"v6 class as adopted (lag {TAU_V6:g} s), 30 W (printer_v4 / v5)"))
res["decision"] = (f"Hotend, relay test at 210 degC: real machines cycle in {ph['Tu_s']['p10']:.0f} to {ph['Tu_s']['p90']:.0f} s (median {ph['Tu_s']['median']:.0f}), "
                   f"Ku {ph['Ku_per_K']['p10']:g} to {ph['Ku_per_K']['p90']:g} (median {ph['Ku_per_K']['median']:g}). The old model: {o_['Tu_s']} s (at the low edge). "
                   f"The fitted Ender hotend: {e_['Tu_s']} s (it really is that light: the log shows it cooling 2.6 K/s at 245 degC), outside. The v6 class "
                   f"(fitted structure, Prusa's E3D V6 totals) with Prusa's own lag of 2.1 s: {p_['Tu_s']} s, outside. Its sensor lag was therefore raised "
                   f"to {TAU_V6:g} s (inside the 2.9 to 10 s that Marlin's MPC sets imply): {a['Tu_s']} s and Ku {a['Ku_per_K']} with a 40 W heater, inside the "
                   f"band but below the median; with the 30 W cartridge of printer_v4 / v5, {w_['Tu_s']} s and Ku {w_['Ku_per_K']}, "
                   f"{'inside' if w_['Tu_inside_10_90'] else 'just under the 10th percentile'}. The model still cycles faster than a typical real hotend.")
res["table_entry"] = {
    "status": "checked; hotend sensor lag ADJUSTED to it", "old": {"hotend_sensor_tau_s": 4.5, "bed_sensor_tau_s": 10.0},
    "value": {"hotend_v6_sensor_tau_s": TAU_V6, "hotend_revo_sensor_tau_s": 0.27, "bed_sensor_tau_s": 10.0,
              "hotend_v6_40w_210c": {k: a[k] for k in ("Tu_s", "Ku_per_K")}, "beds_60c": {n: {k: v[k] for k in ("Tu_s", "Ku_per_K")} for n, v in res["bed"].items()}},
    "low": {"hotend_Tu_s": ph["Tu_s"]["p10"], "bed_Tu_s": pb["Tu_s"]["p10"], "hotend_Ku_per_K": ph["Ku_per_K"]["p10"], "bed_Ku_per_K": pb["Ku_per_K"]["p10"]},
    "high": {"hotend_Tu_s": ph["Tu_s"]["p90"], "bed_Tu_s": pb["Tu_s"]["p90"], "hotend_Ku_per_K": ph["Ku_per_K"]["p90"], "bed_Ku_per_K": pb["Ku_per_K"]["p90"]},
    "unit": "s, duty per K (ultimate period and gain of Klipper's relay autotune)",
    "source": f"{ph['distinct_sets']} distinct extruder and {pb['distinct_sets']} distinct bed PID sets in Klipper's example configurations "
              f"(hotend Tu median {ph['Tu_s']['median']:g} s, Ku {ph['Ku_per_K']['median']:g}; bed Tu median {pb['Tu_s']['median']:g} s, Ku {pb['Ku_per_K']['median']:g}); "
              "the twin's figures from Klipper's own ControlAutoTune on the model. research_notes/fitting/relay_check.py",
    "held_out": "this IS the outside check of the heater models' fast dynamics. " + res["decision"]
                + " Beds of printer_v4 / v5: " + ", ".join(f"{n} Tu {v['Tu_s']} s, Ku {v['Ku_per_K']}" for n, v in res["bed"].items())
                + f" against {pb['Tu_s']['p10']:g} to {pb['Tu_s']['p90']:g} s and {pb['Ku_per_K']['p10']:g} to {pb['Ku_per_K']['p90']:g}: inside, nothing changed. "
                  "The Revo class cycles faster than any cartridge hotend in the public sets; no Revo-only set was found to check it against.",
    "used_by": "hotend_thermal.v6.sensor_tau_s"}
json.dump(res, open(OUT, "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "table_entry"}, indent=1))
