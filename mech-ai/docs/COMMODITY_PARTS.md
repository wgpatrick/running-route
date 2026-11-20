# Commodity parts: real catalogue items (DG-07)

Every commodity / BOM-only purchased line of printer_v10_1 that was a "class value" ("not specified" maker) is pinned here to
a real, orderable item: maker, maker part number, seller part number, pack, price at the build quantity, stock and data sheet
(owner's key rule, docs/DESIGN_GUIDELINES.md; check DG-07, mechloop/verifiers/purchased.py).

- **Read on 2026-11-20** from the distributor APIs through `mechloop/sourcing` (Digi-Key v4, Mouser v1, element14/Newark).
  Stock and prices are that day's; re-run `python -m mechloop.sourcing --bom-csv docs/build/printer_v10_1/bom.csv --electrical-only`
  before ordering.
- **Where it is recorded**: `mechloop/data/sourcing/mpn_map.json` (every item of a line: colours per wire gauge, housings +
  crimps per connector line, quantities, prices, `source`, `checked`) and `mechloop/data/real_parts.json` (the DG-07 record:
  maker + MPN + sellers of the line's main item; `order` points back to the map). `mechloop/sourcing/resolve.py` now takes the
  order breakdown from the map when the DG-07 record names the same part, so a pinned wire line still orders feet per colour.
- **Quantities**: from the v10_1 BOM and its wiring list (docs/build/printer_v10_1/wiring.csv); wire metres are conductor
  metres split per colour and rounded up to whole feet (sold cut to length, so no spool is bought for a few metres).
  Connector counts are the wiring list's connector ends (the generator counts one per end), with a few spares.
- **Build quantity 1**: these lines cost **about 347 USD** as ordered (the BOM's class-value estimate for the same lines was
  about 85 USD). The big items are the 14 AWG earth wire (70.54: 100 ft minimum, see decisions), the braided sleeve
  (44.14: 200 ft is the smallest put-up the distributors list), seven TMC2209 modules (42, BOM estimate) and the 24 AWG
  motor wire (42.12). Without the earth-wire minimum and the sleeve spool the rest is about 232 USD.

DG-07 after this pass (BOM-only lines of v10_1): 20 of 22 pinned (maker, MPN, seller); the two left are the GT2 open belts
(not commodity: the 12 mm GT2 belt is a design decision in docs/PROVENANCE_AUDIT.md). The three Pololu spacer SKUs now have a
seller (Pololu, maker direct); their geometry is still a stand-in, so DG-07 keeps the geometry finding.

## Hook-up wire (BOM unit: metre of conductor; bought by the foot unless noted)

| BOM line (qty) | Chosen item: maker MPN | Seller PN | Order | Unit price | Ext. | Stock | Note |
|---|---|---|---|---|---|---|---|
| **WIRE-AWG20-SILICONE-M** (4) | CNC Tech 3239-20-1-0500-001-1-TS | Digi-Key 1175-3239-20-1-0500-001-1-TS-DS-ND | 6 ft | 1.026 | 6.16 | 37893 | black |
|  | CNC Tech 3239-20-1-0500-002-1-TS | Digi-Key 1175-3239-20-1-0500-002-1-TS-DS-ND | 6 ft | 1.026 | 6.16 | 1024 | white |
| | *line total at build quantity* | | | | **12.32** | | basis: wiring.csv v10_1: hotend heater 1.57 m x2 = 3.14 m -> 6 ft per colour (flexing toolhead run: fine-strand silicone) |
| **WIRE-AWG16-SILICONE-M** (2) | CNC Tech 3239-16-1-0500-001-1-TS | Digi-Key 1175-3239-16-1-0500-001-1-TS-DS-ND | 2 ft | 1.64 | 3.28 | 654 | black (0 V) |
|  | CNC Tech 3239-16-1-0500-004-1-TS | Digi-Key 1175-3239-16-1-0500-004-1-TS-DS-ND | 2 ft | 2.69 | 5.38 | 146 | red (+24 V) |
|  | igus CF880-15-02 | Digi-Key 2389-CF880-15-02-ND | 3 ft | 0.81 | 2.43 | 3981 | 2 x 16 AWG chainflex for the moving bed run (0.62 m of cable); Digi-Key Marketplace listing |
| | *line total at build quantity* | | | | **11.09** | | basis: wiring.csv v10_1: 24 V to board 0.2 m x2, bed heater 0.62 m x2 (moving bed run), heater tail 0.09 m x2 = 1.82 m; the bed run in igus CF880 (V12 plan), the fixed runs in single wires, 2 ft per colour |
| **WIRE-AWG18-PVC105-M** (1) | CNC Tech 1015-18-1-2000-001-1-TS | Digi-Key 1175-1015-18-1-2000-001-1-TS-DS-ND | 2 ft | 0.81 | 1.62 | 1672 | black (L) |
|  | CNC Tech 1015-18-1-2000-002-1-TS | Digi-Key 1175-1015-18-1-2000-002-1-TS-DS-ND | 2 ft | 0.81 | 1.62 | 4932 | white (N; US colour - blue is not listed per foot) |
|  | LAPP 4180600 | Digi-Key 2181-4180600-DS-ND | 2 ft | 0.98 | 1.96 | 2874 | green/yellow (PE); LAPP OLFLEX multi-standard hook-up wire: confirm the UL 1015 / 105 degC style on the LAPP sheet |
| | *line total at build quantity* | | | | **5.2** | | basis: wiring.csv v10_1: mains L 0.32 m, N 0.33 m, PE to supply 0.24 m (0.89 m of conductor) -> 2 ft per colour |
| **WIRE-AWG13-PVC105-M** (1) | LAPP 4160500 | Digi-Key 2181-4160500-ND | 100 ft | 0.7054 | 70.54 | 0 | 14 AWG green/yellow; Digi-Key bulk, minimum 100 ft, no stock on 2026-11-20 (Mouser 58-4160500: 1000 ft minimum, no stock) |
| | *line total at build quantity* | | | | **70.54** | | basis: wiring.csv v10_1: earth to frame 0.15 m; 13 AWG is not a stocked hook-up gauge -> 14 AWG green/yellow |
| **WIRE-AWG24-PVC-M** (26) | CNC Tech 1007-24-1-2000-001-1-TS | Digi-Key 1175-1007-24-1-2000-001-1-TS-DS-ND | 23 ft | 0.458 | 10.53 | 1801 | black (A+) |
|  | CNC Tech 1007-24-1-2000-007-1-TS | Digi-Key 1175-1007-24-1-2000-007-1-TS-DS-ND | 23 ft | 0.458 | 10.53 | 3633 | green (A-) |
|  | CNC Tech 1007-24-1-2000-004-1-TS | Digi-Key 1175-1007-24-1-2000-004-1-TS-DS-ND | 23 ft | 0.458 | 10.53 | 4766 | red (B+) |
|  | CNC Tech 1007-24-1-2000-005-1-TS | Digi-Key 1175-1007-24-1-2000-005-1-TS-DS-ND | 23 ft | 0.458 | 10.53 | 4511 | blue (B-) |
| | *line total at build quantity* | | | | **42.12** | | basis: wiring.csv v10_1: 6 motor runs x 4 conductors = 25.88 m -> 6.5 m per coil colour, 23 ft each |
| **WIRE-AWG26-PVC-M** (16) | CNC Tech 1569-26-1-0500-001-1-TS | Digi-Key 1175-1569-26-1-0500-001-1-TS-DS-ND | 17 ft | 0.508 | 8.64 | 7059 | black (0 V) |
|  | CNC Tech 1569-26-1-0500-004-1-TS | Digi-Key 1175-1569-26-1-0500-004-1-TS-DS-ND | 17 ft | 0.509 | 8.65 | 5238 | red (supply) |
|  | CNC Tech 1569-26-1-0500-002-1-TS | Digi-Key 1175-1569-26-1-0500-002-1-TS-DS-ND | 17 ft | 0.508 | 8.64 | 3088 | white (signal) |
| | *line total at build quantity* | | | | **25.93** | | basis: wiring.csv v10_1: relay control, fans, endstops, host serial = 15.03 m -> 3 colours x 17 ft |
| **WIRE-AWG26-SILICONE-M** (11) | CNC Tech 3132-26-1-0500-001-1-TS | Digi-Key 1175-3132-26-1-0500-001-1-TS-DS-ND | 14 ft | 0.606 | 8.48 | 1758 | black |
|  | CNC Tech 3132-26-1-0500-005-1-TS | Digi-Key 1175-3132-26-1-0500-005-1-TS-DS-ND | 14 ft | 0.606 | 8.48 | 920 | blue |
|  | CNC Tech 3132-26-1-0500-004-1-TS | Digi-Key 1175-3132-26-1-0500-004-1-TS-DS-ND | 7 ft | 0.636 | 4.45 | 1186 | red (probe 24 V) |
| | *line total at build quantity* | | | | **21.41** | | basis: wiring.csv v10_1: bed and hotend thermistors, probe signal + 24 V = 10.64 m -> black 14 ft, blue 14 ft, red 7 ft |
| **WIRE-AWG14-PVC105-M** (0) | LAPP 4160500 | Digi-Key 2181-4160500-ND | - ft | 0.7054 | - | 0 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG16-PVC105-M** (0) | LAPP 4160400 | Digi-Key 2181-4160400-DS-ND | - ft | 1.17 | - | 3621 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG13-SILICONE-M** (0) | CNC Tech 3239-14-1-0100-001-1-TS | Digi-Key 1175-3239-14-1-0100-001-1-TS-ND | - spool (100 ft) | 107.14 | - | 30 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG14-SILICONE-M** (0) | CNC Tech 3239-14-1-0100-001-1-TS | Digi-Key 1175-3239-14-1-0100-001-1-TS-ND | - spool (100 ft) | 107.14 | - | 30 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG18-SILICONE-M** (0) | CNC Tech 3239-18-1-0500-002-1-TS | Digi-Key 1175-3239-18-1-0500-002-1-TS-DS-ND | - ft | 1.42 | - | 23457 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG20-PVC-M** (0) | CNC Tech 1007-20-1-2000-001-1-TS | Digi-Key 1175-1007-20-1-2000-001-1-TS-DS-ND | - ft | 0.65 | - | 2980 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG22-PVC-M** (0) | CNC Tech 1007-22-1-2000-001-1-TS | Digi-Key 1175-1007-22-1-2000-001-1-TS-DS-ND | - ft | 0.58 | - | 12000 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG22-SILICONE-M** (0) | CNC Tech 3239-22-1-0500-001-1-TS | Digi-Key 1175-3239-22-1-0500-001-1-TS-DS-ND | - ft | 0.99 | - | 476 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |
| **WIRE-AWG24-SILICONE-M** (0) | CNC Tech 3239-24-1-0500-001-1-TS | Digi-Key 1175-3239-24-1-0500-001-1-TS-DS-ND | - ft | 0.95 | - | 39112 |  |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU the wiring generator can emit); order per the design's metres |

- **WIRE-AWG20-SILICONE-M**: why: UL3239 silicone, 200 degC, fine strand (flexes with the toolhead), sold per foot. Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf.
- **WIRE-AWG16-SILICONE-M**: why: UL3239 silicone 16 AWG per foot for the fixed runs; the flexing bed run in a rated high-flex 2-core cable as V12 plans. Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf. Alternatives: igus CF130-03-02 (flex signal cable named by V12 for the flexing signal runs, Digi-Key 4903-CF130-03-02-DS-ND 1.54/ft, 974 in stock). Note: the bed run becomes one 2-core igus cable (design change, V12 plan); CF880 is a Digi-Key Marketplace item (shipped by the marketplace seller)
- **WIRE-AWG18-PVC105-M**: why: UL1015 PVC 105 degC 600 V stranded, sold by the foot (no 100 ft spool for 0.9 m); green/yellow PE from LAPP because CNC Tech's 1015 G/Y is not listed per foot. Data sheet: https://cnctech.us/pdfs/1015-XX-1-2000-0XX-1-TS.pdf. Alternatives: Alpha Wire 3075 BK005 / 3075 GY005 (UL1015 18 AWG 100 ft spools, Digi-Key A2103B-100-ND 141.04 each (overkill for 0.9 m)); CNC Tech 3239-18-1-0500-011-1-TS (silicone 18 AWG G/Y per foot 1.42 (CN105GY-DS-ND)).
- **WIRE-AWG13-PVC105-M**: why: no 13 AWG hook-up wire is stocked; 14 AWG (2.08 mm2) is the nearest gauge that the 16-14 AWG FASTON and #10 (M5) ring terminals accept; 12 AWG would not fit the 4.8 mm FASTON. Data sheet: https://www.mouser.com/datasheet/3/5935/1/DB4160100EN.pdf. Alternatives: CNC Tech 3239-14-1-0100-007-1-TS (14 AWG silicone G/Y, Digi-Key 1175-3239-14-1-0100-007-1-TS-ND, 100 ft minimum, 500 in stock, 1.0501/ft (105.01)); LAPP 4160400 (16 AWG G/Y per foot 1.17, 3621 in stock (2181-4160400-DS-ND): a downsizing - design decision). Note: DESIGN DECISION: the wiring list asks 13 AWG; choose 14 AWG (this pin, 100 ft minimum, back-order) or 16 AWG (LAPP 4160400, per foot, in stock) for the earth-to-frame lead and update WIRE-AWG13 in the design
- **WIRE-AWG24-PVC-M**: why: UL1007 PVC 80 degC 300 V stranded 24 AWG per foot, four coil colours. Data sheet: https://www.cnctech.us/pdfs/1007-XX-1-2000-0XX-1-TS.pdf. Alternatives: igus CF130-03-02 (high-flex alternative for the flexing motor runs (V12 plan)). Note: X motor and left Y motor runs flex with the gantry: V12 plans igus chainflex for flexing runs; UL1007 hook-up wire is not rated for continuous flexing
- **WIRE-AWG26-PVC-M**: why: UL1569 PVC 105 degC 300 V 26 AWG per foot (CNC Tech lists no UL1007 26 AWG per foot); exceeds the 'pvc' class. Data sheet: https://cnctech.us/pdfs/1569-XX-1-0500-0XX-1-TS.pdf.
- **WIRE-AWG26-SILICONE-M**: why: UL3132 silicone 26 AWG per foot (CNC Tech 3239 has no 26 AWG). Data sheet: CNC Tech 3132 series sheet (Digi-Key media link, mm.digikey.com).
- **WIRE-AWG14-PVC105-M**: why: 14 AWG G/Y LAPP multi-standard; 100 ft minimum, back-order (no 14 AWG UL1015 per foot found). Data sheet: https://www.mouser.com/datasheet/3/5935/1/DB4160100EN.pdf.
- **WIRE-AWG16-PVC105-M**: why: 16 AWG G/Y LAPP multi-standard per foot. Data sheet: https://www.lapptannehill.com/media/datasheet/lapp/olflex/multi-standard-har-hookup-wire.pdf.
- **WIRE-AWG13-SILICONE-M**: why: no 13 AWG: 14 AWG UL3239 silicone, 100 ft spool (design change). Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf.
- **WIRE-AWG14-SILICONE-M**: why: 14 AWG UL3239 silicone, 100 ft spool only. Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf.
- **WIRE-AWG18-SILICONE-M**: why: 18 AWG UL3239 silicone per foot (white; G/Y CN105GY-DS-ND). Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf.
- **WIRE-AWG20-PVC-M**: why: 20 AWG UL1007 per foot. Data sheet: https://www.cnctech.us/pdfs/1007-XX-1-2000-0XX-1-TS.pdf.
- **WIRE-AWG22-PVC-M**: why: 22 AWG UL1007 per foot. Data sheet: https://www.cnctech.us/pdfs/1007-XX-1-2000-0XX-1-TS.pdf.
- **WIRE-AWG22-SILICONE-M**: why: 22 AWG UL3239 silicone per foot. Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf.
- **WIRE-AWG24-SILICONE-M**: why: 24 AWG UL3239 silicone per foot. Data sheet: https://www.cnctech.us/pdfs/3239-XX-1-0500-0XX-1-TS.pdf.

## Ferrules, terminals, connectors

| BOM line (qty) | Chosen item: maker MPN | Seller PN | Order | Unit price | Ext. | Stock | Note |
|---|---|---|---|---|---|---|---|
| **CONN-FERRULE** (22) | Phoenix Contact 3200043 | Digi-Key 277-2190-ND | 15 each | 0.18 | 2.7 | 147822 | AI 1,5-8 BK for 16 AWG (1.31 mm2) |
|  | Phoenix Contact 3200030 | Digi-Key 277-2188-ND | 10 each | 0.18 | 1.8 | 203735 | AI 1-8 RD for 18 AWG (0.82 mm2) |
|  | Phoenix Contact 3200014 | Digi-Key 277-2185-ND | 5 each | 0.18 | 0.9 | 256949 | AI 0,5-8 WH for 20 AWG |
|  | Phoenix Contact 3203011 | Digi-Key 277-7433-ND | 3 each | 0.38 | 1.14 | 27859 | 26 AWG grey (AI 0,14 class) for the probe 24 V lead at the PSU |
| | *line total at build quantity* | | | | **6.54** | | basis: wiring.csv v10_1 screw-terminal ends by gauge: 16 AWG x12, 18 AWG x7, 20 AWG x2, 26 AWG x1; ordered with spares |
| **CONN-JST-XH** (28) | JST XHP-4 | Digi-Key 455-2267-ND | 15 each | 0.065 | 0.98 | 73533 | 4-way housing (13 + 2 spare) |
|  | JST XHP-3 | Digi-Key 455-2219-ND | 10 each | 0.065 | 0.65 | 126302 | 3-way housing (8 + 2) |
|  | JST XHP-2 | Digi-Key 455-2266-ND | 10 each | 0.059 | 0.59 | 186027 | 2-way housing (7 + 3) |
|  | JST SXH-001T-P0.6 | Digi-Key 455-1135-100-ND | 100 each | 0.0471 | 4.71 | 9800 | crimp contact 22-28 AWG; bag of 100 (89 + spares) |
| | *line total at build quantity* | | | | **6.93** | | basis: wiring.csv v10_1 JST-XH ends (the generator counts one per connector end): 4-way x13, 3-way x8, 2-way x6, 1-way x1 (probe 24 V, put in a 2-way); 89 contacts |
| **CONN-MOLEX-MICROFIT** (3) | Molex 43020-0400 | Digi-Key WM1778-ND | 1 each | 0.67 | 0.67 | 28247 | 4-way plug housing for the Roto motor lead |
|  | Molex 43031-0001 | Digi-Key WM1841CT-ND | 10 each | 0.078 | 0.78 | 419791 | male crimp 20-24 AWG, cut tape |
|  | Molex 43025-0200 | Digi-Key WM1783-ND | 2 each | 0.36 | 0.72 | 208477 | 2-way receptacle (both genders bought until E3D's lead gender is seen) |
|  | Molex 43020-0200 | Digi-Key WM1777-ND | 2 each | 0.32 | 0.64 | 17309 | 2-way plug |
|  | Molex 43030-0001 | Digi-Key WM1837CT-ND | 10 each | 0.075 | 0.75 | 1334160 | female crimp 20-24 AWG, cut tape |
| | *line total at build quantity* | | | | **3.56** | | basis: wiring.csv v10_1: extruder motor (4-way: mates the Roto lead's 43025-0400, e3d_roto.json), hotend heater and thermistor (2-way each; E3D does not state the gender on its leads) |
| **CONN-DUPONT** (3) | Molex 50-57-9405 | Digi-Key WM2903-ND | 2 each | 0.39 | 0.78 | 49982 | SL 1x5 2.54 mm housing (host serial, Pi pins 2-10 with pin 4 empty) |
|  | Molex 50-57-9402 | Digi-Key WM2900-ND | 1 each | 0.32 | 0.32 | 87761 | SL 1x2 housing (fan 5 V at the board) |
|  | Molex 16-02-0097 | Digi-Key WM2513-ND | 10 each | 0.165 | 1.65 | 161878 | SL female crimp 24-30 AWG gold (26 AWG wire) |
| | *line total at build quantity* | | | | **2.75** | | basis: wiring.csv v10_1: host serial + 5 V (4 wires, both ends) and the heat-sink fan's board end (2 wires); Pi GPIO 2/6/8/10 sit in a 5-position row |
| **CONN-FASTON-4.8** (4) | TE Connectivity 2-520182-2 | Digi-Key A27804-ND | 4 each | 0.35 | 1.4 | 119251 | FASTON 187 fully insulated receptacle 22-18 AWG |
|  | Panduit DNF14-187FIB-C | Digi-Key 298-11930-ND | 1 each | 1.53 | 1.53 | 148 | 0.187 fully insulated receptacle 16-14 AWG for the earth-to-frame lead (pack 'C' sold singly) |
| | *line total at build quantity* | | | | **2.93** | | basis: wiring.csv v10_1 inlet tabs: L, N, PE-to-supply (18 AWG) + earth-to-frame (13 AWG -> 14 AWG); one spare 18 AWG |
| **CONN-FASTON-6.3** (0) | TE Connectivity 2-520184-2 | Digi-Key A27817-ND | - each | 0.34 | - | 166848 | FASTON 250 fully insulated receptacle 22-18 AWG |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU) |
| **CONN-RING-M5** (1) | Panduit PV14-10R-M | Digi-Key 298-10075-ND | 2 each | 0.31 | 0.62 | 174897 | vinyl-insulated ring, 16-14 AWG, #10 stud (fits M5) |
| | *line total at build quantity* | | | | **0.62** | | basis: wiring.csv v10_1: earth to frame at the M5 earth stud (14 AWG after the gauge decision); one spare |
| **CONN-RING-M4** (0) | Panduit PV18-8R-MY | Digi-Key 298-10437-ND | - each | 0.45 | - | 13525 | vinyl-insulated ring 22-18 AWG, #8 stud (M4) |
| | *line total at build quantity* | | | | **-** | | basis: not in the v10_1 BOM (catalogue SKU) |

- **CONN-FERRULE**: why: Phoenix AI insulated bootlace ferrules, DIN 46228-4 colours, one size per conductor gauge; Digi-Key sells them singly. Data sheet: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/1173/AI.pdf. CAD: TraceParts STEP per part (Digi-Key media). Alternatives: Phoenix Contact 3200519 (AI 0,75-8 GY (the earlier single pin); 18 AWG (0.82 mm2) is over 0.75 mm2, so AI 1-8 RD is used). Note: 0.75 mm2 gray; 3200014 (0.5 mm2 white) for thinner wire
- **CONN-JST-XH**: why: genuine JST XH (the Octopus headers are XH); contacts from the 100-piece bag instead of the 8000 reel. Data sheet: https://www.jst-mfg.com/product/pdf/eng/eXH.pdf. CAD: XHP-2 STEP on Digi-Key; XHP-3/4 and SXH via SnapEDA (Digi-Key media). Alternatives: JST B4B-XH-A / B3B-XH-A / B2B-XH-A (PCB headers, Digi-Key 455-B4B-XH-A-ND / 455-2248-ND / 455-B2B-XH-A-ND); JST SXH-001T-P0.6 (Mouser 306-SXH-001T-P0.6 sold singly (0.041 at 25+)). Note: headers B2B/B3B/B4B-XH-A only where a device-side board is made (DESIGN DECISION: motors, fans, endstops come with their own leads/terminals; the relay module has its own header). If wanted: B4B-XH-A x6 (455-B4B-XH-A-ND 0.17), B3B-XH-A x3 (455-2248-ND 0.13), B2B-XH-A x3 (455-B2B-XH-A-ND 0.10): 1.71
- **CONN-MOLEX-MICROFIT**: why: Micro-Fit 3.0 as E3D uses; the 4-way gender follows E3D's motor-wiring note (43025-0400 on the motor), the 2-way gender is confirmed on arrival. Data sheet: https://www.molex.com/pdm_docs/sd/430250200_sd.pdf. CAD: Molex STEP per part (Digi-Key media). Note: 26 AWG thermistor wire is below the 43030/43031 range (20-24 AWG per Molex): fold the strip back or use a 24 AWG pigtail; confirm the Revo leads' gender
- **CONN-DUPONT**: why: Molex SL (C-Grid III) mates 0.64 mm square 2.54 mm pins (Octopus and Pi headers); 24-30 AWG contact fits the 26 AWG wire (16-02-0102 is 22-24 AWG). Data sheet: https://www.molex.com/pdm_docs/sd/050579405_sd.pdf. CAD: 50-57-9405 / 50-57-9402 STEP (Digi-Key media). Alternatives: Harwin M20-1060500 / M20-1060200 + M20-1180042 (Harwin M20 housings + 22-30 AWG crimp; M20-1060500 out of stock at Digi-Key, Mouser 855-M20-1060500 4955 in stock).
- **CONN-FASTON-4.8**: why: TE Ultra-Fast fully insulated, 4.8 mm (0.187) tab size of the DD11 inlet; 22-18 AWG range matches the mains wire. Data sheet: https://www.te.com/commerce/DocumentDelivery/DDEController?Action=srchrtrv&DocNm=1-1773948-3_Ultra-Fast. CAD: TE STEP + DXF (Digi-Key media; staged earlier). Note: DESIGN DECISION: the inlet PE tab carries two conductors (earth to supply + earth to frame); one FASTON per tab - use a piggy-back receptacle or take PE to a frame stud and bond the supply FG from the stud
- **CONN-FASTON-6.3**: why: TE Ultra-Fast fully insulated 6.3 mm (0.250) receptacle, 22-18 AWG. Data sheet: https://www.te.com/commerce/DocumentDelivery/DDEController?Action=srchrtrv&DocNm=1-1773948-3_Ultra-Fast. CAD: TE STEP/IGS/DXF (Digi-Key media). Alternatives: Panduit DNF14-250FIB-M (16-14 AWG 0.250 fully insulated, Digi-Key 298-10278-ND 0.67, 151955 in stock).
- **CONN-RING-M5**: why: Panduit Pan-Term ring, #10 (5 mm) stud; 13 AWG (2.6 mm2) exceeds its 14 AWG range -> follows the 14 AWG decision. Data sheet: https://www.panduit.com/content/dam/panduit/en/products/media/2/72/172/1172/111461172.pdf. Note: 13 AWG does not fit any 16-14 AWG ring; with 12 AWG use Panduit PV10-10R (12-10 AWG)
- **CONN-RING-M4**: why: Panduit Pan-Term ring for M4 (#8). Data sheet: https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/1154/PV18-xxR%28N%29.pdf. Alternatives: Panduit PV14-8R-M (16-14 AWG #8, Digi-Key 298-10305-ND 0.43, 69561 in stock).

## Loom, protection, consumables

| BOM line (qty) | Chosen item: maker MPN | Seller PN | Order | Unit price | Ext. | Stock | Note |
|---|---|---|---|---|---|---|---|
| **SLEEVE-BRAIDED-8MM-M** (4) | Techflex PTN0.25BK200 | Digi-Key 1030-PTN0.25BK200-ND | 1 spool (200 ft) | 44.14 | 44.14 | 750 | Flexo PET 1/4 in nominal (expands to about 7/16 in, 11 mm), black |
| | *line total at build quantity* | | | | **44.14** | | basis: BOM v10_1: 4 m of loom (13 ft); the smallest put-up Digi-Key lists is 200 ft |
| **CABLE-TIE-100MM** (106) | Panduit PLT1M-C | Digi-Key 298-1020-ND | 106 each | 0.2123 | 22.5 | 285661 | Pan-Ty 99 mm (3.9 in), 18 lb, natural nylon 6.6; Panduit pack C = bag of 100, Digi-Key sells singly |
| | *line total at build quantity* | | | | **22.5** | | basis: BOM v10_1: 106 ties |
| **FUSE-5x20-T8A** (2) | Schurter 0001.2513 | Mouser 693-0001-2513 | 2 each | 0.91 | 1.82 | 6954 | SPT 5x20 ceramic time-lag T8A 250 VAC |
| | *line total at build quantity* | | | | **1.82** | | basis: BOM v10_1: one fitted, one spare |
| **FUSE-5x20-T5A** (0) | Schurter 0001.2511 | Mouser 693-0001.2511 | - each | 0.92 | - | 11497 | SPT 5x20 ceramic T5A |
| | *line total at build quantity* | | | | **-** | | basis: V12 plan: the 230 V fuse-link (not in the v10_1 BOM) |
| **DIODE-BAT85** (1) | Vishay BAT85S-TAP | Digi-Key BAT85S-TAPCT-ND | 2 each | 0.5 | 1.0 | 27916 | DO-35 (DO-204AH) axial, ammo pack cut tape |
| | *line total at build quantity* | | | | **1.0** | | basis: BOM v10_1: one in the probe signal lead; one spare |
| **THREADLOCKER-MEDIUM** (1) | Henkel (Loctite) 1329837 | Newark 80R9545 | 1 each | 23.41 | 23.41 | 26 | Loctite 243, 10 ml bottle, blue medium strength |
| | *line total at build quantity* | | | | **23.41** | | basis: BOM v10_1: one bottle (the line appears twice in the BOM: THREADLOCKER-MEDIUM and its annotated duplicate - buy ONE) |

- **SLEEVE-BRAIDED-8MM-M**: why: Techflex Flexo PET, 1/4 in nominal covers an 8 mm bundle; only spool put-ups at the distributor (no per-foot listing). Data sheet: Techflex Flexo PET (PTN) product sheet: techflex.com (not linked by Digi-Key's API record). Alternatives: Techflex PTN0.38BK125 (3/8 in nominal, 125 ft, Digi-Key 1030-PTN0.38BK125-ND 44.14, 437 in stock). Note: pays for 200 ft to use 13 ft; a 25 ft put-up exists only at resellers (not API-verified)
- **CABLE-TIE-100MM**: why: Panduit PLT1M-C as pinned before; price unit confirmed per tie at Digi-Key (Mouser 644-PLT1M-C: minimum 100, 0.212 per tie). Data sheet: https://www.mouser.com/datasheet/3/506/1/110198548.pdf. Alternatives: Panduit PLT1M-M (bag of 1000, Digi-Key 298-1021-ND 0.05956/tie (59.56 per bag) - cheaper per tie, more than needed).
- **FUSE-5x20-T8A**: why: V12 plan: SPT ceramic for breaking capacity (Digi-Key 486-1767-ND 1.09, 41439 in stock). Data sheet: https://www.schurter.com/en/datasheet/typ_SPT_5x20.pdf. CAD: Schurter STEP/IGS (Digi-Key media). Alternatives: Littelfuse 0218008.MXP (glass T8A (audit)).
- **FUSE-5x20-T5A**: why: V12 plan (230 V): Digi-Key 486-1785-ND 1.10, 5532 in stock. Data sheet: https://www.schurter.com/en/datasheet/typ_SPT_5x20.pdf. CAD: Schurter STEP/IGS (Digi-Key media).
- **DIODE-BAT85**: why: Vishay BAT85S as pinned in the audit; axial suits an in-lead splice. Data sheet: https://www.vishay.com/docs/85513/bat85s.pdf. CAD: Ultra Librarian (Digi-Key media). Alternatives: Vishay BAT85S-TR (same diode on tape-and-reel, Digi-Key BAT85SCT-ND 0.50, 31958 in stock); Nexperia BAT85,133 (DO-34 (audit)).
- **THREADLOCKER-MEDIUM**: why: Henkel IDH 1329837 = Loctite 243 10 ml (element14 attributes: Product Range LOCTITE 243, Volume 10 ml); Digi-Key lists it only on its Marketplace (2275-1329837-ND, 5 minimum). Data sheet: http://www.farnell.com/datasheets/4159804.pdf. Alternatives: Henkel (Loctite) 1330255 (Loctite 243 0.5 ml capsule, Newark 80R9546 4.55 (too small for the joints listed)). Note: duplicate BOM line: 'THREADLOCKER-MEDIUM' and 'THREADLOCKER-MEDIUM (Loctite 243 class: ...)' are the same bottle; the design should merge them

## Maker-direct modules

| BOM line (qty) | Chosen item: maker MPN | Seller PN | Order | Unit price | Ext. | Stock | Note |
|---|---|---|---|---|---|---|---|
| **DRIVER-BTT-TMC2209** (7) | BIGTREETECH TMC2209 V1.3 | BIGTREETECH official store (maker direct)  | 7 each | 6.0 | 42.0 | n/a | StepStick module; price is the BOM estimate - the store was not reachable from this session |
| | *line total at build quantity* | | | | **42.0** | | basis: BOM v10_1: Octopus sockets X, Y, Y1, Z, Z1, Z2, E |

- **DRIVER-BTT-TMC2209**: why: maker-direct only: BTT's own module; Digi-Key/Mouser list ADI/Trinamic boards (TMC2209-EVAL / BOB), not a StepStick for the Octopus sockets. Data sheet: https://raw.githubusercontent.com/bigtreetech/BIGTREETECH-TMC2209-V1.2/master/manual/TMC2209-V1.2-manual.pdf. Note: price, stock and product page not verified (biqu.equipment blocked in this session's network): owner or Instinct to confirm the V1.3 listing

## Spacers and standoffs (geometry lines: stock lengths only)

| BOM line (qty) | Status | Candidate (stock length) |
|---|---|---|
| SPACER-NYLON-M2.5-4x2.7x4 (2), SPACER-NYLON-M3-5x3.3x4 (2), SPACER-NYLON-M3-5x3.3x6 (7) | pinned: Pololu 1971 / 1981 / 1982, seller Pololu (maker direct); price not re-read | Harwin R30-6700494 / R30-6700694 (Digi-Key 952-1527-ND 0.64, 952-1529-ND 0.67) as distributor alternatives (bore 3.2 vs 3.3) |
| SPACER-NYLON-M3-5x3.3x5.5 (2) | **not pinned**: 5.5 mm is not stocked | Harwin R30-6700594 (5 mm, 952-1528-ND 0.69, 21122) or R30-6700694 (6 mm): design decision |
| SPACER-AL-M3-6x3.2x4 (2) | **not pinned**: no 6 mm OD M3 round at 4 mm found | Harwin R30-6200414 (4 mm, 952-2006-ND 0.50, 10522), OD 5 mm: design change |
| SPACER-AL-M3-6x3.2x3.6 (6) | **not pinned**: 3.6 mm not stocked | Harwin R30-6200314 (3 mm, 952-2365-ND 0.50) or R30-6200414 (4 mm): design change |
| SPACER-AL-M2.5-5x2.7x6.55 (3) | **not pinned**: 6.55 mm not stocked | RAF M0904-A-25-AL series (6.9 mm listed in the audit): design change |
| SPACER-AL-M5-10x5.1x54.825 (4), x58 (2), x9 (1) | **not pinned**: no stocked M5 round at these lengths | RAF M5 rounds list 3, 5, 11, 44 mm (Digi-Key M0592-5-AL, M0594-5-AL, M0633-5-AL-22, all without stock on 2026-11-20): stack stock lengths or make the part (then it is a fabricated part) |

These are recorded in mpn_map.json as `kind: placeholder` with `replace_with` naming the candidates, not in real_parts.json:
pinning a different size there would mark the drawn part real when it is not the part that will be bought.

## Not pinned / open

- **WIRE-AWG13 (earth to frame), design decision.** 13 AWG hook-up wire is not stocked, and 13 AWG (2.6 mm2) does not fit the
  16-14 AWG FASTON or ring. Pinned to 14 AWG green/yellow (LAPP 4160500: 100 ft minimum, no stock on 2026-11-20). Choose
  14 AWG (this pin, or CNC Tech 3239-14 G/Y silicone, 100 ft, in stock) or 16 AWG (LAPP 4160400, per foot, in stock; a
  downsizing) and change the wiring list; the CONN-RING-M5 and 16-14 AWG FASTON follow that gauge.
- **Inlet PE tab, design decision.** Two conductors (earth to supply, earth to frame) land on one 4.8 mm PE tab; one receptacle
  per tab. Use a piggy-back receptacle, or take PE to the frame stud and bond the supply FG from there.
- **JST XH headers (B2B/B3B/B4B-XH-A), design decision.** The wiring list shows JST-XH at device ends, but the motors, fans
  and endstop switches come with their own leads/terminals and the relay module has its own header; a header is needed only
  where a device-side breakout is made. Priced as an option in the CONN-JST-XH note (1.71 for 6 + 3 + 3).
- **Micro-Fit 2-way gender (E3D Revo leads).** E3D states "Micro-Fit 3.0, 2 pin" without the gender; both halves are bought
  (0.72 + 0.64) until the leads are seen. 26 AWG thermistor wire is under the 20-24 AWG Micro-Fit crimp range.
- **Flexing runs.** The X and left-Y motor runs and the toolhead loom flex; UL1007 / UL1569 hook-up wire is not rated for
  continuous flexing. V12 plans igus chainflex (CF130-03-02 signals, CF880-15-02 bed); only the bed run is switched here
  (WIRE-AWG16-SILICONE-M, design change). CF880-15-02 is a Digi-Key Marketplace listing.
- **TMC2209 V1.3 (needs Instinct / network).** Maker-direct only; the BTT store (biqu.equipment) is not reachable from this
  session, so price (6.00, the BOM estimate), stock and the product page are not verified.
- **Threadlocker duplicate.** `THREADLOCKER-MEDIUM` and `THREADLOCKER-MEDIUM (Loctite 243 class: ...)` are the same bottle;
  both keys are recorded (DG-07 reads the full BOM key), order one. The design should merge the two lines. The suggested
  Henkel 1329467 is not listed by Digi-Key, Mouser or Newark; 1329837 (10 ml) is, at Newark.
- **Heat-shrink**: not a BOM line (the wiring list asks for the BAT85 to be heat-shrunk); add a line if it is to be bought.
- **Braided sleeve**: Alex Tech is not listed by the distributors; Techflex PTN is (spools only).
- **Datasheets behind bot blocks**: JST (jst-mfg.com) and Panduit/LAPP sheets were not opened here; links are as the
  distributors give them. Wire insulation ratings (UL style, temperature) are from the series names and need confirming on
  the CNC Tech / LAPP sheets before the ratings are used by a check.
