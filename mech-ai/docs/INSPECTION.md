# Inspection: measuring the parts that come back, and learning from them

Stage 0 of Build 1 is a few of our own sheet parts ordered from SendCutSend / Fabworks to test bend radii, flanges,
holes near bends and fit against our predictions. This is the workflow from "the box arrived" to "the system has
proposed what to change". Tools needed: calipers, an engineer's square, a feeler gauge set, the flatbed scanner, and a
printed calibration target.

Code: `mechloop/inspect/` (plan.py, scan.py, record.py, import_form.py). Data: `inspect_form/plans/` (the plans),
`mechloop/data/measurements/` (the record and orders), `mechloop/data/learnings/ledger.jsonl` (the learnings).

## 0. Before the order: plans and the form

```
.venv/bin/python -m mechloop.inspect.plan --stage0          # RP03, RP04, printer_v10_1 x_belt_bracket, y_plate_left, z_deck
.venv/bin/python -m mechloop.inspect.import_form --build    # embeds the plans in inspect_form/index.html
.venv/bin/python -m mechloop.inspect.scan --make-target --out inspect_form/target
```

Each plan (`inspect_form/plans/<part>.json` + `.svg`) lists the dimensions that matter, ranked by what depends on them:
hole pitches in a pattern that takes a mating part's screws, holes our checks expect to distort near a bend, bend angles,
bend radii, flange lengths, holes measured from a bend, fastener hole diameters, hole positions, overall size, flatness,
stock thickness. For each: nominal, tolerance (the shop's published figure where it has one: SendCutSend cut +/-0.127 mm,
bend-to-edge +/-0.381 mm, bend angle +/-1 degree; otherwise mechloop's class value, marked as such), what we predict
(e.g. RP03's 6 mm flange predicted 5.68 mm because SendCutSend bends .090 in 5052 at 0.813 mm, not our 2.286 mm), the
verbatim finding behind the prediction, and how to measure it. The SVG shows the part with a numbered balloon per
dimension.

Record the order when it is placed (loop time starts here):

```python
from mechloop.inspect import record as R
R.add_order("SCS-123456", "sendcutsend", ["RP03", "RP04"], placed="2026-12-01", design_changed="2026-11-28")
```

## 1. The order arrives

Record the date received: `R.add_order("SCS-123456", "sendcutsend", ["RP03", "RP04"], placed="2026-12-01", received="2026-12-06")`
(rows with the same order id are merged, later dates win). Number the pieces if you ordered more than one (piece no. in the form).

## 2. Flat parts: scan with the target

1. Print `inspect_form/target/scan_target.pdf` at 100 % ("actual size"). Measure the 150 mm bar with calipers; if it is
   not 150.00, the print scale is `measured / 150` (`--print-scale`).
2. Cut a strip of dots (three columns are enough) and lay it on the glass beside the part, dots down. Lay the part on the
   glass, top face down (the scan is then read as the DXF's top view; a part the other way up is detected as mirrored and
   handled). Close the lid: the part must be dark against a light lid. Scan greyscale at 600 dpi (1200 for small holes),
   no auto-crop, no "descreen" or sharpening, PNG or TIFF.
3. Run:

```
.venv/bin/python -m mechloop.inspect.scan scans/rp04.png --dxf reference_parts/batch01/RP04_laser_plate.dxf \
    --dpi 600 --plan inspect_form/plans/RP04.json --out out/inspect/scans
```

It writes `<scan>.scan.json` (scanner scale as measured by the target, the part's rigid fit to the DXF, every hole's
diameter and position error, each straight edge's offset, overall size) and `<scan>.deviation.png` (deviations drawn 50
times larger). Turn the scan into record rows with `record.rows_from_scan(scan_json, plan, order=..., who=...)` and
`record.add(...)`.

Without the target the scanner's own scale error (typically 0.1-0.5 %, i.e. 0.1-0.6 mm over a 120 mm part) goes straight
into the sizes; with it, synthetic scans of RP04 (600 dpi, 7 degree rotation, +0.4 % / -0.3 % scanner scale, blur and
noise) come back within 0.01 mm on hole diameter, 0.01 mm on hole position and 0.002 mm on overall size, and a hole
moved by 0.30 mm is found at 0.297 mm (tests/test_inspect_scan.py).

The scan also works for a separate target scan with the same settings (`--target-scan target.png`), when the part covers
the glass.

## 3. Everything else: calipers, square, feeler gauge, through the form

Open the form (the published page of `inspect_form/index.html`). Enter the order, supplier, piece number and your
initials once at the top. For each part card, measure the numbered dimensions in the drawing that the scan did not
cover: bend angles (square and feeler gauge), flange lengths and hole-to-bend distances (calipers from the outside
face of the other flange), the two diameters of a hole near a bend, bend radius (radius gauge), flatness (feeler under a
corner), thickness. Each row shows nominal +/- tolerance, the prediction and a live in/out chip. "Save measurements"
writes one entry per part to the page's shared store (collection `measurements`); where the store is unavailable it
shows the same entry as JSON to copy. Then:

```
.venv/bin/python -m mechloop.inspect.import_form rows.json      # an export of the collection, or pasted JSON
```

## 4. Report and proposed learnings

```
.venv/bin/python -m mechloop.inspect.record summary     # per supplier / material / thickness / check kind: bias, scatter, in/out
.venv/bin/python -m mechloop.inspect.record propose     # appends new proposed learnings to the ledger
.venv/bin/python -m mechloop.inspect.record metrics     # loop time, fidelity, autonomy
.venv/bin/python -m mechloop.inspect.record accept --id L-... --by owner --note "checked"
```

A learning is proposed when one check kind in one group (supplier, material, thickness) has at least 3 measurements and
a mean deviation larger than twice its standard error and a small floor. Examples: "SendCutSend al5052 .090 in (2.286 mm)
inside bend radius measured 0.84 mm vs rule 0.813 mm (n=3)" -> the rule's `value_mm`; a bend-angle bias or scatter ->
`mechloop/tolerance/bends.py`; a flange or hole-to-bend error -> the shop's K-factor; a hole-diameter bias -> the hole
allowance in `mechloop/tolerance/process.py`; edge or slot offsets -> kerf compensation; whether holes near bends really
went oval -> evidence for the hole-to-bend rule. Each learning carries its evidence (measurement ids, n, mean, sd), the
prediction error before and after (after is leave-one-out), and status `proposed`. Nothing edits a rule automatically:
accepting is the owner's or the parent agent's call, and applying an accepted learning is a separate, reviewed change
that cites the learning id.

Loop metrics: loop time (design change -> order -> received -> measured), fidelity (mean |predicted - measured| per check
kind, beside |nominal - measured| as the do-nothing baseline), autonomy (manual steps per part per order: each caliper
reading and each scan counts one, the importer and the scanner pipeline count none). These are the numbers the loop
itself should improve.

## Bent parts: what the scanner can and cannot do yet

- Each flange that lies flat on the glass can be scanned like a flat part; the holes on it are measured, holes near a
  bend as ovals (two diameters) to quantify the stretching the checks predict. Registration to a single flange's outline
  (cut from the 3D model at that face) is the next step; until then use the form for those holes.
- Bend angle by photo (later step): stand the part on one flange on a printed angle grid (radial lines every degree about
  a pivot mark) and photograph square from above; or stand the part on its end on the scanner glass, whose image shows
  the bend's end profile. Fitting the two flange edges gives the angle, fitting the inside arc gives the radius the shop
  actually formed. Today: square and feeler gauge (angle = 90 + atan(gap / flange length)), radius gauge.

## Machined and printed parts

The plan generator handles them with the process-class tolerances or the print service's published figure (Hubs FDM:
+/-0.5 % with a +/-0.5 mm floor); printed holes are predicted 0.15 mm small. The scanner works for any part with a flat
face on the glass and a DXF or outline of that face.
