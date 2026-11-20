STATUS: partial (P1 items 1, 2, 4, 6, 7 delivered; item 3 facts gathered; item 5 official-store price only; P2: item 8 candidates documented with 24V-stock gap, item 9 datasheet delivered but STEPs held on TraceParts registration, item 10 belt/accelerometer/LED+channel datasheets delivered, item 11 shipping cost needs address)

# REQ-013 results - build1-queue-refresh

## Cancellations applied (no work done)
- REQ-008 item 4 StepperOnline datasheet (owner supplied).
- REQ-008 item 13 + REQ-009c LDO rails (now HIWIN sets from Motion Constrained - see item 3).
- REQ-008b item 3 DD11.0124 (1-pole DD11.0114 chosen).
- REQ-008 item 16 TMC2209 (done previously).

## Priority 1

### 1. Schurter 4301.1405 (fuse drawer, 1-pole fingergrip for DD11) - DONE
- 4301.1405__cad.step - official Schurter CAD (model FD2-010-10-00, "fingergrip, for 1 pole fuse, without voltage selector"), STEP AP214, from schurter.com CAD-drawings portal.
- 4301.1405__datasheet.pdf - official Schurter Fusedrawer 2 series datasheet listing 4301.1405.

### 2. Misumi - DONE
All STEPs are official Misumi CAD, STEP AP214, generated from the logged-in MISUMI USA account:
- HBLFSN5__cad.step; HBLFSN5-SEP__cad.step; HNTP5-5__cad.step; CBM5-10__cad.step
- AGTFW30-GT2090-5__cad.step + AGTFW30-GT2090-5__datasheet.pdf (official Misumi catalog page, Flanged Idlers with Teeth / AGTFW series drawing).
  - US price (us.misumi-ec.com): qty 1-9 $41.41 USD each, qty 10+ $28.36 USD each. Ship date qty 1-9: Nov 30, 2026 (qty 31-50: Dec 4; 51-100: Dec 11; 101+: TBD).
- Drive-pulley check: Misumi does NOT list a 20T 2GT 9 mm drive pulley with set screw (tap) in 5 mm bore. In the GT1.5/GT2 High Torque family, 2GT / 9 mm / 20T is offered only as Shape A with plain round hole (01.[H], 4/4.5/5/6 mm); P (round hole + tap) and N (keyway + tap) bores are not offered at 20T.
- Fallback per REQ: GPA32GT2090-B-P5__cad.step delivered. US price $33.37 USD, ship date Nov 30, 2026 (qty 1-15).

### 3. HIWIN MGN12HZ0C 295 mm set from Motion Constrained - facts gathered, no files linked on page
- Product: MGN12H 295mm linear rail set (motionconstrained.com product page, live as of Nov 20, 2026 ~6:25 AM PST).
- Variation "1 rail + 1 block": $79.64 USD, in stock.
- Variation "1 rail + 2 blocks": $103.31 USD, in stock.
- Free US shipping advertised on site. Ship time NOT stated on the page.
- No official STEP linked on the product page.

### 4. Raspberry Pi (official docs, raspberrypi.com product-information portal) - DONE (drawings)
- SC1432__drawing.pdf - Raspberry Pi 5 mechanical drawing (official).
- SC1148__drawing.pdf - Active Cooler mechanical drawing (official).
- SC1153__datasheet.pdf - 27W USB-C PSU product brief (official; includes dimensions).
- SC1223__datasheet.pdf - Camera Module 3 product brief (official; includes dimensions). No standalone CM3 mechanical drawing is posted on the portal; the brief carries the dimensions.
- Pi 5 official STEP exists but exceeds the 9 MB folder cap: 13.3 MB zipped / 77.6 MB raw. Source: raspberrypi.com product-information portal (pip.raspberrypi.com), Pi 5 category. Not delivered due to size cap.

