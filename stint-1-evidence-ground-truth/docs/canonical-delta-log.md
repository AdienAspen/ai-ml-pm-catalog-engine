# Canonical Delta Log - STINT 1

## Purpose

This log continues the STINT_1.1 canonical delta log for evidence-reconstruction work.

The frozen reference layer remains the input baseline. STINT_1 may propose deltas, but it must not silently modify the canonical contract or the reference layer.

## Open Deltas Carried Forward

| delta_id | topic | status | STINT_1 handling |
|---|---|---|---|
| `DELTA-0002` | Record identifier | resolved_for_poc_policy | Use deterministic `stint1_record_id` proxy for PoC denominators; do not claim production runtime identity. |
| `DELTA-0003` | Primary text field by target | resolved_for_poc_policy | Use target-specific `source_text_field` routing; every evidence row must carry this field. |
| `DELTA-0009` | Shared Cause / Activity / Activity Type evidence | open | Run semantic split before target promotion or denominator use. |

## Rule

Every new delta must record what changed, what evidence justified it, who decided it, and when.
