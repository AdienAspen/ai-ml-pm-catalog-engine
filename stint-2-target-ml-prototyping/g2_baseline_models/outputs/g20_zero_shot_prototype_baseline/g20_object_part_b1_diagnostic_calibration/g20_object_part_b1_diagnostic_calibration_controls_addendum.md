# G2.0 Object Part B1 Diagnostic Calibration Controls

This addendum corrects the interpretation of the previous row-level calibration report. The original precision/coverage figures were sample metrics over annotation rows. They do not estimate the B1 population unless the score-band sampling design is accounted for.

## Count reconciliation

```text
annotation_rows_total                      375
abstain_rows                               1
leakage_gap_rows                           1
rows_both_abstain_and_leakage_gap          1
effective_rows_before_leakage_exclusion    374
effective_rows_after_leakage_exclusion     374
```

The apparent mismatch is resolved because the one leakage-gap annotation row is also the one abstention. Therefore `375 - 1 abstain = 374`. The leakage-gap row is the same abstain row, so excluding leakage as a separate category does not reduce the effective threshold-math rows again. The union exclusion remains `374` effective annotation rows; subtracting both independently would double-count the same row.

## Unique source-unit metric

Overlap rows are not forced into consensus. Each `source_unit_key` carries the mean of its available annotator judgments, so disagreement contributes fractional correctness instead of duplicating the physical unit.

At threshold `0.30`:

```text
calibration_60 precision_unique_units  0.956522
calibration_60 coverage_unique_pct     89.944134
heldout_40 precision_unique_units      0.972222
heldout_40 coverage_unique_pct         90.000000
```

## Score-band weighted population estimate

The population estimate weights sampled source units by score-band inclusion against the Object Part B1 universe distribution. This is still diagnostic calibration, not final evaluation.

At threshold `0.30`:

```text
calibration_60 weighted_precision       0.912716
calibration_60 weighted_coverage_pct    63.002981
heldout_40 weighted_precision           0.942262
heldout_40 weighted_coverage_pct        63.002981
```

## Governance still active

```text
evaluation_role              diagnostic_calibration
eligible_for_final_heldout   false
production_claim_allowed     false
```

Object Part B1 remains modelable under the prototype baseline, but the population-facing number to quote is the weighted source-unit diagnostic estimate, not the unweighted annotation-row metric.
