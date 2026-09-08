# T5.1b2.4 - Reason Semantic Classification

## Method

Prototype similarity classification using `paraphrase-multilingual-MiniLM-L12-v2` and `semantic_prototype_matching_v1`. This is not a trained classifier and does not promote any row to a denominator.

## Calibration

- Validation rows: `80`.
- Selected threshold: `0.58`.
- Covered validation rows: `11`.
- Correct covered validation rows: `11`.
- Precision on covered validation rows: `1.0`.
- Coverage on validation rows: `0.1375`.

## Subset Guardrail

Metrics are also emitted by validation subset because the residual sample intentionally over-represents difficult cases.

## Circularity Guardrail

The reviewed rows calibrate this semantic rule. They are `model_blind_review` calibration material and a potential seed for future independent annotation; they are not a held-out evaluation set for STINT_2 if the same semantic-prototype mechanism is used.
