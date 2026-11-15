"""Scratch only: Rat Rig's published printed parts (STEP, CC BY-NC-SA 4.0, read from the scratch clone, not copied
anywhere) put through the manufacture verifier as printed PETG parts. Rat Rig's print settings say: supports none."""
import glob, os
from build123d import import_step, Pos
from mechloop import Design

SRC = "/tmp/claude-0/-home-user-running-route/87481e0a-8f62-5246-a6fc-1c1f80e15b45/scratchpad/refmachine/src/vminion/cad/printed_parts/machine/step"


def build():
    d = Design("real_printed_parts")
    d.manufacturing = {"shop": "generic", "printer": {"build_volume": (220.0, 220.0, 220.0), "nozzle": 0.4}}
    for i, f in enumerate(sorted(glob.glob(os.path.join(SRC, "*.step")))):
        s = import_step(f)
        sol = s.solids()
        if len(sol) != 1:
            continue
        name = os.path.basename(f)[:-5].replace(" ", "_")
        d.add(name, Pos(i * 150.0, 0, 0) * sol[0], material="petg", process="printed")
    return d
