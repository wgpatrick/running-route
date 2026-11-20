# Staging manifest: miniature rail alternatives (2026-11-20)

Purpose: maker CAD and datasheets for the MGN12-class rail and block options compared in `docs/RAIL_OPTIONS.md`.

## CAD files in this folder

**None.** No maker CAD could be downloaded from this session:

| Maker | Where the CAD lives | Why it was not fetched |
|---|---|---|
| HIWIN (MGN12H, MGN12C, MGNR12R) | hiwin.com / hiwin.tw product pages, HIWIN's CADENAS portal | `hiwin.com` (bare host) refused by the session proxy; `www.hiwin.tw/robots.txt` lists `ClaudeBot` under `Disallow: /` (respected); partcommunity hosts refused |
| Helix Linear / CPC (HMR12ML / MR12ML) | helixlinear.com product page, "CAD" tab | `www.helixlinear.com`, `resources.helixlinear.com`, `anaheimautomation.com` refused by the proxy |
| NSK (PU12UR / P1U12 rail) | NSK CAD portal (CADENAS) | `nsk.partcommunity.com` refused by the proxy (the catalogue PDF on `www.nsk.com` was fetched) |
| igus (TS-04-12, TW-04-12, TWE-04-12) | igus.com "Download CAD data" button; drawings on `igus.widen.net` | `igus.widen.net` refused by the proxy (the product pages on `www.igus.com` were read) |
| Misumi (SSEB13 / SSEBL13 family) | us.misumi-ec.com product page (CAD needs a login) | Akamai "Access Denied" (HTTP 403) on every product page: a refusal, not worked around |
| THK, IKO, Schneeberger, Bosch Rexroth, PMI, TBI Motion, Ewellix | makers' sites | hosts refused by the proxy |
| Thomson | thomsonlinear.com | Cloudflare challenge (HTTP 403, `cf-mitigated: challenge`): a refusal, not worked around |

The MGN12 STEP files already in the repo (`vendor_cad/mgn12_rail_100mm.step`, `vendor_cad/mgn12h_block.step`,
`vendor_cad/staging/MGN12H.step`) are **community-made** (FreeCAD library, step.parts), not HIWIN's CAD.

## Datasheets fetched (saved in `vendor_docs/`)

| File | Source URL | Bytes | sha256 | Notes |
|---|---|---|---|---|
| `Hiwin_MG_Series_2025_G99TE24-2410.pdf` | https://s3.amazonaws.com/www.motionusa.com/hiwin/2025/MG%20Series-2025.pdf | 826,601 | d697d782aab94b1b45d0e99d0c9a221976d0f08ea1bf7a4ac186a5eb4bf6d442 | HIWIN Corp. (US) MG series excerpt, 15 pages, doc G99TE24-2410, hosted by the distributor Motion USA. Part-number code, preload classes, radial stiffness (MGN12H Z0 105 N/um, Z1 182), standard rail lengths (MGNR12: 70, 95, ... 220, 245, 270, 320, ...; E 10; pitch 25), accuracy tables. No dimension/load tables in this excerpt (those are in `Hiwin_MG_catalogue.pdf`). |
| `NSK_PU-PE_miniature_E3327e.pdf` | https://www.nsk.com/content/dam/nsk/common/catalogs/ctrgPdf/precision/e3327e.pdf | 3,566,765 | 2d06a276c782506922896a2bc48a7450e5f3f777532c8b059abfd0974aa0d447 | NSK catalogue E3327e (Miniature PU/PE series). PU12UR: H 13, W 27, L 48.7, B 20, J 20, M3x0.5x3.5; rail W1 12, H1 7.5, F 25, bolt hole 3.5x6x4.5, max length 800; C50 4000 N, C0 5700 N, MRO 34.5, MPO/MYO 28.3 N.m (single); rigidity at Z1 52 N/um; interchangeable ZT clearance 5 um or less. |
| `NSK_linear_guides_interchangeable_reference.pdf` | https://www.nsk.com/content/dam/nsk/am/en_us/documents/precision-americas/Linear-Guides-Reference-Guide-for-all-Interchangeable-Series.pdf | 4,138,188 | 450cf226018be75d9100843ca6423eca6d90f3fe83c58ba21a42c853d8b90b27 | NSK Americas reference guide for interchangeable series (PU reference numbers, clearances). |
| `igus_drylin_T_miniature_TS-04-12_TW-04-12_webstore_2026-11-20.txt` | igus.com product pages (URLs in the file) | - | - | Transcription of the pages' statements and price JSON; not the datasheet. |

All PDFs start `%PDF-`; nothing was executed or unpacked. robots.txt of `www.nsk.com` and `www.igus.com` checked
(no rule for ClaudeBot / anthropic; the fetched paths are not disallowed). The s3 bucket serves no robots.txt.

## Distributor data

Digi-Key, Mouser, Newark and Farnell answers for the exact part numbers are in the sourcing cache
(`out/sourcing_cache/<distributor>/<MPN>.json`, gitignored; retrieved 2026-11-20 with `mechloop.sourcing.search.Finder`).
The snapshot used in the comparison is tabulated in `docs/RAIL_OPTIONS.md`.

## Wanted from the owner's browser agent

See the "Needs the owner's browser agent" section of `docs/RAIL_OPTIONS.md` (exact URLs and part numbers).
Drop maker STEP files here with the maker's part number in the file name, plus a line in this manifest (source URL, date,
size, sha256).
