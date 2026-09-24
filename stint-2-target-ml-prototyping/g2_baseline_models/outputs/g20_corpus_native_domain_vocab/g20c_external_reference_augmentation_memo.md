# G2.0c External Reference Augmentation

## Purpose

Preserve externally supported domain signal that disappeared from the model-eligible
B2 construction corpus because every observed occurrence was excluded with the
evaluation set. The evaluation set is unchanged and none of its text is used.

## Admitted

- `bearing failure`: exact term in the frozen F1c2 external vocabulary.
- `crack` and `cracking`: morphological variants backed by the frozen crack-family
  reference terms. Their subsystem constraints remain active during grouping.

All admitted rows carry `evidence_type=reference_evidence` and
`anchor_source=domain_vocabulary`. They are a separate reference layer, not
corpus-native terms, and never contribute to frequency thresholds.

## Held

- `main bearing failure`: main-bearing scope and bearing-failure evidence exist, but
  the exact compound is absent from the frozen reference vocabulary.
- `casting` and `hub casting`: no frozen F1c2/NREL/subsystem term was found.

Held terms are documented but not added. This avoids silently turning compositional
inference or committee recollection into documentary provenance.

## Step 2 Rules

- Filter corpus-native terms with path-specific frequency thresholds.
- Keep this external reference layer outside the reduction curve and term-frequency
  statistics.
- Permit it only as external coverage evidence during semantic grouping.
- Do not perform additional B2 recovery, touch the evaluation set, promote a
  denominator, map to SAP, or re-run G2.0 in this pass.
