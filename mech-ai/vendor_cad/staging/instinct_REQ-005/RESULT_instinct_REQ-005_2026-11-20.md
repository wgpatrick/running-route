STATUS: partial

# REQ-005 results — rails addendum (Helix/HIWIN/NSK/igus/Misumi)

Nothing purchased. All prices are listed distributor prices captured 2026-11-19 (US sites, USD), single unit unless noted. CAD = official vendor CAD only.

## Price / MOQ / lead time / CAD summary

| Part (exact config) | Price (unit) | MOQ | Lead time | CAD | Source |
|---|---|---|---|---|---|
| Helix HMR12MLSS1V0N-245L (set, 1 long block) | $100.85 | 10 (Digi-Key) | Digi-Key shows 10 available; 21-day supplier lead time (marketplace item, ships from Helix) | no (not obtained) | digikey.com p/n HMR12MLSS1V0N-245L-15-15 |
| Helix HMR12MLSS1V0N-270L | $106.71 | 10 | 10 available; 21-day supplier lead time | no | digikey.com |
| Helix HMR12MLSS1V0N-300L | not listed at Digi-Key | — | — | no | Anaheim CPC-branded listing (below) is the only US 300 mm source found |
| Helix HMR12MLSS1V0N-320L | $118.44 | 10 | 10 available; 21-day supplier lead time | no | digikey.com |
| CPC MR12MLSSV0N-300-12.5-12.5 (ALTERNATE, not proven identical — see item 1 notes) | $109.00 (1 pc); $104.99 / $102.07 / $100.67 at higher qty | 1 | not in stock, typ. 60 days | no | anaheimautomation.com/cpc-mr12mlssv0n-300-12-5-12-5.html |
| HIWIN MGN12H block, ZF preload (MGN12HZFH) | $59.00 | 1 | cart-enabled | no (blocked, see below) | motionusa.com/manufacturer/hiwin/mgn12hzfh-hiwin |
| HIWIN MGN12H block, Z1 preload (MGN-12-H-Z1-HM) | $59.00 | 1 | 96 in stock | no | digikey.com |
| HIWIN MGN12H block, Z0 preload (MGN-12-H-Z0-HM) | $59.00 | 1 | 70 in stock | no | digikey.com |
| HIWIN MGNR12R rail 245 mm (MGNR12R0245HM/E10/E10) | $126.00 | 1 | cart-enabled | no | motionusa.com |
| HIWIN MGNR12R rail 300 mm (MGN-R12-R300-HM) | $125.00 | 1 | in stock | no | digikey.com (no 245 mm rail listed) |
| HIWIN assembled set (ZF block + 245 mm rail) | ~$185 (calculated: $59 + $126, my arithmetic, not a quoted bundle) | 1 | — | no | calculated from the two lines above |
| NSK PU12UR block / P1U12 rail | not found | — | — | no (blocked) | see notes |
| igus TS-04-12 rail | $119.84 (length basis unconfirmed; configured 250/300 mm price not obtained) | 1 | — | no (blocked) | igus.com product JSON-LD |
| igus TW-04-12 carriage | $27.92 | 1 | — | no | igus.com |
| igus TWE-04-12 carriage | $46.29 | 1 | — | no | igus.com |
| Misumi SSEB13-245 (set, block+rail, light preload, high grade) | $117.27 (qty 1-3); $111.39 (4-6); $105.54 (7-10); $99.66 (11-599) | 1 | ship date shown Nov 23, 2026 | no (blocked) | us.misumi-ec.com |
| Misumi SSEB13-250 / -300 | not offered — SSEB13 comes in 25 mm steps (45…970); 245 yes, nearest to 250/300 are 295 and 320 | — | — | no | us.misumi-ec.com |
| Misumi SSEBL13-250 (set, long block, light preload, high grade) | $158.95 | 1 | ship date shown Nov 30, 2026 | no (blocked) | us.misumi-ec.com |
| Misumi SSEBL13-300 | $168.11 | 1 | ship date shown Nov 30, 2026 | no | us.misumi-ec.com |
| Misumi SSEBL13-245 | no price shown (part number SSEBL13-245 forms but price field stays "---") | — | — | no | us.misumi-ec.com |

