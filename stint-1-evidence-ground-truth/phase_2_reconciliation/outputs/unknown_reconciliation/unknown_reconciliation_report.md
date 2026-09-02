# F2 Unknown Reconciliation Report

## Scope

This report reconciles the historical `unknown` pair-discovery rows and the newer F1
high-confidence lexical assignments whose observed target hint was `unknown`.

## Pair-Discovery Unknowns

| metric | value |
| --- | ---: |
| unknown pair rows | 802 |
| pattern groups | 22 |

| classification | pair rows |
| --- | ---: |
| matched_vocabulary | 18 |
| out_of_scope | 662 |
| pending | 94 |
| unrelated_cooccurrence | 28 |

## F1 Lexical Unknowns

| metric | value |
| --- | ---: |
| high-confidence target assignments from unknown hint | 1414 |
| unresolved/rework rows from unknown hint | 3186 |

| assigned target | high-confidence rows |
| --- | ---: |
| Activity | 63 |
| Cause | 198 |
| Damage | 163 |
| FLOC leaf | 333 |
| Object Part | 579 |
| Symptom | 78 |
| unresolved_or_rework | 0 |

Rows routed to unresolved/rework from unknown hint: `3186`.

## Count Reconciliation

`192` and `1,414` are different stages/views of the lexical layer, not an undeclared
expansion:

- `192` = originally-unknown rows mapped by the F1d1 string/token baseline.
- `2,689` = originally-unknown rows mapped by F1d4 semantic matching before quality filtering.
- `1,414` = originally-unknown rows that F1f retained as
  high-confidence candidate targets after the quality filter.

Therefore `1,414 > 192` is valid because it compares F1f high-confidence semantic matches
against the earlier F1d1 baseline, not against the same matching method.

## Out-of-Scope Rule

Rows are classified as `out_of_scope` when their pattern is explained by spreadsheet layout
artifacts, temporal fields, scheduling fields, duration/quantity fields, or similar metadata
co-occurrences rather than by a source text concept paired to a target code or controlled
vocabulary.

## Interpretation

- The historical `unknown` pair rows are not a single backlog. They split into schema/layout artifacts, identifier joins, temporal metadata, and a smaller set of narrative/status candidates.
- The F1 lexical layer assigns some formerly `unknown` lexical evidence to candidate targets, but those assignments remain `expert_inference` and `derived_from_rules`.
- No row is promoted to contractual evidence by this pass.
- Group review is pattern-based and sanitized. Human confirmation can be applied at group level without inspecting all 802 rows.
