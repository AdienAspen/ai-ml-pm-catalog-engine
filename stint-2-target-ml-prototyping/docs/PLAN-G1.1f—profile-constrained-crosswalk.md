# G1.1f — Profile-Constrained Crosswalk

**FSA BRIDGE / STINT_2 · Reopens G1.1 · Diagnostic only · B1 only**
Estimated: half a day to one day

---

## Why this exists

`G1.1` mapped each consumed material to a Catalog B code by comparing descriptions against the **full** Catalog B (1,240 codes). The profile mechanism was not known when it was built.

`G2.0k.6` and `G2.0k.7` showed:

```
5,778 crosswalk-strong pairs · 3,013 orders
each pair enabled by exactly one RBNR
1,804 orders: no node with that RBNR under the order's turbine
```

The crosswalk has two separate properties:

```
i   semantic match    material description ↔ code description
                      · plausible · never validated
ii  profile condition the chosen code exists in a profile present
                      under the order's turbine · not considered by
                      design · main cause of the mismatch
```

**Question for the 1,804 orders:** is the mismatch caused by the crosswalk's choice, or by the client configuration?

```
hypothesis A   an equivalent code exists in a profile present under
               the turbine · the crosswalk chose the code of another
               profile because its description scored slightly higher
hypothesis B   no equivalent code exists under the turbine · the
               client configuration has no code for that part there
```

This step repeats the `G1.1` match **with the candidate set restricted to the profiles present under each order's turbine**, keeping property i unchanged and adding property ii. It assigns nothing.

---

## 0 · Pre-flight — confirm from the G1.1 code, the chain spec and prior outputs

State each item as `confirmed` or `differs`, citing file, field or code location. **If any item differs, stop and report before running.**

```
F1  G1.1 method: name the matching method (lexical, embedding model
    and version), the exact fields compared on each side (material
    field · Catalog B field: code description, group description or
    both), and the tier thresholds for strong · medium · weak
F2  tier rule: state whether tiers use an absolute score only, or
    also a margin to the second-best candidate · if a margin is used,
    state how it is computed · under restriction the second-best
    changes, so the margin rule must be declared before running
F3  pair = order × (catalogue group, Catalog B code), distinct
    · 5,778 pairs · same key as G2.0k.6 and G2.0k.7
    the match runs per material concept (G1.1 unit); each original
    pair is the set of material concepts that produced it in that
    order · the pair takes the highest-precedence category among its
    material concepts · report pairs with more than one concept
F4  G2.0k.7 persisted only the enabling RBNRs of original pairs.
    Rebuild the full enabled code set per RBNR from the frozen
    catalogue, using G2.0k.5 profile expansion unchanged.
    Gate: reproduce G2.0k.6 membership 0 / 11 / 5,767
F5  turbine subtree and its set of RBNR values are reconstructed as
    in G2.0k.4 and G2.0k.7: via `Superior functional location`,
    reachable subtree only · PMMUWW included in the set
F6  replay gate: an UNRESTRICTED replay of the G1.1 match must
    reproduce exactly the code and tier of every one of the 708
    concepts and of all 5,778 pairs · any mismatch → stop · do not
    analyse a non-identical replay
```

---

## 1 · Restricted match

For each pair, the candidate set is the Catalog B codes enabled by any RBNR present in the order's turbine subtree. Run the `G1.1` match unchanged on that set: same method, same fields, same thresholds, and the margin rule declared in F2.

No retuning. No new similarity method.

---

## 2 · Pair categories — unit: pair · sum = 5,778

First matching rule wins:

```
1  no_turbine_subtree        the order has no turbine subtree
2  original_code_available   the G1.1 code itself is enabled under
                             the subtree · assert 1,459 pairs
3  exact_equivalent          a code under the subtree has a normalised
                             description identical to the G1.1 code's
                             description · normalisation as in
                             G2.0k.6: lowercase, trimmed, internal
                             whitespace collapsed
4  restricted_strong         best restricted candidate meets the G1.1
                             strong threshold
5  restricted_medium_weak    best restricted candidate meets medium or
                             weak, not strong
6a no_enabled_codes_under_subtree
                             the turbine subtree enables no Catalog B
                             code at all · structural absence
6b enabled_codes_no_score    enabled codes exist; none reaches weak
                             · lexical absence
```

