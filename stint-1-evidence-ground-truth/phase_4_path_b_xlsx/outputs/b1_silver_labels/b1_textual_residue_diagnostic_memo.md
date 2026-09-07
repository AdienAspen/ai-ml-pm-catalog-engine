# B1.2b Textual Residue Diagnostic

## Questions

- Is 50 a technical cap? No cap was found in B1.2; the script uses distinct concept counts after matching.
- Does Damage show possible over-generation? The sanitized anchor sample and source-family split are emitted for review before closing B1.

## Cap Check

Cause / descriptionExtended and Damage / descriptionExtended both reaching 50 in the B1.2 memo is not produced by a visible 	op-N cap in B1.2. The upstream lexical source has different counts for those target-field pairs, so the equality should be treated as an observed crossing result, not as a configured limit.

## Damage Review Guardrail

Damage remains a weak-supervision candidate only. High incidence from free text does not support a contractual denominator, and B1.2 should feed review rather than measurement until anchors are accepted.

## Sanitized Outputs

- 1_damage_anchor_sample_sanitized.csv
- 1_damage_anchor_source_family_sanitized.csv
- 1_textual_residue_diagnostic_summary_sanitized.json

raw_operational_values_emitted: false
