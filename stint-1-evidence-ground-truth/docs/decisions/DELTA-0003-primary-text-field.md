# DELTA-0003 - Primary Text Field

## Status

`resolved_for_poc_policy`

## Issue

The canonical contract contains multiple text-bearing fields, but does not bind one primary runtime text field per target.

## STINT 1 Requirement

Every evidence row must carry `source_text_field`.

Before target-level measurement, STINT_1 must decide which text field or field family is valid for each target.

## Decision

STINT_1 uses explicit `source_text_field` routing by target. The field is mandatory on every evidence row and no evidence can be promoted if the text/source field is unknown.

| target | primary_source_text_field | allowed_supporting_fields | notes |
|---|---|---|---|
| Symptom | `classification_input.description_extended` | `classification_input.description`, `classification_input.reason` | Symptom remains hypothesis/silver-medium at most until downstream validation. Run on semantically reactive subsets only. |
| Object Part | `classification_input.description_extended` | `classification_input.work_performed`, `pdf_assets_of_concern.event` | Use component/system mentions; do not promote if only generic action text is present. |
| Damage | `classification_input.description_extended` | `classification_input.description`, `pdf_assets_of_concern.event` | Route through failure-process semantics; do not treat generic failure mode as SAP Damage. |
| Cause | `classification_input.reason` | `classification_input.description_extended` | Never infer Cause directly from Damage. Shared multi-target evidence remains blocked by `DELTA-0009`. |
| Activity | `classification_input.work_performed` | `classification_input.description_extended` | Action/measure evidence can support Activity after semantic split. |
| FLOC leaf | `header.functional_location` | `classification_input.description_extended` | FLOC target is structural; text is supporting evidence only. Resolve against IH06-derived nodes. |
| Activity Type | `header.activity_type` | `classification_input.work_performed` | Direct field where available; inferred maintenance type remains `expert_inference`. |

PDF-derived records keep `stratum: event_structural` and must not be mixed with planned/reactive strata.

## Why This Is Acceptable for PoC

The canonical contract does not bind a primary text field per target. This policy documents a PoC runtime assumption so STINT_1 can reconstruct evidence without losing field provenance.

This does not modify the frozen canonical contract.

## Constraint

Do not merge evidence extracted from different text fields unless the merge rule is documented and provenance is preserved.

Do not promote any evidence row without `source_text_field`.
