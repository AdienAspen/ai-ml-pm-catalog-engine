# Asset Maintenance Bridge ML Feasibility - Draft 1 Postscript: Denominator Reconciliation

## Scope

Postscript to `ai_ml_data_feasibility_assessment_draft1_sanitized.md`.

This note records a denominator reconciliation pass performed after Draft 1 committee review. It does not change the assessment scope, does not introduce model training, does not estimate accuracy, and does not include raw operational client values.

## Corrections / Clarifications

### D01 - `838` vs `910` Candidate Pair Rows

The apparent difference is explained by multi-target expansion.

- `838` rows correspond to safe content pair discovery rows before target expansion.
- `910` rows correspond to target-expanded classification rows.
- `36` rows carried a shared `target_hint` for `Cause;Activity;Activity Type`.
- Each of those rows expanded into three target-attributed rows, adding `72` rows.

Reconciliation:

```text
838 + (36 * 2) = 910
```

### D02 - Cause / Activity / Activity Type Uniformity

The repeated counts for `Cause`, `Activity`, and `Activity Type` should be read as shared evidence, not independent target-specific evidence.

The uniformity comes from a shared multi-target hint expansion over the same source/rule pattern. These rows remain candidate evidence pending semantic validation, runtime validation, and label/mapping confirmation. They must not be treated as three independent denominators.

### D03 - Parser Gap Register / G08

The current reconciliation pass reports:

```text
parser_issue_on_tabular_files = 0
```

Therefore, any previous open item stating `G08 - Remaining parser issues on tabular files` should be moved out of the open gap register and marked as `Resolved / Closed Control`, unless a newer parser-triage artifact contradicts this status.

### D04 - `147` vs `157` File Denominator

The `157` file count represents the broader structural scan attempt universe.

The `147` file count represents the intentional `source_data` scope used by safe content pair discovery.

The difference of `10` files is explained by non-source files that were structurally scanned but intentionally excluded from pair discovery:

- `4` mapping documents
- `6` reference data files

This is a scope distinction, not a missing-read condition.

## Reporting Implication

Draft 1 remains usable, but the denominator language should be interpreted with these four clarifications:

- `838` and `910` are different stages of the same evidence pipeline.
- `Cause`, `Activity`, and `Activity Type` shared counts are not independent evidence.
- `G08` is closed under the current parser-triage state.
- `147` is the correct denominator for source-data pair discovery; `157` is the broader structural scan denominator.

## Non-Goals

- No raw operational client values were emitted.
- No model training was performed.
- No model accuracy estimate was produced.
- No final feasibility conclusion is added by this postscript.
