# Reference Layer v1 Freeze Checklist

This checklist defines the minimum controls required before freezing `reference-layer-v1`.

## T9 Freeze Controls

- Confirm that every reference-layer artifact has provenance fields populated.
- Confirm that evidence type and evidence tier remain separate fields.
- Confirm that SAP catalog rows are treated as `reference_evidence` unless a source concept to SAP code relation is independently demonstrated.
- Confirm that external corroboration is not promoted to FSA validation without project-specific evidence.
- Confirm that no produced concept lacks a valid canonical destination in `canonical-constraints.md`.
- Confirm that unresolved concepts are explicitly marked `unresolved` and do not enter measurement denominators.
- Confirm that no raw operational values are emitted in versioned outputs.

## Freeze Rule

`reference-layer-v1` can be frozen only when every produced concept is either mapped to a valid canonical destination constraint or explicitly marked as unresolved.
