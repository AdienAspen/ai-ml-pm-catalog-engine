# F3 OEM Fault Code Crosswalk Report

## Scope

This pass processes the corrected PDF `Assets of Concern` extraction for Path A. It uses
fault-code context to create candidate maintenance concepts against the available reference
layer. It does not claim an OEM-to-SAP 1:1 mapping.

## Input Coverage

| metric | value |
| --- | ---: |
| fault-code rows | 602 |
| distinct fault-code keys | 79 |
| crosswalk candidate rows | 316 |

## Candidate Status

| status | rows |
| --- | ---: |
| candidate_high_requires_review | 12 |
| candidate_medium_requires_review | 31 |
| unresolved_below_threshold | 273 |

## Interpretation

- Fault codes are treated as OEM/contextual evidence, not SAP codes.
- A fault code may map to multiple candidate targets, one candidate target, or none.
- Candidate rows are `expert_inference`, `silver-medium`, and `derived_from_rules`.
- No candidate can support the contractual denominator without later validation.
- No candidate is included in the POC proxy denominator yet; F3 emits a review queue.

## Controls

- Versioned outputs use fault-code keys, concept IDs, counts, scores, and provenance only.
- Raw fault codes, event text, asset identifiers, and file paths are not emitted in versioned outputs.
- An internal redacted review file exists under `reports/internal/` for human review.
