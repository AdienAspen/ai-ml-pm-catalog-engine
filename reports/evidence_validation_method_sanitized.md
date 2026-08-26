# Asset ML Feasibility - Evidence and Validation Method

## Scope

This section documents the method used to move from data prospection to defensible target-level feasibility evidence.
It does not include model training, accuracy estimates, or final feasibility conclusions.

This POC pipeline is the reproducible source of record for the current feasibility assessment.
Current report claims should cite sanitized local artifacts and explicitly separate observed, validated, proxy, synthetic, and inferred evidence.

## Validation Chain

`signal exists -> runtime usable -> valid label/mapping -> measurable target -> feasible method`

| step | question | evidence_needed |
| --- | --- | --- |
| signal_exists | Is there source evidence that plausibly carries target information? | Safe schema/profile evidence, controlled-vocabulary overlap, row-level co-occurrence, or parser-derived structured evidence. |
| runtime_usable | Will the signal be available when the production engine runs? | Runtime app/source confirmation, canonical field matrix alignment, or source owner confirmation. |
| valid_label_or_mapping | Can we prove what the correct target code was for a record? | Real observed label or validated mapping. Reference catalogs and agent inference are not enough. |
| measurable_target | Is there a defensible denominator for coverage/confidence measurement? | Record-level label/mapping evidence tied to runtime-available input fields. |
| feasible_method | Which method is justified by the evidence? | Rules, classifier, NER, hybrid method, or unresolved status based on validated evidence. |

## Evidence Taxonomy

| evidence_type | definition | can_support_measurement | measurement_use |
| --- | --- | --- | --- |
| real_observed_label | Record-level evidence where the correct target code is observed as data. | True | Can enter the measurement denominator after runtime availability is confirmed. |
| validated_mapping | A mapping confirmed by an SME, mapping owner, or governed project documentation. | True | Can enter the measurement denominator if it applies at record level. |
| illustrative_example | An example showing intended behavior, not proof of a record-level label. | False | Useful for interpretation only unless later validated. |
| reference_catalog | Catalog, code list, glossary, or controlled vocabulary. | False | Useful for matching and normalization, not a ground-truth denominator. |
| agent_inference | A pipeline-generated hypothesis inferred from metadata or structure. | False | Must never be used as a label. |
| unknown | Unresolved text-code opportunity that has not been classified. | False | Preserve for semantic reconciliation; do not promote to a target yet. |

## Method Phases

| phase | purpose | status | current_role |
| --- | --- | --- | --- |
| Initial evidence baseline | Initial inventory, schema profiling, vocabulary exploration, and methodology review. | baseline_context | Findings are retained as methodological context; current claims should cite reproducible sanitized artifacts. |
| Reproducible POC pipeline | Implements the evidence chain as modular Python scripts with sanitized outputs and repeatable run summaries. | active_source_of_record | Feeds all current report sections and can be re-run as source data, parsers, vocabularies, or validation decisions change. |
| Controlled vocabulary prospection | Use target-specific controlled terms to reduce broad keyword noise. | active_supporting_method | Supports signal discovery, not final model thresholding or endpoint thresholding. |
| Safe content and row-level pair discovery | Identify text-code co-occurrence opportunities without emitting raw operational values in committee-facing outputs. | active_supporting_method | Produces candidate opportunities that require evidence classification and runtime validation. |
| Target-level evidence matrix | Organize evidence by target across signal, runtime, label/mapping, measurability, and method direction. | draft_dependency | Useful as a bridge to target-level feasibility, but must be regenerated after sections 5 and 7 are consolidated. |

## Current Supporting Artifacts

| artifact | method_use | current_count |
| --- | --- | --- |
| source_file_inventory_sanitized.csv | Defines source universe, roles, categories, and versionable sanitized scope. | 575 |
| basic_structural_scan_summary_sanitized.json | Confirms structured/tabular read coverage for supported sources. | 157 |
| schema_profile_summary_sanitized.json | Profiles fields, candidate text/code signals, and safe column-level metadata. | not_available |
| catalog_vocabulary_summary_sanitized.json | Loads controlled vocabulary for SAP catalog targets S/B/C/5/A. | not_available |
| pair_evidence_classification_summary_sanitized.json | Classifies candidate text-code opportunities by evidence type. | 910 |
| pdf_assets_of_concern_summary_sanitized.json | Documents verified PDF table extraction and file-read denominator. | 394 |
| report_readiness_check_summary_sanitized.json | Maps current artifacts to the requested report table of contents. | 15 |
| target_level_evidence_matrix_summary_sanitized.json | Draft dependency for target-level assessment; must be regenerated after sections 5 and 7 settle. | 7 |

## Runtime Availability Rule

A source signal is not treated as production-usable until the runtime owner or canonical field evidence confirms that the field is available to the engine when classification is requested.
Analysis-only files, mapping examples, reference catalogs, and post-hoc exports can guide prospection but do not prove runtime availability.

## Measurement Denominator Rule

A target is measurable only when record-level inputs can be tied to a real observed label or validated mapping.
Reference catalogs, metadata-inferred links, illustrative examples, and unresolved unknown opportunities are excluded from the measurement denominator.

## Zero Interpretation Rule

A zero is informative only when the relevant source class was successfully read and the zero type is explicit.
If a file was not read, not attempted, or parsed by the wrong extractor, the result is not interpretable as absence of evidence.

## Guardrails

- No raw operational client values are emitted in versioned outputs.
- Reference catalogs are not ground truth.
- Illustrative examples do not create a measurement denominator unless validated.
- Agent inference must never be used as a label.
- A zero is reportable only when the relevant source was successfully read and the denominator is explicit.
- Unknown text-code opportunities are preserved for reconciliation but are not promoted to a target without validation.
- The dual overlap settings are prospection settings only: 0.10 for discovery and 0.20 for high-specificity sanity checks.
- KKS can support and validate FLOC interpretation; it must not be treated as resolving or constructing the hierarchy.

## Current Status

This section is ready as a method section for a draft assessment.
Sections on measurement readiness, cross-target gaps, and target-level feasibility must still consume the latest evidence before final report language is frozen.

## Run Metadata

- Created at UTC: `2026-08-24T19:17:48.026918+00:00`
- Raw operational values emitted: `false`
