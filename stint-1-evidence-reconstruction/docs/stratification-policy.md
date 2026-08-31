# Stratification Policy

## Known Stratification State

| corpus segment | policy |
|---|---|
| `CONTRACTOR_PATH_001` | Uses explicit `activityType` with observed 100% coverage in T8a. Stratify directly. |
| PDFs | Use `stratum: event_structural`. Never label as planned/reactive in this phase. |
| inferred derivation | Mark as `evidence_type: expert_inference` and keep separate from direct explicit strata. |

## Reporting Rule

Do not combine planned/reactive strata with `event_structural` in the same denominator or evidence count.

## Downstream Implication

Symptom and Cause denominators may need to be conditioned on the subset where those concepts can semantically exist.

