PRACTICAL DESIGN REFERENCES
Collected 15 November 2026 for the v6 toolhead reference folder.

START HERE
Numbers match the 19 requested topics. Page numbers below are PDF pages, starting at 1, unless marked "printed". These are reference documents, not approved design calculations. SOURCES.txt records each file's URL, byte count and SHA-256. MISSING.txt lists unresolved fields.

Manufacturer/distributor copies are used where the standards themselves are not freely available. A maker's table is not the licensed standard. Do not silently substitute a different material, screw size, belt generation or lead-screw variant. Original PDFs are unchanged. Two files are explicitly labeled web-source snapshots/excerpts: items 16 and 17.

01. TORQUE AND PRELOAD
01_Bossard_preload_torque.pdf
- Page 2 (printed 61) begins the metric preload/torque tables, including the requested small diameters and classes 8.8, 10.9 and 12.9. Friction coefficients are tabulated.
- Read the introduction and footnotes: these are maximum values based on approximately 90% utilization of yield strength, not a ready-made safety-factored joint specification.
- UNIT TRAP: the smallest screw torque rows use Ncm; larger rows use Nm. Friction, finish and lubrication must match the selected column.

02. ISO 273 CLEARANCE HOLES
02_MetricMCC_ISO273_clearance.pdf
- Distributor's table reproduces fine, medium and coarse clearance-hole series. Image-based table, so text search may not work.

03. ISO 4762 THREAD LENGTHS AND LENGTH SELECTION
03_Westfield_socket_head_cap_screw.pdf
03_Aramfix_ISO4762_dimensions.pdf
03_Lederer_ISO4762.pdf
- Westfield gives the diameter dimensions and b values, including M3 and M5.
- Aramfix page 2 gives the length-by-diameter matrix, full-thread entries and ls/lg. Important source caveat: although the document is headed ISO 4762, this matrix is labeled "according to DIN 912". Do not treat it as an independently verified current ISO 4762 length schedule.
- Lederer includes a maker's availability matrix. Catalogue availability is not the same as the standard's complete permitted length range.
- A definitive current ISO 4762 standard length-range matrix remains unverified.

04. SURFACE PRESSURE UNDER HEADS
04_Bossard_surface_pressure.pdf
- Page 1 (printed 53) reproduces VDI 2230 surface-pressure tables for metals. It shows both the 1986 and 2015 tables; do not mix their values.
- Read the temperature, contact geometry and material conditions. These are not universal bearing-pressure allowables for 3D-printed plastics.
- No validated PETG/ABS printed-plastic surface-pressure table was found in these documents.

05. THREAD ENGAGEMENT
05_Bossard_thread_engagement.pdf
- Material/property-class dependent minimum effective engagement ratios, with the test assumptions stated.
- The underlying trials cover M6-M16, tolerance classes 6g/6H. They do not validate a blanket rule for M2.5 or M3.
- Effective engagement excludes chamfer/runout. Do not turn a table ratio into a universal "1d steel / 2d aluminium" rule.

06. WASHERS
06_RC_ISO_washers.pdf
06_Stephens_ISO7090.pdf
- RC page 1: ISO 7089, including M2.5-M8. RC page 3: ISO 7093 large-series dimensions, starting at M3.
- Stephens: ISO 7090 chamfered normal-series dimensions, starting at M5.
- These lower bounds are not merely missing catalogue stock: Westfield's ISO 7090 summary gives the standard's range as M5-M64. ISO's current ISO 7093-1:2000 scope gives nominal sizes 3-36 mm. Thus M2.5 is outside that ISO 7093-1 scope, and M2.5/M3/M4 are outside ISO 7090's stated range. Use ISO 7089 or a separately specified non-standard part where appropriate.
- Scope sources:
  https://www.westfieldfasteners.co.uk/Standards/Washer-ISO7090-M.html
  https://www.iso.org/fr/standard/13677.html

07. HEAT/ULTRASONIC INSERTS
07_SPIROL_inserts_design_guide.pdf
07_SPIROL_heat_ultrasonic_hole_design.pdf
07_Ruthex_RX_insert_data.pdf
- SPIROL guide page 7 (printed 5): wall/boss design. Page 10 (printed 8): Series 19 hole and insert dimensions for sizes including M3/M5 and short/long lengths.
- SPIROL pages 22-23: pull-out and torque-out test data and conditions. Test plastic is nylon 6 for INS 63/65 and 16% glass-filled nylon 6 for the other listed series; bosses are at least twice insert diameter. Installation method also varies by series.
- Ruthex provides RX dimensions/hole guidance. Do not combine Ruthex geometry with SPIROL strength tables.
- These strength numbers are not ratings for inserts in your printed PETG/ABS parts. Actual polymer, print, boss, insert and installation need validation.

