# T7 KKS / RDS-PP Presence Check

## Scope

This note records a repository-level presence check for inherited KKS/RDS-PP-style designations.

No raw operational values are emitted. Numeric project-specific portions of KKS-like strings are not parsed or interpreted.

## Patterns Checked

- RDS-PP mounted designation pattern beginning with `=M`.
- RDS-PP mounted designation pattern beginning with `=U`.
- Plan-specified RDS-PP letter codes: `MDA`, `MDK`, `MDL`, `MKA`, `MSE`, `MST`, `MUD`.
- Classic KKS-like alphanumeric candidates, counted only as presence evidence.

## Summary

- Files scanned: 764
- Source/extracted data files scanned: 541
- Source/extracted data files with KKS/RDS hits: 9
- Source/extracted data KKS/RDS hit count: 201
- Source/extracted data classic KKS candidate hit count: 201
- Source/extracted data RDS-PP hit count: 0
- Total repository-level pattern hit count: 2974
- Pattern rows emitted: 15
- Scan errors: 0
- RDS-PP normative letter codes with hits: 7 / 7

## Interpretation

This is a presence check, not a resolver. KKS/RDS-PP evidence may support FLOC interpretation, validation, or crosswalk construction, but it must not be treated as resolving or constructing the final hierarchy by itself.

The corrected regex pass finds KKS-like candidate hits in `source_or_extracted_data`, all under the broad `classic_kks_candidate` pattern. It does not find RDS-PP scoped hits in source/extracted data.

The large repository-level count is not a source-data denominator: it includes reference documents, planning material, generated artefacts, and external support code. Scope separation is therefore part of the control.

The result should feed STINT_1 as supporting source-designation evidence for FLOC and related semantic reconciliation work.

## Outputs

- `outputs/kks_presence_check_pattern_counts_v1.csv`
- `outputs/kks_presence_check_scope_summary_v1.csv`
- `outputs/kks_presence_check_errors_v1.csv`
- `reference_layer/source_designations/rds_pp_normative_pattern_presence_v1.csv`
- `outputs/kks_presence_check_summary_v1.json`

## Guardrails

- Do not parse the project-specific numeric portion of KKS-like strings.
- Do not promote KKS/RDS-PP presence to ground truth.
- Do not treat KKS/RDS-PP as a hierarchy resolver.
- Preserve namespace separation: IEC id != RDS-PP != ISO != FLOC != EQUNR != technician term.
