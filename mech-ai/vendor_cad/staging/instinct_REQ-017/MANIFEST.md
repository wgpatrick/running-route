# instinct_REQ-017: printer feet for the HFS5-2020 frame (McMaster 6301K78 / 6301K79, Misumi NFJN5-30)

Ingested 2026-11-20 (batch 16, about 23:15Z). Drive folder `REQ-017-printer-feet` (1oTmOZq2zwA42wp-kq_f6DTyidvPqnw8e).
Fetched by Drive id only. Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed. No payment was made (per Instinct).

Instinct's STATUS: **done**. Neither McMaster candidate has an M5 stud (M6 and M8). The only direct-fit M5 option is Misumi NFJN5-30, which is all metal with no rubber pad.

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1S4rpFB43LfQ2Odm9mI_khVKfjDDGYD0o, 5,055 B) | RESULT_instinct_REQ-017_2026-11-20.md | 61f483ca3b3a0bf8adbbfeb04d713cfb93fa244735c9a7a6ba91b3962c04ee09 |
| 6301K78__cad.step (19resH6P5BZC0G4oRLNNMvJSadFDcHYSj, 1,164,569 B) | McMaster_6301K78_swivel-leveling-mount_M6.step | 3f670eea592efbf7ecef00c1ba1d6dd62ff191f83ee8c5dcac3fc70c6127b042 |
| 6301K79__cad.step (1306vwGq_b6djhcEdBHOW4Mu8lSBzFLX-, 1,226,081 B) | McMaster_6301K79_swivel-leveling-mount_M8.step | 4f4faa12d57a92a35978c2f4cae3f2f9cc36994f2ae99f0ca7ee9b6519ec7e3b |
| NFJN5-30__cad.step (18SZUQX5PzHOEW5LbQrKEFIw_LcA4Cv_I, 97,399 B) | Misumi_NFJN5-30_leveling-mount_M5.step | 301747c24972ef542c4b0db780a4750668a49ceaefda8dcd28f5559b0ec3c33d |
| 6301K78__datasheet.pdf (11fytjz4doReU6hrNldvJ4s3u34F6jQC5, 47,856 B) | vendor_docs/McMaster_6301K78_drawing.pdf | 0ac2a2b157273ea235aa4e3120bbb113e2ecbcb92cc982d7915b13b3b4fa84b9 |
| 6301K79__datasheet.pdf (1pmlCZmQ8wcOoAtaC9kbPm_GfJT9lp6W3, 48,401 B) | vendor_docs/McMaster_6301K79_drawing.pdf | 064d234df5a7247314fc34700332242115615690d8a1f59a831cb3216a18a0e6 |
| NFJN5-30__datasheet.pdf (13nQoPkRtmYHmKdMr8gqxZmvn_3uk5Jss, 300,865 B) | vendor_docs/Misumi_NFJN_leveling-mounts_2019US_p3166-3167.pdf | 4924f3a151d72a1b3081d888bf4ddc57489b9784b1a7d662774ab24b2e1b7d2a |

None of these files was already in the repo (sha256 check against vendor_docs and staging).

PDF safety (pypdf full object walk): none of the three PDFs contains JavaScript, Launch, OpenAction/AA, EmbeddedFiles, URI, XFA, SubmitForm or AcroForm. None is encrypted.
The two McMaster PDFs are 1-page image-only PDFs with no text layer. Their Title is "6301K7x__drawing" and they were created 2026-11-20T22:35:29Z, so they are Instinct's GIF-to-PDF conversion, not McMaster files. Instinct says McMaster's own 2-D PDF link returned 404.
The Misumi PDF is the original 2019 US catalog spread, pages 3166-3167 (InDesign, 2021-08-05). Its text layer holds the NFJN and FJGN/FJGM tables.

## Stated provenance and prices (per Instinct, not verified; displayed 2026-11-20, USD)
- **McMaster 6301K78**: M6 x 1 stud, 25 mm long; 19 mm base; natural rubber cushion (no durometer given); 515 lb; 41 mm high; swivel 7.5 deg; locknut included. **$7.65** each, "Delivers Monday by 5 pm". The 19 mm pad is just under the 20 mm minimum asked for.
- **McMaster 6301K79**: M8 x 1.25 stud, 32 mm long; 25 mm base; 750 lb; 52 mm high. **$8.24** each, "Delivers Monday by 5 pm".
- Both STEP files came from the McMaster product-page CAD link, through the owner's existing signed-in session. Header: SolidWorks 2024 / SwSTEP 2.0, author "McMaster Carr Supply", time_stamp 2026-11-05.
- **Misumi NFJN5-30** ("Leveling Mounts - Standard"): M5, A = 30, 1018 steel with trivalent chromate, 1.5 kN, 15 g. **$4.32** each, ship date Tue Nov 24 2026. Instinct says it "screws directly into the HFS5-2020 M5 end tap".
  The STEP came from Misumi's logged-in CAD download. Header: SolidWorks 2016, FILE_NAME 'NFJN5-30.step', time_stamp 2026-07-17. The author/org fields read "EC2" / "Amazon.com", which suggests a cached file from Misumi's cloud generator; this is not a concern in itself.
