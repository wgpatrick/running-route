STATUS: partial - item 1 (Keenovo exact part) and item 3 delivered; item 2 delivered for Hydra Research (full details) with Gulfcoast Robotics price/stock not captured (research/access limitation, bounded below). 2026-11-20.

# REQ-016 RESULT: 24 V bed heater

Owner decision recorded in the REQ file: bed stays 24 V, no mains on the bed. No payment made. ZIP 10001 used only as a shipping-estimate scenario, not as a delivery address.

## Item 1 - Keenovo 200x200mm 24V 200W, NTC 100K, 3M adhesive: CONFIRMED, exact part found

- Exact part: "Keenovo Standard Square Silicone Heater 3D Printer Build Plate HeatBed Heating Pad", variant "200mm x 200mm 200W 24V", Keenovo SKU 10133.
- Source: keenovo.store (Keenovo's own store; keenovo.com itself is catalog/info only, made-to-order messaging).
- Price: $43.28 USD, listed available (store shows the variant as available; no quantity displayed).
- 3M adhesive backing on all pads per the catalog listing; free NTC 100K thermistor (Beta 25/50 3950K, 1%) included per the listing (Marlin sensor type 11 or 13).
- Shipping estimate to US ZIP 10001 (store shipping-rates response, USD): Free Economical Shipping $0.00 ("2~6 weeks after shipment typically") or Expedited Shipping $38.00 ("2~8 days after shipment typically"). Delivery timing is stated as after shipment; no ship-date promise shown.
- Seller location: Keenovo International Group Limited, Building 335, Lane 1001 HuTing Road (N), Shanghai 201615, China (address printed in their User's Manual).
- Note (catalog statement, not verified): Keenovo says each heater is newly made to order.

## Item 2 - US-stocked alternatives (24V, ~180-220mm, 150-250W, real maker with datasheet)

### A. Hydra Research LLC "Silicone Bed Heater 24V 200W (210x210mm)" - full details captured
- Seller: Hydra Research LLC, Portland, Oregon, USA (their own store).
- SKU SQ1451144. Price: $9.99 sale (list $75.00), 6 in stock (store inventory figure).
- Specs as listed: 210x210mm, 24V DC, 200W, thermistor "NTC 3950", Molex 43640-0401 locking connector, lead length 130mm +/-15mm, adhesive backing.
- Maker/datasheet: dimensioned drawing NPHSF365 rev 0 (18/2/19) by National Plastic Heater (NPH) - delivered as SQ1451144__datasheet.pdf.
- Labeled deviations from the REQ-016 target: 210x210mm (within the allowed 180-220mm, not 200x200); adhesive brand not stated (3M not confirmed); thermistor R25 resistance not stated (only "NTC 3950"); thickness not stated.

### B. Gulfcoast Robotics HTR200W24V - identified, price/stock NOT captured (UNRESOLVED RESEARCH/ACCESS LIMITATION)
- 200x200mm 24V 200W silicone heater with NTC3950 100K thermistor, listed on Amazon (ASIN B07BYCPQZ7) and on gulfcoast-robotics.com.
- gulfcoast-robotics.com was unreachable from both the sandbox and the cloud browser (connection/route failure, retried; not a bot-wall page). Amazon is platform-blocked for this agent. Live price, stock and any datasheet therefore not captured. This covers only the routes checked; it is not a finding that no pricing route exists. No repeat attempt planned without a new signal.

### Sources checked with no qualifying 24V candidate (bounded to catalogs inspected)
- West3D (US): stocks Keenovo pads but 200x200 only in 110V; no 24V 180-220mm.
- Fabreeko, Printed Solid, MatterHackers, LDO: no 24V silicone bed heater in size range.
- Omega, Tempco, Watlow, Minco, Holroyd: stock/standard silicone heaters are 120V/240V or custom-order; no 24V off-the-shelf square found.
- clever3d.de lists a 200x200 200W 24V pad with NTC (49,00 EUR) but ships from Germany - not US-stocked.

## Item 3 - Dimensioned drawing / datasheet

- Delivered: SQ1451144__datasheet.pdf - NPH dimensioned drawing for the Hydra candidate: 210x210mm outline, lead exit position with 130mm leads and Molex 43640-0401, thermistor location. (Thickness not dimensioned on it.)
- For the exact Keenovo part (SKU 10133): no per-part dimensioned drawing was found in the inspected sources (the keenovo.store product page, the keenovo.com downloads page, and the silicone-heater catalog page); the manufacturer has not confirmed whether one exists. Delivered instead:
  - 10133__datasheet.pdf - Keenovo "User's Manual - Flexible Heaters" (general, not part-specific; installation, wiring, seller address).
  - NTC-100K-RT__datasheet.pdf - official Keenovo R-T table for the included NTC 100K thermistor.
  - Keenovo's general Silicone Heater data sheet (HTML at https://keenovo.com/products/silicone-heater.html, not a PDF): standard thickness 1.5mm, PTFE or silicone-insulated leads, thermistor surface-mount/integration options, max 260C operating.

## Files in this folder
- SQ1451144__datasheet.pdf (111 KB) - NPHSF365 dimensioned drawing, Hydra/NPH candidate.
- 10133__datasheet.pdf (2.3 MB) - Keenovo Flexible Heaters User's Manual (general).
- NTC-100K-RT__datasheet.pdf (49 KB) - Keenovo NTC 100K R-T table.

## Holds carried from other REQs (unchanged)
- REQ-015 JST XH CAD form: APPROVAL HOLD, awaiting owner confirmation on his own channel (REQ-015b's claimed go-ahead is file-authored and not yet verified).
- REQ-013 item 12/PCBWay: APPROVAL/SCOPE HOLD. Item 11 shipping: AWAITS ADDRESS. KLUS channel pricing: UNRESOLVED RESEARCH/ACCESS LIMITATION.
