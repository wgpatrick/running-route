STATUS: partial

# REQ-004 RESULT: cheaper 12 mm miniature linear rails and blocks

Baseline (from REQ): genuine HIWIN MGN12 ≈ $125 per 300 mm rail + $59 per MGN12H block at Digi-Key US (≈$184 per rail+block set). Need: 6 rails + 6 blocks.

Regions/currencies as checked: us.misumi-ec.com = US catalog, USD. igus.com = US (EN), USD. mrosupply.com, anaheimautomation.com = US, USD. matara.com = UK distributor, GBP ex VAT (inc VAT in parentheses). onetwo3d.co.uk = UK seller, GBP. robotdigg.com = China direct, USD. pmi-amt.eu = PMI's official EU shop (unreachable from here 2026-11-19). A part "not listed" below means not listed on the specific regional source checked, not that it does not exist anywhere.

Series-name corrections found while researching (load-bearing for part numbers):
- PMI's miniature series is MSC/MSD, not MSA/MSB (MSA/MSB are PMI's standard-size lines).
- TBI Motion's miniature series is TH (TH12NN standard block, TH12NL long block), per TBI's official 2025 linear-guide catalog. TRH is TBI's standard-size line.
- IKO's MGN-compatible series is LWL; "ML" is IKO's family name (C-Lube Linear Way ML). Size 12 = LWL12.
- THK RSR12: not listed on Misumi US EC (only RSR3 is); THK's current caged-ball miniature is SRS12 (SRS12M standard / SRS12N long).
- CPC block codes: N = standard block, L = long block (per CPC catalog).

## Candidate table (2026-11-19 ~6:05 PM PST)

