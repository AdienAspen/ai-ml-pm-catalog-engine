# Reference Layer v1 Bootstrap

This directory defines the static reference layer that the next evidence-reconstruction pass will consume.

It does not create ground truth, train models, estimate accuracy, or execute production-scale candidate generation.

## Objects

- `CANONICAL_TAXONOMY`: functional hierarchy concepts.
- `SOURCE_DESIGNATIONS`: external designation systems and structural identifiers.
- `LEXICAL_LAYER`: observed and curated terminology used by technicians.
- `SEMANTIC_NORMALISATION`: normalisation rules and pipeline specification.
- `SAP_MAPPING`: valid catalog/code universe and target mapping candidates.

## Boundary

The reference layer connects observed text and reference concepts to valid target candidates. The interface contract remains a consumer constraint, not semantic content.

Operational chain:

```text
real text -> lexical/semantic normalisation -> canonical concept -> SAP_MAPPING candidate -> valid target code -> interface field
```

Every row-level entry must carry granular provenance and keep `evidence_type` separate from `tier`.
