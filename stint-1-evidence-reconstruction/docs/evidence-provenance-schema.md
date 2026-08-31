# Evidence Provenance Schema

## Purpose

This schema extends the STINT_1.1 provenance model with record-level fields needed for evidence reconstruction.

## Required Fields

| field | meaning |
|---|---|
| `record_id` | Stable record identifier or documented proxy. |
| `target` | One of the seven project targets. |
| `evidence_type` | Provenance/type of evidence. |
| `tier` | Confidence tier. |
| `status` | Promotion state. |
| `source_path` | Sanitized source path or source family key. |
| `source_text_field` | Text/runtime field from which evidence was extracted. |
| `stratum` | Maintenance-type or event-structural stratum. |
| `site_key` | Sanitized site key. |
| `contractor_path` | Sanitized contractor/path key. |
| `concept_id` | Stable reference-layer or STINT_1 concept id. |
| `confidence` | Numeric or categorical confidence, if defensible. |
| `notes` | Sanitized methodological note, never raw operational text. |

## Evidence Types

- `real_observed_label`
- `validated_mapping`
- `reference_evidence`
- `external_corroboration`
- `expert_inference`
- `synthetic`
- `proxy_label`
- `unresolved`

## Tiers

- `gold`
- `silver-high`
- `silver-medium`
- `unresolved`

## Non-Negotiable Rule

`evidence_type` and `tier` are independent axes. Do not encode source provenance inside confidence tier.

