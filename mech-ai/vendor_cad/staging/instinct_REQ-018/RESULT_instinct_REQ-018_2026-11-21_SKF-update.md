STATUS: partial

# REQ-018: filament spool and feed path

Updated 2026-11-20 (second pass). Items 1-3 landed; item 4 remains open with named blocks. No payment, no new accounts; existing signed-in sessions only.

## Item 1: 1 kg spool with maker drawing/STEP — DONE (maker STEP landed)

Maker-published STEP found and saved:

- Prusa Research (official account @Prusa3D on Printables), "Dummy Prusament Spool for Makers" — a dimensioned dummy spool model Prusa publishes for designing accessories. Source page: https://www.printables.com/model/1648762-dummy-prusament-spool-for-makers
- Saved as prusament-dummy-spool__cad.step.zip (3.98 MB). The official STP is 25.4 MB, over the 9 MB folder limit, so it is stored zipped; inside, the file is named prusament-dummy-spool__cad.step and is the untouched official Prusa STP (STEP AP214, verified).
- No maker dimensioned drawing was found in the inspected sources (Prusa's download pack for this model contains only the STP, an STL, and a model info sheet PDF that is not a drawing; also inspected: Overture wiki/product pages, Polymaker product pages, eSUN pages). Absence beyond these inspected sources is not established.
- Text dims (not maker drawings, kept for reference): Overture official wiki — spool 200 mm outer dia x 65.6 mm width, hub diameter 55 mm, empty spool mass ~147 g (wiki.overture3d.com/en/Filament/PLA).

## Item 2: PTFE guide tube — research done

Capricorn XS (maker: Capricorn, captubes.com/specs.html):
- ID 1.90 ± 0.05 mm, OD 3.95 ± 0.05 mm (both as published on the maker's spec page).
- Minimum bend radius: not published on the inspected maker pages.
- US seller: RobotShop ("3D Printing Canada USA" storefront), Capricorn XS for 1.75 mm, $12.18 per 1 m length, 93 units in stock as displayed 2026-11-20. https://www.robotshop.com/products/3d-printing-canada-usa-capricorn-premium-ptfe-bowden-tubing-xs-series-for-175mm-1m
- Also sold cut-to-length (up to 5 m) at MatterHackers; price did not render in-session.
- Standard 4 mm OD / 2 mm ID alternative: Capricorn TL (ID 2.05 ± 0.05, OD 3.95 ± 0.05), same sources.

## Item 3: push-fit couplers for 4 mm PTFE — DONE

Roto bowden inlet thread — measured inference, compatibility UNCONFIRMED. Source: E3D's official Roto Bowden reference CAD (E3DOfficial on Printables, https://www.printables.com/model/655950-e3d-roto-reference-cad, file REVO-ROTO-COLDSIDE-BOW-AS.STEP, saved here as e3d-roto-bowden-reference-cad.step):

- The inlet is the Hemera bowdaptor (HEMERA-175-BOWDAPTOR-REFERENCE) screwed into the Roto heatsink. Measured from the CAD geometry: bowdaptor threaded-end cylinder dia 6.97 mm into the coaxial heatsink hole dia 7.36 mm.
- These two measurements are consistent with a possible M8 x 1.0 thread (whose internal pitch dia is 7.35 and external minor dia 6.92) and appear inconsistent with M10 x 1. The CAD models no thread helix and E3D publishes no thread spec in the inspected sources, so the pitch is inferred, not confirmed. Coupler compatibility with the Roto inlet is UNCONFIRMED without an authoritative thread spec or a physical fit check.
- No coupler below should be treated as confirmed to fit the Roto inlet.

Coupler picks — McMaster nickel-plated brass push-to-connect male adapters for 4 mm tube OD, each saved as <PN>__cad.step (official McMaster STEP AP214) + <PN>__datasheet.pdf (McMaster's published dimensioned drawing):

- 2333N197 — M5 x 0.8 mm male, $6.95 each. https://www.mcmaster.com/2333N197/
- 2333N202 — M6 x 1 mm male, $13.72 each. https://www.mcmaster.com/2333N202/
- 2333N211 — M8 x 1 mm male, $13.72 each. Candidate for the Roto bowden inlet only if the M8 x 1 inference above is confirmed; compatibility unconfirmed. https://www.mcmaster.com/2333N211/
- 2333N214 — M10 x 1 mm male, $11.98 each (generic M10 option; appears inconsistent with the measured Roto inlet geometry, inference unconfirmed). https://www.mcmaster.com/2333N214/

All four show "Delivers Monday by 5 pm" as displayed 2026-11-20. Thread/size of each verified on its McMaster product page title and drawing.

## Item 4: 608 bearing — OPEN (buy route captured; maker CAD blocked)

- Pick (unchanged): NSK 608ZZ via Misumi USA (real maker, REQ-named brand): $2.54 each, 560 in stock, ship date shown Sat. Nov 21, 2026. 8 mm ID x 22 mm OD x 7 mm W, basic dynamic load 3300 N, single row, steel, as displayed. https://us.misumi-ec.com/vona2/detail/221000058301/?HissuCode=608ZZ
- CAD blocks:
  - Misumi's CAD download returns "No CAD file is available for the specified conditions" for NSK 608ZZ; EZO (SPB-USA) 608 variants via Misumi are also CAD-unavailable.
  - SKF 608-2Z on skf.com (2026-11-20 ~8:00 PM update): SKF account created with owner approval (name + usual Gmail + owner-approved company/state fields; terms/privacy read, routine; mandatory consent checkbox was agreement to those same documents). SSO sign-in works and the product page loads signed in. However the CAD download did not complete: the CAD tab's viewer and download are served through a TraceParts iframe/widget, and the "CAD download" button stays at "Loading..." indefinitely after sign-in (fresh reload tried). Whether it requires a TraceParts account or the TraceParts widget is failing cannot be confirmed without registering TraceParts, which remains held (owner decision). The SKF-hosted "Download PDF" datasheet also did not fire in this browser session (no request, no tab, no download event); not retrieved.
  - 3dfindit (existing CADENAS account): retried 2026-11-20 ~3:47 PM after a footer-only first failure. The page shell loads and the account shows signed in (WP), but the API route the search page needs (service/searchtemplate/...) returns a Cloudflare-challenged 404, and content never renders - a bot-protection block on this session's API routes, not a render glitch (the same account worked 2026-11-19). Not retried further without a materially different verified route or a verified recovery signal.
  - McMaster 5972K222 ($18.46) has STEP + drawing but is McMaster's unbranded part, reference only, not the deliverable.
  - Other official maker CAD routes beyond the ones inspected above (Misumi, skf.com, 3dfindit, McMaster) were not checked; no other route within the owner's existing accounts is known. This is not a finding that no other maker CAD route exists.
  - Remaining decision: SKF account approval was granted and used; the SKF route now dead-ends at the TraceParts-served download widget, which never finishes loading. The loading failure does not establish that a TraceParts account would fix it - registration is held (owner decision) and is not a verified remedy. No scheduled retries remain, and no repeated attempts on blocked routes without new evidence. Work resumes on a materially different verified route or a verified recovery of 3dfindit/TraceParts delivery - a fresh REQ alone does not clear the 3dfindit bot block.

## Holds and compliance

Nothing purchased. No accounts created. All prices/stock/ship labels are quoted as displayed; dates in PST. The possible-M8 x 1 Roto-inlet reading is a geometric inference from E3D's published CAD, labeled as such; compatibility is unconfirmed and no design modification is proposed or approved.
