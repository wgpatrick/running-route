"""Measurement-and-learning pipeline for parts that come back from a shop (docs/INSPECTION.md).

- plan.py:        inspection plan per fabricated part (what to measure, nominal, tolerance, prediction, method) + SVG drawing
- scan.py:        flatbed-scanner measurement of flat parts (calibration target, outline and holes registered to the DXF)
- record.py:      measurement record, comparison against nominal and prediction, proposed learnings, loop metrics
- predictions.py: frozen, hashed predictions per part and order (freeze / load / verify); record.compare scores only these
- import_form.py: rows from the measurement form (inspect_form/index.html) into the record
"""
