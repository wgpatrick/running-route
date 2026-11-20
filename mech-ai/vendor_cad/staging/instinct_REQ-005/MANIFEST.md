# instinct_REQ-005: rails addendum (Helix / CPC MR12, HIWIN MGN12H 245 mm, NSK, igus, Misumi), first (interim) delivery

Ingested 2026-11-20 (batch 5) from Google Drive `mechloop handoff/results/REQ-005-rails-addendum-helix-hiwin/`
(folder 1_-rIetDBexZ6IT3MwJJwYEeNrE4yaU8_), 4 files, last modified 03:01:58Z. Collected by Instinct (the owner's browser
agent). Instinct's STATUS: **partial** ("INTERIM snapshot ... 0 of 5 fully"). RESULT.md as delivered is
`RESULT_instinct_REQ-005_2026-11-20.md` (sha256 3425a6fed74222298c615f78fc2c9f5328cc3305eeba6a006485549a39ad73a5). Everything was
handled as untrusted data.

Staged for review only. Nothing has been copied to `vendor_cad/inbox/`. Nothing committed.

**No STEP or other CAD was delivered** (Helix CAD library loads client-side; HIWIN configurator download not reached; Misumi
CAD needs an unapproved account; NSK / igus CAD pending).

Method (PDFs): header / %%EOF, raw and inflated-stream scan, pypdf object-graph walk for /JavaScript, /JS, /Launch,
/EmbeddedFile, /RichMedia, /XFA, /SubmitForm, /OpenAction, /AA. All three PDFs: **no JavaScript, actions, embedded files
or link annotations**; not encrypted. None duplicates a file already in vendor_docs (sha256).

## Documents copied to vendor_docs/ (unchanged)

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 1 | CPC_MR12_spec_AnaheimAutomation.pdf | CPC-MR12__spec.pdf | 52e088be76a263bdf7fb3faca244058b65e06ae258dc24ab2ee8494e78fb4699 | 2 p, Anaheim Automation (US CPC distributor) MR12 dimension / load table for SS and SU seals, MN / ML / WN / WL blocks, rails 100 to 1000 mm |
| 1 | CPC_MR_miniature_guides_catalog_27p.pdf | CPC-MR__catalog.pdf | a29238cee89b08ffdcdee3a1e6cff1494c5710e915aceafdc1da3227749116ea | 27 p CPC MR catalogue (two-page spreads). **Not the same file** as REQ-004's `CPC_miniature_guides_catalog.pdf` (32 p, 028923c0...). Tables are images (accuracy p.5, preload p.6, rail lengths p.10) |
| 1 | Helix_HMR_miniature_linear_guides_catalog.pdf | Helix-Miniature-Linear-Guides__catalog.pdf | 3681dac553ae831d9285449922f5c51c538cbf67779e9a31ffa1d64be9d10173 | 40 p Helix Linear (CPC-made, HMR = CPC MR). Accuracy / preload PDF p.7, rail lengths p.15, HMR-M SS table PDF p.20-21 (printed p.18-19) |

## Size-12 facts extracted (catalogue values, checked against HIWIN `vendor_docs/Hiwin_MG_catalogue.pdf` GW-11-5-EN-2207-K)

