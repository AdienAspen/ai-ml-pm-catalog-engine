# G2.0 Object Part B1 Clean Annotation Package Regeneration

Both prior annotator batches are rejected because the source package format was not robust for chat transfer and exposed pipeline metadata. This regeneration does not patch responses; it creates clean JSONL packages from scratch.

## Leakage Scan

The full B1/Path A/B2 corpus was scanned before package regeneration. Leakage is present only in B1. See `g20_object_part_input_leakage_scan_sanitized.csv` and `g20_object_part_input_leakage_evidence_membership_sanitized.csv`.

Decision: **mask in input, not exclude**. The leakage is localizable and low-volume, so package text replaces catalogue-assignment patterns with `[MASKED_OBJECT_PART_ASSIGNMENT]`. Current G2.0 evidence membership is documented separately because those rows were present in the evidence frame.

## Package Format

Packages are JSONL, one record per line, with exactly two visible fields: `annotation_id` and `text`. No path, stratum, score, best class, prototype id, target hint, anchor source, or tier appears in visible packages.

## Counts

Union rows: `300`. Annotator 01 rows: `188`. Annotator 02 rows: `187`. Overlap rows: `75`.

## Scope

Scope lives in the manifest, not visible package: `evaluation_independence=independent`, `evaluation_role=diagnostic_calibration`, `sampling_design=score_band_stratified`, `eligible_for_final_heldout=false`, `protocol_version=g01-v1`.

## Verification

Each package was written and read back with a JSON parser; row counts and unique `annotation_id` were asserted. Checksums are in `g20_object_part_b1_clean_annotation_package_checksums_sanitized.csv`.
