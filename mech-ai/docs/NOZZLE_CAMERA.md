# Nozzle camera: a real, orderable close-focus camera for the bead at the nozzle (2026-11-20)

Question: which real camera, lens and light should the v12 nozzle-camera bracket carry? It sits on the part-cooling
duct, 20-40 mm from the nozzle tip and outside the heater plume, and feeds the Raspberry Pi 5. ROADMAP priority 3, phase 2:
a labelled nozzle-camera dataset, then a CAXTON-style model. The CAXTON-style research captured 1280x720 at about 2.5 Hz.

Owner's rule (docs/DESIGN_GUIDELINES.md, key rule): a named maker, the maker's part number, the maker's datasheet, and the
maker's CAD or a dimensioned drawing. Prefer US sellers. A part from abroad is allowed only when its shipping cost is low,
and the doc must state that cost.

Sources: distributor APIs through `mechloop/sourcing` (Digi-Key, Mouser, Newark, Farnell; live on 2026-11-20 and cached
in `out/sourcing_cache/`), maker documents saved in `vendor_docs/`, and maker pages this session could reach. From this
session, raspberrypi.com, mm.digikey.com and raw.githubusercontent.com were reachable. The proxy refused arducam.com,
download.arducam.com, docs.arducam.com, uctronics.com, dfrobot.com, camemake.eu, commonlands.com, edmundoptics.com,
elpcctv.com, webcamerausb.com, mouser.com and farnell.com. Section 6 lists what the owner's browser agent must fetch from
them. Prices are in USD for quantity 1, before shipping and tax.

## 1. What the camera must do

| Need | Value | Why |
|---|---|---|
| Focus | 20-40 mm object distance (design point: lens front 30 mm from the nozzle tip) | Bracket on the duct, outside the plume |
| Field of view at the nozzle | about 10-20 mm across, or a wider frame that is cropped to about 320 px around the tip (as CAXTON did) | A 0.4-0.5 mm bead must span at least ~10 px; ~20-30 px is better |
| Depth of field | about 1-2 mm or more | The tip and the first few mm of bead should both be sharp |
| Resolution / rate | 1280x720 or better; 2.5 Hz is enough (every candidate below does 720p at 30 fps MJPG) | Research setup |
| Interface | USB UVC (preferred: a round cable flexes on the moving toolhead better than a CSI ribbon); CSI with a long flex is the second choice | Pi 5 has 2 x CSI + USB |
| Board size | ideally <= 30 x 30 mm | Toolhead space and mass |
| Temperature | as high as possible; ambient at the bracket is maybe 50-70 °C | Near the hot block |
| Light | built-in LEDs or a separate small LED | The bead is in the shadow of the nozzle |

## 2. How the numbers were worked

- **Field of view (FOV)** across the frame at object distance u, for sensor width w and focal length f:
  the simple estimate is `w x u / f`, and the thin-lens value is `w x (u - f) / f`. The simple estimate is larger; the
  thin-lens value is closer to the real one at macro distances. Both are given. u is measured from the lens's principal plane,
  which sits a few mm behind the barrel front. With the lens front at 30 mm, the effective u is therefore about 33-37 mm.
  Read the "30 mm" columns as the closest case. The FOV is a little wider in practice.
- **Close-focus extension**: an M12 lens set to infinity must screw out by `f^2 / (u - f)` to focus at u. For example,
  6.2 mm needs 1.6 mm, 8 mm needs 2.9 mm and 12 mm needs 8 mm. M12 holders normally give a few mm of travel, so
  **focal lengths of 8 mm and under are practical. 12 mm and longer are not** without a spacer.
- **Depth of field (DoF)**: `2 N c (1 + m) / m^2`, where m = f / (u - f), N is the f-number and c = 2 sensor pixels at
  720p (sensor width / 1280 x 2). This leads to the key trade: **a narrower FOV gives more pixels on the bead but less DoF**.
  At the same FOV, a smaller sensor or a higher f-number gives more DoF. M12 lenses have a fixed aperture, so DoF is set
  by choosing the lens, not by stopping it down.
- Sensor widths used: OV5648 1/4" (Arducam B0454) 2592 x 1.4 µm = 3.63 mm. Arducam B045401, 1/2.8" with 2 µm pixels:
  2592 x 2.0 µm = 5.18 mm. OV2710 1/2.7" (Arducam B0506): 1920 x 3 µm = 5.76 mm. If the 720p mode crops the sensor
  instead of scaling it, the FOV is narrower than shown. Check this on the bench.
