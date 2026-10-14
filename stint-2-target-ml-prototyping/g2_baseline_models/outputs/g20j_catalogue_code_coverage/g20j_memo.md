# G2.0j - Catalogue code coverage and residual characterization

Report only: no training, mapping to production, candidate promotion or F6 change.
All results are uncalibrated semantic candidates, not verified code assignments.
Catalogue and presence thresholds 0.50 were frozen before observing this run.
They are inherited historical values, not calibrated on these new class spaces.
Unit text uses semantic_normalisation_v2 after G2.0b masking; prototype code
descriptions are verbatim. All thirteen source leakage rows are checked masked.

## Universe and class-space controls

B1 eligible 9,263; Path A 159; B2 1,478. Full-corpus exclusions are separately
registered. No unit counts or residuals are aggregated across paths.
B2 preserves its inherited event universe and remains provisional because its
source identity does not reconcile with historical F6; no silent repair was made.
Symptom S: 1 PMMUWW group -> 6 codes; catalogue-wide 4,171 group-code pairs.
Cause 5: 1 PMMUWW group -> 13 codes; catalogue-wide 6,232 group-code pairs.
Both class spaces score the SAME eligible units. PMMUWW for orders without
that structural profile is counterfactual, not a fabricated asset assignment.
The 9,151 structural PMMUWW orders overlap the 3,934 component-profile orders.
Those components have 30 profiles, only 50 PMMUWW; their code spaces are not
all PMMUWW. Their text-derived dependency is retained and not independently evaluated.

## Coverage

| Target | Path | Space | n | Assigned | Coverage | Domain | Gap | No anchor | Top share |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cause | B1_RELATIONAL | catalogue_wide | 9263 | 4284 | 46.25% | 135 | 17 | 4962 | 14.24% |
| Cause | B1_RELATIONAL | profile_scoped | 9263 | 213 | 2.30% | 135 | 121 | 8929 | 53.05% |
| Cause | B2_WORKBOOKS | catalogue_wide | 1478 | 821 | 55.55% | 109 | 9 | 648 | 28.75% |
| Cause | B2_WORKBOOKS | profile_scoped | 1478 | 112 | 7.58% | 109 | 14 | 1352 | 85.71% |
| Cause | PATH_A | catalogue_wide | 159 | 156 | 98.11% | 53 | 0 | 3 | 33.33% |
| Cause | PATH_A | profile_scoped | 159 | 24 | 15.09% | 53 | 43 | 92 | 45.83% |
| Symptom | B1_RELATIONAL | catalogue_wide | 9263 | 3753 | 40.52% | 106 | 6 | 5504 | 10.42% |
| Symptom | B1_RELATIONAL | profile_scoped | 9263 | 218 | 2.35% | 106 | 92 | 8953 | 78.90% |
| Symptom | B2_WORKBOOKS | catalogue_wide | 1478 | 589 | 39.85% | 21 | 0 | 889 | 22.07% |
| Symptom | B2_WORKBOOKS | profile_scoped | 1478 | 5 | 0.34% | 21 | 21 | 1452 | 80.00% |
| Symptom | PATH_A | catalogue_wide | 159 | 146 | 91.82% | 20 | 0 | 13 | 23.29% |
| Symptom | PATH_A | profile_scoped | 159 | 4 | 2.52% | 20 | 20 | 135 | 50.00% |

## Presence and gap interpretation

Cause presence uses exactly nine WMEP causes. Symptom uses the single
frozen ZEUS detection_symptom container definition as a presence-test
prototype, plus eight WMEP effects as operational-consequence references.
The ZEUS container is not represented as a developed lexicon. Both are
imperfect, explicit presence tests and cannot prove subject matter.
no_catalogue_code = domain anchored AND no catalogue score >= threshold.
no_anchor_at_all = neither detector anchors; NOT proof of no target signal.
no_applicable_rate denominator is domain-anchored units; the separate
no_catalogue_code_rate_of_universe uses all evaluated units.
A gap can arise from catalogue expressiveness, profile restrictions or
detector/threshold limitations; this run alone does not distinguish them.
Catalogue-only matches are reported separately: matching a code does not
establish target presence or true classification.

## Assignment ambiguity and fallback descriptions

Catalogue keys are type|group|code. Ties within 1e-6 are explicitly counted;
the displayed assignment uses stable lexicographic tie-breaking, not truth.
Identical descriptions across groups can inflate top-code concentration.
PMMUWW OTH/NOTH are unspecified fallback codes and separately counted;
they do not demonstrate that a specific symptom/cause was expressed.

## Residual characterization

Only eligible masked gap texts generate 1-3 grams. G2.0c path frequency
floors and neutral shape/generic/safety filters are reused. Semantic grouping
uses normalized MiniLM vectors and MiniBatchKMeans with frozen sqrt(n)
k rule capped at 256, member cosine >=0.50 and at least two members.
Canonical labels are centroid/frequency summaries, not analyst adjudication.
Concept frequency deduplicates physical units across all member ngrams.
Concepts can overlap; their unit counts must not be summed. Empty residuals
and small ungrouped sets are explicitly registered, not silently omitted.
Top 20 and >5% concentration are separate files; concepts are diagnostic
and never promoted into vocabulary, training or evaluation from this run.

## Historical contrast and plan corrections

The 104 Symptom / 289 Cause B1 historical semantic values are contrasted
on identical eligible unit keys. The earlier Cause instrument included
NREL as well as WMEP; the old Symptom instrument had eight WMEP effects
and no developed ZEUS symptom lexicon. Deltas are descriptive, not improvement.
A literal lexical-to-semantic contrast would change detectors; these two
historical values specifically come from the semantic G2.0d2 scores.
The plan Activity example 1/375 is stale: corrected v2.1 has 6/375 responses,
none in the 75 shared units. Those annotations were not used for this run.
No independent precision, recall, F1, final-heldout or SAP correctness claim.
