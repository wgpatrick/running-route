# Rail options: alternatives to genuine HIWIN MGN12 for the printer (2026-11-20)

Question: genuine HIWIN from Digi-Key costs $125 per rail and $59 per block, about $1,100 for the printer's 6 rails and 6
blocks, against an owner's budget of about $1,100-1,350 for the whole printer. What else is real and orderable, what fits
without redesign, and what does each configuration cost?

Owner's rule (docs/DESIGN_GUIDELINES.md, key rule, 2026-11-20): every purchased part is a real, orderable product from a
named maker, with the maker's datasheet and CAD (or a dimensioned drawing to re-make it faithfully), used at a stock size.
Rails are bought at the length sold; a length the maker cuts to order is allowed only if the maker's cutting service is
named (as for the Misumi extrusion).

Sources: distributor APIs (Digi-Key, Mouser, Newark, Farnell through `mechloop/sourcing`, 2026-11-20; cached in
`out/sourcing_cache/`), maker documents saved in `vendor_docs/` (list in `vendor_cad/staging/rails_2026-11-20/MANIFEST.md`),
and maker web pages where the session could reach them. Many maker sites could not be read from this session; what they
hold is listed at the end for the owner's browser agent. Prices are USD, quantity 1 unless stated, before shipping and tax.

## 1. What the design needs (designs/printer_v11.py, out/printer_v11/report.json)

| Axis | Rails x length (v11 as drawn) | Blocks | Preload in the model | Load per block (ratings.guide_loads) | Static safety / moment safety |
|---|---|---|---|---|---|
| X | 1 x 250 mm (`X_RAIL_L`; v11.1 plan: 300 mm, docs/V11_1_PLAN.md) | 1 MGN12H | not declared: Z0 assumed | 5.2 N, 0.13 N.m | 1125 / 272 |
| Y | 2 x 300 mm | 2 MGN12H (one per rail) | not declared: Z0 assumed | 8.7 N, 0.21 N.m | 679 / 173 |
| Z | 3 x 250 mm (`Z_RAIL_L`) | 3 MGN12H, one per rail | **ZF** (`mgn12h_carriage(preload="ZF")`) | 14.7 N, 0.54 N.m | 401 / 68 |

What depends on the block:

- **Static ratings** (ratings.guide_loads, bed_support): the loads are tiny. Any 12 mm ball block (and even a 9 mm one)
  passes with safeties far above 10.
