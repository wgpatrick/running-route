# Fabricators: SendCutSend (cut sheet) and Xometry (CNC)

The owner has named the shops that will make printer_v8's custom metal parts: **SendCutSend** for the 20 flat
laser-cut parts and **Xometry** (or an equivalent online CNC bureau) for the 2 machined parts. This page holds
those shops' own published design rules, how a design selects them, what v8 fails or wastes under them, a
material review, and an ordering checklist for each.

Every number below was read from the supplier's public pages on **2026-11-15** by plain page fetch (no
account, no upload, no quote). The machine-readable form, with the URL, date and the page's own words for each
figure, is `mechloop/shops/sendcutsend.json` and `mechloop/shops/xometry.json`. Where a supplier publishes
nothing, this page says so; the two values that are recalled rather than read are marked **recalled**.

Printed parts: no supplier was named. The generic FDM rules in `mechloop/verifiers/dfm_rules.py` and
`docs/DFM.md` still apply to all 13 of them, unchanged.

## 1. Selecting a shop in a design

```python
from mechloop.shops import assign

d.manufacturing = {"shop": "generic", "sheet": {"method": "laser"}, ...}   # unchanged
...                                                                         # add all parts
assign(d, sheet="sendcutsend", machined="xometry")    # after the parts exist: names the shop on every custom part of that process
```

`assign` writes `meta["dfm"]["shop"]` on each part (a part that already names a shop keeps it). One part can be
set by hand: `d.add(..., meta={"dfm": {"shop": "xometry"}})`. `d.manufacturing["shop"] = "sendcutsend"` still
works for a design made at one shop, but only the manufacture verifier reads it; the tolerance simulation sees
parts, not the design, so use `assign` (or per-part meta) when the supplier's tolerance should be used.

What a named shop changes:

| Where | Effect |
|---|---|
| manufacture: stock | thickness must be one the shop stocks in that material, within 0.05 mm (`non_stock_thickness`: error for sheet, warning for machined plate); a material absent from the chart is `shop_material_not_offered` (error) |
| manufacture: rule limits | the shop's own figure replaces the general one where it publishes one (table in section 2 and 3); the finding's `source` is the shop's page |
| manufacture: shop checks | `shop_web_below_minimum`, `shop_tap_not_offered`, `shop_countersink_not_offered`, `bare_steel_no_finish`, `shop_finish_not_offered`, `shop_material_not_listed`, `shop_thread_callout`, `shop_part_too_big`, `shop_feature_below_minimum`, `shop_process_not_profiled` |
| manufacture: metrics | each sheet part's row gains `shop_services` (nearest stock and the difference, which of deburr / tumble / tap / countersink / powder coat / plating / anodize / bend / hardware fit that material, thickness and size, least web against the minimum); each machined part's row gains `shop_notes` (general tolerance, flatness without a drawing, the edge-break statement, finish) |
| tolerance | `tolerance.process.tol(part)` returns the shop's cut or machining tolerance in place of the class value for the fields it publishes; the class table itself is untouched |

Declaring a finish: `meta={"finish": "powder_coat"}` (`zinc`, `nickel`, `anodize`, `paint`, `oil`, `chem_film`,
`bare`). Carbon steel with none is `bare_steel_no_finish` (warning); a finish the shop does not list for that
stock and size is `shop_finish_not_offered` (error).

A face or pattern that will be toleranced on a drawing: `meta={"dfm": {"shop": "xometry", "tolerance": {"flat": 0.02}}}`
(one standard deviation, same fields as `tolerance.process.PROCESS`).

