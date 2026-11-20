# PCBWay manual review status, reference parts batch 01 (2026-11-20)

Source: note from the owner's browser agent ("Instinct") in Google Drive, `mechloop handoff/results/NOTE-pcbway-review-status/RESULT.md`
(id 10B1hI-MHF3MTObwhS7bSy3xKfCZWlvKq, 06:47:12Z, 1,550 B, sha256 b7fa6ac7db3805b9663c900f498f5298eed5cb66e2e73efc01f3967f3ce3b59e).
The note is headed "STATUS: info (note to mechloop, 2026-11-19 ~10:47 PM PT)". It says Instinct checked it against the PCBWay
order detail pages; this repo has not seen those pages. **The note is recorded here as data.** It includes a request for a
revised RP03 STEP. That request has not been acted on, and it waits for the owner's decision. Nothing has been ordered or paid.

## Summary

| Part | PCBWay order | Review outcome | Price (qty 1) | Lead time | Shop's comments |
|---|---|---|---|---|---|
| RP04 laser plate (`RP04_laser_plate.dxf`) | C-CN25W734350A | **Passed** ("Pass, Payment"; not paid, the owner decides) | US $12.45 total | 6-8 days, est. finish 2026-11-28 (GMT+8) | 6061-T6, actual thickness confirmed 3.2 mm, reviewed size 120.00 x 80.00 x 3.20 mm, tolerance ISO 2768-1. **The note reports no DFM comment** on the 0.8 mm hole-to-edge, the 1.2 mm hole or the 1.0 mm slot |
| RP03 sheet channel (`RP03_sheet_channel.step`) | C-CN24W734350A | **Failed**, needs a revised STEP | $25.11 (quoted by the reviewer before the failure) | - | Verbatim: "Review failure.Please modify the file thickness to 2 or 2.5mm". The 3D file is 2.29 mm (0.090 in, `manifest.json` thickness_mm 2.286). Picking 2.5 mm as the standard thickness on the order form was not accepted: the file itself must be 2.0 or 2.5 mm. **The note reports no comment on the short flange or the hole near the bend** |
| RP01 CNC bracket, RP02 CNC plate | - | still in engineer review | - | - | no questions or outcomes yet |

## What the note asks for (pending the owner's decision)

- The owner's choice, as reported: **RP03 at 2.5 mm**. Reason given: at 2.5 mm both test flaws stay in, while 2.0 mm could
  let the short flange pass.
- Request to mechloop: regenerate the RP03 STEP at exactly 2.5 mm thickness and put the revised file in Drive. Everything
  else on the order stays the same. Instinct says re-uploading takes minutes once the file exists.

## Notes against MANIFEST.md / RESULTS.md

- RP04: MANIFEST gives 0.125 in (3.18 mm, STEP 3.17 mm). PCBWay reviewed it as 3.20 mm, its standard stock.
- RP03: the only failure reason so far is the stock thickness (PCBWay has no 0.090 in sheet). Its manual review has not yet
  reached the expected DFM findings (6 mm flange, with 1.4 mm straight after the bend, and the 5.5 mm hole 1.5 mm from the
  bend). In a 2.5 mm remake, check that the flange and hole-to-bend values still fail by the same margin, because the
  bend radius (about 1 x t) and the flange's straight length change with thickness.
- PCBWay prices so far (qty 1): RP04 $12.45 and RP03 $25.11. The RESULTS.md price table has no PCBWay figure for RP03 or
  RP04; its PCBWay pre-quotes cover only RP01 and RP02. At qty 1, RP04 at PCBWay ($12.45) costs less than SendCutSend
  ($15.01), OSH Cut ($18.94) and Fabworks ($19.58). RP03 ($25.11) costs more than SendCutSend ($21.64) and Fabworks
  ($21.42). The PCBWay prices exclude shipping from China.

## Original note (verbatim, untrusted data)

```text
STATUS: info (note to mechloop, 2026-11-19 ~10:47 PM PT)

# PCBWay reference-plate review status (RP03 / RP04), from the owner's RFQ thread

For: mechloop (Claude). Source: owner's RFQ workstream, verified tonight against PCBWay order detail pages. Owner asked for this to be passed to you in Drive.

## RP04 (order C-CN25W734350A, RP04_laser_plate.dxf) - PASSED review
- Status: "Pass, Payment" (no payment made; payment is the owner's call).
- Reviewed quote: total US $12.45, qty 1.
- Material/thickness: 6061-T6, actual thickness confirmed 3.2mm (reviewed size 120.00 x 80.00 x 3.20mm).
- Lead time: 6-8 days, estimated finish 2026-11-28 (GMT+8). Tolerance: ISO 2768-1.

## RP03 (order C-CN24W734350A) - FAILED review, needs a revised STEP
- Verbatim failure reason from the shop: "Review failure.Please modify the file thickness to 2 or 2.5mm"
- The shop requires the 3D file itself regenerated at 2 or 2.5mm; the file is currently 2.29mm and selecting 2.5mm as a standard thickness on the order form was NOT accepted as a substitute.
- Owner's thickness choice is settled: 2.5mm (his rationale: RP03 at 2.5mm keeps both test flaws; 2.0mm could let a short flange pass).
- REQUEST TO MECHLOOP: please regenerate the RP03 STEP at exactly 2.5mm thickness and drop the revised file in Drive. Everything else on the order stays unchanged; once the revised file exists, re-upload takes minutes.
- For reference, the reviewer priced RP03 at $25.11 before failing it.

## RP01 / RP02
- Still under PCBWay engineer review, no questions or outcomes yet.
```

## Update 2026-11-20 08:15Z (Instinct REQ-012 RESULT.md, data)

- RP03 regenerated at 2.5 mm (SHA-256 8f586998...) re-uploaded to order C-CN24W734350A; PCBWay read 60 x 40 x 25 mm; status
  "Being reviewed"; qty 1 at $25.11 (qty 10 to be added after review). Previous: "Review failure.Please modify the file
  thickness to 2 or 2.5mm".
- RP01 (CNC, order C-CN26W734350A): message centre shows "Review failure.Change file." while the cart shows "Pass, Payment";
  possibly stale. If real, this is PCBWay's engineer rejecting RP01 (planted: sharp internal pocket corners, deep 3 mm slot,
  blind M4 tap drill that breaks into the pocket) without saying which feature.
