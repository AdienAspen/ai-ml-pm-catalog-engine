# T3.5.6 Path A Integrated NOTES Crosswalk

## Scope

This pass integrates code-derived candidates from `T3.5.5` with NOTES-derived candidates from `T3.5.3`. It fixes the gap where NOTES prose was used only as code context but not emitted as its own evidence source.

## Summary

- Estimated events input: `362`
- Integrated evidence rows: `848`
- Integrated event-target pairs: `771`
- Code estimated events with any integrated evidence: `209`
- NOTES-only event candidate keys: `312`
- Event or candidate keys with any integrated evidence: `521`
- Code candidate rows: `117`
- NOTES candidate rows: `731`
- Converged event-target pairs: `6`
- Contractual denominator supported: `False`
- POC proxy denominator supported: `False`

## By Source And Target

| evidence_source | target | rows | event_targets |
| --- | --- | ---: | ---: |
| code_context | Cause | 36 | 36 |
| code_context | Damage | 21 | 21 |
| code_context | Object Part | 60 | 60 |
| notes_region | Activity | 381 | 339 |
| notes_region | Damage | 99 | 98 |
| notes_region | Object Part | 251 | 223 |

## Code + NOTES Convergence

| target | rows | converged_events |
| --- | ---: | ---: |
| Damage | 7 | 3 |
| Object Part | 6 | 3 |

## Interpretation

Activity appears only through `NOTES`, as expected. Numeric codes remain weak for Activity because they describe state/condition rather than technician action.

The integrated evidence includes both deduplicated code-table events and NOTES-only event candidates. These are reported separately so the code event universe is not confused with candidate events created from prose.

`asset_state` remains separate and is not promoted to Activity Type. All NOTES joins are candidate joins and require target review before denominator use.

The `910` scoring rows in `T3.5.5` are unrelated to the historical `910` denominator issue; here they are the explicit expansion of the cleaned code event universe.
