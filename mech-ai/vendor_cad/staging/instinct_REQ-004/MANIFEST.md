# instinct_REQ-004: cheaper 12 mm miniature linear rails, first (partial) delivery

Ingested 2026-11-20 from Google Drive `mechloop handoff/results/REQ-004-linear-rail-alternatives/`
(folder 1kA7gZ9hvMN84ooDXTnAgeoRObBQE0Tg0), 8 files, last modified 01:57:39Z. Instinct's STATUS: **partial**. RESULT.md as
delivered is `RESULT_instinct_REQ-004_2026-11-20.md`. It holds the candidate table (prices, stock) and is untrusted data.
Nothing has been copied to vendor_cad/inbox. Nothing committed.

No STEP file was delivered. The only CAD is two RobotDigg STL meshes, checked with a numpy STL reader:
binary-STL size consistent, bbox, section and hole pitch.

| REQ item | Part | Maker | MPN / listing | File | sha256 | Mesh | BBox (mm) | Checks vs need (rail 12 x 8, M3 at 25) | Result | Replaces SKU | Price / stock (RESULT.md) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 6 | MGN12 rail 320 mm with **MGN12C** (short) carriage | RobotDigg | MGN12 440C (robotdigg.com/product/766) | RobotDigg_MGN12C_rail320.stl | cb28a5c8c0288761b5cc490183598e088f2c9a89161e6062db4527b207138444 | 37,286 triangles, binary | 27.5 x 320 x 13.3 | rail end section **12.00 x 8.00**: match. Holes at **25** pitch, 10 from the ends: match. Carriage 27.5 wide x 34.7 long (MGN12C L 34.7), overall height 13.3 (MGN12 H 13) | PASS for the rail. The carriage is the **C** block, not the required H (45.4 long). Mesh only, no STEP | MGN12-R-300 / MGN12H (comparison only) | pending (site needs a browser) |
| 6 | several MGN rails and carriages in one mesh | RobotDigg | (unlabelled) | RobotDigg_MGN-rails_multi.stl | 2a5e1b88b732beb82214b53f3008e900eb060c6dcacba9a428365076ce02646a | 117,896 triangles, binary | 524.4 x 1040 x 20.6 (6 rails laid side by side) | not separable without more work; reference only | INFO | - | - |
| 6 | render of the multi-rail mesh | RobotDigg | - | RobotDigg_MGN_render.jpg (9921 x 7016 JPEG, delivered as "drawing") | cd0a6cfcab08cd14f37c9e2951ed0d97e3f0c8a2b73a7c86ff80eb5810049485 | - | - | **not a dimensioned drawing**, just a screenshot of the STL | INFO | - | - |

Documents copied to vendor_docs/ (unchanged; no JavaScript, launch actions or embedded files; the TBI PDF is
permission-encrypted and opens without a password):

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 6 | LDO_MGN12H-C_rail_drawing.pdf | LDO_MGN12H__drawing.pdf | c36a29cf947285fb2251e85668983b8d94d0cafa762602bde596a0fdc407e1fe | LDO-MGN12H/C rev A (9/12/20), hosted by onetwo3D. Rail **12 x 8, holes 25 pitch**, Ø3.5 thru / Ø6 x 4.5 c-bore: match. MGN12H 45.4 x 27 x 13, holes 20 x 20 M3x3.5 (same as HIWIN MGN12H). Accuracy class C (±40 µm), **light clearance (4 µm max), not preload**, max 100 °C (plastic parts) |
| 3 | TBI_linear_guide_catalog_2025.pdf | TBI_LinearGuide__catalog.pdf | 2237ba78e8baba4f3a0d7c3729de8404e2a651c31ec46941fac1973ec38c0fbb | 129 p; TH12 miniature section at p. A92 (per RESULT.md) |
| 4 | IKO_LWL_datasheet.pdf | IKO_LWL__datasheet.pdf | a5e5c942146c98917f05ac4fb5403b8a62961927a95872ce1739d8a1ac752768 | 1 p, IKO doc hosted by Distrelec |
| (extra) | CPC_miniature_guides_catalog.pdf | CPC_MiniatureGuides__catalog.pdf | 028923c0e73a554cf4c2eca7c21ddd97d67a0f7c9666b0d8e5c03d078d1ca14e | Chieftek (CPC) miniature guide catalogue, 32 p. Not yet referenced in RESULT.md |

