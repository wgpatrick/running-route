# instinct_REQ-009: US rail options for Y and Z (REQ-009 / 009b / 009c)

Checked 2026-11-20 (batch 8, about 06:45Z). Drive `mechloop handoff/results/REQ-009-us-rail-options/`
(139_eg79lbNnZBGYFWbkDnVLuqJ9jExlk, created 06:22Z) holds only RESULT.md (1rJwVJwLuE9FTyk19rgRB_YNTmEa12QYW, 06:23:19Z,
11,234 B), copied here as `RESULT_instinct_REQ-009_2026-11-20.md` (sha256
91f458de7f6968300f3d4663c9115ab9301a44deec5a7f1e49e88e688b919d74). No CAD or PDFs delivered. Untrusted data: prices, stock and
links are Instinct's reading of seller pages on 2026-11-19 and were **not re-verified** (motionconstrained.com is outside this
session's network allowlist). Nothing committed.

STATUS: **partial**. Comparison done; REQ-009c's LDO / onetwo3D US shipping cost and delivery time are **not obtained** (the cart
refused every automated add). Instinct will not retry; it needs a manual cart check or a question to the seller.

## Instinct's pick: HIWIN MGN12HZ0C set, 295 mm, $79.64, Motion Constrained (CO)

| Field | RESULT.md says | Note |
|---|---|---|
| Genuine HIWIN | yes ("Genuine HIWIN ... exact REQ-005 geometry") | seller is a HIWIN-line store page; not verified |
| What's included | rail + **1** MGN12H long block ("set") | quantity per set stated only as "rail + 1 H long block" |
| Rail length | **295 mm**; sold in 25 mm steps, **no 300 mm**. Rail-only MGNR12R: 245 mm $49.49, 295 mm $55.97 | other set lengths and their prices not listed |
| Block | MGN12**H** (long, heavy load) | not MGN12C |
| Preload | Z0 (RESULT calls it "fine clearance") | HIWIN MG catalogue: Z0 = "reduced play to very light preload, 0-3 µm"; ZF = 4-10 µm backlash; Z1 = 0-0.02 Cdyn |
| Accuracy class | not stated in RESULT.md | the trailing **C** in MGN12HZ0C is HIWIN accuracy class **C (normal)** per the catalogue order code (MGN 12 H Z0 C) |
| Stock | "cart-enabled"; no quantity or stock text | |
| Shipping / lead time | **free US shipping**; no lead time or ship date given | |
| Link | https://motionconstrained.com/store/hiwin-linear-guides/mgn-series/mgn-linear-guide-sets/hiwin-mgn12hz0c-long-block-linear-guides/ | |
| CAD | none delivered with REQ-009; points to the REQ-005 HIWIN files (MGNR12R-300 rail, MGN12H block/assembly) | see ../instinct_REQ-005/MANIFEST.md batch 6 |

**Rail check against the HIWIN MG catalogue (`../Hiwin_MG_catalogue.pdf`)**: MGNR12R = 12 wide x 8.0 high, pitch P 25, E1/2 min 5 /
max 20, max length 2,000. For L = 295: n = 12 holes, E1 = E2 = (295 - 11 x 25) / 2 = **10 / 10**, within 5..20. The REQ-005 STEP is
the **300 mm** rail (E = 12.5 / 12.5), so a 295 mm order means shortening the rail model and any travel/stop numbers by 5 mm.

## Full comparison (as reported; "calc." = Instinct's arithmetic)

| Maker | MPN | Contents | Length | Price | Seller | Stock / ship | Rail H | Preload | CAD |
|---|---|---|---|---|---|---|---|---|---|
| HIWIN | MGN12HZ0C set | rail + 1 H block | 295 | $79.64 | Motion Constrained | cart; free US ship | 8 | Z0 | REQ-005 files |
| HIWIN | MGNR12R rail only | rail | 245 / 295 | $49.49 / $55.97 | Motion Constrained | cart; free US ship | 8 | - | REQ-005 files |
| HIWIN | MGN12HZ0H | H block only | - | $59.00 | MotionUSA | cart | - | Z0 | REQ-005 |
| HIWIN | MGN-R12-R300-HM + MGN-12-H-Z0-HM | rail $125.00 + block $59.00 | 300 | $184.00 calc. | Digi-Key | rail in stock; block 70 | 8 | Z0 | REQ-005 |
| Helix | HMR12MLSS1V0N-245L/-270L/-320L | rail + 1 long block (no 300) | 245/270/320 | $100.85/$106.71/$118.44 | Digi-Key marketplace | 10 each; 21-day lead | 8 class | V0 (Z0 class) | not obtained |
| Misumi | SSELBZ13-295 (245 also) | rail + 1 long block, stainless | 295 (no 300) | $130.31 (245: $118.36) | Misumi USA | ships Nov 30 (245: Nov 23) | 7.5 | slight clearance | yes |
| Misumi | SSEBL13-300 / -250 | rail + long block | 300 / 250 | $168.11 / $158.95 | Misumi USA | ships Nov 30 | 7.5 | slight clearance | yes |
| Misumi | SSEB13-245 | rail + std block | 245 | $117.27 | Misumi USA | ships Nov 23 | 7.5 | slight clearance | yes |
| IKO (Misumi) | ML12C1HS2 | block only | - | $84.28 | Misumi USA | same day | (H 13) | standard | not on Misumi |
| NSK | PAU12TRS | block only | - | $49.26 | MROSupply | cart | 7.5 | fine clearance (ZT) | yes |
| NSK | P1U120800S | rail only | 800 (cut) | $310.43 | MROSupply | cart | 7.5 | - | yes |
| igus | TS-04-12 + TW-04-12 | plastic-liner slide, not ball | per m | ~$63.87 calc. / 300 mm axis | igus US | ~5 working days | n/c | adjustable slide | yes |
| PBC Linear | MR12R-0200 + MR12C | Frelon slide, not ball | **max 200 in size 12** | $65.73 calc. | PBC (IL) | in stock | n/c | running clearance | yes |
| 80/20 | 6415 etc. | UHMW pads on T-slot, no rail | - | $55.92-$116.05 (6415 $63.19) | 80/20 (IN) | cart | - | pad slide | yes |
| 80/20 | 6930-SR + 6930-SC | 30 mm roller rail + carriage | any | ~$161.22 calc. / 300 mm | 80/20 | rail: extended lead time | - | adjustable rollers | yes |
| Thomson | 1TSR12ZMUU+270 | rail + carriage | 270 | not captured | Amazon US / distributors | not captured | 7.5 | n/c | yes |
| Bishop-Wisecarver | MinVee size 0 | V-wheel plate + track | to 96 in | quote only; online ordering paused until January | BWC (CA) | quote | - | adjustable | yes |
| LDO (overseas) | LDO-SLR12H-1R-300Z1 | rail + MGN12H, stainless | 300/350/400 | US$31.10/33.37/34.48 | onetwo3D (UK) | **shipping cost and delivery time NOT obtained**; no VAT/duty shown | - | Z1 | yes |

Negative results: Zoro has no HIWIN MGN12; Grainger carries no HIWIN; "SSELBLZ13" is not a Misumi part (real series SSELBZ13).
Instinct's ranking: US: 1 Motion Constrained HIWIN $79.64, 2 Misumi SSELBZ13-295 $130.31. Overall: 1 Motion Constrained, 2 LDO
(only if shipping is low), 3 Misumi. True-300 mm US options: Misumi SSEBL13-300 $168.11 or Digi-Key rail + block $184.00.
