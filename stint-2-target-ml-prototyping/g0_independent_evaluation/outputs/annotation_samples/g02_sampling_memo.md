# G0.2 Stratified Annotation Sample

## Purpose

Build the blind annotation sample and closed-environment visible packages from admitted STINT 1 units.

## Sampling Rules Applied

- Sample by `sampling_unit_key`.
- Cap per `source_unit_key`: `5%` of each target sample.
- Stratify by path, stratum, and anchor source where row-level metadata is available.
- Use admitted units only; G1 candidate pools remain excluded.
- Two annotators with `25%` target-level overlap.

## Outputs

- Versioned sanitized manifest: `g02_annotation_sample_manifest_sanitized.csv`.
- Versioned availability audit: `g02_sampling_frame_availability_sanitized.csv`.
- Versioned text-recovery blockers: `g02_text_recovery_blockers_sanitized.csv`.
- Closed visible packages: `g0_independent_evaluation/internal/g02_annotation_packages/` with permissions 600.

## Text Recovery Limitation

Rows without recoverable visible text are excluded from the visible annotation packages. This affects B2 workbook snapshot paths and must be resolved before those units can be annotated.

No visible text is written to versioned outputs.
