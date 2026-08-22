# STINT_0 Controlled Migration Reconstruction Plan

## Objective

Rebuild the prior notebook-based ML feasibility work into a local, reproducible Python pipeline without recreating the notebook sprawl one-for-one.

## Strategy

1. Create a clean local repository scaffold.
2. Reconstruct reusable modules for inventory, schema profiling, controlled vocabularies, evidence scanning, PDF extraction, and reporting.
3. Reproduce the key safe outputs from the prior pass.
4. Re-run the corrected PDF table parser and preserve the controlled-code vocabulary finding in sanitized form.
5. Emit a target-level feasibility draft only after the evidence chain is explicit target by target.

## Known Prior Findings To Preserve In Sanitized Form

- One critical target has no current demonstrable proof-of-life under available lexical, quality, reference-matrix, and ground-truth evidence.
- One PDF source family contains record-level fault-code and event evidence, but corrected fault-code tokens do not map to the current S/B/C/5/A catalog vocabulary.
- That PDF source family likely requires a source-system-specific fault or alarm vocabulary owner or equivalence mapping.
- One spreadsheet source family was read successfully and produced no pair candidates under the safe pair-discovery method.
- One structured JSON/XML source family was read successfully and produced candidate pairs requiring label/runtime validation.
- Measurement-ready denominators remain unavailable until candidate pairs are confirmed as real observed labels or validated mappings.
