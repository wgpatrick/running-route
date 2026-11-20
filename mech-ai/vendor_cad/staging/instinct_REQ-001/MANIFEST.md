# Staging manifest: Instinct REQ-001 supplier CAD batch 3

Source: Google Drive folder "mechloop handoff/results/REQ-001-supplier-cad-batch-3" (id 1ZtlzfkmX-Yz92soEepnPbyNiPK0uQ43v).
Fetched 2026-11-20 via the Google Drive connector. 21 files listed (2 pages, no subfolders), all 21 downloaded; every local size equals the Drive size.
The folder's RESULT.md is kept here as `RESULT_instinct_REQ-001.md` (untrusted notes; used only for source URLs and descriptions).
Nothing has been moved to `vendor_cad/inbox/`: these are staged only, to be applied later.

Verification: each STEP imported with build123d 0.13.0 (`.venv/bin/python -I`); solids counted, bounding box taken, BRep validity checked,
and key dimensions measured from planar-face positions along the axis, cylinder diameters and vertex radii. Compared with the McMaster
drawing PDF (vendor_docs/McMaster_<MPN>_drawing.pdf) or the Omron datasheet (vendor_docs/Omron_E2B_datasheet_D116-E1-02.pdf, Cat. No. D116-E1-02, printed p.14 "M12 Size, Pre-wired Models (Shielded), Short Body").
Bounding boxes are in mm, in the file's own frame, as size X x Y x Z.

## Parts