## Item 1 — Helix HMR12MLSS1V0N (REQ notes CPC/Chieftek manufacture; not confirmed by public sources — see provenance caution below)

Files landed in this folder:
- Helix-Miniature-Linear-Guides__catalog.pdf — the requested catalogue.
- CPC-MR__catalog.pdf — CPC MR series catalogue (accuracy class, preload, parallelism).
- CPC-MR12__spec.pdf — CPC MR12 spec sheet.

Confirmed from the catalogue/spec:
- Rail hole pitch 25 mm, M3 counterbored mounting holes (6 × 3.5 × 4.5). Matches expectation.
- Block mounting pattern 20 × 20 mm, tapped M3 × 3.5 — MGN12H-compatible. Confirmed.
- Size 12 ML (long block) stainless: dynamic C = 3,240 N, static C0 = 5,630 N. SS series max speed 3 m/s, max accel 250 m/s² (60 at V0 preload).
- Accuracy grades P/H/N (N tolerance ±40 µm height, ±40 µm width; parallelism per spec sheet); preload V0 = +5–0 µm, VS = +2–0, V1 = 0–-5 µm at size 12.
- "1V0N" decodes as 1 block, V0 preload, N (standard) accuracy.

Price/MOQ/lead:
- Digi-Key (marketplace listing, ships from Helix): MOQ 10; 245L $100.85, 270L $106.71, 320L $118.44 each; Digi-Key shows 10 available of each with a 21-day supplier lead time. 300L is NOT listed at Digi-Key.
- Only 1-pc 300 mm source found: Anaheim Automation, CPC-branded MR12MLSSV0N-300-12.5-12.5, $109 single, tiered down to $100.67; not in stock, typical 60-day lead. PROVENANCE CAUTION: this CPC-branded listing shares the MR12ML...V0N model-code pattern and the dimensions above, but I found no manufacturer statement proving it is the identical part to the Helix HMR12MLSS1V0N. The REQ notes the Helix guides are made by CPC/Chieftek, while Helix's own product page (helixlinear.com/miniature-linear-guides) says "American-manufactured: full quality control and traceability from design through production." I could not reconcile those two claims from public sources, so treat the Anaheim/CPC listing as an alternate with matching code pattern and dimensions, not a proven-identical part.
- Helix's own store lists only HMR2–HMR7 sizes (no 12). Motion Industries lists only an EE-seal 245L variant ($176.47, different seal code, not the requested part). MotionUSA is phone-quote only — excluded by the standing no-calls rule.
- STEP per length: NOT obtained. Helix's CAD library is a client-side JS app; no downloadable STEP route was cracked this run.

## Item 2 — HIWIN MGN12H / MGN12C / MGNR12R

- STEP: STILL BLOCKED, now on account access rather than the disclaimer. Will approved accepting the disclaimer (2026-11-19 iMessage); I accepted it as guest, and the download stage then required a configure.hiwin.com login (the guest path warns "Signup required at end"). The only HIWIN credential on file (hiwinsupport.com support account) was rejected: "Incorrect Username or Password Provided." HIWIN self-registration failed on their side on 2026-11-14, and creating a new account needs Will's OK under the standing rules. Original disclaimer analysis kept below for the record.
- hiwin.com CAD downloads route to configure.hiwin.com (DriveWorks; no account needed, "Continue as Guest" works). A guest session configured MGN12H ZF successfully (part number MGN-12-H-1XXXX-ZF-H-M), but before the model download the configurator shows a click-through with "I Accept" / "I Decline". Verbatim wording (captured 2026-11-19 at configure.hiwin.com/run.html, Linear Guideway Configurator): "You are responsible for verifying the suitability of the product configuration for your application. HIWIN makes no warranty, expressed or implied, regarding the suitability of a product configuration to an application. Submit configurations to Hiwin engineering for a free review before ordering." What acceptance means: an acknowledgment that the user (not HIWIN) is responsible for checking the configuration suits the application, and a warranty disclaimer on configuration suitability. It contains no license grant, no restriction on using or keeping the downloaded CAD, and no account or payment terms. Per the standing no-extra-terms rule I clicked "I Decline", which ends the session. If Will approves accepting this acknowledgment, the STEP downloads are otherwise reachable.
- Prices in the table above (ZF block and 245 mm rail both cart-enabled at MotionUSA; Z0/Z1 blocks and 220/300/320 mm rails at Digi-Key).
- MGN12C (short block) STEP/price: covered by the same blocked CAD route; no distributor price captured this run.

