# Canonical Delta Log - STINT 1

## Purpose

This log continues the STINT_1.1 canonical delta log for evidence-reconstruction work.

The frozen reference layer remains the input baseline. STINT_1 may propose deltas, but it must not silently modify the canonical contract or the reference layer.

## Open Deltas Carried Forward

| delta_id | topic | status | STINT_1 handling |
|---|---|---|---|
| `DELTA-0002` | Record identifier | open | Define defensible record identity/proxy before denominator claims. |
| `DELTA-0003` | Primary text field by target | open | Require `source_text_field` on every evidence row and decide target-level runtime text source. |
| `DELTA-0009` | Shared Cause / Activity / Activity Type evidence | open | Run semantic split before target promotion or denominator use. |

## Rule

Every new delta must record what changed, what evidence justified it, who decided it, and when.