08. SKF 608, AXIAL LOAD, FITS AND SHOULDERS
08_SKF_608_product_data.pdf
08_SKF_deep_groove_general_catalogue.pdf
08_SKF_installation_maintenance.pdf
- Product data pages 1-2: 8 x 22 x 7 mm, basic dynamic/static load ratings and abutment dimensions. It is an SKF-generated sheet hosted by a distributor, not a fresh live rating certificate. Page 2 has an "image NOT FOUND" placeholder for one image; the abutment drawing and dimension table remain readable.
- General catalogue page 14 (printed 299): axial-load discussion. Read the special limitation for small bearings (bore up to approximately 12 mm) and light series. Do not apply the general 0.5 C0 statement without that exception.
- Installation/maintenance pages 56-61: fit selection by load and ring motion; tolerance tables continue afterward. There is no single universally correct shaft/housing fit for every 608 application.
- Basic load ratings are not permissible service loads without life, speed, fits, lubrication, shock and combined-load checks.

09. HIWIN MG/MGN INSTALLATION
09_HIWIN_installation.pdf
09_HIWIN_MG_catalogue.pdf
- Current installation instructions: page 14 MG shoulder/reference geometry; page 15 rail-bolt torque by screw and mounting-base material.
- UNIT TRAP: the rail torque table uses Ncm, not Nm.
- MG catalogue page 8 (printed 99): MGN12/MGN15 rail dimensions and bolt pitch. Pages 12-13 (printed 103-104): mounting surface parallelism/flatness with preload conditions. Page 14 (printed 105): reference shoulders.
- A separate, explicitly identified MG block-to-carriage bolt tightening table was not verified. Do not substitute rail torque for block torque.

10. SET-SCREW HOLDING POWER
10_HoloKrome_metric_handbook.pdf
10_Unbrako_metric_set_screws.pdf
- Holo-Krome page 35 (printed 88): axial holding by metric cup-point screw size, installation torque, shaft-hardness assumptions and approximate scatter. Torsional holding is related to shaft radius.
- Unbrako page 3: metric torsional/axial holding tables by screw and shaft diameter, under the stated shaft conditions.
- No controlled with-flat versus without-flat shaft comparison was verified. A flat-point screw is not the same thing as a flat machined on the shaft.

11. 8 MM CIRCLIP / COLLAR
11_Maedler_DIN471.pdf
11_Ruland_metric_collars.pdf
- Maedler: DIN 471 shaft ring and groove dimensions, including the 8 mm shaft row.
- Ruland distributor-hosted MCL table: 8 mm bore collar dimensions and screw. This is dimensional data, not a verified holding-force rating.
- DIN 6799 is not separately included; DIN 471 supplies the requested circlip alternative.

12. GATES 2 MM DRIVE DESIGN
12_Gates_GT2_drive_design.pdf
12_Gates_light_power_precision.pdf
- The legacy Gates GT2 design manual is a third-party-hosted original. It provides GT2 product/engineering context, but this collection did not verify a complete exact 2 mm GT2 installation-tension-by-width rule from it.
- The current official Gates Light Power and Precision manual includes 2 mm 2MGT GT3 belts used with GT2 sprockets. It is NOT a table of exact legacy GT2 belt tensions.
- Current manual page 67 (printed 65): tension tables, explicitly GT3. Page 70 (printed 68): idler guidance, wrap, teeth in mesh and minimum idler sizes for the named product families.
- Do not transfer those GT3 values to generic printer "GT2" belts. Exact legacy GT2 2 mm minimum pulley/idler/mesh/tension rules remain only partially resolved.

13. TRAPEZOIDAL LEAD SCREWS
13_ElesaGanter_trapezoidal_engineering.pdf
13_Igus_DryLin_leadscrews.pdf
13_Igus_dryspin_engineering.pdf
- Elesa/Ganter: page 1 thread families and accuracy; page 2 straightness, multi-start threads and reversal backlash; pages 3-4 buckling/critical-speed graphs and end fixity; page 5 forces/torque.
- Igus DryLin page 8 includes pitch deviation per 300 mm and straightness for the listed product; pages 5, 14 and 23 address anti/zero-backlash designs.
- Important: an 8 mm diameter alone does not identify a screw. Elesa's smallest listed trapezoidal family is 8 x 1.5; it is not the generic printer T8x8, four-start variant. Pitch, lead, nut type, tolerance and fixity must match. No generic T8x8 accuracy/backlash guarantee is established here.

