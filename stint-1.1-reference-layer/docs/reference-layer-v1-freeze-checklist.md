# Reference Layer v1 Freeze Checklist

This checklist defines the minimum controls required before freezing `reference-layer-v1`.

## T9 Freeze Controls

- Confirm that every reference-layer artifact has provenance fields populated.
- Confirm that evidence type and evidence tier remain separate fields.
- Confirm that SAP catalog rows are treated as `reference_evidence` unless a source concept to SAP code relation is independently demonstrated.
- Confirm that the canonical contract is treated as `interface_constraint`, not as evidence.
- Confirm that ZEUS public-preview category names are `reference_evidence`; project-target routing remains `expert_inference`.
- Confirm that external corroboration is not promoted to FSA validation without project-specific evidence.
- Confirm that no produced concept lacks a valid canonical destination in `canonical-constraints.md`.
- Confirm that unresolved concepts are explicitly marked `unresolved` and do not enter measurement denominators.
- Confirm that no raw operational values are emitted in versioned outputs.
- Confirm that `LTIM` is documented as IEC 61850-7-4-derived and excluded from the IEC 61400-25-2 physical-node IH06 contrast.
- Confirm that `LEXICAL_LAYER` is frozen only as provisional, with the T8b/T8c cause documented.
- Confirm that `SEMANTIC_NORMALISATION` is frozen as a structural scaffold while WMEP and NREL GRD remain `source_capture_pending`.

## T9 Object Status

| object | freeze_status | reason | downstream implication |
|---|---|---|---|
| `SAP_MAPPING` | complete_for_poc_reference_layer | SAP catalog rows are ingested as authoritative valid-code universe with row-level `reference_evidence`, not validated mappings. | Can validate whether a candidate SAP code is legal; cannot create record-level denominators by itself. |
| `SOURCE_DESIGNATIONS` | complete_for_poc_reference_layer | IEC logical-node intake, IH06 contrast, KKS/RDS review, and FLOC namespace rules are documented. | FLOC resolution proceeds through IH06 lexical matching in STINT_1, not through KKS/RDS crosswalk. |
| `CANONICAL_CONSTRAINTS` | complete_for_poc_reference_layer | Seven targets have destination fields declared; canonical is interface constraint, not domain evidence. | Produced concepts must resolve to a valid canonical destination before downstream consumption. |
| `SEMANTIC_NORMALISATION` | partial_structural_scaffold | ZEUS/MaintIE/Malyi scaffold is usable, but WMEP and NREL GRD content remain `source_capture_pending`. | Containers and routing rules exist; wind failure vocabulary still requires population in STINT_1. |
| `LEXICAL_LAYER` | provisional_pending_token_filtering_and_domain_grouping | T8 was a contact test; T8b/T8c show broad token/n-gram admission and weak grouping into canonical domain concepts. | Do not treat lexical output as final seed dictionary; rework filtering/grouping during STINT_1. |

## Freeze Rule

`reference-layer-v1` can be frozen when every produced concept is either mapped to a valid canonical destination constraint or explicitly marked as unresolved/provisional, and when partial objects are named with cause and downstream handling.

For this freeze, the layer closes with three objects complete for PoC use and two objects explicitly partial/provisional:

- Complete: `SAP_MAPPING`, `SOURCE_DESIGNATIONS`, `CANONICAL_CONSTRAINTS`
- Partial/provisional: `SEMANTIC_NORMALISATION`, `LEXICAL_LAYER`
