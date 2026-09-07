# T5.1b2.3 - OEM Alarm Dictionary

## Purpose

Extract observed OEM-style code-description pairs from `reason` without assuming prefix-only format or one-to-one code semantics.

## Pattern Coverage

This pass detects code-description evidence in four positions: prefix with separator, prefix with space, suffix with separator, and embedded/terminal code. It preserves raw descriptions only in ignored internal storage and emits hashes plus normalized shapes in versioned outputs.

## Results

- OEM occurrence rows: `4057`.
- Distinct OEM codes: `679`.
- Distinct code-normalized-description pairs: `1014`.
- Codes with multiple normalized descriptions: `151`.
- Codes with multiple raw descriptions: `161`.

## Guardrails

- This is an observed OEM dictionary, not a SAP mapping.
- A code may map to multiple observed descriptions; no one-to-one assumption is made.
- No target denominator is affected by this pass.
- OEM codes are parsed and persisted as strings. Leading zeros are preserved before hashing, grouping, joining, or counting. Numeric coercion is prohibited because it can create silent code collisions.
