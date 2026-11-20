STATUS: partial (interim — items 1, 3, 4, 12 resolved; remaining items in progress)

# REQ-008 results — priority queue

Interim result landed early so an interruption never leaves the folder empty. Item states are updated as work completes. Where an item was already delivered in an earlier request's folder, that is stated instead of duplicating the file.

## Stage 1
1. Schurter DD11.0114.1111 / 4301.1401 / 0001.2513 / 0001.2511 — DONE. 7 files in this folder, all official schurter.com downloads: DD11.0114.1111__cad.step (family model) + DD11.0114.1111__datasheet.pdf (typ_DD11), 4301.1401__cad.step + 4301.1401__datasheet.pdf (typ_Fusedrawer_2), 0001.2513__cad.step, 0001.2511__cad.step (fuse STEPs are surface geometry, official as-is), SPT-5x20__datasheet.pdf (covers both fuses).
2. Finder 22.32.0.120.4320 STEP — REQ-006 delivered findernet.com series STEP 2232_xx20 (recorded as 2NO outline match). REQ-008 says the earlier file was the wrong part (auxiliary block); re-verifying against the official source.
3. Phoenix Contact 1119897 (PLC-RSC-5DC/21) — DONE. 1119897__cad.stp (official Creo export, 2 solids) + 1119897__datasheet.pdf (official product-details PDF generated from phoenixcontact.com online catalog) in this folder.
4. StepperOnline 17E19S1684AB4-330RA full datasheet — BLOCKED. The direct PDF link and the whole stepperonline.com / files.omc-stepperonline.com domain sit behind a Cloudflare challenge that returns an interstitial page instead of the PDF; no alternate official source. Not retried further without a genuinely new source.
5. Bed heater + magnetic PEI kit — REQ-003 items 1-2 state: item 1 had only 1 stock candidate of 2-3 requested, item 2 only 1 of 2 candidates (sold out); pending further research.
6. JST XH STEPs — pending.
7. Molex Mini-Fit Jr 39-01-2020 — see REQ-002 item 21 state; pending.
8. Harwin R30-6700694 + spacer lengths near 5.5/6.1/9.725/13.2/40 mm — REQ-006 item 5 delivered the official drawing DRG-02007; STEP blocked on TraceParts portal access. Spacer-length research pending.
9. Century Spring DJ-8X20YCS — REQ-002 item 21 partial; pending.
10. DIN rail Phoenix NS 35/7.5 — pending.
11. PEM S-M3-0ZI — PEM account approval still pending (watched); 3Dfindit/Bossard route is CADENAS (exhausted).

## Stage 2
12. HIWIN MGNR12R-300 + MGN12H STEP — delivered via the REQ-005 results folder (REQ-005 item 2): MGNR12R-300__cad.step (rail, 1 solid) + drawing PDF, and MGN-12-H-1R0300-ZF-H-M__cad-block-rail-assembly.step (official block+rail assembly STEP containing the MGN12H block geometry; explicitly labeled as an assembly, not a per-part block file). See REQ-005 RESULT.md item 2 for full provenance and the MGN12C generator-defect note.
13. LDO MGN12H rail+carriage US sellers — pending.
14. Misumi GT2 20T 9mm 5mm-bore pulley/idler — part-number research possible; CAD blocked (Misumi registration rejected; 3Dfindit is CADENAS, exhausted).
15. Gates 2MGT 9mm open belt — REQ-003 item 3 delivered Gates LL2MR09 (9396-0052) page; datasheet pending.
16. TMC2209 datasheet — pending (Trinamic/ADI).

## Stage 3
17. Accelerometer board CAD/drawing — pending.
18. Arducam UVC nozzle camera candidates — pending.
19. Pi 5 camera cable 22-to-15 — REQ-006 item 2 partial (no official drawing exists; reseller SKUs recorded).
20. 24 V COB LED strip CRI 90+ + channel — pending.

## REQ-008b-updates (worked 2026-11-19)

Items 1-2 (item 4 photo + item 16): skipped per REQ-008b, already done by owner.

Item 3 - Schurter DD11.0124.1111 (new part): DONE. Two files added to this folder:
- DD11.0124.1111__cad.step - official schurter.com STEP (AP214, 1 solid, ~3 MB), fetched via Schurter's own CAD download flow for the exact order number.
- DD11.0124.1111__datasheet.pdf - copy of the typ_DD11 series datasheet. 2-pole confirmed two ways: the series datasheet variant table lists the line "2-pole none illuminated green ... DD11.0124.1111", and the product page text reads "IEC Appliance Inlet C14 with Line Switch 2-pole, Fuseholder 1- or 2-pole".
US distributor price/stock (Digi-Key, checked 2026-11-19): DD11.0124.1111 = Digi-Key 486-1286-ND, $28.36 qty 1 (price breaks $24.10 @10, $22.59 @25, $21.51 @50, $20.49 @100), not stocked, Manufacturer Standard Lead Time 16 weeks. Digi-Key also lists DD11.0123.1111 (486-1284-ND, $28.04 qty 1, 108 in stock) - a different order number (switch variant), recorded for reference only, not a substitute. Mouser product page was inaccessible (bot-protection block).

Item 4 - cartridge (no-leads) STEP check for 0001.2513 / 0001.2511: NO ACTION, per the REQ's fallback. Schurter's official CAD entries for these exact order numbers offer only pigtail STEP geometry (0001-2511-pt.stp / 0001-2513-pt.stp, already in this folder as 0001.2511__cad.step / 0001.2513__cad.step). No plain-cartridge STEP exists for 2511/2513 (some other ratings, e.g. 0001.2514, do have plain cartridge STEPs). Owner will model the cartridge from the datasheet as stated in the REQ.

Item 5 - Phoenix 1119897 alternative/newer CAD check: NO ACTION, per the REQ's fallback. The product page's CAD download offers a single model with a format picker only - no newer version, no variant including the base element. The delivered 1119897__cad.stp (92.6 mm deep vs 94 mm datasheet depth) remains the only official CAD for the exact part number. The relay base PLC-BSC-5DC/21 (item 2980225) is a separate product with its own CAD; Phoenix offers no combined module+base assembly CAD.
