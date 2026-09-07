# B2.5 Grouping Refinement

## Scope

This pass refines B2 event grouping and re-anchors lexical evidence on concatenated group text. It does not emit raw operational values and does not promote any candidate to a denominator.

## Grouping Comparison

- Baseline date-sensitive events from B2.2b: `1843`
- Refined events: `1857`
- Refined minus baseline delta: `14`
- Duration-present rows: `115`
- Duration-grouped events: `109`
- Fallback grouped events: `1748`

## By Document Type

| doc_type | snapshot_text_rows | baseline_date_sensitive_events | refined_events | refined_compression_ratio | duration_present_rows | duration_grouped_events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| EOD | 1344 | 1230 | 1246 | 1.078652 | 115 | 109 |
| POD | 429 | 411 | 411 | 1.043796 | 0 | 0 |
| daily_or_eod | 69 | 54 | 54 | 1.277778 | 0 | 0 |
| snapshot_unprefixed | 146 | 146 | 146 | 1.0 | 0 | 0 |

## Re-Anchored Evidence By Target

| target | status | evidence_rows | refined_event_units | canonical_concepts | grouped_text_rows |
| --- | --- | ---: | ---: | ---: | ---: |
| Activity | b25_grouped_text_candidate_requires_review | 78 | 74 | 8 | 81 |
| Cause | b25_grouped_text_candidate_requires_review | 70 | 57 | 15 | 72 |
| Damage | b25_grouped_text_candidate_requires_review | 124 | 110 | 15 | 139 |
| Object Part | b25_grouped_text_candidate_requires_review | 701 | 488 | 45 | 736 |
| Symptom | b25_symptom_like_candidate_source_unconfirmed | 584 | 365 | 6 | 585 |

## Interpretation

The refined grouping is conservative where duration is unavailable. Duration-derived incident starts are used only when a parsable duration and asset reference are present; all other rows retain date-sensitive fallback grouping.

Grouping simulates the behavior that would belong to SyncHub in production. It is performed here only because STINT_1 needs constituted event units before defining reviewable evidence.

raw_operational_values_emitted: false
