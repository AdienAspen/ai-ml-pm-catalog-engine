# T8a - Stratification Check

## Purpose

This precondition check determines whether T8 lexical sampling can be stratified by maintenance type and by contractor/site before dictionary construction begins.

No free-text maintenance-type inference is performed in this task. Outputs are aggregate and sanitized.

## Answers to Required Questions

### 1. Explicit Maintenance-Type Field

- `CONTRACTOR_PATH_001` service orders contain an explicit `activityType` field.
- Coverage: 10749 / 10749 rows (100.0%).
- This supports direct stratification for that path.
- For the PDF assets-of-concern path, `event` exists as a structured table field, but it is not declared as maintenance type. It can support a separate event stratum, not a direct planned/reactive label without downstream rules.
- PDF event coverage: 1581 / 1581 rows (100.0%).

### 2. Values and Distribution

- Value distributions are emitted in `outputs/t8a_maintenance_type_distribution_v1.csv` using value keys and coarse buckets, not raw operational text.
- Nomenclature is path-specific and must not be unified at T8a. `activityType` and PDF `event` are separate fields with different semantics.

### 3. Derivable Fields

- Potential derivation fields exist, including order type, priority, event, and fault-code presence.
- No derivation rule is applied here, because deriving maintenance type from text or mixed operational signals belongs to STINT_1 evidence engineering, not this pre-sampling profile check.

### 4. Contractor/Site Segmentation

- Contractor/path segmentation is direct from source path families and is emitted as sanitized `CONTRACTOR_PATH_*` keys.
- `CONTRACTOR_PATH_001` service orders contain `siteId` with 10749 / 10749 rows (100.0%).
- PDF assets-of-concern rows contain structured site text with 1581 / 1581 rows (100.0%).

## Declared Output Case

Case `A_partial_B_pending` applies.

- A: direct stratification is available for the service-order path through `activityType`.
- A-event: PDF rows have a structured `event` field, but this is not equivalent to maintenance type and must remain separate.
- B pending: other source paths may require derivation from order type, priority, event, fault-code presence, or description patterns, but no such inference is performed in T8a.

## Implication for T8 Sampling

- T8 must stratify `CONTRACTOR_PATH_001` by `activityType` and site key.
- T8 may stratify PDF rows by structured `event` and site key, but must not call that planned/reactive maintenance type without a documented STINT_1 rule.
- T8 must record `source_text_field` for every sampled term, per `DELTA-0003`.
- Symptom and Cause sampling must avoid mixing planned-like and reactive-like strata when a direct stratum exists.

## Outputs

- `outputs/t8a_maintenance_type_distribution_v1.csv`
- `outputs/t8a_stratification_coverage_v1.csv`
- `outputs/t8a_candidate_stratification_fields_v1.csv`
- `outputs/t8a_stratification_summary_v1.json`
