# Micro-Plan `F5.1b2` — Quantifying Symptom in `reason`

**FSA BRIDGE / AI-ML Workstream · STINT_1 · Phase 5**
Estimate: half a day

---

## Why This Step

The blind review of 20 `reason` rows returned 18 observed conditions, 2 ambiguous cases, and **zero administrative reasons** — contrary to the B1.3 expectation. The texts contain an OEM alarm code, technical description, and measured-value placeholder, meaning information recorded **before** the intervention.

This contradicts the three-week conclusion that Symptom does not exist in the corpus. Before revisiting any verdict, we need to know **how much** signal there is: the sample came from 921 rows preselected by cue, not from the 10,338 rows with populated `reason`.

---

## T5.1b2.1 — Expand the Blind Review

- New sample of **40 rows**, this time from the complete non-empty `reason` universe, **without cue-based preselection**
- Same blind design: text visible to the reviewer, PII redacted, no pipeline proposal, no semantic flags
- Same single question and same four permitted responses

**Why it matters:** the previous 20 came from a biased subset. This sample estimates the actual rate across the complete field.

**Deliverable:** `f51b2_reason_blind_review_unbiased.csv` with recorded responses.

---

## T5.1b2.2 — Automatic Alarm Pattern Detection

The texts show a recognizable structure:

```
[numeric code] [separator] [condition description] [measured-value placeholder]

5142-WaterLevelLow
165-LowOilLevelHydraulic
6846-High temp.Gear bearing _:___°C
VTM 14211: Main Bear Temp High 4MW MK3
2981 MainBearLubrResLevelLow
```

- Detect this pattern across the **10,338 rows** with populated `reason`
- Report how many fully match it, how many partially match it, and how many do not
- **Do not classify yet** — only count and profile

**Deliverable:** `f51b2_alarm_pattern_coverage.csv` with coverage rate over the actual universe.

---

## T5.1b2.3 — OEM Alarm Code Dictionary ⭐

**The side finding, and possibly the highest-value one.**

Track 4 concluded that no public catalogs of CONTRACTOR_PATH_001 or OEM_ENTITY_001 fault codes exist. Here, a **de facto dictionary** can be built from the corpus itself.

- Extract `code → description` pairs from all rows matching the pattern
- Deduplicate by code; report how many distinct descriptions each has
- Count unique codes and their frequency
- **Do not map to SAP yet** — only build the dictionary

**Deliverable:** `f51b2_oem_alarm_dictionary_sanitized.csv`

**Provenance:** `evidence_type: real_observed_label` for the code-description pair exactly as it appears in the source. Mapping to an SAP catalog, when it occurs, will be `expert_inference` and handled separately.

---

## T5.1b2.4 — Check the Other Path

With the pattern identified, search for the same structure in:

- Path A · NOTES field and concern table
- B2 · workbooks OEM_ENTITY_001

**Question:** is it exclusive to the relational path, or does it also exist in OEM_ENTITY_001 and the pipeline was not looking for it?

**Deliverable:** section in the memo with a verdict by path.

---

## T5.1b2.5 — Revised Symptom Verdict

Consolidate and declare by path:

| Path | Symptom source | Coverage | Status |
|---|---|---|---|
| B1 relational | `reason` | ? | ? |
| Path A | ? | ? | ? |
| B2 OEM_ENTITY_001 | ? | ? | ? |

**Update the target status.** If confirmed, Symptom is no longer *structurally unattainable* and becomes *present in the relational path*.

---

## Constraints

- **Review in a closed environment.** The text does not leave it; only responses keyed by `reason_hash` leave
- **Record the reviewer:** `human_blind_review` or `model_blind_review` as applicable. The initial 20 rows were reviewed by a model, not a human — the record must reflect this
- No raw operational values in versioned artifacts
- **Do not promote to a denominator** until quantification is complete
- No mapping to an SAP catalog in this pass

---

## Completion Criteria

- Observed-condition rate over the unbiased sample
- Alarm-pattern coverage over the 10,338 rows
- OEM code dictionary with unique-code count
- Documented verdict by path
- Symptom status updated with evidence

---

## What It Unlocks

- **Symptom** may have its own denominator in the relational path
- **The OEM dictionary** closes the gap that Track 4 declared irresolvable through public sources
- **F5.2** —assisted derivation— could be limited to the OEM_ENTITY_001 paths, or become unnecessary if coverage is high
