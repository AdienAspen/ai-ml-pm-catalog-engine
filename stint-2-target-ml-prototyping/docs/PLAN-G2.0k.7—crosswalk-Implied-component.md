# G2.0k.7 — Crosswalk-Implied Component

**FSA BRIDGE / STINT_2 · Diagnostic only · B1 only**
Estimated: half a day · no replay of G2.0i

---

## Why this exists

`G2.0k.6`, section b: of 5,778 crosswalk-strong Object Part pairs, 0 are enabled by `PMMUWW`, 11 by the component profile identified by `G2.0i`, and 5,767 by other profiles.

**Hypothesis to test, not assumed:** each crosswalk pair is enabled by specific profiles. If a node carrying one of those profiles exists in the IH06 subtree of the order's turbine, the `itemDescription`-derived crosswalk may point to a component independently of the order narrative read by G2.0i.

If the hypothesis holds, this step provides:

```
1  an identification via itemDescription for crosswalk-strong
   orders, independent of the order narrative
2  a comparison against G2.0i on the 1,189 orders where both exist
   · agreement between two methods, not precision · neither is
   ground truth
```

This step reads neither itemDescription nor order narrative anew; it
reuses the previously derived crosswalk, changes no resolution and
promotes nothing. The crosswalk itself was built from itemDescription.

---

## 0 · Pre-flight — confirm from the chain spec, the crosswalk code and prior outputs

State each item as `confirmed` or `differs`, citing file, field or code location. **If any item differs, stop and report before running.**

```
R1  crosswalk input: itemDescription in the consumed item record.
    This is text distinct from the order narrative reason and
    descriptionExtended read by G2.0i. Report agreement between
    two text-derived methods using different fields of the order.
R2  G2.0k.6 persists enabling RBNRs for in_other_profile pairs,
    but omits them for 11 in_component_profile pairs. Before any
    analysis, complete and persist those 11 sets using unchanged
    G2.0k.6 catalogue logic. Reuse the completed per-pair sets.
    Gate: categories reproduce 0 / 11 / 5,767; mismatch -> stop.
R3  turbine subtree per order is reconstructed as in G2.0k.4: via
    `Superior functional location`, reachable subtree only. Node
    RBNR means effective nearest-valid-ancestor RBNR, as in G2.0i.
R4  3,935 resolved profiles: 2,400 unique nodes with persisted
    resolved_node_hash, and 1,535 profile-consensus outcomes with
    ambiguous nodes. Among 1,189 overlap orders: 770 unique nodes
    and 419 ambiguous nodes. Assert these counts and name sources.
R5  all 3,013 crosswalk-strong orders are B1 · the 1,189 overlap
    orders are a subset of the 3,935
R6  candidate nodes are IH06 functional locations only · equipment
    is excluded, since the assetId → IH08 link is 0 of 10,749
```

---

## 1 · Implied component — availability

**Definitions:**

```
enabling set of a pair    RBNRs that enable that pair (from G2.0k.6)
implied nodes of a pair   IH06 descendants in the order's turbine
                          subtree whose effective nearest-valid-ancestor
                          RBNR belongs to the pair's enabling set
implied nodes of an order union of the implied nodes of its pairs
```

### Pair view — unit: pair · sum = 5,778

```
1  no_turbine_subtree           order has no turbine node
2  implied_single_node          exactly one implied node
3  implied_multi_node_one_rbnr  several implied nodes, all with the
                                same RBNR · profile determined, node
                                not determined
4  implied_multi_rbnr           implied nodes carry more than one RBNR
5  implied_none                 no node of any enabling RBNR exists in
                                this turbine subtree
```

First matching rule wins. Assert the sum.

Also report the distribution of enabling-set size per pair: 1 · 2–5 · 6–20 · more than 20. **A pair enabled by many profiles carries little information about the component.**

### Order view — unit: order · sum = 3,013

Same five categories, applied to the order's union of implied nodes. Assert the sum.

Report alongside, not as a sixth category:

```
pairs_point_to_different_nodes   orders with at least two pairs
                                 having nonempty, disjoint implied
                                 node sets · empty sets do not qualify
                                 · the order may record more than one part
```

---

## 2 · Comparison with G2.0i — two non-collapsed order views

### 2a · Node level — 770 orders with a unique G2.0i node

Compare the persisted `resolved_node_hash` with the crosswalk-implied
nodes. First matching rule wins:

