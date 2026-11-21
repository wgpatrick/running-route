# Fast lane for iterative changes (owner: "edits should be snappier", 2026-11-21)

Goal: an owner decision becomes a visible change in the review page in minutes, not hours.

1. Make the change (flag in designs/printer_v12_1.py). Keep it small: one decision, the parts it touches.
2. FAST CHECKS ONLY before shipping:
   tools/heavy.sh .venv/bin/python -m mechloop verify designs/printer_v12_1.py --only geometry interference manufacture assemblability practice part_quality --no-render --out <tmp>
   (with only this change's flag on). Compare against v12 for those verifiers.
3. Ship immediately if the fast checks add no new errors: export with tools/build_change.py (no --verify), status "proposed",
   checks line starting "fast checks: ..." and ending "full checks running".
4. Then run the slow checks (tolerance Monte Carlo, fea, motion, printing, electrical, subsystems, ratings) for that change in
   the background through tools/heavy.sh, and when done update that change's checks line (and status to "needs work" if it
   adds errors). Start the NEXT change while the slow checks run.
5. Never wait on a slow check to start the next change. Never batch changes.
