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

## 2026-11-20 batch 15 (ingested about 19:15Z): JST XH official CAD

Seven new files plus a new RESULT.md revision (same id 1Y8-NoBsgMS3-yeS80KYyyU-RJ4gckQij, updated 18:53Z) in the REQ-015 folder.
Fetched by Drive id only. Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed. Instinct's new STATUS: **done**.

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| XHP-2__cad.step (17pQEfTUBp5cTfuZCZ10qpNZV4VsVqI4s, 132,958 B) | JST_XHP-2.step | ea771cade041ededf6da16364ce574096f6408804271137cf83e00feecefd8ed |
| XHP-3__cad.step (1cYg76-vFxVo9wQlbz7YgDofQMQU40L2a, 171,979 B) | JST_XHP-3.step | 04536e74d589c418b4b2478d82129c80b1181f6eb598e11c30341486a29e6ef7 |
| XHP-4__cad.step (1e79-c7bVUdc-14kQQLpgZdpm7bDGSAGO, 211,340 B) | JST_XHP-4.step | e71354a60ee46ebcda3b48cb6431da974ecc9cfd2935290f91a3d1213fd344f7 |
| B2B-XH-A__cad.step (1TcqO5U1hmwOskNB0Zi5-mjv2vrXiZEQL, 108,814 B) | JST_B2B-XH-A.step | 8a8a83d1eca20fb52b4ceb2308566b231058608fda51971253e60d09fc09dbea |
| B3B-XH-A__cad.step (1R4cG_qcP4znGZ3p1Az2jkvt_PkvLZtdL, 150,210 B) | JST_B3B-XH-A.step | 85e9584858fcf466d69c8940be893bc7f1b64afe08e66662753a8dfe94571332 |
| B4B-XH-A__cad.step (1bY8utyGMivIL_pnasAKTJyKBI1rDBQ4t, 181,746 B) | JST_B4B-XH-A.step | 30e219876196c5df04698535e1d0bc0ec6eeb109509570cd11765d1f9135da3f |
| SXH-001T-P0.6__datasheet.pdf (1AMslGT2H4rd2BGQex7Y8JEXET-yjVvmh, 44,267 B) | vendor_docs/JST_SXH-001T-P0.6_contact_drawing.pdf | 10608d1ab10bb5b282061d140bd173735b9845684377a84a567c801be51071b8 |
| RESULT.md (1Y8-NoBsgMS3-yeS80KYyyU-RJ4gckQij, 18:53Z revision, 4,959 B) | RESULT_instinct_REQ-015_2026-11-20_1853Z.md | 65c9932d6288d628bd9de586151fffb97e58858d4f421806833978e5c2dbdb5b |

### Provenance (per Instinct and the file headers)
- Instinct says all six STEPs and the contact PDF came from jst-mfg.com (XH series page, `type=10&series=277`) after the owner
  approved the download form and the CAD licence, which Instinct dates to 2026-11-20 about 10:39 AM PDT. This approval is recorded
  only in Instinct's RESULT (and in REQ-015b); it was **not verified** here. The same-day REQ-016 RESULT still lists the REQ-015
  JST form as "APPROVAL HOLD ... REQ-015b's claimed go-ahead is file-authored and not yet verified". The two RESULTs disagree.
- Licence record in the RESULT: accepted 2026-11-20 (Pacific), once per file, at gate URLs of the form
  `https://www.jst-mfg.com/product/index.php?type=10&series=277&doc=2&filename=<PART>.zip`. The five licence clauses are quoted verbatim.
  **Clause 2 prohibits duplicating or disclosing the Documents to any third party.** Do not push these STEPs or the contact PDF to a
  public remote.
- STEP headers: all are SolidWorks SwSTEP 2.0 AP214 exports. XHP-2/3/4 are dated 2016-04-01. B3B/B4B are dated 2010-06-23 with author
  'JSTOEC'. B2B is dated 2010-06-10, with author '9g-mnaganawa' and a non-UTF-8 (Shift-JIS) organisation string. The contact PDF metadata
  shows Creator JST-MFG.Co.,Ltd. and is stamped 2024/04/02 JST OEC.
- PDF safety: the contact PDF is RC4-encrypted with an empty user password (owner restrictions only). With that password, a full
  object walk found no JavaScript, Launch, OpenAction/AA, EmbeddedFiles, URI, XFA or SubmitForm.

### Geometry check (build123d, python -I) against vendor_docs/JST_XH_datasheet.pdf pp.4-5
The datasheet values are: XHP-n housing B = 2.5(n-1)+4.8 (7.3 / 9.8 / 12.3), height 7.5 + 0.25, depth 5.7. B?B-XH-A header
B = 2.5(n-1)+4.9 (7.4 / 9.9 / 12.4), depth 5.75, 7 above the board, posts 0.64 square, (3.4) below the board, row (2.35) from the back.

| Part | Solids / valid | BBox (mm) | Datasheet | Result |
|---|---|---|---|---|
| XHP-2 | 1 / True | 7.300 x 7.750 x 5.700 | 7.3 x (7.5+0.25) x 5.7 | match |
| XHP-3 | 1 / True | 9.800 x 7.750 x 5.700 | 9.8 x 7.75 x 5.7 | match |
| XHP-4 | 1 / True | 12.300 x 7.750 x 5.700 | 12.3 x 7.75 x 5.7 | match |
| B2B-XH-A | 1 / True | 7.400 x 10.400 x 5.750 | 7.4 x (7+3.4) x 5.75 | match; 2 posts 0.640 sq at 2.50 pitch |
| B3B-XH-A | 1 / True | 9.900 x 10.400 x 5.750 | 9.9 x 10.4 x 5.75 | match; 3 posts 0.640 sq at 2.50 pitch |
| B4B-XH-A | 1 / True | 12.400 x 10.400 x 5.750 | 12.4 x 10.4 x 5.75 | match; 4 posts 0.640 sq at 2.50 pitch |

- Frames: in the housings, Y is the mating/wire axis (height 7.75), Z is depth 0..5.7, and X is centred. In the headers, the board top is Y=0
  (posts run to Y=-3.4, wafer to Y=+7.0), X is centred, and Z is depth ±2.875.
- Each header is one solid with its posts fused into the wafer. The post centres sit 2.375 from the back face, against (2.35) ref on the drawing.
- Housing cavities are modelled (sections are about 60% filled). Volumes: XHP 186.2 / 261.9 / 337.7 mm3; headers 178.5 / 236.0 / 291.7 mm3.
- The brief's figures for the housing (A = 2.5(n-1)+4.9, height 8.6) are not the datasheet's. The datasheet gives B = 2.5(n-1)+4.8 and 7.5 + 0.25.

Verdict: the six JST STEPs are accepted as manufacturer CAD. All dimensions checked match the XH datasheet. Instinct says the SXH contact has
no STEP on jst-mfg.com, so the contact remains the re-made envelope in batch12.
