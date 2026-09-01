# F1d2 - Semantic Domain Grouping

## Purpose

This pass uses multilingual sentence embeddings to anchor observed lexical term keys to canonical concepts without pre-translating the corpus.

It emits only keys, IDs, scores, and aggregate metadata. It does not emit observed terms or canonical concept text.

## Result

- Embedding model: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Input rows: 7790
- Mapped rows: 4878
- Unresolved rows: 2912
- Mapped percentage: 62.62%
- Distinct canonical concepts mapped: 573

## Target Summary

| target | rows | mapped_rows | unresolved_rows | mapped_pct | distinct_canonical_concepts |
|---|---:|---:|---:|---:|---:|
| Activity | 879 | 318 | 561 | 36.18 | 11 |
| Activity Type | 11 | 0 | 11 | 0.0 | 0 |
| Cause | 175 | 141 | 34 | 80.57 | 28 |
| Damage | 347 | 277 | 70 | 79.83 | 52 |
| Object Part | 1492 | 1272 | 220 | 85.25 | 120 |
| Symptom | 286 | 189 | 97 | 66.08 | 29 |
| unknown | 4600 | 2681 | 1919 | 58.28 | 422 |

## Governance

- Semantic matches are `expert_inference`, not `validated_mapping`.
- All labels remain `derived_from_rules`; they cannot evaluate the same rule set in STINT_2.
- `unresolved` remains an expected and valid output.
- Translation alias layer was not used in this pass; it is a separate follow-up layer.
