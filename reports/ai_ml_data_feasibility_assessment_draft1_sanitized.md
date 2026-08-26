# Asset Maintenance Bridge - AI/ML Data Feasibility Assessment

**Draft status:** Draft 1 / evidence-based technical memo.

**Scope guardrail:** no model training, no accuracy estimate, and no final feasibility conclusion are included in this draft.

**Data governance guardrail:** no raw operational client values are emitted in this report.

## Table of Contents

1. Executive Summary
2. Assessment Scope & Questions
3. Data Universe & Effective Read Coverage
4. Evidence & Validation Method
5. Ground-Truth & Measurement Readiness
6. Target-Level Feasibility Assessment
7. Cross-Target Findings & Data Gaps
8. Feasibility Matrix & Recommended Technical Direction
9. Required Inputs, Owners & Decisions
10. Conclusions & Next Steps
Appendices A-E

## 1. Executive Summary

This assessment reconstructs the AI/ML data feasibility evidence chain in a local, reproducible, sanitized pipeline. The current result is an evidence-readiness view, not a final feasibility decision.

- Targets assessed: `7`.
- Current measurement-ready targets: `0`.
- Inventoried source universe: `575` files.
- Structured/tabular output rows emitted by the structural pass: `288`.
- Candidate safe content pair rows classified: `910`.
- External PDF-derived fault-code rows with non-empty code signal: `602`.
- Distinct external fault-code tokens profiled: `79`.
- High-severity open gaps: `6`.

Main finding: the corpus contains meaningful source signal and structured opportunities, but no target currently has a validated measurement denominator. The next decision is therefore not model selection; it is validation of runtime availability and true labels or SME-confirmed mappings.

## 2. Assessment Scope & Questions

The objective is to assess whether available historical and reference data can support AI/ML-assisted extraction or classification into the seven target outcomes.

- Symptom / Catalog S.
- Object Part / Catalog B.
- Damage / Catalog C.
- Cause / Catalog 5.
- Activity / Catalog A.
- FLOC leaf segment.
- Activity Type / MAT.

This assessment measures evidence readiness: source signal, runtime plausibility, label/mapping support, measurement readiness, and method direction. It does not train models, estimate production accuracy, or set endpoint thresholds.

## 3. Data Universe & Effective Read Coverage

The reconstructed local pipeline separates inventory from effective read coverage. A listed file is not treated as read unless the parser opened it successfully.

| source_block | files_listed | files_read_ok | files_failed | candidate_pairs_found | measurement_ready_pairs | zero_type |
| --- | --- | --- | --- | --- | --- | --- |
| inventoried_source_universe | 575 |  |  |  | 0 | not_applicable_inventory_denominator |
| safe_content_pair_discovery | 147 | 147.0 | 0.0 | 838.0 | 0 | candidate_pairs_found_not_measurement_ready |
| pdf_assets_of_concern_parser | 394 | 394.0 | 0.0 | 602.0 | 0 | candidate_pairs_found_controlled_vocabulary_pending |

- Source inventory files: `575`.
- Structural scan files attempted: `157`.
- Structural scan output rows emitted: `288`.
- PDF files listed in the external fault-code parser pass: `394`.
- PDF files read successfully: `394`.
- PDF parser failures: `0`.

Remaining gaps are tracked as parser, vocabulary, runtime, and SME-confirmation dependencies rather than as negative feasibility findings.

## 4. Evidence & Validation Method

The local reconstruction uses a conservative validation chain:

| step | question | evidence_needed |
| --- | --- | --- |
| signal_exists | Is there source evidence that plausibly carries target information? | Safe schema/profile evidence, controlled-vocabulary overlap, row-level co-occurrence, or parser-derived structured evidence. |
| runtime_usable | Will the signal be available when the production engine runs? | Runtime app/source confirmation, canonical field matrix alignment, or source owner confirmation. |
| valid_label_or_mapping | Can we prove what the correct target code was for a record? | Real observed label or validated mapping. Reference catalogs and agent inference are not enough. |
| measurable_target | Is there a defensible denominator for coverage/confidence measurement? | Record-level label/mapping evidence tied to runtime-available input fields. |
| feasible_method | Which method is justified by the evidence? | Rules, classifier, NER, hybrid method, or unresolved status based on validated evidence. |

