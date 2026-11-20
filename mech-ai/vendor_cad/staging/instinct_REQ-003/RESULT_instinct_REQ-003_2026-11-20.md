# RESULT — REQ-003

## STATUS: PARTIAL
Research finished on 9 of 10 items (item 10 waits on PEM account approval). Requirements fully met on 5 of 10.
DONE (requirements met): items 3, 5, 7, 8, 9.
PARTIAL (research finished, requirement not fully met): items 1, 2, 6.
BLOCKED: item 4. WAITING (dependency): item 10.

Prepared by Instinct for Will. Prices as seen Nov 19, 2026 (USD unless noted); verify at order time.
Naming: `<MPN>__<what>.<ext>`; official vendor/brand sources only.

| # | Part | Result |
|---|------|--------|
| 1 | 24V silicone bed heater ~200x200, 180-220W, stock | PARTIAL — 1 stock candidate fully documented (2-3 requested); search negatives documented |
| 2 | Magnetic PEI kit 220x220, base ≥100°C (ideally 120°C), 2 candidates | PARTIAL — 1 candidate fully verified, base rating OK; second not found |
| 3 | Gates GT2 9mm belt, roll/cut ≥3m, part no. + datasheet | DONE |
| 4 | Misumi GT2 pulley+idler 9mm, 20T, 5mm bore | BLOCKED (CAD routes exhausted; see REQ-002 item 3) |
| 5 | ADXL345 accelerometer board (e.g. Adafruit 1231 / BTT V2.0) | DONE (2 candidates) |
| 6 | USB nozzle camera, 2 candidates w/ dimensioned drawings | PARTIAL — candidates + drawings delivered; 20-40mm close focus UNVERIFIED |
| 7 | Pi Camera Module 3 + Pi 5 camera cable | DONE — delivered under REQ-002 item 17 |
| 8 | 24V COB LED strip high-CRI + alu channel w/ drawings | DONE |
| 9 | DIN rail 35mm + end stops, drawing/STEP | DONE (WAGO equivalents, dimensioned drawings; no STEP - see notes) |
| 10 | PEM S-M3-0 self-clinching nut | WAITING — PEM account pending manual approval (see REQ-001/002 item 6) |

## Item 1 — PARTIAL (research finished)
- Candidate 1: **Keenovo standard square silicone heater, 200mm x 200mm, 200W, 24V** — exact spec match, stock product, **$43.28, available** at keenovo.store (maker direct, live variant data Nov 19). Maker states 3M adhesive backing and includes a free NTC 100K thermistor (Beta 3950). Also stock: 220x220 200W 24V with cut corners ($54.38). Delivered: `Keenovo_200x200-24V-200W__page.pdf` (product page) + `Keenovo_NTC-Thermistor-R-T-Table.pdf` (official Keenovo R-T table).
- Requirement gap: the request asked for 2-3 candidates from real makers; bounded search found no other maker selling a stock (non-custom) 24V ~200x200 pad with a datasheet. Omega SRFG (real maker datasheet platform) stocks only 120/240V mains parts; 24V is custom/quote-only. Most 24V pads this size are no-name 3D-printer-market parts without maker documentation. So: 1 candidate, alternates exhausted.

## Item 2 — PARTIAL (research finished)
**Wham Bam PEX Flexi Plate set 220x220** (candidate 1 of 2 requested).
- Delivered under REQ-002 item 24 (that folder): plate page PDF + magnet base page PDF.
- Plate: $35.00 (currently **SOLD OUT** at whambam3d.com). 0.4mm spring steel, 0.12mm ULTEM PEI per side, double-sided, 220x220.
- Magnetic base: 1.0mm, 3M 468MP adhesive, **rated 150°C continual use** (vendor FAQ) — exceeds the ≥100°C / ideal 120°C requirement.
- Second candidate: not found meeting all constraints (see REQ-002 item 24 negatives: 8 vendors checked). Wham Bam is the sole verified candidate; spec match is strong but it is sold out.

