# Two operating modes for design work (owner, 2026-11-21)

## 1. Iterative mode (default during review)

One change at a time, on top of a fixed base revision (now: printer_v12).

- Trigger: one owner decision from the review page (a comment thread), or one finding from a check.
- Scope: the parts that decision touches, rebuilt from a short spec (functions, mates, loads, process, envelope), not patched.
- Each change is a named flag in the next design file (e.g. `znut-direct`). With every flag off, the design is the base.
- Checks: base plus that one change, affected-tier verifiers, and the part-quality checks on the changed parts.
- Output: a change set (`changes/index.json`, `changes/<id>.json`, `changes/<id>.txt`) published to the review page. The owner sees it in the Changes tab as a switchable diff (Before | After | Overlay) and accepts or rejects it there.
- Turnaround target: minutes to an hour per change, a small agent per change, short context.
- Tool: `tools/build_change.py <design> <change-id>`.

## 2. Full revision mode (occasional)

Roll up the accepted changes into a new numbered revision (v12.1, v13, ...).

- Trigger: enough accepted changes, a structural change that touches many parts, or before ordering parts.
- Steps: all accepted flags on, flags removed from the code (the new revision is clean, not a stack of switches), full verify, part-quality checks on every custom part, full review package and build package regenerated, a new base for the next round of iterative changes.
- Rejected changes go back with the owner's note; they do not enter the revision.
- Output: designs/printer_vX.py, docs/PRINTER_VX.md, a new review page version.

## Why

Single long runs that redesign the whole machine produced patched, weird parts and gave the owner no way to see or approve each change. Small, visible, individually approved changes keep the owner in the loop and give the learning ledger one clear before/after per decision.
