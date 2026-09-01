# F1d4 - Semantic Grouping With Translation Aliases

## Purpose

This pass uses multilingual sentence embeddings to anchor observed lexical term keys to canonical concepts and Spanish translation aliases.

It emits only keys, IDs, scores, and aggregate metadata. It does not emit observed terms or canonical concept text.

## Result

- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Input rows: 7790
- Mapped rows: 4887
- Unresolved rows: 2903
- Mapped percentage: 62.73%
- Distinct canonical concepts mapped: 579

## Target Summary

| target | rows | mapped_rows | unresolved_rows | mapped_pct | distinct_canonical_concepts |
|---|---:|---:|---:|---:|---:|
| Activity | 879 | 318 | 561 | 36.18 | 11 |
| Activity Type | 11 | 0 | 11 | 0.0 | 0 |
| Cause | 175 | 141 | 34 | 80.57 | 30 |
| Damage | 347 | 277 | 70 | 79.83 | 53 |
| Object Part | 1492 | 1272 | 220 | 85.25 | 119 |
| Symptom | 286 | 190 | 96 | 66.43 | 29 |
| unknown | 4600 | 2689 | 1911 | 58.46 | 424 |

## Governance

- Semantic matches are `expert_inference`, not `validated_mapping`.
- All labels remain `derived_from_rules`; they cannot evaluate the same rule set in STINT_2.
- `unresolved` remains an expected and valid output.
- Translation alias layer was used, but aliases remain `expert_inference` and preserve the original canonical concept ID.
