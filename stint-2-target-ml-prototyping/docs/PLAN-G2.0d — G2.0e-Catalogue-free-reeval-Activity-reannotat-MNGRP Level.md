# G2.0d + G2.0e — Parallel Steps Before Phase G2

**FSA BRIDGE / STINT_2**
Both run in parallel. Neither blocks the other.

```
G2.0d   re-evaluate Damage · Cause · Symptom against external vocabulary
G2.0e   re-annotate Activity at MNGRP family level
```

---

# G2.0d — Catalogue-Free Re-evaluation

**Targets: Damage · Cause · Symptom** · Estimated: 1 day

---

## Why this exists

`G1.2c` established that three targets carry catalogue-inflated denominators:

```
Damage B1    815 of 1,263 · sap_catalog     65%
Cause B1   1,203 of 1,250 · sap_catalog     96%
Symptom      no catalogue anchoring         clean by construction
```

`G2.0c` fixed Activity and Object Part by building corpus-native vocabulary. These three do not need that — **they already have authoritative external vocabulary** brought in by the research tracks:

```
Damage    NREL GRD + per-subsystem failure mode vocabularies
Cause     9 WMEP failure causes
Symptom   ZEUS detection symptom + 8 WMEP failure effects
```

**What they need is re-measurement against that vocabulary, with the catalogue removed as an anchor source.**

Without this, three targets reach Phase G2 with figures we already know are inflated, and any training decision rests on false numbers.

---

## Objective

Recompute anchoring for the three targets using **only domain vocabulary**, and report the real volume per target per path.

**Out of scope:** building new vocabulary, changing thresholds, training, promoting candidates.

---

## Method

Mirror the G2.0c Step 5 coverage procedure exactly, so results are comparable.

```
anchor sources     domain_vocabulary only
                   sap_catalog excluded as anchor
corpus             model_eligible_construction_corpus
                   same exclusions as G2.0c
normalisation      semantic_normalisation_v2
embedding          paraphrase-multilingual-MiniLM-L12-v2
```

⚠️ **Do not re-derive the vocabulary.** Use what F1c2 materialised:

```
g20c external reference augmentation artefacts
WMEP causes · WMEP effects · NREL GRD failure modes
ZEUS detection symptom categories
```

If a vocabulary is thin, that is a finding. Report the concept count per target before running coverage.

---

## Required output — per target, per path

```
units_with_domain_anchor
units_with_sap_catalog_only     reported, not counted as signal
units_with_no_anchor
distinct_concepts_matched
top_concept_share               flag above 30%
```

**Plus the contrast against current F6 figures:**

```
                    F6 current    domain-only    delta
Damage B1              1,263            ?          ?
Cause B1               1,250            ?          ?
Symptom B1             1,827            ?          ?
```

⚠️ **Expect Cause to drop sharply.** With 96% catalogue-anchored and only 9 WMEP causes available, the real figure will be much lower. **That is the point of the exercise.**

Symptom should barely move — it never had the defect.

---

## Constraints

- Report only. No F6 update in this step.
- Never aggregate across paths.
- `anchor_source` as a literal field on every evidence row.
- Sanitised versioned outputs.

---

## Deliverables

```
g20d_domain_only_coverage_sanitized.csv
g20d_f6_contrast_sanitized.csv
g20d_vocabulary_inventory_sanitized.csv    concepts available per target
g20d_memo.md
```

---

## Closure criteria

- Three targets measured against domain vocabulary only
- Contrast against F6 reported with delta
- `top_concept_share` flagged where above 30%
- Vocabulary thinness reported where it limits coverage

---

# G2.0e — Activity Re-annotation at MNGRP Level

**Target: Activity** · Estimated: 1–2 days

---

## Why this exists

Activity failed in G0.3 with **κ = −0.018** against 0.96 raw agreement. The cause was not the annotators — **the question was wrong**.

```
asked        "is there an activity present?"
corpus       work orders · virtually every record describes activity
result       98% one class · agreement no better than chance
```

`G2.0c` confirms it from a second direction:

