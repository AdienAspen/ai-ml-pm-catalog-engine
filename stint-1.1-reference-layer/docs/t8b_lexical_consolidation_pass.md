# T8b - Lexical Consolidation Pass

## Purpose

This pass reconciles Chapter #1 and Chapter #2 feedback on T8 before freezing the reference layer.

It measures whether the T8 artefact is a convergent lexical dictionary or a broad vocabulary dump, then applies conservative abbreviation/suffix consolidation without exposing source-derived terms.

## Measured Collapse

- Initial rows: 14235
- Distinct observed term keys: 10639
- Distinct normalised term keys: 10639
- Observed keys equal normalised keys: True
- Consolidated distinct term keys: 10303
- Consolidated contextual rows: 14000
- Row reduction: 1.65%
- Distinct-term reduction: 3.16%

## Interpretation

The warning is confirmed: the original T8 output behaves more like a broad vocabulary dump than a compact seed dictionary. The equality between observed and normalised term keys shows that little lexical convergence occurred in T8 itself.

T8b improves the artefact through conservative consolidation, but the result remains provisional. It should not be frozen in T9 as final lexical truth without manual/domain review and downstream evidence triangulation.

## Governance

- `source_text_field` remains mandatory.
- `stratum` remains mandatory and `event_structural` must not be mixed with planned/reactive strata.
- Target assignment remains `expert_inference` unless independently validated later.
- `Symptom` entries are candidate symptom-like lexical signal, not Catalog S proof-of-life.
- The 300-800 concept range is a sanity heuristic, not a hard requirement.
- No raw source-derived terms are emitted in the versioned consolidated artefact.

## Outputs

- `reference_layer/lexical_layer/lexical_seed_dictionary_v1_consolidated_sanitized.csv`
- `outputs/t8b_lexical_consolidation_summary_v1.json`
