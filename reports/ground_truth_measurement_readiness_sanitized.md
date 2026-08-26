# Asset ML Feasibility - Ground Truth and Measurement Readiness

## Scope

This section consolidates current ground-truth and measurement-readiness evidence for the seven target classifications. It does not include model training, accuracy estimates, or final feasibility conclusions.

No raw operational client values are emitted.

## Measurement Rule

Only `real_observed_label` and `validated_mapping` evidence can enter a measurement denominator. Reference catalogs, illustrative examples, agent inference, and unknown opportunities remain useful for discovery but are not measurement-ready.

## Current Measurement Readiness

- Measurement-ready pair rows: 0
- Classified pair rows: 910
- Unknown opportunity rows preserved: 802
- External structured fault-code signal rows: 602
- Distinct external fault-code tokens: 79

## Evidence Type Summary

| evidence_type | can_enter_measurement_denominator | current_pair_rows | interpretation |
| --- | --- | --- | --- |
| real_observed_label | True | 0 | eligible_after_runtime_and_sme_validation |
| validated_mapping | True | 0 | eligible_after_runtime_and_sme_validation |
| illustrative_example | False | 0 | not_measurement_ready_in_current_pass |
| reference_catalog | False | 0 | not_measurement_ready_in_current_pass |
| agent_inference | False | 108 | not_measurement_ready_in_current_pass |
| unknown | False | 802 | not_measurement_ready_in_current_pass |

## Target Measurement Readiness

| target | candidate_pair_rows | row_level_pair_count | distinct_files | measurement_ready_pair_count | measurement_readiness_status | zero_type_or_denominator_status | next_required_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Symptom | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_current_demonstrable_proof_of_life | Keep under explicit proof-of-life review; do not infer from broad narrative text. |
| Object Part | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Damage | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Cause | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| Activity | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| FLOC leaf segment | 0 | 0 | 0 | 0 | no_current_measurement_denominator | supporting_vocabulary_not_record_label | Validate whether the glossary and KKS support are sufficient for ML/NLP use. |
| Activity Type | 36 | 379593 | 1 | 0 | no_current_measurement_denominator | pending_controlled_mat_source | Confirm the controlled source and mapping rules before treating this target as measurable. |

## Source Denominator Summary

| source_block | files_listed | files_read_ok | files_failed | candidate_pairs_found | measurement_ready_pairs | zero_type |
| --- | --- | --- | --- | --- | --- | --- |
| inventoried_source_universe | 575 |  |  |  | 0 | not_applicable_inventory_denominator |
| safe_content_pair_discovery | 147 | 147 | 0 | 838 | 0 | candidate_pairs_found_not_measurement_ready |
| pdf_assets_of_concern_parser | 394 | 394 | 0 | 602 | 0 | candidate_pairs_found_controlled_vocabulary_pending |

## Unresolved Opportunity Buckets

| bucket | candidate_pair_rows | measurement_ready_pair_rows | status | next_required_action |
| --- | --- | --- | --- | --- |
| unknown_text_code_opportunities | 802 | 0 | preserved_pending_semantic_reconciliation | Split by target relevance, runtime availability, and evidence type before promotion. |
| external_fault_code_signal | 602 | 0 | controlled_source_required | Confirm the owning controlled vocabulary and SAP equivalence with SME or mapping owner. |

## Current Interpretation

- The current measurable denominator remains zero because no pair has yet been confirmed as a real observed label or validated mapping.
- Unknown text-code opportunities are preserved for semantic reconciliation; they are not discarded and not promoted to a target yet.
- The external PDF-derived fault-code signal is structurally real, but it requires controlled-vocabulary ownership and SME/SAP mapping validation before it can support target measurement.
- Zero measurement-ready evidence in this pass does not equal zero derivability.
- Runtime availability still requires confirmation before any target can move from candidate evidence to measurable feasibility.

## Required Follow-Up

- Classify unknown text-code opportunities by target relevance and evidence type.
- Confirm runtime availability for candidate source columns and parsed structured signals.
- Obtain SME or mapping-owner validation for any candidate label/mapping before measurement.
- Confirm the controlled source for external fault-code values and whether it maps to any SAP target.
- Keep Symptom under explicit proof-of-life guardrail unless new validated evidence overturns the current status.

## Non-Goals

- No model training was performed.
- No model accuracy estimate was produced.
- No final feasibility conclusion is included.
- No raw operational client values were emitted.