- Endoscope modules state only an angle (diagonal FOV assumed). Their width at 30 mm is `2 x 30 x tan(HFOV/2)`, with the
  HFOV taken from the diagonal angle for a 16:9 frame.

Scratch scripts: `fov.py`, `kw.py`, `det.py`, `fnd.py` in the session scratchpad. They are not part of the repo.

## 3. Comparison

Stock is the live distributor answer on 2026-11-20. "MP" means a Digi-Key Marketplace listing (shipped by the maker,
not from Digi-Key's warehouse).

### 3a. Camera boards and modules

| Maker | MPN | Sensor | Resolution / fps (720p) | Lens and focus | FOV at 30 mm | Interface | Board size | Operating temp. | LEDs | Price | US seller / stock | Datasheet / drawing / CAD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Arducam | **B045401** (upgraded B0454) | 5 MP, 1/2.8", 2 µm (UCTRONICS page; Digi-Key lists "OV5648", which conflicts with 1/2.8" and 2 µm) | 2592x1944@30; **1280x720@30 MJPG**; HDR | M12x0.5, stock 2.7 mm F2.8 fixed focus, "300 cm-∞" as shipped, distortion < -1 %; set closer by turning the lens | stock lens: 57.6 simple / 52.4 thin-lens (crop 320 px ≈ 13 mm) | USB 2.0 UVC, JST B4B-ZR | **32 x 32 x 1.6 mm**, metal enclosure | 0 to 70 °C | none | $62.41 | Digi-Key 4679-B045401-ND: **0 in stock**, maker lead 2 weeks | Spec table on the UCTRONICS page (`vendor_docs/Arducam_B0454_page_2026-11-20.pdf`, B045401 column). Its own datasheet, drawing and STEP were not reached: Digi-Key's datasheet link serves the B0454 PDF |
| Arducam | **B0454** (B0454-1) | OV5648 1/4", 1.4 µm | 1280x720@30 MJPG (YUY2 10 fps) | M12x0.5, stock 2.1 mm F2.5, FOV 95° H, distortion < 20 % | stock lens: 51.9 simple (≈ 65 by the 95° angle; crop 320 px ≈ 16 mm) | USB 2.0 UVC, JST B4B-ZR, 1 m cable | **38 x 38 x 1.6 mm**, holes 28 x 28 | **-20 to +70 °C** (datasheet); 0 to 70 °C on the UCTRONICS page | none | "as low as $38.99" (UCTRONICS) | Not at Digi-Key, Mouser or Newark. Maker store UCTRONICS / Amazon: ship origin and cost unknown (browser agent) | **Datasheet with dimension and lens diagrams in hand**: `vendor_docs/Arducam_B0454_datasheet.pdf`. STEP linked from the maker page: `https://download.arducam.com/3D-Drawing/B0454.STEP` (blocked here) |
| Arducam | B0506 | OV2710 1/2.7", 3 µm | 1280x720@30 MJPG | M12, 4.3 mm F1.6 manual focus, "2 m-∞" as shipped, IR-cut | 40.2 / 34.4 (720p if scaled) | USB 2.0 UVC | 38 x 38 mm | 0 to 70 °C | none (IR mode for external 850 nm LEDs) | $56.04 | Digi-Key 4679-B0506-ND: 0 in stock, lead 5 weeks | `vendor_docs/Arducam_B0506_datasheet.pdf` (dimension diagram) |
| DFRobot | FIT0819 | not stated in API data | 1280x720 | endoscope, fixed focus (range not reachable) | unknown | USB (micro-USB / USB-A / USB-C 3-in-1) | endoscope head on cable | not reachable | yes (endoscope LEDs, per its class; confirm) | $19.90 | **Digi-Key 240, Mouser 110**, Newark 26 ($35.17) | No datasheet at Digi-Key/Mouser. Newark points to `http://www.farnell.com/datasheets/4020645.pdf` (blocked). PROVENANCE_AUDIT: no CAD found |
| Camemake | CM_ENDO_010 / _011 / _014 / _023 | OV9734, 1280x720 | 1280x720 | endoscope head OD 3.5 / 3.5 / 3.3 / 3.9 mm; FOV 88° / 102° / 102° / ?; fixed focus (range on maker page) | 88° D: ≈ 50 (crop 320 px ≈ 13); 102° D: ≈ 65 (crop ≈ 16) | USB-UVC | tiny head plus decoder board | not reachable | most OV9734 endoscope modules have LEDs; confirm | $17.43-20.51 **each, MOQ 10** | Digi-Key **Marketplace** (shipped by Camemake, an EU maker): 118-138 in stock | Datasheets only on camemake.eu (blocked); exact URLs in section 6 |
| DFRobot | FIT0892 | not stated | 720p "wide-angle" | unknown (M12 or not) | unknown | USB | unknown | unknown | unknown | $19.90 | Digi-Key 137, Mouser 356 | No datasheet in API data |
| Raspberry Pi | Camera Module 3 (SC1223 per V12_PLAN; Mouser lists SC0895 std, SC0874 wide) | IMX708, 1.4 µm | 1280x720 supported | autofocus, **closest 10 cm (std), 5 cm (wide)** | at 100 mm std: ≈ 130; **cannot focus at 20-40 mm** without a +close-up lens | CSI ribbon | 25 x 24 mm | **0 to 50 °C** | none | $25 | Digi-Key / Mouser in stock | `vendor_docs/RaspberryPi_Camera-Module-3_*` |
| Raspberry Pi | SC1221 HQ Camera M12 | IMX477 1/2.3" | 1280x720 binned | M12, back focus 2.6-11.8 mm | with CIL083: 23.6 / 17.3 | CSI ribbon | 38 x 38 mm | see brief | none | $50 | **Digi-Key 0, lead 32 weeks**; Mouser 0 | `vendor_docs/RaspberryPi_HQ-Camera_product_brief_2025-02.pdf` |

