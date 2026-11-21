STATUS: PARTIAL — items 3 and 4 have maker STEP + datasheet + US stock/price; items 1-2 are sourced candidates only, with maker STEP blocked by account walls held for owner decision (Omron registration, TraceParts) or not retrievable from the maker in this session (Eaton). All candidates below are sourced candidates, not a verified compatible safety system: matches are limited to the component attributes the request named (form factor, reset type, contact form/count, width, ratings as listed); electrical integration and system-level suitability are unverified.

Provenance and stock notes per item below. Prices as displayed, USD, single-unit unless noted, checked 2026-11-20 ~7:40-7:55 PM PST. "In stock" counts are as displayed by the seller at check time.

== Item 1: Emergency stop (22mm, mushroom, latching twist-to-release, red, >=1 NC) ==

Candidate A: Omron A22E-M-02 (complete assembly: switch + locking ring + nut)
- Matches the request's component attributes: 40mm red mushroom, push-lock turn-reset (twist-to-release), panel mount front, 22.3mm cutout, DPST-NC (2 NC, meets "2 NC preferred"), screw terminals, IP65, 10A AC / 8A DC rating per DigiKey attributes. Suitability for the printer's safety circuit (voltage, current, wiring) unverified.
- Seller: DigiKey (US) — In-Stock: 343; $94.27 unit (5+: $82.232). Source: digikey.com/en/products/detail/omron-automation-and-safety/A22E-M-02/549568
- Datasheet: A22E-M-02__datasheet.pdf = pages 33-36 + 41-42 (ordering/ratings + dimensions) extracted from Omron's 52-page A22E datasheet (19 MB original exceeds the 9 MB file limit; rendered at 150 dpi). Full original: assets.omron.com (A22E_A263-E1_20_2-pdf.pdf).
- Maker STEP: BLOCKED — Omron CAD downloads sit behind an Omron account registration (industrial.omron.eu CAD page is a login/register form). Registration not approved; held as an owner decision.

