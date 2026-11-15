"""What the tolerance verifier says about the nozzle gap of a machine whose NOZZLE (not bed) rides the Z joint, when no
z_offset adjustment is declared. Scratch only."""
import importlib.util
spec = importlib.util.spec_from_file_location("ref", "designs/ref_vminion.py"); ref = importlib.util.module_from_spec(spec); spec.loader.exec_module(ref)
from mechloop.runner import verify
d = ref.build()
d.adjustments = [a for a in d.adjustments if a.kind != "z_offset"]
rep = verify(d, only=["tolerance"])
for r in rep.results:
    for f in r.findings:
        if f.code in ("nozzle_gap_not_adjustable",):
            print(f.severity, f.code, f.message)
    if r.verifier == "tolerance":
        print({k: v for k, v in r.metrics["printer"].items() if "gap" in k or "reach" in k})
