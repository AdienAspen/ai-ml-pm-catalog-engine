# F0 - Consolidation and Preconditions

## Purpose

Phase 0 consolidates STINT_0 accounting and STINT_1.1 reference-layer decisions before evidence reconstruction begins.

This pass does not train models, estimate accuracy, create production ground truth, or modify the frozen reference layer.

## Reconciled Accounting

- Source opportunity rows: 838
- Target-expanded classification rows: 910
- Multi-target hint rows: 36
- Expansion delta: 72
- Structural files attempted: 157
- Source-data pair-discovery files: 147
- Current tabular parser issues: 0

## Decisions

- `G04` is closed for PoC by documented proxy assumption, not by production runtime proof.
- `G08` is closed under current evidence: tabular parser issues are zero.
- Cause / Activity / Activity Type shared expansion remains open for Phase 2 semantic split.
- `DELTA-0002` is resolved for PoC by `stint1_record_id` deterministic proxy policy.
- `DELTA-0003` is resolved for PoC by target-specific `source_text_field` routing.

## Phase Gate

F0 clears the preconditions for Phase 1 lexical rework. It does not create measurement-ready targets.

Measurement-ready targets remain: 0

## Governance

- No raw operational values are emitted.
- No global denominator is introduced.
- `expert_inference` remains outside measurement denominators unless later converted through a documented validation/proxy rule.