```
1  same_node              G2.0i node is among the implied nodes
2  same_rbnr_other_node   G2.0i RBNR is among the implied RBNRs, the
                          node is not
3  same_subsystem         G2.0i node and at least one implied node
                          share a lowest common ancestor below the
                          turbine node
4  different_subsystem    lowest common ancestor is the turbine node
5  no_implied_node        section 1 category 1 or 5 for this order
```

Assert the 2a sum equals 770.

### 2b · Profile level — 419 orders with an ambiguous G2.0i node

First matching rule wins:

```
1  same_rbnr       G2.0i RBNR is among the implied RBNRs
2  different_rbnr  implied nodes exist, none with the G2.0i RBNR
3  no_implied_node section 1 category 1 or 5 for this order
```

Assert the 2b sum equals 419. Do not compute node agreement for 2b;
state this limitation in the memo.

**11-order control:** every order from G2.0k.6 with
`in_component_profile` must fall in 2a category 1 or 2, or 2b
category 1. Assert all 11.

⚠️ **This measures agreement, not precision.** Both methods are
text-derived but read different fields: itemDescription versus order
narrative. Profile agreement in 2b is not node agreement.

---

## 3 · Potential coverage — report only

For the crosswalk-strong orders **without** a G2.0i component profile (expected 3,013 − 1,189 = 1,824; state the actual count):

```
implied_single_node · implied_multi_node_one_rbnr    → profile determinable
implied_multi_rbnr · implied_none · no_turbine_subtree → not determinable
```

Report counts per category. **No order is assigned a profile in this step.**

---

## Handling of client content

```
versioned, sanitised    category counts · sums · distributions
                        · safe identifiers only
internal/, 600          node identifiers · RBNR values other than
                        PMMUWW · per-order detail · not versioned
                        · never labelled sanitised
```

---

## Deliverables

```
g20k7_implied_pairs_sanitized.csv       section 1 · pair view
g20k7_implied_orders_sanitized.csv      section 1 · order view
g20k7_g20i_agreement_sanitized.csv      section 2
g20k7_coverage_sanitized.csv            section 3
internal/g20k7_detail.csv               permissions 600
g20k7_memo.md                           pre-flight table
```

Add to the existing `g20k_component_lift` folders.

---

## Constraints

```
no text fields reread in this step · no replay of G2.0i
no change to the itemDescription-derived crosswalk
no profile assigned · no promotion · no F6 update
B1 only · never aggregate across paths
```

---

## Closure criteria

- Pre-flight R1 to R6 stated with references
- Section 1: both views, sums 5,778 and 3,013 asserted
- Section 2: separate sums 770 and 419 asserted · the 11-order
  check asserted · no node-level claim for 2b
- Section 3: reported, no assignment
- Node identifiers and non-PMMUWW RBNR values only in `internal/`

---

## What this decides

**Section 1:**

```
implied_single_node or implied_multi_node_one_rbnr dominant
    → the itemDescription-derived crosswalk identifies a component
      profile independently of the order narrative (subject to R1)

implied_multi_rbnr dominant
    → the crosswalk narrows to a few candidate profiles but does not
      determine one · it can only be combined with another method

implied_none dominant
    → the profiles that enable the crosswalk pairs are not present
      under these turbines · the crosswalk was built against a
      catalogue configuration that does not match this IH06
      · the status-table row is relabelled as inconsistent with the
      client's configuration

pairs_point_to_different_nodes non-trivial
    → a share of orders records more than one part · relevant to
      the multi-label question for G2 modelling
```

**Section 2a — node-level only:**

```
same_node or same_rbnr_other_node dominant
    → G2.0i and the crosswalk agree · first evidence supporting the
      G2.0i identifications, within the independence stated in R1

same_subsystem dominant
    → both methods identify the subsystem, not the same component
      · consistent with G2.0k.4: ambiguity is within the subsystem

different_subsystem non-trivial
    → the methods disagree on the subsystem · one of them identifies
      the wrong component for those orders · cases go to manual
      review in internal/

no_implied_node dominant
    → no comparison possible · follows from section 1
```

**Section 2b:** `same_rbnr` indicates agreement at profile level
only. Node agreement is undefined for these 419 orders.

**Section 3:** the count of `profile determinable` orders is the potential gain of an itemDescription-derived identification path. It is reported, not applied.

**Each category has a stated reading. Any of them is a result.**
