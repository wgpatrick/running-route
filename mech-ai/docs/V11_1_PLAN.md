# printer_v11.1 plan (owner decisions, 2026-11-20)

Starts from the finished v11. Goal: every purchased part is a real, orderable product with maker CAD or a faithful re-make
of the maker's drawing (docs/DESIGN_GUIDELINES.md, key rule), and X travel won back with a stock rail.

1. X rail: stock HIWIN MGN-R12-R300-HM (300 mm, Digi-Key $125, ~100 in stock; confirm the length on the order page) with
   HIWIN block MGN-12-H-Z0-HM ($59). Lengthen the X beam / move the Y carriages as needed inside the 420 mm frame; report
   the real X travel and its limit. Fallback MGN-R12-R220-HM only if 300 cannot fit (ask the owner first).
2. Belts: 9 mm GT2 (2 mm pitch, Gates 2MGT stock width) on Y as well as X; no 12 mm GT2 (not a stock width). Re-run the
   belt check (stretch, stiffness, tooth load) and report.
3. Pulleys and idlers: MISUMI 20-tooth GT2, 9 mm belt, 5 mm bore (GPA20GT2090-B-P5 / -A-N5 class; exact part numbers and CAD
   from REQ-002).
4. Spacers: stock lengths only (Harwin R30 / RAF), stacking two where needed; no custom lengths (5.5, 6.1, 9.725, 13.2,
   40 mm are not stock).
5. Bed heater: a stock heater from a real maker with a datasheet (e.g. 200 x 200 mm, 24 V); size the bed to suit. A custom
   heater is the fallback, treated as made to our spec.
6. Apply the provenance audit (docs/PROVENANCE_AUDIT.md, "Ready for Phase 3") and every maker file that has arrived
   (vendor_cad/staging/provenance_2026-11-19/, Instinct's REQ-001 / REQ-002 results).
7. Placeholders: any purchased part still without maker data is named PLACEHOLDER-... in the BOM, flagged in the viewer and
   listed at the top of docs/PRINTER_V11_1.md; the DG-07 check reports each as an error.

## Linear rails (owner, 2026-11-20)

- X: genuine HIWIN MGN-R12-R300-HM rail + MGN-12-H-Z0-HM block (Digi-Key; accuracy H). Declare the Z0 preload in the model.
- Y and Z: LDO Motors MGN12H rail + block sets (rail 12 x 8, 25 mm pitch, block 45.4 x 27 x 13 per LDO's drawing; accuracy
  class C, light clearance fit, not preloaded; about GBP 31-34 per set at 300-400 mm, in stock). Stock lengths only: Y 300
  or 350, Z the nearest stock length that gives the Z travel (HIWIN-style 245 is not an LDO length; check LDO's list).
- The checks must model LDO's clearance (play) in the bed-support, tolerance and motion checks (Y rail parallelism, Z tilt
  allowance, bed level over travel) and pass; if Y fails, fall back to HIWIN on Y. LDO CAD and full drawing: REQ-004/005.
- Estimated rails total about $365 (vs $1,104 all-HIWIN).

## Bed thermal limit (b) (owner, 2026-11-20)

v11 fails limit (b), nozzle-gap change after probing: -0.101 mm vs 0.1 mm (computed as if probed cold).
- Commissioning procedure: probe the bed after a heat soak (bed at print temperature, stated soak time from the thermal
  model's time constant); model limit (b) on that basis, with the remaining carrier warming only. Write the soak into the
  build package's commissioning steps and the Klipper start macro.
- Also evaluate a stiffer / shorter thermal path in the bed carrier and report its effect on (b) and on mass/cost.

Update (owner, 2026-11-20): no international shipping. LDO (UK-only) is out for Y and Z. X stays genuine HIWIN. For Y and Z:
evaluate US-stocked options — HIWIN (about $185/set, Digi-Key/MotionUSA), IKO ML12 (about $84/assembly at Misumi USA, to
confirm), NSK PAU12 ($49 at MROSupply, block or assembly to confirm), Misumi SSEB13 (from $117) — noting rail height (8 vs
7.5 mm) and block length differences against MGN12H, and the two-Z-rails option. Choose the cheapest that passes the checks.

## Rails, revised (2026-11-20, REQ-009)

Genuine HIWIN MGN12HZ0C sets (rail + one MGN12H block, preload Z0, accuracy class C) from Motion Constrained (Colorado), $79.64
per set with free US shipping, rail 295 mm (HIWIN standard length; E = 10/10). Six sets about $478 for all axes (vs $1,104 at
Digi-Key). Design to 295 mm rails (X travel about 5 mm less than the 300 mm plan); Z may use 295 or 245 (rail-only $49.49 +
block) as the Z travel requires. Use the HIWIN official CAD (REQ-005) with the length changed per HIWIN's E rule. Confirm
stock and lead time before ordering.

## Frame corner brackets (owner-supplied Misumi pages, 2026-11-20)

- Standard: MISUMI HBLFSN5-SEP (reversal tabbed bracket, 30 x 30 legs, 20 wide, 4.5 thick, 3 x dia 5.3 holes; aluminium
  casting alloy 383.0, no surface treatment; 15 g; allowable load 1176 N; Misumi lists 2 screws + 2 T-nuts per bracket).
  -SEP = Misumi's matched set: CBM5-10 screws + HNTP5-5 post-assembly spring nuts (drop-in, per the owner's T-nut rule).
- Where a 30 mm leg does not fit: HBLFSNF5-SEP (30 x 20 legs, 20 wide, 2 x dia 5.2; 13 g; same load and set).
- No alteration C (cover taps) needed.
- Source: Misumi catalogue pages supplied by the owner (dimension drawing, materials, specifications, alterations).
  CAD to collect: HBLFSN5, HNTP5-5, CBM5-10 (HBLFSNF5 STEP already staged, vendor_cad/staging/instinct_REQ-001b/).
