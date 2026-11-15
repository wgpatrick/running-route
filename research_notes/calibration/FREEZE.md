# Freeze note: blind predictions

Frozen 2026-11-15T00:34Z (UTC), before any measured resonance or tuned acceleration of these three
machines was searched for, opened or recorded in this study.

| File | sha256 |
|---|---|
| `mech-ai/mechloop/twin/calibration_machines.json` (inputs) | `4561db2df882dafed988b5aa936d412a7cf222bd984e070ca477691f235dd7bf` |
| `blind_predictions.json` (output of `python -m mechloop.twin.calibration predict`) | `eb43636b2dc931bc7d9f4b95e5740f20fe640f28b70afab1d4f22fb2d833d6a3` |

Twin parameters used: belt EA 22 kN per 6 mm width (3,667 N per mm of width), 4 EA / L per belt, motor
magnetic spring from holding torque x run current, no frame compliance (there is no FEA of these machines).

## What had been seen before the freeze (so the reader can judge how blind this is)

- Inputs opened before the freeze: `research_notes/trade_study/measurements.json` and `SOURCES.md` (CAD
  masses, belt lengths, stock config limits), the three stock config files, the motor database. None of these
  contains a resonance measurement of the three machines. The stock `max_accel` values (2000, 3000, 3000)
  were seen; they are firmware defaults, not tuned results.
- `mech-ai/mechloop/twin/reference.py` was read. It contains the measured ranges for a Voron 2.4 **350**
  (X 54-62 Hz, Y 38-50 Hz) and the twin's belt stiffness default was tuned to those. The Trident 250 shares
  the gantry design at a smaller size, so the Trident prediction is "out of sample but same family", not
  fully independent. `research_notes/Voron reference data for twin validation.md` was NOT opened before the freeze.
- The model doing the work has general background knowledge of typical printer resonances from training
  (roughly: small CoreXY machines high, bed-slinger Y axes low). No specific number was looked up, and every
  prediction is a mechanical output of the frozen inputs through the twin's formula; no input was adjusted
  after seeing an output. One code change was made between the first and second prediction run (00:33Z to
  00:34Z): the step-loss search was capped at 400,000 mm/s^2 and the rigid-body force limit was added,
  because the first run returned 2,000,000 for one axis (ramp shorter than a time step). The resonance
  predictions were identical in both runs.

## Predictions (nominal, with 5-95 % band over the input ranges)

| Machine | Axis | Resonance Hz | Band | Shaper-rule max accel (MZV) | Step-loss accel at stock speed |
|---|---|---|---|---|---|
| Voron 0.2 | X | 112.6 | 101-117 | 47,000 | none below 400,000 |
| Voron 0.2 | Y | 85.2 | 77-89 | 26,300 | 84,900 |
| Trident 250 | X | 76.2 | 71-80 | 20,900 | 83,900 |
| Trident 250 | Y | 44.5 | 41-47 | 6,600 | 32,900 |
| Ender 3 | X | 85.8 | 78-89 | 26,800 | 76,100 |
| Ender 3 | Y | 45.6 | 39-46 | 7,000 | 18,900 |