- **Z tilt allowance** (requirement "v10: the Z motors may tilt the carrier by at least 3 x the routine height error",
  bed_support.tilt_allowance): needs `overload_free_mm` >= 3 x 0.142 = 0.43 mm. Today the first limit is the nut seats at
  1.14 mm; the block limits are 1.82 mm (rear block, from MGN12H's 36.3 N.m MP/MY and 5,880 N C0) and 1.93 mm.
- **Z support stiffness** (bed_support): the ZF block has no maker rigidity figure, so the model **assumes** 40 N/um
  (`ratings.BLOCK_K`). A Z0 or Z1 block carries HIWIN's published figure instead.
- **Level over the travel** (bed_support.level_over_travel): uses HIWIN's running-parallelism table (class C assumed) only
  when the block SKU starts with "MGN"; result 0.0006 mm, negligible against the 0.08 mm from screw lead error.
- **Y rail pair** (tolerance.paired_rails.y): Z0 allows 9 um parallelism; the design aligns the rails at assembly (1.28 mm
  needed of 1.6 mm available at 99 %). A clearance-class block would relax this; a heavier preload (Z1, 5 um) would tighten it.
- **Nozzle stiffness** (FEA nozzle_stiffness_x/y, 2,570 N/mm in Y): rail and block are bonded in the FEA, so block rigidity
  is not in that number; in reality the X block's preload matters for ringing and backlash at the nozzle.
- **Geometry**: the parts are `mgn12_rail` / `mgn12h_carriage` (mechloop/parts/__init__.py), built from HIWIN's catalogue
  data (`vendor_data("hiwin_mgn12")`). Any other maker needs its own vendor-data record and part function (or a maker
  parameter), even when the envelope is identical. That is code and data work, not a geometry redesign.

Two findings that matter whatever is chosen:

1. **The 250 mm length is not a stocked length.** Digi-Key stocks MGN-R12 at 90, 100, 110, 120, 145, 150, 170, 200, 220,
   300, 320, 370, 430, 470, 570, 635, 720, 770 mm. HIWIN's own standard MGNR12 lengths are 70 + 25n (... 220, 245, 270,
   320 ...; HIWIN MG 2025, table 2-4-15). So v11's "stock 250 mm" X and Z rails are neither: X goes to 300 in the v11.1 plan;
   Z needs 245 (HIWIN standard, from another HIWIN distributor or Helix/CPC), 300 (Digi-Key; must be checked against the
   364 mm uprights and the carriage-plate travel), or a length cut by HIWIN to order (E = 12.5 mm is inside HIWIN's 5-20 mm).
   220 mm is too short for the 183 mm Z travel with a 45.4 mm block.
2. **Digi-Key has no MGN12**H** in ZF.** It lists MGN-12-H-Z0, H-Z1, C-Z0, C-Z1, C-ZF (and C-ZF-HMU). The Z guides
   therefore become either H-Z0 (declare `preload="Z0"`; the check then uses HIWIN's 63 N/um instead of the assumed 40) or
   C-ZF (different hole pattern, see table).

The Digi-Key HIWIN items are sold by Midwest Machine Tool Supply through the Digi-Key Marketplace. Their suffix "HM" is
HIWIN's accuracy class H, stainless steel (M), interchangeable type: better than the class C the bed check assumes.

## 2. Compare and contrast

MGN12 reference envelope (HIWIN catalogue, vendor_docs/Hiwin_MG_catalogue.pdf): rail 12 wide x 8 high, M3 bolt holes
3.5 x 6 x 4.5 at 25 mm pitch; block MGN12H: H 13, W 27, L 45.4, holes B 20 x C 20 (M3 x 3.5 deep), L1 32.4;
C 3,720 N, C0 5,880 N, MR 38.2 / MP 36.3 / MY 36.3 N.m. MGN12C: same section, L 34.7, holes 20 x 15, L1 21.7,
C 2,840 N, C0 3,920 N, MR 25.5 / MP 13.7 / MY 13.7 N.m.

| # | Maker / series | Rail (part no., length) | Block (part no.) | Price rail / block (set of 6 + 6) | Stock, lead, MOQ, where | MGN12 mounting fit | Preload / accuracy | Rated loads | Maker CAD / datasheet | Engineering trade-off |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **HIWIN MGN12** (genuine) | MGN-R12-R300-HM (also R220, R320 $160) | MGN-12-H-Z0-HM (or H-Z1) | $125 / $59 ($1,104) | ~100 rails, 70-96 blocks; 1 wk; MOQ 1; Digi-Key Marketplace (Midwest Machine Tool Supply) | Reference | Z0 0-3 um (Z1 light preload; ZF 4-10 um clearance); class H | as above | Datasheet: in repo (HIWIN GmbH catalogue + HIWIN Corp MG 2025 excerpt). CAD: HIWIN site not reachable (hiwin.tw robots.txt disallows ClaudeBot) -> **owner's agent** | Best documented: rigidity published (MGN12H Z0 63 N/um in the GmbH catalogue; **105 N/um in HIWIN Corp's 2025 table**, a discrepancy to note; Z1 81 / 182). |
| 1b | HIWIN MGN12C | same rails | MGN-12-C-ZF-HM / C-Z0 / C-Z1 | $59 (no saving) | 94-98; 1 wk; Digi-Key | Same rail; block 34.7 long, holes **20 x 15** (Z carriage plates re-drilled) | ZF available in C only | C0 3,920; MP/MY 13.7 | as 1 | Only reason to use it: ZF in stock. On Z the block limit of the tilt allowance falls from 1.82 to about 0.7 mm (scaled by MP/MY; estimate, not run), still above 0.43 mm. Shorter ball track (21.7) lowers tilt stiffness. |
| 1c | HIWIN MGN9 (X only) | MGN-R9-R300-HM | MGN-9-H-Z0-HM | $119 / $53 | 100 / 81; 1 wk; Digi-Key | **No**: rail 9 wide, block H 10, W 20, holes 15 x 16 (tool plates, beam change) | Z0 | C 2,550, C0 4,020, MP/MY 18.6 | as 1 | Saves $12 on X for a softer, lower-rated guide and a redesign. Not worth it. |
| 2 | **Helix Linear HMR12** (made by CPC / Chieftek: the code is CPC's MR12 code with an H prefix; Nook Industries sells the same as NMR12) | Rail and block sold assembled: HMR12**ML**SS1V0N-245L-15-15 ($100.85), -270L ($106.71), -320L ($118.44); no 300 at Digi-Key (a 300L listing exists on helixlinear.com) | included (ML = long block, SS = seals, 1 block, V0 preload, N accuracy; also V1, VS, MN short block ~$2.6 less) | $100.85-118.44 per rail **with** block (6 sets: $617-658) | Digi-Key Marketplace: stock 10, 0 wk, **MOQ 10 per part number**; direct from helixlinear.com (qty-1 price not readable here) | Nominal MGN12 (12 mm rail, 25 mm pitch, block W 27; MN holes 15 x 20 per Helix listing) - **to verify on the drawing**: the Digi-Key suffix "-15-15" (end distances?) does not fit a 25 mm pitch at 245 mm, while Helix's own 300L listing reads "-12.5-12.5" | V0 (zero), V1 (light), VS (clearance); accuracy N (normal) | MN block C0 3,465 N (Helix listing); ML ratings not read | Helix catalogue and CAD tab: host not reachable -> **owner's agent**; CPC MR catalogue on anaheimautomation.com -> **owner's agent** | About 45 % below HIWIN rail + block. A real US maker (Helix) and Taiwanese OEM (CPC) with catalogues and CAD. Normal accuracy and unknown published rigidity: fine for Z, acceptable for Y once CPC's parallelism figure for V0 is in the tolerance check, second choice for X. The MOQ 10 at Digi-Key kills the saving unless Helix (or Anaheim for CPC) sells singles. |
| 3 | **NSK PU12** (miniature, interchangeable with NSK LU) | P1U12 rail (interchangeable, accuracy PC), max 800 mm | PAU12UR (high-load, long) or PAU12TR (standard) | Not found at Digi-Key / Mouser / Newark / Farnell; NSK distributors quote -> **owner's agent** | NSK Americas distributors | Yes for the block face: H 13, W 27, holes B 20 x J 20 (UR), M3 x 3.5; rail 12 x **7.5** (0.5 lower than HIWIN; screw seat 0.5 lower, M3 x 8 still fine), F 25, bolt hole 3.5 x 6 x 4.5 | ZT fine clearance (interchangeable: 5 um or less for UR); Z1 slight preload for assemblies | PU12UR: C50 4,000 N, C0 5,700 N, MRO 34.5, MPO/MYO 28.3 N.m; rigidity Z1 52 N/um | **Datasheet fetched**: vendor_docs/NSK_PU-PE_miniature_E3327e.pdf. CAD: NSK CADENAS portal not reachable -> owner's agent | Premium quality, published rigidity, resin parts rated to 80 C (50 C with K1). Probably not cheaper than HIWIN. Fits all three axes without geometry change; data record and part function needed. |
| 4 | **igus drylin T miniature** (polymer liner on anodised aluminium) | TS-04-12, cut to length by igus (100-2000 mm; "no cutting charge for standard lengths") | TW-04-12 (fixed clearance, zinc + iglide J) or TWE-04-12 (clearance adjustable with a screwdriver) | Rail: qty-1 price for size 12 not in the static page (ladder shown for size 07 is $106.92 per "ft"; estimate ~$128 per unit, **not a quote**). Carriage TWE-04-12 $46.29; TW-04-12 ~$23 (estimate) | igus US store, "ships within 5 working days"; not at the four distributors | igus states "dimensionally interchangeable with recirculating ball bearing guides"; carriage width A 27 mm. Height, hole pattern, length **not read** (drawing on a blocked host) | Running clearance (polymer slide), adjustable on TWE | ~0.96 kN static (distributor figure, not the maker's) | Page facts: vendor_docs/igus_drylin_T_miniature_TS-04-12_TW-04-12_webstore_2026-11-20.txt. Drawing + CAD -> **owner's agent** | Much softer and with play (tens of um, set by hand on TWE), stick-slip risk, but dirt-tolerant and lubrication-free. Not cheaper once the rail is priced. Could serve on Z only (the guides only locate there), never X/Y. The bed check would need a clearance and a stiffness for it. |
| 5 | igus drylin N (NS-01-27 / NW-02-27) | NS-01-27 (27 mm wide, M4 holes, ~$51-60 per m) | NW-02-27 (~$7) | cheap | igus | **No**: 27 mm wide low-profile rail, M4 at 60 mm pitch, different heights | clearance | 50 kg max per carriage (size 27) | igus | Very different: low stiffness, real play. Only with a new Z guide design. Listed because it was asked for. |
| 6 | Misumi own-brand miniature (SSEB13 standard, SSEBL13 long block; rail 12, H 13; also economy series) | configurable length (Misumi cuts) | included (sold as set) | Not read: us.misumi-ec.com product pages answer "Access Denied" (Akamai 403) to this session; a Misumi JP page quotes SSEBL13-246 at 6,500 yen (snippet) | Misumi USA | Nominal MGN12 envelope (H 13, rail 12) - to confirm on the drawing | Misumi offers clearance and light preload classes | not read | Datasheet and CAD (login) -> **owner's agent** | Often the cheapest real-maker option in the US for configured lengths; numbers needed before it can be ranked. |
| 7 | THK RSR12 (RSR12VM, RSR12ZM, wide RSR12WVM) | RSR12 rail | RSR12VM / RSR12ZM | quote | THK distributors | MGN12 grew from this envelope (H 13, W 27, rail 12, pitch 25), to confirm on THK's drawing | clearance / light preload, normal-to-precision | not read | thk.com not reachable -> owner's agent | Premium; no saving expected. |
| 8 | IKO (LWL12 / ML12), Schneeberger (MINIRAIL 12), Bosch Rexroth (miniature ball rail size 12), PMI (MSC12M / MSC12LM), TBI Motion (miniature series), Ewellix, Thomson (miniature profile rail) | - | - | quote | distributors | nominally the same 12 mm envelope; each to confirm on the maker's drawing | - | - | makers' sites not reachable (Thomson: Cloudflare challenge, a refusal) -> owner's agent | No list prices visible; PMI and TBI are the likely value options of this group. TBI is on Digi-Key, but only sizes 15 and up. |
| 9 | Excluded | Olimex "LINEAR-GUIDE-MGN12-400MM" (Digi-Key, $28, 0 stock), unbranded marketplace MGN12, PBC Linear Mini-Rail MR12 | - | - | - | Olimex/unbranded: no named maker, datasheet or CAD -> fails the rule. PBC Mini-Rail (plain bearing): carriage 10.7 mm high, not the MGN12 block -> redesign | - | - | - | Not usable under the rule (or a different envelope). |

## 3. Per-axis recommendation (best value that keeps the checks passing)

- **X: genuine HIWIN.** MGN-R12-R300-HM + MGN-12-H-Z0-HM (Digi-Key, $184), as the v11.1 plan already says. One block
  carries the toolhead; preload and published rigidity matter here more than anywhere, and the price gap to the
  alternatives is only $65-80. Declare the preload in the model (`mgn12h_carriage(preload="Z0")`) so the metrics stop
  saying "assumed". Z1 costs the same and is stiffer; Z0 is the gentler choice for a single block on an aluminium beam.
- **Y: HIWIN unless a cheaper real maker is confirmed at qty 1.** 2 x (MGN-R12-R300-HM + MGN-12-H-Z0-HM), $368. The
  value alternative is Helix/CPC HMR12MLSS1V0N-320L (320 mm, $118.44 each with block): it needs (a) qty-1 purchase from
  Helix or CPC's distributor, (b) the drawing to confirm hole pattern and height, (c) a check that 320 mm clears the Y
  idler and motor plates on the 373 mm top rail, (d) CPC's allowable parallelism for V0 in the Y tolerance check.
  Saving about $50 for the pair; worth it only together with Z.
- **Z: the cheapest real ball guide.** The Z blocks only locate the carrier sideways (the three screws hold its tilt), loads
  are 15 N, and the running accuracy contributes 0.0006 mm: every option in rows 1-3 and 6 passes. Choices:
  - HIWIN at Digi-Key: 3 x MGN-R12-R300-HM (fit check on the uprights) + 3 x MGN-12-H-Z0-HM, $552. No ZF in H: use Z0 and
    declare it (the check then uses 63 N/um instead of the assumed 40 N/um: an improvement). Or C-ZF ($59, carriage plates
    re-drilled 20 x 15, tilt-allowance block limit ~0.7 mm, still passes).
  - Helix/CPC HMR12MLSS1V0N-245L x 3 ($302.55 at the Digi-Key unit price): 245 mm is 5 mm shorter than v11's 250, which
    leaves 9 and 6 mm of rail beyond the block at the ends of the travel instead of 11.5 and 8.5; no other change. **Best
    value** if Helix sells singles. Choose V0 (or VS for the clearance the v9 design wanted) to match.
  - igus drylin T only if the owner accepts a polymer guide on Z and a new clearance/stiffness input to the bed check.

## 4. Estimated totals (6 rails + 6 blocks unless stated; Digi-Key prices of 2026-11-20, before shipping)

| Configuration | X | Y | Z | Total | vs all-HIWIN |
|---|---|---|---|---|---|
| A. All genuine HIWIN (Digi-Key) | R300 + H-Z0: $184 | 2 x (R300 + H-Z0): $368 | 3 x (R300 or R220 + H-Z0 / C-ZF): $552 | **$1,104** | - |
| B1. HIWIN X + Y, Helix/CPC Z | $184 | $368 | 3 x HMR12MLSS1V0N-245L: $302.55 | **$855** (qty-1 from Helix assumed; at Digi-Key's MOQ 10 the Z line is $1,008.50 and the total $1,561) | -$249 |
| B2. HIWIN X, Helix/CPC Y + Z | $184 | 2 x HMR12MLSS1V0N-320L: $236.88 | $302.55 | **$723** (same qty-1 caveat) | -$381 |
| C. All Helix/CPC (cheaper real maker) | HMR12MLSS1V0N-245L $100.85 (v11 length; X travel drops 5 mm to 186.6) or -320L $118.44 (v11.1, fit check) | $236.88 | $302.55 | **$640-658** (same caveat) | -$446 to -$464 |
| D. Two Z rails instead of three | | | one rail + block fewer | A: **$920**; B1: **$754**; C: **$539-557** | -$184 / -$101 per removed guide |

Notes on D (2 Z rails): the v9 layout uses three guides so that each holds one in-plane direction on a flexure (left/right
hold Y and yaw, rear holds X). With two side rails, one side mount must become rigid along its wall normal to take X while
the other keeps its flexure. That is exact-constraint and workable, but it is a redesign of `designs/printer_v11.py` (rear
upright, carriage plates, the "three rails without over-constraint" requirement and the bed-support model), not a part
swap.

Other design alternatives considered:

- Round shafts + real linear bearings on Z (e.g. Misumi shafts with LMU ball bushings, igus drylin R): the bed-support
  model already handles plain/bushing supports, but it means new uprights, shaft supports and carriage plates. Not quoted
  (Misumi and the igus shaft pages could not be read); likely $150-250 for three guides; not cheaper enough to justify the
  redesign while option B1 exists.
- MGN9 for X: saves $12, lowers ratings and stiffness, and changes the tool plates. Rejected.
- MGN12C instead of H: same price at Digi-Key. Only for availability of ZF.
- Assembled HIWIN sets (non-interchangeable, e.g. a block preinstalled on a 300 mm rail): not offered by Digi-Key; other
  HIWIN distributors may price a set below rail + block. Owner's agent to ask.

Budget reality: even configuration C with two Z rails is about $540 for guides alone, roughly 40-50 % of the whole-printer
budget. The cheapest real-maker set that keeps every check passing without geometry redesign is B1 or C, and only if
Helix (or CPC's US distributor) sells single assemblies at about the Digi-Key unit price.

## 5. What a switch costs in code (no geometry redesign, but not free)

- New vendor-data record (maker, part numbers, drawing dimensions, ratings, rigidity, allowable parallelism, running
  parallelism) and part functions for any non-HIWIN guide; `real_part` facts for DG-07 (mechloop/verifiers/purchased.py).
- bed_support.level_over_travel only applies HIWIN's running-parallelism table to SKUs starting with "MGN"; another maker
  needs its own table or the check silently skips the term.
- tolerance.paired_rails takes the allowable parallelism from the block's ratings: needed for the Y pair.
- Z: if the preload becomes Z0 (HIWIN H at Digi-Key), change `mgn12h_carriage(preload="ZF")` to `"Z0"`; if C-ZF, the
  carriage plate's block holes become 20 x 15 and a `mgn12c_carriage` part is needed.
- Rail lengths: X 300 (v11.1 plan) and Z 245 or 300 replace the non-stocked 250.

## 6. Needs the owner's browser agent (exact pages and part numbers)

Helix Linear / CPC (priority: decides configurations B and C)
1. https://www.helixlinear.com/miniature-linear-guides - qty-1 price, MOQ and lead time for HMR12MLSS1V0N-245L, -270L,
   -300L, -320L (and the V0/VS/V1 variants); the CAD tab (STEP) for HMR12ML with each length.
2. https://resources.helixlinear.com/hubfs/Helix%20Miniature%20Linear%20Guides.pdf - catalogue (HMR-M SU tables, pp. 14-17):
   rail and block drawing, end distances, ratings, rigidity, accuracy and parallelism tables.
3. https://www.helixlinear.com/products/Miniature-Linear-Guides/HMR12MN-SU-1-VSN-300L-12.5-12.5~HMR12MN%20300%20mm%20OAL -
   the 300 mm listing (confirms the end-distance notation).
4. CPC originals: https://anaheimautomation.com/media/anaheim/files/manuals/linearguide/L011725_-_MR_Catalog_(english)_2018.pdf,
   https://anaheimautomation.com/media/anaheim/files/manuals/linearcomponents/L010999_-_CPC-MR12_Spec_Sheet_(NEW).pdf,
   and https://anaheimautomation.com/cpc-mr12mlssv0n-1000l.html (price/lengths of CPC MR12MLSSV0N at qty 1).
5. Digi-Key page (MOQ 10 confirmation): https://www.digikey.com/en/products/detail/helix-linear/HMR12MLSS1V0N-245L-15-15/30130476

HIWIN (CAD for the parts already in the design, required by the key rule)
6. HIWIN 3D CAD (STEP) for MGN12H block, MGN12C block and MGNR12R rail at 300 mm (and 245 mm): hiwin.com / hiwin.us product
   pages or HIWIN's CAD portal. The MGN12 STEPs in the repo are community-made.
7. Distributor catalogue linked from Digi-Key: https://midwestmachinetool.com/pub/media/assets/product/documents/MG-Series-Catalog.pdf
8. Digi-Key product pages: MGN-R12-R300-HM https://www.digikey.com/en/products/detail/midwest-machine-tool-supply/MGN-R12-R300-HM/16622745,
   MGN-12-H-Z0-HM .../MGN-12-H-Z0-HM/16623000, MGN-12-C-ZF-HM .../MGN-12-C-ZF-HM/16622924 (stock, shipping cost of the
   marketplace seller).
9. A HIWIN distributor quote for an assembled set (e.g. MGN12H1R300Z0H) and for MGN12H in ZF, and for MGNR12R at 245 mm.

NSK
10. NSK CAD (CADENAS) for PAU12UR and P1U12 rail at 245/300 mm; a US distributor price for both (reference numbers per
    vendor_docs/NSK_PU-PE_miniature_E3327e.pdf, section "Reference number").

igus
11. https://www.igus.com/product/drylin_TS_04?artNr=TS-04-12 (price for 250 and 300 mm, the drawing, CAD),
    https://www.igus.com/product/drylin_TW_04?artNr=TW-04-12 and https://www.igus.com/product/drylin_TWE_04?artNr=TWE-04-12
    (drawing PNG/PDF on igus.widen.net, CAD, load ratings, clearance).

Misumi
12. https://us.misumi-ec.com/vona2/result/?Keyword=SSEBL13 and ?Keyword=SSEB13 - price for rail 12 / H 13 sets at 245, 250,
    300 mm (clearance and light-preload classes), catalogue page and CAD (login).

Others (only if the above do not close the gap)
13. THK RSR12VM / RSR12ZM catalogue and CAD (thk.com); PMI MSC12LM (https://pmi-amt.eu/linear-guideway); TBI Motion
    miniature series; IKO LWL12; Schneeberger MINIRAIL 12; Rexroth miniature size 12; Thomson miniature profile rail
    (thomsonlinear.com answers with a Cloudflare challenge: needs a person).
