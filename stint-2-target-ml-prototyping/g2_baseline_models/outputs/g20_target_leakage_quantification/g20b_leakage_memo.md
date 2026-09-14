# G2.0b - Target Leakage Quantification Memo

## Status

Steps 1-4 are complete for the current leakage issue.

## Step 1 count

The scan covered all three paths and all seven target-label families listed in the plan. It found 13 regex hits across 13 unique source rows. All hits were in `B1_RELATIONAL`.

```text
Cause        9 rows
Object Part  4 rows
```

No leaked row was above the active G2.0 threshold.

## Step 2 materiality

Decision: `not_material_for_G2_0`.

The decisive field is `rows_above_threshold`; its value is 0. This falls into the first branch of the materiality rule: exclude/mask and proceed, without rerunning G2.0.

## Evaluation set v1

`evaluation_set_v1` was checked separately and has 0 leaked rows. No evaluation-set cleaning is required.

## Step 3 deterministic routing

The leaked target-label segments were extracted by regex into deterministic evidence with provenance:

```text
evidence_type       real_observed_label
extraction_method   regex_target_label_parse
anchor_source       structural_field_in_text
tier                gold_pending_validation_sample
```

These rows are not promoted. Promotion remains blocked until a sample validation confirms the parsed assignment and catalogue alignment.

## Step 4 masking

The affected source rows were written to an internal masked-row file and a sanitized masking manifest. Versioned outputs contain hashes, target labels, and counts only; no raw surrounding text was emitted.

## Reproducibility

The regex catalog is recorded in `g20b_leakage_regex_catalog_sanitized.csv`. The detailed sanitized hit list is `g20b_leakage_regex_hits_sanitized.csv`.
