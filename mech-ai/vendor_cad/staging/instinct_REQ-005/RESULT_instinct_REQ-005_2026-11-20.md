# RESULT — REQ-005: rails addendum

STATUS: partial

INTERIM snapshot (research in progress). Requirements fulfilled so far: 0 of 5 fully;
catalog/spec and several prices landed below. Updated as work completes.

All prices USD, sources checked 2026-11-19 PM PST. CAD = official maker CAD only.

## 1. Helix HMR12MLSS1V0N-245L / -270L / -300L / -320L (CPC/Chieftek-made)
| What | Result |
|---|---|
| Single-unit price / MOQ / lead | PENDING — Digi-Key (MOQ 10 per REQ) and motion.com pricing not yet captured; Helix's own store does not list HMR12 (store covers HMR2–7 only) |
| Catalog | Helix-Miniature-Linear-Guides__catalog.pdf (helixlinear.com resources; the REQ's hubfs link is dead, this is the current official file) |
| STEP per length | PENDING — Helix CAD library page loads client-side; under investigation |
| Rail hole pitch | CONFIRMED 25 mm, M3 counterbored holes (6 x 3.5 x 4.5), catalog p.18 |
| Block mounting pattern | CONFIRMED 20 x 20 mm, four tapped M3 x 3.5 holes (HMR 12ML) — MGN12H-compatible as expected. Block W=27, L=47.6, rail H1=7.5, W1=12 |
| Load ratings (12ML SS) | C100 = 3,240 N dynamic, C0 = 5,630 N static; MA/MB = 30.2 Nm, MC = 34.9 Nm; block 51 g; rail 602 g/m |
| CPC MR12 catalog/spec | CPC-MR__catalog.pdf + CPC-MR12__spec.pdf (anaheimautomation.com). Accuracy grades P/H/N (H tol ±10/±20/±40 µm, ΔH 7/15/25, W2 ±15/±25/±40, ΔW2 10/20/30). Preload classes V0 clearance (+5–0 µm @ size 12), VS standard (+2–0), V1 light preload (0–-5). Speed: SS series Vmax 3 m/s, Qmax 250 m/s² (60 m/s² at V0 preload). Requested SKU decodes: SS end-seal series, V0 preload, N accuracy grade. Stiffness: catalog states preload raises stiffness; no per-size stiffness table — treated as not published |

## 2. HIWIN MGN12H / MGN12C blocks, MGNR12R rail 300 mm + 245 mm
| What | Result |
|---|---|
| STEP (hiwin.com CAD download) | IN PROGRESS — hiwin.com routes CAD to configure.hiwin.com (DriveWorks). Guest configuration possible without an account; download step not yet reached (page notes "Signup required at end" — an account would need Will's approval) |
| Distributor price: MGN12H ZF preload block, 245 mm rail, assembled set | PENDING |

## 3. NSK PU12UR block / P1U12 rail
| What | Result |
|---|---|
| CAD | PENDING (nsk.com direct CDN works; REQ-004 folder already holds official NSK_PU_PE__datasheet.pdf) |
| US distributor price | PENDING |

## 4. igus drylin T (igus.com US, verified page data)
| Part | Price (USD) | CAD | Drawing |
|---|---|---|---|
| TS-04-12 rail | $119.84 listed (length basis not yet confirmed — 250/300 mm configured price pending) | pending | pending |
| TW-04-12 carriage | $27.92 | pending | pending |
| TWE-04-12 carriage | $46.29 | pending | pending |

## 5. Misumi SSEB13 / SSEBL13 at 245 / 250 / 300 mm
| What | Result |
|---|---|
| Price | PENDING on Misumi US configurator. Prior REQ-004 finding (same family): SSELBL13-300 $185.97 / -350 $204.20 / -400 $222.43 (light preload, High Grade, ships Nov 30 2026) |
| CAD | CONFLICT NOTED: the REQ says "3Dfindit is fine", but the 3Dfindit/partcommunity (CADENAS family) route is technically exhausted (viewer repeatedly hung the browser; per ruling it is not retried without a new signal). Misumi's own CAD tab needs a Misumi account — not approved, not created. So CAD is blocked unless Will approves a Misumi account |

## Blockers / decisions
- TraceParts portal access also gates nothing in this REQ, but HIWIN configurator download may require an account (would need approval).
- No purchases made; no accounts created; no terms accepted. Quotes/questions by web form not yet used.
