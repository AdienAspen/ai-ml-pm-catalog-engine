# G2.0c — Corpus-Native Domain Vocabulary

**FSA BRIDGE / STINT_2 · Targets: Activity and Object Part**
Estimated: 2 days

**Release correction for v0.8.3:** current totals are 79,330 candidate path-terms,
24,825 filtered forms, and 24,405 grouped members. Earlier execution counts below
are historical. The release reconciliation at the end of this plan records the
restricted-variant removal and its limits. G2 remains open.

---

## Why this exists

`G1.2c` established that two targets have no domain vocabulary at all:

```
Activity     B1 1,215 · 100% sap_catalog · B1 top concept 832/1,215 = 68.48%
Object Part  B1 3,737 of 6,670 no-item orders · 100% sap_catalog · top 738
```

Step 5 scope correction: the previously quoted Activity 52.7% was 858/1,628
across paths, not B1. Frozen G1.2c outputs are not rewritten. Object Part's
historical 3,737 count applies only to the no-item subset, not all 10,749 orders.

The other three targets have externally sourced vocabulary — Damage from NREL GRD, Cause from WMEP, Symptom from ZEUS. Activity and Object Part have nothing, so the SAP catalogue did that work by default and over-generated.

**Root cause, from T8 in STINT_1.1:** the corpus lexicon was described in terms of the destination catalogue rather than built from the technician's own language. Catalogue entries are encoded descriptions; a long free-text record matches them by word accumulation, not by meaning.

**This step builds the missing layer from the corpus itself**, using the method already proven twice in this project: the OEM code dictionary in F5 and the lexical layer in T8.

---

## Objective

Produce a domain vocabulary for Activity and Object Part, extracted from the model-eligible corpus in the technician's register — then map it to the SAP catalogue, in that order.

The construction layer is kept separate from externally sourced reference evidence. External terms may improve out-of-vocabulary coverage only when their frozen provenance is explicit; they do not become corpus-native terms and do not contribute to corpus-frequency filters.

**Explicitly not a goal:** re-running G2.0, changing denominators, promoting candidates, or assigning catalogue codes to records.

---

## What the blind sample already told us

The `G1.1e` review of 20 orders found real components the current 145 catalogue concepts do not capture:

```
yaw ring · torque arm bushing · pitch manifold accumulator
hub safety pilot valve · deck hatches · lift guide arm
smoke detector · M12 connector · MSC/LSC stack · PMG encoder
bottom cover · generator bearing DE/NonDE
```

**These are not exotic.** `yaw ring` appeared three times in twenty orders and anchored to nothing.

**Expect the extraction to surface many more.** Twenty orders is 0.2% of B1.

---

## Step 1 — Extraction

Build two universes for B1, Path A and B2 separately:

```
descriptive_full_corpus               statistics only
model_eligible_construction_corpus    vocabulary construction
```

The construction corpus excludes `evaluation_set_v1`, current held-out rows, and exact text duplicates of excluded evaluation content. Vocabulary candidates are emitted only from this second universe.

```
source fields       descriptionExtended · reason
                    as declared in the F0 routing table
normalisation       semantic_normalisation_v2 before extraction
                    mask tags · clean · split CamelCase
                    strip alarm codes · expand abbreviations
unit                n-grams of 1 to 3 words
target              unassigned in Step 1
```

⚠️ **Normalisation first.** In `T5.1b2.X` the same operation recovered 366 terms unnormalised and 1,827 normalised. Extracting from raw text repeats a known error.

⚠️ **Mask leakage first.** Extract from the G2.0b-masked corpus. The 13 known serialized target-assignment rows must already be masked before normalization and n-gram emission.

⚠️ **Do not assign a target during extraction.** An n-gram such as `replace yaw ring` can contain Activity and Object Part signal. The literal construction method is `corpus_extracted_neutral_ngram_target_assignment_deferred_to_semantic_grouping`.

**Output:** neutral raw candidate term list with frequency by path, plus separate full-versus-eligible retention diagnostics.

### Step 1b — External reference augmentation

