# Canonical Constraints

The interface contract is not domain semantics. It is the destination constraint for the reference layer.

The reference layer must know which interface field, namespace, data type, and cardinality each concept can feed, but it must not copy the interface contract as semantic content.

## Required Columns

| target | target_field | namespace | data_type | cardinality | required | notes |
|---|---|---|---|---|---|---|
| symptom | TBD | catalog_s | string | TBD | TBD | Symptom semantics remain hypothesis-level until direct project evidence exists. |
| object_part | TBD | catalog_b | string | TBD | TBD | Valid target code universe comes from catalog reference evidence. |
| damage | TBD | catalog_c | string | TBD | TBD | Damage must be treated as physical process, not observation. |
| cause | TBD | catalog_5 | string | TBD | TBD | Low-coverage target; denominator is target-specific. |
| activity | TBD | catalog_a | string | TBD | TBD | Shared evidence must not be counted as independent target evidence. |
| floc_leaf_segment | TBD | floc | string | TBD | TBD | Structural support can validate interpretation but does not resolve hierarchy by itself. |
| activity_type | TBD | mat | string | TBD | TBD | Pending controlled source confirmation. |

## Validation Rule

Before freezing `reference-layer-v1`, every produced concept or mapping candidate must have a valid destination constraint or be explicitly marked `unresolved`.
