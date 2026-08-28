# ZEUS Semantic Scaffold

## Scope

This document defines a PoC semantic scaffold inspired by the public ZEUS/SAP maintenance taxonomy shape. It does not ingest, reproduce, or claim access to any proprietary ZEUS standard.

The scaffold is a design artifact for `STINT_1.1-reference-layer`. It specifies how later STINT_1 evidence reconstruction should separate maintenance language before attempting target-level promotion.

## Blocking Cautions

- ZEUS-style categories are semantic scaffolding, not ground truth.
- A ZEUS-style failure mode does not map one-to-one to SAP Damage / Catalog C.
- Maintenance type support does not resolve Activity Type / MAT until the controlled source is confirmed.
- No row in this scaffold is `validated_mapping`.
- Canonical fields are destination constraints, not evidence sources.
- This T5 deliverable defines containers and routing rules; it does not yet populate domain vocabulary from WMEP or NREL GRD.

## Content Status

T5 is intentionally structural. It provides the semantic container model that STINT_1 will consume, but the lexical content for several containers is still pending.

| content_area | status | implication |
|---|---|---|
| ZEUS-style category names | scaffolded from public-preview category shape | Usable as high-level reference framing only. |
| Target routing from category to project target | hypothesis | Treated as `expert_inference`, not as validated mapping. |
| WMEP vocabulary/content | source_capture_pending | Container exists; vocabulary load remains pending. |
| NREL GRD vocabulary/content | source_capture_pending | Container exists; vocabulary load remains pending. |
| MaintIE/Malyi structural corroboration | ingested | Useful to support architecture, not project-specific labels. |

## Category Scaffold

| concept_id | zeus_category | working_definition | category_evidence_type | nearest_project_target_or_use | target_link_evidence_type | tier | status |
|---|---|---|---|---|---|---|---|
| RL-NORMALISATION-0101 | detection_symptom | Observable indication that something abnormal was detected. | reference_evidence | Symptom / Catalog S hypothesis only | expert_inference | silver-medium | hypothesis |
| RL-NORMALISATION-0102 | failure_mode | Way in which a component or system fails to perform. | reference_evidence | Damage / Object Part context, not one-to-one Damage | expert_inference | silver-medium | hypothesis |
| RL-NORMALISATION-0103 | failure_cause | Underlying reason or condition contributing to failure. | reference_evidence | Cause / Catalog 5 candidate semantics | expert_inference | silver-medium | hypothesis |
| RL-NORMALISATION-0104 | failure_process | Physical degradation or damage process. | reference_evidence | Damage / Catalog C supporting semantics | expert_inference | silver-medium | source_capture_pending |
| RL-NORMALISATION-0105 | maintenance_measure | Action taken or recommended to restore, inspect, or prevent failure. | reference_evidence | Activity / Catalog A supporting semantics | expert_inference | silver-medium | active |
| RL-NORMALISATION-0106 | maintenance_type | Maintenance class such as corrective, preventive, planned, or reactive. | reference_evidence | Activity Type / MAT support only | expert_inference | silver-medium | pending_controlled_source |

## Provenance Slots

| source_family | intended_use | evidence_type | tier | current_status | constraint |
|---|---|---|---|---|---|
| MaintIE | Maintenance entity and relation shape for technical text. | reference_evidence | silver-medium | ingested | Does not validate project-specific labels. |
| Malyi | External corroboration for maintenance schema concepts and system/component framing. | external_corroboration | silver-high | ingested | Corroborates architecture only; does not validate FSA mappings. |
| WMEP | Wind maintenance event process/cause/effect reference slot. | reference_evidence | silver-medium | source_capture_pending | Must be registered before downstream use. |
| NREL GRD | Gearbox failure-mode/degradation reference slot. | reference_evidence | silver-medium | source_capture_pending | Must be registered before downstream use. |
| ZEUS public preview | High-level SAP maintenance semantic categories. | reference_evidence | silver-medium | scaffold_only | Category names guide design; project-target routing remains expert inference. |

## Canonical Destination Constraint

Any concept produced by this scaffold must resolve to a valid destination in `canonical-constraints.md` before it can be consumed by later pipeline stages.

This means:

- the target field must exist;
- the namespace must be known;
- the expected type and cardinality must be respected;
- unresolved record identifier and primary text field deltas must remain visible.

## Mapping Rule

The reference layer should not jump directly from source text to a SAP code. The intended STINT_1 flow is:

```text
real text
  -> lexical/semantic normalisation
  -> canonical concept
  -> SAP_MAPPING candidate
  -> valid target code
  -> canonical field
```

## Target Implications

| target | scaffold support | current interpretation |
|---|---|---|
| Symptom | detection symptom can frame search, but does not overturn near-zero evidence. | Remains no-current-demonstrable-proof-of-life unless new evidence appears. |
| Object Part | failure mode/system context may help split component references. | Requires target-specific evidence reconstruction. |
| Damage | failure process is the closest safe semantic anchor. | Must avoid treating generic failure mode as Damage. |
| Cause | failure cause provides a direct semantic bucket. | Requires labels/mappings or strong silver evidence before measurement. |
| Activity | maintenance measure provides a direct semantic bucket. | Candidate for evidence reconstruction after semantic split. |
| FLOC leaf segment | outside ZEUS/SAP S/B/C/5/A catalog universe. | Keep separate; KKS/RDS-PP can support/validate but not resolve hierarchy. |
| Activity Type / MAT | maintenance type supports framing. | Blocked/pending until controlled MAT source or documented proxy is confirmed. |

## T5 Result

T5 creates the semantic scaffold required for later Evidence Engineering. It does not run on operational data and does not produce candidates, labels, coverage, confidence, or final feasibility findings.

The scaffold is not yet lexically populated for WMEP/NREL-derived wind failure vocabulary. That work remains pending for T8 or STINT_1, depending on the final execution plan.
