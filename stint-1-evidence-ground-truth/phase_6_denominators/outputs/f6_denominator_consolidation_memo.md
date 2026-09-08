# F6 — Evidence Denominator Consolidation

## Nature

F6 does not generate new evidence. It consolidates the denominator status of evidence already produced by F3, F4 and F5.

## Counting Rule

- Path A: `estimated_event_key × target`
- B1 structured/textual: `physical_record_id × target`
- B2 snapshots: `refined_event_key × target`
- Evidence rows are not denominators.
- Path A, B1 and B2 are not globally aggregated.

## Contractual Denominator

A row is admitted only when all conditions hold: `evidence_type` in `real_observed_label` or `validated_mapping`, `tier = gold`, and `status = resolved`.

Current result: only `Activity Type / MAT` in B1 has admitted contractual units. All other targets are declared zero for the contractual denominator.

## Proxy POC Denominator

The proxy denominator is declared separately from the contractual denominator. In this corrected F6 pass, qualified reconstructed evidence is admitted to the proxy even when its terminal POC status is `requires_review`.

Everything derived from rules or embeddings remains non-contractual and must retain provenance and anti-circularity controls. `requires_review` blocks contractual use, but it does not automatically block proxy admission in a POC without SME closure.

## Target Summary

| Target | Contractual admitted by path | Proxy admitted by path | Proxy candidates by path | Status |
|---|---|---|---|---|
| Symptom | 0 | B2_WORKBOOKS:62;PATH_A_CONCERN_TABLE:68;PATH_A_NOTES:42;RELATIONAL_REASON:1827 | B2_WORKBOOKS:62;B2_WORKBOOK_SNAPSHOTS:365;LEXICAL_LAYER_V2_HIGH_BAND:41;PATH_A_CONCERN_TABLE:68;PATH_A_NOTES:42;RELATIONAL_REASON:1827 | proxy_denominator_available_poc_only_not_ground_truth |
| Object Part | 0 | B2_WORKBOOK_SNAPSHOTS:488;PATH_A_PDF_EVENTS:280 | B1_RELATIONAL_STRUCTURED:4079;B2_WORKBOOK_SNAPSHOTS:488;PATH_A_PDF_EVENTS:280 | proxy_denominator_available_poc_only_requires_review |
| Damage | 0 | B1_RELATIONAL_TEXTUAL:1263;B2_WORKBOOK_SNAPSHOTS:110;PATH_A_PDF_EVENTS:116 | B1_RELATIONAL_TEXTUAL:4477;B2_WORKBOOK_SNAPSHOTS:110;PATH_A_PDF_EVENTS:116 | proxy_denominator_available_poc_only_requires_review |
| Cause | 0 | B1_RELATIONAL_TEXTUAL:1250;B2_WORKBOOK_SNAPSHOTS:57;PATH_A_PDF_EVENTS:36 | B1_RELATIONAL_TEXTUAL:3273;B2_WORKBOOK_SNAPSHOTS:57;PATH_A_PDF_EVENTS:36 | proxy_denominator_available_poc_only_requires_review |
| Activity | 0 | B1_RELATIONAL_TEXTUAL:1215;B2_WORKBOOK_SNAPSHOTS:74;PATH_A_PDF_EVENTS:339 | B1_RELATIONAL_TEXTUAL:2846;B2_WORKBOOK_SNAPSHOTS:74;PATH_A_PDF_EVENTS:339 | proxy_denominator_available_poc_only_requires_review |
| FLOC leaf | 0 | 0 | B1_RELATIONAL_STRUCTURED:10749 | candidate_requires_alignment_to_valid_destination |
| Activity Type / MAT | B1_RELATIONAL_STRUCTURED:10749 | B1_RELATIONAL_STRUCTURED:10749 | B1_RELATIONAL_STRUCTURED:10749 | contractual_denominator_available_for_b1_only |

## Scope Statements

- Grouping simulates the upstream event constitution role that would belong to SyncHub in production. It is used here only to define auditable POC event units.
- POC metrics must never be presented as verified production accuracy.
- The contractual 95% accuracy requirement cannot be evaluated from the current reconstructed evidence layer except where a contractual denominator exists.
- FLOC leaf is an explicit zero, not a silent miss: joins exist internally, but no SAP/FLOC leaf alignment evidence has been produced. This carries to STINT_2.
- Symptom `B2_WORKBOOK_SNAPSHOTS` remains a diagnostic candidate only. Its 365 event units are excluded from proxy admission because F5.1a discarded that thread as generic catalog noise.
- Raw operational values emitted: `false`.
