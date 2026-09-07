# Phase 5 — Symptom *(G07)*
### Rewrite after F4

**FSA BRIDGE / AI-ML Workstream · STINT_1**

---

## What Changed

STINT_0 declared *"no current demonstrable proof-of-life"*. That status remains valid, but it is now **explained and bounded**.

**Three corpus families, three confirmations of absence:**

```
Path A · OEM_ENTITY_001 PDF     no initial report recorded
B1 · relational     no confirmed pre-execution field
B2 · OEM_ENTITY_001 snapshot    no initial-report field
```

**And the structural explanation, which we did not have before:**

> The corpus consists of order-like objects and status reports. Neither records the observed symptom. It was not lost — that object simply does not contain it.

This turns *"we did not find it"* into *"it cannot be there"*, which is a much more defensible claim.

---

## But Three Threads Remain Open

Against STINT_0's absolute zero, there are now three places with signal:

| Thread | Volume | Status |
|---|---|---|
| `reason` symptom-like *(B1.3)* | 921 rows | `possible_pre_execution_context_unconfirmed` |
| Lexical signal in B2.3/B2.5 | 365 events · **6 concepts** | `source_unconfirmed` |
| Vocabulary in the lexicon *(T8)* | 289 terms | unverified band |

**None confirmed. None ruled out.**

---

## F5.1 — Resolution of the Three Threads *(First)*

Before deriving anything, exhaust what already exists.

### F5.1a — The 6 B2 Concepts

**365 events across 6 concepts** is a high concentration. A handful of terms is driving nearly all the signal.

- List the 6 concepts and their frequency
- Are they observed conditions (`vibration`, `noise`, `overheating`) or generic terms?
- **If generic → noise, discard the thread**
- If they are conditions → blind manual review of 20 events

**This is the cheapest thread to resolve and the one with the highest concentration.**

### F5.1b — The 921 `reason` Records

**Blind** manual review — without showing the pipeline classification.

- Sample of 20 redacted rows
- Ask the reviewer: *does this describe something observed before the intervention, or the administrative reason for dispatch?*
- If it is the former → **`reason` would be the only pre-execution field in the corpus**

**Blind design is mandatory.** If the reviewer sees the proposal, it is `human_validated`, not `independent`.

### F5.1c — The 289 Lexicon Terms

Verify whether they survive in the high band or fell into the 64% discarded by F1.

---

## F5.2 — Inverse Derivation *(Only If F5.1 Does Not Resolve It)*

**Path A from the original plan, with cross-validation.**

### Method

```
Damage + Object Part + Activity
        ↓  documented domain rules
Plausible symptom
        ↓  cross-check against reference
ZEUS detection symptom categories
+ WMEP effects (8 terms)
        ↓  validity filter
Client Wind S catalog
        ↓
candidate · expert_inference · silver-medium maximum
```

### Non-Negotiable Rules

- **The cross-check filters; it never confirms.** A derived symptom being plausible and existing in the catalog does not make it observed
- **Maximum tier `silver-medium`.** Never `silver-high`, never `gold`
- **Always outside the contractual denominator**
- **Only on the reactive subset.** Planned maintenance has no symptom by definition
- **Never infer from Damage alone** — the F1 rule remains in force

### The 8 Available WMEP Effects

```
Overspeed · Overload · Noise · Vibration
Reduced power · Causing follow-up damage
Plant stoppage · Other consequences
```

**Sparse vocabulary.** Many derivations will fall to `UNKNOWN`, and that is correct.

---

## F5.3 — Prohibitions

⚠️ **Do not fill with a generic value** so that the canonical is not empty. This turns an honest gap into unauditable false data.

⚠️ **`Symptom ≈ Failure Effect type 6` remains a `hypothesis`.** Do not crystallize it without FSA configuration evidence.

⚠️ **Do not promote due to completeness pressure.** An empty target is a result.

---

## F5.4 — Possible Outcomes

All four are valid. **None is a failure.**

| Outcome | Condition |
|---|---|
| **A — Confirmed thread** | F5.1 validates `reason` or the 6 concepts → there is a real, though partial, source |
| **B — Bounded derivation** | F5.2 produces `expert_inference` candidates over the reactive subset |
| **C — Structurally unattainable** | F5.1 confirms nothing → declare it with evidence from all three families |
| **D — Mixed** | derivation where there is a basis, `UNKNOWN` where there is not |

**Outcome C would be the project's best-supported feasibility conclusion:** three independent sources, a structural explanation, and documented elimination of three threads.

---

## Deliverables

```
 f51_symptom_thread_resolution     the three threads, with verdict
 f52_symptom_derivation            candidates, if applicable
 f5_symptom_verdict                the declared outcome
```

---