| Maker | MPN / listing | 300mm | 350mm | 400mm | Preload | Accuracy | Stock/lead | CAD | Link |
|---|---|---|---|---|---|---|---|---|---|
| HIWIN (baseline) | MGNR12R300 rail + MGN12H block | ~$184/set (Digi-Key US, per REQ) | | | per REQ | per REQ | Digi-Key US | HIWIN CAD portal (not fetched) | digikey.com |
| MISUMI own | SSELBL13-300/-350/-400 (non-interchangeable set: rail + 1 long block) | $185.97 | $204.20 | $222.43 | Light preload | High Grade | ships Nov 30 2026 (Misumi US) | 2D/3D offered on product page; download not yet fetched (3dfindit viewer hung this run) | https://us.misumi-ec.com/vona2/detail/110302586710/ |
| MISUMI own (clearance) | SSELBLZ13-300 | $171.90 | | | Slight clearance (no preload), interchangeable | Standard Grade | ships Nov 30 2026 | same | same page |
| NSK | PAU12TRS (PU12; unit scope block vs assembly to confirm) | — | — | — | TRS code | per NSK PU/PE datasheet (saved) | $49.26, in stock at MROSupply US | pending | https://www.mrosupply.com/linear-motion/5038190_pau12trs_nsk-bearings/ |
| TBI Motion | TH12NL (long) / TH12NN | pending distributor price | | | per TBI catalog (saved) | per catalog | pending | in official catalog (saved); STEP pending | https://www.tbimotion.com.tw/en/category/linear-guide-miniature-series |
| IKO | ML12C1HS2 (LWL12 family, long H carriage) at Misumi US | $84.28 (assembly; rail length for this code still to confirm — likely configurable) | | | Standard preload | pending | ships Nov 20 2026 at Misumi US | pending | https://us.misumi-ec.com/vona2/detail/221005387514/?HissuCode=ML12C1HS2 |
| THK | SRS12N (long) | not captured — Misumi US configurator did not converge in bounded attempts; THK direct is quote-only | | | per THK SRS catalog (saved) | per catalog | pending | on Misumi page; official SRS catalog saved | https://us.misumi-ec.com/vona2/detail/221000096246/ |
| PMI | MSC12LM long carriage | rail: Matara UK sells MSC-12-R in 25 mm steps 120–1000 mm; 1000 mm = £42.21 ex VAT; per-length price for 295/320 not captured | | | per PMI catalog (saved) | per PMI catalog | block £51.23 ex VAT (£61.48 inc) at Matara UK; MSC12M std £48.91 ex (£58.69 inc) | STEP pending | https://matara.com/products/linear-motion/linear-rail-and-guides/miniature-type/ |
| igus (comparison, polymer slide) | NS-01-27 rail + NW-02-27 carriage | rail is priced per meter: $74.99/m cut-to-length; 300mm ≈ $22.50 is MY CALCULATION from the per-meter price, not a merchant-quoted total | ≈ $26.25 (calculated) | ≈ $30.00 (calculated) | n/a (sliding, clearance adjustable) | n/a | carriage $11.16; both ship within 5 working days (igus US) | CAD via igus product page CAD tab (not downloaded) | https://www.igus.com/product/drylin-ns-2-27-j?artnr=NW-02-27 |
| CPC (lower-cost #1, Taiwanese brand) | MR12MNSUV0N-300-12.5-12.5 (rail + 1 standard MN block; long = ML code) | $106.00 list, $102.85 @ qty 10 | | | V0N = standard preload per CPC code | per CPC catalog (saved) | in stock at Anaheim Automation US | official catalog saved; STEP via CPC e-catalog pending | https://anaheimautomation.com/cpc-mr12mnsuv0n-300-12-5-12-5.html |
| LDO (lower-cost #2, 3D-printer staple) | MGN12H stainless rail+carriage set | £31.14 | £33.37 | £34.48 | "Precision H" per reseller listing (verify) | per reseller | in stock at onetwo3d.co.uk (UK) | official LDO dimensioned drawing saved; no official STEP found (checked MotorDynamicsLab GitHub) | https://www.onetwo3d.co.uk/product/ldo-linear-rails-mgn12h/ |
| RobotDigg (lower-cost #3, China direct) | SS_MGN12-1H-300 / -1H-350 (rail + 1 long carriage, 440C stainless) | $22 | $24 | (400mm C-carriage listed $28; H variant to confirm) | none stated | none stated | in stock at robotdigg.com | vendor's own dimension drawing (JPEG) + STL models saved (2017 set; mesh, not STEP) | https://www.robotdigg.com/product/766 |

## Notes
- MISUMI US sells miniature guides as non-interchangeable sets (rail+blocks together); no separate rail/block pricing. Mounting matches MGN12 pattern: 12 mm rail, M3 holes at 25 mm pitch; rail height H1 = 7.5 mm (HIWIN is 8 mm) — flag for Will.
- On Misumi US EC (us.misumi-ec.com, checked 2026-11-19) there is no separate "economy" miniature guide line; the SSEBZ/SEBS economy naming appears on Misumi's Asia sites. The US own-brand equivalent is the SSELB/SSELBL series above. Not checked: misumi.jp/.cn regional catalogs. 3dfindit DOES list the economy family "ES-SSELB" (ES Miniature Linear Guides, Long Blocks, Light Preload) in the Misumi CADENAS catalog — CAD download attempt failed this run (viewer page hung the browser renderer twice; search pages fine).
- igus drylin N is a sliding polymer system: near-silent, no lubrication, but lower stiffness/accuracy than ball rails. Included as behavior comparison per REQ.
- RobotDigg and similar no-grade rails: no published preload/accuracy class; drawing is the vendor's own. Treat accuracy as unknown.

## Suggested shortlist (prices still partial — treat as provisional)
Provisional — none of these has verified preload/accuracy grades yet, and suitability for the printer is not verified:
1. LDO MGN12H — ~£31-34 per rail+carriage set (merchant-listed variant prices at onetwo3D, ~6x cheaper than HIWIN baseline), published drawing, known-good reputation in 3D-printer use (Voron BOM standard). UNRESOLVED: preload/accuracy grade (reseller listing says "Precision H", not confirmed against an LDO document). UK seller; US resellers exist (dremc.com.au checked, US sellers pending).
2. RobotDigg SS_MGN12-1H-300/350 — $22-24/set (merchant variant prices), cheapest with a vendor drawing. UNRESOLVED: no stated accuracy/preload grade at all; CAD is the vendor's STL mesh, NOT the STEP format the REQ asks for; quality unverified beyond vendor claims.
3. CPC MR12 — $106/set at Anaheim Automation (US, in stock) BUT that assembly has the STANDARD MN block; the long-block equivalent (MR12ML code) is not yet priced. Official catalog + engineering data; the "industrial but cheaper than HIWIN" option. UNRESOLVED: long-block price, preload grade options, US stock of ML.
igus NS-27 stays as the quiet/low-maintenance outlier (~$34 per 300mm set, calculated from per-meter pricing) — different physics (slide, not ball), flagged in the table.

## Files in this folder
- HIWIN_LinearGuideway__catalog.pdf — official HIWIN linear guideway catalog (hiwin.com, linked from hiwin.us), covers MGN12/MGN12H.
- TBI_LinearGuide__catalog.pdf — official TBI Motion 2025 linear guide catalog (TH12 miniature section at A92). Source: tbimotion.com.tw.
- THK_SRS__catalog.pdf — official THK Models SRS-S/M/N catalog (tech.thk.com), covers SRS12.
- NSK_PU_PE__datasheet.pdf — official NSK Miniature PU/PE data sheet (nsk.com e3327e).
- IKO_LWL__datasheet.pdf — IKO C-Lube Linear Way ML/LWL engineering datasheet (IKO document hosted by distributor Distrelec; IKO's own download centre is JS-gated).
- CPC_MiniatureGuides__catalog.pdf — official CPC miniature linear guides catalog (cpc-europe.com).
- PMI_LinearGuideways__catalog.pdf — PMI's 142-page linear guideway catalog (PMI-authored; hosted by distributor sbn.de — pmi-amt.com exposes no direct PDF), MSC/MSD 12 verified inside.
- LDO_MGN12H__drawing.pdf — official LDO MGN12 rail drawing (Rev A), hosted by reseller onetwo3D.
- RobotDigg_MGN__drawing.jpg — RobotDigg's own MGN dimension sheet (from robotdigg.com download page).
- RobotDigg_MGN12C__cad.stl / RobotDigg_MGN-rail__cad.stl — RobotDigg's published STL models (mesh, not STEP).

## CAD download status
The 3dfindit digitaltwin viewer route is EXHAUSTED for now (hung the cloud-browser renderer across 2 leases / 3 tabs on 2026-11-19; per main's ruling it is not retried without a new signal). Remaining CAD would need a genuinely different official route: vendor CAD portals (HIWIN, THK, NSK, IKO, igus, CPC e-catalog) or Misumi's own CAD tab (needs a Misumi account — not created; no owner approval).

## Still to do
- Prices: TBI TH12 at a distributor; PMI MSC12 rail per-length at Matara (295/320mm) or another distributor; IKO ML12C1HS2 rail-length confirmation; THK SRS12N price (any source); NSK PU12 rail price.
- CAD: Misumi SSELBL13 STEP (3dfindit ES-SSELB or Misumi CAD tab — 3dfindit viewer hung this run, retry next run or via CADENAS partcommunity mirror); PMI/TBI/THK/NSK/igus official STEP; HIWIN MGN12 STEP (CAD portal).
- igus CAD download + drylin N datasheet/catalog PDF.
- Confirm RobotDigg 1H-400 price.
