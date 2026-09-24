# G2.0c Step 3b - Bounded Anchor Expansion

Step 3 grouping remained frozen at 256 concepts. No cluster was rebuilt and no
threshold was lowered. Only concepts that were `unassigned` in Step 3 were
re-evaluated with the bounded corpus-inspection anchor families.

All 25 new lexical anchors carry
`construction_method=derived_from_corpus_inspection` and remain separate from externally
transcribed anchors. The 10 diagnostic concepts plus the 3 additional concepts
inspected during Step 3b QA are registered with
`eligible_for_future_evaluation=false` for Activity and Object Part.

```
before  {'unassigned': 191, 'Object Part': 40, 'Activity': 21, 'ambiguous': 4}
after   {'unassigned': 185, 'Object Part': 43, 'Activity': 24, 'ambiguous': 4}
changed 6 concept assignments
```

The maximum target-by-path surface concentration changed from
23.62% to
23.38%. All six blocking surface
concentration gates remain at or below 30%. Non-deduplicated unit-mention weights
remain diagnostic only; exact physical-unit concentration is deferred to Step 5.
