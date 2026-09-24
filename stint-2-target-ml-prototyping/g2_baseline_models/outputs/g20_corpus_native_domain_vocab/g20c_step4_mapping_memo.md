# G2.0c Step 4 - Concept to Catalogue Candidates

Input: the unchanged Step 3b vocabulary (24 Activity, 43 Object Part, 4 ambiguous,
185 unassigned). Activity uses catalogue A; Object Part uses B in the same Wind
workbook used by G1.1. The 189 unresolved concepts are retained as held in the
256-row status register, and are not declared catalogue gaps.

## Method and confidence

Encode canonical labels and unique catalogue descriptions with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
Embedding normalization lowercases, splits punctuation, and collapses spaces only.
A separate lexical guard uses the declared morphology table and singular/plural
normalization. Activity requires shared action support; Object Part requires the
last recognized component head from the canonical label. The guard is
analyst_authored_after_candidate_diagnostics, retained in the manifest. It removes
related-but-incompatible proposals such as crane -> rotor and stack -> cpu.
Query only the assigned target's catalogue; accept every compatible description
with cosine >= 0.6 and within 0.08 of the best compatible
description for that concept.
There is no top-k truncation. Exact normalized descriptions score 1. Tiers are
candidate_strong >= 0.8, candidate_medium >= 0.7, and
candidate_weak >= 0.6. These are analyst-defined retrieval settings,
not calibrated probabilities, evaluated accuracy, or validated mappings.

All composite keys (catalogue, code group, code) for each retained description
are preserved. Group alternatives require asset/profile context; a high score
does not resolve that context. Source sheet, row, and file hash are recorded.
One Activity source anomaly, A/PMKNFAN/PMKN, contains a cooling-system description
instead of an action and is explicitly excluded from retrieval.

## Results

     target catalogue  n_concepts  zero_candidates  one_candidate  multiple_candidates  candidate_edges  max_candidates_per_concept                              path  threshold  near_best_margin             evaluation_set_type
   Activity         A          24               16              0                    8              477                          86 concept_level_no_path_aggregation        0.6              0.08 not_evaluated_candidate_mapping
Object Part         B          43                9              3                   31              165                          15 concept_level_no_path_aggregation        0.6              0.08 not_evaluated_candidate_mapping

The edge table contains only actual candidates. The status register declares all
zero mappings. Assigned concepts with no candidate under this retrieval rule are
listed as candidate_catalogue_gap: this is not proof of catalogue absence.
Mapping uses canonical labels only; mixed clusters or unrepresentative labels
can cause missed or inappropriate candidates. No member text or evaluation
labels were used to broaden queries. Human/domain review is still required.
The lexical guard can miss synonyms, and candidate_catalogue_gap includes
retrieval failures: for example, a low score on setting does not establish that
the catalogue lacks a software/firmware setting adjustment entry. All rejected
description scores and gate reasons are retained for review. No similarity tier
establishes equivalence or validates the additional specificity of a catalogue code.

## Provenance and boundaries

Catalogue mapping carries expert_inference and anchor_source=domain_vocabulary.
The 13 Step 3b construction exclusions propagate to the status register and edge
rows; eligibility of other concepts remains not_established. Inputs and frozen
references are checked byte-for-byte unchanged. Mapping is stored separately;
no target, denominator, calibration, model, or Step 5 result is changed here.
Counts describe vocabulary concepts, not physical records or path coverage.
