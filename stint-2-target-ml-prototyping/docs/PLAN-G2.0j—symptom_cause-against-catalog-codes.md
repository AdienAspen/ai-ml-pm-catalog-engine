# G2.0j — Symptom and Cause Against Real Catalogue Codes

**FSA BRIDGE / STINT_2 · Pipeline work · runs independently of annotation**
Estimated: 1 day

---

## Why this exists

Symptom and Cause were measured against external vocabulary that turned out to be much smaller than the client's own answer space:

```
                  measured against        client's catalogue
Symptom           8 WMEP failure effects  161 QMGRP groups · 4,171 codes
Cause             9 WMEP failure causes   161 URGRP groups · 6,232 codes
```

Under the `PMMUWW` Catalog Profile the reachable space narrows:

```
Symptom    1 group →  6 codes
Cause      1 group → 13 codes
```

**The external vocabulary was never the client's class space.** WMEP effects describe operational consequence — plant stoppage, reduced power — while Symptom should carry the condition detected on the asset. Those are different things.

**This step measures both targets against the codes SAP will actually store.**

---

## Objective

Re-derive candidate evidence for Symptom and Cause using the client's catalogue codes as the class space, and report coverage and non-coverage per path.

**Out of scope:** annotation, training, denominator promotion, catalogue mapping of individual records to production.

---

## Method

Same pipeline as `T5.1b2.X-normalized`. Only the class space changes.

```
normalisation    semantic_normalisation_v2
embedding        paraphrase-multilingual-MiniLM-L12-v2
class space      catalogue code descriptions, verbatim
                 including the catalogue's own typographical errors
threshold        frozen before running · declare it
scope            B1 eligible corpus · Path A and B2 separately
```

⚠️ **Use the code descriptions as they appear in the catalogue.** Do not paraphrase, expand or clean them. The model must compare against what SAP stores.

---

## Two class spaces per target · report both

```
PROFILE-SCOPED       codes reachable under PMMUWW
                     Symptom 6 · Cause 13
                     applies to the 9,151 orders with turbine profile
                     and the 3,934 with component profile

CATALOGUE-WIDE       all codes of the type
                     Symptom 4,171 · Cause 6,232
                     applies to the 1,548 orders without profile
                     and as a reference ceiling for the rest
```

**The contrast between the two is informative in itself.** If profile-scoped coverage is much lower than catalogue-wide, the profile may be excluding codes the corpus actually describes.

---

## Required output per target and path

```
units_evaluated
assigned_per_code
abstained
coverage_pct
no_applicable_rate        ← see below
top_code_share            flag above 30%
```

⚠️ **`no_applicable_rate` is a required metric, not an afterthought.**

The Activity annotation round showed that a target can have abundant text and near-zero catalogue coverage: 1 code assigned in 375 responses. **Measuring how much of the corpus the catalogue cannot express is as valuable as measuring what it can.**

Report it as: units with text describing the target's subject matter, but no code above threshold.

---

## Contrast against previous figures

```
                  WMEP-measured    catalogue-measured    delta
Symptom B1              104                ?               ?
Cause B1                289                ?               ?
```

⚠️ **These two numbers are not directly comparable.** The earlier figures used a different class space and, in Symptom's case, a different detector. Report the delta as descriptive, not as a measurement of improvement.

---

## Provenance

```
evidence_type            expert_inference
tier                     silver-medium maximum
label_generation_method  semantic_catalogue_code_matching_v1
embedding_model          paraphrase-multilingual-MiniLM-L12-v2
anchor_source            sap_catalog_as_class_space
evaluation_independence  derived_from_rules
class_space              profile_scoped | catalogue_wide
```

⚠️ **Note on `anchor_source`.** The catalogue is being used here as the **class space**, not as a detector against raw text. That is a different use from the one that over-generated in G1.1d, and the field value should make the distinction explicit.

---

## Constraints

- Report only. No denominator change, no promotion, no F6 update.
- Never aggregate across paths.
- Freeze the threshold before looking at results.
- `anchor_source` and `class_space` as literal fields on every row.
- Sanitised versioned outputs. No raw text, no PII.
- Leakage rows from G2.0b enter masked.

---

## Deliverables

```
g20j_catalogue_coverage_sanitized.csv       per target · path · class space
g20j_no_applicable_report_sanitized.csv     the uncovered share
g20j_wmep_contrast_sanitized.csv            descriptive delta
g20j_memo.md
```

---

## Closure criteria

- Both targets measured against both class spaces, all three paths
- `no_applicable_rate` reported per target and path
- `top_code_share` flagged above 30%
- Threshold declared and frozen before results
- Contrast against the WMEP figures reported as descriptive only

---

## What this unblocks

```
F6              final denominator update for Symptom and Cause
G2 scoping      whether either target has enough signal to train
```

**A low result here is a finding about catalogue expressiveness, not a shortfall of the corpus.** The Activity round already established that a client catalogue can cover very little of what its own technicians record.


ADDENDUM — G2.0j · Residual characterisation

Beyond counting non-coverage, characterise what the residual contains.
Text the catalogue cannot express is not noise to discard — it may be
a configuration gap on the client side.

───────────────────────────────────────────────────────────────
FIRST · partition the non-covered units
───────────────────────────────────────────────────────────────

`no_applicable_rate` must be computed over an explicit partition, not
over an implicit judgement of whether the text "describes the target's
subject matter". Two distinct outcomes:

  no_anchor_at_all      no catalogue code above threshold AND no
                        anchor to domain vocabulary
                        → the text probably does not address the target

  no_catalogue_code     anchors to domain vocabulary but no catalogue
                        code above threshold
                        → the text addresses the target; the catalogue
                          cannot express it

Report both separately. Only the second is the configuration gap.

Domain vocabulary for this partition:
  Symptom   ZEUS detection symptom + WMEP effects as reference only
  Cause     WMEP failure causes

⚠️ Use domain vocabulary here strictly as a presence test — does the
text talk about this subject at all. It is not the class space; the
catalogue is.

───────────────────────────────────────────────────────────────
THEN · characterise the no_catalogue_code set
───────────────────────────────────────────────────────────────

  1. Extract candidate terms from their text
     same method as G2.0c · semantic_normalisation_v2

  2. Group into concepts by semantic similarity
     report concept count and frequency distribution

  3. Report the top 20 concepts with their unit counts

  4. Flag any concept appearing in more than 5% of this set

Deliverables:
  g20j_noncoverage_partition_sanitized.csv
  g20j_residual_concepts_sanitized.csv

Why: if the gap concentrates in a handful of recurring concepts, that
is a concrete recommendation — either the catalogue lacks those codes,
or the profile assignment excludes codes the corpus needs.

Report only. No promotion, no denominator change.
