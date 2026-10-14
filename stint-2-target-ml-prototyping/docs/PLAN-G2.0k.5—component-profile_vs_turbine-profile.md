# G2.0k.5 — Component Profile vs Turbine Profile

**FSA BRIDGE / STINT_2 · Diagnostic only · B1 only**
Estimated: half a day or less

---

## Why this exists

The whole `G2.0k` line rests on one assumption that has never been measured: **that the profile read at a component node enables a different, more pertinent code set than the turbine profile `PMMUWW`.**

`G2.0k.4` put that assumption in question. The lowest common ancestor carried a valid RBNR in 2,201 tie sets, yet did not reduce the answer space for Symptom or Object Part, and did so for Cause in only 358 cases.

**Hypothesis to test, not assumed:** if the subsystem profile barely differs from the turbine profile, the component profile may not differ either.

This step compares, **for the 3,935 orders already resolved to a component profile**, what that profile enables against what `PMMUWW` enables. It resolves nothing new.

---

## 0 · Pre-flight — confirm against the chain spec and the code

Derive each item from `G2.0i-resolution-chain-code-spec.md` and the code. State `confirmed` or `differs`, citing the spec section or code location. **If any item differs, stop and report before running.**

```
P1  the resolved RBNR per order is persisted in G2.0i / G2.0k.2
    outputs for all 3,935 orders · name the file and field
    if NOT persisted: deterministic replay permitted, with gate —
    the replay must reproduce the same 3,935 orders and the same
    RBNR per order exactly · any mismatch → stop
P2  the turbine RBNR per order is recoverable for the same orders
P3  the profile → enabled-codes table covers all five catalogue
    targets: Symptom (S) · Object Part (B) · Damage (C) · Cause (5)
    · Activity (A) · name the source
P4  unit of comparison per target is defined in that table
    · state it: group+code pair, or code within group
P5  crosswalk-strong Object Part output (3,013) is at the same unit
    as P4 · needed only for section 3
```

---

## 1 · Profile identity — per order

```
turbine_profile_missing   no valid turbine RBNR · non-comparable
                          · declared, never counted as zero
same_rbnr                 component RBNR = turbine RBNR
different_rbnr            component RBNR ≠ turbine RBNR
```

**Sum must equal 3,935. Assert it.** Among these, 3,267 have a
comparable turbine `PMMUWW` profile and 668 have no valid turbine
profile. Never represent the latter as zero enabled codes.

Also report the number of distinct component RBNRs and the share of orders held by the top 5.

---

## 2 · Code-set comparison — per order, per target

Only for `different_rbnr` among the 3,267 `PMMUWW`-comparable orders.
For each of the five targets, compare enabled group+code pair sets.
Apply the first matching rule:

```
same_set        different RBNR, identical enabled codes
narrower        component set is a strict subset of turbine set
wider           component set is a strict superset
overlapping     partial overlap, neither contains the other
disjoint        no code in common
component_empty component set is empty · first, even if turbine is
                also empty
```

Precedence: `component_empty` → `same_set` → `narrower` → `wider`
→ `overlapping` → `disjoint`. The six are mutually exclusive and
exhaustive. Per target, they must sum to the `different_rbnr` count
within the 3,267 comparable orders. Assert it.

Per target, also report the distribution of group+code pairs added
and removed relative to `PMMUWW`: median and max.

Separately, for the 668 `turbine_profile_missing` orders, report
`component profile obtained`: their answer space moved from the
catalogue-wide, unfiltered space to a component profile. Per target,
report the enabled group+code pair count under that component profile
(median and max). These orders are outside the 3,267 comparison and
never enter the six-class sum. When the 1,548-order no-profile status
table is updated later, reflect these 668 there; do not change that
table in this diagnostic run.

⚠️ **Count alone is not the measure.** `same_set` and `narrower` are different findings from `overlapping`, even when the sizes match. Direction also depends on the target: Object Part is a single code under `PMMUWW`, so the expected gain there is `wider`, not `narrower`.

---

## 3 · Pertinence signal — Object Part only, if P5 confirmed

For orders in both the 3,935 resolved and the 3,013 crosswalk-strong sets:

```
crosswalk code ∈ component set     ?
crosswalk code ∈ PMMUWW set        ?
in both · in neither               ?
```

**Report only.** The crosswalk is a deterministic lookup, not ground truth. This is a consistency signal, not precision.

If P5 differs, skip this section and declare it.

---

## 4 · Carry-over from G2.0k.4 — confirm in this memo

```
identical_descriptions   tied sibling nodes with identical IH06
                         description text · counts only
lca_rbnr_vs_turbine      in the 2,201 LCA-profiled ties: LCA RBNR
                         equal to turbine RBNR, or different RBNR
                         with the same code count
```

---

## Handling of client content

```
versioned, sanitised    category counts · distributions · safe IDs
internal/, 600          per-RBNR code lists, added and removed code
                        detail · not versioned · never labelled
                        sanitised
```

---

## Deliverables

```
g20k5_profile_identity_sanitized.csv       section 1 · sum check
g20k5_codeset_comparison_sanitized.csv     section 2 · five targets
g20k5_missing_turbine_profile_sanitized.csv 668 orders · per-target summary
g20k5_object_part_consistency_sanitized.csv section 3 · if run
internal/g20k5_codeset_detail.csv          permissions 600
g20k5_memo.md                              pre-flight table · section 4
```

Add to the existing `g20k_component_lift` folders.

---

## Constraints

```
no new resolution · no scoring beyond a gated replay if P1 requires it
threshold 0.60 and margin 0.05 untouched
no promotion · no F6 update
B1 only · never aggregate across paths
```

---

## Closure criteria

- Pre-flight P1 to P5 stated with spec or code references
- Section 1 sums to 3,935
- Section 2 sums per target to the `different_rbnr` count, all five targets
- Section 3 run or declared skipped
- Section 4 carry-over items answered
- Client code detail only in `internal/`

---

## What this decides

```
same_rbnr or same_set dominant
    → component resolution does not change the answer space
      · the G2.0k line stops here · the profile is not the lever
      · finding recorded for Symptom, Cause, Damage, Activity and
        Object Part at once

narrower (S, 5, C, A) or wider (B) dominant
    → the component profile is a real lever · further work on
      resolving the 6,814 is justified, and G2.0k.4 ties become
      worth resolving

mixed by target
    → the lever exists for some targets only · subsequent work is
      scoped per target, never generalised
```

**Any of the three is a result. The first one would also reframe the client deliverable: the configuration question moves from "which node" to "which profile".**