Evidence types are explicitly separated so that reference material, inferred relationships, and examples do not become artificial ground truth.

| evidence_type | definition | can_support_measurement | measurement_use |
| --- | --- | --- | --- |
| real_observed_label | Record-level evidence where the correct target code is observed as data. | True | Can enter the measurement denominator after runtime availability is confirmed. |
| validated_mapping | A mapping confirmed by an SME, mapping owner, or governed project documentation. | True | Can enter the measurement denominator if it applies at record level. |
| illustrative_example | An example showing intended behavior, not proof of a record-level label. | False | Useful for interpretation only unless later validated. |
| reference_catalog | Catalog, code list, glossary, or controlled vocabulary. | False | Useful for matching and normalization, not a ground-truth denominator. |
| agent_inference | A pipeline-generated hypothesis inferred from metadata or structure. | False | Must never be used as a label. |
| unknown | Unresolved text-code opportunity that has not been classified. | False | Preserve for semantic reconciliation; do not promote to a target yet. |

Method phases:

| phase | purpose | status | current_role |
| --- | --- | --- | --- |
| Workbench prospection | Initial manual/notebook data inventory, schema profiling, vocabulary exploration, and committee review. | historical_context | Findings are retained as methodological context, but the local pipeline is the reproducible source of record going forward. |
| Local reproducible reconstruction | Rebuild the same evidence chain as modular Python scripts with sanitized outputs and repeatable run summaries. | active_source_of_record | Feeds all current report sections and can be re-run as source data, parsers, or SME decisions change. |
| Controlled vocabulary prospection | Use target-specific controlled terms to reduce broad keyword noise. | active_supporting_method | Supports signal discovery, not final model thresholding or endpoint thresholding. |
| Safe content and row-level pair discovery | Identify text-code co-occurrence opportunities without emitting raw operational values in committee-facing outputs. | active_supporting_method | Produces candidate opportunities that require evidence classification and runtime validation. |
| Target-level evidence matrix | Organize evidence by target across signal, runtime, label/mapping, measurability, and method direction. | draft_dependency | Useful as a bridge to target-level feasibility, but must be regenerated after sections 5 and 7 are consolidated. |

Controlled vocabulary and prospection notes:

- Controlled catalog vocabulary rows loaded: `13986`.
- Vocabulary overlap rows: `2`.
- Prospection thresholds are methodological filters only; they are not model confidence thresholds and are not endpoint thresholds.
- Stage-loss evidence is used to explain filtering behavior, not to estimate final model performance.

## 5. Ground-Truth & Measurement Readiness

Current ground-truth status remains conservative. Candidate pairs are preserved for review, but none are measurement-ready until runtime availability and label/mapping validity are confirmed.

| target | candidate_pair_rows | row_level_pair_count | distinct_files | measurement_ready_pair_count | measurement_readiness_status | zero_type_or_denominator_status | next_required_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Symptom | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_current_demonstrable_proof_of_life | Keep under explicit proof-of-life review; do not infer from broad narrative text. |
| Object Part | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Damage | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Cause | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| Activity | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| FLOC leaf segment | 0 | 0 | 0 | 0 | no_current_measurement_denominator | supporting_vocabulary_not_record_label | Validate whether the glossary and KKS support are sufficient for ML/NLP use. |
| Activity Type | 36 | 379593 | 1 | 0 | no_current_measurement_denominator | pending_controlled_mat_source | Confirm the controlled source and mapping rules before treating this target as measurable. |

- Measurement-ready pair rows after conservative classification: `0`.
- Unknown opportunity rows preserved for later semantic reconciliation: `802`.
- Reference/catalog evidence is useful for matching and rule design, but it does not create a record-level measurement denominator.
- Agent inference is never used as a label.

