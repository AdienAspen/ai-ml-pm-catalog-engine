# G0.0 STINT 1 Inventory for Annotation Protocol

## Purpose

This inventory supports the STINT 2 blind annotation protocol. It counts available units by target and path before sample sizes are declared.

## Findings

- Target-path rows inventoried: `23`.
- Row-level rows with unit identifiers: `18`.
- Aggregate-only rows from F6 summaries: `5`.
- Cause on `PATH_A_PDF_EVENTS` has a protocol ceiling of `36` units.
- Protocol v1 samples admitted units only.
- Rows with zero admitted units but positive candidates are G1 candidate pools, not protocol v1 evaluation material.
- Symptom has `1999` admitted units in aggregate-only F6 rows; row-level units must be recovered before Symptom can enter protocol v1.
- Cross-path exact overlap is generally not assessable where STINT 1 uses different record/event namespaces across paths.
- Cross-path deduplication is not required for protocol v1 because F6 forbids aggregation across paths.
- `anchor_source` can be derived for row-level artifacts; membership is non-exclusive and shares may sum above 100%.
- Aggregate-only Symptom paths require protocol-level handling before row-level sampling.

## Outputs

- `g00_target_path_inventory_sanitized.csv`
- `g00_anchor_source_distribution_sanitized.csv`
- `g00_cross_path_overlap_sanitized.csv`
- `g00_protocol_blockers_sanitized.csv`
- `g00_inventory_summary_sanitized.json`

No raw operational values are emitted.
