# F1b - Grouping Readiness Check

## Purpose

This check answers whether F1 has demonstrated lexical grouping into canonical concepts.

It emits counts only and no source-derived terms.

## Result

- Rows checked: 7790
- Distinct term keys: 5710
- Distinct concept IDs: 7790
- `canonical_concept` column present: False
- Distinct canonical concepts: None
- Status: `grouping_not_demonstrated_missing_canonical_concept`

## Interpretation

F1 bootstrap filtered singleton unknown terms but did not yet produce a canonical_concept grouping field.

`LEXICAL_LAYER` remains `provisional_pending_token_filtering_and_domain_grouping`.

The current F1 output is a filtered working layer. It is not yet evidence that variants have collapsed into a smaller domain-concept inventory.

## Evaluation Boundary

All lexical rows remain `derived_from_rules`; they are not a held-out evaluation set for STINT_2.
