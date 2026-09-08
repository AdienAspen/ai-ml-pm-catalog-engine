# STINT_1 — Closing Report
## Evidence Reconstruction & Surrogate Ground Truth

**FSA BRIDGE / AI-ML Workstream**
Document for Technical Committee · Handoff to STINT_2

---

## Executive Summary

STINT_1 converted an unlabeled corpus into target-level evaluable evidence, with traceable per-record provenance.

**The result in one line:**

> One target has real observed evidence. Five have reconstructed proxy evidence. One remains at an explicit zero with declared debt.

```
Contractual denominator    Activity Type / MAT · 10,749 records
                           All other targets · 0

POC proxy denominator      Symptom      1,999
                           Damage       1,489
                           Cause        1,343
                           Activity     1,628
                           Object Part    768
                           FLOC leaf        0
```

All denominators are **per path, never aggregated**. The totals above are diagnostic and must not be used as a single denominator.

---

## 1. What Changed About the Nature of the Project

The project began as a production migration with an active channel to the client. During STINT_0 that channel was permanently lost: no SME, no ground-truth validation, no confirmation of controlled sources, and no canonical update.

**The project was reframed as an industry-grade POC.** This did not lower the methodological standard — it changed the source of truth, not the rigor applied to it.

**Adopted governing rule:**

> Never conceal what is observed, validated, proxy, synthetic, or inferred.

Direct and non-negotiable consequence: the project may report `accuracy against validated proxy evaluation set`. **It may not report `verified production accuracy`.** The original contract's 95% does not apply to the POC.

---

## 2. Corpus Anatomy

Three source families, with incompatible natures.

| Family | Volume | Nature | Counting unit |
|---|---|---|---|
| **Path A** · OEM_ENTITY_001 PDFs | 394 files → 602 rows → **362 events** | Plan of Day / End of Day · state snapshot | `estimated_event` |
| **B1** · relational | 21 files = 7 entities × 3 formats → **10,749 records** | API dump · atomic records | `physical_record_id` |
| **B2** · OEM_ENTITY_001 workbooks | 127 files → 1,988 rows → **1,857 events** | daily state workbooks | `estimated_event_key_with_snapshot_date` |

**Reading note:** the 21 B1 files are 7 logical entities serialized as JSON, XLSX, and XML. They are 7 sources, not 21.

### The Finding That Reordered the Project

**B1 is not a spreadsheet family. It is a relational API dump.**

```
api_common_v1    assets · sites · customers · contracts        master data
api_service_v1   service-orders · service-visits · consumption transactional
```

Fourteen relationships between entities, with match rates from 93.6% to 100%. This changed the scope of ML work in that path: much of it is resolved by joins, not classification.

### The Structural Conclusion About the Corpus

> **These notifications never existed.** The corpus is the contractor's operational documentation, not the client's maintenance system. The project is not reconstructing lost records — it is creating SAP records that were never issued, from data not designed for that purpose.

This explains the absence of ground truth, the scarcity of Symptom, and why an SME was indispensable.

---

## 3. Phase Walkthrough

### F0 — Consolidation and Preconditions

- Reconciliation of denominators inherited from STINT_0: `838 + 72 = 910`, `147 vs 157`
- G04 closed by documented proxy · G08 closed with 0 parser issues
- **DELTA-0002** resolved: `stint1_record_id` with declared composition and duplicate check
- **DELTA-0003** resolved: text-field routing table by target
- Safeguards added: `physical_record × target` counting unit, `label_generation_method` and `evaluation_independence` fields, contractual denominator hardened with `tier=gold` and `status=resolved`

### F1 — Lexical Layer

```
10,639 observed terms  →  filtering  →  semantic clustering
                                            ↓
                            359 high-confidence canonical concepts
                            usable coverage 35.6%
```

**Method finding:** string matching produced 5.24% anchoring. With multilingual embeddings it rose to **62.73%**. Twelvefold, measured on the corpus itself.

**Calibration was as important as the jump:** manual review showed precision of 10/10 in the high band, 3/10 in the middle band, and 1/10 at the boundary. **35.6% usable** was reported, not the 62.73% raw coverage.

### F2 — Semantic Reconciliation

- The 802 `unknown` rows classified into 22 pattern groups: 662 out of scope, 94 pending, 28 unrelated co-occurrences, 18 vocabulary matches
- **DELTA-0009 resolved:** Cause, Activity, and Activity Type shared a multi-target expansion. They are not independent evidence. Nothing was promoted

### F3 and F3.5 — Path A

F3 ran correctly on a poorly characterized universe. F3.5 repaired it:

- **52% of rows were status codes, not fault codes.** `Repair` and `Maintenance` mirrored status-panel categories. They were moved to the `asset_state` namespace
- **NOTES recovered.** A sequential extractor reported 3.89% coverage; the spatial extractor produced **95.51%**. NOTES is a parallel column, not a stacked section
- **Deduplication:** 602 rows → 362 events. Compression was 3.56x in `asset_state` and 1.07x in fault codes — a differential that independently validates the partition
- **Integration:** 743 evidence rows, 96% from NOTES

### F4 — Path B in Two Paths

**B1 · relational**

```
MAT           direct activityType field        → 10,749 · out of ML scope
Object Part   consumption · requires material→catalog B mapping
Activity      structural + textual remainder
FLOC leaf     internal joins 99.99% · SAP alignment missing
Cause         reason · mixed semantics
Damage        no dedicated field · textual only
Symptom       no declared pre-execution field
```

**B2 · snapshot**

- 127 workbooks, 10 template variants, validated positive control 12/12
- EOD and POD compress similarly (4.98x and 4.05x): **the prefix does not determine the nature of the content.** Both are persistent state
- Duration refinement: only 5.7% of rows contain it in usable form. Robust incident reconstruction is not possible in B2

### F5 — Symptom

The target with the longest journey in the stint.

```
STINT_0     zero proof-of-life · 4 methods converge at zero
F5.1a       B2 thread · 365 events → discarded as catalog noise
F5.1b       reason · blind review → 1,827 candidates ⭐
F5.1c       lexicon · 289 terms → 41 survive in the high band
T5.1b2.4b   Path A and B2 · marginal but real signal
                        ↓
            1,999 candidates · 4 sources · 2 evidence-generation methods
```

**Formal verdict:** `symptom_signal_exists_as_proxy_candidate_but_is_not_ground_truth`

### F6 — Denominators

37 rows: 17 admitted, 14 explicit zeros, 6 not admitted. `count_unit` present in all.

---

## 4. The Denominator Matrix

### Contractual — `real_observed_label` + `tier=gold` + `status=resolved`

| Target | Path | N |
|---|---|---|
| Activity Type / MAT | Structured relational B1 | **10,749** |
| All others | — | 0 |

**MAT is the project's only `real_observed_label`.**

### POC Proxy — Per Path, Without Aggregation

| Target | Path A | B1 | B2 | Diagnostic total |
|---|---|---:|---:|---:|
| **Symptom** | 42 notes · 68 concern | 1,827 | 62 | 1,999 |
| **Activity** | 339 | 1,215 | 74 | 1,628 |
| **Damage** | 116 | 1,263 | 110 | 1,489 |
| **Cause** | 36 | 1,250 | 57 | 1,343 |
| **Object Part** | 280 | **0** | 488 | 768 |
| **FLOC leaf** | 0 | **0** | 0 | **0** |
| **MAT** | — | 10,749 | — | 10,749 |

⚠️ The total columns are **diagnostic**. Each path counts different units — events, physical records, and dated events. Aggregating across paths is methodologically invalid.

### Three Readings Revealed by the Matrix

**1 · Object Part is zero in B1.** The richest path does not contribute to the target with the most candidates in the other two. The signal exists —`consumption` with 708 material concepts— but requires material → catalog B mapping before admission. **It is the most tractable gap in the stint.**

**2 · FLOC leaf at an absolute zero.** It has the project's best-resolved structural route — internal joins at 99.99%— and still produces no denominator. Alignment against the IH06 hierarchy is missing. **This is explicit debt, not an absence of data.**

**3 · Symptom exceeds Object Part.** The target we considered nonexistent has more proxy evidence than one with an available structural source. The difference is that Symptom was pursued to the end, while Object Part was blocked at a mapping step.

---

## 5. Status by Target

| Target | Route | Status | Observation |
|---|---|---|---|
| **Activity Type / MAT** | direct field | ✅ resolved | out of ML scope in B1 |
| **Activity** | structural + textual | proxy | 1,628 candidates across 3 paths |
| **Damage** | textual | proxy · caution | 91% of anchors come from SAP catalog |
| **Cause** | textual | proxy | `reason` as support, mixed semantics |
| **Object Part** | join + textual | partial proxy | B1 blocked by material mapping |
| **Symptom** | textual | proxy candidate | not ground truth · 4 sources |
| **FLOC leaf** | join + matching | **explicit zero** | SAP alignment debt |

---

## 6. Produced Assets

**`reference-layer-v1`** — frozen in STINT_1.1, five objects, three complete and two declared partial:

```
CANONICAL_TAXONOMY · SOURCE_DESIGNATIONS · LEXICAL_LAYER
SEMANTIC_NORMALISATION · SAP_MAPPING
```

**OEM code dictionary** — 679 codes, 1,014 code-description pairs, extracted from the corpus itself.

