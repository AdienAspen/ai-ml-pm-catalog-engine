# G2.0k.6 — Semantic Disjunction and Crosswalk Membership

**FSA BRIDGE / STINT_2 · Diagnostic only · B1 only**
Estimated: half a day or less · no replay

---

## Why this exists

`G2.0k.5` compared enabled sets at the unit **group + code**. For the 3,217 orders with a component RBNR different from `PMMUWW`, the sets were disjoint for Symptom, Object Part, Cause and Activity; Damage was disjoint in 3,159 and identical in 58.

Two questions remain open:

```
a  Is the disjunction semantic, or only a naming effect?
   Hypothesis to test: a profile enables code groups; groups may be
   profile-specific; the same code, with the same meaning, may exist
   in different groups. In that case the pairs differ while the
   meaning is shared.

b  Where do the crosswalk-strong Object Part pairs belong?
   G2.0k.5: only 11 of 1,189 orders have a crosswalk pair enabled by
   the component profile. Membership in PMMUWW, in other profiles,
   or in no profile was not reported.
```

This step compares existing sets. It reads no order text and resolves nothing.

---

## 0 · Pre-flight — confirm from the chain spec, the catalogue sources and the code

State each item as `confirmed` or `differs`, citing the source file, field or code location. **If any item differs, stop and report before running.**

```
Q1  profile definition: state what the client's profile table lists
    per catalogue type · code groups, group patterns with wildcards,
    or group + code pairs · if wildcards: state the expansion rule
    used in G2.0k.5
Q2  catalogue master: every (catalogue type, group, code) has a
    description text · name the field and the language used · if
    several languages exist, use one language consistently and
    state which
Q3  G2.0k.5 enabled sets per RBNR are persisted · reuse them · verify
    they reproduce the G2.0k.5 category counts before any analysis
    · any mismatch → stop
Q4  crosswalk-strong output (3,013 orders) carries catalogue type,
    group and code per order · not code only
Q5  within one catalogue type, report whether the same code value
    appears in more than one group · counts only
```

---

## a · Semantic disjunction

**Unit of analysis: distinct RBNR, not order.** Enabled sets depend only on the RBNR. Compute per distinct component RBNR against `PMMUWW`, then report two views: per RBNR, and weighted by the number of orders holding that RBNR among the 3,217.

For each component RBNR × target, compare the enabled sets at two further units:

```
code_value         the code value alone, group removed
description        the code description, normalised: lowercase,
                   trimmed, internal whitespace collapsed
                   · exact match only · no synonyms, no embeddings
```

⚠️ **A shared code value does not establish shared meaning.** The same value can carry different descriptions in different groups. `description` is the semantic unit; `code_value` is a control.

Per unit, classify with the G2.0k.5 precedence, first matching rule wins:

```
1  component_empty
2  same_set
3  narrower      component ⊂ PMMUWW, strict
4  wider         component ⊃ PMMUWW, strict
5  overlapping   non-empty intersection, neither contains the other
6  disjoint      empty intersection
```

**Per target and per unit, the six categories must sum to the number of distinct component RBNRs, and in the weighted view to 3,217. Assert both.**

Also report, per target, the share of `code_value` matches whose descriptions differ.

---

## b · Crosswalk membership

For each crosswalk-strong Object Part pair, assign membership, first matching rule wins:

```
1  in_component_profile   enabled by the order's component RBNR
                          · only for orders with a component RBNR
2  in_pmmuww              enabled by PMMUWW
3  in_other_profile       enabled by at least one other RBNR, by
                          neither of the above
4  in_no_profile          exists in the catalogue master, enabled
                          by no RBNR
5  not_in_catalog         the pair does not exist in the catalogue
                          master
```

Report both units of analysis for two populations:

```
PAIR VIEW
  unit         distinct crosswalk-strong group + code pair per order
  categories  rules 1 to 5 above, in precedence order
  overlap     1,313 pairs across 1,189 resolved-component orders
  full        5,778 pairs across 3,013 strong-crosswalk orders
  assert      category sums equal 1,313 and 5,778, respectively

ORDER VIEW
  unit         order
  category     highest-precedence category among that order's pairs
               (rule 1 before 2 before 3 before 4 before 5)
  overlap     1,189 orders
  full        3,013 orders; where component RBNR is absent, rule 1
               is inapplicable and classification starts at rule 2
  assert      category sums equal 1,189 and 3,013, respectively

mixed_membership
  count orders whose pairs span more than one category, separately
  for both populations; this is not a sixth category
  overlap     at most 97 orders can be mixed (97 have multiple pairs)
```

State in the memo how many orders have multiple pairs in each population:
97 in the overlap, 821 in the full set. The order view is consistent
with G2.0k.5's any-enabled-pair count, but pair and order rates must
never be conflated.

For `in_other_profile`: number of distinct enabling RBNRs, and the share of pairs covered by the top 5.

---

## Handling of client content

```
versioned, sanitised    category counts · sums · shares · safe IDs
                        · PMMUWW may be named · other RBNR values
                        anonymised unless repo convention differs
                        (state it)
internal/, 600          code descriptions · per-RBNR detail · pair
                        lists · not versioned · never labelled
                        sanitised
```

---

## Deliverables

```
g20k6_semantic_overlap_sanitized.csv      section a · per RBNR and
                                          weighted · sum checks
g20k6_crosswalk_membership_sanitized.csv  section b · both
                                          populations · sum checks
internal/g20k6_detail.csv                 permissions 600
g20k6_memo.md                             pre-flight table · Q5
```

Add to the existing `g20k_component_lift` folders.

---

## Constraints

```
no order text read · no replay · no scoring
no promotion · no F6 update · no change to the crosswalk
B1 only · never aggregate across paths
```

---

## Closure criteria

- Pre-flight Q1 to Q5 stated with references
- Section a: both units, both views, all five targets, sums asserted
- Section b: both populations and both units, sums asserted; multi-pair
  and mixed-membership order counts declared
- Client descriptions only in `internal/`

---

## What this decides

**Section a**, read at the `description` unit:

```
disjoint dominant
    → the profiles enable different meanings · the registration
      level, turbine or component, changes which meanings can be
      recorded · the client decision on registration level is
      required before further component work

same_set dominant
    → the G2.0k.5 disjunction is a naming effect · a mapping by
      description between profiles is feasible · registering both
      levels in one migration becomes simpler

narrower or wider dominant
    → the component profile restricts or extends the meanings
      available · read per target, as in G2.0k.5

overlapping dominant
    → partial shared meaning · quantify the shared share per target
      before any mapping proposal

component_empty non-trivial
    → the component profile enables nothing for that target · the
      target cannot be coded at component level for those RBNRs
```

**Section b:**

```
in_pmmuww dominant
    → the crosswalk is consistent with turbine-level registration
      and inconsistent only with component-level registration

in_component_profile non-trivial
    → the crosswalk is consistent with component-level registration
      for those orders

in_other_profile dominant
    → the crosswalk was built against other profiles · identify
      which

in_no_profile or not_in_catalog non-trivial
    → defect in the crosswalk output · the status-table row
      "Object Part B1 · 3.013 · crosswalk strong" must be relabelled
      before any further use
```

**Each category has a stated reading. Any of them is a result.**
