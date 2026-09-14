# G2.0 Committee Threshold and Object Part B1 Annotation Follow-up

This follow-up does not promote candidates, change denominators, or set a final threshold. It exposes committee decision points after G2.0 diagnostics showed that precision >= 0.80 is not reachable for B1/B2 under the current evaluation support.

## Threshold decision artefacts

- `g20_threshold_reselection_by_target_path_sanitized.csv` reports the best calibration-curve point by target and path and marks whether precision 0.80 is reachable.
- `g20_committee_threshold_coverage_sanitized.csv` reports operational coverage at thresholds 0.45, 0.50, 0.55, and 0.60.
- `g20_committee_threshold_eval_precision_sanitized.csv` reports calibration/held-out precision at those same thresholds wherever evaluation rows exist.

Final cut selection is a committee decision, not an automated script decision.

## Object Part B1 annotation gap

Object Part B1 has the largest volume and no independent branch evaluation in v1, so it cannot be calibrated as a branch. A 300-row diagnostic annotation package was created in the closed internal environment. The selection is score-band stratified for calibration diagnosis; model scores and predicted classes are hidden from annotators. The package has four declared scoping fields: `evaluation_independence = independent`, `evaluation_role = diagnostic_calibration`, `sampling_design = score_band_stratified`, and `eligible_for_final_heldout = false`. The annotation can be independent because model predictions are hidden from annotators, but the package is diagnostic calibration material and must not become final held-out evaluation.
