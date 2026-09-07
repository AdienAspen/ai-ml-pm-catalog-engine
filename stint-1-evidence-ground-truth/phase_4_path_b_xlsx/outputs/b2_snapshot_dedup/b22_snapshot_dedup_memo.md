# B2.2 Snapshot Deduplication

## Scope

This pass estimates event compression for B2 snapshot workbooks after the XLSX known-positive control passed. It keeps `snapshot_rows` and `estimated_events` separate.

## Summary

- Files scanned: `127`
- Snapshot rows: `1988`
- Estimated events: `460`
- Compression ratio: `4.321739`
- Date-sensitive estimated events: `1843`
- Date-sensitive compression ratio: `1.078676`
- Dedup method: `family_doc_type_asset_code_text_signature`

## By Document Type

| doc_type | snapshot_rows | estimated_events | compression_ratio | date_sensitive_events | date_sensitive_ratio | asset_ref_present_rate | code_ref_present_rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EOD | 1344 | 270 | 4.977778 | 1232 | 1.090909 | 0.96131 | 0.0 |
| POD | 429 | 106 | 4.04717 | 411 | 1.043796 | 0.986014 | 0.254079 |
| daily_or_eod | 69 | 54 | 1.277778 | 54 | 1.277778 | 0.492754 | 0.0 |
| snapshot_unprefixed | 146 | 30 | 4.866667 | 146 | 1.0 | 1.0 | 0.417808 |

## Interpretation

The non-date event key estimates persistence across daily snapshots. The date-sensitive key is provided as a conservative upper bound that avoids merging repeated work on different days.

No target evidence is promoted here. B2.2 only establishes deduplication accounting for downstream B2.3 extraction and weak supervision.

raw_operational_values_emitted: false
