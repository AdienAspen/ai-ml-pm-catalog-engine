# T3.5.5 Path A Crosswalk v2

## Scope

This pass reruns Path A crosswalk scoring against the cleaned event universe from `T3.5.4`. It separates `asset_state` from `fault_code` and uses `NOTES` semantics only as candidate support.

## Summary

- Estimated events input: `362`
- Scoring rows emitted: `910`
- Candidate rows: `117`
- Candidate events: `62`
- Asset-state events kept in separate namespace: `88`
- Fault-code events evaluated: `175`
- Undetermined-code events carried forward: `99`
- Contractual denominator supported: `False`
- POC proxy denominator supported: `False`

## By Target And Status

| target | status | rows | estimated_events |
| --- | --- | ---: | ---: |
| Cause | candidate_high_requires_review | 7 | 7 |
| Cause | candidate_medium_requires_review | 29 | 29 |
| Cause | not_applicable_to_fault_crosswalk | 99 | 99 |
| Cause | unresolved_below_threshold | 139 | 139 |
| Damage | candidate_high_requires_review | 9 | 9 |
| Damage | candidate_medium_requires_review | 12 | 12 |
| Damage | not_applicable_to_fault_crosswalk | 99 | 99 |
| Damage | unresolved_below_threshold | 154 | 154 |
| Object Part | candidate_high_requires_review | 27 | 27 |
| Object Part | candidate_medium_requires_review | 33 | 33 |
| Object Part | not_applicable_to_fault_crosswalk | 99 | 99 |
| Object Part | unresolved_below_threshold | 115 | 115 |
| asset_state | keep_as_asset_state_operational_context | 85 | 85 |
| asset_state | review_repair_or_maintenance_as_secondary_activity_type_signal | 3 | 3 |

## By Namespace And Target

| namespace | target | rows | estimated_events |
| --- | --- | ---: | ---: |
| asset_state | asset_state | 88 | 88 |
| fault_code | Cause | 175 | 175 |
| fault_code | Damage | 175 | 175 |
| fault_code | Object Part | 175 | 175 |
| undetermined_code | Cause | 99 | 99 |
| undetermined_code | Damage | 99 | 99 |
| undetermined_code | Object Part | 99 | 99 |

## Interpretation

`asset_state` is not promoted to Activity Type. Maintenance-like state evidence is routed only as secondary review material, while operational states remain operational context.

Fault-code crosswalk candidates remain `expert_inference`, `silver-medium`, `derived_from_rules`, and `requires_target_review`. No row supports the contractual or POC proxy denominator yet.
