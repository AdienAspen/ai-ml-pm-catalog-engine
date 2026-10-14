# C1–C4 — Closure Bookkeeping

**FSA BRIDGE / STINT_2 · POC closure · report and register only**
Estimated: one day

---

## Why this exists

The POC is closing. The status table is updated with the component line (G2.0k), the profile-constrained crosswalk (G1.1f) and the Symptom/Cause signal volumes. Before documentation starts, every figure the documentation will cite must be registered, traceable to a file, and labelled with its unit, evidence level and condition.

This step creates no new results. It registers, reconciles and closes.

```
C1   F6 final update            denominators per target × path × level
C2   G0.4b                      register evaluation_set_v2
C3   leakage rows               validate the 13 extracted rows
C4   closure manifest           index of artefacts for documentation
```

---

## 0 · Pre-flight — confirm before writing anything

State each item as `confirmed` or `differs`, with file and field. **If any item differs, stop and report.**

```
K1  every figure listed in C1 exists in a persisted output and
    reproduces exactly · cite the file per figure
K2  g01-v2 responses for Damage and Activity (v2.1, A3 rewrite) are
    persisted for both annotators, with overlap keys
K3  the 13 leakage rows and their extracted values are persisted in
    internal/
K4  evaluation_set_v1 training-exclusion keys are persisted (900)
```

No rerun. No rescoring. No threshold or vocabulary change.

---

## C1 · F6 final update

**One row per target × path × level.** Never aggregate across paths or levels.

### Required columns

```
target · path · level (turbine | component | n/a)
unit (order | event | estimated_event_key | pair)
figure · source file
evidence level (structural | annotated agreement | semantic candidate
                | provisional grouping)
layer (deterministic | ML-addressable | operator decision |
       data preparation)
conditions (precision not validated · 128-token limit · contingent
            on episode reconstruction · as applicable)
```

### Rows to include, B1

```
MAT                  10,749 · direct field · deterministic
FLOC turbine         10,699 · join · deterministic · 50 out of scope
Object Part turbine  1 enabled code under PMMUWW · deterministic
Object Part text     7,668 · corpus vocabulary · κ 0.671
Object Part crosswalk, component level
                     as built: 3,013 orders · 5,778 pairs
                     profile-constrained: valid candidate under the
                     turbine, by category (G1.1f) · state the total
Component profile    3,935 resolved (2,400 unique node · 1,535 consensus)
                     6,814 unresolved by first failing link (G2.0k.3)
Activity             7,606 · corpus vocabulary · κ 0.893 (v2.1)
                     39/75 overlap units: work described, no code
Damage               3,078 · external vocabulary · κ 0.60 / 0.61
Symptom              G2.0d2: 104 · G2.0j anchored: 106 split 14 / 86 / 6
Cause                G2.0d2: 289 · G2.0j anchored: 135 split 14 / 104 / 17
```

⚠️ **Symptom and Cause:** report G2.0d2 and G2.0j side by side. Same 9,263 orders, different presence prototypes · never subtract one from the other.

### Rows to include, Path A and B2

```
per target, as frozen in F6 · unit as frozen
condition on every row: contingent on episode reconstruction
compression observed: A 1.66× · B2 1.07× with date, 4.32× without
```

### Separation kept from the previous F6

```
contractual denominator    MAT only
POC proxy denominators     all other rows
```

**Assertions:** each row has exactly one unit and one source file · no row mixes paths or levels.

---

## C2 · G0.4b · register evaluation_set_v2

Register as a new artefact. **Do not modify or merge with evaluation_set_v1.**

```
targets          Damage · Activity
protocol         g01-v2 · Activity under v2.1 (A3 rewrite) · state it
annotators       two, different model families · as recorded
per target       responses annotator 01 and 02 · overlap keys
agreement        raw · Cohen's κ · Gwet's AC1 · per class · confusion
                 matrix · Damage at group and at group+code
registration     evaluation_independence      independent
                 label_generation_method      blind_llm_annotation
                 evaluation_role              diagnostic
                 eligible_for_final_heldout   false
                 reason                       drawn from a pool that
                                              built vocabulary or
                                              thresholds · state per
                                              target
exclusion keys   v2 keys · union with v1 keys · assert counts
limitations      file, as for v1
```

**Formal closure records:** confirm that g01-v2, G2.0e and G2.0f each have a closure memo. If one is missing, write it from existing outputs, short: question, protocol, agreement, reading, status.

---

## C3 · Leakage rows

13 rows is small enough for full review, not a sample.

```
for each row     extracted value matches the text · yes | no
status           validated | rejected · per row
result           close pending_sample_validation
```

Review text stays in `internal/`. The versioned output carries row identifiers and status only.

---

## C4 · Closure manifest

One file listing every artefact the documentation will cite.

```
per entry   step code · one-line purpose · memo path · sanitised
            tables · internal/ files (path only) · status
scope       STINT_1 phases cited by F6 · STINT_2 G0, G1, G2.0 to
            G2.0k, G1.1f · the chain specification
```

The documentation will cite figures only through this manifest.

---

## Handling of content

```
versioned, sanitised    counts · agreement · unit · status · safe IDs
internal/, 600          any text, descriptions, node identifiers
```

---

## Deliverables

```
f6_final_denominators_sanitized.csv
f6_final_memo.md
evaluation_set_v2/ · same structure as v1
evaluation_set_v2_registration_summary.json
g20b_leakage_validation_sanitized.csv
stint2_closure_manifest.md
```

---

## Constraints

```
no rerun · no new measurement · no promotion
no aggregation across paths or levels
commit and push only on the lead's instruction
```

---

## Closure criteria

- K1 to K4 confirmed with references
- C1: every row with unit, source, evidence level, layer, conditions
- C2: v2 registered separately · exclusion keys asserted · closure memos present
- C3: 13 rows with status · pending_sample_validation closed
- C4: manifest covers every figure in the status table
