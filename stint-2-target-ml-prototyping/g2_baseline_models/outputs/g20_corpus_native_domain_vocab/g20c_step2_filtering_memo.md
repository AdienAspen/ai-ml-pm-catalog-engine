# G2.0c Step 2 - Filtering

## Scope

Filtering only. No target assignment, semantic grouping, catalogue mapping,
candidate promotion, denominator change, or model re-run occurred.

## Path-specific frequency floors

- B1_RELATIONAL: 3 eligible units.
- B2_WORKBOOKS: 2 eligible units.
- PATH_A: 1 eligible unit. Path A frequency is not a prevalence estimate after
  evaluation exclusions, so singletons are retained when they pass lexical filters.

## Result

- Input terms: 79,330.
- Retained terms: 24,825.
- Input by path: {'B1_RELATIONAL': 75615, 'B2_WORKBOOKS': 1752, 'PATH_A': 1963}.
- Retained by path: {'B1_RELATIONAL': 22371, 'B2_WORKBOOKS': 684, 'PATH_A': 1770}.

The generic filter removes a phrase only when every token is generic. Mixed phrases
remain available for Step 3. The shape filter removes one-character fragments and
terms outside the declared 1-3 alphabetic-token format.

## External reference layer

The 3 admitted external reference terms remain in their separate
artefact. They were not merged, frequency-filtered, or counted in the reduction
curve. Step 3 may use them only as explicitly sourced coverage evidence.

## Governance

- Construction universe: model_eligible_construction_corpus.
- Normalisation: semantic_normalisation_v2.
- Target remains unassigned until Step 3 semantic grouping.
- Evaluation text was not used.
- Raw operational values emitted: false.