14. PRINTED PETG / ABS: HDT AND CREEP
14_Prusament_PETG_TDS.pdf
14_Stratasys_ABSM30_TDS.pdf
14_ABS_creep_MDPI_research.pdf
14_PETG_creep_UTS_research.pdf
- Prusament PETG maker TDS: print-orientation-specific short-term data and HDT. Stratasys ABS-M30 maker TDS: print/process-specific values; page 5 includes HDT. Both documents' test conditions and disclaimers matter.
- ABS research: "Numerical and Experimental Investigations of Polymer Viscoelastic Materials Obtained by 3D Printing", Polymers 2021, 13, 3276. Page 6 states the Z-ABS/Zortrax M200 print and specimen conditions. Pages 10-13 and 19-20 discuss creep/relaxation tests and modelling. This is research, not a general allowable-stress design sheet.
- PETG UTS accepted manuscript studies pellet-extruded PETG. It is not a qualification of Prusament filament or your print process.
- HDT, glass transition, tensile strength and unloaded aging are not sustained-load creep allowables. No universal long-term allowable stress for arbitrary printed PETG/ABS was verified. Keep stress, temperature, duration, print orientation, infill and acceptance criterion together.

15. FDM GEOMETRY GUIDE
15_Stratasys_FDM_design_guide.pdf
- Page 5: holes and minimum wall guidance; page 7: bosses/ribs. July 2025 Stratasys guide.
- Values depend on machine, nozzle/layer, material, orientation and feature geometry. Validate critical hole fits on a coupon rather than assuming one correction fits every print.

16. ISO 13715 EDGE NOTATION
16_ISO13715_Modulus_maker_summary.pdf
- Saved maker article with source text and diagrams, not an original ISO standard. Includes plus/minus symbols and edge examples.
- Source inconsistency flagged on page 1: in chart B.7 (page 6), the notation/diagram show 0.1-0.5 mm while its explanation says 0.1-0.3 mm. Do not resolve that conflict by guessing.
- Example values illustrate notation; they are not universal recommended edge-break dimensions. Check the licensed standard for released drawings.

17. IEC 60204-1 ELECTRICAL SAFETY
17_SUVA_machine_electrical_safety.pdf
17_JMF_IEC60204_summary.pdf
17_IEC60204_IP2X_source_excerpt.pdf
- SUVA: concise machine electrical safety and bonding checklist.
- IDEC presentation hosted by JMF discusses the 2016 edition. Pages 20-26 cover equipotential/protective bonding; pages 65-66 discuss verification of protective bonding continuity.
- The one-page GT Engineering source excerpt supplies the general IP2X/IPXXB enclosure statement attributed to clause 6.2.2, with its source and limitations. The presentation's page 13 instead concerns residual voltage at exposed plug conductors; do not confuse the two rules.
- These summaries do not replace the applicable edition of the standard, local electrical rules, competent design or verification.

18. SLOCUM: EXACT CONSTRAINT AND BOLTED JOINTS
18_Slocum_Topic9.pdf
18_Slocum_fundamental_principles.pdf
- Topic 9: pages 16-25 discuss bolted structural joints; page 42 begins three-groove kinematic coupling discussion.
- Fundamental Principles lecture: page 37 (printed 3-36) covers exact constraint and degrees of freedom; page 39 discusses elastic averaging/reciprocity.
- Both are MIT-hosted Slocum materials. The fundamental-principles file is a lecture presentation rather than an OCW book chapter.

19. NASA-STD-5020
19_NASA_STD5020B_revalidated2026.pdf
- Official NASA-STD-5020B, approved 2021-08-06 and revalidated 2026-01-05 with no changes (cover/history log).
- Title: Requirements for Threaded Fastening Systems in Spaceflight Hardware. Its aerospace scope is important; it is a reference, not a declaration that every requirement applies to this printer.
- NASA source landing page: https://standards.nasa.gov/standard/NASA/NASA-STD-5020

All delivered files are below 10,000,000 bytes; no split was needed. No CAD was generated and no standards were purchased.