## 6. Target-Level Feasibility Assessment

This section is intentionally written as target-level evidence readiness. It does not claim final feasibility, coverage, or confidence because validated denominators are not yet established.

### 6.1 Symptom

- Available source signal: `near_zero_current_evidence`.
- Runtime usability: `not_demonstrated`.
- Ground-truth / mapping support: `not_demonstrated`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `not_demonstrable_with_current_evidence`.
- Recommended method direction: `blocked_pending_new_evidence_or_sme_proof_of_life`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: No current demonstrable proof-of-life under available evidence.
- Input needed from: SME / technical lead / field matrix owner

### 6.2 Object Part

- Available source signal: `external_fault_code_signal_not_mapped_to_current_catalog`.
- Runtime usability: `not_demonstrated`.
- Ground-truth / mapping support: `not_demonstrated`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `candidate_signal_requires_vocab_mapping`.
- Recommended method direction: `requires_controlled_fault_vocabulary_before_method_selection`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed.
- Input needed from: OEM SME / controls owner / mapping owner

### 6.3 Damage

- Available source signal: `external_fault_code_signal_not_mapped_to_current_catalog`.
- Runtime usability: `not_demonstrated`.
- Ground-truth / mapping support: `not_demonstrated`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `candidate_signal_requires_vocab_mapping`.
- Recommended method direction: `requires_controlled_fault_vocabulary_before_method_selection`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed.
- Input needed from: OEM SME / controls owner / mapping owner

### 6.4 Cause

- Available source signal: `limited_or_uncertain_signal`.
- Runtime usability: `candidate_requires_runtime_validation`.
- Ground-truth / mapping support: `metadata_or_agent_inference_not_label`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `partial_candidate_requires_validation`.
- Recommended method direction: `candidate_pending_ground_truth_and_runtime_validation`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: Runtime availability and record-level label or validated mapping support are not closed.
- Input needed from: SME / mapping owner / runtime application owner

### 6.5 Activity

- Available source signal: `candidate_text_code_signal`.
- Runtime usability: `candidate_requires_runtime_validation`.
- Ground-truth / mapping support: `metadata_or_agent_inference_not_label`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `partial_candidate_requires_validation`.
- Recommended method direction: `candidate_pending_ground_truth_and_runtime_validation`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: Runtime availability and record-level label or validated mapping support are not closed.
- Input needed from: SME / mapping owner / runtime application owner

### 6.6 FLOC leaf segment

- Available source signal: `provisional_glossary_or_supporting_signal`.
- Runtime usability: `not_demonstrated`.
- Ground-truth / mapping support: `not_demonstrated`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `insufficient_current_evidence`.
- Recommended method direction: `rules_or_classifier_candidate_with_kks_supporting_validator`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: Glossary or KKS support must be validated as ML/NLP signal, not resolver.
- Input needed from: SAP functional owner / SME / technical lead

### 6.7 Activity Type

- Available source signal: `pending_controlled_source_signal`.
- Runtime usability: `pending_controlled_source_confirmation`.
- Ground-truth / mapping support: `pending_controlled_source_confirmation`.
- Measurable target status: `not_currently_measurable`.
- Current measurement-ready pair rows: `0`.
- Derivability assessment: `blocked_pending_controlled_source`.
- Recommended method direction: `blocked_pending_controlled_mat_source`.
- Coverage/confidence status: `not_estimated_no_validated_denominator`.
- Primary blocker: Controlled source for activity type code remains unconfirmed.
- Input needed from: OEM SME / mapping owner / technical lead

## 7. Cross-Target Findings & Data Gaps

Cross-target findings show that the principal current risk is not lack of text signal; it is unresolved target relevance, runtime usability, and label/mapping confirmation.

