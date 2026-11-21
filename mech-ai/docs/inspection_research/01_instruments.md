# Inspection research 01: instruments and methods (accuracy, cost, automation)

Researcher 1 of 3, 2026-11-21. Scope: which instruments and methods can measure mechloop's parts well enough for the loop
to learn from them, at what cost, and how far each can be automated (driven by the printer, loaded by the planned robot arm,
or read straight into `mechloop/inspect/`). Companion to docs/INSPECTION.md (today's kit: calipers, square, feeler gauges,
flatbed scanner with printed dot-grid target).

Notation used throughout:
- **[claim]** = manufacturer or seller specification.
- **[indep]** = independently measured (paper, lab, or reviewer with a reference artefact).
- **[est]** = my engineering estimate from first principles, to be checked by our own gauge study.
- Prices are US street prices found in November 2026 searches; they move, so treat them as +/-30 %.

Network note: the full text of the key 2026 scanner benchmark (ISPRS, Kersten et al.) could not be fetched from this
session (isprs-archives.copernicus.org is not in the allowed hosts); only its abstract and search snippets are used.

## 1. The yardstick: how good must the instrument be?

The usual metrology rule is that the measuring system's uncertainty should be 1/10 of the tolerance band (1/4 is
the practical floor, the "4:1 test uncertainty ratio"). For our parts that means:

| Part / feature | Tolerance (band) | Instrument uncertainty needed (10:1 / 4:1) |
|---|---|---|
| SendCutSend laser-cut edge, hole position | +/-0.13 mm (0.26) | 0.026 / 0.065 mm |
| Bend-to-edge, flange length | +/-0.38 mm (0.76) | 0.08 / 0.19 mm |
| Bend angle | +/-1 deg (2 deg) | 0.2 / 0.5 deg |
| CNC 6061 features | +/-0.05-0.13 mm (0.10-0.26) | 0.010-0.026 / 0.025-0.065 mm |
| FDM prints (size, holes) | +/-0.1-0.3 mm | 0.02-0.06 / 0.05-0.15 mm |
| Bed flatness, rail parallelism (assembly) | typically 0.05-0.1 mm over 200-300 mm | 0.005-0.01 / 0.012-0.025 mm |

But mechloop's purpose is slightly different from pass/fail inspection: it wants to estimate **bias** (e.g. "SCS holes come
out 0.05 mm small") from n >= 3 parts. Averaging helps random error, not instrument bias, so the instrument must be
*calibrated* (traceable to gauge blocks/pins) more than it must be *precise*. The flatbed+target pipeline already follows
this idea. Consequence: a cheap instrument plus a good reference artefact often beats an expensive instrument used blind.

## 2. Contact instruments

### 2.1 Calipers, micrometers, height gauges (with data output)

