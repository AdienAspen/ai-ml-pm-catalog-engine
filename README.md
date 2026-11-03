# FSA BRIDGE - ML Feasibility for SAP S/4HANA PM Catalog Mapping

This industry-grade POC examines when legacy plant maintenance records contain enough evidence to support mapping into SAP S/4HANA Plant Maintenance catalog codes.

The implementation and cited evidence are maintained on the [`stint-2-target-ml-prototyping` branch](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/tree/stint-2-target-ml-prototyping); `main` is the public overview. Artifact links below point to that branch.

## Development stages

The published branches preserve successive stages of the project ("stints") and show how the evidence and methods evolved. `feasibility-assessment` contains the initial prospection; `reference-layer-v1` adds the reference layer; `stint-1-evidence-ground-truth` reconstructs the evidence and denominators; and `stint-2-target-ml-prototyping` contains the target-specific diagnostics. `main` provides this overview.

## Scope and findings

The deliverables are a frozen reference layer, path-specific evidence, blind diagnostic annotation, and an auditable [figure register](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/outputs/f6_final_denominators_sanitized.csv). This is not a production service or a deployed classifier. No supervised classifier is trained or shipped, and no result here establishes contractual accuracy.

The analysis separates direct fields, structural joins, text-derived candidates, catalog-profile constraints, and upstream data preparation. A text signal can be reproducible while the permitted catalog codes do not express it; signal presence, catalog coverage, and code correctness are different claims. The [F6 memo](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/outputs/f6_final_memo.md) and [closure manifest](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/docs/stint2_closure_manifest.md) give the source, unit, universe, and limitation for each cited figure.

| B1 finding | Persisted figure | Interpretation |
|---|---:|---|
| MAT direct field | 10,749 orders | The sole contractual denominator; not an ML prediction. [F6](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/outputs/f6_final_denominators_sanitized.csv) |
| Asset-level FLOC structural match | 10,699 of 10,749 orders | Structural asset alignment; no component leaf admission. [F6](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/outputs/f6_final_denominators_sanitized.csv) |
| Object Part / Activity corpus anchors | 7,668 / 7,606 orders | Descriptive full B1 corpus; concepts are not validated SAP codes. [G2.0c contrast](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20_corpus_native_domain_vocab/g20c_coverage_contrast_sanitized.csv) |
| Damage / Cause / Symptom semantic signal | 3,078 / 289 / 104 orders | External-vocabulary detector on a different, 9,263-order model-eligible B1 universe; not comparable as prevalence to the preceding row. [G2.0d2 comparison](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20d2_semantic_reference_coverage/g20d2_detector_comparison_sanitized.csv) |
| Component profile candidate | 3,935 orders | Text-assisted node or profile resolution, not a validated component FLOC or code assignment. [G2.0k.3 partition](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20k_component_lift/g20k3_partition_summary_sanitized.csv) |

These rows have different evidence levels and universes; they must not be added or treated as a global success rate. The four operating layers are deterministic structure, ML-addressable signal, operator decision, and data preparation. [F6](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/outputs/f6_final_denominators_sanitized.csv) records the layer for each figure.

## Sources and targets

| Path | Source | Counting unit | Availability |
|---|---|---|---|
| B1 relational | Relational maintenance records and work-order fields | Order or explicitly named source unit | Raw source not versioned |
| Path A | Daily PDF snapshots | Snapshot row or estimated event, according to the artifact | Raw PDFs not versioned |
| B2 | Daily workbooks | Snapshot row or estimated event, according to the grouping rule | Raw workbooks not versioned |

Paths are never aggregated. Path A and B2 snapshot groupings are provisional; episode reconstruction is required before treating them as completed maintenance histories. The path-specific counts and grouping rules are indexed in the [closure manifest](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/docs/stint2_closure_manifest.md). Private sources belong under `data/raw/source_package/` or the relevant ignored `data/interim/extracted_source/` staging area, not in Git.

| Target | SAP destination or field | Resolution investigated |
|---|---|---|
| MAT / Activity Type | Direct structured field | Observed value |
| FLOC | Functional location | Structural asset join; component remains candidate-level |
| Symptom | Catalog S | Text signal and profile-scoped code space |
| Object Part | Catalog B | Text concepts, material crosswalk, component/profile constraints |
| Damage | Catalog C | Text signal and two-level group/code annotation |
| Cause | Catalog 5 | Text signal and profile-scoped code space |
| Activity | Catalog A | Text signal and catalog-code applicability |

A catalog profile (`RBNR`) restricts the valid **group-and-code pairs** for a technical object. A detected concept, reachable code, and correct assignment are separate stages; the [resolution-chain specification](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/docs/G2.0i-resolution-chain-code-spec.md) documents the filters and scoring.

## Method and evidence

```text
source record -> normalized text / direct fields -> domain concept
              -> hierarchy node -> inherited catalog profile -> eligible group + code pair
```

Not every target uses every stage: MAT is direct, asset-level FLOC is structural, and text-derived candidates require additional checks.

| Stage | Implemented work | Main reference |
|---|---|---|
| Initial prospection | Numbered inventory, schema, source and safety scripts in `scripts/` | [STINT 0 plan](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/docs/stint_0_reconstruction_plan.md) |
| STINT 1.1 | Frozen canonical constraints, source designations, normalization and SAP reference vocabulary | [Reference layer](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-1.1-reference-layer/README.md) |
| STINT 1 | Path-specific evidence reconstruction and denominator matrix | [Evidence layer](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-1-evidence-ground-truth/README.md) |
| STINT 2, G0/G1 | Blind evaluation registration, material crosswalk and asset alignment | [STINT 2 overview](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/README.md) |
| STINT 2, G2.0c-k | Corpus-native concepts, external-vocabulary detectors, catalog-code diagnostics, profile inheritance and component-link partitions | [Closure manifest](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/docs/stint2_closure_manifest.md) |

