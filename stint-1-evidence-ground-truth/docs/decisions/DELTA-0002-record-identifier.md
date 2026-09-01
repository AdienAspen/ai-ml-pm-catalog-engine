# DELTA-0002 - Record Identifier

## Status

`resolved_for_poc_policy`

## Issue

The frozen canonical constraints do not yet name the definitive record identity field used to form target-level measurement denominators.

## STINT 1 Requirement

Before any target denominator is claimed, STINT_1 must document the selected `record_id` or proxy record identifier and its coverage.

## Decision

STINT_1 uses `stint1_record_id` as the record identity key for PoC evidence reconstruction.

`stint1_record_id` is a deterministic, non-reversible proxy generated from sanitized record lineage:

```text
source_family + source_path_key + source_record_ordinal + source_text_field
```

Because `source_text_field` is part of the key, `stint1_record_id` identifies a `record-field` evidence unit. The same physical source record can therefore produce more than one `stint1_record_id` when multiple text/runtime fields contribute evidence.

When a canonical runtime record already exposes `record_meta.canonical_record_id`, that value may be recorded as `canonical_record_id_ref`, but STINT_1 denominators use `stint1_record_id` for consistency across source families.

## Why This Is Acceptable for PoC

The project no longer has a client validation channel for production record identity. A deterministic proxy is therefore the only auditable way to prevent row/file/candidate counts from being mistaken for measurement denominators.

This does not modify the frozen canonical contract and does not claim production runtime identity.

## Constraint

Do not treat row counts, file counts, or candidate counts as measurement denominators unless they are grouped by `stint1_record_id` and target.

When a report needs a physical-record denominator, it must be calculated separately by deduplicating sanitized source lineage without `source_text_field`.

Do not emit raw source paths or raw business identifiers into versioned evidence.

## Downstream Validation

Phase 6 must report record-id coverage by:

```text
target x evidence_type x tier x contractor_path x site_key x stratum
```
