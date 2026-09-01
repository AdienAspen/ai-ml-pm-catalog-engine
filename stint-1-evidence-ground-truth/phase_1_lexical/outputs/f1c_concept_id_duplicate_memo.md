# F1c - Concept ID Duplicate Check

## Purpose

This check determines whether repeated `concept_id` values in the canonical vocabulary are ambiguous collisions or repeated occurrences of the same concept across context.

It emits counts only and no canonical text, codes, or source-derived values.

## Result

- Vocabulary rows: 14479
- Distinct concept IDs: 13816
- Duplicate concept-id groups: 200
- Duplicate rows total: 863
- Ambiguous duplicate concept IDs: 0
- Ambiguous duplicate rows: 0
- Max rows per duplicate ID: 9

## Interpretation

The duplicate concept IDs are not ambiguous under the checked dimensions: owner, target, namespace, target field, concept role, and canonical concept key remain stable within duplicate groups.

For F1d, repeated rows should be treated as contextual occurrences of the same concept, not separate concepts.