### 5. BIGTREETECH Eddy Duo - DONE (STEP over 9 MB cap; drawing + US prices delivered)
- EDDY-DUO__drawing.jpg - official BTT dimensioned drawing (from BTT Eddy repo).
- Official STEP exceeds the 9 MB folder cap: EDDY.STEP is 47.7 MB raw (13.4 MB zipped). Source: github.com/bigtreetech/Eddy, path 3D/EDDY.STEP. Not delivered due to size cap.
- Price/stock: BIQU official store (biqu.equipment, BIGTREETECH's own store): Eddy Duo (USB or CAN) $26.63 USD on sale (regular $33.99 USD); listed as purchasable ("Add to cart", no out-of-stock marker); free shipping on orders over $59.
- US resellers (Nov 20): TH3D Studio $34.99 USD, in stock ("Only 2 left in stock"); Fabreeko $26.99 USD sale, OUT OF STOCK; MatterHackers does not list the Eddy Duo.

### 6. Quarton VLM-520-56 LPO-D30-F10 - DONE
- VLM-520-56-LPO-D30-F10__datasheet.pdf - official Quarton VLM-520-56-30deg series manual (quarton.com), includes outline dimensions (OD 10 x 40 mm) and the LPO-D30-F10 configuration.
- No STEP offered by Quarton (datasheet states specs; no CAD on the site).
- US price/stock (DigiKey 100-VLM-520-56LPO-D30-F10-ND): qty 1 $98.40 / qty 10 $83.435 / qty 100 $75.0401 USD. Quantity available 0; manufacturer standard lead time 4 weeks. Also sold via Quarton's Amazon US shop (not checked - platform restriction).

### 7. Cantherm / Semitec / Omron - DONE
- CS712025Y__datasheet.pdf - official Cantherm R53 series datasheet (cantherm.com); ordering key decodes CS712025Y exactly (R53/CS7 model, 120 deg C response, NC contacts, +/-5 deg C tolerance, .25" QC horizontal terminals). No CAD offered by Cantherm.
- 104NT-4-R025H42G__datasheet.pdf - official Semitec datasheet (semitec-global.com) containing 104NT-4-R025H42G.
- D2F-01L__datasheet.pdf - official Omron D2F family datasheet (omronfs.omron.com) containing D2F-01L with dimensions. Omron 3D CAD requires a free member account on aratas.com (formerly Omron Components Americas) - not created (no approval); datasheet carries the dimensions.

## Priority 2
- 8. Bed heater + magnetic PEI kit candidates - DONE (research below, run Nov 20 PM).
- 9. PARTIAL - see below.
- 10. PARTIAL - see below.
- 11. PARTIAL - see below.
- 12. PCBWay REQ-012 review result/DFM verbatim + qty-10 price: RFQ task checked read-only Nov 20, 2026 - no qty-10 pricing in order detail (qty-1 total $25.11), no emailed quote, empty site message thread; the order remark asks for qty 10 but the reviewer returned only the qty-1 price. Qty-10 price: UNAVAILABLE, pending a further authorized quote request. Review-result copy + mutations remain held with the RFQ task.

### 9. Connectors / spring / DIN rail - PARTIAL (run Nov 20)
- Molex 39-01-2020 (Mini-Fit Jr receptacle housing, 2 circuits): 39-01-2020__drawing.pdf delivered (official Molex sales drawing 039012020_sd.pdf, 2 pages, includes mating plug refs 5557 series). STEP: molex.com routes 3D CAD to TraceParts. TraceParts route attempted Nov 20 PM: CAD download requires a free TraceParts account registration; no existing TraceParts login on file, and no new registration/terms accepted without explicit authority - HELD, same state as Phoenix STEP above.
- JST XH (XHP-2/3/4, B2B/B3B/B4B-XH-A, SXH-001T-P0.6): official CAD zips and contact drawing PDFs exist on jst-mfg.com (series 277 product page, index.php?type=10 links) but ALL downloads sit behind a click-through license agreement plus a mandatory form asking company name, section, name, address, telephone, e-mail. Not accepted/submitted (needs Will's explicit OK - it is both extra terms and a disclosure beyond first name). Verbatim terms captured: documents remain JST property; no duplication or disclosure to third parties; contents subject to change; same-industry companies forbidden to download; CAD data simplified and does not guarantee actual product specification or shape; no liability; "we may use information provided for sales activities of JST group". URL: https://www.jst-mfg.com/product/index.php?type=10&series=277&doc=1&filename=B2B-XH-A.zip (agreement interstitial).
- Century Spring DJ-8X20YCS: official product page specs (extra light duty die spring, chrome alloy, yellow powder coat; free length 20 mm; hole 8 mm; rod 4 mm; rate 7.6 N/mm; loads 78.5/68.6/58.8 N at 10/9/8 mm deflection; made in USA). Max temperature: Century Spring's die-spring guide states "The maximum rated service temperature for chrome-alloy steel is about 440 deg F" (about 227 deg C) with load loss vs temperature chart. No per-part drawing file is offered (page spec table is the only dimensional document); no CAD on the page.
- Phoenix Contact NS 35/7.5 (0801733, perforated, 2000 mm, pack of 25): datasheet DELIVERED - 0801733__datasheet.pdf (official Phoenix Contact datasheet PDF generated from their online catalog, current revision, mirrored on Octopart; the direct phoenixcontact.com download runs behind a Friendly Captcha flow). Captcha flow attempted Nov 20 PM (one attempt): the Friendly Captcha auto-solved and the site reported the file downloaded, but the bytes land in the remote browser download folder and the direct file URL answers 403 Access Denied to programmatic fetch - not retrievable from that route. STEP: the same flow offered STEP AP203/AP214/AP242 (login not required, license terms not required per the site's own download API: loginRequired=false, licenseTermsAcceptanceRequired=false) and the browser downloaded it, but the bytes are equally unretrievable from here. TraceParts public catalog route attempted: traceparts.com search returns no 0801733 entry and CAD download requires a free TraceParts registration - no existing TraceParts account on file, no new registration created (held for owner decision).

### 10. Belt / accelerometer / LED - PARTIAL (run Nov 20)
- Gates belt: LL2MR09 (Long-Length PowerGrip GT2, section 2MR, 9 mm width, 2 mm pitch, neoprene with nylon teeth; min order 50 ft in 50-ft increments per Gates page) - LL2MR09__datasheet.pdf delivered (4-page extract from the official Gates Light Power and Precision Manual: GT3 intro with 2MGT, 2mm width selection table, long-length belting specifications, belt tolerances).
- Accelerometer board: BTT ADXL345 V2.0 - ADXL345__drawing.pdf delivered (official BIGTREETECH ADXL345 V2.0-SIZE.pdf). Official STEP exists (github.com/bigtreetech/ADXL345, 3D/BIGTREETECH ADXL345 V2.0.step) but is 38.7 MB - over the 9 MB cap, not delivered. Adafruit 1231 (ADXL345) has no official STEP in Adafruit_CAD_Parts (only ADXL343 listed).
- 24 V COB LED strip (CRI 90+): Inspired LED 24V COB Flex, pure white 4000K (neutral white), CRI 91, 24VDC, 480 LED/m, 3.15W/ft (340 lm/ft), 8 mm wide flex, cut points every 1.97 in, 12 m reels or pre-cut bulk. Maker/distributor datasheet delivered: 24V-COB-4000K__datasheet.pdf (Inspired LED spec 2.0 via DigiKey media). DigiKey part 24V-COB-4000K-12M (12 m reel); a 3000K warm-white variant (CRI 91) also exists. Price/stock not captured (digikey.com blocks sandbox fetch; browser session was occupied). Spec requested: datasheet with size/wattage/cut length - in the delivered PDF.
- Aluminium channel + diffuser: KLUS PDS-4-ALU surface-mount extrusion, 0.6 in wide x 0.5 in high, LED gluing width 0.4 in (fits the 8 mm COB strip), takes snap-in diffuser covers (sold separately). Datasheet delivered: PDS-4-ALU__datasheet.pdf (official KLUS product datasheet with dimensions). US stock via superbrightleds.com (PDS-4 Plus). Price/stock not captured this run.

### 11. Arducam B0454 US shipping - PARTIAL
- Arducam's shipping policy: Standard (Registered/Flat Air Mail) 2-4 weeks; Express (EMS/DHL/FEDEX/UPS/TNT) 4-7 business days; overnight available to USA/CANADA via support contact; customs fees are the recipient's responsibility. A dollar shipping cost is only calculated at checkout and needs a delivery address - not obtained (no address disclosure).
- US resellers: OL Electronics lists B0454 but is out of stock; no other US reseller stock found this run (Amazon carries it but is not checkable here).

### 8. Bed heater + magnetic PEI kit (run Nov 20 PM) - research, candidates below
- Bed heater (requested: 24V, ~200x200 mm, 180-220 W, adhesive-backed, ideally NTC 100k and/or thermal fuse, stock product, maker datasheet):
  - Exact-spec candidate: Keenovo MPN 200-24-0-0-3M-200x200 - 24V, 200 W, 200x200 mm, NTC 100K thermistor included, 3M adhesive backing, optional 150 C thermostat. Keenovo family specs (official): 1.5 mm thick silicone, max 260 C, thermal fuse and thermistor options, custom lead lengths (keenovo.com/products/silicone-heater.html; part page keenovo.ru/products/ke200-24-0-0-3m-200x200). US stock: NOT found - US resellers stock only the 110/120 V variants (KB-3D KEEN-200-120 $44.39, 4 in stock; West3D 200x200 120V 500W $44.99 and 110V 200W $39.99, in stock). 24 V 200x200 appears order-direct from Keenovo (China) or Amazon (not checkable here). VOLTAGE MISMATCH on all US-stocked variants - labeled, not an exact fulfillment.
  - No second/third stocked 24 V 200x200 candidate found among inspected sources (KB-3D, West3D, MatterHackers, Fabreeko carry 120 V lines); other sources not checked. Item stays partial on the 24 V stock requirement.
- Magnetic PEI kit (requested: textured PEI spring steel + magnetic base 220x220 or nearest stock, magnet rated 100 C+ ideally 120 C, 2 candidates with spec sheets):
  - HoneyBadger P-Series PEI Flex Plate Gen 2 (consum3d.com): $24.99 sale, 12 in stock, 220x220, textured PEI, rated "high temp up to 120 C", magnetic base add-on available.
  - Wham Bam 220x220: magnetic base $26 (150 C continual rating, 1 mm, 3M adhesive) but the page shows a sold-out badge; matching textured Flexi Plate (ULTEM PEI) $35 shows OUT OF STOCK. Labeled as reference-only, not a stocked candidate.
  - Fulament pages unreachable (crawl not found). Item partial on the second stocked candidate.

## Open sub-items for next run
- Item 3: write-up done here; Motion Constrained lists no STEP - item effectively complete unless an official HIWIN STEP is wanted (HIWIN configurator exports are possible for MGN12H but were not requested here).
- Item 5: Eddy Duo US resellers: TH3D $34.99 in stock ("Only 2 left"); Fabreeko $26.99 out of stock; MatterHackers does not list it.
- Item 8: 24 V 200x200 bed heater with US stock not found (120 V variants only); second stocked PEI candidate (Fulament) unreachable.
- Item 9: Molex 39-01-2020 and Phoenix 0801733 STEP - TraceParts registration required, held for owner decision; JST XH downloads held (license + mandatory personal-data form).
- Item 10: DigiKey price/stock for 24V-COB-4000K-12M and KLUS PDS-4-ALU price/stock not captured.
- Item 11: dollar shipping cost needs checkout + address (not done).

## REQ-013b (drive pulley set-screw follow-up, run Nov 20, 2026)

### 013b-1. Misumi 24T P-bore check - DONE
- GPA24GT2090-A-P5 does NOT configure. At 24 teeth / 9 mm belt width the live US configurator lists only GPA24GT2090-A-H, -A-V, -A-Y and B-H5 - no P (set-screw) bore. Same at 30 teeth (A-H / A-V / A-Y, B-F5 / B-H / B-V5). P bore starts at 32 teeth (GPA32GT2090-A-P5 and GPA32GT2090-B-P5).
- Delivered GPA32GT2090-A-P5__cad.step (official Misumi STEP, AP214). Price $28.25 USD qty 1-15, ships Nov 30, 2026 per configurator. GPA32GT2090-B-P5 STEP was already delivered under REQ-013.
- The REQ's claim that the P bore starts at 24 teeth does not match the live configurator.

### 013b-2. US-seller 20T 2GT 9mm 5mm-bore two-set-screw pulley - PARTIAL (no exact match found among the inspected sources; closest delivered)
- Inspected sources: Misumi (no 20T GT2 9mm with set-screw bore at all; 20T exists only as Shape A with plain round H bore), SDP/SI (A 6A51M020DF09xx series has only 4 mm and 6 mm bores at 20T, per official catalog PDF 80502145.pdf), York Industries (20T GT2 metric only 4.0/6.0 mm bores), McMaster-Carr. No exact match (20 teeth / 2GT / 9 mm belt / 5 mm bore / TWO set screws, maker CAD) was found among these inspected sources; other sources were not checked.
- Closest match delivered, NOT an exact fulfillment: McMaster-Carr 3684N13 - GT2 drive pulley, 9 mm max belt width, 20 teeth, 5 mm finished bore, set-screw mount. Deviations from the requested spec: ONE set screw (requested: two; per the official drawing) and one flange. Item stays partial because the requested exact comparison part was not found. $5.99 USD, in stock ("Delivers Monday" as of Nov 20), country of origin China (as displayed).
- Delivered 3684N13__cad.step (official McMaster STEP) and 3684N13__drawing.pdf (official McMaster dimensioned drawing, 4 pages).