## Item 3 — DONE
- Part number: **Gates LL2MR09** (Long-Length PowerGrip GT2: LL prefix + 2MR pitch + 09 = 9mm width; designation convention in the Gates design manual p.59, delivered under REQ-002 item 4). Gates product ID **9396-0052**.
- Source with price: **VBeltSupply.com — $5.98 per foot, in stock**, sold open-ended by the foot, minimum 50ft / maximum 300ft (50ft = 15.24m, satisfies ≥3m), store requires $300 minimum in Gates items (50ft x $5.98 = $299, so a Gates order is effectively ~$300). Second listing seen at MROSupply ($ per unit unstated) and RS Mexico ($5.46, region-specific) — not verified further.
- Delivered: `Gates_LL2MR09__page.pdf` (product page, visually verified). Datasheet: Gates PowerGrip GT2 design manual (REQ-002 folder).
- Note: an earlier draft of this file referenced LL2MR06 (6mm) in error; the 6mm page file has been removed. 9mm is the requested width.

## Item 4 — BLOCKED
Misumi GT2 pulley + idler (9mm belt, 20T, 5mm bore): CAD download routes exhausted (3Dfindit/partcommunity CADENAS family blocks automation; Misumi CAD tab needs a Misumi account, which is not approved). See REQ-002 item 3. The REQ's suggested 3Dfindit/CADENAS route is exactly the blocked one. No further permitted routes.