When a domain term is absent from the construction corpus only because all observed occurrences belong to the evaluation exclusions, it may enter from a frozen external reference source. It must be stored separately with `evidence_type=reference_evidence`, must not use evaluation text, and must not count toward corpus frequency.

For the B2 gate, frozen F1c2 evidence admits `bearing failure`, `crack`, and `cracking`. `main bearing failure`, `casting`, and `hub casting` remain held because exact frozen support was not found. The evaluation set remains untouched and no further B2 recovery is planned.

---

## Step 2 — Filtering

```
frequency floor     evaluate separately by path; never use one global floor
                    B1_RELATIONAL >= 3 eligible units
                    B2_WORKBOOKS >= 2 eligible units
                    PATH_A >= 1 eligible unit
stopword removal    generic maintenance verbs that carry no
                    discrimination: "work", "check", "done"
length              keep 1–3 words · discard fragments
```

**Report how many terms survive each filter.** In T8, 10,639 observed terms reduced to 359 concepts — the reduction curve is itself informative.

Path-specific treatment is mandatory: Path A retains its top term forms but lost more than half of its descriptive frequency for 74 of the top 100 terms after evaluation exclusion. Its eligible frequencies show existence, not corpus prevalence. External reference terms are excluded from every frequency-based reduction count.

The generic filter removes a phrase only when every token is generic. A mixed phrase such as `check yaw ring` survives because it still carries domain signal. One-character fragments are removed without attempting target assignment.

---

## Step 3 — Grouping into concepts

**This is the step T8 never completed**, and the reason its `concept_id` ended up identifying rows rather than concepts.

```
group surface variants into one canonical concept

  "yaw ring" · "yaw-ring" · "yawring" · "anillo de yaw"
  → concept: YAW_RING

  "air filter" · "converter air filter" · "inlet filter"
  → concept: AIR_FILTER
```

**Method:** semantic similarity between terms, not string distance. String grouping already failed in T8 — it reduced only 3.16%.

**Each concept carries:**

```
concept_id          stable · referenceable by code
canonical_label     the preferred form
surface_variants    all observed forms, with frequency
target              Activity or Object Part
```

⚠️ **Do not map to SAP yet.** Grouping happens in the technician's register. Mapping comes after.

### Step 3 execution record — 2026-09-21

The 24,841 filtered forms were embedded with
`paraphrase-multilingual-MiniLM-L12-v2` and grouped with MiniBatchKMeans
over normalized semantic embeddings. Candidate values `k=256, 384, 512, 768`
were compared on a deterministic 3,000-term cosine-silhouette sample. `k=256`
was selected as the highest-silhouette candidate passing the global cluster and
target-by-path surface-concentration gates.

```
concepts                                256
grouped path-term rows               24,421
unresolved or low-similarity rows       420

Activity concepts                         21
Object Part concepts                      40
ambiguous concepts                         4
unassigned concepts                      191
```

Target assignment occurred after grouping. It used frozen ZEUS/IEC/F1c2
reference scopes plus declared analyst-authored generic action and component-head
lexicons. Object Part was not used as a residual class. G2.0 prototypes and
evaluation text were not reused.

The Step 3 blocking metric is `surface_variant_share`, which directly measures
whether grouping created an over-broad concept. All six Activity/Object Part
target-by-path gates pass; the maximum is 23.62%. The separately reported
`unit_mention_weight_share` is diagnostic only because overlapping n-grams can
count the same physical record more than once. It exceeds 30% in three cells,
including Object Part B2 (`blades` variants), and remains an explicit warning.
Exact `physical_record × target` concentration is deferred to the unit-level
coverage pass in Step 5.

The sanitisation assertion found zero operational-entity tokens in the Step 3
concept, member, and decision outputs. No SAP mapping, denominator change,
candidate promotion, model training, or G2.0 rerun occurred.

A deterministic diagnostic review of 10 unassigned concepts found five correctly
conservative rejections, four recoverable target-support gaps (three Activity and
one Object Part), and one mixed cluster requiring a split. This sample is not a
prevalence estimate. The result argues against lowering thresholds globally:
bounded anchor/support expansion may recover coherent concepts, while broad
relaxation would promote the largest noise clusters.

### Step 3b execution record - 2026-09-23

