# T3.5.2 Template-Aware PDF Reparse

## Scope

This pass reparses the Path A PDF corpus by heading anchors rather than fixed coordinates. It preserves section-level text internally and emits sanitized coverage outputs for review.

- Extraction engine: `pdfplumber_heading_anchored`
- Files reparsed: `394`
- Validation sample size: `10`
- Sample validation pass: `10`
- Sample validation review: `0`
- Files with all four core headings found: `334`
- Files with all four core section texts non-empty: `13`
- Raw operational values emitted in versioned outputs: `False`

## Coverage By Template Variant

| template_variant | files | recognised_core_files | core_4_heading_files | core_4_text_nonempty_files | asset_status_text | notes_text | assets_of_concern_text | planned_work_text | site_roster_text |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| PDF-TPL-006 | 198 | 198 | 198 | 11 | 198 | 11 | 198 | 197 | 198 |
| PDF-TPL-005 | 136 | 136 | 136 | 2 | 136 | 2 | 136 | 136 | 0 |
| PDF-TPL-007 | 26 | 0 | 0 | 0 | 26 | 0 | 0 | 26 | 0 |
| PDF-TPL-003 | 24 | 0 | 0 | 0 | 24 | 4 | 24 | 0 | 0 |
| PDF-TPL-002 | 7 | 0 | 0 | 0 | 7 | 2 | 0 | 0 | 0 |
| PDF-TPL-001 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 1 | 1 |
| PDF-TPL-004 | 1 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 |
| PDF-TPL-008 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Interpretation

The reparse confirms that section coverage must be evaluated by `template_variant`, not globally. Heading presence and non-empty section text are reported separately because an empty `NOTES` section is not a template failure.

The internal section-preserving output is deliberately kept under `reports/internal/`; versioned outputs contain only hashes, section-presence flags, counts, and content hashes.

## Next Control

Use this reparse as input for `T3.5.3` notes semantics and for later snapshot deduplication. Do not promote Path A evidence to denominators from this pass alone.
