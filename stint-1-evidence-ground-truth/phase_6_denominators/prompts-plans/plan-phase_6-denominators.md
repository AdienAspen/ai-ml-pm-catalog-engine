# Phase 6 — Denominators *(G01)*
### Rewrite after F4

---

## Nature

**This is not a production task. It is consolidation.** F6 does not generate evidence — it organizes and declares it.

---

## The Two Denominators

```
┌──────────────────────────────────────────────────────┐
│  CONTRACTUAL                                         │
│  evidence_type ∈ {real_observed_label,               │
│                   validated_mapping}                 │
│  tier   = gold                                       │
│  status = resolved                                   │
│                                                      │
│  Only known candidate:                               │
│    MAT in B1 — 10,749 direct observed labels         │
│                                                      │
│  Expectation: zero for all other targets             │
└──────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────┐
│  PROXY POC                                           │
│  allows qualified silver-high · silver-medium        │
│  allows expert_inference with complete provenance    │
│                                                      │
│  ALWAYS reported as a proxy evaluation set           │
│  NEVER as verified production accuracy                │
└──────────────────────────────────────────────────────┘
```

---

## Counting Unit — Per Path

```
Path A   →  estimated_event × target
B1       →  physical_record_id × target
B2       →  estimated_event_key_with_snapshot_date × target
```

**Evidence rows are never the denominator.** A record with three converging pieces of evidence counts once.

---

## Segmentation Rule

```
Path A  ·  B1  ·  B2     →  separate denominators, never aggregated
```

They are three distinct natures: OEM_ENTITY_001 snapshot, relational, OEM_ENTITY_001 workbook snapshot. **A global denominator would be methodologically invalid.**

**And within each path:** declared stratum. `event_structural` never with `planned/reactive`.

---

## Requirements for Including `expert_inference` in the Proxy

All five are mandatory:

- Stable and resolvable `concept_id`
- Documented and reproducible derivation rule
- Declared source from which it is derived
- Valid canonical destination in `canonical-constraints.md`
- Tier assigned using explicit criteria

**If any is missing → `unresolved`.**

---

## Circularity Control

Everything produced in F4 carries `evaluation_independence: derived_from_rules`.

**Consequence for STINT_2, which must be written down:**

> The held-out proxy can only be built with records marked `independent`, or by explicitly excluding the rule set and embedding model that generated the labels.

**Available `independent` material today: none.** The 30 rows from F1e2 were reclassified as `human_validated` — the reviewer saw the proposal.

**If F5.1 performs a blind review, those rows would be the project's first genuinely independent records.**

---

## Reporting Structure

```
target × denominator_type × evidence_type × tier
      × path × site × stratum  →  N
```

`denominator_type` is a mandatory column. **A report without it is invalid.**

---

## Expected Status by Target

| Target | Path A | B1 | B2 |
|---|---|---|---|
| **Activity Type / MAT** | expert_inference | ⭐ **observed** | no source |
| **Object Part** | candidate | partial structural | 488 events |
| **Activity** | 381 candidates | partial + textual | 74 events |
| **Damage** | 120 candidates | textual, with caution | 110 events |
| **Cause** | 36 candidates | `reason`, unconfirmed | 57 events |
| **FLOC leaf** | — | joins, SAP alignment missing | — |
| **Symptom** | absent | `reason` unconfirmed | 365 unconfirmed |

**Everything except MAT remains `requires review`.**

---

## STINT_1 Completion Criteria

For each of the 7 targets:

- Contractual denominator declared — even if zero
- Proxy denominator declared — even if zero
- `evidence_type` and `tier` supporting each one
- Provenance documented per record
- Declared route: deterministic · ML · unattainable
- Segmentation by path and stratum
- Method recommendation justified by the actual evidence

**Declaring that a target lacks sufficient evidence is a valid and expected result.**

---

## Mandatory Scope Statements

Two things must be written in the final report:

- **Grouping simulates SyncHub behavior.** It was run because there is no denominator without constituted events. It is not an ML workstream deliverable
- **Every metric is measured against the proxy evaluation set.** Never as verified accuracy. The contractual 95% does not apply to the POC

---
