# Height sensing: an eddy-current bed probe and a laser line for the nozzle camera (2026-11-20)

Two questions from ROADMAP priority 3 (cameras and sensors; phase 3 lists "optional eddy or load-cell probe, line laser"):

1. Which eddy-current probe should replace or supplement the OMRON E2B-M12KS04 inductive probe?
2. Which laser line module turns the nozzle camera (docs/NOZZLE_CAMERA.md: Arducam B045401 + Commonlands CIL062-F4.0-M12A650,
   lens front about 30 mm from the tip, about 16-19 µm per pixel) into a triangulation height sensor, and what resolution does
   that give?

Owner's rules applied (docs/DESIGN_GUIDELINES.md): named maker, maker's part number, maker's datasheet and drawing or CAD,
US seller preferred (overseas only with a stated, low shipping cost). Prices are USD, quantity 1, before shipping and tax.

**Sources and reach.** Distributor APIs through `mechloop/sourcing` (Digi-Key, Mouser, Newark, Farnell; live on 2026-11-20,
cached in `out/sourcing_cache/`); klipper3d.org (Eddy_Probe and Config_Reference pages, read directly); the makers' public
GitHub repositories (read with a blob-less git clone: bigtreetech/Eddy, Cartographer3D/cartographer-klipper,
beacon3d/beacon_klipper, SeeedDocument/Grove-2-Channel_Inductive_Sensor-LDC1612); mm.digikey.com for datasheets Digi-Key
hosts. The session proxy refused ti.com, quarton.com, wmsc.lcsc.com, beacon3d.com and docs.beacon3d.com,
cartographer3d.com and docs.cartographer3d.com, biqu.equipment and bttwiki.com, adafruit.com, seeedstudio.com,
panasonic.biz, coherent.com, us-lasers.com, globallasertech.com, jameco.com, klipper.discourse.group and the reseller sites
(Fabreeko, West3D, DREMC, Amazon). Where a figure comes only from a web-search summary of one of those pages it is marked
**(search)** and is listed in section 7 for the owner's browser agent to confirm. Nothing was worked around.

## 1. Eddy-current bed probe

### 1.1 What an eddy probe needs from this printer

- **The target is the spring-steel sheet.** The bed stack is MIC-6 aluminium 232 x 232 x 6.35 mm, a magnetic base (a
  flexible ferrite-in-polymer sheet, non-conductive), then 220 x 220 mm textured PEI on 0.4 mm spring steel
  (docs/PRINTER_V11.md). An eddy coil 2-3 mm above the PEI sees the steel. At the LDC1612's working frequency (a few MHz) the
  skin depth in spring steel is of the order of 10-20 µm (resistivity about 2e-7 Ω·m, relative permeability of order 100), so
  0.4 mm of steel is many skin depths thick and the aluminium plate below is effectively hidden. The PEI coating (tens of µm,
  non-conductive) only adds a constant offset, which calibration absorbs.
