# F0b - Routing Field Coverage Check

## Purpose

This check validates two routing risks before Phase 1: concentration on `description_extended` and the stratum boundary for PDF event support.

It emits aggregate coverage only and no raw operational values.

## Field Coverage

| source_family | source_text_field | records_checked | non_empty_records | non_empty_pct | status |
|---|---|---:|---:|---:|---|
| source_data_structured | `classification_input.description` | 10749 | 10749 | 100.0 | available |
| source_data_structured | `classification_input.description_extended` | 10749 | 10341 | 96.2 | available |
| source_data_structured | `classification_input.reason` | 10749 | 10338 | 96.18 | available |
| source_data_structured | `classification_input.work_performed` | 10749 | 10123 | 94.18 | available |
| source_data_structured | `header.activity_type` | 10749 | 10749 | 100.0 | available |
| pdf_structural_event | `pdf_assets_of_concern.event` | 1581 | 1581 | 100.0 | available |

## Controls

- `description_extended` coverage must be considered before F1 filtering because multiple targets depend on it as primary or supporting text.
- `pdf_assets_of_concern.event` is `event_structural`. Evidence using it as support for Object Part or Damage must keep that stratum explicit.
- F6 must not merge `event_structural` evidence with planned/reactive denominators.

## Decision

F0 remains open only if `description_extended` is unavailable or materially sparse. Otherwise F1 can proceed while preserving the explicit stratum rule.
