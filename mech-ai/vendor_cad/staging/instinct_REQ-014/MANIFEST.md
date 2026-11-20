# instinct_REQ-014: PEM nut CAD via Bossard; SendCutSend cart for RP03/RP04

Ingested 2026-11-20 (folder state at about 15:15Z). The Drive folder `mechloop handoff/results/REQ-014-bossard-pem-and-sendcutsend-cart`
(1q3mYOgMuesTlqiKL3pHd0fxZDrbDfdLU) holds only RESULT.md. It was saved as text and handled as untrusted data.

| Delivered as (Drive id, modified, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1o3MXYPd8IoYfY1XjdygDAofhF46ZVrjF, 2026-11-20T15:10:42.649Z, 5,996 B) | RESULT_instinct_REQ-014_2026-11-20.md | 493f41289112437863fba943bff26a92b32230293f5a705949122ebf0b64db3c |

Instinct's STATUS is **partial**, and no files were delivered.

1. PEM S-M3-0 / S-M3-1 via Bossard: **blocked**. Bossard lists only plated variants (S-M3-0ZC is out of stock and quote-only,
   with no CAD). A quote needs an account, so Instinct stopped there.
2. The PCBWay RP03/RP04 review comments are quoted from existing batch01 records (no new submission). RP03: no 5052 in 2.29 mm
   (2 / 2.5 mm available). RP04: no 6061 in 3.18 mm (3.2 available). PCBWay showed $12.45 as the prequote, then $25.11 at qty 1.
   No qty-10 quote exists and nothing was paid.
3. SendCutSend: these are the **historical** 2026-11-19 quotes, not a fresh cart. RP04 qty 10 was $90.50 and RP03 qty 10 $68.50
   (with deburring, plus a flange-length DFM error). Shipping is unknown because checkout was not entered.

Open owner decisions per Instinct: a fresh SendCutSend cart, and the plain S-M3-0/-1 route via PEM direct (pending earlier).

## 2026-11-20 batch 12 (ingested about 16:15Z)

Three new files in the REQ-014 folder (1q3mYOgMuesTlqiKL3pHd0fxZDrbDfdLU), fetched by Drive id only (folder not re-listed).
Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed. Instinct's new STATUS: **partial**. Item 1 is
"resolved via owner-approved plated alternative S-M3-0ZI". Instinct says the owner approved this by iMessage on Nov 20;
that is Instinct's claim and is **not verified** here. Items 2 and 3 are unchanged: existing batch01 records, no new
submissions, SendCutSend shipping still unknown.

| Delivered as (Drive id, modified, size) | Staged as | sha256 |
|---|---|---|
| S-M3-0ZI__cad.step (1gDZObejlT0rxwMj5M6IW0Bja3ZPzYifo, 2026-11-20T15:56:14.575Z, 765,355 B) | McMaster_95185A520_PEM-S-M3-0ZI.step | 7912c5cf540bb30510cfb02c3d2dc9e5e5986f7b49a17d8445efb02c44263c43 |
| S-M3-0ZI__drawing.pdf (1FavqgaxpsqPUehM56AnHJiuG45Dl_Mb-, 2026-11-20T15:56:15.745Z, 102,125 B) | ../../../vendor_docs/McMaster_95185A520_PEM-S-M3-0ZI_drawing.pdf | 44ce64cfd47805c9e5a5303515adb77f2b590b0b42a9575f75e32c5ebbedd3e5 |
| RESULT.md (1o8MTud_uP3sb3cvOxEXmnpdfu2fT3UvU, new file id, 2026-11-20T15:56:28.881Z, 6,009 B) | RESULT_instinct_REQ-014_2026-11-20_1556Z.md | 69347ed59dd9c781efc75af1aed08fb01c49efad514b8b4374aabb368f96c604 |

Provenance as stated by Instinct: official McMaster-Carr CAD and drawing for McMaster 95185A520, which McMaster
cross-references to PEM S-M3-0ZI (zinc-plated steel self-clinching nut, M3 x 0.5). $3.75 per pack of 25, in stock, no purchase.
PEM's catalog STEP needs a personal-information form, which was not submitted. The STEP header agrees: SolidWorks 2024 SwSTEP
AP214, FILE_NAME "95185A520_Zinc-Plated Steel Press-Fit Nut for Sheet Metal", McMaster Carr Supply.

Checks: the drawing PDF is 1 page from SOLIDWORKS PDF Publisher, with only 2 /URI links (no JavaScript, Launch, OpenAction or
embedded files, not encrypted). build123d: **1 solid, valid**, 263 faces, bbox 6.35 x 6.35 x 2.27 mm (z 0 to 2.27, shank down),
volume 46.74 mm3. The thread is modelled (a helical 3.0 mm major-diameter face set at 0.5 mm pitch).

| Feature | STEP | McMaster drawing | PEM S-M3-0 catalog | Result |
|---|---|---|---|---|
| Thread | M3 modelled, 3.0 major, 0.5 pitch | M3 x 0.5 | M3 x 0.5 | match |
| Head dia (E) | 6.35 | 6.35 | 6.35 | match |
| Head height (T) | 1.50 (z 0.77 to 2.27) | 1.50 | 1.50 | match |
| Shank / clinch dia (C) | 4.20 (z 0 to 0.20, then a 4.075 undercut groove) | 4.20 | 4.20 max | match |
| Shank length (A) | 0.77 | 0.77 | 0.77 max | match |
| Panel hole | n/a | drill 4.22 | 4.22 | match |
| Min sheet | n/a | 0.8 | 0.8 | match (0.77 shank < 0.8 sheet, as designed) |
| Overall height | 2.27 | 0.77 + 1.50 | 2.27 | match |

Result: **PASS**. A geometric match for the plain S-M3-0. Plating (ZI = zinc) differs from the plain part originally asked for.
