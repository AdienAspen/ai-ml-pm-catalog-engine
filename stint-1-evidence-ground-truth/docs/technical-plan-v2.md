# Technical Plan v2 — STINT_1
## Evidence Reconstruction & Surrogate Ground Truth

**FSA BRIDGE / AI-ML Workstream**
*Updated after the closure of `STINT_1.1-reference-layer`*

---

## Framing

> **STINT_0** measured the evidence problem. **STINT_1.1** built the reference layer.
> **STINT_1 reconstructs target-level evaluable evidence without inventing it.**

---

## Objective

For each of the 7 targets, produce an evaluable evidence set with traceable provenance that enables model prototyping in STINT_2.

**Out of scope:** training models, estimating accuracy, or closing the `/classify` contract.

---

## What Changed Since the Previous Version

| Area | Before | Now |
|---|---|---|
| Reference layer | did not exist | `reference-layer-v1` frozen |
| G06 / FLOC | via KKS + research | **KKS closed.** Uses lexical matching against IH06 |
| G03 / Fault codes OEM_ENTITY_001 | research pending | research exhausted. **No public catalog** |
| G05 / MAT | blocked without a source | ZEUS provides `maintenance_type` |
| G07 / Symptom | no framework | `≈ Failure Effect type 6` (hypothesis) + 289 lexical terms detected |
| G04 | pending | closed by documented proxy |
| G08 | open | closed — `0 parser issues` |
| Benchmark | nonexistent | 0.75–0.85 F1 published in the domain |

---

## Governance Principles

- **Granular per-row provenance** — `evidence_type` and `tier` on independent axes
- **Canonical frozen** — `v1.8-baseline-frozen`. Divergence goes to the `canonical-delta-log`, never overwrite
- **Denominators by target** — and by site/contractor/stratum where applicable. Never global
- **No performance claims** until a defensible denominator exists
- **`UNKNOWN` always allowed** — empty is better than invented
- **Never infer Cause from Damage**

---

## Debts Inherited from STINT_1.1

These are resolved within STINT_1, with an assigned owner:

| Debt | What is missing | Phase |
|---|---|---|
| Provisional `LEXICAL_LAYER` | frequency filtering + domain clustering | F1 |
| Partial `SEMANTIC_NORMALISATION` | populate WMEP and NREL GRD in the ZEUS scaffold | F1 |
| `DELTA-0002` | decide identity key for denominators | F0 |
| `DELTA-0003` | link primary text field by target | F0 |
| `DELTA-0009` | semantic split Activity / Cause / Activity Type | F2 |

---

## Phase 0 — Consolidation and Preconditions *(immediate)*

**Objective:** make the Feasibility Report auditable and resolve the two deltas blocking denominators.

- Incorporate denominator reconciliation (838+72=910; 147 vs 157)
- Correct G08 status — closed, `0 issues`
- Mark in the matrix that Cause / Activity / Activity Type share a multi-target expansion
- **Resolve DELTA-0002** — declare `physical_record_id` for denominator counts and `stint1_record_id` for record-field traceability. Without this there is no defensible denominator
- **Resolve DELTA-0003** — declare the primary text field by target. Without this there is no measurable evidence

**Deliverable:** Feasibility Report Draft 2 + updated `canonical-constraints.md`.

---

## Phase 1 — Lexical Consolidation (Revised)

Objective: convert the provisional dictionary into an operational layer.

Mandatory preliminary step — size before deciding

The T8c count reported rows by length, not distinct terms. Before any filtering:

count distinct observed_term_key by length in words

The 3,081 unigrams are a count of contextual rows and may be inflated by duplicates. The actual vocabulary may be substantially smaller.

Without this count, any sizing is blind.

Work
Frequency filtering — discard one-off n-grams without domain signal
Concept clustering — collapse variants into canonical_concept with stable concept_id
Expand sampling beyond the 600 records, maintaining stratification
Populate the ZEUS scaffold with WMEP and NREL GRD vocabulary, evidence_type per row
Preserve source_text_field per term


About the 300–800 range

It is a timebox heuristic, not a success criterion.

The correct number emerges from the domain. Forcing 800 merges distinct concepts; forcing 300 removes useful signal.

