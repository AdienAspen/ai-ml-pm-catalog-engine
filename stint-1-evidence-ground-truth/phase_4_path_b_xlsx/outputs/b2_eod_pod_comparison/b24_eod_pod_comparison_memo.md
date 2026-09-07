# B2.4 EOD vs POD Structural Comparison

## Scope

This pass compares snapshot workbook families after B2.1 characterization. It reports structure and candidate text density only; it does not inspect or emit raw operational text.

## Summary

- Files compared: `127`
- EOD files: `83`
- POD files: `31`
- Unprefixed snapshot files: `12`
- Daily/EOD ambiguous files: `1`
- Known-positive validation: `pending_not_provided_for_b2_xlsx`
- Symptom availability verdict: `structural_opportunity_only_content_validation_pending`

## By Document Type

| doc_type | files | files_with_candidate_text | candidate_text_file_rate | candidate_text_rows | files_with_issue_or_notes | issue_or_notes_file_rate | issue_or_notes_rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EOD | 83 | 83 | 1.0000 | 1344 | 83 | 1.0000 | 1344 |
| POD | 31 | 31 | 1.0000 | 429 | 31 | 1.0000 | 429 |
| daily_or_eod | 1 | 1 | 1.0000 | 23 | 1 | 1.0000 | 23 |
| snapshot_unprefixed | 12 | 12 | 1.0000 | 146 | 12 | 1.0000 | 146 |

## Interpretation

B2.4 can identify where prose-like structures exist, but it cannot conclude that a source contains Symptom, Cause, Damage, or Activity evidence until a known-positive workbook case and content-level extraction are validated.

If issue/notes structures are present in EOD/POD, they remain candidates for B2.3 extraction. If absent, that absence is not interpreted until the template variant has a validated positive/negative control.

raw_operational_values_emitted: false
