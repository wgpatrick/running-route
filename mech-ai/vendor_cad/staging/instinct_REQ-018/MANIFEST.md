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

## 2026-11-20 batch 17 (ingested about 00:15Z on 2026-11-21): RESULT 23:49Z, Prusament spool STEP, McMaster couplers

Fetched by Drive id only, from folder 1LUF4BGyRvbsBEL23O5ovpvjlOsvmyYrf. Each file went into its own empty scratch directory and was read with `python -I`.
Untrusted data. Nothing went to `vendor_cad/inbox/` and nothing was committed. Instinct's STATUS is still **partial**: items 1 to 3 are delivered, and item 4 (the 608 CAD) is blocked.

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (1Xd6q51QZ-nGX2bJTv1bws0IbmIcM52Um, 6,470 B, 23:49Z revision) | RESULT_instinct_REQ-018_2026-11-20_2349Z.md (the interim RESULT_instinct_REQ-018_2026-11-20.md is kept as history) | 3bdaf6c0721c55b2c9a990c7170a0ead995ab7bbe612e827edd4bb2ef63194ba |
| prusament-dummy-spool__cad.step.zip (11jigV_zJ8yyulWn5kw3aWR7o7UB4jRpH, 3,978,634 B) | Prusament_dummy_spool_1kg.step.zip (kept zipped as delivered) | 7c43c16bb27d7f951ea68d040d8817a2c77709f734d192b6bf81ff1c1142dc62 |
| (zip member) prusament-dummy-spool__cad.step, 25,441,235 B | not staged unzipped | b8dbb4efd3723a925b048f6a791b5939c5d8450a005fdd770aa60da280230d80 |
| e3d-roto-bowden-reference-cad.step (1LVphpqcJnyEC4kY_d3sZ3Rp5f_6kNt1Z, 1,411,826 B) | **not re-staged**: byte-identical to staging/E3D_Roto_Bowden_reference.step | 1a8ac7dc89f2239ec41e1815da9e95295b51dc119ddbd7b4134adfa693cc4b12 |
| 2333N197__cad.step (1TdFWRZaff6OUdA4VGVtcJQ-OthYx1rgp, 713,378 B) | McMaster_2333N197_push-to-connect_4mm_M5x0.8.step | 717e927ee2fcefcbf3c0810f273c4ee572c3bc3e6160876637d4693442660b3e |
| 2333N202__cad.step (182finrZxvyN344qrjZJoKzWrNdNuHQyi, 631,576 B) | McMaster_2333N202_push-to-connect_4mm_M6x1.step | cfe12e53fe720ded6c3be4640d1d225cd4a7ede3507952019e2d524a8ed054a0 |
| 2333N211__cad.step (1k2a5cZ5LfFNV243xSWAyunT2N6zRehCv, 738,965 B) | McMaster_2333N211_push-to-connect_4mm_M8x1.step | b69c7c9a1936ef73d28f93503ba6ae5fef3e536d4f9b841246707966e4a0a83c |
| 2333N214__cad.step (1pwUiwkIny47tvytRCux1gu3lUAAfPcdl, 766,063 B) | McMaster_2333N214_push-to-connect_4mm_M10x1.step | ca54ec1dc475cd4fd8023af6401a407498be364b152eaf23a71b0ca8075a1ff7 |
| 2333N197__datasheet.pdf (1e_hwVRzPTMG5L_RJOKmlNMIXkHyGEpu9, 55,439 B) | vendor_docs/McMaster_2333N197_push-to-connect_4mm_M5x0.8_drawing.pdf | ca37866d99a7369263ba3f403bc0a2da31bfe96ebe23b9bcd7545ab24bb446a7 |
| 2333N202__datasheet.pdf (1tHSIUo9_7NkBgTWXDJK6i7FA-0yJa0mR, 60,246 B) | vendor_docs/McMaster_2333N202_push-to-connect_4mm_M6x1_drawing.pdf | 0b472ac3725a41befe387bff185d496b2a5b6b83907a5e8c3b23dc0f1f42f978 |
| 2333N211__datasheet.pdf (1nK1vyFF3118oC6hyeB0D84tMa7SgMhyZ, 57,799 B) | vendor_docs/McMaster_2333N211_push-to-connect_4mm_M8x1_drawing.pdf | 291af4e9c2a78d2850b867c40522f6c80f083c3d40c54d23fd0d0d9e129f8ce9 |
| 2333N214__datasheet.pdf (1_GpiDq7VtazdCbbxZknpXuS_SBFYJcev, 58,853 B) | vendor_docs/McMaster_2333N214_push-to-connect_4mm_M10x1_drawing.pdf | 1dc39d023f3835d358ba5b858dcccb18742abf477beef6dc30578c9b9ba1f221 |

### Stated provenance and prices (per Instinct, not verified; prices as displayed 2026-11-20, USD)
- **Spool.** Instinct names the source as Prusa Research (@Prusa3D) on Printables, "Dummy Prusament Spool for Makers", model 1648762, and calls the STP the
  untouched official file. Instinct stated no licence, and the STEP carries no licence or copyright entity. The STEP header shows Autodesk Inventor 2019 and
  ST-Developer v17, AP214, time_stamp 2026-01-20T12:49:30+01:00. The author is "Jiří Bílek". The source path is `...\Inventor\1 projekty\186_civka\soutez civka\civka.stp`
  ("soutěž cívka" is Czech for "spool competition"). The zip member is dated 2026-09-01. The licence on the Printables page is **unknown**; check it before redistributing the file.
  Instinct found no maker dimensioned drawing.