Step 3b kept all 256 clusters and the global target thresholds frozen. Only the
191 concepts previously marked `unassigned` were eligible for reassignment. The
bounded lexical families came from the four recoverable diagnostic concepts and
carry `construction_method=derived_from_corpus_inspection`; they are stored
separately from all externally transcribed anchors.

An initial audit rejected bare `set` as an expansion token after it incorrectly
promoted the hardware concept `screws` to Activity. The accepted expansion uses
only the more specific observed forms. The final six promotions were inspected:
three Activity concepts and three Object Part hardware concepts.

```
                         before   after   delta
Activity                     21      24      +3
Object Part                  40      43      +3
assigned total               61      67      +6
ambiguous                     4       4       0
unassigned                  191     185      -6
```

Maximum blocking surface concentration decreased from 23.62% to 23.38%. All six
target-by-path gates remain below 30%. Clusters were not rebuilt, thresholds were
not lowered, and 13 reviewed concepts are registered as ineligible for future
Activity/Object Part evaluation because they informed instrument construction:
the original 10-concept diagnostic sample plus `screws`, `bolts cim`, and `box`
inspected during Step 3b QA.

---

## Step 4 — Map to SAP catalogue

Only now, and as a separate artefact:

```
concept_id → zero, one, or many candidate catalogue codes
             with match confidence
             with tier
```

**Keep the two layers separate in storage.** The domain vocabulary is one artefact; the mapping to catalogue is another. Collapsing them recreates exactly the defect this step exists to fix.

**Concepts with no catalogue candidate are a finding, not a failure** — `G1.1e` already identified 24 likely components with no code in Wind Catalog B. Register them as `candidate_catalogue_gap`, never as a definitive catalogue gap.

### Step 4 execution record - 2026-09-23

The active input is `g20c_domain_vocabulary_step3b_sanitized.csv`. All 256
concepts have a mapping-status row: 24 Activity and 43 Object Part were evaluated;
185 unassigned and 4 ambiguous concepts remain explicitly held. The vocabulary,
members, and 13 construction exclusions remain byte-for-byte unchanged.

Activity maps to catalogue A; Object Part maps to B in the Wind catalogue workbook
used by G1.1. Each candidate retains its composite key (catalogue, code group,
code), source sheet, source row, similarity, tier, and unresolved profile context.
Repeated descriptions across groups remain distinct candidates; there is no
top-k truncation or automatic choice of an asset's catalogue profile.

The retrieval rule requires compatible action/component lexical support,
cosine similarity >= 0.60, and distance <= 0.08 from the best compatible
description. Tiers are candidate_strong >= 0.80, candidate_medium >= 0.70,
and candidate_weak >= 0.60. Similarity is not a calibrated probability or
validated mapping. The mapping-only lexical guard was authored after inspecting
candidate diagnostics, with its morphology and head lists recorded in the
manifest. It does not alter Step 3/3b targets or extraction.

| Target | Concepts | Zero candidates | One candidate | Multiple candidates | Edges |
| --- | ---: | ---: | ---: | ---: | ---: |
| Activity | 24 | 16 | 0 | 8 | 477 |
| Object Part | 43 | 9 | 3 | 31 | 165 |

These are concept counts, not record denominators or path coverage. The 25 zero
cases are candidate_catalogue_gap under the declared method, with explicit
reasons. Some reflect retrieval limitations or insufficient canonical labels:
for example, `setting` does not pass despite a related software/firmware
adjustment description in the catalogue. Absence of a candidate is not proof of
catalogue absence. Canonical-label-only matching and the lexical guard can miss
synonyms. All description scores and rejection reasons remain auditable.

One source anomaly (A/PMKNFAN/PMKN, a cooling-system description in the activity
catalogue) is retained in the source register and excluded from retrieval.
Candidate mapping requires domain review, including component specificity and
asset profile selection. No denominator, independent label, or Step 5 metric
was changed by this pass.

---

## Step 5 — Coverage report

```
per target, per path:
  units with at least one domain-vocabulary anchor
  units with only sap_catalog anchor
  units with no anchor
  distinct concepts matched
  top concept share  ← flag if above 30%
```

**Contrast against the catalogue-only baseline:**