Not found at any US distributor API: Arducam B0205, B0268 and B0196 (all checked by MPN: not found at Digi-Key, Mouser,
Newark or Farnell), ELP modules and Edmund Optics M12 lenses. All Arducam USB boards at Digi-Key (12 listed) show 0 in
stock. The ones that meet 720p (B0506, B045401, B0292, B0559, B0560, B0561, B043301, B044601, B044701) are on factory
lead. The global-shutter B0632/B0633/B0634 are 640x480 only, which fails the 720p requirement.

### 3b. M12 lenses for the M12 boards (FOV and DoF on B045401 / B0454, lens front about 30 mm from the tip)

| Maker | MPN | f / F# | Lens data (maker drawing) | Extension to focus at 30 mm | B045401 (5.18 mm): FOV simple / thin-lens, DoF | B0454 (3.63 mm): FOV simple / thin-lens, DoF | Operating temp. | Price | US seller / stock | Drawing |
|---|---|---|---|---|---|---|---|---|---|---|
| Commonlands (San Diego, CA) | **CIL062-F4.0-M12A650** | 6.2 mm / F4.0 | 1/1.8"-1/1.7", 10 MP; front Ø16.0, TTL 23.4, 5.5 g; rectilinear HFOV 55° on 1/1.8"; distortion < -1 %; IR cut 650 nm | 1.6 mm | 25.1 / 19.9 mm, DoF 1.2 mm (at effective u = 35: 24 mm, 1.7 mm) | 17.6 / 13.9 mm, DoF 0.84 mm (u = 35: 16.9 mm, 1.2 mm) | not stated ("/") | $23.00 | Digi-Key MP 4946-CIL062-F4.0-M12A650-ND: 158 | `vendor_docs/Commonlands_CIL062-F4.0-M12A650_drawing.pdf` |
| Commonlands | CIL062-F2.8-M12A650 | 6.2 mm / F2.8 | same body | 1.6 mm | 25.1 / 19.9, DoF 0.84 | 17.6 / 13.9, DoF 0.59 | not stated | $23.00 | Digi-Key MP: 1,306 | `vendor_docs/Commonlands_CIL062-F2.8-M12A650_drawing.pdf` |
| Commonlands | CIL083-F2.8-M12A650 | 8.0 mm / F2.8 | 1/1.8", 16 MP; front Ø14.0, TTL 24.4, 4.0 g; distortion < -1 % | 2.9 mm | 19.4 / 14.2, DoF 0.47 (u = 35: 17.5, 0.67) | 13.6 / 10.0, DoF 0.33 | not stated | $35.00 | Digi-Key MP: 211 | `vendor_docs/Commonlands_CIL083-F2.8-M12A650_drawing.pdf` |
| Commonlands | CIL059-F4.0-M12A650 (F5.6 version: CIL059-F5.6-M12A650) | 5.9 mm / F4.0 (F5.6) | 1/1.7", 12 MP; front Ø20.0, MTTL 31.3, 10.5 g (large) | 1.4 mm | 26.3 / 21.2, DoF 1.34 (F5.6: ≈ 1.9) | 18.5 / 14.8, DoF 0.94 (F5.6: ≈ 1.3) | not stated | $59.00 | Digi-Key MP: 44 (F5.6: 66) | `vendor_docs/Commonlands_CIL059-F4.0-M12A650_drawing.pdf` (F5.6 drawing is on docsend, not fetched) |
| EDATEC | ED-LENS-M12-180770-04 | 7.7 mm / not in API data | 4 MP | 2.7 mm | ≈ 20.2 / 15.0 | 14.1 / 10.5 | datasheet not reached | $11.50 | Mouser 25 (Digi-Key 0) | datasheet URL in section 6 |
| EDATEC | ED-LENS-M12-170800-12 | 8 mm / not in API data | 12 MP | 2.9 mm | 19.4 / 14.2 | 13.6 / 10.0 | datasheet not reached | $33.00 | Mouser 12 (Digi-Key 0) | datasheet URL in section 6 |
| Raspberry Pi | SC0949 | 8 mm | 12 MP | 2.9 mm | 19.4 / 14.2 | 13.6 / 10.0 | not reached | $25.00 | Mouser 93 (Digi-Key 0, lead 22 weeks) | not in API data |
| (any) | 12 mm and longer (e.g. EDATEC ED-LENS-M12-201200-08, SC0861 25 mm) | | | **8 mm or more: impractical** | | | | | | |

