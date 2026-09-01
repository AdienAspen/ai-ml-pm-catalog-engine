# F1c - Canonical Vocabulary Materialization

## Purpose

This pass materializes the canonical vocabulary owners that F1d can use for domain grouping.

It does not map observed terms to concepts and does not emit raw operational values.

## Result

- Sanitized vocabulary rows: 14479
- Working vocabulary rows: 14477
- Distinct concept IDs: 13816
- `concept_id` is a concept-level identifier, not a row identifier.

## Vocabulary Owners

- IH06_OBSERVED_NODES: 640
- MALYI_SCHEMA: 5
- NREL_GRD: 1
- SAP_MAPPING: 13826
- WMEP: 1
- ZEUS_SCAFFOLD: 6

## Status

- active: 14467
- hypothesis: 3
- pending_controlled_source: 1
- schema_only: 5
- source_capture_pending: 3

## Pending Sources

- WMEP remains `source_capture_pending`; no source rows were invented.
- NREL GRD remains `source_capture_pending`; no source rows were invented.

## Governance

- SAP catalog rows are `reference_evidence`: they define valid target-code universe, not observed mappings.
- Observed text to canonical concept links will be `expert_inference` unless independently corroborated.
- `unresolved` remains a valid downstream outcome.