| | CPC MR12ML SS (Anaheim spec) | Helix HMR 12ML SS | HIWIN MGN12H + MGNR12R |
|---|---|---|---|
| Overall height H (rail base to block top) | 13 | 13 | 13 |
| Rail W1 x H1 | 12 x **7.5** | 12 x **7.5** | 12 x **8.0** |
| Rail hole pitch / counterbore D x d x h | 25 / 6 x 3.5 x 4.5 (M3) | 25 / 6 x 3.5 x 4.5 | 25 / 6 x 3.5 x 4.5 |
| Rail end distance L2/L3 (E) min-max | 4 - 20 | 4 - 20 | 5 - 20 |
| Block width W / rail edge to block edge | 27 / 7.5 | 27 / 7.5 | 27 / N 7.5 |
| Block length L / body L1 | **47.8** (SU: 48) / 34 | **47.6** (SU 47.6; EE/SUE 49) / 34 | **45.4** / 32.4 |
| Block mounting holes | 20 x 20, M3 x 3.5 | 20 x 20, M3 x 3.5 | 20 x 20 (B x C), M3 x 3.5 |
| C (dynamic) | 3.24 kN at 100 km (= 4.08 kN at 50 km) | 3,240 N C100 | 3,720 N at 50 km |
| C0 (static) | 5.63 kN | 5,630 N | 5,880 N |
| Static moments roll / pitch / yaw | 34.9 / 30.2 / 30.2 Nm | 30.2 / 30.2 / 34.9 as printed (column order differs from CPC) | M0X 38.2 / M0Y 36.3 / M0Z 36.3 |
| Block / rail weight | 0.11 lb (50 g) / 0.40 lb per 300 mm | 51 g / 602 g/m | 50 g / 650 g/m |
| Accuracy classes | P / H / N: H ±10/±20/±40 µm, ΔH 7/15/25, W2 ±15/±25/±40, ΔW2 10/20/30 | same table; N stocked | C / H / P (LDO drawing: C ±40 µm) |
| Preload (size 12) | V0 clearance +5~0 µm, VS standard +2~0, V1 light 0~-5 | same; V0 stocked | ZF 4-10 µm backlash, Z0 0-3 µm, Z1 0.02 C |
| Stiffness | **not published** (qualitative only) | **not published** | MGN12H radial 63 N/µm (Z0), 81 N/µm (Z1) |
| Standard rail lengths | 70, 95, 120, 145, 170, 195, 220, **245**, 270, 320, 370, 470, 570; Lmax 1000 (butt-joint beyond) | same list, printed as 96 / 196 for 95 / 195 (likely typo); Lmax 1000 | any length to 2000 |
| Speed / acceleration | SS/SU: 3 m/s, 250 m/s² (40 m/s² at V0); EE: 5 m/s, 300 m/s² (60 at V0) | same | - |
| Operating temperature | -40 to +80 °C (short term 100 °C) | - | - |

Drop-in assessment: **mechanically interchangeable with MGN12H for the carriage mounting** (same 13 mm height to the block
top, same 27 mm width and 7.5 mm reference offset, same 20 x 20 M3 x 3.5 block holes, same rail width, 25 mm pitch and
M3 counterbore). Differences: the rail is **0.5 mm lower** (7.5 vs 8) so anything that references the rail top (end
stops, wipers, clamps) moves; the long block is **2.2 to 2.4 mm longer** (47.6 / 47.8 vs 45.4), which costs that much
stroke; rails above 1000 mm need a butt joint; the ordered codes are V0 (clearance) and N (normal) grade, not a preload.
Load ratings are about the same once the 100 km vs 50 km rating basis is converted.

Corrections to RESULT.md (not verified beyond the catalogues):
- "SS series ... Qmax 250 m/s² (60 m/s² at V0)" should read 40 m/s² at V0; 60 m/s² is the EE type (both catalogues).
- RESULT.md calls the Helix p.18 table the source; in the PDF it is p.20-21 (printed p.18-19).
- REQ-004 RESULT.md says "V0N = standard preload". Per both catalogues V0 = clearance and N = normal accuracy.

## Prices / stock in RESULT.md (as delivered; nothing verified here)

| Item | Result |
|---|---|
| Helix HMR12MLSS1V0N-245L/-270L/-300L/-320L single-unit price / MOQ / lead | **PENDING** (Digi-Key MOQ 10 per REQ; Helix store lists only HMR2-7) |
| CPC long block (MR12ML) | **not priced**. Only the standard-block set is priced (REQ-004): MR12MNSUV0N-300 $106.00, $102.85 at qty 10, in stock at Anaheim Automation |
| LDO US availability | **not established**. Only UK onetwo3D in stock at £31.14 / £33.37 / £34.48 ex VAT (300/350/400) per REQ-004 |
| HIWIN MGN12H ZF block + 245 mm rail | **PENDING**; HIWIN STEP needs configure.hiwin.com and maybe an account (owner approval). Baseline per REQ: about $184 per 300 mm rail + MGN12H at Digi-Key |
| igus drylin T | TS-04-12 rail $119.84 (length basis unconfirmed), TW-04-12 $27.92, TWE-04-12 $46.29 |
| Misumi SSEB13 / SSEBL13 | PENDING; REQ-004 SSELBL13 300/350/400 = $185.97 / $204.20 / $222.43; CAD blocked (account) |
| NSK PU12UR / P1U12 | CAD and price PENDING |

Outstanding: every STEP; all prices above marked PENDING / not priced.
