# RESULT — REQ-006: corrections after checking REQ-002 deliveries

STATUS: partial

Research finished on every item. Requirements fulfilled: 1 of 7 (item 4 only).
Partial: items 1 (2NC variant unfulfilled), 2, 5, 6. Skipped per REQ: item 3. No-op per REQ: item 7.
STEPs for items 5 and 6 are blocked on TraceParts portal access (see Notes).

## 1. Finder 22.32 contactor — PARTIAL (22.32.0.120.4320 done; 22.32.0.230.4340 NOT fulfilled)
Old REQ-002 file was the 022.33/022.35 auxiliary-contact block; replaced.
- Finder_22.32__step.zip — official 22 series STEP set downloaded from findernet.com
  (product page -> CAD, cdn.findernet.com). Extracted the two 22.32 geometry variants:
  - 2232_xx20.stp — PRODUCT name "2232_2NO_senza_slitta" = 2 NO, no slide/din clip: matches
    22.32.0.120.4320 (17.5 mm module, 2 NO, 25 A; catalog code x3x0 = 2 NO).
  - 2232_xx40.stp — 1 NO + 1 NC variant.
- Finder_22-series__catalog.pdf — official 22 series catalog (coding table on p.1:
  x3x0 = 2NO, x5x0 = 1NO+1NC, x4x0 = 2NC).
- Finder_22.32.0.120.4320__page.pdf — findernet.com product page for 22.32.0.120.4320.
NOT fulfilled: 22.32.0.230.4340 decodes as 2 NC per the catalog coding, and Finder publishes
no dedicated 2NC STEP. The delivered 2NO STEP is an exact maker model of the 2NO variant only;
its outline/mounting is identical across contact variants, so it can serve as a 2NC
outline-only reference, but it does not fulfill the requested 2NC part. Accepting it as the
2NC reference needs Will's explicit OK.

## 2. Pi 5 camera cable (22-to-15 pin) — PARTIAL
- PiCameraCable-Pi5__page.pdf — raspberrypi.com official Pi 5 camera cable page.
  Confirms 200 / 300 / 500 mm, 22-to-15 pin, but publishes NO mechanical drawing and NO SKU.
- Checked the Product Information Portal (pip.raspberrypi.com): FPC cable category has only
  the standard camera cable drawing (RP-008146, 15-to-15) and the mini DISPLAY cable drawing
  (RP-008145, 22-to-22). No mini camera cable (22-to-15) drawing exists on raspberrypi.com.
- SKUs recorded from reseller listings (not maker-published): SC1128 (200 mm), SC1129 (300 mm),
  SC1130 (500 mm) — The Pi Hut states "Raspberry Pi SKU: SC1128".
- Delivered earlier: 200/300/500 mm physical verification stands via product page.

## 3. HQ Camera — SKIPPED per REQ (uses Camera Module 3).

## 4. M2 hex nut — DONE
Old 90370A201 was a thin nut (1.2 mm high). Replaced with standard DIN 934 / ISO 4032 M2 nut.
- 91828A111__step.step — official McMaster STEP (AP214), 91828A111, 18-8 stainless hex nut,
  M2 x 0.4, 4.0 mm AF x 1.6 mm high (verified against drawing).
- 91828A111__drawing.pdf — official McMaster dimensioned drawing.
- Price at pull time: $7.41 / pack of 100, McMaster listing "Delivers November 27".

## 5. Harwin R30-6700694 nylon spacer — PARTIAL
- Harwin_R30-6700694__drawing.pdf — official Harwin drawing DRG-02007 (M3 clearance, L=6.00,
  ID 3.20, OD 5.00, nylon) — visually verified.
- Harwin_R30-6700694__page.pdf — harwin.com product page.
- STEP: harwin.com offers it only via "Download from TraceParts", which requires TraceParts
  portal access. BLOCKED on TraceParts portal access. Not substituted: aluminium R30-6200614
  was explicitly rejected by the REQ.

## 6. Molex 43020-0201 + 0457503111 — PARTIAL (drawings done, STEP blocked)
- 43020-0201__drawing.pdf — official Molex sales drawing SDA-43020-**** (family drawing
  covering 43020-0201, 2-circuit plug). molex.com part attributes confirm Panel Mount: No,
  matching the "without panel-mount ears" requirement (replaces 43020-0200).
- 43020-0201 STEP: molex.com offers STEP AP242 only through an embedded TraceParts viewer.
  BLOCKED on TraceParts portal access. partcommunity mirror is the CADENAS family, out of
  scope per prior ruling.
- 45750-3111__drawing.pdf — official Molex sales drawing for 45750 series incl. 457503111.
  457503111 is ACTIVE (not superseded): Mini-Fit Plus female crimp terminal, 16 AWG, tin,
  reel; bag packaging alternative = 457503112. Product spec PS-45750 applies.

## 7. Camera Module 3 depth note — DONE (no action, per REQ fallback)
Checked raspberrypi.com product page, camera documentation page, and Product Information
Portal category 786 (4 documents: product brief, picamera2 manual, sensor assembly brief,
standard-cable drawing). No newer Camera Module 3 STEP is published and no note about the
10.25/11.4 mm (STEP) vs 11.3/12.0 mm (drawing) depth discrepancy. No action, per REQ.

## Notes
- All files sourced from official maker sites (findernet.com, mcmaster.com, molex.com,
  harwin.com, raspberrypi.com) using the owner's existing accounts. No purchases, no new
  accounts, no click-through terms accepted.
- TraceParts is the single live blocker (items 5 + 6 STEP). A TraceParts API key request is
  pending from earlier work, but a key is not a portal login and is not proven CAD-download
  entitlement: retry these STEPs only after evidence that the access actually covers
  downloads.