```
                        historical catalogue    domain vocabulary
Activity B1 (10,749)                    1,215                7,606
top concept share                    68.48%               37.27%
Object Part B1 no-item (6,670)           3,737                4,672
```

⚠️ **`top_concept_share` above 30% flags possible over-breadth for review.**
It does not by itself distinguish a generic cluster from a genuinely frequent
concept. Building our own vocabulary does not make us immune to over-generation.
The historical and current methods differ; the table is a descriptive contrast,
not an estimate of corrected labels, precision, or newly admitted units.

### Step 5 execution record - 2026-09-23

The frozen Step 3b vocabulary is applied as exact contiguous surface-variant
matches after G2.0b masking and `semantic_normalisation_v2`. The shared vocabulary
uses only construction-derived terms; it is applied to each path separately.
No phrase spans original source segments. Each concept counts at most once per
unit and target. All 67 assigned concepts participate, irrespective of Step 4
mapping success; 189 ambiguous/unassigned concepts are not detectors.

The paired catalogue comparator uses frozen lexical-layer-v2 high-band concepts
with SAP ownership, the same normalization, and the same units. It is not a
replay of historical semantic admissions. `anchor_source` is literal on hit rows;
its SAP provenance is explicitly derived from frozen owner/source/namespace.

Full-corpus results below are statistics only. Domain includes units with both
sources, so `domain + SAP only + neither = universe` in each row.

| Target | Path | Universe | Domain | SAP only | Neither | Domain concepts | Top share | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---|
| Activity | B1 | 10,749 | 7,606 | 3 | 3,140 | 24 | 37.27% | FLAG |
| Activity | B2 | 1,857 | 213 | 0 | 1,644 | 19 | 20.66% | within limit |
| Activity | Path A | 362 | 321 | 0 | 41 | 20 | 60.44% | FLAG |
| Object Part | B1 | 10,749 | 7,668 | 891 | 2,190 | 43 | 20.33% | within limit |
| Object Part | B2 | 1,857 | 353 | 152 | 1,352 | 31 | 31.73% | FLAG |
| Object Part | Path A | 362 | 289 | 16 | 57 | 29 | 46.37% | FLAG |

`top_concept_share` uses distinct concept-matched units divided by units with
at least one domain anchor in the same target/path/universe. It is not a share
of n-gram occurrences or of summed concept mentions. The four flagged leaders
are `inspection` (Activity B1), `annual maintenance` (Activity Path A), `blade`
(Object Part B2), and `motors` (Object Part Path A). Thresholds and clusters were
not adjusted to remove these flags.

The eligible-construction view is separate. B1 has 6,680 Activity-anchored and
6,459 Object-Part-anchored units out of 9,263. Eligible top shares are 41.35%
and 22.98%, respectively. Path A still has only 159 construction units; B2 has
1,478. The same four concentration cells are flagged in that view.

For the 6,670 no-item B1 orders, domain coverage is 4,672. The same-normalization
SAP comparator matches 4,207; the historical detector matched 3,737. Those are
different methods, not a silent denominator revision. Historical/domain overlap
is 3,190: 547 historical-only, 1,482 domain-only, and 1,451 neither. None of these
categories demonstrates label correctness or a catalogue artefact by itself.

Integrity checks reconciled all 13 masked units, all 10,900 eligible keys, and
all 24,421 frozen path-term member frequencies. Seven focused tests passed.
SHA-256 checks verified 216 upstream input files unchanged. No response labels
were used. The 13 construction-reviewed concept exclusions remain registered;
unit exposure is recorded without changing existing evaluation sets. No raw
source text, site names, asset identifiers, or new visible-text sample is emitted.

Step 5 is executed with four open concentration findings. Lexical coverage is
not an independent evaluation of concept coherence, component presence, or SAP
coding correctness. No F6 change, candidate promotion, training, or G2 closure
is authorized by this report.

Additional Step 5 artefacts include the unit/concept hit ledger, separate
full/eligible coverage, concept concentration, no-item-subset comparison,
historical scope reconciliation, frozen-frequency audit, source hashes, and
`g20c_step5_coverage_manifest.json`. `g20c_memo.md` records method and limitations.

