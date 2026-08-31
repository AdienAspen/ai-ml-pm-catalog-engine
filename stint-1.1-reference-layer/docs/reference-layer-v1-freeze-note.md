# Reference Layer v1 Freeze Note

## Scope

This note records the `T9` freeze decision for `reference-layer-v1`.

The freeze does not claim production ground truth, runtime validation, model readiness, or accuracy. It freezes the PoC reference-layer baseline that STINT_1 will consume for evidence reconstruction.

## Freeze Decision

`reference-layer-v1` is frozen for PoC downstream use with three complete objects and two explicitly partial/provisional objects.

| object | freeze_status | decision |
|---|---|---|
| `SAP_MAPPING` | complete_for_poc_reference_layer | The SAP catalog universe is ingested as authoritative `reference_evidence`. It validates legal target codes, but does not by itself create validated mappings or measurement denominators. |
| `SOURCE_DESIGNATIONS` | complete_for_poc_reference_layer | IEC logical nodes, IH06 contrast, KKS/RDS review, and FLOC namespace rules are documented. FLOC resolution proceeds through IH06 lexical matching in STINT_1, not KKS/RDS crosswalk. |
| `CANONICAL_CONSTRAINTS` | complete_for_poc_reference_layer | The seven target destinations are declared. The canonical remains an interface constraint, not domain evidence. |
| `SEMANTIC_NORMALISATION` | partial_structural_scaffold | ZEUS/MaintIE/Malyi scaffolding defines containers and routing rules. WMEP and NREL GRD content remain `source_capture_pending`. |
| `LEXICAL_LAYER` | provisional_pending_token_filtering_and_domain_grouping | T8 completed as a contact test. T8b/T8c show broad token/n-gram admission and weak grouping into canonical domain concepts. |

## Corrections Captured Before Freeze

- `LEXICAL_LAYER` is not accepted as a final seed dictionary; it is frozen as provisional and assigned to STINT_1 rework.
- `SEMANTIC_NORMALISATION` is not claimed to contain populated WMEP/NREL wind-failure vocabulary; it is a structural scaffold.
- The canonical contract is classified as `interface_constraint`, not `expert_inference` or any evidence type.
- ZEUS public-preview category names are treated as `reference_evidence`; project-target routing derived from those categories remains `expert_inference`.
- `LTIM` is documented as an IEC 61850-7-4-derived time-management node and excluded from the IEC 61400-25-2 physical-node IH06 contrast.

## Governance Position

The reference layer remains compatible with the constitutional PoC rule:

```text
observed != validated != proxy != synthetic != inferred
```

No object in this freeze creates gold labels, production accuracy, or target-level measurement denominators. The layer gives STINT_1 a controlled starting point for reconstructing evidence with provenance.

## Downstream Handling

STINT_1 should:

- use `SAP_MAPPING` as the legal target-code universe;
- use `CANONICAL_CONSTRAINTS` as destination/interface constraints;
- use `SOURCE_DESIGNATIONS` to guide FLOC and source-designation interpretation;
- use `SEMANTIC_NORMALISATION` as routing architecture, while filling WMEP/NREL content only with documented provenance;
- rework `LEXICAL_LAYER` by token/n-gram filtering and domain grouping before promoting entries to silver evidence.

## Freeze Status

`reference-layer-v1` is committee-auditable for PoC use, with known partial objects explicitly named and excluded from premature measurement claims.
