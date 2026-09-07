# F5.1a B2 Symptom Concept Thread

## Scope

This pass resolves the B2 Symptom-like thread at concept level. It uses B2.5 grouped snapshot candidates and emits only sanitized concept identifiers and counts.

## Summary

- Symptom concepts evaluated: `6`
- Symptom evidence rows: `584`
- Symptom refined event units: `365`
- Observed-condition-like concepts: `0`
- Generic/unusable concepts: `6`
- Blind review needed: `False`
- Blind review event sample size: `0`
- Thread verdict: `discard_thread_as_generic_noise`

## Concept-Level Verdict

| concept_id | vocabulary_owner | semantic_level | evidence_rows | refined_event_units | term_keys | f51a_verdict |
| --- | --- | --- | ---: | ---: | ---: | --- |
| CV-SAP-37ae53f5f441 | SAP_MAPPING | nan | 211 | 211 | 1 | generic_or_unusable_for_symptom_thread |
| CV-SAP-b993f8f0453b | SAP_MAPPING | nan | 220 | 210 | 3 | generic_or_unusable_for_symptom_thread |
| CV-SAP-eec9953aaabc | SAP_MAPPING | nan | 126 | 126 | 1 | generic_or_unusable_for_symptom_thread |
| CV-SAP-c99f29f99517 | SAP_MAPPING | nan | 13 | 13 | 2 | generic_or_unusable_for_symptom_thread |
| CV-SAP-4818bf0de4d4 | SAP_MAPPING | nan | 9 | 9 | 1 | generic_or_unusable_for_symptom_thread |
| CV-SAP-f22e6d37f9d8 | SAP_MAPPING | nan | 5 | 5 | 1 | generic_or_unusable_for_symptom_thread |

## Interpretation

F5.1a does not promote Symptom. It only decides whether the concentrated B2 six-concept thread is worth blind review.

Any concept classified as condition-like remains `source_unconfirmed`; only a blind review of events can determine whether it reflects an observed pre-intervention symptom or post/status wording.

raw_operational_values_emitted: false
