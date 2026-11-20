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