G2.0c embeds filtered corpus terms with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, groups normalized vectors with `MiniBatchKMeans`, and maps concepts to target and catalog candidates in later, separate steps. The [Step 3 memo](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20_corpus_native_domain_vocab/g20c_step3_semantic_grouping_memo.md) records the historical fit; the [release reconciliation](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20_corpus_native_domain_vocab/g20c_release_sanitization_memo.md) distinguishes later member pruning from reclustering. Dependency constraints are in [pyproject.toml](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/pyproject.toml) and pinned versions in [uv.lock](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/uv.lock).

Each F6 row carries `target`, `path`, `level`, `metric_id`, `unit`, `source_file`, `evidence_level`, `layer`, `universe`, and `conditions`. Expert inference, proxy evidence, structural observation, and diagnostic annotation are not interchangeable with verified code accuracy. [C1b derived diagnostics](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/outputs/c1b_g11f_profile_agreement_sanitized.csv) retain their own source and denominator.

## Annotation and evaluation

Blind LLM annotation was used as a diagnostic instrument, not as human subject-matter validation. The [v1 registration](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/artifacts/evaluation_sets/evaluation_set_v1/evaluation_set_v1_registration_summary.json) admits Cause, Object Part, and Symptom; the separate [v2 registration](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/artifacts/evaluation_sets/evaluation_set_v2/evaluation_set_v2_registration_summary.json) covers Activity and Damage under revised protocols. V2 has 300 distinct units and 75 shared units per target, yielding 375 separate annotator responses per target. Model identities in v2 come from project-lead attestation, not the response CSVs.

Agreement is reported by question and level using raw agreement, Cohen's kappa, Gwet's AC1 where available, class-level tables, and confusion matrices. The [v2 limitations](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/artifacts/evaluation_sets/evaluation_set_v2/evaluation_set_v2_limitations.md) explicitly mark it diagnostic and ineligible as a final held-out test. Evaluation keys are excluded from future model fitting; annotator responses are never merged into a consensus label.

## Repository map

```text
data/                              ignored private source and staging zones
src/asset_ml_feasibility/          reusable ingestion, parsing, profiling, evidence code
scripts/                           numbered initial-prospection entry points
stint-1.1-reference-layer/         frozen reference vocabulary and constraints
stint-1-evidence-ground-truth/     path-specific evidence and original F6 matrix
stint-2-target-ml-prototyping/
  g0_independent_evaluation/       annotation protocols and evaluation registration
  g1_actionable_zeros/             crosswalk, FLOC alignment, figure register
  g2_baseline_models/              detector and profile/component diagnostics
  g3_semantic_models/ ... g6_consolidated_results/  scaffolded downstream work
  artifacts/evaluation_sets/       versioned labels and exclusion metadata
  docs/                            technical plans and closure manifest
```

Generated, shareable counts and metadata live in `outputs/`. Visible-text packages and other sensitive review material remain in ignored `internal/` directories with restricted permissions; do not commit them.

## Reproduction

The code targets Python 3.10 (`.python-version`); `pyproject.toml` requires Python 3.10 or newer. With `uv` installed:

```bash
uv sync --frozen --extra dev
uv run python scripts/00_environment_check.py
uv run pytest -q
```

The numbered root scripts, STINT 1 phases, and STINT 2 `g*` scripts are **not** a single public end-to-end runner. Recomputing source-dependent steps requires the unversioned client inputs, local model assets, and the step-specific plans. For the published aggregate checks, run `stint-2-target-ml-prototyping/g1_actionable_zeros/g1_denominator_update/scripts/c1b_persist_diagnostics.py`, then `f6_register_final_denominators.py`, then `stint-2-target-ml-prototyping/docs/generate_stint2_closure_manifest.py` only in an authorized environment containing their private inputs. Those scripts assert the expected source counts and unique metric keys. The [manifest](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/docs/stint2_closure_manifest.md) lists each step's exact memo and output.

## Limits and next decisions

- No independently verified SAP-code precision or production threshold is claimed. LLM annotations are not human expert labels; diagnostic overlap is not a final held-out estimate.
- G2.0d2 and G2.0j use a declared 128-token input limit. See their [detector memo](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20d2_semantic_reference_coverage/g20d2_memo.md) and [catalog-coverage memo](https://github.com/AdienAspen/ai-ml-pm-catalog-engine/blob/stint-2-target-ml-prototyping/stint-2-target-ml-prototyping/g2_baseline_models/outputs/g20j_catalogue_code_coverage/g20j_memo.md).
- Profile filtering describes code eligibility, not correctness. A recurring text concept without an eligible code is characterized as potential catalog or profile-configuration non-coverage, not silently discarded.
- Component-level registration needs an explicit operator decision and independent human review. Path A and B2 need data-engineering episode reconstruction before their estimated events can serve as completed histories.

`G2` is not closed by this evidence register. The next modeling decision should use target-specific, path-specific evaluation and the declared registration level; it should not extrapolate these diagnostic figures into a contractual success rate.

## Publications

For a deeper account of the main engineering findings and contributions, see the forthcoming white paper and related publications. Links will appear here as they become available.

- Medium — white paper; link pending.
- Weights & Biases — related publication; link pending.
- LinkedIn — project summary; link pending.

## License

This repository includes the [Apache License 2.0](LICENSE).
