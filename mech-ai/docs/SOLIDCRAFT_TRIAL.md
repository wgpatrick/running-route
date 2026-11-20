# SolidCraft trial: an independent second kernel for sheet-metal flats and mass properties

Trial run 2026-11-20, owner-approved, contained (scratchpad install, no change to the printer_v12 work, no heavy-solver lock
taken, all runs under `nice`). Artefacts: `reference_parts/solidcraft_trial/` (SolidCraft scripts, its flat DXFs and folded
STEPs, our folded STEPs, the hand calculation and the measured numbers).

## Summary

- **Verdict: the two sides agree.** On all three parts the flat size, bend-line positions, hole positions and cut length
  agree to within 0.002 mm. That is about 100 times inside SendCutSend's ±0.13 mm cut tolerance, with no bend-position or
  angle difference at all. Folded volume, area, mass, centre of mass and bounding box are the same to 1e-4 % on RP03 and
  the X belt bracket. The probe mount differs by 0.007 % in volume, and the cause is a modelling difference on our side,
  not a kernel disagreement (see below). Both sides also match the hand calculation from the bend-allowance formula.
- **What this does and does not prove.** Both sides took the same inputs (thickness, inside radius, K = 0.37). The trial
  confirms our unfold arithmetic and our build123d mass properties. It does not confirm that K = 0.37 is what SendCutSend's
  brake actually does: only a measured part can show that (mechloop/inspect).
- **Errors found on our side (the important result):**
  1. **Our pipeline does not unfold bent parts.** `verifiers/dfm_sheet.py` writes no DXF for a bent part
     ("not unfolded"). `shops/supplier_rules._develop` gives a blank size only for one-bend parts; a part with two or more
     bends gets none ("gap").
  2. **The build package ships wrong DXFs for the two bent printer parts.** `tools/build_package.export_part_files`
     writes a "flat profile" DXF for every `process == "sheet"` part. It takes the planar faces at the top of the part in
     its drawing frame. For a bent part that is not a flat pattern:
     - `docs/build/printer_v11/dxf/probe_mount.dxf` is a 2.286 x 23.9 mm sliver (4 LINEs: the end face of one leg).
     - `docs/build/printer_v11/dxf/x_belt_bracket.dxf` is only the straight part of one leg: 27.9 x 30 mm, 4 of the 6
       holes, no bend.
     - FABRICATION.md lists both parts as "flat (no bends)".

     Uploaded to SendCutSend as they are, both would come back as the wrong part. The correct flats are 33.000 x 70.649 mm
     and 40.409 x 30.000 mm (SolidCraft's DXFs in `reference_parts/solidcraft_trial/solidcraft/`, confirmed by hand
     calculation). Either send these parts as STEP with bends (SendCutSend takes STEP for bent parts) or unfold them before
     writing a DXF. build_package is shared by every design, so check the v12 package the same way before any v12 order.
  3. Minor: `round_profile` (in designs/printer_v11.py and v12) says it rounds *convex* corners, but it also puts R0.8 into
     concave ones. Its test, the outward-normal bisector pointing out of the material, is true at both kinds of corner.
     On the probe mount this adds a 0.314 mm³ inside fillet where the wide tab meets the leg. It does no harm, but the code
     does not do what its docstring says.
- **SolidCraft itself:** it installed from the release .deb with no compiling. Every script ran in about 1 s with no crash.
  It took our K-factor directly. Its quirks are listed under "What worked and what failed".

## Install

| Item | Value |
|---|---|
| Version | SolidCraft 0.45.0 (`solidcraft-cli --version` → `solidcraft-cli 0.45.0`), latest release tag v0.45.0 |
| Asset | https://github.com/tangency-labs/solidcraft/releases/download/v0.45.0/solidcraft-linux-x86_64.deb (203,006,030 bytes) |
| sha256 | `ba5aaa9bcd59ba56e4826e73b2c91603763b0db9fc932f48e6b962229d88db7f`. This matches the release's `sha256sums.txt` (also listed there as `solidcraft-0.45.0-linux-x86_64.deb`) |
| How | `dpkg-deb -x` into the scratchpad (`…/scratchpad/solidcraft/pkg/usr/bin/solidcraft-cli`, 229 MB). No root install, no AppImage. The AppImage's AppRun writes a wrapper into ~/.local/bin and desktop files; the .deb avoided that. `ldd` showed no missing libraries. No cargo build |
| Repo read for docs | github.com/tangency-labs/solidcraft @ c03abab (docs/scripts.md, docs/book/src/guide/sheet-metal.md, `solidcraft-cli commands`, examples/regressions/sheet-side-flange-corner.json) |

