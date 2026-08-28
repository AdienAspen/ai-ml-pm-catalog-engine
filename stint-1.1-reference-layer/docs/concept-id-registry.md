# Concept ID Registry

Stable concept identifiers prevent downstream stages from referencing mutable text labels.

## Format

```text
RL-{OBJECT}-{NNNN}
```

Examples:

- `RL-CANONICAL-0001`
- `RL-SOURCE-0001`
- `RL-LEXICAL-0001`
- `RL-NORMALISATION-0001`
- `RL-SAP-0001`

## Registry

| concept_id | object | preferred_label | namespace | status | notes |
|---|---|---|---|---|---|
| RL-CANONICAL-0001 | CANONICAL_TAXONOMY | TBD | TBD | pending | Bootstrap placeholder. |
| RL-SOURCE-0001 | SOURCE_DESIGNATIONS | TBD | TBD | pending | Bootstrap placeholder. |
| RL-LEXICAL-0001 | LEXICAL_LAYER | TBD | TBD | pending | Bootstrap placeholder. |
| RL-NORMALISATION-0001 | SEMANTIC_NORMALISATION | TBD | TBD | pending | Bootstrap placeholder. |
| RL-SAP-0001 | SAP_MAPPING | TBD | TBD | pending | Bootstrap placeholder. |
| RL-NORMALISATION-0101 | SEMANTIC_NORMALISATION | detection_symptom | semantic_scaffold | active | ZEUS-style scaffold category; Symptom hypothesis only. |
| RL-NORMALISATION-0102 | SEMANTIC_NORMALISATION | failure_mode | semantic_scaffold | active | Scaffold category; not one-to-one with SAP Damage. |
| RL-NORMALISATION-0103 | SEMANTIC_NORMALISATION | failure_cause | semantic_scaffold | active | Scaffold category for Cause evidence reconstruction. |
| RL-NORMALISATION-0104 | SEMANTIC_NORMALISATION | failure_process | semantic_scaffold | source_capture_pending | Physical process anchor for Damage semantics; WMEP/NREL vocabulary load pending. |
| RL-NORMALISATION-0105 | SEMANTIC_NORMALISATION | maintenance_measure | semantic_scaffold | active | Action/measure anchor for Activity semantics. |
| RL-NORMALISATION-0106 | SEMANTIC_NORMALISATION | maintenance_type | semantic_scaffold | pending_controlled_source | MAT support only; does not resolve Activity Type. |