- Other routes named but with no files: Misumi **HAJP5-2020-6** end plate with an M6 boss, $16.38, ship Nov 24. Misumi **HFPD5-2020** TPE end pad (fixed, not adjustable), $5.78, 55 in stock.
- Instinct found no M5-stud foot with a rubber pad in the McMaster or Misumi families it inspected. It skipped SDP/SI because of a Cloudflare challenge.

## Misumi NFJN table as read (M5 row, catalog p3166)
D 30, (l1) 3.5, (l2) 4, E 5.4, B 8, t 1.6; NFJN5-30: A 30, L 40.5, 1.5 kN, 15 g. NFJN5-60: L 70.5, 19 g.
The drawing shows the following: the foot is D in diameter, with a base flange t thick. Above it is a dome E high, then an integral hex (l1 high, B across flats), then the screw A long to the tip. (l2) is the loose jam nut. L is the overall height.

## Geometry check (build123d 0.13.0, python -I)

| Check | McMaster_6301K78 (M6) | McMaster_6301K79 (M8) | Misumi_NFJN5-30 (M5) |
|---|---|---|---|
| Schema | AP214 (AUTOMOTIVE_DESIGN) | AP214 | AP214 |
| Solids / faces | 4 / 246 (base, stud, jam nut, rubber pad) | 4 / 265 (same) | 3 / 38 (foot+screw, hex, jam nut) |
| is_valid / BRepCheck | True / True (each solid True) | True / True (each solid True) | True / True (each solid True) |
| BBox (mm), Y = axis | 19.0 x 41.0 x 19.0 | 25.0 x 52.0 x 25.0 | 30.0 x 40.5 x 30.0 |
| Volume (mm3) | 3,360.7 | 7,026.0 | 4,179.3 |
| Overall height | 41.0 = drawing 41 | 52.0 = drawing 52 | 40.5 = L 40.5 |
| Pad / foot dia | metal base 19.0 = drawing 19; rubber disc 18.52 x 3.18 thick | base 25.0 = drawing 25; rubber 24.38 x 3.18 | 30.0 = D 30 (flange t 1.60 = 1.6) |
| Thread | modelled helical, major 6.0, pitch 1.0 = M6x1 | modelled helical, major 8.0, pitch 1.25 = M8x1.25 | plain 5.0 cylinder, not threaded (nominal M5) |
| Thread length | about 25.0 (hex top to tip) = 25 | about 32.0 = 32 | 30.0 (hex top 10.5 to tip 40.5) = A 30 |
| Hex | integral hex 10 AF = drawing 10; jam nut 10 AF x 3.3 | 12 AF = drawing 12; jam nut 12 AF x 4.4 | integral hex 8 AF x 3.5 = B 8 / l1 3.5; dome 1.6 to 7.0 = E 5.4; jam nut 8 AF x 4.0 = l2 4 |
| Notes | Ball stud sits in the base socket (swivel). The rubber pad is a separate solid. | As 6301K78. | Simplified model. The foot is a **solid** disc and dome, so the volume of about 3,865 mm3 (about 30 g steel) is twice the catalog's 15 g. The real foot is pressed sheet. Both hexes overlap the 5.0 screw cylinder (bore 4.13), and the jam nut is placed flush with the tip. |

Verdict: all three are accepted as maker CAD. The McMaster models match their drawings on every dimension shown. The NFJN5-30 model matches every dimension in the Misumi M5 table, but it is a simplified envelope with no thread and a solid foot, so do not use it for mass.

## Points for the owner
- The HFS5-2020 centre bore is only tapped M5 if the end-tap alteration is ordered. Instinct calls it "the stock HFS5 M5 end tap"; check that the frame order actually includes the tap.
- No candidate meets every requirement: NFJN5-30 fits M5 but has no rubber, and the McMaster feet need M6 or M8 (by tapping the bore out, which is not approved, or with the HAJP5 plate).
