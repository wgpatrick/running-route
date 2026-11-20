STATUS: partial

# REQ-004 RESULT: cheaper 12 mm miniature linear rails and blocks

Baseline (from REQ): genuine HIWIN MGN12 ≈ $125 per 300 mm rail + $59 per MGN12H block at Digi-Key US (≈$184 per rail+block set). Need: 6 rails + 6 blocks.

Regions/currencies as checked: us.misumi-ec.com = US catalog, USD. onetwo3d.co.uk = UK seller, GBP (ex VAT shown). mrosupply.com = US, USD. pmi-amt.eu = PMI's official EU shop, EUR. A part "not listed" below means not listed on the specific regional source checked, not that it does not exist anywhere.

Series-name corrections found while researching (load-bearing for part numbers):
- PMI's miniature series is MSC/MSD, not MSA/MSB (MSA/MSB are PMI's standard-size lines).
- TBI Motion's miniature series is TH (TH12NN standard block, TH12NL long block), per TBI's official 2025 linear-guide catalog. TRH is TBI's standard-size line.
- IKO's MGN-compatible series is LWL; "ML" is IKO's family name (C-Lube Linear Way ML). Size 12 = LWL12.
- THK RSR12: not listed by Misumi US (only RSR3). THK's current caged-ball miniature is SRS12 (long block = N type), which Misumi does sell.

## Candidate table (in progress)

| Maker | MPN | Rail+block set 300mm | 350mm | 400mm | Preload | Accuracy | Stock/lead | CAD | Link |
|---|---|---|---|---|---|---|---|---|---|
| MISUMI own | SSELBL13-300 (set: rail + 1 long block, non-interchangeable) | $185.97 | $204.20 (SSELBL13-350) | $222.43 (SSELBL13-400) | Light preload | High Grade | ships Nov 30 2026 (~11 days) | 2D/3D on page (not yet downloaded) | https://us.misumi-ec.com/vona2/detail/110302586710/ |
| MISUMI own (clearance variant) | SSELBLZ13-300 | $171.90 | pending | pending | Slight clearance (no preload), interchangeable | Standard Grade | ships Nov 30 2026 | 2D/3D on page | same page |
| NSK | PAU12TRS (PU12 block) | rail price pending | | block $49.26 | TRS = light preload per NSK code | pending | In stock at MROSupply | pending | https://www.mrosupply.com/linear-motion/5038190_pau12trs_nsk-bearings/ |
| TBI Motion | TH12NL (long) / TH12NN | pending | | | pending | pending | pending | in official catalog (saved) | https://www.tbimotion.com.tw/en/category/linear-guide-miniature-series |
| IKO | ML12C1HS2 (LWL12 family, long H carriage) at Misumi US | $84.28 (assembly; rail length for this code still to confirm — likely configurable) | | | Standard preload | pending | ships Nov 20 2026 at Misumi US | pending | https://us.misumi-ec.com/vona2/detail/221005387514/?HissuCode=ML12C1HS2 |
| THK | SRS12N (long) — RSR12 not listed on Misumi US EC (only RSR3 checked there); THK direct is quote-only | pending | | | pending | pending | pending | on page | https://us.misumi-ec.com/vona2/detail/221000096246/ |
| PMI | MSC12 / MSD12 | pending — PMI's official EU shop pmi-amt.eu lists MSC-M (EUR); US distributor price still to find | | | pending | pending | pending | pending | https://pmi-amt.eu/linear-guideway-msc-m-lm |
| igus | drylin N NS-27 rail + NW-02-27 carriage | pending | | | n/a (polymer slide) | n/a | pending | igus CAD portal | https://www.igus.com (drylin N) |
| LDO (low-cost #1) | MGN12H stainless, rail+carriage set | £31.14 @ onetwo3D | £33.37 | £34.48 | pending (dremc lists "Precision H") | pending | in stock at onetwo3d.co.uk | dimensioned drawing saved; STEP pending | https://www.onetwo3d.co.uk/product/ldo-linear-rails-mgn12h/ |
| RobotDigg (low-cost #2) | MGN12 440C, rail+carriage | pending (robotdigg.com is JS-rendered; curl gets a shell page, needs browser) | | | pending | pending | pending | pending | https://www.robotdigg.com/product/766 |

## Notes
- MISUMI US sells miniature guides as non-interchangeable sets (rail+blocks together); no separate rail/block pricing. Mounting matches MGN12 pattern: 12 mm rail, M3 holes at 25 mm pitch; rail height H1 = 7.5 mm (HIWIN is 8 mm) — flag for Will.
- On Misumi US EC (us.misumi-ec.com, checked 2026-11-19) there is no separate "economy" miniature guide line; the SSEBZ/SEBS economy naming appears on Misumi's Asia sites. The US own-brand equivalent is the SSELB/SSELBL series above. Not checked: misumi.jp/.cn regional catalogs.
- HIWIN datasheets for comparison: pending (from REQ-002 item 2, in flight).

## Suggested shortlist
Pending price completion — LDO at ~£31/set is the early standout on price; MISUMI SSELBL13 is essentially HIWIN-level pricing.

## Files in this folder
- TBI_LinearGuide__catalog.pdf — official TBI Motion 2025 linear guide catalog (TH12 miniature section at A92). Source: tbimotion.com.tw.
- IKO_LWL__datasheet.pdf — IKO C-Lube Linear Way ML/LWL engineering datasheet (IKO document hosted by distributor Distrelec; IKO's own download centre is JS-gated).
- LDO_MGN12H__drawing.pdf — official LDO MGN12 rail drawing (Rev A), hosted by reseller onetwo3D.
