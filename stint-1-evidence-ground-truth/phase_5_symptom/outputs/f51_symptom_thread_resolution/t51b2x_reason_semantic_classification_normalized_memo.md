# T5.1b2X - Normalized Reason Semantic Classification

## Method

This rerun applies telegram-style text normalisation before embedding with `paraphrase-multilingual-MiniLM-L12-v2`. It strips leading numeric codes and placeholders, expands separators, and splits CamelCase before prototype matching.

## Calibration

- Validation rows: `80`.
- Threshold: `0.5`.
- Covered validation rows: `27`.
- Correct covered validation rows: `22`.
- Precision on covered rows: `0.8148`.
- Coverage on validation rows: `0.3375`.
- Proxy F1: `0.4112`.

## Guardrail

This pass remains `expert_inference`, `silver-medium`, and `derived_from_rules`. It emits Symptom candidates for downstream assessment only; nothing is promoted to a denominator here.