---

## Provenance

```
evidence_type            reference_evidence     for extracted terms
                         reference_evidence     for frozen external terms
                         expert_inference       for concept grouping
                         expert_inference       for catalogue mapping
anchor_source            domain_vocabulary
extraction_method        corpus_native_neutral_ngram_extraction_v2
normalisation_pipeline   semantic_normalisation_v2
construction_method      corpus_extracted_neutral_ngram_
                         target_assignment_deferred_to_semantic_grouping
```

⚠️ **`anchor_source` must be a literal field.** `G1.2c` found it absent everywhere and had to derive it from vocabulary ownership. Do not reproduce that gap.

---

## Constraints

- Report and build only. No denominator change, no re-run of G2.0, no promotion.
- Sanitised versioned outputs — concept labels are domain terms, not operational values, but surrounding text remains sensitive.
- Keep domain vocabulary and catalogue mapping as separate artefacts.
- Keep corpus-native candidates and external reference augmentation as separate artefacts.
- Do not reuse the prototypes from G2.0 as seeds. Those were analyst-authored; this extraction must come from the corpus.
- Do not learn terms from evaluation text. Externally sourced terms must point to a frozen reference artefact.
- Use path-specific frequency thresholds in Step 2; Path A frequencies are not comparable with B1 or B2 after exclusions.

---

## Deliverables

```
g20c_candidate_terms_sanitized.csv          Step 1 · raw with frequency
g20c_external_reference_augmentation_sanitized.csv
                                             Step 1b · external layer only
g20c_external_reference_augmentation_decisions_sanitized.csv
                                             Step 1b · admitted/held register
g20c_filter_reduction_report_sanitized.csv  Step 2 · survival per filter
g20c_filtered_terms_sanitized.csv          Step 2 · input to grouping
g20c_filter_decisions_sanitized.csv        Step 2 · one decision per term
g20c_step2_filter_rules_sanitized.csv      Step 2 · frozen filter rules
g20c_domain_vocabulary_sanitized.csv        Step 3 · one row per concept
g20c_concept_members_sanitized.csv          Step 3 · surface variants by path
g20c_step3_cluster_selection_sanitized.csv  Step 3 · candidate-k audit
g20c_step3_concentration_by_target_path_sanitized.csv
                                             Step 3 · concentration diagnostics
g20c_step3_grouping_summary_sanitized.csv   Step 3 · target × path summary
g20c_step3_semantic_grouping_memo.md        Step 3 · method and boundaries
g20c_step3_unassigned_diagnostic_sample_sanitized.csv
                                             Step 3 · 10-concept review
g20c_step3_unassigned_diagnostic_memo.md     Step 3 · diagnostic decision
g20c_domain_vocabulary_step3b_sanitized.csv Step 3b · bounded target view
g20c_concept_members_step3b_sanitized.csv   Step 3b · member target view
g20c_step3b_anchor_expansion_sanitized.csv  Step 3b · corpus-derived anchors
g20c_step3b_construction_exclusions_sanitized.csv
                                             Step 3b · evaluation exclusions
g20c_step3b_assignment_changes_sanitized.csv
                                             Step 3b · six promotions
g20c_step3b_before_after_target_counts_sanitized.csv
                                             Step 3b · count comparison
g20c_step3b_before_after_concentration_sanitized.csv
                                             Step 3b · gate comparison
g20c_step3b_bounded_anchor_expansion_memo.md Step 3b · method and decision
g20c_vocabulary_to_catalogue_map_sanitized.csv  Step 4 · separate artefact
g20c_step4_mapping_register_sanitized.csv   Step 4 · all 256 concept states
g20c_step4_catalogue_source_register_sanitized.csv
                                             Step 4 · composite keys and anomaly
g20c_step4_description_scores_sanitized.csv Step 4 · accepted/rejected scores
g20c_step4_mapping_summary_sanitized.csv    Step 4 · 0/1/N counts per target
g20c_step4_mapping_manifest.json           Step 4 · settings and hashes
g20c_step4_mapping_memo.md                 Step 4 · method and limitations
g20c_catalogue_gaps_sanitized.csv           concepts with no code
g20c_coverage_contrast_sanitized.csv        Step 5 · vs catalogue baseline
g20c_memo.md                                narrative and method
```

