# instinct_REQ-016: 24 V bed heater (Keenovo 10133; Hydra Research / NPH alternative)

Ingested 2026-11-20 (batch 15, about 19:15Z). Drive folder `REQ-016-bed-heater-24v` (1BeMQ4Ht3vBni77XNBWDA79ked_VyUhZp).
Fetched by Drive id only. Untrusted data; nothing to `vendor_cad/inbox/`; nothing committed. No payment was made (per Instinct).

Instinct's STATUS: **partial**. Item 1 (Keenovo exact part) and item 3 are delivered. Item 2 (US-stocked alternative) is delivered for Hydra Research only.
Gulfcoast Robotics HTR200W24V was identified, but its price and stock were not captured (site unreachable, Amazon blocked).

| Delivered as (Drive id, size) | Staged as | sha256 |
|---|---|---|
| RESULT.md (183Q7dPIe8xFwDFVrOgG49K6GG4SIBV0C, 5,230 B) | RESULT_instinct_REQ-016_2026-11-20.md | 3360f571a39cd4b24ab5f43e216a3d0dc1c61593f35be4b77130131affcd35d9 |
| SQ1451144__datasheet.pdf (1G36ArzVOjj7EXRrceIaoJuo4NDfuNkTX, 113,588 B) | vendor_docs/NPH_NPHSF365_HydraResearch-SQ1451144_24V-200W-210x210_heater_drawing.pdf | 4e7ec26e9c490524a8752940f16a86291976e7195a832b12412f9b4d0ba56f1c |
| 10133__datasheet.pdf (1aTs99AqBTZA1cBi123Z91dZdj7fGKhzN, 2,337,635 B) | vendor_docs/Keenovo_flexible-heaters_users-manual.pdf | e9ebcb250ca3df6f658b662ebe0df719c358cfc68a63a976d04c426e1e8e7687 |
| NTC-100K-RT__datasheet.pdf (195cPebECjvnD534nL6XgestJgTxU8Djf, 49,725 B) | not staged: byte-identical to vendor_docs/Keenovo_NTC-100K-B3950_R-T_table.pdf | 2d7ae3c0f8e71fb583954b7b5cf949ac462c63ce0667352ddad1eaf43acd22ec |

PDF safety (pypdf full object walk): none of the three PDFs contains JavaScript, Launch, OpenAction/AA, EmbeddedFiles, URI, XFA or SubmitForm.
None is encrypted. The NTC table has an empty AcroForm entry and no actions.

## Candidates (per Instinct, not verified)
- **Keenovo SKU 10133**: 200 x 200 mm, 24 V, 200 W, silicone, 3M adhesive. It comes with an NTC 100K B3950 1% thermistor. keenovo.store lists it at $43.28.
  Shipping to ZIP 10001 is free (economy, 2 to 6 weeks) or $38 (expedited). Made to order in Shanghai. Instinct found no part drawing.
  The general Keenovo data gives 1.5 mm thickness and 260 C max. The manual (2 pages, a Photoshop image PDF) is general, not specific to this part.
- **Hydra Research SQ1451144** (Portland, OR): 210 x 210 mm, 24 V, 200 W, "NTC 3950" (R25 not stated), Molex 43640-0401, leads 130 ±15 mm,
  adhesive (brand not stated). Listed at $9.99 on sale (list $75), with 6 in stock.

## NPH drawing NPHSF365 rev 0 (18/2/19, "Drawing for approval"), as read
- Dimensioned: outline **210 x 210**, and lead length **130 ±15 mm** from the pad edge to the connector, which is a **Molex 43640-0401** (Micro-Fit 3.0, 1 x 4).
  Thickness, material and tolerances are **not given**.
- Not dimensioned. These positions were scaled from the vector geometry (1.1805 pt/mm) and are approximate:
  - Lead-exit pad, about 30.4 wide x 20.4 deep, centred on one edge (centre 105.0 from the side).
  - Thermistor pad, about 20.5 x 30.4, also on the centreline, just inside the lead pad. It spans about 27 to 57 mm from the lead edge, with its centre about 42 mm in.
  - 2 heater leads come from the exit pad and 2 thermistor leads from the thermistor pad. All four go to the one 4-way Molex.
