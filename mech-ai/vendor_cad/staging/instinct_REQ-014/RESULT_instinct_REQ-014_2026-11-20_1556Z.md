STATUS: partial - item 1 resolved via owner-approved plated alternative S-M3-0ZI (CAD + drawing delivered), items 2-3 fulfilled from existing batch01 records (no new submissions); SendCutSend shipping still unknown

# REQ-014 RESULT: PEM nut CAD via Bossard; SendCutSend cart for RP03/RP04

Run: Nov 20, 2026. Rules kept: no payment, no checkout, no manual review, no new accounts, no repeated submissions, nothing disclosed beyond quoting needs.

## 1. PEM S-M3-0 / S-M3-1 - RESOLVED via owner-approved alternative (Nov 20)
Owner approved the zinc-plated S-M3-0ZI and CAD acquisition from PEM or McMaster (iMessage, Nov 20).
- Delivered S-M3-0ZI__cad.step and S-M3-0ZI__drawing.pdf: official McMaster-Carr CAD for McMaster 95185A520, which McMaster cross-references to PEM S-M3-0ZI (zinc-plated steel press-fit/self-clinching nut, M3 x 0.5 mm, for 0.8 mm minimum panel thickness, round head).
- Price/stock as displayed: $3.75 USD per pack of 25, in stock ("Delivers Monday by 5 pm", Nov 20). No purchase made.
- PEM's own catalog (catalog.pemnet.com) also offers S-M3-0ZI STEP AP203/AP214/AP242, but its download demands a User Information form (email, first name, last name, company, job title, country) - beyond the approved disclosure scope, so it was not submitted; McMaster needed no form.
- Bossard findings (kept for the record): plain S-M3-0/S-M3-1 not stocked; only plated variants (S-M3-0ZC, S-M3-0ZI, S-M3-1ZI, S-M3-2ZN, S-M3-2ZI, S-M3-3ZI). S-M3-0ZC out of stock, "Request a quote" only, no price, no CAD on the page.
## 2. PCBWay review comments for RP03/RP04 (order C-CN24W734350A) - verbatim, from existing records
Source: batch01_quote_log.csv (Drive id 1ZWps324rhZ9oJ_po9cpnUyEHhHftKJmY), email channel with Kingsely (PCBWay), dated 2026-11-19. No payment made; the order stays as is.

- RP03, verbatim: "RP03: we don't have Aluminum 5052 in 2.29 mm, 2 mm and 2.5 mm is available."
- RP04, verbatim: "RP04: we don't have Aluminum 6061 in 3.18 mm, 3.2 mm is available."
- RP01, RP02, verbatim: "RP01, RP02: If you need us tap thread, pls als prepare a technical drawing to point out where need thread and the thread description. Sample drawing attached for reference."
- File requirements, verbatim: "We need 3D file to quote and order via system (our engineers review files via system)." Accepted formats listed: CNC .stp/.step/.iges/.igs/.x_t/.sldprt; sheet metal 3D same plus 2D .dwg/.dxf/.pdf; 3D printing .stl/.obj/.step/.stp/.3mf.
- Order chronology (existing records, gmail thread 1a1f7aa1c196f342 + screens/pcbway folder): no 2.29 mm stock; the failed review demanded an actual 2 or 2.5 mm file; a revised 2.5 mm file passed review. Price: $12.45 system prequote, $25.11 on the failed-reviewer quote, unchanged $25.11 after pass; qty 1, 6-8 days. No qty-10 quote exists; no payment made.

## 3. SendCutSend cart for RP03/RP04 - historical quotes on record; no fresh cart built
These are HISTORICAL quotes from the Nov 19, 2026 batch01 benchmark run (same files, materials, quantities), verbatim from batch01_quote_log.csv (rows dated 2026-11-19) - NOT a fresh cart. No new upload was made (standing ruling: no repeated submissions; don't cross checkout to chase shipping). Shipping remains UNKNOWN: SendCutSend shows shipping only in checkout, which was not crossed. Prices below may have changed since Nov 19.

- RP04_laser_plate.dxf, 0.125 in 6061-T6, process as understood: Sheet Cutting (laser); material as understood: 6061-T6 Aluminum 0.125" (3.2mm), finish none.
  - qty 1: $15.01 USD total, "Arrives as soon as: Mon, Nov 23". Qty breaks: 2=$10.87, 50=$7.08, 100=$6.21, 1000=$4.67 (per unit).
  - qty 10: $90.50 USD total ($9.05/unit), "Arrives as soon as: Mon, Nov 23".
  - DFM verbatim: "1 Issue found | Review Required: Hole-to-Edge Bridging | Order review required due to hole to edge distance | The minimum hole to edge distance for instant quoting in this material is 0.97 mm."
  - The 1.2 mm hole, 1 mm slot and sharp corner were NOT flagged. The order review happens at order time and does not block the quote.
- RP03_sheet_channel.step (original, 0.090 in 5052-H32, bent), process as understood: Sheet Cutting + Bending (2 bends detected).
  - qty 1: $21.64 USD total including default Deburring ($2.54/ea), "Arrives as soon as: Tue, Nov 24". Qty breaks: 2=$12.57, 50=$5.33, 100=$4.58, 1000=$3.10 (per unit).
  - qty 10: $68.50 USD total incl. deburring ($6.85/unit), "Arrives as soon as: Tue, Nov 24".
  - DFM verbatim: "Bend Radius Warning | The bend radius for your part (0.09") does not match the SCS bend radius for this material (0.032"). This will impact the finished dimensions of your parts. | 2 Bends Affected" and "Bend Minimum Flange Contact Error | Some flanges on your part are too short to be bent properly. 5052 H32 Aluminum (.090") requires a minimum flange length of at least 0.254". You have three options to resolve this issue: Clear affected bends from this part / Select another material or thickness / Adjust the design to increase the flange length | 1 Bend Affected".
  - NONMATCHING INDICATIVE QUOTE, blocked (per the earlier parent ruling, still in effect): the flange error blocks the finishing wizard step, so finish "none" could not be selected and the price includes default Deburring; the price is visible but does not imply manufacturability approval; the dimensional-variance checkbox was NOT accepted. The hole-near-bend was not flagged.
- SendCutSend terms check before any upload (re-verified Nov 20 against https://sendcutsend.com/terms-of-service): no clause forbidding automated or bot access. Noted: an account is required to place an order; US/Canada shipping only.

## Open (owner decisions - not re-run automatically)
- Fresh SendCutSend cart with shipping: only if the owner wants it despite the checkout-crossing rule; the historical quotes above stand until then. (A separate checkout task owns RP04 purchase prep - this folder's job was research only.)
- Item 1 closed by the owner-approved S-M3-0ZI alternative above.
