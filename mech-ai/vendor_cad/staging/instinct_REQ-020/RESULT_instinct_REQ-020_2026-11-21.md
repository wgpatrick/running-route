STATUS: PARTIAL — fulfilled: item 1 (NSK dimension page + STEP per the request's NSK-or-Misumi wording), item 2 (axle, nut, washer candidate), item 4. UNRESOLVED: item 3 centering sleeves only (search continues next run).

# REQ-020-spool-hardware — Results

## Item 1: NSK 608ZZ bearing reference + CAD
- nsk-608zz1mc3-dimension-page.pdf — NSK's own engineering dimension page for 608ZZ1MC3 (nsk.com, public page): d 8 / D 22 / B 7 mm, r min 0.3, Cr 3650 N, C0r 1370 N, 34000 rpm, clearance MC3, ISO NORMAL class. Captured as PDF. Bounded note: NSK's 608ZZ1MC3 engineering page (the only NSK source inspected) offers no PDF download; other NSK sources were not checked for a PDF.
- B608ZZ__cad.step — official Misumi STEP (AP214) for Misumi's own B608ZZ (8x22x7 double-shielded bearing, the same dimensions and ZZ shielding as the NSK 608ZZ). Assessment against the request wording: the request asks for a STEP "if NSK or Misumi offers one"; Misumi offers this one, so the STEP requirement is fulfilled as worded, from a named source. Provenance: Misumi-authored, not NSK-authored. The NSK-brand 608ZZ listing on Misumi carries no CAD ("No CAD file is available for the specified conditions", checked while signed in, Nov 20); 3dfindit (also named acceptable in the request) is currently bot-blocked and was not retried. An NSK-authored STEP specifically was not obtained, but the request does not require NSK-authored CAD.
- Buy reference (Misumi, NSK-brand 608ZZ listing, as displayed): $2.54 each (1-20), $2.16 (21-50), $2.03 (51-560), $2.03 TBD (561+); ships Sat Nov 21, 2026.

## Item 2: M8 axle ~80-90 mm with M8 threads + nut + washer
Axle: Misumi SFAL8-90-B15-S15 (Both Ends Threaded Linear Shafts, hardened 52100 steel, g6 tolerance, D=8 mm, L=90 mm, M8 x 1.25 threads both ends, 15 mm thread length each end).
- SFAL8-90-B15-S15__cad.step (official Misumi STEP, AP214)
- SFAL8-90-B15-S15__datasheet.pdf (official Misumi catalog page, visually verified: correct series with dimension diagram and D=8 row)
- Price as displayed: $37.87 each (1-4), $20.83 (5-12), $18.94 (20-49), $18.18 (50-100); ships Wed Nov 25, 2026.
Nut: McMaster-Carr 90592A022 — title-verified "Steel Hex Nut, Medium-Strength, Class 8, M8 x 1.25 mm Thread Size".
- 90592A022__cad.step (official McMaster STEP, AP214)
- 90592A022__datasheet.pdf (McMaster 2-D dimension drawing)
- Price as displayed: $6.51 per pack of 100; delivers Monday by 5 pm.
Washer: Misumi WSF20 — Linear Shaft Washer ("End-Washer for Linear Shaft", official Misumi WSF series), 1045 carbon steel, black oxide: ID d 8 (+0.3/+0.1), OD D 20 (±0.2), T 5 (±0.2). This is a DIMENSIONED CANDIDATE matched to the 8 mm shaft, not a verified fit: bearing contact pattern and seal/outer-race clearance against the 608 (D 22) depend on the intended assembly, which I have not verified against an assembly drawing or maker guidance. Misumi's own application example shows WSF as a shaft end-washer against a plate, not against a bearing.
- WSF20__cad.step (official Misumi STEP, AP214, verified)
- WSF20__datasheet.pdf (official Misumi catalog page 289 crop, visually verified: WSF series dimension diagram + full size table with D20/d8/T5 row)
- Price as displayed: $3.49 each (qty 1-7, ships Sat Nov 21, 2026, 7 in stock); 8-19 $3.49 TBD; 20-499 $1.44 TBD; 500+ $1.37 TBD.
- Supersedes my earlier McMaster 91116A160 pick (18-8 SS oversized washer, 8.4 ID / 24.0 OD); its files have been removed from this folder. Neither part is a verified fit; WSF20 is the closer dimensional match to an 8 mm shaft application.

## Item 3: two centering sleeves (ID fits 22 mm bearing OD, OD <= 50 mm)
NOT COMPLETE — bounded McMaster/Misumi search not finished this run. Will either deliver a stock part with files or state that no stock part exists (fabricate per REQ) next run.

## Item 4: REQ-019 spacer
Already fulfilled — see results/REQ-019-* folder (files + RESULT.md landed Nov 20).

## Notes
- All CAD is official vendor CAD (Misumi / McMaster-Carr); nothing generated. The separate SKF-authored 608 CAD question belongs to REQ-018 and is tracked there, not here.
- All prices/ship dates are exactly as displayed on the vendor pages, Nov 20, 2026. Nothing purchased; no accounts created; no terms accepted.
