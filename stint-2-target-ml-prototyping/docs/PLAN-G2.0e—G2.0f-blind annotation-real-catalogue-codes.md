# G2.0e + G2.0f — Blind Annotation Against Real Catalogue Codes

**FSA BRIDGE / STINT_2 · Protocol `g01-v2`**
One annotation round, two targets. Same annotators, same setup.

---

## Why this is different from earlier rounds

Previous annotation rounds asked whether information of a given type was present. This round asks **which code applies**, against the client's actual catalogue.

That became possible because the Catalog Profile narrows the answer space under `PMMUWW`:

```
Activity     1 group →  5 codes
Damage       9 groups → 94 destinations (grupo + código)
```

**Annotators choose from the client's real codes**, not from families we invented. The result is directly comparable to what a model will have to predict.

---

## Why both targets in one round

```
G2.0e   Activity  κ −0.018 in g01-v1 · the question did not discriminate
                  98% answered "activity present" in a work-order corpus
G2.0f   Damage    κ 0.196 in g01-v1 · boundaries were never operational
                  3,078 units with signal, precision never measured
```

Both need re-annotation, both use the same annotators and protocol. Running the setup twice costs more than running it once.

---

# Protocol `g01-v2`

Issue as a new version. **Do not modify `g01-v1`** — it governs Cause, Object Part and Symptom, already frozen in `evaluation_set_v1`.

---

## G2.0e — Activity

**Question:** *Which of these five activity codes best describes the work performed?*

### Controlled vocabulary

Take the **5 actual codes** from group `PMMUWW` in Catalog A. Present them with their catalogue descriptions, in the client's wording.

```
<code 1> · <description>
<code 2> · <description>
<code 3> · <description>
<code 4> · <description>
<code 5> · <description>
multiple        more than one applies, none dominant
none_applicable no maintenance work described
abstain         cannot decide within these definitions
```

⚠️ **Extract the codes and descriptions from the catalogue before writing the protocol.** Do not paraphrase them — annotators must see what SAP will store.

### Tie-break rules — write before annotating

```
work spanning two codes      when does `multiple` apply
inspection vs troubleshoot   routine check or fault-driven
work described but not done  planned vs performed
```

**Undefined boundaries are what sank Damage in v1.** Write these first.

---

## G2.0f — Damage

**Question:** *Which damage group applies, and within it, which code?*

### Two-level annotation

With 94 destinations, annotate in two steps:

```
step 1   which of the 9 groups applies
         ELE · EXT · FCH · FHY · INS · MAT · MEC · MIC · PRC
         with their catalogue descriptions

step 2   within that group, which code
         group sizes: 7 · 7 · 9 · 3 · 8 · 20 · 32 · 6 · 2
```

**Report agreement at both levels.** Group-level agreement may be high while code-level is low — that is itself a finding about achievable granularity.

### Inherited rule, non-negotiable

⚠️ **Damage is the physical process, not the observation.** `high temperature` is a symptom; `spalling` is damage. This is DELTA-0008 and it did not change.

### Tie-break rules — write before annotating

```
present damage vs future risk    "can lead to failure"
damage vs action                 "replaced worn bearing"
multi-class text                 which takes precedence
leak                             single operational rule
                                 seal leaking vs oil leak detected
```

**These four are the boundaries that produced κ 0.196.** Resolve them in writing before a single row is annotated.

---

## Sampling

```
source       B1 only · Path A and B2 non-viable by volume
size         300 unique units per target
overlap      25% for inter-annotator agreement
design       simple random sample · NOT score-band stratified
```

⚠️ **Simple random.** The Object Part calibration needed population weighting because it was stratified by score band. A random sample avoids that and can qualify as a real held-out set.

**Exclusions:**

```
Activity    the 13 concepts excluded during G2.0c Step 3 and 3b
Damage      none recorded · verify before sampling
Both        any unit already in evaluation_set_v1
```

**Arithmetic:** 300 unique units with 25% overlap = **375 responses per target**, not 300 from each annotator.

---

## Annotators

```
annotator_01   Claude Opus 5 · medium effort
annotator_02   different model family · GPT 5.6 or equivalent
```

⚠️ **Scope restriction, verbatim at the top of the prompt:**

> Your only permitted action is to read the assigned rows and emit one
> annotation per row, based on your own reading of each text against
> the definitions in this brief. You must not write, generate, or
> execute any script, code, regex, or automated rule to produce the
> annotations.

**Deliver the package pasted as text.** Two earlier batches broke on file reading over SSH.

---

## Package format

```
format       JSONL · one record per line
             immune to the unquoted-line-break failure
columns      annotation_id · text
             nothing else · no path, no score, no hint
text         PII redacted · full, never truncated
             leakage pattern masked per G2.0b
integrity    unique annotation_id verified by assertion
             declared row count matches actual
```

---

## Registration

```
protocol_version             g01-v2
evaluation_independence      independent
label_generation_method      blind_llm_annotation
evaluation_role              evaluation
sampling_design              simple_random
eligible_for_final_heldout   pending verification
```

⚠️ **`eligible_for_final_heldout` is confirmed only after checking** that these texts did not participate in building vocabulary, prototypes or thresholds. Activity texts did, via G2.0c — verify and exclude before declaring.

---

## Agreement metrics — not κ alone

Activity already showed the prevalence paradox: 0.96 raw agreement with κ ≈ 0.

**Report all of:**

```
raw agreement
Cohen's κ
per-class agreement
confusion matrix
Gwet's AC1
```

**A κ near zero does not by itself prove the corpus is indiscriminable.**

For Damage, report all five **at group level and at code level separately**.

---

## Verification before accepting any batch

```
row count matches package exactly
no duplicate annotation_id
no annotation_id outside package range
all values within the controlled vocabulary
abstention rate reported, not assumed zero
```

**Reject the whole file on any failure. Do not patch.**

---

## Deliverables

```
g01-v2_protocol.md                      both targets, tie-break rules
g20ef_sample_manifest_sanitized.csv
g20ef_responses_annotator_01.csv
g20ef_responses_annotator_02.csv
g20ef_agreement_sanitized.csv           all five metrics, both targets
g20ef_memo.md
```

---

## Closure criteria

- `g01-v2` written with tie-break rules **before** annotation begins
- Codes and descriptions extracted verbatim from the catalogue
- 300 units per target, two annotators, 25% overlap
- Five agreement metrics reported; Damage at both levels
- Class distribution reported · flag any class above 40%
- `eligible_for_final_heldout` verified, not assumed

**If Activity remains near zero at code level with only 5 options, that is a finding about the corpus and not a failure of the instrument.**