- **Beacon's guidance (search):** Beacon's FAQ says any highly conductive surface works, names PEI-coated steel as a
  recommended surface, and gives **400 µm as the recommended minimum steel thickness**. Our 0.4 mm sheet is exactly at that
  minimum. A reseller comparison (DREMC, search) says neither Beacon RevH nor Cartographer V4 works with printers that have
  *integrated* magnetic beds (magnets embedded in the plate). Our magnetic base is a uniform sheet under the steel, not discrete
  magnets in the plate, and the steel sheet shields it; still, confirm on the first calibration that the frequency map is
  smooth across the bed (a `BED_MESH_CALIBRATE METHOD=scan` on the bare sheet should show only the plate's shape).
- **The sheet must seat the same way every time.** The probe measures the steel, so any lift of the sheet from debris under
  it is measured as bed shape (correctly, since the print sits on the PEI).
- **Heat.** The BTT Eddy family is rated **60 °C ambient maximum** (BTT manual, section 1). The E2B is rated 70 °C. The v11
  doc estimates the probe's temperature at its position 34.5 mm behind the nozzle (`{{PTEMP_SHORT}}` in PRINTER_V11). Any eddy
  probe must be checked against that estimate; BTT says to put the electronics end furthest from the hotend.
- **Klipper's own warning:** "changes to the temperature of the bed, sensor coil, sensor electronics, or any metal near the
  sensor can all impact the results ... (think microns)". Calibrate and probe at a consistent temperature, or use a coil
  thermistor with `[temperature_probe]` drift calibration (section 1.4).

### 1.2 How Klipper supports eddy probes (klipper3d.org, read 2026-11-20; page saved as `vendor_docs/Klipper_Eddy_Probe_page_2026-11-20.html`)

- **Mainline module:** `[probe_eddy_current]` with `sensor_type: ldc1612` (the only sensor type it accepts), over I2C to an
  MCU (`i2c_mcu`, `i2c_bus`, optional `intb_pin`, `frequency` = the LDC1612's reference crystal, default 12 MHz). Required:
  `descend_z` (recommended 0.5 mm). Calibration: `LDC_CALIBRATE_DRIVE_CURRENT` with the sensor about 20 mm above the bed,
  then `PROBE_EDDY_CURRENT_CALIBRATE` (paper test, then an automatic sweep). Klipper's example output shows noise of about
  0.2-0.7 µm at 0.25-3 mm.
- **Probing methods:** default (descend and sample; recommended for `Z_TILT_ADJUST` etc.), `scan` and `rapid_scan` (bed mesh
  with horizontal moves only at `HORIZONTAL_MOVE_Z` of about 1 mm), and **`tap`**: the nozzle touches the bed and the probe
  finds the moment it lifts off. Tap needs `position_min: -1` on Z, a `tap_threshold` from `PROBE_EDDY_CURRENT_TAP_CALIBRATE`,
  a clean nozzle and bed, a nozzle cool enough not to mark the PEI, and nothing that stops the nozzle reaching the bed. Tap
  has no thermal drift and no XY offset. **So mainline Klipper now gives LDC1612 probes a contact mode**; it is not only a
  Beacon/Cartographer feature.
- **Drift compensation:** a `[temperature_probe <same name>]` linked to the eddy probe, then `TEMPERATURE_PROBE_CALIBRATE
  PROBE=<name> TARGET=<max coil temp>` (paper test every 2 °C while the bed heats the coil). Makers may supply a stock
  `drift_calibration`.
- **Homing Z with the probe** is supported (`endstop_pin: probe:z_virtual_endstop`) with a one-time bootstrap procedure.
- **Vendor plugins instead of mainline:** Beacon (`beacon_klipper`, a Klipper module plus Beacon's own firmware, RevD and RevH
  `.dfu` files in the repo) and Cartographer (`cartographer-klipper`, the "scanner"/"idm" module plus firmware for USB or CAN,
  v5 "Survey" firmware in the repo). Both replace `[probe_eddy_current]` with their own module and calibration. A Klipper
  forum thread "Cartographer V3/V4: Reverse engineering" (search) suggests community work on running Cartographer from
  mainline; not verified.

### 1.3 Comparison

Stock and price: BTT, Beacon and Cartographer are **not carried by Digi-Key, Mouser, Newark or Farnell** (keyword searches
returned nothing). Their figures come from the makers' GitHub repositories (read) or web-search summaries of store pages
(search).

| | BTT Eddy (USB) | **BTT Eddy Duo** | BTT Eddy Coil | Cartographer3D V4 (V3 earlier) | Beacon RevH (RevD earlier) | Seeed Grove 2-Ch Inductive Sensor | TI LDC1612EVM |
|---|---|---|---|---|---|---|---|
| Maker / MPN | BIGTREETECH (BIQU) Eddy USB V1.0 | BIGTREETECH Eddy Duo (BTT order no. 1060000710 per a UK reseller listing, search) | BIGTREETECH Eddy Coil | Cartographer3D, Cartographer V4 "AIO" USB & CAN | Beacon3D, Beacon RevH (standard and low-profile) | Seeed Studio 101020599 | Texas Instruments LDC1612EVM |
| Sensor IC | LDC1612 + RP2040 | LDC1612 + RP2040 | LDC1612 only (I2C to a toolboard) | eddy-current (IC not stated in what was reached); STM32 MCU per firmware files | eddy-current, Beacon's own firmware (Rust/RTIC) | LDC1612, on-board PCB coil | LDC1612 + MSP430, breakaway 14 mm PCB coil |
| Klipper support | **mainline** `[probe_eddy_current]` (BTT README: "no longer necessary to use the BIGTREETECH fork") | **mainline** (USB or CAN) | mainline, via the toolboard's I2C | vendor plugin `cartographer-klipper` | vendor plugin `beacon_klipper` | mainline in principle (`ldc1612` over I2C); no printer mount, no maker Klipper guidance | not a printer probe (bench evaluation) |
| Interface | USB (4-pin 1.5 mm, 2.5 m cable) | **USB or CAN** (same 4-pin; firmware selects) | I2C, 15 cm DuPont lead | USB or CAN, both cables in the kit, USB firmware as shipped (search) | USB only (search; West3D warns a BTT Pi/Manta needs an inline USB hub) | I2C (Grove) | USB (GUI) |
| Price / US seller / stock | Micro Center (US) listed 2 in stock at one store, price not shown (search); BIQU feed shows a US-warehouse SKU at $25.98, out of stock when cached (search) | **$38.99 at us.biqu.equipment** (BIQU's US store; free shipping over $59) (search); the cached US-warehouse SKU showed $25.98 out of stock (search); Newegg $23.49 ships from China (search) | BIQU store (price not reached) | **No US seller found.** DREMC (Australia) AUD 74.45, 1 left; reach.dog $39.99, currency and origin not stated (search) | Fabreeko $79.99 (US storefront, search); West3D $81.49 low-profile, currency not confirmed (search); Beacon's own store "from $80" at the 2024 launch (search) | Mouser 713-101020599 $16.40, **23 in stock**; Digi-Key 0 (7 wk) | Digi-Key 296-39660-ND $130.68, 41 in stock; Mouser $130.70, 16 |
| Mounting drawing / CAD | **Dimensioned drawing** (`vendor_docs/BTT_Eddy_dimensions.jpg`, also in the manual) and **maker STEP** (`EDDY.STEP`, 48 MB, SolidWorks 2023 export; saved gzipped as `vendor_cad/staging/BTT_EDDY.STEP.gz`); printed mounts for common machines in the repo | same manual and repo (one housing drawing covers the series) | same | in the repo: assembly-jig STLs only; mount drawings on docs site (blocked) | not in the repo; docs site (blocked) | `vendor_docs/Seeed_Grove-LDC1612_101020599_size.jpg` (board outline); schematic in the Seeed repo | TI user guide SNOU135A (ti.com, blocked) |
| Body size | 18.1 x 33.8 x 15.3 mm (18.3 at the cable boss); 2 x Ø3.15 holes 10.5 mm apart, 13.9 mm from the top; designed for the Voron carriage's Omron-probe position (2 x M3 x 25) | same | same housing | not reached | not reached | Grove 20 x 40 mm class (see drawing) | EVM board |
| Coil size | **not published**; the coil centre is 9.05 mm from each side and 11.33 mm from the sensing-end edge, so the coil is under about 16 mm across | same | same | not reached | not reached | on-board coil (size on the drawing) | 14 mm PCB coil (TI test coil: 2 layers, 32 turns/layer, 14 mm, 19.4 µH) |
| Mounting height (sensor face above the nozzle tip) | **2-3 mm**, about 2.5 mm optimal (BTT README and manual) | 2-3 mm | 2-3 mm | 2.6-3.0 mm per a community wiki (search) | 2-3 mm per a Voron community wiki (search); quickstart not reached | user's choice | n/a |
| Temperature compensation | coil thermistor (Generic 3950 on `eddy:gpio26` in BTT's sample config) + Klipper `[temperature_probe]` drift calibration; RP2040 temperature also reported | **thermistor + drift calibration** ("Eddy and Eddy Duo ONLY") | **none** (BTT: "may be less reliable for homing ... in a sealed chamber") | factory pre-calibrated temperature/touch compensation per a reseller; community config shows a 47k thermistor on the Carto MCU (search) | "low thermal drift, minimized by design, with active compensation" (West3D, search); MCU temperature reported (firmware 2.0.0 notes) | none | n/a |
| Operating temperature | ≤ 60 °C ambient | ≤ 60 °C ambient | ≤ 60 °C ambient | not reached ("high-temperature-rated accelerometer", search) | accelerometer 100 °C measuring / 115 °C standby (West3D, search); firmware 2.0.0 "reduced current ... above rated temperature" | not stated | LDC1612 IC: -40 to 125 °C |
| Stated repeatability | "Standard error 0.5 µm" (BTT manual) | same | same | not reached | not reached | none | n/a |
| Contact / touch mode | **Klipper's mainline `tap` method** (generic for LDC1612 probes; BTT does not document it) | same | same (no thermistor, but tap does not need one) | yes, Cartographer "touch" in the vendor plugin (search) | yes, **Beacon Contact**, free firmware update for RevH and RevD, contact force < 30 g (search) | Klipper `tap` in principle | n/a |
| Accelerometer | no | no | no | yes (V4, search) | yes (RevH) | no | no |
| Wiring to our boards | USB to the Pi 5 | USB to the Pi 5, or **CAN to the Octopus V1.1** (BTT manual sections 4.15-4.16 draw both for "Octopus V1.1/Pro V1.0/Pro V1.0.1") | I2C to a toolboard (we have none) | USB to the Pi, or CAN | USB to the Pi | I2C to the Octopus (software I2C pins) | n/a |
| Steel-sheet guidance | BTT says nothing specific; the probe is sold for PEI spring-steel beds | same | same | "not for integrated magnetic beds" (DREMC, search) | **≥ 400 µm steel recommended**; PEI-coated steel recommended (Beacon FAQ, search); "not for integrated magnetic beds" (DREMC, search) | none | TI tests on 1.5 mm aluminium and 2 mm stainless |

### 1.4 The LDC1612 itself (TI datasheet SNOSCY9A, saved as `vendor_docs/TI_LDC1612_LDC1614_datasheet_SNOSCY9A.pdf`)

ti.com was refused; the file is TI's own datasheet (Rev. A, March 2018) as published in Seeed's documentation repository
(PDF metadata: Texas Instruments, SNOSCY9A).

- 2-channel, 28-bit inductance-to-digital converter, I2C, 2.7-3.6 V, sensor frequency 1 kHz to 10 MHz, operating
  -40 to 125 °C, Digi-Key 296-LDC1612DNTR-ND $3.62 (22,500+ in stock), Mouser 595-LDC1612DNTR $3.19.
- **Sensing range vs coil size:** "Sensing Range Beyond Two Coil Diameters" (features list), but resolution falls quickly
  with distance. TI's worked curves are for a 14 mm PCB coil: R_P rises from about 5 kΩ at 1 mm to about 16 kΩ by 8 mm on
  2 mm stainless (Figure 51), and the frequency/inductance change flattens beyond about 0.5-1 coil diameter (Figure 52, 1.5 mm
  aluminium). "The target distance scales based on the sensor diameter." So a coil of about 14-16 mm (the size the BTT
  housing allows) works best a few mm from the target: that is why every maker says 2-3 mm, and why the scan height is about
  1-2 mm (`HORIZONTAL_MOVE_Z`).
- Layout rule relevant to our bracket: "If the sensor is placed in a plane, there should be a gap of at least 20 % of a sensor
  diameter between the plane and the outermost coil", and no continuous conductive ring around the coil. A metal bracket
  close behind or around the coil lowers its Q and couples its thermal expansion into the reading; hold the probe in a
  printed holder or by its two screws with a gap of several mm to any aluminium (section 5).
- TI's reference coil document is saved as `vendor_docs/TI_LDC_Reference_Coil.pdf`.

### 1.5 Recommendation (eddy probe)

**BIGTREETECH Eddy Duo, $38.99, BIQU US store (us.biqu.equipment/products/bigtreetech-eddy, variant "Eddy Duo"),
mounted where the E2B sits now, connected by USB to the Pi 5 (CAN to the Octopus as the fallback).**

Why:
- It is the only candidate with **mainline Klipper** support, so it adds no vendor plugin to keep in step with Klipper
  updates (Beacon and Cartographer each need their own module and firmware).
- It has the **coil thermistor** that Klipper's `[temperature_probe]` drift calibration needs (the Eddy Coil does not).
- The maker publishes a **dimensioned drawing, a STEP model, a manual with wiring for our exact Octopus V1.1** (USB and CAN),
  and sample configs. All are now in `vendor_docs/` and `vendor_cad/staging/`.
- It has a US seller, at the lowest price of the three.
- Mainline Klipper's **`tap` method** gives it a nozzle-contact Z reference, which removes the main advantage Beacon and
  Cartographer had. Treat tap as "to be proven on our machine" (BTT does not document it).

What it buys over the E2B:
- Bed meshes by `rapid_scan` in seconds, at any density.
- Z zero from the nozzle itself (tap), so no Z-offset paper test after nozzle swaps.
- Sub-micron noise against the E2B's switching repeatability. The E2B's figure is still unsourced (PROVENANCE_AUDIT lists it
  as assumed).
- The same probe can scan a printed coupon's top surface as a coarse height map (coil-sized footprint, about 15 mm).

**Replace or supplement?** Replace. The two compete for the same spot behind the Roto, and the E2B's M12 body and nuts
would be metal in the eddy coil's field. Keep the E2B bracket design as a fallback variant in the design history, not on the
machine.

Conditions before ordering:
1. **Temperature.** Recompute the probe-position temperature for the Eddy's 60 °C ambient rating, which is lower than the
   E2B's 70 °C. If the estimate is above about 50 °C, move the probe further from the heater, or add a printed shield (the
   electronics end must face away from the hotend).
2. **Mounting height** 2.5 mm (range 2-3) from the probe face to the nozzle tip. The E2B face sits 2.0 mm above the tip, so
   the new bracket is a new part, not the E2B L.
3. Confirm the variant, stock and ship-from (US warehouse) on the BIQU page with the browser agent (section 7). Fallback
   seller: Micro Center (US) for the Eddy USB V1.0. That is the same probe without CAN, and it also has the thermistor.

**Alternatives kept:**
- **Beacon RevH** (US resellers, about $80): the most mature contact mode (Beacon Contact, < 30 g force), an accelerometer,
  and a higher temperature rating than BTT. It needs a vendor plugin, and its drawings are on docs.beacon3d.com (blocked here).
  Choose it if the Eddy's tap or thermal behaviour disappoints.
- **Cartographer V4**: no US seller found.
- **Seeed Grove LDC1612 board** (Mouser, $16.40): a named-maker LDC1612 board for a bench experiment, not a printer probe.
  It has no thermistor and no mount, and the maker gives no Klipper guidance.

## 2. Laser line for the nozzle camera

### 2.1 Choosing the wavelength

- **The lens decides against 650 nm.** The recommended lens, Commonlands CIL062-F4.0-M12A**650**, carries a 650 nm IR-cut
  filter. A 650-655 nm line sits right on the filter edge and is attenuated by an unknown amount. Use 635-638 nm red, or
  better, green.
- **The sensor favours green.** The B045401 is a colour (Bayer) sensor. Green pixels are half of all pixels, and 520 nm is
  near the peak of silicon colour-sensor response. A green line is sampled at twice the density of a red one and needs less
  exposure.
- **The scene favours green too.** A nozzle at 200-280 °C emits no visible light, and the IR-cut filter removes its infrared,
  so glow is not the issue. The issue is the white COB lights (docs/NOZZLE_CAMERA.md, section 3c). Switch them off or dim
  them for laser frames, or use the green channel minus the red/blue background.
- **Filament colours.** A line returns little light from filament that absorbs its colour: green on red or black, red on
  green or blue. Translucent PETG and natural PLA scatter light below the surface. That moves the line's centroid and widens
  it, and longer wavelengths penetrate further in most lightly pigmented polymers, so blue (450 nm) or green is better than
  red on translucent plastic. **No 450 nm line module was found at a US distributor**: Quarton's 450 nm parts at Digi-Key are
  all dot modules (VLM-450-52/-60/-61/-62). Green 520 nm is the practical choice. Calibrate per material (section 3.4).

### 2.2 Laser class (eye safety)

The owner asked for Class 1 or 2 only. **Every line module found with a short focus is Class 1M**, which is a subclass of
Class 1 under IEC 60825-1. Class 1M is safe for unaided viewing under reasonably foreseeable conditions, but **not when the beam
is viewed through magnifying optics** (a loupe, a magnifier, binoculars). Quarton states "laser power output < 0.39 mW",
measured through a 7 mm aperture at 10 cm. All the Quarton line modules at Digi-Key are 1M, including the economy -28 series.
The only strictly Class 1 or Class 2 parts found do not fit:
- Quarton VLM-635-27 LPA (Class I): focused for more than 2 m, line 3 mm wide at 5 m, rated +10 to +40 °C.
- Panasonic HG-C (Class 2): a point sensor, not a line.
- Adafruit 1057 (Class IIIa): excluded.

**Owner's decision needed:** accept Class 1M with these controls, or drop the laser.
- The laser is off by default and is switched on only by a measurement macro (Klipper `output_pin`, section 5.3).
- It is never on while someone inspects the bead with a loupe or magnifier.
- The beam points down at the bed, below eye level, and inside the printer's enclosure panels (if fitted).
- Label the toolhead with the maker's 1M label (Quarton ships one).

### 2.3 Comparison

Stock and prices are live distributor answers on 2026-11-20. Quarton Inc. sells through Digi-Key (US). Quarton USA Inc. is
its US arm (DirectIndustry listing). Datasheet links in the table are the URLs Digi-Key gives. quarton.com and LCSC (which
mirrors them) were refused, so figures marked (search) come from search summaries of those PDFs.

| Maker / MPN | λ | Class | Fan angle | Focus / line width | Supply | Size | Op. temp. | Price | US stock | Datasheet |
|---|---|---|---|---|---|---|---|---|---|---|
| **Quarton VLM-520-56 LPO-D30-F10** | 520 nm (Digi-Key: 523) | 1M | 30° | **focused at 10 cm** ("super fine line" series); width table in datasheet (Table B, not reached) | 3-6 V DC, 80 mA (Digi-Key); 10 mW optical, < 0.39 mW through the 7 mm/10 cm aperture | Ø10 mm cylinder (length on datasheet) | -20 to +60 °C (VLM-520-56 series listing, search) | **$98.40** | Digi-Key 100-VLM-520-56LPO-D30-F10-ND: **3**, maker lead 4 wk | Quarton VLM-520-56 30° manual (URL in section 7) |
| Quarton VLM-520-56 LPO-D5-F10 | 520 nm | 1M | 5° | 10 cm | 3-6 V | Ø10 mm | as above | $98.40 | Digi-Key: 3 | VLM-520-56 5° manual |
| Quarton VLM-520-56 LPO-D110-F10 | 520 nm | 1M | 110° | 10 cm | 3-6 V | Ø10 mm | -20 to +60 °C (search) | $78.57 | Digi-Key: 3 | |
| Quarton VLM-520-58 LPO-D20-F10 / -D60-F10 | 520 nm | 1M | 20° / 60° | 10 cm | | | | $136.98 / $136.35 | Digi-Key: 2 / 1 | |
| Quarton VLM-635-56 LPO-D20-F10 | 638 nm | 1M | 20° | 10 cm | 3-6 V, 50 mA | Ø10 mm | not reached | $76.56 | Digi-Key: 3 | VLM-635-56 20° manual |
| Quarton VLM-635-56 LPO-D45-F10 / -D5-F10 / -D60-F10 | 638 nm | 1M | 45° / 5° / 60° | 10 cm | 3-6 V, 50 mA | Ø10 mm | | $73.21 / $76.56 / $73.21 | Digi-Key: 2 / 3 / 1 | |
| Quarton VLM-635-57 LPO-D45-F10 (TTL input) | 638 nm | 1M | 45° | 10 cm | 3-6 V, 50 mA, TTL on/off input | Ø10 mm | | $79.25 | Digi-Key: 2 | VLM-635-57 45° manual |
| Quarton VLM-520-28 LPT (economy) | 520 nm | 1M (datasheet order table, search) | not reached | not stated (economy, long range) | **7-10 V**, 100 mA (Digi-Key); 3-6 V on a series sheet (search) | Ø9 x 33 mm (search) | not reached | $58.27 | Digi-Key: 189 | VLM-520-28 manual |
| Quarton VLM-650-28 LPT (economy) | 645-665 nm | 1M | > 60° (search) | 1.2 mm wide at 1 m; fixed (search) | 2.6-6 V, < 35 mA | Ø9 x 26 mm, brass (search) | not reached | $41.96 | Digi-Key: 36 | VLM-650-28 manual |
| Quarton VLM-650-23 LPO (mini) | 650 nm | (LPO: 1 or 1M; not reached) | not reached | not reached | 3-6 V, 50 mA | **Ø5 mm** | not reached | $82.57 | Digi-Key: 31 | VLM-650-23 manual |
| Quarton VLM-635-27 LPT-10 / LPA | 630-645 nm | 1M / **Class I** | > 90° | 3 mm wide at 5 m; "work distance above 2 m" | 2.6-6 V, < 55 / 50 mA | Ø12.5 x 30 mm, brass | **+10 to +40 °C** | $86.39 / $69.95 | Digi-Key: 2 / 13 | **in hand**: `vendor_docs/Quarton_VLM-635-27-series_datasheet_DigiKey-link-for-VLM-650-27-LPT-10.pdf`, `vendor_docs/Quarton_VLM-635-27-LPA_manual.pdf` |
| Adafruit 1057 | 650 nm | **IIIa (5 mW): excluded** | 120° | fixed; "fades out" | 2.8-5.2 V, 25 mA | Ø10.1 x 32.8 mm | -10 to +40 °C | $8.95 | Digi-Key: 256 | in hand: `vendor_docs/Adafruit_1057_line-laser_datasheet.pdf` |
| Diode Laser Concepts 511322-0014 | 635 nm | not reached | 45° | industrial M12 | | M12 | | $490.65 | Mouser: 7 | Mouser link (blocked) |
| Coherent (Lasiris), US-Lasers, Global Laser | | | | | | | | | not at Digi-Key/Mouser/Newark; maker sites refused | |

Notes:
- **Housing at +V.** In the Quarton -27 datasheets the brass housing is at VDD(+): "it is imperative that contact between the
  laser module and the machine be avoided". Assume the same for the -56 until its datasheet says otherwise. Hold the module
  in a **printed (insulating) clamp**, never in a metal bore, and protect it against supply surges.
- **Temperature.** The -27 series is rated +10 to +40 °C. Only the -56 series listing (search) gives -20 to +60 °C. The laser
  sits higher on the toolhead than the camera board (section 3.5), but measure its temperature on the first hot print.

### 2.4 Recommendation (laser)

**Quarton VLM-520-56 LPO-D30-F10** (520 nm green, 30° fan, focused at 10 cm, Class 1M, 3-6 V at 80 mA, Ø10 mm), Digi-Key
100-VLM-520-56LPO-D30-F10-ND, **$98.40, 3 in stock** (4-week maker lead after that), held in a printed clamp beside the
hotend as in section 3.5.

- **Fan.** In the compact geometry of section 3.5 (source about 45 mm up and 38 mm along the line), the 30° fan lights a line
  about 40 mm long on the bed, which covers the camera's 20-24 mm field. The -D5-F10 ($98.40, 3 in stock) gives only about
  7 mm, enough for a single bead but not for a sweep over a coupon. The F10 focus is the shortest Quarton offers. The beam
  path here is about 60 mm, short of the 100 mm waist, so the line is wider than at focus. Read the line-width table in the
  datasheet (section 7) and confirm on the bench. If it is too wide (over about 0.2 mm), mount the laser further out along
  the line so the path approaches 100 mm.
- **Cheaper red alternative:** VLM-635-56 LPO-D20-F10, $76.56, 3 in stock. 638 nm is inside the lens's 650 nm IR-cut
  passband, but uses only the red Bayer pixels.
- **TTL-gated red alternative:** VLM-635-57 LPO-D45-F10, $79.25, 2 in stock. Its on/off input avoids a driver transistor.
- **Stock is thin** (1-5 per part number). Order early, or accept the 4-week lead.

## 3. Triangulation with the nozzle camera

### 3.1 Principle

A laser sheet makes a bright line where it meets the surface. When the surface rises by Δz, the line's intersection with the
surface moves, and the camera, looking from another direction, sees the line shift in the image. With the camera's pixel
scale p (µm per pixel at the object), the shift in pixels is Δz·S/p, where S is the geometric gain.

Geometry. Let the camera's optical axis lie in a vertical plane (the "camera plane"), tilted β from vertical (β = 90° would be
horizontal). The laser line runs perpendicular to the camera plane, so it appears as a near-horizontal line across the image.
The laser sheet contains the line and is tilted α from vertical within the camera plane, from the side opposite the camera
(α = 0: a vertical sheet). Then:

    S = sin(α + β) / cos α        height per pixel = p / S

- α = 0 (vertical sheet): S = sin β. The line stays at the same XY on the part, whatever the height.
- Laser tilted on the camera's own side (α measured toward the camera): S = sin(β − α) / cos α, which is always worse.
- The classical form (camera looking straight down, β = 0, laser at α): S = tan α.

**The sheet's tilt along the line direction does not matter.** Moving the source along the line's own direction only moves
the line along itself. So the laser can sit off one end of the line, beside the hotend and out of the plume, with its sheet
vertical. That is the mount proposed in section 3.5.

### 3.2 Resolution for our camera (p = 16-19 µm/px from docs/NOZZLE_CAMERA.md; 17.5 µm/px used for the sub-pixel column)

| Camera tilt β (from vertical) | Laser tilt α | S | µm per pixel at p = 16 | at p = 19 | at 0.2 px sub-pixel (p = 17.5) |
|---|---|---|---|---|---|
| 45° | 0° (vertical sheet) | 0.71 | 22.6 | 26.9 | 4.9 |
| 45° | 30° | 1.12 | 14.3 | 17.0 | 3.1 |
| 45° | 45° | 1.41 | 11.3 | 13.4 | 2.5 |
| 65° | 0° | 0.91 | 17.7 | 21.0 | 3.9 |
| 65° | 30° | 1.15 | 13.9 | 16.5 | 3.0 |
| 65° | 45° | 1.33 | 12.0 | 14.3 | 2.6 |
| 75° | 0° | 0.97 | 16.6 | 19.7 | 3.6 |
| 65° | 15° on the camera's side | 0.79 | 22 (at 17.5) | | |

Readings:
- At the pixel level the sensor resolves about **14-27 µm of height per pixel**. A 30-45° laser tilt from the opposite side
  roughly halves that compared with a vertical sheet under a steep camera. Under a camera that is already shallow
  (β = 65-75°), the gain from tilting the laser is only 15-35 %.
- With sub-pixel line-centre finding (Gaussian or centre-of-mass fit across a line 5-20 px wide; 0.1-0.3 px is typical), the
  **ideal noise is about 2-6 µm**.
- **Physical limit, speckle** (Dorsch, Häusler and Herrmann, "Laser triangulation: fundamental uncertainty in distance
  measurement", Applied Optics 33(7), 1994): δz ≈ λ / (2π · sin u · sin θ), where u is the observation aperture half-angle
  and θ the triangulation angle. Our lens is F4 with f = 6.2 mm, so the aperture is 1.55 mm at about 35 mm and
  sin u ≈ 0.022. With λ = 0.52 µm and sin θ ≈ 0.9, **δz ≈ 4 µm**. Red at 0.638 µm gives about 5 µm. Speckle, not pixel
  count, sets the floor. That is another small point in green's favour.
- **Expected in practice:** about **5-10 µm repeatability on opaque matte surfaces** (textured PEI, opaque PLA). About
  **10-30 µm on translucent PETG or natural PLA**, after per-material calibration, because sub-surface scattering moves and
  widens the line. Heat shimmer near the nozzle adds noise if the beam crosses the plume (section 3.5).
- **Range.** The lens's depth of field is about 1.2-1.7 mm (docs/NOZZLE_CAMERA.md). The line stays sharp over about
  ±0.6-0.8 mm around focus and can still be centred, less precisely, over a few mm. In the 20-24 mm field, ±1 mm of height
  moves the line by about ±60 px, so the field is not a limit.

What it is good for:
- (a) First-layer and layer-top height across a bead or coupon, measured against the bare sheet in the same frame. This is an
  absolute layer thickness without any probe offset.
- (b) Bead width and height (cross-section) right after deposition, for flow calibration.
- (c) A height map of a printed coupon: sweep the toolhead at constant Z. At 30 fps and 5 mm/s that is one profile every
  0.17 mm.
- (d) A cross-check of the eddy probe's Z zero: the line on the bare sheet at a known Z, next to the nozzle tip seen in the
  same image.

### 3.3 Why not just the camera?

The camera alone sees the bead's width and the nozzle-to-bead gap only in silhouette. The laser turns each frame into a
calibrated height profile. The same pixels, lens and Pi pipeline are used, and the added hardware is about $100.

### 3.4 Calibration (uses the printer's own Z axis as the standard)

1. **Intrinsics.** Calibrate the camera at the working distance with a printed dot or checker target on the bed corner (the
   v12 top-down camera's target can be reused). This gives the µm-per-pixel scale and the lens distortion (the lens is under
   -1 % distortion).
2. **Height map.** Over the bare sheet, step Z (the bed) in 20 µm steps through ±1 mm and record the line's image row at
   each step. Fit row against Z, a low-order polynomial per image column. This absorbs α, β and lens errors with no angle
   measurement. Klipper's Z resolution (lead-screw microsteps) is far finer than the target. Backlash in the POM nuts is
   removed by always approaching from one side.
3. **Per material.** Print a flat coupon in each filament and compare the laser height with a dial indicator or the eddy
   probe's scan. Record the offset as a material learning, with provenance (ROADMAP: every result updates the system).
4. Repeat steps 2-3 after any change to the camera or laser mount.

### 3.5 Mounting sketch (keeps out of the heater plume)

The heater plume rises from the Revo heater core and sock as a column above the block. The part-cooling jet leaves a 14 x 3 mm
outlet 24 mm from the nozzle on the rear-right diagonal (PRINTER_V11). The nozzle camera sits on the blower duct, outside the
plume, looking at the tip at about 30 mm, tilted roughly β = 55-70° from vertical (fix the exact value in the bracket design).

Proposed:
- **Line.** On the bed, perpendicular to the camera plane, **6-10 mm from the nozzle axis on the camera's side** of the tip.
  That is far enough that no ray of the sheet passes through the sock or nozzle, and inside the camera's 20-24 mm field.
- **Laser.** Off one end of the line, in the line's vertical plane (vertical sheet, α = 0): about **45 mm above the bed and
  38 mm along the line from its centre**, aimed down about 50° below horizontal, path about 59 mm (geometry computed with a
  scratch script). Its rays reach the bed from the side, never from above the heater block, and pass at least 10 mm from the
  heater core and sock. Check that against the Roto/Revo STEP in the design and adjust the 38/45 mm. The laser is on the
  opposite side of the camera plane from the blower outlet, so its beam does not cross the cooling jet.
- **Optional gain.** A tilt α of 10-20° away from the camera adds 10-20 % gain (section 3.2), but at the bed the sheet then
  moves toward the nozzle by h·tan α. Only do this with the line at 10 mm or more from the tip.
- **Holder.** A printed PETG clamp around the Ø10 mm body (the housing may be at +V, so it must be insulating), through-bolted
  with nuts and washers (DG-04), with a set screw or slot to rotate the module about its axis so the line can be made square
  to the camera rows. Print-service rules apply (ROADMAP: 0.8 mm minimum wall, 2 mm minimum feature).

```
 Side view in the camera plane                  Plan view (looking down)
 (camera on the duct, laser not shown)

        camera                                   laser (45 mm up)
          \  beta from vertical                    o
           \                                        \  sheet is vertical,
            \      |  hotend                         \  contains the line,
             \     |                                  \ rays come in from the side
              \   [#]  heater + sock                   \
               \   v  nozzle tip                        \
    ------------*--+------------------- bed        ======*=================  laser line (perpendicular
                ^  ^                                     |   6-10 mm         to the camera plane)
     laser line    nozzle axis                           +   nozzle axis
     (6-10 mm toward the camera)                          \
                                                           \  camera plane (camera looks along it)
                                                            [cam]
```

## 4. Reference only: an industrial triangulation point sensor

**Panasonic HG-C1030** (CMOS laser displacement sensor, NPN). Datasheet: `vendor_docs/Panasonic_HG-C_series_datasheet.pdf`
(via Digi-Key media).
- Measurement centre 30 mm, range ±5 mm, **repeatability 10 µm**, linearity ±0.1 % F.S., temperature characteristic
  0.03 % F.S./°C.
- 655 nm **Class 2**, 1 mW maximum; beam about Ø50 µm at the centre.
- 0-5 V analogue output (100 Ω), plus an NPN output; response time 1.5/5/10 ms.
- Supply 12-24 V DC; ambient **-10 to +45 °C**; IP67.
- **$439.60 at Digi-Key** (1110-3794-ND, **15 in stock**); Mouser 658-HG-C1030 $439.60, 0 in stock. PNP version HG-C1030-P:
  Digi-Key 9 in stock.

It is the benchmark for the DIY sensor: our camera-and-laser setup should approach its 10 µm repeatability over a line instead
of a point, for about a quarter of the price. Its 45 °C rating and 85 g body rule it out for the toolhead. It could be a
bench reference for calibrating the DIY sensor, if one is ever bought.

## 5. Integration notes for the build candidate (v11.1 + v12)

### 5.1 Eddy Duo: Klipper config (USB to the Pi 5)

Based on BTT's `vendor_docs/BTT_Eddy_sample-bigtreetech-eddy.cfg` and the current Klipper Config_Reference. BTT's sample still
uses `z_offset:`, but current mainline requires `descend_z:`. Fill in the serial path and offsets from the bracket design.

```ini
[mcu eddy]
serial: /dev/serial/by-id/usb-Klipper_rp2040_eddy-if00   # from ls /dev/serial/by-id
restart_method: command

[temperature_sensor btt_eddy_mcu]
sensor_type: temperature_mcu
sensor_mcu: eddy
min_temp: 10
max_temp: 100

[probe_eddy_current btt_eddy]
sensor_type: ldc1612
i2c_mcu: eddy
i2c_bus: i2c0f
descend_z: 0.5
x_offset: 0          # coil centre relative to the nozzle, from the bracket model
y_offset: 34.5       # placeholder: E2B position; recompute from the coil centre (9.05 / 11.33 mm in the BTT drawing)
#tap_threshold:      # from PROBE_EDDY_CURRENT_TAP_CALIBRATE; needs [stepper_z] position_min: -1

[temperature_probe btt_eddy]
sensor_type: Generic 3950
sensor_pin: eddy:gpio26
horizontal_move_z: 2
calibration_bed_temp: 80       # our maximum safe bed temperature
calibration_extruder_temp: 160
extruder_heating_z: 50

[stepper_z]
endstop_pin: probe:z_virtual_endstop   # if the probe homes Z (bootstrap per Eddy_Probe.md); or keep the current Z endstop
#position_min: -1                      # only if tap is used

[bed_mesh]
horizontal_move_z: 2
mesh_min: ...        # from the probed area in the design
mesh_max: ...
probe_count: 9, 9
algorithm: bicubic
```

Commissioning order:
1. `LDC_CALIBRATE_DRIVE_CURRENT CHIP=btt_eddy` at 20 mm.
2. `PROBE_EDDY_CURRENT_CALIBRATE CHIP=btt_eddy` (paper test).
3. `Z_TILT_ADJUST` (three Z screws).
4. `BED_MESH_CALIBRATE METHOD=scan HORIZONTAL_MOVE_Z=1`.
5. `TEMPERATURE_PROBE_CALIBRATE PROBE=btt_eddy TARGET=<max coil temp seen>`.
6. Then try `PROBE_EDDY_CURRENT_TAP_CALIBRATE TAP=guess / refine / verify`, with the nozzle at 150-160 °C (not hot enough
   to mark the PEI) and a hand on M112.

The start macro then follows ROADMAP's "heat the bed, soak, then probe", which PRINTER_V11 already asks for.

### 5.2 Eddy Duo: wiring and mount

- **USB (chosen):** the Eddy Duo's 4-pin 1.5 mm-pitch lead (5 V, D-, D+, GND; BTT manual 4.15) to a Pi 5 USB port. The Pi 5
  then has the nozzle camera and the Eddy on USB, and the two Camera Module 3s on CSI.
  - Do not use the stiff 2.5 m stock cable through the drag chain. Make up a high-flex 4-core lead, like the nozzle camera
    (igus chainflex CF130 class, as V12_PLAN uses for flexing signal runs; pin the exact part when the loom is drawn), with
    the mating 1.5 mm-pitch housing (JST ZH class; confirm the exact header from the STEP or the board).
  - Keep it away from the stepper leads (BTT: route apart, and do not coil the slack; use figure-8s).
- **CAN (fallback, if USB proves noisy on the moving loom):** 5 V, GND, CAN-H and CAN-L to the Octopus V1.1's CAN connection, as
  drawn in BTT manual 4.16. The Octopus must then run Klipper as a USB-to-CAN bridge. That is more firmware work, so it is
  not the first choice.
- **Mount (new fabricated part, replacing the E2B L):**
  - The probe face sits 2.5 mm above the nozzle tip.
  - Hold the probe by its two Ø3.15 holes (10.5 mm pitch) with M3 through-bolts, nuts and washers.
  - Use a printed PETG holder, or a printed spacer of at least 5 mm between the probe's back and any aluminium. The coil
    should not see a metal plane close behind it (TI layout rule, section 1.4).
  - The electronics end faces away from the hotend.
  - Place the coil centre for the smallest Y offset the toolhead allows. With tap for Z zero, the offset matters only for
    mesh coverage.
  - Run the clearance check against the Roto, the blower duct and the camera bracket, and the heat check against the 60 °C
    rating.
  - CAD: `vendor_cad/staging/BTT_EDDY.STEP.gz` (maker STEP). Gunzip it into `vendor_cad/inbox/` with a sidecar when the
    design adopts it. It is 48 MB unzipped, so consider a reduced copy as was done for the SKR board.

### 5.3 Laser: wiring

- Supply 5 V (inside the 3-6 V range), 80 mA.
- Switch it with Klipper so G-code measurement macros control it. Either:
  - (a) a Pi GPIO through Klipper's host MCU (`[mcu host]`, `serial: /tmp/klipper_host_mcu`) driving the **PN2222A** NPN
    already on the v12 list as a low-side switch: 1 kΩ base resistor, about 2.5 mA from the GPIO, laser between the Pi's 5 V
    and the collector; or
  - (b) a spare Octopus GPIO through the same transistor stage, from the Octopus 5 V rail.

```ini
[output_pin nozzle_laser]
pin: host:gpio17          # example; pick a free Pi GPIO
value: 0
shutdown_value: 0
```

- A macro `LASER_ON` / `LASER_OFF` brackets each capture, and dims the COB lights for laser frames
  (`SET_PIN PIN=nozzle_laser VALUE=1`).
- Add a surge-protected supply (Quarton's advice): a small series resistor (about 10 Ω) and a TVS or a 100 nF + 10 µF
  decoupling pair at the module end. Pin the parts when the loom is drawn.
- Route the leads with the camera cable. Never clamp the brass body in metal.

### 5.4 Mounts and BOM lines to add to the build candidate

| SKU (proposed) | Maker / MPN | Qty | Seller | Status |
|---|---|---|---|---|
| PROBE-BTT-EDDY-DUO | BIGTREETECH Eddy Duo | 1 | BIQU US store (us.biqu.equipment), $38.99 (search) | maker drawing and STEP in hand; price/stock/ship-from to confirm (browser agent); replaces PROBE-OMRON-E2B |
| LASER-QUARTON-VLM-520-56-D30-F10 | Quarton VLM-520-56 LPO-D30-F10 | 1 | Digi-Key 100-VLM-520-56LPO-D30-F10-ND, $98.40, 3 in stock | datasheet and outline drawing to fetch (section 7); Class 1M: owner's decision (2.2) |
| (printed) Eddy holder / spacer | fabricated (PETG, print service) | 1 | Hubs / Protolabs | new part; replaces the E2B bent L |
| (printed) laser clamp | fabricated (PETG, print service) | 1 | Hubs / Protolabs | new part; insulating, rotatable |
| laser driver | PN2222A + 1 kΩ (already on the v12 list) + decoupling | 1 set | Digi-Key | pin in the electrical BOM |
| high-flex 4-core lead for the Eddy | igus chainflex CF130 class + 1.5 mm-pitch housing | 1 | Digi-Key / igus | pin when the loom is drawn |

## 6. Short answers

| Question | Answer |
|---|---|
| Eddy probe | **BTT Eddy Duo**, $38.99, BIQU US store: mainline Klipper `[probe_eddy_current]`, coil thermistor with `[temperature_probe]` drift calibration, USB to the Pi 5 (CAN to the Octopus possible), maker drawing, STEP and Octopus V1.1 wiring in hand. Replace the E2B; mount 2.5 mm above the tip; check the 60 °C rating. |
| Works over spring-steel PEI on aluminium? | Yes. The 0.4 mm steel is the target and is many skin depths thick; Beacon recommends at least 400 µm of steel, and our sheet is exactly that. Not for magnets embedded in the plate (ours is a uniform magnetic sheet under the steel). |
| Contact mode | Mainline Klipper `tap` (any LDC1612 probe; to be proven); Beacon Contact and Cartographer touch are the vendor equivalents. |
| Laser | **Quarton VLM-520-56 LPO-D30-F10**, green 520 nm, 30° fan, focused at 10 cm, 3-6 V, Ø10 mm, $98.40 at Digi-Key (3 in stock). **Class 1M**: the owner must accept it with the stated controls. |
| Expected height resolution | About 14-27 µm per pixel; about 2-6 µm ideal with sub-pixel fitting; speckle floor about 4 µm; **about 5-10 µm real on opaque surfaces, 10-30 µm on translucent plastics**. |
| Geometry | Vertical laser sheet from the side of the hotend (about 45 mm up, 38 mm along the line), line 6-10 mm from the tip on the camera's side, perpendicular to the camera plane; out of the plume and the cooling jet. |
| Industrial reference | Panasonic HG-C1030: 10 µm repeatability, 30 ± 5 mm, Class 2, $439.60 at Digi-Key (15 in stock). |

## 7. What the owner's browser agent must fetch

Save each file into `vendor_docs/` with the maker prefix shown, and CAD into `vendor_cad/`. Read each site's terms first, at
customer pace.

1. **BTT Eddy Duo price, variant, stock and ship-from** (US warehouse?):
   `https://us.biqu.equipment/products/bigtreetech-eddy`. Also BTT's wiki page for the Duo's own figures (coil temperature
   rating, any coil diameter, CAN pinout): `https://global.bttwiki.com/Eddy.html`. Micro Center's Eddy USB V1.0 price:
   `https://www.microcenter.com/product/686800/eddy-usb-v10`. Save as `BTT_Eddy-Duo_page_<date>.pdf`.
2. **Quarton datasheets** (outline drawing, line width at distance (Table B), operating temperature, housing potential, laser
   label), from the URLs Digi-Key gives:
   - VLM-520-56 30°:
     `https://www.quarton.com/uploadfiles/1028/product/Green-line-laser-modules/Super-fine-line-in-1meter/VLM-520-56-D30-series/Green-Line-Laser-Module-VLM-520-56-30%C2%B0-Manual.pdf`
     → `Quarton_VLM-520-56-D30_manual.pdf`
   - VLM-520-56 5°:
     `https://www.quarton.com/uploadfiles/1028/product/Green-line-laser-modules/Super-fine-line-in-1meter/VLM-520-56-D5-series/Green-Line-Laser-Module-VLM-520-56-5%C2%B0-Manual.pdf`
   - VLM-635-56 20°:
     `https://www.quarton.com/uploadfiles/1028/product/Red-line-laser-modules/Super-fine-line-in-1meter/VLM-635-56-D20-series/Red-Line-Laser-Module-VLM-635-56-20%C2%B0-Manual.pdf`
   - VLM-635-57 45° (TTL):
     `https://www.quarton.com/uploadfiles/1028/product/Red-line-laser-modules/Super-fine-line-in-1meter-TTL/VLM-635-57-D45-series/Red-Line-Laser-Module-VLM-635-57-45%C2%B0-Manual.pdf`
   - VLM-650-23 (Ø5 mm mini):
     `https://www.quarton.com/uploadfiles/1028/product/Red-line-laser-modules/Small-Size/VLM-650-23-LPO/Red-Line-Laser-Module-VLM-650-23-manual.pdf`
   - VLM-520-28 and VLM-650-28 (economy):
     `https://www.quarton.com/uploadfiles/1028/product/Green-line-laser-modules/Economic/VLM-520-28-LPT/Green-Line-Laser-Module-VLM-520-28-Manual.pdf`,
     `https://www.quarton.com/uploadfiles/1028/product/Red-line-laser-modules/Economic/VLM-650-28-LPT/Red-Line-Laser-Module-VLM-650-28-Manual.pdf`
   - Ask Quarton (contact@quarton.com) whether a Class 1 or Class 2 version of the -56 line exists, and for a STEP model of the
     Ø10 mm body.
3. **Beacon RevH** (alternative): quickstart (mounting height), FAQ (steel thickness, magnetic beds), models (dimensions,
   temperature rating, mount drawings/STEP), contact (force, nozzle temperature):
   `https://docs.beacon3d.com/quickstart/`, `https://docs.beacon3d.com/faq/`, `https://docs.beacon3d.com/models/`,
   `https://docs.beacon3d.com/contact/`. US price and stock:
   `https://www.fabreeko.com/products/beacon-rev-h-eddy-current-surface-scanner-contact-probe` and Beacon's own store at
   `https://beacon3d.com/`. Save as `Beacon_RevH_*`.
4. **Cartographer V4** (alternative): `https://docs.cartographer3d.com/` (dimensions, coil temperature, touch, mounting height,
   STEP) and the maker store at `https://cartographer3d.com/` (price, ship-from, shipping cost to the US). Klipper forum thread
   on running it from mainline: `https://klipper.discourse.group/t/cartographer-v3-v4-reverse-engineering/25018`.
5. **TI documents** (copies from ti.com for provenance; the datasheet is already in hand via Seeed):
   `https://www.ti.com/lit/ds/symlink/ldc1612.pdf`; "LDC Sensor Design" `https://www.ti.com/lit/an/snoa930c/snoa930c.pdf` (coil
   size vs range; confirm the revision letter); "LDC Target Design" `https://www.ti.com/lit/an/snoa957a/snoa957a.pdf` (target
   thickness vs skin depth; confirm the revision letter); EVM guide `https://www.ti.com/lit/ug/snou135a/snou135a.pdf`.
6. **Seeed Grove LDC1612 wiki** (only if the bench experiment is wanted):
   `https://wiki.seeedstudio.com/Grove-2-Channel_Inductive_Sensor-LDC1612/` (reference clock, coil size).

## 8. Files added in this pass

- `vendor_docs/Klipper_Eddy_Probe_page_2026-11-20.html`: klipper3d.org Eddy_Probe page as read.
- `vendor_docs/BTT_Eddy_Series_User_Manual_20250507.pdf`: maker manual (Eddy, Eddy Coil, Eddy Duo; Octopus V1.1 wiring), from
  github.com/bigtreetech/Eddy at commit 4e8ebf2 (2025-08-20).
- `vendor_docs/BTT_Eddy_dimensions.jpg`: maker dimension drawing and coil centre.
- `vendor_docs/BTT_Eddy_sample-bigtreetech-eddy.cfg`: maker sample Klipper config.
- `vendor_cad/staging/BTT_EDDY.STEP.gz`: maker STEP (SolidWorks 2023 export, 2024-04-22), gzipped from 48 MB to 14 MB.
- `vendor_docs/TI_LDC1612_LDC1614_datasheet_SNOSCY9A.pdf` and `vendor_docs/TI_LDC_Reference_Coil.pdf`: TI documents as
  published in Seeed's documentation repository.
- `vendor_docs/Seeed_Grove-LDC1612_101020599_size.jpg`: board outline.
- `vendor_docs/Panasonic_HG-C_series_datasheet.pdf`: via Digi-Key media.
- `vendor_docs/Quarton_VLM-635-27-series_datasheet_DigiKey-link-for-VLM-650-27-LPT-10.pdf`: Digi-Key's datasheet link for the
  VLM-650-27 LPT-10 serves the VLM-635-27 series sheet; kept under its true content name.
- `vendor_docs/Quarton_VLM-635-27-LPA_manual.pdf`: the Class I far-focus line, for the class comparison.
- `vendor_docs/Adafruit_1057_line-laser_datasheet.pdf`: Class IIIa, excluded; kept as the record.
- `out/sourcing_cache/`: live distributor records for the recommended and reference MPNs.
