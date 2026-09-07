# T5.1b2.4b - Semantic Classification In Path A and B2

## Purpose

Apply the normalized semantic classifier from `T5.1b2X-normalized` to Path A and B2 text sources using the fixed threshold `0.50`. The threshold is not recalibrated on these sources.

## OEM Pattern vs Semantic Classifier

| Source | Rows | OEM pattern rows | Semantic observed_condition | Semantic coverage | Verdict |
| --- | ---: | ---: | ---: | ---: | --- |
| `PATH_A_NOTES` | 882 | 15 (4.14%) | 42 (4.76%) | 45.12% | `signal_present_beyond_oem_pattern` |
| `PATH_A_CONCERN_TABLE` | 1581 | 0 (0.0%) | 68 (4.3%) | 70.84% | `signal_present_beyond_oem_pattern` |
| `B2_WORKBOOKS` | 1963 | 3 (0.15%) | 62 (3.16%) | 13.65% | `signal_present_beyond_oem_pattern` |

## Guardrail

This pass is a semantic cross-check only. It does not map to SAP, does not promote Symptom evidence to a denominator, and keeps `evaluation_independence = derived_from_rules`.