```
Step 4   8 Activity concepts map to ~60 catalogue codes each
Step 5   concentration 37.27% in B1 · `inspection` dominates
```

**The catalogue discriminates at a granularity the text does not reach.** The technician writes `replaced`; catalogue A distinguishes dozens of replacement types.

---

## Objective

Re-annotate Activity asking **which family** of activity, at `MNGRP` level, not whether activity is present.

**This is a new instrument, not a re-run.** Different question, different vocabulary, different protocol version.

---

## Protocol

Issue as **`g01-v2`, Activity section**. Do not modify `g01-v1` — it governs the three targets already frozen in `evaluation_set_v1`.

### Question

> *Which family of maintenance work does this text describe?*

### Controlled vocabulary — MNGRP families

Derive from catalogue A group level, cross-checked against ZEUS `maintenance measure`. Target 6–8 families, not dozens.

```
replacement      part or component replaced
repair           restored without replacement
inspection       checked · examined · borescope · audit
lubrication      greased · oil change · lubricant refill
adjustment       calibrated · setting changed · aligned
cleaning         cleaned · debris removed
troubleshooting  fault finding · diagnosis without resolution
installation     new equipment mounted · commissioned
multiple         more than one family, none dominant
not_applicable   no maintenance work described
abstain          cannot decide within these definitions
```

⚠️ **Confirm the family list against the actual catalogue A groups before annotating.** The list above is a working draft, not the final vocabulary.

### Tie-break rules to define before starting

```
replacement vs repair       part swapped or restored in place
inspection vs troubleshoot  routine check or fault-driven diagnosis
multi-family text           when does `multiple` apply
```

**Write these before the first annotation.** Undefined boundaries are what sank Damage.

---

## Sampling

```
source       Activity B1 only · Path A and B2 are non-viable by volume
size         300 records
overlap      25% for inter-annotator agreement
design       simple random sample · NOT score-band stratified
```

⚠️ **Simple random, not stratified.** The Object Part B1 calibration produced sample-level metrics that needed population weighting. A random sample avoids that.

**Exclusions:** the 13 concepts excluded during G2.0c Step 3 and 3b diagnostics must not appear.

---

## Annotators

```
annotator_01   Claude Opus 5 · medium effort
annotator_02   different model family · GPT 5.6 or equivalent
```

⚠️ **Scope restriction, verbatim in the prompt:** no scripts, no regex, no automated rules. Read each row, judge each row. Two batches were rejected in this project for exactly that.

**Deliver the package pasted as text, not read over SSH.** Both rejected batches broke on file reading.

---

## Registration

```
protocol_version             g01-v2
evaluation_independence      independent
label_generation_method      blind_llm_annotation
evaluation_role              evaluation          ← not diagnostic
sampling_design              simple_random
eligible_for_final_heldout   true
```

**This one can be a real held-out set**, unlike the Object Part calibration package — because the sampling is random.

---

## Verification before accepting any batch

```
row count matches package exactly
no duplicate annotation_id
no annotation_id outside package range
all values within controlled vocabulary
abstention rate reported, not assumed zero
```

**Reject the whole file on any failure. Do not patch.**

---

## Deliverables

```
g01-v2_activity_mngrp_protocol.md
g20e_activity_mngrp_sample_manifest_sanitized.csv
g20e_activity_mngrp_responses_annotator_01.csv
g20e_activity_mngrp_responses_annotator_02.csv
g20e_activity_mngrp_agreement_sanitized.csv    κ · confusion matrix
g20e_memo.md
```

---

## Closure criteria

- `g01-v2` Activity section written with tie-break rules before annotating
- Family vocabulary confirmed against catalogue A groups
- 300 records annotated by two annotators from different model families
- κ and confusion matrix reported
- Class distribution reported — flag if any family exceeds 40%

**If κ remains near zero at family level, Activity is not discriminable in this corpus. That is a valid finding.**

---

# What both unblock

```
F6 final update          denominators free of catalogue inflation
Phase G2 scoping         which targets have enough real signal to train
```

**Until both close, only Object Part B1 has a verified, catalogue-free, concentration-passing figure.**