How to use it: if the result falls far outside the range, that is a signal to review the clustering method — not to adjust the result toward the number.

Deliverable: lexical_layer_v2 + complete SEMANTIC_NORMALISATION + count of distinct terms by length.

---

## Phase 2 — Semantic Reconciliation *(G02 + DELTA-0009)*

**Objective:** convert the 802 `unknown` rows into a real evidence map, and separate targets that share signal.

- Group by pattern, not by row — 15–30 groups are expected
- Classify: `matched_vocabulary`, `unrelated_cooccurrence`, `out_of_scope`, `pending`
- Human validation by group
- **Semantic split of the 36 multi-target structures** — determine whether Activity, Cause, and Activity Type have their own evidence or share one expanded signal

**Critical precondition:** without this split, none of the three can be promoted to target level.

**Deliverable:** `unknown_reconciliation_report` + `multitarget_split_report`.

---

## Phase 3 — Path A: Fault Codes OEM_ENTITY_001 *(G03)*

**Objective:** resolve the 79 fault-code tokens across 602 PDF records.

**Research is exhausted.** No public OEM_ENTITY_001 catalog or OEM→SAP crosswalk exists. The workflow is internal:

```
fault code → appearance context → maintenance concept
→ SAP candidate (B/C/5/A) + provenance + confidence
```

**Adopted rule:** do not force 1:1 equivalence. If a fault code does not map to a single SAP code, that is a valid finding.

**Available resources:** ZEUS scaffold, WMEP vocabulary, Malyi dictionaries by system.

**Deliverable:** `ge_fault_code_crosswalk` with `evidence_type: expert_inference`, tier based on convergence.

---

## Phase 4 — Path B: XLSX / Daily Maintenance Reports

**The largest workstream. Weak supervision is the primary tool.**

Semantic reconstruction from:
```
narrative + component + action + site + turbine
+ metadata + catalogs + business rules
```

Run **target by target**, issuing silver labels when multiple signals converge.

### Stratification — Confirmed Asymmetric *(T8a)*

- **`CONTRACTOR_PATH_001`** — explicit `activityType`, 100% coverage. Stratify directly
- **PDFs** — structural `event`. Separate stratum, **never planned/reactive**
- **Do not mix strata in the same denominator**

If planned/reactive derivation requires inference, mark it `expert_inference`.

### FLOC Leaf *(G06)* — Within This Phase

**KKS definitively closed.** There are no usable inherited designations. The route is lexical matching against the actual IH06 nodes.

**Confirmed constraints:**
- Actual hierarchy: 88,441 rows, 9 sites, depth 4–5
- **Zero rows at depth ≥ 6** — the available leaf is Component/Maintainable Item, not Part
- Depth is **not homogeneous across sites** — measure by plant, not globally
- An Object Part more granular than the FLOC leaf **has no node on which to land**

**Note:** the IH06 ↔ IEC crosswalk is coverage documentation, not a pipeline requirement. Low priority.

### Activity Type / MAT *(G05)*

- ZEUS `maintenance_type` as a conceptual scaffold
- `activityType` from `CONTRACTOR_PATH_001` as a direct signal where present
- Without a controlled OEM_ENTITY_001 source: reconstruction marked `expert_inference`

**Deliverable:** silver labels by target, with provenance and stratum.

---

## Phase 5 — Symptom *(G07)*

**The most difficult. Last, with deliberation.**

**Updated status:** T8 detected **289 lexical Symptom terms** in the corpus. They are not labels or codes, but they confirm that symptomatic vocabulary exists in the text. This enables Route A.

**Routes, in order of preference:**

- **A — Inverse derivation + cross-validation** ⭐ *(agreed strategy)*
  - Infer a plausible Symptom from Damage + Object Part + Activity
  - **Cross-check against a reference:** ZEUS `detection symptom` categories populated with WMEP effects
  - **Second filter:** the client's Wind S catalog. Anything not present there is discarded
  - **The cross-check filters; it never confirms.** It remains `expert_inference`, maximum tier `silver-medium`
- **B — Grounded synthetic** data based on the real Wind S catalog
- **C — Supervised expert inference**, documented as such
- **D — Accept the finding** — declare it not derivable. **Valid feasibility result**

