# Technical Plan v2 — `STINT_1.1-reference-layer`

**FSA BRIDGE / AI-ML Workstream · Consolidation sub-stint**
*Incorporates the five clarifications from Chapter #2*

---

## Framing

> **STINT_1.1 does not create ground truth. It builds the semantic and reference layer that will allow STINT_1 to reconstruct ground truth without inventing it.**

---

## Objective

Convert scattered research findings into a **single, versioned, code-consumable artifact**.

**Out of scope:** training models, generating labels, running the pipeline over the corpus, or closing denominators. That is STINT_1.

**Operational distinction:** 1.1 **specifies** the pipeline; STINT_1 **runs** it. Deliberate exception: T8 touches ~500 real records to calibrate the artifact against the actual corpus.

---

## Guiding Principle — Cost/Benefit

- The normative reference **validates and names**; it never dictates
- If a real record does not fit the standard, the finding concerns the data
- **Timebox each task**, not "until it is perfect"
- **Reuse before building** — MaintIE, Malyi, and WMEP already exist
- Prefer **broad coverage with honest `UNKNOWN`** over narrow precision

---

## Governance *(Non-Negotiable)*

- **Granular per-row provenance** — `evidence_type` and `tier` are independent axes. Never a global label
- **Canonical frozen** — `v1.8-baseline-frozen`. Divergence documented, never silently overwritten
- **No-ingest rule** — loose alarm lists, author codes, Kaggle re-uploads, and community dictionaries: excluded
- **No performance claims** — not applicable in this sub-stint

---

## Provenance Schema — Mandatory for Every Entry

```
concept_id        stable identifier, referenceable by code
source            exact source
source_version    document edition / version
source_date       publication or review date
evidence_type     origin: real_observed_label · validated_mapping ·
                  reference_evidence · expert_inference ·
                  external_corroboration · unknown
tier              confidence: gold · silver-high · silver-medium · unresolved
status            resolved · hypothesis · pending
notes             observations
```

**Critical rule:** `evidence_type` answers *where it comes from*. `tier` answers *how much we trust it*. They are never collapsed.

---

## Deliverable Structure

```
CANONICAL_TAXONOMY      → turbine functional hierarchy
SOURCE_DESIGNATIONS     → RDS-PP, KKS, IEC nodes
LEXICAL_LAYER           → how the technician writes
SEMANTIC_NORMALISATION  → conversion rules (pipeline specification)
SAP_MAPPING             → SAP catalogs and types
```

**Rule separating them — six non-collapsible namespaces:**

```
IEC id ≠ RDS-PP ≠ ISO ≠ FLOC ≠ EQUNR ≠ technician term
```

---

## Tasks

### T1 — Repo Bootstrap *(0.5 day)*

```
stint-1.1-reference-layer/
├── reference_layer/
│   ├── canonical_taxonomy/
│   ├── source_designations/
│   ├── lexical_layer/
│   ├── semantic_normalisation/
│   └── sap_mapping/
├── external/
│   ├── maintie/
│   └── malyi/
├── scripts/
├── outputs/
└── docs/
    ├── provenance-schema.md
    ├── canonical-delta-log.md
    ├── no-ingest-policy.md
    └── concept-id-registry.md
```

**Deliverable:** branch, skeleton, and `provenance-schema.md` with mandatory fields including `concept_id`.

---

### T2 — External Ingestion *(1 day)*

- Clone the Malyi repo — `used_taxonomy.md`, `technical_report.md`, prompts, schemas
- Download MaintIE — corpus, annotation schema, preprocessing pipeline
- Record licenses and restrictions

**Deliverable:** populated `external/` + license note.
**Do not:** use Malyi's `input_dataset.csv` — it is a dummy sample.

---

### T3 — Malyi Schema Delta ⭐ *(1 day)*

Compare Malyi's input schema against our canonical matrix.

```
Malyi:     WO_ID · Descriptions · System_Code · System_Name · Maintenance_Type
Ours:      [fields from canonical v1.8]
```

**Chapter #2 adjustment:** a match is recorded as `external_corroboration`, **not** as validation of our architecture. Malyi reinforces the design; it does not prove that the canonical is correct for FSA BRIDGE.

- Match → `external_corroboration`, tier `silver-high`
- Divergence → entry in `canonical-delta-log` with justification

**Deliverable:** `malyi_schema_delta.md`.

---

### T4 — Canonical vs SAP Reconciliation *(1.5 days)*

Align the matrix against the SAP types confirmed by Track 3.

**Points to resolve:**

- **Symptom / Catalog S ≈ Failure Effect type 6** → ⚠️ record with `status: hypothesis`, **never `resolved`**, until evidence from the catalog or actual FSA configuration is found. This is the highest-risk point for structural semantic error in the sub-stint
- **Damage (C) = physical process, not observation** — correct the extractor's operational definition
- Anchor B, 5, and A to their official SAP definitions

**Rule:** do not overwrite the canonical with the standard. Document the gap.

**Deliverable:** `canonical_reconciliation_v1.md` + entries in `canonical-delta-log`.

---

### T5 — ZEUS Semantic Scaffold *(2 days)*

Build the semantic scaffold without acquiring the standard.

**From the public preview — the categories:**
`detection symptom` · `failure mode` · `failure cause` · `failure process` · `maintenance measure` · `maintenance type`

