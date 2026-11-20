# RESULT — REQ-002: supplier CAD and datasheets, batch 3 (full list)
STATUS: partial (2026-11-19 ~6:50 PM PST). Research finished on 24 of 25 items (item 6 awaits PEM account approval). Requirements fully met on 11 of 25: items 4, 5, 8, 13, 14, 17, 20, 21, 22, 23, 25. Partial (datasheet/catalog delivered, required STEP/CAD or second candidate not obtained): 2, 7, 9, 10, 11, 15, 18, 19, 24. Blocked, routes exhausted (nothing delivered beyond documented negatives): 1, 3, 12, 16. Waiting on PEM approval: 6. Blocked-exhausted means the vendor blocks automated access and no permitted route remains - it is research finished, not fulfillment.

Naming: `<MPN>__<what>.<ext>`, files unchanged as downloaded. Prices are McMaster pack prices as shown, USD.

## 5. McMaster — DONE (all STEP AP214/ISO-10303-21 verified, drawing PDFs saved, signed into owner's account)
- M5x6 SHCS confirmed = 91290A221 ("Black-Oxide Alloy Steel Socket Head Screw, US Origin, M5 x 0.8, 6 mm", $13.96/pack): 91290A221__step.step, 91290A221__drawing.pdf
- M2x20 SHCS = 91290A049 ("M2 x 0.4, 20 mm", $16.58): 91290A049__step.step, 91290A049__drawing.pdf
- M2.5x20 SHCS = 91290A108 ("US Origin, M2.5 x 0.45, 20 mm", $10.88): 91290A108__step.step, 91290A108__drawing.pdf
- M3x25 SHCS = 91290A125 ("US Origin, M3 x 0.5, 25 mm", $17.78): 91290A125__step.step, 91290A125__drawing.pdf
- M5x16 SHCS = 91290A232 ("US Origin, M5 x 0.8, 16 mm", $17.27): 91290A232__step.step, 91290A232__drawing.pdf
- M5x65 SHCS = 91290A270 ("US Origin, M5 x 0.8, 65 mm", $8.73): 91290A270__step.step, 91290A270__drawing.pdf
- M2 hex nut = 90370A201 ("Medium-Strength Steel Thin-Profile Hex Nut, M2 x 0.4", $6.51): 90370A201__step.step, 90370A201__drawing.pdf. DESIGN DECISION: REQ said only "hex nut M2"; picked plain steel to match the steel fastener set (316 SS 93935A305 and brass 93187A115 also exist if preferred).
- M2 washer = 91166A180 ("Zinc-Plated Steel General Purpose Washer, for M2 Screw Size, 2.2 ID, 5.0 OD", $3.00): 91166A180__step.step, 91166A180__drawing.pdf. NOTE: REQ-001's oversized-washer family (91100A1xx) starts at M2.5, so general-purpose washer used for M2.
- M4x6 = 90128A208 drawing PDF: 90128A208__drawing.pdf (STEP also saved: 90128A208__step.step). NOTE: 90128A208 is zinc-plated alloy steel SHCS M4x6, $11.33; differs from REQ-001's 91290A139 (black-oxide US Origin M4x6) — both valid, different finish.
- Flanged BHCS M5x8/M5x10 (92137A412/92137A414) and M5 DIN 6797 J internal-tooth lock washer (93925A260/93925A420/91106A126): REQ-001 overlaps, already in REQ-001 results.

## 4. Gates 2MGT belt — DONE
- PowerGripGT2__design-manual.pdf — Gates PowerGrip GT2 Light Power & Precision design manual (official gates.com asset); verified it covers the 2MR (2 mm pitch GT2) belt family with 9 mm width data, tooth dimensions and ratings. The shorter GT2 brochure on the same page is image-only scans (unverifiable content) and was not uploaded.

## 9. Schurter — partial
- DD11 series datasheet (typ_DD11.pdf, covers DD11.0114.1111): DD11.0114.1111__datasheet.pdf — https://us.schurter.com/en/datasheet/typ_DD11.pdf
- Still blocked: DD11 STEP (schurter.com/cadstep returns HTML form); 4301.1401 / 0001.2513 / 0001.2511 datasheet+STEP. Retry via browser session.

## 10. JST — partial
- XH series datasheet eXH.pdf (covers XHP-3/4, B2B/B4B-XH-A, SXH-001T-P0.6): XH__datasheet.pdf — https://www.jst-mfg.com/product/pdf/eng/eXH.pdf
- XH STEP files still needed (JST 3D CAD pages).

## 14. Vishay — DONE: BAT85S__datasheet.pdf — https://www.vishay.com/docs/85513/bat85s.pdf

