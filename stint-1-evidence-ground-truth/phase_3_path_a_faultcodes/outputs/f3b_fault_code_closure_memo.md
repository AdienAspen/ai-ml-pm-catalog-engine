# F3b Fault Code Closure Check

## Scope

This mini-pass closes the F3 accounting language before Path B. It does not change the
F3 scoring results and does not manually validate candidate mappings.

## Scoring Matrix, Not Crosswalk

| metric | value |
| --- | ---: |
| scoring matrix rows | 316 |
| high candidate rows | 12 |
| medium candidate rows | 31 |
| unresolved rows | 273 |

The `316` rows are a scoring matrix: `79` fault-code keys scored against `4` target
families. They are not `316` mappings.

## High Candidate Review Queue

| metric | value |
| --- | ---: |
| high candidate rows | 12 |
| distinct fault-code keys with high candidates | 10 |
| codes with one high target | 8 |
| codes with multiple high targets | 2 |

The 12 high rows correspond to 10 fault-code keys. Two keys have high candidates in more
than one target family, so downstream denominators must not count them as independent
evidence without target-specific review.

## Activity Finding

`Activity` has zero high and zero medium candidates across the 79 fault-code keys. This is
treated as a domain finding: fault codes describe condition/state, not technician action.

## Controls

- No high candidate is promoted by F3b.
- Blind review is required before any candidate can become independent review evidence.
- All F3 candidates remain `expert_inference`, `silver-medium`, and `derived_from_rules`.
- Measurement readiness remains unchanged.