| finding | affected_targets | current_evidence | interpretation | required_action |
| --- | --- | --- | --- | --- |
| measurement_denominator_not_established | all | 0 measurement-ready pair rows | No target can yet receive accuracy, coverage, or final feasibility claims. | Validate real observed labels or SME-confirmed mappings by target. |
| unknown_text_code_opportunities_preserved | all_pending_split | 802 unknown opportunity rows | This is the largest unresolved bucket and may change target-level conclusions after semantic reconciliation. | Split by target relevance, source role, runtime availability, and evidence type. |
| external_fault_code_vocabulary_gap | Damage/Cause/Activity/Object Part possible, pending SME | 602 structured rows, 79 distinct numeric fault-code tokens | Structured external fault-code signal exists, but it does not currently map to the loaded Wind S/B/C/5/A catalog vocabulary. | Ask SME or mapping owner to identify the controlling source and SAP equivalence, if any. |
| runtime_availability_not_closed | all | candidate signals are from historical files and parsed artifacts | A candidate field is not usable by the engine until confirmed available at runtime. | Runtime app owner confirms available fields and stable extraction path. |
| catalog_scope_gap | FLOC leaf segment; Activity Type | S/B/C/5/A vocabulary loaded; FLOC and MAT require separate controlled sources | The five Wind catalog targets are not sufficient to validate FLOC or Activity Type. | Confirm FLOC vocabulary sufficiency and the controlled MAT source. |
| symptom_proof_of_life_guardrail | Symptom | near-zero evidence across lexical, quality, Field Matrix, and ground-truth passes | Symptom remains no-current-demonstrable-proof-of-life, not a final impossibility claim. | SME or source owner provides proof-of-life example if one exists. |
| field_matrix_is_not_record_level_ground_truth | Object Part; Damage; Cause; Symptom | Field Matrix rates are treated as profiling/mapping coverage indicators | Coverage rates do not automatically provide record-level labels for model measurement. | Field Matrix owner confirms whether rates represent mapping coverage or validated labels. |
| parser_issue_information_loss_bucket | unknown_until_triage_closed | 0 parser issues on tabular files | Parser issues are the remaining probable information-loss bucket after expected non-tabular handling. | Review parser issue files and decide whether additional parsers are needed. |
| denominators_must_remain_block_specific | all | inventory, tabular/structured scan, PDF extraction, and pair discovery use different denominators | Combining file counts across passes without labels can overstate or understate evidence. | Report files_listed, files_read_ok, files_failed, and zero_type per source block. |

Open gap register:

| gap_id | gap | type | targets | severity | owner_needed | decision_needed |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | No measurement-ready denominator | label_mapping_gap | all | high | SME / mapping owner | Confirm record-level labels or validated mappings. |
| G02 | Unknown text-code opportunities not split by target | semantic_reconciliation_gap | all | high | ML / SME / mapping owner | Classify unknown opportunities before promoting them. |
| G03 | External fault-code vocabulary not identified | controlled_vocabulary_gap | Damage/Cause/Activity/Object Part possible | high | SME / source owner / SAP mapping owner | Identify controlling vocabulary and SAP equivalence. |
| G04 | Runtime availability not validated | runtime_gap | all | high | runtime app owner | Confirm whether candidate fields exist at engine runtime. |
| G05 | Activity Type controlled source pending | controlled_source_gap | Activity Type | high | source owner / SME | Confirm MAT/activity-type controlled source and mapping rules. |
| G06 | FLOC support is not a label | target_specific_validation_gap | FLOC leaf segment | medium | SME / SAP functional owner | Confirm whether glossary/KKS support is sufficient and runtime-available. |
| G07 | Symptom proof-of-life not demonstrated | proof_of_life_gap | Symptom | high | SME / Field Matrix owner | Provide validated example or accept current no-proof-of-life status. |
| G08 | Remaining parser issues on tabular files | parser_gap | unknown | medium | ML engineering | Fix parser coverage or mark affected files out of scope. |

External PDF-derived fault-code evidence is a material finding: the parser recovered structured fault-code signal, but those codes do not currently map to the loaded S/B/C/5/A vocabulary. This points to a separate controlled fault/alarm vocabulary or crosswalk that requires SME or source-owner confirmation.