**Populate them with differentiated per-row provenance:**

| Content | `evidence_type` | Source |
|---|---|---|
| WMEP causes and effects | `reference_evidence` | WMEP, ~64k incidents |
| Multiplier failure modes | `reference_evidence` | NREL GRD |
| Dictionary structure by system | `reference_evidence` | Malyi |
| **The relationship between those concepts and ZEUS/SAP** | **`expert_inference`** | own construction |

**Chapter #2 adjustment:** provenance remains granular. **Do not mark the entire scaffold as `expert_inference`** — only the mapping we build ourselves.

⚠️ **Critical point:** ZEUS `failure mode` does **not map 1:1** to SAP `Damage`. Document this explicitly.

**Deliverable:** `zeus_semantic_scaffold.md` — first structural support for MAT.

---

### T6 — FLOC Coverage Crosscheck *(1.5 days)*

Cross-check the **actual IH06** against the external reference.

- Extract IH06 structure by plant: levels, depth, nodes
- Compare against the 21 logical IEC nodes
- Map to ISO 14224 levels (Section/System, Equipment Unit, Subunit, Component, Part)
- **Measure by site, not globally**

**Questions to answer:**
- Which IEC systems do not appear in IH06?
- Where is IH06 deeper than the standard?
- Is depth consistent across plants?

**Deliverable:** `floc_coverage_crosscheck.md` + table by plant.

---

### T7 — KKS Presence Check *(0.5 day)*

Grep the local repo for inherited designations.

- RDS-PP patterns: `=M**`, `=U**`, `MDA`, `MDK`, `MDL`, `MKA`, `MSE`, `MST`, `MUD`
- Classic KKS patterns
- **Remember:** normative letters, project-specific numbers. Do not parse the numeric portion of an external KKS

**Deliverable:** `kks_presence_check.md` — yes/no with evidence.

---

### T8 — Seed Lexical Dictionary ⭐ *(3 days)*

**The task that connects the structure to how the FSA corpus is written.**

**Stratified sampling — Chapter #2 adjustment:**

```
~500 records, stratified by:
  ├── contractor / site
  ├── planned vs reactive          ← critical
  └── maintenance type
```

Mixing planned and corrective work particularly contaminates Symptom and Cause. Stratification is a requirement, not a preference.

**Work:**

- Extract observed terms: components, actions, faults
- Build `observed_term → normalised_term → canonical_concept`, each with its `concept_id`
- Start from the ~40 research variants, **correcting `Umrichter`** (it is a converter, not a generator)
- Explicitly cover ES / EN / mixed

**Specify the 5-step normalization pipeline:**
```
mask tags → clean → expand abbreviations
→ correct spelling → NER
```

**Adopted decision:** do not pre-translate. Multilingual backbone + bilingual canonical dictionaries.

**Deliverable:** `lexical_seed_dictionary_v1.csv` + `normalisation_pipeline_spec.md`.

---

### T9 — Consolidation and Freeze *(1 day)*

- Assemble the five objects
- **Verify that every entry has:** `concept_id`, `source`, `source_version`, `source_date`, `evidence_type`, `tier`, `status`
- Populate `concept-id-registry.md` — without stable IDs, STINT_1 would reference by text and reintroduce ambiguity
- Remove rejected sources: `studylib.net`, Scribd, ResearchGate as primary sources
- Clean URLs with `utm_source=chatgpt.com`
- Freeze as `reference-layer-v1`

**Deliverable:** versioned `reference-layer-v1` + usage `README`.

---

## Sequence and Dependencies

| Task | Duration | Depends on | Parallelizable |
|---|---|---|---|
| T1 Bootstrap | 0.5 d | — | — |
| T2 External ingestion | 1 d | T1 | ✅ |
| T3 Malyi delta ⭐ | 1 d | T2 | — |
| T4 SAP reconciliation | 1.5 d | T1 | ✅ |
| T5 ZEUS scaffold | 2 d | T2, T4 | — |
| T6 FLOC crosscheck | 1.5 d | T1 | ✅ |
| T7 KKS check | 0.5 d | T1 | ✅ |
| T8 Lexical dictionary ⭐ | 3 d | T2 | ✅ |
| T9 Consolidation | 1 d | all | — |

**Critical path:** T1 → T2 → T5 → T9
**Estimate:** 6–8 days with parallelization · 12 sequential days

---

## Completion Criteria

- `reference-layer-v1` exists, versioned, with all five objects populated
- Every entry has `concept_id`, complete provenance, and declared tier
- The `canonical-delta-log` records every detected divergence
- `Symptom ≈ Failure Effect` is recorded as a **hypothesis**, not an equivalence
- The seed dictionary covers ≥500 stratified records
- A documented yes/no answer exists regarding KKS presence in the corpus

**Not required for closure:** reference-layer completeness, total vocabulary coverage, or resolution of STINT_1 gaps.

---

## Risks

- **Over-engineering** → strict timebox, sufficiency criterion per task
- **Provenance contamination** → `evidence_type` and `tier` on separate axes, verification in T9
- **Structural semantic error in Symptom** → `status: hypothesis` mandatory until FSA evidence
- **Text-based references in STINT_1** → stable `concept_id` from T1
- **Reintroduction of rejected sources** → explicit `no-ingest-policy.md` from the start