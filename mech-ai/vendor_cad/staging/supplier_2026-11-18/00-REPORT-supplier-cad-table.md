# Supplier CAD — Nov 18 batch (final, v5)

Drive folder: https://drive.google.com/drive/folders/1YzqW0h4VMvjzZb2Gk-xAsHR37Rsqf4xI
Every delivered STEP validated: metric (millimetres), one part per file (or exactly the parts Will asked for in one file), under 5 MB, geometry checked against the description. Status values: DELIVERED (STEP+PDF, exact match, main folder), DELIVERED AS DEVIATION (real supplier part, differences stated, in the _DEVIATIONS-read-me-first subfolder), PDF ONLY, EXCEPTION (found but withheld per rules), NOT FOUND (checked-source limit, not an absolute claim).

## Folder layout

- Main folder: exact matches only.
- _DEVIATIONS-read-me-first/: every file whose part deviates from the request, so a requested filename never silently implies compliance: EXT2020-PROFILE, TNUT-2020-M3, TNUT-2020-M5, BRKT-2020 (all McMaster 5 mm-slot system, not true-2020 6 mm slot), GT2-20T-B5 + GT2-20T-B5-W9 (6 mm-belt pulley, see C), NUT-M5 (DIN 934 height 4.00 mm, below ISO 4032's 4.7 mm), SHCS-M4x6.pdf (zinc finish; compliant STEP withheld, over 5 MB cap), CTRL-OCTOPUS-V1.0.pdf (V1.0, not the requested V1.1).

## A. Fasteners — all McMaster-Carr, steel, black-oxide unless noted

| File | Status | Supplier PN | Description | Price | Differences / notes | Source |
|---|---|---|---|---|---|---|
| SHCS-M2.5x12 | DELIVERED | 91290A008 | SHCS M2.5x12, black-oxide alloy steel, DIN 912 / ISO 4762, fully threaded | $3.93/50 | — | https://www.mcmaster.com/91290A008/ |
| SHCS-M2.5x16 | DELIVERED | 91290A200 | same, M2.5x16 | $5.36/50 | — | https://www.mcmaster.com/91290A200/ |
| SHCS-M3x5 | DELIVERED | 91290A110 | same, M3x5 | $11.91/100 | — | https://www.mcmaster.com/91290A110/ |
| SHCS-M3x6 | DELIVERED | 91290A111 | same, M3x6 | $11.59/100 | — | https://www.mcmaster.com/91290A111/ |
| SHCS-M3x8 | DELIVERED | 91290A400 | same, M3x8 | $6.48/100 | — | https://www.mcmaster.com/91290A400/ |
| SHCS-M3x10 | DELIVERED | 91290A115 | same, M3x10 | $13.23/100 | — | https://www.mcmaster.com/91290A115/ |
| SHCS-M3x12 | DELIVERED | 91290A500 | same, M3x12 | $5.87/100 | — | https://www.mcmaster.com/91290A500/ |
| SHCS-M3x16 | DELIVERED | 91290A120 | same, M3x16 | $12.22/100 | — | https://www.mcmaster.com/91290A120/ |
| SHCS-M3x18 | DELIVERED | 91290A121 | same, M3x18 | $15.26/100 | — | https://www.mcmaster.com/91290A121/ |
| SHCS-M3x20 | DELIVERED | 91290A123 | same, M3x20 | $14.47/100 | — | https://www.mcmaster.com/91290A123/ |
| SHCS-M3x40 | DELIVERED | 91290A136 | same, M3x40 | $4.86/25 | partially threaded, 18 mm min thread (drawing callout; only way sold; spec allows) | https://www.mcmaster.com/91290A136/ |
| SHCS-M3x45 | DELIVERED | 91290A079 | same, M3x45 | $3.96/25 | partially threaded, 18 mm min thread (drawing callout) | https://www.mcmaster.com/91290A079/ |
| SHCS-M3x50 | DELIVERED | 91290A137 | same, M3x50 | $6.69/25 | partially threaded, 18 mm min thread (drawing callout) | https://www.mcmaster.com/91290A137/ |
| SHCS-M4x6 | PDF ONLY (in _DEVIATIONS) | 90128A208 | SHCS M4x6, zinc-plated alloy steel, DIN 912 / ISO 4762, fully threaded | $11.33/100 | EXCEPTION: zinc-plated (finish meets request; no black-oxide M4x6 exists at McMaster). STEP is ~9 MB — over the 5 MB cap, withheld. Drawing PDF delivered. | https://www.mcmaster.com/90128A208/ |
| SHCS-M5x8 | DELIVERED | 91290A222 | SHCS M5x8, black-oxide, fully threaded | $13.05/100 | — | https://www.mcmaster.com/91290A222/ |
| SHCS-M5x10 | DELIVERED | 91290A224 | M5x10 | $14.23/100 | — | https://www.mcmaster.com/91290A224/ |
| SHCS-M5x12 | DELIVERED | 91290A228 | M5x12 | $16.36/100 | — | https://www.mcmaster.com/91290A228/ |
| SHCS-M5x30 | DELIVERED | 91290A194 | M5x30 | $4.59/10 | fully threaded — VERIFIED from the McMaster product-page Threading spec ("Fully Threaded") | https://www.mcmaster.com/91290A194/ |
| SHCS-M5x35 | DELIVERED | 91290A195 | M5x35 | $6.00/10 | fully threaded — VERIFIED from the product-page Threading spec | https://www.mcmaster.com/91290A195/ |
| SHCS-M5x70 | DELIVERED | 91290A201 | M5x70 | $2.22 each | fully threaded — VERIFIED from the product-page Threading spec | https://www.mcmaster.com/91290A201/ |
| FHCS-M4x40 | DELIVERED | 91294A204 | Flat-head socket screw M4x40, DIN 7991 / ISO 10642, fully threaded | $12.85/50 | — | https://www.mcmaster.com/91294A204/ |
| WASHER-M2.5 | DELIVERED | 91166A190 | Flat washer M2.5, DIN 125 / ISO 7089 | $3.09/100 | — | https://www.mcmaster.com/91166A190/ |
| WASHER-M3 | DELIVERED | 91166A210 | M3 | $2.97/100 | — | https://www.mcmaster.com/91166A210/ |
| WASHER-M4 | DELIVERED | 91166A230 | M4 | $3.13/100 | — | https://www.mcmaster.com/91166A230/ |
| WASHER-M5 | DELIVERED | 91166A240 | M5 | $3.09/100 | — | https://www.mcmaster.com/91166A240/ |
| WASHER-M3-LARGE | NOT FOUND | — | 9 mm OD fender washer, steel | — | McMaster carries no metric steel oversized washer with 9 mm OD (checked their metric oversized-washer tables). Checked-source limit. | https://www.mcmaster.com/products/washers/ |
| WASHER-M4-LARGE | NOT FOUND | — | 12 mm OD fender washer, steel | — | same | https://www.mcmaster.com/products/washers/ |
| NUT-M2.5 | DELIVERED | 90591A270 | Hex nut M2.5, DIN 934 | $3.03/100 | Supplied to DIN 934. Cross-reference (manufacturer Dresselhaus, URL below): DIN 934 is superseded by DIN EN ISO 4032; for M2.5 the nut height is unchanged (drawing shows 2.00 mm), so dimensions coincide. | https://www.mcmaster.com/90591A270/ ; cross-ref https://eshop.dresselhaus.de/en/Standardisation-overview/DIN-934-%3E-DIN-EN-ISO-4032.html |
| NUT-M3 | DELIVERED | 90591A250 | M3 | $3.06/100 | Supplied to DIN 934; height unchanged in ISO 4032 at M3 (drawing 2.40 mm), dimensions coincide. Same cross-ref. | https://www.mcmaster.com/90591A250/ |
| NUT-M4 | DELIVERED | 90591A255 | M4 | $3.39/100 | Supplied to DIN 934; height unchanged in ISO 4032 at M4 (drawing 3.20 mm), dimensions coincide. Same cross-ref. | https://www.mcmaster.com/90591A255/ |
| NUT-M5 | DELIVERED AS DEVIATION (in _DEVIATIONS) | 90591A260 | M5 | $3.88/100 | Supplied to DIN 934. Per the Dresselhaus cross-reference, ISO 4032 INCREASED nut heights for M5-M39, so ISO 4032 equivalence does NOT hold at M5: delivered nut is 4.00 mm high (DIN 934 value), ISO 4032 M5 is 4.7 mm. DIN 934 as supplied; deviation from ISO 4032 stated. | https://www.mcmaster.com/90591A260/ |
| NUT-M3-NYLOC | DELIVERED | 90576A102 | Nylon-insert lock nut M3, DIN 985 / ISO 10511 | $4.88/100 | — | https://www.mcmaster.com/90576A102/ |
| THUMBNUT-DIN466-M4 | NOT FOUND (account needed) | KIPP K0143.04 | DIN 466 tall knurled nut M4, steel | not shown | Real current part identified: KIPP K0143.04 (current number; legacy K0151.104). CAD exists in Kipp's CADENAS portal (3D preview works); download requires a free 3dfindit/CADENAS account. The download route is a free 3dfindit/CADENAS account; none exists, and an agent-side registration attempt failed because the 3dfindit registration page/postback hangs the browser tab (site issue; no retries without a new signal). With any working CADENAS account this is a plain CAD download; no other input is missing. | https://www.kippusa.com/us/en/Product%20family%20Nuts%20Washers%20Screws%20Miscellaneous/Standard%20parts%20K0151/p/agid.540 ; CAD portal https://kipp-embedded-v2.partcommunity.com/3d-cad-models/k0143-knurled-nuts-high-steel-or-stainless-steel-din-466 |

## B. T-slot hardware — all McMaster-Carr (all in _DEVIATIONS)

| File | Status | Supplier PN | Description | Price | Differences / notes | Source |
|---|---|---|---|---|---|---|
| EXT2020-PROFILE | DELIVERED AS DEVIATION | 5537T101-5537T044 | 20x20 mm T-slot extrusion, 1/2 ft | $3.75 | DEVIATION: McMaster's metric rail has a 5 mm slot, not the standard-2020 6 mm slot. Delivered as closest real system, never as a compliant 6 mm match. Cross-section drawing included. | https://www.mcmaster.com/5537T101/ |
| TNUT-2020-M3 | DELIVERED AS DEVIATION | 5278N42 | Drop-in self-aligning spring-ball T-nut, M3 | $5.09/4 | front-loading (drop-in, no end slide) verified against request; sized for the 5 mm-slot rail above | https://www.mcmaster.com/5278N42/ |
| TNUT-2020-M5 | DELIVERED AS DEVIATION | 5278N44 | same, M5 | $5.09/4 | same | https://www.mcmaster.com/5278N44/ |
| BRKT-2020 | DELIVERED AS DEVIATION | 5537T935 | Corner bracket for 20 mm rail, fasteners included | $6.44 | drawing verified: 2X M5 holes (one per leg), for 20 mm rail height; same 5 mm-slot system | https://www.mcmaster.com/5537T935/ |

## C. Motion

| File | Status | Supplier | PN | Description | Price | Differences / notes | Source |
|---|---|---|---|---|---|---|---|
| MGN12H | NOT FOUND (login) | HIWIN | MGN12H | linear guide block | — | HIWIN CAD sits behind member login at hiwinsupport.com. Saved account login attempted 3x with captcha solved; postback hangs and returns to the login form (sign_in_failed reported). Community fallback assessed: models exist (e.g. https://grabcad.com/library/hiwin-mgn-12h-linear-guide-1 , https://www.printables.com/model/1527120-mgn12h-linear-rail-model-for-cad ) but were not used — official CAD does exist, so "nothing else exists" does not hold; one working hiwinsupport login unlocks it. | https://www.hiwinsupport.com/cad_download |
| MGN12-R-250 | NOT FOUND (login) | HIWIN | MGNR12R 250 mm | rail | — | same | https://www.hiwinsupport.com/cad_download |
| MGN12-R-300 | NOT FOUND (login) | HIWIN | MGNR12R 300 mm | rail | — | same | https://www.hiwinsupport.com/cad_download |
| NEMA17-LEADSCREW | NOT FOUND (blocked) | StepperOnline | 17E19S1684AB4-330RA | NEMA17, Tr8x2 330 mm integral screw, 1.68 A, anti-backlash nut included | $46.30 | No STEP offered for this part (Downloads tab lists only the datasheet PDF). Datasheet PDF itself is Cloudflare-blocked on every route tried (browser download, in-page fetch, curl, mirrors). Ships WITH anti-backlash nut (POM), not a plain flanged brass nut. Stock lengths: this exact Tr8x2 1.68 A family = 330 mm only; 0.4 A sibling = 300/330 mm (17E19S0406AB2-300RA/-330RA); lead-8 mm sibling = 200/300 mm (17E19S1684MB4-200RS/-300RS). | https://www.omc-stepperonline.com/anti-backlash-screw-nut-nema-17-external-48mm-stack-1-68a-lead-2mm-0-07874-length-330mm-17e19s1684ab4-330ra |
| T8-NUT | NOT FOUND | — | — | flanged brass nut for Tr8x2 | — | The named motor ships with an anti-backlash nut (see above); no standalone supplier CAD found for a brass Tr8x2 nut at StepperOnline. | https://www.omc-stepperonline.com/lead-screw-nut/ |
| GT2-20T-B5 | DELIVERED AS DEVIATION (in _DEVIATIONS) | ServoCity | 3422-0005-0020 | GT2 pinion pulley, 20 teeth, 5 mm bore, set-screw, steel flange + aluminum body | $7.99 | DEVIATION: built for 6 mm belt (tooth section 7 mm), not the requested 12 mm. Tooth count and 5 mm bore are exact. Supplier STEP (2.8 MB, mm) + supplier dimensioned schematic PDF delivered. Other suppliers assessed: SDP/SI closest is A 6D51M020DF0605 (6 mm belt, Fairloc) or A 6A51M020DF0904/0906 (9 mm belt but 4/6 mm bore); Gates 2MR-20S-12 is 12 mm belt but minimum-plain-bore only (not 5 mm as sold); McMaster does not stock GT2; Misumi route terminal (signup failure, prior batch). ServoCity chosen: bore is the hard constraint and its CAD is public. | https://www.servocity.com/2mm-pitch-gt2-pinion-timing-pulley-5mm-bore-20-tooth/ |
| GT2-20T-B5-W9 | DELIVERED AS DEVIATION (in _DEVIATIONS) | ServoCity | 3422-0005-0020 | same part as above | $7.99 | DEVIATION: 6 mm belt vs requested 9 mm; tooth count and bore exact. Alternative: SDP/SI A 6A51M020DF0904 (9 mm belt, 4 mm bore) or ...0906 (6 mm bore) — belt exact but bore off; CAD only behind the cad.sdpsi.com account portal. | https://www.servocity.com/2mm-pitch-gt2-pinion-timing-pulley-5mm-bore-20-tooth/ |
| GT2-IDLER-20T-B5 | NOT FOUND | — | — | toothed idler w/ bearings, 20T, 5 mm bore, 12 mm belt | — | No supplier CAD exists for a toothed 20T 5 mm-bore bearing idler at any checked supplier: SDP/SI idler line is inch-bore needle-bearing only; ServoCity idlers are smooth/shielded (3427-0002-0001, 6 mm belt) or dual-bearing smooth 4/6/8 mm bore (3428-0019-xxxx); Gates sells no 2MR idlers; Misumi route terminal. Community fallback assessed: toothed-idler models exist (e.g. https://ink.parts/pulley/GT2-IDLER-TOOTHED-20T-B5-W6 , https://xemstudio.com/objects/gt2-idler-pulleys-toothed-smooth/ ) but are 6 mm-belt and community-authored; not used pending Will's call, since supplier parts do exist but without CAD. | — |
| GT2-IDLER-20T-B5-W9 | NOT FOUND | — | — | same, 9 mm belt | — | same | — |

## D. Toolhead

| File | Status | Supplier | PN | Description | Price | Differences / notes | Source |
|---|---|---|---|---|---|---|---|
| PROBE-OMRON-E2E-X5ME1 | DELIVERED | Omron | E2E-X5ME1 | M12 inductive sensor, pre-wired | not shown | STEP is Omron's own (their CAD download portal); contains base + both mounting nuts as requested; datasheet PDF also delivered | https://download.ia.omron.com/download/page/E2E_X5ME1/OEI/E2E_X5ME1 |
| FAN-3010-CG3010U24 | NOT FOUND (specs captured) | Coolerguys | CG3010U24 | 30x30x10 mm, 24 V, dual ball | $6.45 | Maker offers no CAD and no PDF datasheet. Specs from product page: 13,400 RPM, 0.07 A, 31.5 dBA, 5.45 CFM, 8.01 mmH2O, 67k h life, 2-wire 4 in. | https://coolerguys.com/products/coolerguys-30mm-30x30x10mm-24v-dc-2pin-ultra-high-speed-fan-cg3010u24-with-4-inch-wire-length |
| BLOWER-4010-24V | PDF ONLY | GDSTIME | GDB4010 (A-Type) | 40x40x10 radial blower, 24 V | ~$4-8 (resellers) | No CAD offered by maker. MAKER DATASHEET DELIVERED as PDF (2 pages, converted from the maker's own two spec images): page 1 is the maker's spec table covering GDB4010 at 3/5/12/24 V (24 V section: 9500 RPM, 0.08 A, 0.52 in H2O, 35 dBA); page 2 is the P-Q curve + dimension drawing (40 mm overall envelope with a 35 mm subdimension, 10 mm thick). Bearing: the maker's table says only generic "Hydraulic/Ball" — DUAL-BALL CONSTRUCTION IS UNVERIFIED; a west3d reseller listing says sleeve bearing, which conflicts and is unresolved. | https://www.gdstime.com/list_45/138.html |

## E. Bed

| File | Status | Supplier | PN | Description | Price | Differences / notes | Source |
|---|---|---|---|---|---|---|---|
| SPRING-DIE-DJ-8X20YCS | DELIVERED | Century Spring | DJ-8X20YCS | die spring, JIS extra-light, 20 mm free length, fits 8 mm hole / 4 mm rod, 7.6 N/mm | not shown | STEP generated by Century's own CAD configurator (metric verified: 20.0 mm free length, ~8 mm measured OD on the model). Supplier 2D drawing PDF delivered with load/deflection table. The 8 mm / 4 mm figures are the JIS CLEARANCE hole/rod designations (the maker's series table lists them as nominal outer/inner dia columns); the ACTUAL spring OD/ID are not published separately — unknown. Solid height: not published on the product page or in the series catalog tables — unknown. Temperature limit: not published for this exact product — unknown (a sister brand's catalog rating was found but is not transferred here for lack of applicability evidence). | https://www.centuryspring.com/shop/dj-8x20ycs ; series data https://www.asraymond.com/globalassets/catalogs/raymond-die-spring-catalog2.pdf |
| SHEET-PEI-235 | NOT FOUND (part picked) | Creality | Black PEI Magnetic Flexible Steel Plate 235x235x0.4 mm | PEI spring-steel sheet + magnetic base | $43.66 | No maker named, so this real currently-sold part is the pick: Creality 235x235, spring steel 0.4 mm + PEI coating, magnetic base included. Magnetic base thickness: NOT PUBLISHED by Creality on the checked product page — unknown (one third-party retailer lists an overall 235x235x1.2 mm envelope, unverified, so not relied on). No maker CAD/datasheet exists for a flat sheet. | https://creality3dglobal.com/product/creality-black-pei-magnetic-flexible-steel-plate-2352350-4mm |

## F. Electronics

| File | Status | Supplier | PN | Description | Price | Differences / notes | Source |
|---|---|---|---|---|---|---|---|
| CTRL-OCTOPUS-V1.1 | PDF ONLY, V1.0 (in _DEVIATIONS) | BIGTREETECH | Octopus | control board | — | EXCEPTION: BTT's GitHub publishes CAD only for V1.0 (24 MB STEP — over cap AND wrong revision; V1.1 CAD does not exist there). V1.0 drawing PDF delivered, clearly named CTRL-OCTOPUS-V1.0 so it cannot pass as V1.1. | https://github.com/bigtreetech/BIGTREETECH-OCTOPUS-V1.0 |
| RELAY-BTT-V1.2 | PDF ONLY | BIGTREETECH | Relay V1.2 | relay module | — | no CAD in BTT repo; official manual PDF delivered | https://github.com/bigtreetech/BTT-Relay-V1.2 |
| HOST-RPI-ZERO-2W | PDF ONLY | Raspberry Pi | Zero 2 W | SBC | — | official mechanical drawing PDF delivered; Raspberry Pi publishes no official STEP (community STEPs exist, not used) | https://www.raspberrypi.com/documentation/computers/raspberry-pi.html |
| INLET-C14-SW-FUSE | DELIVERED | Schurter | DD11.0121.1110 (CAD model 0100.2571) | IEC C14 inlet + 2-pole switch + 1 fuse holder | not shown | screw-mount version chosen (snap-in is the KM variant); maker STEP 3.0 MB metric validated (27x46x38 mm envelope); datasheet PDF delivered | https://www.schurter.com/en/datasheet/DD11 |
| ENDSTOP-MICRO | PDF ONLY | Omron | D2F (D2F-01L) | lever microswitch | — | Omron CAD library has no D2F model (0 results; only unrelated SC/STC items). Bare-switch datasheet PDF delivered; no endstop-board CAD found. | https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf |

## Sites that needed a login or blocked the download

- hiwinsupport.com — member login for all CAD; saved account + captcha attempted 3x, login never sticks (sign_in_failed reported). TRUE BLOCKER.
- 3dfindit.com / kipp-embedded-v2.partcommunity.com — Kipp CAD downloads need a free CADENAS/3dfindit account; none on file; self-registration attempted but the registration page hangs the browser tab on every route tried. TRUE BLOCKER pending either a working account or a successful registration retry.
- cad.sdpsi.com — SDP/SI CAD portal (account); also unreachable via the browser's network route.
- 8020.net — CAD gated behind 3DContentCentral form + captcha.
- files.omc-stepperonline.com — Cloudflare blocks the datasheet download on every route tried.
- centuryspring.com — WORKED: no account needed, configurator generated STEP + drawing PDF.
- mcmaster.com, schurter.com, download.ia.omron.com, gdstime.com, coolerguys.com, creality3dglobal.com, servocity.com — WORKED (McMaster with saved login).

## Counts (verified against the live Drive folder listings this run)

- Files supplied for 43 of 56 requested filenames, counting deviations and PDF-only coverage: 38 filenames with STEP+PDF (29 fasteners, 4 T-slot, 2 GT2 pulleys, Schurter inlet, Omron probe, Century spring — of which the 4 T-slot, 2 GT2 and NUT-M5 pairs are labeled deviations) and 5 PDF-only with stated reasons (SHCS-M4x6 exception, Relay V1.2, Pi Zero 2W, D2F endstop, GDSTIME blower datasheet). The wrong-revision CTRL-OCTOPUS-V1.0.pdf supplies no requested filename — it is a labeled deviation/exception only.
- Files in Drive: 83 total = 67 in the main folder (66 content files + this report) + 16 in _DEVIATIONS-read-me-first/. Verified by folder listing.
- Withheld exceptions: SHCS-M4x6 STEP (9 MB over cap; PDF delivered), Octopus V1.0 STEP (24 MB, wrong revision; V1.0 PDF delivered under its own name).
- No community models used anywhere; the two cases where they could apply (HIWIN, GT2 idlers) are listed above with sources and reasons.
