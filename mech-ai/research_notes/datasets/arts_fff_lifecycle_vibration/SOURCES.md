# FFF printer full-lifecycle vibration monitoring (ARTS Laboratory, Univ. of South Carolina)

- URL: https://github.com/ARTS-Laboratory/dataset-FFF-printer-full-lifecycle-vibration-monitoring (archived as DOI 10.5281/zenodo.21795890, not reachable from this sandbox)
- Licence: CC BY-SA 4.0 (LICENSE copied here). Fetched 2026-11-15.

One Creality Ender 5 Plus followed over about 1,600 operating hours; at 15 wear states three PCB 352A92 accelerometers (hotend, feeder motor, frame; NI 9234) recorded about 639 s at 1,651.6 samples/s while the printer printed tensile bars. Stored here: the README, `features.csv` (81 features per state), the maintenance log, and one of the 15 raw recordings, `raw_vibration/Sample01.lvm` (41.5 MB, LabVIEW text: 23 header lines then `X_Value, Acceleration_0..2` in g, 1,056,000 rows). The other 14 raw files are about 41 MB each at the same path (`Sample02.lvm` ... `Sample11.lvm`, `Sample_12.lvm` ... `Sample_15.lvm`) and were left out to stay inside the size limit. The 75 tensile-test files were not fetched. The motion that produced the vibration is not recorded, so this is a spectrum-while-printing reference, not an input-output data set.
