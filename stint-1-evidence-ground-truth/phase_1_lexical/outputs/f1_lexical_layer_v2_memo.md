# F1 - Lexical Layer v2 Bootstrap

## Purpose

This pass starts Phase 1 by converting the provisional STINT_1.1 lexical seed into an auditable STINT_1 working layer.

It does not freeze the lexical layer and does not emit source-derived terms.

## Mandatory Pre-Filter Count

| word_length | contextual_rows | distinct_observed_term_keys | distinct_normalised_term_keys |
|---:|---:|---:|---:|
| 1 | 3081 | 1477 | 1477 |
| 2 | 5579 | 4365 | 4365 |
| 3 | 5575 | 4797 | 4797 |

## Lexical Layer v2 Status

- Source contextual rows: 14235
- Source distinct observed term keys: 10639
- V2 retained rows: 7790
- V2 distinct term keys: 5710
- Rows removed by singleton unknown filter: 6210
- 300-800 concepts remains a sanity/timebox heuristic, not a success criterion.
- `source_text_field` is preserved for every retained term.
- `label_generation_method` and `evaluation_independence` are populated from the first F1 output.

## Target Distribution

- Activity: 879
- Activity Type: 11
- Cause: 175
- Damage: 347
- Object Part: 1492
- Symptom: 286
- unknown: 4600

## Status Distribution

- provisional_pending_domain_grouping: 1066
- provisional_singleton_domain_signal: 2124
- unresolved: 4600

## Semantic Normalisation

`SEMANTIC_NORMALISATION` remains structurally present but not fully populated: WMEP and NREL GRD are recorded as `source_capture_pending`.

## Interpretation

F1 can proceed with filtering and domain grouping, but this first artifact is a working layer, not a frozen reference object.

The high coverage of `description_extended` applies to the structured path only. PDF-derived evidence stays in `event_structural` and must not be mixed with planned/reactive denominators.
