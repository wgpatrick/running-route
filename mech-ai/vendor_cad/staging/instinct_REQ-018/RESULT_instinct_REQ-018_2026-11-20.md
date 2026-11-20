STATUS: partial

# REQ-018: filament spool and feed path

Research-in-progress snapshot (2026-11-20). Per-item state below; open work is named per item. No payment, no new accounts; existing signed-in sessions only.

## Item 1: 1 kg spool with maker drawing/STEP — OPEN (no maker drawing found in inspected sources)

Maker-published dimensions found as text, not as a dimensioned drawing or STEP:

- Overture (official wiki, wiki.overture3d.com/en/Filament/PLA): spool 200 mm outer dia x 65.6 mm width, hub diameter 55 mm, empty spool mass ~147 g.
- Checked for a maker dimensioned drawing/STEP: Overture wiki/product pages, Prusament/Prusa help, Polymaker product pages, eSUN (third-party dimension tables exist, e.g. Reddit/duesenwerk3d, but those are not maker documents). None of these inspected sources publish a dimensioned drawing or STEP of the spool. Absence beyond these sources is not established.

Next: check Prusa's official Printables account and Polymaker/eSUN support pages for a published spool drawing before closing this as unavailable.

## Item 2: PTFE guide tube — research done

Capricorn XS (maker: Capricorn, captubes.com/specs.html):
- ID 1.90 ± 0.05 mm, OD 3.95 ± 0.05 mm (both as published on the maker's spec page).
- Minimum bend radius: not published on the inspected maker pages.
- US seller: RobotShop ("3D Printing Canada USA" storefront), Capricorn XS for 1.75 mm, $12.18 per 1 m length, 93 units in stock as displayed 2026-11-20. https://www.robotshop.com/products/3d-printing-canada-usa-capricorn-premium-ptfe-bowden-tubing-xs-series-for-175mm-1m
- Also sold cut-to-length (up to 5 m) at MatterHackers; price did not render in-session.
- Standard 4 mm OD / 2 mm ID alternative: Capricorn TL (ID 2.05 ± 0.05, OD 3.95 ± 0.05), same sources.

## Item 3: push-fit couplers for 4 mm PTFE — OPEN

- E3D Roto inlet: E3D's Roto docs (e3d-online.com/pages/revo-support-roto-standard-sensored) show the Bowden variant uses a screw-in "bowdaptor" at the bottom of the heatsink; the thread/size of that interface is not stated in the inspected E3D pages. E3D publishes official Roto reference CAD at https://www.printables.com/model/655950-e3d-roto-reference-cad — measuring the inlet thread from that CAD is the planned confirmation route.
- Coupler candidates (not yet pulled): McMaster metric push-to-connect male connectors for 4 mm OD tube in M5, M6, and M10x1 threads (generic PC4-M5/M6/M10 equivalents), each with McMaster STEP + dimensioned drawing. Capricorn's fittings guide (captubes.com/fittings.html) documents the PC4 thread taxonomy.

## Item 4: 608 bearing — OPEN (maker found, CAD outstanding)

- Pick: NSK 608ZZ via Misumi USA (real maker, REQ-named brand): $2.54 each, 560 in stock, ship date shown Sat. Nov 21, 2026. Configured specs as displayed: 8 mm ID x 22 mm OD x 7 mm W, basic dynamic load 3300 N, single row, steel. https://us.misumi-ec.com/vona2/detail/221000058301/?HissuCode=608ZZ
- CAD: Misumi's CAD download returns "No CAD file is available for the specified conditions" for NSK 608ZZ. EZO (SPB-USA) 608 variants via Misumi are also CAD-unavailable. A 608-2RS from McMaster (5972K222, $18.46) does have STEP + drawing but is McMaster's unbranded part, not an SKF/NSK/NTN brand.
- Next: pull SKF 608-2RSH STEP via the existing 3dfindit/CADENAS login and an official SKF datasheet PDF from skf.com (product page https://www.skf.com/us/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-608-2RSH has a Download-PDF control that needs the JS flow).

## Holds and compliance

Nothing purchased. No accounts created. All prices/stock/ship labels are quoted as displayed; dates in PST.