External research established that no public catalogs for the relevant contractor/OEM fault-code sources exist. **This dictionary closes that gap internally.**

⚠️ **151 codes with multiple descriptions; 81 classified as probably polysemous.** The resolution key must be `code + description`, never `code` alone.

**Lexical layer v2** — 359 canonical concepts with provenance, based on vocabulary from the actual corpus.

**80 blind reviews** — two rounds over `reason`, with verified blind design. This is potentially independent calibration material. It does not constitute a held-out evaluation set.

---

## 7. Methodological Findings

Five substantive corrections in the stint came from **cross-checking outputs against prior evidence**, not from running more analysis:

```
3.89% of NOTES        →  extractor artifact, it was 95.51%
Activity: 0           →  NOTES not integrated into the crosswalk
convergence 0         →  misaligned site keys
52% of universe       →  status codes, not fault codes
Symptom nonexistent   →  field misrouted from F0
```

**None was detected by the pipeline. All were detected through cross-reading.**

### Established Rules

- **No zero is interpreted until the extractor is validated against a known positive case.** This saved a phase on four occasions
- **Characterize the source before parsing it.** Treating snapshots as events cost a full phase in Path A
- **`evidence_type` and `tier` are independent axes.** Origin and confidence are never collapsed
- **Anchor origin matters.** Domain vocabulary and SAP catalogs are not equivalent in strength. The catalog produces broad matches because it is coded description, not technician language
- **High coverage with low precision is not useful.** 35.6% was reported despite 62.73% being available

---

## 8. Open Debts Toward STINT_2

| Debt | Origin | Impact |
|---|---|---|
| **No `evaluation_independence: independent` material** | entire stint | held-out must be built from scratch |
| **FLOC leaf without SAP alignment** | B1.1 | only target at zero |
| **B1 Object Part without material→catalog B mapping** | B1.1 | blocks the richest target path |
| **Provisional `LEXICAL_LAYER`** | STINT_1.1 | frequency filtering and domain clustering missing |
| **Partial `SEMANTIC_NORMALISATION`** | STINT_1.1 | WMEP and NREL partially populated |
| **F5.2 inverse derivation** | F5 | deferred · optional extension |
| **Grouping as owner** | B2 | design decision pending |

### Circularity Risk — The Most Important

All F4 and F5 evidence carries `evaluation_independence: derived_from_rules`, generated with `paraphrase-multilingual-MiniLM-L12-v2`.

> **A classifier using semantic embeddings and evaluated against these labels would be measured against its own logic.** High accuracy, zero information.

**The held-out can only be built with `independent` records, or by explicitly excluding the rule set and model that generated the labels.**

The 80 blind reviews are `model_blind_review` and `human_blind_review`. They are a seed for future independent annotation, not a held-out evaluation set. Expanding them with blind design is probably the highest-return investment for STINT_2.

---

## 9. Scope Statements

**About Grouping**

> Reconstructing events from snapshots simulates the behavior that would correspond to SyncHub/FSA-Bridge in production. It was run here because there is no definable denominator without constituted events. **It is not an ML workstream deliverable.**

**About Metrics**

> Every metric is reported against the `proxy evaluation set`, never as verified accuracy. The published domain benchmark —0.75 to 0.85 F1 on wind work orders— is an expectation reference, **not a POC claim.**

**About Symptom**

> Proxy candidate signal exists in four sources, with 1,999 admitted units. **It is not ground truth.** It remains `expert_inference`, maximum tier `silver-medium`, outside all contractual denominators.

**About the Absence of Symptom in the Original Corpus**

> The corpus documents execution, not detection. Evaluating the client's monitoring systems —SCADA, CMS— as an alternative source is recommended. In their absence, a sentinel code preserves record integrity without fabricating information.

---

## 10. Completion Criteria — Verification

For each of the seven targets:

- ✅ Contractual denominator declared, even if zero
- ✅ Proxy denominator declared, even if zero
- ✅ `evidence_type` and `tier` supporting each one
- ✅ Provenance documented per record
- ✅ Declared route: deterministic, ML, or unattainable
- ✅ Segmentation by path and stratum, without aggregation
- ✅ `count_unit` present in all 37 matrix rows

**No silent zeros. No hidden debt.**

---

## Conclusion

STINT_0 measured the evidence problem. **STINT_1 built a defensible evidence layer without inventing it.**

The result is not a labeled corpus. It is a corpus with **traceable proxy evidence, per-record provenance, and declared limits** — the maximum that can be produced when the validation channel does not exist.

**STINT_2 can be designed target by target**, not as a single classification problem. It also inherits a constraint that governs its evaluation design: without independent material, the first task is not training — it is building what to measure against.
---