| Part | Maker | MPN | Source URL | File | sha256 | Solids | BBox (mm) | Checks against drawing | Result | Would replace SKU |
|---|---|---|---|---|---|---|---|---|---|---|
| SHCS M4 x 0.7 x 6, black-oxide alloy steel, 12.9 | McMaster-Carr | 91290A139 | https://www.mcmaster.com/91290A139/ | 91290A139.step | 08a47229776abdb25265f1d983919583b6ff94a421c6d37de7e3e5df7bec1337 | 1 (valid) | 7.0 x 7.0 x 10.0 | head dia 7.0 (dwg 7); head height 4.0 (dwg 4); length under head 6.0 (dwg 6); thread major 4.0 (M4) | PASS | SHCS-M4x6 (substitute for 90128A208, which is zinc-plated). Byte-identical to the already staged `staging/SHCS-M4x6.step` (2026-11-15) |
| SHCS M5 x 0.8 x 6, black-oxide alloy steel | McMaster-Carr | 91290A221 | https://www.mcmaster.com/91290A221/ | 91290A221.step | 682c663abb4ea740c57efa9251315ad00cdb968f3593c7903944f5d37b1206a6 | 1 (valid) | 8.5 x 8.5 x 11.0 | head dia 8.5 (dwg 8.5); head height 5.0 (dwg 5); length 6.0 (dwg 6); thread 5.0 (M5) | PASS | SHCS-M5x6 (confirms the "unverified" 91290A221 in mcmaster_wanted.csv). Byte-identical to `staging/SHCS-M5x6.step` |
| Internal-tooth lock washer M5, DIN 6797 J, 18-8 stainless | McMaster-Carr | 93925A260 | https://www.mcmaster.com/93925A260/ | 93925A260.step | 76c29a0217dbb65718f03a5b1f5e1086fd3dd83762a05c0b58bddac6aee6129f | 1 (BRep check FAILS: `is_valid` False) | 10.0 x 10.0 x 1.268 | OD 10.0 (dwg 10); sheet thickness 0.60 (dwg 0.5-0.7); tooth-tip clear dia 5.37 (dwg ID 5.3); overall height with set teeth 1.268 | PASS on dimensions, WARN on geometry validity | WASHER-M5-SERRATED (also named WASHER-M5-STAR in tools/build_package.py). RECOMMENDED choice |
| Internal-tooth lock washer M5, DIN 6797 J, zinc-plated steel | McMaster-Carr | 93925A420 | https://www.mcmaster.com/93925A420/ | 93925A420.step | 6fae8160a3a35539d412dbc8ca6a7258be69010eddb433667a5bbfbfbbd4932d | 1 (BRep check FAILS) | 10.0 x 10.0 x 1.268 | same geometry as 93925A260 (identical volume 27.907 mm3 and dimensions; only the header differs) | PASS on dimensions, WARN on validity | WASHER-M5-SERRATED (alternative) |
| Internal-tooth lock washer M5, black-oxide steel | McMaster-Carr | 91106A126 | https://www.mcmaster.com/91106A126/ | 91106A126.step | 3bdd6bb40cd4ccac6acf2ce8fb675f59b4e55983deacd9433d85816484e59bb4 | 1 (valid) | 10.0 x 10.0 x 1.298 | OD 10.0 (dwg 10); sheet thickness 0.60 (dwg 0.5-0.7); tooth-tip clear dia 5.41 (dwg 5.3) | PASS | WASHER-M5-SERRATED (alternative; the only one of the three whose STEP passes the BRep check) |
| Flanged button head hex-drive screw M5 x 0.8 x 8, ISO 7380-2, black oxide | McMaster-Carr | 92137A412 | https://www.mcmaster.com/92137A412/ | 92137A412.step | 0ac488d693b6df141feb036b8851ad559f3a700e0e49739a1997bc19fcf6d526 | 1 (valid) | 11.8 x 11.8 x 10.75 | flange dia 11.8 (dwg 11.8); head height 2.75 (dwg 2.75); length under head 8.0 (dwg 8); thread 5.0 | PASS | BHCS-FL-M5x8 |
| Flanged button head hex-drive screw M5 x 0.8 x 10, ISO 7380-2, black oxide | McMaster-Carr | 92137A414 | https://www.mcmaster.com/92137A414/ | 92137A414.step | 5fae5356954c2a718ce2d482fdaace362270235d8fca1428232c0c6cc6b0f8f7 | 1 (valid) | 11.8 x 11.8 x 12.75 | flange dia 11.8 (dwg 11.8); head height 2.75 (dwg 2.75); length 10.0 (dwg 10); thread 5.0 | PASS | BHCS-FL-M5x10 |
| Oversized washer M3, 9 x 3.2 x 0.8, zinc-plated steel | McMaster-Carr | 91100A120 | https://www.mcmaster.com/91100A120/ | 91100A120.step | 6dfe818e4c836faa4cecac7d74a961a4c7eb6b851fed4a9a1dc1079aa1baca2b | 1 (valid) | 9.0 x 9.0 x 0.8 | OD 9.0 (dwg 9); ID 3.2 (dwg 3.2); thickness 0.8 (dwg 0.7-0.9) | PASS | WASHER-M3-LARGE (csv says "not sold by McMaster": this is the dimensional ISO 7093-1 match) |
| Oversized washer M4, 12 x 4.3 x 1.0, zinc-plated steel | McMaster-Carr | 91100A130 | https://www.mcmaster.com/91100A130/ | 91100A130.step | 632f96fe6f02cd6085c0a81087b51447c2fc2e609a125136aebed497ae7dd0eb | 1 (valid) | 12.0 x 12.0 x 1.0 | OD 12.0 (dwg 12); ID 4.3 (dwg 4.3); thickness 1.0 (dwg 0.9-1.1) | PASS | WASHER-M4-LARGE |
| Inductive proximity sensor M12, shielded, 4 mm, NPN NO, 2 m (with 2 clamping nuts) | Omron | E2B-M12KS04-WP-C1 | https://download.ia.omron.com/download/zip/ST/OEE/E2B_M12KS04_WP_C1/ | E2B-M12KS04-WP-C1.step (extracted, unchanged, from E2B-M12KS04-WP-C1_STEP.zip, member E2B_M12KS04_WP_C1.STEP, 145036 B, SolidWorks 2011 AP203, dated 2013-04-24) | 344fbce57ed5d4820843afe4376762e5498f211f02ec852df41f8d421e3c7eed (zip: 6b5a4b7869f5458484a297965379a5cfa5f97883576d77789b59464543580ab4) | 3 (all valid): body + 2 nuts | 17.0 x 19.63 x 57.0 (body 12 x 12 x 57) | overall body 47.0 (ds 47); thread M12 dia 12.0 over 0.8-30.0 from the face, i.e. 30 from the face (ds 30); rear part 7.9 at dia 10.2 (ds 7.9); then 9.1 at dia 8.2 to the 47 mark; cable stub dia 4.0 x 10 (ds 4-dia cable); nuts 17.0 AF (ds 17), 19.63 AC, 4.0 thick (ds 4), bore 12.0 | PASS (see notes) | E2B-M12KS04-WP-C1 probe (the catalogue picks up `inbox/E2B-M12KS04-WP-C1.step`; SKU family PROBE-OMRON-E2B-M12KS04) and its clamping nuts (2 x M12x1 17 AF x 4) |

## Documents (saved in vendor_docs/)

