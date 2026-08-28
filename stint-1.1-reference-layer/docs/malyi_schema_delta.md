# Malyi Schema Delta

## Scope

This note compares the external Malyi maintenance-log labelling framework with the frozen canonical constraints used by this PoC reference layer.

It is a schema and method-alignment check only. It does not validate project-specific runtime availability, record-level labels, or production feasibility.

## External Source

| source | ingested evidence | evidence_type | tier | interpretation |
|---|---|---|---|---|
| Malyi wind turbine maintenance log labelling framework | README, prompt schemas, taxonomy handler, orchestration template, requirements | external_corroboration | silver-high | Corroborates that a wind-maintenance NLP pipeline commonly needs work-order identity, technician text, system/component code, system/component name, and maintenance type context. |

Exact files named in the original T2 plan, `used_taxonomy.md` and `technical_report.md`, were not present in the ingested Malyi source tree. Available equivalents used for this comparison were `README.md`, `prompts/schemas.py`, and `src/taxonomy_handler.py`.

## Malyi Minimum Input Schema

| Malyi field | role | notes |
|---|---|---|
| `WO_ID` | record identifier | Required work-order level identifier. |
| `Descriptions` | primary text signal | Free-text technician/maintenance description. |
| `System_Code` | existing component/system code | Used for system-code correction and contextual labelling. |
| `System_Name` | component/system name | Human-readable component/system context. |
| `Maintenance_Type` | maintenance class | Used to separate preventive, corrective, inspection, reset, and related activity classes. |

## Canonical Target Constraints

| target | namespace | current canonical status | comparison to Malyi |
|---|---|---|---|
| Symptom | `catalog_s` | Destination exists as target concept, but semantics remain unresolved. | Malyi includes symptom/effect style fields in failure-mode output, but this only corroborates the need for a symptom/effect dimension. It does not prove project-specific Symptom labels. |
| Object Part | `catalog_b` | Valid SAP code universe available through catalog reference evidence. | Malyi's `System_Code`/`System_Name` and taxonomy handler corroborate a component/object-part layer, but with RDS-PP-style taxonomy rather than project SAP Catalog B labels. |
| Damage | `catalog_c` | Treated as physical process, not merely observation. | Malyi failure-mode output includes failure mode/mechanism/cause/symptom structure. This supports the need for a damage/mechanism-like dimension, not a validated mapping. |
| Cause | `catalog_5` | Low-coverage target; denominator remains target-specific. | Malyi explicitly models `Cause`, corroborating the target concept. It does not resolve low project coverage or provide labels for this corpus. |
| Activity | `catalog_a` | Shared evidence must not be counted as independent target evidence. | Malyi includes `Maintenance_Type` and `Action_Taken`, corroborating the need to separate maintenance class from action labels. |
| FLOC leaf segment | `floc` | Structural support can validate interpretation but does not resolve hierarchy by itself. | Malyi's taxonomy handler corroborates hierarchical component-code handling. It does not validate project FLOC construction. |
| Activity Type | `mat` | Pending controlled source confirmation. | Malyi's `Maintenance_Type` aligns conceptually with activity type/classification, but cannot substitute for the missing project GE MAT/activity-type controlled source. |

## Main Alignments

- The external framework corroborates the project decision to treat technician text as the primary lexical signal.
- It supports separating maintenance class/type from action taken.
- It supports using component/system taxonomies as context for downstream labels.
- It supports confidence/review flags as first-class output fields.
- It supports preserving legacy fields and appending derived fields instead of overwriting source evidence.

## Main Divergences

| delta_id | object | observed divergence | implication | proposed action |
|---|---|---|---|---|
| DELTA-0002 | input schema | Malyi requires `WO_ID`; current canonical constraints do not yet name the record identifier field. | The reference layer needs a record identity constraint before measurement denominators can be defended. | Add/confirm canonical record identifier constraint in STINT_1 before measurement. |
| DELTA-0003 | text signal | Malyi centers `Descriptions`; current canonical constraints do not yet bind the primary text field per target. | Target-level evidence cannot be measured until runtime text fields are declared. | Add primary text-signal constraint per target or mark unresolved. |
| DELTA-0004 | component taxonomy | Malyi uses RDS-PP-style `System_Code`/`System_Name`; project targets use SAP Catalog B plus FLOC/KKS support. | External taxonomy corroborates architecture, but not project code mappings. | Keep as `external_corroboration`; do not promote to validated mapping. |
| DELTA-0005 | maintenance type | Malyi includes `Maintenance_Type`; project `Activity Type / MAT` remains source-pending. | Concept aligns, but controlled source is still missing for this project. | Keep Activity Type blocked/pending until controlled source is confirmed or substituted by documented proxy. |
| DELTA-0006 | output labels | Malyi generates FMEA/action labels with confidence/review flags; project requires target-specific SAP catalog outputs. | Method is relevant, but target-code validity must still be checked against the SAP mapping universe and canonical destination fields. | Require SAP_MAPPING candidate and canonical field destination for each promoted concept. |

## Evidence Classification

The Malyi comparison is classified as:

- `evidence_type`: `external_corroboration`
- `tier`: `silver-high`
- `can_support_measurement_denominator`: `False`

Reason: it is a strong external architecture/method corroboration, but it does not provide project-specific observed labels or validated source-text-to-SAP-code mappings.

## T3 Conclusion

Malyi strongly corroborates the need for a reference layer that connects real maintenance text, component/system context, maintenance type, target concepts, confidence flags, and human review.

It does not validate FSA target mappings and must not be used as ground truth. Its value for STINT_1.1 is architectural and methodological: it supports the design of the evidence pipeline that STINT_1 will later execute over the project corpus.
