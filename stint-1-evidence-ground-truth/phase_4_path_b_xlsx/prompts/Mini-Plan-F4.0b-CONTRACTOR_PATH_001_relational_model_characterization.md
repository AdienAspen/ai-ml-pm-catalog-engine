# Mini-Plan `F4.0b` — CONTRACTOR_PATH_001 Relational Model Characterization

**FSA BRIDGE / AI-ML Workstream · STINT_1 · F4 prerequisite**
Estimate: 1 day · Executor: characterization sub-agent, within the project perimeter

---

## 1. Why It Exists

F4.0 characterized four XLSX files and concluded that the sampled families behave like daily/status workbooks. That conclusion is valid for the sampled snapshot/EOD-like families, but not sufficient for CONTRACTOR_PATH_001, which is the family F4 needs to process.

**CONTRACTOR_PATH_001 was left out of the sample.** And CONTRACTOR_PATH_001 is the family that F4 will actually process.

Evidence that the sampled universe was not the correct one:

| Indicator | F4.0 reported | Contradiction |
|---|---|---|
| Columns per file | 4–5 | a daily maintenance report has dozens |
| `planned/reactive` candidates | 0 | T8a established `activityType` with 100% coverage |
| Language-classifiable text | 1 of 11 | technical prose should be identified as ES or EN |
| Estimated volume | ~3,500 rows | `CONTRACTOR_PATH_001` reports 10,749 records |

---

## 2. The Finding That Changes the Nature of the Task

Visual inspection of the CONTRACTOR_PATH_001 directory revealed that **it is not a file export; it is an API dump**:

```
api_common_v1_assets          .json  .xlsx  .xml
api_common_v1_contracts       .json  .xlsx  .xml
api_common_v1_customers       .json  .xlsx  .xml
api_common_v1_sites           .json  .xlsx  .xml
api_service_v1_service-orders              .json  .xlsx  .xml
api_service_v1_service-orders-consumption  .json  .xlsx  .xml
api_service_v1_service-visits              .json  .xlsx  .xml
```

Pattern `{namespace}_{version}_{resource}` — the signature of REST endpoints, not folders.

**Two domains:**

```
 api_common    master data      what exists   assets · sites · customers · contracts
 api_service   transactional    what happened service-orders · service-visits · consumption
```

**Immediate consequences:**

- It is a **relational model**, not a collection of spreadsheets. Entities are joined by foreign keys
- Profiling file by file loses most of the value: the graph must be mapped
- **The three formats are redundant** — same content, three serializations. If the pipeline counted files, it inflated the universe 3x
- `service-orders` is semantically **an order (PM00)**, not a notification (MH)
- `consumption` lists consumed materials — structured evidence of **Object Part** without requiring NLP
- Because they are atomic records, **CONTRACTOR_PATH_001 does not have the snapshot deduplication problem** seen in snapshot/POD-EOD style families

---

## 3. Objective

Establish which part of the mapping to SAP catalogs can be resolved by **joins and deterministic rules**, and which remainder genuinely requires ML.

**Out of scope:** extracting evidence, producing candidates, building parsers, or issuing mappings.

---

## 4. Tasks

### T4.0b.1 — Entity Inventory

- List the entities present in the CONTRACTOR_PATH_001 directory and their record volumes
- Confirm redundancy between `.json`, `.xlsx`, `.xml` — same content or not
- Recommend a canonical format for the pipeline (JSON preferred for typing)
- Verify whether additional entities are not visible in the initial snapshot

**Deliverable:** `f40b_contractor_path_001_entity_inventory.csv`

---

### T4.0b.2 — Transactional Entity Profile ⭐

Priority: `service-orders`, `service-visits`, `service-orders-consumption`.

For each entity:

- Fields, types, null rate
- Field classification: identifier · code · free text · date · metadata · foreign key
- For text fields: length distribution, language, three short redacted examples
- **Locate `activityType` and `description_extended`** — T8a reported them with 100% and 96.2% coverage

**Deliverable:** `f40b_contractor_path_001_transactional_profile_sanitized.csv`

---

### T4.0b.3 — Key Graph

Map the relationships between the seven entities:

```
service-orders      → assets?  sites?  customers?  contracts?
service-visits      → service-orders?
consumption         → service-orders?  materiales?
assets              → sites?
```

For each candidate relationship: source field, target field, estimated cardinality, match rate.

**Deliverable:** `f40b_contractor_path_001_key_graph.md` with an entity-relationship diagram.

---

