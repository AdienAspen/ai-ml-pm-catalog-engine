# G2.0c Step 3 - Semantic Grouping

## Method

The 24,841 Step 2 terms were embedded with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and grouped with
MiniBatchKMeans over normalized semantic embeddings. String distance was not used.
Candidate cluster counts were compared using cosine silhouette on a deterministic
3,000-term sample; `k=256` was selected.

Members below cosine 0.50 or clusters with fewer than
2 accepted members remain unresolved. The resulting vocabulary
contains 256 concepts and 24,421 grouped path-term rows.

## Target assignment

Target assignment occurred only after semantic grouping. It used frozen ZEUS/IEC/F1c2
reference scopes, one generic descriptor per target, a declared generic maintenance
action lexicon, and a declared generic component-head lexicon. No G2.0 prototype or
evaluation text was reused; both lexical lists are registered as analyst-authored rather
than corpus-derived evidence. Object Part was never assigned as the residual class;
insufficient or conflicting evidence yields `unassigned` or `ambiguous`.

## Concentration

Concentration is reported separately by target and path. The Step 3 blocking gate is
surface-variant concentration, the quantity directly governed by semantic grouping.
Non-deduplicated unit-mention weight is retained as a diagnostic warning only: overlapping
n-grams can count the same physical unit repeatedly (for example, `blades`, `ground blades`,
and `high ground blades`). Exact `physical_record x target` coverage requires the unit-level
pass in Step 5 and is not inferred here.

## External reference layer

The three B2 external reference terms remain separate because their frozen target is
Damage, outside this Activity/Object Part grouping scope. They did not affect clustering,
target assignment, or concentration.

## Boundaries

No SAP mapping, catalogue-gap decision, denominator change, candidate promotion, model
training, or G2.0 rerun occurred.

## Release sanitization correction

The original six-token guard was incomplete. The broader local restricted-term policy removes 39 path-term candidates and 16 clustered variants. Current counts are 79,330 candidates, 24,825 filtered rows and 24,405 members. All 256 concept IDs and canonical labels remain stable. Member statistics and concentration are recomputed; original fitted centers, silhouette and target scores are historical, not a claim of a fresh clean fit. No restricted variant remains usable as an anchor. Step 3b, mapping and unit coverage are rerun separately. See the release reconciliation report for current results.
