# Canonical Constraints

The interface contract is not domain semantics. It is the destination constraint for the reference layer.

The reference layer must know which interface field, namespace, data type, and cardinality each concept can feed, but it must not copy the interface contract as semantic content.

## Target Destination Constraints

| target | target_field | type | cardinality | namespace | record_identifier | primary_text_field | status | notes |
|---|---|---|---|---|---|---|---|---|
| symptom | TBD | string | TBD | catalog_s | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Symptom semantics remain hypothesis-level until direct project evidence exists. |
| object_part | TBD | string | TBD | catalog_b | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Valid target code universe comes from catalog reference evidence. |
| damage | TBD | string | TBD | catalog_c | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Damage must be treated as physical process, not observation. |
| cause | TBD | string | TBD | catalog_5 | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Low-coverage target; denominator is target-specific. |
| activity | TBD | string | TBD | catalog_a | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Shared evidence must not be counted as independent target evidence. |
| floc_leaf_segment | TBD | string | TBD | floc | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Structural support can validate interpretation but does not resolve hierarchy by itself. |
| activity_type | TBD | string | TBD | mat | pending_DELTA-0002 | pending_DELTA-0003 | unresolved | Pending controlled source confirmation. |

## Pending Runtime Constraints

- `record_identifier` is pending under `DELTA-0002`.
- `primary_text_field` is pending per target under `DELTA-0003`.
- Until these constraints are resolved or explicitly proxied, candidate evidence must not be promoted to a measurement denominator.

## Validation Rule

Before freezing `reference-layer-v1`, every produced concept or mapping candidate must have a valid destination constraint or be explicitly marked `unresolved`.
