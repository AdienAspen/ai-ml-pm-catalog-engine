# F5.1c — Symptom Lexicon Survival Check

## Objective

Verify whether the 289 historical Symptom lexical terms from `reference-layer-v1` survived into the F1 high-confidence lexical band or fell into the F1 unresolved/discarded population.

## Inputs

- Historical Symptom lexical rows: `289`
- Consolidated Symptom rows consumed by F1: `286`
- Distinct consolidated term keys: `222`
- Source: `lexical_seed_dictionary_v1_consolidated_sanitized.csv`
- Comparator: `lexical_layer_v2_high_confidence_candidates_sanitized.csv`
- Raw terms emitted: `false`

## Result

- Survived high band, any target: `57` consolidated rows / `41` distinct keys
- Survived high band as Symptom: `57` consolidated rows / `41` distinct keys
- Survived high band but retargeted: `0` consolidated rows / `0` distinct keys
- Retained in F1 v2 but not high band: `0` consolidated rows / `0` distinct keys
- Fell to unresolved/rework: `229` consolidated rows / `181` distinct keys
- Discarded before or during F1 v2 routing: `0` consolidated rows / `0` distinct keys

## Source-Row Accounting

- Historical source rows represented by high-band survivors: `59`
- Historical source rows represented by unresolved/rework: `230`

## Interpretation

The historical Symptom lexical pool does not provide an independent Symptom-ready layer unless terms survive as high-confidence Symptom anchors. Terms that survive only after retargeting may still support other targets, but they do not close the Symptom evidence thread.

This check is diagnostic only. It does not promote any row into a contractual or proxy denominator.

## Governance

- Evidence type: `expert_inference`
- Tier: `silver-medium` maximum
- Evaluation independence: `derived_from_rules`
- Raw operational values emitted: `false`
