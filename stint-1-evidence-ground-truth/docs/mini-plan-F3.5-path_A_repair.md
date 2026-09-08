# Mini-Plan `F3.5` — Path A Repair

**F3 repair after PDF characterization**
Inserted between F3 and F4 · Estimate: 3–4 days

---

## Why It Exists

Manual inspection of 2 PDFs revealed that the F3 universe was poorly characterized:

- Structural parsing discarded the **NOTES** block, where maintenance semantics live
- Codes `156` and `155` match categories in the `ASSET STATUS` panel — **they may be status codes, not fault codes**
- The same event appears repeatedly in consecutive daily snapshots (T9: `112d 20h`)

F3 ran correctly over the wrong universe. This phase corrects the universe, not the method.

---

## T3.5.1 — Verification of the Status-Code Hypothesis

**The cheapest and highest-impact task.**

- Extract the `ASSET STATUS` panel categories from a PDF sample: `Tripped`, `Stopped`, `Impacted`, `Repair`, `Maintenance`, `No Comm.`, `Online`, `Available`
- Cross-check the 79 fault-code keys against the associated `Event` field value
- Classify each token: `state_code` · `fault_code` · `undetermined`

**Expected output:** partition of the 79. The `state_code` tokens **leave the Damage and Cause universe** — they do not describe faults.

**Deliverable:** `f35_faultcode_state_partition.csv`

⚠️ If a substantial portion turns out to be `state_code`, the 55/79 without an F3 candidate are explained, and the result should no longer be read as a matching failure.

---

## T3.5.2 — Re-Parsing with Docling

**Objective:** recover NOTES without returning to the parser that transposed columns.

- Evaluate Docling on a sample of 10 PDFs before running all 394
- Verify that it preserves both layers: `ASSETS OF CONCERN` table + `NOTES` prose
- Compare structural extraction against the current parser — it must not degrade

**New fields to capture:**
```
notes_text          free prose from the NOTES block
asset_status_panel  counts by category
planned_work        section (empty in the sample, verify)
site_roster         ⚠️ contains PII — do not version
```

**Deliverable:** `pdf_docling_reparse_v1` + comparison note with the previous parsing.

---

## T3.5.3 — Semantic Extraction from NOTES

The NOTES block has a recognizable structure:

```
[contractor] - [turbine] [component] [action]

"CONTRACTOR_ENTITY_001- T48 Yaw Limit switch"
"CONTRACTOR_ENTITY_003- T9 blade repair"
"CONTRACTOR_ENTITY_002- T30 & T33 annual maintenance"
"WTG 26 PCH and accumulator"
```

- Extract contractor, turbine reference, component, and action
- **Resolve the turbine reference** (`T48` → asset 48) to join with the concern table
- Anchor component and action against `LEXICAL_LAYER v2` (359 concepts)

**Important note:** NOTES references do not always match the assets in the table. In the 2025 sample, NOTES mentions T26 while the table lists 4, 45, 55. **They are complementary, not redundant, sources.**

**Deliverable:** `pdf_notes_extraction_v1` with per-row provenance.

---

## T3.5.4 — Snapshot Deduplication

**Objective:** establish how many real events are behind the 602 rows.

- Group by `asset + fault_code + duration window`
- An event with increasing duration on consecutive dates is **one event**, not N
- Produce two counts: `filas_snapshot` and `eventos_estimados`

**Rule:** the Path A denominator uses `eventos_estimados`. Snapshot rows remain observations of the same event.

**Deliverable:** `pdf_event_deduplication_v1` + both counts declared.

---

## T3.5.5 — Re-Run the Crosswalk

With the corrected universe:

- Only tokens classified as `fault_code` enter matching against Damage/Cause
- `state_code` tokens are routed to **Activity Type**, where they have semantic meaning
- NOTES provides new signal for **Object Part** and **Activity**

**Deliverable:** `ge_fault_code_crosswalk_v2`, replacing the F3 version.

---

## Completion Criteria

- All 79 tokens classified by nature, with evidence
- NOTES extracted and anchored, with provenance
- Both Path A counts declared: rows versus events
- Crosswalk v2 issued, with `expert_inference` and tier per row
- PII in the site roster identified and excluded from versioned artifacts

**Nothing is promoted to measurement-ready.**

---

## Risks

| Risk | Mitigation |
|---|---|
| Docling degrades structural extraction | evaluate on 10 before the 394 |
| NOTES does not join to the table due to a missing key | treat them as separate sources, do not force a join |
| Deduplication collapses distinct legitimate events | duration window, not only asset+code |
| PII leaks into versioned artifacts | explicit exclusion during parsing |

---
