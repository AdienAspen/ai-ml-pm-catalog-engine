# G2.0k.4 — Tie Structure Diagnostic

**FSA BRIDGE / STINT_2 · Diagnostic only · B1 only**
Estimated: half a day

---

## Why this exists

`G2.0k.3` placed **2,238 of 6,814 unresolved orders** in `concept_ambiguous_node`: a match above 0.60 exists, but the margin to the next node is below 0.05. It is the largest block that already has a strong match.

Only 136 of them share `RBNR` across the top two nodes, so most ties cross profiles.

**Working hypothesis, to be tested, not assumed:** many ties are between nodes on the same hierarchical line, for example a subsystem and its assembly carrying near-identical descriptions. If that holds, a principled resolution exists: read the profile at their lowest common ancestor.

This step describes **the structure of each tie**. It resolves nothing.

---

## 0 · Pre-flight — confirm from code before running

State each as `confirmed` or `differs` in the memo, quoting the code location. **If any item differs, stop and report before running.**

```
A1  the 2,238 have best score ≥ 0.60 and (best − second) < 0.05,
    AND remain unprofiled after G2.0k.3 all-near-top RBNR consensus
A2  candidates are restricted to descendants of the order's own
    turbine node · not drawn from the global IH06
A3  candidates are restricted to nodes with a valid RBNR (G2.0i
    pre-filter, confirmed in G2.0k.3)
A4  the turbine node itself is never a candidate
A5  for candidates reachable from the order's turbine node, the path
    is reconstructable through `Superior functional location`;
    global parent completeness is not assumed · roots and 79 dangling
    parent references are declared
A6  withdrawn · a node's score is the maximum over ALL detected
    concepts; no tie is attributed to one concept
A7  the profile → enabled-codes table from G2.0h/G2.0i is available
    for Symptom, Cause and Object Part
```

---

## 1 · Tie set definition

**Not only the top two.** The tie set of an order is every candidate
node whose score is strictly within 0.05 of the best node score. Each
node score is the maximum over all detected concepts, as in G2.0i.

This addresses the team's observation: a third close node may carry a different profile.

Report the distribution of tie set size: 2 · 3 · 4–5 · more than 5.

---

## 2 · Structural category — mutually exclusive, exhaustive

Assign each order by the first rule that applies:

```
ancestor_chain       every node in the tie set lies on a single
                     ancestor–descendant line

siblings             every node shares the same immediate parent,
                     and none is an ancestor of another

shared_subtree       lowest common ancestor is below the turbine
                     node, and neither rule above applies

cross_subsystem      lowest common ancestor is the turbine node

path_incomplete      a tie node's path to the turbine cannot be
                     reconstructed · expected 0 · assert and report
```

**The five must sum to 2,238. Assert it.**

For each order also record:

```
lca_depth              levels below the turbine node · 0 = turbine
identical_descriptions nodes in the tie set with identical IH06
                       description text · signals repeated instances
                       such as three blades or several modules
```

For every node in the tie set, record the concept producing its
maximum score. Classify the order as `single_concept_tie` if every
node has the same winning concept, or `multi_concept_tie` otherwise.
Multiple concepts may reflect multiple named parts rather than node
ambiguity. Cross-tab concept origin with structural category; assert
that the counts sum to 2,238.

---

## 3 · Profile dimension

For each tie set:

```
tie_rbnr_homogeneous   all nodes in the tie set share one RBNR
lca_profiled           the lowest common ancestor carries a valid RBNR
```

Cross-tab: **structural category × tie_rbnr_homogeneous × lca_profiled.**

Recompute the 136 figure over the full tie set, not only the top two,
and report both. Because these 2,238 remained unprofiled after the
all-near-top consensus check, full-set RBNR homogeneity is expected
to be zero; verify rather than promote.

---

## 4 · Answer-space size — what a resolution would buy

Only for orders where `lca_profiled = true`. Per target, compare the number of enabled codes:

```
                 turbine profile   LCA profile   tie-node profiles
Symptom                 6               ?          min · max
Cause                  13               ?          min · max
Object Part             1               ?          min · max
```

Report medians and distributions.

⚠️ **This is the line that decides.** An LCA that sits one level below the turbine may enable almost the same codes as the turbine profile. In that case, resolving at the LCA buys nothing, whatever the structure says.

---

## Handling of IH06 content

```
versioned, sanitised    counts · categories · depths · code counts
                        · safe identifiers only
internal/, 600          any node descriptions, description pairs or
                        examples used for inspection · not versioned
                        · never labelled sanitised
```

Include in `internal/` a sample of **20 tie sets** stratified by structural category, showing the node descriptions and scores, for manual reading by the lead.

---

## Deliverables

```
g20k4_tie_structure_summary_sanitized.csv    categories · sum check
g20k4_concept_origin_crosstab_sanitized.csv   structural × concept origin
g20k4_tie_profile_crosstab_sanitized.csv     section 3
g20k4_answer_space_sanitized.csv             section 4
internal/g20k4_tie_samples.csv               20 tie sets · permissions 600
g20k4_memo.md                                includes the pre-flight table
```

Add to the existing `g20k_component_lift` folders.

---

## Constraints

```
threshold 0.60 and margin 0.05 frozen
deterministic replay of frozen G2.0i scoring permitted · no retuning
same model, vocabulary, threshold, margin and max-over-concepts rule
replay gate before analysis: reproduce the G2.0k.3 category of all
6,814 unresolved orders exactly; any mismatch stops the run
G2.0i chain and G2.0k.2 vocabulary as registered
no resolution · no promotion · no F6 update
B1 only · never aggregate across paths
```

---

## Closure criteria

- Pre-flight A1 to A5 and A7 confirmed from code, with locations;
  A6 explicitly withdrawn
- Replay gate confirms all 6,814 unresolved categories before analysis
- Tie set built from the 0.05 window, not top-2 only
- Five structural categories and concept-origin cross-tab sum to 2,238
- Profile cross-tab and recomputed 136 reported
- Answer-space comparison reported for `lca_profiled` orders
- IH06 content only in `internal/`

---

## What this decides

```
ancestor_chain or siblings dominant, LCA profiled,
LCA answer space clearly narrower than turbine
    → LCA-level profile reading is a candidate rule
      · admissibility is a separate decision, with precision measured

LCA profiled but answer space close to turbine
    → the structure resolves, the gain does not · finding recorded,
      no rule proposed

cross_subsystem dominant
    → ties are genuine ambiguity between different parts · the
      concept label is too generic for this link · points back to
      vocabulary granularity, not to hierarchy
```

**The hypothesis in "Why this exists" may not hold. Any of the three outcomes is a result.**

