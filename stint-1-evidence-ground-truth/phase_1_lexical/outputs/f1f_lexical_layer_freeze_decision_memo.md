# F1f Lexical Layer Freeze Decision

## Decision

`LEXICAL_LAYER v2` is closed for F2 consumption as a high-confidence candidate layer.
The prior semantic mapping coverage is retained as diagnostic coverage, not quality.

## Coverage After Quality Filter

| metric | value |
| --- | ---: |
| input rows | 7790 |
| mapped rows before quality filter | 4887 |
| mapped pct before quality filter | 62.73% |
| usable high-confidence rows | 2773 |
| usable high-confidence pct | 35.60% |
| high-confidence distinct canonical concepts | 359 |
| routed to unresolved/rework | 5017 |

## Manual Review Basis

| score band | manual review result |
| --- | --- |
| high | QA sample result, n=10, no errors observed |
| middle | 3 correct / 2 doubtful / 5 incorrect |
| borderline | 1 correct / 2 doubtful / 7 incorrect |

## Routing Rule

- `semantic_anchor_high` is retained as the F2 candidate input.
- `middle` is routed to unresolved/rework, not auto-promoted.
- `borderline` is routed to unresolved/rework, not auto-promoted.
- `unresolved_below_threshold` remains unresolved.

## Controls

- The high-confidence layer remains `expert_inference` and `derived_from_rules`.
- It can support POC proxy review workflows after F2 target review.
- It cannot support contractual denominators.
- The 30 manually reviewed rows are preserved as `human_validated_pipeline_proposal`.
- They are calibration material and potential seed for future independent annotation, not a held-out evaluation set, because the pipeline-proposed anchor was visible to the reviewer.
- A truly independent review requires blind annotation: observed term plus allowed catalog, without the pipeline proposal.
