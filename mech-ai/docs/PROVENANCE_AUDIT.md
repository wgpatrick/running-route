# Provenance audit: what is still "from memory" (2026-11-19/20)

Scope: every part and figure the printer design (printer_v11, and the v12 parts in `docs/V12_PLAN.md`) rests on that
is recalled, typical, proxy, unverified, estimated, generic, a stand-in, or read from search snippets. Sources of
truth read: the catalogue (`mechloop/parts/*.py`, `mechloop/parts/vendor/*.json`), the v11 verify report
(`out/printer_v11/report.json` of 2026-11-19 20:03: BOM, `unverified_parts`, `geometry.vendor_cad`), the v10_1 BOM
provenance (`docs/build/printer_v10_1/bom.csv`; no v11 build package exists yet), the verifiers and physics code,
`mechloop/twin/*.json`, `mechloop/shops/*.json`. The grep of the brief (`recalled|from memory|not fetched|unverified|
typical|assumed|estimate|stand-in|proxy`, supplier_rules excluded) gives 549 lines in 76 files; many are the same
figure repeated or the word "proxy" meaning "simulation solid". They are grouped below into items.

Rules applied (docs/DESIGN_GUIDELINES.md): supplier CAD first; a re-make only if faithful to the maker's drawing;
otherwise a stand-in, reported as such; stock sizes. Key rule (owner, 2026-11-19): every off-the-shelf part is a real,
orderable product (maker, MPN, seller, stock size), geometry from the maker's CAD or a faithful re-make of its
drawing, ratings from its datasheet; only parts we fabricate may be generated; placeholders are allowed while
designing but must be named `PLACEHOLDER-...`, coloured, listed, and reported as errors.

Status words: **fixed** (real source now in hand, this fetch), **fetch now** (reachable, done or doable here),
**owner's agent** (login wall, bot refusal, robots.txt disallows us: exact page in the last section), **standard
purchase** (paid standard), **measure on arrival**, **design decision** (no real part at the size the design uses).

Reachability found (2026-11-19): reachable and permitted: api.digikey.com (v4), api.mouser.com, api.element14.com,
mm.digikey.com (Digi-Key-hosted copies of maker PDFs and CAD), github.com (anonymous git reads), www.sdp-si.com,
www.cantherm.com, www.semitec-global.com, www.igus.com, www.keenovo.com, www.findernet.com (pages only; its
cdn.findernet.com is refused by the proxy), www.omc-stepperonline.com (pages only), www.delta-fan.com,
www.pololu.com, www.bossard.com. Refused by the proxy: files.omc-stepperonline.com, cdn.findernet.com,
pip.raspberrypi.com (where datasheets.raspberrypi.com redirects), media.digikey.com, www.mouser.com,
www.farnell.com, traceparts.com, e3d-online.com, bigtree-tech.com, omron (ia/components/download), vishay,
te.com, nexperia, panduit, harwin, RAF. The site itself refuses bots (HTTP 403 at its edge): schurter.com,
jst-mfg.com, littelfuse.com, phoenixcontact.com, misumi-ec.com, accu.co.uk, gates.com, raspberrypi.com, pemnet.com
(202 challenge, empty body), molex.com (stream reset). robots.txt disallows our user agent (ClaudeBot): mcmaster.com,
hiwin.tw / hiwin.com. Those all go to the owner's agent.

## Summary

Counted by rows of the tables below (one row may cover several SKUs of one family).

| class | rows | fixed this fetch (source in hand) | data already held, apply in Phase 3 | owner's agent | standard purchase | measure on arrival | design decision | keep as labelled assumption / acceptable as is |
|---|---|---|---|---|---|---|---|---|
| (a) purchased parts | 37 | 5 (TCO, FHCS-M4x40, NUT-M3-NYLOC, Octopus CAD, connectors partly: XHP-2 + FASTON CAD) | 3 (EXT2020 mass/Ixx, THUMBNUT from KIPP STEP, LRS-350 STEP) | 19 | 0 | 1 primary (E3D inductance/thermal) + 5 also after purchase | 3 (GT2 pulleys/idlers, 12 mm belt, spacer lengths) | 6 (faithful re-makes, low impact, not in v11) |
| (b) engineering constants | 27 | 2 partly (ISO 10642 M4, ISO 10511 M3 from McMaster STEPs) | 1 (Hiwin friction) | 7 | 6 (+ rest of 10642/10511) | 0 | 1 (rail accuracy class) | 9 (incl. Bossard torque, already sourced) |
| (c) twin parameters | 12 | 0 | 0 | 0 | 0 | 12 | 0 | 0 |

"Fixed" means the real source is now in `vendor_docs/` or `vendor_cad/staging/provenance_2026-11-19/` with its figures
quoted in that folder's `MANIFEST.md`. Nothing has been written into the catalogue yet: Phase 3 waits until
printer_v11 is finished (at the time of writing `docs/PRINTER_V11.md` still has 19 `{{` placeholders and there is
no "printer_v11 ..." finishing commit).

## Top 15 by impact

Impact = does a check or a dimension of the design depend on it, and how badly could it be wrong.

