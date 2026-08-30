# T7c - Classic KKS Candidate Review

## Purpose

This follow-up reviews the broad `classic_kks_candidate` hits found in source/extracted data after the T7 regex correction.

The task classifies the files and token shapes without emitting raw values or interpreting numeric/project-specific code segments.

## Result

- Source/extracted files with classic KKS-like candidates: 9
- Classic KKS-like candidate hits: 201
- Hits by contractor/path: `{'CONTRACTOR_PATH_001': 201}`
- Hits by extension: `{'.json': 67, '.xlsx': 67, '.xml': 67}`
- Dominant context buckets: `{'unspecified_context': 78, 'fault_alarm_context': 3, 'asset_material_serial_context': 42, 'order_work_context': 78}`
- The hit distribution is format-repeated: the same contractor/path contributes equal counts across JSON, XLSX, and XML, suggesting serialized representations of the same source family rather than nine independent KKS-bearing sources.

## Interpretation

`classic_kks_candidate` is intentionally broad. These hits are not promoted to KKS evidence by pattern alone.

The sanitized context review determines whether the candidates occur near FLOC/KKS language, asset/material/serial language, order/work language, or unspecified context. This separates possible FLOC support from likely false positives such as material numbers, serials, or order-like identifiers.

Current assessment: `likely_false_positive_or_non_floc_code_until_validated`.

## Impact on G06

G06 remains routed through T8 lexical matching against the IH06-derived node inventory. These classic KKS-like candidates may become support features only if T8 or later crosswalk work confirms semantic alignment with observed IH06 nodes.

## Outputs

- `outputs/t7c_classic_kks_candidate_files_v1.csv`
- `outputs/t7c_classic_kks_candidate_sample_v1.csv`
- `outputs/t7c_classic_kks_candidate_shapes_v1.csv`
- `outputs/t7c_classic_kks_candidate_contexts_v1.csv`
- `outputs/t7c_classic_kks_candidate_summary_v1.json`
