# STINT 1 - Evidence Reconstruction

## Purpose

This directory contains the STINT 1 evidence-reconstruction workspace for the PoC.

STINT 1 consumes the frozen `reference-layer-v1` and builds auditable surrogate evidence by target. It does not claim production ground truth, client validation, production accuracy, or final model readiness.

## Reference Layer Dependency

The frozen reference layer is consumed by relative path:

```python
REFERENCE_LAYER = "../stint-1.1-reference-layer/reference_layer"
```

Do not copy `reference-layer-v1` into this directory. If the reference layer ever changes, it must change in its own location and be versioned separately.

## Operating Chain

```text
observed signal
  -> runtime usable source
  -> evidence with provenance
  -> valid label or defensible proxy mapping
  -> target-level denominator
  -> feasible method candidate
```

## Phases

| phase | purpose |
|---|---|
| `phase_0_consolidation` | Import STINT_0 and STINT_1.1 decisions into the STINT_1 working frame. |
| `phase_1_lexical` | Rework the provisional lexical layer through filtering and domain grouping. |
| `phase_2_reconciliation` | Reconcile unknown and shared multi-target evidence before promotion. |
| `phase_3_path_a_faultcodes` | Build the fault-code evidence path with provenance and confidence. |
| `phase_4_path_b_xlsx` | Build the tabular/source-data evidence path by target, including FLOC and MAT. |
| `phase_5_symptom` | Treat Symptom after stronger Object Part, Damage, Activity, and Cause evidence exists. |
| `phase_6_denominators` | Produce target-level evaluable denominators and readiness tables. |

## Governance

- No global denominator.
- No raw operational values in versioned evidence.
- `expert_inference` is evidence provenance, not measurement truth.
- `reference_evidence` supports reasoning but does not create labels by itself.
- `validated_mapping` is reserved for demonstrated `source concept/text -> target code` relationships.
- Each target is assessed independently.