**Preconditions:** requires B, C, and A to be resolved first. It must run **on the reactive subset**, not on the full corpus.

⚠️ **Prohibited:** filling with a generic value so the canonical is not empty. This turns an honest gap into unauditable false data.

⚠️ **`Symptom ≈ Failure Effect type 6` remains a `hypothesis`.** Do not crystallize it without FSA configuration evidence.

---

## Phase 6 — Denominators *(rewritten)*

**This is not a task — it is the consequence of the preceding phases.**

### The Distinction Governing the Entire Phase

F3, F4, and F5 produce mostly `expert_inference`. Excluding it completely would leave those targets with no form of evaluation.

**Therefore, two separate denominators are issued, never merged:**

```
┌─────────────────────────────────────────────────────┐
│  CONTRACTUAL DENOMINATOR                            │
├─────────────────────────────────────────────────────┤
│  Allows:   real_observed_label                      │
│           validated_mapping                         │
│           tier = gold                               │
│           status = resolved                         │
│  Excludes: expert_inference — no exceptions         │
│            reference_evidence                       │
│            external_corroboration                   │
│                                                     │
│  This is the only one that would answer the         │
│  contract's 95% requirement.                       │
│  Realistic expectation: zero or near zero for       │
│  several targets. That is a valid result.           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  POC PROXY DENOMINATOR                              │
├─────────────────────────────────────────────────────┤
│  Allows:   everything in the contractual            │
│           denominator                               │
│           silver-high                               │
│           qualified silver-medium                  │
│           expert_inference with complete provenance │
│                                                     │
│  ALWAYS reported as a proxy evaluation set.         │
│  NEVER as verified production accuracy.             │
│  This is what enables POC evaluation.               │
└─────────────────────────────────────────────────────┘
```

### Requirements for Including `expert_inference` in the Proxy

An `expert_inference` entry enters the proxy denominator only if it meets **all** of the following:

- Stable and resolvable `concept_id`
- Documented and reproducible derivation rule
- Declared source from which it is derived
- Valid canonical destination in `canonical-constraints.md`
- Tier assigned using explicit criteria
- Declared `label_generation_method`
- Declared `evaluation_independence`

**If any is missing, it goes to `unresolved`.**

### Counting Unit

`N` counts unique physical records by target, not evidence rows. Multiple convergent evidence rows over the same physical record and target count once.

`stint1_record_id` may identify `record-field` units for auditability, but F6 must deduplicate by `physical_record_id x target`.

### Evaluation Independence

Every proxy label must declare `label_generation_method` and `evaluation_independence`.

A held-out proxy evaluation set may only use records marked `independent`, or must explicitly exclude the rule set that produced the labels from the predictor under evaluation. If the same rule set generates and predicts the label, the evaluation is circular and cannot be reported as accuracy.

### Report Structure

```
target × denominator_type × evidence_type × tier
      × path × site × stratum → N evaluable records
```

`denominator_type` is a mandatory column. **A report that does not include it is invalid.**

### Rules That Do Not Change

- Never a global denominator
- Strata are not mixed — `event_structural` never with `planned/reactive`
- A zero denominator is a valid and expected result
- The contractual and proxy figures are **never presented together without labels**

**Deliverable:** `evidence_denominator_matrix` with both denominators separated by target.

---

## Update to the Completion Criteria

For each of the 7 targets, there must be:

- **Declared contractual denominator** — even if zero
- **Declared proxy denominator** — even if zero
- Tier and `evidence_type` supporting each one
- Provenance documented per record
- Method recommendation justified by actual evidence
- Declared stratification where applicable

---

## Update to the Risk Register

| Risk | Mitigation |
|---|---|
| Proxy reported as contractual | `denominator_type` mandatory in all output; verification in F6 |
| `expert_inference` enters proxy without provenance | five-requirement checklist, blocking |
| Circular evaluation over rule-generated labels | `label_generation_method` and `evaluation_independence` mandatory |
| Evidence convergence inflates denominators | count `N` by `physical_record_id x target`, not evidence rows |
| Vocabulary sized from inflated count | count distinct terms before filtering (F1) |
| 300–800 range treated as a target | explicitly declared a timebox heuristic |