## Item 3 — NSK PU12UR / P1U12

- File landed: PU12UR__datasheet.pdf (NSK PU/PE series datasheet, covers PU12UR and P1U12 rails).
- CAD: BLOCKED. NSK's nskautomation.com configurator is an embedded partcommunity (CADENAS) viewer — the CADENAS family is exhausted per the standing ruling. store.nsk.com product pages (Salesforce/Lightning) render no product data even in a real browser session.
- US distributor price: not found. MROSupply lists the PAU12TRS assembly ($49.26, captured in REQ-004) but no separate PU12UR block or P1U12 rail; apollousa.com lists "P1U12-S guideways" with unreliable page data ($2,641.56, meta tags point at a different part — not trustworthy).

## Item 4 — igus drylin T (TS-04-12, TW-04-12, TWE-04-12)

- Prices from igus.com US product JSON-LD (in table). The $119.84 TS-04-12 figure's length basis is unconfirmed; igus.com redirected every configured-length (250/300 mm) page request this run, so the configured rail price is still open.
- Drawing + CAD: BLOCKED. igus CAD downloads are served by the CADENAS-powered igus CAD service — exhausted per the standing ruling.

## Item 5 — Misumi SSEB13 / SSEBL13

- SSEB13 (standard block): fixed 25 mm length steps 45–970. 245 exists; 250 and 300 do not (nearest are 295, 320). SSEB13-245 price $117.27 (qty 1-3), volume tiers in the table, ship date Nov 23, 2026 shown. Note: series is non-interchangeable, block and rail sold as a set only.
- SSEBL13 (long block): rail length freely configurable 46–970 mm. Captured 2026-11-19: SSEBL13-250 $158.95 and SSEBL13-300 $168.11, both showing ship date Nov 30, 2026. SSEBL13-245 forms a valid part number but Misumi shows no price for it. REQ-004 family reference: SSELBL13-300 $185.97 (stainless long-block type).
- CAD: BLOCKED by Misumi's own registration, not by permission. Will explicitly approved creating a free Misumi account under wgpatrick@gmail.com (2026-11-18, iMessage). Registration was attempted that evening on two separate browser routes: the first returned "Validation failed, please contact MISUMI Customer Service if you need assistance with your registration" at the email step; the second silently refused to advance. An earlier attempt on 2026-11-14 failed the same way. The signup form's disclosures are: email registration, then company/user information, with a notice that "Products purchased from us are only for general industrial use" and an export/re-export guideline reference. The REQ names 3Dfindit as an allowed CAD source, but 3Dfindit is CADENAS and that family was technically exhausted earlier — flagging the conflict rather than retrying a failed route. Plausible ways forward: Will registers himself from his own device (his IP passes the bot check), or MISUMI USA replies to the API-access email sent 2026-11-19 (replies watched through Nov 23).

## Open items for next run / decisions for Will

1. HIWIN STEP — disclaimer accepted with Will's OK, but download needs a configure.hiwin.com account. Support-site credential rejected; Nov 14 self-registration failed on HIWIN's side. Needs Will: register a configure.hiwin.com "New User" account himself, or approve another registration attempt by us.
2. Misumi CAD — account already approved by Will 2026-11-18 but Misumi's registration rejects our signups; needs Will to register himself or a MISUMI USA reply.
3. igus configured rail price at 250/300 mm — retry when igus.com stops redirecting.
4. Helix per-length STEP — CAD library JS route still uncracked.
5. NSK PU12UR/P1U12 US price — no distributor listing found; NSK store page never rendered data.
