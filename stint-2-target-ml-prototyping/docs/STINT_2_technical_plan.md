# STINT_2 — Technical Plan
## Target-Specific ML Prototyping

**FSA BRIDGE / AI-ML Workstream**
Successor to STINT_1 · Evidence Reconstruction & Surrogate Ground Truth

---

## Framing

> **STINT_0** measured the evidence problem.
> **STINT_1** reconstructed a defensible evidence layer.
> **STINT_2 asks what ML can learn from it — target by target, not as a single classification problem.**

---

## Objective

Build and evaluate target-specific classification prototypes on the proxy evidence produced by STINT_1, with declared provenance, calibrated confidence, and non-circular evaluation.

**Out of scope:** production deployment, contractual accuracy claims, retraining loops, `/classify` endpoint delivery.

---

## Inherited constraints — non-negotiable

These come from STINT_1 and govern every phase.

| Constraint | Source | Consequence |
|---|---|---|
| `evaluation_independence: independent = 0` | all F4/F5 evidence | held-out must be built before any metric is interpreted |
| Contractual denominator = MAT only | F6 | five targets can only be evaluated against proxy |
| No cross-path aggregation | F6 | separate denominators, separate metrics, always |
| `anchor_source` matters | B1.2b, F5.1a | `sap_catalog` anchors over-generate; filter before counting |
| MAT resolved by field | B1.1 | out of ML scope in the relational path |
| Domain benchmark 0.75–0.85 F1 | NIST/Lutz, Malyi | expectation reference, never a POC claim |

### The circularity constraint — read this first

All STINT_1 evidence carries `evaluation_independence: derived_from_rules`, generated with `paraphrase-multilingual-MiniLM-L12-v2`.

> **A classifier using semantic embeddings, evaluated against these labels, measures itself against its own logic.** High accuracy, zero information.

**Therefore:** no metric produced in this stint is interpretable until an evaluation set exists that is independent of the mechanism that generated the labels.

---

## Phase G0 — Independent Evaluation Set

**The first phase, and the precondition for every metric in this stint.**

### Why it comes first

STINT_1 produced 80 blind reviews on `reason`, registered as `model_blind_review` and `human_blind_review`. They are **potentially independent material, not a held-out set** — the sample is small, drawn from one field of one path, and the residual round over-represents hard cases.

Without expanding this, STINT_2 can train but cannot evaluate.

### G0.1 — Blind annotation protocol

Define before annotating anything:

```
input shown       raw text, PII-redacted
input NOT shown   pipeline proposal · anchor · confidence · target hint
question          single, closed, per target
responses         controlled vocabulary + abstain
environment       closed, local, permissions 600, not versioned
output            hash → response only
```

**Anchoring bias rule:** if the annotator sees the pipeline proposal and confirms or rejects it, the record is `human_validated`, **not** `independent`. Only unprompted assignment qualifies.

**Deliverable:** `g01_blind_annotation_protocol.md`

### G0.2 — Stratified annotation sample

Draw from all three paths, stratified by:

```
path             PATH_A · B1_RELATIONAL · B2_WORKBOOKS
target           the six with proxy evidence
stratum          as declared in F6
anchor_source    domain_vocabulary vs sap_catalog
```

**Target size:** 150–300 records per target where evidence allows. Where a target has fewer proxy units than that, annotate all of them and declare the ceiling.

⚠️ **Do not draw only from high-confidence bands.** An evaluation set biased toward easy cases inflates every metric downstream.

**Deliverable:** `g02_annotation_sample_sanitized.csv`

### G0.3 — Inter-annotator agreement

Where two annotators are available, annotate the same subset independently and report agreement.

**This matters more than it appears.** No one measures how much two reviewers agree on the same record in a multi-thousand-code catalog. If agreement is 0.70, then a model at 0.68 operates within the variability of the available standard — and that reframes the entire accuracy question.

**Honest limitation to declare:** no SME is available. Annotators can judge whether a field carries information of a given type; they cannot validate domain correctness of a specific SAP code assignment.

**Deliverable:** `g03_inter_annotator_agreement.md`

### G0.4 — Evaluation set registration

```
evaluation_independence   independent
label_generation_method   blind_human_annotation
annotator_id              recorded
excluded_mechanisms       rule_set_v1, semantic_prototype_matching_v1,
                          paraphrase-multilingual-MiniLM-L12-v2
```

**Deliverable:** `g04_evaluation_set_v1.csv` — frozen, never used for training.

---

## Phase G1 — Actionable Zeros

**Two targets sit at zero not for lack of signal, but for a missing mapping step. Both are cheap relative to their return.**

### G1.1 — Object Part: material → Catalog B crosswalk

```
current state    B1 proxy = 0
available        consumption entity · 15,358 item-signal rows
                 4,079 orders with item signal (38% of 10,749)
                 708 distinct source item concepts
blocker          no mapping from material/source item to Catalog B
```

