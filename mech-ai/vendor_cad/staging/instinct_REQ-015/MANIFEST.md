# instinct_REQ-015: maker STEP for JST XH, Molex Mini-Fit Jr, Phoenix DIN rail

Ingested 2026-11-20 (batch 14, about 18:15Z). Drive folder `REQ-015-jst-molex-phoenix-step` (1VCBDeYJwDDkOHQIvsY4zNF4tm7ejUW7f).
Fetched by Drive id only. Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed.

Instinct's STATUS: **partial**. Items 2 (Molex) and 3 (Phoenix) are delivered. Item 1 (JST XH) is still held: jst-mfg.com
requires a click-through licence and a personal-data form, and 3dfindit has no JST catalog. That needs the owner's OK.

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| 39-01-2020__cad.step (1TxwVop47Q3ucqMQbzZ-kYx1lG6qQXMLD, 108,730 B) | Molex_39-01-2020.step | 014d90a197325f951006c9bddb7eb2df30bfdb2a4070f0c7cbe77e257af32d66 |
| 0801733__cad.step (1x5W4YSOZ2vpmiPrTn1tOagMVOJ9drbMc, 521,901 B) | Phoenix_0801733_NS35-7.5-PERF-2000.step | 41c4b189fde8ec8b0ac45feb14be7f22843073105c70b4a15673cf56ee04aaed |
| RESULT.md (1Y8-NoBsgMS3-yeS80KYyyU-RJ4gckQij, 3,175 B) | RESULT_instinct_REQ-015_2026-11-20.md | b7adcdf582d659e4250555e41f1d858c391e6031ee18ed995b3c980852490991 |

## Stated provenance (per Instinct, not verified)
- Both STEPs came from 3dfindit (CADENAS PARTcommunity), using the owner's existing account. Instinct says no new
  registration was made and no new terms were accepted. The CADENAS terms text ships inside each zip, but the zips were not delivered.
- Molex 39-01-2020: CADENAS generation order **22026112018464072700088d0b6156e**, catalog row "Molex 39012020, Mini-Fit Jr.
  Receptacle Housing, Dual Row, 2 Circuits, UL 94V-2, Natural". The zip also held 39012020.pdf (the datasheet), which was not uploaded.
- Phoenix 0801733: CADENAS generation order **22026112018380171964729d0b6156e**. Instinct says 522 KB; the actual size is 521,901 B.
- What the STEP headers show: both files are AP214 from CADENAS PARTsolutions (ST-Developer), and the author field in both is
  "License CC BY-ND 4.0". The Phoenix FILE_NAME is '0801733' with time_stamp 2026-11-20T18:38:11+01:00. That is 17:38Z, which
  matches the order id read as CET. The Molex FILE_NAME is 'psolqas_6036_9985' with time_stamp **2024-07-16**T16:22:07+02:00,
  which suggests a cached or pre-generated model. Its PRODUCT is '39012020wbm000_01'.

## Geometry check (build123d 0.13.0, python -I)

| Check | Molex_39-01-2020.step | Phoenix_0801733_NS35-7.5-PERF-2000.step |
|---|---|---|
| Solids / faces | 1 / 84 (82 planar, 2 cylindrical) | 1 / 342 |
| is_valid / BRepCheck | True / True | True / True |
| BBox (mm) | 5.4 x 19.6 x 14.4 | 2000.0 x 35.0 x 7.5 |
| Volume (mm3) | 871.78 | 86,988.08 (mean section 43.49 mm2) |
| vs drawing / datasheet | Width 5.4 = dim A for 2 ckt (5.40). Overall 19.6 (.77) matches. Body 10.7 (.42) matches. Body height 9.6 (.38) matches. Latch 8.5 (.33) matches. | Width 35, height 7.5 and length 2000 match. 79 slots, each 15.00 x 6.20, at 25.00 pitch (centres 25 to 1975) match. Top and bottom base faces differ by 2000 x 2.0 mm2, which means 1.0 mm wall thickness. This matches. |
| Notes | **Simplified envelope model.** The body is solid with no terminal cavities (point classification of the x-y and x-z sections). As a result, the 2 circuits and the 4.20 mm pitch cannot be checked from the geometry. It is fine for fit and clearance, but not for terminal or pin positions. | Full perforated profile. Use it as is, or cut it to length. |

Verdict: both are accepted as manufacturer CAD for fit. The Molex model is an outline only.
