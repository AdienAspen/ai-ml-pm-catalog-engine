# B2.1 Snapshot Workbook Characterization

## Scope

This pass characterizes snapshot-style workbooks before extraction. It inventories workbook families, detects template variants through sheet/header signatures, and identifies candidate prose-bearing areas without emitting operational values.

## Summary

- Files discovered: `127`
- Files read OK: `127`
- Files failed: `0`
- Template variants: `10`
- Sheets profiled: `251`
- Sheets with candidate text: `144`
- Rows with candidate text: `1942`
- Known-positive validation: `pending_not_provided_for_b2_xlsx`

## Top Template Variants

| template_variant | file_count | families | doc_types | month_buckets | candidate_text_rows |
| --- | ---: | --- | --- | --- | ---: |
| B2TPL-d4d0ad5054f0 | 56 | SNAPSHOT_FAMILY_001 | EOD | 2026-05,2026-06,2026-07,unknown_month | 958 |
| B2TPL-845a1a48e58e | 26 | SNAPSHOT_FAMILY_003 | POD,snapshot_unprefixed | 2024-12,2025-01,2025-02,2025-03,2025-04,2025-05,2026-07,2026-08 | 306 |
| B2TPL-3a9f88b91b3b | 20 | SNAPSHOT_FAMILY_001 | EOD | 2026-03,2026-04,2026-05 | 266 |
| B2TPL-73c07cc3144b | 8 | SNAPSHOT_FAMILY_003 | POD | 2025-06 | 91 |
| B2TPL-09352e59ea57 | 6 | SNAPSHOT_FAMILY_002 | POD | 2026-08 | 137 |
| B2TPL-1d8b6aa3f107 | 5 | SNAPSHOT_FAMILY_001 | EOD | 2026-07 | 91 |
| B2TPL-928f4491e44f | 2 | SNAPSHOT_FAMILY_001 | EOD | 2026-06 | 29 |
| B2TPL-c0b34b358d76 | 2 | SNAPSHOT_FAMILY_003 | POD | 2025-05 | 28 |

## Interpretation

B2.1 is characterization only. No row is promoted to a target, no denominator is created, and no absence is interpreted until a known-positive workbook case is validated.

B2 sources remain `event_structural`; they must not be mixed with planned/reactive strata from the relational branch.

raw_operational_values_emitted: false