## 8. Feasibility Matrix & Recommended Technical Direction

The matrix below is directional. It supports prioritization and next-step planning, but not final go/no-go feasibility decisions.

| target | available_source_signal | measurable_target_status | recommended_method | coverage_confidence_status | primary_blocker |
| --- | --- | --- | --- | --- | --- |
| Symptom | near_zero_current_evidence | not_currently_measurable | blocked_pending_new_evidence_or_sme_proof_of_life | not_estimated_no_validated_denominator | No current demonstrable proof-of-life under available evidence. |
| Object Part | external_fault_code_signal_not_mapped_to_current_catalog | not_currently_measurable | requires_controlled_fault_vocabulary_before_method_selection | not_estimated_no_validated_denominator | Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed. |
| Damage | external_fault_code_signal_not_mapped_to_current_catalog | not_currently_measurable | requires_controlled_fault_vocabulary_before_method_selection | not_estimated_no_validated_denominator | Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed. |
| Cause | limited_or_uncertain_signal | not_currently_measurable | candidate_pending_ground_truth_and_runtime_validation | not_estimated_no_validated_denominator | Runtime availability and record-level label or validated mapping support are not closed. |
| Activity | candidate_text_code_signal | not_currently_measurable | candidate_pending_ground_truth_and_runtime_validation | not_estimated_no_validated_denominator | Runtime availability and record-level label or validated mapping support are not closed. |
| FLOC leaf segment | provisional_glossary_or_supporting_signal | not_currently_measurable | rules_or_classifier_candidate_with_kks_supporting_validator | not_estimated_no_validated_denominator | Glossary or KKS support must be validated as ML/NLP signal, not resolver. |
| Activity Type | pending_controlled_source_signal | not_currently_measurable | blocked_pending_controlled_mat_source | not_estimated_no_validated_denominator | Controlled source for activity type code remains unconfirmed. |

## 9. Required Inputs, Owners & Decisions

The following inputs are needed before any target can move from evidence readiness to measured feasibility.

| gap_id | gap | targets | severity | owner_needed | decision_needed |
| --- | --- | --- | --- | --- | --- |
| G01 | No measurement-ready denominator | all | high | SME / mapping owner | Confirm record-level labels or validated mappings. |
| G02 | Unknown text-code opportunities not split by target | all | high | ML / SME / mapping owner | Classify unknown opportunities before promoting them. |
| G03 | External fault-code vocabulary not identified | Damage/Cause/Activity/Object Part possible | high | SME / source owner / SAP mapping owner | Identify controlling vocabulary and SAP equivalence. |
| G04 | Runtime availability not validated | all | high | runtime app owner | Confirm whether candidate fields exist at engine runtime. |
| G05 | Activity Type controlled source pending | Activity Type | high | source owner / SME | Confirm MAT/activity-type controlled source and mapping rules. |
| G06 | FLOC support is not a label | FLOC leaf segment | medium | SME / SAP functional owner | Confirm whether glossary/KKS support is sufficient and runtime-available. |
| G07 | Symptom proof-of-life not demonstrated | Symptom | high | SME / Field Matrix owner | Provide validated example or accept current no-proof-of-life status. |
| G08 | Remaining parser issues on tabular files | unknown | medium | ML engineering | Fix parser coverage or mark affected files out of scope. |

- Confirm which candidate signals are available at runtime.
- Confirm which text-code relationships are real observed labels or SME-validated record-level mappings.
- Confirm the controlled source for Activity Type / MAT.
- Provide or confirm the controlled vocabulary/crosswalk for external fault-code signals.
- Continue treating Symptom as no-current-demonstrable-proof-of-life unless SME evidence overturns it.

## 10. Conclusions & Next Steps

This draft is ready as an evidence-based technical memo, with explicit limitations.