No M12 lens found states a minimum object distance. M12 lenses are designed for infinity, and close focus comes only from
screwing the lens out (extension above). The Commonlands drawings give barrel and image-plane dimensions but no MOD and no
operating temperature.

### 3c. Light

| Maker | MPN | What | Data | Price | US seller / stock | Docs |
|---|---|---|---|---|---|---|
| Inspired LED (US) | **24V-COB-4000K-12M**, cut to 2 segments | 24 V COB flex strip, cut every 1.97" (50 mm, 24 LEDs), 8 mm wide, 4000 K, CRI 91, 3.15 W/ft, so **≈ 0.52 W (≈ 22 mA) per 50 mm segment** | Operating temperature **not stated** in the spec sheet | $1.23 per segment (Digi-Key cut tape sells it per segment) | Digi-Key 1647-24V-COB-4000K-12MCT-ND: 3,261 | `vendor_docs/InspiredLED_24V-COB_flex_spec.pdf` (already on the v12 list as LED-INSPIRED-24V-COB) |
| (endoscope route) | built into FIT0819 / Camemake heads | LEDs at the lens | unconfirmed | included | as above | browser agent |

## 4. Recommendation

**Camera: Arducam B045401** (USB UVC, 1280x720@30 MJPG, M12x0.5 mount, 32 x 32 mm board, 0-70 °C). Buy it from
Digi-Key (US seller, $62.41, on a 2-week maker lead today). It is the only M12 UVC board here that is close to the
30 x 30 mm target. Its HDR mode helps with the scene, which has a glowing hot nozzle over a dark bead. **Condition:** the
browser agent must get its own datasheet, dimensioned drawing and STEP (section 6). Until then it does not meet the
owner's rule. **Fallback with data in hand: Arducam B0454** (38 x 38 mm, OV5648 1/4", -20 to +70 °C in the datasheet,
dimension drawing in `vendor_docs/Arducam_B0454_datasheet.pdf`, STEP linked by the maker). It is sold by Arducam's store
UCTRONICS from $38.99. Ship origin and cost are still to be confirmed. The B0454's smaller sensor gives about 1.4x the DoF
at the same FOV.

**Lens: Commonlands CIL062-F4.0-M12A650** (6.2 mm, F4.0; US maker, San Diego; $23 on Digi-Key Marketplace, 158 in
stock; maker drawing in vendor_docs). Screw it about 1.3-1.6 mm out from its infinity position to focus at the nozzle.
- On the B045401 it gives a field of about 20-24 mm across, about 16-19 µm per pixel, so a 0.45 mm bead spans about
  24-29 px. DoF is about 1.2-1.7 mm.
- On the B0454 it gives about 14-17 mm, about 11-13 µm per pixel and about 0.8-1.2 mm DoF.
- The F4 aperture was chosen over the F2.8 version and over 8 mm lenses because DoF, not pixel count, is the limit at this
  distance. The 8 mm CIL083 narrows the view to about 14-17 mm but gives only about 0.5-0.7 mm of DoF.
