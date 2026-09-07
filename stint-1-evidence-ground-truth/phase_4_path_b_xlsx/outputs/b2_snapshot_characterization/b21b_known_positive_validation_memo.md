# B2.1b XLSX Known-Positive Validation

## Scope

This pass validates that candidate text structures detected in B2.1 can be recovered from workbook cells for selected positive cases. It emits marker hashes only, never raw operational text.

## Summary

- Validated files: `4`
- Validated markers: `12`
- Markers recovered: `12`
- Doc type buckets validated: `EOD, POD, other, snapshot_unprefixed`
- Known-positive validation: `passed_direct_cell_markers`

## Interpretation

The B2.1 text structures are no longer only parser-observed. At least one positive workbook in each validated bucket contains recoverable text markers through the header-aware extractor.

This does not yet promote target evidence. It only clears the false-negative guardrail before B2.2/B2.3.

raw_operational_values_emitted: false
