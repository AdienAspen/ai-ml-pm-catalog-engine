# G2.0c Step 1 - Neutral Corpus-Native N-gram Extraction Rerun

## Status

Step 1 was regenerated as a target-neutral extraction. No filtering, semantic grouping,
catalogue mapping, candidate promotion, denominator change, or G2.0 rerun was performed.

## Universes

Two universes are registered:

- `descriptive_full_corpus`: all source units, used for descriptive statistics only.
- `model_eligible_construction_corpus`: excludes every `evaluation_set_v1` source unit
  and every source unit currently marked held-out in a split manifest. Only this universe
  emits candidate terms and may construct the future vocabulary.

Some B1, Path A, and B2 evidence uses historical or surface-specific namespaces. Frozen
G0/G2 exclusions are reconciled through a `semantic_normalisation_v2` fingerprint of the
internal G0.2 visible text. Each source segment and the combined unit text are checked; every
current unit sharing an excluded hash is removed. This also
prevents duplicate text from re-entering under a regenerated event ID.

This duplicate-text exclusion is intentionally conservative and systematically removes
more copies of frequent repeated text. The top-100 term-retention diagnostic compares the
full descriptive universe with the eligible universe without allowing full-corpus terms to
construct the vocabulary.

## Path A limitation

Path A retains 159 of 362 units. The other 203 units (56.08%) are excluded because they
belong to evaluation or share text with evaluation records. Path A vocabulary coverage must
therefore be reported as a small and selectively reduced construction sample.

## Frequent-term retention gate

  path_bucket  top_terms_checked  terms_retained  median_unit_count_retention_pct  minimum_unit_count_retention_pct  fully_lost_terms  retained_below_50pct_terms  terms_retained_pct                       diagnostic_scope  candidate_construction_from_full_corpus  raw_operational_values_emitted
B1_RELATIONAL                100             100                        95.142936                         48.634590                 0                           1               100.0 top_terms_from_descriptive_full_corpus                                    False                           False
 B2_WORKBOOKS                100              89                        92.857143                          0.000000                11                          11                89.0 top_terms_from_descriptive_full_corpus                                    False                           False
       PATH_A                100             100                        43.610547                          2.857143                 0                          74               100.0 top_terms_from_descriptive_full_corpus                                    False                           False

Interpretation:

- B1 retains all top-100 terms; median unit-count retention is
  95.14%.
- Path A retains all top-100 term forms, but
  74 of them retain less
  than half their original unit count. Eligible Path A frequencies are not population
  prevalence estimates.
- B2 retains 89 of its top 100.
  The fully lost terms are: site technician, site lead, bearing failure, main bearing failure, found, in, is, casting, crack, hub casting, as. These remain descriptive findings
  only and may not be reintroduced as vocabulary seeds from evaluation text.

## Leakage masking

The G2.0b regex catalogue is applied before normalisation. The expected 13 leaked B1
source rows were all detected and masked on the G2.0c source fields. Mask tokens are
removed before n-gram emission and cannot become candidate terms.

## Normalisation and extraction

- Normalisation version: `semantic_normalisation_v2`.
- B1 source fields: `reason` and `descriptionExtended` only.
- N-grams: 1 to 3 words.
- Generic maintenance abbreviations use the separately versioned analyst-authored map.
- Known operational organisation and site tokens are removed before n-gram extraction.
- G2.0 prototypes, ZEUS target prototypes, and SAP catalogue concepts were not used as seeds.

## Target assignment

Every row has `target=unassigned`. The `construction_method` is
`corpus_extracted_neutral_ngram_target_assignment_deferred_to_semantic_grouping`. Assignment to Activity or Object Part is explicitly deferred
until after Step 2 filtering and Step 3 semantic grouping.

## Structural decisions

1. Extract, then group semantically, then map to the catalogue.
2. Group by semantic similarity, not string distance.
3. Never use G2.0 prototypes as vocabulary seeds.
4. Retain `top_concept_share` as a Step 5 generic-concept detector.
