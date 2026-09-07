# T5.1b2.4 - Other Path OEM Pattern Check

## Purpose

Check whether the OEM alarm-code-description structure observed in the relational `reason` field is exclusive to that path, or also appears in Path A and B2 sources.

## Verdict By Path

| Path bucket | Text rows evaluated | Rows with OEM pattern | Distinct codes | Verdict |
| --- | ---: | ---: | ---: | --- |
| `PATH_A_NOTES` | 362 | 15 (4.14%) | 10 | `pattern_present` |
| `PATH_A_CONCERN_TABLE` | 1581 | 0 (0.0%) | 0 | `pattern_not_observed` |
| `B2_WORKBOOKS` | 1963 | 3 (0.15%) | 3 | `pattern_present` |

## Interpretation

This is a pattern cross-check only. It does not map OEM codes to SAP, classify Symptom, or promote any evidence to a denominator.

Overall answer: `not_exclusive`.
