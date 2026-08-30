# Canonical Constraints

## Purpose

This file records the canonical destination constraints for concepts produced by `reference-layer-v1`.

The canonical contract is an interface constraint, not domain evidence. This file reads and transcribes the frozen canonical v1.8 baseline; it does not modify it and does not promote any field to ground truth.

## Source

- `data/interim/extracted_source/package_004_bf45b793/latest/canonical_field_matrix.csv`
- `data/interim/extracted_source/package_004_bf45b793/latest/FSA_SyncHub_Canonical_Record_Specification_v1_8.md`

## Target Destination Constraints

| target | namespace | target_field | field_type | cardinality | required | source_ref | status |
|---|---|---|---|---|---|---|---|
| Symptom | `catalog_s` | `header.symptom.group` + `header.symptom.code` | `string(8)` group + `string(4)` code | `1` per notification header | yes | `canonical_field_matrix.csv`: `header.symptom.group`, `header.symptom.code`; evidence ref `Wind_Catalog_Group_and_Codes_Final_v4.xlsx`, Catalog S | resolved |
| Object Part | `catalog_b` | `findings[].object_part` | `Resolution<{group,code,text}>` | `0..10`, exactly `1` per finding when emitted | conditional | `canonical_field_matrix.csv`: `findings[].object_part`; evidence ref Catalog B | resolved |
| Damage | `catalog_c` | `findings[].damage` | `Resolution<{group,code,text}>` | `0..10`, exactly `1` per finding when emitted | conditional | `canonical_field_matrix.csv`: `findings[].damage`; evidence ref Catalog C | resolved |
| Cause | `catalog_5` | `findings[].cause` | `Resolution<{group,code,text}>` | `0..10`, exactly `1` per finding when emitted | conditional | `canonical_field_matrix.csv`: `findings[].cause`; evidence ref Catalog 5 | resolved |
| Activity | `catalog_a` | `findings[].activity` | `Resolution<{group,code,text}>` | `0..10`, exactly `1` per finding when emitted | conditional | `canonical_field_matrix.csv`: `findings[].activity`; evidence ref Catalog A | resolved |
| FLOC leaf | `floc` | `header.functional_location` | `string(30)` | `1` per notification/order root | yes | `canonical_field_matrix.csv`: `header.functional_location`; SAP field `TPLNR`; mirrored by `order.funct_loc` | resolved |
| Activity Type | `mat` | `header.activity_type` | `string(3)` | `1` per notification/order root | yes | `canonical_field_matrix.csv`: `header.activity_type`; SAP field `ILART`; mirrored by `order.pmacttype` | resolved |

## Open Delta Constraints

| constraint | delta_id | status | reason | downstream impact |
|---|---|---|---|---|
| `record_identifier` | `DELTA-0002` | pending | The canonical constraints do not yet name the record identity field used to form target-level measurement denominators. `record_meta.canonical_record_id` exists as a generated canonical id, while external evidence such as Malyi expects an explicit work-order identifier. | STINT_1 must not claim a measurement denominator until the selected record identity key is documented or proxied. |
| `primary_text_field` | `DELTA-0003` | pending | The canonical includes text-bearing fields such as `header.short_text`, `header.long_text`, and classification-input text fields, but it does not bind one primary runtime text source per target. | T8 and later evidence passes must record which text field(s) were used per target before promoting candidates to measurable evidence. |

## Design Rules

- Do not invent canonical fields. If a concept has no destination listed above, mark it `unresolved`.
- Do not modify the canonical contract from this file.
- Treat this file as the destination constraint consumed by T8/T9 and downstream STINT_1 evidence engineering.
- A valid SAP catalog code is not enough; a concept must also have a valid canonical destination field.
- Before freezing `reference-layer-v1`, T9 must verify that no produced concept lacks a valid destination in this file.
