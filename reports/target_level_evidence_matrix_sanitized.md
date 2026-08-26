# Target-Level Evidence Matrix

This matrix is a prerequisite input to the Target-Level Feasibility Assessment.
It does not provide model accuracy, endpoint thresholds, or final feasibility conclusions.

## Summary

- Targets covered: 7
- Measurement-ready targets: 0
- Blocked or not-demonstrable targets: 3
- Raw operational values emitted: false

## Matrix

| target | available_source_signal | runtime_usability | ground_truth_or_mapping_support | measurable_target_status | measurement_ready_pair_rows | preliminary_mapping_rows | classified_pair_rows | row_level_pair_count | derivability_assessment | recommended_method | coverage_confidence_status | primary_blocker | needed_from_whom | field_matrix_reference | raw_operational_values_emitted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Symptom | near_zero_current_evidence | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | not_demonstrable_with_current_evidence | blocked_pending_new_evidence_or_sme_proof_of_life | not_estimated_no_validated_denominator | No current demonstrable proof-of-life under available evidence. | SME / technical lead / field matrix owner | 0 resolvable mappings in profiling evidence. | False |
| Object Part | external_fault_code_signal_not_mapped_to_current_catalog | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | candidate_signal_requires_vocab_mapping | requires_controlled_fault_vocabulary_before_method_selection | not_estimated_no_validated_denominator | Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed. | OEM SME / controls owner / mapping owner | Long-tail and singleton behavior reported; record-level mappings still need confirmation. | False |
| Damage | external_fault_code_signal_not_mapped_to_current_catalog | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | candidate_signal_requires_vocab_mapping | requires_controlled_fault_vocabulary_before_method_selection | not_estimated_no_validated_denominator | Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed. | OEM SME / controls owner / mapping owner | Partial profiling or mapping coverage reported; record-level labels not demonstrated here. | False |
| Cause | limited_or_uncertain_signal | candidate_requires_runtime_validation | metadata_or_agent_inference_not_label | not_currently_measurable | 0 | 3 | 36 | 379593 | partial_candidate_requires_validation | candidate_pending_ground_truth_and_runtime_validation | not_estimated_no_validated_denominator | Runtime availability and record-level label or validated mapping support are not closed. | SME / mapping owner / runtime application owner | Low profiling or mapping coverage reported; record-level labels not demonstrated here. | False |
| Activity | candidate_text_code_signal | candidate_requires_runtime_validation | metadata_or_agent_inference_not_label | not_currently_measurable | 0 | 3 | 36 | 379593 | partial_candidate_requires_validation | candidate_pending_ground_truth_and_runtime_validation | not_estimated_no_validated_denominator | Runtime availability and record-level label or validated mapping support are not closed. | SME / mapping owner / runtime application owner | No final measured derivability conclusion in this pass. | False |
| FLOC leaf segment | provisional_glossary_or_supporting_signal | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | insufficient_current_evidence | rules_or_classifier_candidate_with_kks_supporting_validator | not_estimated_no_validated_denominator | Glossary or KKS support must be validated as ML/NLP signal, not resolver. | SAP functional owner / SME / technical lead | Glossary-based support exists; KKS is supporting validator only. | False |
| Activity Type | pending_controlled_source_signal | pending_controlled_source_confirmation | pending_controlled_source_confirmation | not_currently_measurable | 0 | 3 | 36 | 379593 | blocked_pending_controlled_source | blocked_pending_controlled_mat_source | not_estimated_no_validated_denominator | Controlled source for activity type code remains unconfirmed. | OEM SME / mapping owner / technical lead | Controlled MAT/activity-type source pending. | False |

## Interpretation Guardrails

- A candidate signal is not a validated label.
- Runtime availability must be confirmed before a source can become a usable feature.
- Only real observed labels or validated mappings can support measurement.
- Zero measurement-ready rows does not automatically mean zero derivability.
- KKS can support or validate FLOC interpretation; it must not be treated as a resolver.
