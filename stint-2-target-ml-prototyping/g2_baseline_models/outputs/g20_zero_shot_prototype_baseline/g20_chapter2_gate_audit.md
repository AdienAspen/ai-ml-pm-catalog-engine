# G2.0 Chapter #2 Gate Audit

## Gate 1 - Split Integrity

Status: **PASS**.

The selected threshold for `Object Part | PATH_A` is `0.38`. Recomputing threshold selection from `calibration_60` rows only gives `0.38`. The held-out result file declares `threshold_selected_from = calibration_60`. Therefore the held-out subset did not participate in threshold selection.

Held-out result remains **insufficient evaluation support**, not a performance claim: `17/17` means no observed errors in 17 covered held-out rows.

## Gate 2 - Catalogue vs Prototype Contrast

Status: **PASS**.

The formal contrast is recorded in `g20_catalogue_vs_zero_shot_comparison_sanitized.csv`. For `Object Part | B1_RELATIONAL`, the catalogue-anchor baseline is `3,737` units; the path-calibrated prototype baseline admits `0` units because no independent B1 Object Part evaluation exists in v1 and no path-specific threshold is selected.

## Gate 3 - Nomenclature

Status: **PASS**.

Object Part is not pure zero-shot. Its prototypes are `derived_from_blind_sample` and carry `evaluation_exclusion = g11e_group_b_blind_order_sample_internal`. The correct label for Object Part is **corpus-informed prototype baseline**. Cause, Damage and Activity remain source-transcribed prototype baselines.

## Split Counts

See `g20_split_integrity_counts_sanitized.csv`.