Assert the sum.

**Readings per category:** 3 and 4 support hypothesis A. 6a supports a configuration finding; 6b is inconclusive because the unchanged lexical detector found no match among enabled codes. 5 also needs manual reading.

---

## 3 · Order view — unit: order · sum = 3,013

Each order takes the highest-precedence category among its pairs. Assert the sum.
`original_code_available` must equal **1,207 orders**; assert it.

Report alongside, not as a seventh category:

```
mixed_category_orders   orders whose pairs fall in more than one
                        category
```

Report the same distribution separately for the **1,804 orders** classified `implied_none` in G2.0k.7. That subset is the target of this step.

---

## 4 · By-product — component implied by the restricted code

For pairs in categories 3, 4 and 5, the restricted code belongs to RBNRs present under the turbine, so it points to nodes. Classify, as in G2.0k.7:

```
single_node · multi_node_one_rbnr · multi_rbnr
```

For orders that also have a `G2.0i` profile, report whether the restricted code's RBNR equals the `G2.0i` RBNR. **Agreement, not precision.** Both methods read text: `itemDescription` and the order narrative.

---

## Handling of client content

```
versioned, sanitised    counts · sums · distributions · safe IDs
                        · PMMUWW may be named · other RBNR values
                        anonymised
internal/, 600          material descriptions · code descriptions ·
                        per-pair detail · node identifiers · not
                        versioned · never labelled sanitised
```

Include in `internal/` a sample of **30 pairs** from the 1,804 orders, stratified by categories 3 to 6b where present, with 6a and 6b separate. For each pair: the material description, the original G1.1 code description and the best restricted code description. This sample is for manual reading by the lead.

---

## Deliverables

```
g11f_pair_categories_sanitized.csv        section 2 · sum check
g11f_order_categories_sanitized.csv       section 3 · both populations
g11f_component_byproduct_sanitized.csv    section 4
internal/g11f_detail.csv                  permissions 600
internal/g11f_sample_30.csv               permissions 600
g11f_memo.md                              pre-flight table · F2 margin
                                          rule as applied
```

Folder: `g1_actionable_zeros/g11_object_part_crosswalk/outputs/g11f_profile_constrained/`, with `internal/` alongside.

---

## Constraints

```
the G1.1 method, fields and thresholds unchanged · gated replay only
the original crosswalk is not modified · results go to a new file
no code assigned · no promotion · no F6 update
B1 only · never aggregate across paths
```

---

## Closure criteria

- Pre-flight F1 to F6 stated with references · both gates passed
- Section 2 sums to 5,778 · section 3 sums to 3,013
- 1,804-order subset reported separately
- Section 4 reported
- 30-pair sample in `internal/` only

---

## What this decides

```
exact_equivalent or restricted_strong dominant in the 1,804
    → hypothesis A · the mismatch comes from the crosswalk choice
      · a profile-constrained crosswalk gives valid component-level
        Object Part codes for those orders, subject to precision
        measurement · the status-table row can move back toward
        resolved, at component level only

no_enabled_codes_under_subtree dominant in the 1,804
    → structural configuration finding for the client

enabled_codes_no_score dominant in the 1,804
    → inconclusive · the lexical method found no match among enabled
      codes · does not establish a configuration gap

restricted_medium_weak dominant
    → inconclusive · the 30-pair manual reading decides before any
      further step

original_code_available
    → control · 1,459 pairs and 1,207 orders with an implied node in
      G2.0k.7 · any difference indicates reconstruction error

no_turbine_subtree
    → structural · expected ≈ 2 orders, as in G2.0k.7

mixed_category_orders non-trivial
    → orders recording several parts with different outcomes · read
      per pair, not per order
```

**Each category has a stated reading. Any of them is a result.** Its practical value depends on the client choosing component-level registration.