---

## Closure criteria

- Domain vocabulary built for both targets from corpus text
- Concept grouping demonstrated — many surface variants per concept, not one concept per row
- Catalogue mapping in a separate artefact
- Catalogue gaps registered
- Coverage contrast against catalogue-only baseline reported
- `top_concept_share` reported and flagged where above 30%

---

## What this unblocks

```
Activity      currently 100% catalogue-anchored · no real volume known
Object Part   currently split between lookup and catalogue artefact
F6            three targets still marked post_catalog_review_required
G2.1 scoping  cannot be decided on inflated figures
```

**Until this closes, the free-text volume of Activity and Object Part remains unknown.**

---

## Release sanitization and reconciliation - v0.8.3

The pre-publication gate found 39 restricted path-term candidates in six CSVs,
repeated across 142 cells. The earlier fixed-token check missed concatenated
tokens and a site-name family. Original artefacts were preserved only in ignored
internal storage with directory mode 700 and file mode 600.

`restricted_lexical_substring_exclusion_v1` now consults the local restricted-term
configuration and excludes whole offending n-gram windows before candidate
emission. It does not delete tokens and create new adjacent phrases. It is a
separate lexical safety rule: `semantic_normalisation_v2`, semantic hashes and
evaluation/heldout construction exclusions do not change. The guard fails closed
when the local configuration is missing or empty.

| Layer | Before | Current | Change |
|---|---:|---:|---:|
| Candidate path-terms | 79,369 | 79,330 | -39 |
| Filtered path-terms | 24,841 | 24,825 | -16 |
| Grouped members | 24,421 | 24,405 | -16 |
| Concepts | 256 | 256 | 0 |
| Assigned concepts | 67 | 67 | 0 |

Candidate removals are B1 18 and Path A 21. All 16 removed cluster members are
from Path A: 15 were unassigned and one belonged to Object Part / brake. No B2
candidate or member was removed. Step 2 retains B1 22,371; B2 684; Path A 1,770.

This is bounded post-fit member pruning, not a clean re-clustering. The original
concept IDs, canonical labels, fitted centers and similarity geometry remain
traceable. Member summaries and concentration are recalculated. Historical
silhouette and selection statistics are marked as pre-release fit measurements;
they must not be represented as measurements of a new sanitized fit.

Step 3b is revalidated without lowering thresholds. All 67 assignments and the
13 construction-reviewed concept exclusions remain unchanged. Step 4 is rerun
with updated input hashes; the candidate mapping is unchanged. Step 5 is rerun
against the masked corpus. The release coverage reconciliation gives explicit
before/after values per target, path and universe, including review-exposure flags.

One Path A unit stops matching a reviewed concept after pruning; its historical
instrument-exposure exclusion is explicitly retained for both targets in
`g20c_release_preserved_evaluation_exclusions_sanitized.csv`. Future evaluation
must union this ledger with existing exclusions. Cleanup never restores eligibility.

The publication gate scans every G2.0c output against the local restricted-term
policy. Exact frozen catalogue-code collisions are recorded separately, not
treated as raw operational names. The legacy whole-repository checker still
flags pre-existing project titles/source locators and catalogue substrings; a
scoped pass does not imply that historical repository findings were repaired.

Authoritative release artefacts:

- `g20c_release_removed_terms_sanitized.csv`: hash-only removal ledger.
- `g20c_release_count_reconciliation_sanitized.csv`: counts by layer and path.
- `g20c_release_coverage_reconciliation_sanitized.csv`: Step 5 before/after.
- `g20c_release_hash_reconciliation_sanitized.csv`: original/current hashes.
- `g20c_release_sanitization_manifest.json` and `g20c_release_sanitization_memo.md`.
- `g20c_release_gate_sanitized.json`: scoped output-publication audit.

The checkpoint covers G2.0c Steps 1-5 and this repair. It does not change F6,
evaluation labels or training scope, and does not close G2 or clear its four
unit-concentration findings. One annotated milestone tag is used, not one tag
per intermediate step.