| # | item | class | where | what depends on it | status / what was done |
|---|---|---|---|---|---|
| 1 | Bed thermal cut-off TCO-133C-15A: "SEFUSE SF-E class ... recalled", no maker, no part number | a | `mechloop/parts/electrical.py:378-396` (`thermal_fuse`) | mains-safety check (heater runaway), electrical BOM | **fixed (source)**: Cantherm RT series sheet in hand (RT128: Tf 128, fusing 124±2, Th 98 / 113 UL, Tm 200, 15/16 A 250 VAC; RT134: Tf 134, Th 104/119; body Φ4 x 14, leads Φ1). No DC rating on the sheet. v12 plan already replaces it with Cantherm CS712025Y (120 °C NC bimetal, 10 A at 24 V DC: sheet in hand). Catalogue change waits for Phase 3 |
| 2 | Lead-screw nut NUT-T8x2-POM-AB-17E19S1684AB4: every dimension estimated from photographs | a | `mechloop/parts/batch10.py:96-123`, `vendor/stepperonline_17e19_ab4.json:62-81` | Z carriage nut seat, bed support stiffness | **owner's agent**: `https://files.omc-stepperonline.com/17E19S1684AB4-330RA_Full_Datasheet.pdf` (link read from the maker's product page; host refused here). Then measure on arrival |
| 3 | Z motor + integral screw 17E19S1684AB4-330RA: rotor inertia, mass, screw length above face assumed from the sister model | a | `mechloop/parts/batch7.py:22-110` | motor sizing, Z travel and screw-length fit | **owner's agent**: same datasheet PDF |
| 4 | Linear guides MGN12 rail / MGN12H block: CAD is the FreeCAD community model swept to length; sideways stiffness assumed equal to radial; preload class Z0 assumed | a + b | `mechloop/parts/__init__.py:209-273`, `verifiers/bed_support.py:11,549-553`, `verifiers/ratings.py:13-16` | guide-load and stiffness checks, rail length (stock sizes) | real part found: Digi-Key (Midwest Machine Tool) HIWIN `MGN-R12-R300-HM` 125 USD, 100 in stock; `MGN-R12-R220-HM` 125 USD, 100; block `MGN-12-H-Z0-HM` 59 USD, 70 (also -Z1-HM). Datasheet link is midwestmachinetool.com (refused). Hiwin CAD: **owner's agent** (hiwin robots.txt disallows us). Catalogue figures already from Hiwin's MG catalogue (`vendor_docs/Hiwin_MG_catalogue.pdf`) |
| 5 | GT2 pulleys and idlers 20T 5 mm bore for 9 mm and 12 mm belts: "generic, typical, unverified"; no CAD | a | `mechloop/parts/__init__.py:326-362,452-463` | belt drive, pulley/idler clearances, belt tension checks | **design decision**: SDP/SI catalogue in hand: GT2 9 mm-belt 20-groove pulleys only with 4 or 6 mm bore (A 6A51M020DF0904 / DF0906); no 12 mm GT2 2 mm-pitch belt anywhere stocked (SDP/SI: 3, 6, 9 mm, special widths cut from sleeve; Gates manual the same). See "Real-part replacements" |
| 6 | GT2 belts 9 mm and 12 mm open, by the metre: generic | a | BOM lines GT2-BELT-9MM/12MM | belt stiffness in the twin and the resonance prediction | **design decision** (12 mm), **owner's agent** (Gates 2MGT 9 mm open length: gates.com refuses bots) |
| 7 | Silicone bed heater 192 x 205, 24 V 180 W: "typical, unverified", no maker | a | `mechloop/parts/electrical.py:360-375` | bed heat-up time, power budget, TCO placement | **owner's agent / custom order**: Keenovo (keenovo.com reachable but sells custom sizes through a quote form; no stock 192 x 205). Digi-Key stocks only Thermo Heating Elements wound pads at other sizes. Measure on arrival |
| 8 | Magnetic base + PEI sheet 220 (BED-MAGNET-PEI220-BASE-STANDIN, SHEET-PEI-220): snippets of resellers' listings; base is a hand-made stand-in | a | `mechloop/parts/batch9.py`, `batch10.py:130-140`, `vendor/creality_pei235.json`, `vendor/threedjake_pei257.json` | first-layer stack height, probe target (spring steel thickness), bed max temp | **owner's agent** (reseller pages); measure on arrival |
| 9 | FHCS-M4x40 head dims "recalled from ISO 10642" | a | `mechloop/parts/__init__.py:700-729` (`CSK`) | countersink depth / head below surface on the bed jacks | **fixed (source)**: measured in McMaster's own STEP (`inbox/FHCS-M4x40.step`, 91294A204): head 8.00 dia (catalogue 7.53), height 2.3, key 2.5. Apply in Phase 3 |
| 10 | Spacers: aluminium M2.5 / M3 / M5 (OpenBuilds "seen in search-result snippets", lengths 9.725, 6.1, 13.2, 40, 9 are not stock) and nylon M3 x 5.5 (not a stock length) | a | `mechloop/parts/hardware.py:15-60`, `vendor/openbuilds_spacers.json` | stack heights (bed posts, board standoffs) | real parts with drawings found on Digi-Key (Harwin R30-620xxxx Al, R30-670xxxx nylon, RAF M09xx); lengths must move to stock values: **design decision**, CAD **owner's agent** (harwin.com, TraceParts) |
| 11 | Corner brackets BRKT-2020: community FreeCAD model | a | `mechloop/parts/__init__.py:1001-1020` | frame stiffness, bracket/screw clearances (36 used) | **owner's agent**: Misumi HBLFSN5 CAD (misumi-ec.com refuses bots; the profile and T-nut came through 3dfindit for the owner) |
| 12 | Wire / connector current ratings: JST XH 3 A, VH 10 A "recalled"; screw terminals "typical"; bundle derating IEC 60364-5-52 B.52.17 "recalled"; wire h 12 W/m²K assumed | b | `mechloop/electrical.py:29-43,76-79` | wire-temperature and connector checks (bed and heater runs) | JST XH sheet: **owner's agent** (jst-mfg.com refuses bots; Digi-Key links it there). IEC 60364-5-52: **standard purchase**. v12 moves the bed run to Molex Mini-Fit (data sheet: owner's agent) |
| 13 | TMC2209 RDS(on) 170 mΩ, VS max 29 V "recalled, analog.com not reachable" | b | `mechloop/parts/electrical.py:106-107` | driver dissipation in the bay-temperature check | **owner's agent**: `https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf` (Digi-Key's datasheet link). BTT's module manual (`vendor_docs/BTT_TMC2209-V1.2-manual.pdf`) is already held |
| 14 | Endstop ENDSTOP-MICRO: community switch model on a generated board | a | `mechloop/parts/details.py:280-300`, `__init__.py:474-528` | homing trigger position (switch figures are already Omron's) | real part: Omron (Aratas) D2F-01L, Digi-Key 1.44 USD, 79,881 in stock (v12 plan); D2F-L 2.55 USD. Data sheet re-fetched from Digi-Key (same content as held). CAD: TraceParts via Digi-Key: **owner's agent** |
| 15 | Fastener proof loads (ISO 898-1), clearance holes (ISO 273), tap drills: "typical, unverified" | b | `mechloop/parts/__init__.py:646-654` (`SCREW`), `vendor/iso_fasteners.json:92-97` | screw-load and hole-class checks everywhere | **standard purchase** (ISO 898-1, ISO 273) or a maker's table (Bossard's technical pages are reachable: proof loads per class are on bossard.com; not yet read) |

## (a) Purchased parts, by topic (v11 BOM, ranked within topic)

