# SAP Mapping Catalog Ingest Note

## Purpose

T3 ingests the Wind catalog workbook as the authoritative universe of valid SAP target codes for the five catalog-backed targets.

## Evidence Classification

Rows from the workbook are classified as `reference_evidence` by default.

They are not classified as `validated_mapping`, because the workbook proves that a target code exists and belongs to a catalog/code group. It does not prove that any observed source text or source concept maps to that code at record level.

## Measurement Rule

Catalog rows do not enter measurement denominators.

Only `real_observed_label` or independently validated `source concept/text -> target code` mappings can support a denominator for accuracy, coverage, or confidence estimates.

## Consumer Constraint

The ingested catalog feeds the `SAP_MAPPING` object of the reference layer. Each row carries the canonical target field it can feed, so downstream concepts can be checked against the interface constraint without treating the canonical contract as semantic content.

## Downstream Use

Use this artifact to:

- verify that a candidate code is legal for a target catalog;
- reject impossible target-code candidates;
- connect lexical and semantic evidence to valid answer namespaces;
- identify missing or external vocabularies, such as OEM fault-code systems.

Do not use this artifact to:

- claim ground truth;
- estimate model accuracy;
- promote source text to a target label without validation.
