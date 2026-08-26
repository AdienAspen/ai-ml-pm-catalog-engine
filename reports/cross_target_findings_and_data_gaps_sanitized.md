# Asset ML Feasibility - Cross-Target Findings and Data Gaps

## Scope

This section consolidates cross-target findings and data gaps for the feasibility draft. It is an evidence-readiness section, not a model-training result, accuracy estimate, or final feasibility conclusion.

No raw operational client values are emitted.

## Current Cross-Target Position

- Inventoried files: 575
- Schema columns profiled: 1914
- Candidate text/signal columns: 164
- Controlled catalog terms loaded for Wind S/B/C/5/A: 13986
- Safe content pair opportunity rows: 838
- Unknown opportunity rows preserved: 802
- PDF-derived external fault-code rows: 602
- Distinct external fault-code tokens: 79
- Measurement-ready pair rows: 0

## Cross-Target Findings

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

## Gap Register

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

## Field Matrix Reconciliation

| target | field_matrix_signal | current_reconciliation | interpretation |
| --- | --- | --- | --- |
| Symptom | 0 resolvable mappings in profiling evidence | aligned_near_zero | Supports no-current-demonstrable-proof-of-life, subject to SME override. |
| Object Part | long-tail/singleton mapping difficulty indicator | requires_record_level_validated_mapping | Reference coverage does not yet create measurement denominator. |
| Damage | partial profiling/mapping coverage indicator | rates_exist_but_record_level_labels_not_confirmed | Needs label/mapping validation before coverage or confidence estimates. |
| Cause | low profiling/mapping coverage indicator | rates_exist_but_record_level_labels_not_confirmed | Needs label/mapping validation before coverage or confidence estimates. |
| Activity | no final measured derivability conclusion in this pass | candidate_signal_pending_validation | Candidate evidence exists, but runtime and label/mapping validation are pending. |
| FLOC leaf segment | glossary/supporting signal | supporting_signal_not_label | KKS can support/validate interpretation; it must not resolve or build hierarchy. |
| Activity Type | controlled MAT source pending | blocked_pending_controlled_source | Cannot be measurement-ready until controlled source and mapping rules are confirmed. |

## Source Denominator Context

| source_block | files_listed | files_read_ok | files_failed | candidate_pairs_found | measurement_ready_pairs | zero_type |
| --- | --- | --- | --- | --- | --- | --- |
| inventoried_source_universe | 575 |  |  |  | 0 | not_applicable_inventory_denominator |
| safe_content_pair_discovery | 147 | 147 | 0 | 838 | 0 | candidate_pairs_found_not_measurement_ready |
| pdf_assets_of_concern_parser | 394 | 394 | 0 | 602 | 0 | candidate_pairs_found_controlled_vocabulary_pending |

## Unresolved Buckets

| bucket | candidate_pair_rows | measurement_ready_pair_rows | status | next_required_action |
| --- | --- | --- | --- | --- |
| unknown_text_code_opportunities | 802 | 0 | preserved_pending_semantic_reconciliation | Split by target relevance, runtime availability, and evidence type before promotion. |
| external_fault_code_signal | 602 | 0 | controlled_source_required | Confirm the owning controlled vocabulary and SAP equivalence with SME or mapping owner. |

## Target-Level Caveats

| target | candidate_pair_rows | row_level_pair_count | distinct_files | measurement_ready_pair_count | measurement_readiness_status | zero_type_or_denominator_status | next_required_action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Symptom | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_current_demonstrable_proof_of_life | Keep under explicit proof-of-life review; do not infer from broad narrative text. |
| Object Part | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Damage | 0 | 0 | 0 | 0 | no_current_measurement_denominator | no_candidate_pair_found_after_successful_read_or_not_target_specific | Do not interpret as zero derivability; confirm source coverage and target-specific labels. |
| Cause | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| Activity | 36 | 379593 | 1 | 0 | candidate_signal_without_measurement_denominator | requires_label_or_mapping_validation | Validate whether candidate pairs are runtime-available record-level labels or validated mappings. |
| FLOC leaf segment | 0 | 0 | 0 | 0 | no_current_measurement_denominator | supporting_vocabulary_not_record_label | Validate whether the glossary and KKS support are sufficient for ML/NLP use. |
| Activity Type | 36 | 379593 | 1 | 0 | no_current_measurement_denominator | pending_controlled_mat_source | Confirm the controlled source and mapping rules before treating this target as measurable. |

## Required Committee Decisions

- Confirm whether the evidence taxonomy is acceptable for the final assessment.
- Confirm owners for runtime availability checks by source family.
- Confirm whether Field Matrix rates represent coverage/profiling indicators or validated record-level labels.
- Confirm the controlled source for external fault-code values and whether they map to any target.
- Confirm whether unknown text-code opportunities should be split by SME review, rule prototypes, or both.
- Confirm whether remaining parser issue files must be remediated before the report is finalized.

## Mandatory Cautions

- Reference catalogs are not ground truth.
- Unknown opportunities are preserved but not measurement-ready.
- Zero measurement-ready evidence does not automatically mean zero derivability.
- Runtime availability must be confirmed before candidate evidence can become implementation evidence.
- KKS may support or validate FLOC interpretation; it must not resolve or construct hierarchy.
- Prospection thresholds are not model thresholds and not endpoint thresholds.

## Non-Goals

- No model training was performed.
- No model accuracy estimate was produced.
- No final feasibility conclusion is included.
- No raw operational client values were emitted.
