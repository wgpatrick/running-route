"""Sensitivity of the hotend overshoot finding (not a tuning of the model: nothing here goes into the design file).
Variants: Klipper's own stock PID for the V-Minion kit hotend (config/printer-ratrig-v-minion-2021.cfg), and a 40 W cartridge."""
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("ref", "designs/ref_vminion.py"); ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
from mechloop.runner import verify
for label, pid in (("simulated autotune (as in the run)", None), ("Klipper stock config PID 22.2 / 1.08 / 114", (22.2, 1.08, 114.0))):
    d = ref.build()
    if pid:
        d.electrical.firmware["heaters"]["extruder"]["pid"] = pid
    rep = verify(d, only=["electrical"])
    m = [r for r in rep.results if r.verifier == "electrical"][0].metrics["heaters"]["extruder"]
    print(label, "-> pid", [round(x, 2) for x in m["pid"]], "overshoot", list(m["closed_loop"].values())[0]["overshoot_c"], "K, settle", list(m["closed_loop"].values())[0]["settling_time_s"], "s",
          [f.code for r in rep.results for f in r.findings if f.severity == "error"])
