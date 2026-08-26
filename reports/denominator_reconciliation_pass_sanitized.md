# Asset Maintenance Bridge ML Feasibility - Denominator Reconciliation Pass

## Scope

Short accounting pass to verify four denominator and attribution questions raised during Draft 1 review. This pass uses sanitized generated artifacts only and emits no raw operational values.

## Reconciliation Checks

| check_id | issue | observed_values | verification | calculation | reconciled_status | report_action |
| --- | --- | --- | --- | --- | --- | --- |
| D01 | 838_vs_910_candidate_pair_rows | safe_content_rows=838; classified_rows=910 | 36 safe-content rows carried multi-target hint 'Cause;Activity;Activity Type'; classification expands each into 3 target rows. | 838 + (36 * 2 expansion_delta) = 910 | reconciled_target_expansion_not_denominator_change | Label 838 as source opportunity rows and 910 as target-expanded classification rows. |
| D02 | Cause_Activity_ActivityType_uniformity | 36 structures and 379593 row-level pairs repeated across three targets | The repeated counts arise from shared multi-target expansion, not from three independent target-specific denominators. | Same 36 source opportunities are expanded to Cause, Activity, and Activity Type. | reconciled_shared_multitarget_expansion_requires_semantic_validation | Do not present the three rows as independent evidence; keep them pending target disambiguation. |
| D03 | parser_gap_G08_vs_zero_parser_issues | current_parser_issue_on_tabular_files=0 | Current cross-target summary reports zero tabular parser issues; any G08 gap-register row that still claims remaining tabular parser issues is stale unless supported by the latest triage. | Use latest parser triage/cross-target summary as controlling source. | stale_gap_language_needs_report_update | Update or retire G08 language in the draft if latest triage confirms zero tabular parser issues. |
| D04 | 147_vs_157_files | structural_attempted=157; safe_content_pair_files=147 | Structural scan included eligible structured/tabular files across roles. Safe content pair discovery intentionally scanned source_data only. | 157 structural attempted = 147 source_data + 4 mapping_doc + 6 reference_data. | reconciled_scope_filter | State that 10 non-source files were excluded from pair discovery by design. |

## Target Uniformity Reconciliation

| target | classified_pair_rows | row_level_pair_count | distinct_files | measurement_ready_rows | source_of_uniformity | interpretation |
| --- | --- | --- | --- | --- | --- | --- |
| Cause | 36 | 379593 | 1 | 0 | shared_multi_target_hint_expansion | candidate_for_semantic_disambiguation_not_independent_denominator |
| Activity | 36 | 379593 | 1 | 0 | shared_multi_target_hint_expansion | candidate_for_semantic_disambiguation_not_independent_denominator |
| Activity Type | 36 | 379593 | 1 | 0 | shared_multi_target_hint_expansion | candidate_for_semantic_disambiguation_not_independent_denominator |

## File Denominator Reconciliation

| scope | files_attempted | source_data | mapping_doc | reference_data | purpose |
| --- | --- | --- | --- | --- | --- |
| basic_structural_scan | 157 | 147 | 4 | 6 | read/profile eligible structured or tabular files across roles |
| safe_content_pair_discovery | 147 | 147 | 0 | 0 | discover text-code opportunities only in productive source_data |
| excluded_from_pair_discovery | 10 | 0 | 4 | 6 | non-source roles intentionally excluded from source-data pair discovery |

## Current G08 / Parser Gap Rows

| gap_id | gap | type | targets | severity | owner_needed | decision_needed |
| --- | --- | --- | --- | --- | --- | --- |
| G08 | Remaining parser issues on tabular files | parser_gap | unknown | medium | ML engineering | Fix parser coverage or mark affected files out of scope. |

## Interpretation

- `838` and `910` are different denominators: `838` source opportunity rows vs. `910` target-expanded classification rows.
- Cause, Activity, and Activity Type uniformity is explained by shared multi-target expansion; it is not independent target evidence.
- `147` vs. `157` is a scope difference: pair discovery used only source_data, while structural scan also profiled mapping/reference files.
- The parser gap language should be governed by the latest triage/cross-target summary; if tabular parser issues are zero, stale G08 language should be updated before the next draft.

## Non-Goals

- No model training was performed.
- No model accuracy estimate was produced.
- No final feasibility conclusion is included.
- No raw operational client values were emitted.