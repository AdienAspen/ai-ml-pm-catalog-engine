# T3.5.3 NOTES Semantic Extraction

## Scope

This pass extracts candidate semantics from the spatial `NOTES` region. It does not promote any candidate to a denominator and does not emit raw note text in versioned outputs.

## Control Rule

No zero is interpreted until the extractor is validated against a known positive case. This pass consumes the `T3.5.2b` positive-control diagnostic where the known samples were recovered.

## Summary

- Input files: `394`
- NOTES region non-empty files: `362`
- Note lines extracted: `1323`
- Note lines with semantic signal: `882`
- Note lines with candidate asset reference: `697`
- Note lines with candidate contractor key: `206`
- Note lines with candidate target family: `647`

## Coverage By Template Variant

| template_variant | files | notes_nonempty_files | note_lines | semantic_signal_lines | asset_ref_lines |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF-TPL-006 | 188 | 188 | 784 | 505 | 379 |
| PDF-TPL-005 | 131 | 131 | 324 | 264 | 225 |
| PDF-TPL-003 | 17 | 17 | 111 | 63 | 53 |
| PDF-TPL-007 | 25 | 25 | 95 | 45 | 36 |
| PDF-TPL-002 | 1 | 1 | 9 | 5 | 4 |

## Candidate Target Families

| candidate_target | note_line_count |
| --- | ---: |
| activity | 458 |
| object_part | 293 |
| damage | 102 |

## Interpretation

`NOTES` contains real Path A prose and should be used for candidate Object Part / Activity / Damage support. All extracted links remain `expert_inference`, `silver-medium`, `derived_from_rules`, and `candidate_requires_review`.

`Txx -> asset` links are candidate joins only. They carry `join_confidence` and must be validated against `site_key` before being treated as resolved.

## Next Control

Proceed to `T3.5.4` snapshot deduplication using `site_key + asset/code + incident_start_estimated window`, not raw row counts.
