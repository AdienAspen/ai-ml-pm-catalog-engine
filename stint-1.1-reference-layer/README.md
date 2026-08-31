# Reference Layer v1 Bootstrap

This directory defines the static reference layer that the next evidence-reconstruction pass will consume.

It does not create ground truth, train models, estimate accuracy, or execute production-scale candidate generation.

## Objects

- `CANONICAL_CONSTRAINTS`: interface/destination constraints for the seven targets. Status: `complete_for_poc_reference_layer`.
- `SOURCE_DESIGNATIONS`: external designation systems and structural identifiers. Status: `complete_for_poc_reference_layer`.
- `LEXICAL_LAYER`: observed terminology contact-test output. Status: `provisional_pending_token_filtering_and_domain_grouping`.
- `SEMANTIC_NORMALISATION`: normalisation rules and pipeline specification. Status: `partial_structural_scaffold`.
- `SAP_MAPPING`: valid catalog/code universe and target mapping candidates. Status: `complete_for_poc_reference_layer`.

## Boundary

The reference layer connects observed text and reference concepts to valid target candidates. The interface contract remains a consumer constraint, not semantic content.

Operational chain:

```text
real text -> lexical/semantic normalisation -> canonical concept -> SAP_MAPPING candidate -> valid target code -> interface field
```

Every row-level entry must carry granular provenance and keep `evidence_type` separate from `tier`.

## Freeze

`reference-layer-v1` is frozen for PoC downstream use with known limitations documented in `docs/reference-layer-v1-freeze-note.md`.