## 13. Littelfuse — DONE (via product-page datasheet links, fetched in owner browser session)
- 297 MINI 32V series: 297__datasheet.pdf — https://www.littelfuse.com/assetdocs/littelfuse-datasheet-297-mini32v?assetguid=42c9dd21-a88e-4328-8e67-2f832444faf1
- 218 series (0218008.MXP): 218__datasheet.pdf — https://www.littelfuse.com/assetdocs/fuse-218-datasheet?assetguid=a96d72b7-5296-4815-88b4-98b2f6738874
- NOTE: the REQ's bare assetdocs URL 404s; the current site serves these via assetguid links.

## 11. Molex — partial
- 43025-0200: 43025-0200__step.zip + 43025-0200__drawing.pdf (sales drawing) — molex.com part detail 430250200
- 43020-0200: 43020-0200__step.zip + 43020-0200__drawing.pdf — part detail 430200200
- 43030-0001: 43030-0001__drawing.pdf only; product page shows no 3D CAD link (STEP not offered at molex.com direct paths)
- 43031-0001: 43031-0001__drawing.pdf only; same — no CAD link on product page
- 39-01-2020: 39-01-2020__drawing.pdf only; same — no CAD link on product page
- 0457503111 (crimp terminal): neither drawing nor CAD link found on product page — NOT AVAILABLE at molex.com direct route; try TraceParts next

## 15. Finder — partial
- 22.32 datasheet: 22.32__datasheet.pdf — https://cdn.findernet.com/app/uploads/S22EN.pdf
- 22.32 STEP: 22.32__step.stp (extracted 0223x.stp from official series zip; ISO-10303-21 verified; full 173 MB zip not retained)
- BLOCKED-exhausted: IB2232EN-1 instructions PDF — official findernet.com CDN returns 403 to both curl and cloud browser. Unofficial mirrors host it; not uploaded (unofficial source).

## 17. Raspberry Pi — DONE
- Pi 5 mechanical drawing: RaspberryPi5__mechanical-drawing.pdf
- Active Cooler brief: PiActiveCooler__product-brief.pdf; 27W PSU brief: Pi27W-PSU__product-brief.pdf
- HQ Camera: PiHQCamera__product-brief.pdf, CS-mount + M12 mechanical drawings + schematics. NOTE: raspberrypi.com offers no STEP for the HQ Camera (drawings only).
- Camera Module 3: product brief, standard + wide mechanical drawings, official STEP zip (both variants, pip.raspberrypi.com design files), schematic, 200 mm cable drawing. (Files landed in this folder; they also serve REQ-003.)