| File | Drive id | sha256 | Note |
|---|---|---|---|
| McMaster_91290A139_drawing.pdf | 1vwRHKJkIJW3gaI138gcNPCUbF5RF8TUX | 120c0aa0c4852b50623179236b4a6d5316ea978dcf0e794b925c364f562d598d | 1 page |
| McMaster_91290A221_drawing.pdf | 1lsStF5pR_zfTeAqw9-eSSNrUgspPkVAO | d9079754b6d21fe8f43453ca9292922e972e56e7dc111617eeaae2e97c22855b | 1 page |
| McMaster_93925A260_drawing.pdf | 1UtjWHO5Svm8cyewfmhkSzqgqjxEXOZVo | 9bf088740b25aca472333d64ea2fb53ea783ab98c3b43623ec66c1e26200b727 | drawing does not state the material |
| McMaster_93925A420_drawing.pdf | 1GDooS-jXc2BIrCE2abTg6Pql7LAiylSG | c980af610d5d45ba2128642bd36cd76e4128d912369525c7e94fe5581ced4454 | drawing does not state the material |
| McMaster_91106A126_drawing.pdf | 1oRw_xoeLNExLJWHpt3N2pwlDrHDTUZ0e | ccfe49ff5426bf8062e3559029d693ef049c373e8e61549a7b54c083d3422736 | "Black-Oxide Steel" |
| McMaster_92137A412_drawing.pdf | 1q1oxfj24Qw-IL_EfEzz5P_Vv-CXic2fi | e98e315dc1646d8ffc7fd5dbfbc1863515fdaff80f6436d3fc6c49ccbb520d05 | |
| McMaster_92137A414_drawing.pdf | 149gmDdCZXN3iNVZ_5sNAGaCX0chppqI1 | 4cdfc818a0197c91d84c1eb6a14997c85508982edf6fa6b97e617fd38d6a4bfc | |
| McMaster_91100A120_drawing.pdf | 1AB46A9AuD90OUj9wxhMo_df1PWUlRyVh | c36ba79bf6e8bdc025607f76723fc311c6b7bc16b97955ceabb495a25e8de913 | |
| McMaster_91100A130_drawing.pdf | 1VOqzh6BxWnPp9dPDpXzqA731xyz9cBBL | 451a121fc118b04c3777d5f94ac5f46c57a6f59561831c57d014578ff3eb0bad | |
| Omron_E2B_datasheet_D116-E1-02.pdf | 1o5qg9tzeWA5YmyrjvBn1pdOzuzwzp5xQ | 3948852a80069bab328c217e7e0cf3e9b8a220690b94447ee2a5c980f57d05d4 | Source https://assets.omron.com/m/2da718de55d407e8/original/D116-E1-02_E2B_Datasheet-pdf.pdf; 22 pages, footer "Cat. No. D116-E1-02". Not byte-identical to the existing vendor_docs/omron_E2B_datasheet_en.pdf (different sha256 and size); page numbering may differ from that copy |

## Notes and mismatches

- Lock washer choice: recommend **93925A260 (18-8 stainless)** for WASHER-M5-SERRATED unless the design specifies otherwise. Its STEP (and the zinc 93925A420, which is the same model) fails the OCCT BRep validity check; it imports as one solid with the right dimensions and should display fine, but may misbehave in booleans or clearance checks. If that matters, 91106A126 (black oxide) has the same dimensions and a valid solid.
- The McMaster drawings for 93925A260 and 93925A420 do not print the material; the material split comes from RESULT.md and the STEP file names only.
- Omron probe vs the repo's current record (mechloop/parts/vendor/omron_e2e.json, `body_mm`): the record has `body_length` 39.1 + `cable_protector` 7.9 = 47. The STEP and datasheet instead show: thread 30 from the face (incl. a 0.8 mm, 10.5 dia front cap), then the 7.9 mm unthreaded rear part at dia 10.2, then a 9.1 mm cable protector at dia 8.2, total 47. So "7.9" is the rear body part, not the cable protector. Rear-body diameters 10.2 / 8.2 and nut across-corners 19.63 are now known from the STEP (the record marked them as assumed).
- The Omron STEP contains no toothed washer (the datasheet shows one: "Two clamping nuts, Toothed washer"); the nuts are positioned at 5.8-9.8 and 9.8-13.8 mm from the sensing face.
- The Omron STEP includes a 10 mm stub of the 4 mm cable beyond the 47 mm body, so its bounding-box length is 57.
- 91290A139 and 91290A221 STEPs are byte-identical to the SHCS-M4x6 / SHCS-M5x6 files already staged on 2026-11-15; this batch adds their drawings.

## Pending / blocked (from RESULT.md)

- MISUMI HNTAJ5-3, HNTAJ5-5 and the HFS5-2020 corner bracket: PENDING, retry via the owner's CADENAS (3Dfindit) account, awaiting the owner's approval.
- PEM S-M3-0: BLOCKED, PEM's CAD download needs a registration form; needs an owner decision (or the PEM catalogue on CADENAS).
