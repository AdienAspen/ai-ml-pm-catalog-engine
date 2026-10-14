# G2.0d - Catalogue-free reference coverage

This execution addendum applies the approved committee corrections to G2.0d
only. G2.0e is not started, and F6 is not edited.

## Frozen method

1. Inventory complete frozen F1c2 sources, existing translation aliases,
   reference augmentation and ZEUS containers before reading corpus results.
2. Use exact contiguous lexical matching after G2.0b masking and
   semantic_normalisation_v2. No embeddings, similarity threshold, new synonyms,
   lemmatization, prototypes or term splitting. Preserve source-segment boundaries.
3. Retain source, subsystem, semantic level, evidence type and tier. A lexical
   match does not validate subsystem applicability or a SAP target assignment.
   ZEUS category definitions are not a populated technician-language lexicon.
4. Freeze registry, settings and source hashes before measurement. Fail on drift.
5. Report full_cleaned_corpus and model_eligible_construction_corpus separately
   for each target and path, with explicit evaluation/heldout exclusions.
6. Count each concept once per unit and target. Report domain-only, both,
   SAP-only and neither; SAP is a companion comparator, never positive signal.
7. Use the same frozen high-band SAP comparator selection as G2.0c Step 5.
   This comparator is not a replay of F6's historical semantic detectors.
8. Contrast F6 with identical unit membership per universe. If legacy text-row
   units cannot be related one-to-one to constituted events, retain the original
   F6 row/stratum and report the delta as unavailable, not zero or a subtraction
   of incompatible counts. Do not aggregate Path A Symptom strata.
9. B1 Symptom reason rows must reconcile in sequence and hash to physical orders.
   Also report reason-only coverage so field expansion is not mistaken for a
   detector effect. Historical F6 labels are used only to reconstruct membership,
   never to select vocabulary or tune the matcher.
10. Flag top_concept_share > 0.30 using distinct concept-matched units divided by
    units with at least one domain anchor in that same target/path/universe.

## Interpretation

The result is domain-supported volume or catalogue-free anchored volume, not
real volume, independent evaluation, precision, or SAP ground truth. No expected
direction of change is prescribed. Exact matching may miss real signal outside
the frozen lexical forms; counts do not establish the absence of that signal.

## Required artefacts

- g20d_vocabulary_inventory_sanitized.csv
- g20d_anchor_registry_sanitized.csv and g20d_freeze_manifest.json
- g20d_domain_only_coverage_sanitized.csv
- g20d_f6_contrast_sanitized.csv and F6 membership/reconciliation ledgers
- unit/concept hit ledgers, source breakdown, exclusion counts and g20d_memo.md

No training, new annotation, F6 admission, commit or push is part of this run.

## Pre-publication reconciliation amendment

The first attempt stopped before publishing measurements: F6 membership was
not a subset of the inherited Step 5 universe. Damage Path A includes 48
PATHA-NOTE-EVENT keys absent from that universe. The frozen B2 helper recognizes
sanitized directory tokens, so original source paths regenerate event keys with
an unknown family. All 57 Cause and 110 Damage F6 B2 keys are unmatched.

Do not count these as evaluation exclusions or detector losses. Retain exact
Step 5 replication, report missing memberships, and suppress incomparable F6
deltas. B2 coverage remains provisional pending an explicit grouping/identity
repair. Preserve the original freeze manifest; renew the execution checksum
with identical matching policy and anchor-registry checksum. This amendment
changes reconciliation/reporting only, not the frozen instrument or vocabulary.