- Proceed with SME/runtime validation before any modeling work.
- Use unknown opportunities as a preserved discovery backlog, not as target evidence.
- Use the external fault-code appendix as a concrete SME ask for vocabulary ownership and crosswalk confirmation.
- Do not estimate model accuracy or coverage until a measurement denominator exists.
- After SME validation, update the target matrix and only then decide whether rules, NER, classical ML, or hybrid methods are justified per target.

## Appendices

### Appendix A. Source and Effective-Read Inventory

| source_block | files_listed | files_read_ok | files_failed | candidate_pairs_found | measurement_ready_pairs | zero_type |
| --- | --- | --- | --- | --- | --- | --- |
| inventoried_source_universe | 575 |  |  |  | 0 | not_applicable_inventory_denominator |
| safe_content_pair_discovery | 147 | 147.0 | 0.0 | 838.0 | 0 | candidate_pairs_found_not_measurement_ready |
| pdf_assets_of_concern_parser | 394 | 394.0 | 0.0 | 602.0 | 0 | candidate_pairs_found_controlled_vocabulary_pending |

### Appendix B. Ground-Truth Evidence Tables

The evidence tables are included as denominator-readiness evidence, not as final performance evidence.

| target | candidate_pair_rows | row_level_pair_count | distinct_files | measurement_ready_pair_count | measurement_readiness_status | zero_type_or_denominator_status | next_required_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Symptom | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_current_demonstrable_proof_of_life | Keep under explicit proof-of-life review; do not infer from broad narrative text. |
| Object Part | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Damage | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Cause | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| Activity | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| FLOC leaf segment | 0 | 0 | 0 | 0 | no_current_measurement_denominator | supporting_vocabulary_not_record_label | Validate whether the glossary and KKS support are sufficient for ML/NLP use. |
| Activity Type | 36 | 379593 | 1 | 0 | no_current_measurement_denominator | pending_controlled_mat_source | Confirm the controlled source and mapping rules before treating this target as measurable. |

### Appendix C. Target Reconciliation Matrix

| target | available_source_signal | runtime_usability | ground_truth_or_mapping_support | measurable_target_status | measurement_ready_pair_rows | preliminary_mapping_rows | classified_pair_rows | row_level_pair_count | derivability_assessment | recommended_method | coverage_confidence_status | primary_blocker | needed_from_whom | field_matrix_reference | raw_operational_values_emitted |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Symptom | near_zero_current_evidence | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | not_demonstrable_with_current_evidence | blocked_pending_new_evidence_or_sme_proof_of_life | not_estimated_no_validated_denominator | No current demonstrable proof-of-life under available evidence. | SME / technical lead / field matrix owner | 0 resolvable mappings in profiling evidence. | False |
| Object Part | external_fault_code_signal_not_mapped_to_current_catalog | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | candidate_signal_requires_vocab_mapping | requires_controlled_fault_vocabulary_before_method_selection | not_estimated_no_validated_denominator | Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed. | OEM SME / controls owner / mapping owner | Long-tail and singleton behavior reported; record-level mappings still need confirmation. | False |
| Damage | external_fault_code_signal_not_mapped_to_current_catalog | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | candidate_signal_requires_vocab_mapping | requires_controlled_fault_vocabulary_before_method_selection | not_estimated_no_validated_denominator | Fault-code vocabulary owner or crosswalk to SAP catalog is not confirmed. | OEM SME / controls owner / mapping owner | Partial profiling or mapping coverage reported; record-level labels not demonstrated here. | False |
| Cause | limited_or_uncertain_signal | candidate_requires_runtime_validation | metadata_or_agent_inference_not_label | not_currently_measurable | 0 | 3 | 36 | 379593 | partial_candidate_requires_validation | candidate_pending_ground_truth_and_runtime_validation | not_estimated_no_validated_denominator | Runtime availability and record-level label or validated mapping support are not closed. | SME / mapping owner / runtime application owner | Low profiling or mapping coverage reported; record-level labels not demonstrated here. | False |
| Activity | candidate_text_code_signal | candidate_requires_runtime_validation | metadata_or_agent_inference_not_label | not_currently_measurable | 0 | 3 | 36 | 379593 | partial_candidate_requires_validation | candidate_pending_ground_truth_and_runtime_validation | not_estimated_no_validated_denominator | Runtime availability and record-level label or validated mapping support are not closed. | SME / mapping owner / runtime application owner | No final measured derivability conclusion in this pass. | False |
| FLOC leaf segment | provisional_glossary_or_supporting_signal | not_demonstrated | not_demonstrated | not_currently_measurable | 0 | 0 | 0 | 0 | insufficient_current_evidence | rules_or_classifier_candidate_with_kks_supporting_validator | not_estimated_no_validated_denominator | Glossary or KKS support must be validated as ML/NLP signal, not resolver. | SAP functional owner / SME / technical lead | Glossary-based support exists; KKS is supporting validator only. | False |
| Activity Type | pending_controlled_source_signal | pending_controlled_source_confirmation | pending_controlled_source_confirmation | not_currently_measurable | 0 | 3 | 36 | 379593 | blocked_pending_controlled_source | blocked_pending_controlled_mat_source | not_estimated_no_validated_denominator | Controlled source for activity type code remains unconfirmed. | OEM SME / mapping owner / technical lead | Controlled MAT/activity-type source pending. | False |