Candidate B: Eaton M22-PVT-K02 (complete device: twist-release e-stop operator + 2 NC contact blocks, single part number)
- Matches the request's component attributes: red mushroom, twist-to-release, panel mount front, 22.5mm cutout, DPST-NC (2 NC), per DigiKey attributes and the Eaton spec sheet. Suitability for the printer's safety circuit unverified.
- Seller: DigiKey (US) — In-Stock: 27; $100.77 unit (5+: $87.90). Source: digikey.com/en/products/detail/eaton-electrical/M22-PVT-K02/25844231
- Datasheets: M22-PVT-K02__datasheet.pdf (Eaton-authored spec sheet incl. AutoCAD 2D footprint reference, Werner Electric-hosted mirror) and M22-PVT__datasheet.pdf (Eaton-authored operator datasheet, Farnell-hosted mirror; Eaton's own datasheet endpoint is JS-rendered and did not load in the browser session).
- Maker STEP: NOT RETRIEVED from the maker in this session — Eaton skuPage renders no CAD section, eaton.partcommunity.com (Eaton's former CAD portal) does not resolve, Eaton Download Center exposes only tabular product data, and ecat search did not render. Bounded claim: these routes only, in this session. DigiKey lists third-party EDA models for M22-PVT, which were not used (not maker-authored).
- Alternative build if the complete device is unwanted: M22-PVT operator (337 in stock, $57.40) + 2x M22-K01 NC blocks ($17.42 each, 0 in stock / backorder at DigiKey at check time); calculated assembly total $92.24 (calculation; M22-A adapter $4.98 listed as companion, stock not checked).

Note: Schneider XB4BS84445 (2NC, twist, 22mm) was checked and set aside: DigiKey does not stock it ($144.18, "check lead time"). IDEC FB1W-HW1B-V402R-EMO-2 likewise 0 stock at DigiKey.

== Item 2: Safety relay (24VDC, dual-channel e-stop, >=2 NO safety out, DIN rail, <=22.5mm) ==

Candidate A: Phoenix Contact PSR-SCP-24DC/ESP4/2X1/1X2 (part no. 2981020)
- Matches the request's component attributes: 2 NO safety contacts (DPST-NO, 2 Form A), 6A contact rating, 24VDC coil 60mA, DIN rail, width 22.5mm (at the REQ limit), automatic/manual start per datasheet, screw terminals. Dual-channel e-stop wiring and reset-mode configuration for this build unverified.
- Seller: DigiKey (US) — In-Stock: 23; $285.21 unit. Source: digikey.com/en/products/detail/phoenix-contact/2981020/2237316
- Datasheet: PSR-SCP-24DC-ESP4-2X1-1X2__datasheet.pdf (Phoenix Contact-authored catalog data sheet, Distrelec-hosted; phoenixcontact.com blocked curl fetches with 403 in this session).
- Maker STEP: BLOCKED — the product page's "3D view and CAD download" is a TraceParts iframe; CAD download requires a TraceParts account. TraceParts registration is held (owner decision).

Candidate B: Omron G9SE-201 (24VDC)
- Matches the request's component attributes: 2 NO safety outputs (DPST-NO, 2 Form A), 5A contact rating, 17.5mm wide, DIN rail, screw terminals. Manual/auto reset supported per G9SE series datasheet (J198). Suitability for the printer's safety circuit unverified.
- Seller: DigiKey (US) — In-Stock: 279; $275.29 unit (10+: $245.102). Source: digikey.com/en/products/detail/omron-automation-and-safety/G9SE-201/7495167
- Datasheet: G9SE-201__datasheet.pdf (Omron-authored J198 G9SE datasheet, assets.omron.eu).
- Maker STEP: BLOCKED — Omron account registration wall (same as item 1), held as owner decision.

Note: Pilz PNOZ s3 checked — not carried by DigiKey; no verified US stock from an accessible seller in this session.

== Item 3: Dowel pins 4mm x 8mm hardened steel (COMPLETE) ==

McMaster-Carr 91595A150 — 52100 alloy steel dowel pin, 4mm dia x 8mm, tolerance +0.004/+0.012mm (m6, press fit), min hardness Rockwell C52, DIN 6325-m6 / ISO 8734.
- $12.10 per pack of 50 (pack price as requested); "Delivers Monday by 5 pm" shown at check time (in stock).
- Files: 91595A150__cad.step (McMaster CAD, STEP AP203 as served — McMaster does not offer AP214), 91595A150__datasheet.pdf (McMaster dimensioned drawing X.GIF rendered to PDF).
- Source: mcmaster.com/91595A150/
- Hole-size/press-fit suitability for the specific aluminium parts is a fit question for the build, not verified here.

== Item 4: LRS-350-24 alternatives (COMPLETE) ==

1) Mean Well RSP-320-24 (320W, 24V 13.4A, 88-264VAC, active PFC)
- Seller: meanwellsource.com (US Mean Well distributor) — $78.96, "In stock / Ships in 3-5 business days" as displayed. DigiKey does not currently list RSP-320-24 (search redirects to a substitute); Jameco/Mouser/Newark/Allied/TME were not price-verifiable in this session (bot-blocked or 403).
- Files: RSP-320-24__cad.step (maker 3D, series-level model RSP-320.stp from meanwell.com, AP214), RSP-320-24__datasheet.pdf (maker spec PDF, meanwell.com).
2) Mean Well UHP-350-24 (350.4W, 24V 14.6A, 90-264VAC, slim 41mm height)
- Seller: meanwellsource.com — $102.01, "In stock / Ships in 3-5 business days". DigiKey page for UHP-350-24 states "This product is no longer available at DigiKey".
- Files: UHP-350-24__cad.step (maker 3D, series-level UHP-350(201111).stp, AP214), UHP-350-24__datasheet.pdf (maker spec PDF).
3) Non-Mean Well: XP Power LBA350PS24 (350W, 24V 14.6A, 90-264VAC, enclosed chassis mount, 215x115x30mm)
- Seller: DigiKey — In-Stock: 63; $44.75 unit (5+: $43.408). (DigiKey's RSP-320-24 search redirects to this part as its suggested substitute.)
- Files: LBA350PS24__cad.step (maker STEP, series-level LBA350.STEP from xppower.com, AP214), LBA350PS24__datasheet.pdf (maker datasheet SF_LBA350.pdf).

Note: PSU STEP files are series-level models (same enclosure across output voltages); they represent the -24 variants' mechanics, not voltage-specific internals. Electrical suitability for the printer (inrush, wiring, cooling) unverified.

== Open items / holds ==
- Omron account registration (would unblock A22E-M-02 and G9SE-201 maker STEP) — owner decision, not approved.
- TraceParts registration (would unblock Phoenix 2981020 maker STEP; also noted on REQ-018) — owner decision, held.
- Eaton maker STEP: not retrievable in this session via Eaton's own routes (see item 1 candidate B). A fresh-session retry of eaton.com is plausible; not a registration hold.
- No purchases made; no accounts created; nothing shared beyond existing logged-in sessions (McMaster, DigiKey anonymous).