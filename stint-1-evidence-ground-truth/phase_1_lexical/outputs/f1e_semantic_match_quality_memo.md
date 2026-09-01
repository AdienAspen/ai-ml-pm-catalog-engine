# F1e Semantic Match Quality Check

## Scope

This pass audits the F1d4 semantic grouping output before freezing the F1 lexical layer.
It does not create additional labels and does not promote any evidence to contractual
measurement readiness.

## Thresholds

F1d4 used target-specific cosine thresholds:

| target | threshold |
| --- | ---: |
| Activity | 0.52 |
| Activity Type | 0.52 |
| Cause | 0.48 |
| Damage | 0.48 |
| Object Part | 0.52 |
| Symptom | 0.48 |
| unknown | 0.56 |

## Score Bands

| band | rows |
| --- | ---: |
| borderline | 747 |
| high | 2773 |
| middle | 1367 |
| unresolved_below_threshold | 2903 |

## Interpretation

- `high` means the semantic score is at least `max(0.70, threshold + 0.12)`.
- `middle` means the score is above threshold but not close to either the high band or the cutoff.
- `borderline` means the score is within `0.06` of the target threshold.
- `unresolved_below_threshold` remains unresolved and is not promoted.

## Manual Review Sample

A 30-row sample was generated for precision review: 10 high-score anchors, 10 middle-score
anchors, and 10 borderline anchors, subject to availability. The versioned sample contains
only keys, target metadata, thresholds, scores, provenance fields, and no raw operational
values. An internal redacted review file was also generated under `reports/internal/`, which
is ignored by Git.

## Controls

- All rows remain `expert_inference` or `unresolved`.
- All mapped rows remain `evaluation_independence = derived_from_rules`.
- These anchors may support weak supervision and POC proxy evidence after review.
- They do not support contractual denominators or independent STINT_2 evaluation as-is.
- `translation_alias_es` added little net coverage, which supports the multilingual-backbone
  decision over broad pre-translation.

## Decision

F1 is not frozen by this pass. The semantic layer is ready for manual precision review.