### Appendix D. Prospection / Threshold / Stage-Loss Evidence

The prospection history supports methodological defensibility. It shows why broad text availability was insufficient and why controlled vocabulary, threshold sensitivity, and stage-loss accounting were required. These artifacts are not accuracy measurements.

- Vocabulary overlap rows: `2`.
- Preliminary target mapping rows: `9`.
- Dual-threshold interpretation remains methodological: lower threshold for discovery, higher threshold for high-specificity sanity checks.

### Appendix E. Parser, PDF and Remaining Data-Quality Issues

External fault-code profile, sanitized:

| fault_code_hash | fault_code_length | fault_code_pattern | frequency | associated_event_count | raw_operational_values_emitted |
| --- | --- | --- | --- | --- | --- |
| 0fecf9247f3ddc84 | 3 | numeric | 272 | 27 | False |
| 210e3b160c355818 | 3 | numeric | 36 | 8 | False |
| b8aed072d29403ec | 3 | numeric | 34 | 12 | False |
| 38d66d9692ac5900 | 3 | numeric | 22 | 10 | False |
| c8c9cad7b920b50f | 3 | numeric | 16 | 7 | False |
| 37834f2f25762f23 | 3 | numeric | 15 | 8 | False |
| 7045d16ae7f043ec | 3 | numeric | 14 | 3 | False |
| eeca91fd439b6d5e | 3 | numeric | 13 | 6 | False |
| 8cd2510271575d84 | 3 | numeric | 12 | 4 | False |
| f8818b67ab25419a | 3 | numeric | 8 | 5 | False |
| 16dc368a89b428b2 | 3 | numeric | 7 | 5 | False |
| 8527a891e2241369 | 2 | numeric | 7 | 2 | False |
| d4ee9f58e5860574 | 3 | numeric | 7 | 4 | False |
| d48ff4b2f68a10fd | 3 | numeric | 7 | 4 | False |
| dbb1ded63bc70732 | 3 | numeric | 6 | 3 | False |
| 2c7d5490e6050836 | 3 | numeric | 6 | 3 | False |
| fa2b7af0a811b9ac | 3 | numeric | 6 | 4 | False |
| 9b871512327c09ce | 3 | numeric | 6 | 4 | False |
| 5ec1a0c99d428601 | 3 | numeric | 5 | 2 | False |
| 718127812c05853f | 3 | numeric | 4 | 2 | False |

Parser and data-quality caveats:

- PDF parser results are structured and sanitized; raw operational text is not emitted here.
- External fault-code values are represented in sanitized profile form for versioned outputs.
- Remaining data-quality issues should be handled as parser or source-owner follow-up, not as negative feasibility conclusions.
