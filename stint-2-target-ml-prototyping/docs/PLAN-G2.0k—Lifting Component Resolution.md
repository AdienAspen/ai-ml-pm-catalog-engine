# G2.0k — Lifting Component Resolution

**FSA BRIDGE / STINT_2 · Two independent fixes, run together**
Estimated: 1 day

---

## Why this exists

Component resolution stands at 3,934 of 10,749 orders. The remaining 6,815 fall back to the turbine profile, where the answer space is coarse: 6 codes for Symptom, 13 for Cause, and Object Part collapses to 1.

**The unresolved set is a limitation of our method, not a property of the corpus.** Two fixes address it without touching the threshold, so neither can degrade precision.

```
G2.0k.1   token window segmentation      702 orders currently truncated
G2.0k.2   component vocabulary expansion  terms the blind sample revealed
```

⚠️ **Threshold lowering is deliberately excluded.** It is the only one of the three candidate fixes that trades precision for coverage, and it must be measured separately afterwards. Do not combine it with these two.

---

# G2.0k.1 — Token Window Segmentation

## The problem

`paraphrase-multilingual-MiniLM-L12-v2` processes 128 tokens — roughly 90 to 100 words. Everything beyond that is discarded before the vector is produced.

**702 B1 orders exceed the limit.** In this corpus the technician's closing note tends to sit at the end — `"replaced clogged converter air filters"` — while the opening repeats the alarm code. **We are likely truncating the segment that carries the component name.**

**Proportion that matters:** 702 of the 6,815 unresolved orders is 10%, not 7.6% of the corpus. All of them sit in the group we are trying to resolve.

## Task

```
1. Segment texts longer than 128 tokens into overlapping windows
   window size    ≤ 128 tokens
   overlap        ~20 tokens · so a phrase spanning a boundary
                  is not lost
2. Embed each window independently
3. Take the best score across windows for each concept
4. Record how many windows each order produced
```

**Do not change the threshold.** Same cut, same vocabulary — only the input is no longer truncated.

## Report

```
orders re-processed                     702
orders newly resolved to a component    ?
orders still unresolved                 ?
windows per order · min, median, max
position of the winning window          first · middle · last
```

⚠️ **The last line is the interesting one.** If the winning window is usually the last, it confirms that the component name sits at the end of the text — a finding worth recording for the whole pipeline, not just this step.

---

# G2.0k.2 — Component Vocabulary Expansion

## The problem

The component vocabulary was built in G2.0c and closed with 40 concepts after Step 3b. The `G1.1e` blind sample surfaced component names the vocabulary does not cover.

## Confirmed present in the corpus, absent from the vocabulary

From the 20-order blind review:

```
yaw ring · torque arm bushing · pitch manifold accumulator
hub safety pilot valve · deck hatches · lift guide arm
bottom cover · generator bearing DE/NonDE
smoke detector · M12 connector · MSC/LSC stack · PMG encoder
```

## Task

```
1. Add these terms as new concepts or as surface variants of
   existing ones, whichever the semantic grouping supports

2. Re-run component resolution over the 6,815 unresolved orders
   with the expanded vocabulary

3. Report which new concepts produced resolutions and how many
```

## Provenance — mandatory

```
construction_method    derived_from_corpus_inspection
                       NOT transcribed_from_source
source                 g11e_blind_sample
```

⚠️ **These terms come from reading annotated orders.** Keep them distinct from externally transcribed vocabulary, and exclude the 20 `G1.1e` orders from any later evaluation of Object Part.

⚠️ **Do not seed from G2.0 prototypes.** Those were analyst-authored and the original G2.0c instruction prohibited them as seeds. That prohibition stands.

---

## Combined reporting

Run both, then report the lift attributable to each:

```
                        resolved    unresolved
baseline                   3,934        6,815
after segmentation only        ?            ?
after vocabulary only          ?            ?
after both                     ?            ?
```

**Run each in isolation before running them together.** They are independent, and knowing which contributed what matters for deciding whether a third fix is warranted.

---

## What the lift buys

Every order that resolves to a component reads its own profile instead of the turbine profile:

```
turbine profile      Symptom 6 · Cause 13 · Object Part 1
component profile    the codes valid for that specific part
```

**And it removes ties.** Two near-identical codes tie only when both are candidates. Under a component profile one of them is frequently not enabled, so the tie never forms — without touching the model.

---

## Constraints

```
threshold frozen · unchanged from G2.0i
vocabulary changes logged with construction_method
no denominator change · no promotion · no F6 update
never aggregate across paths · this is B1 only
sanitised versioned outputs
```

---

## Closure criteria

- 702 truncated orders re-processed with windows
- Winning window position reported
- Expanded vocabulary applied with provenance recorded
- Lift reported per fix and combined
- Threshold unchanged and verified

---

## What this decides

Whether a third fix — threshold lowering with precision measurement — is warranted at all.

**If these two lift resolution substantially, the coarse-profile fallback shrinks and Symptom, Cause and Object Part all gain a better-delimited answer space.** If the lift is small, the remaining orders likely do not name their component in text, and that is the finding.

