# T3.5.2b NOTES Region Diagnostic

## Scope

This diagnostic tests whether `NOTES` behaves as a right-side column rather than a stacked section. It uses spatial extraction from the `NOTES` heading to the next block heading.

- Engine: `pdfplumber_spatial_notes_region`
- Files evaluated: `394`
- Core-recognized files: `334`
- Stacked extractor NOTES non-empty over core files: `13`
- Spatial NOTES region non-empty over core files: `319`
- Spatial NOTES region non-empty rate over core files: `0.9551`
- Known sample files checked: `2`
- Known sample files with non-empty NOTES region: `2`
- Known sample markers all found: `True`

## Coverage By Template Variant

| template_variant | files | core_files | stacked_notes_nonempty | region_notes_nonempty | region_notes_nonempty_core |
| --- | ---: | ---: | ---: | ---: | ---: |
| PDF-TPL-006 | 198 | 198 | 11 | 188 | 188 |
| PDF-TPL-005 | 136 | 136 | 2 | 131 | 131 |
| PDF-TPL-007 | 26 | 0 | 0 | 25 | 0 |
| PDF-TPL-003 | 24 | 0 | 4 | 17 | 0 |
| PDF-TPL-002 | 7 | 0 | 2 | 1 | 0 |
| PDF-TPL-001 | 1 | 0 | 0 | 0 | 0 |
| PDF-TPL-004 | 1 | 0 | 0 | 0 | 0 |
| PDF-TPL-008 | 1 | 0 | 0 | 0 | 0 |

## Interpretation

The stacked heading extractor undercounts `NOTES` because the PDF layout places NOTES as a parallel right-side column. `NOTES` coverage must therefore be derived from the spatial region extractor, not from sequential section text.

This diagnostic supersedes the earlier `NOTES non-empty = 13` interpretation for T3.5.3 planning. It does not promote any row to a denominator; it only fixes section availability accounting.