| Instrument | Accuracy | Price | Data out | Notes |
|---|---|---|---|---|
| Mitutoyo 500-196-30 Digimatic caliper, 150 mm | +/-0.02 mm [claim, Mitutoyo spec]; real-world operator repeatability 0.01-0.03 mm [est], dominated by jaw force and alignment | ~$213-260 ([eBay](https://ebay.com/itm/395800335028), [Mitutoyo EU promo 2026](https://mitutoyo.eu/application/files/1117/7493/7849/PRE_1278_-_Spring_Promotion_2026_WEB.pdf)) | Digimatic SPC port | Industry reference; IP67 variants take U-WAVE. |
| iGaging Absolute Origin caliper, 150 mm | +/-0.02-0.03 mm (0.001 in) [claim]; reviewers note errors at low battery ([Machinist Guides](https://machinistguides.com/igaging-absolute-origin-digital-caliper-review/)) | ~$70-78 ([Newegg](https://www.newegg.com/p/0AF-037S-007B4), [Zoro](https://zoro.com/igaging-6-ip54-digital-caliper-absolute-origin-100-700-06-100-700-06/i/G003077747)) | SPC; USB cable sold separately ([Grizzly T27465](https://www.grizzly.com/products/igaging-spc-usb-cable-and-control-box-for-t27455-64/t27465), [Penn Tool](https://www.penntoolco.com/igaging-cable-data-connect-100-700-usb)) | Good value; absolute encoder (no re-zero). |
| $20 generic caliper | ~0.03-0.05 mm [est] | $20 | 4-pin 1.5 V serial behind cover, 24-bit frame ([MIT serial_caliper](https://bio.cba.mit.edu/davepreiss/serial_caliper/-/tree/ecce57b9cfcc36f693092f87d2a359d520b932b8), [Robot Room](https://robotroom.com/Caliper-Digital-Data-Port.html)) | Fine as a fixture-mounted sensor, not as the reference. |
| Mitutoyo 293-340-30 micrometer 0-25 mm | +/-1 um [claim, Mitutoyo spec] | ~$180-325 ([Finditparts](https://finditparts.com/t/21895/manufacturer/mitutoyo), older promos $178-183) | SPC | Stock thickness, pin/shaft OD, print wall thickness. The only hand tool here that meets 10:1 for CNC parts. |
| iGaging 35-630 height gauge 300 mm | +/-0.04-0.05 mm (0.002 in) [claim] | ~$200-410 ([Penn Tool](https://www.penntoolco.com/igaging-12-digital-height-gauge-w-absolute-origin-35-630/), [Zoro](https://zoro.com/igaging-absolute-origin-height-gage-0-12-35-700-h12-35-700-h12/i/G303077515)) | SPC (some models) | With surface plate: flange heights, hole heights on bent parts, print heights. |
| Mitutoyo QM-Height 350 mm | 7 um [claim] | ~$5,000-5,600 ([Selectum](https://selectumllc.com/i/mitutoyo-518-241), [KBC](https://www.kbctools.ca/itemdetail/1-808-64PKA129A)) | Yes | 2D height gauge (can probe bores); out of budget for now. |

**Getting data out (the autonomy metric).** Each caliper reading typed by hand is one manual step plus a transcription
risk. Options:
- Mitutoyo U-WAVE: transmitter ~$218-250 ([TestEquity](https://www.testequity.com/product/10139372-264-620), [Zoro](https://www.zoro.com/mitutoyo-wireless-transmitter-mitutoyo-32ft-264-624/i/G002015474/)) plus USB receiver ~$110-140 ([TEquipment](https://www.tequipment.net/Mitutoyo/series_mitutoyo-u-wave-data-management/)). It types into any focused field as a keyboard ([Transcat brochure](https://www.transcat.com/media/pdf/U-WAVE.pdf)), so it works with the existing inspect form unchanged.
- DIY: a Raspberry Pi Pico/RP2040 reading the Digimatic SPC port (open driver: [CircuitPython-mitutoyo](https://github.com/vifino/CircuitPython-mitutoyo); protocol notes [pcbheaven](https://pcbheaven.com/exppages/Digital_Caliper_Protocol/), [Hackaday 2024](https://hackaday.com/2024/07/17/digitally-reading-a-micrometers-output)) acting as a USB HID keyboard or serial device. ~$10 plus a $15-30 Digimatic cable. This fits the project ethos (the loop builds its own instrument interfaces) and can tag each reading with the balloon number the form is asking for.
- A foot switch on the DIY reader removes the "press DATA" hand movement.

**Automation potential.** Calipers are hand tools; a robot arm cannot use one well. But the *encoder* inside a cheap
caliper or a digital indicator is an excellent sensor for a printed fixture (see 2.6). Micrometers and height gauges
likewise become fixture sensors.

### 2.2 Dial and test indicators, surface plate, height stand

- Granite surface plate 12x18 in Grade B (flatness ~0.0002 in = 5 um over the plate [claim, Fed. spec GGG-P-463c]):
  $70 sale to $130 for imports ([Grizzly G9651](https://www.grizzly.com/products/grizzly-12-x-18-x-3-granite-surface-plate-no-ledge/g9651),
  [Penn Tool Precise](https://penntoolco.com/precise-black-granite-surface-plate-grade-b-12-x-18-x-3), [Zoro HHIP](https://www.zoro.com/hhip-18-x-12-x-3-granite-surface-plate-grade-b-ledge-0-4401-0012/i/G2512914/)),
  $270-300 for Mitutoyo/Starrett with certificate ([Transcat Starrett 85017](https://transcat.com/tru-stone-starrett-g-85017-85017-85017),
  [Selectum Mitutoyo 517-941](https://selectumllc.com/i/mitutoyo-517-941)). The plate is the datum for almost every
  measurement of a bent or printed part (flatness, warp, flange height, squareness). Highest value per dollar in this report.
- Dial test indicator (lever), 0.01 mm graduation, e.g. Mitutoyo 513-404-10E ~$120-130 ([Mitutoyo promo PDFs](https://www.crossco.com/wp-content/uploads/2018/09/Mitutoyo-Fall-Promo-2018-Web-Version.pdf));
  digital plunger indicators with SPC exist from iGaging ([Zoro](https://zoro.com/igaging-absolute-indi-digital-indicator-0-050-125mm-range-000005-reading-35-950-12-35-950-12/i/G703077566)).
  Repeatability of a decent indicator is a few um [claim]; the stand's rigidity is usually the limit.
- Uses: print warp (sweep the part on the plate), bed flatness and rail parallelism (indicator riding on the printer's own
  carriage), sheet flatness, bend squareness against a square or angle plate.

**Automation.** An SPC digital indicator mounted on the printer toolhead, with the part on the bed or on a reference
plate, turns the printer into a slow 1-D-probe coordinate machine: G-code steps over a grid and logs indicator + axis
position. Errors are dominated by the printer's own Z and XY errors (belt/leadscrew, typically tens of um [est]), so it is
good for *differences* (warp, flatness relative to a reference plate scanned in the same session) rather than absolute size.

### 2.3 Gauge blocks, pins, rings: the calibration references

- Pin gauge set 0.061-0.250 in, class ZZ (+/-0.0002 in = 5 um): imports ~$70 ([Penn Tool Precise](https://www.penntoolco.com/precise-061-250-minus-class-zz-steel-pin-gage-set-303-503m1/), [eBay HFS](https://www.ebay.com/p/1937816895));
  Vermont Gage with NIST-traceable certificate ~$230 ([Zoro](https://www.zoro.com/vermont-gage-pin-gage-set-minus-0061-0250-in-black-901200400/i/G3196977));
  Meyer ~$270 ([Transcat](https://transcat.com/meyer-gage-company-m-1m-minus-pin-gage-set)). Metric sets (1-6 mm, 0.01 mm step) exist at similar prices.
  Pins are the best way to measure laser-cut and printed **holes**: calipers under-read small holes (jaw tip geometry)
  and the scanner sees only the bottom edge of the hole. Go/no-go with pins gives the functional diameter (largest
  inscribed cylinder through the full thickness), which is what a screw or dowel actually experiences, including laser
  taper and print elephant's foot.
- Gauge blocks (grade 2/B, 81- or 47-piece imports ~$100-200 [est from typical listings]): calibrate calipers, the scanner
  target scale, the telecentric camera, a 3D scanner and any printer-based probing. One 25/50/100 mm block trio plus a
  ring gauge is the minimum.
- Thread plug gauges (go/no-go, M3/M4/M5 6H, ~$20-60 each [est]): for tapped holes in CNC parts and heat-set/printed
  threads. Cheap and fully functional.
- Bore gauges / telescoping gauges: only needed for CNC bores >= 8 mm (bearing seats). A telescoping gauge set + the
  micrometer (~$30-60 [est]) is enough until there are many bearing bores; a 3-point bore micrometer is $300+.

### 2.4 Go/no-go and printed functional gauges

This is the most "mechloop-native" idea in the report. Instead of measuring every dimension, the printer makes a gauge
that encodes the *function*: a plate with pins at the mating part's hole pattern (laser-cut part must drop on), a slot of
the minimum flange length, a cradle that only accepts a 90 +/- 1 deg bend, a hole-pattern template with the mating
screws. Accuracy of a printed gauge is the printer's (+/-0.1-0.2 mm [est]) unless it holds precise inserts (ground dowel
pins, pin gauges, gauge blocks) at the critical datums, in which case the print only needs to be stiff and the inserts
carry the accuracy. Pass/fail data is coarse but cheap, fast, robot-friendly (a robot can try to place the part onto the
gauge and sense success with a switch or the camera), and directly answers "will it assemble". Recommend: a printed
"assembly gauge" for every Build 1 sheet part that mates with another part, generated from the CAD by `mechloop`.

### 2.5 Touch-probe CMMs: bought, used, DIY

- Used manual/DCC bridge CMMs show up at $3,000-6,000 (e.g. Brown & Sharpe Micro-Hite DCC at $5,500 on eBay and a 2012
  Micro-Hite 3D at $4,899 from a dealer, per [search of listings](https://surplusrecord.com/listing/brown-sharpe-micro-hite-3d-4-5-4-coordinate-measuring-machine-22-x-23-tesastar-probe-2012-1100461/)).
  Accuracy when calibrated: a few um [claim, class typical]. Downsides: 100-500 kg granite, often needs clean compressed air
  for air bearings, temperature control, software licences (PC-DMIS etc.) that may not transfer, controller repairs.
  Not recommended before the loop is producing parts weekly.
- New "manual video CMM" starts around $11,500 ([eBay listing](https://ebay.com/itm/173883247281)) - above budget.
- DIY: a touch probe on the printer or arm. Hobby probes like the Hallmark ITTP are reported at a few um repeatability
  (anecdotal, [Hackaday comments](https://hackaday.com/2022/01/05/a-simple-touch-probe-made-with-basic-tools));
  printed kinematic probes exist ([MostlyPrintedProbe](https://github.com/Stutchbury/MostlyPrintedProbe)); building one
  precise enough needs machined parts and a Renishaw-style stylus ([Fab Academy project](https://fabacademy.org/2022/labs/cpcc/students/garrett-nelson/projects/touch_probe/)).
  The probe is never the limit; the machine carrying it is. A belt CoreXY has tens-of-um position error [est] that is
  partly systematic and can be mapped with a ball plate or gauge blocks. Expect 0.03-0.05 mm absolute after mapping [est] -
  good enough for bend-to-edge, prints and laser-cut hole positions at 4:1, not for CNC parts.
  This is a natural loop project ("the loop improves its own measurement tool"), but should come after the printer runs.
- Printer bed probes (Beacon, Cartographer eddy probes) quote ~0.5 um *resolution* [claim], no published repeatability
  ([Voxel Matters](https://www.voxelmatters.com/beacon-the-worlds-first-ultra-rapid-surface-scanner-for-3d-printers/),
  [DREMC](https://store.dremc.com.au/blogs/news/cartographer-v4-vs-beacon-h-3d-printer-eddy-probes)); Klipper's own
  check treats a 25 um spread as poor ([Klipper probe calibrate](https://www.klipper3d.org/Probe_Calibrate.html)).
  For bed flatness, an eddy probe *is* the instrument (dense mesh), but it should be checked once against a dial indicator.
  Eddy probes also sense aluminium sheet, so the same probe could map flatness of a laser-cut plate lying on the bed [est].

## 3. Optical 2D

### 3.1 Flatbed scanner (current)

Literature: a modified flatbed reached +/-0.05 mm on slip gauges against an optical measuring machine
([Strathclyde, Desktop Scanner Based Metrology](https://strathprints.strath.ac.uk/36540/3/Desktop_Scanner_Based_Metrology.pdf),
[Divis et al. 2015](https://strathprints.strath.ac.uk/51140/1/Divis_etal_MVMP2015_Desktop_scanner_metrology.pdf)) [indep];
errors are systematic (S-shaped across the sensor, periodic along the travel from drive-wheel runout) and largely removable
with a grid calibration ([IMEKO 2015](https://imeko.org/publications/wc-2015/IMEKO-WC-2015-TC14-307.pdf),
[Iowa State JTMAE](https://iastatedigitalpress.com/jtmae/article/14157/galley/12921/view)) [indep].
Our dot-grid target already corrects scale; extending it to a full 2D distortion map (fit a smooth field to all dots, not
just scale) is cheap and is what the papers recommend. Remaining limits [est]:
- It sees one face only, through the glass, and only the bottom edge of every hole and contour. Laser-cut taper/dross,
  print elephant's foot and burrs are therefore measured at the worst edge.
- CIS scanners (most cheap ones) have ~1 mm depth of field and perspective that varies along the sensor; tall or bent
  parts lose focus and cast shadows. CCD (photo/film) scanners such as the Epson V600/V850 class have more depth of field.
- The printed paper target is itself the reference; paper swells with humidity (0.1-0.3 % [est]). A glass or
  photo-plotted film target, or a laser-cut stainless/aluminium dot plate measured once against gauge blocks, is better.
- Realistic: ~0.03-0.05 mm after a full-field calibration, 0.05-0.1 mm with scale-only correction [est consistent with the papers].
  That meets 4:1 for laser-cut parts and prints, not CNC.
- Automation: a robot can place a flat part on glass, but lid handling is awkward; a backlit station is easier (3.2).

### 3.2 Backlit silhouette with a telecentric lens (optical-comparator style)

The silhouette of a part on a collimated backlight, through a telecentric lens, has magnification independent of height
(within the depth of field) - so part thickness, bends and slight non-flatness stop mattering
([Edmund Optics, Advantages of telecentricity](https://www.edmundoptics.com/resources/application-notes/imaging/advantages-of-telecentricity/),
[Quality Magazine](https://www.qualitymag.com/articles/98660-precision-in-optical-metrology-telecentric-vs-endocentric-imaging)).
With subpixel edge detection and calibration, labs report sub-micron error on mm-scale fields
([Tianjin Univ. paper, 0.84 um over 2.1 mm](https://www.researching.cn/ArticlePdf/m00006/2015/35/8/0815002.pdf)) [indep];
for our field sizes:
- 0.1x lens with ~90 mm field: Avantier AVTLC-0042 listed at $750 (2024) or $1,900 (later catalogue)
  ([Avantier stock sheet](https://avantierinc.com/wp-content/uploads/2024/03/Stock-Telecentric-Lenses_AV051-2312A.pdf),
  [Avantier catalogue](https://avantierinc.com/wp-content/uploads/2024/12/AVT-Telecentric-Lenses.pdf)); Edmund TitanTL/GoldTL
  0.06-0.08x lenses cover 100-240 mm but cost more ([Edmund 0.08x GoldTL](https://www.edmundoptics.in/p/008x-goldtlt-telecentric-lens-mount-included/47360/)).
- With a 12-20 MP machine-vision camera (~$300-700 [est]) the pixel is ~20-25 um on a 90 mm field; edge-fit repeatability
  ~2-5 um and accuracy ~10-20 um after calibration with a glass grid or gauge blocks [est]. That is 10:1 for laser-cut parts
  and 4:1 for most CNC features in-plane.
- Larger parts than the field: move the part (or camera) on the printer's XY and stitch using a fiducial grid in the
  backlight plate, so stitching accuracy comes from the grid, not the belts.
- Also measures bend angle and inside radius from the end profile (part stood on end in the beam), which is the
  "later step" INSPECTION.md describes, done properly.
- Cost of a DIY station: lens $750-1,900 + camera $300-700 + collimated/LED backlight $50-400 + printed/extruded frame. ~$1,200-3,000.
- Automation: excellent. The robot drops a part on the backlight, the camera fires, the existing `scan.py` fitting code
  (DXF registration, hole/edge fitting) carries over almost unchanged because the image is a clean binary silhouette.
- A non-telecentric alternative (good macro lens, camera far away, ~$300) has height-dependent scale of ~0.1 % per mm
  of height at 1 m working distance [est]; acceptable for flat sheet if the lens distortion is calibrated, poor for bent parts.
- Used benchtop optical comparators: $650-5,400 asking ([Surplus Record listings](https://surplusrecord.com/listing/16-starrett-vb400-benchtop-optical-comparator-250-mm-x-travel-150-mm-y-travel-90-kg-load-capacity-1084191/));
  new Starrett ~$27,700 ([Zoro](https://www.zoro.com/starrett-optical-comparator-he400-m2e-sp/i/G816293327)). Manual
  readings, heavy, hard to automate; the DIY telecentric station is the better fit for an automated loop.

### 3.3 USB microscope

$30-300. Useful for inspection *images* (layer defects, burrs, dross, bend cracking on the outside radius, thread form) and
small features (<5 mm) with a calibrated stage micrometer slide. Not telecentric, shallow depth of field; dimensional
accuracy ~0.01-0.05 mm only on features within one field [est]. Good per-part photo record and future defect classifier
training data; easy to mount on the printer toolhead (already planned as the "nozzle camera").

## 4. 3D methods

### 4.1 Structured-light and laser-line desktop/handheld scanners

| Scanner | Claimed accuracy | Price | Independent evidence |
|---|---|---|---|
| Revopoint MINI 2 | 0.02 mm precision, 0.05 mm single-frame accuracy [claim] ([Revopoint](https://global.revopoint3d.com/pages/support-mini2)) | ~$800-1,000 ([MatterHackers](https://www.matterhackers.com/store/l/revopoint-mini-2-3d-scanner/sk/MSXSSYRM)) | No reference-artefact test found; forum users report accuracy improved with software updates ([Revopoint forum](https://forum.revopoint3d.com/t/mini-2-accuracy-check/25187)) and some find 0.05 mm "unobtainable" ([forum](https://forum.revopoint3d.com/t/0-05mm-accuracy-seems-unobtainable/10782)). |
| Revopoint MetroX (blue laser lines + structured light) | 0.01 mm precision, 0.03 mm accuracy; volumetric 0.025 + 0.05 mm/m [claim] ([CNX](https://www.cnx-software.com/2024/11/04/revopoint-metrox-3d-scanner-blue-laser-scanning-breakthrough-at-an-appealing-price/), [Revopoint](https://global.revopoint3d.com/en-au/products/3d-laser-scanner-metrox)) | ~$1,100-1,250 | Reviewer gauge-block scan "within 0.03 mm, most within 0.01 mm" ([PrinterTech Lab](https://duqira.github.io/revopoint-metrox-3d-scanner-review-professional-cad-design)) [indep-ish, reviewer]. **ISPRS 2026 benchmark against a ZEISS ATOS 5 reference: both Revopoint scanners (MetroX, Pop 3 Plus) "show low accuracy and exhibit systematic deviations"; low-cost scanners are less stable under varying conditions** ([Kersten et al. 2026](https://isprs-archives.copernicus.org/articles/XLIX-B1-2026/263/2026/)) [indep]. |
| Revopoint MetroY / Pro / Ultra | 0.02 mm (Ultra 0.015 mm) [claim] ([Revopoint](https://global.revopoint3d.com/pages/metroy-ultra-metrology-solution)) | ~$1,300-2,500 ([MatterHackers](https://www.matterhackers.com/store/l/revopoint-metroy-3d-scanner/sk/MJ0ZST38)) | CNC Kitchen comparison (second-hand summary): MetroY Pro and Raptor Pro both ~+/-0.02-0.03 mm ([Geeky Gadgets](https://www.geeky-gadgets.com/creality-raptor-pro-vs-revopoint/)); users report noise on ceramic gauge blocks ([forum](https://forum.revopoint3d.com/t/need-help-with-metro-y-ultra-cmm-scanner-accuracy/43389)). |
| Creality CR-Scan Otter | 0.02 mm at 60 mm distance [claim] ([Creality wiki](https://wiki.creality.com/en/3d-scanner/cr-scan-otter/tutorial)) | ~$900 ([B&H](https://www.bhphotovideo.com/c/product/1833196-REG/creality_cr_scan_otter_portable_3d.html)) | Hands-on reviews, no artefact numbers ([Digitec](https://www.digitec.ch/en/page/cr-scan-otter-3d-scanning-is-easy-with-a-little-practice-43083)). |
| Creality Raptor / Raptor Pro | 0.02 mm blue laser (0.1 mm NIR) [claim]; Raptor Pro volumetric 0.02 + 0.08 mm/m [claim] | ~$1,000-1,700 ([Creality](https://store.creality.com/ca/products/cr-scan-raptor-3d-scanner), [Micro Center](https://www.microcenter.com/product/700140/raptor-pro-3d-scanner)) | The Gadgeteer's caliper check: "great in theory, not so great in reality" ([review](https://the-gadgeteer.com/?p=481335)); Hackster notes precision is not accuracy ([review](https://www.hackster.io/news/the-maker-s-toolbox-creality-raptor-pro-3d-scanner-review-b3dfd160afa9)). |
| Shining3D EinScan SP V2 (turntable desktop) | <=0.05 mm single shot [claim] ([Shining3D](https://www.shining3d.com/professional-solutions/desktop-3d-scanner/einscan-sp-v2)) | ~$2,000-2,500 [est, check] | Reviews only, no CMM comparison found ([3D Tech Valley](https://www.3dtechvalley.com/einscan-sp-v2-review/)). |

Reading of the evidence:
- "0.02 mm" figures are single-frame precision (noise) or best-case accuracy at the sweet-spot distance. Accuracy of a
  finished, aligned mesh against a reference is consistently worse and has systematic components. My working figure for
  sub-$2,000 scanners on 50-200 mm parts: **0.05-0.1 mm** surface deviation, worse on edges and holes [est]. Verify with our
  own artefact (a gauge block, a ball pair at known spacing, a printed step block measured with the micrometer).
- Holes, sharp edges and thin flanges are where they are weakest: meshes round off edges and fitted hole diameters are
  biased by point spacing (0.05-0.2 mm). Don't use them for laser-cut hole diameters; pins or the backlit camera are better.
- Bare aluminium needs scanning spray (vanishing sprays, e.g. AESUB, ~$30-50/can [est]); PLA/PETG mostly scan untreated
  except glossy black or translucent.
- Where they win: **shape** - print warp, overall distortion vs CAD (colour deviation map), bend angles by fitting planes
  to the two flanges (plane fits average thousands of points, so angle uncertainty ~0.1-0.2 deg on 30 mm flanges [est],
  well inside 4:1 for +/-1 deg), flange lengths, twist of bent parts, and later freeform arm parts.
- Data: all export STL/PLY/OBJ point clouds or meshes; inspection can be done in our own Python (Open3D: ICP to the STEP
  tessellation, plane/cylinder fits) or CloudCompare, so no paid inspection software is needed.
- Automation: a turntable scanner (EinScan SP or Revopoint with its turntable) is the one form a robot can drive: place the
  part, trigger the scan via the vendor software (scripting/APIs are limited [est]; may need UI automation). A handheld
  scanner held by the arm is possible but adds motion error; the fixed-scanner + turntable + arm-presents-part layout is better.

### 4.2 Laser-line triangulation profilometers

Industrial 2D laser profilers (Keyence LJ-X, Micro-Epsilon scanCONTROL, Gocator) give ~5-20 um repeatability [claim class]
but cost $5k-15k+ new [est]; used units appear for less. A DIY line laser + camera on the printer gantry is the cheap
version (the ROADMAP already lists a line laser for phase 3): ~0.02-0.05 mm height resolution over a small field [est].
Good for bed flatness, first-layer height, print surface defects and sheet flatness; the printer's gantry is the scanning axis.

### 4.3 Photogrammetry

Coded-target photogrammetry reaches "tenths of a mm, up to hundredths with a high-end setup" on a DSLR
([ProQuest paper](https://www.proquest.com/docview/2636122296)); absolute accuracy is set by the scale bar
([PhotoModeler](https://www.photomodeler.com/pm-kb/getting-the-highest-possible-accuracy/)). For 50-300 mm parts, expect
~0.05-0.2 mm with a calibrated camera, coded targets and a gauge-block scale bar [est]. Zero hardware cost beyond a camera,
and the arm can move the camera through a fixed path - but it is slow, needs good texture or targets, and is beaten by a
$1,000 structured-light scanner for our part sizes. Worth it later for assembled machines (rail alignment over 300+ mm)
using targets on the rails.

### 4.4 CT scanning as a service

- Industrial CT gives full internal + external geometry: voids, layer adhesion, infill, wall thickness inside prints,
  porosity, hidden threads. Accuracy on plastic parts is typically 10-50 um depending on voxel size [est].
- Prices: Zeiss service quoted ~$400-700 per plastic part ([Plastics Technology](https://ptonline.com/articles/ct-scans-see-inside-plastic-parts));
  outsourced scans ~$519 each in a cited comparison ([Keyence guide](https://www.keyence.com/blog/industrial-ct-scanner-guide-what-it-is-who-needs-it-and-how-to-choose-the-best-system.jsp));
  university micro-CT ~$250-500 per scan up to 4 h for external users ([McGill fee structure](https://www.mcgill.ca/iqbi/equipmentnavigation/xraymicroscopy/xradia/fee-structure));
  Lumafield sells a subscription from $75,000/year, not per-scan ([Lumafield Neptune](https://www.lumafield.com/products/neptune-industrial-x-ray-ct-scanner)).
  Many parts fit in one scan volume, so batching coupons cuts per-part cost.
- Use: occasional ground truth (a few times per process change): scan a batch of print coupons and one reference part of
  each process, and use the result to calibrate the cheap everyday methods. Loop time days to weeks; zero autonomy.

## 5. Flatness and angle tools

| Tool | Accuracy | Price | Best for |
|---|---|---|---|
| Engineer's square + feeler gauges (current) | ~0.1-0.3 deg on a 30 mm flange [est] (0.05 mm feeler step / 30 mm = 0.1 deg) | have | Bends; works, but slow and manual. |
| Digital angle gauge (Wixey WR300) | +/-0.2 deg accuracy, +/-0.1 deg repeatability [claim] ([Woodcraft](https://www.woodcraft.com/products/wixey-wr300-type-2-digital-angle-gauge)); Woodsmith test within 0.1 deg [indep] ([Woodsmith](https://www.woodsmith.com/article/versatile-digital-angle-gauges-worth-a-look-wixey-digital-protractor/)); one forum comparison found 0.1 deg disagreement ([Shopsmith forum](https://forum.shopsmith.com/viewtopic.php?p=194888)) | ~$40 | Bend angle: zero on the plate-resting flange, read the other. Meets 4:1 for +/-1 deg. Small flanges (<25 mm) are hard to seat. |
| Sine bar + gauge blocks + indicator | ~0.01 deg [est] | $50-150 | Reference to check the angle gauge and to qualify a bend gauge. |
| Precision straightedge + feelers | 0.01-0.02 mm over 300 mm (grade dependent) [est] | $50-200 | Rail straightness, sheet flatness. |
| Surface plate + indicator on stand | few um [est] | see 2.2 | Warp, flatness of parts < plate size. |
| Printer eddy probe mesh / indicator on toolhead | see 2.5 | have / $40 | Bed flatness, rail parallelism (indicator on carriage riding the other rail), gantry squareness via a reference square. |
| Electronic level / inclinometer (0.02 mm/m class) | [claim class] | $100-300 | Frame level and twist of assembled printer/arm. |

## 6. Suitability matrix

Rating: ++ = recommended primary method, + = usable, - = poor, x = not applicable. "Auto" = can be loaded/driven by the
printer or arm without a human (A = arm loads it, P = printer drives it).

| Method | Laser-cut flat | Bent sheet | CNC 6061 | FDM prints | Assemblies | Auto |
|---|---|---|---|---|---|---|
| Caliper (with SPC) | + | + (flanges) | - (marginal) | ++ | + | no (data yes) |
| Micrometer | + (thickness) | + (thickness) | ++ | + (walls) | x | no |
| Height gauge + plate | + | ++ | + | ++ | + | no |
| Test indicator + plate | + (flatness) | + | + | ++ (warp) | ++ | P (on toolhead) |
| Pin / thread gauges | ++ (holes) | ++ (holes) | ++ | ++ (holes) | x | A possible (insertion test) |
| Printed functional gauge | ++ | ++ | + | ++ | ++ | A |
| Flatbed scanner + target | ++ | + (one flange) | - | + (bottom face) | x | awkward |
| Telecentric backlit camera | ++ | ++ (profile, angle, radius) | + (in-plane) | + (outline) | x | A, P (stitch) |
| USB microscope | + (burr, dross) | + (cracks) | + (finish) | + (layer defects) | x | P |
| Structured-light scanner | - (holes) | ++ (angles, twist) | - | ++ (warp, shape) | + | A (turntable) |
| Touch probe on printer | + | + | - (machine error) | + | + | P |
| Used CMM | ++ | ++ | ++ | + | x | partial (DCC) |
| CT service | - | - | + | ++ (internal) | x | no |
| Digital angle gauge | x | ++ | + | + | + | no |
| Eddy probe / line laser on gantry | + (flatness) | x | x | + (surface) | ++ (bed) | P |

## 7. Recommended kits by budget

All tiers keep the existing flatbed scanner and square/feelers. The guiding principle: buy **references** (plate, pins,
blocks) first, because they make every cheap instrument trustworthy; buy **automatable** instruments second; buy
expensive hand instruments last.

### Tier 1 (~$300): references + digital data

| Item | ~Price |
|---|---|
| Granite plate 12x18x3 Grade B (import) | $70-130 |
| iGaging Absolute Origin 150 mm caliper | $70 |
| DIY SPC-to-USB reader (RP2040 + cable + foot switch) | $30 |
| Pin gauge set 0.061-0.250 in ZZ minus (import) or metric 1-6 mm | $70 |
| Digital angle gauge (Wixey WR300) | $40 |
| Dial test indicator + magnetic base (import) | $40 |
| Radius gauge set (have or $15) | - |
| **Total** | **~$320-400** |

Plus free upgrades: full-field distortion map for the scanner target; a laser-cut aluminium dot target (order with the
Stage 0 SendCutSend parts, then measure it once against the caliper/pins) to replace paper; printed functional gauges for
each Stage 0 part. Covers Stage 0 sheet parts at 4:1 for bends and flanges, holes by pins, flat outlines by scanner.

### Tier 2 (~$1,500): add a micrometer, height gauge and the automatable 2D station

Tier 1, plus:

| Item | ~Price |
|---|---|
| Mitutoyo 500-196-30 caliper (reference; iGaging becomes the fixture/shop caliper) | $215-260 |
| Mitutoyo 0-25 mm micrometer (SPC) | $180-320 |
| iGaging 300 mm height gauge with SPC | $200-410 |
| Gauge block set, grade 2 (import) + 1-2 ring gauges | $120-200 |
| Thread plug gauges M3, M4, M5 | $60-150 |
| Telecentric lens 0.1x (Avantier-class) + 12 MP machine-vision camera + LED backlight + printed frame | $1,100-1,500 (the dominant cost; can be phased: start with a non-telecentric macro setup ~$300) |
| **Total** | **~$1,500 if the telecentric station is built with the cheaper lens price or phased; ~$2,300 with everything** |

If only ~$1,500 is available, prefer the telecentric backlit station over the Mitutoyo caliper/height gauge: it is the
one instrument that meets 10:1 for laser-cut parts, measures bends from the end profile, reuses `scan.py`, and is
arm-loadable (directly improves the autonomy metric).

### Tier 3 (~$5,000): add 3D shape, probing and occasional ground truth

Tier 2, plus:

| Item | ~Price |
|---|---|
| Structured-light / blue-laser scanner with turntable (Revopoint MetroX/MetroY class or Creality Raptor Pro) + scanning spray | $1,200-1,800 |
| Calibration artefacts for 3D: ball bar / ball plate, step block; validate the scanner on our parts before trusting it | $100-300 |
| Certified Mitutoyo/Starrett Grade B plate (if the import plate is uncertified) | $270-300 |
| U-WAVE (2 transmitters + receiver) or more DIY readers for every SPC gauge | $100-600 |
| Touch probe for printer/arm (used Renishaw TP20-class or ITTP-class hobby probe) + ball plate for mapping | $300-600 [est] |
| Sine bar, precision straightedge, electronic level | $250-500 |
| CT service budget: 2 batched scans of print coupons + one CNC part | $500-1,000 |
| **Total** | **~$5,000** |

Not recommended at any of these budgets yet: a used bridge CMM (logistics, air, software) and a new optical comparator.
Reconsider a used CMM if CNC parts become a large share of iterations, since nothing else here reaches 10:1 on +/-0.05 mm.

## 8. Recommendations for the inspection design (beyond buying things)

1. **Run a gauge study first.** Before trusting any instrument's numbers in the ledger, measure a set of reference
   artefacts (gauge blocks, pins, a laser-cut master measured with the best instrument available) 10x each by each method
   and record bias and repeatability in `mechloop` as an instrument record. Learnings should carry the instrument's
   uncertainty, and the "propose" rule should require mean deviation > 2x *combined* (instrument + sample) uncertainty.
2. **Measure functional dimensions with functional tools.** Hole diameter by pin (largest pin that passes), hole pattern
   by a printed gauge with dowel inserts, bend by angle gauge or plane fit. These answer "will it assemble" directly.
3. **Make instruments loop outputs.** The printer can make the telecentric station frame, fixtures that hold a cheap
   caliper/indicator as a sensor, functional gauges and robot-friendly nests. Each is a part the loop can improve.
4. **Prioritise automatable stations for the arm.** A backlit telecentric station and a turntable 3D scanner are the two
   instruments the arm can load; hand tools stay for spot checks and calibration.
5. **Treat 3D scanner accuracy claims as unverified** until our own artefact test; the 2026 ISPRS benchmark found
   systematic deviations in Revopoint units, and none of the "0.02 mm" claims has an independent reference-artefact
   confirmation in the sources found.
