# G2.0b — Target Leakage Quantification

**FSA BRIDGE / STINT_2 · Blocking sub-step before any calibration**
Estimated: half a day for the count · scope of remediation decided by the count

---

## What was found

During Object Part B1 annotation, annotator 01 reported that several CMS rows contain, inside the visible text itself, the literal catalogue assignment the model is meant to predict:

```
Object Part: Nacelle / Main generator - 265 - Bearing DE
```

A concrete before/after exists. Record `G20-B1-OBJ-R2-0188`:

```
before masking   text contained the assignment
                 → component_identified

after masking    text reduced to a repeated CMS header plus "GnDe"
                 → abstain
```

**The annotator's decision changed from decidable to undecidable once the assignment was removed.** That is direct evidence the leakage was operating on at least one record.

---

## Why this blocks everything downstream

This is **feature leakage**, not label leakage. The answer is written inside the model's own input.

```
an embedding reading "Object Part: ... Bearing DE"
anchors perfectly to "bearing" and returns high confidence

from the outside, the model appears to work very well
```

Consequences, all currently unmeasured:

- **G2.0 ran on text containing the leakage.** Every anchoring result, catalogue and prototype alike, may be inflated.
- **The catalogue-vs-prototype comparison is contaminated on both sides.** Neither figure is clean.
- **`evaluation_set_v1` may contain leaked rows.** If so, any metric computed against it is overstated.
- **Object Part B1 calibration cannot proceed.** The 375 annotations were made on the masked package, while the G2.0 corpus is unmasked. Calibrating one against the other compares two different things.

---

## Objective

Quantify the leakage, decide whether it is material, and route the affected rows to the deterministic path.

**Explicitly not a goal:** re-running G2.0 unless the count justifies it.

---

## Step 1 — Count · this alone decides the rest

Scan the **full corpus**, all three paths, not only admitted units.

### Pattern to search

Do not search only for `Object Part:`. Search the **generic form**:

```
[Target label] : [value]
```

Check for all seven targets and their common variants:

```
Object Part · ObjectPart · Object_Part
Damage · Schadensbild
Cause · Ursache
Activity · Maßnahme
Symptom
Functional Location · FLOC · TPLNR
Activity Type · MAT · ILART
```

**If one target label leaked into the text, others may have too.** The CMS row that triggered this carried the full catalogue assignment, not just one field.

### Required output

```
rows_with_leakage            total · by path · by target label found
pct_of_corpus                by path
distribution_by_score_band   G2.0 score bands for those rows
rows_above_threshold         how many leaked rows are among
                             G2.0 assigned units, not abstained
rows_in_evaluation_set_v1    how many are in the frozen eval set
rows_in_annotation_packages  how many are in the 375 Object Part
                             annotations
```

⚠️ **`rows_above_threshold` is the line that decides.** Percentage of corpus can mislead: with near-total abstention in B1, the relevant denominator is small, so a handful of leaked rows may account for a large share of what actually got assigned.

---

## Step 2 — Materiality decision

Apply this rule and record the outcome:

```
0 leaked rows above threshold
  → not material for G2.0 · exclude and proceed

< 1% of assigned units
  → not material · exclude · note as limitation

1–5% of assigned units
  → marginal · exclude · document in G2.0 memo
     no re-run required

> 5% of assigned units
  → material · re-run G2.0 on the cleaned corpus
     redo the catalogue-vs-prototype comparison
```

**Report the decision explicitly.** Do not infer it.

**Separate check, independent of the above:** if any leaked rows are in `evaluation_set_v1`, that set must be cleaned regardless of materiality for G2.0. A contaminated evaluation set overstates every metric computed against it.

---

## Step 3 — Route leaked rows to the deterministic path

These rows do not belong in a classification problem. The answer is already there.

```
extract by regex  →  target label + catalogue value
                  →  parse into code and description
                  →  emit as deterministic lookup evidence
```

**Provenance for extracted rows:**

```
evidence_type            real_observed_label
extraction_method        regex_target_label_parse
anchor_source            structural_field_in_text
tier                     gold  pending validation of a sample
```

⚠️ **Validate a sample of 20 before promoting.** Confirm the parsed code matches the Wind Catalog and that the label corresponds to the target it claims.

**Benefit is twofold:** those rows resolve at full precision without a model, and the ML set is left clean of trivial cases that only inflated metrics.

---

## Step 4 — Mask in the remaining corpus

For rows that stay in the ML path, mask the leaked segment as already done in the annotation package:

```
[MASKED_OBJECT_PART_ASSIGNMENT]
[MASKED_<TARGET>_ASSIGNMENT]
```

**Do not delete the row.** The rest of the text may still carry usable signal — `R2-0194` retained `component_identified` after masking because the technician's closing text still named the components.

---

## Constraints

- Counting first. No re-run, no recalibration, no denominator change until Step 2 is decided.
- Sanitised versioned outputs. No raw text, no PII.
- Leaked values themselves are catalogue codes, not operational data, but treat the surrounding text as sensitive as always.
- Record the regex used, so the scan is reproducible.

---

## Deliverables

```
g20b_leakage_count_sanitized.csv           by path, target label, score band
g20b_leakage_materiality_decision.md       the rule applied and the outcome
g20b_leaked_rows_deterministic_evidence.csv  if Step 3 proceeds
g20b_masking_manifest_sanitized.csv        rows masked, pattern applied
g20b_leakage_memo.md                       narrative, regex used, sample
                                           validation of 20
```

---

## Closure criteria

- Leakage counted across all three paths and all seven target labels
- Materiality decision recorded against the stated rule
- `evaluation_set_v1` contamination checked and cleaned if present
- Leaked rows either routed to deterministic evidence or masked
- Regex documented and reproducible

**Nothing calibrated, nothing promoted, no denominator changed until this closes.**

---

## What this unblocks

```
Object Part B1 calibration   using the 375 annotations
F6 denominator update        post-catalogue, post-leakage
G2.1 scoping decision        is supervised training warranted at all
```

**Until this closes, no figure from the free-text section of the target map should be cited.**