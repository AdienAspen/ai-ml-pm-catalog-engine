# F6-G20 Denominator Update Memo

This artefact updates the effective STINT_2 denominator matrix after G20 Object Part B1 diagnostic calibration. It does not mutate the frozen STINT_1 F6 closure or the earlier G1 closure artefacts.

## Object Part B1

Object Part B1 returns to the proxy denominator through the corpus-informed prototype baseline at threshold `0.30`.

```text
B1 universe units                         10749
previous G1 strong crosswalk denominator   3,027
G20 threshold                              0.30
admitted at threshold, leakage excluded    6764
unmasked-leakage reference count           6774
leakage-gap units excluded                 13
```

The threshold is diagnostic only:

```text
evaluation_role              diagnostic_calibration
eligible_for_final_heldout   false
threshold_selection_source   calibration_60_only
production_claim_allowed     false
```

## Majority baseline

The threshold report is paired with a majority-class baseline in `g20_object_part_b1_threshold_vs_majority_baseline_sanitized.csv`. This is required because Object Part B1 is prevalence-heavy; high raw performance must be read against the class distribution.

## Activity, Cause and Damage

Their counts are not changed in this update. They remain caveated as possibly inflated by catalogue-derived anchors and should not be treated as clean ML scope until anchor-source review/calibration closes.

## No hidden changes

No recalibration beyond the Object Part B1 diagnostic threshold was performed. No candidate promotion was performed. No contractual denominator was changed.

## Chapter #2 calibration controls

The Object Part B1 threshold count remains a deterministic score-threshold denominator count: 6,764 B1 units at threshold 0.30, excluding leakage-gap units.

The precision/coverage metrics must not be quoted from raw annotation rows alone. Chapter #2 controls add:

- count reconciliation for 375 / 374 / 373 rows
- unique `source_unit_key` metrics so overlap does not double-count a physical unit
- score-band inverse-probability weighting against the B1 universe distribution

Use `g20_object_part_b1_selected_threshold_weighted_population_report_sanitized.csv` for population-facing diagnostic precision/coverage, and keep `eligible_for_final_heldout=false` attached to every figure.