| part / SKU | what is not sourced | file:line | used for | best real source | status |
|---|---|---|---|---|---|
| TCO-133C-15A | trip/hold/current recalled; no maker | `parts/electrical.py:378` | thermal-runaway check | Cantherm RT128 / RT134 sheet; v12: CS712025Y | fixed (source), Phase 3 |
| HEATER-SIL-192x205-24V-180W | everything | `parts/electrical.py:360` | heat-up, power | maker's quote drawing (Keenovo custom) | owner's agent; measure on arrival |
| BED-MAGNET-PEI220-BASE-STANDIN | everything (hand-made stand-in in the design) | design file | stack height | a real kit's listing (e.g. the one bought) | owner's agent; measure |
| SHEET-PEI-220 | size from snippets; steel thickness third-party | `parts/batch9.py:30-40` | probe target, stack | seller's page | owner's agent; measure |
| NUT-T8x2-POM-AB-17E19S1684AB4 | every dimension estimated from photos | `parts/batch10.py:96` | Z nut seat | 17E19S1684AB4 full datasheet | owner's agent; measure |
| NEMA17-48-LEADSCREW-...-AB4, TR8x2-INTEGRAL-... | inertia, mass, screw length above face, efficiency 0.35 "typical" | `parts/batch7.py:22-110` | motor sizing, Z fit | same datasheet; efficiency: measure | owner's agent |
| MGN12-R-250 / -300, MGN12H | community CAD; ZF/Z0 preload assumed; sideways stiffness assumed | `parts/__init__.py:209-273` | guides | Hiwin CAD (MGNR12R300 / R220, MGN12H) | owner's agent; real parts on Digi-Key |
| GT2-20T-B5 / -W9, GT2-IDLER-20T-B5 / -W9 | generic dims, no CAD | `parts/__init__.py:326-362` | belt drive | SDP/SI or Misumi GPA catalogue | design decision (bore 5 / 12 mm width not stocked) |
| GT2-BELT-9MM / 12MM-OPEN | generic | BOM | twin belt stiffness | Gates 2MGT design manual (held), SDP/SI | design decision / owner's agent |
| EXT2020-* (HFS5-2020) | mass 0.45 kg/m and Ixx 6900 in the simulation solid vs Misumi 0.5 / 7420 | `parts/__init__.py:275-293`, `vendor/misumi_hfs5_2020.json:18` | frame FEA, mass | Misumi catalogue p.2686 (held) | data in hand: apply in Phase 3 (no fetch needed) |
| BRKT-2020 | community CAD, no maker | `parts/__init__.py:1001` | frame | Misumi HBLFSN5 CAD / drawing | owner's agent |
| TNUT-2020-M3/M5 | faithful re-make of Misumi HNTAJ5 drawing; mass, cost unconfirmed | `parts/tslot.py:118` | slot fit | Misumi CAD | acceptable (faithful re-make); mass: measure |
| SPACER-AL-* (5 SKUs), SPACER-NYLON-M3-5x3.3x5.5 | secondary / non-stock lengths | `parts/hardware.py:39-60` | stack heights | Harwin / RAF drawings + CAD | design decision (stock lengths) + owner's agent (CAD) |
| SPACER-NYLON-M2.5/M3 (Pololu) | mass from volume, nylon grade | `parts/hardware.py:51` | mass only | Pololu pages (reachable, held) | low impact |
| NUT-PEM-S-M3-1 | stand-in drawn as an ISO hex nut | `parts/__init__.py:755-771` | sheet nut | PEM S-M3-1ZI (Mouser 0.20 USD, 7,981 in stock); PEM CL data sheet + CAD | owner's agent (pemnet.com bot challenge, mouser.com refused) |
| FHCS-M4x40 | head dims recalled | `parts/__init__.py:700` | countersinks | McMaster STEP in inbox | fixed (measured), Phase 3 |
| NUT-M3-NYLOC | height recalled | `parts/__init__.py:745` | nyloc check | McMaster STEP in inbox | fixed (confirmed 4.0) |
| WASHER-M5-SERRATED | DIN 6797 J sizes recalled, generated ring | `parts/hardware.py:153-173` | earth stud | McMaster or Bossard part + CAD | owner's agent |
| BHCS-FL-M5x8 / x10 (ISO 7380-2) | head figures from distributors' listings, generated | `parts/batch10.py:150-172`, `vendor/iso7380_2.json:11` | 68 frame screws | McMaster flanged button-head M5 STEP | owner's agent |
| SHCS-M2x20, M2.5x20, M3x25, M4x6, M5x16, M5x6, M5x65; NUT-M2, NUT-M5; WASHER-M2 | generated by bd_warehouse (no supplier file) | `parts/details.py`, `vendor/mcmaster_fasteners.json` | fit, display | McMaster STEPs (numbers known for M4x6 90128A208, M5x6 91290A221, NUT-M5 90591A260; others to look up) | owner's agent |
| WASHER-M3-LARGE / M4-LARGE | faithful re-make of Accu HPLW drawings | `parts/hardware.py:138` | bed posts | Accu CAD | acceptable; CAD owner's agent (accu.co.uk refuses bots) |
| THUMBNUT-DIN466-M4 | catalogue figures from a Halder snippet; KIPP STEP is in inbox | `parts/batch8.py:60-75`, `vendor/halder_din466.json` | bed knobs | KIPP K0143.04 drawing (from the STEP's maker) | data in hand from the STEP; record in Phase 3 |
| SPRING-DIE-DJ-8X20YCS | rate etc. from search snippets; coil OD/ID, max temp not sourced | `parts/batch8.py:30-47`, `vendor/century_spring_dj8x20.json:22-24` | bed spring preload | Century Spring page/drawing (STEP held) | owner's agent (centuryspring.com refused) |
| PROBE-OMRON-E2E-X5ME1 + nuts | mass, Al switching distance, repeatability assumed; nuts drawn round | `parts/probes.py:93-188`, `vendor/omron_e2e.json:156-157,326,382,413` | probe checks | Omron sheet (held); E2B-M12KS04-WP-C1 CAD (Digi-Key 35.22 USD, 153 in stock) | owner's agent (download.ia.omron.com 403) |
| ENDSTOP-MICRO | community model + generated board | `parts/details.py:280-300` | homing | D2F-01L CAD | owner's agent |
| FAN-BLOWER-4010-GDB4010 | envelope from the maker's drawing (maker offers no CAD); bearing type unstated | `parts/batch10.py:30-60` | part cooling (v10) | GDSTIME sheet held | acceptable stand-in until replaced; v11 uses Delta BFB0524HH (vendor CAD) for part cooling |
| CTRL-OCTOPUS-V1.1 | no detail model; price typical | `parts/batch6.py:233-257`, `vendor/bigtreetech_octopus_v11.json:48` | bay layout, connector access | BTT's STEP | fixed (STEP staged, V1.0 outline) |
| RELAY-BTT-V1.2 | contact 10 A and supply 0.5 W unverified | `vendor/bigtreetech_relay_v12.json:59-62` | mains switching | BTT repo has no CAD/rating; the relay's own data sheet | v12 replaces with Finder 22.32 + Phoenix PLC-RSC (data: owner's agent) |
| HOST-RPI-ZERO-2W | mechanical record level none; supply current typical | `parts/electrical.py`, `vendor/raspberry_pi_zero2w.json:44-53` | bay | RPi mechanical drawing | owner's agent (pip.raspberrypi.com refused); v12 moves to Pi 5 (STEP fixed) |
| PSU-LRS-350-24 | "mechanical record level: none" in the BOM, though `staging/LRS-350-24.step` and datasheet are held | BOM | bay | Mean Well (held) | data in hand: promote in Phase 3 |
| INLET-C14-SW-FUSE-T8A | order number not pinned | `parts/electrical.py:248` | mains | Schurter DD11.0114.1111 (Digi-Key 17.62 USD, 2,572 in stock) + drawer 4301.1401 (6.23, 34,318) + SPT 0001.2513 (1.09, 41,439) | real part chosen (v12); Schurter sheet/CAD owner's agent |
| FUSE-5x20-T8A | no part | BOM | fuse | Schurter SPT 0001.2513 (ceramic T8A); or Littelfuse 0218008.MXP (glass, Digi-Key 2.48, 9,489) | real part found; sheet owner's agent |
| DIODE-BAT85 | no part | BOM | probe level shift | Vishay BAT85S-TAP (Digi-Key 0.50, 57,921) or Nexperia BAT85,133 | real part found; sheet owner's agent |
| E3D Roto, Revo | phase inductance 11 mH estimated; thermal block capacity/area estimated; lead sleeve scaled | `parts/toolhead.py:19,87,146-211` | extruder drive, heater model | E3D (blocked here) | measure on arrival (inductance, step response) |
| FAN-3010-CG3010U24 | max flow/pressure not one point | `vendor/coolerguys_cg3010u24.json` | hotend cooling | sheet held | low impact |
| E3D V6 (not in v11) | heater block 23 x 16 x 11.5 recalled, mass recalled | `parts/toolhead.py:232-253`, `vendor/e3d_v6.json:128` | not used by v11 | - | not in v11 |
| Wires, ferrules, JST XH, Micro-Fit, Faston, ring lug, Dupont, braided sleeve, cable ties, thread locker | generic class lines, prices "typical" | `parts/electrical.py:564-575` | BOM, cost, wire checks | see "Real-part replacements" | real parts found for most; CAD for XHP-2 and TE 2-520182-2 fixed (staged) |

