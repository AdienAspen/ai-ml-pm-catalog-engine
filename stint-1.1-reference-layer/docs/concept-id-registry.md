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
| RL-SOURCE-0101 | SOURCE_DESIGNATIONS | FLOC guidance source | floc | present_not_promoted | Supporting reference only; not a record-level label source. |
| RL-SOURCE-0102 | SOURCE_DESIGNATIONS | KKS/RDS-style source | floc | present_not_resolver | Supporting feature/validator only; does not resolve or construct FLOC hierarchy. |
| RL-SOURCE-0103 | SOURCE_DESIGNATIONS | FLOC structure guideline | floc | present_not_promoted | Structure support only; not a measurement denominator. |
| RL-SOURCE-0104 | SOURCE_DESIGNATIONS | FLOC segment controlled glossary | floc | not_versioned_in_reference_layer | Must be ingested with provenance before use as controlled vocabulary content. |
| RL-SOURCE-0105 | SOURCE_DESIGNATIONS | IEC 21 logical-node reference intake | floc | active | Materialized from accessible IEC 61400-25-2 preview/table material; not a full normative transcription. |
| RL-SOURCE-0201 | SOURCE_DESIGNATIONS | LLN0 | iec_logical_node | active | Base logical node; not applicable to IH06 physical subsystem contrast. |
| RL-SOURCE-0202 | SOURCE_DESIGNATIONS | LPHD | iec_logical_node | active | Physical device information; not an IH06 functional-location subsystem expectation. |
| RL-SOURCE-0203 | SOURCE_DESIGNATIONS | WPPD | iec_logical_node | active | Wind power plant information; not an IH06 turbine subsystem expectation. |
| RL-SOURCE-0204 | SOURCE_DESIGNATIONS | WTUR | iec_logical_node | active | Wind turbine general/root context; not counted as missing physical subsystem. |
| RL-SOURCE-0205 | SOURCE_DESIGNATIONS | WROT | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0206 | SOURCE_DESIGNATIONS | WTRM | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0207 | SOURCE_DESIGNATIONS | WGEN | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0208 | SOURCE_DESIGNATIONS | WCNV | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0209 | SOURCE_DESIGNATIONS | WTRF | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0210 | SOURCE_DESIGNATIONS | WNAC | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0211 | SOURCE_DESIGNATIONS | WYAW | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0212 | SOURCE_DESIGNATIONS | WTOW | iec_logical_node | active | Physical turbine subsystem node for IH06 contrast. |
| RL-SOURCE-0213 | SOURCE_DESIGNATIONS | WMET | iec_logical_node | active | Information node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0214 | SOURCE_DESIGNATIONS | WALM | iec_logical_node | active | Alarm information node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0215 | SOURCE_DESIGNATIONS | WAVL | iec_logical_node | active | Availability information node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0216 | SOURCE_DESIGNATIONS | WAPC | iec_logical_node | active | Control node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0217 | SOURCE_DESIGNATIONS | WRPC | iec_logical_node | active | Control node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0218 | SOURCE_DESIGNATIONS | WSLG | iec_logical_node | active | Log node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0219 | SOURCE_DESIGNATIONS | WALG | iec_logical_node | active | Log node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0220 | SOURCE_DESIGNATIONS | WREP | iec_logical_node | active | Report node; excluded from IH06 physical subsystem contrast. |
| RL-SOURCE-0221 | SOURCE_DESIGNATIONS | LTIM | iec_logical_node | active | Time-management node derived from IEC 61850-7-4; excluded from IH06 physical subsystem contrast. |
| RL-CANONICAL-0101 | CANONICAL_TAXONOMY | FLOC leaf observed depth constraint | floc | active_design_constraint | IH06 sanitized crosscheck observed site max depth 4-5 and no depth >= 6; use as design constraint, not final ISO mapping. |
