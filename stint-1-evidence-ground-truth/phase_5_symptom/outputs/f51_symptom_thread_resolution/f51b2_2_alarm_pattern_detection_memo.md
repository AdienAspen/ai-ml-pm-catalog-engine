# F5.1b2.2 - Automatic Alarm Pattern Detection

## Purpose

Count and profile four reason-text pattern families before any Symptom classification or target promotion.

## Scope

- Source universe: complete non-empty `reason` field for `CONTRACTOR_PATH_001`.
- Rows evaluated: `10338` non-empty reason rows from `10749` service-order records.
- This pass counts and profiles only. It does not classify Symptom, create denominator rows, or promote evidence.

## Pattern Tracks

| Track | Meaning | Flag rows | Exclusive rows |
| --- | --- | ---: | ---: |
| F5.1b2.2a | OEM alarm pattern coverage | 3519 | 3519 |
| F5.1b2.2b | CMS pattern coverage with severity extracted | 189 | 189 |
| F5.1b2.2c | Dispatch-motive exclusion by pattern | 855 | 811 |
| F5.1b2.2d | Residual without pattern; likely location for technician prose | 5819 | 5819 |

## Counting Note

Flag counts are independent pattern hits and may overlap. Exclusive bucket counts apply this precedence: OEM alarm, then CMS alert, then dispatch motive, then residual. This prevents double counting while preserving separate pattern coverage.

## Interpretation Guardrail

Dispatch-motive rows are actively separated so administrative, inspection, upgrade, testing, planned, or adjustment text does not remain hidden inside the residual pool. The residual is not Symptom evidence by itself; it is the candidate area where free technician prose may live and still requires downstream review.

## Privacy

No raw reason text, operational values, source paths, site names, contractor names, or customer identifiers are emitted in versioned artifacts.
