# T8 - Lexical Seed Dictionary

## Purpose

T8 builds a seed lexical layer from sampled real records as a contact/calibration test for `reference-layer-v1`.

It does not execute the STINT_1 candidate pipeline and does not claim target-level denominators or model performance.

## Result

- Records inspected/captured by sampling: 600
- Minimum required: 500
- Minimum met: True
- Unique lexical entries: 14235
- Target summary: `{'unknown': 11002, 'Activity': 909, 'Object Part': 1501, 'Symptom': 289, 'Cause': 176, 'Damage': 347, 'Activity Type': 11}`
- Sample strata: `{'other_explicit_value': 120, 'planned_like': 120, 'reactive_like': 120, 'unclassified_explicit_value': 60, 'event_structural': 180}`

## Required Controls

- `source_text_field` is populated for every lexical entry, satisfying the DELTA-0003 control for this artefact.
- `event_structural` PDF rows are not mixed with planned/reactive strata.
- Every non-unknown lexical entry carries a canonical destination field from `canonical-constraints.md`.
- Unknown terms remain unresolved and are not promoted.
- The working dictionary contains source-derived lexical terms and must remain local-only. The versionable dictionary replaces terms with stable keys.

## Outputs

- `reference_layer/lexical_layer/lexical_seed_dictionary_v1.csv` local-only working dictionary
- `reference_layer/lexical_layer/lexical_seed_dictionary_v1_sanitized.csv` versionable keyed dictionary
- `reference_layer/semantic_normalisation/normalisation_pipeline_spec.md`
- `outputs/t8_sampled_records_v1.csv`
- `outputs/t8_lexical_seed_dictionary_summary_v1.json`
