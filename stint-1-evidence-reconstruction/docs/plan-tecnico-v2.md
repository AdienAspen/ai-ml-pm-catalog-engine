# Technical Plan v2 - STINT 1 Evidence Reconstruction

## Scope

STINT 1 reconstructs a defensible evidence layer for the PoC after the STINT_0 feasibility assessment and the frozen STINT_1.1 reference layer.

The working objective is:

```text
target x evidence_type x tier x contractor_path x site_key x stratum -> evaluable records
```

## Inputs

- Frozen `reference-layer-v1`
- STINT_0 feasibility artefacts and sanitized findings
- Local corpus under private enclosure
- Public/external references admitted in STINT_1.1

## Core Rules

- Do not treat client confirmation as available.
- Do not report production accuracy.
- Do not mix observed, validated, proxy, synthetic, and inferred evidence.
- Do not promote shared multi-target structures before semantic split.
- Do not mix planned/reactive strata with `event_structural` PDF strata.
- Do not copy the reference layer; consume it by relative path.

## Phase Plan

| phase | workstream | expected output |
|---|---|---|
| 0 | Consolidation | Imported decisions, open deltas, and source gates. |
| 1 | Lexical rework | Filtered/grouped lexical layer v2 and populated scaffold where sources allow. |
| 2 | Reconciliation | Unknown split and multi-target shared-evidence split. |
| 3 | Fault-code path | Fault-code evidence with provenance, confidence, and no one-to-one SAP assumption. |
| 4 | XLSX/source-data path | Target evidence from structured runtime sources. |
| 5 | Symptom path | Symptom assessment after stronger target context exists. |
| 6 | Denominators | Defensible per-target measurement denominator tables. |

## Starting Deltas

- `DELTA-0002`: record identifier policy.
- `DELTA-0003`: primary text field by target.
- `DELTA-0009`: Cause / Activity / Activity Type shared evidence split.