Code: data in `mechloop/shops/*.json`, logic in `mechloop/shops/__init__.py`. Three hooks, all additive:
`dfm_rules.py` (profiles merged into `SHOPS`; `Limits` reads a shop's `limits`), `manufacture.py` (one call
after a part's process checks), `tolerance/process.py` (`tol`). Tests: `tests/test_shop_profiles.py`.

A published "+/-" is taken as two standard deviations, the convention already used in
`tolerance/process.py`.

## 2. SendCutSend: published rules

Sources (all read 2026-11-15):
[min/max sizes](https://sendcutsend.com/materials/min-max/),
[processing min/max](https://sendcutsend.com/materials/processing-min-max/),
[sheet cutting guidelines](https://sendcutsend.com/guidelines/sheet-cutting/),
[sheet cutting service](https://sendcutsend.com/services/laser-cutting/),
[tolerances and cut-feature relationships](https://sendcutsend.com/blog/basic-tolerances-and-cut-feature-relationships/),
[hole distance specifications](https://sendcutsend.com/blog/how-to-apply-hole-distance-specifications/),
[tapping](https://sendcutsend.com/services/tapping/),
[countersinking](https://sendcutsend.com/services/countersinking/),
[bending](https://sendcutsend.com/services/cnc-bending/),
[deburring](https://sendcutsend.com/services/deburring-services/),
[tumbling](https://sendcutsend.com/services/tumbling/),
[anodizing](https://sendcutsend.com/services/anodizing/),
[powder coating](https://sendcutsend.com/services/powder-coating/),
[plating](https://sendcutsend.com/services/plating/),
[hardware](https://sendcutsend.com/services/hardware/) and its [catalog](https://sendcutsend.com/guidelines/hardware/catalog/),
[edge quality](https://sendcutsend.com/blog/edge-quality-and-surface-finish/),
[warping](https://sendcutsend.com/faq/will-my-metal-parts-be-perfectly-flat/),
material pages for [6061](https://sendcutsend.com/materials/6061-aluminum/), [5052](https://sendcutsend.com/materials/5052-aluminum/),
[mild steel](https://sendcutsend.com/materials/mild-steel/), [304](https://sendcutsend.com/materials/stainless-steel/),
[MIC-6](https://sendcutsend.com/materials/mic-6-cast-aluminum/), [Delrin](https://sendcutsend.com/materials/delrin/),
[CNC (billet) guidelines](https://sendcutsend.com/guidelines/cnc-machining/).

### 2.1 Cutting

| Rule | Figure | The page's words | Checked by |
|---|---|---|---|
| Process | fibre laser for all metals here; CO2 laser for 3.18 mm Delrin, CNC router for thicker Delrin | "You don't choose the cutting method. We route your part to the machine best suited to your material" | process column of the stock tables |
| Minimum hole or cut-out | 0.5 x thickness | "Laser Cutting: At least 50% of material thickness ... Holes smaller than the minimum will distort, char, or fail to cut." | `hole_too_small_to_cut` (error) |
| Per-thickness minimum hole | **not read** | "the exact minimum changes with the material and thickness. The current values for every stock we carry live on each material's page" (behind "View specs", loaded by script) | - |
| Minimum web (bridge) between cut features and to the edge | 0.5 x thickness | "We recommend that hole diameters and bridging widths be no less than 50% of the material thickness. For example, on a 0.125" thick part, this would mean having 0.0625" between all of your cut features, or cut features and the edge of your part." | `shop_web_below_minimum` (error) |
| Preferred web | 1 to 1.5 x thickness | "we would prefer that wall thickness or bridging be closer to 1X - 1.5X the material thickness" | `holes_too_close`, `hole_too_close_to_edge` (warning, the general 1 x thickness) |
| Hole to edge, recommended | 1 x hole diameter; slots 1.5 x width | "we generally recommend keeping your holes at least 1X their diameter from an edge and slots at least 1.5X their width away from edges or other cut features" | data only |
| Cut tolerance | +/-0.127 mm under 305 mm, +/-0.254 mm over | "Laser: ±0.005" on parts under 12", ±0.010" on parts over 12"" | tolerance simulation |
| What the tolerance means | per feature, in X or Y | "any given cut feature or perimeter geometry may be +/-.005" ... in either the X or Y axis" | - |
| Kerf | compensated by the shop; common-line gap 0.15 to 0.30 mm | "Our software accounts for kerf"; "The actual gap between common-nested parts runs 0.006" to 0.012" depending on material" | - |
| Inside corners | practically sharp | "Laser Cutting: Approximately the kerf width (very small)" (router: .063"; waterjet: .032") | general rule |
| Laser thickness range | to 19.05 mm | "Laser: .015" to .750"" | `sheet.thickness_max_laser_mm` = 19.05 |
| Edge over 4.75 mm | striated | "Materials over .187" thick will show small striations and an abrasive edge. Add deburring for a cleaner finish." | - |
| Dross | light on thick aluminium | "Thicker gauges (.190"-.500") may show light dross that can be removed easily" (6061 page); "our deburring process only contacts the top and bottom face of the material, so it will not fully remove edge dross" | - |
| Tabs | laser micro-joints 0.4 to 0.8 mm wide, about 0.25 mm tall; "Detabbing" is a listed service (+1 day) | "Tabs / micro joints: Not removed prior to coating ... Typically .015"-.030" wide, ~.010" tall." | - |
| Material removed | under 50 % | "removing around 50% of the material starts to increase the likelihood it will warp" | `mostly_holes` |
| Flatness | **not published** | "Sometimes, there's nothing you can do, and warping just happens"; "often warped parts can't be deburred" | class value kept |
| Part size | per material and thickness (tables below); smallest 6.35 x 9.5 mm, largest instant-quote about 1118 x 1727 mm | min/max chart | `too_small_to_cut`, `too_big_to_cut` (error) |

### 2.2 Stock, sizes and services by thickness

Read from the two min/max charts; mm are the inch figure x 25.4 (the chart's own rounded mm are kept in the
JSON). "min part" and "max part" are for cutting (instant quote). A dash is "N/A" or no row in the chart.
Tap: smallest to largest metric tap. Bend radius is the shop's only radius for that stock ("we don't offer
custom bend radii"); min flange is after the bend, from the outside.

**6061 T6 Aluminum** (`al6061`): 6061-T6. Laser cut, +/- .005" tolerance

| in | mm | process | min part mm | max part mm | tap | csk | deburr max mm | tumble | powder | zinc / nickel | anodize | bend: radius / min flange / max length mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.040 | 1.016 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | - | - | - | - | - | - | - | - |
| 0.063 | 1.6 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | M2-M6 | - | 914.4 x 3048 | - | yes | - | yes | - |
| 0.080 | 2.032 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | M2-M6 | - | 914.4 x 3048 | - | yes | - | yes | - |
| 0.100 | 2.54 | Fiber Laser | 6.35 x 9.52 | 762 x 1422.4 | M2-M6 | - | - | - | yes | - | yes | - |
| 0.125 | 3.175 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M10 | yes | 1016 x 3048 | yes | yes | - | yes | - |
| 0.187 | 4.75 | Fiber Laser | 12.7 x 12.7 | 1117.6 x 1422.4 | M3-M10 | yes | 1016 x 3048 | yes | yes | - | yes | - |
| 0.250 | 6.35 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1727.2 | M3-M10 | yes | 1016 x 3048 | yes | yes | - | yes | - |
| 0.313 | 7.95 | Fiber Laser | 19.05 x 25.4 | 1117.6 x 1422.4 | M3-M10 | yes | 1016 x 2489.2 | yes | yes | - | yes | - |
| 0.375 | 9.525 | Fiber Laser | 19.05 x 25.4 | 1117.6 x 1422.4 | M5-M10 | yes | 1016 x 2082.8 | yes | yes | - | yes | - |
| 0.500 | 12.7 | Fiber Laser | 25.4 x 25.4 | 1117.6 x 1422.4 | M5-M10 | yes | 1016 x 1549.4 | yes | yes | - | yes | - |
| 0.625 | 15.875 | Fiber Laser | 76.2 x 76.2 | 1041.4 x 1422.4 | M8-M10 | yes | 1016 x 1244.6 | yes | yes | - | yes | - |
| 0.750 | 19.05 | Fiber Laser | 76.2 x 76.2 | 1041.4 x 1422.4 | M8-M16 | yes | 1016 x 1041.4 | yes | yes | - | yes | - |

**5052 H32 Aluminum** (`al5052`): 5052-H32. Laser cut, +/- .005" tolerance

| in | mm | process | min part mm | max part mm | tap | csk | deburr max mm | tumble | powder | zinc / nickel | anodize | bend: radius / min flange / max length mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.040 | 1.016 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | - | - | - | - | - | - | - | 0.61 / 7.26 / 1117.6 |
| 0.063 | 1.6 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M4 | - | 914.4 x 3048 | - | yes | - | yes | 0.89 / 7.7 / 1117.6 |
| 0.080 | 2.032 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M6 | - | 914.4 x 3048 | - | yes | - | yes | 1.14 / 7.95 / 1117.6 |
| 0.090 | 2.286 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | M2-M6 | - | 914.4 x 3048 | - | yes | - | yes | 0.81 / 8.28 / 1117.6 |
| 0.100 | 2.54 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M6 | - | 914.4 x 3048 | - | yes | - | yes | 3.17 / 11.76 / 1117.6 |
| 0.125 | 3.175 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M10 | yes | 1016 x 3048 | yes | yes | - | yes | 3.17 / 12.09 / 1117.6 |
| 0.187 | 4.75 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1727.2 | M3-M10 | yes | 1016 x 3048 | yes | yes | - | yes | 6.35 / 20.27 / 1117.6 |
| 0.250 | 6.35 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1727.2 | M3-M10 | yes | 1016 x 3048 | yes | yes | - | yes | 6.35 / 34.82 / 1117.6 |
| 0.313 | 7.95 | Fiber Laser | 19.05 x 25.4 | 1117.6 x 1422.4 | M5-M10 | yes | 1016 x 2489.2 | yes | yes | - | yes | - |
| 0.375 | 9.525 | Fiber Laser | 19.05 x 25.4 | 1117.6 x 1422.4 | M5-M10 | yes | 1016 x 2082.8 | yes | yes | - | yes | - |
| 0.500 | 12.7 | Fiber Laser | 25.4 x 25.4 | 1117.6 x 1422.4 | M5-M10 | yes | 1016 x 1549.4 | yes | yes | - | yes | - |

**Mild Steel** (`steel`): A1008 cold rolled up to .135″ (3.43 mm); A36/A1018 HRP&O (hot rolled, pickled and oiled) from .187″ (4.75 mm). Tolerance: ±.005″ across all thicknesses from .030″–.500″.

| in | mm | process | min part mm | max part mm | tap | csk | deburr max mm | tumble | powder | zinc / nickel | anodize | bend: radius / min flange / max length mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.030 | 0.762 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | - | - | - | - | - | - | - | 1.14 / 7.26 / 1117.6 |
| 0.048 | 1.219 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | - | - | 914.4 x 3048 | - | yes | - | - | 1.14 / 7.57 / 1117.6 |
| 0.059 | 1.499 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M3 | - | 914.4 x 3048 | - | yes | - | - | 1.6 / 7.85 / 1117.6 |
| 0.074 | 1.88 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M6 | - | 914.4 x 3048 | - | yes | - | - | 1.6 / 8.13 / 1117.6 |
| 0.104 | 2.642 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M6 | - | 914.4 x 2286 | - | yes | - | - | 1.6 / 11.66 / 1117.6 |
| 0.119 | 3.023 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M8 | - | 1016 x 2133.6 | yes | yes | - | - | 1.6 / 11.84 / 1117.6 |
| 0.135 | 3.429 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M10 | - | 1016 x 1981.2 | yes | yes | - | - | 2.54 / 18.85 / 1117.6 |
| 0.187 | 4.75 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1422.4 | M2-M10 | - | - | yes | yes | yes | - | 3.17 / 19.84 / 558.8 |
| 0.250 | 6.35 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1422.4 | M2-M10 | - | 1016 x 1066.8 | yes | yes | yes | - | 3.81 / 34.57 / 508 |
| 0.313 | 7.95 | Fiber Laser | 25.4 x 25.4 | 1117.6 x 1422.4 | M4-M10 | - | 609.6 x 1168.4 | yes | yes | yes | - | - |
| 0.375 | 9.525 | Fiber Laser | 25.4 x 25.4 | 1117.6 x 1422.4 | M6-M10 | - | 609.6 x 1168.4 | yes | yes | yes | - | - |
| 0.500 | 12.7 | Fiber Laser | 25.4 x 25.4 | 1117.6 x 1422.4 | M6-M10 | - | 609.6 x 1168.4 | yes | yes | yes | - | - |

**304 Stainless Steel** (`stainless304`): 304. Laser cut, +/- .005" tolerance

| in | mm | process | min part mm | max part mm | tap | csk | deburr max mm | tumble | powder | zinc / nickel | anodize | bend: radius / min flange / max length mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.030 | 0.762 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | - | - | - | - | - | - | - | 2.03 / 7.47 / 1117.6 |
| 0.048 | 1.219 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | - | - | 914.4 x 3048 | - | yes | - | - | 2.03 / 7.8 / 1117.6 |
| 0.060 | 1.524 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M6 | - | 914.4 x 3048 | - | yes | - | - | 1.78 / 7.98 / 1117.6 |
| 0.074 | 1.88 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M6 | - | 914.4 x 3048 | - | yes | - | - | 1.9 / 8.23 / 1117.6 |
| 0.100 | 2.54 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | M2-M6 | - | 914.4 x 3048 | - | yes | - | - | 4.75 / 18.59 / 889 |
| 0.125 | 3.175 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1727.2 | M2-M10 | - | 1016 x 2108.2 | yes | yes | - | - | 3.81 / 18.8 / 1016 |
| 0.187 | 4.75 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | M3-M10 | - | 1016 x 1397 | yes | yes | - | - | 3.3 / 19.91 / 914.4 |
| 0.250 | 6.35 | Fiber Laser | 6.35 x 9.52 | 1117.6 x 1422.4 | M4-M10 | - | 1016 x 1041.4 | yes | yes | - | - | 5.71 / 35.08 / 457.2 |
| 0.375 | 9.525 | Fiber Laser | 12.7 x 12.7 | 1117.6 x 1422.4 | M6-M10 | - | 609.6 x 1168.4 | yes | yes | - | - | - |
| 0.500 | 12.7 | Fiber Laser | 12.7 x 12.7 | 1117.6 x 1422.4 | M6-M10 | - | 609.6 x 1168.4 | yes | yes | - | - | - |

**MIC-6 Cast Aluminum (ALUMIC-6)** (`al_mic6`): MIC-6 cast tooling plate. Laser cut, +/- .005" tolerance

| in | mm | process | min part mm | max part mm | tap | csk | deburr max mm | tumble | powder | zinc / nickel | anodize | bend: radius / min flange / max length mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.250 | 6.35 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1422.4 | M2-M10 | yes | 914.4 x 1168.4 | - | - | - | - | - |
| 0.375 | 9.525 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1422.4 | M3-M10 | yes | 914.4 x 1168.4 | - | - | - | - | - |
| 0.500 | 12.7 | Fiber Laser | 12.7 x 19.05 | 1117.6 x 1422.4 | M3-M10 | yes | 914.4 x 1168.4 | - | - | - | - | - |

**Delrin 150 (acetal homopolymer, POM-H)** (`delrin`): Delrin 150. Laser cut, +/- .009" tolerance, CNC routed +/- .005"

| in | mm | process | min part mm | max part mm | tap | csk | deburr max mm | tumble | powder | zinc / nickel | anodize | bend: radius / min flange / max length mm |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.125 | 3.175 | CO2 Laser | 25.4 x 50.8 | 584.2 x 1117.6 | M2-M10 | yes | - | - | - | - | - | - |
| 0.187 | 4.75 | CNC Router | 25.4 x 50.8 | 584.2 x 1117.6 | - | - | - | - | - | - | - | - |
| 0.270 | 6.858 | CNC Router | 25.4 x 50.8 | 863.6 x 1117.6 | - | - | - | - | - | - | - | - |

Oddities in the source, kept as found: mild steel .187" has no row in the deburring table; the Delrin page
lists two thicknesses (.125", .270") while the min/max chart lists three and the tapping table names .125" and
.250"; the MIC-6 page gives two different minimum sizes; the min/max chart rounds .135" to "3.5mm" where the
mild-steel page says 3.43 mm.

Other plastics on the min/max chart (not profiled): ABS, acrylic, HDPE, polycarbonate, polypropylene, UHMW
(CNC router or laser), carbon fibre, G10/FR-4, phenolic (waterjet, +/-0.229 mm).

### 2.3 Services

| Service | Rule | The page's words |
|---|---|---|
| Deburring | parts 25.4 x 76.2 mm and larger, from 1.22 mm thick; max per table; +0 days | "Min part size 1" x 3" ... Min thickness .048"" |
| Deburring result | **faces only; not an edge break** | "Parts are burr-free, smooth, and ready to use, but not perfectly cosmetic ... Some edges will be sharp, while others may have slight rounding ... Small machining tabs will remain on edges ... aggressive edge softening must be done after delivery." "Deburred Mild Steel is more prone to rusting, and is not recommended for outdoor use unless it's coated." |
| Tumbling | parts 12.7 x 38.1 mm to 101.6 x 177.8 mm, from 3.02 mm thick; +1-2 days | "Min part size (flat) .5" x 1.5"; Max part size (flat) 4" x 7"; Min material thickness .119"" |
| Tumbling result | **the edge-softening service**; radius not controlled | "Tumbling is for deburring and edge softening only ... Expect rounded, uniform edges, not a specific radius. Holes and cutouts: Features smaller than 0.5" won't be fully processed inside." "For tumbling plus anodizing, plating, or powder coating, submit a custom quote request." |
| Tapping | from 1.5 mm; part 25.4 x 38.1 to 914 x 1168 mm; thread range per table; perpendicular, right-hand only; +1-2 days | "Model your hole at the size listed below for the tap you want. We automatically resize laser cut holes to the correct drill size": M2 1.66, M2.5 2.11, M3 2.60, M4 3.41, M5 4.32, M6 5.16, M8 6.96, M10 8.74 mm |
| Tapped hole to edge | (tap hole / 2) + a per-material minimum, **not read** (one example: 1.6 mm for .125" 5052) | "Keep the center of any tapped hole at least this distance from other cut features: (tap hole size ÷ 2) + minimum tap hole-to-edge distance for the material" |
| Tapping and powder coat | threads are coated | "Tapped holes are not plugged before coating; expect to chase threads after" |
| Countersinking | from 3.18 mm; part 25.4 x 101.6 to 355.6 x 1168 mm; 82 or 90 deg; depth at most 60 % of thickness; +/-0.38 mm | "Draw only the minor hole in your CAD file"; metric 90 deg: M3 major 6 / minor 3.18 / depth 1.35; M4 8 / 4.04 / 1.93; M5 10 / 5.00 / 2.44 mm. Not offered in mild steel or 304 (no rows) |
| Hardware (PEM) | nuts, standoffs, studs incl. M3, M4, M5; part 25.4 x 38.1 to 914 x 1168 mm | "Nut, M3 (S-M3-0): hole in sheet .168", minimum sheet thickness .031", hole C/L to edge .250", C/L to C/L .336"". "Hardware is installed after anodizing and plating ... before powder coating" |
| Bending | 5052, mild steel, 304 (not 6061, MIC-6, Delrin); flat part 9.5 x 38.1 to 762 x 1118 mm; angle to 130 deg | "Bend-to-edge tolerance: +/- 0.015" (each additional bend adds at least 0.015")"; "Bends up to 24": +/- 1°"; U-channel base at least 2 x flange; tapped holes at least half the die width from the bend line (die widths **not read**) |
| Anodizing | 5052 / 6061 / 7075 from 1.6 mm; part 25.4 x 76.2 to 584 x 584 mm; hanging hole 1.6 mm or larger | "Type II anodizing adds ~0.0002"-0.0009" per side"; "**Anodizing is non-conductive**"; "Deburring is preselected on all anodized sheet metal parts" |
| Powder coating | from 1.22 mm; part 25.4 x 76.2 to 762 x 914 mm; hanging hole | "Adds .002"-.005" per side (.004"-.010" total). Account for this in areas with tight clearances or small holes." |
| Zinc / nickel plating | mild steel **from 4.75 mm only**; part 25.4 x 76.2 to 584 x 584 mm | "Zinc plating adds approximately .0003" per side; nickel adds approximately .0002" per side" |
| CNC machining (billet) | 6061-T6 only, part up to 178 x 178 x 305 mm, +/-0.127 mm | "Sharp edges will have a .010" / .254mm edge break"; "Internal features will have a minimum radius of .0625"" |

Coatings and fits: powder adds 0.05 to 0.13 mm per side, so a 3.4 mm hole can come back 3.15 mm and a 5 mm
plate up to 5.25 mm. Coatings and earth bonding: anodize is non-conductive and powder coat insulates, so a
protective-earth bond through a coated part needs a bare contact (leave the part uncoated, scrape under a
serrated washer, or use a dedicated stud).

### 2.4 Files

"2D vector files (preferred for flat cuts): .DXF (preferred), .DWG, .EPS, .AI" (3D .STEP for bent parts);
"Scale 1:1 ... Inch units are preferred. Mm is fine if you keep it consistent between your file and your quote
inputs. We don't support cm or meter units"; "Strip out dimensions, notes, borders, title blocks"; "Convert all
text to outlines"; "Closed contours only"; "No intersecting or shared lines"; "Single layer for cut paths";
"one part per file"; "For hole services (countersinking, dimple forming, hardware, tapping), model simple
through-holes and add the service in the app after upload"; "Model the part at the thickness you'll order".
The DXFs `verify` writes (`out/<name>/dxf/<part>.dxf`: millimetres, 1:1, one part per file, one layer `CUT`,
true arcs and circles, no text) meet these.

### 2.5 Not found

Per-thickness minimum hole, minimum bridge, tap hole-to-edge, countersink centre-to-edge and die width (on the
material pages behind "View specs", loaded from the ordering application; not read); flatness; the edge radius
left by deburring or tumbling; a hole-to-hole position tolerance; stock thickness tolerance; prices (no quote
was requested).

## 3. Xometry CNC: published rules

Sources (read 2026-11-15): [CNC machining service](https://www.xometry.com/capabilities/cnc-machining-service/),
[CNC milling service](https://www.xometry.com/capabilities/cnc-machining-service/cnc-milling-service/),
[manufacturing standards](https://www.xometry.com/manufacturing-standards/),
[aluminium](https://www.xometry.com/capabilities/cnc-machining-service/cnc-aluminum/),
[inspection options](https://www.xometry.com/resources/industry-design-tips/inspection-options/),
[thin walls](https://www.xometry.com/resources/machining/cnc-machining-thin-walls/),
[internal corner radii](https://www.xometry.com/resources/machining/cnc-machining-optimizing-internal-corner-radii/),
[cost reduction](https://www.xometry.com/resources/machining/cnc-machining-cost-reduction/).
The [CNC design guide](https://www.xometry.com/resources/design-guides/design-guide-cnc-machining/) is a PDF
behind a contact form and was **not read**.

| Rule | Figure | The page's words | Checked by |
|---|---|---|---|
| Standard tolerance, size and location | +/-0.127 mm (metals), +/-0.254 mm (plastics) | "For features of size (Length, width, height, diameter) and location (position, concentricity, symmetry) +/- .005" (metals) or +/- .010 (plastics and composites) following ISO 2768 unless otherwise specified." (no ISO 2768 class is named) | tolerance simulation |
| Standard form tolerance (flatness, parallelism, perpendicularity ...) | 0.127 mm to 305 mm; 0.254 to 610; 0.41 to 914; 0.79 to 1524; 1.6 beyond; angularity 0.5 deg to 610 mm | "0 to 12" .005" 0.5°; 12" to 24" .010" 0.5°; 24" - 36" 1/64"; 36" - 60" 1/32"; Over 60" 1/16"" | tolerance simulation (`flat`), `shop_notes` |
| Tightest | under +/-0.025 mm, by drawing | "tight tolerances, including sub +/- 0.001" tolerances, per your drawing specifications and GD&T callouts" | part-level `tolerance` override |
| **Edge break** | broken by default, size **not published** | "Sharp edges will be broken and deburred by default. Critical edges that must be left sharp should be noted and specified on a print." Workmanship: "All exposed edges will be free of burrs, sharp edges, and metal slivers." | `shop_notes.edge_break` |
| Edge break, contradiction | - | the "Standard (As-Milled)" finish on the CNC page reads "Machined parts are left with visible tool marks and potentially sharp edges and burrs, which can be removed upon request." State the break on the drawing. | - |
| Surface finish | 3.2 um Ra | "As machined surface finish is 125 Ra or better. Machine tool marks may leave a swirl-like pattern." | `shop_notes` |
| Minimum feature | 0.5 mm | "0.020" (0.50 mm). This may vary depending on part geometry and chosen material." | `shop_feature_below_minimum` |
| Minimum wall | 0.794 mm | "As a general rule of thumb, CNC machined walls should have a minimum width of 1/32" (0.794mm)." | `cnc.wall_recommended_metal_mm` = 0.794 |
| Inside corners | depth at most 3 x tool diameter; add 0.5 to 1.3 mm to the radius | "use an inside corner radius that has a L:D ratio (length to diameter) of 3:1 or less"; "at least 0.02" - 0.05" added to internal corner radii" | `cnc.corner_depth_ratio` = 3 |
| Thread depth | 3 x diameter | "you don't need to thread a hole to more than 3X the hole's diameter" | `cnc.thread_depth_ratio` = 3 |
| Threads offered | any standard size | "Xometry can accommodate any standard thread size ... custom threads ... manual quote review"; "Anything smaller than a 2-56 requires hand tapping" | - |
| **Thread call-out** | every thread must be named | "Tapped holes not explicitly called out as Features on the quoted CAD model may be machined to the diameters specified in that model." | `shop_thread_callout` (warning) |
| Hole depth to diameter, pocket depth | **not read** (gated guide) | - | mechloop's general rules (Hubs) stay |
| Maximum part | milled 2032 x 1219 x 610 mm; 3-axis to 1524 mm, 4-axis to 914 mm, 5-axis to 660 mm | "Milled parts up to 80" x 48" x 24""; "5 Axis Machining up to 26"; 4 Axis Machining up to 36"; 3 Axis Machining up to 60"" | `shop_part_too_big`, `cnc.part_max_mm` = 1524 |
| Materials | Aluminum 6061 (properties "based upon 1/2" Aluminum 6061-T6": yield 276 MPa), 5052, 2024, 6063, 7050, 7075, **MIC-6** (yield 105 MPa, "cast specifically for ... fixture plates ... no internal stresses"); Steel 1018, 1215, 4130, 4140; Stainless 18-8, 303, 316; Delrin (acetal) | "If you do not see the material stock you are looking for, please choose "Custom"" (ATP-5 is not listed) | `shop_material_not_listed` (warning) |
| Stock plate thicknesses | **not published**; MIC-6 thickness list in the profile is **recalled** (inch plate: 6.35, 9.53, 12.7, 15.9, 19.05, 25.4 mm; SendCutSend's list agrees for the first three) | - | `non_stock_thickness` (warning) |
| Finishes | as-milled, bead blast, tumbled, anodize II / III, chem film, powder coat, zinc | "Chem Film ... Provides corrosion resistance and good conductivity properties ... about 0.00001"-0.00004""; "No surface treatments ... will be applied unless you have paid for them" | - |
| Inspection | standard, included | "If no dimensional print is provided with a part, QC measures to Xometry's Manufacturing Standards on dimensions they deem critical, such as overall size, holes, and depths. If a dimensional print is provided, QC will verify up to 20 dimensions they deem critical. Documentation will not be shipped with your parts." | - |
| Inspection, paid | formal report, CMM report, FAIR (AS9102), source, custom | each: "A customer-supplied dimensional print is required" | - |
| What needs a drawing | anything tighter than +/-0.127 mm; flatness under 0.127 mm; an edge that must stay sharp or have a stated break; threads (or name them as features in the quote); any inspection report | above | - |

Not found: the size of the default edge break; stock thicknesses; which ISO 2768 class; hole and pocket depth
rules; a tolerance between features cut in one set-up; prices.

## 4. Tolerance tables used

One standard deviation, mm (`scale` is a fraction). Fields a shop does not publish keep the class value.

| Process / shop | pos | pattern | scale | hole_sd | flat | Basis |
|---|---|---|---|---|---|---|
| sheet, class | 0.08 | 0.04 | 0.0005 | 0.04 | 0.10 | `tolerance/process.py` |
| sheet, SendCutSend, part up to 305 mm | **0.0635** | 0.04 | 0.0005 | **0.0635** | 0.10 | half of +/-0.127 mm |
| sheet, SendCutSend, part over 305 mm | **0.127** | 0.04 | 0.0005 | **0.0635** | 0.10 | half of +/-0.254 mm (front_plate 314 mm, electronics_tray 340 mm) |
| machined, class | 0.04 | 0.02 | 0.0002 | 0.02 | 0.02 | `tolerance/process.py` |
| machined, Xometry, no drawing, part up to 305 mm | **0.0635** | 0.02 | 0.0002 | **0.0635** | **0.0635** | half of +/-0.127 mm; half of the 0.127 mm form tolerance |
| bent sheet, SendCutSend | angle 0.5 deg, bend line 0.19 mm | | | | | half of +/-1 deg and +/-0.38 mm: equal to the class values, which were recalled and are now confirmed |

SendCutSend is tighter than the class value on feature position and looser on hole size. Xometry without a
drawing is looser than the class value on everything it states: the class figures describe what a mill does,
Xometry's describe what it guarantees unless told otherwise.

## 5. printer_v8 under these shops

Run on a scratch copy (the design file is not edited): `designs/printer_v8.py` plus
`assign(d, sheet="sendcutsend", machined="xometry")`, then
`verify <copy> --only manufacture tolerance --no-render`.

Result: **manufacture FAIL, 7 errors, 24 warnings** (generic: pass, 0 errors, 7 warnings).
**tolerance pass, 0 errors, 0 warnings** (as generic).

### 5.1 Failures: thickness not stocked (7 parts)

| Part | Material | Drawn | Nearest stock | Difference | Consequence |
|---|---|---|---|---|---|
| back_plate | 6061 | 5.0 mm | 4.75 mm (.187") | -0.25 | rail carriage and bed arm faces move 0.25 mm; M3x8 into the MGN12H blocks gain 0.25 mm of engagement |
| electronics_tray | 6061 | 3.0 mm | 3.175 mm (.125") | +0.175 | PSU and board stand 0.18 mm higher; nothing critical |
| inlet_panel | 6061 | 3.0 mm | 3.175 mm | +0.175 | the power entry module's snap-in or screw panel range must cover 3.18 mm; its screw-hole web is unaffected |
| y_motor_mount, y_motor_mount_l | steel | 2.0 mm | 1.88 mm (.074", 14 ga) | -0.12 | 17 % less bending stiffness (t cubed); motor face moves 0.12 mm; next up is 2.64 mm (+0.64, 2.3 x stiffer) |
| y_idler_mount, y_idler_mount_l | steel | 2.0 mm | 1.88 mm | -0.12 | as above: the Y belt plane share already sits near its limit, re-run after choosing |

The other 13 sheet parts map to stock within 0.05 mm: 3.0 mm steel is .119" (3.023 mm, +0.023) and 1.5 mm
steel is .059" (1.499 mm). The tolerance run uses the drawn thickness; the gauge differences above are
systematic offsets that are **not** in the tolerance numbers of section 5.5 until the parts are redrawn.

### 5.2 Machined parts (Xometry)

| Part | Result | Notes |
|---|---|---|
| bed_plate (MIC-6, 8 mm, 236.5 mm long) | warning `non_stock_thickness` | 8 mm is not a MIC-6 thickness (list recalled; SendCutSend stocks MIC-6 at 6.35, 9.53, 12.7 mm only, and the maker's brochure speaks of 1/4 to 5/8 in and 3/4 in plate). From 9.53 mm both faces are machined: the cast plate's as-supplied flatness is lost and the estimate becomes $209 instead of a profile-and-holes job. Without a drawing the flatness guarantee is 0.127 mm. Use 6.35 or 9.53 mm and keep the stock faces, or put a flatness on a drawing. Material is listed ("Aluminum MIC-6"); ATP-5 would be a manual quote. |
| tool_plate (6061, 8 mm, 62 mm long) | passes | Xometry publishes no stock list; 8 mm plate is ordinary metric stock (5/16" is 7.94 mm at a US shop: state "8.0, stock faces acceptable" or tolerance it). Minimum wall 1.01 mm against Xometry's 0.794 mm. Two M3x50 screws are declared as threading into it; the verifier finds no thread in its material, so confirm whether those holes are tapped and, if so, call the threads out. Edges are broken by default: note which, if any, must stay sharp. |

### 5.3 The seven generic manufacture warnings

| Generic warning | Under the shop profiles |
|---|---|
| back_plate: 12 holes of 3.4 mm in 5 mm plate (`hole_smaller_than_thickness`) | **stays a warning, not a shop limit**: SendCutSend's minimum is 2.38 mm in 4.75 mm stock; 3.4 mm cuts. Its own 6061 page still says "Design holes no smaller than material thickness" for best results: expect taper, ream or drill if the fit matters (these are M3 clearance holes: no action). |
| electronics_tray: 2 holes of 2.7 mm in 3 mm sheet | stays a warning; shop minimum is 1.59 mm in 3.18 mm stock. If these are M2.5 clearance holes powder coat would close them to about 2.45 mm: leave the tray uncoated or open them. |
| y_plate_left / y_plate_right: 2.05 mm web between holes | **stays a warning; passes the shop minimum** of 1.51 mm (0.5 x 3.02) with 0.54 mm in hand, below the 3 to 4.5 mm the shop prefers. In aluminium at 4.75 mm (section 6.3) the minimum becomes 2.38 mm and **2.05 mm would fail**: open the spacing to 2.4 mm or more if the gauge changes. |
| inlet_panel: 2.75 mm between the inlet cut-out and its screw holes | stays a warning; passes the shop minimum of 1.59 mm. It is the bought module's own pattern. |
| z_drive_mount, z_pedestal_fr (`load_across_layers`) | printed parts: no supplier, unchanged (one of the two is now reported by the concurrent checker work as compression, not flagged). |

New warnings: `bare_steel_no_finish` on all 17 steel parts (section 6.3), `non_stock_thickness` on bed_plate.

### 5.4 Services per part

Stock, deburring, tumbling, coating and tapping as SendCutSend lists them for each part's material, nearest
stock thickness and flat size. No part has a countersink or a bend. No sheet part carries a thread today:
every screw through a sheet part ends in a T-nut, a bought part's own thread, or a loose nut.

| Part | Stock mm | Flat size mm | Least web / shop min mm | Deburr | Tumble | Powder coat | Tap range | Screws ending in a loose nut (could be tapped or a PEM nut) |
|---|---|---|---|---|---|---|---|---|
| back_plate (6061) | 4.75 | 214 x 97 | 5.2 / 2.38 | yes | no (over 102 x 178) | yes (anodize yes) | M3-M10 | 4 x M3, 3 x M5 |
| front_plate (steel) | 3.02 | 314 x 81 | 3.3 / 1.51 | yes | no (too long) | yes | M2-M8 | 8 x M3, 2 x M5 |
| bed_post_tab_0..3 (steel) | 3.02 | 43.5 x 38 | 3.75 / 1.51 | **no** (under 25.4 x 76.2) | yes | **no** (under 25.4 x 76.2) | M2-M8 | the M5x90 bed posts (jam nuts: keep) |
| bed_tie (steel) | 1.50 | 54 x 46.5 | 5.3 / 0.75 | **no** | **no** (under 3.02 mm) | **no** | M2-M3 | 2 x M3, 1 x M5 (M5 not offered at this gauge) |
| y_plate_left (steel) | 3.02 | 73.5 x 68 | 2.05 / 1.51 | **no** (2.7 mm short of 76.2) | yes | **no** (2.7 mm short) | M2-M8 | 2 x M3 |
| y_plate_right (steel) | 3.02 | 70.5 x 43.5 | 2.05 / 1.51 | **no** | yes | **no** | M2-M8 | - |
| x_rail_stop_left / right (steel) | 3.02 | 26.5 x 20 | 3.25 / 1.51 | **no** | **no** (under 12.7 x 38.1) | **no** | (part under 25.4 x 38.1: no tapping) | - |
| x_motor_mount (steel) | 3.02 | 64 x 50 | 5.25 / 1.51 | **no** | yes | **no** | M2-M8 | - |
| x_idler_mount (steel) | 3.02 | 53 x 50 | 5.25 / 1.51 | **no** | yes | **no** | M2-M8 | 1 x M5, 1 x M3 |
| y_motor_mount, _l (steel) | 1.88 | 106.5 x 59 | 3.7 / 0.94 | yes | no (under 3.02 mm) | yes | M2-M6 | 1 x M3 each |
| y_idler_mount, _l (steel) | 1.88 | 78 x 39 | 4.75 / 0.94 | yes | no | yes | M2-M6 | 1 x M5 each |
| y_endstop_mount (steel) | 3.02 | 54.5 x 25 | 3.0 / 1.51 | **no** | yes | **no** | (part 0.4 mm under 25.4 wide: no tapping) | 2 x M3 |
| electronics_tray (6061) | 3.18 | 340 x 223 | 4.96 / 1.59 | yes | no (too big) | yes (anodize yes) | M2-M10 | 7 x M3, 2 x M2.5 |
| inlet_panel (6061) | 3.18 | 94 x 70 | 2.75 / 1.59 | yes | yes | yes (anodize yes) | M2-M10 | 2 x M3 |

Reading it for the owner's sharp-edge concern:

- **Deburring is not an edge break.** It brushes the two faces; SendCutSend says "Some edges will be sharp".
  Tumbling is the service that rounds edges, and only parts up to 102 x 178 mm and 3.02 mm or thicker qualify.
- Tumble (edges rounded): bed_post_tab x 4, y_plate_left, y_plate_right, x_motor_mount, x_idler_mount,
  y_endstop_mount, inlet_panel: **10 parts**.
- Deburr only (faces cleaned, edges may stay sharp: break them by hand): back_plate, front_plate, electronics_tray,
  y_motor_mount x 2, y_idler_mount x 2: **7 parts**. The tray and both plates are the largest, most-handled
  parts of the machine.
- Neither service: bed_tie, x_rail_stop x 2: **3 parts**, hand-finish.
- Tumbling cannot be combined with a coating without a custom quote, and the parts that most need a coating
  (small 3 mm steel) are too small to be coated at all (section 6.3).

Tapping or PEM nuts instead of loose nuts: about 40 loose M3 / M5 nuts sit behind sheet parts. Every one in
3.02 mm steel or 3.18 / 4.75 mm aluminium is inside the tapping range (M3 in 3.02 mm steel: 6 threads; M5 in
4.75 mm 6061: 5.9 threads; M5 in 3.02 mm steel: 3.8 threads, marginal, use a PEM nut). Good candidates, where
the nut is hard to reach at assembly: front_plate 8 x M3, electronics_tray 7 x M3 (board and relay mounts),
back_plate 4 x M3, inlet_panel 2 x M3. Model the hole at the shop's tap size (M3: 2.60 mm, M5: 4.32 mm) and
choose the tap in the app; which side the nut sits on was not resolved here, so confirm the screw enters from
the far side of the tapped part. No countersinks are drawn; back_plate, electronics_tray (3.18 mm and up, part
at least 25.4 x 101.6 mm) could take 90-degree M3 countersinks if a flush head is ever wanted.

Bending (v8 has no bends; opportunities only):

- y_motor_mount and y_idler_mount (1.88 mm steel) would gain far more stiffness from one bent flange than
  from a thicker gauge: SendCutSend bends .074" steel at 1.6 mm radius, minimum flange 8.1 mm.
- bed_post_tab and the x / y motor mounts are flat tabs bolted to brackets or extrusion faces; an L in 3.02 mm
  steel (radius 1.6 mm, flange at least 11.8 mm) could replace a tab plus a corner bracket. A bent part also
  clears the 25.4 x 76.2 mm coating minimum more easily.
- electronics_tray (340 x 223 mm, 6061) cannot be bent at SendCutSend; in 5052-H32 3.18 mm (radius 3.18 mm,
  flange at least 12.1 mm) two stiffening lips would let it drop to 2.03 or 2.54 mm.
- Costs of bending: +/-1 degree and +/-0.38 mm per bend enter the stack-up (the tolerance verifier models
  both), and holes within half a die width of the bend distort.

### 5.5 Tolerance results: generic class values against supplier tolerances

3000 builds, same seed. First column as committed (class values), second with SendCutSend and Xometry tables.

| Result | Class values | Supplier tolerances |
|---|---|---|
| Bed levelling needed (99 %) | 0.79 mm of 4.0 available | 0.82 mm |
| Bed out of level as built (99 %) | 1.58 mm | 1.63 mm |
| Z offset needed (99 %) | 0.98 mm of 1.65 available | 1.00 mm |
| Nozzle-to-bed gap error (99 %) | 0.98 mm | 1.00 mm |
| First layer reachable as built | 23.2 % | 22.2 % |
| Bed reaches nozzle with overtravel | 100 % | 100 % |
| Z rails, parallelism error over travel (99 %) | 1.016 mm (set at assembly) | 1.022 mm |
| Y rails, parallelism error over travel (99 %) | 1.396 mm (set at assembly) | 1.393 mm |
| X belt within 1 mm of plane | 99.5 % (limit 95 %), 1.09 mm at 99 % | 99.5 %, 1.12 mm |
| Y belt (right / left) within 1 mm | 97.9 % / 98.2 % | 97.8 % / 98.3 % |
| Lead screw nut misalignment, front-left (99 %) | 1.82 mm of 2.2 float | 1.86 mm |
| Closing clearances: pairs examined | 25, none closing | 25, none closing |
| Largest gap standard deviation | 0.223 mm | 0.234 mm |
| Smallest 0.15-percentile gap | 0.404 mm | 0.481 mm |
| Screw patterns that start | all 170 groups | all 170 groups |
| Findings | 0 errors, 0 warnings | 0 errors, 0 warnings |

The design is insensitive to the change: every figure moves by 5 % or less and none crosses a limit. The
stack-up is dominated by saw-cut extrusion, printed parts and joints, not by cut or machined part accuracy;
the declared adjustments (bed nuts 4 mm, probe offset 1.65 mm, rails on sliding T-nuts, floating nut) still
cover it. Xometry's looser no-drawing guarantee shows up as `bed_magnet / bed_plate` and
`tool_plate / x_belt_block_nut` entering the top contributors. The only tightening worth buying is a flatness
call-out on the bed (section 7.2); position tolerances tighter than standard buy nothing here.

## 6. Material review

The owner's expectation: 6061 aluminium for CNC parts, aluminium or Delrin for 2D cut parts. v8 today:
2 machined parts (6061, MIC-6), 3 sheet parts in 6061, **17 sheet parts in an unnamed "steel"** with no finish.

### 6.1 Is each material, temper and thickness a stocked item?

| mechloop material | SendCutSend (cut) | Xometry (CNC) |
|---|---|---|
| `al6061` | "6061 T6 Aluminum", 12 thicknesses 1.02 to 19.05 mm; not bent | "Aluminum 6061", properties for 6061-T6 |
| `al5052` | "5052 H32 Aluminum", 11 thicknesses 1.02 to 12.7 mm; the bendable aluminium | "Aluminum 5052" |
| `steel` | "Mild Steel": **A1008 cold rolled** to 3.43 mm, **A36/A1018 HRP&O** from 4.75 mm; 12 thicknesses | "Steel 1018" (not the same grade) |
| `stainless304` | "304 Stainless Steel", 10 thicknesses 0.76 to 12.7 mm | "Stainless Steel 18-8", 303, 316 |
| `al_mic6` | "MIC-6 Cast Aluminum", 6.35 / 9.53 / 12.7 mm, laser cut, tap and countersink | "Aluminum MIC-6"; thicknesses not published |
| `al_atp5` | not offered | not listed ("Custom", manual review) |
| Delrin (not in `MATERIALS`) | "Delrin 150": 3.18 mm CO2 laser (+/-0.23 mm), 4.75 and 6.86 mm CNC router (+/-0.127 mm, tabs, 1.6 mm inside corners); tap and countersink only | "Delrin (Acetal)", +/-0.254 mm |

Every v8 thickness against the nearest stocked gauge is in section 5.1: 13 parts within 0.05 mm, 7 parts off
by 0.12 to 0.25 mm, the bed plate off by 1.5 mm either way.

### 6.2 `mechloop/model.py` MATERIALS against the suppliers' figures

Not edited here (another agent is in mechloop); proposed catalogue changes:

| Entry | In the model (density, E, yield) | Supplier / grade | Change proposed |
|---|---|---|---|
| `al6061` | 2700, 68.9 GPa, 276 MPa | SendCutSend: "~40,000 psi" yield (276 MPa), 0.0975 lb/in3 (2699); Xometry: 276 MPa, 2.7 | none; rename or alias `al6061_t6` so the temper is stated |
| `al5052` | 2680, 70.3 GPa, 193 MPa | SendCutSend H32: "~28,000 psi" (193 MPa) | none; alias `al5052_h32` |
| `steel` | 7850, 200 GPa, **250 MPa** | 250 MPa is A36's minimum, but A36 is only what SendCutSend supplies from 4.75 mm. All 17 v8 steel parts are 1.5 to 3 mm, which is **A1008 cold rolled**; SendCutSend gives mild steel as "Yield strength: 25-50 ksi" (172 to 345 MPa) | split: `steel_a1008` (cold rolled sheet, yield 172 MPa = the published lower bound) and `steel_a36` (250 MPa, 4.75 mm and up); keep `steel` as a deprecated alias of the weaker one. FEA margins on the thin steel parts are overstated by up to 45 % today |
| `stainless304` | 8000, 193 GPa, **215 MPa** | SendCutSend: "~30 ksi (205 MPa)" | 205 MPa |
| `al_mic6` | **2800**, 71 GPa, 105 MPa | Xometry: yield 105 MPa, density **2.7** ("generalized values") | density unresolved: the model's 2800 is recalled (0.101 lb/in3), Xometry's 2.7 is generalised; 3.6 % on the bed's 1.16 kg. Confirm from the plate maker's sheet |
| Delrin | absent | SendCutSend: "will still deform or degrade at prolonged temperatures above ~185-200°F" (85 to 93 C); no modulus published | add `pom_h` only when a part uses it; modulus about 3 GPa and density about 1.41 g/cm3 are **recalled**, not read |

No finish, grade or temper is recorded on any part today. Proposed: a `finish` key in `meta` (implemented as
read-only input to the shop checks here), and grade-specific material names as above.

### 6.3 Is each steel part the sane choice?

Bare mild steel rusts, and SendCutSend says so twice ("it will oxidize (rust) if left unprotected"; deburred
mild steel "is more prone to rusting"). What it offers for v8's steel parts:

| Finish | Offered for | Thickness added | v8 steel parts that qualify |
|---|---|---|---|
| Powder coat | mild steel from 1.22 mm, part at least 25.4 x 76.2 mm | 0.05 to 0.13 mm per side; insulates | **5 of 17**: front_plate, y_motor_mount x 2, y_idler_mount x 2 |
| Zinc or nickel plating | mild steel **from 4.75 mm only** | 0.008 / 0.005 mm per side; conductive | **none** (all are 1.5 to 3 mm) |
| None available at SendCutSend | - | - | **12 of 17**: bed_post_tab x 4, bed_tie, y_plate x 2, x_rail_stop x 2, x_motor_mount, x_idler_mount, y_endstop_mount (too small, and too thin to plate) |

So twelve steel parts would arrive bare with no coating the supplier can apply. Options, in order of sanity:

1. **Aluminium instead** (the owner's expectation). No finish needed, earth-bonds through bare contact,
   stocked, lighter.
2. **304 stainless** at 3.18 mm where steel's stiffness or wear is wanted (same modulus, no coating, all
   services but countersink; yield 205 MPa).
3. Keep mild steel and finish at home (cold-blue, oil, or paint) and say so: `meta={"finish": "oil"}`.

The moving parts (ride on Y; 261 g of steel in a Y moving mass of 1.34 kg):

| Option for the 3 mm steel plates on Y | Bending stiffness (E t^3) | Bending strength (yield x t^2) | Mass | Y moving mass |
|---|---|---|---|---|
| A1008 steel 3.02 mm (today) | 1.00 | 1.00 (at 250 MPa; 0.69 at 172) | 1.00 = 261 g | 1.34 kg |
| 6061-T6 3.18 mm | 0.40 | 1.22 | 0.36 = 94 g | 1.17 kg (-12 %) |
| **6061-T6 4.75 mm** | **1.34** | **2.72** | **0.54 = 141 g** | **1.22 kg (-9 %)** |
| 6061-T6 6.35 mm | 3.19 | 4.87 | 0.72 = 188 g | 1.27 kg (-5 %) |
| 304 stainless 3.18 mm | 1.12 | 0.90 | 1.07 = 280 g | 1.36 kg (+1 %) |

6061-T6 at 4.75 mm is stiffer, nearly three times stronger in bending, 120 g lighter on Y, needs no finish,
and at that gauge every part gains tapping from M3 and tumbling. What it costs: 1.73 mm more thickness at each
plate (belt plane, rail-stop and endstop positions, M3x6 into the MGN12H blocks become M3x8), the shop's web
minimum rises to 2.38 mm (the 2.05 mm web on the Y plates must open), and M3 threads in aluminium wear if
re-assembled often. Price was not compared: no quote was requested.

Where steel is right:

- **bed_tie** (1.5 mm): a thin flexure. Spring behaviour and fatigue favour steel; aluminium that thin is
  weaker and fatigues. Keep it, in 304 stainless 1.52 mm (no coating, stocked) or oiled A1008.
- **front_plate** if it is the surface the M12 inductive probe or a magnet works against: check before
  changing (474 g in steel, about 256 g in 4.75 mm 6061; it rides on Z, where mass matters little).
- **bed_post_tab**: carries the M5 bed posts with jam nuts; steel resists the nut faces better, but 4.75 mm
  6061 with washers is sufficient. Either.

Where Delrin would be sane: low-load, low-friction, electrically insulating, room-temperature parts such as
a bumper, a cable guide, a switch carrier or a wear strip. In v8 the only candidates are y_endstop_mount
(switch position is set on a slot, so +/-0.23 mm laser tolerance is harmless; 54.5 x 25 mm is 0.4 mm under the
25.4 mm minimum width) and the x_rail_stops as soft stops (26.5 x 20 mm: under the 25.4 x 50.8 mm minimum).
Where it would not be: any plate that locates a rail, motor, idler or the bed (about a twentieth of
aluminium's stiffness, and it creeps under bolt preload: use metal sleeves or washers if it is ever clamped);
anything near the bed or hotend (SendCutSend: degrades above about 85 to 93 C); the mains inlet_panel and the
electronics_tray (earth continuity and heat spreading want metal; acetal burns).

### 6.4 Rules for a material check (data: `material_rules` in each profile)

| Id | Rule | Severity | Status |
|---|---|---|---|
| `stocked_thickness` | a cut part's thickness is one the declared shop stocks in that material, within 0.05 mm | error | implemented (`non_stock_thickness`) |
| `material_offered` | the material is in the declared shop's chart for that process | error (cut), warning (CNC: manual quote) | implemented (`shop_material_not_offered`, `shop_material_not_listed`) |
| `no_bend_6061` | a bent sheet part is 5052-H32, mild steel or 304; never 6061-T6, cast plate or Delrin | error | implemented (`material_not_bent`, existing) |
| `bare_carbon_steel` | carbon steel declares a finish (`meta["finish"]`), `bare` or `oil` being explicit choices | warning | implemented (`bare_steel_no_finish`) |
| `zinc_min_thickness`, `anodize_aluminium_only`, size limits | a declared finish is one the shop lists for that material, thickness and part size | error | implemented (`shop_finish_not_offered`) |
| `cast_plate_stock` | cast tooling plate is used at a thickness it is made in, so its faces stay as supplied | warning | implemented for Xometry (`non_stock_thickness`; thickness list recalled) |
| `threads_called_out` | a machined part with threads names them in the quote or on a drawing | warning | implemented (`shop_thread_callout`) |
| `delrin_process` | Delrin 3.18 mm is laser cut at +/-0.23 mm; thicker is routed with 1.6 mm inside corners and tabs; no deburr, no coating | info | data only: needs a `delrin` material and a per-material cut method in `dfm_sheet.py` |
| `cast_plate_for_flat` | a plate declared flatness-critical (a print bed) is cast tooling plate, not rolled 6061 | info | data only: needs a way to declare a flatness-critical face |
| `coating_insulates` | a part in a protective-earth path has no insulating finish, or declares a bare contact | info | data only: belongs to the electrical verifier |
| proposed | every custom metal part names a grade and temper (`al6061_t6`, `steel_a1008`), not a family | warning | needs the `MATERIALS` split of section 6.2 |
| proposed | a tapped sheet hole is at least (tap hole / 2 + the shop's tap hole-to-edge) from any cut edge | error | needs the per-thickness value SendCutSend loads by script |

## 7. Ordering checklists

### 7.1 SendCutSend (20 flat parts)

- [ ] Redraw to stock first: 5.0 to 4.75 mm, 3.0 to 3.175 mm (6061), 2.0 to 1.88 or 2.64 mm (steel); or change
      material per section 6.3 and re-run `verify`.
- [ ] Files: the DXFs from `out/printer_v8/dxf/`, one part per file, millimetres, 1:1. Check each upload
      preview shows the size in section 5.4; set the unit to mm in the quote.
- [ ] No dimensions, text, title block or construction geometry in the file; one layer; closed contours.
- [ ] Material call-out per part, by the shop's name: "6061 T6 Aluminum .187"" / ".125""; "Mild Steel .119""
      (A1008 cold rolled), ".074"", ".059""; quantity: bed_post_tab x 4, mirrored left / right parts as
      separate files.
- [ ] Mirrored parts (`_l`, left / right): flat and uncoated they are interchangeable by flipping only if
      nothing is countersunk or tapped from one side; otherwise upload each hand.
- [ ] Services to tick: **Tumbling** on the 10 parts that qualify (section 5.4) for rounded edges; **Deburring**
      on the 7 that only qualify for that, then break their edges by hand (file or 240-grit: deburring leaves
      "some edges ... sharp"); nothing is available for bed_tie and the x_rail_stops.
- [ ] Tapping (optional): select the holes and the tap in the app; model them at 2.60 mm (M3) or 4.32 mm (M5).
- [ ] Finish on steel: powder coat is available on 5 parts only; not together with tumbling without a custom
      quote. If coated: holes shrink by 0.1 to 0.25 mm on diameter, chase any tapped holes, and bare the
      earth-bond contact.
- [ ] Leave electronics_tray and inlet_panel **uncoated** (or anodize and fit the earth bond with a serrated
      washer on a scraped spot): anodize is non-conductive.
- [ ] Order note is not read for dimensions ("We don't adjust based on written dimensions"); anything that
      matters must be in the geometry or the selected service.
- [ ] On receipt: expect tab witness marks 0.4 to 0.8 mm wide on edges, light dross on the 4.75 mm aluminium,
      oil on tapped parts; check flatness of electronics_tray and front_plate (no flatness is guaranteed).

### 7.2 Xometry or equivalent CNC bureau (2 parts)

- [ ] Files: STEP of each part plus a PDF drawing. Without a drawing everything is +/-0.127 mm and flatness
      0.127 mm, and inspection covers only what QC "deem critical".
- [ ] Material call-out: tool_plate "Aluminum 6061-T6, 8.0 mm plate, stock faces acceptable"; bed_plate
      "Aluminum MIC-6 cast tooling plate, stock thickness (6.35 or 9.53 mm), **do not machine the two faces**".
- [ ] Drawing notes: "Break all edges 0.2 to 0.5 mm" (the default break has no published size, and the
      as-milled finish text allows sharp edges); name any edge that must stay sharp.
- [ ] Threads: list every tapped hole (size, depth, through or blind) as a thread feature in the quote and on
      the drawing; an uncalled hole "may be machined to the diameters specified in that model".
- [ ] bed_plate drawing: flatness of the top face (the stock's own guarantee is 0.381 mm for 6.35 to 15.9 mm MIC-6 plate per the
      maker's brochure recorded in `mechloop/parts/vendor/cast_tooling_plate.json`; a tighter figure must be asked for), hole positions at the
      standard +/-0.127 mm.
- [ ] Finish: "As-milled, no coating" (bare aluminium bonds to earth; nothing is applied unless ordered). If
      a coating is wanted on the tool plate, chem film is the conductive one.
- [ ] Inspection: standard is enough; with the drawing, up to 20 dimensions are verified. No report is shipped
      unless a formal or CMM inspection is bought.
- [ ] Alternative worth pricing: SendCutSend laser-cuts MIC-6 at 6.35 / 9.53 / 12.7 mm with tapping and
      countersinking at +/-0.127 mm. If bed_plate is redrawn as a plain through-cut profile (today it has
      features that are not through cuts: `could_be_cut_2d` is false), it can go on the sheet order.

## 8. What v8.1 should change for these suppliers

1. Draw every sheet part at a stocked gauge: back_plate 4.75 mm; electronics_tray and inlet_panel 3.175 mm;
   Y motor and idler mounts 1.88 mm with a bent stiffening flange, or 2.64 mm flat. Re-check screw lengths and
   the Y belt plane.
2. Replace generic "steel" with named materials. Moving plates (y_plate x 2, x_motor_mount, x_idler_mount,
   x_rail_stop x 2) and the small static tabs: 6061-T6 at 4.75 mm; bed_tie: 304 stainless 1.52 mm; front_plate:
   6061 4.75 mm unless the probe needs steel. Then no part needs a coating the supplier cannot apply.
3. Open the 2.05 mm web on the Y plates to at least 2.4 mm (shop minimum at 4.75 mm), preferably 4.75 mm.
4. Grow the parts that miss a service by a few millimetres: y_plate_left to 76.2 mm long (deburr and coat),
   y_endstop_mount to 25.4 mm wide (tapping), x_rail_stop to 12.7 x 38.1 mm (tumbling) or make it a feature
   of the Y plate.
5. Bed plate: 6.35 or 9.53 mm MIC-6, faces as supplied, flatness on a drawing; decide Xometry against
   SendCutSend's cut MIC-6.
6. Declare a finish on every metal part (`meta["finish"]`) and adopt `assign(d, sheet="sendcutsend",
   machined="xometry")` in the design so these checks run on every verify.
7. Replace hard-to-reach loose nuts with tapped holes or PEM nuts on front_plate, electronics_tray,
   back_plate and inlet_panel.
8. Tumble everything that fits 102 x 178 mm; plan a hand edge-break for the seven larger parts and say so in
   the assembly notes.