**Tasks:**

- Profile the 708 concepts: frequency distribution, coverage of the order universe
- Determine whether a controlled material catalog exists in the corpus
- Build `material_concept → catalog_b_code` crosswalk, anchored to the Wind Catalog
- Report coverage and residual

**Provenance:** the crosswalk is `expert_inference`. The material record itself is `real_observed_label`. Keep them on separate rows.

⚠️ **Investigate the 62% of orders without consumption.** Cross against `activityType` — if they concentrate in specific work types, that explains coverage and bounds where Object Part is reachable.

**Deliverable:** `g11_material_to_catalog_b_crosswalk.csv` + coverage memo

### G1.2 — FLOC leaf: IH06 alignment

```
current state    proxy = 0 in every path
available        internal joins at 99.99% (asset) and 100% (site)
                 IH06: 88,441 rows · 9 sites · depth 4–5
blocker          no alignment between relational asset references
                 and IH06 functional location nodes
```

**Confirmed constraints from STINT_1:**

- Zero rows at depth ≥ 6 — the reachable leaf is Component/Maintainable Item, not Part
- Depth is **not homogeneous across sites** (max depth 4 at some, 5 at others)
- Measure per site, never globally
- An Object Part more granular than the FLOC leaf **has no node to land on**

**Tasks:**

- Map asset identifiers from the relational path to IH06 nodes
- Report match rate **per site**
- Where text matching is required, use `LEXICAL_LAYER v2` high-band anchors only
- Declare the reachable depth per site

⚠️ **`max_depth = 4` at a site may mean less modelled granularity, or an incomplete extract.** The data does not distinguish. Do not read it as an asset property without verification.

**Deliverable:** `g12_floc_alignment_by_site.csv` + verdict on reachability

---

## Phase G2 — Baseline Models

**Interpretable, auditable, and measured before anything more complex is justified.**

### G2.1 — Per-target, per-path baselines

```
approach     TF-IDF + linear classifier (LR / linear SVM)
scope        one model per target per path — never pooled
rationale    interpretable, auditable, cheap, and required
             as a reference point
```

**Why per-path:** B1 is relational and transactional; B2 and Path A are reconstructed snapshot events. Different distributions. A model trained on one and evaluated on the other measures nothing.

### G2.2 — Feature design

Driven by two artefacts already produced:

```
canonical-constraints.md     defines the output space
                             field · type · cardinality per target
reference-layer-v1           supplies the input vocabulary
                             normalisation · canonical concepts
```

**Cardinality shapes the problem, and the contract already declares it:**

```
header    1 per notification    FLOC · MAT · Symptom   → single-label
items     0..10 per record      B · C · 5 · A          → multi-label
```

**Mandatory feature-level fields:**

```
source_text_field    DELTA-0003 · which field the evidence came from
anchor_source        domain_vocabulary | sap_catalog
stratum              as declared in F6
```

⚠️ **`anchor_source` is a first-line filter, not a post-hoc check.** Catalog-derived anchors over-generate — 91% of Damage signal in B1.2 came from `SAP_MAPPING`, and the same mechanism produced the 365 false Symptom candidates that F5.1a discarded.

### G2.3 — Class imbalance

STINT_1 did not assess class distribution per target. Before training:

- Report label distribution per target per path
- Declare handling: class weights, resampling, or none
- Report **macro F1 alongside weighted F1** — a target dominated by two codes can show high weighted F1 while failing every minority class

**Deliverable:** `g2_baseline_results.md` — per target, per path, with distributions

---

## Phase G3 — Semantic Models

**Only after baselines exist and have been measured.**

### G3.1 — Justification, already empirical

STINT_1 measured, on this corpus:

```
string/token matching     5.24%
semantic embeddings      62.73%
```

That is a 12× difference on our own data, not a benchmark claim. It establishes that lexical-only approaches under-serve a multilingual, telegraphic corpus.

### G3.2 — Approach

```
embeddings + classifier head, or few-shot prototype matching
model: same as STINT_1 for pipeline consistency
```

⚠️ **Circularity check, mandatory before interpreting any result:**

```
IF classifier mechanism == label generation mechanism
THEN evaluation is circular
     → evaluate only against G0 independent set
     → or use a mechanistically different classifier
```

### G3.3 — Normalisation is not optional

STINT_1 demonstrated this directly: the same semantic classifier went from 366 to 1,827 recovered rows purely by normalising input before embedding.

**Apply the 5-step pipeline from `SEMANTIC_NORMALISATION`:**

```
mask tags → clean → expand abbreviations → correct spelling → NER
```

**And do not pre-translate.** Multilingual backbone plus bilingual canonical dictionaries — the decision was validated empirically: the Spanish alias layer added 9 net rows (0.11%), because the model already resolved ES↔EN.

**Deliverable:** `g3_semantic_results.md`

---

## Phase G4 — Calibration and Abstention

