# Phase 4 — Rewrite
## Path B · Evidence Reconstruction by Source Family

**FSA BRIDGE / AI-ML Workstream · STINT_1**
*Replaces Phase 4 of Technical Plan v2, after F4.0 and F4.0b*

---

## What Changed

The previous version treated Path B as a homogeneous "XLSX / Daily Maintenance Reports" family and assumed weak supervision was the primary tool for all seven targets.

**Characterization revealed two families with opposite natures:**

```
CONTRACTOR_PATH_001    relational model · 7 entities · 33,660 records
                       atomic records · joins at 93.6–100%
                       → much of it is resolved without ML

OEM_ENTITY_001 EOD / POD           daily state workbooks
                       same nature as Path A
                       → requires deduplication before extraction
```

**Consequence:** two paths, same objective, different method. Never a shared denominator.

---

## Objective

Produce target-level evaluable evidence, with provenance and stratum, for both Path B paths.

**Guiding principle confirmed by characterization:**

> ML work is not about classifying everything. It is about classifying what cannot be resolved another way.

---

## Path B1 — `CONTRACTOR_PATH_001` · Relational

### Deterministic / ML Boundary — Established

| Target | Route | Method |
|---|---|---|
| **Activity Type / MAT** | direct `activityType` field | join · **out of ML** |
| **Object Part** | `consumption` → materials | join + material→catalog B mapping |
| **Activity** | structural + textual detail | join + ML over remainder |
| **FLOC leaf** | internal joins + SAP alignment | join + matching against IH06 |
| **Cause** | `reason` — semantics unconfirmed | text → ML |
| **Damage** | no dedicated field | text → ML |
| **Symptom** | no pre-execution field | ❌ unattainable |

### B1.1 — Deterministic Harvest *(First)*

- Extract `activityType` → **resolved MAT**, `evidence_type: real_observed_label`
- `consumption` → materials per order. Evaluate coverage and feasibility of rule-based mapping to catalog B
- Internal joins for FLOC: `assets → sites`, and alignment against the IH06 hierarchy
- **Nothing harvested here enters the ML pipeline.** It is structural evidence

**Deliverable:** `b1_deterministic_harvest` with tier and provenance by target.

### B1.2 — Textual Remainder *(Only What Remains)*

Targets: **Cause**, **Damage**, and **Activity** detail not covered by a field.

- Primary field: `description_extended` (96.2% coverage)
- Support: `reason` (100% coverage, semantics unconfirmed)
- Apply `LEXICAL_LAYER v2` — 359 concepts, high band only
- Weak supervision with signal convergence

**Deliverable:** `b1_silver_labels` by target, with declared `source_text_field`.

### ⚠️ B1.3 — Open Question About `reason`

`reason` is populated 100%, but its semantics are unconfirmed. In field-service models it is often the **reason for the visit** — why the technician was dispatched — not root cause.

> **If that is the case, it is closer to Symptom than Cause** — and would be the only field in the corpus with pre-execution information.

**Verify before routing it definitively.** Do not promote it while it remains unconfirmed.

---

## Path B2 — OEM_ENTITY_001 EOD / POD · Snapshot

**Same nature as Path A. Same treatment.**

### B2.1 — Pending Characterization

`F4.0` sampled `CONTRACTOR_PATH_002` and `SITE_PATH_002_SNAPSHOT` with low caps. Missing:

- Inventory of template variants by family
- Spatial extraction validated against a known positive case
- Locate prose fields outside routing

**Apply the F3.5 method, which is already proven.**

### B2.2 — Deduplication

The workbooks contain state: a condition persists across multiple daily files.

```
key: site + asset + code + window(incident_start ± tolerance)
incident_start_estimated = snapshot_date − duration
```

**Always report `snapshot_rows` and `estimated_events` separately.**

### B2.3 — Extraction and Weak Supervision

- Separate status codes from fault codes — `asset_state` namespace
- Extract technical prose where present
- Anchor against `LEXICAL_LAYER v2`

### ⚠️ B2.4 — EOD vs POD Verification

```
POD  →  Plan of Day   ·  state at the start of the shift
EOD  →  End of Day    ·  work performed
```

**No one has compared the two families.** If EOD records execution, it should have higher Activity density and less repetition.

**And the critical question:** does any EOD record the initial problem report? It is the only place in the corpus where Symptom might exist.

---

## FLOC Leaf *(G06)* — Cross-Cutting Both Paths

**KKS definitively closed.** No usable inherited designations. The route is matching against the actual IH06 nodes.

**Confirmed constraints:**

- Actual hierarchy: 88,441 rows · 9 sites · depth 4–5
- **Zero rows at depth ≥ 6** — the available leaf is Component/Maintainable Item, not Part
- Depth is **not homogeneous across sites** — measure by plant, never globally
- An Object Part more granular than the FLOC leaf **has no node on which to land**

In B1, internal joins can provide a partial structural route. In B2, it is pure lexical matching.

**Note:** the IH06 ↔ IEC crosswalk is coverage documentation, not a pipeline requirement. Low priority.

---

## Activity Type / MAT *(G05)* — Updated Status

```
B1   →  resolved by direct field. Out of ML
B2   →  no controlled OEM_ENTITY_001 source
        ZEUS maintenance_type as scaffold
        reconstruction marked expert_inference
```

**G05 is no longer blocked in the relational path.** It had been the project's most blocked target since STINT_0.

---

## Stratification — Rules

```
B1  →  explicit activityType, 100% coverage → stratify directly
B2  →  event_structural · NEVER planned/reactive
Path A → event_structural
```

- **Do not mix strata in the same denominator**
- Planned/reactive derivation by inference → `expert_inference`
- **B1 and B2 never share a denominator.** Different distributions, different natures

---

## Symptom — Status After Characterization

```
Path A        no observed symptom recorded
B1            no confirmed pre-execution field
B2            pending verification (B2.4)
```

**Two of three families confirmed without a source.** If B2.4 confirms the third, Symptom moves from *scarce* to **structurally unattainable** — because the corpus consists of order-like objects and status reports, and none records the reported symptom.

**That is a valid feasibility finding, not a failure.**

---

## Sequence

| Step | Path | Depends on |
|---|---|---|
| B1.1 deterministic harvest | B1 | F4.0b ✅ |
| B1.3 verify `reason` | B1 | — |
| B1.2 textual remainder | B1 | B1.1, B1.3 |
| B2.1 characterization | B2 | — |
| B2.4 EOD vs POD | B2 | B2.1 |
| B2.2 deduplication | B2 | B2.1 |
| B2.3 extraction | B2 | B2.2 |

**B1 and B2 can run in parallel.** B1.1 has the highest immediate return: it resolves MAT and evaluates Object Part without ML.

---

## Deliverables

```
b1_deterministic_harvest      structural evidence
b1_silver_labels              Cause · Damage · residual Activity
b2_snapshot_dedup             snapshot_rows vs estimated_events
b2_silver_labels              by target, with stratum
floc_leaf_candidates          by site, never global
reason_semantics_verdict      B1.3 resolution
eod_pod_comparison            B2.4 resolution
```

---

## Completion Criteria

By target and by path:

- Evidence declared with `evidence_type`, `tier`, `status`
- Declared route: deterministic, ML, or unattainable
- Stratum and `source_text_field` on every row
- Denominators separated by path, never aggregated
- `UNKNOWN` allowed and expected

**Declaring that a target is unattainable in a path is a valid result.**
