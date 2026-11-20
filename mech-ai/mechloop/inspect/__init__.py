"""Measurement-and-learning pipeline for parts that come back from a shop (docs/INSPECTION.md).

- plan.py:        inspection plan per fabricated part (what to measure, nominal, tolerance, prediction, method) + SVG drawing
- scan.py:        flatbed-scanner measurement of flat parts (calibration target, outline and holes registered to the DXF)
- record.py:      measurement record, comparison against nominal and prediction, proposed learnings, loop metrics
- import_form.py: rows from the measurement form (inspect_form/index.html) into the record
"""
