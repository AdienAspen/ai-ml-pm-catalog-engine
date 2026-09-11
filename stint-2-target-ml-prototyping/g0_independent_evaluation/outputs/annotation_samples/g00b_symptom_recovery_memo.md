# G0.0b Symptom Row-Level Unit Recovery

## Purpose

Recover row-level unit keys for Symptom paths that F6 retained only as aggregate admitted counts.

## Selection Rule

`predicted_class = observed_condition` and `abstained = False`.

## Reconciliation

- `RELATIONAL_REASON`: expected `1827`, recovered `1827` rows, `696` unique units: `reconciled`.
- `PATH_A_CONCERN_TABLE`: expected `68`, recovered `68` rows, `68` unique units: `reconciled`.
- `PATH_A_NOTES`: expected `42`, recovered `42` rows, `42` unique units: `reconciled`.
- `B2_WORKBOOKS`: expected `62`, recovered `62` rows, `62` unique units: `reconciled`.

## Sampling Key

`sampling_unit_key` is unique per recovered row. Source hashes are retained as provenance, but `RELATIONAL_REASON` contains repeated `reason_hash` values and must not use that hash alone as the sampling key.

## Decision Impact

The Symptom aggregate-only blocker is recoverable for the four admitted paths. These row-level keys can support G0 protocol sampling, but they remain `derived_from_rules` labels until blind annotation creates independent labels.

No raw operational values are emitted.
