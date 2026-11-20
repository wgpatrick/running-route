STATUS: partial

# REQ-010 results — nozzle camera files

Nothing purchased. Prices captured 2026-11-19 (US sites, USD). CAD = official vendor files only.
Close-focus requirement (20-40mm nozzle distance) is checked per candidate below, from official sources only.

## 1. Arducam B045401 (5MP HDR UVC, M12-S, 32x32mm board)

- CLOSE FOCUS: FAILS the 20-40mm requirement. The maker's own spec table (uctronics.com product data for sku B045401 / A5648S) lists Focus Type "Fixed Focus", Default Focus Range "300cm-infinity". This is official and explicit.
- STEP: NOT OBTAINED. The REQ's URL (https://download.arducam.com/3D-Drawing/B045401.STEP) returns 404; no directory listing is available, and no alternate official STEP for B045401 was found (checked name variants and Digi-Key Documents & Media, which lists only the datasheet).
- Datasheet: B045401__datasheet.pdf in this folder. Note on provenance: Arducam publishes no B045401-specific datasheet; this is the maker's B0454-family datasheet, byte-identical to the file Digi-Key hosts as the B045401 datasheet. B045401-specific specs (HDR sensor A5648S, fixed focus, 32x32x1.6mm board, metal enclosure, 0-70C) come from the maker's product data on uctronics.com.
- Dimensioned drawing: NOT OBTAINED as a separate document. The B0454-family datasheet contains a dimensioned board drawing, but for the 38x38mm B0454 board, not the 32x32mm B045401 with metal enclosure.
- US sellers with stock and price:
  - Digi-Key 4679-B045401-ND: $62.41 qty 1 (breaks $57.65 @5, $55.88 @10, $53.75 @25, $52.30 @50, $50.97 @100), In-Stock: 0 (matches the REQ's note), Manufacturer Standard Lead Time 2 weeks. Digi-Key's listed attributes say "OV5648, 3264x2448", which conflicts with the maker's A5648S/2592x1944 spec; the maker data should win.
  - UCTRONICS (maker's own store): B045401 appears as the "Upgraded Module" style option of the B0454 listing; a standalone US price was not isolated. Amazon listing exists but Amazon is not accessible from Instinct's browser right now, so price/stock there is unverified.

## 2. Arducam B0454 (fallback, 5MP OV5648 UVC, M12, 38x38mm board)

- CLOSE FOCUS: UNVERIFIED. The maker datasheet does not state a focusing range. The maker's short description says "Manual Focus: the removable M12 lens allows you to manually adjust the focus", so close focus can likely be achieved by turning the lens, but no official minimum focus distance is published. Stated as unverified rather than assumed.
- Files in this folder:
  - B0454__cad.zip - official STEP from https://download.arducam.com/3D-Drawing/B0454.STEP (verified AP214). Zipped because the raw STEP is 9.23 MB, over the 9 MB folder limit; zip is 1.78 MB.
  - B0454__datasheet.pdf - official 9-page datasheet (includes board dimension diagram 38x38mm, hole pitch 28x28mm, lens diagram). MJPG 30fps at 1920x1080 and 1280x720, so 720p+ is met.
- UCTRONICS product page: price $38.99 (+$1.00 for the "Standard Module" style; $39.99 in cart). Ships from: not stated on the product page; the store's shipping policy describes international CFR shipping with duties/taxes unpaid by the seller, i.e. not US-stocked. Shipping cost to the US: NOT OBTAINED - the cart's estimate form (US / CA / 94110) returned no rates, and guest checkout bounces to a login form, so a shipping quote requires an account. Account creation was not approved, so I stopped there.

## 3. DFRobot FIT0819 (3-in-1 waterproof USB endoscope inspection camera)

- No maker datasheet or drawing exists; DFRobot's product page (dfrobot.com/product-2328.html) is the only maker document. Its published specs: 8mm lens diameter, 1200P, 70 deg viewing angle, USB + micro-USB + Type-C, 5m cable, IP67.
- Temperature rating: NOT PUBLISHED on the maker page. The Farnell/Newark route suggested in the REQ is bot-blocked from both the sandbox and the cloud browser (403), so the Farnell PDF could not be checked.
- Focal distance / close focus: NOT PUBLISHED on the maker page. Endoscope cameras of this type are built for close work, but with no official number the 20-40mm capability is UNVERIFIED.

## 4. Commonlands CIL062-F4.0-M12A650 (6mm no-distortion M12 lens)

- STEP: NOT OFFERED. The product page (commonlands.com "Rectilinear 6mm M12 Lens | CIL062") has the mechanical drawing (which we already have) but no STEP/3D model link; a second lens page and a site search confirm Commonlands does not publish STEP files.
- Stock/price while there: CIL062-F4.0-M12A650 in stock at $19.00 (maker direct).

## 5. Other USB UVC M12 boards (named maker, datasheet, 720p+, <=32mm board, in stock at US seller)

Checked Digi-Key's in-stock USB-UVC M12 listings and Arducam's official UVC selection guide (docs.arducam.com):

- Arducam B0292 (8MP IMX219 autofocus, M12): the only Arducam with an official short minimum focus - its datasheet states "Focusing Range: 40mm to infinity". But its board is 38x38mm (over 32mm) and Digi-Key (4679-B0292-ND, $56.35) shows In-Stock: 0. Official datasheet saved here as B0292__datasheet.pdf. Meets the spirit of close focus only at the 40mm edge (20mm not covered).
- Arducam B0196 / B0197 (stock lens, official 40mm-to-infinity per the selection guide): not M12 (fixed stock lens) and not carried by Digi-Key; US stock unverified.
- Arducam B0203 (M12, 32x32mm board per the selection guide): official focusing range 1M to infinity - fails close focus.
- Camemake CM_USB2 series (Digi-Key marketplace, in stock 168-1,600 pcs, $52.58-$65.18): boards are 38x38mm, 55x19mm, or 80x28mm - none is <=32mm.
- Verdict: no board found that satisfies all four REQ criteria AND has official 20-40mm focus. The closest on focus (B0292) fails board size and stock; the closest on size (B045401) fails focus outright.

## Files in this folder

- B0454__cad.zip - official Arducam STEP (zipped to fit the 9 MB limit)
- B0454__datasheet.pdf - official Arducam datasheet with dimensioned drawing
- B045401__datasheet.pdf - maker's family datasheet as listed by Digi-Key under B045401 (same bytes as the B0454 file; no B045401-specific datasheet exists)
- B0292__datasheet.pdf - official Arducam autofocus datasheet (40mm-to-infinity focus, for the close-focus comparison)

## Gaps / blocked

- B045401 STEP and B045401-specific dimensioned drawing: not published at the REQ's URL (404) or anywhere else official found.
- B0454 US shipping cost: not quoted without a UCTRONICS account (not approved to create).
- FIT0819 temperature rating and focal distance: not published by the maker; Farnell/Newark PDF route bot-blocked.
- Amazon seller listings for both Arducam SKUs: unverified (Amazon inaccessible to Instinct's browser at the moment).
