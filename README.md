# Asset ML Feasibility

Reproducible local workspace for an asset-maintenance ML data prospection and feasibility POC.

## Scope

This repository implements a reproducible Python pipeline for inventory, schema profiling, controlled vocabulary, lexical prospection, evidence classification, PDF extraction, and reporting.

No model training, no accuracy estimates, and no final feasibility conclusions are produced in this stage.

## Validation Chain

Every target-level conclusion must follow this chain:

```text
signal exists -> runtime usable -> valid label/mapping -> measurable target -> feasible method
```

## Target Families

1. Symptom / Catalog S
2. Object Part / Catalog B
3. Damage / Catalog C
4. Cause / Catalog 5
5. Activity / Catalog A
6. Functional-location leaf segment
7. Activity Type / equipment or material activity code

## Operating Rules

- Do not commit raw source data.
- Do not emit raw operational values in external or shareable reports.
- Use counts, schemas, generic package identifiers, safe summaries, and configuration/code vocabulary where possible.
- Reference catalogs are not ground truth.
- Mapping examples do not create a measurement denominator unless validated.
- Agent inference must never be used as a label.
- Structural asset identifiers may support or validate interpretation; they must not be treated as target labels without validation.
- Prospection thresholds are not model thresholds and are not endpoint thresholds.

## Local Layout

- `src/asset_ml_feasibility/`: reusable pipeline modules.
- `scripts/`: executable entry points.
- `notebooks/`: optional audit notebooks and review workbooks.
- `reports/`: sanitized reports and CSV summaries.
- `reports/internal/`: local restricted reports, ignored by Git.
- `artifacts/`: machine-readable sanitized summaries.
- `artifacts/internal/`: local restricted artifacts, ignored by Git.
- `data/`: local data zones, intentionally ignored except placeholders.