### T4.0b.4 — Evaluation of `consumption` as an Object Part Signal

- Which fields does it contain? Material code, description, quantity?
- Do the materials have an associated catalog or vocabulary?
- How many orders have associated consumption? Coverage rate
- **Is it feasible to map material → catalog B by rule, without NLP?**

**Deliverable:** section within the memo, with an explicit verdict.

---

### T4.0b.5 — Deterministic / ML Boundary

Based on the above, classify each target:

| Target | Resolvable by join/rule | Requires ML | Rationale |
|---|---|---|---|
| Object Part | ? | ? | Does `consumption` suffice? |
| Activity | ? | ? | Does `activityType` suffice? |
| Activity Type / MAT | ? | ? | confirmed direct field |
| FLOC leaf | ? | ? | `assets` → hierarchy? |
| Damage | ? | ? | does a dedicated field exist? |
| Cause | ? | ? | does a dedicated field exist? |
| Symptom | ? | ? | does any initial-report field exist? |

**This is the highest-value deliverable of the pass.** It defines the actual scope of ML work in CONTRACTOR_PATH_001.

---

### T4.0b.6 — Pending Verification: Nature of the Object

Recorded as an open project question:

> **Are all EOD/PODs status objects, or does any EOD record the initial problem report?**

For CONTRACTOR_PATH_001, the equivalent question is:

> **Does any entity or field capture the reported symptom before the work is performed?**

If the answer is no for both families, **Symptom is not scarce: it is structurally unattainable**, because the corpus consists of order-like objects and status reports, and none records the observed symptom.

That would be a feasibility finding, not a failure.

**Deliverable:** explicit yes/no answer with evidence, in the memo.

---

## 5. Execution Conditions

**Perimeter and sensitivity**

- Run within the project. Data must not leave it
- No raw operational values in reasoning, logs, or report
- Text examples: maximum 3 per field, maximum 12 words, PII redacted
- PII: report location (entity and field), never values

**Budget**

```
Profiled entities            up to 7
Fields per entity             up to 60
Sampled records               up to 30 per entity
Text examples                 3 per field, 12 words
```

Exceeding a limit means **sample and mark `truncated`**, never read more.

**Reading method**

- Prefer JSON with incremental reading rather than loading complete XLSX files
- For XLSX: `openpyxl` with `read_only=True`, iterating by row
- Do not rely on `pandas.read_excel(nrows=N)` to limit actual cost
- Ignore embedded objects except for yes/no presence
- Abort an entity if it exceeds ~2 minutes, mark `read_incomplete`, continue

**Rule inherited from F3.5 — mandatory**

> No zero is interpreted until the extractor has been validated against a known positive case.

Before running, the team must provide the agent **two or three verified markers**: a field known to exist and a text value known to be present. Without a positive case, a zero is not interpretable.

**Prohibitions**

- Do not build parsers or extraction code
- Do not produce candidates, crosswalks, or mappings
- Do not extrapolate from the sample to the full corpus
- Do not unify formats or normalize field names

---

## 6. Output — Memo Under One Page

```
WHAT CONTRACTOR_PATH_001 IS
  One paragraph. The nature of the data model.

ENTITY INVENTORY
  Compact table: entity · records · formats · role.

KEY GRAPH
  Confirmed relationships and their match rates.

WHERE THE SIGNAL IS
  Which fields carry usable semantics and which do not.

DETERMINISTIC vs ML FRONTIER
  The completed T4.0b.5 table.

SYMPTOM VERDICT
  Answer to T4.0b.6, with evidence.

RED FLAGS
  PII · format redundancy · status fields
  disguised as descriptions · keys that do not close.

COVERAGE NOTE
  What was read, what was omitted, and what was truncated.
```

---

## 7. Completion Criteria

- Entity inventory with actual volumes
- Documented key graph
- Deterministic/ML boundary declared per target
- Verdict on `consumption` as an Object Part source
- Answer to the Symptom question
- Recommended canonical format
- **Confirmation of whether `CONTRACTOR_PATH_001` corresponds to CONTRACTOR_PATH_001**

---

## 8. What It Unlocks

Once `F4.0b` is complete, Phase 4 of the technical plan can be rewritten based on reality:

- **Two separate pipelines**, not one: relational CONTRACTOR_PATH_001 · snapshot/POD-EOD style family
- ML scope limited to the genuine textual remainder
- Denominators by family, never mixed
- Informed decision about which targets are achievable in each path

**Without this, F4 would start from assumptions we already know to be incorrect.**
