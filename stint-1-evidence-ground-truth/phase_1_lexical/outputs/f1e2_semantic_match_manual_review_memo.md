# F1e2 Semantic Match Manual Review

## Scope

This pass records a manual semantic review of the 30-row F1e sample. The reviewer saw the
pipeline-proposed anchor, so this is `human_validated_pipeline_proposal`, not independent
annotation. It does not create ground truth, does not create held-out evaluation evidence,
and does not promote any row to contractual measurement readiness.

## Result By Band

| band | sample rows | correct | doubtful | incorrect | correct % | correct or doubtful % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| high | 10 | 10 | 0 | 0 | 100.00 | 100.00 |
| middle | 10 | 3 | 2 | 5 | 30.00 | 50.00 |
| borderline | 10 | 1 | 2 | 7 | 10.00 | 30.00 |

## Overall Result

| result | rows |
| --- | ---: |
| correct | 14 |
| doubtful | 4 |
| incorrect | 12 |

## Interpretation

- The high-score band had no observed errors in the QA sample (`n=10`); this is not a performance precision claim.
- The middle band is mixed; it should remain reviewable evidence, not automatic promotion.
- The borderline band is mostly noisy; raising thresholds or routing borderline rows to unresolved/manual review is likely better than carrying noise into F2.

## Controls

- Review is based on redacted observed terms and the pipeline-proposed redacted canonical concepts.
- Versioned outputs contain keys, metadata, scores, and review results only.
- Internal redacted review detail remains under `reports/internal/`, which is ignored by Git.
- All rows remain non-independent for STINT_2 because the anchor proposal was visible to the reviewer.
