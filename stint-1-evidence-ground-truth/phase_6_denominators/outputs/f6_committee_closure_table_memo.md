# F6 Committee Closure Denominator Table

This memo accompanies the sanitized CSV table for the STINT_1 closing report.

## Files

- Consolidated table: `f6_committee_closure_denominator_table_sanitized.csv`
- Context summary: `f6_committee_closure_context_sanitized.json`

## Context Figures

- Path A PDFs: `394` files; `602` rows evaluated; `362` estimated events.
- B1 relational/API branch: `7 logical entities; 21 redundant structured files across json/xlsx/xml`; `10749` physical records used as the main denominator unit.
- B2 snapshot workbooks: `127` files; `1988` snapshot text rows; `1857` refined events.

## Canonical Deltas

- `DELTA-0002`: Record identifier - `resolved_for_poc_policy`. Use deterministic `stint1_record_id` proxy for PoC denominators; do not claim production runtime identity.
- `DELTA-0003`: Primary text field by target - `resolved_for_poc_policy`. Use target-specific `source_text_field` routing; every evidence row must carry this field.
- `DELTA-0009`: Shared Cause / Activity / Activity Type evidence - `open`. Run semantic split before target promotion or denominator use.

## Controls

- No global denominator is reported across paths.
- `count_unit` is explicit in every row.
- `B2_WORKBOOK_SNAPSHOTS:365` for Symptom remains diagnostic only and is not admitted to the proxy denominator.
- FLOC leaf is an explicit zero: routeability exists, admitted evidence does not.
- Raw operational values emitted: `false`.