The binaries and downloads stay in the scratchpad. Nothing from SolidCraft is in git except the small outputs listed at the
top.

## Inputs: our sheet-metal parameters

- Thickness: 5052-H32 .090 in = **2.286 mm**.
- K-factor: **0.37**, SendCutSend's published value for 5052 .090 (`sendcutsend.bend.k_factor.al5052.2.286mm`), read
  through `supplier_rules._k_factor`.
- Bend allowance: BA = (r + K t)·θ. Bend deduction at 90°: BD = 2(r + t) − BA = 3.592 mm with SendCutSend's r 0.813, as
  `supplier_rules.bend_deduction` gives. SendCutSend prints .142 in.
- Inside radius, as modelled: RP03 r = t = **2.286**. The printer parts use r = **0.81** (`R_B23`; SendCutSend publishes
  0.813, which is inside `BEND_RADIUS_TOL_MM`).
- SolidCraft took the same values as a sheet rule (`sheet.manage_rules {thickness, k_factor, bend_radius}`), with no
  conversion.
- "Ours" folded parts come from our own code in the same frame as the SolidCraft scripts:
  - RP03: `make_reference_parts.rp03_sheet_channel()`.
  - X belt bracket and probe mount: `printer_v11.bent_L` / `probe_bracket_shape` + `round_profile`.
  - Each was checked against the shipped STEPs (`reference_parts/batch01/RP03_sheet_channel.step`,
    `docs/build/printer_v11/cad/*.step`): the same volume and area to 1e-3.
- "Ours" flats: our pipeline writes none for bent parts, so the reference is the hand calculation with our K and r. For the
  one-bend parts it is checked against our `_develop` blank, which gives 40.41 x 30 and 70.65 x 33.

**Parts.** No printer_v11 sheet part has two bends. The only bent parts are the X belt bracket and the probe mount, both
`bent_L` one-bend Ls (v12 uses the same `bent_L`). Both go to SendCutSend, so the trial used them. RP03 covers the two-bend case.

| Part | What | Bends |
|---|---|---|
| RP03 | U-channel 60 x 40, flanges 25 / 6, r = t, 3 x Ø5.5 | 2 |
| x_belt_bracket (printer_v11) | L, legs 13 / 31, 30 wide, 6 x Ø3.4, R0.8 corners | 1 |
| probe_mount (printer_v11) | L, legs 52.55 / 21.69, 25.5 wide with a 33-wide tab, Ø12.5 + 2 x Ø3.4, R0.8 corners | 1 |

## Method

