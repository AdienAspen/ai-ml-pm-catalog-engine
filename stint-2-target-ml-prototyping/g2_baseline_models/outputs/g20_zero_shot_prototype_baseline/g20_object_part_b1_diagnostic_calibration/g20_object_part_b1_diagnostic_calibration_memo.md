# G2.0 Object Part B1 Diagnostic Threshold Calibration

This calibration uses the 375 clean Object Part B1 annotation records as `diagnostic_calibration`. The rows are not eligible for final held-out claims.

## Governance

```text
evaluation_role              diagnostic_calibration
sampling_design              score_band_stratified
eligible_for_final_heldout   false
threshold_selection_source   calibration_60_only
production_claim_allowed     false
```

## Split integrity

The split is grouped by `source_unit_key` and stratified by hidden score band, so overlap records for the same text cannot land on both sides of the split. Integrity pass: `True`.

Unique source split: 180 calibration / 120 held-out. Annotation rows: 230 calibration / 145 held-out.

Effective rows for threshold math: 374. Abstentions excluded from threshold math: 1. Leakage-gap excluded rows: 1.

## Threshold decision

Selected threshold: `0.30`.

Calibration 60:

```text
evaluation_rows        229
covered_rows           207
correct_rows           196
precision_on_covered   0.946860
coverage_pct           90.393013
```

Held-out 40 report, not used for selection:

```text
evaluation_rows        145
covered_rows           131
correct_rows           128
precision_on_covered   0.977099
coverage_pct           90.344828
```

## Interpretation

This is a calibrated diagnostic figure for Object Part B1. It answers whether the corpus-informed prototype score can be thresholded against the clean annotation package. It is not a production performance claim and does not alter denominators or promote candidates.

Full curve: `g20_object_part_b1_threshold_precision_coverage_curve_sanitized.csv`.