- Lock the focus once it is set, with the holder's set screw or a drop of low-strength thread locker, because the
  toolhead vibrates.
- Zero-cost baseline: the stock lens on either board focuses at 30 mm with only about 0.2-0.3 mm of extension. It gives a
  50-65 mm frame, and a CAXTON-style 320 px crop around the tip is then about 13-16 mm. Use this first to prove the
  pipeline, then fit the 6.2 mm lens.

**Light: two 50 mm segments of Inspired LED 24V-COB-4000K-12M** (Digi-Key, US, $1.23 each). Place one on each side of
the camera on the duct, aimed at the tip, so the nozzle casts no single hard shadow. They run from the 24 V toolhead
supply (about 45 mA for both) through a spare Klipper `output_pin` MOSFET, so the light is on for captures and can be
dimmed. The spec gives no temperature rating and the strip's 3M adhesive will not hold at 50-70 °C, so hold the segments
in a printed clip with a through-bolt clamp. Do not rely on the adhesive.

**Mounting and heat.** Every board here is rated 70 °C maximum. The board sits behind the lens (lens TTL 23.4 mm plus the
holder), so with the lens front at 30 mm the board face is about 55-60 mm from the tip. Keep it in the duct's cooled lee,
out of the plume, and measure the board temperature during the first hot print (260 °C nozzle, hot bed) before trusting
the 70 °C rating. Cable: the board has a JST B4B-ZR (4-pin, 1.5 mm) USB connector. Make up a high-flex 4-wire cable through
the drag chain instead of the supplied 1 m stiff cable. The Pi 5 load at 720p MJPG and 2.5 Hz capture is negligible.

**Second route (if the browser agent can get the data): an endoscope module.** The Camemake CM_ENDO_010 (3.5 mm head,
88°) or DFRobot FIT0819 have a tiny head, built-in LEDs and very large DoF thanks to their short focal length. They need a
CAXTON-style crop: about 13-16 mm around the tip at 25-20 px/mm. Both are blocked on paperwork today:
- FIT0819: in US stock at $19.90, but no reachable maker datasheet, drawing or temperature rating.
- Camemake: Digi-Key Marketplace, MOQ 10 (about $174), shipped from an EU maker. Datasheets are only on camemake.eu.

**Rejected:**
- Raspberry Pi Camera Module 3: its closest focus is 10 cm (5 cm on the wide version), it is rated 0-50 °C, and it uses a
  CSI ribbon. It would need a +close-up lens.
- HQ Camera M12 SC1221: CSI, 0 in stock, 32-week lead.
- B0506: 38 mm board, and its 1/2.7" sensor costs DoF.
- 12 mm and longer lenses: they need too much extension.

## 5. Proposed BOM lines (for mechloop/data/sourcing/v12_electronics.json once confirmed)

| SKU | Maker / MPN | Qty | Seller | Note |
|---|---|---|---|---|
| CAM-NOZZLE-ARDUCAM-B045401 | Arducam B045401 | 1 | Digi-Key 4679-B045401-ND | fallback Arducam B0454 (UCTRONICS); placeholder until its datasheet and drawing are in vendor_docs |
| LENS-NOZZLE-CIL062-F4 | Commonlands CIL062-F4.0-M12A650 | 1 | Digi-Key Marketplace 4946-CIL062-F4.0-M12A650-ND | drawing in vendor_docs; STEP from commonlands.com (browser agent) |
| LED-NOZZLE-COB-2SEG | Inspired LED 24V-COB-4000K-12M | 2 segments | Digi-Key 1647-24V-COB-4000K-12MCT-ND | same strip as the overview light |

## 6. What the owner's browser agent must fetch

Save each file to `vendor_docs/` with the maker prefix shown, and the STEP files to `vendor_cad/`.

1. Arducam B045401: datasheet, dimensioned drawing and STEP. Also check whether the metal enclosure lets an M12 lens with
   a Ø16 mm front be screwed in, or whether the enclosure must come off.
   - STEP (pattern of the B0454 link): `https://download.arducam.com/3D-Drawing/B045401.STEP`
   - Product page: search `https://www.uctronics.com/usb-uvc-camera-modules/usb-2-0-camera.html` for "B045401", or try
     `https://www.arducam.com/` and search "B045401".
   - Save as `Arducam_B045401_datasheet.pdf` and `Arducam_B045401.STEP`.
