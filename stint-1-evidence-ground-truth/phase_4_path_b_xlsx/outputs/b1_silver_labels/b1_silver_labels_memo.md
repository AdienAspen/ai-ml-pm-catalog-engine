# B1.2 Textual Residue Silver Labels

## Scope

This pass applies `LEXICAL_LAYER v2` high-confidence anchors to `CONTRACTOR_PATH_001` textual residue. It does not use `activityType`, does not map materials, and does not support contractual denominators.

## Summary

- Records evaluated: `10749`
- Lexical high-confidence terms loaded: `495`
- `descriptionExtended` non-empty rows: `10341`
- `reason` non-empty rows: `10338`
- Textual evidence rows: `30240`
- Physical records with any textual candidate: `6859`
- Record-target units with any textual candidate: `10596`
- Physical records with multi-field convergence: `3501`
- Record-target units with multi-field convergence: `3728`
- Proxy denominator candidate unit: `physical_record_id x target`
- Proxy denominator candidate units after review: `3728`
- Proxy candidate evidence rows, not denominator: `13238`
- Contractual denominator supported: `False`

## By Target And Field

| target | source_text_field | status | evidence_rows | physical_records | canonical_concepts |
| --- | --- | --- | ---: | ---: | ---: |
| Activity | descriptionExtended | textual_residue_candidate_requires_review | 2840 | 1709 | 11 |
| Activity | descriptionExtended | textual_residue_converged_candidate_requires_review | 2384 | 1215 | 10 |
| Activity | reason | textual_residue_candidate_requires_review | 50 | 50 | 4 |
| Activity | reason | textual_residue_converged_candidate_requires_review | 1736 | 1215 | 10 |
| Cause | descriptionExtended | textual_residue_candidate_requires_review | 6660 | 2509 | 50 |
| Cause | descriptionExtended | textual_residue_converged_candidate_requires_review | 2656 | 1250 | 27 |
| Cause | reason | textual_residue_candidate_requires_review | 57 | 52 | 12 |
| Cause | reason | textual_residue_converged_candidate_requires_review | 2196 | 1250 | 27 |
| Damage | descriptionExtended | textual_residue_candidate_requires_review | 7343 | 3623 | 50 |
| Damage | descriptionExtended | textual_residue_converged_candidate_requires_review | 2166 | 1263 | 26 |
| Damage | reason | textual_residue_candidate_requires_review | 52 | 50 | 8 |
| Damage | reason | textual_residue_converged_candidate_requires_review | 2100 | 1263 | 26 |

## Interpretation

These rows are weak-supervision candidates generated from a rule-derived lexical layer. They can support B1 target review and later proxy workflows, but they cannot evaluate the same rules that generated them.

Denominator-style counts use `physical_record_id x target`; evidence rows remain separate so multi-field convergence does not inflate `N`.

`reason` remains textual support only. B1.3 explicitly rejected deterministic Cause promotion.

raw_operational_values_emitted: false