Flags from RESULT.md to review (not verified here):
- The MISUMI SSELBL13 rail height is given as H1 7.5 vs HIWIN 8. That changes the carriage top height, so check before
  substituting it.
- MISUMI sets cost $185.97 (300) / $204.20 (350) / $222.43 (400) for rail + 1 long block, which is about HIWIN price.
- LDO MGN12H set: £31.14 (300) / £33.37 (350) / £34.48 (400) at onetwo3D, ex VAT, in stock. This is the early price
  standout. Its drawing says light clearance, class C.
- IKO ML12C1HS2 $84.28 at Misumi US (rail length to confirm). NSK PU12 block $49.26 at MROSupply. PMI is MSC/MSD, and TBI
  is TH12. RSR12 is not listed at Misumi US (SRS12N is).
Outstanding: the price table is mostly "pending"; there are no STEP files and no shortlist yet.

## Second delivery (ingested 2026-11-20, batch 4)

New in the Drive folder: THK_SRS__catalog.pdf, NSK_PU_PE__datasheet.pdf, HIWIN_LinearGuideway__catalog.pdf,
PMI_LinearGuideways__catalog.pdf, and a RESULT.md revision of 02:12:39Z. `RESULT_instinct_REQ-004_2026-11-20.md` is now
that revision (sha256 90b1e7a0c3e2b976e09f8dad90c068ee6296d16e8dd2c76507297bf349f4e46c). It has the full candidate
table (HIWIN baseline, Misumi SSELBL13 / SSELBLZ13, NSK, TBI, IKO, THK, PMI, igus, CPC, LDO, RobotDigg) and a
provisional shortlist (1 LDO, 2 RobotDigg, 3 CPC MR12). Still no STEP files.

| REQ item | File in vendor_docs | Delivered as | sha256 | Content / checks |
|---|---|---|---|---|
| 5 | THK_SRS_catalog.pdf | THK_SRS__catalog.pdf | 5e6bbdf6770e86da09bf103609a362ba9b7a7e864616beee88e022683844fbae | THK Models SRS-S/M/N, 2 pages (dimension tables incl. SRS12M / SRS12N), Antenna House 2025-08. Permission-encrypted, opens without a password. Only action: `/OpenAction /GoTo /Fit`. No JavaScript. Text layer partly uses a custom font encoding |

Not copied (same sha256 already in vendor_docs): NSK_PU_PE__datasheet.pdf (2d06a276...) =
`vendor_docs/NSK_PU-PE_miniature_E3327e.pdf`. Checked anyway: 7 p, CAT. No. E3327e 2023, permission-encrypted; the one
raw-byte "/JS" is inside compressed data, and the pypdf walk finds no JavaScript or actions.

Not downloaded (over the Drive connector's 10 MB limit; manual download needed if wanted):
- HIWIN_LinearGuideway__catalog.pdf (1tes9dKwSdToGkvQj_JneN1rjWZ2MNjMe, 17,883,962 bytes). Same size as REQ-002's
  HIWIN_MG__catalog.pdf; probably one file uploaded twice, but not confirmed by sha256.
- PMI_LinearGuideways__catalog.pdf (1wf9psuDU7OkiMsGvFGNxdmMLXmBSo7eV, 14,262,623 bytes; 142 p per RESULT.md, hosted by
  distributor sbn.de).

Flag: RESULT.md lists LDO preload/accuracy as "Precision H per reseller listing (verify)". The LDO drawing staged in the
first delivery (`vendor_docs/LDO_MGN12H-C_rail_drawing.pdf`) says accuracy class C (±40 µm) and light clearance (4 µm
max), not preload. The drawing should take precedence.