## Item 5 — DONE (both candidates)
**Candidate 1: BIGTREETECH ADXL345 V2.0.1 USB accelerometer** — native USB, Klipper input-shaping ready.
- Seller: biqu.equipment (BTT's official store), variant ADXL345 V2.0.1, **$9.25, InStock**.
- Delivered: `BTT-ADXL345-V2.0__step.zip` (6.0MB; full board STEP from official github.com/bigtreetech/ADXL345, ISO-10303-21 verified), `BTT-ADXL345-V2.0__drawing.pdf` (official SIZE drawing: PCB 28.25 x 15.50mm, 2x Ø2.50 mounting holes 20.50 x 15.50mm pattern), `BTT-ADXL345-V2.0__manual.pdf` (official 13-page manual, wiring + Klipper config).
- Note: repo files labeled V2.0; current retail variant is V2.0.1 (same board, minor revision).
**Candidate 2: Adafruit #1231** ADXL345 breakout (I2C/SPI, STEMMA QT/Qwiic), **$17.50, in stock** at adafruit.com.
- Delivered: `Adafruit_ADXL345-1231__page.pdf` (product page with price, visually verified) + `Adafruit_ADXL345-1231__datasheet.pdf` (official Analog Devices ADXL345 data sheet, hosted on Adafruit's cdn-learn). No official STEP exists for #1231 (not in Adafruit's CAD Parts repo); no substitute generated per sourcing rules.
- Suggestion: BTT V2.0.1 (native USB, Klipper plug-and-play, cheaper, full STEP available). Adafruit only if a bare SPI/I2C breakout is preferred.

## Item 6 — PARTIAL (2 candidates + official dimensioned datasheets delivered; close-focus requirement UNVERIFIED)
Both are Arducam USB2 UVC modules (plug-and-play, no driver), 38x38mm boards, M12 lens mounts.
- Candidate 1: **Arducam B0454** — 5MP OV5648, 1080p30, wide low-distortion M12 lens (95°H FOV), 38x38mm board (28x28mm hole pitch), from **$38.99** at uctronics.com (Arducam's official store; Add to Cart shown, explicit stock status not stated). Delivered: `Arducam_B0454__datasheet.pdf` (official, Overall Dimension Diagram + Lens Diagram) + `Arducam_B0454__page.pdf` (visually verified).
- Candidate 2: **Arducam B0506** — 1080p OV2710 day/night, manual-focus M12 lens, onboard 850nm IR LEDs with automatic IR-cut, 105°(D) FOV, 38x38mm board, **$34.99** at uctronics.com (Add to Cart shown). Delivered: `Arducam_B0506__datasheet.pdf` (official, Board + Lens Dimension Diagrams) + `Arducam_B0506__page.pdf` (visually verified).
- **Close focus UNVERIFIED**: the request asks for manual/fixed focus usable at 20-40mm working distance. Neither maker spec supports that: B0506's official datasheet states default focus range 2m-infinity, and neither maker publishes a minimum focus distance after M12 lens adjustment. M12 lenses are commonly refocused to close distances in practice, but that is not maker-specified here, so 20-40mm focus is unproven for both candidates pending physical test or a maker statement.
- **Lighting distinction**: B0506's onboard 850nm IR LEDs are infrared illumination (only usable with IR-cut off, night-vision-style image) — NOT a substitute for the visible task lighting in item 8. B0454 has no LEDs. Item 8's visible strip remains needed for either candidate.
- No official STEP for either board; dimensioned maker drawings delivered (request allows drawings/CAD). No recommendation given the unverified close-focus requirement.

## Item 7 — DONE
Already delivered under REQ-002 item 17 (Pi Camera Module 3 standard + wide mechanical drawings, product brief, schematic, STEP; Pi 5 camera cable drawing). See REQ-002 folder.

## Item 8 — DONE
Single-maker matched set from **Inspired LED** (sold at Digi-Key; Digi-Key PN 1647-24V-COB-4000K-12M for the 12m reel; digikey.com blocks automated access from this environment, so Digi-Key price/stock unverified — maker-direct pricing verified instead):
- Strip: **24V COB Flex, 480 LED/m, Pure White 4000K, CRI 91**, 3.15W/ft, 8mm wide, cut points every 1.97in. Maker direct: $6.00/ft custom-cut ($0.62/in + $6.00 cut fee), available. Delivered: `InspiredLED_24V-COB__datasheet.pdf` (official spec with dimensions + power table) + `InspiredLED_24V-COB__page.pdf`.
- Channel: **Radiant Edge Series Channel & Lens Set (SKU 8492, short 3/8in)** — aluminum channel 72 x 0.84 x 0.14in (fits the 8mm strip), polycarbonate diffuser lens, end caps + clips included, **$50.00, in stock** maker direct. Delivered: `InspiredLED_RadiantEdge-short__datasheet.pdf` (official dimensioned spec) + `InspiredLED_RadiantEdge__page.pdf`.
- Visible task lighting per the camera requirement (distinct from any IR illumination, see item 6).

## Item 9 — DONE
WAGO equivalents of the Phoenix NS 35/7.5 rail + end clamps (both Digi-Key listed; phoenixcontact.com blocks automation, per standing block):
- Rail: **WAGO 210-112** — steel carrier rail 35 x 7.5mm, EN 60715 top-hat, slotted, 2m (cut to length). **Digi-Key currently shows it out of stock/backorder** (the listing offers an in-stock direct substitute; Newark stocks 210-112). Delivered: `WAGO_210-112__datasheet.pdf` (official, dimensioned drawing incl. hole pattern, visually verified) + `WAGO_210-112__page.pdf`.
- End stop: **WAGO 249-117** — screwless, 10mm wide, snap-on, fits DIN 35x7.5 and 35x15. Also stocked at MISUMI. Delivered: `WAGO_249-117__datasheet.pdf` (official, dimensioned, visually verified) + `WAGO_249-117__page.pdf`.
- STEP: WAGO's CAD downloads route through CADENAS (blocked family), so no STEP; the official dimensioned drawings in the datasheets satisfy the drawing/STEP requirement. Digi-Key price/stock for both: verify at order time.

## Item 10 — WAITING
PEM S-M3-0: PEM catalog account (registered as Will) pending PEM's manual review; the REQ's suggested 3Dfindit/CADENAS fallback is the blocked family. Files deliver automatically on approval (see REQ-001/002 item 6). PEM is a watched dependency, not a fulfilled requirement.
