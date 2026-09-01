# DELTA-0002 - Record Identifier

## Status

`resolved_for_poc_policy`

## Issue

The frozen canonical constraints do not yet name the definitive record identity field used to form target-level measurement denominators.

## STINT 1 Requirement

Before any target denominator is claimed, STINT_1 must document the selected `record_id` or proxy record identifier and its coverage.

## Decision

STINT_1 uses two related identifiers:

- `physical_record_id` for denominator counting
- `stint1_record_id` for record-field evidence traceability

`physical_record_id` is a deterministic, non-reversible proxy generated from sanitized physical record lineage:

```text
source_family + source_path_key + source_record_ordinal
```

`stint1_record_id` is a deterministic, non-reversible proxy generated from sanitized record-field lineage:

```text
source_family + source_path_key + source_record_ordinal + source_text_field
```

Because `source_text_field` is part of the key, `stint1_record_id` identifies a `record-field` evidence unit. The same physical source record can therefore produce more than one `stint1_record_id` when multiple text/runtime fields contribute evidence.

Denominator `N` is counted by unique `physical_record_id x target`, not by evidence rows and not by `stint1_record_id`. A record with multiple convergent evidence rows for the same target counts once.

When a canonical runtime record already exposes `record_meta.canonical_record_id`, that value may be recorded as `canonical_record_id_ref`, but STINT_1 denominator counts use `physical_record_id` for consistency across source families.

## Why This Is Acceptable for PoC

The project no longer has a client validation channel for production record identity. A deterministic proxy is therefore the only auditable way to prevent row/file/candidate counts from being mistaken for measurement denominators.

This does not modify the frozen canonical contract and does not claim production runtime identity.

## Constraint

Do not treat row counts, file counts, candidate counts, or evidence-row counts as measurement denominators unless they are deduplicated by `physical_record_id` and target.

`stint1_record_id` may be used for audit trails, conflict review, and evidence convergence, but not as the default denominator count.

Do not emit raw source paths or raw business identifiers into versioned evidence.

## Downstream Validation

Phase 6 must report denominator coverage by:

```text
target x denominator_type x evidence_type x tier x contractor_path x site_key x stratum
```

The report must state whether `N` is a contractual denominator or a POC proxy denominator.