- **McMaster nickel-plated brass push-to-connect male adapters for 4 mm tube OD.** 2333N197 M5x0.8 $6.95; 2333N202 M6x1 $13.72; 2333N211 M8x1 $13.72;
  2333N214 M10x1 $11.98. All showed "Delivers Monday by 5 pm". Each STEP is AP214 with the header "(c) 2026 McMaster-Carr Supply Company".
- **Drawings.** The PDFs are **not** McMaster's original PDFs. Each is a 1-page wrapper around one embedded raster (1050x811) of the McMaster drawing, with
  /Title `<PN>__datasheet` and CreationDate 2026-11-20 23:28 to 23:34Z, which is when Instinct produced them. The drawing content is McMaster's title block and dimensions.
- PDF safety (pypdf full object walk): no JavaScript, JS, OpenAction, AA, Launch, EmbeddedFile(s), RichMedia, XFA, AcroForm, URI, SubmitForm or GoToR keys. The files are not encrypted and contain no text layer.

### Spool geometry (build123d, python -I, 24 s import)
1 valid solid, 11,056 faces, 181,112 mm3. Its axis is X.

| Dim | STEP | Overture wiki (text) | Prusament, community-measured (no official Prusa sheet found) |
|---|---|---|---|
| Flange OD | 199.89 | 200 | about 199 to 200 |
| Overall width | 64.13 | 65.6 | 65 to 69 reported |
| Hub bore (min) | 51.25 (only in about 6 mm at each end; 51.8 at the outer faces) | 55 | about 50 to 52 |
| Core barrel | OD 100.60, wall ID 96.20, between the end hubs | - | - |

The hub bore is not a simple cylinder. It was taken from radial sections at 12 stations, and the end hubs are ribbed (about 12,000 section edges at the flanges).
A holder sized for Overture's 55 mm hub will **not** pass through a Prusament 51.25 bore. A design spindle should be 50 mm or less if it must take both spools.

### McMaster fittings vs drawing (build123d)
Each file has 3 valid solids (body, collet and seal, by construction).

| PN | Drawing: thread / L / hex A/F / int. hex | STEP: L / hex A/F (6 flats) / int. hex (6 flats) | Tube socket | Thread envelope (slices, tip to shoulder) | Result |
|---|---|---|---|---|---|
| 2333N197 | M5x0.8 / 18 / 8 / 2 | 18.000 / 8.0 / 2.0 | 4.000 | 4.64 to 4.82, length about 3.8 | match |
| 2333N202 | M6x1 / 19 / 10 / 3 | 19.000 / 10.0 / 3.0 | 4.000 | 5.53 to 5.74, length about 4.3 | match |
| 2333N211 | M8x1 / 18 / 11 / 3 | 18.000 / 11.0 / 3.0 | 4.000 | 7.52 to 7.74, length about 4.5 | match |
| 2333N214 | M10x1 / 19 / 13 / 3 | 19.000 / 13.0 / 3.0 | 4.000 | 9.52 to 9.76, length about 4.8 | match |

- The thread is a cosmetic conical envelope with no helix, so the pitch cannot be measured. The envelope tapers at about 1:16 on diameter and sits 0.25 to 0.5 below nominal.
  The drawings call out plain metric threads, so treat the taper as a modelling artefact unless McMaster says otherwise.
- The "2 mm / 3 mm" callout on the drawings is the internal hex key socket. In the STEP it is six flats at 2.0 or 3.0 A/F, and it also sets the filament path ID.
  On 2333N197 that ID is **2.0**, which is tight for 1.75 filament. The others are 3.0. The bbox across corners reads less than the theoretical value because the hex corners are chamfered.

### Roto Bowden inlet, measured from the E3D reference CAD (REVO-ROTO-COLDSIDE-BOW-AS)
The CAD is byte-identical to staging/E3D_Roto_Bowden_reference.step. The inlet is HEMERA-175-BOWDAPTOR-REFERENCE, with M-BOWDEN-COUPLING-PLASTIC-175 (E3D's own collet) and M-BOWDEN-CLIP-175. All three sit on the
filament axis (assembly Y axis, X = Z = 0).
- Bowdaptor **outside**: 9.00 body (Y 11.7 to 19.2), then a chamfer cone to a **6.00 spigot**, 0.9 long (Y 21.8 to 22.7). The spigot sits in a **6.20 recess** in the heatsink, 1 mm deep (floor
  at Y 22.8), with a 3.30 filament hole beyond it. The 7.36 feature is a plain 1 mm deep step (ring or counterbore) concentric with that recess (Y 21.8 to 22.8). It is not a threaded hole.
- Bowdaptor **inside**: 5.064 collet bore, cone, then a **6.966 internal cavity** (Y 15.0 to 17.2, the collet-jaw chamber), cone down to a 4.10 PTFE bore (Y 19.2 to 21.2), then a 2.0 filament hole.
  The collet itself is 7.0 flange / 4.8 sleeve / 4.1 bore.
- **This contradicts Instinct's reading.** RESULT 23:49Z calls 6.97 the bowdaptor's "threaded-end cylinder" going into a 7.36 heatsink hole, and infers M8x1 from that. The 6.966 surface is
  internal and lies about 5 mm away from the heatsink interface. The heatsink interface is a plain 6.0-in-6.2 locating spigot. **No thread is modelled anywhere on the inlet.**
  The inlet already takes 4 mm OD PTFE directly through E3D's integrated collet (4.1 bore). None of the four McMaster adapters is indicated for the Roto inlet. The M8x1 2333N211 has
  no basis as a "Roto fit". These couplers are only for other ends of the feed path, such as a spool-side bulkhead in a tapped printed or metal part.
