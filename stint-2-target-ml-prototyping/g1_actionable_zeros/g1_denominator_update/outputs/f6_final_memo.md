# F6 final bookkeeping - C1

This register reconciles existing figures; it does not promote candidates, replace frozen STINT_1 evidence, or establish code-classification accuracy. The source of each row is the sole file in `source_file`. The key is `target x path x level x metric_id`, because volume and agreement cannot honestly share one source row. No figures are summed across paths or levels.

## Metric vocabulary

The closed `metric_id` vocabulary in this release is:

```text
ac1_g01_v21, agreement_raw_g01_v21,
compression_b2_with_date, compression_b2_without_date, compression_path_a,
agreement_chosen_code_all_comparable, agreement_chosen_code_prior_implied_node,
agreement_chosen_code_prior_implied_none,
agreement_identical_description_all_comparable,
agreement_identical_description_prior_implied_node,
agreement_identical_description_prior_implied_none,
agreement_equal_score_all_comparable, agreement_equal_score_prior_implied_node,
agreement_equal_score_prior_implied_none,
enabled_codes_pmmuww,
kappa_g01_v21, kappa_g01_v2_group, kappa_g01_v2_group_code, kappa_g20_diagnostic,
partition_share_component_description, partition_share_pmmuww_description,
volume_component_concept_ambiguous_node, volume_component_concept_no_node,
volume_component_no_component_concept, volume_component_no_profiled_component_candidate,
volume_component_no_turbine_node, volume_component_resolved,
volume_contractual, volume_corpus_anchor,
volume_crosswalk_enabled_codes_no_score, volume_crosswalk_exact_equivalent,
volume_crosswalk_no_enabled_codes_under_subtree, volume_crosswalk_no_turbine_subtree,
volume_crosswalk_orders, volume_crosswalk_original_code_available,
volume_crosswalk_pairs, volume_crosswalk_restricted_medium_weak,
volume_crosswalk_restricted_strong,
volume_domain_anchor_j, volume_domain_candidate_catalogue_wide_only,
volume_domain_candidate_under_pmmuww, volume_domain_no_catalogue_code,
volume_external_semantic_d2, volume_frozen_f6, volume_frozen_zero,
volume_overlap_work_no_code, volume_prior_f6_proxy,
volume_profile_agreement_cohort_prior_implied_node,
volume_profile_agreement_cohort_prior_implied_none,
volume_profile_consensus_ambiguous_node, volume_profile_constrained_candidate,
volume_structural_match, volume_unique_node
```

`volume` counts a stated unit in a stated universe. `enabled_codes` describes answer space, not classified records. `kappa`, `ac1`, and `agreement_raw` describe diagnostic overlap, not population precision. `compression` is snapshot rows per estimated event, not an ML result. `partition_share` is the percentage of shared normalized catalogue descriptions in one profile set, weighted by the 3,217 comparable orders; it is not the percentage of orders sharing descriptions. The three `agreement_*` metrics count orders under alternative profile/code equivalence tests, not independently validated labels.

## Readings

- MAT is the sole contractual denominator: 10,749 B1 orders. FLOC turbine is 10,699 structurally aligned orders; FLOC leaf remains zero admitted. Component-profile resolution (3,935) is a distinct text-derived candidate claim, not FLOC leaf admission or code accuracy.
- The B1 Object Part and Activity corpus-anchor volumes (7,668 and 7,606) describe the full cleaned corpus of 10,749. The Damage, Cause and Symptom G2.0d2 volumes (3,078, 289 and 104) use the 9,263 model-eligible construction orders. Do not compare these as like-for-like prevalence estimates. G2.0j Symptom 106 and Cause 135 use the same 9,263 as G2.0d2 but different presence prototypes; no subtraction across methods.
- G1.1f retains 3,013 crosswalk orders and 5,778 order x group-code pairs as different units. The 2,868 profile-constrained candidate orders are 1,207 original-code-available + 1,401 exact-equivalent + 230 restricted-strong + 30 restricted-medium/weak. This includes weaker candidates and is not validated precision. The remaining 145 orders are the two no-subtree and 143 enabled-code/no-score categories.
- Activity's 39/75 work-without-code and its kappa 0.893 are diagnostic agreement on the shared sample; they do not establish population catalogue coverage. Damage's group and group+code kappas are reported separately. The prior F6 proxy rows remain marked historical, rather than silently overwritten by domain signal.
- Path A and B2 values preserve their frozen F6 units. `candidate_text_row_or_hash` is retained for the three Symptom source strata because translating it into `event` would misstate the original unit. All Path A/B2 proxy rows remain contingent on upstream episode reconstruction. Compression is 1.66x for Path A, 1.07x for B2 with date (B2.5 refinement), and 4.32x for B2 without date (B2.2); these are different grouping rules.
- The 128-token limit remains attached to G2.0d2 and G2.0j. LLM annotators supplied the diagnostic agreement; this is not human-SME validation. Historical F6 proxies and new domain candidates are not the 95% contractual target.
- C1b reproduces G2.0k.6 order-weighted shared-description percentages from its private profile/code detail and the frozen catalogue: Symptom 9.52/41.61, Object Part 0/0, Damage 48.43/20.62, Cause 14.47/43.76, Activity 22.76/26.68 (component-set share / PMMUWW-set share). G1.1f profile agreement is 54 chosen-code, 138 identical-description and 143 equal-score among 1,120 comparable orders. The cohorts are 248 prior implied-node orders and 872 prior implied-none orders; the sanitized C1b table records each numerator by cohort. All are `diagnostic, derived`; neither changes F6 denominators or measures code precision.

## Assertions

`c1b_persist_diagnostics.py` asserts the ten reported percentages, 248/872 cohorts and 54/138/143 agreement counts before writing sanitized derived tables. `f6_register_final_denominators.py` asserts persisted input figures, 3,013 order categories, 5,778 pairs, 2,868 candidate-category sum, 10,749 component partition, and unique `target x path x level x metric_id` keys. Every output row has one source file, unit, evidence level, layer and condition. C1 is bookkeeping complete, not model acceptance.
