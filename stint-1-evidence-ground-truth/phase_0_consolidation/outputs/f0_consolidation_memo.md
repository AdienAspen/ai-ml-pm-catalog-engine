# F0 - Consolidation and Preconditions

## Purpose

Phase 0 consolidates STINT_0 accounting and STINT_1.1 reference-layer decisions before evidence reconstruction begins.

This pass does not train models, estimate accuracy, create production ground truth, or modify the frozen reference layer.

## Reconciled Accounting

- Source opportunity rows: 838
- Target-expanded classification rows: 910
- Multi-target hint rows: 36
- Expansion delta: 72
- Structural files attempted: 157
- Source-data pair-discovery files: 147
- Current tabular parser issues: 0

## Decisions

- `G04` is closed for PoC by documented proxy assumption, not by production runtime proof.
- `G08` is closed under current evidence: tabular parser issues are zero.
- Cause / Activity / Activity Type shared expansion remains open for Phase 2 semantic split.
- `DELTA-0002` is resolved for PoC by `stint1_record_id` deterministic proxy policy.
- `DELTA-0003` is resolved for PoC by target-specific `source_text_field` routing.

## DELTA-0002 Record Identifier Specification

- Record id field: `stint1_record_id`
- Composition:
  - `source_family`
  - `source_path_key`
  - `source_record_ordinal`
  - `source_text_field`
- Construction: `deterministic_non_reversible_hash_over_sanitized_record_lineage`
- Stability: stable_if_source_package_ordering_and_source_record_ordinal_are_reproducible.
- Uniqueness scope: unique_by_design_within_source_family_source_path_key_source_record_ordinal_source_text_field.
- Collision policy: check_for_duplicate_stint1_record_id_within_each_phase_output_before_denominator_use.
- Production claim: PoC proxy only; does not claim production runtime record identity.

## DELTA-0003 Source Text Routing

| target | primary_source_text_field | allowed_supporting_fields | notes |
|---|---|---|---|
| Symptom | `classification_input.description_extended` | `classification_input.description; classification_input.reason` | Hypothesis/silver-medium at most until downstream validation; run on semantically reactive subsets only. |
| Object Part | `classification_input.description_extended` | `classification_input.work_performed; pdf_assets_of_concern.event` | Use component/system mentions; do not promote if only generic action text is present. |
| Damage | `classification_input.description_extended` | `classification_input.description; pdf_assets_of_concern.event` | Route through failure-process semantics; do not treat generic failure mode as SAP Damage. |
| Cause | `classification_input.reason` | `classification_input.description_extended` | Never infer Cause directly from Damage; shared multi-target evidence remains blocked by DELTA-0009. |
| Activity | `classification_input.work_performed` | `classification_input.description_extended` | Action/measure evidence can support Activity after semantic split. |
| FLOC leaf | `header.functional_location` | `classification_input.description_extended` | Structural target; text is supporting evidence only. Resolve against IH06-derived nodes. |
| Activity Type | `header.activity_type` | `classification_input.work_performed` | Direct field where available; inferred maintenance type remains expert_inference. |

PDF-derived records keep `stratum: event_structural` and must not be mixed with planned/reactive strata.

## Phase Gate

F0 clears the preconditions for Phase 1 lexical rework. It does not create measurement-ready targets.

Measurement-ready targets remain: 0

## Governance

- No raw operational values are emitted.
- No global denominator is introduced.
- `expert_inference` remains outside measurement denominators unless later converted through a documented validation/proxy rule.
