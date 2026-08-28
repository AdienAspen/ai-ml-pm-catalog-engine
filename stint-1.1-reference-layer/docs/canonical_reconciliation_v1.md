# Canonical Reconciliation v1

## Purpose

This note reconciles the frozen interface constraints with the SAP target-code universe ingested into `SAP_MAPPING`.

It does not create ground truth, does not validate runtime availability, and does not overwrite the frozen canonical contract. It records how each target should be interpreted by the reference layer before STINT_1 executes evidence reconstruction.

## Inputs

| input | role | evidence_type | measurement use |
|---|---|---|---|
| Canonical constraints | Interface and destination constraint | expert_inference | Not a label source |
| SAP mapping catalog | Authoritative target-code universe for S/B/C/5/A | reference_evidence | Not a denominator |
| External schema delta | Architecture corroboration | external_corroboration | Not FSA validation |

## Reconciliation Principles

- The canonical contract defines the shape and destination field.
- The SAP catalog defines valid target-code namespaces for S/B/C/5/A.
- The reference layer connects observed text or concepts to valid target-code candidates with provenance.
- A catalog row is `reference_evidence`, not `validated_mapping`, unless a source concept or source text to SAP code relation is independently demonstrated.
- Any gap between the canonical contract, SAP vocabulary, and observed corpus evidence is logged instead of being silently resolved.

## Target Reconciliation

| target | namespace | SAP/catalog interpretation | reconciliation_status | reference-layer instruction |
|---|---|---|---|---|
| Symptom | catalog_s | Close to failure-effect semantics, but project evidence does not prove the equivalence. | hypothesis | Keep as hypothesis until project-specific catalog/configuration or SME evidence confirms it. |
| Object Part | catalog_b | Object/component part answer namespace. | anchored_reference | Use as valid code universe; do not treat as source-text mapping. |
| Damage | catalog_c | Physical damage or failure-process namespace, not a visual observation bucket. | anchored_reference_with_definition_fix | Extractor language must treat Damage as physical process/state, not generic observation. |
| Cause | catalog_5 | Cause-code answer namespace. | anchored_reference | Use as valid code universe; low observed coverage remains a data/evidence issue, not a catalog issue. |
| Activity | catalog_a | Maintenance action or measure answer namespace. | anchored_reference | Shared evidence must be semantically split before any target-specific claim. |
| FLOC leaf segment | floc | Outside SAP S/B/C/5/A catalog universe; supported by separate FLOC/KKS/RDS-style references. | separate_namespace | KKS/supporting designations can validate interpretation but must not be treated as resolving hierarchy by themselves. |
| Activity Type | mat | Separate controlled source remains pending. | blocked_pending_source | Do not promote to measurement-ready until the controlled Activity Type / MAT source is confirmed or proxied. |

## Key Decisions

- Symptom/Catalog S remains `hypothesis`, not `resolved`.
- Damage/Catalog C is defined operationally as physical process/state evidence, not observation text alone.
- Object Part, Cause, and Activity are anchored to the SAP catalog as valid answer namespaces.
- Activity and Activity Type must not inherit independent evidence from shared multi-target structures without semantic split.
- FLOC remains outside the Wind S/B/C/5/A catalog and requires its own namespace treatment.

## Open Deltas

| delta | issue | required action |
|---|---|---|
| DELTA-0002 | `record_identifier` not yet fixed in canonical constraints. | Resolve before measurement denominators. |
| DELTA-0003 | `primary_text_field` not yet fixed per target. | Resolve or proxy before target evidence execution. |
| DELTA-0007 | Symptom/Catalog S semantic equivalence remains hypothesis. | Require project-specific catalog/configuration evidence or SME proxy. |
| DELTA-0008 | Damage extractor definition must avoid treating observations as Damage labels. | Align extractor rules to physical damage/process semantics. |
| DELTA-0009 | Activity evidence may be shared with Cause/Activity Type. | Require semantic split before target-level promotion. |
| DELTA-0010 | FLOC support vocabulary is outside SAP S/B/C/5/A. | Keep separate namespace and validate consumer constraint. |

## T4 Closeout

T4 is complete for STINT_1.1 when this reconciliation is used as the rule source for downstream scaffold, dictionary, and freeze checks. It remains non-final until STINT_1 tests these constraints against evidence reconstruction.
