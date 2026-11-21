# CAD quality plan: from "passes the verifiers" to "good parts"

The owner's review of printer_v12 found that many CUSTOM (fabricated) parts have problems of three kinds:

- **(a) broken** solid models,
- **(b) weird**: partly correct parts carrying artefacts of patching (slivers, hair-thin steps and webs, left-over features),
- **(c) fair / poor design ideas**: a part that works on paper but is not how a good designer would make it.

The existing verifiers (B-rep validity, DFM rules, interference, FEA, assembly) all passed on most of these parts. This
document records why, and the agreed plan.

## Root causes

1. **One monolithic, copy-forward script.** designs/printer_v12.py is ~3,150 lines carried forward and patched from v2 to
   v12. Custom parts are built inline from Box / Cylinder booleans at absolute world coordinates. Every change is a local
   patch (`+ 0.01` past a wall, a 0.6 mm bridge block, a cut moved by hand), and the patches pile up.
2. **The checks catch "wrong in known ways", not "good".** Validity, DFM limits, clearance and stress tell us a part is
   not broken in the ways we thought of. Nothing asks whether a part is clean, or whether each feature has a purpose.
3. **The loop chases verifier errors with minimal local patches.** A finding is fixed by the smallest edit that silences
   it, which is how the artefacts in (b) are made.
4. **Parts carry no recorded intent.** No part says what it is for, what it mates with, what it carries or how it is
   made, so neither an agent nor a check can tell a purposeful feature from a left-over one.
5. **No one looks at each part.** There is no independent reviewer, human or model, looking at each part on its own
   against what it should be.
6. **One very long agent run designs the whole machine**, so each part gets a sliver of attention and its context is
   lost between versions.

## Fixes

1. **Spec before shape.** Each custom part gets a short spec before it is drawn: functions; interfaces and mates;
   loads; process and material; envelope and keep-outs. Mounting holes are derived from the mating part's real hole
   positions (its interface data), never typed in.
2. **One module per part, in local coordinates, from a feature vocabulary.** Plate, boss, rib, pocket, slot,
   counterbore (and so on) as named features with their own parameters; a sheet-metal builder that works from a flat
   pattern plus bends; print conventions (orientation, teardrops, insert/nut pockets) applied by the builder. The part
   is placed into the assembly by one transform.
3. **Checks for broken / weird / poor.**
   - broken and weird: automated geometric checks on every custom part (`mechloop/verifiers/part_quality.py`, below);
   - poor: an independent vision reviewer looking at renders of each part against its spec, a rubric and reference
     designs of the same role (Voron and Prusa parts, for instance).
4. **Small per-part agents.** A part is designed, checked and reviewed by an agent that has only that part's spec,
   its mates and the rules. Parts that were patched across versions are rebuilt from their spec, not patched again.
5. **The owner's tagged feedback becomes checks and guidelines.** The review page now stores `kind` =
   broken | weird | poor | other and `severity` = minor | major | blocker on each feedback doc. Each recurring tag
   becomes a check or a written guideline, and we track **owner-flagged issues per part per version** as the measure
   that matters.

## Definition of good

| level | meaning | checked by |
|---|---|---|
| **correct** | valid single solid, makeable, fits, strong enough | geometry, manufacture (DFM), interference, FEA, assemblability |
| **clean** | no artefacts: no slivers, tiny edges, hair-thin steps, webs or slits, no unused features, no hidden clashes | part_quality (new) |
| **well designed** | each feature has a purpose from the spec; the part is how a good designer would make it for its role | spec + vision reviewer + owner review |

## Status (2026-11-21)

Done in this step (the automated side of fix 3 for classes (a) and (b), run on v12 in parallel with the owner's manual
review):

- `mechloop/verifiers/part_quality.py`: a new verifier for every non-COTS part. Broken (error): not one solid, invalid
  B-rep, open shell / free edges, non-manifold edges, internal voids, tiny edges (< 0.05 mm), sliver faces (area
  < 0.01 mm2 or width < 0.1 mm), bad volume, mesh not watertight, self-intersection. Weird (warning): sparse bounding
  box, thin walls / webs (ray-cast, below the process minimum), near-coincident faces (slit < 0.2 mm), small steps
  (< 0.5 mm), near-parallel adjacent faces (< 2 deg), weak attachment, holes and slots nothing passes through,
  material outside a declared envelope. Odd dims (info): overall sizes and hole diameters off the 0.1 mm grid, hole
  sizes that are no standard size. Design-wide audits: every `allow_overlap` pair's real overlap volume (flagging
  overlaps that are not threads), joins held only by a note naming hardware that is not drawn, and purchased parts
  whose interface data lists holes their solid does not have or that do not meet a hole in the mating part. The
  thresholds and what each check cannot catch are in the module docstring and in docs/part_quality_v12.md.
- Opt-in only: it is not in the default verify (runner.OPTIONAL). Run it with
  `mechloop verify designs/printer_v12.py --only part_quality` or, without the rest of the verify machinery,
  `python -m mechloop.verifiers.part_quality designs/printer_v12.py --json out.json`. About 25 s on v12 after the build.
- Tests: tests/test_part_quality.py, a synthetic part for each check and a clean part that passes.
- Results on printer_v12: docs/part_quality_v12.md (per part, worst first) and
  mechloop/data/part_quality/printer_v12.json. 52 custom parts; 4 with errors (part_duct; nut_keeper x3), 7 with
  warnings (z_motor_plate_fl/fr, estop_bracket, x/y_endstop_carrier, sfs_mount, part_duct), 42 with neither. The two
  known true positives from the owner's review are found: the e-stop's switch block passing through estop_bracket
  (2430 mm3, hidden by allow_overlap; ring nut not drawn) and the z motors' listed M3 holes that their solid lacks.

What the numbers say: the automated checks find the clear artefacts, but most of what the owner is flagging is likely
class (c) and feature-purpose issues that need a spec (fix 1) and a reviewer (fix 3, "poor"). Compare the owner's
tagged feedback (kind/severity per part) with docs/part_quality_v12.md part by part; every owner flag the checks
missed is a candidate for a new check or a written guideline (fix 5).

Next:

1. Compare with the owner's review once it is done; record hits, misses and false alarms per check.
2. Specs for the custom parts, starting with the ones the owner and the checks both flagged (part_duct, nut_keeper,
   z_motor_plate, endstop carriers, estop bracket).
3. Feature vocabulary and the sheet-metal builder (fix 2); rebuild the flagged parts from spec as separate modules.
4. Vision reviewer on per-part renders with a rubric and reference designs (fix 3, poor).
5. Once v13 is clean, consider making part_quality's error class part of the default verify.