**Coverage without precision is worthless. STINT_1 proved this three times.**

### G4.1 — Confidence calibration

- Method must be declared: Platt scaling, isotonic regression, or temperature scaling
- Report reliability curve per target
- Calibration is measured on the **G0 independent set**, never on proxy labels

### G4.2 — Threshold selection

**Adopt the rule that worked in STINT_1:**

```
select threshold maximising coverage subject to precision >= 0.80
report the full curve, not just the selected point
```

**Precedent:** F1e2 found high band 10/10, middle 3/10, borderline 1/10. Coverage was reported at 35.6% when 62.73% was available. **That decision was correct and must be repeated.**

### G4.3 — Abstention

```
abstention is a legitimate output, not a failure to minimise
```

Every target must be able to return `UNKNOWN`. A record with no defensible candidate abstains.

**Deliverable:** `g4_calibration_memo.md` — thresholds, curves, abstention rates per target

---

## Phase G5 — Error Analysis

**Where the POC produces its most transferable findings.**

- Confusion matrices per target per path
- **Error breakdown by `anchor_source`** — do catalog-derived anchors fail more than domain vocabulary?
- Error breakdown by stratum — does planned vs reactive segmentation matter?
- Error breakdown by site — FLOC especially
- Qualitative review of a sample of errors, blind-designed

**Question to answer explicitly:** are the errors concentrated in specific codes, specific sites, or specific text patterns? That determines whether the ceiling is data, method, or vocabulary.

**Deliverable:** `g5_error_analysis.md`

---

## Phase G6 — Consolidated Results

### Reporting rules — inherited and mandatory

```
✅  "F1 = X against proxy evaluation set, n=N, path=P"
✅  "coverage X% at precision >= 0.80, threshold T"
✅  "abstention rate X%"

❌  "accuracy = X"                       without qualifier
❌  metrics aggregated across paths
❌  metrics against derived_from_rules labels
    presented without the circularity caveat
❌  any comparison to the 95% contractual figure
```

### Reporting structure

```
target × path × metric × evaluation_set_type
       × n × threshold × coverage → value
```

`evaluation_set_type` is a mandatory column: `independent` or `proxy_derived`.

**Deliverable:** `g6_results_matrix.csv` + closure report

---

## Sequence and dependencies

| Phase | Focus | Depends on | Parallelisable |
|---|---|---|---|
| **G0** | Independent evaluation set | — | — |
| **G1.1** | Object Part crosswalk | — | ✅ |
| **G1.2** | FLOC alignment | — | ✅ |
| **G2** | Baselines | G0, G1 | — |
| **G3** | Semantic models | G2 | — |
| **G4** | Calibration | G2, G3 | — |
| **G5** | Error analysis | G4 | — |
| **G6** | Consolidation | all | — |

**Critical path:** G0 → G2 → G3 → G4 → G6
**G1.1 and G1.2 run in parallel from day one** — they unblock two targets currently at zero.

---

## Closure criteria

Per target, per path:

- Baseline result, or explicit declaration that the target is not modellable
- Semantic result where applicable
- Threshold and coverage declared with the selection rule
- Metrics against `independent` evaluation set where it exists; clearly marked `proxy_derived` where it does not
- Abstention rate reported
- Error analysis with breakdown by `anchor_source` and stratum

**Declaring that a target cannot be modelled with available evidence is a valid and expected result.**

---

## Risk register

| Risk | Mitigation |
|---|---|
| Circular evaluation | G0 first; `excluded_mechanisms` recorded; `evaluation_set_type` mandatory in all reporting |
| Proxy metrics read as verified accuracy | qualifier mandatory in every reported figure |
| Path aggregation | separate models, separate metrics, no pooled reporting |
| `sap_catalog` anchors inflating results | `anchor_source` as first-line filter and as error-analysis dimension |
| Evaluation set biased toward easy cases | stratified sampling in G0.2, not confidence-band sampling |
| Class imbalance hidden by weighted metrics | macro F1 reported alongside weighted |
| Over-engineering | timebox per phase; baseline before complexity; explicit sufficiency criterion |

---

## Open debts carried forward

Not resolved in STINT_2 unless they block a phase:

```
LEXICAL_LAYER provisional        frequency filtering + domain grouping
SEMANTIC_NORMALISATION partial   WMEP / NREL population incomplete
F5.2 inverse derivation          deferred · optional extension
Grouping ownership               design decision · simulates SyncHub behaviour
OEM dictionary polysemy          81 polysemous codes · composite key required
```

---

## What STINT_2 hands to STINT_3

STINT_3 covers POC evaluation, robustness, and confidence calibration at system level. It receives from here:

- Per-target models with declared method and scope
- Calibrated thresholds with abstention policy
- An independent evaluation set, however small
- Error analysis identifying whether ceilings are data, method, or vocabulary
- A clear statement of which targets are modellable and which are not
