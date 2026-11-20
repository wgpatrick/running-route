STATUS: done

# REQ-017: printer feet (2020 frame, ~14 kg printer)

4 leveling feet for a Misumi HFS5-2020 (6 mm slot) frame. Wanted: M5 stud (or M6 with note), rubber/neoprene pad, 5-10 mm height adjust, pad dia 20-30 mm, load >5 kg/foot, US sellers, no payment.

## Item 1: candidates (2 from McMaster-Carr; no third maker added, see notes)

Prices/stock are as displayed on the product pages 2026-11-20, signed-in session. USD. McMaster shows a delivery promise rather than a stock count; quoted verbatim. Both are swivel (ball-and-socket, 7.5°) with a bonded natural-rubber cushion pad, include a locknut, and adjust height continuously along the stud (so the 5-10 mm adjust range is covered).

| Part | Stud | Pad dia | Pad material | Load cap | Overall ht | Price (each) | Availability as displayed |
|---|---|---|---|---|---|---|---|
| McMaster 6301K78 | M6 x 1, 25 mm long | 19 mm | Natural rubber cushion (durometer not listed) | 515 lb (~234 kg) | 41 mm | $7.65 | "Delivers Monday by 5 pm" |
| McMaster 6301K79 | M8 x 1.25, 32 mm long | 25 mm | Natural rubber cushion (durometer not listed) | 750 lb (~340 kg) | 52 mm | $8.24 | "Delivers Monday by 5 pm" |

Links: https://www.mcmaster.com/6301K78/ and https://www.mcmaster.com/6301K79/

Notes:
- M5 stud: no M5-stud rubber-pad leveling foot was found in the inspected McMaster metric swivel/rigid families (smallest metric there is M6), and none was found in the inspected Misumi rubber-pad families (FJSN/FJSM Rubber Base, FJGN/FJGM Non-Slip), whose thread sizes start at M8 with 40 mm+ pads; absence beyond these inspected catalog families is not established. Both candidates are therefore M6/M8. Neither is verified compatible with the stock HFS5 M5 end tap. Fitting one would require a design modification (e.g. tapping the extrusion center bore to M6/M8, which is a proposed modification only and not approved) or the Misumi plate in item 3. The verified direct-fit M5 route is NFJN5-30 in item 3, but it has no rubber pad.
- 6301K78's pad is 19 mm, just under the requested 20 mm floor; 6301K79's 25 mm is in range.
- A "one other US maker" was not added: SDP/SI's shop (shop.sdp-si.com) is behind a Cloudflare challenge to direct requests and was not pursued further within this REQ. The two McMaster candidates plus the Misumi item-3 route below cover the requirements.
- For reference, Misumi's rubber-pad family FJSN (M8 and up) lists its neoprene at Shore A80; McMaster does not list a durometer for the cushion pads above.

## Item 2: maker STEP + dimensioned drawing (this folder)

- 6301K78__cad.step — official McMaster STEP (AP214 verified) from the product page CAD link.
- 6301K78__datasheet.pdf — McMaster's dimensioned drawing for 6301K78. Provenance: saved from McMaster's published drawing image (GIF) and converted to PDF as-is; McMaster's own "2-D PDF" link returned a 404 during this session.
- 6301K79__cad.step / 6301K79__datasheet.pdf — same sources as above for 6301K79.
- NFJN5-30__cad.step — official Misumi STEP (AP214 verified, internal file name NFJN5-30.step) via Misumi's logged-in CAD download (us.misumi-ec.com).
- NFJN5-30__datasheet.pdf — Misumi catalog page (2019_US_3166_001.pdf) with the NFJN family dimensioned drawing and size table, https://us.misumi-ec.com/pdf/fa/2019/2019_US_3166_001.pdf.

## Item 3: Misumi foot for the HFS5 end tap (M5), or matching corner foot plate

Yes to both variants:

1. Direct M5 end-tap foot: Misumi NFJN5-30 ("Leveling Mounts - Standard") — M5 thread, 30 mm long screw, 30 mm swivel foot, all-metal (1018 carbon steel, trivalent chromate; stainless version NFJNS also exists), allowable vertical load 1.5 kN (~153 kg) per Misumi's table, mass 15 g. $4.32 each, ship date shown Tue. Nov 24, 2026. Screws directly into the HFS5-2020 M5 end tap. Caveat: no rubber pad (metal foot).
   Link: https://us.misumi-ec.com/vona2/detail/110302593010/
2. Corner/end plate route: Misumi HAJP5-2020-6 ("Mounting Plates for Casters and Leveling Mounts", 1018 carbon steel) bolts to the HFS5-2020 end and provides an M6 threaded boss that accepts an M6 leveling mount (e.g. 6301K78 above, or Misumi NFJN6-40). $16.38 each, ship date shown Tue. Nov 24, 2026. Misumi does not offer this plate with an M5 thread; M6 is the smallest.
   Link: https://us.misumi-ec.com/vona2/detail/110300476640/
3. Adjacent option found while checking: Misumi HFPD5-2020 ("Pads for Aluminum Extrusions") is a TPE end pad made to fit HFS5-2020 directly (no end tapping needed), $5.78 each, 55 in stock, same-day ship shown. It is a fixed pad, not an adjustable foot.
   Link: https://us.misumi-ec.com/vona2/detail/110302266360/

## Compliance

No purchase or payment made. No new accounts created; used the existing signed-in McMaster and Misumi sessions. All CAD/drawings are official vendor files (no generated substitutes); the only transformation is GIF-to-PDF format conversion of McMaster's own published drawing, labeled above. Nothing about the owner beyond his existing signed-in sessions was disclosed; no email notifications sent.
