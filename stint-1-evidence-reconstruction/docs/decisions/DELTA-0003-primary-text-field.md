# DELTA-0003 - Primary Text Field

## Status

`open`

## Issue

The canonical contract contains multiple text-bearing fields, but does not bind one primary runtime text field per target.

## STINT 1 Requirement

Every evidence row must carry `source_text_field`.

Before target-level measurement, STINT_1 must decide which text field or field family is valid for each target.

## Constraint

Do not merge evidence extracted from different text fields unless the merge rule is documented and provenance is preserved.

