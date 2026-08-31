# T8c - Observed Term Length Diagnostic

## Purpose

This diagnostic tests whether the high volume in T8/T8b is caused by extracting multi-word phrases or complete text segments instead of lexical terms.

The diagnostic reads the local-only working dictionary, computes word-count distributions over `observed_term`, and emits only aggregate counts. No raw source-derived terms are versioned.

## Result

- Rows inspected: 14235
- Distinct observed terms: 10639
- Word-length distribution: {'1': 3081, '2': 5579, '3': 5575}
- 1-2 word entries: 60.84%
- 3+ word entries: 39.16%
- 5+ word entries: 0.0%
- Median word length: 2.0
- Mean word length: 2.18

## Interpretation

The full text-segment extraction hypothesis is not supported, but the short phrase/n-gram hypothesis is supported. The T8 artefact is not made of long copied segments; however, a substantial share of entries are 3-word observed terms.

The remaining issue is therefore upstream token/n-gram admission and downstream semantic grouping: too many short lexical candidates are being admitted, and too few are being collapsed into canonical domain concepts.

## Decision

`LEXICAL_LAYER` remains provisional. T9 may freeze the other reference-layer objects, but this object should be marked `pending_rework` or `pending_token_filtering_and_domain_grouping` rather than accepted as a final seed dictionary.

## Governance

- No raw source-derived terms are emitted.
- `source_text_field` and `stratum` remain mandatory for downstream rework.
- `Symptom` remains candidate symptom-like lexical signal, not validated ground truth.