## (b) Engineering constants used by checks

| constant | value / basis | file:line | used by | best real source | status |
|---|---|---|---|---|---|
| ISO 898-1 proof loads, ISO 273 clearance holes, tap drills | typical | `parts/__init__.py:646-654`, `vendor/iso_fasteners.json:92-97` | screw checks, hole classes | ISO 898-1, ISO 273 | standard purchase (or Bossard technical tables, reachable, not read yet) |
| ISO 10642 head table (M3-M6) | recalled | `parts/__init__.py:700-702` | countersinks | ISO 10642 / McMaster STEPs | M4 fixed from STEP; rest standard purchase |
| ISO 10511 nyloc heights | recalled | `parts/__init__.py:737-740` | nyloc | ISO 10511 / McMaster | M3 confirmed from STEP; rest standard purchase |
| DIN 6797 serrated washer table | recalled | `parts/hardware.py:153` | earth stud | DIN 6797 | standard purchase / supplier part |
| ISO 4035 thin nut 0.5 d (T-nut thread engagement limit) | recalled | `verifiers/interference.py:281`, `vendor/tslot_2020_hardware.json:104` | T-nut engagement check | ISO 4035 | standard purchase |
| ISO 4762 length tolerance js15 | recalled | `vendor/tslot_2020_hardware.json:108` | screw-into-T-nut bottoming | ISO 4759-1 | standard purchase |
| IEC 60364-5-52 bundle derating B.52.17 | recalled | `electrical.py:31` | wire temperature | IEC 60364-5-52 | standard purchase |
| IEC 60947-5-2 switching-distance tolerance ±10 %; probe repeatability 0.01 | recalled / assumed | `electrical.py:1453-1456`, `parts/electrical.py:449-464`, `parts/probes.py:93` | probe check | IEC 60947-5-2; Omron sheet states its own tolerances | standard purchase; repeatability: measure |
| JST XH 3 A / VH 10 A, 5.08 terminal 15 A, PSU barrier 20 A | recalled / typical | `electrical.py:76-79` | connector current | JST sheets; terminal maker | owner's agent |
| Wire surface h 12 W/m²K; motor case h 12 W/m²K; insulation temps | assumed | `electrical.py:29-43` | wire and motor temperature | measure (thermocouple) | keep as labelled assumption |
| Hot-end heat sink capacity/conductances (HEAT_SINK_ASSUMED) | assumed | `electrical.py:1250-1260` | TCO-on-heat-sink check | measure | keep labelled |
| TMC2209 RDS(on), VS max | recalled | `parts/electrical.py:106-107` | driver dissipation | ADI datasheet | owner's agent |
| Board MOSFET output resistance 12 mΩ; MCU pin limit 3.6 V | assumed | `parts/electrical.py:109-115` | heater channel, endstop logic | IPD036N04L sheet; STM32 sheet | owner's agent |
| Steel torque Bossard class 8.8 mu 0.14 | fetched (practice_refs/01) | `verifiers/bearing.py:62` | torque table | - | sourced |
| "Soft" torque for screws into plastic | assumed, no table exists | `verifiers/bearing.py:29,152` | torque in printed joints | test on samples | keep labelled |
| Friction mu ball 0.005, plain 0.15, nut 0.2 | assumed | `verifiers/bed_support.py:73`, `tolerance/__init__.py:15` | tolerance and bed-support | Hiwin catalogue friction section (held) | data in hand (Hiwin); nut: measure |
| Guide block stiffness BLOCK_K 40 N/µm, K_GUIDE 15000 N/mm, sideways = radial, ball gauge 0.45 x width | assumed | `verifiers/ratings.py:13-16`, `tolerance/__init__.py:16`, `bed_support.py:549-587` | stiffness and resonance | Hiwin rigidity tables (held, radial only) | keep labelled (maker publishes none sideways) |
| Nut axial stiffness 10 kN/mm, backlash 0.1, lead accuracy 0.1/300, sync-belt 0.02 | assumed | `verifiers/bed_support.py:71-82` | bed level, backlash | AB4 datasheet (owner's agent), measure | owner's agent / measure |
| Rail accuracy class C | assumed | `verifiers/bed_support.py:74` | bed level | design states the class on order (Digi-Key HM parts) | design decision |
| Rail residual after alignment 0.02 mm | assumed | `tolerance/__init__.py:23` | paired rails | measure | keep labelled |
| Process tolerances (FDM pattern, laser, press brake ±1°) | recalled class values | `tolerance/process.py:25-31`, `tolerance/bends.py:25-44` | tolerance stack-ups | shop's own published tolerances (SendCutSend rules held in `shops/`) | partly sourced; rest owner's agent per shop |
| Belt pulley run-out shop practice | recalled | `verifiers/belts.py:24` | warnings only | - | keep labelled |
| al_mic6 density 2800, nu 0.33; ATP-5 nu | recalled / typical | `model.py:38-43`, `verifiers/fea.py:26`, `vendor/cast_tooling_plate.json:25-27,171` | FEA, mass | Alcoa MIC 6 data sheet (density) | owner's agent (alcoa.com refused) |
| MIC-6 stock thicknesses, flatness/thickness tolerances | recalled | `shops/xometry.json:58-136,415,435`, `vendor/cast_tooling_plate.json:84` | stock-size check, flatness | Alcoa / Vista Metals sheets | owner's agent |
| PETG/PLA printed-part properties (across-layer ratio, cp) | assumed from materials table | `printsettings.py:33-56`, `verifiers/electrical.py:1071` | printed-part FEA, mass | filament maker's TDS | owner's agent (pick the filament) |
| Heat-set insert pilot holes | typical | `verifiers/dfm_rules.py:259` | DFM hint | insert maker's sheet (e.g. Ruthex, CNC Kitchen reachable) | fetch later (low impact: hint only) |
| CNC cost model, laser cost per metre | own assumptions, labelled estimate | `verifiers/dfm_rules.py:265-269`, `manufacture.py:70` | cost estimate only | shop quotes | keep labelled |

## (c) Twin / model parameters

All are measure-on-arrival (Klipper SHAPER_CALIBRATE, pressure-advance test print, PID/step response, bed mesh); none
is a part datasheet figure. Each is already reported as "assumed" by the twin.

| parameter | file:line |
|---|---|
| axis friction 2 / 3 / 5 N | `twin/__init__.py:42` |
| stepper damping ratio (fitted to public data, not this machine) | `twin/__init__.py:47`, `twin/fitted_parameters.json:71,96` |
| extruder melt-flow lag (pressure advance start) | `twin/tuning.py:6,96`, `twin/deposit.py:18` |
| as-built bed surface (tilt, bow) and probe repeatability in the mesh study | `twin/__init__.py:72`, `twin/tuning.py:120-147,328-359`, `cli.py:66` |
| hot-end and bed heater thermal parameters (capacity, bond conductance) | `twin/fitted_parameters.json:192-211,379` |
| Bowden reference tube length (Prusa MINI, recalled) | `twin/fitted_parameters.json:164` |
| reference belt length range (estimated) | `twin/reference.py:44` |
| calibration machines: rotor inertia class values, CAD mass range, factory current recalled | `twin/calibration_machines.json:17,25,49,51` |
| MGN7H block length recalled | `twin/calibration_posthoc.json:5` |
| nozzle exponent (assumed, not fitted) | `twin/fitted.py:78` |
| E3D Roto phase inductance 11 mH | `parts/toolhead.py:19` |
| Revo HeaterCore thermal capacity / area | `vendor/e3d_revo.json:108-113` |

## Purchased parts drawn by a generator (owner: only fabricated parts may be generated)

From `out/printer_v11/report.json` `geometry.vendor_cad.checked` (model kinds: vendor CAD 373 instances, community
CAD 50, generated to standard 261, proxy 60, re-made from drawing 19), plus the parts with no detail model at all.

| SKU (instances) | drawn by | real catalogue item and CAD source |
|---|---|---|
| BHCS-FL-M5x8 (66), BHCS-FL-M5x10 (2) | generated ISO 7380-2 solids | McMaster flanged button-head socket cap screw M5x0.8, 8 and 10 mm, black-oxide alloy steel (number: owner's agent) + its STEP |
| SHCS-M3x25 (6), SHCS-M5x16 (6), SHCS-M5x65 (6), SHCS-M2.5x20 (3), SHCS-M2x20 (2), SHCS-M5x6 (1), SHCS-M4x6 (4) | bd_warehouse ISO 4762 | McMaster 91290A series (alloy steel black oxide): M5x6 91290A221 (recorded, unconfirmed); M4x6 90128A208 (zinc, its STEP is over 5 MB: take the drawing PDF and re-make faithfully, or accept the larger file); others: owner's agent looks up |
| NUT-M5 (4), NUT-M2 (2) | bd_warehouse ISO 4032 | McMaster 90591A260 (M5, DIN 934, already in inbox as NUT-M5-DIN934: the design can call that SKU); M2: McMaster 90591A series (look up) |
| WASHER-M2 (4) | generated ring | McMaster 91166A series M2 (look up) |
| WASHER-M5-SERRATED (1) | generated ring | McMaster internal-tooth lock washer M5 DIN 6797 J (look up) |
| NUT-OMRON-E2E-M12 / -W (1 + 1) | hexagon from Omron's dims | the nut solids inside Omron's own STEP (`inbox/PROBE-OMRON-E2E-X5ME1.step` holds two nut solids, left out today): split them out in Phase 3 |
| NUT-PEM-S-M3-1 (2) | ISO hex nut stand-in | PEM S-M3-1ZI CAD from pemnet.com (owner's agent) |
| TNUT-2020-M3 (33), TNUT-2020-M5 (119) | faithful re-make of Misumi HNTAJ5 drawing | allowed (faithful re-make, drawing recorded); Misumi CAD via 3dfindit would replace it |
| WASHER-M3-LARGE (16), WASHER-M4-LARGE (3) | faithful re-make of Accu HPLW drawings | allowed; Accu CAD optional |
| FAN-BLOWER-4010-GDB4010 (1) | envelope from maker's drawing | maker offers no CAD: stays a reported stand-in (or drop: v11 part cooling is the Delta BFB0524HH with vendor CAD) |
| NUT-T8x2-POM-AB-17E19S1684AB4 (3) | estimated from photographs | StepperOnline datasheet (owner's agent), then a faithful re-make or their CAD |
| GT2-20T-B5 (2), GT2-20T-B5-W9 (1), GT2-IDLER-20T-B5 (2), GT2-IDLER-20T-B5-W9 (1) | simulation solids only | see "Real-part replacements" (design decision) |
| SPACER-AL-* , SPACER-NYLON-M3-5x3.3x5.5 / x8 | simulation solids only | Harwin / RAF stock spacers, CAD via TraceParts or harwin.com (owner's agent) |
| MGN12-R-250 (4), MGN12-R-300 (2), MGN12H (3) | community section swept to length | Hiwin CAD for MGNR12R300 / R220 and MGN12H (owner's agent) |
| BRKT-2020 (36), ENDSTOP-MICRO (2) | community CAD (+ generated board) | Misumi HBLFSN5; Omron D2F-01L CAD (owner's agent) |
| HEATER-SIL, BED-MAGNET base, SHEET-PEI-220, TCO, CONN-*, WIRE-*, CABLE-TIE | no geometry or a plain box | real parts below; CAD where the maker has it (XHP-2 and TE FASTON staged) |

## Real-part replacements

Prices and stock from the distributor APIs on 2026-11-19/20 (Digi-Key v4 unless marked Mouser / element14). "CAD"
says whether the maker publishes it and whether it is in hand.

| BOM line (generic now) | real part (maker, MPN) | seller, price, stock | CAD / drawing | note / design change |
|---|---|---|---|---|
| TCO-133C-15A | Cantherm RT134 (Tf 134, Th 104, 15 A 250 VAC) — nearest stocked: Cantherm RT128 (Tf 128) or RT121 | RT128 Digi-Key 1.08 USD, 4,614; RT121 1.26, 4,203; RT134 not listed at Digi-Key | maker drawing in the sheet (in hand); no STEP | no DC rating; v12 plan's Cantherm CS712025Y (5.38 USD, 427; 10 A at 24 V DC) is the better answer. Trip 128 °C vs a bed run near 100-110 °C: check Th (98 °C) against the bed's maximum before choosing RT128 |
| FUSE-5x20-T8A | Schurter SPT 0001.2513 (ceramic T8A) | Digi-Key 1.09, 41,439 | Schurter CAD (owner's agent) | glass alternative Littelfuse 0218008.MXP 2.48, 9,489 |
| INLET-C14-SW-FUSE-T8A | Schurter DD11.0114.1111 + drawer 4301.1401 | 17.62, 2,572 / 6.23, 34,318 | Schurter STEP (Digi-Key links schurter.com: owner's agent); the DD11 STEP already in inbox is the 0111 variant's | pins the order number |
| DIODE-BAT85 | Vishay BAT85S-TAP (DO-204AH) | 0.50, 57,921 | data sheet owner's agent | Nexperia BAT85,133 (DO-34) also listed, no stock shown |
| ENDSTOP-MICRO | Omron (Aratas) D2F-01L (gold contact, hinge lever) | 1.44, 79,881 | TraceParts via Digi-Key (owner's agent) | the board is the design's own PCB or a printed holder: decide |
| CONN-JST-XH | JST XHP-2 / -3 / -4, SXH-001T-P0.6, B2B-XH-A / B4B-XH-A | 0.10, 186,027 / 0.10, 126,417 / 0.10, 73,645 / 0.024, 1,416,000 / 0.10, 201,823 / 0.17, 50,922 | XHP-2 STEP staged; others: Digi-Key media (owner's agent) | |
| CONN-MOLEX-MICROFIT | Molex 43025-0200, 43030-0001, 43031-0001, 43020-0200 | 0.36, 208,467 / 0.10, 1,334,200 / 0.10, 419,831 / 0.32, 17,309 | molex.com STEP zips (owner's agent) | |
| bed run (v12) | Molex Mini-Fit Jr 39-01-2020 + Mini-Fit Plus HCS 0457503111 | 0.27, 270,631 / 0.17, 95,831 | molex.com | |
| CONN-FASTON-4.8 | TE 2-520182-2 (FASTON 187 fully insulated) | 0.35, 119,251 | STEP + DXF staged | |
| CONN-FERRULE | Phoenix 3200519 (0.75 mm², gray) / 3200014 (0.5 mm², white) | 0.18, 79,050 / 0.18, 256,949 | Phoenix data sheets in hand (dimensions); CAD via TraceParts | |
| CONN-RING-M5, CONN-DUPONT, SLEEVE-BRAIDED-8MM | not searched to a part yet | - | - | open: pick in the next pass (TE / Panduit ring lug; TE AMPMODU or Harwin M20 for "Dupont"; Techflex PTN) |
| CABLE-TIE-100MM | Panduit PLT1M-C (99 mm, 18 lb) | 0.25, 285,661 | Panduit drawing (owner's agent) | |
| WIRE-AWG16..26 | igus CF880-15-02 (2 x 16 AWG, moving bed run), CF130-03-02 (2 x 22 AWG); CNC Tech 3239-20 silicone 20 AWG | 0.81/ft, 3,981 / 1.54/ft, 974 / 1.15/ft, 37,893 | CF130 sheet in hand | CF880 sheet: owner's agent |
| THREADLOCKER-MEDIUM | Loctite 243, 10 ml (Henkel 1329837) | 25.85, 116 | Henkel TDS (owner's agent) | |
| SPACER-AL-M3-6x3.2x6.1 | Harwin R30-6200614 (Ø5 x 6, M3 clearance 3.2, Al) | 0.50, 15,879 | Harwin drawing + TraceParts STEP | OD 5 not 6, length 6 not 6.1: design change |
| SPACER-AL-M2.5-5x2.7x9.725 | RAF M0904-A-25-AL series (Ø4.5, 2.7 ID) | 0.93, 1,975 (6.9 mm length) | RAF cut sheet | 9.725 is not stock: pick 10 mm (RAF/Harwin) |
| SPACER-AL-M5-10x5.1x9 / 13.2 / 40 | RAF M06xx-5-AL round M5 spacers (Ø 10, 5.3 ID; 3, 5, 11, 44 mm listed) | Mouser/Digi-Key, small stock | RAF cut sheet | 9, 13.2, 40 are not stock lengths: design change |
| SPACER-NYLON-M3-5x3.3x5.5 / x6 / x8 | Harwin R30-6700594 (5 mm), R30-6700694 (6), R30-6700894 (8): Ø5, 3.2 ID nylon | 0.69, 21,122 / 0.67, 16,466 / 0.69, 10,089 | Harwin drawing + TraceParts | 5.5 is not stock: use 5 or 6 |
| NUT-PEM-S-M3-1 | PEM S-M3-1ZI | Mouser 0.20, 7,981 | pemnet.com CAD (owner's agent) | v12 note: S-M3-0 where sheet allows (Mouser S-M3-0 not checked) |
| GT2-20T-B5-W9 (9 mm belt) | SDP/SI A 6A51M020DF0906 (20 grooves, 6 mm bore) or DF0904 (4 mm) | SDP/SI (shop.sdp-si.com refused here) | SDP/SI drawing in catalogue (in hand); CAD on their shop | no 5 mm bore in this series: a 5 mm motor shaft needs Misumi GPA20GT2090-B-P5 class (owner's agent) or a different SDP/SI style |
| GT2-20T-B5 / IDLER (12 mm belt) | none: GT2 2 mm pitch is stocked in 3, 6, 9 mm (Gates manual, SDP/SI) | - | - | design change: 9 mm GT2 (two belts if stiffness is short), or GT2 3 mm pitch 9/15 mm (SDP/SI stocks 9 mm and 15 mm 3 mm-pitch pulleys), or HTD 3M 15 mm |
| GT2-IDLER-20T-B5-W9 | toothed idler: Misumi GPA20GT2090-A-N5 class / SDP/SI idler pulley styles (look up) | owner's agent | | |
| GT2-BELT-9MM-OPEN | Gates 2MGT 9 mm open length (Gates 9 mm GT2 by the metre) | owner's agent (gates.com refuses bots) | Gates manual (held) | SDP/SI sells closed loops only |
| HEATER-SIL-192x205 | Keenovo custom silicone heater 192 x 205, 24 V 180 W with 100k thermistor | keenovo.com quote | maker's drawing on order | measure on arrival |
| BED-MAGNET base + SHEET-PEI-220 | a named kit (maker, size, steel thickness) | owner's agent | seller's drawing | measure on arrival |
| MGN12-R-250 / 300, MGN12H | HIWIN MGN-R12-R300-HM / MGN-R12-R220-HM; MGN-12-H-Z0-HM (or -Z1-HM) | Digi-Key 125.00, 100 / 125.00, 100; 59.00, 70 | Hiwin CAD (owner's agent) | Digi-Key's parameter text says "2m Length" for the rails: confirm the length on the order page |
| HOST (v12) | Raspberry Pi 5 8 GB SC1432, Active Cooler SC1148, 27 W PSU SC1153 | 175.00, 19,347 / 5.00, 31,905 / 12.00, 6,881 | Pi 5 STEP staged; cooler/PSU briefs: owner's agent | |
| cameras (v12) | Raspberry Pi Camera Module 3 SC1223 (Digi-Key 25.00, 1,231); HQ Camera SC1220 (50.00); nozzle camera DFRobot FIT0819 USB endoscope (19.90, 240) | | RPi publishes camera mechanical drawings/STEP on raspberrypi.com (owner's agent); DFRobot: no CAD found | |
| accelerometer (v12) | Adafruit 1231 ADXL345 breakout (Digi-Key search 17.50, 104; part-number lookup failed, use the product URL) | | Adafruit publishes board outlines on GitHub (Adafruit-ADXL345-PCB, not fetched) | |
| filament sensor (v12) | BIGTREETECH SFS V2.0 | BTT shop / Amazon | STEP staged (BTT GitHub) | |
| lighting (v12) | Inspired LED 24V-COB-4000K-12M | 1.23 per unit, 3,261 | sheet in hand (8 mm flex) | |
| mains (v12) | Finder 22.32.0.120.4320; Phoenix PLC-RSC-5DC/21 1119897; ST PN2222A | 46.34, 205 / 17.30, 1,407 / 0.04 | Finder STEP `22.stp_-3.zip` and S22 sheet on cdn.findernet.com (owner's agent); Phoenix via TraceParts | |
| bed fuse (v12) | Littelfuse 0297010.WXNV | 0.39, 76,730 | Littelfuse sheet (owner's agent) | |
| bed thermistor (v12) | Semitec 104NT-4-R025H42G | 0.91, 250 | sheet in hand | |

## DG-07 check (sketch, not implemented)

Rule: every `Stock` placed in a design with `cots=True` is either a **real part** or a **placeholder**; a placeholder
is an error in a buildable design ("must be fixed before buying") and a warning while designing.

Catalogue fields required on every purchased `Stock` (new `real_part` record next to `source` and `model`):
`maker`, `mpn` (the maker's orderable number, at the stock size), `seller` (at least one: name, seller part number,
URL, date checked), `stock_size` (what is sold: length, pack), `datasheet` (vendor_docs file + URL), `geometry`
(one of `vendor CAD` with file + SHA-256 + bbox check, `re-made from drawing` with the drawing file and a list of
every drawing dimension used, `none` = placeholder), `ratings_source` ("datasheet p.N" per rating or "none").

Classification per placed part:
- **real**: maker + mpn + seller present, geometry is `vendor CAD` or `re-made from drawing` (faithful: drawing
  recorded, every feature dimensioned), every rating the verifiers read has a datasheet reference, and the length
  or size used equals `stock_size`.
- **real, geometry pending**: real part pinned but its CAD is generated or community → error in buildable mode
  (the owner's rule: no generator for purchased parts), with the fetch instruction from the catalogue.
- **placeholder**: anything else (generic class value, `level` proxy/secondary/partial without the missing fields,
  hand-made stand-in, non-stock length). Error.
- Parts we fabricate (custom sheet / machined / printed) are exempt.

What it changes outside the verifier:
- BOM: a placeholder's SKU is emitted as `PLACEHOLDER-<sku>` with a column `replace_with` (the real part or the
  search that will replace it, from the catalogue's `real_part.candidates`), and the BOM is sorted with
  placeholders first.
- Exported part metadata (`place()` meta and the viewer JSON): `real_part_state: "real" | "geometry pending" |
  "placeholder"`; the viewer and review page colour `placeholder` in a distinct warning colour (e.g. magenta) and
  `geometry pending` hatched, with a legend.
- Design doc and build package: a "Placeholders (must be fixed before buying)" table at the top, generated from the
  check's metrics (SKU, qty, why, replacement or search).
- `mechloop verify` summary: count of placeholders and geometry-pending parts; the design is not "buildable" while
  either is non-zero.

Applied to v11 today it would flag as placeholder: TCO, heater, magnetic base, PEI sheet, AB4 nut, GT2 pulleys and
idlers, 9 / 12 mm belts, spacers with non-stock lengths, PEM nut, BAT85 / fuse / connectors / wire / ties /
threadlocker until pinned, BRKT-2020 (no maker); as geometry pending: generated screws, nuts, washers listed above,
MGN12 rail and block, endstop, Omron nuts, Octopus (until the staged STEP is promoted).

## For the owner's agent

Save every file into the Drive folder **"mechloop supplier CAD batch 3"**, named `<SKU or MPN>__<what>.<ext>` (e.g.
`17E19S1684AB4-330RA__datasheet.pdf`). No login is needed for any item except McMaster (the owner's own account, as
in batch 2026-11-18).

| # | part | where (exact) | save |
|---|---|---|---|
| 1 | StepperOnline 17E19S1684AB4-330RA (Z motor, integral Tr8x2 screw, POM anti-backlash nut) | https://files.omc-stepperonline.com/17E19S1684AB4-330RA_Full_Datasheet.pdf ; product page https://www.omc-stepperonline.com/anti-backlash-screw-nut-nema-17-external-48mm-stack-1-68a-lead-2mm-0-07874-length-330mm-17e19s1684ab4-330ra (STEP if offered) | PDF, STEP |
| 2 | HIWIN MGN12 rail 300 mm and 220 mm, block MGN12H | hiwin.com (or hiwin.tw) 3D CAD download for MGNR12R300, MGNR12R220, MGN12H (Z0); also the Digi-Key/Midwest pages for MGN-R12-R300-HM, MGN-R12-R220-HM, MGN-12-H-Z0-HM (confirm rail length) and the MG catalogue https://midwestmachinetool.com/pub/media/assets/product/documents/MG-Series-Catalog.pdf | STEP, PDF |
| 3 | Misumi 2020 corner bracket HBLFSN5 | us.misumi-ec.com part page (or 3dfindit as for the profile) | STEP + drawing PDF |
| 4 | Misumi GT2 pulley 20 T, 9 mm belt, 5 mm bore (GPA20GT2090-B-P5 class) and toothed idler 20 T 9 mm (GPA20GT2090-A-N5 class) | us.misumi-ec.com configurator | STEP + drawing |
| 5 | Gates 2MGT GT2 9 mm open-length belt | gates.com product page / data sheet | PDF |
| 6 | McMaster: flanged button-head socket screw M5 x 8 and M5 x 10 (black oxide); SHCS M2 x 20, M2.5 x 20, M3 x 25, M5 x 16, M5 x 65 (91290A series), M5 x 6 (confirm 91290A221), M4 x 6 (90128A208 drawing PDF); hex nut M2 (90591A series); washer M2 (91166A series); M5 internal-tooth lock washer DIN 6797 J | mcmaster.com product pages (logged in, as batch 2026-11-18) | STEP per part + part number list |
| 7 | PEM S-M3-1ZI (and S-M3-0ZI) | pemnet.com product page, CAD download and the CL/S data sheet https://www.pemnet.com/fastening-products/self-clinching-nuts/type-s-ss-cls-clss-h-hn/ | STEP, PDF |
| 8 | Omron D2F-01L | Digi-Key D2F-01L page "CAD Models" (TraceParts) | STEP |
| 9 | Omron E2B-M12KS04-WP-C1 2M | https://download.ia.omron.com/download/zip/ST/OEE/E2B_M12KS04_WP_C1/ (Digi-Key Z4126-ND media) | ZIP/STEP |
| 10 | Schurter DD11.0114.1111, drawer 4301.1401, SPT 0001.2513 / 0001.2511 | https://www.schurter.com/cadstep/DD11.0114.1111 , https://us.schurter.com/en/datasheet/typ_DD11.pdf ; Schurter pages for 4301.1401 and 0001.2513 (data sheet + STEP) | STEP, PDF |
| 11 | JST XH series | https://www.jst-mfg.com/product/pdf/eng/eXH.pdf ; STEP for XHP-3, XHP-4, B2B-XH-A, B4B-XH-A, SXH-001T-P0.6 (Digi-Key media or jst-mfg.com) | PDF, STEP |
| 12 | Molex 43025-0200, 43030-0001, 43031-0001, 43020-0200, 39-01-2020, 0457503111 | molex.com part pages: product spec PDF + 3D STEP zip (e.g. https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/3dcadmodels/430/43025/430250200_stp.zip) | PDF, STEP |
| 13 | Analog Devices TMC2209 | https://www.analog.com/media/en/technical-documentation/data-sheets/TMC2209_datasheet_rev1.09.pdf | PDF |
| 14 | Littelfuse 0297010.WXNV, 0218008.MXP | https://www.littelfuse.com/assetdocs/littelfuse_datasheet_297_mini32v.pdf ; https://www.littelfuse.com/assetdocs/fuse-218-datasheet | PDF |
| 15 | Vishay BAT85S | https://www.vishay.com/docs/85513/bat85s.pdf | PDF |
| 16 | Finder 22.32.0.120.4320 | https://cdn.findernet.com/app/uploads/S22EN.pdf , https://cdn.findernet.com/app/uploads/2020/09/19094115/22.stp_-3.zip , installation sheet https://cdn.findernet.com/app/uploads/2020/09/10231349/IB2232EN-1.pdf | PDF, STEP |
| 17 | Phoenix Contact PLC-RSC-5DC/21 1119897 | https://www.phoenixcontact.com/us/products/1119897 (data sheet PDF + CAD) | PDF, STEP |
| 18 | Raspberry Pi: Pi 5 mechanical drawing, Active Cooler, 27 W PSU, Camera Module 3, HQ Camera, Zero 2 W | https://pip.raspberrypi.com/documents/RP-008347-DS-raspberry-pi-5-mechanical-drawing.pdf ; https://datasheets.raspberrypi.com/cooling/raspberry-pi-active-cooler-product-brief.pdf ; https://datasheets.raspberrypi.com/power-supply/27w-usb-c-power-supply-product-brief.pdf ; camera mechanical drawings/STEP from https://www.raspberrypi.com/documentation/accessories/camera.html ; https://datasheets.raspberrypi.com/hq-camera/hq-camera-product-brief.pdf ; Zero 2 W mechanical drawing from datasheets.raspberrypi.com | PDF, STEP |
| 19 | Harwin R30-6200614, R30-6700594 / 694 / 894 (and the 10 mm Al / M5 spacers chosen) | Digi-Key media "CAD Models" (TraceParts) and https://cdn.harwin.com/pdfs/R30-620.pdf | STEP, PDF |
| 20 | RAF M0904 / M06xx round spacers | https://dpk3n3gg92jwt.cloudfront.net/domains/raf/pdf/RAF_catalog_0289.pdf and RAF CAD | PDF, STEP |
| 21 | Panduit PLT1M-C; Henkel Loctite 243 TDS; igus CF880 data sheet | https://www.panduit.com (PLT1M-C drawing); Henkel TDS for Loctite 243; https://igus.widen.net/view/pdf/vp0r0by5zd/EU_Data_sheet_chainflex_CF880.pdf | PDF |
| 22 | Century Spring DJ-8X20YCS | centuryspring.com product page (drawing / data incl. max temperature) | PDF |
| 23 | Accu HPLW-M3-A2 / HPLW-M4-A2 | accu.co.uk product pages, CAD | STEP |
| 24 | Bed heater (Keenovo custom 192 x 205, 24 V, 180 W, 100k NTC) and the magnetic PEI kit chosen | keenovo.com quote / the kit's seller page with steel and magnet thickness and max temperature | PDF / page print |
| 25 | Alcoa MIC 6 data sheet (density, stock thicknesses, flatness) | alcoa.com / the plate distributor's sheet | PDF |

## Measure on arrival

AB4 POM nut (all dimensions, preload) and the motor's screw length above the face; PEI sheet + magnetic base stack
(thickness, steel thickness under the probe); silicone heater (size, thickness, resistance, lead exit); Roto motor
phase inductance and Revo heater step response; nyloc and spacer masses; probe repeatability; then the twin's (c)
parameters with Klipper's own calibrations.

## Files added by this audit

- `docs/PROVENANCE_AUDIT.md` (this file)
- `vendor_cad/staging/provenance_2026-11-19/` (MANIFEST.md and 7 CAD files)
- `vendor_docs/`: Cantherm_RT_series_OTCO_datasheet.pdf, Cantherm_CS7_R53_thermostat_datasheet.pdf,
  Semitec_NT-4_thermistor_datasheet.pdf, Phoenix_3200519_ferrule_datasheet.pdf, Phoenix_3200014_ferrule_datasheet.pdf,
  igus_CF130_datasheet.pdf, InspiredLED_24V-COB_flex_spec.pdf, RPi5_product_brief_v2.pdf, ST_PN2222A_datasheet.pdf,
  BTT_SFS_V2.0_user_manual_20231123.pdf, delta_BFB_51x51x15_series_drawing.pdf,
  SDP-SI_D815_GT2_2mm_belts_pulleys_pp144-148_153-155.pdf, Omron_D2F_datasheet_digikey_0318.pdf
