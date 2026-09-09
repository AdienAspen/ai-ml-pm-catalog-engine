# STINT 2 - Target ML Prototyping

## Purpose

STINT 2 begins from the closed STINT 1 evidence denominator matrix and builds the measurement frame required before any model-performance claim.

The first goal is not model training. The first goal is independent evaluation material: annotation protocol, candidate samples, frozen evaluation sets, and reporting controls that prevent circular measurement.

## Starting Point

- Source branch: `stint-1-evidence-ground-truth`
- Closure commit: `ad59514`
- Closure tag: `stint1-denominator-closure-v0.7`
- Frozen reference layer: `../stint-1.1-reference-layer`
- Frozen evidence layer: `../stint-1-evidence-ground-truth`

## Non-Goals

- Do not modify STINT 1.1 or STINT 1 artifacts from this branch.
- Do not report F1, accuracy, coverage, or confidence without an explicitly independent evaluation set.
- Do not use frozen evaluation sets for training, tuning, rule creation, or prompt calibration.
- Do not aggregate proxy paths into a global denominator.

## Work Groups

| group | purpose |
|---|---|
| `g0_independent_evaluation` | Build annotation protocol, samples, and frozen evaluation sets. |
| `g1_actionable_zeros` | Work the two actionable zeros: Object Part crosswalk and FLOC alignment. |
| `g2_baseline_models` | Train auditable baseline models only after G0 measurement gates exist. |
| `g3_semantic_models` | Test semantic/feature-rich models under the same evaluation constraints. |
| `g4_calibration` | Build reliability curves and threshold recommendations. |
| `g5_error_analysis` | Analyze confusion, failure modes, and target/path breakdowns. |
| `g6_consolidated_results` | Consolidate target-level findings without over-claiming. |

## Governance

All produced artifacts must keep evidence provenance, tier, target, contractor path, stratum, and evaluation independence as separate axes.
