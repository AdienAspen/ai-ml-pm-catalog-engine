# B2.2b Dedup Method Reconciliation

## Question

B2.2 produced two event counts from the same snapshot universe. This note defines both counts and declares which one B2.3 may use.

## Definitions

- `snapshot_rows`: extracted rows from validated workbook text structures.
- `estimated_event_key`: `family + doc_type + asset_key + code_key + text_signature`; it intentionally excludes date and therefore measures persistence clusters.
- `estimated_event_key_with_snapshot_date`: same key plus `snapshot_date_bucket`; it prevents merging similar rows that occur on different snapshot dates.

## Counts

- `snapshot_rows`: `1988`
- `estimated_events_without_date`: `460`
- `estimated_events_with_snapshot_date`: `1843`

## By Document Type

| doc_type | snapshot_rows | events_without_date | compression_without_date | events_with_date | compression_with_date |
| --- | ---: | ---: | ---: | ---: | ---: |
| EOD | 1344 | 270 | 4.977778 | 1232 | 1.090909 |
| POD | 429 | 106 | 4.04717 | 411 | 1.043796 |
| daily_or_eod | 69 | 54 | 1.277778 | 54 | 1.277778 |
| snapshot_unprefixed | 146 | 30 | 4.866667 | 146 | 1.0 |

## By Bucket

| family | doc_type | snapshot_rows | events_without_date | compression_without_date | events_with_date | compression_with_date |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| SNAPSHOT_FAMILY_001 | EOD | 1344 | 270 | 4.977778 | 1232 | 1.090909 |
| SNAPSHOT_FAMILY_002 | POD | 137 | 33 | 4.151515 | 121 | 1.132231 |
| SNAPSHOT_FAMILY_002 | daily_or_eod | 69 | 54 | 1.277778 | 54 | 1.277778 |
| SNAPSHOT_FAMILY_003 | POD | 292 | 73 | 4.0 | 290 | 1.006897 |
| SNAPSHOT_FAMILY_003 | snapshot_unprefixed | 146 | 30 | 4.866667 | 146 | 1.0 |

## Decision

`estimated_event_key` is retained as a persistence-cluster metric, not as the B2 denominator. It is useful to show repeated snapshot state, but it can merge separate events from different days.

B2.3 must use `estimated_event_key_with_snapshot_date` as the conservative event unit until duration or incident-start semantics are validated for B2 workbooks.

`daily_or_eod` remains a small ambiguous bucket. Its low compression suggests more event-like behavior, but it must be characterized separately before promotion.

B2.4 status: EOD/POD/snapshot buckets show prose-like structures but no confirmed initial problem report field. This is the third family without confirmed Symptom source.

raw_operational_values_emitted: false