1. SolidCraft JSON scripts (`solidcraft-cli run script.json --results --out folded.step`), one per part:
   - a base flange from a sketch, then edge flanges (90°, height to the outer virtual sharp);
   - corner fillets (sketch fillets, and `solid.fillet` on the flange's corners);
   - holes cut through the folded body from sketches;
   - then `sheet.flat_pattern`, `sheet.export_dxf` and the STEP.
   - The probe mount is built with its long leg as the base flange, because SolidCraft refuses a flat once a non-sheet
     feature (the tab) is joined after the flanges.
2. Both folded STEPs were measured with build123d (`import_step`, `.volume`, `.area`, `.center()`, `.bounding_box()`), and
   SolidCraft's DXF with ezdxf. Everything ran under `python -I` (`reference_parts/solidcraft_trial/measure.py`). Mass uses
   2.68 g/cm³ on both sides.
3. Hand calculation: L = Σ straight legs (outside dimension − (r + t) per adjacent bend) + Σ BA.

## Flat patterns

All dimensions in mm. Positions are from the flat's bounding-box edge (the free edge named in each row). Difference =
SolidCraft − reference.

| Part | Quantity | Hand calc (our K, r) | Our pipeline | SolidCraft | Diff |
|---|---|---|---|---|---|
| RP03 | Flat size | 82.5509 x 40.000 | none (not unfolded) | 82.5509 x 40.000 | 0.0000 |
| RP03 | Bend lines from tall-flange edge | 22.8877, 78.6632 | none | 22.8877, 78.6632 | 0.0000 |
| RP03 | Holes from tall-flange edge (all y = 20.0) | 16.178, 38.7755, 62.7755 | none | 16.178, 38.7755, 62.7755 | 0.0000 |
| RP03 | Cut length | 296.938 | none | 296.938 | 0.000 |
| x_belt_bracket | Flat size | 40.4090 x 30.000 | 40.41 x 30 (`_develop`) | 40.4090 x 30.000 | 0.0000 |
| x_belt_bracket | Bend line from leg-A edge | 11.2045 | none | 11.2045 | 0.0000 |
| x_belt_bracket | Holes from leg-A edge | 3.3802 (x2), 20.2090 (x2), 34.2090 (x2) | none | 3.3802, 20.209, 34.209 | 0.0000 |
| x_belt_bracket | Cut length | 203.532 | (shipped DXF: 157.846, wrong part) | 203.531 | −0.001 |
| probe_mount | Flat size | 33.000 x 70.6490 | 33 x 70.65 (`_develop`) | 33.000 x 70.6490 | 0.0000 |
| probe_mount | Bend line from leg-B end / leg-A top | 19.8945 / 50.7545 | none | 19.8945 / 50.7545 | 0.0000 |
| probe_mount | Ø12.5 hole from leg-B end, from tab edge | 10.500, 20.000 | none | 10.500, 20.000 | 0.000 |
| probe_mount | Ø3.4 holes from leg-A top (x from tab edge) | 5.500 (4.142), 36.000 (10.942) | none | 5.500 (4.142), 36.000 (10.942) | 0.000 |
| probe_mount | Cut length | 266.213 | (shipped DXF: 52.372, wrong part) | 266.211 | −0.002 |

**Hand check of the flat lengths:**

- RP03: BA = (2.286 + 0.37 · 2.286) · π/2 = 4.9195. L = (25 − 4.572) + (60 − 9.144) + (6 − 4.572) + 2 · 4.9195 = 82.551.
- X belt bracket: BA = (0.81 + 0.8458) · π/2 = 2.6010. L = 9.904 + 27.904 + 2.601 = 40.409.
- Probe mount: L = 49.454 + 18.594 + 2.601 = 70.649.
- With SendCutSend's printed deduction (.142 in = 3.607 mm) instead of the exact 3.591, the bracket comes out
  13 + 31 − 3.607 = 40.393: 0.016 mm shorter, which is rounding of the printed figure.

Note on RP03: it is modelled at r = t = 2.286, but SendCutSend forms .090 5052 at r 0.813. Made there, its flat would be
83.815 (+1.26 mm), with the outside dimensions held. This is a property of the reference part (it was built to break
rules), not a kernel difference.

## Folded part: mass properties

Volume in mm³, area in mm², mass in g at 2.68 g/cm³, positions in mm in the script frame. Both sides measured by build123d.

| Part | Quantity | Ours | SolidCraft | Diff (mm or %) |
|---|---|---|---|---|
| RP03 | Volume | 7470.890 | 7470.890 | 0.000 (0 %) |
| RP03 | Area | 7219.281 | 7219.281 | 0.000 |
| RP03 | Mass | 20.022 | 20.022 | 0 |
| RP03 | CoM | (−6.5009, 0, 4.7244) | (−6.5009, 0, 4.7244) | < 1e-4 |
| RP03 | Bounding box | 60.000 x 40.000 x 25.000 | 60.000 x 40.000 x 25.000 | 0 |
| x_belt_bracket | Volume | 2677.474 | 2677.474 | 0.000 (0 %) |
| x_belt_bracket | Area | 2809.907 | 2809.907 | 0.000 |
| x_belt_bracket | Mass | 7.1756 | 7.1756 | 0 |
| x_belt_bracket | CoM | (12.0319, 0, 2.8051) | (12.0319, 0, 2.8051) | < 1e-4 |
| x_belt_bracket | Bounding box | 31.000 x 30.000 x 13.000 | 31.000 x 30.000 x 13.000 | 0 |
| probe_mount | Volume | 4628.066 | 4627.752 | −0.314 (−0.0068 %) |
| probe_mount | Area | 4658.966 | 4659.476 | +0.510 (+0.011 %) |
| probe_mount | Mass | 12.4032 | 12.4024 | −0.0008 g (−0.0068 %) |
| probe_mount | CoM | (−2.7428, 22.3610, 3.1879) | (−2.7421, 22.3621, 3.1881) | (0.0007, 0.0011, 0.0002) |
| probe_mount | Bounding box | 33.000 x 52.550 x 21.690 | 33.000 x 52.550 x 21.690 | 0 |

SolidCraft's own `inspect.measure` gives the same volume, area and CoM as build123d to the precision shown. Its mass differs because it
used a default density (see below).

**Why the probe mount differs.** Our `round_profile` put an R0.8 fillet into the inside corner where the 33-wide tab meets
the 25.5-wide leg. The SolidCraft model, built to the drawing, has a sharp inside corner there. That fillet adds
(1 − π/4) · 0.8² · 2.286 = 0.314 mm³, which matches the volume difference exactly. It also changes the area by
2 · 0.137 − (1.6 − 1.257) · 2.286 = −0.510 mm², which matches too. With that corner accounted for, the two kernels agree
exactly on this part as well.

## What worked and what failed in SolidCraft

Worked:

- Sheet rules took an explicit K-factor and radius. The flat followed them exactly (bend allowance reported per bend: 4.9195
  and 2.6010, as calculated by hand).
- Base and edge flanges; sketch fillets.
- `solid.fillet` on a flange's corner edges, carried into the flat.
- Holes cut through the folded body from sketches on any plane appear correctly in the flat, including the hole on the
  tall flange of RP03.
- DXF with layers OUTLINE / CUT / BEND_UP; STEP export.
- Clear JSON results; every run took about 1 s and little memory. No crashes and no wrong results.

Failed, refused or awkward (none of these gave a wrong number):

- Joining a solid feature (an extrude) to a sheet body after its flanges makes `sheet.flat_pattern` refuse with a clear
  message ("can't include Extrude1, which changed the body after its sheet metal features"). This is correct behaviour.
  The workaround is to draw the irregular leg as the base flange.
- `inspect.measure` reports mass at a default density of 1.29 g/cm³ (body material "Default"). The rule's `material` label
  does not set the body's material, so a mass from SolidCraft needs a material assigned or a density applied by hand.
- `sheet.export_bend_table` with `format: json` writes the whole flat-pattern payload (27 KB with tessellated cut-outs) and
  not just the bend table.
- `sketch.line` returns point references as `l1.end` and so on, while `sketch.rectangle.two_point` returns `p1`… ids.
  Using `p3` on a polyline is refused ("unknown point"). The reply does say which form to use.
- The DXF carries bend centre lines on BEND_UP / BEND_DOWN. For SendCutSend, export with `bend_lines: false`, or check
  that their importer ignores those layers, so the lines are not cut.

Not tried (out of scope):

- `sheet.recognize` / `sheet.convert` on our STEPs (the trial rebuilt from dimensions on purpose).
- The MCP server.
- Rolls, hems, and corner reliefs between adjoining flanges.

## Verdict

Within SendCutSend's tolerances (cut ±0.13 mm; bend ±0.25 mm / ±1°), the two kernels agree:

- Flats: the largest difference is 0.002 mm, in cut length.
- Bend lines and holes: identical to 1e-4 mm.
- Folded mass properties: identical apart from one inside fillet that only our model has.

No disagreement needed settling. The hand calculation agrees with both sides.

The trial did expose a real gap in our pipeline: bent parts are never unfolded, and the build package's DXFs for the two bent
printer parts are wrong. Fix that before the next sheet order. A cheap regression test would be to compare our blank
against SolidCraft's flat for any new bent part, using `reference_parts/solidcraft_trial/` as the pattern.

The learnings ledger (`mechloop/data/learnings/ledger.jsonl`) holds only learnings proposed from measured parts, with
measurement evidence. A software cross-check does not belong there, so no entry was added.