## 18. Harwin — partial
- R30-6200614 datasheet: R30-6200614__datasheet.pdf — current content.harwin.com asset URL (the REQ's cdn.harwin.com URL now serves an HTML interstitial).
- Still needed: CAD for R30-6200614 (TraceParts), and the other R30-67005xx/6xx/8xx spacers.

## 19. RAF — partial
- RAF catalogue (spacer section): RAF__catalog.pdf — official cloudfront host
- Still needed: CAD for lengths nearest 5.5 / 6.1 / 9.725 / 13.2 / 40 mm + stock-length notes.

## 20. DONE
- igus CF880 chainflex cable datasheet: CF880__datasheet.pdf (via current widencdn signed preview URL from igus.com product page)
- Loctite 243 TDS: Loctite243__tds.pdf — datasheets.tdx.henkel.com (official Henkel)
- Panduit PLT1M-C cable tie: PLT1M-C__drawing.pdf + PLT1M-C__step.stp (official panduit.com resource)

## 23. Alcoa MIC-6 — DONE
- MIC-6__datasheet.pdf — Alcoa AMP 003 (MIC-6) brochure, hosted by distributor Howard Precision; PROVENANCE: no current official alcoa.com/arconic.com PDF for MIC-6 was found, this is the Alcoa-authored document via a distributor host.

## 21. Century Spring DJ-8X20YCS — DONE
- DJ-8X20YCS__drawing.pdf — two pages extracted from the official Century Spring 2021 catalog (centuryspring.com/catalog): (1) catalog p.460 "Spring Characteristics" with the chrome-alloy load-loss-vs-temperature chart, and (2) catalog p.475 JIS EXTRA LIGHT DUTY (YELLOW) spec table incl. the DJ-8X20Y row (hole 8 mm, rod 4 mm, free length 20 mm, rate 0.78 kgf/mm ≈ 7.6 N/mm; max oper. deflection 8.0 mm at 50% free length) plus dimensioned spring figure. Both pages visually verified.
- MAX TEMPERATURE: catalog p.460 states "The maximum rated service temperature for chrome-alloy steel is about 440° F" (≈227 °C). Product page lists material "Chrome Alloy", so this rating applies to DJ-8X20YCS.
- Product page facts (centuryspring.com/shop/dj-8x20ycs): $2.20 each; chrome alloy, yellow / JIS extra-light duty; closed ends. (Corrects an earlier partial note that said music wire / 0.8 N/mm — that was wrong.)

## 22. Accu HPLW-M3-A2 / HPLW-M4-A2 — DONE
- Owner approved creating a free Accu account (2026-11-19, via main). Account created as Will Patrick / wgpatrick@gmail.com (personal use, no marketing opt-in), email verified same day.
- HPLW-M3-A2__step.stp and HPLW-M4-A2__step.stp (ISO-10303-21 verified) — accu-components.com/us product pages 406212 / 406216, official CAD API. Note: Accu caps CAD downloads at 20/day; 19-20 remain today.

## Blocked-exhausted (site refuses automated access; labeled, no further retries)
- 1. StepperOnline 17E19S1684AB4-330RA datasheet: Cloudflare challenge loops on files.omc-stepperonline.com, including in the cloud browser (product page: omc-stepperonline.com product_id=5186)
- 12. TMC2209 datasheet: Akamai 403 on analog.com for both curl and cloud browser
- 16. Phoenix Contact 1119897: Akamai "Access Denied" on phoenixcontact.com, 2 bounded browser attempts
- 15. Finder IB2232EN-1 (see item 15 above)

## 25. Keenovo — DONE
- KeenovoCustomHeater__page.pdf — the REQ's URL (custom-silicone-heaters.html) 404s; the live page is https://www.keenovo.com/products/silicone-heater.html, saved via headless Chrome print-to-PDF and visually verified: full silicone rubber heater data sheet (structure, 0-400V, -50 to +260 C, max power density 2.5 W/sq.cm, standard thickness 1.5 mm). No quote requested.

## Not yet started
- 2. HIWIN MGNR12R300 / MGNR12R220 / MGN12H CAD (STEP) — MG catalogue delivered: HIWIN_MG__catalog.pdf (official hiwin.com linear guideway catalog, covers MGN12/MGN12H, verified 16 MGN12 mentions)
- 3. Misumi HBLFSN5 bracket; GPA20GT2090-B-P5 / -A-N5 pulley+idler (3dfindit route now EXHAUSTED — viewer hangs cloud-browser renderer; needs a different official route or retry after new signal)
- 6. PEM S-M3-1ZI + S-M3-0ZI: waiting on PEM account approval (registered 2026-11-19, review pending, activation email watched)
- 7. Omron D2F-01L: official datasheet DELIVERED (Omron_D2F-01L__datasheet.pdf, from omronfs.omron.com, covers D2F-01L). STEP still gated: Omron's own CAD library (aratas.com) is member-account only; TraceParts website needs an account; a TraceParts API key request was already submitted 2026-11-19 morning from Will's gmail and is pending validation, but NOTE (per main): a granted API key does not by itself establish CAD-download entitlement - that route is UNVERIFIED until the key arrives and its scope is checked; Digi-Key CAD tab works with Will's existing DigiKey vault login but presents a click-through CAD Model Agreement (as-is, internal-business-purposes-only use restriction, broad indemnification) - route BLOCKED by unapproved terms; left unaccepted, no acceptance question to the owner; CADENAS-family mirrors (3dfindit, partcommunity.com) hang the cloud-browser renderer - route exhausted, no retries.
- 24. PEI spring-steel kit research — PARTIAL (one of two products verified). Product 1 VERIFIED and pages saved as PDF: Wham Bam Systems (US, USD) — WhamBam_PEI-plate-220__page.pdf (Flexi Plate with Textured ULTEM PEI, 220 x 220, $35, 0.4 mm high-chromium spring steel, 0.12 mm ULTEM PEI per side; page shows Sold out as of 2026-11-19) + WhamBam_magnetic-base-220__page.pdf (matching Magnetic Base 220 x 220, 1 mm, 3M adhesive, rated 150 C continual use — exceeds the 120 C requirement; plate and base are separate SKUs at the same store). Product 2 NOT FOUND with a documented >=120 C magnet after checking: IdeaFormer (EXCLUDED — its own page states the magnetic bottom sheet is limited to 80 C), Kingroon / TwoTrees / Metaflex / Forgely (no magnet temperature stated), 3DJAKE (no 220 x 220 size; 120 C stated is max bed temp, not a magnet rating), Energetic (states 130 C magnet but is B2B inquiry-only, no retail price), Trianglelab (no 220 x 220 size). Next wake can try more vendors (e.g. Mandala Roseworks, Sparta3D, printer-universe stores) or accept documenting that the >=120 C magnet is a market rarity and Wham Bam is the find.

## Overlap note
- 8. Omron E2B-M12KS04-WP-C1: already delivered in REQ-001 results (overlap)
