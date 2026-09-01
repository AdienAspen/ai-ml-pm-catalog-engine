# F1d - Domain Grouping Against Canonical Vocabulary

## Purpose

This pass anchors observed lexical term keys to canonical vocabulary concepts where a conservative domain match exists.

It does not emit observed terms or canonical text, and it does not create validated mappings.

## Expectations Before Run

- Damage should anchor better than before because F1c2 added external failure/damage vocabulary.
- Cause may anchor where WMEP causes apply.
- Symptom is expected to remain mostly unresolved because only eight public failure-effect anchors are available.

## Results

- Input rows: 7790
- Mapped rows: 408
- Unresolved rows: 7382
- Mapped percentage: 5.24%
- Distinct term keys: 5710
- Distinct canonical concepts mapped: 104

## Target Summary

| target | rows | mapped_rows | unresolved_rows | mapped_pct | distinct_canonical_concepts |
|---|---:|---:|---:|---:|---:|
| Activity | 879 | 22 | 857 | 2.5 | 5 |
| Activity Type | 11 | 0 | 11 | 0.0 | 0 |
| Cause | 175 | 17 | 158 | 9.71 | 4 |
| Damage | 347 | 12 | 335 | 3.46 | 7 |
| Object Part | 1492 | 165 | 1327 | 11.06 | 30 |
| Symptom | 286 | 0 | 286 | 0.0 | 0 |
| unknown | 4600 | 192 | 4408 | 4.17 | 70 |

## Governance

- Grouping links are `expert_inference`, not `validated_mapping`.
- All rows are `derived_from_rules`; they cannot be used as independent held-out labels for STINT_2.
- `unresolved` is an expected output and must not be forced into a concept.
- Damage-adjacent evidence preserves vocabulary owner, subsystem, and semantic level to avoid flattening heterogeneous evidence sets.
