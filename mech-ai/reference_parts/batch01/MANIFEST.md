# Reference parts, batch 01

Made by mechloop (our own geometry, no supplier CAD). Units: mm. Each part lists the issues we
expect a supplier's DFM check to raise; RP02 is a control built to pass.

## RP01 cnc_bracket_sharp

- Files: RP01_cnc_bracket_sharp.step
- Process: CNC milling
- Material: Aluminium 6061-T6
- Finish: as machined
- Quantities to quote: 1, 10
- Size: 80.0 x 50.0 x 20.0 mm
- Notes: Thread: the 3.3 mm blind hole in the +X end face is M4x0.7, 10 mm deep (state in the quote's thread callout if the site allows).
- Expected findings:
  - sharp internal pocket corners (R0) cannot be milled with a round tool
  - 3 mm slot 16 mm deep: depth 5.3 x width, needs a long small cutter
  - blind tapped hole: check thread depth/drill depth rules

## RP02 cnc_plate_clean

- Files: RP02_cnc_plate_clean.step
- Process: CNC milling
- Material: Aluminium 6061-T6
- Finish: as machined
- Quantities to quote: 1, 10
- Size: 100.0 x 60.0 x 10.0 mm
- Notes: Control part: built to pass.
- Expected findings:
  - no issues expected (R4 pocket corners, 4 mm deep pocket, plain through holes)

## RP03 sheet_channel

- Files: RP03_sheet_channel.step
- Process: Sheet metal: laser cut + bend
- Material: Aluminium 5052-H32, 0.090 in (2.29 mm)
- Finish: none
- Quantities to quote: 1, 10
- Size: 60.0 x 40.0 x 25.0 mm
- Notes: Inside bend radius about 1 x thickness.
- Expected findings:
  - 6 mm flange (outside; 1.4 mm straight after the bend) is shorter than typical minimum flange for 0.090 in
  - 5.5 mm hole in the tall flange 1.5 mm from the bend tangent: too close, will distort

## RP04 laser_plate

- Files: RP04_laser_plate.step, RP04_laser_plate.dxf
- Process: 2D laser cutting
- Material: Aluminium 6061-T6, 0.125 in (3.18 mm)
- Finish: none
- Quantities to quote: 1, 10
- Size: 120.0 x 80.0 x 3.17 mm
- Notes: Upload the DXF where a site wants 2D; STEP otherwise. Units: mm.
- Expected findings:
  - 1.2 mm hole: below the usual minimum hole (about 50-100 % of thickness)
  - 4 mm hole with 0.8 mm to the edge: too close
  - 1.0 mm slot: narrower than the usual minimum feature width
  - sharp inside corner of the L cutout (laser leaves a kerf radius; usually acceptable)

## RP05 fdm_clip

- Files: RP05_fdm_clip.step
- Process: 3D printing: FDM
- Material: PETG (or PLA)
- Finish: standard
- Quantities to quote: 1, 10
- Size: 60.0 x 20.0 x 15.0 mm
- Notes: Print flat on the 60 x 20 base.
- Expected findings:
  - 0.6 mm wall: below a typical 0.8-1.2 mm minimum FDM wall
  - 20 mm flat unsupported overhang: needs support
  - 1.5 mm pin: fragile / below minimum feature for some services
