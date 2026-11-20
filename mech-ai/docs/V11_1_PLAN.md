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
