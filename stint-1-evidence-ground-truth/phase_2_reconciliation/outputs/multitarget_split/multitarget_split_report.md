# F2 Multitarget Split Report

## Scope

This report resolves `DELTA-0009` for the 36 pair structures previously expanded across
Cause, Activity, and Activity Type.

## Reconciliation

| metric | value |
| --- | ---: |
| expanded rows before split | 108 |
| unique pair structures | 36 |
| split groups | 6 |

| prior target | expanded rows |
| --- | ---: |
| Activity | 36 |
| Activity Type | 36 |
| Cause | 36 |

## Decision

The 36 structures are shared-expanded evidence, not three independent target signals.
No target is promoted to measurement readiness by this split.

- `reason` is a Cause-specific candidate field, but its paired code fields are identifiers or metadata, not validated mappings.
- `activityType` is an Activity Type structural candidate, pending MAT/catalog validation.
- `description` and `descriptionExtended` are shared narrative evidence; they support downstream weak supervision but do not independently prove Cause, Activity, or Activity Type.
- No independent Activity evidence is demonstrated by these 36 structures.

## Implication

The apparent uniform evidence for Cause, Activity, and Activity Type is downgraded to
shared evidence. F4/F6 must treat each target separately and must not count the same shared
source structure as three independent denominators.
