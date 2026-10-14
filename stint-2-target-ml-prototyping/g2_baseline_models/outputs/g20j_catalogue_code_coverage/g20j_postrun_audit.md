# G2.0j - Independent post-run audit

## Integrity checks

- Frozen source hashes and the completed-run output hashes all match.
- Thresholds were frozen at 2026-09-28 22:10:33 UTC, before corpus preparation
  completed at 22:13:25 UTC and before either target was scored.
- Both thresholds are 0.50; no result-based adjustment occurred.
- Model revision: e8f8c211226b894fcb81acc59f3b34ba3efd5f42.
- Independent standard CSV parsing verified 21,800 rows per target, unique
  unit/class-space pairs, consistent field counts and literal provenance fields.
- All 12 target/path/class-space summaries reconcile to four disjoint partitions.
- Eligible units per path: B1 9,263; Path A 159; B2 1,478.
- Prototype-scoped positive units are a subset of catalogue-wide positive units.
- All 13 leaked full-corpus source units matched the frozen masking manifest.
- Private cache files are mode 600, within a mode-700 directory.
- Public CSV schemas contain no raw text, descriptionExtended, reason,
  catalogue description or residual-segment fields. Residual labels passed
  the restricted-term gate and originate from the reused PII-redaction helper.
- Five focused tests passed, covering partitions, duplicate-description ties,
  source-field boundaries, empty residuals and distinct-unit concept frequencies.
- Frozen evaluation and F6 inputs retain their pre-run hashes.

## Duplicate descriptions and catalogue-wide ambiguity

Symptom: 4,171 group-code pairs have 273 distinct verbatim descriptions.
Cause: 6,232 group-code pairs have 382 distinct verbatim descriptions.

The narrow/wide comparison below uses the SAME 9,263 eligible B1 units,
MiniLM and frozen threshold 0.50. These are candidate-coverage figures, not
independent evaluation metrics or correct SAP assignments.

| Target | Space | Assigned | Ambiguous maximum ties | Catalogue-only, without domain anchor |
| --- | --- | ---: | ---: | ---: |
| Symptom | PMMUWW reference | 218 | 0 | 204 |
| Symptom | Catalogue-wide | 3,753 | 2,261 | 3,653 |
| Cause | PMMUWW reference | 213 | 0 | 199 |
| Cause | Catalogue-wide | 4,284 | 2,855 | 4,166 |

Catalogue-wide matches often lack support from the narrower domain detector.
This can reflect domain-test undercoverage, semantic over-generation or both.
The run cannot separate those explanations; it does not prove broad coverage
of genuine symptoms or explicit causal assertions.

Within PMMUWW candidates, OHE accounts for 172/218 Symptom assignments (78.90%)
and OVHE for 113/213 Cause assignments (53.05%). Both exceed the 30% warning.
These similarities do not prove overheating is actually asserted in every row.

## Structural profile applicability

The 9,151 original direct PMMUWW orders leave 7,900 eligible orders after
evaluation/held-out exclusions. Only that eligible structural subset supports
calling PMMUWW an actual turbine-level profile rather than a common reference.

| Target | n eligible structural PMMUWW | Narrow candidates | Wide candidates |
| --- | ---: | ---: | ---: |
| Symptom | 7,900 | 189 | 3,244 |
| Cause | 7,900 | 187 | 3,590 |

The 3,934 text-derived component profiles span 30 profiles, overlap the turbine
population and are not all PMMUWW. They cannot be added as a new denominator or
used to claim a uniform 6/13-code answer space. No code correctness was evaluated
against a profile derived from Object Part text.

## Residual interpretation

In the 9,263-unit B1 common reference comparison, domain-anchored but uncoded
units are Symptom 92 narrow / 6 wide and Cause 121 narrow / 17 wide.
This partition is a detector-conditioned candidate gap, not a confirmed client
configuration defect.

Automatically grouped residual terms include work actions, administrative
context and abbreviations, not solely the target's subject matter. For example,
clusters labelled reset or cleaning in Cause context do not establish missing
Cause catalogue concepts. The concept tables describe the whole residual text;
their target label is contextual, not an independently validated assignment.
They require semantic review before a client-facing code-gap recommendation.
Overlapping concept unit counts must not be summed.

## Inherited embedding text-length limit

The unchanged local MiniLM configuration caps each embedded segment at 128
wordpiece tokens. Of 6,500 unique normalized eligible segments, 286 exceed this
limit. At least one capped segment occurs in 702 B1 units; none in the eligible
Path A or B2 units. Original full segment text was retained privately, and
residual term extraction used the full sanitized text. No chunking or longer
input variant was introduced after seeing results.

This is an inherited limitation of the scoring instrument, not source-text loss.
It is not legitimate to interpret a miss in a long field as absent signal.

## Status

Report complete for both targets, both spaces and all three separate paths.
B2 remains provisional under the explicitly inherited source-identity defect.
No training, promotion, F6 update, annotation or final-heldout claim.
This audit is an additional file; it does not replace or modify the frozen
instrument, scored evidence, original reports or their hash manifest.
