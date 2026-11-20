# instinct_REQ-018: filament spool and feed path (interim)

Ingested 2026-11-20 (batch 16, about 23:15Z). Drive folder `REQ-018-spool-and-filament-path` (1LUF4BGyRvbsBEL23O5ovpvjlOsvmyYrf).
Fetched by Drive id only. Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed. Text only: no CAD or PDFs were delivered.

Instinct's STATUS: **partial** (research-in-progress snapshot).

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1Xd6q51QZ-nGX2bJTv1bws0IbmIcM52Um, 3,676 B) | RESULT_instinct_REQ-018_2026-11-20.md | 26941a6ba3b11f56f7f959cb0d231f4af4dc050c80b5cbdce803bc1d3187cf97 |

## Per-item state (per Instinct, not verified; prices as displayed 2026-11-20, USD)
- **Item 1, 1 kg spool: OPEN.** Instinct found no maker drawing or STEP. The Overture wiki gives the dimensions as text: 200 OD x 65.6 wide, 55 hub, about 147 g empty. Next step is Prusa Printables and Polymaker/eSUN support.
- **Item 2, PTFE: done.** Capricorn XS is ID 1.90 ±0.05 / OD 3.95 ±0.05, per captubes.com. The maker does not publish a minimum bend radius. RobotShop sells it at $12.18 per 1 m, with 93 in stock. The alternative is Capricorn TL, ID 2.05 ±0.05 / OD 3.95 ±0.05.
- **Item 3, push-fit couplers: OPEN.** The thread of the E3D Roto Bowden "bowdaptor" is not stated. The plan is to measure it from E3D's Printables reference CAD; compare `vendor_cad/e3d_roto_reference_cad.step` and `staging/E3D_Roto_Bowden_reference.step`, which are already in the repo. The McMaster PC4-M5/M6/M10 candidates have not been pulled yet.
- **Item 4, 608 bearing: OPEN.** The pick is NSK 608ZZ via Misumi: $2.54, 560 in stock, ship Nov 21; 8 x 22 x 7, 3300 N. Misumi has no CAD for it. The next step is the SKF 608-2RSH STEP through the existing 3dfindit login, plus the skf.com PDF.
