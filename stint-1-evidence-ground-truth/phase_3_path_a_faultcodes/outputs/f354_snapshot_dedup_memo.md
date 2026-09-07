# T3.5.4 Path A Snapshot Deduplication

## Scope

This pass converts Path A code-bearing PDF rows from daily snapshots into estimated incident groups. It does not promote any event to a measurement denominator.

## Deduplication Rule

`incident_start_estimated = snapshot_date - duration`

Grouping key:

`site_key + asset_key + code_key + namespace + incident_start_estimated window`

Window tolerance: `1` day.

## Summary

- Snapshot rows evaluated: `602`
- Rows dedup-ready: `600`
- Rows missing temporal inputs: `2`
- Estimated events: `362`
- Overall compression ratio: `1.66`
- Raw operational values emitted in versioned outputs: `False`

## By Namespace

| namespace | snapshot_rows | estimated_events | compression_ratio |
| --- | ---: | ---: | ---: |
| asset_state | 313 | 88 | 3.56 |
| fault_code | 188 | 175 | 1.07 |
| undetermined_code | 101 | 99 | 1.02 |

## By Classification

| classification | snapshot_rows | estimated_events | compression_ratio |
| --- | ---: | ---: | ---: |
| fault_code | 188 | 175 | 1.07 |
| state_code | 313 | 88 | 3.56 |
| undetermined | 101 | 99 | 1.02 |

## Interpretation

`asset_state` remains a separate namespace. It is not automatically promoted to Activity Type; only maintenance-like state families may be reviewed later as secondary evidence.

Estimated events are `expert_inference`, `silver-medium`, `derived_from_rules`, and `estimated_event_requires_review` unless temporal inputs are missing.
