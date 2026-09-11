# F6-G1 Denominator Update Memo

This artefact updates the effective STINT_2 denominator matrix after G1. It does not mutate the frozen STINT_1 F6 closure.

## Changes

| Target | Path | Previous | Updated | Basis |
|---|---|---:|---:|---|
| Object Part | B1_RELATIONAL_STRUCTURED | 0 | 3,027 | G1.1 strong material-to-Catalog-B crosswalk candidates only |
| FLOC turbine | B1_RELATIONAL_STRUCTURED | 0 | 10,699 | G1.2 site + turbine-token alignment to IH06 asset node |

## Held

FLOC leaf remains 0 admitted. The source reaches turbine asset nodes, not component or maintainable-item leaf nodes. Component descent via consumption is registered as G2-or-later debt and is not an open G1 blocker.

## Tier Rule

For Object Part B1, only `strong` G1.1 candidates enter the denominator update. Medium, weak, and no-candidate residuals remain declared but excluded from this denominator tier.

## G2 Rule

G2 must consume `f6_g1_evidence_denominator_matrix_sanitized.csv`, not the STINT_1 F6 matrix, or it will train/evaluate against stale denominators.