2. Arducam B0454 STEP and current price, ship-from location and shipping cost to the US:
   - `https://download.arducam.com/3D-Drawing/B0454.STEP`
   - `https://www.uctronics.com/5mp-ov5648-usb-camera-module-with-wide-angle-m12-lens-and-single-microphone-for-windows-linux-android-and-mac-os.html`
   - Also record the B0454 lens-holder height and thread length, which give the available focus travel.
3. Commonlands CIL062-F4.0-M12A650: STEP model, and the minimum object distance and operating temperature if Commonlands
   states them. Product page under `https://commonlands.com/` (search "CIL062"). Save as
   `Commonlands_CIL062-F4.0-M12A650.STEP`.
4. Arducam B0506 datasheet as linked by Digi-Key (only needed if B0506 is reconsidered):
   `https://www.arducam.com/downloads/datasheet/B0506_OV2710_Day&Night_UVC_Camera_Datasheet.pdf`
5. Camemake endoscope datasheets (focus range, LEDs, operating temperature, head and board drawings), from the URLs
   Digi-Key gives as datasheets:
   - `https://www.camemake.eu/shop/cm-endo-010-ov9734-hd-endoscope-camera-1280720-with-88-fov-966`
   - `https://www.camemake.eu/shop/cm-endo-011-ov9734-hd-endoscope-camera-1280720-with-102-fov-967`
   - `https://www.camemake.eu/shop/cm-endo-014-ov9734-compact-endoscope-module-1280720-102-fov-970`
   - `https://www.camemake.eu/shop/cm-endo-023-ov9734-integrated-hd-endoscope-camera-1280720-od-39mm-979`
   - Also: does Camemake sell single units direct, and what does shipping to the US cost?
6. DFRobot FIT0819 (focus range, head diameter, LED count, temperature, drawing):
   - Newark's datasheet link: `http://www.farnell.com/datasheets/4020645.pdf`
   - DFRobot product page: search "FIT0819" at `https://www.dfrobot.com/`, and the wiki at `https://wiki.dfrobot.com/`.
7. DFRobot FIT0892 (whether it has an M12 lens, plus board size and drawing): search "FIT0892" at `https://www.dfrobot.com/`.
8. EDATEC lens datasheets (f-number, which sets DoF), only needed if a cheaper 7.7-8 mm lens is wanted:
   - `https://edatec.cn/docs/assets/m12-lens/180770-04/ED-LENS-M12-180770-04-datasheet-en.pdf`
   - `https://edatec.cn/docs/assets/m12-lens/170800-12/ED-LENS-M12-170800-12-datasheet-en.pdf`

## 7. Files added in this pass

- `vendor_docs/Commonlands_CIL062-F4.0-M12A650_drawing.pdf` (recommended lens; via Digi-Key media, mm.digikey.com)
- `vendor_docs/Commonlands_CIL062-F2.8-M12A650_drawing.pdf`
- `vendor_docs/Commonlands_CIL083-F2.8-M12A650_drawing.pdf`
- `vendor_docs/Commonlands_CIL059-F4.0-M12A650_drawing.pdf`
- Already present and used: `vendor_docs/Arducam_B0454_datasheet.pdf` (byte-identical to Digi-Key's B045401 datasheet
  link), `vendor_docs/Arducam_B0454_page_2026-11-20.pdf` (UCTRONICS page with the B045401 / B0454-1 spec table),
  `vendor_docs/Arducam_B0506_datasheet.pdf`, `vendor_docs/RaspberryPi_Camera-Module-3_product_brief.pdf`,
  `vendor_docs/InspiredLED_24V-COB_flex_spec.pdf`.

## Update 2026-11-20 (Instinct REQ-010)

Arducam publishes no datasheet, drawing or STEP for the B045401 (Digi-Key's "B045401 datasheet" is the B0454's, byte for
byte). Primary camera is now the Arducam B0454 (USB UVC, OV5648, 38 x 38 mm board, M12 lens, -20..70 °C; datasheet and STEP
in hand) with the Commonlands CIL062-F4.0 lens. Its "fixed focus 300 cm to infinity" is the factory lens setting; close
focus comes from screwing the M12 lens out (~0.16 mm for the stock lens at 30 mm). Bench-check before relying on it that the
lens is not glued and the holder has the thread travel. Arducam's STEP lacks the 34 x 34 corner holes (4 x dia 2.4) shown
on the drawing: add them from the drawing. Fallback: B0292 (stated focus 40 mm to infinity, autofocus, not M12).
