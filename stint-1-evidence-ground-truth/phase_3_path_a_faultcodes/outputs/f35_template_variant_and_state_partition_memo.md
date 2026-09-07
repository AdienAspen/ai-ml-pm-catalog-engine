# F3.5.0 / T3.5.1 Path A Template and Code-State Check

## Scope

This pass inventories PDF template variants before interpreting code/event rows, then performs a conservative provisional partition of non-empty code tokens into `state_code`, `fault_code`, or `undetermined`.

No raw operational values, file names, asset identifiers, site names, or event descriptions are emitted in versioned outputs.

## F3.5.0 Template Variant Inventory

- Files profiled: `394`
- Template variants detected: `8`
- Files with all core sections recognised: `334`
- Files eligible for zero interpretation under recognised-template rule: `334`

| template_variant | file_count | month_min | month_max | section_signature | core_recognised |
| --- | ---: | --- | --- | --- | --- |
| PDF-TPL-006 | 198 | 2025-01 | 2026-03 | ASSET STATUS; NOTES; ASSETS OF CONCERN; PLANNED WORK; SITE ROSTER; NO ATTACHMENTS | True |
| PDF-TPL-005 | 136 | 2025-09 | 2026-01 | ASSET STATUS; NOTES; ASSETS OF CONCERN; PLANNED WORK | True |
| PDF-TPL-007 | 26 | 2025-04 | 2025-09 | ASSET STATUS; NOTES; PLANNED WORK | False |
| PDF-TPL-003 | 24 | 2022-11 | 2023-02 | ASSET STATUS; NOTES; ASSETS OF CONCERN | False |
| PDF-TPL-002 | 7 | 2022-11 | 2022-12 | ASSET STATUS; NOTES | False |
| PDF-TPL-001 | 1 | 2025-08 | 2025-08 | ASSET STATUS; ASSETS OF CONCERN; PLANNED WORK; SITE ROSTER; NO ATTACHMENTS | False |
| PDF-TPL-004 | 1 | 2022-11 | 2022-11 | ASSET STATUS; NOTES; ASSETS OF CONCERN; NO ATTACHMENTS | False |
| PDF-TPL-008 | 1 | unknown | unknown | NOTES | False |

## T3.5.1 Code-State Hypothesis Check

- Non-empty code rows evaluated: `602`
- Distinct code keys evaluated: `79`
- Provisional `fault_code`: `34`
- Provisional `state_code`: `5`
- Provisional `undetermined`: `40`

## Interpretation

The partition is provisional because it is based on the existing table extraction and event-family distribution. It is suitable for triage, not for denominator promotion.

The template inventory is now a precondition for Path A repair: every downstream extracted row must carry `template_variant`, and no zero should be interpreted for a file whose template is not recognised.

## Next Control

Before rerunning Path A crosswalks, execute a template-aware reparse that preserves `ASSET STATUS`, `NOTES`, `ASSETS OF CONCERN`, and `PLANNED WORK`, with coverage reported by template variant.
