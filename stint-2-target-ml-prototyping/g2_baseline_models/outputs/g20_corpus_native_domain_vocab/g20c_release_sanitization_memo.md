# G2.0c release sanitization and reconciliation

The pre-push gate found restricted operational names in six CSVs (142 repeated cells, representing 39 path-term candidates). They are removed, not renamed or turned into new vocabulary. The local restricted-term policy also catches substrings inside compounds; ambiguous matches are conservatively excluded.

## Current state

- Candidates: 79,369 -> 79,330. Filtered rows: 24,841 -> 24,825.
- Cluster members: 24,421 -> 24,405; 256 stable IDs and 67 assigned concepts.
- Normalization and evaluation/heldout exclusion universes are unchanged.
- Step 3b assignments and 13 reviewed-concept exclusions reconcile exactly.
- Step 4 mapping reconciles; input hashes reflect the corrected artefacts.
- Step 5 is recomputed from the masked corpus with corrected dictionaries.

## Method limitation

This is post-fit member pruning with stable concept IDs, not re-clustering. Original centers, similarity scores and silhouette describe the historical fit. Member summaries and concentration are recomputed. Restricted terms can no longer be emitted as candidates or matched as vocabulary anchors, but this does not claim removal of their prior influence on fitted geometry.

Pre-correction counts in earlier notes are historical; this report and the release count/coverage ledgers are authoritative for publication. Full original artefacts are retained only in ignored internal storage (700/600).

One Path A unit no longer matches a reviewed concept after pruning. Its historical instrument-exposure exclusion remains in the preserved-evaluation-exclusions ledger for both targets. A reduction in current lexical matches never restores evaluation eligibility; future evaluation must union that ledger with the existing exclusions.

No model training, F6 update, evaluation-label change, or G2 closure occurred.
