# G2.0k.3 — Resolution Chain Partition

**FSA BRIDGE / STINT_2 · Diagnostic only · B1 only**
Estimated: half a day

---

## Why this exists

`G2.0k.2` established that text detection is not the binding constraint:

```
unresolved orders with a new component term detected    459
new profiles resolved                                      1
baseline → after G2.0k.2                     3,934 → 3,935
```

The text names a component in hundreds of orders, and the chain still does not reach a node. **The limiting step sits after detection, in the link from concept to IH06 node.**

This step locates, for every unresolved order, **the exact link where the frozen `G2.0i` chain stops**. It replays the chain; it does not change it.

`G2.0k.1` is closed as not applicable: the `G2.0i` detector matches phrases over the full text, so the 128-token limit does not act on component resolution.

---

## Objective

Assign each of the **6,814 unresolved B1 orders** to exactly one category, based on the first link of the chain that fails.

**Out of scope:** changing threshold or margin, adding vocabulary, new detectors, promotion, F6 updates.

---

## The chain being instrumented

```
order
 └─ 1  join to turbine node          assetId + site → IH06
     └─ 2  component concept in text     frozen phrase detector
         └─ 3  concept → profiled IH06 node MiniLM label vs description
                                         threshold 0.60 · margin 0.05
```

Run the frozen `G2.0i` chain, with the `G2.0k.2` vocabulary as registered, and **log the outcome of every link for every order**. No link is re-parameterised.

---

## Categories — mutually exclusive, exhaustive

```
no_turbine_node          link 1 fails · order does not join an IH06
                         turbine node

no_component_concept     link 2 fails · no component concept detected
                         in the order text

no_profiled_component_candidate
                         link 3 fails before scoring · concept detected,
                         but no IH06 node with a valid RBNR exists as a
                         candidate under that turbine · G2.0i excludes
                         unprofiled nodes upfront

concept_no_node          link 3 fails · concept detected, best profiled
                         IH06 node score below 0.60

concept_ambiguous_node   link 3 fails · best score ≥ 0.60, but margin
                         to the second node below 0.05

```

Link 4 cannot fail in the frozen chain: G2.0i excludes unprofiled nodes
before scoring. Record this in the memo; do not change the candidate filter.

**Orders with more than one concept** are assigned by the concept that progressed furthest along the chain. Report how many orders had multiple concepts.

Report `resolved` (3,935) alongside, as reference. **All categories plus `resolved` must sum to 10,749.** Assert it.

---

## Required breakdowns

### A · `concept_no_node` — near-miss profile

```
score band          ≥ 0.55 · 0.50–0.55 · 0.40–0.50 · < 0.40
top 20 concepts     by order count
node availability   does the turbine's IH06 subtree contain any node
                    of that component class · only if IH06 carries a
                    class or object-type field · else declare N/A
unprofiled best match
                    recompute the best score over ALL descendant nodes,
                    profiled or not · count orders whose best overall
                    match is an unprofiled node scoring ≥ 0.60
                    · diagnostic only · the frozen chain is not changed
```

Plus a sample of **30 pairs**, stratified by score band:

```
concept label · best IH06 node description · score
```

⚠️ **Private, not sanitised.** The 30 pairs go to
`g2_baseline_models/internal/g20k_component_lift/g20k3_near_miss_pairs.csv`
with file permissions 600 and directory permissions 700. The lead reads
them there. Version only score-band counts and safe identifiers, never
the concept label or IH06 description. The pairs help distinguish wording
differences from absent IH06 nodes.

### B · `concept_ambiguous_node` — does the ambiguity matter?

For each order in this category, compare the top two candidate nodes:

```
same RBNR        both nodes carry the same profile
different RBNR   profiles differ
```

⚠️ **Report the count only. Do not promote and do not resolve.** Matching
top-two RBNRs do not establish profile consensus if another node within
the frozen 0.05 band has a different RBNR.

### C · `G2.0k.2` cross-tab

Distribution of the 459 orders touched by the new terms across the five
unresolved categories and `resolved`.

---

## Deliverables

```
g20k3_partition_summary_sanitized.csv     counts per category · sum check
g20k3_order_stage_sanitized.csv           one row per order · category
                                          · furthest link reached
g20k3_near_miss_summary_sanitized.csv     score-band counts and safe IDs
g20k3_ambiguous_rbnr_sanitized.csv        breakdown B
g20k3_memo.md

internal/g20k3_near_miss_pairs.csv        30 visible pairs · mode 600
```

Add to the existing `g20k_component_lift` output folder.

---

## Constraints

```
threshold 0.60 and margin 0.05 frozen · verified, not assumed
G2.0i chain replayed as-is · vocabulary as registered in G2.0k.2
B1 only · never aggregate across paths
no precision claim · no promotion · no F6 update
sanitised versioned outputs
```

---

## Side check — scope of the 128-token limit

**Separate from the partition, one short table.** The limit acts only where MiniLM embeds order text, not concept labels. List, for each past semantic step, what was embedded:

```
step      embedded input                        affected by 128 limit
G2.0c     ?                                     ?
G2.0d2    ?                                     ?
G2.0i     concept labels · IH06 descriptions    no · confirmed
G2.0j     order text segments                   yes · 702 orders declared
```

Fill from the code, not from the memos. **Report only.**

---

## Closure criteria

- Every unresolved order assigned to exactly one category
- Sum check equals 10,749
- Breakdowns A, B and C reported
- 30 near-miss pairs delivered for manual reading
- visible pairs confined to internal/ and sanitisation check clean
- Threshold and margin verified unchanged
- Side-check table filled from code

---

## What this decides

```
concept_no_node dominant, near-misses high
    → the lever is the lexical bridge between technician terms and
      IH06 descriptions · a mapping concern, not a detection one

no_component_concept dominant
    → most unresolved orders do not name their component in text
      · that is the finding, and the turbine profile is the ceiling

concept_ambiguous_node with same RBNR large
    → a profile can be read without resolving the exact node
      · the cheapest gain available, pending an admissibility decision

no_turbine_node non-trivial
    → a join issue upstream, independent of any text work
```

**Each outcome points to a different next step, and each one applies to Object Part, Symptom and Cause at once.**

